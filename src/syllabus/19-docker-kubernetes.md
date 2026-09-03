# Syllabus — 19 Docker & Kubernetes

**Target versions: Kubernetes v1.37 "Garhwal" (released 26 Aug 2026, EOL 28 Oct 2027) and Docker
Engine 29.x, checked 2026-09-03.** Every constant, default, field name, flag and command below is
stated against this set unless a leaf says otherwise. Because most corporate estates run something
older, every leaf that depends on a version boundary names the release that introduced the
behaviour, and the widely-repeated-but-now-stale claims carry `[VERSION-TRAP]`.

| Layer | Release this file targets | Previous generation, also covered |
|---|---|---|
| Kubernetes | **1.37** (26 Aug 2026; 67 enhancements — 16 stable, 23 beta, 27 alpha, 1 deprecation) | **1.33** (Apr 2025), **1.34** (Aug 2025), **1.35** (19 Dec 2025), **1.36** (Apr 2026) — the range EKS/GKE/AKS actually run |
| Docker Engine | **29.x** (29.3.0, 29.7.0 features cited). **containerd image store is the default on new installs**; classic graph drivers (`overlay2`) deprecated | **24.x–28.x** with `overlay2` graph driver — what most CI runners and older hosts still use |
| Docker CLI compose | **Compose v2** (Go, `docker compose`) implementing the **Compose Specification** | `docker-compose` v1 (Python) — **EOL, removed** |
| Builder | **BuildKit** (default since Engine 23) + `docker buildx`, `docker buildx bake` | the legacy builder, `DOCKER_BUILDKIT=0` |
| containerd | **2.2.x** (2.1 made **NRI and CDI default-enabled**, moved CRI image pulls to the transfer service, added parallel range-request layer pulls, OCI image volumes) | 1.6.x / 1.7.x — still shipped by many distros |
| runc | **1.4.x** (OCI runtime-spec 1.2.x conformant; `pids.limit = 0` now means a real limit of zero) | 1.1.x |
| OCI specs | **image-spec 1.1.x** (`subject`, `artifactType`), **distribution-spec 1.1** (Referrers API), **runtime-spec 1.3** (Nov 2025) | image-spec 1.0.x, runtime-spec 1.0.2 |
| Ingress | **Gateway API 1.5** (27 Feb 2026 — biggest release so far; release-train model) and 1.6; `ingress2gateway` 1.0 (Mar 2026) | the `networking.k8s.io/v1` **Ingress** API — frozen but still in core |
| ingress-nginx | **RETIRED 24 Mar 2026** — no features, no bugfixes, **no CVE patches**. `InGate` (its intended successor) was also retired | ingress-nginx 1.x — what almost every existing cluster is still running |
| kube-proxy | **iptables** is still the default in 1.37; **nftables** GA since 1.33; **IPVS deprecated in 1.35** | iptables/IPVS |
| Packaging | **Helm 4.x** (server-side apply for new releases, WASM plugin system, kstatus-based `--wait`), **Kustomize** built into `kubectl` | Helm 3.x with three-way merge |
| Node autoscaling | **Karpenter v1** (`NodePool` + `EC2NodeClass`, `NodeClaim`, disruption budgets) | Cluster Autoscaler with ASGs |
| Service mesh | **Istio ambient mode** (GA since Istio 1.24, 7 Nov 2024): ztunnel + waypoints | sidecar-injection mode |
| cgroups | **cgroup v2 only** in practice: v1 in maintenance mode since **1.31**, kubelet refuses to start without v2 by default from **1.35** | cgroup v1 on RHEL 7/8-era hosts |
| Java runtime for all code | **Java 21 LTS**, Spring Boot 3.x/4.x | — |

**The twenty deltas that most often produce a stale answer in a 2026 container interview**, each
marked `[VERSION-TRAP]` at its leaf:

1. **`ingress-nginx` is dead.** It reached end of life on **24 March 2026** — no features, no
   bugfixes, and critically no CVE patches — and its planned replacement `InGate` was retired too.
   Naming "nginx ingress controller" as the default answer is now naming an unpatched component.
   The `Ingress` *API* remains in core Kubernetes; only the controller project retired.
   `[RESEARCH]`
2. **Gateway API is the successor, and it is GA.** v1.5 (27 Feb 2026) promoted `ListenerSet`,
   `TLSRoute`, the HTTPRoute **CORS filter**, client-certificate validation, certificate selection
   for TLS origination and `ReferenceGrant` to the Standard channel; `BackendTLSPolicy` went
   Standard in v1.4; `GRPCRoute` and the GAMMA mesh bindings are GA. `ingress2gateway` 1.0 converts
   existing Ingress objects. `[RESEARCH]`
3. **Docker no longer stores images in `/var/lib/docker/overlay2` by default.** Engine 29 makes the
   **containerd image store** the default on new installs and deprecates the classic graph drivers.
   Multi-platform images under one tag and attestations work natively as a result. Any answer that
   describes `overlay2` layer directories as *the* mechanism must now say "with the classic graph
   driver". `[RESEARCH]`
4. **nftables is GA and IPVS is deprecated.** nftables mode: alpha 1.29, beta 1.31, **GA 1.33**;
   **IPVS deprecated in 1.35**; iptables is *still* the default in 1.37, with KEP-5343 tracking the
   switch. "iptables or IPVS" is a 2023 answer. nftables needs a **5.13+** kernel. `[RESEARCH]`
5. **You can resize a running pod's CPU and memory without restarting it.** In-place pod resize went
   **GA in 1.35** (19 Dec 2025) via the `pods/resize` subresource, with `resizePolicy` per resource.
   Pod-level in-place vertical scaling went beta in 1.36. "Changing resources always recreates the
   pod" is stale. `[RESEARCH]`
6. **Sidecars are a first-class lifecycle, not a convention.** An `initContainers` entry with
   `restartPolicy: Always` is a native sidecar: started before the app, kept alive for the pod's
   life, torn down after the app exits, and it no longer prevents a `Job` from completing. Beta
   1.29, **GA 1.33**. `[RESEARCH]`
7. **cgroup v1 is effectively gone.** Maintenance mode since **1.31** (KEP-4569); the kubelet
   **refuses to start** without cgroup v2 by default as of **1.35**; KEP-5573 tracks removal. Every
   memory/CPU number in this file is a cgroup **v2** number. `[RESEARCH]`
8. **PodSecurityPolicy does not exist.** Deprecated 1.21, **removed in 1.25**. The mechanism is
   **Pod Security Admission** enforcing the three **Pod Security Standards** profiles
   (`privileged`/`baseline`/`restricted`) in three modes (`enforce`/`audit`/`warn`), set by
   namespace labels.
9. **Requests and limits are no longer only per-container.** `spec.resources` (pod-level
   requests/limits for `cpu`, `memory`, `hugepages-<size>`) is **beta and enabled by default since
   1.34**, gate `PodLevelResources`. `[RESEARCH]`
10. **Docker is not a Kubernetes container runtime.** Dockershim was removed in **1.24**; the
    kubelet speaks **CRI** to containerd or CRI-O. Docker images still run because they are OCI
    images. "Kubernetes runs Docker" is a 2021 answer.
11. **`docker-compose` (v1, Python) is gone.** It is `docker compose` — a Go CLI plugin implementing
    the Compose Specification. Hyphen-vs-space is a real version signal.
12. **The JVM reads cgroup limits by default, and one of the old flags is deleted.**
    `-XX:+UseContainerSupport` is on by default; `-XX:MaxRAMPercentage` **defaults to 25**;
    `-XX:+UseContainerCpuShares` (the flag that restored pre-container `availableProcessors()`
    behaviour) was **removed in JDK 21**. `[RESEARCH]`
13. **User namespaces for pods are GA (1.36).** `spec.hostUsers: false` maps container root to an
    unprivileged host UID. "Container root is host root, and there is nothing you can do" now has a
    supported answer. `[RESEARCH]`
14. **`Endpoints` is deprecated in favour of `EndpointSlice`.** kube-proxy, Gateway
    implementations and the topology/traffic-distribution features all consume EndpointSlices.
    `[RESEARCH]`
15. **HPA can scale to zero.** Scale-to-zero for HPA went **beta in v1.37**; before that only
    KEDA-style external controllers could do it. `[RESEARCH]`
16. **`gitRepo` volumes were removed in 1.36** and **`Service.spec.externalIPs` was deprecated in
    1.36** for security reasons. `[RESEARCH]`
17. **Helm 4 changed the apply model.** New releases default to **server-side apply** (Helm 3
    releases keep client-side after upgrade); conflicts are now hard errors, not silent overwrites;
    `--wait` uses **kstatus** and needs the `watch` verb; post-renderers must be plugins.
    `[RESEARCH]`
18. **Admission policy is now in-tree CEL, not only webhooks.** `ValidatingAdmissionPolicy` GA in
    **1.30**; `MutatingAdmissionPolicy` requires **1.36+**. "Policy means OPA Gatekeeper or Kyverno"
    is incomplete. `[RESEARCH]`
19. **`kubectl` has a new output format.** **KYAML** (`-o kyaml`) reached beta in 1.35 — an
    opinionated, unambiguous YAML dialect. And Service *name* validation was relaxed in 1.35 to
    allow leading digits. `[RESEARCH]`
20. **OCI images can carry non-image payloads and be referenced as volumes.** image-spec 1.1's
    `subject`/`artifactType` plus the distribution-spec **Referrers API** are how signatures, SBOMs
    and attestations attach to a digest; **OCI images and artifacts as Kubernetes volume sources**
    went **stable in 1.36**. `[RESEARCH]`

**Scope boundary against the sibling guides.** This file owns **the container as a mechanism and the
orchestrator as a mechanism**: which kernel features make a container, how an image is built stored
and moved, what every Kubernetes object actually does at runtime, and every way the pair fails.
Owned elsewhere:

- EC2/S3/RDS/SQS/Lambda primitives, IAM policy evaluation, VPC/subnet/route-table design, ALB/NLB
  provisioning, cost modelling and IaC live in `18-cloud-aws.md`. This guide owns EKS/ECS/Fargate
  only as *orchestrator* choices, IRSA/Pod Identity only as the pod-identity mechanism, and the
  cloud load balancer only as the thing a Service or Gateway provisions. `[X-REF 18]`
- Terraform's state file, plan/apply graph, locking and drift live in `23-terraform.md`. This guide
  owns cluster and manifest lifecycle, not the IaC runtime. `[X-REF 23]`
- Processes, threads, scheduling classes, virtual memory and paging, file descriptors, signals, the
  OOM killer as a kernel subsystem, and `top`/`ps`/`lsof`/`ss`/`strace`/`dmesg` live in
  `11-operating-systems-linux.md`. This guide owns namespaces, cgroups, OverlayFS and the
  container-shaped view of all of it. `[X-REF 11]`
- Heap regions, G1/ZGC behaviour, humongous allocation, the OOM taxonomy, heap dumps, `jcmd`/`jstack`
  and JIT warmup live in `06-jvm-internals.md`. This guide owns the JVM-inside-a-cgroup arithmetic
  and the container-aware flags. `[X-REF 06]`
- TCP/IP, TLS handshakes, HTTP/1.1 vs 2 vs 3, DNS as a protocol, keep-alive, connection pooling,
  timeouts and retries live in `10-networking.md`. This guide owns pod networking, Service VIPs,
  cluster DNS and the L7 routing objects. `[X-REF 10]`
- Thread pools, `availableProcessors()`-driven sizing, virtual threads, and graceful-shutdown
  concurrency live in `05-multithreading-concurrency.md` and `04-modern-java.md`. This guide owns
  what the cgroup does to those defaults. `[X-REF 05]` `[X-REF 04]`
- Metrics, logs, traces, Micrometer/Prometheus wiring, SLI/SLO, alert design, incident command and
  postmortems live in `20-observability-operations.md`. This guide owns which container/cluster
  signals exist, what a bad value looks like, and the debugging commands. `[X-REF 20]`
- OWASP, authn/authz for *end users*, sessions vs JWT, TLS configuration and secrets *storage*
  design live in `13-web-security.md`. This guide owns the container security boundary, RBAC for
  *workloads*, Pod Security Standards, network policy and image supply chain. `[X-REF 13]`
- Testcontainers mechanics, test slices, flakiness and contract testing live in `16-testing.md`.
  This guide owns Testcontainers only as a consumer of the Docker API and the CI cost model.
  `[X-REF 16]`
- Kafka/RabbitMQ semantics, consumer groups, DLQs and outbox live in `14-messaging-queues.md`. This
  guide owns consumer-lag-driven autoscaling as a mechanism. `[X-REF 14]`
- Redis/ElastiCache mechanics and readiness-gated warm-up live in `15-caching.md`. `[X-REF 15]`
- Connection pools against a shared database, replica lag and partitioning live in
  `09-sql-databases.md` and `22-system-design.md`. This guide owns "more pods does not mean more
  database". `[X-REF 09]` `[X-REF 22]`
- CI runners, build reproducibility, `fetch-depth`, hooks and the review gate live in
  `17-git-craft.md`. This guide owns the image build inside that pipeline. `[X-REF 17]`
- "Design a container orchestrator" as an interview prompt lives in `22-system-design.md`; this
  guide owns Kubernetes' own design decisions as the worked example. `[X-REF 22]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in **one paragraph** before pointing away — it never sends the reader off empty-handed.

**Every example, service name, image name, namespace, manifest and incident in the bible comes from
the QuizStakes domain in `src/scenario/scenario.md`.** Images are named for the services —
`quizstakes/application-gateway`, `quizstakes/router-int`, `quizstakes/jwt-service`,
`quizstakes/client-restrictions`, `quizstakes/funds-ledger`, `quizstakes/payment-service`,
`quizstakes/card-payments`, `quizstakes/bank-deposits`, `quizstakes/bank-withdrawal`,
`quizstakes/document-verification`, `quizstakes/screening-service`, `quizstakes/account-opening`,
`quizstakes/account-activation`, `quizstakes/account-maintenance`, `quizstakes/bonus-service`,
`quizstakes/balance-view`, `quizstakes/profile-service`, `quizstakes/pending-actions`,
`quizstakes/notification-service`, `quizstakes/internal-platforms`, `quizstakes/application-history`,
`quizstakes/personal-details`, `quizstakes/client-agreements`, `quizstakes/assessment-service`,
`quizstakes/document-requirements`. Namespaces are `quizstakes-money`, `quizstakes-onboarding`,
`quizstakes-ops`. Status codes are the real ones (`AO-400`, `AA-610`, `AA-801`, `DEP-301`,
`DEP-400`). **The current guide uses `myapp`, `api`, `app.jar`, `payments`, `billing`,
`myrepo/myapp:1.4.2`, `myns` and `api-7d9f-x2k4`; every one of those must be re-domained by the
write pass.**

**Domain facts the bible's examples must be consistent with** (scenario Appendix A and B): 2.4M
registered clients; 380k monthly active; **14k concurrent sessions, 55k peak**; 12k registrations/day
(40k on campaign launch); 7.2k applications reaching `AO-400`/day, 24k peak; 95k card deposits/day at
**40/sec**; **2.8M stake reservations/day at 1,200/sec**; 2.8M settlements/day with **3,400/sec**
bursts; 19.8M ledger entries/day at **230 writes/sec sustained and 13,600/sec peak**; 24k document
uploads/day at **2–6 MB each**; a **30 ms** restriction-decision budget, an 80 ms balance-read
budget, a **150 ms** stake-reservation budget, a **4 s** card-deposit budget, a **90 s** async
document-verification budget and a **hard 500 ms** self-exclusion budget. The deployment shapes are
Appendix B verbatim: `ApplicationGateway` **2 GB heap, 12 → 40 instances**, stateless and
autoscaled; `ClientRestrictions` **4 GB heap × 8**, aggressively autoscaled, 30 ms on every money
path; `DocumentVerification` **8 GB heap × 6** with 2–6 MB humongous buffers;
`FundsLedger` **12 GB heap × 3**, partition-affine by client id, **explicitly not** function-based
because a cold connection pool and lost index locality cost more than elasticity;
`BankDeposits` **6 GB × 2**, bursty then idle 23 hours; `BankWithdrawal` **6 GB × 2** with a
**scheduled run job and a single leader — it must not run twice**; `PaymentService` **4 GB × 8**;
`InternalPlatforms` **4 GB × 3**, session-affine; `RouterInt` as a **sidecar or dedicated HAProxy
tier**. Deployment policy is Appendix B.4: **rolling, with drain-before-terminate on the payment
run**; scheduled work is **a central scheduler plus leader election, never per-instance cron**;
configuration is **versioned and promoted, never edited in place**; service identity is **workload
identity with short-lived credentials and mutual TLS**. **Invariant 8 — self-exclusion takes effect
before the next stake** — is the constraint that makes a sloppy rollout a regulatory breach rather
than a blip.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real spec text, official documentation, or Kubernetes/containerd/runc source (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic Java 21 code, or a complete runnable script / manifest |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in K8s 1.37 / Engine 29 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number / byte arithmetic explicitly |
| `[CFG]` | must give the exact field path or config key and its default value |
| `[CMD]` | must give the exact command line, copy-pasteable |
| `[YAML]` | must give the complete manifest, not a fragment |
| `[KEP]` | must cite the KEP number and the alpha/beta/GA release for the feature |
| `[DIAG]` | a named failure mode: symptom → the command that confirms it → cause → fix |

---

# PART 1 — BASICS

## §1.1 Why containers exist at all, and what they decided differently

1.1.1 The 2013 problem statement: deploying an application meant reproducing an environment — JDK
      version, native libraries, locale, file layout, `/etc` contents — by hand or by configuration
      management, and every environment drifted. "Works on my machine" was a class of defect, not a
      joke.
1.1.2 The three prior answers and why each fell short: a shared host with hand-managed
      dependencies (drift, conflicting versions); configuration management (Chef/Puppet/Ansible —
      convergent, not identical, and slow); a full VM image per service (correct, but gigabytes and
      minutes). `[RESEARCH]`
1.1.3 The container's central decision: **ship the filesystem, share the kernel**. Dependencies,
      runtime and layout travel with the artefact; the kernel does not.
1.1.4 The second decision: **the artefact is immutable and content-addressed**. An image digest
      names exactly one byte sequence, so "what is running" is answerable and "the same thing runs
      in CI and prod" is checkable, not hoped for. `[PROVE]`
1.1.5 The third decision: **the isolation is assembled from pre-existing kernel features**, not a
      new subsystem. Namespaces (1991 Plan 9 lineage; Linux mount namespaces 2002, the rest through
      2013), cgroups (Google, merged 2007), capabilities, seccomp, LSMs. Docker invented the
      packaging and the UX, not the isolation. `[RESEARCH]`
1.1.6 What containers actually give you, in priority order: a reproducible artefact; a uniform
      deployment interface across wildly different services; fast start-up enabling elasticity and
      cheap rollback; density. **Efficiency is fourth, not first** — the current guide is right
      about this and the bible must keep the framing.
1.1.7 The cost of these decisions: a weaker isolation boundary than a VM; a shared-kernel
      constraint on OS choice; a build system whose caching semantics you must learn; an ecosystem
      that grew a hundred moving parts; and a whole new class of "my process cannot see its own
      limits" bugs (§2.8).
1.1.8 Why an *orchestrator* became inevitable the moment containers worked: an immutable artefact
      that starts in milliseconds makes "put N copies somewhere healthy, keep them there, and route
      to them" the actual problem. Forward to §1.17.
1.1.9 The standardisation that made the ecosystem possible: Docker donated `libcontainer` as
      **runc** and the image format as the **OCI Image Specification** (June 2015, OCI founded under
      the Linux Foundation), so an "image" and a "container" are now specs, not one vendor's
      product. `[RESEARCH]`
1.1.10 The vocabulary to get right on day one and never confuse again: **image** (build artefact),
       **container** (a running process tree from an image), **registry** (where images live),
       **repository** (a named set of tags in a registry), **tag** (a mutable pointer), **digest**
       (an immutable content address), **runtime** (what starts the process), **orchestrator**
       (what decides where and how many).
1.1.11 The interview framing this guide serves: turning "I write Dockerfiles and `kubectl apply`"
       into "I can say which kernel feature enforces this limit, why my p99 has 90 ms holes in it,
       and what happens between `kubectl apply` and a running process."

*(11 leaves)*

## §1.2 Namespaces — isolation of what a process can see

1.2.1 The model: a namespace is a **kernel-maintained scope for one class of global resource**. A
      process sees the instance of that resource belonging to its namespace, and cannot name the
      others.
1.2.2 The complete list, with the `clone(2)` flag and what it scopes: **mount** (`CLONE_NEWNS`,
      2002, Linux 2.4.19) — the mount table; **UTS** (`CLONE_NEWUTS`) — hostname and domainname;
      **IPC** (`CLONE_NEWIPC`) — System V IPC objects and POSIX message queues; **PID**
      (`CLONE_NEWPID`) — the process ID number space; **network** (`CLONE_NEWNET`) — interfaces,
      routes, iptables/nftables rules, sockets, **and the port space**; **user**
      (`CLONE_NEWUSER`, 3.8) — UID/GID mappings and capabilities; **cgroup** (`CLONE_NEWCGROUP`,
      4.6) — the cgroup root a process sees; **time** (`CLONE_NEWTIME`, 5.6) — `CLOCK_MONOTONIC`
      and `CLOCK_BOOTTIME` offsets. `[NUM]` `[SOURCE]`
1.2.3 What is *not* namespaced, and therefore shared with the host: the kernel itself and its
      version; loaded modules; most `sysctl`s; the clock (except the two offsets above); the
      scheduler; `/dev` device nodes unless remapped; kernel keyrings (partly); and CPU/memory
      *capacity* — that is cgroups' job, not namespaces'. `[TRAP]`
1.2.4 Why the network namespace is why two containers can both bind 8080, and why `-p 8080:8080`
      is needed to reach either from outside. `[PROVE]`
1.2.5 Why the PID namespace makes your process PID 1, and the consequences: no default signal
      handlers, no orphan reaping, and `kill -9 1` from inside is a no-op. Forward to §1.11.
1.2.6 Why the mount namespace plus `pivot_root(2)` — **not** `chroot(2)` — is how a container gets
      its own root filesystem, and why runc deliberately prefers `pivot_root` (chroot is escapable
      from a process holding a descriptor to a directory outside it). `[PROVE]` `[SOURCE]`
1.2.7 The user namespace as the one that changes the security posture: UID 0 inside maps to an
      unprivileged UID outside, so container root is not host root. Why it was slow to adopt (file
      ownership on shared volumes, `newuidmap`/`newgidmap`, storage driver support).
1.2.8 Kubernetes exposure of it: `spec.hostUsers: false`, **GA in 1.36**, per-pod ID-range
      allocation by the kubelet. `[KEP]` `[VERSION-TRAP]` `[RESEARCH]`
1.2.9 The cgroup namespace's job: without it, `/proc/self/cgroup` inside the container leaks the
      host's full cgroup path, telling the workload where it sits in the host hierarchy — and
      breaking naive cgroup-limit readers.
1.2.10 Namespace lifetime: a namespace exists while a process or a bind mount references it, which
       is what `/proc/<pid>/ns/*` and `ip netns` exploit. `nsenter` and `setns(2)` are how you
       enter one — the mechanism behind `docker exec` and `kubectl debug`. `[CMD]`
1.2.11 Shared namespaces are the whole basis of the **Pod**: containers in a pod share network,
       IPC and UTS, and optionally PID (`shareProcessNamespace: true`), but each keeps its own
       mount namespace. Forward to §1.21. `[CFG]`
1.2.12 The commands to see all of this on a real host: `lsns`, `ls -l /proc/<pid>/ns/`,
       `unshare --pid --fork --mount-proc bash`, `nsenter -t <pid> -n ip addr`. `[CMD]`
1.2.13 **Trap:** believing namespaces are a security boundary on their own. They isolate *naming*;
       they do not stop a kernel exploit, and without user namespaces the container's root is the
       host's root. `[TRAP]`

*(13 leaves)*

## §1.3 cgroups — limitation of what a process can use

1.3.1 The model: a cgroup is a node in a tree of processes to which **controllers** attach limits
      and accounting. Namespaces answer "what can I see"; cgroups answer "how much can I use".
1.3.2 cgroup **v1**: one hierarchy per controller, mounted under `/sys/fs/cgroup/<controller>/`,
      each with its own tree — which made coherent policy across CPU and memory impossible and
      produced the notorious `memory.limit_in_bytes` / `cpu.cfs_quota_us` split.
1.3.3 cgroup **v2** (unified hierarchy, Linux 4.5+): one tree at `/sys/fs/cgroup`, controllers
      enabled per-subtree via `cgroup.subtree_control`, and the **no-internal-process** rule.
      `[SOURCE]`
1.3.4 The v2 controller inventory: `cpu`, `cpuset`, `memory`, `io`, `pids`, `hugetlb`, `rdma`,
      `misc`. Name each and say what a container platform uses it for.
1.3.5 The v2 interface files that matter, by exact name and unit: `cpu.max` (`"$QUOTA $PERIOD"` in
      µs, default `"max 100000"`), `cpu.weight` (1–10000, default 100), `cpu.stat`
      (`nr_periods`, `nr_throttled`, `throttled_usec`), `cpu.pressure`; `memory.max`,
      `memory.high`, `memory.low`, `memory.min`, `memory.current`, `memory.swap.max`,
      `memory.events` (`low`/`high`/`max`/`oom`/`oom_kill`), `memory.stat`, `memory.pressure`;
      `pids.max`, `pids.current`; `io.max`, `io.stat`. `[NUM]` `[CFG]` `[SOURCE]`
1.3.6 The v1 → v2 name mapping table every older blog post forces you to translate:
      `cpu.cfs_quota_us`/`cpu.cfs_period_us` → `cpu.max`; `cpu.shares` → `cpu.weight` (and the
      conversion formula); `memory.limit_in_bytes` → `memory.max`;
      `memory.soft_limit_in_bytes` → `memory.high` (with different semantics!);
      `memory.usage_in_bytes` → `memory.current`. `[NUM]` `[TRAP]`
1.3.7 **`memory.high` is not `memory.max`.** `high` throttles reclaim and stalls the workload;
      `max` triggers the cgroup OOM killer. Kubernetes MemoryQoS uses `high`; the limit is `max`.
      `[PROVE]` `[TRAP]`
1.3.8 `cpu.weight` is *proportional and only matters under contention*; `cpu.max` is *absolute and
      applies even on an idle machine*. This one sentence explains most of §2.8's pathology.
      `[PROVE]`
1.3.9 How a request maps to a weight: Kubernetes converts `requests.cpu` into `cpu.weight`
      (formerly `cpu.shares`, 1024 shares per core) and `limits.cpu` into `cpu.max` quota. State
      the arithmetic. `[NUM]` `[PROVE]`
1.3.10 The **cgroup driver** question: `systemd` vs `cgroupfs`. Why the kubelet and the container
       runtime must agree, what happens when they disagree (two writers, drifting limits, pods that
       are never limited), and that containerd 2.0+ can autodetect and configure it. `[CFG]`
       `[TRAP]` `[RESEARCH]`
1.3.11 The cgroup tree a Kubernetes node actually has: `kubepods.slice` →
       `kubepods-besteffort.slice` / `kubepods-burstable.slice` / (Guaranteed pods directly under
       `kubepods.slice`) → `kubepods-*-pod<uid>.slice` → `cri-containerd-<id>.scope`. Plus
       `system.slice` and the kubelet's own `--kube-reserved` / `--system-reserved` /
       `--enforce-node-allocatable` slices. `[SOURCE]` `[NUM]`
1.3.12 Node **Allocatable** arithmetic: `capacity − kube-reserved − system-reserved −
       eviction-hard = allocatable`, and allocatable is what the scheduler bin-packs against. Work
       a real example on a 4 vCPU / 16 GiB node. `[NUM]` `[PROVE]`
1.3.13 PSI (Pressure Stall Information): `cpu.pressure`, `memory.pressure`, `io.pressure` with
       `some`/`full` averages. **PSI metrics for Kubernetes went GA in 1.36** — the first
       first-class "is this container actually starved" signal. `[KEP]` `[RESEARCH]`
1.3.14 `hugetlb` and why `hugepages-2Mi`/`hugepages-1Gi` **cannot be overcommitted** while CPU and
       memory can. `[CFG]`
1.3.15 The commands: `systemd-cgls`, `systemd-cgtop`, `cat /sys/fs/cgroup/<path>/cpu.stat`,
       `cat /proc/self/cgroup`, `stat -fc %T /sys/fs/cgroup` (to prove you are on v2). `[CMD]`
1.3.16 **Trap:** thinking `cpu: "500m"` means "half a core, continuously". It means 50 ms of CPU
       per 100 ms period summed across all threads. Full treatment in §3.3. `[TRAP]`

*(16 leaves)*

## §1.4 The other kernel primitives a container is made of

1.4.1 **Capabilities**: root's powers split into ~40 bits. The default Docker/containerd set
      (`CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `FSETID`, `KILL`, `SETGID`, `SETUID`, `SETPCAP`,
      `NET_BIND_SERVICE`, `NET_RAW`, `SYS_CHROOT`, `MKNOD`, `AUDIT_WRITE`, `SETFCAP`) and the
      capability sets (permitted, effective, inheritable, bounding, ambient). `[NUM]` `[SOURCE]`
1.4.2 The ones you must be able to name as dangerous and why: `SYS_ADMIN` (mount, effectively
      root), `NET_ADMIN`, `SYS_PTRACE`, `SYS_MODULE`, `DAC_READ_SEARCH`, `BPF`, `PERFMON`,
      `NET_RAW` (ARP/DNS spoofing inside the pod network).
1.4.3 `--privileged` decoded precisely: all capabilities, all devices in `/dev`, no seccomp
      profile, no AppArmor, unmasked `/proc` and `/sys`. It is not "a bit more access", it is "the
      isolation is off". `[PROVE]` `[TRAP]`
1.4.4 `--cap-drop=ALL --cap-add=NET_BIND_SERVICE` as the pattern, and the Kubernetes spelling
      `securityContext.capabilities.drop: ["ALL"]`. `[CFG]`
1.4.5 **seccomp**: syscall filtering via BPF. The `RuntimeDefault` profile blocks ~44 syscalls of
      ~300+; `Unconfined`; `Localhost` with a profile file. Kubernetes made `RuntimeDefault` the
      default for new pods via `SeccompDefault` (beta 1.25, GA 1.27). `[NUM]` `[CFG]` `[RESEARCH]`
1.4.6 **AppArmor / SELinux** as the LSM layer: `securityContext.appArmorProfile.type`
      (`RuntimeDefault`/`Localhost`/`Unconfined`, the field GA in 1.31 replacing the
      `container.apparmor.security.beta.kubernetes.io/*` annotation) and
      `seLinuxOptions.{user,role,type,level}` with the allowed types `container_t`,
      `container_init_t`, `container_kvm_t`, `container_engine_t`. `[CFG]` `[RESEARCH]`
1.4.7 **`no_new_privs`** and `allowPrivilegeEscalation: false`: what it actually blocks (setuid
      binaries and file capabilities gaining privilege on `execve`) and why the Restricted profile
      requires it. `[PROVE]`
1.4.8 **`pivot_root`, `MS_PRIVATE` mount propagation, and the masked paths**: `/proc/kcore`,
      `/proc/keys`, `/proc/timer_list`, `/sys/firmware` masked; `/proc/asound`, `/proc/bus`,
      `/proc/fs`, `/proc/irq`, `/proc/sys`, `/proc/sysrq-trigger` read-only. Name them; they are
      the reason `--privileged` is a boundary removal. `[SOURCE]`
1.4.9 **rlimits** (`RLIMIT_NOFILE`, `RLIMIT_NPROC`) and why they are per-process while `pids.max`
      is per-cgroup — the two ways a fork bomb is contained, only one of which works.
1.4.10 **OOM score adjustment**: `oom_score_adj` per container, and the values Kubernetes sets per
       QoS class: Guaranteed **−997**, BestEffort **1000**, Burstable
       `min(max(2, 1000 − 1000×memoryRequest/machineCapacity), 999)`. `[NUM]` `[SOURCE]`
1.4.11 **Read-only root filesystem** (`readOnlyRootFilesystem: true`) plus `emptyDir` for `/tmp`,
       and why a JVM needs a writable `/tmp` (hsperfdata, `java.io.tmpdir`, JFR dumps) — the
       specific reason this setting breaks Java apps that nobody warns you about. `[TRAP]`
1.4.12 **Device access**: `--device`, `devices.allow`, the **Container Device Interface (CDI)** —
       default-enabled in containerd 2.1 — and the **Node Resource Interface (NRI)**, also
       default-enabled in 2.1. `[RESEARCH]`
1.4.13 The stronger sandboxes and when they earn their cost: **gVisor** (userspace kernel,
       syscall interception), **Kata Containers** (a real VM per pod), **Firecracker** microVMs
       (Lambda, Fargate). Kubernetes exposes them through `RuntimeClass`. `[CFG]`

*(13 leaves)*

## §1.5 Images: the OCI model

1.5.1 An "image" is three kinds of object in a registry: an **index** (manifest list), one or more
      **manifests**, and the **blobs** they point at (config JSON + layer tarballs).
1.5.2 The **descriptor** — the universal pointer: `mediaType`, `digest`, `size`, and optionally
      `urls`, `annotations`, `data`, `artifactType`, `platform`. Every reference in the whole spec
      is a descriptor. `[SOURCE]`
1.5.3 The **image manifest** fields, exactly: `schemaVersion` (MUST be `2`), `mediaType`
      (`application/vnd.oci.image.manifest.v1+json`), `artifactType` (optional; required when
      `config.mediaType` is empty), `config` (descriptor to
      `application/vnd.oci.image.config.v1+json`), `layers` (ordered array of descriptors),
      `subject` (descriptor to another manifest), `annotations`. `[SOURCE]` `[NUM]`
1.5.4 The layer media types: `application/vnd.oci.image.layer.v1.tar`, `…tar+gzip`,
      `…tar+zstd` (recommended support), and the deprecated `…nondistributable.v1.tar[+gzip]`.
      Plus the Docker Schema 2 equivalents
      (`application/vnd.docker.image.rootfs.diff.tar.gzip`,
      `application/vnd.docker.distribution.manifest.v2+json`) you will actually see in `crane`
      output. `[SOURCE]`
1.5.5 The **image index**: `manifests[]` each with a `platform` block (`architecture`, `os`,
      `os.version`, `os.features`, `variant`) — this is how one tag serves `linux/amd64` and
      `linux/arm64`. `[SOURCE]`
1.5.6 The **image config** JSON: `architecture`, `os`, `config` (`User`, `ExposedPorts`, `Env`,
      `Entrypoint`, `Cmd`, `Volumes`, `WorkingDir`, `Labels`, `StopSignal`), `rootfs`
      (`type: "layers"`, `diff_ids[]`), `history[]`. **`diff_ids` are digests of the
      *uncompressed* tar; layer descriptors are digests of the *compressed* blob** — two different
      hashes for the same layer, and the source of endless confusion. `[PROVE]` `[TRAP]` `[NUM]`
1.5.7 **The image ID is the digest of the config JSON**, not of the manifest. The manifest digest
      is what a registry reference `@sha256:…` names. `docker images` shows the former;
      `kubectl describe pod` records the latter. `[PROVE]` `[TRAP]` `[NUM]`
1.5.8 The layer tar format: whiteout entries `.wh.<name>` and the opaque marker
      `.wh..wh..opq`, hardlink handling, and why `tar` metadata (mtimes, ownership, ordering)
      determines reproducibility. `[SOURCE]`
1.5.9 `artifactType` + `subject` + the **Referrers API** (`GET /v2/<name>/referrers/<digest>`,
      distribution-spec 1.1) as the mechanism for attaching signatures, SBOMs, provenance and
      scan results to an image digest, with `artifactType` filtering and pagination. `[SOURCE]`
      `[RESEARCH]`
1.5.10 Annotation keys worth setting, from the pre-defined set: `org.opencontainers.image.created`,
       `.revision`, `.source`, `.version`, `.title`, `.description`, `.licenses`,
       `.base.name`, `.base.digest`. These are how an incident responder gets from a running
       container to a commit. `[CFG]`
1.5.11 The tooling that reads all of this without a daemon: `crane manifest`, `crane config`,
       `crane digest`, `skopeo inspect --raw`, `oras discover`, `docker buildx imagetools inspect`.
       `[CMD]`
1.5.12 **OCI images as Kubernetes volumes** — `volumes[].image` — **stable in 1.36**, and why it
       matters for shipping large read-only datasets (agreement-document bundles, ML models)
       separately from the app image. `[KEP]` `[RESEARCH]`
1.5.13 Where the *container* fits: an OCI **runtime** bundle is a directory with a `config.json`
       (runtime-spec) and a `rootfs/`. The image is converted to a bundle before anything runs.
       Forward to §3.9. `[SOURCE]`

*(13 leaves)*

## §1.6 Layers, the union filesystem, and the writable layer

1.6.1 A layer is a **content-addressed filesystem diff**, not a snapshot. The image's root
      filesystem is the ordered application of every layer diff.
1.6.2 Layers are **immutable and shared by digest**: twenty images built
      `FROM eclipse-temurin:21-jre-jammy` store that base once per node. Compute the disk saving on
      the QuizStakes estate. `[NUM]` `[PROVE]`
1.6.3 The union mount: `lowerdir` (the read-only image layers, colon-separated, most-recent
      first), `upperdir` (the container's writable layer), `workdir` (OverlayFS scratch), and
      `merged` (what the process sees). Full internals in §3.5. `[SOURCE]`
1.6.4 **Copy-up**: the first write to a file that lives in a lower layer copies the **whole file**
      up, because OverlayFS works at file granularity, not block granularity. Consequence: the
      first write to a 900 MB agreement-document bundle costs 900 MB of I/O and disk. `[PROVE]`
      `[NUM]` `[TRAP]`
1.6.5 **Deletion in a later layer does not shrink the image** — it writes a whiteout. The bytes
      remain in the earlier layer and are extractable with `docker save` / `crane export`. The
      security consequence: a secret `COPY`d then `rm`'d is still in the image. `[PROVE]` `[TRAP]`
1.6.6 The writable layer is **ephemeral**: it dies with the container. Anything that must survive
      goes in a volume. And writing to it counts against `ephemeral-storage`, which can get your
      pod evicted (§2.12).
1.6.7 Page-cache sharing: multiple containers reading the same file from the same lower layer
      share a single page-cache entry — the reason container density is memory-cheap. `[PROVE]`
1.6.8 Layer count limits and costs: `overlay2` supports up to **128 lower layers**; deep stacks
      slow path lookup because every `stat` walks the stack. `[NUM]` `[RESEARCH]`
1.6.9 The storage drivers, named and positioned: `overlay2` (the standard; **deprecated in Engine
      29** in favour of the containerd snapshotter), `fuse-overlayfs` (rootless), `btrfs`, `zfs`,
      `devicemapper` (removed), `vfs` (no CoW, full copy per layer — testing only), and
      containerd's **snapshotter** plugin model. `[VERSION-TRAP]` `[RESEARCH]`
1.6.10 **The containerd image store as the new default (Engine 29)**: what changes for the user —
       multi-platform images under one tag, attestation storage, `docker image ls` semantics — and
       what breaks (`docker save`/`load` behaviour, tooling that reads
       `/var/lib/docker/overlay2` directly). `[VERSION-TRAP]` `[RESEARCH]`
1.6.11 How to see per-layer sizes and find the bloat: `docker history --no-trunc`, `dive`,
       `crane manifest | jq '.layers[].size'`, `docker system df -v`. `[CMD]`
1.6.12 Lazy-pulling futures worth naming: **eStargz**, **SOCI**, **Nydus** — start the container
       before the whole layer arrives, which matters when a 900 MB image blocks a scale-out during
       a 40k-registration campaign launch. `[RESEARCH]`

*(12 leaves)*

## §1.7 The Dockerfile instruction set, complete

1.7.1 `# syntax=docker/dockerfile:1` — the frontend directive that opts into current Dockerfile
      features independent of the engine version, and the other parser directives
      (`escape`, `check`). `[CFG]`
1.7.2 `FROM <image>[:tag|@digest] [AS name]`, `FROM scratch`, multiple `FROM`s for multi-stage,
      and `--platform=$BUILDPLATFORM`/`$TARGETPLATFORM`.
1.7.3 The automatic platform ARGs: `TARGETPLATFORM`, `TARGETOS`, `TARGETARCH`, `TARGETVARIANT`,
      `BUILDPLATFORM`, `BUILDOS`, `BUILDARCH`, `BUILDVARIANT`. `[CFG]`
1.7.4 `RUN` — shell form vs exec form; `RUN --mount=type=cache,target=…[,sharing=locked|shared|private,id=…]`;
      `--mount=type=bind,from=…,source=…,target=…`; `--mount=type=secret,id=…,target=…,required`;
      `--mount=type=ssh`; `--mount=type=tmpfs`; `--network=none|host`; `--security=insecure`.
      `[CFG]` `[SOURCE]`
1.7.5 `COPY` vs `ADD`: `COPY --from=<stage|image>`, `--chown`, `--chmod`, `--link` (the
      cache-friendly one nobody uses), `--parents`, `--exclude`; `ADD`'s extra powers (remote URLs,
      automatic tar extraction, `--checksum`, `--keep-git-dir` for Git refs) and why "prefer COPY"
      is the rule. `[CFG]` `[TRAP]`
1.7.6 `WORKDIR`, and why a relative `WORKDIR` compounds across instructions.
1.7.7 `ENV` vs `ARG`: build-time vs run-time, scope rules (an `ARG` before the first `FROM` is
      global; one inside a stage is stage-scoped), the pre-defined proxy ARGs, `ARG` with a default,
      and **both are visible in image metadata**. `[TRAP]` `[CFG]`
1.7.8 `ENTRYPOINT` and `CMD` — the full 3×3 interaction table (neither/`CMD` only/`ENTRYPOINT`
      only/both, in shell or exec form) and exactly what process ends up as PID 1 in each cell.
      `[PROVE]`
1.7.9 `EXPOSE` is **documentation plus a hint** — it publishes nothing. `-P` uses it; `-p` does
      not need it; Kubernetes ignores it entirely except as `containerPort` documentation. `[TRAP]`
1.7.10 `USER <uid>[:<gid>]` — why a numeric UID (not a name) is required for the Restricted PSS
       profile and for `runAsNonRoot` validation to work without a passwd lookup. `[TRAP]` `[CFG]`
1.7.11 `VOLUME` — what declaring it actually does (anonymous volume on run, and it *silently
       discards* later writes to that path in the image build), and why most people should not use
       it. `[TRAP]`
1.7.12 `HEALTHCHECK [--interval=30s --timeout=30s --start-period=0s --start-interval=5s
       --retries=3]` with its exact defaults; and that **Kubernetes ignores it** in favour of
       probes. `[NUM]` `[CFG]` `[VERSION-TRAP]`
1.7.13 `LABEL`, and the OCI annotation keys from §1.5.10 as the labels worth standardising.
1.7.14 `STOPSIGNAL` — how to make `SIGQUIT`-shutdown runtimes behave, and its Kubernetes analogue
       (there isn't one: Kubernetes always sends SIGTERM). `[TRAP]`
1.7.15 `SHELL` — changing the shell form's interpreter, and the `SHELL ["/bin/bash", "-eo",
       "pipefail", "-c"]` idiom that turns silent pipeline failures into build failures. `[CMD]`
1.7.16 `ONBUILD` — deferred instructions in a base image, why it exists and why it surprises.
1.7.17 `.dockerignore` — syntax (glob, `!` negation, `**`), that it is evaluated against the build
       *context*, and that a missing one is both a speed and a leak problem. `[CFG]`
1.7.18 The heredoc form (`RUN <<EOF`) for multi-line scripts without `&& \` chains. `[CMD]`
1.7.19 `CHECK` / build checks (`# check=error=true`, `--check`) — BuildKit's built-in linting of
       your Dockerfile, and the rule names it emits. `[RESEARCH]`
1.7.20 Which instructions create layers and which only write metadata: `RUN`/`COPY`/`ADD` create
       filesystem layers; `ENV`/`LABEL`/`EXPOSE`/`USER`/`WORKDIR`/`ENTRYPOINT`/`CMD`/`VOLUME`/
       `STOPSIGNAL`/`SHELL`/`ARG` are metadata-only (they still create history entries). `[PROVE]`
       `[NUM]`

*(20 leaves)*

## §1.8 The build: BuildKit, LLB, and the cache

1.8.1 What replaced what: the legacy builder executed instructions sequentially against the
      daemon; **BuildKit** compiles the Dockerfile into **LLB** (low-level build definition), a
      content-addressed DAG, and solves it. Default since Engine 23.
1.8.2 What the DAG buys: **parallel execution of independent stages**, skipping stages no target
      depends on, mount-based caching, and secrets that never enter a layer. `[PROVE]`
1.8.3 The cache key rule, stated precisely: for a metadata instruction the key is the instruction
      string plus the parent's key; for `COPY`/`ADD` it also includes a **checksum of the copied
      file contents and metadata**; for `RUN` it is the command string only — **BuildKit does not
      know what a `RUN` reads**. `[PROVE]` `[TRAP]`
1.8.4 The corollary the current guide gets right and the bible must prove: **invalidating one layer
      invalidates every layer after it**, therefore order least-frequently-changing first.
      `[PROVE]`
1.8.5 The canonical Maven/Gradle ordering fix, with the numbers: `COPY mvnw pom.xml .mvn` →
      `RUN ./mvnw dependency:go-offline` → `COPY src` → `RUN ./mvnw package`. Quantify the
      difference on `funds-ledger`'s dependency set. `[NUM]` `[PROVE]`
1.8.6 `RUN --mount=type=cache` as the better answer for `~/.m2`, `~/.gradle`, `/root/.npm`,
      `/go/pkg/mod`, `/root/.cache/go-build`, `/root/.cache/pip`, `/root/.gem`,
      `/root/.nuget/packages`, `/var/cache/apt` + `/var/lib/apt` (with `sharing=locked`). It
      survives cache-key invalidation, which a layer cannot. `[PROVE]` `[CFG]` `[RESEARCH]`
1.8.7 `RUN --mount=type=secret` and `--mount=type=ssh`: build-time credentials that exist only for
      that `RUN` and appear in no layer and no history. The replacement for the `ARG TOKEN`
      antipattern. `[CMD]`
1.8.8 `apt-get update && apt-get install` must be **one `RUN`**, with `--no-install-recommends` and
      `rm -rf /var/lib/apt/lists/*`. Explain the stale-index failure mode mechanically, not as a
      rule. `[PROVE]` `[TRAP]`
1.8.9 Cache **exporters/importers**, complete: `inline` (embedded in the image, **min mode only**),
      `registry` (separate ref, supports `mode=max`), `local`, `gha`, `s3`, `azblob`. The
      `mode=min` vs `mode=max` distinction — min exports only the final stage's layers, max
      exports every intermediate step, which is what makes multi-stage builds cacheable in CI.
      `[CFG]` `[PROVE]` `[RESEARCH]`
1.8.10 Why CI has no cache by default (fresh runner, empty local store) and the three fixes:
       `--cache-from`/`--cache-to type=registry,mode=max`, `type=gha`, or a persistent builder.
       Quantify a build going from 9 minutes to 90 seconds. `[NUM]` `[CMD]`
1.8.11 `docker buildx` and **builder instances**: `docker-container`, `kubernetes` and `remote`
       drivers; `docker buildx create --use`, `--bootstrap`, `docker buildx du`,
       `docker buildx prune --filter until=72h`. `[CMD]`
1.8.12 Multi-platform builds: QEMU emulation (`--platform linux/amd64,linux/arm64`) vs **native
       multi-node builders**, and why emulated JDK builds are pathologically slow. `[NUM]`
1.8.13 `docker buildx bake` — declarative builds in `docker-bake.hcl`: targets, groups, matrices,
       inheritance, variables. The tool for building the whole QuizStakes estate in one command.
       `[CMD]` `[BUILD]`
1.8.14 Build output types: `--output type=docker|image|registry|local|tar|oci|cacheonly`, and why
       `--load` and `--push` are shorthands that behave differently for multi-platform images.
       `[CFG]` `[TRAP]`
1.8.15 `--provenance` and `--sbom`: SLSA provenance and SPDX SBOM attestations attached via the
       `subject` mechanism from §1.5.9, on by default for `--push` in recent buildx. `[RESEARCH]`
1.8.16 Reproducible builds: `SOURCE_DATE_EPOCH`, `--build-arg BUILDKIT_INLINE_CACHE`,
       `BUILDKIT_MULTI_PLATFORM=1` for deterministic output, and the timestamps/ordering that
       normally defeat bit-for-bit reproducibility. `[RESEARCH]`
1.8.17 Alternative builders worth being able to name and contrast: **Jib** (no Dockerfile, no
       daemon, layers by Maven dependency/resource/class split — genuinely the best default for a
       plain Spring Boot service), **Cloud Native Buildpacks** / `pack` /
       `spring-boot:build-image`, **Kaniko** (in-cluster, no privileged daemon), **ko** (Go),
       **Bazel `rules_oci`**. `[RESEARCH]`
1.8.18 Spring Boot's **layered jars** (`layertools`) and why they exist: split `dependencies`,
       `spring-boot-loader`, `snapshot-dependencies`, `application` into separate image layers so a
       code change re-pushes 2 MB, not 80 MB. Show the `layers.idx` and the extract idiom. `[NUM]`
       `[PROVE]` `[BUILD]`
1.8.19 Class Data Sharing (`-XX:ArchiveClassesAtExit`, `-XX:SharedArchiveFile`) and AppCDS baked
       into an image layer to cut JVM start-up — the lever that makes a 12→40 `ApplicationGateway`
       scale-out land inside a campaign spike. `[NUM]` `[X-REF 06]`
1.8.20 Build **context** sources: a path, `-` (stdin), a Git URL, a tarball URL, and named contexts
       (`--build-context deps=…`). `[CMD]`

*(20 leaves)*

## §1.9 Multi-stage builds and the JVM runtime image

1.9.1 The mechanism: multiple `FROM`s; only the last stage (or `--target`) is exported; earlier
      stages exist only to produce files that a later stage `COPY --from`s.
1.9.2 What that removes from the shipped image: the JDK, Maven/Gradle and their caches, the source
      tree, build tools, compilers, and the `.git` directory — both size and attack surface.
      Quantify: ~800 MB JDK+build image → ~200 MB JRE image → ~90 MB jlink image. `[NUM]`
1.9.3 `COPY --from=<stage>` and `COPY --from=<external image>` (e.g. copying `wget` or a CA bundle
      out of a distro image into a distroless one). `[CMD]`
1.9.4 `--target` for building only the test stage in CI, and the "test stage" pattern that makes
      `docker build --target test` the whole CI test command. `[CMD]` `[X-REF 16]`
1.9.5 Base image options for a JVM service, compared on libc, size, shell presence, CVE surface
      and JVM support: `eclipse-temurin:21-jdk-jammy`, `:21-jre-jammy`, `:21-jre-alpine`,
      `amazoncorretto:21`, `bellsoft/liberica-openjre-debian`, `gcr.io/distroless/java21-debian12`,
      `chainguard/jre`, `ubi9/openjdk-21-runtime`, `scratch` + jlink. `[NUM]` `[RESEARCH]`
1.9.6 **Alpine and musl**: why `-alpine` JDK images are a real trap for JVM workloads (musl vs
      glibc, DNS resolution differences, `Nashorn`/JNI native libs, historically worse
      `Thread.sleep`/futex behaviour), and that Temurin ships genuine musl builds so it *can* work
      — if you test it. `[TRAP]` `[RESEARCH]`
1.9.7 **Distroless**: no shell, no package manager, no `ls`. Why that is a security win and a
      debugging problem, and the answer (`kubectl debug --image=busybox --target=…`, §2.29).
      `[TRAP]`
1.9.8 `jlink` + `jdeps` to build a custom runtime containing only the modules the service uses;
      `--strip-debug --no-man-pages --no-header-files --compress=zip-9`. Show the module list for
      a Spring Boot service and the resulting size. `[NUM]` `[CMD]` `[BUILD]`
1.9.9 **`jlink` + AppCDS + a static base** vs **GraalVM native image** for `client-restrictions`
      (30 ms budget, 8 instances, aggressive autoscaling): start-up, RSS, peak throughput,
      build time, reflection configuration cost. Give the decision, not a survey. `[NUM]`
      `[RESEARCH]`
1.9.10 The complete production Dockerfile for a QuizStakes service, annotated line by line — this
       is the artefact the reader copies. `[BUILD]` `[YAML]`
1.9.11 Ordering constraints inside the runtime stage that people get wrong: create the user before
       `COPY --chown`; `USER` after everything needing root; `chmod` on the jar not needed;
       `WORKDIR` before `COPY .` relative paths.
1.9.12 Why the container should *not* run `./mvnw spring-boot:run` and should not contain the
       wrapper at all.

*(12 leaves)*

## §1.10 The Docker CLI surface

1.10.1 Build and inspect: `docker build`/`docker buildx build` with `-t`, `-f`, `--build-arg`,
       `--target`, `--platform`, `--progress=plain|tty|rawjson`, `--no-cache`, `--pull`,
       `--secret`, `--ssh`, `--cache-from`, `--cache-to`, `--push`, `--load`, `--provenance`,
       `--sbom`. `[CMD]`
1.10.2 `docker images`, `docker image inspect`, `docker history`, `docker manifest inspect`,
       `docker buildx imagetools inspect --raw`. `[CMD]`
1.10.3 `docker run` — the flags that matter, grouped: identity (`--name`, `-d`, `--rm`,
       `--restart=no|on-failure[:n]|always|unless-stopped`); I/O (`-i`, `-t`, `-a`); networking
       (`-p`, `-P`, `--network`, `--add-host`, `--dns`, `--hostname`); resources (`--memory`,
       `--memory-swap`, `--memory-reservation`, `--cpus`, `--cpu-shares`, `--cpuset-cpus`,
       `--pids-limit`, `--oom-kill-disable`, `--blkio-weight`); config (`-e`, `--env-file`,
       `-v`, `--mount`, `-w`, `-u`, `--entrypoint`); lifecycle (`--init`, `--stop-signal`,
       `--stop-timeout`, `--health-*`); security (`--cap-add/drop`, `--privileged`,
       `--security-opt`, `--read-only`, `--tmpfs`, `--userns`, `--group-add`). `[CMD]` `[CFG]`
1.10.4 `docker ps [-a] [--filter] [--format]`, `docker inspect`, `docker top`, `docker stats
       [--no-stream]`, `docker events`, `docker port`, `docker diff` (what changed in the writable
       layer — the underused one). `[CMD]`
1.10.5 `docker logs -f --tail --since --until --timestamps`, and where those bytes actually live
       (`/var/lib/docker/containers/<id>/<id>-json.log`) and why `--log-driver`/`--log-opt
       max-size=10m,max-file=3` is not optional on a long-lived host. `[NUM]` `[CFG]` `[X-REF 20]`
1.10.6 `docker exec -it … sh` vs `docker run -it --entrypoint sh <image>`: enter a running
       container vs poke at the image. **You cannot `exec` into a crash-looping container** — the
       current guide's point, kept and expanded. `[TRAP]`
1.10.7 `docker stop` (SIGTERM, then SIGKILL after **10 s** by default, `-t` to change; Engine 29
       adds a daemon-wide `default-stop-timeout`) vs `docker kill [-s SIGNAL]` (immediate) vs
       `docker pause`/`unpause` (cgroup freezer). `[NUM]` `[CFG]` `[RESEARCH]`
1.10.8 `docker cp` in both directions and its use for heap dumps
       (`docker cp funds-ledger:/tmp/heap.hprof .`). `[CMD]` `[X-REF 06]`
1.10.9 `docker commit`, `docker save`/`docker load`, `docker export`/`docker import` — the
       difference between an image with history and a flattened rootfs tar, and why `commit` is a
       debugging tool and never a build tool. `[TRAP]`
1.10.10 `docker system df [-v]`, `docker system prune -a --volumes`, `docker image prune
        --filter until=168h`, `docker builder prune`, `docker volume prune`. The "my CI runner ran
        out of disk" toolkit — and the warning that `-a` deletes images you still want. `[TRAP]`
        `[CMD]`
1.10.11 `docker context` (`create`, `use`, `ls`) and `DOCKER_HOST` — how you point the CLI at a
        remote daemon, and why exposing the daemon over TCP without mTLS is a root-shell-as-a-service.
        `[TRAP]`
1.10.12 `docker info`, `docker version` (client vs server), and reading the storage driver /
        cgroup driver / image store from `docker info` — the first thing to check when behaviour
        differs between hosts. `[CMD]`
1.10.13 The Docker API and socket: `/var/run/docker.sock`, `curl --unix-socket`,
        `GET /containers/json`, and that **socket access == root on the host** (mount it in a
        container and you can start a privileged container mounting `/`). This is the mechanism
        behind Testcontainers *and* behind a large class of CI compromises. `[PROVE]` `[TRAP]`
        `[X-REF 16]`
1.10.14 The Docker-adjacent CLIs to recognise: `nerdctl` (containerd, Docker-compatible flags),
        `ctr` (containerd's low-level debug CLI), `crictl` (CRI-level, what you use on a
        Kubernetes node), `podman` (daemonless, rootless-first, `podman generate kube`). `[CMD]`

*(14 leaves)*

## §1.11 Container lifecycle, PID 1, and signals

1.11.1 The states: `created` → `running` → (`paused`) → `exited`/`dead`, plus `restarting` and
       `removing`, and what `docker ps -a` shows for each.
1.11.2 Exit codes you must recognise on sight: `0` clean; `1` app error; `125` daemon/CLI error;
       `126` command not executable; `127` command not found (**the misspelled entrypoint**);
       `128+N` killed by signal N — so **`137` = SIGKILL (9)**, **`143` = SIGTERM (15)**,
       `139` = SIGSEGV (11), `130` = SIGINT (2). `[NUM]` `[PROVE]`
1.11.3 **PID 1 is special**: the kernel does not install default handlers for it, so a signal with
       no registered handler is *ignored* rather than killing the process. Consequence: a naive PID
       1 that ignores SIGTERM is SIGKILLed after the grace period, every time. `[PROVE]` `[TRAP]`
1.11.4 **PID 1 must reap orphans.** When a container's PID 1 is not an init, exited grandchildren
       become permanent zombies, consuming PIDs until `pids.max` is hit. `[PROVE]`
1.11.5 The two fixes: `--init` (Docker injects `tini`) / `tini` as entrypoint, or make your process
       handle it. Kubernetes has no `--init` — you add a real init or you make PID 1 correct.
       `[TRAP]`
1.11.6 **Exec form vs shell form, mechanically.** `ENTRYPOINT java -jar app.jar` becomes
       `/bin/sh -c "java -jar app.jar"`; the shell is PID 1, the JVM is PID 2, **`sh` does not
       forward SIGTERM**, and the JVM never learns it should shut down. Prove it with
       `docker top`/`ps` output. `[PROVE]` `[TRAP]` `[SOURCE]`
1.11.7 The wrapper-script escape hatch: `exec java …` as the last line replaces the shell with the
       JVM so the JVM *is* PID 1. Show both scripts and the resulting `ps` trees. `[BUILD]`
1.11.8 What the JVM does with SIGTERM: the default shutdown hook path runs `Runtime` hooks; Spring
       Boot's `server.shutdown=graceful` and
       `spring.lifecycle.timeout-per-shutdown-phase` build on it. Full chain in §2.11.
1.11.9 `STOPSIGNAL` and `--stop-signal` for runtimes that want something else; and why Kubernetes
       always sends SIGTERM regardless.
1.11.10 `postStart` and `preStop` **lifecycle hooks** (`exec`, `httpGet`, `sleep` — the
        `sleep` handler being the newer, shell-free form), their blocking semantics, and that a
        failing hook kills the container. `[CFG]` `[RESEARCH]`
1.11.11 The **restart backoff** numbers: exponential from **100 ms** to a cap of **5 minutes
        (300 s)**, reset after **10 minutes** of successful running — which is exactly why a
        `CrashLoopBackOff` pod restarts less and less often and why "it recovered on its own after
        20 minutes" is usually a coincidence. `[NUM]` `[PROVE]` `[RESEARCH]`
1.11.12 `restartPolicy` at pod level (`Always`/`OnFailure`/`Never`) and, since 1.29+, at
        **container** level — including the sidecar spelling and the container-level restart rules
        with exit-code-based restart. `[CFG]` `[RESEARCH]`
1.11.13 Health as a first-class state: Docker's `HEALTHCHECK` produces `starting`/`healthy`/
        `unhealthy` in `docker ps`; Compose's `depends_on: condition: service_healthy` consumes it;
        Kubernetes ignores it. `[TRAP]`

*(13 leaves)*

## §1.12 Container storage: volumes, bind mounts, tmpfs

1.12.1 The three mount kinds and when each is right: **named volume** (Docker-managed under
       `/var/lib/docker/volumes/<name>/_data`, the choice for persistence), **bind mount** (a host
       path, the choice for local development), **tmpfs** (memory-backed, the choice for secrets
       and scratch). `[CFG]`
1.12.2 `-v` short syntax vs `--mount` long syntax, and why `--mount` is preferable (explicit,
       fails on typos instead of silently creating a directory). `[TRAP]`
1.12.3 Volume drivers and options: `local` with `o=bind`, NFS/CIFS options, and third-party
       drivers.
1.12.4 Mount propagation (`private`/`rprivate`/`shared`/`rshared`/`slave`/`rslave`) and the one
       place it matters in practice (a CSI node plugin, a log agent). `[CFG]`
1.12.5 `:ro`, `:z`/`:Z` for SELinux relabelling, `nocopy`, and `--read-only` + `--tmpfs /tmp` as
       the hardened shape.
1.12.6 The UID mismatch problem: a bind mount owned by host UID 1000 mounted into a container
       running as UID 10001 is unreadable, and the fixes (`--user $(id -u):$(id -g)`, `chown` in an
       init container, user namespace ID mapping, `idmap` mounts). `[TRAP]` `[DIAG]`
1.12.7 Why bind-mount I/O is slow on Docker Desktop for macOS/Windows: the container runs in a Linux
       VM, so every file access crosses a 9p/virtiofs boundary. The mitigations
       (`:cached`/`:delegated` legacy flags, VirtioFS, gRPC-FUSE, mutagen-style sync, or simply not
       bind-mounting `~/.m2`). `[NUM]` `[TRAP]`
1.12.8 What happens to the writable layer and to volumes on `docker rm`, `docker rm -v`,
       `docker compose down`, `docker compose down -v`. `[PROVE]`
1.12.9 Kubernetes volume types, complete inventory with what each is for: `emptyDir` (+
       `medium: Memory`, `sizeLimit`), `hostPath` (+ every `type` value, and why it is banned by
       Baseline), `configMap`, `secret`, `downwardAPI`, `projected`, `persistentVolumeClaim`,
       `csi`, `ephemeral` (generic ephemeral volumes), `image` (**stable 1.36**), `nfs`,
       `iscsi`, `fc`, `local`, and the removed ones (`gitRepo` **removed in 1.36**, in-tree cloud
       providers migrated to CSI). `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
1.12.10 `subPath` and `subPathExpr`, and the classic trap: **a `configMap` mounted with `subPath`
        does not get updated** when the ConfigMap changes, while a whole-directory mount does.
        `[TRAP]` `[PROVE]`
1.12.11 `emptyDir` sizing against `ephemeral-storage` limits, and `medium: Memory` counting against
        the **memory** limit — so a 1 GiB tmpfs inside a 1 GiB pod is an instant OOMKill.
        `[PROVE]` `[TRAP]` `[NUM]`
1.12.12 The QuizStakes mapping: document images (2–6 MB × 24k/day) go to object storage, never a
        volume; `FundsLedger`'s in-memory reservation index is heap, not a volume; `/tmp` is an
        `emptyDir` because the root filesystem is read-only.

*(12 leaves)*

## §1.13 Container networking (the Docker side)

1.13.1 The default `bridge` network: `docker0`, a `veth` pair per container, NAT via
       iptables/nftables `MASQUERADE`, and why containers on the default bridge get IPs but no name
       resolution. `[PROVE]`
1.13.2 **User-defined bridge networks** get an embedded DNS server at `127.0.0.11`, which is why
       `docker compose` service names resolve and default-bridge containers need `--link` (legacy).
       `[PROVE]`
1.13.3 The other drivers: `host` (no network namespace — the container shares the host's, so no
       port mapping and no isolation), `none`, `overlay` (Swarm/multi-host, VXLAN), `macvlan`,
       `ipvlan`, and third-party plugins. `[CFG]`
1.13.4 `-p [hostIP:]hostPort:containerPort[/proto]` decoded: it is a DNAT rule plus a
       userland proxy fallback (`docker-proxy`), and `hostPort` binds on all interfaces unless you
       say `127.0.0.1:8080:8080` — which is why "I only exposed it locally" is often false and the
       service is on the internet. `[TRAP]` `[PROVE]`
1.13.5 `host.docker.internal` / `gateway.docker.internal` and `--add-host
       host.docker.internal:host-gateway` — reaching the host from a container. `[CMD]`
1.13.6 `docker network create/inspect/connect/disconnect`, custom subnets, and IP address
       management. `[CMD]`
1.13.7 Why the Docker daemon writes iptables rules, what `DOCKER-USER` is for, and why
       `--iptables=false` breaks connectivity while a hand-written `INPUT` rule silently does not
       protect published ports (DNAT happens in `PREROUTING`, before `INPUT`). `[PROVE]` `[TRAP]`
       `[X-REF 10]`
1.13.8 `/etc/hosts`, `/etc/resolv.conf` and `/etc/hostname` are **bind-mounted files**, not part of
       the image — which is why editing them inside a container does not persist and why
       `--dns`/`--dns-search` exist. `[PROVE]`
1.13.9 MTU problems: an overlay or VPN reduces the effective MTU, large responses hang while small
       ones work, and the symptom is "curl works but the JDBC driver times out". `[DIAG]`
       `[X-REF 10]`
1.13.10 How this all differs in Kubernetes: **no NAT between pods**, one IP per pod, a flat address
        space, and a CNI plugin rather than `docker0`. Forward to §3.17.

*(10 leaves)*

## §1.14 Registries, references, tags and digests

1.14.1 The reference grammar, fully decomposed:
       `[registry[:port]/]namespace/repository[:tag][@digest]`, and the defaults that bite —
       a bare `redis` means `docker.io/library/redis:latest`. `[PROVE]` `[TRAP]`
1.14.2 The registries you will meet: Docker Hub (and its **anonymous/authenticated pull rate
       limits**, which break CI at the worst possible moment), ECR (+ ECR Public), GHCR, GAR/GCR,
       ACR, Quay, GitLab, Artifactory, Harbor, and `distribution` (the reference implementation) as
       a local pull-through cache. `[RESEARCH]` `[X-REF 18]`
1.14.3 The distribution API verbs a pull actually performs: `GET /v2/`,
       `GET /v2/<name>/manifests/<ref>` with an `Accept` list, then `GET /v2/<name>/blobs/<digest>`
       per layer; and the push flow with `POST /v2/<name>/blobs/uploads/` chunked uploads and
       `PUT /v2/<name>/manifests/<ref>`. Full treatment in §3.7. `[SOURCE]`
1.14.4 Authentication: `docker login`, `~/.docker/config.json`, credential helpers
       (`docker-credential-ecr-login`, `osxkeychain`), the token-service handshake
       (`WWW-Authenticate: Bearer realm=…,service=…,scope=…`), and
       `aws ecr get-login-password | docker login --password-stdin`. `[CMD]`
1.14.5 In Kubernetes: `imagePullSecrets`, the `kubernetes.io/dockerconfigjson` secret type,
       service-account-attached pull secrets, and node-level credential providers (the EKS/GKE
       node role, the **kubelet credential provider** plugin API) — which is why ECR usually needs
       no secret at all. `[CFG]`
1.14.6 **Tags are mutable pointers; digests are immutable content addresses.** `myimage:1.4.2` can
       be repointed; `myimage@sha256:…` cannot. `[PROVE]`
1.14.7 The tagging strategy, argued rather than asserted: semantic version for humans, **git SHA
       for traceability**, `<version>-<sha>` as the best default, `latest` as a convenience pointer
       only. Push both; **deploy only the immutable one.**
1.14.8 **Trap: deploying `:latest`.** You cannot tell what is running; two nodes can hold different
       bytes under the same tag; `imagePullPolicy` defaults interact badly; and **rollback is
       impossible because the previous artefact has no name**. Keep the current guide's framing and
       add the `imagePullPolicy` mechanism. `[TRAP]`
1.14.9 `imagePullPolicy` values and the **implicit default rule**: `Always` if the tag is `:latest`
       or absent, otherwise `IfNotPresent`; `Never` for pre-loaded images. Plus
       `alwaysPullImages` admission and why a mutable tag plus `IfNotPresent` gives you a fleet
       running two different builds. `[CFG]` `[PROVE]` `[TRAP]`
1.14.10 Rollback by tag as the fastest recovery action: `kubectl rollout undo` vs
        `kubectl set image` vs re-applying the previous Git commit, and which one leaves your
        cluster matching Git. Keep the current guide's "roll back first, diagnose second".
        `[X-REF 20]`
1.14.11 Registry lifecycle policies: keep the last N *and* everything currently referenced by a
        running workload; the incident where the rollback target had been garbage-collected.
        `[TRAP]` `[X-REF 18]`
1.14.12 Kubernetes records the **digest it actually pulled** in
        `status.containerStatuses[].imageID` — the only reliable answer to "what is running right
        now". `[CMD]` `[PROVE]`
1.14.13 Image garbage collection on the node: kubelet's `--image-gc-high-threshold` (85) /
        `--image-gc-low-threshold` (80) / `--minimum-image-ttl-duration` (2m), and why a node with
        a full disk starts evicting pods and deleting images you were about to roll back to.
        `[NUM]` `[CFG]` `[RESEARCH]`
1.14.14 Mirroring, pull-through caches and air-gapped estates: `registry-mirrors`, containerd's
        `hosts.toml`, and why a Hub outage should not stop a scale-out. `[CFG]`

*(14 leaves)*

## §1.15 Compose for local stacks and CI

1.15.1 What Compose is for: one command that gives a new engineer the whole QuizStakes local
       stack — Postgres, Redis, the object store, the broker, LocalStack, the service under test —
       correctly wired. Its value is onboarding time, not orchestration.
1.15.2 The **Compose Specification** as the actual schema (top-level `services`, `networks`,
       `volumes`, `configs`, `secrets`, `include`, `profiles`), and that `version:` is obsolete and
       ignored. `[VERSION-TRAP]` `[CFG]`
1.15.3 The service keys worth knowing by name: `build` (with `context`, `dockerfile`, `args`,
       `target`, `cache_from`, `platforms`), `image`, `command`, `entrypoint`, `environment`,
       `env_file`, `ports`, `expose`, `volumes`, `depends_on`, `healthcheck`, `restart`,
       `deploy.resources.limits`, `networks`, `profiles`, `develop.watch`, `extends`,
       `init`, `stop_grace_period`, `stop_signal`, `user`, `working_dir`, `tmpfs`, `cap_add`,
       `sysctls`, `ulimits`, `labels`, `pull_policy`, `scale`. `[CFG]`
1.15.4 Compose creates a **project-scoped network where service names are DNS names** — hence
       `jdbc:postgresql://ledger-db:5432/…`, not `localhost`. `[PROVE]`
1.15.5 **`depends_on` orders start-up, not readiness.** The classic bug: the service starts before
       Postgres accepts connections and crash-loops. Fixes: `condition: service_healthy` with a
       real `healthcheck`, `condition: service_completed_successfully` for migrations, and
       app-side connection retry — which you want anyway. Keep the current guide's treatment and
       add the third condition. `[TRAP]` `[CFG]`
1.15.6 `healthcheck` in Compose: `test` (`CMD` vs `CMD-SHELL`), `interval`, `timeout`, `retries`,
       `start_period`, `start_interval`, `disable`. `[CFG]`
1.15.7 Variable interpolation and precedence: `.env`, shell environment, `--env-file`,
       `env_file` vs `environment`, `${VAR:-default}` and `${VAR:?error}`, and the
       `COMPOSE_PROJECT_NAME`/`COMPOSE_FILE`/`COMPOSE_PROFILES` variables. `[CFG]` `[TRAP]`
1.15.8 Multiple files and overrides: `compose.yaml` + `compose.override.yaml` automatic merge,
       `-f a.yaml -f b.yaml` explicit merge and its list-vs-map merge rules, `include:`, and
       `profiles:` for optional services. `docker compose config` to see the resolved result.
       `[CMD]` `[TRAP]`
1.15.9 The command surface: `up -d --build --wait --wait-timeout --remove-orphans`, `down [-v]
       [--rmi]`, `ps`, `logs -f`, `exec`, `run --rm`, `build`, `pull`, `restart`, `stop`, `cp`,
       `top`, `events`, `config`, `watch`, `scale`. `[CMD]`
1.15.10 `docker compose watch` and the `develop.watch` block (`action: sync|rebuild|sync+restart`)
        — the modern inner-loop replacement for bind-mounting your whole source tree.
        `[RESEARCH]` `[CFG]`
1.15.11 `docker compose up --wait` as the CI gate: it exits non-zero if a service never becomes
        healthy, which is what makes Compose usable in a pipeline. `[CMD]` `[X-REF 16]`
1.15.12 Named volumes for `pgdata` and why `down -v` between test runs is both the fix and the
        footgun.
1.15.13 Where Compose stops: no rescheduling, no autoscaling, no rolling updates, no health-driven
        replacement, single host. **Compose is development and CI; production is ECS or
        Kubernetes.** Keep the current guide's line and justify it mechanically.
1.15.14 The complete QuizStakes `compose.yaml` the bible must ship: `application-gateway`,
        `funds-ledger`, `client-restrictions`, Postgres (two instances — shared-schema and
        ledger-own-instance, matching Appendix B.2), Redis, LocalStack for object storage, a broker,
        and a `migrations` one-shot service. `[BUILD]` `[YAML]`
1.15.15 Compose vs Testcontainers for integration tests, and the `compose.yaml`-driven
        `ComposeContainer` that lets you use one definition for both. `[X-REF 16]`

*(15 leaves)*

## §1.16 The runtime stack: from `docker run` to a process

1.16.1 The layered picture, named end to end: `docker` CLI → **dockerd** (HTTP API, images, builds,
       networks) → **containerd** (container lifecycle, snapshots, content store) →
       **containerd-shim-runc-v2** (one per container, owns the process, survives daemon restarts) →
       **runc** (creates the namespaces/cgroups and `execve`s) → your process. `[SOURCE]`
1.16.2 Why the shim exists: it keeps containers running when containerd or dockerd restarts, owns
       the stdio/TTY, and reports exit status. Without it, restarting the daemon would kill every
       container. `[PROVE]`
1.16.3 The three specs that make this pluggable: **OCI Image Spec** (what an image is),
       **OCI Runtime Spec** (`config.json` + rootfs = a bundle), **OCI Distribution Spec** (how
       registries talk).
1.16.4 The **CRI** (Container Runtime Interface): a gRPC API with `RuntimeService` and
       `ImageService`, spoken by the kubelet to containerd (via the `cri` plugin) or **CRI-O**.
       Full method inventory in §3.10. `[SOURCE]`
1.16.5 **Dockershim was removed in Kubernetes 1.24.** Docker is not a Kubernetes runtime; Docker
       *images* still run because they are OCI images. Say this precisely — it is the single most
       misremembered fact in the topic. `[VERSION-TRAP]` `[TRAP]`
1.16.6 `cri-dockerd` as the external adapter for estates that still need it, and why choosing it is
       choosing an extra hop.
1.16.7 Alternative runtimes by shape: `runc` (default), `crun` (C, faster start), `youki` (Rust),
       `runsc`/gVisor (userspace kernel), `kata-runtime` (VM per pod), `wasmtime`/`runwasi`
       (WASM). Selected per-pod through `RuntimeClass`. `[CFG]`
1.16.8 Node-level debugging with `crictl`: `crictl ps`, `crictl pods`, `crictl images`,
       `crictl logs`, `crictl inspect`, `crictl exec`, `crictl stats`, `crictl rmi --prune`, and
       `--runtime-endpoint unix:///run/containerd/containerd.sock`. This is what you use when
       `kubectl` cannot reach the pod. `[CMD]`
1.16.9 `ctr -n k8s.io containers ls` and why the `k8s.io` namespace matters — containerd
       namespaces are not Kubernetes namespaces. `[TRAP]`
1.16.10 The Engine 29 experiment worth knowing about: **embedded containerd** running inside the
        daemon process rather than as a separate managed process. `[RESEARCH]`

*(10 leaves)*

## §1.17 Why Kubernetes exists at all, and what it decided differently

1.17.1 The problem statement once containers worked: N services × M replicas on K machines, with
       machines failing, images changing, traffic moving, and no human able to hold the placement
       in their head. Scheduling, health, discovery, rollout and recovery all become mandatory.
1.17.2 The lineage: Google's **Borg** and **Omega**, the 2014 open-sourcing as Kubernetes, the CNCF
       donation in 2015, and the 2017 Mesos/Swarm/Kubernetes convergence. Name what Borg taught it:
       declarative jobs, labels over hostnames, priority/preemption, and the "everything is a
       controller" model. `[RESEARCH]`
1.17.3 Decision one: **declarative desired state, not imperative commands.** You submit what should
       be true; controllers make it true and keep it true. `[PROVE]`
1.17.4 Decision two: **level-triggered reconciliation, not edge-triggered events.** A controller
       compares full desired state against full observed state, so a missed event is self-healing
       rather than a permanent divergence. This is the single most important architectural fact in
       the whole system. `[PROVE]`
1.17.5 Decision three: **a uniform, extensible API is the product.** Everything is a REST resource
       with the same verbs, the same metadata, the same watch semantics — so a CRD is
       indistinguishable from a built-in to every client, controller and tool. `[PROVE]`
1.17.6 Decision four: **labels and selectors instead of names and hostnames.** Grouping is a query,
       not a registry, which is what makes rollouts, Services and NetworkPolicies composable.
1.17.7 Decision five: **the pod, not the container, is the unit of scheduling** — because
       co-located processes that share a network namespace and lifecycle are a real pattern
       (proxies, log shippers, `RouterInt` as a sidecar).
1.17.8 Decision six: **a flat pod network with no NAT between pods**, which pushes the hard part
       into a pluggable CNI and makes service discovery a naming problem rather than a
       port-allocation problem.
1.17.9 What all this costs: an enormous concept surface; eventual consistency everywhere, so
       "applied" ≠ "running"; YAML as the interface; a control plane to operate; and a genuine
       organisational prerequisite. The bible must state this honestly — §2.30 is the payoff.
1.17.10 The honest positioning to hold onto: **use the simplest orchestrator that meets the
        requirement, and be able to say why the requirement needs more.** Keep the current guide's
        §13 argument.

*(10 leaves)*

## §1.18 The Kubernetes architecture

1.18.1 The control-plane components, each with its single responsibility: **kube-apiserver** (the
       only thing that talks to etcd; auth, admission, validation, watch), **etcd** (the state),
       **kube-scheduler** (pod → node binding), **kube-controller-manager** (the built-in control
       loops), **cloud-controller-manager** (cloud-specific loops).
1.18.2 The node components: **kubelet** (the node agent; makes pods real), **container runtime**
       (containerd/CRI-O), **kube-proxy** (Service datapath — and increasingly replaced by a CNI's
       eBPF datapath).
1.18.3 The add-ons that every real cluster has and that are not "core": **CoreDNS**, a **CNI
       plugin**, **metrics-server**, a **CSI driver**, an **ingress/Gateway controller**, and
       usually cert-manager, external-secrets and a node autoscaler.
1.18.4 The controller inventory inside kube-controller-manager, named: deployment, replicaset,
       statefulset, daemonset, job, cronjob, node lifecycle, endpointslice, service account,
       token, namespace, PV/PVC binder, attach/detach, resource quota, HPA, disruption, TTL,
       garbage collector, root-CA publisher, PodGC. Naming these is how you answer "what actually
       created my ReplicaSet". `[SOURCE]`
1.18.5 **Nothing except the API server talks to etcd.** Every other component watches the API
       server. This is why an etcd problem looks like "everything is frozen but still serving".
       `[PROVE]`
1.18.6 What keeps running when the control plane is down: existing pods keep running, kube-proxy
       keeps its rules, DNS keeps answering — but nothing reschedules, nothing scales, no rollout
       progresses, and no new pod starts. Being able to say this precisely is a common interview
       discriminator. `[PROVE]`
1.18.7 High availability: 3 or 5 control-plane nodes, **etcd quorum arithmetic
       `(n/2)+1`** and why even numbers are worse than the odd number below them; stacked vs
       external etcd; leader election via `Lease` objects in `kube-system`. `[NUM]` `[PROVE]`
       `[X-REF 22]`
1.18.8 Managed control planes: what EKS/GKE/AKS take over (etcd, apiserver, upgrades, backups) and
       what remains yours (node images, addons, RBAC, cost, resource requests). EKS control-plane
       pricing (~$73/month/cluster at $0.10/hr) as a real input to §2.30. `[NUM]` `[X-REF 18]`
1.18.9 Cluster bootstrap paths worth recognising: `kubeadm`, managed services, `kind`/`k3d`/`minikube`
       for local, k3s/k0s for edge, and "the hard way" as a learning exercise. `[CMD]`
1.18.10 Where a request goes, one sentence per hop: `kubectl` → TLS → apiserver
        (authn → authz → mutating admission → schema validation → validating admission →
        etcd write) → watch event → controller → watch event → scheduler → binding → kubelet →
        CRI → runc → process. §3.11 does this properly. `[PROVE]`
1.18.11 Static pods (`/etc/kubernetes/manifests`) and why the control plane on a kubeadm cluster is
        itself pods that the kubelet runs without an API server. `[PROVE]`
1.18.12 Node object lifecycle: registration, `kubelet` heartbeats via **Lease** objects (default
        `nodeLeaseDurationSeconds` 40 s, node-monitor-grace-period 50 s), `Ready` condition,
        `node.kubernetes.io/not-ready` and `unreachable` taints, and the **5-minute default**
        `tolerationSeconds` that governs how long pods stay on a dead node. `[NUM]` `[CFG]`
        `[RESEARCH]`

*(12 leaves)*

## §1.19 The API: groups, versions, resources, and the object envelope

1.19.1 The URL shapes: `/api/v1/namespaces/{ns}/pods/{name}` (the legacy core group) and
       `/apis/{group}/{version}/namespaces/{ns}/{resource}/{name}` for everything else. `[SOURCE]`
1.19.2 The groups you must recognise: core (`v1`), `apps`, `batch`, `networking.k8s.io`,
       `rbac.authorization.k8s.io`, `policy`, `storage.k8s.io`, `autoscaling`,
       `apiextensions.k8s.io`, `admissionregistration.k8s.io`, `coordination.k8s.io`,
       `discovery.k8s.io`, `scheduling.k8s.io`, `node.k8s.io`, `certificates.k8s.io`,
       `authentication.k8s.io`, `authorization.k8s.io`, `events.k8s.io`, `flowcontrol.apiserver.k8s.io`,
       `resource.k8s.io`, `gateway.networking.k8s.io`. `[SOURCE]`
1.19.3 The stability ladder in the version string: `v1alpha1` (may vanish, off by default),
       `v1beta1` (on or off by default depending on the release policy — and **new beta APIs are
       off by default** since 1.24), `v1` (permanent). What "deprecated" means under the
       **Kubernetes deprecation policy** (GA APIs: 12 months or 3 releases, whichever is longer).
       `[NUM]` `[SOURCE]`
1.19.4 The **object envelope** every object shares: `apiVersion`, `kind`, `metadata`, `spec`,
       `status`. Why `spec` is yours and `status` is the controller's, and why writing `status` by
       hand is meaningless.
1.19.5 `metadata` in full: `name`, `generateName`, `namespace`, `uid`, `resourceVersion`,
       `generation`, `creationTimestamp`, `deletionTimestamp`, `deletionGracePeriodSeconds`,
       `labels`, `annotations`, `ownerReferences`, `finalizers`, `managedFields`. Each of these
       does real work; the bible explains each. `[SOURCE]`
1.19.6 `resourceVersion` is an **opaque etcd revision**, not a counter you may compare or
       increment — and it is the basis of optimistic concurrency (`409 Conflict`) and of watch
       resumption. `[PROVE]` `[TRAP]`
1.19.7 `generation` vs `status.observedGeneration`: the mechanism by which you can tell whether a
       controller has seen your latest change — and therefore whether "it worked" or "it has not
       looked yet". `[PROVE]`
1.19.8 `ownerReferences` and **cascading deletion**: `Foreground`, `Background` (the default) and
       `Orphan` propagation policies, `blockOwnerDeletion`, and the garbage collector that walks the
       graph. This is why deleting a Deployment deletes its ReplicaSets and Pods. `[PROVE]` `[CFG]`
1.19.9 `finalizers` and the reason a namespace gets stuck in `Terminating` forever: the object
       cannot be removed until every finalizer is cleared, and the controller that was supposed to
       clear it is gone. The diagnosis and the (dangerous) fix. `[DIAG]` `[TRAP]`
1.19.10 **Server-side apply** and `managedFields`: field ownership per manager, conflict detection,
        `--force-conflicts`, and why `kubectl apply` (client-side, three-way merge via the
        `last-applied-configuration` annotation) and `kubectl apply --server-side` behave
        differently. Helm 4 defaulting to SSA makes this a working concern, not trivia.
        `[PROVE]` `[RESEARCH]`
1.19.11 The verbs: `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`,
        `deletecollection`, plus the non-resource verbs. And the four patch types —
        JSON Patch (`application/json-patch+json`), merge patch
        (`application/merge-patch+json`), **strategic merge patch**
        (`application/strategic-merge-patch+json`, with `patchMergeKey`/`patchStrategy`), and
        apply patch (`application/apply-patch+yaml`). Which one `kubectl patch` uses by default.
        `[SOURCE]` `[TRAP]`
1.19.12 **Subresources** are separate endpoints with separate RBAC: `status`, `scale`,
        `resize` (**1.35 GA**), `log`, `exec`, `attach`, `portforward`, `proxy`, `binding`,
        `eviction`, `token`, `ephemeralcontainers`, `approval`. "Can read pods" and "can exec into
        pods" are different permissions because of this. `[PROVE]` `[CFG]`
1.19.13 Watch semantics: `?watch=true&resourceVersion=…`, `ADDED`/`MODIFIED`/`DELETED`/`BOOKMARK`
        events, `410 Gone` on a too-old resourceVersion and the relist that follows, and
        `sendInitialEvents` + watch cache. Forward to §3.13. `[SOURCE]`
1.19.14 Pagination and its traps: `limit`/`continue`, why a `list` of 40k pods can OOM the
        apiserver, and the 1.37 **etcd RangeStream** work that cuts memory on large list reads.
        `[RESEARCH]`
1.19.15 API discovery and `kubectl api-resources -o wide` / `kubectl api-versions` /
        `kubectl explain <kind>.<field> --recursive` — the way to answer a field question without
        a browser. `[CMD]`
1.19.16 **API Priority and Fairness** (`flowcontrol.apiserver.k8s.io`): `FlowSchema`,
        `PriorityLevelConfiguration`, and why a runaway controller gets `429`d instead of taking
        the apiserver down. `[CFG]` `[RESEARCH]`
1.19.17 `Event` objects: `events.k8s.io/v1`, the `reason`/`message`/`count`/`firstTimestamp`
        shape, aggregation, and the **1-hour default TTL** that is why
        `kubectl get events` is empty for the incident you are investigating. `[NUM]` `[TRAP]`
1.19.18 Object size and count limits that matter: the **1.5 MiB** etcd request limit (so a
        ConfigMap/Secret cannot exceed ~1 MiB), the 262144-byte annotation limit, and the label
        value constraints (63 chars, alphanumeric plus `-_.`). `[NUM]` `[TRAP]`

*(18 leaves)*

## §1.20 The declarative model and the reconciliation loop

1.20.1 The loop, stated as code: `for { desired := readSpec(); actual := observe();
       act(diff(desired, actual)) }`. Every controller is this.
1.20.2 Why **idempotence** is a hard requirement of every action in that loop, and what happens
       when a controller's action is not idempotent (duplicate cloud load balancers, orphaned
       volumes). `[PROVE]`
1.20.3 Why **level-triggered** beats edge-triggered here: a dropped, duplicated or reordered event
       costs latency, not correctness. Contrast with an event-sourced design that would need exactly
       once delivery. `[PROVE]` `[X-REF 14]`
1.20.4 The consequences you must be able to predict: deleting a pod recreates it; a crashed node's
       pods get rescheduled; a manual `kubectl scale` is reverted by the next `apply`; a manually
       edited field is reverted by the owning controller.
1.20.5 **Trap: `kubectl edit` on a live object.** Your fix vanishes at the next apply/sync and
       nobody can find out why. Keep the current guide's point and add the SSA field-ownership
       mechanism that makes it visible. `[TRAP]`
1.20.6 `kubectl apply` vs `create` vs `replace` vs `patch` vs `apply --server-side`, and the
       "declarative until you are debugging" honesty about `kubectl scale`/`set image` in an
       incident.
1.20.7 Why "applied successfully" says almost nothing: it means the object was persisted, not that
       anything runs. The correct completion signals are `rollout status`, `observedGeneration`,
       and the object's own conditions. `[PROVE]` `[TRAP]`
1.20.8 **Conditions** as the universal status vocabulary: `type`, `status`
       (`True`/`False`/`Unknown`), `reason`, `message`, `lastTransitionTime`,
       `observedGeneration`. Reading conditions is the skill; `kubectl get -o
       jsonpath='{.status.conditions}'` is the command. `[CMD]`
1.20.9 Eventual consistency in the small: pod created → scheduled → image pulled → started →
       ready → in endpoints → in every node's proxy rules → in the load balancer target group.
       Each arrow is a separate loop with its own latency, and the sum of those latencies is why
       deploys drop requests (§2.11). `[PROVE]`
1.20.10 Where the model leaks: ordering (there is none — `kubectl apply -f dir/` does not sequence
        dependencies), cross-object transactions (there are none), and "delete the CRD and its
        controller" (finalizers wedge). `[TRAP]`

*(10 leaves)*

## §1.21 Pod: the atom

1.21.1 Definition, precisely: one or more containers that **share a network namespace (one IP, so
       `localhost` reaches each other), the IPC and UTS namespaces, and any declared volumes**,
       scheduled together on one node, living and dying together.
1.21.2 The **pause container** (`registry.k8s.io/pause`): it holds the namespaces open so app
       containers can come and go without the pod losing its IP, and it reaps zombies for the
       shared PID namespace. This is the mechanism behind "a pod has an IP". `[PROVE]` `[SOURCE]`
1.21.3 **Pods are disposable.** A pod name, a pod IP and a pod's node are all ephemeral facts.
       Never treat a pod as a server, never hardcode a pod IP, never store state on the pod's
       filesystem. Keep the current guide's framing.
1.21.4 `spec.containers[]` in full: `name`, `image`, `imagePullPolicy`, `command`, `args`,
       `workingDir`, `ports[]`, `env[]`, `envFrom[]`, `resources`, `resizePolicy`,
       `volumeMounts[]`, `volumeDevices[]`, `livenessProbe`, `readinessProbe`, `startupProbe`,
       `lifecycle`, `terminationMessagePath`, `terminationMessagePolicy`, `securityContext`,
       `stdin`, `stdinOnce`, `tty`, `restartPolicy` (container-level). `[SOURCE]` `[CFG]`
1.21.5 `command`/`args` vs `ENTRYPOINT`/`CMD`: `command` overrides `ENTRYPOINT`, `args` overrides
       `CMD`. Get this table right — it is a classic question and a classic outage
       (setting `command` and losing the entrypoint's exec wrapper). `[PROVE]` `[TRAP]`
1.21.6 **Init containers**: run to completion, in order, before app containers; each must exit 0;
       they can have their own resources and security context; their resource requests participate
       in scheduling as a max, not a sum. Use cases: schema migration, waiting for a dependency,
       `chown`ing a volume. `[PROVE]`
1.21.7 **Native sidecars**: an init container with `restartPolicy: Always` — started before the
       app, restarted independently, kept alive for the pod's lifetime, terminated **after** the
       app containers, and it no longer blocks a `Job` from completing. Beta 1.29, **GA 1.33**.
       This is how `RouterInt`-as-a-sidecar and a mesh proxy should be declared today.
       `[KEP]` `[VERSION-TRAP]` `[RESEARCH]`
1.21.8 Sidecar ordering guarantees and the failure modes they fix: the app starting before the
       proxy is ready (connection refused on boot), and the proxy dying first at shutdown
       (connection refused on drain).
1.21.9 **Ephemeral containers** (`spec.ephemeralContainers`, the `ephemeralcontainers`
       subresource): injected into a running pod for debugging, cannot have probes or ports, cannot
       be removed. The mechanism behind `kubectl debug`. `[PROVE]`
1.21.10 Pod phases — `Pending`, `Running`, `Succeeded`, `Failed`, `Unknown` — and the crucial
        clarification that **`CrashLoopBackOff` and `Terminating` are not phases**; they are
        kubectl-rendered container reasons/deletion states. `[SOURCE]` `[TRAP]`
1.21.11 Container states: `Waiting` (with `reason`: `ContainerCreating`, `ImagePullBackOff`,
        `ErrImagePull`, `CrashLoopBackOff`, `CreateContainerConfigError`,
        `CreateContainerError`, `InvalidImageName`), `Running`, `Terminated` (with `reason`:
        `Completed`, `Error`, `OOMKilled`, `ContainerStatusUnknown`, `DeadlineExceeded`).
        Memorising this list is most of pod debugging. `[SOURCE]` `[DIAG]`
1.21.12 Pod conditions: `PodScheduled`, `PodReadyToStartContainers`, `Initialized`,
        `ContainersReady`, `Ready`, `DisruptionTarget`, `PodResizePending`/`PodResizeInProgress`.
        `[SOURCE]` `[RESEARCH]`
1.21.13 **Readiness gates** (`spec.readinessGates`) — how an external controller (an AWS target
        group, a mesh) blocks pod readiness until *it* is ready, and why this is the correct fix
        for the LB-lag race in §2.11. `[CFG]` `[PROVE]`
1.21.14 **Scheduling gates** (`spec.schedulingGates`, GA 1.30): a pod that will not be considered
        for scheduling until a controller removes the gate — the hook queue-based schedulers and
        quota systems use. `[CFG]` `[RESEARCH]`
1.21.15 Pod-level fields worth naming: `serviceAccountName`, `automountServiceAccountToken`,
        `nodeSelector`, `affinity`, `tolerations`, `topologySpreadConstraints`,
        `priorityClassName`, `preemptionPolicy`, `restartPolicy`,
        `terminationGracePeriodSeconds`, `activeDeadlineSeconds`, `dnsPolicy`, `dnsConfig`,
        `hostNetwork`, `hostPID`, `hostIPC`, `hostUsers`, `shareProcessNamespace`, `hostname`,
        `subdomain`, `setHostnameAsFQDN`, `securityContext`, `imagePullSecrets`, `runtimeClassName`,
        `schedulerName`, `overhead`, `enableServiceLinks`, `os`, `resources` (pod-level). `[CFG]`
1.21.16 `enableServiceLinks: true` is the default and injects an environment variable **per Service
        in the namespace** into every container — which in a big namespace is hundreds of variables
        and a real start-up cost. Turn it off. `[TRAP]` `[NUM]`
1.21.17 The **Downward API**: `fieldRef` (`metadata.name`, `metadata.namespace`, `metadata.uid`,
        `metadata.labels`, `metadata.annotations`, `spec.nodeName`, `spec.serviceAccountName`,
        `status.podIP`, `status.hostIP`) and `resourceFieldRef`
        (`limits.cpu`, `requests.memory`, …, with `divisor`) — as env vars or as a projected
        volume. `resourceFieldRef` on `limits.memory` is the clean way to size a JVM heap without
        hardcoding. `[CFG]` `[BUILD]`
1.21.18 `terminationMessagePath` / `terminationMessagePolicy: FallbackToLogsOnError` — how a dying
        container leaves a message in `status`, and why nobody uses it and should. `[CFG]`
1.21.19 Static pods, mirror pods, and why `kubectl delete` on a mirror pod does nothing.
1.21.20 The pod template as the shared substructure of every workload controller, and
        **`spec.selector` immutability** as the reason you cannot relabel in place.
1.21.21 The single-container default and when a second container is genuinely right: sidecar
        proxy, log/metric shipper, config reloader, credential refresher, `RouterInt`. And when it
        is wrong: "one concern per container" — no supervisord running app + nginx + cron.

*(21 leaves)*

## §1.22 Workload controllers, complete

1.22.1 **ReplicaSet**: maintains N pods matching a selector, adopts and orphans by
       `ownerReferences`, and is the thing you almost never create directly.
1.22.2 **Deployment** → ReplicaSet → Pods: what each layer owns, why the indirection exists (a new
       ReplicaSet per pod-template revision is what makes rollout and rollback possible), and how a
       revision is hashed into `pod-template-hash`. `[PROVE]`
1.22.3 Deployment fields with exact defaults: `replicas` (1), `strategy.type`
       (`RollingUpdate`), `maxSurge` (**25%**, rounded up), `maxUnavailable` (**25%**, rounded
       down), `minReadySeconds` (0), `progressDeadlineSeconds` (**600**),
       `revisionHistoryLimit` (**10**), `paused`, `selector` (immutable). `[NUM]` `[CFG]`
       `[RESEARCH]`
1.22.4 **StatefulSet**: stable ordinal names (`funds-ledger-0..2`), stable per-pod PVCs, ordered
       start-up and reverse-ordered shutdown, a required headless Service. Fields:
       `serviceName`, `volumeClaimTemplates`, `podManagementPolicy`
       (`OrderedReady` default / `Parallel`), `updateStrategy.type`
       (`RollingUpdate` default / `OnDelete` / **`Recreate` new in 1.37**),
       `rollingUpdate.partition` (0), `rollingUpdate.maxUnavailable` (1.24+),
       `persistentVolumeClaimRetentionPolicy.whenDeleted`/`whenScaled` (both `Retain`),
       `ordinals.start` (stable 1.31), `minReadySeconds` (0), `revisionHistoryLimit` (10).
       `[NUM]` `[CFG]` `[RESEARCH]`
1.22.5 **DaemonSet**: one pod per matching node, `updateStrategy` `RollingUpdate` (with
       `maxUnavailable` 1, `maxSurge`) or `OnDelete`, automatic tolerations for the node taints,
       and the priority class `system-node-critical`. Used for log shippers, metric agents, CNI,
       CSI node plugins, and `RouterInt` if you run it as a node-local proxy tier. `[CFG]`
1.22.6 **Job**: `completions`, `parallelism`, `backoffLimit` (**6**),
       `activeDeadlineSeconds`, `ttlSecondsAfterFinished`, `completionMode`
       (`NonIndexed`/`Indexed`), `podFailurePolicy`, `backoffLimitPerIndex`,
       `maxFailedIndexes`, `suspend`, `managedBy`, and the `successPolicy`. Plus the 1.34 change
       that made the controller distinguish **active vs failed vs terminating** pods with a
       `status.terminating` field and configurable pod replacement. `[NUM]` `[CFG]` `[RESEARCH]`
1.22.7 **CronJob**: `schedule` (with the timezone field `timeZone`, stable 1.27),
       `concurrencyPolicy` (`Allow`/`Forbid`/`Replace`), `startingDeadlineSeconds`,
       `suspend`, `successfulJobsHistoryLimit` (**3**), `failedJobsHistoryLimit` (**1**), and the
       **100-missed-schedules** rule that silently stops a CronJob forever. **CronJob is
       at-least-once**, so the job body must be idempotent. `[NUM]` `[TRAP]` `[X-REF 14]`
1.22.8 The QuizStakes application of that: the `BankWithdrawal` payment run **must not run twice**;
       therefore a CronJob alone is insufficient and the design is "central scheduler + leader
       election + a distributed lock", exactly as Appendix B.4 says. Work the failure case where
       `concurrencyPolicy: Allow` plus a slow run double-pays. `[PROVE]` `[TRAP]`
1.22.9 **ReplicationController** as the pre-ReplicaSet legacy object, and why you will still see it
       in old tutorials.
1.22.10 The **`scale` subresource** as the uniform interface that HPA, `kubectl scale` and custom
        autoscalers use — and why a DaemonSet has none and cannot be HPA'd. `[PROVE]`
1.22.11 `ControllerRevision` as the mechanism behind StatefulSet/DaemonSet history, vs
        ReplicaSets for Deployments.
1.22.12 Which controller for which QuizStakes service, with the reason: Deployment for every
        stateless service; StatefulSet only where identity or per-instance storage is real (the
        ledger's partition affinity is *routing*, not storage, so it is still a Deployment plus a
        consistent-hash router — argue it); DaemonSet for the log/metric agents; Job for
        migrations; CronJob + leader election for the withdrawal run. `[PROVE]`
1.22.13 Advanced/third-party workload shapes worth naming: **Argo Rollouts** (blue-green and
        canary as a CRD), **Argo Workflows**, **KubeVirt**, **Kueue** and gang scheduling, and the
        1.37 workload-aware scheduling work. `[RESEARCH]`

*(13 leaves)*

## §1.23 Services, EndpointSlices, and service discovery

1.23.1 The problem a Service solves: pods are ephemeral and their IPs change, so callers need a
       stable name and address plus load spreading. The Service is that indirection, and the
       indirection *is* the point.
1.23.2 `ClusterIP`: a **virtual IP that nothing owns** — no interface has it, no process listens on
       it; it exists only as packet-rewriting rules on every node. Proving this to yourself
       (`ping` a ClusterIP fails while `curl` works) is the fastest way to understand
       Kubernetes networking. `[PROVE]` `[TRAP]`
1.23.3 The types: `ClusterIP` (default), `NodePort` (**30000–32767** by default, allocated per
       Service, and a NodePort Service *also* gets a ClusterIP), `LoadBalancer` (provisions a cloud
       LB and is a superset of NodePort), `ExternalName` (a CNAME, no proxying, no selector).
       `[NUM]` `[CFG]`
1.23.4 **Headless Services** (`clusterIP: None`): DNS returns the pod IPs directly, no proxying, no
       load balancing. The right choice for a client that does its own balancing or needs per-pod
       addressing — StatefulSets, and any partition-affine client like `FundsLedger`'s router.
       `[PROVE]`
1.23.5 Service spec fields: `selector`, `ports[]` (`name`, `port`, `targetPort` — number or
       **named port**, `protocol`, `nodePort`, `appProtocol`), `clusterIP`, `clusterIPs`,
       `ipFamilies`, `ipFamilyPolicy`, `sessionAffinity` + `sessionAffinityConfig.clientIP.timeoutSeconds`
       (**10800**), `externalTrafficPolicy`, `internalTrafficPolicy`,
       `publishNotReadyAddresses`, `allocateLoadBalancerNodePorts`,
       `loadBalancerClass`, `trafficDistribution`, `externalIPs` (**deprecated 1.36**),
       `healthCheckNodePort`. `[NUM]` `[CFG]` `[RESEARCH]`
1.23.6 A **Service with no selector** plus manually managed EndpointSlices as the way to front an
       external database or a legacy VM with a cluster-internal name.
1.23.7 **EndpointSlice** (`discovery.k8s.io/v1`) replaced `Endpoints`: why (one 5000-pod Service
       was one giant object rewritten on every pod change, melting the apiserver and every
       kube-proxy), the **100-endpoint default slice size**, `endpoints[].conditions`
       (`ready`, `serving`, `terminating`), `hints.forNodes` for topology, and the
       `kubernetes.io/service-name` label. `Endpoints` is deprecated as of 1.33. `[NUM]` `[PROVE]`
       `[VERSION-TRAP]` `[RESEARCH]`
1.23.8 The distinction `ready` vs `serving` vs `terminating` and why it exists: a terminating pod
       can still serve in-flight requests, which is what lets `externalTrafficPolicy: Local` avoid
       black-holing during a rollout. `[PROVE]`
1.23.9 `externalTrafficPolicy: Cluster` vs `Local`: SNAT and lost client IP vs preserved client IP
       with imbalanced load and the `healthCheckNodePort` mechanism. Give the decision rule.
       `[PROVE]`
1.23.10 `internalTrafficPolicy: Local` for node-local traffic, and where it is a genuine latency
        win (a node-local `RouterInt` or cache sidecar).
1.23.11 **Topology-aware routing** (`service.kubernetes.io/topology-mode: Auto`, formerly
        `topology-aware-hints`) and the newer `spec.trafficDistribution`
        (`PreferClose`, `PreferSameZone`, `PreferSameNode`) — keeping traffic in-AZ to cut
        cross-AZ data-transfer cost and latency. `[CFG]` `[X-REF 18]` `[RESEARCH]`
1.23.12 `sessionAffinity: ClientIP` and why it is a poor substitute for real stickiness (it is a
        source-IP hash, so everything behind one NAT is one client) — relevant to
        `InternalPlatforms`, which is session-affine.
1.23.13 Dual-stack: `ipFamilyPolicy` `SingleStack`/`PreferDualStack`/`RequireDualStack`. `[CFG]`
1.23.14 Service discovery as DNS: `client-restrictions` within a namespace,
        `client-restrictions.quizstakes-money.svc.cluster.local` across. Full DNS treatment in
        §2.18 and §3.19.
1.23.15 The legacy environment-variable discovery (`CLIENT_RESTRICTIONS_SERVICE_HOST`) — where it
        comes from, why it is ordering-dependent and therefore useless, and `enableServiceLinks:
        false`. `[TRAP]`
1.23.16 Service topology at scale: how many iptables/nftables rules 400 Services × 8 endpoints
        produces, and why that number is the reason nftables exists. `[NUM]` `[PROVE]`

*(16 leaves)*

## §1.24 Ingress, Gateway API, and L7 entry

1.24.1 Why a Service is not enough for HTTP: one cloud LB per Service is expensive, and
       host/path routing, TLS termination, header manipulation, and rewrites are L7 concerns.
1.24.2 **Ingress** (`networking.k8s.io/v1`): `ingressClassName`, `rules[].host`,
       `rules[].http.paths[]` with `pathType` (`Exact`/`Prefix`/`ImplementationSpecific`),
       `backend.service.name`/`port`, `defaultBackend`, `tls[]` with `secretName`. Plus
       `IngressClass` and the `ingressclass.kubernetes.io/is-default-class` annotation. `[CFG]`
1.24.3 Why Ingress stalled: everything beyond basic routing was vendor annotations, so an Ingress
       manifest was not portable in practice. `nginx.ingress.kubernetes.io/*` as the canonical
       example. The API is **frozen** — it will not gain features. `[PROVE]`
1.24.4 **`ingress-nginx` reached end of life on 24 March 2026.** No features, no bugfixes, **no CVE
       patches**; existing deployments keep working; `InGate`, the intended successor, was also
       retired. This is the single most important operational fact in this section, and it
       invalidates the current guide's parenthetical. `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
1.24.5 The migration options, compared: **Envoy Gateway**, **NGINX Gateway Fabric**, **Traefik**,
       **HAProxy**, **Kong**, **kgateway/Gloo**, **Istio**, **Cilium**, and the cloud-native
       controllers (AWS Load Balancer Controller, GKE Gateway). `[RESEARCH]`
1.24.6 **Gateway API** — the role-oriented model that replaced Ingress: `GatewayClass`
       (infrastructure operator), `Gateway` (cluster operator: listeners, ports, TLS, allowed
       routes), `HTTPRoute`/`GRPCRoute`/`TLSRoute`/`TCPRoute`/`UDPRoute` (application developer).
       Explain the three-persona split as the actual design innovation. `[SOURCE]`
1.24.7 The `HTTPRoute` surface: `parentRefs`, `hostnames`, `rules[].matches` (path, header, query
       param, method), `rules[].filters` (`RequestHeaderModifier`,
       `ResponseHeaderModifier`, `RequestRedirect`, `URLRewrite`, `RequestMirror`, **`CORS`
       (Standard in 1.5)**, `ExtensionRef`), `backendRefs` with **weights** (the mechanism for
       canary and blue-green without a third-party controller), `timeouts`
       (`request`, `backendRequest`), `retry`, `sessionPersistence`. `[CFG]` `[RESEARCH]`
1.24.8 The policy attachment objects: `BackendTLSPolicy` (**Standard since 1.4**),
       `BackendLBPolicy`, `ReferenceGrant` (**Standard in 1.5** — the cross-namespace consent
       mechanism), `ListenerSet` (**Standard in 1.5**), plus client-certificate validation and
       certificate selection for TLS origination. `[RESEARCH]`
1.24.9 **GAMMA**: the same route objects bound to a Service instead of a Gateway, giving
       mesh east-west routing a standard API. `[RESEARCH]`
1.24.10 Gateway API release mechanics: channels **Standard** vs **Experimental**, the CRDs shipped
        separately from Kubernetes, the **release-train model adopted in v1.5**, and version
        compatibility with controllers. `[RESEARCH]`
1.24.11 `ingress2gateway` **1.0** (Mar 2026) — reads existing Ingress objects and emits `Gateway` +
        `HTTPRoute`, and the annotations it cannot translate. `[CMD]` `[RESEARCH]`
1.24.12 The QuizStakes entry design: one `Gateway` in `quizstakes-ops` terminating TLS, an
        `HTTPRoute` per public surface (`/api/onboarding`, `/api/payments`, `/api/balance`),
        `ReferenceGrant`s from `quizstakes-money` and `quizstakes-onboarding`, weighted
        `backendRefs` for the `application-gateway` canary, and **card-data egress isolation**
        (only `card-payments` may reach the PSP) expressed as NetworkPolicy rather than routing.
        `[BUILD]` `[YAML]`
1.24.13 Where the cloud LB fits: `Service type=LoadBalancer` with a target-group per Service vs one
        `Gateway`/ALB fronting many routes; the AWS Load Balancer Controller's IP vs instance
        target mode and why IP mode plus readiness gates is what fixes deploy-time 502s.
        `[X-REF 18]` `[PROVE]`
1.24.14 TLS: `Secret` of type `kubernetes.io/tls`, cert-manager `Certificate`/`Issuer`, SNI-based
        listener selection, and mTLS at the edge vs in the mesh. `[X-REF 13]`

*(14 leaves)*

## §1.25 Configuration: ConfigMap, Secret, and the injection surface

1.25.1 `ConfigMap`: `data` (UTF-8) and `binaryData` (base64), the **~1 MiB practical limit** from
       the etcd request size, and `immutable: true` (which both prevents accidental change and
       stops the kubelet watching it — a real apiserver-load win at scale). `[NUM]` `[CFG]`
1.25.2 The three injection mechanisms and how each behaves on update: **env var from
       `valueFrom.configMapKeyRef`** (snapshot at start; never updates), **`envFrom`** (same),
       **volume mount** (updated by the kubelet, eventually — default sync period 60 s plus cache
       TTL, so up to ~1–2 minutes), **volume mount with `subPath`** (**never updates**).
       This table is the whole topic. `[PROVE]` `[TRAP]` `[NUM]`
1.25.3 Therefore: a ConfigMap change does not restart your pods and does not reach your
       environment variables. The fixes: a checksum annotation on the pod template
       (`checksum/config: {{ … | sha256sum }}`), Reloader/Stakater, Spring Cloud Kubernetes config
       watch, or `immutable: true` + a new name per version. `[TRAP]` `[BUILD]`
1.25.4 `Secret`: `data` (base64) vs `stringData` (write-only convenience), the built-in types
       (`Opaque`, `kubernetes.io/service-account-token`, `kubernetes.io/dockerconfigjson`,
       `kubernetes.io/basic-auth`, `kubernetes.io/ssh-auth`, `kubernetes.io/tls`,
       `bootstrap.kubernetes.io/token`), `immutable`. `[CFG]`
1.25.5 **Secrets are base64-encoded, not encrypted.** Anyone with `get secrets` in the namespace
       reads them; without encryption at rest they are plaintext in etcd; and `kubectl describe`
       hides them only cosmetically. Keep the current guide's warning and give the three real
       mitigations: **encryption at rest with a KMS provider**, tight RBAC, and not putting the
       secret in the cluster at all (§2.21). `[TRAP]` `[PROVE]`
1.25.6 Secrets as env vars vs as files: files are better (no leak via `/proc/<pid>/environ`, no
       leak into crash dumps or child processes, and they can be rotated). `[PROVE]`
1.25.7 `projected` volumes: combining `configMap`, `secret`, `downwardAPI` and
       `serviceAccountToken` (with `audience` and `expirationSeconds`) into one directory —
       the mechanism behind bound service account tokens and IRSA. `[CFG]` `[X-REF 18]`
1.25.8 Spring Boot's consumption of all this: `SPRING_APPLICATION_JSON`, relaxed binding of
       `SPRING_DATASOURCE_URL`, `spring.config.import=configtree:/etc/config/`,
       `--spring.config.additional-location`, and profile activation via
       `SPRING_PROFILES_ACTIVE`. Show the exact mapping from a ConfigMap key to an
       `@ConfigurationProperties` field. `[BUILD]` `[X-REF 07]`
1.25.9 The Appendix B.4 rule this section must respect: **configuration is versioned and promoted
       through environments, never edited in place** — which rules out `kubectl edit configmap` as
       a workflow and argues for immutable, name-versioned ConfigMaps in Git.
1.25.10 What must never be a ConfigMap: the PSP vendor credential, the token signing key, the
        database password. Appendix B.4 puts those in a managed secret store, rotated, never in
        config or environment. `[X-REF 13]`

*(10 leaves)*

## §1.26 Namespaces, labels, annotations, selectors

1.26.1 What a `Namespace` actually partitions: object names, RBAC scope, `ResourceQuota` and
       `LimitRange` scope, NetworkPolicy scope, and the DNS second label. What it does **not**
       partition: nodes, PVs, StorageClasses, ClusterRoles, CRDs, or the pod network by default.
       `[PROVE]` `[TRAP]`
1.26.2 The default namespaces and their jobs: `default`, `kube-system`, `kube-public`,
       `kube-node-lease`.
1.26.3 Namespace deletion mechanics and the `Terminating` wedge: the namespace controller, the
       `kubernetes` finalizer, and orphaned CRD instances whose controller is gone. `[DIAG]`
1.26.4 Namespace strategy, argued: per-team, per-environment, per-service, per-tenant — and the
       QuizStakes choice (`quizstakes-money`, `quizstakes-onboarding`, `quizstakes-ops`) justified
       by blast radius, quota boundaries, and the card-data isolation requirement.
1.26.5 **Labels** are for selection: `matchLabels` (equality) and `matchExpressions`
       (`In`, `NotIn`, `Exists`, `DoesNotExist`), the 63-character value limit, and the
       recommended `app.kubernetes.io/*` label set (`name`, `instance`, `version`, `component`,
       `part-of`, `managed-by`). `[CFG]` `[NUM]`
1.26.6 **Annotations** are for data no selector needs: arbitrary size (up to the 256 KiB total
       limit), used by controllers and tools —
       `kubernetes.io/change-cause`, `deployment.kubernetes.io/revision`,
       `kubectl.kubernetes.io/last-applied-configuration`, `prometheus.io/scrape`, cloud LB
       configuration, `checksum/config`. `[NUM]` `[CFG]`
1.26.7 The auto-applied labels worth knowing: `kubernetes.io/metadata.name` on namespaces (the one
       that makes "select a namespace by name" possible in a NetworkPolicy),
       `pod-template-hash`, `apps.kubernetes.io/pod-index`, `statefulset.kubernetes.io/pod-name`,
       and the well-known node labels (`kubernetes.io/hostname`, `topology.kubernetes.io/zone`,
       `topology.kubernetes.io/region`, `node.kubernetes.io/instance-type`,
       `kubernetes.io/arch`, `kubernetes.io/os`). `[CFG]` `[RESEARCH]`
1.26.8 The label-selector commands: `kubectl get pods -l 'app.kubernetes.io/part-of=quizstakes,
       app.kubernetes.io/component!=batch'`, `--field-selector`, `--show-labels`, `kubectl label`.
       `[CMD]`
1.26.9 **Trap:** changing a Deployment's pod labels so they no longer match its selector — the
       selector is immutable, and if you get it wrong you get orphaned pods and a
       double-serving fleet. `[TRAP]`
1.26.10 Field selectors and their limits (only a handful of indexed fields:
        `metadata.name`, `metadata.namespace`, `spec.nodeName`, `status.phase`) — and why
        `--field-selector spec.nodeName=…,status.phase=Running` is the fast way to list what a
        sick node is running. `[CMD]`

*(10 leaves)*

## §1.27 Probes: liveness, readiness, startup

1.27.1 The framing that makes the distinction stick: **the question differs, but what matters is
       who acts on the answer and what they do.** Liveness → kubelet restarts the container.
       Readiness → the EndpointSlice controller removes the address. Startup → the kubelet gates
       the other two. Keep the current guide's table and expand each row into a mechanism.
1.27.2 The probe handler types: `httpGet` (with `path`, `port`, `host`, `scheme`, `httpHeaders`),
       `tcpSocket`, `exec` (with `command`), and `grpc` (with `port`, `service` — GA 1.27, using
       the standard gRPC Health Checking Protocol). `[CFG]` `[RESEARCH]`
1.27.3 Every timing field with its **exact default**: `initialDelaySeconds` **0**,
       `periodSeconds` **10**, `timeoutSeconds` **1**, `successThreshold` **1**
       (and it must be 1 for liveness and startup), `failureThreshold` **3**,
       `terminationGracePeriodSeconds` (probe-level override). `[NUM]` `[CFG]` `[SOURCE]`
1.27.4 The detection-time arithmetic nobody does:
       worst-case detection = `initialDelaySeconds + periodSeconds × failureThreshold +
       timeoutSeconds`. Work it for the defaults (≈31 s) and for a
       `client-restrictions` pod on a 30 ms budget. `[NUM]` `[PROVE]`
1.27.5 **`timeoutSeconds: 1` is the default and it is wrong for a JVM.** If your endpoint's p99
       under load exceeds 1 s, the kubelet restarts your pods precisely when you are busiest —
       a positive feedback loop into a full outage. `[TRAP]` `[PROVE]`
1.27.6 **Readiness is the one you use most**: it is temporary and reversible, so a pod warming a
       cache, draining, or briefly overloaded stops receiving traffic and resumes. Nothing is
       destroyed. `[X-REF 15]`
1.27.7 **Liveness is a last resort**, for states a restart genuinely fixes: a deadlock, a wedged
       event loop, an unrecoverable internal error. **If a restart would not fix it, liveness must
       not detect it.** `[PROVE]`
1.27.8 **The dependency-storm trap, in full.** Dependency checks in liveness: the ledger database
       blips for 30 s → every pod's liveness fails → Kubernetes kills the entire fleet
       simultaneously → they restart, fail again because the database is still recovering, and now
       it is recovering while being hammered by a hundred reconnecting pods with cold caches. A
       30-second dependency blip becomes a self-sustaining outage. **Restarting your pod does not
       fix someone else's database.** Keep the current guide's paragraph essentially verbatim and
       add the QuizStakes numbers. `[TRAP]` `[PROVE]`
1.27.9 **The readiness caveat**: a hard dependency check in readiness takes the Service to **zero
       endpoints** and you are fully down — even though you might have degraded gracefully.
       Distinguish **hard** dependencies (no ledger database → `funds-ledger` genuinely cannot
       serve) from **soft** (no Redis → `balance-view` can serve slowly). Only hard dependencies
       belong in readiness. `[TRAP]` `[PROVE]`
1.27.10 The special case that makes this concrete: `client-restrictions` must **never** report
        ready-but-lying, because invariant 12 says restriction decisions are read live. Work out
        what its readiness probe may and may not check. `[PROVE]`
1.27.11 **Startup probes** exist so liveness can be aggressive: use `periodSeconds: 10,
        failureThreshold: 30` for a 5-minute JVM boot budget, and set liveness
        `initialDelaySeconds: 0`. A huge `initialDelaySeconds` on liveness instead means real
        failures go undetected for minutes. `[NUM]` `[PROVE]`
1.27.12 Spring Boot's native support: `management.endpoint.health.probes.enabled=true` (automatic
        in Kubernetes), `/actuator/health/liveness`, `/actuator/health/readiness`,
        `management.endpoint.health.group.*`, `LivenessState`/`ReadinessState`
        `AvailabilityChangeEvent`, and the fact that readiness automatically reports
        `OUT_OF_SERVICE` during graceful shutdown — which is exactly what you want.
        `[CFG]` `[BUILD]` `[X-REF 07]`
1.27.13 Composing the right Spring health indicators into each group: `db`, `redis`, `diskSpace`,
        `ping`, and custom ones — with the explicit exclusion of downstream HTTP checks from
        liveness. `[BUILD]`
1.27.14 The other probe mistakes, each with its symptom: an expensive probe endpoint (the probe
        becomes the load); an authenticated probe endpoint (the kubelet is unauthenticated); a
        probe on a port the app has not bound yet; an `exec` probe that forks a JVM
        (`CreateContainerError` under `pids.max`, and enormous CPU cost); a probe that returns 200
        while the app is broken (a static `/health` file). `[TRAP]` `[DIAG]`
1.27.15 Probes and the **PID budget**: an `exec` probe every 10 s on 40 `application-gateway` pods
        is 4 process spawns per second; `httpGet` costs nothing comparable. `[NUM]`
1.27.16 Probes and sidecars: a native sidecar can have its own probes, and its readiness
        participates in the pod's `ContainersReady`, so a broken `RouterInt` sidecar correctly
        takes the pod out of rotation. `[PROVE]`
1.27.17 What probes do **not** do: they do not check the whole pod (they are per-container), they
        do not run during termination in a way you can rely on, and Docker's `HEALTHCHECK` is
        ignored entirely. `[TRAP]`

*(17 leaves)*

## §1.28 Requests, limits, and QoS

1.28.1 `resources.requests` is a **scheduling contract**: the scheduler finds a node whose
       *allocatable* minus the sum of *requests* of pods already there leaves room. It is not a
       runtime guarantee of anything except the cgroup weight. `[PROVE]`
1.28.2 `resources.limits` is a **runtime ceiling enforced by the kernel** — and CPU and memory
       are enforced by completely different mechanisms with completely different consequences.
1.28.3 The asymmetry table, which is the heart of the section: over the CPU limit → **CFS
       throttling**, the container is stopped for the remainder of the 100 ms period, causing
       latency spikes and no crash, automatically recoverable. Over the memory limit →
       **OOMKill**, the kernel terminates the process instantly, exit **137**, restart, possibly
       `CrashLoopBackOff`, not recoverable. Keep the current guide's table and prove each cell.
       `[PROVE]` `[NUM]`
1.28.4 **Memory is incompressible; CPU is compressible.** That single sentence generates the
       standard guidance. `[PROVE]`
1.28.5 CPU units: `1` = one full core/vCPU/hyperthread; `500m` = 500 millicpu; the minimum
       meaningful precision is `1m`. Memory units: bytes with SI (`K`/`M`/`G`, powers of 1000) or
       binary (`Ki`/`Mi`/`Gi`, powers of 1024) suffixes — and **`1G ≠ 1Gi`** (a 7.4% difference
       that has caused real OOMKills). `[NUM]` `[TRAP]`
1.28.6 The **QoS classes** and their exact definitions: **Guaranteed** (every container has
       requests == limits for both CPU and memory), **Burstable** (at least one request set, not
       Guaranteed), **BestEffort** (no requests or limits anywhere). Read from
       `status.qosClass`. `[PROVE]` `[CFG]`
1.28.7 What QoS decides: eviction order under node pressure, `oom_score_adj` (§1.4.10), and CPU
       manager static-policy eligibility. It does **not** decide scheduling priority — that is
       `PriorityClass`. `[TRAP]`
1.28.8 The default-request rule: **if you set a limit and no request, the request is set equal to
       the limit.** Which means a "limits-only" manifest silently produces Guaranteed QoS and
       potentially enormous requests. `[PROVE]` `[TRAP]` `[RESEARCH]`
1.28.9 The guidance, argued: **always set a memory limit, and set `requests.memory ==
       limits.memory`** so the pod is Guaranteed and last to be evicted. Memory
       overcommitment does not degrade — it kills.
1.28.10 **CPU limits are contentious, and the bible must take a position.** Setting one means
        throttling even on an idle node; many teams set CPU *requests* only and let pods burst.
        Set CPU limits when you need hard multi-tenant isolation or predictable per-pod
        performance; otherwise consider omitting them. Then give the counter-argument (noisy
        neighbours, unpredictable capacity planning, HPA behaviour) honestly. `[PROVE]`
1.28.11 `resources.claims` and **Dynamic Resource Allocation** (`resource.k8s.io`): the successor
        to device plugins for GPUs and accelerators, with `ResourceClaim`, `DeviceClass`,
        `ResourceSlice`, and **partitionable devices in 1.36**. Name it; a backend engineer needs
        to recognise it, not use it. `[KEP]` `[RESEARCH]`
1.28.12 `ephemeral-storage` requests and limits: what counts (writable layer, `emptyDir`, container
        logs), and that exceeding the limit gets the **pod evicted**, not OOMKilled. `[PROVE]`
1.28.13 `hugepages-2Mi` / `hugepages-1Gi`: cannot be overcommitted; request must equal limit.
1.28.14 **Pod-level `spec.resources`** (beta, default-on since **1.34**, gate `PodLevelResources`)
        for `cpu`, `memory`, `hugepages-<size>`: one budget for a multi-container pod with sharing
        between containers, and how it interacts with container-level values and QoS.
        `[KEP]` `[VERSION-TRAP]` `[RESEARCH]`
1.28.15 **In-place resize**: the `pods/resize` subresource (**GA 1.35**), `resizePolicy` per
        resource (`NotRequired` / `RestartContainer`) which is **immutable after pod creation**,
        the pod conditions `PodResizePending` (`Deferred`/`Infeasible`) and `PodResizeInProgress`,
        and why `NotRequired` is safe for CPU but `RestartContainer` is the honest default for
        memory. `[KEP]` `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
1.28.16 `LimitRange` (per-namespace defaults, min, max, and `maxLimitRequestRatio`) and
        `ResourceQuota` (aggregate `requests.cpu`, `limits.memory`, object counts, `scopes` and
        `scopeSelector`) — and the trap that **a ResourceQuota on `requests.cpu` makes requests
        mandatory**, so previously-working pods start failing admission. `[CFG]` `[TRAP]`
1.28.17 Reading actual usage vs configured values: `kubectl top pod --containers`,
        `kubectl describe node` (the Allocated resources table with percentages),
        `container_memory_working_set_bytes` vs `container_memory_usage_bytes` (the latter
        includes reclaimable page cache and is the wrong metric — **the OOM killer uses working
        set**). `[PROVE]` `[TRAP]` `[X-REF 20]`
1.28.18 Right-sizing procedure: set requests from observed p50–p90, limits from observed peak plus
        headroom, then verify throttling is zero and OOMKills are zero. Apply it to
        `client-restrictions` (4 GB heap × 8, extreme rate, trivial objects) and
        `document-verification` (8 GB heap × 6, 2–6 MB buffers). `[NUM]` `[PROVE]`

*(18 leaves)*

## §1.29 Storage in Kubernetes

1.29.1 The three-object model: **StorageClass** (the "kind of storage" and its provisioner),
       **PersistentVolumeClaim** (the workload's request), **PersistentVolume** (the actual
       volume). The claim/volume split exists so a developer never names a disk.
1.29.2 Static vs **dynamic provisioning**, and the `DefaultStorageClass` admission plugin plus the
       `storageclass.kubernetes.io/is-default-class` annotation.
1.29.3 PV phases: `Available`, `Bound`, `Released`, `Failed`, and `Terminating` under a finalizer.
       `[SOURCE]`
1.29.4 **Access modes** with their short names and their real meanings: `ReadWriteOnce` (RWO — one
       *node*, not one pod), `ReadOnlyMany` (ROX), `ReadWriteMany` (RWX),
       `ReadWriteOncePod` (RWOP — genuinely one pod, GA 1.29). The RWO-means-node misunderstanding
       is a classic. `[TRAP]` `[PROVE]`
1.29.5 **Reclaim policies**: `Retain` (the default for statically created PVs; data survives,
       manual cleanup), `Delete` (the usual dynamic default; the disk goes away with the PVC),
       `Recycle` (deprecated). The `Delete`-plus-`kubectl delete pvc` accident that loses a
       database. `[TRAP]`
1.29.6 **`volumeBindingMode`**: `Immediate` vs **`WaitForFirstConsumer`** — and why WFFC is
       mandatory for zonal disks, because binding before scheduling can put an `eu-west-1a` disk
       under a pod the scheduler wants in `eu-west-1b`. `[PROVE]` `[TRAP]`
1.29.7 `volumeMode`: `Filesystem` (default) vs `Block` with `volumeDevices`/`devicePath`.
1.29.8 `allowVolumeExpansion` and online expansion: edit `spec.resources.requests.storage`, the
       `FileSystemResizePending` condition, and that **shrinking is impossible**. `[CFG]`
1.29.9 StorageClass fields: `provisioner`, `parameters` (driver-specific — `type: gp3`, `iops`,
       `throughput`, `encrypted`, `kmsKeyId`), `reclaimPolicy`, `volumeBindingMode`,
       `allowVolumeExpansion`, `mountOptions`, `allowedTopologies`. `[CFG]` `[X-REF 18]`
1.29.10 **PVC protection**: the `kubernetes.io/pvc-protection` finalizer keeps a PVC in
        `Terminating` while a pod still uses it — and the corresponding PV protection.
1.29.11 Snapshots and clones: `VolumeSnapshotClass`, `VolumeSnapshot`, `VolumeSnapshotContent`, and
        `dataSource`/`dataSourceRef` on a PVC to restore from a snapshot or clone a PVC. Plus
        **Volume Group Snapshots (GA 1.36)** for crash-consistent multi-volume snapshots.
        `[RESEARCH]`
1.29.12 `VolumeAttributesClass` for changing QoS attributes (IOPS tier) on an existing volume.
        `[RESEARCH]`
1.29.13 `ephemeral.volumeClaimTemplate` (generic ephemeral volumes): a per-pod, dynamically
        provisioned, deleted-with-the-pod volume — the right shape for
        `document-verification`'s scratch space for 2–6 MB image processing.
1.29.14 `local` PVs and `nodeAffinity`: real disks, real performance, no rescheduling. When that
        trade is correct and when it is a trap.
1.29.15 **StatefulSet + `volumeClaimTemplates`**: one PVC per ordinal, `<template>-<set>-<ordinal>`
        naming, retained on scale-down by default, reattached to the same ordinal on
        reschedule — and `persistentVolumeClaimRetentionPolicy` to change that. `[PROVE]`
1.29.16 The honest position on databases in Kubernetes: the QuizStakes ledger is a relational
        database on its own instance (Appendix B.2) and there is no operational reason to move it
        into the cluster; operators (CloudNativePG, Zalando/Crunchy Postgres, Strimzi for Kafka)
        make it *possible*, and RDS makes it *someone else's problem*. Give the decision rule.
        `[X-REF 18]` `[X-REF 09]`
1.29.17 Debugging storage: `kubectl describe pvc`/`pv`, `FailedMount`/`FailedAttachVolume`
        events, `Multi-Attach error for volume`, the CSI node plugin's logs, and the
        "pod stuck in `ContainerCreating` for 4 minutes" AWS attach-detach timeout. `[DIAG]`

*(17 leaves)*

## §1.30 kubectl: the working surface

1.30.1 **Orientation before anything else**: `kubectl config get-contexts`,
       `current-context`, `use-context`, `set-context --current --namespace=…`,
       `kubectl cluster-info`, `kubectl version`. And the habit: **check your context before every
       destructive command** — deleting in prod because the context was left there yesterday is a
       real, common incident. Keep the current guide's warning. `[CMD]` `[TRAP]`
1.30.2 `kubeconfig` structure: `clusters`, `users`, `contexts`, `current-context`; `KUBECONFIG`
       with multiple colon-separated files; `exec` credential plugins (`aws eks get-token`,
       `gke-gcloud-auth-plugin`). `[CFG]`
1.30.3 Reading: `get` with `-o wide|yaml|json|name|jsonpath|go-template|custom-columns|kyaml`,
       `--sort-by`, `-l`, `--field-selector`, `-A`, `--watch`, `--show-labels`. The
       `-o jsonpath` recipes worth memorising (all container images in a namespace; every pod's
       node; every pod's restart count). `[CMD]`
1.30.4 **KYAML** (`-o kyaml`, beta 1.35): an opinionated, quote-everything, comment-preserving
       YAML dialect designed to remove YAML's ambiguity footguns (the Norway problem, octal-looking
       strings). `[VERSION-TRAP]` `[RESEARCH]`
1.30.5 `describe` — and the instruction that carries the most diagnostic weight in the whole
       guide: **the Events section at the bottom is what you read first.** `[CMD]`
1.30.6 `logs` with `-f`, `--tail`, `--since`, `--since-time`, `--timestamps`, `-c`,
       `--all-containers`, `-l` (by label, across pods), `--prefix`, and **`--previous` for the
       crashed container's output**. `[CMD]`
1.30.7 `events` as a first-class command: `kubectl events --for pod/…`,
       `--types=Warning`, `-w`, and `kubectl get events --sort-by=.lastTimestamp` for older
       clusters — with the 1-hour retention caveat. `[CMD]` `[TRAP]`
1.30.8 `exec -it … -- sh`, `attach`, `cp` (both directions, and its `tar`-in-the-container
       requirement that breaks on distroless), `port-forward` (pod, Service, or Deployment;
       `:0` for a random local port), `proxy`. `[CMD]`
1.30.9 **`kubectl debug`** in its three modes: `--image=… --target=<container>` (ephemeral
       container sharing namespaces — for distroless pods), `--copy-to=… --set-image=…`
       (a debug copy with a changed image or command), and `node/<name>` (a privileged pod in the
       host namespaces). This is the modern answer to "I cannot get a shell". `[CMD]` `[PROVE]`
1.30.10 Writing: `apply -f|-k|-R`, `--server-side --force-conflicts`, `--dry-run=client|server`,
        `--prune`, `diff`, `create`, `replace --force`, `patch --type=…`, `edit`, `delete`
        (`--grace-period`, `--force`, `--cascade=background|foreground|orphan`,
        `--wait`), `label`, `annotate`, `taint`, `cordon`/`uncordon`, `drain`. `[CMD]`
1.30.11 **`kubectl diff`** as the pre-flight you should run every time, and `--dry-run=server` as
        the way to get real admission-webhook validation without applying. `[CMD]`
1.30.12 Rollout: `rollout status` (with `--timeout`, and its non-zero exit as a CI gate),
        `rollout history [--revision=N]`, `rollout undo [--to-revision=N]`, `rollout restart`
        (the correct way to force a pod refresh after a Secret change), `rollout pause`/`resume`.
        `[CMD]`
1.30.13 `scale [--replicas] [--current-replicas]`, `autoscale`, `set image`, `set env`,
        `set resources`, `set serviceaccount`. `[CMD]`
1.30.14 `top pod [--containers] [--sort-by=cpu|memory]`, `top node`, and that both require
        **metrics-server** — the reason `top` fails on a fresh cluster. `[CMD]` `[DIAG]`
1.30.15 `auth can-i`, `auth can-i --list`, `auth can-i --as=system:serviceaccount:ns:name`,
        `auth whoami` — the fastest way to answer an RBAC question. `[CMD]`
1.30.16 `api-resources`, `api-versions`, `explain <kind>.<path> --recursive`,
        `kubectl get --raw /metrics`, `kubectl get --raw /readyz?verbose`. `[CMD]`
1.30.17 `wait --for=condition=Ready --timeout=120s`, `--for=jsonpath=…`,
        `--for=delete` — the scriptable synchronisation primitive. `[CMD]`
1.30.18 Ergonomics that pay for themselves in a week: `alias k=kubectl`, `kubectl completion`,
        `kubens`/`kubectx`, `stern`, `k9s`, `kubecolor`, `kube-ps1` showing context in the prompt,
        `krew` and the plugins worth having (`kubectl neat`, `ktop`, `tree`, `view-secret`,
        `resource-capacity`). Typing `-n quizstakes-money` on every command is how people run
        commands against the wrong namespace. `[CMD]`
1.30.19 `kubectl` plugin mechanics (`kubectl-<name>` on `PATH`) and the one-file plugin worth
        writing for QuizStakes. `[BUILD]`
1.30.20 What `kubectl` does under the hood: discovery, REST mapping, the client-side
        `last-applied-configuration` annotation, and `-v=8` to print every HTTP request — the way
        to learn the API by watching the CLI use it. `[CMD]` `[PROVE]`

*(20 leaves)*

## §1.31 Versions, release cadence, and support windows

1.31.1 The Kubernetes cadence: **three minor releases a year** (roughly Apr/Aug/Dec), each
       supported for **14 months** (12 months of standard support + 2 of maintenance). 1.37 was
       released **26 Aug 2026** with EOL **28 Oct 2027**. `[NUM]` `[RESEARCH]`
1.31.2 The release names and dates you should be able to place: 1.33 (Apr 2025), 1.34 (Aug 2025),
       1.35 (19 Dec 2025), 1.36 (Apr 2026), **1.37 "Garhwal"** (26 Aug 2026). `[RESEARCH]`
1.31.3 What 1.37 shipped, by theme: HPA **scale-to-zero** (beta), etcd **RangeStream** for
       large list reads, **Storage Version Migration** enabled by default,
       **PodCertificateRequest**/pod certificates and **ClusterTrustBundles**,
       the **Metrics API GA**, StatefulSet **`Recreate`** rollout strategy, watch-based route
       controller reconciliation (beta), and DRA maturation. `[KEP]` `[RESEARCH]`
1.31.4 What 1.36 shipped: **user namespaces GA**, fine-grained kubelet API authorization GA,
       **declarative validation** GA, **PSI metrics** GA, volume group snapshots GA,
       **OCI artifacts/images as volumes** stable, in-place vertical scaling for pod-level
       resources (beta), `MutatingAdmissionPolicy`, mixed version proxy (beta), memory QoS /
       tiered memory protection (alpha) — plus the **removal of `gitRepo` volumes** and the
       **deprecation of `Service.spec.externalIPs`**. `[KEP]` `[RESEARCH]`
1.31.5 What 1.35 shipped: **in-place pod resize GA**, **KYAML** (beta), relaxed Service name
       validation, PodCertificateRequest (beta), structured authentication config stable,
       **IPVS mode deprecated**, and the cgroup v2 requirement for the kubelet. `[KEP]`
       `[RESEARCH]`
1.31.6 What 1.34 shipped: 23 enhancements to stable, pod-level resources default-on, the Job
       controller's terminating-pod accounting, CEL authorizer selectors, Windows kube-proxy DSR.
       `[RESEARCH]`
1.31.7 The older boundaries that still matter in interviews: dockershim removed **1.24**;
       PodSecurityPolicy removed **1.25**; `SeccompDefault` GA **1.27**; native sidecars GA
       **1.33**; nftables GA **1.33**; `Endpoints` deprecated **1.33**;
       `ValidatingAdmissionPolicy` GA **1.30**; cgroup v1 maintenance mode **1.31**.
       `[NUM]` `[RESEARCH]`
1.31.8 **Skew policy**, precisely: kube-apiserver instances within one minor; controller-manager
       and scheduler up to 1 minor behind the apiserver; **kubelet up to 3 minors behind** (since
       1.28); kubectl within ±1 minor. And the consequence: you upgrade one minor at a time,
       control plane first. `[NUM]` `[PROVE]` `[RESEARCH]`
1.31.9 Upgrade procedure and its failure modes: read the deprecation notes, run
       `kubectl-convert`/`pluto`/`kubent` against your manifests, upgrade the control plane, then
       node groups (surge or blue-green), watch PDBs block a drain, and check that no CRD or
       webhook is version-pinned. `[CMD]` `[DIAG]`
1.31.10 Feature gates: how to read the alpha→beta→GA table, `--feature-gates` on the components,
        that a managed control plane usually will not let you set them, and that **new beta APIs
        are disabled by default** since 1.24. `[CFG]`
1.31.11 Where to look things up authoritatively: `kubernetes.io/docs/reference`, the KEP
        repository, the per-release changelog, and the deprecated-API-migration guide. `[CMD]`
1.31.12 Docker Engine's own cadence and the deltas: BuildKit default (23), containerd image store
        default (**29**), graph drivers deprecated (**29**), `default-stop-timeout` (29.x),
        embedded containerd experiment (29.7), plus CVE-2026-34040 (AuthZ plugin bypass) and
        CVE-2026-33997 (`docker plugin install` privilege validation) as the reason to patch.
        `[RESEARCH]`

*(12 leaves)*

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master cost table** — one row per operation, split amortised vs worst case, with the
      mechanism that produces each: image pull (cold vs warm layer cache vs lazy-pull), container
      create, container start, JVM start to first request, probe detection, pod schedule,
      endpoint propagation, iptables vs nftables rule sync, DNS resolution, rolling update of N
      replicas, node provision (Cluster Autoscaler vs Karpenter), etcd write, watch delivery.
      `[NUM]` `[PROVE]`
2.1.2 **The layer-2 latency table**: pod-to-pod same node, pod-to-pod cross node, pod-to-pod
      cross AZ, via ClusterIP, via a headless Service, via an Ingress/Gateway, via a mesh sidecar,
      via ambient ztunnel. Each with the extra hops that explain the number. `[NUM]`
2.1.3 **The enforcement table**: for each of CPU request, CPU limit, memory request, memory limit,
      `pids`, `ephemeral-storage`, hugepages — which component enforces it, at what granularity,
      with what symptom on breach, and whether it is recoverable. `[PROVE]`
2.1.4 **The "who acts on this" table** for every health-ish signal: liveness probe, readiness
      probe, startup probe, Docker HEALTHCHECK, node condition, PDB, eviction API, `oom_score_adj`,
      LB health check, mesh outlier detection.
2.1.5 **The failure-mode table**: `ImagePullBackOff`, `ErrImagePull`, `CrashLoopBackOff`,
      `OOMKilled`, `Error`, `Evicted`, `Pending`/`FailedScheduling`, `CreateContainerConfigError`,
      `CreateContainerError`, `RunContainerError`, `ContainerCannotRun`, `InvalidImageName`,
      `Init:Error`, `Init:CrashLoopBackOff`, `NodeAffinity`, `Preempted`,
      `DeadlineExceeded`, `Unschedulable`, `ContainerStatusUnknown`,
      `FailedMount`, `FailedAttachVolume`, `Multi-Attach error`, `Terminating` (stuck),
      `Unknown`, `NotReady`, `NodeNotReady`, `TaintToleration`, `Insufficient cpu/memory`,
      `too many pods` — each with the confirming command and the fix. `[DIAG]`
2.1.6 **The object-selection table**: for each of "run a stateless service", "run something with
      identity", "run one per node", "run once", "run on a schedule", "expose internally",
      "expose externally", "route by host/path", "store non-secret config", "store a secret",
      "persist data", "limit a namespace", "protect during drains", "scale on load", "add nodes" —
      the object, and the second-choice object with why it is second.
2.1.7 **The Dockerfile-decision table**: base image family × (size, libc, CVE surface, shell,
      package manager, JVM support, debuggability) for the nine options in §1.9.5. `[NUM]`
2.1.8 **The orchestrator comparison table**: bare containers on VMs, Compose, Docker Swarm, Nomad,
      ECS on EC2, ECS on Fargate, EKS, EKS on Fargate, GKE Autopilot, Cloud Run, Lambda — across
      concepts to learn, control-plane cost, portability, IAM integration, ecosystem, team size
      needed, and what it cannot do.
2.1.9 **The kube-proxy mode table**: iptables, IPVS (deprecated 1.35), nftables (GA 1.33),
      eBPF/Cilium kube-proxy-replacement — across rule-count scaling, sync cost, first-packet
      latency, features, kernel requirement, and current default status. `[NUM]` `[RESEARCH]`
2.1.10 **The JVM-flag table for containers**: `-XX:+UseContainerSupport`,
       `-XX:MaxRAMPercentage`, `-XX:InitialRAMPercentage`, `-XX:MinRAMPercentage`,
       `-XX:ActiveProcessorCount`, `-XX:MaxMetaspaceSize`, `-XX:MaxDirectMemorySize`,
       `-Xss`, `-XX:+ExitOnOutOfMemoryError`, `-XX:+HeapDumpOnOutOfMemoryError`,
       `-XX:HeapDumpPath`, `-XX:+UseSerialGC`/`UseG1GC`/`UseZGC`, `-XX:TieredStopAtLevel`,
       `-XX:+UseContainerCpuShares` (**removed in JDK 21**) — with default, effect, and when to
       set it. `[NUM]` `[CFG]` `[RESEARCH]`
2.1.11 **The probe-defaults table** (from §1.27.3) reproduced as a single reference block with
       recommended values per QuizStakes service shape. `[NUM]`
2.1.12 **The security-hardening table**: for each control (`runAsNonRoot`, `runAsUser`,
       `allowPrivilegeEscalation`, `capabilities.drop`, `readOnlyRootFilesystem`,
       `seccompProfile`, `hostNetwork/PID/IPC`, `hostPath`, `privileged`, `hostUsers`,
       `automountServiceAccountToken`) — the field, the value, which PSS profile requires it, what
       it breaks for a JVM app, and the fix.
2.1.13 **The memory-footprint table** for a JVM pod, with the arithmetic shown: heap +
       metaspace + code cache + thread stacks (~1 MB × N) + direct buffers + GC structures +
       symbol/string tables + JVM overhead + the container's own page-cache pressure — summed for
       `funds-ledger` (12 GB heap) and `client-restrictions` (4 GB heap) to a recommended
       `limits.memory`. `[NUM]` `[PROVE]` `[X-REF 06]`
2.1.14 **The rollout-parameter table**: `maxSurge` × `maxUnavailable` × `minReadySeconds` ×
       `progressDeadlineSeconds` × replica count → capacity during the roll, total roll duration,
       and blast radius of a bad image. Worked for `application-gateway` at 12 and at 40 replicas.
       `[NUM]` `[PROVE]`

*(14 leaves)*

## §2.2 Dockerfile craft as a decision list

2.2.1 **Pin base image tags** — `eclipse-temurin:21-jre-jammy`, never `:latest`, and pin by
      **digest** where supply-chain integrity matters. `latest` makes builds non-reproducible and
      silently upgrades your runtime mid-incident. `[TRAP]`
2.2.2 The digest-pinning workflow that does not rot: Renovate/Dependabot bumping the digest in a
      PR, so you are current *and* reproducible. `[X-REF 17]`
2.2.3 **Multi-stage; ship a JRE, not a JDK.** ~800 MB → ~200 MB, and compilers, build tools and
      source leave the production attack surface. `[NUM]`
2.2.4 **Never put secrets in `ENV` or `ARG`** — both are baked into image metadata and readable via
      `docker history` by anyone with the image, including `ARG`, which people wrongly believe is
      build-time-only and discarded. Use `--mount=type=secret` or runtime injection. Prove it with
      real `docker history` output. `[TRAP]` `[PROVE]` `[SOURCE]`
2.2.5 **Run as a non-root user** with a numeric UID; create the user, `COPY --chown` after, `USER`
      after anything needing root. Containers run as root by default, and root plus a bad volume
      mount or a kernel bug is a host compromise. `[TRAP]`
2.2.6 **Add a `.dockerignore`.** Without one the whole directory — `.git`, `target/`,
      `node_modules/`, `.env`, IDE files — is sent to the daemon as context: slow, and a real leak
      if any of it is `COPY . .`'d. Give the QuizStakes `.dockerignore` verbatim. `[BUILD]`
2.2.7 **Use exec form for `ENTRYPOINT`/`CMD`.** Shell form makes `/bin/sh` PID 1, and **the shell
      does not forward SIGTERM** — so the app never gets the shutdown signal, is SIGKILLed after
      the grace period, and drops in-flight requests on **every single deploy**. `[TRAP]`
2.2.8 **Handle PID 1 semantics**: no default handlers, no zombie reaping. `--init`/`tini` if you
      spawn subprocesses. `[TRAP]`
2.2.9 **`HEALTHCHECK`** so the runtime distinguishes "process running" from "working" — for
      Docker/Compose/ECS. Kubernetes ignores it and uses probes. `[TRAP]`
2.2.10 **One concern per container.** No supervisord running app + nginx + cron; separate
       containers scale, restart and are monitored independently.
2.2.11 **Combine and clean package installs in one layer**:
       `RUN apt-get update && apt-get install -y --no-install-recommends x && rm -rf
       /var/lib/apt/lists/*`.
2.2.12 **Log to stdout/stderr**, never to a file inside the container. `[X-REF 20]`
2.2.13 **Scan images in CI and fail on critical CVEs** — `trivy`, `grype`, `docker scout`, ECR
       enhanced scanning. A base pinned two years ago is a pile of known vulnerabilities. Full
       treatment in §2.5.
2.2.14 **Keep the image small**: faster pulls, faster scale-out, faster deploys, smaller attack
       surface. Quantify the pull-time saving across a 12→40 scale-out on a campaign launch.
       `[NUM]` `[PROVE]`
2.2.15 The additional rules the current guide does not have: set `WORKDIR` explicitly; do not
       `COPY` the `.mvn` wrapper into the runtime stage; drop `curl`/`wget` from the runtime image
       and use a `grpc` or `httpGet` probe instead of an `exec` one; declare
       `LABEL org.opencontainers.image.revision`; set `-XX:+ExitOnOutOfMemoryError` so a heap OOM
       becomes a restart rather than a zombie; make the jar path stable (`app.jar`) so the
       entrypoint never needs a wildcard.
2.2.16 The anti-patterns worth naming: `RUN apt-get upgrade` (non-reproducible), `ADD` from a URL
       (no checksum), `chmod 777`, installing `sudo`, `ENV JAVA_OPTS` used with shell-form
       entrypoint (word splitting), a `wait-for-it.sh` entrypoint wrapper that swallows signals,
       and building the image inside the image. `[TRAP]`
2.2.17 Hadolint and BuildKit build checks as the automated version of this list, and the rules
       worth suppressing. `[CMD]` `[RESEARCH]`

*(17 leaves)*

## §2.3 Image size, base images, and the CVE budget

2.3.1 Where the bytes actually are in a JVM image: base OS (~30–80 MB), JRE (~120–180 MB),
      application jar (~40–90 MB for a Spring Boot service), plus anything installed. Do the
      arithmetic before optimising the wrong thing. `[NUM]` `[PROVE]`
2.3.2 Why image size matters *operationally*, quantified: pull time on a cold node during a
      12→40 scale-out at a 40k-registration campaign launch; registry egress cost; node disk and
      image GC pressure; CI push time on every commit. `[NUM]` `[PROVE]`
2.3.3 Why image size matters *for security*: every package is a CVE surface, and `apt list
      --installed | wc -l` on a full distro base vs distroless is a 10× difference in things a
      scanner will flag. `[NUM]`
2.3.4 The four size levers in order of payoff: multi-stage + JRE; layered jars (§1.8.18);
      a slimmer base; `jlink`. With the measured saving of each. `[NUM]`
2.3.5 **Docker Hardened Images / Chainguard / distroless** as the "near-zero-CVE base" category,
      what you give up (shell, package manager, glibc assumptions), and how it changes the CVE
      triage conversation. `[RESEARCH]`
2.3.6 Reading a scan report without panicking: reachability, `--severity CRITICAL,HIGH`,
      `--ignore-unfixed`, VEX statements, and the difference between "a CVE exists in a package in
      my image" and "my service is exploitable".
2.3.7 The base-image upgrade cadence as a process, not an event: a scheduled rebuild of every
      image weekly even with no code change, so the CVE clock is reset by CI rather than by an
      incident. `[X-REF 17]`
2.3.8 `docker history` + `dive` + `crane` as the size-forensics toolkit, applied to a real bloated
      image to find the 400 MB `~/.m2` someone `COPY`d. `[CMD]` `[DIAG]`

*(8 leaves)*

## §2.4 The build in CI

2.4.1 Why the CI build is slow by default: fresh runner, empty layer cache, empty dependency cache,
      shallow-clone context, and QEMU emulation for arm64. Attribute the minutes to each. `[NUM]`
      `[DIAG]`
2.4.2 The cache strategy matrix: `type=registry,mode=max` (best default, works across runners),
      `type=gha` (GitHub-native, size-capped), `type=local` + actions/cache (fiddly),
      a persistent self-hosted builder (fastest, least reproducible). Give the recommendation.
      `[PROVE]` `[RESEARCH]`
2.4.3 Cache poisoning and correctness: a `mode=max` cache from an untrusted branch, and why cache
      scope must follow trust boundaries.
2.4.4 The `docker/build-push-action` / `buildx bake` pipeline for the whole QuizStakes estate, with
      per-service targets and a shared base target. `[BUILD]`
2.4.5 Tag and label generation in CI: `docker/metadata-action`-style outputs producing
      `1.4.2`, `1.4.2-a1b2c3d`, `a1b2c3d`, `sha-<short>`, plus every
      `org.opencontainers.image.*` label from the Git context. `[BUILD]` `[X-REF 17]`
2.4.6 Build-time secrets in CI without leaks: OIDC federation to the registry instead of a stored
      password, `--mount=type=secret` for a private Maven repo token, and never `--build-arg`.
      `[X-REF 18]`
2.4.7 Test-in-the-build vs test-outside-the-build: `--target test` inside the Dockerfile
      (hermetic, cache-friendly, awkward for reports) vs `mvn verify` on the runner with
      Testcontainers (needs a Docker socket — Docker-in-Docker vs socket mount vs a remote
      Testcontainers Cloud). Give the decision and the DinD security caveat. `[X-REF 16]`
      `[TRAP]`
2.4.8 Multi-arch in CI properly: matrix build per native runner + `docker buildx imagetools
      create` to assemble the index, instead of one emulated job. `[CMD]` `[NUM]`
2.4.9 The image-promotion model: build once, tag by digest, promote the *same digest* through
      dev → staging → prod rather than rebuilding per environment. Prove why rebuilding per
      environment defeats the point of an immutable artefact. `[PROVE]`
2.4.10 Kaniko/Buildah/`podman build` for building inside a Kubernetes cluster without a privileged
       daemon, and why "give the CI pod the Docker socket" is a cluster-admin-equivalent grant.
       `[TRAP]` `[PROVE]`
2.4.11 Build reproducibility as a debugging tool: when two builds of the same commit differ,
       `SOURCE_DATE_EPOCH` and `diffoci`/`crane export | diff` tell you where. `[RESEARCH]`

*(11 leaves)*

## §2.5 Image supply chain: signing, SBOM, provenance, admission

2.5.1 The threat model, concretely: a compromised base image, a typosquatted dependency, a
      malicious builder, a registry substitution, or a stolen registry credential — and which
      control addresses which. `[X-REF 13]`
2.5.2 **Signing** with Sigstore/`cosign`: keyless signing via OIDC and Fulcio, the Rekor
      transparency log, `cosign sign`/`cosign verify --certificate-identity
      --certificate-oidc-issuer`, and where the signature is stored (as a referrer to the digest,
      §1.5.9). `[CMD]` `[RESEARCH]`
2.5.3 **SBOM**: SPDX vs CycloneDX, `syft`/`docker buildx --sbom`, and what an SBOM is actually for
      (answering "am I affected by this CVE" in minutes, not days).
2.5.4 **Provenance / SLSA**: `--provenance=mode=max`, what the attestation records (source repo,
      commit, builder identity, build parameters), and the SLSA levels 1–4 as a maturity ladder.
      `[RESEARCH]`
2.5.5 Verifying at **admission**: `sigstore-policy-controller`, Kyverno `verifyImages`, Connaisseur,
      or a `ValidatingAdmissionPolicy` — so an unsigned or unprovenanced image cannot run in
      `quizstakes-money`. `[BUILD]` `[YAML]`
2.5.6 Registry-side controls: immutable tags (ECR tag immutability), scan-on-push, blocking
      pushes that fail a policy, and a pull-through cache so an upstream compromise is contained.
      `[X-REF 18]`
2.5.7 The QuizStakes policy this section must produce: only images from the internal registry,
      only signed by the CI identity, only with a provenance attestation naming a
      `quizstakes/*` repository, no `:latest`, and card-data services additionally pinned by
      digest. `[BUILD]`
2.5.8 The honest caveat: signing proves *who built it*, not *that it is safe*. Say so.

*(8 leaves)*

## §2.6 Container security posture

2.6.1 The boundary, stated precisely: a container is a **process on a shared kernel**, so a kernel
      vulnerability is a container escape. Containers are an isolation boundary but a **weaker one
      than a VM**. Keep the current guide's framing and add the specific consequences.
2.6.2 Why multi-tenant platforms use microVMs (Firecracker under Fargate and Lambda) or gVisor
      rather than raw containers, and what that implies for running untrusted code in *your*
      cluster.
2.6.3 The escape paths worth being able to name: `--privileged` + `mount`, the **Docker socket**,
      `hostPath` on `/` or `/var/run`, `hostPID` + `nsenter`, `CAP_SYS_ADMIN`,
      writable `/sys/fs/cgroup` (the `release_agent` escape), core-pattern abuse, and kernel CVEs
      (Dirty COW, Dirty Pipe, `runc` CVE-2019-5736 and the 2024 `runc`/Leaky Vessels family).
      `[RESEARCH]`
2.6.4 Docker-specific CVEs to know as illustrations, not trivia: CVE-2019-5736 (runc
      `/proc/self/exe` overwrite), CVE-2024-21626 (`runc` fd leak / "Leaky Vessels"),
      CVE-2025-9074 (Docker Desktop API reachable from a container), CVE-2026-34040 (AuthZ plugin
      bypass), CVE-2026-33997 (`docker plugin install`). `[RESEARCH]`
2.6.5 The hardening set, in the order you should apply it: non-root numeric UID; `runAsNonRoot:
      true`; `allowPrivilegeEscalation: false`; `capabilities.drop: ["ALL"]`;
      `seccompProfile.type: RuntimeDefault`; `readOnlyRootFilesystem: true` + `emptyDir` for
      `/tmp`; no host namespaces; no `hostPath`; `automountServiceAccountToken: false` unless
      needed; `hostUsers: false` where supported. `[BUILD]` `[YAML]`
2.6.6 **`automountServiceAccountToken: false`** as the single highest-value one-line change most
      teams have not made: by default every pod carries a token that can talk to the API server.
      `[TRAP]` `[PROVE]`
2.6.7 Runtime detection as the layer above prevention: **Falco**, Tetragon, `seccomp` audit mode,
      and the eBPF-based tools — what "unexpected `execve` in a container" detection buys you.
      `[X-REF 20]`
2.6.8 The QuizStakes-specific requirements from the scenario: **card data isolation** (only
      `card-payments` may egress to the PSP — a NetworkPolicy plus a separate node pool, not a
      code convention), **PII access logged per field**, and **workload identity with short-lived
      credentials and mTLS**. `[X-REF 13]` `[X-REF 18]`
2.6.9 Where the container boundary is the *wrong* control: it does not stop SQL injection, does not
      stop a leaked JWT signing key, and does not make a `restriction decision read from a cache`
      correct. Say what it does not solve.

*(9 leaves)*

## §2.7 Rootless, Docker Desktop, and the developer environment

2.7.1 **Rootless mode** mechanics: user namespaces + `slirp4netns`/`pasta` networking +
      `fuse-overlayfs`, `newuidmap`/`newgidmap` and `/etc/subuid`. What it fixes (a daemon
      compromise is not root) and what it costs (slower I/O, no privileged ports below 1024
      without `net.ipv4.ip_unprivileged_port_start`, some storage drivers unavailable).
      `[PROVE]` `[CFG]`
2.7.2 **Podman** as rootless-and-daemonless by design, `podman-compose`, `podman generate kube`,
      and the Docker-socket compatibility shim that lets Testcontainers work.
2.7.3 **Docker Desktop** is a Linux VM: the consequences are bind-mount I/O cost, a memory ceiling
      you must configure, and the fact that `localhost` semantics differ. Plus the licensing
      change that pushed many companies to alternatives. `[TRAP]`
2.7.4 The alternatives on macOS: **Colima**, **Rancher Desktop**, **OrbStack**, `podman machine`,
      plain Lima — compared on speed, socket compatibility and Kubernetes support. `[RESEARCH]`
2.7.5 Local Kubernetes: **kind** (containers as nodes, fastest CI cluster), **k3d**, **minikube**,
      **Docker Desktop's** built-in cluster, **k3s**. Which to use for what, and the
      `kind load docker-image` step people forget. `[CMD]` `[TRAP]`
2.7.6 The inner loop for a Kubernetes-targeted service: `docker compose watch` for the fast path,
      **Skaffold** / **Tilt** / **Telepresence** / **mirrord** / **DevSpace** for the
      cluster-attached path, and the honest position that most backend work does not need any of
      them. `[RESEARCH]`
2.7.7 **Dev Containers** (`devcontainer.json`) and Codespaces as the "the environment is an image"
      end state.
2.7.8 The QuizStakes local-development story the bible must actually ship: `compose.yaml` for
      dependencies, the service run from the IDE against it, `kind` + the real manifests when you
      need to test probes and rollouts, and Testcontainers in the test suite. `[BUILD]`
      `[X-REF 16]`

*(8 leaves)*

## §2.8 The JVM in a container

2.8.1 The historical bug and why it still shapes behaviour: pre-8u191/pre-10 JVMs read
      `/proc/meminfo` and `/proc/cpuinfo`, so a JVM in a 512 MiB container computed a heap from the
      **host's** memory and was OOMKilled on start-up. `[PROVE]` `[NUM]`
2.8.2 `-XX:+UseContainerSupport` (**on by default since 10/8u191**): the JVM reads
      `memory.max`/`memory.limit_in_bytes`, the CPU quota and the CPU set. State exactly which
      cgroup files it reads on v1 and on v2. `[SOURCE]` `[RESEARCH]`
2.8.3 **`-XX:MaxRAMPercentage` defaults to 25.** So a 1 GiB container with no flags gets a
      ~256 MiB heap — usually wasteful, occasionally exactly wrong. `[NUM]` `[TRAP]`
      `[RESEARCH]`
2.8.4 Why `-XX:MaxRAMPercentage=70` beats `-Xmx700m`: it tracks the cgroup limit, so changing
      `limits.memory` automatically re-sizes the heap and cannot drift out of sync with the
      manifest. Keep the current guide's recommendation and add
      `-XX:InitialRAMPercentage`/`-XX:MinRAMPercentage` (the latter applies only below 96 MB — the
      detail almost everyone gets wrong). `[NUM]` `[PROVE]` `[TRAP]`
2.8.5 **The cgroup limit covers everything, not just the heap.** RSS = heap + metaspace + code
      cache + thread stacks (~1 MB each, and `-Xss` is per thread) + direct/mapped buffers + GC
      structures (G1 remembered sets, card table ≈ 0.2–2% of heap) + symbol and string tables +
      JIT compiler arenas + JVM internal. Show the full arithmetic for `funds-ledger` at 12 GB
      heap and derive the required `limits.memory`. `[NUM]` `[PROVE]` `[X-REF 06]`
2.8.6 **The diagnostic distinction that must be stated unambiguously**: exit **137** with no Java
      exception = the kernel OOMKilled the container (raise the limit or lower the heap
      percentage); `java.lang.OutOfMemoryError: Java heap space` **with a stack trace** = the JVM's
      own heap exhaustion (a leak, or too small a heap). They look identical on a dashboard and
      have opposite fixes. Keep this verbatim and add the confirming commands
      (`kubectl get pod -o jsonpath='{.status.containerStatuses[0].lastState.terminated}'`,
      `dmesg | grep -i oom`, `memory.events`). `[TRAP]` `[DIAG]` `[PROVE]`
2.8.7 The third case the current guide does not cover: **`OutOfMemoryError: Metaspace`**,
      **`unable to create native thread`** (a `pids.max` or `RLIMIT_NPROC` problem, not a heap
      problem), **`Direct buffer memory`** (Netty/`-XX:MaxDirectMemorySize`), and
      **native leak with a healthy heap** (NMT: `-XX:NativeMemoryTracking=summary` +
      `jcmd VM.native_memory`). `[DIAG]` `[X-REF 06]`
2.8.8 `Runtime.availableProcessors()` in a container: it follows the **CPU limit** as
      `ceil(quota/period)` — so `limits.cpu: 1500m` gives 2, and **no limit gives the node's full
      core count**, which may be 64 when your fair share is 2. `[PROVE]` `[NUM]` `[TRAP]`
2.8.9 What silently depends on that number: G1's `ParallelGCThreads` and `ConcGCThreads`, the
      common `ForkJoinPool` parallelism (`availableProcessors()-1`), Netty's default event-loop
      count (`2 × cores`), Tomcat/Undertow acceptor and I/O thread counts, HikariCP sizing advice,
      `Executors.newWorkStealingPool()`, parallel streams, and the virtual-thread carrier pool.
      **Be explicit about pool sizes rather than trusting the default.** `[PROVE]` `[X-REF 05]`
      `[X-REF 04]`
2.8.10 `-XX:ActiveProcessorCount=N` as the override, and that **`-XX:+UseContainerCpuShares` was
       removed in JDK 21** — so the old "restore the shares-based behaviour" advice no longer
       compiles. `[VERSION-TRAP]` `[RESEARCH]`
2.8.11 **CFS throttling is the sneakiest performance bug in Kubernetes.** A limit of `500m` is 50 ms
       of CPU per 100 ms period **across all threads**: a JVM with 8 GC threads and 200 request
       threads burns the quota in the first few milliseconds and then sits frozen for ~95 ms. Your
       p99 is terrible, your CPU **utilisation looks low** (you are throttled, not busy), and
       nothing in the application log explains it. Keep this verbatim; §3.3 proves it. `[TRAP]`
       `[PROVE]`
2.8.12 The metric and the threshold: `container_cpu_cfs_throttled_seconds_total`,
       `container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total` as a ratio,
       and `cpu.stat`'s `nr_throttled`/`throttled_usec` read directly. **Non-zero throttling on a
       latency-sensitive service is an actionable finding.** `[CMD]` `[NUM]` `[X-REF 20]`
2.8.13 The fixes, ranked: raise or remove the CPU limit; reduce thread counts to fit the quota;
       shorten `cpu.cfs_period_us` (rarely available); use `static` CPU manager policy with
       integral CPUs for a genuinely latency-critical service. Apply this to
       `client-restrictions`' 30 ms budget and show which fix its shape demands. `[PROVE]`
2.8.14 GC selection in a small container: **SerialGC** below ~2 CPU and ~2 GB is often faster than
       G1 (the JVM's own ergonomics pick it); G1 for the general case; ZGC/Generational ZGC for
       `funds-ledger`'s pause sensitivity; and the memory overhead each carries. `[NUM]`
       `[X-REF 06]`
2.8.15 Start-up: the 12→40 `application-gateway` scale-out has to be fast, so
       `-XX:TieredStopAtLevel=1` (dev only), **AppCDS**, **CRaC**, or **GraalVM native image**
       become architectural choices, not micro-optimisations. Give measured start-up numbers.
       `[NUM]` `[RESEARCH]`
2.8.16 Sizing `client-restrictions` end to end as the worked example: 4 GB heap, 8 instances,
       "extreme request rate, trivial objects", 30 ms p99, and derive `requests`, `limits`,
       `MaxRAMPercentage`, thread pool sizes, GC choice, and HPA metric. `[NUM]` `[PROVE]`
       `[BUILD]`
2.8.17 The `document-verification` counter-example: 8 GB heap, 2–6 MB buffers crossing the G1
       humongous threshold, 6 instances — why its memory limit needs more headroom than the
       generic 70% rule and how to compute it. `[NUM]` `[X-REF 06]`
2.8.18 Heap dumps from a container that will be killed: `-XX:+HeapDumpOnOutOfMemoryError
       -XX:HeapDumpPath=/dumps` on a mounted volume, and why writing a 12 GB dump to the
       writable layer gets you evicted for `ephemeral-storage` instead. `[TRAP]` `[DIAG]`
2.8.19 Getting diagnostics out of a live pod: `kubectl exec -- jcmd 1 Thread.print`,
       `jcmd 1 GC.heap_info`, `jcmd 1 VM.native_memory summary`, `jcmd 1 JFR.start`, then
       `kubectl cp`. And why a distroless image has no `jcmd`, and `kubectl debug` with a
       JDK-bearing ephemeral container sharing the process namespace is the answer.
       `[CMD]` `[PROVE]` `[X-REF 06]`
2.8.20 `-XX:+ExitOnOutOfMemoryError` / `-XX:+CrashOnOutOfMemoryError`: turning a wedged JVM into a
       restart the orchestrator can act on, which is strictly better than a liveness probe
       guessing. `[PROVE]`

*(20 leaves)*

## §2.9 Scheduling: how a pod lands on a node

2.9.1 The two phases: **filtering** (which nodes *can* run this pod) then **scoring** (which of
      them *should*), then binding. §3.14 does the framework; this section does the knobs.
2.9.2 The filters you control: resource requests vs allocatable, `nodeSelector`, node affinity
      (`requiredDuringSchedulingIgnoredDuringExecution`), taints and tolerations, volume
      topology and node limits, pod affinity/anti-affinity, `hostPort` conflicts, the node's
      `maxPods`. `[CFG]`
2.9.3 **`nodeSelector`** vs **`nodeAffinity`**: the latter adds operators (`In`, `NotIn`,
      `Exists`, `DoesNotExist`, `Gt`, `Lt`) and a soft form
      (`preferredDuringSchedulingIgnoredDuringExecution` with `weight` 1–100). Note that
      `IgnoredDuringExecution` means **a running pod is never moved when labels change**.
      `[PROVE]` `[TRAP]`
2.9.4 **Taints and tolerations**: `NoSchedule`, `PreferNoSchedule`, `NoExecute` (+
      `tolerationSeconds`), the operators `Equal`/`Exists`, and the built-in taints
      (`node.kubernetes.io/not-ready`, `unreachable`, `memory-pressure`, `disk-pressure`,
      `pid-pressure`, `network-unavailable`, `unschedulable`,
      `node.cloudprovider.kubernetes.io/uninitialized`). `[CFG]` `[SOURCE]`
2.9.5 The mental model: **taints repel, tolerations permit, affinity attracts.** A toleration does
      not *cause* placement, which is the single most common confusion. `[TRAP]` `[PROVE]`
2.9.6 **Pod affinity / anti-affinity**: `topologyKey`, `labelSelector`, `namespaceSelector`,
      `matchLabelKeys`/`mismatchLabelKeys`, and the crucial performance warning — required
      anti-affinity is O(pods × nodes) and the docs explicitly advise against it in clusters of
      hundreds of nodes. `[PROVE]` `[TRAP]`
2.9.7 **`topologySpreadConstraints`** as the better tool: `maxSkew`, `topologyKey`,
      `whenUnsatisfiable` (`DoNotSchedule`/`ScheduleAnyway`), `labelSelector`, `minDomains`,
      `nodeAffinityPolicy`, `nodeTaintsPolicy`, `matchLabelKeys`. Plus the cluster-level default
      constraints. This is how you spread `application-gateway`'s 12–40 replicas across three AZs
      without hand-written anti-affinity. `[CFG]` `[PROVE]`
2.9.8 The QuizStakes placement requirements, expressed as manifests: `funds-ledger`'s 3 instances
      must be in 3 different AZs and never co-located; `card-payments` must run only on the
      card-data node pool (taint + toleration + nodeSelector); `document-verification` needs
      memory-optimised nodes; the log DaemonSet must tolerate everything. `[BUILD]` `[YAML]`
2.9.9 **PriorityClass** and **preemption**: `value`, `globalDefault`,
      `preemptionPolicy: Never|PreemptLowerPriority`, the system classes
      (`system-cluster-critical` 2000000000, `system-node-critical` 2000001000), and the
      preemption algorithm (victim selection respecting PDBs where it can). `[NUM]` `[CFG]`
2.9.10 The priority design for QuizStakes: money-path services above read-only views above batch,
       so a node shortage sheds `application-history` writes before `funds-ledger`. `[PROVE]`
2.9.11 `nodeName` set directly (bypassing the scheduler entirely) and why that is a debugging tool,
       not a deployment technique. `[TRAP]`
2.9.12 Multiple schedulers and `schedulerName`; scheduler profiles and plugin
       enable/disable via `KubeSchedulerConfiguration`; `percentageOfNodesToScore`. `[CFG]`
2.9.13 `FailedScheduling` message decoding, verbatim strings: `0/12 nodes are available: 8
       Insufficient cpu, 4 node(s) had untolerated taint …`, `didn't match Pod's node affinity/
       selector`, `node(s) exceed max volume count`, `node(s) had volume node affinity conflict`,
       `too many pods`, `Insufficient ephemeral-storage`. Each with its fix. `[DIAG]` `[SOURCE]`
2.9.14 Why **requests, not usage**, drive scheduling — and therefore why a cluster can be 30%
       utilised and still unable to schedule anything. The single most common capacity confusion.
       `[PROVE]` `[TRAP]`
2.9.15 Descheduler as the missing half: nothing rebalances after the fact, so
       `descheduler` policies (`RemoveDuplicates`, `LowNodeUtilization`,
       `RemovePodsViolatingTopologySpreadConstraint`, `TooManyRestarts`) exist. `[RESEARCH]`
2.9.16 `Overhead` from `RuntimeClass` and how it changes the arithmetic for Kata/gVisor pods.

*(16 leaves)*

## §2.10 Rollouts and rollbacks

2.10.1 The `RollingUpdate` mechanism step by step: create up to `maxSurge` new pods → wait for
      Ready (+ `minReadySeconds`) → delete up to `maxUnavailable` old pods → repeat, all driven by
      two ReplicaSets.
2.10.2 The parameter choice, argued: `maxSurge: 1, maxUnavailable: 0` is the safest (capacity never
      dips, but the roll is slow and needs headroom for one extra pod);
      `maxUnavailable: 25%` is faster and drops capacity; `maxSurge: 100%` is a
      blue-green-in-a-Deployment. Work the roll duration for 12 and 40 replicas. `[NUM]` `[PROVE]`
2.10.3 **Readiness probes are what make a rolling update safe.** Without a meaningful readiness
      probe, Kubernetes shifts traffic to a pod that is not serving yet. Keep the current guide's
      sentence and prove it. `[PROVE]`
2.10.4 `minReadySeconds` as the cheap protection against "ready then immediately crashes", and
      `progressDeadlineSeconds` (600) as the thing that turns a stuck roll into a
      `ProgressDeadlineExceeded` condition rather than a silent hang. `[NUM]`
2.10.5 What a rollback actually is: scaling the previous ReplicaSet back up. Hence it is seconds,
      needs no build, and the artefact is known-good because it was running an hour ago. Keep the
      current guide's argument. `[PROVE]`
2.10.6 `rollout undo` vs `set image` vs re-applying the previous Git commit: which leaves the
      cluster matching Git, and why GitOps changes the correct answer. `[TRAP]`
2.10.7 **`rollout restart`** and how it works (a `kubectl.kubernetes.io/restartedAt` annotation on
      the pod template, producing a new revision) — the supported way to pick up a changed Secret.
      `[PROVE]`
2.10.8 `revisionHistoryLimit: 10` and why setting it to 0 removes your ability to roll back.
      `[TRAP]`
2.10.9 The `Recreate` strategy and its two legitimate uses: a singleton that cannot have two
      instances (a leader-elected `bank-withdrawal` run), and an incompatible schema change.
2.10.10 **Proportional scaling** during a rollout and why replica counts look strange mid-roll.
        `[PROVE]`
2.10.11 The strategies Kubernetes does **not** give you natively, and what implements each:
        **blue-green** (two Deployments + a Service selector flip, or Argo Rollouts),
        **canary** (weighted `backendRefs` in an HTTPRoute, a mesh, or Argo Rollouts with
        analysis), **shadow/mirror** (`RequestMirror` filter), **feature flags** (the one that
        decouples deploy from release entirely — and usually the right answer). `[PROVE]`
        `[X-REF 17]`
2.10.12 Analysis-driven promotion: what metric gates a canary (error rate, p99, saturation), the
        minimum sample size to make it meaningful, and why a 5-minute canary on a 40/sec deposit
        rate is statistically empty. `[NUM]` `[PROVE]` `[X-REF 20]`
2.10.13 **Schema and contract compatibility as a rollout constraint**: during any rolling update two
        versions run simultaneously, so every change must be backward compatible for at least one
        release — expand/contract migrations, additive-only API changes, and tolerant readers.
        Apply it to adding a column to the ledger and to changing `AA-610`'s payload.
        `[PROVE]` `[X-REF 12]` `[X-REF 09]`
2.10.14 The rollout that must not be rolling: the agreement-version publish (it makes every cached
        copy legally wrong) and the self-exclusion path (invariant 8). Argue what deployment shape
        each demands. `[PROVE]`
2.10.15 Rollout observability: `rollout status` in CI with a timeout and an automatic
        `rollout undo` on failure — the two-line pipeline change that prevents most bad deploys
        becoming incidents. `[BUILD]`
2.10.16 StatefulSet rollouts: ordered, reverse-ordinal, one at a time, gated by Ready — and
        `partition` as a manual canary. Plus the **stuck-rollout** recovery procedure (set
        `partition`, revert the spec, delete the broken pod). `[DIAG]`
2.10.17 DaemonSet rollouts and why `maxUnavailable: 1` on a 200-node cluster is a 200-step rollout.
        `[NUM]`

*(17 leaves)*

## §2.11 Graceful shutdown: the full chain

2.11.1 The complete termination sequence, in order, with what performs each step: (1) the pod's
      `deletionTimestamp` is set and it enters `Terminating`; (2) **concurrently**, the
      EndpointSlice controller marks the endpoint not-ready and that propagates to every node's
      kube-proxy, to the ingress/Gateway controller, and to any cloud LB target group; (3) the
      kubelet runs `preStop`; (4) the kubelet sends **SIGTERM** to PID 1 of each container
      (sidecars last); (5) the app stops accepting new work, fails readiness, drains in-flight
      requests; (6) it closes connection pools, flushes logs and metrics, releases locks, exits 0;
      (7) if it has not exited by `terminationGracePeriodSeconds`, **SIGKILL**. `[PROVE]`
      `[SOURCE]`
2.11.2 **The race, stated precisely: steps 2 and 3/4 are concurrent, not sequential.** There is a
      window in which the pod has received SIGTERM and started shutting down while load balancers
      are **still sending it new requests**. The result is a handful of connection resets on every
      single deploy — small enough to dismiss as noise, real enough to show as a p99.9 error
      spike, and completely avoidable. Keep the current guide's paragraph verbatim. `[TRAP]`
      `[PROVE]`
2.11.3 Why endpoint propagation takes hundreds of milliseconds to seconds: the controller must
      write the EndpointSlice, every kube-proxy must observe it and rewrite rules, and a cloud LB
      must complete a deregistration cycle (an ALB's default deregistration delay is **300 s**).
      Quantify each hop. `[NUM]` `[PROVE]` `[X-REF 18]`
2.11.4 **The fix chain, complete**: a `preStop` sleep (~5–15 s, or the `sleep` handler) so
      deregistration propagates *before* shutdown starts; `terminationGracePeriodSeconds` >
      preStop + the longest in-flight request; `server.shutdown=graceful` and
      `spring.lifecycle.timeout-per-shutdown-phase=30s`; exec-form `ENTRYPOINT`; and pod
      **readiness gates** where the LB supports them. `[BUILD]` `[YAML]`
2.11.5 The arithmetic that must hold: `terminationGracePeriodSeconds ≥ preStop + p99.9 request
      duration + pool-close time`. Otherwise you have carefully implemented graceful shutdown and
      then SIGKILL it halfway through. Work it for `application-gateway` (fast) and for the
      `bank-withdrawal` payment run (5–40 minutes). `[NUM]` `[PROVE]` `[TRAP]`
2.11.6 The `bank-withdrawal` case from the scenario: a `PaymentRun` killed mid-flight means **money
      sent and nothing recorded**. Appendix B.4's "drain-before-terminate on the payment run" is
      therefore a hard requirement, and the answer is not a bigger grace period — it is
      checkpointed, idempotent, resumable work plus a lock. `[PROVE]` `[X-REF 14]`
2.11.7 What Spring Boot's graceful shutdown actually does: stops accepting new connections at the
      web server, lets in-flight requests finish within the phase timeout, closes
      `SmartLifecycle` beans in phase order, and flips readiness to `OUT_OF_SERVICE` first.
      Show the log lines you should see. `[SOURCE]` `[X-REF 07]`
2.11.8 The things that must happen in shutdown and usually do not: flush the Micrometer registry
      (otherwise the last 60 s of metrics are lost — exactly the interesting 60 s), flush the log
      appender, commit consumer offsets, release the distributed lock, close the DB pool, and
      deregister from any external discovery. `[BUILD]` `[X-REF 20]`
2.11.9 Keep-alive as the hidden reason a "drained" pod still gets requests: an HTTP/1.1
      keep-alive or HTTP/2 connection already established bypasses endpoint changes entirely
      until it is closed. The fixes: `Connection: close` during shutdown,
      `server.tomcat.max-keep-alive-requests`, LB idle-timeout tuning, and a `preStop` long enough
      for the client to cycle. `[PROVE]` `[TRAP]` `[X-REF 10]`
2.11.10 `terminationGracePeriodSeconds: 0` / `kubectl delete --force --grace-period=0`: what it
        actually does (removes the API object immediately without waiting for the kubelet to
        confirm), why it can leave a container running and a volume attached, and why it is the
        wrong tool for a stuck pod. `[TRAP]` `[PROVE]`
2.11.11 The 1.37 pod-lifecycle detail worth knowing: the ordering guarantees for **sidecar**
        shutdown (app containers get SIGTERM, then sidecars) and what still goes wrong if the
        sidecar dies first. `[RESEARCH]`
2.11.12 Node shutdown and the graceful-node-shutdown feature:
        `shutdownGracePeriod`/`shutdownGracePeriodCriticalPods`, and why a spot-instance
        reclamation (2-minute notice) is a different problem than a drain. `[CFG]` `[X-REF 18]`
2.11.13 A complete, verifiable test for all of this: a load generator at 1,200 req/s against
        `client-restrictions` while `kubectl rollout restart` runs, asserting **zero** non-2xx.
        This is the only way to know your chain works. `[BUILD]` `[X-REF 16]`

*(13 leaves)*

## §2.12 Disruption: PDBs, drains, eviction, preemption

2.12.1 The vocabulary that makes this section coherent: **voluntary** disruption (a drain, a
      cluster upgrade, a descheduler, a Karpenter consolidation) vs **involuntary** (a node dying,
      an OOMKill, a kernel panic, a spot reclamation). PDBs only constrain the voluntary kind.
      `[PROVE]` `[TRAP]`
2.12.2 **PodDisruptionBudget**: `minAvailable` (absolute or percentage) or `maxUnavailable`,
      `selector`, `unhealthyPodEvictionPolicy` (`IfHealthyBudget` default / `AlwaysAllow`), and
      the `status` fields (`disruptionsAllowed`, `currentHealthy`, `desiredHealthy`,
      `expectedPods`). `[CFG]` `[SOURCE]`
2.12.3 What a PDB does mechanically: the **Eviction API** (`pods/eviction`) consults it and returns
      **429** when the budget is exhausted. `kubectl drain` uses the Eviction API;
      `kubectl delete pod` does not — which is why `delete` ignores your PDB. `[PROVE]` `[TRAP]`
2.12.4 The PDB that blocks a node drain forever: `minAvailable: 3` with `replicas: 3`, or a PDB on
      a single-replica Deployment. The symptom (a cluster upgrade stuck for hours), the diagnosis
      (`kubectl get pdb`, `disruptionsAllowed: 0`) and the fix. `[DIAG]` `[TRAP]`
2.12.5 The PDBs QuizStakes needs, with reasons: `funds-ledger` `minAvailable: 2` of 3 (it is
      partition-affine, so losing 2 of 3 loses a third of clients' money paths);
      `client-restrictions` `maxUnavailable: 1` of 8; `application-gateway` `maxUnavailable: 25%`;
      no PDB on batch. `[BUILD]` `[YAML]` `[PROVE]`
2.12.6 `kubectl cordon` / `drain` (`--ignore-daemonsets`, `--delete-emptydir-data`,
      `--disable-eviction`, `--grace-period`, `--timeout`, `--pod-selector`) / `uncordon`, and the
      correct node-replacement runbook. `[CMD]`
2.12.7 **Node-pressure eviction** by the kubelet: the eviction **signals**
      (`memory.available`, `nodefs.available`, `nodefs.inodesFree`, `imagefs.available`,
      `imagefs.inodesFree`, `containerfs.available`, `containerfs.inodesFree`, `pid.available`)
      and their formulas — note `memory.available` uses **workingSet**, not RSS.
      `[SOURCE]` `[PROVE]`
2.12.8 The **default hard thresholds**: `memory.available<100Mi`, `nodefs.available<10%`,
      `nodefs.inodesFree<5%`, `imagefs.available<15%`, `pid.available<4%`; grace period **0s**.
      Soft thresholds with `eviction-soft-grace-period` and
      `eviction-max-pod-grace-period`; `eviction-minimum-reclaim`;
      `eviction-pressure-transition-period` **5m** and the housekeeping interval of **10s**.
      `[NUM]` `[CFG]` `[RESEARCH]`
2.12.9 The node conditions produced: `MemoryPressure`, `DiskPressure`, `PIDPressure`, and the
      matching taints that stop new pods landing on a sick node. `[CFG]`
2.12.10 The **eviction victim ordering**: BestEffort first, then Burstable, then Guaranteed; within
        a class by priority, then by how much of the starved resource the pod is using **over its
        request**. Prove why `requests == limits` is the strongest protection available. `[PROVE]`
2.12.11 **Eviction vs OOMKill, side by side**: eviction is the kubelet acting proactively, honours a
        grace period, respects QoS and priority, and produces an `Evicted` pod with a `status`
        message; OOMKill is the kernel acting reactively inside a single cgroup, is instant, uses
        `oom_score_adj`, and produces exit 137. Different actor, different signal, different fix.
        `[PROVE]` `[TRAP]`
2.12.12 What the kubelet reclaims *before* evicting: unused images and dead containers
        (§1.14.13) — which is why a disk-pressure event deletes the image you wanted to roll back
        to. `[TRAP]`
2.12.13 `Evicted` pods accumulate as objects and are not restarted (the controller creates *new*
        pods); `PodGC` and `--terminated-pod-gc-threshold` clean them up.
2.12.14 Spot/preemptible instances: the interruption notice, `node-termination-handler`, and why a
        2-minute notice plus a 45-second graceful shutdown is fine for `application-gateway` and
        not fine for the withdrawal run. `[X-REF 18]`
2.12.15 Cluster upgrade as the composite exercise: drain order, PDBs, surge node groups,
        `topologySpreadConstraints` keeping replicas across AZs, and the runbook that survives it
        without an outage. `[BUILD]`

*(15 leaves)*

## §2.13 Autoscaling pods: HPA

2.13.1 The algorithm, exactly:
      `desiredReplicas = ceil(currentReplicas × (currentMetricValue / desiredMetricValue))`,
      clamped to `[minReplicas, maxReplicas]`. `[NUM]` `[PROVE]` `[SOURCE]`
2.13.2 The **tolerance**: no action if the ratio is within **0.1 (10%)** of 1.0, configurable via
      `--horizontal-pod-autoscaler-tolerance` (and per-HPA in newer releases). Why this exists and
      what it costs you at the margin. `[NUM]` `[PROVE]` `[RESEARCH]`
2.13.3 The control-loop period: `--horizontal-pod-autoscaler-sync-period` **15 s** — so the
      *fastest possible* reaction is 15 s plus metric-pipeline lag plus pod start-up, which for a
      JVM is 30–90 s. **HPA cannot absorb a spike; it can only follow a trend.** `[NUM]` `[PROVE]`
      `[TRAP]`
2.13.4 The metric-pipeline lag nobody accounts for: cAdvisor scrape (10–15 s) → metrics-server
      (15 s) → HPA read. Sum it, then compare to the 40k-registration campaign spike. `[NUM]`
      `[PROVE]`
2.13.5 **Utilisation is measured against `requests`, not limits.** A wrong request value silently
      mis-scales everything: halve the request and every pod looks twice as busy. Keep the current
      guide's point and prove it arithmetically. `[PROVE]` `[TRAP]` `[NUM]`
2.13.6 The metric types: `Resource` (`Utilization` / `AverageValue`), `ContainerResource` (the fix
      for a pod whose sidecar dilutes the average), `Pods`, `Object` (with
      `AverageValue`/`Value` and a `describedObject`), `External`. `[CFG]`
2.13.7 The `behavior` block with its **exact defaults**: `scaleUp.stabilizationWindowSeconds` **0**
      with policies "100% or 4 pods per **15 s**, `selectPolicy: Max`";
      `scaleDown.stabilizationWindowSeconds` **300** with policy "100% per **15 s**"
      (commonly tuned to 10%/60 s), `selectPolicy: Min`. Plus `selectPolicy: Disabled` to forbid a
      direction entirely. `[NUM]` `[CFG]` `[RESEARCH]`
2.13.8 The design rule: **scale up fast, scale down slowly.** Then give the QuizStakes tuning:
      `client-restrictions` needs an aggressive scale-up and a 10-minute scale-down because a
      cold pod costs 30 ms budget; `bank-deposits` is bursty-then-idle-23-hours and wants
      scale-to-zero behaviour instead. `[PROVE]`
2.13.9 **Scale to zero**: `minReplicas: 0` with HPA scale-to-zero **beta in 1.37**, and why
      KEDA was the only answer before. What "the first request after zero" costs. `[KEP]`
      `[VERSION-TRAP]` `[RESEARCH]`
2.13.10 Multiple metrics: the HPA computes a desired count per metric and takes the **maximum** —
        so any metric can scale you up, and all must be below target to scale down. `[PROVE]`
2.13.11 Missing metrics and unready pods: pods without a `Ready` condition and pods within the
        initialization period are excluded; missing metrics are treated pessimistically (as 0% for
        scale-down, 100% for scale-up). The flags:
        `--horizontal-pod-autoscaler-initial-readiness-delay` (30 s),
        `--horizontal-pod-autoscaler-cpu-initialization-period` (5 m). `[NUM]` `[CFG]`
        `[RESEARCH]`
2.13.12 **Choose the metric that reflects your bottleneck.** CPU is a poor proxy for an I/O-bound
        service; requests-per-pod, in-flight requests, queue depth, or **consumer lag** are often
        right. Keep the current guide's point and give the QuizStakes mapping: reservations/sec for
        the ledger's caller, lag for the outbox poller, in-flight for the gateway.
        `[PROVE]` `[X-REF 14]`
2.13.13 **KEDA**: `ScaledObject`/`ScaledJob`, 60+ scalers (SQS depth, Kafka lag, Prometheus query,
        cron), the `HPA` it generates underneath, and `activationThreshold` vs `threshold` —
        the practical route to queue-driven and scheduled scaling. `[CFG]` `[RESEARCH]`
2.13.14 Prometheus Adapter / `custom.metrics.k8s.io` and `external.metrics.k8s.io` as the
        alternative plumbing, and the **Metrics API GA in 1.37**. `[RESEARCH]`
2.13.15 **Scaling does not help if the bottleneck is downstream.** More pods against the same
        ledger database is more connections against the same constraint — and at 3 ledger
        instances with partition affinity, adding gateway pods can *hurt*. Keep the current
        guide's warning and quantify it with the pool arithmetic. `[PROVE]` `[X-REF 09]`
        `[X-REF 18]`
2.13.16 Flapping, and the three causes: too tight a target, no stabilisation window, and a metric
        that is itself a function of replica count (the classic feedback loop). `[DIAG]`
2.13.17 HPA and rolling updates interacting: what happens when a roll and a scale-up coincide, and
        why `maxSurge` plus HPA can briefly double your pod count. `[PROVE]`
2.13.18 **Trap:** an HPA and a `replicas:` value in Git fighting each other — every `apply` resets
        the count, the HPA scales it back, and the audit log fills with churn. The fix (omit
        `replicas`, or `ignoreDifferences` in Argo CD). `[TRAP]` `[BUILD]`
2.13.19 Reading it: `kubectl get hpa -w`, `kubectl describe hpa` (the conditions
        `AbleToScale`, `ScalingActive`, `ScalingLimited` and the events), and
        `kubectl get --raw /apis/metrics.k8s.io/v1beta1/pods`. `[CMD]` `[DIAG]`

*(19 leaves)*

## §2.14 Autoscaling pods vertically: VPA and in-place resize

2.14.1 **VPA** components: recommender, updater, admission-controller; `updateMode`
      `Off`/`Initial`/`Recreate`/**`InPlaceOrRecreate`**; `resourcePolicy` with
      `minAllowed`/`maxAllowed`/`controlledResources`/`controlledValues`. `[CFG]` `[RESEARCH]`
2.14.2 `updateMode: Off` as the **most useful mode**: it produces a recommendation you read and
      apply in Git, which is right-sizing as a review activity rather than an autonomous
      mutation. `[PROVE]`
2.14.3 Why VPA and HPA on the same resource conflict: HPA scales replicas from utilisation against
      requests, VPA changes the requests, and each invalidates the other's baseline. The rule:
      HPA on CPU + VPA on memory only, or HPA on a custom metric + VPA on both. `[PROVE]`
      `[TRAP]`
2.14.4 **In-place resize changes this picture** (GA 1.35): the `resize` subresource lets a VPA
      adjust a running pod without recreating it, which is what `InPlaceOrRecreate` uses. State
      what still requires a restart (memory decrease, or `resizePolicy:
      RestartContainer`). `[KEP]` `[RESEARCH]`
2.14.5 The resize mechanics to be able to describe: the request goes to `pods/resize`, the kubelet
      evaluates feasibility against node allocatable, and the pod gets
      `PodResizePending` with reason `Deferred` (retry later) or `Infeasible` (never), or
      `PodResizeInProgress`. `[SOURCE]` `[DIAG]`
2.14.6 **The JVM problem with vertical resize**: the heap was sized from the cgroup limit *at JVM
      start*, so raising `limits.memory` in place does **not** raise `-Xmx`. Resizing memory
      without restarting a JVM buys you headroom against OOMKill and nothing else. This is exactly
      the kind of interaction the bible must state. `[PROVE]` `[TRAP]` `[NUM]`
2.14.7 Raising `limits.cpu` in place *does* help immediately (the quota is a kernel setting), but
      `availableProcessors()` and every pool sized from it were fixed at start-up. Same shape,
      different consequence. `[PROVE]`
2.14.8 Pod-level in-place vertical scaling (beta 1.36) and the pod-level resource budget from
      §1.28.14. `[RESEARCH]`
2.14.9 The commercial/OSS right-sizing tools worth naming (Goldilocks, KRR, StormForge,
      ScaleOps, Cast AI) and what they all actually do: read the same metrics and compute the same
      percentiles you could compute yourself. `[RESEARCH]`
2.14.10 The right-sizing procedure for the QuizStakes estate, executed: for each of the eight
        services in Appendix A.6, derive requests/limits from the stated heap and instance count,
        then say which would benefit from VPA-`Off` recommendations. `[NUM]` `[BUILD]`

*(10 leaves)*

## §2.15 Autoscaling nodes

2.15.1 The gap HPA leaves: more pods need more nodes, and **HPA without node autoscaling just gets
      you pods stuck in `Pending`**. Keep the current guide's line. `[PROVE]`
2.15.2 **Cluster Autoscaler**: watches for unschedulable pods, picks a node group whose template
      would fit them, and scales the ASG/MIG; scales down a node whose pods can all be placed
      elsewhere. The key parameters: `--scale-down-utilization-threshold` (0.5),
      `--scale-down-unneeded-time` (10m), `--scale-down-delay-after-add` (10m),
      `--max-node-provision-time` (15m), `--expander` (`random`/`most-pods`/`least-waste`/
      `priority`/`price`), and the `cluster-autoscaler.kubernetes.io/safe-to-evict` annotation.
      `[NUM]` `[CFG]` `[RESEARCH]`
2.15.3 Why Cluster Autoscaler is slow: it must scale an ASG, wait for an instance, wait for the
      kubelet to register, wait for the CNI and the image pull — **3–4 minutes** typical. `[NUM]`
      `[RESEARCH]`
2.15.4 The node-group constraint: Cluster Autoscaler needs homogeneous groups and picks a group,
      not an instance type, so you pre-declare your shapes.
2.15.5 **Karpenter v1**: `NodePool` (requirements, limits, disruption policy, weights) +
      `EC2NodeClass` (AMI, subnets, security groups, user data, instance profile) + `NodeClaim`
      (one per node it created). It provisions **instances directly** and bin-packs the pending
      pods, so **45–60 s** to a Ready node. `[NUM]` `[CFG]` `[RESEARCH]`
2.15.6 Karpenter's `disruption` block: `consolidationPolicy`
      (`WhenEmpty`/`WhenEmptyOrUnderutilized`), `consolidateAfter`, `expireAfter`, and
      **`budgets` — default one budget of 10%**. Plus the `karpenter.sh/do-not-disrupt` annotation
      as the per-pod opt-out. `[NUM]` `[CFG]` `[RESEARCH]`
2.15.7 Consolidation is aggressive by design: it will delete a node to repack pods more cheaply, so
      **your workloads must tolerate being moved**, which means PDBs, graceful shutdown and
      topology spread are prerequisites, not extras. Say this plainly — it is the most common
      Karpenter surprise. `[PROVE]` `[TRAP]`
2.15.8 Spot handling: `capacity-type: [spot, on-demand]`, price-capacity-optimised allocation,
      interruption handling via the SQS queue, and the shape of workload that may take spot at
      QuizStakes (read-only views and batch, never the money path). `[X-REF 18]`
2.15.9 The comparison table: Cluster Autoscaler vs Karpenter across provisioning latency,
      instance-type flexibility, bin-packing quality, consolidation, spot support, operational
      complexity, and cloud portability. `[NUM]`
2.15.10 **Overprovisioning** as the answer to autoscaling latency: a low-priority pause-image
        Deployment holding reserved capacity that real pods preempt. The manifest, the arithmetic
        for a 40k-registration launch, and the cost. `[BUILD]` `[NUM]` `[PROVE]`
2.15.11 GKE **Autopilot** and EKS **Fargate/Auto Mode** as "no nodes to manage" — what you gain and
        the constraints you accept (no DaemonSets, per-pod pricing, limited privileges).
        `[X-REF 18]`
2.15.12 The interaction chain to be able to draw end to end: request rate ↑ → HPA scales replicas →
        pods `Pending` → Karpenter provisions → node Ready → image pull → JVM start → readiness →
        endpoints → traffic. Sum the latency and compare it to the campaign spike. `[NUM]`
        `[PROVE]`

*(12 leaves)*

## §2.16 StatefulSets and stateful workloads in practice

2.16.1 What a StatefulSet actually guarantees, and what it does not: stable name, stable DNS,
      stable per-ordinal storage, ordered lifecycle. It does **not** give you leader election,
      replication, backup, or any awareness of your data.
2.16.2 The headless-Service + `serviceName` requirement, and the per-pod DNS name
      `funds-ledger-0.funds-ledger.quizstakes-money.svc.cluster.local` as the thing that makes
      peer discovery possible. `[PROVE]`
2.16.3 `podManagementPolicy: Parallel` as the fix for "my 5-replica cluster takes 10 minutes to
      start because pod 0 waits for readiness".
2.16.4 The `OrderedReady` stall: pod 1 never becomes ready, so pods 2..N never start and the
      rollout is stuck forever. Diagnosis and the `partition`-based recovery. `[DIAG]` `[TRAP]`
2.16.5 `partition` as a canary knob for a stateful rollout, worked as a procedure.
2.16.6 `persistentVolumeClaimRetentionPolicy` and the scale-down data question: `Retain` keeps a
      1 TB volume billing forever after you scale from 5 to 3; `Delete` loses it if the scale-down
      was a mistake. There is no safe default — say which you would pick and why. `[PROVE]`
      `[TRAP]`
2.16.7 The **1.37 `Recreate` update strategy** for StatefulSets and the case it serves. `[KEP]`
      `[RESEARCH]`
2.16.8 `ordinals.start` and what it enables (splitting a StatefulSet across clusters for a
      migration). `[RESEARCH]`
2.16.9 Leader election in Kubernetes without a StatefulSet: the `coordination.k8s.io/v1` `Lease`
      object, the `LeaderElector` pattern, and Spring's `LockRegistryLeaderInitiator` — this is
      the correct implementation of Appendix B.4's "central scheduler plus leader election, never
      per-instance cron" for the `bank-withdrawal` run. `[BUILD]` `[PROVE]`
2.16.10 Why `FundsLedger`'s **partition affinity by client id** is *not* a StatefulSet requirement:
        the affinity is a routing decision made by callers, not identity owned by the pod. But
        state the consequence the scenario names — **scale 3 instances to 4 and ownership shifts**
        — and what that means for a rolling update (in-flight reservations, the in-memory expiry
        index, and the split-brain risk of two instances believing they own a client). This is the
        best design discussion in the topic. `[PROVE]` `[X-REF 22]`
2.16.11 The rebalancing options and their trade-offs: consistent hashing with virtual nodes, a
        coordination service, or accepting a brief unavailability window per partition. Give the
        recommendation for a 150 ms stake-reservation budget. `[PROVE]` `[X-REF 22]`
2.16.12 Operators for stateful systems: CloudNativePG, Crunchy/Zalando Postgres, Strimzi (Kafka),
        Redis Operator, Elastic Cloud on Kubernetes — what an operator adds over a StatefulSet
        (failover, backup, version upgrades, topology awareness). Forward to §2.26.
2.16.13 The decision the bible must actually make: **the QuizStakes ledger database stays on its
        own managed instance** (Appendix B.2), and here is the argument — cross-position invariants,
        pause sensitivity, backup/PITR requirements, and the fact that a Postgres operator does not
        remove the operational burden, it relocates it. `[PROVE]` `[X-REF 09]` `[X-REF 18]`

*(13 leaves)*

## §2.17 Jobs, CronJobs, and batch work

2.17.1 The Job completion models: single (`completions` unset), fixed-count parallel
      (`completions` + `parallelism`), work-queue (`completions` unset, `parallelism` > 1), and
      **`completionMode: Indexed`** with `JOB_COMPLETION_INDEX` — which is how you shard the
      `bank-deposits` file ingestion across a worker pool. `[CFG]` `[BUILD]`
2.17.2 `backoffLimit` **6** with exponential backoff capped at 6 minutes, and
      `backoffLimitPerIndex` + `maxFailedIndexes` for indexed jobs. `[NUM]` `[CFG]`
2.17.3 `podFailurePolicy` — acting on **exit codes** and on pod conditions
      (`DisruptionTarget`, `ConfigIssue`) so an infrastructure disruption does not consume your
      retry budget. `[CFG]` `[PROVE]`
2.17.4 `activeDeadlineSeconds` (kills the job, reason `DeadlineExceeded`) vs `backoffLimit`
      (counts failures) vs `ttlSecondsAfterFinished` (cleans up the object). Three different
      timers people conflate. `[TRAP]`
2.17.5 `suspend: true` for queued/gated jobs, and **Kueue** as the queueing layer above it.
      `[RESEARCH]`
2.17.6 The 1.34 Job-controller change: separate accounting for **active / failed / terminating**
      pods with `status.terminating`, and configurable pod-replacement policy
      (`podReplacementPolicy: TerminatingOrFailed | Failed`) — which fixes the long-standing
      "two pods running the same index during a disruption" hazard. `[KEP]` `[PROVE]`
      `[RESEARCH]`
2.17.7 Jobs and native sidecars: before 1.29 a sidecar kept the pod alive forever and the Job never
      completed. With `restartPolicy: Always` init containers, the sidecar is torn down when the
      app container exits. This is *the* reason native sidecars exist. `[PROVE]` `[VERSION-TRAP]`
2.17.8 **CronJob** fields with defaults: `schedule`, `timeZone`, `concurrencyPolicy`
      (`Allow` default / `Forbid` / `Replace`), `startingDeadlineSeconds`, `suspend`,
      `successfulJobsHistoryLimit` **3**, `failedJobsHistoryLimit` **1**. `[NUM]` `[CFG]`
2.17.9 The **100 missed schedules** rule: if the controller sees more than 100 missed start times it
      gives up and logs an error, and your nightly job silently stops running. Combined with
      `startingDeadlineSeconds` being unset, this is a real and quiet outage. `[NUM]` `[TRAP]`
      `[PROVE]`
2.17.10 **CronJob is at-least-once and has no exclusivity guarantee.** `concurrencyPolicy: Forbid`
        reduces overlap but is not a lock. For the `bank-withdrawal` payment run — where "twice
        means duplicate payouts" — the design must be a distributed lock plus an idempotent,
        resumable run, exactly as the scenario says. Work the double-payout failure case.
        `[PROVE]` `[TRAP]` `[X-REF 14]`
2.17.11 The `bank-deposits` shape from the scenario: **file-arrival trigger → container worker
        pool**, once daily, bursty, idle 23 hours. Design it as an event-triggered indexed Job with
        `parallelism` tuned to the file size, and argue why a long-running Deployment is the wrong
        shape. `[BUILD]` `[PROVE]`
2.17.12 Migrations as a Job, and the three ways to sequence them against a rollout: an init
        container (runs per pod — wrong for a migration), a pre-install/pre-upgrade Helm hook, or
        an Argo CD sync wave. Give the recommendation and the expand/contract requirement.
        `[PROVE]` `[X-REF 09]`
2.17.13 Batch observability: why a failed Job is silent by default and what to alert on
        (`kube_job_status_failed`, a job that has not succeeded within its window). `[X-REF 20]`

*(13 leaves)*

## §2.18 DNS in practice

2.18.1 The cluster DNS contract: `<service>.<namespace>.svc.<cluster-domain>` A/AAAA records,
      SRV records `_<port-name>._<protocol>.<service>.<namespace>.svc.<domain>`, headless
      services resolving to all pod IPs, pod records
      `<ip-with-dashes>.<namespace>.pod.<domain>`, and `ExternalName` returning a CNAME.
      `[SOURCE]`
2.18.2 The pod's `/etc/resolv.conf`, exactly as the kubelet writes it: `nameserver <kube-dns
      ClusterIP>`, `search <ns>.svc.cluster.local svc.cluster.local cluster.local [host domains]`,
      `options ndots:5`. `[SOURCE]` `[NUM]`
2.18.3 **The `ndots:5` trap, proved.** Any name with fewer than 5 dots is tried against every
      search domain **first**. So resolving `api.stripe.com` (3 dots) issues
      `api.stripe.com.quizstakes-money.svc.cluster.local`,
      `api.stripe.com.svc.cluster.local`, `api.stripe.com.cluster.local` — three NXDOMAINs, ×2 for
      A and AAAA — before the correct query. **Six wasted round trips per external lookup.** At
      QuizStakes' external call volume this is a measurable latency and CoreDNS load problem.
      `[PROVE]` `[NUM]` `[TRAP]`
2.18.4 The three fixes, with trade-offs: a **trailing dot** (`api.stripe.com.`) to make it fully
      qualified; per-pod `dnsConfig: options: [{name: ndots, value: "2"}]`; or client-side DNS
      caching. And why lowering `ndots` globally breaks short-name service discovery. `[PROVE]`
      `[CFG]`
2.18.5 `dnsPolicy` values and exactly when each is right: `ClusterFirst` (default),
      `ClusterFirstWithHostNet` (**required** for `hostNetwork` pods, or they get the node's
      resolver and cannot see cluster DNS), `Default` (inherit the node's), `None` (+ mandatory
      `dnsConfig`). `[CFG]` `[TRAP]`
2.18.6 `dnsConfig`: `nameservers`, `searches`, `options` — and the limits (3 nameservers, 32 search
      domains, 2048-character search list). `[NUM]` `[CFG]`
2.18.7 The JVM's DNS caching, which is the other half of every Kubernetes DNS incident:
      `networkaddress.cache.ttl` (**default 30 s** with no security manager; historically
      *forever*), `networkaddress.cache.negative.ttl` (**10 s**), and why a JVM can keep hitting a
      dead pod IP long after the endpoint changed. Set it explicitly. `[NUM]` `[TRAP]` `[PROVE]`
      `[X-REF 10]`
2.18.8 **NodeLocal DNSCache**: a DaemonSet cache on `169.254.20.10` that removes most CoreDNS
      round trips and the conntrack-race UDP timeouts. When it is worth deploying. `[RESEARCH]`
2.18.9 The classic 5-second DNS timeout: the kernel conntrack race on parallel UDP queries from the
      same socket (`--random-fully`, `single-request-reopen`), which manifests as *exactly* 5.000 s
      latencies. Recognising the signature is the whole skill. `[DIAG]` `[NUM]` `[RESEARCH]`
2.18.10 CoreDNS scaling and configuration: the `Corefile` plugin chain
        (`errors`, `health`, `ready`, `kubernetes`, `prometheus`, `forward`, `cache`, `loop`,
        `reload`, `loadbalance`), `cache` TTLs, `autopath` as an ndots mitigation, replica sizing
        (~1 replica per 8–16 nodes as a starting rule), and the `cluster-proportional-autoscaler`.
        `[CFG]` `[NUM]` `[RESEARCH]`
2.18.11 `stubDomains`/`forward` for split-horizon DNS to on-prem or to a VPC private zone.
        `[X-REF 18]`
2.18.12 Debugging DNS from inside: `kubectl run -it --rm dnsutils --image=…`,
        `nslookup client-restrictions.quizstakes-money.svc.cluster.local`, `dig +search`,
        `dig @169.254.20.10`, `cat /etc/resolv.conf`, and checking CoreDNS logs with the `log`
        plugin enabled. `[CMD]` `[DIAG]`
2.18.13 Why DNS and not a VIP-per-name: the docs' own argument — DNS TTLs are widely ignored,
        clients cache indefinitely, and round-robin DNS with frequent changes would create enormous
        DNS load. Hence proxying. `[SOURCE]` `[PROVE]`

*(13 leaves)*

## §2.19 Service networking decisions

2.19.1 The decision list for exposing a QuizStakes service: internal-only (`ClusterIP`),
      internal with client-side balancing (headless), external HTTP (Gateway/Ingress),
      external non-HTTP (`LoadBalancer` + NLB), node-local (`internalTrafficPolicy: Local`),
      external-name shim (`ExternalName`).
2.19.2 Why `NodePort` is almost never the right production answer, and the two cases where it is.
2.19.3 The cost dimension: one `LoadBalancer` Service per microservice is one cloud LB per
      microservice. Compute the monthly cost for 25 QuizStakes services and compare to one
      Gateway. `[NUM]` `[X-REF 18]`
2.19.4 Cross-AZ traffic cost and latency, and how `trafficDistribution: PreferSameZone` /
      topology-aware routing addresses both — with the availability trade-off (a zone with too
      few endpoints falls back). `[NUM]` `[PROVE]` `[X-REF 18]`
2.19.5 Client-side load balancing vs Service-VIP balancing: why a JVM with a long-lived HTTP/2 or
      gRPC connection pinned to one pod defeats `ClusterIP` balancing entirely, and the three
      fixes (headless + client-side LB, a mesh, or per-request connection cycling). This is a
      genuinely common and badly understood production problem. `[PROVE]` `[TRAP]` `[X-REF 10]`
2.19.6 The same problem for JDBC and Redis pools: a pool established at start-up survives the
      endpoint list changing, so scaling the ledger does not rebalance existing callers.
      `[PROVE]` `[X-REF 09]`
2.19.7 Preserving the client IP end to end: `externalTrafficPolicy: Local`, `X-Forwarded-For`,
      the PROXY protocol, and an NLB in IP-target mode. Needed for QuizStakes' geo/fraud signals.
      `[X-REF 10]`
2.19.8 Egress: how a pod reaches the internet (SNAT at the node, or a NAT gateway), why the PSP
      needs a **stable source IP** for allow-listing, and the three ways to get one (a dedicated
      egress node pool with an EIP, a NAT gateway per subnet, or an egress gateway/mesh).
      This is the mechanism behind "only `card-payments` may egress to the PSP".
      `[PROVE]` `[X-REF 18]`
2.19.9 `hostNetwork: true` and `hostPort`: what they buy (no NAT hop, a fixed port), what they cost
      (one pod per node per port, no network isolation, `ClusterFirstWithHostNet` needed), and why
      Baseline PSS forbids them.
2.19.10 IPv4 exhaustion as a real cluster-design constraint: pods-per-node vs subnet size, the
        AWS VPC CNI's ENI/secondary-IP arithmetic and prefix delegation, and how it caps
        `maxPods`. `[NUM]` `[X-REF 18]`
2.19.11 Connection tracking limits: `nf_conntrack_max`, the "table full, dropping packet" dmesg
        line, and why a high-connection-rate service on a small node hits it.
        `[DIAG]` `[X-REF 11]`
2.19.12 The 1.37 networking items worth knowing: watch-based route controller reconciliation
        (beta) and the ongoing nftables-default work. `[RESEARCH]`

*(12 leaves)*

## §2.20 RBAC and workload identity

2.20.1 The four objects and the two axes: `Role`/`RoleBinding` (namespaced) and
      `ClusterRole`/`ClusterRoleBinding` (cluster-wide) — plus the fifth combination that trips
      people: a **`RoleBinding` referencing a `ClusterRole`** grants those rules in one namespace,
      which is the standard way to reuse a role definition. `[PROVE]` `[TRAP]`
2.20.2 A rule's shape: `apiGroups`, `resources` (+ `resources/subresource`), `resourceNames`,
      `verbs`, `nonResourceURLs`. And that RBAC is **allow-only and additive** — there is no deny
      rule, so you cannot subtract a permission. `[PROVE]` `[SOURCE]`
2.20.3 Subjects: `User`, `Group`, `ServiceAccount`, and the built-in groups
      `system:authenticated`, `system:unauthenticated`, `system:serviceaccounts`,
      `system:serviceaccounts:<ns>`, `system:masters`.
2.20.4 The default ClusterRoles: `cluster-admin`, `admin`, `edit`, `view`, and the
      `system:*` roles. Why `edit` in a namespace is nearly namespace-admin (it can read every
      Secret). `[TRAP]`
2.20.5 **Aggregated ClusterRoles** (`aggregationRule`) and the
      `rbac.authorization.k8s.io/aggregate-to-view` labels — the extension point for CRDs.
2.20.6 **Escalation prevention**: you cannot grant a permission you do not hold, and the
      `escalate`/`bind`/`impersonate` verbs are the explicit exceptions. `[PROVE]`
2.20.7 Authentication mechanisms, named: client certificates, bearer tokens, service account
      tokens, OIDC, webhook token authentication, and the **structured authentication config**
      that went **stable in 1.35**. Note there is no `User` object — users come from outside.
      `[TRAP]` `[RESEARCH]`
2.20.8 **ServiceAccount tokens**: legacy long-lived Secret-based tokens vs **bound tokens**
      (projected, audience-scoped, time-limited, auto-rotated — default since 1.22), and the
      `TokenRequest` API. Why the legacy token in a Secret is a standing credential you should
      delete. `[PROVE]` `[VERSION-TRAP]`
2.20.9 Cloud workload identity: **IRSA** (OIDC federation, `eks.amazonaws.com/role-arn`
      annotation, the projected token, `AssumeRoleWithWebIdentity`) and **EKS Pod Identity**
      (agent-based, no OIDC trust policy per cluster) — plus GKE Workload Identity and AKS
      Workload Identity. This is Appendix B.4's "workload identity, short-lived credentials".
      `[PROVE]` `[X-REF 18]`
2.20.10 The RBAC each QuizStakes workload actually needs: **most need nothing**
        (`automountServiceAccountToken: false`); the config-reloader needs `get`/`watch` on one
        ConfigMap; the leader-elected withdrawal runner needs `get`/`update` on one `Lease`; the
        operator needs its CRD plus `create` on Pods. `[BUILD]` `[YAML]`
2.20.11 Auditing RBAC: `kubectl auth can-i --list --as=system:serviceaccount:quizstakes-money:funds-ledger`,
        `kubectl-who-can`, `rakkess`, `rbac-tool`, and reading the audit log for
        `authorization.k8s.io` decisions. `[CMD]` `[X-REF 20]`
2.20.12 The privilege-escalation paths inside a cluster worth understanding as a defender: a
        ServiceAccount with `create pods` (mount any Secret, use any SA), with `create
        pods/exec`, with `escalate`, with `impersonate`, with `patch nodes`, or with access to a
        privileged DaemonSet's SA. `[PROVE]` `[X-REF 13]`
2.20.13 Admission control as the layer RBAC cannot express: "no privileged pods" is not a verb, so
        it belongs to Pod Security Admission, `ValidatingAdmissionPolicy`, or a webhook.
        Forward to §2.22.

*(13 leaves)*

## §2.21 Secrets in practice

2.21.1 Restating the boundary: a Kubernetes Secret is a base64 blob in etcd with RBAC in front of
      it. That is the whole security model unless you add encryption at rest.
2.21.2 **Encryption at rest**: `EncryptionConfiguration`, the provider list order (first provider
      encrypts, all are tried for decrypt), `identity` (no-op), `aescbc`, `secretbox`, `aesgcm`,
      and **`kms` v2** (envelope encryption with a DEK cached in the apiserver, GA since 1.29).
      Plus the `secrets-encryption` rotation procedure and the **Storage Version Migration**
      controller (default-enabled in 1.37) that rewrites existing objects. `[CFG]` `[PROVE]`
      `[RESEARCH]`
2.21.3 The three architectures, compared honestly: (a) Secrets in etcd with KMS encryption;
      (b) **External Secrets Operator** syncing from AWS Secrets Manager/Vault into a Secret
      (`SecretStore`/`ClusterSecretStore`/`ExternalSecret`/`PushSecret`, `refreshInterval`);
      (c) **Secrets Store CSI Driver** mounting them as files without ever creating a Secret
      object (`SecretProviderClass`, and the optional `secretObjects` sync). Give the
      recommendation for QuizStakes and the reason. `[PROVE]` `[RESEARCH]`
2.21.4 Why (c) is stronger and (b) is more practical: file-only means no Secret object to leak via
      RBAC, but almost every Java library expects an environment variable or a
      `spring.datasource.password` property. Show the Spring `configtree` binding that makes (c)
      workable. `[BUILD]` `[X-REF 07]`
2.21.5 Rotation as the actual requirement: Appendix B.4 says vendor credentials and signing keys
      are rotated, so the mechanism must include the application **noticing** — file watch,
      short-TTL re-read, or a rolling restart triggered by the secret version. A rotated secret
      that the app read once at start-up is not rotated. `[PROVE]` `[TRAP]`
2.21.6 Sealed Secrets / SOPS / `git-crypt` for the GitOps case: encrypted-in-Git secrets, the
      controller that decrypts, and the key-management problem you have just moved rather than
      solved. `[X-REF 17]`
2.21.7 What leaks a secret in practice, as a checklist: `kubectl get secret -o yaml`, a pod's
      environment in a crash dump or an APM trace, `/proc/<pid>/environ`, a log line at DEBUG, a
      Helm `--set` in shell history, `kubectl describe` on a ConfigMap that should have been a
      Secret, an image layer, a `docker history` `ARG`, and the audit log itself. `[TRAP]`
      `[X-REF 13]`
2.21.8 QuizStakes' actual secret inventory and where each belongs: the token signing key (managed
      key store, never in the cluster — Appendix B.4), the PSP credential (secret store, rotated,
      only reachable by `card-payments`), the ledger database password (workload identity/IAM auth
      instead of a password where possible), the PII database's separate credentials, and the
      identity vendor's API key. `[BUILD]` `[PROVE]`
2.21.9 Auditing secret access: which RBAC subjects can `get secrets` in `quizstakes-money`, and the
      audit-policy rule that records it. `[CMD]` `[X-REF 20]`

*(9 leaves)*

## §2.22 Pod Security Standards, security contexts, and network policy

2.22.1 **Pod Security Admission**: the built-in admission controller enforcing the three **Pod
      Security Standards** profiles, configured by **namespace labels**
      `pod-security.kubernetes.io/<enforce|audit|warn>[-version]=<privileged|baseline|restricted>`.
      `[CFG]` `[SOURCE]`
2.22.2 The three modes: `enforce` (reject), `audit` (annotate the audit event), `warn` (return a
      warning to the client). The recommended rollout: `warn` + `audit` first, `enforce` after you
      have fixed everything. `[PROVE]`
2.22.3 **Baseline**, control by control with the exact field paths and allowed values:
      HostProcess (Windows), host namespaces (`hostNetwork`/`hostPID`/`hostIPC` must be
      unset/false), privileged containers, **capabilities `add` restricted to a 13-item allow-list**
      (`AUDIT_WRITE`, `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `FSETID`, `KILL`, `MKNOD`,
      `NET_BIND_SERVICE`, `SETFCAP`, `SETGID`, `SETPCAP`, `SETUID`, `SYS_CHROOT`),
      `hostPath` volumes forbidden, `hostPort` forbidden, **probe and lifecycle-hook `host`
      fields forbidden (1.34+)**, AppArmor limited to `RuntimeDefault`/`Localhost`, SELinux type
      limited to four values and `user`/`role` forbidden, `procMount: Default`, seccomp not
      `Unconfined`, and sysctls limited to a named safe set (`kernel.shm_rmid_forced`,
      `net.ipv4.ip_local_port_range`, `net.ipv4.ip_unprivileged_port_start`,
      `net.ipv4.tcp_syncookies`, `net.ipv4.ping_group_range`,
      `net.ipv4.ip_local_reserved_ports` (1.27+), `net.ipv4.tcp_keepalive_time`,
      `net.ipv4.tcp_fin_timeout`, `net.ipv4.tcp_keepalive_intvl` (1.29+)). `[SOURCE]` `[NUM]`
      `[RESEARCH]`
2.22.4 **Restricted**, the additional controls: volume types limited to the safe set
      (`configMap`, `csi`, `downwardAPI`, `emptyDir`, `ephemeral`, `image`, `persistentVolumeClaim`,
      `projected`, `secret`), `allowPrivilegeEscalation: false`,
      `runAsNonRoot: true`, `runAsUser != 0`, `capabilities.drop` must include `ALL` with only
      `NET_BIND_SERVICE` addable, and `seccompProfile.type` must be
      `RuntimeDefault` or `Localhost`. `[SOURCE]` `[NUM]`
2.22.5 What Restricted breaks for a typical Spring Boot image, and the fix for each: a base image
      whose `USER` is a name not a UID; a JVM wanting a writable `/tmp`; an app binding port 80;
      an `exec` probe needing a shell. `[TRAP]` `[BUILD]`
2.22.6 `securityContext` at pod level vs container level, and which fields live where:
      pod-level `runAsUser`, `runAsGroup`, `runAsNonRoot`, `fsGroup`, `fsGroupChangePolicy`,
      `supplementalGroups`, `sysctls`, `seLinuxOptions`, `seccompProfile`, `appArmorProfile`,
      `seLinuxChangePolicy`; container-level `capabilities`, `privileged`, `procMount`,
      `readOnlyRootFilesystem`, `allowPrivilegeEscalation`, plus overrides of the pod-level ones.
      `[SOURCE]` `[CFG]`
2.22.7 `fsGroup` and `fsGroupChangePolicy: OnRootMismatch` — the volume-ownership mechanism, and
      why `Always` on a large PV makes pod start-up take minutes (a recursive `chown` of a million
      files). `[PROVE]` `[TRAP]` `[NUM]`
2.22.8 Enforcement beyond PSS: `ValidatingAdmissionPolicy` with CEL (GA 1.30),
      `MutatingAdmissionPolicy` (1.36+), Kyverno, OPA Gatekeeper — and the rule for choosing:
      in-tree CEL for simple field assertions, a policy engine when you need mutation,
      generation, image verification or a report pipeline. `[PROVE]` `[RESEARCH]`
2.22.9 A worked `ValidatingAdmissionPolicy` for QuizStakes: reject any pod in `quizstakes-money`
      whose image is not from the internal registry, or which sets `hostNetwork`, or whose memory
      request differs from its limit. `[BUILD]` `[YAML]`
2.22.10 The admission-controller order and where each thing happens: authn → authz → **mutating
        webhooks** → object schema validation → **`ValidatingAdmissionPolicy`** → **validating
        webhooks** → etcd. Getting this order right explains why a mutating webhook can make a pod
        pass a validating policy. `[PROVE]` `[SOURCE]`
2.22.11 Webhook operational hazards: `failurePolicy: Fail` on a down webhook wedges the whole
        cluster (including the webhook's own pods — the classic deadlock),
        `timeoutSeconds`, `namespaceSelector` to exclude `kube-system`, and
        `reinvocationPolicy`. `[TRAP]` `[DIAG]`
2.22.12 **NetworkPolicy**: `podSelector` (empty = all pods in the namespace), `policyTypes`
        (`Ingress`/`Egress`; **defaults to `Ingress` when omitted** — a real trap),
        `ingress[].from` / `egress[].to` with `podSelector`, `namespaceSelector`, and `ipBlock`
        (`cidr` + `except`), `ports` with `port`/`endPort`/`protocol` (TCP/UDP/SCTP). `[SOURCE]`
        `[CFG]`
2.22.13 The isolation semantics, precisely: a pod is **non-isolated until some policy selects it**,
        then only explicitly allowed traffic is permitted; policies are **additive** with OR
        semantics; and **both** the source's egress and the destination's ingress must allow a
        connection. Prove each clause. `[PROVE]`
2.22.14 The selector-combination trap: `from: [{namespaceSelector: X, podSelector: Y}]` (one list
        item — AND) vs `from: [{namespaceSelector: X}, {podSelector: Y}]` (two items — OR). One
        YAML dash is the difference between "pods labelled Y in namespaces labelled X" and "any
        pod in X, or any pod labelled Y in *this* namespace". `[TRAP]` `[PROVE]`
2.22.15 The default-deny pattern and the pieces you must then re-allow: DNS to CoreDNS
        (UDP/TCP 53 — forgetting this is the single most common NetworkPolicy outage), the
        API server, the metrics scraper, and the cloud metadata endpoint (which you should
        *block*). `[BUILD]` `[TRAP]`
2.22.16 **What NetworkPolicy cannot do**: force traffic through a proxy, redirect, NAT, operate at
        L7, block localhost or node-to-pod traffic, filter ICMP, or apply to `hostNetwork` pods.
        And it needs a CNI that implements it — **a policy with no enforcing plugin silently does
        nothing**, which is the most dangerous failure mode in this section. `[SOURCE]` `[TRAP]`
        `[PROVE]`
2.22.17 CNI-specific extensions worth naming: Calico `GlobalNetworkPolicy`/`NetworkSet` with
        ordering and deny rules, Cilium `CiliumNetworkPolicy` with L7 (HTTP method/path, Kafka
        topic) and DNS-based egress, and the emerging `AdminNetworkPolicy`/
        `BaselineAdminNetworkPolicy` (cluster-scoped, with real deny and priority). `[RESEARCH]`
2.22.18 The QuizStakes policy set the bible must ship: default-deny in all three namespaces;
        `application-gateway` may reach `router-int` only; only `card-payments` may egress to the
        PSP CIDR; `personal-details` accepts ingress only from `profile-service` and
        `account-opening`; `funds-ledger` accepts only from `payment-service` and
        `bonus-service`; nothing may reach the cloud metadata IP. This is the card-data-isolation
        and PII-blast-radius requirement made concrete. `[BUILD]` `[YAML]` `[PROVE]`
2.22.19 Testing network policy: a `netshoot` pod, `nc -zv` matrices, `cilium connectivity test`,
        and asserting the *denials*, not just the allows. `[CMD]` `[X-REF 16]`

*(19 leaves)*

## §2.23 Multi-tenancy and cluster hygiene

2.23.1 `ResourceQuota` in full: compute quotas (`requests.cpu`, `requests.memory`, `limits.cpu`,
      `limits.memory`, `requests.ephemeral-storage`, `hugepages-<size>`), object counts
      (`pods`, `services`, `secrets`, `configmaps`, `persistentvolumeclaims`,
      `services.loadbalancers`, `services.nodeports`, `count/<resource>.<group>`), storage quotas
      per StorageClass, and `scopes`/`scopeSelector` (`Terminating`, `NotTerminating`,
      `BestEffort`, `NotBestEffort`, `PriorityClass`). `[CFG]` `[SOURCE]`
2.23.2 The quota trap: **once a quota constrains `requests.cpu`, every pod in the namespace must
      declare it**, so previously-valid manifests start failing admission — and the fix is a
      `LimitRange` supplying defaults. `[TRAP]` `[PROVE]`
2.23.3 `LimitRange`: `default`, `defaultRequest`, `min`, `max`, `maxLimitRequestRatio`, per
      `Container`/`Pod`/`PersistentVolumeClaim`. `[CFG]`
2.23.4 The tenancy models, compared: namespace-per-team in a shared cluster (cheap, weak
      isolation), cluster-per-team (strong, expensive, 25 × $73/month plus 25 upgrade cycles),
      virtual clusters (vCluster, Capsule, HNC), and node pools per tenant. Give the QuizStakes
      answer. `[NUM]` `[PROVE]`
2.23.5 What a namespace does **not** isolate, restated as a security statement: the kernel, the
      node, the pod network by default, CRDs, and cluster-scoped objects.
2.23.6 `PriorityClass` as the capacity-shedding policy (§2.9.9) and the honest warning that
      preemption without PDBs plus graceful shutdown is just an outage with extra steps.
2.23.7 Node pools as the real isolation boundary for the card-data requirement: a tainted,
      labelled, separately-IAM'd node group that only `card-payments` tolerates. `[BUILD]`
      `[X-REF 18]`
2.23.8 Cluster hygiene checks worth automating: pods without requests, pods without probes, pods
      running as root, `:latest` images, Deployments with one replica and a PDB, orphaned PVCs,
      Secrets nobody mounts, and unused Services. `Popeye`, `polaris`, `kube-score`,
      `kube-linter`, `kubent`/`pluto` for deprecated APIs. `[CMD]` `[BUILD]`

*(8 leaves)*

## §2.24 Packaging: Helm, Kustomize, and the templating decision

2.24.1 The problem: the same manifest set differs by environment in a handful of values, and
      copy-paste-per-environment rots immediately.
2.24.2 **Helm** anatomy: `Chart.yaml` (`apiVersion: v2`, `type`, `dependencies`), `values.yaml`,
      `templates/`, `_helpers.tpl`, `NOTES.txt`, `crds/`, `.helmignore`, and the packaged
      `.tgz`.
2.24.3 The templating surface: Go templates plus Sprig, `{{ .Values }}`, `{{ .Release }}`,
      `{{ .Chart }}`, `{{ .Capabilities }}`, `{{ .Files }}`, `include`/`define`,
      `tpl`, `required`, `toYaml`/`nindent`, `lookup`, and the whitespace-control operators
      that make or break readability. `[CFG]`
2.24.4 The release model: a **release** is a named installation with a **revision history** stored
      in a Secret (`sh.helm.release.v1.<name>.v<n>`), which is what makes `helm rollback` possible
      and what makes a 1 MiB limit a real chart-size constraint. `[PROVE]` `[NUM]`
2.24.5 **Helm 4 changes**: **server-side apply** is the default for new releases (Helm 3 releases
      keep client-side after upgrade), conflicts are now hard errors instead of silent overwrites,
      `--wait` uses **kstatus** and therefore needs the `watch` verb on all chart resources, and
      post-renderers must be **plugins** (a WASM-capable plugin system) rather than an executable
      path. `[VERSION-TRAP]` `[RESEARCH]`
2.24.6 The command surface: `helm install`, `upgrade --install`, `--atomic`, `--wait`,
      `--timeout`, `--set`/`--set-string`/`--set-file`/`--values`, `template`, `lint`,
      `get manifest|values|hooks`, `history`, `rollback`, `diff` (plugin), `dependency
      update`, `package`, `push` (OCI registries), `test`. `[CMD]`
2.24.7 Helm **hooks**: `pre-install`, `post-install`, `pre-upgrade`, `post-upgrade`,
      `pre-delete`, `post-delete`, `pre-rollback`, `post-rollback`, `test`, with
      `helm.sh/hook-weight` and `helm.sh/hook-delete-policy`. The correct place for a schema
      migration Job, and the caveat that a failed hook leaves the release in `pending-upgrade`.
      `[CFG]` `[DIAG]`
2.24.8 The Helm failure modes to be able to recover from: a release stuck in
      `pending-upgrade`/`pending-install`, `another operation in progress`, a CRD that Helm will
      not upgrade (the `crds/` directory is install-only), `--force` recreating a resource and
      losing a LoadBalancer IP, and a `helm rollback` that cannot undo a migration. `[DIAG]`
      `[TRAP]`
2.24.9 **Kustomize**: `kustomization.yaml` with `resources`, `bases` (legacy),
      `patches` (strategic-merge and JSON6902), `patchesStrategicMerge`/`patchesJson6902`
      (deprecated names), `configMapGenerator`/`secretGenerator` with
      `generatorOptions` and the **name-hash suffix that makes a config change roll the pods**,
      `images`, `replicas`, `namePrefix`/`nameSuffix`, `namespace`, `commonLabels`/`labels`,
      `commonAnnotations`, `replacements`, `vars` (deprecated), `components`, `transformers`,
      `helmCharts`. `[CFG]`
2.24.10 The **base/overlay** model and why the ConfigMap name-hash behaviour is Kustomize's single
        best feature: it solves §1.25.3 for free. `[PROVE]`
2.24.11 The decision, argued rather than surveyed: **Kustomize** for your own services (no
        templating language, valid YAML at rest, native `kubectl -k`); **Helm** for third-party
        software and for anything you distribute; both together (`helmCharts` in Kustomize, or a
        Helm post-renderer running Kustomize) when you must patch someone else's chart. Then name
        the alternatives — `jsonnet`/Tanka, `cdk8s`, Pulumi, Timoni/CUE, `ytt` — and say when
        typed configuration earns its cost. `[PROVE]`
2.24.12 The QuizStakes packaging layout the bible must ship: a `base/` per service, overlays for
        `dev`/`staging`/`prod`, `components/` for cross-cutting concerns
        (money-path hardening, PSS-restricted context), and the per-environment replica/resource
        deltas taken from Appendix A.6. `[BUILD]` `[YAML]`
2.24.13 The Appendix B.4 constraint again: **configuration is versioned and promoted through
        environments, never edited in place** — so the overlay diff between staging and prod must
        be small, reviewable, and the only difference. `[PROVE]`

*(13 leaves)*

## §2.25 GitOps and delivery

2.25.1 The definition worth defending: the desired state of the cluster lives in Git, an in-cluster
      agent reconciles the cluster toward it, and drift is detected and reported. `kubectl apply`
      from a laptop is not delivery.
2.25.2 **Argo CD**: `Application`, `ApplicationSet`, projects, sync policies
      (`automated` with `prune` and `selfHeal`), **sync waves** and hooks
      (`argocd.argoproj.io/sync-wave`, `PreSync`/`Sync`/`PostSync`/`SyncFail`), health
      assessment, `ignoreDifferences` (the HPA-replica problem from §2.13.18), and the
      app-of-apps pattern. `[CFG]` `[RESEARCH]`
2.25.3 **Flux**: `GitRepository`/`OCIRepository`, `Kustomization`, `HelmRelease`,
      `ImageRepository`/`ImagePolicy`/`ImageUpdateAutomation`, and **Flux 2.8's Helm v4
      server-side-apply support and CEL health checks**. `[RESEARCH]`
2.25.4 The image-update loop: CI builds and pushes a digest → an automation commits the new digest
      to the environment repo → the agent syncs. Why the commit is the audit trail and the
      rollback mechanism. `[PROVE]` `[X-REF 17]`
2.25.5 Repository topology: app repo vs environment repo (and why one repo per environment beats
      branches per environment), the promotion PR, and who is allowed to approve it.
      `[X-REF 17]`
2.25.6 What GitOps makes worse if you are not careful: an incident where the fastest fix is a
      `kubectl` command that `selfHeal` immediately reverts. The answer (a break-glass procedure,
      `argocd app set --sync-policy none`, or a documented "commit the hotfix" path) must be
      written down *before* the incident. `[TRAP]` `[X-REF 20]`
2.25.7 Secrets in a GitOps world: never plaintext in Git, so ESO/CSI/Sealed Secrets/SOPS —
      cross-reference §2.21.
2.25.8 Progressive delivery on top: Argo Rollouts or Flagger driving a canary against
      HTTPRoute weights with metric analysis, and the `AnalysisTemplate` shape. `[RESEARCH]`
2.25.9 Drift detection as an operational signal: what a permanently out-of-sync Application usually
      means (a mutating webhook, a controller writing defaults, or someone's `kubectl edit`).
      `[DIAG]`
2.25.10 The deployment pipeline the bible should specify for QuizStakes end to end: PR → build +
        test + scan + sign → push by digest → promote to staging → smoke test → PR to prod repo →
        approval → sync → `rollout status` gate → automated rollback on failure. `[BUILD]`

*(10 leaves)*

## §2.26 CRDs and operators

2.26.1 `CustomResourceDefinition` anatomy: `group`, `versions[]` (with `served`, `storage`,
      `schema.openAPIV3Schema`, `subresources.status`, `subresources.scale`,
      `additionalPrinterColumns`, `deprecated`), `scope`
      (`Namespaced`/`Cluster`), `names` (`kind`, `plural`, `singular`, `shortNames`,
      `categories`), `conversion` (`None`/`Webhook`), `preserveUnknownFields`. `[SOURCE]`
      `[CFG]`
2.26.2 **Structural schemas and validation**: OpenAPI v3 constraints, `x-kubernetes-validations`
      with **CEL** rules (`rule`, `message`, `messageExpression`, `reason`, `fieldPath`),
      `x-kubernetes-list-type` (`atomic`/`set`/`map`) + `x-kubernetes-list-map-keys` — which is
      what makes server-side-apply merges behave, `x-kubernetes-preserve-unknown-fields`,
      `x-kubernetes-int-or-string`, and defaulting. `[SOURCE]` `[RESEARCH]`
2.26.3 Version conversion webhooks and the storage-version problem; the **Storage Version
      Migration** controller (default-enabled 1.37) as the thing that rewrites existing objects
      after you change the storage version. `[RESEARCH]`
2.26.4 The **operator pattern** defined: a CRD encoding an application's desired state plus a
      controller that knows the domain — the "operational knowledge as code" framing, and the
      **capability levels** (basic install → seamless upgrades → full lifecycle → deep insights →
      autopilot).
2.26.5 The controller-runtime concepts you must be able to name: manager, cache/informer, work
      queue with rate limiting, `Reconcile(ctx, req) (Result, error)`, owner references +
      `Owns()`, predicates, finalizers, `RequeueAfter`, status conditions, and **idempotent
      reconciliation**. `[PROVE]`
2.26.6 Why reconcile must be idempotent and must not assume it sees every event — the level-trigger
      argument from §1.20.3 applied to your own code. `[PROVE]`
2.26.7 Building one in Java: the **Java Operator SDK** and **fabric8 kubernetes-client** —
      `@ControllerConfiguration`, `Reconciler<T>`, `UpdateControl`, `DeleteControl`,
      `EventSourceInitializer`, dependent resources; and the honest note that Go is the ecosystem's
      default and Java is a legitimate choice when your team writes Java. `[BUILD]` `[RESEARCH]`
2.26.8 When an operator is the right answer and when a Helm chart plus a Job is: the test is
      whether there is ongoing *operational* logic (failover, backup, resharding), not just
      installation. `[PROVE]`
2.26.9 Operators you will actually meet: cert-manager, External Secrets, Strimzi, CloudNativePG,
      Prometheus Operator, Argo CD, KEDA, Karpenter, AWS Controllers for Kubernetes (ACK), Crossplane.
2.26.10 The **operational hazards of CRDs**: deleting a CRD deletes every instance;
        finalizers on a CR whose controller is gone wedge deletion; a CRD's conversion webhook
        being down breaks `kubectl get`; and CRDs are cluster-scoped so two teams cannot have
        different versions. `[TRAP]` `[DIAG]`
2.26.11 The QuizStakes CRD worth designing as an exercise: a `PaymentRun` custom resource whose
        controller enforces "exactly one run in flight, resumable, with a recorded checkpoint" —
        which is the scenario's hardest operational requirement expressed as Kubernetes.
        `[BUILD]` `[PROVE]`

*(11 leaves)*

## §2.27 Service mesh, and whether you need one

2.27.1 What a mesh actually provides, itemised: mTLS with workload identity, L7 retries/timeouts/
      circuit breaking, traffic splitting, per-request routing, uniform golden metrics and traces,
      and authorization policy — all without application code.
2.27.2 The sidecar model: an injected Envoy per pod, iptables redirection of all traffic through
      it, and the costs (100–200 MB and ~0.5 CPU per pod × every pod, ~1–3 ms added per hop,
      start-up ordering problems, and an upgrade that touches every pod). `[NUM]`
2.27.3 **Ambient mode** (Istio, GA since 1.24): a per-node **ztunnel** doing L4 mTLS and telemetry
      via HBONE, plus optional per-namespace **waypoint** proxies for L7. Why this changes the cost
      equation — no per-pod sidecar, no injection, no restart to enrol. `[PROVE]` `[RESEARCH]`
2.27.4 The mesh options and their shapes: Istio (sidecar or ambient), **Linkerd** (Rust
      micro-proxy, simplest), **Cilium Service Mesh** (eBPF, no sidecar, per-node Envoy),
      **Consul**, **AWS App Mesh** (deprecated) and **Kuma**. `[RESEARCH]`
2.27.5 **GAMMA** and the Gateway API as the mesh's north-star config surface, replacing
      `VirtualService`/`DestinationRule` with `HTTPRoute` bound to a Service. `[RESEARCH]`
2.27.6 `AuthorizationPolicy` / Linkerd `Server`+`ServerAuthorization` as **L7 identity-based**
      policy — which is what NetworkPolicy cannot express (§2.22.16), and the correct place for
      "only `card-payments` may call the PSP egress gateway" and "only `profile-service` may read
      a PII field". `[PROVE]` `[X-REF 13]`
2.27.7 mTLS everywhere as Appendix B.4's stated requirement, and the two ways to get it: a mesh, or
      application-level TLS with certificates from cert-manager / the new
      **PodCertificateRequest** + **ClusterTrustBundle** APIs (1.37). Compare the operational cost.
      `[RESEARCH]`
2.27.8 Retries and circuit breaking in a mesh vs in the client library (Resilience4j): why doing
      both silently multiplies your retry budget and can amplify an incident. `[TRAP]` `[PROVE]`
      `[X-REF 10]`
2.27.9 The honest decision rule: a mesh is justified when you need uniform mTLS and L7 policy
      across many teams and cannot change every service; it is not justified for 25 services owned
      by one team who can add a library. Say which side QuizStakes falls on and why. `[PROVE]`
2.27.10 Debugging a mesh: `istioctl proxy-config route|cluster|endpoint|listener`,
        `istioctl analyze`, envoy admin `/stats` and `/config_dump`, and the 503 taxonomy
        (`UF`, `UO`, `NR`, `URX`, `upstream_reset_before_response_started`). `[CMD]` `[DIAG]`

*(10 leaves)*

## §2.28 Observability of containers and clusters

2.28.1 The container-level metric sources: **cAdvisor** embedded in the kubelet
      (`/metrics/cadvisor`), `/metrics/resource`, `/metrics/probes`, `/stats/summary`, and what
      each exposes. `[CMD]` `[X-REF 20]`
2.28.2 The metrics that actually matter for a container, with the good/bad values:
      `container_cpu_usage_seconds_total`,
      `container_cpu_cfs_throttled_periods_total` / `..._periods_total`,
      `container_memory_working_set_bytes` (**the one the OOM killer uses**),
      `container_memory_rss`, `container_memory_cache`,
      `container_memory_failcnt`, `container_oom_events_total`,
      `container_fs_usage_bytes`, `container_network_receive_bytes_total`,
      `container_processes`. `[NUM]` `[PROVE]`
2.28.3 The trap that follows: `container_memory_usage_bytes` includes reclaimable page cache and
      will alarm on a healthy pod; **use working set**. Keep this as a `**Trap:**`. `[TRAP]`
2.28.4 **kube-state-metrics** vs metrics-server vs cAdvisor: object state vs live resource usage vs
      container cgroup counters. Three different sources people conflate. `[PROVE]`
2.28.5 The kube-state-metrics series worth alerting on: `kube_pod_container_status_restarts_total`,
      `kube_pod_container_status_terminated_reason{reason="OOMKilled"}`,
      `kube_pod_status_phase{phase="Pending"}`,
      `kube_deployment_status_replicas_unavailable`,
      `kube_horizontalpodautoscaler_status_current_replicas` vs `..._spec_max_replicas`,
      `kube_poddisruptionbudget_status_pod_disruptions_allowed`,
      `kube_node_status_condition`, `kube_persistentvolumeclaim_status_phase`,
      `kube_cronjob_status_last_successful_time`. `[CMD]` `[X-REF 20]`
2.28.6 Control-plane health signals: `/readyz?verbose`, `/livez`, `/healthz`,
      `apiserver_request_duration_seconds`, `apiserver_request_total{code=~"5.."}`,
      `etcd_server_leader_changes_seen_total`, `etcd_disk_wal_fsync_duration_seconds`,
      `etcd_mvcc_db_total_size_in_bytes`, `apiserver_flowcontrol_rejected_requests_total`,
      `workqueue_depth`, `scheduler_pending_pods`,
      `scheduler_e2e_scheduling_duration_seconds`. `[CMD]` `[NUM]`
2.28.7 Container logging mechanics: stdout/stderr → the runtime's CRI log file at
      `/var/log/pods/<ns>_<pod>_<uid>/<container>/<n>.log`, kubelet rotation
      (`containerLogMaxSize` **10Mi**, `containerLogMaxFiles` **5**), the symlink farm in
      `/var/log/containers/`, and the DaemonSet collector (Fluent Bit / Vector / OTel Collector)
      that tails it. `[NUM]` `[SOURCE]` `[X-REF 20]`
2.28.8 Why `kubectl logs` loses your data: rotation, `--previous` only keeping one generation, and
      an evicted pod's logs disappearing with the pod. Hence ship logs off the node. `[TRAP]`
2.28.9 Structured logs plus the Kubernetes metadata that makes them queryable
      (`pod`, `namespace`, `container`, `node`, `image digest`, and the `revision` label), and the
      correlation-ID propagation that ties them to a trace. `[X-REF 20]`
2.28.10 Traces across a pod boundary: the sidecar/ambient proxy's spans vs application spans, the
        OTel Operator's auto-instrumentation injection, and `OTEL_RESOURCE_ATTRIBUTES` populated
        from the Downward API. `[BUILD]` `[X-REF 20]`
2.28.11 The dashboards that answer real questions, specified: "is any pod being throttled",
        "is any pod near its memory limit", "what restarted in the last hour and why",
        "what is Pending and why", "which nodes are over-committed",
        "is the rollout progressing". `[BUILD]`
2.28.12 The alert set worth paging on, and the ones that must not page: OOMKill rate, sustained
        throttling on a money-path service, `Pending` pods older than 5 minutes, a PDB blocking
        for over an hour, `ProgressDeadlineExceeded`, a node `NotReady`, certificate expiry, and
        `kube_cronjob` overdue. `[X-REF 20]`
2.28.13 Cost observability: OpenCost/Kubecost, and the arithmetic that maps requests → node hours →
        money, which is what makes the "requests, not usage, are what you pay for" argument land
        with a manager. `[NUM]` `[X-REF 18]`

*(13 leaves)*

## §2.29 The debugging cookbook

2.29.1 **Rule zero: `kubectl describe pod` first, and read the Events at the bottom before
      anything else.** Then `logs`, then `logs --previous`, then `get events`, then the node.
      Keep the current guide's framing and make it an explicit ordered procedure. `[CMD]`
2.29.2 `[DIAG]` **`ImagePullBackOff` / `ErrImagePull`** — symptom, the event text variants
      (`manifest unknown`, `unauthorized`, `denied`, `no such host`, `toomanyrequests`), causes
      (bad tag, wrong registry, missing/expired pull secret, Hub rate limit, wrong architecture,
      private registry not reachable from the node), the confirming commands, and the fix for
      each.
2.29.3 `[DIAG]` **`CrashLoopBackOff`** — the pod restarts with growing backoff. The procedure:
      `logs --previous` first, then exit code, then `describe` for OOMKilled, then
      `kubectl debug --copy-to` with the command replaced by `sleep infinity` to inspect the
      filesystem. Causes: application start-up failure, missing config/secret, bad `command`,
      failing liveness probe, immediate OOMKill, a dependency unavailable at boot.
2.29.4 `[DIAG]` **`OOMKilled` / exit 137** — distinguish container-cgroup OOM from node OOM from
      JVM heap OOM (§2.8.6), read `lastState.terminated`, `memory.events`, `dmesg`, and
      `container_memory_working_set_bytes` at the moment of death.
2.29.5 `[DIAG]` **`Pending` / `FailedScheduling`** — decode the scheduler message (§2.9.13),
      check `describe node` allocated resources, check taints, check PVC binding mode, check
      quota.
2.29.6 `[DIAG]` **`ContainerCreating` forever** — image pull in progress, volume attach/mount
      failure, CNI IP exhaustion, a CSI node plugin down, a Secret/ConfigMap that does not exist,
      or a mutating webhook timing out.
2.29.7 `[DIAG]` **`CreateContainerConfigError`** — a referenced ConfigMap or Secret key is
      missing. The one-line fix and why it is a distinct state from `CrashLoopBackOff`.
2.29.8 `[DIAG]` **`Evicted`** — read the pod's status message, correlate with the node's
      `MemoryPressure`/`DiskPressure` condition and the eviction thresholds (§2.12.8).
2.29.9 `[DIAG]` **`Terminating` forever** — a finalizer, a stuck volume unmount, an unresponsive
      kubelet, or a `preStop` that never returns. The safe order of investigation and why
      `--force --grace-period=0` is the last resort, not the first.
2.29.10 `[DIAG]` **Node `NotReady`** — kubelet down, container runtime down, disk full, kernel
        panic, network partition; the `describe node` conditions, `journalctl -u kubelet`,
        `crictl ps`, and the `kubectl debug node/…` privileged shell.
2.29.11 `[DIAG]` **"My service is unreachable"** — the ordered checklist: does the pod pass
        readiness → does the EndpointSlice have addresses → does the Service selector match the
        pod labels → is `targetPort` right → does the app bind `0.0.0.0` rather than `127.0.0.1`
        → does DNS resolve → does a NetworkPolicy block it → is kube-proxy healthy →
        `port-forward` directly to the pod to bisect. **This checklist is the single most useful
        artefact in the section.** `[BUILD]` `[PROVE]`
2.29.12 `[DIAG]` **"It works via `port-forward` but not via the Service"** — the selector/label
        mismatch, the named-port mismatch, and `publishNotReadyAddresses`.
2.29.13 `[DIAG]` **Intermittent 502/504 at the ingress** — the deploy-time deregistration race
        (§2.11.2), keep-alive to a dead pod, an idle-timeout mismatch between LB and app, and a
        readiness probe that is too permissive.
2.29.14 `[DIAG]` **p99 latency with no CPU saturation** — CFS throttling. The metric, the
        confirmation, the fix (§2.8.11–13).
2.29.15 `[DIAG]` **Exactly 5.000-second latencies** — the DNS conntrack race (§2.18.9).
2.29.16 `[DIAG]` **"Works on my machine, not in the cluster"** — the ordered suspects: a different
        architecture, a missing env var, a read-only filesystem, a non-root UID, a missing CA
        bundle, a locale/timezone difference, `/tmp` not writable, and a `hostname` the app
        assumes.
2.29.17 `[DIAG]` **Disk full on a node** — image cache, container logs, `emptyDir`, a runaway heap
        dump, or `containerd` content store; `du -sh /var/lib/containerd/*`, `crictl imagefsinfo`,
        and the image-GC thresholds.
2.29.18 `[DIAG]` **The apiserver is slow or 429ing** — a controller in a hot loop, a huge `list`, a
        webhook timing out, or etcd disk latency; `apiserver_request_duration_seconds`, the audit
        log by user agent, and APF (`§1.19.16`).
2.29.19 `[DIAG]` **etcd is unhealthy or the database is full** — the **8 GiB** default quota, the
        `mvcc: database space exceeded` alarm, compaction and defragmentation, and the recovery
        procedure. `[NUM]`
2.29.20 The tools that shortcut all of this: `stern`, `k9s`, `kubectl-debug`, `netshoot`,
        `kubectl-trace`, `kubeshark`, `Robusta`, `popeye`, `kubectl events -w`. `[CMD]`
2.29.21 The habit that prevents most of it: `kubectl diff` before apply, `rollout status` as a
        gate, and **"roll back first, diagnose second"** with a preserved artefact.
        `[X-REF 20]`
2.29.22 The QuizStakes incident write-ups this section must include as worked examples: (a) the
        `funds-ledger` rolling update that dropped in-flight stake reservations because
        `terminationGracePeriodSeconds` was 30 and the pool close took 40; (b) the
        `client-restrictions` CPU limit that turned a 30 ms budget into a 130 ms p99 under
        throttling; (c) the liveness probe on the ledger database that restarted all 8
        `client-restrictions` pods during a 30-second database blip and breached invariant 8;
        (d) the `bank-withdrawal` CronJob that ran twice and double-paid because
        `concurrencyPolicy` was `Allow` and the lock was advisory. `[BUILD]` `[PROVE]`

*(22 leaves)*

## §2.30 Choosing an orchestrator

2.30.1 The full option set with the concepts each demands: bare containers + systemd on VMs,
      Compose on one host, Docker Swarm, Nomad, ECS on EC2, **ECS on Fargate**, EKS, EKS on
      Fargate/Auto Mode, GKE Autopilot, Cloud Run, App Runner, Lambda.
2.30.2 **The ECS vs Kubernetes table**, kept from the current guide and extended: concepts to
      learn, control-plane cost (free vs ~$73/month/cluster), portability, ecosystem, IAM
      integration (task roles vs IRSA/Pod Identity), team size to run well, flexibility, and the
      hiring/transferability factor. `[NUM]`
2.30.3 **The honest positioning**, kept verbatim in substance: if you are all-in on AWS running a
      normal set of stateless services, **ECS with Fargate does the job with a fraction of the
      concepts and operational burden**, and you will ship faster. Kubernetes wins when you need
      portability, many teams needing a shared self-service platform, the operator/CRD ecosystem,
      or you already run it.
2.30.4 **The failure mode worth naming**: adopting Kubernetes for a five-service application and
      spending a year on platform work instead of product.
2.30.5 The counter-argument to take seriously: Kubernetes skills are broadly transferable in a way
      ECS skills are not, which is a legitimate factor in the decision — and the ecosystem
      (ArgoCD, Strimzi, KEDA, cert-manager, external-secrets) is genuinely hard to reproduce.
2.30.6 The QuizStakes decision, made and defended: 25 services, one platform team, an existing
      AWS estate, a regulated money path with hard latency budgets, and a mixture of long-running
      containers, file-triggered workers and a leader-elected batch run. State the choice, the
      reasoning, and the conditions under which you would change it. `[PROVE]`
2.30.7 What is *not* a good reason to choose Kubernetes: it is on the CV, the conference talk was
      persuasive, or "we might need multi-cloud one day".
2.30.8 The migration question if you already have ECS: what transfers directly (images, health
      checks, env config, IAM patterns), what does not (task definitions → Deployments, ALB target
      groups → Gateway, Service Discovery → CoreDNS), and the strangler order.
2.30.9 Serverless containers as the third option: Fargate/Cloud Run per-request pricing vs
      always-warm instances, and why `funds-ledger` explicitly rejects function compute in the
      scenario (cold connection pool, lost index locality, pause sensitivity). `[PROVE]`
      `[X-REF 18]`

*(9 leaves)*

## §2.31 Testing against containers

2.31.1 **Testcontainers** mechanics: it talks to the Docker API (`/var/run/docker.sock` or
      `DOCKER_HOST`), starts the container, waits on a strategy, exposes a random host port, and
      reaps via **Ryuk**. `[X-REF 16]`
2.31.2 Wait strategies as the thing that makes tests non-flaky: `Wait.forListeningPort`,
      `forLogMessage`, `forHttp`, `forHealthcheck`, `forSuccessfulCommand`, and why a fixed
      `Thread.sleep` is the classic flake. `[X-REF 16]`
2.31.3 `@Container` static vs instance, reuse (`testcontainers.reuse.enable`), Docker-in-Docker vs
      socket mounting in CI, and Testcontainers Cloud. The security note: giving a CI job the
      Docker socket is a root-equivalent grant (§1.10.13). `[TRAP]`
2.31.4 Spring Boot 3.1+'s `@ServiceConnection` and `ConnectionDetails` — the mechanism that removes
      the `@DynamicPropertySource` boilerplate; and `spring-boot-testcontainers` +
      `TestcontainersConfiguration` for local development against real dependencies.
      `[BUILD]` `[X-REF 16]`
2.31.5 What to test with containers and what not to: the ledger's SQL against real Postgres yes;
      Redis eviction behaviour yes; the whole stack in one test no.
2.31.6 Testing the *Kubernetes* parts, which nobody does and everybody should: `kubeconform`/
      `kubeval` schema validation, `helm lint`/`helm template | kubeconform`, `conftest`/OPA
      unit tests on manifests, `kube-score`, `kubectl apply --dry-run=server` in CI against a real
      cluster, and a `kind`-based end-to-end that asserts probes, rollout, and graceful shutdown.
      `[BUILD]` `[X-REF 16]`
2.31.7 The graceful-shutdown test from §2.11.13 as the canonical example of a test that catches a
      whole class of production defect nothing else catches.
2.31.8 Chaos as a test: `kubectl delete pod` in a loop during a load test, Chaos Mesh /
      LitmusChaos, and the four experiments worth running on QuizStakes (kill a `funds-ledger`
      pod mid-reservation; partition `client-restrictions` from its database; fill a node's disk;
      throttle a pod's CPU to 10%). `[BUILD]` `[PROVE]`

*(8 leaves)*

---

# PART 3 — UNDER THE HOOD

## §3.1 Namespace internals

3.1.1 `clone(2)`/`clone3(2)` with the `CLONE_NEW*` flags, `unshare(2)`, and `setns(2)` — the three
      syscalls that create, detach from, and join a namespace. `[SOURCE]`
3.1.2 `/proc/<pid>/ns/{mnt,net,pid,ipc,uts,user,cgroup,time}` as bind-mountable handles, and the
      inode number as the namespace's identity — `readlink /proc/self/ns/net` printing
      `net:[4026531840]` is how you prove two processes share a namespace. `[CMD]` `[PROVE]`
3.1.3 The mount-namespace mechanics runc performs, in order: `unshare(CLONE_NEWNS)`, mark the old
      root `MS_PRIVATE` (so nothing propagates back to the host), mount the new rootfs,
      `pivot_root(new, put_old)`, `chdir("/")`, `umount2(put_old, MNT_DETACH)`. Explain why every
      step is necessary. `[SOURCE]` `[PROVE]`
3.1.4 Why `pivot_root` and not `chroot`: `chroot` changes only the process's root directory, so a
      process holding a file descriptor to a directory outside can `fchdir` out and escape.
      `pivot_root` changes the mount namespace's root. `[PROVE]`
3.1.5 PID namespace nesting: PID 1 inside is a different number outside, `/proc/<hostpid>/status`'s
      `NSpid` line shows both, and killing the namespace's PID 1 kills every process in it.
      `[SOURCE]` `[PROVE]`
3.1.6 Why `/proc` must be remounted inside the PID namespace, and what a container sees when it is
      not (`ps` showing host processes) — the `--mount-proc` in `unshare`. `[PROVE]`
3.1.7 Network namespace internals: `veth` pairs, one end in the container namespace and one on the
      host bridge; `ip link set <name> netns <pid>`; and that a namespace with no interface still
      has a `lo`. `[CMD]`
3.1.8 User namespace ID mapping: `/proc/<pid>/uid_map` and `gid_map` line format
      `<inside-id> <outside-id> <length>`, `/etc/subuid` and `/etc/subgid`, `setgroups` denial, and
      capability semantics inside a user namespace (you are root *in that namespace only*).
      `[SOURCE]` `[NUM]`
3.1.9 How Kubernetes' `hostUsers: false` allocates ranges per pod, and the storage-driver
      requirement (`idmap` mounts or a shifting filesystem) that made it hard. `[RESEARCH]`
3.1.10 Time namespace offsets (`/proc/<pid>/timens_offsets`) and why `CLOCK_REALTIME` is
       deliberately not namespaced.
3.1.11 The experiment the bible must include: build a container by hand with `unshare`,
       `mount`, `pivot_root` and `cgcreate`, then show the same thing via `runc`'s
       `config.json`. Forward to §4.1. `[BUILD]`

*(11 leaves)*

## §3.2 cgroup v2 internals and the arithmetic

3.2.1 The unified hierarchy on disk: `/sys/fs/cgroup` with `cgroup.controllers`,
      `cgroup.subtree_control`, `cgroup.type`, `cgroup.procs`, `cgroup.threads`,
      `cgroup.events`, `cgroup.freeze`, `cgroup.kill`, `cgroup.max.depth`,
      `cgroup.max.descendants`. `[SOURCE]`
3.2.2 The **no-internal-process constraint**: a cgroup with children may not contain processes
      (except the root), which is why the container platform's tree has the shape it does.
      `[PROVE]` `[SOURCE]`
3.2.3 Delegation: `cgroup.subtree_control` must enable a controller in the parent before a child
      can use it, and `systemd`'s `Delegate=yes` is what lets a container runtime manage a subtree.
      `[PROVE]`
3.2.4 `cpu.weight` semantics: proportional share among siblings under contention only,
      1–10000, default 100. The conversion Kubernetes uses from `requests.cpu`
      (`shares = millicores × 1024 / 1000`, then the v1-shares→v2-weight mapping
      `weight = (1 + ((shares - 2) * 9999) / 262142)`). Work a real example. `[NUM]` `[PROVE]`
      `[SOURCE]`
3.2.5 `cpu.max` semantics: `"$MAX $PERIOD"`, default `"max 100000"`, Kubernetes writes
      `quota = millicores × period / 1000` with period **100000 µs**. Work `500m` and `2` to their
      exact file contents. `[NUM]` `[PROVE]`
3.2.6 `cpu.stat`: `usage_usec`, `user_usec`, `system_usec`, `nr_periods`, `nr_throttled`,
      `throttled_usec`, `nr_bursts`, `burst_usec` — read it directly in a pod to prove throttling.
      `[CMD]` `[SOURCE]`
3.2.7 `cpu.max.burst` and the CFS burst feature: allowing accumulated unused quota to be spent,
      which materially helps bursty JVM workloads. State availability and the risk. `[RESEARCH]`
3.2.8 `cpuset.cpus` / `cpuset.mems` / `cpuset.cpus.effective`, and Kubernetes' **CPU Manager**
      policies `none` and `static` — the latter giving integral-CPU Guaranteed pods exclusive
      cores, which removes both throttling and scheduler migration cost. When that matters for
      `client-restrictions`. `[CFG]` `[PROVE]`
3.2.9 **Topology Manager** and **Memory Manager** policies (`none`, `best-effort`,
      `restricted`, `single-numa-node`) and NUMA locality as a real latency factor at 12 GB heap.
      `[CFG]` `[RESEARCH]`
3.2.10 `io.max` (`riops`/`wiops`/`rbps`/`wbps`) and `io.weight`; why Kubernetes does not expose
       block-I/O limits and what that means for a noisy-neighbour disk problem. `[TRAP]`
3.2.11 `pids.max` / `pids.current` and the kubelet's `--pod-max-pids`; the thread-per-request JVM
       that hits it and reports `unable to create native thread` with plenty of heap free.
       `[DIAG]` `[NUM]`
3.2.12 PSI files in depth: `some`/`full`, `avg10`/`avg60`/`avg300`/`total`, and how to read
       `memory.pressure` to distinguish "slow because of reclaim" from "slow because of CPU".
       **PSI metrics GA in 1.36.** `[SOURCE]` `[RESEARCH]`
3.2.13 The full node cgroup tree walk for a real Guaranteed pod: from `/sys/fs/cgroup` down to
       `kubepods.slice/kubepods-pod<uid>.slice/cri-containerd-<id>.scope`, reading `cpu.max`,
       `memory.max` and `cpu.stat` at each level and showing which level enforces what.
       `[SOURCE]` `[BUILD]` `[PROVE]`
3.2.14 `--kube-reserved`, `--system-reserved`, `--enforce-node-allocatable`
       (`pods`, `kube-reserved`, `system-reserved`) and the reserved-cgroup names — and the
       allocatable arithmetic worked on a `m5.xlarge`. `[NUM]` `[PROVE]`
3.2.15 `systemd` vs `cgroupfs` driver at the file level: `kubepods.slice` naming and the escaped
       `-` characters vs `/kubepods/burstable/pod<uid>`. Showing both is the fastest way to
       diagnose a driver mismatch. `[SOURCE]` `[DIAG]`

*(15 leaves)*

## §3.3 CFS bandwidth control, proved

3.3.1 The mechanism: the CFS bandwidth controller gives a cgroup `quota` microseconds of runtime
      per `period`; the runtime is distributed to per-CPU local pools in `slice`-sized chunks
      (default `sched_cfs_bandwidth_slice_us` = **5000 µs**); when the global pool is exhausted
      every runnable task in the cgroup is throttled until the period rolls over. `[SOURCE]`
      `[NUM]`
3.3.2 **[PROVE]** Why an 8-thread process with a `500m` limit can be frozen for ~95 ms of every
      100 ms period: 8 threads × 5 ms slices consumes the 50 ms quota in ~6 ms of wall time, then
      all 8 are throttled. Do the arithmetic explicitly. `[NUM]`
3.3.3 **[PROVE]** Why utilisation graphs look *low* during throttling: the container is not
      running, so it accrues no CPU seconds. Utilisation and throttling are near-orthogonal
      signals, which is why you must chart both. `[TRAP]`
3.3.4 The per-CPU slice-hoarding bug: unused runtime stranded in per-CPU pools caused throttling
      below the nominal limit; the kernel fix (5.4-era, expiring unused local slices) and why
      Kubernetes issues #67577 and #51135 are still cited. State what is fixed and what is
      inherent. `[RESEARCH]` `[VERSION-TRAP]`
3.3.5 The knobs and their availability: `cpu.cfs_period_us` (shortening the period reduces the
      stall length but raises overhead), `cpu.max.burst`, and `--cpu-cfs-quota=false` on the
      kubelet (disable enforcement entirely). `[CFG]`
3.3.6 The measurement procedure: `nr_throttled / nr_periods` over a window, and
      `throttled_usec / (nr_periods × period)` as the fraction of wall time frozen. Define the
      threshold at which you act. `[NUM]` `[BUILD]`
3.3.7 **[PROVE]** Why removing the CPU limit is usually safe and sometimes not: with requests set,
      `cpu.weight` still gives you your fair share under contention; the risk is that your p99
      now depends on your neighbours. Work both cases.
3.3.8 The interaction with GC: a stop-the-world pause that begins just before a throttle boundary
      is extended by the throttle, so throttling inflates GC pause *observations* as well as
      request latency. `[PROVE]` `[X-REF 06]`
3.3.9 The interaction with probes: a throttled pod fails a 1-second `timeoutSeconds` liveness probe
      and gets restarted — throttling causing restarts causing more load. `[PROVE]` `[TRAP]`
3.3.10 The published evidence to cite rather than assert: the Omio write-up, the CoreOS bug report
       showing containers requesting 6 cores throttled to 3 with ~50% throughput loss, and the
       kubernetes/kubernetes issues. Attribute, do not present as measurement. `[RESEARCH]`

*(10 leaves)*

## §3.4 The memory cgroup and the OOM killer

3.4.1 What `memory.current` counts: anonymous pages, page cache, kernel memory (slab, socket
      buffers), and `tmpfs` — which is why a container doing heavy file I/O appears to grow
      without leaking. `[PROVE]`
3.4.2 **Working set** vs RSS vs usage: `working_set = memory.current − inactive_file`, and the
      kubelet reports working set. This is the number the eviction logic and the OOM decision are
      about. `[PROVE]` `[NUM]` `[TRAP]`
3.4.3 `memory.max` breach path: the kernel attempts direct reclaim; if it cannot free enough it
      invokes the **cgroup OOM killer**, which selects a victim *within the cgroup* using
      `oom_score` adjusted by `oom_score_adj`. `[SOURCE]` `[PROVE]`
3.4.4 Why the JVM is almost always the victim in a single-process container (it is the only
      process, and the biggest), and why in a multi-container pod the wrong container can die.
      `[PROVE]`
3.4.5 `memory.high` as the throttling knob: exceeding it puts the allocating task under reclaim
      pressure and slows it rather than killing it — which is what **MemoryQoS**
      (`memory.high` set from the request, alpha/beta) uses, and what "tiered memory protection"
      in 1.36 extends. `[RESEARCH]`
3.4.6 `memory.min` / `memory.low` as reclaim protection, and where they matter (a cache-heavy
      sidecar starving the app).
3.4.7 `memory.events` (`low`, `high`, `max`, `oom`, `oom_kill`) and `memory.oom.group` — the
      counter that proves an OOM happened even after the pod restarted. `[CMD]` `[SOURCE]`
3.4.8 `memory.stat` fields worth reading: `anon`, `file`, `kernel_stack`, `slab`, `sock`,
      `shmem`, `file_mapped`, `pgfault`, `pgmajfault`, `workingset_refault`. `[SOURCE]`
3.4.9 Swap: `memory.swap.max`, why Kubernetes historically required swap **off** entirely, and the
      current swap support (`NodeSwap`, `swapBehavior: NoSwap|LimitedSwap`) plus why swap is fatal
      for a latency-sensitive JVM. `[CFG]` `[RESEARCH]` `[X-REF 11]`
3.4.10 Node-level OOM vs cgroup OOM: the global killer scores across the whole machine and can pick
       a pod that is well within its limit — which is why the kubelet's eviction thresholds exist
       to act *before* the kernel does. `[PROVE]`
3.4.11 The evidence trail after an OOMKill, in order: `kubectl get pod -o jsonpath` for
       `lastState.terminated.{reason,exitCode,finishedAt}`, the pod's `OOMKilling` event,
       `dmesg -T | grep -i "killed process"`, `memory.events`'s `oom_kill` counter, and the
       working-set series at the death timestamp. `[CMD]` `[DIAG]` `[BUILD]`
3.4.12 Transparent Huge Pages and `khugepaged` as a memory-footprint surprise for the JVM, and the
       `madvise` setting. `[X-REF 11]` `[X-REF 06]`

*(12 leaves)*

## §3.5 OverlayFS internals

3.5.1 The mount call itself:
      `mount -t overlay overlay -o lowerdir=L1:L2:L3,upperdir=U,workdir=W /merged` — with the
      lowerdir order being **highest layer first**, and why `workdir` must be on the same
      filesystem as `upperdir`. `[SOURCE]` `[CMD]`
3.5.2 The on-disk layout with the classic graph driver: `/var/lib/docker/overlay2/<id>/` containing
      `diff/`, `link`, `lower`, `merged/`, `work/`, plus `/var/lib/docker/overlay2/l/` holding the
      short symlinks that exist purely to stay under the mount-option page limit. `[SOURCE]`
      `[NUM]`
3.5.3 The equivalent under containerd's snapshotter: `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/<n>/`
      — and the mapping from snapshot IDs to layer digests via the content store. `[RESEARCH]`
3.5.4 Lookup semantics: a path is resolved top-down through the lowerdirs; the first hit wins; a
      whiteout stops the search. Cost is O(layers) per miss. `[PROVE]`
3.5.5 **copy_up** in detail: triggered by any write, `chmod`, `chown`, `utimes`, or opening
      `O_WRONLY`/`O_RDWR` on a lower file; copies data plus xattrs; is **whole-file**. The
      consequence for a 900 MB file and for a database file inside the writable layer. `[PROVE]`
      `[NUM]`
3.5.6 Whiteouts are character devices with device number 0/0 named after the deleted file; opaque
      directories carry the `trusted.overlay.opaque="y"` xattr. Show both with `ls -l` and
      `getfattr`. `[SOURCE]` `[CMD]`
3.5.7 The metacopy and redirect_dir features and what they optimise.
3.5.8 **POSIX deviations** you must know: two descriptors to the same path opened before and after
      copy_up refer to different files; `rename(2)` across layers returns `EXDEV`, so applications
      must fall back to copy-and-unlink; and `st_dev`/`st_ino` are not stable across copy_up.
      These break real software. `[SOURCE]` `[TRAP]` `[PROVE]`
3.5.9 Page-cache sharing across containers for lower-layer files, and why the writable layer does
      not share. `[PROVE]`
3.5.10 Inode consumption and the `overlay2` advantage over the older drivers; the XFS `ftype=1` /
       `d_type=true` requirement and the kernel version floor. `[NUM]` `[SOURCE]`
3.5.11 The **128-lower-layer limit** and the practical advice to keep layer counts modest.
       `[NUM]` `[RESEARCH]`
3.5.12 Why write-heavy workloads must use a volume: the storage driver is bypassed entirely, so
       you get the host filesystem's performance and no copy_up. `[PROVE]`
3.5.13 The alternatives and their trade-offs: `fuse-overlayfs` (rootless, slower),
       `btrfs`/`zfs` snapshotters (block-level CoW, no copy_up penalty, different operational
       burden), `devmapper` (removed), `vfs` (full copy per layer — the "why is my disk full"
       driver), and the lazy-pull snapshotters (`stargz`, `nydus`, `soci`).

*(13 leaves)*

## §3.6 Image layers, digests, and content addressing

3.6.1 The digest computation, end to end: layer tar → gzip → `sha256` of the **compressed** bytes
      = the layer descriptor digest; `sha256` of the **uncompressed** tar = the `diff_id` in the
      config; `sha256` of the config JSON = the **image ID**; `sha256` of the manifest JSON = the
      **manifest digest** used in `@sha256:` references. Four hashes, four purposes. `[PROVE]`
      `[NUM]` `[SOURCE]`
3.6.2 Why the chain is tamper-evident: the manifest names the config and layer digests, so
      changing any byte anywhere changes a digest that something above it references. Contrast
      with a tag, which names nothing. `[PROVE]`
3.6.3 `chainID` vs `diff_id`: the snapshotter identifies a *stack* of layers, computed as
      `sha256(parentChainID + " " + diffID)`, which is why the same layer applied on different
      parents is a different snapshot. `[PROVE]` `[SOURCE]`
3.6.4 Why layer digests differ between two builds of identical content: gzip level and
      implementation, tar entry ordering, mtimes, uid/gid, and xattrs. The reproducibility
      levers from §1.8.16 target exactly these. `[PROVE]`
3.6.5 Cross-repository blob mounts (`POST /v2/<name>/blobs/uploads/?mount=<digest>&from=<repo>`)
      and why pushing a retagged image is nearly free. `[SOURCE]`
3.6.6 Reading it all by hand: `crane manifest`, `crane config`, `crane blob`,
      `skopeo inspect --raw`, `docker save | tar tvf`, and `jq` to walk the descriptors. Then do
      it for a real Temurin image and read the bytes. `[CMD]` `[BUILD]`
3.6.7 The `zstd` layer media type, its compression/decompression trade-off vs gzip, and the
      registry/runtime support you must check before using it. `[RESEARCH]`
3.6.8 How the referrers relationship is stored when the registry does not implement the Referrers
      API: the tag-schema fallback (`sha256-<digest>.sig`) and why `cosign` grew both.
      `[RESEARCH]`

*(8 leaves)*

## §3.7 The registry protocol

3.7.1 The distribution-spec endpoints: `GET /v2/`,
      `GET|HEAD /v2/<name>/manifests/<reference>`, `PUT /v2/<name>/manifests/<reference>`,
      `GET|HEAD /v2/<name>/blobs/<digest>`, `POST /v2/<name>/blobs/uploads/`,
      `PATCH|PUT <location>`, `DELETE`, `GET /v2/<name>/tags/list`,
      `GET /v2/_catalog`, `GET /v2/<name>/referrers/<digest>`. `[SOURCE]`
3.7.2 Content negotiation: the `Accept` header listing manifest media types, and how a client that
      does not send the index media type gets a single-platform manifest — the mechanism behind
      "the same tag pulled a different architecture". `[PROVE]` `[TRAP]`
3.7.3 The auth handshake: an unauthenticated request gets `401` with
      `WWW-Authenticate: Bearer realm=…,service=…,scope="repository:name:pull"`, the client
      exchanges credentials at the realm for a token, and retries. Show the actual `curl`
      sequence against Docker Hub. `[CMD]` `[SOURCE]`
3.7.4 Push mechanics: chunked or monolithic blob upload, the `Docker-Upload-UUID` session, digest
      verification on `PUT`, and the manifest written last so a partially-pushed image is never
      referenceable. `[PROVE]`
3.7.5 Thin manifests, cross-repo mounts, and why pulls are usually parallel per layer — plus
      containerd 2.1's **parallel HTTP range requests within a single layer**. `[RESEARCH]`
3.7.6 Rate limiting and its symptoms: `429 toomanyrequests`, the `Docker-RateLimit-Source`
      header, and the pull-through cache as the structural fix. `[DIAG]`
3.7.7 Garbage collection in a registry: reference counting from manifests to blobs, the two-phase
      mark-and-sweep, and why deleting a tag frees nothing until GC runs. `[PROVE]`
3.7.8 Registry-side digest immutability vs tag mutability, and ECR's tag-immutability setting as
      the enforcement point. `[X-REF 18]`

*(8 leaves)*

## §3.8 containerd architecture

3.8.1 The plugin model: content store, snapshotter, metadata (bbolt at
      `/var/lib/containerd/io.containerd.metadata.v1.bolt/meta.db`), differ, image store,
      runtime (`io.containerd.runc.v2`), CRI, transfer service, NRI, CDI, and the gRPC services
      over `/run/containerd/containerd.sock`. `[SOURCE]`
3.8.2 containerd **namespaces** (`default`, `k8s.io`, `moby`) as a multi-tenancy boundary inside
      the daemon, and why `ctr -n k8s.io` is required to see Kubernetes' containers. `[CMD]`
      `[TRAP]`
3.8.3 The pull path: resolver → fetcher → content store (blobs by digest) → unpack via the differ
      into snapshots → image record in metadata. Then the run path: snapshot → view/active
      snapshot → OCI runtime spec generated → task created via the shim. `[PROVE]`
3.8.4 The **shim** (`containerd-shim-runc-v2`) API: `Create`, `Start`, `Delete`, `Wait`, `Kill`,
      `Exec`, `ResizePty`, `Stats`, and the shim's ownership of the container's stdio and exit
      status. One shim per pod sandbox with the v2 API. `[SOURCE]`
3.8.5 What survives a containerd restart and why: the shim keeps running, reconnects, and reports
      state — so a containerd upgrade does not restart your pods. Contrast with dockershim-era
      behaviour. `[PROVE]`
3.8.6 The `config.toml` surface a node operator actually touches: `SystemdCgroup`,
      `sandbox_image`, `registry.mirrors`/`hosts.toml`, `snapshotter`,
      `discard_unpacked_layers`, `max_concurrent_downloads`, `device_ownership_from_security_context`,
      and `enable_unprivileged_ports`. `[CFG]` `[RESEARCH]`
3.8.7 containerd 2.x changes worth knowing: the CRI plugin as the only supported path,
      **NRI and CDI enabled by default in 2.1**, the transfer service for pulls,
      OCI image volumes, container restore through CRI, and multiple CNI bin dirs.
      `[VERSION-TRAP]` `[RESEARCH]`
3.8.8 CRI-O as the alternative: OCI-only scope, `crio.conf`, and why some distributions prefer it.
3.8.9 The debugging surface: `ctr`, `crictl`, `containerd` logs via `journalctl -u containerd`,
      and `nerdctl` for a Docker-like experience on a Kubernetes node. `[CMD]`

*(9 leaves)*

## §3.9 runc: from a spec file to a process

3.9.1 The bundle: a directory containing `config.json` (runtime-spec) and `rootfs/`. Everything
      about the container is in that one JSON file. `[SOURCE]`
3.9.2 `config.json` structure, walked field by field: `ociVersion`, `process`
      (`terminal`, `user`, `args`, `env`, `cwd`, `capabilities` with all five sets,
      `rlimits`, `noNewPrivileges`, `apparmorProfile`, `oomScoreAdj`, `scheduler`),
      `root` (`path`, `readonly`), `hostname`, `mounts[]`,
      `linux` (`namespaces[]`, `resources` with `devices`/`memory`/`cpu`/`pids`/`blockIO`/
      `hugepageLimits`, `cgroupsPath`, `uidMappings`/`gidMappings`, `maskedPaths`,
      `readonlyPaths`, `seccomp`, `sysctl`, `rootfsPropagation`, `personality`,
      `timeOffsets`), and `hooks` (`prestart` deprecated, `createRuntime`,
      `createContainer`, `startContainer`, `poststart`, `poststop`). `[SOURCE]`
3.9.3 The lifecycle verbs and the state machine: `runc create` (namespaces, cgroups, rootfs, all
      set up, process not started — state `created`) → `runc start` → `running` → `stopped`,
      plus `runc run` as create+start, `runc exec`, `runc kill`, `runc delete`, `runc state`,
      `runc ps`, `runc events`, `runc checkpoint`/`restore` (CRIU). `[SOURCE]` `[CMD]`
3.9.4 The two-process dance: `runc` forks `runc init`, which does the namespace setup and then
      `execve`s the user's binary — so the container's PID 1 *is* your process, with no runc left
      behind. `[PROVE]`
3.9.5 The exact ordering `runc init` performs: unshare namespaces → set up cgroups → mount the
      rootfs and the `mounts[]` list → apply masked and readonly paths → `pivot_root` →
      set hostname → set rlimits → apply seccomp and LSM labels → drop capabilities →
      `setuid`/`setgid` → `no_new_privs` → `execve`. Why seccomp must be applied *after* the
      mounts and *before* the exec. `[PROVE]` `[SOURCE]`
3.9.6 CVE-2019-5736 as the reason the ordering and the `/proc/self/exe` handling matter: the
      original attack rewrote the host's runc binary from inside a container via
      `/proc/self/exe`. Explain the mechanism and the fix (a memfd copy of the binary). `[PROVE]`
      `[RESEARCH]`
3.9.7 CVE-2024-21626 ("Leaky Vessels"): an inherited file descriptor to a host directory left the
      container's cwd outside the rootfs. Explain what it teaches about descriptor hygiene.
      `[RESEARCH]`
3.9.8 `runc 1.4`'s behaviour change: `pids.limit = 0` now means an actual limit of zero rather
      than "unlimited", per updated OCI guidance — an example of a spec clarification producing a
      breaking behaviour change. `[VERSION-TRAP]` `[RESEARCH]`
3.9.9 OCI runtime-spec versions: 1.1 (July 2023), 1.2 (Feb 2024), **1.3 (Nov 2025)** — and how to
      say which features are conditional on which version. `[RESEARCH]`
3.9.10 `crun`, `youki`, `runsc` and `kata-runtime` against the same `config.json`: the point of a
       spec is that the bundle is portable. `[PROVE]`
3.9.11 Reading a real `config.json` generated for a QuizStakes pod and mapping every Kubernetes
       field that produced each entry — the exercise that connects §1.21 to the kernel.
       `[BUILD]` `[SOURCE]`

*(11 leaves)*

## §3.10 CRI in detail

3.10.1 The two gRPC services and the shape of the API: `RuntimeService` and `ImageService` over a
      Unix socket, with the kubelet as the only client. `[SOURCE]`
3.10.2 `RuntimeService` methods, named: `Version`, `RunPodSandbox`, `StopPodSandbox`,
      `RemovePodSandbox`, `PodSandboxStatus`, `ListPodSandbox`, `CreateContainer`,
      `StartContainer`, `StopContainer`, `RemoveContainer`, `ListContainers`,
      `ContainerStatus`, `UpdateContainerResources`, `ReopenContainerLog`, `ExecSync`,
      `Exec`, `Attach`, `PortForward`, `ContainerStats`, `ListContainerStats`,
      `PodSandboxStats`, `UpdateRuntimeConfig`, `Status`, `CheckpointContainer`,
      `GetContainerEvents`, `ListMetricDescriptors`, `ListPodSandboxMetrics`,
      `RuntimeConfig`. `[SOURCE]`
3.10.3 `ImageService`: `ListImages`, `ImageStatus`, `PullImage`, `RemoveImage`, `ImageFsInfo`.
      `[SOURCE]`
3.10.4 The **pod sandbox** concept: `RunPodSandbox` creates the network namespace (calling CNI) and
      the pause container *before* any app container, which is why a pod has an IP before its
      containers start and why `PodReadyToStartContainers` exists as a condition. `[PROVE]`
3.10.5 `UpdateContainerResources` as the CRI call behind **in-place resize** — and why memory
      decrease needs a restart while CPU does not. `[PROVE]` `[RESEARCH]`
3.10.6 `Exec` vs `ExecSync` vs `Attach`, and the streaming server the kubelet runs to proxy
      `kubectl exec`/`port-forward` — which is why exec works even though the apiserver cannot
      reach the container directly. `[PROVE]`
3.10.7 `GetContainerEvents` (the evented pod-lifecycle path) vs the older 1-second **PLEG relist**,
      and the infamous `PLEG is not healthy` node condition — its cause (a slow runtime or too
      many containers) and what the evented path fixed. `[DIAG]` `[RESEARCH]`
3.10.8 CRI logging format: the kubelet expects
      `<RFC3339Nano> <stdout|stderr> <F|P> <message>` in the container log file, and `P` marks a
      partial line — which is why a 20 KB log line arrives as fragments and why some collectors
      reassemble and some do not. `[SOURCE]` `[NUM]` `[TRAP]`
3.10.9 `crictl` mapped to CRI calls, so you can see the API by using the CLI: `crictl pods`,
      `crictl ps -a`, `crictl inspectp`, `crictl logs`, `crictl stats`, `crictl imagefsinfo`.
      `[CMD]`
3.10.10 What removing dockershim actually removed and what it did not: the kubelet's in-tree Docker
        adapter, not the ability to run Docker-built images. `[VERSION-TRAP]`

*(10 leaves)*

## §3.11 The API server request pipeline

3.11.1 The ordered stages of a write request: TLS termination → **authentication** (cert, token,
      OIDC, webhook) → **audit** annotation begins → **authorization** (RBAC / Node / ABAC /
      webhook, in `--authorization-mode` order, first ALLOW wins, no DENY) → **mutating admission
      webhooks** (and `MutatingAdmissionPolicy`) → **object schema validation and defaulting** →
      **validating admission** (`ValidatingAdmissionPolicy` then validating webhooks) → **quota
      admission** → serialization → **etcd write** → response → **watch fan-out**. `[SOURCE]`
      `[PROVE]`
3.11.2 The built-in admission plugins worth naming and what each does:
      `NamespaceLifecycle`, `LimitRanger`, `ServiceAccount`, `DefaultStorageClass`,
      `DefaultTolerationSeconds`, `ResourceQuota`, `PodSecurity`, `Priority`,
      `MutatingAdmissionWebhook`, `ValidatingAdmissionWebhook`, `RuntimeClass`,
      `PodTopologySpread`, `TaintNodesByCondition`, `CertificateApproval`,
      `StorageObjectInUseProtection`, `NodeRestriction`. `[SOURCE]`
3.11.3 The **`NodeRestriction`** plugin and the `Node` authorizer as the reason a compromised
      kubelet cannot read every Secret in the cluster. `[PROVE]` `[X-REF 13]`
3.11.4 **Declarative validation** (GA 1.36): validation rules expressed on the types themselves
      rather than in hand-written Go — what changes for error messages and for CRD parity.
      `[RESEARCH]`
3.11.5 The **watch cache**: the apiserver keeps a per-resource ring buffer so most watches and
      `list`s are served from memory, `BOOKMARK` events advance a client's resourceVersion
      without data, and `410 Gone` forces a relist. Explain the "too old resource version" error
      properly. `[PROVE]` `[SOURCE]`
3.11.6 Consistent reads: `resourceVersion=0` (any cached version — fast, possibly stale),
      unset (quorum read), and `resourceVersion=<n>` (at least that version). Which one
      `kubectl get` uses and why a controller must care. `[PROVE]` `[TRAP]`
3.11.7 The list-cost problem: `list` of a large resource deserialises everything into memory, and
      one badly written controller listing all pods every second can destabilise the apiserver.
      **APF** (§1.19.16), pagination, and the 1.37 **etcd RangeStream** work are the three
      mitigations. `[PROVE]` `[RESEARCH]`
3.11.8 **Server-side apply** internals: `managedFields` entries per manager with the field set,
      `apiVersion`, `operation` and `time`; conflict detection when two managers own a field; and
      how `--force-conflicts` transfers ownership. Then show what a Helm 3 → Helm 4 transition
      does to `managedFields`. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.11.9 The audit pipeline: `Policy` with `None`/`Metadata`/`Request`/`RequestResponse` levels,
      stages, and what a useful policy records for a regulated estate (every `secrets` access,
      every `exec`, every `delete`). `[CFG]` `[X-REF 13]`
3.11.10 Aggregated API servers (`APIService`) and the **mixed version proxy** (beta 1.36) — how
        `metrics.k8s.io` is served by metrics-server through the aggregation layer, and the
        `Unable to connect to the server: service unavailable` failure that follows when it is
        down. `[DIAG]`
3.11.11 The apiserver's own health surface: `/livez`, `/readyz?verbose`, `/healthz`, and the
        individual checks (`etcd`, `poststarthook/...`, `informer-sync`) — reading which one is
        failing is how you diagnose a control plane. `[CMD]` `[DIAG]`
3.11.12 Encryption at rest at the pipeline level: where in the write path the KMS provider is
        invoked, DEK caching, and the performance cost. `[PROVE]`

*(12 leaves)*

## §3.12 etcd

3.12.1 What it is: a strongly consistent, replicated key-value store using **Raft**, with a
      **MVCC** key space and a watch primitive. Kubernetes uses exactly those three properties.
3.12.2 Raft in the depth required: leader election with randomised election timeouts, log
      replication, commit on majority, and the **quorum `(n/2)+1`** rule — so 3 nodes tolerate 1
      failure, 5 tolerate 2, and **4 tolerate the same 1 as 3 while being slower**. `[PROVE]`
      `[NUM]` `[X-REF 22]`
3.12.3 The key layout: `/registry/<resource>/<namespace>/<name>`, values as protobuf (or JSON),
      and the practical consequence that `etcdctl get /registry/pods --prefix --keys-only` is a
      cluster inventory. `[CMD]` `[SOURCE]`
3.12.4 MVCC and revisions: every write bumps a global revision; `resourceVersion` **is** that
      revision, which is why it is opaque and monotonic but not per-object. `[PROVE]`
3.12.5 Compaction and defragmentation: `--auto-compaction-retention`, the `mvcc: database space
      exceeded` alarm, `etcdctl defrag`, and why compaction frees revisions while defrag frees
      disk. `[CMD]` `[PROVE]`
3.12.6 The limits that matter operationally: default **2 GiB** quota (commonly raised to **8 GiB**
      max recommended), the **1.5 MiB** max request size (hence the ~1 MiB Secret/ConfigMap
      ceiling), and the recommendation of **≤ 10 ms** fsync latency — which is why etcd needs
      dedicated fast disks. `[NUM]` `[RESEARCH]`
3.12.7 The watch path: etcd watch → apiserver watch cache → client informers. And the leases
      etcd provides that Kubernetes uses for node heartbeats and leader election. `[PROVE]`
3.12.8 Backup and restore: `etcdctl snapshot save`, `snapshot status`,
      `etcdutl snapshot restore` with `--data-dir` and a new initial cluster, and the fact that a
      restore is a **point-in-time rollback of the entire cluster** — including objects created
      since. Write the runbook. `[CMD]` `[BUILD]` `[PROVE]`
3.12.9 What a lost etcd quorum looks like from the outside and the recovery order.
      `[DIAG]`
3.12.10 The metrics to alert on: `etcd_server_leader_changes_seen_total`,
        `etcd_disk_wal_fsync_duration_seconds`, `etcd_disk_backend_commit_duration_seconds`,
        `etcd_mvcc_db_total_size_in_use_in_bytes`, `etcd_server_proposals_failed_total`,
        `etcd_network_peer_round_trip_time_seconds`. `[NUM]` `[X-REF 20]`
3.12.11 Why nothing in your application should ever talk to etcd, and why "use etcd as our
        configuration store" is almost always the wrong idea when you have a database.
        `[TRAP]`

*(11 leaves)*

## §3.13 Controllers, informers, and the shared cache

3.13.1 The client-go machinery, named and in order: `Reflector` (list + watch) →
      `DeltaFIFO` → `Indexer`/`Store` (the local cache) → `SharedInformer` → event handlers →
      `RateLimitingWorkQueue` → worker goroutines → `Reconcile`. `[SOURCE]`
3.13.2 Why the queue exists between the informer and the worker: it **deduplicates** by key,
      provides rate limiting and exponential backoff, and lets N workers process
      independently — and why the handler must therefore enqueue a *key*, not an object.
      `[PROVE]`
3.13.3 The **cache is eventually consistent**, so a controller's `Get` from the informer can be
      stale, and writing based on a stale read causes a `409 Conflict`. The two correct responses
      (requeue, or read from the API server for the decision). `[PROVE]` `[TRAP]`
3.13.4 Resync vs relist: `resyncPeriod` re-delivers everything from cache (a level-trigger
      safety net); a relist re-fetches from the apiserver after `410 Gone`. `[PROVE]`
3.13.5 Optimistic concurrency in practice: read `resourceVersion`, write with it, get `409`,
      requeue. Why every controller loop must tolerate this and why "retry on conflict" is a
      library function.
3.13.6 Owner references and the **garbage collector** controller: how it builds the ownership
      graph, the `Foreground`/`Background`/`Orphan` deletion semantics, `blockOwnerDeletion`
      and the `foregroundDeletion` finalizer. `[PROVE]` `[SOURCE]`
3.13.7 Finalizer protocol from the controller's side: add the finalizer on first reconcile,
      detect `deletionTimestamp != nil`, do the external cleanup, remove the finalizer. The bug
      that wedges deletion forever is skipping the last step. `[PROVE]` `[BUILD]`
3.13.8 Leader election with `Lease`: `leaseDurationSeconds`, `renewDeadline`, `retryPeriod`, and
      what happens during a leadership gap (nothing reconciles, which is safe because level
      triggering). `[NUM]` `[PROVE]`
3.13.9 Rate limiting and the "hot loop" pathology: a controller that always returns an error and
      requeues immediately can generate thousands of API writes per second. What it looks like in
      APF and the audit log, and the fix. `[DIAG]` `[TRAP]`
3.13.10 Reading a real controller's source: `pkg/controller/deployment` — `syncDeployment`,
        `rolloutRolling`, `reconcileNewReplicaSet`, `reconcileOldReplicaSets`,
        `getAllReplicaSetsAndSyncRevision`, and the `maxUnavailable` arithmetic in
        `deploymentutil`. Quote the surge/unavailable computation and read it line by line.
        `[SOURCE]` `[PROVE]`
3.13.11 The ReplicaSet controller's `expectations` mechanism, and why it exists: without it, a
        slow cache makes the controller create duplicate pods. This is the single best example of
        "eventual consistency has real consequences in controller code". `[PROVE]` `[SOURCE]`
3.13.12 The EndpointSlice controller's batching and why endpoint updates are not instantaneous —
        connecting directly to §2.11.3. `[PROVE]`

*(12 leaves)*

## §3.14 The scheduler

3.14.1 The two-cycle architecture: a **scheduling cycle** (serial, one pod at a time) and a
      **binding cycle** (concurrent), with the framework's extension points between them.
      `[SOURCE]`
3.14.2 The extension points in order, each with its job: `PreEnqueue`, `QueueSort` (exactly one
      plugin), `PreFilter`, `Filter`, `PostFilter` (preemption lives here), `PreScore`, `Score`,
      `NormalizeScore`, `Reserve`/`Unreserve`, `Permit` (approve/deny/**wait**), `PreBind`,
      `Bind` (exactly one), `PostBind`. Plus `EnqueueExtension` and **`QueueingHint`
      (stable 1.34)**. `[SOURCE]` `[RESEARCH]`
3.14.3 The queues: active, backoff, and unschedulable — and `QueueingHint` as the mechanism that
      decides whether a cluster event could plausibly make a rejected pod schedulable, instead of
      periodically retrying everything. `[PROVE]` `[RESEARCH]`
3.14.4 The default filter plugins: `NodeUnschedulable`, `NodeName`, `TaintToleration`,
      `NodeAffinity`, `NodePorts`, `NodeResourcesFit`, `VolumeRestrictions`, `EBSLimits`/
      `NodeVolumeLimits`, `VolumeBinding`, `VolumeZone`, `PodTopologySpread`,
      `InterPodAffinity`. `[SOURCE]`
3.14.5 The default score plugins and their weights: `NodeResourcesFit` (with
      `LeastAllocated`/`MostAllocated`/`RequestedToCapacityRatio` strategies),
      `NodeAffinity`, `InterPodAffinity`, `TaintToleration`, `ImageLocality`,
      `PodTopologySpread`, `NodeResourcesBalancedAllocation`, `VolumeBinding`, plus
      **capacity scoring (beta 1.37)**. Why `ImageLocality` exists and what it does to a fresh
      node. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.14.6 `percentageOfNodesToScore` and the adaptive default: the scheduler stops filtering once it
      has found "enough" feasible nodes, so **placement is not globally optimal by design**. This
      explains a lot of "why did it put it there". `[PROVE]` `[NUM]` `[TRAP]`
3.14.7 Preemption in full: victim selection (lowest priority first, minimising the number of
      victims and PDB violations), the nomination (`status.nominatedNodeName`), the grace period
      given to victims, and why preemption can fail to help (the freed resources get taken by
      another pod). `[PROVE]`
3.14.8 The binding cycle and the `Bind` call: the scheduler does not start the pod; it writes a
      `Binding`/sets `spec.nodeName`, and the kubelet takes over. `[PROVE]`
3.14.9 `KubeSchedulerConfiguration`: profiles, plugin enable/disable, plugin args, multiple
      profiles with different `schedulerName`s. `[CFG]`
3.14.10 Scheduler performance and observability: `scheduler_pending_pods{queue=…}`,
        `scheduler_schedule_attempts_total{result=…}`,
        `scheduler_scheduling_attempt_duration_seconds`,
        `scheduler_e2e_scheduling_duration_seconds`, and the throughput ceiling (order of 100
        pods/second) that matters during a mass reschedule. `[NUM]` `[X-REF 20]`
3.14.11 Gang scheduling and why the default scheduler cannot do it — Kueue, Volcano, and the 1.35+
        gang-scheduling work. Relevant only if QuizStakes adds batch analytics. `[RESEARCH]`
3.14.12 Reading `kube-scheduler` source: `schedulePod`, `findNodesThatFitPod`,
        `prioritizeNodes`, and `NodeResourcesFit`'s scoring function. `[SOURCE]`

*(12 leaves)*

## §3.15 The kubelet

3.15.1 The kubelet's job in one sentence: for each pod assigned to this node, make reality match
      the pod spec, and report the truth back.
3.15.2 The pod sources: the apiserver (watch on `spec.nodeName`), static manifest files
      (`--pod-manifest-path`), and an HTTP endpoint. The merge into a single desired-state channel.
3.15.3 The **sync loop**: `syncLoopIteration` consuming config updates, PLEG events, the periodic
      sync (`--sync-frequency` **1m**), housekeeping (**2s**), and the liveness/readiness manager
      results — then `podWorkers` running one goroutine per pod. `[SOURCE]` `[NUM]`
3.15.4 `syncPod` in order: create the pod's cgroup → create/verify the sandbox (CRI
      `RunPodSandbox` → CNI `ADD`) → pull images (honouring `imagePullPolicy` and the pull
      queue/`--serialize-image-pulls`, `--max-parallel-image-pulls`) → run init containers in
      sequence → start sidecars → start app containers → run `postStart` → start probes.
      `[PROVE]` `[SOURCE]`
3.15.5 The managers the kubelet is made of, each named with its responsibility: `podManager`,
      `containerManager` (cgroups, CPU manager, memory manager, topology manager, device manager),
      `volumeManager` (the desired/actual world reconciler for mounts),
      `imageManager` (+ image GC), `statusManager` (writes pod status),
      `probeManager`, `evictionManager`, `pleg`, `runtimeState`, `oomWatcher`,
      `certificateManager`, `nodeStatusUpdater`, `cadvisor`. `[SOURCE]`
3.15.6 Node status reporting: the periodic status update, the `Lease` heartbeat every
      **10 s** by default with `nodeLeaseDurationSeconds` **40**, and the node controller's
      `--node-monitor-grace-period` **50 s** before marking `NotReady`. Then the
      `NoExecute` taint plus **5-minute** `tolerationSeconds` before pods are evicted — so a dead
      node's pods move after roughly **5–6 minutes**, not instantly. This arithmetic is a very
      common interview question. `[NUM]` `[PROVE]` `[RESEARCH]`
3.15.7 The volume manager's reconcile loop, and why a stuck unmount blocks pod deletion — the
      `Terminating` pod with `FailedUnmount` events. `[DIAG]`
3.15.8 The probe manager: one worker per probe per container, the result cache, and how a readiness
      result reaches the endpoints controller (via pod status → apiserver → EndpointSlice
      controller — **three hops**, which is why readiness changes are not instant). `[PROVE]`
3.15.9 The eviction manager's loop (§2.12.7–2.12.10) as a kubelet component, with its 10-second
      housekeeping and its reclaim-before-evict behaviour.
3.15.10 The kubelet's own API: `:10250` (authenticated: `/pods`, `/runningpods`, `/metrics`,
        `/metrics/cadvisor`, `/metrics/resource`, `/metrics/probes`, `/stats/summary`,
        `/logs`, `/exec`, `/portForward`, `/configz`, `/healthz`), the read-only `:10255` (should
        be disabled), and **fine-grained kubelet API authorization (GA 1.36)** which splits these
        into distinct RBAC subresources instead of one `nodes/proxy` grant. `[CFG]` `[RESEARCH]`
        `[X-REF 13]`
3.15.11 `KubeletConfiguration` fields a backend engineer should recognise: `maxPods` (**110**
        default), `podsPerCore`, `cgroupDriver`, `containerLogMaxSize`/`Files`,
        `imageGCHighThresholdPercent`/`Low`, `evictionHard`/`Soft`,
        `kubeReserved`/`systemReserved`, `cpuManagerPolicy`, `topologyManagerPolicy`,
        `serializeImagePulls`, `registryPullQPS`/`registryBurst`,
        `shutdownGracePeriod`, `failSwapOn`, `protectKernelDefaults`,
        `seccompDefault`, `memorySwap`. `[CFG]` `[NUM]`
3.15.12 The kubelet as the reason `kubectl logs` and `kubectl exec` work at all, and what breaks
        when the kubelet is up but the runtime is down (pods keep running, nothing new starts,
        `PLEG is not healthy`). `[PROVE]` `[DIAG]`
3.15.13 The **1.35 cgroup v2 requirement**: the kubelet refuses to start by default on a cgroup v1
        host. State the flag/behaviour precisely and re-verify. `[VERSION-TRAP]` `[RESEARCH]`
3.15.14 The kubelet's certificate rotation (`serverTLSBootstrap`, `RotateKubeletServerCertificate`)
        and the CSR approval flow — plus the 1.37 `PodCertificateRequest`/`ClusterTrustBundle`
        APIs that extend the same idea to workloads. `[RESEARCH]`

*(14 leaves)*

## §3.16 kube-proxy: the Service datapath

3.16.1 What kube-proxy is: a controller that watches Services and EndpointSlices and programs the
      kernel so that packets to a ClusterIP are DNAT'd to a pod IP. It is **not** a proxy in the
      data path in iptables/IPVS/nftables modes — no userspace hop. `[PROVE]` `[TRAP]`
3.16.2 The (removed) `userspace` mode as the historical baseline, and why it was slow.
3.16.3 **iptables mode**, the chain walk in order: `PREROUTING`/`OUTPUT` → `KUBE-SERVICES` →
      a per-service `KUBE-SVC-<hash>` chain → statistic-module random selection among
      `KUBE-SEP-<hash>` chains → `DNAT` to the endpoint; plus `KUBE-MARK-MASQ`,
      `KUBE-POSTROUTING`, `KUBE-NODEPORTS`, `KUBE-FORWARD`, `KUBE-EXTERNAL-SERVICES`,
      `KUBE-FIREWALL`. Show real `iptables-save` output and read it. `[SOURCE]` `[PROVE]`
3.16.4 The backend selection: the `statistic` module with `--mode random --probability`, computed
      so each endpoint gets an equal share — which is **per-connection**, not per-request, and
      therefore does nothing for a long-lived HTTP/2 connection (§2.19.5). `[PROVE]` `[NUM]`
3.16.5 Why iptables mode scales badly: rules are a **linear list evaluated in order**, and
      updating them requires rewriting and reloading the whole table under a lock. With 5,000
      Services × 10 endpoints you are at ~O(100k) rules and multi-second sync times. Quantify.
      `[PROVE]` `[NUM]`
3.16.6 The mitigations that existed before nftables: `--iptables-min-sync-period` (**1s**),
      `--iptables-sync-period` (**30s**), partial sync, and `KUBE-SERVICES` restructuring.
      `[NUM]` `[CFG]`
3.16.7 **IPVS mode**: an in-kernel L4 load balancer with hash-table lookup (O(1)), the scheduling
      algorithms `rr`, `wrr`, `lc`, `wlc`, `dh`, `sh`, `sed`, `nq`, and the dummy interface
      `kube-ipvs0` holding every ClusterIP. Plus its residual iptables rules for masquerade and
      the reason it was **deprecated in 1.35**. `[SOURCE]` `[NUM]` `[VERSION-TRAP]`
3.16.8 **nftables mode**: a single table with maps/sets keyed by service VIP and port, so lookup is
      a hash rather than a linear scan; incremental updates instead of whole-table reloads;
      **verdict maps** for endpoint selection. GA 1.33, kernel **5.13+**, **not yet the default in
      1.37** (KEP-5343 tracks the switch). `[SOURCE]` `[NUM]` `[RESEARCH]`
3.16.9 The measured differences worth citing and attributing: rule-count growth, sync latency at
      scale, and first-packet latency. Attribute to the Kubernetes blog post rather than
      asserting. `[RESEARCH]`
3.16.10 **kube-proxy replacement**: Cilium's eBPF datapath attaching at the socket and TC layers,
        which removes DNAT for in-cluster traffic entirely (the connection is redirected at
        `connect()` time), plus Calico's eBPF mode. What you gain and what you lose (observability
        tooling that reads iptables). `[PROVE]` `[RESEARCH]`
3.16.11 Conntrack's role: the DNAT decision is recorded per connection, so a mid-connection
        endpoint change leaves a stale entry pointing at a dead pod — the mechanism behind
        "connection refused after a scale-down" and the reason
        `--conntrack-tcp-timeout-established`, `nf_conntrack_max` and the "graceful termination"
        handling exist. `[PROVE]` `[DIAG]`
3.16.12 `sessionAffinity: ClientIP` implemented via the `recent` module (iptables) or IPVS
        persistence, with the **10800 s** default timeout. `[NUM]`
3.16.13 `externalTrafficPolicy: Local` at the datapath level: no cross-node forwarding, the
        `healthCheckNodePort` telling the cloud LB which nodes have endpoints, and the
        traffic imbalance that follows from uneven pod distribution. `[PROVE]`
3.16.14 The complete packet walk for one QuizStakes request, hop by hop:
        `application-gateway` pod → `client-restrictions` ClusterIP → conntrack/DNAT → veth →
        bridge/eBPF → (possibly VXLAN/ENI) → destination veth → pod. Annotate each hop with its
        latency contribution. `[PROVE]` `[NUM]`
3.16.15 Debugging the datapath: `iptables-save | grep <clusterIP>`, `nft list table ip kube-proxy`,
        `ipvsadm -Ln`, `conntrack -L -d <clusterIP>`, `kubectl get endpointslices`,
        `kubectl logs -n kube-system ds/kube-proxy`, and `tcpdump` on the veth. `[CMD]` `[DIAG]`

*(15 leaves)*

## §3.17 CNI and the pod network

3.17.1 The Kubernetes network model's four requirements, stated as invariants: every pod gets its
      own IP; pods can reach all pods **without NAT**; nodes can reach all pods without NAT; and
      the IP a pod sees itself as is the IP others see. Everything else is an implementation
      detail. `[SOURCE]` `[PROVE]`
3.17.2 The CNI spec: a plugin binary in `/opt/cni/bin`, a JSON config in
      `/etc/cni/net.d`, the operations `ADD`, `DEL`, `CHECK`, `VERSION`, `GC`, and the
      environment contract (`CNI_COMMAND`, `CNI_CONTAINERID`, `CNI_NETNS`, `CNI_IFNAME`,
      `CNI_ARGS`, `CNI_PATH`) with the result on stdout. `[SOURCE]`
3.17.3 Who calls it: the **container runtime** (containerd's CRI plugin) during `RunPodSandbox`,
      not the kubelet — which is why a broken CNI shows up as pods stuck in
      `ContainerCreating` with `NetworkPlugin cni failed to set up pod`. `[PROVE]` `[DIAG]`
3.17.4 Chained plugins and the standard set: `bridge`, `ptp`, `host-local` and `dhcp` IPAM,
      `portmap`, `bandwidth`, `tuning`, `firewall`, `sbr`, `loopback`.
3.17.5 The datapath families, each with its mechanism: **overlay/encapsulation** (VXLAN or
      IP-in-IP — Flannel, Calico VXLAN; costs ~50 bytes of MTU and some CPU), **pure routing/BGP**
      (Calico BGP — no encapsulation, needs L3 fabric cooperation), **cloud-native ENI/IP
      allocation** (AWS VPC CNI, Azure CNI — pods get real VPC IPs, so security groups and flow
      logs work, at the cost of IP exhaustion), and **eBPF** (Cilium — programmable, no iptables).
      `[PROVE]`
3.17.6 The AWS VPC CNI's arithmetic in detail: ENIs per instance type × IPs per ENI = max pods,
      the warm-pool settings (`WARM_ENI_TARGET`, `WARM_IP_TARGET`, `MINIMUM_IP_TARGET`),
      **prefix delegation** (`ENABLE_PREFIX_DELEGATION` giving /28 prefixes) and the
      `max-pods` calculator. Work a real instance type. `[NUM]` `[PROVE]` `[X-REF 18]`
3.17.7 MTU as a real and badly-diagnosed problem: overlay encapsulation reduces the usable MTU, so
      small requests succeed and large responses hang. The symptom, `ping -s` bisection, and
      `PMTUD` blackholes. `[DIAG]` `[X-REF 10]`
3.17.8 IPAM lifecycle and IP reuse: a deleted pod's IP is returned and may be reused within
      seconds, which is why a client caching a pod IP can hit an entirely different service.
      `[PROVE]` `[TRAP]`
3.17.9 NetworkPolicy enforcement at the datapath: how Calico compiles policy into iptables/eBPF
      and how Cilium compiles it into eBPF identity-based policy — and again, that **without an
      enforcing plugin the policy object is inert**. `[PROVE]` `[TRAP]`
3.17.10 Multi-network: Multus, `NetworkAttachmentDefinition`, and the newer
        `DRA`-based network device work — name it, do not teach it.
3.17.11 Debugging pod networking from first principles: `ip netns`/`nsenter -t <pid> -n`,
        `ip addr`, `ip route`, `ip -d link show` on the veth, `bridge fdb`, `tcpdump -i`
        on both veth ends, `ss -tnp` inside the pod, and `kubectl debug node/…` as the way in.
        `[CMD]` `[BUILD]`
3.17.12 The `hostNetwork` shortcut at the datapath level, and why a `hostNetwork` pod's
      `status.podIP` equals the node IP. `[PROVE]`

*(12 leaves)*

## §3.18 CSI

3.18.1 The CSI architecture: a **controller plugin** (a Deployment, doing `CreateVolume`,
      `DeleteVolume`, `ControllerPublishVolume` = attach, `CreateSnapshot`) and a **node plugin**
      (a DaemonSet, doing `NodeStageVolume` = format+mount to a global path, `NodePublishVolume` =
      bind-mount into the pod), plus the sidecars `external-provisioner`, `external-attacher`,
      `external-resizer`, `external-snapshotter`, `node-driver-registrar`, and `livenessprobe`.
      `[SOURCE]`
3.18.2 The gRPC service split — `Identity`, `Controller`, `Node` — and the capability negotiation
      that tells Kubernetes what the driver can do. `[SOURCE]`
3.18.3 The **stage vs publish** distinction and why it exists: staging happens once per node
      (format and mount), publishing happens once per pod (bind mount), which is how one RWO
      volume serves two pods on the same node. `[PROVE]`
3.18.4 `VolumeAttachment` objects and the attach/detach controller; the AWS EBS attach limits per
      instance type and the `node(s) exceed max volume count` scheduling failure. `[NUM]`
      `[DIAG]` `[X-REF 18]`
3.18.5 The **Multi-Attach error** and the 6-minute force-detach: what happens when a node dies
      holding an RWO volume, why a StatefulSet pod cannot start on a new node until the old
      attachment is released, and `Non-graceful node shutdown`'s `out-of-service` taint as the
      supported fix. `[NUM]` `[DIAG]` `[PROVE]`
3.18.6 In-tree → CSI migration: what `CSIMigration` did, and why old manifests referencing
      `kubernetes.io/aws-ebs` still work through a translation layer. `[VERSION-TRAP]`
3.18.7 `CSIDriver` object fields: `attachRequired`, `podInfoOnMount`, `volumeLifecycleModes`,
      `fsGroupPolicy`, `requiresRepublish`, `seLinuxMount` (the last being why SELinux mount
      options can be applied without a recursive relabel). `[CFG]`
3.18.8 Ephemeral inline CSI volumes and how the **Secrets Store CSI Driver** uses them — a
      "volume" that is really a secret fetch. `[PROVE]`
3.18.9 Debugging a CSI problem: the controller pod's sidecar logs, the node plugin's logs,
      `kubectl get volumeattachments`, `kubectl describe pvc`, and the `mount` table on the node.
      `[CMD]` `[DIAG]`

*(9 leaves)*

## §3.19 CoreDNS internals

3.19.1 CoreDNS as a plugin chain: the `Corefile`'s server blocks, the ordered plugin list, and the
      fact that plugin **order in the code**, not in the file, determines execution. `[SOURCE]`
3.19.2 The `kubernetes` plugin: it watches Services, EndpointSlices and Pods through an informer
      and answers from memory — so DNS answers are as fresh as the informer cache and no faster.
      `[PROVE]`
3.19.3 The plugins that matter operationally: `cache` (with `success`/`denial` TTLs and
      `serve_stale`), `forward` (with `policy`, `max_fails`, `health_check`, and multiple
      upstreams), `errors`, `log`, `health`, `ready`, `prometheus`, `loop` (the
      self-referential-forward detector that crash-loops CoreDNS on a misconfigured node
      resolver), `reload`, `autopath`, `rewrite`, `template`, `hosts`. `[CFG]`
3.19.4 `autopath` as the server-side ndots mitigation: CoreDNS notices the search-domain pattern
      and answers with a CNAME to the right name, collapsing six queries into one — at the cost
      of a pod-watching informer. `[PROVE]` `[RESEARCH]`
3.19.5 Sizing: queries per second per replica, the `cluster-proportional-autoscaler`, and the
      standing recommendation to run at least 2 replicas with anti-affinity. `[NUM]`
3.19.6 The metrics: `coredns_dns_requests_total`, `coredns_dns_responses_total{rcode}`,
      `coredns_dns_request_duration_seconds`, `coredns_forward_requests_total`,
      `coredns_cache_hits_total`/`misses_total`, `coredns_panics_total`. What a healthy
      NXDOMAIN ratio looks like and why an unhealthy one is usually ndots. `[NUM]` `[X-REF 20]`
3.19.7 NodeLocal DNSCache's datapath: a link-local IP on a dummy interface, iptables NOTRACK rules
      to skip conntrack, and a TCP upstream to CoreDNS — which is precisely what removes the
      5-second conntrack-race timeouts. `[PROVE]` `[RESEARCH]`
3.19.8 The failure modes: CoreDNS OOMKilled by a query flood, `loop` plugin crash-loop, an
      overloaded upstream making every external lookup slow, and a NetworkPolicy blocking port 53.
      `[DIAG]`

*(8 leaves)*

## §3.20 Concurrency, consistency, and failure in the control plane

3.20.1 The consistency model, stated once and precisely: **linearizable writes through etcd,
      eventually consistent reads through caches, and no cross-object transactions**. Every
      surprising behaviour in Kubernetes follows from one of those three clauses. `[PROVE]`
3.20.2 Optimistic concurrency as the only mutual exclusion: `resourceVersion` + `409`, no locks,
      no two-phase commit. What that means for two controllers touching the same object.
      `[PROVE]`
3.20.3 The absence of ordering: `kubectl apply -f dir/` has no dependency graph, so a Deployment
      can be created before its ConfigMap. The three answers (retry-until-healthy, sync waves,
      init containers) and why the level-triggered design makes the first one work. `[PROVE]`
3.20.4 Duplicate-work hazards and how each controller avoids them: ReplicaSet expectations,
      Job's `podReplacementPolicy`, the StatefulSet's ordinal identity, and leader election for
      singletons. `[PROVE]`
3.20.5 Split-brain scenarios that actually occur: two `bank-withdrawal` runners after a leader-lease
      renewal failure; two `funds-ledger` instances both believing they own a client partition
      during a rebalance (the scenario names this explicitly); and a pod running on a node the
      control plane thinks is dead. For each: the mechanism, the detection, and the mitigation.
      `[PROVE]` `[X-REF 22]`
3.20.6 **The unavoidable fact for the money path**: Kubernetes gives you *at-least-once* pod
      execution, not exactly-once. Therefore idempotency and a durable lock are application
      requirements, not orchestration features. This is the single most important sentence in the
      part for a payments engineer. `[PROVE]` `[X-REF 14]`
3.20.7 Failure-domain reasoning: pod → node → AZ → region, and which Kubernetes construct addresses
      each (replicas, `topologySpreadConstraints`, multi-AZ node groups, and nothing at all for
      region — that is a second cluster). `[PROVE]` `[X-REF 22]`
3.20.8 What a control-plane outage does and does not break (restating §1.18.6 with the mechanism
      now available), and what a *node* outage does on the 5–6 minute timeline from §3.15.6.
      `[NUM]`
3.20.9 Clock assumptions: leases and probes depend on reasonably synchronised clocks; a node with
      a skewed clock produces bizarre lease and certificate failures. `[DIAG]`
3.20.10 The graceful-degradation properties worth designing for: cached DNS answers, existing
        conntrack entries, and already-pulled images all mean a partially broken cluster keeps
        serving — and that is why "it looked fine" during a control-plane incident. `[PROVE]`

*(10 leaves)*

## §3.21 The security boundary, examined

3.21.1 The threat model laid out as columns: attacker on the network, attacker with a pod,
      attacker with a ServiceAccount token, attacker with node access, attacker in the supply
      chain. For each, what container isolation does and does not stop.
3.21.2 The escape chain from a pod, step by step, and the control that breaks each step: reachable
      metadata endpoint → IMDSv2 and a NetworkPolicy; mounted SA token → `automountServiceAccountToken:
      false`; `create pods` RBAC → least privilege; `hostPath` → PSS Baseline; `privileged` →
      PSS; kernel exploit → seccomp, user namespaces, gVisor/Kata. `[PROVE]`
3.21.3 Why `seccompProfile: RuntimeDefault` is a genuinely high-value single setting: it removes
      the syscalls most kernel exploits need, at essentially zero cost. `[PROVE]`
3.21.4 The specific isolation gap user namespaces close, and the residual risk when they are on.
3.21.5 The node as the real blast radius: everything on a node shares a kernel, so a
      `card-payments` pod next to a low-trust pod is a policy failure regardless of NetworkPolicy.
      Hence dedicated node pools. `[PROVE]`
3.21.6 The Docker socket, restated as the strongest statement in the guide: **socket access is
      root on the host**, so mounting it into a CI container, a monitoring agent or a
      Testcontainers job is a cluster-admin-equivalent grant. `[PROVE]` `[TRAP]`
3.21.7 Image-layer forensics as an attacker technique and a defender technique: `docker save` +
      `tar` to recover the deleted secret from §1.6.5, and the same command to audit whether one
      ever landed. `[CMD]` `[BUILD]`
3.21.8 Runtime detection and response: what a Falco rule for "shell spawned in a container" costs
      and catches, and what the response runbook is when it fires on `funds-ledger`. `[X-REF 20]`
3.21.9 Compliance mapping without ceremony: the CIS Kubernetes Benchmark, `kube-bench`,
      `kubescape`, and NSA/CISA hardening guidance — as checklists you run, not documents you
      read. `[CMD]` `[RESEARCH]`

*(9 leaves)*

## §3.22 Reading the source

3.22.1 The repository map worth knowing: `kubernetes/kubernetes` (`pkg/kubelet`,
      `pkg/scheduler`, `pkg/controller`, `pkg/registry`, `staging/src/k8s.io/*`),
      `kubernetes/api`, `kubernetes/client-go`, `kubernetes-sigs/controller-runtime`,
      `containerd/containerd`, `opencontainers/runc`, `moby/buildkit`,
      `kubernetes-sigs/gateway-api`, `kubernetes/enhancements` (the KEPs).
3.22.2 How to find the code behind a behaviour, as a procedure: find the API field in
      `staging/src/k8s.io/api/...types.go`, grep for the field name to find the controller that
      reads it, then read that controller's sync function. Demonstrate it on
      `progressDeadlineSeconds`. `[BUILD]` `[SOURCE]`
3.22.3 Reading a KEP properly: the summary, motivation, design details, **test plan**, graduation
      criteria, and the "drawbacks / alternatives considered" section that tells you what the
      feature will not do. Do it for KEP-1287 (in-place resize) and KEP-753 (sidecars).
      `[SOURCE]` `[RESEARCH]`
3.22.4 The five source excerpts this guide must actually quote and explain line by line: the
      Deployment controller's `maxUnavailable`/`maxSurge` computation; the kubelet's
      `syncPod` ordering; the eviction manager's threshold comparison and ranking function;
      kube-proxy's iptables chain generation; and runc's `pivot_root` sequence. `[SOURCE]`
3.22.5 Where the numbers in this file come from, so the reader can re-derive them:
      `pkg/kubelet/eviction/defaults.go`-style default blocks, `pkg/apis/core/v1/defaults.go`,
      and the generated API reference. `[SOURCE]`

*(5 leaves)*

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf ships complete, runnable artefacts — no elisions, no `...`. Java is Java 21;
scripts are POSIX shell or bash with a stated shebang; manifests are complete and `kubectl
apply`-able. Each build is followed by a **Diff vs the real one** table.

## §4.1 A container from scratch, with nothing but the kernel

4.1.1 `[BUILD]` A bash script that creates a container by hand: `unshare --pid --net --mount --uts
      --ipc --fork`, a `mount --make-rprivate /`, an OverlayFS mount assembled from an extracted
      image rootfs, `pivot_root`, `mount -t proc proc /proc`, a `hostname`, a `veth` pair into the
      host bridge with an IP and a default route, a cgroup created under
      `/sys/fs/cgroup/demo` with `cpu.max` and `memory.max` written, and finally `exec` of a shell.
      Every line commented with which container property it produces.
4.1.2 `[BUILD]` The verification harness: from inside, `ps aux` (only your processes), `ip addr`
      (only your veth), `cat /proc/self/cgroup`, `hostname`, `df -h`, and a `stress`-style loop
      proving the CPU quota throttles and the memory limit OOMKills.
4.1.3 `[BUILD]` The same container expressed as an OCI bundle: a hand-written `config.json` plus
      the extracted rootfs, run with `runc run`, so the reader sees the spec produce the identical
      result.
4.1.4 `[BUILD]` A minimal PID-1 init in ~40 lines of C or Go that installs SIGTERM/SIGINT handlers
      and reaps children with `waitpid(-1, …, WNOHANG)` — the thing `tini` is.
4.1.5 **Diff vs the real one** (runc/containerd): seccomp, LSM labels, capability sets, masked and
      readonly paths, user-namespace mappings, `no_new_privs`, rlimits, the cgroup delegation
      dance, hook execution, the shim and its stdio/exit-status ownership, image unpacking and
      snapshot management, CNI invocation, error handling and cleanup on partial failure — and
      why each matters.

*(5 leaves)*

## §4.2 An OCI image reader and puller in Java

4.2.1 `[BUILD]` `record Descriptor(String mediaType, String digest, long size, Platform platform,
      String artifactType, Map<String,String> annotations)`,
      `record ImageIndex(int schemaVersion, String mediaType, List<Descriptor> manifests)`,
      `record ImageManifest(int schemaVersion, String mediaType, Descriptor config,
      List<Descriptor> layers, Descriptor subject, Map<String,String> annotations)`, and
      `record ImageConfig(String architecture, String os, ContainerConfig config, RootFs rootfs,
      List<History> history)` — sealed where appropriate, with Jackson binding.
4.2.2 `[BUILD]` A `RegistryClient` on `java.net.http.HttpClient` implementing the token handshake
      from §3.7.3: probe `/v2/`, parse `WWW-Authenticate`, fetch the bearer token, retry, and
      cache the token per scope.
4.2.3 `[BUILD]` `resolve(String reference)` — full reference parsing per §1.14.1 (defaults for
      registry, `library/`, and `:latest`), then `HEAD`/`GET` the manifest with the correct
      `Accept` list, follow an index to the manifest matching `linux/amd64`, and verify the
      returned digest against the computed `sha256` of the body. **Digest verification is the
      point of the exercise.**
4.2.4 `[BUILD]` `pull(...)` — download each layer blob to a content-addressed store
      (`blobs/sha256/<hex>`), verify each digest while streaming, and compute the `diff_id` of the
      decompressed stream to prove §1.5.6's two-hash claim.
4.2.5 `[BUILD]` `explain(...)` — print the config's entrypoint, cmd, user, env, exposed ports and
      per-layer sizes with the `history` `created_by` strings: a working `docker history` for an
      image you have never pulled with Docker.
4.2.6 `[BUILD]` A `main` that runs against `eclipse-temurin:21-jre-jammy` and against a QuizStakes
      image, printing the manifest digest, the image ID, the layer count and total size.
4.2.7 **Diff vs the real one** (`crane`/containerd's resolver): mirror and `hosts.toml` support,
      cross-repo blob mounts, chunked resumable downloads, parallel range requests, retry with
      backoff, `zstd` and non-distributable layers, the Referrers API and tag-schema fallback,
      OCI-layout on-disk format, garbage collection, lease management, signature verification,
      and platform matching including `variant` and `os.version`.

*(7 leaves)*

## §4.3 A cgroup-aware resource reporter in Java

4.3.1 `[BUILD]` `ContainerLimits` — detect cgroup v1 vs v2 (`/sys/fs/cgroup/cgroup.controllers`
      exists ⇒ v2), read `memory.max`/`memory.limit_in_bytes` (handling the literal `"max"` and
      the v1 sentinel `9223372036854771712`), `cpu.max`/`cpu.cfs_quota_us` + `cpu.cfs_period_us`,
      `cpu.weight`/`cpu.shares`, `pids.max`, and `cpuset.cpus.effective` (parsing the
      `0-3,8` range syntax). Return a record.
4.3.2 `[BUILD]` `effectiveCpus()` — reproduce the JVM's own calculation
      (`ceil(quota/period)`, bounded by the cpuset and by `ActiveProcessorCount`) and assert it
      equals `Runtime.getRuntime().availableProcessors()`. When it does not, print why.
4.3.3 `[BUILD]` `ThrottleMonitor` — a scheduled task reading `cpu.stat` every 10 s and logging
      `nr_throttled/nr_periods` and `throttled_usec` as a percentage of wall time, registered as a
      Micrometer gauge so it lands on the dashboard from §2.28.11.
4.3.4 `[BUILD]` `MemoryHeadroomReporter` — `memory.current`, `memory.max`, working set computed as
      `memory.current − inactive_file` from `memory.stat`, the JVM's committed heap and
      `NativeMemoryTracking` summary if enabled, and the derived headroom in MiB. Log a warning
      when headroom drops below a threshold.
4.3.5 `[BUILD]` A Spring Boot `@Component` wrapping all of the above with an
      `ApplicationReadyEvent` listener that logs one authoritative line at start-up: cgroup
      version, memory limit, heap max, effective CPUs, `MaxRAMPercentage`, and computed non-heap
      headroom — the line you want in the log of every QuizStakes service.
4.3.6 `[BUILD]` A JUnit 5 test using Testcontainers to run the class under a
      `--memory=512m --cpus=0.5` container and assert the values it reports. `[X-REF 16]`
4.3.7 **Diff vs the real one** (HotSpot's `OSContainer`/`CgroupSubsystemFactory`): cgroup namespace
      handling and `/proc/self/mountinfo` parsing, hybrid v1/v2 hosts, the memory+swap limit
      interaction, host-vs-container detection heuristics, `-XX:ActiveProcessorCount` precedence,
      dynamic re-reading after an in-place resize, and the interaction with
      `-XX:+UseContainerSupport` being disabled.

*(7 leaves)*

## §4.4 A reconciliation loop in Java

4.4.1 `[BUILD]` A generic, dependency-free reconciler: `interface Reconciler<K> { Result
      reconcile(K key); }`, `sealed interface Result { record Done() …; record RequeueAfter(Duration
      d) …; record Failed(Throwable t) …; }`, a `WorkQueue<K>` that **deduplicates by key**,
      supports delayed re-add, and applies exponential backoff per key, and a fixed worker pool
      draining it.
4.4.2 `[BUILD]` A `Store<K,V>` (the informer cache stand-in) with an indexer, plus a `Watcher` that
      simulates `ADDED`/`MODIFIED`/`DELETED`/`BOOKMARK` and a periodic full resync — so the reader
      can *see* level triggering absorb a dropped event.
4.4.3 `[BUILD]` A test that drops a random 30% of events and asserts the desired state is still
      reached. **This is the `[PROVE]` for §1.20.3, executable.**
4.4.4 `[BUILD]` An owner-reference-style cascade: deleting a parent key enqueues its children, with
      a finalizer that must complete before the parent is removed — and a test for the wedged case
      when the finalizer never clears.
4.4.5 `[BUILD]` A real controller against a real cluster using fabric8: watch `ConfigMap`s labelled
      `quizstakes.io/reload=true` and trigger a `rollout restart` (patch the pod template
      annotation) on the Deployments that reference them — solving §1.25.3 in ~120 lines.
4.4.6 `[BUILD]` The `PaymentRun` operator sketch from §2.26.11 with the Java Operator SDK: the CRD
      YAML with a CEL validation rule enforcing a single in-flight run, the `Reconciler`, the
      status conditions, the finalizer that releases the lock, and the `Lease`-based leader
      election.
4.4.7 **Diff vs the real one** (client-go / controller-runtime): the `Reflector`'s
      list-then-watch with `resourceVersion` bookkeeping and `410 Gone` relist, `DeltaFIFO`
      compression semantics, shared informers with multiple handlers, per-GVK caches and field
      indexers, `RateLimitingQueue`'s two-tier limiter, metrics and workqueue instrumentation,
      leader election with `Lease` renewal, graceful shutdown draining, `RetryOnConflict`,
      server-side apply with a field manager, event recording, and admission-webhook plumbing.

*(7 leaves)*

## §4.5 A signal-correct, shutdown-correct service

4.5.1 `[BUILD]` A plain Java 21 HTTP service (`com.sun.net.httpserver` or a small
      `HttpServer` on virtual threads) with: a `Runtime.addShutdownHook`, an in-flight request
      counter, a readiness flag flipped false on SIGTERM, refusal of new work, a drain with a
      deadline, and `System.exit(0)` — the reference implementation of §2.11.1 steps 4–6.
4.5.2 `[BUILD]` The same behaviour in Spring Boot 3.x: `server.shutdown=graceful`,
      `spring.lifecycle.timeout-per-shutdown-phase=30s`, a `SmartLifecycle` bean with an explicit
      phase that closes the ledger connection pool and the broker producer last, an
      `AvailabilityChangeEvent` listener that logs the readiness transition, and a Micrometer
      `MeterRegistry` close that flushes.
4.5.3 `[BUILD]` The matching Kubernetes manifest: exec-form entrypoint, `preStop` sleep,
      `terminationGracePeriodSeconds` computed from §2.11.5, all three probes with the values
      derived in §1.27, `resources` with `requests.memory == limits.memory`, no CPU limit, the
      full Restricted-compliant `securityContext`, and the Downward-API env vars.
4.5.4 `[BUILD]` The proof harness: a `kind` cluster, the service deployed with 4 replicas, a
      load generator at 1,200 req/s (the scenario's stake-reservation rate), `kubectl rollout
      restart`, and an assertion of **zero** non-2xx responses. Then the same run with the
      `preStop` removed, showing the failures — so the reader sees the difference rather than
      reading about it.
4.5.5 `[BUILD]` The two negative controls: shell-form `ENTRYPOINT` (SIGTERM never arrives, exit
      143 after grace period) and `terminationGracePeriodSeconds: 5` (SIGKILL mid-drain), each with
      the log output that identifies it.
4.5.6 **Diff vs the real one** (a production Spring Boot service): Tomcat/Netty connector shutdown
      internals, keep-alive connection handling, HTTP/2 GOAWAY, in-flight async and
      `CompletableFuture` completion, Kafka consumer `close(Duration)` and offset commit, JDBC pool
      `evictConnections`, distributed lock release, JFR/heap-dump-on-exit, and the readiness gate
      integration with the cloud load balancer.

*(6 leaves)*

## §4.6 The complete QuizStakes container and manifest set

4.6.1 `[BUILD]` The production `Dockerfile` from §1.9.10 for a Spring Boot service, with the
      layered-jar extraction, the cache mounts, the non-root numeric UID, the digest-pinned base,
      and every OCI annotation.
4.6.2 `[BUILD]` A `jlink`-based variant for `client-restrictions`, with the `jdeps` command that
      produced the module list and the measured size and start-up difference.
4.6.3 `[BUILD]` `.dockerignore`, `docker-bake.hcl` building all 25 services with a shared base
      target, and the CI workflow from §2.4.4–2.4.5.
4.6.4 `[BUILD]` `compose.yaml` — the full local stack from §1.15.14 with healthchecks, a
      `migrations` one-shot, `depends_on` conditions, named volumes, profiles for the optional
      services, and `develop.watch`.
4.6.5 `[BUILD]` The Kustomize tree from §2.24.12: `base/` per service (Deployment, Service,
      ServiceAccount, ConfigMap, PDB, HPA, NetworkPolicy), `components/money-path-hardening`,
      and `overlays/{dev,staging,prod}` with the replica and resource values from Appendix A.6.
4.6.6 `[BUILD]` The `funds-ledger` manifests as the hardest case: 3 replicas across 3 AZs with
      `topologySpreadConstraints`, a PDB of `minAvailable: 2`, no CPU limit,
      `requests.memory == limits.memory` at the size derived in §2.1.13, a 12 GB heap via
      `MaxRAMPercentage`, ZGC, a `preStop` and grace period sized for a 150 ms budget with pool
      close, and a `PriorityClass` above the read-only services.
4.6.7 `[BUILD]` The `bank-withdrawal` manifests: a `CronJob` that only *triggers*, plus a
      leader-elected Deployment holding the `Lease`, `concurrencyPolicy: Forbid`,
      `startingDeadlineSeconds` set, `activeDeadlineSeconds`, a `terminationGracePeriodSeconds`
      that accommodates a 40-minute run, and the drain-before-terminate hook.
4.6.8 `[BUILD]` The `card-payments` manifests: a dedicated tainted node pool, a NetworkPolicy
      permitting egress only to the PSP CIDR, a separate ServiceAccount with its own IRSA role, and
      a `ValidatingAdmissionPolicy` that refuses any other workload onto that node pool.
4.6.9 `[BUILD]` The entry layer: `Gateway`, `HTTPRoute`s, `ReferenceGrant`s and the
      cert-manager `Certificate` from §1.24.12.
4.6.10 `[BUILD]` The namespace scaffolding: three `Namespace`s with Pod Security labels,
       `ResourceQuota`, `LimitRange`, default-deny `NetworkPolicy`, and the DNS allow rule.
4.6.11 **Diff vs the real one** (a mature platform's manifests): what a real platform adds —
       ArgoCD `Application`s and sync waves, ExternalSecret objects, ServiceMonitor/PodMonitor,
       PrometheusRule, OTel auto-instrumentation annotations, cost-allocation labels, an
       `imagePolicy` for automated digest updates, and the golden-path Helm chart that generates
       all of it from ten values.

*(11 leaves)*

## §4.7 Diagnostic scripts and runbooks

4.7.1 `[BUILD]` `pod-triage.sh <pod> [-n ns]` — runs the §2.29.1 procedure in order and prints a
      structured summary: phase, container states with reasons, restart counts, last terminated
      state with exit code, resource requests/limits vs current usage, throttling ratio, probe
      configuration, events sorted by time, and the owning ReplicaSet's image digest.
4.7.2 `[BUILD]` `service-reachability.sh <service> [-n ns]` — the §2.29.11 checklist as a script:
      selector vs pod labels, EndpointSlice contents with `ready`/`serving`/`terminating`,
      `targetPort` resolution, a DNS lookup from a throwaway pod, a direct pod-IP `curl`, and a
      NetworkPolicy summary for the target.
4.7.3 `[BUILD]` `node-pressure.sh <node>` — allocatable vs allocated vs actual, the eviction
      thresholds and current signal values, image and log disk usage, the pods ranked by
      overage-above-request (the eviction order), and the node's conditions and taints.
4.7.4 `[BUILD]` `throttle-report.sh` — cluster-wide `nr_throttled/nr_periods` per container via
      `kubectl get --raw /api/v1/nodes/<n>/proxy/metrics/cadvisor`, sorted worst-first, with a
      threshold flag.
4.7.5 `[BUILD]` `image-audit.sh` — every running image digest in the cluster, mapped to its
      `org.opencontainers.image.revision` annotation and its registry scan status; flags
      `:latest`, unpinned tags, images not in the internal registry, and images whose digest is
      no longer present in the registry (the un-rollbackable set).
4.7.6 `[BUILD]` `etcd-backup.sh` and the restore runbook from §3.12.8, with the verification step.
4.7.7 `[BUILD]` `layer-secret-scan.sh` — `docker save` an image, walk every layer tar, and grep for
      high-entropy strings and known key formats, proving §1.6.5 and §2.6/§3.21.7.
4.7.8 `[BUILD]` The four incident runbooks matching §2.29.22, each as symptom → confirm → mitigate
      → root-cause → prevent, with the exact commands.
4.7.9 **Diff vs the real one**: what a platform tool (`k9s`, Robusta, a managed observability
      product) adds — event correlation, historical series, automatic enrichment, and the
      alerting integration that means nobody has to run the script.

*(9 leaves)*

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The question bank

Each question below must be answered in the bible with a **one-paragraph model answer plus the
follow-up the interviewer will actually ask**, and must reference the section that proves it.

5.1.1 Container fundamentals (24 questions): container vs image vs VM; which two kernel features
      make a container; name every namespace and what it scopes; what is *not* namespaced; why can
      two containers both bind 8080; why can you not run a Windows container on Linux; what
      exactly does `--privileged` turn off; namespaces vs cgroups in one sentence each; cgroup v1
      vs v2 and why the migration mattered; what does `cpu: 500m` mean at the kernel level; what
      does `memory: 1Gi` do on breach; what is a whiteout file; what does copy-up cost; why does
      deleting a file not shrink an image; what is the image ID vs the manifest digest; how many
      hashes are involved in one image and what does each name; what is an OCI bundle; what does
      `runc` do between `create` and `start`; why does a shim exist; what happened to dockershim;
      is Docker required to run Kubernetes; what is PID 1's special behaviour; why does shell-form
      `ENTRYPOINT` break deploys; what does `tini` do.
5.1.2 Image and build (18 questions): what invalidates a layer cache; why copy `pom.xml` before
      `src`; why must `apt-get update` and `install` share a `RUN`; what is in `docker history`
      that should not be; three ways to get a build secret in without leaking it; inline vs
      registry cache and `mode=min` vs `mode=max`; how do multi-platform images work; what is a
      manifest list; what does a multi-stage build actually remove; why is Alpine risky for a JVM;
      what does distroless cost you; what does `jlink` buy; what are Spring Boot layered jars for;
      how do you make a build reproducible; what does `--provenance` produce; how do you verify an
      image at admission; how do you find what bloated an image; how do you keep a pinned base
      image current.
5.1.3 Kubernetes objects and model (26 questions): what is a pod and why is it not a container;
      what does the pause container do; Deployment vs ReplicaSet vs Pod; Deployment vs
      StatefulSet vs DaemonSet; what does a Service actually create; ClusterIP vs NodePort vs
      LoadBalancer vs ExternalName vs headless; what is an EndpointSlice and why did it replace
      Endpoints; Ingress vs Gateway API and what happened to ingress-nginx; ConfigMap update
      propagation for env vars vs volumes vs subPath; why are Secrets not secret; what is a
      namespace *not* isolating; labels vs annotations; what is `ownerReferences` for; what is a
      finalizer and how does one wedge a namespace; what is `resourceVersion`; what is
      `observedGeneration` for; what does server-side apply change; what are the four patch types;
      what is a subresource and why does it matter for RBAC; level-triggered vs edge-triggered and
      why Kubernetes chose one; what does "applied successfully" actually guarantee; what runs when
      the control plane is down; what happens 5 minutes after a node dies; what is a static pod;
      what is an init container vs a sidecar now; what is an ephemeral container.
5.1.4 Probes, resources and lifecycle (22 questions): liveness vs readiness vs startup — who acts
      and how; why must dependency checks not be in liveness; what breaks if you put them in
      readiness; what are the probe defaults and what is wrong with `timeoutSeconds: 1`; how long
      until a dead container is detected; requests vs limits; what enforces each; what are the QoS
      classes and what do they decide; what is `oom_score_adj` per class; why set memory request ==
      limit; should you set a CPU limit — argue both sides; what is CFS throttling and how do you
      detect it; why does a throttled pod show low CPU utilisation; exit 137 vs
      `OutOfMemoryError` — which fix for which; what does `MaxRAMPercentage` default to; what does
      `availableProcessors()` return in a container and what depends on it; what did JDK 21 remove;
      what is in-place resize and what does it not fix for a JVM; what is the full termination
      sequence; why do deploys drop requests and how do you fix it; what does `preStop` buy;
      what does a PDB constrain and what does it not.
5.1.5 Networking (20 questions): the four rules of the Kubernetes network model; can you ping a
      ClusterIP and why not; what does kube-proxy do and is it in the data path; iptables vs IPVS
      vs nftables — status and scaling; why does a long-lived gRPC connection defeat Service load
      balancing; what is `ndots:5` and what does it cost; what is the JVM's DNS cache TTL; what
      produces exactly 5-second latencies; `externalTrafficPolicy: Cluster` vs `Local`; how do you
      preserve a client IP; how does a pod get an IP and who calls CNI; overlay vs routed vs
      ENI-based CNI; what limits pods per node on AWS; what is an MTU problem's signature; what
      does a NetworkPolicy default to when `policyTypes` is omitted; what is the one-dash
      selector trap; name three things NetworkPolicy cannot do; what happens to a NetworkPolicy
      with no enforcing CNI; what does a mesh add over NetworkPolicy; sidecar vs ambient.
5.1.6 Scheduling, autoscaling, capacity (18 questions): the two scheduling phases; taints vs
      tolerations vs affinity in one sentence each; why is required pod anti-affinity discouraged
      at scale; what is `topologySpreadConstraints` for; decode a `FailedScheduling` message; why
      can a 30%-utilised cluster be unschedulable; what is preemption and when does it not help;
      the HPA formula; what is the tolerance and the sync period; why is utilisation measured
      against requests; what are the default scale-up and scale-down behaviours; why can HPA not
      absorb a spike; what metric should scale an I/O-bound service; when does HPA make things
      worse; HPA vs VPA conflict; Cluster Autoscaler vs Karpenter; how do you make autoscaling
      fast enough for a campaign launch; what is node allocatable and how is it computed.
5.1.7 Storage and state (12 questions): PV vs PVC vs StorageClass; what does `ReadWriteOnce`
      actually restrict; `Retain` vs `Delete` and the accident each causes; what is
      `WaitForFirstConsumer` for; what happens to a StatefulSet's PVCs on scale-down; what is a
      Multi-Attach error and how long does it last; should you run your database in Kubernetes —
      argue it; what does an operator add over a StatefulSet; what is `subPath`'s update trap;
      what does `fsGroupChangePolicy: Always` cost on a large volume; what counts against
      `ephemeral-storage`; what does `emptyDir: medium: Memory` count against.
5.1.8 Security (16 questions): why is a container a weaker boundary than a VM; name three escape
      paths; what does `seccompProfile: RuntimeDefault` remove; what happened to
      PodSecurityPolicy; name five Restricted-profile requirements; what breaks in a Spring Boot
      image under Restricted; what does `automountServiceAccountToken: false` prevent; what can a
      ServiceAccount with `create pods` do; why is Docker socket access root; how do you encrypt
      Secrets at rest; ESO vs Secrets Store CSI — which and why; how does IRSA work; what is the
      admission-controller order and why does it matter; `ValidatingAdmissionPolicy` vs a webhook;
      what does a webhook with `failurePolicy: Fail` do when it is down; how do you enforce
      "only signed images from our registry".
5.1.9 Operations and debugging (20 questions): first three commands for a broken pod; how do you
      get the logs of a crashed container; distinguish `ImagePullBackOff` causes; how do you debug
      a distroless pod; how do you get a heap dump out of a pod; what is the fastest recovery
      action in an incident and what makes it possible; why is `:latest` un-rollbackable; how do
      you find what is actually running; how do you tell if a pod was OOMKilled after it
      restarted; what does `kubectl get events` not show you; where do container logs live and
      what rotates them; what is `PLEG is not healthy`; how do you diagnose a slow apiserver;
      what does an etcd space-exceeded alarm mean and how do you fix it; what is the etcd request
      size limit and what does it imply; how do you restore etcd and what does that lose; how do
      you upgrade a cluster without an outage; what is the version skew policy; what does a
      cluster upgrade break most often; what would you check first if p99 doubled with no code
      change.
5.1.10 Design and judgement (14 questions, `[STAFF]`-flavoured): ECS/Fargate vs EKS for this
       estate — decide and defend; would you run the ledger database in the cluster; how do you
       guarantee a payment run executes exactly once; how would you deploy a change that must take
       effect before the next stake (invariant 8); how do you deploy an agreement-version publish
       that invalidates every cached copy; how do you give the PSP a stable egress IP; how do you
       isolate card data; how many clusters and why; how do you do multi-region; what is your
       rollback story end to end; how do you right-size 25 services without guessing; how would you
       migrate 25 services from ECS to EKS; what is the first thing you would change about a
       cluster you inherited; what would you refuse to put in Kubernetes.
5.1.11 The whiteboard prompts: draw the path from `kubectl apply -f deployment.yaml` to a running
       process, naming every component; draw the packet path for one ClusterIP request; draw the
       termination sequence as a timeline with the concurrent branches; draw the cgroup tree for a
       Guaranteed pod; draw the layers of one image and what a `docker build` does to each.
5.1.12 The "explain it in one sentence" set, for fluency drilling: namespace, cgroup, layer,
       copy-up, digest, pod, Service, EndpointSlice, reconciliation, level triggering, QoS class,
       throttling, OOMKill, eviction, PDB, taint, readiness, `preStop`, HPA tolerance,
       `ndots`, CNI, CSI, CRI, finalizer, `resourceVersion`, server-side apply.

*(12 leaves — expanding to ~190 written questions)*

## §5.2 The trap index

Every `**Trap:**` in the bible, collected as a single scannable list so the reader can self-quiz.
The write pass must ensure each one exists inline *and* appears here.

5.2.1 Believing namespaces are a security boundary; believing cgroups provide isolation.
5.2.2 Thinking `cpu: 500m` means half a core continuously.
5.2.3 Believing `1G == 1Gi`.
5.2.4 Assuming a deleted file leaves the image; assuming `rm` after `COPY` removes a secret.
5.2.5 Believing `ARG` is discarded at build time.
5.2.6 Shell-form `ENTRYPOINT` and the un-forwarded SIGTERM.
5.2.7 Assuming PID 1 gets default signal handlers and reaps children.
5.2.8 Believing `EXPOSE` publishes a port.
5.2.9 Believing `-p 8080:8080` only binds locally.
5.2.10 Believing Docker `HEALTHCHECK` does anything in Kubernetes.
5.2.11 `depends_on` mistaken for readiness.
5.2.12 Deploying `:latest`; `imagePullPolicy: IfNotPresent` with a mutable tag.
5.2.13 Believing Kubernetes runs Docker.
5.2.14 Believing `kubectl apply` succeeding means the workload is running.
5.2.15 `kubectl edit` on a live object.
5.2.16 Dependency checks in a liveness probe (the fleet-wide restart storm).
5.2.17 Hard dependency checks in readiness (zero endpoints).
5.2.18 A huge `initialDelaySeconds` instead of a startup probe.
5.2.19 `timeoutSeconds: 1` against a JVM p99.
5.2.20 An authenticated or expensive probe endpoint.
5.2.21 `-Xmx` equal to the container memory limit.
5.2.22 Confusing exit 137 with `OutOfMemoryError`.
5.2.23 Trusting `availableProcessors()`-derived pool defaults in a container.
5.2.24 Reading CPU utilisation instead of throttling.
5.2.25 Using `container_memory_usage_bytes` instead of working set.
5.2.26 Setting a limit with no request (silently becoming Guaranteed with a huge request).
5.2.27 Believing a ResourceQuota does not change admission for existing manifests.
5.2.28 Believing endpoint removal happens before SIGTERM.
5.2.29 A grace period shorter than preStop plus drain.
5.2.30 Believing keep-alive connections respect endpoint changes.
5.2.31 `kubectl delete pod` ignoring PDBs.
5.2.32 A PDB that permanently blocks a drain.
5.2.33 `--force --grace-period=0` as a first response.
5.2.34 Believing HPA can absorb a spike; scaling on CPU for an I/O-bound service.
5.2.35 An HPA fighting a `replicas:` value in Git.
5.2.36 Believing more pods fixes a downstream bottleneck.
5.2.37 Believing `ReadWriteOnce` means one pod.
5.2.38 Deleting a PVC with `reclaimPolicy: Delete`.
5.2.39 A `configMap` mounted with `subPath` never updating.
5.2.40 Believing env-var config updates when the ConfigMap does.
5.2.41 Believing Secrets are encrypted.
5.2.42 Leaving `automountServiceAccountToken` on by default.
5.2.43 The NetworkPolicy one-dash AND/OR trap.
5.2.44 `policyTypes` omitted defaulting to Ingress only.
5.2.45 Forgetting to allow DNS in a default-deny policy.
5.2.46 A NetworkPolicy with no enforcing CNI silently doing nothing.
5.2.47 Believing a toleration causes placement.
5.2.48 Believing the scheduler finds the optimal node.
5.2.49 Believing usage, not requests, drives scheduling.
5.2.50 `ndots:5` and the six wasted DNS lookups.
5.2.51 The JVM's DNS cache outliving the pod IP.
5.2.52 `hostNetwork` without `ClusterFirstWithHostNet`.
5.2.53 Believing `Endpoints` is still the current API.
5.2.54 Naming ingress-nginx as a current, supported choice.
5.2.55 Believing `Terminating` and `CrashLoopBackOff` are pod phases.
5.2.56 Believing `kubectl get events` retains history.
5.2.57 Mounting the Docker socket.
5.2.58 A mutating/validating webhook that can wedge its own cluster.
5.2.59 Believing `overlay2` is still Docker's default image store on Engine 29.
5.2.60 Believing a CronJob gives you exactly-once execution.
5.2.61 A CronJob silently stopping after 100 missed schedules.
5.2.62 Believing `helm rollback` can undo a migration.
5.2.63 Believing in-place resize re-sizes the JVM heap.
5.2.64 `fsGroupChangePolicy: Always` on a large volume.
5.2.65 Believing a container escape is theoretical.

*(65 leaves)*

## §5.3 Drills and one-line assertions

5.3.1 **The numbers drill** — state from memory: probe defaults (0/10/1/1/3); restart backoff
      (100 ms → 300 s, reset at 10 min); default grace period (30 s); Deployment
      `maxSurge`/`maxUnavailable` (25%/25%); `progressDeadlineSeconds` (600);
      `revisionHistoryLimit` (10); `backoffLimit` (6); CronJob history (3/1) and the 100-missed
      rule; NodePort range (30000–32767); `sessionAffinity` timeout (10800 s);
      CFS period (100 ms) and slice (5 ms); default `maxPods` (110); eviction hard defaults
      (100Mi / 10% / 5% / 15% / 4%); `eviction-pressure-transition-period` (5 m);
      image GC (85/80, 2 m); HPA tolerance (0.1), sync (15 s), scale-down stabilisation (300 s);
      etcd request limit (1.5 MiB) and quota (2 GiB default, 8 GiB max);
      `MaxRAMPercentage` default (25); `oom_score_adj` (−997 / 1000);
      EndpointSlice size (100); `ndots` (5); JVM DNS TTL (30 s / 10 s);
      node lease (10 s / 40 s), monitor grace (50 s), `tolerationSeconds` (300 s);
      version skew (kubelet 3 minors, kubectl ±1); overlay2 lower-layer limit (128);
      `containerLogMaxSize`/`Files` (10Mi/5).
5.3.2 **The command drill** — produce from memory: the triage sequence; the three `kubectl debug`
      forms; the throttling metric read from `cpu.stat` inside a pod; the OOMKill evidence chain;
      `crictl` equivalents when `kubectl` fails; the `curl` sequence for a registry pull;
      `iptables-save`/`nft list`/`ipvsadm` for a ClusterIP; the etcd backup command.
5.3.3 **The recovery drill** — for each of the eight named failure modes, state symptom → confirm
      → mitigate → root-cause, out loud, in under 60 seconds.
5.3.4 **The reading drill** — given a `docker history` output, find the leaked secret; given a
      `describe pod`, name the cause; given a `describe node`, say whether a pod will schedule;
      given a `cpu.stat`, compute the throttled fraction; given an `iptables-save` fragment,
      trace a packet; given a `config.json`, list the container's privileges.
5.3.5 **The manifest drill** — write from memory, without reference: a Deployment with all three
      probes, correct resources, a Restricted `securityContext`, a `preStop` and a grace period; a
      Service; a PDB; an HPA with `behavior`; a default-deny NetworkPolicy plus a DNS allow.
5.3.6 **The explanation drill** — the whiteboard prompts from §5.1.11, timed.
5.3.7 **The Atomic concept checklist** — the write pass must carry every one of the current
      guide's **56 checklist lines** forward verbatim or expanded (never deleted), and extend it to
      cover every part of this syllabus. Downstream agents parse this section, so its flat
      one-bullet-per-concept shape is a contract.

*(7 leaves)*

---

## Sources consulted

Primary sources first. Where a fetch failed, returned only a summary, or a search returned nothing
usable, that is stated rather than padded. Every `[RESEARCH]` leaf must be re-verified against the
source named here before the write pass commits a number to the page. **Target versions for all
verification: Kubernetes v1.37 and Docker Engine 29.x.**

**Kubernetes official documentation (primary, fetched in full)**

- <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/> — source of §1.21.10–§1.21.14
  and §1.27.3: the five pod phases with the explicit note that `CrashLoopBackOff` and `Terminating`
  are **not** phases; the three container states and their `Waiting` reasons; the pod conditions
  `PodScheduled`/`ContainersReady`/`Initialized`/`Ready`; all three probe types with the exact
  defaults `initialDelaySeconds 0`, `timeoutSeconds 1`, `periodSeconds 10`, `successThreshold 1`,
  `failureThreshold 3`; the `exec`/`httpGet`/`tcpSocket` handlers; `restartPolicy`
  `Always`/`OnFailure`/`Never`; the **restart backoff of 100 ms → 300 s with a 10-minute reset**;
  the termination sequence and the 30-second default grace period; forced termination;
  readiness gates; scheduling gates; and the in-place-resize gate name.
- <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/> — source of
  §1.28: the four resource types (`cpu`, `memory`, `ephemeral-storage`, `hugepages-<size>`); CPU
  and memory unit semantics including the `M` vs `Mi` distinction; CPU limits enforced by
  throttling and memory limits by OOM kill with the explicit note that memory is *reactive* and a
  container may briefly exceed the limit; **pod-level `spec.resources` beta and enabled by default
  since v1.34 with the `PodLevelResources` gate, covering `cpu`/`memory`/`hugepages`**; hugepages
  being non-overcommittable; extended resources via device plugins; local ephemeral storage; the
  **"limit set with no request ⇒ request = limit"** defaulting rule; `LimitRange`/`ResourceQuota`;
  and the three QoS classes. The page confirms the target release as **1.37**.
- <https://kubernetes.io/docs/reference/networking/virtual-ips/> — source of §1.23, §2.1.9 and
  §3.16: the four kube-proxy modes with **iptables still the default in Kubernetes 1.37 and
  nftables named as the future default**; the iptables `minSyncPeriod 1s` / `syncPeriod 30s`
  defaults; the six IPVS scheduling algorithms `rr`/`lc`/`dh`/`sh`/`sed`/`nq`; random backend
  selection; `sessionAffinity: clientIP`; `internalTrafficPolicy` and `externalTrafficPolicy` with
  `Cluster` as both defaults; the **NodePort range 30000–32767**; traffic distribution and
  topology-aware routing; and the documented argument for proxying rather than DNS.
- <https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/> — source of
  §2.12.7–§2.12.12: the eight eviction signals with their formulas (including
  `memory.available` being computed from **workingSet**); the **hard defaults
  `memory.available<100Mi`, `nodefs.available<10%`, `nodefs.inodesFree<5%`,
  `imagefs.available<15%`, `pid.available<4%`**; soft thresholds and
  `eviction-max-pod-grace-period`; `eviction-minimum-reclaim`;
  `--eviction-pressure-transition-period` **5m**; the `MemoryPressure`/`DiskPressure`/`PIDPressure`
  conditions; the QoS-then-priority-then-overage victim ordering; reclaim-before-evict; and the
  **`oom_score_adj` values −997 / 1000 / the Burstable formula**. *Caveat for the write pass: the
  fetched summary listed "soft eviction defaults" of 80Mi/5%/10%/20% and an
  `--eviction-max-pod-grace-period` default of 30s. **The kubelet ships no default soft
  thresholds.** Do not write those numbers without re-reading the page.*
- <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/> — source of §2.13:
  the algorithm `ceil(currentReplicas × currentMetric/desiredMetric)`; the **0.1 tolerance**; the
  **15 s sync period**; the five metric types including `ContainerResource`; the `behavior` block
  with `scaleUp.stabilizationWindowSeconds 0` and `scaleDown.stabilizationWindowSeconds 300`, the
  100%-or-4-pods/15 s scale-up policies and `selectPolicy` `Max`/`Min`/`Disabled`; utilisation
  measured against **requests**; missing-metric and unready-pod handling; the readiness-delay and
  cpu-initialization-period flags; scale-to-zero; and which kinds have a `scale` subresource.
- <https://kubernetes.io/docs/concepts/security/pod-security-standards/> — source of §2.22.3–
  §2.22.4: the three profiles; every Baseline control with its exact field paths and allowed
  values, including the **13-capability allow-list**, the four permitted SELinux types (with
  `container_engine_t` noted as v1.31+), the safe `sysctl` list with its per-release additions
  (`net.ipv4.ip_local_reserved_ports` 1.27+, the three TCP options 1.29+), and the
  **probe/lifecycle-hook `host` field restriction added in v1.34**. *The Restricted section was
  truncated in the fetch; re-fetch it before writing §2.22.4's control list.*
- <https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/> — source of §2.18 and
  §3.19: A/AAAA and SRV record formats for normal and headless Services; pod records; the
  `hostname`/`subdomain` FQDN rule and its headless-Service prerequisite; `setHostnameAsFQDN`
  (stable v1.22) with the **64-character kernel hostname limit**; the four `dnsPolicy` values; the
  `dnsConfig` fields; the exact generated `resolv.conf` with **`options ndots:5`** and the three
  search domains; and `ExternalName` returning a CNAME.
- <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/> — source of §1.22.4 and
  §2.16: the identity guarantees; `apps.kubernetes.io/pod-index`; **`ordinals.start` stable in
  v1.31**; `volumeClaimTemplates`; `podManagementPolicy` `OrderedReady`(default)/`Parallel`;
  `updateStrategy` `RollingUpdate`(default)/`OnDelete`/**`Recreate`**; `partition` default 0 and
  `maxUnavailable` (v1.24+); `persistentVolumeClaimRetentionPolicy.whenDeleted`/`whenScaled` both
  defaulting to `Retain` (Delete available v1.27+); `minReadySeconds` 0;
  `revisionHistoryLimit` 10; reverse-ordinal scale-down; the forced-rollback procedure; and the
  documented limitations.
- <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/> — source of §1.22.3 and
  §2.10: `RollingUpdate`/`Recreate`; **`maxSurge` 25% rounded up and `maxUnavailable` 25% rounded
  down**; `minReadySeconds` 0; **`progressDeadlineSeconds` 600**; **`revisionHistoryLimit` 10**;
  rollback as a controlled scale of a previous ReplicaSet; pause/resume; proportional scaling; the
  `Progressing`/`Complete`/`Failed` conditions with `ProgressDeadlineExceeded`,
  `NewReplicaSetAvailable` and `FailedCreate`; the `kubernetes.io/change-cause` annotation; and
  **selector immutability**.
- <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/> — source of
  §3.14.2: all fifteen extension points in order (`PreEnqueue`, `EnqueueExtension`,
  **`QueueingHint` stable since v1.34**, `QueueSort`, `PreFilter`, `Filter`, `PostFilter`,
  `PreScore`, `Score` including **capacity scoring beta since v1.37**, `NormalizeScore`,
  `Reserve`/`Unreserve`, `Permit` with approve/deny/wait, `PreBind`, `Bind`, `PostBind`), the
  one-plugin-only constraints on `QueueSort` and `Bind`, and the serial-scheduling /
  concurrent-binding split.
- <https://kubernetes.io/docs/concepts/services-networking/network-policies/> — source of §2.22.12–
  §2.22.16: the ingress/egress isolation model with non-isolated-by-default semantics; the
  **`policyTypes` defaulting to `Ingress` when omitted**; `podSelector`/`namespaceSelector`/
  `ipBlock` with `except`; `ports` with `endPort` and TCP/UDP/**SCTP**; the additive OR semantics
  and the requirement that both sides allow; the five default-policy recipes; the
  `kubernetes.io/metadata.name` namespace-name idiom; the node-traffic always-allowed exception;
  the `hostNetwork` bypass; and the explicit **"what you can't do with network policies"** list.
- <https://kubernetes.io/docs/concepts/storage/persistent-volumes/> — source of §1.29: the PV
  phases; static vs dynamic provisioning and the `DefaultStorageClass` admission plugin; one-to-one
  binding via `claimRef`; `Retain`/`Delete`/`Recycle`(deprecated); the four access modes with
  short names **RWO/ROX/RWX/RWOP** and the node-not-pod semantics of RWO; `Filesystem` vs `Block`
  with `volumeDevices`; `volumeBindingMode` `Immediate` vs **`WaitForFirstConsumer`**; node
  affinity on a PV; mount options; snapshots, clones and `dataSource`;
  the **`kubernetes.io/pvc-protection`** finalizer; `allowVolumeExpansion` and
  `FileSystemResizePending`; `VolumeAttributesClass`; and the CSI positioning.
- <https://kubernetes.io/blog/2026/03/30/kubernetes-v1-36-sneak-peek/> — source of §1.31.4 and of
  version-trap 1: **user namespaces GA**, fine-grained kubelet API authorization GA, declarative
  validation GA, **PSI metrics GA**, volume group snapshots GA, mixed version proxy beta, in-place
  vertical scaling for pod-level resources beta, mutable pod resources for suspended jobs beta,
  pod-level resource managers alpha, memory-QoS/tiered-memory-protection alpha, **`externalIPs`
  deprecation**, and **ingress-nginx retired on 24 March 2026**.
- <https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/> — confirms the release date
  (26 Aug 2026), the name **Garhwal**, and the **67 enhancements (16 stable / 23 beta / 27 alpha /
  1 deprecation)** counts. **The page body was truncated in the fetch and did not yield the
  per-KEP list**; the write pass must fetch <https://kubernetes.io/releases/1.37/> and the linked
  per-feature blog posts (HPA scale-to-zero beta, etcd RangeStream, Storage Version Migration GA,
  PodCertificateRequest + ClusterTrustBundles, Metrics API GA) before writing §1.31.3.

**Kubernetes searches (secondary — every number below must be re-verified against a primary page)**

- Kubernetes 1.34 / 1.35 / 1.36 feature summaries — the source for §1.31.4–§1.31.6:
  1.34's 23-stable count, Job-controller terminating-pod accounting and CEL authorizer selectors;
  1.35's **KYAML beta**, relaxed Service name validation, PodCertificateRequest beta, structured
  auth config stable; 1.36's `gitRepo` removal, `externalIPs` deprecation, DRA partitionable
  devices, and **OCI artifacts/images as volume sources stable**. Search summaries only — no
  primary release-note page was fetched for 1.34 or 1.35.
- kube-proxy nftables status — the source for version-trap 4: nftables **alpha 1.29, beta 1.31,
  GA 1.33**; **IPVS deprecated in v1.35**; iptables still default in 1.37; **kernel 5.13+**
  required; KEP-3866 (nftables to GA) and **KEP-5343 (nftables to default)**. Re-verify against
  <https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/> and the KEP directory.
- In-place pod resize — the source for version-trap 5: **GA in v1.35 (19 Dec 2025)**, the
  `/resize` subresource accepting Update and Patch on
  `spec.containers[*].resources` / `spec.initContainers[*].resources` (sidecars only) /
  `spec.resizePolicy`, `resizePolicy` immutability, `NotRequired` for CPU vs `RestartContainer`
  for memory, and the `Deferred`/`Infeasible`/`InProgress` conditions. Primary source to re-fetch:
  KEP-1287 and <https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/>.
- Native sidecar containers — the source for version-trap 6: `initContainers` +
  `restartPolicy: Always`, gate default-on since **1.29**, **GA 1.33**, `Always` as the only legal
  value, and the Job-completion fix. Primary source to re-fetch: **KEP-753**.
- cgroup v1 maintenance mode — the source for version-trap 7: **maintenance mode in 1.31**
  (KEP-4569) with a kubelet start-up warning, **KEP-5573 "Remove cgroup v1 support"**, and the
  claim that **as of 1.35 the kubelet fails to start by default without cgroup v2**. That last
  claim came from a secondary summary and is the single highest-risk number in this file —
  **verify against KEP-5573 and the 1.35 release notes before writing §3.15.13.**
- Pod Security Admission / PodSecurityPolicy — PSP **deprecated 1.21, removed 1.25**; the
  three levels × three modes model; KEP-2579.
- ValidatingAdmissionPolicy / MutatingAdmissionPolicy — **VAP GA in 1.30**;
  **MutatingAdmissionPolicy requires 1.36+** (KEP-3962); and the admission order
  mutating webhooks → `ValidatingAdmissionPolicy` → validating webhooks. Re-verify against
  <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/>.
- Secrets encryption — **KMS v2 support from 1.29**, EKS 1.28+ using KMS v2 envelope encryption by
  default, and the External Secrets Operator / Secrets Store CSI Driver split. Primary sources to
  fetch for the write pass: the encrypt-data-at-rest task page and
  <https://secrets-store-csi-driver.sigs.k8s.io/introduction>.

**Docker / OCI / containerd / runc**

- <https://docs.docker.com/engine/release-notes/29/> (via search summary) — source of the Engine 29
  facts: the **containerd image store as the default on new installs with the classic graph drivers
  deprecated**, `mount type=image` no longer experimental, the `default-stop-timeout` daemon
  option, the `bind-create-src` mount option (29.3.0), CLI plugin error-hooks, the **experimental
  embedded containerd (29.7.0)**, and **CVE-2026-34040** (AuthZ plugin authorization bypass) and
  **CVE-2026-33997** (`docker plugin install` privilege validation) in 29.3.1. Only a search
  summary was obtained — **fetch the release-notes page directly before writing §1.31.12.**
- <https://docs.docker.com/engine/storage/drivers/overlayfs-driver/> — fetched in full. Source of
  §1.6 and §3.5: `lowerdir`/`upperdir`/`merged`/`workdir`; the `/var/lib/docker/overlay2/<id>/`
  layout with `diff/`, `link`, `lower`, `merged/`, `work/` and the `l/` symlink directory;
  read precedence; **whole-file copy-up**; whiteout files and opaque directories;
  **page-cache sharing**; the **128-lower-layer** support and lower inode consumption of
  `overlay2`; the kernel-4.0 / RHEL-3.10.0-514 floor and the XFS `d_type=true`/`ftype=1`
  requirement; the volume advice for write-heavy workloads; and the two documented **POSIX
  deviations** (the two-descriptor case and `rename(2)` returning `EXDEV`).
- <https://docs.docker.com/build/cache/optimize/> — fetched. Source of §1.8.6 and §2.4: layer
  ordering, `.dockerignore`, `--mount=type=bind`, `--mount=type=cache` with the per-language
  target paths (`/go/pkg/mod`, `/root/.cache/go-build`, `/var/cache/apt` + `/var/lib/apt` with
  `sharing=locked`, `/root/.cache/pip`, `/root/.gem`, `/app/target/`, `/root/.nuget/packages`,
  `/tmp/cache`), and `--cache-from`/`--cache-to type=registry,mode=max`.
- <https://docs.docker.com/build/cache/backends/> (via search) — source of §1.8.9: the exporters
  `inline` / `registry` / `local` / `gha` (and `s3`/`azblob`), **`inline` supporting `mode=min`
  only**, and `mode=max` exporting every intermediate stage. Re-verify the exporter list against
  the page.
- <https://github.com/opencontainers/image-spec/blob/main/manifest.md> — fetched. Source of §1.5.3:
  `schemaVersion` MUST be `2`; `mediaType`
  `application/vnd.oci.image.manifest.v1+json`; `config` pointing at
  `application/vnd.oci.image.config.v1+json`; the layer media types
  `…layer.v1.tar`, `…tar+gzip`, `…tar+zstd` (recommended) and the deprecated
  `…nondistributable.*`; `artifactType` being **required when `config.mediaType` is empty**;
  `subject`; and `annotations`.
- <https://opencontainers.org/posts/blog/2024-03-13-image-and-distribution-1-1/> and the
  image-spec `artifact.md` — source of §1.5.9: the `subject` and `artifactType` fields, the
  **`GET /v2/<name>/referrers/<digest>`** endpoint with `artifactType` filtering and pagination,
  and the RFC 6838 constraint on `artifactType`.
- <https://opencontainers.org/posts/blog/2025-11-04-oci-runtime-spec-v1-3/> (via search) — source
  of §3.9.9: **runtime-spec 1.3 released Nov 2025**, with 1.1 (Jul 2023) and 1.2 (Feb 2024) as the
  prior releases. Only the search result was seen; fetch the post before citing its contents.
- containerd release notes for 2.1 and 2.2, and <https://samuel.karp.dev/blog/2025/05/hello-containerd-2.1/>
  (via search) — source of §3.8.7: **NRI and CDI supported and enabled by default in 2.1**, CRI
  image pulls moving to the transfer service, **parallel HTTP range requests within a layer**,
  **OCI image volumes**, container restore through CRI, multiple CNI bin dirs, and the
  automatic-cgroup-driver-configuration support from containerd 2.0. Search summaries only.
- <https://github.com/opencontainers/runc/blob/main/CHANGELOG.md> (via search) — source of
  §3.9.8: runc 1.3 tracking runtime-spec 1.2.1, and **runc 1.4 changing `pids.limit = 0` to mean a
  real limit of zero** per updated OCI guidance. Search summary only — read the changelog entry
  before writing the leaf.
- <https://github.com/opencontainers/runc/blob/main/docs/cgroup-v2.md> and
  `docs/systemd.md` — named as the primary sources for §1.3.10 and §3.2.15 (the systemd vs
  cgroupfs driver). **Not fetched in this pass.**

**Gateway API and ingress**

- <https://kubernetes.io/blog/2026/04/21/gateway-api-v1-5/> and the v1.5.0 / v1.6.0 release
  discussions (via search) — source of §1.24.6–§1.24.10: v1.5 released **27 Feb 2026** promoting
  **`ListenerSet`, `TLSRoute`, the HTTPRoute CORS filter, client-certificate validation,
  certificate selection for Gateway TLS origination, and `ReferenceGrant`** to Standard; the new
  **release-train model**; v1.5.1 and v1.6.0 existing. **`BackendTLSPolicy` has been Standard
  since v1.4.0**, and `GRPCRoute` plus the mesh/GAMMA bindings went Standard in v1.1. The blog
  post itself was not fetched — do so before writing the promotion list.
- ingress-nginx retirement (multiple vendor write-ups plus the 1.36 sneak peek) — source of
  §1.24.4: **EOL 24 March 2026**, no features/bugfixes/CVE patches, existing deployments keep
  working, artefacts remain available, **`InGate` also retired**, Gateway API named as the
  successor, and **`ingress2gateway` 1.0 shipped March 2026**. The retirement date is corroborated
  by the Kubernetes blog; the `ingress2gateway` 1.0 date is from secondary sources only.
  The `kubernetes-retired/ingate` repository is the primary evidence for InGate's retirement.

**JVM in containers**

- <https://developers.redhat.com/articles/2022/04/19/java-17-whats-new-openjdks-container-awareness>,
  <https://bugs.openjdk.org/browse/JDK-8196595>, <https://bugs.openjdk.org/browse/JDK-8189497> and
  the AWS containers blog (via search) — source of §2.8: `-XX:+UseContainerSupport` on by default;
  `MaxHeapSize = MaxRAMPercentage × MEMORY_LIMIT` with **`MaxRAMPercentage` defaulting to 25**;
  cgroup v1 and v2 detection handled entirely in the JDK from 17+ and 11u;
  `-XX:ActiveProcessorCount` as the override; and **`-XX:+UseContainerCpuShares` removed in
  JDK 21**. The JDK-21 removal is the highest-value version fact here and should be confirmed
  against the JDK 21 release notes, not the blog.
- <https://developers.redhat.com/articles/2025/11/27/how-does-cgroups-v2-impact-java-net-and-nodejs-openshift-4>
  — named as the source for the cgroup-v2-specific JVM behaviour. **Not fetched.**

**CFS throttling evidence**

- <https://github.com/kubernetes/kubernetes/issues/67577> ("CFS quotas can lead to unnecessary
  throttling"), issue #51135, <https://github.com/coreos/bugs/issues/2623> (a **50% throughput
  loss in production, containers requesting 6 cores throttled to 3**), and
  <https://engineering.omio.com/cpu-limits-and-aggressive-throttling-in-kubernetes-c5b20bd8a718>
  — the evidence base for §2.8.11–§2.8.13 and §3.3. These are **issue threads and a company blog,
  not measurements this file made**: the write pass must attribute them, not assert them. The
  kernel-side per-CPU slice-expiry fix must be verified before it is described as fixed.
- <https://k8s.af/> (Kubernetes Failure Stories) — the catalogue of public postmortems to mine for
  §2.29.22's worked incidents. Not individually fetched.

**Helm, Karpenter, Istio, autoscaling ecosystem (search summaries only)**

- <https://helm.sh/blog/helm-4-released/> and the migration write-ups — source of §2.24.5:
  **server-side apply as the default for new releases** (Helm 3 releases staying client-side after
  upgrade), conflicts becoming explicit errors, **`--wait` using kstatus and therefore needing the
  `watch` verb**, post-renderers becoming plugins, and the WASM-capable plugin system. Fetch the
  official blog post and the migration guide before writing this section.
- <https://karpenter.sh/docs/concepts/disruption/> (via search) — source of §2.15.5–§2.15.7:
  `NodePool` + `NodeClass` + `NodeClaim`, `consolidationPolicy`, and the **default single
  disruption budget of 10%**. The **45–60 s Karpenter vs 3–4 min Cluster Autoscaler**
  provisioning figures come from vendor comparison blogs and must be attributed, not asserted.
- Istio ambient mode — **GA in Istio 1.24 on 7 Nov 2024** with ztunnel, waypoints and the related
  APIs marked Stable; one ztunnel per node and a recommended minimum of one waypoint per
  namespace; ambient multicluster alpha in Istio 1.27 (Aug 2025). Search summaries only; fetch
  istio.io before writing §2.27.3.
- CKA/CKAD/CKS curricula (via search) — used purely as a **completeness checklist** against which
  the syllabus was diffed. CKA domains: Cluster Architecture/Installation/Configuration 25%,
  Workloads & Scheduling 15%, Storage 10%, Services & Networking 20%, **Troubleshooting 30%** —
  the troubleshooting weight is why §2.29 is the largest section in PART 2. CKAD domains:
  Application Design & Build 20%, Deployment 20%, Observability & Maintenance 15%, Environment/
  Configuration/Security 25%, Services & Networking 20%. The published domain percentages should
  be re-checked against training.linuxfoundation.org before being quoted.

**Searches that produced nothing usable**

- No authoritative, current, per-operation **cost/latency table** for container and Kubernetes
  operations exists. §2.1.1 and §2.1.2 must therefore be presented as **derived from the
  mechanism, with the derivation shown**, or as clearly attributed measurements — never as quoted
  authority.
- No primary source was found for a consolidated list of "the QuizStakes-shaped" numbers, which is
  correct: those come from `src/scenario/scenario.md` Appendices A and B and must be taken from
  there verbatim.
- Interview-question searches returned only aggregator listicles. §5.1's bank was constructed from
  the mechanism inventory in PARTS 1–3 and cross-checked against the CKA/CKAD domain weights,
  not copied from any list.

**Sibling files read for scope boundaries**

- `src/topics/00-index.md` — the declared scope line for guide 19 and the sibling ownership map.
- `src/topics/19-docker-kubernetes.md` — the current guide, read in full; every concept in it is a
  leaf in this syllabus and appears in the gap table below.
- `src/syllabus/17-git-craft.md` — the structural and tagging convention this file follows,
  including its explicit parking of "container images, layer caching, CI runners and build
  reproducibility" in guide 19.
- `src/syllabus/15-caching.md` — its `[X-REF 19]` line confirms that probes, rolling updates,
  `terminationGracePeriodSeconds`, HPA and `CrashLoopBackOff` debugging are **owned here**.
- `src/scenario/scenario.md` §6.4, §15, Appendix A.6, A.7 and Appendix B.1–B.5 — the deployment
  shapes, heap sizes, instance counts, latency budgets, compute/storage/messaging mapping, the
  drain-before-terminate deployment policy, the scheduler-plus-leader-election rule, and the
  "what does not map cleanly" list.

---

## Gaps vs the current guide

`src/topics/19-docker-kubernetes.md` is **706 lines** across 13 sections plus a 56-item checklist.
It is a genuinely good practitioner's guide: its namespaces/cgroups framing, its build-cache
ordering fix, its Dockerfile checklist, its probe table with the dependency-storm trap, its
requests/limits asymmetry table, its JVM interplay section, and its termination-race treatment are
all strong and must survive **verbatim or expanded**. It is not a bible: it contains **no OCI
specs, no image/layer internals, no BuildKit beyond one paragraph, no registry protocol, no
containerd/runc/CRI, no control-plane architecture, no etcd, no scheduler, no kubelet, no
kube-proxy datapath, no CNI/CSI, no DNS, no RBAC, no Pod Security Standards, no NetworkPolicy, no
StatefulSet/Job/CronJob depth, no storage, no Helm/Kustomize, no GitOps, no CRDs/operators, no
service mesh, no version history, and no build-it content at all**. The table below is the work
order.

| Syllabus area | Present in `src/topics/19-docker-kubernetes.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why containers exist, the decisions, the vocabulary | §1 ("what containers actually give you" — reproducible artefact, not efficiency) | ✅ the origin story, the prior answers, the OCI standardisation, the cost of the decisions, the vocabulary table | ✅ **the "reproducible artefact, not efficiency" paragraph must survive verbatim** |
| §1.2 namespaces, all eight | §1 (a one-line list of seven, no flags) | ✅ the `clone` flags, what is *not* namespaced, lifetime, `setns`/`nsenter`, shared namespaces as the pod's basis, `hostUsers` | ✅ the port-space and PID-1 consequences are right and must be kept and proved |
| §1.3 cgroups v1 vs v2, every interface file | §1 (one line: "limits on what you can use: CPU, memory, block I/O, PIDs") | ✅ everything — v2 unified hierarchy, every file and default, the v1→v2 name map, `memory.high` vs `max`, weight vs quota, the cgroup driver, the node cgroup tree, allocatable arithmetic, PSI | ✅ severely |
| §1.4 capabilities, seccomp, LSMs, masked paths, rlimits | §1/§3 (`--privileged` and the Docker socket named as "serious") | ✅ the full capability set, seccomp profiles, AppArmor/SELinux fields, `no_new_privs`, masked/readonly paths, `oom_score_adj`, read-only rootfs, CDI/NRI, gVisor/Kata/`RuntimeClass` | ✅ the `--privileged` warning must be kept and decoded precisely |
| §1.5 the OCI image model | §1 ("an immutable, layered filesystem plus metadata") | ✅ the entire spec — descriptors, manifest fields and media types, the index, the config, the four digests, whiteouts in the tar, `subject`/`artifactType`/Referrers, annotations, OCI volumes, the bundle | ✅ severely |
| §1.6 layers, union FS, the writable layer | §2 (layers are content-addressed diffs, shared bases, additive deletion) | ✅ copy-up cost, page-cache sharing, the layer limit, the storage-driver inventory, **the Engine 29 containerd-image-store default**, lazy pulling, the size-forensics commands | ✅ **the "deleting a file doesn't shrink the image / the secret is still there" paragraph must survive verbatim** |
| §1.7 the Dockerfile instruction set | §3 (a production example using ~12 instructions) | ✅ the other eight instructions, every `RUN --mount` type, `COPY`'s full flag set, `ADD` vs `COPY`, the `ENTRYPOINT`/`CMD` 3×3 table, `HEALTHCHECK` defaults, `STOPSIGNAL`, `SHELL`, `ONBUILD`, heredocs, build checks, which instructions make layers | ✅ the example is excellent and is the spine of the section |
| §1.8 BuildKit, LLB, the cache | §2 (the cache rule, the ordering fix, the `apt-get` rule, one paragraph on BuildKit) | ✅ LLB and the DAG, the precise cache-key rule, every cache exporter and `mode=min`/`max`, buildx builders and drivers, multi-platform, `bake`, output types, provenance/SBOM, reproducibility, Jib/buildpacks/Kaniko/ko, **Spring Boot layered jars**, AppCDS | ✅ **the BAD/GOOD Dockerfile pair and the cache rule must survive verbatim — they are the single highest-leverage thing in the guide** |
| §1.9 multi-stage and the JVM runtime image | §3 (multi-stage build/runtime example, "ship a JRE not a JDK", the 800→200 MB figure, jlink and distroless mentioned) | ✅ the base-image comparison table, the Alpine/musl argument, distroless debugging, the `jlink`/`jdeps` walk-through, the GraalVM comparison, ordering constraints | ✅ **the 800→200 MB claim and the attack-surface argument must be kept and quantified** |
| §1.10 the Docker CLI surface | §4 (~18 commands, `exec` vs `run`, `-p` semantics, volumes) | ✅ the full `run` flag inventory, `docker diff`, `docker events`, log drivers and rotation, `stop` timeout numbers, `commit`/`save`/`export` distinctions, `context`/`DOCKER_HOST`, `docker info` reading, **the API socket as root**, `nerdctl`/`ctr`/`crictl`/`podman` | ✅ **the `exec` vs `run` and `host:container` clarifications must survive verbatim** |
| §1.11 lifecycle, PID 1, signals | §3 (exec vs shell form, SIGTERM not forwarded, `--init`/tini, PID 1 zombies) | ✅ the state machine, the exit-code table, the restart-backoff numbers, `postStart`/`preStop` handlers, container-level `restartPolicy`, Docker health states | ✅ **the exec-form trap is one of the guide's best paragraphs and must survive verbatim** |
| §1.12 volumes, bind mounts, tmpfs | §4 (three lines: bind vs named volume, writable layer is ephemeral) | ✅ `--mount` syntax, propagation, SELinux relabelling, the UID-mismatch problem, Docker Desktop I/O, **the full Kubernetes volume-type inventory**, `subPath`'s update trap, `emptyDir` sizing | ✅ |
| §1.13 Docker networking | §4 (`-p host:container` and the port-namespace explanation) | ✅ entire section — bridge/veth/NAT, embedded DNS, host/none/overlay/macvlan, the `DOCKER-USER` chain and the `PREROUTING` bypass, the bind-mounted `/etc` files, MTU | ✅ |
| §1.14 registries, references, tags, digests | §6 (registries named, login, tagging strategy, the `:latest` trap, rollback by tag, digests) | ✅ the reference grammar and its defaults, the pull/push verbs, the token handshake, `imagePullSecrets` and node credential providers, **the `imagePullPolicy` implicit default rule**, image GC thresholds, mirrors | ✅ **§6's tagging strategy, the `:latest` trap and "rollback by tag is the fastest recovery action" must survive verbatim** |
| §1.15 Compose | §5 (a good example, DNS names, the `depends_on` trap, volumes, "not for production") | ✅ the Compose Specification and the v1-is-dead fact, the full service-key inventory, `condition: service_completed_successfully`, interpolation precedence, multi-file merge and profiles, the full command surface, **`docker compose watch`**, `up --wait` in CI | ✅ **the `depends_on`-is-not-readiness trap must survive verbatim** |
| §1.16 the runtime stack and CRI | — | ✅ entire section — dockerd→containerd→shim→runc, why the shim exists, the three OCI specs, **CRI**, **dockershim's removal**, alternative runtimes, `crictl`/`ctr` | ✅ **and this is a top-three gap: the guide never says Kubernetes does not run Docker** |
| §1.17 why Kubernetes exists, the design decisions | §7 (the declarative model paragraph) | ✅ the Borg lineage, level-triggering as the central decision, the uniform-API decision, labels-over-names, pod-as-unit, the flat network, and what it all costs | ✅ **the declarative-model paragraph and the `kubectl edit` trap must survive verbatim** |
| §1.18 the architecture | §7 (a Node row in the object table) | ✅ entire section — every control-plane and node component, the controller inventory, "only the apiserver talks to etcd", what survives a control-plane outage, HA and quorum, managed control planes and their cost, static pods, the node-death timeline | |
| §1.19 the API: groups, versions, the object envelope | — | ✅ entire section — URL shapes, the group inventory, the stability ladder, `metadata` field by field, `resourceVersion`, `generation`/`observedGeneration`, owner refs and cascade, finalizers, **server-side apply**, the four patch types, subresources, watch semantics, APF, events and their 1-hour TTL, the size limits | |
| §1.20 reconciliation | §7 (a strong paragraph) | ✅ idempotence, level-vs-edge proved, the conditions vocabulary, the eventual-consistency chain, where the model leaks | ✅ **the paragraph and its `kubectl edit` conclusion must be preserved and expanded** |
| §1.21 the pod | §7 (one table row) | ✅ the pause container, the full container-field inventory, `command`/`args` vs `ENTRYPOINT`/`CMD`, init containers, **native sidecars**, ephemeral containers, phases vs kubectl statuses, every container-state reason, pod conditions, readiness and scheduling gates, `enableServiceLinks`, the **Downward API**, `terminationMessagePolicy` | ✅ **"pods are ephemeral and disposable" must survive verbatim** |
| §1.22 the workload controllers | §7 (six table rows) | ✅ every field and default, the pod-template-hash mechanism, `ControllerRevision`, the `scale` subresource, the 1.34 Job changes, the 1.37 StatefulSet `Recreate`, **the CronJob 100-missed rule**, the which-controller-for-which-service mapping, Argo Rollouts/Kueue | ✅ the six rows are accurate and are the section's skeleton |
| §1.23 Services and EndpointSlices | §7 (one table row + the service-discovery paragraph) | ✅ the ClusterIP-is-not-real proof, every spec field and default, headless Services, **EndpointSlice and why it replaced Endpoints**, `ready`/`serving`/`terminating`, traffic policies, topology-aware routing, `trafficDistribution`, dual-stack, the rule-count arithmetic | ✅ **the service-discovery DNS paragraph must survive verbatim** |
| §1.24 Ingress and Gateway API | §7 (one table row, "Gateway API is its successor" in parentheses) | ✅ entire section — the Ingress field surface, the annotation problem, **the ingress-nginx retirement**, the controller options, the Gateway API three-persona model, `HTTPRoute` filters and weights, the policy objects, GAMMA, channels, `ingress2gateway`, the QuizStakes entry design | ✅ **severely, and this is the most version-stale line in the current guide** |
| §1.25 ConfigMap, Secret, injection | §7 (two table rows, including the base64 warning) | ✅ **the update-propagation table (env vs volume vs subPath)**, `immutable`, the checksum-annotation fix, the Secret type inventory, files vs env vars, projected volumes, the Spring Boot binding | ✅ **the "Secrets are base64, not encrypted" warning must survive verbatim** |
| §1.26 namespaces, labels, annotations | §7 (one table row) | ✅ what a namespace does and does not partition, the default namespaces, the `Terminating` wedge, namespace strategy, the recommended label set, the auto-applied labels, field selectors | ✅ |
| §1.27 probes | §8 (the actor table, the readiness/liveness argument, **the dependency-storm trap**, the YAML, Spring Boot support, the readiness caveat, four other mistakes) | ✅ the `grpc` handler, every default value, the detection-time arithmetic, the `timeoutSeconds: 1` problem, the `client-restrictions` case, health-group composition, the PID cost of `exec` probes, sidecar probes | ✅ **§8 is the guide's best section. The actor table, the dependency-storm trap, the "liveness checks only what a restart can fix" rule, the readiness caveat with hard-vs-soft dependencies, and all four probe mistakes must survive verbatim.** |
| §1.28 requests, limits, QoS | §9 (the YAML, the requests/limits distinction, **the CPU/memory asymmetry table**, the Guaranteed-QoS advice, the CPU-limits argument) | ✅ the unit semantics and `1G ≠ 1Gi`, the three QoS classes defined precisely and what they decide, the limit-with-no-request rule, DRA, `ephemeral-storage`, hugepages, **pod-level resources**, **in-place resize**, `LimitRange`/`ResourceQuota`, working-set vs usage, the right-sizing procedure | ✅ **the asymmetry table, "memory is incompressible; CPU is compressible", and the whole CPU-limits argument must survive verbatim** |
| §1.29 storage | §7 (one table row: "PVC/PV — persistent storage claims and volumes") | ✅ entire section — the three-object model, phases, access modes and the RWO-means-node correction, reclaim policies, `WaitForFirstConsumer`, volume modes, expansion, StorageClass fields, PVC protection, snapshots/clones, ephemeral volumes, local PVs, StatefulSet PVCs, the database-in-Kubernetes decision | ✅ severely |
| §1.30 kubectl | §12 (a well-chosen ~25-command set, the `describe`-events instruction, the context warning) | ✅ kubeconfig structure, `-o jsonpath` recipes, **KYAML**, `kubectl events`, `kubectl debug`'s three modes, `diff` and `--dry-run=server`, `auth can-i`, `explain`, `wait`, `--raw`, plugins/krew, `-v=8` | ✅ **§12's command set, the "describe pod is the first command" instruction and the wrong-context warning must survive verbatim** |
| §1.31 versions and release cadence | §9 (one parenthetical: "modern JVMs 8u191+, 11+"), §2 ("default in recent Docker") | ✅ entire section — the cadence and support window, what each of 1.33–1.37 shipped, the older boundaries, **the version-skew policy**, the upgrade procedure, feature gates, Docker Engine's deltas and CVEs | ✅ **and this is the highest-value single addition, because most of this topic's folklore is version-stale** |
| §2.1 the master tables | §1 (the container-vs-VM table), §9 (the CPU/memory table) | ✅ twelve of the fourteen tables, including the master cost table, the failure-mode table, the enforcement table, the memory-footprint arithmetic and the rollout-parameter table | ✅ the two existing tables are good and must be absorbed, not replaced |
| §2.2 Dockerfile craft as a decision list | §3 (a 13-item checklist — the guide's second-best content) | ✅ digest pinning as a maintained practice, the extra rules (`ExitOnOutOfMemoryError`, stable jar path, no curl in the runtime image), the anti-pattern list, hadolint/build checks | ✅ **every one of the 13 checklist items must survive verbatim and be expanded into a mechanism** |
| §2.3 image size, base images, CVE budget | §3 (the last checklist item, plus the Alpine/musl warning) | ✅ the byte-by-byte breakdown, the operational and security quantification, the four levers ranked, hardened base images, reading a scan report, the scheduled-rebuild practice | ✅ **the Alpine/musl warning must survive verbatim** |
| §2.4 the build in CI | §2 (BuildKit cache mounts mentioned) | ✅ entire section — why CI is slow, the cache-strategy matrix, cache poisoning, the bake pipeline, tag/label generation, OIDC for registry auth, test-in-build vs Testcontainers with the DinD caveat, multi-arch in CI, **build-once-promote-by-digest**, Kaniko | ✅ severely |
| §2.5 supply chain: signing, SBOM, provenance, admission | §3 (one checklist item: "scan images in CI and fail on critical CVEs") | ✅ entire section — the threat model, cosign/Sigstore/Rekor, SBOM formats, SLSA provenance, admission-time verification, registry controls, the QuizStakes policy | ✅ **the scanning item must be kept as the entry point** |
| §2.6 container security posture | §1 (the shared-kernel/escape paragraph, Firecracker, `--privileged`, the Docker socket) | ✅ the escape-path inventory, the named CVEs, the ordered hardening set, `automountServiceAccountToken: false`, runtime detection, the QuizStakes card-data and PII requirements, what the boundary does not solve | ✅ **the shared-kernel-escape paragraph and the Firecracker/multi-tenancy point must survive verbatim** |
| §2.7 rootless, Docker Desktop, dev environments | §1 (one clause: "which is exactly what Docker Desktop on macOS/Windows does, and why file I/O across the bind mount is slow there") | ✅ entire section — rootless mechanics, Podman, the Desktop alternatives, local Kubernetes options, the inner-loop tools, dev containers, the QuizStakes local story | ✅ **the Docker-Desktop-is-a-VM clause is correct and must be kept and explained** |
| §2.8 the JVM in a container | §1 (the historical host-memory bug), §9 (the JVM interplay: RSS composition, `MaxRAMPercentage`, **the 137-vs-OOME distinction**, `availableProcessors()`, **CFS throttling**) | ✅ the exact cgroup files the JVM reads, the `MaxRAMPercentage` default of 25, `MinRAMPercentage`'s 96 MB rule, the full RSS arithmetic worked, the other three OOM classes, **the JDK 21 flag removal**, the throttling fixes ranked, GC selection, start-up levers, the two worked service sizings, heap dumps and live diagnostics | ✅ **§9 is the guide's third-best section. The RSS composition, the WRONG/RIGHT `-Xmx` pair, the exit-137-vs-`OutOfMemoryError` paragraph, the `availableProcessors()` warning and the entire CFS-throttling paragraph including `container_cpu_cfs_throttled_seconds_total` must survive verbatim.** |
| §2.9 scheduling | §12 (one clause: `FailedScheduling` = "insufficient CPU/memory requests available, or a taint/affinity mismatch") | ✅ entire section — filtering and scoring, `nodeSelector` vs affinity, taints/tolerations with the built-in taint list, the repel/permit/attract model, anti-affinity's cost, `topologySpreadConstraints`, the QuizStakes placement manifests, PriorityClass and preemption, message decoding, **requests-not-usage**, the descheduler | ✅ severely — the one clause is right and is the seed |
| §2.10 rollouts and rollbacks | §10 (the strategy YAML, `maxUnavailable: 0` reasoning, readiness-makes-it-safe, `rollout status`/`undo`) | ✅ the parameter arithmetic, `minReadySeconds`/`progressDeadlineSeconds`, what a rollback *is*, `rollout restart`, `Recreate`'s two uses, proportional scaling, blue-green/canary/shadow/flags, analysis gating, **the two-versions-at-once compatibility constraint**, the rollouts that must not be rolling, StatefulSet and DaemonSet rollouts | ✅ **the strategy block, the `maxUnavailable: 0` argument and "readiness probes are what make a rolling update safe" must survive verbatim** |
| §2.11 graceful shutdown | §10 (**the concurrency race**, the `preStop` fix, the Spring properties, the 6-step sequence, the grace-period arithmetic, PDBs) | ✅ the propagation-latency quantification, readiness gates, the `bank-withdrawal` case, what Spring actually does, the shutdown work nobody does (metric/log flush, offset commit, lock release), **keep-alive defeating endpoint changes**, `--force --grace-period=0`, sidecar ordering, node shutdown, the zero-error test | ✅ **§10's termination-race trap, the full fix chain, the 6-step recite-able sequence and the grace-period warning must survive verbatim — this is the guide's second-best section** |
| §2.12 disruption: PDBs, drains, eviction, preemption | §10 (a `PodDisruptionBudget` paragraph) | ✅ voluntary vs involuntary, every PDB field, **the Eviction API vs `delete` distinction**, the blocked-drain failure, the QuizStakes PDB set, drain flags, **every eviction signal and default threshold**, node conditions, victim ordering, eviction-vs-OOMKill, reclaim-before-evict, spot handling, the upgrade exercise | ✅ **the PDB paragraph must be kept and expanded** |
| §2.13 HPA | §11 (the v2 YAML, utilisation-against-requests, metric choice, stabilisation, KEDA, the database-bottleneck warning, Cluster Autoscaler/Karpenter) | ✅ the algorithm and tolerance, the sync period and pipeline lag, all five metric types, **the exact `behavior` defaults**, scale-to-zero, multi-metric maximum semantics, missing-metric handling, KEDA's object model, the HPA-vs-Git-replicas conflict, flapping, reading `describe hpa` | ✅ **§11's "utilisation is measured against requests", the metric-choice advice with consumer lag, and the "scaling doesn't help if the bottleneck is the database" warning must survive verbatim** |
| §2.14 VPA and in-place resize | — | ✅ entire section — VPA components and modes, `updateMode: Off` as the useful one, the HPA/VPA conflict, in-place resize mechanics, **the JVM heap-not-resized consequence**, the right-sizing tools, the estate-wide exercise | |
| §2.15 node autoscaling | §11 (two sentences: Cluster Autoscaler/Karpenter add nodes; HPA without them leaves pods `Pending`) | ✅ Cluster Autoscaler's parameters and latency, node-group homogeneity, **Karpenter v1's object model, consolidation and disruption budgets**, the consolidation prerequisite, spot handling, the comparison table, overprovisioning, Autopilot/Fargate, the end-to-end latency chain | ✅ **the "HPA without node autoscaling leaves pods Pending" sentence must survive verbatim** |
| §2.16 StatefulSets in practice | §7 (one table row) | ✅ entire section — what it guarantees and does not, the headless requirement, `Parallel`, the `OrderedReady` stall and its recovery, `partition` canaries, the PVC-retention dilemma, `Recreate`, **the `FundsLedger` partition-affinity and rebalancing discussion**, operators, and the keep-the-database-outside decision | ✅ |
| §2.17 Jobs, CronJobs, batch | §7 (one table row, "at-least-once") | ✅ entire section — completion models and `Indexed`, `backoffLimit`/`podFailurePolicy`/deadlines/TTL, `suspend` and Kueue, the 1.34 accounting change, **sidecars-and-Jobs**, every CronJob default, **the 100-missed-schedules rule**, the double-payout proof, the `bank-deposits` design, migrations, batch observability | ✅ **the "at-least-once" note must survive verbatim and become the section's thesis** |
| §2.18 DNS | §7 (the FQDN example) | ✅ entire section — the record contract, the exact `resolv.conf`, **the `ndots:5` proof with the six wasted lookups**, the three fixes, `dnsPolicy` values, `dnsConfig` limits, **the JVM DNS cache TTLs**, NodeLocal DNSCache, the 5-second conntrack race, CoreDNS configuration and sizing, split-horizon, the debugging commands | ✅ **the `payments.billing.svc.cluster.local` example must be kept and re-domained** |
| §2.19 service networking decisions | §7 (the ClusterIP-indirection paragraph) | ✅ entire section — the exposure decision list, why NodePort rarely, the LB cost arithmetic, cross-AZ cost, **long-lived-connection load-balancing failure**, pool staleness, client-IP preservation, **egress and the stable-source-IP requirement**, `hostNetwork`, IP exhaustion, conntrack limits | ✅ |
| §2.20 RBAC and workload identity | §7 (one clause: "restrict RBAC"), §7 Secret row | ✅ entire section — the four objects and the fifth combination, rule shape and allow-only semantics, subjects and built-in groups, the default ClusterRoles, aggregation, escalation prevention, authn mechanisms, **bound service account tokens**, IRSA/Pod Identity, the per-workload RBAC set, auditing, the escalation paths | |
| §2.21 secrets in practice | §7 (encryption at rest, External Secrets and Secrets Store CSI named in one line) | ✅ `EncryptionConfiguration` and KMS v2, the three architectures compared, why files beat env vars, **rotation requiring the app to notice**, Sealed Secrets/SOPS, the leak checklist, the QuizStakes secret inventory, auditing | ✅ **the one-line mention of External Secrets/CSI is correct and is the seed for the section** |
| §2.22 PSS, security contexts, network policy | — | ✅ entire section — Pod Security Admission and the label scheme, the three modes and the rollout order, **every Baseline and Restricted control with field paths**, what Restricted breaks for Spring Boot, pod- vs container-level `securityContext`, `fsGroupChangePolicy`, `ValidatingAdmissionPolicy` vs policy engines, **the admission order**, webhook hazards, **the whole of NetworkPolicy including the one-dash trap and the DNS omission**, CNI extensions, the QuizStakes policy set, testing denials | ✅ **and this is a top-three gap: the index scope line promises "Secret" and security-adjacent content and the guide delivers one warning** |
| §2.23 multi-tenancy and hygiene | §7 (one clause: namespaces are "a logical partition for names, RBAC, and resource quotas") | ✅ entire section — `ResourceQuota` and its admission trap, `LimitRange`, the tenancy models compared with cost, node pools as the real boundary, the automated hygiene checks | ✅ |
| §2.24 Helm, Kustomize, the templating decision | §13 (Helm named in the ecosystem row) | ✅ entire section — chart anatomy, the templating surface, the release/revision model, **Helm 4's SSA default and its consequences**, the command surface, hooks, the Helm failure modes, all of Kustomize including the **ConfigMap name-hash**, the argued decision, the QuizStakes layout | |
| §2.25 GitOps and delivery | §6 (implicitly, via "the next `apply` from Git overwrites it") | ✅ entire section — Argo CD and Flux object models, the image-update loop, repository topology, **the `selfHeal`-vs-hotfix break-glass problem**, secrets, progressive delivery, drift as a signal, the end-to-end pipeline | ✅ the "next apply from Git overwrites it" observation is the seed and must be kept |
| §2.26 CRDs and operators | §13 (operators named in the ecosystem row) | ✅ entire section — CRD anatomy, structural schemas and **CEL validation**, conversion and storage-version migration, the operator pattern and capability levels, the controller-runtime concepts, idempotence, **the Java Operator SDK**, when an operator is right, the operators you meet, the CRD hazards, the `PaymentRun` design | |
| §2.27 service mesh | §13 (Istio named in the ecosystem row) | ✅ entire section — what a mesh provides, the sidecar cost, **ambient mode**, the options compared, GAMMA, L7 authorization policy as what NetworkPolicy cannot do, mTLS options, double-retry amplification, the honest decision rule, debugging | |
| §2.28 observability | §3/§12 (log to stdout; `kubectl top` needs metrics-server) | ✅ entire section — cAdvisor and the kubelet endpoints, the container metrics with good/bad values, **the working-set-vs-usage trap**, the three metric sources distinguished, the kube-state-metrics series, control-plane signals, the CRI log path and rotation, why `kubectl logs` loses data, the dashboards, the alert set, cost observability | ✅ severely |
| §2.29 the debugging cookbook | §12 (the four named Events causes + the `logs --previous` tip + the context warning) | ✅ all 20 named failure modes as symptom → confirm → cause → fix, **the service-unreachability checklist**, the 5-second-DNS and throttling signatures, the works-on-my-machine list, the disk-full and apiserver and etcd cases, the tooling, **the four QuizStakes incident write-ups** | ✅ **§12's four Events causes, the `--previous` tip, `port-forward`, `kubectl debug` and the context warning must all survive verbatim — they are the nucleus of the largest section in PART 2** |
| §2.30 choosing an orchestrator | §13 (the 7-row comparison table, the honest positioning, the five-service failure mode, the transferability point) | ✅ the full option set beyond ECS/EKS, the QuizStakes decision made explicitly, the bad reasons, the migration order, serverless containers and the `FundsLedger` exception | ✅ **§13 is excellent. The table, the "ECS with Fargate does the job" paragraph, the five-service failure mode and the transferability caveat must all survive verbatim.** |
| §2.31 testing against containers | — | ✅ entire section — Testcontainers mechanics and wait strategies, the socket-access caveat, `@ServiceConnection`, what to test with containers, **manifest testing and the kind-based e2e**, the graceful-shutdown test, chaos experiments | |
| §3.1 namespace internals | §1 (the seven-namespace list) | ✅ the syscalls, `/proc/<pid>/ns`, the runc mount sequence, `pivot_root` vs `chroot` proved, PID-namespace nesting, `/proc` remounting, veth mechanics, uid_map format, time offsets, the by-hand experiment | ✅ severely |
| §3.2 cgroup v2 internals and arithmetic | — | ✅ entire section | |
| §3.3 CFS bandwidth control | §9 (the 50ms/100ms explanation and the throttling metric) | ✅ the slice mechanism and its numbers, the 8-thread proof, why utilisation looks low, the per-CPU hoarding bug and its fix, the knobs, the measurement procedure, the GC and probe interactions, the published evidence | ✅ **the 50ms-per-100ms explanation is correct and is the seed for the whole section** |
| §3.4 the memory cgroup and the OOM killer | §9 (OOMKill = "the kernel kills the process instantly", exit 137) | ✅ what `memory.current` counts, **working set defined**, the breach path and victim selection, `memory.high`/`min`/`low`, `memory.events`, `memory.stat`, swap, node-vs-cgroup OOM, the evidence trail, THP | ✅ |
| §3.5 OverlayFS internals | §2 (one clause: "stacked with a union filesystem (overlay2)") | ✅ entire section — the mount call, both on-disk layouts, lookup cost, copy-up triggers, whiteouts and opaque xattrs, the **POSIX deviations**, page-cache sharing, inode and kernel requirements, the layer limit, the driver alternatives | |
| §3.6 layers, digests, content addressing | §2 (layers are "content-addressed"), §6 ("images are content-addressed by digest") | ✅ the four-hash chain, tamper-evidence proved, `chainID`, why builds are not reproducible, cross-repo blob mounts, the by-hand reading exercise, zstd, the referrers fallback | ✅ **§6's "`myapp@sha256:...` is the truly immutable reference" and "Kubernetes records the digest it pulled" must survive verbatim** |
| §3.7 the registry protocol | — | ✅ entire section | |
| §3.8 containerd architecture | — | ✅ entire section | |
| §3.9 runc | — | ✅ entire section — including the two CVEs that explain why the ordering matters | |
| §3.10 CRI in detail | — | ✅ entire section — including the CRI log format that explains fragmented log lines | |
| §3.11 the API server pipeline | — | ✅ entire section | |
| §3.12 etcd | — | ✅ entire section — including the 1.5 MiB and 8 GiB limits and the restore runbook | |
| §3.13 controllers and informers | §7 ("controllers continuously reconcile actual state toward it") | ✅ the client-go machinery, the queue's role, cache staleness and `409`, resync vs relist, owner refs and GC, the finalizer protocol, leader election, the hot-loop pathology, **the Deployment controller source walk**, ReplicaSet expectations, EndpointSlice batching | ✅ severely |
| §3.14 the scheduler | §7 (one clause in the Node row) | ✅ entire section | |
| §3.15 the kubelet | §7 (one clause: nodes run "the kubelet and a container runtime") | ✅ entire section — the sync loop, `syncPod` ordering, every manager, **the node-death timeline arithmetic**, the volume and probe managers, the kubelet API and its 1.36 authorization split, the config fields, the cgroup-v2 requirement | |
| §3.16 kube-proxy datapath | §7 (kube-proxy named as the actor for readiness) | ✅ entire section — the chain walk with real output, statistic-module selection, the linear-scan scaling proof, IPVS and its deprecation, **nftables**, eBPF replacement, **conntrack and stale entries**, session affinity, `Local` policy, the full packet walk, the debugging commands | |
| §3.17 CNI and the pod network | §7 (DaemonSet row mentions CNI) | ✅ entire section — the four network invariants, the CNI spec and who calls it, the datapath families, **the AWS VPC CNI max-pods arithmetic**, MTU, IP reuse, policy enforcement, Multus, the debugging procedure | |
| §3.18 CSI | §7 (PVC/PV row) | ✅ entire section — the controller/node split, stage vs publish, `VolumeAttachment` and attach limits, **the Multi-Attach error and the 6-minute force-detach**, CSI migration, `CSIDriver` fields, ephemeral inline volumes, debugging | |
| §3.19 CoreDNS internals | — | ✅ entire section | |
| §3.20 concurrency, consistency, failure | — | ✅ entire section — and §3.20.6 ("Kubernetes gives you at-least-once pod execution, not exactly-once") is the sentence the whole money-path discussion depends on | |
| §3.21 the security boundary examined | §1 (the escape-risk paragraph), §3 (the Docker socket) | ✅ the threat-model columns, the escape chain with the control that breaks each step, `RuntimeDefault`'s value, the node as blast radius, layer forensics, runtime detection, the compliance tooling | ✅ **the escape-risk paragraph must survive verbatim** |
| §3.22 reading the source | — | ✅ entire section | |
| PART 4 — every `[BUILD]` (§4.1–§4.7) | §3 (one production Dockerfile), §5 (one compose file), §8/§9/§10/§11 (manifest fragments), §4/§12 (command lists) | ✅ all 52 leaves. **The current guide contains no Java, no complete manifest set, no scripts and no from-scratch implementations.** The existing Dockerfile, compose file and YAML fragments must be preserved, re-domained to QuizStakes, and become the seeds of §4.5–§4.6 | ✅ |
| PART 5 §5.1 — the question bank | — | ✅ all ~190 questions | |
| PART 5 §5.2 — the trap index | 4 explicit `**Trap:**` markers (`:latest`, the dependency storm, the termination race, and the liveness rule) plus ~12 inline trap-shaped warnings | ✅ all 65 entries; **all four existing `**Trap:**` blocks must be preserved verbatim** | |
| PART 5 §5.3 — drills | the 56-line closing checklist | ✅ the numbers/command/recovery/reading/manifest/explanation drills | ✅ **the 56-line `## Atomic concept checklist` must be preserved verbatim and extended, not rewritten — `gaps-analyzer-agent` and `understanding-book-keeper` parse it** |

Six corrections the write pass **must** make to existing text, not merely additions:

1. **§7's Ingress row says "(Gateway API is its successor.)" and names nginx as an implementation.**
   As of 24 March 2026 `ingress-nginx` is retired with no CVE patches, and Gateway API v1.5 is a
   shipped, GA, Standard-channel API — not a future successor. The row must say so, name the live
   controller options, and point at `ingress2gateway`.
2. **§1 says "Modern JVMs (8u191+, 11+) read cgroup limits — but the lesson generalises."** That is
   correct but incomplete in the direction that matters: `-XX:MaxRAMPercentage` **defaults to 25**,
   so a container-aware JVM with no flags still gets a heap that is usually wrong, and
   `-XX:+UseContainerCpuShares` — the flag that used to restore the old `availableProcessors()`
   behaviour — was **removed in JDK 21**. State both.
3. **§2 says "BuildKit (`DOCKER_BUILDKIT=1`, default in recent Docker)".** Name the release
   (default since Engine 23) and add the Engine 29 change that matters more: the **containerd image
   store is now the default and the classic `overlay2` graph driver is deprecated**, which
   invalidates the mental model of images living in `/var/lib/docker/overlay2`.
4. **§7's Secret row says "base64-encoded, NOT encrypted by default"** and lists three mitigations
   in one line. Keep the warning verbatim, but the mitigations are a section: KMS v2 encryption at
   rest, RBAC, ESO vs Secrets Store CSI, and the rotation requirement that the application must
   notice a rotated secret.
5. **§7's Pod row says "one or more containers sharing a network namespace … Usually one app
   container plus optional sidecars."** Since 1.33 a sidecar is a *distinct lifecycle* — an
   `initContainers` entry with `restartPolicy: Always`, started first, torn down last, and no
   longer blocking Job completion. The current wording describes the pre-1.29 convention.
6. **§9's `resources` example sets both `requests.cpu: 500m` and `limits.cpu: "2"`** while the prose
   argues that many teams should omit CPU limits. The example and the argument contradict each
   other; the write pass must give two examples (with and without a CPU limit) and say which shape
   belongs on which QuizStakes service.

Eleven passages in the current guide are strong and must survive **verbatim or expanded**, not
rewritten: the container-vs-VM table and the shared-kernel consequences (§1); the "reproducible
artefact, not efficiency" paragraph (§1); the BAD/GOOD dependency-ordering Dockerfile pair and the
cache rule (§2); the deleted-file-still-in-the-image paragraph (§2); the 13-item Dockerfile
checklist, especially the exec-form `ENTRYPOINT` item (§3); the `exec`-vs-`run` and
`host:container` clarifications (§4); the `depends_on`-is-not-readiness trap (§5); the tagging
strategy with "rollback by tag is the fastest recovery action" (§6); the probe actor table with the
dependency-storm trap and the readiness caveat (§8); the CPU/memory asymmetry table with the
`-Xmx`/`MaxRAMPercentage` pair and the exit-137-vs-`OutOfMemoryError` distinction (§9); and the
termination-race trap with its full six-step fix chain (§10). Plus §13's ECS-vs-Kubernetes table
and its honest positioning paragraph, and §12's `describe pod`-first instruction.

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.31 | 436 |
| PART 2 — Intermediate | §2.1–§2.31 | 393 |
| PART 3 — Under the hood | §3.1–§3.22 | 236 |
| PART 4 — Build it | §4.1–§4.7 | 52 |
| PART 5 — Interview and retention | §5.1–§5.3 | 84 |
| **Total** | **94 sections** | **1,201 leaves** |

`[RESEARCH]`-tagged leaves: **189** (counted as tagged lines, of which 20 sit in the currency
header's twenty-delta list). Each must be re-verified against its cited source during the write
pass before any constant from it is written down. The highest-risk clusters, in order:

- **The cgroup v2 hard requirement** (§1.3, §3.15.13, version-trap 7). The claim that the kubelet
  *fails to start* by default without cgroup v2 as of **1.35** came from a single secondary summary.
  Verify against KEP-4569, KEP-5573 and the 1.35 release notes before writing it. If it cannot be
  confirmed, state only what is documented: maintenance mode since 1.31 and a start-up warning.
- **Every Kubernetes 1.34–1.37 feature claim** (§1.31.3–§1.31.6, §1.21.7, §1.28.14–§1.28.15,
  §2.13.9, §2.14.4, §1.22.4, §1.24.7–§1.24.8). Only the 1.36 sneak peek and the 1.37 release
  announcement's counts were fetched from kubernetes.io; the rest are search summaries. Fetch
  `kubernetes.io/releases/1.37/` and the per-release blog posts.
- **The soft eviction thresholds** (§2.12.8). The fetched summary asserted defaults of
  80Mi/5%/10%/20% and a 30 s `eviction-max-pod-grace-period`. The kubelet ships **no default soft
  thresholds**. Re-read the page; do not write those numbers.
- **The Restricted profile's control list** (§2.22.4). The fetch truncated before the Restricted
  section; the list in this syllabus is from recall. Re-fetch the Pod Security Standards page.
- **Gateway API v1.5's promotion list and v1.6's contents** (§1.24.6–§1.24.10). The promotions came
  from a search summary of the announcement blog, not the blog itself, and `BackendTLSPolicy`'s
  Standard release (v1.4.0) came from a vendor page. Fetch
  `kubernetes.io/blog/2026/04/21/gateway-api-v1-5/` and the v1.5.0/v1.6.0 release notes.
- **Docker Engine 29's release notes** (§1.6.9–§1.6.10, §1.10.7, §1.31.12). The containerd-image-
  store default, the graph-driver deprecation, `default-stop-timeout`, the embedded-containerd
  experiment and both 2026 CVE identifiers are all from a single search summary. Fetch
  `docs.docker.com/engine/release-notes/29/`.
- **containerd 2.1/2.2 and runc 1.3/1.4** (§3.8.7, §3.9.8, §3.9.9, §1.4.12). NRI/CDI defaults, the
  transfer service, parallel range requests, the `pids.limit = 0` behaviour change and the
  runtime-spec 1.3 release date are all secondary. Read the release notes and CHANGELOG.
- **Helm 4's apply semantics** (§2.24.5). The SSA-for-new-releases-only rule, the kstatus `watch`
  requirement and the post-renderer-as-plugin change are from third-party migration posts. Fetch
  `helm.sh/blog/helm-4-released/` and the Helm 4 migration guide.
- **Karpenter's provisioning-latency figures and the 10% default budget** (§2.15.5–§2.15.6,
  §2.15.9). The 45–60 s vs 3–4 min comparison is from vendor marketing and must be **attributed**,
  not asserted. The default budget should be confirmed against `karpenter.sh`.
- **The CFS throttling evidence** (§2.8.11–§2.8.13, §3.3.4, §3.3.10). The "6 cores throttled to 3,
  50% throughput loss" figure is from a CoreOS issue report; the Omio numbers are from a company
  blog. Attribute both. Whether the per-CPU slice-hoarding bug is fully fixed in current kernels
  was **not** established — do not claim it is.
- **The JDK 21 removal of `-XX:+UseContainerCpuShares`** (§2.8.10, version-trap 12) and the
  `MaxRAMPercentage` default of 25 (§2.8.3). Both are from Red Hat/AWS articles rather than the JDK
  release notes. Confirm against the JDK 21 release notes and `java -XX:+PrintFlagsFinal`.
- **The CKA/CKAD domain weights** (§5.1, used as the completeness checklist). From a third-party
  guide; if they are quoted in the bible at all, attribute them to
  training.linuxfoundation.org and re-check.
- **The kubelet defaults in §3.15.6, §3.15.11 and §1.18.12** — the 10 s heartbeat, 40 s lease
  duration, 50 s monitor grace period, 300 s `tolerationSeconds`, `maxPods` 110, image GC 85/80,
  `containerLogMaxSize` 10Mi / `containerLogMaxFiles` 5. These are from recall and the fetched
  eviction page, not from the `KubeletConfiguration` reference. Verify each.
- **The etcd limits** (§1.19.18, §3.12.6) — the 1.5 MiB request size, the 2 GiB default quota and
  the 8 GiB recommended maximum. From recall; verify against etcd.io's tuning and
  hardware pages.

A note on balance for the write pass. PART 1 is deliberately the largest part because this topic's
"basics" include two complete API surfaces (the Dockerfile/CLI and the Kubernetes object model),
and a bible that leaves an object or a field unnamed sends the reader elsewhere. PART 2 is nearly
as large because the *decisions* — which controller, which probe, which limit, which orchestrator —
are where this topic is actually assessed in an interview, and because §2.29 (debugging) reflects
the CKA's 30% troubleshooting weight. PART 3 is smaller in leaf count but will take the most words
per leaf: every `[SOURCE]` leaf needs a real excerpt read line by line, and §3.2, §3.3, §3.5,
§3.9, §3.14, §3.15 and §3.16 each require a walkthrough rather than a description.

**This topic will exceed 2,500 lines. Split it at the PART 2/PART 3 boundary** into
`19-docker-kubernetes.md` (PARTS 1–2, the container and orchestrator as a working system) and
`19-docker-kubernetes-internals.md` (PARTS 3–5, the kernel and control-plane internals, the
build-its, and the interview layer). Cross-link both at the top, keep an
`## Atomic concept checklist` in **each** file, carry the current guide's 56 checklist lines into
the first file, and add the new file to `src/topics/00-index.md`.




