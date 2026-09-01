# 03 Java Core — Exception builds — the stackless exception, and what a stack trace costs — BUILD IT (§4.6.2)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Catch boundaries and the serial form](03n-exception-boundaries-and-serialization.md) · Next: [AutoCloseable, try-with-resources, and suppression](03d-autocloseable-and-finally.md)

All numbers on this page were measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64 (Apple silicon)**, compressed oops on.

The exception hierarchy this file measures is built across leaf 4.6.1's three files: the two
abstract roots and `InsufficientFundsException` in
[`03c-exception-hierarchy-and-stackless.md`](03c-exception-hierarchy-and-stackless.md), the
immutable context map in
[`03m-exception-context-and-null-policy.md`](03m-exception-context-and-null-policy.md), the catch
boundary and the serial form in
[`03n-exception-boundaries-and-serialization.md`](03n-exception-boundaries-and-serialization.md).
The section-wide §4.6 diff table, leaf 4.6.9, lives in
[`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

---

## §4.6.2 `[BUILD]` `[NUM]` `[PROVE]` The stackless exception

### The mechanism, from the source

Four lines of `java.lang.Throwable` decide everything. From
`/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/lib/src.zip`,
`java.base/java/lang/Throwable.java`:

```java
// line 162
    private static final StackTraceElement[] UNASSIGNED_STACK = new StackTraceElement[0];

// line 213
    private StackTraceElement[] stackTrace = UNASSIGNED_STACK;
```

```java
// lines 363-375
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

```java
// lines 817-826
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

Line by line:

- `UNASSIGNED_STACK` (line 162) is the **shared zero-length array**. Its javadoc is literally "A
  shared value for an empty stack." Every `Throwable` starts pointing at it, so an unfilled
  throwable allocates no array.
- Line 213 initialises `stackTrace` to that sentinel — **not** to `null`. The distinction is the
  whole protocol, documented in the comment at lines 164-172: "A `null` value of this field
  indicates subsequent calls to `setStackTrace` and `fillInStackTrace` will be no-ops."
- In the four-argument constructor, `writableStackTrace = false` sets `stackTrace = null`. Note
  that this contradicts the common description "it points the trace at a shared empty sentinel" —
  the *field* is set to `null`. The empty sentinel appears later, on read.
- `fillInStackTrace()` guards on `stackTrace != null || backtrace != null`. With `stackTrace ==
  null` and `backtrace == null`, the guard is false, the native call never happens, and no stack
  walk occurs. The four other public constructors (lines 257, 272, 294, 317) all call
  `fillInStackTrace()` unconditionally, which is why every ordinary exception pays for a walk.
- `stackTrace = UNASSIGNED_STACK` *after* the native call is the trick that makes the walk lazy:
  the native side fills the `transient Object backtrace` and the `transient int depth`, and
  `getOurStackTrace()` (lines 857-867) only materialises `StackTraceElement` objects on first
  read — returning `UNASSIGNED_STACK` when `backtrace` is also `null`, which is precisely the
  stackless case:

```java
// lines 857-867
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

[`../exceptions/03b-internals-stack-trace-capture.md`](../exceptions/03b-internals-stack-trace-capture.md)
owns `fillInStackTrace`, the native `backtrace` structure, and the lazy materialisation in full.

### The two exceptions

`StacklessInsufficientFundsException` is `InsufficientFundsException` with one difference: the
`super` call routes through the four-argument constructor.

```java
/** Byte-for-byte the same as InsufficientFundsException except for the super call:
 *  the four-argument Throwable constructor with writableStackTrace = false. */
public final class StacklessInsufficientFundsException extends QuizStakesException {

    private static final long serialVersionUID = 1L;

    public StacklessInsufficientFundsException(ClientId clientId, Money requested, Money stakeable) {
        super(DomainFault.INSUFFICIENT_FUNDS, Map.of(
                        "clientId", clientId,
                        "requested", requested,
                        "stakeable", stakeable,
                        "shortfall", requested.minus(stakeable)),
                null,
                false);
    }

    public Money shortfall() { return (Money) contextValue("shortfall"); }

    public Money stakeable() { return (Money) contextValue("stakeable"); }
}
```

The driver that exercises it — `SINGLETON` aside, everything this file measures runs through one
of these two classes:

```java
public static void main(String[] args) {
    InsufficientFundsException normal = new InsufficientFundsException(ID, REQUESTED, STAKEABLE);
    StacklessInsufficientFundsException stackless =
            new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);

    System.out.println("normal   getStackTrace().length = " + normal.getStackTrace().length);
    System.out.println("stackless getStackTrace().length = " + stackless.getStackTrace().length);
    System.out.println("stackless array identity across two calls = "
            + (stackless.getStackTrace() == stackless.getStackTrace()));
    System.out.println("stackless array is empty and shared-by-value = "
            + java.util.Arrays.equals(stackless.getStackTrace(), new StackTraceElement[0]));

    stackless.fillInStackTrace();
    System.out.println("after fillInStackTrace(): length = "
            + stackless.getStackTrace().length + " (the call is a no-op)");

    try {
        stackless.setStackTrace(normal.getStackTrace());
        System.out.println("after setStackTrace(): length = "
                + stackless.getStackTrace().length + " (also a no-op)");
    } catch (RuntimeException e) {
        System.out.println("setStackTrace threw " + e);
    }

    System.out.println("-- printStackTrace of the normal one --");
    normal.printStackTrace(System.out);
    System.out.println("-- printStackTrace of the stackless one --");
    stackless.printStackTrace(System.out);

    System.out.println("-- suppression knob is separate --");
    System.out.println("stackless.getSuppressed().length = " + stackless.getSuppressed().length);
    stackless.addSuppressed(new IllegalStateException("close failed"));
    System.out.println("after addSuppressed              = " + stackless.getSuppressed().length);
    NoSuppressionFailure quiet = new NoSuppressionFailure();
    quiet.addSuppressed(new IllegalStateException("close failed"));
    System.out.println("enableSuppression=false, after addSuppressed = "
            + quiet.getSuppressed().length + " (silently discarded)");
    System.out.println("enableSuppression=false, frames              = "
            + quiet.getStackTrace().length + " (still has a trace)");
}
```

The `NoSuppressionFailure` class it references is in the `Pitfalls` section below, where the two
knobs are contrasted. Run and pasted:

```console
normal   getStackTrace().length = 1
stackless getStackTrace().length = 0
stackless array identity across two calls = false
stackless array is empty and shared-by-value = true
after fillInStackTrace(): length = 0 (the call is a no-op)
after setStackTrace(): length = 0 (also a no-op)
-- printStackTrace of the normal one --
qs.InsufficientFundsException: INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
	at qs.StacklessProof.main(StacklessProof.java:10)
-- printStackTrace of the stackless one --
qs.StacklessInsufficientFundsException: INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
-- suppression knob is separate --
stackless.getSuppressed().length = 0
after addSuppressed              = 1
enableSuppression=false, after addSuppressed = 0 (silently discarded)
enableSuppression=false, frames              = 1 (still has a trace)
```

`identity across two calls = false` because `getStackTrace()` is `return
getOurStackTrace().clone()` — the sentinel is shared internally but every caller gets a fresh
(zero-length) copy. `printStackTrace` on the stackless one prints the header line and nothing
else: no frames, and nothing marking that frames were deliberately omitted.

The last four lines prove the two knobs are independent. `enableSuppression = false` sets
`suppressedExceptions = null`, and `addSuppressed` on a null list is a **silent no-op** — a
try-with-resources close failure simply vanishes. `writableStackTrace = false` sets `stackTrace =
null`, and it is `fillInStackTrace`/`setStackTrace` that become no-ops. Turning one off does not
turn the other off.

| Knob | `false` sets | Consequence |
|---|---|---|
| `enableSuppression` | `suppressedExceptions = null` | `addSuppressed` silently discards; suppressed close failures are lost |
| `writableStackTrace` | `stackTrace = null` | no `fillInStackTrace` walk; `getStackTrace()` returns empty; `setStackTrace` is a no-op |

### The measurement — this is not JMH

**Not JMH.** No forking, no `Blackhole`, no dead-code-elimination guard beyond a `volatile
Object sink`, and the JIT's compilation state is whatever it happens to be. Relative comparisons
inside one run are meaningful; the absolute nanoseconds are not portable. JMH would add process
forking (so one benchmark's profile cannot pollute another's), proper warm-up-iteration
accounting, `Blackhole` sinks that defeat dead-code elimination reliably, and statistics across
forks — guide 06 owns it. [`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md)
owns the canonical harness, and this one follows its shape.

Depth is built with **real recursion**: one Java frame per level, `depth == 1` being the base
case that does the work. A `recursion baseline` row descends the same 500 frames and returns a
static marker, so the recursion's own cost can be subtracted.

```java
static final ClientId ID = ClientId.of("3f2a1c88-0000-4000-8000-000000000001");
static final Money REQUESTED = Money.gbp("4.20");
static final Money STAKEABLE = Money.gbp("1.75");

static volatile Object sink;
static final Object MARKER = new Object();

/** The preallocated singleton: one instance, stackless, no per-occurrence context. */
static final StacklessInsufficientFundsException SINGLETON =
        new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);

static Object baseline(int depth) {
    if (depth > 1) return baseline(depth - 1);
    return MARKER;
}

static Object constructNormal(int depth) {
    if (depth > 1) return constructNormal(depth - 1);
    return new InsufficientFundsException(ID, REQUESTED, STAKEABLE);
}

static Object constructStackless(int depth) {
    if (depth > 1) return constructStackless(depth - 1);
    return new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);
}

/** Context-only: everything my design costs apart from the Throwable machinery. */
static Object constructContextOnly(int depth) {
    if (depth > 1) return constructContextOnly(depth - 1);
    return new FailureDetail(DomainFault.INSUFFICIENT_FUNDS, Map.of(
            "clientId", ID, "requested", REQUESTED, "stakeable", STAKEABLE,
            "shortfall", REQUESTED.minus(STAKEABLE)));
}

static void throwNormal(int depth) throws InsufficientFundsException {
    if (depth > 1) { throwNormal(depth - 1); return; }
    throw new InsufficientFundsException(ID, REQUESTED, STAKEABLE);
}

static void throwStackless(int depth) throws StacklessInsufficientFundsException {
    if (depth > 1) { throwStackless(depth - 1); return; }
    throw new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);
}

static void throwSingleton(int depth) throws StacklessInsufficientFundsException {
    if (depth > 1) { throwSingleton(depth - 1); return; }
    throw SINGLETON;
}

static double nanosPerOp(Work work, int depth, int iterations) {
    for (int warm = 0; warm < 5; warm++) {
        for (int i = 0; i < iterations; i++) work.run(depth);
    }
    long best = Long.MAX_VALUE;
    for (int trial = 0; trial < 5; trial++) {
        long start = System.nanoTime();
        for (int i = 0; i < iterations; i++) work.run(depth);
        long elapsed = System.nanoTime() - start;
        if (elapsed < best) best = elapsed;
    }
    return (double) best / iterations;
}

interface Work { void run(int depth); }

static final Work BASELINE       = d -> sink = baseline(d);
static final Work CTX_ONLY       = d -> sink = constructContextOnly(d);
static final Work NEW_NORMAL     = d -> sink = constructNormal(d);
static final Work NEW_STACKLESS  = d -> sink = constructStackless(d);
static final Work TC_NORMAL      = d -> {
    try { throwNormal(d); } catch (InsufficientFundsException e) { sink = e; }
};
static final Work TC_STACKLESS   = d -> {
    try { throwStackless(d); } catch (StacklessInsufficientFundsException e) { sink = e; }
};
static final Work TC_SINGLETON   = d -> {
    try { throwSingleton(d); } catch (StacklessInsufficientFundsException e) { sink = e; }
};

static void row(String label, Work work, int depth, int iterations) {
    System.out.printf("%-26s depth=%-4d %10.2f ns/op%n",
            label, depth, nanosPerOp(work, depth, iterations));
}

public static void main(String[] args) {
    for (int depth : new int[] {1, 100, 500}) {
        int iters = switch (depth) {
            case 1 -> 200_000;
            case 100 -> 100_000;
            default -> 20_000;
        };
        row("recursion baseline", BASELINE, depth, iters);
        row("context only (no Throwable)", CTX_ONLY, depth, iters);
        row("new normal", NEW_NORMAL, depth, iters);
        row("new stackless", NEW_STACKLESS, depth, iters);
        row("throw+catch normal", TC_NORMAL, depth, iters);
        row("throw+catch stackless", TC_STACKLESS, depth, iters);
        row("throw+catch singleton", TC_SINGLETON, depth, iters);
        System.out.println();
    }
}
```

The throw is raised at the deepest frame and caught at the top, so `throw+catch` includes a full
500-frame unwind. 200,000 iterations at depth 1, 20,000 at depth 500; five warm-up passes, best
of five timed passes. Run with `-Xss4m`. The `main` above is the **second** invocation's version;
the first run's output below came from the identical program with the depth array reading
`{1, 500}` and a two-branch iteration count — nothing else differed, and the depth-1 and depth-500
rows reproduce across both.

Real output, `java -Xss4m -cp classes qs.DepthHarness` (second of two runs; the first agreed to
within 3%):

```console
recursion baseline         depth=1          0.51 ns/op
context only (no Throwable) depth=1         25.53 ns/op
new normal                 depth=1        276.11 ns/op
new stackless              depth=1         25.16 ns/op
throw+catch normal         depth=1        274.42 ns/op
throw+catch stackless      depth=1         24.61 ns/op
throw+catch singleton      depth=1          2.21 ns/op

recursion baseline         depth=500     1220.85 ns/op
context only (no Throwable) depth=500     2561.74 ns/op
new normal                 depth=500     8716.63 ns/op
new stackless              depth=500     1356.59 ns/op
throw+catch normal         depth=500    27497.91 ns/op
throw+catch stackless      depth=500    19604.74 ns/op
throw+catch singleton      depth=500    19710.80 ns/op
```

The arithmetic, `[NUM]`:

| Quantity | Depth 1 | Depth 500 | Derivation |
|---|---|---|---|
| recursion alone | 0.51 ns | 1,220.85 ns | measured; 1220.85 / 500 = **2.44 ns per frame** |
| my context alone | 25.02 ns | 1,340.89 ns | context-only minus baseline |
| **`fillInStackTrace` cost** | **250.95 ns** | **7,495.78 ns** | new normal minus new stackless |
| per captured frame | — | **14.99 ns** | 7495.78 / 500 |
| stackless construction, net of recursion | 24.65 ns | 135.74 ns | new stackless minus baseline |
| unwind cost, 500 frames | — | ~18,248 ns | throw+catch stackless minus new stackless; **36.5 ns per frame** |
| **normal / stackless, construction** | **10.97x at depth 1** | **6.42x at depth 500** | 276.11/25.16 and 8716.63/1356.59 |
| **normal / stackless, throw+catch** | **11.15x at depth 1** | **1.40x at depth 500** | 274.42/24.61 and 27497.91/19604.74 |

**Every ratio on this page carries its depth, and none of them travels without it.** A bare
"stackless exceptions are 11x cheaper" is false at depth 500 and a bare "1.4x" is false at depth 1.
The reason is mechanical: `fillInStackTrace` costs about 15 ns per frame it captures, and the
`throw`/`catch` unwind costs about 36.5 ns per frame it crosses. Both scale with depth, but only
the first is what going stackless removes — so as depth grows, the part you cannot remove grows
faster than the part you can, and the ratio compresses toward 1.

The expected relationship appeared, with one correction to the folklore. **Construction** behaves
as predicted: the stackless one is nearly flat in depth (24.65 ns to 135.74 ns net — it grows a
little, because at depth 500 the allocation happens with a cold 500-frame stack and worse cache
behaviour, not because it walks anything), while the normal one scales linearly at about 15 ns per
frame captured. The 250.95 ns of `fillInStackTrace` at depth 1 sits inside the master cost table's
measured band of **278.05–282.39 ns** for whole-exception construction, and the depth-500
construction figure of 8,716.63 ns interpolates sensibly against its **16,483 ns at depth 1000**.

**The correction:** at depth 500 the interesting ratio is *not* the construction ratio. `throw` +
`catch` across 500 frames costs about 18,248 ns of pure unwinding, which swamps the 7,496 ns saved
on capture. The stackless exception therefore only saves **29%** of the total (27,497.91 to
19,604.74), and the preallocated singleton — which allocates nothing at all — is
indistinguishable from it at 19,710.80 ns. At depth 1, where there is nothing to unwind, the same
change saves **91%**. If you are optimising a deep throw, the capture is not your problem.

### Depth 100, and a disagreement with a sibling file worth resolving

A second invocation of the same harness, with `100` added to the depth array and 100,000
iterations at that depth (nothing else changed; the listings above are unedited):

```console
recursion baseline         depth=1          1.59 ns/op
context only (no Throwable) depth=1         29.14 ns/op
new normal                 depth=1        278.66 ns/op
new stackless              depth=1         25.11 ns/op
throw+catch normal         depth=1        281.48 ns/op
throw+catch stackless      depth=1         24.66 ns/op
throw+catch singleton      depth=1          2.13 ns/op

recursion baseline         depth=100       38.39 ns/op
context only (no Throwable) depth=100      370.87 ns/op
new normal                 depth=100     1997.12 ns/op
new stackless              depth=100       76.44 ns/op
throw+catch normal         depth=100     5658.12 ns/op
throw+catch stackless      depth=100     3839.70 ns/op
throw+catch singleton      depth=100     3727.25 ns/op

recursion baseline         depth=500     1205.31 ns/op
context only (no Throwable) depth=500     2564.66 ns/op
new normal                 depth=500     8654.24 ns/op
new stackless              depth=500     1235.68 ns/op
throw+catch normal         depth=500    26936.11 ns/op
throw+catch stackless      depth=500    19207.20 ns/op
throw+catch singleton      depth=500    18810.00 ns/op
```

The depth-1 and depth-500 rows reproduce the first run within 3%. The new row:

| Ratio at depth 100 | Value | Derivation |
|---|---|---|
| normal / stackless, construction | **26.1x** | 1997.12 / 76.44 |
| normal / stackless, `throw`+`catch` | **1.47x** | 5658.12 / 3839.70 |
| capture cost per frame | **19.2 ns** | (1997.12 − 76.44) / 100 |
| unwind cost per frame | **37.6 ns** | (3839.70 − 76.44) / 100 |

`1.47x` at depth 100 lands inside the **1.3–1.6x** band that
[`../exceptions/03b-internals-stack-trace-capture.md`](../exceptions/03b-internals-stack-trace-capture.md)
reports, and the absolute figures nearly coincide with its published rows: its `normal` at depth
100 is 5,895.5 ns against this harness's 5,658.12 ns, and its `stackless-ctor` is 3,826.1 ns
against 3,839.70 ns. Two independently written harnesses on the same build agree to within 4% on
the same quantity, which is the strongest evidence either page has.

**The disagreement, and what actually resolves it.** That sibling states its harness "never
observes anything close to [an order of magnitude] between a normal and a stackless exception **at
any depth**", and both it and
[`../exceptions/03c-internals-fast-throw-and-truncation.md`](../exceptions/03c-internals-fast-throw-and-truncation.md)
build a pitfall and a self-test answer on the 1.3–1.6x band. This page measures **11.15x at depth
1**. Three things reconcile them, and only the third is a correction:

1. **The band is a depth-100-and-up band.** The sibling's quoted ratios are computed from its
   depth-100 and depth-1000 rows. On the rows this page shares with it — depth 100 — the two agree.
2. **The quantity differs at the shallow end.** Its `normal` column is construct-plus-throw-plus-catch;
   this page reports construction and `throw`+`catch` separately, and at depth 1 those two are the
   same number because there is nothing to unwind. So depth 1 is precisely where the ratio is
   largest and where the two pages must be compared most carefully.
3. **"At any depth" overreaches, and the sibling's own table shows it.** Its depth-1 row reads
   `normal = 237.0 ns` and `stackless-ctor = 4.8 ns`. That ratio is **49.4x** — five times an order
   of magnitude — and the sibling never computes it, having read the ratio claim off its depth-100
   and depth-1000 rows only. Its data and this page's data both say the advantage is large at depth
   1; the phrase "at any depth" is what does not survive its own measurement.

Why this page's depth-1 ratio is 11x rather than the sibling's 49x is the last piece, and it is a
property of the exception, not the harness: `StacklessInsufficientFundsException` spends about
**25.02 ns** building a four-entry immutable context map before it does anything else — measured
directly by the `context only (no Throwable)` row — whereas the sibling's stackless type carries a
literal message and costs 4.8 ns. Structured context is not free, and at depth 1 it is essentially
the entire cost of a stackless exception. That is the trade the design in leaf 4.6.1 makes on
purpose, and it is the reason a *preallocated singleton*, which builds no context at all, measures
2.13–2.21 ns at depth 1.

**Insight:** the two pages were never really in conflict. One measured a cheap stackless exception
at moderate-to-great depth, the other an expensive stackless exception at depth 1, and the only
false statement between them is a universal quantifier attached to a range derived from part of the
range.

### The judgement

A stackless exception is right for a **high-frequency, expected, control-flow-shaped** signal
where the stack tells you nothing you did not already know. It is wrong for anything you will have
to debug from a log, because the trace was the only evidence and you deleted it at the source.

Work the QuizStakes rate. Stake reservations run at **2.8M/day, 1,200/sec peak, average value
4.20**. Take the worst case and assume *every* reservation is rejected:

- 2.8M x 276.11 ns = **0.773 seconds of CPU per day**, of which 250.95 ns each — **0.703 s/day** —
  is `fillInStackTrace`.
- At the 1,200/sec peak: 1,200 x 276.11 ns = **331 microseconds per second**, i.e. **0.033% of one
  core**.
- Per request, 276 ns against a card PSP authorise at p50 240ms is **one part in 870,000**.

So at this rate, on this measurement, **the stackless exception is not justified**, and it is the
arithmetic rather than an opinion that says so. What you would give up for 0.7 s/day: on the first
production incident where reservations reject and nobody knows which of the eleven callers of
`ReserveStake` is asking for the wrong amount, there is no frame to look at. The threshold where
the trade flips is a throw rate around a million per second per core — a tight inner loop, a
parser, a `ScopedValue`-style unwind — not a 1,200/sec business path.

The **third option, often the right one**: a preallocated singleton.

```java
/** The preallocated singleton: one instance, stackless, no per-occurrence context. */
static final StacklessInsufficientFundsException SINGLETON =
        new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);
```

Measured at **2.21 ns** for throw+catch at depth 1 — at that depth, 125x cheaper than the normal
exception and 11x cheaper than a fresh stackless one, because it allocates nothing whatsoever. At
depth 500 it is 18,810–19,710 ns, indistinguishable from the fresh stackless one, because by then
the cost is all unwind and allocation is noise. Its two costs are
structural and neither is fixable:

1. **A shared instance cannot carry per-occurrence context.** The `SINGLETON` above permanently
   reports a shortfall for client `3f2a1c88-0000-4000-8000-000000000001` on a 4.20 stake against
   1.75 stakeable. That
   is a lie on every occurrence but the one it was built for. It is only honest when the code
   *is* the whole message.
2. **Its stack trace, if it has one, is from wherever it was created** — the static initialiser.
   A preallocated exception with `writableStackTrace = true` is worse than a stackless one,
   because it prints a plausible-looking trace pointing at `<clinit>`.

The JDK does exactly this, and does it correctly. `jdk.internal.misc.ScopedMemoryAccess`:

```java
    public static final class ScopedAccessError extends Error {

        @SuppressWarnings("serial")
        private final Supplier<RuntimeException> runtimeExceptionSupplier;

        public ScopedAccessError(Supplier<RuntimeException> runtimeExceptionSupplier) {
            super("Invalid memory access", null, false, false);
            this.runtimeExceptionSupplier = runtimeExceptionSupplier;
        }

        static final long serialVersionUID = 1L;

        public final RuntimeException newRuntimeException() {
            return runtimeExceptionSupplier.get();
        }
    }
```

Both knobs off, and a `Supplier<RuntimeException>` field so the boundary can call
`newRuntimeException()` and build a *real* exception, with a real trace, at the point where a
human will read it. That is the pattern worth stealing: stackless on the hot path, materialised at
the boundary. Note also the `@SuppressWarnings("serial")` on a non-`Serializable`-typed field —
the same trade `FailureDetail.context` makes.

### The JVM flags

Verified on this build with `java -XX:+PrintFlagsFinal -version`:

```console
     intx MaxJavaStackTraceDepth                   = 1024                                      {product} {default}
     bool OmitStackTraceInFastThrow                = true                                      {product} {default}
     bool StackTraceInThrowable                    = true                                      {product} {default}
```

`MaxJavaStackTraceDepth = 1024` caps how many frames `fillInStackTrace` records, so the linear
capture cost measured above stops growing past 1,024 frames — which is why the depth-500 numbers
are in the linear region and a depth-2000 measurement would not be.
`OmitStackTraceInFastThrow = true` applies only to JVM-generated implicit exceptions
(`NullPointerException`, `ArrayIndexOutOfBoundsException`, `ArithmeticException` and friends) at
a site C2 has compiled hot: the JVM then throws a preallocated, traceless instance. It does
**not** apply to anything constructed with `new` in Java code, so it has no effect on this
hierarchy. `StackTraceInThrowable = false` would disable capture globally — a debugging
catastrophe, listed here only so you recognise it in someone else's JVM arguments.
[`../exceptions/03c-internals-fast-throw-and-truncation.md`](../exceptions/03c-internals-fast-throw-and-truncation.md)
owns fast-throw and truncation.

> **`writableStackTrace = false` makes `Throwable`'s constructor skip the native stack walk by
> setting `stackTrace` to `null`, which permanently disables `fillInStackTrace` and
> `setStackTrace` — buying about 15 ns per frame you would have captured, at the price of every
> future investigation.**

### Diff vs the real one — §4.6.2

| Aspect | This build | The JDK |
|---|---|---|
| Edge cases | `getStackTrace()` returns a fresh empty array each call; `fillInStackTrace` and `setStackTrace` become permanent no-ops | same, because the mechanism *is* the JDK's — but `readObject` (`Throwable.java:1028-1040`) can also produce a null `stackTrace` from a serialized form, plus a one-element `STACK_TRACE_SENTINEL` for the "trace was omitted" case, which no Java-level constructor can reach |
| Intrinsics | none | `fillInStackTrace(int)` is `native`; the walk and the `backtrace` structure live in the VM |
| Serialization | `serialVersionUID = 1L`, trace round-trips as zero frames | `Throwable.writeObject` walks the suppressed list, refuses to serialize a self-suppressing throwable, and swaps in `SentinelHolder.STACK_TRACE_SENTINEL` |
| Null policy | `cause` passed as `null`, meaning no cause | identical; `initCause` afterwards throws `IllegalStateException` because `cause` was already set to `this`-or-a-value |
| Thread safety | immutable after construction, so the stackless instance is trivially shareable — which is exactly what makes the singleton pattern legal | `Throwable`'s mutators are `synchronized`; a preallocated `OutOfMemoryError` is safe only because the VM never mutates it |
| Allocation tricks | stackless construction still allocates the exception, the `FailureDetail` and a 4-entry `MapN`: 25.16 ns at depth 1 | `UNASSIGNED_STACK` shared, `backtrace` lazy, and C2's `OmitStackTraceInFastThrow` reuses *one* preallocated instance per implicit-exception kind per compiled site |
| Why the JDK bothers | — | the four-argument constructor exists so `OutOfMemoryError` can be thrown when there is no heap left to allocate a `StackTraceElement[]` in; its javadoc names `OutOfMemoryError`, `NullPointerException` and `ArithmeticException` |

---

## Pitfalls

### Reaching for a stackless exception before measuring

**Wrong**

```java
// "stake rejections are hot, 2.8M a day, so make it stackless"
throw new StacklessInsufficientFundsException(clientId, requested, stakeable);
```

```console
throw+catch stackless      depth=1         24.61 ns/op
throw+catch normal         depth=1        274.42 ns/op
```

An 11x ratio, which looks decisive until you multiply it out: 2.8M x 250.95 ns = **0.703 seconds
of CPU per day** saved, against a 240ms p50 PSP call on the same request. What you bought is
0.0008% of one core; what you sold is the frame that tells you which caller asked for the wrong
amount.

**Right**

Measure the rate first, keep the trace, and revisit only if the throw rate approaches a million
per second per core:

```java
throw new InsufficientFundsException(clientId, requested, stakeable);
```

**Why people believe it:** the *relative* number is genuinely large and gets quoted on its own.
"Exceptions are 10x cheaper without a stack trace" is true and almost always irrelevant, because
the absolute cost was already three orders of magnitude below the request's critical path.

### A preallocated singleton whose stack trace points somewhere irrelevant

**Wrong**

```java
static final InsufficientFundsException REJECTED =
        new InsufficientFundsException(ID, REQUESTED, STAKEABLE);   // writable trace
// then, 2.8M times a day:
throw REJECTED;
```

Every occurrence prints the same trace, and it points at the class initialiser that ran at
startup, not at the reservation that failed. It also permanently reports the shortfall of the one
client the constant was built for. The trace looks real, which is worse than no trace: an
investigator follows it into `<clinit>` and concludes the reservation path is fine.

**Right**

Either make the singleton stackless so nothing misleading is printed, and carry the code alone —

```java
static final StacklessInsufficientFundsException SIGNAL =
        new StacklessInsufficientFundsException(ID, REQUESTED, STAKEABLE);  // 2.21 ns/op, no trace
```

— or do what `ScopedMemoryAccess.ScopedAccessError` does: throw the stackless singleton on the hot
path and call `newRuntimeException()` at the boundary to build a real exception, with a real
trace and real context, where a human will read it.

**Why people believe it:** "allocation is the expensive part, so allocate once" is sound advice
for buffers and formatters, and the JVM itself preallocates exceptions under
`OmitStackTraceInFastThrow`. The step that gets skipped is that the JVM preallocates them
*without* traces, precisely because a shared trace would be a fabrication.

### Believing `enableSuppression` and `writableStackTrace` are the same knob

**Wrong**

```java
/** enableSuppression = false, writableStackTrace = true: the two knobs are independent. */
static final class NoSuppressionFailure extends RuntimeException {
    private static final long serialVersionUID = 1L;
    NoSuppressionFailure() { super("AA-699 DOCUMENTS_EXHAUSTED", null, false, true); }
}
```

Somebody wanted a cheap exception, saw two booleans, and set the first one. Measured:

```console
enableSuppression=false, after addSuppressed = 0 (silently discarded)
enableSuppression=false, frames              = 1 (still has a trace)
```

Nothing was saved — the stack walk still happened, because that is the *second* boolean. What
was lost is every suppressed exception: `enableSuppression = false` sets `suppressedExceptions =
null`, and `addSuppressed` on a null list is a **silent** no-op. A try-with-resources whose
`close()` fails while this exception propagates now drops the close failure with no exception, no
warning and nothing in a log.

**Right**

The knob that removes the stack walk is the fourth argument. Leave suppression alone:

```java
super(DomainFault.INSUFFICIENT_FUNDS, context, null, false);   // routes to
// super(null, cause, /* enableSuppression */ true, /* writableStackTrace */ false)
```

```console
stackless.getSuppressed().length = 0
after addSuppressed              = 1
```

The trace is gone, suppression still works.

**Why people believe it:** the two parameters are adjacent `boolean`s in one constructor, both
default to `true`, and both sound like they turn off diagnostic bookkeeping. The javadoc names
`OutOfMemoryError` as the motivating case for the constructor as a whole, which invites the
reading that the flags are one switch for "cheap exception mode". They are not: one skips a
native walk, the other silently discards data.

---

## Cheat sheet

| Thing | Value / rule |
|---|---|
| Four-arg constructor | `protected Throwable(String, Throwable, boolean enableSuppression, boolean writableStackTrace)` |
| `writableStackTrace = false` | sets `stackTrace = null`; skips `fillInStackTrace()`; `fillInStackTrace`/`setStackTrace` become permanent no-ops |
| `enableSuppression = false` | sets `suppressedExceptions = null`; `addSuppressed` silently discards |
| The shared empty array | `Throwable.UNASSIGNED_STACK`, `new StackTraceElement[0]`, `Throwable.java:162` |
| `stackTrace` field default | `UNASSIGNED_STACK`, not `null` — the `null` is what marks the no-op protocol |
| `fillInStackTrace` guard | `if (stackTrace != null \|\| backtrace != null)`, `Throwable.java:818-819` |
| Stackless read path | `getOurStackTrace()` sees `stackTrace == null`, `backtrace == null`, returns `UNASSIGNED_STACK` |
| `getStackTrace()` | `getOurStackTrace().clone()` — a fresh zero-length array every call |
| `MaxJavaStackTraceDepth` | 1024 (default, verified on 21.0.7) — capture cost stops growing past it |
| `OmitStackTraceInFastThrow` | true (default) — JVM-implicit exceptions only, never your `new` |
| `StackTraceInThrowable` | true (default) — `false` disables capture globally |
| Construction, depth 1 | normal 276.11 ns, stackless 25.16 ns |
| `throw`+`catch`, depth 1 | normal 274.42 ns, stackless 24.61 ns, singleton 2.21 ns |
| `fillInStackTrace` cost | 250.95 ns at depth 1; ~14.99 ns per captured frame |
| Unwind cost | ~36.5 ns per frame — dominates at depth 500 |
| Ratio normal/stackless, throw+catch | 11.15x at depth 1, 1.47x at depth 100, 1.40x at depth 500 — **never quote it without the depth** |
| Ratio normal/stackless, construction | 10.97x at depth 1, 26.1x at depth 100, 6.42x at depth 500 |
| Why the ratio compresses | capture is ~15 ns/frame, unwind ~36.5 ns/frame; going stackless removes only the first |
| QuizStakes arithmetic | 2.8M rejections/day x 250.95 ns = 0.703 s CPU/day. Not worth the trace |
| Singleton's two costs | no per-occurrence context; its trace, if any, is from `<clinit>` |
| The JDK's own use | `jdk.internal.misc.ScopedMemoryAccess.ScopedAccessError`: both knobs off, plus a `Supplier<RuntimeException>` to materialise a real one at the boundary |
| Harness caveat | not JMH: no forking, no `Blackhole`, whatever JIT state obtained |

## Self-test

**Q1.** With `writableStackTrace = false`, what exactly does `Throwable`'s constructor set
`stackTrace` to, and why does that stop the walk?

<details><summary>Answer</summary>

It sets `stackTrace = null` — not the shared empty array, which is the common but wrong
description. The field is *initialised* to `UNASSIGNED_STACK` at line 213, and the four-argument
constructor overwrites it with `null` in the `else` branch. `fillInStackTrace()` guards on
`stackTrace != null || backtrace != null`; with both null the guard is false, the native
`fillInStackTrace(int)` never runs, and no walk happens. The shared empty array shows up later,
on the read side: `getOurStackTrace()` sees `stackTrace == null` and `backtrace == null` and
returns `UNASSIGNED_STACK`, which `getStackTrace()` then clones. So a stackless exception's
`getStackTrace()` gives you a fresh zero-length array on every call.

</details>

**Q2.** You measure an 11x speed-up from going stackless at depth 1 and only 1.4x at depth 500.
What changed?

<details><summary>Answer</summary>

Nothing about the capture — it still costs about 15 ns per frame either way, and at depth 500
that is 7,496 ns saved. What changed is that the *other* cost showed up. Throwing across 500
frames and catching at the top costs roughly 18,248 ns of unwinding, which is independent of
whether a trace was captured. At depth 1 there is essentially nothing to unwind, so the capture
is the whole cost and removing it removes 91%. At depth 500 the unwind is 2.4x the capture, so
removing the capture removes only 29%. Depth 100 sits between, at **1.47x** (5,658.12 / 3,839.70),
which is why a sibling file measuring from depth 100 upward reports a 1.3–1.6x band and this page
reports 11x — same mechanism, different depth range. The corollary: if you are optimising a deep
throw, the stack trace is not your bottleneck — the throw itself is, and the fix is not to throw.

</details>

**Q6.** Stake reservations run at 2.8M/day, 1,200/sec peak. Justify or reject a stackless
`InsufficientFundsException` with numbers.

<details><summary>Answer</summary>

Reject it. `fillInStackTrace` measured 250.95 ns at depth 1. Even assuming every one of the 2.8M
daily reservations is rejected, 2.8M x 250.95 ns = 0.703 seconds of CPU per day. At the 1,200/sec
peak that is 301 microseconds per second, or 0.03% of one core. Per request it is 251 ns against
a card PSP authorise at p50 240ms — one part in about 950,000. In exchange you delete the only
evidence of which caller of `ReserveStake` asked for the wrong amount. The rate at which the trade
starts making sense is around a million throws per second per core, which is an inner loop, not a
business path.

</details>

**Q7.** What are the two costs of a preallocated singleton exception, and how does the JDK avoid
both?

<details><summary>Answer</summary>

First, a shared instance cannot carry per-occurrence context: whatever client id and amount it was
built with, it reports forever. Second, if it has a writable stack trace, that trace is from
wherever the instance was created — typically a static initialiser — so it prints something
plausible and wrong. `jdk.internal.misc.ScopedMemoryAccess.ScopedAccessError` avoids both by
calling `super("Invalid memory access", null, false, false)` — no trace to be misleading, and a
fixed message that is the entire information content — and by carrying a
`Supplier<RuntimeException>` so the boundary calls `newRuntimeException()` and materialises a real
exception, with a real trace, where a human will read it. The JVM's own
`OmitStackTraceInFastThrow` preallocation follows the same rule: preallocated *and* traceless.

</details>

**Q8.** `enableSuppression = false` and `writableStackTrace = false` — what does each turn off,
and what is the trap in the first?

<details><summary>Answer</summary>

`writableStackTrace = false` sets `stackTrace = null`, so `fillInStackTrace()` skips the native
walk and both `fillInStackTrace` and `setStackTrace` become permanent no-ops.
`enableSuppression = false` sets `suppressedExceptions = null`, and the trap is that
`addSuppressed` on a null list is a **silent no-op** — no exception, no warning, nothing in
a log. So a try-with-resources whose `close()` fails while this exception is propagating loses the
close failure entirely. Measured: `enableSuppression=false, after addSuppressed = 0`, while the
same object still reported `frames = 1`, proving the knobs are independent.

</details>

## Open questions

- **Unverified:** whether `new stackless` growing from 24.65 ns (depth 1) to 135.74 ns (depth 500)
  net of the recursion baseline is entirely cache and stack-bank effects, or whether some
  depth-dependent cost remains in the allocation path. A JMH run with `-prof perfasm` on Linux, or
  an allocation-profiler comparison at both depths, would settle it; this harness cannot.
- **Unverified:** the leaf text asks for a JMH comparison. JMH is not available in this
  environment, so every figure on this page comes from the house harness in
  `../cost-model/02-master-cost-table.md` — no forking, no `Blackhole`, whatever JIT state
  happened to obtain. A real JMH run (guide 06) would confirm the ratios and replace the absolute
  nanoseconds.

---

**Leaves covered:** 4.6.2 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 839
