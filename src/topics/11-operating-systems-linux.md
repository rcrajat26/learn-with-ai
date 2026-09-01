# 11 — Operating Systems & Linux for Backend Engineers

Scope: the OS mechanisms that show up in production incidents, plus the command-line toolkit to
triage a misbehaving box. The interview version of this topic is almost always "the service is slow /
the box is unhealthy — what do you do?", so the tooling section is as important as the theory.

---

## 1. Processes vs threads — the kernel's view

**Process:** an instance of a running program with its own **virtual address space**, its own file
descriptor table, and its own set of resources. Isolation is the point: process A cannot read process
B's memory (barring explicit shared memory or ptrace).

**Thread:** a schedulable execution context *inside* a process. Threads in a process share the address
space (heap, globals, code), the fd table, and signal handlers. Each has its own **stack**, program
counter, and registers.

On Linux both are created by `clone()`; the difference is which resources you ask to share. The
kernel schedules `task_struct`s and largely doesn't care whether you call one a "thread". A "thread
group" of tasks sharing an mm is what userspace calls a process.

| | Process | Thread |
|---|---|---|
| Address space | private | shared |
| Creation cost | high (fork, page tables) | lower |
| Communication | IPC: pipes, sockets, shared mem | shared memory — just variables |
| Failure isolation | a crash kills only that process | **an unhandled crash can take the whole process down** |
| Context switch | expensive (TLB flush, page tables) | cheaper (same address space) |

Java maps each platform `Thread` to one OS thread (a 1:1 model). Default stack reservation is ~1 MB
(`-Xss`), which is why thousands of platform threads is expensive and why virtual threads exist
(topic 10, §15).

**Thread states you'll see in a thread dump:** `RUNNABLE` (running or ready), `BLOCKED` (waiting for a
monitor lock), `WAITING`/`TIMED_WAITING` (`wait()`, `park()`, `sleep()`, waiting on a pool). Reading a
dump: many threads `BLOCKED` on the same monitor = lock contention; many `WAITING` on a pool = the
pool is exhausted or the downstream is hung; many `RUNNABLE` in the same stack frame = a real CPU hot
spot.

> **Trap:** "`RUNNABLE` means it's using CPU." A Java thread blocked in a socket read shows as
> `RUNNABLE`, because the JVM cannot distinguish "in a syscall" from "computing". Correlate with
> `%us` from `top` before concluding you're CPU-bound.

---

## 2. Context switches and their real cost

A context switch saves the current task's registers and stack pointer, updates the scheduler's
bookkeeping, and restores another task's. Direct cost is roughly **1–5 µs**. The *indirect* cost is
usually larger: the new task's data isn't in L1/L2 cache, so it runs slowly until caches refill
("cache pollution"). A process switch additionally changes page tables, flushing or partially
invalidating the TLB — meaningfully worse than a thread switch.

Switches happen on: timeslice expiry (involuntary), blocking on I/O or a lock (voluntary), a higher
priority task waking, or a syscall that sleeps.

Practical implication: **more threads is not more throughput.** Past roughly the number of cores (for
CPU-bound work), extra threads only add switching overhead and memory. For I/O-bound work more threads
do help, because they're blocked most of the time — but that's precisely the case where async or
virtual threads do it more cheaply.

Measure with `vmstat 1` — the `cs` column is context switches/sec, `in` is interrupts/sec. Tens of
thousands of `cs` per second on a small box with high `%sy` is a strong signal of thread thrashing or
lock convoying.

---

## 3. Virtual memory, pages, and the page cache

Every process sees a private, contiguous **virtual address space**. The MMU translates virtual pages
(4 KB typically; 2 MB "huge pages") to physical frames via page tables, cached in the **TLB**. A
translation miss on a page not resident in RAM raises a **page fault**:

- **Minor fault:** the page is in memory but not mapped into this process (e.g. shared library
  already loaded, or copy-on-write after fork). Cheap.
- **Major fault:** the page must be read from disk. Expensive — this is what "swapping/thrashing"
  feels like.

**Overcommit:** Linux lets processes allocate more virtual memory than physical RAM, because most
allocations are never fully touched. Memory is only really consumed when a page is written. Hence
"virtual size" (VSZ/`VIRT`) is nearly meaningless for a JVM; **RSS** (resident set size) is what's
actually in RAM.

**Page cache.** Linux uses all otherwise-free RAM to cache file contents. A read of a file already in
page cache never touches the disk. This is why databases benefit from a large machine even when their
own buffer pool is modest, and why the first query after a restart is slow (cold cache).

### `free -h`: "free" vs "available" — the classic misread

```
              total        used        free      shared  buff/cache   available
Mem:            16Gi       6.0Gi       0.3Gi       0.1Gi       9.7Gi       9.4Gi
```

`free` = **completely unused RAM**, which on a healthy long-running Linux box is near zero *by design*
— idle RAM is wasted RAM, so the kernel fills it with page cache. `buff/cache` is reclaimable.
**`available`** is the number that matters: an estimate of how much a new process could get, counting
reclaimable cache.

> **Trap:** "We're out of memory, `free` shows 300 MB!" Almost always wrong. Read the `available`
> column. Only when `available` is small *and* swap is being actively used are you genuinely short.

**Swap** extends RAM onto disk. Modest swap is a useful safety valve for cold anonymous pages, but
active swapping of a JVM heap is pathological — the GC touches the whole heap, so every collection
faults pages back in and latency explodes. Common practice: disable swap for latency-sensitive JVM
services (Kubernetes historically required `swapoff` for this reason), size the heap to fit, and let
the OOM killer act decisively rather than letting the box die slowly. `vmstat 1`'s `si`/`so` columns
(swap in/out) should be 0.

---

## 4. Blocking syscalls and thread states

A syscall is a controlled transition into kernel mode (`syscall` instruction). A **blocking** syscall
(`read` on a socket with no data, `write` to a full pipe, `accept` with no pending connection) puts
the calling thread into an uninterruptible or interruptible sleep and yields the CPU. The thread
consumes no CPU while blocked — but it *does* consume its stack, its slot in whatever pool owns it,
and any locks it holds.

This is the mechanism behind the cascading failure in topic 10 §7: a hung downstream doesn't burn CPU,
it burns **threads**. The box looks idle and the service is dead.

Process states in `ps`/`top`:

| Code | Meaning |
|---|---|
| `R` | running or runnable |
| `S` | interruptible sleep (waiting on I/O, a lock, a timer) — most threads, most of the time |
| `D` | **uninterruptible sleep** — usually blocked on disk/NFS I/O; cannot even be killed with SIGKILL |
| `Z` | zombie — exited, parent hasn't `wait()`ed for the exit status |
| `T` | stopped (SIGSTOP, or under a debugger) |

Processes stuck in `D` are the signature of a storage problem (a hung NFS mount, a failing disk).
`kill -9` will not touch them; you fix the I/O or reboot.

Zombies consume only a PID entry. A handful is normal churn; thousands means a parent process is
leaking children — a bug in the parent, not in the children.

---

## 5. File descriptors, `ulimit`, and "Too many open files"

An fd is a small integer indexing the process's open-file table. Sockets, files, pipes, epoll
instances, and inotify watches are all fds. 0/1/2 are stdin/stdout/stderr.

**Limits:**
```bash
ulimit -n              # current soft limit for this shell
ulimit -Hn             # hard limit
cat /proc/<pid>/limits # limits of a *running* process — the authoritative one
ls /proc/<pid>/fd | wc -l   # how many it currently has
cat /proc/sys/fs/file-max   # system-wide ceiling
```

The critical subtlety: **the limit that applies is the one in force when the process started**, not
what your shell shows now. Raise it in systemd (`LimitNOFILE=`), the container runtime, or
`/etc/security/limits.conf` — and then verify via `/proc/<pid>/limits`.

**`java.net.SocketException: Too many open files` / `java.io.IOException: Too many open files`** has
two causes, and you must distinguish them:

1. **Limit too low for legitimate load.** 1024 fds with 2,000 concurrent connections. Raise it
   (65536 is a normal service value).
2. **An fd leak.** Streams, HTTP responses, or JDBC connections never closed. fd count grows
   monotonically and never drops. This is a bug; raising the limit only delays the crash.

**Diagnose with `lsof`:**
```bash
lsof -p <pid> | wc -l                 # total fds for a process
lsof -p <pid> | awk '{print $5}' | sort | uniq -c | sort -rn   # by fd type
lsof -p <pid> | grep -c TCP           # sockets specifically
lsof -i :8080                         # who is on this port
lsof +L1                              # deleted-but-still-open files (disk-full culprit, §8)
```

If the count by type shows thousands of `REG` (regular files) for the same path, it's a stream leak.
Thousands of `TCP` in `CLOSE_WAIT` is a socket leak (topic 10, §8). The fix in Java is always
try-with-resources; the fix in review is never trusting a `finally` block written by hand.

---

## 6. Signals and graceful shutdown

A signal is an asynchronous notification delivered to a process.

| Signal | Number | Catchable | Meaning |
|---|---|---|---|
| `SIGTERM` | 15 | **yes** | "please terminate" — the polite request, the default of `kill` |
| `SIGKILL` | 9 | **no** | kernel destroys the process immediately; no cleanup runs |
| `SIGINT` | 2 | yes | Ctrl-C |
| `SIGHUP` | 1 | yes | terminal closed; conventionally repurposed as "reload config" |
| `SIGSTOP`/`SIGCONT` | 19/18 | no/yes | suspend / resume |
| `SIGQUIT` | 3 | yes | Ctrl-\; **to a JVM, prints a full thread dump to stdout** — enormously useful |
| `SIGSEGV` | 11 | — | invalid memory access |

`kill -3 <java-pid>` giving you a thread dump for free (no jstack, no agent) is worth memorising.

### The graceful shutdown flow

1. Orchestrator (systemd, Docker, Kubernetes) sends **SIGTERM**.
2. Application catches it and:
   - **stops accepting new work** — fails the readiness probe / deregisters from the LB / pauses
     queue consumers;
   - **finishes in-flight requests** (bounded by a drain deadline);
   - flushes buffers (logs, metrics, batched writes);
   - closes connection pools, releases locks, commits or aborts transactions;
   - exits 0.
3. If it hasn't exited within the grace period (Docker: 10 s default; Kubernetes:
   `terminationGracePeriodSeconds`, 30 s default), the orchestrator sends **SIGKILL** and the process
   dies mid-flight.

**Ordering matters and is routinely got wrong.** If you close the DB pool before draining in-flight
requests, every in-flight request fails. Drain first, then close resources.

**Java:**
```java
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    server.stopAcceptingNewRequests();
    awaitInFlight(Duration.ofSeconds(20));
    pool.close();
}));
```
Spring Boot does this for you with `server.shutdown=graceful` and
`spring.lifecycle.timeout-per-shutdown-phase=20s`. Shutdown hooks do **not** run on SIGKILL, on
`Runtime.halt()`, or on a JVM crash — so never make correctness depend on them; they are best-effort
cleanup, not a durability mechanism.

> **Trap (Docker PID 1):** If your container's entrypoint is a shell script (`CMD java -jar app.jar`
> in *shell* form), the shell is PID 1 and it does not forward SIGTERM to the JVM. Your app never gets
> the signal, sits there for the full grace period, and is SIGKILLed every single deploy — silently
> losing in-flight requests. Fix: use exec form (`CMD ["java","-jar","app.jar"]`), `exec java ...` in
> the script, or an init like `tini`. See topic 19.

> **Trap (Kubernetes race):** SIGTERM and endpoint-removal happen *concurrently*, not in sequence. For
> a few hundred milliseconds the LB still sends traffic to a pod that is already shutting down. Fix: a
> `preStop` hook that sleeps ~5 s before the signal, so deregistration propagates first. Topic 19 §8.

---

## 7. Box triage toolkit — "the service is slow, you have SSH"

Work top-down: is it CPU, memory, disk, or network? Then which process, then which thread.

### `top` / `htop`

```
top - 14:22:31 up 41 days,  3:12,  2 users,  load average: 8.42, 7.90, 6.11
%Cpu(s): 22.1 us,  4.0 sy,  0.0 ni, 12.3 id, 61.2 wa,  0.0 hi,  0.4 si
```

**Load average vs cores.** The three numbers are 1/5/15-minute averages of runnable + uninterruptible
tasks. They are meaningless without the core count (`nproc`). Load 8 on 16 cores = half-utilised.
Load 8 on 2 cores = 4× oversubscribed. Trend matters more than value: 8.42 / 7.90 / 6.11 is *rising*.

Note the Linux quirk: load average includes `D`-state tasks, so a load spike can indicate an I/O stall
with the CPUs completely idle.

**The CPU-time breakdown is the actual diagnostic:**

| Field | Meaning | High value suggests |
|---|---|---|
| `us` | user-space CPU | your code: hot loop, GC, serialisation, regex |
| `sy` | kernel CPU | syscall storm, context switching, network interrupts, tiny reads/writes |
| `ni` | niced user processes | background jobs |
| `id` | idle | if high while latency is bad, you are **not** CPU-bound — look at I/O or locks |
| `wa` | **I/O wait** | disk or network storage bottleneck; CPU idle waiting on I/O |
| `hi`/`si` | hardware/software interrupts | high `si` = heavy network packet processing |
| `st` | **steal** | the hypervisor gave your vCPU to someone else — noisy neighbour on a shared instance |

In the sample above, 61% `wa` with 12% idle: this box is I/O-bound. Do not go looking at GC logs.

Inside `top`: `1` shows per-core lines (one core pegged at 100% with 15 idle = a single-threaded
bottleneck), `M` sorts by memory, `P` by CPU, `H` shows individual **threads** — which lets you find
the hot thread's TID and map it to a Java thread (`printf '%x\n' <tid>` → match `nid=0x...` in a
`jstack` dump). That two-step is the standard "which Java thread is eating a core" recipe.

`htop` is the same information with colour, per-core bars, tree view (`F5`), and searchable filtering
(`F4`) — strictly nicer when it's installed.

### `free -h`
See §3. Read the `available` column. Check `Swap` used and `vmstat`'s `si`/`so`.

### Disk: `df` vs `du`

```bash
df -h            # per-filesystem usage — "am I full?"
df -i            # INODE usage — you can be "full" with free bytes
du -sh /var/log/* | sort -h    # what is consuming a directory
du -xh /var --max-depth=2 | sort -h | tail -20   # -x stays on one filesystem
```

- `df` asks the filesystem; `du` walks the tree and adds up files.
- **Inode exhaustion**: millions of tiny files (session files, unrotated logs, cached fragments)
  exhaust inodes while `df -h` shows free space. `No space left on device` with 40% free = check
  `df -i`.
- **`df` and `du` disagree** when a deleted file is still held open by a process: the directory entry
  is gone (so `du` doesn't count it) but the blocks aren't freed until the last fd closes (so `df`
  does). Classic cause: log rotation that deleted the file without signalling the writer to reopen.
  Find it with `lsof +L1`; fix by restarting the holder or having it reopen.

### `iostat`

```bash
iostat -xz 1
```
Key columns: `%util` (fraction of time the device had I/O in flight — near 100% means saturated for a
single-queue device, though it's misleading for SSD/NVMe which handle parallel requests), `await`
(average ms per request, including queueing — the latency your app actually feels), `r/s`/`w/s`
(IOPS), `rkB/s`/`wkB/s` (throughput), `aqu-sz` (queue depth).

High `await` with modest IOPS on a cloud volume usually means you've exhausted a **provisioned IOPS
or burst-credit budget** (gp2 burst balance, EBS baseline). That's a billing decision surfacing as a
latency incident.

### `ps` — targeted, sortable

```bash
ps aux --sort=-%cpu | head -15        # top CPU consumers
ps aux --sort=-%mem | head -15        # top memory consumers
ps -eLf | wc -l                       # total threads on the box
ps -o pid,ppid,stat,etime,rss,cmd -p <pid>
ps -eo pid,stat,cmd | awk '$2 ~ /^D/' # anything stuck in uninterruptible I/O
```
`RSS` is resident memory (real). `VSZ` is virtual and will look absurd for a JVM — ignore it.

### Network
```bash
ss -tunap                      # sockets with process names (replaces netstat)
ss -s                          # summary, incl. TIME_WAIT count
ss -tan state established | wc -l
ping / traceroute / mtr        # reachability and per-hop loss
dig +short api.example.com     # resolution; dig @8.8.8.8 to bypass local resolver
curl -w '@curl-format.txt' -o /dev/null -s https://host/   # DNS/connect/TLS/TTFB breakdown
tcpdump -i any -n port 8080 -c 100     # last resort, but definitive
```
`curl -w` with a format file that prints `time_namelookup`, `time_connect`, `time_appconnect`,
`time_starttransfer`, `time_total` tells you *which phase* of topic 10's pipeline is slow. Learn it.

### Triage order (say this out loud in an interview)
1. `uptime` / `top` — load vs cores, and the `us`/`sy`/`wa`/`st` split.
2. If `us` high → which process, then which thread (`top -H`), then a thread dump or profiler.
3. If `sy` high → syscall/context-switch storm (`vmstat 1`, `strace -c -p <pid>`).
4. If `wa` high → `iostat -xz 1`, then `du`/`df`, then which process (`iotop`, `pidstat -d 1`).
5. If all idle but slow → it's **waiting**: locks, downstream calls, pool exhaustion. Thread dump.
6. If `st` high → noisy neighbour; move the instance.
7. Memory: `free -h` (available!), then `ps --sort=-%mem`, then `dmesg -T | grep -i oom`.
8. Disk full: `df -h`, `df -i`, `du -xh`, `lsof +L1`.
9. Always ask **what changed** — deploy, config, traffic, dependency (topic 20 §7).

---

## 8. Log combat

```bash
tail -f /var/log/app.log                 # follow
tail -F /var/log/app.log                 # follow *by name* — survives log rotation. Prefer -F.
tail -n 500 app.log
less +F app.log                          # follow, then Ctrl-C to scroll/search, F to resume
```

`less` beats `cat`/`vim` on a 4 GB log: it doesn't load the file. Inside: `/pattern` search, `n`/`N`
next/prev, `G` end, `g` start, `&pattern` show only matching lines, `-S` chop long lines.

**grep pipelines** — the daily bread:
```bash
grep -i 'timeout' app.log
grep -c ERROR app.log                    # count
grep -n ERROR app.log                    # with line numbers
grep -C 5 'NullPointerException' app.log # 5 lines of context either side (-A after, -B before)
grep -v 'health' app.log                 # invert: drop healthcheck noise
grep -E 'ERROR|FATAL' app.log            # extended regex alternation
grep -r 'apiKey' src/                    # recursive
zgrep ERROR app.log.2.gz                 # search compressed rotated logs
```

Composed:
```bash
# Top 10 error messages by frequency
grep ERROR app.log | awk -F'ERROR' '{print $2}' | sort | uniq -c | sort -rn | head

# Requests per minute around the incident
grep '2026-08-21T14:' app.log | cut -c1-16 | uniq -c

# Slowest endpoints from an access log (field 7 = path, field 10 = duration)
awk '{print $10, $7}' access.log | sort -rn | head -20

# Trace one request across a multi-line log
grep 'correlationId=abc-123' app.log
```
That last one is the payoff for topic 20's correlation IDs: without one, you cannot reconstruct a
single request from an interleaved log.

**`jq` for structured logs** (and every JSON API response):
```bash
jq . response.json                                    # pretty-print
jq -r '.items[].name' response.json                   # raw strings, no quotes
jq 'select(.level=="ERROR")' app.jsonl                # filter a JSON-lines log
jq -r 'select(.durationMs > 1000) | "\(.path) \(.durationMs)"' app.jsonl
jq -s 'group_by(.path) | map({path: .[0].path, n: length}) | sort_by(-.n)' app.jsonl
kubectl logs deploy/api | jq -r 'select(.traceId=="abc") | .message'
```

Also worth knowing: `wc -l` (count), `sort -u`, `cut -d',' -f2`, `head`/`tail -n +N`, `sed -n
'100,200p'` (line range), `xargs`, and `journalctl -u myservice -f --since '10 min ago'` on
systemd boxes.

---

## 9. cron

```
┌ minute (0-59)
│ ┌ hour (0-23)
│ │ ┌ day of month (1-31)
│ │ │ ┌ month (1-12)
│ │ │ │ ┌ day of week (0-7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *  /usr/local/bin/job.sh
```
`*/15 * * * *` = every 15 minutes. `0 2 * * *` = 02:00 daily. `0 9 * * 1-5` = 09:00 weekdays.
`crontab -e` edits, `crontab -l` lists, `/etc/cron.d/*` for system jobs.

**The four cron failures everyone hits:**
1. **Minimal environment.** cron does not run your shell profile. `$PATH` is tiny, `JAVA_HOME` is
   unset. Use absolute paths for everything and set env vars explicitly in the crontab.
2. **Output goes to mail, i.e. nowhere.** Always redirect:
   `>> /var/log/job.log 2>&1`. Without `2>&1` you lose exactly the errors you need.
3. **Overlapping runs.** A job scheduled every 5 minutes that takes 7 minutes will pile up until the
   box dies. Guard with `flock -n /var/run/job.lock <cmd>`.
4. **Timezone.** cron uses the system timezone; DST transitions can skip or double-run a job.

**Distributed cron is the real interview question.** Cron on N replicas runs the job N times. Options:
a leader-elected scheduler, a distributed lock (topic 14 — with the expiry hazard), a dedicated
scheduler service (Quartz with a JDBC job store, ShedLock, Kubernetes `CronJob` with
`concurrencyPolicy: Forbid`), or making the job idempotent so double-running is harmless. **Idempotency
is the most robust answer** because every locking scheme has a failure mode.

---

## 10. SSH, keys, and file transfer

```bash
ssh user@host
ssh -i ~/.ssh/id_ed25519 user@host
ssh -p 2222 user@host
ssh -J bastion.example.com user@private-host      # jump host / bastion (ProxyJump)
ssh -L 5432:db.internal:5432 user@bastion         # local port forward: localhost:5432 → db
ssh -N -f -L ...                                  # no command, background
```

**Key mechanism.** You generate a keypair (`ssh-keygen -t ed25519 -C "you@example.com"`). The
**public** key goes into `~/.ssh/authorized_keys` on the server; the **private** key never leaves your
machine. On connect, the server sends a challenge, you sign it with the private key, the server
verifies with the public key. Nothing secret crosses the wire — this is why keys beat passwords.

Permissions are enforced strictly: `~/.ssh` must be `700`, `authorized_keys` and private keys `600`.
"Permissions 0644 for 'id_rsa' are too open" is a refusal, not a warning.

`~/.ssh/config` saves enormous time:
```
Host prod-api
    HostName 10.0.4.17
    User deploy
    IdentityFile ~/.ssh/prod_ed25519
    ProxyJump bastion.example.com
    ServerAliveInterval 30
```
Then just `ssh prod-api`.

`ssh-agent` holds decrypted keys in memory (`ssh-add`); `-A` forwards the agent to the remote host —
convenient but a security risk on hosts you don't fully trust (root there can use your keys).

`known_hosts` pins the server's host key; a changed fingerprint is either a rebuild or a MITM. Do not
blindly `ssh-keygen -R`.

**Copying files:**
```bash
scp file.txt user@host:/tmp/
scp -r dir/ user@host:/tmp/
scp user@host:/var/log/app.log ./
rsync -avz --progress dir/ user@host:/dest/     # resumable, incremental — better for anything large
```

In AWS, prefer **SSM Session Manager** over SSH: no open port 22, no key distribution, IAM-controlled,
audited. Mention it — it signals current practice.

---

## 11. Finding and killing a process

```bash
ps aux | grep -i myapp        # note: also matches the grep itself
pgrep -fa myapp               # cleaner: full command line
pgrep -f 'java.*myapp'
lsof -i :8080                 # what is holding the port
ss -lptn 'sport = :8080'
fuser -n tcp 8080
```

**The kill workflow — escalate, never lead with `-9`:**
```bash
kill <pid>            # SIGTERM (15): the graceful request. ALWAYS FIRST.
kill -3 <java-pid>    # thread dump first, if you want to know WHY it hung
# wait 10-30s, check with: ps -p <pid>
kill -9 <pid>         # SIGKILL: only if it ignored SIGTERM
pkill -f 'java.*myapp'
killall java          # blunt; avoid on shared boxes
```

`kill -9` skips shutdown hooks, buffered log flushes, in-flight request completion, lock release, and
clean connection teardown. It can leave stale distributed locks, half-written files, and orphaned
transactions. Reaching for it first is a genuine red flag in an interview; escalating to it after
SIGTERM is ignored is correct.

Before killing a hung JVM, capture evidence: `kill -3` (thread dump to stdout), `jstack <pid>`,
`jcmd <pid> GC.heap_info`, `jmap -histo:live <pid> | head -30`, or a heap dump
(`jcmd <pid> GC.heap_dump /tmp/heap.hprof`). Once it's gone, so is the diagnosis.

---

## 12. OOM killer vs JVM OutOfMemoryError

These are completely different events with different evidence, and confusing them sends you down the
wrong path for hours.

| | **Linux OOM killer** | **JVM `OutOfMemoryError`** |
|---|---|---|
| Who acts | the kernel | the JVM |
| Trigger | the **host/cgroup** is out of physical memory | the **Java heap** (or metaspace, or direct buffers) is full and GC can't reclaim |
| What happens | `SIGKILL` to the highest-`oom_score` process — no cleanup, no stack trace | an `Error` is thrown; stack trace in logs; hooks may run |
| Evidence | `dmesg -T \| grep -i 'killed process'`; exit code **137** (128+9); Kubernetes `OOMKilled` | `java.lang.OutOfMemoryError: Java heap space` in the log; heap dump if `-XX:+HeapDumpOnOutOfMemoryError` |
| Usual cause | heap+metaspace+stacks+native > container limit | leak, or heap simply too small for the workload |
| Fix | raise the limit, or lower `-XX:MaxRAMPercentage` | fix the leak, or raise `-Xmx` |

The kernel scores candidates by memory footprint (adjustable via `/proc/<pid>/oom_score_adj`) and
kills the worst offender. In a container, the *cgroup* limit triggers it, so your JVM can be killed
while the host has plenty of free RAM.

> **Trap:** A JVM in a container needs more than `-Xmx`. Total RSS = heap + metaspace + code cache +
> thread stacks (~1 MB each) + direct/NIO buffers + GC structures + JVM overhead. Setting `-Xmx` equal
> to the container memory limit guarantees an eventual OOMKill with **no Java stack trace at all** —
> which is exactly why people misdiagnose it. Use `-XX:MaxRAMPercentage=70` (or ~75) and let the JVM
> read the cgroup limit; modern JVMs are container-aware by default. See topic 19 §7.

Exit code 137 with no application error in the log is the tell-tale. If you see a Java stack trace,
it's a JVM OOM; if the process just vanishes, check `dmesg`.

---

## 13. Swap, briefly

Swap is disk used as overflow RAM. Pages the kernel judges cold get written out; touching them again
causes a major fault. `vm.swappiness` (0–100, default 60) tunes how eagerly the kernel prefers
swapping anonymous pages over dropping page cache.

For a JVM service: some swap is a useful cushion against a sudden spike (better than an instant
OOMKill), but *sustained* swapping is worse than dying, because the GC's whole-heap traversal drags
every swapped page back in and p99 latency goes from 50 ms to 30 s while nothing looks "down". Set
`vm.swappiness=1`–`10` on database and JVM boxes, or disable swap entirely and size memory properly.
Watch `si`/`so` in `vmstat 1` — non-zero on a latency-sensitive box is an alert, not a curiosity.

---

## Atomic concept checklist

- [ ] Process = own address space and fd table; thread = shared address space, own stack.
- [ ] Both are `clone()` on Linux; the difference is which resources are shared.
- [ ] A thread crash can kill the whole process; a process crash is isolated.
- [ ] Java platform threads are 1:1 with OS threads and reserve ~1 MB of stack each.
- [ ] Thread-dump states: `RUNNABLE`, `BLOCKED` (monitor), `WAITING`/`TIMED_WAITING` (pool, sleep).
- [ ] Java shows socket reads as `RUNNABLE` — don't infer CPU usage from it.
- [ ] Context switch ≈ 1–5 µs direct, plus cache/TLB pollution; process switches cost more than thread switches.
- [ ] More threads ≠ more throughput past core count for CPU-bound work; `vmstat`'s `cs` column reveals thrashing.
- [ ] Virtual memory: pages, MMU, TLB; **minor** fault = already in RAM, **major** fault = disk read.
- [ ] Overcommit means VSZ is meaningless for a JVM; read RSS.
- [ ] Linux fills free RAM with page cache by design — `free` near zero is healthy.
- [ ] **Read the `available` column of `free -h`, not `free`.**
- [ ] Blocking syscalls burn threads, not CPU — the box looks idle while the service is dead.
- [ ] `D` state = uninterruptible I/O sleep; `kill -9` cannot touch it.
- [ ] Zombies are exited children the parent never reaped; thousands = a parent bug.
- [ ] fds cover files, sockets, pipes, epoll; `ulimit -n` in containers often defaults to 1024.
- [ ] The applicable fd limit is the one at process start — verify via `/proc/<pid>/limits`.
- [ ] "Too many open files" = limit too low **or** an fd leak; a monotonic rise means leak.
- [ ] `lsof -p <pid>`, `lsof -i :port`, `lsof +L1` are the three you need.
- [ ] SIGTERM (15) is catchable and polite; SIGKILL (9) is uncatchable and skips all cleanup.
- [ ] `kill -3` on a JVM dumps all thread stacks — free diagnostics before you kill it.
- [ ] Graceful shutdown order: stop accepting → drain in-flight → flush → close pools → exit.
- [ ] Shutdown hooks never run on SIGKILL — never depend on them for correctness.
- [ ] Docker shell-form `CMD` makes the shell PID 1 and swallows SIGTERM; use exec form or `tini`.
- [ ] Kubernetes deregistration races SIGTERM; a `preStop` sleep fixes the dropped-request window.
- [ ] Load average is meaningless without `nproc`, and includes `D`-state tasks.
- [ ] `top` CPU split: `us` (your code), `sy` (kernel/syscalls), `wa` (I/O bound), `st` (noisy neighbour), `id`.
- [ ] High `id` with bad latency = you're waiting on locks or downstreams, not CPU.
- [ ] `top -H` + `printf '%x'` maps a hot OS thread to a Java thread in a `jstack` dump.
- [ ] `df -h` for space, `df -i` for **inodes** — you can be full with bytes free.
- [ ] `df`/`du` disagreement = a deleted file still held open; find it with `lsof +L1`.
- [ ] `iostat -xz 1`: `await` is the latency you feel; `%util` near 100% means a saturated device.
- [ ] High `await` on cloud storage often means exhausted IOPS/burst credits.
- [ ] `ps aux --sort=-%mem`; RSS is real memory, VSZ is not.
- [ ] Triage order: load vs cores → CPU split → per-process → per-thread → **what changed**.
- [ ] `tail -F` (capital F) survives log rotation; `tail -f` does not.
- [ ] `grep -C` for context, `-v` to drop noise, `zgrep` for rotated `.gz` logs.
- [ ] `sort | uniq -c | sort -rn` is the universal "top N by frequency" idiom.
- [ ] `jq -r`, `select()`, and `group_by` handle structured logs and API responses.
- [ ] Correlation IDs are what make `grep` able to reconstruct one request.
- [ ] cron: minimal `$PATH`, output lost unless redirected with `2>&1`, overlapping runs need `flock`.
- [ ] Distributed cron double-runs on N replicas: leader election, lock, or **idempotency** (best).
- [ ] SSH keys: public key on the server, private key never leaves; strict `600`/`700` permissions.
- [ ] `~/.ssh/config` with `ProxyJump`; `-L` for port forwarding; prefer AWS SSM over open port 22.
- [ ] Kill workflow: `kill -3` (dump) → `kill` (TERM) → wait → `kill -9` only if ignored.
- [ ] Capture a thread/heap dump before killing a hung JVM; evidence dies with the process.
- [ ] OOM killer = kernel, cgroup/host memory, exit **137**, `dmesg`, no stack trace.
- [ ] JVM OOM = heap exhausted, `java.lang.OutOfMemoryError` with a stack trace in the log.
- [ ] JVM RSS = heap + metaspace + code cache + thread stacks + direct buffers; never set `-Xmx` = container limit.
- [ ] Use `-XX:MaxRAMPercentage` (~70) so the JVM sizes itself from the cgroup limit.
- [ ] Sustained swapping destroys JVM latency because GC touches the whole heap; keep `si`/`so` at 0.