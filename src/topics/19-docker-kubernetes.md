# 19 — Docker & Kubernetes

Scope: containers as a mechanism (not a magic box), the image-building details that determine build
speed and security, and the Kubernetes concepts a backend engineer needs to deploy, debug, and reason
about their own service.

---

## 1. Images vs containers vs VMs

**Image** — an immutable, layered filesystem plus metadata (entrypoint, env, exposed ports, user). A
build artefact. Analogy: a class.

**Container** — a running process (or process tree) started from an image, with a thin writable layer
on top. Analogy: an instance. Multiple containers from one image share the read-only layers.

**Container vs VM — the mechanism.** A VM runs a **complete guest OS with its own kernel** on top of
a hypervisor. A container is **just a process on the host kernel**, isolated by two Linux features:

- **Namespaces** provide isolation of *what you can see*: PID (your process is PID 1 and can't see
  the host's), network (own interfaces, own port space — this is why two containers can both bind
  8080), mount (own filesystem view), UTS (own hostname), IPC, user (UID mapping), cgroup.
- **cgroups** (control groups) provide limits on *what you can use*: CPU, memory, block I/O, PIDs.

| | Container | VM |
|---|---|---|
| Kernel | **shared with the host** | its own |
| Startup | milliseconds | tens of seconds |
| Overhead | ~process-level | hundreds of MB, plus CPU |
| Density | hundreds per host | tens |
| Isolation | process-level (weaker) | hardware-level (stronger) |
| Guest OS choice | must match the host kernel | any |

**Consequences of the shared kernel that actually matter:**
- **You cannot run a Windows container on a Linux host** (or vice versa) without a VM underneath —
  which is exactly what Docker Desktop on macOS/Windows does, and why file I/O across the bind mount
  is slow there.
- A kernel vulnerability is a **container escape** risk. Containers are an isolation boundary, but a
  weaker one than a VM. This is why multi-tenant platforms use Firecracker microVMs (Fargate, Lambda)
  rather than raw containers, and why `--privileged` and mounting the Docker socket are serious.
- **`/proc` and the kernel are shared**, so a naive process sees the *host's* CPU count and memory
  unless it's cgroup-aware. Historically this made JVMs allocate heap based on host memory inside a
  512 MB container and get OOMKilled instantly. Modern JVMs (8u191+, 11+) read cgroup limits — but
  the lesson generalises to any tool that reads `/proc/cpuinfo` (thread pool sizing!). See §7.

**What containers actually give you:** a reproducible artefact that runs the same on a laptop, in CI,
and in production, including its dependencies and runtime. "Works on my machine" becomes "here is my
machine." That, not efficiency, is the main value.

---

## 2. Layers and build cache

A Dockerfile instruction (`RUN`, `COPY`, `ADD`) creates a **layer** — a content-addressed diff of the
filesystem. Layers are stacked with a union filesystem (overlay2) and are **immutable and shared**:
ten images built `FROM eclipse-temurin:21-jre` store that base once.

**Cache rule: an instruction's cache is valid only if the instruction and all preceding layers are
unchanged. Once a layer is invalidated, every layer after it is rebuilt.** For `COPY`/`ADD`, the
checksum of the copied files is part of the cache key.

That rule dictates Dockerfile ordering: **least-frequently-changing first.**

```dockerfile
# BAD — source changes on every commit, so dependencies are re-downloaded every build
COPY . .
RUN ./mvnw package
```

```dockerfile
# GOOD — dependency layer is cached until pom.xml changes
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN ./mvnw -B dependency:go-offline     # cached across all source-only changes
COPY src ./src
RUN ./mvnw -B package -DskipTests
```

The first version downloads the entire Maven repository on every build (minutes). The second does it
only when `pom.xml` changes (seconds thereafter). The same pattern applies to `package.json`/`npm ci`
and `requirements.txt`/`pip install`. This is the single highest-leverage Dockerfile change most
teams can make.

Two more cache facts:
- `RUN apt-get update && apt-get install -y x` must be **one instruction**. Split across two `RUN`s,
  a cached `update` layer pairs with a fresh `install` and you get stale package indexes and
  irreproducible builds.
- Layers are additive: deleting a file in a later layer **doesn't shrink the image**, because the
  bytes still exist in the earlier layer (and can be extracted). A secret `COPY`d and then `rm`'d is
  still in the image. Use multi-stage builds or BuildKit secret mounts.

BuildKit (`DOCKER_BUILDKIT=1`, default in recent Docker) adds parallel stage execution, `--mount=type=cache`
for persistent package caches across builds, and `--mount=type=secret` for build-time secrets that
never land in a layer.

---

## 3. Dockerfile hygiene checklist

A complete, production-shaped example, then the rules:

```dockerfile
# syntax=docker/dockerfile:1

# ---------- build stage ----------
FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /build
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN --mount=type=cache,target=/root/.m2 ./mvnw -B dependency:go-offline
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 ./mvnw -B package -DskipTests

# ---------- runtime stage ----------
FROM eclipse-temurin:21-jre-jammy
RUN groupadd -r app && useradd -r -g app -u 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /build/target/app.jar app.jar
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health/readiness || exit 1
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=70", "-jar", "app.jar"]
```

**The checklist:**

- [ ] **Pin base image tags.** `FROM eclipse-temurin:21-jre-jammy`, not `:latest`. `latest` makes
      builds non-reproducible and silently upgrades your runtime mid-incident. Pin by digest
      (`@sha256:...`) where supply-chain integrity matters.
- [ ] **Multi-stage build; ship a JRE, not a JDK.** The build stage needs a compiler, Maven, and the
      source; the runtime needs none of it. This typically takes an image from ~800 MB to ~200 MB, and
      more importantly removes compilers, build tools, and source code from the production attack
      surface. Consider `jlink`/`jdeps` for a custom minimal runtime, or a distroless base.
- [ ] **Never put secrets in `ENV` or `ARG`.** Both are **baked into image metadata** and readable by
      anyone with the image via `docker history` — including `ARG`, which people wrongly believe is
      build-time-only and discarded. Inject secrets at runtime (topic 18 §6) or use BuildKit
      `--mount=type=secret`.
- [ ] **Run as a non-root user.** Containers run as root by default. Combined with a kernel
      vulnerability or a bad volume mount, that's a host compromise. Create a user and `USER` it. Note
      the ordering: `COPY --chown` *after* creating the user, and `USER` after anything needing root.
- [ ] **Add a `.dockerignore`.** Without one, the whole directory (including `.git`, `target/`,
      `node_modules/`, `.env`, IDE files) is sent to the daemon as build context — slow, and a real
      leak risk if any of it gets `COPY . .`'d.
      ```
      .git
      target/
      node_modules/
      .env*
      *.md
      .idea/
      Dockerfile
      ```
- [ ] **Use exec form for `ENTRYPOINT`/`CMD`.** `ENTRYPOINT ["java", "-jar", "app.jar"]` runs the JVM
      as PID 1. Shell form (`ENTRYPOINT java -jar app.jar`) runs `/bin/sh -c` as PID 1, and **the
      shell does not forward SIGTERM** — so your app never gets the shutdown signal, is SIGKILLed
      after the grace period, and drops in-flight requests on **every single deploy**. (Topic 11 §6.)
      If you genuinely need a wrapper script, `exec java ...` at the end of it.
- [ ] **Handle PID 1 semantics.** PID 1 doesn't get default signal handlers and doesn't reap orphaned
      children (zombies). If your container spawns subprocesses, use `--init` / `tini`.
- [ ] **`HEALTHCHECK`** so the runtime knows the difference between "process running" and "working".
      Note Kubernetes ignores Docker `HEALTHCHECK` and uses its own probes (§6) — this is for
      Docker/Compose/ECS.
- [ ] **One concern per container.** No supervisord running your app plus nginx plus cron. Separate
      containers, so they scale, restart, and are monitored independently.
- [ ] **Combine and clean package installs in one layer:**
      `RUN apt-get update && apt-get install -y --no-install-recommends x && rm -rf /var/lib/apt/lists/*`
- [ ] **Log to stdout/stderr**, never to a file inside the container (topic 20 §3).
- [ ] **Scan images** (`trivy`, `grype`, ECR scanning) in CI and fail on critical CVEs. A base image
      pinned two years ago is a pile of known vulnerabilities.
- [ ] Keep the image small: smaller means faster pulls, faster scale-out, faster deploys, and less
      attack surface. Alpine is tiny but uses musl libc, which has bitten JVM and glibc-dependent
      workloads — prefer a slim glibc base or distroless unless you've tested Alpine.

---

## 4. Docker CLI basics

```bash
docker build -t myapp:1.4.2 .
docker build -t myapp:1.4.2 --build-arg VERSION=1.4.2 --progress=plain .
docker images
docker history myapp:1.4.2            # per-layer size — find what's bloating the image

docker run -d --name api -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=local \
  --memory=1g --cpus=1.5 \
  myapp:1.4.2
docker ps                             # running; -a for all
docker logs -f --tail 100 api         # follow logs
docker exec -it api sh                # shell inside a RUNNING container
docker stop api                       # SIGTERM, then SIGKILL after 10s (-t to change)
docker rm -f api
docker stats                          # live CPU/memory/network per container
docker inspect api                    # full JSON config and state
docker cp api:/app/heap.hprof ./      # get a file out
docker system prune -af --volumes     # reclaim disk (careful: -a removes unused images)
```

Two distinctions that trip people up:

- **`docker exec` vs `docker run`.** `exec` enters an already-running container; `run` starts a new
  one from the image. If a container is crash-looping you cannot `exec` into it — instead
  `docker run -it --entrypoint sh myapp:1.4.2` to poke around the image, or read `docker logs`.
- **`-p 8080:8080` is `host:container`.** The container's port space is its own namespace; publishing
  is what bridges it to the host.

Volumes: `-v /host/path:/container/path` (bind mount, host filesystem — good for local dev) vs
`-v myvolume:/data` (named volume, Docker-managed — the right choice for persistence). Anything
written to the container's writable layer disappears when the container is removed.

---

## 5. docker-compose for local stacks

Compose defines a multi-container local environment in one file. Its real value is that a new
engineer runs `docker compose up` and has Postgres, Redis, LocalStack, and the app running with
correct wiring in two minutes rather than a day of README archaeology.

```yaml
services:
  api:
    build: .
    ports: ["8080:8080"]
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/app
      SPRING_DATA_REDIS_HOST: cache
    depends_on:
      db:    { condition: service_healthy }
      cache: { condition: service_started }

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: local-only-not-a-secret
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10

  cache:
    image: redis:7-alpine

volumes:
  pgdata:
```

Points worth knowing:
- Compose creates a **network where service names are DNS hostnames** — `db:5432` resolves. This is
  why the connection string uses `db`, not `localhost`.
- **`depends_on` alone only orders *startup*, not readiness** — the classic bug is the app starting
  before Postgres accepts connections and crash-looping. Use `condition: service_healthy` with a
  healthcheck (as above), or make the app retry its connection, which it should do anyway.
- Named volumes persist data across `down`/`up`; `docker compose down -v` wipes them.
- Compose is for local development and CI, not production. Production orchestration is ECS or
  Kubernetes.

---

## 6. Registries, tags, and rollback

A **registry** stores images (Docker Hub, ECR, GHCR, GitLab, Artifactory). `docker push` /
`docker pull`; private registries need `docker login` (for ECR, `aws ecr get-login-password | docker
login --password-stdin ...`, or let the ECS/EKS node role handle it).

**Tagging strategy — the important part.**

> **Trap:** Deploying `myapp:latest`. You cannot tell what's running, two nodes can pull different
> images under the same tag, `imagePullPolicy` interacts badly with mutable tags, and **rollback is
> impossible because the previous artefact has no name.**

Tag with something immutable and traceable:
```
myapp:1.4.2                      # semantic version — for humans and releases
myapp:1.4.2-a1b2c3d              # version + git SHA — fully traceable
myapp:a1b2c3d                    # git SHA alone — simplest immutable tag
myapp:latest                     # convenience pointer only; never referenced by a deployment
```
Push both an immutable tag and a moving one; **deploy only the immutable tag.**

**Rollback by tag** then becomes the fastest and safest recovery action available:
```bash
kubectl set image deployment/api api=myrepo/myapp:1.4.1
# or
kubectl rollout undo deployment/api
```
Seconds, no build, no CI queue, and an artefact you know worked because it was running an hour ago.

This is why **"roll back first, diagnose second"** is the standard incident response (topic 20 §7) —
and it only works if your tags are immutable and the previous image is still in the registry (set
registry lifecycle policies to keep the last N, not to expire aggressively).

Also: images are content-addressed by digest, so `myapp@sha256:...` is the truly immutable reference.
Kubernetes records the digest it pulled, which is how you find out what *actually* ran.

---

## 7. Kubernetes vocabulary

Enough to be useful; the concepts a backend engineer touches.

| Object | What it is |
|---|---|
| **Pod** | the smallest deployable unit: **one or more containers sharing a network namespace (same IP and localhost) and volumes**. Usually one app container plus optional sidecars. **Pods are ephemeral and disposable** — never treat one as a server. |
| **Node** | a worker machine (EC2 instance) running the kubelet and a container runtime. |
| **ReplicaSet** | maintains N identical pods. You rarely create one directly. |
| **Deployment** | declares desired state for stateless apps: image, replica count, update strategy. Manages ReplicaSets to perform rolling updates and rollbacks. **This is what you'll write.** |
| **StatefulSet** | like a Deployment but with stable network identities (`db-0`, `db-1`), stable per-pod storage, and ordered rollout. For databases, Kafka, anything with identity. |
| **DaemonSet** | one pod per node — log collectors, monitoring agents, CNI. |
| **Job / CronJob** | run-to-completion work; CronJob on a schedule (at-least-once — topic 14 §12). |
| **Service** | a stable virtual IP and DNS name in front of a changing set of pods, selected by label. Types: `ClusterIP` (internal, the default), `NodePort`, `LoadBalancer` (provisions a cloud LB), `ExternalName`. |
| **Ingress** | L7 HTTP routing (host/path) into Services, implemented by an ingress controller (nginx, ALB controller, Traefik). One load balancer serving many services. (Gateway API is its successor.) |
| **ConfigMap** | non-secret configuration, injected as env vars or mounted files. |
| **Secret** | the same, for sensitive values — **base64-encoded, NOT encrypted by default.** Enable encryption at rest, restrict RBAC, or use External Secrets / Secrets Store CSI to pull from AWS Secrets Manager. Anyone with `get secrets` in the namespace can read them. |
| **Namespace** | a logical partition for names, RBAC, and resource quotas. |
| **HPA** | Horizontal Pod Autoscaler — scales replica count on metrics. |
| **PVC / PV** | persistent storage claims and volumes (EBS, EFS). |

**Service discovery** is DNS: `http://payments` within a namespace, `http://payments.billing.svc.cluster.local`
across namespaces. The Service's ClusterIP is stable even as pods come and go — that indirection is
the whole point.

**The declarative model** is the conceptual core: you submit *desired state* (`kubectl apply -f`), and
controllers continuously reconcile *actual state* toward it. A deleted pod is recreated; a crashed
node's pods are rescheduled. You don't run commands to make things happen; you describe the world and
the system converges. This is also why `kubectl edit` on a live object is a bad habit — the next
`apply` from Git overwrites it, and your fix vanishes mysteriously.

---

## 8. Liveness vs readiness (and startup) probes

Kubernetes' most commonly misconfigured feature, and a favourite interview question because the
distinction is about *who acts on the answer*.

| Probe | Question | Failure action | Actor |
|---|---|---|---|
| **Liveness** | "Is this process broken beyond recovery?" | **kill and restart the container** | kubelet |
| **Readiness** | "Can this pod serve traffic *right now*?" | **remove from Service endpoints** (pod keeps running) | endpoints controller / kube-proxy |
| **Startup** | "Has it finished booting yet?" | kill; **disables liveness/readiness until it passes** | kubelet |

**Readiness is the one you'll use most.** It is temporary and reversible: a pod that's warming its
cache (topic 15 §13), draining before shutdown, or briefly overloaded stops receiving traffic and
resumes when it recovers. Nothing is destroyed.

**Liveness is a last resort.** It exists for states a restart genuinely fixes — a deadlock, an
unrecoverable internal error, a wedged event loop. If a restart wouldn't fix it, liveness shouldn't
detect it.

### The dependency-storm trap

> **Trap:** Putting dependency checks (database, Redis, downstream APIs) in the **liveness** probe.
>
> The database has a 30-second blip. Every pod's liveness probe fails. Kubernetes kills **every pod in
> the fleet simultaneously**. They restart, and their liveness probes fail again because the database
> is still recovering — and now it's recovering while being hammered by a hundred reconnecting pods
> and a full cold cache. You have converted a 30-second dependency blip into a total, self-sustaining
> outage. The restarts helped nothing: restarting your pod does not fix someone else's database.
>
> **Rule: liveness checks only what a restart can fix — the process itself.** Keep it shallow and
> local. Dependency health belongs in readiness (and even there, be careful — see below).

```yaml
livenessProbe:                      # shallow, local, cheap
  httpGet: { path: /actuator/health/liveness, port: 8080 }
  initialDelaySeconds: 0            # not needed when using a startupProbe
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 2

readinessProbe:                     # may include critical dependencies
  httpGet: { path: /actuator/health/readiness, port: 8080 }
  periodSeconds: 5
  failureThreshold: 2
  timeoutSeconds: 2

startupProbe:                       # slow JVM boot: allow up to 5 minutes
  httpGet: { path: /actuator/health/liveness, port: 8080 }
  periodSeconds: 10
  failureThreshold: 30
```

Spring Boot supports this split natively (`management.endpoint.health.probes.enabled=true` gives
`/actuator/health/liveness` and `/actuator/health/readiness`), and readiness automatically reports
`OUT_OF_SERVICE` during graceful shutdown — which is exactly what you want.

**The readiness caveat.** Even in readiness, a hard dependency check is dangerous: if Redis is down
and every pod reports not-ready, the Service has **zero endpoints** and you're fully down — even
though you might have degraded gracefully by skipping the cache. Distinguish **hard dependencies**
(no database, genuinely cannot serve) from **soft** ones (no cache, can serve slowly). Only hard
dependencies belong in readiness.

**Other probe mistakes:**
- No `startupProbe` on a slow-starting JVM, so `initialDelaySeconds` on liveness has to be huge —
  which also delays detection of real failures forever. Use a startup probe instead.
- A probe endpoint that's expensive or that requires auth (it comes from the kubelet, unauthenticated).
- `timeoutSeconds` shorter than the endpoint's p99 under load, causing restarts precisely when you're
  busiest.
- Probing a port the app hasn't bound yet.

---

## 9. Requests, limits, and the JVM

```yaml
resources:
  requests:            # what the SCHEDULER guarantees and uses for bin-packing
    cpu: "500m"
    memory: "1Gi"
  limits:              # the hard ceiling the KERNEL enforces via cgroups
    cpu: "2"
    memory: "1Gi"
```

**Requests** determine placement: the scheduler finds a node with that much *unreserved* capacity.
Requests are also what you're effectively paying for in capacity planning.

**Limits** are enforced at runtime, and **CPU and memory behave completely differently:**

| | Over the CPU limit | Over the memory limit |
|---|---|---|
| Mechanism | **CFS throttling** — the container is stopped for the rest of the 100 ms period | **OOMKill** — the kernel kills the process instantly |
| Effect | latency spikes, no crash | container terminated, exit **137**, restart, possible CrashLoopBackOff |
| Recoverable | yes, automatically | no — the process dies |

**Memory is incompressible; CPU is compressible.** That asymmetry drives the standard guidance:

- **Always set a memory limit, and set `requests.memory == limits.memory`.** This puts the pod in the
  `Guaranteed` QoS class, so it's the last to be evicted under node memory pressure. Memory
  overcommitment doesn't degrade — it kills.
- **CPU limits are contentious.** Setting a CPU limit means your pod gets throttled even when the node
  is idle, adding latency for no benefit. Many teams set CPU *requests* (for scheduling and fair
  share) and **no CPU limit**, letting pods burst into idle capacity. Set CPU limits when you need
  hard multi-tenant isolation or predictable performance; otherwise consider omitting them.

**CPU throttling is the sneakiest performance bug in Kubernetes.** A limit of `500m` does **not** mean
"half a core continuously" — it means 50 ms of CPU per 100 ms period, *across all threads*. A JVM
with 8 GC threads and 200 request threads burns the quota in the first few milliseconds of the period
and then sits frozen for the remaining ~95 ms. Your p99 is terrible, your CPU utilisation metric
looks *low* (you're throttled, not busy), and nothing in the application logs indicates why. Check
`container_cpu_cfs_throttled_seconds_total` — non-zero throttling on a latency-sensitive service is
an actionable finding.

### The JVM interplay

Recall topic 11 §12: JVM RSS = heap + metaspace + code cache + thread stacks (~1 MB each) + direct
buffers + GC structures + JVM overhead. The cgroup limit applies to **all of it**, not just the heap.

```
# WRONG — no headroom; guaranteed eventual OOMKill with no Java stack trace
limits.memory: 1Gi
JAVA_OPTS: -Xmx1g

# RIGHT — the JVM reads the cgroup limit and leaves room for non-heap memory
limits.memory: 1Gi
JAVA_OPTS: -XX:MaxRAMPercentage=70.0     # heap ≈ 700Mi, ~300Mi for everything else
```

`-XX:MaxRAMPercentage` is container-aware (the JVM reads the cgroup limit, not host memory) and scales
automatically if you change the limit — which is why it's preferred over a hard-coded `-Xmx`. Start
around 70% and tune from actual RSS measurements; heavy direct-buffer users (Netty) need more
headroom, and services with thousands of threads need to account for stacks.

**The diagnostic distinction to state clearly:** exit code **137** with no Java exception in the log
is the kernel OOMKilling the container (raise the limit or lower the heap percentage);
`java.lang.OutOfMemoryError: Java heap space` **with** a stack trace is the JVM's own heap exhaustion
(a leak, or too small a heap). They look similar in a dashboard and have opposite fixes.

Also container-aware: `Runtime.availableProcessors()` respects the CPU **limit** (as `ceil(quota)`),
which sizes the common ForkJoinPool, GC threads, and anything using `availableProcessors()`. With a
low CPU limit you get a tiny parallelism default; with no limit you get the node's full core count,
which may be far more than your share. Be explicit about pool sizes rather than trusting the default.

---

## 10. Rolling updates and graceful shutdown

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1              # how many extra pods above desired during the roll
    maxUnavailable: 0        # never drop below desired capacity — safest setting
minReadySeconds: 10          # a pod must stay ready this long before it counts
```

With `maxUnavailable: 0`, Kubernetes creates a new pod, **waits for it to be Ready**, then terminates
an old one, and repeats. Capacity never dips. That's why readiness probes are what make a rolling
update safe — without a meaningful readiness probe, Kubernetes shifts traffic to a pod that isn't
serving yet.

`kubectl rollout status deployment/api` waits and reports; `kubectl rollout undo deployment/api`
reverts to the previous ReplicaSet in seconds.

### The termination sequence — and the race

When a pod is deleted (deploy, scale-in, node drain), **two things happen concurrently, not in
sequence**:

1. The pod is marked Terminating and **removed from Service endpoints** — which must then propagate
   to kube-proxy on every node, to the ingress controller, and to any cloud load balancer target
   group. This takes hundreds of milliseconds to several seconds.
2. The kubelet runs the `preStop` hook, then sends **SIGTERM** to PID 1.

> **Trap:** Because these are concurrent, there is a window in which the pod has received SIGTERM and
> started shutting down while load balancers are **still sending it new requests**. The result is a
> handful of connection resets on every single deploy — small enough to be dismissed as noise, real
> enough to show up as a p99.9 error spike, and completely avoidable.

**The fix — the full chain:**

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 5"]        # let deregistration propagate BEFORE SIGTERM
terminationGracePeriodSeconds: 45             # > preStop + drain time
```

```properties
# Spring Boot
server.shutdown=graceful
spring.lifecycle.timeout-per-shutdown-phase=30s
```

The complete sequence, which is worth being able to recite:

1. Pod marked Terminating; endpoint removal begins propagating.
2. `preStop` sleeps ~5 s — the pod is still fully serving, but is being removed from every LB.
3. SIGTERM to PID 1 (this requires exec-form `ENTRYPOINT` — §3).
4. The app stops accepting new requests, fails readiness, and finishes in-flight ones.
5. It closes connection pools, flushes logs and metrics, releases locks, and exits 0.
6. If it hasn't exited by `terminationGracePeriodSeconds`, **SIGKILL** — in-flight work is lost.

Ensure `terminationGracePeriodSeconds` > preStop sleep + your longest request. Otherwise you've
carefully implemented graceful shutdown and then SIGKILL it halfway through.

**Also relevant:** a **PodDisruptionBudget** (`minAvailable: 2`) prevents voluntary disruptions (node
drains, cluster upgrades) from taking down too many pods at once. Without one, a node drain during a
cluster upgrade can remove most of your replicas simultaneously.

---

## 11. HPA, briefly

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api }
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
```

The HPA controller reads metrics (from metrics-server, or custom/external metrics via Prometheus
Adapter or KEDA) and adjusts replica count. Utilisation is measured **against `requests`**, not
limits — so a wrong request value silently mis-scales everything.

Practical notes: scale on the metric that reflects *your* bottleneck (CPU is a poor proxy for an I/O-
bound service; requests-per-pod, queue depth, or **consumer lag** — topic 14 §8 — are often better,
and KEDA makes queue-driven scaling straightforward). Configure stabilisation windows to avoid
flapping (scale up fast, scale down slowly). And remember scaling doesn't help if the bottleneck is
the database — more pods just means more connections against the same constraint (topic 18 §7).

Related: **Cluster Autoscaler / Karpenter** add *nodes* when pods can't be scheduled. HPA without node
autoscaling just gets you pods stuck in `Pending`.

---

## 12. kubectl survival commands

```bash
# Orientation
kubectl config get-contexts && kubectl config current-context   # WHICH CLUSTER AM I ON?
kubectl config use-context staging
kubectl get pods -n myns -o wide                # includes node and pod IP
kubectl get deploy,svc,ingress -n myns

# What is wrong with this pod
kubectl describe pod api-7d9f-x2k4 -n myns      # EVENTS AT THE BOTTOM — read these first
kubectl logs api-7d9f-x2k4 -n myns --tail=200 -f
kubectl logs api-7d9f-x2k4 -n myns --previous   # logs from the CRASHED container
kubectl get events -n myns --sort-by=.lastTimestamp

# Interact
kubectl exec -it api-7d9f-x2k4 -n myns -- sh
kubectl port-forward svc/api 8080:8080 -n myns  # reach a ClusterIP service from your laptop
kubectl cp myns/api-7d9f-x2k4:/tmp/heap.hprof ./heap.hprof
kubectl debug -it api-7d9f-x2k4 --image=busybox --target=api   # ephemeral container into a distroless pod

# Deploy and roll back
kubectl apply -f deployment.yaml
kubectl rollout status deployment/api -n myns
kubectl rollout undo deployment/api -n myns
kubectl set image deployment/api api=repo/myapp:1.4.1 -n myns
kubectl scale deployment/api --replicas=6 -n myns

# Resources
kubectl top pods -n myns                        # actual CPU/memory (needs metrics-server)
kubectl top nodes
kubectl get pod api-7d9f-x2k4 -o yaml           # full live spec + status
```

**`kubectl describe pod` is the first command in almost every investigation** — the Events section
tells you `ImagePullBackOff` (bad tag or registry auth), `CrashLoopBackOff` (app exits on start — then
read `logs --previous`), `OOMKilled` (§9), `FailedScheduling` (insufficient CPU/memory requests
available, or a taint/affinity mismatch), or failing probes.

Set up `kubens`/`kubectx` or an alias; typing `-n myns` on every command is how people accidentally
run commands against the wrong namespace. And **check your context before every destructive command**
— running a `delete` against prod because your context was left there from yesterday is a genuine and
common incident.

---

## 13. ECS vs Kubernetes — positioning

| | **ECS (with Fargate)** | **Kubernetes (EKS)** |
|---|---|---|
| Concepts to learn | task definition, service, cluster | dozens of object kinds, plus CRDs |
| Control plane | free, AWS-managed | ~$73/month per cluster, plus real operational work |
| Portability | AWS only | any cloud, on-prem |
| Ecosystem | AWS services | enormous: Helm, operators, service meshes, ArgoCD |
| IAM integration | native and simple (task roles) | via IRSA/Pod Identity — more setup |
| Team size to run well | small | needs platform capability, or a managed platform team |
| Flexibility | limited but sufficient for most services | can express almost anything |

**The honest positioning:** if you're all-in on AWS and running a normal set of stateless services,
**ECS with Fargate does the job with a fraction of the concepts and operational burden**, and you'll
ship faster. Kubernetes wins when you need portability, have many teams needing a shared self-service
platform, want the operator/CRD ecosystem (Kafka operators, ArgoCD, Istio, KEDA), or are already
running it.

The failure mode worth naming: **adopting Kubernetes for a five-service application** and spending a
year on platform work instead of product. "Use the simplest orchestrator that meets the requirement,
and be able to say why the requirement needs more" is the answer that lands well — as is
acknowledging that Kubernetes skills are broadly transferable in a way ECS skills are not, which is a
legitimate factor in the decision.

---

## Atomic concept checklist

- [ ] Image = immutable layered artefact; container = a running process with a thin writable layer.
- [ ] Containers are **processes on the host kernel** isolated by **namespaces** (what you see) and **cgroups** (what you use).
- [ ] Shared kernel ⇒ no cross-OS containers, and escape is a real (if unlikely) risk — weaker isolation than a VM.
- [ ] A non-cgroup-aware process sees the **host's** CPU/memory; modern JVMs read cgroup limits, but thread-pool defaults still bite.
- [ ] The main value of containers is a reproducible artefact, not efficiency.
- [ ] Layers are cached; **invalidating one layer invalidates every layer after it.**
- [ ] **Copy dependency manifests and install deps BEFORE copying source** — the highest-leverage Dockerfile fix.
- [ ] `apt-get update && install` must be one `RUN`, or you get stale indexes.
- [ ] Deleting a file in a later layer doesn't shrink the image or remove the bytes — secrets stay recoverable.
- [ ] BuildKit adds cache mounts and `--mount=type=secret` for build-time secrets.
- [ ] **Pin base tags** — never `:latest` in `FROM`.
- [ ] **Multi-stage: build with JDK, ship JRE** — smaller image, no compilers or source in production.
- [ ] **Never put secrets in `ENV` or `ARG`** — both are visible via `docker history`.
- [ ] Run as a **non-root** user; containers default to root.
- [ ] `.dockerignore` keeps `.git`, `target/`, `node_modules/`, and `.env` out of the build context.
- [ ] **Exec-form `ENTRYPOINT`** — shell form makes `/bin/sh` PID 1, which **doesn't forward SIGTERM**, so every deploy SIGKILLs your app.
- [ ] PID 1 doesn't reap zombies; use `--init`/`tini` if you spawn subprocesses.
- [ ] One concern per container; log to stdout; scan images in CI.
- [ ] `docker exec` enters a running container; a crash-looping one needs `run --entrypoint sh` or `logs`.
- [ ] `-p host:container`; named volumes persist, the writable layer does not.
- [ ] Compose service names are DNS names on a shared network.
- [ ] **`depends_on` orders startup, not readiness** — use `condition: service_healthy` or app-side retries.
- [ ] **Never deploy `:latest`** — you can't tell what's running and you can't roll back.
- [ ] Tag with version + git SHA (or digest); push a moving tag but deploy only the immutable one.
- [ ] **Rollback by tag is the fastest recovery action** — keep old images in the registry.
- [ ] Pod = one or more containers sharing network and volumes; **pods are disposable**.
- [ ] Deployment → ReplicaSet → Pods; StatefulSet for stable identity/storage; DaemonSet for per-node agents.
- [ ] Service = stable virtual IP + DNS in front of changing pods; Ingress = L7 routing into Services.
- [ ] **Kubernetes Secrets are base64, not encrypted** — enable encryption at rest and restrict RBAC.
- [ ] Kubernetes is declarative: you submit desired state, controllers reconcile toward it.
- [ ] **Liveness → restart the container. Readiness → remove from Service endpoints. Startup → gate the other two.**
- [ ] **Never put dependency checks in liveness** — a DB blip then restarts your entire fleet at once and prevents recovery.
- [ ] Liveness checks only what a restart can fix; keep it shallow, local, cheap, and unauthenticated.
- [ ] Even in readiness, distinguish hard dependencies from soft ones, or a cache outage takes all endpoints to zero.
- [ ] Use a `startupProbe` for slow JVM boots instead of a huge `initialDelaySeconds`.
- [ ] Spring Boot exposes `/actuator/health/liveness` and `/readiness` and drops readiness during shutdown.
- [ ] **Requests = scheduling guarantee; limits = runtime ceiling.**
- [ ] **Over CPU limit → throttled (latency, no crash). Over memory limit → OOMKilled (exit 137).**
- [ ] Memory is incompressible: set memory limit == request (`Guaranteed` QoS).
- [ ] CPU limits throttle even on an idle node; many teams set CPU requests only.
- [ ] CFS throttling is invisible in CPU-utilisation graphs — check `container_cpu_cfs_throttled_seconds_total`.
- [ ] The cgroup limit covers heap **plus** metaspace, stacks, direct buffers, and JVM overhead.
- [ ] Use `-XX:MaxRAMPercentage=70`, never `-Xmx` equal to the container limit.
- [ ] Exit 137 with no stack trace = OOMKill; `OutOfMemoryError` with a stack trace = JVM heap — opposite fixes.
- [ ] `availableProcessors()` follows the CPU limit and silently sizes GC and ForkJoinPool.
- [ ] `maxUnavailable: 0` + `maxSurge: 1` keeps capacity constant during a roll; readiness makes it safe.
- [ ] **Endpoint removal and SIGTERM happen concurrently** — hence dropped requests on every deploy.
- [ ] A `preStop` sleep (~5 s) lets deregistration propagate before shutdown starts.
- [ ] Full chain: preStop sleep → SIGTERM → stop accepting → drain → flush/close → exit, all inside `terminationGracePeriodSeconds`.
- [ ] PodDisruptionBudgets protect you during node drains and cluster upgrades.
- [ ] HPA measures utilisation **against requests**; scale on the metric that reflects your real bottleneck (queue depth, lag).
- [ ] HPA without Cluster Autoscaler/Karpenter leaves pods `Pending`.
- [ ] `kubectl describe pod` **Events** first: ImagePullBackOff, CrashLoopBackOff, OOMKilled, FailedScheduling.
- [ ] `kubectl logs --previous` gets the crashed container's output; `port-forward` reaches a ClusterIP locally.
- [ ] **Always check your context/namespace before a destructive command.**
- [ ] ECS+Fargate is far simpler and sufficient for most AWS-only workloads; Kubernetes buys portability and ecosystem at a real operational cost.