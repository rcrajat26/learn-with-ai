# 03 Java Core — What an exception costs, and when control flow is the only option — INTERMEDIATE (§2.6)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Designing an exception hierarchy](02b-designing-an-exception-hierarchy.md) · Next: [Logging discipline and API boundaries](02d-logging-and-api-boundaries.md)

`02b-designing-an-exception-hierarchy.md` decided *what* your exceptions should look like — the hierarchy, the fields, the four-argument `Throwable` constructor named as a design option. This file decides *what they cost*, and where the JVM stops giving you a choice at all: `StackOverflowError` and `OutOfMemoryError` are not design decisions, they are the platform running out of a resource, and knowing their shape is what turns a 3am page into a five-minute fix instead of a guess.

Everything measured below ran on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, in `/tmp/exc02c`, with the harness code shown alongside every number. The harness is not JMH: no forking, no `Blackhole`, no dead-code-elimination guard beyond a `volatile` sink field, and the JIT's compilation state is whatever it happens to be at the point the timing loop runs. Treat every nanosecond figure as "this shape, this machine, this run" — a relative comparison within one run, not an absolute number to quote elsewhere. Guide 06 covers JMH, which is the tool for a number you would actually put in a capacity plan.

---

## 1. Exceptions as control flow — the anti-pattern, and the one legitimate case (2.6.11)

`[TRAP]` Picture two doors again, but this time both are unlocked, and the question is which one your own code should walk through to report an *expected* outcome — not a bug, not an unrecoverable resource failure, just one of the possible answers to a question you asked. `throw` is a door built for the rare case: unwind every frame between here and a handler, doing enough bookkeeping to explain where the trip happened. A `return`, or a `Result`-shaped value, is a door built for the common case: hand the answer back to the one caller who asked, at the cost of exactly one method return. Reaching for the throw door for a common case is exchanging the cheap door for the expensive one, at a frequency that turns the expense into a measurable bottleneck.

### Why it exists

The rule this concept states — "don't use exceptions for control flow" — is repeated so often it has become a slogan divorced from a mechanism, which is why it needs the cost story that concept 2 supplies. But the rule itself exists for a structural reason, not just a performance one: an exception's contract is *I am reporting something the normal path did not plan for*, and every reader of the code — the next engineer, the static analyser, the monitoring dashboard counting `ERROR`-level log lines — relies on that contract to decide what deserves attention. A `stake reservation was short of funds` outcome happening on a meaningful fraction of 2.8M/day reservations is not something anyone should be alerted to; it is Tuesday. Routing it through `throw` corrodes the signal that `throw` is supposed to carry, on top of whatever it costs in nanoseconds.

### When to reach for it, and when not

The decision rule: **is the condition expected at high frequency, and does the immediate caller branch on it right away?** If both hold, it is a return value or a `Result<T, E>` — `02a-checked-exceptions-and-lambdas.md` owns that type in full; this file only points to it. If neither holds — the condition is rare, or nobody at the call site can act on it without unwinding several frames anyway — the throw is fine, and optimising it further is solving a problem you do not have.

Two QuizStakes cases, worked all the way through, because "it depends" is not an answer a reviewer can apply:

**Illegitimate: `InsufficientFundsException` as the *first* check on the hot stake path.** `PaymentService.reserveStake` runs at 1,200/sec peak. If the balance check throws on every shortfall and `StakeController.post` immediately catches it to build a 4xx response, the exception is doing the job of a boolean — the caller branches on it in the very next line, and the condition is common enough that "rare" does not describe it. The measured cost in concept 2 is what this decision is paying for no reason: at a realistic controller-to-service call depth, throwing is materially slower than returning `false` or an `Optional`-shaped result, and it buys nothing a return value would not.

**Legitimate: parsing a malformed PSP callback amount.** `Long.parseLong` has no `tryParse` twin anywhere in the JDK — there is no method that returns a sentinel or an `Optional<Long>` on malformed input. A minor-unit deposit amount arriving from a card PSP capture callback is either well-formed or it is not, and the JDK gives exactly two ways to find out: catch `NumberFormatException`, or hand-roll a validator that duplicates `Long.parseLong`'s own digit-scanning logic ahead of the real parse. That second option is not free either — it is a second pass over the string, done in application code, to avoid a JDK API that already does the work. This is the case the leaf names explicitly, and it is genuinely a case with no clean third option.

**And then measure**, because "legitimate" does not mean "free." A parse-with-catch over a QuizStakes-shaped minor-unit amount (`"420"` well-formed, `"4x20"` malformed, modelling a corrupted PSP callback payload), against a hand-rolled digit-scan validator that pre-checks before parsing:

```java
static long parseMinorUnits(String raw) {
    try {
        return Long.parseLong(raw);
    } catch (NumberFormatException e) {
        return -1L;
    }
}

static boolean isAllDigits(String raw) {
    if (raw.isEmpty()) return false;
    int start = (raw.charAt(0) == '-') ? 1 : 0;
    if (start == raw.length()) return false;
    for (int i = start; i < raw.length(); i++) {
        if (raw.charAt(i) < '0' || raw.charAt(i) > '9') return false;
    }
    return true;
}

static long parseValidated(String raw) {
    return isAllDigits(raw) ? Long.parseLong(raw) : -1L;
}
```

Warmed for 200,000 iterations, then timed over 3,000,000 iterations each, `System.nanoTime()` around the loop, divided by iteration count:

```
well-formed input:   catch-based=4ns   pre-validated=6ns
malformed input:     catch-based=328ns  pre-validated=2ns
```

Read this the honest way. On the *well-formed* path the two are indistinguishable — the try block costs nothing when no exception is thrown, which is the whole reason "don't be afraid of `try`" is correct advice. On the *malformed* path the catch-based version is roughly two orders of magnitude slower than the validator, because it pays the construction cost concept 2 prices. Whether that matters depends entirely on how often malformed payloads actually arrive: if PSP callbacks are malformed on 0.01% of the 95k/day card deposits, the aggregate cost of the catch-based path is a rounding error; if a misbehaving PSP integration starts sending malformed amounts on 30% of callbacks, the catch-based path is now doing real, measurable work for no reason, and the validator earns its keep. **The mandate is not "never catch `NumberFormatException`"; it is "know which side of that ratio you are on, and measure before assuming."**

### How it works

The mechanism is concept 2's, in full — this concept only states the decision rule and shows the measurement recipe: a warmed loop, several million iterations, `System.nanoTime()` around a tight timing loop, and both the expected-common path and the expected-rare path measured separately, because their costs diverge sharply and a single averaged number hides that.

### Diagram

No diagram for this concept: the content is a decision rule and a two-line measurement table, and a flowchart of "is it expected and immediately actionable" would just be the sentence redrawn as boxes.

### A concrete example

The illegitimate case, made concrete, and its fix:

```java
// Illegitimate: the exception is doing a boolean's job on a 1,200/sec path.
public StakeSplit reserveStakeThrowing(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        throw new InsufficientFundsException(
            "stakeable balance " + stakeable + " short of requested stake " + stake);
    }
    return bonusService.split(clientId, stake);
}

// Legitimate: a return value the immediate caller branches on right away.
public Optional<StakeSplit> reserveStake(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        return Optional.empty();
    }
    return Optional.of(bonusService.split(clientId, stake));
}
```

`StakeController.post` in the second form writes `reserveStake(clientId, stake).map(this::accepted).orElseGet(this::rejected)` — the same branch the catch block would have written, at the cost of one allocation-free `Optional` rather than a stack-trace-carrying exception. `02a-checked-exceptions-and-lambdas.md` shows the fuller `Result<T, E>` shape for cases that need to carry a reason alongside the failure, which `Optional.empty()` cannot.

### The gotcha

**Pitfall:** believing "exceptions are for exceptional conditions" settles every case on inspection, without measuring. The wrong belief is that frequency alone decides it — "this happens often, so it must be unchecked-and-thrown is wrong, must be a return value" skips the second half of the test. `TimeoutException` on the identity-vendor call (`02-in-practice.md` concept 1) happens often too — the p99 of 38 seconds against a 30-second watchlist timeout guarantees it — and it is correctly an exception, because the *action* it triggers (retry, fall back, alert) is not a branch the immediate caller was already going to take on every call; it is a genuinely exceptional path through otherwise-linear code. Symptom of getting this wrong in the other direction: a codebase where every validation failure is a hand-rolled boolean-returning method with no message, no context, and no stack trace, making a *genuinely* rare failure three call stacks deep impossible to diagnose because nobody preserved where it happened. Fix: apply both halves of the rule — expected *and* immediately actionable — not frequency alone, and when a case is close to the line, write the two-path harness above rather than asserting an answer.

> **Definition.** Using `throw`/`catch` to signal an outcome that is both expected at meaningful frequency and immediately branched on by the calling code is control flow wearing exception syntax, and it is worth its measured cost only where the JDK genuinely offers no return-value alternative — parsing being the standing example — and even then only after measuring which side of the frequency ratio the real traffic falls on.

---

## 2. The three costs of an exception, priced (2.6.12)

`[NUM]` `[RESEARCH]` An exception is not one operation with one price; it is three operations, only one of which is expensive, and the folklore "exceptions are slow" usually means only the first of the three without saying so.

### Why it exists

`Throwable`'s constructor calls `fillInStackTrace()` unconditionally (`01a-throwable-api-and-chaining.md` owns this as API; here it is a cost line item). That call exists so that *by default*, every exception carries enough information to answer "where did this come from" without the thrower having to remember to ask for it — a design that optimises for diagnosability over throw-site cost, which is the correct default for the 99.9% of exceptions that are genuinely exceptional and thrown rarely. The cost only becomes a design problem at the frequency end of concept 1's decision rule.

### When to reach for it, and when not

Reach for pricing this out when a `throw` sits on a path measured in thousands per second — the stake-reservation path at 1,200/sec peak, or stake settlement at 3,400/sec burst, are the QuizStakes shapes where it is worth asking. Do not reach for it on a path that throws once per request at most, where the entire per-throw cost is a rounding error next to a PSP round trip at p50 240ms.

### How it works

Three separable costs, priced:

| Cost | What happens | Paid when | Dominant? |
|---|---|---|---|
| Construction | `fillInStackTrace()` walks the call stack, one frame per level, up to `min(depth, MaxJavaStackTraceDepth)` | Every `new InsufficientFundsException("message")`, always | Yes — proportional to stack depth |
| Throw + handler search | `athrow` unwinds frames until a matching `catch` is found | Every `throw` | No — cheap, and independent of how many enclosing `try` blocks exist, because the JVM's exception table is a per-method range lookup, not a linked search up nested blocks |
| Materialising `StackTraceElement[]` | Turns the internal backtrace into the array `getStackTrace()`/`printStackTrace()` return | Only if one of those methods is called | No — lazy, and skippable entirely |

The `[NUM]` arithmetic the leaf demands, worked through rather than asserted. **Depth capture:** at a call stack `N` frames deep, `fillInStackTrace()` captures `min(N, MaxJavaStackTraceDepth)` frames — measured on this build, `MaxJavaStackTraceDepth = 1024` (from the `PrintFlagsFinal` block at the top of this file). So a stake-reservation call arriving through `StakeController.post` → `PaymentService.reserveStake` → `FundsLedger.append` → three or four JDK frames is perhaps 10 deep, and captures all 10; a pathological recursive validator 5,000 frames deep captures only the first 1,024 and silently truncates the rest — the same cap concept 4 hits from the other direction.

**The byte arithmetic for materialising the array.** `StackTraceElement`'s declared instance fields, read via reflection on this JDK: `Class declaringClassObject`, `String classLoaderName`, `String moduleName`, `String moduleVersion`, `String declaringClass`, `String methodName`, `String fileName`, `int lineNumber`, `byte format` — seven reference fields, one `int`, one `byte`. (This is the Java 9+ shape, carrying the lazily-resolved class/module/loader fields used by `toString()`; it is not "four references and two ints," which describes an older, smaller layout and is worth flagging as the stale number if you find it quoted elsewhere.) Assuming a 64-bit JVM with compressed oops and compressed class pointers on — the default for a heap under 32 GB, true of every QuizStakes service — each reference field is 4 bytes, the object header is 12 bytes (8-byte mark word plus 4-byte compressed class pointer), and object size rounds up to the next multiple of 8:

```
7 references × 4 bytes  = 28 bytes
1 int                   =  4 bytes
1 byte (padded)         =  1 byte  (rounds into alignment padding)
                          ------
data                     = 33 bytes
+ 12-byte header         = 45 bytes
rounded to 8-byte align  = 48 bytes per StackTraceElement shell
```

For a 100-frame trace: 100 shells at 48 bytes = 4,800 bytes, plus the backing `StackTraceElement[]` itself — array header is 16 bytes (12-byte object header + 4-byte length field, already 8-aligned) plus 100 compressed references at 4 bytes = 400 bytes, total 416 bytes. **Roughly 5.2 KB** to materialise a 100-frame trace as an array — and this is paid only if `getStackTrace()` or `printStackTrace()` is actually called; the construction-time cost (concept 2's dominant term) uses a cheaper internal VM structure, not this array, which is why materialisation is priced separately in the table above. The full internal-structure walk-through belongs to `03b-internals-stack-trace-capture.md`; this is the cost model this tier needs, not the mechanism.

**Measured construction cost**, normal exception versus two stackless forms, recursing to a fixed depth before throwing, 3,000,000 iterations after a 200,000-iteration warmup:

```
depth=10   normal=784ns   stackless-ctor=490ns   stackless-override=508ns   boolean=9ns
depth=100  normal=5790ns  stackless-ctor=3891ns  stackless-override=3890ns  boolean=66ns
```

and, at greater depth (500,000 iterations after a 50,000-iteration warmup, `-Xss16m` to allow the recursion room):

```
depth=1000  normal=52260ns  stackless-ctor=39449ns  ratio=1.3x
```

Two honest readings, not one triumphant one. First, the boolean return is two to three **orders of magnitude** cheaper than any exception at every depth measured — this is the number that makes concept 1's rule concrete. Second, the stackless forms are only **roughly 1.3–1.6× cheaper** than a normal exception **at the depths this harness measured** — 10, 100 and 1,000 — not the order-of-magnitude improvement the "stack traces are the whole cost" story predicts, because on this JIT-warmed harness the `StringBuilder`-based message construction, the object allocation itself, and the exception's own field initialisation are a larger fraction of the total than the folklore suggests.

Note the qualifier carefully, because it is load-bearing and this harness does not test it: **the ratio is depth-dependent and this table starts at depth 10, after most of the collapse has already happened.** `03b-internals-stack-trace-capture.md` concept 4 extends the same measurement down to depth 1 and gets ≈49×, falling to ≈1.97× by depth 10 and ≈1.54× by depth 100 — its depth-10-and-deeper figures agree closely with these. The mechanism is simple: a stackless exception skips only the capture and still pays the N-frame recursion and unwind, so the saving is nearly everything in a shallow frame and a modest fraction of the total once there are frames to walk *and* frames to unwind. For this tier's decision the 1.3–1.6× figure is the right one, because a real service throws from deep in a call stack — but do not carry it to a shallow throw site and do not quote it without the depth. Report both numbers rather than picking the flattering one: stackless exceptions are worth having on a hot control-flow path, but they are not a substitute for not throwing at all.

Two ways to build a stackless exception, both compiling:

```java
// (a) The four-argument protected constructor, writableStackTrace = false.
static final class StakelessInsufficientFunds extends RuntimeException {
    StakelessInsufficientFunds(String message) {
        super(message, null, false, false);   // enableSuppression, writableStackTrace
    }
}

// (b) Overriding fillInStackTrace() to skip the walk entirely.
static final class NoTraceInsufficientFunds extends RuntimeException {
    NoTraceInsufficientFunds(String message) { super(message); }

    @Override
    public synchronized Throwable fillInStackTrace() {
        return this;   // never walks the stack; getStackTrace() returns length 0
    }
}
```

Both measured within noise of each other above, because both skip the same walk — `writableStackTrace = false` short-circuits the constructor's call to `fillInStackTrace()` before it starts, and the override intercepts the same call and does nothing. The four-argument constructor is the Java 7 addition (`02b-designing-an-exception-hierarchy.md` names it as a design option); overriding `fillInStackTrace()` works on every version this project targets.

There is a JVM-wide off switch, `-XX:-StackTraceInThrowable`, measured on this build to actually work — a plain `throw new RuntimeException("insufficient stakeable balance for stake 4.20")` under that flag produced a `getStackTrace().length` of `0`, versus `1` with the flag at its default `true`:

```
-XX:-StackTraceInThrowable   -> trace length=0
default (StackTraceInThrowable=true) -> trace length=1
```

**Do not reach for this flag in production.** It silences every stack trace in the JVM, including the ones from real bugs nobody was optimising for — turning every future `NullPointerException`, every misconfigured bean, every genuine defect into a message with no origin. The per-class override above gets the same construction saving on the one exception type that is actually hot, without blinding the rest of the process. Name it once, in a review comment, so the next engineer does not reach for the global flag out of familiarity with the name.

### Diagram

No diagram for this concept: the content is a three-row cost table and a byte-arithmetic worksheet, and both read faster as text than as a picture. `03b-internals-stack-trace-capture.md` carries the diagram for the internal `backtrace` structure this array is materialised from — D-115, per the topic's manifest — and owns the full measured comparison at the mechanism level.

### A concrete example

The table required for the three-or-more-siblings rule, gathering everything measured above into one place:

| Form | Construction cost (depth 100, this run) | Diagnosability | When to use |
|---|---|---|---|
| Normal exception | 5790ns | Full trace, always | Default. Anything thrown rarely |
| Stackless via 4-arg constructor | 3891ns | None — `getStackTrace().length == 0` | A hot, well-understood control-flow exception you have deliberately chosen to keep as an exception (rare after concept 1) |
| Stackless via `fillInStackTrace()` override | 3890ns | None, same as above | Same use case; prefer the 4-arg constructor where the superclass allows it — it needs no override to maintain |
| Boolean / `Optional` return | 66ns | N/A — no exception object exists | The default answer for anything expected and immediately actionable, per concept 1 |

### The gotcha

**Pitfall:** treating "stackless" as free rather than as a trade against diagnosability. The wrong belief is that overriding `fillInStackTrace()` on an exception type is a purely beneficial optimisation with no downside once applied. The symptom: months later, that same exception type starts firing from a *different*, genuinely buggy call site — a real defect reusing a control-flow exception type because it was already there and looked convenient — and the incident has no stack trace to work from, because the type was built to have none. The fix is naming discipline as much as code: a stackless exception's name and Javadoc should say, explicitly, "this type is deliberately stackless for the hot path at call site X; do not reuse it as a generic failure signal," and a code reviewer should treat a new `throw` of an existing stackless type as worth a second look, the same way a reviewer would treat a new caller of a `deprecated` method.

> **Definition.** An exception's cost splits into construction (dominant, proportional to stack depth via `fillInStackTrace()`), throw-and-unwind (cheap, independent of nesting), and array materialisation (lazy, paid only on `getStackTrace()`/`printStackTrace()`); the four-argument `Throwable` constructor or a `fillInStackTrace()` override skip the first and measured, on this build, roughly 1.3–1.6× cheaper than a normal exception at depths 10 through 1,000 — a real but modest saving at the depths a real service throws from, though the ratio rises steeply in shallower frames (`03b-internals-stack-trace-capture.md` measures ≈49× at depth 1, because only the capture is skipped while the recursion and unwind are shared) and is in every case small next to the two-to-three-orders-of-magnitude gap to a boolean return, which is why the fix for a hot path is usually "stop throwing," not "throw cheaper."

---

## 3. Fast-throw: when the JVM itself makes the trace disappear (2.6.13)

`[TRAP]` `[RESEARCH]` `[X-REF 06]` A production NPE with no stack trace and a `null` message is not always a logging bug or a bad exception constructor. Past a compiler-chosen threshold, C2 stops constructing a fresh exception for a hot *implicit* exception site and throws a preallocated, stackless instance instead — and the disappearance is the compiler's decision, not anything the throw site's author wrote.

### Why it exists

An implicit exception — the JVM inserting a null check, a bounds check, or a cast check and throwing on failure, with no `throw` keyword anywhere in the source — behaves, from C2's perspective, exactly like the control-flow anti-pattern in concept 1 when it fires repeatedly at the same bytecode location: a method that keeps trapping back to the interpreter defeats the compiled code's assumptions and prevents further optimisation. Past the trap-count thresholds, C2 gives up trying to compile a fast path around that site and instead throws a single, preallocated, **stackless** instance of the exception type every time — because building a fresh `fillInStackTrace()`-carrying object for a site that has proven itself hot would be paying concept 2's construction cost on every hit, for a site the compiler has already concluded is not exceptional in practice.

### When to reach for it, and when not

You do not reach for this — it is not a tool you invoke, it is a JVM behaviour you need to recognise on sight, because it produces a debugging trap: an implicit NPE that was informative during a warm-up window becomes uninformative once the site gets hot, with nothing in the application's own code changing between the two states.

### How it works

`[X-REF 06]` The mechanism, self-contained: C2's inlining and speculation both track how often a given bytecode location throws relative to how many times it is executed, against two counters visible on this build — `PerBytecodeTrapLimit = 4` and `PerMethodTrapLimit = 100` (from the `PrintFlagsFinal` block above). Once a site re-traps past what the compiler considers acceptable for a site it is trying to optimise, `-XX:+OmitStackTraceInFastThrow` — **on by default on this build, and has been for a very long time**; the folklore that it defaults to off is stale — permits the compiler to substitute a preallocated, stackless instance for `NullPointerException`, `ArrayIndexOutOfBoundsException`, `ArithmeticException` and `ClassCastException` at that site, confirmed against this JDK's `-XX:+PrintFlagsFinal` output and reproduced below for `NullPointerException`. That is the confirmed set; do not extend it further without checking the OpenJDK compiler source, which guide 06 owns. The exact trap-count threshold at which the substitution kicks in is not one of the flags above and is not documented as a fixed number — `PerBytecodeTrapLimit` and `PerMethodTrapLimit` are inputs to the JIT's broader deoptimisation bookkeeping, not a published "substitute after N throws" constant, so do not quote a threshold you have not measured on the build in front of you.

Reproduced, rather than asserted: a tight loop alternating a valid `Reservation` with `null`, calling a method that dereferences a field on it — an implicit-NPE site — 30,000,000 times, printing `e.getStackTrace().length` and `e.getMessage()` only when either changes:

```java
static String touch(Reservation r) {
    return r.clientId.trim();   // implicit NPE site when r is null
}
```

```
iter=1        traceLen=2  msg=Cannot read field "clientId" because "<parameter1>" is null
iter=5321     traceLen=0  msg=null
iter=70851    traceLen=2  msg=Cannot read field "clientId" because "<parameter1>" is null
iter=109763   traceLen=0  msg=null
```

Read the sequence: a real trace and the Java 15+ helpful-NPE message at first, then — once the site has trapped enough times — the trace collapses to length 0 and the message becomes `null`, exactly the shape a production log shows. It then **reverts** at iteration 70,851, and collapses again at 109,763 — this is the JIT deoptimising the method (falling back to the interpreter, which always builds a full trace) and later recompiling it back into the fast-throw state, a cycle guide 06's JIT chapter owns in full. Repeating the identical loop with `-XX:-OmitStackTraceInFastThrow` on the command line, the trace never collapses across all 30,000,000 iterations — confirming the flag is what gates the behaviour, on this build, for this exception type.

### Diagram

No diagram for this concept: the evidence is a four-line iteration log showing the exact moment the trace collapses and reverts, and that log is clearer read top to bottom than redrawn as a picture. `03c-internals-fast-throw-and-truncation.md` owns the C2 mechanism at the compiler-internals level and carries D-116.

### A concrete example

The diagnostic move, once you recognise the shape — restore the trace at a small, temporary cost to confirm the hypothesis before spending an hour on a false lead:

```
java -XX:-OmitStackTraceInFastThrow -jar payment-service.jar
```

If the traces come back once this flag is set, the site was fast-throw-substituted, not genuinely broken in a way that erased its own context; if they do not come back, the empty trace has a different cause — a hand-written stackless exception from concept 2, or a framework swallowing the cause during re-wrapping, both worth ruling in before ruling out. This flag is a diagnostic, run temporarily against a canary instance under load — not a standing production setting, because it reintroduces concept 2's full construction cost at every hot implicit-exception site in the process, which is exactly what fast-throw exists to avoid.

### The gotcha

**Pitfall:** the wrong belief is "our code doesn't throw exceptions on this path, so an empty stack trace must mean the log line itself is broken." The site that fast-throw substitutes is never a `throw` statement in application source — it is the JVM's own inserted null check, bounds check, or cast check, invisible in the code the author wrote, so grepping the method for `throw` finds nothing and the investigation stalls. Symptom: a `NullPointerException` with `getMessage() == null` and zero stack frames arriving in a log aggregator, on a method that "obviously" cannot throw NPE according to a source read, with the on-call engineer suspecting the logging framework rather than the JIT. Fix: recognise the shape — empty trace, null message, `NullPointerException`/`AIOOBE`/`CCE`/`ArithmeticException`, a hot method — and reach for `-XX:-OmitStackTraceInFastThrow` on a canary before assuming the logging pipeline dropped data. `02d-logging-and-api-boundaries.md` covers the logging-side symptom in full; this concept explains the cause it is the symptom of.

> **Definition.** Past its trap-count limits, C2 substitutes a single preallocated, stackless instance for a hot implicit `NullPointerException`, `ArrayIndexOutOfBoundsException`, `ClassCastException` or `ArithmeticException`, gated by `-XX:+OmitStackTraceInFastThrow` (on by default on this build) — reproduced here as a trace that collapses to length 0 and a `null` message after several thousand iterations of a tight loop, and confirmed absent entirely when the flag is turned off.

---

## 4. `StackOverflowError`: proving the depth is not a constant (2.6.20)

`[PROVE]` `[X-REF 06]` Every `StackOverflowError` you will ever see reports the same underlying fact: a thread's call stack, a fixed region of native memory reserved when the thread was created, ran out of room. The number of frames that fit is not a JVM constant — it is arithmetic over the size of that region and the size of each frame, and both sides of that division are things you can move.

### Why it exists

The JVM reserves a stack per thread up front — measured on this build, `ThreadStackSize = 2048` **kilobytes**, i.e. **2048 × 1024 = 2,097,152 bytes ≈ 2 MB**, is the default main-thread stack size (the unit matters: the raw number `2048` is meaningless without it). That region has to be fixed at thread creation because growing a thread's stack after the fact would require relocating every frame on it, including every reference into it from registers and other frames — a much harder problem than growing a heap, which is why the JVM does not attempt it and instead throws when the region is exhausted.

### When to reach for it, and when not

You do not reach for a `StackOverflowError` — it reaches for you, on unbounded recursion. The design lever you actually control is depth versus data: recursion over a `Movement` chain that walks a fixed, small, known depth (a single settlement's parent chain) is safe; recursion over a chain whose depth is driven by *user or data volume* — a client's full ledger history, or a `PaymentRun` batch — is a `StackOverflowError` waiting for a large-enough input, and the fix is the iterative rewrite this concept ends with.

### How it works

`[PROVE]` A recursive `Movement` walk that never terminates, incrementing a counter each frame, run to failure under three stack sizes:

```java
record Movement(String id, Movement parent) {}

static long counter = 0;

static long walkNarrow(Movement m) {
    counter++;
    return walkNarrow(new Movement("m" + counter, m));
}
```

```
default (-Xss2048k, this build's ThreadStackSize)  -> depth reached=9453
-Xss512k                                           -> depth reached=2473
-Xss8m                                             -> depth reached=38051
```

The depth scales with the stack size, not by coincidence but by direct proportion — quartering the stack from 2048 KB to 512 KB roughly quarters the depth reached (9453 → 2473), and quadrupling it to 8 MB roughly quadruples it again (9453 → 38051). This is the arithmetic the leaf asks for, made visible: `frames ≈ stack size ÷ frame size`, and the frame size is the other side of that division, which the next measurement isolates.

**Frame size depends on the method's own locals and operand stack — proven by widening the frame and re-measuring**, same three stack sizes, a method identical in recursive shape but carrying twenty extra `long` locals:

```java
static long walkWide(Movement m) {
    counter++;
    long a=1,b=2,c=3,d=4,e=5,f=6,g=7,h=8,i=9,j=10;
    long k=11,l=12,mm=13,n=14,o=15,p=16,q=17,r=18,s=19,t=20;
    long u=a+b+c+d+e+f+g+h+i+j+k+l+mm+n+o+p+q+r+s+t;
    return walkWide(new Movement("m" + counter + u, m));
}
```

```
default (-Xss2048k)  -> depth reached=4023   (versus 9453 narrow — 43% of the depth)
-Xss512k             -> depth reached=900    (versus 2473 narrow — 36% of the depth)
-Xss8m               -> depth reached=16477  (versus 38051 narrow — 43% of the depth)
```

Roughly the same frame reaches only 40–45% as deep at every stack size, because each frame is carrying twenty more live locals — proof, not assertion, that "how deep can I recurse" has no single answer independent of what the recursing method actually does. A validator with a handful of locals per level recurses far deeper than one accumulating a `BigDecimal` running total and several intermediate values per level, on an identical stack.

**Tail calls do not help, because HotSpot does not eliminate them.** A genuinely tail-recursive method — the recursive call is the very last action, and its result is returned with no pending work on the current frame:

```java
static BigDecimal sumStakes(long remaining, BigDecimal acc, BigDecimal perStake) {
    if (remaining == 0) return acc;
    return sumStakes(remaining - 1, acc.add(perStake), perStake);
}
```

`javap -c` on this build shows the recursive call is still a real `invokestatic` followed by a plain `areturn`, not a jump back to the method's own entry:

```
       8: lload_0
       9: lconst_1
      10: lsub
      11: aload_2
      12: aload_3
      13: invokevirtual #7   // BigDecimal.add:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      16: aload_3
      17: invokestatic  #13  // Method sumStakes:(JLjava/math/BigDecimal;Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      20: areturn
```

Offset 17 pushes a brand-new frame; offset 20 is a normal return, not a `goto` back to offset 0. `sumStakes` over a `remaining` in the millions overflows the stack exactly like `walkNarrow`, despite being written in the textbook tail-recursive shape that other languages compile into a loop. **The JVM specification does not require tail-call optimisation and HotSpot does not perform it** — this is a specification gap, not a missed HotSpot optimisation opportunity, and it has stayed a gap through every LTS release to date. The adjacent facts, only as far as verifiable without over-claiming: Project Loom's virtual-thread continuations change how cheaply a *blocked* stack can be suspended and resumed, which is a different problem from TCO and does not eliminate frames from a recursive call chain; and a JVMS tail-call proposal has been discussed in the OpenJDK community for years without landing as a specified feature on any released JDK. **Unverified:** whether any specific JEP or JVMS revision is currently active toward TCO — treat both adjacent facts as background, not as a roadmap this file can commit to.

The fix, unconditionally, is an explicit loop over an explicit `Deque` — trading unbounded native stack frames (2 MB, fixed at thread creation) for a heap-allocated structure that grows with the heap:

```java
static BigDecimal sumStakesIterative(long count, BigDecimal perStake) {
    BigDecimal acc = BigDecimal.ZERO;
    Deque<Long> pending = new ArrayDeque<>();
    for (long i = 0; i < count; i++) {
        pending.push(i);
    }
    while (!pending.isEmpty()) {
        pending.pop();
        acc = acc.add(perStake);
    }
    return acc;
}
```

(This particular sum does not need the `Deque` at all — a plain counting loop would do — but the shape generalises to the case that actually needs it: an iterative walk of a `Movement` parent chain that would otherwise recurse, using an explicit stack to hold the work still pending, exactly the transformation a compiler's TCO would have performed for you if HotSpot had one.)

### Diagram

No diagram for this concept: the proof is four measured depth counts across two frame shapes and three stack sizes, plus one `javap` listing, and a table carries that more precisely than a picture would. `03c-internals-fast-throw-and-truncation.md` owns the frame-layout internals and carries D-116.

### A concrete example

Why the trace itself is truncated and repetitive, tying back to concept 2's arithmetic: `MaxJavaStackTraceDepth = 1024` on this build caps `fillInStackTrace()` at 1,024 frames regardless of how deep the actual overflow went — a `StackOverflowError` from `walkNarrow` overflowing at frame 9,453 still reports only the innermost 1,024 in `getStackTrace()`, and every one of those 1,024 frames names the same method, `MovementDepth2.walkNarrow`, because the recursion is a single method calling itself. A printed trace showing the same frame 1,024 times is not corruption; it is the cap doing exactly what it is documented to do, on a genuinely repetitive call chain.

### The gotcha

**Pitfall:** the wrong belief is "increasing `-Xss` fixes unbounded recursion." The measurements above show it *postpones* the failure proportionally — 2473 frames at 512 KB, 9453 at 2048 KB, 38051 at 8 MB — not that it removes the ceiling. Symptom: a `StackOverflowError` "fixed" by raising the thread stack size in one environment reappears in production against a larger `Movement` chain, a deeper client history, or a bigger `PaymentRun` batch, because the input that drives the recursion grew rather than the recursion becoming safe. Fix: treat any recursion whose depth is a function of external data volume as needing the iterative rewrite above, and reserve `-Xss` tuning for recursion with a small, provably bounded depth where the default margin is merely too tight — never as a substitute for bounding the recursion itself.

> **Definition.** `StackOverflowError` is thrown when a thread's fixed-size call stack — 2048 KB by default on this build, i.e. 2,097,152 bytes — is exhausted by nested frames; the depth reached is `stack size ÷ frame size` and is not a JVM constant, since frame size grows with a method's own locals (measured: a twenty-local frame reaches roughly 40–45% the depth of a narrow one at every stack size tested), and it is never rescued by tail-call elimination, because the JVM specification does not require TCO and HotSpot's compiled output for a tail-recursive method — measured via `javap` — is a plain `invokestatic` followed by `areturn`, not a loop.

---

## 5. `OutOfMemoryError` variants, and why catching one rarely helps (2.6.21)

`[X-REF 06]` `OutOfMemoryError` is not one condition with one fix. Six distinct messages report six distinct resources running out, and conflating them is how a metaspace leak gets "fixed" by raising `-Xmx`, which does nothing, because the heap was never the resource that ran out.

### Why it exists

The JVM manages several independently-sized memory regions — the object heap, the metaspace holding class metadata, native thread stacks, and off-heap direct buffers among them — and each has its own limit, its own exhaustion condition, and its own message, because the *fix* for each is different and a shared message would erase the information needed to pick the right one.

### When to reach for it, and when not

You almost never reach for *catching* `OutOfMemoryError`. `01e-catch-discipline-and-top-level-handling.md` already establishes the general rule against catching `Error`; this concept is the specific case where that rule bites hardest, because `OutOfMemoryError` is the `Error` most tempting to catch — it looks, superficially, like a resource-exhaustion condition an application could recover from the way it recovers from a full disk or a timed-out socket.

### How it works

The variants, verbatim messages where reproduced on this build, table form because there are more than three:

| Message | Meaning | Reproduced here |
|---|---|---|
| `Java heap space` | Ordinary object-heap exhaustion — allocation requested, no room, GC could not free enough | Yes |
| `GC overhead limit exceeded` | The collector is running (by default) more than 98% of wall-clock time and reclaiming less than 2% of the heap each cycle — thrashing, not merely full | Yes |
| `Metaspace` | Class metadata region exhausted — commonly a class-loader leak (dynamic proxies, scripting engines, hot-redeploy without unloading) rather than ordinary object growth | **Unverified** — not reproduced in this session; see Open questions |
| `Requested array size exceeds VM limit` | A single array allocation requested a length the JVM will not attempt regardless of available heap | Yes |
| `unable to create native thread` | The OS refused a new native thread — process thread-count limit, OS-level resource exhaustion, or address space for thread stacks exhausted | **Unverified** — not reproduced in this session; see Open questions |
| `Direct buffer memory` | A `DirectByteBuffer` allocation exceeded `-XX:MaxDirectMemorySize`, independent of `-Xmx` | **Unverified** — not reproduced in this session; see Open questions |

The two reproduced non-heap-shaped variants, both measured on `-Xmx64m`:

```java
// Java heap space — repeated large retained allocations
List<long[]> ledgerWindow = new ArrayList<>();
while (true) { ledgerWindow.add(new long[1_000_000]); }
// -> caught: Java heap space

// Requested array size exceeds VM limit — one allocation, regardless of headroom
long[] x = new long[Integer.MAX_VALUE - 1];
// -> caught: Requested array size exceeds VM limit
```

And `GC overhead limit exceeded`, which needs a different shape — most allocations discarded immediately, a tiny fraction retained, forcing the collector to run constantly while recovering almost nothing:

```java
List<byte[]> mostlyGarbage = new ArrayList<>();
long i = 0;
while (true) {
    byte[] junk = new byte[1024];
    if (i % 1000 == 0) mostlyGarbage.add(junk);   // retain 0.1%
    i++;
}
// -Xmx32m -XX:+UseParallelGC -> caught: GC overhead limit exceeded
```

Why catching one rarely helps, three reasons, all structural rather than about any one message. First, the allocation that finally *failed* is almost never the one that consumed the heap — by the time `new long[1_000_000]` throws, thousands of prior successful allocations already used up the room, so the catch block is reacting to the symptom at the wrong location to do anything about the cause. Second, the handler itself typically needs to allocate — building a log message, opening a file for a heap dump, constructing a response body — and a JVM that just failed to satisfy a much smaller allocation may fail the handler's allocations too, compounding the failure inside the recovery path. Third, `OutOfMemoryError` can be thrown from almost any allocating bytecode in almost any thread, including inside the JDK's own internals, which means the JVM's state at the throw point is not one your application code was designed to reason about — invariants a `finally` block or a partially-constructed object depended on may not hold.

The three cases where `catch (OutOfMemoryError e)` is defensible, stated precisely rather than as a blanket exemption: **(1)** converting a *known-bounded* allocation failure into a request-level rejection — a single request tried to allocate a buffer sized directly from a client-supplied length, the allocation failed, and rejecting that one request with a 4xx is safe because the failure is local and the cause is understood; **(2)** a top-level handler that logs enough to identify the failure, triggers `-XX:+HeapDumpOnOutOfMemoryError` if not already configured to fire automatically, and then performs an orderly shutdown rather than attempting to continue; **(3)** a test that asserts a resource limit is actually enforced — deliberately exhausting a bounded resource and asserting the expected `OutOfMemoryError` or an equivalent bounded-allocation rejection is thrown.

Two flags worth naming and verifying rather than assuming, on this build:

```
bool HeapDumpOnOutOfMemoryError  = false  {manageable} {default}
bool ExitOnOutOfMemoryError      = false  {manageable} {default}
```

Both default off. `HeapDumpOnOutOfMemoryError` is the one worth turning on in every production JVM — a heap dump captured at the moment of failure is the single highest-value artefact for diagnosing which allocation actually consumed the heap, and it costs nothing until the error fires. `ExitOnOutOfMemoryError` forces the JVM to terminate immediately on `OutOfMemoryError` rather than attempting to continue in a state case (3) above warns against trusting — worth enabling anywhere an orchestrator (Kubernetes, ECS) will restart the process cleanly, since a JVM that keeps running after an `OutOfMemoryError` is running in a state nobody tested for. Guide 06 owns heap dump analysis and GC tuning in full.

The domain framing, with the arithmetic worked: the ledger hot window is 90 days at roughly 19.8M entries/day, roughly 180 bytes/row —

```
90 days × 19,800,000 entries/day = 1,782,000,000 entries
1,782,000,000 entries × 180 bytes = 320,760,000,000 bytes
320,760,000,000 bytes ÷ 1024³      ≈ 298.7 GiB
```

— roughly 299 GiB, if the entire hot window were loaded into a single JVM's heap at once. No realistic `-Xmx` absorbs that, and no `catch (OutOfMemoryError e)` around the load makes it absorbable — the fix is streaming the window (a cursor over `FundsLedger`, processed in bounded batches) rather than materialising it, which is a design change, not an exception-handling change. This is the shape every one of the six variants points back to: the message tells you *which* resource ran out, but the fix is almost always upstream of the catch block, in how much was asked for at once.

### Diagram

No diagram for this concept: six message strings and a three-reason argument read faster as a table and prose than as a picture, and guide 06 carries the GC and heap-layout diagrams this concept would otherwise duplicate.

### A concrete example

The defensible case (1), made concrete — rejecting a single request whose *own* input drove an unreasonable allocation, without pretending the JVM is healthy afterward:

```java
public byte[] readCallbackPayload(InputStream pspStream, int declaredLength) {
    if (declaredLength > MAX_CALLBACK_BYTES) {
        throw new IllegalArgumentException(
            "PSP callback declared length " + declaredLength + " exceeds bound " + MAX_CALLBACK_BYTES);
    }
    try {
        return pspStream.readNBytes(declaredLength);
    } catch (OutOfMemoryError e) {
        // Bounded, single-request allocation; failure is local to this request.
        throw new IllegalStateException("unable to buffer PSP callback payload", e);
    }
}
```

The bound check above the `try` is the real fix — it should make the `catch` unreachable in practice — and the `catch` exists only as a last-resort translation for the case the bound check missed, converting a process-wide `Error` into a request-scoped failure the caller's normal error handling already knows how to reject. It is not a substitute for the bound.

### The gotcha

**Pitfall:** the wrong belief is "catching `OutOfMemoryError` around the one place we saw it thrown will stop it from happening." The symptom is a `catch (OutOfMemoryError e) { log.error("oom", e); }` block added at the stack frame from a crash report, after which the process either throws the same error moments later from an unrelated frame, or hangs in a half-collected state that is worse than a clean crash, because the code inside and around the catch block assumed heap allocation always succeeds and several of those assumptions are now false. Fix: treat the caught `OutOfMemoryError` as informational at best — log what you can with the least possible further allocation, and prefer letting `-XX:+ExitOnOutOfMemoryError` or an orchestrator restart to attempting an in-process recovery from a state the rest of the code was never written to handle.

> **Definition.** `OutOfMemoryError` reports one of several independently-exhaustible JVM resources — heap, GC efficiency, metaspace, a single array's addressable size, native threads, or direct buffer memory — via a message naming which one, and catching it is defensible only to reject a known-bounded single request, to log-and-shut-down in an orderly way, or to assert a limit in a test; in every other case the allocation that finally failed is not the one that consumed the resource, and the fix is upstream — usually streaming rather than materialising, as the ~299 GiB arithmetic for a naively-loaded 90-day ledger window shows.

---

## Pitfalls

### Using an exception to signal an expected outcome on a hot path

**Wrong**

```java
public StakeSplit reserveStake(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        throw new InsufficientFundsException(
            "stakeable balance " + stakeable + " short of requested stake " + stake);
    }
    return bonusService.split(clientId, stake);
}
```

Measured consequence, from concept 2's harness at a realistic call depth: constructing this exception costs roughly 500–800ns at shallow depth and climbs with call-stack depth, against 9–66ns for a boolean or `Optional` path at the same depths — and on a path running at 1,200 stake reservations/sec peak, a meaningful shortfall rate turns that difference into real, avoidable CPU spent building stack traces nobody reads, because `StakeController.post` catches the exception one frame up and immediately converts it to a rejection response.

**Right**

```java
public Optional<StakeSplit> reserveStake(ClientId clientId, Money stake) {
    Money stakeable = balanceView.stakeable(clientId);
    if (stakeable.amount().compareTo(stake.amount()) < 0) {
        return Optional.empty();
    }
    return Optional.of(bonusService.split(clientId, stake));
}
```

The immediate caller branches on the result exactly as before, at the cost of an `Optional` wrapper rather than a stack-trace-carrying exception. `02a-checked-exceptions-and-lambdas.md`'s `Result<T, E>` is the shape to reach for once the caller needs a *reason* alongside the failure, which `Optional.empty()` cannot carry.

**Why people believe it:** the domain exception already exists — `InsufficientFundsException` is a real, well-named type used correctly elsewhere for genuinely exceptional callers — and reusing it here reads as consistent rather than as a frequency mismatch. The cost is invisible at review time; it only shows up in a profiler under peak load, by which point the pattern has usually spread to several call sites.

### Assuming `-Xmx` fixes every `OutOfMemoryError`

**Wrong**

```
# Metaspace exhausted by a class-loader leak (repeated hot-redeploy,
# or dynamically generated proxy classes never unloaded); "fixed" by:
java -Xmx4g -jar payment-service.jar
```

Raising `-Xmx` changes the object-heap ceiling and does nothing to the metaspace ceiling, which is governed by `-XX:MaxMetaspaceSize` (unbounded by default, but bounded in practice by available native memory) — a `Metaspace` `OutOfMemoryError` recurs on schedule regardless of how large the heap is, because the heap was never the resource that ran out.

**Right**

Read the message before choosing a lever. `Java heap space` or `GC overhead limit exceeded` is a heap-sizing or allocation-rate question, and `-Xmx` or reducing retained-object growth are the right levers. `Metaspace` is almost always a class-loading leak — look for a class loader created per request, per plugin invocation, or per hot-redeploy that is never discarded, and fix the leak rather than raising the ceiling on a resource that will keep filling.

**Why people believe it:** `-Xmx` is the one JVM memory flag most engineers already know, and `OutOfMemoryError` sounds like it is always about "memory" in the singular sense that flag controls. The six distinct messages exist precisely to correct that assumption, but only if the message is actually read rather than pattern-matched to "OOM, raise the heap."

### Catching `StackOverflowError` around a recursive call to "handle" it

**Wrong**

```java
static long depth(Movement m, long counted) {
    try {
        return depth(m.parent(), counted + 1);
    } catch (StackOverflowError e) {
        return counted;   // "recovered"
    }
}
```

This "recovers" by returning a truncated, meaningless depth — the number returned is whatever depth happened to remain before the stack ran out on this particular run, not a property of the `Movement` chain, and it will differ between two runs against identical data if the JVM's stack usage at the moment of the call differs at all (a different `-Xss`, a different JIT compilation state, a thread pool reusing a stack with different residual usage). Worse, the `catch` fires deep inside an already-thin stack — the handler's own execution, including string formatting for any logging it does, is competing for the last few frames of room that caused the overflow in the first place, and can itself throw a second `StackOverflowError` mid-handler.

**Right**

```java
static long depth(Movement m) {
    long counted = 0;
    Movement current = m;
    while (current.parent() != null) {
        current = current.parent();
        counted++;
    }
    return counted;
}
```

An explicit loop has no depth limit tied to native stack size at all — it is bounded only by heap and by how long you are willing to wait, which for a `Movement` chain is the correct bound to be operating under.

**Why people believe it:** `StackOverflowError` is catchable — the JVM permits `catch (StackOverflowError e)` and even `catch (Error e)` without complaint, so it looks like a normal recoverable condition the same way a checked `IOException` is. `01e-catch-discipline-and-top-level-handling.md`'s rule against catching `Error` covers exactly why that syntactic permission is not permission in the design sense: the state the catch block resumes into is not one the surrounding code was written to handle correctly.

---

## Cheat sheet

| Flag / constant | Measured value (this build) | Meaning |
|---|---|---|
| `OmitStackTraceInFastThrow` | `true` (default) | C2 substitutes a stackless instance for hot implicit NPE/AIOOBE/CCE/ArithmeticException |
| `StackTraceInThrowable` | `true` (default) | JVM-wide switch for whether *any* `Throwable` gets a trace at all; `-XX:-StackTraceInThrowable` measured to zero every trace |
| `MaxJavaStackTraceDepth` | `1024` | Cap on frames captured by `fillInStackTrace()`, and on `getStackTrace().length` |
| `PerBytecodeTrapLimit` | `4` | Input to C2's per-site deoptimisation bookkeeping; not itself the fast-throw threshold |
| `PerMethodTrapLimit` | `100` | Same, per-method |
| `ThreadStackSize` | `2048` **KB** = 2,097,152 bytes ≈ 2 MB | Default per-thread native call-stack size |
| `ShowCodeDetailsInExceptionMessages` | `true` (default, Java 15+) | Helpful-NPE messages naming the null expression |
| `HeapDumpOnOutOfMemoryError` | `false` (default) | Turn on in production — cheapest high-value OOM diagnostic |
| `ExitOnOutOfMemoryError` | `false` (default) | Turn on where an orchestrator restarts the process cleanly |
| Exception construction (depth 100) | ~5790ns normal / ~3890ns stackless / ~66ns boolean | Stackless saves ~1.3–1.6× **at depth 10–1000**; boolean saves ~2 orders of magnitude |
| Stackless ratio is depth-dependent | ≈49× at depth 1 → ≈1.97× at 10 → ≈1.5× at 100 (`03b`) | Only the capture is skipped; recursion + unwind are shared and come to dominate |
| Parse-with-catch, malformed input | ~328ns vs ~2ns pre-validated | Only pay this if malformed input is actually rare |
| `StackOverflowError` depth, narrow frame | 2473 / 9453 / 38051 at `-Xss512k` / default / `-Xss8m` | Scales with stack size; not a constant |
| `StackOverflowError` depth, wide frame (+20 locals) | ~40–45% of the narrow depth at every stack size | Frame size, not just stack size, sets the ceiling |
| Tail-recursive `sumStakes` bytecode | `invokestatic` then `areturn` | No TCO on HotSpot — proven, not assumed |
| `OutOfMemoryError: Java heap space` | reproduced | Ordinary heap exhaustion |
| `OutOfMemoryError: GC overhead limit exceeded` | reproduced | Thrashing: >98% time in GC, <2% reclaimed |
| `OutOfMemoryError: Requested array size exceeds VM limit` | reproduced | Single allocation exceeds VM's addressable array size |
| `OutOfMemoryError: Metaspace` | not reproduced this session | Class-metadata exhaustion — usually a class-loader leak |
| `OutOfMemoryError: unable to create native thread` | not reproduced this session | OS thread/resource limit hit |
| `OutOfMemoryError: Direct buffer memory` | not reproduced this session | `DirectByteBuffer` past `-XX:MaxDirectMemorySize` |

---

## Self-test

**Q1.** A teammate says "we should never throw exceptions in the hot path, full stop." Where does that overreach, using the parsing example?

<details><summary>Answer</summary>

It overreaches at the case the JDK gives no alternative for. `Long.parseLong` has no `tryParse` twin, so a minor-unit amount parsed from a PSP callback is either caught as `NumberFormatException` or hand-validated with a duplicate digit scan ahead of the real parse — there is no third JDK-native option. Measured on this build: the catch-based path costs about 4ns on well-formed input (indistinguishable from the validated path's 6ns) and about 328ns on malformed input, against about 2ns for the pre-validated path. The right framing is not "never," it is "measure which side of the well-formed/malformed ratio your real traffic sits on" — if malformed PSP callbacks are rare, the catch-based path's cost is a rounding error; if a broken integration starts sending malformed amounts on a large fraction of callbacks, the validator earns its keep. The rule that generalises is: is the condition expected at high frequency, and does the caller branch on it immediately? Parsing external, untrusted input usually is expected-often-malformed *and* immediately branched on, which is exactly why it is the standing exception to "avoid exceptions as control flow" rather than proof the rule is wrong.

</details>

**Q2.** Break down what `new SomeException("message")` actually costs, in the order the cost is paid.

<details><summary>Answer</summary>

Three separable costs, in this order. First and dominant: the constructor calls `fillInStackTrace()`, which walks the call stack capturing up to `min(depth, MaxJavaStackTraceDepth)` frames — `1024` on this build — into an internal structure; this cost is proportional to how deep the call stack is at the throw point, measured here at roughly 784ns at depth 10 and 5790ns at depth 100 for a normal exception. Second: the `throw` itself and the search for a matching handler, which is cheap and does not depend on how many `try` blocks are nested around the throw site, because the JVM's per-method exception table is a direct range lookup rather than a chained search. Third, and only if invoked: materialising the internal backtrace into the `StackTraceElement[]` array that `getStackTrace()` or `printStackTrace()` return — lazy, skippable, and for a 100-frame trace costs roughly 5.2 KB of object allocation under the byte arithmetic worked through in concept 2 (seven reference fields plus an int and a byte per `StackTraceElement`, 48 bytes per shell under compressed oops, plus the backing array). The folklore "exceptions are slow because of stack traces" is only accurate about the first of these three, and even then the measured saving from skipping it — roughly 1.3 to 1.6× on this build — is far smaller than the two-to-three-orders-of-magnitude gap between throwing at all and returning a boolean.

</details>

**Q3.** A production NPE arrives in the log with no stack trace and a null message, on a method the source shows no `throw` in. Explain it.

<details><summary>Answer</summary>

This is very likely `-XX:+OmitStackTraceInFastThrow` — on by default on this build and has been for a long time, despite folklore claiming otherwise — substituting a preallocated, stackless `NullPointerException` for a hot *implicit* null-check site. Reproduced on this build: a tight loop alternating a valid object and `null` through a field-dereferencing method showed `getStackTrace().length` and `getMessage()` both change from a real trace and a helpful Java-15+ message to `traceLen=0, msg=null` after several thousand iterations, then flip back and forth as the JIT deoptimised and later recompiled the method — because C2 tracks how often a given bytecode location traps, and past its trap-count bookkeeping it stops constructing a full exception at that site and throws a single shared, stackless instance instead. The `throw` the reader is looking for does not exist in source, because the site is an implicit null check the JVM inserted, not application code. The diagnostic move is to restart the same workload with `-XX:-OmitStackTraceInFastThrow` on a canary: if the traces come back, this was the cause; if they do not, look elsewhere — a hand-written stackless exception type, or a framework re-wrapping and dropping the cause.

</details>

**Q4.** "Bigger `-Xss` fixes stack overflows." Where does that go wrong, with numbers?

<details><summary>Answer</summary>

It postpones the failure proportionally to the new stack size; it does not remove the ceiling. Measured on this build with an unbounded recursive `Movement` walk: 2473 frames reached at `-Xss512k`, 9453 at the default 2048 KB, 38051 at `-Xss8m` — roughly linear in stack size, because depth is `stack size ÷ frame size` and only the numerator moved. The denominator matters independently: the identical recursive shape with twenty extra `long` locals per frame reached only about 40–45% of the narrow version's depth at every stack size tested (4023 vs 9453 at the default, for instance), proving frame size is not fixed either — it is a property of what the method actually does. So raising `-Xss` is the right move only for recursion that is provably bounded and merely too close to the default margin; for recursion whose depth tracks external data volume — a client's ledger history, a growing `PaymentRun` batch — every `-Xss` value is a larger constant hiding the same unbounded growth, and the fix is the iterative rewrite with an explicit `Deque`, which has no native-stack-tied ceiling at all.

</details>

**Q5.** Does the JVM perform tail-call optimisation? Prove your answer rather than stating it.

<details><summary>Answer</summary>

No. `javap -c` on a genuinely tail-recursive method — `sumStakes(remaining, acc, perStake)`, where the recursive call is the last action and its result is returned directly — shows the recursive call compiled to `invokestatic sumStakes:(JLjava/math/BigDecimal;Ljava/math/BigDecimal;)Ljava/math/BigDecimal;` immediately followed by a plain `areturn`, not a `goto` back to the method's own entry point and not a loop of any kind. Each recursive call therefore pushes a genuinely new frame, and a `sumStakes` invoked with `remaining` in the millions overflows the stack exactly like the openly non-tail-recursive `walkNarrow` measured in this concept, despite being written in the textbook shape that other languages' compilers turn into a loop. The JVM specification does not require tail-call elimination and HotSpot does not implement it on any released JDK through 21 — this is a specification gap that has persisted across every LTS release, not a missed HotSpot optimisation the compiler is expected to someday apply automatically. The only reliable fix for a call that must run at a depth the default stack cannot hold is to write the loop yourself, typically with an explicit `Deque` standing in for the frames the recursion would otherwise have pushed.

</details>

**Q6.** Give three separate `OutOfMemoryError` messages and say what is actually exhausted in each.

<details><summary>Answer</summary>

`Java heap space`, reproduced by repeatedly appending large retained arrays under `-Xmx64m`, means the ordinary object heap is full and the collector could not free enough to satisfy the current allocation. `GC overhead limit exceeded`, reproduced by retaining a tiny fraction (0.1%) of a stream of small allocations under `-Xmx32m -XX:+UseParallelGC`, means the heap is not necessarily full but the collector is thrashing — spending more than 98% of wall-clock time collecting while reclaiming less than 2% of the heap per cycle — which is a different failure from simple exhaustion and calls for a different fix (find and stop the retention, not just raise `-Xmx`). `Requested array size exceeds VM limit`, reproduced with `new long[Integer.MAX_VALUE - 1]` under `-Xmx64m`, means a single allocation requested a length the JVM refuses regardless of how much heap headroom exists — this one is not a capacity problem at all, it is a request that was never going to be granted at any heap size. Naming the message correctly is the whole diagnosis: raising `-Xmx` fixes the first, finding the retention leak fixes the second, and fixes neither the third, whose actual fix is validating the requested size before allocating.

</details>

**Q7.** Someone proposes wrapping a batch-processing loop's body in `try { processPayoutEntry(entry); } catch (OutOfMemoryError e) { continue; }` so one bad item does not abort the batch. What is wrong with this, precisely?

<details><summary>Answer</summary>

Three separate problems, not one. First, the item that triggered the throw is very unlikely to be the one that actually consumed the heap — by the time any single allocation fails, the heap was already exhausted by everything processed before it, so `continue`-ing to the next item does nothing about the underlying cause and the next allocation is likely to fail too, in a tight, CPU-burning loop of failures. Second, the `catch` block and the surrounding loop machinery — incrementing counters, logging the skip, updating a "processed" list — themselves need to allocate, and a JVM that just failed a much smaller allocation may fail those too, so the "handled" path can itself throw moments later from inside the handler. Third, `OutOfMemoryError` can surface from essentially any allocating bytecode in any thread, including JDK-internal code the batch loop calls into, so the state the loop resumes into after `continue` is not one the loop's author reasoned about — accumulators, partially-filled buffers, or half-updated collections may be left inconsistent. The defensible pattern instead is a bound *before* the allocation — reject or chunk any batch item whose declared size exceeds a known-safe limit — so the `catch`, if it exists at all, is a last-resort translation of a failure that should already be structurally impossible, not the primary mechanism for surviving unbounded allocations.

</details>

**Q8.** What does `-XX:-OmitStackTraceInFastThrow` cost you if you leave it on permanently in production, versus using it as a diagnostic?

<details><summary>Answer</summary>

Permanently, it reintroduces concept 2's full construction cost — the `fillInStackTrace()` walk — at every hot implicit-exception site in the process, which is precisely the cost the fast-throw substitution exists to avoid for sites the JIT has already concluded trap often enough to matter. A site that was fast-throw-substituted specifically because it traps thousands of times a second under load would go back to paying full stack-capture cost thousands of times a second, which can be a measurable regression on exactly the paths that were hot enough to trigger the substitution in the first place. Used as a temporary diagnostic — deployed to a canary instance under representative load, for the duration of an investigation — it costs only that instance's share of the extra construction work, and it answers a real question decisively: if traces come back once the flag is off, the empty traces were fast-throw substitution and the fix is upstream (why is this site so hot, and is the exception actually exceptional per concept 1); if traces still do not come back, the cause is elsewhere — a hand-written stackless exception, or a layer above that discards the cause during logging or re-wrapping, which `02d-logging-and-api-boundaries.md` covers.

</details>

---

## Open questions

- **Unverified:** the exact trap-count threshold at which C2 substitutes a stackless preallocated exception for a hot implicit-exception site. `PerBytecodeTrapLimit = 4` and `PerMethodTrapLimit = 100` are measured on this build but are inputs to broader deoptimisation bookkeeping, not a documented "substitute after N throws" constant, and no threshold is asserted in this file beyond the reproduced fact that the substitution does occur within tens of thousands of iterations of a tight loop. What would settle it: a `-XX:+PrintCompilation` run correlated against the iteration count at which the trace collapsed, or a reading of OpenJDK's `graphKit.cpp` / `Compile::too_many_traps` in the C2 source guide 06 owns.
- **Unverified:** the full list of exception types eligible for fast-throw substitution beyond the four named (`NullPointerException`, `ArrayIndexOutOfBoundsException`, `ClassCastException`, `ArithmeticException`). Only `NullPointerException` was reproduced in this session; the other three are named from general knowledge of the mechanism, not from an independent reproduction here. What would settle it: repeating the `FastThrow` harness with a hot `ArrayIndexOutOfBoundsException` and `ClassCastException` site and confirming the same trace-collapse pattern on this build.
- **Unverified:** the exact verbatim messages for `OutOfMemoryError: Metaspace`, `unable to create native thread`, and `Direct buffer memory` on this build. All three were judged too time-costly to reproduce safely in this session — metaspace exhaustion needs a sustained class-loader leak, native-thread exhaustion needs pushing the OS's process thread limit, and direct-buffer exhaustion needs a `-XX:MaxDirectMemorySize`-bounded allocation loop — and none is printed as a verified string above. What would settle it: a `-XX:MaxMetaspaceSize`-bounded loop that defines fresh classes via `MethodHandles.Lookup.defineHiddenClass` without releasing them; a loop spawning threads until the OS refuses, with `ulimit -u` lowered for a fast repro; and a loop allocating `ByteBuffer.allocateDirect` under a small `-XX:MaxDirectMemorySize`.
- **Unverified:** whether any specific OpenJDK JEP or JVMS revision is currently active toward specifying tail-call optimisation. Project Loom's continuations and a long-discussed JVMS tail-call proposal are named here only as adjacent, generally-known facts, not as a verified roadmap. What would settle it: a current search of the OpenJDK JEP index and JVMS change proposals, which was out of scope for a JDK-measurement-focused file.

---

**Leaves covered:** 2.6.11, 2.6.12, 2.6.13, 2.6.20, 2.6.21 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 693
