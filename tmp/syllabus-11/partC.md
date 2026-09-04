---

# PART 2 — INTERMEDIATE

PART 1 named the mechanisms. PART 2 is where the operating system stops being trivia and becomes the
reason a JVM service misbehaves: every leaf here is a number, a cgroup file or a flag that decides
whether `FundsLedger` holds its 150 ms stake-reservation budget or `ClientRestrictions` breaches 30 ms.
The organising claim is that a Java service is a Linux process with unusually strong opinions about
memory and threads, and that almost every "mysterious" latency incident is the kernel and the JVM
disagreeing about a resource one of them thinks it owns.

## §2.1 The master cost tables

2.1.1 **The master memory-hierarchy table**, because every other cost in this guide is a multiple of
      these: register ~0.3 ns, L1d hit ~1 ns (4–5 cycles), L2 hit ~4 ns (~14 cycles), L3 hit ~15–40 ns
      (shared, and the number rises with core count), local DRAM ~80–100 ns, **remote NUMA-node DRAM
      ~140–200 ns**, NVMe SSD read ~80–150 µs, EBS gp3 read ~500 µs–1 ms, same-AZ network RTT ~0.5 ms,
      cross-AZ ~1 ms. Normalise the column to "L1 = 1 s" so the reader feels that a DRAM miss is a
      minute and an EBS read is a week. `[TABLE]` `[NUM]` `[CALC]`
2.1.2 **The syscall cost row, and why it grew.** A trivial syscall (`getpid`) was ~50–80 ns on
      pre-2018 hardware; with **KPTI** (Meltdown page-table isolation), retpoline/IBRS and the
      Spectre-v1 array-index mitigations the same call costs **~250–600 ns**, and the exact number is
      readable per-machine from `/sys/devices/system/cpu/vulnerabilities/*`. This is why a
      syscall-per-log-line design regressed twice as hard on post-2018 kernels. `[NUM]` `[PROC]`
      `[VERSION-TRAP]`
2.1.3 **`vDSO` is the exception that proves the cost is real**: `clock_gettime`, `gettimeofday` and
      `time` are served from a page mapped into every process (`ls -l /proc/self/map_files`, the
      `[vdso]` line in `/proc/self/maps`) with **no mode transition**, so `System.nanoTime()` costs
      ~20–30 ns rather than ~300 ns. State the corollary: on a VM whose `clocksource` has fallen back
      from `tsc` to `xen`/`acpi_pm`, the vDSO fast path is lost and `nanoTime()` becomes a real
      syscall — check `/sys/devices/system/clocksource/clocksource0/current_clocksource`. `[PROC]`
      `[NUM]` `[TRAP]`
2.1.4 **The context-switch row**: direct cost ~1–5 µs (register save/restore plus scheduler
      bookkeeping), thread-to-thread within one address space at the low end, process-to-process at
      the high end because page tables change and the TLB is flushed or PCID-tagged. Indirect cost —
      a cold L1/L2 for the incoming task — is typically **2–10× the direct cost** and does not show
      up in any counter. Measure the rate with `vmstat 1`'s `cs` column, attribute it per-process with
      `pidstat -w 1` (`cswch/s` = voluntary, `nvcswch/s` = involuntary). `[NUM]` `[DIAG]`
2.1.5 **The page-fault rows**: minor fault ~0.2–1 µs (page present in RAM, just not mapped here —
      COW after `fork`, first touch of a lazily-populated anonymous page, a shared library already in
      page cache); major fault = a minor fault **plus a device read**, so ~100 µs on NVMe and
      ~0.5–1 ms on EBS. Read them per-process from `/proc/<pid>/stat` fields 10 and 12 (`minflt`,
      `majflt`) or `ps -o min_flt,maj_flt -p <pid>`. `[NUM]` `[PROC]` `[SYSCALL]`
2.1.6 **The TLB row**: an L1-dTLB hit is free (part of the load), a miss served by the L2 TLB costs
      ~7–10 cycles, and a full **4-level page-table walk** on x86-64 costs up to 4 dependent memory
      accesses — ~100–300 ns if those lines are not cached. A 12 GB heap at 4 KB pages needs
      **3,145,728 page-table entries**; a typical L2 TLB holds ~1,500–2,000 entries, so a
      pointer-chasing GC mark phase over that heap misses the TLB on essentially every object.
      `[CALC]` `[NUM]` `[PROVE]`
2.1.7 **The futex row**: an uncontended lock acquire is a compare-and-swap, ~20 ns, **no syscall at
      all**; a contended acquire enters `futex(FUTEX_WAIT)` and the wake path
      (`futex(FUTEX_WAKE)` → scheduler → the woken thread runs) costs **~1–5 µs of latency and
      ~2–4 µs of CPU across both threads**. This is the entire justification for the JVM's
      thin-lock/spin-then-park design and for `-XX:+UseSpinWait`-style adaptive spinning. `[SYSCALL]`
      `[NUM]`
2.1.8 **The `fsync`/durability row**: `write()` to page cache ~1–5 µs per 4 KB and returns before
      anything is durable; `fsync()` on NVMe with a power-loss-protected cache ~100–500 µs; `fsync()`
      on **EBS gp3 ~0.7–1.5 ms**; `fsync()` on a spinning disk ~10 ms. `fdatasync()` skips the inode
      metadata write and is measurably cheaper for append-only files. State the consequence up front:
      any code path that `fsync`s per request cannot meet a 30 ms p99 at 1,200/sec on one device.
      `[SYSCALL]` `[NUM]` `[CALC]`
2.1.9 **The EBS/block-device row**: gp3 baseline **3,000 IOPS and 125 MB/s** included, provisionable
      to 16,000 IOPS / 1,000 MB/s; single-request latency ~0.5–1 ms; io2 Block Express single-digit-
      hundreds of µs. The arithmetic that matters: 3,000 IOPS ÷ 4 KB = 12 MB/s of *random* 4 KB work,
      so an fsync-heavy workload exhausts IOPS long before it exhausts throughput. `[NUM]` `[CALC]`
      `[X-REF 18]`
2.1.10 **The thread-cost row**: one platform thread = 1 MB reserved stack on Linux/x64 (`-Xss`
       default **1024 KB**, Linux/aarch64 **2048 KB**) of which typically 16–64 KB is ever touched, a
       `task_struct` plus kernel stack (~10–16 KB unswappable kernel memory), a slot in the run queue
       and roughly 2–4 µs of `clone()` cost. A virtual thread = a heap-allocated continuation,
       hundreds of bytes to a few KB, ~1 µs to create, and **no kernel object at all**. `[TABLE]`
       `[NUM]` `[API]`
2.1.11 **The QuizStakes budget arithmetic, worked.** `ClientRestrictions` has a **30 ms p99** budget
       and sits synchronously on deposit, stake and withdrawal. Spend it explicitly: ~1 ms same-AZ
       network in, ~0.5 ms TLS/framing, ~2 ms JDBC round trip to its own schema, leaving ~25 ms.
       A single **200 ms GC pause** consumes 6.6 budgets; **CFS throttling** of 60 ms in a 100 ms
       period consumes 2 budgets; one major page fault on EBS costs 4% of the budget and a thousand of
       them costs the whole thing. Conclusion the write pass must state: at 30 ms, *the OS is inside
       the budget*, not underneath it. `[CALC]` `[NUM]`
2.1.12 **The second budget worked: stake reservation at 150 ms p99, 1,200/sec sustained,
       3,400/sec settlement burst, against `FundsLedger`'s three instances.** 1,200/sec ÷ 3 = 400/sec
       per instance; at 150 ms each that is Little's-law **60 concurrent requests in flight per
       instance** (§2.26), which sets the floor on pool sizes and the ceiling on how much stack and
       socket-buffer memory the instance needs. At the 3,400/sec burst it is **170 in flight**, and
       the peak ledger write rate of **13,600/sec** is what the block device must absorb. `[CALC]`
       `[NUM]`
2.1.13 **The "what does a 12 GB heap cost the kernel" table** for `FundsLedger`: 12 GB heap → 3.15 M
       4 KB PTEs → ~24 MB of last-level page tables alone (8 bytes/PTE), plus ~1.5% of heap for G1
       remembered sets and ~1/64th of heap for the card table if it were parallel-scavenge, plus
       ~192 MB of GC-internal structures. Read the real figure from `/proc/<pid>/status`
       (`VmPTE:`, `VmRSS:`, `RssAnon:`, `RssFile:`) rather than guessing. `[PROC]` `[CALC]`
2.1.14 **The cost-table discipline leaf**: every number above is an order of magnitude, not a
       measurement of *your* machine, and the guide's rule is that any claim inside 3× must be
       measured. Name the measuring tools once, here: `perf stat -e
       task-clock,context-switches,page-faults,cycles,instructions,cache-misses,dTLB-load-misses`,
       `getconf PAGESIZE`, `lscpu --caches`, `numactl --hardware`, `fio --rw=randwrite --fsync=1`.
       `[BUILD]` `[DIAG]`

*(14 leaves)*

## §2.2 The JVM as a Linux process: reading its memory map

2.2.1 **`/proc/<pid>/maps` is the ground truth** and every JVM memory argument is settled by reading
      it. Format: `address-range perms offset dev inode pathname`, e.g.
      `00007f2c00000000-00007f2f00000000 rw-p 00000000 00:00 0` for a reserved-and-committed heap
      region and `7f2bd8021000-7f2bd8022000 ---p 00000000 00:00 0` for a **thread-stack guard page**.
      `[PROC]` `[SOURCE]`
2.2.2 **`/proc/<pid>/smaps` and `smaps_rollup`** add the per-mapping accounting that `maps` lacks:
      `Rss`, `Pss`, `Anonymous`, `AnonHugePages`, `Swap`, `Locked`, and the `VmFlags` line. `Pss`
      (proportional set size) is the only honest per-process number when mappings are shared, and
      `smaps_rollup` gives the whole-process total in one read instead of parsing thousands of
      mappings. `[PROC]` `[NUM]`
2.2.3 **The five numbers in `/proc/<pid>/status` that answer "how much memory is this JVM using":**
      `VmPeak`, `VmSize` (= VSZ, meaningless for a JVM), `VmHWM` (peak RSS — the number an OOM
      post-mortem needs), `VmRSS` with its `RssAnon`/`RssFile`/`RssShmem` breakdown, and `VmSwap`.
      **`RssAnon` is the JVM's real footprint**; `RssFile` is mostly mapped jars and the JDK's own
      shared objects. `[PROC]` `[NUM]`
2.2.4 **Reserve vs commit vs touch — the three-stage lifecycle of every JVM memory region.** The JVM
      `mmap`s the whole max heap `PROT_NONE` at startup (**reserve** — shows in VSZ, costs nothing),
      `mprotect`s regions to `PROT_READ|PROT_WRITE` as the heap grows (**commit** — still no physical
      pages), and physical frames appear only on first write (**touch** — a minor fault each). This
      is why RSS climbs for minutes after a restart under load and why `-XX:+AlwaysPreTouch` exists
      (§2.6). `[SYSCALL]` `[FLOW]` `[PROVE]`
2.2.5 **The anatomy of a JVM's map**, region by region, in the order they appear: the ELF text/data
      of `java` itself, the heap reservation (one large `rw-p` anonymous range), the metaspace and
      class-space reservations (a **1 GB compressed-class-space** reservation by default when
      compressed class pointers are on), the code cache (**240 MB** reserved by default with tiered
      compilation, 48 MB without), the CDS archive `classes.jsa` mapped read-only and shared, one
      `1 MB + guard page` mapping per platform thread, direct `ByteBuffer` mappings, `libjvm.so` and
      glibc, the `[vdso]`/`[vvar]` pages, and the main thread's `[stack]`. `[TABLE]` `[PROC]`
2.2.6 **Why VSZ is a lie and RSS is only most of the truth.** A 12 GB-heap `FundsLedger` instance
      routinely shows **VSZ > 20 GB** because reservations are free, while RSS is what the cgroup
      counts. But RSS also *under*states the container's charge: the kernel additionally charges page
      cache and kernel memory (socket buffers, dentries, page tables) to `memory.current`, so
      `memory.current` > RSS is normal and the OOM decision is made on the former (§2.11). `[TRAP]`
      `[PROVE]`
2.2.7 **`pmap -x <pid>` and `pmap -XX <pid>`** as the human-readable view, and the exact reading
      recipe: sort by RSS, look for the single largest anonymous mapping (heap), then count the 1 MB
      `rw-p` mappings (threads), then look for anything you cannot name — an unnamed multi-hundred-MB
      anonymous region that is not the heap is a native leak or an unreleased direct buffer.
      `[DIAG]` `[BUILD]`
2.2.8 **Native Memory Tracking is the JVM's side of the same ledger**: start with
      `-XX:NativeMemoryTracking=summary` (~5–10% overhead) and read it with
      `jcmd <pid> VM.native_memory summary scale=MB`, which itemises Java Heap, Class, Thread,
      Code, GC, Compiler, Internal, Symbol, Native Memory Tracking, Arena Chunk and Other with
      **reserved and committed** for each. The discipline: NMT `committed` total should account for
      most of `RssAnon`; the gap is malloc'd memory the JVM does not track (JNI, `libssl`, glibc
      arenas). `[API]` `[DIAG]` `[NUM]`
2.2.9 **`jcmd <pid> VM.native_memory baseline` then `... summary.diff`** is the leak-hunting
      procedure — a growing `Thread` category means thread leak, growing `Class` means classloader
      leak, growing `Internal`/`Other` means direct buffers or JNI. Show the diff output and read it.
      `[DIAG]` `[FLOW]`
2.2.10 **`vm.max_map_count` is a real ceiling on a JVM**: default **65530** mappings per process
       (`/proc/sys/vm/max_map_count`). Each thread's stack contributes mappings, as do
       `MappedByteBuffer`s, THP splits and `mprotect` fragmentation; exceeding it produces
       `mmap failed` in `hs_err` or `OutOfMemoryError: Map failed`, and it is the standard failure of
       a service that memory-maps thousands of segment files. Elasticsearch's famous
       `sysctl -w vm.max_map_count=262144` is this leaf. `[SYSCTL]` `[NUM]` `[RESEARCH]`
       (kernel `Documentation/admin-guide/sysctl/vm.rst`, `max_map_count`)
2.2.11 **glibc `malloc` arenas inflate RSS for a threaded JVM**: glibc creates up to
       **8 × ncores** arenas, each growing in 64 MB heaps on 64-bit, so a JVM on a 16-core host can
       hold hundreds of MB of freed-but-unreturned native memory. `MALLOC_ARENA_MAX=2` (or
       `-XX:MallocLimit`, or switching to jemalloc/tcmalloc) is the standard container fix, and the
       measurement is `RssAnon` minus NMT `committed`. `[NUM]` `[TRAP]` `[RESEARCH]`
2.2.12 **`/proc/<pid>/limits`, `/proc/<pid>/fd`, `/proc/<pid>/task` and `/proc/<pid>/io`** complete
       the process picture: the limits actually in force (not the shell's), the open fds, one
       directory per thread (`ls /proc/<pid>/task | wc -l` = live thread count, which should match
       `jcmd Thread.print`), and cumulative `read_bytes`/`write_bytes` actually issued to the block
       layer. `[PROC]` `[DIAG]`
2.2.13 **The one-command JVM footprint audit**, as a runnable shell block combining
       `grep -E 'VmHWM|VmRSS|RssAnon|VmSwap|VmPTE' /proc/$PID/status`,
       `cat /proc/$PID/smaps_rollup`, `jcmd $PID VM.native_memory summary scale=MB`,
       `ls /proc/$PID/task | wc -l`, `ls /proc/$PID/fd | wc -l` and
       `cat /sys/fs/cgroup/memory.current` — with a worked reading for a 12 GB-heap `FundsLedger`
       instance in a 16 GB container. `[BUILD]` `[CALC]`

*(13 leaves)*

## §2.3 JVM native memory: what lives outside the heap and how much

2.3.1 **The identity that must be memorised**: container RSS ≈ Java heap (committed, not max) +
      metaspace + compressed class space + code cache + thread stacks (touched, not reserved) +
      GC structures + direct/mapped buffers + JNI/native libs + glibc malloc arenas + JVM internal
      (symbols, compiler arenas). Write it as an equation with a per-term source of truth (NMT
      category or `/proc` path) next to each term. `[TABLE]` `[CALC]` `[PROVE]`
2.3.2 **Metaspace**: native, not heap; `-XX:MaxMetaspaceSize` is **unlimited by default**, which
      means a classloader leak exhausts the *container* rather than throwing. Typical steady state for
      a Spring Boot 3.5 service is **80–150 MB**; the tell of a leak is `jcmd <pid> VM.metaspace`
      showing a rising loader count. Set it explicitly in a container — an
      `OutOfMemoryError: Metaspace` with a heap dump beats a silent exit 137. `[NUM]` `[API]` `[TRAP]`
2.3.3 **Compressed class space** is a separate reservation, **1 GB by default**
      (`-XX:CompressedClassSpaceSize`), committed lazily, and it exists only while compressed class
      pointers are enabled. It is the largest single item in a naive VSZ-based capacity estimate and
      contributes almost nothing to RSS. `[NUM]` `[VERSION-TRAP]`
2.3.4 **Code cache**: `-XX:ReservedCodeCacheSize` default **240 MB** with tiered compilation,
      **48 MB** without, split into three segments (non-nmethod, profiled, non-profiled) when
      `-XX:+SegmentedCodeCache` is on (default with tiered). Exhaustion prints
      `CodeCache is full. Compiler has been disabled` and the service silently reverts to
      interpretation — a 10–50× throughput cliff with no error and no exception. Monitor
      `jcmd <pid> Compiler.codecache` or the `jvm.memory.used{area=nonheap,id=CodeCache}` meter.
      `[NUM]` `[TRAP]` `[API]`
2.3.5 **Thread stacks: reserved vs touched, and why `-Xss` is a capacity decision.**
      512 platform threads × 1 MB reserved = 512 MB of *virtual* address space but typically
      **16–48 MB resident**; the kernel-side `task_struct` + kernel stack is ~10–16 KB each and is
      **unswappable and charged to the cgroup**. The arithmetic that bites: a thread-per-request
      `ProfileService` fanning out to eight owners with a 400-thread pool commits ~40 MB of stacks and
      ~6 MB of kernel memory — small — while the same design at 20,000 threads does not fit at all.
      `[CALC]` `[NUM]`
2.3.6 **Direct byte buffers and `MaxDirectMemorySize`**: `ByteBuffer.allocateDirect` allocates
      outside the heap, is reclaimed only when its `Cleaner` runs (i.e. after the referring object is
      collected, which a full GC may be needed to notice), and defaults to **the same value as
      `-Xmx`** when `-XX:MaxDirectMemorySize` is unset. So a 12 GB heap implicitly permits a further
      12 GB of direct memory — a container-killer. Netty allocates here by default; so does every
      NIO socket write. `[API]` `[NUM]` `[TRAP]`
2.3.7 **`OutOfMemoryError: Direct buffer memory`** is a distinct diagnosis with a distinct fix:
      it means the *direct* limit was hit, not the heap, and it is usually leaked
      `ByteBuf`s (Netty's `-Dio.netty.leakDetection.level=paranoid` finds them) or an
      un-`close()`d `FileChannel.map`. Track it via
      `java.nio:type=BufferPool,name=direct` (`Count`, `MemoryUsed`, `TotalCapacity`) or
      `jcmd <pid> VM.native_memory` `Other`. `[DIAG]` `[API]`
2.3.8 **Mapped byte buffers are page cache, not process memory** — `FileChannel.map` costs
      address space and `RssFile`, is charged to the cgroup as page cache (and therefore *reclaimable*
      under pressure rather than OOM-triggering), and is unmapped only by GC. This is why a
      memory-mapped index behaves completely differently from a direct buffer of the same size under
      a container limit. `[PROVE]` `[X-REF 12]`
2.3.9 **GC structures scale with heap and are not free**: G1's remembered sets and card table run
      **~1–5% of heap** and can spike far higher under heavy cross-region referencing; ZGC's forwarding
      tables and mark stacks are similar; `jcmd <pid> VM.native_memory` reports them under `GC`. For
      `FundsLedger`'s 12 GB heap, budget **150–500 MB** of native GC overhead before any other native
      allocation. `[NUM]` `[CALC]`
2.3.10 **The container sizing rule, derived rather than asserted.** For a 16 GB `FundsLedger`
       container: reserve **~1 GB for the OS/agent/sidecar**, then subtract metaspace 150 MB +
       code cache 240 MB + GC 400 MB + stacks 100 MB + direct 512 MB + malloc slack 300 MB ≈ 1.7 GB
       of non-heap JVM native, leaving **~13.3 GB** — hence a heap of ~12 GB, i.e.
       `-XX:MaxRAMPercentage=75`. Show the same arithmetic failing for `ClientRestrictions` at 4 GB
       heap in a 5 GB container, where fixed native costs are ~35% of the container. `[CALC]` `[NUM]`
       `[PROVE]`
2.3.11 **`-XX:+PerfDisableSharedMem`** and the `/tmp/hsperfdata_*` mmap: the JVM writes its perf
       counters to a memory-mapped file, and on a container whose `/tmp` is on a slow or full
       overlay this causes **multi-second safepoint stalls**. Disabling it loses `jps`/`jstat`
       attachment by pid, which is the trade to state. `[TRAP]` `[NUM]`
2.3.12 **`-XX:+UseSerialGC` / `-XX:+UseZGC` change the native profile, not just pause behaviour**,
       and small containers (`ClientRestrictions` at 4 GB) are exactly where GC ergonomics pick badly:
       fewer than 2 CPUs *or* less than 1792 MB of memory silently selects **SerialGC**, which is
       almost never what a latency-sensitive service wants. `[VERSION-TRAP]` `[NUM]` `[X-REF 12]`
2.3.13 **The native-leak decision tree**: RSS rising while heap is flat → NMT baseline/diff → if
       `Thread` grows it is a thread leak (§2.4); if `Class` grows it is metaspace (§2.3.2); if
       `Internal`/`Other` grows it is direct buffers (§2.3.7); if none grows, it is untracked malloc —
       switch to jemalloc with `MALLOC_CONF=prof:true` and profile. `[FLOW]` `[DIAG]`

*(13 leaves)*

## §2.4 Threads in the JVM: platform threads, stack size, and pool sizing against real cores

2.4.1 **A platform `Thread` is one `clone()`d task with `CLONE_VM|CLONE_FS|CLONE_FILES|
      CLONE_SIGHAND|CLONE_THREAD|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID|
      CLONE_SYSVSEM`** — the JVM's 1:1 model made concrete. `strace -f -e trace=clone` on a starting
      JVM shows the flag word; the kernel sees no "thread", only a task in a thread group.
      `[SYSCALL]` `[SOURCE]`
2.4.2 **`Runtime.availableProcessors()` is the number every pool derives from**, and in a container
      it is *not* `nproc`: it is the JVM's container-aware CPU count (§2.12). Every default that
      depends on it: `ForkJoinPool.commonPool` parallelism = **n − 1**, G1's
      `ParallelGCThreads` = **n for n ≤ 8, then 8 + (n−8)×5/8**, `ConcGCThreads` = `ceil(ParallelGCThreads/4)`,
      `CICompilerCount`, the virtual-thread scheduler's parallelism = **n**, Netty's default event-loop
      group = **2n**, Tomcat's acceptor count. Get `availableProcessors()` wrong and all of them are
      wrong together. `[API]` `[NUM]` `[CALC]`
2.4.3 **Pool sizing for CPU-bound work**: threads ≈ cores, because past that point you buy only
      context switches and cache pollution. State the measurable symptom of overshoot: `vmstat`'s
      `cs` in the tens of thousands per second with `%sy` climbing and throughput flat or falling.
      `[PROVE]` `[DIAG]`
2.4.4 **Pool sizing for I/O-bound work — Little's law, not folklore.** threads =
      arrival_rate × service_time. For `ProfileService`'s eight-owner fan-out at, say, 200 requests/sec
      with a 120 ms slowest leg: **24 concurrent legs minimum**, and 8 outstanding calls per request
      means the *downstream* pool must hold 8 × 24. The classic wrong answer,
      `cores × (1 + wait/compute)`, gives the same number only when arrival rate happens to saturate
      the CPU. `[CALC]` `[NUM]` `[PROVE]`
2.4.5 **Bounded queues or bust.** `Executors.newFixedThreadPool` uses an **unbounded**
      `LinkedBlockingQueue`, which converts a downstream slowdown into an
      `OutOfMemoryError: Java heap space` hours later instead of a fast rejection now. The production
      shape is `ThreadPoolExecutor` with an explicit `ArrayBlockingQueue` capacity and
      `CallerRunsPolicy` or `AbortPolicy`; state the queue-depth-to-latency identity: a 1,000-deep
      queue drained at 400/sec adds **2.5 s** of latency before any work starts. `[API]` `[CALC]`
      `[TRAP]`
2.4.6 **`Executors.newCachedThreadPool` is unbounded in threads** — an `Integer.MAX_VALUE` maximum
      pool size — and under a hung downstream it will attempt to create tens of thousands of OS
      threads and fail with `OutOfMemoryError: unable to create native thread` (§2.11). Never in a
      service. `[API]` `[TRAP]`
2.4.7 **`OutOfMemoryError: unable to create native thread` is a *native* failure with a heap-shaped
      name.** It means `pthread_create`/`clone` returned `EAGAIN`, and the causes are, in order of
      frequency: the **`pids.max`** cgroup limit, `ulimit -u` (`RLIMIT_NPROC`),
      `kernel.threads-max`, `vm.max_map_count`, or genuinely exhausted address space/memory for the
      stack. Diagnose with `cat /sys/fs/cgroup/pids.max /sys/fs/cgroup/pids.current`,
      `cat /proc/<pid>/limits`, `ls /proc/<pid>/task | wc -l`. `[SYSCTL]` `[DIAG]` `[TRAP]`
2.4.8 **`-Xss` is a per-thread reservation and a recursion budget at the same time.** Lowering it to
      256 KB makes 20,000 threads addressable but makes a deep Jackson/Hibernate stack throw
      `StackOverflowError`; raising it to 8 MB fixes a recursive parser and quietly multiplies the
      address-space and `vm.max_map_count` cost. State the practical range (512 KB–1 MB) and the fact
      that the JVM's guard pages sit at the end of each stack mapping (visible as `---p` in
      `/proc/<pid>/maps`). `[NUM]` `[PROC]` `[TRAP]`
2.4.9 **Thread priority is mostly a no-op on Linux**: `Thread.setPriority` maps to nothing unless
      `-XX:+UseThreadPriorities -XX:ThreadPriorityPolicy=1` is set *and* the process has
      `CAP_SYS_NICE`. Real priority control is `nice`/`renice`, `chrt` (SCHED_FIFO/RR) and cgroup
      `cpu.weight` (§2.9) — not the Java API. `[TRAP]` `[API]`
2.4.10 **Naming threads is an operational requirement, not hygiene.** Every pool gets a
       `ThreadFactory` with a name pattern, because the only path from "one core is pegged" to "which
       code" is `top -H -p <pid>` → hot TID → `printf '%x\n' <tid>` → match `nid=0x…` in
       `jcmd <pid> Thread.print`. Show that chain end to end with a `FundsLedger` reservation-expiry
       thread as the culprit. `[FLOW]` `[DIAG]` `[BUILD]`
2.4.11 **Per-thread CPU attribution without a profiler**: `top -H`, `ps -eLo
       pid,tid,pcpu,comm --sort=-pcpu`, `pidstat -t 1 -p <pid>`, and `/proc/<pid>/task/<tid>/stat`
       fields 14/15 (`utime`/`stime` in clock ticks, `getconf CLK_TCK` = 100). `[PROC]` `[DIAG]`
2.4.12 **Thread-dump reading rules for a Linux-caused problem**, distinct from a lock-caused one:
       many threads `RUNNABLE` inside `SocketRead`/`epollWait` means the box is *waiting*, not busy
       (the JVM cannot see a syscall — §1); many `BLOCKED` on one monitor is contention; many
       `TIMED_WAITING` in `getTask` is an idle pool; a single `RUNNABLE` frame repeated across
       samples is a genuine hot spot. Take **three dumps 10 s apart** — one dump is a photograph, not
       a diagnosis. `[FLOW]` `[DIAG]`
2.4.13 **`jcmd <pid> Thread.print` vs `kill -3` vs `jstack -F`**: the first two are safepoint-based
       and require a responsive JVM; `-F` (force) uses the serviceability agent on a hung or
       partially-dead process and is the last resort. All three are free; capture before you kill
       (§1). `[API]` `[DIAG]`

*(13 leaves)*

## §2.5 Virtual threads and the kernel: carrier threads, pinning, and which blocking is invisible

2.5.1 **The model in one paragraph**: a virtual thread is a `Continuation` plus a scheduler; its
      stack lives on the **Java heap** as a chunk of frames, is copied out on `park` and back on
      `unpark`, and it executes on a **carrier** platform thread drawn from a dedicated
      `ForkJoinPool`. The kernel never sees it — `ls /proc/<pid>/task` counts carriers, not virtual
      threads. `[API]` `[PROVE]`
2.5.2 **The scheduler's real defaults**: a `ForkJoinPool` in **FIFO** mode with parallelism =
      `Runtime.availableProcessors()`, tunable by
      `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize`
      (default **256**), plus `jdk.virtualThreadScheduler.minRunnable`. Carrier threads are named
      `ForkJoinPool-1-worker-N` and are **daemon**. `[API]` `[NUM]` `[SYSCTL]`
2.5.3 **What blocking is *invisible* to the kernel (good) — the instrumented set.** Socket I/O
      (`java.net.Socket`, `SocketChannel`, `HttpClient`), `LockSupport.park`,
      `java.util.concurrent` locks and queues, `Thread.sleep`, `CompletableFuture.get`,
      `Selector.select`, and `Object.wait` **from JDK 24**: these unmount the virtual thread and free
      the carrier. State the mechanism — the JDK's `Poller`/`NIO` layer converts the blocking call
      into non-blocking + park. `[TABLE]` `[API]`
2.5.4 **What still pins, and therefore still burns a carrier and an OS thread.** After
      **JEP 491 (JDK 24)** removed `synchronized`-monitor pinning, the residue is: **native frames
      (JNI) and `Foreign` downcalls**, blocking inside a **class initializer**, and blocking while
      **waiting for another thread to initialise a class**. `[RESEARCH]` (OpenJDK JEP 491, "Pinning"
      section) `[VERSION-TRAP]`
2.5.5 **In JDK 21 — the LTS this guide targets — `synchronized` *does* pin**, and that is the single
      most important operational fact about virtual threads on 21: a virtual thread that blocks on
      I/O inside a `synchronized` block holds its carrier, and with parallelism = 8 it takes eight
      such threads to deadlock the entire scheduler. Diagnose with
      `-Djdk.tracePinnedThreads=full` (JDK 21) — **removed in JDK 24** because it became unnecessary.
      `[VERSION-TRAP]` `[TRAP]` `[NUM]` `[RESEARCH]`
2.5.6 **The pinning fix on 21 is `ReentrantLock`, not cleverness.** Show the before/after for a
      `FundsLedger` reservation path that synchronises around a JDBC call, and state the second-order
      point: `synchronized` is fine when it guards *only* in-memory work, because a non-blocking
      critical section never parks. `[BUILD]` `[API]`
2.5.7 **File I/O is the honest gap.** There is no non-blocking `read()` for regular files on Linux
      without `io_uring` (§2.18), so `FileInputStream`/`FileChannel` blocking is handled by
      **offloading to a separate thread pool** rather than by unmounting — meaning file-heavy work
      (`DocumentVerification` streaming 2–6 MB images) gets no benefit and may quietly consume
      `jdk.virtualThreadScheduler` capacity. `[TRAP]` `[X-REF 18]`
2.5.8 **`ThreadLocal` and pooling assumptions invert.** A million virtual threads × a 1 KB
      `ThreadLocal` value = **1 GB of heap** that a 200-thread pool never paid; and any code that
      caches per-thread expensive objects (`SimpleDateFormat`, a `ByteBuffer`, a Netty
      `PooledByteBufAllocator` arena) now allocates per *task*. `-Djdk.traceVirtualThreadLocals`
      helps find them; `ScopedValue` is the replacement. `[CALC]` `[API]` `[TRAP]`
2.5.9 **Virtual threads remove the thread limit and therefore expose the *next* limit.** Ten
      thousand concurrent virtual threads calling `ClientRestrictions` need ten thousand
      **connections and fds** (§2.16) and the downstream needs to absorb ten thousand concurrent
      requests. The correct pattern is an explicit `Semaphore` per downstream, sized to the
      downstream's capacity — the thread pool used to be the accidental limiter, and now it isn't.
      `[PROVE]` `[BUILD]` `[INCIDENT]`
2.5.10 **Virtual threads do not help CPU-bound work at all** and can hurt: parallelism is still
       `availableProcessors()`, and a CPU-bound task inside a virtual thread occupies a carrier for
       its whole duration with no unmount point (there is no preemption). `ForkJoinPool` /
       `parallelStream` remains the right tool. `[PROVE]` `[TRAP]`
2.5.11 **Observing virtual threads**: `jcmd <pid> Thread.dump_to_file -format=json <file>` (thread
       dumps that include virtual threads and group them by `StructuredTaskScope`) — a plain
       `Thread.print` does **not** list them. JFR events
       `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd`, `jdk.VirtualThreadPinned`,
       `jdk.VirtualThreadSubmitFailed` are the production telemetry. `[API]` `[DIAG]`
2.5.12 **`spring.threads.virtual.enabled=true` in Spring Boot 3.5** switches Tomcat's request
       executor and `@Async`/scheduling to virtual threads; state exactly what it does *not* change —
       JDBC drivers still block on a socket (fine) but the **connection pool** (HikariCP, fixed size)
       is now the sole limiter, and a fixed 20-connection pool behind unlimited virtual threads is a
       20-deep queue with unbounded waiters. `[API]` `[TRAP]` `[NUM]`
2.5.13 **The kernel-visible signature of a correctly-working virtual-thread service** is the
       diagnostic to memorise: a few dozen tasks in `/proc/<pid>/task`, tens of thousands of
       established sockets in `ss -s`, near-zero `cs` growth per request, and heap growth proportional
       to concurrency. Any of those inverted means pinning or offloading. `[DIAG]` `[PROVE]`

*(13 leaves)*

## §2.6 GC and the operating system: page faults, `AlwaysPreTouch`, THP, page-cache competition

2.6.1 **A GC is a memory-access pattern the kernel is badly placed to help.** A mark phase touches
      every live object in pseudo-random order, so it defeats prefetch, misses the TLB on nearly
      every access (§2.1.6) and, if any page is not resident, converts a 20 ms pause into a
      disk-bound one. State the design consequence: a GC's cost is set as much by the *residency and
      locality* of the heap as by its size. `[PROVE]`
2.6.2 **The startup page-fault storm, quantified.** With lazy commit, the first full traversal of a
      12 GB `FundsLedger` heap takes **3,145,728 minor faults** at ~0.5 µs each ≈ **1.6 s of pure
      fault time**, spread across the first minutes of traffic and visible as elevated p99 plus a
      climbing `minflt` in `/proc/<pid>/stat`. `[CALC]` `[NUM]` `[PROC]`
2.6.3 **`-XX:+AlwaysPreTouch`** writes a byte to every page of the heap at startup, so every fault
      is paid before the service accepts traffic: startup grows by roughly `heap / (pretouch
      bandwidth)` — **seconds for 12 GB** — and RSS immediately equals committed heap. Pair it with
      `-Xms == -Xmx` (otherwise you pre-touch only the initial heap) and with a readiness probe that
      does not time out during the pre-touch. It is the correct default for a long-lived,
      latency-sensitive service and the wrong default for a scale-to-zero one. `[API]` `[CALC]`
      `[TRAP]`
2.6.4 **`AlwaysPreTouch` interacts with the container limit, not just with latency.** Pre-touching
      makes the JVM's full memory demand visible at second 0, which means a container sized on
      *observed* steady-state RSS will be OOM-killed at startup instead of an hour in. That is a
      feature — fail fast, at deploy time, in the canary. `[PROVE]` `[X-REF 19]`
2.6.5 **`-XX:+UseCountedLoopSafepoints` / safepoint bias is an OS-visible effect**: reaching a
      safepoint requires *every* thread to arrive, so one thread descheduled by CFS throttling
      (§2.10) or a page fault stalls all of them. Enable
      `-Xlog:safepoint*:file=/var/log/qs/safepoint.log` and read `Reaching safepoint` vs
      `At safepoint` — a large *reaching* time is an OS problem, a large *at* time is a GC problem.
      `[DIAG]` `[API]` `[PROVE]`
2.6.6 **Time-to-safepoint pathologies caused by the OS**, enumerated: CFS throttling mid-safepoint,
      a swapped-out thread stack, `/tmp/hsperfdata` writeback on a full overlay (§2.3.11), THP
      compaction stalls (§2.7), and a `SIGSEGV`-based implicit null check hitting a paged-out page.
      Each has the same symptom — a pause far longer than the GC log's "user" time — and a different
      fix. `[TABLE]` `[TRAP]`
2.6.7 **The GC log's three time figures are a diagnosis**: `user` (CPU across GC threads), `sys`
      (kernel time — **should be near zero**; non-zero means page faults, THP compaction or
      swapping), `real` (wall clock). `real` ≫ `user/threads` means the GC threads were not
      *scheduled* — CPU starvation or throttling. Show a real
      `[gc,cpu] GC(412) User=1.84s Sys=0.91s Real=2.11s` line and read it. `[DIAG]` `[SOURCE]`
      `[NUM]`
2.6.8 **Page-cache competition is a real and under-appreciated cost.** Linux fills free RAM with
      page cache; inside a cgroup, page cache is charged to `memory.current`, so heavy log writing or
      a 68 GB/day document-image stream (`DocumentVerification`) pushes the cgroup toward
      `memory.high`, triggers reclaim, and reclaim competes with the JVM for CPU
      (`kswapd`/direct reclaim in `%sy`). `[PROVE]` `[NUM]`
2.6.9 **The JVM heap is anonymous memory and therefore *not* reclaimable** — the kernel can only
      swap it (§2.20) or OOM-kill. Page cache is reclaimable. This asymmetry is why a container under
      memory pressure sheds cache first (slowing I/O) and kills second (killing the service), and why
      `memory.high` throttling looks like a mysterious CPU cost. `[PROVE]` `[X-REF 12]`
2.6.10 **`madvise` and the JVM's uncommit behaviour**: G1 uncommits regions after a full GC and
       returns them with `MADV_DONTNEED`/`munmap`, dropping RSS; ZGC and Shenandoah do so
       proactively (`-XX:+ZUncommit`, `ZUncommitDelay=300` s). In a container this makes RSS *fall*,
       which breaks naive "RSS only ever grows" alerting and is the reason
       `-XX:+ShenandoahUncommit`-style flags matter for bin-packing. `[SYSCALL]` `[API]` `[NUM]`
2.6.11 **`vm.overcommit_memory` and the JVM's large reservations.** Default **0** (heuristic) lets
       the JVM reserve 20 GB of address space on a 16 GB box; setting **2** (strict, with
       `overcommit_ratio`) makes the JVM fail to *start* rather than fail later. Databases want 2;
       JVMs generally want 0 — and the failure mode of 2 with a large `-Xmx` is
       `Could not reserve enough space for object heap` on a machine with plenty of free RAM.
       `[SYSCTL]` `[NUM]` `[TRAP]`
2.6.12 **`min_free_kbytes` and `watermark_scale_factor` (default 10, i.e. 0.1% of node memory)**
       control how much headroom the kernel keeps before *direct* reclaim — the synchronous kind that
       stalls the allocating thread. On a memory-tight JVM host, raising `watermark_scale_factor` to
       100–200 trades a little RAM for far fewer direct-reclaim stalls. `[SYSCTL]` `[NUM]`
       `[RESEARCH]` (kernel `Documentation/admin-guide/sysctl/vm.rst`, `watermark_scale_factor`)
2.6.13 **`mlockall` is not available to a normal JVM** — there is no supported flag to pin the heap
       in RAM — which is why "just lock the heap" is not an answer to swapping and why §2.20's answer
       is to remove swap instead. `[TRAP]` `[PROVE]`

*(13 leaves)*

## §2.7 Huge pages and transparent huge pages: when they win and when they stall

2.7.1 **The arithmetic that motivates huge pages.** x86-64 supports 4 KB, **2 MB** and **1 GB**
      pages. A 12 GB heap needs 3,145,728 4 KB PTEs but only **6,144 2 MB PTEs** — a 512× reduction
      in page-table entries and TLB pressure, and ~24 MB → ~48 KB of last-level page tables. The
      payoff is measured in TLB miss rate, not in throughput directly. `[CALC]` `[NUM]` `[PROVE]`
2.7.2 **Explicit huge pages (`hugetlbfs`)**: pre-reserved at boot or via
      `vm.nr_hugepages` (`/proc/sys/vm/nr_hugepages`, default **0**), visible in
      `/proc/meminfo` as `HugePages_Total`, `HugePages_Free`, `Hugepagesize: 2048 kB`. They are
      **never swapped, never split, never reclaimed** — genuinely reserved RAM removed from the
      general pool. `[SYSCTL]` `[PROC]` `[NUM]`
2.7.3 **`-XX:+UseLargePages` uses explicit huge pages** and requires: enough `nr_hugepages`,
      the process's `RLIMIT_MEMLOCK` (`ulimit -l`) to permit it, and — for a non-root JVM —
      membership of `vm.hugetlb_shm_group`. If any precondition fails the JVM prints a warning and
      **silently falls back to 4 KB pages**, which is why "we enabled large pages" is a claim to
      verify in `-Xlog:pagesize` or `/proc/meminfo`, never to assume. `[API]` `[TRAP]` `[DIAG]`
2.7.4 **Transparent huge pages (THP)** are the kernel promoting 512 contiguous 4 KB pages to a 2 MB
      page automatically. Control file
      `/sys/kernel/mm/transparent_hugepage/enabled` with values `[always] madvise never`, and
      `/sys/kernel/mm/transparent_hugepage/defrag` with
      `always defer defer+madvise [madvise] never`. Amazon Linux 2023 ships `madvise`.
      `[PROC]` `[SYSCTL]` `[NUM]`
2.7.5 **`khugepaged` is the background promoter** (`/sys/kernel/mm/transparent_hugepage/khugepaged/*`,
      `pages_to_scan` default 4096, `scan_sleep_millisecs` default 10000, `alloc_sleep_millisecs`
      default 60000). It costs steady low CPU and occasionally holds `mmap_lock`, which is a
      time-to-safepoint hazard. `[PROC]` `[NUM]`
2.7.6 **`enabled=always` is the setting that causes the famous stalls**, and the mechanism must be
      stated precisely: an allocation that needs a 2 MB page and cannot find 512 contiguous free 4 KB
      pages triggers **synchronous compaction** in the allocating thread — page migration under
      locks, hundreds of milliseconds, attributed to your thread. Symptom: multi-hundred-ms pauses
      with high `%sy`, `compact_stall` rising in `/proc/vmstat`, and a
      `perf top` dominated by `compaction_alloc`/`migrate_pages`. `[TRAP]` `[DIAG]` `[PROC]`
2.7.7 **The historical database guidance ("always disable THP") is version-stale for a JVM.**
      MongoDB, Redis and Oracle documented `never` because of fork-heavy COW and latency spikes.
      For a JVM the modern answer is `madvise` + `-XX:+UseTransparentHugePages`, so the JVM asks for
      huge pages **only for the heap** (via `madvise(MADV_HUGEPAGE)`) and nothing else in the process
      is promoted. `[VERSION-TRAP]` `[RESEARCH]` `[API]`
2.7.8 **`-XX:+UseTransparentHugePages` is documented as disabled by default and "made available for
      experimentation"**, and in JDK 21 it issues `madvise(MADV_HUGEPAGE)` over the heap reservation
      rather than requiring `hugetlbfs`. `[RESEARCH]` (JDK 21 `java` man page,
      `-XX:+UseTransparentHugePages`) `[API]` `[VERSION-TRAP]`
2.7.9 **THP + `AlwaysPreTouch` is the combination that actually works**, and the reason is
      mechanical: pre-touching at startup finds memory unfragmented, so the 2 MB allocations succeed
      cheaply and the heap ends up genuinely backed by huge pages; pre-touching *without* THP wastes
      the opportunity, and THP *without* pre-touching pays compaction later, under load. Verify with
      `AnonHugePages:` in `/proc/<pid>/smaps_rollup` ≈ committed heap. `[PROVE]` `[PROC]` `[CALC]`
2.7.10 **Where THP actively hurts**: `fork()`-heavy processes (COW at 2 MB granularity copies 512×
       more than needed — the Redis `bgsave` pathology), memory-tight containers (internal
       fragmentation wastes up to 2 MB per sparse mapping), and short-lived JVMs where compaction cost
       is never amortised. `[TRAP]` `[TABLE]`
2.7.11 **1 GB pages exist and are almost never right for a JVM**: `hugepagesz=1G hugepages=N` on the
       kernel command line only, no runtime reservation, and a granularity that makes a 12 GB heap a
       12-page object with brutal rounding. Mention for completeness and to close the question.
       `[NUM]`
2.7.12 **The measurement that settles any huge-page argument**:
       `perf stat -e dTLB-load-misses,dTLB-store-misses,iTLB-load-misses,cycles,instructions -p <pid>`
       before and after, plus `grep -E 'AnonHugePages|thp' /proc/meminfo /proc/vmstat`. Typical
       honest result for a large-heap JVM: **2–10% throughput, and a larger reduction in GC mark-phase
       time** — worth having, not transformative. `[DIAG]` `[NUM]` `[BUILD]`

*(12 leaves)*

## §2.8 NUMA: topology, node-local allocation, `numactl`, and the JVM's NUMA options

2.8.1 **NUMA in one sentence with the number that matters**: on a multi-socket machine each socket
      has its own memory controller, and a load from the *remote* node's DRAM costs
      **~1.5–2.2× local latency** (≈90 ns local vs ≈160–200 ns remote) with lower bandwidth and
      contention on the interconnect (UPI/Infinity Fabric). `[NUM]` `[PROVE]`
2.8.2 **Reading the topology**: `numactl --hardware` (nodes, per-node MB free, and the **distance
      matrix** where 10 = local and 21 = one hop), `lscpu` (`NUMA node0 CPU(s): 0-31,64-95`),
      `/sys/devices/system/node/node*/{meminfo,cpulist,distance}`. Show a real two-node
      `r6i.8xlarge`-shaped output and read every field. `[DIAG]` `[PROC]` `[SOURCE]`
2.8.3 **Which EC2 shapes are actually NUMA.** Instances up to and including one socket
      (`m6i.16xlarge` and below) present a **single node** and the whole topic is moot;
      `.24xlarge`/`.32xlarge`/`metal` shapes present two. State the operational rule: check
      `numactl --hardware` before spending any effort — most QuizStakes services run on shapes with
      one node. `[NUM]` `[TRAP]` `[X-REF 18]`
2.8.4 **The kernel's default policy is `MPOL_DEFAULT` — first-touch local**: a page is allocated on
      the node of the CPU that first *writes* it, not the node that allocated the virtual range. The
      consequence for a JVM: with `-XX:+AlwaysPreTouch` and no NUMA awareness, whichever thread
      pre-touches owns the placement, so the entire heap can land on **one node** and half the cores
      then run remote. `[SYSCALL]` `[PROVE]` `[TRAP]`
2.8.5 **`-XX:+UseNUMA`** makes the collector NUMA-aware — Parallel GC splits the young generation
      into per-node **eden partitions** so a thread allocates on its own node; G1 has
      `-XX:+UseNUMA` support that distributes *young* regions across nodes on an interleave basis.
      ZGC is NUMA-aware in its page allocation. `-XX:+UseNUMAInterleaving` interleaves the whole
      reservation instead, which trades peak locality for predictability. `[API]` `[NUM]`
2.8.6 **The honest limit of JVM NUMA support**: objects are *not* migrated when a thread moves, and
      old-generation regions have no node affinity, so a long-lived structure like `FundsLedger`'s
      reservation index ends up wherever it was promoted. NUMA tuning helps allocation-heavy young-gen
      workloads (`ClientRestrictions`) far more than it helps long-lived-state workloads. `[PROVE]`
      `[TRAP]`
2.8.7 **`numactl` as the blunt, reliable instrument**:
      `numactl --cpunodebind=0 --membind=0 java -jar …` (pin CPU and memory to node 0),
      `--interleave=all` (round-robin every page — the standard answer for a JVM that spans nodes),
      `--preferred=0`, `--localalloc`. The container-era equivalent is one JVM per node, each pinned,
      instead of one JVM spanning both. `[BUILD]` `[API]`
2.8.8 **`cpuset.cpus` and `cpuset.mems` are the cgroup v2 way** (§2.9), and Kubernetes exposes them
      through the **CPU Manager `static` policy** (requires integer CPU requests and
      `Guaranteed` QoS) and the **Topology Manager** (`single-numa-node` policy). For
      `FundsLedger`'s three pause-sensitive instances this is the correct lever, not `numactl` in an
      entrypoint script. `[SYSCTL]` `[API]` `[X-REF 19]`
2.8.9 **`vm.zone_reclaim_mode` (disabled by default)** is the NUMA trap that used to bite: when
      enabled, the kernel reclaims *locally* rather than allocating remotely, which on a
      page-cache-heavy box causes needless reclaim and latency. Default off is correct; verify it
      rather than assuming, since some tuned profiles set it. `[SYSCTL]` `[RESEARCH]`
      (kernel `Documentation/admin-guide/sysctl/vm.rst`, `zone_reclaim_mode`) `[TRAP]`
2.8.10 **`vm.numa_balancing`** (`/proc/sys/kernel/numa_balancing`) periodically unmaps pages to
       sample which node touches them and migrates accordingly. It costs minor faults and page
       migrations — visible as `numa_pages_migrated` in `/proc/vmstat` and as unexplained `%sy` — and
       for a pinned, latency-sensitive JVM the right setting is **off**, with placement decided
       statically. `[SYSCTL]` `[PROC]` `[TRAP]`
2.8.11 **Per-node measurement**: `numastat -p <pid>` (per-node MB for one process — the fastest way
       to prove a heap is single-node), `/proc/<pid>/numa_maps`,
       `perf stat -e node-load-misses`, and `/sys/devices/system/node/node*/numastat`
       (`numa_hit`, `numa_miss`, `numa_foreign`, `other_node`). A rising `numa_miss` with flat
       `numa_hit` is remote allocation. `[DIAG]` `[PROC]` `[NUM]`
2.8.12 **When NUMA is the answer and when it is a distraction**, stated as a decision rule: it
       matters when (a) `numactl --hardware` shows ≥2 nodes, (b) the heap is large enough to span
       them, and (c) `perf` shows a memory-bound profile. Otherwise the effort belongs in §2.10
       (throttling) or §2.21 (I/O), which cause far more QuizStakes incidents. `[PROVE]` `[TRAP]`

*(12 leaves)*

## §2.9 cgroups v2: the controllers, the interface files, and the defaults that matter

2.9.1 **The unified hierarchy in one paragraph**: cgroup v2 is a **single tree** mounted at
      `/sys/fs/cgroup` (`cgroup2` filesystem), in which a process belongs to exactly one cgroup and
      *all* controllers apply at that node — as opposed to v1's per-controller trees where a process
      could sit at different depths for `memory` and `cpu`. Detect which you are on:
      `stat -fc %T /sys/fs/cgroup` → `cgroup2fs` (v2) or `tmpfs` (v1). `[PROC]` `[VERSION-TRAP]`
2.9.2 **The controller list**: `cpu`, `cpuset`, `io`, `memory`, `pids`, `hugetlb`, `rdma`, `misc`,
      `perf_event`. Which are *enabled* at a node is `cgroup.controllers` (available) and
      `cgroup.subtree_control` (delegated to children) — and a controller absent from
      `cgroup.controllers` on Amazon Linux 2023 is a kernel-config or delegation problem, not a
      missing feature. `[PROC]` `[RESEARCH]` (kernel `Documentation/admin-guide/cgroup-v2.rst`,
      "Controllers")
2.9.3 **The no-internal-process constraint**: a non-root cgroup with children may not itself contain
      processes when controllers are enabled — which is exactly why systemd's tree is all leaves
      (`system.slice/docker-<id>.scope`) and why hand-built hierarchies fail with `EBUSY`.
      `[TRAP]` `[PROVE]`
2.9.4 **The memory controller's five limits, with defaults**: `memory.max` = **`max`** (hard limit;
      exceeding it triggers reclaim then OOM kill), `memory.high` = **`max`** (soft limit; exceeding
      it triggers *throttled* reclaim in the allocating task rather than a kill),
      `memory.low` = **`0`** (best-effort protection), `memory.min` = **`0`** (hard protection,
      unreclaimable), `memory.swap.max` = **`max`**. `memory.current` and `memory.peak` are the
      readings. `[SYSCTL]` `[NUM]` `[RESEARCH]` (cgroup-v2.rst, "Memory Interface Files")
2.9.5 **`memory.high` is the single most useful and least-used file.** It converts an OOM kill into
      *slowness*: the kernel reclaims aggressively and applies an artificial allocation delay to
      tasks in the cgroup. For a JVM this looks like CPU time appearing in `%sy` and latency
      degrading with no GC explanation — so it must be monitored via `memory.events`'s `high`
      counter, not inferred. Kubernetes does **not** set it by default (memory requests map to
      nothing on the memory controller unless `MemoryQoS` is enabled). `[TRAP]` `[NUM]` `[X-REF 19]`
2.9.6 **`memory.events` is the forensic file**, with counters `low`, `high`, `max`, `oom`,
      `oom_kill`, and `oom_group_kill`. `oom_kill` > 0 is *proof* that the kernel killed something in
      this cgroup; `max` > 0 with `oom_kill` = 0 means the cgroup hit its ceiling and reclaimed its
      way out. `memory.events.local` scopes the same counters to the cgroup itself rather than
      descendants. `[PROC]` `[DIAG]` `[RESEARCH]` (cgroup-v2.rst, `memory.events`)
2.9.7 **`memory.oom.group` (default `0`)** makes the cgroup an OOM *unit*: on kill, every process in
      it dies together rather than the kernel picking the fattest. Kubernetes 1.28+ sets it for
      pod-level cgroups, which is why a sidecar can now be killed alongside the JVM and why exit-code
      forensics must look at the whole pod. `[SYSCTL]` `[NUM]` `[VERSION-TRAP]`
2.9.8 **`memory.stat` is the breakdown that explains `memory.current`**: `anon` (the JVM heap and
      stacks — unreclaimable), `file` (page cache — reclaimable), `kernel`, `slab_reclaimable`,
      `sock`, `pgfault`/`pgmajfault`, `pgscan`/`pgsteal`, `thp_fault_alloc`,
      `workingset_refault_anon`. The reading rule: if `anon` ≈ `memory.max` you have a JVM sizing
      problem; if `file` is large you have a page-cache-competition problem (§2.6.8). `[PROC]`
      `[TABLE]` `[DIAG]`
2.9.9 **The `cpu` controller files with defaults**: `cpu.max` = **`max 100000`** (`$QUOTA $PERIOD`
      in µs), `cpu.max.burst` = **`0`**, `cpu.weight` = **`100`** (range 1–10000, the v2 rendering of
      v1 `cpu.shares` where weight ≈ shares/1024×100), `cpu.weight.nice`, `cpu.pressure`, and
      `cpu.idle`. `[SYSCTL]` `[NUM]` `[RESEARCH]` (cgroup-v2.rst, "CPU Interface Files")
2.9.10 **`cpu.stat` is the throttling evidence**: `usage_usec`, `user_usec`, `system_usec`,
       `nr_periods`, `nr_throttled`, `throttled_usec`, `nr_bursts`, `burst_usec`. The one derived
       metric worth alerting on is **`nr_throttled / nr_periods`** — any sustained value above a few
       percent on a latency-sensitive service is a defect (§2.10). `[PROC]` `[CALC]` `[RESEARCH]`
2.9.11 **`cpuset.cpus` / `cpuset.mems` / `cpuset.cpus.partition`** pin a cgroup to specific CPUs and
       NUMA nodes; `cpuset.cpus.effective` shows what actually applies after intersection with the
       parent. This is how a `Guaranteed`-QoS `FundsLedger` pod gets exclusive cores under the
       Kubernetes CPU Manager `static` policy (§2.8.8). `[SYSCTL]` `[X-REF 19]`
2.9.12 **`pids.max` (default `max`), `pids.current`, `pids.peak`, `pids.events`** — the limit that
       produces `OutOfMemoryError: unable to create native thread` in a container whose author never
       thought about threads. Kubernetes exposes it as the kubelet's `podPidsLimit` (default
       **4096** on many distributions). `[SYSCTL]` `[NUM]` `[TRAP]`
2.9.13 **`io.max`, `io.weight` (default `default 100`), `io.stat`, `io.latency`, `io.pressure`** and
       the crucial caveat: `io.max` throttling applies reliably only to **direct** I/O and to
       writeback attributed to the cgroup; buffered writes are charged when the flusher runs, so a
       JVM's log writes can escape the limit and land on a neighbour. `[SYSCTL]` `[TRAP]`
       `[RESEARCH]` (cgroup-v2.rst, "IO Interface Files")
2.9.14 **`*.pressure` files expose per-cgroup PSI** (`cpu.pressure`, `memory.pressure`,
       `io.pressure`) in the same `some`/`full avg10= avg60= avg300= total=` format as
       `/proc/pressure/*`, where **`some`** = at least one task stalled and **`full`** = all non-idle
       tasks stalled. This is the single best "is the container starved" signal and is far more
       actionable than CPU utilisation. `[PROC]` `[NUM]` `[RESEARCH]`
       (kernel `Documentation/accounting/psi.rst`)
2.9.15 **Where a container's own files actually are, from inside the container**: with cgroup
       namespaces (§2.13) the container sees its own cgroup as `/sys/fs/cgroup/` root, so the
       one-liner audit is `cat /sys/fs/cgroup/{memory.max,memory.current,memory.events,cpu.max,cpu.stat,pids.max}`
       — and `cat /proc/self/cgroup` shows the path (`0::/` under a cgroup namespace, a full
       `/kubepods.slice/...` path without one). `[BUILD]` `[PROC]` `[DIAG]`

*(15 leaves)*

## §2.10 CPU throttling: `cpu.max`, periods, quota, and `throttled_time`

2.10.1 **The mechanism, stated exactly.** CFS bandwidth control gives the cgroup `QUOTA` µs of CPU
       time per `PERIOD` µs. Consumption is summed across **all threads**, so eight threads exhaust
       the quota eight times faster than one. When the quota is gone, every runnable thread in the
       cgroup is **removed from the run queue until the next period boundary** — not slowed, stopped.
       `[FLOW]` `[PROVE]`
2.10.2 **`cpu.max` syntax and the Kubernetes mapping**: `cpu.max` = `$QUOTA $PERIOD`, default
       `max 100000` (100 ms period). A Kubernetes `limits.cpu: 0.4` becomes `40000 100000`; `2`
       becomes `200000 100000`. `cpu.weight` carries `requests.cpu`, so **requests affect
       contention and limits affect throttling** — two entirely different mechanisms routinely
       conflated. `[SYSCTL]` `[NUM]` `[CALC]` `[X-REF 19]`
2.10.3 **The worked arithmetic the brief demands: a 100 ms period with a 40 ms quota against eight
       runnable threads.** Eight threads each wanting CPU consume 40 ms of quota in **5 ms of wall
       clock**; the cgroup is then frozen for the remaining **95 ms**. Average CPU utilisation
       measured over a second reads **40%** — comfortably "under-utilised" — while any request
       unlucky enough to be in flight at the freeze takes **up to 95 ms extra**. That is the whole
       phenomenon: p99 collapses while the utilisation dashboard says there is headroom. `[CALC]`
       `[NUM]` `[PROVE]` `[TRAP]`
2.10.4 **Applied to `ClientRestrictions` and its 30 ms budget**: a single 95 ms stall is
       **3.2× the entire p99 budget**, and because `ClientRestrictions` sits on every money path, the
       breach propagates to the 150 ms stake reservation and the hard 500 ms self-exclusion guarantee.
       A service with a tight budget must either have no CPU limit or a limit generous enough that the
       quota is never exhausted within a period. `[CALC]` `[INCIDENT]`
2.10.5 **The evidence chain**: `cpu.stat`'s `nr_periods`, `nr_throttled` and `throttled_usec` (v2) —
       or `cpu.cfs_throttled_time`/`nr_throttled` in v1's `cpu.stat` — plus the derived
       **throttled fraction** `nr_throttled/nr_periods` and **mean stall** `throttled_usec/nr_throttled`.
       In Prometheus terms: `rate(container_cpu_cfs_throttled_periods_total[5m]) /
       rate(container_cpu_cfs_periods_total[5m])`. `[PROC]` `[DIAG]` `[CALC]`
2.10.6 **Shrinking the period is the classic mitigation and it is a trade, not a fix.**
       `cpu.cfs_period_us` down to 10 ms (`10000`) with proportionally reduced quota caps the worst
       stall at ~10 ms instead of ~95 ms, at the cost of more scheduler bookkeeping. Kubernetes
       exposes this as the kubelet's `cpuCFSQuotaPeriod` (alpha `CustomCPUCFSQuotaPeriod`), which is
       node-wide — you cannot set it per pod. `[SYSCTL]` `[NUM]` `[TRAP]` `[X-REF 19]`
2.10.7 **`cpu.max.burst` (default `0`)** lets unused quota accumulate up to the burst value and be
       spent in a later period, which directly addresses bursty request-response services. State the
       limit: burst cannot exceed quota, and it smooths spikes rather than raising the average.
       `[SYSCTL]` `[NUM]` `[RESEARCH]` (cgroup-v2.rst, `cpu.max.burst`)
2.10.8 **The historical per-CPU-slice throttling bug**, because it is still repeated as advice:
       pre-**4.18** kernels distributed quota to per-CPU run queues in 5 ms slices and leaked
       unused remainder, so multi-threaded processes were throttled at well under their nominal
       quota. Fixed in 4.18 (and backported); on a 6.12 kernel the bug does not exist and the
       remaining throttling is real. `[VERSION-TRAP]` `[NUM]`
2.10.9 **Fractional CPU limits are the ones that break the JVM twice.** `limits.cpu: 0.4` throttles
       *and* — because the JVM computes `availableProcessors()` from `ceil(quota/period)` — reports
       **1** processor, selecting SerialGC (below 2 CPUs and 1792 MB, §2.3.12), a
       `commonPool` parallelism of **0**, `ParallelGCThreads`=1, and a virtual-thread scheduler
       parallelism of 1. One config line changes the garbage collector. `[TRAP]` `[NUM]` `[CALC]`
2.10.10 **The GC-thread interaction is the reason throttling is worse for a JVM than for a Go or
        Node service.** A stop-the-world pause with `ParallelGCThreads=8` needs 8 CPU-seconds' worth
        of quota in a few hundred milliseconds; if the quota is 0.4 CPU the pause is stretched across
        many periods, so a 50 ms pause becomes a **multi-second** one, and the GC log shows
        `Real` ≫ `User/threads` (§2.6.7). `[PROVE]` `[CALC]` `[INCIDENT]`
2.10.11 **"Remove CPU limits" is a defensible position and must be argued, not asserted.** Without
        limits, `requests` (via `cpu.weight`) still guarantee a share under contention, and the pod
        can use idle capacity — better p99, worse isolation and worse capacity predictability. The
        rule to state: keep limits for batch and untrusted workloads (`BankDeposits` ingestion,
        `InternalPlatforms`), drop or greatly over-provision them for latency-critical ones
        (`ClientRestrictions`, `FundsLedger`). `[PROVE]` `[TABLE]`
2.10.12 **Throttling vs steal vs starvation — the disambiguation table.** Throttling:
        `nr_throttled` rising, `%st` = 0, host idle. Steal: `%st` > 0 in `top`, nothing in
        `cpu.stat`. Starvation by neighbours: `cpu.pressure` `some` rising, run-queue length
        (`/proc/schedstat`, `sar -q`) high, no throttling. Each has a different fix and they are
        constantly confused. `[TABLE]` `[DIAG]` `[TRAP]`
2.10.13 **The reproduction, so the reader can see it once**: a container with
        `cpu.max = 40000 100000`, a Java 21 program spinning eight threads for 200 ms per "request",
        and a histogram of response times showing the bimodal distribution with a mode near the
        period boundary. Then the same program with `cpu.max = max 100000`. `[BUILD]` `[DIAG]`

*(13 leaves)*

## §2.11 Container memory limits: cgroup OOM vs global OOM vs JVM `OutOfMemoryError`

2.11.1 **The three-way distinction, as a table, because conflating them costs hours.** Rows:
       *who acts*, *what resource ran out*, *what the process does*, *what evidence exists*,
       *whether a heap dump is possible*, *typical fix*. Columns: **global OOM killer**,
       **cgroup OOM kill**, **JVM `OutOfMemoryError`**. This table is the section. `[TABLE]`
       `[PROVE]`
2.11.2 **Evidence set 1 — cgroup OOM kill.** Exit code **137** (128 + SIGKILL 9), pod state
       `OOMKilled` with `reason: OOMKilled` in `kubectl describe`, a `dmesg -T` line of the shape
       `Memory cgroup out of memory: Killed process 1234 (java) total-vm:20971520kB,
       anon-rss:16250880kB, file-rss:24576kB, shmem-rss:0kB, UID:1000 pgtables:33792kB
       oom_score_adj:968`, and `memory.events`'s **`oom_kill`** counter incremented. Read every field
       of that line — `anon-rss` is the JVM's real footprint and `pgtables` is §2.1.13 made visible.
       `[DIAG]` `[SOURCE]` `[NUM]`
2.11.3 **Evidence set 2 — global (host) OOM kill**, distinguished by the `dmesg` header
       `Out of memory: Killed process …` *without* the `Memory cgroup` prefix, preceded by a
       full task list and `oom_score` values. The cause is host over-commitment (sum of limits >
       node capacity, or a process outside any limited cgroup), and the victim is often **not** the
       guilty process. `[DIAG]` `[TRAP]`
2.11.4 **`oom_score` and `oom_score_adj`**: the kernel scores candidates roughly proportionally to
       RSS + swap + page tables, normalised to 0–1000, adjusted by
       `/proc/<pid>/oom_score_adj` (−1000 = never kill, +1000 = kill first). Kubernetes sets it by
       QoS class: **`Guaranteed` → −997**, `BestEffort` → **1000**, `Burstable` → a value scaled
       between 2 and 999 from the memory request. This is why a `Burstable` `ProfileService` dies
       before a `Guaranteed` `FundsLedger`. `[PROC]` `[NUM]` `[X-REF 19]`
2.11.5 **Evidence set 3 — `java.lang.OutOfMemoryError: Java heap space`.** The JVM threw an
       `Error` after GC failed to free enough: there is a **stack trace**, shutdown hooks may run, a
       heap dump is possible, and the exit code is whatever the application chooses (often 1, or 0 if
       something catches it — the worst case). `[DIAG]` `[API]`
2.11.6 **The other `OutOfMemoryError` messages and what each really means**, as a table:
       `Java heap space` (heap), `GC overhead limit exceeded` (>98% of time in GC recovering <2%),
       `Metaspace` / `Compressed class space` (§2.3.2–3), `Direct buffer memory` (§2.3.7),
       `unable to create native thread` (§2.4.7 — a *native* limit), `Requested array size exceeds
       VM limit` (>~2^31−3 elements), `Map failed` (`mmap` refused — `vm.max_map_count` or address
       space), `Out of swap space?` (the JVM's malloc failed — a genuine native exhaustion, usually
       preceding a cgroup kill). `[TABLE]` `[NUM]` `[TRAP]`
2.11.7 **Why a container OOM kill produces *no* heap dump, stated mechanically.** The kernel delivers
       an uncatchable **SIGKILL**; there is no unwinding, no shutdown hook, no
       `HeapDumpOnOutOfMemoryError` handler, and — crucially — writing a 12 GB heap dump would
       itself require memory and disk the container does not have. The only pre-mortem options are
       continuous heap-usage telemetry, JFR with a `dumponexit` recording on an
       `emptyDir`, or a `preStop` hook that dumps. `[PROVE]` `[TRAP]`
2.11.8 **`-XX:+ExitOnOutOfMemoryError` and `-XX:+CrashOnOutOfMemoryError`.** The first exits the JVM
       immediately on the *first* `OutOfMemoryError` (exit code 3 by default) instead of limping on
       with one dead thread; the second produces an `hs_err_pid<pid>.log` and a core file. Combine
       with `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps` and
       `-XX:OnOutOfMemoryError='kill -9 %p'` only if you understand the ordering. The default —
       catch nothing, exit nothing — leaves a service that is up, failing readiness intermittently,
       and impossible to diagnose. `[API]` `[NUM]` `[TRAP]`
2.11.9 **The single most common misdiagnosis, spelled out**: `-Xmx` set equal to the container
       memory limit. Heap is only one term of §2.3.1, so the container is exceeded by non-heap native
       memory while the heap never fills — meaning **no `OutOfMemoryError`, no stack trace, exit
       137**, and an engineer spending a day looking for a Java memory leak that does not exist.
       `[TRAP]` `[INCIDENT]` `[CALC]`
2.11.10 **The inverse misdiagnosis**: `-Xmx` far below what the container allows, so the JVM throws
        `Java heap space` while `memory.current` sits at 45% of `memory.max`. The tell is a heap dump
        that exists *and* a cgroup with headroom. Fix the heap, not the limit. `[TRAP]` `[DIAG]`
2.11.11 **The reclaim staircase before the kill** — the sequence a container actually walks:
        allocation → `memory.high` breached → throttled direct reclaim (page cache dropped,
        anonymous pages swapped if `memory.swap.max` > 0) → `memory.max` breached → attempted reclaim
        → **cgroup OOM kill**. Each step has a counter (`memory.events`, `memory.stat`'s
        `pgscan`/`pgsteal`, `memory.pressure`) so the pre-kill minutes are always visible in
        hindsight — if you collected them. `[FLOW]` `[PROC]` `[PROVE]`
2.11.12 **The `dmesg` access problem in a container** is worth its own leaf: `dmesg` inside a
        container usually returns nothing (`/dev/kmsg` is not namespaced and often not permitted), so
        the OOM line must be read from the node — `kubectl debug node/…`, the CloudWatch/journald
        node log, or `kubectl get events --field-selector reason=OOMKilling`. `[TRAP]` `[DIAG]`
        `[X-REF 19]`
2.11.13 **The forensic checklist for "the pod restarted and nobody knows why"**, in order:
        `kubectl describe pod` → `lastState.terminated.exitCode` and `reason`;
        exit **137** → cgroup or host OOM, go to `dmesg`/`memory.events`;
        exit **143** (128+15) → it received SIGTERM and exited, i.e. an eviction or a rollout, not a
        crash; exit **1**/**3** → application or `ExitOnOutOfMemoryError`, look in the log;
        no exit code and `Error` → look for `hs_err_pid*.log`. `[FLOW]` `[NUM]` `[DIAG]`
2.11.14 **Memory-limit sizing, as a formula rather than a guess**: `memory.max` = heap ÷
        `MaxRAMPercentage` + sidecar + agent + a **10% safety margin for page cache and kernel
        memory**, then validated by running the canary with `AlwaysPreTouch` and reading
        `memory.peak`. Show it for `FundsLedger` (12 GB heap → 16 GB limit) and
        `ClientRestrictions` (4 GB heap → 6 GB limit, because fixed native costs are proportionally
        larger). `[CALC]` `[NUM]`

*(14 leaves)*

## §2.12 JVM container awareness: `UseContainerSupport`, `MaxRAMPercentage`, `ActiveProcessorCount`

2.12.1 **`-XX:+UseContainerSupport` is on by default** and is what makes the JVM read
       `memory.max`/`cpu.max` instead of `/proc/meminfo` and `nproc`. Quote the man page: "The VM now
       provides automatic container detection support, which allows the VM to determine the amount of
       memory and number of processors that are available to a Java process running in docker
       containers… The default for this flag is `true`". `[SOURCE]` `[API]` `[RESEARCH]`
       (JDK 21 `java` man page, `-XX:+UseContainerSupport`)
2.12.2 **Container awareness has a version history that still generates wrong advice.** Before
       **8u191/JDK 10** the JVM read host memory and host CPU count, so `-XX:+UnlockExperimentalVMOptions
       -XX:+UseCGroupMemoryLimitForHeap` was necessary; those flags are **obsolete** and removed.
       cgroup **v2** support arrived in **JDK 15** and was backported to 11.0.16/8u372 — a JDK 11.0.9
       on a v2-only host reads *nothing* and sizes from the host. `[VERSION-TRAP]` `[NUM]`
       `[RESEARCH]`
2.12.3 **`-XX:MaxRAMPercentage` default is 25.0** — the JVM takes a quarter of the container limit as
       maximum heap. For a dedicated single-JVM container this wastes three quarters of the memory
       you are paying for: a 16 GB `FundsLedger` container defaults to a **4 GB heap**, not 12 GB, and
       the service GC-thrashes at a memory limit it never approaches. `[NUM]` `[TRAP]` `[CALC]`
2.12.4 **Why the default is 25% and not a bug**: it is deliberately conservative because the JVM
       cannot know whether it shares the container. Also state the two companions —
       `-XX:InitialRAMPercentage` default **1.5625** and `-XX:MinRAMPercentage` default **50.0**,
       where `MinRAMPercentage` confusingly applies only when physical memory is **below 250 MB**
       (it is a *maximum*-heap fraction for small containers, not a minimum). `[NUM]`
       `[VERSION-TRAP]` `[TRAP]`
2.12.5 **The right setting, derived**: `-XX:MaxRAMPercentage=75` for a dedicated container ≥4 GB
       (leaving ~25% for the native terms of §2.3.1), lower — 50–60% — for small containers where
       fixed native costs dominate, and `-XX:MaxRAMPercentage=70 -XX:InitialRAMPercentage=70
       -XX:+AlwaysPreTouch` for a pause-sensitive service where a fixed, pre-touched heap is wanted.
       Prefer percentages to `-Xmx` so a limit change does not silently desynchronise. `[CALC]`
       `[API]` `[NUM]`
2.12.6 **`-Xmx` beats `MaxRAMPercentage` when both are given**, and mixing them across a base image
       and a deployment manifest is a real production hazard: the base image's `JAVA_TOOL_OPTIONS`
       with `-Xmx2g` silently overrides the manifest's carefully computed percentage. Verify with
       `jcmd <pid> VM.flags` (or `-XX:+PrintFlagsFinal`), never with the manifest. `[TRAP]` `[DIAG]`
2.12.7 **How the JVM computes the CPU count in a container.** It takes the **minimum** of: the host
       CPU count, `ceil(cpu.max quota / period)` when a quota is set, and the `cpu.weight`-derived
       share when `-XX:-PreferContainerQuotaForCPUCount` is used; the result is floored at **1**.
       Also honoured: `cpuset.cpus.effective`. So `limits.cpu: 3.5` yields **4**, and
       `limits.cpu: 0.4` yields **1**. `[CALC]` `[NUM]` `[RESEARCH]`
2.12.8 **`-XX:ActiveProcessorCount=N` overrides the whole computation** and is the correct lever when
       the quota-derived count is wrong in either direction — e.g. a `limits.cpu: 0.5`
       `ClientRestrictions` pod that should still use 2 GC threads, or a `Guaranteed` pod with
       `cpuset` pinning where you want the JVM to see exactly its pinned cores. Quote the man page:
       "Overrides the number of CPUs that the VM will use to calculate the size of thread pools it
       will use for various operations such as Garbage Collection and ForkJoinPool." `[SOURCE]`
       `[API]` `[RESEARCH]`
2.12.9 **The fractional-quota blast radius, enumerated.** With `availableProcessors()` = 1:
       `ForkJoinPool.commonPool` parallelism = **0** (every `parallelStream` runs on the caller
       thread), `ParallelGCThreads` = 1, `ConcGCThreads` = 1, `CICompilerCount` = the minimum,
       G1 or **SerialGC** by ergonomics, the virtual-thread scheduler parallelism = 1, Netty's
       default event-loop group = 2, and any `Runtime.getRuntime().availableProcessors()`-sized
       application pool = 1. One YAML field, eight consequences. `[CALC]` `[NUM]` `[TRAP]`
       `[INCIDENT]`
2.12.10 **`Runtime.availableProcessors()` can change at runtime** — a `cpuset` or quota update is
        picked up on subsequent calls — which means a pool sized once at startup and a pool sized
        lazily can disagree. Cache it deliberately, once, at startup. `[API]` `[TRAP]`
2.12.11 **The verification recipe, which must be run in CI or a canary, not reasoned about**:
        `jcmd <pid> VM.flags | tr ' ' '\n' | grep -E 'MaxHeapSize|MaxRAMPercentage|ActiveProcessor|UseG1|UseSerial|ParallelGCThreads'`
        plus a one-liner
        `jshell -q -s <(echo 'System.out.println(Runtime.getRuntime().availableProcessors()+" "+Runtime.getRuntime().maxMemory()/1048576);')`
        and `java -XshowSettings:system -version` (which prints the detected cgroup limits directly).
        `[BUILD]` `[DIAG]`
2.12.12 **`-XshowSettings:system` is the single most under-used container-debugging flag**: on Linux
        it prints "Operating System Metrics" — provider (cgroupv2), effective CPU count, CPU period,
        CPU quota, CPU shares, memory limit, memory soft limit, memory & swap limit — i.e. the JVM's
        *own view*, which is the only view that matters. `[API]` `[DIAG]` `[SOURCE]`
2.12.13 **The `JAVA_TOOL_OPTIONS` / `JDK_JAVA_OPTIONS` / `_JAVA_OPTIONS` precedence trap**, because
        container images use all three: `_JAVA_OPTIONS` wins over the command line, the command line
        wins over `JAVA_TOOL_OPTIONS`, and `JDK_JAVA_OPTIONS` (JDK 9+) applies only to the `java`
        launcher. State the order and the fact that `JAVA_TOOL_OPTIONS` announces itself on stderr —
        which is how you discover it exists. `[TRAP]` `[NUM]` `[VERSION-TRAP]`

*(13 leaves)*

## §2.13 Namespaces: the eight kinds and what each isolates

2.13.1 **The eight namespace types**, as the canonical table with flag, `/proc/<pid>/ns` entry and
       introduction version: **mount** `CLONE_NEWNS`/`mnt` (3.8 for unprivileged; the flag predates
       the naming), **UTS** `CLONE_NEWUTS`/`uts` (2.6.19; hostname and NIS domain), **IPC**
       `CLONE_NEWIPC`/`ipc` (2.6.19; System V IPC and POSIX message queues), **PID**
       `CLONE_NEWPID`/`pid` (2.6.24), **network** `CLONE_NEWNET`/`net` (2.6.29), **user**
       `CLONE_NEWUSER`/`user` (3.8), **cgroup** `CLONE_NEWCGROUP`/`cgroup` (**4.6**), **time**
       `CLONE_NEWTIME`/`time` (**5.6**; boot and monotonic clocks only). `[TABLE]` `[NUM]`
       `[RESEARCH]` (`namespaces(7)`, man-pages 6.x)
2.13.2 **A container is not a kernel object.** It is a process with a private set of namespaces, a
       cgroup, a seccomp filter, a set of capabilities and a root filesystem — five independent
       mechanisms, any of which can be shared. Say this once, plainly, because it explains every
       "why can the container see X" question. `[PROVE]`
2.13.3 **The three syscalls**: `clone(2)`/`clone3(2)` with `CLONE_NEW*` flags creates a process in new
       namespaces, `unshare(2)` moves the *calling* process into new ones, `setns(2)` joins an
       existing one via an fd on `/proc/<pid>/ns/<type>`. `nsenter -t <pid> -n ss -tanp` — enter a
       container's network namespace from the host to run tools the image does not contain — is the
       single most useful application of `setns`. `[SYSCALL]` `[BUILD]` `[DIAG]`
2.13.4 **The PID namespace is the one that changes JVM behaviour.** The first process is **PID 1**
       inside, with two kernel-conferred properties: signals with default dispositions are
       **not delivered** to it (so an app that installs no `SIGTERM` handler ignores `SIGTERM`
       entirely), and it must **reap orphans** or they accumulate as zombies. Both feed §2.23.
       `[PROVE]` `[TRAP]`
2.13.5 **`/proc` is where namespace isolation leaks.** Unless `/proc` is remounted inside the
       container's mount namespace, `/proc/cpuinfo`, `/proc/meminfo`, `/proc/stat`,
       `/proc/loadavg` and `/proc/diskstats` all show **host** values — which is exactly why
       `nproc`, `free`, `top` and most Java libraries that read them are wrong inside a container,
       and why the JVM had to learn cgroups (§2.12). `lxcfs` exists solely to paper over this.
       `[TRAP]` `[PROC]` `[PROVE]`
2.13.6 **Load average is host-wide, always.** `/proc/loadavg` is not namespaced, so a container's
       "load 40" may be entirely a neighbour's. Any autoscaler or health check keyed on load average
       inside a container is measuring the wrong machine. `[TRAP]` `[NUM]`
2.13.7 **The mount namespace and the container's root**: `pivot_root`/`chroot` onto the overlayfs
       mount (§2.14), then a curated set of mounts — `proc`, `sysfs`, `tmpfs` on `/dev/shm`
       (**64 MB by default in Docker**, which breaks JVM tooling and anything using shared memory),
       `devpts`, and the bind mounts for `ConfigMap`s and `Secret`s. `[NUM]` `[TRAP]`
2.13.8 **The network namespace** gives a private loopback, interfaces, routing table, iptables/nftables
       rules, conntrack table and socket table. Two consequences worth stating: `127.0.0.1` inside a
       pod reaches only the pod (which is how sidecars are addressed), and `conntrack` limits are
       **per-namespace in principle but shared in practice** on most CNI setups. `[X-REF 10]`
       `[X-REF 19]` `[TRAP]`
2.13.9 **The user namespace** maps container UIDs to unprivileged host UIDs
       (`/proc/<pid>/uid_map`, `gid_map`), which is what makes "root in the container" not root on the
       host. Kubernetes exposes it as `spec.hostUsers: false` (beta from 1.30). The practical JVM
       consequence is file ownership on mounted volumes and the ability to `mlock`/set `RLIMIT_*`.
       `[PROC]` `[X-REF 19]` `[VERSION-TRAP]`
2.13.10 **The cgroup namespace** is why `cat /proc/self/cgroup` inside a modern container prints
        `0::/` rather than a long host path, and why `/sys/fs/cgroup` shows the container's own files
        at the root (§2.9.15). Without it, a container could read — and be confused by — the entire
        host hierarchy. `[PROC]` `[PROVE]`
2.13.11 **The time namespace is the odd one out**: it virtualises `CLOCK_MONOTONIC` and
        `CLOCK_BOOTTIME` offsets only — **not `CLOCK_REALTIME`** — so you cannot fake wall-clock time
        for a container, which matters for anyone hoping to test QuizStakes' 14-day coupon validity or
        30-day bonus expiry by shifting the container's clock. `[TRAP]` `[NUM]` `[RESEARCH]`
        (`time_namespaces(7)`)
2.13.12 **Inspecting namespaces**: `lsns` (all namespaces with their type, nprocs and owning
        command), `readlink /proc/<pid>/ns/*` (identical inode = same namespace — the definitive test
        for "are these two processes isolated"), and `docker inspect`/`crictl inspect` for the
        container's view. `[DIAG]` `[BUILD]`

*(12 leaves)*

## §2.14 The container substrate end to end: image layers, overlayfs, runc, containerd

2.14.1 **An image is a manifest plus an ordered list of tarball layers**, each identified by a
       content-addressed digest (`sha256:…`), plus a config blob holding the entrypoint, env and
       rootfs diff-ids. The image ID is the digest of the *config*, which is why two images with
       identical layers can have different IDs. `[NUM]` `[PROVE]`
2.14.2 **`overlayfs` is how layers become a filesystem**: read-only **lowerdirs** (the image layers,
       stacked), a writable **upperdir** (the container's changes), a **workdir** (for atomic
       operations), and the **merged** mount the process sees. Read a real mount line from
       `/proc/self/mountinfo` and name each component. `[SOURCE]` `[PROC]` `[TABLE]`
2.14.3 **Copy-up is the performance property that matters.** Writing one byte to a file in a lower
       layer copies the **entire file** into the upperdir first. A JVM that appends to a log file
       baked into the image, or rewrites a 200 MB data file, pays a full copy on first write —
       and whiteout files (`.wh.*` in older drivers, character devices in overlayfs) implement
       deletion without touching the lower layer. `[PROVE]` `[TRAP]` `[NUM]`
2.14.4 **Why writable overlay is the wrong place for a JVM's hot writes**: logs, heap dumps and
       temp files on the overlay contend with the container runtime, are counted against ephemeral
       storage (`ephemeral-storage` requests/limits, and eviction when the node's `imagefs` fills),
       and are lost on restart. Mount an `emptyDir` and point `-XX:HeapDumpPath`,
       `java.io.tmpdir` and the log appender at it. `[TRAP]` `[X-REF 19]`
2.14.5 **The layer-caching arithmetic that justifies image structure**: a 400 MB base JRE layer, a
       120 MB dependency layer and a 3 MB application layer means a code-only deploy pushes and pulls
       **3 MB**; a single fat layer pushes 523 MB every time. Spring Boot's layered jars
       (`java -Djarmode=tools -jar app.jar extract --layers`) and jib exist for exactly this.
       `[CALC]` `[NUM]` `[API]`
2.14.6 **The runtime stack, named precisely and in order**: kubelet → **CRI** (gRPC) → **containerd**
       → the CRI plugin → **containerd-shim-runc-v2** (one shim per pod, which is what keeps
       containers alive across a containerd restart) → **runc** (which sets up namespaces, cgroups,
       seccomp, capabilities and `pivot_root`, then `execve`s your process and **exits**). `[FLOW]`
       `[NUM]`
2.14.7 **runc exits; your process does not have a parent runtime.** This is the mechanical reason
       PID 1 semantics matter (§2.13.4, §2.23): after `execve` there is no supervisor inside the
       container, so signal forwarding and zombie reaping are *your* problem or `tini`'s. `[PROVE]`
       `[TRAP]`
2.14.8 **The OCI runtime spec's `config.json` is the whole container in one file** —
       `process.args`, `process.env`, `process.rlimits` (where `RLIMIT_NOFILE` actually comes from),
       `linux.namespaces`, `linux.resources.memory.limit`, `linux.resources.cpu.quota`,
       `linux.seccomp`, `mounts`. Reading it (`crictl inspect`, or
       `/run/containerd/io.containerd.runtime.v2.task/k8s.io/<id>/config.json`) is how you settle any
       "what limits does this container really have" argument. `[SOURCE]` `[BUILD]` `[DIAG]`
2.14.9 **Seccomp and capabilities are the second half of "why does this syscall fail in a
       container".** The default Docker/containerd seccomp profile blocks ~40 syscalls
       (`perf_event_open` among them — §2.24), and the default capability set drops
       `CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`, `CAP_SYS_NICE`, `CAP_IPC_LOCK` and `CAP_SYS_RESOURCE`.
       Consequence for a JVM: no `perf`, no `jstack -F` across containers, no `chrt`, no
       `mlockall`, no raising a hard `ulimit`. `[TABLE]` `[TRAP]` `[X-REF 13]`
2.14.10 **`RLIMIT_NOFILE` in containers has a version history that changed the answer.** Docker
        historically inherited the daemon's `1024`; modern containerd/Docker set it to a large value
        or `infinity`, and systemd 240+ sets `LimitNOFILE=1024:524288` for services (soft:hard), while
        **systemd 255 defaults `DefaultLimitNOFILE` to 1024 soft / 512K hard** so a process that does
        not raise its own soft limit still gets 1024. The only trustworthy reading is
        `cat /proc/<pid>/limits` (§2.15). `[VERSION-TRAP]` `[NUM]` `[PROC]`
2.14.11 **`--init` / `tini` / `dumb-init`**: a ~10 KB PID 1 that forwards signals to the child's
        process group and reaps zombies. Kubernetes has no `--init` equivalent — you add it to the
        image or use exec form correctly (§2.23). `[API]` `[NUM]`
2.14.12 **Distroless, JRE-only and CDS as image decisions with runtime consequences**: a distroless
        base has no shell (so no shell-form `ENTRYPOINT`, and no `jcmd` unless you add the JDK), a
        JRE-only image has **no `jcmd`/`jstack`/`jmap`** (which is why a debug sidecar sharing the
        pid namespace is the standard pattern), and an AppCDS archive
        (`-XX:SharedArchiveFile`, `-XX:ArchiveClassesAtExit`) cuts startup by 20–40% and is
        page-cache-shared across containers on the same node. `[TABLE]` `[API]` `[TRAP]`
2.14.13 **The container-startup timeline for a JVM, with real numbers**, so the reader can attribute
        a slow rollout: image pull (0 if cached, 5–60 s if not, dominated by layer size), runc setup
        (~50–200 ms), JVM start to `main` (~200–400 ms, less with CDS), Spring context refresh
        (1–8 s), `AlwaysPreTouch` (seconds per 10 GB), JIT warmup to steady-state p99 (**30 s–3 min**,
        and this is the term everyone forgets when setting `initialDelaySeconds`). `[CALC]` `[NUM]`
        `[X-REF 19]`

*(13 leaves)*

## §2.15 `ulimit`s and kernel limits that break production at scale

2.15.1 **Soft vs hard, and the rule that decides every argument**: the soft limit is what applies,
       the hard limit is the ceiling a process may raise itself to, and an unprivileged process can
       lower either but raise only the soft limit (raising the hard limit needs
       `CAP_SYS_RESOURCE`). `getrlimit`/`setrlimit`/`prlimit(2)` are the syscalls; `prlimit --pid
       <pid> --nofile` changes a **running** process. `[SYSCALL]` `[NUM]` `[PROVE]`
2.15.2 **`/proc/<pid>/limits` is the only authoritative reading**, because the limit that applies is
       the one in force when the process was created — not what your shell shows, not what the
       Dockerfile says, not what `/etc/security/limits.conf` says (which `pam_limits` applies to
       *login* sessions only, and a systemd service is not a login session). `[PROC]` `[TRAP]`
2.15.3 **`RLIMIT_NOFILE` (`ulimit -n`)** — the limit that actually causes outages. Typical soft
       defaults: 1024 (systemd `DefaultLimitNOFILE` soft), 1048576 (modern containerd), 65535
       (hand-tuned). A production Java service value is **65536 or higher**; set it in the systemd
       unit (`LimitNOFILE=65536`), the OCI `config.json` `process.rlimits`, or the pod's
       `securityContext` via the runtime — never in `.bashrc`. `[SYSCTL]` `[NUM]`
2.15.4 **`fs.nr_open` is the ceiling on `RLIMIT_NOFILE`** (default **1048576**) and
       **`fs.file-max`** is the system-wide count of open files (default derived from RAM, typically
       millions on a modern box). `ulimit -n` cannot exceed `fs.nr_open`; `fs.file-nr` shows
       allocated/free/max. State the distinction because they are constantly confused. `[SYSCTL]`
       `[NUM]` `[PROC]`
2.15.5 **`RLIMIT_NPROC` (`ulimit -u`) counts threads, not processes**, per **real UID across the
       whole system**, which is why two containers running as the same UID share it and why a
       thread-heavy JVM hits it unexpectedly. `kernel.threads-max` and
       `kernel.pid_max` (default **4194304** on 64-bit since 4.x, previously 32768) are the
       system-wide ceilings; the cgroup equivalent is `pids.max` (§2.9.12). All four produce the same
       `unable to create native thread`. `[SYSCTL]` `[NUM]` `[TRAP]`
2.15.6 **`RLIMIT_CORE` (`ulimit -c`)** is 0 on most systems, which means a JVM crash produces an
       `hs_err_pid*.log` but **no core file** — and without a core there is no post-mortem for a
       native crash. Set it to `unlimited`, set `/proc/sys/kernel/core_pattern` to a path that exists
       and has space (a 16 GB JVM writes a 16 GB core), and remember `kernel.core_pattern` is
       **host-wide and not namespaced**, so a container's core lands where the host says. `[SYSCTL]`
       `[NUM]` `[TRAP]`
2.15.7 **`RLIMIT_MEMLOCK` (`ulimit -l`)** — default 8 MB (systemd often 64 MB) — gates explicit huge
       pages (§2.7.3), `mlock`, and io_uring's fixed buffers. `RLIMIT_AS` (`ulimit -v`) is the one to
       *never* set for a JVM, because the JVM reserves far more address space than it commits and
       `-v` counts reservations. `[SYSCTL]` `[TRAP]` `[NUM]`
2.15.8 **`RLIMIT_STACK` (`ulimit -s`, default 8192 KB) is not `-Xss`** but it does set the **main
       thread's** stack size, so `ulimit -s unlimited` makes the JVM pick a different (and on some
       platforms much larger) main-thread stack and can change `-Xss` defaults. It is also the
       single most common cause of "works on my laptop, `StackOverflowError` in the container".
       `[NUM]` `[TRAP]`
2.15.9 **The complete limit table with defaults and the JVM symptom of each**: `NOFILE` → `Too many
       open files`; `NPROC` → `unable to create native thread`; `MEMLOCK` → large pages silently
       disabled; `CORE` → no core dump; `STACK` → `StackOverflowError`; `AS` → `Could not reserve
       enough space for object heap`; `FSIZE` → truncated heap dump; `CPU` → `SIGXCPU`;
       `SIGPENDING`/`MSGQUEUE` → rarely, signal delivery failures. `[TABLE]` `[NUM]` `[DIAG]`
2.15.10 **The systemd surface, because most VMs are systemd**: `LimitNOFILE=`, `LimitNPROC=`,
        `LimitCORE=`, `LimitMEMLOCK=`, `TasksMax=` (which is `pids.max`, and
        `DefaultTasksMax` is **15%** of `kernel.pid_max`), `MemoryMax=`, `CPUQuota=`,
        `OOMPolicy=`, plus `systemctl show <unit> -p LimitNOFILE` to verify. And the rule:
        `/etc/security/limits.conf` does **not** affect systemd services. `[SYSCTL]` `[NUM]`
        `[TRAP]`
2.15.11 **The network sysctls that behave like limits** and are the other half of "we scaled and it
        broke": `net.core.somaxconn` (default **4096** since 5.4), `net.ipv4.tcp_max_syn_backlog`,
        `net.ipv4.ip_local_port_range` (default `32768 60999` — 28,231 ephemeral ports),
        `net.netfilter.nf_conntrack_max`, `net.core.netdev_max_backlog`. One paragraph of mechanism
        each, then point away. `[SYSCTL]` `[NUM]` `[X-REF 10]`
2.15.12 **`inotify` limits are the silent Kubernetes killer**: `fs.inotify.max_user_watches`
        (default 8192 on some distros, 65536+ on others) and `fs.inotify.max_user_instances`
        (default **128**) are **per-UID and host-wide**, so many pods watching `ConfigMap`s and
        Spring Boot devtools/`FileSystemWatcher` exhaust them and file-change detection stops with no
        error. `[SYSCTL]` `[NUM]` `[TRAP]`
2.15.13 **How to verify limits from inside the running JVM**, so the check is part of the service and
        not a runbook step: log `/proc/self/limits`, `/sys/fs/cgroup/pids.max`,
        `Runtime.availableProcessors()`, `Runtime.maxMemory()` and the resolved `MaxHeapSize` at
        startup, and fail the readiness probe if `RLIMIT_NOFILE` is below a configured floor.
        `[BUILD]` `[API]`

*(13 leaves)*

## §2.16 File-descriptor exhaustion: symptoms, arithmetic, diagnosis

2.16.1 **What consumes an fd, exhaustively**: regular files, sockets (TCP, UDP, Unix), pipes,
       `epoll` instances, `eventfd`, `timerfd`, `signalfd`, `inotify` instances, `memfd`,
       `/dev/urandom`, mapped jars, the JVM's own `hsperfdata` mapping, and every `Selector`. A
       modern JVM has **200–400 fds before your code opens anything** — count them once with
       `ls /proc/<pid>/fd | wc -l` on a freshly started service. `[NUM]` `[PROC]`
2.16.2 **The two causes, and the diagnostic that separates them in thirty seconds.** Limit too low
       for legitimate load → fd count is **high and stable**, proportional to connections. Leak → fd
       count **rises monotonically** and never falls, including during idle periods. Plot
       `ls /proc/<pid>/fd | wc -l` every 10 s for 5 minutes; the shape is the diagnosis. `[FLOW]`
       `[DIAG]` `[PROVE]`
2.16.3 **The arithmetic for `ApplicationGateway` at 55k concurrent sessions**: inbound sockets 55,000
       ÷ 40 instances = **1,375 per instance**, plus outbound pooled connections to ~10 downstreams at
       50 each = 500, plus ~300 JVM baseline, plus headroom = a working set near **2,200 fds** and a
       limit of 65,536 chosen so that a 10× traffic spike or a pool misconfiguration does not hit it.
       `[CALC]` `[NUM]`
2.16.4 **The arithmetic for `FundsLedger` at 3 instances**: 170 in-flight stake reservations at burst
       (§2.1.12), a JDBC pool of 50, three inbound connections per client-affine caller, plus
       baseline — a few hundred fds, so `Too many open files` on `FundsLedger` is **always a leak**,
       never load. Stating which services can legitimately need many fds and which cannot is the
       useful part. `[CALC]` `[PROVE]`
2.16.5 **The symptom set, because `Too many open files` is not always the message.**
       `java.net.SocketException: Too many open files` on `accept`,
       `java.io.FileNotFoundException: … (Too many open files)`,
       `java.nio.channels.ClosedChannelException` cascades, an `epoll_create` failure at Netty
       startup, `SSLException: Could not generate secret` (it failed to open `/dev/urandom`), and —
       the nastiest — a **health check that still passes** because its connection was already open.
       `[DIAG]` `[TABLE]` `[TRAP]`
2.16.6 **The `EMFILE` vs `ENFILE` distinction**: `EMFILE` = this process hit `RLIMIT_NOFILE`;
       `ENFILE` = the **system** hit `fs.file-max`. The second means another process is the culprit
       and raising your own limit will not help. Check `cat /proc/sys/fs/file-nr`. `[SYSCALL]`
       `[NUM]` `[TRAP]`
2.16.7 **The `lsof` diagnostic sequence, in order**: `lsof -p <pid> | wc -l` (total),
       `lsof -p <pid> | awk '{print $5}' | sort | uniq -c | sort -rn` (by type — `IPv4`/`IPv6`/`REG`/
       `sock`/`a_inode`/`FIFO`), `lsof -p <pid> | awk '{print $9}' | sort | uniq -c | sort -rn | head`
       (by target — a thousand fds on one path is the leak), `lsof -i -a -p <pid>` (sockets only),
       and `lsof +L1` (deleted-but-open). Prefer `ls -l /proc/<pid>/fd` when `lsof` is not in the
       image. `[BUILD]` `[DIAG]`
2.16.8 **The socket-state cross-check**: `ss -tanp | grep <pid> | awk '{print $1}' | sort | uniq -c`.
       Thousands in **`CLOSE_WAIT`** means *your* code is not closing (the peer sent FIN, you never
       called `close`) — the definitive Java-side socket leak signature. Thousands in
       `TIME_WAIT` is normal churn on the *initiating* side and consumes a port, not an fd (once the
       socket is closed). `[DIAG]` `[NUM]` `[X-REF 10]`
2.16.9 **The Java-side causes, ranked by how often they actually occur**: an `HttpResponse`/
       `InputStream` from a pooled HTTP client not consumed or closed (so the connection is never
       returned), `Files.list`/`Files.walk`/`DirectoryStream` used without try-with-resources (a
       `Stream` holding a directory fd), a JDBC `Connection` obtained outside a
       `try`-with-resources, a `Selector` or `EventLoopGroup` created per request, a
       `FileChannel.map` never released, and `Runtime.exec` output streams left open. `[TABLE]`
       `[TRAP]` `[API]`
2.16.10 **Why raising the limit is sometimes exactly right and sometimes negligent**, as an explicit
        decision: raise it when the arithmetic of §2.16.3 says the working set legitimately exceeds
        the limit; fix the code when the count rises without bound. Doing the first for the second
        buys **`limit / leak_rate`** seconds — compute that number and put it in the incident
        write-up, because "we raised the limit" and "we bought 6 hours" are different statements.
        `[CALC]` `[PROVE]`
2.16.11 **Detecting it before it happens**: JMX
        `java.lang:type=OperatingSystem` `OpenFileDescriptorCount` / `MaxFileDescriptorCount`,
        Micrometer's `process.files.open` and `process.files.max` gauges, and an alert on
        **ratio > 0.8** plus a second alert on **positive 1-hour slope during a traffic trough** —
        the latter catches leaks that the ratio alert never will. `[API]` `[BUILD]` `[NUM]`
2.16.12 **Netty's and the JDK client's fd accounting differ**, and it matters when reading the
        numbers: each Netty `EventLoop` holds one `epoll` fd plus one `eventfd` (wakeup) plus one
        `timerfd`, so a 2×`nproc` event-loop group on a 16-core box is ~96 fds before a single
        connection; the JDK `HttpClient` holds one `Selector` and one connection per
        origin-and-protocol. `[NUM]` `[API]`
2.16.13 **Reproduce it once, deliberately**: a Java 21 program that opens sockets in a loop under
        `ulimit -n 256`, catching and printing the exact exception at the exact count — the point
        being that the failure arrives at `limit − baseline`, not at `limit`, which is why the
        alerting threshold must be a ratio and not an absolute number. `[BUILD]` `[CALC]`

*(13 leaves)*

## §2.17 `epoll` in practice: level vs edge triggered, the thundering herd, Netty and NIO

2.17.1 **Why `epoll` exists, in complexity terms**: `select`/`poll` are **O(n)** per call because the
       whole fd set is copied into the kernel and scanned every time (and `select` is additionally
       capped at `FD_SETSIZE` = **1024**); `epoll` registers interest **once**
       (`epoll_ctl`) and returns only ready fds, making the wait **O(ready)**. At 10,000 idle
       connections with 10 active, that is 10,000 scanned versus 10 returned. `[CALC]` `[PROVE]`
       `[SYSCALL]`
2.17.2 **The three syscalls and their exact signatures**: `epoll_create1(EPOLL_CLOEXEC)` (returns an
       fd — hence §2.16.1), `epoll_ctl(epfd, EPOLL_CTL_ADD|MOD|DEL, fd, &event)`, and
       `epoll_wait(epfd, events, maxevents, timeout)` / `epoll_pwait2` (nanosecond timeout, 5.11+).
       `[SYSCALL]` `[API]`
2.17.3 **The event mask, completely**: `EPOLLIN`, `EPOLLOUT`, `EPOLLRDHUP` (**the peer half-closed** —
       the flag that lets you detect a dead connection without a read), `EPOLLPRI`, `EPOLLERR` and
       `EPOLLHUP` (always reported, never need registering), plus the behaviour modifiers
       `EPOLLET`, `EPOLLONESHOT`, `EPOLLEXCLUSIVE` (**4.5+**), `EPOLLWAKEUP`. `[TABLE]` `[NUM]`
2.17.4 **Level-triggered (default) vs edge-triggered, defined precisely.** LT: `epoll_wait` reports
       readiness as long as the condition holds, so a partial read is safe and a missed event is
       impossible. ET: reports only on a **transition**, so you must drain until `EAGAIN` or the
       event is lost forever — fewer wakeups, and a whole class of hang bugs. `[PROVE]` `[TABLE]`
2.17.5 **Java's choice**: `java.nio.channels.Selector` on Linux uses `EPollSelectorImpl` in
       **level-triggered** mode, which is why `SelectionKey`s must be deregistered or their interest
       cleared before doing work, or `select()` returns immediately in a busy loop. Netty's
       `EpollEventLoop` also defaults to level-triggered, with edge-triggered available via
       `EpollChannelOption.EPOLL_MODE = EpollMode.EDGE_TRIGGERED`. `[API]` `[SOURCE]` `[NUM]`
2.17.6 **The classic Java NIO busy-loop bug**: a key registered for `OP_WRITE` whose socket buffer is
       always writable makes `select()` return every call, burning **100% of one core** with
       `epoll_wait` returning instantly. Register `OP_WRITE` only when a write has actually returned
       short. The symptom is one pegged core, `%us` high, and `strace -c` dominated by
       `epoll_wait`. `[TRAP]` `[DIAG]` `[INCIDENT]`
2.17.7 **The `epoll` spurious-wakeup / `select()`-returns-zero JDK bug (JDK-6693490 and family)** is
       the historical reason Netty implemented its own selector-rebuilding workaround
       (`io.netty.selectorAutoRebuildThreshold`, default **512** consecutive premature returns).
       State that it is fixed in modern JDKs and that the workaround remains as insurance —
       version-stale advice either way. `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
2.17.8 **The thundering herd, in its two distinct forms.** Form 1: many threads blocked in
       `accept()` on one listening socket — solved in the kernel long ago (only one is woken). Form
       2: many threads/processes each with the listening fd in **their own** `epoll` set — every one
       is woken on a single incoming connection, and all but one get `EAGAIN`. This second form is
       real and is what `EPOLLEXCLUSIVE` (4.5+) and `SO_REUSEPORT` (3.9+) exist to fix. `[PROVE]`
       `[TRAP]` `[NUM]`
2.17.9 **`SO_REUSEPORT` gives each acceptor its own accept queue** with kernel-side hashing of
       incoming connections, which is how Netty's `EpollServerSocketChannel` with
       `EpollChannelOption.SO_REUSEPORT` and multiple bound event loops removes the single-acceptor
       bottleneck. State the caveat: rebalancing is by 4-tuple hash, so long-lived connections do not
       redistribute when an acceptor is added. `[API]` `[NUM]` `[X-REF 10]`
2.17.10 **The event-loop model's cardinal rule and its cost**: never block the event loop. One
        blocking JDBC call on a Netty event loop stalls **every connection assigned to that loop** —
        with 2×16 = 32 loops and 10,000 connections, a 2-second blocking call freezes ~312
        connections. This is the arithmetic that makes "offload to a business executor" a
        requirement, not a style preference. `[CALC]` `[NUM]` `[TRAP]`
2.17.11 **Sizing event loops**: default is `2 × availableProcessors()`
        (`io.netty.eventLoopThreads`), and more loops do not help because the work is
        CPU-bound-with-syscalls; fewer loops with a separate blocking executor is almost always
        better than many loops that occasionally block. Note the container interaction — get
        `availableProcessors()` wrong (§2.12) and the loop count is wrong. `[NUM]` `[API]`
2.17.12 **Observing `epoll` behaviour**: `strace -c -f -p <pid>` (syscall histogram — a healthy event
        loop is dominated by `epoll_wait`/`read`/`write`, an unhealthy one by `futex` or `epoll_ctl`),
        `perf trace -e 'epoll*' -p <pid>`, `ls -l /proc/<pid>/fd | grep eventpoll` (count the epoll
        instances), and `cat /proc/<pid>/fdinfo/<epfd>` (which lists the registered fds and their
        event masks — the definitive answer to "what is this selector watching"). `[PROC]` `[DIAG]`
        `[BUILD]`
2.17.13 **When `epoll` is not the answer**: regular-file I/O (always "ready", so `epoll` tells you
        nothing — §2.5.7, §2.18), very low connection counts where a thread per connection is
        simpler and faster, and workloads where the per-event syscall cost dominates — which is the
        opening for `io_uring`. `[PROVE]`

*(13 leaves)*

## §2.18 `io_uring`: the model, where it wins, and its JDK status

2.18.1 **The model**: two lock-free ring buffers shared between user space and kernel via `mmap` — a
       **submission queue (SQ)** and a **completion queue (CQ)** — with three syscalls only:
       `io_uring_setup(2)`, `io_uring_enter(2)`, `io_uring_register(2)`. Work is *submitted* by
       writing an SQE and advancing a tail, and completions are *read* from the CQ. `[SYSCALL]`
       `[FLOW]` `[NUM]`
2.18.2 **Why that is fundamentally different from `epoll`.** `epoll` is a **readiness** interface —
       it tells you a syscall would not block, and you then make the syscall. `io_uring` is a
       **completion** interface — you describe the operation and are told when it finished. That
       difference is what lets it batch, and what lets it cover operations `epoll` cannot express.
       `[PROVE]` `[TABLE]`
2.18.3 **The syscall-amortisation arithmetic**: with `epoll`, one request costs ~1 `epoll_wait`
       (amortised over a batch) + 1 `read` + 1 `write` ≈ 2–3 mode transitions at ~300 ns each
       (§2.1.2). With `io_uring` and batching, 64 operations can be submitted in **one**
       `io_uring_enter`, and with `IORING_SETUP_SQPOLL` a kernel thread polls the SQ so the count
       reaches **zero syscalls per operation**. `[CALC]` `[NUM]`
2.18.4 **The features that have no `epoll` equivalent**: asynchronous **regular-file** reads and
       writes without a thread pool (the gap in §2.5.7), `fsync`, `openat`, `statx`, `splice`,
       linked SQEs (`IOSQE_IO_LINK` — "connect, then write, then read" as one submission),
       registered files and buffers (`IORING_REGISTER_FILES`, avoiding fd lookup),
       provided buffers, and multishot accept/recv (5.19+). `[TABLE]` `[NUM]`
2.18.5 **Where it demonstrably wins**: high-IOPS storage (databases — this is why it exists),
       small-message network servers at very high rates, and proxies that can chain operations.
       Where it does not: anything whose cost is dominated by userspace work or by a single slow
       downstream — which is most business services, including every QuizStakes service except
       possibly `FundsLedger`'s write path. Say this plainly so the reader does not chase it.
       `[PROVE]` `[TRAP]`
2.18.6 **The kernel-version matrix matters more here than anywhere else in this guide**: introduced
       in **5.1**, usable for networking from **5.5–5.6**, `IORING_FEAT_FAST_POLL` in 5.7,
       multishot accept in 5.19, `IORING_SETUP_DEFER_TASKRUN` in 6.1, zero-copy send
       (`IORING_OP_SEND_ZC`) in 6.0. Amazon Linux 2023's 6.1/6.12 kernels have the full modern
       feature set; a 5.10-based node does not. `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
2.18.7 **The security story, stated honestly because it decides deployability.** A large share of
       recent kernel CVEs have been in `io_uring`; Google disabled it across Android, ChromeOS and
       production servers; the default **Docker/containerd seccomp profile blocks
       `io_uring_setup`**, and kernel **6.6+** added `kernel.io_uring_disabled` (0 = allowed,
       1 = privileged only, 2 = disabled entirely). So "use io_uring" is often not a decision the
       application gets to make. `[SYSCTL]` `[NUM]` `[TRAP]` `[RESEARCH]`
2.18.8 **The JDK status, precisely.** There is **no `io_uring` support in the JDK** as of Java 21 or
       25: NIO's `Selector` is `epoll`-based, `AsynchronousChannel` uses a thread pool over `epoll`,
       and virtual-thread file I/O offloads to a pool. The one relevant OpenJDK effort is Loom's
       poller work (`jdk.pollerMode`), not an io_uring backend. `[VERSION-TRAP]` `[API]` `[RESEARCH]`
2.18.9 **Netty's `io_uring` transport is real but incubating**:
       `io.netty.incubator:netty-incubator-transport-native-io_uring`, with
       `IOUringEventLoopGroup`, `IOUringServerSocketChannel` and `IOUring.isAvailable()`. It is a
       drop-in swap for `EpollEventLoopGroup` in code that programmed against `EventLoopGroup`
       rather than the concrete class — which is the practical reason to write against the interface.
       `[API]` `[BUILD]` `[NUM]`
2.18.10 **`liburing` is the reference user-space API** and the thing to read to understand the model
        (`io_uring_queue_init`, `io_uring_get_sqe`, `io_uring_prep_read`, `io_uring_submit`,
        `io_uring_wait_cqe`). Show the five-call skeleton once, in C, because the Java reader will
        otherwise never see the shape of a completion API. `[SOURCE]` `[BUILD]`
2.18.11 **Detecting availability and capability at runtime**, since "the kernel supports it" is not
        the same as "this container may use it": `uname -r`, `grep io_uring_setup
        /proc/kallsyms`, `cat /proc/sys/kernel/io_uring_disabled`, the container's seccomp profile,
        and — the only real test — attempting `io_uring_setup` and handling `ENOSYS`/`EPERM`.
        `[DIAG]` `[BUILD]`
2.18.12 **The verdict leaf**, which the write pass must not soften: for a Spring Boot 3.5 service on
        JDK 21 in EKS, `io_uring` is **not** a lever you have; it matters because the *databases and
        proxies* underneath you use it, and because it is the shape the next decade of Linux I/O
        takes. Know the model, do not plan a migration. `[PROVE]`

*(12 leaves)*

## §2.19 Zero-copy: `sendfile`, `splice`, `mmap`, and `FileChannel.transferTo`

2.19.1 **Count the copies in the naive path**, because zero-copy only makes sense against a baseline:
       `read(file, buf)` = DMA disk→page cache, then **copy page cache→user buffer**;
       `write(socket, buf)` = **copy user buffer→socket buffer**, then DMA→NIC. That is
       **4 copies and 4 context switches** (2 syscalls × 2 transitions) for one file-to-socket
       transfer. `[CALC]` `[FLOW]` `[NUM]`
2.19.2 **`sendfile(2)`** moves data between two fds entirely in the kernel: DMA disk→page cache, copy
       page cache→socket buffer, DMA→NIC = **3 copies, 2 context switches**; and with NIC
       scatter-gather DMA support the page-cache→socket copy disappears too, giving **2 copies (both
       DMA), 2 switches** — the true "zero-copy" case, where zero means *zero CPU copies*.
       `[SYSCALL]` `[CALC]` `[NUM]` `[PROVE]`
2.19.3 **`sendfile`'s constraints, which are why it is not universal**: the source must be a
       file-like fd supporting `mmap` (not a socket, not a pipe), the destination in modern Linux may
       be a socket or a file, and there is a per-call transfer cap. It cannot transform the bytes —
       so **TLS defeats it** unless kTLS is in play. `[TRAP]` `[NUM]`
2.19.4 **`splice(2)` and `vmsplice`/`tee`** generalise it by moving *page references* through a
       **pipe** (`SPLICE_F_MOVE`, `SPLICE_F_MORE`, `SPLICE_F_NONBLOCK`), which is what allows
       socket→socket transfer (a proxy) with no user-space copy. Netty exposes it as
       `EpollSocketChannel`'s `spliceTo`. `[SYSCALL]` `[API]` `[NUM]`
2.19.5 **`mmap` + `write` is the third option and the one with the hidden cost**: it eliminates the
       read copy but adds page faults, TLB pressure, and — the killer — an **unpredictable `SIGBUS`
       if the file is truncated under you**. It also cannot be unmapped deterministically in Java
       (§2.3.8). `[TRAP]` `[SYSCALL]`
2.19.6 **`FileChannel.transferTo(position, count, WritableByteChannel)` is the Java door to
       `sendfile`**, and `transferFrom` the reverse. It uses `sendfile` **only when** the target is a
       `SocketChannel` (or file) in blocking mode and no interception is in the way; otherwise it
       silently falls back to a user-space copy loop. `[API]` `[SOURCE]` `[TRAP]`
2.19.7 **The `transferTo` return value is the API's sharp edge**: it returns the number of bytes
       actually transferred, which may be **less than requested** (historically capped around
       2 GB / `Integer.MAX_VALUE`-ish per call and limited by socket buffer space), so it must be
       called in a loop. Code that ignores the return value silently truncates large files — a real
       and recurring bug. `[API]` `[TRAP]` `[BUILD]`
2.19.8 **Where the JDK and frameworks use it for you**: `Files.copy`, `InputStream.transferTo`
       (which is *not* zero-copy — it is a heap-buffer loop, and the name misleads),
       Netty's `DefaultFileRegion` and `FileRegion`, Tomcat's `sendfile` support
       (`useSendfile`, on by default for static content above a threshold), and Kafka's broker read
       path — the canonical production example. `[API]` `[TABLE]` `[TRAP]`
2.19.9 **TLS is where zero-copy usually dies**, and the two escapes must be named: **kTLS**
       (`4.13+`, `net.ipv4.tcp_available_ulp` contains `tls`, `setsockopt(TCP_ULP, "tls")`) moves
       encryption into the kernel so `sendfile` works on an encrypted socket — but the JDK has no
       kTLS support, so in Java the practical answer is to terminate TLS at
       `ApplicationGateway`/an LB and serve large bodies over plaintext internally. `[NUM]`
       `[VERSION-TRAP]` `[X-REF 10]`
2.19.10 **The QuizStakes case where this actually matters**: `DocumentVerification` streaming
        **2–6 MB** document images at **24k uploads/day (68 GB/day)** to and from object storage.
        Naive heap buffering allocates 2–6 MB per request into the humongous-object path (A.6),
        pressures G1 directly, and copies each byte four times; `transferTo` to the socket or a
        direct-buffer pool avoids both. Do the arithmetic: 68 GB/day × 2 avoidable copies = 136 GB/day
        of memory bandwidth and the associated GC churn. `[CALC]` `[NUM]` `[INCIDENT]`
2.19.11 **When zero-copy is irrelevant and claiming it is a red flag**: small payloads (a
        `ClientRestrictions` decision response is a few hundred bytes — syscall and network cost
        dominate utterly), any path that must inspect, compress, encrypt or transform the bytes, and
        any path already bottlenecked on a downstream. `[PROVE]` `[TRAP]`
2.19.12 **Proving it happened, rather than believing the docs**: `strace -e
        trace=sendfile,sendfile64,splice,write,read -p <pid>` (the presence of `sendfile` and the
        absence of large `read`/`write` pairs is the proof), `perf stat -e syscalls:sys_enter_sendfile`,
        and a before/after of `%sy` CPU and `/proc/<pid>/io`'s `read_bytes`. `[DIAG]` `[BUILD]`

*(12 leaves)*

## §2.20 Swap and the JVM: why a swapping JVM is a dead JVM

2.20.1 **The mechanism restated with the JVM in mind**: swap moves *anonymous* pages to a backing
       device; the Java heap is anonymous; therefore swap can and will take the heap. Page cache is
       reclaimed instead of swapped, so a JVM-heavy box under pressure has essentially nothing else
       to give. `[PROVE]` `[X-REF 12]`
2.20.2 **`vm.swappiness` — default 60**, range 0–200 (the range grew past 100 when cgroup v2
       accounting arrived; >100 biases toward swapping anonymous pages even when cache could be
       dropped). **`0` does not mean "never swap"** — it means "avoid swapping until reclaim
       otherwise fails", which is the correction to the most repeated myth in this area. `[SYSCTL]`
       `[NUM]` `[TRAP]` `[RESEARCH]` (kernel `Documentation/admin-guide/sysctl/vm.rst`, `swappiness`)
2.20.3 **The GC pathology, worked as arithmetic.** A G1 young collection on `FundsLedger` touches,
       say, 500 MB of survivor and remembered-set data in ~20 ms. If **2%** of those pages
       (2,560 pages of 4 KB) have been swapped to EBS at ~1 ms each, the collection additionally
       waits **~2.5 s** — a 125× pause amplification — and because the mark phase is
       pointer-chasing, the faults are serialised and cannot be prefetched. This is the single number
       that ends the "a little swap is fine" argument for a latency-sensitive JVM. `[CALC]` `[NUM]`
       `[PROVE]`
2.20.4 **The second-order effect that makes it worse**: swapping in requires *free* memory, so under
       pressure the kernel swaps something else out to make room, and a GC that touches the whole
       heap causes the entire heap to be swapped in and out repeatedly — **thrashing**. Throughput
       collapses to device IOPS while CPU sits idle and every dashboard says "healthy".
       `[PROVE]` `[TRAP]`
2.20.5 **`memory.swap.max` (default `max`) and `memory.swap.current`, `memory.swap.events`
       (`high`, `max`, `fail`)** are the cgroup v2 controls; `memory.swap.high` throttles before the
       hard limit. Setting `memory.swap.max = 0` disables swap **for that cgroup only**, which is the
       right granularity: swap on for batch cgroups, off for the JVM. `[SYSCTL]` `[NUM]`
       `[RESEARCH]` (cgroup-v2.rst, memory swap files)
2.20.6 **cgroup v1 vs v2 swap accounting is a real behavioural difference**: v1's
       `memory.memsw.limit_in_bytes` limited memory **plus** swap together, so a container could
       trade one for the other; v2 has a **separate** `memory.swap.max`, so `memory.max` is a pure
       physical-memory limit. Advice written for v1 does not transfer. `[VERSION-TRAP]` `[NUM]`
2.20.7 **Kubernetes and swap — the current state, stated with versions.** Kubernetes required swap
       to be **off** for years (the kubelet refused to start with `failSwapOn: true` by default);
       `NodeSwap` reached **beta in 1.28** with `LimitedSwap` (Burstable pods only, proportional to
       the memory request) and `NoSwap` as the default behaviour, and GA work continued through 1.30+.
       For a `Guaranteed` `FundsLedger` pod the answer is still **no swap**. `[VERSION-TRAP]`
       `[NUM]` `[X-REF 19]`
2.20.8 **The correct configuration for a QuizStakes JVM host, as a decision with reasons**:
       swap off (`swapoff -a` + no `fstab` entry) or `memory.swap.max = 0` per cgroup;
       `vm.swappiness = 1` if swap must exist for some other tenant; size the heap so that
       `MaxRAMPercentage` leaves the native headroom of §2.3.10; and **prefer a fast, loud OOM kill
       to a slow, silent death** — a killed pod is rescheduled in seconds, a thrashing pod degrades
       every caller for an hour. `[PROVE]` `[NUM]`
2.20.9 **The counter-argument, stated fairly.** Swap lets the kernel evict genuinely cold anonymous
       pages (a JVM's startup-only structures, an idle sidecar's memory) and can improve *density*
       and survive transient spikes. It is defensible for batch (`BankDeposits`' once-a-day
       ingestion) and indefensible for anything with a p99 budget. State both, then take the
       position. `[PROVE]` `[TABLE]`
2.20.10 **zswap and zram are a third option** — compressed swap in RAM rather than on a device
        (`/sys/module/zswap/parameters/enabled`, `zswap.max_pool_percent` default 20). Latency is
        microseconds not milliseconds, so the GC pathology is far milder, but you have traded memory
        for CPU and still have less usable RAM than you think. Worth knowing, rarely worth deploying
        for a JVM. `[NUM]` `[SYSCTL]`
2.20.11 **Detecting it, per-process and per-box**: `vmstat 1`'s **`si`/`so`** columns (non-zero on a
        latency-sensitive box is an alert, not a curiosity), `free -h`'s `Swap` row,
        `/proc/<pid>/status`'s **`VmSwap`**, `/proc/<pid>/smaps_rollup`'s `Swap:`,
        `cat /sys/fs/cgroup/memory.swap.current`, `sar -W 1`, and
        `awk '/VmSwap/{print FILENAME, $2}' /proc/*/status | sort -k2 -n | tail` to rank processes by
        swapped bytes. `[PROC]` `[DIAG]` `[BUILD]`
2.20.12 **`workingset_refault_anon` in `memory.stat` is the subtle early warning**: it counts
        anonymous pages faulted back in after eviction, which is thrashing *before* `si`/`so` become
        dramatic. Together with `memory.pressure`'s `full avg60`, it is the pair to alert on.
        `[PROC]` `[NUM]` `[DIAG]`
2.20.13 **The `D`-state interaction, because it is how this presents in an incident**: a thread
        faulting a swapped page in is in **uninterruptible sleep**, so it is unkillable, it counts
        toward load average, and `jstack` cannot reach a safepoint — meaning the JVM looks *hung*
        rather than slow, and `kill -9` does nothing. `[TRAP]` `[DIAG]` `[INCIDENT]`

*(13 leaves)*

## §2.21 Disk I/O for a JVM service: logging, `fsync`, journal contention, log rotation

2.21.1 **Logging is a JVM service's dominant disk workload**, and the arithmetic makes the point:
       `ClientRestrictions` at its decision rate with one 400-byte log line per decision on the
       money paths (1,200 stakes/sec + 40 deposits/sec + 12 withdrawals/sec ≈ 1,250/sec) writes
       **500 KB/sec, 43 GB/day, per instance** — 8 instances → 344 GB/day of logs against 68 GB/day
       of document images. State it once and the reader will never again treat logging as free.
       `[CALC]` `[NUM]`
2.21.2 **Synchronous vs asynchronous appenders**: a synchronous appender does a `write(2)` (and
       possibly an `fsync`) **on the request thread**, so p99 latency inherits disk p99 directly.
       Logback's `AsyncAppender` (`queueSize` default **256**, `discardingThreshold` default 20% —
       i.e. it **silently drops** TRACE/DEBUG/INFO when 80% full) and Log4j2's async loggers
       (LMAX Disruptor, `AsyncLoggerConfig.ringBufferSize` default **256×1024**) move it off the
       request thread. Name the defaults, because both defaults surprise people. `[API]` `[NUM]`
       `[TRAP]`
2.21.3 **`immediateFlush` is the setting that costs the most and is noticed the least.** Logback's
       `FileAppender.immediateFlush` defaults to **true**, forcing a `flush()` per event (a syscall,
       though not an `fsync`); setting it false batches into the buffer and can be worth
       double-digit percentages of syscall CPU on a log-heavy service — at the cost of losing the tail
       of the log on `SIGKILL`. `[API]` `[NUM]` `[TRAP]`
2.21.4 **`write` vs `fsync` vs `fdatasync` vs `O_DIRECT` vs `O_SYNC`**, as a table of "what is
       guaranteed when the call returns": nothing durable / data+metadata durable / data durable /
       bypassed page cache but not necessarily durable / durable per write. Logs need **none** of
       these guarantees; a ledger's WAL needs `fdatasync`. Getting this backwards — `fsync`ing logs
       and buffering ledger writes — is a real and catastrophic inversion. `[TABLE]` `[SYSCALL]`
       `[PROVE]`
2.21.5 **The `fsync` budget against QuizStakes' write rate.** `FundsLedger`'s **13,600 entries/sec
       peak** cannot be one `fsync` per entry on gp3 (~1 ms each = 13.6 device-seconds of work per
       wall-clock second). The resolution is **group commit** — the database batches many
       transactions into one `fsync` — so the arithmetic becomes 13,600 entries ÷ ~200 commits/sec ≈
       68 entries per commit. Name this as the reason `commit_delay`/`group_commit` settings exist.
       `[CALC]` `[NUM]` `[X-REF 09]`
2.21.6 **Filesystem journal contention is the mechanism behind "the whole box stalled".** ext4's
       journal (`data=ordered` by default) serialises metadata commits, and `jbd2`'s
       **5-second commit interval** plus a `fsync` from any process can block *unrelated* writers on
       the same filesystem — which is how a noisy log rotation stalls a database on the same volume.
       Symptom: threads in `D` state, `jbd2/nvme0n1p1-8` visible in `top`, `%wa` high. `[TRAP]`
       `[DIAG]` `[NUM]`
2.21.7 **`data=writeback`, `noatime`, `nobarrier` and `commit=` are the ext4 mount options that get
       proposed**, and each must be stated with its risk: `noatime` is free and correct (avoids a
       metadata write per read); `data=writeback` risks stale data after a crash; `nobarrier`/
       `nobarrier`-equivalents risk actual data loss on power failure and should never be used for a
       ledger. XFS is the common alternative and is generally better for large-file and parallel
       workloads. `[TABLE]` `[TRAP]`
2.21.8 **Writeback tuning is what turns a stall into a smooth cost**: `vm.dirty_ratio` (default
       **20%** of available memory — the point at which the *writing process* is forced to write back
       synchronously), `vm.dirty_background_ratio` (default **10%** — when the flusher starts),
       `vm.dirty_expire_centisecs` (**3000** = 30 s), `vm.dirty_writeback_centisecs` (**500** = 5 s).
       On a large-memory box, 20% of 64 GB is **12.8 GB of dirty pages** whose eventual flush is a
       multi-second stall — which is why the modern advice is to lower both ratios or use the
       `_bytes` variants. `[SYSCTL]` `[NUM]` `[CALC]`
2.21.9 **Log rotation done wrong is a disk-full incident with a specific signature.** If the rotator
       deletes or renames the file without the writer reopening it, the writer keeps its fd on the
       unlinked inode: `du` no longer counts the blocks, `df` still does, and the space is never
       reclaimed until the process restarts. Find it with **`lsof +L1`** (`NLINK` = 0). The fix is
       `copytruncate` (with its own race) or a `SIGHUP`/`logrotate postrotate` reopen — and for a
       JVM, Logback's `SizeAndTimeBasedRollingPolicy` doing its own rotation, with
       `totalSizeCap` and `maxHistory` set. `[TRAP]` `[DIAG]` `[FLOW]`
2.21.10 **Container logging has an extra hop that changes the arithmetic**: the JVM writes to
        stdout → the container runtime's json-file/journald driver → the node's log files →
        a shipper (Fluent Bit) → CloudWatch. Each hop buffers; `max-size`/`max-file` on the driver
        (Docker default is **unlimited**, i.e. a disk-full risk) and the kubelet's
        `containerLogMaxSize` (default **10 Mi**, 5 files) are the actual retention. And when the
        pipe's buffer fills because the shipper is behind, **`write` to stdout blocks the JVM
        thread** — a logging outage becoming an application outage. `[TRAP]` `[NUM]` `[X-REF 19]`
2.21.11 **Per-process I/O attribution**: `/proc/<pid>/io` (`rchar`/`wchar` = bytes through the
        syscall interface, `read_bytes`/`write_bytes` = bytes actually to the block layer,
        `cancelled_write_bytes` = dirty pages deleted before writeback — the difference between
        `wchar` and `write_bytes` is exactly the page cache's benefit), `pidstat -d 1`, `iotop -oPa`.
        `[PROC]` `[DIAG]` `[NUM]`
2.21.12 **Device-level attribution**: `iostat -xz 1` and the four columns that matter —
        `r_await`/`w_await` (the latency the application feels, including queueing), `aqu-sz`
        (average queue depth — Little's law again), `%util` (misleading on NVMe/EBS, which service
        many requests in parallel), `rareq-sz`/`wareq-sz` (average request size, which tells you
        whether the workload is random or sequential). `[DIAG]` `[NUM]`
2.21.13 **The EBS-specific failure**: high `await` with modest IOPS means the volume's provisioned
        IOPS or burst credit is exhausted, which is a **billing decision surfacing as a latency
        incident**. Check the CloudWatch `VolumeQueueLength` and `BurstBalance`, and note that
        gp3's baseline 3,000 IOPS is shared by the OS, the logs and the database if they are on one
        volume. `[NUM]` `[INCIDENT]` `[X-REF 18]`
2.21.14 **The I/O scheduler question, answered briefly and correctly for 6.12**: `none` (noop) for
        NVMe and virtio/EBS — the device's own queueing beats the kernel's — `mq-deadline` for
        SATA SSDs, `bfq` for desktop interactivity, never `cfq` (removed with legacy blk).
        Read/set at `/sys/block/<dev>/queue/scheduler`, and check
        `/sys/block/<dev>/queue/{nr_requests,read_ahead_kb,rotational}` while you are there.
        `[PROC]` `[SYSCTL]` `[NUM]`

*(14 leaves)*

## §2.22 Signals and the JVM: `SIGTERM`, `SIGQUIT`, `SIGSEGV`, and the crash log

2.22.1 **The signal table the JVM actually cares about**, with number, catchability and JVM
       behaviour: `SIGHUP` 1 (JVM ignores; historically "reload"), `SIGINT` 2 (runs shutdown hooks),
       `SIGQUIT` 3 (**thread dump to stdout**, JVM keeps running), `SIGILL` 4 / `SIGBUS` 7 /
       `SIGFPE` 8 / `SIGSEGV` 11 (JVM handles these internally — see 2.22.4),
       `SIGKILL` 9 (**uncatchable**, no hooks), `SIGUSR1`/`SIGUSR2` (**used internally by the JVM** —
       do not install handlers), `SIGTERM` 15 (runs shutdown hooks), `SIGXFSZ` 25 (file-size limit).
       `[TABLE]` `[NUM]`
2.22.2 **`kill -3 <pid>` is free diagnostics and must be memorised**: the JVM's signal-dispatcher
       thread catches `SIGQUIT` and writes a full thread dump — every thread, stack, lock owner,
       deadlock detection — to **stdout**, which in a container means the container log
       (`kubectl logs`), and the JVM continues running. `-XX:+DisableAttachMechanism` does **not**
       disable it; `-Xrs` does. `[API]` `[DIAG]` `[NUM]`
2.22.3 **`-Xrs` ("reduce signal usage") is the flag that breaks graceful shutdown**, and it exists
       for hosts that install their own handlers: it stops the JVM installing `SIGINT`/`SIGTERM`/
       `SIGHUP`/`SIGQUIT` handlers, which means **shutdown hooks no longer run on `SIGTERM`** and
       `kill -3` no longer produces a thread dump. If a service ignores `SIGTERM` and nothing else
       explains it, check for `-Xrs`. `[TRAP]` `[API]`
2.22.4 **The JVM deliberately generates and handles `SIGSEGV` in normal operation.** Implicit null
       checks are a `SIGSEGV` on address 0 that the JVM's handler converts into a
       `NullPointerException`, and safepoint polling and stack-banging use protected pages too. So a
       `SIGSEGV` visible under `strace` is **not** a crash, and the presence of a segfault handler is
       why `hs_err` logs distinguish "problematic frame" from a genuine fault. `[PROVE]` `[TRAP]`
       `[SOURCE]`
2.22.5 **The anatomy of `hs_err_pid<pid>.log`**, section by section, because reading it is the skill:
       the header (`# A fatal error has been detected…`, `SIGSEGV (0xb) at pc=…`, `siginfo`), the
       **problematic frame** (`# J 1234 c2 com.quizstakes.ledger.ReservationIndex.expire(…)` = JIT
       code, `# V [libjvm.so+0x…]` = the VM itself, `# C [libssl.so…]` = native library — this one
       line assigns blame), the JVM arguments, the thread list, the **native and Java frames of the
       failing thread**, the heap and metaspace summary, `/proc/meminfo` and `/proc/cpuinfo`
       excerpts, and the `Environment Variables` section. `[SOURCE]` `[DIAG]` `[FLOW]`
2.22.6 **Reading the problematic frame decides who owns the bug**: `V` = a JVM bug or a
       hardware/memory fault, `C` = a native library (JNI, a native SSL provider, a compression
       library), `J` = JIT-compiled Java, usually a compiler bug reproducible with
       `-XX:-TieredCompilation` or `-XX:CompileCommand=exclude`, and a frame in `libc` `malloc` =
       heap corruption from *someone's* native code. `[TABLE]` `[DIAG]`
2.22.7 **`-XX:ErrorFile=/dumps/hs_err_%p.log`** is mandatory in a container, because the default
       writes to the **current working directory** — which on an ephemeral overlay disappears with
       the container, taking the only evidence of the crash. `[API]` `[TRAP]` `[X-REF 19]`
2.22.8 **`SIGBUS` in a JVM has two specific causes worth knowing**: a truncated memory-mapped file
       (§2.19.5), and — on a container — a **`/dev/shm` too small** for the JVM's perf memory
       (`/tmp/hsperfdata`, §2.3.11) or for a mapped buffer. Both present as a crash with no Java
       stack. `[TRAP]` `[DIAG]`
2.22.9 **`SIGXCPU`, `SIGXFSZ` and `SIGPIPE`**: the first two arrive when `RLIMIT_CPU`/`RLIMIT_FSIZE`
       are exceeded (§2.15.9); `SIGPIPE` is **ignored by the JVM** and the write instead returns
       `EPIPE`, which surfaces as `java.io.IOException: Broken pipe` — which is why a Java service
       does not die when a client disconnects mid-response, and why "broken pipe" is a client-side
       event, not a server fault. `[NUM]` `[TRAP]` `[X-REF 10]`
2.22.10 **Java's signal API surface, such as it is**: `Runtime.addShutdownHook`,
        `Signal`/`SignalHandler` in `sun.misc` (unsupported, and `SIGUSR1`/`SIGUSR2`/`SIGQUIT` must
        not be taken), and `ProcessHandle.destroy()` (SIGTERM) vs `destroyForcibly()` (SIGKILL) for
        child processes. State the recommendation: use shutdown hooks or Spring's lifecycle, never a
        raw handler. `[API]` `[TRAP]`
2.22.11 **Shutdown hooks: the complete rules.** They are unstarted `Thread`s run **concurrently and
        in unspecified order**, with no timeout — so a hook that blocks forever hangs the JVM until
        the orchestrator SIGKILLs it. They do **not** run on `SIGKILL`, on `Runtime.halt()`, on a
        JVM crash, or on `System.exit` from within a hook (which deadlocks). Therefore they are
        best-effort cleanup and never a durability mechanism. `[API]` `[TRAP]` `[PROVE]`
2.22.12 **Sending signals into a container**: `kubectl exec <pod> -- kill -3 1` (needs the pid
        namespace and a shell), `crictl exec`, `docker kill -s QUIT`, or `kill -3` from the node
        against the **host-side pid** (`crictl inspect | jq .info.pid`). Note the trap: PID 1 will
        not receive a signal whose disposition is default (§2.13.4) — but `SIGQUIT` is *handled* by
        the JVM, so this works precisely because the JVM installed a handler. `[BUILD]` `[DIAG]`
        `[TRAP]`
2.22.13 **`jcmd` is the modern replacement for signal-based diagnostics** and should be preferred
        where it exists: `jcmd <pid> Thread.print`, `GC.heap_info`, `GC.heap_dump`,
        `VM.native_memory`, `VM.flags`, `VM.system_properties`, `JFR.start`,
        `Thread.dump_to_file`. It uses the attach mechanism (a Unix socket in `/tmp`, hence
        `-XX:+DisableAttachMechanism` breaks it and `/tmp` must be writable), which is exactly why
        `kill -3` remains the fallback. `[API]` `[DIAG]` `[TRAP]`

*(13 leaves)*

## §2.23 Graceful shutdown in a container: PID 1, signal propagation, grace periods

2.23.1 **The complete Kubernetes termination sequence, in order and with the concurrency made
       explicit.** (1) The pod is marked `Terminating` and (2) **simultaneously** removed from
       `Endpoints`/`EndpointSlice` *and* sent to the kubelet for termination — these are concurrent,
       not sequential. (3) `preStop` hook runs to completion (counted inside the grace period).
       (4) `SIGTERM` to PID 1 of each container. (5) Wait up to
       **`terminationGracePeriodSeconds`, default 30**. (6) `SIGKILL`. `[FLOW]` `[NUM]`
       `[X-REF 19]`
2.23.2 **Step 2's concurrency is the source of the dropped requests**, and the mechanism must be
       named: endpoint removal must propagate to kube-proxy/the CNI on every node and to any external
       load balancer (an ALB target-group deregistration takes **seconds to tens of seconds**), while
       `SIGTERM` arrives in milliseconds. For that window the LB still sends traffic to a pod that
       has begun shutting down. `[PROVE]` `[NUM]` `[TRAP]`
2.23.3 **The fix is a `preStop` sleep, and the reason is arithmetic, not superstition**:
       `lifecycle.preStop.exec.command: ["sleep","10"]` (or `sleep` with a `sleep` binary present —
       distroless images need `["/bin/sleep"]` or the 1.30+ `sleep` action) delays `SIGTERM` until
       deregistration has propagated. Size it from the observed propagation time plus a margin, and
       **add it to the grace period**, because `preStop` runs inside it. `[BUILD]` `[CALC]` `[NUM]`
2.23.4 **Readiness must fail before draining starts, and the ordering is the whole design.** The
       correct order is: fail readiness → wait for LBs to notice → stop accepting new work → drain
       in-flight → flush → close pools → exit 0. Closing the pool before draining fails every
       in-flight request; exiting before deregistration drops new ones. State both failure modes
       explicitly. `[FLOW]` `[PROVE]` `[TRAP]`
2.23.5 **`SIGTERM` reaches your JVM only if PID 1 forwards it.** With shell-form
       `ENTRYPOINT java -jar app.jar`, `/bin/sh -c` is PID 1, the JVM is a child, and `sh` neither
       forwards signals nor waits properly — so the JVM never sees `SIGTERM`, sits until the grace
       period expires, and is **SIGKILLed on every single deploy**, silently. Symptom: pod
       termination always takes exactly `terminationGracePeriodSeconds`, and exit code **137**
       (not 143) on a normal rollout. `[TRAP]` `[NUM]` `[DIAG]` `[INCIDENT]`
2.23.6 **The three fixes, with their trade-offs**: exec-form
       `ENTRYPOINT ["java","-jar","/app/app.jar"]` (the JVM *is* PID 1 — simplest, but the JVM must
       then reap any children it spawns); `exec java -jar app.jar` as the last line of a wrapper
       script (keeps the script's setup, replaces the shell); or an init —
       `docker run --init` / `tini -- java …` / `dumb-init` — which forwards signals to the process
       *group* and reaps zombies (§2.14.11). `[BUILD]` `[TABLE]`
2.23.7 **The `exit 143` vs `exit 137` distinction is the fastest deploy diagnostic there is**:
       143 = 128 + 15 = the process received `SIGTERM` and exited, i.e. graceful shutdown worked;
       137 = 128 + 9 = it was killed, i.e. either it ignored `SIGTERM` or it exceeded the grace
       period (or it was OOM-killed — disambiguate with `memory.events`, §2.11). `[NUM]` `[DIAG]`
2.23.8 **Spring Boot's graceful shutdown, exactly**: `server.shutdown=graceful` (default
       **`immediate`** — so it is **off** unless you set it) makes the web server stop accepting new
       requests and wait for active ones; the wait is bounded by
       `spring.lifecycle.timeout-per-shutdown-phase`, default **30s**. It is driven by
       `SmartLifecycle` phases, so `@PreDestroy`/`DisposableBean` beans are destroyed *after* the web
       layer drains — which is why the datasource is still available to in-flight requests. `[API]`
       `[NUM]` `[FLOW]`
2.23.9 **The deadlock the brief calls out, spelled out with numbers.** Kubernetes
       `terminationGracePeriodSeconds: 30` and Spring's
       `timeout-per-shutdown-phase: 30s` are **equal by default**, so a request that takes the full
       30 s to drain means the JVM is still shutting down at the instant Kubernetes sends `SIGKILL` —
       and worse, a `preStop: sleep 10` consumes 10 of the 30, leaving Spring 20 s of a 30 s budget.
       The rule: `terminationGracePeriodSeconds` **>** `preStop` duration **+**
       `timeout-per-shutdown-phase` **+** a margin; e.g. `preStop 10` + Spring `20s` + 10 s margin →
       `terminationGracePeriodSeconds: 45`. `[CALC]` `[NUM]` `[TRAP]`
2.23.10 **What "in flight" means for QuizStakes is a business question, not a technical one.** A
        draining `FundsLedger` instance may hold **stake reservations** that are neither settled nor
        voided — reserved money in `CLIENT_CASH_RESERVED`/`CLIENT_BONUS_RESERVED` with an expiry
        index that lives in that instance's memory (§6.4 partition affinity). Shutting down must not
        silently drop the index: either the reservations are recoverable from the ledger on the new
        owner, or draining must wait for them. State that a 30 s grace period cannot possibly
        "drain" a reservation whose natural lifetime is *seconds to hours*, so the answer must be
        recovery, not waiting. `[PROVE]` `[INCIDENT]`
2.23.11 **The other services' drain requirements differ and the table makes the point**:
        `ApplicationGateway` (drain = finish sub-second HTTP requests, 5 s is plenty),
        `PaymentService` calling a PSP with a **p99 of 11 s** (a 30 s grace period is barely
        adequate, and a `capture` timeout is `Timeout ≠ failure` — dropping it mid-flight risks a
        double charge), `BankWithdrawal` mid-`PaymentRun` (must **not** be interrupted; a leader-lease
        and idempotent restart, not a longer grace period), `BankDeposits` mid-file (checkpoint the
        offset). `[TABLE]` `[PROVE]`
2.23.12 **Queue and message consumers need an explicit drain step that HTTP frameworks give you for
        free**: stop polling, finish or return in-flight messages (visibility timeout, not `ack`),
        commit offsets. A consumer that is SIGKILLed mid-handler causes a redelivery, which is only
        safe if the handler is idempotent — which for QuizStakes is guaranteed by the
        idempotency-key-plus-unique-constraint design (B.2), and this is where that pays off.
        `[FLOW]` `[X-REF 19]`
2.23.13 **JVM-side implementation, complete and runnable**: `SpringApplication` with
        `server.shutdown=graceful`, a `@PreDestroy` that closes the Kafka consumer,
        `-XX:+ExitOnOutOfMemoryError`, an actuator readiness group that a `preStop` can flip
        (`management.endpoint.health.group.readiness.include`), and — for the non-Spring case — a
        shutdown hook that fails readiness, awaits an `AtomicInteger` of in-flight requests with a
        deadline, then closes resources in reverse acquisition order. `[BUILD]` `[API]`
2.23.14 **Verifying it rather than believing it**: roll a deployment and assert
        `lastState.terminated.exitCode == 143` and a termination duration well under the grace
        period; run a load test through a rolling restart and assert **zero** 502/503 at the LB.
        A graceful-shutdown claim with no failed-request count is not a claim. `[DIAG]` `[BUILD]`

*(14 leaves)*

## §2.24 CPU profiling: `perf`, async-profiler, flame graphs, `perf_event_paranoid`

2.24.1 **Sampling vs instrumenting, and why the JVM makes this harder than C.** Sampling
       (`perf`, async-profiler, JFR) interrupts periodically and records stacks — low overhead,
       statistically complete. Instrumenting (a JVMTI agent, `-agentlib`, most "APM" profilers)
       rewrites bytecode — precise counts, but a 2–10× slowdown and inlining disabled, which changes
       the thing being measured. `[PROVE]` `[TABLE]`
2.24.2 **`perf` and the `perf_event_open(2)` syscall** are the kernel's sampling interface; the
       basic commands are `perf top -p <pid>`, `perf record -F 99 -g -p <pid> -- sleep 30`,
       `perf report`, `perf script`, and `perf stat -e <events> -p <pid>`. `perf list` enumerates
       hardware and software events. `[SYSCALL]` `[BUILD]` `[API]`
2.24.3 **`kernel.perf_event_paranoid` — default `2`** — is the gate, and its values are:
       **−1** = all events, including raw tracepoints; **0** = no CPU-event restriction but no raw
       tracepoint access; **1** = no kernel profiling for unprivileged users;
       **2** = **no kernel *or* CPU event access, user-space measurements only**; some distributions
       and Debian/Ubuntu patches add **3** (nothing without `CAP_PERFMON`). A container therefore
       usually needs `kernel.perf_event_paranoid=1` on the *node* plus `CAP_PERFMON` (or
       `CAP_SYS_ADMIN` pre-5.8) and a seccomp profile that permits `perf_event_open`. `[SYSCTL]`
       `[NUM]` `[TRAP]`
2.24.4 **`kernel.kptr_restrict` (default `1`)** hides kernel symbol addresses, so `perf report` shows
       hex instead of function names for kernel frames; set it to `0` to symbolise the kernel side.
       Together with `perf_event_paranoid` this is why "perf shows nothing useful in a container" is
       almost always a permissions problem, not a tooling problem. `[SYSCTL]` `[NUM]` `[TRAP]`
2.24.5 **Why plain `perf` on a JVM produces a useless flame graph**: JIT-compiled frames have no
       symbols in any ELF file, so they appear as bare addresses, and the JVM's default
       frame-pointer omission (`-XX:-OmitStackTraceInFastThrow` is unrelated; the relevant flag is
       **`-XX:+PreserveFramePointer`**, off by default) breaks `-g` stack walking. The two fixes are
       `-XX:+PreserveFramePointer` plus `perf-map-agent`, or — far simpler — async-profiler.
       `[TRAP]` `[API]` `[PROVE]`
2.24.6 **async-profiler is the right default tool for a JVM**, and the reason is `AsyncGetCallTrace`:
       it walks Java stacks from a signal handler **without** requiring a safepoint, so it does not
       suffer **safepoint bias** — the systematic error where safepoint-based profilers
       (`hprof`, most JVMTI samplers, `jstack` loops) can only sample at safepoint polls and
       therefore systematically miss hot loops that contain none. `[PROVE]` `[TRAP]` `[SOURCE]`
2.24.7 **async-profiler's event modes, each answering a different question**: `-e cpu`
       (`perf_event` cycles — needs `perf_event_paranoid` ≤ 1), `-e itimer` (a fallback that works
       with no privileges at all — **the container answer**), `-e wall` (wall-clock, including
       blocked time — the one that finds a hung downstream), `-e alloc` (TLAB-based allocation
       profiling), `-e lock`, `-e ctimer`, plus `--alloc`/`--live` for heap. State the rule: `cpu`
       for "which code burns CPU", `wall` for "why is this request slow". `[TABLE]` `[API]` `[NUM]`
2.24.8 **Invocation, three ways**: attach (`asprof -d 30 -e cpu -f /tmp/out.html <pid>`), start-up
       (`-agentpath:/opt/async-profiler/lib/libasyncProfiler.so=start,event=cpu,file=/tmp/out.html`),
       and via `jcmd`-style `AsyncProfiler` API. Attach requires the same-namespace access and
       writable `/tmp` as `jcmd` (§2.22.13), which is why a **debug sidecar sharing the pod's pid
       namespace** (`shareProcessNamespace: true`) is the standard EKS pattern. `[BUILD]` `[X-REF 19]`
2.24.9 **Reading a flame graph correctly**, because it is misread constantly: the **x-axis is not
       time**, it is alphabetically-sorted merged samples; **width = share of samples**; **height =
       stack depth**, not cost. A wide *plateau* is where CPU goes; a tall thin spike is deep but
       cheap. Look for plateaus, then for unexpected frames (a `Pattern.compile` in a hot loop, a
       `String.format` in a log statement below the enabled level, `sun.nio.ch.SocketDispatcher`
       meaning you are I/O-bound). `[PROVE]` `[DIAG]` `[TABLE]`
2.24.10 **Differential flame graphs are the technique that finds regressions**: profile the old and
        new builds under identical load and render the delta
        (`FlameGraph/difffolded.pl`, or async-profiler's `--diff`). Red = new cost. This turns "the
        new release is 15% slower" from a debate into a diagnosis. `[BUILD]` `[DIAG]`
2.24.11 **JFR is the always-on complement, not a competitor**: `-XX:StartFlightRecording=
        settings=profile,maxsize=256m,maxage=1h,dumponexit=true,filename=/dumps/qs.jfr` costs
        **~1–2%** with `profile` settings (~0.5% with `default`), and gives execution samples,
        allocation, monitor contention, safepoint, GC, thread-park and socket events with a
        correlated timeline — which a flame graph does not. The production posture is JFR always on,
        async-profiler on demand. `[API]` `[NUM]` `[BUILD]`
2.24.12 **`perf` for the things async-profiler cannot see** — because half of a JVM's problems are in
        the kernel: `perf stat -e context-switches,cpu-migrations,page-faults,dTLB-load-misses,
        LLC-load-misses -p <pid>`, `perf record -e sched:sched_switch` (who preempts whom),
        `perf trace` (a `strace` that scales), and the BCC/bpftrace tools (`runqlat`, `offcputime`,
        `biolatency`, `execsnoop`) which are the modern answer to "where is the off-CPU time".
        `[BUILD]` `[DIAG]`
2.24.13 **The observer-effect discipline**: profiling in production is correct and normal, but state
        the costs — async-profiler `cpu` at 99 Hz ≈ **<1%**, `wall` at high rates on thousands of
        threads can be several percent, `alloc` at a small interval is worse, and a JVMTI
        instrumenting profiler can be 10×. Always profile the *same* build under the *same* load;
        a profile of a warm-up phase is a profile of the JIT. `[NUM]` `[PROVE]`

*(13 leaves)*

## §2.25 Latency debugging: run-queue delay, steal time, PSI, noisy neighbours

2.25.1 **The reframe this whole section depends on**: request latency = service time +
       **wait time**, and on a busy Linux box most of the tail is wait — waiting for a CPU, for a
       lock, for a disk, for a downstream. Utilisation tells you nothing about wait; only queueing
       does (§2.26). `[PROVE]`
2.25.2 **Run-queue delay is the metric almost nobody collects and the one that explains most
       unexplained p99.** It is the time a task spent *runnable but not running*, exported as the
       second field of `/proc/<pid>/schedstat` (and per-thread in
       `/proc/<pid>/task/<tid>/schedstat`), aggregated in `/proc/schedstat`, and measured
       distributionally by `runqlat` (BCC/bpftrace). A run-queue delay of 20 ms on a service with a
       30 ms budget is the entire incident. `[PROC]` `[NUM]` `[DIAG]`
2.25.3 **`/proc/<pid>/sched` and the `se.statistics` fields** give the same information per-task
       (`wait_sum`, `wait_max`, `wait_count`, `iowait_sum`, `nr_involuntary_switches`) — and
       `nr_involuntary_switches` climbing fast is the signature of CPU contention rather than
       blocking. `[PROC]` `[DIAG]`
2.25.4 **PSI is the best single starvation signal available**, and it must be read correctly:
       `/proc/pressure/{cpu,memory,io}` and the per-cgroup `cpu.pressure`/`memory.pressure`/
       `io.pressure`, each with `some` (≥1 task stalled) and `full` (all non-idle tasks stalled)
       lines carrying `avg10=`, `avg60=`, `avg300=` percentages and a `total=` in **microseconds**.
       A real line: `some avg10=12.44 avg60=8.31 avg300=3.02 total=48219341`. Note that CPU `full`
       is meaningless at the system level (reported as 0) but is meaningful per-cgroup.
       `[PROC]` `[NUM]` `[SOURCE]` `[RESEARCH]` (kernel `Documentation/accounting/psi.rst`)
2.25.5 **Why PSI beats load average and utilisation**: load average is host-wide and not namespaced
       (§2.13.6), includes `D`-state tasks, and needs `nproc` to interpret; utilisation is an average
       that hides the bimodality throttling creates (§2.10.3). PSI directly measures **lost time**,
       is per-cgroup, and needs no normalisation. Alert on `memory.pressure` `full avg60 > 1%` and
       `cpu.pressure` `some avg60 > 20%`. `[PROVE]` `[NUM]`
2.25.6 **Steal time (`%st`) is the hypervisor telling you it took your vCPU.** Read it from `top`,
       `vmstat 1`'s `st` column, `mpstat -P ALL 1`, or field 8 of `/proc/stat`'s `cpu` line. On
       shared-tenancy EC2 (`t3`/`t4g` burstable, and any oversubscribed host) sustained `%st` above
       a few percent means a neighbour; the fix is an instance change (dedicated, or a non-burstable
       family), not a code change. `[PROC]` `[NUM]` `[X-REF 18]`
2.25.7 **Burstable instances have a *second* throttling mechanism that looks identical to steal**:
       `t3`-family CPU credits, where exhausting the credit balance caps you at the baseline (e.g.
       **t3.medium: 20% of 2 vCPUs**) — or, in `unlimited` mode, charges you instead. Symptom:
       latency degrades on a schedule (after a burst) with no code change; evidence is the
       CloudWatch `CPUCreditBalance`, not anything on the box. **No latency-sensitive QuizStakes
       service belongs on a burstable instance.** `[NUM]` `[TRAP]` `[X-REF 18]`
2.25.8 **The noisy-neighbour taxonomy**, because "noisy neighbour" is used for four different
       things: (a) another *tenant* on the hypervisor → `%st`; (b) another *pod* on the node →
       `cpu.pressure`, run-queue delay, no steal; (c) another *container in the same pod* (a
       sidecar) → pod-level cgroup contention, and the sidecar's CPU counts against the pod's limit;
       (d) another process in the same *container*. Each is diagnosed differently and fixed
       differently. `[TABLE]` `[DIAG]` `[TRAP]`
2.25.9 **The "everything is idle and the service is slow" playbook**, which is the most common real
       shape: CPU idle, no throttling, no steal, low `%wa` — therefore the time is spent **blocked**.
       Order of investigation: thread dump ×3 (pool exhaustion, lock convoy), `wall`-clock profile
       (async-profiler `-e wall`), `offcputime`/`offwaketime` (BPF, which attributes off-CPU time to
       the stack that blocked *and* the thread that woke it), then downstream latency metrics.
       `[FLOW]` `[DIAG]`
2.25.10 **The interrupt and softirq dimension**: high `%si` means packet processing is consuming a
        core; `/proc/interrupts` and `/proc/softirqs` show the per-CPU distribution, and a single CPU
        taking all `NET_RX` softirqs (no RSS/RPS spread, or a single-queue NIC) pins one core at 100%
        while 15 idle. `irqbalance`, RSS queue counts and
        `/sys/class/net/<dev>/queues/rx-*/rps_cpus` are the levers. `[PROC]` `[NUM]` `[X-REF 10]`
2.25.11 **Timer and clock-source effects on measured latency**: `CONFIG_HZ` (typically **250** or
        1000) sets the tick and therefore the granularity of some scheduler decisions;
        `nohz_full` reduces ticks on isolated CPUs; and a degraded `current_clocksource` (§2.1.3)
        makes every `nanoTime()` a syscall, inflating instrumented latency by more than the thing
        being measured. `[PROC]` `[NUM]` `[TRAP]`
2.25.12 **The full latency-triage order, as the one thing to memorise from this section**:
        (1) is the request slow at the *edge* or at a *hop* (tracing);
        (2) `cpu.pressure`/`memory.pressure`/`io.pressure`;
        (3) `cpu.stat` `nr_throttled`; (4) `%st` and CPU credits; (5) run-queue delay;
        (6) GC log `Real` vs `User`; (7) safepoint log `Reaching` vs `At`;
        (8) thread dumps ×3; (9) wall-clock profile; (10) downstream p99. Stop at the first one that
        explains the magnitude. `[FLOW]` `[DIAG]` `[PROVE]`
2.25.13 **Correlate with what changed, always.** Deploy time, config change, traffic level, a
        specific AZ, a specific node, a specific instance — an OS-level cause that appeared without
        any of those changing is rare, and the sequence "it started at 14:07, the canary went out at
        14:06" beats any amount of profiling. `[PROVE]` `[X-REF 20]`

*(13 leaves)*

## §2.26 Utilisation, queueing and Little's law at the CPU

2.26.1 **Little's law, stated and then used**: **L = λW** — concurrency = arrival rate × residence
       time. It is an identity, not a model: it needs no assumption about distributions and holds for
       any stable system. Every capacity number in this guide is one rearrangement of it. `[PROVE]`
       `[CALC]`
2.26.2 **Use it three ways, each answering a real question.** L = λW: at 1,200 stake reservations/sec
       and 150 ms, **180 concurrent** requests exist in the system (60 per `FundsLedger` instance).
       W = L/λ: a 400-deep queue drained at 400/sec adds **1 s**. λ = L/W: 60 in-flight at 150 ms
       is a per-instance capacity of 400/sec — so three instances are exactly at capacity at
       sustained rate and **2.8× oversubscribed at the 3,400/sec settlement burst**. `[CALC]`
       `[NUM]` `[PROVE]`
2.26.3 **The utilisation law**: U = λ × S (service demand), so a service taking 2 ms of CPU per
       request at 400 requests/sec consumes **0.8 CPU-seconds/second** = 0.8 of one core. This is how
       you convert a latency budget into a CPU request instead of guessing. `[CALC]` `[NUM]`
2.26.4 **The queueing-delay curve is the single most important shape in performance work**: for an
       M/M/1 approximation, W = S / (1 − U). At U = 0.5 latency is 2× service time; at 0.8 it is
       **5×**; at 0.9 it is **10×**; at 0.95 it is **20×**. Tabulate it. The consequence: a target of
       70–80% CPU utilisation is not timidity, it is the arithmetic of the tail. `[CALC]` `[TABLE]`
       `[PROVE]`
2.26.5 **Multiple servers change the curve favourably (Erlang-C intuition without the algebra)**:
       n servers at the same utilisation queue far less than one server, which is why 8
       `ClientRestrictions` instances at 80% behave better than 2 at 80%, and why consolidating onto
       fewer, larger instances degrades the tail even at identical total utilisation. `[PROVE]`
       `[NUM]`
2.26.6 **Variability is the third term everyone omits.** With the same mean service time, higher
       variance means longer queues (the Kingman approximation: delay scales with
       (C²ₐ + C²ₛ)/2). QuizStakes' PSP with **p50 240 ms and p99 11 s** has enormous service-time
       variance, so `PaymentService`'s queue behaves far worse than its mean would suggest — this is
       why bulkheads and per-dependency concurrency limits exist rather than one shared pool.
       `[CALC]` `[NUM]` `[PROVE]`
2.26.7 **CPU utilisation as reported is not the CPU's utilisation.** `/proc/stat` counts a CPU as
       busy if any task was on it, but SMT/hyperthreading means two logical CPUs share one physical
       core's execution units, so **100% across all logical CPUs is roughly 60–70% of the core's
       actual throughput** — the reason throughput flattens well before the graph reaches 100%.
       Check `lscpu`'s `Thread(s) per core`. `[TRAP]` `[NUM]` `[PROVE]`
2.26.8 **Frequency scaling breaks the "CPU-second" as a unit**: turbo boost, thermal and power
       limits, and `intel_pstate`/`amd-pstate` governors mean a CPU-second at 3.6 GHz and one at
       2.1 GHz do different amounts of work. Read
       `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq` and
       `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` (`performance` vs `powersave`);
       `turbostat` shows the real picture. On EC2 this is largely out of your hands, which is itself
       the point: measure work done, not CPU seconds. `[PROC]` `[NUM]` `[TRAP]`
2.26.9 **Amdahl's law bounds every "add more threads" plan**: speedup ≤ 1/(s + p/n). With **5%**
       serial work the ceiling is **20×** no matter how many cores — and for a JVM the serial
       fraction includes safepoints, a single-threaded GC phase, a contended lock, and
       `FundsLedger`'s deliberate single-writer design. Compute the ceiling before buying cores.
       `[CALC]` `[NUM]` `[PROVE]`
2.26.10 **The Universal Scalability Law adds the term Amdahl lacks** — **coherency** (crosstalk),
        which makes throughput *decrease* past a peak rather than plateau. This is why adding
        threads past the knee makes a contended service slower, and it is the formal statement of
        §2.4.3's empirical rule. `[PROVE]` `[CALC]`
2.26.11 **Coordinated omission is the measurement error that invalidates most published latency
        numbers**: a load generator that waits for a response before sending the next request stops
        measuring exactly when the system is slowest, so a 30 s stall produces one slow sample
        instead of thousands. Use a constant-*rate* generator (wrk2, Gatling with
        `constantUsersPerSec`, JMeter with a throughput shaper), and never a "1,000 threads in a
        loop" harness. `[TRAP]` `[PROVE]` `[NUM]`
2.26.12 **Percentiles do not add, and this is where the 30 ms budget really breaks.**
        `ProfileService`'s eight-owner fan-out waits for the slowest leg, so if each leg is
        independent with a p99 of 50 ms, the probability that *all* eight are under 50 ms is
        0.99⁸ = **92.3%** — i.e. the fan-out's p99 is the legs' **p99.9**, not their p99. Compute it,
        then state the fixes: hedged requests, per-leg timeouts below the total budget, and
        returning partial results. `[CALC]` `[NUM]` `[PROVE]`
2.26.13 **The capacity-planning recipe, end to end, for one QuizStakes service**: measure service
        demand per request (`perf stat` CPU-seconds ÷ requests), multiply by peak arrival rate for
        the CPU requirement, divide the target utilisation (0.7) in, add the queueing-delay check
        against the budget, then size instances for the *failure* case (n−1 available during a
        rolling deploy, or n−1 AZs). Do it for `ClientRestrictions` at its 30 ms budget and show why
        8 instances is the answer. `[CALC]` `[BUILD]` `[NUM]`

*(13 leaves)*

## §2.27 The failure catalogue: twenty-four OS-caused production incidents

Every leaf is one incident: a symptom line and a root-cause line, each drawn from a QuizStakes
service. The write pass must render each as symptom → the one command that disambiguates → root
cause → fix, in that order and nothing else.

2.27.1 **`FundsLedger` pods restart every 40–90 minutes with no application error and no stack
       trace.** Root cause: `-Xmx12g` in a 12 GB container — heap plus 1.7 GB of native (§2.3.1)
       exceeded `memory.max`, cgroup OOM kill, exit **137**, no heap dump possible (§2.11.7). Fix:
       16 GB limit with `-XX:MaxRAMPercentage=75`. `[INCIDENT]`
2.27.2 **`ClientRestrictions` p99 jumps from 18 ms to 140 ms while average CPU utilisation reads
       35%.** Root cause: `limits.cpu: 0.4` → `cpu.max 40000 100000`, eight request threads
       exhausting the quota in 5 ms and freezing for 95 ms (§2.10.3); `nr_throttled/nr_periods` =
       0.71. Fix: raise or remove the limit; shrink the period only if the limit must stay.
       `[INCIDENT]`
2.27.3 **`ClientRestrictions` GC pauses grew 6× after a "cost optimisation" that changed nothing
       else.** Root cause: `limits.cpu` reduced from 2 to 0.8 → `ceil(0.8)` = 1 →
       `availableProcessors()` = 1 → ergonomics selected **SerialGC** and `ParallelGCThreads=1`
       (§2.12.9). Fix: `-XX:ActiveProcessorCount=2` plus an explicit `-XX:+UseG1GC`. `[INCIDENT]`
2.27.4 **Every `ApplicationGateway` rollout takes exactly 30 seconds per pod and drops ~200 requests
       per pod.** Root cause: shell-form `ENTRYPOINT`, `/bin/sh` as PID 1, `SIGTERM` never reaching
       the JVM, grace period exhausted, exit **137** on a *normal* deploy (§2.23.5). Fix: exec form,
       plus `server.shutdown=graceful`. `[INCIDENT]`
2.27.5 **A rolling `PaymentService` deploy produced 14 duplicate card captures.** Root cause:
       `terminationGracePeriodSeconds: 30` against a PSP capture **p99 of 6 s** and an authorise
       p99 of **11 s** — in-flight captures were SIGKILLed, the retry re-submitted, and "timeout ≠
       failure" (A.4) did the rest. Fix: grace period 45 s + `preStop` 10 s + idempotency key
       enforced by the unique constraint. `[INCIDENT]`
2.27.6 **Clients saw 502s for ~8 seconds at the start of every `ProfileService` deploy, even though
       shutdown was graceful.** Root cause: endpoint removal and `SIGTERM` are concurrent, and the
       ALB target-group deregistration lagged the pod's shutdown (§2.23.2). Fix:
       `preStop: sleep 10` and readiness failure before drain. `[INCIDENT]`
2.27.7 **`FundsLedger` p99 went from 90 ms to 4.5 s over two hours with CPU at 30% and no GC log
       anomaly in `User` time.** Root cause: the node began swapping; `si`/`so` non-zero,
       `VmSwap: 1840128 kB`, and a young collection touching swapped survivor pages amplified a 20 ms
       pause to seconds (§2.20.3). Fix: `memory.swap.max = 0` for the cgroup and correct heap sizing.
       `[INCIDENT]`
2.27.8 **`ApplicationGateway` began returning `Too many open files` at 09:00 every Monday.** Root
       cause: `RLIMIT_NOFILE` soft = 1024 from a systemd default (§2.14.10) against a legitimate
       working set of ~2,200 fds at the Monday-morning session peak (§2.16.3) — a limit problem, not
       a leak: the count was high and *stable*. Fix: `LimitNOFILE=65536`, verified in
       `/proc/<pid>/limits`. `[INCIDENT]`
2.27.9 **`PaymentService` fd count climbed 40/hour forever and the pod died every 30 hours.** Root
       cause: an fd **leak** — `HttpResponse` bodies from the PSP client not consumed on the error
       path, so pooled connections were never returned; `ss -tanp` showed thousands in
       `CLOSE_WAIT` (§2.16.8). Fix: try-with-resources; raising the limit only bought 30 more hours.
       `[INCIDENT]`
2.27.10 **`FundsLedger` threw `OutOfMemoryError: unable to create native thread` with 6 GB of the
        12 GB heap free.** Root cause: a *native* limit, not heap — the pod's `pids.max` (kubelet
        `podPidsLimit` 4096) was reached by a `newCachedThreadPool` growing unboundedly while the
        PSP was slow (§2.4.6, §2.9.12). Fix: a bounded `ThreadPoolExecutor` with an
        `ArrayBlockingQueue`. `[INCIDENT]`
2.27.11 **`DocumentVerification` stalled for 400–900 ms at unpredictable intervals, with high `%sy`
        and nothing in the GC log.** Root cause: THP `enabled=always` plus `defrag=always`, so 2 MB
        allocations for document buffers triggered **synchronous compaction** in the request thread;
        `compact_stall` in `/proc/vmstat` was climbing (§2.7.6). Fix: `madvise` +
        `-XX:+UseTransparentHugePages` + `AlwaysPreTouch`. `[INCIDENT]`
2.27.12 **`DocumentVerification` OOM-killed under a document-upload campaign while its heap was 40%
        free.** Root cause: 2–6 MB `ByteBuffer.allocateDirect` buffers with
        `-XX:MaxDirectMemorySize` unset (defaulting to `-Xmx` = 8 GB, §2.3.6) plus page cache from
        68 GB/day of image streaming pushing `memory.current` to `memory.max` (§2.6.8). Fix: an
        explicit direct-memory cap, a pooled allocator, and `transferTo` instead of heap buffering.
        `[INCIDENT]`
2.27.13 **`ProfileService`'s p99 was 620 ms even though all eight owners reported a p99 under
        50 ms.** Root cause: not an OS fault at all — percentile composition. 0.99⁸ = 92.3%, so the
        fan-out's p99 is each leg's p99.9 (§2.26.12). Fix: per-leg timeouts below the total budget,
        partial results, and hedging on the slowest owner. `[INCIDENT]`
2.27.14 **One `FundsLedger` instance ran one core at 100% while the other 15 sat idle, and throughput
        was a third of the other two instances.** Root cause: a Java NIO busy-loop —
        `OP_WRITE` left registered on an always-writable socket, so `epoll_wait` returned
        immediately forever (§2.17.6); `top -H` → `printf '%x'` → `jcmd Thread.print` named the
        thread in one minute. Fix: register `OP_WRITE` only after a short write. `[INCIDENT]`
2.27.15 **`BankDeposits` file ingestion took 6 hours instead of 20 minutes, with threads in `D`
        state and load average 40 on an otherwise idle box.** Root cause: the statement file
        (40k records, 500k at month end) was being written to the writable overlay, so every write
        paid overlayfs copy-up and contended with the container runtime on the node's `imagefs`
        (§2.14.3–4); `%wa` was 70%. Fix: an `emptyDir` volume and `java.io.tmpdir` pointed at it.
        `[INCIDENT]`
2.27.16 **`/var` filled to 100% on a node while `du -sh /var/log` reported 2 GB of 200 GB.** Root
        cause: `logrotate` deleted the log file without the JVM reopening it, so the writer held an
        fd on an unlinked inode — `df` counted the blocks, `du` did not, `lsof +L1` showed
        `NLINK 0` (§2.21.9). Fix: Logback's own rolling policy with `totalSizeCap`, and
        `copytruncate` removed. `[INCIDENT]`
2.27.17 **`ClientRestrictions` breached its 30 ms budget for 3–5 seconds every 60 seconds, in
        lockstep across all 8 instances.** Root cause: `vm.dirty_ratio` at the default 20% of a
        64 GB node = 12.8 GB of dirty pages, flushed in bulk, stalling every writer on the shared
        volume — including the synchronous log appender with `immediateFlush=true` (§2.21.3, §2.21.8).
        Fix: `dirty_background_bytes`/`dirty_bytes` lowered, and an async appender. `[INCIDENT]`
2.27.18 **`PaymentService` latency degraded every afternoon and recovered overnight, with `%st` at
        0 and no throttling.** Root cause: a `t3.large` node exhausting its **CPU credit balance**
        and being capped at the baseline (§2.25.7) — invisible on the box, visible only in
        CloudWatch `CPUCreditBalance`. Fix: move to a non-burstable instance family. `[INCIDENT]`
2.27.19 **`FundsLedger` p99 doubled after the node was replaced with a larger, "identical" instance
        type.** Root cause: the new shape was **two NUMA nodes**, `AlwaysPreTouch` put the entire
        12 GB heap on node 0 via first-touch, and half the cores then ran remote at ~1.8× memory
        latency (§2.8.4). Fix: `numactl --interleave=all` or CPU-Manager `static` + Topology Manager
        `single-numa-node`. `[INCIDENT]`
2.27.20 **A `FundsLedger` scale-up from 3 to 4 instances lost 61 stake reservations.** Root cause:
        the in-memory reservation expiry index is partition-affine (§6.4), and the draining
        instance's 30 s grace period cannot possibly cover a reservation whose lifetime is
        "seconds to hours" (§2.23.10) — the reservations were neither settled nor voided when the
        owner exited. Fix: recover the index from the ledger on the new owner; never treat the
        grace period as a drain for long-lived state. `[INCIDENT]`
2.27.21 **`InternalPlatforms` operators were logged out mid-review roughly hourly, and the pod
        showed exit code 143 with no error.** Root cause: not a crash — a **node eviction** under
        memory pressure, and `InternalPlatforms` was `Burstable` QoS with
        `oom_score_adj` near 1000 while `FundsLedger` sat at −997 (§2.11.4). Fix: correct
        requests/limits so session-bearing pods are not the first eviction candidate. `[INCIDENT]`
2.27.22 **After enabling virtual threads, `PaymentService` throughput collapsed to 8 concurrent
        requests under PSP slowness on JDK 21.** Root cause: `synchronized` around the PSP call
        pinned each carrier thread, and with a scheduler parallelism of 8 all carriers were pinned
        (§2.5.5); `-Djdk.tracePinnedThreads=full` named the frame. Fix: `ReentrantLock`, or JDK 24+
        where JEP 491 removes the cause. `[INCIDENT]`
2.27.23 **`FundsLedger` heap-dump-on-OOM produced a 0-byte file, twice.** Root cause: the dump path
        was on the writable overlay with an `ephemeral-storage` limit smaller than the 12 GB heap, so
        the write failed and — because the container was then evicted — even the partial file was
        lost (§2.14.4, §2.22.7). Fix: `-XX:HeapDumpPath` on a sized `emptyDir` plus
        `-XX:+ExitOnOutOfMemoryError` and always-on JFR with `dumponexit`. `[INCIDENT]`
2.27.24 **`ApplicationGateway` stopped picking up `ConfigMap` changes across the whole node, with no
        error in any log.** Root cause: `fs.inotify.max_user_instances` (default **128**, per-UID
        and host-wide) exhausted by the pods on that node, so new watches failed silently
        (§2.15.12). Fix: raise the sysctl on the node; poll rather than watch where possible.
        `[INCIDENT]`

*(24 leaves)*

---

## Sources consulted — PART C

- <https://docs.kernel.org/admin-guide/cgroup-v2.html> — the authoritative defaults for every cgroup v2
  interface file used in §2.9–§2.12 and §2.20: `memory.max`/`memory.high`/`memory.swap.max` default
  `max`, `memory.low`/`memory.min` default `0`, `memory.oom.group` default `0`, the
  `memory.events` field list (`low`, `high`, `max`, `oom`, `oom_kill`, `oom_group_kill`),
  `cpu.max` default **`max 100000`**, `cpu.max.burst` default `0`, `cpu.weight` default `100`
  (range 1–10000), the full `cpu.stat` field list (`usage_usec`, `user_usec`, `system_usec`,
  `nr_periods`, `nr_throttled`, `throttled_usec`, `nr_bursts`, `burst_usec`), `pids.max` default
  `max` with `pids.current`/`pids.peak`/`pids.events`, `io.weight` default `default 100`, the
  `io.max` key set (`rbps`, `wbps`, `riops`, `wiops`), and the controller list
  (`cpu`, `io`, `memory`, `pids`, `cpuset`, `perf_event`).
- <https://docs.kernel.org/admin-guide/sysctl/vm.html> — `vm.max_map_count` default **65530** (§2.2.10),
  `vm.swappiness` default **60** (§2.20.2), `vm.overcommit_memory` default **0** (§2.6.11),
  `vm.panic_on_oom` and `vm.oom_kill_allocating_task` default **0**, `vm.watermark_scale_factor`
  default **10** = 0.1% of node memory (§2.6.12), and `vm.zone_reclaim_mode` **disabled by default**
  (§2.8.9).
- <https://docs.kernel.org/accounting/psi.html> — the exact PSI file set
  (`/proc/pressure/{cpu,memory,io}` plus per-cgroup `cpu.pressure`/`memory.pressure`/`io.pressure`),
  the two-line `some`/`full avg10= avg60= avg300= total=` format with `total` in microseconds, the
  precise definitions of `some` ("at least some tasks are stalled") and `full` ("all non-idle tasks
  are stalled"), and the note that system-level CPU `full` is reported as zero. Used in §2.9.14 and
  §2.25.4.
- <https://man7.org/linux/man-pages/man7/namespaces.7.html> — the eight namespace types with their
  `CLONE_NEW*` flags, `/proc/[pid]/ns` entry names and introduction versions, confirming **cgroup
  namespace 4.6** and **time namespace 5.6**, and that the time namespace covers boot and monotonic
  clocks only. Used in §2.13.1 and §2.13.11.
- <https://openjdk.org/jeps/491> — that `synchronized`-monitor pinning was removed in **JDK 24**, that
  `Object.wait()` also unmounts after the JEP, that the residual pinning causes are class loading,
  blocking inside a class initializer and waiting for another thread to initialise a class, and that
  the `jdk.tracePinnedThreads` system property is **removed** (setting it has no effect). Used in
  §2.5.4–§2.5.5.
- <https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html> — the JDK 21 `java` man page:
  `-XX:+UseContainerSupport` "The default for this flag is `true`, and container support is enabled by
  default"; `-XX:ActiveProcessorCount` "Overrides the number of CPUs that the VM will use to calculate
  the size of thread pools it will use for various operations such as Garbage Collection and
  ForkJoinPool"; `-XX:ReservedCodeCacheSize` default **240 MB** (48 MB without tiered compilation);
  `-Xss` default **1024 KB** on Linux/x64 and **2048 KB** on Linux/aarch64;
  `-XX:+UseLargePages` and `-XX:+UseTransparentHugePages` both **disabled by default**, the latter
  documented as "made available for experimentation"; `-XX:LargePageSizeInBytes` default **0**;
  `-XX:+HeapDumpOnOutOfMemoryError` **disabled by default**; `-XX:MaxDirectMemorySize` unset means the
  JVM chooses. Used in §2.3, §2.4.8, §2.7.3, §2.7.8, §2.12.1 and §2.12.8.
