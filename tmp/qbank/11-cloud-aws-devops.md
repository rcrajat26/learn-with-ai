# 11 — Cloud, AWS & DevOps

**What this decides:** the on-ramp length for the prep plan's AWS portfolio
projects (Project 1 assumes you can navigate an AWS account), whether Docker
needs a from-scratch session, and whether observability literacy is a gap.
L2 overall is the healthy 3–4 YOE line here.

---

## Ladder

### Q1 [L1] rapid-fire — Cloud vocabulary
(a) Region vs Availability Zone — and why an app spans AZs. (b) One-liners:
EC2, S3, RDS, Lambda, SQS, IAM. (c) What does "managed service" actually
buy you?
**Strong answer:** region = geographic area of multiple isolated DCs (AZs);
multi-AZ = survive a DC failure. Correct one-liners (S3 = object storage,
NOT a filesystem; Lambda = event-triggered functions, no server management).
Managed = provider runs patching/backups/failover; you trade control + cost.
**Score:** 1 if ≤1 slip.

### Q2 [L2] explain-back — IAM: users vs roles vs policies
Why does an EC2/ECS service use a ROLE rather than an access key in config?
**Strong answer:** user = permanent identity + long-lived credentials; role
= assumable identity with TEMPORARY auto-rotated credentials; policies =
JSON permission docs attached to either. Services assume roles via instance
profile/task role → no static secrets to leak or rotate. Least-privilege as
the design principle. The no-static-keys rationale is the point.

### Q3 [L2] explain-back — Image vs container, and why not a VM?
What is a Docker image made of, what's a container, and what's the actual
difference from a VM?
**Strong answer:** image = immutable stack of layers (each Dockerfile
instruction) + metadata; container = running instance with a writable layer
on top, isolated via namespaces/cgroups sharing the host KERNEL; VM ships a
whole guest OS on a hypervisor — heavier, slower to start. Layer caching as
the build-speed mechanism. "Lightweight VM" without the shared-kernel
correction = 0.5.

### Q4 [L3] spot-the-bug — Read this Dockerfile
```dockerfile
FROM openjdk:latest
COPY . /app
WORKDIR /app
RUN ./mvnw package
ENV DB_PASSWORD=prodSecret123
EXPOSE 8080
CMD ["java", "-jar", "target/service.jar"]
```
Find ≥4 problems.
**Strong answer (any 4):** `latest` tag — unreproducible builds; secret baked
into the image (visible via `docker history`/inspect — inject at runtime);
`COPY . ` before build → any file change busts the dependency cache (copy
pom first, resolve deps, then copy src) + likely no `.dockerignore`;
running as root; fat image — no multi-stage build (JDK + sources shipped to
prod instead of JRE + jar); no healthcheck. Each with the WHY.

### Q5 [L2] scenario — Deploy literacy (about YOUR job)
Walk through, concretely, what happens between `git push` on your current
project and your code serving production traffic. Where would you look when
a deploy fails?
**Strong answer:** scored on SPECIFICITY about your real pipeline: CI
triggers → build/test stages → artifact/image → registry → deploy mechanism
(k8s/ECS/VM/PaaS — whatever yours is) → traffic shift → where logs/status
live for each stage. Vague ("Jenkins does something, then it's live") = 0.5
and IS ITSELF A FINDING — record "deploy pipeline literacy" as a gap.

### Q6 [L3] explain-back — Config & secrets
Same image must run in staging and prod with different DB endpoints and
credentials. How? Where do secrets live, and name two places they must
NEVER be.
**Strong answer:** build once, configure at runtime — env vars / mounted
config / config service per 12-factor; secrets in a secret manager
(Secrets Manager/Vault/k8s secrets) injected at runtime, rotated; never in:
git, image layers, logs, client-side code. Bonus: Spring profiles map onto
this (ties to 04).

### Q7 [L2] explain-back — Stateless services & scaling
Horizontal vs vertical scaling; what does "stateless" require you to evict
from the service, and where does that state go?
**Strong answer:** vertical = bigger box (limit + restart risk); horizontal
= more instances behind an LB — requires statelessness: no in-memory
sessions (→ Redis/token), no local file writes (→ S3), no in-process
caches you can't afford to lose, no scheduled jobs assuming one instance
(ties to 09 checklist). Naming ≥2 concrete state evictions = 1.

### Q8 [L3] explain-back — Health checks & graceful shutdown
Liveness vs readiness — what does each answer, and what goes wrong if you
conflate them? Tie in the SIGTERM flow from 07/Q12.
**Strong answer:** liveness = "am I stuck? → restart me"; readiness = "can I
take traffic? → route to me". Conflation bug: failing liveness during a slow
dependency → restart storm of healthy pods (readiness should fail instead).
Deploy flow: readiness off → LB drains → SIGTERM → finish in-flight → exit.
Bonus: what a health endpoint should actually check (own deps, shallow vs
deep checks).

### Q9 [L4] discriminator — Logs vs metrics vs traces
When do you reach for each? What would you put on a dashboard and what
would you ALERT on for a payments API?
**L1 tier:** definitions. **L4 tier (=1.0):** logs = per-event detail for
forensics; metrics = cheap aggregates for trends/alerts; traces = one
request's path across services (correlation/trace ids tie back to 10/Q10).
Alert on SYMPTOMS users feel (error rate, p99 latency, queue age) not causes
(CPU); p99 vs average — averages hide tail pain; dashboard: RED
(rate/errors/duration) + saturation; alert fatigue as a real failure mode.

### Q10 [L4] scenario — 3 a.m. on-call
Pager: 5xx rate on your service jumped from 0.1% → 8%. First 15 minutes,
concretely.
**Strong answer:** acknowledge + check blast radius (all endpoints or one?
all instances or one?) → WHAT CHANGED (deploy? flag? dependency? traffic
spike?) — rollback first if a deploy correlates, diagnose later → check
saturation (pool exhaustion, memory, connections) and downstream health
(is it us or a dependency?) → mitigate (rollback/scale/circuit-break/shed)
BEFORE root-causing → communicate status. The mitigate-before-diagnose
instinct + rollback-on-correlation is the L4 signal. "Start reading logs
line by line" as step one = 0.5.

---

## Breadth checklist (rate 0–3)

- [CORE] AWS console/CLI — ever actually deployed/touched anything yourself (vs it being "the DevOps team's job")?
- [CORE] docker build / run / logs / exec — hands-on
- [CORE] docker-compose — spun up a local stack (app + DB)?
- [CORE] Written or meaningfully edited a CI config (GitHub Actions / GitLab CI / Jenkins)
- [CORE] tail -f / grep through prod (or prod-like) logs yourself
- [CORE] Environment promotion concept (dev → staging → prod) and what differs
- Kubernetes vocabulary: pod / deployment / service — used, or words only?
- Load balancer config exposure (ALB/nginx — target groups, health check paths)
- DNS records: A vs CNAME; ever pointed a domain at something?
- Terraform/CDK/CloudFormation — heard/read/written?
- CloudWatch or Grafana/Prometheus/Datadog — built a dashboard or alert yourself?
- SSH into a box and diagnose (ties to 07/Q11) — done it on a real incident?
- Blue/green or canary deploys (heard of? seen one?)
- Feature flags — used a system (LaunchDarkly/homegrown)?
- Cost awareness: roughly what does your service cost to run? (honest "no idea" is a common, notable gap)
- Backups/restore: has your team ever TESTED a restore? (heard-of level fine)
- CDN / S3 static hosting exposure
- Serverless: written a Lambda (any language)?
