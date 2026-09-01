# 03 Java Core — Measurement, amortisation, and what a microbenchmark actually measured — INTERMEDIATE (§2.1)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The master cost table](02-master-cost-table.md) · Next: [The five immutability rules](../immutability-and-design/02-immutability.md)

---

[The master cost table](02-master-cost-table.md) settled the *prices*: one table of operations in nanoseconds, the TLAB bump-pointer allocation model behind them, and the column showing which rows the JIT deletes outright. This file settles the *reasoning*. Four things the table cannot say on its own: why exception construction is the one row that scales with something outside the operation itself, why reflection has three different prices depending on how you hold the handle, what "amortised O(1)" actually guarantees as against "average O(1)", and — last and most important — which of the numbers in either file are measurements of Java and which are measurements of `javac` and C2 doing the work before the timer started.

Everything quoted below was measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64**, by two harnesses reproduced in place. Neither is JMH: no forking, no `Blackhole`, no dead-code-elimination guard beyond a `volatile` sink field, and the JIT's compilation state is whatever it happens to be when the timing loop runs. The empty-loop floor in harness 1 measured **0.51–0.63 ns/op** across three runs, so any row within about a nanosecond of that is at or under the measurement apparatus and its number means "too cheap to separate from the harness," not "costs exactly this." Relative comparisons *within one run* are meaningful; absolute figures are not portable off this machine. Guide 06 owns JMH, which is the tool for a number you would put in a capacity plan.

---

## 1. Exception creation is proportional to stack depth; throw and catch are not (2.1.4)

`[PROVE]` `[RESEARCH]` Every other row in the master cost table prices an operation whose cost is a property of the operation. `new InsufficientFundsException("…")` is the exception: its cost is a property of *where you are standing when you call it*. The constructor's job is not just to initialise two fields, it is to answer "how did control get here", and answering that means walking every frame between the `new` and the bottom of the thread's stack. The `throw` that follows — the part everyone blames — is a table lookup.

### Why it exists

`Throwable`'s constructor calls `fillInStackTrace()` unconditionally, because the platform's default is that an exception can always answer "where did this come from" without the throw site having remembered to ask. That is the right default for the overwhelming majority of exceptions, which are thrown rarely and read by a human under time pressure. It becomes a cost model problem only when a `throw` migrates onto a path measured in thousands per second, and the point of this section is that the migration is priced by *depth*, which is a number nobody looks at during code review.

### When to reach for it, and when not

Reach for this arithmetic when a `throw` sits on the stake-reservation path (1,200/sec peak) or the stake-settlement path (3,400/sec burst) and you need to decide whether it is worth removing. Do not reach for it on a path that throws at most once per HTTP request, where an entire exception construction at any plausible depth disappears next to a card PSP authorise at p50 240 ms. The design decision that follows from the numbers — return value versus exception, and the stackless-exception escape hatch — belongs to [`../exceptions/02c-cost-and-control-flow.md`](../exceptions/02c-cost-and-control-flow.md); this section only prices it.

### How it works

`[PROVE]` The proof is a depth sweep. Constructing (not throwing) `InsufficientFundsException` at a measured recursion depth, 20,000-iteration warmup, then 500,000 iterations (100,000 at depth ≥ 500), under `-Xss24m` so the deep cases have room. `frames captured` is `e.getStackTrace().length` at that depth:

```
depth=1     construct=   266.5 ns   frames captured=4
depth=5     construct=   272.3 ns   frames captured=8
depth=10    construct=   338.5 ns   frames captured=13
depth=50    construct=   900.3 ns   frames captured=53
depth=100   construct=  1906.7 ns   frames captured=103
depth=500   construct=  8369.3 ns   frames captured=503
depth=1000  construct= 16482.7 ns   frames captured=1003
depth=2000  construct= 19856.3 ns   frames captured=1024
```

The harness that produced it:

```java
static long recurseNoTrace(int d) {
    if (d == 0) {
        OSINK = new InsufficientFundsException("stakeable balance short of stake 4.20");
        return 1;
    }
    return recurseNoTrace(d - 1);
}
```

driven at depths `1, 5, 10, 50, 100, 500, 1000, 2000`, with a twin `recurse(d)` that returns `e.getStackTrace().length` to fill the frames column.

**Reading one: the slope, derived rather than asserted.** Take the two rows furthest apart before the cap bites, depth 10 and depth 1000, and divide the cost difference by the frame-count difference:

```
(16482.7 ns − 338.5 ns) / (1003 frames − 13 frames)
  = 16144.2 ns / 990 frames
  ≈ 16.3 ns per captured frame
```

Check it against a row in the middle rather than trusting one subtraction. Predicting depth 100 from the depth-1 floor: `266.5 + 16.3 × (103 − 4) = 266.5 + 1613.7 = 1880.2 ns`, against a measured 1906.7 ns — within 1.5%. Depth 500: `266.5 + 16.3 × (503 − 4) = 8400.2 ns`, against a measured 8369.3 ns — within 0.4%. The relationship is linear in captured frames, at roughly 16.3 ns each, across two orders of magnitude of depth.

**Reading two: the floor that no depth reduction removes.** The 266.5 ns at depth 1 is not stack walking — at four captured frames, only `4 × 16.3 = 65.2 ns` of it can be. The remaining `266.5 − 65.2 = 201.3 ns` is fixed cost: the object allocation itself (an *escaping* allocation, since the harness stores it to a `volatile` — the master cost table's escape-analysis rows are what price that), the `String` message field write, and the constructor chain `InsufficientFundsException` → `RuntimeException` → `Exception` → `Throwable`, each level running its own initialisation. Moving a `throw` two frames shallower buys you `2 × 16.3 ≈ 33 ns` out of a 280 ns bill. Refactoring for depth is not the lever; not constructing the exception is.

**Reading three: `frames captured = depth + 3`.** Depth 1 reports 4, depth 10 reports 13, depth 1000 reports 1003. The three extra frames are the harness's own: `main`, the sweep method that selects the depth, and the recursion entry point `recurseNoTrace` before its first self-call. This is worth stating rather than leaving as a puzzle, because it is the difference between "the numbers are inconsistent" and "the numbers include the measuring apparatus," and the same offset shows up in any depth measurement you take yourself.

**Reading four, and the strongest single piece of evidence in this file: the cap is visible in both columns at once.** `MaxJavaStackTraceDepth = 1024` on this build (from the `PrintFlagsFinal` block the master cost table quotes). Put the last two rows side by side:

| Depth | Frames captured | Construct (measured) | Linear extrapolation from the 16.3 ns slope |
|---|---|---|---|
| 1000 | 1003 | 16,482.7 ns | — (this is the row the slope was fitted to) |
| 2000 | **1024** | **19,856.3 ns** | `266.5 + 16.3 × (2003 − 4) ≈ 32,850 ns` |

Doubling the depth did not double the cost, and the reason is printed in the adjacent column: the captured count stopped at exactly 1024 rather than reaching 2003. The extra `19856.3 − 16482.7 = 3373.6 ns` between the two rows is the 1,000 additional frames the VM still had to *walk past* to reach the 1024 it kept, plus the deeper recursion itself — not additional frames recorded. Two columns, one flag, and no interpretation required: the cost tracks `min(depth, 1024)`, not `depth`.

**Now the second half of the leaf, which the folklore gets backwards: `throw` plus `catch` is cheap.** From harness 1, both rows at the same stack depth (~5) and both at 2,000,000 iterations:

| Operation as measured | R1 | R2 | R3 |
|---|---|---|---|
| `new InsufficientFundsException(msg)` at stack depth ~5, **not thrown** | 278.05 | 282.39 | 282.00 |
| `throw` + `catch` the same exception at depth ~5 | 284.36 | 284.49 | 282.48 |
| `throw` + `catch` a **preallocated stackless** instance | 1.45 | 1.46 | 1.34 |

Construct-and-discard: 278.05 ns. Construct-and-throw-and-catch: 284.36 ns. The unwind and handler search cost `284.36 − 278.05 = 6.31 ns`, which is `6.31 / 278.05 = 2.3%` of the bill — and the third row settles what the other 97.7% is, because a preallocated stackless instance thrown and caught through the same code costs **1.34–1.46 ns**, at the harness floor — `278.05 / 1.46 = 190×` to `282.39 / 1.34 = 211×` cheaper, call it **roughly 190–210×**. There is no stack to fill in, and what remains is the part the folklore blames.

**Insight:** that 2% is structural, not a lucky measurement. The JVM does not search a chain of nested `try` blocks at throw time. Each method's `Code` attribute carries an *exception table*: a list of `(start_pc, end_pc, handler_pc, catch_type)` rows. On `athrow`, the VM takes the current frame's program counter and scans that method's table for a row whose `[start_pc, end_pc)` range contains it and whose `catch_type` is assignable from the thrown class; on no match it pops the frame and repeats in the caller. Nesting three `try` blocks inside one method does not make the lookup three times slower — it makes the table three rows longer, scanned once. The cost scales with *frames unwound*, and even that is a few nanoseconds per frame of table scan, against 16.3 ns per frame to *record* one. Recording is dearer than unwinding. [`../exceptions/02c-cost-and-control-flow.md`](../exceptions/02c-cost-and-control-flow.md) works the three-way cost split and the stackless constructors in full.

### Diagram

No diagram is assigned here: the evidence is a measured table read top to bottom, where the cost column and the frames column move together until the cap, and a picture would be that table redrawn with the numbers harder to compare. [`../exceptions/03b-internals-stack-trace-capture.md`](../exceptions/03b-internals-stack-trace-capture.md) carries D-115 for the `fillInStackTrace` internal structure this section prices from the outside.

### A concrete example

The QuizStakes arithmetic, worked at a stated shortfall fraction rather than hand-waved. `PaymentService.reserveStake` runs at **1,200/sec peak**. Assume a shortfall rate of **20%** of reservations — a client staking down to an empty wallet is ordinary behaviour, not an incident — so 240 exceptions per second. Take the depth-100 row, since a Spring Boot controller-to-service-to-ledger stack plus the servlet container plumbing is realistically around 100 frames deep, not 5:

```
240 throws/sec × 1906.7 ns  = 457,608 ns/sec
                            = 0.458 ms/sec of CPU
                            = 0.046% of one core
```

Report that honestly: **at 1,200/sec and 20% shortfall, the exceptions cost about a twentieth of one percent of a core.** That is not a bottleneck, and a file that pretends otherwise to make its own numbers sound important is lying. Now change one input — stake settlement bursts at **3,400/sec**, and suppose a settlement-side validation failure fires on 20% of them at the same depth:

```
680 throws/sec × 1906.7 ns  = 1,296,556 ns/sec ≈ 1.3 ms/sec ≈ 0.13% of one core
```

Still small. The number only becomes interesting when depth grows: the same 680/sec at depth 1000 costs `680 × 16482.7 = 11.2 ms/sec`, about **1.1% of a core**, and at that point a deeply-recursive validator throwing on a hot path is a real line item. **The lever is the same in every case: 16.3 ns per frame, times frames, times rate.** Do the multiplication before arguing about it.

### The gotcha

**Pitfall:** believing "exceptions are slow" is a fact about `throw`. The wrong belief attaches the cost to the keyword, which leads people to restructure `try` blocks — flattening nesting, hoisting `try` outside loops, moving handlers "closer" — to make throwing cheaper. Symptom: a refactor that measurably changes nothing, because the exception table lookup was 2% of the bill and the restructuring did not touch the 98%. Worse, the same belief produces the mirror-image error: a reviewer objecting to a `try` block wrapping a hot loop that *never throws*, where the cost is exactly zero — the exception table is metadata in the `Code` attribute, and a `try` that does not fire is not executed code at all. Fix: attribute the cost to `fillInStackTrace()`, which is where the depth sweep puts it, and remember the two escape hatches are "do not construct it" (a return value) and "construct it once" (a preallocated stackless instance at 1.34–1.46 ns), never "throw it more efficiently."

> **Definition.** Exception creation costs a fixed ~266 ns floor plus roughly 16.3 ns per captured stack frame, capped at `MaxJavaStackTraceDepth = 1024` frames — measured across depths 1 to 2000 on this build — while `throw` plus `catch` adds about 6 ns, or 2%, because handler search is a per-method bytecode-range lookup in the `Code` attribute's exception table rather than a walk through nested `try` blocks.

---

## 2. Reflection has three prices, and the field modifier picks which one you pay (2.1.5)

`[RESEARCH]` Think of three ways to call `LedgerEntry.amountMinor()`. One, you wrote the call in source and C2 compiled it to a direct jump. Two, you asked `Class` for a `Method` object and called `invoke` on it — a lookup, an argument array, an access check, then a dispatch. Three, you asked `MethodHandles.lookup()` for a handle and called `invokeExact` — a *linkage* resolved once, then something the JIT can inline through as if you had written the call by hand. The measured spread between them is not the spread the folklore predicts, and the single largest factor is a keyword: whether the field holding the handle is `static final`.

### Why it exists

Reflection exists because a framework cannot know your types at compile time. Spring instantiating `PaymentService`, Jackson populating a `LedgerEntry`, JPA reading `Account.status` — none of them can emit a direct call, so the platform gives them a way to name a member at runtime. `MethodHandle` exists because `Method.invoke`'s shape — boxed `Object[]` arguments, `Object` return, an access check on each call — is opaque to the JIT, and the `invokedynamic`/`MethodHandle` machinery was designed specifically so that a *linked* handle can be constant-folded and inlined. Knowing which of the three you are on is what separates "reflection is slow" from an actual cost model.

### When to reach for it, and when not

Reach for `MethodHandle` in `static final` form when you are writing framework-shaped code — a dispatcher, a serialiser, a plugin bridge — that must call a member chosen at runtime on a hot path. Reach for `Method.invoke` for one-shot work at startup, where 4.54 ns is irrelevant and the API is simpler. Reach for neither when the type is known: no reflective mechanism is faster than the call you could have written. [`../reflection/02-reflection.md`](../reflection/02-reflection.md) owns the reflection API chapter; guide 06 owns JIT inlining; guide 07 owns why Spring's startup profile looks the way it does.

### How it works

Harness 2, plain loops with no lambda indirection, 200,000-iteration warmup, 3,000,000 measured:

```
direct virtual call                          0.99 ns
Method.invoke (warmed)                       4.54 ns
MethodHandle.invokeExact, handle in a non-static field   2.49 ns
MethodHandle.invokeExact, handle in a static final field  0.80 ns
Method.invoke, FIRST call, no warmup      13791 ns   (single sample, not an average)
```

Four separate findings, and the leaf's claim has to be checked against each.

**Finding one: a `static final MethodHandle` is genuinely free.** 0.80 ns against a direct virtual call's 0.99 ns. The reflective call measured *below* the direct call, which is not a claim that reflection is faster — it is a statement that both are inside the measurement noise of a harness whose floor is around half a nanosecond, and that the difference between them is unresolvable. That is the strongest possible confirmation of the leaf's second half: "close to free after warmup for a monomorphic `MethodHandle`" understates it. It is free.

**Finding two: `static final` is the entire optimisation, not a style preference.** The *same handle*, calling the *same method*, from a non-static field: **2.49 ns**, three times dearer (`2.49 / 0.80 = 3.1×`). The mechanism is constant folding, and the rule is `final`-specific: a `static final` field of a reference type whose value is set in the class initialiser is treated by C2 as a *trusted constant* — it may read the field once at compile time and bake the value into the compiled code. Once the handle is a constant, the entire `invokeExact` chain behind it is constant too, and C2 inlines straight through to `amountMinor()`'s body. A non-static field is a load from an object on every iteration; the handle is not a constant; there is nothing to fold, and the invocation runs as a real indirect call. `../classes-and-initialization/04-internals-final-and-constant-folding.md` owns the `final` freeze and trusted-constant rules in full.

The initialiser that produced the 0.80 ns row, verbatim from the harness:

```java
static final MethodHandle MH_STATIC;
static {
    try {
        MH_STATIC = MethodHandles.lookup().findVirtual(LedgerEntry.class, "amountMinor",
                MethodType.methodType(long.class));
    } catch (Exception e) { throw new ExceptionInInitializerError(e); }
}
// timed loop body:  acc += (long) MH_STATIC.invokeExact(ENTRY);
```

Three details in five lines that all matter. The field is `static final` and assigned in a `static` initialiser, which is the only shape that gets the trusted-constant treatment. The `catch` rethrows as `ExceptionInInitializerError` because a `static` block cannot declare checked exceptions and a handle that fails to link is not a recoverable condition — the class is unusable. And the call site is `invokeExact` with an explicit `(long)` cast, not `invoke`: `invokeExact` demands the call site's descriptor match the handle's `MethodType` exactly, and that exactness is precisely what lets the JIT emit a direct call rather than an adapting one. Switching to `invoke`, or dropping the cast so the compiler infers `Object`, inserts asType adaptation and gives up the property being measured.

**Finding three: warmed `Method.invoke` is 4.6× a direct call — not "orders of magnitude."** `4.54 / 0.99 = 4.59`. Dearer, and worth avoiding on a hot path, but the folklore's "1000×" is off by `1000 / 4.59 = 218×` in the warmed case — better than two orders of magnitude of exaggeration. The reason is that `Method.invoke` does not stay interpretive: after enough invocations the JDK generates a bytecode accessor for that specific method and the JIT compiles it, so the steady-state path is a compiled call plus argument boxing and an access check, not a VM-internal dispatch. What remains at 4.54 ns is mostly that boxing and checking, not "reflection."

**Finding four: the folklore is measuring the first call.** `Method.invoke`, first call, no warmup: **13,791 ns**. State it correctly — this is a **single sample, not an average**, taken once, and single samples carry no error bound at all. Against the 0.99 ns direct call that is roughly `13791 / 0.99 ≈ 13,900×`, call it 14,000×. This is a real cost, and it is paid **once per method, at startup, by every reflective framework in the process.** That is the number underneath Spring Boot's startup profile: thousands of distinct members reflected over during context refresh, each paying its own first-call linkage — accessor generation, access checking, and the class loading that generation entails. It is not a steady-state cost and it never shows up in a request-latency percentile, which is exactly why it survives as folklore about a thing it does not describe.

**Interview:** "Is reflection slow?" has a three-part answer and most candidates give one part. Part one: **the first call is enormous** — measured 13,791 ns here as a single sample, about 14,000× a direct call — and that is where the reputation comes from, paid once per member at startup. Part two: **warmed `Method.invoke` is about 4.6× a direct call** (4.54 ns against 0.99 ns), because the JDK generates and JIT-compiles an accessor; dear, but ordinary. Part three: **a monomorphic `MethodHandle` in a `static final` field, called with `invokeExact`, is free** — 0.80 ns against 0.99 ns, indistinguishable — and the same handle in a non-static field is 2.49 ns, because only the `static final` form is a constant C2 can fold and inline through. Giving all three, with the field-modifier detail, is the difference between having read a blog post and having measured it.

### Diagram

No diagram is assigned here: the evidence is a five-row measured table read top to bottom, and the one relationship in it — that the `static final` row is 3× cheaper than the non-static row for an identical handle — is a comparison between two adjacent numbers, which a picture would obscure rather than clarify. No sibling file carries an adjacent picture for this comparison.

### A concrete example

The shape this finding dictates in QuizStakes code. A `LedgerEntry` projection used by `BalanceView` to build the four wallet buckets, where the field to read is chosen by configuration and so cannot be a direct call:

```java
public final class PositionAccessor {

    private static final MethodHandle AMOUNT_MINOR;
    private static final MethodHandle POSITION;

    static {
        try {
            MethodHandles.Lookup lookup = MethodHandles.lookup();
            AMOUNT_MINOR = lookup.findVirtual(LedgerEntry.class, "amountMinor",
                    MethodType.methodType(long.class));
            POSITION = lookup.findVirtual(LedgerEntry.class, "position",
                    MethodType.methodType(String.class));
        } catch (NoSuchMethodException | IllegalAccessException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private PositionAccessor() {}

    public static long amountMinor(LedgerEntry entry) throws Throwable {
        return (long) AMOUNT_MINOR.invokeExact(entry);
    }

    public static String position(LedgerEntry entry) throws Throwable {
        return (String) POSITION.invokeExact(entry);
    }
}
```

Both handles are `static final`, both linked once in the class initialiser, both called with `invokeExact` and an explicit cast matching the handle's return type. `invokeExact` is declared to throw `Throwable`, which is not a mistake in the signature above — the signature-polymorphic `invokeExact` can propagate anything the target throws, and narrowing it here would mean catching and rewrapping on a path measured at 0.80 ns. On a 1,200/sec stake-reservation path reading two positions per reservation, this shape costs `1200 × 2 × 0.80 ns = 1.9 microseconds per second`. The same class with `private final MethodHandle` instance fields and a `PositionAccessor` bean injected by Spring costs `1200 × 2 × 2.49 ns = 6.0 microseconds per second` — both negligible, which is the honest reading, but the 3× ratio holds at any rate and the `static final` version is not harder to write.

### The gotcha

**Pitfall:** caching a `MethodHandle` in an instance field and believing the caching was the optimisation. The wrong belief is that the cost of reflection is *lookup*, so any form of caching the looked-up handle recovers direct-call speed. Symptom: a framework-shaped class with `private final MethodHandle handle;` assigned in its constructor, benchmarked against `Method.invoke`, showing a real improvement (2.49 ns against 4.54 ns) and declared done — while leaving 3× on the table against the `static final` form, and leaving it there permanently, because nothing about the code looks wrong. Fix: the handle must be reachable as a constant, which on this JVM means a `static final` field assigned in the class initialiser. If the member to call is genuinely per-instance and cannot be static, the honest options are a `static final` handle per *known* member selected by a `switch`, or accepting the 2.49 ns — not pretending the instance field got you the 0.80 ns.

> **Definition.** Reflective invocation has three distinct prices on this build: about 13,791 ns for the first, unwarmed `Method.invoke` (a single sample, roughly 14,000× a direct call, paid once per member at startup), 4.54 ns for warmed `Method.invoke` (about 4.6× a direct call, once the JDK has generated and compiled an accessor), and 0.80 ns for `invokeExact` on a `static final MethodHandle` — indistinguishable from the 0.99 ns direct call, because only a `static final` field lets C2 fold the handle to a constant and inline through it; the same handle in a non-static field measured 2.49 ns.

---

## 3. Amortised is not average, and `StringBuilder` growth proves the difference (2.1.6)

`[PROVE]` Three phrases get used as synonyms in code review and mean three different things. *Worst case* is a promise about the unluckiest single operation. *Average* is a claim about a probability distribution over inputs. *Amortised* is an accounting identity: total work across a sequence, divided by the length of the sequence, with no probability anywhere in it. `StringBuilder` growth is the cleanest place to prove the distinction, because you can print every reallocation it performs and count them.

### Why it exists

The distinction exists because the three carry different *guarantees*, and substituting one for another changes what you are allowed to conclude. "Amortised O(1)" lets you multiply by the number of appends and get a bound. "Average O(1)" does not, because an adversarial or merely unlucky input distribution can defeat an average. Getting this wrong in the other direction is how a p99 latency surprise happens: someone reads "amortised O(1)" as "O(1)", plans for uniform per-append cost, and is then surprised by a single append that copied 286 bytes. Guide 01 owns amortised analysis as a technique — the potential method, the accounting method, the banker's argument; this section proves the specific instance on measured data.

### When to reach for it, and when not

Reach for the distinction whenever a growable structure sits on a latency-sensitive path and someone quotes a per-operation cost: `StringBuilder`, `ArrayList`, `HashMap` resize, `ArrayDeque`. Do not reach for it when the total is what matters and per-operation variance does not — a batch payout file written once per window is a total-throughput problem, and there the amortised bound is the only number of interest.

### How it works

`[PROVE]` Appending the 8-character string `"DEP-301/"` forty times to `new StringBuilder()`, printing every capacity change:

```
initial capacity=16
length=24   grew 16 -> 34
length=40   grew 34 -> 70
length=72   grew 70 -> 142
length=144  grew 142 -> 286
length=288  grew 286 -> 574
final length=320 capacity=574 reallocations=5
presized new StringBuilder(320).capacity()=320
new StringBuilder("CLIENT_BONUS_RESERVED").capacity()=37 (16 + 21)
```

**Check the growth rule rather than asserting it.** The claim is `newCapacity = 2 × old + 2`. Every step, verified arithmetically:

| Old capacity | `2 × old + 2` | New capacity (measured) | Matches |
|---|---|---|---|
| 16 | `2×16 + 2 = 34` | 34 | yes |
| 34 | `2×34 + 2 = 70` | 70 | yes |
| 70 | `2×70 + 2 = 142` | 142 | yes |
| 142 | `2×142 + 2 = 286` | 286 | yes |
| 286 | `2×286 + 2 = 574` | 574 | yes |

Five for five. The `+ 2` is not decoration and not rounding — it is in the growth expression, and it is why the capacities are 34 and 70 rather than 32 and 64, which is the sequence most people would predict and would then fail to reconcile with a printed capacity. The other two lines confirm the two boundary behaviours: `new StringBuilder(320)` starts at exactly 320 and the trace shows **zero** reallocations for it, and `new StringBuilder("CLIENT_BONUS_RESERVED")` starts at **37**, which is `16 + 21` — the default 16 slots *plus* the argument's length of 21, not 16 and not 21. [`../strings/02-performance-and-text.md`](../strings/02-performance-and-text.md) owns `ArraysSupport.newLength`, the overflow handling, and the full growth chapter; the rule and this trace are what this section needs.

**Now the amortised argument, worked.** Each reallocation copies the *entire current contents* into a new array. Total copy work to reach the final length of 320, summing the length at each grow point — which is bounded above by the old capacity being abandoned:

```
16 + 34 + 70 + 142 + 286 = 548 bytes copied, across 5 reallocations
```

Compare against the bound: `2n = 2 × 320 = 640`, and `548 < 640`. The bound holds, and it holds for a structural reason, not a numerical coincidence. The sequence of copies is geometric with ratio ~2 *read backwards*: the last copy is at most `n`, the one before at most `n/2`, before that `n/4`, each term halving, so the total is at most `n(1 + 1/2 + 1/4 + …) < 2n`. Total copy work reaching length *n* is therefore **O(n)** across all appends, no matter how many appends there were. Divide by the number of appends: 40 appends, 548 bytes copied, `548 / 40 = 13.7` bytes copied per append — a constant, independent of *n*. That is the amortised bound, and note what the derivation did **not** use: any assumption about which appends were likely, any distribution, any probability. It is arithmetic on a total.

The three terms, kept apart:

| Term | What it promises | Holds for `StringBuilder.append` | What it lets you conclude |
|---|---|---|---|
| **Worst case** | A bound on the single most expensive operation | **O(n)** — the append that triggers the copy at capacity 286 copies 286 bytes | A latency bound for one call. The right term for a p99 question |
| **Average** | A bound on the expected cost over a *distribution* of inputs | **Not the claim being made.** Requires assuming which appends occur, which nobody does here | Nothing, without stating and defending the distribution |
| **Amortised** | A bound on `total work ÷ number of operations`, for **every** sequence, with no probability involved | **O(1)** — total copy work `< 2n` over any sequence of appends reaching length *n* | A throughput bound. Multiply by the append count and the answer is valid for the worst possible sequence |

**Insight:** the reason *amortised* is the strong claim and *average* the weak one is that amortised has no adversary. An average-case bound can be defeated by an input distribution; an amortised bound cannot be defeated by anything, because it is a statement about all sequences. This is the opposite of most engineers' intuition, which ranks "average" as the more reassuring word because it sounds like the common case. The leaf exists to fix exactly that inversion.

### Diagram

No diagram is assigned here: the evidence is a measured capacity trace read top to bottom against a five-row arithmetic check, and a picture of doubling boxes would be the table redrawn with the `+ 2` — the one detail that surprises people — no longer legible. [`../strings/02-performance-and-text.md`](../strings/02-performance-and-text.md) carries D-066 for `StringBuilder` growth.

### A concrete example

The QuizStakes shape: a payout file line built for each of the **7,000 batched bank withdrawals** in a `PaymentRun`, where every line is the same known width.

```java
public final class PayoutFileWriter {

    private static final int LINE_WIDTH = 320;

    public String formatLine(WithdrawalTransaction txn) {
        StringBuilder line = new StringBuilder(LINE_WIDTH);
        line.append(txn.reference())
            .append('|')
            .append(txn.instrument().sortCode())
            .append('|')
            .append(txn.instrument().accountNumber())
            .append('|')
            .append(txn.amount().amount().movePointRight(2).toBigIntegerExact())
            .append('|')
            .append(txn.amount().currency().getCurrencyCode())
            .append('|')
            .append("BDP-301")
            .append('|')
            .append(txn.signedOffBy().value());
        return line.toString();
    }
}
```

The arithmetic, from the trace above. Default `new StringBuilder()` reaching length 320: **5 reallocations**, 548 bytes copied per line. Across the batch:

```
7,000 lines × 5 reallocations = 35,000 reallocations
7,000 lines × 548 bytes       = 3,836,000 bytes copied ≈ 3.66 MiB
```

`new StringBuilder(320)`: **0 reallocations, 0 bytes copied.** One constructor argument removes 35,000 allocations and 3.66 MiB of copying from a batch that runs four times a day. Two honest qualifications, both of which matter more than the headline. First, 3.66 MiB of short-lived, non-escaping byte arrays is a trivial cost for a young-generation collector, and the master cost table's escape-analysis rows are the reason: this is not a bug being fixed, it is a free improvement being taken. Second, the presize is only free if 320 is right — over-sizing to 4096 allocates 4 KiB per line and copies nothing, which is `7,000 × 4,096 = 28,672,000 bytes ≈ 27.3 MiB` of allocation to avoid 3.66 MiB of copying, and is worse. **Presize to the measured line width, not to a comfortable round number.**

### The gotcha

**Pitfall:** reading "amortised O(1)" as a per-call latency guarantee. The wrong belief is that amortised and worst-case coincide for a doubling structure, so no individual `append` can be slow. Symptom: a p99 investigation on a path building a large string per request finds a latency tail nobody can account for from the average, because the single append that reallocated at capacity 286 copied 286 bytes and allocated a 574-byte array while every neighbouring append copied nothing — the amortised bound was correct throughout and said nothing at all about that one call. Fix: use the right term for the question being asked. Throughput and capacity planning take the amortised bound and multiply. Tail-latency work takes the worst case, which for a doubling structure is O(n) on the reallocating operation — and the fix for the tail is presizing, which removes the reallocation rather than averaging it away.

> **Definition.** `StringBuilder` grows by `newCapacity = 2 × old + 2` (verified on this build at 16 → 34 → 70 → 142 → 286 → 574), so total copy work to reach length *n* is bounded by `2n` and each append is **O(1) amortised** — a guarantee about the total divided by the count that holds for every sequence — while remaining **O(n) worst case** for the single append that copies, and making no *average*-case claim at all, since no input distribution is assumed anywhere in the argument.

---

## 4. What this harness measured, and what only JMH can measure (2.1.7)

`[X-REF 06]` This is the section that decides how far the reader should trust the rest. A microbenchmark is a conversation with two optimising compilers — `javac`, which folds constants before the class file exists, and C2, which hoists, inlines and deletes at runtime — and both are free to answer a question you did not ask. There is exactly one reliable tell, and it needs no tooling: **a number below one CPU cycle is not a cost, it is evidence that the operation was removed.**

### Why it exists

The failure mode is not that a naive benchmark is imprecise; it is that it is confidently wrong in a direction that flatters the code under test. `javac` folds constant expressions at compile time because JLS 15.28 defines them as constants and 15.29 requires string constants to be interned — so a benchmark of `+` over literals contains no `+` by the time the JVM sees it. C2 hoists loop-invariant computations out of loops because that is what an optimising compiler is for. Neither is a bug and neither can be turned off in a way that leaves a representative measurement behind. The only defence is a harness built to defeat them, plus knowing the tells.

### When to reach for it, and when not

Reach for JMH whenever the resulting number will be quoted to someone else, appear in a capacity plan, or justify a code change. Reach for a hand-rolled loop only to build intuition about relative order-of-magnitude — which is exactly what the two cost-model files are for, and no more. **Nothing in either cost-model file is a JMH result, and no figure in them belongs in a capacity plan.** Guide 06 owns JMH.

### How it works

Plain loops, 500,000 warmup, 20,000,000 measured (2,000,000 for the last row):

```
hashCode(), result DISCARDED                  0.3267 ns/op
hashCode(), result SUNK into an accumulator   0.3834 ns/op
"CLIENT_" + "BONUS_RESERVED" (two literals)   0.0755 ns/op
"CLIENT_" + POS (POS is a non-constant field) 1.7536 ns/op
```

**Lead with the row that cannot possibly be a cost. 0.0755 ns/op is below one CPU cycle at any clock this machine runs.** The arithmetic: one cycle at 4 GHz is `1 / 4×10⁹ s = 0.25 ns`; producing a genuine 0.0755 ns per operation would require a clock of `1 / 0.0755 ns = 13.2 GHz`, and no shipping Apple silicon core runs anywhere near that. So the loop body is not doing 0.0755 ns of work — it is doing a fraction of one operation per iteration, which means most iterations did nothing.

What happened: `"CLIENT_" + "BONUS_RESERVED"` is a **constant expression** in the sense of JLS 15.28 — both operands are string literals — and JLS 15.29 requires that a constant expression of type `String` be interned. `javac` therefore performs the concatenation at compile time and emits a single `ldc` of the interned literal `"CLIENT_BONUS_RESERVED"`. There is no `StringBuilder`, no `invokedynamic` to `StringConcatFactory`, no allocation, nothing in the class file resembling a `+`. The loop body reduces to `length()` on a constant `String` — itself loop-invariant — which C2 hoists out of the loop entirely, leaving an empty loop it then unrolls. **Anyone benchmarking `+` this way is measuring `javac`.** [`../strings/01b-the-string-pool.md`](../strings/01b-the-string-pool.md) owns constant folding and interning.

The control is the next row, and it is the whole demonstration: **the same expression with one non-constant operand measured 1.7536 ns**, where `POS` is a non-`final` static field holding `new String("CLIENT_BONUS_RESERVED")`. `1.7536 / 0.0755 = 23.2` — **a 23× difference produced purely by which side of the constant fold one operand fell on.** Nothing about the concatenation changed. The type is the same, the resulting characters are identical, the source line is one identifier different. If a 23× swing can be created by that edit, then no absolute concatenation figure from a hand-rolled harness means anything without knowing which side of the fold it was on.

**The subtler finding, and the more useful one.** Compare the first two rows: `hashCode()` **discarded** at 0.3267 ns and `hashCode()` **sunk** into an accumulator at 0.3834 ns. Both near zero. Both essentially the same number. The sink did **not** save the benchmark. The reason is that `String` caches its hash in its `hash` field, so on every iteration after the first the call is a field read of a value that cannot change — a loop-invariant computation on a loop-invariant receiver — and C2 hoists it out of the loop **whether or not the result is used**. The `volatile` sink forced the *store* to happen; it did nothing about the *computation*, which had already left the loop.

**Insight:** this is a more precise lesson than "always sink your result." A sink prevents **elimination of the store**, not **hoisting of a loop-invariant computation**. Those are two different optimisations with two different defences, and only the first one a `volatile` field addresses. The second needs an input that varies per iteration, or a consumer the compiler is specifically prevented from reasoning through — which is what JMH's `Blackhole` is.

And that is exactly why harness 1 measured **1.89, 1.89, 1.95 ns** for the identical `hashCode()` call across three runs, against harness 2's 0.383 ns. **Both numbers are real and they measure different things.** Harness 1 routes the body through a `java.util.function.LongUnaryOperator` lambda; that indirection is a call C2 did not fully see through in this configuration, so the cached-hash read stayed inside the loop and got executed 5,000,000 times. Harness 2's plain loop let C2 hoist it out, so it got executed roughly once. Harness 1's 1.89 ns is closer to "what one cached-hash read costs when it actually happens"; harness 2's 0.383 ns is closer to "what a loop of redundant cached-hash reads costs after the compiler notices they are redundant." Present this as the point of the section, not as an inconsistency in the data: **the harness is part of the measurement, and a `1.89 / 0.3834 = 4.9×` discrepancy between two honest harnesses is the normal state of affairs, not a defect.**

**One more calibration, stated once.** Under `-Xint`, with no JIT at all, the allocation rows from the master cost table's harness measured **42–63 ns/op**. Set that against the same rows at 0.3–4.4 ns compiled. Two orders of magnitude of every figure in these two files is **the compiler**, not the operation. That is the honest frame for the entire cost model: what is being priced is not "what Java costs" but "what Java costs after C2 has had a look at a tight loop doing the same thing five million times," which is not the shape of most production code.

### Diagram

No diagram is assigned here: the evidence is a four-row measured table read top to bottom, where the two adjacent pairs — discarded against sunk, folded against unfolded — are the entire argument, and a picture would be the table redrawn with the pairing harder to see. No sibling file carries an adjacent picture; guide 06 owns the JIT phase diagrams this would otherwise duplicate.

### A concrete example

What JMH gives you that this harness does not, item by item, and what each one defends against:

| JMH feature | What it defends against | What the hand-rolled harness did instead |
|---|---|---|
| **Forking** — a fresh JVM per trial | One benchmark's profile pollution and compilation state leaking into the next, so measurement order changes results | Ran every row in one JVM, in source order; profile pollution is present and unquantified |
| **`Blackhole.consume`** | Dead-code elimination *and* hoisting — the JIT is specifically prevented from reasoning through a `Blackhole` | A single `volatile` sink field, which stopped the store and not the hoist (measured: 0.3267 vs 0.3834 ns) |
| **`@State` scoping** (`Benchmark`/`Group`/`Thread`) | Constant folding of inputs the compiler can see are fixed, and accidental sharing between threads | `static final` fields, which are the *most* foldable shape possible — the opposite of the defence |
| **`@Warmup` / `@Measurement` iterations** | Measuring during tiered compilation rather than after it, and treating one run as a result | Fixed 500,000-iteration warmup for every row regardless of that row's compilation profile |
| **Reported error bound** (mean ± 99.9% CI) | Quoting a single number as if it had no variance | Three manual runs, spread shown per row, no interval computed |
| **`@BenchmarkMode`** (throughput, avg time, sample, single-shot) | Answering the wrong question — a p99 asked of an average | Total elapsed divided by iteration count: average time only |

Read the right-hand column as a list of known defects, because that is what it is. The three-run spread in harness 1 is narrow — `hashCode` at 1.89 / 1.89 / 1.95 ns, exception construction at 278.05 / 282.39 / 282.00 ns — which is reassuring about *repeatability on this machine* and says nothing about correctness. A benchmark can be perfectly repeatable and measure the wrong thing five million times.

### The gotcha

**Pitfall:** treating a suspiciously good benchmark result as good news. The wrong belief is that a fast number is a success and a slow number is the thing to investigate, so the sanity check only ever runs in one direction. Symptom: a team concludes string concatenation in a loop is free, ships `+=` on a hot `PayoutFileWriter` path, and finds real allocation in production — because the benchmark folded to a constant and measured nothing, and 0.0755 ns/op looked like a win rather than an impossibility. Fix: apply the cycle test to every result before believing it. Estimate one cycle at your clock (0.25 ns at 4 GHz), and treat any per-op figure at or below a few cycles as a claim that the operation was **removed**, to be proven wrong before it is quoted. Then vary the inputs so at least one operand cannot be constant-folded, and re-measure: if the number moves by 23×, the original result was about the compiler.

> **Definition.** A hand-rolled timing loop measures the compiler as much as the code: `"CLIENT_" + "BONUS_RESERVED"` measured 0.0755 ns/op — below one cycle at any clock, because JLS 15.28/15.29 make it a folded, interned constant — against 1.7536 ns for the same expression with one non-constant operand, and a `volatile` sink failed to stop C2 hoisting a loop-invariant `hashCode()` out of the loop (0.3267 discarded vs 0.3834 sunk), which is why only JMH's forking, `Blackhole`, `@State` scoping, warmup control and reported error bounds produce a number fit to quote — and why no figure in either cost-model file is one.

---

## Pitfalls

### `throw` is the expensive part of an exception, so restructuring `try` blocks will make it cheaper

**Wrong**

```java
// "Flatten the nesting so the handler search is faster."
public StakeSplit reserveStake(ClientId clientId, Money stake) {
    try {
        Money stakeable = balanceView.stakeable(clientId);
        if (stakeable.amount().compareTo(stake.amount()) < 0) {
            throw new InsufficientFundsException(
                "stakeable balance " + stakeable + " short of stake " + stake);
        }
        return bonusService.split(clientId, stake);
    } catch (InsufficientFundsException e) {
        throw e;
    }
}
```

Measured on this build, the restructuring targets 2% of the bill: `throw` plus `catch` at depth ~5 cost **284.36 ns** against **278.05 ns** to construct the same exception and never throw it. The unwind is `284.36 − 278.05 = 6.31 ns`. Flattening nesting changes nothing at all, because handler search is a scan of the current method's exception table — a list of `(start_pc, end_pc, handler_pc, catch_type)` rows in the `Code` attribute — not a walk through nested `try` scopes.

**Right**

```java
// Do not construct it. A return value the immediate caller branches on.
public Optional<StakeSplit> reserveStake(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        return Optional.empty();
    }
    return Optional.of(bonusService.split(clientId, stake));
}
```

The 98% that the restructuring missed is `fillInStackTrace()`, measured at roughly **16.3 ns per captured frame** on top of a fixed ~266 ns floor. The only two things that touch it are not constructing the exception at all, as above, or constructing it once — a preallocated stackless instance thrown and caught measured **1.34–1.46 ns**, i.e. `278.05 / 1.46 = 190×` to `282.39 / 1.34 = 211×` cheaper. [`../exceptions/02c-cost-and-control-flow.md`](../exceptions/02c-cost-and-control-flow.md) owns that decision.

**Why people believe it:** `throw` is the keyword you can see, and it is the word in the slogan. The construction is written as `new`, which looks like every other allocation in the file and reads as free — and the depth dependence is invisible at the throw site, because it is a property of the caller's caller's caller, which is not on screen.

### Reflection is orders of magnitude slower than a direct call

**Wrong**

```java
// "Reflection is 1000x slower, so we hand-rolled a switch over 40 position codes
//  rather than use a MethodHandle."
public long read(String accessorName, LedgerEntry entry) {
    return switch (accessorName) {
        case "amountMinor" -> entry.amountMinor();
        case "sequenceNumber" -> entry.sequenceNumber();
        case "postedAtEpochMillis" -> entry.postedAtEpochMillis();
        default -> throw new IllegalArgumentException("unknown accessor " + accessorName);
    };
}
```

The premise is measured wrong in the steady state. On this build, warmed `Method.invoke` is **4.54 ns** against a direct virtual call's **0.99 ns** — about 4.6×, not 1000×. And a `static final MethodHandle` called with `invokeExact` is **0.80 ns**, indistinguishable from the direct call. The hand-rolled `switch` above bought nothing measurable and has to be edited every time a position code is added.

**Right**

```java
private static final MethodHandle AMOUNT_MINOR;
static {
    try {
        AMOUNT_MINOR = MethodHandles.lookup().findVirtual(LedgerEntry.class, "amountMinor",
                MethodType.methodType(long.class));
    } catch (NoSuchMethodException | IllegalAccessException e) {
        throw new ExceptionInInitializerError(e);
    }
}

public static long amountMinor(LedgerEntry entry) throws Throwable {
    return (long) AMOUNT_MINOR.invokeExact(entry);
}
```

`static final` field, linked once in the class initialiser, `invokeExact` with an explicit cast matching the handle's `MethodType`. Measured 0.80 ns. Move that field to a non-static instance field and the identical handle measures **2.49 ns**, three times dearer, because C2 can no longer fold it to a constant.

**Why people believe it:** the folklore is a real measurement of the wrong call. The **first, unwarmed `Method.invoke` measured 13,791 ns** on this build — a single sample, roughly 14,000× a direct call — and that cost is genuinely paid, once per member, at startup, by every reflective framework in the process. It is what makes Spring Boot context refresh feel the way it does. It is not a steady-state cost and never appears in a request latency percentile, so it survives as a claim about a thing it does not describe.

### An `append` is O(1), so building a 320-character line has uniform per-call cost

**Wrong**

```java
// "append is O(1), so this is 40 uniform operations."
public String formatLine(WithdrawalTransaction txn) {
    StringBuilder line = new StringBuilder();
    for (String field : payoutFields(txn)) {
        line.append(field).append('|');
    }
    return line.toString();
}
```

Measured on this build, reaching length 320 from the default capacity of 16 performs **five reallocations** — `16 → 34 → 70 → 142 → 286 → 574` — and the append that reallocates at capacity 286 copies 286 bytes and allocates a 574-byte array while its neighbours copy nothing. Total copy work per line is `16 + 34 + 70 + 142 + 286 = 548` bytes. Across a `PaymentRun` of 7,000 batched bank withdrawals: 35,000 reallocations and about 3.66 MiB copied. `O(1)` was never the per-call claim; `O(1)` **amortised** was.

**Right**

```java
private static final int LINE_WIDTH = 320;

public String formatLine(WithdrawalTransaction txn) {
    StringBuilder line = new StringBuilder(LINE_WIDTH);
    for (String field : payoutFields(txn)) {
        line.append(field).append('|');
    }
    return line.toString();
}
```

Measured: `new StringBuilder(320).capacity()` is exactly 320, and the presized builder reallocated **zero** times reaching the same final length. Presize to the measured line width, though — over-sizing to 4096 allocates 4 KiB per line to avoid 548 bytes of copying, which is strictly worse.

**Why people believe it:** "amortised" is usually dropped in conversation, and when it survives it is heard as a hedge on an O(1) claim rather than as a different claim. It also *sounds* weaker than "average", when it is in fact stronger — amortised holds for every sequence with no distributional assumption, while average needs one — so the term that carries the real guarantee is the one that gets discarded.

### A `volatile` sink field is enough to keep the JIT from deleting your benchmark

**Wrong**

```java
static volatile long SINK;
static final String POS = "CLIENT_BONUS_RESERVED";

static void benchHashCode(int iters) {
    long acc = 0;
    long t0 = System.nanoTime();
    for (int i = 0; i < iters; i++) {
        acc += POS.hashCode();          // "sunk into acc, so it can't be eliminated"
    }
    long t1 = System.nanoTime();
    SINK = acc;
    System.out.printf("%.4f ns/op%n", (double) (t1 - t0) / iters);
}
```

Measured on this build: **0.3834 ns/op sunk, against 0.3267 ns/op with the result discarded entirely.** The sink changed nothing. `String` caches its hash, the receiver is loop-invariant, and C2 hoisted the read out of the loop regardless of whether anything consumed it — so the loop ran 20,000,000 times over an empty body either way. A sink prevents elimination of the **store**; it does not prevent hoisting of a loop-invariant **computation**.

**Right**

Use JMH, and consume through a `Blackhole` rather than a field:

```java
@State(Scope.Benchmark)
public class PositionHashBenchmark {

    private String position;

    @Setup(Level.Iteration)
    public void setUp() {
        this.position = new String("CLIENT_BONUS_RESERVED");
    }

    @Benchmark
    @BenchmarkMode(Mode.AverageTime)
    @OutputTimeUnit(TimeUnit.NANOSECONDS)
    @Fork(3)
    @Warmup(iterations = 5, time = 1)
    @Measurement(iterations = 10, time = 1)
    public void positionHash(Blackhole blackhole) {
        blackhole.consume(position.hashCode());
    }
}
```

`@State` keeps `position` out of reach of constant folding, the `new String(…)` in `@Setup` prevents the literal from being an interned constant, `Blackhole.consume` is a consumer the JIT is specifically prevented from reasoning through, `@Fork(3)` gives each trial a fresh JVM so no earlier benchmark's compilation state leaks in, and the harness reports a confidence interval instead of one number.

**Why people believe it:** the advice "assign your result to a `volatile` field or the JIT will delete the loop" is correct as far as it goes, and it does defend against the failure it names. It gets over-generalised into a complete defence because the two optimisations it half-covers — store elimination and loop-invariant hoisting — both present as "the number is implausibly small," so the same symptom has two causes and the well-known fix only addresses one.

---

## Cheat sheet

| Fact | Measured value (this build) |
|---|---|
| Harness 1 empty-loop floor | 0.51–0.63 ns/op — anything within ~1 ns of this is unresolved, not "this cheap" |
| Exception construction, fixed floor | ~266.5 ns at depth 1 (allocation + message field + constructor chain) |
| Exception construction, per-frame slope | `(16482.7 − 338.5) / (1003 − 13) ≈ 16.3 ns` per captured frame |
| Slope cross-check, depth 100 | predicted 1880.2 ns, measured 1906.7 ns (1.5%) |
| `MaxJavaStackTraceDepth` | `1024` — at depth 2000 frames captured stop at 1024, cost stops at 19,856 ns not ~33,000 ns |
| `frames captured` offset | `depth + 3` (harness contributes `main`, sweep method, recursion entry) |
| `throw` + `catch` overhead | `284.36 − 278.05 = 6.31 ns`, ~2% of the bill; handler search is a `Code`-attribute range lookup |
| Preallocated stackless throw+catch | 1.34–1.46 ns — at the floor; `278.05 / 1.46 = 190×` to `282.39 / 1.34 = 211×` cheaper than constructing |
| Direct virtual call | 0.99 ns |
| `static final MethodHandle` + `invokeExact` | **0.80 ns** — indistinguishable from direct; `static final` is the whole optimisation |
| Same handle, non-static field | 2.49 ns — 3.1× dearer, cannot be constant-folded |
| `Method.invoke`, warmed | 4.54 ns — 4.6× direct, not "orders of magnitude" |
| `Method.invoke`, first cold call | **13,791 ns — single sample, ~14,000× direct**, paid once per member at startup |
| `StringBuilder` growth rule | `newCapacity = 2 × old + 2`: 16 → 34 → 70 → 142 → 286 → 574 |
| Reallocations reaching length 320 | 5 from default; **0** from `new StringBuilder(320)` |
| `new StringBuilder("CLIENT_BONUS_RESERVED").capacity()` | 37 = 16 + 21 |
| Total copy work reaching *n* | `16 + 34 + 70 + 142 + 286 = 548 < 2n = 640` → O(n) total, O(1) amortised |
| Amortised vs average vs worst | amortised = total ÷ count, all sequences, no distribution; average = a distributional claim (**not** made here); worst = O(n), the reallocating append |
| `"CLIENT_" + "BONUS_RESERVED"` | 0.0755 ns/op — below one cycle (0.25 ns at 4 GHz); `javac` folded it (JLS 15.29) |
| Same with one non-constant operand | 1.7536 ns/op — **23× difference from the fold alone** |
| `hashCode()` discarded vs `volatile`-sunk | 0.3267 vs 0.3834 ns — the sink stopped the store, not the hoist |
| Same call through harness 1's lambda | 1.89 / 1.89 / 1.95 ns — the indirection blocked the hoist; both numbers real |
| `-Xint`, no JIT | 42–63 ns/op — the ceiling; most of every figure here is the compiler |
| JMH gives what this does not | forking, `Blackhole`, `@State` scoping, warmup/measurement control, error bounds |

---

## Self-test

**Q1.** Derive the per-frame cost of exception construction from the depth sweep, and say what the number at depth 1 is made of.

<details><summary>Answer</summary>

Take the two rows furthest apart before the cap bites and divide the cost difference by the frame-count difference: `(16482.7 − 338.5) / (1003 − 13) = 16144.2 / 990 ≈ 16.3 ns per captured frame`. Cross-check it against a row that was not used in the fit: predicting depth 100 gives `266.5 + 16.3 × (103 − 4) = 1880.2 ns` against a measured 1906.7 ns, within 1.5%, and depth 500 gives 8400.2 ns against 8369.3 ns, within 0.4%. So the relationship is linear in *captured* frames at about 16.3 ns each.

The 266.5 ns at depth 1 is the fixed floor. Only `4 × 16.3 = 65.2 ns` of it can be stack walking, since only four frames were captured. The rest is the escaping allocation of the exception object, the write of the `String` message field, and the constructor chain running one level at a time up through `InsufficientFundsException` → `RuntimeException` → `Exception` → `Throwable`. The practical consequence is the one worth remembering: refactoring to throw two frames shallower saves `2 × 16.3 ≈ 33 ns` out of a 280 ns bill, so depth is not the lever. Not constructing the exception is.

</details>

**Q2.** How does the depth sweep prove `MaxJavaStackTraceDepth` is doing something, rather than just being a flag someone read out of `PrintFlagsFinal`?

<details><summary>Answer</summary>

Because the cap shows up in two columns at once, and the two rows sit next to each other. At depth 1000 the sweep captured 1003 frames and cost 16,482.7 ns. At depth 2000 it captured **exactly 1024** — not 2003 — and cost 19,856.3 ns. The 16.3 ns/frame slope, extrapolated linearly, predicts `266.5 + 16.3 × (2003 − 4) ≈ 32,850 ns` for depth 2000. The measured figure is `19856.3 / 32850 = 0.60`, about 60% of that — a shortfall of some 13,000 ns — and the frames column says why in the same row: the capture stopped. So the cost tracks `min(depth, 1024)`, and the flag value `1024` is confirmed by an independently-measured count rather than quoted.

The residual `19856.3 − 16482.7 = 3373.6 ns` between the two rows is not additional frames recorded — it is the deeper recursion itself plus the cost of the VM walking past the extra 1,000 frames on its way to the 1024 it kept. Also worth stating: the `frames captured` column reads `depth + 3` throughout, because the harness itself contributes `main`, the sweep method, and the recursion entry point before the first self-call. That offset is why depth 1 reports 4.

</details>

**Q3.** Why is "throw plus catch is cheap" a structural fact about the JVM rather than a lucky measurement on one machine?

<details><summary>Answer</summary>

The measurement first: at the same stack depth, constructing the exception and not throwing it cost 278.05 ns, and constructing, throwing and catching it cost 284.36 ns. The unwind and handler search are `6.31 ns`, about 2.3% of the bill. The confirming third row is a preallocated stackless instance thrown and caught through the same code at 1.34–1.46 ns — at the harness floor, `278.05 / 1.46 = 190×` to `282.39 / 1.34 = 211×` cheaper — which localises the missing 97.7% to `fillInStackTrace()`.

The structural reason is how handler search actually works. Every method's `Code` attribute carries an exception table: rows of `(start_pc, end_pc, handler_pc, catch_type)`. On `athrow` the VM takes the current program counter and scans that one method's table for a row whose `[start_pc, end_pc)` range contains it and whose `catch_type` is assignable from the thrown class; if none matches, it pops the frame and repeats in the caller. Nesting three `try` blocks in one method does not triple the work — it makes one table three rows longer, scanned once. So the cost scales with frames *unwound*, at a few nanoseconds of table scan per frame, against 16.3 ns to *record* a frame. Recording is dearer than unwinding, on any implementation with this design.

</details>

**Q4.** "Is reflection slow?" Give the full answer.

<details><summary>Answer</summary>

Three parts, and most candidates give one. **Part one, where the folklore comes from:** the first, unwarmed `Method.invoke` measured 13,791 ns on this build — a single sample, not an average, roughly 14,000× a direct call. That is real, and it is paid once per member, at startup, by every reflective framework in the process: accessor generation, access checking, and the class loading that entails. It is what makes Spring Boot context refresh feel the way it does, and it never appears in a request-latency percentile.

**Part two, the steady state:** warmed `Method.invoke` measured 4.54 ns against a direct virtual call's 0.99 ns, about 4.6×. Dearer, worth avoiding on a hot path, but `1000 / 4.59 = 218×` off the folklore's "1000×", because after enough invocations the JDK generates a bytecode accessor for that specific method and the JIT compiles it. What remains is mostly argument boxing and the access check.

**Part three, the finding that matters:** a `MethodHandle` in a `static final` field, called with `invokeExact`, measured 0.80 ns against the direct call's 0.99 ns — indistinguishable, genuinely free. And the field modifier is the whole optimisation, not a style choice: the identical handle in a non-static field measured 2.49 ns, 3.1× dearer, because only a `static final` field assigned in the class initialiser is a trusted constant C2 can fold, and only a folded handle lets it inline through the `invokeExact` chain to the target's body.

</details>

**Q5.** Give the growth rule for `StringBuilder`, verify it on real capacities, and then define "amortised O(1)" precisely enough that it is distinguishable from "average O(1)".

<details><summary>Answer</summary>

The rule is `newCapacity = 2 × old + 2`, and the measured trace confirms every step: 34 = 2×16+2, 70 = 2×34+2, 142 = 2×70+2, 286 = 2×142+2, 574 = 2×286+2. The `+ 2` is in the expression, which is why the capacities are 34 and 70 rather than the 32 and 64 most people predict. `new StringBuilder("CLIENT_BONUS_RESERVED")` starts at 37, i.e. 16 + 21 — the default slots plus the argument's length, not one or the other.

Reaching length 320 from 16 performs five reallocations, copying `16 + 34 + 70 + 142 + 286 = 548` bytes in total, against the bound `2n = 640`. That bound is structural: read backwards, the copies are at most `n`, `n/2`, `n/4`, …, so the sum is under `n(1 + 1/2 + 1/4 + …) < 2n`. Total copy work is therefore O(n) across all appends, and `548 / 40 = 13.7` bytes per append is a constant independent of *n*.

**Amortised O(1)** means total work divided by operation count is bounded by a constant, for **every** sequence of operations, with no probability anywhere in the argument — which is exactly what the derivation above did. **Average O(1)** is a claim about an expected cost over a distribution of inputs, and it is not what is being claimed here, because no distribution was assumed. The counter-intuitive part is which is stronger: amortised has no adversary and cannot be defeated, whereas an average-case bound can be defeated by an unfavourable input distribution. **Worst case is O(n)** — the single append that triggers the copy at capacity 286 copies 286 bytes — and that is the term to use when the question is about tail latency.

</details>

**Q6.** A colleague benchmarks string concatenation and reports 0.0755 ns/op. What do you tell them, and what is the one-line check that generalises?

<details><summary>Answer</summary>

That the number is impossible as a cost, so it is evidence of removal rather than speed. One cycle at 4 GHz is `1 / 4×10⁹ = 0.25 ns`; a genuine 0.0755 ns/op would need a clock of `1 / 0.0755 ns = 13.2 GHz`, which nothing on this machine runs at. So most iterations executed nothing.

The specific cause: `"CLIENT_" + "BONUS_RESERVED"` has two string-literal operands, making it a constant expression under JLS 15.28, and JLS 15.29 requires a constant `String` expression to be interned. `javac` therefore performs the concatenation at compile time and emits a single `ldc` of `"CLIENT_BONUS_RESERVED"`. There is no `StringBuilder`, no `invokedynamic` to `StringConcatFactory`, and nothing resembling a `+` in the class file. The loop body reduces to `length()` on a constant, which is loop-invariant, so C2 hoists it out and unrolls an empty loop. They measured `javac`.

The control proves it: the same expression with one non-constant operand measured 1.7536 ns — `1.7536 / 0.0755 = 23.2`, a 23× swing produced purely by which side of the fold one operand fell on, with the resulting characters identical.

The check that generalises: estimate one cycle at your clock, and treat any per-op figure at or below a few cycles as a claim that the operation was deleted, to be disproven before it is quoted. Then vary an operand so it cannot be folded and re-measure.

</details>

**Q7.** The same `String.hashCode()` call measured 1.89 ns in one harness and 0.383 ns in another. Which is wrong?

<details><summary>Answer</summary>

Neither. They measure different things, and saying so is the entire point rather than an excuse.

Harness 2 runs the call in a plain loop. `String` caches its hash in its `hash` field, and the receiver is loop-invariant, so after the first iteration the call is a read of a value that cannot change. C2 hoists that read out of the loop entirely and the 20,000,000-iteration loop executes it roughly once — hence 0.383 ns/op, which is the cost of a loop of *redundant* reads after the compiler noticed they were redundant.

Harness 1 routes the loop body through a `java.util.function.LongUnaryOperator` lambda. That indirection is a call C2 did not fully see through in this configuration, so the read stayed inside the loop and genuinely happened 5,000,000 times — hence 1.89 ns/op across three consistent runs, which is closer to the cost of one cached-hash read actually occurring.

The sharper lesson is in the sink. Harness 2 measured 0.3267 ns with the result discarded and 0.3834 ns with it sunk into a `volatile` accumulator — the same number. The `volatile` sink prevented elimination of the **store** and did nothing about hoisting of the loop-invariant **computation**, which had already left the loop. Two different optimisations, two different defences, and the well-known advice only covers one. JMH's `Blackhole` covers both because the JIT is specifically prevented from reasoning through it.

</details>

**Q8.** How much of a figure in these two cost-model files is Java, and how much is the compiler?

<details><summary>Answer</summary>

Mostly the compiler, and there is a measured calibration for it. Under `-Xint`, with no JIT at all, the allocation rows measured **42–63 ns/op**; the same rows compiled measured 0.3–4.4 ns. That is roughly two orders of magnitude, and it is the honest frame for the whole cost model: what is priced is not "what Java costs" but "what Java costs after C2 has had a look at a tight loop doing the same thing five million times" — which is not the shape of most production code, where a method runs a handful of times per request among thousands of other methods competing for the same code cache and branch predictors.

Three specific concessions follow. The 0.51–0.63 ns harness floor means every row within about a nanosecond of it is unresolved, not cheap. Nothing here is forked, so one row's compilation state can leak into the next and measurement order is a variable nobody controlled. And nothing here reports an error bound: three runs agreed closely, which establishes repeatability on this machine and says nothing about correctness — a benchmark can be perfectly repeatable and measure the wrong thing five million times. **No figure in either cost-model file belongs in a capacity plan.** Guide 06 owns JMH, which is the tool for a number you would quote.

</details>

---

## Open questions

- **Unverified:** the internal breakdown of the ~266.5 ns fixed floor at depth 1. The sweep establishes that roughly 200 ns of it is not stack walking, but it does not separate the escaping allocation from the `String` message field write from the four-level constructor chain. What would settle it: a JMH benchmark comparing `new InsufficientFundsException(msg)`, the same class with `writableStackTrace = false`, and a bare `new RuntimeException()` with a `null` message at fixed depth 1, plus an allocation-profiler run to attribute the allocation share.
- **Unverified:** the actual clock frequency of the machine these figures were measured on. The one-cycle argument in section 4 uses 4 GHz as an illustrative figure and derives that 0.0755 ns/op would require 13.2 GHz — the conclusion holds for any clock in the plausible range for shipping Apple silicon, but the exact cycle time here was not measured. What would settle it: `sysctl -n hw.cpufrequency_max` or a JFR CPU-information event captured during the run.
- **Unverified:** whether C2's hoisting of the loop-invariant cached-hash read is guaranteed rather than incidental. The 0.3267 vs 0.3834 ns pair is strong evidence the hoist occurred, and the 1.89 ns figure through harness 1's lambda is strong evidence it did not occur there, but C2 makes no documented guarantee about when loop-invariant code motion applies, and the inlining decision that let it see through to the cached field is unspecified. What would settle it: a `-XX:+PrintCompilation -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` run on both harnesses, or a `-XX:CompileCommand=print` dump of the compiled loop body.
- **Unverified:** whether the `19856.3 − 16482.7 = 3373.6 ns` gap between the depth-1000 and depth-2000 rows is attributable to walking past the uncaptured frames rather than to the deeper recursion itself. Both contribute and the sweep does not separate them. What would settle it: a run at depths 1024, 1100, 1500 and 3000 — if the cost plateaus rather than continuing to creep, the walk-past term is small and the recursion dominates.
- **Unverified:** the `Effective Java` item-number mapping for *Minimize mutability*, cited by title only in the sibling immutability file. The number mapping is on the standing unverified list for this batch; citing by title makes a wrong number self-correcting.

---

**Leaves covered:** 2.1.4, 2.1.5, 2.1.6, 2.1.7 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 704
