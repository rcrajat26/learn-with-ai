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

**PART 3 total: 19 sections, 234 leaves.**

## Sources consulted — PART D

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
