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

## Sources consulted — PART A

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
