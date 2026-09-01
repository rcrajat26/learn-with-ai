# 06 — JVM Internals

The difference between a mid-level and a senior backend engineer in interviews is usually visible
here: can you take "the service got slow and then died" and turn it into a diagnosis with named tools
and named evidence? This guide is organized to make that answer available.

---

## 1. Runtime memory areas

The JVM divides memory into areas with different lifetimes, sharing, and failure modes.

| Area | Shared? | Holds | Error when exhausted |
|---|---|---|---|
| **Heap** | all threads | all objects and arrays | `OutOfMemoryError: Java heap space` |
| **Stack** | per thread | frames: locals, operand stack, return address | `StackOverflowError` |
| **Metaspace** | all threads | class metadata, method bytecode | `OutOfMemoryError: Metaspace` |
| **Code cache** | all threads | JIT-compiled native code | code cache full → JIT disables, silent slowdown |
| **Native/direct** | all threads | direct ByteBuffers, JNI, thread stacks | `OutOfMemoryError: Direct buffer memory` |
| **PC register** | per thread | current instruction pointer | — |

**Stack** frames are pushed per method call and popped on return. Depth is bounded by `-Xss` (typically
512 KB–1 MB). Deep or infinite recursion throws `StackOverflowError`. Note this is an `Error`, not an
`Exception` — catching it is possible but the stack state is untrustworthy.

**Metaspace** replaced PermGen in Java 8 and lives in **native** memory, growing dynamically unless
capped with `-XX:MaxMetaspaceSize`. It holds class metadata, so metaspace leaks come from *classes*,
not objects: repeated redeployment in an app server, dynamic proxy or bytecode generation in a loop,
and classloader leaks.

**Trap:** "the heap is the JVM's memory" is wrong and it breaks container sizing. Total RSS = heap +
metaspace + code cache + thread stacks (threads × `-Xss`) + direct buffers + GC structures + the
allocator's own overhead. Setting `-Xmx` equal to the container limit guarantees an eventual
OOMKill.

---

## 2. Garbage collection

### The generational hypothesis
Most objects die young. GC exploits this by splitting the heap so that collecting the young space is
cheap and frequent, and the expensive full collection is rare.

- **Young generation** — Eden plus two Survivor spaces (S0/S1). New objects go in Eden. A **minor GC**
  copies the few live objects to a survivor space and reclaims the rest wholesale. Because it copies
  survivors rather than scanning garbage, its cost is proportional to *live* data, not total data —
  which is why allocating many short-lived objects is genuinely cheap in Java.
- Objects surviving enough minor GCs (the tenuring threshold) are **promoted** to the old generation.
- **Old generation** — long-lived objects. A **major/full GC** here is much more expensive.

**Stop-the-world (STW)**: all application threads pause at a safepoint while GC runs. Every collector
has STW phases; they differ in how long and how often. STW pauses are what your p99 latency graph is
actually measuring when it spikes.

### Collectors

| Collector | Flag | Character |
|---|---|---|
| Serial | `-XX:+UseSerialGC` | single-threaded; tiny heaps, containers with 1 CPU |
| Parallel | `-XX:+UseParallelGC` | throughput-optimized, multi-threaded STW; batch jobs |
| **G1** | `-XX:+UseG1GC` | **default since Java 9**; region-based, pause-target driven |
| ZGC | `-XX:+UseZGC` | concurrent, sub-millisecond pauses, scales to terabytes |
| Shenandoah | `-XX:+UseShenandoahGC` | concurrent compaction, low pause |
| Epsilon | `-XX:+UseEpsilonGC` | no-op collector, for testing allocation behaviour |

**G1** ("Garbage First") splits the heap into ~2048 equal **regions**, each dynamically labelled Eden,
Survivor, Old or Humongous. It tracks liveness per region and collects the regions with the most
garbage first, within a soft pause goal set by `-XX:MaxGCPauseMillis` (default 200 ms). It performs
concurrent marking and compacts incrementally, which avoids the fragmentation that plagued CMS.
Objects larger than half a region are "humongous" and allocated directly in Old — a stream of large
arrays can therefore fill Old without any old-gen "leak".

**ZGC** does essentially all work concurrently using coloured pointers and load barriers, giving pauses
under a millisecond independent of heap size, at some throughput cost. Reach for it when tail latency
matters more than throughput.

**Tuning advice worth giving in an interview:** set `-Xms` equal to `-Xmx` (avoids resize pauses and
makes behaviour predictable), set a realistic pause goal, and change nothing else until you have
measured. Most "GC tuning" problems are allocation problems or leaks.

Enable GC logging always — it is nearly free and irreplaceable after an incident:
```
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=20M
```

**Trap:** `System.gc()` is a *hint*, may be ignored (`-XX:+DisableExplicitGC`), and typically triggers
a full STW collection. Never call it in application code.

**Trap:** finalizers and `Cleaner`s delay reclamation by at least one extra GC cycle and can back up
the reference-processing queue. Use try-with-resources.

---

## 3. OutOfMemoryError — the taxonomy

The message after the colon tells you which subsystem failed. Read it before theorizing.

| Message | Meaning | Usual cause |
|---|---|---|
| `Java heap space` | heap full, GC cannot reclaim | leak, undersized heap, unbounded cache or queue |
| `GC overhead limit exceeded` | >98% of time in GC recovering <2% of heap | a leak, just before the heap-space error |
| `Metaspace` | class metadata exhausted | classloader leak, dynamic class generation |
| `Direct buffer memory` | direct ByteBuffer limit hit | Netty/NIO buffers not released; `-XX:MaxDirectMemorySize` |
| `unable to create new native thread` | OS thread limit or native memory exhausted | thread leak, missing pool shutdown, low ulimit |
| `Requested array size exceeds VM limit` | array larger than ~Integer.MAX_VALUE | a bug in size arithmetic |

Always run production with:
```
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/
-XX:+ExitOnOutOfMemoryError
```
The first gives you the evidence — an OOM without a heap dump means you will be guessing. The second
kills the process rather than leaving it in a half-dead state where some threads died and the health
check still passes; the orchestrator restarts it cleanly.

**Trap:** an `OutOfMemoryError` kills only the thread that hit it. Other threads carry on in a
degraded, partially-initialized world. This is why a JVM that "OOMed an hour ago" can be producing
bizarre, unrelated errors — and why `ExitOnOutOfMemoryError` matters.

---

## 4. Class loading

Loading has three phases: **loading** (read bytes, create the `Class` object), **linking**
(verification, preparation of static fields to defaults, optional resolution), and
**initialization** (run static initializers and static field assignments — exactly once, thread-safely,
guaranteed by the JVM).

The **delegation hierarchy**: Bootstrap (core JDK classes) → Platform/Extension → Application
(classpath) → any custom loaders. A loader asks its **parent first**, and only loads the class itself
if the parent cannot. This prevents application code from replacing `java.lang.String`.

Class identity is `(fully qualified name, defining classloader)`. The same class file loaded by two
loaders produces two incompatible types — the source of
`ClassCastException: com.X cannot be cast to com.X`, which looks impossible until you know this.

**Trap — the two errors that sound the same:**
- `ClassNotFoundException` — a **checked** exception from an explicit dynamic lookup
  (`Class.forName`, `loader.loadClass`). The class was never found. Usually a missing dependency.
- `NoClassDefFoundError` — an **Error** thrown when the class was present at compile time but is
  missing or **failed to initialize** at runtime. The nastiest case: a static initializer threw an
  exception on the *first* use (you get `ExceptionInInitializerError` once), and every subsequent use
  throws `NoClassDefFoundError` for a class that is right there on the classpath. Always look for the
  original `ExceptionInInitializerError` earlier in the log.

Custom classloaders power app servers, plugin systems, and hot reload. Their classic failure is the
**classloader leak**: any strong reference from a longer-lived context (a static field in a JDK class,
a ThreadLocal on a pool thread, a JDBC driver registered in `DriverManager`, a running timer thread)
pins the whole classloader and every class it defined, leaking metaspace on each redeploy.

---

## 5. JIT compilation and warmup

Java starts by **interpreting** bytecode. The JVM profiles execution and, once a method or loop passes
an invocation threshold, compiles it to native code — **HotSpot's** tiered compilation:

- Tier 0: interpreter.
- Tiers 1–3: **C1**, fast compilation, light optimization, gathers profiling data.
- Tier 4: **C2**, slow compilation, aggressive optimization using the collected profile.

Because C2 uses the observed profile, it can do things a static compiler cannot: inline hot virtual
calls after proving there is effectively one receiver (monomorphic inlining), eliminate dead branches
never taken, escape-analyze objects that never leave a method and allocate them on the stack or
scalar-replace them entirely, unroll loops, and eliminate redundant locks. If an assumption is later
violated, it **deoptimizes** back to the interpreter and recompiles.

**Warmup** is the direct consequence: the first thousands of executions run at interpreted or C1 speed.
Real implications — the first requests after a deploy are slow, so a health check that passes
instantly can send full traffic to a cold JVM; benchmarks that do not warm up measure the interpreter;
and canary rollouts should ramp traffic rather than switch it.

Options: `-XX:+PrintCompilation` to see compilation events, `-XX:-TieredCompilation` to force C2 only,
AOT/CDS (`-XX:SharedArchiveFile`) to cut startup class-loading cost, and GraalVM native-image to
eliminate warmup entirely at the cost of peak throughput and dynamic features.

**Trap:** microbenchmarks without warmup, without dead-code elimination guards, and without multiple
forks measure noise. Use **JMH**:

```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5) @Measurement(iterations = 10) @Fork(2)
@State(Scope.Benchmark)
public class MyBench {
    @Benchmark public int measure() { return compute(); }   // returning it prevents DCE
}
```
JMH handles warmup, forking (fresh JIT profile per fork), blackholes to defeat dead-code elimination,
and state scoping. Knowing *why* each of those exists is the interview-worthy part.

---

## 6. Diagnostic tooling

Know these by name and by what they output.

| Tool | Gives you |
|---|---|
| `jps -l` | running JVMs and their PIDs |
| `jstack <pid>` | thread dump: every thread's stack, state, and held/awaited locks |
| `jmap -histo:live <pid>` | live object histogram by class — count and bytes |
| `jmap -dump:live,format=b,file=heap.hprof <pid>` | full heap dump |
| `jstat -gcutil <pid> 1s` | live GC statistics: space utilization percentages, GC counts and times |
| `jcmd <pid> <command>` | the modern superset — `Thread.print`, `GC.heap_info`, `GC.heap_dump`, `VM.flags`, `VM.native_memory`, `JFR.start` |
| `jinfo <pid>` | current flags and system properties |
| Java Flight Recorder | low-overhead continuous profiling; `jcmd <pid> JFR.start duration=60s filename=r.jfr` |
| JDK Mission Control | reads JFR recordings |
| Eclipse MAT | heap-dump analysis, dominator tree, leak suspects |
| `async-profiler` | flame graphs for CPU and allocation, no safepoint bias |

Prefer `jcmd` — it is the actively maintained entry point and the others are effectively aliases.

### Workflow: a thread pegged at 100% CPU

This is the classic live-debugging interview question. The answer is a procedure.

1. `top -H -p <pid>` — list **threads** and find the one burning CPU. Note its TID (decimal).
2. `printf '%x\n' <tid>` — convert to hex, because thread dumps print `nid` in hex.
3. `jstack <pid> > dump.txt` — take a thread dump. Take **three, a few seconds apart**; a thread stuck
   at the same frame across all three is the culprit, while a moving stack is just busy work.
4. Search `dump.txt` for `nid=0x<hex>` and read the stack.

Typical findings: an infinite loop, a regex with catastrophic backtracking, an unbounded
`HashMap.get` degenerating under a bad hash, or — very commonly — **GC**, in which case the hot
threads are `GC task thread#N`, and the real problem is heap pressure, not application code. Check
`jstat -gcutil` before blaming code.

Also read the dump for deadlocks (`jstack` prints "Found one Java-level deadlock" explicitly) and for
large numbers of BLOCKED threads pointing at one monitor.

### Workflow: suspected memory leak

1. `jstat -gcutil <pid> 1s 60` — watch **old-gen utilization after each full GC**. If the post-GC
   floor rises monotonically over time, it is a leak. If it returns to a stable baseline, the heap is
   just undersized or the load spiked.
2. `jmap -histo:live <pid>` at two points in time and diff — which class grew?
3. `jcmd <pid> GC.heap_dump /tmp/heap.hprof` (or rely on `HeapDumpOnOutOfMemoryError`). Note the dump
   pauses the JVM and is roughly heap-sized on disk.
4. Open in **Eclipse MAT**. Run **Leak Suspects**, then the **Dominator Tree** — this shows which
   objects hold the most retained heap. **Retained size** (memory freed if this object were collected)
   is the number that matters, not shallow size.
5. Right-click the suspect → **Path to GC Roots (exclude weak/soft references)**. That path *is* the
   leak: it tells you which live reference is preventing collection.

**Common Spring/Java leak culprits:**
- An unbounded `HashMap` or `ConcurrentHashMap` used as a cache with no eviction, held in a singleton
  bean. The single most common one.
- `ThreadLocal` values never removed on pooled request threads (guide 05, section 12).
- Listeners, callbacks, or `@EventListener`-registered objects never deregistered.
- `static` collections accumulating entries.
- Non-static inner classes and anonymous listeners holding their enclosing object.
- Unclosed resources — JDBC connections, streams, `HttpClient` responses — exhausting a pool.
- Session-scoped or request-scoped state promoted to singleton scope by accident.
- Interned or `substring`-derived strings retained in a long-lived structure.
- An unbounded `LinkedBlockingQueue` in a thread pool backing up under load.

Prefer a bounded cache (Caffeine with `maximumSize` plus `expireAfterWrite`) over a raw map, always.

---

## 7. Container awareness

Since Java 10 (backported to 8u191) the JVM reads cgroup limits, so `Runtime.availableProcessors()`
and default heap sizing respect the container rather than the host. Verify with
`-XX:+PrintFlagsFinal -version | grep MaxHeapSize`.

Default `MaxRAMPercentage` is **25%** of the container limit — deliberately conservative and almost
always wrong for a dedicated service container. Set it explicitly:

```
-XX:InitialRAMPercentage=60 -XX:MaxRAMPercentage=70
```

Leave 25–35% headroom for metaspace, code cache, thread stacks, direct buffers and GC structures.

**Trap — OOMKilled versus OutOfMemoryError.** These are completely different events and are constantly
confused:
- `java.lang.OutOfMemoryError` is thrown by the **JVM** when the heap (or metaspace, etc.) cannot
  satisfy an allocation. You get a stack trace, and a heap dump if configured.
- **OOMKilled** (exit code 137, `Reason: OOMKilled` in `kubectl describe pod`) is the **Linux kernel**
  killing the process because the container exceeded its memory cgroup limit. There is no stack trace,
  no heap dump, no Java-level log line — the process just vanishes. `dmesg` shows the kernel OOM
  killer entry.

If you see 137 with no Java error, the JVM's *non-heap* memory is the suspect: too many threads, direct
buffers, metaspace growth, or simply `-Xmx` set too close to the container limit. Diagnose with
Native Memory Tracking: start with `-XX:NativeMemoryTracking=summary`, then
`jcmd <pid> VM.native_memory summary`, which breaks down every native category.

Also relevant in containers: `-XX:ActiveProcessorCount` when CPU limits are fractional (a 0.5-CPU
limit still reports 1, and GC/ForkJoin thread pools sized from processor count can be badly wrong),
and using `-XX:+UseSerialGC` for very small single-CPU containers where G1's overhead does not pay.

---

## Atomic concept checklist

- [ ] Heap is shared and holds objects; each thread owns a stack; metaspace holds class metadata in native memory.
- [ ] Heap exhaustion gives OutOfMemoryError, stack exhaustion gives StackOverflowError, class metadata gives OOM: Metaspace.
- [ ] Total process memory is heap plus metaspace, code cache, thread stacks, direct buffers and GC overhead — never set `-Xmx` to the container limit.
- [ ] Metaspace replaced PermGen in Java 8 and grows in native memory unless capped.
- [ ] The generational hypothesis is why minor GC is cheap: cost scales with live data, not garbage.
- [ ] Eden → Survivor → promotion to Old after the tenuring threshold.
- [ ] G1 is the default since Java 9: region-based, pause-goal driven, incrementally compacting; humongous objects go straight to Old.
- [ ] ZGC gives sub-millisecond pauses independent of heap size, trading throughput.
- [ ] Set `-Xms` equal to `-Xmx`, always enable GC logging, and never call `System.gc()`.
- [ ] Read the text after `OutOfMemoryError:` — heap space, Metaspace, Direct buffer memory and native thread are four different diagnoses.
- [ ] `GC overhead limit exceeded` means >98% of time in GC reclaiming <2% — the leak's last warning.
- [ ] Always run with `HeapDumpOnOutOfMemoryError` and `ExitOnOutOfMemoryError`; an OOM kills only one thread otherwise.
- [ ] Classloading delegates to the parent first; class identity is name plus defining loader.
- [ ] `ClassNotFoundException` is a checked exception from a dynamic lookup; `NoClassDefFoundError` often means a static initializer already failed — look for the earlier `ExceptionInInitializerError`.
- [ ] Classloader leaks come from static fields, ThreadLocals, JDBC drivers, and stray threads pinning a loader.
- [ ] HotSpot interprets first, then C1, then C2 using the collected profile; wrong assumptions cause deoptimization.
- [ ] Warmup is real: the first requests after a deploy run interpreted, so ramp traffic rather than switching it.
- [ ] JMH exists because warmup, dead-code elimination and per-fork JIT profiles all invalidate naive benchmarks.
- [ ] `jcmd` is the modern superset of jstack/jmap/jinfo; JFR gives low-overhead continuous profiling.
- [ ] 100% CPU workflow: `top -H`, convert TID to hex, take three jstacks, match `nid=0x…`, and rule out GC threads first.
- [ ] Leak workflow: watch post-full-GC old-gen floor with jstat, diff histograms, heap dump, MAT dominator tree, path to GC roots.
- [ ] Retained size, not shallow size, identifies the culprit in MAT.
- [ ] The most common Spring leak is an unbounded map cache in a singleton bean; use Caffeine with a size and TTL bound.
- [ ] Default `MaxRAMPercentage` is 25%; set it to ~70% and leave headroom for non-heap memory.
- [ ] OOMKilled (exit 137, no stack trace, kernel cgroup kill) is not the same as OutOfMemoryError; use Native Memory Tracking to investigate.