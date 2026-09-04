---

# PART 4 — BUILD IT

Ten artefacts. Each one exists to convert a claim made earlier in this file into a number measured on
a real box, and each one must end by naming the trap it proves and how it differs from the production
tool that already does the job.

## §4.1 A process and signal harness: `fork`/`exec`/`wait` in C, `ProcessBuilder` in Java `[BUILD]`

4.1.1 **The C harness.** ~120 lines: `fork()`, then in the child `dup2()` a pipe onto `STDOUT_FILENO`,
      `execvp("/usr/bin/sha256sum", ...)` against a `PaymentRun` payout file, and in the parent
      `wait4(pid, &status, 0, &rusage)`. Print `WIFEXITED`/`WEXITSTATUS`, `WIFSIGNALED`/`WTERMSIG`,
      and the full `struct rusage` — `ru_utime`, `ru_stime`, `ru_maxrss` (KiB), `ru_minflt`,
      `ru_majflt`, `ru_nvcsw`, `ru_nivcsw`. `[SYSCALL]` `[BUILD]`
4.1.2 **The zombie and orphan demonstrations, both deliberate.** Variant A: the parent `sleep(60)`s
      without `wait`ing — `ps -o pid,ppid,stat,cmd` must show `Z` and `/proc/<pid>/status` must show
      `State: Z (zombie)` with **no `VmRSS` line**, proving a zombie holds no memory. Variant B: the
      parent `_exit(0)`s first — the child's `PPid` in `/proc/<pid>/status` must change to **1**
      (or to the nearest `prctl(PR_SET_CHILD_SUBREAPER, 1)` ancestor, which the harness also sets in
      a third variant). `[PROC]` `[PROVE]`
4.1.3 **The signal half.** Install a handler with `sigaction()` (never `signal()`), using only
      `write(2)` inside the handler and a `volatile sig_atomic_t` flag, and block delivery around the
      critical section with `sigprocmask(SIG_BLOCK, ...)`. Prove the async-signal-safety rule by
      calling `printf` in a second variant under load and observing interleaved/garbled output. Then
      prove `SIGKILL` and `SIGSTOP` cannot be caught: `sigaction(SIGKILL, ...)` must return `-1` with
      `errno == EINVAL`. `[SYSCALL]` `[PROVE]`
4.1.4 **The Java 21 equivalent, and the measurement that matters.** A `record ExecResult(int exitCode,
      String stdout, String stderr, Duration wall)` produced by
      `new ProcessBuilder("sha256sum", file).redirectErrorStream(true).start()`, consuming the stream
      with `p.inputReader().lines()` on a virtual thread and calling
      `p.waitFor(30, TimeUnit.SECONDS)` — then `p.destroy()` (SIGTERM) and, if still alive,
      `p.destroyForcibly()` (SIGKILL). Run it from a JVM started with `-Xmx12g -XX:+AlwaysPreTouch`
      and time it under `-Djdk.lang.Process.launchMechanism=POSIX_SPAWN` versus `FORK`: the
      `POSIX_SPAWN` path must be roughly flat as the heap grows, the `FORK` path must scale with
      touched heap because it copies ~**24 MB of page tables** per 12 GB. `[API]` `[CALC]`
      `[VERSION-TRAP]`
4.1.5 **The number it must land on.** Report, for 1,000 iterations: mean `fork`+`exec`+`wait` wall
      time (expect **1–3 ms** dominated by `execve`'s ELF load and dynamic linking, not by `fork`),
      mean `posix_spawn` wall time, and `ru_minflt` per child. Then report the same for a JVM with a
      12 GB pre-touched heap and show the `FORK` variant's `ru_minflt` rising by tens of thousands.
      `[NUM]` `[CALC]`
4.1.6 **The trap it proves.** A `ProcessBuilder` whose output stream is never drained deadlocks at
      the **64 KiB** default pipe buffer (`/proc/sys/fs/pipe-max-size` bounds it; `fcntl(F_GETPIPE_SZ)`
      reads it) — the child blocks in `write`, the parent blocks in `waitFor`, and neither ever
      returns. Reproduce it with a child emitting 1 MiB, then fix it three ways and time each:
      drain-on-a-thread, `redirectOutput(Redirect.to(file))`, and `Redirect.DISCARD`. This is the
      §1.4.14 `BankWithdrawal` zombie incident in 40 lines. `[TRAP]` `[INCIDENT]`
4.1.7 **Diff vs the real one** (`zt-exec`, Apache Commons Exec, `systemd-run --scope`, Kubernetes
      Jobs): pumped stream handling with bounded buffers, per-stream charset handling, timeout →
      SIGTERM → grace → SIGKILL escalation ladders, environment scrubbing, working-directory and
      umask control, exit-code allowlists, process-group kill (`kill(-pgid, ...)`) so grandchildren
      die too, cgroup placement, and OOM-score adjustment for the child. `[TABLE]`

*(7 leaves)*

## §4.2 A minimal `epoll` echo server in C, and the Java NIO equivalent `[BUILD]`

4.2.1 **The C server, complete.** `socket(AF_INET, SOCK_STREAM|SOCK_NONBLOCK|SOCK_CLOEXEC, 0)`,
      `setsockopt(SO_REUSEADDR)`, `bind`, `listen(fd, 4096)`, `epoll_create1(EPOLL_CLOEXEC)`, then a
      loop over `epoll_wait(epfd, events, 1024, -1)` with
      `struct epoll_event { uint32_t events; epoll_data_t data; }` carrying the connection state in
      `data.ptr`. Registration via `epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev)` with
      `EPOLLIN|EPOLLRDHUP|EPOLLERR`. `[SYSCALL]` `[BUILD]`
4.2.2 **Both trigger modes, side by side, with the bug in each.** Level-triggered: return to
      `epoll_wait` after a single partial `read` and it re-reports — correct but chattier.
      Edge-triggered (`EPOLLET`): you **must** loop `read()` until `EAGAIN`/`EWOULDBLOCK` or the
      connection stalls forever with data sitting in the socket buffer. Ship the ET version with the
      drain loop deliberately removed, reproduce the hang against a client that writes 128 KiB in one
      `write`, then add the loop. `[TRAP]` `[PROVE]`
4.2.3 **Writability handled correctly.** Register `EPOLLOUT` **only** when a `write` returns short or
      `EAGAIN`, buffer the remainder, and `EPOLL_CTL_MOD` it back off once drained — the
      always-registered-`EPOLLOUT` mistake produces a 100%-CPU spin that `top` shows as `%us` with
      no work done. Also handle `EPOLLRDHUP` (peer half-closed) distinctly from `read` returning 0.
      `[TRAP]`
4.2.4 **The Java 21 NIO equivalent.** `ServerSocketChannel.open()` + `configureBlocking(false)` +
      `register(selector, SelectionKey.OP_ACCEPT)`, per-connection state in
      `key.attach(new Conn(ByteBuffer.allocateDirect(16 * 1024)))`, and the two things people get
      wrong: **`selectedKeys().iterator().remove()` on every iteration**, and calling
      `interestOps(OP_WRITE)` only when a partial write occurred. Confirm the JDK is using `epoll`
      with `-Djava.nio.channels.spi.SelectorProvider` unset and
      `strace -e trace=epoll_create1,epoll_ctl,epoll_wait -f -p <pid>` for one second only.
      `[API]` `[DIAG]`
4.2.5 **The third variant: the identical blocking code on virtual threads.** The same handler written
      as straight-line `in.read()`/`out.write()` submitted to
      `Executors.newVirtualThreadPerTaskExecutor()`. Prove with `top -H -p <pid>` that the kernel sees
      only `ForkJoinPool-1-worker-N` carriers — **`availableProcessors()` of them** — not 10,000
      threads, and with `/proc/<pid>/task | wc -l` that the task count is flat. `[API]` `[PROC]`
4.2.6 **The measurement it must produce.** 10,000 idle connections and then 10,000 connections at 100
      msg/sec each, against all four servers (LT C, ET C, NIO selector, virtual threads), reporting:
      `/proc/<pid>/status` `VmRSS`, thread count, `vmstat 1`'s `cs` column, syscalls/message from
      `perf stat -e 'syscalls:sys_enter_*'`, and p99 echo latency. Expected shape: RSS for the
      thread-per-connection baseline lands at **2.2–5 GB** for 55k connections against a **2 GB**
      `ApplicationGateway` heap (§1.5.8), while the three scalable variants sit in the low hundreds of
      MB; the ET server issues measurably fewer `epoll_wait` calls per message than LT.
      `[CALC]` `[NUM]`
4.2.7 **Diff vs the real one** (Netty's `EpollEventLoop`, the JDK's `EPollSelectorImpl`): a native
      transport that avoids `ByteBuffer` copies with `EPOLLET` plus `Native.epollWait` timerfd
      integration, `SO_REUSEPORT` accept sharding across event loops, pooled and reference-counted
      `ByteBuf`, high/low write watermarks for backpressure, `EPOLLEXCLUSIVE` to avoid the
      thundering herd, per-loop task queues with a configurable I/O ratio, and `io_uring` as an
      alternative transport. `[TABLE]` `[X-REF 10]`

*(7 leaves)*

## §4.3 An `mmap` and page-fault experiment harness `[BUILD]`

4.3.1 **The harness.** `mmap(NULL, 4L*1024*1024*1024, PROT_READ|PROT_WRITE,
      MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)` for 4 GiB, then walk it at a 4096-byte stride while sampling
      `/proc/self/stat` fields **10 (`minflt`)** and **12 (`majflt`)** and `/proc/self/status`
      `VmSize`/`VmRSS`/`RssAnon`. The mapping must cost **0 bytes of RSS** at `mmap` time and exactly
      one minor fault per page touched — **1,048,576** faults for 4 GiB at 4 KiB. `[SYSCALL]`
      `[PROC]` `[CALC]`
4.3.2 **The four variants that isolate each mechanism.** (a) `MAP_ANONYMOUS` write-walk → minor
      faults, RSS climbs. (b) `MAP_POPULATE` → faults taken up front, `mmap` itself becomes slow.
      (c) `MAP_PRIVATE` over a 6 MB `DocumentVerification` TIFF, read-walked twice with
      `posix_fadvise(POSIX_FADV_DONTNEED)` and a `echo 3 > /proc/sys/vm/drop_caches` between runs →
      **major** faults on the cold pass, minor on the warm pass. (d) `MAP_HUGETLB` or
      `madvise(MADV_HUGEPAGE)` → fault count drops by **512×** (2 MiB / 4 KiB) and
      `/proc/self/smaps` shows a non-zero `AnonHugePages`. `[PROVE]` `[NUM]`
4.3.3 **The copy-on-write measurement.** Touch 1 GiB, `fork()`, have the child write one byte per page
      across the first 256 MiB, and read both tasks' `minflt` and `smaps_rollup` `Pss`. The child's
      minor-fault count must equal the pages it wrote (**65,536** at 4 KiB), and `Pss` must diverge
      from `Rss` by the shared remainder — the arithmetic behind §1.4.4. `[CALC]` `[PROC]`
4.3.4 **The `/proc/<pid>/smaps` reader.** A 60-line parser that groups the per-mapping records by
      `VmFlags`/pathname and sums `Rss`, `Pss`, `Anonymous`, `AnonHugePages`, `Swap`,
      `Private_Dirty`, `Shared_Clean` — then run it against a live `FundsLedger` JVM and reconstruct
      the §2.2 RSS decomposition (heap `[anon]`, metaspace, code cache, `1 MiB` thread stacks with
      their `PROT_NONE` guard pages, mapped JARs, `libjvm.so`, `[vdso]`, `[vvar]`). Cross-check the
      total against `VmRSS` and against `jcmd <pid> VM.native_memory summary`. `[PROC]` `[BUILD]`
4.3.5 **The Java side.** `FileChannel.map(MapMode.READ_ONLY, 0, size)` over a `BankDeposits`
      statement file versus `Files.readAllBytes` versus a `BufferedInputStream` walk — report wall
      time, `majflt` delta, and syscall count for each. Include the two Java-specific traps:
      `MappedByteBuffer` unmapping is **not deterministic** before `Arena`/`MemorySegment`
      (`java.lang.foreign`, `Arena.ofConfined()`), and `sun.nio.ch.maxCachedBufferSize` /
      `-XX:MaxDirectMemorySize` bound the direct-buffer path, not the mapped one. `[API]` `[TRAP]`
4.3.6 **The trap it proves and the number to quote.** A **major** fault against gp3 EBS costs
      ~**0.5–1 ms**; a minor fault costs ~**1–3 µs**; the ratio is ~**500×**. Thirty major faults
      inside one `ClientRestrictions` call consumes the whole **30 ms** p99 budget with zero
      application work — which is why `si`/`so` must read 0 and why `-XX:+AlwaysPreTouch` exists.
      `[NUM]` `[CALC]`

*(6 leaves)*

## §4.4 A false-sharing benchmark with JMH `[BUILD]`

4.4.1 **The benchmark skeleton.** JMH 1.37 with
      `@BenchmarkMode(Mode.Throughput) @OutputTimeUnit(SECONDS) @State(Scope.Benchmark)`,
      `@Fork(value = 3, jvmArgs = {"-Xmx2g", "-XX:+UseG1GC"})`, `@Threads(3)` to match the three
      `FundsLedger` partitions, 5 warmup + 10 measurement iterations. Four `@Benchmark` methods over
      the same workload: unpadded adjacent counters, manually padded counters, `@Contended`, and
      `LongAdder`. `[BUILD]` `[API]`
4.4.2 **The four subjects, exactly.** (a) `long[] c = new long[3]` incremented at `c[threadIdx]`.
      (b) `long[] c = new long[3 * 8]` incremented at `c[threadIdx * 8]` — one 64-byte line per
      counter, 168 bytes of padding total. (c) a class with
      `@jdk.internal.vm.annotation.Contended` fields, run **with `-XX:-RestrictContended`** and again
      **without it** to prove the annotation is silently ignored on application classes.
      (d) `java.util.concurrent.atomic.LongAdder`. `[API]` `[TRAP]` `[VERSION-TRAP]`
4.4.3 **Prove the layout rather than assuming it.** Print `ClassLayout.parseClass(Counters.class)
      .toPrintable()` with JOL 0.17 and show the 12-byte header, the JVM's field **reordering**, and
      the 8-byte alignment; read the line size from
      `/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size` (**64** on x86-64,
      **128** on Apple M-series) rather than hardcoding it. `[PROC]` `[SOURCE]`
4.4.4 **Attribute the loss to coherence, not to guesswork.** Run each variant under
      `perf stat -e cycles,instructions,cache-misses,cache-references,LLC-load-misses,
      mem_load_l3_hit_retired.xsnp_hitm` (or the `-e cpu/event=.../` equivalent for the host CPU
      family) and show `HITM` events collapsing to near zero once padded. Note that this requires
      `kernel.perf_event_paranoid` ≤ 1 and does not work under the default Docker seccomp profile.
      `[DIAG]` `[SYSCTL]`
4.4.5 **The numbers it must land on.** At `@Threads(3)`, unpadded throughput should be roughly
      **5–15×** below padded, matching the ~**40–100 ns** coherence round trip versus the ~**1 ns**
      L1 hit of §1.32.6. `LongAdder` should track padded at high contention and lose slightly at
      single-thread. Report ops/sec with JMH's ±99.9% CI, not a single number. `[NUM]` `[CALC]`
4.4.6 **The trap it proves.** The unpadded code is **correct** — no data race, no shared variable,
      passing every test — and an order of magnitude slower for reasons invisible in the source.
      Pin threads with `taskset -c 0,1,2` versus `taskset -c 0,8,16` on a NUMA box and show the
      penalty growing across sockets, tying §1.32.5 to §2.8. `[TRAP]` `[PROVE]`
4.4.7 **Diff vs the real one** (`LongAdder`/`Striped64`, Netty's `FastThreadLocal`, JCTools
      `MpscArrayQueue`): `Striped64`'s probe-based cell allocation and growth-on-collision policy,
      `@Contended` applied by the JDK where `-XX:-RestrictContended` does not apply, padding of
      producer and consumer indices in ring buffers, and the fact that all of them trade memory and
      read cost for write scalability. `[TABLE]` `[X-REF 05]`

*(7 leaves)*

## §4.5 A CPU-throttling reproducer in a cgroup v2 slice `[BUILD]`

4.5.1 **Build the slice by hand, no container runtime.** `mkdir /sys/fs/cgroup/quizstakes.slice`,
      `echo "+cpu +memory +pids" > /sys/fs/cgroup/cgroup.subtree_control`,
      `echo "40000 100000" > /sys/fs/cgroup/quizstakes.slice/cpu.max` (0.4 CPU),
      `echo $$ > /sys/fs/cgroup/quizstakes.slice/cgroup.procs`, then `exec java ...`. The systemd
      equivalent for comparison: `systemd-run --scope -p CPUQuota=40% -p MemoryMax=512M java ...`.
      `[SYSCTL]` `[BUILD]`
4.5.2 **The workload.** A `ClientRestrictions`-shaped loop: 400 requests/sec of a **2 ms** CPU-bound
      restriction evaluation (a `ConcurrentHashMap` lookup plus a small predicate chain over the
      restriction catalog), with per-request latency recorded into an HdrHistogram
      (`org.hdrhistogram:HdrHistogram:2.2.2`) — **not** a mean. Offered load is 0.8 CPU against a
      0.4-CPU quota, so throttling is guaranteed and predictable. `[BUILD]` `[CALC]`
4.5.3 **The measurement.** Sample `cpu.stat` every 100 ms and plot `nr_periods`, `nr_throttled`,
      `throttled_usec` (the exact field names, verified against
      `Documentation/admin-guide/cgroup-v2.rst`) alongside the latency histogram. Derive the
      **throttled fraction** = `nr_throttled / nr_periods` and the mean stall per throttled period
      = `throttled_usec / nr_throttled`. `[PROC]` `[CALC]`
4.5.4 **The number it must land on.** With a 100 ms period and a 40 ms quota, a request unlucky enough
      to exhaust the quota at the start of a period waits up to **60 ms** — twice the entire
      `ClientRestrictions` **30 ms** budget — while `top` inside the cgroup reports **40% CPU** and
      looks healthy. p99 must be dominated by a mode near 60 ms even though p50 stays at ~2 ms.
      `[NUM]` `[CALC]` `[TRAP]`
4.5.5 **The period sweep that produces the actual guidance.** Rerun at `"40000 100000"`,
      `"20000 50000"`, `"10000 25000"` and `"4000 10000"` — identical 0.4 CPU, shrinking period —
      and show p99 falling roughly with the period while `nr_throttled` rises. Then rerun at
      `"400000 100000"` (4 CPU) with the same load and show `nr_throttled` at **0**: the fix is
      headroom, and period tuning only redistributes the pain. Note that `cpu.max.burst` (default
      **0**) buys back a bounded amount of it. `[CALC]` `[SYSCTL]`
4.5.6 **The JVM half of the trap.** Print `Runtime.getRuntime().availableProcessors()` inside the
      slice at `cpu.max` values of `"400m"`-equivalents — `"40000 100000"` → **1**,
      `"150000 100000"` → **2** (`ceil(1.5)`, not 1.5) — and show the knock-on sizing of
      `ForkJoinPool.commonPool().getParallelism()`, `ParallelGCThreads` and
      `jdk.virtualThreadScheduler.parallelism`, plus the `-XX:ActiveProcessorCount` override.
      A JVM that thinks it has 1 CPU and a pool sized for 16 is the other half of the incident.
      `[API]` `[CALC]`
4.5.7 **Diff vs the real one** (Kubernetes CPU limits, `cgroup` driver in kubelet, EKS): `requests`
      mapping to `cpu.weight` and `limits` to `cpu.max`, the static `CPUManager` policy pinning
      guaranteed pods with `cpuset.cpus` instead of quota, `topologyManager` NUMA alignment,
      `cpu.max.burst` exposure, the `container_cpu_cfs_throttled_periods_total` cAdvisor metric that
      is the fleet-wide version of this harness, and the standing argument for setting CPU requests
      without limits on latency-critical services. `[TABLE]` `[X-REF 19]`

*(7 leaves)*

## §4.6 A cgroup OOM-kill reproducer that proves 137 is not an `OutOfMemoryError` `[BUILD]`

4.6.1 **The setup.** `echo 512M > /sys/fs/cgroup/quizstakes.slice/memory.max`,
      `echo 0 > /sys/fs/cgroup/quizstakes.slice/memory.swap.max` (so there is no swap escape hatch),
      then run a JVM with `-Xmx256m -XX:MaxMetaspaceSize=128m -XX:MaxDirectMemorySize=256m
      -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/quizstakes` — a configuration whose
      **sum of parts exceeds the limit** while every individual JVM bound is respected.
      `[SYSCTL]` `[BUILD]`
4.6.2 **Two deliberately different deaths from the same JVM.** Path A: allocate a retained
      `ArrayList<byte[]>` of on-heap `DocumentVerification` buffers until `-Xmx` is exhausted →
      `java.lang.OutOfMemoryError: Java heap space`, a stack trace in
      `/var/log/documentverification/application.log`, a written heap dump, shutdown hooks running,
      exit code **1**. Path B: allocate `ByteBuffer.allocateDirect(2 * 1024 * 1024)` for each 2 MB
      document, retained, so native memory grows outside the heap → the cgroup limit hits first,
      `SIGKILL`, **no stack trace, no heap dump, no hooks**, exit code **137**. `[PROVE]` `[TRAP]`
4.6.3 **The evidence trail for path B, read line by line.** `memory.events` must show `oom_kill 1`
      (and `max` incrementing before it); `memory.peak` must sit at the limit;
      `dmesg -T | grep -iE 'oom|killed process'` must show the
      `Memory cgroup out of memory: Killed process <pid> (java) total-vm:...kB, anon-rss:...kB,
      file-rss:...kB, shmem-rss:...kB, UID:... pgtables:...kB oom_score_adj:...` record; the
      kubelet-level view is `reason: OOMKilled` with `exitCode: 137`. Show that **`memory.max` is
      hit, not `memory.limit_in_bytes`** — the cgroup v1 name is not present on the box.
      `[DIAG]` `[PROC]` `[VERSION-TRAP]`
4.6.4 **The `memory.high` variant that fails differently.** Set `memory.high 448M` alongside
      `memory.max 512M` and rerun path B: the process is now **throttled under heavy reclaim**
      instead of killed, `memory.events` shows `high` climbing, `memory.pressure` `full avg10`
      goes double-digit, and latency degrades to the point where the service is useless while
      staying "up". Name this explicitly as the worse failure mode. `[SYSCTL]` `[TRAP]`
4.6.5 **The arithmetic that predicts the kill before you run it.** For the 512 MiB limit: heap 256 +
      metaspace ~90 (observed, not the max) + code cache ~50 (`-XX:ReservedCodeCacheSize`) + 200
      threads × 1 MiB **reserved** but ~48 KiB touched ≈ 10 + GC structures ~25 + direct buffers as
      allocated + glibc arena overhead (`MALLOC_ARENA_MAX`, default **8 × cores**) ≈ **440 MiB before
      a single direct buffer**. Cross-check every term against
      `jcmd <pid> VM.native_memory summary` with `-XX:NativeMemoryTracking=summary` and against
      `smaps_rollup`. Then show why `-XX:MaxRAMPercentage` defaulting to **25.0** wastes three
      quarters of a 4 GB container and why setting `-Xmx` = limit guarantees this incident.
      `[CALC]` `[NUM]`
4.6.6 **The `oom_score` half.** Read `/proc/<pid>/oom_score` and `oom_score_adj` for all three
      `FundsLedger` JVMs on a host, write `-500` into one, and show the global (non-cgroup) OOM
      killer's choice change — then note that `memory.oom.group 1` kills the **whole cgroup** rather
      than the fattest task, which is what you want for a pod and not what you want for a sidecar
      you were relying on to flush metrics. `[PROC]` `[SYSCTL]`
4.6.7 **Diff vs the real one** (`systemd-oomd`, kubelet eviction, `earlyoom`): PSI-driven action at
      `memory.pressure` thresholds *before* the kernel killer engages, `ManagedOOMSwap`/
      `ManagedOOMMemoryPressure` in `systemd.resource-control`, kubelet's `evictionHard`/`evictionSoft`
      signals and QoS-ordered eviction, pod-level versus container-level limits, and why
      user-space OOM management gives you a graceful `SIGTERM` where the kernel gives you `SIGKILL`.
      `[TABLE]` `[X-REF 19]`

*(7 leaves)*

## §4.7 A `/proc` parser: build your own `top` for a JVM `[BUILD]`

4.7.1 **The scope, stated as a contract.** A single-file Java 21 program,
      `ProcTop <pid> [intervalMs]`, using only `java.nio.file.Files.readString` — no JMX, no
      attach API, no native code — that prints a `top`-like screen every second for one JVM and its
      threads. It must work inside a container where `top` reads the **host's** `/proc/stat` and
      lies. `[BUILD]` `[API]`
4.7.2 **The exact fields it must parse.** `/proc/<pid>/stat`: field **3** `state`, **10** `minflt`,
      **12** `majflt`, **14** `utime`, **15** `stime`, **20** `num_threads`, **22** `starttime`,
      **23** `vsize`, **24** `rss` (in **pages**, multiply by `getconf PAGESIZE` = 4096), **42**
      `delayacct_blkio_ticks` — with the comm field's parenthesised, space-containing name handled by
      splitting on the **last** `)` rather than on whitespace, which is the bug in every naive
      parser. Divide tick fields by `sysconf(_SC_CLK_TCK)` = **100**. `[PROC]` `[SOURCE]` `[TRAP]`
4.7.3 **The other files it must read.** `/proc/<pid>/status` for `VmRSS`, `RssAnon`, `RssFile`,
      `VmSwap`, `Threads`, `voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`, `Seccomp`;
      `/proc/<pid>/io` for `read_bytes`/`write_bytes`; `/proc/<pid>/schedstat` for the three numbers
      whose **second** is run-queue wait time in ns; `/proc/<pid>/limits` for the authoritative
      `Max open files`; `ls /proc/<pid>/fd | wc -l` for current fd usage; and
      `/proc/<pid>/task/<tid>/{stat,comm,schedstat}` per thread. `[PROC]`
4.7.4 **The container-aware denominators, which is the whole point.** Read
      `/sys/fs/cgroup/cpu.max`, `cpu.stat`, `memory.current`, `memory.max`, `memory.peak`,
      `memory.events`, `pids.current`, `pids.max` and `cpu.pressure`/`memory.pressure`/`io.pressure`,
      and express CPU as a percentage of **quota**, not of host cores. Print both numbers side by
      side so the divergence is visible: 92% of quota can be 4% of the host. `[PROC]` `[CALC]`
4.7.5 **The thread-to-Java-thread join.** For the hottest TIDs by `utime + stime` delta, print
      `printf("%x", tid)` and match `nid=0x<hex>` against a `jcmd <pid> Thread.print` dump captured
      by the same tool, producing a single line per hot thread: TID, hex nid, Java thread name,
      `%cpu`, run-queue wait, voluntary/involuntary switch counts, and the top frame. This automates
      the §1.5.12 recipe. `[FLOW]` `[DIAG]`
4.7.6 **The numbers it must land on.** Against a live `FundsLedger` at the **13,600 writes/sec** peak,
      the tool must reconcile to within a few percent of: `top -H` per-thread `%CPU`,
      `pidstat -t -p <pid> 1`, `jcmd VM.native_memory summary` for RSS composition, and
      `cat /sys/fs/cgroup/cpu.stat`'s `usage_usec` delta. Any divergence larger than that is a bug in
      the parser, and the reconciliation is the exercise. `[CALC]` `[DIAG]`
4.7.7 **The trap it proves.** Inside a container with `cpu.max = "400000 100000"` on a 64-core host,
      `top` shows the JVM at 380% of 6400% and looks idle while it is at **95% of its quota and
      being throttled every period**. `free -h` inside the same container reports the host's 256 GiB
      against a 4 GiB `memory.max`. Neither tool is broken; both are reading the wrong file. The
      correct files are the eight cgroup interface files in 4.7.4. `[TRAP]` `[PROC]`
4.7.8 **Diff vs the real one** (`procps-ng` `top`, `htop`, `pidstat`, cAdvisor, JFR): terminfo-driven
      rendering and per-key state, `/proc` batch reads with a single `openat` per pass, cumulative vs
      delta accounting, hertz detection, cgroup namespace awareness, `CONFIG_TASK_DELAY_ACCT`
      integration, cAdvisor's per-container metric families
      (`container_cpu_cfs_throttled_seconds_total`, `container_memory_working_set_bytes`) and JFR's
      in-JVM `jdk.ThreadCPULoad`/`jdk.NativeMemoryUsage` events. `[TABLE]` `[X-REF 20]`

*(8 leaves)*

## §4.8 An `fsync` latency measurement tool `[BUILD]`

4.8.1 **The tool.** `FsyncBench <path> <recordBytes> <records> <mode>` where mode ∈
      {`buffered`, `fsync-per-record`, `fdatasync-per-record`, `fsync-per-1000`, `O_DSYNC`,
      `O_DIRECT`} — mirroring the `BankDeposits` **40,000-record** statement file (500,000 at month
      end) and `FundsLedger`'s **230 writes/sec sustained, 13,600/sec peak**. Record every individual
      sync into an HdrHistogram and report p50/p90/p99/p999/max, never a mean. `[BUILD]` `[CALC]`
4.8.2 **The exact syscall surface and the difference between the modes.** `write(2)` returning success
      means "in the page cache", nothing more. `fsync(fd)` flushes data **and** metadata;
      `fdatasync(fd)` skips metadata not needed to read the data back — per `man 2 open`, "the last
      modification timestamp is not needed to ensure that a read completes successfully, but the file
      length is", which is why `fdatasync` is cheaper only when the file is not growing. `O_SYNC` and
      `O_DSYNC` on `openat` make every `write` synchronous. `O_DIRECT` bypasses the page cache and
      "may impose alignment restrictions on the length and address of user-space buffers and the file
      offset" — get the logical block size from `ioctl(BLKSSZGET)` or `blockdev --getss`, and never
      mix `O_DIRECT` with buffered I/O on the same region. `[SYSCALL]` `[SOURCE]`
4.8.3 **The Java 21 mapping, stated precisely.** `FileChannel.force(boolean metaData)` → `fsync` when
      `true`, `fdatasync` when `false`; `FileOutputStream` + `FileDescriptor.sync()` → `fsync`;
      `StandardOpenOption.SYNC` → `O_SYNC` and `DSYNC` → `O_DSYNC`; `flush()` on a
      `BufferedOutputStream` reaches the **page cache only** and is not durability. There is **no
      `O_DIRECT` in the JDK** — that is the honest answer, and the workaround is
      `java.lang.foreign` with `Linker.nativeLinker()` or a JNI shim. `[API]` `[TRAP]`
4.8.4 **Confirm the syscalls actually issued.** `strace -f -e trace=write,fsync,fdatasync,openat -c`
      for a short run to get the count, then `bpftrace -e 'tracepoint:syscalls:sys_enter_fsync
      /pid == $1/ { @start[tid] = nsecs; } tracepoint:syscalls:sys_exit_fsync /@start[tid]/
      { @us = hist((nsecs - @start[tid]) / 1000); delete(@start[tid]); }'` for the production-safe
      histogram, plus `biolatency` and `biosnoop` from `bcc` for the device-level view.
      `[DIAG]` `[BUILD]`
4.8.5 **The numbers it must land on, and the derived capacity.** Order-of-magnitude targets: local
      NVMe `fsync` p50 ~**25–100 µs**; EBS gp3 ~**0.5–2 ms**; a spinning disk or an
      IOPS-exhausted volume tens of ms. Therefore **one `fsync` per record at 1 ms caps you at
      ~1,000 records/sec**, which is under the 13,600/sec peak by an order of magnitude and takes
      **40 seconds** for the 40k-record file; batching to one `fsync` per 1,000 records takes
      **40 ms** of sync time. Report the measured ratio, and show the `writeback` side with
      `/proc/meminfo`'s `Dirty`/`Writeback` and `vm.dirty_ratio` (**20**),
      `vm.dirty_background_ratio` (**10**), `vm.dirty_expire_centisecs` (**3000**).
      `[CALC]` `[NUM]` `[SYSCTL]`
4.8.6 **The trap it proves — twice.** (a) An `fsync` **error is reported once**: a failed writeback
      marks the error, the next `fsync` returns it, and a subsequent `fsync` returns success on data
      that was never written. `close()` may swallow it entirely. Reproduce with `dmsetup` error
      injection or a full filesystem, and note that Linux since 4.13 keeps per-file-description error
      tracking. (b) `fsync` on a file does **not** sync the directory entry — after creating a new
      payout file you must `fsync` the **parent directory fd** or the file can vanish on power loss.
      Both are `[TRAP]` `[RESEARCH]`, to be re-verified against `man 2 fsync` and the LWN
      writeback-error articles before writing. `[TRAP]` `[INCIDENT]`
4.8.7 **Diff vs the real one** (PostgreSQL's WAL, `fio`, RocksDB, Kafka): group commit amortising one
      `fsync` across many transactions, `wal_sync_method` selection between `fdatasync`/`fsync`/
      `open_datasync`/`open_sync`, PostgreSQL's post-2018 `data_sync_retry`/panic-on-fsync-failure
      response to the error-reporting trap, `fio`'s `--ioengine=libaio|io_uring --direct=1
      --fsync=1` matrix for device characterisation, Kafka's decision to rely on replication and the
      page cache instead of per-record `fsync`, and the durability-vs-latency contract each one
      publishes. `[TABLE]` `[X-REF 09]`

*(7 leaves)*

## §4.9 A graceful-shutdown harness: PID 1, `SIGTERM`, in-flight requests `[BUILD]`

4.9.1 **The subject under test.** A Spring Boot 3.5.x `ApplicationGateway`-shaped app with one
      endpoint that sleeps a configurable 0–20 s (standing in for the card-PSP p99 of **11 s**),
      `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=25s`, Actuator
      `/actuator/health/readiness` and `/actuator/health/liveness`, and a load generator holding
      **200 in-flight requests** at the moment of the signal. Success is measured as
      **zero non-2xx responses** among requests accepted before the signal. `[BUILD]` `[API]`
4.9.2 **The four PID 1 variants, run identically.** (a) `CMD java -jar app.jar` — **shell form**, so
      `/bin/sh` is PID 1, does not forward `SIGTERM`, and the JVM is `SIGKILL`ed after the full grace
      period on **every deploy**. (b) `CMD ["java","-jar","app.jar"]` — exec form, JVM is PID 1 and
      receives the signal. (c) an entrypoint script ending in `exec java -jar app.jar`. (d)
      `ENTRYPOINT ["/sbin/tini","--"]` in front of the JVM, which also **reaps orphans** — the JVM as
      PID 1 does not. Prove which is which with `docker exec <c> ps -eo pid,ppid,cmd` showing PID 1's
      identity, and instrument the JVM's own view with a `SIGTERM` handler that logs
      `System.nanoTime()`. `[TRAP]` `[DIAG]`
4.9.3 **The correct ordering, made falsifiable.** Fail readiness → wait for the LB/endpoint controller
      to observe it → stop accepting new connections → drain in-flight to a deadline → flush the
      metrics registry and the log appenders → close the JDBC pool and the HTTP client pools → commit
      or abort open transactions → release distributed locks → exit **0**. Then ship the deliberately
      wrong version that closes the connection pool **first**, and show all 200 in-flight requests
      failing with `CannotGetJdbcConnectionException`. `[FLOW]` `[PROVE]`
4.9.4 **The Kubernetes race, reproduced.** `terminationGracePeriodSeconds: 40`, no `preStop` hook →
      measure the window in which the Service still routes to a pod that has already begun shutting
      down, and count the 502s. Add `lifecycle.preStop.exec.command: ["sleep","8"]` and show the
      count go to zero. Note that `SIGTERM` and endpoint removal are **concurrent**, not sequential,
      and that the correct grace period is `preStop sleep + drain deadline + flush margin` — for the
      11 s PSP p99 that is **40 s**, not the 30 s default. `[INCIDENT]` `[CALC]` `[X-REF 19]`
4.9.5 **The Java-level mechanics and their limits.** `Runtime.addShutdownHook` ordering is
      **unspecified** across hooks; hooks run concurrently; `Runtime.halt()` and `System.exit()` from
      inside a hook deadlock; hooks do **not** run on `SIGKILL`, on `Runtime.halt`, or on a JVM crash.
      Show `Runtime.getRuntime().addShutdownHook` versus Spring's `SmartLifecycle`
      `getPhase()`/`stop(Runnable)` versus `@PreDestroy` ordering, and demonstrate the
      `ExecutorService.shutdown()` → `awaitTermination(20, SECONDS)` → `shutdownNow()` →
      `awaitTermination` ladder, including the fact that `shutdownNow` only **interrupts** and a
      thread ignoring interrupts survives it. `[API]` `[TRAP]`
4.9.6 **The `BankWithdrawal` drain-before-terminate case.** A `PaymentRun` mid-file (**1.8k records,
      4 files/day**, operator-gated, irreversible past a point) must not be interrupted: implement a
      shutdown path that refuses to exit until the current file is either fully submitted or fully
      rolled back, backed by a resumable checkpoint, and show what happens at the 40 s `SIGKILL`
      boundary without it — a half-submitted payout file, which is the only genuinely unrecoverable
      failure in this whole part. `[INCIDENT]` `[BUILD]`
4.9.7 **The measurement table it must produce.** Rows: the four PID 1 variants × {no preStop,
      8 s preStop} × {correct order, pool-closed-first}. Columns: time from `docker stop`/pod delete
      to signal receipt in the JVM, time to exit, exit code (**0** / **143** / **137**), non-2xx
      count, requests lost, and whether shutdown hooks ran. Shell-form PID 1 must show signal receipt
      at **never** and exit code **137** in every row. `[TABLE]` `[NUM]`
4.9.8 **Diff vs the real one** (systemd, `tini`/`dumb-init`, containerd/runc, Kubernetes): systemd's
      `KillMode=control-group|mixed|process`, `KillSignal`, `TimeoutStopSec`,
      `FinalKillSignal=SIGQUIT` and `SendSIGKILL`; `tini`'s `-g` process-group signalling and
      subreaper mode; runc's `terminationGracePeriod` plumbing and the cgroup freezer; kubelet's
      pod-termination state machine and `terminationGracePeriodOverride` for eviction; and ALB/NLB
      **deregistration delay** (default 300 s) as the piece that must be shorter than nothing else
      breaks. `[TABLE]` `[X-REF 19]`

*(8 leaves)*

## §4.10 A `bpftrace` and `perf` diagnostic kit for a JVM service `[BUILD]`

4.10.1 **The prerequisites, stated first because they are where this fails.**
       `kernel.perf_event_paranoid` (default **2** — "disallow kernel profiling by users without
       `CAP_PERFMON`") must be ≤ 1 for user profiling and ≤ -1 for full kernel access;
       `kernel.kptr_restrict=0` for kernel symbols; `CAP_BPF`/`CAP_PERFMON` (or
       `--privileged`, or `securityContext.capabilities.add: [SYS_ADMIN, BPF, PERFMON]`) in a pod;
       and **the default Docker seccomp profile blocks `perf_event_open` and `bpf` outright**, which
       is why the kit runs on the **host** against a container's pid, not inside it. Verify with
       `bpftrace -l 'tracepoint:syscalls:sys_enter_read'` before believing anything else.
       `[SYSCTL]` `[TRAP]` `[RESEARCH]`
4.10.2 **The nine one-liners, each with the symptom it answers.** Syscall census:
       `bpftrace -e 'tracepoint:raw_syscalls:sys_enter /pid == $1/ { @[probe] = count(); }'`.
       Run-queue latency: `runqlat -p <pid> 10 1` (or the `sched:sched_wakeup`→`sched_switch` delta),
       answering "p99 spiked at 40% CPU". Off-CPU time by stack: `offcputime -p <pid> -K 30`,
       answering "where is the wall time going". Block I/O latency: `biolatency -D 10 1`. Per-file
       I/O: `biosnoop`, `filetop`, `fileslower 10`. Page faults:
       `bpftrace -e 'software:major-faults:1 /pid == $1/ { @[ustack] = count(); }'`. Futex wait time:
       `bpftrace -e 'tracepoint:syscalls:sys_enter_futex /pid == $1/ { @[args->op] = count(); }'`.
       TCP retransmits: `tcpretrans`. New processes: `execsnoop -T`. `[BUILD]` `[DIAG]`
4.10.3 **The `perf` half, with the JVM-specific flag that makes it usable.** `perf stat -p <pid> -e
       cycles,instructions,cache-misses,dTLB-load-misses,context-switches,cpu-migrations,
       page-faults -- sleep 30` for the IPC/TLB picture; `perf record -F 99 -g -p <pid> -- sleep 30`
       then `perf report --stdio`; and the mandatory
       **`-XX:+PreserveFramePointer`** (JDK 8u60+) plus `-XX:+UnlockDiagnosticVMOptions
       -XX:+DebugNonSafepoints` so Java frames resolve at all, with `perf-map-agent` or
       `perf inject --jit` for the JIT symbol map. Without `PreserveFramePointer` every Java frame is
       `[unknown]` and the profile is worthless — state that as the first thing to check.
       `[API]` `[TRAP]` `[VERSION-TRAP]`
4.10.4 **async-profiler as the honest default for a JVM.** `asprof -e cpu -d 30 -f
       /tmp/fundsledger.html <pid>` and `-e wall`, `-e alloc`, `-e lock`, `-e cache-misses`,
       `-e itimer` as the fallback when `perf_event_open` is blocked. It resolves Java, JNI and kernel
       frames in one flame graph, uses `AsyncGetCallTrace` so it is not safepoint-biased, and needs
       only `perf_event_paranoid ≤ 1` for its `cpu` mode. State plainly when to use it over `perf`
       (Java-dominated stacks) and when not to (kernel-side or off-CPU questions, where
       `offcputime` wins). `[API]` `[DIAG]`
4.10.5 **The triage script the kit actually is.** One shell file, `boxtriage.sh <pid>`, that captures
       in order and writes a timestamped tarball: `uptime`, `nproc`,
       `cat /proc/pressure/{cpu,memory,io}`, `vmstat 1 5`, `mpstat -P ALL 1 3`, `free -h`,
       `cat /sys/fs/cgroup/<path>/{cpu.max,cpu.stat,memory.current,memory.max,memory.events}`,
       `iostat -xz 1 3`, `ss -s`, `cat /proc/<pid>/{status,limits,io,schedstat}`,
       `ls /proc/<pid>/fd | wc -l`, `ps -eLo pid,tid,stat,wchan:30,pcpu,comm -p <pid>`,
       `jcmd <pid> Thread.print`, `jcmd <pid> GC.heap_info`,
       `jcmd <pid> VM.native_memory summary`, `dmesg -T | tail -100`, and
       `journalctl -u <unit> --since '15 min ago'`. Evidence before intervention — because the
       diagnosis dies with the process. `[FLOW]` `[BUILD]`
4.10.6 **The overhead budget, measured rather than asserted.** Run the `FundsLedger` load at
       **13,600 writes/sec** and measure throughput and p99 with: nothing attached, `perf record -F
       99 -g`, `async-profiler -e cpu`, `bpftrace` counting one tracepoint, `offcputime`, and
       `strace -c -f`. `strace` must show the **10–100×** penalty of §1.3.9 and be marked
       never-in-production; the rest should sit in the low single-digit percent. Producing this table
       is what earns the right to run any of it on a money path. `[TABLE]` `[CALC]`
4.10.7 **The trap it proves.** The tool you reach for first is usually the one whose output you can
       read least well. Include one worked misread of each: a `perf report` dominated by
       `[unknown]` mistaken for native code (missing `PreserveFramePointer`), an `offcputime` flame
       graph dominated by `epoll_wait` mistaken for a stall (that is a healthy idle event loop),
       `biolatency` p99 in the tens of ms mistaken for a bad disk (it is `nr_throttled` on
       `io.max`), and a `runqlat` histogram read as a CPU shortage when the box is at 38% (it is
       `cpu.max` throttling). `[TRAP]` `[DIAG]`
4.10.8 **Diff vs the real one** (`bcc`/`libbpf-tools`, JFR, Pyroscope/Parca, `perf` in a fleet):
       CO-RE and BTF so a tool built once runs on every kernel, `libbpf-tools`' C rewrites replacing
       the Python `bcc` tools' compile-at-runtime cost, JFR's in-process always-on model
       (`-XX:StartFlightRecording=settings=profile`) with a ~1–2% budget and `jdk.*` event types
       that no eBPF tool can see, continuous-profiling backends that aggregate flame graphs across
       the fleet with a 10-second sample interval, and the fact that none of them replaces
       `/proc/<pid>/schedstat` for a single question about a single thread. `[TABLE]` `[X-REF 20]`

*(8 leaves)*

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question bank

Every question is answerable from a named section of this file. If you cannot name the section, you
do not yet know the answer.

**Band A — the screen (fluency; 60 seconds each).**

5.1.1 What is the difference between a process and a thread, on Linux specifically? (§1.4.1, §1.5.1,
      §1.5.6 — one `clone()` with different flags, and the shared/private table.)
5.1.2 What does a context switch cost, and what makes a process switch worse than a thread switch?
      (§1.9.3, §1.9.4 — **1–5 µs** direct, plus cache and TLB pollution, plus `CR3` reload.)
5.1.3 What happens when you call `malloc(64)`? And `malloc(1 GiB)`? (§1.14.2–§1.14.5 — arena free
      list, then `brk`, then `mmap` past `M_MMAP_THRESHOLD` = **128 KiB**, and no physical page
      until you write.)
5.1.4 What is the difference between virtual memory and resident memory, and which one do you look
      at for a JVM? (§1.10.1, §1.11.3 — `VmSize` vs `VmRSS`; `VIRT` is meaningless for a JVM.)
5.1.5 What is a page fault? What is the difference between a minor and a major one, and what does
      each cost? (§1.12.2 — ~**1–3 µs** vs ~**0.5–1 ms** on EBS, a **500×** ratio.)
5.1.6 What does `kill -9` skip that `kill -15` does not? (§1.23.4, §2.23.2 — shutdown hooks,
      in-flight completion, buffer and log flush, pool close, lock release, transaction resolution;
      `SIGKILL` is not deliverable to userspace at all.)
5.1.7 What is a `D`-state process, and why does `kill -9` not help? (§1.6.3, §1.6.4 — uninterruptible
      sleep in a kernel path that cannot unwind; `TASK_KILLABLE` is the partial exception.)
5.1.8 What does `load average 8` mean on a 4-core box? (§1.6.6 — 2× oversubscribed *if* it is all
      runnable; load counts `R` **plus** `D`, has no denominator, and PSI is the correct signal.)
5.1.9 What is a file descriptor, and what can be behind one? (§1.16.1 — files, sockets, pipes,
      `epoll` instances, `eventfd`, `timerfd`, `inotify` watches, `signalfd`, `pidfd`, memfd.)
5.1.10 Why is `free` showing 300 MB on a healthy 16 GB box? (§1.13.2 — page cache by design; read the
       **`available`** column, not `free`.)
5.1.11 What is the difference between the Linux OOM killer and a `java.lang.OutOfMemoryError`?
       (§2.11.1 — kernel vs JVM, cgroup/host vs heap, `SIGKILL`/**137**/`dmesg` vs an `Error` with a
       stack trace and a heap dump.)
5.1.12 What does `kill -3` on a JVM do, and why is it worth memorising? (§2.22.3 — full thread dump
       to stdout, no `jstack`, no attach, works when the JVM will not accept a connection.)

**Band B — L5 mechanics (name the mechanism, the file, and the number).**

5.1.13 Walk me through a syscall from the `syscall` instruction to the return. (§1.3.1–§1.3.3, §3.3 —
       `rax`/`rdi`/`rsi`/`rdx`/`r10`/`r8`/`r9`, `MSR_LSTAR`, `entry_SYSCALL_64`, `-errno` in `rax`.)
5.1.14 What does a syscall cost, and what changed in 2018? (§1.3.4 — **50–100 ns** unmitigated vs
       **250–600 ns** with KPTI/retpoline/IBRS, against ~1–2 ns for a function call.)
5.1.15 Why is `System.nanoTime()` cheap enough to call per request? (§1.3.5, §1.27.5 — the vDSO,
       ~**20–25 ns**, no ring transition; `[vdso]`/`[vvar]` in `/proc/<pid>/maps`.)
5.1.16 What is the Linux scheduler, and what is `vruntime` for? (§1.7 — and the trap: **EEVDF since
       6.6**, `lag` and virtual deadlines, `base_slice_ns` = **750,000 ns**, not
       `sched_latency_ns`.) `[VERSION-TRAP]`
5.1.17 How does a virtual address become a physical one? (§1.10.4, §3.4 — the 4-level walk
       PGD→PUD→PMD→PTE, 9 bits each, 12-bit offset, `CR3`, the TLB, and the **4** memory accesses a
       miss costs.)
5.1.18 What is in a process's address space? (§1.11.1 — text, data, bss, heap, per-thread stacks with
       guard pages, `mmap` regions, `[vdso]`/`[vvar]`/`[vsyscall]`; read it from
       `/proc/<pid>/maps` and `smaps`.)
5.1.19 What is the page cache, what is a dirty page, and when is it written back? (§1.13 —
       `vm.dirty_ratio` **20**, `vm.dirty_background_ratio` **10**, `vm.dirty_expire_centisecs`
       **3000**, `[kworker/*flush*]`.)
5.1.20 What does `write()` returning success guarantee? (§1.18.3 — that it is in the page cache.
       Nothing about the disk. Durability requires `fsync`/`fdatasync`/`O_DSYNC`.)
5.1.21 What is the difference between `fsync` and `fdatasync`, and when does it matter? (§1.18.5 —
       metadata; `fdatasync` still syncs the file length, so a growing file gains little.)
5.1.22 What are the four I/O models, and which one is `epoll`? (§1.21 — blocking, non-blocking
       polling, **readiness multiplexing** (`epoll`), and true async completion (`io_uring`).)
5.1.23 How does `epoll` beat `select`? (§1.22.4–§1.22.7 — a **persistent** kernel-side interest set
       in an RB-tree plus a ready list populated by callback, so `epoll_wait` is O(ready) not O(n);
       and `select`'s `FD_SETSIZE` = **1024** hard cap.)
5.1.24 Level-triggered vs edge-triggered — what breaks if you get it wrong? (§1.22.9 — ET without a
       read-until-`EAGAIN` loop silently stalls a connection forever.)
5.1.25 What is a signal, and what can you legally do inside a handler? (§1.23.2, §1.23.6 —
       async-signal-safe functions only, `write(2)` yes and `printf` no, `volatile sig_atomic_t`,
       `sigaction` not `signal`.)
5.1.26 Which signals cannot be caught, and which one gives you a thread dump? (§1.23.3 — `SIGKILL`
       (9) and `SIGSTOP` (19) cannot; `SIGQUIT` (3) dumps threads on a JVM.)
5.1.27 What is `futex` and why does it appear in every Java `strace`? (§1.3.7, §1.24.9, §3.13 —
       uncontended locks stay in userspace on a CAS; contention calls `FUTEX_WAIT`/`FUTEX_WAKE`.
       Dominant `futex` means **lock contention**, not I/O.)
5.1.28 What are the three fd tables and why does the distinction matter? (§1.16.2 — per-process fd
       table → shared open-file description (which holds the **offset** and status flags) → inode.
       This is why `dup2` shares an offset and `open` twice does not.)
5.1.29 Where does the fd limit come from, and which value applies? (§1.16.5–§1.16.7 — soft/hard
       `RLIMIT_NOFILE`, systemd's **1024** soft / **524288** hard, `fs.nr_open` **1048576**,
       `fs.file-max`; the authoritative answer is `/proc/<pid>/limits`.) `[VERSION-TRAP]`
5.1.30 What is an inode, and how can `df` be full while there are free bytes? (§1.17.2, §1.19.7 —
       inode exhaustion; `df -i`.)
5.1.31 Why do `df` and `du` disagree? (§1.19.8 — a deleted file still held open; blocks are not freed
       until the last fd closes. `lsof +L1`.)
5.1.32 What does `%util` at 100% actually mean on an NVMe device? (§1.20.6 — time with **at least
       one** request in flight, which for a multi-queue device says nothing about saturation;
       `await` and `aqu-sz` are the useful columns.) `[TRAP]`
5.1.33 What does `Runtime.availableProcessors()` return under `cpu.max = "400000 100000"`? (§2.12.3 —
       **4**. Under `"150000 100000"` it is **2**, because it is `ceil(quota/period)`, not 1.5.)
       `[CALC]`
5.1.34 Why does an unflagged JVM in a 4 GB container take a 1 GB heap? (§2.12.2 —
       `UseContainerSupport` is on by default and `MaxRAMPercentage` defaults to **25.0**.)
5.1.35 What is in a JVM's RSS besides the heap? (§2.2.4, §2.3 — metaspace, code cache, GC structures,
       thread stacks (1 MiB reserved each), direct and mapped buffers, the class-space, glibc arenas,
       JIT compiler arenas. Enumerate it with `-XX:NativeMemoryTracking=summary`.)
5.1.36 How do you size a thread pool from the core count? (§2.4 — Little's Law and
       `N = cores × target × (1 + wait/service)`; and the answer changes entirely under `cpu.max`.)
5.1.37 What does the kernel see when you run a million virtual threads? (§1.5.9, §2.5 — the carrier
       `ForkJoinPool`, `availableProcessors()` platform threads, and nothing else.)
5.1.38 What is THP, and why might it be the cause of your p99? (§2.7 — `khugepaged`, direct
       compaction stalls, `/sys/kernel/mm/transparent_hugepage/enabled` being `always` on RHEL-family
       and `madvise` on Debian-family. Read the file; do not assume.) `[VERSION-TRAP]`
5.1.39 What are cgroups v2, and which files control CPU and memory? (§2.9 — `cpu.max`, `cpu.weight`
       (**100**, 1–10000), `cpu.stat`, `memory.max`, `memory.high`, `memory.current`,
       `memory.events`, `pids.max`, `io.max`. The v1 names are not on your box.) `[VERSION-TRAP]`
5.1.40 What is a namespace, and what makes a container a container? (§2.13, §2.14 — `clone()` with
       `CLONE_NEW*` flags plus a cgroup plus a seccomp filter plus overlayfs. Nothing more exotic.)

**Band C — L6 depth (mechanism plus judgement plus a scale argument).**

5.1.41 EEVDF replaced CFS in 6.6. What actually changed, and what would you now say differently in a
       latency-tuning conversation? (§1.7.7, §3.2.5 — eligibility from `lag`, virtual deadlines from
       a requested slice, `base_slice_ns`, and the death of `sched_latency_ns / nr_running`
       arithmetic.) `[VERSION-TRAP]`
5.1.42 Why is CPU **limit** on a latency-sensitive service usually the wrong control, and what do you
       set instead? (§2.10.5–§2.10.7 — throttling injects up-to-a-full-period stalls; set requests
       (`cpu.weight`) for the scheduling contract, keep headroom, and use `cpu.max.burst` or no
       limit at all.)
5.1.43 You have three `FundsLedger` instances at 12 GB on one host. Argue for or against swap.
       (§2.20 — GC traverses the whole heap, so every collection faults swapped pages back;
       `vm.swappiness` range is **0–200** since 5.8, default **60**; and Kubernetes `NodeSwap` is
       beta, so "Kubernetes forbids swap" is stale.) `[VERSION-TRAP]`
5.1.44 How would you decide between `epoll`, `io_uring` and virtual threads for a new service?
       (§2.17, §2.18, §2.5 — and the deployment constraint that Docker's and Kubernetes' default
       seccomp profiles **block `io_uring_setup`**, so "just use io_uring" is not advice.)
5.1.45 NUMA: when does it matter, and what would you measure before changing anything? (§2.8 —
       `numactl --hardware`, `numastat -p <pid>`, remote-access latency ratios, `-XX:+UseNUMA`, and
       the interleave-vs-bind decision for a 12 GB heap on a two-socket box.)
5.1.46 Design the memory configuration for the `FundsLedger` pod, given a 12 GB heap and a **59:1**
       peak-to-sustained write ratio. (§2.2, §2.11, §4.6.5 — the full RSS budget, why you cannot
       provision for the average, `MaxRAMPercentage`, `memory.high` vs `memory.max`, and the
       `oom.group` decision.)
5.1.47 Utilisation: why does p99 collapse at 70–80% CPU rather than at 100%? (§2.26 — the M/M/1
       queueing curve `W = 1/(µ−λ)`, Little's Law, and why a 30 ms budget forces you to run at 40%.)
       `[CALC]`
5.1.48 How do you get a fleet-wide answer to "which service is being CPU-throttled" without SSHing to
       anything? (§2.10.8, §2.25 — `container_cpu_cfs_throttled_periods_total`, PSI per cgroup, and
       the alert threshold you would actually set.) `[X-REF 20]`
5.1.49 Your platform team wants to standardise `terminationGracePeriodSeconds` at 30 s fleet-wide.
       Respond. (§2.23.5 — it must be `preStop + drain deadline + flush margin`; with an 11 s PSP
       p99 the correct number is **40 s**, and `BankWithdrawal`'s `PaymentRun` needs a different
       contract entirely.)
5.1.50 When would you reach for eBPF in production, and what is the risk? (§3.17 — verifier-bounded
       programs, CO-RE/BTF portability, the `perf_event_paranoid` and seccomp prerequisites, the
       overhead budget of §4.10.6, and the fact that a bad `bpftrace` map can still cost you memory.)
5.1.51 Argue the case for and against `-XX:+AlwaysPreTouch` on a 12 GB heap. (§1.12.8, §2.6 —
       startup cost of 3.1M minor faults vs a flat steady state; the interaction with THP; and the
       interaction with `vm.overcommit_memory=2`.)
5.1.52 Two services, one host, one is latency-critical and one is a nightly batch. Specify the
       isolation. (§1.1.10, §2.9, §2.10 — `cpu.weight` vs `cpu.max`, `io.max`, `memory.high`,
       anti-affinity, and why `cpu.weight` alone starved `ClientRestrictions` in the opening
       incident.)
5.1.53 What is the honest limit of what you can learn from userspace, and when do you escalate to a
       kernel engineer? (§1.1.11, §3.19 — and the evidence pack you hand over.)

**Band D — debug the incident (you have SSH; talk out loud).**

5.1.54 `DocumentVerification` pods restart every few hours with **exit 137**, no Java stack trace, and
       the heap graph looks flat. Diagnose. (§2.11, §4.6 — `memory.events` `oom_kill`, `dmesg`,
       native/direct buffers outside `-Xmx`, `smaps_rollup` vs NMT.)
5.1.55 `ClientRestrictions` p99 goes from 11 ms to 340 ms with no deploy and CPU at **38%**.
       Diagnose. (§1.1.10, §2.10, §2.25 — `/proc/pressure/cpu` `some avg10`, `cpu.stat`
       `nr_throttled`, `/proc/<pid>/schedstat` field 2, `runqlat`.)
5.1.56 `BankDeposits` hangs at 06:05 mid-ingestion, will not terminate, `kill -9` does nothing, load
       is 42 with 4% CPU. Diagnose. (§1.6.12 — `D` state, `wchan = io_schedule`,
       `/proc/pressure/io` `full avg10`, exhausted gp3 IOPS, one `fsync` per record.)
5.1.57 `ApplicationGateway` starts throwing `Too many open files` at 55k concurrent sessions.
       Distinguish "limit too low" from "fd leak" in under two minutes. (§2.16 — `/proc/<pid>/limits`
       vs a monotonically rising `ls /proc/<pid>/fd | wc -l`, and `lsof -p` grouped by type.)
5.1.58 A host accumulates 18,000 zombies over nine days and process creation starts failing with
       `EAGAIN`. Diagnose. (§1.4.14 — a `ProcessBuilder` whose `waitFor` was never called; the bug is
       in the parent and killing the children does nothing.)
5.1.59 `InternalPlatforms` throws `OutOfMemoryError: unable to create native thread` with a 4 GB heap
       40% used. Name the three candidate limits and how you tell them apart. (§1.5.13 —
       `threads-max`, `RLIMIT_NPROC` (`ulimit -u`, **per uid**), cgroup `pids.max`.)
5.1.60 `FundsLedger` p99 goes to seconds during the settlement burst and `vmstat` shows non-zero
       `si`/`so`. Explain the mechanism, not just the fix. (§1.15, §2.20 — reclaim, `kswapd`, GC's
       whole-heap traversal faulting swapped pages back.)
5.1.61 Throughput drops 14% after a kernel upgrade, same code, same hardware, unchanged IPC.
       Diagnose. (§1.2.12 — `dTLB-load-misses` up, `/sys/devices/system/cpu/vulnerabilities/*`,
       KPTI + retpoline against 13,600 syscall-heavy writes/sec; the fix is fewer syscalls.)
5.1.62 A service shows 45% `%sy` and low `%us` while processing 6 MB uploads. Diagnose. (§1.3.14 —
       millions of 1-byte `read`s through an unbuffered stream; `perf trace -s`; 6,000,000 syscalls
       become **1,464** at an 8 KiB buffer.) `[CALC]`
5.1.63 Every deploy loses in-flight requests and the pod always takes the full grace period.
       Diagnose. (§2.23, §4.9.2 — shell-form `CMD`, `/bin/sh` as PID 1, `SIGTERM` never forwarded,
       exit **137** every time.)
5.1.64 A thread dump shows 200 `RUNNABLE` threads and the box is at 6% `%us`. What is happening?
       (§1.6.9, §1.6.10 — Java reports a socket read as `RUNNABLE`; they are all in `recvfrom`.)
5.1.65 Disk full with 40% of bytes free, and after deleting the biggest log file nothing is reclaimed.
       Diagnose. (§1.19.7, §1.19.8 — inodes (`df -i`), then a deleted-but-open file (`lsof +L1`) from
       a rotation that never signalled the writer to reopen.)
5.1.66 A batch job on a shared host makes `ClientRestrictions` slow but the batch job's own metrics
       look fine. Trace the resource. (§1.13, §2.21 — page-cache eviction and `io.max` contention;
       `/proc/pressure/io` per cgroup, `biosnoop`, `filetop`.)
5.1.67 A JVM's `perf report` is entirely `[unknown]`. What went wrong? (§4.10.3 — missing
       `-XX:+PreserveFramePointer` and no JIT symbol map.)
5.1.68 One core is pegged at 100% and 15 are idle. Find the Java thread in four commands. (§1.5.12 —
       `top -H -p <pid>` → `printf '%x\n' <tid>` → `jcmd <pid> Thread.print` → match `nid=0x...`.)
5.1.69 Where did my heap dump go? (§2.11.6 — `SIGKILL` writes no dump; `-XX:HeapDumpPath` inside a
       container's ephemeral filesystem dies with the container; a 12 GB heap needs 12 GB of
       writable volume and tens of seconds it does not have inside the grace period. Mount a volume,
       or accept that you will never get one.) `[TRAP]`

**Band E — "what does this command output tell you" (read it, do not summarise it).**

5.1.70 A `top` header with `load average: 8.42, 7.90, 6.11` and `61.2 wa`, `12.3 id`, `22.1 us`.
       (§1.30.3 — I/O-bound, rising, and the GC logs are not where to look.)
5.1.71 `/proc/pressure/cpu` reading `some avg10=62.00 avg60=41.10 avg300=12.00 total=91847362` next
       to `top` showing idle CPU. (§1.6.7 — contended, not busy; `total` is in **microseconds**.)
5.1.72 `cat /sys/fs/cgroup/cpu.stat` with `nr_periods 5981`, `nr_throttled 4412`,
       `throttled_usec 173829411`. (§2.10.4 — 74% of periods throttled, mean stall ≈ **39 ms** per
       throttled period, against a 30 ms budget.) `[CALC]`
5.1.73 A `dmesg` `Memory cgroup out of memory: Killed process ... anon-rss:... pgtables:...
       oom_score_adj:...` record, read field by field. (§2.11.3, §3.7.)
5.1.74 `vmstat 1` with `si 412 so 1088`, `cs 84000`, `wa 31`. (§1.15, §1.9.7 — active swapping plus a
       switch storm; two independent problems in one line.)
5.1.75 `iostat -xz 1` with `%util 99.8`, `await 42.1`, `r/s 210`, `aqu-sz 8.9` on an NVMe device.
       (§1.20.6 — `await` and `aqu-sz` are the signal; `%util` is not, and 210 IOPS at 42 ms on
       NVMe means a throttle, not a device limit.)
5.1.76 `ps -eo pid,stat,wchan:30,cmd` showing several tasks in `io_schedule` and one in
       `folio_wait_bit_common`. (§1.6.5 — block I/O submission vs waiting on a page under
       writeback.)
5.1.77 `free -h` inside a container showing `total 251Gi` next to `memory.max` of `4G`. (§2.12.5 —
       `free` reads the host's `/proc/meminfo`; the container's real numbers are `memory.current`
       and `memory.max`.) `[TRAP]`
5.1.78 `strace -c -f -p <pid>` output where `futex` is 78% of time and `epoll_wait` is 4 calls.
       (§1.3.8 — lock contention, not I/O; and never leave `strace` attached.)
5.1.79 `/proc/<pid>/schedstat` reading `48281937461 9174829183 412884` on a service missing a 30 ms
       budget at 38% CPU. (§1.6.11 — field 2 is run-queue wait, ~19% of on-CPU time spent waiting to
       run.) `[CALC]`
5.1.80 `/proc/<pid>/status` showing `Threads: 1021`, `VmRSS: 3891204 kB`, `VmSwap: 812004 kB`,
       `nonvoluntary_ctxt_switches: 8814222`. (§1.5.13, §2.20 — near a `pids.max` of 1024, swapping,
       and being preempted rather than blocking.)
5.1.81 `jcmd <pid> VM.native_memory summary` whose `Thread` reserved is 1.0 GB and committed is
       48 MB. (§2.3.4 — 1 MiB reserved per thread stack against ~48 KiB touched; reserved is not
       RSS.)
5.1.82 `lsof -p <pid> | awk '{print $5}' | sort | uniq -c | sort -rn` showing `18422 REG` for one
       path. (§2.16.4 — a stream leak, not a socket leak; the fix is try-with-resources.)

*(82 leaves)*

## §5.2 One-line assertions to be able to state cold

5.2.1 Every checklist line from the current `src/topics/11-operating-systems-linux.md` — all **46** —
      restated and preserved as the floor of this section, with each one's number attached where it
      had none. `[TABLE]`
5.2.2 On Linux, `fork` is `clone(SIGCHLD)` and `pthread_create` is `clone(CLONE_VM|CLONE_FS|
      CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|CLONE_SETTLS|...)` — one syscall, different
      flags.
5.2.3 `getpid()` returns `tgid`; `gettid()` returns `pid`. The kernel's per-thread object is
      `task_struct`.
5.2.4 A trivial syscall costs **50–100 ns** unmitigated and **250–600 ns** with KPTI + retpoline +
      IBRS; a function call costs 1–2 ns.
5.2.5 The vDSO serves `clock_gettime`, `gettimeofday`, `time` and `getcpu` in ring 3 at ~**20–25 ns**.
5.2.6 x86-64 syscall arguments go in `rdi, rsi, rdx, r10, r8, r9` — **`r10`, not `rcx`** — with the
      number in `rax` and at most **six** register arguments.
5.2.7 The kernel returns `-errno` in `rax` in the range `-1..-4095`; glibc converts it. `errno` is
      meaningless unless the call failed.
5.2.8 `strace` costs **10–100×**. `perf trace`, `bpftrace` and `bcc` do not.
5.2.9 Exit status: `128 + signal`. **137 = 128 + 9 (SIGKILL)**, **143 = 128 + 15 (SIGTERM)**.
5.2.10 `SIGKILL` (9) and `SIGSTOP` (19) cannot be caught, blocked or ignored. `SIGQUIT` (3) dumps JVM
       threads.
5.2.11 EEVDF replaced CFS's pick in **6.6**; the tunable is `/sys/kernel/debug/sched/base_slice_ns`
       = **750,000 ns**, and `sched_latency_ns`/`sched_min_granularity_ns` are gone. `[VERSION-TRAP]`
5.2.12 A context switch is **1–5 µs** direct; the indirect cache and TLB cost is usually larger; a
       process switch adds a `CR3` reload.
5.2.13 `voluntary_ctxt_switches` means it blocked; `nonvoluntary_ctxt_switches` means it was
       preempted. Both are in `/proc/<pid>/status`.
5.2.14 Load average is `R` **plus** `D`, exponentially damped over 1/5/15 minutes, with **no
       denominator**. Always divide by `nproc` and always state the trend.
5.2.15 PSI is the correct pressure signal: `/proc/pressure/{cpu,memory,io}`, `some`/`full`,
       `avg10`/`avg60`/`avg300`, `total` in **microseconds**.
5.2.16 `R` in `ps` means running **or** runnable; `ps` cannot tell you which.
5.2.17 `D` state is uninterruptible sleep in a kernel path that cannot unwind; `SIGKILL` does not
       reliably reach it. `/proc/<pid>/wchan` names the function.
5.2.18 `/proc/<pid>/schedstat` field **2** is nanoseconds spent waiting on the run queue. That is the
       number that explains a budget breach at 38% CPU.
5.2.19 The canonical x86-64 split is 128 TiB user (`0x0000_7fff_ffff_ffff`) and 128 TiB kernel
       (`0xffff_8000_0000_0000`+) under 4-level paging.
5.2.20 A 4-level page-table walk costs up to **4** memory accesses on a TLB miss; the page size is
       **4 KiB**, huge pages are **2 MiB** and **1 GiB**.
5.2.21 A minor fault is ~**1–3 µs**; a major fault against gp3 EBS is ~**0.5–1 ms** — a **500×**
       ratio, and 30 of them consume the whole `ClientRestrictions` 30 ms budget.
5.2.22 `fork` copies page tables, not pages: 12 GB of touched heap is ~3.1M PTEs ≈ **24 MB**, which
       is why COW makes `Runtime.exec` survivable.
5.2.23 The JVM uses **`POSIX_SPAWN`**, not `fork`, for `ProcessBuilder` since JDK 13
       (`-Djdk.lang.Process.launchMechanism`). `[VERSION-TRAP]`
5.2.24 glibc `malloc` switches from `brk`/arena to `mmap` at `M_MMAP_THRESHOLD` = **128 KiB**;
       `MALLOC_ARENA_MAX` defaults to **8 × cores**.
5.2.25 `vm.overcommit_memory` is **0** (heuristic) by default; **2** refuses allocation past
       `CommitLimit` and can stop a 12 GB-heap JVM from starting on a box with free RAM.
5.2.26 `vm.swappiness` ranges **0–200** since 5.8, default **60**. Every guide saying 100 is the
       maximum is pre-5.8. `[VERSION-TRAP]`
5.2.27 `vm.dirty_ratio` **20**, `vm.dirty_background_ratio` **10**, `vm.dirty_expire_centisecs`
       **3000** — these three decide when your `write` becomes a disk write.
5.2.28 Linux fills free RAM with page cache by design. Read the **`available`** column of `free -h`,
       never `free`.
5.2.29 MGLRU (`/sys/kernel/mm/lru_gen/enabled`, since 6.1) may have replaced the active/inactive
       LRU pair on your box. Check before reasoning about reclaim. `[VERSION-TRAP]`
5.2.30 `RLIMIT_NOFILE` under systemd 240+ is soft **1024** / hard **524288**, capped by
       `fs.nr_open` = **1048576**. The applicable value is in `/proc/<pid>/limits`.
5.2.31 There are three fd tables: per-process fd table → open file description (holding the offset
       and status flags) → inode.
5.2.32 `select` cannot exceed `FD_SETSIZE` = **1024** and is O(n) per call; `epoll` keeps a
       persistent RB-tree interest set and a callback-populated ready list, so `epoll_wait` is
       O(ready).
5.2.33 Edge-triggered `epoll` requires reading until `EAGAIN`; omit the loop and the connection
       stalls forever.
5.2.34 `write()` success means "in the page cache". Durability needs `fsync`, `fdatasync`, `O_SYNC`
       or `O_DSYNC`.
5.2.35 `fsync` p50 is ~**25–100 µs** on local NVMe and ~**0.5–2 ms** on gp3 EBS; one `fsync` per
       record at 1 ms caps you at ~**1,000 records/sec**.
5.2.36 An `fsync` error is reported **once**; the next `fsync` may return success on data that was
       never written. Also `fsync` the parent directory after creating a file.
5.2.37 There is no `O_DIRECT` in the JDK. `FileChannel.force(true)` is `fsync`, `force(false)` is
       `fdatasync`.
5.2.38 `%util` measures time with ≥1 request in flight and is misleading on multi-queue NVMe;
       `await` is the latency you feel and `aqu-sz` is the queue depth.
5.2.39 `df -i` for inodes; `df`/`du` disagreement means a deleted-but-open file (`lsof +L1`).
5.2.40 cgroup **v2** is the only layout on any current distro: `cpu.max` ("max 100000"),
       `cpu.weight` (**100**, 1–10000), `memory.max` ("max"), `memory.high`, `pids.max`, `io.max`.
       The v1 names are not on your box. `[VERSION-TRAP]`
5.2.41 `cpu.stat` reports `nr_periods`, `nr_throttled`, `throttled_usec`, `nr_bursts`, `burst_usec`.
       `memory.events` reports `low`, `high`, `max`, `oom`, `oom_kill`, `oom_group_kill`.
5.2.42 CFS-bandwidth throttling stalls a task for **up to a full period** — 60 ms of a 100 ms period
       at a 40 ms quota — while `top` shows 40% CPU and looks healthy.
5.2.43 `Runtime.availableProcessors()` under cgroup v2 is `ceil(quota/period)`:
       `"150000 100000"` → **2**, not 1.5. `-XX:ActiveProcessorCount` overrides it.
5.2.44 `UseContainerSupport` is on by default, and `MaxRAMPercentage` defaults to **25.0** — an
       unflagged JVM in a 4 GB container takes a **1 GB** heap.
5.2.45 A JVM's RSS is heap + metaspace + code cache + GC structures + thread stacks (1 MiB reserved
       each) + direct/mapped buffers + glibc arenas. Never set `-Xmx` equal to the container limit.
5.2.46 OOM killer = kernel, cgroup or host memory, `SIGKILL`, exit **137**, `dmesg`,
       `memory.events` `oom_kill`, **no stack trace and no heap dump**. `OutOfMemoryError` = JVM,
       heap or metaspace or direct memory, an `Error` with a stack trace, hooks run.
5.2.47 `memory.high` throttles under heavy reclaim instead of killing — often the worse failure,
       because the service stays "up" and useless.
5.2.48 `top` and `free` inside a container read the **host's** `/proc`; the container's real numbers
       are `memory.current`, `memory.max` and `cpu.stat`. `[TRAP]`
5.2.49 A container is `clone()` with `CLONE_NEW{NS,PID,NET,UTS,IPC,USER,CGROUP,TIME}` plus a cgroup
       plus a seccomp filter plus overlayfs. Nothing more exotic.
5.2.50 Docker's default seccomp profile blocks **40+** syscalls including `perf_event_open`, `bpf`,
       `ptrace`, `mount` and **`io_uring_setup`** — which is why "just use io_uring" is not
       deployable advice and why `perf` fails inside a pod. `[VERSION-TRAP]`
5.2.51 `kernel.perf_event_paranoid` defaults to **2** ("disallow kernel profiling by users without
       `CAP_PERFMON`"); `perf` on a JVM also needs `-XX:+PreserveFramePointer` or every frame is
       `[unknown]`.
5.2.52 A virtual thread on **Java 21** pins its carrier inside `synchronized`; **JEP 491 (JDK 24)**
       removed that and removed `jdk.tracePinnedThreads`. Native-call pinning remains in both.
       `[VERSION-TRAP]`
5.2.53 Shell-form `CMD` makes `/bin/sh` PID 1, which does not forward `SIGTERM`; the JVM as PID 1
       receives signals but does not reap orphans. Use exec form plus `tini`.
5.2.54 Graceful shutdown order: fail readiness → wait for deregistration → stop accepting → drain
       in-flight → flush → close pools → exit **0**. Closing the pool first fails every in-flight
       request.
5.2.55 Shutdown hooks never run on `SIGKILL`, `Runtime.halt()` or a JVM crash, and their ordering
       across hooks is unspecified. They are cleanup, not durability.
5.2.56 `terminationGracePeriodSeconds` must be `preStop sleep + drain deadline + flush margin`;
       Kubernetes `SIGTERM` and endpoint removal are **concurrent**, so a `preStop` sleep of ~5–8 s
       is what closes the dropped-request window.
5.2.57 The cache line is **64 bytes** on x86-64 (**128** on Apple M-series); a write requires
       exclusive ownership, so two unrelated fields in one line cost a coherence round trip
       (~40–100 ns) instead of an L1 hit (~1 ns).
5.2.58 `@Contended` is `jdk.internal.vm.annotation.Contended` and is **silently ignored** on
       application classes without `-XX:-RestrictContended`.
5.2.59 The latency ladder to keep in one breath: L1 ~1 ns, L2 ~4 ns, L3 ~15–20 ns, DRAM ~80–100 ns,
       NVMe ~20 µs, EBS ~1 ms, cross-AZ RTT ~1 ms.
5.2.60 For every symptom, name the resource **and** the file that measures it. "The box is slow" is
       not a diagnosis; `avg10=41.2` on `/proc/pressure/io` is.
5.2.61 The ten sentences that most reliably signal depth in an OS interview, and the ten that most
       reliably signal its absence. `[TABLE]`

*(61 leaves)*

## §5.3 Retention drills

5.3.1 **Constant recall drill.** 60 flashcard pairs (name → value) covering every `[NUM]` and
      `[SYSCTL]` leaf in this file: page size, huge-page sizes, cache-line size, `base_slice_ns`,
      `cpu.max` default, `cpu.weight` default and range, `MaxRAMPercentage` default,
      `M_MMAP_THRESHOLD`, `MALLOC_ARENA_MAX`, `vm.swappiness` range and default, the three dirty
      knobs, `FD_SETSIZE`, the systemd soft/hard `RLIMIT_NOFILE` pair, `fs.nr_open`,
      `perf_event_paranoid`, `pid_max`, `ThreadStackSize`, 137/143, and the L1→cross-AZ ladder.
5.3.2 **Symptom → file drill.** 30 symptom strings; for each, name the **one file** you read first
      and the number in it you are looking for. `Too many open files` → `/proc/<pid>/limits`.
      p99 spike at 40% CPU → `cpu.stat` `nr_throttled`. Exit 137 → `memory.events` `oom_kill`.
      `kill -9` not working → `/proc/<pid>/wchan`.
5.3.3 **One command per symptom drill.** 25 pairs, and the discipline is exactly one command, no
      pipeline of alternatives: hot thread → `top -H -p <pid>`; run-queue delay →
      `cat /proc/<pid>/schedstat`; throttling → `cat /sys/fs/cgroup/<path>/cpu.stat`;
      disk latency → `iostat -xz 1`; who has the port → `ss -lptn 'sport = :8080'`;
      deleted-but-open → `lsof +L1`; OOM record → `dmesg -T | grep -i 'killed process'`.
5.3.4 **`[DIAG]` output-reading drill A: `top` and `vmstat`.** Ten pre-baked headers and `vmstat`
      lines (including the four in §5.1.70, §5.1.74, and two clean ones), read aloud field by field
      with a one-sentence verdict and the next command. Marked wrong if you name a cause the output
      does not support. `[DIAG]`
5.3.5 **`[DIAG]` output-reading drill B: cgroup and `/proc` files.** Ten pastes of `cpu.stat`,
      `memory.events`, `memory.current`/`memory.max`, `/proc/pressure/*`, `/proc/<pid>/status`,
      `/proc/<pid>/schedstat`, `/proc/<pid>/smaps_rollup` and `/proc/<pid>/limits` — for each, state
      the derived quantity (throttled fraction, mean stall, RSS composition, headroom to the limit)
      **with the arithmetic shown**. `[DIAG]` `[CALC]`
5.3.6 **`[DIAG]` output-reading drill C: JVM-meets-kernel.** Five pairs where you must reconcile a
      JVM view against a kernel view and explain the divergence: `jcmd VM.native_memory summary`
      reserved vs `VmRSS`; a thread dump's `RUNNABLE` count vs `%us`;
      `availableProcessors()` vs `nproc` vs `cpu.max`; `-Xmx` vs `memory.max`; GC pause logs vs
      `si`/`so`. `[DIAG]`
5.3.7 **Arithmetic drill.** Page-table size for a 12 GB heap; fault count for a 4 GiB mapping at
      4 KiB and at 2 MiB; RSS budget for a 512 MiB container running a 256 MB heap; throttled
      fraction and mean stall from a `cpu.stat` paste; records/sec ceiling from an `fsync` p50;
      syscalls saved by an 8 KiB buffer over 6 MB; thread-model RSS for 55k connections at 1 MiB
      reserved and 48 KiB touched; `availableProcessors()` for four `cpu.max` values.
      `[CALC]`
5.3.8 **"Trace it to the kernel" drill.** For each of eight Java-level statements, write the syscall
      sequence and the kernel subsystem it lands in, from memory:
      `new Thread(...).start()`; `synchronized` under contention; `socketChannel.read(buf)` on an
      empty socket; `FileChannel.force(true)`; `byte[] b = new byte[2_000_000]`;
      `ProcessBuilder.start()`; `Thread.sleep(50)`; `System.nanoTime()`.
5.3.9 **Reverse trace drill.** The same in reverse: given a syscall or kernel function
      (`futex_wait_queue`, `io_schedule`, `folio_wait_bit_common`, `ep_poll`, `do_user_addr_fault`,
      `try_to_free_pages`, `posix_spawn`), name the Java-level operation that produced it and the
      one command that would have shown it to you.
5.3.10 **Version drill.** For each of the **seventeen** deltas in the front matter, state the stale
       claim, the true baseline behaviour, and the release in which it changed. Marked wrong if you
       state the truth without the version, because a version-free answer is only accidentally
       correct. `[VERSION-TRAP]`
5.3.11 **Incident drill.** The **five** incidents of §3.19 plus the per-section `[INCIDENT]` leaves,
       reconstructed from the symptom line alone: state the diagnosis path as an ordered command
       list, the root cause, the immediate fix, and the durable fix — in that order, and without
       skipping to the answer.
5.3.12 **Triage-order drill.** Recite the §1.30 order cold, then run it against three randomly
       chosen QuizStakes symptom cards under a two-minute clock. The measured skill is not knowing
       the commands; it is not running the eleventh one before the first.
5.3.13 **Whiteboard drill.** Draw from memory, unaided: the process address space with every region
       labelled; the 4-level page-table walk; the page-fault decision tree; the three fd tables;
       `epoll`'s RB-tree and ready list; the cgroup v2 hierarchy with `cpu.max` and `memory.max`
       marked; and the OOM three-way decision. Seven of the diagrams in the manifest below.
5.3.14 **Number-defence drill.** For eight of the constants in 5.3.1, state **where you would read it
       on the box** rather than reciting it — `getconf PAGESIZE`,
       `/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size`,
       `/sys/kernel/debug/sched/base_slice_ns`, `sysctl vm.swappiness`, `/proc/<pid>/limits`,
       `cat /sys/fs/cgroup/<path>/cpu.max`, `java -XX:+PrintFlagsFinal -version | grep
       MaxRAMPercentage`, `sysconf(_SC_CLK_TCK)`. Values drift; the file does not.
5.3.15 **Build-recall drill.** For each of the ten `[BUILD]` artefacts in PART 4, state in three
       sentences what it measures, the number it lands on, and the trap it proves — without looking
       at the code.
5.3.16 **Scope-boundary drill.** For twelve prompts that sit on a seam
       (`epoll` vs topic 10, thread pools vs topic 05, heap sizing vs topic 06, probes vs topic 19,
       SLOs vs topic 20, EBS products vs topic 18, WAL vs topic 09, container breakout vs topic 13),
       state the one-paragraph mechanism this guide owns and then name the guide that owns the rest.
       `[X-REF]`
5.3.17 **Spaced-repetition schedule.** Constants (5.3.1) daily for seven days, then twice weekly.
       Output-reading drills (5.3.4–5.3.6) every other day — this is the perishable skill. Trace
       drills (5.3.8, 5.3.9) weekly. The version drill (5.3.10) weekly, because it is the cheapest
       way to sound current. The full question bank once at T-7 days and once at T-1.
5.3.18 **The self-assessment gate.** You are ready when you can, cold: read any `top`/`vmstat`/
       `iostat`/`cpu.stat`/`dmesg` paste and give a verdict plus the next command; state the file
       that measures each of the five resources; recite the exit-code and signal-number table;
       explain 137 vs `OutOfMemoryError` in four sentences with the evidence for each; and name a
       version for every one of the seventeen deltas. Anything less and the interview will find the
       gap, because the debug-the-incident band is unfakeable.

*(18 leaves)*

---

## Diagram manifest

Diagrams the write pass must produce as standalone SVGs (never inline `<svg>`, never ASCII art),
embedded at the point of explanation. Numbered `D-NN-slug.svg`, topic-scoped.

| ID | Diagram | What it must show | Anchored at |
|---|---|---|---|
| D-01 | The syscall path, user to kernel and back | `syscall` instruction → `MSR_LSTAR` → `entry_SYSCALL_64` → the syscall table → the handler → `sysretq`, with the register convention (`rax`, `rdi`, `rsi`, `rdx`, `r10`, `r8`, `r9`) labelled and the KPTI `CR3` swap marked as an optional extra step | §1.3.2, §3.3.2 |
| D-02 | The process address space | Low-to-high: text, rodata, data, bss, heap with the `brk` pointer, the `mmap` region growing down, per-thread stacks with `PROT_NONE` guard pages, `[vdso]`/`[vvar]`, the 128 TiB user limit, the non-canonical hole, and kernel space — annotated with a real `/proc/<pid>/maps` excerpt from a `FundsLedger` JVM | §1.11.1 |
| D-03 | The 4-level page-table walk | `CR3` → PGD → PUD → PMD → PTE → frame, with the 9/9/9/9/12 bit split of a 48-bit virtual address marked, the TLB short-circuit path, and the "4 memory accesses on a miss" cost annotated; 5-level paging shown as an extra level | §1.10.4, §3.4.2 |
| D-04 | The page-fault decision tree | Fault → is the address in a VMA? → permissions? → present bit? → branch to: minor (page cache hit / COW / zero page), major (swap-in or file read), or `SIGSEGV`; each leaf labelled with its cost (~1–3 µs vs ~0.5–1 ms vs death) | §1.12.2, §3.5.3 |
| D-05 | The page cache and writeback path | `write()` → page cache page marked dirty → the three triggers (`dirty_background_ratio` 10, `dirty_ratio` 20 blocking the writer, `dirty_expire_centisecs` 3000) → `[kworker/*flush*]` → block layer, with `fsync`/`fdatasync`/`O_DSYNC` shown as the paths that bypass the wait | §1.13.4, §3.8.5 |
| D-06 | The reclaim and OOM decision path | Allocation → free-list → watermarks (min/low/high) → direct reclaim vs `kswapd` → MGLRU generations or the active/inactive LRU pair → swap or drop-clean → compaction → OOM, with PSI `memory.pressure` and `memory.high` throttling marked as the pre-OOM signals | §1.15.3, §3.6.4 |
| D-07 | The run queue and the EEVDF timeline | Per-CPU `rq` with the `cfs_rq` RB-tree keyed by virtual deadline, each task's `lag` shown as credit or debt, and a four-task timeline over three `base_slice_ns` (750 µs) slices showing the eligible-with-earliest-deadline pick — contrasted with the pre-6.6 lowest-`vruntime` pick | §1.7.6, §3.2.5 |
| D-08 | The context-switch timeline | Two tasks on one CPU: timer interrupt or block → `schedule()` → `pick_next_task` → `switch_mm` (process only) → `switch_to` register save/restore → resume, with the 1–5 µs direct cost and the cache/TLB refill tail drawn to scale so the indirect cost visibly dominates | §1.9.2 |
| D-09 | The four I/O models side by side | Blocking, non-blocking polling, readiness multiplexing (`epoll`), and completion-based async (`io_uring`) as four timelines for the same read, with the thread's state and the syscall count annotated on each | §1.21.1 |
| D-10 | `epoll` internals | The `eventpoll` struct, the RB-tree of registered `epitem`s keyed by fd, the ready list, the `ep_poll_callback` wired into the file's wait queue, and `epoll_wait` draining the ready list — with the level-triggered re-add versus edge-triggered one-shot difference marked | §1.22.7, §3.11.2 |
| D-11 | The `io_uring` rings | The shared SQ and CQ mmapped between user and kernel, head/tail indices, an SQE and a CQE laid out field by field, `io_uring_enter` batching N operations, and the `IORING_SETUP_SQPOLL` zero-syscall path — plus a callout that `io_uring_setup` is blocked by the default Docker seccomp profile | §2.18.3, §3.12.2 |
| D-12 | The three fd tables | `files_struct` fd array → `struct file` open file description (holding `f_pos` and `f_flags`) → `struct inode`, with three scenarios drawn: two `open`s of one path, `dup2`, and `fork` — showing exactly which arrow is shared in each | §1.16.2 |
| D-13 | The VFS path | `openat` → path walk through the dentry cache → inode → `file_operations` dispatch → the concrete filesystem (ext4/XFS) → the block layer, with the dentry and inode caches drawn as the two things that make a second `open` cheap | §1.17.5, §3.10.1 |
| D-14 | The block-layer path | `submit_bio` → `blk-mq` software queue per CPU → hardware dispatch queue → I/O scheduler (`none`/`mq-deadline`/`bfq`) → driver → device, with `iostat`'s `await`, `aqu-sz` and `%util` marked at the exact points they are measured and `io.max` throttling shown as a gate | §1.20.3, §3.9.1 |
| D-15 | The cgroup v2 unified hierarchy | The single tree from `/sys/fs/cgroup` down to a pod's container, with `cgroup.subtree_control` delegation, and each level's `cpu.max`, `cpu.weight`, `memory.max`, `memory.high`, `pids.max`, `io.max` and `*.pressure` files shown — annotated with the v1 names that no longer exist | §2.9.2, §3.15.1 |
| D-16 | The namespace map of a container | One `FundsLedger` container's eight namespaces (mount, PID, net, UTS, IPC, user, cgroup, time) drawn as membranes around the process, with `/proc/<pid>/ns/*` symlink targets shown and what leaks through each one marked | §2.13.3, §3.16.1 |
| D-17 | The JVM's Linux memory map | A 12 GB-heap `FundsLedger` process: heap, metaspace, compressed class space, code cache, GC structures, thread stacks (1 MiB reserved / ~48 KiB touched), direct and mapped buffers, glibc arenas, `libjvm.so`, `[vdso]` — drawn to scale against `memory.max`, with reserved-vs-committed-vs-resident as three distinct bar segments | §2.2.4, §2.3.2 |
| D-18 | The CFS bandwidth throttling timeline | Four consecutive 100 ms periods at `cpu.max = "40000 100000"`: quota consumed, the throttled remainder shaded, and a request arriving at the wrong moment waiting 60 ms — with `nr_periods`, `nr_throttled` and `throttled_usec` shown accumulating and the 30 ms `ClientRestrictions` budget drawn as a line the stall crosses | §2.10.3 |
| D-19 | The OOM three-way decision | One diagram, three killers: cgroup OOM (`memory.max` breached → `memory.events` `oom_kill` → `SIGKILL` → 137), global OOM (`oom_score`/`oom_score_adj` → `oom_badness` → victim), and JVM `OutOfMemoryError` (heap/metaspace/direct exhausted → `Error` + stack trace + heap dump), with the evidence file for each on its branch | §2.11.2 |
| D-20 | The graceful-shutdown sequence | A swimlane over 40 s: orchestrator, LB/endpoint controller, PID 1, the JVM, and an in-flight request — `SIGTERM` and endpoint removal drawn as **concurrent**, the `preStop` sleep closing the gap, the drain deadline, the flush, the pool close, exit 0, and the `SIGKILL` boundary; with the shell-form-PID-1 variant drawn beneath showing the signal never arriving | §2.23.4 |
| D-21 | The `futex` park chain | `LockSupport.park()` → `Unsafe.park` → `pthread_cond_wait`/`futex(FUTEX_WAIT)` → task off the run queue → `futex(FUTEX_WAKE)` from the unlocker → wakeup → run-queue re-entry, with the uncontended CAS-only path drawn alongside as the branch that never enters the kernel | §1.24.9, §3.13.4 |
| D-22 | The cache line and false sharing | Two 64-byte lines: `long[3]` with three counters in one line and three cores' MESI states thrashing, versus `long[24]` with `i*8` indexing giving one line per counter; the read-for-ownership invalidation arrows drawn, and the 168-byte cost of the fix labelled | §1.32.5 |
| D-23 | The NUMA topology | A two-socket box: cores, per-node local memory, the interconnect, and a 12 GB heap drawn once as interleaved and once as node-bound, with local versus remote access latencies annotated and `numactl --hardware`/`numastat -p` output excerpted beside it | §2.8.2 |
| D-24 | The triage decision tree | The §1.30 order as a decision tree from "the service is slow and you have SSH": PSI first, then the CPU split (`us`/`sy`/`wa`/`st`/`id`), branching to per-process, per-thread, memory, disk, fd and network legs — every leaf naming exactly one command and one file, and every branch labelled with the observation that takes it | §1.30.2 |
| D-25 | Huge pages and THP | 512 × 4 KiB PTEs versus one 2 MiB PMD-level mapping, the TLB-entry saving shown numerically, and `khugepaged`'s promotion path plus the direct-compaction stall drawn as the latency cost — with `enabled`/`defrag` file values for the RHEL-family and Debian-family defaults side by side | §2.7.3 |
| D-26 | PSI stall accounting | A four-task timeline over one second showing which intervals count toward `some` and which toward `full` for memory, and how those produce `avg10`/`avg60`/`avg300` and the microsecond `total` — with load average drawn beneath over the same interval to show it counting `D`-state tasks and having no denominator | §2.25.4 |
| D-27 | Boot to PID 1 | Firmware/UEFI → bootloader → kernel decompression → `start_kernel` → `initcall` ordering → initramfs → `switch_root` → `/sbin/init` (systemd) → default target → the `quizstakes.slice` unit and its cgroup, with the `dmesg` line that marks each transition annotated | §3.1.1 |
| D-28 | The `ReserveStake` path as OS work | One QuizStakes stake reservation from `ApplicationGateway` to `FundsLedger` to disk, annotated at every hop with the OS mechanism it costs: syscalls, `epoll_wait` wakeups, run-queue wait, page faults, `futex` contention, page-cache hits, the `fsync`, and the block-layer round trip — summing to the **150 ms** stake-reservation budget | §2.26.6 |

## Sources consulted — PART E

| URL | What it established for this part |
|---|---|
| `https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html` | The exact field numbers and types of `/proc/<pid>/stat` used in §4.7.2 and §4.3.1: `state` (3), `minflt` (10), `majflt` (12), `utime` (14), `stime` (15), `num_threads` (20), `starttime` (22), `vsize` (23), `rss` (24, in **pages**), `delayacct_blkio_ticks` (42), `guest_time` (43); and that tick fields must be divided by `sysconf(_SC_CLK_TCK)` |
| `https://docs.kernel.org/admin-guide/cgroup-v2.html` | The exact cgroup v2 interface-file names and defaults used across §4.5, §4.6 and §4.7: `cpu.stat` fields `nr_periods, nr_throttled, throttled_usec, nr_bursts, burst_usec`; `memory.events` fields `low, high, max, oom, oom_kill, oom_group_kill`; `cpu.max` format `$MAX $PERIOD` with default `"max 100000"`; `memory.max`/`memory.high`/`memory.swap.max`/`pids.max` all defaulting to `"max"`; `io.max` as a nested-keyed file with `rbps`/`wbps`/`riops`/`wiops`; `memory.pressure` as a read-write nested-keyed PSI file |
| `https://man7.org/linux/man-pages/man2/open.2.html` | The `O_DIRECT`, `O_SYNC` and `O_DSYNC` semantics quoted in §4.8.2: that `O_DIRECT` "may impose alignment restrictions on the length and address of user-space buffers and the file offset of I/Os", that logical block size comes from `ioctl(BLKSSZGET)` or `blockdev --getss`, that `O_DSYNC` flushes only metadata needed to read the data back ("the last modification timestamp is not needed… but the file length is"), and that applications "should avoid mixing `O_DIRECT` and normal I/O to the same file" |

**Not independently re-verified in this part, and therefore carrying `[RESEARCH]` at the leaf.** The
session's WebSearch budget was exhausted before PART E, so the following are stated from the baseline
established in PART A's front matter and must be re-checked against a primary source during the write
pass: the `fsync` error-reporting-once behaviour and the per-file-description error tracking added in
4.13 (§4.8.6 — check `man 2 fsync` and the LWN writeback-error series); the exact set of syscalls
blocked by the current Docker and Kubernetes default seccomp profiles (§4.10.1, §5.2.50); the
`bpftrace`/`bcc` tool names and flags as shipped in 0.21+ and their availability on Amazon Linux 2023
(§4.10.2); `cpu.max.burst` semantics and default (§4.5.5); async-profiler's current CLI surface, which
changed name from `profiler.sh` to `asprof` (§4.10.4); and the `mem_load_l3_hit_retired.xsnp_hitm`
event name, which is Intel-microarchitecture-specific and has no AMD or Graviton equivalent under that
name (§4.4.4).

## Gaps vs the current guide

`src/topics/11-operating-systems-linux.md` is **616 lines** across 13 numbered sections plus a
46-item atomic concept checklist. For its size it is a genuinely good triage guide, and its strongest
material is better than most writing at this level: the `free`-vs-`available` explanation, the
`top` CPU-split table with `st` for the noisy-neighbour case, the `df`/`du`-disagreement mechanism,
the OOM-killer-versus-`OutOfMemoryError` comparison table, the graceful-shutdown ordering rule, the
Docker shell-form PID 1 trap, and the nine-step triage order are all correct, mechanism-aware and
directly usable. **Every one of its five `**Trap:**` blocks and every one of the 46 checklist lines
must survive into the bible** — none is superseded, and §5.2.1 preserves the checklist in full while
each trap is carried into the section that now owns its mechanism.

What it is not is a complete operating-systems document. It has no scheduler section at all, no
address translation, no page-fault taxonomy beyond two sentences, no `/proc` or `/sys` treatment, no
cgroups, no namespaces, no `epoll` or `io_uring`, no cache hierarchy, no kernel internals, no
build-it section, no scenario numbers anywhere, and no version discipline — it names no kernel, so
its `vm.swappiness` "0–100" and its cgroup-v1-shaped assumptions are stale rather than wrong.

Two of its sections have **no counterpart in this syllabus and must be rehomed rather than dropped**:
current §9 (cron, `flock`, distributed cron) and current §10 (SSH, keys, `ProxyJump`, `rsync`, SSM).
Their five checklist lines are in the 46 that must survive. The write pass must either extend §1.26
(sessions, daemons, PID 1) to absorb cron and `flock` and add an operator-access appendix for SSH, or
hand both to `19-docker-kubernetes.md` and `18-cloud-aws.md` explicitly with an `[X-REF]`. Silently
losing them would be a regression against the current guide, which is why this table ends with rows
for both.

| Syllabus area | Present in `src/topics/11-operating-systems-linux.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why the OS is a backend discipline; the five resources and their files | the 3-line scope preamble | ✅ the four paid-for questions, the five-resources table, the name-the-file habit, the opening incident | ✅ |
| §1.2 the user/kernel boundary, rings, KPTI, monolithic vs microkernel | §4 mentions "a controlled transition into kernel mode" | ✅ rings and the `CPL`, the address-space split, kernel threads in brackets, KPTI's cost, modules and taint, what is *not* in the kernel | ✅ severely |
| §1.3 syscalls: the ABI, the cost, the vDSO, batching, seccomp | §4 (one paragraph on blocking syscalls) | ✅ the register ABI, the `-errno` convention, the 50–600 ns cost, the vDSO, the must-know syscall list, `strace`'s 10–100× penalty, batching arithmetic, seccomp | ✅ severely |
| §1.4 the process, `fork`/`exec`/`wait`, exit status, zombies, orphans | §1 (the definition), §4 (zombies, correctly) | ✅ `task_struct` vs `tgid`, COW arithmetic, `POSIX_SPAWN` since JDK 13, the 128+signal encoding, `rusage`, orphans and subreapers, `pid_max`, `pidfd` | ✅ the zombie explanation is correct and must be preserved verbatim |
| §1.5 threads: `clone()`, sharing flags, stacks, virtual threads | §1 (both are `clone()`, the shared/private split, the 1 MB stack, the comparison table) — the guide's strongest section | ✅ the flag inventory, the unsharing flags, the 55k-session RSS arithmetic, `top -H`/`task/` navigation, `threads-max`/`RLIMIT_NPROC`/`pids.max`, the JDK 24 pinning change | ✅ the process/thread table is good and must be preserved verbatim and quantified |
| §1.6 process states, `D` state, load average, PSI | §1 (thread-dump states), §4 (the `ps` state table), §7 (load average vs cores, the `D`-state note) — good | ✅ `TASK_KILLABLE`, `wchan`/`stack`, PSI entirely, `schedstat`'s run-queue field, the lossy Java-to-kernel state mapping | ✅ the `RUNNABLE` trap and the load-average-includes-`D` point are excellent and must be preserved verbatim |
| §1.7 CFS, `vruntime`, nice, EEVDF | — | ✅ entire section — the largest single hole in the file | |
| §1.8 scheduling classes, RT policies, priorities, CPU affinity | — | ✅ entire section (`SCHED_OTHER`/`FIFO`/`RR`/`IDLE`/`DEADLINE`, `nice`, `chrt`, `taskset`, `cpuset.cpus`) | |
| §1.9 context switches: mechanics, kinds, cost | §2 (direct cost 1–5 µs, cache pollution, the causes, `vmstat`'s `cs`, the more-threads-≠-throughput point) — good | ✅ the switch mechanics step by step, voluntary vs involuntary counters in `/proc/<pid>/status`, migration cost, the arithmetic at scale | ✅ the 1–5 µs figure and the `vmstat cs` guidance must be preserved verbatim |
| §1.10 virtual memory, page tables, MMU, TLB | §3 (MMU, 4 KB/2 MB pages, TLB, one sentence each) | ✅ the 4-level walk, the bit split, TLB sizes and miss cost, ASIDs/PCIDs, `CR3` | ✅ severely |
| §1.11 the process memory map | §3 (VSZ vs RSS, correctly) | ✅ `/proc/<pid>/maps` and `smaps` entirely, every region, guard pages, `[vdso]`, reserved vs committed vs resident | ✅ severely |
| §1.12 page faults: minor, major, COW, demand paging, pre-faulting | §3 (minor vs major, one line each) | ✅ the fault handler's decision tree, the cost numbers, the zero page, `MAP_POPULATE`/`MADV_*`, `AlwaysPreTouch`, per-process fault counters | ✅ the minor/major distinction is correct and must be preserved verbatim and quantified |
| §1.13 the page cache, dirty pages, writeback | §3 (page cache, cold-cache-after-restart, the `free -h` misread) — very good | ✅ dirty-page accounting, the three writeback triggers and their sysctls, `[kworker/*flush*]`, readahead, `posix_fadvise`, `drop_caches` | ✅ the `free`/`available` trap is excellent and must be preserved verbatim |
| §1.14 user-space allocation: `brk`, `mmap`, glibc arenas, overcommit | §3 (overcommit in one paragraph, correctly) | ✅ `brk` vs `mmap`, `M_MMAP_THRESHOLD` 128 KiB, `MALLOC_ARENA_MAX`, the three `vm.overcommit_memory` modes, `CommitLimit`, `Committed_AS` | ✅ severely |
| §1.15 reclaim, swap, the OOM killer | §3 and §13 (swap, `swappiness`, GC-touches-the-whole-heap, `si`/`so` must be 0), §12 (the OOM killer's scoring) — good | ✅ watermarks, `kswapd` vs direct reclaim, MGLRU, `oom_badness`, `oom_score_adj`, `memory.high` throttling, `systemd-oomd` | ✅ `vm.swappiness` is stated as **0–100** and must be corrected to **0–200**; the GC-vs-swap argument is excellent and must be preserved verbatim |
| §1.16 fds, the three tables, the limits | §5 (fds, `ulimit -n`, `/proc/<pid>/limits` as authoritative, the two causes of `Too many open files`, `lsof` recipes) — the guide's second-strongest section | ✅ the three-table structure, `fs.nr_open` vs `fs.file-max`, the systemd 1024/524288 split, `epoll`/`eventfd`/`timerfd`/`pidfd` as fds, `O_CLOEXEC` | ✅ preserve the entire section verbatim; add the three tables and the current defaults |
| §1.17 files, inodes, the VFS, links, the dentry cache | §7 mentions `df -i` | ✅ inodes and their contents, hard vs symbolic links, the VFS dispatch, dentry and inode caches, path resolution | ✅ severely |
| §1.18 file I/O, the three layers of buffering, `fsync`, `O_DIRECT` | §7 mentions nothing; §3 covers the page cache only | ✅ entire section — `read`/`write`/`pread`/`writev`, application vs libc vs page-cache buffering, `fsync` vs `fdatasync`, `O_SYNC`/`O_DSYNC`/`O_DIRECT`, the error-reported-once trap, the directory-`fsync` trap | |
| §1.19 ext4 and XFS, journalling, `df` vs `du` | §7 (`df -h`, `df -i`, `du` recipes, inode exhaustion, the `df`/`du` disagreement mechanism) — very good | ✅ the filesystems themselves, journalling modes, block size and alignment, extents, `tune2fs`/`xfs_info` | ✅ the inode-exhaustion and deleted-but-open explanations are excellent and must be preserved verbatim |
| §1.20 disks, the block layer, schedulers, readahead, EBS | §7 (`iostat -xz`, `await`, `%util`, `aqu-sz`, and the burst-credit point) — good | ✅ `blk-mq`, the scheduler choice (`none`/`mq-deadline`/`bfq`), queue depth, `/sys/block/*/queue/*`, readahead tuning, gp3 vs io2 mechanics | ✅ the `%util`-is-misleading-on-NVMe caveat is present but must be sharpened into a `[TRAP]`; the burst-credit point must be preserved verbatim |
| §1.21 the four I/O models | §4 (blocking only) | ✅ non-blocking, multiplexed and completion-based entirely, and the comparison that makes the four a set | ✅ severely |
| §1.22 `select`, `poll`, `epoll` | — (topic 10 §15 carries it) | ✅ entire section as a kernel mechanism: `FD_SETSIZE` 1024, the O(n) argument, the RB-tree and ready list, LT vs ET, the `epoll_ctl` API | |
| §1.23 signals: the catalogue, delivery, dispositions, handler constraints | §6 (the signal table with numbers and catchability, `kill -3` for a thread dump) — very good | ✅ delivery vs generation, `sigaction` vs `signal`, the signal mask, async-signal-safety, `SA_RESTART` and `EINTR`, real-time signals, `signalfd` | ✅ the table and the `kill -3` point are excellent and must be preserved verbatim |
| §1.24 IPC: pipes, FIFOs, unix sockets, shared memory, `eventfd`, `futex` | §1's comparison table names "IPC: pipes, sockets, shared mem" | ✅ every mechanism's actual API and cost, the 64 KiB pipe buffer, `SCM_RIGHTS`, `futex` as the lock primitive | ✅ severely |
| §1.25 users, groups, permissions, `setuid`, capabilities | — | ✅ entire section (mode bits, `umask`, sticky/setgid, the capability inventory, `getcap`/`setcap`, `NoNewPrivs`) | |
| §1.26 sessions, process groups, controlling terminals, daemons, PID 1 | §6's PID 1 trap; §11 mentions `pkill`/`killall` | ✅ `setsid`/`setpgid`, `SIGHUP` on SSH drop, `nohup`/`setsid`/`systemd-run --scope`, the double-fork daemon idiom, systemd unit types, reaping as PID 1's job | ✅ the Docker PID 1 trap is excellent and must be preserved verbatim |
| §1.27 time: wall clock vs monotonic, `clock_gettime`, the vDSO, timers | — | ✅ entire section (`CLOCK_REALTIME` vs `CLOCK_MONOTONIC`, NTP slew vs step, why `System.currentTimeMillis` can go backwards, `timerfd`, timer slack) | |
| §1.28 finding, inspecting and killing a process | §11 (`pgrep -fa`, `lsof -i`, `fuser`, the escalate-never-lead-with-`-9` workflow, capture-evidence-first) — excellent | ✅ `pidfd_open` for race-free kill, process-group kill, `/proc/<pid>/{exe,cwd,environ,root}` inspection, `kill -0` for existence | ✅ preserve the entire kill workflow and the evidence-capture list verbatim |
| §1.29 `/proc` and `/sys`: the observability substrate | scattered (`/proc/<pid>/limits`, `/proc/sys/fs/file-max`, `/proc/<pid>/fd`) | ✅ the substrate itself — the per-process file inventory, the system-wide inventory, `/sys/fs/cgroup`, `/sys/block`, `/sys/kernel/mm`, `sysctl` vs writing the file | ✅ severely |
| §1.30 the box-triage toolkit and the order | §7 (the whole section — `top` header, the CPU-split table, `free`, `df`/`du`, `iostat`, `ps`, network, and the nine-step order) — the guide's best section | ✅ PSI first, `mpstat -P ALL`, `pidstat`, `sar`, per-cgroup files, the evidence-before-intervention rule, the two-minute time box | ✅ preserve the CPU-split table, the sample `top` header reading, and the nine-step order verbatim; reorder to put PSI ahead of load average |
| §1.31 log combat | §8 (`tail -F`, `less +F`, the grep pipelines, the composed one-liners, `jq`, `journalctl`) — excellent and essentially complete | ✅ only additions: `journalctl` field filtering and `--output=json`, log-rotation interaction with the deleted-but-open trap, ripgrep, and the correlation-id drill | ✅ preserve the entire section verbatim |
| §1.32 CPU caches, cache lines, false sharing | §2 mentions "cache pollution" in one clause | ✅ entire section — the hierarchy with numbers, the 64-byte line, MESI, false sharing, `@Contended` and its `-XX:-RestrictContended` footgun, `LongAdder`/`Striped64`, JOL, Java object layout | ✅ severely |
| §2.1 the master cost / failure / file tables | — | ✅ entire section; the guide has no master table | |
| §2.2 the JVM as a Linux process | §12's trap enumerates RSS components correctly | ✅ the full mapping of every JVM region to a `/proc` line, reserved vs committed vs resident, NMT workflow, `smaps_rollup` reconciliation | ✅ the RSS-composition trap is excellent and must be preserved verbatim and turned into arithmetic |
| §2.3 native memory: direct buffers, metaspace, code cache, arenas | §12's trap names them in a list | ✅ each one's own limit flag, growth behaviour, leak signature and diagnostic; `MaxDirectMemorySize`, `MaxMetaspaceSize`, `ReservedCodeCacheSize`, `MALLOC_ARENA_MAX` | ✅ severely |
| §2.4 thread pool sizing against real core counts | §2 (the more-threads-≠-throughput point, correctly) | ✅ the sizing formula, Little's Law, the CPU-bound vs I/O-bound split, and what changes under `cpu.max` | ✅ preserve the point verbatim; add the arithmetic |
| §2.5 virtual threads and the kernel | §1 points at topic 10 §15 | ✅ the m:n mapping, the carrier pool and its sizing, what `top -H`/`/proc/<pid>/task` show, pinning as a kernel-visible event, the JDK 24 change | ✅ severely |
| §2.6 GC and the OS | §13 (GC touches the whole heap, so swapping is fatal) | ✅ GC's page-fault and TLB behaviour, `AlwaysPreTouch`, GC threads vs `cpu.max`, safepoints vs preemption, GC pauses caused by the OS rather than the collector | ✅ the GC-vs-swap argument is excellent and must be preserved verbatim |
| §2.7 huge pages and THP | §3 mentions "2 MB huge pages" in parentheses | ✅ entire section — `enabled`/`defrag` files and their distro-dependent defaults, `khugepaged`, compaction stalls, `UseTransparentHugePages` vs `UseLargePages`, when to turn it off | ✅ severely |
| §2.8 NUMA | — | ✅ entire section | |
| §2.9 cgroups v2 as the resource contract | §12 mentions "the *cgroup* limit triggers it" | ✅ entire section — the unified hierarchy, every controller and interface file, delegation, and the v1-name correction | ✅ severely |
| §2.10 CPU throttling: the p99 killer | — | ✅ entire section — one of the two highest-value gaps in the file | |
| §2.11 container OOM vs JVM `OutOfMemoryError` | §12 (the whole section, including the comparison table and the exit-137 tell) — excellent | ✅ `memory.events` `oom_kill`, `memory.high` as the third failure mode, `oom.group`, the `dmesg` record read field by field, where the heap dump went | ✅ preserve the comparison table and the trap verbatim; add the cgroup-v2 file names |
| §2.12 JVM container awareness | §12's trap ("modern JVMs are container-aware by default", `MaxRAMPercentage=70`) | ✅ the **25.0** default that is the actual trap, `availableProcessors()` = `ceil(quota/period)`, `ActiveProcessorCount`, `InitialRAMPercentage`/`MinRAMPercentage`, and the `free`/`top`-lie-in-a-container point | ✅ the `MaxRAMPercentage` recommendation is correct and must be preserved verbatim and quantified |
| §2.13 namespaces | — | ✅ entire section | |
| §2.14 the container substrate: overlayfs, runc, images | — | ✅ entire section | |
| §2.15 `ulimit`s that matter in production | §5 (`ulimit -n`, and the crucial limit-at-start-time point) | ✅ the other limits — `RLIMIT_NPROC`, `RLIMIT_STACK`, `RLIMIT_CORE`, `RLIMIT_MEMLOCK`, `RLIMIT_AS` — and how each is set in systemd, Docker and Kubernetes | ✅ the limit-at-start-time point is excellent and must be preserved verbatim |
| §2.16 fd exhaustion in a JVM service | §5 (the two causes, `lsof` by type, the try-with-resources fix) — excellent | ✅ the fd budget arithmetic for 55k sessions, `epoll`/`timerfd` fds the JVM opens, the monotonic-rise signature as a metric, `CLOSE_WAIT` correlation | ✅ preserve verbatim; add the arithmetic and the metric |
| §2.17 `epoll` in practice | — | ✅ entire section | |
| §2.18 `io_uring` | — | ✅ entire section, including the seccomp-blocked deployment reality | |
| §2.19 zero-copy: `sendfile`, `splice`, `MSG_ZEROCOPY`, `FileChannel.transferTo` | — | ✅ entire section | |
| §2.20 swap and the JVM | §13 (the whole section — the mechanism, the GC argument, `swappiness=1–10`, watch `si`/`so`) — very good | ✅ `memory.swap.max`, the Kubernetes `NodeSwap` beta correction, zram/zswap, the swappiness range correction | ✅ preserve the whole argument verbatim; correct the 0–100 range and the "Kubernetes required swapoff" tense |
| §2.21 disk I/O for a JVM service | §7's `iostat` block | ✅ log-writing as the dominant I/O of most services, GC log and heap-dump I/O, readahead for a `BankDeposits` sequential scan, `io.max` throttling, per-process `/proc/<pid>/io` | ✅ severely |
| §2.22 signals and the JVM | §6 (`kill -3`, the signal table) | ✅ which signals the JVM installs handlers for and why (`SIGSEGV` for null-check elimination, `SIGBUS`, `SIGQUIT`, `SIGPIPE`), `-Xrs`, chaining, and why `SIGSEGV` in `hs_err_pid.log` is usually not a kernel bug | ✅ severely |
| §2.23 graceful shutdown in a container | §6 (the full flow, the ordering rule, the Java and Spring surface, both traps) — excellent | ✅ the grace-period arithmetic, `SmartLifecycle` phases, `awaitTermination` ladder semantics, the drain-before-terminate case for `PaymentRun`, the measurement table | ✅ preserve the ordering rule, both traps and the Spring properties verbatim |
| §2.24 CPU profiling: `perf`, async-profiler, JFR | §7 mentions "a thread dump or profiler" | ✅ entire section — `perf_event_paranoid`, `PreserveFramePointer`, flame graphs, `AsyncGetCallTrace`, safepoint bias, the seccomp obstacle, the overhead budget | ✅ severely |
| §2.25 latency debugging with PSI, `runqlat`, `offcputime` | — | ✅ entire section — the other of the two highest-value gaps | |
| §2.26 utilisation, saturation and Little's Law | §2's more-threads point gestures at it | ✅ the queueing curve, why p99 collapses at 70–80%, the 30/80/150/500 ms QuizStakes budgets as capacity constraints | ✅ severely |
| §2.27 the failure catalogue | scattered across §4, §5, §12 | ✅ a single indexed catalogue: every exception string and symptom with its resource, its file, and its first command | ✅ |
| §3.1–§3.19 (all of PART 3) | §12 describes the OOM killer's scoring at a conceptual level; §3 describes the page cache correctly | ✅ **everything else**: boot to PID 1, `task_struct` and EEVDF, the syscall entry path, TLB shootdown, the fault handler, MGLRU, `oom_badness`, writeback internals, `blk-mq`, VFS internals, `epoll` internals, `io_uring` internals, `futex` and parking, signal delivery, cgroup and namespace internals, eBPF, where the JVM meets the kernel, and the five traced incidents | ✅ the OOM-scoring sentence is correct and must be preserved verbatim as the entry point to §3.7 |
| §4.1–§4.10 (all of PART 4) | — | ✅ entire part; the guide contains one 6-line shutdown-hook snippet and shell recipes, and nothing measurable | |
| §5.1–§5.3 (all of PART 5) | the 46-item atomic concept checklist | ✅ the 82-question bank, the 61 cold assertions, the output-reading and trace-to-the-kernel drills, the spaced-repetition schedule | ✅ the checklist is good and must be preserved **in full** inside §5.2.1 |
| **Rehome required** — current §9 (cron, `flock`, distributed cron, the four cron failures) | §9 in full, and 2 checklist lines | ✅ no syllabus section owns it; must be absorbed into §1.26 or handed to `19-docker-kubernetes.md` with an `[X-REF]` | |
| **Rehome required** — current §10 (SSH, keys, `~/.ssh/config`, `ProxyJump`, `-L`, `rsync`, SSM) | §10 in full, and 3 checklist lines | ✅ no syllabus section owns it; must become an operator-access appendix or be handed to `18-cloud-aws.md` with an `[X-REF]` | |
