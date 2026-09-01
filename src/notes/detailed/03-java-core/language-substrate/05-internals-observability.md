# 03 Java Core — Observability toolkit — INTERNALS (§3.18)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Version history, Java 18 onward](04a-internals-version-history-18-onward.md) · Next: [Primitives](../primitives-and-conversions/01-basics.md)

Every claim in the internals part of this guide is falsifiable with a command, and a reader who knows the commands never has to trust folklore again. The follow-up a strong interviewer asks after any confident statement about the JVM is exactly *"how would you check?"* — this file is that answer, ten times over.

## The claim-to-command map

| Claim category | Instrument that falsifies it | What you read |
|---|---|---|
| "`javac` desugared X into Y" | `javap -c -p -v X.class` | the instruction sequence and the constant pool |
| "this object is N bytes" | JOL `internals` + `-XX:+PrintFlagsFinal` | printed `Instance size`, and the oop/alignment flags it depends on |
| "this class was initialised when Y happened" | `java -Xlog:class+init=info` | `Initializing '<Class>' by thread` lines, in causal order |
| "this loop boxes" | async-profiler `asprof -e alloc` | `java.lang.Integer` frames under the call site |
| "this exception is cheap / expensive" | JFR `jdk.ExceptionStatistics`, `jdk.JavaExceptionThrow` | throw rate, then the stack trace per throw |
| "this inner class retains its enclosing instance" | heap dump + Eclipse MAT | `this$0` on the path from the object to a GC root |
| "these two strings/boxes are the same object" | `jshell` one-liner | `true` / `false` |
| "this flag defaults to N" | `java -XX:+PrintFlagsFinal -version \| grep <Flag>` | the value plus its `{default}` / `{ergonomic}` origin |
| "these are the live objects on the hot path" | `jcmd <pid> GC.class_histogram` | `#instances` / `#bytes` per class |

**Provenance.** Every listing below was produced by running the command while writing this file, on Oracle GraalVM JDK 25.0.1+8.1 (HotSpot, macOS aarch64), with `javac --release 21` for class files so the class-file output is what a JDK 21 compiler emits. The flag *defaults* in §3 come from a `java -XX:+PrintFlagsFinal -version` run on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245, macOS aarch64). Version-sensitive differences are flagged inline; `## Open questions` names the two listings that were not run here.

## 1. `javap -c -p -v`: the primary instrument `[BYTECODE]`

**The picture.** `javap` reads a `.class` file off disk. It never runs anything, never loads a class, never sees the JIT. It is a pretty-printer for the class file format — the exact bytes the JVM will be handed, a format specified in JVMS §4 in which a method body is a byte array and every name is an index into a constant pool. That position in the lifecycle is what makes it authoritative: everything `javac` decided is already frozen in those bytes, and everything the JIT will later decide has not happened yet. If you want to know what the *language* compiled to, this is the only tool that cannot be wrong.

**How it works.** `javap` parses the class file's sections and prints the ones you ask for. Nothing is inferred; the trailing comments (`// Method java/math/BigDecimal.add`) are `javap` resolving pool indices for you.

| Flag | Prints | Use it when |
|---|---|---|
| (none) | public API signatures only | checking an erased signature quickly |
| `-p` | private and package-private members, including synthetics | hunting `this$0`, `access$000`, bridge methods |
| `-c` | disassembled bytecode per method | any desugaring claim |
| `-v` | `-c` plus constant pool, `BootstrapMethods`, `InnerClasses`, `StackMapTable`, `major version` | `invokedynamic`, records, sealed classes, nest members |

**Command.** Against the `FundsLedger` ledger-total loop:

```java
public final class FundsLedger {
    private final List<Movement> movements;
    public FundsLedger(List<Movement> movements) { this.movements = movements; }
    public BigDecimal total() {
        BigDecimal sum = BigDecimal.ZERO;
        for (Movement m : movements) {
            sum = sum.add(m.amount());
        }
        return sum;
    }
    public String auditLine(String runId, int lines) {
        return "PaymentRun " + runId + " lines=" + lines;
    }
    public record Movement(String position, BigDecimal amount) {}
}
```

```
$ javac --release 21 -d out FundsLedger.java && javap -c -p out/FundsLedger.class
  public java.math.BigDecimal total();
    Code:
         0: getstatic     #13    // Field java/math/BigDecimal.ZERO:Ljava/math/BigDecimal;
         3: astore_1
         4: aload_0
         5: getfield      #7     // Field movements:Ljava/util/List;
         8: invokeinterface #19,  1  // InterfaceMethod java/util/List.iterator:()Ljava/util/Iterator;
        13: astore_2
        14: aload_2
        15: invokeinterface #25,  1  // InterfaceMethod java/util/Iterator.hasNext:()Z
        20: ifeq          45
        23: aload_2
        24: invokeinterface #31,  1  // InterfaceMethod java/util/Iterator.next:()Ljava/lang/Object;
        29: checkcast     #35    // class FundsLedger$Movement
        32: astore_3
        33: aload_1
        34: aload_3
        35: invokevirtual #37    // Method FundsLedger$Movement.amount:()Ljava/math/BigDecimal;
        38: invokevirtual #41    // Method java/math/BigDecimal.add:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
        41: astore_1
        42: goto          14
        45: aload_1
        46: areturn
```

Read it instruction by instruction. `0–3`: `BigDecimal.ZERO` is a static field read, stored into local slot 1 (`sum`). `4–13`: the enhanced-for is gone — `javac` emitted a real `List.iterator()` call and parked the `Iterator` in slot 2, a local variable that does not exist in the source. `14–20`: `hasNext()`, and `ifeq 45` jumps past the body when it returns `0` (false); the test is at the *top*, so the backward branch at `42: goto 14` is unconditional. `24–29`: `next()` is erased to `()Ljava/lang/Object;`, so `javac` inserted a `checkcast` to `FundsLedger$Movement` — that cast is the runtime price of erased generics and it runs on every one of the ~19.8M ledger rows a day. `33–41`: accumulate, store back. `46: areturn`.

The concat method is one instruction, and `-v` names who implements it:

```
  public java.lang.String auditLine(java.lang.String, int);
    Code:
         0: aload_1
         1: iload_2
         2: invokedynamic #45,  0  // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/String;I)Ljava/lang/String;
         7: areturn

BootstrapMethods:
  0: #64 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #62 PaymentRun \u0001 lines=\u0001
```

No `StringBuilder` anywhere. The recipe is a constant-pool string in which `\u0001` (a literal 0x01 byte, which `javap` prints escaped) marks each argument slot and the literal text is baked in; the `int` travels as a primitive `I` in the call-site descriptor, so there is no `Integer.valueOf`. `-v` also confirms the target: `major version: 65` is Java 21 (`major = release + 44`; the same source compiled without `--release` on JDK 25 prints `69`). **Version note:** `invokedynamic` concat arrived in Java 9 (JEP 280) — on Java 8 this method compiles to `new StringBuilder` / `append` / `toString`.

### The foil: a decompiler `[TRAP]`

A decompiler reads the same bytes and reconstructs *source*: a harder, lossy job that pattern-matches instruction shapes back onto language constructs and prints the prettiest source which would compile to something equivalent.

| Decompiler | Typical use | Re-sugars back into source | Where it misleads |
|---|---|---|---|
| CFR | CLI, single jar, best control-flow recovery | enhanced-for, try-with-resources, `switch` on `String`/enum, lambdas, records | hides the `Iterator` and the `checkcast`; can print `var` where the source named the type |
| Fernflower | bundled in IntelliJ IDEA — this is what "go to declaration" on a library shows you | the same set, plus `invokedynamic` concat back to `+` | silently drops synthetic bridges and `access$` accessors unless configured otherwise |
| Procyon | closest to `javac`'s own shapes, strongest on generics | enhanced-for, lambdas, generic signatures | rebuilds generics from the `Signature` attribute, which is metadata rather than code — it can print a cast that is not there and omit one that is |

**Pitfall:** decompile `total()` and all three print back `for (Movement m : this.movements) { sum = sum.add(m.amount()); }` — the exact source. The wrong belief that follows is "so there is no `Iterator`, and erasure costs nothing at runtime". The symptom is an engineer who cannot explain a `ClassCastException` thrown from a line containing no cast, or who claims a hot loop over a `List` allocates nothing. The fix: decompile to *navigate*, `javap -c -p` to *conclude*. Any sentence you say about what the compiler emitted should be backed by a listing you have actually seen.

**Interview:** *"How do you know the enhanced-for allocates?"* — "`javap -c` shows `invokeinterface List.iterator`, so one `Iterator` per call in the bytecode; whether it survives to the heap is escape analysis, which I check with async-profiler `-e alloc`, not with a static tool."

> **Definition — `javap`:** the JDK's class-file disassembler, which prints the exact contents of a compiled class without loading or executing it, making it the authoritative evidence for any claim about what `javac` produced.

> **Definition — decompiler:** a tool that reconstructs plausible Java source by re-sugaring recognised bytecode patterns, and therefore deliberately hides the desugaring you are trying to observe. The full desugaring catalogue these listings come from is [03-internals-javac-and-class-file.md](03-internals-javac-and-class-file.md).

## 2. The class-loading and initialization logs `[RESEARCH]`

**The picture.** A class goes through *loading* (bytes found and defined), *linking* (verify, prepare, resolve) and *initialization* (`<clinit>` runs) — three separate events at three different times, all of which the JVM will narrate on request. `-Xlog:class+load` witnesses the first. `-Xlog:class+init` witnesses the third, and it is the one that answers "who triggered this?", because it prints the triggering thread and prints in causal order. JVMS §5.5 makes initialization lazy with exactly five triggers, so static initialisers run at times that are correct by spec and surprising in practice; guessing is hopeless and the log is definitive.

| Form | Introduced | Status on 21 | Notes |
|---|---|---|---|
| `-verbose:class` | all versions | supported, and is an alias | emits unified-logging output for `class+load` **and** `class+unload` at `info` |
| `-Xlog:class+load=info` | 9 (JEP 158/271) | canonical | one line per class defined, with its source |
| `-Xlog:class+init=info` | 9 | canonical | verification lines plus `Initializing '<C>' by thread` |
| `-XX:+TraceClassLoading` | 8 | **removed** | aliased in 9, then obsoleted; never put it in a runbook |
| `-Xlog:class+init=info:file=/var/log/init.log:uptime,tid:filecount=5,filesize=20M` | 9 | canonical | the only form fit for a long-lived node — sink, decorate, rotate |

**Command and output.** The question: who triggers `BonusService`'s `<clinit>`?

```java
class BonusService {
    static final int GRANT_CAP_MINOR = 10000;
    static final java.math.BigDecimal GRANT_RATE = new java.math.BigDecimal("0.10");
    static { System.out.println("BonusService <clinit>"); }
}
public class BalanceView {
    public static void main(String[] args) {
        System.out.println("cap=" + BonusService.GRANT_CAP_MINOR);
        System.out.println("rate=" + BonusService.GRANT_RATE);
    }
}
```

```
$ java -Xlog:class+init=info BalanceView
[0.029s][info][class,init] 559 Initializing 'BalanceView'(no method) (0x00000ffe01040800) by thread "main"
cap=10000
[0.029s][info][class,init] 564 Initializing 'BonusService' (0x00000ffe01040a10) by thread "main"
BonusService <clinit>
rate=0.10
```

Line by line. `BalanceView` initialises first; `(no method)` means it has no `<clinit>` of its own, and the JVM still records the state transition. Then `cap=10000` prints **before** `BonusService` initialises — reading `GRANT_CAP_MINOR` did not trigger initialization at all. The `GRANT_RATE` read does trigger it, `<clinit>` runs, and `rate=0.10` follows. `559` / `564` are class-loading sequence numbers, so the log stays orderable under concurrency, and `by thread "main"` is the attribution you came for.

**Insight:** the asymmetry is `javac`'s, not the JVM's. `static final int GRANT_CAP_MINOR = 10000` is a *constant variable* (JLS §4.12.4): `final`, primitive-or-`String`, constant-expression initialiser. `javac` folds its value into each reader's own constant pool, so no field access survives to trigger anything.

```
$ javap -c BalanceView.class
         3: ldc           #15   // String cap=10000
        11: getstatic     #23   // Field BonusService.GRANT_RATE:Ljava/math/BigDecimal;
```

Offset `3` is a fully folded string literal — `BonusService` is not even mentioned. Offset `11` is a real `getstatic`, and `getstatic` on a non-constant field is one of the five specified triggers. This is also why bumping `GRANT_CAP_MINOR` and redeploying only `BonusService` leaves the old `10000` baked into every caller. The weaker question — *was it loaded, and from where* — is `class+load`'s: `[0.030s][info][class,load] BonusService source: file:/private/tmp/qs/`, where `source:` is the diagnostic value (`shared objects file` means CDS, a `jar:file:` URL names the exact jar, and a class duplicated across two jars shows up here and nowhere else).

**Gotcha / trade-off.** Both tags are cheap per event and ruinous in aggregate. A `PaymentService` node serving 2.4M registered clients loads on the order of 10⁴ classes at startup and `class+init=info` adds three lines each; left on `stdout` it interleaves with application logging and can make startup I/O-bound. Always sink it to a rotated file, as in the last table row. Turn it on for a canary, read it, turn it off.

**Interview:** *"A static initialiser in `BonusService` runs during a health check and you do not know why."* — "Run the node with `-Xlog:class+init=info` to a file and read the position and thread of the `Initializing 'BonusService'` line; whatever initialised immediately before it is the trigger, and I confirm with `javap -c` that the caller really emits a `getstatic` rather than a folded constant."

> **Definition — unified logging:** the JDK 9+ `-Xlog:<tag-set>=<level>:<output>:<decorators>:<options>` framework that replaced the ad-hoc `-verbose:` and `-XX:+Trace*` flags with one selectable, sinkable, decorated log; `-verbose:class` survives as an alias for `class+load` and `class+unload` at `info`. Loading, linking and the five triggers belong to [../classes-and-initialization/03-internals-class-loading-and-init.md](../classes-and-initialization/03-internals-class-loading-and-init.md).

## 3. Confirm the flag before you do byte arithmetic `[X-REF 06]`

**The picture.** Every memory number in this guide — "a `Movement` is 24 bytes", "a restriction code above 127 allocates" — is arithmetic over VM *parameters*, not constants. HotSpot has thousands of flags with three competing sources of truth: the compiled-in default, the ergonomic decision made at startup from heap size and platform, and your command line. `-XX:+PrintFlagsFinal` collapses all three into one table and labels which won, which is the only version of those values worth quoting.

```
$ java -XX:+PrintFlagsFinal -version | grep -E 'UseCompressedOops|AutoBoxCacheMax|StringTableSize|UseCompactObjectHeaders'
     intx AutoBoxCacheMax                 = 128     {C2 product} {default}
    uintx StringTableSize                 = 65536   {product} {default}
     bool UseCompressedOops               = true    {product lp64_product} {ergonomic}
```

Three of the four are there. Read the columns: type, name, value, then **two** brace groups — the flag's kind and its origin.

| Marker | Means | Consequence for you |
|---|---|---|
| `{default}` | compiled-in default, nothing changed it | safe to quote as "the default on this version" |
| `{ergonomic}` | the VM chose it at startup from heap size, CPU count, platform | **not** portable — recheck on the target node |
| `{command line}` / `{management}` | you or a launcher passed it / it was set on a live VM via JMX or `jcmd VM.set_flag` | read the launch script, not the docs; someone may have changed it in production |
| Kind `{product}` / `{C2 product}` | supported everywhere / owned by the C2 compiler subsystem | both are product flags; `AutoBoxCacheMax` is the second kind |
| Kind `{diagnostic}` / `{experimental}` | needs `-XX:+UnlockDiagnosticVMOptions` / `-XX:+UnlockExperimentalVMOptions` | do not ship without a reason |

The four flags this leaf names, values confirmed on Oracle JDK 21.0.7:

- `UseCompressedOops = true {ergonomic}` — reference fields are 4 bytes, not 8. **Ergonomic, not default:** the VM turns it off once the heap needs addresses beyond the ~32 GB a 3-bit-shifted 32-bit oop can reach, so a node with `-Xmx40g` silently doubles every reference field. Every byte figure in this guide assumes it is on.
- `AutoBoxCacheMax = 128 {C2 product} {default}` — the `Integer` cache covers `-128` to `127`, so a restriction code of `128` allocates on every box. See [../wrappers-and-boxing/03-internals-boxing.md](../wrappers-and-boxing/03-internals-boxing.md).
- `StringTableSize = 65536 {default}` — the intern table's bucket count. See [../strings/03-internals-string.md](../strings/03-internals-string.md).
- `UseCompactObjectHeaders` — **does not exist on JDK 21.** Greping for it returns nothing, and that is the correct result, not a mistake in your command line. It arrived later as an experimental flag (JEP 450) shrinking the header from 12 bytes to 8; on the JDK 25 used for the runs here the same grep prints `bool UseCompactObjectHeaders = false {product lp64_product} {default}`. Where it is on, every JOL figure in this guide shifts by 4 bytes.

Also confirmed on 21 and used elsewhere in this guide: `ObjectAlignmentInBytes = 8 {default}` (instance sizes round up to a multiple of 8, which is where JOL's "alignment gap" comes from), `OmitStackTraceInFastThrow = true`, `CompactStrings = true`, `MaxJavaStackTraceDepth = 1024`, `StringDeduplicationAgeThreshold = 3` — all `{default}`.

**Gotcha.** `-XX:+PrintFlagsFinal -version` describes *that* invocation. Ergonomic flags depend on the heap and CPU count of the machine, so a laptop run tells you nothing about a container with a 40 GB heap and a CPU quota. For a live node, ask the node: `jcmd <pid> VM.flags`.

**Interview:** *"Is the object header 12 bytes or 16?"* — "On JDK 21 with compressed oops it is 12: 8 mark plus 4 compressed class pointer. I check `UseCompressedOops` on the target node before saying so, because it is `{ergonomic}` and flips off above roughly a 32 GB heap."

> **Definition — `-XX:+PrintFlagsFinal`:** a HotSpot flag that dumps every VM flag's post-ergonomics value with its kind and origin, making it the precondition for any statement about object size, cache bounds or table sizing.

## 4. Attributing an allocation to a call site

**The picture.** Four tools, one investigation, each answering the question the previous one raises. Layout tells you what one object costs. A JFR event tells you the rate at which they appear. A profiler tells you which line makes them. A heap dump tells you why they are still alive. Reaching for the wrong one first is the most common wasted afternoon in JVM performance work.

| Question | Tool | Cost | Blind spot |
|---|---|---|---|
| What does one instance cost, field by field? | JOL `internals` / `externals` | none — offline, or a tiny in-process call | says nothing about rate or count |
| How many are made, by what, at what rate? | JFR `jdk.ObjectAllocationSample` | ~1–2% on `profile` settings; throttled to a fixed event rate | throttled, so a burst is under-represented |
| Which call site makes them? | async-profiler `-e alloc` | sampling, a few percent | samples per bytes allocated, so a rare-but-huge allocation can hide |
| Why are they still alive? | heap dump + Eclipse MAT | a full stop-the-world dump | a snapshot; says nothing about rate |

### 4a. JOL: what one `Movement` costs `[X-REF 06]`

Mechanism: an object's size is the header plus the fields *as the VM chose to lay them out*, rounded up to `ObjectAlignmentInBytes`. HotSpot reorders fields (longs and doubles first, then ints, then shorts and chars, then bytes and booleans, then references) to minimise padding, so declaration order is not layout order. JOL asks the VM itself through `Unsafe.objectFieldOffset` instead of computing a guess.

```
$ java -Djol.magicFieldOffset=true -jar jol-cli-0.17-full.jar internals -cp out 'FundsLedger$Movement'
FundsLedger$Movement object internals:
OFF  SZ                   TYPE DESCRIPTION               VALUE
  0   8                        (object header: mark)     0x0000000000000001 (non-biasable; age: 0)
  8   4                        (object header: class)    0x01050400
 12   4       java.lang.String Movement.position         null
 16   4   java.math.BigDecimal Movement.amount           null
 20   4                        (object alignment gap)
Instance size: 24 bytes
Space losses: 0 bytes internal + 4 bytes external = 4 bytes total
```

Offsets `0–7` are the mark word (identity hash, GC age, lock state); `8–11` the compressed class pointer — 12 bytes of header, the `UseCompressedOops = true` figure from §3. `12` and `16` are the two reference fields at 4 bytes each, again because compressed oops are on. `20` is 4 bytes of pure padding to reach the 8-byte alignment boundary: **two thirds of this record's bytes are data and one third is header plus padding.** `Instance size: 24 bytes` is the *shallow* size; the ~180 bytes/row figure for a ledger entry is dominated by the `String` and `BigDecimal` graphs hanging off it, which is what the `externals` operation (or `GraphLayout.parseInstance(m).totalSize()`) reports. `(non-biasable)` is a version artefact — biased locking was deprecated in 15 and removed in 18, so JDK 8–14 prints `biasable` in that slot for the same object.

**Gotcha, observed here:** `internals` on a record *without* `-Djol.magicFieldOffset=true` fails outright with `UnsupportedOperationException: can't get field offset on a record class`, because `Unsafe.objectFieldOffset` refuses record components on JDK 21+. JOL's own error message names the flag; most blog posts predate the problem. In-process equivalent (`org.openjdk.jol:jol-core:0.17`): `System.out.println(ClassLayout.parseClass(Movement.class).toPrintable());`. Header arithmetic in full: [../objects-equality-and-lifecycle/05-internals-object-layout.md](../objects-equality-and-lifecycle/05-internals-object-layout.md).

### 4b. JFR: the rate `[X-REF 20]`

Mechanism: JFR is an event recorder built into the VM, writing fixed-layout events into thread-local buffers. Events are individually enable-able and individually *throttled*, so you trade completeness for overhead per event type.

```
$ java -XX:StartFlightRecording=settings=profile,duration=120s,filename=/tmp/settle.jfr,+jdk.JavaExceptionThrow#enabled=true \
       -XX:FlightRecorderOptions=stackdepth=128 -jar payment-service.jar
$ jfr print --events jdk.ObjectAllocationSample,jdk.JavaExceptionThrow /tmp/settle.jfr
```

`jdk.ObjectAllocationSample` (JDK 16+) is enabled in both shipped settings and throttled — `150/s` under `default`, `300/s` under `profile`, read out of `$JAVA_HOME/lib/jfr/*.jfc`. On the 3,400/sec settlement burst that throttle means a proportional sample, not a census: use it for *which types*, never for *how many bytes in total*. `jdk.ObjectAllocationInNewTLAB` records every TLAB-boundary allocation with a stack trace and is `enabled=false` in both profiles for good reason. `jdk.ExceptionStatistics` is a cheap periodic counter (`period 1000 ms`, enabled in both) and is the right first look at the `RestrictedActionException` path at 1,200/sec — the rate without paying for a stack trace per throw. `jdk.JavaExceptionThrow` gives you the trace and is the expensive one, hence the explicit `+jdk.JavaExceptionThrow#enabled=true` above.

**Version note.** JFR is free and in OpenJDK from Java 11 (JEP 328); on Oracle Java 8 it needed `-XX:+UnlockCommercialFeatures` and a licence, so "just turn on JFR" is not a Java 8 answer. On JDK 21 `jdk.JavaExceptionThrow` is off in both shipped settings files; on JDK 25 it is on with a `100/s` (default) / `300/s` (profile) throttle that JDK 21 does not have. Why `fillInStackTrace` is the cost: [../exceptions/03-internals-exception-mechanics.md](../exceptions/03-internals-exception-mechanics.md). JFR as a production practice belongs to guide 20, observability and operations.

**Correction on string deduplication.** There is no `jdk.StringDeduplication` JFR event on JDK 21 (nor on 25 — a metadata dump of a `profile` recording lists `jdk.StringFlag`, `jdk.StringFlagChanged` and `jdk.StringTableStatistics`, and nothing else matching). G1's dedup is observed through unified logging instead, and that tag is real:

```
$ java -XX:+UseG1GC -XX:+UseStringDeduplication -Xlog:'stringdedup*=debug' BalanceView
[0.008s][info][stringdedup,init] String Deduplication is enabled
[0.013s][debug][stringdedup     ] Starting string deduplication thread
[0.013s][debug][stringdedup,phases,start] Idle start
```

The `init` line confirms the feature is genuinely on — asking for it on a collector that does not support it is silently ignored. The `phases` lines bracket each dedup pass and report how many strings were examined and how much was saved; `StringDeduplicationAgeThreshold = 3` is why a short-lived `String` is never a candidate. Keep the single quotes: `zsh` tries to glob a bare `stringdedup*`.

### 4c. async-profiler: the call site `[X-REF 06]`

Mechanism: async-profiler hooks HotSpot's allocation-sampling callbacks (`AsyncGetCallTrace` plus the TLAB slow path) and attributes each sample to the full Java stack without safepoint bias — the specific flaw that makes an ordinary sampling profiler lie about allocation.

```
$ asprof -e alloc --alloc 512k -d 60 -f /tmp/alloc.html <pid>      # flame graph; use -o flat -f alloc.txt for a text ranking
```

`-e alloc` selects the allocation event, `--alloc <interval>` sets the sampling interval in bytes (larger = cheaper = blinder), `-o flat` gives a text ranking instead of a flame graph. On the 2.8M/day stake-reservation path the finding is a `java.lang.Integer` row whose hottest frame is `FundsLedger.reserve` — a restriction code above `AutoBoxCacheMax = 128` being boxed, with the flame graph naming the line. **Gotcha:** because sampling is per-bytes-allocated, a once-a-minute 40 MB array can rank *above* a 1,200/sec boxing site, and a once-an-hour one vanishes entirely. Cross-check totals against `jdk.ObjectAllocationSample` or `GC.class_histogram` before concluding.

### 4d. Heap dump plus MAT: the retention `[X-REF 06]`

Mechanism: a heap dump serialises every live object and every reference between them. MAT builds a *dominator tree* over that graph — A dominates B if every path from a GC root to B passes through A — which converts the unanswerable "why is this alive" into "read the path from B up to a root".

```
$ jcmd <pid> GC.heap_dump -all /var/tmp/payment-service.hprof
$ jhsdb jmap --binaryheap --pid <pid> --dumpfile /var/tmp/fallback.hprof   # if the VM is wedged
```

In MAT: open the dump, run *Leak Suspects*, then on the suspect run **Path to GC Roots → exclude weak/soft references**. The `PaymentRun` case reads as a chain from a `PaymentRun.Line` through a field literally named `this$0` to the `PaymentRun`, which holds the whole 7k-withdrawal batch alive. That field is the compiler-generated back-reference every non-`static` inner class keeps to its enclosing instance, so one surviving `Line` pins the batch; `javap -p PaymentRun\$Line.class` shows the field, closing the loop back to §1. Fix: make `Line` a `static` nested class (or a record) and pass it what it needs. Capture semantics and `this$0`: [../inheritance-and-dispatch/04-internals-nested-classes.md](../inheritance-and-dispatch/04-internals-nested-classes.md).

**Trade-off.** `GC.heap_dump` performs a full GC and stops the world for the duration of the dump — seconds to minutes at multi-GB heaps. On a node carrying part of 55k peak concurrent sessions that is a user-visible outage, so dump a drained node or a canary, or take the hit deliberately in a window. `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/tmp` costs nothing until the day it saves the investigation.

> **Definition — the allocation investigation chain:** JOL sizes one instance, JFR measures the rate, async-profiler names the call site, and a heap dump with MAT explains the retention; each tool answers the question the previous one leaves open, and using them out of order wastes the expensive one.

## Supporting instruments

### `jshell` — the ten-second experiment

Mechanism: `jshell` (Java 9+, JEP 222) wraps each snippet in a synthetic class and runs it on a real JVM, so the semantics are the language's rather than an interpreter's approximation. Script it for reproducible evidence — actual run:

```
$ jshell -q --execution local exp.jsh          # exp.jsh contents shown as executed
System.out.println(Integer.valueOf(127) == Integer.valueOf(127));      // true
System.out.println(Integer.valueOf(128) == Integer.valueOf(128));      // false
System.out.println("DEP-301 CAPTURED" == new String("DEP-301 CAPTURED").intern());   // true
Integer bonusMinor = null;
try { int x = true ? bonusMinor : 0; } catch (NullPointerException e) { System.out.println("NPE: " + e.getMessage()); }
NPE: Cannot invoke "java.lang.Integer.intValue()" because "REPL.$JShell$5.bonusMinor" is null
```

`true` then `false` is `AutoBoxCacheMax = 128` in one line: a restriction code of 127 is a cache hit, 128 is a fresh object. The third is `intern()` returning the literal already in the string table. The fourth is a ternary whose branches are `Integer` and `int`, so the whole expression is typed `int` and the `Integer` is unboxed — the helpful-NPE message (JEP 358, JDK 14, on by default from 15) names `intValue()` as the failing call, which is the proof that an invisible unboxing happened. **Gotcha:** `--execution local` runs snippets in the `jshell` JVM itself, which is what lets `jshell -R-XX:AutoBoxCacheMax=1000` move the cache boundary; the default remote JVM ignores flags you did not forward with `-R`.

> **Definition — `jshell`:** the JDK's REPL, which compiles and executes snippets on a real JVM, making single-expression language questions answerable in seconds and scriptable as evidence.

### `jcmd` — asking a live JVM `[X-REF 06]`

Mechanism: `jcmd` attaches to a running JVM over the attach mechanism (a socket in the process's temp directory) and issues a diagnostic command executed inside that VM, usually at a safepoint. `jcmd -l` lists attachable PIDs; `jcmd <pid> help` lists that VM's commands, which vary by version and collector.

| Subcommand | Answers | Cost |
|---|---|---|
| `VM.flags` | this node's actual flags, post-ergonomics | negligible; `-all` gives the full `PrintFlagsFinal` table |
| `VM.system_properties` | the real `java.version`, `file.encoding`, anything a launcher injected | negligible |
| `GC.class_histogram` | live `#instances` / `#bytes` per class | **forces a full GC** — a stop-the-world pause |
| `VM.native_memory summary` | NMT breakdown (needs `-XX:NativeMemoryTracking=summary` at startup) | small ongoing overhead |

```
$ jcmd 77410 GC.class_histogram
 num     #instances         #bytes  class name (module)
-------------------------------------------------------
   1:        209369        8434184  [B (java.base@25.0.1)
   2:        209227        5021448  java.lang.String (java.base@25.0.1)
   3:        200141        3202256  java.lang.Integer (java.base@25.0.1)
```

`[B` on top is the `byte[]` inside every `String` (`CompactStrings = true`, so Latin-1 text is one byte per character); the `String` count tracks it almost exactly, the signature of strings that each own a private array rather than sharing. `java.lang.Integer` at 200,141 instances is the stake-reservation boxing bill made visible. On JDK 21 the module suffix reads `(java.base@21.0.7)`. **Gotcha:** the full GC makes this the one subcommand you never fire casually on a node taking traffic, and note it is a *census* where `jdk.ObjectAllocationSample` is a *sample* — they disagree by design.

> **Definition — `jcmd`:** the JDK's single diagnostic entry point, which attaches to a live JVM and runs an in-VM diagnostic command, superseding `jinfo` / `jmap` / `jstack`.

### Static analysis that catches this guide's traps `[RESEARCH]`

Mechanism: ErrorProne is a `javac` plugin running *inside* the compiler with the real typed AST, which is how it distinguishes `Integer == Integer` from `int == int` — no text-based linter can. SpotBugs works the other way round, analysing compiled bytecode, so it sees desugared code. Running both is not redundant.

| Tool | Check | Trap in this guide it catches |
|---|---|---|
| ErrorProne | `ReferenceEquality` (WARNING) | a `StatusCode` compared with `==`, so `AA-801 ACTIVATED` from two sources never matches |
| ErrorProne | `BoxedPrimitiveEquality` (ERROR) | two `Integer` restriction codes compared with `==` — right up to 127, wrong at 128 |
| ErrorProne | `BadShiftAmount` (ERROR) | a 32-bit restriction mask shifted by 32: `1 << 32` is `1`, because `int` shifts mask the count to 5 bits |
| ErrorProne | `SelfEquals` (ERROR) | a hand-edited `Money.equals` comparing a field to itself |
| SpotBugs | `ES_COMPARING_STRINGS_WITH_EQ`, `SIC_INNER_SHOULD_BE_STATIC` | string identity seen in bytecode; the `PaymentRun.Line` retention of §4d, found statically |
| NullAway | `@Nullable` dataflow, hosted inside ErrorProne | the null `Money` amount reaching a ternary that unboxes it |
| SonarQube | `java:S1244`, `java:S2159`, `java:S4973` | float equality; `BigDecimal.equals` in a `Money` assertion; comparing incompatible types |

**Gotcha:** `ReferenceEquality` is a WARNING by default and warnings are noise, so it does nothing until you promote it — `-Xplugin:ErrorProne -Xep:ReferenceEquality:ERROR`. ErrorProne also needs `-XDcompilePolicy=simple` and `--should-stop=ifError=FLOW`, plus JDK 16+ `--add-exports` flags to reach `javac` internals.

> **Definition — ErrorProne:** a `javac`-hosted static analyser that inspects the typed AST during compilation, which is what lets it decide boxing and reference-equality questions a source-text linter cannot.

### IDE inspections worth enabling, and worth disabling

Mechanism: IntelliJ inspections run the same typed-AST analysis incrementally in the editor. Their default severities are tuned for signal-to-noise across all projects, not for a money-handling codebase, so they are wrong in both directions for QuizStakes.

Raise to ERROR: *Number comparison using `==`* and *String comparison using `==`* (the `StatusCode` and `Integer` traps); *`BigDecimal` compared with `equals`*, because a `Money` assertion must use `compareTo` — `new BigDecimal("3.00").equals(new BigDecimal("3.0"))` is `false` on scale alone; *Ignored or swallowed `InterruptedException`*, since a `PaymentRun` batch loop that eats the interrupt never shuts down cleanly; *Inner class may be `static`*, the `this$0` retention. Keep *Auto-boxing in a loop* as an informational hint only. Disable: *Local variable could be `final`* and *Parameter could be `final`*, which fire on every method and change nothing in the bytecode; *Class can be a record* on aggregates with identity or JPA mapping, where a record is wrong; *Field can be converted to a local* on Spring-injected fields the inspection cannot see the framework writing.

**Gotcha:** inspection state lives in the IDE, not the build, so it is a per-developer preference and never a guarantee. Anything that must not reach `main` belongs in ErrorProne or SpotBugs in CI. Use the IDE to shorten the loop, the build to enforce.

> **Definition — IDE inspection:** an editor-time static check over the typed AST, valuable for latency and worthless as a gate, because its configuration is local to the developer rather than to the build.

## Pitfalls

### Believing a decompiler shows you what the JVM runs

**Wrong**

```java
// Decompiled FundsLedger.total() — CFR, Fernflower and Procyon all print this
for (Movement m : this.movements) { sum = sum.add(m.amount()); }
```
"The class file contains my loop. There is no `Iterator`, no cast, and nothing allocated per call."

**Right**

```
         8: invokeinterface #19,  1  // InterfaceMethod java/util/List.iterator:()Ljava/util/Iterator;
        24: invokeinterface #31,  1  // InterfaceMethod java/util/Iterator.next:()Ljava/lang/Object;
        29: checkcast     #35        // class FundsLedger$Movement
```
There is an `Iterator`, allocated per call to `total()`, and a `checkcast` executed on every one of the ~19.8M daily ledger rows. The decompiler re-sugared both away because an enhanced-for is the prettiest source that produces this shape.

**Why people believe it:** the decompiler's output is *correct* — it compiles to equivalent bytecode. It answers "what source would produce this?" and the reader heard "what does this do?". Those coincide often enough that the gap only bites on exactly the questions an internals interview asks.

### Quoting a byte size without checking `UseCompressedOops`

**Wrong**

"A `Movement` is 24 bytes: 12 header, two 4-byte references, 4 padding. I measured it with JOL."

**Right**

You measured it where `-XX:+PrintFlagsFinal` prints `UseCompressedOops = true {ergonomic}`. On a `PaymentService` node whose heap exceeds ~32 GB, ergonomics turns compressed oops off: the class pointer becomes 8 bytes and each reference field becomes 8, so the same record is 32 bytes and the padding disappears. The number is a function of the flag and the flag is a function of the heap — print both, and read the origin marker, because `{ergonomic}` is a promise about *this* JVM and no other.

**Why people believe it:** compressed oops have been ergonomically on for every heap anyone tests locally since Java 7, so the 12-byte header behaves exactly like a language constant right up to the day someone raises `-Xmx` past the threshold and every cache-size estimate in the service is wrong at once.

### Measuring object size with `Runtime.freeMemory()` deltas or `System.gc()`

**Wrong**

```java
Movement[] batch = new Movement[100_000];
System.gc();
long before = Runtime.getRuntime().freeMemory();
for (int i = 0; i < batch.length; i++) batch[i] = new Movement("CLIENT_CASH_AVAILABLE", BigDecimal.ONE);
System.gc();
System.out.println("bytes each: " + (before - Runtime.getRuntime().freeMemory()) / batch.length);
```

**Right**

`java -Djol.magicFieldOffset=true -jar jol-cli-0.17-full.jar internals -cp out 'FundsLedger$Movement'` prints `Instance size: 24 bytes` and the field offsets that produce it. The delta method measures the heap, not the object: `System.gc()` is advisory (`-XX:+DisableExplicitGC` makes it a no-op outright), `freeMemory()` reports a committed-heap figure that G1 resizes underneath you, TLAB allocation moves the bump pointer in chunks unrelated to your objects, and background threads allocate throughout. The result is noise plus a shared `String` literal counted once per element.

**Why people believe it:** the numbers it produces are plausible and roughly stable across runs, so it survives casual checking. It is the single most common route to a confidently wrong object-size figure.

## Cheat sheet

| Question | Command | Look for |
|---|---|---|
| What did `javac` emit for this method? | `javap -c -p out/FundsLedger.class` | `invokeinterface`, `checkcast`, `invokedynamic` |
| Which release targeted this class file? | `javap -v out/FundsLedger.class \| head` | `major version:` (65 = 21, 61 = 17, 52 = 8) |
| Who implements this string concat? | `javap -v out/FundsLedger.class` | `BootstrapMethods` → `StringConcatFactory` and the recipe |
| Was this class loaded, and from where? | `java -Xlog:class+load=info App \| grep BonusService` | `BonusService source: jar:file:/opt/qs/bonus.jar` |
| Who triggered this `<clinit>`? | `java -Xlog:class+init=info App` | `Initializing 'BonusService' by thread "main"`, and what precedes it |
| Is this constant folded into callers? | `javap -c BalanceView.class` | `ldc` (folded) versus `getstatic` (triggers init) |
| What is this flag's real value? | `java -XX:+PrintFlagsFinal -version \| grep AutoBoxCacheMax` | the value plus `{default}` / `{ergonomic}` |
| Are references 4 or 8 bytes here? | `java -XX:+PrintFlagsFinal -version \| grep UseCompressedOops` | `true {ergonomic}` — recheck on the target heap |
| Does JDK 21 have compact headers? | `java -XX:+PrintFlagsFinal -version \| grep UseCompactObjectHeaders` | no output — the flag does not exist on 21 |
| What are a live node's flags? | `jcmd <pid> VM.flags` | `-XX:+UseCompressedOops`, `-XX:MaxHeapSize` |
| What is on the heap right now? | `jcmd <pid> GC.class_histogram` | `[B`, `java.lang.String`, `java.lang.Integer` counts — forces a full GC |
| What does one instance cost? | `java -Djol.magicFieldOffset=true -jar jol-cli-0.17-full.jar internals -cp out 'FundsLedger$Movement'` | `Instance size`, field order, alignment gap |
| Is this box or intern the same object? | `jshell -q --execution local exp.jsh` | `true` / `false` |
| How often is this exception thrown? | `jfr print --events jdk.ExceptionStatistics /tmp/settle.jfr` | throw count per second, no stack-trace cost |
| Which stack throws it? | `-XX:StartFlightRecording=settings=profile,+jdk.JavaExceptionThrow#enabled=true` | `jdk.JavaExceptionThrow` events with traces |
| Which types are being allocated? | `jfr print --events jdk.ObjectAllocationSample /tmp/settle.jfr` | type plus stack, throttled 150/s default, 300/s profile |
| Which call site allocates them? | `asprof -e alloc -d 60 -f /tmp/alloc.html <pid>` | `java.lang.Integer` under `FundsLedger.reserve` |
| Is G1 string dedup actually on? | `java -XX:+UseG1GC -XX:+UseStringDeduplication -Xlog:'stringdedup*=debug' App` | `[stringdedup,init] String Deduplication is enabled` |
| Why is this object still alive? | `jcmd <pid> GC.heap_dump -all /var/tmp/ps.hprof`, then MAT | Path to GC Roots → a `this$0` edge |
| Will this trap reach `main`? | `javac -Xplugin:ErrorProne -Xep:ReferenceEquality:ERROR` | `BoxedPrimitiveEquality`, `BadShiftAmount`, `SelfEquals` |

## Self-test

**Q1.** You claim a `Movement` instance is 24 bytes. What do you check first, and why?

<details><summary>Answer</summary>

`java -XX:+PrintFlagsFinal -version | grep -E 'UseCompressedOops|ObjectAlignmentInBytes'` on the target machine, before quoting anything. The 24 bytes decomposes as 12 bytes of header (8 mark + 4 compressed class pointer) + two 4-byte compressed reference fields + 4 bytes of alignment padding, and three of those four terms depend on `UseCompressedOops`. That flag prints as `{ergonomic}`, not `{default}`, meaning the VM chose it from the heap size and will choose differently above roughly 32 GB, at which point the same record is 32 bytes. Then confirm the layout itself with JOL `internals` rather than deriving it, because HotSpot reorders fields. On JDK 24+ you would also check `UseCompactObjectHeaders`; on JDK 21 that flag does not exist and finding nothing is the correct outcome.
</details>

**Q2.** A colleague shows you decompiled source from IntelliJ and says the enhanced-for over `movements` allocates nothing. How do you settle it?

<details><summary>Answer</summary>

`javap -c -p` on the same class file. IntelliJ decompiles with Fernflower, which re-sugars the `Iterator` loop back into an enhanced-for — the source it prints is correct in the sense that it compiles to equivalent bytecode, and useless for this question. The disassembly shows `invokeinterface java/util/List.iterator:()Ljava/util/Iterator;`, so an `Iterator` is allocated per call, plus a `checkcast` per element from erasure. Whether that allocation survives to the heap is a *different* question, decided by escape analysis and answered by async-profiler `-e alloc` against the running service, not by any static tool.
</details>

**Q3.** Bumping a `static final int GRANT_CAP_MINOR` in `BonusService` and redeploying only that jar changed nothing. Explain, with the command that proves it.

<details><summary>Answer</summary>

`GRANT_CAP_MINOR` is a *constant variable* under JLS §4.12.4 — `final`, primitive type, constant-expression initialiser — so `javac` inlined its value into every reader's constant pool at *their* compile time. `javap -c BalanceView.class` shows `ldc` with the folded value and no mention of `BonusService`, where a non-constant field would show `getstatic`. `-Xlog:class+init=info` corroborates from the other side: the folded value prints *before* the `Initializing 'BonusService'` line, because a folded constant is not one of the five initialization triggers. Fix by recompiling all readers, or by sourcing the value from configuration so the read is a real field access.
</details>

**Q4.** JFR reports heavy `java.lang.Integer` allocation, but async-profiler `-e alloc` puts `FundsLedger.reserve` nowhere near the top. Who is wrong?

<details><summary>Answer</summary>

Neither, necessarily — they measure different things and both sample. `jdk.ObjectAllocationSample` is throttled to a fixed event rate (150/s on `default`, 300/s on `profile`), so on a 3,400/sec settlement burst it is a proportional sample scaled up, and its *type* attribution is far more trustworthy than any byte total derived from it. async-profiler samples per bytes allocated at the `--alloc` interval, so it ranks by volume and can put a rare huge array above a very frequent small allocation. Reconcile with a census: `jcmd <pid> GC.class_histogram` gives exact live counts at the price of a full GC, and if `java.lang.Integer` is not high there, the boxing is short-lived and dying in young generation — a different and much cheaper problem than a steady stream of surviving garbage.
</details>

**Q5.** A `PaymentRun` for 7k bank withdrawals is retained long after the run completes. Walk the investigation.

<details><summary>Answer</summary>

`jcmd <pid> GC.heap_dump -all /var/tmp/ps.hprof` on a drained node — it performs a full GC and stops the world for the dump, so not on a node carrying peak sessions. Open in Eclipse MAT, run Leak Suspects, then Path to GC Roots with weak and soft references excluded on the retained `PaymentRun`. The path runs through a `PaymentRun.Line` field named `this$0`, the synthetic back-reference every non-`static` inner class holds to its enclosing instance. Confirm statically with `javap -p PaymentRun\$Line.class`, which lists `final PaymentRun this$0;`. Fix: make `Line` `static` (or a record) and pass it the data it needs. Prevent recurrence with SpotBugs `SIC_INNER_SHOULD_BE_STATIC` in CI, and set `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/tmp` so the next occurrence dumps itself.
</details>

## Deferred

None.

## Open questions

- **JDK 21 versus JDK 25 for the shipped JFR settings.** The `.jfc` values quoted in §4b (`jdk.ObjectAllocationSample` throttled 150/s on `default` and 300/s on `profile`; `jdk.ObjectAllocationInNewTLAB` disabled in both; `jdk.ExceptionStatistics` enabled with a 1000 ms period in both) were read from `$JAVA_HOME/lib/jfr/*.jfc` on the JDK 25 installed here. **Unverified:** that `jdk.JavaExceptionThrow` is disabled in *both* shipped settings files on JDK 21 — on JDK 25 it is enabled with an `exceptions-throttle-rate` control that JDK 21 does not have. Explicitly enabling it with `+jdk.JavaExceptionThrow#enabled=true` is correct and harmless on every version from 11 onward, which is why the text recommends it unconditionally. Settle it by reading `lib/jfr/default.jfc` in a JDK 21.0.7 installation.
- **Not run here:** the async-profiler invocation (`-e alloc`, `--alloc <interval>`, `asprof` launcher — the 2.x launcher was `profiler.sh`), because async-profiler is not installed on this machine; and the Eclipse MAT screens in §4d (Leak Suspects, Path to GC Roots with weak/soft excluded), described from knowledge. The `jcmd GC.heap_dump` and `javap -p` commands that bracket the MAT step are real.

---

**Leaves covered:** 3.18.1–3.18.13 (13 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 498
