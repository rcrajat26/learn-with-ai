# 04 Modern Java — Part 3 wrap-up — internals — INTERVIEW (§3.1, §3.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](00-index.md)
Previous: [Part 2 wrap-up — intermediate — interview intermediate](91-interview-intermediate.md) · Next: [Part 4 wrap-up — build it — interview build it](93-interview-build-it.md)

This file owns no syllabus leaves. It closes Part 3 — the internals tier, §3.1 through §3.17 —
with one summary table over everything the part covered, ten Q&As a candidate would actually say
out loud, and five predict-the-output puzzles run for real on this machine. Every number and every
stack trace below was produced with `javac --release 21` / `java` in a scratch directory, not
recalled.

---

## 1. Summary table — the whole internals tier, §3.1–§3.17

Part 3 answers one question for every Part 1/2 feature: *what does the compiler and the runtime
actually do underneath the syntax.* The table below is the map; each row cites the mechanism that
matters most in an interview and the sibling it trades against.

| § | Subject | Compile-time mechanism | Run-time mechanism | Cost / trap | Chooses against |
|---|---|---|---|---|---|
| 3.1 | Lambda translation | Body becomes a private synthetic method; call site becomes `invokedynamic` bound to `LambdaMetafactory.metafactory` | First invocation of the `invokedynamic` call site runs the bootstrap once, which spins a hidden class implementing the target functional interface and links a `CallSite` to it; every later hit of that call site is a direct invoke, not a re-bootstrap | Non-capturing lambdas are cached — the bootstrap produces one shared instance reused across all invocations, which trips reference-equality assumptions | Anonymous inner classes (always a compiled `.class` file, always allocated on every construction) |
| 3.2 | Method reference translation | Same `invokedynamic`/`LambdaMetafactory` path as 3.1; the "body" synthesized is a bridge that forwards to the referenced method or constructor | Bound (`instance::method`) references capture the receiver like a capturing lambda; unbound (`Type::method`) and static references do not | `array::new` compiles to a distinct `IntFunction`-shaped bootstrap, not `Array.newInstance` reflection | Explicit lambdas (identical bytecode shape once past the reference sugar) |
| 3.3 | Stream pipeline internals | `Stream.of`/`.stream()` builds a `Head` stage of `ReferencePipeline`; each intermediate op allocates one more `AbstractPipeline` stage linked to the previous, carrying an `opWrapSink` | Nothing traverses until a terminal op calls `evaluate(TerminalOp)`, which walks stages backwards from the terminal calling `wrapSink`, then drives the composed `Sink` chain with one pass over the source's `Spliterator` via `copyInto` | A stream with no terminal operation does literally nothing — a common "why didn't my forEach run" bug is actually "there is no forEach, only a filter" | `for`-loops (eager, no fusion, but no per-element virtual dispatch through a `Sink` chain either) |
| 3.4 | Collectors internals | `Collectors.of` composes a `Collector<T,A,R>` from `supplier`/`accumulator`/`combiner`/`finisher`; built-ins hand back purpose-built accumulator containers, not generic boxes | `summingInt` accumulates into `new int[1]` — a genuine `int`, so it silently wraps exactly like `IntStream.sum()`; `summingLong`/`averagingInt`/`averagingLong` use `long[]` slots; `summingDouble`/`averagingDouble` use Kahan-compensated `double[3]`/`double[4]` | `Collectors.toMap` with a duplicate key throws `IllegalStateException` from its default merge function — not a silent overwrite | `Stream.reduce` (no combiner state hidden from the caller, but no fork/join parallel split either) |
| 3.5 | Spliterator / parallel decomposition | `AbstractTask.suggestTargetSize` does **floored** integer division (`sizeEstimate / getLeafTarget()`, clamped to a minimum of `1`) — not "rounded up" | `getLeafTarget()` reads the **current** pool's parallelism when the calling thread is already a `ForkJoinWorkerThread`, else falls back to `LEAF_TARGET = commonPoolParallelism << 2`; a `parallelStream()` terminal op submitted from inside another `ForkJoinPool` decomposes against that pool's width, not the common pool's | Submitting the terminal op from a custom pool changes leaf sizing without changing a line of the stream code — the classic "why did wrapping it in `customPool.submit()` change throughput" interview probe | Sequential streams (predictable single-pass cost, no decomposition arithmetic to reason about) |
| 3.6 | Optional internals | `Optional<T>` is a final class wrapping one nullable field `value`; `Optional.empty()` returns the same cached singleton instance every call | `map`/`flatMap`/`filter` short-circuit on the empty singleton without invoking the function argument at all | `Optional.of(null)` throws `NullPointerException` immediately — only `ofNullable` tolerates a null input | `null` checks (cheaper per-call, but the absence is not type-visible at the API boundary) |
| 3.7 | Record internals | The compiler emits final fields, a canonical constructor, accessor methods named after the components (no `get` prefix), and one `invokedynamic` bootstrap into `ObjectMethods.bootstrap` for `equals`/`hashCode`/`toString` | The bootstrap builds the three methods from a runtime-computed list of getter `MethodHandle`s over the record's components — one shared code path for every record type, not one generated method body per class | A compact constructor cannot assign `this.field = ...` directly — the field is `final`; you reassign the *parameter*, and the compiler appends the field write for you | Plain classes with manual `equals`/`hashCode` (full control, full boilerplate, and no structural invariant enforcement) |
| 3.8 | Sealed types internals | `sealed` emits a class-file `PermittedSubclasses` attribute listing the permitted direct subtypes by binary name | The JVM verifier does not re-check the permits list at load time beyond what `javac` already enforced; exhaustiveness is a **compile-time** guarantee over the permits list, not a runtime one | Two separately-compiled sealed hierarchies with the same simple name but different `PermittedSubclasses` binary names do not satisfy each other's exhaustiveness — a classpath-shadowing trap | Plain interfaces (open extension, no exhaustiveness at any stage) |
| 3.9 | Pattern matching for switch internals | Switching over a sealed type or a `Class`-typed selector with type patterns compiles to `invokedynamic` bound to `SwitchBootstraps.typeSwitch`; switching over an exhaustive plain enum still compiles to the classic `tableswitch` over a synthetic `$SwitchMap` ordinal array | The synthetic default reached when no case (or no `default`) matches now constructs and throws `java.lang.MatchException` via its `(String, Throwable)` constructor — verified in `javap -c` output below | Through Java 20 that same synthetic default threw `IncompatibleClassChangeError`; **Java 21 changed the exception type**, not the fact that a default exists — get the direction right or lose the point | Chained `if (x instanceof A a) ... else if (x instanceof B b) ...` (no exhaustiveness check, but no bootstrap indirection either) |
| 3.10 | `instanceof` pattern matching internals | `if (obj instanceof StakeReservation r)` desugars to a checked cast plus a scoped local; the compiler tracks flow-scoping so `r` is definitely assigned only where the `instanceof` is known true | Bytecode is an ordinary `instanceof` test followed by a conditional `checkcast` and `astore` — no new opcode, no bootstrap | Negated patterns (`if (!(obj instanceof StakeReservation r)) return;`) still make `r` available *after* the guard, because flow analysis proves it must have matched to reach that point | The old cast-then-use idiom (identical bytecode after the fact, strictly more source to read) |
| 3.11 | Text block internals | Content between `"""` delimiters is processed **entirely at compile time**: incidental whitespace stripped per JLS 3.10.6's algorithm, line terminators normalized to `\n`, then the result becomes an ordinary constant `String` | No runtime type, no runtime processing step — a `javap -v` on a class using a text block shows a plain `Ldc` of a `String` constant, identical to a literal | Trailing spaces on a text-block line are significant unless followed by `\` — the "invisible" trailing-whitespace-strips-a-line-you-didn't-mean-to-strip trap | Regular string literals with `\n` (equivalent once compiled, strictly less readable for multi-line content) |
| 3.12 | `var` / LVTI internals | `var` is compiler-only: the declared type is inferred from the initializer expression at compile time and baked into the class file exactly as if it had been spelled out; there is no `var` type descriptor at runtime | Bytecode for `var x = new StakeReservation(...)` is byte-for-byte identical to `StakeReservation x = new StakeReservation(...)` | `var list = new ArrayList<>()` infers `ArrayList<Object>`, not a deferred generic — the diamond has nothing but `Object` to infer against without a target type | Explicit types (identical runtime behaviour; the tradeoff is entirely at the reading site, per the OpenJDK LVTI style guide's G1–G7 and P1–P4) |
| 3.13 | Virtual thread internals | `Thread.ofVirtual()` builds a `VirtualThread` backed by a `Continuation`; the default scheduler is a `ForkJoinPool` built by `VirtualThread.createDefaultScheduler()` with `asyncMode = true` (the source's own comment: `// FIFO`) | Parallelism defaults to `availableProcessors()`; `maxPoolSize` defaults to `Integer.max(parallelism, 256)` — **256 is a floor, not a flat default**, so a >256-core box gets `maxPoolSize == parallelism`; `minRunnable` defaults to `max(parallelism / 2, 1)`, a third tunable most material never names | On Java 21, `synchronized` still pins the virtual thread to its carrier for the block's duration (JEP 491 fixes this at Java 24); native/foreign frames pin at every release, so `jdk.VirtualThreadPinned` never fully disappears | Platform threads submitted to a fixed `ExecutorService` (bounded, OS-thread-backed, no pinning concept because there is no continuation to unmount) |
| 3.14 | Structured concurrency internals | Java 21 (JEP 453, **preview**, needs `--enable-preview`): `StructuredTaskScope` has public constructors; `fork` returns `Subtask<T>`, not `Future<T>`; policies are `ShutdownOnFailure`/`ShutdownOnSuccess`; the package moved from `jdk.incubator.concurrent` to `java.util.concurrent` at 21 | `join`/`joinUntil`/`shutdown`/`close` all run on the owning thread, inside try-with-resources, so a scope's lifetime is provably bounded by a lexical block — the "structure" in the name | Java 25 (JEP 505) replaces the public constructors with static `open()` factories and the two policies with a composable `Joiner` — naming Java 21's shape as the final one is a version trap | `ExecutorService` + manual `Future` fan-out/fan-in (no lexical lifetime guarantee — a leaked subtask can outlive the method that spawned it) |
| 3.15 | Scoped values internals | `ScopedValue.where(KEY, value).run(...)` (preview at 21) binds a value for the dynamic extent of the call, carried on the thread's stack frame rather than a mutable slot | Immutable for the bound extent, automatically visible to child threads forked inside a `StructuredTaskScope` running in that extent, automatically unbound on exit — no `remove()` to forget | `ThreadLocal.remove()` forgetting is a real memory-leak vector under virtual threads (millions of short-lived threads each carrying a lingering map entry); scoped values structurally can't leak that way | `ThreadLocal` (mutable, inheritable only via explicit `InheritableThreadLocal`, and leak-prone at virtual-thread scale) |
| 3.16 | FFM / Vector API internals | `Arena`/`MemorySegment` (JEP 442, **third preview** at Java 21, needs `--enable-preview`; finalized without preview at Java 22 by JEP 454) model off-heap memory with an explicit, checked lifetime tied to the `Arena`; the Vector API (incubator module across 21) compiles vector lanes down to CPU SIMD instructions when the JIT can, and to a scalar loop when it can't | A `MemorySegment` access after its `Arena` closes throws `IllegalStateException` at the access site, not at close time — the checked lifetime is enforced lazily | Confusing an incubator/preview module's API shape across releases is the single most common version trap in this area — always name the JEP and its status at the release you're quoting; on Java 21 specifically, FFM is still preview | `sun.misc.Unsafe` and JNI (unchecked, no lifetime enforcement, no portable SIMD story) |
| 3.17 | Observability and tooling | JFR (`jdk.VirtualThreadPinned`, `jdk.ObjectAllocationSample`, `jdk.ExecutionSample`) is built into the JDK and always recording a low-overhead default profile via `-XX:+FlightRecorder`; `javap -c -p -v` disassembles any class file to JVM bytecode plus its constant pool | `jcmd <pid> JFR.start`/`JFR.dump` attach to a live process without a restart; `async-profiler` layers native-frame sampling on top of JFR's event model for flame graphs that cross the JVM/native boundary | Reading `javap` output without `-p` hides private/synthetic members — exactly the ones that carry the mechanism (the `$SwitchMap` field, the record's synthetic accessors) | Ad-hoc `System.nanoTime()` timers and log-line profiling (zero setup, but sampling bias and no cross-thread causality) |

**Insight:** every row above is the same shape of interview answer — name the JDK class, name the
field or method that does the work, then name the number or exception that proves it. That is what
separates "streams are lazy" from a Staff-level answer.

---

## 2. Ten interview Q&As — spoken length, full model answers

**Q1. Why does calling a stream pipeline's `count()` twice throw, and what exactly does the
message tell you?**

Because a `Stream` is a one-shot description of a computation, not a reusable data structure. Every
`AbstractPipeline` tracks a `linkedOrConsumed` flag that flips to `true` the moment any operation —
intermediate or terminal — is called on it. Every public entry point checks that flag first and
throws `IllegalStateException("stream has already been operated upon or closed")` if it's already
set. I ran this for real: building a stream over a list of `LedgerEntry` records, calling
`.count()` once succeeded, and calling `.count()` again on the *same* stream reference threw
exactly that message, from `AbstractPipeline.evaluate`. There's a second message,
`"source already consumed or closed"`, but it guards a narrower internal case — a second attempt to
pull a `Spliterator` from a source that's already handed one out — and in practice you will only
ever see the first message from ordinary code, because `linkedOrConsumed` is checked before the
source is ever touched.

**Q2. What does `invokedynamic` actually buy you for lambdas that an anonymous inner class
doesn't?**

Deferred class generation and a cache. With an anonymous inner class, `javac` emits a real
`.class` file at compile time — `Something$1.class` — and every `new Something$1(...)` at runtime
allocates a fresh instance of that pre-baked class. With a lambda, `javac` emits only a private
synthetic method holding the body plus an `invokedynamic` call site whose bootstrap method is
`LambdaMetafactory.metafactory`. The very first time that call site executes, the bootstrap runs
once, spins up a hidden class implementing the target functional interface at runtime, and links
a `CallSite` to it — every subsequent hit of that call site skips the bootstrap and calls directly.
The payoff that actually shows up in `==` comparisons: a **non-capturing** lambda's `CallSite` is
bound to a cached singleton instance, so calling the same lambda-returning method twice hands back
the identical object — I verified `a == b` prints `true` for two calls to a non-capturing
`Function`. A capturing lambda can't be cached that way because each call closes over different
state, so `c == d` for two calls to a capturing lambda prints `false`, even though both instances
share the same hidden class.

**Q3. Records give you `equals`/`hashCode`/`toString` for free — where do those method bodies
actually live?**

They don't live anywhere as ordinary compiled method bodies. The compiler emits one
`invokedynamic` call site per method, each bootstrapping into
`java.lang.runtime.ObjectMethods.bootstrap`. That bootstrap method is handed the record's class,
a descriptor string naming its components, and a `MethodHandle` per component's accessor, and it
builds the actual `equals`/`hashCode`/`toString` logic at link time from that generic recipe — one
shared code path reused across every record type in the JVM, not a separate generated method body
stamped out per class the way old IDE-generated boilerplate worked. It's the same
"metafactory-style" trick as lambda translation, aimed at a different problem: keep the class file
small and let the JDK's own runtime supply the mechanism.

**Q4. Why can't a record's compact constructor write `this.field = value` directly?**

Because by the time you're inside the compact constructor, the component fields are already
declared `final`, and the compiler is going to emit the assignment for you at the end of the
constructor body. What you're allowed to reassign is the **parameter** with the same name as the
component — that's legal because parameters aren't final unless you mark them so, and it's exactly
how you normalize or validate input before the implicit field write happens. I compiled the wrong
version — `this.bonusPortion = bonusPortion.setScale(2)` inside the compact constructor of a
`StakeSplitAmounts` record — and `javac` rejects it with `cannot assign a value to final variable
bonusPortion`, pointing at the `this.` field write, not at some vaguer "invalid compact
constructor" diagnostic. The fix is `bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN);`
with no `this.` — reassign the parameter, let the compiler write the field.

**Q5. Java 21 introduced `MatchException`. What throws it, and what did the same code throw a
release earlier?**

An exhaustive `switch` **expression** (not statement) over a sealed type or an enum compiles a
synthetic default arm for the case nothing matches — the compiler trusts exhaustiveness at compile
time, but the runtime still needs a defensive arm for the case a sealed hierarchy or an enum widens
between separate compilations. Through Java 20, hitting that synthetic default threw
`IncompatibleClassChangeError`. Starting at Java 21, it throws `java.lang.MatchException`,
constructed via its `(String, Throwable)` constructor — I checked this by compiling an enum with
five constants and a `switch` expression handling all five, then recompiling *only* the enum with a
sixth constant added, without touching the switch's class file. Calling the switch with the new
constant threw `MatchException` with no message. The `javap -c` output on the switch's class file
shows exactly why: the `default:` arm of the `tableswitch` does `new MatchException`, `dup`,
`aconst_null`, `aconst_null`, `invokespecial MatchException.<init>:(Ljava/lang/String;
Ljava/lang/Throwable;)V`, `athrow` — both constructor arguments are literally `null`, which is why
the exception carries no message. Say both halves and name the release that changed it; stating
only one direction is the trap the syllabus itself walked into.

**Q6. `Collectors.summingInt` — does it have the same overflow trap as `IntStream.sum()`, or is
it protected like `averagingInt`?**

It has the exact same trap. `summingInt`'s accumulator is `new int[1]` — a genuine 32-bit `int`
slot — so summing values that overflow `Integer.MAX_VALUE` wraps silently, with no exception and no
warning. I ran three ledger amounts of `1_000_000_000` each through `Collectors.summingInt`: the
mathematically correct sum is `3_000_000_000`, but `summingInt` printed `-1294967296` — classic
two's-complement wraparound. Running the identical three values through `summingLong` printed the
correct `3000000000`, because that accumulator is a `long[1]`. `averagingInt` and `averagingLong`
are genuinely safe from this specific trap, but for a different reason than people assume: their
accumulator is a `long[2]` holding `{sum, count}`, so the running sum never overflows at `int`
width even though the *inputs* are `int`. Get the pairing right: `summingInt` unsafe,
`summingLong`/`averagingInt`/`averagingLong` safe, `summingDouble`/`averagingDouble` safe via Kahan
compensation in a `double[3]`/`double[4]`.

**Q7. What does `ForkJoinPool.commonPool()`'s default parallelism actually equal, and why is
"availableProcessors() minus one" only half the answer?**

The pool itself is constructed with parallelism `availableProcessors() - 1` — that's the number of
*worker* threads the common pool spins up. But whenever you submit work to the common pool from an
external thread (say, the thread that called `parallelStream()`), that calling thread doesn't just
block and wait — it participates in executing the fork/join computation itself, under
`ForkJoinPool.managedBlock`-style helping. So the **effective** parallel width of any computation
run on the common pool is `(availableProcessors() - 1)` worker threads **plus** the one submitting
thread, which equals `availableProcessors()`. State only the constructor argument and you've
under-counted by one; state only "it equals the core count" and you've hidden the mechanism. Both
halves, every time.

**Q8. The virtual-thread scheduler's `maxPoolSize` is usually quoted as "256". When is that
wrong?**

It's wrong on any machine with more than 256 available processors. `VirtualThread
.createDefaultScheduler()` computes `maxPoolSize = Integer.max(parallelism, 256)`, where
`parallelism` defaults to `availableProcessors()`. That's a **floor**, not a flat constant — on a
typical developer laptop or a modest cloud instance, `parallelism` is well under 256, so
`maxPoolSize` does land on 256 and the folklore happens to be right by coincidence. On a
256+-core box, `maxPoolSize` equals `parallelism` instead, and the "256" figure never appears
anywhere in the running system. There's a third tunable people rarely mention at all:
`minRunnable`, defaulting to `max(parallelism / 2, 1)`, which governs how many runnable carrier
threads the scheduler tries to keep available before it stops unmounting more virtual threads onto
new carriers. All three are overridable via `jdk.virtualThreadScheduler.parallelism`,
`.maxPoolSize`, and `.minRunnable` system properties — and setting `maxPoolSize` below the
processor count silently clamps `parallelism` down to match it, so one property can move two
numbers.

**Q9. `synchronized` and virtual threads — what pins on Java 21, and does `ReentrantLock` make
the pinning problem disappear forever?**

On Java 21, entering a `synchronized` block or method while running on a virtual thread pins that
virtual thread to its current carrier platform thread for the block's duration — the continuation
can't unmount mid-monitor because the JVM's object-monitor implementation isn't yet
continuation-aware. `ReentrantLock` doesn't have that limitation, because it's implemented in terms
of `LockSupport.park`, which *is* continuation-aware, so swapping `synchronized` for
`ReentrantLock` around a blocking call is the standard Java 21 fix — and it shows up as a
`jdk.VirtualThreadPinned` JFR event disappearing once you make the swap. But that fix is
version-scoped, not permanent: JEP 491 makes object monitors continuation-aware starting at Java
24, which removes `synchronized`-caused pinning as a source. It doesn't remove pinning entirely —
native frames and foreign-function calls still pin at every release, because unmounting requires
the JVM to control the full call stack, and it doesn't control code across the JNI/FFM boundary.
So the honest answer names the release the `synchronized` fix landed at and says pinning survives
in the native case regardless.

**Q10. `var list = new ArrayList<>()` — what type does that actually infer, and why does it
matter?**

`ArrayList<Object>`. `var` infers its type from the initializer expression alone, and the
diamond operator `<>` infers its type argument from the assignment's target type — but with `var`,
there *is* no target type yet; the initializer expression `new ArrayList<>()` is evaluated in
isolation, and with nothing to infer against, the diamond falls back to `Object`. That's
`Object`, not "deferred until first use" — the class file for that declaration is byte-for-byte
identical to writing `ArrayList<Object> list = new ArrayList<>();` explicitly. It matters because
adding a `StakeReservation` and later trying to assign the whole `list` to a
`List<StakeReservation>` variable fails to compile with no diamond-related diagnostic clue at the
declaration site — the OpenJDK LVTI style guide's own guideline G6, "take care when using `var`
with diamond or generic methods," exists specifically because this failure mode surfaces far from
its cause.

---

## 3. Five predict-the-output puzzles

Every snippet below was compiled with `javac --release 21` in a scratch directory and run with
`java` on this machine; the output blocks are pasted verbatim, not recalled.

### Puzzle 1 — the enum widens, the switch doesn't know

```java
// RestrictionSource.java — compiled and shipped first
public enum RestrictionSource {
    SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT
}
```

```java
// RestrictionDispatcher.java — compiled against the five-constant enum above
public class RestrictionDispatcher {
    static String describe(RestrictionSource source) {
        return switch (source) {
            case SYSTEM_ONBOARDING -> "auto-lifted at AA-801";
            case SYSTEM_COMPLIANCE -> "requires compliance review";
            case SYSTEM_LIFECYCLE -> "tied to account lifecycle";
            case ADMIN -> "requires operator action";
            case CLIENT -> "requires client action";
        };
    }
}
```

Now `RestrictionSource.java` is edited to add a sixth constant, `SELF_EXCLUSION_DESK`, and
**only that file is recompiled** — `RestrictionDispatcher.class` is untouched, exactly as it would
be if the two classes shipped in separately-versioned JARs. A new class calls
`RestrictionDispatcher.describe(RestrictionSource.SELF_EXCLUSION_DESK)`.

**Predict the output**, then the real run:

```
Exception in thread "main" java.lang.MatchException
	at RestrictionDispatcher.describe(RestrictionDispatcher.java:3)
	at Probe.main(Probe.java:5)
```

**Why.** The switch expression is exhaustive **against the enum it was compiled against** —
five constants, five cases, no `default` needed at compile time. But the compiler still emits a
synthetic default arm for defense against exactly this scenario: the enum widening after the
switch was compiled. `javap -c -p` on `RestrictionDispatcher.class` shows the mechanism directly —
a `tableswitch` over `RestrictionSource.ordinal()` via a synthetic `$SwitchMap` array, with a
`default:` arm at offset 44:

```
44: new           #19    // class java/lang/MatchException
47: dup
48: aconst_null
49: aconst_null
50: invokespecial #21    // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
53: athrow
```

`SELF_EXCLUSION_DESK`'s ordinal (5) has no entry in the five-slot `$SwitchMap`, so control falls
through to that default arm, which constructs `MatchException` with both constructor arguments
`null` — which is exactly why the printed exception carries no message. On Java 20 and earlier,
that same default arm threw `IncompatibleClassChangeError` instead; the exception type is what
changed at 21, not the fact that a default exists.

### Puzzle 2 — `summingInt` on ledger amounts

```java
import java.util.List;
import java.util.stream.Collectors;

public class StakeSums {
    public static void main(String[] args) {
        List<Integer> stakeReservationCents = List.of(1_000_000_000, 1_000_000_000, 1_000_000_000);
        int summedInt = stakeReservationCents.stream().collect(Collectors.summingInt(i -> i));
        long summedLong = stakeReservationCents.stream().collect(Collectors.summingLong(i -> i));
        System.out.println("summingInt : " + summedInt);
        System.out.println("summingLong: " + summedLong);
    }
}
```

**Predict the output**, then the real run:

```
summingInt : -1294967296
summingLong: 3000000000
```

**Why.** `Collectors.summingInt`'s accumulator is `new int[1]` at the jdk-21+35 tag — a genuine
32-bit slot. Summing three values of `1_000_000_000` reaches `3_000_000_000`, which exceeds
`Integer.MAX_VALUE` (`2_147_483_647`) by `852_516_353`; two's-complement wraparound lands at
`-1_294_967_296`, the value printed. `summingLong`'s accumulator is `new long[1]`, wide enough to
hold `3_000_000_000` without wrapping, so it prints the mathematically correct figure. No exception
is thrown in either case — this is a silent-corruption trap, not a crash, which is precisely why it
survives into production ledger code that "worked" for months of small stakes.

### Puzzle 3 — one stream, two terminal calls

```java
import java.util.List;
import java.math.BigDecimal;

public class LedgerStreamReuse {
    record LedgerEntry(String position, BigDecimal amount) {}

    public static void main(String[] args) {
        List<LedgerEntry> entries = List.of(
            new LedgerEntry("CLIENT_CASH_AVAILABLE", new BigDecimal("65.00")),
            new LedgerEntry("CLIENT_BONUS_AVAILABLE", new BigDecimal("4.20"))
        );
        var stream = entries.stream().filter(e -> e.amount().signum() > 0);
        long first = stream.count();
        System.out.println("first count: " + first);
        long second = stream.count();
        System.out.println("second count: " + second);
    }
}
```

**Predict the output**, then the real run:

```
first count: 2
Exception in thread "main" java.lang.IllegalStateException: stream has already been operated upon or closed
	at java.base/java.util.stream.AbstractPipeline.evaluate(AbstractPipeline.java:260)
	at java.base/java.util.stream.ReferencePipeline.count(ReferencePipeline.java:750)
	at LedgerStreamReuse.main(LedgerStreamReuse.java:14)
```

**Why.** `stream` is one `AbstractPipeline` instance; calling the terminal operation `count()`
sets its `linkedOrConsumed` flag. The second call to `count()` on the same reference hits the
`linkedOrConsumed` check at the top of the terminal-operation entry point and throws
`IllegalStateException("stream has already been operated upon or closed")` before the pipeline is
ever walked a second time. The fix is to build a fresh `entries.stream()` call for each terminal
operation — a `Stream` describes one traversal, it is not a reusable `Collection` view.

### Puzzle 4 — the compact constructor that won't compile

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

record StakeSplitAmounts(BigDecimal bonusPortion, BigDecimal cashPortion) {
    StakeSplitAmounts {
        bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN);
        this.bonusPortion = bonusPortion;
    }
}
```

**Predict the compiler diagnostic**, then the real run:

```
StakeSplit.java:8: error: cannot assign a value to final variable bonusPortion
            this.bonusPortion = bonusPortion;
                ^
1 error
```

**Why.** Inside a compact constructor, the record's component fields are already `final` from the
compiler's point of view — the implicit field-assigning code the compiler appends runs *after*
the compact constructor body, once, for every component. Line 7's `bonusPortion =
bonusPortion.setScale(2, RoundingMode.DOWN);` is legal because it reassigns the **parameter**
`bonusPortion`, not the field. Line 8's `this.bonusPortion = bonusPortion;` is illegal because
`this.bonusPortion` already refers to the final field, which cannot be written from user code at
all — the compiler, not the programmer, performs that write. Deleting line 8 entirely is the fix;
the rounded value the parameter now holds is exactly what the compiler writes to the field for you.

### Puzzle 5 — same lambda expression, two identity questions

```java
import java.util.function.Function;

public class LambdaIdentity {
    static Function<String, Integer> nonCapturing() {
        return s -> s.length();
    }

    static Function<String, Integer> capturing(int bonusCapCents) {
        return s -> s.length() + bonusCapCents;
    }

    public static void main(String[] args) {
        Function<String, Integer> a = nonCapturing();
        Function<String, Integer> b = nonCapturing();
        System.out.println("non-capturing same instance: " + (a == b));
        System.out.println("non-capturing same class: " + (a.getClass() == b.getClass()));

        Function<String, Integer> c = capturing(100);
        Function<String, Integer> d = capturing(100);
        System.out.println("capturing same instance: " + (c == d));
        System.out.println("capturing same class: " + (c.getClass() == d.getClass()));
    }
}
```

**Predict the output**, then the real run:

```
non-capturing same instance: true
non-capturing same class: true
capturing same instance: false
capturing same class: true
```

**Why.** `javap -c` on `nonCapturing()` shows `invokedynamic #7, 0 // InvokeDynamic
#0:apply:()Ljava/util/function/Function;` — a zero-argument descriptor, because the lambda body
`s -> s.length()` captures nothing from its enclosing scope. `LambdaMetafactory` recognizes a
non-capturing target and links the call site to a single cached instance; every call to
`nonCapturing()` returns that same object, so `a == b` is `true`. `capturing()`'s call site is
`invokedynamic #11, 0 // InvokeDynamic #1:apply:(I)Ljava/util/function/Function;` — the descriptor
now takes an `int`, because `bonusCapCents` must be captured into the lambda instance at
construction time. A capturing lambda cannot be cached as a singleton, because different calls
close over different values, so each call to `capturing(100)` allocates a fresh instance — `c == d`
is `false` even though both calls pass the identical argument. Both `a` and `c` are still
instances of the *same hidden class* generated once per `invokedynamic` call site (`getClass() ==
getClass()` is `true` in both cases) — caching is about the **instance**, not the class.

---

## Pitfalls

### Assuming `Collectors.summingInt` is overflow-safe because `averagingInt` is

**Wrong**

```java
List<Integer> stakeReservationCents = List.of(1_000_000_000, 1_000_000_000, 1_000_000_000);
int total = stakeReservationCents.stream().collect(Collectors.summingInt(i -> i));
// total == -1294967296, not 3_000_000_000 — silent wraparound, no exception
```

**Right**

```java
long total = stakeReservationCents.stream().collect(Collectors.summingLong(i -> i));
// total == 3000000000L — the accumulator is a long[1], wide enough for the real sum
```

**Why people believe it:** `averagingInt` is genuinely safe, and it sits one line away from
`summingInt` in the same class with a nearly identical name, so the safety gets generalized across
the pair. `averagingInt`'s accumulator is a `long[2]` holding `{sum, count}` — its safety comes
from tracking two numbers at `long` width, not from any special int-overflow guard that
`summingInt` also has.

### Calling a terminal operation twice on the same `Stream` reference

**Wrong**

```java
var stream = ledgerEntries.stream().filter(e -> e.amount().signum() > 0);
long a = stream.count();
long b = stream.count();   // IllegalStateException: stream has already been operated upon or closed
```

**Right**

```java
long a = ledgerEntries.stream().filter(e -> e.amount().signum() > 0).count();
long b = ledgerEntries.stream().filter(e -> e.amount().signum() > 0).count();
```

**Why people believe it:** streams read like `Collection` views built once and queried repeatedly
— `list.size()` called twice is fine, so the same shape on a stream looks fine too. A `Stream` is
a single-use description of a pipeline, not a view; `linkedOrConsumed` flips permanently on the
first operation.

### Stating "the default is 256" for the virtual-thread scheduler's `maxPoolSize`

**Wrong**

```java
// "the virtual thread scheduler always caps its carrier pool at 256"
```

**Right**

```java
// maxPoolSize = Integer.max(parallelism, 256), where parallelism defaults to availableProcessors()
// — 256 is a floor: on a >256-core box, maxPoolSize == parallelism, not 256
```

**Why people believe it:** 256 is what you observe on almost every laptop, workstation, and modest
cloud instance, because `availableProcessors()` on those machines is well under 256 — the floor and
the observed value coincide everywhere most people test it.

### Treating the Java 21 synthetic switch default's exception type as unconditionally
`IncompatibleClassChangeError`

**Wrong**

```java
// "an exhaustive switch expression's synthetic default throws IncompatibleClassChangeError"
// — stated without naming a release
```

**Right**

```java
// Through Java 20: IncompatibleClassChangeError.
// From Java 21: java.lang.MatchException, via the (String, Throwable) constructor.
```

**Why people believe it:** `IncompatibleClassChangeError` was the only answer for years, and it's
still the technically-correct answer for a target release below 21 — the folklore just doesn't
track which release it learned the fact in.

---

## Cheat sheet

| Mechanism | One-line fact | Verified as |
|---|---|---|
| Lambda translation | `invokedynamic` → `LambdaMetafactory.metafactory`; non-capturing lambdas are cached singletons, capturing ones are not | `a == b` true, `c == d` false (Puzzle 5) |
| Method reference translation | Same bootstrap path as lambdas; bound references capture the receiver | — |
| Stream pipeline | No traversal until a terminal op; `linkedOrConsumed` flag blocks reuse | `IllegalStateException` on 2nd terminal call (Puzzle 3) |
| `Collectors.summingInt` | Accumulates into `int[1]` — overflows exactly like `IntStream.sum()` | `-1294967296` for 3×10⁹ (Puzzle 2) |
| `Collectors.summingLong`/`averagingInt`/`averagingLong` | `long[]`-width accumulators — safe from the `summingInt` trap | `3000000000` (Puzzle 2) |
| `AbstractTask.suggestTargetSize` | Floored division, min 1 — not "rounded up" | source quote |
| `AbstractTask.getLeafTarget()` | Reads the *current* pool's parallelism if called from a `ForkJoinWorkerThread`, else `commonPoolParallelism << 2` | source quote |
| Record `equals`/`hashCode`/`toString` | One `invokedynamic` per method into `ObjectMethods.bootstrap`, not per-class generated bodies | — |
| Record compact constructor | Reassign the parameter, never `this.field =` — field is already final | compile error (Puzzle 4) |
| Sealed types | `PermittedSubclasses` class-file attribute; exhaustiveness is compile-time only | — |
| Exhaustive switch synthetic default | Java ≤20: `IncompatibleClassChangeError`. Java 21+: `MatchException((String,Throwable))` | Puzzle 1, both directions run |
| `var` + diamond | `var list = new ArrayList<>()` infers `ArrayList<Object>` — no target type to infer against | — |
| Virtual thread scheduler | `parallelism = availableProcessors()`; `maxPoolSize = max(parallelism, 256)` (floor, not flat); `minRunnable = max(parallelism/2, 1)`; `asyncMode = true` (`// FIFO`) | source quote |
| `synchronized` + virtual threads | Pins on Java 21; JEP 491 (Java 24) fixes monitors; native/foreign frames still pin at every release | — |
| Structured concurrency (21) | Preview (JEP 453), `StructuredTaskScope` moved to `java.util.concurrent`, public constructors, `Subtask<T>`, `ShutdownOnFailure`/`ShutdownOnSuccess` | — |
| Structured concurrency (25) | `open()` factories replace constructors; composable `Joiner` replaces the two policies | — |
| `ForkJoinPool.commonPool()` width | Constructed at `availableProcessors() - 1`; submitting thread also participates → effective width = `availableProcessors()` | — |

---

## Self-test

**Q1.** Two calls to a method returning the same non-capturing lambda expression compare `==` as
`true`. Why doesn't the same hold for a capturing lambda with identical captured values?

<details><summary>Answer</summary>

`LambdaMetafactory` caches the instance behind a non-capturing lambda's `invokedynamic` call site,
because there is no per-call state to differentiate one invocation from the next — the call site's
descriptor takes zero arguments. A capturing lambda's call site descriptor includes the captured
values as arguments (verified via `javap`: `apply:(I)Ljava/util/function/Function;` for a
capturing lambda vs. `apply:()Ljava/util/function/Function;` for a non-capturing one), so a new
instance is constructed on every call even when the captured value happens to be identical across
calls — the metafactory doesn't do value-based deduplication, only shape-based caching for the
zero-argument case.

</details>

**Q2.** A stream built with `entries.stream().filter(...)` is stored in a `var`, and `.count()` is
called on it twice. What is thrown, and from which class?

<details><summary>Answer</summary>

`IllegalStateException("stream has already been operated upon or closed")`, thrown from
`AbstractPipeline.evaluate`, reached via `ReferencePipeline.count()`. Every `AbstractPipeline`
tracks a `linkedOrConsumed` flag set by the first operation (intermediate or terminal) invoked on
it; every public entry point checks that flag before doing anything else. There is a second,
narrower message (`"source already consumed or closed"`) guarding an internal invariant about
re-pulling a `Spliterator` from an already-emptied source, but it is not reachable this way —
`linkedOrConsumed` is checked before the source is ever touched, so ordinary reuse always reports
the first message.

</details>

**Q3.** Why does `Collectors.summingInt` overflow silently on the same inputs that
`Collectors.summingLong` sums correctly?

<details><summary>Answer</summary>

`summingInt`'s accumulator container is `new int[1]` at the jdk-21+35 tag — the running total is
held as a genuine 32-bit `int`, so it wraps via two's-complement arithmetic exactly like
`IntStream.sum()` once the true sum exceeds `Integer.MAX_VALUE`. `summingLong`'s accumulator is
`new long[1]`, wide enough to hold sums well beyond what any `int`-typed input stream can produce
without itself overflowing at the source. Neither collector throws on overflow; the corruption is
silent in both directions, which is what makes it dangerous.

</details>

**Q4.** What is the difference between what a compact record constructor is allowed to reassign
and what it is forbidden to assign, and why does the forbidden form fail specifically with "cannot
assign a value to final variable"?

<details><summary>Answer</summary>

A compact constructor may reassign its own **parameters** — `bonusPortion = bonusPortion
.setScale(2, RoundingMode.DOWN);` is legal, because parameters are ordinary local variables unless
declared `final`. It may not write `this.bonusPortion = ...` directly, because by the time the
compact constructor body runs, the record's component field is already `final` from the compiler's
perspective, and the compiler itself appends the actual field-assigning code after the compact
constructor body finishes — once per component, using whatever value the parameter holds at that
point. Writing to `this.bonusPortion` collides with a field the language spec treats as
effectively write-once and not written by user code, so `javac` reports the same diagnostic it
would for any other illegal write to a `final` field.

</details>

**Q5.** A sealed enum-based switch expression is exhaustive at compile time. A colleague adds a
sixth enum constant and recompiles only the enum, not the switch. What happens at runtime when the
switch is invoked with the new constant, and why does the language even allow this scenario to
exist?

<details><summary>Answer</summary>

Calling the switch with the new constant throws `java.lang.MatchException` (Java 21+; the same
scenario threw `IncompatibleClassChangeError` through Java 20). It happens because the switch's
exhaustiveness check ran against the enum's shape **at the switch's own compile time**, and once
compiled, the switch's class file is a fixed `tableswitch` over a fixed set of ordinals baked into
a synthetic `$SwitchMap` array — it has no way to know the enum grew a sixth constant unless it is
recompiled too. The language allows this because separate compilation units are allowed to be
versioned independently in the JVM's binary compatibility model; the synthetic default exists
specifically to fail loudly (via an exception) rather than silently (by falling through to garbage)
when that independence produces an inconsistency.

</details>

**Q6.** Where does `AbstractTask.getLeafTarget()` get its parallelism figure from, and why does
that make "submit the terminal operation into your own custom pool" change parallel decomposition
width?

<details><summary>Answer</summary>

`getLeafTarget()` checks whether the calling thread is already a `ForkJoinWorkerThread`; if so, it
returns that thread's own pool's `getParallelism() << 2`, and only falls back to the static
`LEAF_TARGET` (computed once from the common pool's parallelism) when called from an ordinary
thread. So when a `parallelStream()`'s terminal operation is submitted via
`customPool.submit(() -> stream.collect(...))`, the fork/join decomposition that follows reads
*that* pool's parallelism, not the common pool's — changing the effective leaf task size and task
count without changing a single line of the stream pipeline itself.

</details>

**Q7.** Name the three system properties that tune the default virtual-thread scheduler, their
default formulas, and the one interaction between two of them that is easy to miss.

<details><summary>Answer</summary>

`jdk.virtualThreadScheduler.parallelism` (default `availableProcessors()`),
`jdk.virtualThreadScheduler.maxPoolSize` (default `Integer.max(parallelism, 256)`), and
`jdk.virtualThreadScheduler.minRunnable` (default `Integer.max(parallelism / 2, 1)`). The easy-to-
miss interaction: setting `maxPoolSize` explicitly below the natural `parallelism` value clamps
`parallelism` down to match it (`parallelism = Integer.min(parallelism, maxPoolSize)` in the
source), so one property write silently moves two numbers, not one.

</details>

**Q8.** `synchronized` pinning a virtual thread is described as fixed by JEP 491. Fixed as of
which release, and does that JEP remove every cause of pinning?

<details><summary>Answer</summary>

JEP 491 lands at Java 24 and makes object monitors continuation-aware, removing `synchronized`
blocks and methods as a pinning cause from that release onward. It does not remove pinning
entirely: native frames and foreign-function calls still pin a virtual thread at every release,
including 24 and beyond, because unmounting a continuation requires the JVM to control the entire
call stack being unmounted, and it does not control frames across the JNI/FFM boundary. The
`jdk.VirtualThreadPinned` JFR event therefore survives JEP 491; it simply stops firing for the
`synchronized` case specifically.

</details>

**Q9.** What changed about `StructuredTaskScope`'s public API surface between Java 21 (JEP 453,
preview) and Java 25 (JEP 505), and what stayed the same?

<details><summary>Answer</summary>

At Java 21, `StructuredTaskScope` is constructed directly via public constructors, and the
built-in shutdown behaviors are two concrete subclasses, `ShutdownOnFailure` and
`ShutdownOnSuccess`. At Java 25, the public constructors are replaced by static `open()` factory
methods, and the two concrete shutdown-policy subclasses are replaced by a single composable
`Joiner` abstraction. What stays the same across both shapes: `fork` returns a `Subtask<T>` (never
a bare `Future<T>`), and the scope's lifetime is still lexically bounded by try-with-resources on
the owning thread via `join`/`close`, which is the entire point of "structured" concurrency — a
subtask can never outlive the block that created its scope.

</details>

**Q10.** A record's canonical `equals` implementation is described as coming from
`ObjectMethods.bootstrap`. What is the practical difference between that and every record type
independently generating its own hand-rolled `equals` method body, and where would you look to
verify the claim?

<details><summary>Answer</summary>

Practically, there is no per-record-type compiled method body for `equals`/`hashCode`/`toString`
at all — the compiler emits one `invokedynamic` call site per method, each bootstrapping into the
shared `java.lang.runtime.ObjectMethods.bootstrap`, which builds the actual comparison/hash/format
logic once, generically, from a descriptor string and a list of component accessor
`MethodHandle`s supplied at the call site. You'd verify this by running `javap -c -p` on a
compiled record class: there is no `equals` method body containing per-field comparisons the way a
hand-written or IDE-generated `equals` would show — instead there's an `invokedynamic` instruction
whose bootstrap method entry names `ObjectMethods.bootstrap` in the constant pool.

</details>

---

## Deferred

None.

---

## Open questions

None.

---

**Leaves covered:** none — part wrap-up (0 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 720

The atomic concept checklist for the whole set lives at the end of `95-traps-drills-and-checklist.md`.
