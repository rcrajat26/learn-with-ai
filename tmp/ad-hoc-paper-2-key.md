# Ad-hoc Paper 2 — Answer Key

Scoring: 1 = matches the key's marks · 0.5 = right idea with a named gap ·
0 = wrong or blank.

**Q1.** A **process** owns its own address space (virtual memory), file
descriptor table, and PID; a **thread** has its own stack, registers and
program counter but shares the address space, fds, and open files with its
siblings. On Linux both are created by **`clone()`** — the difference is purely
which resources the flags say to share (a "process" is `fork`/`clone` without
sharing; a thread is `clone` with `CLONE_VM|CLONE_FILES|...`). A segfault in
one thread raises SIGSEGV on the **process**, so the default action kills the
whole process and every thread with it — thread isolation does not exist, which
is exactly why process isolation is worth its cost. Marks: own/shared split
(0.5), `clone()` (0.25), whole-process death (0.25).

**Q2.** Three reasons: (1) the process **catches SIGTERM** and its handler is
slow, broken, or deliberately ignoring it — `kill -9` **does** help
(SIGKILL is uncatchable); (2) the process is in **`D` state**, uninterruptible
sleep in a kernel I/O path — `kill -9` **does not** help, the signal is only
delivered when the syscall returns, so you must fix the storage/NFS/device;
(3) it is already a **zombie** (`Z`) — it is dead, the entry just hasn't been
reaped by its parent, so no signal helps, you fix or restart the parent.
(Also accepted: PID 1 in a container ignores signals it has no handler for.)
Before `kill -9` on a hung JVM: take a **thread dump** — `kill -3 <pid>` (goes
to stdout) or `jstack <pid>`, plus a heap dump if memory is implicated. Skip it
and the evidence dies with the process: you get a restarted service and no way
to explain the incident, so it recurs. Marks: 0.25 per reason with the correct
verdict, 0.25 for the dump-first discipline.

**Q3.** **VSZ is virtual address space reserved, not memory used.** The JVM
reserves the full heap range plus large mappings for metaspace, code cache,
thread stacks and memory-mapped files up front; Linux **overcommits**, so
untouched pages consume nothing physical. **RSS** — resident set size — is the
real physical memory the process holds, and 1.4 GB on a 4 GB box is fine.
Alert on **RSS** (and against the cgroup limit if containerised); alerting on
VSZ produces permanent false alarms. Marks: overcommit/reserved-vs-resident
(0.5), RSS as the alerting metric (0.5).

**Q4.** The sequence, each step narrowing the space:
1. **`uptime`** (or `top`'s first line) — load average, compared against
   `nproc`. Decision: is the box overloaded at all, and roughly by how much.
   Remember load includes `D`-state tasks, so high load with idle CPU means I/O.
2. **`top`** — the CPU split: `us` (your code), `sy` (kernel/syscalls), `wa`
   (blocked on I/O), `st` (stolen by a noisy neighbour), `id`. Decision: which
   *kind* of problem this is. High `id` with bad latency means you are waiting
   on locks or downstreams, not CPU.
3. **`free -h`** (read the **available** column, not `free` — Linux fills RAM
   with page cache by design) and/or `vmstat 1` for `si`/`so`. Decision: memory
   pressure or swapping.
4. **`ps aux --sort=-%cpu | head`** (or `--sort=-%mem`) — which process.
   Decision: is it our service, and now go per-thread with `top -H -p <pid>`.

Then the question no tool answers: **what changed?** — deploy, config, traffic,
data, infrastructure. Marks: 0.25 each for a sensible ordered narrowing; an
unordered pile of tool names = 0.5 maximum. Accepting `iostat`/`dmesg`/
`journalctl -xe` in place of one of the above is fine if the reasoning is stated.

**Q5.** `wa` at 89% means the CPU is idle **waiting on I/O** — the bottleneck is
storage (or a network filesystem), not compute. Adding threads or CPU will not
help. Next: **`iostat -xz 1`**. The column that is the latency you feel is
**`await`** — average time per I/O request in milliseconds, queueing included.
`%util` near 100 says the device is saturated, and `r/s`+`w/s` tell you whether
it is reads or writes. On cloud storage, high `await` with modest IOPS usually
means **exhausted burst credits / provisioned IOPS**, not a broken disk.
Marks: I/O-bound (0.25), `iostat -xz 1` (0.5), `await` (0.25).

**Q6.** (a) **File descriptors.** Besides regular files: **sockets** (every TCP
connection is an fd — usually the real consumer), pipes, epoll instances,
memory-mapped files, and in a JVM, `inotify` watches. (b)
**`cat /proc/<pid>/limits`** — because the applicable limit is the one in force
**when the process started**, not what `ulimit -n` reports in your current
shell (containers commonly ship 1024). `lsof -p <pid> | wc -l` gives the
current count. (c) A too-low limit shows a count that hits a **flat ceiling**
and stays there; a leak shows a **monotonic rise** over hours that never comes
back down after load drops. `lsof -p <pid>` grouped by type usually names the
leak — a client not being closed, hence also piles of `CLOSE_WAIT` sockets in
`ss -tan`. Marks: fds + sockets (0.25), `/proc/<pid>/limits` (0.5), monotonic
rise vs flat ceiling (0.25).

**Q7.** Most likely: **inodes are exhausted**, not bytes — millions of tiny
files (session files, unrotated logs, cache entries) consume every inode while
leaving space free. Confirm with **`df -i`**. Second case: a **deleted file
still held open** by a running process — the directory entry is gone so `du`
doesn't count it, but the kernel won't free the blocks until the last fd
closes, so `df` still does. Find it with **`lsof +L1`** (files with link count
0), then restart or signal the holder to release it; truncating the file
in place (`: > /proc/<pid>/fd/N`) is the no-restart option. Marks: inodes +
`df -i` (0.5), deleted-but-open + `lsof +L1` (0.5).

**Q8.**
(a) `tail -F /var/log/app.log` — capital **`-F`** follows by name and survives
rotation; lowercase `-f` holds the old inode and goes silent after a rotate.
(b) `jq -r '.path' app.log | sort | uniq -c | sort -rn | head -20` — the
`sort | uniq -c | sort -rn` idiom is the universal "top N by frequency"; with
plain text, `awk '{print $7}'` in place of `jq`.
(c) `zgrep -C 3 'abc-123' app.log app.log.*.gz` — `zgrep` reads both plain and
gzipped files, `-C 3` gives three lines of context each side. (Accepted:
`grep -C 3` for the live file plus `zgrep` for the archive.)
Marks: 1/3 each; `-f` instead of `-F` loses that third.

**Q9.** Six defects:
1. **`FROM openjdk:latest`** — unpinned and unreproducible; a rebuild silently
   changes the JDK. Also `openjdk` is deprecated. Fix: pin a digest or a
   specific tag, e.g. `eclipse-temurin:21-jdk-jammy`.
2. **`COPY . .` before the build** — any source change invalidates the layer, so
   dependencies are re-downloaded on every build. Fix: copy `pom.xml` +
   `mvnw`/`.mvn` first, run `./mvnw dependency:go-offline`, then copy `src`.
3. **`ENV DB_PASSWORD=hunter2`** — a secret baked into an image layer, visible
   to anyone via `docker history` or by inspecting the image; deleting it later
   does not remove it. Fix: inject at runtime from a secrets manager (by ARN in
   ECS, a Secret in K8s), and **rotate this password** — it is compromised.
4. **Single stage** — the final image ships the JDK, Maven, the `.m2` cache and
   your source. Fix: multi-stage, build with the JDK and `COPY --from=build` the
   jar into a JRE base.
5. **Runs as root** — the default. Fix: `RUN useradd -r app` + `USER app`.
6. **Shell-form `CMD`** — `/bin/sh` becomes PID 1 and does not forward SIGTERM
   (see Q11). Fix: exec form, `ENTRYPOINT ["java","-jar","/app/app.jar"]`.
Also acceptable: no `.dockerignore` (ships `.git` and `target/`), no
`HEALTHCHECK`, no `MaxRAMPercentage`.
Marks: 1 for four or more with fixes; 0.5 for two or three; the secret and the
unpinned base must be among them for full marks.

**Q10.** Each instruction that changes the filesystem (`FROM`, `COPY`, `ADD`,
`RUN`) creates a **layer**; the build cache reuses a layer only if that
instruction and all preceding ones are unchanged — so **invalidating one layer
invalidates every layer after it.** Copying source first means every one-line
code change busts the dependency-install layer and re-downloads the world. The
Maven ordering:
```dockerfile
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN ./mvnw -B dependency:go-offline
COPY src src
RUN ./mvnw -B -o package -DskipTests
```
The secret is **not gone**. Layers are additive; `rm` in a later layer writes a
whiteout entry that hides the file, but the bytes remain in the earlier layer
and anyone who pulls the image can extract them. The only fixes are: never add
it (BuildKit `--mount=type=secret`, or runtime injection), rebuild without it,
and **rotate the credential**. Marks: layer definition + cascade (0.25),
correct reordering (0.5), secret-still-there + rotate (0.25).

**Q11.** With shell-form `CMD`, Docker runs `/bin/sh -c "./start.sh"`, so
**`/bin/sh` is PID 1**, and your JVM is a child. On `docker stop` /
`kubectl delete`, the runtime sends **SIGTERM to PID 1 only**. A plain `sh` has
no handler for it and — as PID 1, which has no default signal dispositions —
simply ignores it, and it does not forward the signal to children either. So
nothing shuts down; the runtime waits out its grace period (Docker's default is
exactly **10 s**, Kubernetes' `terminationGracePeriodSeconds` defaults to 30 s —
hence the "exactly 30 seconds") and then **SIGKILLs** everything. The JVM never
runs its shutdown hooks, never drains, and in-flight requests are dropped.
Fixes, best first: **exec form** so the JVM is PID 1 —
`ENTRYPOINT ["java","-jar","app.jar"]`; if you must keep a script, `exec java
-jar app.jar` as its last line so the JVM replaces the shell; or use
`--init`/`tini` as a signal-forwarding, zombie-reaping PID 1.
Marks: PID 1 identified (0.25), SIGTERM ignored/not forwarded → SIGKILL after
the grace period (0.5), exec form or `exec` in the script (0.25).

**Q12.** A container is an ordinary **process on the host kernel**, isolated by
**namespaces** (what it can *see*: PID, network, mount, user, UTS, IPC) and
limited by **cgroups** (what it can *use*: CPU, memory, I/O). It shares the
**host kernel** — which is why you cannot run a Windows container on a Linux
host, and why isolation is weaker than a VM: a kernel vulnerability is a
container-escape path, and a shared kernel is a shared attack surface. Related
practical consequence: a process that isn't cgroup-aware sees the **host's**
CPU count and memory. The real reason teams adopt containers is a
**reproducible, immutable artifact** — the same image runs on a laptop, CI and
production, which kills "works on my machine" — not density or speed.
Marks: namespaces + cgroups named and distinguished (0.5), shared kernel and
its security consequence (0.25), reproducible artifact (0.25).

**Q13.** **Liveness** fails → the kubelet **restarts the container** (same pod,
restart count increments). **Readiness** fails → the pod's IP is **removed from
the Service endpoints**, so it stops receiving traffic; it is not restarted and
recovers on its own when the check passes. **Startup** fails → the container is
restarted, but while it is *pending* it **suspends liveness and readiness
checks** — it exists so slow JVM boots don't get killed by an impatient liveness
probe without needing a huge `initialDelaySeconds`.

The trap: during a 5-minute DB outage, the liveness check fails on **every pod
simultaneously**, so the kubelet restarts the **entire fleet at once** — and
keeps restarting it, because the DB is still down. You have now added a cold
start, an empty cache, a thundering herd of reconnections at the moment the DB
recovers, and zero capacity in the meantime; the pods were perfectly healthy and
would have served cached or degraded traffic. The rule: **liveness checks only
what a restart can fix** — shallow, local, cheap, unauthenticated. Dependency
checks belong in **readiness** at most, and even there you distinguish hard
dependencies from soft ones, or a cache outage takes every endpoint to zero.
Marks: three actions correct (0.5), the fleet-wide restart storm and
"restart can't fix a dependency" (0.5).

**Q14.** (a) **Requests** are the scheduling guarantee — the scheduler places
the pod on a node with that much capacity free, and they are the denominator
for HPA utilisation. **Limits** are the runtime ceiling enforced by cgroups.
(b) Over the **CPU** limit → the container is **throttled**: the kernel's CFS
scheduler stops giving it slices for the rest of the 100 ms period. Latency
spikes, nothing crashes. Over the **memory** limit → **OOMKilled**, exit code
**137**, immediate, no stack trace, no chance to flush anything. The difference
matters because memory is **incompressible**: you can borrow time, you can't
borrow bytes. Hence the standard advice: set memory limit **equal to** request
(Guaranteed QoS), and consider setting CPU requests only, no CPU limit.
(c) Throttling doesn't show up in utilisation graphs because a throttled
container *by definition* isn't using CPU — the graph shows low usage while
latency is terrible. The metric is
**`container_cpu_cfs_throttled_seconds_total`** (and
`..._throttled_periods_total` over `..._periods_total` as a ratio).
Marks: 1/3 each.

**Q15.**
```
kubectl get pods                              # confirm state, restart count
kubectl describe pod <pod>                    # EVENTS first — the answer is usually here
kubectl logs <pod> --previous                 # the CRASHED container's output
kubectl logs <pod> -c <container>             # if multi-container
kubectl get events --sort-by=.lastTimestamp   # cluster-level context
```
`--previous` is the key one: the current container may not have produced output
yet, and the stack trace that matters belongs to the instance that already
died. If the container dies before logging, `kubectl run --rm -it --image=<img>
-- sh` or overriding the command to `sleep 3600` lets you get a shell in the
same image.

Four causes: (1) the app **exits non-zero on startup** — bad config, missing env
var/secret, unreachable dependency at boot; (2) **OOMKilled** — exit 137, seen
in `describe` under Last State; (3) a **failing liveness or startup probe**
killing a container that is actually still booting (wrong port/path, too-short
`initialDelaySeconds`); (4) a **bad image or entrypoint** — missing binary,
wrong architecture, `ImagePullBackOff`'s neighbour. Also accepted: a missing
ConfigMap/Secret mount, or a port already bound.
Marks: `describe` + Events named (0.25), `logs --previous` (0.5), three-plus
distinct causes (0.25).

**Q16.** The race: **endpoint removal and SIGTERM happen concurrently.** When a
pod is marked for deletion, the kubelet sends SIGTERM at the same moment the
endpoints controller starts propagating the removal to kube-proxy on every node,
to the Ingress controller, and to any cloud load balancer. Propagation takes
hundreds of milliseconds to seconds; the SIGTERM takes none. So the app begins
shutting down while traffic is still being routed to it, and those requests are
refused. `maxUnavailable: 0` and a correct readiness probe don't help — they
govern rollout capacity and traffic *admission*, not this teardown window.

Fix: a **`preStop` hook that sleeps** (~5 s), which delays SIGTERM long enough
for deregistration to propagate while the pod keeps serving normally.

Full chain:
1. Pod marked Terminating; endpoint removal begins propagating.
2. `preStop` hook runs (sleep ~5 s) — pod still serving.
3. **SIGTERM** to PID 1.
4. App **stops accepting** new connections/messages, fails readiness.
5. **Drains** in-flight requests to completion.
6. Flushes buffers, commits offsets, **closes pools** and connections.
7. Process exits — all of this inside `terminationGracePeriodSeconds`.
8. If the grace period expires first: **SIGKILL**, and steps 5–6 didn't happen.

Marks: the concurrency race named (0.5), `preStop` sleep (0.25), an ordered
chain with drain-before-close (0.25).

**Q17.** **Logs** = discrete timestamped records of what happened in **one
case**; best at "what exactly went wrong for this request." **Metrics** =
numeric aggregates over time; best at "is this normal, and is it getting
worse." **Traces** = a tree of spans following one request across services;
best at "**where did the time go**, and which hop failed." Workflow:
**a metric alert fires → a trace localises the slow or failing hop → the logs
for that span explain it.** Monitoring answers questions you predicted;
observability lets you answer ones you didn't, without shipping a deploy.

User ids go in logs (and trace attributes) because those systems are built for
high-cardinality identifiers and are queried per-case. They must never go in a
**metric label** because Prometheus creates a **separate time series for every
unique label combination** — one label with a million users is a million series.
That is the cardinality explosion: it exhausts memory on the scrape target and
the TSDB, slows every query, and in hosted systems it is billed per series.
Marks: three definitions with the right question each (0.5), the workflow
(0.25), cardinality explanation (0.25).

**Q18.** (a) An average hides the distribution: if 95% of requests take 50 ms
and 5% take 2 s, the mean is a comfortable 147 ms and one user in twenty is
furious. Averages are also dragged around by outliers and can't show bimodality.
Show **percentiles — p50, p95, p99, p99.9** — and the request rate and error
rate alongside them (RED). (b) **You cannot average percentiles.** A percentile
is a quantile of a distribution, not an additive quantity; the mean of two p99s
is not the p99 of the combined traffic, and it is wrong in a
traffic-weighting-dependent, unbounded way. Instead export **histograms** (bucket
counters), sum the buckets across instances, and compute the quantile from the
merged histogram — that is what `histogram_quantile(0.99, sum(rate(..._bucket[5m]))
by (le))` does. This is also why histograms beat summaries: summaries compute
quantiles per-instance and are therefore un-aggregatable. (c) A widening p50→p99
gap means **queueing or contention**, not a uniformly slower system: most
requests are fine and a tail is waiting behind something — a saturated thread
pool or connection pool, lock contention, GC pauses, or a hot partition. The
p50 tells you the work itself hasn't got slower; the p99 tells you the waiting
has.
Marks: 1/3 each.

**Q19.** (a) Generated **at the edge** — the API gateway, load balancer, or the
first filter in your service — and reused if the incoming request already
carries one (`traceparent`, `X-Request-Id`). Stored in **MDC** (Mapped
Diagnostic Context), so the logging pattern includes it on every line
automatically without threading it through method signatures. Return it in a
response header so users and support can quote it, and propagate it on every
outbound call. Best practice: use the OpenTelemetry **`traceId`** as the
correlation id so logs and traces join on the same key. (b) MDC is backed by a
**`ThreadLocal`**, and in a pooled-thread server the thread outlives the
request: you must **`MDC.clear()` in a `finally`** at the request boundary.
Without it, request B logs under request A's correlation id and user id — wrong
attribution during an incident, and a PII leak across users. (c) It does not
cross **asynchronous boundaries** — `@Async`, an `ExecutorService`, a reactive
scheduler hop — because the work runs on a different thread with a different
ThreadLocal. Add a **`TaskDecorator`** (or `MDC.getCopyOfContextMap()` captured
and restored in the submitted task; Micrometer's context propagation for
reactive). This is the single most common observability gap in a Spring app.
Marks: 1/3 each.

**Q20.** (a) **Alert on symptoms — user-visible impact — not causes.** Wrong
kind: "CPU > 80%", "a pod restarted", "disk 70% full" — none of these are
necessarily hurting anyone, and all of them page someone at 3 a.m. for nothing.
Right kind: error rate above the SLO threshold, p99 latency past the SLO, orders
per minute dropped to zero. (Cause-metrics still belong on dashboards and in
runbooks — just not attached to a pager.) (b) **Page** — real user impact and a
human must act **now**; the test: *is there something a person can do about it
immediately, and does it justify waking them?* If either answer is no it isn't a
page. **Ticket** — real but can wait for business hours. **Dashboard only** —
information, no notification. Every alert must be actionable; alert fatigue is
the main way on-call fails, because the one real page arrives among forty
ignored ones. (c) An **error budget** is the complement of the SLO: at 99.9%
availability you may be unavailable ~43 minutes a month, and that allowance is a
**resource to spend**. It drives a concrete decision: **budget remaining → ship
features; budget exhausted → stop feature work and spend on reliability.** It
also scales alert urgency — **burn-rate alerting** pages on a fast burn
(consuming the month's budget in hours) and files a ticket on a slow one. 100%
is the wrong target because the cost curve is exponential while the user-visible
benefit is nil (their network is less reliable than that), it leaves no budget
for deploys or experiments, and it is unachievable anyway given the
dependencies you don't control.
Marks: 1/3 each.

---

## Section mapping (for the valuation)

| Section | Questions | Topic guide |
|---|---|---|
| 1 Processes, threads, signals | Q1–Q3 | `11-operating-systems-linux.md` |
| 2 Diagnosing a sick box | Q4–Q8 | `11-operating-systems-linux.md` |
| 3 Docker | Q9–Q12 | `19-docker-kubernetes.md` |
| 4 Kubernetes | Q13–Q16 | `19-docker-kubernetes.md` |
| 5 Observability | Q17–Q20 | `20-observability-operations.md` |

Expected range if the UNMEASURED classification is right: **4–8/20.** Section 2
is the one previously measured at zero (E3 Q12) and is pure keyboard practice —
if it scores below 2, the 30-minute terminal drill moves to the top of the study
order. Q9 is a deliberate near-repeat of M2 Q19 (scored 0.5); anything below 1
there means image hygiene needs written material, not just a retest.