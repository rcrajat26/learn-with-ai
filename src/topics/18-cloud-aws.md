# 18 — Cloud & AWS

Scope: what a backend engineer is expected to know about running on AWS — the services, the identity
model, the network model, and the failure and cost modes. Depth target: one level below the marketing
page, at the level where you can explain *why* a service behaves the way it does.

---

## 1. Regions, Availability Zones, and why multi-AZ

**Region** — a geographic area (e.g. `eu-west-1` Ireland, `us-east-1` N. Virginia). Regions are
**isolated from each other by design**: separate control planes, separate failure domains. Data does
not move between regions unless you move it, which matters for both resilience and data residency
(GDPR).

**Availability Zone** — one or more discrete data centres within a region, with independent power,
cooling, and networking, physically separated by kilometres but connected by **low-latency (typically
sub-millisecond, single-digit ms worst case) private links**. A region typically has 3–6 AZs.

**Edge locations** — hundreds of PoPs for CloudFront and Route 53, far more numerous than regions.

**Why the AZ construct exists.** It gives you a failure domain that is independent (a power failure,
a flood, a network partition, a fire affects one AZ) but close enough that **synchronous replication
between AZs is practical**. Cross-region synchronous replication is not practical — 80 ms of RTT in
every write is unacceptable — so cross-region is asynchronous, meaning a regional failover can lose
recent writes.

**The design rule: spread every tier across at least two, preferably three, AZs.**
- EC2/ECS/EKS: instances in multiple AZs behind a load balancer (the ALB itself is multi-AZ).
- RDS: Multi-AZ deployment (§9).
- Auto Scaling Group: multiple subnets in multiple AZs, so a lost AZ triggers replacement in another.

**Why three rather than two.** With two AZs, losing one removes 50% of your capacity, so you must run
at 200% to survive — expensive. With three, losing one removes 33%, so 150% suffices. Quorum systems
(etcd, Zookeeper, Kafka with RF=3) *require* three to maintain a majority after losing one.

**Multi-region is a different, much larger commitment**: data replication with conflict resolution,
global routing, cross-region cost, duplicated infrastructure, and a substantially harder operational
model. Justify it with an actual RTO/RPO requirement or a data-residency/latency requirement, not
with "for high availability" — multi-AZ already gives you that. Interviewers respect a candidate who
says "multi-AZ by default; multi-region only when the requirement demands it."

An important caveat to know: AZ names (`eu-west-1a`) are **randomised per account** to spread load, so
your `1a` is not my `1a`. Use AZ *IDs* (`euw1-az1`) when correlating across accounts.

---

## 2. Core services, one level deep

### EC2 — virtual machines
Instance families encode the trade-off: `t` (burstable, CPU credits — great for dev, dangerous for
steady load because you can exhaust credits and get throttled to a fraction of a vCPU), `m`
(balanced), `c` (compute-optimised), `r`/`x` (memory-optimised), `i` (NVMe storage), `g`/`p` (GPU).

Storage: **EBS** is network-attached block storage — persists independently of the instance, snapshot-
able to S3, AZ-scoped (an EBS volume cannot be attached across AZs). **Instance store** is physically
attached NVMe: much faster, and **lost on stop/terminate**. Never put state on instance store.

Pricing models: On-Demand (flexible, expensive), **Spot** (up to 90% off, can be reclaimed with a
2-minute warning — excellent for stateless/batch/CI, unusable for stateful singletons), Reserved
Instances / **Savings Plans** (1–3 year commitment, ~30–70% off — the single biggest cost lever for
steady-state workloads).

**User data** runs at first boot for bootstrapping. **Instance metadata service (IMDS)** at
`169.254.169.254` provides instance identity and, crucially, **temporary role credentials** (§5).
Always use **IMDSv2** (session-token-based); IMDSv1's simple GET was exploitable via SSRF — an
attacker who could make your app fetch an arbitrary URL could steal your instance role's credentials.
That was the mechanism of the 2019 Capital One breach, and it's worth being able to name.

### S3 — object storage, **not a filesystem**

This distinction generates real bugs, so be precise:

| | S3 | Filesystem |
|---|---|---|
| Unit | immutable **object** (key + bytes + metadata) | file with mutable byte ranges |
| Partial write | **impossible** — you replace the whole object | seek and write in place |
| Append | **not supported** | yes |
| Directories | **don't exist** — `a/b/c.txt` is one flat key; "folders" are a console illusion via prefix listing | real hierarchy |
| Rename | **not an operation** — copy then delete (O(size), not O(1)) | atomic metadata change |
| Listing | paginated API call over a prefix; expensive at scale | cheap directory read |
| Consistency | **strong read-after-write** since Dec 2020 (it used to be eventual — old material and old code may still assume otherwise) | strong |

Practical consequences: you cannot append to a log file in S3 (write many objects and compact
instead); a "move" of a 5 GB object costs a full copy; `ListObjects` on a bucket with 10 million keys
is not a lookup mechanism — keep an index in a database.

**Durability** is 11 nines (99.999999999%) via replication across ≥3 AZs — but **durability is not
backup**. S3 will faithfully preserve the empty object you overwrote and the deletion you performed.
Enable **versioning** and, for anything critical, **Object Lock** or cross-region replication.

**Storage classes and lifecycle policies:** Standard → Standard-IA (cheaper storage, per-GB retrieval
fee, 30-day minimum) → Glacier Instant/Flexible/Deep Archive (very cheap, retrieval from
milliseconds to 12 hours). **Intelligent-Tiering** moves objects automatically based on access
patterns for a small monitoring fee — usually the right default when the pattern is unknown.

Lifecycle rules automate it:
```
transition to STANDARD_IA after 30 days
transition to GLACIER_IR   after 90 days
expire                     after 365 days
also: expire noncurrent versions after 30 days
      abort incomplete multipart uploads after 7 days   ← easily-forgotten silent cost
```
That last rule matters: failed multipart uploads leave invisible parts that you pay for indefinitely
and that don't appear in normal listings.

**Presigned URLs** — the pattern to know. Instead of proxying a 500 MB upload through your service
(consuming its bandwidth, memory, threads, and request timeout), generate a time-limited signed URL
and let the client talk to S3 directly:
```java
var presigner = S3Presigner.create();
var presigned = presigner.presignPutObject(r -> r
        .signatureDuration(Duration.ofMinutes(15))
        .putObjectRequest(p -> p.bucket("uploads").key("user/42/" + id)));
return presigned.url();
```
The URL carries your permissions, scoped to one operation, one key, and a short expiry. Use it for
both uploads and downloads of large or private objects. Constrain the content type and size where the
API allows, and keep expiries short — a leaked presigned URL is a valid credential until it expires.

**Security defaults:** buckets are private by default and **Block Public Access** is on by default at
the account level. Public S3 buckets remain a leading cause of data breaches, essentially always
because someone turned that off. Prefer CloudFront with Origin Access Control over making a bucket
public. Enable default encryption (SSE-S3 is now automatic; SSE-KMS when you need key control and
audit).

### RDS / Aurora — managed relational databases
AWS runs the engine (Postgres, MySQL, SQL Server, Oracle, MariaDB): provisioning, patching, backups,
point-in-time recovery, Multi-AZ failover, read replicas, monitoring. You still own schema, indexes,
queries, and connection management.

Key knobs: automated backups with a retention window (PITR to any second in it), maintenance windows
(patching **causes a failover** — plan for it and make your app reconnect cleanly), Performance
Insights for query-level diagnosis, and Parameter Groups for engine config.

**Aurora** is AWS's reimplementation with a distributed storage layer: 6 copies across 3 AZs, faster
failover (~30 s vs 60–120 s), up to 15 low-lag read replicas, and **Aurora Serverless v2** for
autoscaling capacity. More expensive per hour; usually worth it at scale.

**Connection management is the thing backend engineers get wrong.** RDS instances have a
`max_connections` derived from instance memory. With 20 pods × a 10-connection HikariCP pool, you need
200 connections before serving a single request — and a scale-out event can exhaust the limit
instantly, taking down every service sharing the database. Size pools deliberately
(`pods × poolSize < max_connections`, with headroom for maintenance and admin), and use **RDS Proxy**
for Lambda or high-pod-count workloads, since it multiplexes many client connections onto few database
connections.

### Lambda — functions as a service
Event-driven, per-request billing (GB-seconds), automatic scaling, no servers to manage. Concurrency
is per-account with a configurable per-function reserved concurrency.

**Cold start** is the defining characteristic: on the first invocation (and on each scale-out), AWS
must create an execution environment, download your code, and initialise the runtime. For a JVM this
can be **1–10 seconds** — a genuine problem for latency-sensitive APIs. Mitigations: smaller
deployment packages, **Provisioned Concurrency** (pre-warmed environments — but you're now paying for
idle capacity, which undercuts the model), SnapStart for Java (snapshot the initialised JVM and
restore it, cutting cold starts dramatically), or choosing a lighter runtime.

Other constraints: 15-minute max execution, 10 GB memory (CPU scales *with* memory — a memory
increase can make a function cheaper by finishing faster), 512 MB `/tmp` (up to 10 GB configurable),
6 MB synchronous payload, and statelessness (containers are reused, so **globals persist between
invocations** — good for connection reuse and caching, dangerous if you accidentally leak state
between requests).

Good fits: event processing (S3 → Lambda, SQS → Lambda), scheduled jobs, glue code, spiky/unpredictable
traffic, and genuinely low-volume services. Bad fits: sustained high-throughput services (containers
are cheaper past a crossover point), long-running work, anything needing large connection pools
(each concurrent execution is a separate environment with its own connections — hence RDS Proxy), and
strict low-latency APIs.

### SQS and SNS
**SQS** — managed message queue; the mechanics are in topic 14 §9 (visibility timeout,
`maxReceiveCount`, DLQ redrive, long polling, FIFO vs standard).

**SNS** — pub/sub topics. One publish fans out to many subscribers (SQS queues, Lambda, HTTP
endpoints, email, SMS).

**The `SNS → multiple SQS` fan-out pattern is the canonical AWS event architecture** and directly
addresses topic 14 §7's "SQS can't do fan-out": each consumer gets its own queue with its own DLQ,
its own retry policy, and its own consumption rate, and adding a new consumer requires no change to
the producer.

**EventBridge** is the modern evolution: content-based routing rules, schema registry, third-party
SaaS sources, and a scheduler. Prefer it over SNS for new event-driven work when you need routing on
message content.

### ECS / Fargate — containers
**ECS** is AWS's container orchestrator: a **task definition** (the container spec: image, CPU,
memory, environment, IAM role, log config) and a **service** (desired count, load-balancer
registration, deployment configuration, autoscaling).

Two launch types: **EC2** (you manage the instance fleet — cheaper at scale, more control, more work)
and **Fargate** (serverless — you specify CPU/memory per task and AWS runs it; no instances to patch,
scale, or bin-pack; more expensive per unit but frequently cheaper in total once you count
engineering time).

ECS is meaningfully simpler than Kubernetes: no control plane to run, IAM integration is native, and
the concept count is a fraction. See topic 19 §11 for the positioning argument.

### ALB / NLB
**ALB** — L7. Path- and host-based routing, TLS termination with ACM certificates (free, auto-renewing
— a real operational win), HTTP/2 and gRPC, WebSocket support, sticky sessions, target groups with
health checks, and native integration with ECS/EKS/Lambda. The default for HTTP services.

**NLB** — L4. Ultra-low latency, millions of requests/sec, static IPs (which ALB doesn't offer, and
which some corporate firewalls require), TLS passthrough, non-HTTP protocols. See topic 10 §11 for
the L4-vs-L7 consequences — particularly that an NLB in front of gRPC/HTTP-2 pins connections to
backends.

Both are multi-AZ. Enable **cross-zone load balancing** (default on for ALB, off for NLB with a data
transfer charge) or an AZ with fewer targets receives disproportionate load per target.

### Route 53 — DNS
Authoritative DNS with health checks and routing policies: simple, weighted (canary/blue-green traffic
splitting), latency-based, geolocation, failover, and multi-value. **Alias records** solve the
zone-apex CNAME problem (topic 10 §5) and are free for AWS targets.

Remember topic 10's warning: DNS-based failover is slow and unreliable because clients (especially
JVMs) ignore TTLs. Route 53 failover is for region-level disaster recovery, not for instance-level
availability — that's the load balancer's job.

### CloudWatch — metrics, logs, alarms
Metrics (1-minute standard, 1-second high-resolution, 15-month retention), Logs (log groups → streams;
**set a retention policy or you pay to store logs forever** — the default is "never expire", a common
silent cost), Logs Insights for querying, Alarms (thresholds → SNS → PagerDuty/Slack), Dashboards,
and Synthetics for canaries.

Custom metrics cost per metric per month, and **every unique dimension combination is a separate
metric** — putting a user ID or request ID in a dimension produces a five-figure bill (the cardinality
trap; topic 20 §4). CloudWatch is convenient and deeply integrated but expensive and comparatively
weak at high-cardinality querying; many teams add Prometheus/Grafana, Datadog, or Honeycomb alongside.

---

## 3. IAM: users, roles, and policies

**The model:** a **principal** (who) requests an **action** on a **resource**, and IAM evaluates
**policies** to allow or deny.

| Concept | What it is | When to use |
|---|---|---|
| **User** | a permanent identity with long-lived credentials (password, access keys) | humans without SSO; **avoid for applications** |
| **Group** | a collection of users | attach policies once for a team |
| **Role** | an identity with **no permanent credentials**, that can be *assumed* to obtain temporary ones | **applications, services, cross-account access, federated humans** |
| **Policy** | a JSON document listing Effect/Action/Resource/Condition | attached to users, groups, roles, or resources |

### Why roles, and the temporary-credential mechanism

The problem with access keys: they're permanent, they end up in config files and environment
variables and `.env` files and Slack messages and Git history, they don't rotate, and a leak grants
indefinite access.

**How a role actually works on an EC2 instance:**
1. You attach an **instance profile** (a wrapper around a role) to the instance.
2. Your application (via the AWS SDK's default credential provider chain) queries IMDS at
   `169.254.169.253`… precisely, `169.254.169.254/latest/meta-data/iam/security-credentials/<role>`.
3. It receives an **access key, secret key, and session token**, valid for a few hours.
4. **The SDK refreshes them automatically before expiry.** Nothing is ever written to disk.

The same mechanism, different plumbing:
- **ECS task role** — credentials served from a container-local endpoint, per *task*, so different
  containers on the same host get different permissions.
- **Lambda execution role** — injected as environment variables and refreshed by the runtime.
- **EKS IRSA / Pod Identity** — a projected service-account token exchanged via STS for role
  credentials, so permissions are per Kubernetes service account, not per node.
- **Cross-account** — `sts:AssumeRole` into a role in another account that trusts yours.
- **Humans** — SSO/identity federation issuing short-lived role credentials, never static keys.

Result: **no long-lived secrets anywhere**, automatic rotation, per-workload scoping, and a full
CloudTrail audit trail of who assumed what and when. If you take one thing from IAM, take this:
**applications should never have access keys.**

### Policy structure
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadWriteOwnPrefix",
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::my-app-uploads/tenant/${aws:PrincipalTag/tenant}/*",
    "Condition": { "Bool": { "aws:SecureTransport": "true" } }
  }]
}
```

**Evaluation logic — know this order:**
1. An **explicit `Deny` anywhere always wins.** Nothing overrides it.
2. Otherwise, an explicit `Allow` grants access.
3. Otherwise, **implicit deny** (the default is deny everything).

Also in play: **Service Control Policies** (org-level guardrails that cap what any account can do —
they can only restrict, never grant), **permission boundaries** (the maximum permissions an identity
can have, used to delegate role creation safely), and **resource-based policies** (on S3 buckets, SQS
queues, KMS keys — these allow cross-account access without assuming a role).

**Least privilege in practice.** `"Action": "s3:*"` on `"Resource": "*"` is the norm in tutorials and
a finding in review. How to get it right without spending a week: start restrictive, run the workload,
and read the `AccessDenied` errors — each one tells you exactly what's missing. Or use **IAM Access
Analyzer** to generate a policy from actual CloudTrail activity. Then add conditions
(`aws:SourceIp`, `aws:SecureTransport`, `aws:PrincipalTag`, MFA) to tighten further.

Other essentials: enable **MFA** on all human users and always on the root account; **never use root**
for anything but the handful of operations that require it; enable **CloudTrail** in all regions
(this is your audit log and your incident evidence); rotate whatever long-lived keys still exist; and
prefer one AWS account per environment (prod/staging/dev) — account boundaries are the strongest
isolation AWS offers, far stronger than IAM within one account.

---

## 4. VPC basics

A **VPC** is your logically isolated network, defined by a CIDR block (e.g. `10.0.0.0/16` ≈ 65k
addresses). It spans a region.

**Subnets** are CIDR sub-ranges, each pinned to **exactly one AZ**. That's why "spread across AZs"
mechanically means "put your resources in subnets in different AZs."

- **Public subnet** — its route table has a route to an **Internet Gateway**. Resources with a public
  IP here are directly reachable from the internet. Put load balancers, bastions, and NAT Gateways
  here.
- **Private subnet** — no IGW route. Outbound internet goes via a **NAT Gateway** in a public subnet;
  inbound from the internet is impossible. Put application servers, databases, and caches here.

**The standard three-tier layout:** public subnets (ALB) → private app subnets (ECS/EC2) → private
data subnets (RDS, ElastiCache), each replicated across 2–3 AZs. Databases should never be in a public
subnet, and should be reachable only from the app tier's security group.

### Security groups vs NACLs — the comparison that gets asked

| | **Security group** | **Network ACL** |
|---|---|---|
| Attaches to | an **ENI** (instance/task/RDS) | a **subnet** |
| Rules | **allow only** | allow **and deny** |
| State | **stateful** — return traffic is automatically permitted | **stateless** — you must write both directions |
| Evaluation | all rules evaluated; any match allows | rules evaluated **in numbered order**, first match wins |
| Default | deny all inbound, allow all outbound | default NACL allows everything |
| Typical use | the primary control — use these | coarse subnet-level guardrails, explicit IP blocks |

**Stateful vs stateless is the crux.** With a security group, allowing inbound 443 automatically
allows the response out. With a NACL, you must also allow outbound on the **ephemeral port range**
(1024–65535) or replies are silently dropped — and the symptom is a connection that establishes and
then hangs, which is baffling if you don't know the mechanism.

**Security groups can reference other security groups**, which is the idiomatic pattern and much
better than CIDR ranges:
```
sg-alb:   inbound 443 from 0.0.0.0/0
sg-app:   inbound 8080 from sg-alb          ← not an IP range; follows autoscaling automatically
sg-rds:   inbound 5432 from sg-app
```
This expresses intent, survives IP changes and scaling events, and reads as documentation.

**VPC Endpoints** let private resources reach AWS services without traversing a NAT Gateway:
- **Gateway endpoints** (S3, DynamoDB) — free, a route-table entry. **Always create these**; without
  one, all S3 traffic from private subnets goes through the NAT Gateway and you pay per-GB processing
  for traffic that never needed to leave AWS's network. This is one of the most common avoidable
  costs in an AWS bill.
- **Interface endpoints** (PrivateLink, for most other services) — an ENI in your subnet; costs per
  hour plus per GB, but usually still cheaper than NAT and better for security posture.

Other pieces: **VPC Peering** (1:1, non-transitive, no overlapping CIDRs), **Transit Gateway** (hub
for many VPCs and on-prem), **VPC Flow Logs** (connection-level logging — invaluable for debugging
"why can't A reach B", where the answer is a security group or route table roughly every time).

---

## 5. The managed-service trade-off

**Managed gives you:** operational work you don't do (patching, backups, failover, scaling,
monitoring), a well-tested HA story, an SLA, faster delivery, and less on-call surface. That last one
is the real value — the cost of a self-managed database is not the EC2 bill, it's the engineer who
gets paged at 3am for a failed failover.

**Managed costs you:** money (typically 2–5× the raw compute), control (you can't install that
extension, tune that kernel parameter, or run that version), a slower upgrade cadence, lock-in
proportional to how proprietary the service is, and opaque debugging (you can't strace a managed
service).

**Where to draw the line, practically:**
- **Always managed:** databases (RDS/Aurora/DynamoDB), queues (SQS), object storage (S3), DNS
  (Route 53), certificates (ACM), secrets (Secrets Manager), load balancers. Running these yourself
  is almost never a good use of a backend team.
- **Usually managed:** Kafka (MSK), Redis (ElastiCache), Kubernetes control plane (EKS), search
  (OpenSearch).
- **Self-manage when:** you have specific requirements the managed version can't meet, you're at a
  scale where the multiple is millions of dollars, you need multi-cloud portability as a real
  requirement, or you already have deep expertise and the ops cost is genuinely marginal.

**On lock-in:** it's a spectrum, not a binary. S3 and SQS have simple, widely-cloned APIs — porting is
work but not a rewrite. Step Functions, DynamoDB single-table designs, and deep IAM integration are
much stickier. Trading some lock-in for real velocity is usually correct for a startup or a product
team; be deliberate about it rather than accidental, and keep the *business logic* free of vendor
types even where the infrastructure isn't.

---

## 6. Configuration and secrets

**The twelve-factor rule:** configuration that varies by environment lives in the environment, not in
the code. Same artefact — the same container image, the same JAR — promoted from dev to staging to
prod, with only configuration differing. If you rebuild per environment, you're testing one artefact
and shipping another.

**Where config goes:**
- **Environment variables** — universal, simple, works everywhere. Fine for non-secret config.
- **SSM Parameter Store** — hierarchical (`/myapp/prod/db/host`), versioned, IAM-controlled. Standard
  parameters are **free**; SecureString parameters are KMS-encrypted. Excellent default for
  configuration and adequate for many secrets.
- **Secrets Manager** — like Parameter Store but with **automatic rotation** (native for RDS
  credentials, Lambda-driven for anything else), cross-region replication, and a per-secret monthly
  charge. Use it where rotation matters, especially database credentials.
- **AppConfig** — validated, gradually-rolled-out dynamic configuration with automatic rollback. For
  config you change at runtime, like feature flags.

**Rule of thumb:** Parameter Store for config and low-churn secrets, Secrets Manager where you need
rotation. Don't put secrets in plain environment variables in a task definition — they're visible to
anyone with `ecs:DescribeTaskDefinition`, they appear in the console, and they get captured in
CloudTrail and error reports. Both ECS and Lambda support injecting secrets **by ARN** at runtime,
which resolves them at start without storing the value in the definition.

```yaml
# ECS task definition — the correct way
secrets:
  - name: DB_PASSWORD
    valueFrom: arn:aws:secretsmanager:eu-west-1:123456789012:secret:prod/db-AbCdEf
environment:
  - name: SPRING_PROFILES_ACTIVE
    value: prod
```

**Never in Git.** See topic 17 §13 for what to do when it happens anyway — rotate first, clean second.
And note that a secret fetched at startup and cached forever defeats rotation: either fetch on a TTL,
or handle the auth failure by re-fetching.

---

## 7. Scaling and the statelessness requirement

**Vertical (scale up)** — a bigger instance. Simple, no code changes, and the right first move
surprisingly often (many "we need to scale out" situations are one instance size or one index away
from resolution). Limits: a hard ceiling, requires downtime or a failover to change, and cost grows
super-linearly at the top end.

**Horizontal (scale out)** — more instances. Effectively unbounded, gives you fault tolerance as a
side effect, and enables rolling deploys. Requires the application to be **stateless**, and adds
distributed-systems problems (topics 14 and 15 exist largely because of it).

### What "stateless" actually requires

An instance must be replaceable at any moment with no user-visible effect. Four things commonly break
this, and you should be able to list all four:

1. **Sessions in local memory.** User logs in on pod A; the load balancer routes their next request to
   pod B; they're logged out. *Fix:* externalise to Redis/ElastiCache (Spring Session does this
   transparently) or use stateless JWTs. Sticky sessions are a crutch — they break on deploy, on
   scale-in, and on instance failure, and they defeat even load distribution.
2. **Files on local disk.** Uploads written to `/tmp` exist on one instance only, and vanish on
   restart or scale-in. *Fix:* S3, with presigned URLs so the file never transits your service (§2).
   For genuinely shared filesystem semantics, EFS — but ask hard whether you actually need it.
3. **In-process caches diverging.** Each instance has a different view (topic 15 §7). *Fix:*
   distributed cache, or accept short-TTL divergence deliberately.
4. **Scheduled jobs running on every instance.** N replicas run the job N times (topic 14 §12).
   *Fix:* idempotency, a distributed lock, a leader, or a dedicated scheduler.

Also: in-memory rate limiters (each instance counts separately, so your limit is silently N×),
in-memory WebSocket connection registries (topic 10 §14), and startup work that assumes it's the only
instance (a migration, a seed).

**Auto Scaling.** Target-tracking on CPU or request-count-per-target is the usual mechanism; also
schedule-based for known patterns and predictive for learned ones. Two things to get right: **scale
out fast, scale in slow** (a premature scale-in during a lull causes a second scale-out event and
churn), and account for **warm-up time** — if a JVM takes 90 seconds to start and warm its cache
(topic 15 §13), a CPU-triggered scale-out arrives 90 seconds *after* you needed it. Provision headroom
accordingly, and keep startup fast because startup time is a scaling parameter.

Watch out for scaling something whose bottleneck is elsewhere: doubling the app tier when the database
is saturated makes things strictly worse by adding connections and load.

---

## 8. Cost awareness

Cost is an engineering property, and being able to reason about it is a seniority signal.

**The top surprises, in rough order of frequency:**

1. **Data transfer.** Compute is what you notice; egress is what gets you.
   - Internet **egress**: ~$0.09/GB. Ingress is free.
   - **Cross-AZ traffic: charged in both directions** (~$0.01/GB each way). A chatty microservice mesh
     spread across three AZs pays for a large share of its own internal traffic. This is the tension
     with the multi-AZ resilience rule, and the answer is usually AZ-aware routing for high-volume
     internal chatter, not fewer AZs.
   - Cross-region: significantly more.
   - Within an AZ, between instances using private IPs: free.
2. **NAT Gateway.** ~$0.045/hour *plus* ~$0.045/GB processed. Terabytes of S3 traffic through a NAT
   Gateway is a five-figure annual line item that a **free S3 Gateway Endpoint** eliminates entirely
   (§4). Check this on any account you inherit.
3. **Forgotten resources.** Unattached EBS volumes (you pay for the volume, not the attachment), old
   snapshots, idle load balancers (~$16–20/month each, even with zero traffic), unassociated Elastic
   IPs (charged precisely *because* they're idle), oversized dev/test environments running 24/7,
   CloudWatch log groups with no retention policy, and abandoned dev accounts. These are individually
   small and collectively enormous.
4. **Over-provisioning.** Instances sized for a peak that never comes, RDS at 8% CPU, and — very
   commonly — **CloudWatch custom metrics and logs**, where high-cardinality dimensions produce
   thousands of billed metrics from one line of code.
5. **No commitment discounts.** Steady-state workloads on On-Demand pricing pay 30–70% more than
   necessary. Savings Plans are the easiest large win available.
6. **Per-request services at high volume.** Lambda, API Gateway, and Step Functions are wonderfully
   cheap at low volume and can exceed container costs past a crossover point. Do the arithmetic before
   the architecture is fixed.

**Practices:** tag everything (`Environment`, `Team`, `Service`, `CostCentre`) and enforce it, so Cost
Explorer can attribute spend to an owner; set **budgets with alerts**; review the Cost Explorer
top-10 monthly; use S3 lifecycle policies (§2) and CloudWatch log retention; run non-production on a
schedule (nights and weekends off is a ~65% saving); use Spot for CI, batch, and anything stateless;
and use Compute Optimizer / Trusted Advisor for rightsizing recommendations.

The framing to use in an interview: **cost is a design constraint like latency.** "We chose X over Y
because it was 3× cheaper at our volume and the latency difference didn't matter" is a strong,
senior-sounding statement.

---

## 9. RDS Multi-AZ vs read replicas — a comparison worth having crisp

These are constantly confused, and the confusion is diagnostic.

| | **Multi-AZ** | **Read replica** |
|---|---|---|
| Purpose | **availability** | **read scaling** |
| Replication | synchronous (standard Multi-AZ) | **asynchronous** |
| Standby serves traffic? | **No** — the standby is invisible and idle (Multi-AZ *cluster* deployments are the exception: two readable standbys) | Yes — read-only queries |
| Failover | automatic, 60–120 s (Aurora ~30 s); the **DNS endpoint** flips to the standby | manual promotion, and the promoted replica becomes an independent database |
| Data loss on failover | none (synchronous) | possible — replica lag |
| Cross-region | no (same region) | **yes** — a disaster-recovery option |
| Cost | ~2× (you pay for the standby) | per replica |

**They solve different problems and are commonly used together:** Multi-AZ for the primary's
availability, plus read replicas for reporting and read-heavy endpoints.

**Read-replica gotchas your application must handle:**
- **Replication lag** means read-after-write inconsistency: a user saves a profile, is routed to a
  replica, and sees the old data. Route reads that must be fresh to the primary (Spring's
  `@Transactional(readOnly = true)` with a routing DataSource is the common pattern), or hold the user
  on the primary briefly after a write.
- Lag grows under heavy write load or a long-running query on the replica — precisely when you're
  relying on it. Monitor `ReplicaLag` and alert on it.
- Failover is **DNS-based**, which brings the JVM DNS-cache problem from topic 10 §3 straight back:
  set `-Dsun.net.inetaddr.ttl` to something small, or your app keeps connecting to the old primary
  after failover. Also ensure your connection pool detects and discards broken connections
  (HikariCP's validation query and `maxLifetime`).
- Reads on a replica can see a snapshot older than a write your own request just made — always ask
  whether the endpoint tolerates that before routing it.

---

## Atomic concept checklist

- [ ] Region = isolated geography; **AZ = independent failure domain within a region**, close enough for synchronous replication.
- [ ] Cross-region replication must be asynchronous, so regional failover can lose recent writes.
- [ ] Spread every tier across 2–3 AZs; **three AZs means losing one costs 33%, not 50%**, and quorum systems need it.
- [ ] Multi-region is a much bigger commitment — justify it with RTO/RPO, residency, or latency, not "HA".
- [ ] AZ names are randomised per account; use AZ IDs to correlate.
- [ ] EC2: `t` instances burst on credits and throttle when exhausted; EBS persists, **instance store does not**.
- [ ] Spot for stateless/batch (2-minute reclaim warning); Savings Plans are the biggest steady-state cost lever.
- [ ] Use **IMDSv2** — IMDSv1 + SSRF is how instance-role credentials get stolen (Capital One).
- [ ] **S3 is object storage, not a filesystem**: no append, no partial write, no real directories, rename = copy + delete.
- [ ] S3 is strongly read-after-write consistent since Dec 2020; older material says otherwise.
- [ ] 11 nines of durability is **not backup** — enable versioning; S3 faithfully preserves your mistakes.
- [ ] Lifecycle rules: transition to IA/Glacier, expire noncurrent versions, and **abort incomplete multipart uploads**.
- [ ] **Presigned URLs** let clients upload/download directly, keeping large payloads out of your service.
- [ ] Buckets are private by default; public buckets are a leading breach cause — use CloudFront + OAC.
- [ ] RDS manages the engine; you still own schema, queries, and **connection count** (`pods × poolSize < max_connections`).
- [ ] RDS Proxy multiplexes connections — essential for Lambda and high pod counts.
- [ ] Aurora: 6 copies over 3 AZs, ~30 s failover, up to 15 replicas.
- [ ] Lambda **cold starts** are 1–10 s for a JVM; mitigate with Provisioned Concurrency or SnapStart.
- [ ] Lambda limits: 15 min, 10 GB memory (CPU scales with it), 6 MB sync payload; globals persist across invocations.
- [ ] **SNS → multiple SQS** is the canonical fan-out, giving each consumer its own queue, DLQ, and pace.
- [ ] EventBridge adds content-based routing and is the modern default for event routing.
- [ ] ECS = task definition + service; **Fargate removes instance management** at a higher unit price.
- [ ] ALB = L7 (path/host routing, ACM certs, gRPC, WebSocket); NLB = L4 (static IPs, ultra-low latency, passthrough).
- [ ] Enable cross-zone load balancing or unevenly-populated AZs overload their targets.
- [ ] Route 53 Alias records solve the zone-apex CNAME restriction and are free for AWS targets.
- [ ] CloudWatch log groups default to **never expire** — set retention or pay indefinitely.
- [ ] Every unique CloudWatch dimension combination is a **separately billed metric** — never put IDs in dimensions.
- [ ] IAM: **roles for applications, users only for humans without SSO.**
- [ ] Role mechanism: SDK fetches **temporary credentials** from IMDS / the ECS endpoint / STS and auto-refreshes them — nothing on disk.
- [ ] EKS uses IRSA/Pod Identity to scope permissions per service account rather than per node.
- [ ] Policy evaluation: **explicit Deny > explicit Allow > implicit deny.**
- [ ] SCPs cap permissions org-wide and can only restrict; resource-based policies enable cross-account access.
- [ ] Build least privilege by starting restrictive and reading `AccessDenied`, or generating from CloudTrail with Access Analyzer.
- [ ] Enable MFA, never use root, enable CloudTrail everywhere, and separate environments by **account**.
- [ ] A subnet lives in exactly one AZ — that's the mechanics behind "spread across AZs".
- [ ] Public subnet = IGW route; private subnet = NAT for egress, no inbound from the internet.
- [ ] **Security groups are stateful and allow-only; NACLs are stateless and support deny.**
- [ ] A NACL requires an explicit ephemeral-port outbound rule or replies are dropped — connection establishes then hangs.
- [ ] Security groups should reference other security groups, not CIDRs.
- [ ] **S3/DynamoDB Gateway Endpoints are free** and remove NAT Gateway processing charges — always create them.
- [ ] VPC Flow Logs answer "why can't A reach B" (almost always a security group or route table).
- [ ] Managed services buy operational time and an SLA; they cost money, control, and some lock-in.
- [ ] Always managed: databases, queues, S3, DNS, certificates, secrets, load balancers.
- [ ] Same artefact across environments; configuration comes from the environment (twelve-factor).
- [ ] Parameter Store for config (standard params are free); Secrets Manager where **rotation** matters.
- [ ] Inject secrets **by ARN** in ECS/Lambda — plain env vars in a task definition are visible via the API.
- [ ] A secret cached forever at startup defeats rotation.
- [ ] Vertical scaling is underrated as a first move; horizontal scaling requires statelessness.
- [ ] Statelessness breaks on: local sessions, local files, in-process caches, per-instance scheduled jobs.
- [ ] Also: in-memory rate limiters silently multiply the limit by N, and WebSocket registries need a backplane.
- [ ] Sticky sessions are a crutch that fails on deploy, scale-in, and instance loss.
- [ ] Scale out fast, scale in slow; **startup + warm-up time is a scaling parameter.**
- [ ] Don't scale the tier that isn't the bottleneck — more app pods against a saturated DB makes it worse.
- [ ] Cost surprises: **cross-AZ transfer is charged both ways**, NAT Gateway per-GB, forgotten EBS/EIP/ALB/log groups.
- [ ] Tag everything, set budget alerts, schedule non-prod off, use Spot for CI/batch, buy Savings Plans.
- [ ] Per-request services (Lambda/API Gateway) cross over to being more expensive than containers at volume.
- [ ] **Multi-AZ = availability (synchronous, idle standby, automatic failover); read replica = read scaling (asynchronous, promotable).**
- [ ] Replica lag causes read-after-write inconsistency — route must-be-fresh reads to the primary.
- [ ] RDS failover is DNS-based, so the **JVM DNS cache** can pin you to the old primary; set a short TTL and validate pooled connections.