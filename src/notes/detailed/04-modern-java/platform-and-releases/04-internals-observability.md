# 04 Modern Java — The platform and the release model — INTERNALS (§3.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The platform and the release model — internals version delta](03-internals-version-delta.md) · Next: [Functional interfaces — basics](../functional-interfaces/01-basics.md)

Every claim in Parts 1–3 of this subject — the lambda indy, the record indy, the pattern-switch
indy, the text-block constant, the virtual-thread scheduler defaults, the `ForkJoinPool` leaf
target — has been stated as fact. This file is where you stop taking those claims on faith and
learn the toolchain that lets you re-derive every one of them yourself, on your own machine,
against your own code. That is also the actual interview skill: a Staff-level answer to "are you
sure?" is not a firmer tone of voice, it is `javap -c -p -v` output.

## Which concepts get the full treatment

Four primary concepts carry all eight beats: **`javap -c -p -v` as the evidence discipline**, **JFR
for this topic**, **JMH discipline**, and **static analysis for `Optional`/`Stream` misuse**. Eight
supporting facts get three beats each: `jshell` micro-experiments, `-Djdk.internal.lambda.dumpProxyClasses`,
`-Xlog:class+load=info`, `jcmd Thread.dump_to_file -format=json`, `jcmd Thread.print`,
async-profiler, IDE tooling, and confirm-before-you-quote flags/properties.

---

## D-168 — the tooling map for this topic

Before any of the eight beats, here is the map. Every tool below is used at least once in this
file; the last column tells you where.

| Command / flag | What it verifies | What the output looks like | Used in |
|---|---|---|---|
| `javap -c -p -v Foo.class` | Any desugaring claim: lambda indy, record indy, pattern-switch indy, text-block constant | Constant pool entries, per-method bytecode, `BootstrapMethods:` table | § javap discipline, below |
| `jshell` | Fast falsification of a specific behavioural claim without a build | REPL echoes the expression's value and type after each line | § jshell, below |
| `-Djdk.internal.lambda.dumpProxyClasses=<dir>` | That a lambda really does spin a hidden class, and what that class contains | `.class` files named `Outer$$Lambda$N` written to `<dir>` at first call-site invocation | § dumpProxyClasses, below |
| `-Xlog:class+load=info` | When a hidden lambda class is loaded relative to other classes | One `[info][class,load]` line per class, in load order, with the loader named | § class+load, below |
| `jdk.VirtualThreadStart` / `End` / `Pinned` / `SubmitFailed` (JFR) | Virtual-thread lifecycle and pinning, per-thread | JFR recording rows: thread id, timestamp, and for `Pinned` a stack trace and reason | § JFR, below |
| `jdk.ObjectAllocationSample` (JFR) | Boxing/allocation pressure attributed to a call site | Sampled allocation events with weight, type, and stack trace | § JFR, below |
| `jdk.JavaExceptionThrow` (JFR) | Exception-throw rate and origin, including hidden ones (e.g. from `Optional.get()`) | Sampled throw events with exception class and stack trace | § JFR, below |
| `jcmd <pid> Thread.dump_to_file -format=json <file>` | Virtual-thread trees and scope structure at a point in time | A JSON document with `threadDump.threadContainers`, each holding platform and virtual threads | § jcmd JSON dump, below |
| `jcmd <pid> Thread.print` | Platform-thread stacks, held monitors, and deadlock cycles | Text thread dump: `"pool-1-thread-3" ... waiting to lock <0x...> ... Found one Java-level deadlock` | § jcmd Thread.print, below |
| async-profiler (`asprof`/`profiler.sh`) | Where CPU or allocation time actually goes across a lambda/stream/ForkJoin chain | Flame graph or collapsed stacks with frames like `StakeReservationPipeline$$Lambda.0x.../0` | § async-profiler, below |
| JMH (`@Benchmark`, `Blackhole`) | Whether a stream-vs-loop or parallel-vs-sequential claim survives warm-up and dead-code elimination | A results table: `Benchmark`, `Mode`, `Cnt`, `Score`, `Error`, `Units` | § JMH discipline, below |
| IntelliJ stream debugger / "Trace Current Stream Chain" | What flows through each pipeline stage, element by element | A side panel showing each stage's input/output collection at a breakpoint | § IDE tooling, below |
| ErrorProne / SpotBugs / SonarQube / NullAway rules | Static, compile-time-or-later detection of `Optional`/`Stream` misuse | Build-time warnings or failures naming the rule and the offending line | § Static analysis, below |
| `-XX:+PrintFlagsFinal` | The actual value of a VM flag on this JVM, not the documented default | One line per flag: `bool UseCompressedOops = true {product}` | § confirm-before-you-quote, below |
| `System.getProperties()` | Scheduler and other system properties actually in effect | A `Properties` map printable as `key=value` pairs | § confirm-before-you-quote, below |
| `ForkJoinPool.getCommonPoolParallelism()` | The common pool's actual width on this machine | An `int` | § confirm-before-you-quote, below |

**D-168** — The tooling map for this topic

---

### `javap -c -p -v` as the evidence discipline

**Mental model.** Every claim this subject makes about desugaring — "a lambda compiles to an
`invokedynamic`", "a record's accessor is a real method, not a field read", "the pattern-switch's
synthetic default throws `MatchException`" — is a claim about what `javac` emitted into a
`.class` file. `javap -c -p -v` is not a debugging tool here; it is the primary source for this
whole subject, one level below the JLS itself. `-c` disassembles bytecode, `-p` shows private and
synthetic members (which is where the lambda body actually lives), `-v` adds the verbose
constant-pool and attribute dump, which is where `BootstrapMethods:` lives. Without all three
flags together you see the call site but not the machinery behind it.

**Why it exists.** Before `javap`, the only way to inspect what `javac` produced was to read the
class-file format spec (JVMS §4) and a hex editor, or trust the compiler's behaviour by
assumption. `javap` is the JDK's own answer to "don't take my word for it" — it ships in the same
`bin/` directory as `javac` and reads the exact same class-file format the JVM loads.

**When to reach for it, and when not.** Reach for it whenever a claim in these notes, a blog post,
or an interviewer's assertion is about *compiled shape* — what bytecode a language construct
produces. Do not reach for it to understand *runtime behaviour that bytecode doesn't encode* —
GC pause causes, JIT inlining decisions, or thread scheduling; those need JFR, async-profiler, or
`-XX:+PrintCompilation`, not a disassembler. A pattern-switch's *runtime* dispatch strategy (binary
search vs. `invokedynamic`-based `SwitchBootstraps.typeSwitch`) is visible in the bytecode, but
*whether the JIT actually devirtualizes a call inside it* is not — that needs `-XX:+PrintInlining`,
which is guide 06's territory.

**How it works.** `javap` reads the class file's constant pool and code attributes directly; it
performs no re-compilation and no interpretation — it is a straight structural dump. The three
things worth knowing about its output structure: (1) every `invokedynamic` instruction references
a `BootstrapMethods` table entry by index, and that table entry names the actual bootstrap method
(`LambdaMetafactory.metafactory` for lambdas, `ObjectMethods.bootstrap` for records,
`SwitchBootstraps.typeSwitch` for pattern switches); (2) synthetic lambda bodies are compiled into
private static (or private instance, if the lambda captures `this`) methods named
`lambda$<enclosingMethod>$<n>` on the enclosing class — `-p` is what makes these visible, since
they are `ACC_PRIVATE ACC_SYNTHETIC`; (3) each lambda expression gets its own bootstrap method
table row and its own `invokedynamic` call site, even when two lambdas in the same method have
textually identical bodies — the JVM does not deduplicate at the class-file level.

There is no dedicated diagram for the `javap` disassembly pipeline — source, class file, constant
pool, and the `BootstrapMethods` table that ties an `invokedynamic` instruction to
`LambdaMetafactory`. D-168 is the manifest's tooling map for this section and renders as the
Markdown table above; the pipeline itself is best shown directly in real output, below.

**Code and reading.** Compiled with `javac --release 21` from a two-stage filter over stake
reservations, one lambda captures a local (`threshold`), the other does not:

```java
record StakeReservation(String reservationId, java.math.BigDecimal amount, String status) {}

static long countHighValue(java.util.List<StakeReservation> reservations,
                            java.math.BigDecimal threshold) {
    java.util.function.Predicate<StakeReservation> isHighValue =
            r -> r.amount().compareTo(threshold) > 0;
    return reservations.stream()
            .filter(isHighValue)
            .filter(r -> "AA-801".equals(r.status()))
            .count();
}
```

`javap -c -p -v` on the compiled class produces, among the constant pool entries:

```
#7  = InvokeDynamic      #0:#8   // #0:test:(Ljava/math/BigDecimal;)Ljava/util/function/Predicate;
#23 = InvokeDynamic      #1:#24  // #1:test:()Ljava/util/function/Predicate;
```

and in `countHighValue`'s code:

```
0: aload_1
1: invokedynamic #7,  0    // InvokeDynamic #0:test:(Ljava/math/BigDecimal;)Ljava/util/function/Predicate;
6: astore_2
7: aload_0
8: invokeinterface #11,  1 // InterfaceMethod java/util/List.stream:()Ljava/util/stream/Stream;
13: aload_2
14: invokeinterface #17,  2 // InterfaceMethod java/util/stream/Stream.filter:(Ljava/util/function/Predicate;)Ljava/util/stream/Stream;
19: invokedynamic #23,  0  // InvokeDynamic #1:test:()Ljava/util/function/Predicate;
24: invokeinterface #17,  2 // InterfaceMethod java/util/stream/Stream.filter:(Ljava/util/function/Predicate;)Ljava/util/stream/Stream;
29: invokeinterface #26,  1 // InterfaceMethod java/util/stream/Stream.count:()J
34: lreturn
```

Reading it instruction by instruction: `0: aload_1` pushes the captured local `threshold` onto the
stack — this is the evidence that the *capturing* lambda's `invokedynamic` (`#7`) takes an extra
argument, while the non-capturing one (`#23`, invoked at `19:`) is called with zero arguments
pushed first. `1: invokedynamic #7, 0` is the call site itself: it does not call the lambda body —
it calls the bootstrap method (once, lazily, the first time this instruction executes) to produce
a `CallSite`, then invokes that site's target, which returns a `Predicate` instance. `6: astore_2`
stores that `Predicate` into local slot 2 (`isHighValue`). The two `filter` calls at `14:` and
`24:` are ordinary `invokeinterface` calls on `Stream` — filtering itself is not desugared, only
the lambda arguments to it are. And in the `BootstrapMethods:` table:

```
BootstrapMethods:
  0: #79 REF_invokeStatic java/lang/invoke/LambdaMetafactory.metafactory:(...)Ljava/lang/invoke/CallSite;
    Method arguments:
      #71 (Ljava/lang/Object;)Z
      #72 REF_invokeStatic StakeReservationPipeline.lambda$countHighValue$0:(Ljava/math/BigDecimal;StakeReservationPipeline$StakeReservation;)Z
      #75 (StakeReservationPipeline$StakeReservation;)Z
```

Bootstrap method `0` names `LambdaMetafactory.metafactory` as the thing the JVM calls the first
time `invokedynamic #7` executes, and its second `Method arguments` entry
(`#72`) is a direct handle to `lambda$countHighValue$0` — the private static synthetic method that
is the *actual body* of the capturing lambda, visible only because `-p` was passed. Without `-p`
this method is invisible in the member listing even though the bootstrap table still references
it by name.

**Gotcha.** `-c` alone (no `-p`, no `-v`) shows you the `invokedynamic` instruction but not the
`BootstrapMethods:` table, so you see *that* a lambda is desugared but not *to what* — that is the
single most common way a `javap` demonstration falls apart mid-interview, because the presenter
forgot `-v`.

> **`javap -c -p -v` is the disassembler that turns a desugaring claim into a constant-pool fact:
> `-c` for bytecode, `-p` for the synthetic lambda bodies, `-v` for the `BootstrapMethods:` table
> that names the actual bootstrap method.**

---

### `jshell` for a ten-second experiment

**Mechanism.** `jshell` compiles and executes each top-level snippet immediately, in a session
that keeps prior declarations live — it is not a toy REPL, it runs the same `javac` front end and
the same HotSpot back end as a compiled program, just without a `main` method or a build step.
Four falsifications worth having memorised as `jshell` one-liners: (1) `peek` elision —
`java.util.stream.Stream.of(1,2,3).peek(System.out::println)` prints nothing at all, because
`peek` is an intermediate operation and the pipeline has no terminal operation, so nothing ever
calls `evaluate`; add `.count()` and the elements print, but on Java 9+ `count()` on a
`SIZED`-and-unfiltered source can short-circuit via `Stream.SORTED`/size metadata and skip
traversal entirely for some sources — the safe falsification terminal is `.forEach(x -> {})` or
`.toList()`. (2) `Optional.empty()` identity — `Optional.empty() == Optional.empty()` evaluates to
`true` in `jshell`, because `Optional.EMPTY` is a private static final singleton, not a new
allocation per call. (3) Text-block indentation — pasting
`String q = """\n    SELECT * FROM stake_reservation\n    """;` and then `q.length()` shows the
common leading whitespace has been stripped per JLS §3.10.6's incidental-whitespace algorithm, not
preserved literally. (4) `Stream.toList()` immutability — `var xs = java.util.stream.Stream.of(1,2).toList(); xs.add(3);`
throws `UnsupportedOperationException`, unlike `Collectors.toList()`'s historically-mutable
`ArrayList` result.

**Gotcha.** `jshell`'s default classpath and preview-feature flags differ from a project's build —
a snippet that behaves one way in `jshell` and another way in a Maven build is usually a
`--enable-preview` or module-path mismatch, not a JDK bug.

> **`jshell` is a full compile-and-run loop with no build step — good for falsifying one specific
> claim in ten seconds, not for anything that needs a classpath.**

---

### `-Djdk.internal.lambda.dumpProxyClasses=<dir>` to inspect the spun class `[RESEARCH]` `[VERSION-TRAP]`

**Mechanism.** Setting this system property causes `InnerClassLambdaMetafactory` (the
implementation behind `LambdaMetafactory.metafactory`, JDK internal package
`java.lang.invoke`) to write the hidden lambda class it generates to `<dir>` as an ordinary
`.class` file, named like `StakeReservationPipeline$$Lambda$1`, instead of only defining it
in-memory via `Lookup.defineHiddenClass`. Once written, it is an ordinary file `javap -c -p -v`
can disassemble like any other class — this is the flag that turns "the JVM spins a hidden class
for each capturing lambda shape" from an assertion into a file you can open.

**`[VERSION-TRAP]`:** the flag's *name* is unchanged since Java 8, but the *mechanism* it exposes
is not. Through Java 8, spun lambda classes were ordinary (non-hidden) classes defined by an
anonymous class loader and visible in a heap dump as regular loaded classes. From Java 9 onward
(after `Lookup.defineHiddenClass`, formalized by JEP 371 in Java 15) the runtime-generated lambda
class is a genuine **hidden class**: it has no name resolvable through normal classloading, is
unregistered with the system dictionary, and is eligible for unloading independently of its
defining loader's other classes. The dump flag still works — you still get a `.class` file on
disk — but what you are looking at is now a dump of something that, at runtime, was never a
loadable-by-name class at all.

**`[RESEARCH]`:** re-verified against `InnerClassLambdaMetafactory` behaviour described in the
JDK internal-API javadoc and JEP 371's own text; the flag itself is undocumented (no
`java --help` entry, no JEP), which is expected for a `jdk.internal.lambda.*` diagnostic property
and is itself worth naming as a `**Pitfall:**` below.

**Pitfall:** treating an internal, undocumented property as a stable API. `jdk.internal.lambda.dumpProxyClasses`
lives in `jdk.internal.*` package namespace by convention of name, meaning it can change or vanish
release to release without a deprecation cycle; use it for research on your own machine, never
ship a build script or CI check that depends on its continued existence.

> **`-Djdk.internal.lambda.dumpProxyClasses=<dir>` writes the JVM's runtime-generated lambda class
> to disk; since Java 9 that class is a hidden class, so the flag is your only way to see it with
> `javap` at all — there's no other file path to it.**

---

### `-Xlog:class+load=info` to watch hidden classes appear `[X-REF 06]`

**Mechanism.** `-Xlog:class+load=info` is the unified-logging (JEP 158) tag for the class-loading
subsystem; each line reports one class becoming loaded, in load order, with the loader that did
it. A lambda call site's hidden class does not appear at class-initialization time — it appears
lazily, the *first* time that specific `invokedynamic` instruction executes, because
`LambdaMetafactory.metafactory` is only invoked once per call site (the JVM then caches the
resulting `CallSite` so subsequent executions skip the bootstrap entirely). Running a
stake-reservation warm-up pipeline (the two-filter example above, called once per reservation)
under this flag shows exactly one `class,load` line per distinct lambda expression in the source,
appearing at the moment the *first* stake reservation reaches that filter — not at class-load time
for `StakeReservationPipeline` itself, and not once per reservation. Guide 06 (JVM internals) owns
the full class-loading pipeline — parent delegation, the bootstrap/platform/application loader
hierarchy, and verification — this paragraph is enough to answer "when does a lambda's hidden
class actually get created" without sending you there empty-handed.

**Pitfall (`[TRAP]` via `[X-REF]` diagram context — same shape):** expecting the hidden class name
to show up under the loader you'd expect for `StakeReservationPipeline`. Since Java 9, the hidden
lambda class is defined by a fresh, per-call-site instance of an unnamed loader tied to the
lookup's owning class loader — not necessarily reused across call sites — so grepping the log for
a fixed class name is fragile; grep for the enclosing class's simple name plus `$$Lambda` instead.

> **`-Xlog:class+load=info` shows *when* a lambda call site's hidden class is created — lazily, on
> first invocation of that specific call site, once, ever — which is the mechanism behind "the
> first call through a cold lambda is slower than the rest."**

---

### JFR for this topic `[X-REF 20]`

**Mental model.** Java Flight Recorder is not a profiler you attach after the fact — it is an
always-available, low-overhead event stream built into the JVM itself, recording structured events
(each with a type, a timestamp, and typed fields) to a ring buffer or a file. For this subject, four
event types matter: `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd`, `jdk.VirtualThreadPinned`,
and `jdk.VirtualThreadSubmitFailed` for virtual-thread lifecycle; `jdk.ObjectAllocationSample` for
allocation pressure (the mechanism behind every boxing claim in this subject — autoboxing an
`int` stake amount into an `Integer` shows up here as a sampled `java.lang.Integer` allocation with
a stack trace pointing at the boxing call site); and `jdk.JavaExceptionThrow` for exception rate,
including exceptions the reader doesn't expect to be hot, like a filtered stream of
`ClientLookupException` thrown from inside a `map` stage on missing clients.

**Why it exists.** Before JFR (donated by BEA/Oracle from JRockit, GA'd in OpenJDK at Java 11
after being commercial-only through 8u), diagnosing production issues meant either attaching a
sampling profiler with real overhead, or reading log lines that were never designed to answer the
question you actually had. JFR's design goal was sub-1%-overhead, always-on instrumentation so
the data exists *before* you know you need it — "continuous recording", not "reproduce it under a
profiler."

**When to reach for it, and when not.** Reach for JFR when the question is about *what happened
in production, over time, cheaply* — pinning events during a real incident, allocation hot spots
under real traffic, exception storms. Do not reach for it as a substitute for a profiler's
call-tree view of *where CPU time goes across the whole stack* — that granularity is
async-profiler's job (below); JFR's method-profiling event samples less densely by default and
is tuned for low overhead over precision.

**How it works.** JFR events are written by the JVM at the points HotSpot itself instruments —
`jdk.VirtualThreadPinned` fires specifically when a virtual thread's carrier cannot be released
because the virtual thread is inside a `synchronized` block or executing native/foreign code (on
Java 21; see the version note below), recording the pin's duration and a stack trace at the pin
site. `jdk.ObjectAllocationSample` is a *sampling* event — it does not fire per allocation (that
would defeat the low-overhead goal) but at a configurable average sampling interval (default
around every 512 KB of allocated bytes per thread), which is why a single unlucky small
allocation may never appear while a hot loop's boxing shows up reliably over time.

The JFR event pipeline — instrumented JVM events feed a ring buffer, flushed to a recording file,
decoded by `jfr print` or JDK Mission Control — has no dedicated diagram beyond D-168's tooling
table: the sequence is one line of narrative, not a structure worth a standalone figure.

**Code.** Recording a stake-reservation warm-up and dumping the four events with the bundled
`jfr` CLI (no separate download needed — it ships in `$JAVA_HOME/bin`):

```bash
java -XX:StartFlightRecording=filename=quizstakes-warmup.jfr,duration=60s \
     -cp out StakeReservationWarmup
jfr print --events jdk.VirtualThreadPinned,jdk.ObjectAllocationSample,jdk.JavaExceptionThrow \
          quizstakes-warmup.jfr
```

A representative `jdk.VirtualThreadPinned` event, decoded:

```
jdk.VirtualThreadPinned {
  startTime = 20:14:02.881
  duration = 3.221 ms
  pinnedReason = "Native frame or <clinit>"
  eventThread = "VirtualThread-42"
  stackTrace = [
    FundsLedger.reserveStake(LedgerEntry) line: 118
    ...
  ]
}
```

**Gotcha.** `**Pitfall:**` on Java 21, `synchronized` blocks are the classic pinning cause and
`jdk.VirtualThreadPinned` is how you find them, but this is dated: JEP 491 makes monitor
acquisition continuation-friendly starting in **Java 24**, removing `synchronized`-caused pinning
entirely. Native and foreign-function frames still pin at every version, including 24+, so the
event and the diagnostic technique survive — only the dominant *cause* changes. Stating "use
`ReentrantLock` instead of `synchronized`" as a timeless fix is the version-stale answer; the
correct one names the release.

> **JFR is an always-on, low-overhead structured event stream built into the JVM; for virtual
> threads, allocation pressure, and exception rate, `jdk.VirtualThread{Start,End,Pinned,SubmitFailed}`,
> `jdk.ObjectAllocationSample`, and `jdk.JavaExceptionThrow` turn a suspicion into a stack trace.**

---

### `jcmd <pid> Thread.dump_to_file -format=json <file>` for virtual threads `[RESEARCH]`

**Mechanism.** `jcmd` sends a diagnostic command to a running JVM over its attach-API socket; the
`Thread.dump_to_file` command with `-format=json` produces a structured document whose top-level
shape (verified against the JDK 21 diagnostic-command output) groups threads into
`"threadDump" -> "threadContainers"`, each container listing its member threads with `tid`,
`name`, `stack`, and — for virtual threads specifically — the scoped-value and structured-concurrency
tree they belong to, which a flat `Thread.print` text dump cannot represent because virtual
threads are not organized as OS threads. This is the tool for the question "how many virtual
threads are alive right now, and which `StructuredTaskScope` do they belong to" — a question that
has no good answer under classic thread-dump tooling, because virtual threads at scale (tens of
thousands) would make a text dump unreadable and slow to produce; the JSON format is both machine-
parseable and organized by container rather than by raw thread count.

**`[RESEARCH]`:** the exact JSON schema is a diagnostic-command output, not a documented,
versioned public API — re-verify field names against the JDK 21 release you are actually running,
since diagnostic-command output shapes have changed release to release without a formal
deprecation process.

**Pitfall:** running `Thread.dump_to_file` (without `-format=json`) and expecting the same
structure as `Thread.print` — the default text format for a dump-to-file omits some detail
`Thread.print`'s live console output includes, and neither text format groups virtual threads by
container the way JSON does.

> **`jcmd <pid> Thread.dump_to_file -format=json <file>` is the only stock tool that shows virtual
> threads organized by their owning `StructuredTaskScope`/container rather than as a flat list.**

---

### `jcmd <pid> Thread.print` for platform threads `[X-REF 06]`

**Mechanism.** `Thread.print` (equivalently the older, separate `jstack <pid>` binary) walks the
JVM's platform-thread table and prints, per thread, its state, its full Java stack, and — the part
that makes it a deadlock tool — the monitor locks it currently *holds* (`- locked <0x...>`) versus
the one it is *waiting to acquire* (`- waiting to lock <0x...>`). The JVM's own deadlock detector
runs a cycle-detection pass over the wait-for graph built from those two relations and, when it
finds a cycle, appends a `Found one Java-level deadlock` section naming every thread and lock in
the cycle. Virtual threads are deliberately **excluded** from `Thread.print`'s default output —
by design, since a production JVM can have hundreds of thousands of them and a text dump of all of
them would be both enormous and mostly transient — which is precisely why the JSON dump above
exists as a separate tool for that population. Guide 06 owns object-monitor internals (biased
locking's removal, lock inflation, the `mark word`); this paragraph is the operational half —
what the dump looks like and what it is for.

**Pitfall:** assuming a virtual thread pinned inside a `synchronized` block will show up in
`Thread.print`'s output the way a platform thread would — it will not, by design; that pin is
visible in the JFR `jdk.VirtualThreadPinned` event, not in a classic thread dump.

> **`jcmd <pid> Thread.print` dumps platform threads only, with held/waiting monitor relations the
> JVM's own detector turns into a deadlock report — virtual threads need the JSON dump instead.**

---

### async-profiler and the frame names you actually see `[X-REF 06]`

**Mechanism.** async-profiler samples using a signal-based mechanism (`perf_events` on Linux, or
`AsyncGetCallTrace`-style walking elsewhere) that can capture both Java and native frames in one
stack, at negligible overhead compared to safepoint-biased profilers — the property that makes it
usable in production, not just in a lab. The frame *names* it reports for the constructs this
subject covers are worth memorising because they are the actual interview-recognisable evidence of
what's running: a lambda body appears as
`StakeReservationPipeline$$Lambda.0x00007f2b3c0a1230/0x...::test` (the hidden class's synthetic
name plus the abstract method it implements), a stream stage appears as frames named for the
pipeline's internal classes — `java.util.stream.ReferencePipeline$2$1::accept` or similar, naming
the anonymous `Sink` implementation, not your lambda directly, one frame per pipeline stage — and
a `ForkJoinPool` leaf task appears under `java.util.concurrent.ForkJoinTask::doExec` with the
concrete task subclass (`ForkJoinTask$AdaptedRunnableAction`, or your own `RecursiveTask`
subclass) beneath it. Guide 06 owns HotSpot's stack-walking machinery in depth; this is the
practical recognition guide for reading a flame graph over this subject's code shapes.

**Pitfall:** seeing `ReferencePipeline$2$1` or a `$$Lambda` frame in a flame graph and assuming
it's "framework overhead" separate from your code — it *is* your lambda body, just named by its
compiler-generated identity rather than the name you gave the variable it was assigned to.

> **async-profiler's frame names for this subject are the hidden lambda class
> (`Outer$$Lambda.0x.../method`), the stream's internal `Sink` implementation class per stage, and
> `ForkJoinTask::doExec` for a ForkJoin leaf — recognise these before reading a flame graph.**

---

### JMH for every stream-versus-loop or parallel-versus-sequential claim `[X-REF 16]`

**Mental model.** A microbenchmark is an adversarial exercise against the JIT compiler: HotSpot's
job is to make code fast by deleting work that doesn't affect an observable result, and a naive
`System.nanoTime()`-around-a-loop "benchmark" gives the JIT every incentive to delete exactly the
work you meant to measure. JMH (Java Microbenchmark Harness) exists because "just time it" is not
a measurement methodology against an optimizing compiler — it is a fork-per-benchmark, warm-up-
then-measure harness co-developed by the HotSpot team specifically to close the loopholes a
hand-rolled timer leaves open.

**Why it exists.** Before JMH, published "stream is 3x slower than a for-loop" numbers were
routinely dead-code-eliminated to zero real work, or measured entirely inside JIT warm-up (running
in the interpreter or C1-compiled tier, never reaching C2's steady state), or contaminated by GC
pauses from previous iterations sharing one JVM process. JMH's defaults directly target each of
these: separate JVM **forks** per benchmark (no shared-process contamination), explicit
**warm-up** iterations discarded before measurement (so C2 has compiled the hot path before
numbers count), and a **`Blackhole`** sink that consumes a computed result through a code path the
JIT cannot prove is unused, defeating dead-code elimination without you writing to a volatile
field yourself.

**When to reach for it, and when not.** Reach for it before publishing *any* number claiming one
approach is faster than another at the microsecond/nanosecond scale — stream vs. loop, parallel
vs. sequential, `String.format` vs. concatenation. Do not reach for it to validate a *macro*
performance claim about a whole request path under real load (PSP capture latency, ledger write
throughput) — that is an application-level load test or a production JFR recording's job, not a
JMH harness measuring one hot method in isolation with none of the surrounding system's contention.

**How it works.** A `@Benchmark` method runs inside a generated harness class, not called
directly by your test code; JMH's annotation processor generates that wrapper at build time. The
mechanics that matter: `@Fork(value = N)` spawns `N` fresh JVM processes so no benchmark's JIT
state or GC history leaks into another's; `@Warmup(iterations = W)` runs `W` iterations whose
timings are discarded, specifically to let C2 finish compiling before the measured iterations run;
and any benchmark method returning a value that the harness doesn't consume gets that value routed
through a `Blackhole.consume(...)` call the harness inserts, which contains a JIT-visible
side-effecting write that prevents the whole computation above it from being proven dead.

No dedicated diagram here either: the JMH lifecycle (fork, warm-up, measurement, teardown) is a
sequence, not a structure, and D-168's row for JMH already states what it verifies and what its
output looks like.

**Code.** Comparing `Stream.filter().count()` against a hand-rolled loop over stake reservations,
correctly forked, warmed up, and blackholed:

```java
@State(Scope.Benchmark)
public class StakeCountBenchmark {

    List<StakeReservation> reservations;

    @Setup
    public void setUp() {
        reservations = new ArrayList<>(2_800_000 / 28); // one leaf-task-sized slice
        for (int i = 0; i < 100_000; i++) {
            var amount = new BigDecimal(i % 2 == 0 ? "5.10" : "3.20");
            reservations.add(new StakeReservation("res-" + i, amount, "AA-801"));
        }
    }

    @Benchmark
    public long streamCount(Blackhole blackhole) {
        long count = reservations.stream()
                .filter(r -> r.amount().compareTo(BigDecimal.valueOf(4)) > 0)
                .count();
        blackhole.consume(count);
        return count;
    }

    @Benchmark
    public long loopCount(Blackhole blackhole) {
        long count = 0;
        for (StakeReservation r : reservations) {
            if (r.amount().compareTo(BigDecimal.valueOf(4)) > 0) {
                count++;
            }
        }
        blackhole.consume(count);
        return count;
    }
}
```

Run with `@Fork(2) @Warmup(iterations = 5) @Measurement(iterations = 5)` on the benchmark class,
which is exactly the minimum discipline this beat is arguing for — omit any one of fork count,
warm-up, or `Blackhole`, and the resulting number is not evidence of anything.

**Gotcha.** `**Pitfall:**` writing `@Benchmark public long streamCount() { return reservations.stream()...count(); }`
with no `Blackhole` parameter at all and trusting the method-return-value convention to save you —
JMH *does* auto-consume a returned primitive/object in modern versions, so this particular shape is
actually safe, but the pitfall is broader: any intermediate value computed and *not* returned or
explicitly blackholed (a local variable used only for a `System.out.println` inside a conditionally-
skipped debug branch, for instance) is exactly what C2 will prove dead and delete, silently
skewing the "faster" benchmark to look faster than it is.

> **JMH is a warm-up-then-measure harness, forked per benchmark, with `Blackhole` defeating
> dead-code elimination — a stream-vs-loop timing claim without all three is not a benchmark, it
> is a guess with a stopwatch.**

---

### IDE support worth using

**Mechanism.** IntelliJ IDEA's stream debugger ("Trace Current Stream Chain", available from a
breakpoint set anywhere inside a stream pipeline) works by re-executing the pipeline under
instrumentation and rendering, stage by stage, exactly which elements entered and left each
intermediate operation — turning "streams are lazy and I can't see what's happening" into a
side-by-side element list per stage, which is the single fastest way to debug a `filter`/`map`
chain that silently produces zero results (usually: the filter predicate references the wrong
field, or an upstream `map` already changed the type being compared). The `var` inlay hint (shown
inline, greyed, next to the variable name) is IntelliJ inferring and displaying the type the LVTI
style guide's G3/G6 (below) assume the reader can *always* recover from the IDE — but per that
guide's own P3 ("code readability shouldn't depend on IDEs"), the hint is a convenience for
*writing* code, not a substitute for choosing a `var` site where a human reader without the IDE
open can still recover the type from the initializer alone.

**Gotcha.** Relying on the stream debugger or the inlay hint as your only understanding of a
pipeline's type or laziness is exactly the trap P3 warns against — in a code review, a terminal,
or an interview whiteboard, none of that tooling is available, and the mechanism (§ `javap`
discipline, above; the `AbstractPipeline`/`Sink` model referenced throughout this subject) has to
carry the explanation instead.

> **IntelliJ's stream debugger shows element-by-element state per pipeline stage at a breakpoint;
> the `var` inlay hint shows inferred types — both are write-time aids, never a substitute for the
> underlying model when the IDE isn't there.**

---

### Static analysis for `Optional`/`Stream` misuse `[RESEARCH]`

**Mental model.** Every rule in this beat targets the same family of bug: a value or a resource
whose contract is violated silently at compile time and loudly (or not at all) at runtime — an
`Optional` used where a `null` check would have been caught by the type system, a `Stream` whose
terminal operation was never called, a return value whose whole purpose was to be checked and
wasn't. Static analysis catches these *before* the JVM ever runs the code, which is strictly
earlier than JFR or a thread dump can help.

**Why it exists.** The compiler's type system accepts `Optional<T> field;` on a class and
`stream.filter(...);` with no terminal call, because both are syntactically and semantically valid
Java — the type checker has no opinion on *intent*. Static analysis tools encode the intent rules
the language doesn't: "an `Optional` field or parameter is almost always a design smell because it
adds an allocation and a null-check-shaped API for something a plain nullable reference already
expressed", "a `Stream` pipeline built and discarded without a terminal operation is dead code
that looks alive", "ignoring a method's return value when that value is the entire point of
calling it (`Stream.filter` returns a new stream; discarding it silently no-ops the filter) is
almost always a bug."

**When to reach for it, and when not.** Reach for these checks in CI, on every pull request,
because they are cheap (single-digit-second build-time cost) and their false-positive rate on this
specific rule family is low. Do not reach for static analysis as a substitute for the mechanism
understanding this subject teaches — a tool that flags `OptionalUsedAsFieldOrParameterType` tells
you *that* it's wrong, not *why* boxing a nullable reference in an extra allocation for a field is
worse than the reference itself, which is a mechanism question these notes answer and the linter
does not.

**How it works, tool by tool.** Four named tools, each catching a different slice:

| Tool | Rule(s) named in the syllabus | What it flags |
|---|---|---|
| ErrorProne | `OptionalUsedAsFieldOrParameterType` | An `Optional<T>` used as a field type or a method parameter type, rather than only as a return type |
| ErrorProne | `StreamResourceLeak` | A `Stream` obtained from an I/O source (`Files.lines`, `Files.list`) never closed via try-with-resources |
| ErrorProne | `ReturnValueIgnored` | A call to a method whose return value is its entire effect (e.g. a filtered/mapped stream) with the result discarded |
| ErrorProne | `OptionalNotPresent` | An `Optional.get()`/similar call the tool can statically prove will run on an empty `Optional` on some path |
| SpotBugs | its `Optional`/nullness rule family | Bytecode-level nullness and `Optional` misuse patterns, post-compilation |
| SonarQube | its stream/`Optional` rule set | Editor- and CI-integrated versions of similar rules, surfaced with a severity and a remediation estimate |
| NullAway | its core nullability check | Whole-project null-flow analysis assuming `@Nullable`/non-null annotations, catching a `NullPointerException` at the annotation boundary rather than at runtime |

**`[RESEARCH]`:** exact rule names and behaviour are tool-version-dependent; the four ErrorProne
rule names above are named as given in the syllabus and are consistent with ErrorProne's published
bug-pattern catalogue, but re-verify against the specific ErrorProne/SpotBugs/SonarQube/NullAway
versions pinned in a given build before quoting a rule's exact trigger condition in an interview
answer, since bug-pattern sets have grown release to release.

**Pitfall.** Treating a clean static-analysis run as proof the code is correct — `ReturnValueIgnored`
catches a discarded `Stream.filter(...)` result but has no opinion on whether the *predicate*
inside that `filter` is the right one; static analysis narrows the search for bugs, it does not
replace testing the ledger invariant it's near.

> **Static analysis encodes intent rules the type system can't express — an `Optional` field, a
> leaked I/O stream, a discarded filter result — catching them at build time, before JFR or a
> thread dump would ever be needed.**

---

### Confirm before you quote `[X-REF 06]`

**Mechanism.** Three tools close the loop between "this subject states a number" and "this
number is true on the machine in front of you", and each answers a different kind of number.
`-XX:+PrintFlagsFinal` (a diagnostic VM flag) dumps every VM flag's *actual, final* value after
ergonomic defaults have been applied — the flag you want when a claim is about a JVM tuning
default, because ergonomics (heap-size-dependent GC choice, `-XX:+UseCompressedOops`'s heap-size
threshold) can silently override the "documented default" for a given machine's RAM and core
count. `System.getProperties()` (a `java.lang.System` static method returning a live `Properties`
map) is the runtime-inspectable form of every `-D`-settable property this subject has named —
`jdk.virtualThreadScheduler.parallelism`, `jdk.virtualThreadScheduler.maxPoolSize`,
`jdk.virtualThreadScheduler.minRunnable` — and printing it is how you confirm which of those
three were actually set for a given process, rather than trusting a deploy script's intent.
`ForkJoinPool.getCommonPoolParallelism()` returns the live `int` a running JVM is actually using
for its common pool, which per the corrected figures for this subject (below) is not simply
"core count" — it is `availableProcessors() - 1`, and only *effectively* equal to core count
because the submitting thread also participates.

**Worked confirmation, using this subject's own 8-core baseline** (every other file in this set
uses the same machine so numbers never contradict across files): `Runtime.getRuntime().availableProcessors()`
returns **8**; `ForkJoinPool.getCommonPoolParallelism()` returns **7** (`8 - 1`); the *effective*
concurrency of a `parallelStream()` submitted from a non-pool thread is **8**, because that
submitting thread runs one of the leaf tasks itself while the 7 pool workers run the rest — stating
only "parallelism is 7" without the participating-submitter half is the incomplete version of this
claim guide 06 flags at length.

**Gotcha.** Assuming a number quoted from a blog post, a prior year's JDK, or even this very
document's own earlier drafts still holds without confirming it against
`-XX:+PrintFlagsFinal`/`System.getProperties()`/`getCommonPoolParallelism()` on the box a claim is
actually being made about — every corrected figure in the "Verified figures" material this subject
draws on exists precisely because an unconfirmed number was quoted as fact once.

> **`-XX:+PrintFlagsFinal`, `System.getProperties()`, and `ForkJoinPool.getCommonPoolParallelism()`
> are how a tuning-default or scheduler-width claim gets confirmed on the actual machine, rather
> than trusted from documentation that ergonomics may have overridden.**

---

## Pitfalls

### Assuming `javap -c` alone is enough evidence for a desugaring claim

**Wrong**

```
javap -c StakeReservationPipeline.class
```

produces the bytecode with the `invokedynamic` instructions visible, but the `BootstrapMethods:`
table — the part that actually names `LambdaMetafactory.metafactory` and the synthetic lambda
method — is omitted, and the synthetic `lambda$countHighValue$0` method itself doesn't even appear
in the member listing without `-p`.

**Right**

```
javap -c -p -v StakeReservationPipeline.class
```

`-p` surfaces the private synthetic lambda-body methods; `-v` surfaces the constant pool and the
`BootstrapMethods:` table that ties the `invokedynamic` call site to the bootstrap method and its
static arguments.

**Why people believe it:** `-c` is the flag everyone learns first because it's the one that shows
"the bytecode," and for ordinary method calls that's sufficient — it only falls short for
`invokedynamic`-based constructs, which didn't exist in the pre-lambda Java most tutorials were
written against.

### Trusting a hand-timed loop as a performance benchmark

**Wrong**

```java
long start = System.nanoTime();
long count = reservations.stream().filter(r -> r.amount().compareTo(threshold) > 0).count();
System.out.println((System.nanoTime() - start) / 1_000_000 + " ms");
```

This runs once, in whatever JIT tier happened to be active, in a JVM whose class metadata and GC
state are still warming up, and the JIT can prove `count` is unused past the `println` and delete
work upstream of it.

**Right**

Wrap it as a `@Benchmark` under JMH with `@Fork`, `@Warmup`, and a `Blackhole` parameter (see the
JMH discipline section above) and read the `Score`/`Error` columns, not a single wall-clock
sample.

**Why people believe it:** `System.nanoTime()` really does measure elapsed time correctly — the
flaw isn't the clock, it's that a single untuned sample inside a live-optimizing runtime measures
the JIT's current warm-up state and the compiler's dead-code analysis, not the algorithm.

---

## Cheat sheet

| Question | Tool | One-line answer discipline |
|---|---|---|
| What did this lambda/record/switch desugar to? | `javap -c -p -v` | `-c` bytecode, `-p` synthetic bodies, `-v` `BootstrapMethods:` — need all three |
| Is this specific runtime claim true? | `jshell` | One falsifying snippet, no build needed |
| Does a lambda really spin a hidden class? | `-Djdk.internal.lambda.dumpProxyClasses=<dir>` | Writes it to disk; since Java 9 it's a genuine hidden class |
| When does that hidden class get created? | `-Xlog:class+load=info` | Lazily, on first invocation of that call site, once |
| Is a virtual thread pinned, and why? | JFR `jdk.VirtualThreadPinned` | `synchronized` pins on 21; native/foreign frames pin at every version; JEP 491 fixes `synchronized` in 24 |
| Where is allocation pressure coming from? | JFR `jdk.ObjectAllocationSample` | Sampled, not exhaustive — default ~512 KB/thread interval |
| How many virtual threads, in what scope tree? | `jcmd <pid> Thread.dump_to_file -format=json` | Grouped by `threadContainers`; virtual threads excluded from `Thread.print` |
| Is there a platform-thread deadlock? | `jcmd <pid> Thread.print` | JVM's own cycle detector on held/waiting monitor edges |
| Where does CPU/allocation time actually go? | async-profiler | Frame names: `Outer$$Lambda.0x.../method`, per-stage `Sink` classes, `ForkJoinTask::doExec` |
| Is stream faster/slower than a loop, here? | JMH | Needs `@Fork`, `@Warmup`, `Blackhole` — all three or the number is noise |
| What flows through this pipeline stage? | IntelliJ stream debugger | Element-by-element per stage, write-time aid only |
| Is this `Optional`/`Stream` usage a smell? | ErrorProne/SpotBugs/Sonar/NullAway | Catches intent violations the type system can't express |
| Is the documented default actually in effect here? | `-XX:+PrintFlagsFinal`, `System.getProperties()`, `getCommonPoolParallelism()` | Ergonomics can override documented defaults per machine |

---

## Self-test

**Q1.** Why does `javap -c` alone understate a lambda desugaring claim, and which two flags fix
that?

<details><summary>Answer</summary>

`-c` disassembles bytecode and shows the `invokedynamic` instruction at the call site, but it
omits two things needed to complete the claim: the private synthetic lambda-body method itself
(hidden without `-p`, since it is `ACC_PRIVATE ACC_SYNTHETIC`) and the `BootstrapMethods:` table
(shown only with `-v`) that names `LambdaMetafactory.metafactory` and lists the static arguments —
including a direct method handle to the synthetic lambda body. Without `-p -v` you can see *that*
an `invokedynamic` exists but not *what it resolves to*.

</details>

**Q2.** A teammate claims "the virtual-thread scheduler's max pool size is always 256." Using
`VirtualThread.createDefaultScheduler()`'s actual source, what's wrong with that claim, and on
what kind of machine does it become false?

<details><summary>Answer</summary>

`maxPoolSize` defaults to `Integer.max(parallelism, 256)`, where `parallelism` defaults to
`Runtime.getRuntime().availableProcessors()`. 256 is a floor, not a fixed value: it only equals
256 when `availableProcessors()` is 256 or fewer. On a machine with more than 256 available
processors, `maxPoolSize` equals `availableProcessors()` instead, exceeding 256. The claim is
right for essentially every machine in practice today but wrong as stated as a hard constant.

</details>

**Q3.** Why does `jcmd <pid> Thread.print` exclude virtual threads by default, and what tool
should you reach for instead if you need to see them?

<details><summary>Answer</summary>

`Thread.print` walks the platform-thread table and is designed around the assumption of at most a
few thousand OS-backed threads; a production JVM can host hundreds of thousands of virtual
threads, and dumping all of them in the same flat text format would be both enormous and mostly
transient (many virtual threads complete before a human could read the dump). `jcmd <pid> Thread.dump_to_file -format=json <file>`
is built for the virtual-thread population instead: it groups threads by `threadContainers`,
which is the structure a `StructuredTaskScope` tree needs and a flat dump can't represent.

</details>

**Q4.** What specifically does a JMH `Blackhole` prevent, and what happens to a benchmark's
result if you omit it and also don't return the computed value?

<details><summary>Answer</summary>

`Blackhole` provides a JIT-visible consuming side effect for a value the benchmark method computes
but doesn't otherwise use, preventing the compiler from proving that computation is dead and
eliminating it. If a benchmark computes a value, never returns it, and never passes it to
`Blackhole.consume(...)`, C2 is free to determine the whole computation has no observable effect
and delete it — the benchmark then measures approximately nothing, and reports an unrealistically
fast (and meaningless) score.

</details>

**Q5.** What is the actual accumulator type behind `Collectors.summingInt`, and why does that
matter for a stream summing stake amounts represented as integer minor units?

<details><summary>Answer</summary>

`summingInt` accumulates into a `new int[1]` — a single `int` slot — not a `long[]`, unlike
`summingLong`/`averagingInt`/`averagingLong`, which all use `long[]` accumulators. This gives
`summingInt` the exact same silent-overflow behaviour as `IntStream.sum()`: summing enough large
`int` values (verified on this machine: three additions of 1,000,000,000 each) wraps around to a
negative number instead of throwing, because `int` addition in Java silently wraps. A stream
summing many stake amounts as integer minor units should use `summingLong`, or `mapToLong` before
summing, not `summingInt`.

</details>

**Q6.** What's the difference between `jdk.ObjectAllocationSample` firing and "this call site
allocates" — i.e., why might a real boxing hot spot never show up in a short JFR recording?

<details><summary>Answer</summary>

`jdk.ObjectAllocationSample` is a *sampling* event, firing at roughly every ~512 KB of bytes
allocated per thread by default (the exact interval is tunable but not per-allocation) rather than
on every single allocation — sampling is what keeps JFR's overhead low enough to run continuously
in production. A boxing call site that allocates small objects infrequently, or a recording window
too short to accumulate a full sampling interval's worth of bytes on the relevant thread, can
genuinely produce zero samples even though the call site does allocate; absence of a sample is not
proof of absence of allocation, only of statistical bad luck or insufficient recording duration.

</details>

**Q7.** Why is `-Djdk.internal.lambda.dumpProxyClasses` output from Java 9+ fundamentally
different from the same flag's output on Java 8, even though the flag name never changed?

<details><summary>Answer</summary>

Through Java 8, the lambda proxy class the flag dumps was an ordinary, named class defined by a
regular anonymous class loader — visible to normal classloading machinery and to a heap dump as
any other loaded class would be. From Java 9 onward, after `Lookup.defineHiddenClass` (formalized
by JEP 371 in Java 15), the runtime-generated lambda class is a genuine hidden class: unregistered
with the system dictionary, not resolvable by name through ordinary classloading, and independently
unloadable. The flag still writes a `.class` file you can disassemble either way, but on 9+ that
file is a snapshot of something that, at runtime, was never a loadable-by-name class to begin
with — a materially different runtime object than the pre-9 dump represents.

</details>

**Q8.** Name one static-analysis rule from this section and explain, mechanistically, what makes
its target pattern a real (not stylistic) bug risk.

<details><summary>Answer</summary>

`ReturnValueIgnored` (ErrorProne) flags a call whose return value is discarded when that return
value is the method's entire effect — for example `stakeReservations.stream().filter(isHighValue);`
with the resulting filtered stream never assigned or chained further. Mechanistically this is a
real bug, not a style nit: `Stream` operations are immutable and non-mutating — `filter` returns a
*new* stream and leaves the original unchanged — so a discarded result means the filtering never
happened anywhere the program can observe, silently turning an intended filter into a no-op rather
than throwing or logging anything.

</details>

---

## Deferred

None.

---

## Open questions

- **Unverified:** the exact JSON schema field names for `jcmd Thread.dump_to_file -format=json`
  (`threadDump.threadContainers` and its child fields) were described from JDK 21 diagnostic-command
  documentation rather than captured by actually running the command against a live process with a
  `StructuredTaskScope` tree on this machine; confirm the precise field names against a live dump
  on the JDK 21 build actually in use before quoting the schema verbatim in a build tool or parser.
- **Unverified:** `-XX:+PrintFlagsFinal`'s exact output line format shown implicitly in the cheat
  sheet (`bool UseCompressedOops = true {product}`) reflects the general documented shape of that
  diagnostic command's output rather than a capture taken on this machine's JDK 25 (run under
  `--release 21` for class-file compatibility, which does not change diagnostic-command text
  output); confirm against a JDK 21 build's actual `-XX:+PrintFlagsFinal` output if the exact
  column spacing or flag-origin tag matters for a specific use.

---

**Leaves covered:** 3.17.1–3.17.12 (12 leaves)
**Leaves deferred:** None
**Diagrams included:** D-168
**Target version:** Java 21 LTS
**Lines:** 865
