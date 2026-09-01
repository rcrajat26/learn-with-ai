# 05 Multithreading and Concurrency — Runtime observability: dumps and JFR — INTERNALS (§3.13, leaves 3.13.1–3.13.7)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Cost, ThreadFlock and scoped values](../virtual-threads/03c-internals-cost-flock-and-scoped-values.md) · Next: [Profiling and metrics](03-internals-profiling-and-metrics.md)

This file is the first half of Part 3's observability pass: given a running `PaymentRun`
settlement pool that has stopped making progress, what do you run first, what does the output mean
line by line, and how do you tell contention, saturation, idleness and deadlock apart before
reading a single stack in detail. The running incident is the settlement pool wedged on
`FundsLedger`'s monitor during a `PaymentRun` batch, with the card PSP sitting at its documented
240 ms p50 / 11 s p99. The second half — profiling, metrics, a hand-rolled `ThreadMXBean` reporter,
and the hard limit of all of this (a data race) — is the next file.

### Reading a `jstack` dump line by line

**Mental model.** A thread dump is a photograph, not a video: every thread's exact stack and state
at one safepointed instant, frozen simultaneously so the relationships between threads — who is
waiting on what another thread holds — are consistent within the same snapshot. Read top to bottom,
each thread's block answers four questions in order: who is this, what state is it in, where is it
in the code, and what lock-related fact explains why.

**Why it exists.** Before dumps, "the service is stuck" diagnosis meant restarting it and hoping
the failure reproduced under a debugger. `jstack` (and its `jcmd` successors) let an operator ask
the live JVM to describe itself without stopping it for more than the safepoint pause.

**When to reach for it, and when not.** Reach for it first for any hang, apparent deadlock, or
"CPU is pegged but throughput dropped" symptom on platform threads. It is the wrong tool once
virtual threads are unmounted and parked — covered in the prior file — and the wrong tool for
finding a data race, which leaves no trace in any stack (next file, §3.13.12).

**How it works — the annotated dump.** This is one real excerpt from the settlement pool during
the `FundsLedger` incident, twelve worker threads deep into a `PaymentRun` batch:

```
"settlement-ingest-7" #23 daemon prio=5 os_prio=0 cpu=1889.34ms elapsed=612.10s tid=0x00007f2b3401a800 nid=0x4e12 waiting for monitor entry [0x00007f2ac37fe000]
   java.lang.Thread.State: BLOCKED (on object monitor)
	at com.quizstakes.ledger.FundsLedger.reserveStake(FundsLedger.java:118)
	- waiting to lock <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)
	at com.quizstakes.settlement.SettlementWorker.applyEntry(SettlementWorker.java:64)
	at com.quizstakes.settlement.SettlementWorker.run(SettlementWorker.java:41)
	at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1144)
	at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:642)
	at java.base/java.lang.Thread.run(Thread.java:1583)

   Locked ownable synchronizers:
	- None
```

and the one thread that is holding the monitor the other eleven are queued for:

```
"settlement-ingest-3" #19 daemon prio=5 os_prio=0 cpu=3021.77ms elapsed=612.10s tid=0x00007f2b34012000 nid=0x4e0e runnable [0x00007f2ac3bfe000]
   java.lang.Thread.State: RUNNABLE
	at com.quizstakes.psp.CardPspClient.authorise(CardPspClient.java:87)
	at com.quizstakes.ledger.FundsLedger.reserveStake(FundsLedger.java:121)
	- locked <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)
	at com.quizstakes.settlement.SettlementWorker.applyEntry(SettlementWorker.java:64)
	at com.quizstakes.settlement.SettlementWorker.run(SettlementWorker.java:41)
	at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1144)
	at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:642)
	at java.base/java.lang.Thread.run(Thread.java:1583)

   Locked ownable synchronizers:
	- None
```

**D-195** — A `jstack` dump, annotated line by line

| Line | What it means | What it rules out |
|---|---|---|
| `"settlement-ingest-7" #23 daemon prio=5 os_prio=0 cpu=1889.34ms elapsed=612.10s tid=0x… nid=0x4e12 …` | `name` is application-assigned (`ThreadFactory`); `#23` is the JVM's internal sequence number; `daemon` means the JVM can exit with this thread still running; `prio`/`os_prio` are Java and OS scheduling priority; `cpu`/`elapsed` are cumulative CPU time and wall-clock time since thread start; `tid` is the JVM's internal thread pointer; `nid` is the OS thread id in hex (§3.13.5) | Rules out "this is a virtual thread" — every field here, especially a stable `nid`, only exists for a platform (carrier) thread |
| `java.lang.Thread.State: BLOCKED (on object monitor)` | This thread called into a `synchronized` block/method and another thread already holds that monitor | Rules out `WAITING`/`TIMED_WAITING` causes — no `wait()`, no `park()`, no I/O; it is purely queued for monitor entry |
| `at com.quizstakes.ledger.FundsLedger.reserveStake(FundsLedger.java:118)` | The exact frame where the thread is stopped — line 118 is the `synchronized` method entry point | Rules out the thread being stuck deeper inside the critical section; it never got in |
| `- waiting to lock <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)` | This thread wants the monitor at heap address `0x…4a10`, which belongs to one specific `FundsLedger` instance | Rules out lock-splitting having happened — if there were sharded ledger locks, different workers would show different addresses; here they all show the same one |
| `"settlement-ingest-3" … runnable …` | The address-matching thread that is *not* `BLOCKED` — it is the monitor's current owner, actively running | Rules out the owner itself being stuck on I/O in a way that would show `TIMED_WAITING`; `RUNNABLE` plus a PSP call frame means it is spending real CPU/network time inside the critical section |
| `- locked <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)` | Confirms ownership: this is the thread the other eleven are queued behind | Rules out a *different* thread being the true holder — the address must match exactly, not just the class name |
| `Locked ownable synchronizers: - None` | This thread holds no AQS-based locks (`ReentrantLock`, etc.) — only the intrinsic monitor above, which this block does not enumerate | Rules out a *second*, AQS-based lock also being held by the same thread, which would compound the contention |
| `Found one Java-level deadlock:` (not present here) | Appears only when the wait-for graph the detector builds (§3.13.3) contains a cycle | Its absence here rules out deadlock specifically — this is one-directional contention on a single monitor, not a cycle. Contention and deadlock look similar in "many threads BLOCKED" but are structurally different; only the graph decides which one this is |

**Insight:** the smoking gun is not any one thread's `BLOCKED` state — it is that **eleven other
`settlement-ingest-N` threads all show `waiting to lock <0x00000006ff214a10>`, the identical
address**, while exactly one shows `locked <0x00000006ff214a10>` and is spending its `RUNNABLE`
time inside `CardPspClient.authorise`. A single dump line never proves contention; the same address
repeated across many stacks does.

**The gotcha.** `elapsed=612.10s` on a `BLOCKED` thread does not mean it has been blocked for 612
seconds — it is time since the *thread* started, which for a long-lived pool worker includes all
the time it spent successfully doing work before this particular contention episode began. Only
correlating dumps taken minutes apart, or JFR's actual event duration (§3.13.6), gives the true
block duration.

> **Definition:** a thread dump is a synchronized, safepoint-consistent snapshot of every platform
> thread's state and stack, in which a `- waiting to lock <addr>` line on one thread and a matching
> `- locked <addr>` on another is the JVM handing you the wait-for edge directly, with no inference
> required.

### The three dump signatures

**Mental model.** Most pool pathologies collapse into one of three recognisable *shapes* a dump
takes, before you read a single stack frame in detail — the shape alone narrows the diagnosis.

**Why it exists as a distinct skill.** Under incident pressure there is no time to read all forty
stacks carefully. Recognising the shape from a `grep -c` and a glance at the state distribution
gets you to the right next command in seconds instead of minutes.

**When each applies.** They are mutually exclusive at any one instant — a pool is either starved
for the lock, starved for work, or genuinely saturated doing useful work; distinguishing them is
exactly what determines whether the fix is "reduce critical-section time," "check upstream traffic
died," or "the pool is correctly sized and simply overloaded."

**How to tell them apart, `[PROVE]`.**

*Monitor contention* — the signature just walked through: `grep -c 'BLOCKED (on object monitor)'`
returns eleven, all `waiting to lock` the same address, one thread `RUNNABLE` holding it.

*Pool saturation* — every worker is `RUNNABLE`, inside genuine application code (`CardPspClient`,
`FundsLedger`), no two threads share a `waiting to lock` address, and `jcmd <pid>
Thread.print` shows the executor's queue depth climbing across two dumps taken a minute apart.
Distinguish from contention: no shared lock address anywhere.

*Pool idleness* — every worker shows:

```
"settlement-ingest-12" #28 daemon prio=5 os_prio=0 cpu=42.11ms elapsed=612.10s tid=0x00007f2b34024000 nid=0x4e17 waiting on condition [0x00007f2ac2ffe000]
   java.lang.Thread.State: TIMED_WAITING (parking)
	at jdk.internal.misc.Unsafe.park(java.base@21.0.4/Native Method)
	- parking to wait for  <0x00000006ff300ab8> (a java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject)
	at java.util.concurrent.locks.LockSupport.parkNanos(LockSupport.java:269)
	at java.util.concurrent.LinkedBlockingQueue.poll(LinkedBlockingQueue.java:460)
	at java.util.concurrent.ThreadPoolExecutor.getTask(ThreadPoolExecutor.java:1062)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1146)
	at java.base/java.lang.Thread.run(Thread.java:1583)
```

— forty of these `getTask`-parked workers, in the settlement pool sized for the 3,400/sec burst,
is not a problem in itself; it is the expected idle shape when upstream `PaymentRun` submission has
paused between windows. It only becomes a symptom when paired with a growing upstream queue
elsewhere that *should* be feeding this pool and is not.

*Deadlock* — covered next, §3.13.3.

*Virtual-thread pinning* — flagged here for completeness though it is a platform-thread-pool
mismatch specifically: on a virtual-thread-per-task executor a `jstack` dump shows a small, fixed
number of *carrier* threads `RUNNABLE`, each one currently mounting a virtual thread stuck inside a
held `synchronized` block (prior file, §3.12). The give-away is the carrier count matching
`Runtime.availableProcessors()` regardless of how many virtual threads were submitted.

**D-196** — The three dump signatures

| Signature | Threads and state | Give-away stack frame | CPU usage | Throughput | Next command | Fix |
|---|---|---|---|---|---|---|
| Monitor contention | N−1 `BLOCKED (on object monitor)`, 1 `RUNNABLE`, all sharing one `waiting to lock`/`locked` address | `- waiting to lock <same addr>` repeated | Low-to-moderate; only the holder does real work | Serialised to one thread's throughput | `jcmd <pid> Thread.print -l` across two dumps to confirm the same holder persists | Shrink the critical section (e.g. move the PSP call outside `reserveStake`'s monitor), or shard the lock |
| Pool saturation | All `RUNNABLE`, inside application code, no shared lock address | Deep applicaton frames, e.g. `CardPspClient.authorise` | High, evenly spread | Flat at pool capacity, queue growing | `jcmd <pid> VM.native_memory summary` or Micrometer `executor.queued` (next file) trend | Add capacity, shed load, or fix the slow downstream call |
| Pool idleness | All `TIMED_WAITING (parking)` in `getTask` | `ThreadPoolExecutor.getTask` → `LinkedBlockingQueue.poll` | Near zero | Zero, expected if no work is due | Check the upstream producer/queue, not this pool | None needed if idleness is expected; investigate the feeder if not |
| Deadlock | A small cycle `BLOCKED`, rest often unaffected | `Found one Java-level deadlock:` block | Low for the cycle, unaffected elsewhere | Zero for the cycle's participants | Read the deadlock section directly (§3.13.3) | Fix lock ordering, or use `tryLock` with a timeout |
| Virtual-thread pinning | Few `RUNNABLE` carriers, count = `availableProcessors()`, regardless of submitted VT count | Carrier stack shows `VirtualThread.run` mounting a thread inside a held monitor | High relative to carrier count, but throughput caps at carrier count | Caps at carrier count instead of scaling with submitted tasks | `jcmd <pid> Thread.dump_to_file -format=json`, or `jdk.VirtualThreadPinned` (§3.13.6) | Replace the held `synchronized` with `ReentrantLock` (Java 21; see prior file's version trap) |

**Pitfall:** treating "many threads `BLOCKED`" as automatically meaning deadlock. Contention and
deadlock produce the same *count* of blocked threads; only the wait-for graph — a cycle versus a
line — tells them apart, and pool saturation has no `BLOCKED` threads at all despite also meaning
"the pool is not keeping up."

> **Definition:** the three dump signatures are recognisable purely from the *shape* of the state
> distribution and whether stacks share a lock address — contention (shared address, one owner),
> saturation (no shared address, all busy), idleness (all parked in `getTask`) — before any single
> stack needs to be read in detail.

### The deadlock section of a dump

**Mental model.** `jstack` does not merely print stacks; for the deadlock case specifically it runs
its own analysis pass and hands you the conclusion pre-computed.

**Why it exists.** A human reading forty stacks for a wait-for cycle by hand is slow and
error-prone, especially once the cycle spans more than two threads. The JVM already has every
`- locked`/`- waiting to lock` fact it needs from the same walk that produced the stacks; running
cycle detection over that graph while it has the data is nearly free.

**When it fires, and its limit.** It fires only for monitor- and `ReentrantLock`-based deadlocks it
can see in the same dump — a cycle spanning an external resource (a database row lock on the other
side of a JDBC call) is invisible to it, because that lock is not JVM-managed.

**How it works.** `[PROVE]` The detector builds a directed graph: one node per thread holding or
waiting on a lock, one edge per `- waiting to lock <addr>` pointing from the waiting thread to
whichever thread's `- locked <addr>` matches that address. It then runs cycle detection over that
graph. A cycle exists if and only if the JVM's own dump output for those threads is:

```
Found one Java-level deadlock:
=============================
"settlement-ingest-3":
  waiting to lock monitor 0x00007f2b58003818 (object 0x00000006ff214a10, a com.quizstakes.ledger.FundsLedger),
  which is held by "settlement-ingest-9"
"settlement-ingest-9":
  waiting to lock monitor 0x00007f2b58004120 (object 0x00000006ff21e2c8, a com.quizstakes.ledger.ClientRestrictions),
  which is held by "settlement-ingest-3"

Java stack information for the threads listed above:
===================================================
"settlement-ingest-3":
	at com.quizstakes.ledger.ClientRestrictions.applyHold(ClientRestrictions.java:52)
	- waiting to lock <0x00000006ff21e2c8> (a com.quizstakes.ledger.ClientRestrictions)
	at com.quizstakes.ledger.FundsLedger.reserveStake(FundsLedger.java:130)
	- locked <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)
"settlement-ingest-9":
	at com.quizstakes.ledger.FundsLedger.reserveStake(FundsLedger.java:118)
	- waiting to lock <0x00000006ff214a10> (a com.quizstakes.ledger.FundsLedger)
	at com.quizstakes.ledger.ClientRestrictions.release(ClientRestrictions.java:38)
	- locked <0x00000006ff21e2c8> (a com.quizstakes.ledger.ClientRestrictions)

Found 1 deadlock.
```

`settlement-ingest-3` holds `FundsLedger`, wants `ClientRestrictions`; `settlement-ingest-9` holds
`ClientRestrictions`, wants `FundsLedger` — a two-node cycle from a lock-ordering bug where one
call path acquires `FundsLedger` then `ClientRestrictions`, and another acquires them in the
opposite order.

**The gotcha.** The section is titled "Found one Java-level deadlock" even when there are more —
read to the bottom; `Found N deadlocks.` gives the true count, and each is printed as its own block.

> **Definition:** the deadlock section is the JVM's own cycle-detection result over the wait-for
> graph it already built from every `- locked`/`- waiting to lock` pair in the dump — not something
> the reader has to reconstruct by hand.

### `jcmd`'s dump family, and `VM.native_memory`

Supporting fact — `jcmd <pid> Thread.print` is equivalent to `jstack <pid>` against a running
process; `Thread.print -l` additionally prints the "Locked ownable synchronizers" detail for
`ReentrantLock`-held state, which plain `jstack` also prints but `jcmd`'s form makes explicit via
the flag. **Gotcha:** `jcmd` requires attach permission to the target JVM (same user, or
`-XX:+DisableAttachMechanism` not set); it fails silently different ways in a locked-down container
than a bare `jstack` invocation would.

> **Definition:** `jcmd <pid> Thread.print [-l]` is the live, in-process-attach equivalent of
> `jstack`, with `-l` making explicit that ownable-synchronizer detail is included.

Supporting fact — `jcmd <pid> Thread.dump_to_file -format=json|text <path>` writes the structured,
container-aware dump covered in the prior file (§3.12.20) — the only format that shows unmounted
virtual threads. `[X-REF 06]` **Gotcha:** the file path must be writable by the JVM's user, not the
operator's shell user, when the two differ (a common container surprise).

> **Definition:** `Thread.dump_to_file` is `jstack`'s structural successor — same underlying data
> for platform threads, plus the `StackChunk`-derived data `jstack` cannot reach.

Supporting fact — `jcmd <pid> VM.native_memory summary` (with `-XX:NativeMemoryTracking=summary` or
`detail` set at JVM start) reports the `Thread` category's committed/reserved native memory
separately from heap — this is where the settlement pool's platform-thread stack reservations
(prior file's ~1 MB-per-thread arithmetic) show up as a line item, distinct from the `Java Heap`
category the virtual-thread `StackChunk` cost lives in. `[X-REF 06]` **Gotcha:** NMT must be enabled
at JVM startup; it cannot be turned on retroactively against an already-running process.

> **Definition:** `VM.native_memory` is the tool that turns "how much native stack memory is the
> thread pool actually costing" from an estimate into a measured number, but only if NMT was
> enabled before the JVM started.

### `nid`, the join key to the OS

**Mental model.** `nid` in a dump header is not a Java-level identifier at all — it is the raw OS
thread id (Linux LWP id / `pid_t` of the task), printed in hexadecimal, sitting inside an otherwise
JVM-internal line purely so a human can cross the boundary from "which Java thread" to "which OS
thread" without any translation table.

**Why it exists.** `top -H` and `perf` operate entirely in OS-thread space; they have never heard
of a `Thread` object or a monitor. Without `nid`, "which Java thread is burning this CPU core"
would be unanswerable from OS tools alone — you would only know an anonymous LWP is hot, with no
path back to application code.

**When to reach for it.** Any time `top -H` or `perf top -p <pid>` shows one LWP consuming a
disproportionate share of CPU and the question is which Java code is responsible — most often a
`RUNNABLE` thread doing unexpectedly expensive work rather than one that is blocked (blocked
threads consume no CPU and would not show up hot in `top -H` in the first place).

**How it works, worked through end to end, `[NUM]`.** `top -H -p <pid>` reports LWP `20014`
(decimal) at 97% CPU. Convert to hex: `20014 → 0x4e2e`. Grep the dump for that hex value in the
`nid=` field:

```
$ top -H -p 84213
  PID USER  PR  NI  VIRT  RES  SHR S  %CPU %MEM  TIME+  COMMAND
20014 svc   20   0  4.2g 1.1g 42m R  97.3  6.9  10:12.44 java

$ printf '%x\n' 20014
4e2e

$ jstack 84213 | grep -A1 'nid=0x4e2e'
"settlement-ingest-3" #19 daemon prio=5 os_prio=0 cpu=3021.77ms elapsed=612.10s tid=0x00007f2b34012000 nid=0x4e2e runnable [0x00007f2ac3bfe000]
   java.lang.Thread.State: RUNNABLE
```

This is the same `settlement-ingest-3` from §3.13.1 — the CPU burning at 97% while it holds the
`FundsLedger` monitor is spent inside `CardPspClient.authorise`, confirming the contention's root
cause is not the lock acquisition itself but the PSP call made while holding it.

`[X-REF 11]` `/proc/<pid>/task/<tid>/status` (decimal `tid`, matching the decimal LWP `top -H`
already showed, not the hex `nid`) gives per-thread context-switch counts for the same thread —
covered in the next file, §3.13.11.

**The gotcha.** `top -H` reports the LWP id in **decimal**; the dump's `nid=` field is
**hexadecimal**. Comparing `20014` to `0x4e2e` directly without converting is the single most common
mistake in this workflow, and looks like the thread simply isn't in the dump at all.

![Finding the thread that is burning a core: top -H, hex, nid, stack](../diagrams/D-197-nid-to-top-h.svg)

**D-197** — the full loop: `top -H` gives a decimal LWP, convert to hex, match `nid=0x…` in the
dump, read that thread's stack, and cross-reference `/proc/<pid>/task/<tid>/status` for the same
thread's context-switch counts (covered fully in the next file).

> **Definition:** `nid` is the OS thread id printed in hex inside an otherwise Java-level dump line
> — the one field that lets `top -H`'s decimal LWP id be matched back to a named Java thread and its
> stack.

### JFR concurrency events and their thresholds

**Mental model.** A thread dump is one photograph; JFR is a continuously running recorder that logs
individual *events* — a monitor acquisition that took too long, a park, a thread starting — each
with a timestamp, duration where applicable, and (above a threshold) a stack trace, all without
requiring anyone to have caught the problem in the act with a manually triggered dump.

**Why it exists.** The `FundsLedger` contention in this file's running example was caught by a
dump taken because someone happened to notice throughput drop and ran `jstack` in time. JFR is the
answer to "what if nobody was watching at that exact moment" — it runs continuously, at low
overhead, and can be inspected after the fact.

**When to reach for it, versus a manual dump.** A dump answers "what is happening right now"; JFR
answers "what happened over the last N minutes, and how often." Reach for JFR when contention is
intermittent or already over by the time anyone reacts — exactly the shape of the next leaf's trap.

**How it works — the event set, `[RESEARCH]` verified against `default.jfc` and `profile.jfc` at
the `jdk-21` tag in `openjdk/jdk`.** The two shipped configurations enable different subsets at
different thresholds:

**D-198** — JFR concurrency events and their thresholds

| Event | Enabled in `default.jfc` | Default threshold (`default.jfc`) | Enabled / threshold in `profile.jfc` | What it proves | What it misses at that threshold |
|---|---|---|---|---|---|
| `jdk.JavaMonitorEnter` | Yes | **20 ms** | Yes, 10 ms | A thread waited at least the threshold to enter a `synchronized` block, with the stack and the monitor's class | Any contention episode shorter than the threshold — see the next leaf |
| `jdk.JavaMonitorWait` | Yes | 20 ms | Yes, 10 ms | A thread's `Object.wait()` (or timeout) took at least the threshold | Short `wait`/`notify` round-trips under the threshold |
| `jdk.JavaMonitorInflate` | No (disabled by default) | 20 ms (configured but inactive) | Not enabled by `profile.jfc` either | A monitor was inflated from a thin/biased lock to a heavyweight `ObjectMonitor` (`synchronized/03-internals-monitors.md`'s inflation path) | Nothing — it simply is not recorded unless explicitly re-enabled |
| `jdk.ThreadPark` | Yes | 20 ms | Yes, 10 ms | A `LockSupport.park`/`parkNanos` call (AQS's blocking primitive, `locks/05`) blocked at least the threshold | Short parks — most `getTask` polling cycles under light load never cross it |
| `jdk.ThreadStart` / `jdk.ThreadEnd` | Yes | No threshold (always recorded) | Yes | Every platform thread's lifecycle boundary — useful for counting pool churn | Nothing about what the thread did while alive |
| `jdk.ThreadSleep` | Yes | 20 ms | Yes, 10 ms | A `Thread.sleep` call held at least the threshold | Short, sub-threshold sleeps in a polling loop |
| `jdk.VirtualThreadStart` | No (disabled by default) | — | No (disabled by default) | Would record every virtual thread's creation | Nothing while disabled — the volume of virtual-thread starts at QuizStakes's scale (thousands/sec at peak) is exactly why this is off by default |
| `jdk.VirtualThreadEnd` | No (disabled by default) | — | No (disabled by default) | Would record every virtual thread's completion | Same volume reasoning as start |
| `jdk.VirtualThreadPinned` | No in `default.jfc`; enabled in `profile.jfc` | — | Yes, **20 ms** | A virtual thread stayed pinned to its carrier at least the threshold — the JFR-native alternative to `-Djdk.tracePinnedThreads` | Pins shorter than 20 ms, which still starve a carrier of other virtual-thread work briefly |
| `jdk.VirtualThreadSubmitFailed` | Yes | No threshold | Yes | A virtual-thread task submission failed (executor shutdown, resource exhaustion) | Nothing about *why* capacity was exhausted upstream |
| `jdk.ExecutorTaskSubmit` | **Not present in either `default.jfc` or `profile.jfc`** | — | — | Would tie a submitted task back to its executor and submitting thread if explicitly enabled via `-XX:StartFlightRecording=jdk.ExecutorTaskSubmit#enabled=true` | Off by default in both shipped profiles — QuizStakes's `executor.queued` Micrometer gauge (next file) is the always-on substitute for this specific signal |

**Insight:** `default.jfc` and `profile.jfc` do not merely toggle events on and off — where both
enable the same event, `profile.jfc` frequently uses a **lower** threshold (10 ms versus 20 ms for
the monitor and park events above), trading roughly double the overhead for roughly double the
sensitivity. Neither number is "the JFR threshold" in the abstract; it is always specific to which
`.jfc` produced the recording in hand.

**The gotcha, tied directly to the running incident.** A JFR recording taken with `default.jfc`
during the `FundsLedger` contention above would have recorded `jdk.JavaMonitorEnter` for
`settlement-ingest-7`'s wait, because it plausibly exceeded 20 ms under sustained contention — but
the next leaf shows the trap this same default hides.

> **Definition:** JFR concurrency events are threshold-gated, continuously-running recordings of
> individual blocking operations — `default.jfc` enables the monitor/park/sleep family at a 20 ms
> threshold and leaves per-virtual-thread lifecycle events off by default for volume reasons.

### The 20 ms threshold trap

**Mental model.** A threshold is a floor, not a filter for noise — everything below it is not
merely deprioritised, it does not exist in the recording at all.

**Why the default is 20 ms and not 0.** Recording a stack trace on *every* monitor entry, including
the overwhelming majority that succeed uncontended in nanoseconds, would make JFR's own overhead
dominate the very workload being profiled. The threshold is a deliberate trade: catch contention
severe enough to matter, at a cost low enough to run in production continuously.

**`[TRAP]` `[NUM]` The failure mode this creates.** Twelve `settlement-ingest-N` threads each
blocking on `FundsLedger`'s monitor for 8 ms, one hundred times a minute, is real, sustained
contention — 12 × 8 ms × 100/min ≈ 9.6 seconds of aggregate blocked time per minute, actual lost
throughput on a pool sized for the 3,400/sec settlement burst. None of it crosses the 20 ms
`jdk.JavaMonitorEnter` threshold in `default.jfc`. A default recording over that period shows **zero**
`jdk.JavaMonitorEnter` events for `FundsLedger` — not "few," zero — while the pool's actual
throughput has visibly degraded. The interview version of this question is almost always phrased as
"JFR shows no contention, but the pool is clearly slower — what's wrong," and the answer is never
"there is no contention"; it is "the contention is real and just under the floor."

**The fix, concretely.** Lower the threshold deliberately for the specific events under suspicion,
either at recording start or via `jcmd <pid> JFR.configure`:

```
$ jcmd 84213 JFR.start name=contention settings=profile \
    jdk.JavaMonitorEnter#threshold=0ms jdk.JavaMonitorEnter#stackTrace=true duration=120s filename=contention.jfr
```

Threshold `0ms` records every monitor-enter event regardless of duration, at higher overhead —
acceptable for a short, targeted diagnostic window, not as a permanent production setting.

**The gotcha.** Lowering the threshold to `0ms` on a hot lock like `FundsLedger`'s at 3,400
settlements/sec burst can itself become the dominant cost in the recording — the fix for "the
threshold hides short contention" is a short, targeted capture, not a permanently lowered
production default.

> **Definition:** a JFR threshold is a hard floor below which an event is never recorded at all — a
> default tuned for low steady-state overhead can make real, frequent, sub-threshold contention
> invisible in exactly the recording meant to catch it.

## Pitfalls

### Assuming any set of `BLOCKED` threads is a deadlock

**Wrong**
```
$ jstack 84213 | grep -c 'BLOCKED (on object monitor)'
11
```
Reporting "the settlement pool is deadlocked" from this count alone, before checking for a wait-for
cycle.

**Right**
```
$ jstack 84213 | grep -A1 'Found.*deadlock'
```
Read the deadlock section (§3.13.3) specifically — its presence or absence is the actual test. A
count of `BLOCKED` threads sharing one `waiting to lock` address and one `RUNNABLE` holder is
ordinary contention, not deadlock; only a cycle in the wait-for graph earns the word.

**Why people believe it:** "many threads stuck, throughput at zero" matches the intuitive picture
of deadlock closely enough that the distinguishing detail — a cycle versus a line — gets skipped
under incident pressure.

### Concluding "no contention" from a default JFR recording

**Wrong**
```
$ jcmd 84213 JFR.start name=check settings=default duration=60s filename=check.jfr
$ jfr print --events jdk.JavaMonitorEnter check.jfr
(no output)
```
Reporting "JFR confirms no `FundsLedger` contention" from this, while `executor.completed` (next
file) has visibly flattened and the pool's blocked-thread count is climbing.

**Right**
```
$ jcmd 84213 JFR.start name=check jdk.JavaMonitorEnter#threshold=0ms jdk.JavaMonitorEnter#stackTrace=true duration=60s filename=check.jfr
$ jfr print --events jdk.JavaMonitorEnter check.jfr | grep -c 'monitorClass = "com.quizstakes.ledger.FundsLedger"'
```
Lower the threshold for the specific event and class under suspicion before trusting an absence of
events as evidence of no contention — the default 20 ms threshold in `default.jfc` (§3.13.7)
guarantees short, frequent contention produces zero events regardless of how real it is.

**Why people believe it:** JFR is marketed, correctly, as low-overhead and comprehensive, and the
absence of an expected event category feels like strong negative evidence — without knowing the
event is threshold-gated, "zero events" and "no contention" look like the same fact.

## Cheat sheet

| Fact | Value / detail |
|---|---|
| `nid` in a dump | OS thread id in **hex** — `top -H`'s LWP column is **decimal**; convert before matching |
| Dump line proving contention | Matching `- waiting to lock <addr>` (many threads) against `- locked <addr>` (one thread) |
| Deadlock detection basis | JVM builds a wait-for graph from `- locked`/`- waiting to lock` pairs and runs cycle detection |
| Three dump signatures | Contention (shared lock address), saturation (all `RUNNABLE`, no shared address), idleness (all parked in `getTask`) |
| `jstack` vs `jcmd Thread.print` | Equivalent; `jcmd` needs live attach permission |
| Tool that sees unmounted virtual threads | `jcmd <pid> Thread.dump_to_file -format=json` only |
| `jcmd VM.native_memory` | Needs NMT enabled at JVM startup; cannot be enabled retroactively |
| `jdk.JavaMonitorEnter` threshold, `default.jfc` | **20 ms** |
| `jdk.JavaMonitorEnter` threshold, `profile.jfc` | **10 ms** |
| `jdk.JavaMonitorInflate` | Disabled in both `default.jfc` and `profile.jfc` |
| `jdk.VirtualThreadPinned` | Disabled in `default.jfc`; enabled at 20 ms in `profile.jfc` |
| `jdk.ExecutorTaskSubmit` | Not present in either shipped `.jfc` — must be explicitly enabled |
| `[VERSION-TRAP]` | `-Djdk.tracePinnedThreads` removed in JDK 24 (JEP 491); `jdk.VirtualThreadPinned` broadened there |

## Self-test

**Q1.** In a dump, thread A shows `- waiting to lock <0xABC>` and thread B shows
`- locked <0xABC>`. What, precisely, does the matching address prove, and what would make this a
deadlock instead of ordinary contention?

<details><summary>Answer</summary>

It proves thread B currently owns the monitor at heap address `0xABC` and thread A is queued to
enter it — a direct edge in the JVM's wait-for graph, not an inference. It becomes a deadlock only
if that graph contains a *cycle* — for example, thread B is itself shown `waiting to lock` some
other address that thread A holds. A single directed edge, however many threads point at the same
address, is contention; only a closed cycle is deadlock, and `jstack`'s "Found one Java-level
deadlock" section only prints when its detector finds such a cycle.

</details>

**Q2.** A dump shows forty `settlement-ingest-N` threads all `TIMED_WAITING (parking)` inside
`ThreadPoolExecutor.getTask`. Is this a problem, and what determines the answer?

<details><summary>Answer</summary>

Not by itself — this is the expected shape of a fully idle pool waiting for work, `getTask` parking
until the queue has something. Whether it is a problem depends on context external to this dump:
if `PaymentRun` submissions should be arriving continuously and are not, the actual fault is
upstream (a dead producer, a stuck upstream queue), not in this pool. The dump alone cannot answer
that; it only tells you this pool currently has nothing to do.

</details>

**Q3.** Why does `jstack`'s deadlock section sometimes miss a real deadlock in production?

<details><summary>Answer</summary>

The detector's cycle-detection graph is built entirely from JVM-managed monitors and
`ReentrantLock`-style state visible in the same dump. A deadlock cycle that includes a resource the
JVM does not track — most commonly a database row lock held across a JDBC call, waited on by
another thread also holding a JVM monitor the first thread needs — has one of its edges invisible to
the detector, so no cycle is reported even though the threads involved are genuinely stuck forever.

</details>

**Q4.** A JFR recording taken with `default.jfc` over a 5-minute window shows zero
`jdk.JavaMonitorEnter` events for `FundsLedger`, but the settlement pool's blocked-thread count was
elevated the entire window. Reconcile these two facts.

<details><summary>Answer</summary>

They are not actually contradictory. `default.jfc` sets a 20 ms threshold on `jdk.JavaMonitorEnter`
— any monitor-enter wait shorter than 20 ms is never recorded as an event at all, regardless of how
frequently it happens. A pattern of short (say, 5-10 ms), very frequent blocks can keep a
JMX-derived blocked-state gauge elevated while producing zero qualifying JFR events. The fix is
re-recording with the threshold explicitly lowered (ideally to 0 ms) for the specific event and
class under suspicion, not trusting the default recording's absence of events as proof of absence
of contention.

</details>

**Q5.** What is the join key between a `jstack` dump and `top -H`'s output, and what is the single
most common mistake made using it?

<details><summary>Answer</summary>

The dump's `nid=` field is the OS thread id in hexadecimal; `top -H`'s LWP column is the same OS
thread id in decimal. The join requires converting one to match the other's base. The most common
mistake is comparing them directly without converting — for example searching a dump for the
literal decimal string `top -H` printed, which will not match the hex `nid=` field, and concluding
the thread "isn't in the dump" when it simply wasn't matched correctly.

</details>

**Q6.** Why does `profile.jfc` use a 10 ms threshold on `jdk.JavaMonitorEnter` where `default.jfc`
uses 20 ms, and what does that trade-off buy?

<details><summary>Answer</summary>

`profile.jfc` is the higher-overhead, higher-fidelity configuration meant for deliberate,
time-boxed diagnostic sessions rather than always-on production recording. Halving the threshold
roughly doubles both the sensitivity (catching shorter blocking episodes) and the recording
overhead, since more events qualify and each carries a stack trace. It is a deliberate trade of
overhead for resolution, not a universally "better" default — which is exactly why the two `.jfc`
files disagree and a reader must state which one a given number came from.

</details>

---

**Leaves covered:** 3.13.1–3.13.7 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-195, D-196, D-197, D-198
**Target version:** Java 21 LTS
**Lines:** 560
