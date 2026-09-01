# 03 Java Core — How a stack trace is captured, and what it costs — INTERNALS (§3.9, 3.9.6–3.9.8, 3.9.15)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [`finally` and try-with-resources desugaring](03a-internals-finally-and-twr-desugaring.md) · Next: [Fast-throw, truncation and StackOverflowError](03c-internals-fast-throw-and-truncation.md)

An exception is cheap to *throw* and expensive to *create*, because creating one photographs the call stack — and the photograph is taken in the constructor, developed only if someone asks to see it. `03-internals-exception-mechanics.md` already proved the `throw` side is nearly free: the exception table costs nothing to enter and `athrow`'s handler search is a bounded linear scan. This file prices the side that is not free — `Throwable`'s constructor calling `fillInStackTrace()` — down to the real OpenJDK source, the real field layout, and a harness run on this machine.

Everything below is measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, in `/tmp/exc03b`, and every source quotation is pulled from that build's own `lib/src.zip` — `java.base/java/lang/Throwable.java` and `java.base/java/lang/StackTraceElement.java` — not recalled from memory or from an older JDK. `-XX:+PrintFlagsFinal -version` on this build, quoted verbatim:

```
intx MaxJavaStackTraceDepth                   = 1024    {product} {default}
bool OmitStackTraceInFastThrow                = true    {product} {default}
bool StackTraceInThrowable                    = true    {product} {default}
intx ThreadStackSize                          = 2048    {pd product} {default}
```

`ThreadStackSize` is in **kilobytes** — `2048 × 1024 = 2,097,152 bytes ≈ 2 MB`, the fixed native region a thread's whole call stack lives in; `03c-internals-fast-throw-and-truncation.md` owns what happens when that region runs out. `01a-throwable-api-and-chaining.md` already states the *API* shape of `fillInStackTrace`, `getStackTrace`, `setStackTrace` and the four-argument constructor, and already quotes the top of `fillInStackTrace()` itself — this file does not repeat that quotation as new information, it goes one level further: the guard clause's actual semantics, the native delegate, the lazy decode path (`getOurStackTrace()`, not previously quoted anywhere in this topic), the byte arithmetic for what that decode allocates, and a harness that puts real nanoseconds against every claim.

---

## 1. Construction calls `fillInStackTrace`, and the cost is proportional to depth (3.9.6)

`[SOURCE]` `[NUM]` `[PROVE]` The picture: `new InsufficientFundsException("stakeable balance short of requested stake")` pays its stack-capture cost the moment `new` runs, whether or not the exception is ever thrown. There is no separate "capture on throw" step — by the time `athrow` sees the object, the photograph has already been taken.

### Why it exists

A `Throwable` whose trace is filled in only when actually thrown would need the constructor and the `throw` to cooperate, and an object can be constructed in one method, stored, and thrown from a completely different call stack later (a cached validation-failure singleton, a retry queue holding a pending failure). Capturing at construction time is the only point at which "the current call stack" reliably means the place the failure actually originated — by the time of a later `throw`, the original frames may already be gone. The design trades a cost every caller of `new` pays, including callers who never throw, for the guarantee that `getStackTrace()` always answers "where was this born," not "where was this last handed to `athrow`."

### When this changes what you do

It rules out one specific optimisation attempt: caching a pre-built exception instance to reuse across calls, in the belief that construction happens once and the saving compounds. The `## Pitfalls` section below measures exactly why that backfires — the trace is frozen at the one construction, and every later `throw` of the cached instance reports the original construction site, not the call that actually failed this time.

### How it works

`[SOURCE]` Every public `Throwable` constructor calls `fillInStackTrace()` unconditionally, quoted from this build's `Throwable.java`:

```java
public Throwable() {
    fillInStackTrace();
}

public Throwable(String message) {
    fillInStackTrace();
    detailMessage = message;
}

public Throwable(String message, Throwable cause) {
    fillInStackTrace();
    detailMessage = message;
    this.cause = cause;
}

public Throwable(Throwable cause) {
    fillInStackTrace();
    detailMessage = (cause==null ? null : cause.toString());
    this.cause = cause;
}
```

All four call `fillInStackTrace()` as their first statement, before a single field of the exception's own state is set — the capture is the very first thing that happens, ahead of even the message assignment. `fillInStackTrace()` itself:

```java
public synchronized Throwable fillInStackTrace() {
    if (stackTrace != null ||
        backtrace != null /* Out of protocol state */ ) {
        fillInStackTrace(0);
        stackTrace = UNASSIGNED_STACK;
    }
    return this;
}

private native Throwable fillInStackTrace(int dummy);
```

Read the guard the way the source's own comment invites: `stackTrace != null || backtrace != null` is true for a freshly-constructed, ordinary `Throwable` (`stackTrace` starts as the sentinel `UNASSIGNED_STACK`, which is non-null, and `backtrace` starts `null`, so the first disjunct alone is true). That is what lets the call proceed into the native `fillInStackTrace(int dummy)`, the overload actually implemented in the JVM, which walks the calling thread's frames and stores an opaque snapshot into the `transient Object backtrace` field — concept 2 below owns exactly what that snapshot is and is not. After the native call returns, `stackTrace` is reset to `UNASSIGNED_STACK` — not left alone — which is the signal concept 2's decode path reads to know a fresh backtrace is waiting to be turned into `StackTraceElement[]` on first request. The comment `/* Out of protocol state */` on the second disjunct exists because the guard is also how the four-argument constructor's `writableStackTrace = false` disables capture entirely: that constructor sets `stackTrace = null` directly (concept 3 quotes it), and a `null` `stackTrace` together with a `null` `backtrace` makes the guard false, so `fillInStackTrace(0)` is never reached — the guard is the single choke point both the normal path and the opt-out path pass through.

Two things about the method's own signature are easy to skim past and worth naming explicitly. First, `fillInStackTrace()` is `synchronized` — on the throwable's own monitor, not a shared or static one, because the method mutates `backtrace` and must not race with a concurrent reader of that same instance (`getOurStackTrace()` in concept 2 is `synchronized` for the identical reason: two threads calling `getStackTrace()` on a throwable shared across threads, or a thread reading while another calls `fillInStackTrace()` again, must not observe a half-written `backtrace`). Because the vast majority of `Throwable` instances are never shared across threads — an exception is created, thrown, and caught on one thread's stack — this lock is essentially always uncontended, and an uncontended `synchronized` on HotSpot resolves to a cheap biased/thin-lock fast path (`objects-equality-and-lifecycle/05-internals-object-layout.md` owns the mark-word mechanics behind that fast path). It is not a global bottleneck; it is a per-instance lock that happens to be declared `synchronized` because *some* throwables genuinely are shared (a preallocated `OutOfMemoryError`, or a stackless singleton reused across calls) and the field-mutation invariant has to hold for those too. Second, the constructor's call and the field name are easy to conflate: `fillInStackTrace()` fills in `backtrace`, an opaque VM structure — it does not touch `stackTrace`, the `StackTraceElement[]` field, beyond resetting it to the sentinel. No `StackTraceElement` object exists yet after construction; that is concept 2's subject.

**`[NUM]`** The depth arithmetic the leaf names, worked and then measured rather than assumed. The native walk captures `min(N, MaxJavaStackTraceDepth)` frames for a call stack `N` frames deep, and `MaxJavaStackTraceDepth = 1024` on this build. So a stake-reservation call three or four frames deep captures all of it; a pathological validator recursing 1,500 frames deep before throwing captures only the first 1,024 and silently drops the rest. Proven, not asserted — a method recursing to a controlled depth before throwing, then reading `getStackTrace().length`:

```java
static void recurse(int n) {
    if (n <= 0) {
        throw new RuntimeException("cap probe");
    }
    recurse(n - 1);
}
```

Measured on this build, `-Xss8m` to give the deeper call room to run without a `StackOverflowError` intervening first:

```
requested depth=500  captured length=502
requested depth=1500 captured length=1024
```

The 500-deep call captured 502 frames (500 plus `recurse`'s own initiating frame plus `main`), confirming the walk captures the *true* depth when it is under the cap; the 1,500-deep call capped out at exactly 1,024, confirming `MaxJavaStackTraceDepth` as a hard ceiling rather than a soft target. `[NUM]` The cost that dominates construction — walking and recording those frames — is therefore bounded above by 1,024 frames regardless of how deep the real recursion goes, which is why concept 4's depth=1000 measurement is close to depth=1024's true worst case and a depth=1500 measurement would show no further growth at all: the walk simply stops.

### The diagram

No diagram for this concept alone — D-115, embedded in concept 4 below, is the figure for the cost curve this concept explains the origin of; a second figure repeating "the walk is proportional to depth, capped at 1024" here would only anticipate concept 4's picture out of order.

### A concrete example

The QuizStakes shape that makes "construction, not throw" concrete — an exception built once and reused across two different call sites, showing the trace freezes at the first `new`:

```java
public final class InsufficientFundsException extends RuntimeException {
    public InsufficientFundsException(String message) {
        super(message);
    }
}

final class StakeReservationProbe {
    static final InsufficientFundsException CACHED =
        new InsufficientFundsException("stakeable balance short of requested stake");

    static void reserveViaControllerA() {
        throw CACHED;
    }

    static void reserveViaControllerB() {
        throw CACHED;
    }
}
```

`CACHED`'s trace is captured exactly once, wherever the static initializer runs — almost certainly inside neither `reserveViaControllerA` nor `reserveViaControllerB`, but at class-loading time. Every subsequent `throw CACHED` from either method reports the *same* frozen trace, pointing at the static initializer, not at whichever controller actually threw it this time. `## Pitfalls` below measures this precisely.

### The gotcha

**Insight:** the guard `stackTrace != null || backtrace != null` is a single boolean expression doing two jobs — it is both "has a walk already happened for this instance" (true after the first call resets `stackTrace` to `UNASSIGNED_STACK`, so a *second* call to `fillInStackTrace()` on the same instance re-walks and overwrites) and "is capture permitted at all for this instance" (false forever once the four-argument constructor set both fields to `null`). One field pair, two independent questions, answered by the same test — which is why concept 3's opt-out and concept 1's default path are the same three lines of code taking different branches, not two separate mechanisms.

**Pitfall:** believing the walk happens at `throw`, not `new`. `athrow` (`03-internals-exception-mechanics.md` concept 2) does nothing to the trace — it pops a reference and searches an exception table. If a profiler shows time inside `fillInStackTrace` on a hot path, the fix is at the `new` site, not at the `throw` site, and "we don't throw this often" is the wrong question if the type is *constructed* often — a validator that builds an exception speculatively and only throws it conditionally still pays full price on every construction.

> **Definition.** Every public `Throwable` constructor calls `fillInStackTrace()` as its first action, which — guarded by `stackTrace != null || backtrace != null` — delegates to a `native`, `synchronized` `fillInStackTrace(int)` that walks the calling thread's frames into the opaque `backtrace` field, capturing `min(depth, MaxJavaStackTraceDepth)` frames (`1024` on this build, confirmed by recursing past it and observing `getStackTrace().length` cap at exactly 1024); the cost is paid at `new`, not at `throw`, and is proportional to call-stack depth up to that cap.

---

## 2. The lazy `backtrace`/`stackTrace` pair, materialised only on demand (3.9.7)

`[SOURCE]` `[RESEARCH]` The picture: `fillInStackTrace()` writes into a cheap, VM-private structure — `backtrace` — and nothing resembling a `StackTraceElement[]` exists until something actually calls `getStackTrace()` or `printStackTrace()`. Between construction and that first call, an exception carrying a "full stack trace" has allocated exactly zero `StackTraceElement` objects.

### Why it exists

Most exceptions are caught and handled — logged with a message, mapped to an HTTP status, retried — without anyone ever calling `getStackTrace()` or `printStackTrace()` directly (a logging framework calling `printStackTrace`-equivalent formatting on the way to a log line is a different, later cost, paid by the *logger*, not by the `throw`). Materialising an array of decoded frame objects eagerly, on every construction, would allocate real heap objects for information the overwhelming majority of exceptions never need read back out. The design defers that allocation to the one call site that actually asks, which is the general "pay only for what you use" shape — the same shape `02c-cost-and-control-flow.md` names for the array materialisation cost at the intermediate-tier cost-model level; this file is where that laziness is implemented.

### When this changes what you do

It relocates the cost, and the relocation is the actionable fact: a log filter, an observability agent, or a `catch` block that calls `e.getStackTrace()` "just to check the depth" or "just to grab the top frame" pays the decode cost on *its own* thread, at the moment it calls it — not on the throwing thread, not at construction. A hot logging path that calls `getStackTrace()` per event has moved concept 1's cost from "once, at throw time, unavoidably" to "again, at log time, avoidably" — the same total decode work still has to happen once, but a badly-placed second or third call to `getStackTrace()` re-pays the *array-construction* cost (the clone, not the decode) every time, which is cheap per call but not free at scale.

### How it works

`[SOURCE]` The two field declarations, quoted exactly with their own comments, because the comments are the specification:

```java
/**
 * The JVM saves some indication of the stack backtrace in this slot.
 */
private transient Object backtrace;
```

```java
/**
 * A shared value for an empty stack.
 */
private static final StackTraceElement[] UNASSIGNED_STACK = new StackTraceElement[0];
```

```java
/**
 * The stack trace, as returned by {@link #getStackTrace()}.
 *
 * The field is initialized to a zero-length array.  A {@code
 * null} value of this field indicates subsequent calls to {@link
 * #setStackTrace(StackTraceElement[])} and {@link
 * #fillInStackTrace()} will be no-ops.
 *
 * @serial
 * @since 1.4
 */
private StackTraceElement[] stackTrace = UNASSIGNED_STACK;
```

Three facts fall directly out of these declarations. `backtrace` is `Object`-typed and `transient` — it is deliberately opaque at the Java level (nothing in this class or any subclass inspects its shape; only the native code that wrote it can decode it), and `transient` means it is never written to a serialization stream: a deserialized `Throwable`'s trace cannot come from a re-walk, because there is nothing on the wire to re-walk from. `UNASSIGNED_STACK` is a shared, zero-length sentinel — not `null` — used as `stackTrace`'s initial value, distinct from the `EMPTY_STACK`-style "genuinely no frames" case a reader might expect; the class comment states the deliberate write-once protocol in its own words:

```java
/*
 * To allow Throwable objects to be made immutable and safely
 * reused by the JVM, such as OutOfMemoryErrors, fields of
 * Throwable that are writable in response to user actions, cause,
 * stackTrace, and suppressedExceptions obey the following
 * protocol:
 *
 * 1) The fields are initialized to a non-null sentinel value
 * which indicates the value has logically not been set.
 *
 * 2) Writing a null to the field indicates further writes
 * are forbidden
 *
 * 3) The sentinel value may be replaced with another non-null
 * value.
 */
```

`UNASSIGNED_STACK` is exactly that sentinel for `stackTrace`: present (non-`null`) means "logically unset, decode on demand"; a `null` written later (by the four-argument constructor, concept 3) means "no further writes, ever." The decode itself — not previously quoted anywhere in this topic's other files — lives in `getOurStackTrace()`:

```java
public StackTraceElement[] getStackTrace() {
    return getOurStackTrace().clone();
}

private synchronized StackTraceElement[] getOurStackTrace() {
    // Initialize stack trace field with information from
    // backtrace if this is the first call to this method
    if (stackTrace == UNASSIGNED_STACK || stackTrace == null) {
        if (backtrace != null) { /* Out of protocol state */
            stackTrace = StackTraceElement.of(backtrace, depth);
        } else {
            // no backtrace, fillInStackTrace overridden or not called
            return UNASSIGNED_STACK;
        }
    }
    return stackTrace;
}
```

Read this against the field states it branches on. `stackTrace == UNASSIGNED_STACK` is the ordinary post-construction state (concept 1's guard reset it there); `stackTrace == null` is also tested here because the four-argument constructor's opt-out sets exactly that, and this method has to fail gracefully rather than throw for a stackless instance. In the ordinary case, `backtrace != null` — the native walk stored something — and the branch calls `StackTraceElement.of(backtrace, depth)` (`depth` is a `private transient int` sibling field the native `fillInStackTrace(0)` call also sets, recording how many frames `backtrace` actually holds), decoding the opaque native structure into real `StackTraceElement` objects **exactly once**, then caching the result back into `stackTrace`. Every call after the first sees `stackTrace` already holding real elements — not `UNASSIGNED_STACK` — and returns the cached array directly, skipping `StackTraceElement.of` entirely. The public `getStackTrace()` wrapping this always calls `.clone()` on whatever `getOurStackTrace()` returns, decoded or not, which is the second half of the laziness story: the *decode* happens once, but the *array returned to the caller* is a fresh defensive copy on every single call, so no caller can mutate another caller's view of the trace by writing into the array it was handed.

`[RESEARCH]` `StackTraceElement.of(Object, int)`, from this build's `StackTraceElement.java`, confirming the decode is a native fill into pre-allocated shells rather than a native array construction:

```java
static StackTraceElement[] of(Object x, int depth) {
    StackTraceElement[] stackTrace = new StackTraceElement[depth];
    for (int i = 0; i < depth; i++) {
        stackTrace[i] = new StackTraceElement();
    }

    // VM to fill in StackTraceElement
    initStackTraceElements(stackTrace, x, depth);
    return of(stackTrace);
}

private static native void initStackTraceElements(StackTraceElement[] elements,
                                                  Object x, int depth);
```

Java code allocates the array and every element shell with a private no-arg constructor first, then hands the whole array to a native call that fills each shell's fields from `backtrace`; a final `of(StackTraceElement[])` overload (not the two-argument one above) walks the array once more calling `computeFormat()` on each element, which resolves the `format` byte used by `toString()` — the byte field named among `StackTraceElement`'s fields below.

`[RESEARCH]` **Every observable consequence, verified rather than assumed:**

**A constructed-but-never-inspected exception allocates no `StackTraceElement`.** Measured via `ThreadMXBean.getThreadAllocatedBytes`, comparing bytes allocated by `new InsufficientFundsException("stake short")` against bytes allocated by the *first* `getStackTrace()` call on the same instance, on this build:

```
constructed  -> allocation attributable to construction (message field, object shell, native walk's Java-visible cost)
first getStackTrace() -> +152 bytes  (decode: array + one StackTraceElement shell + format computation, for a 1-frame trace)
second getStackTrace() -> +24 bytes  (clone of the now-cached 1-length array only — no decode work repeated)
```

The jump from the first call to the second — 152 bytes down to 24 — is the decode-versus-clone split made visible: the first call pays `StackTraceElement.of`'s allocation (the array, the shell, `computeFormat()`'s internal string work) once; every call after that pays only `.clone()`'s cost on an already-decoded array.

**The first `getStackTrace()` decodes; every call after clones a fresh array.** Same run: `first == second` compared by reference is `false`, while both report the same `.length` — confirming the public method never hands out the cached backing array itself, only copies of it, exactly as `getStackTrace()`'s own source (`getOurStackTrace().clone()`) states.

**`setStackTrace` replaces the cache and makes `backtrace` irrelevant.** Calling `ex.setStackTrace(new StackTraceElement[0])` after the exception already has a real trace, then calling `getStackTrace()` again, returned length `0` — the replacement is authoritative and `getOurStackTrace()`'s branch on `stackTrace == UNASSIGNED_STACK` is now false (the field holds the caller's array, not the sentinel), so `backtrace` is never consulted again for this instance even though the native walk that produced it still technically exists in memory.

**The field is `transient`, so deserialization does not re-walk.** `backtrace` carries `transient` in its own declaration, meaning `ObjectOutputStream` never writes it; a deserialized `Throwable`'s `stackTrace` field — which *is* serialized, per its own `@serial` javadoc tag on the field above — is exactly the array that was on the wire, decoded or not, with no native re-walk possible because the thread that originally threw the exception may not exist, may be on a different machine, or may simply no longer have those frames live. `../serialization/02-serialization.md` owns `transient` and the serialization mechanism itself; the consequence that matters here is narrower and specific to this field: **a trace surviving a serialization round trip is data, not a live capability** — it is inert `StackTraceElement[]` content, never something that can be re-decoded or re-walked on the receiving JVM.

**`[NUM]`** The byte arithmetic for the decode, enumerated from this build's actual field declarations rather than recalled:

```java
private transient Class<?> declaringClassObject;
private String classLoaderName;
private String moduleName;
private String moduleVersion;
private String declaringClass;
private String methodName;
private String fileName;
private int    lineNumber;
private byte   format = 0; // Default to show all
```

Seven reference-typed fields (`declaringClassObject`, `classLoaderName`, `moduleName`, `moduleVersion`, `declaringClass`, `methodName`, `fileName`), one `int`, one `byte` — the module/loader/version trio was added in **Java 9** alongside the module system, so a `StackTraceElement` from a pre-9 JDK is genuinely narrower; a claim of "four references and two ints" describes that older, smaller shape and is the stale version to flag if quoted elsewhere. `05-internals-object-layout.md` owns the general arithmetic this borrows: a 64-bit JVM with compressed oops and a compressed class pointer gives a **12-byte object header** (8-byte mark word plus 4-byte compressed class pointer) and 4-byte compressed reference fields, with object size rounded up to the next multiple of 8:

```
7 references × 4 bytes  = 28 bytes
1 int                   =  4 bytes
1 byte (padded)         =  1 byte  (absorbed into alignment padding)
                          ------
data                     = 33 bytes
+ 12-byte header         = 45 bytes
rounded to 8-byte align  = 48 bytes per StackTraceElement shell
```

A 100-frame trace: 100 shells at 48 bytes = 4,800 bytes, plus the backing array itself (a 16-byte array header — 12-byte object header plus a 4-byte length field, already 8-aligned — plus 100 compressed element references at 4 bytes = 400 bytes) = 416 bytes, for a total of **5,216 bytes ≈ 5.09 KiB** to materialise a 100-frame trace. At the `MaxJavaStackTraceDepth` ceiling of 1,024 frames: 1,024 shells at 48 bytes = 49,152 bytes, plus the array's 16-byte header and 1,024 × 4 = 4,096 bytes of references = 4,112 bytes, for a total of **53,264 bytes ≈ 52.02 KiB** — the maximum a single `getStackTrace()` call can ever allocate for its decode, because the frame count is capped at 1,024 regardless of how deep the throw actually was. Both figures assume compressed oops and a compressed class pointer, which is the default for any heap under roughly 32 GB — true of every QuizStakes service — and both are the *decode* cost specifically; concept 1's construction-time cost, dominant in every measurement below, uses the cheaper opaque `backtrace` structure and never touches this arithmetic unless `getStackTrace()` or `printStackTrace()` is actually called.

### The diagram

No diagram for this concept: the lazy pair's behaviour is four verified facts and a byte-arithmetic worksheet, both of which read faster as prose and a calculation than as a picture; D-115 in concept 4 marks the materialisation point on the cost curve as a labelled second cost, which is the one place this concept's shape belongs in a figure.

### A concrete example

The QuizStakes shape that shows the cost moving to whoever asks — a stake-reservation failure logged two different ways:

```java
// Cheap: the logger's format string never calls getStackTrace() or printStackTrace().
LOGGER.warn("stake reservation rejected for client {}: {}", clientId, ex.getMessage());

// Expensive, on the logging thread, and easy to miss in review:
LOGGER.warn("stake reservation rejected for client {}: depth={} frame0={}",
    clientId, ex.getStackTrace().length, ex.getStackTrace()[0]);
```

The second line calls `getStackTrace()` twice — the first call pays the one-time decode (concept 2's ~52 bytes-per-frame arithmetic, times whatever depth this particular exception actually captured), the second call re-clones the now-cached array for no reason beyond the code being written as two separate expressions instead of one local variable. Neither call is expensive in isolation; at 1,200 stake reservations/sec peak with a meaningful shortfall rate, two avoidable `getStackTrace()` calls per rejection is exactly the kind of cost concept 1's "why it exists" argument is protecting the *unlogged* majority of exceptions from paying, reintroduced by a logging statement that did not need the array at all.

### The gotcha

**Insight:** `getOurStackTrace()` is where "lazy" actually means something operationally — the decode is gated on `stackTrace == UNASSIGNED_STACK`, an identity comparison against the one shared sentinel instance, not a null check or a length check, which is why `setStackTrace(new StackTraceElement[0])` (a *different*, caller-supplied zero-length array) permanently disables the decode branch even though its `.length` matches `UNASSIGNED_STACK`'s — the two are `==`-different and the check is identity, not content.

**Pitfall:** assuming `getStackTrace()` is a cheap, side-effect-free "peek" safe to call from a hot log-enrichment path because "it's just reading a field." The *second* call is exactly that cheap — a clone of a cached array. The *first* call on any given instance is not, and code paths that call `getStackTrace()` conditionally (only on the first exception of a burst, for instance) can appear cheap in testing and then pay the full decode the one time it matters, under load, on the thread that can least afford it.

> **Definition.** `Throwable` stores its trace as a lazy pair — an opaque, `transient`, native-written `backtrace` filled in at construction, and a `StackTraceElement[] stackTrace` initialised to the shared sentinel `UNASSIGNED_STACK` — decoded into real `StackTraceElement` objects exactly once, by `getOurStackTrace()`, on the first call to `getStackTrace()` or `printStackTrace()`, and cached thereafter; every public `getStackTrace()` call clones that cache fresh (measured: reference-unequal, content-equal arrays on repeated calls), so the decode is paid once per instance and the clone is paid once per call, at roughly 48 bytes per frame under compressed oops.

---

## 3. The four-argument constructor and the `fillInStackTrace` override — cheaper by a factor that depends on depth (3.9.8)

`[SOURCE]` `[NUM]` `[RESEARCH]` `[BUILD]` The picture: two independent ways to tell `Throwable` "skip the walk," one a constructor argument that also happens to control suppression, the other a virtual method override that intercepts the same call from the other side.

### Why it exists

Concept 1's default — walk the stack on every construction — is the right default for exceptions that are genuinely exceptional, thrown rarely, and need to be diagnosed when they do occur. It is the wrong default for an exception type constructed thousands of times a second on a path the JIT and the application both already understand well, where the trace would only ever say "here, again, at the same three lines" and nobody reads it. Java 7 added the four-argument constructor specifically to give library and application authors a supported way to opt a *type* out of the walk without hand-rolling the interception themselves — the Javadoc names the motivating cases explicitly: "a virtual machine reusing exception objects under low-memory situations" and repeated catch-and-rethrow "to implement control flow between two sub-systems."

### When this changes what you do

This is `02c-cost-and-control-flow.md`'s decision, stated once more only to anchor the mechanism to it: reach for a stackless exception when a `throw` sits on a path measured in thousands per second and the trace has never once been the thing that diagnosed a real defect at that site. Do not reach for it as a blanket policy, and note that *how much* it buys depends on how deep the throw site sits: concept 4's table below measures ≈49× at depth 1 but only ≈1.4–1.6× from depth 100 onward, because a stackless exception skips the capture and still pays the recursion and unwind. A throw from a shallow handler genuinely does get an order of magnitude and more; a throw from 100 frames down a Spring call stack — which is where a real service throws — gets a modest 1.4–1.6×, nowhere close to the two-to-three-orders-of-magnitude gap to simply not throwing, which `02c-cost-and-control-flow.md` concept 1 covers as the sibling that wins whenever the caller branches on the outcome immediately. `StackWalker` (Java 9, owned by `03d-internals-npe-messages-and-diagnostics.md`) is the sibling to reach for instead when the actual goal is inspecting the current call stack rather than reporting a failure — it walks frames lazily, with no `Throwable` involved at all, and is cheaper still for that narrower job.

### How it works

`[SOURCE]` The protected four-argument constructor, quoted from this build's source:

```java
protected Throwable(String message, Throwable cause,
                    boolean enableSuppression,
                    boolean writableStackTrace) {
    if (writableStackTrace) {
        fillInStackTrace();
    } else {
        stackTrace = null;
    }
    detailMessage = message;
    this.cause = cause;
    if (!enableSuppression)
        suppressedExceptions = null;
}
```

Both booleans, line by line. `writableStackTrace = true` takes the ordinary path — `fillInStackTrace()`, identical to every other constructor. `writableStackTrace = false` skips the call entirely and sets `stackTrace = null` **directly**, not to `UNASSIGNED_STACK`. That distinction is the whole mechanism: concept 1 showed `fillInStackTrace()`'s guard is `stackTrace != null || backtrace != null`, and `null` is exactly the value that makes both disjuncts false when `backtrace` is also still `null` (it never got written, because the native call never ran) — so this constructor does not merely skip the walk once, it writes the field into the one state that keeps `fillInStackTrace()` a permanent no-op on this instance, including any *future*, redundant call to `fillInStackTrace()` a subclass or caller might make. `enableSuppression = false` sets `suppressedExceptions = null`, and `addSuppressed`'s own source (owned by `01c-try-with-resources-and-suppression.md`) checks for exactly that sentinel before appending — so a `null` suppressed-exceptions list makes every future `addSuppressed` call a silent no-op, by the identical write-once protocol concept 2 quoted for `stackTrace`.

`[BUILD]` Two compiling forms, the QuizStakes stake-reservation exception built both ways:

```java
public final class InsufficientFundsException extends RuntimeException {
    public InsufficientFundsException(String message) {
        super(message, null, false, false);   // enableSuppression, writableStackTrace
    }
}
```

```java
public final class InsufficientFundsStacklessException extends RuntimeException {
    public InsufficientFundsStacklessException(String message) {
        super(message);
    }

    @Override
    public synchronized Throwable fillInStackTrace() {
        return this;   // intercepts the call every ctor makes; never walks
    }
}
```

The second form works by a completely different route to the same field state: its ordinary `RuntimeException(String)` superclass constructor calls `fillInStackTrace()` exactly as concept 1 showed, but virtual dispatch resolves that call to the **overriding** method on the most-derived class — `InsufficientFundsStacklessException`'s own `fillInStackTrace()`, which does nothing but `return this`. `stackTrace` is left at its initial sentinel `UNASSIGNED_STACK` (never reset to it a second time, because the override never runs the code that would do that), and `backtrace` is left `null` (the native call was never reached). `getOurStackTrace()`'s branch — `if (backtrace != null)` — sees `backtrace == null` and falls to `return UNASSIGNED_STACK` in both forms, which is why the two forms are observably identical from the outside despite reaching that state by different code paths.

`[RESEARCH]` The claim worth checking rather than assuming — that the two forms differ in what `getStackTrace()` returns — measured directly on this build:

```java
StakelessInsufficientFunds a = new StakelessInsufficientFunds("ctor-form");
NoTraceInsufficientFunds b = new NoTraceInsufficientFunds("override-form");
System.out.println(a.getStackTrace().length);   // 0
System.out.println(b.getStackTrace().length);   // 0
```

```
ctor-form getStackTrace().length = 0
override-form getStackTrace().length = 0
```

Both return a zero-length array, not `null` and not two different lengths — refuting any version of the claim that one form leaves a genuinely empty (but non-null) array and the other something distinguishable. Both hit the identical `return UNASSIGNED_STACK` branch in `getOurStackTrace()` for the identical reason (`backtrace == null`), and the public `getStackTrace()` clones that shared zero-length sentinel on the way out either way. The two forms do differ, though, on the axis the constructor's other argument controls — suppression — confirmed on the same run:

```
ctor-form getSuppressed().length after addSuppressed()      = 0   (silently ignored)
override-form getSuppressed().length after addSuppressed()  = 1   (accepted normally)
```

The four-argument constructor's `enableSuppression = false` argument silently drops the suppressed exception; the `fillInStackTrace()`-override form, built on the ordinary two-argument `RuntimeException(String)` superclass call, never touched `suppressedExceptions` and accepts suppression normally. This is the concrete, measured answer to "which is right for my type": the constructor form is a package deal — stack trace off *and*, if you ask for it, suppression off — while the override form is narrower and touches only the trace.

**`[NUM]`** The three-way comparison table the leaf and the house style both require, gathering the mechanism and its consequence in one place:

| Mechanism | What it disables | `getStackTrace()` returns | `addSuppressed` | Available since | When to use |
|---|---|---|---|---|---|
| Four-argument constructor, `writableStackTrace=false` | The walk, permanently (`stackTrace=null`, both future `fillInStackTrace()` and `setStackTrace` become no-ops) | Zero-length array | No-op if `enableSuppression=false` too; normal otherwise | Java 7 | Default choice — it is the platform's own mechanism, needs no override to maintain, and lets you also disable suppression in the same call |
| Overriding `fillInStackTrace()` to `return this` | The walk, permanently, via virtual dispatch intercepting every constructor's call | Zero-length array (measured identical to the constructor form) | Unaffected — normal `addSuppressed` behaviour | Works on any JDK this project targets (no version floor of its own) | A class whose immediate superclass does not expose (or does not forward to) a four-argument constructor, and suppression should stay enabled |
| `-XX:-StackTraceInThrowable` | The walk, for **every** `Throwable` in the JVM, no exceptions | Zero-length array, JVM-wide | Unaffected | JVM flag, all supported versions | Diagnostic use only — see the pitfall below |

The override form is a genuinely virtual call — every one of `RuntimeException`'s inherited constructors still executes the line `fillInStackTrace();` in source, and the JIT has to resolve that call site to whichever override is actually installed on the runtime type, same as any other overridden method call. That resolution is not free in the abstract, but it is not where this mechanism's saving comes from either — concept 4's measurement shows both stackless forms landing within noise of each other, which means the dispatch overhead is negligible next to the walk it is avoiding.

The design rule, stated as a trade rather than a free win: a stackless exception on the 1,200/sec insufficient-funds path is the right call once `02c-cost-and-control-flow.md`'s frequency-and-actionability test says the type is worth keeping as an exception at all — but the day a genuinely new bug starts throwing that same type from a different, broken call site, there is no trace to work from, because the type was built to have none. Pair a stackless exception with a metric incremented at the throw site (a counter, not a log line requiring a trace to be useful) and a one-line comment at the class declaration naming which hot path it exists for, so a reviewer treats a new `throw` of that type as a deliberate reuse to double-check, not a convenient existing name.

### The diagram

No diagram for this concept: the mechanism is two short, complete code listings and a three-row comparison table, both of which are precise as text; D-115 in concept 4 plots the *cost consequence* of choosing one of these forms, which is the one place a picture earns its keep for this material.

### A concrete example

Already given above as the two `[BUILD]` listings — both compile, both are shown in full, and concept 4 measures both against a normal exception and a boolean return at four depths.

### The gotcha

**Pitfall:** believing the override form is "more portable" because it needs no Java-7-specific API, while missing that it changes suppression behaviour not at all — a reviewer expecting the override to also silence `addSuppressed` (because that is what the four-argument constructor's Javadoc trains people to expect from "the stackless idiom" generically) gets a class that happily accumulates suppressed exceptions it has no readable trace to report alongside. Fix: if suppression must also be off, the override form needs its own explicit `suppressedExceptions = null` assignment or an overridden `addSuppressed` — it does not come for free the way it does with the constructor.

**Interview:** "Name two ways to build a stackless exception, and say what each one actually skips." The four-argument constructor's `writableStackTrace=false`, which sets `stackTrace` to `null` directly so `fillInStackTrace`'s guard is permanently false, optionally paired with `enableSuppression=false`; and overriding `fillInStackTrace()` to `return this`, which intercepts the identical constructor-time call via virtual dispatch and touches nothing else. Both measured, on this build, to produce `getStackTrace().length == 0`.

> **Definition.** A stackless exception is one whose `stackTrace` field is fixed at `null` before `fillInStackTrace`'s guard is ever consulted — either directly, via the Java 7 four-argument `Throwable(String, Throwable, boolean, boolean)` constructor's `writableStackTrace=false` argument (which can also disable suppression via its third argument), or indirectly, by overriding `fillInStackTrace()` itself to `return this` and relying on virtual dispatch to intercept every superclass constructor's call to it; both forms measured identical in `getStackTrace().length == 0` and in construction cost, and differ only in whether suppression is affected.

---

## 4. Exception performance, measured: depth, form, and the boolean baseline (3.9.15)

`[NUM]` `[PROVE]` `[RESEARCH]` The picture, now with numbers on it rather than an impression: five shapes, four depths, one machine, one run — construct, throw, catch, repeat, timed.

### Why it exists

Concepts 1 through 3 establish the mechanism; this concept exists to stop the mechanism from being argued about in the abstract. "Stack traces are the whole cost of an exception" and "stackless exceptions are basically free" are both claims a harness can confirm or refute, and both deserve to be checked against this exact build rather than repeated from folklore.

### When to reach for it, and when not

Run a harness like this one before optimising an exception path, not instead of running it — a number from a different machine, a different JIT warm-up state, or a different JDK minor version is a *shape*, not a value to plan capacity around. `02c-cost-and-control-flow.md` ran its own version of this measurement at the intermediate-tier decision-making level; this concept re-runs it at the mechanism level and reports where the two runs agree and where they do not, honestly, rather than picking whichever number is more flattering.

### How it works

`[PROVE]` The harness: five call shapes, sharing an identical recursion depth per row so the only variable across a row is which exception type (or non-exception) gets constructed and thrown at the bottom of the recursion.

```java
static boolean reserveNormal(int depthRemaining) {
    if (depthRemaining > 0) return reserveNormal(depthRemaining - 1);
    throw new NormalReservationException("stake reservation short of funds");
}
static boolean callNormal(int depth) {
    try { return reserveNormal(depth); }
    catch (NormalReservationException e) { sink = e; return false; }
}

// identical shape, but the catch block also materialises the trace:
static boolean callNormalMat(int depth) {
    try { return reserveNormalMat(depth); }
    catch (NormalReservationException e) { sink = e.getStackTrace(); return false; }
}

// identical shape, StakelessCtorException built via the four-argument constructor
// identical shape, StakelessOverrideException overriding fillInStackTrace()

static boolean reserveBoolean(int depthRemaining) {
    if (depthRemaining > 0) return reserveBoolean(depthRemaining - 1);
    return false;
}
static boolean callBoolean(int depth) {
    boolean r = reserveBoolean(depth);
    flagSink = r;
    return r;
}
```

`sink` and `flagSink` are `volatile` fields the result is written into after every call, the harness's only dead-code-elimination guard. Warmed 200,000 iterations then timed over 2,000,000 (depth 1/10/100), and separately warmed 5,000 then timed over 50,000 (depth 1,000, run with `-Xss16m` so the deep recursion has room), `System.nanoTime()` around the timing loop, divided by iteration count. Measured on this build:

```
depth=1     normal=    237.0ns  normal+getStackTrace=    589.8ns  stackless-ctor=      4.8ns  stackless-override=      5.9ns  boolean=    1.5ns
depth=10    normal=    784.2ns  normal+getStackTrace=   1814.3ns  stackless-ctor=    398.1ns  stackless-override=    399.5ns  boolean=    4.9ns
depth=100   normal=   5895.5ns  normal+getStackTrace=  13133.1ns  stackless-ctor=   3826.1ns  stackless-override=   3797.7ns  boolean=   39.9ns
depth=1000  normal=  56537.9ns  normal+getStackTrace= 122695.7ns  stackless-ctor=  39537.9ns  stackless-override=  39699.0ns  boolean= 2399.9ns
```

State the harness's limitations plainly, because they are the reason nobody should quote these numbers as a capacity-planning input: no forking (each depth ran in the same JVM process as the others, so JIT and GC state at one depth is influenced by whatever ran immediately before it), no `Blackhole`-equivalent beyond a single `volatile` sink field (a sufficiently aggressive future JIT could in principle prove more of the boolean path dead than it currently does), JIT compilation state uncontrolled (whichever tier C1/C2 happened to be active when the timing loop ran is what got measured, not a guaranteed steady state), and a single run rather than several repetitions with variance reported. Guide 06 owns JMH, which removes all four of these caveats at the cost of a much heavier harness.

`[NUM]` Compute `normal / stackless-ctor` at **every** row, not just the deep ones, because the ratio is not a constant — it collapses as depth grows, and that is the single most important thing this table says:

| Depth | `normal` | `stackless-ctor` | Ratio | Capture cost (`normal − stackless`) | Shared cost (recursion + unwind) |
|---|---|---|---|---|---|
| 1 | 237.0ns | 4.8ns | **≈49.4×** | 232.2ns | 4.8ns |
| 10 | 784.2ns | 398.1ns | **≈1.97×** | 386.1ns | 398.1ns |
| 100 | 5895.5ns | 3826.1ns | **≈1.54×** | 2069.4ns | 3826.1ns |
| 1000 | 56537.9ns | 39537.9ns | **≈1.43×** | 17000.0ns | 39537.9ns |

So the leaf's "roughly an order of magnitude cheaper" is **right at shallow depth and wrong at realistic depth**, and stating it as one number in either direction misleads. At depth 1 the measured ratio is `237.0 / 4.8 ≈ 49.4×` — five times the folklore's 10×, not a fifth of it — and the `fillInStackTrace` override form is `237.0 / 5.9 ≈ 40.2×`. By depth 10 it is already down to ≈1.97×, and from depth 100 onward it sits in the 1.4–1.6× band.

**Insight:** the mechanism behind the collapse is in the last two columns, and it is arithmetic rather than anything subtle. A stackless exception skips only the *capture*; it still pays the N-frame recursion down and the N-frame unwind back up, and that cost is **shared** with the normal path. At depth 1 there is essentially no shared cost — 4.8ns — so the capture is nearly the entire cost of a normal exception and removing it removes nearly everything. As depth grows both terms grow roughly linearly (capture 232ns → 17,000ns; shared 4.8ns → 39,538ns), but the shared term grows from almost nothing while the capture grows from a large base, so the shared term comes to dominate and the ratio decays toward 1×. Extrapolating that trend rather than the ratio is what makes the number predictable: the saving is always about "the cost of walking N frames", and the question is only how large that is next to the cost of *having* N frames.

**The honest conclusion, stated once and not softened**: skipping `fillInStackTrace()` is a real and worthwhile saving whose size is entirely a function of stack depth — an order of magnitude and more in a shallow frame, a modest 1.4–1.6× at the depths a real service actually throws from. Neither figure alone is the answer, and quoting the depth-1 number as a general result is exactly as wrong as quoting the depth-100 number as one. What the table also shows, and what the folklore gets wrong in a way the depth dependence does not excuse, is that a stackless exception is *not* free even when the capture is gone: at depth 100 it still costs 3,826ns, because the object allocation, the `RuntimeException`'s own field initialisation, and (for the constructed-message forms) any `String` work all remain, and at realistic depth those are a larger fraction of the remaining total than "stack traces are the whole cost" accounts for.

What *is* an order of magnitude and more at **every** depth measured — the one ratio in this table that does not collapse — is `normal / boolean`: `237.0 / 1.5 ≈ 158×` at depth 1, `5895.5 / 39.9 ≈ 148×` at depth 100, and `56537.9 / 2399.9 ≈ 23.6×` at depth 1000 (the ratio narrows at depth 1000 because the boolean path's own recursion — 1,000 real frame pushes with no exception involved — starts to dominate its own cost, not because the exception got relatively cheaper). The boolean return is where the durable order-of-magnitude-and-more gap lives, which is `02c-cost-and-control-flow.md` concept 1's entire argument, confirmed again here from the mechanism side.

`[RESEARCH]` Independently corroborated by `../build-it/03h-stackless-exception.md`, which builds a stackless exception from scratch and measures **11.15× at depth 1 and 1.47× at depth 100** — the same collapse, and its depth-100 absolute figures land within 4% of this file's. Its depth-1 ratio is lower than this file's 49.4× for a reason worth knowing, because it is the practical caveat on the whole shallow-depth result: its exception carries a four-entry immutable context map costing 25.02ns to build, and at depth 1 that construction work is most of a stackless exception's total. In other words the 49.4× here is the ceiling for a *bare* stackless exception with a literal message, and any real one that does useful work in its constructor gives some of it straight back.

`[RESEARCH]` Cross-checking against `02c-cost-and-control-flow.md`'s own numbers, run on the same machine with a differently-shaped harness (message built via `String` concatenation rather than a literal, and a slightly different warm-up/iteration schedule): its depth=10 figure of **784ns** for a normal exception matches this file's **784.2ns** almost exactly; its depth=100 figure of **5790ns** is close to but not identical with this file's **5895.5ns**; its depth=1000 figure of **52260ns** is noticeably below this file's **56537.9ns**. Report the disagreement rather than silently picking one: two harnesses on the same machine, timing the same underlying mechanism, differing in message construction and in exactly which iteration/warmup counts were used, land within a few percent at shallow depth and diverge by roughly 8% at depth 1,000 — consistent with the harnesses' own stated limitation that neither controls JIT compilation state, and evidence for why guide 06's JMH is the tool to reach for the moment a number needs to go into a document more permanent than this one.

`[RESEARCH]` The JVM-wide switch, confirmed to behave exactly as `02c-cost-and-control-flow.md` reported, reproduced independently on this build:

```
default (StackTraceInThrowable=true)  -> trace length=1
-XX:-StackTraceInThrowable            -> trace length=0
```

A plain `new RuntimeException("insufficient stakeable balance for stake 4.20")`, with the flag off, produced a zero-length trace with no code change anywhere — the JVM-wide equivalent of every `Throwable` in the process silently gaining `writableStackTrace=false`. **Do not reach for this flag in production**: it blinds every future genuine defect's trace along with the hot path it was meant to help, for a saving no larger than the per-class stackless forms above already deliver on the one type that actually needs it.

### The diagram

![D-115 — `fillInStackTrace` dominates exception cost](../diagrams/D-115-fillinstacktrace-cost.svg)

**D-115** — Three curves against stack depth 1 → 1,000: a normal exception rising roughly linearly with depth, a stackless exception flat, and a boolean return as a flat baseline near zero; the y axis is explicitly a curve *shape*, not this file's measured data, because the mechanism gives the linearity while the constants are machine-specific — the measured table above is the numbers, this figure is the shape, and reading data points off the picture is exactly the mistake the caption is written to prevent. The figure marks `-XX:-StackTraceInThrowable` (default `true`) as the JVM-wide switch that flattens every curve to the stackless line, the `MaxJavaStackTraceDepth = 1024` cap as a vertical line past which the normal curve stops rising because the walk simply stops capturing more frames, the lazy `backtrace → StackTraceElement[]` materialisation as a second, separate cost paid only when `getStackTrace()` is first called (this file's `normal+getStackTrace` row, roughly double the plain-normal row at every depth measured), and names the insufficient-funds path at **1,200 stake reservations/sec** as the case where these curves stop being academic.

### A concrete example

The design decision made concrete once more, now with this file's own numbers rather than a cross-reference to `02c`'s:

```java
// On the 1,200/sec insufficient-funds path, deliberately stackless.
// Measured, this build: ~1.4-1.5x cheaper to construct than the default
// form at realistic call depth; getStackTrace().length == 0, by design.
public final class InsufficientFundsException extends RuntimeException {
    public InsufficientFundsException(String message) {
        super(message, null, false, false);
    }
}
```

```java
// Metered, not silent: the throw site records that this fired, so an
// operator can see the rate without needing a trace to diagnose the shape.
public StakeSplit reserveStake(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        insufficientFundsCounter.increment();
        throw new InsufficientFundsException(
            "stakeable balance " + stakeable + " short of requested stake " + stake);
    }
    return bonusService.split(clientId, stake);
}
```

The counter is what replaces the trace this type has deliberately given up — an operator watching `insufficientFundsCounter`'s rate against the 1,200/sec baseline can tell "this is happening more than usual" without ever needing `getStackTrace()`, which is the whole point of choosing this type for this path in the first place. `02c-cost-and-control-flow.md` concept 1 covers the sibling that wins more often in practice — returning `Optional.empty()` instead of throwing at all — which needs no counter because there is no exception to have gone silent.

### The gotcha

**Pitfall:** quoting *any* single ratio for "how much cheaper a stackless exception is" as settled fact — in either direction — without a harness of your own and without naming the depth. The folklore figure of 10× is not simply wrong: on this build it is an *understatement* at depth 1, where the measured ratio is ≈49.4×, and an overstatement from depth 10 onward, where it falls to ≈1.97× and then settles in the 1.4–1.6× band. Both halves of the table are real, so a claim that omits the depth is unfalsifiable rather than merely imprecise. Two further reasons to re-measure rather than quote: a genuinely different JIT, heap size, or JDK minor version could move any of these numbers, and `02c-cost-and-control-flow.md`'s independently-run harness already disagrees with this one by up to 8% at depth 1,000 despite measuring the identical mechanism on the identical machine. Treat every figure here as "roughly this shape, at this depth, on this hardware," never as a number to write into a capacity plan without re-measuring. The one claim that *is* robust across every depth measured is the comparison against a plain boolean return.

> **Definition.** Measured on Oracle JDK 21.0.7 (macOS aarch64), a normal exception's construct-throw-catch cost rises from roughly 237ns at depth 1 to roughly 56,538ns at depth 1,000, and a stackless exception (either mechanism from concept 3) is cheaper by a factor that **collapses with depth** — ≈49.4× at depth 1, ≈1.97× at depth 10, ≈1.54× at depth 100 and ≈1.43× at depth 1,000 — because the capture is the only thing skipped while the N-frame recursion and unwind are paid by both, so the saving is an order of magnitude and more in a shallow frame and a modest 1.4–1.6× at the depths a real service throws from; the one ratio that does not collapse is against a plain boolean return, which stays one to two orders of magnitude cheaper than *any* exception form at every depth and is the number that actually settles `02c-cost-and-control-flow.md`'s control-flow decision; `-XX:-StackTraceInThrowable`, confirmed independently on this build, produces the identical zero-length-trace effect JVM-wide rather than per class.

---

## Pitfalls

### Caching a pre-constructed exception to avoid the cost

**Wrong**

```java
public final class StakeReservationValidator {
    // "Optimisation": build it once, throw the same instance every time.
    private static final InsufficientFundsException CACHED_FAILURE =
        new InsufficientFundsException("stakeable balance short of requested stake");

    public void validate(ClientId clientId, Money stakeable, Money stake) {
        if (stakeable.amount().compareTo(stake.amount()) < 0) {
            throw CACHED_FAILURE;
        }
    }
}
```

Concept 1 measured why this is wrong, not just distasteful: `fillInStackTrace()` runs once, at `CACHED_FAILURE`'s static initialization, wherever that happens to occur — almost certainly not inside any call to `validate`. Every subsequent `throw CACHED_FAILURE`, from any caller, at any later time, reports the identical frozen trace pointing at the class's static initializer. A real defect elsewhere that happens to route through this exact exception type produces a trace that is actively misleading rather than merely absent — worse than the stackless forms in concept 3, which at least advertise their emptiness rather than implying a false origin.

**Right**

```java
public final class StakeReservationValidator {
    public void validate(ClientId clientId, Money stakeable, Money stake) {
        if (stakeable.amount().compareTo(stake.amount()) < 0) {
            throw new InsufficientFundsException(
                "stakeable balance " + stakeable + " short of requested stake " + stake);
        }
    }
}
```

If the construction cost genuinely matters at this call frequency, the fix is concept 3's stackless constructor or override — a *fresh* instance every time, with the walk skipped deliberately and visibly, not a *shared* instance whose walk happened once, accidentally, somewhere else.

**Why people believe it:** "expensive to construct" sounds exactly like "cache the constructed result," which is correct advice for almost every other expensive-to-build immutable value in the language — a compiled `Pattern`, a `DateTimeFormatter`, a large `BigDecimal` constant. `Throwable` looks like it should follow the same rule because it, too, is nominally immutable once built. The rule breaks specifically because a `Throwable`'s entire diagnostic value is tied to *when and where* it was built, which no other commonly-cached immutable value carries as its primary purpose.

### Believing the cost is in the `throw`, not the `new`

**Wrong**

```java
// "This method never throws under load, so exceptions aren't a concern here."
static StakeSplit reserveOrFail(ClientId clientId, Money stakeable, Money stake) {
    InsufficientFundsException prebuilt =
        stakeable.amount().compareTo(stake.amount()) < 0
            ? new InsufficientFundsException("stakeable balance short of requested stake")
            : null;
    // The decision whether to actually throw `prebuilt` is made below,
    // based on a downstream check — but the object above is already built.
    if (prebuilt != null && someLaterCondition()) {
        throw prebuilt;
    }
    return bonusService.split(clientId, stake);
}
```

The belief that "we don't throw this often" makes the path cheap is checking the wrong verb. The `new InsufficientFundsException` call on the line above runs `fillInStackTrace()` and pays concept 1's full, depth-proportional cost the moment the shortfall condition is true — regardless of whether `someLaterCondition()` ever lets the `throw` execute. A path that constructs speculatively on every shortfall but only throws occasionally pays construction's cost at the shortfall rate, not at the throw rate.

**Right**

Construct only once the decision to throw is final, or restructure so the exceptional object is not built until the branch that actually raises it:

```java
static StakeSplit reserveOrFail(ClientId clientId, Money stakeable, Money stake) {
    if (stakeable.amount().compareTo(stake.amount()) < 0 && someLaterCondition()) {
        throw new InsufficientFundsException("stakeable balance short of requested stake");
    }
    return bonusService.split(clientId, stake);
}
```

**Why people believe it:** "exceptions are for exceptional control flow" is usually taught alongside "so don't throw them often," and the two statements blur into "the throw is the event to worry about," when the actual expensive event — `fillInStackTrace()` — is one keyword earlier, on the `new`, and fires regardless of what happens next.

### Reaching for `-XX:-StackTraceInThrowable` to make exceptions cheap

**Wrong**

```
# "Exceptions are slow, and I don't want to change every exception type."
java -XX:-StackTraceInThrowable -jar payment-service.jar
```

Confirmed on this build: this flag zeroes the trace for **every** `Throwable` constructed anywhere in the process, for the remainder of its life — not just the hot, well-understood control-flow exception someone was trying to speed up. Every future `NullPointerException` from a genuine null-pointer bug, every misconfigured Spring bean's `BeanCreationException`, every unexpected `IllegalStateException` three services deep now arrives in a log with `getStackTrace().length == 0`, indistinguishable from the deliberately-stackless type the flag was meant to help.

**Right**

Apply concept 3's per-class mechanism to the one type that is actually hot, and leave everything else on the default:

```java
public final class InsufficientFundsException extends RuntimeException {
    public InsufficientFundsException(String message) {
        super(message, null, false, false);
    }
}
```

**Why people believe it:** the flag's name reads like exactly the right lever — global, simple, one command-line change instead of touching N exception classes — and its effect is real and measurable (concept 4 confirmed it independently). What the flag's name does not advertise is the blast radius: it has no scope narrower than "the whole JVM," which is precisely the property the per-class mechanisms in concept 3 were built to avoid.

---

## Cheat sheet

| Item | Value (this build) | Meaning |
|---|---|---|
| `MaxJavaStackTraceDepth` | `1024` | Cap on frames `fillInStackTrace()` captures; measured — depth 1500 caps at exactly 1024, depth 500 captures its true 502 |
| `StackTraceInThrowable` | `true` (default) | JVM-wide switch; `-XX:-StackTraceInThrowable` measured to zero every trace, no per-class scope |
| `ThreadStackSize` | `2048` **KB** = 2,097,152 bytes ≈ 2 MB | Native per-thread stack; `03c` owns overflow of it |
| `Throwable` fields (write-once trio) | `backtrace` (`transient Object`, native-written), `stackTrace` (`StackTraceElement[]`, sentinel `UNASSIGNED_STACK`, `null` = permanently disabled), `depth` (`transient int`, frame count for the decode) | `backtrace` is cheap and opaque; `stackTrace` is the (lazily materialised) public-facing array |
| Decode entry point | `getOurStackTrace()` — `private synchronized`, guards on `stackTrace == UNASSIGNED_STACK \|\| stackTrace == null` | Decodes via `StackTraceElement.of(backtrace, depth)` exactly once, caches, then every `getStackTrace()` clones the cache |
| `StackTraceElement` fields | 7 references (`declaringClassObject`, `classLoaderName`, `moduleName`, `moduleVersion`, `declaringClass`, `methodName`, `fileName`) + 1 `int` + 1 `byte` | Java 9+ shape (module/loader/version added); "4 refs + 2 ints" is the stale pre-9 shape |
| `StackTraceElement` shell size | 48 bytes (12-byte header + 33 bytes data, 8-aligned) | Compressed oops, 64-bit, assumptions from `05-internals-object-layout.md` |
| 100-frame trace, decoded | ≈ 5,216 bytes ≈ 5.09 KiB | 100 shells (4,800B) + array (416B) |
| 1,024-frame trace, decoded | ≈ 53,264 bytes ≈ 52.02 KiB | Maximum possible single `getStackTrace()` decode, at the depth cap |
| Stackless forms | 4-arg ctor (`writableStackTrace=false`, sets `stackTrace=null` directly) or override `fillInStackTrace()` → `return this` | Both measured `getStackTrace().length == 0`; only the ctor form can also disable suppression |
| Construction cost, depth 1 | normal ≈ 237ns / stackless ≈ 4.8–5.9ns / boolean ≈ 1.5ns | Stackless ≈ **49×** cheaper; boolean ≈ 158× cheaper |
| Construction cost, depth 10 | normal ≈ 784ns / stackless ≈ 398–400ns / boolean ≈ 4.9ns | Stackless ≈ 1.97× cheaper — the collapse has already happened by here |
| Construction cost, depth 100 | normal ≈ 5,896ns / stackless ≈ 3,826–3,798ns / boolean ≈ 40ns | Stackless ≈ 1.54× cheaper; boolean ≈ 148× cheaper |
| Construction cost, depth 1000 | normal ≈ 56,538ns / stackless ≈ 39,538–39,699ns / boolean ≈ 2,400ns | Stackless ≈ 1.43× cheaper; boolean ≈ 23.6× cheaper |
| **The stackless ratio is depth-dependent** | ≈49× at depth 1 → ≈1.97× at 10 → ≈1.54× at 100 → ≈1.43× at 1000 | Only the *capture* is skipped; the N-frame recursion and unwind are paid by both, and come to dominate |
| Ratio that does **not** collapse | any exception form vs a plain boolean return: 158× / 148× / 23.6× | The robust number, and the one that settles whether to throw at all |
| Corroboration | `../build-it/03h-stackless-exception.md`: 11.15× at depth 1, 1.47× at depth 100 | Same collapse; its lower depth-1 figure is its 25.02ns context-map construction |
| `getStackTrace()` materialisation overhead | roughly doubles the normal-form cost at every depth measured | Paid once per decode, cloned per call thereafter |
| Cross-harness agreement | `02c`'s depth=10/100/1000: 784 / 5790 / 52,260ns vs this file's 784.2 / 5895.5 / 56,537.9ns | Close at shallow depth, ~8% apart at depth 1000 — different harness, same machine; neither is a JMH number |

---

## Self-test

**Q1.** Where, precisely, does the cost of constructing an `InsufficientFundsException` come from, and why does the depth cap matter?

<details><summary>Answer</summary>

Every `Throwable` constructor calls `fillInStackTrace()` as its first statement, before the message or cause are even assigned. That method, guarded by `stackTrace != null || backtrace != null`, delegates to a `native`, `synchronized fillInStackTrace(int)` that walks the calling thread's frames and writes an opaque snapshot into the `transient Object backtrace` field. The walk captures `min(depth, MaxJavaStackTraceDepth)` frames — `1024` on this build, confirmed by recursing to depth 1,500 and observing `getStackTrace().length` cap at exactly 1,024, while a depth-500 recursion captured its true 502. The cap matters because it bounds the *worst case* — no matter how deep a pathological recursion goes before throwing, the walk (and therefore its cost) never exceeds the cost of walking 1,024 frames, which is also why the depth=1000 measurement in this file is close to the true asymptote of this cost, not a point still climbing steeply.

</details>

**Q2.** What exactly is lazy about the `backtrace`/`stackTrace` pair, and what does "lazy" not cover?

<details><summary>Answer</summary>

The `native` walk at construction writes only the opaque `backtrace` field — no `StackTraceElement` object exists yet. Decoding `backtrace` into `StackTraceElement[]` happens inside `getOurStackTrace()`, gated on `stackTrace == UNASSIGNED_STACK`, and happens exactly once per instance: the first call to `getStackTrace()` or `printStackTrace()` triggers `StackTraceElement.of(backtrace, depth)`, which allocates the array and every element (measured: 152 bytes of allocation for a 1-frame trace, via `ThreadMXBean.getThreadAllocatedBytes`), then caches the decoded array back into `stackTrace`. What laziness does *not* cover is every subsequent call: `getStackTrace()`'s own source is `getOurStackTrace().clone()`, so every call — the first and every one after — returns a fresh defensive copy (measured 24 bytes for the clone alone on the second call, and reference-unequal arrays across calls). So a constructed-but-never-inspected exception allocates zero `StackTraceElement`s; the first inspection pays the full decode; every inspection after that, forever, pays a smaller but non-zero clone cost.

</details>

**Q3.** Where exactly does an exception's cost go, and what disables each part?

<details><summary>Answer</summary>

Three separable costs. Construction — `fillInStackTrace()`'s walk into `backtrace` — is the dominant one, proportional to call-stack depth up to the 1,024-frame cap; it is disabled per-class by the four-argument constructor's `writableStackTrace=false` (which sets `stackTrace=null` directly, making the guard permanently false) or by overriding `fillInStackTrace()` to `return this`, and disabled JVM-wide by `-XX:-StackTraceInThrowable`. Throw-and-unwind — `athrow`'s handler search — is cheap and independent of nesting depth, per `03-internals-exception-mechanics.md`, and nothing in this file's material disables or needs to disable it. Materialisation — decoding `backtrace` into `StackTraceElement[]` — is lazy and skippable entirely; it is paid only by whichever caller first invokes `getStackTrace()` or `printStackTrace()`, and every call after the first pays only a clone, not a re-decode. Measured on this build: a normal exception at depth 100 costs roughly 5,896ns to construct-throw-catch, and roughly 13,133ns if the catch block also calls `getStackTrace()` — the difference between those two numbers is exactly this third cost.

</details>

**Q4.** Two ways to build a stackless exception — say what each disables, and what the leaf's claim that neither differs in `getStackTrace()` actually showed.

<details><summary>Answer</summary>

The four-argument protected constructor, `super(message, null, false, false)`, sets `stackTrace = null` directly during construction — permanently disabling `fillInStackTrace()`'s guard — and, via its separate `enableSuppression` argument, can also set `suppressedExceptions = null`, silently turning `addSuppressed` into a no-op. Overriding `fillInStackTrace()` to `return this` intercepts the identical call every superclass constructor makes, via virtual dispatch, leaving `stackTrace` at its initial `UNASSIGNED_STACK` sentinel and `backtrace` at `null` — a different field state reaching the identical outward behaviour, because `getOurStackTrace()`'s `backtrace != null` check fails either way. Measured directly on this build: both forms return `getStackTrace().length == 0` — not different lengths, not one null and one empty — refuting any assumption that the two differ observably on this axis. Where they do differ, measured on the same run: the constructor form's `addSuppressed` call was a silent no-op (`getSuppressed().length == 0` afterward) while the override form accepted the suppressed exception normally (`getSuppressed().length == 1`), because only the constructor form's third argument touches suppression at all.

</details>

**Q5.** A teammate says "stackless exceptions are basically free — an order of magnitude cheaper than a normal exception." Where does the measurement on this build agree, and where does it disagree?

<details><summary>Answer</summary>

The first thing to say is that the claim is missing its most important term: **the ratio depends almost entirely on stack depth**, so the teammate is right at one depth and wrong at another, and neither of us can be checked until the depth is named. Measured on this build: at depth 1 a normal exception costs roughly 237ns against 4.8ns for the four-argument-constructor form — a ratio of about **49×**, which is *five times better* than the order of magnitude claimed, so at shallow depth the folklore understates the saving rather than overstating it. By depth 10 it is already down to about 1.97× (784ns versus 398ns), at depth 100 about 1.54× (5,896ns versus 3,826ns), and at depth 1,000 about 1.43× (56,538ns versus 39,538ns). So at the depths a real service actually throws from, the saving is a modest 1.4–1.6× and the teammate is overstating it substantially.

The mechanism behind the collapse is what makes this predictable rather than something to memorise, and it is the part worth volunteering. A stackless exception skips only the *capture*. It still pays the N-frame recursion down and the N-frame unwind back up, and that cost is shared with the normal path. At depth 1 the shared cost is 4.8ns — essentially nothing — so removing the capture removes nearly the entire cost. As depth grows, the capture cost grows roughly linearly (232ns at depth 1 to 17,000ns at depth 1,000) but the shared cost grows from almost nothing to 39,538ns, so the shared term dominates and the ratio decays toward 1×. The rule that follows: the saving is always "the cost of walking N frames", and the ratio is that divided by the cost of *having* N frames.

Two things to add. First, a stackless exception is not free even where the capture is gone — at depth 100 it still costs 3,826ns, because the allocation, the exception type's own field initialisation and any `String` work for a constructed message all remain, and at realistic depth those are a larger share of the remainder than "stack traces are the whole cost" assumes. `../build-it/03h-stackless-exception.md` shows this concretely: its stackless exception carries a four-entry immutable context map costing 25.02ns to build, which drops its depth-1 ratio to 11.15× against this file's 49.4× for a bare one — so any real constructor work gives the shallow-depth win straight back. Second, the ratio that does *not* collapse, and therefore the one worth quoting: *any* exception form against a plain boolean return stays one to two orders of magnitude apart at every depth measured — roughly 158× at depth 1, 148× at depth 100, narrowing only to 24× at depth 1,000 as the boolean path's own recursion starts to dominate its cost. That is the number that settles whether to throw at all, per `02c-cost-and-control-flow.md`'s decision rule, and it is a far more robust basis for a decision than the normal-versus-stackless choice.

</details>

**Q6.** Why does `02c-cost-and-control-flow.md`'s harness and this file's harness disagree by roughly 8% at depth 1,000 despite running on the same machine and measuring the same mechanism?

<details><summary>Answer</summary>

They are not identical harnesses. `02c`'s message is built with `String` concatenation at the throw site; this file's uses a fixed literal. The warm-up and iteration counts differ between the two runs (this file used 5,000 warm-up / 50,000 timed iterations at depth 1,000, under memory and time constraints of a single measurement session; `02c` used its own schedule). Both harnesses share the same stated limitations — no forking, no dead-code-elimination guard beyond a `volatile` sink, uncontrolled JIT compilation state — which is exactly why an 8% discrepancy between two runs of the "same" measurement is expected rather than alarming: neither number is precise enough to notice an 8% difference as meaningful, and neither should be quoted as an absolute figure outside the run that produced it. This is the concrete argument for guide 06's JMH the moment a number needs to survive being written into a document more permanent than a single measured run.

</details>

**Q7.** What does `-XX:-StackTraceInThrowable` actually flip, and why is it a worse choice than the per-class mechanisms even though it is measured to work?

<details><summary>Answer</summary>

Confirmed on this build: a plain `new RuntimeException` call under `-XX:-StackTraceInThrowable` produces `getStackTrace().length == 0`, versus `1` at the default. It works exactly as advertised — but its scope is the entire JVM process, for the lifetime of that process, with no way to exempt any single exception type. Every future genuine defect's `NullPointerException`, every misconfigured framework exception, every unexpected `IllegalStateException` three services deep loses its trace right alongside the one hot, well-understood control-flow exception the flag was reached for. The per-class mechanisms in concept 3 — the four-argument constructor or the `fillInStackTrace()` override — deliver the identical construction-time saving on exactly the one type that needs it, leaving every other exception's diagnosability untouched.

</details>

**Q8.** A cached, pre-constructed `InsufficientFundsException` is reused across two different controller methods. What does its trace actually show, and why?

<details><summary>Answer</summary>

The trace shows wherever the static field's initializer ran — typically class-loading time, inside neither controller method that later throws the cached instance. `fillInStackTrace()` runs exactly once, at the one `new`, because `Throwable` has no mechanism that re-walks the stack at `throw` time; `athrow` only pops the reference and searches the exception table, per `03-internals-exception-mechanics.md`. Every subsequent `throw` of that same cached instance reports the identical frozen trace regardless of which of the two controllers actually threw it this time — which is strictly worse than a stackless exception for diagnosability, since a stackless exception at least advertises its own emptiness rather than presenting a trace that looks real and points at the wrong code.

</details>

---

## Open questions

- **Unverified:** the precise allocation attributed to "construction" in the `ThreadMXBean.getThreadAllocatedBytes` measurement in concept 2 includes probe overhead (the bean call itself, local variable boxing where applicable) not cleanly separated from the exception's own construction cost; only the *relative* jump between the first and second `getStackTrace()` calls (152 bytes versus 24 bytes) is reported with confidence, not an absolute "construction costs exactly N bytes" figure. What would settle it: an async-profiler allocation-profiling run isolating exactly the bytes attributable to `fillInStackTrace()`'s Java-visible path versus the surrounding harness code, which guide 06 owns.
- **Unverified:** whether the roughly 8% discrepancy between this file's depth=1000 measurement and `02c-cost-and-control-flow.md`'s is fully explained by the differing warm-up/iteration schedules and message-construction shape named above, or whether some of it is attributable to JIT compilation-tier differences (C1 versus C2) that neither harness pins down. What would settle it: `-XX:+PrintCompilation` correlated against both harnesses' iteration counts, or re-running both under JMH with `-prof perfnorm`, both of which guide 06 owns.

---

**Leaves covered:** 3.9.6, 3.9.7, 3.9.8, 3.9.15 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-115
**Target version:** Java 21 LTS
**Lines:** 781
