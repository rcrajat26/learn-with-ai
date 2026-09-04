# Syllabus — 11 Operating Systems & Linux

**Target version baseline (checked 2026-09-04).** Every constant, sysctl name, default value,
`/proc` path, syscall signature, cgroup interface file and JVM flag below is stated against this set
of kernels, libraries and releases, and every leaf that depends on a version says so:

| Layer | Normative source this file targets |
|---|---|
| Kernel | **Linux 6.12 LTS** as primary, **6.6 LTS** cited wherever EEVDF, PREEMPT or MGLRU behaviour differs; kernel `Documentation/admin-guide/`, `Documentation/scheduler/`, `Documentation/mm/`, `Documentation/accounting/psi.rst` |
| Scheduler | **EEVDF** (merged 6.6, `kernel/sched/fair.c`), `Documentation/scheduler/sched-design-CFS.rst`, `sched-rt-group.rst`, `sched-bwc.rst`; `/sys/kernel/debug/sched/*` |
| Memory management | `Documentation/admin-guide/sysctl/vm.rst`, `Documentation/admin-guide/mm/transhuge.rst`, `Documentation/admin-guide/mm/multigen_lru.rst`, `Documentation/mm/overcommit-accounting.rst` |
| cgroups | **cgroup v2 unified hierarchy** as the only supported layout (`Documentation/admin-guide/cgroup-v2.rst`); cgroup v1 named only as historical `[VERSION-TRAP]` material |
| Syscall / libc interface | **`man-pages` 6.x** (`man 2 *`, `man 5 proc`, `man 7 *`), **glibc 2.39+** manual, `Documentation/ABI/` |
| Pressure / accounting | `Documentation/accounting/psi.rst`, `Documentation/filesystems/proc.rst` |
| Observability | `perf` from the 6.12 tree, `Documentation/admin-guide/sysctl/kernel.rst` (`perf_event_paranoid`), `bpftrace` 0.21+, `bcc`, `Documentation/bpf/` |
| Init & supervision | **systemd 255+** (`man 5 systemd.exec`, `systemd.resource-control`, `systemd.kill`, `journald.conf`) |
| Java runtime | **Java 21 LTS** for all code and all flag defaults; JDK 24/25 deltas marked `[VERSION-TRAP]`; OpenJDK JEPs 425/444/491, `hotspot/os/linux` sources |
| Framework | **Spring Boot 3.5.x** (`server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase`, Actuator probes) |
| Containers | **containerd 2.x / runc 1.2+**, OCI runtime spec 1.1, Docker Engine 27.x, **Kubernetes 1.31+** (`terminationGracePeriodSeconds`, NodeSwap beta, `topologyManager`) |
| Deployment target | **Amazon Linux 2023** (kernel 6.1/6.12 series) on EC2 and **EKS 1.31+**, Nitro instance families, EBS gp3/io2 |
| Filesystems / block | ext4 and XFS as shipped on AL2023, `Documentation/block/`, `/sys/block/*/queue/*`, overlayfs |

## The seventeen deltas that most often produce a stale operating-systems answer

Each is marked `[VERSION-TRAP]` at its leaf.

1. **CFS is no longer the Linux scheduler.** **EEVDF** (Earliest Eligible Virtual Deadline First)
   replaced the CFS picking logic in **Linux 6.6** and is what 6.12 runs. `vruntime` still exists,
   but the pick is no longer "lowest `vruntime`" — it is "eligible task with the earliest virtual
   deadline", where eligibility comes from a per-task **`lag`** (its credit or debt against the fair
   share) and the deadline comes from a requested **slice**. `sched_latency_ns` and
   `sched_min_granularity_ns` are gone; the tunable is
   `/sys/kernel/debug/sched/base_slice_ns` (**750,000 ns** by default). An answer built on
   `sched_latency_ns / nr_running` is a pre-6.6 answer. `[RESEARCH]`
2. **cgroup v1 is not the layout you are running on.** Every current distribution — Amazon Linux
   2023, RHEL 9, Ubuntu 22.04+, Debian 12 — boots the **cgroup v2 unified hierarchy** by default.
   The file names changed completely: `cpu.cfs_quota_us`/`cpu.cfs_period_us` became a single
   `cpu.max` (`"max 100000"` by default), `memory.limit_in_bytes` became `memory.max` (`"max"`),
   `cpu.shares` became `cpu.weight` (**100**, range 1–10000). Guides naming `cpu.cfs_quota_us` are
   pre-2021. `[RESEARCH]`
3. **The reclaim algorithm is no longer necessarily two LRU lists.** **MGLRU** (multi-generational
   LRU) landed in **6.1** and is a build/runtime option gated on `CONFIG_LRU_GEN` and toggled at
   `/sys/kernel/mm/lru_gen/enabled` (bit `0x0001` is the main switch). Reasoning about "the active
   list and the inactive list" is only correct when MGLRU is off. `[RESEARCH]`
4. **Load average is the wrong pressure signal and has been since 4.20.** **PSI** exposes
   `/proc/pressure/{cpu,memory,io}` with `some` and `full` lines carrying `avg10`/`avg60`/`avg300`
   percentages and a `total` in **microseconds** of stall. Per-cgroup equivalents are
   `cpu.pressure`, `memory.pressure`, `io.pressure`. Load average conflates runnable tasks with
   `D`-state tasks and has no denominator; PSI is a saturation measurement. `[RESEARCH]`
5. **`-XX:+UseContainerSupport` is on by default** (since JDK 10) and the JVM reads `memory.max`
   and `cpu.max` from cgroup v2 with no flags at all. The stale answer is "the JVM doesn't know
   it's in a container"; the current trap is different — **`MaxRAMPercentage` defaults to 25.0**, so
   an unflagged JVM in a 4 GB container takes a **1 GB** heap and wastes three quarters of the
   limit. `[NUM]`
6. **CPU count and CPU quota are different things.** `Runtime.availableProcessors()` under cgroup
   v2 returns `ceil(quota / period)` from `cpu.max`, not the host core count, and
   `-XX:ActiveProcessorCount` overrides it. A `cpu.max` of `"150000 100000"` yields **2**
   processors, not 1.5 — which sizes `ForkJoinPool.commonPool` at 1 and G1's `ParallelGCThreads`
   from 2. `[CALC]`
7. **THP defaults are distro-dependent, not kernel-uniform.** `/sys/kernel/mm/transparent_hugepage/enabled`
   is `always` on RHEL-family images and `madvise` on Debian/Ubuntu. "THP is always on in Linux" is
   wrong; so is "THP is off". You must read the file. `[RESEARCH]`
8. **`vm.swappiness` is no longer a 0–100 knob.** The documented range is **0–200** (extended in
   5.8): "a value between 0 and 200. At 100, the VM assumes equal IO cost". Default is still **60**.
   Every tuning guide describing 100 as the maximum predates 5.8. `[RESEARCH]`
9. **io_uring is the current high-performance I/O interface and is also widely disabled.**
   `io_uring_setup`/`io_uring_enter`/`io_uring_register` give batched, submission-queue I/O with
   near-zero syscalls, but its CVE history led Docker's and Kubernetes' default seccomp profiles and
   several hardened distributions to block `io_uring_setup` outright. "Just use io_uring" is not
   deployable advice without checking the seccomp profile. `[RESEARCH]`
10. **`perf` does not work out of the box.** `kernel.perf_event_paranoid` defaults to **2**, which
    per `Documentation/admin-guide/sysctl/kernel.rst` "Disallow kernel profiling by users without
    `CAP_PERFMON`"; several distributions and container runtimes ship 3 or higher, and
    `perf_event_open` is blocked by the default Docker seccomp profile entirely. `[RESEARCH]`
11. **`PREEMPT_RT` is mainline as of 6.12.** The realtime preemption model is no longer an
    out-of-tree patch set, and 6.12 also carries the `PREEMPT_LAZY`/preemption-model work. Answers
    describing RT Linux as "a patch you apply" are pre-6.12. `[RESEARCH]`
12. **Virtual threads no longer pin on `synchronized`.** **JEP 491 (JDK 24)** removed
    `synchronized`-block pinning and removed the `jdk.tracePinnedThreads` property. On Java 21 a
    virtual thread blocking inside `synchronized` pins its carrier and can starve the
    `ForkJoinPool`; from 24 it does not. Both statements are version-scoped. `[VERSION-TRAP]`
13. **The fd limit defaults moved twice.** systemd 240+ deliberately keeps the *soft* `RLIMIT_NOFILE`
    at **1024** (for `select()` compatibility) while raising the *hard* limit to **524288**, and
    `fs.nr_open` (**1048576**) caps what the hard limit may be raised to. Docker/containerd stopped
    inheriting the daemon's limits and set a large default. "Containers default to 1024 fds" is now
    runtime-specific, and the only authoritative answer is `/proc/<pid>/limits`. `[RESEARCH]`
14. **eBPF has superseded SystemTap and DTrace-for-Linux.** `bpftrace` one-liners, `bcc` tools
    (`execsnoop`, `biolatency`, `offcputime`, `runqlat`) and `perf` are the current toolkit; a
    SystemTap answer dates you and usually does not even compile against a 6.x kernel.
15. **`top` and `free` inside a container lie.** They read `/proc/meminfo` and `/proc/stat`, which
    are the **host's** unless something (lxcfs, a masked `/proc`) intercepts them. The container's
    real figures are `memory.current`, `memory.max` and `cpu.stat` in
    `/sys/fs/cgroup/`. `[PROC]` `[TRAP]`
16. **`vm.overcommit_memory=2` is not "the safe setting" for a JVM host.** Under mode 2 the kernel
    refuses any allocation past `CommitLimit`, and since the JVM reserves its whole heap virtually
    up front, a `FundsLedger` instance with a 12 GB heap can fail to start — or fail to `fork` for
    a `Runtime.exec` — on a box with abundant free RAM.
17. **Kubernetes no longer requires swap off.** `NodeSwap` reached **beta** and `LimitedSwap` lets
    burstable pods use swap; the historical `swapoff -a` requirement is a pre-1.22 fact. It remains
    the right choice for `FundsLedger` for GC reasons, but "Kubernetes forbids swap" is stale.
    `[RESEARCH]`

## Scope boundary against the sibling guides

This file owns **the machine**: the abstractions the kernel provides to a process, the cost each
one charges, the file or counter that measures it, and the production failure each one produces.
Owned elsewhere:

- The wire — TCP state machine, congestion control, MTU/MSS, TLS handshakes, HTTP semantics, DNS,
  socket options as *protocol* tuning, and `epoll` as the engine of a network server — lives in
  `10-networking.md`. This guide owns file descriptors, `epoll`/`io_uring` and blocking-vs-readiness
  as **kernel mechanisms**, and it owns `ss`/`lsof` as general triage. `[X-REF 10]`
- Java concurrency semantics — the memory model, `ThreadPoolExecutor` sizing, `CompletableFuture`,
  locks, `ThreadLocal`, and the virtual-thread *programming model* — lives in
  `05-multithreading-concurrency.md` and `04-modern-java.md`. This guide owns what a thread **is**
  to the kernel, what its creation and switching cost, and how a carrier thread maps to a
  `task_struct`. `[X-REF 05]` `[X-REF 04]`
- Heap sizing strategy, GC algorithm selection, generational layout, NMT workflow and heap-dump
  analysis live in `06-jvm-internals.md`. This guide owns **the JVM as a Linux process**: its RSS
  composition, its `mmap` regions, its page-fault and THP behaviour, and why the kernel killed it.
  `[X-REF 06]`
- The Kubernetes object model — Deployments, probes, QoS classes, requests/limits as a *scheduling
  contract*, CNI, CSI — lives in `19-docker-kubernetes.md`. This guide owns **namespaces, cgroups,
  overlayfs, seccomp and capabilities as kernel mechanisms**, and PID 1 semantics. `[X-REF 19]`
- Metrics, tracing, SLOs, alerting and dashboard design live in `20-observability-operations.md`.
  This guide owns `/proc`, `/sys`, `perf`, `ftrace`, eBPF and the raw counters those systems
  scrape. `[X-REF 20]`
- Instance-family selection, EBS volume products, burst credits as a billing construct, and managed
  service limits live in `18-cloud-aws.md`. This guide owns the **block layer** underneath: the
  request queue, schedulers, `iostat` fields, and what `await` is actually measuring. `[X-REF 18]`
- Durability at the database level — WAL, checkpoints, isolation, index design, `fsync` as a
  transaction guarantee — lives in `09-sql-databases.md`. This guide owns `fsync`/`fdatasync`,
  the page cache and writeback as **syscalls and kernel state**. `[X-REF 09]`
- Capabilities, seccomp, `setuid`, namespace escapes and container breakout as an **adversary
  model** live in `13-web-security.md`. This guide owns them as isolation primitives with a stated
  mechanism. `[X-REF 13]`
- Test isolation, containerised test infrastructure and flaky-test diagnosis live in
  `16-testing.md`. `[X-REF 16]`
- Queueing theory as a design activity, capacity arithmetic, Little's Law applied to architecture,
  and load shedding as a product decision live in `22-system-design.md`. This guide owns the
  run-queue and device-queue instances of the same mathematics. `[X-REF 22]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the
mechanism in one paragraph *before* pointing away — it never sends the reader off empty-handed.

## The example domain

**Every example, service name, heap size, instance count, rate and budget comes from the QuizStakes
domain in `src/scenario/scenario.md`.** The OS-relevant surfaces this file must keep returning to:

`ClientRestrictions` — **4 GB heap, 8 instances**, "extreme request rate, trivial objects", sitting
synchronously on every money path inside a **30 ms p99 budget**. It is the allocation-rate and
scheduler-latency example: heap size barely matters, run-queue delay and context-switch count
dominate.

`FundsLedger` — **12 GB heap, 3 instances**, partition-affine by client id, holding a long-lived
in-memory reservation expiry index, **230 writes/sec sustained and 13,600/sec peak** against
**19.8M ledger entries/day**. It is the page-fault, THP, swap, `fsync` and OOM-killer example: a
GC that traverses 12 GB is the reason `si`/`so` must be zero, and the 59:1 peak-to-sustained ratio
is the reason its memory cannot be provisioned for the average.

`DocumentVerification` — **8 GB heap, 6 instances**, **2–6 MB document image buffers**, 24k
uploads/day → **68 GB/day**. It is the `mmap`-threshold, direct-buffer, page-cache and glibc-arena
example.

`ApplicationGateway` — **2 GB heap, scaling 12 → 40 instances**, terminating client TLS and
stripping the client token. It is the fd-limit, `epoll`, ephemeral-port and graceful-shutdown
example.

`BankDeposits` — **6 GB heap, 2 instances**, a once-daily **40k-record** statement file (500k at
month end) arriving at 06:00, idle 23 hours. It is the readahead, writeback, `D`-state and
page-cache-cold example.

`BankWithdrawal` — **6 GB heap, 2 instances**, owning `PaymentRun` (**1.8k records, 4 files/day**),
operator-gated, requiring **drain-before-terminate**. It is the signal-handling, PID 1 and
distributed-cron example.

`InternalPlatforms` — **4 GB heap, 3 instances**, session-affine, **30–90 minute** operator
sessions, 40 operators on shift (90 at peak).

The figures that constrain every capacity claim: **2.4M registered clients**, **14k concurrent
sessions (55k peak)**, **95k card deposits/day at 40/sec**, **2.8M stake reservations/day at
1,200/sec with 3,400/sec settlement bursts**, **19.8M ledger entries/day at ~180 bytes/row**, a
**30 ms restriction budget**, an **80 ms balance-read budget**, a **150 ms stake-reservation
budget**, a hard **500 ms self-exclusion budget**, and a card-PSP p99 of **11 s** on authorise.

Never `myapp`, never `foo`, never `thread1`, never `/var/log/app.log` where
`/var/log/fundsledger/application.log` is meant.

## Tag legend

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real kernel source/documentation, man-page text, glibc source or OpenJDK source (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code, or a complete runnable artifact where the artifact is a shell session, a unit file, a `bpftrace` script or a config file |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte/latency arithmetic explicitly |
| `[SYSCTL]` | give the exact sysctl, cgroup interface file or `ulimit`/`RLIMIT_*` name and its default value |
| `[SYSCALL]` | name the exact syscall and give its signature |
| `[PROC]` | name the exact `/proc` or `/sys` path and show a real line of its content |
| `[FLOW]` | must be rendered as an ordered step-by-step trace |
| `[TABLE]` | must be rendered as a table |
| `[API]` | must state the exact Java/Spring type, method signature, JVM flag or system-property name |
| `[DIAG]` | must show real diagnostic output — a `top` header, a `vmstat` line, a `dmesg` OOM record, a `perf` histogram, a stack trace — and read it line by line |
| `[CALC]` | must show the arithmetic (page counts, quota shares, switch costs, RSS composition, fd budgets) |
| `[INCIDENT]` | must be framed as a production failure: symptom, diagnosis path, root cause, fix |

---

# PART 1 — BASICS

Everything a backend engineer must be able to state cold: what the kernel provides, what each
abstraction costs, and which file measures it. No leaf here is optional.

## §1.1 Why the operating system is a backend discipline, not an ops detail

1.1.1 The problem statement: every latency number a service publishes is the sum of time spent
      **computing**, **waiting for the kernel**, and **waiting to be scheduled**. Only the first is
      visible in application profiling, and on a loaded box it is frequently the smallest of the
      three. `[PROVE]`
1.1.2 The four questions an engineer is actually paid to answer about a box: *why is it slow*, *why
      did it die with no stack trace*, *why does it only fail under load*, and *why does it behave
      differently in the container than on my laptop*. Each maps to a specific part of this guide.
      `[TABLE]`
1.1.3 The kernel is a **shared, preemptive, oversubscribed resource arbiter**, not a library. Three
      `FundsLedger` instances at 12 GB each on one host are competing for page cache, run-queue
      slots, block-device queue depth and memory bandwidth — none of which appear in any of the
      three JVMs' own metrics. `[PROVE]`
1.1.4 The `ClientRestrictions` framing that makes this concrete: a **30 ms p99** budget on every
      money path, served by 8 instances of a 4 GB JVM. A single 12 ms scheduler run-queue delay or
      one 8 ms major fault consumes a third of the budget before a line of business logic runs.
      `[NUM]` `[CALC]`
1.1.5 The five resources and the one signal for each: CPU (`/proc/pressure/cpu`), memory
      (`/proc/pressure/memory`), block I/O (`/proc/pressure/io`), network (`ss -ti`, `nstat`), and
      **file descriptors** (`/proc/<pid>/fd`) — the fifth is the one people forget and it is the
      most common hard failure. `[PROC]` `[TABLE]`
1.1.6 What "the OS" is composed of as code: the syscall entry path, the scheduler, the memory
      manager, the VFS and page cache, the block layer, the network stack, the device drivers, and
      the interrupt/softirq machinery. Every one holds state, every one has a queue, and every
      queue can be the bottleneck. `[TABLE]`
1.1.7 The single most useful mental habit: **for every symptom, name the resource and name the
      file that measures it.** "The box is slow" is not a diagnosis; `avg10=41.2` on
      `/proc/pressure/io` is. `[PROC]`
1.1.8 Why the interview asks: "the service is slow and you have SSH" cannot be faked, cannot be
      memorised as a script, and reveals in ninety seconds whether the candidate has ever been on
      call. `[X-REF 20]`
1.1.9 The three classes of OS-caused production failure, with a QuizStakes instance of each:
      **resource exhaustion** (`ApplicationGateway` hitting `RLIMIT_NOFILE` at 55k concurrent
      sessions), **latency injection** (`FundsLedger` majoring-faulting its reservation index back
      from swap during a settlement burst), and **silent death** (a `DocumentVerification` pod
      OOM-killed with exit **137** and no Java stack trace). `[TABLE]`
1.1.10 `[INCIDENT]` Symptom: `ClientRestrictions` p99 jumps from 11 ms to 340 ms with no code
       change, no traffic change, and CPU utilisation at 38%. Diagnosis: `/proc/pressure/cpu`
       `some avg10=62.00` while `top` shows idle CPU — the box is not CPU-*busy*, it is
       CPU-*contended*, because 8 instances were co-scheduled onto a host also running a batch
       `BankDeposits` ingestion. Root cause: no CPU quota on the batch workload, so `cpu.weight`
       arbitration starved the latency-sensitive service. Fix: `cpu.max` on the ingestion cgroup
       and anti-affinity for `ClientRestrictions`. This is the whole guide in one incident.
       `[INCIDENT]` `[PROC]`
1.1.11 The honest boundary of this guide: it does not teach kernel development. It teaches the
      subset of kernel behaviour that is **observable from userspace, tunable from userspace, and
      capable of taking your service down**.

*(11 leaves)*

## §1.2 The user/kernel boundary: privilege levels, kernel space, and what a "kernel" actually is

1.2.1 x86-64 privilege rings: **ring 0** (kernel) and **ring 3** (user); rings 1 and 2 exist
      architecturally and are unused by Linux. The `CPL` field of `CS` holds the current level, and
      only a controlled transition (syscall, interrupt, exception) may change it. `[NUM]`
1.2.2 What privilege actually buys: access to privileged instructions (`lgdt`, `mov` to `CR3`,
      `hlt`, `wrmsr`, `in`/`out`), and access to page-table entries whose `U/S` bit marks them
      supervisor-only. Userspace cannot touch a kernel page even with a valid virtual address — the
      MMU refuses it. `[PROVE]`
1.2.3 The canonical x86-64 split under a 4-level page table: **user space `0x0000_0000_0000_0000`
      – `0x0000_7fff_ffff_ffff` (128 TiB)**, a non-canonical hole, then **kernel space
      `0xffff_8000_0000_0000` – `0xffff_ffff_ffff_ffff` (128 TiB)**. Under 5-level paging the user
      half extends to **64 PiB** (`0x00ff_ffff_ffff_ffff`). `[NUM]` `[CALC]`
1.2.4 The kernel is mapped into **every** process's address space at the same high addresses, which
      is why a syscall does not require a page-table switch — only a privilege transition.
      `[PROVE]`
1.2.5 **KPTI (Kernel Page Table Isolation)** breaks exactly that property in response to Meltdown:
      with KPTI the user page table contains only a trampoline, and every syscall/interrupt swaps
      `CR3`, adding a TLB cost. Check with
      `/sys/devices/system/cpu/vulnerabilities/meltdown` and `dmesg | grep -i 'page table
      isolation'`. `[PROC]` `[NUM]`
1.2.6 Monolithic vs microkernel, stated precisely: Linux is **monolithic with loadable modules** —
      drivers, filesystems and network protocols run in ring 0 in the same address space, which is
      why a bad driver panics the box and a bad userspace daemon does not. `[TABLE]`
1.2.7 `lsmod`, `modinfo <mod>`, `modprobe`, `/proc/modules`, and why a tainted kernel
      (`/proc/sys/kernel/tainted`) changes the support conversation. `[PROC]`
1.2.8 Kernel threads are not processes: they appear in `ps` with names in square brackets
      (`[kswapd0]`, `[kworker/3:1H]`, `[jbd2/nvme0n1p1-8]`, `[ksoftirqd/0]`), have no user address
      space (`VmSize` absent from `/proc/<pid>/status`), and cannot be killed. Recognising
      `[kswapd0]` at 100% CPU is a memory-reclaim diagnosis, not a mystery process. `[DIAG]`
      `[PROC]`
1.2.9 What is *not* in the kernel and is often assumed to be: the shell, `libc`, the dynamic
      loader, DNS resolution (glibc NSS in userspace), `systemd`, and the container runtime. "The
      OS did X" usually means glibc or systemd did X. `[TRAP]`
1.2.10 The three ways userspace and kernel exchange data: **syscalls** (§1.3), **memory-mapped
       interfaces** (`/proc`, `/sys`, `mmap`, shared rings such as io_uring), and **signals /
       eventfd / netlink** as asynchronous notification. `[TABLE]`
1.2.11 `copy_to_user` / `copy_from_user` as the reason a kernel/user boundary crossing costs a copy,
       and why zero-copy interfaces (`sendfile`, `splice`, `MSG_ZEROCOPY`, io_uring registered
       buffers) exist to avoid it. `[SOURCE]` `[X-REF 10]`
1.2.12 `[INCIDENT]` Symptom: after a kernel upgrade on the `FundsLedger` hosts, throughput drops
       ~14% with identical code and identical hardware. Diagnosis: `perf stat` shows unchanged IPC
       but a large rise in `dTLB-load-misses`, and `/sys/devices/system/cpu/vulnerabilities/*`
       now reports mitigations active. Root cause: KPTI plus retpoline on a syscall-heavy write
       path — 13,600 ledger writes/sec is 13,600 boundary crossings/sec minimum. Fix: batch the
       writes so the syscall count per entry falls, rather than disabling mitigations.
       `[INCIDENT]` `[CALC]`

*(12 leaves)*

## §1.3 Syscalls: the mechanism, the ABI, and the cost

1.3.1 The x86-64 syscall ABI exactly: syscall **number in `rax`**, arguments in **`rdi`, `rsi`,
      `rdx`, `r10`, `r8`, `r9`** (note `r10`, not `rcx` — `rcx` is clobbered by the `syscall`
      instruction), return value in `rax`. Maximum **six** register arguments, which is why
      `clone3` and `io_uring_setup` take a struct pointer. `[NUM]` `[SOURCE]`
1.3.2 The `syscall` instruction mechanics: it loads `RIP` from `MSR_LSTAR`, sets `CPL=0`, saves the
      return address in `rcx` and `RFLAGS` in `r11`, and jumps to `entry_SYSCALL_64`; `sysretq`
      reverses it. The older `int 0x80` path still exists for 32-bit compatibility and is
      significantly slower. `[SOURCE]` `[NUM]`
1.3.3 Errno is not part of the kernel ABI: the kernel returns **`-errno` in `rax`** (values in
      `-1..-4095`); the glibc wrapper detects that range, stores the positive value in the
      thread-local `errno`, and returns `-1`. This is why `strace` shows `= -1 ENOENT (No such file
      or directory)` and why `errno` is meaningless unless the call actually failed. `[PROVE]`
      `[SOURCE]`
1.3.4 The cost of a trivial syscall, quantified: on the order of **50–100 ns** on an unmitigated
      pre-2018 CPU, and typically **250–600 ns** with KPTI, retpoline and IBRS active. Compare a
      function call at **~1–2 ns**. A syscall is therefore roughly **100–500× a function call** and
      roughly **1/1000th of the 30 ms `ClientRestrictions` budget** — which is why syscall count,
      not syscall cost, is the design variable. `[CALC]` `[NUM]`
1.3.5 The **vDSO** as the syscall you don't make: `clock_gettime`, `gettimeofday`, `time` and
      `getcpu` are implemented in a page mapped into every process (visible as `[vdso]` and
      `[vvar]` in `/proc/<pid>/maps`), executing in ring 3 at **~20–25 ns**. This is why
      `System.nanoTime()` is cheap enough to call per request. `[PROC]` `[NUM]` `[API]`
1.3.6 `[SYSCALL]` The syscalls a backend engineer must be able to name and sign:
      `read(int fd, void *buf, size_t count)`, `write`, `openat(int dirfd, const char *pathname,
      int flags, mode_t mode)`, `close`, `mmap(void *addr, size_t length, int prot, int flags,
      int fd, off_t offset)`, `munmap`, `mprotect`, `brk`, `clone3`, `execve`, `wait4`,
      `futex(uint32_t *uaddr, int futex_op, uint32_t val, ...)`, `epoll_wait`, `sendto`, `recvfrom`,
      `fsync`, `nanosleep`, `getdents64`, `ioctl`. Syscall numbers live in
      `arch/x86/entry/syscalls/syscall_64.tbl`. `[TABLE]` `[SYSCALL]`
1.3.7 **`futex` is the syscall behind every Java lock.** Uncontended `synchronized` and
      `ReentrantLock` acquisition never enters the kernel (CAS on a header word / an atomic state
      field); contention calls `futex(FUTEX_WAIT)` to sleep and `futex(FUTEX_WAKE)` to release.
      Seeing `futex` dominate `strace -c` output is a **lock contention** diagnosis, not an I/O
      one. `[SYSCALL]` `[X-REF 05]`
1.3.8 `[DIAG]` Reading `strace -c -f -p <pid>` output: the `% time`, `seconds`, `usecs/call`,
      `calls` and `errors` columns, and the four shapes to recognise — dominant `futex`
      (contention), dominant `read`/`write` with tiny `usecs/call` (unbuffered I/O), dominant
      `epoll_wait` (healthy idle), and a high `errors` count on `EAGAIN` (busy-polling a
      non-blocking fd). `[DIAG]`
1.3.9 **`strace` is a ptrace-based debugger and costs 10–100× in overhead**, because it stops the
      tracee twice per syscall. Never attach it to `FundsLedger` at 13,600 writes/sec. The
      production-safe alternatives are `perf trace`, `bpftrace`, and the `bcc` tools, which read
      tracepoints without stopping the process. `[TRAP]` `[X-REF 20]`
1.3.10 `[BUILD]` A `bpftrace` one-liner that counts syscalls per name for one pid without stopping
       it: `bpftrace -e 'tracepoint:raw_syscalls:sys_enter /pid == $1/ { @[args->id] = count(); }'`,
       and the `syscall:*:*` variant that names them directly. `[BUILD]` `[DIAG]`
1.3.11 **seccomp** as syscall-level policy: `seccomp(SECCOMP_SET_MODE_FILTER, ...)` installs a BPF
       program that returns `SCMP_ACT_ALLOW`, `SCMP_ACT_ERRNO`, `SCMP_ACT_KILL` or
       `SCMP_ACT_TRAP` per syscall. Docker's default profile blocks on the order of **40+**
       syscalls including `perf_event_open`, `bpf`, `mount`, `ptrace` and `io_uring_setup` — which
       is why `jcmd` sometimes fails inside a container while working on the host. `[SYSCALL]`
       `[X-REF 13]` `[RESEARCH]`
1.3.12 `Seccomp` and `NoNewPrivs` are reported in `/proc/<pid>/status`
       (`Seccomp: 2`, `NoNewPrivs: 1`) — the first thing to read when a syscall inexplicably
       returns `EPERM`. `[PROC]`
1.3.13 **Batching is the only real syscall optimisation.** `writev`/`readv` (scatter-gather),
       `sendmmsg`/`recvmmsg`, buffered `BufferedOutputStream`, `epoll_wait` returning many events
       per call, and io_uring submitting many operations per `io_uring_enter`. `BankDeposits`
       ingesting a 40k-record file with one `write` per record makes 40,000 syscalls; batching to
       4 KB blocks makes ~2,000. `[CALC]` `[BUILD]`
1.3.14 `[INCIDENT]` Symptom: `DocumentVerification` shows 45% `%sy` (system CPU) and low `%us`
       while processing uploads. Diagnosis: `perf trace -s -p <pid>` shows millions of 1-byte
       `read` calls. Root cause: a `FileInputStream` read byte-at-a-time through an unbuffered
       `InputStreamReader` over a 6 MB document. Fix: wrap in `BufferedInputStream` — 6,000,000
       syscalls become ~1,464 at an 8 KB buffer, and `%sy` falls to 3%. `[INCIDENT]` `[CALC]`

*(14 leaves)*

## §1.4 The process: address space, `task_struct`, `fork`/`exec`/`wait`, exit status, zombies and orphans

1.4.1 A process is the tuple of: a **private virtual address space** (`mm_struct`), a **file
      descriptor table** (`files_struct`), a **signal disposition table** (`sighand_struct`), a
      **credentials set** (uid/gid/capabilities), a **namespace set** (`nsproxy`), a **cgroup
      membership**, a **cwd/root** (`fs_struct`), and one or more threads. Isolation is the point:
      the `PersonalDetails` process cannot read `FundsLedger`'s heap even on the same host.
      `[TABLE]`
1.4.2 `task_struct` in `include/linux/sched.h` is the kernel's **per-thread** object, not
      per-process: it holds `pid` (the kernel's thread id), `tgid` (the thread-group id that
      userspace calls the PID), `state`, `prio`, `se` (the scheduler entity), `mm`, `files`, and
      the parent/children/sibling list pointers. **`getpid()` returns `tgid`; `gettid()` returns
      `pid`.** `[SOURCE]` `[SYSCALL]`
1.4.3 `[SYSCALL]` `pid_t fork(void)` — implemented via `clone(SIGCHLD, ...)` — duplicates the
      calling process, returning **0 in the child and the child's pid in the parent**. Address
      space is duplicated **copy-on-write**: page tables are copied and every writable page is
      marked read-only in both, so the memory cost of `fork` is page tables plus the pages
      subsequently written, not the whole RSS. `[SYSCALL]` `[PROVE]`
1.4.4 `[CALC]` The COW arithmetic for a `FundsLedger` JVM with **12 GB** of touched heap: at 4 KB
      pages, 12 GB requires ~3.1M PTEs ≈ **24 MB of page tables** per 4-level level pair, so a
      `fork` copies tens of MB rather than 12 GB. This is why `Runtime.exec()` from a large-heap
      JVM is survivable at all — and why it still fails under `vm.overcommit_memory=2`, where the
      kernel accounts the full 12 GB against `CommitLimit`. `[CALC]` `[TRAP]`
1.4.5 `[VERSION-TRAP]` The JVM does **not** use `fork` for `Runtime.exec`/`ProcessBuilder` on
      Linux by default: since JDK 13 the default launch mechanism is **`POSIX_SPAWN`**, tunable via
      `-Djdk.lang.Process.launchMechanism=FORK|POSIX_SPAWN|VFORK`. `posix_spawn` uses a small
      helper (`jspawnhelper`) precisely to avoid duplicating a multi-GB address space. Answers
      about "fork bombs from Java" are pre-13. `[API]` `[VERSION-TRAP]`
1.4.6 `[SYSCALL]` `int execve(const char *pathname, char *const argv[], char *const envp[])`
      **replaces** the current address space, keeping the pid, the fd table (minus `FD_CLOEXEC`
      fds), the cwd and the cgroup. The `fork`+`exec` split is what makes redirection possible:
      the child rearranges its fds between the two calls. `[SYSCALL]` `[FLOW]`
1.4.7 The exit-status encoding, exactly: `wait4` yields a 16-bit value where **normal exit** gives
      `WEXITSTATUS = status >> 8` and **signal death** gives `WTERMSIG = status & 0x7f`. Shells
      report signal death as **128 + signal**, which is why **137 = 128 + 9 (SIGKILL)** and
      **143 = 128 + 15 (SIGTERM)**. Memorise both. `[NUM]` `[CALC]`
1.4.8 `[SYSCALL]` `pid_t wait4(pid_t pid, int *wstatus, int options, struct rusage *rusage)` and
      `waitid`; `WNOHANG` for polling, `WUNTRACED`/`WCONTINUED` for job control. `rusage` carries
      `ru_utime`, `ru_stime`, `ru_maxrss`, `ru_minflt`, `ru_majflt` — a free per-child resource
      report almost nobody reads. `[SYSCALL]` `[API]`
1.4.9 **Zombie** = a task that has exited but whose exit status has not been reaped; it holds only
      a pid slot and its `task_struct`, no memory and no fds, and shows `Z` in `ps`. A handful is
      normal churn. Thousands mean the **parent** is not calling `wait()` — a bug in the parent,
      and unfixable by killing the children (they are already dead). `[PROC]` `[TRAP]`
1.4.10 **Orphan** = a task whose parent died; it is re-parented to the nearest
       `PR_SET_CHILD_SUBREAPER` ancestor or to **PID 1**, which must reap it. This is the entire
       reason a container needs a real init: a shell-form `CMD` shell as PID 1 reaps nothing.
       `[X-REF 19]`
1.4.11 `[PROC]` The per-process `/proc` files worth knowing by heart: `/proc/<pid>/status`
       (`Name`, `State`, `Tgid`, `Pid`, `PPid`, `Threads`, `VmSize`, `VmRSS`, `RssAnon`, `RssFile`,
       `VmSwap`, `voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`), `cmdline` (NUL-separated),
       `environ`, `cwd`, `exe`, `root`, `limits`, `stat`, `smaps_rollup`, `cgroup`, `oom_score`,
       `oom_score_adj`, `sched`, `wchan`, `stack`, `io`. `[PROC]` `[TABLE]`
1.4.12 `pid_max` and pid wraparound: `/proc/sys/kernel/pid_max` (**32768** by default on many
       configurations, commonly raised to 4194304), the reason a pid is **not** a durable
       identifier, and `pidfd_open`/`CLONE_PIDFD` as the race-free alternative for "kill exactly
       this process". `[SYSCTL]` `[SYSCALL]`
1.4.13 Process groups, sessions and the controlling terminal: `setsid`, `setpgid`, why `SIGHUP`
       reaches your job when the SSH session drops, and why `nohup`, `setsid` and `systemd-run
       --scope` are the three ways to survive it. Relevant every time an operator runs a
       `PaymentRun` reconciliation by hand over SSH. `[SYSCALL]`
1.4.14 `[INCIDENT]` Symptom: the `BankWithdrawal` host accumulates 18,000 zombie processes over
       nine days and new process creation starts failing with `EAGAIN`. Diagnosis:
       `ps -eo pid,ppid,stat,cmd | awk '$3 ~ /^Z/'` shows every zombie parented to a single
       long-running JVM; `/proc/<pid>/status` shows `Threads: 214`. Root cause: a payout-file
       checksum step shelled out via `ProcessBuilder` and never called `Process.waitFor()` or
       consumed the exit status, so the JVM never reaped. Fix: `waitFor()` with a timeout in a
       try-with-resources block over the process's three streams; `pid_max` raised as a stopgap
       only. `[INCIDENT]` `[DIAG]`

*(14 leaves)*

## §1.5 Threads: `clone()`, LWPs, what is shared and what is not

1.5.1 On Linux there is no separate "thread" object: **`clone()` creates a task, and the flags
      decide how much of the parent it shares.** A "process" is a thread group whose members share
      an `mm_struct`; the kernel schedules `task_struct`s and is indifferent to the userspace
      vocabulary. `[PROVE]` `[SOURCE]`
1.5.2 `[SYSCALL]` The glibc wrapper signature, verbatim from `man 2 clone`:
      `int clone(int (*fn)(void *), void *stack, int flags, void *arg, ... /* pid_t *parent_tid,
      void *tls, pid_t *child_tid */)`, and the modern form
      `long syscall(SYS_clone3, struct clone_args *cl_args, size_t size)` whose struct fields are
      `flags, pidfd, child_tid, parent_tid, exit_signal, stack, stack_size, tls, set_tid,
      set_tid_size, cgroup`. `[SYSCALL]` `[SOURCE]` `[RESEARCH]`
1.5.3 `[TABLE]` The sharing flags and what each shares: `CLONE_VM` (address space), `CLONE_FS`
      (root, cwd, umask), `CLONE_FILES` (fd table), `CLONE_SIGHAND` (signal handler table),
      `CLONE_THREAD` (same thread group, so same `tgid`), `CLONE_SYSVSEM` (SysV semaphore
      adjustments), `CLONE_SETTLS`, `CLONE_PARENT_SETTID`, `CLONE_CHILD_CLEARTID` (clear the TID
      and `FUTEX_WAKE` on exit — the mechanism behind `pthread_join`), `CLONE_IO` (shared block
      I/O context), `CLONE_VFORK`, `CLONE_PIDFD`. `[TABLE]` `[RESEARCH]`
1.5.4 `[TABLE]` The **unsharing** flags — the ones that build containers rather than threads:
      `CLONE_NEWNS` (mount), `CLONE_NEWPID`, `CLONE_NEWNET`, `CLONE_NEWUTS`, `CLONE_NEWIPC`,
      `CLONE_NEWUSER`, `CLONE_NEWCGROUP`, `CLONE_NEWTIME`. A container is `clone()` with these
      set plus a cgroup plus a seccomp filter — nothing more exotic than that. `[X-REF 19]`
1.5.5 `pthread_create` is `clone` with, in essence,
      `CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|CLONE_SETTLS|
      CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID`. `fork` is `clone(SIGCHLD)` with none of them.
      Stating this once makes the whole process/thread distinction fall out mechanically.
      `[PROVE]` `[RESEARCH]`
1.5.6 `[TABLE]` What is **shared** by threads in a group: address space (heap, globals, code,
      `mmap` regions), fd table, signal dispositions, cwd, uid/gid, cgroup, namespaces, resource
      limits, and the `/proc/<tgid>` view. What is **private**: the stack, register state
      (including the instruction pointer), `errno` (thread-local), the signal *mask*, the pending
      signal set, the TLS block, `gettid()`, scheduler state (`vruntime`, `lag`, priority,
      affinity) and per-thread CPU accounting. `[TABLE]`
1.5.7 Thread stacks are `mmap`'d anonymous regions with a `PROT_NONE` **guard page**, sized by
      `pthread_attr_setstacksize` or `RLIMIT_STACK` (glibc default 8 MB when unlimited-adjacent).
      **The JVM does not use the default**: `ThreadStackSize` on linux-x86_64 is **1 MB**
      (`-Xss1m`), reserved virtually and populated on demand. `[NUM]` `[API]`
1.5.8 `[CALC]` The platform-thread cost arithmetic that motivates virtual threads: 1 MB reserved
      stack + ~8–16 KB kernel `task_struct`/kernel stack per thread. `ApplicationGateway` handling
      **55k concurrent sessions** thread-per-request needs 55 GB of virtual reservation and, at a
      realistic 40–90 KB of touched stack per thread, **2.2–5 GB of RSS** — against a **2 GB**
      heap allocation. The thread model, not the heap, is the binding constraint. `[CALC]` `[NUM]`
1.5.9 `[API]` Virtual threads as an OS statement: **`m:n` scheduling in userspace** over a
      `ForkJoinPool` of carrier platform threads sized to `Runtime.availableProcessors()`. The
      kernel sees only the carriers; `top -H` shows `ForkJoinPool-1-worker-N`, not your million
      virtual threads. Tunables: `jdk.virtualThreadScheduler.parallelism`,
      `jdk.virtualThreadScheduler.maxPoolSize`. `[API]` `[X-REF 04]`
1.5.10 `[VERSION-TRAP]` **Pinning.** On **Java 21**, a virtual thread that blocks inside a
       `synchronized` block or in a native call pins its carrier; enough pinned carriers deadlock
       the scheduler. **JEP 491 (JDK 24)** removed `synchronized` pinning and removed the
       `jdk.tracePinnedThreads` diagnostic property. Native-call pinning remains in both. State
       the version or the answer is wrong half the time. `[VERSION-TRAP]` `[API]`
1.5.11 `[PROC]` Finding threads: `/proc/<tgid>/task/` lists one directory per thread, each with its
       own `stat`, `status`, `wchan`, `comm` and `schedstat`. `ps -eLf`, `ps -L -p <pid>`,
       `top -H -p <pid>`, and `/proc/<tgid>/task/<tid>/comm` (the 15-character name — which is why
       `Thread.setName` beyond 15 chars is truncated in `top`). `[PROC]` `[DIAG]`
1.5.12 `[DIAG]` The canonical "which Java thread is burning a core" recipe, as an exact sequence:
       `top -H -p <pid>` → note the hot TID → `printf '%x\n' <tid>` → match `nid=0x<hex>` in
       `jstack <pid>` output. Works identically with `jcmd <pid> Thread.print`. `[FLOW]` `[DIAG]`
1.5.13 `threads-max` and `RLIMIT_NPROC`: `/proc/sys/kernel/threads-max` is derived at boot from
       RAM (roughly 1/8 of pages), `ulimit -u` bounds threads *per uid* (not per process), and
       cgroup v2's `pids.max` (default `"max"`) bounds them per cgroup. A `java.lang.OutOfMemoryError:
       unable to create native thread` is one of these three, never a heap problem. `[SYSCTL]`
       `[TRAP]`
1.5.14 `[INCIDENT]` Symptom: `InternalPlatforms` throws
       `OutOfMemoryError: unable to create native thread` at 90 operators on shift, with a 4 GB
       heap only 40% used. Diagnosis: `/proc/<pid>/status` shows `Threads: 1021`;
       `cat /sys/fs/cgroup/pids.max` shows `1024`. Root cause: an unbounded thread pool per
       operator session (30–90 minute lifetimes) against a `pids.max` set by the pod spec. Fix: a
       bounded pool sized from concurrent sessions, plus `pids.max` raised with headroom — in that
       order, because raising the limit alone only defers it. `[INCIDENT]` `[PROC]`

*(14 leaves)*

## §1.6 Process states and what "runnable", "sleeping" and "D state" mean

1.6.1 `[TABLE]` The kernel task states and their `ps` codes: `R` = `TASK_RUNNING` (**running *or*
      on the run queue** — the single most misread state), `S` = `TASK_INTERRUPTIBLE`,
      `D` = `TASK_UNINTERRUPTIBLE`, `T` = `TASK_STOPPED`, `t` = tracing stop, `Z` = `EXIT_ZOMBIE`,
      `X` = `EXIT_DEAD`, `I` = `TASK_IDLE` (idle kernel threads, excluded from load average).
      `[TABLE]` `[PROC]`
1.6.2 `R` does **not** mean "on a CPU". `ps` cannot distinguish running from runnable. The count of
      truly running tasks is bounded by `nproc`; the count of `R` tasks is the run-queue depth.
      `[TRAP]` `[PROVE]`
1.6.3 `S` vs `D`, precisely: an interruptible sleeper can be woken by a signal, so `kill` works; an
      **uninterruptible** sleeper is inside a kernel path that cannot safely unwind — typically
      block I/O submission, a page fault against disk, an NFS RPC, or a filesystem lock — and
      **`SIGKILL` does nothing to it**. `[PROVE]` `[TRAP]`
1.6.4 `TASK_KILLABLE` (`D` with a killable flag, added for NFS) is the middle ground and is why
      *some* `D`-state tasks do respond to `SIGKILL`. Do not promise a candidate answer that all
      `D` states are unkillable — promise that you cannot rely on killing them. `[TRAP]`
1.6.5 `[PROC]` `/proc/<pid>/wchan` names the kernel function the task is sleeping in
      (`ep_poll`, `futex_wait_queue`, `io_schedule`, `folio_wait_bit_common`,
      `rpc_wait_bit_killable`), and `/proc/<pid>/stack` gives the full kernel stack when
      `CONFIG_STACKTRACE` allows. `ps -eo pid,stat,wchan:30,cmd` turns "it's stuck" into "it's in
      `io_schedule`". `[PROC]` `[DIAG]`
1.6.6 `[CALC]` **Load average is `R` + `D`, exponentially damped over 1/5/15 minutes, with no
      denominator.** Load 8.42 on 16 cores is half-utilised; load 8.42 on 2 vCPU is 4×
      oversubscribed; load 8.42 with all CPUs idle is an I/O stall, because `D` counts. Always
      divide by `nproc` and always state the trend: `8.42, 7.90, 6.11` is *rising*. `[CALC]`
      `[NUM]`
1.6.7 `[VERSION-TRAP]` PSI is the correct modern signal and load average is legacy.
      `/proc/pressure/cpu` `some avg10=` is the fraction of time **at least one** task was stalled
      waiting for CPU; `full` is when **all** non-idle tasks were stalled (undefined at system
      level for CPU and reported as zero since 5.13). `total=` is cumulative stall in
      **microseconds**. `[PROC]` `[RESEARCH]`
1.6.8 `[PROC]` `/proc/pressure/io` and `/proc/pressure/memory` are how you distinguish "slow
      because of disk" from "slow because of reclaim" without guessing. A memory `full avg10`
      above a few percent means tasks are being stalled in reclaim — the pre-OOM signal, and what
      `systemd-oomd` acts on. `[PROC]` `[DIAG]`
1.6.9 `[TABLE]` Java thread states are **not** kernel states and the mapping is lossy:
      `RUNNABLE` covers both "computing" and "blocked in a syscall" (because the JVM cannot tell),
      `BLOCKED` means waiting on a monitor, `WAITING`/`TIMED_WAITING` means `Object.wait`,
      `LockSupport.park` or `sleep`. A thread blocked in a socket read is `RUNNABLE` in the dump
      and `S` in the kernel. `[TABLE]` `[TRAP]`
1.6.10 `[TRAP]` **Trap:** "the thread dump shows 200 `RUNNABLE`, so we are CPU-bound." Correlate
       with `%us` from `top` and with `/proc/<pid>/task/*/stat` state characters before concluding
       anything. 200 `RUNNABLE` threads on a 4-vCPU `ClientRestrictions` pod with 6% `%us` are all
       sitting in `recvfrom`. `[TRAP]` `[DIAG]`
1.6.11 `[PROC]` Per-thread scheduling delay, exactly: `/proc/<pid>/schedstat` gives three numbers —
       time on CPU (ns), **time waiting on the run queue (ns)**, and timeslices run.
       `/proc/<pid>/sched` gives `se.sum_exec_runtime`, `se.statistics.wait_sum` and
       `nr_switches`. The second number is the one that explains a 30 ms budget breach at 38% CPU.
       `[PROC]` `[CALC]`
1.6.12 `[INCIDENT]` Symptom: `BankDeposits` hangs at 06:05 during statement-file ingestion; the pod
       will not terminate, `kill -9` has no effect, and the node's load average reads 42 with 4%
       CPU. Diagnosis: `ps -eo pid,stat,wchan:30,cmd | grep '^ *[0-9]* D'` shows the ingestion
       threads in `io_schedule`; `/proc/pressure/io` reads `full avg10=88.31`. Root cause: the EBS
       gp3 volume had exhausted its provisioned IOPS while writing 40k records with an `fsync` per
       record. Fix: batch the commit so one `fsync` covers 1,000 records, and provision IOPS for
       the month-end 500k-record file, not the median day. `[INCIDENT]` `[PROC]` `[X-REF 18]`

*(12 leaves)*

## §1.7 CPU scheduling: CFS, `vruntime`, nice, and EEVDF

1.7.1 What the scheduler is choosing between: the per-CPU **run queue** (`struct rq`) holding
      `TASK_RUNNING` tasks, organised as a **red-black tree keyed on virtual time** for the fair
      class. `pick_next_task` runs on every timer tick, every wakeup, every block, and every
      explicit `yield`. `[SOURCE]`
1.7.2 **CFS's rule, stated exactly (kernels < 6.6):** each task accumulates
      `vruntime += delta_exec × (NICE_0_LOAD / weight)`, where `NICE_0_LOAD = 1024`; the scheduler
      always runs the task with the **smallest `vruntime`**. Fairness is therefore not a heuristic
      but an invariant — every runnable task converges on equal virtual time. `[PROVE]` `[NUM]`
1.7.3 `[CALC]` The **nice weight table**: nice 0 → weight **1024**, and each nice level multiplies
      the weight by roughly **1.25** (so nice −1 ≈ 1277, nice 1 ≈ 820, nice 19 ≈ **15**, nice −20 ≈
      **88761**). Two tasks at nice 0 and nice 5 (weight 335) get CPU in the ratio
      1024 : 335 ≈ **75% : 25%**. One nice level ≈ a **10%** CPU shift. `[CALC]` `[NUM]`
1.7.4 `[VERSION-TRAP]` **CFS's old latency tunables no longer exist.** Pre-6.6:
      `sched_latency_ns` (**6,000,000 ns**), `sched_min_granularity_ns` (**750,000 ns**),
      `sched_wakeup_granularity_ns` (**1,000,000 ns**), with the target latency stretched once
      `nr_running > sched_latency / sched_min_granularity` (8 tasks). From **6.6** these are gone,
      replaced by `/sys/kernel/debug/sched/base_slice_ns` (**750,000 ns**). Reproducing the old
      `sched_latency_ns / nr_running` formula in an interview is a pre-2023 answer.
      `[VERSION-TRAP]` `[RESEARCH]` `[SYSCTL]`
1.7.5 `[PROVE]` **EEVDF, from first principles.** Each task has a **`lag`** — the difference
      between the service it was *owed* by the fair-share ideal and the service it actually
      received. A task is **eligible** only when `lag >= 0` (it is not in credit-spent debt). Each
      task requests a **slice** (default `base_slice_ns`, per-task settable), and its **virtual
      deadline** is its eligible time plus the slice scaled by weight. The scheduler picks the
      **eligible task with the earliest virtual deadline**. `[PROVE]` `[RESEARCH]`
1.7.6 Why EEVDF replaced CFS: `vruntime`-minimum picking gives no way to express "I want a short
      slice soon" versus "I want a long slice eventually". EEVDF's slice request does, which is
      what makes latency-nice / `sched_attr.sched_runtime` meaningful and what lets a short-slice
      `ClientRestrictions` request preempt a long-slice batch task without abusing nice. `[PROVE]`
      `[RESEARCH]`
1.7.7 `[API]` `sched_setattr(pid_t pid, struct sched_attr *attr, unsigned int flags)` with
      `sched_util_min`/`sched_util_max` (uclamp) and the latency-nice field, versus the legacy
      `nice(int inc)` / `setpriority(PRIO_PROCESS, pid, nice)`. Java exposes **none** of this:
      `Thread.setPriority(1..10)` is a no-op on Linux HotSpot unless `-XX:+UseThreadPriorities`
      *and* `-XX:ThreadPriorityPolicy=1` are set **and** the JVM runs as root. `[API]` `[TRAP]`
1.7.8 `[SYSCTL]` **CFS bandwidth control** is the mechanism behind a Kubernetes CPU *limit*:
      cgroup v2 `cpu.max` is `"$MAX $PERIOD"`, default **`"max 100000"`** (unlimited, 100 ms
      period). `cpu.max.burst` allows accumulated unused quota to be spent. `cpu.weight`
      (default **100**, range 1–10000) is the *relative* share and is what a Kubernetes CPU
      *request* becomes. `[SYSCTL]` `[RESEARCH]`
1.7.9 `[CALC]` **Throttling arithmetic.** `cpu.max = "20000 100000"` means 20 ms of CPU per 100 ms
      window. A `ClientRestrictions` request that needs 8 ms of CPU across 4 threads consumes 32 ms
      of quota, exhausts the window after 20 ms, and is **frozen until the next period** — adding
      up to **80 ms** of pure throttle stall to a **30 ms** budget. The pathology is not average
      utilisation (which reads 20%) but the burst shape. `[CALC]` `[NUM]` `[PROVE]`
1.7.10 `[PROC]` The throttling evidence: `/sys/fs/cgroup/<path>/cpu.stat` reports
       `usage_usec`, `user_usec`, `system_usec`, `nr_periods`, **`nr_throttled`**, and
       **`throttled_usec`**. A non-zero and rising `nr_throttled` with `usage_usec` far below quota
       is the burst signature. This is the single most valuable container-latency counter and
       almost nobody scrapes it. `[PROC]` `[DIAG]` `[RESEARCH]`
1.7.11 `[TRAP]` **Trap:** "we set the CPU limit equal to the request, so it can't be throttled."
       Wrong — a multi-threaded JVM consumes quota in parallel, so a 2-CPU limit with 40 GC threads
       burns the 200 ms window in 5 ms of wall time. `-XX:ActiveProcessorCount` and sizing
       `ParallelGCThreads` to the quota are the fix, not raising the limit. `[TRAP]` `[X-REF 06]`
1.7.12 `[PROC]` Reading the scheduler's own view: `/proc/schedstat`,
       `/sys/kernel/debug/sched/debug` (per-CPU run queues, per-task `vruntime`, `lag` and
       deadline), `/proc/<pid>/sched`, and the `runqlat` / `runqlen` bcc tools that histogram
       run-queue latency in microseconds. `[PROC]` `[DIAG]`
1.7.13 Load balancing across CPUs: `sched_domains` built from the CPU topology
       (SMT → core → LLC → NUMA node), periodic balancing at the domain's `balance_interval`, plus
       idle balancing and `wake_affine` (wake a task on the waker's CPU to preserve cache
       locality). This is why pinning `FundsLedger`'s hot threads can help and why it can also
       destroy throughput. `[PROVE]`
1.7.14 `[INCIDENT]` Symptom: `ClientRestrictions` p99 is 480 ms in Kubernetes and 9 ms on a bare
       EC2 instance running identical code and identical traffic. Diagnosis: `cpu.stat` shows
       `nr_throttled: 3,847` against `nr_periods: 4,102` — 94% of periods throttled;
       `throttled_usec` sums to 61% of wall time. Root cause: a `cpu` limit of `250m` on a JVM
       that had sized `ParallelGCThreads` and the common `ForkJoinPool` from the host's 64 cores.
       Fix: `-XX:ActiveProcessorCount=1` plus removing the CPU *limit* while keeping the *request*
       — quota is a latency hazard, weight is not. `[INCIDENT]` `[PROC]` `[CALC]`

*(14 leaves)*

## §1.8 Scheduling classes, real-time policies, priorities and CPU affinity

1.8.1 `[TABLE]` The scheduling classes in strict priority order:
      **`stop_sched_class`** (kernel-internal, CPU hotplug), **`dl_sched_class`**
      (`SCHED_DEADLINE`), **`rt_sched_class`** (`SCHED_FIFO`, `SCHED_RR`),
      **`fair_sched_class`** (`SCHED_OTHER`/`SCHED_BATCH`/`SCHED_IDLE` — EEVDF),
      **`idle_sched_class`**. A runnable RT task **always** preempts every fair task on that CPU,
      unconditionally. `[TABLE]` `[PROVE]`
1.8.2 `[SYSCALL]` `int sched_setscheduler(pid_t pid, int policy, const struct sched_param *param)`
      and `sched_getscheduler`; `SCHED_FIFO`/`SCHED_RR` take a static priority **1–99** (higher
      wins), while `SCHED_OTHER` requires priority **0** and uses nice instead. `chrt -f -p 50
      <pid>`, `chrt -p <pid>` to read. `[SYSCALL]` `[NUM]`
1.8.3 `SCHED_FIFO` runs until it blocks or yields — **no timeslice at all**. `SCHED_RR` is
      identical plus a quantum (`/proc/sys/kernel/sched_rr_timeslice_ms`, **100 ms** by default).
      An infinite loop under `SCHED_FIFO` at priority 99 on a single-CPU box wedges the machine
      completely. `[SYSCTL]` `[TRAP]`
1.8.4 `[SYSCTL]` The safety valve: `kernel.sched_rt_runtime_us` (**950000**) out of
      `kernel.sched_rt_period_us` (**1000000**) caps the RT classes at **95%** of each CPU-second,
      leaving 5% for fair tasks. Setting `sched_rt_runtime_us = -1` removes the cap and removes
      your ability to log in. `[SYSCTL]` `[NUM]`
1.8.5 `SCHED_DEADLINE` (EDF + CBS) takes `sched_runtime`, `sched_deadline` and `sched_period` via
      `sched_setattr`, and the kernel performs **admission control** — it refuses a task whose
      utilisation would oversubscribe the deadline bandwidth. It is the only Linux policy with a
      real guarantee, and it is essentially never what a JVM service wants. `[API]` `[NUM]`
1.8.6 `SCHED_BATCH` (no wakeup preemption, longer effective slices — right for `BankDeposits`
      ingestion) and `SCHED_IDLE` (runs only when nothing else is runnable — right for a
      reconciliation sweep). Both are one `chrt` invocation and both are chronically underused.
      `[API]`
1.8.7 `[VERSION-TRAP]` **Preemption models.** `CONFIG_PREEMPT_NONE` (throughput/server),
      `PREEMPT_VOLUNTARY`, `PREEMPT` (low-latency desktop), and **`PREEMPT_RT`, mainlined in
      6.12**, which converts most spinlocks to sleeping locks and makes almost all kernel code
      preemptible. 6.12 also carries the `PREEMPT_LAZY` work. Read the running model at
      `/sys/kernel/debug/sched/preempt` where exposed, or `uname -v` for the `PREEMPT` tag.
      `[VERSION-TRAP]` `[RESEARCH]`
1.8.8 `[SYSCALL]` CPU affinity: `int sched_setaffinity(pid_t pid, size_t cpusetsize,
      const cpu_set_t *mask)` / `sched_getaffinity`; `taskset -pc 0-3 <pid>`,
      `taskset -c 0-3 java -jar ...`. Affinity is **per thread**, inherited across `clone` and
      `fork`, and preserved across `execve`. `[SYSCALL]` `[API]`
1.8.9 `[TRAP]` **Trap:** `Runtime.availableProcessors()` respects `sched_getaffinity`, so
      `taskset`-ing a JVM changes its GC thread count and common-pool size — but only if the mask
      is set **before** the JVM starts. Applying `taskset` to a running JVM narrows the CPUs
      without resizing any pool, giving you 40 GC threads on 2 CPUs. `[TRAP]` `[API]`
1.8.10 cgroup v2 `cpuset.cpus` and `cpuset.mems` as the declarative form of affinity, and
       `cpuset.cpus.partition` (`member`/`root`/`isolated`) for carving out CPUs. Kubernetes'
       `static` CPU Manager policy writes exactly these files for `Guaranteed` pods with integer
       CPU requests. `[SYSCTL]` `[X-REF 19]`
1.8.11 `[CALC]` **NUMA.** `numactl --hardware` and `lscpu` give node count and per-node memory;
       remote-node memory access typically costs **1.3–2.0×** local latency. `numactl
       --cpunodebind=0 --membind=0` pins both. A 12 GB `FundsLedger` heap spread across two nodes
       does roughly half its GC traversal at remote latency; `-XX:+UseNUMA` makes the JVM allocate
       per-node eden regions instead. `[CALC]` `[API]` `[X-REF 06]`
1.8.12 `vm.zone_reclaim_mode` (**0**, disabled) and `kernel.numa_balancing`
       (`/proc/sys/kernel/numa_balancing`) as the two NUMA knobs that have historically caused
       latency incidents on database hosts — automatic NUMA balancing migrates pages under load
       and stalls the faulting thread. `[SYSCTL]` `[RESEARCH]`
1.8.13 IRQ affinity and `RPS`/`RFS`: `/proc/interrupts`, `/proc/irq/<n>/smp_affinity`,
       `irqbalance`, and why a single NIC queue pinned to CPU 0 shows as 100% `%si` on one core
       while 15 cores idle. Owned in detail by `10-networking.md`; the mechanism is stated here.
       `[PROC]` `[X-REF 10]`
1.8.14 `[INCIDENT]` Symptom: a `FundsLedger` instance shows 40 ms GC pauses on an otherwise
       identical peer that shows 9 ms, both at 12 GB. Diagnosis: `numastat -p <pid>` shows 62% of
       its pages on the remote node; the peer shows 4%. Root cause: the instance started while
       node 0 was under memory pressure, so the JVM's initial heap reservation spilled across
       nodes, and `AlwaysPreTouch` was off so the placement was decided lazily under load. Fix:
       `numactl --membind` at launch plus `-XX:+AlwaysPreTouch` so placement happens once, at
       start, under known conditions. `[INCIDENT]` `[CALC]`

*(14 leaves)*

## §1.9 Context switches: mechanics, kinds, and the real cost

1.9.1 `[FLOW]` What a switch does, in order: save the outgoing task's general-purpose registers and
      stack pointer, save FPU/SSE/AVX state (lazily, via `XSAVE`), update the outgoing task's
      accounting (`vruntime`/`lag`, `sum_exec_runtime`), pick the next task, load its page-table
      root into `CR3` **if the `mm_struct` differs**, restore its registers, and return to
      userspace. `[FLOW]` `[SOURCE]`
1.9.2 **Thread switch vs process switch:** a switch between two threads of the same `mm` skips the
      `CR3` load entirely, so the TLB survives. A switch between processes changes `CR3` and, on
      hardware without PCID, flushes the whole TLB. **PCID/ASID** tags TLB entries with an address
      space id so the flush is avoided — check `pcid` and `invpcid_single` in `/proc/cpuinfo`
      flags. `[PROVE]` `[PROC]`
1.9.3 `[TABLE]` **Voluntary** switches (the task blocked: I/O, `futex`, `epoll_wait`, `sleep`)
      versus **involuntary** switches (the task was preempted: slice exhausted, a higher-priority
      task woke, quota throttled). The distinction is the diagnosis: voluntary means you are
      waiting on something, involuntary means you are competing for CPU. `[TABLE]`
1.9.4 `[PROC]` The exact counters: `/proc/<pid>/status` reports
      `voluntary_ctxt_switches:` and `nonvoluntary_ctxt_switches:` per task, and
      `/proc/<tgid>/task/<tid>/status` gives them per thread. System-wide, `vmstat 1`'s **`cs`**
      column is switches/sec and **`in`** is interrupts/sec. `[PROC]` `[DIAG]`
1.9.5 `[NUM]` **Direct cost: ~1–5 µs**, dominated by the register save/restore and the scheduler
      pick. Measurable with `perf bench sched pipe`, which reports µs/op for a
      ping-pong pair. `[NUM]` `[BUILD]`
1.9.6 `[PROVE]` **Indirect cost is larger and is what actually hurts.** The incoming task's working
      set is not in L1/L2, so it runs at memory latency until the caches refill — commonly
      **10–100 µs** of degraded execution for a task with a meaningful working set. This is
      "cache pollution", it does not appear in any switch counter, and it is why the switch *rate*
      matters more than the switch cost. `[PROVE]` `[NUM]`
1.9.7 `[CALC]` The arithmetic that kills the "more threads = more throughput" belief: on 8 vCPU
      with 800 runnable threads at a 750 µs `base_slice_ns`, each thread runs once per
      **75 ms** (800 / 8 × 750 µs), so a request needing three scheduling turns takes **225 ms**
      of pure queueing — against a **150 ms** stake-reservation budget. Past `nproc` for CPU-bound
      work, threads buy latency variance, not throughput. `[CALC]` `[PROVE]`
1.9.8 Why the same arithmetic **reverses** for I/O-bound work: a thread blocked in `recvfrom`
      occupies no CPU, so 800 threads waiting on the card PSP's **p99 of 11 s** is a
      *concurrency* win — and precisely the case where virtual threads deliver it without 800
      `task_struct`s and 800 MB of stack reservation. `[PROVE]` `[X-REF 04]`
1.9.9 `[DIAG]` Reading `vmstat 1` as a switch diagnosis: high `cs` with high `sy` = thread
      thrashing or lock convoying; high `cs` with high `wa` = many small blocking I/Os; high `in`
      with high `si` in `top` = network interrupt load. A `ClientRestrictions` pod on 2 vCPU
      showing **180,000 `cs`/sec** is spending measurable CPU switching rather than deciding.
      `[DIAG]` `[NUM]`
1.9.10 **Lock convoying** as the specific pathology: N threads contend on one monitor, each wakes,
       fails, and re-sleeps via `futex`, producing two switches per failed acquisition. The
       signature is `nonvoluntary_ctxt_switches` roughly flat while `voluntary_ctxt_switches`
       explodes, plus `futex` dominating `strace -c`. `[X-REF 05]`
1.9.11 `[BUILD]` Measuring off-CPU time properly: `offcputime -p <pid>` (bcc) histograms *why*
       threads left the CPU with kernel stacks attached, and `runqlat -p <pid>` histograms
       run-queue wait in µs. Together they separate "waiting for work" from "waiting for a CPU" —
       the two indistinguishable causes of a missed 30 ms budget. `[BUILD]` `[DIAG]`
1.9.12 **Steal time** as the switch you did not make: `%st` in `top` is time your vCPU was runnable
       but the hypervisor ran someone else. On a shared EC2 instance family sustained `%st` above
       a few percent means a noisy neighbour and the fix is a different instance type, not a code
       change. `[NUM]` `[X-REF 18]`
1.9.13 `[INCIDENT]` Symptom: `ClientRestrictions` throughput *falls* after scaling its thread pool
       from 32 to 512 to "handle the burst". Diagnosis: `vmstat 1` shows `cs` rising from 22k to
       310k/sec while `%sy` goes from 5% to 34% and p99 goes from 11 ms to 190 ms;
       `nonvoluntary_ctxt_switches` on the worker threads rises 14×. Root cause: the work was
       CPU-bound (in-memory restriction evaluation), so 512 threads on 4 vCPU produced pure
       switching overhead. Fix: pool size back to `nproc + 1`, with a bounded queue and load
       shedding at the queue limit rather than unbounded thread growth. `[INCIDENT]` `[CALC]`

*(13 leaves)*

## §1.10 Virtual memory: address translation, page tables, the MMU and the TLB

1.10.1 The contract: every process sees a private, contiguous virtual address space; the **MMU**
       translates virtual page numbers to physical frame numbers using per-process page tables
       rooted in **`CR3`**. Nothing a process does with a pointer can name another process's
       physical memory. `[PROVE]`
1.10.2 `[CALC]` **Page size 4 KiB** on x86-64: the low **12 bits** of an address are the offset
       (2^12 = 4096), leaving 36 bits of virtual page number under 48-bit addressing. Huge pages
       are **2 MiB** (one PMD entry) and **1 GiB** (one PUD entry). Confirm with `getconf
       PAGE_SIZE`. `[CALC]` `[NUM]`
1.10.3 `[CALC]` **The 4-level walk, level by level:** bits 47–39 index the **PGD**, 38–30 the
       **PUD**, 29–21 the **PMD**, 20–12 the **PTE**, and 11–0 are the offset — **9 bits per
       level, 512 entries × 8 bytes = exactly one 4 KiB page per table**. Five-level paging adds
       the **P4D** at bits 56–48, extending user space from 128 TiB to 64 PiB. `[CALC]` `[PROVE]`
1.10.4 `[CALC]` **Why the TLB exists:** a 4-level walk is up to **four** memory accesses per
       translation, so an uncached translation makes every load five loads. A 5-level walk makes
       it six. `[CALC]` `[PROVE]`
1.10.5 `[NUM]` TLB structure on a modern x86-64 core: a small L1 dTLB (**~64** 4 KiB entries), a
       shared L2 STLB (**~1,500–3,000** entries), plus separate huge-page entries. Read yours from
       `cpuid` output or `/sys/devices/system/cpu/cpu0/cache/`. `[NUM]`
1.10.6 `[CALC]` **The huge-page argument, arithmetically.** A 2,048-entry STLB covers
       2,048 × 4 KiB = **8 MiB** with 4 KiB pages, and 2,048 × 2 MiB = **4 GiB** with 2 MiB pages.
       A `FundsLedger` heap of **12 GB** therefore cannot be TLB-resident at 4 KiB granularity at
       all, and a GC traversal of it is a TLB-miss generator. This is the entire case for THP on
       large-heap JVMs. `[CALC]` `[PROVE]` `[NUM]`
1.10.7 `[SYSCTL]` **THP surfaces:** `/sys/kernel/mm/transparent_hugepage/enabled`
       (`always` | `madvise` | `never`), `.../defrag`, `.../hpage_pmd_size` (**2097152**), and
       `khugepaged` as the background collapser with
       `/sys/kernel/mm/transparent_hugepage/khugepaged/*`. Per-process evidence:
       `AnonHugePages:` in `/proc/<pid>/smaps_rollup` and `/proc/meminfo`. `[SYSCTL]` `[PROC]`
       `[RESEARCH]`
1.10.8 `[VERSION-TRAP]` **The THP default is distro-dependent**, not kernel-uniform: RHEL-family
       images (and therefore many container base images' host expectations) ship `always`;
       Debian/Ubuntu ship `madvise`. Under `always`, `khugepaged` can stall an allocating thread
       for milliseconds compacting memory to form a 2 MiB page — the classic
       "unexplained p99 spike on a database host". `madvise` plus
       `-XX:+UseTransparentHugePages` gives the JVM the win without the tax. `[VERSION-TRAP]`
       `[TRAP]` `[RESEARCH]`
1.10.9 `[API]` **Explicit hugetlb** as the alternative: `vm.nr_hugepages`,
       `/proc/meminfo`'s `HugePages_Total`/`HugePages_Free`/`Hugepagesize`, `mmap(MAP_HUGETLB)`,
       and `-XX:+UseLargePages`. Pre-reserved, never swapped, never compacted — and it fails at
       JVM start rather than degrading, which is the property you want for `FundsLedger`.
       `[API]` `[PROC]`
1.10.10 `[PROC]` **Reading a process's own translation state:** `/proc/<pid>/maps` (one line per
        VMA: address range, permissions, offset, device, inode, pathname),
        `/proc/<pid>/smaps` (per-VMA `Rss`, `Pss`, `Private_Dirty`, `Swap`, `AnonHugePages`,
        `THPeligible`), `/proc/<pid>/smaps_rollup` (the same, summed — far cheaper to read), and
        `/proc/<pid>/pagemap` for per-page physical mapping. `[PROC]` `[DIAG]`
1.10.11 `[CALC]` **Page-table memory is not free.** Each 4 KiB page needs an 8-byte PTE, so a fully
        touched 12 GB heap needs 12 GiB / 4 KiB × 8 B = **24 MiB** of PTEs plus the higher levels —
        reported as `PageTables:` in `/proc/meminfo` and `VmPTE:` in `/proc/<pid>/status`. With
        2 MiB pages it is **48 KiB**. `[CALC]` `[PROC]`
1.10.12 **Address-space randomisation:** `/proc/sys/kernel/randomize_va_space`
        (**2** = full, randomising stack, mmap base, brk and PIE text) and `setarch -R` to disable
        it for reproducible debugging. Why a heap address differs across restarts and why a core
        dump's addresses mean nothing without the maps. `[SYSCTL]`
1.10.13 `[DIAG]` Measuring translation cost directly:
        `perf stat -e dTLB-load-misses,dTLB-store-misses,iTLB-load-misses,page-faults -p <pid>`,
        and what a high `dTLB-load-misses`-to-instructions ratio looks like before and after
        enabling THP on a 12 GB heap. `[DIAG]` `[BUILD]`
1.10.14 `[INCIDENT]` Symptom: `FundsLedger` young-GC pause time grows from 6 ms to 28 ms as the
        reservation index grows past ~4 GB of live data, with no rise in allocation rate.
        Diagnosis: `perf stat` shows `dTLB-load-misses` up 9×; `smaps_rollup` shows
        `AnonHugePages: 0 kB`. Root cause: the host had
        `transparent_hugepage/enabled = madvise` and the JVM ran without
        `-XX:+UseTransparentHugePages`, so a 12 GB heap was mapped entirely in 4 KiB pages and the
        GC's whole-heap pointer chase missed the STLB on nearly every access. Fix:
        `-XX:+UseTransparentHugePages` with `-XX:+AlwaysPreTouch`, pause back to 8 ms.
        `[INCIDENT]` `[CALC]` `[DIAG]`

*(14 leaves)*

## §1.11 The process memory map: text, data, bss, heap, stacks, `mmap` regions

1.11.1 `[TABLE]` The regions of a Linux process image, low to high: **text** (`r-xp`, the
       executable, file-backed and shared between instances), **rodata** (`r--p`), **data**
       (`rw-p`, initialised globals, file-backed), **bss** (`rw-p`, zero-initialised globals, no
       file backing), **heap** (`[heap]`, grown by `brk`), the **mmap region** (shared libraries,
       anonymous mappings, thread stacks), the **main stack** (`[stack]`, grown downward), and
       `[vvar]`/`[vdso]`/`[vsyscall]` at the top. `[TABLE]` `[PROC]`
1.11.2 `[PROC]` **A `/proc/<pid>/maps` line, field by field:**
       `7f3c1a400000-7f3c5a400000 rw-p 00000000 00:00 0` — start-end virtual addresses,
       permissions (`r`/`w`/`x` plus `p` private or `s` shared), file offset, device major:minor,
       inode, and pathname (empty for anonymous, `[heap]`/`[stack]` for the specials). Learn to
       read the address delta as the region size. `[PROC]` `[DIAG]`
1.11.3 A **VMA** (`struct vm_area_struct`) is the kernel's unit of bookkeeping: one contiguous
       range with uniform permissions and backing. `vm.max_map_count` (**65530**) caps the number
       of VMAs per process, and exceeding it gives `mmap: Cannot allocate memory` with plenty of
       RAM free — the failure mode of glibc-arena-heavy or ZGC-heavy processes. `[SYSCTL]`
       `[NUM]` `[RESEARCH]`
1.11.4 `[TABLE]` **The JVM's regions, named.** Java heap (one large `rw-p` anonymous reservation),
       Metaspace and compressed class space (separate `mmap`s), the code cache (`rwxp`),
       GC internal structures (card table, remembered sets, mark bitmaps — roughly a few percent
       of heap), per-thread stacks (1 MB each), direct `ByteBuffer` regions, mapped
       `MappedByteBuffer` files, and the native heap used by glibc, JIT and JNI. `[TABLE]`
       `[X-REF 06]`
1.11.5 `[CALC]` **The RSS composition arithmetic for `DocumentVerification`** (8 GB heap, 6
       instances, 2–6 MB image buffers): 8 GB heap + ~350 MB metaspace and code cache + 6 GC
       structures at ~3% of heap (~240 MB) + 200 threads × 1 MB stack (~200 MB touched far less) +
       direct buffers holding up to 40 concurrent 6 MB documents (**240 MB**) + glibc arenas.
       Setting `-Xmx8g` in an 8 GB container guarantees an OOMKill. `-XX:MaxRAMPercentage=70` and
       `-XX:MaxDirectMemorySize` are the two flags that make it survivable. `[CALC]` `[NUM]`
       `[TRAP]`
1.11.6 `[SYSCALL]` `void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t
       offset)` and the flag combinations that matter: `MAP_PRIVATE|MAP_ANONYMOUS` (memory
       allocation), `MAP_SHARED` + fd (shared memory / file), `MAP_PRIVATE` + fd (COW file
       mapping — how the loader maps text), `MAP_NORESERVE`, `MAP_FIXED`, `MAP_POPULATE`,
       `MAP_HUGETLB`, `MAP_STACK`. `[SYSCALL]` `[TABLE]`
1.11.7 `[SYSCALL]` `int mprotect(void *addr, size_t len, int prot)` as the mechanism behind
       guard pages, GC write barriers via `PROT_NONE` tripwires, and the JVM's ability to make the
       code cache non-writable. `madvise(addr, len, advice)` with `MADV_DONTNEED`,
       `MADV_FREE`, `MADV_HUGEPAGE`, `MADV_NOHUGEPAGE`, `MADV_WILLNEED`, `MADV_COLD`,
       `MADV_PAGEOUT`. `[SYSCALL]` `[API]`
1.11.8 `[API]` **Memory-mapped files in Java:**
       `FileChannel.map(MapMode.READ_ONLY, position, size)` returns a `MappedByteBuffer` whose
       pages are page-cache pages — reads are minor faults, not syscalls, and the OS does the
       readahead. Java 21's `MemorySegment.mapFile` / `Arena` is the modern API. The trap: the
       mapping is not unmapped until the buffer is collected, so a mapped 6 MB document image
       holds address space and page cache indefinitely. `[API]` `[TRAP]`
1.11.9 `[CALC]` **VSZ is nearly meaningless for a JVM; RSS is what is in RAM.** A JVM with
       `-Xmx12g` reserves 12 GB of address space at start (`VmSize` ≈ 15–20 GB with everything
       else) while `VmRSS` may be 900 MB. `ps aux`'s `VSZ` column causes more false alarms than any
       other number on the box. `[CALC]` `[TRAP]` `[PROC]`
1.11.10 `[PROC]` **RSS is not one number.** `/proc/<pid>/status` breaks it into `RssAnon:` (heap,
        stacks, anonymous mmaps — the memory only you hold), `RssFile:` (mapped executables and
        libraries, shared with every other instance), and `RssShmem:`. Six
        `DocumentVerification` instances on one host share their `RssFile` exactly once, so summing
        RSS across them overcounts. **`Pss`** in `smaps_rollup` is the share-corrected figure.
        `[PROC]` `[CALC]`
1.11.11 Stack growth and its limits: the main stack grows downward on fault up to `RLIMIT_STACK`
        (`ulimit -s`, commonly **8192** KB), with a guard gap below it. `StackOverflowError` in
        Java is the JVM's own yellow-zone guard page being touched, **not** the kernel's — which
        is why it is catchable while a native stack overflow is a `SIGSEGV`. `[SYSCTL]` `[NUM]`
1.11.12 `[API]` **Native Memory Tracking** as the only way to attribute a JVM's non-heap RSS:
        `-XX:NativeMemoryTracking=summary` then
        `jcmd <pid> VM.native_memory summary scale=MB`, giving per-category reserved/committed for
        Java Heap, Class, Thread, Code, GC, Compiler, Internal, Symbol and Other. The workflow is
        owned by `06-jvm-internals.md`; the reason you need it is this section. `[API]`
        `[X-REF 06]`
1.11.13 `[INCIDENT]` Symptom: `DocumentVerification` pods are OOMKilled (**exit 137**, no Java
        stack trace) at an 8 GB limit while `jcmd GC.heap_info` shows the heap steady at 4.1 GB.
        Diagnosis: `VM.native_memory summary` shows `Other (reserved=...  committed=2.9GB)`;
        `/proc/<pid>/smaps_rollup` confirms `RssAnon: 7.6 GB`. Root cause: direct `ByteBuffer`s
        for 2–6 MB document images with no `MaxDirectMemorySize`, accumulating because the
        reference-cleaner ran only at GC and GC was infrequent on a half-empty heap. Fix:
        `-XX:MaxDirectMemorySize=1g`, explicit buffer pooling, and `MaxRAMPercentage=60` so the
        native ceiling is deliberate rather than discovered. `[INCIDENT]` `[PROC]` `[CALC]`

*(13 leaves)*

## §1.12 Page faults: minor, major, copy-on-write, demand paging and pre-faulting

1.12.1 A page fault is a **CPU exception**, not a syscall: the MMU finds no valid PTE (or a
       permission violation), traps to `do_page_fault`, and the kernel either fixes the mapping and
       resumes the instruction, or delivers `SIGSEGV`/`SIGBUS`. The faulting instruction is
       *restarted*, which is why the mechanism is invisible to the program. `[PROVE]` `[SOURCE]`
1.12.2 `[TABLE]` **Minor fault** — the page is already in physical memory and only the mapping is
       missing (shared library already loaded by another process, page-cache hit for a mapped file,
       first touch of an anonymous page satisfied from the free list, COW resolution). Cost: on the
       order of **hundreds of nanoseconds to a few microseconds**. **Major fault** — the page must
       be read from a block device (executable text not yet loaded, page-cache miss on a mapped
       file, **swap-in**). Cost: **~100 µs on NVMe, ~5–10 ms on network-attached or spinning
       storage**. `[TABLE]` `[NUM]` `[CALC]`
1.12.3 `[CALC]` The ratio is the whole point: a major fault is **1,000–10,000×** a minor fault.
       Fifteen major faults inside a `ClientRestrictions` request at 8 ms each is **120 ms** —
       four times its entire **30 ms** budget — from an event that consumes no CPU and appears
       nowhere in a CPU profile. `[CALC]` `[NUM]` `[PROVE]`
1.12.4 `[PROC]` The counters, exactly: `/proc/<pid>/stat` fields **10 (`minflt`)**, 11 (`cminflt`),
       **12 (`majflt`)**, 13 (`cmajflt`); per-thread equivalents under `/proc/<tgid>/task/<tid>/stat`;
       system-wide `pgfault` and `pgmajfault` in `/proc/vmstat`; and `ps -o min_flt,maj_flt -p <pid>`.
       `perf stat -e page-faults,major-faults` measures a window rather than a lifetime total.
       `[PROC]` `[DIAG]`
1.12.5 **Demand paging** as the default: `mmap` and `malloc` return immediately having only created
       a VMA. Physical memory is allocated at **first touch**, one fault per page. This is why a
       program can allocate 100 GB on a 16 GB box and why `Committed_AS` can exceed
       `MemTotal`. `[PROVE]`
1.12.6 **The zero page:** a read fault on an untouched anonymous page maps a shared read-only page
       of zeros rather than allocating a frame. The frame is allocated only on the first *write*.
       This is why `calloc` of a large region is nearly free and why RSS grows on write, not on
       allocation. `[PROVE]`
1.12.7 `[FLOW]` **Copy-on-write, step by step:** (1) `fork` copies page tables and marks every
       writable page **read-only** in both parent and child, incrementing each frame's refcount;
       (2) either process writes; (3) the write faults on a read-only PTE; (4) the kernel allocates
       a new frame, copies 4 KiB, and marks the new PTE writable; (5) the instruction restarts.
       Each fault is minor, and there is one per written page. `[FLOW]` `[PROVE]`
1.12.8 `[CALC]` **Why COW is a JVM hazard.** A GC touches essentially the whole heap, so a `fork`
       from a 12 GB `FundsLedger` JVM converts a "cheap" COW snapshot into up to
       12 GiB / 4 KiB = **3.1 million** COW faults and, worst case, a full 12 GB duplication.
       `posix_spawn` (JDK 13+ default) avoids it; `Runtime.exec` under
       `-Djdk.lang.Process.launchMechanism=FORK` does not. `[CALC]` `[TRAP]`
1.12.9 `[API]` **Pre-faulting** as the deliberate alternative: `mmap(MAP_POPULATE)`,
       `madvise(MADV_WILLNEED)`, and in the JVM **`-XX:+AlwaysPreTouch`**, which writes one byte
       per page of the heap at startup. It converts thousands of unpredictable in-request faults
       into a slower, bounded, one-time startup cost — which is exactly the trade a
       latency-budgeted service should make. Cost: startup time and immediate full RSS.
       `[API]` `[CALC]`
1.12.10 `[TRAP]` **Trap:** `-XX:+AlwaysPreTouch` plus `-Xms == -Xmx` makes the pod's RSS equal its
        heap at second zero, so a memory *request* sized from steady-state observation now fails
        scheduling or trips a `memory.high` throttle at start. Pre-touch and container sizing must
        be decided together. `[TRAP]` `[X-REF 19]`
1.12.11 `SIGSEGV` vs `SIGBUS`: `SIGSEGV` is an access with no valid mapping or wrong permissions;
        `SIGBUS` is a valid mapping whose backing store cannot satisfy it — classically reading a
        `MappedByteBuffer` past the end of a file that was truncated underneath you, or an I/O
        error on a mapped page. Both produce an `hs_err_pid<pid>.log`, whose `siginfo` line names
        which. `[DIAG]` `[TRAP]`
1.12.12 `[BUILD]` Attributing faults to code: `perf record -e major-faults -p <pid>` then
        `perf report`, or
        `bpftrace -e 'software:major-faults:1 /pid == $1/ { @[ustack] = count(); }'` to get user
        stacks for the faulting paths. This is how you prove a major-fault story rather than assert
        it. `[BUILD]` `[DIAG]`
1.12.13 `[INCIDENT]` Symptom: the first 90 seconds after every `BankDeposits` deploy show 40× the
        normal ingestion latency, then it recovers permanently. Diagnosis:
        `ps -o min_flt,maj_flt` shows `maj_flt` climbing by ~180,000 during the window and flat
        afterwards; `/proc/pressure/io` `some avg10=54` during the window only. Root cause: cold
        page cache — the 40k-record statement file and the JVM's own class-loading reads were all
        major faults on a freshly started container with no cache warmth. Fix: a readiness probe
        that does not pass until a warm-up pass has run, plus `MAP_POPULATE` on the statement-file
        mapping. Not a code bug — an unaccounted OS cost. `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.13 The page cache, dirty pages and writeback

1.13.1 The page cache is the kernel's unified cache of file contents, keyed by (inode, offset), and
       **it uses all otherwise-free RAM by design**. Every buffered `read`/`write` and every
       `MAP_SHARED` file mapping goes through it; a read of a cached page never touches the device.
       `[PROVE]`
1.13.2 `[PROC]` `/proc/meminfo`, the lines that matter: `MemTotal`, `MemFree`, **`MemAvailable`**,
       `Buffers`, `Cached`, `SwapCached`, `Active(file)`/`Inactive(file)`,
       `Active(anon)`/`Inactive(anon)`, **`Dirty`**, **`Writeback`**, `Mapped`, `Shmem`, `Slab`,
       `SReclaimable`, `PageTables`, `AnonHugePages`, `CommitLimit`, `Committed_AS`. `[PROC]`
       `[TABLE]`
1.13.3 `[DIAG]` **`free -h` and the one column that matters.** In
       `total 16Gi / used 6.0Gi / free 0.3Gi / buff/cache 9.7Gi / available 9.4Gi`, `free` is
       **completely unused** RAM, which on a healthy long-running box is near zero *by design*,
       and **`available`** is the kernel's own estimate of what a new allocation could obtain
       counting reclaimable cache. Read `available`. `[DIAG]` `[TRAP]`
1.13.4 `[TRAP]` **Trap:** "we're out of memory, `free` shows 300 MB." Almost always wrong. You are
       genuinely short only when `available` is small **and** `si`/`so` in `vmstat` are non-zero
       **and** `/proc/pressure/memory` `full avg10` is elevated. Three signals, not one. `[TRAP]`
       `[PROC]`
1.13.5 `[SYSCTL]` **Writeback thresholds, with defaults:** `vm.dirty_background_ratio` (**10**% of
       available memory — background flushers start), `vm.dirty_ratio` (**20**% — the *writing
       process itself* is throttled synchronously), `vm.dirty_expire_centisecs` (**3000** = 30 s —
       age at which a dirty page must be written), `vm.dirty_writeback_centisecs` (**500** = 5 s —
       flusher wake interval), and the `_bytes` variants that override the ratios. `[SYSCTL]`
       `[NUM]` `[RESEARCH]`
1.13.6 `[CALC]` **Why `dirty_ratio` produces a latency cliff.** On a 64 GB host,
       `dirty_ratio = 20` allows **~12.8 GB** of dirty pages before the writer is throttled. A
       `BankDeposits` ingestion that dirties faster than the gp3 volume drains hits the ratio, and
       *every* writing thread — including unrelated ones — is then stalled in
       `balance_dirty_pages` until writeback catches up. The symptom is a multi-second stall with
       no CPU load and no application change. Fix: lower the ratio so throttling is gradual, or
       use `_bytes` to make it absolute rather than proportional to a host size you do not
       control. `[CALC]` `[PROVE]` `[INCIDENT]`
1.13.7 `[SYSCALL]` **The durability syscalls and exactly what each guarantees:**
       `int fsync(int fd)` — data *and* metadata for one file, durable on the device;
       `int fdatasync(int fd)` — data plus only the metadata needed to read it back (skips
       `mtime`), measurably cheaper; `sync_file_range` — start writeback without a durability
       guarantee; `msync(addr, len, MS_SYNC)` for mapped regions; `syncfs` for a whole filesystem.
       `O_SYNC`/`O_DSYNC` make every `write` durable; `O_DIRECT` bypasses the page cache entirely.
       `[SYSCALL]` `[TABLE]`
1.13.8 `[TRAP]` **Trap:** "`write()` returned, so the data is safe." It is in the page cache. A
       power loss or kernel panic loses it. Only `fsync`/`fdatasync` returning **0** makes it
       durable — and an `fsync` returning `EIO` may mean the dirty pages were already discarded, so
       retrying it does not recover them. Databases handle this; application code writing the
       `PaymentRun` payout file usually does not. `[TRAP]` `[X-REF 09]`
1.13.9 `[CALC]` **The `fsync` cost that decides a batch design.** An `fsync` on gp3 costs roughly
       one device round trip — on the order of **0.5–2 ms**. `BankDeposits` ingesting a
       40k-record file with one `fsync` per record spends **20–80 seconds** in `fsync` alone; one
       `fsync` per 1,000-record batch spends **20–80 ms**. The 500k-record month-end file makes the
       difference 4–17 minutes versus 0.25–1 second. `[CALC]` `[NUM]`
1.13.10 `[SYSCTL]` **Readahead:** `/sys/block/<dev>/queue/read_ahead_kb` (**128** KB typically),
        `posix_fadvise(fd, off, len, POSIX_FADV_SEQUENTIAL | POSIX_FADV_RANDOM | POSIX_FADV_DONTNEED)`,
        and `blockdev --getra`. Sequential detection is why a 40k-record file streams at device
        bandwidth and random 180-byte ledger reads do not. `[SYSCTL]` `[X-REF 09]`
1.13.11 `[API]` **Cache eviction and pollution.** Reading a 68 GB/day stream of document images
        evicts the page cache that `FundsLedger`'s index files were relying on, on a shared host.
        `posix_fadvise(POSIX_FADV_DONTNEED)` after streaming, or `O_DIRECT`, keeps a
        write-once-read-never workload from displacing a hot one. `[API]` `[PROVE]`
1.13.12 `[BUILD]` Inspecting the cache: `vmtouch -v <file>` for per-file residency,
        `/proc/sys/vm/drop_caches` (`echo 3 >` — **a diagnostic-only, never-in-production** tool),
        `cachestat` (bcc) for hit ratio, and `filetop`/`biolatency` for who is doing the I/O.
        `[BUILD]` `[DIAG]`
1.13.13 `[PROC]` cgroup v2 makes the page cache accountable: `memory.stat` reports `file`,
        `file_dirty`, `file_writeback`, `inactive_file`, `active_file`, `pgfault`, `pgmajfault`,
        `pgscan`, `pgsteal`, `workingset_refault_file` per cgroup — so you can prove *which
        container* is thrashing the cache. `[PROC]` `[RESEARCH]`
1.13.14 `[INCIDENT]` Symptom: `FundsLedger` p99 write latency triples every day at 06:05 and
        recovers by 06:40, with no change in its own write rate. Diagnosis: `memory.stat` on the
        `FundsLedger` cgroup shows `workingset_refault_file` spiking; the `BankDeposits` cgroup
        shows 40 GB of `file` growth in the same window. Root cause: page-cache eviction by the
        co-located statement-file ingestion — a resource the two services shared and neither
        declared. Fix: `memory.min` on `FundsLedger` to protect its cache, and
        `POSIX_FADV_DONTNEED` on the ingestion read path. `[INCIDENT]` `[PROC]`

*(14 leaves)*

## §1.14 User-space allocation: `brk`, `mmap`, glibc arenas, overcommit

1.14.1 **`malloc` is a library, not a syscall.** glibc's allocator satisfies most requests from
       memory it already holds, and calls the kernel only to grow: `brk`/`sbrk` for the main heap
       and `mmap` for large or thread-local requests. `free` usually returns memory to the
       allocator, **not** to the kernel — which is why RSS does not fall when a Java native
       library frees. `[PROVE]` `[SYSCALL]`
1.14.2 `[SYSCALL]` `int brk(void *addr)` / `void *sbrk(intptr_t increment)` move the top of the
       `[heap]` VMA. `brk` can only shrink from the top, so a single live allocation at the top
       pins everything below it — the classic heap-fragmentation-looks-like-a-leak shape.
       `[SYSCALL]` `[PROVE]`
1.14.3 `[SYSCTL]` **glibc's `mmap` threshold:** `M_MMAP_THRESHOLD` starts at **128 KiB** and is
       **dynamic** — glibc raises it (up to `DEFAULT_MMAP_THRESHOLD_MAX`, **32 MiB** on 64-bit)
       whenever an `mmap`'d block is freed, on the theory that the workload will reuse that size.
       Set `MALLOC_MMAP_THRESHOLD_` in the environment or `mallopt(M_MMAP_THRESHOLD, n)` to pin it.
       `M_TRIM_THRESHOLD` is **128 KiB**. `[SYSCTL]` `[NUM]` `[RESEARCH]`
1.14.4 `[CALC]` **glibc arenas — the container RSS trap.** To reduce lock contention glibc creates
       per-thread arenas up to **8 × number of cores** on 64-bit. On a 64-core host that is **512**
       arenas, each able to hold up to 64 MiB of `HEAP_MAX_SIZE` address space; the arenas are
       never merged and rarely trimmed, so a multi-threaded JVM's *native* RSS grows and never
       recedes. `MALLOC_ARENA_MAX=2` (or `4`) is the standard fix and typically reclaims hundreds
       of MB on `DocumentVerification`. `[CALC]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.14.5 `[TRAP]` **Trap:** "the JVM's memory is `-Xmx`, so `MALLOC_ARENA_MAX` is irrelevant." The
       JVM itself calls `malloc` for JIT structures, symbol tables, GC metadata and every JNI
       library — and `DocumentVerification`'s image codecs are native. Arena growth is counted in
       the cgroup's `memory.current` and gets you OOMKilled with a clean heap. `[TRAP]`
1.14.6 `[API]` `malloc_trim(0)` returns free top-of-arena pages to the kernel and is callable from
       Java only via JNI or a `jcmd`-triggered path — which is why the practical answers are
       `MALLOC_ARENA_MAX`, switching to **jemalloc** or **tcmalloc** via `LD_PRELOAD`, or moving
       the allocation into the Java heap. jemalloc also gives you `jeprof` heap profiling for
       native leaks. `[API]` `[BUILD]`
1.14.7 `[SYSCTL]` **Overcommit, exactly.** `vm.overcommit_memory`: **0** (default) — "the kernel
       compares the userspace memory request size against total memory plus swap and rejects
       obvious overcommits"; **1** — "pretends there is always enough memory until it actually runs
       out"; **2** — "a 'never overcommit' policy that attempts to prevent any overcommit".
       `vm.overcommit_ratio` (**50**) and `vm.overcommit_kbytes` set the mode-2 ceiling.
       `[SYSCTL]` `[SOURCE]` `[RESEARCH]`
1.14.8 `[CALC]` **The mode-2 arithmetic:** `CommitLimit = swap + MemTotal × overcommit_ratio/100`.
       On a 64 GB host with no swap and `overcommit_ratio = 50`, `CommitLimit` is **32 GB** — so
       three `FundsLedger` instances reserving 12 GB of heap each (36 GB committed) cannot all
       start, on a box with 64 GB of RAM. Both numbers are in `/proc/meminfo` as `CommitLimit`
       and `Committed_AS`. `[CALC]` `[PROC]` `[TRAP]`
1.14.9 `[SYSCTL]` `vm.admin_reserve_kbytes` (**min(3% of free pages, 8 MiB)**) and
       `vm.user_reserve_kbytes` (**min(3% of current process size, 128 MiB)**) — the reserves that
       exist so that under mode 2 root can still log in and kill something. `[SYSCTL]`
       `[RESEARCH]`
1.14.10 `[PROVE]` Why overcommit exists at all: `fork` COW, the zero page, `MAP_NORESERVE`, sparse
        thread-stack reservation and the JVM's up-front heap reservation all allocate address space
        that will never be fully touched. Refusing them would waste most of the machine. The price
        is that allocation failure is deferred from `malloc` to the **OOM killer** (§1.15).
        `[PROVE]`
1.14.11 `[API]` The Java side of native allocation: `ByteBuffer.allocateDirect` (bounded by
        `-XX:MaxDirectMemorySize`, defaulting to `-Xmx` when unset), `Unsafe.allocateMemory`,
        Java 21's `Arena`/`MemorySegment` from the FFM API, and `Cleaner`-based reclamation — which
        runs only at GC, so direct-buffer pressure is invisible until it isn't. `[API]`
        `[X-REF 06]`
1.14.12 `[BUILD]` Attributing native allocation: `jcmd <pid> VM.native_memory detail.diff`,
        `LD_PRELOAD=libjemalloc.so` with `MALLOC_CONF=prof:true` plus `jeprof`, and
        `bpftrace -e 'uprobe:libc:malloc { @ = hist(arg0); }'` for a size histogram. `[BUILD]`
        `[DIAG]`
1.14.13 `[INCIDENT]` Symptom: six `DocumentVerification` pods each drift from 5.2 GB to 7.9 GB RSS
        over ten days and get OOMKilled, with the Java heap flat at 4 GB and NMT showing no growth
        in any JVM category. Diagnosis: `/proc/<pid>/maps | grep -c 'rw-p'` shows 480+ anonymous
        64 MiB regions; `MALLOC_ARENA_MAX` unset on a 64-core node. Root cause: glibc per-thread
        arena proliferation driven by the native image codec, with fragmentation preventing trim.
        Fix: `MALLOC_ARENA_MAX=4` in the pod env, dropping steady-state RSS by 1.9 GB, plus
        jemalloc for the codec path. `[INCIDENT]` `[PROC]` `[CALC]`

*(13 leaves)*

## §1.15 Memory reclaim, swap, and the OOM killer

1.15.1 `[TABLE]` **Watermarks.** Each memory zone has `min`, `low` and `high` watermarks
       (`/proc/zoneinfo`). Free memory falling below `low` wakes **`kswapd`** to reclaim
       asynchronously up to `high`; falling below `min` forces **direct reclaim** in the context of
       the allocating thread, which is a synchronous stall the application feels.
       `vm.min_free_kbytes` and `vm.watermark_scale_factor` (**10**, i.e. 0.1% of memory) set the
       gaps. `[TABLE]` `[SYSCTL]` `[RESEARCH]`
1.15.2 `[PROVE]` **`kswapd` versus direct reclaim is the whole latency story.** Background reclaim
       is free to the application; direct reclaim means your request thread is scanning LRU lists
       and writing pages before its `malloc` returns. `/proc/vmstat`'s `allocstall_*` counters
       count direct-reclaim entries, and `pgscan_kswapd` vs `pgscan_direct` tells you which regime
       you are in. `[PROVE]` `[PROC]`
1.15.3 `[TABLE]` **Classic reclaim:** four LRU lists — `active_anon`, `inactive_anon`,
       `active_file`, `inactive_file`. Pages enter inactive, get promoted on a second reference,
       and are reclaimed from the inactive tail. Clean file pages are dropped for free; dirty file
       pages must be written first; anonymous pages need **swap** or cannot be reclaimed at all.
       `[TABLE]` `[PROVE]`
1.15.4 `[VERSION-TRAP]` **MGLRU** (6.1+) replaces that with **generations**: pages are aged into
       numbered generations, `min_gen_nr` holding the coldest and `max_gen_nr` the hottest, with
       `max_gen_nr` and `max_gen_nr-1` "not fully aged (equivalent to the active list) and
       therefore cannot be evicted". Enable via `/sys/kernel/mm/lru_gen/enabled` (bit `0x0001`
       main switch, `0x0002` leaf accessed-bit clearing, `0x0004` non-leaf), inspect
       `/sys/kernel/debug/lru_gen`, and set `min_ttl_ms` (default **0** = disabled; "N=1000
       usually eliminates intolerable janks due to thrashing") to protect a working set.
       `[VERSION-TRAP]` `[PROC]` `[RESEARCH]`
1.15.5 `[SYSCTL]` **`vm.swappiness`: default 60, range 0–200**, documented as "the rough relative
       IO cost of swapping and filesystem paging... At 100, the VM assumes equal IO cost and will
       thus apply memory pressure to the page cache and swap-backed pages equally; lower values
       signify more expensive swap IO". **0 does not disable swap** — it only makes the kernel
       avoid it until it must. `vm.page-cluster` (**3** = 8 pages read per swap-in) tunes swap
       readahead. `[SYSCTL]` `[SOURCE]` `[VERSION-TRAP]` `[RESEARCH]`
1.15.6 `[PROVE]` **Why sustained swapping destroys a JVM specifically.** GC traverses live objects
       across the whole heap, so a 12 GB `FundsLedger` heap with 2 GB swapped out faults those
       pages back in *during a stop-the-world pause*, at ~100 µs–8 ms each. 500,000 swapped pages
       × 200 µs is **100 seconds** of pause. The service is not down, it is worse than down — it
       is timing out at every layer while every health check that measures liveness passes.
       `[PROVE]` `[CALC]` `[NUM]`
1.15.7 `[DIAG]` The swap signals: `vmstat 1`'s **`si`/`so`** columns (**must be 0** on a
       latency-sensitive box), `VmSwap:` in `/proc/<pid>/status`, `Swap:` per-VMA in
       `/proc/<pid>/smaps`, `swapon --show`, and `memory.swap.current`/`memory.swap.max` per cgroup.
       Non-zero `so` on a `FundsLedger` host is an alert, not a curiosity. `[DIAG]` `[PROC]`
1.15.8 `zswap` (compressed swap cache in RAM,
       `/sys/module/zswap/parameters/enabled`) and `zram` (a compressed RAM block device) as the
       middle ground: they convert a major fault into a decompress instead of a device read,
       trading CPU for latency. Worth stating because "swap or no swap" is a false binary.
       `[SYSCTL]`
1.15.9 `[VERSION-TRAP]` **Kubernetes and swap.** `NodeSwap` reached beta with `LimitedSwap` (only
       Burstable pods, proportional to their memory request) and `UnlimitedSwap`; the historical
       hard requirement that kubelet refuses to start with swap enabled is pre-1.22. The right
       answer for `FundsLedger` is still no swap — for the GC reason in 1.15.6, not because
       Kubernetes forbids it. `[VERSION-TRAP]` `[RESEARCH]`
1.15.10 `[CALC]` **`oom_badness`, the scoring function:** roughly
        `RSS + swap_usage + page_table_bytes`, in pages, normalised to 0–1000, then adjusted by
        `oom_score_adj × total_pages / 1000`. `/proc/<pid>/oom_score_adj` ranges **−1000
        (immune) to +1000**, `/proc/<pid>/oom_score` is the result. Consequence: **the biggest
        process gets killed**, which on a host running a JVM and a sidecar is always the JVM,
        regardless of which one leaked. `[CALC]` `[PROC]` `[NUM]`
1.15.11 `[DIAG]` **Reading a kernel OOM record.** `dmesg -T | grep -iE 'killed process|oom'` yields
        a task table (pid, uid, tgid, `total_vm`, `rss`, `pgtables_bytes`, `swapents`,
        `oom_score_adj`, name) followed by
        `Out of memory: Killed process 21418 (java) total-vm:14892340kB, anon-rss:8140228kB,
        file-rss:0kB, shmem-rss:0kB, UID:1000 pgtables:16284kB oom_score_adj:0`. Read
        `anon-rss` against the container limit, and read the task table to see who *else* was
        growing. `[DIAG]` `[PROC]`
1.15.12 `[TABLE]` **Kernel OOM kill versus JVM `OutOfMemoryError` — different events, different
        evidence.** Kernel: the *host or cgroup* ran out of physical memory, `SIGKILL`, no cleanup,
        no stack trace, exit **137**, evidence in `dmesg` and `memory.events`'s `oom_kill` counter
        and Kubernetes `OOMKilled`. JVM: the *heap, metaspace or direct-buffer ceiling* is
        exhausted and GC cannot reclaim; an `Error` is thrown, there is a stack trace, hooks may
        run, and `-XX:+HeapDumpOnOutOfMemoryError` produces an hprof. Confusing them costs hours.
        `[TABLE]` `[TRAP]`
1.15.13 `[SYSCTL]` **cgroup-level OOM control:** `memory.max` (hard limit — exceeding it triggers
        cgroup OOM), `memory.high` (**throttle** rather than kill — the allocating task is stalled
        proportionally), `memory.low` and `memory.min` (reclaim protection), `memory.oom.group`
        (kill the whole cgroup atomically rather than one task), and `memory.events`'s `low`,
        `high`, `max`, `oom` and `oom_kill` counters. `memory.high` is the underused one: it turns
        a kill into a slowdown you can alert on. `[SYSCTL]` `[PROC]` `[RESEARCH]`
1.15.14 `[SYSCTL]` `vm.panic_on_oom` (**0**), `vm.oom_kill_allocating_task` (**0** — kill the
        biggest, not the requester), `vm.oom_dump_tasks`, and `systemd-oomd` acting on
        **PSI** thresholds (`ManagedOOMMemoryPressure=`,
        `ManagedOOMMemoryPressureLimit=`) to kill *before* the kernel has to — user-space OOM
        management being the current direction of travel. `[SYSCTL]` `[RESEARCH]`
1.15.15 `[INCIDENT]` Symptom: a `FundsLedger` pod disappears during the 3,400/sec settlement burst.
        Kubernetes reports `OOMKilled`, exit **137**; the application log ends mid-request with no
        error and no `OutOfMemoryError`. Diagnosis: `kubectl get events` plus
        `memory.events`'s `oom_kill 1`; `dmesg` shows `anon-rss:12648992kB` against a 13 GB limit;
        NMT shows heap 12 GB committed as configured. Root cause: `-Xmx12g` set equal to the
        container limit, leaving no room for metaspace, code cache, 214 thread stacks, GC
        structures and glibc arenas. Fix: `-XX:MaxRAMPercentage=70` against a 16 GB limit, so the
        JVM sizes itself from `memory.max` and the native overhead has declared headroom; plus a
        `memory.high` at 85% so the next occurrence throttles and alerts instead of vanishing.
        `[INCIDENT]` `[CALC]` `[PROC]`

*(15 leaves)*

## §1.16 File descriptors, the three tables, and the limits that break production

1.16.1 `[TABLE]` **The three tables, and why the distinction matters.** (1) The per-process
       **fd table** (`files_struct`) maps a small integer to a `struct file *`. (2) The system-wide
       **open file table** holds `struct file` — the **file offset**, the open flags, and a
       reference count. (3) The **inode table** holds `struct inode` — the actual file, its size,
       permissions and link count. `dup`/`dup2`/`fork` create new *fd table* entries pointing at
       the *same* `struct file`, so they **share the offset**; a second `open()` of the same path
       creates a new `struct file` with an independent offset onto the same inode. `[TABLE]`
       `[PROVE]`
1.16.2 An fd is not "a file": sockets, pipes, FIFOs, epoll instances, eventfd, signalfd, timerfd,
       inotify watches, pidfds, memfds and `/dev` nodes are all fds. `0`/`1`/`2` are
       stdin/stdout/stderr by convention only — `close(1)` then `open()` gets you fd 1 back,
       because **`open` returns the lowest available fd**. `[PROVE]`
1.16.3 `[SYSCTL]` **The four limits, in the order they bind.** `RLIMIT_NOFILE` **soft**
       (`ulimit -n`) is what the process may use and may raise itself up to the hard limit;
       `RLIMIT_NOFILE` **hard** (`ulimit -Hn`) is the ceiling, raisable only with
       `CAP_SYS_RESOURCE`; `fs.nr_open` (**1048576**) caps what the hard limit may be set to;
       `fs.file-max` is the system-wide count of open files. Per-cgroup there is no fd limit —
       `pids.max` limits tasks, not fds. `[SYSCTL]` `[NUM]` `[TABLE]`
1.16.4 `[VERSION-TRAP]` systemd 240+ deliberately keeps the **soft** limit at **1024** (for
       `select()`-based programs, which corrupt memory above `FD_SETSIZE`) while setting the
       **hard** limit to **524288** — `DefaultLimitNOFILE=1024:524288`. Modern container runtimes
       set large defaults of their own rather than inheriting the daemon's. So "containers get
       1024 fds" is runtime-specific, and the **only** authoritative answer is
       `/proc/<pid>/limits`. `[VERSION-TRAP]` `[RESEARCH]`
1.16.5 `[TRAP]` **Trap:** **the limit that applies is the one in force when the process was
       `exec`'d**, not what your shell shows now. Raising `ulimit -n` in your SSH session changes
       nothing about a running `ApplicationGateway`. Set it in the systemd unit
       (`LimitNOFILE=65536`), the pod spec, or the runtime config — then **verify** with
       `grep 'open files' /proc/<pid>/limits`. `[TRAP]` `[PROC]`
1.16.6 `[PROC]` `/proc/<pid>/limits` — a real line:
       `Max open files            65536                65536                files`
       (soft, hard, units). `/proc/<pid>/fd/` is a symlink directory (one entry per fd, resolving
       to the target — `socket:[38471]`, `pipe:[38470]`, `/var/log/fundsledger/application.log`),
       `/proc/<pid>/fdinfo/<fd>` gives `pos`, `flags`, `mnt_id` and, for epoll fds, the registered
       set. `/proc/sys/fs/file-nr` gives allocated / free / max system-wide. `[PROC]` `[DIAG]`
1.16.7 `[BUILD]` The counting one-liners: `ls /proc/<pid>/fd | wc -l` (exact and cheap),
       `lsof -p <pid> | wc -l`, and the type breakdown
       `ls -l /proc/<pid>/fd | awk '{print $NF}' | sed 's/\[.*//' | sort | uniq -c | sort -rn`.
       Prefer `/proc` over `lsof` on a busy box — `lsof` walks every process. `[BUILD]` `[DIAG]`
1.16.8 `[CALC]` **The fd budget for `ApplicationGateway`** at its **55k concurrent session** peak
       across 40 instances: 1,375 client sockets per instance + one upstream socket per in-flight
       backend call (say 400) + 12 epoll/eventfd/timerfd instances + ~30 log and config files +
       JAR file mappings ≈ **~1,850**. A soft limit of 1024 fails at roughly **60%** of design
       load — so it fails first during the exact traffic spike it was provisioned for. 65536 is the
       normal service value. `[CALC]` `[NUM]`
1.16.9 `[DIAG]` **`Too many open files` has exactly two causes and you must distinguish them.**
       (a) *Limit too low for legitimate load* — the fd count is high, **stable**, and
       proportional to concurrency; raise the limit. (b) *An fd leak* — the count rises
       **monotonically** and never falls, even when traffic drops; raising the limit only moves the
       crash. The diagnostic is one sample per minute for ten minutes, not one sample.
       `[DIAG]` `[TRAP]`
1.16.10 `[API]` The Java surface: `java.io.IOException: Too many open files` and
        `java.net.SocketException: Too many open files`; leaks come from unclosed `InputStream`,
        `HttpResponse` bodies, `FileChannel`, JDBC `Connection`/`Statement`/`ResultSet`, and
        `Files.list`/`Files.walk` streams (which hold a directory fd until closed).
        **try-with-resources on every one, always** — a hand-written `finally` is where leaks
        live. `[API]` `[BUILD]`
1.16.11 `[SYSCALL]` fd lifecycle syscalls: `int dup2(int oldfd, int newfd)`,
        `int dup3(int oldfd, int newfd, int flags)`, `fcntl(fd, F_SETFD, FD_CLOEXEC)`, and
        **`O_CLOEXEC` as the flag you must pass at `open` time** — without it a `fork`+`exec`
        leaks every fd into the child, which is both a leak and a security hole (the child inherits
        your database socket). `[SYSCALL]` `[X-REF 13]`
1.16.12 `[SYSCALL]` **`epoll` as a kernel mechanism** (the network-server usage is
        `10-networking.md`'s): `int epoll_create1(int flags)` returns an fd holding an interest set
        (a red-black tree of `epitem`) and a ready list; `epoll_ctl(epfd, EPOLL_CTL_ADD|MOD|DEL,
        fd, struct epoll_event *)` mutates it; `epoll_wait(epfd, events, maxevents, timeout)`
        returns only ready fds, making it **O(ready)** rather than `select`'s O(watched). Each
        registered fd costs kernel memory, and the epoll instance is itself an fd counted against
        `RLIMIT_NOFILE`. `[SYSCALL]` `[X-REF 10]`
1.16.13 `[BUILD]` Raising the limit in each of the three places that actually matter, with the
        verification step for each: a systemd drop-in (`LimitNOFILE=65536` under `[Service]`,
        then `systemctl show -p LimitNOFILE`), a Kubernetes pod (`securityContext` /
        runtime default, then `kubectl exec -- cat /proc/1/limits`), and
        `/etc/security/limits.conf` for interactive logins (which does **not** apply to systemd
        services — the most common misconfiguration). `[BUILD]` `[TRAP]`
1.16.14 `[INCIDENT]` Symptom: `ApplicationGateway` instances begin returning 502s during a major
        sporting event as concurrent sessions climb from 14k toward 55k; the log fills with
        `java.io.IOException: Too many open files`. Diagnosis:
        `grep 'open files' /proc/1/limits` shows `1024 1024`; `ls /proc/1/fd | wc -l` shows 1021,
        and the type breakdown is 96% `socket:[...]` — high but *stable per unit of traffic*, so a
        limit problem rather than a leak. Root cause: the pod inherited the systemd-era 1024 soft
        default and had never been load-tested above 14k sessions. Fix: `LimitNOFILE=65536` in the
        pod spec, a dashboard panel on `ls /proc/1/fd | wc -l` against the limit, and an alert at
        70% — the metric nobody had. `[INCIDENT]` `[DIAG]` `[CALC]`

*(14 leaves)*

---

## §1.17 Files, inodes, the VFS, links and the dentry cache

1.17.1 An **inode** holds everything about a file *except its name*: mode bits and file type,
       `uid`/`gid`, size in bytes, block/extent map, link count (`i_nlink`), and the three
       timestamps `atime`/`mtime`/`ctime`. The name lives in a **directory entry**, which is
       nothing but a `(name → inode number)` pair. `ls -i` and `stat` prove it. `[PROVE]` `[DIAG]`
1.17.2 A directory is therefore a *file whose contents are a name-to-inode table*. This single fact
       explains hard links, rename atomicity, and why `mv` within a filesystem is O(1) while `mv`
       across filesystems is a copy plus a delete. `[PROVE]`
1.17.3 **Hard link vs symlink**, as a table: a hard link is another directory entry pointing at the
       same inode (same `st_ino`, `i_nlink` incremented, cannot cross filesystems, cannot target a
       directory); a symlink is a *distinct inode whose data is a path string* (crosses
       filesystems, can dangle, `lstat` vs `stat` see different things). `[TABLE]` `[NUM]`
1.17.4 **`unlink(2)` removes a name, not a file.** `int unlink(const char *pathname)` decrements
       `i_nlink`; the inode and its blocks are freed only when `i_nlink == 0` **and** no process
       holds an open descriptor. This is the mechanism behind the `df`/`du` divergence in §1.19.
       `[SYSCALL]` `[PROVE]` `[X-REF 11]`
1.17.5 The four VFS objects the kernel actually manipulates: `struct super_block` (a mounted
       filesystem), `struct inode` (a file), `struct dentry` (a name→inode binding), `struct file`
       (an *open* file — offset, flags, and a pointer to `file_operations`). An fd indexes into the
       process's fd table, which points at a `struct file`; two fds can share one `struct file`
       (after `dup`) and therefore share the file offset. `[SOURCE]` `[PROVE]`
1.17.6 The **dentry cache** and inode cache live in the slab allocator and are reclaimable, which
       is why they appear under `Slab`/`SReclaimable` in `/proc/meminfo` and can be tens of GB on a
       box that walks many paths. `vm.vfs_cache_pressure` default **100**; lowering it makes the
       kernel prefer keeping dentries over page cache. Observe with `slabtop -o` and
       `/proc/sys/fs/dentry-state`. `[SYSCTL]` `[PROC]` `[RESEARCH: Documentation/admin-guide/sysctl/vm.rst]`
1.17.7 **Path resolution** walks one component at a time, checking `x` (search) permission on each
       directory, following mount points and symlinks (max 40 links, `ELOOP` beyond).
       `openat(2)`'s `dirfd` + `AT_FDCWD`, and `O_PATH` for "a handle to a path without opening
       it", are how you avoid TOCTOU races in that walk. `[SYSCALL]` `[TRAP]`
1.17.8 **`atime` is a write on every read.** Modern distributions mount with `relatime`, which
       updates `atime` only if the old value is older than `mtime`/`ctime` or more than 24 hours
       stale; `noatime` disables it entirely. On the `DocumentVerification` document store — 24k
       uploads/day, cold after 90 days — `noatime` removes a metadata write per read. `[NUM]`
       `[SYSCTL]`
1.17.9 `statx(2)` is the modern `stat`:
       `int statx(int dirfd, const char *path, int flags, unsigned mask, struct statx *buf)`. It is
       the only interface that returns **`btime`** (creation time, `STATX_BTIME`) and, since 6.1,
       `STATX_DIOALIGN` for `O_DIRECT` alignment (§1.18). `stat(2)` has no birth time at all.
       `[SYSCALL]` `[VERSION-TRAP]`
1.17.10 **File locking is advisory, and there are two incompatible families.** `flock(2)` locks the
        *open file* (shared across `dup`, not across `fork`-independent opens, whole-file only);
        `fcntl(F_SETLK)` POSIX record locks are per-process, byte-range, and released by closing
        *any* fd on the file. Java's `FileChannel.lock()` maps to the `fcntl` family, which is why
        two `FileLock`s inside one JVM throw `OverlappingFileLockException` rather than blocking.
        `[SYSCALL]` `[API]` `[TRAP]`
1.17.11 `inotify` as the fd-based file-watch mechanism (`inotify_init1`, `inotify_add_watch`) and its
        per-user ceiling `fs.inotify.max_user_watches` — a **memory-derived default** on 6.x, not
        the historical fixed 8192, which is why "too many open files" from a file-watching library
        surprises people. Each watch is charged against the limit and each instance is an fd.
        `[SYSCTL]` `[VERSION-TRAP]` `[RESEARCH: man 7 inotify, "/proc interfaces"]`
1.17.12 Java's file surface, stated exactly: `java.nio.file.Files` +
        `Path`, `Files.createLink` / `createSymbolicLink`,
        `Files.readAttributes(p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS)`,
        `Files.move(src, dst, ATOMIC_MOVE)` (which only works within one filesystem, for exactly
        the reason in 1.17.2), and `Files.newDirectoryStream` — a **closeable** resource whose leak
        is a classic fd leak. `[API]` `[TRAP]`
1.17.13 `[INCIDENT]` `DocumentVerification` stopped accepting uploads with
        `java.nio.file.FileSystemException: /tmp/…: No space left on device` while `df -h /tmp`
        showed 38% used. **Diagnosis:** `df -i /tmp` showed 100% inodes. **Root cause:**
        `Files.createTempFile` per uploaded image, 24k/day, with deletion only on the happy path —
        two years of 2–6 MB stubs the rotation script had truncated but never unlinked, so the
        directory entries (and inodes) survived. **Fix:** `DELETE_ON_CLOSE` in a
        try-with-resources, plus a `tmpfiles.d` age policy. `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.18 File I/O: the syscalls, the three layers of buffering, `fsync` and `O_DIRECT`

1.18.1 The core signatures, stated exactly: `int open(const char *path, int flags, mode_t mode)`,
       `ssize_t read(int fd, void *buf, size_t n)`, `ssize_t write(int fd, const void *buf, size_t n)`,
       `off_t lseek(int fd, off_t off, int whence)`, and the offset-explicit
       `pread`/`pwrite` which do **not** touch the shared file offset and are therefore the only
       safe form when descriptors are shared across threads. `[SYSCALL]` `[API]`
1.18.2 **`write()` may write less than you asked.** A short write is not an error; the contract is
       "0 ≤ returned ≤ n". Every correct writer loops. Likewise `read()` returning 4 KB from a
       requested 64 KB says nothing about EOF — only `0` does. `[TRAP]` `[PROVE]`
1.18.3 **The three layers of buffering, named separately, because "flush" means a different thing
       at each.** (1) *Userspace*: `BufferedOutputStream` / stdio, drained by `flush()`. (2) *Kernel
       page cache*: dirty pages, drained by writeback or `fsync`. (3) *Device write cache*: drained
       by a `FUA`/flush command the kernel issues as part of `fsync`. `flush()` moves bytes from (1)
       to (2) and gives you **no durability at all**. `[FLOW]` `[TRAP]`
1.18.4 `int fsync(int fd)` forces data **and** metadata for one file to stable storage;
       `int fdatasync(int fd)` skips metadata not needed to retrieve the data (it still writes a
       size change, it skips an `mtime` change). Java: `FileChannel.force(boolean metaData)` — the
       boolean *is* the `fsync`/`fdatasync` choice — and `FileDescriptor.sync()`. `[SYSCALL]` `[API]`
1.18.5 **`fsync` reports an I/O error once, to one descriptor, and then forgets.** Since the
       `errseq_t` rework (4.13) the error is reported to every fd open *at the time of the failure*
       exactly once; a process that opens the file afterwards sees success on a file whose data was
       never written. Treat `EIO` from `force()` as data loss, not as a retryable error. `[PROVE]`
       `[VERSION-TRAP]` `[RESEARCH: LWN "PostgreSQL's fsync() surprise"]`
1.18.6 The writeback tunables and their defaults, because they set how much unwritten data a power
       loss destroys: `vm.dirty_background_ratio` **10** (% of available memory at which background
       writeback starts), `vm.dirty_ratio` **20** (at which the *writer* is throttled synchronously),
       `vm.dirty_expire_centisecs` **3000** (30 s), `vm.dirty_writeback_centisecs` **500** (5 s
       flusher wakeup). The `_bytes` variants override the ratios and are what you use on a
       large-memory box. `[SYSCTL]` `[NUM]` `[CALC]`
1.18.7 **`O_DIRECT` bypasses the page cache** and imposes alignment on the buffer address, the file
       offset and the length — historically 512 bytes or the logical block size, now discoverable
       properly via `statx(STATX_DIOALIGN)`'s `stx_dio_mem_align` / `stx_dio_offset_align` (6.1+).
       Misaligned `O_DIRECT` I/O fails with `EINVAL`, silently falls back, or corrupts, depending on
       the filesystem. `[SYSCALL]` `[VERSION-TRAP]` `[TRAP]`
1.18.8 `O_SYNC` (every write implies `fsync`) vs `O_DSYNC` (implies `fdatasync`) vs `O_APPEND`
       (offset positioning and write are atomic with respect to other writers on the same file —
       the property that makes concurrent appends to one log file safe on a local filesystem and
       unsafe on NFS). `[SYSCALL]` `[TABLE]`
1.18.9 In Java, direct I/O is **not** in `StandardOpenOption`: it is
       `com.sun.nio.file.ExtendedOpenOption.DIRECT` (Java 10+), and it requires you to align the
       `ByteBuffer` yourself — `ByteBuffer.allocateDirect(n)` gives you 8-byte alignment, not
       block alignment. This is why almost no JVM service uses `O_DIRECT` and why the ledger relies
       on `fsync` + group commit instead. `[API]` `[VERSION-TRAP]`
1.18.10 `mmap(2)` as the fourth way to do file I/O: `MAP_SHARED` vs `MAP_PRIVATE`, page-fault-driven
        population, `msync` for durability, and the JVM's `MappedByteBuffer`. Its two standing
        problems: an unmapped region cannot be reliably freed before GC (mitigated in Java 21+ by
        `Arena` + `FileChannel.map(mode, off, size, arena)` in the FFM API), and an I/O error
        surfaces as `SIGBUS`, not an exception. `[API]` `[TRAP]`
1.18.11 Zero-copy: `sendfile(2)`, `splice(2)`, `copy_file_range(2)`, and `FileChannel.transferTo` —
        the payload never enters user space, which removes two copies and the userspace buffer.
        Relevant to serving the 2–6 MB `DocumentVerification` images and to `BankWithdrawal`'s 1.8k
        record payout files. `[SYSCALL]` `[API]`
1.18.12 Cache-management hints: `posix_fadvise(fd, off, len, POSIX_FADV_SEQUENTIAL |
        POSIX_FADV_DONTNEED | POSIX_FADV_RANDOM)` and `readahead(2)`. `POSIX_FADV_DONTNEED` after
        streaming a 68 GB/day document batch is the standard way to stop a bulk job evicting the
        ledger's hot page cache. `[SYSCALL]` `[NUM]`
1.18.13 `io_uring` in three syscalls — `io_uring_setup`, `io_uring_enter`, `io_uring_register` — with
        a shared submission and completion ring, so a batch of I/O costs one syscall or none
        (`SQPOLL`). It is the first Linux interface that is asynchronous for **regular files**, not
        only sockets. No JDK API exposes it as of Java 21/25. `[SYSCALL]` `[VERSION-TRAP]`
1.18.14 `[INCIDENT]` `[CALC]` `ApplicationHistory` lost 4 minutes of transition records after a host
        failure, despite "flushing after every write". **Diagnosis:** the writer called
        `BufferedWriter.flush()` and never `FileChannel.force()`; the records sat in dirty page cache
        under `vm.dirty_expire_centisecs=3000`. **Root cause:** confusing layer (1) with layer (2)
        of 1.18.3. **Fix:** `fdatasync` per batch, not per record — at 2.6M records/day and ~400
        bytes each that is 30/sec sustained; one `fsync` per record at ~1 ms each would cap the
        writer at 1,000/sec, so the correct answer is **group commit**: batch 100 records, one
        `force(false)`, 30 syncs/minute. `[INCIDENT]` `[CALC]`

*(14 leaves)*

## §1.19 File systems in practice: ext4 and XFS, journalling, block size, alignment, `df` vs `du`

1.19.1 **ext4 vs XFS**, as a decision table: ext4 (fixed inode count set at `mkfs`, extents,
       delayed allocation, shrinkable, `data=ordered` default journal mode, better on small
       filesystems and small files) vs XFS (dynamic inode allocation, allocation groups, extremely
       good parallel-write and large-file behaviour, **cannot be shrunk**, the default root
       filesystem on Amazon Linux 2023 and RHEL 8+). `[TABLE]`
1.19.2 The **three ext4 journal modes** and exactly what each guarantees: `data=journal` (data and
       metadata both journalled — slowest, safest), `data=ordered` (**default** — metadata
       journalled, data forced to disk *before* the metadata commit, so you never see metadata
       pointing at stale blocks), `data=writeback` (metadata only, no ordering — a crash can expose
       another file's old contents in your file). Read it with `tune2fs -l /dev/nvme0n1p1 |
       grep -i 'default mount'`. `[TABLE]` `[PROVE]` `[DIAG]`
1.19.3 A journal makes *metadata* consistent after a crash; it does **not** make your application
       data durable and it does not replace `fsync`. `fsck` after an unclean shutdown replays the
       journal rather than walking the whole tree — that is the entire point, and it is why a 1 TB
       volume mounts in seconds. `[PROVE]` `[TRAP]`
1.19.4 **Block size 4096 bytes** is the default and is fixed at `mkfs` time (`tune2fs -l | grep
       'Block size'`). A 180-byte ledger row is not the unit of storage; a 400-byte
       `ApplicationHistory` record occupies a full 4 KiB block unless the filesystem inlines it.
       `[NUM]` `[CALC]`
1.19.5 **Inode count is fixed at `mkfs` for ext4** and derives from the `inode_ratio` in
       `/etc/mke2fs.conf` — **16384 bytes per inode** for the `default` type, so a 100 GiB
       filesystem gets roughly 6.5M inodes. You can exhaust them with millions of tiny files while
       `df -h` reports free space, and `No space left on device` with 40% free is *always* a
       `df -i` question. XFS allocates inodes dynamically and does not have this failure mode.
       `[NUM]` `[CALC]` `[TRAP]` `[RESEARCH: man 5 mke2fs.conf]`
1.19.6 The **5% reserved-block default**: `mke2fs` reserves 5% of blocks for uid 0
       (`tune2fs -m <pct>`, visible as `Reserved block count` in `tune2fs -l`). Consequences worth
       stating: `df` counts them as used-capacity headroom so a "100% full" filesystem still lets
       root write; and on a 1 TB data volume 5% is **50 GB** of storage you are paying for and
       cannot use — the standard `-m 0` or `-m 1` change on a non-root data volume. `[NUM]`
       `[SYSCTL]`
1.19.7 **`df` and `du` disagree for exactly two reasons**, and you must distinguish them. (a)
       Reserved blocks and metadata: `df` asks the filesystem's own accounting, `du` walks the tree
       and sums file sizes. (b) **A deleted-but-still-open file**: the directory entry is gone so
       `du` cannot see it, but `i_nlink == 0` with an open fd means the blocks are not freed, so
       `df` still counts them (§1.17.4). `[PROVE]` `[TABLE]`
1.19.8 `lsof +L1` lists open files with a link count below 1 — the one command that finds case (b).
       The `NLINK` column reads `0` and the `NAME` column shows the path with `(deleted)`. The fix
       is to make the holder reopen (`SIGHUP` on a well-behaved daemon, `copytruncate` in
       `logrotate`, or a restart); `rm` cannot help you because there is nothing left to remove.
       `[DIAG]` `[TRAP]`
1.19.9 `df -h` / `df -i` / `df -hT` (with type) / `findmnt` / `lsblk -f`, and `du -sh dir`,
       `du -xh --max-depth=2 /var | sort -h | tail -20` — where `-x` is the flag that stops you
       walking into a mounted volume and misattributing its contents. `[DIAG]`
1.19.10 **Alignment**, because a misaligned write becomes a read-modify-write. Partitions start at
        1 MiB (2048 sectors) by default in modern `parted`/`sfdisk` precisely so that every 4 KiB
        filesystem block lands on a device boundary. On RAID/striped storage, `mkfs.xfs -d
        su=,sw=` and `mkfs.ext4 -E stride=,stripe_width=` must match the array geometry. On EBS,
        I/O is metered in **16 KiB units for gp2/gp3** (larger sequential I/Os are merged up to
        256 KiB), so 4 KiB random writes cost you the same IOPS as 16 KiB ones — batch them.
        `[NUM]` `[CALC]` `[RESEARCH: AWS EBS volume-types documentation, "I/O size"]`
1.19.11 Mount options that matter in production: `noatime` (§1.17.8), `errors=remount-ro` (the ext4
        default — a filesystem error silently makes your data volume read-only, and your service
        starts throwing `IOException` on every write with the disk looking healthy), `discard` vs a
        periodic `fstrim.timer` (prefer the timer; inline discard adds latency to every delete),
        and `nobarrier`, which you should never set on anything holding money. `[SYSCTL]` `[TRAP]`
1.19.12 **Container filesystems are a different animal.** The writable layer is `overlayfs`:
        modifying a file in a lower layer triggers a **copy-up** of the whole file, so a 2–6 MB
        document image edited in place costs a full copy, and `df` inside the container reports the
        overlay, not the host volume. Anything with real write volume belongs on a mounted volume,
        not the container layer. `[X-REF 19]` `[TRAP]`
1.19.13 `[INCIDENT]` `BankDeposits` failed its 06:00 statement-feed ingestion with
        `java.io.IOException: No space left on device` on a volume `df -h` reported at 61%.
        **Diagnosis:** `df -i` was fine; `du -xh --max-depth=1 /var` summed to 40 GB against `df`'s
        historical 210 GB used. `lsof +L1` showed the previous day's 500k-record month-end file
        held open by the ingestion JVM with `NLINK 0`. **Root cause:** the cleanup step `rm`'d the
        file while a `Files.lines` stream from a failed parse was still open, so 170 GB of deleted
        files accumulated across three weeks of failures. **Fix:** try-with-resources on the stream
        (which also fixed a matching fd leak, §1.16), plus a `+L1` check in the box health script.
        `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.20 Disks and the block layer: I/O schedulers, queue depth, readahead, EBS

1.20.1 The request path, top to bottom, as an ordered trace: syscall → page cache → filesystem
       (extent lookup) → `struct bio` → **blk-mq** software queue → I/O scheduler → hardware
       dispatch queue → driver → device → interrupt/completion → `bio_endio` → page marked clean.
       Every latency number in `iostat` is measured on a *segment* of this path, which is why they
       do not add up naively. `[FLOW]`
1.20.2 **blk-mq is the only block layer that exists now** — the legacy single-queue request path was
       removed in 5.0. It gives one software queue per CPU and *n* hardware queues, which removes
       the single per-device lock and is the reason `%util` stopped meaning what it used to mean
       (1.20.6). `[VERSION-TRAP]` `[PROVE]`
1.20.3 The schedulers, and when each is right: **`none`** (pure FIFO, no reordering — the default
       and correct choice for NVMe, where the device reorders better than you can),
       **`mq-deadline`** (deadline-based, read-preferring, the usual default for SATA/virtio),
       **`kyber`** (latency-target-based, for fast multi-queue devices), **`bfq`** (proportional
       fairness, good for desktops and interactive workloads, meaningful CPU overhead). Read and
       set via `cat /sys/block/nvme0n1/queue/scheduler` — the current one is in brackets.
       `[PROC]` `[TABLE]` `[RESEARCH: Documentation/block/ and Documentation/admin-guide/]`
1.20.4 The queue knobs under `/sys/block/<dev>/queue/`: `nr_requests` (per-queue request depth),
       `read_ahead_kb` (**128** by default — the kernel reads 128 KiB ahead on a detected
       sequential pattern), `rotational` (0 for SSD/NVMe; drives scheduler and merge heuristics),
       `nomerges` (**0**, merges enabled), `max_sectors_kb`, `rq_affinity`. Raising
       `read_ahead_kb` helps a sequential scan and *hurts* a random-read workload by evicting
       useful page cache. `[PROC]` `[SYSCTL]` `[NUM]` `[RESEARCH: Documentation/block/queue-sysfs.rst]`
1.20.5 **`iostat -x 1`, field by field** — the single most misread output in Linux
       diagnostics: `r/s`,`w/s` (IOPS), `rkB/s`,`wkB/s` (throughput), `rrqm/s`,`%rrqm` (merges —
       high merge rates mean your application is issuing I/O too small), `r_await`,`w_await` (mean
       ms per request **including queue time** — the latency your code actually experiences),
       `rareq-sz`,`wareq-sz` (mean request size in KiB), `aqu-sz` (mean queue length), `%util`.
       `[DIAG]` `[TABLE]`
1.20.6 **`%util` is not saturation on a multi-queue device.** It measures the fraction of wall time
       with *at least one* request in flight. An NVMe device that services 64 concurrent requests
       can report `%util 100.00` at 5% of its capability. On a single-queue spinning disk it did
       mean saturation; on NVMe or EBS it means "busy", full stop. Use `await` against your latency
       budget and `aqu-sz` against the device's queue depth instead. `[TRAP]` `[PROVE]`
1.20.7 `[CALC]` **`await` and `aqu-sz` are linked by Little's law**: `aqu-sz ≈ (r/s + w/s) × await
       (seconds)`. So 2,000 IOPS at 4 ms `await` gives `aqu-sz ≈ 8`. That identity is your
       cross-check: an `aqu-sz` of 30 with `await` of 2 ms and 500 IOPS is inconsistent and means
       you are reading a bursty average. It also tells you which lever you have — `await` rising
       with `aqu-sz` flat is the *device* slowing down; both rising together is *you* issuing more.
       `[CALC]` `[PROVE]`
1.20.8 Queue depth is the throughput-versus-latency dial: deeper queues let the device coalesce and
       parallelise (higher IOPS) at the cost of per-request latency. This is exactly the trade you
       make when sizing a JDBC pool in front of `FundsLedger` — a pool larger than the device can
       serve concurrently converts device queueing into application-visible p99. `[PROVE]`
       `[X-REF 09]`
1.20.9 **EBS is a network device wearing a block device's clothes**, and its numbers are contractual
       rather than physical: `gp3` gives a baseline **3,000 IOPS and 125 MiB/s** at any size, with
       provisioning up to **16,000 IOPS and 1,000 MiB/s**; `gp2` gives **3 IOPS per GiB** with a
       burst bucket that empties; `io2 Block Express` goes to 256,000 IOPS. Single-digit-millisecond
       `await` is *normal* for EBS and would be pathological for local NVMe. `[NUM]`
       `[RESEARCH: AWS EBS volume-types documentation]`
1.20.10 The ceiling you forget: the **instance's** EBS bandwidth cap, which is per instance type and
        is independent of the volume's provisioning. Attaching three 16,000-IOPS volumes to an
        instance capped at 20,000 does not give you 48,000, and `iostat` on the volume will look
        innocent while the instance-level limit does the throttling. Watch it in CloudWatch, not on
        the box. `[TRAP]` `[X-REF 18]`
1.20.11 `[PROC]` Where the truth is: `/sys/block/<dev>/queue/*` for configuration,
        `/proc/diskstats` for the raw counters `iostat` derives everything from,
        `/sys/block/<dev>/stat`, and `lsblk -o NAME,ROTA,SCHED,RQ-SIZE,MOUNTPOINT` as the one-line
        summary. `nvme list` and `nvme smart-log` for device health. `[PROC]` `[DIAG]`
1.20.12 Per-process attribution, since `iostat` is per-device: `pidstat -d 1` (kB_rd/s, kB_wr/s per
        process), `iotop -o`, `/proc/<pid>/io` (`read_bytes`/`write_bytes` count actual block
        layer traffic; `rchar`/`wchar` count syscall bytes, which include page-cache hits — the
        difference between the two pairs *is* your cache hit rate). `biolatency` and `biosnoop`
        from bcc when you need a histogram rather than a mean. `[DIAG]` `[PROC]`
1.20.13 **`D`-state is the block layer's signature.** Processes in uninterruptible sleep
        (`ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'`) are blocked inside the kernel on I/O and
        cannot be killed even with `SIGKILL`; they also count toward load average, so a load of 40
        on an idle-CPU box is a storage incident, not a compute one. `[X-REF 11]` `[TRAP]`
1.20.14 `[INCIDENT]` `FundsLedger` p99 on stake reservation went from 40 ms to 900 ms at 19:00 on a
        match night, holding for 40 minutes then recovering by itself. **Diagnosis:** `top` showed
        68% `wa` with CPUs idle; `iostat -x 1` showed `w_await` at 220 ms with only 3,100 write
        IOPS and `%util` pinned at 100; `aqu-sz` of 680 confirmed by Little's law. The volume was
        `gp2`, 900 GiB, so baseline was 2,700 IOPS. **Root cause:** the 3,400/sec settlement burst
        (13,600 ledger writes/sec peak) drained the gp2 burst-credit bucket; `BurstBalance` in
        CloudWatch hit 0 exactly when latency broke. **Fix:** migrate to `gp3` with provisioned
        16,000 IOPS and group-commit the settlement batch (§1.18.14) so the same work costs fewer,
        larger I/Os. This was a billing decision presenting as a latency incident. `[INCIDENT]`
        `[DIAG]` `[CALC]`

*(14 leaves)*

## §1.21 The four I/O models: blocking, non-blocking, multiplexed, asynchronous

1.21.1 The four models defined precisely, in one table: **blocking** (thread sleeps in the syscall
       until data moves), **non-blocking** (syscall returns `EAGAIN`/`EWOULDBLOCK` immediately, you
       retry), **multiplexed** (one thread asks the kernel *which of these fds are ready*, then does
       a non-blocking transfer), **asynchronous** (you hand the kernel a buffer and an operation and
       are told later that it is *finished*). `[TABLE]`
1.21.2 **The axis that actually matters is readiness versus completion.** `select`/`poll`/`epoll`
       and `kqueue` report *readiness* — you still perform the copy on your own thread. `io_uring`
       and Windows IOCP report *completion* — the kernel did the copy. Everything else about these
       APIs is detail; this distinction determines whether your event thread can ever block.
       `[PROVE]`
1.21.3 `[CALC]` **The blocking model's cost is arithmetic, not opinion.** QuizStakes peaks at
       **55k concurrent sessions**. One platform thread per connection at the JVM's ~1 MB
       `-Xss` reservation is **55 GB of stack reservation**, before heap; `ApplicationGateway` runs
       a 2 GB heap on 12–40 instances. Even ignoring memory, 55k runnable threads on a 4-vCPU box
       is a context-switch machine, not a server (§1.2). `[CALC]` `[NUM]`
1.21.4 **The non-blocking model alone is useless at scale**: without a readiness notifier you must
       poll every fd, so you burn a core to discover that nothing happened. Non-blocking mode is a
       *prerequisite* for models 3 and 4, not a model you deploy on its own. `[PROVE]` `[TRAP]`
1.21.5 **POSIX AIO (`aio_read`/`aio_write`) is not kernel asynchrony**: glibc implements it with a
       userspace thread pool. And the kernel's own `io_submit`/`libaio` path only behaves
       asynchronously for `O_DIRECT` — on buffered I/O it silently blocks. Two decades of "Linux
       has async file I/O" claims were wrong until `io_uring`. `[VERSION-TRAP]` `[TRAP]`
1.21.6 `io_uring` as the first genuinely asynchronous, genuinely general Linux I/O interface —
       completion-based, batched, works on regular files, sockets, `timeout`s and `poll` uniformly
       (§1.18.13). Its adoption story is the honest caveat: it has been a recurring source of CVEs
       and is disabled by policy in some hardened environments and container runtimes.
       `[RESEARCH: LWN io_uring coverage]`
1.21.7 The two server architectures these models produce: **thread-per-request** (simple, readable
       stack traces, blocking calls fine, bounded by thread count) versus **event loop**
       (`n_cores` threads, non-blocking everything, one blocking call anywhere stalls every
       connection on that loop). Tomcat's default connector vs Netty is exactly this choice.
       `[TABLE]`
1.21.8 The Java mapping, with exact types: blocking = `InputStream`/`OutputStream`,
       `Socket`, and `FileChannel`; non-blocking + multiplexed =
       `SocketChannel.configureBlocking(false)` + `Selector` + `SelectionKey`; asynchronous =
       `AsynchronousSocketChannel` / `AsynchronousFileChannel` with a `CompletionHandler`, which on
       Linux is implemented over a thread pool rather than kernel AIO. `[API]`
1.21.9 **Virtual threads make the blocking model viable again**, and this is the most important
       change to this section in a decade. `Thread.ofVirtual()` / `Executors.
       newVirtualThreadPerTaskExecutor()` (Java 21, JEP 444): the continuation unmounts on a
       blocking call, so you write model 1 and get model 3's scalability — a few KB per task
       instead of 1 MB. `[API]` `[NUM]`
1.21.10 `[VERSION-TRAP]` **The pinning caveat that most write-ups still state wrongly.** In Java 21
        a virtual thread blocking inside a `synchronized` block *pins* its carrier thread, so a
        `synchronized` connection pool could starve the scheduler; the standard advice was
        `ReentrantLock`. **JDK 24 (JEP 491) removed that limitation** — `synchronized` no longer
        pins. Native frames and `Object.wait()` still pin. State which JDK you are on before
        repeating either version of the advice. `[VERSION-TRAP]` `[RESEARCH: JEP 491]`
1.21.11 Choosing for a real service: `ClientRestrictions` has a **30 ms p99 budget**, 8 instances,
       extreme request rate and trivial per-request work — a non-blocking edge with pre-warmed
       pooled connections, because a single connection setup would consume the whole budget
       (§1.30). `DocumentVerification` moves 2–6 MB payloads with a p99 vendor latency of 38 s —
       thread-per-request with virtual threads, because the work is a long wait, not a fast loop.
       Same platform, opposite answers. `[PROVE]` `[NUM]`
1.21.12 `[TRAP]` **"Async is faster" is false as stated.** Asynchrony does not reduce the latency of
        one request; it increases the number of concurrent requests one thread can hold. If your
        p99 is dominated by a 900 ms vendor call, moving to an event loop changes nothing about the
        p99 and makes the stack trace unreadable. Async buys *concurrency per thread*; measure
        against that claim, not against latency. `[TRAP]` `[PROVE]`

*(12 leaves)*

## §1.22 `select`, `poll`, `epoll`: the interfaces and why only one of them scales

1.22.1 `int select(int nfds, fd_set *r, fd_set *w, fd_set *e, struct timeval *timeout)`. Its three
       fatal properties: `fd_set` is a **fixed bitmask capped at `FD_SETSIZE` = 1024** (a
       compile-time constant, not a tunable), the sets are **modified in place** so you must rebuild
       them every iteration, and the kernel must scan all `nfds` descriptors on every call.
       `[SYSCALL]` `[NUM]` `[TRAP]`
1.22.2 `int poll(struct pollfd *fds, nfds_t nfds, int timeout)` with
       `struct pollfd { int fd; short events; short revents; }`. It fixes the 1024 limit and the
       destructive-argument problem, but the **entire array is still copied into the kernel and
       scanned on every call** — O(n) per wait, where *n* is total descriptors, not ready ones.
       `[SYSCALL]` `[PROVE]`
1.22.3 `epoll` is three syscalls and a **kernel-resident interest set**: `int epoll_create1(int
       flags)` returns an fd; `int epoll_ctl(int epfd, int op, int fd, struct epoll_event *ev)` with
       `EPOLL_CTL_ADD`/`MOD`/`DEL` registers once; `int epoll_wait(int epfd, struct epoll_event
       *events, int maxevents, int timeout)` returns **only the ready descriptors**. Registration
       cost is paid once, not per wait. `[SYSCALL]` `[PROVE]`
1.22.4 Internally the interest set is a **red-black tree** and readiness is a **linked ready list**
       populated by the wakeup callback on each file's wait queue. So `epoll_wait` is O(number
       ready), not O(number watched) — that, and nothing else, is why it scales. `[SOURCE]`
       `[PROVE]`
1.22.5 `[CALC]` The scaling arithmetic on QuizStakes' 55k peak sessions with, say, 50 active at any
       instant: `select` cannot even represent 55k fds; `poll` copies and scans 55,000 `pollfd`
       structs (~660 KB) per wait to find 50; `epoll_wait` returns 50 entries and touches nothing
       else. At 10,000 waits/sec that is the difference between a spare core and 6.6 GB/s of
       pointless memory traffic. `[CALC]` `[NUM]`
1.22.6 **Level-triggered vs edge-triggered.** LT (default) reports "this fd is readable" every call
       until you drain it; ET (`EPOLLET`) reports only the *transition*. ET is faster and requires a
       discipline: you must read in a loop until `EAGAIN`, or you will never be told again and the
       connection hangs forever with data sitting in the socket buffer. `[TRAP]` `[PROVE]`
1.22.7 `EPOLLONESHOT` (disarm after one report; re-arm with `EPOLL_CTL_MOD`) as the way to hand an
       fd to a worker thread without a second thread also picking it up; and **`EPOLLEXCLUSIVE`**
       (Linux 4.5) as the fix for the accept **thundering herd** when many processes `epoll` the
       same listening socket. `[SYSCALL]` `[VERSION-TRAP]`
1.22.8 **epoll registers a `(struct file, fd)` pair, not an fd number.** Close the fd and the
       registration goes; `dup` the fd and the *same* `struct file` is now reachable under two
       numbers, so events keep firing under the original registration. This is the source of the
       classic "I closed it but epoll still reports it" bug in fd-recycling code. `[TRAP]`
       `[PROVE]`
1.22.9 **epoll does not work on regular files.** A regular file is always "ready", so registering
       one either fails with `EPERM` or produces a permanent readiness storm. That is precisely why
       file I/O in an event-loop server needs an offload thread pool or `io_uring`, and why "just
       use NIO" is not an answer for disk. `[TRAP]` `[X-REF 11]`
1.22.10 `epoll_pwait` (atomically swap the signal mask while waiting — closes the race that made the
        self-pipe trick necessary) and **`epoll_pwait2`** (Linux 5.11), which takes a
        `struct timespec` and so gives **nanosecond** timeout resolution instead of
        `epoll_wait`'s milliseconds. `[SYSCALL]` `[VERSION-TRAP]` `[NUM]`
1.22.11 The portability table: `epoll` (Linux), `kqueue` (BSD/macOS — one API for fds, signals,
        timers and vnodes), `IOCP` (Windows — completion, not readiness), `/dev/poll` (Solaris,
        historical). A cross-platform library exists to hide exactly this, which is what Netty's
        `EpollEventLoopGroup` vs `NioEventLoopGroup` is about. `[TABLE]`
1.22.12 The Java mapping, exactly: `Selector.open()` yields `sun.nio.ch.EPollSelectorImpl` on Linux;
        `selector.select()` → `epoll_wait`; **`selectedKeys()` must be cleared by the iterator's
        `remove()`** or the same key is redelivered forever (the single most common NIO bug);
        `Selector.wakeup()` is implemented over an `eventfd`; `SelectionKey.OP_WRITE` is
        level-triggered readiness and registering it permanently produces a 100%-CPU spin.
        `[API]` `[TRAP]`
1.22.13 `[INCIDENT]` An `ApplicationGateway` instance sat at 100% CPU on one core with 200 rps and
        no latency impact, then started dropping connections as traffic rose. **Diagnosis:**
        `top -H` isolated one thread; `printf '%x\n' <tid>` mapped it via `nid=` in `jcmd
        Thread.print` to a Netty event loop; `strace -c -p` showed 1.4M `epoll_wait` calls returning
        instantly. **Root cause:** a custom handler registered `OP_WRITE` and never deregistered
        it; a writable socket is *always* level-triggered ready, so the loop span. **Fix:** register
        `OP_WRITE` only when a write actually returns short, deregister on completion — the standard
        NIO write-interest protocol. `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.23 Signals: the catalogue, delivery, dispositions and handler constraints

1.23.1 The catalogue with the **x86-64 numbers**, because `kill -N` requires them and the numbers
       differ across architectures: `SIGHUP` 1, `SIGINT` 2, `SIGQUIT` 3, `SIGILL` 4, `SIGABRT` 6,
       `SIGBUS` 7, `SIGFPE` 8, `SIGKILL` 9, `SIGUSR1` 10, `SIGSEGV` 11, `SIGUSR2` 12, `SIGPIPE` 13,
       `SIGALRM` 14, `SIGTERM` 15, `SIGCHLD` 17, `SIGCONT` 18, `SIGSTOP` 19, `SIGTSTP` 20.
       `kill -l` prints the local truth. `[TABLE]` `[NUM]`
1.23.2 **Standard signals are not queued.** The pending set is a bitmask, so ten `SIGCHLD`s
       delivered while blocked collapse into one — which is exactly why a `SIGCHLD` handler must
       loop `waitpid(-1, &st, WNOHANG)` until it returns 0 rather than reaping one child.
       **Real-time signals `SIGRTMIN` (34) to `SIGRTMAX` (64) *are* queued** and carry a value.
       `[NUM]` `[PROVE]` `[TRAP]`
1.23.3 The three **dispositions**: default action (terminate, terminate+core, ignore, stop,
       continue — per signal, listed in `man 7 signal`), ignore (`SIG_IGN`), or a handler.
       **`SIGKILL` and `SIGSTOP` can be neither caught, blocked, nor ignored** — that is a kernel
       invariant, not a convention, and it is why `kill -9` is both reliable and destructive.
       `[TABLE]` `[PROVE]`
1.23.4 Delivery mechanics: each *thread* has a pending set and a blocked mask
       (`pthread_sigmask`/`sigprocmask`), and the *process* has a shared pending set. A
       process-directed signal is delivered to **an arbitrary thread that does not block it** —
       which is why libraries dedicate one thread to signal handling and block the signal
       everywhere else. `[PROVE]` `[SYSCALL]`
1.23.5 `int sigaction(int signum, const struct sigaction *act, struct sigaction *old)` is the only
       correct installer; `signal(2)`'s semantics (handler reset, mask behaviour) vary by
       platform. **`SA_RESTART`** decides whether an interrupted slow syscall auto-restarts or
       returns **`EINTR`** — and code that does not handle `EINTR` on `read`, `write`, `accept` or
       `poll` is broken in a way that only appears under signals. `[SYSCALL]` `[TRAP]`
1.23.6 **A handler runs on a borrowed stack in the middle of arbitrary code**, so it may call only
       **async-signal-safe** functions (the enumerated list in `man 7 signal-safety`: `write`,
       `_exit`, `signal`, `kill`, …). Not `malloc`, not `printf`, not anything taking a lock the
       interrupted code might hold — that is a self-deadlock, and it is why "log a message from the
       handler" is a bug. The safe pattern is: set a `volatile sig_atomic_t` flag, or `write` one
       byte to a self-pipe, and return. `[SOURCE]` `[TRAP]`
1.23.7 `signalfd(2)` (and `timerfd`, `eventfd`) as the modern escape: it turns signal delivery into a
       **readable file descriptor**, so signals join your `epoll` set and are handled on a normal
       thread with no safety restrictions. This is the right answer whenever the question is
       "signals in an event loop". `[SYSCALL]` `[X-REF 11]`
1.23.8 **`SIGPIPE`** is delivered when you `write` to a socket or pipe whose peer has closed, and its
       default action **terminates the process**. Every network library therefore ignores it and
       reads the `EPIPE` errno instead — the JVM does this at startup, which is why you see
       `java.io.IOException: Broken pipe` rather than a dead JVM. `[PROVE]` `[API]`
1.23.9 The JVM's own signal usage, which is why `-Xrs` exists: `SIGSEGV` is *used deliberately* for
       implicit null checks and safepoint polling (a segfault is a normal event inside HotSpot);
       `SIGQUIT` (3) triggers a full thread dump to stdout; `SIGBUS` surfaces `mmap` I/O errors
       (§1.18.10); `SIGTERM`/`SIGINT`/`SIGHUP` are consumed by the shutdown-hook machinery. Chaining
       a native handler over the JVM's without `SA_ONSTACK`-aware chaining crashes the VM.
       `[API]` `[TRAP]`
1.23.10 **`kill -3 <java-pid>` is free diagnostics**: a complete thread dump with lock ownership, to
        stdout, with no agent, no JDK on the box and no attach permission. Memorise it. Its
        programmatic cousins are `jcmd <pid> Thread.print` and `jstack <pid>`. `[DIAG]` `[API]`
1.23.11 The Java-side API surface, exactly: `Runtime.getRuntime().addShutdownHook(Thread)`,
        `sun.misc.Signal.handle(new Signal("HUP"), handler)` (unsupported but universally used for
        config reload), `ProcessHandle.destroy()` = `SIGTERM` vs `destroyForcibly()` = `SIGKILL`,
        and `Process.exitValue()` reporting **128 + signal number** — so **143** is `SIGTERM` and
        **137** is `SIGKILL`. `[API]` `[NUM]`
1.23.12 **Shutdown hooks are best-effort cleanup, never a durability mechanism.** They do not run on
        `SIGKILL`, on `Runtime.halt()`, on a JVM crash, or on host loss. Anything whose loss is a
        correctness problem must be committed before the response is sent, not flushed in a hook.
        `[TRAP]` `[X-REF 11]`
1.23.13 `[INCIDENT]` A `BankWithdrawal` `PaymentRun` of 1,800 payout records was submitted twice to
        the banking partner on a Tuesday deploy. **Diagnosis:** the pod's exit code was **137**, not
        143 — `SIGKILL`, so the shutdown hook that marked the run `SUBMITTED` never ran; the file had
        already been accepted by the partner. On restart the leader re-read the run as `APPROVED`
        and resubmitted. **Root cause:** `terminationGracePeriodSeconds: 30` against a 45 s p99 on
        the payout-file call, plus state written *after* the irreversible external effect. **Fix:**
        write the "submitted" intent **before** the call with the idempotency key, raise the grace
        period past the dependency's p99, and never let a signal handler be the thing that records
        an irreversible action. `[INCIDENT]` `[NUM]`

*(13 leaves)*

## §1.24 IPC: pipes, FIFOs, unix sockets, shared memory, `eventfd`, `futex`

1.24.1 `int pipe(int pipefd[2])` — a unidirectional in-kernel byte queue: `pipefd[0]` read end,
       `pipefd[1]` write end. Default capacity **65,536 bytes (16 pages)**, adjustable per pipe with
       `fcntl(fd, F_SETPIPE_SZ, n)` up to `fs.pipe-max-size` (default **1,048,576**) for unprivileged
       users. A full pipe blocks the writer; that back-pressure is the feature.
       `[SYSCALL]` `[SYSCTL]` `[NUM]`
1.24.2 **`PIPE_BUF` is 4096 bytes on Linux** and it is the atomicity boundary: a write of ≤ 4096
       bytes to a pipe will not be interleaved with another writer's; a larger write may be. This is
       the entire reason multi-process logging to one pipe produces mangled lines above 4 KB.
       `[NUM]` `[PROVE]` `[TRAP]`
1.24.3 The two pipe end-of-life rules, which people invert: writing when **all read ends** are
       closed raises `SIGPIPE`/`EPIPE`; reading when **all write ends** are closed returns 0 (EOF).
       A forgotten inherited write end in a forked child is why a reader hangs forever waiting for
       an EOF that never comes. `[TRAP]` `[PROVE]`
1.24.4 **FIFOs** (`mkfifo(1)` / `mkfifo(3)`) are pipes with a filesystem name and an inode, usable
       between unrelated processes. `open` for reading blocks until a writer appears (and vice
       versa) unless `O_NONBLOCK` — a startup-ordering hazard people rediscover every time.
       `[SYSCALL]` `[TRAP]`
1.24.5 **Unix domain sockets** are the general-purpose local IPC: `AF_UNIX` with `SOCK_STREAM`,
       `SOCK_DGRAM` (reliable and ordered locally, unlike UDP) or `SOCK_SEQPACKET`. Two Linux-only
       superpowers: `SO_PEERCRED`/`SO_PEERSEC` gives you the peer's authenticated uid/gid/pid — real
       authentication with no protocol — and `SCM_RIGHTS` over `sendmsg` **passes an open file
       descriptor** to another process. The abstract namespace (a leading NUL, conventionally shown
       as `@name`) avoids filesystem permissions entirely, which is a hazard as often as a
       convenience. `[SYSCALL]` `[PROVE]`
1.24.6 Unix socket vs TCP loopback for a sidecar hop: the unix socket skips the whole IP/TCP stack,
       has no port, no `TIME_WAIT`, no ephemeral-port exhaustion, and is authenticated by file
       permissions. Measurably lower latency and CPU per message. `RouterInt` as a sidecar proxy is
       exactly this case. `[PROVE]` `[X-REF 10]`
1.24.7 **POSIX shared memory** is the fastest IPC because after setup there is no syscall at all:
       `shm_open(name, O_CREAT|O_RDWR, 0600)` → `ftruncate` → `mmap(MAP_SHARED)`. It lives in
       `/dev/shm`, a `tmpfs` whose default size is **50% of RAM** on a normal host. You now own
       synchronisation yourself — a shared-memory region without a memory model is a data-race
       generator. `[SYSCALL]` `[NUM]`
1.24.8 **The container trap on `/dev/shm`:** Docker/containerd default it to **64 MB**, not 50% of
       RAM, and Kubernetes gives you an `emptyDir` with `medium: Memory` (counted against the pod's
       memory limit) if you want more. Anything using shared memory or a large `tmpfs` scratch area
       breaks in a container and works on a VM for this one reason. `[NUM]` `[TRAP]` `[X-REF 19]`
1.24.9 **System V IPC** (`shmget`/`semget`/`msgget`, `ipcs`, `ipcrm`) as the legacy family worth
       recognising rather than choosing: global integer keys that collide, objects that **survive
       process exit** and leak until `ipcrm`, and system-wide limits in
       `kernel.shmmax`/`shmall`/`sem`. Prefer the POSIX equivalents in new code. `[SYSCALL]`
       `[SYSCTL]`
1.24.10 `int eventfd(unsigned initval, int flags)` — a kernel counter behind an fd. Write adds,
        read returns and zeroes (or with `EFD_SEMAPHORE`, decrements by one). It is the cheapest
        possible "wake up my event loop" primitive, `epoll`-able, and it is what the JVM's
        `Selector.wakeup()` uses on Linux. `[SYSCALL]` `[API]`
1.24.11 **`futex(2)` is the primitive under every userspace lock**, and its design point is that the
        **uncontended case never enters the kernel**: `long syscall(SYS_futex, uint32_t *uaddr, int
        op, uint32_t val, ...)`. A compare-and-swap on a userspace word takes the lock; only on
        contention does `FUTEX_WAIT` park the thread and `FUTEX_WAKE` release it. `pthread_mutex`,
        `LockSupport.park`/`unpark`, and therefore every `ReentrantLock` and every `synchronized`
        inflation, bottoms out here. `futex_waitv` (5.16) adds waiting on multiple futexes at once.
        `[SYSCALL]` `[PROVE]` `[X-REF 06]`
1.24.12 The Java surface for local IPC: `SocketChannel.open(StandardProtocolFamily.UNIX)` with
        `UnixDomainSocketAddress` (Java 16+), `MemorySegment` +
        `FileChannel.map(READ_WRITE, 0, size, arena)` for shared memory via the FFM API (Java 21),
        `ProcessBuilder` with `Redirect.PIPE`/`INHERIT` for pipes, and `LockSupport.park` for the
        futex path. `[API]` `[VERSION-TRAP]`
1.24.13 `[INCIDENT]` `DocumentVerification` began failing image extraction with
        `java.io.IOException: No space left on device` on `/dev/shm` after a lift-and-shift from EC2
        to EKS. **Diagnosis:** `df -h /dev/shm` inside the pod reported **64 MB total**; the same
        JVM on EC2 saw 15 GB. The native extraction library staged each 2–6 MB page there and kept
        up to 16 in flight. **Root cause:** the container runtime's 64 MB `/dev/shm` default
        (1.24.8), which no configuration in the application could reveal. **Fix:** an `emptyDir`
        with `medium: Memory, sizeLimit: 512Mi` mounted at `/dev/shm`, and the size added to the
        pod's memory accounting so it cannot silently cause an OOMKill instead. `[INCIDENT]`
        `[DIAG]`

*(13 leaves)*

## §1.25 Users, groups, file permissions, `setuid` and capabilities

1.25.1 The identity a process carries is **four ids, not one**: real uid (who you are), **effective
       uid (what the kernel checks)**, saved set-uid (what you may switch back to), and filesystem
       uid. `id`, `/proc/<pid>/status`'s `Uid:` line (all four, in that order), and `getuid` vs
       `geteuid`. Privilege dropping is `setresuid`, and doing it in the wrong order leaves the
       saved id able to climb back. `[PROC]` `[SYSCALL]` `[TRAP]`
1.25.2 The account databases, field by field: `/etc/passwd`
       (`name:x:uid:gid:comment:home:shell` — the `x` means the hash moved),
       `/etc/shadow` (hash, last change, min/max age, warn, inactive, expire),
       `/etc/group` (`name:x:gid:members`). A shell of `/usr/sbin/nologin` is how service accounts
       are prevented from logging in. `[TABLE]`
1.25.3 The nine permission bits as three triples (`user`/`group`/`other` × `rwx`) and their octal
       arithmetic: `644` = `rw-r--r--`, `755` = `rwxr-xr-x`, `600` = owner-only. `chmod` symbolic
       vs numeric, `chown user:group`. `[NUM]` `[CALC]`
1.25.4 **On a directory the bits mean something different**, and this is routinely got wrong: `r` =
       list the names, `w` = create/delete/rename entries, **`x` = traverse/resolve through it**.
       Consequence: with `--x` on a directory you can `open` a file whose name you already know but
       cannot `ls`; with `r--` you can list names but `stat` nothing. And **`w` on the directory,
       not on the file, is what lets you delete a file**. `[PROVE]` `[TRAP]`
1.25.5 **`umask` masks bits off at creation.** Default **022** on most distributions, so a file
       created with mode `0666` becomes `644` and a directory `0777` becomes `755`. `umask 077` for
       anything touching PII. It is inherited by children, which is what makes it dangerous in cron
       (§1.26.11). `[NUM]` `[TRAP]`
1.25.6 The three special bits: **setuid `4000`** (run with the file owner's euid — how `passwd`
       edits `/etc/shadow`), **setgid `2000`** (on a file: the group's egid; **on a directory: new
       entries inherit the directory's group**, the mechanism behind shared upload directories), and
       the **sticky bit `1000`** (in a world-writable directory only the owner may delete —
       `/tmp` is `1777`). `ls -l` shows them as `s`/`s`/`t` in the `x` positions. `[NUM]` `[TABLE]`
1.25.7 Two hard limits on setuid that close most of the naive attack surface: **the kernel ignores
       setuid on interpreted scripts**, and it ignores it entirely on a filesystem mounted
       `nosuid`. `find / -perm -4000 -type f` is the audit; the answer on a hardened box should be
       a short, known list. `[TRAP]` `[DIAG]`
1.25.8 **Capabilities split root into ~40 independent privileges**, so you no longer need uid 0 to
       do one privileged thing. The ones that matter to a backend service:
       `CAP_NET_BIND_SERVICE` (bind below port 1024), `CAP_NET_RAW` (raw sockets — what `ping` and
       `tcpdump` need), `CAP_SYS_PTRACE` (attach a debugger, which is what `strace`/`jstack` on
       another process requires), `CAP_KILL`, `CAP_DAC_OVERRIDE` (bypass file permissions), and
       **`CAP_SYS_ADMIN`, which is close enough to root that granting it is not a mitigation**.
       `[TABLE]` `[NUM]`
1.25.9 The five capability sets a process carries — **permitted, effective, inheritable, bounding,
       ambient** — plus a file's permitted/inheritable/effective sets. `getcap`/`setcap
       'cap_net_bind_service=+ep' /usr/bin/java`, `capsh --print`, and
       `/proc/<pid>/status`'s `CapEff:`/`CapBnd:` hex masks. The **ambient** set (Linux 4.3) is what
       finally let capabilities survive a non-setuid `exec`. `[PROC]` `[NUM]`
1.25.10 **`net.ipv4.ip_unprivileged_port_start` (default 1024)** is the simpler alternative to
        `CAP_NET_BIND_SERVICE`: lower it and an unprivileged process may bind port 80 directly. The
        third option — and the one to use — is to bind 8080 and let the load balancer or a
        `NodePort`/`Service` map 443 to it, so the question never arises. `[SYSCTL]` `[NUM]`
1.25.11 Container defaults, stated as they actually are: `runc` drops all but a **small default
        set** of capabilities (`CAP_CHOWN`, `CAP_DAC_OVERRIDE`, `CAP_NET_BIND_SERVICE`,
        `CAP_SETUID`, `CAP_SETGID`, `CAP_KILL`, … — no `CAP_SYS_ADMIN`, no `CAP_NET_RAW` in newer
        defaults), which is why `ping` and `tcpdump` fail inside a container that can otherwise
        reach the network. The hardening set for a QuizStakes pod:
        `securityContext: { runAsNonRoot: true, runAsUser: 10001,
        allowPrivilegeEscalation: false, readOnlyRootFilesystem: true,
        capabilities: { drop: ["ALL"] } }` — `allowPrivilegeEscalation: false` sets the
        `no_new_privs` prctl, which makes setuid binaries inert for the whole process tree.
        `[X-REF 19]` `[RESEARCH: OCI runtime-spec default capability set]`
1.25.12 Beyond the nine bits: **POSIX ACLs** (`getfacl`/`setfacl -m u:deploy:r`, indicated by a
        trailing `+` in `ls -l`) for per-user grants, and **SELinux/AppArmor** as an orthogonal
        layer that can deny an access the permission bits allow — the reason a `Permission denied`
        with correct-looking `ls -l` output means `ausearch -m avc`, not `chmod`. `[DIAG]` `[TRAP]`
1.25.13 The Java surface: `Files.getPosixFilePermissions(path)` /
        `Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-------"))`, and —
        the important one — creating a file *with* the right mode atomically:
        `Files.createFile(p, PosixFilePermissions.asFileAttribute(perms))`. `Files.createTempFile`
        creates `600`; the legacy `File.createTempFile` historically honoured the umask, which is a
        real difference when the file holds PII. `[API]` `[TRAP]`
1.25.14 `[INCIDENT]` A `PersonalDetails` PII extract written nightly to a shared volume was found
        group-readable by every service account on the box. **Diagnosis:** `ls -l` showed `664`;
        the code called `Files.createFile` with no attributes and relied on "the default is 600".
        `[PROC]` `/proc/<pid>/status` confirmed the process ran with a `umask` of **002**, not 022 —
        inherited from the systemd unit's `UMask=002`, set years earlier for a different job.
        **Root cause:** the file mode was `0666 & ~002 = 664`. **Fix:** pass the permissions
        explicitly at creation (1.25.13) rather than depending on inherited process state, plus
        `UMask=0077` on the unit. `[INCIDENT]` `[NUM]`

*(14 leaves)*

## §1.26 Sessions, process groups, controlling terminals, daemons and PID 1

1.26.1 The four-level hierarchy every process sits in: **pid** → **ppid** → **pgid** (process group,
       the unit of job control and of signal fan-out) → **sid** (session, which owns at most one
       controlling terminal). See all of it at once with
       `ps -eo pid,ppid,pgid,sid,tty,stat,comm`. `[PROC]` `[DIAG]`
1.26.2 `pid_t setsid(void)` creates a new session **and** a new process group with the caller as
       leader and **no controlling terminal** — and fails with `EPERM` if the caller is already a
       group leader, which is the entire reason the classic daemon recipe forks first.
       `setpgid(pid, pgid)` moves a process between groups. `[SYSCALL]` `[PROVE]`
1.26.3 The controlling terminal and the **foreground process group**: only the foreground group may
       read from the terminal; a background process that reads gets `SIGTTIN`, one that writes with
       `TOSTOP` set gets `SIGTTOU`, and both **stop** the process — which is why a backgrounded job
       sometimes just freezes with `T` in `ps`. `[TABLE]` `[TRAP]`
1.26.4 **A negative pid means a process group.** `kill(-pgid, sig)` / `kill -TERM -12345` signals
       every member; `kill(-1, sig)` signals everything you may signal. This is how a shell's
       Ctrl-C reaches an entire pipeline, and it is the correct way to terminate a process tree
       whose children you did not track. `[SYSCALL]` `[NUM]`
1.26.5 Hangup semantics: when a terminal disconnects, the kernel sends **`SIGHUP`** to the
       foreground group of that session, whose default action is to terminate. `&` alone does not
       protect you — you need `nohup cmd &` (ignore `SIGHUP`, redirect output to `nohup.out`),
       `setsid cmd` (leave the session entirely), `disown -h` after the fact, or, properly, a
       terminal multiplexer or a systemd unit. `[PROVE]` `[TRAP]`
1.26.6 The classic **double-fork daemonisation** recipe, because you must be able to explain what it
       was for: `fork` (parent exits, child is not a group leader) → `setsid` (new session, no tty) →
       `fork` again (the grandchild can never reacquire a controlling terminal) → `chdir("/")` →
       `umask(0)` → close/reopen fds 0,1,2 on `/dev/null` → write a pidfile. Every step exists to
       detach from something. `[FLOW]` `[PROVE]`
1.26.7 **systemd made all of that obsolete**, and re-implemented it correctly: `Type=simple` (do
       *not* daemonise — stay in the foreground and let the supervisor own you), `Type=notify` with
       `sd_notify(READY=1)` for real readiness, `Type=forking` only for legacy daemons that insist.
       A modern service that daemonises itself under systemd is fighting its supervisor.
       `[VERSION-TRAP]` `[TRAP]`
1.26.8 The unit fields that decide production behaviour, with defaults:
       `ExecStart=`, `Restart=on-failure`, `RestartSec=`, **`LimitNOFILE=`** (the only place the fd
       limit that applies at exec is really set — §1.16), `User=`/`Group=`, `UMask=`,
       `Environment=`/`EnvironmentFile=`, `KillSignal=SIGTERM` (default), **`TimeoutStopSec=90s`
       (default)** after which systemd escalates to `SIGKILL`, `KillMode=control-group` (default —
       signals **every** process in the unit's cgroup, not just the main pid), and
       `OOMPolicy=`. `systemctl cat`, `systemctl show -p TimeoutStopSec` to read the effective
       values. `[SYSCTL]` `[NUM]` `[API]`
1.26.9 **systemd owns the cgroup v2 hierarchy**, so every unit is a cgroup and every resource limit
       is a cgroup file: `systemd-cgls`, `systemd-cgtop`, `systemctl status` printing the unit's
       `CGroup:` path, and `MemoryMax=`/`CPUQuota=` writing `memory.max`/`cpu.max`. This is the
       bridge between §1.26 and the `/sys/fs/cgroup` reading in §1.29. `[PROC]` `[X-REF 11]`
1.26.10 **PID 1 has two obligations nothing else has.** (a) It must **reap orphans** — when any
        process dies its children are reparented to PID 1, and a PID 1 that never calls `wait`
        accumulates zombies until the pid namespace runs out. (b) The kernel **will not deliver an
        unhandled signal to PID 1**: with no installed handler, `SIGTERM` to PID 1 is silently
        discarded. A JVM as PID 1 does install a `SIGTERM` handler, so it works; a shell does not
        forward it, so it does not. Hence the container fixes: exec-form
        `ENTRYPOINT ["java","-jar","app.jar"]`, `exec java …` in a wrapper script, or `--init`/`tini`
        as a real PID 1. `[PROVE]` `[TRAP]` `[X-REF 19]`
1.26.11 **Scheduled work as a daemon-launch mechanism.** cron's five fields
       (`minute hour day-of-month month day-of-week`, so `*/15 * * * *` and `0 2 * * *`),
       `crontab -e`/`-l`, `/etc/cron.d/*` (which take an extra *user* field). Its four standing
       traps: **cron has no environment** — no profile is sourced, `$PATH` is roughly
       `/usr/bin:/bin` and `JAVA_HOME` is unset, so use absolute paths and set variables in the
       crontab; **output goes to mail, i.e. nowhere** — always `>> /var/log/job.log 2>&1`, and
       without the `2>&1` you lose precisely the errors you need (set `MAILTO=""` to stop the mail
       attempt entirely); **overlapping runs** — a 7-minute job on a 5-minute schedule piles up
       until the box dies, so wrap it in `flock -n /var/run/job.lock`; and **timezone/DST**, which
       can skip or double-run a job. systemd timers (`OnCalendar=`, `Persistent=true` to catch up a
       missed run, `RandomizedDelaySec=`) fix the environment and logging problems by construction.
       The distributed version — cron on N replicas runs the job N times — is why
       `BankWithdrawal`'s `PaymentRun` uses a leader-elected scheduler and why **idempotency beats
       every locking scheme**. `[SYSCTL]` `[TRAP]` `[X-REF 14]`
1.26.12 SSH, `scp` and `rsync` are the transport for every diagnostic in §1.30 and are treated in
       full in **§1.33**: key exchange and `authorized_keys`, `~/.ssh/config` with `ProxyJump`, `-L`
       port forwarding, agent forwarding's trust implications, and AWS SSM Session Manager as the
       preferred alternative to an open port 22.
1.26.13 `[INCIDENT]` Every `BankWithdrawal` deploy took exactly 30 seconds longer than every other
        service's and logged nothing on shutdown. **Diagnosis:** `kubectl get pod -o
        jsonpath='{...exitCode}'` returned **137**, and `docker inspect` showed
        `ENTRYPOINT /bin/sh -c "java -jar app.jar"` — shell form. `ps` inside the container showed
        `sh` as PID 1 with the JVM as PID 7. **Root cause:** `sh` neither forwards `SIGTERM` nor has
        a handler for it as PID 1 (1.26.10), so the JVM never learned it was shutting down, sat for
        the full `terminationGracePeriodSeconds: 30`, and was `SIGKILL`ed mid payout-file
        submission — the same failure as §1.23.13, one layer down. **Fix:** exec-form entrypoint,
        verified by `exitCode: 143` and a graceful-shutdown log line on the next deploy.
        `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.27 Time: wall clock vs monotonic, `clock_gettime`, the vDSO, timers and `timerfd`

1.27.1 `int clock_gettime(clockid_t clk_id, struct timespec *tp)` with `struct timespec { time_t
       tv_sec; long tv_nsec; }` — nanosecond *resolution*, not nanosecond *accuracy*. This one
       syscall replaced `time`, `gettimeofday` and `ftime`. `[SYSCALL]` `[API]`
1.27.2 **The clock catalogue, as a table, because picking the wrong `clk_id` is the bug.**
       `CLOCK_REALTIME` (wall clock, settable, **can jump in both directions**),
       `CLOCK_MONOTONIC` (since an arbitrary boot-ish epoch, **never decreases**, NTP-slewed, does
       **not** advance during suspend), `CLOCK_BOOTTIME` (monotonic *including* suspend),
       `CLOCK_MONOTONIC_RAW` (unslewed hardware counter), `CLOCK_TAI` (realtime without leap
       seconds), `CLOCK_PROCESS_CPUTIME_ID` / `CLOCK_THREAD_CPUTIME_ID` (consumed CPU, not elapsed
       time). `[TABLE]` `[NUM]`
1.27.3 **Why `System.currentTimeMillis()` can go backwards and `System.nanoTime()` cannot.**
       `currentTimeMillis` reads `CLOCK_REALTIME`, which `ntpd`/`chrony` may **step** backwards,
       an operator may set, and a hypervisor may correct after a live migration. `nanoTime` reads
       `CLOCK_MONOTONIC`, which the kernel guarantees never decreases. Therefore: **any elapsed-time
       measurement, timeout, retry backoff or rate limiter must use `nanoTime`**, and
       `currentTimeMillis` is only for "what time is it" — a timestamp to display or store.
       `[PROVE]` `[API]` `[TRAP]`
1.27.4 The corollaries of `nanoTime`'s contract that people get wrong: its **absolute value is
       meaningless** (it may be negative, and its epoch differs per boot), it is **not comparable
       across JVMs or hosts**, and only *differences* are defined. Correct form:
       `long t0 = System.nanoTime(); … long ms = (System.nanoTime() - t0) / 1_000_000;` — and
       subtract, never compare with `<`, to survive overflow. `[API]` `[TRAP]`
1.27.5 **The vDSO is why time is cheap.** `clock_gettime` for `CLOCK_REALTIME`/`CLOCK_MONOTONIC` is
       served from a page the kernel maps read-only into every process, so there is **no syscall,
       no mode switch** — roughly **20–30 ns** versus several hundred nanoseconds for a real
       syscall. `ldd /bin/true | grep vdso`, and `/proc/<pid>/maps` shows `[vdso]`. `[PROC]`
       `[NUM]` `[PROVE]`
1.27.6 **The `clocksource` is what the vDSO reads, and it can silently be the slow one.**
       `cat /sys/devices/system/clocksource/clocksource0/current_clocksource` should read **`tsc`**
       (or `kvm-clock`/`xen` on older virtualised hosts); a fallback to **`hpet`** or `acpi_pm`
       costs a device access per read — on the order of **500 ns to 1 µs instead of 20 ns**, a
       25–50× regression. On code that timestamps every log line and every metric, that is a
       visible CPU and latency change with no application deploy behind it.
       `/sys/devices/system/clocksource/clocksource0/available_clocksource` lists the options.
       `[PROC]` `[NUM]` `[INCIDENT]` `[RESEARCH: AWS EC2 "Set the time" / clock source documentation]`
1.27.7 `[CALC]` The arithmetic that makes 1.27.6 concrete: `ClientRestrictions` serves the money
       paths at extreme request rate inside a **30 ms p99** budget. Two timestamps per request
       (entry and exit) at 20 ns is 40 ns of overhead — noise. At 800 ns it is 1.6 µs per request,
       and on a service doing tens of thousands of requests per second per instance that is
       measurable CPU spent asking what time it is. `[CALC]` `[NUM]`
1.27.8 **NTP slews, and only sometimes steps.** `chrony`/`ntpd` correct small offsets by adjusting
       the tick rate (a *slew*, invisible to monotonic ordering) and large ones — beyond a
       configured threshold, classically 128 ms — by **stepping** the clock. `chronyc tracking`
       (System time, Last offset, RMS offset), `chronyc sources -v`, `timedatectl`. An unsynchronised
       or stepping clock breaks log correlation across services long before it breaks anything
       else. `[DIAG]` `[NUM]`
1.27.9 **Leap seconds and smearing.** A positive leap second inserts 23:59:60 into UTC, which POSIX
       `time_t` cannot represent; historical kernels repeated a second, and applications that
       assumed monotonic wall time crashed. The industry answer is **leap smearing** — spreading the
       second over hours so no clock ever repeats or reverses. The **Amazon Time Sync Service at
       `169.254.169.123`** smears; a public NTP pool may not, so mixing sources across a fleet gives
       you hosts that disagree by up to a second during the smear window. `CLOCK_TAI` sidesteps leap
       seconds entirely. `[NUM]` `[RESEARCH: AWS Time Sync / leap-second guidance]`
1.27.10 The timer families: `nanosleep`/`clock_nanosleep` (the latter with **`TIMER_ABSTIME`**, which
        is the only way to schedule "at time T" without drift), `setitimer` (legacy, per-process,
        signal-delivered), `timer_create` (POSIX per-process timers, signal or thread notification),
        and **`timerfd_create(clockid, flags)`** — a timer behind a **file descriptor**, so it joins
        your `epoll` set and needs no signal handler. `timerfd` is the right primitive for
        "expire these reservations" in an event loop. `[SYSCALL]` `[TABLE]`
1.27.11 Timer accuracy is bounded by the kernel's timekeeping, not by your requested value:
        **hrtimers** give sub-millisecond wakeups, `CONFIG_HZ` (250 or 1000 on distribution
        kernels) sets the tick for the coarse path, and the per-process **timer slack**
        (`prctl(PR_SET_TIMERSLACK)`, default **50 µs**) lets the kernel batch wakeups to save power.
        So `Thread.sleep(1)` may return in 1 ms or in 15 ms depending on the platform and load, and
        `LockSupport.parkNanos` is a *hint*. Never build a rate limiter on sleep granularity.
        `[NUM]` `[SYSCTL]` `[TRAP]`
1.27.12 The Java time API mapped to the clocks: `System.currentTimeMillis` → `CLOCK_REALTIME`;
        `System.nanoTime` → `CLOCK_MONOTONIC`; `Instant.now()` → `Clock.systemUTC()`, which reads
        the realtime clock at **microsecond** precision on modern JDKs (millisecond before Java 9 —
        a real behaviour change in code that deduplicated on timestamp); `Duration.between` for wall
        intervals but `nanoTime` deltas for measurement; and **inject a `Clock`** rather than calling
        the statics, which is the only way the expiry logic in 1.27.13 is testable.
        `[API]` `[VERSION-TRAP]`
1.27.13 `[INCIDENT]` `FundsLedger` released 340 stake reservations early and left 60 held for hours,
        on three instances, within the same minute. **Diagnosis:** logs showed negative computed
        durations (`elapsedMs = -2841`); `chronyc tracking` reported a **−2.9 s step** applied after
        a `chronyd` restart on all three hosts. **Root cause:** the in-memory reservation expiry
        index stored `System.currentTimeMillis() + ttl` as an absolute wall-clock deadline and
        compared it against `currentTimeMillis()`. A backward step made deadlines appear to be in
        the future (held) while the reordered index made others appear passed (released early) —
        against reservations whose lifetime is *seconds to hours* (Appendix A.6). **Fix:** deadlines
        as `System.nanoTime() + ttlNanos` for expiry decisions, wall-clock timestamps retained only
        for the audit record, and `clock_nanosleep(TIMER_ABSTIME)`/`timerfd` semantics for the sweep.
        `[INCIDENT]` `[PROVE]`

*(13 leaves)*

## §1.28 Finding, inspecting and killing a process

1.28.1 The two `ps` dialects and the columns that matter: BSD-style `ps aux` (`%CPU`, `%MEM`, `VSZ`,
       `RSS`, `STAT`, `START`, `TIME`, `COMMAND`) and UNIX-style `ps -ef` (`UID`, `PID`, `PPID`,
       `C`, `STIME`, `TTY`, `TIME`, `CMD`). `%CPU` in `ps` is an average **over the process's whole
       lifetime**, not an instantaneous figure — which is why `ps aux --sort=-%cpu` and `top`
       disagree and why `top` is right for "what is hot now". `[TABLE]` `[TRAP]`
1.28.2 The targeted forms worth memorising: `ps aux --sort=-%cpu | head -15`,
       `ps aux --sort=-%mem | head -15`, `ps -eLf | wc -l` (**total threads on the box** — `-L`
       is the thread flag), `ps -o pid,ppid,pgid,stat,etime,rss,cmd -p <pid>`, and
       `ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'` for anything wedged in uninterruptible I/O
       (§1.20.13). **`RSS` is real memory; `VSZ` is virtual and is meaningless for a JVM.**
       `[DIAG]` `[TRAP]`
1.28.3 `pgrep -fa 'java.*fundsledger'` beats `ps aux | grep`, which famously matches its own `grep`
       process. `pgrep -u <user>`, `pgrep -P <ppid>` (children), `pgrep -c` (count),
       `pidof`, and `pstree -p <pid>` for the tree. `[DIAG]`
1.28.4 **Who holds a port**, three ways, because the tool available differs per box:
       `ss -lptn 'sport = :8080'` (preferred — `netstat` is deprecated), `lsof -i :8080`,
       `fuser -n tcp 8080`. All three need privilege to show *another* user's process name; without
       it you get the socket and no owner. `[DIAG]` `[X-REF 10]`
1.28.5 `[PROC]` **`/proc/<pid>` is the process's own testimony**, and it is more authoritative than
       any tool: `cmdline` (NUL-separated — `tr '\0' ' ' < /proc/1234/cmdline`), `environ` (the
       environment **as it was at exec**, which is how you catch a stale `JAVA_TOOL_OPTIONS`),
       `cwd` and `exe` (symlinks — `exe` still resolves after the binary is deleted, showing
       `(deleted)`), `fd/` (§1.16), `limits` (**the fd/memory limits actually in force**, unlike
       your shell's `ulimit`), `status` (`VmRSS`, `Threads`, `SigBlk`), `wchan` (the kernel function
       it is sleeping in), `stack`. `[PROC]` `[DIAG]`
1.28.6 **`kill` means "send a signal", and its default signal is `SIGTERM` (15), not `SIGKILL`.**
       `int kill(pid_t pid, int sig)`. The name is the single most misleading identifier in POSIX:
       `kill <pid>` politely asks; `kill -9 <pid>` destroys. `kill -l` lists the names and numbers.
       `[SYSCALL]` `[TRAP]` `[NUM]`
1.28.7 **`kill -0 <pid>` sends no signal at all** — it performs only the existence-and-permission
       check, returning success if the process exists and you may signal it, `ESRCH` if it does not,
       `EPERM` if it does but you may not. It is the correct primitive for a pidfile liveness probe,
       and it is subject to the pid-reuse race (the pid may now be a different process), which is
       why systemd's cgroup tracking replaced pidfiles. `[SYSCALL]` `[PROVE]`
1.28.8 **`SIGKILL` cannot be caught, blocked or ignored** (§1.23.3), and there is one case where it
       still does nothing: a task in `D` state is not running any code to be killed and will not die
       until its I/O completes or the box reboots. `kill -9` on a wedged NFS reader is theatre.
       `[PROVE]` `[TRAP]`
1.28.9 **The escalation workflow, in order, and never leading with `-9`:**
       (1) `kill -3 <java-pid>` — capture a thread dump *before* you change anything;
       (2) `kill <pid>` — `SIGTERM`, the graceful request;
       (3) wait the service's real drain time and check `ps -p <pid>`;
       (4) `kill -9 <pid>` only if it ignored `SIGTERM`. `kill -9` skips shutdown hooks, buffered log
       flushes, in-flight request completion, lock release and clean connection teardown — it leaves
       stale distributed locks, half-written files and orphaned transactions. Reaching for it first
       is a genuine interview red flag; escalating to it is correct. `[FLOW]` `[TRAP]`
1.28.10 **`pkill -f` and its footguns.** `-f` matches the **full command line**, which is the only way
        to distinguish two JVMs — and also the way to kill far more than you meant: `pkill -f java`
        on a shared box kills every JVM; a pattern that appears in a *wrapper* script's arguments
        matches the wrapper too; `pkill` also matches processes started by other users and fails
        silently on the ones you cannot signal, so a zero exit code does not mean the target died.
        **Always `pgrep -fa <pattern>` first and read the list**, then reuse the identical pattern
        for `pkill`. `killall` matches by executable name only and means something different on BSD
        than on Linux. `[TRAP]` `[DIAG]`
1.28.11 **`kill -3` has JVM-native equivalents that are better in every way except availability.**
        `jcmd <pid> Thread.print` (thread dump to *your* terminal, not the process's stdout),
        `jcmd <pid> GC.heap_info`, `jcmd <pid> VM.native_memory summary` (needs
        `-XX:NativeMemoryTracking=summary` at start), `jcmd <pid> GC.heap_dump /tmp/heap.hprof`,
        `jstack -l <pid>` (with lock info), `jmap -histo:live <pid> | head -30`, `jps -lv` to find
        the pid. `jcmd` requires the same uid (or `CAP_SYS_PTRACE`) and a JDK on the box — which a
        distroless image does not have, so keep an ephemeral debug container or `jattach` ready.
        `[API]` `[DIAG]` `[TRAP]`
1.28.12 **Capture evidence before you kill.** Three thread dumps ten seconds apart (so you can tell
        a stuck thread from a busy one), `GC.heap_info`, and a heap dump if the symptom is memory.
        Once the process is gone the diagnosis is gone with it, and a hung JVM that gets restarted
        with no dump guarantees the same incident next week. `[TRAP]`
1.28.13 Exit codes as the post-mortem signal: **0** clean, **130** = 128+2 (`SIGINT`, Ctrl-C),
        **137** = 128+9 (`SIGKILL` — OOM killer or a grace-period expiry), **143** = 128+15
        (`SIGTERM`, i.e. a *graceful* stop that completed). `echo $?`,
        `systemctl show -p ExecMainStatus`, `kubectl get pod -o
        jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'`. `143` is a healthy
        deploy; `137` is a question. `[NUM]` `[DIAG]`
1.28.14 `[INCIDENT]` An operator paged for a hung `InternalPlatforms` JVM ran `pkill -f java` on a
        shared triage box and took `FundsLedger` down with it — 40 seconds of failed stake
        reservations at 1,200/sec. **Diagnosis:** `dmesg -T` showed no OOM; both JVMs exited **143**,
        i.e. deliberately signalled; shell history showed the `pkill`. **Root cause:** `-f java`
        matched every JVM on the host, and no dump was taken of the actually-hung one, so the
        original incident recurred two days later undiagnosed. **Fix:** `pgrep -fa` before `pkill`
        as a documented step (1.28.10), the escalation order of 1.28.9 in the runbook, and — the
        real fix — one service per host so that a blunt instrument has one target. `[INCIDENT]`
        `[DIAG]`

*(14 leaves)*

## §1.29 `/proc` and `/sys`: the observability substrate

1.29.1 **`/proc` is not a filesystem, it is a kernel API with `read()` as its calling convention.**
       Nothing is on disk; every `open`/`read` runs kernel code that formats a string at that
       instant. Two consequences: a read is **not atomic or consistent** across fields, so a
       process's numbers can be internally inconsistent; and `stat` sizes are meaningless (`ls -l
       /proc/meminfo` shows 0 bytes). Every tool in §1.30 is a `/proc` parser. `[PROVE]` `[PROC]`
1.29.2 `[PROC]` `/proc/<pid>/status` — the human-readable per-process summary, and the lines to read:
       `State: S (sleeping)`, `Threads: 214`, `VmRSS: 8912340 kB`, **`VmHWM:`** (the resident
       high-water mark — how close it *ever* came to the limit, which `VmRSS` cannot tell you),
       `RssAnon`/`RssFile`/`RssShmem`, `voluntary_ctxt_switches` vs
       `nonvoluntary_ctxt_switches` (the second rising means the scheduler is preempting you — CPU
       contention, not blocking), and the `SigBlk`/`SigIgn`/`SigCgt` hex masks. `[PROC]` `[DIAG]`
1.29.3 `[PROC]` `/proc/<pid>/stat` is the machine-readable form the tools actually parse: a single
       space-separated line whose fields are positional — field 14 `utime`, 15 `stime`, 23 `vsize`,
       24 `rss` (in **pages**, not bytes) — with `utime`/`stime` in **clock ticks**, where
       `USER_HZ` is **100** (`getconf CLK_TCK`). Field 2 is the comm in parentheses and **may
       contain spaces**, which breaks naive `awk '{print $14}'` parsing. `[PROC]` `[NUM]` `[TRAP]`
1.29.4 `[PROC]` `/proc/<pid>/smaps` and **`smaps_rollup`** for the memory question `RSS` cannot
       answer: `Rss`, **`Pss`** (proportional set size — shared pages divided by the number of
       sharers, the only figure that sums correctly across processes), `Private_Dirty` (what a fork
       would actually cost), `Anonymous`, `Swap`. `smaps_rollup` gives you the totals without
       parsing thousands of mapping entries — which matters, because reading full `smaps` on a
       12 GB-heap `FundsLedger` process is itself expensive. `[PROC]` `[NUM]`
1.29.5 `[PROC]` The per-process I/O and descriptor views: `/proc/<pid>/io` with **`rchar`/`wchar`**
       (bytes through the syscall interface, page-cache hits included) versus
       **`read_bytes`/`write_bytes`** (bytes that reached the block layer) — **the ratio between the
       two pairs is your page-cache hit rate**, computed with no extra tooling; plus `/proc/<pid>/fd/`
       (§1.16), `/proc/<pid>/fdinfo/<fd>` (file position, flags, and for an epoll fd the list of
       watched targets), and `/proc/<pid>/limits`. `[PROC]` `[CALC]`
1.29.6 `[PROC]` `/proc/meminfo`, and the lines that decide a memory incident: **`MemAvailable`** (the
       kernel's own estimate of what a new allocation could get — this is the number `free -h`'s
       `available` column reports, and the one to read), `MemFree` (unused, near zero **by design**),
       `Buffers`+`Cached` (reclaimable page cache), `Dirty` and `Writeback` (§1.18.6),
       `AnonPages`, `Slab`/`SReclaimable` (§1.17.6), `PageTables`, `SwapFree`,
       `Committed_AS` vs `CommitLimit`. `[PROC]` `[NUM]`
1.29.7 `[PROC]` The system-wide files: `/proc/loadavg` (`0.42 0.55 0.61 2/1043 88231` — the three
       averages, **runnable/total tasks**, and the last pid), `/proc/stat` (`cpu` lines whose
       columns are the cumulative jiffies behind `top`'s `us/sy/ni/id/wa/hi/si/st`, plus `ctxt`,
       `procs_running`, `procs_blocked`), `/proc/uptime`, `/proc/cpuinfo`, `/proc/interrupts`,
       `/proc/mounts` and `/proc/self/mountinfo`. `[PROC]` `[DIAG]`
1.29.8 `[PROC]` **PSI — pressure stall information — under `/proc/pressure/{cpu,memory,io}`**, the
       modern answer to "is this box saturated": each file gives `some avg10= avg60= avg300=
       total=` as the **percentage of time at least one task was stalled** on that resource, plus
       `full` for all tasks. Unlike load average it is dimensionless and needs no `nproc` to
       interpret, and unlike `%util` it measures the impact on *tasks* rather than on the device.
       It is per-cgroup too (`memory.pressure`, `io.pressure`). `[PROC]` `[NUM]`
       `[RESEARCH: Documentation/accounting/psi.rst]`
1.29.9 **`/proc/sys` *is* `sysctl`** — every tunable in this guide is a writable file there.
       `sysctl -a`, `sysctl net.core.somaxconn`, `sysctl -w vm.swappiness=1` (runtime only),
       `/etc/sysctl.d/99-quizstakes.conf` + `sysctl --system` for persistence. In a container most
       of `/proc/sys` is read-only and namespaced only for the network and IPC families — which is
       why a pod cannot raise `vm.max_map_count` and needs an init container or a node-level
       DaemonSet. `[SYSCTL]` `[TRAP]` `[X-REF 19]`
1.29.10 **`/sys/fs/cgroup` on the cgroup v2 unified hierarchy is where a container's truth lives**,
        and the file names are worth knowing cold: `memory.max` (the limit — `max` means
        unlimited), `memory.current`, `memory.high` (throttling threshold), `memory.stat`,
        **`memory.events`** (whose `oom_kill` counter is the definitive record that the kernel
        killed something in this cgroup), `cpu.max` (`quota period`, e.g. `200000 100000` = 2
        CPUs), **`cpu.stat`** (`nr_throttled`, `throttled_usec`), `pids.max`, `io.max`,
        `cgroup.procs`. v1's `memory.limit_in_bytes` paths are legacy — state which hierarchy you
        are on. `[PROC]` `[VERSION-TRAP]` `[NUM]`
1.29.11 **The JVM reads these files to size itself.** `-XX:+UseContainerSupport` (on by default)
        makes `Runtime.availableProcessors()` derive from `cpu.max` and
        `-XX:MaxRAMPercentage` derive the heap from `memory.max` instead of from host RAM. Verify
        with `java -XX:+PrintFlagsFinal -version | grep MaxHeapSize` **inside the container** —
        a pre-container-aware JVM, or one with cgroup v1 paths on a v2 host, sizes a 12 GB heap
        against the host's RAM and gets OOMKilled with no Java stack trace. `[API]`
        `[VERSION-TRAP]` `[X-REF 19]`
1.29.12 `[PROC]` **`/proc/<pid>/task/<tid>/` is the per-thread mirror** of everything above, and it
        is the bridge from OS to JVM: find the hot TID (`top -H -p <pid>` or `pidstat -t 1`),
        convert it to hex (`printf '%x\n' 4823` → `12d7`), and grep `nid=0x12d7` in a
        `jcmd Thread.print` dump to name the Java thread. That two-step is the standard "which Java
        thread is eating a core" recipe and it works with no profiler and no agent. `[PROC]`
        `[DIAG]` `[FLOW]`
1.29.13 `[INCIDENT]` `ClientRestrictions` breached its **30 ms p99** budget for 20 minutes; p50 was
        unchanged at 3 ms, CPU showed 40% utilisation, GC logs were clean and no dependency was
        slow. **Diagnosis:** `top` and `%CPU` were useless because the limit was not the host's.
        `cat /sys/fs/cgroup/cpu.stat` in the pod showed `nr_throttled` climbing by ~600/minute and
        `throttled_usec` accumulating; `cpu.max` read `20000 100000` — a **0.2 CPU quota** per
        100 ms period. **Root cause:** a Helm values merge dropped `resources.limits.cpu` to `200m`
        while the JVM still saw the node's 16 cores via `availableProcessors()` and sized its
        thread pools accordingly; every 100 ms period the container exhausted its quota and every
        runnable thread was stopped dead until the next one. **Fix:** raise the limit to match the
        measured need, and read `cpu.stat`/`memory.events` — not `top` — as the first move on any
        containerised latency incident. `[INCIDENT]` `[PROC]` `[CALC]`

*(13 leaves)*

## §1.30 The box-triage toolkit and the order you run it in

1.30.1 **Say the order out loud, then follow it: load/CPU → memory → disk → network → application →
       *what changed*.** The discipline is that each step either indicts a resource or exonerates it;
       you never skip ahead because a hypothesis is attractive. The last step is not optional — a
       box that was healthy an hour ago was changed by a deploy, a config push, a traffic shift or a
       dependency, and *that* is usually the answer. `[FLOW]` `[X-REF 20]`
1.30.2 **`uptime` / load average, which is meaningless without `nproc`.** The three figures are
       1/5/15-minute averages of runnable **plus uninterruptible** tasks. Load 8 on 16 cores is
       half-utilised; load 8 on 2 cores is 4× oversubscribed. The **trend matters more than the
       value** — `8.42, 7.90, 6.11` is rising and `6.11, 7.90, 8.42` is recovering. And because
       `D`-state counts, a load spike with idle CPUs is a **storage** incident (§1.20.13).
       `[DIAG]` `[TRAP]` `[NUM]`
1.30.3 **`top`, and the `%Cpu(s)` line that is the actual diagnostic**, field by field:
       `us` (your code: hot loop, GC, serialisation, regex), `sy` (kernel: syscall storm, context
       switching, tiny reads/writes), `ni`, `id` (**high `id` with bad latency means you are not
       CPU-bound — you are waiting on locks or a downstream**), `wa` (I/O wait), `hi`/`si`
       (hard/soft interrupts — high `si` is packet processing), **`st` (steal — the hypervisor gave
       your vCPU to a noisy neighbour; move the instance)**. Reading
       `%Cpu(s): 22.1 us, 4.0 sy, 0.0 ni, 12.3 id, 61.2 wa` takes one second and tells you not to
       open the GC logs. `[DIAG]` `[TABLE]`
1.30.4 `top`'s interactive keys, which is where the per-process answer comes from: **`1`** (per-core
       lines — one core at 100% with fifteen idle is a single-threaded bottleneck), **`H`**
       (individual **threads**, and the TID you feed to 1.29.12), `M` (sort by memory), `P` (by
       CPU), `c` (full command line), `e`/`E` (units). `htop` shows the same data with per-core
       bars, `F5` tree view and `F4` filtering — strictly nicer where it is installed. `[DIAG]`
1.30.5 **`vmstat 1` is the whole-box heartbeat in one line.** `r` (runnable queue — compare with
       `nproc`), `b` (blocked, i.e. `D` state), **`si`/`so` (swap in/out — anything non-zero on a
       latency-sensitive JVM box is an alert, not a curiosity)**, `bi`/`bo` (block I/O),
       `in` (interrupts/sec), **`cs` (context switches/sec — tens of thousands on a small box with
       high `%sy` is thread thrashing or lock convoying)**, then the same CPU split as `top`.
       Discard the first line: it is an average since boot. `[DIAG]` `[NUM]` `[TRAP]`
1.30.6 **`pidstat` is the per-process/per-thread layer `top` cannot give you cleanly:**
       `pidstat 1` (CPU per process), **`pidstat -t -p <pid> 1`** (per **thread**, so you get the
       TID *and* its CPU without `top -H`'s clutter), `pidstat -d 1` (per-process disk I/O),
       `pidstat -w 1` (voluntary vs involuntary context switches per process), `pidstat -r 1`
       (page faults and RSS, minor vs **major** — §1.14). `[DIAG]`
1.30.7 **`free -h`, and the misread that defines this section.** `free` = *completely unused* RAM,
       which on a healthy long-running Linux box is near zero **by design**, because idle RAM is
       wasted RAM and the kernel fills it with page cache. `buff/cache` is reclaimable.
       **`available` is the only column that matters** — the kernel's estimate of what a new
       process could get, counting reclaimable cache (`MemAvailable`, §1.29.6). "We're out of
       memory, `free` shows 300 MB" is almost always wrong; you are genuinely short only when
       **`available` is small *and* swap is actively moving** (`si`/`so` in 1.30.5). `[TRAP]`
       `[DIAG]` `[NUM]`
1.30.8 **Disk space, in the order that finds it:** `df -h` (am I full?) → **`df -i`** (inodes — you
       can be full with bytes free, §1.19.5) → `du -xh --max-depth=2 /var | sort -h | tail -20`
       (what is consuming it, `-x` staying on one filesystem) → **`lsof +L1`** (deleted-but-open
       files, §1.19.8). Four commands, and between them they cover every "no space left on device"
       you will meet. `[FLOW]` `[DIAG]`
1.30.9 **`iostat -x 1`** for the device layer — the field-by-field reading is §1.20.5, and the two
       things to carry into triage are that **`await` is the latency your application feels** and
       that **`%util` is not saturation on a multi-queue device** (§1.20.6). Drop the first sample.
       `[DIAG]` `[X-REF 11]`
1.30.10 **Network, in two commands before anything else:** `ss -s` (the summary — total sockets,
        `TIME-WAIT` count, per-protocol breakdown) and `ss -tanp` (every TCP socket with state and
        **owning process**). Then `ss -lnt` for listen queues, `nstat -az | grep -i listen` for
        overflow counters. `netstat` is deprecated and slower on a box with 50k sockets.
        `[DIAG]` `[X-REF 10]`
1.30.11 **`lsof`, the three invocations that matter:** `lsof -p <pid>` (everything one process holds
        — pipe through `awk '{print $5}' | sort | uniq -c | sort -rn` to bucket by fd type and spot
        a leak's shape), `lsof -i :8080` (who owns a port), `lsof +L1` (deleted-but-open). It is
        slow and needs privilege; `ls /proc/<pid>/fd | wc -l` is the instant approximation.
        `[DIAG]`
1.30.12 **`strace -c -p <pid>`** for a syscall profile (count, time, errors per syscall — the fastest
        way to find a syscall storm behind high `%sy`) and `strace -f -e trace=openat` for a
        specific question. **It uses `ptrace` and can slow the target 10–100×, so it is a
        last resort on a production JVM**, never a monitoring tool. The low-overhead
        alternatives: `perf trace`, `perf stat -p`, and `bpftrace`/bcc (`opensnoop`, `execsnoop`,
        `biolatency`). `[DIAG]` `[TRAP]`
1.30.13 **`dmesg -T` is where the kernel tells you what it did to you** —
        `dmesg -T | grep -i -E 'oom|killed process|blocked for more than'` finds OOM kills
        (with the score, RSS and cgroup of the victim), hung-task warnings, EBS/NVMe I/O errors and
        filesystem remounts. `journalctl -k --since '30 min ago'` for the persistent copy, and
        `-T` for human timestamps rather than seconds-since-boot. **Exit 137 with no application
        error in the log means come here first.** `[DIAG]` `[X-REF 11]`
1.30.14 `[INCIDENT]` "`ApplicationGateway` is slow, you have SSH" — the worked triage.
        `uptime`: load **8.42, 7.90, 6.11** on `nproc` 4, and rising. `top`:
        **`61.2 wa`, `12.3 id`, `22.1 us`** — I/O-bound, so the GC logs are the wrong place and
        `st` at 0.0 exonerates the hypervisor. `free -h`: `available 9.4Gi`, swap 0 — memory is
        fine, and `free 0.3Gi` is a red herring (1.30.7). `iostat -x 1`: `w_await` 180 ms,
        `%util` 100. `pidstat -d 1`: one JVM at 240 MB/s written. `lsof -p` + `ls -l`: an access log
        at DEBUG. **Root cause:** a log level left at DEBUG by a config push 50 minutes earlier
        (the *what changed* step) saturated the volume; every request now waited on a synchronous
        log write. **Fix:** revert the config, then make the appender asynchronous so a log volume
        can never again be on the request path. `[INCIDENT]` `[DIAG]` `[FLOW]`

*(14 leaves)*

## §1.31 Log combat: the text-processing pipeline for an incident

1.31.1 **`tail -F`, capital F, always.** `tail -f` follows the *inode* and goes silent the moment
       `logrotate` renames the file; `tail -F` follows the *name* and reopens. Also
       `tail -n 500 app.log`, `tail -n +1000` (from line 1000 onward), and **`less +F app.log`** —
       follow, `Ctrl-C` to stop and search, `F` to resume. `[TRAP]` `[DIAG]`
1.31.2 **`less` beats `cat`, `vim` and an editor on a 4 GB log because it does not load the file.**
       Inside it: `/pattern` and `?pattern` search, `n`/`N` next/previous, `G` end, `g` start,
       **`&pattern`** (show *only* matching lines — grep without leaving the pager), `-S` chop long
       lines, `-N` line numbers, `F` follow. `zless`/`zcat` for rotated `.gz`. `[DIAG]`
1.31.3 The `grep` surface worth knowing cold: `-i` (case), `-c` (count), `-n` (line numbers),
       **`-v`** (invert — the healthcheck-noise filter), `-E` (alternation: `grep -E
       'ERROR|FATAL'`), **`-C 5`** (5 lines of context either side; `-A` after, `-B` before — the
       flag that turns a matched exception line into a readable stack trace), `-o` (print only the
       match, which is what makes field extraction possible), `-r` (recursive), `-l`/`-L` (files
       with/without matches), **`zgrep`** for rotated archives. `rg` is faster and respects
       `.gitignore`, but is not installed on the box you are paged for. `[DIAG]` `[TABLE]`
1.31.4 **`grep | awk | sort | uniq -c | sort -rn | head` is the whole discipline.** Filter to the
       lines that matter, extract the field that matters, group, count, rank. Learn this one
       pipeline and you can answer "what is happening" on any log format in any language.
       **`uniq -c` counts only *adjacent* duplicates, which is why `sort` must precede it** — the
       single most common mistake in the idiom. `[PROVE]` `[TRAP]`
1.31.5 `[DIAG]` **Top 10 error messages by frequency** — the first command of any incident, because
       it turns 400,000 lines into a ranked list of five distinct problems:
       `grep ERROR app.log | awk -F'ERROR' '{print $2}' | sort | uniq -c | sort -rn | head`.
       Refine by cutting the variable tail (`cut -c1-80`) so that the same error with different ids
       groups together instead of producing 400,000 groups of one. `[DIAG]`
1.31.6 `[DIAG]` **Requests per minute around the incident** — the shape that tells you whether this
       was a traffic event or a code event:
       `grep '2026-08-21T14:' app.log | cut -c1-16 | uniq -c`
       (`cut -c1-16` truncates an ISO-8601 timestamp to minute precision, and the lines are already
       time-ordered so `uniq -c` needs no `sort`). Add `| sort -k2` to compare with the deploy time.
       `[DIAG]` `[CALC]`
1.31.7 `[DIAG]` **Slowest endpoints from an access log, by field**:
       `awk '{print $10, $7}' access.log | sort -rn | head -20` where field 7 is the path and field
       10 the duration. Then the aggregate view — mean and count per path —
       `awk '{s[$7]+=$10; n[$7]++} END {for (p in s) printf "%8.1f %6d %s\n", s[p]/n[p], n[p], p}'
       access.log | sort -rn | head`. **Check the field numbers against your own log format first**;
       every combined-log variant numbers them differently and a confidently wrong `$10` produces a
       confidently wrong incident review. `[DIAG]` `[TRAP]`
1.31.8 `[DIAG]` **Tracing one request across an interleaved, multi-line log** — the payoff for
       correlation ids: `grep 'correlationId=7c9a-…' app.log`, and because a Java stack trace is
       many lines that do *not* carry the id, `grep -A 40 'correlationId=7c9a-…' app.log` or an
       `awk` block that treats a timestamp-prefixed line as a record start
       (`awk '/^2026-/{p=/7c9a/} p'`). **Without a correlation id you cannot reconstruct a single
       request from a concurrent log, and no amount of tooling recovers it after the fact.**
       `[DIAG]` `[X-REF 20]`
1.31.9 **`awk` as a two-line data language, not a mystery**: `-F','` sets the field separator, `$0`
       is the line, `$1..$NF` the fields, `NF` the field count, `NR` the record number, `/re/{…}`
       a pattern-action block, `END{…}` the epilogue. Sum a column
       (`awk '{s+=$10} END {print s}'`), average it (`END {print s/NR}`), filter numerically
       (`awk '$10 > 1000'`), and reformat with `printf`. That is 90% of production `awk`.
       `[TABLE]` `[BUILD]`
1.31.10 **`sed` for line ranges and surgical edits**: `sed -n '100,200p' app.log` (print a line
        range without loading the file), `sed -n '/14:22:00/,/14:24:00/p' app.log` (**a time window
        by pattern range** — the most useful `sed` idiom in an incident),
        `sed 's/token=[^ ]*/token=REDACTED/g'` before pasting a log into a ticket. Plus `wc -l`,
        `sort -u`, `sort -k2 -rn`, `cut -d',' -f2`, `head`/`tail -n +N`, `tr`, `paste`, `comm`, and
        `xargs -n1 -P4` to parallelise. `[DIAG]`
1.31.11 **`jq` for structured logs, which is where new services should be**: `jq .` (pretty-print),
        `jq -r '.items[].name'` (**raw** — no quotes, so the output is pipeable),
        `jq 'select(.level=="ERROR")' app.jsonl`,
        `jq -r 'select(.durationMs > 1000) | "\(.path) \(.durationMs)"' app.jsonl`,
        `jq -s 'group_by(.path) | map({path: .[0].path, n: length}) | sort_by(-.n)' app.jsonl`
        (`-s` slurps a JSON-lines stream into an array so you can aggregate). A structured log
        makes 1.31.5–1.31.7 exact instead of positional. `[DIAG]` `[API]`
1.31.12 **`journalctl` on a systemd box**, because the file may not exist: `journalctl -u
        fundsledger --since '10 min ago'`, `-f` (follow), `-p err` (priority), `-k` (kernel — the
        `dmesg` equivalent, §1.30.13), `-b -1` (the previous boot), `--no-pager`, `-o json` to pipe
        into `jq`, `--disk-usage` and `--vacuum-time=7d`. **`-u` plus `--since` is the one form to
        memorise**; without `--since` you will page through a week. `[DIAG]`
1.31.13 **In Kubernetes the log is a moving target**: `kubectl logs deploy/clientrestrictions --since=15m`,
        **`--previous`** (the *dead* container's log — the only place an OOMKilled JVM's last words
        exist), `-c <container>`, `--all-containers`, `-f`, and `stern`/`kubectl logs -l app=` for
        many pods at once. Then `| jq -r 'select(.traceId=="…") | .message'` to reach 1.31.8. A pod
        that has been rescheduled twice has taken its evidence with it — which is why logs ship to
        a store and `kubectl logs` is only for the last few minutes. `[DIAG]` `[X-REF 19]`
1.31.14 `[INCIDENT]` Card deposit success rate fell from 99.4% to 91% with no alert firing, because
        every individual call was inside its 15 s timeout. **Diagnosis:**
        `grep DEP-309 app.log | cut -c1-16 | uniq -c` (1.31.6) showed failures per minute stepping
        up at 13:47 and holding;
        `grep DEP-309 app.log | awk -F'reason=' '{print $2}' | sort | uniq -c | sort -rn`
        (1.31.5) showed 94% of them were a single PSP decline code, not timeouts;
        `awk '$7=="/authorise" {s+=$10; n++} END {print s/n}' access.log` showed mean authorise
        latency up from 240 ms to 4.1 s — inside the timeout, so no error, no alert. **Root cause:**
        the PSP was degrading and shedding load with declines, the documented
        "elevated declines before outage" signature (Appendix A.4). **Fix:** alert on the
        *success-rate* derivative and on p99 against the 11 s figure, not only on error counts —
        four shell pipelines found in three minutes what the monitoring did not have a rule for.
        `[INCIDENT]` `[DIAG]` `[CALC]`

*(14 leaves)*

## §1.32 CPU caches, cache lines, false sharing and the memory hierarchy

1.32.1 **The hierarchy with real numbers, as an ordered table**, because every optimisation in this
       section is an argument about these ratios: register (<1 ns), **L1d 32–48 KiB, ~4 cycles
       ≈ 1 ns**, **L2 1–2 MiB, ~12–15 cycles ≈ 4 ns**, **L3 (shared) 8–64 MiB, ~40 cycles
       ≈ 15–20 ns**, **DRAM ~80–100 ns**, NVMe read ~20 µs, EBS read ~1 ms, cross-AZ RTT ~1 ms. The
       jump from L3 to DRAM is 5×; the jump from DRAM to NVMe is 200×. `[TABLE]` `[NUM]`
1.32.2 **The cache line is 64 bytes on x86-64, and it is the unit of everything.** Nothing moves
       between memory and cache in smaller pieces: reading one `byte` fetches 64; writing one
       `long` dirties 64. Verify on the box with
       `getconf LEVEL1_DCACHE_LINESIZE`, `lscpu | grep -i cache`, or
       `cat /sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size`. AArch64 is also
       typically 64, but **Apple M-series is 128** — a portability trap for hand-padded code.
       `[NUM]` `[PROC]` `[VERSION-TRAP]`
1.32.3 **Spatial and temporal locality are the only two things the hardware rewards.** Contiguous
       traversal gets 8 `long`s per line fetch and a hardware prefetcher that predicts the next
       line; pointer-chasing a linked list gets one useful word per DRAM round trip. An
       `ArrayList<Long>` of 8 million elements is 8 million pointer dereferences to scattered boxed
       objects; a `long[]` of 8 million is 64 MiB of sequential lines. This single difference is
       usually larger than any algorithmic change you were considering. `[PROVE]` `[CALC]`
1.32.4 **Coherence: MESI**, in exactly enough detail to reason about a write. Each line in each
       core's cache is Modified, Exclusive, Shared or Invalid. A write requires **exclusive
       ownership**, so the core issues a *read-for-ownership* that **invalidates every other core's
       copy of that line**. A read by another core then misses and must fetch the line from the
       owner. Writes are therefore not local operations — they are coherence traffic.
       `[PROVE]` `[SOURCE]`
1.32.5 **False sharing** follows directly: two variables that no thread shares, sitting in the same
       64-byte line, are shared *by the hardware*. Every write by core A invalidates core B's copy
       of a line B needs for a completely unrelated field, and both threads take an L3-or-worse miss
       on every increment. The code is correct, the contention is invisible in the source, and the
       throughput loss is an order of magnitude. `[PROVE]` `[TRAP]`
1.32.6 `[CALC]` **The arithmetic on a QuizStakes counter.** Take
       `long[] settlementsByPartition = new long[3]` — one counter per `FundsLedger` partition, each
       updated by its own thread. Three `long`s is 24 bytes: the array's 16-byte header plus 24
       bytes of payload sits **entirely inside one or two 64-byte lines**, so all three threads
       contend on the same line. At the **3,400/sec settlement burst** each increment costs a
       coherence round trip (~40–100 ns) instead of an L1 hit (~1 ns). Pad to one line per counter —
       `long[] c = new long[3 * 8]`, using index `i * 8` — and the three counters occupy three
       distinct lines with zero coherence traffic. The fix costs 168 bytes. `[CALC]` `[NUM]`
       `[BUILD]`
1.32.7 **`@Contended` is the JVM's declarative padding**, and its two footguns are the reason people
       get it wrong: the annotation is `jdk.internal.vm.annotation.Contended` (it moved out of
       `sun.misc`), and **it is ignored on application classes unless you run with
       `-XX:-RestrictContended`** — silently, with no warning, so the "fix" changes nothing.
       Manual padding (1.32.6) or a purpose-built class is more honest in application code.
       `[API]` `[TRAP]` `[VERSION-TRAP]`
1.32.8 **The JDK already solved this for counters, and the solution is `LongAdder`.**
       `java.util.concurrent.atomic.Striped64` maintains an array of padded `Cell`s
       (`@Contended static final class Cell`), so contending threads hit different lines and
       different cache lines entirely; `sum()` adds them up. Under the 3,400/sec settlement burst
       `LongAdder.increment()` scales with cores where `AtomicLong.incrementAndGet()` degrades — a
       single hot `AtomicLong` is a CAS loop on one cache line, which is 1.32.5 with extra steps.
       Use `AtomicLong` when you need `compareAndSet` or an exact instantaneous read; `LongAdder`
       when you need throughput on a monotonic counter. `[API]` `[SOURCE]` `[PROVE]`
1.32.9 **Java object layout is why you cannot reason about lines from source alone**: a 12-byte
       header (mark word + compressed class pointer) padded to an 8-byte boundary, fields
       **reordered by the JVM** (largest first, references grouped) rather than in declaration
       order, and the whole object aligned to 8 bytes. So two fields you wrote adjacently may not be
       adjacent, and two you wrote apart may share a line. Measure with **JOL**
       (`ClassLayout.parseClass(X.class).toPrintable()`), never assume. Note also the compressed-oop
       boundary: past a **32 GB** heap references become 8 bytes and every object grows.
       `[API]` `[NUM]` `[TRAP]`
1.32.10 The connection to the memory model, stated in one paragraph so the reader is not sent away
        empty-handed: the store buffer and invalidation queues that make 1.32.4 fast are exactly why
        a write by one thread is not immediately visible to another, and why `volatile`, `final`
        and `synchronized` exist — they emit the barriers that flush and order those buffers.
        `volatile` on a hot field is *both* a barrier cost and a cache-line-invalidation cost.
        `[X-REF 06]`
1.32.11 **Measuring it, rather than guessing.** `perf stat -e
        cycles,instructions,cache-references,cache-misses,LLC-load-misses -p <pid> -- sleep 10`
        gives you a miss *rate* (misses ÷ references — above roughly 10% on a data-heavy workload is
        worth investigating) and **IPC** (instructions per cycle; below ~1 on straight-line code
        means you are stalled on memory, not executing). Then
        **`perf c2c record`/`perf c2c report`**, which exists for exactly one purpose: attributing
        **HITM** (hit-modified) events to the specific cache line and source line where two cores
        are fighting. That is the only tool that *proves* false sharing rather than suggesting it.
        `[DIAG]` `[NUM]` `[RESEARCH: perf-c2c(1)]`
1.32.12 Prefetching and the shape of your data structures: the hardware prefetcher detects
        sequential and simple strided access and hides DRAM latency entirely — and detects nothing
        in a hash map, a tree or a linked list. This is why an open-addressed map beats a chained
        one, why sorting before a batch lookup can beat the lookup itself, and why "O(n) with good
        locality" routinely beats "O(log n) with pointer chasing" at the sizes real services use.
        `[PROVE]`
1.32.13 **NUMA is the same argument one level up** — remote-socket memory access costs 1.5–2× local,
        and `numactl`, `numastat`, `lscpu`'s NUMA lines and the JVM's `-XX:+UseNUMA` are the
        controls. Deferred in full to §2.8; the only thing to carry here is that a 12 GB
        `FundsLedger` heap on a two-socket box can have half its pages on the wrong node.
        `[X-REF §2.8]`
1.32.14 `[INCIDENT]` `FundsLedger` settlement throughput plateaued at ~2,100/sec against a
        3,400/sec burst requirement, and **adding instances made it worse**, not better.
        **Diagnosis:** `perf stat` showed IPC of 0.31 and an LLC miss rate above 40% with no obvious
        working set to blame; GC was clean; the profiler pointed at a one-line counter increment.
        `perf c2c report` attributed 78% of HITM events to a single cache line — the
        `long[] settlementsByPartition` array of 1.32.6 — and named the three threads fighting over
        it. **Root cause:** textbook false sharing; three per-partition counters in one 64-byte
        line, so every settlement invalidated two other cores' caches. **Fix:** `LongAdder` per
        partition (1.32.8), which restored 3,600/sec on the same hardware. The lesson worth keeping
        is the diagnostic order — the profiler said *where*, only `perf c2c` said *why*.
        `[INCIDENT]` `[DIAG]` `[CALC]`

*(14 leaves)*

---

## §1.33 Remote access and file transfer: SSH, key mechanics, tunnels and SSM

1.33.1 Why this section exists in an operating-systems bible at all: SSH is the only interface most
       engineers ever have to a production kernel, and every diagnostic in §1.30 is run *through*
       it. The mechanism is also the cleanest available example of a `[SYSCALL]`-level story the
       reader already has intuition for — `fork`/`exec` of a login shell, a pty allocated by the
       kernel (§1.26.3), and a session created with `setsid` (§1.26.2).
1.33.2 The public-key mechanism, stated as an exchange rather than a recipe:
       `ssh-keygen -t ed25519 -C "…"` produces a keypair; the **public** half is appended to
       `~/.ssh/authorized_keys` on the server, the **private** half never leaves the client. On
       connect the server sends a challenge, the client signs it, the server verifies against the
       stored public key. **Nothing secret crosses the wire** — which is the whole reason keys beat
       passwords, and the one-line answer to "why not just use a password". `[PROVE]`
1.33.3 Ed25519 vs RSA as a current-practice choice: `ed25519` is the default recommendation (small
       fixed-size keys, fast verification, no key-size parameter to get wrong); `rsa` requires
       `-b 4096` to be defensible; `ssh-rsa` **as a signature algorithm** (SHA-1) has been disabled
       by default in OpenSSH since 8.8, which is why an old key can suddenly stop working after a
       server upgrade with a bare `Permission denied (publickey)`. `[VERSION-TRAP]` `[TRAP]`
1.33.4 **Permissions are enforced, not advised.** `~/.ssh` must be `700`, `authorized_keys` and any
       private key `600`, and the home directory must not be group-writable.
       `Permissions 0644 for 'id_rsa' are too open` is a **refusal to use the key**, not a warning —
       the connection then falls through to the next auth method and fails as though the key were
       wrong. Ties directly to the permission bits in §1.25. `[DIAG]` `[TRAP]` `[X-REF 11]`
1.33.5 `~/.ssh/config` as the unit of repeatability, with the fields that matter:
       `Host`, `HostName`, `User`, `IdentityFile`, `IdentitiesOnly yes` (without it the agent offers
       every key it holds and can trip a server's `MaxAuthTries`), `ProxyJump`,
       `ServerAliveInterval 30`/`ServerAliveCountMax` (the fix for a session dropped by a NAT or
       load-balancer idle timeout — the same mechanism as TCP keepalive, `[X-REF 10]`), and
       `ControlMaster`/`ControlPersist` for connection reuse. `[API]` `[TABLE]`
1.33.6 The bastion pattern: `ssh -J bastion user@private-host` (equivalently `ProxyJump`), and why
       it is not `ssh bastion` followed by `ssh private-host` — with `ProxyJump` the private key
       stays on the workstation and authentication to the inner host is end-to-end, whereas hopping
       manually requires a key **on the bastion**, which is the thing you were avoiding.
       `[PROVE]` `[TRAP]`
1.33.7 Port forwarding, all three directions, stated precisely because interviews ask for the
       distinction: `-L 5432:db.internal:5432` binds a **local** port and tunnels outward (reach the
       `FundsLedger` Postgres instance through a bastion without exposing it); `-R` binds a port on
       the **remote** host back to the client; `-D` is a local SOCKS proxy. `-N` (no remote command)
       and `-f` (background) are what make a tunnel a tunnel rather than a shell. `GatewayPorts` and
       `AllowTcpForwarding` are the server-side controls. `[TABLE]` `[NUM]`
1.33.8 `ssh-agent` and the trust boundary: `ssh-add` holds decrypted keys in memory so a passphrase
       is typed once; `-A`/`ForwardAgent` exposes that agent socket on the remote host, where
       **anyone with root can use your keys against every host you can reach**. Prefer `ProxyJump`
       over agent forwarding; where forwarding is unavoidable, `ssh-add -c` forces per-use
       confirmation. `[TRAP]`
1.33.9 `known_hosts` as host-key pinning: the first connection records the server's key
       (`StrictHostKeyChecking ask`), and a later mismatch produces
       `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` and a refusal. That warning has exactly
       two causes — the host was rebuilt, or you are being MITM'd — and **blindly running
       `ssh-keygen -R host` discards the only evidence that distinguishes them.** Verify the
       fingerprint out of band first. `[DIAG]` `[TRAP]` `[X-REF 13]`
1.33.10 File transfer and what to use when: `scp file user@host:/tmp/` and `scp -r` for one-shot
        small copies (and note `scp` now runs over the SFTP protocol by default as of OpenSSH 9.0);
        `rsync -avz --progress src/ user@host:/dest/` for anything large or repeated because it is
        **incremental and resumable** — `--partial`, `--delete`, `-e ssh`, and the trailing-slash
        rule (`src/` copies the contents, `src` copies the directory) that silently produces a
        nested directory when you get it wrong. `[VERSION-TRAP]` `[TRAP]`
1.33.11 The reason a heap dump is the motivating example: pulling a 12 GB `FundsLedger` heap dump
        (§2.3) off a node is an `rsync` job, not an `scp` job, and copying it into the container's
        writable overlay first can fill the node's disk — write it to a mounted volume and stream it
        out. `[CALC]` `[X-REF 19]`
1.33.12 **AWS SSM Session Manager as the current answer**, and why naming it signals current
        practice: no inbound port 22, no key distribution or rotation problem, IAM-scoped access,
        every session logged to CloudTrail/S3, and port forwarding via
        `aws ssm start-session --document-name AWS-StartPortForwardingSession`. The trade-off is a
        dependency on the SSM agent and on the instance's IAM role. In an EKS context the equivalent
        for a *container* is `kubectl exec`, which is not SSH at all — it is an API call to the
        kubelet that `exec`s into the container's namespaces (§2.13). `[VERSION-TRAP]` `[X-REF 18]`
        `[X-REF 19]`
1.33.13 `[INCIDENT]` An engineer investigating the `ClientRestrictions` 30 ms budget breach could
        reach the bastion but every `ssh -J` into the private subnet hung for ~2 minutes and then
        returned `Permission denied (publickey)`. **Diagnosis:** `ssh -vvv` showed the client
        offering **six** keys from a forwarded agent before the server closed the connection, and
        the server's `/var/log/secure` logged `error: maximum authentication attempts exceeded`
        against the default `MaxAuthTries 6`. **Root cause:** an agent holding many keys, with no
        `IdentitiesOnly yes` and no `IdentityFile` pinned for that host, so the correct key was
        offered seventh. **Fix:** pin `IdentityFile` + `IdentitiesOnly yes` per `Host` block in
        `~/.ssh/config`; the hang itself was the six failed round trips, not the network.
        `[INCIDENT]` `[DIAG]` `[NUM]`

*(13 leaves)*

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

---

# PART 3 — UNDER THE HOOD

This is the tier that separates someone who has read about the kernel from someone who has traced a
symptom into it. Every section names the struct, the function, the file and the counter — because in
production the only defensible claim is one you can point at.

## §3.1 From power-on to PID 1: firmware, bootloader, `initramfs`, `init`

3.1.1 **UEFI firmware, not BIOS.** Power-on → firmware initialises RAM and PCIe → reads the boot
      order from NVRAM → loads a `.efi` binary from the **EFI System Partition** (FAT32, mounted at
      `/boot/efi`). Evidence the box booted UEFI rather than legacy: `/sys/firmware/efi` exists.
      Inspect and reorder with `efibootmgr -v`. Secure Boot chains firmware → `shim` → `grub` →
      `vmlinuz`, and its state is in `/sys/firmware/efi/efivars/SecureBoot-*` or
      `mokutil --sb-state`. `[PROC]` `[FLOW]`
3.1.2 **The bootloader's one job**: load two blobs and a string. GRUB2 reads
      `/boot/grub2/grub.cfg`, loads `vmlinuz-6.12.x` (a **`bzImage`** — a small real-mode setup
      header plus a self-decompressing compressed kernel) and `initramfs-6.12.x.img` into memory,
      and passes the **kernel command line**. Nothing else about GRUB matters to a backend
      engineer. `[NUM]`
3.1.3 **The kernel command line is the highest-leverage config on the box** because it sets things
      no sysctl can change at runtime: `root=UUID=…`, `ro`, `console=ttyS0,115200`,
      `transparent_hugepage=madvise`, `hugepagesz=2M hugepages=6144`,
      `systemd.unified_cgroup_hierarchy=1`, `cgroup_no_v1=all`, `mitigations=off`,
      `intel_idle.max_cstate=1`, `nvme_core.io_timeout=4294967295`, `crashkernel=`,
      `isolcpus=`/`nohz_full=`. Read yours from `/proc/cmdline` before believing any tuning claim.
      `[PROC]` `[SYSCTL]`
3.1.4 **Early kernel bring-up, in order:** the decompressor relocates and unpacks the kernel →
      `startup_64` in `arch/x86/kernel/head_64.S` builds identity page tables and enters 64-bit
      mode → `start_kernel()` in `init/main.c` runs `setup_arch()`, brings up the `memblock` early
      allocator, then the buddy allocator, then `sched_init()`, `mm_init()`, `time_init()`,
      `rest_init()`. `rest_init` spawns **PID 1** (`kernel_init`) and **PID 2** (`kthreadd`, the
      parent of every `[bracketed]` kernel thread), then becomes the idle task on CPU 0.
      `[SOURCE]` `[FLOW]`
3.1.5 **Why `initramfs` exists at all**, stated as the problem it solves: the kernel must mount the
      root filesystem, but the root filesystem may live behind an NVMe driver, an LVM volume group,
      a LUKS container or an NFS mount whose modules live *on that filesystem*. The `initramfs` is
      a **cpio archive unpacked into a `rootfs` (tmpfs) instance** that the kernel can execute from
      with no drivers at all. `[PROVE]`
3.1.6 **The `initramfs` handover, step by step:** kernel unpacks the cpio into `rootfs` →
      `kernel_init` execs `/init` (a `dracut`- or `mkinitcpio`-generated script, systemd-based on
      Amazon Linux 2023) → udev loads storage/network modules → the real root is assembled and
      mounted at `/sysroot` → `switch_root` (`pivot_root` + `chroot` + `exec`) replaces PID 1 with
      `/usr/lib/systemd/systemd` on the real root → the tmpfs is freed. Inspect the archive with
      `lsinitrd`. `[FLOW]` `[BUILD]`
3.1.7 **systemd as PID 1**: it reaps orphans, resolves a dependency graph of units to reach
      `default.target` (`multi-user.target` on a server), and starts services in parallel subject
      to `After=`/`Requires=`/`Wants=`. The three facts that matter operationally: **socket
      activation** (systemd holds the listening fd, so a restart loses no connections),
      `Type=notify` with `sd_notify` (readiness, not "the process started"), and
      `Restart=`/`RestartSec=`/`StartLimitBurst=` deciding whether a crash loop is visible or
      silent. `[API]`
3.1.8 **systemd creates the cgroup tree**, which is why cgroup v2 is not optional on a modern
      distribution: it mounts `cgroup2` at `/sys/fs/cgroup`, enables controllers in
      `cgroup.subtree_control`, and places everything under `init.scope`, `system.slice` and
      `user.slice`. A `FundsLedger` unit therefore lives at
      `/sys/fs/cgroup/system.slice/fundsledger.service/` and its limits are that directory's
      files. `[PROC]` `[X-REF 19]`
3.1.9 **Measuring boot** and why it is a capacity number, not trivia: `systemd-analyze` (firmware /
      loader / kernel / userspace split), `systemd-analyze blame`, `systemd-analyze
      critical-chain <unit>`, and `dmesg` timestamps (seconds since kernel start, so
      `dmesg -T` for wall clock). `ApplicationGateway` scaling **12 → 40 instances** pays this
      latency on every scale-out; 45 s of boot plus JVM warm-up is 45 s of the incident you were
      scaling to fix. `[DIAG]` `[CALC]`
3.1.10 **A container does not boot.** `runc` reads the OCI `config.json`, `clone()`s with the
       namespace flags, sets up the cgroup, `pivot_root`s onto the overlayfs, applies seccomp and
       capabilities, and `execve`s the entrypoint. There is no firmware, no bootloader, no
       `initramfs`, no `init` — which is precisely why the entrypoint inherits **PID 1 semantics**
       it was never written for. `[PROVE]` `[X-REF 19]`
3.1.11 `[TRAP]` **Trap:** "the JVM is PID 1, so it's fine." PID 1 in a namespace has **no default
       action** for signals it has not handled, and it must reap orphans. A Java process as PID 1
       that installed no `SIGTERM` handler ignores `docker stop` until the 10-second `SIGKILL`, and
       any `ProcessBuilder` grandchild it orphans becomes an unreapable zombie. Fixes:
       `--init`/`tini`, a `SIGTERM` shutdown hook, or `exec`-form `ENTRYPOINT` so the shell is not
       PID 1. `[TRAP]` `[X-REF 19]`
3.1.12 `[INCIDENT]` Symptom: an EKS node group replacement leaves `ApplicationGateway` at
       insufficient capacity for 4 minutes despite a 30-second `terminationGracePeriodSeconds`.
       Diagnosis: `systemd-analyze` on the new node shows 38 s to `multi-user.target`, of which
       19 s is `cloud-init` and 8 s is `containerd` pulling a 900 MB image; the JVM then takes
       26 s to pass its readiness probe. Root cause: the scale-out latency was never measured, so
       the HPA's reaction time was tuned against an imagined 10 s. Fix: a slimmer base image, image
       pre-pull via a DaemonSet, `-XX:TieredStopAtLevel=1` for start-up, and an HPA
       `stabilizationWindowSeconds` that matches reality. `[INCIDENT]` `[CALC]`

*(12 leaves)*

## §3.2 `task_struct` and the scheduler's data structures: from the CFS red-black tree to EEVDF

3.2.1 `[SOURCE]` **`struct task_struct`** (`include/linux/sched.h`) — the fields a diagnosis
      actually uses: `__state` (`TASK_RUNNING`/`INTERRUPTIBLE`/`UNINTERRUPTIBLE`), `on_rq`,
      `stack` (the **16 KiB** kernel stack, `THREAD_SIZE` = 4 pages on x86-64), `prio` /
      `static_prio` / `normal_prio` / `rt_priority`, `sched_class`, `se` (`struct sched_entity`),
      `dl` / `rt`, `mm` and `active_mm`, `cpus_ptr` / `nr_cpus_allowed`, `nvcsw` / `nivcsw` (the
      two numbers `/proc/<pid>/status` reports as `voluntary_ctxt_switches` and
      `nonvoluntary_ctxt_switches`), `utime` / `stime`, `pid` / `tgid`, `files`, `nsproxy`,
      `cgroups`, `signal` / `sighand`, `thread` (the arch register save area). `[SOURCE]`
      `[X-REF 11]`
3.2.2 `[SOURCE]` **`struct sched_entity`** is what the fair scheduler actually queues, and the
      same struct represents a *task group*: `load` (weight), `run_node` (`struct rb_node`),
      `on_rq`, `exec_start`, `sum_exec_runtime`, **`vruntime`**, `prev_sum_exec_runtime`, plus the
      EEVDF additions **`deadline`**, **`vlag`** and **`slice`**, and `my_q`/`cfs_rq` for the group
      case. The presence of `vlag`, `deadline` and `slice` in a tree you are reading is how you
      know you are on 6.6+. `[SOURCE]` `[VERSION-TRAP]`
3.2.3 `[SOURCE]` **`struct rq` and `struct cfs_rq`** (`kernel/sched/sched.h`): one `rq` per CPU
      holding `nr_running`, `curr`, `idle`, `clock`/`clock_task`, and per-class sub-queues. The
      `cfs_rq` holds `tasks_timeline` (an **`rb_root_cached`** — cached leftmost, so "find the next
      task" is O(1) once inserted), `min_vruntime`, `avg_vruntime`, `avg_load`, `nr_running` and
      `curr`. `[SOURCE]`
3.2.4 `[VERSION-TRAP]` **What CFS did, so you can say what changed.** CFS kept an RB-tree keyed by
      `vruntime` = accumulated runtime scaled by `NICE_0_LOAD / weight`, always picked the
      **leftmost** node, and computed a timeslice as `sched_latency_ns / nr_running`, floored at
      `sched_min_granularity_ns`. Preemption on wakeup was gated by `sched_wakeup_granularity_ns`.
      All three tunables are **gone** in 6.6+. An answer that computes a timeslice from
      `sched_latency_ns` is a pre-6.6 answer. `[VERSION-TRAP]` `[RESEARCH]`
3.2.5 `[PROVE]` **EEVDF's model, worked through.** Each task has an entitlement (its weighted share
      of the elapsed service) and an actual service; **`lag` = entitled − received**, so
      "a task with a positive lag is owed CPU time, while a negative lag means the task has
      exceeded its portion". A task is **eligible** iff `lag ≥ 0`, which in the implementation is
      the cheaper test `vruntime ≤ avg_vruntime` (`entity_eligible()` /
      `vruntime_eligible()` in `kernel/sched/fair.c`). Each task gets a **request** — a slice — and
      a **virtual deadline** = its eligible time plus that slice scaled by weight
      (`update_deadline()`). The pick is **the eligible task with the earliest virtual deadline**,
      found by `pick_eevdf()` walking the augmented tree rather than simply taking the leftmost
      node. `[PROVE]` `[SOURCE]`
3.2.6 `[SYSCTL]` **The tunables that exist now.** `/sys/kernel/debug/sched/base_slice_ns`
      (**750,000 ns**) is the default request size; `/sys/kernel/debug/sched/migration_cost_ns`
      (**500,000**), `.../nr_migrate`, `.../features` (the `SCHED_FEAT` bitmap, e.g.
      `PLACE_LAG`, `RUN_TO_PARITY`, `NEXT_BUDDY`), and `sched_setattr(2)` with `sched_runtime` as a
      **per-task slice request** — the supported way for a latency-sensitive
      `ClientRestrictions` thread to ask for a shorter slice and therefore an earlier deadline.
      `[SYSCTL]` `[SYSCALL]` `[RESEARCH]`
3.2.7 `[CALC]` **Nice, weight and `cpu.weight` are one mechanism.** `sched_prio_to_weight[]` maps
      nice −20…+19 to weights 88761…15, with **nice 0 = 1024** and roughly a **1.25× step per
      level** — so one nice level is about a **10%** share change against a single competitor. A
      cgroup's `cpu.weight` (default **100**, range 1–10000) is converted into the same `load` field
      on the group's `sched_entity`, which is why `cpu.weight` and `nice` cannot be reasoned about
      separately. `[CALC]` `[SOURCE]`
3.2.8 `[TABLE]` **Scheduling classes in strict priority order**, because a lower class never runs
      while a higher one is runnable: `stop_sched_class` (CPU hotplug/migration), `dl_sched_class`
      (**`SCHED_DEADLINE`** — runtime/deadline/period admission-controlled), `rt_sched_class`
      (`SCHED_FIFO`, `SCHED_RR`, priorities 1–99), `fair_sched_class` (`SCHED_OTHER`, `SCHED_BATCH`,
      `SCHED_IDLE`), `idle_sched_class`. `pick_next_task()` iterates `for_each_class`.
      `kernel/sched/rt.c` throttles RT to `sched_rt_runtime_us` of `sched_rt_period_us` so a
      runaway `SCHED_FIFO` thread cannot wedge the box. `[TABLE]` `[RESEARCH]`
3.2.9 **Group scheduling is the whole reason containers work.** `struct task_group` owns a
      `cfs_rq` *and* a `sched_entity` per CPU, so the tree is hierarchical: the top-level pick
      selects a group entity, then recurses into that group's `cfs_rq`. Arbitration between two
      containers is therefore the same arithmetic as arbitration between two threads, one level up.
      `[PROVE]` `[X-REF 19]`
3.2.10 **CFS bandwidth control (the throttling mechanism).** `struct cfs_bandwidth` holds `quota`,
       `period` and `runtime`; `sched_cfs_period_timer` refills the pool each period, and each CPU
       draws a **slice** from it (`/sys/kernel/debug/sched/cfs_bandwidth_slice_us`, **5000** µs) into
       `cfs_rq->runtime_remaining`. When a `cfs_rq` cannot draw, `throttle_cfs_rq()` dequeues the
       whole group until the next period. Two consequences: throttling is **all-or-nothing within a
       period**, and per-CPU slice hoarding means a many-threaded JVM can be throttled while its
       quota is nominally unspent. `[SOURCE]` `[NUM]` `[X-REF 11]`
3.2.11 **Load balancing and why migration is not free.** `sched_domain`/`sched_group` form a
       hierarchy (SMT → MC/LLC → NUMA node → system) with per-level `SD_BALANCE_NEWIDLE`,
       `SD_BALANCE_FORK`, `SD_BALANCE_EXEC` and `SD_SHARE_PKG_RESOURCES` flags.
       `run_rebalance_domains()` runs in `SCHED_SOFTIRQ`; `newidle_balance()` pulls on the way to
       idle. `migration_cost_ns` (**500 µs**) encodes the cache-and-TLB refill a migrated task pays,
       and is why `task_hot()` refuses to move a recently-run task. Pin with
       `sched_setaffinity`/`taskset`/`cpuset.cpus` only when you have measured the migration rate.
       `[NUM]` `[CALC]`
3.2.12 **The wakeup path**, since that is where latency is decided: `try_to_wake_up()` →
       `select_task_rq_fair()` → `wake_affine_idle`/`wake_affine_weight` (place near the waker for
       cache locality) or `find_idlest_cpu` → `enqueue_task_fair` with lag-preserving placement
       (`PLACE_LAG`) → `check_preempt_curr` decides whether the woken task preempts immediately.
       A `FundsLedger` thread woken by an I/O completion on a busy socket is competing here, and the
       delay lands in `/proc/<pid>/schedstat` field 2. `[FLOW]` `[PROC]`
3.2.13 `[DIAG]` **Proving a scheduler diagnosis rather than asserting one:**
       `/proc/<pid>/schedstat` (on-CPU ns, **run-queue wait ns**, timeslices),
       `/proc/<pid>/sched` (`se.sum_exec_runtime`, `se.statistics.wait_sum`, `se.vlag`,
       `nr_switches`, `nr_involuntary_switches`), `/proc/schedstat` per-CPU, `perf sched record` +
       `perf sched latency`, `runqlat`/`runqslower` from bcc, and `/proc/pressure/cpu`. A **12 ms**
       run-queue wait against a **30 ms** `ClientRestrictions` budget is a number, not an opinion.
       `[DIAG]` `[PROC]` `[CALC]`

*(13 leaves)*

## §3.3 The syscall entry path: `syscall` instruction to handler and back

3.3.1 **Setup at boot:** `syscall_init()` (`arch/x86/kernel/cpu/common.c`) writes
      `MSR_LSTAR` = `entry_SYSCALL_64`, `MSR_STAR` (the CS/SS selectors for the transition),
      `MSR_SYSCALL_MASK` (the `RFLAGS` bits cleared on entry — notably `IF`, so interrupts are off
      for the first instructions), and sets `EFER.SCE` to enable the instruction at all. Nothing
      per-syscall is configured; there is one entry point for all of them. `[SOURCE]`
3.3.2 `[FLOW]` **`entry_SYSCALL_64` in `arch/x86/entry/entry_64.S`**, in order: `swapgs` (swap the
      user `GS` base for the per-CPU kernel one) → switch to the kernel stack from
      `PER_CPU_VAR(cpu_current_top_of_stack)` → push a full **`struct pt_regs`** via
      `PUSH_AND_CLEAR_REGS` (clearing registers is a Spectre-era hardening step) →
      `call do_syscall_64` with `pt_regs` and the syscall number. `[FLOW]` `[SOURCE]`
3.3.3 **`struct pt_regs` and why `orig_ax` exists.** The return value overwrites `rax`, so the
      original syscall number is saved separately in `orig_ax` — which is what makes syscall
      **restart** (`ERESTARTSYS` after a signal) and `ptrace`-based inspection possible at all.
      `[PROVE]` `[SOURCE]`
3.3.4 **Dispatch:** `do_syscall_64()` (`arch/x86/entry/common.c`) calls
      `syscall_enter_from_user_mode()` (context tracking, audit, seccomp), then indexes
      `sys_call_table[nr]` after masking `nr` — the table generated from
      `arch/x86/entry/syscalls/syscall_64.tbl`, whose entries are the `__x64_sys_*` wrappers
      produced by the `SYSCALL_DEFINEn` macro. An out-of-range number returns `-ENOSYS`, not a
      crash. `[SOURCE]` `[SYSCALL]`
3.3.5 `[FLOW]` **The return path is where everything else happens.**
      `syscall_exit_to_user_mode()` → `exit_to_user_mode_loop()` inspects
      `thread_info->flags`: `TIF_NEED_RESCHED` → `schedule()` (this is where a preemption you
      attributed to "the scheduler" actually lands), `TIF_SIGPENDING` → signal delivery (§3.14),
      `TIF_NOTIFY_RESUME` → deferred work, `TIF_UPROBE`. Only then does it return to userspace.
      **A task that never returns to userspace never runs any of this** — the mechanical reason a
      `D`-state task ignores `SIGKILL`. `[FLOW]` `[PROVE]`
3.3.6 **`sysretq` fast path versus `IRET` slow path.** `sysretq` restores `RIP` from `rcx` and
      `RFLAGS` from `r11` in a few cycles, but is only legal when the register state is unmodified
      and the return address is canonical. If `ptrace`, a signal frame or a 32-bit compat case
      changed `pt_regs`, the kernel must use `IRET`, which is materially slower. This is one reason
      an `strace`d process is not merely "traced" but *slower on every syscall*. `[PROVE]`
      `[NUM]`
3.3.7 **KPTI on the entry path.** With Meltdown mitigation, the user page table contains only a
      trampoline, so entry executes `SWITCH_TO_KERNEL_CR3` (a `CR3` write) onto a per-CPU trampoline
      stack before it can touch kernel data, and exit reverses it. **PCID** keeps the write from
      flushing the whole TLB. Check `/sys/devices/system/cpu/vulnerabilities/meltdown` and `pcid`
      in `/proc/cpuinfo`; `nopti` on the command line disables it. `[SOURCE]` `[PROC]`
3.3.8 `[CALC]` **The mitigation bill, quantified where it lands.** Retpoline or eIBRS on the entry
      path, `MDS`/`L1TF` buffer clears, and SSBD each add tens to low hundreds of nanoseconds, which
      is why a trivial syscall moved from **~50–100 ns** to **~250–600 ns**. At **13,600
      writes/sec**, one syscall per write is 13,600 × 500 ns ≈ **6.8 ms/sec** of pure entry
      overhead per instance — negligible; at one syscall per 180-byte row inside a 19.8M-row day it
      is not. The design variable is always **count**. `[CALC]` `[NUM]`
3.3.9 **seccomp runs here, per syscall.** `__secure_computing()` is called from
      `syscall_trace_enter` before dispatch, executing the installed cBPF/eBPF filter over
      `struct seccomp_data` (`nr`, `arch`, `instruction_pointer`, `args[6]`). Cost is proportional
      to the filter's instruction count, and filters are **cumulative** — a container runtime
      profile plus a Kubernetes `RuntimeDefault` profile plus a library's own filter all run.
      `Seccomp:` and `Seccomp_filters:` in `/proc/<pid>/status`. `[SOURCE]` `[PROC]`
      `[X-REF 13]`
3.3.10 `[TRAP]` **Trap:** "auditd is free because we only audit `execve`." A rule like
       `-a always,exit -F arch=b64 -S all` (or an over-broad `-S openat`) adds a `TIF_SYSCALL_AUDIT`
       check plus a record allocation on **every** matching syscall, and `auditd` backlog exhaustion
       (`audit_backlog_limit`) can put processes to sleep. Check with `auditctl -l` and
       `auditctl -s` (`backlog`, `lost`) before blaming the application. `[TRAP]` `[DIAG]`
3.3.11 **The vDSO as the syscall that isn't.** `arch/x86/entry/vdso/` builds a shared object mapped
       into every process as `[vdso]`, reading a kernel-updated `vdso_data` page mapped read-only as
       `[vvar]`. `clock_gettime(CLOCK_MONOTONIC)` becomes a ring-3 TSC read plus a multiply —
       **~20–25 ns**. This only holds when the clocksource supports it: read
       `/sys/devices/system/clocksource/clocksource0/current_clocksource`, and if it says `xen`
       rather than `tsc` or `kvm-clock`, `System.nanoTime()` degrades into a real syscall and any
       instrumented hot path collapses. `[PROC]` `[NUM]` `[TRAP]`
3.3.12 `[DIAG]` **Measuring the entry path for real:** a `getpid()` loop for the floor,
       `perf stat -e syscalls:sys_enter_write -p <pid>` for a count,
       `perf trace -s -p <pid>` for the per-name distribution,
       `bpftrace -e 'tracepoint:raw_syscalls:sys_enter /pid == $1/ { @[args->id] = count(); }'` for
       production-safe attribution, and `/proc/<pid>/stat`'s `stime` against `utime` to see whether
       the cost is even in the kernel. `[DIAG]` `[BUILD]`

*(12 leaves)*

## §3.4 Address translation in detail: four- and five-level paging, PCID, TLB shootdown

3.4.1 **`CR3` is a physical frame number plus a PCID.** `switch_mm_irqs_off()`
      (`arch/x86/mm/tlb.c`) writes it on every context switch to a task with a different `mm`;
      switching between two threads of the same JVM writes nothing, which is one concrete reason
      threads are cheaper than processes. `mm_struct->pgd` is the virtual address of that table.
      `[SOURCE]` `[PROVE]`
3.4.2 `[SOURCE]` **PTE bits** (`arch/x86/include/asm/pgtable_types.h`), because reclaim, dirty
      tracking and COW are all implemented in them: bit 0 `P` (present), 1 `RW`, 2 `US`, 3 `PWT`,
      4 `PCD`, **5 `A` (accessed)**, **6 `D` (dirty)**, 7 `PSE` (this entry maps a huge page),
      8 `G` (global), 9–11 software-usable, 12–51 the PFN, **63 `NX`**. The `A` bit is what LRU
      aging clears and re-reads; the `D` bit is what writeback consults; clearing `RW` is how COW
      and GC write barriers are armed. `[SOURCE]`
3.4.3 `[CALC]` **The walk, and where huge pages short-circuit it.** 4-level: PGD[47:39] →
      PUD[38:30] → PMD[29:21] → PTE[20:12] → offset[11:0]. A PMD entry with `PSE` set maps a
      **2 MiB** page and the walk stops one level early; a PUD entry with `PSE` maps **1 GiB**.
      Five-level paging inserts **P4D** at bits [56:48] under `CONFIG_X86_5LEVEL`, advertised as
      `la57` in `/proc/cpuinfo`. `[CALC]` `[NUM]`
3.4.4 `[TRAP]` **The 5-level compatibility rule that saves the JVM.** On an LA57 kernel, `mmap`
      still returns addresses **below 47 bits** unless the caller passes an explicit high hint,
      because code that packs data into the top pointer bits — historically including JVM
      compressed-oops and `Unsafe` tricks — would break. So "we upgraded to 5-level paging and the
      heap moved" is not a thing that happens by default. `[TRAP]` `[RESEARCH]`
3.4.5 **PCID / ASID tagging.** Without PCID every `CR3` write flushes the TLB; with it, entries
      carry a 12-bit context id and survive the switch. Linux does **not** use one PCID per
      process — it maps `mm`s onto a small per-CPU set (`TLB_NR_DYN_ASIDS`, **6**) tracked in
      `cpu_tlbstate`, recycling the oldest. `INVPCID` invalidates selectively. Consequence: on a
      host running more than a handful of active address spaces per CPU, PCID stops helping.
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.6 **`_PAGE_GLOBAL` and what KPTI costs.** Kernel text and data are normally marked global so
      they survive `CR3` writes. KPTI removes the global bit from most kernel mappings (the user
      table has only a trampoline), so the kernel's own working set must be re-walked more often —
      the mechanism behind a syscall-heavy workload losing double-digit percentages on a mitigated
      kernel. `[PROVE]` `[X-REF 11]`
3.4.7 `[FLOW]` **TLB shootdown, step by step:** (1) a thread changes a mapping — `munmap`,
      `mprotect`, `madvise(MADV_DONTNEED)`, COW break, page migration, reclaim; (2) the local TLB is
      invalidated with `INVLPG` or an `INVPCID`; (3) because other CPUs may have cached the same
      translation, `flush_tlb_mm_range()` sends an **IPI** to every CPU in `mm_cpumask(mm)`;
      (4) each target runs `flush_tlb_func()` in interrupt context; (5) the initiator waits for
      them. The cost scales with **the number of CPUs currently running that address space**, which
      for a 200-thread JVM on a 64-vCPU node is most of them. `[FLOW]` `[SOURCE]`
3.4.8 `[CALC]` **The batching threshold.** `tlb_single_page_flush_ceiling` (**33**) is the number of
      pages above which the kernel stops issuing per-page `INVLPG` and flushes the whole (non-global)
      TLB instead — cheaper to issue, more expensive afterwards. So unmapping 32 pages and unmapping
      3,200 pages are qualitatively different events, and a GC that uncommits in small chunks can be
      worse than one that uncommits in large ones. `[CALC]` `[NUM]` `[RESEARCH]`
3.4.9 **Why this section matters to a JVM specifically.** Every `MADV_DONTNEED` heap uncommit, every
      ZGC/Shenandoah remap, every `mprotect` of a safepoint polling page (§3.18) and every
      `mprotect` of the code cache is a potential shootdown storm across every vCPU the process
      occupies. `/proc/vmstat`'s `nr_tlb_remote_flush`, `nr_tlb_remote_flush_received`,
      `nr_tlb_local_flush_all` and `/proc/interrupts`' `TLB` row are the counters that prove it.
      `[PROC]` `[X-REF 06]`
3.4.10 `[VERSION-TRAP]` **`mmap_lock` and per-VMA locking.** The per-`mm` `mmap_lock` (renamed from
       `mmap_sem` in 5.8) serialised every VMA change against every page fault; **per-VMA locks**
       (6.4+) let the fault path take a lightweight per-VMA lock via `lock_vma_under_rcu()` and only
       fall back to the write lock for structural changes. Reasoning about "the mmap semaphore is the
       bottleneck for a many-threaded JVM" is now version-scoped. `[VERSION-TRAP]` `[RESEARCH]`
3.4.11 **NUMA is address translation's other half.** `/sys/devices/system/node/node*/`,
       `numactl --hardware`, and the **first-touch** policy: a page lands on the node of the thread
       that first writes it, so a JVM that allocates its 12 GB heap on one thread and reads it from
       all of them pays remote-memory latency forever. Levers: `-XX:+UseNUMA` (G1/Parallel),
       `numactl --interleave=all`, `kernel.numa_balancing` (AutoNUMA page migration, which is itself
       a shootdown source), `vm.zone_reclaim_mode`. Measure with `numastat -p <pid>` and
       `perf stat -e node-load-misses`. `[PROC]` `[CALC]`

*(11 leaves)*

## §3.5 The page-fault handler path

3.5.1 **It starts as a CPU exception, vector 14.** The CPU pushes an **error code** and puts the
      faulting *linear* address in **`CR2`**; `DEFINE_IDTENTRY_RAW_ERRORCODE(exc_page_fault)` in
      `arch/x86/mm/fault.c` reads `CR2` as its very first act, because any nested fault would
      clobber it. `[SOURCE]` `[PROVE]`
3.5.2 `[TABLE]` **The error-code bits are the diagnosis:** bit 0 `P` (0 = not present → demand
      paging/swap; 1 = present → a permission problem), 1 `W/R` (write attempt → COW or read-only
      mapping), 2 `U/S` (userspace or kernel), 3 `RSVD` (a corrupt page table — a hardware or kernel
      bug), 4 `I/D` (instruction fetch → NX violation, i.e. executing data),
      5 `PK` (protection keys), 6 `SS` (shadow stack). An `hs_err` log's fault address plus these
      bits distinguishes "GC write barrier" from "JIT bug" from "executing a corrupted buffer".
      `[TABLE]` `[DIAG]`
3.5.3 `[FLOW]` **`do_user_addr_fault()`:** find the VMA — `lock_vma_under_rcu()` on the fast path
      (6.4+), else `mmap_read_lock()` + `find_vma()`; no VMA → `SIGSEGV` (or stack expansion if the
      address is just below `[stack]`); VMA found but `vma->vm_flags` forbids the access →
      `SIGSEGV`; otherwise `handle_mm_fault()`. `[FLOW]` `[SOURCE]`
3.5.4 `[FLOW]` **`handle_mm_fault()` → `__handle_mm_fault()` → `handle_pte_fault()`**, allocating
      each missing level of the page table on the way down, then branching:
      `do_anonymous_page()` (untouched anonymous memory), `do_fault()` (file-backed, via
      `vma->vm_ops->fault`), `do_swap_page()` (the PTE holds a swap entry — this is a **major**
      fault), `do_wp_page()` (write to a read-only present page — COW), `do_numa_page()` (AutoNUMA
      migration). Every fault your JVM takes is exactly one of these five. `[FLOW]` `[SOURCE]`
      `[TABLE]`
3.5.5 **`do_anonymous_page` and the zero page.** A *read* fault on untouched anonymous memory maps
      the shared read-only zero page — no frame allocated. A *write* fault allocates a zeroed frame
      from the buddy allocator, which is why `-Xms12g` costs address space at start and RSS only as
      the heap is written, and why `-XX:+AlwaysPreTouch` (a byte written per page) is the thing that
      converts it. `[PROVE]` `[X-REF 11]`
3.5.6 **`filemap_fault()` in `mm/filemap.c` is where "major fault" is defined.** It looks the folio
      up in the page cache; on a hit it may still call `do_async_mmap_readahead()`; on a miss it
      calls `do_sync_mmap_readahead()`, submits I/O, waits, and sets **`VM_FAULT_MAJOR`** — and
      *that flag* is what increments `majflt` and `pgmajfault`. So "major fault" means precisely
      "this fault waited for a block device", nothing more. `[SOURCE]` `[PROVE]`
3.5.7 **Fault-around** amortises minor faults: `do_fault_around()` maps up to
      `fault_around_bytes` (`/sys/kernel/debug/fault_around_bytes`, **65536** — 16 pages) worth of
      already-cached neighbouring folios in a single fault. This is why a `MappedByteBuffer` walk
      over a cached file takes far fewer faults than pages, and why fault counts alone understate
      how much was mapped. `[NUM]` `[PROC]`
3.5.8 `[PROVE]` **THP faults are where a fault becomes a millisecond.**
      `create_huge_pmd()` → `do_huge_pmd_anonymous_page()` tries to allocate an **order-9**
      (2 MiB) folio. Under `defrag=always` that allocation may enter **direct compaction**
      (`__alloc_pages_slowpath` → `try_to_compact_pages`), migrating pages to assemble a contiguous
      block, *inside the faulting thread*. Under `defrag=defer` the kernel instead "wake[s] kswapd
      in the background to reclaim pages and wake kcompactd to compact memory so that THP is
      available in the near future" and falls back to 4 KiB now; `defer+madvise` does the deferred
      thing except for `MADV_HUGEPAGE` regions. This one setting decides whether THP costs you a
      p99 or buys you a TLB. `[PROVE]` `[SOURCE]` `[SYSCTL]`
3.5.9 **`do_wp_page` and the refcount-1 shortcut.** If the faulting process is the *only* holder of
      the frame, the kernel reuses it in place instead of copying — so COW faults after a `fork`
      whose peer has already exited are nearly free, and a COW cost estimate must account for
      sharing, not just for pages written. `wp_page_copy()` is the copying path. `[SOURCE]`
      `[CALC]`
3.5.10 **`VM_FAULT_RETRY` and why a fault can happen twice.** When a fault must sleep (read from
       disk, wait on a lock), the handler drops `mmap_lock`, returns `VM_FAULT_RETRY`, and the whole
       fault is re-taken afterwards. So fault *counters* can exceed distinct faulting addresses, and
       a fault is not an atomic event you can time from the outside without care. The other return
       codes: `VM_FAULT_OOM`, `VM_FAULT_SIGBUS`, `VM_FAULT_SIGSEGV`, `VM_FAULT_FALLBACK` (THP
       declined), `VM_FAULT_HWPOISON`. `[SOURCE]` `[TRAP]`
3.5.11 **Kernel-address faults and the exception table.** `copy_to_user()` handed a bad pointer must
       return `-EFAULT`, not panic: the faulting instruction is registered in `__ex_table`, and
       `fixup_exception()` redirects execution to a recovery label. When no fixup exists you get
       `BUG: unable to handle page fault for address …` and an oops — which is how you tell a kernel
       bug from a userspace one in `dmesg`. `[SOURCE]` `[DIAG]`
3.5.12 `[DIAG]` **Measuring the fault path instead of guessing at it:**
       `/proc/<pid>/stat` fields **10 (`minflt`)** and **12 (`majflt`)**;
       `/proc/vmstat`'s `pgfault`, `pgmajfault`, `pgsteal_*`, `thp_fault_alloc`,
       `thp_fault_fallback`, `compact_stall`; `perf stat -e page-faults,major-faults -p <pid>`;
       `perf trace -F maj`;
       `bpftrace -e 'kprobe:handle_mm_fault { @s[tid] = nsecs; } kretprobe:handle_mm_fault /@s[tid]/ { @us = hist((nsecs - @s[tid]) / 1000); delete(@s[tid]); }'`
       for a fault-latency histogram. `thp_fault_fallback` rising with `compact_stall` is the
       compaction story, proved. `[DIAG]` `[BUILD]` `[PROC]`

*(12 leaves)*

## §3.6 Memory reclaim internals: LRU lists, MGLRU, `kswapd`, direct reclaim, PSI

3.6.1 `[SOURCE]` **Nodes, zones and watermarks are the substrate.** `struct pglist_data` per NUMA
      node holds `struct zone`s (`DMA`, `DMA32`, `Normal`, `Movable`), each with
      `_watermark[WMARK_MIN|LOW|HIGH]`, `free_area[]`, `lowmem_reserve[]` and its own `lruvec`.
      `/proc/zoneinfo` prints every one of these, and it is the only place to see *which* zone is
      short. `[SOURCE]` `[PROC]`
3.6.2 **The buddy allocator and why order matters.** `free_area[order]` for orders 0–10 (4 KiB →
      4 MiB); `/proc/buddyinfo` shows the free-list length per order. `__alloc_pages()`
      (`mm/page_alloc.c`) tries `get_page_from_freelist()` with `ALLOC_WMARK_LOW` first, then falls
      into `__alloc_pages_slowpath()` — reclaim, compaction, retry, OOM. A single order-0
      allocation almost never fails; an order-9 THP allocation fails routinely on a fragmented host
      with gigabytes free. `[SOURCE]` `[CALC]`
3.6.3 `[TABLE]` **GFP flags are the caller's latency policy**, and reading them tells you whether a
      stall is possible: `__GFP_DIRECT_RECLAIM` (may block and reclaim in-context),
      `__GFP_KSWAPD_RECLAIM` (only wake the background thread), `__GFP_IO`/`__GFP_FS` (may start
      I/O / may recurse into the filesystem), `__GFP_HIGH` (may dip into reserves), `__GFP_NOFAIL`,
      `__GFP_NORETRY`, `__GFP_THISNODE`, `__GFP_MOVABLE`. `GFP_KERNEL` blocks; `GFP_ATOMIC` cannot
      and therefore fails instead. `[TABLE]` `[SOURCE]`
3.6.4 **`kswapd`: one kthread per node.** `balance_pgdat()` wakes when free falls below `low`, and
      reclaims until free exceeds `high` plus `watermark_boost`. It is *asynchronous*, so a healthy
      box reclaims constantly at no application cost. `[kswapd0]` pinned at 100% CPU is therefore
      not a curiosity — it is the statement "reclaim cannot keep up", and the next thing that
      happens is direct reclaim. `[PROC]` `[DIAG]`
3.6.5 `[PROVE]` **Direct reclaim is the stall.** `__alloc_pages_slowpath` →
      `__alloc_pages_direct_reclaim` → `try_to_free_pages()` → `shrink_zones()` → `shrink_node()`,
      running **in the allocating thread**, scanning LRU lists and possibly writing pages, before
      `malloc`/a page fault/a GC region commit returns. `/proc/vmstat`'s `allocstall_normal`,
      `allocstall_movable`, `allocstall_dma32` count entries; `pgscan_kswapd` versus `pgscan_direct`
      and `pgsteal_kswapd` versus `pgsteal_direct` tell you which regime the box is in. This is the
      single most useful pair of counters in memory triage. `[PROVE]` `[PROC]`
3.6.6 `[SOURCE]` **Classic LRU mechanics.** `shrink_lruvec()` calls `get_scan_count()` to split
      effort between anon and file using `vm.swappiness` and measured refault cost, then
      `shrink_inactive_list()` (`isolate_lru_folios()` → `shrink_folio_list()`) reclaims from the
      inactive tail while `shrink_active_list()` demotes. Second-chance comes from the PTE
      **accessed** bit via `folio_referenced()`. The API is `folio`-based in 6.x — code and articles
      talking about `struct page` LRU functions predate 5.16. `[SOURCE]` `[VERSION-TRAP]`
3.6.7 **What is cheap, expensive and impossible to reclaim.** Clean file-backed folio: unmap and
      drop, essentially free. Dirty file-backed: must be written first, so reclaim becomes I/O
      latency. Anonymous: needs **swap**, or cannot be reclaimed at all — which on a swapless
      `FundsLedger` host means a 12 GB heap is 12 GB of unreclaimable memory and the only remaining
      lever is the OOM killer. Locked (`mlock`, hugetlb) and kernel-stack pages: never.
      `[TABLE]` `[PROVE]`
3.6.8 `[VERSION-TRAP]` **MGLRU, mechanically different.** Instead of two lists it keeps numbered
      generations per `lruvec` (`struct lru_gen_folio`, `min_seq`/`max_seq`), ages by **walking page
      tables** (`walk_page_range`, cheap and sequential) rather than reverse-mapping each folio, and
      evicts from `min_seq`; refault feedback sorts folios into tiers. Controls:
      `/sys/kernel/mm/lru_gen/enabled` (bit `0x0001` main switch, `0x0002` leaf accessed-bit
      clearing, `0x0004` non-leaf), `min_ttl_ms` (default **0**), and `/sys/kernel/debug/lru_gen`
      for the generation table. Any reasoning about "the active and inactive lists" is conditional
      on this being **off**. `[VERSION-TRAP]` `[PROC]` `[RESEARCH]`
3.6.9 `[PROVE]` **Refault detection is how the kernel knows the cache was too small.** When a page
      cache folio is evicted, a **shadow entry** encoding its eviction timestamp stays in the
      `address_space` xarray. If the same offset is read back, the kernel compares the eviction
      distance against the current list size and decides whether this was a genuine working-set
      overflow or a one-off. That is exactly what `workingset_refault_file` /
      `workingset_refault_anon` in `memory.stat` report — the difference between "cache miss" and
      "thrashing". `[PROVE]` `[PROC]`
3.6.10 **Shrinkers reclaim the kernel's own caches.** `struct shrinker` with `count_objects`/
       `scan_objects`, registered by the dentry cache, inode cache, XFS buffer cache, and dozens
       more; driven from `shrink_slab()` in the same reclaim loop. `vm.vfs_cache_pressure` (**100**)
       scales dentry/inode pressure relative to page cache. Inspect with `slabtop -s c`,
       `/proc/slabinfo` and `SReclaimable`/`SUnreclaim` in `/proc/meminfo`. A box whose "memory
       leak" is `dentry` slab is a negative-dentry or open-file problem, not an application one.
       `[SYSCTL]` `[DIAG]`
3.6.11 **Compaction is a separate mechanism from reclaim** and is the one THP depends on.
       `compact_zone()` migrates movable folios to assemble contiguous blocks; `kcompactd<N>` does it
       in the background, and `try_to_compact_pages()` does it synchronously inside an allocation.
       Counters: `compact_stall` (a thread was stalled in compaction), `compact_fail`,
       `compact_success`, `compact_migrate_scanned`, `compact_free_scanned`,
       `/sys/kernel/debug/extfrag/extfrag_index`. `echo 1 > /proc/sys/vm/compact_memory` forces it —
       a diagnostic, not a fix. `[PROC]` `[NUM]`
3.6.12 `[SOURCE]` **Where PSI's numbers come from.** `psi_memstall_enter()`/`psi_memstall_leave()`
       (`kernel/sched/psi.c`) bracket exactly the paths that constitute memory pressure: direct
       reclaim, compaction stalls, `memory.high` throttling, page-fault waits on thrashed pages and
       writeback waits. **"some"** is "the share of time in which at least some tasks are stalled on
       a given resource"; **"full"** is "the share of time in which all non-idle tasks are stalled on
       a given resource simultaneously"; `total=` is "the total absolute stall time (in us)". The
       per-cgroup files `memory.pressure`, `cpu.pressure`, `io.pressure` use the identical format,
       and a trigger written as `some 150000 1000000` makes `poll()` on the file fire at 150 ms of
       stall per second. `[SOURCE]` `[PROC]` `[BUILD]`
3.6.13 `[DIAG]` **The reclaim triage sequence, in order:** `vmstat 1` (`si`/`so` non-zero → swap;
       `free` low with `buff/cache` high → normal; high `sy` with high `cs` → contention) →
       `/proc/pressure/memory` `full avg10` → `/proc/vmstat` `pgscan_direct` vs `pgscan_kswapd` →
       `memory.stat`'s `workingset_refault_*` and `pgscan`/`pgsteal` split → `thp_fault_fallback`
       and `compact_stall` → `sar -B` for the history you did not capture live. Each step either
       exonerates reclaim or names the mechanism. `[DIAG]` `[FLOW]` `[PROC]`

*(13 leaves)*

## §3.7 The OOM killer's selection algorithm

3.7.1 **Three entry points, three different candidate sets.** (a) A global allocation that survived
      reclaim and compaction and still failed: `__alloc_pages_may_oom()` → `out_of_memory()`, with
      every task on the node as a candidate. (b) A cgroup hitting `memory.max` with nothing left to
      reclaim: `mem_cgroup_out_of_memory()`, with only that cgroup's tasks as candidates. (c) The
      administrator: `sysrq-f`. Which entry point fired is printed in the `dmesg` record as the
      **constraint** (`CONSTRAINT_NONE` vs `CONSTRAINT_MEMCG`). `[SOURCE]` `[TABLE]`
3.7.2 `[SOURCE]` **`oom_badness()`, quoted from `mm/oom_kill.c` and read line by line:**

      ```c
      long oom_badness(struct task_struct *p, unsigned long totalpages)
      {
              long points;
              long adj;

              if (oom_unkillable_task(p))
                      return LONG_MIN;
              p = find_lock_task_mm(p);
              if (!p)
                      return LONG_MIN;
              adj = (long)p->signal->oom_score_adj;
              if (adj == OOM_SCORE_ADJ_MIN ||
                              test_bit(MMF_OOM_SKIP, &p->mm->flags) ||
                              in_vfork(p)) {
                      task_unlock(p);
                      return LONG_MIN;
              }
              points = get_mm_rss(p->mm) + get_mm_counter(p->mm, MM_SWAPENTS) +
                      mm_pgtables_bytes(p->mm) / PAGE_SIZE;
              task_unlock(p);
              adj *= totalpages / 1000;
              points += adj;
              return points;
      }
      ```

      Its own comment states the design: "The heuristic for determining which task to kill is made
      to be as simple and predictable as possible. The goal is to return the highest value for the
      task consuming the most memory to avoid subsequent oom failures." Note what the score is
      **not**: it has no notion of importance, age, restart cost or who leaked. `[SOURCE]`
      `[PROVE]`
3.7.3 `[CALC]` **The formula in units.** `points` is in **pages** and equals `RSS + swap entries +
      page-table bytes / PAGE_SIZE`. `oom_score_adj` (range **−1000 … +1000**,
      `/proc/<pid>/oom_score_adj`) is scaled by `totalpages / 1000`, i.e. **each adj point is 0.1%
      of the machine**, then added. So on a 64 GB host `oom_score_adj=+100` adds
      `100 × 16,777,216/1000 ≈ 1.68M` pages ≈ **6.4 GB** of virtual badness — enough to make a
      100 MB sidecar outscore a 6 GB JVM. `OOM_SCORE_ADJ_MIN` (**−1000**) returns `LONG_MIN`, which
      is genuine immunity, not merely a low score. `[CALC]` `[NUM]` `[PROC]`
3.7.4 `[CALC]` **Why the JVM is always the biggest scorer on its host.** A `FundsLedger` instance
      with a **12 GB** heap fully touched is ~3.1M RSS pages plus ~24 MiB of page tables
      (~6,100 pages) ≈ **3.15M points**. A log-shipping sidecar at 60 MB is ~15,400 points. The
      ratio is **~200:1**, so the kernel kills the JVM regardless of which process's growth caused
      the shortage. The only lever is `oom_score_adj`, and in Kubernetes **the pod spec sets it from
      the QoS class** — Guaranteed ≈ **−997**, BestEffort **1000**, Burstable scaled by
      request/capacity. Your resource requests, not your leak, decide who dies. `[CALC]`
      `[X-REF 19]` `[RESEARCH]`
3.7.5 **Selection and exclusion.** `select_bad_process()` iterates candidates through
      `oom_evaluate_task()`, keeping the maximum; `oom_unkillable_task()` excludes init (PID 1 in the
      root namespace) and kernel threads; `MMF_OOM_SKIP` excludes a task whose memory has already
      been reaped; `in_vfork()` excludes a task sharing its parent's mm. `oom_kill_process()` then
      sends `SIGKILL` and, if the victim is a thread group, kills the whole group.
      `[SOURCE]`
3.7.6 **The `oom_reaper` exists because the victim might be stuck.** A task killed while in `D`
      state cannot exit, so its memory is never freed and the OOM path can livelock. The
      `[oom_reaper]` kthread asynchronously tears down the victim's address space (skipping
      `VM_LOCKED` and shared regions), sets `MMF_OOM_SKIP` so it is not chosen again, and lets
      progress resume. `[PROVE]` `[SOURCE]`
3.7.7 `[PROVE]` **A cgroup-scoped kill picks differently, and this surprises people.** Under
      `memory.max`, candidates are restricted to that cgroup's tasks, `totalpages` is the cgroup's
      limit rather than the machine's, and the largest process on the *host* is irrelevant. So the
      same leak produces a different victim depending on whether the limit hit was the pod's or the
      node's — and a pod with a 2 GB limit can be OOM-killed on a node with 40 GB free.
      `[PROVE]` `[TRAP]`
3.7.8 **`memory.oom.group` is the setting almost nobody sets and almost everybody wants.** Default
      `0`; set to `1` it treats the cgroup as an indivisible unit so **all** tasks are killed
      together. Without it, a multi-process container can have its helper killed, leaving a JVM
      running against a dead sidecar — a half-dead pod that passes liveness checks.
      `[SYSCTL]` `[TRAP]`
3.7.9 `[DIAG]` **Reading the whole `dmesg` OOM record**, which has four parts, not one: (1) the
      invocation line naming the allocating task, its `gfp_mask`, `order` and `oom_score_adj`;
      (2) the `Mem-Info` block (free, per-zone free, `active_anon`/`inactive_file`, `slab_reclaimable`,
      `pagetables`, `free_cma`); (3) the `Tasks state (memory values in pages)` table with columns
      `pid`, `uid`, `tgid`, `total_vm`, `rss`, `pgtables_bytes`, `swapents`, `oom_score_adj`, `name`
      — **read this to see who was growing, not just who died**; (4) the kill line, whose format
      string is
      `"Killed process %d (%s) total-vm:%lukB, anon-rss:%lukB, file-rss:%lukB, shmem-rss:%lukB, UID:%u pgtables:%lukB oom_score_adj:%hd"`.
      Compare `anon-rss` against the container limit, not against `MemTotal`. `[DIAG]` `[SOURCE]`
3.7.10 **The cgroup-side evidence, when `dmesg` is unavailable** (a very common situation inside a
       container): `memory.events`' **`oom`** ("allocation failed at limit") versus **`oom_kill`**
       ("processes killed by OOM killer") — the distinction between "we hit the wall" and
       "something died"; `memory.events.local` for this cgroup only, `memory.max` and `memory.peak` for the
       ceiling and the high-water mark, and the Kubernetes `lastState.terminated.reason=OOMKilled`
       with `exitCode: 137`. `[PROC]` `[X-REF 19]`
3.7.11 `[VERSION-TRAP]` **`systemd-oomd` is a different policy on the same box.** It watches PSI
       and swap usage in userspace and kills a **whole cgroup** *before* the kernel would, driven by
       `ManagedOOMMemoryPressure=kill`, `ManagedOOMMemoryPressureLimit=`, `ManagedOOMSwap=` and
       `MemoryPressureLimit=`. So "we were OOM-killed" now has two possible authors with different
       selection rules, and `journalctl -u systemd-oomd` is the second place to look.
       `[VERSION-TRAP]` `[DIAG]`

*(11 leaves)*

## §3.8 Page cache and writeback internals: the xarray, `bdi`, dirty thresholds

3.8.1 `[SOURCE]` **`struct address_space` is the page cache.** One per inode:
      `i_pages` — an **xarray** (the 4.20+ replacement for the radix tree) keyed by page offset;
      `a_ops` (`struct address_space_operations`: `read_folio`, `writepages`, `dirty_folio`,
      `direct_IO`, `migrate_folio`); `nrpages`; `i_mmap` (the interval tree of VMAs mapping this
      file, used by reclaim's reverse mapping); `host` (the inode). `[SOURCE]`
3.8.2 `[VERSION-TRAP]` **`struct folio` is the unit now.** A folio is a head page plus an order, so
      the page cache holds **large folios** (order > 0) and one entry can cover 16 KiB or 2 MiB.
      Consequences that show up in production: fewer entries to manage, larger readahead
      granularity, and `AnonHugePages`/`FileHugePages` becoming meaningful for file-backed data. Any
      description of the page cache in terms of single `struct page`s is pre-5.16 vocabulary.
      `[VERSION-TRAP]` `[SOURCE]`
3.8.3 **The xarray's tag bits are why writeback does not scan.** Entries carry
      `PAGECACHE_TAG_DIRTY`, `PAGECACHE_TAG_WRITEBACK` and `PAGECACHE_TAG_TOWRITE`, so
      `filemap_get_folios_tag()` walks only tagged entries. Evicted entries leave **shadow
      entries** in the same xarray for refault detection (§3.6.9). One data structure serves lookup,
      writeback and working-set estimation. `[PROVE]` `[SOURCE]`
3.8.4 `[FLOW]` **The buffered read path:** `read()` → `vfs_read` → `->read_iter`
      (`generic_file_read_iter`) → `filemap_read()` → `filemap_get_pages()` → xarray lookup; on a
      miss, `page_cache_sync_readahead()`; on a hit of the readahead marker folio,
      `page_cache_async_readahead()`; then `copy_folio_to_iter()`. Readahead state is
      `struct file_ra_state` (`start`, `size`, `async_size`, `ra_pages`) per open file, seeded from
      `/sys/block/<dev>/queue/read_ahead_kb` (**128** KB typically). `[FLOW]` `[SOURCE]`
      `[SYSCTL]`
3.8.5 `[FLOW]` **The buffered write path:** `write()` → `->write_iter`
      (`generic_file_write_iter` → `generic_perform_write`) → `->write_begin` (allocate/lock the
      folio, read-modify-write if partial) → copy from user → `->write_end` → `folio_mark_dirty()`
      → `__mark_inode_dirty(I_DIRTY_PAGES)` puts the inode on its `bdi_writeback` dirty list, and
      the dirty page count is charged **globally, per-bdi and per-cgroup**. Nothing has reached the
      device yet, and `write()` has already returned. `[FLOW]` `[PROVE]`
3.8.6 `[SOURCE]` **`struct backing_dev_info` and `struct bdi_writeback`.** Each backing device gets
      a measured `write_bandwidth`, and the global dirty limit is *divided between devices in
      proportion to it* — so a slow EBS volume gets a small share and is throttled sooner than a
      local NVMe on the same host. Flushing is done by `wb_workfn()` on the `writeback` workqueue,
      visible as `[kworker/u<N>:<n>-writeback]`. Knobs live in
      `/sys/class/bdi/<major>:<minor>/{min_ratio,max_ratio,read_ahead_kb,stable_pages_required}`.
      `[SOURCE]` `[PROC]`
3.8.7 `[SYSCTL]` **The dirty thresholds and the denominator people get wrong.**
      `domain_dirty_limits()` computes the background and hard limits from
      `vm.dirty_background_ratio` and `vm.dirty_ratio` as percentages of **dirtyable memory**
      (free + reclaimable file LRU), *not* of `MemTotal` — so the same ratio means different bytes
      on a box with a hot page cache. `vm.dirty_background_bytes`/`vm.dirty_bytes` override the
      ratios and are the right choice when the host size is not yours to control.
      `vm.dirty_expire_centisecs` and `vm.dirty_writeback_centisecs` set the age and the flusher
      wake interval. Defaults (10 / 20 / 3000 / 500) must be re-read from
      `Documentation/admin-guide/sysctl/vm.rst` before publication. `[SYSCTL]` `[RESEARCH]`
3.8.8 `[PROVE]` **`balance_dirty_pages()` is a rate controller, not a switch.** Called from the
      write path, it estimates a per-task dirty rate from the position of current dirtiness between
      the background and hard limits and the observed device bandwidth, then **sleeps the writing
      task** proportionally (`TASK_KILLABLE`, tracked in `task_struct`'s `nr_dirtied`,
      `nr_dirtied_pause`, `dirty_paused_when`). Above `dirty_ratio` the sleep becomes a hard wait
      for writeback. Two consequences: throttling is charged to **whoever is writing**, so an
      unrelated latency-sensitive thread that writes a single log line pays for the batch job's
      dirtiness; and the stall shows as `io.pressure`/`D` state with no error anywhere.
      `[PROVE]` `[SOURCE]` `[TRAP]`
3.8.9 `[FLOW]` **What `fsync(fd)` actually does:** `vfs_fsync_range` → `->fsync` (e.g.
      `ext4_sync_file`) → `file_write_and_wait_range` → `filemap_fdatawrite_range` → `do_writepages`
      → `->writepages` (`ext4_writepages` / `xfs_vm_writepages`) → block layer submission → wait for
      completion → **journal commit** (`jbd2_complete_transaction`) → `blkdev_issue_flush()` — a
      FLUSH/FUA command that makes the device's volatile cache durable. The last step is the device
      round trip that costs the millisecond, and it cannot be batched away by the kernel — only by
      your code doing fewer `fsync`s. `[FLOW]` `[SOURCE]` `[CALC]`
3.8.10 **ext4 journalling is a shared resource, which is why an unrelated writer adds latency.**
       `data=ordered` (default) orders data before metadata commit; `data=writeback` relaxes it;
       `data=journal` journals data too. The `[jbd2/nvme0n1p1-8]` kthread commits every
       `commit=5` seconds, and **an `fsync` on one file waits for the shared transaction** — so
       `ApplicationGateway`'s access-log `fsync` and `FundsLedger`'s ledger `fsync` on the same
       filesystem are coupled. XFS is per-inode-log-item and behaves differently. `nobarrier` makes
       `fsync` fast by making it a lie. `[PROVE]` `[TRAP]` `[X-REF 09]`
3.8.11 `[TRAP]` **Writeback errors are reported once, per fd.** Since 4.13 each `address_space`
       carries an `errseq_t` and each `struct file` remembers the sequence it last saw, so the first
       `fsync` after an `AS_EIO`/`AS_ENOSPC` returns the error and subsequent ones return **0** —
       while the dirty pages have already been discarded. Retrying `fsync` does not re-attempt the
       write. Application code writing the `PaymentRun` payout file must treat a non-zero `fsync`
       return as data loss, not as a transient. `[TRAP]` `[PROVE]`
3.8.12 **`O_DIRECT`, and the fact that Java cannot ask for it.** `->direct_IO` bypasses the page
       cache entirely, requiring the buffer address, file offset and length to be aligned to the
       device's logical block size; it is how a database owns its own caching. There is **no**
       `StandardOpenOption` for `O_DIRECT`, so a JVM's options are `posix_fadvise(POSIX_FADV_DONTNEED)`
       via JNI/FFM, `sync_file_range`, or accepting the page cache. Stating this closes the
       "why doesn't the JVM just use O_DIRECT" question definitively. `[API]` `[TRAP]`
       `[X-REF 09]`
3.8.13 `[DIAG]` **The writeback instrument set:** `/proc/meminfo`'s `Dirty` and `Writeback`
       (watch `Dirty` climb toward the computed limit); `/proc/vmstat`'s `nr_dirty`,
       `nr_writeback`, `nr_dirtied`, `nr_written`, `nr_dirty_threshold`,
       `nr_dirty_background_threshold` — the last two are the **computed** limits, which is how you
       verify the arithmetic instead of assuming it; `iostat -x 1` for the device side;
       `bpftrace -e 'kprobe:balance_dirty_pages_ratelimited { @[comm] = count(); }'` to name the
       throttled process; `/sys/kernel/debug/bdi/<dev>/stats`. `[DIAG]` `[PROC]` `[BUILD]`

*(13 leaves)*

## §3.9 The block layer: `blk-mq`, request merging, plugging, the schedulers

3.9.1 `[SOURCE]` **`struct bio` is the unit that enters the block layer**: `bi_iter`
      (`bi_sector`, `bi_size`, `bi_idx`), `bi_io_vec[]` (the page/offset/length vector — a bio
      describes scattered memory, which is what makes it zero-copy), `bi_opf` (the operation
      `REQ_OP_READ`/`WRITE`/`FLUSH`/`DISCARD` OR'd with flags `REQ_SYNC`, `REQ_FUA`, `REQ_META`,
      `REQ_PREFLUSH`, `REQ_RAHEAD`), `bi_end_io`, `bi_status`. `submit_bio()` →
      `blk_mq_submit_bio()`, splitting first at `queue_max_sectors`. `[SOURCE]`
3.9.2 `[SOURCE]` **The two-layer queue model, which is the whole point of blk-mq.** Per-CPU (or
      per-node) **software staging queues** `struct blk_mq_ctx` accept requests — "requests will be
      sent to the software queue" when an I/O scheduler is attached or merging is wanted — and
      **hardware dispatch queues** `struct blk_mq_hw_ctx` map onto the device's own submission
      queues: "The hardware queue is a struct used by device drivers to map the device submission
      queues (or device DMA ring buffer)". Configuration lives in `struct blk_mq_tag_set`
      (`nr_hw_queues`, `queue_depth`, `ops`), shareable across request queues. `[SOURCE]`
3.9.3 **Tags are how completion is O(1).** "Every request is identified by an integer, ranging from
      0 to the dispatch queue size" — allocated from an `sbitmap` (scalable bitmap with per-CPU
      hinting), carried to the device, and returned in the completion so no list is ever searched.
      Tag exhaustion is back-pressure: the submitter waits, and that wait is `D` state, not an
      error. `[PROVE]` `[SOURCE]`
3.9.4 `[VERSION-TRAP]` **What blk-mq replaced.** The single `request_queue` with one `queue_lock`
      and one elevator (`noop`, `deadline`, **`cfq`**, `anticipatory`) could not feed a device with
      hundreds of thousands of IOPS across many cores. `cfq` and the legacy single-queue path are
      **gone** from modern kernels; the scheduler names you can actually select are `none`,
      `mq-deadline`, `kyber` and `bfq`. Any tuning guide mentioning `cfq` or
      `/sys/block/*/queue/iosched/slice_idle` predates 5.0. `[VERSION-TRAP]` `[TRAP]`
3.9.5 **Plugging batches submissions on purpose.** `blk_start_plug()`/`blk_finish_plug()` install a
      `struct blk_plug` on the *task*, so bios accumulate in a task-local list instead of being
      issued one by one; on unplug they are merged and dispatched together. This is why a loop of
      `write()`s inside one `writepages` call produces far fewer device requests than `write()`
      calls, and why a single `fsync` at the end is dramatically cheaper than one per record.
      `[PROVE]` `[SOURCE]`
3.9.6 **Merging, and the counter that proves it happened.** `blk_attempt_plug_merge()` tries the
      task's plug list; `blk_mq_sched_try_merge()`/`elv_merge()` try the staging queue, producing a
      **back merge** (contiguous after) or **front merge** (contiguous before) — "requests for
      sector 3-6, 6-7, 7-9" become one. `/sys/block/<dev>/queue/nomerges` (0 = full merging,
      1 = simple, 2 = none) disables it for experiments, and `iostat -x`'s `rrqm/s`/`wrqm/s` and
      `%rrqm`/`%wrqm` are the evidence. High merge rates mean your access pattern is sequential
      whatever your code looks like. `[PROC]` `[DIAG]`
3.9.7 `[TABLE]` **The four schedulers and when each is right.** `none` — no reordering, correct
      default for NVMe and any device with real internal parallelism and low latency;
      `mq-deadline` — read/write expiry deadlines, the right choice for a device with a queue that
      can be starved (rotational, or a throttled network volume like EBS); `kyber` — target
      read/write latencies, self-tuning, for fast multi-queue devices under mixed load; `bfq` —
      proportional-share fairness with per-cgroup weights, high overhead, for interactive
      desktop-shaped workloads. Read and set at `/sys/block/nvme0n1/queue/scheduler` (the active
      one is in `[brackets]`). `[TABLE]` `[SYSCTL]`
3.9.8 `[SYSCTL]` **The queue files that change behaviour**, all under `/sys/block/<dev>/queue/`:
      `nr_requests` (per-hctx depth — raising it increases throughput and *increases* latency),
      `max_sectors_kb` and `max_hw_sectors_kb` (bio split size), `read_ahead_kb`, `rotational`
      (0 for SSD/NVMe — the flag several heuristics read), `add_random`, `rq_affinity` (0/1/2 —
      complete on the submitting CPU's cache domain), `io_poll`/`io_poll_delay`, `write_cache`
      (`write back` vs `write through` — whether FLUSH is needed at all), `wbt_lat_usec`,
      `discard_max_bytes`, `logical_block_size`/`physical_block_size`. `[SYSCTL]` `[PROC]`
3.9.9 **`blk-wbt`: writeback throttling in the block layer.** It monitors read completion latency
      and throttles *background* writes when reads start suffering, targeting
      `wbt_lat_usec` (2 ms default class for non-rotational). This is the mechanism that stops a
      writeback flush storm from destroying `FundsLedger`'s read latency — and setting
      `wbt_lat_usec=0` to "remove a limit" is how people accidentally reintroduce the problem.
      `[NUM]` `[TRAP]`
3.9.10 `[FLOW]` **The completion path closes the `D`-state story:** device raises an MSI-X
       interrupt on the CPU that owns that hardware queue → the driver's handler calls
       `blk_mq_complete_request()` → depending on `rq_affinity`, completion is finished locally, via
       an IPI to the submitting CPU, or via `BLOCK_SOFTIRQ` → `bio_endio()` → the filesystem's
       `bi_end_io` (`folio_end_writeback`, `end_buffer_async_write`) → `wake_up` of whoever was in
       `io_schedule()`. A task in `wchan = io_schedule` is waiting for exactly this chain.
       `[FLOW]` `[PROC]`
3.9.11 `[DIAG]` **`/proc/diskstats`, field by field**, because every I/O metric you have is derived
       from it: (1) reads completed, (2) reads merged, (3) sectors read, (4) ms reading,
       (5) writes completed, (6) writes merged, (7) sectors written, (8) ms writing,
       (9) **I/Os currently in flight**, (10) **ms spent doing I/O (`io_ticks`)**,
       (11) weighted ms in I/O, then discard (12–15) and flush (16–17) fields. `iostat -x`'s
       `r_await`/`w_await` = ms÷count, `aqu-sz` from field 11, `%util` from `io_ticks`.
       **`%util` is meaningless on a device with parallelism** — 100% only means "at least one
       request was outstanding", so a gp3 volume at `%util=100` may be at 5% of its IOPS. Read
       `await` and `aqu-sz` instead. `[DIAG]` `[TRAP]` `[CALC]`
3.9.12 **cgroup v2's io controller, and what its throttling looks like.** `io.max` with keys
       `rbps`, `wbps`, `riops`, `wiops` per `MAJ:MIN`; `io.latency` (a target, protective rather
       than capping); `io.weight`/`io.cost.model`/`io.cost.qos` (`blk-iocost`, proportional);
       `io.stat` reporting `rbytes`, `wbytes`, `rios`, `wios`, `dbytes`, `dios`; `io.pressure`.
       Throttling manifests as **`D` state and rising `await`**, never as an `EAGAIN` — which is why
       "the disk is slow" and "we set an io.max" are indistinguishable without reading the cgroup.
       Buffered writes only attribute correctly because of cgroup writeback (§3.8.6). `[PROC]`
       `[TRAP]`
3.9.13 `[DIAG]` **The block-layer instrument set, by question.** "How long do I/Os take?"
       `biolatency -D` (histogram per device). "Which process and which file?" `biosnoop`,
       `filetop`, `ext4slower`/`xfsslower` (per-operation over a threshold). "What size are they?"
       `bitesize`. "Where is the time inside the layer?" `blktrace -d /dev/nvme0n1 | blkparse`
       (the `Q`/`G`/`I`/`D`/`C` action letters: queued, get-request, inserted, issued to driver,
       completed — `D`→`C` is the device, `Q`→`D` is the kernel) and
       `/sys/kernel/debug/block/<dev>/` for live hctx state. `[DIAG]` `[BUILD]`

*(13 leaves)*

## §3.10 VFS internals: `struct file`, dentry and inode caches, path resolution

3.10.1 `[TABLE]` **The four objects and the one distinction that matters.**
       `struct super_block` (a mounted filesystem instance), `struct inode` (`i_ino`, `i_mode`,
       `i_size`, `i_nlink`, `i_mapping` → the page cache, `i_op`, `i_fop` — the *file itself*),
       `struct dentry` (`d_name`, `d_parent`, `d_inode` — a *name→inode edge*, cached, not
       persistent), `struct file` (`f_pos`, `f_flags`, `f_mode`, `f_op`, `f_path`, `f_count` — an
       **open file description**, i.e. one act of opening). A hard link is two dentries to one
       inode; two `open()`s are two `struct file`s; a `dup()` is two fds to one `struct file`.
       `[TABLE]` `[PROVE]`
3.10.2 `[SOURCE]` **Where an fd number comes from.** `task_struct->files` (`struct files_struct`)
       → `fdtable` → `fd_array[]` of `struct file *`, plus the `open_fds` and `close_on_exec`
       bitmaps. `alloc_fd()` returns the **lowest free** number — which is why fd numbers are
       reused immediately and why an fd leak shows as a monotonically rising *maximum*, not as
       gaps. `dup`/`dup2`/`fcntl(F_DUPFD)` add a table entry pointing at the same `struct file`;
       `fork` copies the table but shares the `struct file`s. `[SOURCE]` `[PROVE]`
3.10.3 `[TRAP]` **`f_pos` is shared, and that is a real bug class.** Because `dup` and `fork` share
       the open file description, two threads or two processes writing through duplicated fds share
       the offset, so concurrent `write()`s interleave rather than overwrite — whereas two separate
       `open()`s of the same path have independent offsets and *do* overwrite. `O_APPEND` makes the
       offset-and-write atomic and is the only safe way for two writers to share a log file.
       `[TRAP]` `[PROVE]`
3.10.4 `[FLOW]` **Path resolution, component by component.** `struct nameidata` holds the walk
       state; `path_lookupat` loops `walk_component()` → `lookup_fast()` (dcache hit under
       **RCU-walk**: no refcounts, no locks, validated by a seqlock retry) → `lookup_slow()`
       (**ref-walk**: take references, call `inode->i_op->lookup`, hit the filesystem). Each `/`
       is a separate lookup with a separate permission check on the directory's execute bit, which
       is why deep paths and long `CLASSPATH`s cost measurable syscall time. Symlink depth is
       capped at **`MAXSYMLINKS` = 40** → `ELOOP`. `[FLOW]` `[SOURCE]` `[NUM]`
3.10.5 **The dentry cache, including the part people forget.** Successful lookups are cached, and
       so are **negative dentries** — the cached fact that a name does *not* exist — which is why a
       repeated stat of a missing optional config file is nearly free after the first miss.
       Reclaimed by a shrinker under memory pressure and tunable via `vm.vfs_cache_pressure`;
       inspect with `/proc/sys/fs/dentry-state` (`nr_dentry`, `nr_unused`, age limit) and
       `slabtop` (`dentry`, `inode_cache`, `ext4_inode_cache`). A "memory leak" that is `dentry`
       slab is an open-file or negative-lookup storm. `[PROC]` `[DIAG]`
3.10.6 `[SOURCE]` **Mounts and propagation.** `struct mount` (kernel-internal) wraps
       `struct vfsmount`, forming the per-namespace mount tree.
       `/proc/self/mountinfo` gives, per line: mount id, parent id, `major:minor`, root within the
       filesystem, mount point, per-mount options, **optional propagation fields**
       (`shared:N`, `master:N`, `propagate_from:N`, `unbindable`), separator, filesystem type,
       source, super options. Propagation type (`MS_SHARED`, `MS_SLAVE`, `MS_PRIVATE`,
       `MS_UNBINDABLE`) decides whether a mount made inside a container is visible outside it —
       the mechanism behind both working and broken volume mounts. `[SOURCE]` `[PROC]`
3.10.7 **overlayfs, and the copy-up cost.** `lowerdir` (read-only image layers, colon-separated),
       `upperdir` (the container's writable layer), `workdir` (atomic staging), `merged` (what the
       container sees). Deleting a lower file creates a **whiteout** (a char device with 0/0);
       writing one byte of a lower file **copies the entire file** to the upper layer. So a
       `DocumentVerification` container that opens a 6 MB image for read-write copies 6 MB before
       the first byte lands, and `metacopy=on`/`redirect_dir=on` only mitigate the metadata case.
       The fix is a volume, not a tuning flag. `[PROVE]` `[CALC]` `[X-REF 19]`
3.10.8 `[TABLE]` **The synthetic filesystems and their costs.** `procfs` — content **generated on
       read** via `seq_file`, so `/proc/<pid>/smaps` on a 12 GB heap walks every VMA under
       `mmap_lock` and is genuinely expensive (use `smaps_rollup`). `sysfs` — one value per file,
       backed by kobjects. `tmpfs` — page cache with no backing store, counted as `Shmem`, charged
       to the creating cgroup and **reclaimable only to swap**, which is why a large
       `emptyDir: {medium: Memory}` counts against `memory.max`. `cgroup2`, `devtmpfs`, `debugfs`,
       `tracefs`, `bpffs`, `pidfs`. `[TABLE]` `[PROVE]`
3.10.9 **"Everything is an fd" as a deliberate design**, because it is what lets one `epoll` loop
       wait on everything: `eventfd` (a counter — Netty's wakeup mechanism), `signalfd` (signals as
       readable events), `timerfd` (timers), `pidfd_open`/`CLONE_PIDFD` (a process, race-free —
       `pidfd_send_signal` cannot kill a recycled pid), `memfd_create` (anonymous shared memory,
       sealable), `inotify`/`fanotify` (filesystem events), `userfaultfd`, `io_uring`'s own fd.
       `[SYSCALL]` `[API]`
3.10.10 **The `*at()` family exists to close TOCTOU races.** `openat(dirfd, path, flags, mode)`,
        `openat2(dirfd, struct open_how *, size)` with `RESOLVE_BENEATH`, `RESOLVE_NO_SYMLINKS`,
        `RESOLVE_NO_MAGICLINKS`, `RESOLVE_IN_ROOT`; `AT_FDCWD` as the "relative to cwd" sentinel;
        `O_PATH` for a reference to a location you may not open; `statx` for the extended attribute
        set. Container runtimes and any code resolving an operator-supplied path must use these.
        `[SYSCALL]` `[X-REF 13]`
3.10.11 `[PROVE]` **`struct file_operations` is what makes `read()` polymorphic.** The same syscall
        dispatches through `f_op->read_iter` to `generic_file_read_iter` (regular file),
        `sock_read_iter` (socket), `pipe_read` (pipe) or a driver's own handler — which is why
        `read()` on a socket has no offset, why `lseek` on a pipe returns `ESPIPE`, and why
        `sendfile`/`splice` require the source to implement `->splice_read` (a socket does not, so
        socket→socket `sendfile` is not a thing). `[PROVE]` `[SOURCE]`
3.10.12 `[DIAG]` **Reading a process's VFS state.** `ls -l /proc/<pid>/fd` (symlinks to paths,
        `socket:[inode]`, `anon_inode:[eventpoll]`, `pipe:[inode]`);
        `/proc/<pid>/fdinfo/<fd>` (`pos`, `flags`, `mnt_id`, `ino`, and for an epoll fd the
        `tfd:` lines naming **exactly which fds it watches** with their event masks — the fastest
        way to audit a Netty event loop); `lsof -p <pid>` and `lsof -nP -i` for sockets;
        `/proc/sys/fs/file-nr` (allocated / free / max) versus `/proc/<pid>/limits`. An fd leak is
        diagnosed by *type*, and `fdinfo` is where the type lives. `[DIAG]` `[PROC]`

*(12 leaves)*

## §3.11 `epoll` internals: the ready list, wakeups, `EPOLLEXCLUSIVE`

3.11.1 `[SOURCE]` **`struct eventpoll`** (`fs/eventpoll.c`) — the object behind an epoll fd:
       `rbr` (the red-black tree root of registered items), `rdllist` (**the ready list**, a
       doubly-linked list), `ovflist` (the overflow list used while events are being handed out),
       `wq` (the wait queue of threads blocked in `epoll_wait` on *this* epfd), `poll_wait` (so an
       epoll fd can itself be polled — nesting), `lock` (spinlock protecting `rdllist`, taken from
       interrupt context), `mtx` (mutex for structural changes). `[SOURCE]`
3.11.2 `[SOURCE]` **`struct epitem`** — one per registered fd: `rbn` (its node in the tree),
       `rdllink` (its link in the ready list), `ffd` (`struct epoll_filefd` = the `struct file *`
       **and** the fd number — the key), `event` (the userspace `struct epoll_event`: `events`
       mask and the opaque 64-bit `data` you get back), `pwqlist` (the installed wait-queue
       entries), `ep`, `fllink` (the link on the *file's* list of watchers, used to clean up when
       the file dies). `[SOURCE]`
3.11.3 `[FLOW]` **Registration, and why nothing is ever scanned.** `epoll_ctl(EPOLL_CTL_ADD)` →
       `ep_insert()` → `ep_item_poll()` calls the file's `->poll` with a `poll_table` whose
       `_qproc` is `ep_ptable_queue_proc`, which allocates an `eppoll_entry` and hooks the callback
       **`ep_poll_callback`** onto the file's own wait queue. From then on the *producer* of
       readiness does the work. `epoll_ctl` is O(log n) on the tree; there is no O(n) anywhere.
       `[FLOW]` `[PROVE]` `[SOURCE]`
3.11.4 `[FLOW]` **The wakeup path, end to end:** a packet arrives → softirq → `tcp_v4_rcv` queues
       to the socket → `sk->sk_data_ready` → `wake_up_interruptible_poll(sk_sleep(sk), EPOLLIN)` →
       every registered `ep_poll_callback` runs **in softirq context** → it checks the event against
       the item's mask, links the `epitem` onto `ep->rdllist` (or `ovflist` if a transfer is in
       progress), and wakes `ep->wq`. The blocked `epoll_wait` returns. Total work is proportional
       to *ready* fds, not registered ones. `[FLOW]` `[PROVE]`
3.11.5 **`ep_poll()` is what you see in `wchan`.** It checks `rdllist` first (a non-empty list is a
       syscall with no sleep at all), otherwise adds an **exclusive** wait-queue entry and calls
       `schedule_hrtimeout_range()` with the caller's timeout. A thread showing
       `wchan = ep_poll` is a **healthy idle event loop**, and mistaking it for a hang is a common
       triage error. `/proc/<pid>/task/*/wchan` plus `epoll_wait` dominance in `strace -c` is the
       healthy shape. `[PROC]` `[TRAP]`
3.11.6 `[PROVE]` **Level-triggered versus edge-triggered is one line in `ep_send_events()`.** It
       splices `rdllist` onto a private list, and for each item calls `ep_item_poll()` **again** to
       fetch the *current* mask (readiness may have gone away — this is the mechanical source of
       spurious wakeups), copies the result to the user array, and then, **if `EPOLLET` is not
       set**, re-links the item onto the ready list so it is reported again next call. Edge-triggered
       simply does not re-link. Therefore ET *requires* draining until `EAGAIN`, or the event is
       lost forever. `[PROVE]` `[SOURCE]` `[TRAP]`
3.11.7 **`EPOLLONESHOT`** clears the item's event mask after delivery, so it will not fire again
       until `EPOLL_CTL_MOD` rearms it — the mechanism behind "at most one handler thread per fd at
       a time" in a multi-threaded event loop, and the reason a forgotten rearm looks like a dead
       connection rather than a busy loop. `[API]` `[TRAP]`
3.11.8 **`EPOLLEXCLUSIVE` (4.5+) and the thundering herd.** When N epoll instances (N worker
       processes, or N event loops) register the same listening socket, a single incoming
       connection wakes all N. `EPOLLEXCLUSIVE` sets `WQ_FLAG_EXCLUSIVE` on the wait-queue entry so
       the wakeup stops after one waiter. Restrictions to state: `EPOLL_CTL_ADD` only (not `MOD`),
       cannot be combined with `EPOLLONESHOT`, and it guarantees "not all" rather than "exactly
       one". The alternative that avoids the problem entirely is `SO_REUSEPORT` with one listening
       socket per worker. `[NUM]` `[X-REF 10]`
3.11.9 `[TRAP]` **Registration follows the open file description, not the fd number.** The
       `epitem` key includes the `struct file *`, so `dup()`ing a registered fd leaves the
       registration alive under the *other* number, and closing one fd does not deregister while
       another reference exists; when the last reference dies, `eventpoll_release_file()` cleans up
       via `fllink`. Closing an fd while another thread is inside `epoll_wait` on it is the classic
       use-after-close race, which is exactly why the JDK's `Selector` and Netty track cancellation
       in userspace instead of trusting `close()` to deregister. `[TRAP]` `[PROVE]`
3.11.10 **Nesting and its limit.** Because an epoll fd is pollable (`poll_wait`), epoll fds can be
        registered in each other; `ep_loop_check()` rejects cycles at
        `EPOLL_MAX_NESTS` (**4**) to bound the recursive wakeup depth. Relevant to any library that
        composes selectors, and the reason a "selector of selectors" design eventually returns
        `EINVAL`. `[NUM]` `[SOURCE]`
3.11.11 `[API]` **The JVM's use of it, concretely.** `sun.nio.ch.EPollSelectorImpl` calls
        `epoll_create1` once per `Selector` and `epoll_wait` with the computed timeout;
        `Selector.wakeup()` writes to a pipe or `eventfd` registered in the same set;
        `sun.nio.ch.EPollPort` backs `AsynchronousChannelGroup`. Netty's `EpollEventLoop` uses
        native `epoll` with `EPOLLET` plus an `eventfd`, and derives the `epoll_wait` timeout from
        its scheduled-task queue. `ApplicationGateway` at **55k concurrent sessions** therefore
        holds ~55k `epitem`s across a handful of `eventpoll` objects — one RB-tree insert per
        connection, and no per-poll cost for idle ones. `[API]` `[CALC]`
3.11.12 `[SYSCTL]` **The limit nobody knows about:** `fs.epoll.max_user_watches` caps total
        registered items per user, sized at boot from available low memory (each watch costs a
        pinned `epitem` plus `eppoll_entry`). Exceeding it gives `epoll_ctl` → **`ENOSPC`**, which
        looks nothing like an fd limit and is not fixed by `ulimit -n`. Read it before sizing a
        gateway for 55k connections × multiple watched fds each. `[SYSCTL]` `[TRAP]`
3.11.13 `[DIAG]` **Proving an event-loop diagnosis.** `/proc/<pid>/fdinfo/<epfd>` for the exact
        registration set; `strace -c` shape — `epoll_wait` dominant with a large `usecs/call` is
        healthy idle, `epoll_wait` at millions/sec with `timeout=0` is a busy-spin bug, and
        `EAGAIN`-heavy `read` is an ET drain loop working correctly;
        `bpftrace -e 'kprobe:ep_poll_callback { @[comm] = count(); }'` for wakeup attribution, and a
        `kprobe`/`kretprobe` pair on `ep_poll` for a histogram of how long the loop actually
        sleeps. `[DIAG]` `[BUILD]`

*(13 leaves)*

## §3.12 `io_uring` internals: the SQ/CQ rings, `SQPOLL`, registered buffers

3.12.1 `[SOURCE]` **The setup call and its parameter block.**
       `int io_uring_setup(u32 entries, struct io_uring_params *p)` returns an fd; "the params is
       used by the application to pass options to the kernel, and by the kernel to convey
       information about the ring buffers". Fields: `sq_entries`, `cq_entries`, `flags`,
       `sq_thread_cpu`, `sq_thread_idle`, `features`, `wq_fd`, `sq_off`
       (`struct io_sqring_offsets`), `cq_off` (`struct io_cqring_offsets`). `entries` is rounded up
       to a power of two; the CQ is twice the SQ unless `IORING_SETUP_CQSIZE` overrides it.
       `[SOURCE]` `[SYSCALL]`
3.12.2 **Three `mmap` regions, and the offsets are constants you should know.**
       `IORING_OFF_SQ_RING`, `IORING_OFF_CQ_RING` and `IORING_OFF_SQES` map the submission ring
       header, the completion ring, and the SQE array into the process — shared with the kernel, no
       copy. The `sq_off`/`cq_off` structs tell userspace where `head`, `tail`, `ring_mask`,
       `ring_entries`, `flags`, `dropped`, `overflow` and `array` live inside those mappings, so the
       ABI is discoverable rather than compiled in. `[SOURCE]` `[NUM]`
3.12.3 `[SOURCE]` **`struct io_uring_sqe` is 64 bytes** — `opcode` (`IORING_OP_READV`, `WRITEV`,
       `READ_FIXED`, `WRITE_FIXED`, `FSYNC`, `ACCEPT`, `CONNECT`, `RECV`, `SEND`, `POLL_ADD`,
       `TIMEOUT`, `OPENAT`, `CLOSE`, `STATX`, `SENDMSG`, `RECVMSG`), `flags` (`IOSQE_*`), `ioprio`,
       `fd`, `off`, `addr`, `len`, **`user_data`**, plus an op-specific union.
       **`struct io_uring_cqe`** is `user_data`, `res` (the syscall's return value, or `-errno`),
       `flags`. `user_data` is the *only* correlation between submission and completion — there is
       no ordering guarantee, which is the fundamental difference from a readiness API.
       `[SOURCE]` `[PROVE]`
3.12.4 `[PROVE]` **The memory-ordering protocol is the part that bites.** The producer writes the
       SQE, then publishes with a release store to `tail`; the consumer does an acquire load. Get
       the barriers wrong and you have silent corruption with no syscall to blame — which is why
       essentially nobody uses the raw interface and everybody uses **`liburing`**
       (`io_uring_get_sqe`, `io_uring_prep_*`, `io_uring_submit`, `io_uring_wait_cqe`,
       `io_uring_cqe_seen`). `[PROVE]` `[TRAP]`
3.12.5 `[SYSCALL]` **`io_uring_enter(fd, to_submit, min_complete, flags, sig, sz)`** is the one
       syscall that does everything: it publishes `to_submit` SQEs and, with
       `IORING_ENTER_GETEVENTS`, waits for `min_complete` CQEs. So a batch of 64 reads plus their
       completions is **one** boundary crossing instead of 128 — and if the CQ already has entries,
       reaping them requires **no syscall at all**, because userspace just reads the shared ring.
       `[SYSCALL]` `[CALC]`
3.12.6 **`IORING_SETUP_SQPOLL` removes even that syscall.** A kernel thread (visible as
       `iou-sqp-<pid>` in `/proc/<pid>/task/*/comm`) polls the submission ring, so steady-state
       submission is a memory write. `IORING_SETUP_SQ_AFF` + `sq_thread_cpu` pins it;
       `sq_thread_idle` (ms) is how long it spins before sleeping — and while it spins it burns a
       core. This is a throughput-for-CPU trade that only makes sense on a dedicated host, never on
       a `cpu.max`-limited pod where the poller consumes the quota the workload needed. `[TRAP]`
       `[CALC]`
3.12.7 **Where the work actually runs.** Operations that can complete without blocking are issued
       inline in the submitter's context. Anything that would block, or anything marked
       `IOSQE_ASYNC`, is handed to the **`io-wq`** pool (`iou-wrk-<pid>` threads, bounded and
       unbounded classes sized from `RLIMIT_NPROC` and settable via
       `IORING_REGISTER_IOWQ_MAX_WORKERS`). `IORING_SETUP_IOPOLL` instead **polls the NVMe
       completion queue** with no interrupts at all — the lowest-latency mode, and only valid for
       `O_DIRECT` on a polling-capable device. `[NUM]` `[X-REF 11]`
3.12.8 **`io_uring_register` is where the remaining per-operation costs go away.**
       `IORING_REGISTER_BUFFERS` pins pages once so each op skips `get_user_pages` (then use
       `READ_FIXED`/`WRITE_FIXED`); `IORING_REGISTER_FILES` pre-resolves fds so `IOSQE_FIXED_FILE`
       skips the fd-table lookup and refcount; `IORING_REGISTER_PBUF_RING` provides a buffer ring so
       the kernel picks a buffer at completion time (essential for multishot receive);
       `IORING_REGISTER_EVENTFD` lets an existing `epoll` loop be notified of CQEs — the bridge for
       incremental adoption. `[SYSCALL]` `[API]`
3.12.9 **Linking and multishot express a whole state machine in one submission.**
       `IOSQE_IO_LINK`/`IOSQE_IO_HARDLINK` make the next SQE depend on this one's success;
       `IOSQE_IO_DRAIN` waits for all prior; `IORING_OP_ACCEPT` with `IORING_ACCEPT_MULTISHOT` and
       `IORING_OP_RECV` with `IORING_RECVSEND_POLL_FIRST`/multishot keep producing completions from
       a single SQE; `IORING_OP_POLL_ADD` and `IORING_OP_TIMEOUT` cover what `epoll_wait`'s timeout
       did. An accept→recv→process→send chain therefore costs one submission rather than three
       round trips. `[PROVE]` `[API]`
3.12.10 `[VERSION-TRAP]` **The current low-overhead configuration is not the 2019 one.**
        `IORING_SETUP_SINGLE_ISSUER` (promise only one task submits, letting the kernel skip
        locking), `IORING_SETUP_DEFER_TASKRUN` (run completion task-work only when the app asks,
        removing interrupt-time work from the hot path), `IORING_SETUP_COOP_TASKRUN` and
        `IORING_SETUP_TASKRUN_FLAG` are the flags a 6.x-era design uses. Benchmarks and blog posts
        from the 5.x era measure a materially different implementation. `[VERSION-TRAP]`
        `[RESEARCH]`
3.12.11 `[TRAP]` **It is also the most widely disabled fast interface in Linux.** A run of
        privilege-escalation CVEs led Docker's and containerd's default seccomp profiles and several
        hardened distributions to block **`io_uring_setup`** outright, Google disabled it across
        ChromeOS/Android, and the kernel now ships `kernel.io_uring_disabled`
        (**0** = allowed, **1** = allowed only with `CAP_SYS_ADMIN`, **2** = disabled entirely).
        "Just use io_uring" is not deployable advice until you have read the target's seccomp
        profile and that sysctl. `[TRAP]` `[SYSCTL]` `[RESEARCH]`
3.12.12 `[API]` **The Java position, stated honestly.** The JDK has **no** io_uring support: NIO is
        `epoll`-based and `AsynchronousFileChannel` uses a thread pool. The options are Netty's
        incubating `io_uring` transport, or a Java 21 **FFM** binding (`Linker`,
        `SymbolLookup.libraryLookup("liburing")`, `MemorySegment` over the mapped rings) —
        which is a legitimate design exercise precisely because the rings are shared memory and FFM
        can address them without JNI. `[API]` `[X-REF 04]`
3.12.13 `[CALC]` **What `FundsLedger` would actually gain, computed.** At **13,600 writes/sec**
        peak with one `write` + one `fsync` per batch of 1,000, the syscall count is already tiny —
        so io_uring buys nothing there. The case it *would* win is the read path: the reservation
        expiry index doing scattered 180-byte reads at high concurrency, where 64 `IORING_OP_READ`
        SQEs per `io_uring_enter` replace 64 syscalls plus 64 thread blocks. State the arithmetic
        before adopting it, because the honest answer for most Spring Boot services is that the
        syscall count was never the bottleneck. `[CALC]` `[PROVE]`

*(13 leaves)*

## §3.13 `futex` and how a mutex, a `park`, and a JVM monitor actually block

3.13.1 `[PROVE]` **The idea, and why it is fast.** A futex is a **32-bit word in ordinary user
       memory**. The uncontended case is an atomic operation on that word with **no syscall and no
       kernel state whatsoever**; the kernel is involved only to *sleep* and *wake*. Every fast
       userspace lock on Linux — glibc mutexes, condvars, semaphores, `pthread_join`, JVM monitors,
       `LockSupport` — is built on this one primitive. `[PROVE]`
3.13.2 `[SOURCE]` **The syscall.** `man 2 futex` gives
       `long syscall(SYS_futex, uint32_t *uaddr, int op, uint32_t val, const struct timespec *timeout, uint32_t *uaddr2, uint32_t val3)`
       — note there is **no glibc wrapper**, so it is always called through `syscall()`.
       `kernel/futex/core.c`, `waitwake.c`, `pi.c`, `requeue.c`. `[SOURCE]` `[SYSCALL]`
3.13.3 `[PROVE]` **`FUTEX_WAIT` is the race-free "check then sleep".** Per the man page: "the
       kernel will block only if the futex word has the value that the calling thread supplied (as
       one of the arguments of the futex() call) as the expected value of the futex word", and "the
       loading of the futex word's value, the comparison of that value with the expected value, and
       the actual blocking will happen atomically and will be totally ordered with respect to
       concurrent operations performed by other threads on the same futex word". If the value
       already changed it returns **`EAGAIN`** and the caller retries the userspace fast path; a
       timeout gives `ETIMEDOUT`; a signal gives `EINTR`. Without this atomicity every lock
       implementation would have a lost-wakeup race. `[PROVE]` `[SOURCE]`
3.13.4 `[TABLE]` **The operations that matter.** `FUTEX_WAKE(nr)` wakes up to `nr` waiters (1 for
       `signal`, `INT_MAX` for `broadcast`); **`FUTEX_PRIVATE_FLAG`** skips the shared-mapping key
       lookup and is a measurable win for process-private locks (glibc uses it by default);
       `FUTEX_CLOCK_REALTIME` selects the timeout clock; `FUTEX_WAIT_BITSET`/`WAKE_BITSET` allow
       selective wakeups on one word; **`FUTEX_CMP_REQUEUE`** *moves* waiters from a condvar's
       queue to a mutex's queue instead of waking them all — the reason
       `pthread_cond_broadcast` does not produce a thundering herd; `FUTEX_WAKE_OP` for
       atomic-op-plus-wake. `[TABLE]` `[SOURCE]`
3.13.5 `[SOURCE]` **Kernel-side state, and what `wchan` shows.** Waiters hash into a global table
       `futex_queues[]` by `union futex_key` — `{mm, address}` for private futexes,
       `{inode, offset}` for shared ones — via `futex_hash()`; each waiter is a `struct futex_q`
       enqueued on the bucket and parked in `futex_wait_queue()`. A thread whose
       `/proc/<pid>/task/<tid>/wchan` reads `futex_wait_queue` is blocked on a lock, full stop —
       not on I/O, not on the network. `[SOURCE]` `[PROC]` `[DIAG]`
3.13.6 **Priority-inheritance and robust futexes.** `FUTEX_LOCK_PI`/`LOCK_PI2`/`TRYLOCK_PI`/
       `UNLOCK_PI` back an `rt_mutex` so a low-priority holder is boosted to the waiter's priority
       (the fix for classic priority inversion, and why `PTHREAD_PRIO_INHERIT` exists);
       `set_robust_list`/`get_robust_list` plus the `FUTEX_OWNER_DIED` bit let the kernel release a
       futex whose owner died holding it, converting a permanent deadlock into an
       `EOWNERDEAD` the next acquirer can handle. `[SYSCALL]`
3.13.7 `[VERSION-TRAP]` **`FUTEX_WAITV` and futex2.** `futex_waitv(2)` (5.16+) waits on **multiple
       futexes at once** — the operation game emulation layers needed and the direction the API is
       moving, with `futex_wait`/`futex_wake`/`futex_requeue` landing as separate syscalls rather
       than one multiplexed `op` argument. Answers describing `futex()` as "the" interface are
       becoming version-scoped. `[VERSION-TRAP]` `[RESEARCH]`
3.13.8 `[FLOW]` **glibc `pthread_mutex_lock`, exactly.** The lock word
       (`pthread_mutex_t.__data.__lock`) has three states — 0 free, 1 held-uncontended,
       2 held-contended. (1) CAS 0→1; success means **zero syscalls, ~10–20 ns, done**.
       (2) On failure, for `PTHREAD_MUTEX_ADAPTIVE_NP`, spin a bounded number of iterations.
       (3) Set the word to 2 and call `futex(&lock, FUTEX_WAIT_PRIVATE, 2, NULL)`; wake, re-CAS,
       loop. Unlock: store 0, and **only if the word was 2** call `futex(FUTEX_WAKE_PRIVATE, 1)` —
       so an uncontended unlock is also syscall-free. That "only if contended" test is the whole
       reason uncontended locking is free. `[FLOW]` `[PROVE]` `[SOURCE]`
3.13.9 **`pthread_cond_wait` and why spurious wakeups are unavoidable.** It releases the associated
       mutex, `futex(FUTEX_WAIT)`s on the condvar's internal signal counter, and reacquires the
       mutex on wake — and because the predicate may have been changed by another thread between the
       wake and the reacquisition, the caller **must** re-check in a loop. `signal` is
       `FUTEX_WAKE(1)`; `broadcast` uses `FUTEX_CMP_REQUEUE`. This is the C-level origin of the
       `while (!condition) wait();` rule in Java. `[PROVE]` `[X-REF 05]`
3.13.10 `[FLOW]` `[SOURCE]` **The chain, named at every hop — the highest-value trace in this
        part.** `LockSupport.park()` → `Unsafe.park(boolean, long)` (a JVM intrinsic; the native
        implementation is `Unsafe_Park` in `hotspot/share/prims/unsafe.cpp`) →
        `JavaThread::parker()->park()` → `Parker::park(bool isAbsolute, jlong time)` in
        `hotspot/os/posix/park_posix.cpp` → `pthread_mutex_lock` on the parker's mutex, then
        `pthread_cond_wait` / `pthread_cond_timedwait` on its condvar → glibc →
        **`futex(uaddr, FUTEX_WAIT_PRIVATE, …)`**. The reverse: `LockSupport.unpark(t)` →
        `Unsafe.unpark` → `Parker::unpark()` → `pthread_cond_signal` → **`futex(FUTEX_WAKE_PRIVATE, 1)`**
        → the kernel wakes the `task_struct`, which then waits on a run queue. Every
        `ReentrantLock`, `ArrayBlockingQueue`, `CountDownLatch`, `CompletableFuture.get()` and
        `ThreadPoolExecutor` take blocks in your service ends here. `[FLOW]` `[SOURCE]`
        `[X-REF 05]`
3.13.11 `[VERSION-TRAP]` **`synchronized` takes a parallel route.** Uncontended acquisition is a
        CAS on the object's **mark word**. On contention `ObjectMonitor::enter` /
        `ObjectMonitor::EnterI` (`hotspot/share/runtime/objectMonitor.cpp`) performs **adaptive
        spinning** (`TrySpin`, tuned from recent success) before parking on
        `os::PlatformEvent::park` → `pthread_cond_wait` → `futex`. Version facts to state rather
        than assume: **biased locking was removed in JDK 15 (JEP 374)**, so "biased locking makes
        repeated uncontended `synchronized` free" is stale; JDK 21+ carries **lightweight
        locking** (`-XX:LockingMode`) in place of stack-locking; and `-XX:-UseBiasedLocking` is now
        a no-op flag. `[VERSION-TRAP]` `[API]` `[RESEARCH]`
3.13.12 `[CALC]` **The cost ladder, and the convoy it produces.** Uncontended CAS **~10–20 ns**; a
        successful spin, tens of ns; a **park/unpark round trip = 2 syscalls + a context switch +
        run-queue wait ≈ 3–10 µs** when the CPU is free, and unbounded when it is not. Now apply
        Little's Law to the **3,400/sec settlement burst**: a `FundsLedger` reservation-index lock
        held for 50 µs gives ρ = 3,400 × 50 µs = **0.17** and negligible queueing; the same lock
        held **250 µs** gives ρ = **0.85**, and mean wait explodes to roughly
        `ρ/(1−ρ) × 250 µs ≈ 1.4 ms` — with every waiter paying two syscalls and a scheduling delay
        on top. Lock **hold time**, not lock count, is the variable. `[CALC]` `[PROVE]`
        `[X-REF 22]`
3.13.13 `[DIAG]` **Proving contention, in escalating order of cost:**
        `/proc/<pid>/status`'s `nonvoluntary_ctxt_switches` versus `voluntary_ctxt_switches`
        (voluntary switches dominating with low CPU = blocking, not compute);
        `wchan = futex_wait_queue` across `/proc/<pid>/task/*`; `strace -c` `futex` share on a
        staging repro only; **`perf lock contention -ab -- sleep 5`** (built on the
        `lock:contention_begin`/`_end` tracepoints, giving per-callsite wait totals);
        `bpftrace` on `syscall:futex` enter/exit with `@[ustack] = hist(latency)`;
        `offcputime -p <pid>` for off-CPU stacks; and on the Java side `jcmd Thread.print`
        `BLOCKED` counts plus JFR's `JavaMonitorEnter` and `ThreadPark` events with their
        `monitorClass`/`parkedClass` fields. `[DIAG]` `[BUILD]`

*(13 leaves)*

## §3.14 Signal delivery internals: from `kill` to the handler frame

3.14.1 `[FLOW]` **Generation.** `kill(pid, sig)` → `sys_kill` → `group_send_sig_info` →
       `send_signal_locked`: allocate a `struct sigqueue`, set the bit in
       `task->signal->shared_pending` for a **process-directed** signal (`kill`, `tgkill` to the
       group) or in `task->pending` for a **thread-directed** one (`tgkill`,
       `pthread_kill`), set `TIF_SIGPENDING` on the target, and wake it if it is
       `TASK_INTERRUPTIBLE`. Note what did **not** happen: no handler ran, nothing was delivered.
       `[FLOW]` `[SOURCE]`
3.14.2 **Which thread gets a process-directed signal.** `wants_signal()` picks any thread that has
       not blocked it and is not exiting — effectively arbitrary. That non-determinism is exactly
       why the JVM **blocks** most signals on every thread and dedicates one **"Signal Dispatcher"**
       thread with them unblocked, turning an arbitrary-thread event into a predictable one.
       `[PROVE]` `[API]`
3.14.3 `[PROVE]` **Delivery happens only on the way back to userspace.** `exit_to_user_mode_loop`
       (§3.3.5) sees `TIF_SIGPENDING` → `arch_do_signal_or_restart()` → `get_signal()` dequeues the
       highest-priority pending signal and consults the disposition → `handle_signal()` builds a
       frame, or the default action runs. **A task in `TASK_UNINTERRUPTIBLE` never reaches this
       point**, which is the complete mechanical explanation of why `kill -9` does nothing to a
       `D`-state thread stuck in `io_schedule`. `[PROVE]` `[FLOW]`
3.14.4 `[SOURCE]` **The handler frame, built on the user stack.** `setup_rt_frame()` pushes a
       `struct rt_sigframe`: the return-trampoline address, a `siginfo_t`, and a `ucontext_t`
       containing the saved `sigcontext` (all general registers plus `RIP`, `RSP`, `RFLAGS`, `CR2`
       for a fault), a pointer to the saved FPU/extended state (`xsave` area), and the **signal mask
       to restore**. It then sets `RIP` to the handler, `RDI`/`RSI`/`RDX` to
       `signo`/`siginfo`/`ucontext` per the `SA_SIGINFO` ABI, and returns to ring 3. If
       `sigaltstack` was registered and `SA_ONSTACK` is set, the frame goes on the alternate stack
       — which is the only way to handle a `SIGSEGV` caused by stack overflow. `[SOURCE]`
       `[FLOW]`
3.14.5 **`rt_sigreturn` is how the handler gets back.** The trampoline (in the vDSO) calls
       `rt_sigreturn`, and the kernel restores registers, FPU state and signal mask from the frame —
       trusting the frame, which is why SROP (sigreturn-oriented programming) is an exploit class
       and why the frame layout is not something to be clever with. `[SOURCE]` `[X-REF 13]`
3.14.6 `[TABLE]` **`sigaction` flags and the `EINTR` contract.** `SA_RESTART` makes the kernel
       restart *restartable* syscalls transparently (`read` on a regular file, `wait4`), but
       **`nanosleep`, `poll`, `epoll_wait`, `select` and timeout-carrying calls never restart** —
       they return `EINTR` or a short result regardless. `SA_SIGINFO` (three-argument handler),
       `SA_ONSTACK`, `SA_NODEFER` (do not block this signal inside its own handler),
       `SA_RESETHAND`, `SA_NOCLDWAIT`/`SA_NOCLDSTOP`. `signal()` has historically ambiguous
       semantics; always `sigaction`. `[TABLE]` `[TRAP]`
3.14.7 `[PROVE]` **Standard signals are not queued; realtime signals are.** Signals 1–31 are a
       **bitmask**, so a second pending `SIGCHLD` while one is pending is *coalesced and lost* — a
       parent that reaps one child per `SIGCHLD` leaks zombies under a burst, and the correct
       handler loops `waitpid(-1, …, WNOHANG)` until it returns 0. `SIGRTMIN`–`SIGRTMAX` (**34–64**)
       are queued in FIFO order with their `sigval`, bounded by `RLIMIT_SIGPENDING` and reported as
       `SigQ:` in `/proc/<pid>/status`. `[PROVE]` `[TRAP]` `[NUM]`
3.14.8 **The two that cannot be caught, blocked or ignored.** `SIGKILL` (**9**) and `SIGSTOP`
       (**19**) are handled in `prepare_signal`/`get_signal` before any user disposition is
       consulted; `SIGKILL` sets `SIGNAL_GROUP_EXIT` so **every** thread in the group exits at its
       next kernel-exit point. Hence: no shutdown hook runs, no `finally` block runs, no heap dump
       is written, and the only evidence is the exit status **137** and a `dmesg`/`memory.events`
       record. `[NUM]` `[PROVE]`
3.14.9 `[TRAP]` **PID 1 in a namespace has no default actions.** For a signal PID 1 has not
       installed a handler for, the kernel discards it rather than applying the default action — a
       deliberate protection so an init cannot be accidentally killed. So `docker stop` →
       `SIGTERM` → a Java PID 1 with no `SIGTERM` handling → **nothing happens** until the 10-second
       `SIGKILL`. The three fixes: `--init`/`tini` as PID 1, an actual shutdown hook, or
       `exec`-form `ENTRYPOINT` so the shell is not PID 1. `[TRAP]` `[X-REF 19]`
3.14.10 `[API]` **The JVM's signal surface, named.** It installs handlers for `SIGSEGV`, `SIGBUS`,
        `SIGFPE`, `SIGILL` (all used as *control flow* — see §3.18.2), `SIGPIPE` (ignored, so a
        write to a closed socket returns `EPIPE` as an `IOException` instead of killing the
        process), **`SIGQUIT`** (`kill -3` → full thread dump to stdout), and
        `SIGTERM`/`SIGINT`/`SIGHUP` → the Signal Dispatcher thread → `Runtime.addShutdownHook`
        callbacks. `-Xrs` ("reduce signal usage") hands `SIGQUIT`/`SIGTERM`/`SIGINT` back to the
        default disposition and **disables shutdown hooks on signal** — correct only when an
        embedding native app owns them. `jdk.internal.misc.Signal`/`sun.misc.Signal` is the
        programmatic hook. `[API]` `[TRAP]`
3.14.11 `[CALC]` **Graceful shutdown is a signal problem with two timers that must be ordered.**
        Kubernetes: endpoint removal → `preStop` hook → `SIGTERM` → wait
        `terminationGracePeriodSeconds` (**30** default) → `SIGKILL`. Spring Boot:
        `server.shutdown=graceful` stops accepting and drains in-flight requests within
        `spring.lifecycle.timeout-per-shutdown-phase` (**30s** default). If the two are equal the
        `SIGKILL` lands exactly as the drain completes; the safe ordering is
        `preStop sleep (≥ readiness propagation) + drain timeout < terminationGracePeriodSeconds`.
        For `BankWithdrawal`, whose **drain-before-terminate** requirement covers a `PaymentRun` of
        1.8k records taking 5–40 minutes, no grace period is long enough — the answer is an
        operator-gated drain and a shutdown hook that refuses new runs, not a bigger timeout.
        `[CALC]` `[API]` `[X-REF 19]`
3.14.12 `[DIAG]` **Reading and proving signal state.** `/proc/<pid>/status`'s hex masks —
        `SigPnd` (thread-pending), `ShdPnd` (process-pending), `SigBlk`, `SigIgn`, `SigCgt`
        (**decode this to see exactly which signals the JVM caught**), `SigQ` (queued/limit).
        `signalfd` for signals as a readable fd (composes with `epoll`, unlike a handler).
        `bpftrace -e 'tracepoint:signal:signal_generate { printf("%s -> pid %d sig %d\n", comm, args->pid, args->sig); }'`
        plus `signal:signal_deliver` answers "who sent the `SIGTERM`" — which in a Kubernetes
        incident is the difference between blaming the kubelet, the OOM killer and your own
        supervisor. `[DIAG]` `[PROC]` `[BUILD]`

*(12 leaves)*

## §3.15 cgroup v2 internals: the hierarchy, controller enablement, and how accounting happens

3.15.1 `[SOURCE]` **The objects.** A `struct cgroup` per directory, holding an array of
       `struct cgroup_subsys_state` (`css`) — one per enabled controller — and a list of
       `struct css_set`s. A task points at a `css_set`, which is the *interned tuple* of all its
       controller states, shared by every identically-placed task; migration swaps the pointer, so
       moving a process between cgroups is cheap. `kernel/cgroup/cgroup.c`,
       `kernel/cgroup/{cpuset,pids,rdma}.c`, `mm/memcontrol.c`, `block/blk-cgroup.c`.
       `[SOURCE]`
3.15.2 `[SOURCE]` **Two files, two meanings — the single most misread part of cgroup v2.**
       `cgroup.controllers` lists what is **available in this cgroup**;
       `cgroup.subtree_control` lists what is **enabled for its children**
       (`echo "+cpu +memory -io" > cgroup.subtree_control`). A controller therefore cannot be
       enabled unless the parent enabled it for children — the **top-down** rule — and cannot be
       disabled while a child has it enabled. Writing to the wrong file is the usual cause of
       "I set the limit and nothing happened". `[SOURCE]` `[TRAP]`
3.15.3 `[SOURCE]` **The no-internal-process constraint, quoted:** "Non-root cgroups can distribute
       domain resources to their children only when they don't have any processes of their own."
       So a cgroup either **holds processes** or **distributes to children**, never both — which is
       why systemd and Kubernetes build `slice → scope` trees with leaves-only membership, and why
       an attempt to add `+cpu` to a directory containing your JVM returns `EBUSY`. `[SOURCE]`
       `[PROVE]`
3.15.4 **`cgroup.type` and threaded subtrees.** `domain` (normal), `domain threaded` (root of a
       threaded subtree), `threaded` (a member — populated via `cgroup.threads`, and the *only*
       way to place individual threads of one process in different cgroups),
       `domain invalid`. Only `cpu`, `cpuset`, `perf_event` and `pids` are threaded-capable;
       `memory` and `io` are not, because you cannot charge a page to a thread. Relevant if you
       ever want to cap `FundsLedger`'s GC threads separately from its request threads.
       `[SOURCE]` `[TRAP]`
3.15.5 `[PROC]` **Population, migration and the kill switch.** `cgroup.procs` (write a pid — the
       **whole thread group** moves), `cgroup.threads`, `cgroup.events` (`populated 0|1`,
       `frozen 0|1` — pollable, so a supervisor can wait for emptiness without polling),
       `cgroup.freeze` (write 1 to `SIGSTOP`-equivalent the whole subtree without racing on
       signals), **`cgroup.kill`** (write 1 to `SIGKILL` every task in the subtree atomically — the
       correct way to terminate a process tree, and what you want instead of a `pkill -f` loop),
       `cgroup.stat` (`nr_descendants`, `nr_dying_descendants`). `[PROC]` `[BUILD]`
3.15.6 `[PROVE]` **How memory accounting actually happens: first-toucher pays.** Every page is
       charged at allocation time by `mem_cgroup_charge()` to the cgroup of the **allocating task**,
       recorded in the folio's `memcg_data` pointer, with a per-CPU stock of
       `MEMCG_CHARGE_BATCH` (**64**) pages so the common case is not an atomic per page. Two
       consequences that surprise everyone: a **shared page-cache page is charged to whichever
       container read it first** and stays charged until reclaimed, so `BankDeposits` reading a
       statement file can be charged for cache that `FundsLedger` then benefits from; and a page
       charged to a dying cgroup keeps it in `nr_dying_descendants` until reclaimed. `[PROVE]`
       `[SOURCE]`
3.15.7 `[SOURCE]` **The four memory knobs are a stack, not four versions of the same thing.**
       `memory.min` (default **0**) — "memory won't be reclaimed if usage stays within this
       boundary", hard protection; `memory.low` (**0**) — best-effort, "reclaim deprioritizes this
       cgroup unless unavoidable"; `memory.high` (**max**) — a **throttle**: exceeding it triggers
       reclaim pressure and sleeps the allocating task, but never OOM; `memory.max` (**max**) — a
       hard limit, "OOM killer invoked if exceeded and cannot reduce". The design point: for a JVM,
       `memory.high` degrades and `memory.max` kills — yet Kubernetes `limits.memory` sets
       **`memory.max`**, which is why a pod with a slow native leak dies at 137 rather than
       reclaiming. `memory.min` on `FundsLedger` is how you protect its page cache from a co-located
       ingestion. `[SOURCE]` `[TRAP]`
3.15.8 `[PROC]` **`memory.stat` is the only honest per-container memory report**, and the reason
       `free` inside a container is useless: `anon`, `file`, `kernel`, `kernel_stack`,
       **`pagetables`**, `slab_reclaimable`/`slab_unreclaimable`, `sock`, `shmem`, `file_mapped`,
       `file_dirty`, `file_writeback`, `anon_thp`, `inactive_anon`/`active_anon`,
       `inactive_file`/`active_file`, `pgfault`/`pgmajfault`, `pgscan`/`pgsteal` split by
       `kswapd`/`direct`, `workingset_refault_anon`/`_file`, `thp_fault_alloc`. Plus
       `memory.current`, `memory.peak`, `memory.numa_stat`, `memory.swap.{current,high,max,events}`,
       `memory.events`, `memory.reclaim` (write a byte count to force proactive reclaim).
       `[PROC]` `[TABLE]`
3.15.9 `[SOURCE]` **CPU control, both halves.** `cpu.weight` (default **100**, range **[1, 10000]**)
       is proportional and becomes the `load` on the group's `sched_entity` (§3.2.7);
       `cpu.weight.nice` expresses the same thing on the nice scale. `cpu.max` is
       `"$MAX $PERIOD"`, default **`"max 100000"`** in microseconds, implemented by CFS bandwidth
       (§3.2.10); `cpu.max.burst` allows accumulated unused quota to be spent in a burst;
       `cpu.idle` marks the group `SCHED_IDLE`. `cpu.stat` reports `usage_usec`, `user_usec`,
       `system_usec`, **`nr_periods`**, **`nr_throttled`**, **`throttled_usec`** (plus burst
       fields). `[SOURCE]` `[SYSCTL]`
3.15.10 `[CALC]` **Why throttling presents as p99 latency on an idle-looking node — the arithmetic.**
        `cpu.max = "200000 100000"` grants 200 ms of CPU per 100 ms period. A `ClientRestrictions`
        JVM on a 16-vCPU node runs 8 GC threads, 2 JIT compiler threads and 4 event-loop threads;
        if 12 of them are runnable simultaneously they consume the 200 ms budget in **~17 ms** of
        wall clock, and the group is then **dequeued for the remaining ~83 ms** — nearly **three
        times** the entire 30 ms budget — while the node reports ~25% utilisation. Proof:
        `nr_throttled / nr_periods` and `throttled_usec` in `cpu.stat`, correlated with the p99
        histogram. The fixes in order of effect: reduce the *thread count*
        (`-XX:ActiveProcessorCount`, `-XX:ParallelGCThreads`, `-XX:CICompilerCount`), then raise
        quota, then shorten the period. Raising quota alone often just moves the cliff. `[CALC]`
        `[PROC]` `[TRAP]`
3.15.11 `[TABLE]` **The rest of the controller set in one place.** `io.max`/`io.latency`/
        `io.weight`/`io.stat`/`io.pressure` (§3.9.12) plus the cgroup-writeback attribution that
        makes buffered writes chargeable; `pids.max` (**max**) / `pids.current` / `pids.events`;
        `cpuset.cpus`/`cpuset.mems`/`cpuset.cpus.effective`/`cpuset.cpus.partition` (exclusive CPU
        partitions — the cgroup way to do what `isolcpus` does at boot); `hugetlb.<size>.max`;
        `misc.max` (accelerators); `rdma.max`; and `memory.oom.group` (§3.7.8). `[TABLE]`
        `[SYSCTL]`
3.15.12 `[PROC]` **Delegation, and finding your own cgroup.** systemd's `Delegate=yes` hands a
        subtree to a service to manage; Kubernetes with the systemd cgroup driver puts a container
        at
        `/sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod<uid>.slice/cri-containerd-<id>.scope/`.
        From inside the container, `cat /proc/self/cgroup` gives `0::<path>` **relative to the
        cgroup namespace root**, so the path you see is not the path on the host — and
        `/sys/fs/cgroup/` inside the container is the namespace-rooted view when
        `cgroupns=private`. Knowing which of the two you are reading is the difference between
        reading your limit and reading the node's. `[PROC]` `[TRAP]`
3.15.13 `[API]` **How the JVM reads all of this.** `hotspot/os/linux/cgroupSubsystem_linux.cpp` /
        `cgroupV2Subsystem_linux.cpp` detect the hierarchy from `/proc/self/mountinfo` and
        `/proc/self/cgroup`, then read `memory.max`, `memory.swap.max`, `cpu.max`, `cpu.weight`,
        `pids.max`. `-XX:+UseContainerSupport` (**on by default** since JDK 10) drives
        `MaxRAMPercentage` (**25.0**) and
        `Runtime.availableProcessors() = ceil(quota/period)`, overridable with
        `-XX:ActiveProcessorCount`. Verify with `java -Xlog:os+container=trace -version`. Failure
        mode to know: if the host cgroupfs is bind-mounted in, or the container is in the root
        cgroup, the JVM reads **`max`** and sizes itself from the node — a 4 GB pod taking a 48 GB
        heap decision. `[API]` `[TRAP]` `[X-REF 19]`

*(13 leaves)*

## §3.16 Namespace internals: `unshare`, `setns`, `/proc/PID/ns`, and what a container is

3.16.1 `[TABLE]` **The eight namespaces and the exact kernel object each virtualises:**
       `mnt` (`struct mnt_namespace` — the mount tree), `pid` (`struct pid_namespace` — the
       pid→task mapping, nestable), `net` (**`struct net`** — an entire stack instance: interfaces,
       routing tables, netfilter rules, conntrack, *and its own `net.*` sysctls*),
       `uts` (`struct uts_namespace` — hostname and domainname), `ipc` (SysV objects, POSIX message
       queues and `/dev/shm`), `user` (`struct user_namespace` — uid/gid maps and the capability
       model), `cgroup` (what the cgroup path root looks like), `time`
       (`CLOCK_MONOTONIC`/`CLOCK_BOOTTIME` offsets only). `[TABLE]` `[SOURCE]`
3.16.2 **`nsproxy` and lifetime.** `task_struct->nsproxy` points to a refcounted
       `struct nsproxy` holding all namespaces except the user namespace (which hangs off
       `cred`). A namespace lives as long as *any* task or *any* open `/proc/PID/ns/*` fd or bind
       mount references it — which is exactly the mechanism behind `ip netns add` (a bind mount in
       `/var/run/netns/`) and `docker run --net=container:<id>`, and the reason a "leaked"
       namespace outlives every process in it. `[PROVE]` `[SOURCE]`
3.16.3 `[SYSCALL]` **The three ways in, and the asymmetry that trips people.**
       `int unshare(int flags)` moves **the caller** into new namespaces;
       `int setns(int fd, int nstype)` joins an **existing** one via an `/proc/PID/ns/<type>` fd;
       `clone(CLONE_NEW*)` creates them for the **child**. The asymmetry: `unshare(CLONE_NEWPID)`
       does **not** move the caller into the new pid namespace — only its subsequent children enter
       it, because a task's pid cannot change. Same for `setns` on a pid namespace. This is why
       `unshare --pid --fork` exists. `[SYSCALL]` `[TRAP]`
3.16.4 `[PROC]` **`/proc/PID/ns/` is the ground truth.** Each entry is a magic symlink reading
       `pid:[4026531836]`, `net:[4026532008]`, …; **two processes share a namespace iff the inode
       numbers match**, and that comparison is the only reliable test. Tooling:
       `lsns -p <pid>`, `readlink /proc/self/ns/net`, and
       `nsenter -t <pid> -n ss -tnp` / `nsenter -t <pid> -a` to debug a container's stack from the
       node using the host's tools. `[PROC]` `[DIAG]`
3.16.5 `[PROVE]` **PID namespace semantics, precisely.** They nest; the first process created in one
       is **PID 1** there and carries init semantics (§3.14.9); a task has a pid **in every ancestor
       namespace** (`struct pid`'s `numbers[]` array indexed by level), and `getpid()` returns the
       one for the caller's own namespace. `/proc` must be remounted inside the namespace to reflect
       it. Killing PID 1 kills the whole namespace. Operationally: a pid seen inside the container
       means nothing on the host, `/proc/<hostpid>/root/…` is how you reach into its filesystem, and
       `/proc/<hostpid>/status`'s `NSpid:` line gives both numbers at once. `[PROVE]` `[PROC]`
3.16.6 **User namespaces, and the property that makes rootless containers possible.**
       `/proc/PID/uid_map` and `gid_map` (`inside-id outside-id length`, written once, needing
       `CAP_SETUID` in the parent for multi-id maps), plus `/proc/PID/setgroups` which must be
       `deny` before an unprivileged single-id map. The key property: **root inside the namespace
       holds full capabilities over objects owned by that namespace only** — it can mount a tmpfs
       and chown its own files, and cannot touch the host's. Guards:
       `/proc/sys/user/max_user_namespaces`, `kernel.unprivileged_userns_clone` on Debian-family
       kernels. Historically the richest container-escape surface. `[SOURCE]` `[X-REF 13]`
3.16.7 `[FLOW]` **Exactly how runc builds a root filesystem.** (1) `unshare(CLONE_NEWNS)`;
       (2) `mount(NULL, "/", NULL, MS_REC|MS_PRIVATE, NULL)` so nothing propagates back to the
       host; (3) mount the overlayfs (lower = image layers, upper = container rw layer) and the bind
       mounts for volumes, `/proc`, `/sys`, `/dev`; (4) `pivot_root(new_root, put_old)`;
       (5) `umount2(put_old, MNT_DETACH)` and `chdir("/")`. Step 2 is the one people omit, and its
       absence is how a container mount leaks onto the node. `[FLOW]` `[PROVE]`
3.16.8 `[TRAP]` **Network sysctls are per-namespace, and this silently undoes tuning.** Because a
       netns is a whole `struct net`, `net.core.somaxconn`, `net.ipv4.tcp_rmem`,
       `net.ipv4.ip_local_port_range`, `net.ipv4.tcp_tw_reuse` and conntrack limits set on the
       **host** have **no effect** on `ApplicationGateway` in its own netns. In Kubernetes the only
       supported route is `securityContext.sysctls` (with the unsafe ones gated by the kubelet's
       `--allowed-unsafe-sysctls`) or an init container. Meanwhile `net.core.*` in `/proc/sys` read
       from inside the container shows the *namespace's* value, so a mismatch is silent both ways.
       `[TRAP]` `[SYSCTL]` `[X-REF 10]`
3.16.9 `[PROVE]` **What is *not* namespaced, which is the whole reason `top` lies.** The kernel and
       its version, `/proc/cpuinfo`, **`/proc/meminfo`**, **`/proc/stat`**, `/proc/loadavg`,
       `/proc/vmstat`, `/proc/interrupts`, all of `/sys` (except a namespaced `/sys/class/net`),
       `dmesg`, the system clock (only offsets are namespaced), `/proc/sys` outside `net.*`, and
       the scheduler's view of CPUs. Therefore `free` and `top` inside a container report the
       **node**, `nproc` reports the node's CPUs unless a cpuset restricts it, and the JVM had to
       learn to read **cgroup files** instead — which is precisely §3.15.13. `[PROVE]` `[TRAP]`
3.16.10 `[PROVE]` **The complete definition, worth memorising.** A container is a `task_struct`
        with (a) a distinct `nsproxy`, (b) membership in a cgroup carrying limits, (c) a seccomp
        filter, (d) a reduced capability set, (e) a root filesystem installed by `pivot_root` over
        an overlayfs, and optionally (f) an LSM label (SELinux/AppArmor). **There is no container
        object in the kernel** — no new scheduler entity, no hypervisor, no VM. Say it this way and
        every container question decomposes into the Linux mechanisms in this part. `[PROVE]`
        `[X-REF 19]`
3.16.11 `[PROC]` **Capabilities as the fourth leg.** Five sets in `/proc/<pid>/status`:
        `CapInh`, `CapPrm`, `CapEff`, `CapBnd` (the bounding set — a ceiling `execve` cannot
        exceed), `CapAmb` (ambient, inherited across a non-setuid `execve`). The ones that decide
        whether your JVM is debuggable: **`CAP_SYS_PTRACE`** (`jcmd`/`jstack`/`jattach` across
        processes, plus `/proc/sys/kernel/yama/ptrace_scope` = 1 by default restricting it to
        descendants), **`CAP_PERFMON`** (`perf`, eBPF profiling), **`CAP_IPC_LOCK`**
        (`-XX:+UseLargePages`, `mlock`), `CAP_NET_BIND_SERVICE` (ports < 1024),
        `CAP_SYS_RESOURCE` (raise hard rlimits), `CAP_BPF`. Read with `capsh --print` /
        `getpcaps <pid>`; `NoNewPrivs: 1` blocks regaining any of them. `[PROC]` `[X-REF 13]`
3.16.12 `[BUILD]` **The complete "attach to a JVM inside a container from the node" recipe**, since
        this is where namespace knowledge pays off: (1) get the container pid —
        `crictl inspect --output go-template --template '{{.info.pid}}' <id>`; (2) confirm the
        namespaces — `lsns -p <pid>`, `readlink /proc/<pid>/ns/pid`; (3) get the **namespace-local**
        pid — `grep NSpid /proc/<pid>/status`, because `jcmd` addresses the target by *its own*
        pid and looks for `/tmp/.java_pid<nspid>`; (4) either `nsenter -t <pid> -m -p -u -- jcmd
        <nspid> Thread.print`, or run a debug container with
        `shareProcessNamespace: true`/`hostPID: true` plus `CAP_SYS_PTRACE`, or use `jattach`
        which handles the namespace translation itself. Failing at step 3 is the single most common
        reason "`jcmd` says process not found" while the JVM is plainly running. `[BUILD]`
        `[DIAG]` `[TRAP]`

*(12 leaves)*

## §3.17 eBPF: the mechanism, the verifier, maps, and `bpftrace`

3.17.1 `[FLOW]` **The mechanism end to end.** Restricted C → `clang -target bpf` → an ELF carrying
       **BTF** type information → `bpf(BPF_PROG_LOAD)` → the **verifier** rejects or accepts →
       JIT compilation to native code (`net.core.bpf_jit_enable`) → attach to a hook → the program
       runs **in kernel context on every event**, writing results into a **map** that userspace
       reads asynchronously. Nothing is interpreted in production and nothing is copied per event.
       `[FLOW]` `[PROVE]`
3.17.2 `[SYSCALL]` **`int bpf(int cmd, union bpf_attr *attr, unsigned int size)`** and the commands
       that matter: `BPF_PROG_LOAD`, `BPF_MAP_CREATE`, `BPF_MAP_LOOKUP_ELEM`/`UPDATE_ELEM`/
       `DELETE_ELEM`/`GET_NEXT_KEY`, `BPF_OBJ_PIN`/`OBJ_GET` (pin a program or map into `bpffs` at
       `/sys/fs/bpf` so it outlives the loader), `BPF_PROG_ATTACH`, `BPF_LINK_CREATE` (the modern
       refcounted attachment), `BPF_BTF_LOAD`, `BPF_PROG_TEST_RUN`. `bpftool prog list`,
       `bpftool map dump`, `bpftool link list` inspect all of it on a running box. `[SYSCALL]`
       `[DIAG]`
3.17.3 `[TABLE]` **Program types = where it can be attached**, and this decides what you can
       observe: `BPF_PROG_TYPE_KPROBE` (`kprobe`/`kretprobe` on any non-inlined kernel symbol in
       `/proc/kallsyms` — powerful and **unstable across kernels**),
       `TRACEPOINT`/`RAW_TRACEPOINT` (stable ABI, listed under
       `/sys/kernel/debug/tracing/events/`), `TRACING` (`fentry`/`fexit` — BTF-based, lower
       overhead than kprobe and with typed arguments), `PERF_EVENT` (sampling profiles, hardware
       counters), `SOCKET_FILTER`, `XDP`, `SCHED_CLS`/`SCHED_ACT` (tc), `CGROUP_SKB`/
       `CGROUP_SOCK_ADDR`, `LSM`, plus **uprobes and USDT** on userspace binaries including
       `libjvm.so`. `[TABLE]`
3.17.4 `[SOURCE]` **The verifier, precisely.** "First step does DAG check to disallow loops and
       other CFG validation"; the second phase "starts from the first insn and descends all possible
       paths. It simulates execution of every insn and observes the state change of registers and
       stack", tracking `struct bpf_reg_state` types — `NOT_INIT` ("the register has not been
       written to"), `SCALAR_VALUE` ("some value which is not usable as a pointer"), `PTR_TO_CTX`,
       `PTR_TO_MAP_VALUE`, `PTR_TO_STACK`, `CONST_PTR_TO_MAP` ("'Const' because arithmetic on these
       pointers is forbidden"), plus `PTR_TO_PACKET`, `PTR_TO_SOCKET` and their `_OR_NULL`
       variants — with value ranges tracked as tristate numbers (`tnum`). The code is
       `kernel/bpf/verifier.c`. `[SOURCE]` `[PROVE]`
3.17.5 `[NUM]` **State pruning and the analysis budget.** "For each new branch to analyse, the
       verifier looks at all the states it's previously been in when at this instruction. If any of
       them contain the current state as a subset, the branch is 'pruned'". The budget is
       `BPF_COMPLEXITY_LIMIT_INSNS` (**1,000,000** simulated instructions) — exceeding it gives
       "BPF program is too large" even for a small program with many paths. Bounded loops are
       allowed since 5.3, and `bpf_loop()` is the supported way to iterate a large count.
       Every `_OR_NULL` pointer must be NULL-checked before use, and every pointer arithmetic must
       be provably in bounds. `[NUM]` `[SOURCE]` `[TRAP]`
3.17.6 `[PROVE]` **The verifier *is* the product.** It is what makes running arbitrary code in ring
       0 on a production host defensible: the program is proven memory-safe, proven terminating, and
       proven bounded before a single instruction executes. That guarantee — not the tooling — is
       why eBPF replaced kernel modules, SystemTap and DTrace-for-Linux, and why you can attach a
       probe to `FundsLedger`'s host during an incident without a change-control conversation.
       `[PROVE]`
3.17.7 `[TABLE]` **Map types as the data plane.** `BPF_MAP_TYPE_HASH`/`ARRAY` (shared, needs
       atomics), `PERCPU_HASH`/`PERCPU_ARRAY` (lock-free counting — what an aggregation should use),
       `LRU_HASH` (bounded with automatic eviction, for per-connection state),
       `STACK_TRACE` (the store behind `@[ustack]`, sized by `stackmap` entries),
       `PERF_EVENT_ARRAY` (the legacy per-CPU event channel), **`RINGBUF`** (5.8+, single shared
       buffer, ordered, cheaper reservation-based API — the current default for streaming events),
       `SOCKMAP`/`SOCKHASH`, `PROG_ARRAY` (tail calls), `CGROUP_STORAGE`, `SK_STORAGE`.
       `[TABLE]`
3.17.8 **Helpers are the only kernel API a program has.** `bpf_map_lookup_elem`/`update_elem`,
       **`bpf_probe_read_kernel`/`bpf_probe_read_user`** (never a raw dereference — the verifier
       forbids it), `bpf_ktime_get_ns`, `bpf_get_current_pid_tgid` (tgid in the upper 32 bits — a
       classic off-by-shift bug), `bpf_get_current_comm`, `bpf_get_current_cgroup_id`,
       `bpf_get_stackid`/`bpf_get_stack`, `bpf_perf_event_output`,
       `bpf_ringbuf_reserve`/`_submit`, `bpf_trace_printk` (debug only — it writes to
       `trace_pipe`). Helper availability is **per program type**, which is the usual reason a
       program that compiles will not load. `[API]` `[TRAP]`
3.17.9 `[VERSION-TRAP]` **CO-RE and BTF changed the deployment model.** With
       `/sys/kernel/btf/vmlinux` present, `libbpf` relocates field offsets at load time
       (`BPF_CORE_READ`, a generated `vmlinux.h`), so **one binary runs across kernel versions** —
       `libbpf-tools` plus `bpftool gen skeleton`. The older BCC model shipped clang and kernel
       headers to the target and compiled on the fly: slow, fragile, and a 200 MB container image.
       Recommending "install bcc" in 2026 is recommending the previous generation.
       `[VERSION-TRAP]` `[BUILD]`
3.17.10 `[API]` **The `bpftrace` language surface you need at 3 a.m.** Probes: `kprobe:`/
        `kretprobe:`, `fentry:`/`fexit:`, `tracepoint:<cat>:<name>`, `uprobe:/path:sym`,
        `usdt:`, `profile:hz:99`, `interval:s:1`, `software:major-faults:1`,
        `hardware:cache-misses:`. Built-ins: `pid`, `tid`, `comm`, `nsecs`, `elapsed`, `cpu`,
        `arg0..argN`, `args->field`, `retval`, `ustack`, `kstack`, `curtask`, `cgroup`.
        Aggregations: `count()`, `sum()`, `avg()`, `min()`/`max()`, `hist()`, `lhist(v, min, max,
        step)`, `stats()`. Structure: `BEGIN`/`END`, `@map[key]`, `delete()`, `printf()`,
        predicates `/pid == $1/`. That list covers essentially every one-liner in this guide.
        `[API]`
3.17.11 `[TABLE]` **The tool inventory indexed by symptom**, which is how you should memorise it:
        scheduler delay → `runqlat`, `runqslower`, `cpudist`; "why is my thread not running" →
        `offcputime`, `wakeuptime`; on-CPU → `profile`, `perf record`; block I/O → `biolatency`,
        `biosnoop`, `bitesize`, `biotop`; filesystem → `ext4slower`/`xfsslower`, `filetop`,
        `cachestat`, `fsrwstat`; memory → `memleak`, `oomkill`, `shmsnoop`, `drsnoop` (direct
        reclaim); process lifecycle → `execsnoop`, `exitsnoop`, `killsnoop`; syscalls →
        `syscount`, `funclatency`, `argdist`; network → `tcpretrans`, `tcplife`, `tcpconnlat`,
        `tcpdrop`. `[TABLE]` `[DIAG]`
3.17.12 `[SYSCTL]` **Permissions and the deployment reality.** `CAP_BPF` + `CAP_PERFMON` were split
        out of `CAP_SYS_ADMIN` in 5.8; `kernel.unprivileged_bpf_disabled` ships as **2** on many
        distributions (disabled without a capability), `kernel.perf_event_paranoid` defaults to
        **2** and container runtimes often raise it, and **`bpf` and `perf_event_open` are both
        blocked by Docker's default seccomp profile**. The correct Kubernetes pattern is therefore a
        privileged DaemonSet with `hostPID: true` and the host's `/sys` mounted — never tooling
        installed into the application container. `[SYSCTL]` `[TRAP]` `[X-REF 13]`
3.17.13 `[BUILD]` **Three scripts that answer three QuizStakes questions.** (1) Prove a 30 ms
        `ClientRestrictions` breach is scheduler delay, not code:
        `bpftrace -e 'tracepoint:sched:sched_wakeup /args->pid == $1/ { @w[args->pid] = nsecs; } tracepoint:sched:sched_switch /@w[args->next_pid]/ { @runq_us = hist((nsecs - @w[args->next_pid]) / 1000); delete(@w[args->next_pid]); }'`.
        (2) Prove a `FundsLedger` lock convoy at the 3,400/sec settlement burst:
        `bpftrace -e 'tracepoint:syscalls:sys_enter_futex /pid == $1/ { @s[tid] = nsecs; } tracepoint:syscalls:sys_exit_futex /@s[tid]/ { @us[ustack] = hist((nsecs - @s[tid]) / 1000); delete(@s[tid]); }'`.
        (3) Attribute `fsync` latency to a file on a saturated volume:
        `bpftrace -e 'kprobe:vfs_fsync_range { @s[tid] = nsecs; @f[tid] = str(((struct file *)arg0)->f_path.dentry->d_name.name); } kretprobe:vfs_fsync_range /@s[tid]/ { @ms[@f[tid]] = hist((nsecs - @s[tid]) / 1000000); delete(@s[tid]); delete(@f[tid]); }'`.
        Each must be validated against the target kernel's BTF before use. `[BUILD]` `[DIAG]`
        `[RESEARCH]`

*(13 leaves)*

## §3.18 Where the JVM meets the kernel: safepoints and signals, JIT and the iTLB, thread parking, `perf` maps

3.18.1 `[PROVE]` **Safepoints are the JVM's own cooperative preemption**, and they are implemented
       with kernel primitives. A safepoint is a point where every Java thread's stack and registers
       are walkable, so GC, deoptimisation, biased-lock revocation (historically), thread dumps and
       `jcmd` operations can run. JIT-compiled code contains **polls** at method returns and loop
       back-edges; since **JEP 312 (thread-local handshakes)** the poll is a load from a
       **per-thread polling page** whose address sits in the thread's register-cached
       `Thread::_polling_page`. Arming it = `mprotect(page, PROT_NONE)`; the cost of a *disarmed*
       poll is one load with no branch. `[PROVE]` `[API]`
3.18.2 `[PROVE]` **`SIGSEGV` as control flow — the trick that surprises every Linux engineer
       reading `strace` on a JVM for the first time.** When a poll loads from the protected page, the
       CPU raises a page fault; the JVM's handler
       (`JVM_handle_linux_signal` in `hotspot/os_cpu/linux_x86/os_linux_x86.cpp`, installed via
       `os::Linux::signal_handler`) recognises the fault address as the polling page and diverts
       execution to the safepoint blob. **The same mechanism implements implicit null checks**: a
       compiled field access on `null` faults at a low address, and the handler resumes at the
       deoptimisation/`NullPointerException` path — which is why null checks cost *nothing* on the
       fast path. Consequence: **a perfectly healthy JVM generates `SIGSEGV`s continuously**, and
       `SIGSEGV` in a trace is not evidence of a crash. `[PROVE]` `[TRAP]` `[SOURCE]`
3.18.3 `[API]` **Time-to-safepoint is a distinct pause from GC and it is where the kernel leaks
       in.** The VM cannot proceed until the **last** thread reaches a poll; a thread in a long
       counted loop with no poll, or one blocked in a page fault or a `D`-state syscall, extends the
       pause for **every** thread. Levers and instruments: `-Xlog:safepoint` (or
       `-Xlog:safepoint+stats`) showing the `Reaching safepoint` versus `At safepoint` split,
       `-XX:+SafepointTimeout -XX:SafepointTimeoutDelay=<ms>` to *name* the offending thread,
       `-XX:LoopStripMiningIter` for counted-loop polling, and JFR's `SafepointBegin`/
       `ExecuteVMOperation` events. `-XX:+PrintSafepointStatistics` was **removed** — quoting it
       dates you. `[API]` `[VERSION-TRAP]` `[DIAG]`
3.18.4 `[TRAP]` **`-Xrs` breaks this, and `hs_err` tells you which fault was real.** `-Xrs` reduces
       the JVM's signal usage and hands `SIGQUIT`/`SIGTERM`/`SIGINT` back to the default
       disposition, disabling both thread dumps on `kill -3` and shutdown hooks on signal. When a
       fault is *not* a safepoint poll or an implicit null check, the JVM writes
       `hs_err_pid<pid>.log`, whose `siginfo` block (`si_signo`, `si_code`, `si_addr`) plus the
       instruction bytes and register dump are what distinguish a JIT bug from a JNI bug from
       memory corruption. `[TRAP]` `[DIAG]`
3.18.5 `[CALC]` **The code cache and iTLB pressure.** The code cache is an `rwxp` mapping,
       `ReservedCodeCacheSize` **240 MB** by default with `-XX:+SegmentedCodeCache` splitting it
       into non-nmethod / profiled / non-profiled regions. A 2,048-entry STLB covers 8 MiB at 4 KiB
       granularity, so a service with tens of MB of hot compiled code misses the **instruction**
       TLB continuously; backing the code cache with 2 MiB pages
       (`-XX:+UseTransparentHugePages`, or `-XX:+UseLargePages` with `CAP_IPC_LOCK`) covers 4 GiB
       with the same entries. Measure, do not assume:
       `perf stat -e iTLB-load-misses,itlb_misses.walk_completed,instructions -p <pid>` before and
       after. `[CALC]` `[NUM]` `[API]`
3.18.6 `[TRAP]` **`AlwaysPreTouch` × THP is a real interaction, not a theoretical one.**
       Pre-touch writes one byte per page across the whole heap at startup. If THP is `always` (or
       `madvise` with `-XX:+UseTransparentHugePages`), each touch of a 2 MiB-aligned region can
       enter `do_huge_pmd_anonymous_page` and, under `defrag=always`, **direct compaction** — so a
       12 GB `FundsLedger` heap's pre-touch turns from seconds into minutes and `khugepaged` churns
       afterwards. The safe combination is `-XX:+AlwaysPreTouch` +
       `-XX:+UseTransparentHugePages` + host `defrag=madvise` or `defer+madvise`, with
       `-Xms == -Xmx` and a memory *request* sized for the post-pre-touch RSS (§1.12.10).
       `[TRAP]` `[RESEARCH]`
3.18.7 `[TRAP]` **Why your `perf` flame graph is a wall of `[unknown]`.** `perf record -g`
       defaults to a **frame-pointer** walk, and HotSpot omits the frame pointer in JIT-compiled
       code to free `RBP` as a general register — so the unwinder stops at the first Java frame.
       **`-XX:+PreserveFramePointer`** (8u60+) restores it for a few percent of throughput and is
       the standard price of profilability. The alternatives:
       `--call-graph dwarf` (huge perf.data, expensive, needs unwind info the JIT does not emit) or
       `--call-graph lbr` (hardware, limited depth, Intel-only). `[TRAP]` `[API]`
3.18.8 `[BUILD]` **Symbolising JIT frames: `perf-<pid>.map`.** `perf` looks for
       `/tmp/perf-<pid>.map`, a plain text file of `<hex start> <hex size> <symbol>` lines that maps
       code-cache addresses to Java method names. Three ways to produce it:
       `perf-map-agent` (attach-on-demand), `-XX:+UnlockDiagnosticVMOptions
       -XX:+DumpPerfMapAtExit`, or **`jcmd <pid> Compiler.perfmap`** (JDK 17+) to dump it live.
       The container trap: the file is written to the **container's** `/tmp` under the
       **namespace-local** pid, so `perf` on the host looks for `/tmp/perf-<hostpid>.map` and finds
       nothing — you must read it from `/proc/<hostpid>/root/tmp/perf-<nspid>.map` and rename it.
       `[BUILD]` `[TRAP]` `[API]`
3.18.9 `[API]` **`async-profiler` sidesteps all of that**, which is why it is the practical default:
       it combines `perf_event_open` sampling with HotSpot's `AsyncGetCallTrace` to produce mixed
       Java+native stacks **without** frame pointers or a perf map, and falls back to
       `itimer`/`ctimer` when `perf_event_paranoid > 1` or seccomp blocks `perf_event_open`. Modes
       worth knowing: `cpu`, `wall` (the one that finds blocking), `alloc`, `lock`. JFR's
       `ExecutionSample` is the always-on alternative but is **safepoint-biased** — it samples only
       at safepoint-pollable points, so it systematically misses code between polls.
       `[API]` `[TRAP]` `[X-REF 20]`
3.18.10 `[DIAG]` **Thread identity across the boundary.** One Java **platform** thread = one
        `task_struct`; the `nid=0x1a2b` in a thread dump is `gettid()` in hex, so
        `printf '%x\n' <tid>` matches `top -H` to `jstack`. `comm` is truncated to **15**
        characters, so `Thread.setName("FundsLedger-settlement-worker-7")` shows as
        `FundsLedger-set` in `top`. The threads that appear as unexplained CPU are the JVM's own:
        `GC Thread#N`, `G1 Conc#N`, `G1 Service`, `C1/C2 CompilerThread<N>`, `VM Thread`,
        `VM Periodic Task Thread`, `Reference Handl`, `Signal Dispatch`. **Virtual threads have no
        `task_struct` at all** — `top -H` shows only the carrier `ForkJoinPool-1-worker-N`, which is
        why kernel-level thread tooling is blind to them. `[DIAG]` `[PROC]` `[X-REF 04]`
3.18.11 `[CALC]` **Clocks and sleep resolution.** `System.nanoTime()` →
        `clock_gettime(CLOCK_MONOTONIC)` through the **vDSO** at ~20–25 ns *when*
        `current_clocksource` is `tsc` or `kvm-clock`; `System.currentTimeMillis()` →
        `CLOCK_REALTIME` (and therefore subject to NTP steps — never use it to measure a duration).
        `Thread.sleep(1)` and `LockSupport.parkNanos` become `clock_nanosleep`/`futex` with a
        timeout, and the wake is subject to **timer slack** (`prctl(PR_SET_TIMERSLACK)`, default
        **50 µs**) plus run-queue delay — so a 1 ms sleep is reliably 1.1–2 ms and a 100 µs sleep is
        meaningless. This is why polling loops with sub-millisecond sleeps do not do what their
        author intended. `[CALC]` `[PROC]` `[API]`
3.18.12 **GC as a kernel workload.** Heap uncommit is `madvise(MADV_DONTNEED)`/`MADV_FREE`
        (G1 `-XX:+ShrinkHeapInSteps`, `-XX:MinHeapFreeRatio`), each of which is a potential TLB
        shootdown across every vCPU the JVM occupies (§3.4.7); ZGC's coloured pointers use
        **multiple virtual mappings of the same physical memory**, which multiplies VMA count and
        makes `vm.max_map_count` (**65530**) a real ceiling; card tables, remembered sets and mark
        bitmaps are anonymous RSS the container limit must include; and
        `-Xms == -Xmx` with `-XX:-UseAdaptiveSizePolicy` is what makes the kernel's job
        predictable rather than reactive. `[X-REF 06]` `[SYSCTL]`
3.18.13 `[FLOW]` **The complete "is it us or the box" sequence**, in the order that eliminates the
        most possibilities per step: (1) `/proc/pressure/{cpu,memory,io}` — is anything saturated at
        all; (2) `cpu.stat`'s `nr_throttled`/`throttled_usec` — are we being stopped;
        (3) `/proc/<pid>/schedstat` field 2 — are we waiting to run; (4) `ps -o min_flt,maj_flt` and
        `memory.stat`'s `pgmajfault`/`workingset_refault_file` — are we waiting for memory;
        (5) `iostat -x` `await` and `io.pressure` — are we waiting for disk;
        (6) `-Xlog:safepoint` time-to-safepoint and `-Xlog:gc*` pause times — is the JVM stopping
        itself; (7) `async-profiler -e wall` — and only now is it the code. Every step names a file;
        a diagnosis that names no file is a guess. `[FLOW]` `[DIAG]`

*(13 leaves)*

## §3.19 Five incidents traced from JVM symptom to kernel counter

3.19.1 **The discipline for every entry below**, and the shape to reproduce in an interview: state
       the **symptom as the JVM presented it**, the **counter that proved the mechanism**, the
       **kernel mechanism** in one sentence, and the **fix** — plus what you would have alerted on
       to catch it earlier. A root cause with no counter behind it is a hypothesis, and saying so
       out loud is a signal of seniority, not of doubt. `[PROVE]`
3.19.2 `[INCIDENT]` `[FLOW]` **THP compaction stall inside a GC pause — `FundsLedger`.**
       (1) Symptom: G1 young pauses on the 3 × **12 GB** instances jump from 9 ms to **310 ms**,
       intermittently, with no rise in allocation rate, live set or heap occupancy; `-Xlog:gc*`
       attributes the time to "Other" rather than to any GC phase. (2) Counter: `/proc/vmstat`
       shows `compact_stall` rising in lockstep with the pauses, `thp_fault_fallback` climbing, and
       `/proc/pressure/memory` `some avg10=23`; `/sys/kernel/mm/transparent_hugepage/defrag` reads
       **`always`**. (3) Mechanism: a GC thread committing heap regions faults on a 2 MiB-aligned
       range, `do_huge_pmd_anonymous_page` requests an order-9 folio, the allocation fails on a
       fragmented host and enters **direct compaction** — migrating pages *inside the
       stop-the-world pause* (§3.5.8). (4) Fix: host `defrag=madvise` plus
       `-XX:+UseTransparentHugePages -XX:+AlwaysPreTouch -Xms=-Xmx` so the heap is committed once at
       startup and never faults during a pause; pauses returned to 11 ms. (5) Alert on:
       `compact_stall` rate and `thp_fault_fallback` rate, not on GC pause alone. `[INCIDENT]`
       `[FLOW]` `[PROC]`
3.19.3 `[INCIDENT]` `[FLOW]` **cgroup CPU throttling presenting as p99 latency — `ClientRestrictions`.**
       (1) Symptom: the **30 ms** restriction budget breaches on 3–4% of requests across all
       **8** instances; p50 is 4 ms and p99 is 140 ms; node CPU utilisation is **26%**; no GC pause
       exceeds 12 ms and no downstream call is slow. (2) Counter:
       `cpu.stat` shows `nr_throttled` **412** of `nr_periods` **600** with
       `throttled_usec` accumulating ~70 ms per second; `/proc/<pid>/schedstat` field 2 shows a p99
       run-queue wait of **86 ms**; `cpu.max` reads `"200000 100000"`. (3) Mechanism: CFS bandwidth
       control (§3.2.10, §3.15.10) — 14 runnable JVM threads consumed the 200 ms quota in ~17 ms of
       the 100 ms period, and the entire group was dequeued for the remainder. (4) Fix: cap the
       thread count first — `-XX:ActiveProcessorCount=2`, `-XX:ParallelGCThreads=2`,
       `-XX:CICompilerCount=2` — then raise quota to `"400000 100000"`; p99 fell to 9 ms with
       *lower* total CPU consumption. (5) Alert on: `nr_throttled / nr_periods`, which no default
       dashboard shows. `[INCIDENT]` `[FLOW]` `[CALC]`
3.19.4 `[INCIDENT]` `[FLOW]` **Major faults after a page-cache eviction by a log flood —
       `ProfileService`.** (1) Symptom: the eight-owner aggregation call degrades from 60 ms to
       **900 ms** p99 for ~35 minutes at a time, always beginning a few minutes after a deploy of an
       unrelated service on the same node; CPU flat, no GC change, all downstreams healthy.
       (2) Counter: `ps -o maj_flt` on the JVM climbs by ~40,000 during the window and is flat
       outside it; `memory.stat` shows `workingset_refault_file` spiking and `pgmajfault` rising;
       the co-tenant's cgroup shows `file` growing by **26 GB**; `/proc/pressure/io`
       `some avg10=48`. (3) Mechanism: the co-tenant wrote a debug-level log flood, its page cache
       grew, global reclaim evicted `ProfileService`'s **memory-mapped** lookup tables, and every
       subsequent read became a major fault at ~8 ms against EBS (§3.5.6, §3.6.9). (4) Fix:
       `memory.min` on `ProfileService` to protect its cache, `POSIX_FADV_DONTNEED` on the log
       writer, log level restored, and the mapped tables pre-faulted with `MAP_POPULATE`.
       (5) Alert on: per-cgroup `workingset_refault_file`, which is the only signal that
       distinguishes "cache miss" from "cache stolen". `[INCIDENT]` `[FLOW]` `[PROC]`
3.19.5 `[INCIDENT]` `[FLOW]` **`futex` convoy under a contended lock at the 3,400/sec settlement
       burst — `PaymentService`.** (1) Symptom: during settlement bursts, throughput **falls** from
       1,200/sec to 400/sec while CPU drops from 65% to 30%; thread dumps show 180 of 200 request
       threads `WAITING` on the same `ReentrantLock`; the 150 ms stake-reservation budget breaches
       for the duration. (2) Counter: `/proc/<pid>/status` shows `voluntary_ctxt_switches` up 40×;
       `wchan` reads `futex_wait_queue` on most threads;
       `perf lock contention -ab` attributes 78% of wait time to one callsite;
       a `bpftrace` `futex` histogram shows a bimodal distribution with a **1–4 ms** mode.
       (3) Mechanism: a single lock guarding rail-selection state was held across a **remote
       call**; hold time went from 40 µs to ~400 µs under burst, ρ crossed 0.8, and every waiter
       paid a park/unpark round trip — two syscalls plus a context switch plus run-queue delay
       (§3.13.12). Throughput *fell* because the machine was spending its time switching.
       (4) Fix: move the remote call outside the critical section, shard the state by rail, and
       replace the lock with a `ConcurrentHashMap` `compute` on the hot path. (5) Alert on:
       `voluntary_ctxt_switches` rate per thread and off-CPU time, not on CPU utilisation — which
       moved in the *wrong* direction. `[INCIDENT]` `[FLOW]` `[CALC]`
3.19.6 `[INCIDENT]` `[FLOW]` **`D`-state pile-up on an `fsync` behind a saturated EBS volume —
       `ApplicationGateway`.** (1) Symptom: during a traffic peak the gateway (scaled to **40**
       instances) starts returning 504s; the JVM is unresponsive to `jcmd`, `kill -9` on the pod
       does nothing, the container will not terminate within its 30 s grace period, and node load
       average reads **38** with 5% CPU. (2) Counter:
       `ps -eo pid,stat,wchan:30,cmd | awk '$2 ~ /D/'` shows request threads in `io_schedule` and
       `jbd2/nvme1n1-8` also in `D`; `/proc/pressure/io` reads `full avg10=91`;
       `iostat -x 1` shows `w_await` **340 ms** with `aqu-sz` 62 while `%util` sits at a useless
       100%; the gp3 volume is at its **3,000** baseline IOPS. (3) Mechanism: an access log written
       with an `fsync` per request shares the ext4 journal with everything else on the volume
       (§3.8.10); once the device saturated, `fsync` waited on the shared transaction, threads
       entered uninterruptible sleep, and a `D`-state task never returns to userspace so it cannot
       receive `SIGKILL` (§3.14.3). (4) Fix: stop `fsync`-ing the access log at all (it is not a
       durability artifact), move logging to stdout for the node agent to ship, and provision
       io2 with adequate IOPS for the paths that genuinely need `fsync`. (5) Alert on:
       `io.pressure` `full avg10` and count of `D`-state tasks — load average would have told you
       something was wrong and nothing about what. `[INCIDENT]` `[FLOW]` `[DIAG]`
3.19.7 `[PROVE]` **The generalisation across all five.** Four of the five were a **resource whose
       limit nobody computed** (CPU quota against thread count, page cache against co-tenancy, lock
       hold time against arrival rate, device IOPS against `fsync` count); the fifth was a **kernel
       default nobody read** (`defrag=always`). None was a bug in the business logic, none produced
       an exception, and **none was visible in application-level CPU or heap metrics** — which is
       precisely why this part of the guide exists. `[PROVE]`
3.19.8 `[TABLE]` **The reverse index: given a counter, name the mechanism.**
       `cpu.stat: nr_throttled` → CFS bandwidth; `schedstat` field 2 → run-queue contention;
       `pgmajfault` → device-backed fault; `workingset_refault_file` → cache too small or stolen;
       `compact_stall` / `thp_fault_fallback` → THP direct compaction; `allocstall_*` /
       `pgscan_direct` → direct reclaim; `si`/`so` → swap; `nr_dirty` near
       `nr_dirty_threshold` → `balance_dirty_pages` throttling; `wchan: io_schedule` +
       `w_await` → block-device saturation; `wchan: futex_wait_queue` +
       `voluntary_ctxt_switches` → lock contention; `memory.events: oom_kill` → cgroup limit;
       `TcpExtListenOverflows` → accept-queue overflow; `epoll_ctl: ENOSPC` →
       `fs.epoll.max_user_watches`. `[TABLE]` `[DIAG]`
3.19.9 **The five things to alert on so these become boring**, each of which was absent in the
       incident above it: per-cgroup `nr_throttled / nr_periods`; `memory.events`' `oom_kill`
       counter (not just Kubernetes restart counts); the `pgmajfault` **rate** per container;
       `io.pressure` `full avg10`; and a p99 of `/proc/<pid>/schedstat`'s run-queue wait. All five
       are cheap to scrape and none is in a default dashboard. `[PROC]` `[X-REF 20]`
3.19.10 **What to actually say in the interview.** Answer in the four-part shape — symptom,
        counter, mechanism, fix — and when you do not know a constant, **name the file that holds
        it**: "`vm.dirty_ratio`, and I'd read `nr_dirty_threshold` from `/proc/vmstat` rather than
        trust the default". Naming the file beats naming the number, because the file is still
        correct on a kernel you have never seen. `[PROVE]`

*(10 leaves)*

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

## Overall leaf totals

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — BASICS | §1.1–§1.33 (33) | 441 |
| PART 2 — INTERMEDIATE | §2.1–§2.27 (27) | 363 |
| PART 3 — UNDER THE HOOD | §3.1–§3.19 (19) | 234 |
| PART 4 — BUILD IT | §4.1–§4.10 (10) | 72 |
| PART 5 — INTERVIEW AND RETENTION | §5.1–§5.3 (3) | 161 |
| **Total** | **92 sections** | **1,271 leaves** |

Tag census for the write pass's planning: **75 leaves carry `[RESEARCH]`** and must be re-verified
against the cited source before a constant is committed to the page — Parts A, C and D each close
their source block with an explicit re-check list naming the kernel file or doc section that holds
the value, and those lists are the write pass's first task. **83 leaves carry `[VERSION-TRAP]`** and
correspond to the seventeen deltas in the header. **80 leaves carry `[INCIDENT]`** and each must be
written as symptom → diagnosis → root cause → fix, never as an anecdote; §2.27 (24 incidents) and
§3.19 (five traced end to end) are the concentrations. `[SOURCE]` appears 146 times, almost all of it
in PART 3, and each occurrence requires a real excerpt of kernel source or documentation with every
line explained. `[BUILD]` covers §4.1–§4.10. `[TRAP]` appears 312 times, `[PROVE]` 271 and `[DIAG]`
239 — the last of these is the discipline that keeps this file from becoming prose: 239 leaves must
show real command output and read it line by line.

The diagram manifest specifies **28 diagrams** (`D-01`–`D-28`), each with the section that embeds it.

## Sources consulted

Primary sources first, grouped by the part that fetched them. **The session's WebSearch budget
was exhausted before this pass began**, so discovery was performed by fetching known-canonical
primary sources directly — `docs.kernel.org`, `man7.org`, `raw.githubusercontent.com/torvalds/linux`
at tag `v6.12`, `openjdk.org/jeps`, Oracle's JDK 21 tool documentation and AWS documentation — rather
than through search. That is a real limitation and it is recorded here honestly: no interview-question
aggregators, no expert blog posts and no LWN discovery were consulted, so the "curriculum",
"interview surface" and "adversarial" research angles were covered from the existing guide, the
sibling syllabi and the primary docs alone. The write pass should re-run those three angles if search
budget is available. One fetch shape is known not to work: **`elixir.bootlin.com` does not render for
`WebFetch`** — use `raw.githubusercontent.com/torvalds/linux/<tag>/<path>` for kernel source.

### PART A

- **`https://www.kernel.org/doc/html/v6.12/admin-guide/sysctl/vm.html`** — established the
  documented defaults and ranges used throughout §1.13–§1.15: `swappiness` **default 60, range
  0–200** with the verbatim "rough relative IO cost of swapping and filesystem paging... between 0
  and 200. At 100, the VM assumes equal IO cost" text; `overcommit_memory` values 0/1/2 with the
  verbatim mode descriptions quoted in 1.14.7; `vfs_cache_pressure` **100**; `page-cluster` **3**
  (8 pages); `watermark_scale_factor` **10** (0.1%); `panic_on_oom` **0**;
  `oom_kill_allocating_task` **0**; `admin_reserve_kbytes` **min(3% of free pages, 8 MiB)**;
  `user_reserve_kbytes` **min(3% of current process size, 128 MiB)**; `max_map_count` **65530**;
  `zone_reclaim_mode` disabled. It also confirmed that `dirty_ratio`, `dirty_background_ratio`,
  `dirty_expire_centisecs`, `dirty_writeback_centisecs` and `min_free_kbytes` have **no defaults
  stated in the document** — hence the `[RESEARCH]` marker on 1.13.5, where the write pass must
  re-verify 20 / 10 / 3000 / 500 against the running kernel rather than the doc.
- **`https://docs.kernel.org/admin-guide/mm/multigen_lru.html`** — established the MGLRU surface
  used in delta 3 and 1.15.4: the sysfs path `/sys/kernel/mm/lru_gen/enabled`, the bit values
  `0x0001` (main switch), `0x0002` (leaf accessed-bit clearing), `0x0004` (non-leaf), the config
  gates `CONFIG_LRU_GEN` / `CONFIG_LRU_GEN_ENABLED`, the `/sys/kernel/debug/lru_gen` histogram with
  `min_gen_nr` coldest and `max_gen_nr` hottest, `min_ttl_ms` defaulting to **0 = disabled** with
  the "N=1000 usually eliminates intolerable janks due to thrashing" guidance, and the verbatim
  statement that `max_gen_nr` and `max_gen_nr-1` "are not fully aged (equivalent to the active
  list) and therefore cannot be evicted". The page does **not** state the introducing kernel
  version, so the "6.1+" claim in delta 3 stays `[RESEARCH]`.
- **`https://docs.kernel.org/accounting/psi.html`** — established the PSI surface used in delta 4,
  §1.1.5, §1.6.7–1.6.8 and §1.6.12: the paths `/proc/pressure/cpu`, `/proc/pressure/memory`,
  `/proc/pressure/io`; the two-line `some` / `full` format with `avg10`, `avg60`, `avg300` and
  `total`; the sample line `some avg10=0.00 avg60=0.00 avg300=0.00 total=0`; `some` as "the share
  of time in which at least some tasks are stalled on a given resource" and `full` as "the share of
  time in which all non-idle tasks are stalled... simultaneously"; `total` in **microseconds**;
  CPU `full` reported as zero at system level since **5.13**; and the cgroup v2 equivalents
  `cpu.pressure`, `memory.pressure`, `io.pressure`. The doc does not state the introducing version,
  so the "4.20+" claim stays `[RESEARCH]`.
- **`https://docs.kernel.org/admin-guide/cgroup-v2.html`** — established every cgroup v2 interface
  file and default used in delta 2, §1.7.8–1.7.10, §1.5.13 and §1.15.13: `cpu.max` default
  **`"max 100000"`**; `cpu.weight` default **`"100"`**, range **[1, 10000]**; `cpu.stat` fields
  `usage_usec`, `user_usec`, `system_usec`, `nr_periods`, `nr_throttled`, `throttled_usec`,
  `nr_bursts`, `burst_usec`; `memory.max` / `memory.high` / `memory.swap.max` default **`"max"`**;
  `memory.low` / `memory.min` default **`"0"`**; `memory.events` entries `low`, `high`, `max`,
  `oom`, `oom_kill`; `io.max` keys `rbps`/`wbps`/`riops`/`wiops`; `io.weight` default
  **`"default 100"`**; `pids.max` default **`"max"`**; `cgroup.controllers` read-only and
  `cgroup.subtree_control` starting empty; and the verbatim no-internal-process constraint
  ("Non-root cgroups can distribute domain resources to their children only when they don't have
  any processes of their own").
- **`https://docs.kernel.org/admin-guide/sysctl/kernel.html`** — established
  `kernel.perf_event_paranoid` **default 2** and the verbatim value table quoted in delta 10
  (`-1` allow almost all; `>=0` disallow ftrace function tracepoints and raw tracepoints without
  `CAP_PERFMON`; `>=1` disallow CPU event access; `>=2` disallow kernel profiling), plus
  `kptr_restrict` default **0**, `core_pattern` default **`core`**, and that `threads-max` is
  derived at boot from ~1/8 of RAM pages with no fixed default (used in §1.5.13). It confirmed the
  document does **not** state defaults for `sched_rt_runtime_us`, `sched_rt_period_us`,
  `sched_cfs_bandwidth_slice_us` or `pid_max` — so the 950000 / 1000000 / 100 ms / 32768 figures in
  §1.4.12 and §1.8.3–1.8.4 carry `[RESEARCH]` and must be re-verified against
  `Documentation/scheduler/sched-rt-group.rst` and the running `/proc/sys` tree at write time.
- **`https://man7.org/linux/man-pages/man2/clone.2.html`** — established the exact `clone()` glibc
  wrapper signature and the `clone3()` / `struct clone_args` field list quoted in §1.5.2, and every
  flag semantic in §1.5.3–§1.5.5: `CLONE_VM`, `CLONE_FS`, `CLONE_FILES`, `CLONE_SIGHAND`,
  `CLONE_THREAD`, `CLONE_SYSVSEM`, `CLONE_SETTLS`, `CLONE_PARENT_SETTID`,
  `CLONE_CHILD_CLEARTID` (clear the TID and `FUTEX_WAKE` on exit — the `pthread_join` mechanism),
  `CLONE_NEWNS`/`NEWPID`/`NEWNET`/`NEWUTS`/`NEWIPC`/`NEWUSER`/`NEWCGROUP`, `CLONE_PIDFD`,
  `CLONE_VFORK`, `CLONE_IO`. Two gaps are marked `[RESEARCH]` in the leaves: the page as fetched
  did **not** document `CLONE_NEWTIME`, and it does **not** state which flag set NPTL/glibc
  `pthread_create` passes — so §1.5.5's flag list must be re-verified against glibc's
  `nptl/pthread_create.c` at write time.

### PART B

- `https://www.kernel.org/doc/Documentation/block/queue-sysfs.rst` — fetched. Established the
  `/sys/block/<dev>/queue/` knob surface used in §1.20.4 and confirmed the documented default
  `nomerges = 0` ("By default (0) all merges are enabled"). The document does **not** state
  defaults for `read_ahead_kb`, `nr_requests`, `rotational` or `rq_affinity`, and does not
  enumerate scheduler names — the leaves carrying those figures (§1.20.3, §1.20.4) are marked
  `[RESEARCH]` for re-verification against the running kernel (`cat` the files on an Amazon Linux
  2023 / 6.12 box) at write time.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/topics/11-operating-systems-linux.md` —
  the superseded 616-line guide. Every `**Trap:**` and atomic-checklist line in the §1.17–§1.32
  range has been folded into a leaf: `free`/`available` (§1.30.7), `df`/`du` + `lsof +L1`
  (§1.19.7–8), inode exhaustion (§1.19.5), `iostat` fields and burst credits (§1.20.5–6, §1.20.14),
  the triage order (§1.30.1), the log pipelines (§1.31.5–8), cron's four failures (§1.26.11),
  the kill workflow and `kill -3` (§1.28.6–12), `tail -F` (§1.31.1), PID 1 / shell-form `CMD`
  (§1.26.10, §1.26.13), and `D`-state (§1.20.13). SSH/`scp`/`rsync` (guide §10) is deliberately
  reduced to a single `[X-REF 17]` pointer at §1.26.12 per the brief.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/syllabus/10-networking.md`
  (lines 140–330, 1243–1330) — format, numbering, hanging-indent and tag-usage benchmark; §1.29
  (diagnostic toolkit) and §1.30 (latency budgets) set the register for §1.30 and §1.31 here, and
  its `[X-REF nn]` convention is reused.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/scenario/scenario.md` — every example,
  service, number and budget: §4 service catalog; §5.1 architectural rules; §9 restrictions;
  A.1 (55k concurrent sessions), A.2 (1,200/sec reservations, 3,400/sec settlement burst,
  95k card deposits/day at 40/sec), A.3 (19.8M entries/day, 230/sec sustained, 13,600/sec peak,
  180-byte rows, 1.3 TB/year), A.4 (PSP 240 ms p50 / 11 s p99, "elevated declines before outage",
  identity vendor 900 ms p50 / 38 s p99, banking payout 45 s p99), A.5 (2.6M ApplicationHistory
  records/day at ~400 bytes, 24k uploads/day → 68 GB/day, 500k month-end statement records),
  A.6 (12 GB `FundsLedger` heap, 2–6 MB document buffers, reservation lifetime seconds-to-hours),
  A.7 (30 ms restriction, 150 ms reservation, 500 ms self-exclusion budgets).

**Leaves marked `[RESEARCH]` for the write pass to re-verify against a live 6.12 box or primary
doc**: §1.17.6 (`vm.vfs_cache_pressure`), §1.17.11 (`fs.inotify.max_user_watches` memory-derived
default), §1.18.5 (`errseq_t` fsync error reporting), §1.19.5 (`mke2fs.conf` inode ratio 16384),
§1.19.10 (EBS 16 KiB I/O metering), §1.20.3–4 (scheduler defaults, `read_ahead_kb`, `nr_requests`),
§1.20.9 (gp3/gp2/io2 figures), §1.21.6 and §1.21.10 (io_uring posture, JEP 491),
§1.25.11 (OCI default capability set), §1.27.6 and §1.27.9 (EC2 clocksource, AWS leap smearing),
§1.29.8 (PSI file format), §1.32.11 (`perf c2c` HITM attribution).

### PART C

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

### PART D

| URL | What it established |
|---|---|
| `https://raw.githubusercontent.com/torvalds/linux/v6.12/mm/oom_kill.c` | Verbatim `oom_badness()` body and its comment block, `OOM_SCORE_ADJ_MIN`/`MMF_OOM_SKIP`/`in_vfork` exclusions, the `RSS + MM_SWAPENTS + mm_pgtables_bytes/PAGE_SIZE` formula, the `adj *= totalpages / 1000` scaling, the kill-line format string, and the names `select_bad_process`, `oom_evaluate_task`, `dump_tasks`, `oom_kill_process`, `out_of_memory` (§3.7.2, §3.7.3, §3.7.5, §3.7.9) |
| `https://docs.kernel.org/admin-guide/cgroup-v2.html` | The no-internal-process constraint verbatim, the top-down enablement rule, `cgroup.controllers` vs `cgroup.subtree_control`, `memory.min/low/high/max` semantics and defaults, `memory.events` fields, `memory.stat` fields, `memory.oom.group`, `cpu.max` (`"max 100000"`), `cpu.weight` (100, [1,10000]), `cpu.stat` fields, `io.stat`/`io.max` keys, `pids.max` (§3.15.2, §3.15.3, §3.15.7, §3.15.8, §3.15.9, §3.15.11, §3.7.8, §3.7.10) |
| `https://docs.kernel.org/accounting/psi.html` | The verbatim `some`/`full` definitions, the `avg10/avg60/avg300/total` line format, `total=` in microseconds, the per-cgroup `cpu.pressure`/`memory.pressure`/`io.pressure` files, the trigger syntax `<some\|full> <us> <us>`, and "CPU full has been reported since 5.13" (§3.6.12) |
| `https://man7.org/linux/man-pages/man2/futex.2.html` | The `syscall(SYS_futex, uaddr, op, ...)` form and absence of a glibc wrapper, the full op list including `FUTEX_PRIVATE_FLAG`, `FUTEX_CLOCK_REALTIME`, `FUTEX_CMP_REQUEUE`, `FUTEX_WAKE_OP` and the PI operations, and the verbatim atomicity guarantee for the load/compare/block sequence (§3.13.2, §3.13.3, §3.13.4) |
| `https://man7.org/linux/man-pages/man2/io_uring_setup.2.html` | `io_uring_setup(u32 entries, struct io_uring_params *p)`, the `io_uring_params` field list, the `IORING_SETUP_*` flag set including `SINGLE_ISSUER`/`DEFER_TASKRUN`/`COOP_TASKRUN`, and the `IORING_OFF_SQ_RING`/`CQ_RING`/`SQES` mmap offsets (§3.12.1, §3.12.2, §3.12.10) |
| `https://docs.kernel.org/bpf/verifier.html` | The two-phase verification ("DAG check to disallow loops", then path simulation), the `bpf_reg_state` type names with their verbatim descriptions, the state-pruning rule quoted verbatim, and `kernel/bpf/verifier.c` as the location (§3.17.4, §3.17.5) |
| `https://docs.kernel.org/block/blk-mq.html` | The software staging queue (`blk_mq_ctx`, per-CPU/per-node) vs hardware dispatch queue (`blk_mq_hw_ctx`) split with quoted definitions, `blk_mq_tag_set` as a shareable tag set, `struct request` built from a bio, plugging/merging with the "sector 3-6, 6-7, 7-9" example, and "Every request is identified by an integer, ranging from 0 to the dispatch queue size" (§3.9.2, §3.9.3, §3.9.5, §3.9.6) |
| `https://docs.kernel.org/admin-guide/mm/transhuge.html` | The `transparent_hugepage/enabled` values (`always`/`madvise`/`never`) and `defrag` values (`always`/`defer`/`defer+madvise`/`madvise`/`never`), the verbatim behaviour of `defer` (wake `kswapd`/`kcompactd`, THP "available in the near future") vs `madvise` (direct reclaim for `MADV_HUGEPAGE` regions only), `hpage_pmd_size`, the `khugepaged/*` tunables, and `AnonHugePages`/`ShmemHugePages` (§3.5.8, §3.18.6, §3.19.2) |
| `https://lwn.net/Articles/925371/` | EEVDF's lag ("A process with a positive lag value has not received its fair share and should be scheduled sooner"), eligible time, virtual deadline = eligible time + allocated slice, and latency-nice driving slice length (§3.2.5) |
| `https://docs.kernel.org/scheduler/sched-eevdf.html` | EEVDF's own statement of lag, eligibility (`lag ≥ 0`), virtual-deadline selection, per-task slice requests via `sched_setattr()`, and the 6.6 merge (§3.2.5, §3.2.6) |
| `https://elixir.bootlin.com/linux/v6.12/source/fs/eventpoll.c` | `struct eventpoll` field names (`rbr`, `rdllist`, `ovflist`, `wq`, `poll_wait`, `lock`, `mtx`), `struct epitem`, and the function names `ep_poll_callback`, `ep_poll`, `ep_send_events`, `ep_item_poll` plus `EPOLLEXCLUSIVE` handling. **Note:** the fetcher returned a summary rather than raw source, so the verbatim excerpts and exact field ordering in §3.11.1–§3.11.6 are marked for re-verification against the v6.12 file during the write pass. `[RESEARCH]` |

**Unverified from reachable documentation — the write pass must re-check each against the named
file before publishing a number.** Part A found the same gap and it persists here: writeback
defaults (`vm.dirty_background_ratio`, `vm.dirty_ratio`, `vm.dirty_expire_centisecs`,
`vm.dirty_writeback_centisecs`) against `Documentation/admin-guide/sysctl/vm.rst` (§3.8.7);
`sched_rt_runtime_us`/`sched_rt_period_us` against `Documentation/scheduler/sched-rt-group.rst`
(§3.2.8); `base_slice_ns` = 750,000 and `cfs_bandwidth_slice_us` = 5000 against
`kernel/sched/fair.c` and `Documentation/scheduler/sched-bwc.rst` (§3.2.6, §3.2.10);
`pid_max` (§3.1 context); MGLRU's introducing version and `lru_gen` bit meanings against
`Documentation/admin-guide/mm/multigen_lru.rst` (§3.6.8); PSI's introducing version (§3.6.12);
`tlb_single_page_flush_ceiling` = 33 and `TLB_NR_DYN_ASIDS` = 6 against `arch/x86/mm/tlb.c`
(§3.4.5, §3.4.8); `fault_around_bytes` = 65536 against `mm/memory.c` (§3.5.7);
`MEMCG_CHARGE_BATCH` = 64 against `mm/memcontrol.c` (§3.15.6);
`BPF_COMPLEXITY_LIMIT_INSNS` = 1,000,000 against `kernel/bpf/verifier.c` (§3.17.5);
`EPOLL_MAX_NESTS` = 4 and `fs.epoll.max_user_watches` derivation against `fs/eventpoll.c`
(§3.11.10, §3.11.12); JDK lightweight-locking mode names and `-XX:LockingMode` values against the
JDK 21/24 release notes (§3.13.11); Kubernetes' `oom_score_adj` values per QoS class against the
kubelet source (§3.7.4).

### PART E

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

Two of its sections sit outside the obvious kernel-mechanism frame and were at risk of being dropped
silently: current §9 (cron, `flock`, distributed cron) and current §10 (SSH, keys, `ProxyJump`,
`rsync`, SSM). Their five checklist lines are in the 46 that must survive, so both are explicitly
rehomed in this syllabus rather than deferred — **cron into §1.26.11**, where it belongs as a
daemon-launch mechanism alongside systemd timers and the leader-election answer to distributed cron,
and **SSH into its own §1.33**, on the grounds that SSH is the transport for every diagnostic in
§1.30 and its permission, host-key and agent-forwarding failures are operating-system failures. The
last two rows of this table record that placement.

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
| §1.26.11 cron and systemd timers (rehomed from current §9) | §9 in full — the five fields, the four cron failures, `flock`, distributed cron, idempotency-beats-locking — and 2 checklist lines | ✅ systemd timers (`OnCalendar=`, `Persistent=true`, `RandomizedDelaySec=`) as the construction-level fix for cron's environment and logging problems | ✅ all four cron traps and the idempotency argument are correct and must be preserved verbatim inside §1.26.11 |
| §1.33 SSH, tunnels and file transfer (rehomed from current §10) | §10 in full — key mechanism, strict permissions, `~/.ssh/config`, `ProxyJump`, `-L`, agent forwarding's risk, `known_hosts`, `scp`/`rsync`, SSM — and 3 checklist lines, all correct | ✅ `IdentitiesOnly yes` and the `MaxAuthTries` failure, the `ssh-rsa`/SHA-1 disablement, `ControlMaster`, `-R`/`-D`, the `rsync` trailing-slash rule, `scp`-over-SFTP, `kubectl exec` as the container equivalent | ✅ the SSM recommendation and the `known_hosts` warning are current and must be preserved verbatim |

|
