# Syllabus — 18 Cloud & AWS

**Target version baseline.** Every quota, default, price, constant, API shape and class name below is
stated against this set of releases, and every leaf that depends on a version says so:

| Layer | Release / date this file targets |
|---|---|
| AWS platform | **AWS as documented September 2026**, including re:Invent 2025 (1–5 Dec 2025) GA'd services |
| AWS SDK for Java | **v2.x** (`software.amazon.awssdk`, current 2.5x line). v1 (`com.amazonaws`) reached **end of support 31 Dec 2025** |
| Spring Cloud AWS | **4.0.x** (Spring Boot 4.0.x / Spring Framework 7.0.x / Spring Cloud 2025.1.x); **3.4.x** is the last Boot 3.5.x line |
| Java runtime | **Java 21** for all code; Lambda managed runtimes `java21` and `java25` |
| Lambda | Durable Functions, MicroVMs, Managed Instances, self-managed S3 code storage all GA |
| S3 | Conditional writes (`If-None-Match`/`If-Match`), conditional copy, 50 TB max object, Express One Zone, S3 Tables, S3 Vectors |
| RDS/Aurora | Multi-AZ DB cluster (3 instances, Raft), Blue/Green deployments, **Aurora DSQL GA (27 May 2025)** incl. multi-Region |
| EC2 | Graviton4 (`*8g`) GA, **Graviton5 (`M9g`/`C9g`) GA 2026**; IMDSv2-only default for new instance types since mid-2024 |
| Containers | **ECS Managed Instances** and **ECS Express Mode** (re:Invent 2025), EKS Auto Mode, EKS Pod Identity |
| Observability | CloudWatch Application Signals + Transaction Search; **X-Ray SDKs in maintenance mode, OpenTelemetry/ADOT is the recommended path** |
| Certification frame | SAA-C03 domain weights (Secure 30 / Resilient 26 / High-Performing 24 / Cost-Optimized 20) used only as a completeness probe |

**The seventeen deltas that most often produce a stale answer in an interview**, all marked
`[VERSION-TRAP]` inline:

1. **`gp3` now does 80,000 IOPS and 2,000 MiB/s, not 16,000 IOPS and 1,000 MiB/s.** Volume size to
   64 TiB. `io2` Block Express does **256,000 IOPS / 4,000 MiB/s** at **99.999% durability** — an
   order of magnitude above the "16,000 / 64,000" numbers every older cheat sheet repeats.
2. **S3 has been strongly read-after-write consistent since December 2020**, for all operations
   including LIST. Any answer mentioning "eventual consistency for overwrite PUTs and DELETEs" is
   describing a platform that no longer exists.
3. **S3 has conditional writes.** `If-None-Match: *` (Aug 2024) gives compare-and-swap create;
   `If-Match: <etag>` gives optimistic-concurrency overwrite; conditional copy landed 2025. "S3 has
   no atomic operations, you need DynamoDB for a lock" is now false.
4. **S3 single objects go to 50 TB** (re:Invent 2025), up from 5 TB. Multipart part count is still
   10,000 and minimum part size still 5 MiB (last part exempt).
5. **The 3,500 PUT / 5,500 GET per second figure is per *partitioned prefix*, not per bucket**, and
   there is no limit on the number of prefixes. The old "randomise your key prefix with a hash" advice
   was obsoleted in July 2018 when S3 added automatic prefix partitioning.
6. **Lambda burst concurrency is 1,000 execution environments every 10 seconds *per function*** —
   not the old flat "500/1000/3000 per region per minute" burst pool. Account concurrency default
   is still 1,000, and new accounts now start with a *reduced* quota that AWS raises automatically.
7. **Lambda SnapStart supports Java 11/17/21 on both x86_64 and arm64, and costs nothing extra.**
   Java 21 cold start drops from roughly 800–1,500 ms to 50–90 ms. "Use Provisioned Concurrency for
   Java" is a pre-2022 answer that costs real money.
8. **Lambda is no longer only 15 minutes.** Lambda **Durable Functions** persist execution state and
   checkpoints; **Lambda MicroVMs** run up to **8 hours (28,800 s)**. The 900-second ceiling still
   applies to a classic function invocation.
9. **API Gateway REST APIs can exceed 29 seconds.** Since June 2024 Regional and private REST APIs
   can be raised via Service Quotas to **300 seconds**; edge-optimized cannot, and HTTP APIs remain
   a hard **30 s**.
10. **The first 100 GB/month of internet egress is free** across most regions, per account. The
    "$0.09/GB from byte one" answer overstates small-workload cost.
11. **Kafka-style "RDS Multi-AZ means an idle standby" is only half true.** The **Multi-AZ DB cluster**
    deployment (MySQL/PostgreSQL) runs one writer plus **two readable standbys** across three AZs
    over a Raft-based protocol, and fails over in **under 35 seconds**.
12. **Aurora DSQL exists and is GA** (27 May 2025): serverless, active-active multi-Region, strongly
    consistent, PostgreSQL-*compatible* but with hard limits — Repeatable Read only, one DDL per
    transaction, **3,000 rows modified per transaction**, 1-hour connection lifetime, no triggers, no
    PL/pgSQL, no extensions, no sequences, no temp tables, no `LISTEN`/`NOTIFY`.
13. **EKS IRSA is no longer the default answer.** **EKS Pod Identity** removes the per-cluster OIDC
    provider and the trust-policy JSON, uses a node-local agent instead of a projected token file,
    supports role session tags, and is built into EKS Auto Mode. IRSA survives for EKS Anywhere,
    ROSA and self-managed clusters.
14. **ECS is not just EC2-vs-Fargate any more.** **ECS Managed Instances** (AWS provisions and patches
    the EC2 fleet, you keep EC2 pricing) and **ECS Express Mode** (image + two IAM roles → Fargate +
    ALB + HTTPS + autoscaling + an `*.ecs.*.on.aws` URL, up to 25 services per ALB) both shipped at
    re:Invent 2025.
15. **X-Ray SDKs are in maintenance mode.** AWS's recommended instrumentation is OpenTelemetry via
    ADOT, with the X-Ray **OTLP endpoint** and **CloudWatch Transaction Search** for 100% span
    retention. "Add the X-Ray SDK and `@XRayEnabled`" is the legacy path.
16. **AWS SDK for Java v1 is end-of-support** (31 Dec 2025). Any answer using `com.amazonaws.services.s3.AmazonS3`
    dates the candidate. v2's `S3Client`/`S3AsyncClient`, the CRT-based S3 client and
    `AwsCrtAsyncHttpClient` are the current surface.
17. **CloudWatch Logs no longer defaults to "never expire" in every path** — but a log group created
    without an explicit retention still can, and Logs is now priced across several classes
    (Standard vs Infrequent Access). Custom metrics remain **$0.30/metric/month for the first 10,000**,
    and every unique dimension combination is still a separate billed metric.

**Scope boundary against the sibling guides.** This file owns **the platform**: what AWS actually
runs, what each primitive guarantees, what it costs, how identity and the network are modelled, and
how a Java service is wired into it. Owned elsewhere:

- Broker semantics — visibility timeout, `maxReceiveCount`, DLQ redrive, FIFO ordering, consumer
  groups, outbox, saga, idempotent consumers — live in `14-messaging-queues.md`. This guide owns
  SQS/SNS/EventBridge/Kinesis/MSK as **AWS primitives**: IAM, VPC endpoints, KMS, quotas, ESM
  wiring, and cost. `[X-REF 14]`
- Cache strategy, eviction policy, stampede prevention, Redis data structures and the Spring Cache
  abstraction live in `15-caching.md`. This guide owns **ElastiCache/MemoryDB/DAX as managed
  services** and CloudFront as an edge cache. `[X-REF 15]`
- Isolation levels, MVCC, index selection, query plans and deadlocks live in `09-sql-databases.md`.
  This guide owns RDS/Aurora/DynamoDB as **operated services**. `[X-REF 09]`
- TCP, TLS, HTTP/1.1 vs 2 vs 3, DNS mechanics, keep-alive, connection pooling, timeouts and retries
  live in `10-networking.md`. This guide owns what AWS's implementations of those change. `[X-REF 10]`
- Container images, layers, Dockerfile discipline for the JVM, Kubernetes objects, probes, HPA and
  CrashLoopBackOff live in `19-docker-kubernetes.md`. This guide owns **ECS/Fargate/EKS as AWS
  products** and the positioning argument between them. `[X-REF 19]`
- The three pillars, structured logging, Micrometer, Prometheus, SLI/SLO, alert design and postmortem
  practice live in `20-observability-operations.md`. This guide owns **CloudWatch/X-Ray/CloudTrail as
  services**, their data models, and their cost model. `[X-REF 20]`
- AuthN vs AuthZ, OAuth 2.x/OIDC flows, JWT, password storage, the OWASP Top 10, CORS, CSRF and TLS
  configuration live in `13-web-security.md`. This guide owns **IAM, KMS, Secrets Manager, Cognito
  and the AWS-specific attack surface** (SSRF→IMDS, confused deputy, public buckets). `[X-REF 13]`
- Heap sizing, GC, container memory flags, `MaxRAMPercentage`, JIT warmup and heap dumps live in
  `06-jvm-internals.md`. This guide owns what Lambda/Fargate memory settings do to them. `[X-REF 06]`
- Rate limiting as an API contract, `Idempotency-Key`, pagination and status-code choice live in
  `12-api-design.md`. This guide owns API Gateway's *implementation* of throttling and usage plans.
  `[X-REF 12]`
- CAP/PACELC, consistent hashing, quorum arithmetic, the scale-up ladder, back-of-envelope sizing
  and multi-region as an architecture decision live in `22-system-design.md`. This guide owns the
  AWS-shaped version of each. `[X-REF 22]`
- `@Transactional`, the proxy model, Boot auto-configuration and `@ConfigurationProperties` live in
  `07-spring-core.md`. This guide owns the Spring Cloud AWS auto-configurations. `[X-REF 07]`
- Testcontainers mechanics, test slices, contract testing and flaky tests live in `16-testing.md`.
  This guide owns **LocalStack, `LocalStackContainer`, and what an AWS integration test can and
  cannot prove**. `[X-REF 16]`
- HikariCP sizing, connection validation and `maxLifetime` live in `08-spring-data-jpa.md` and
  `09-sql-databases.md`. This guide owns the `pods × poolSize < max_connections` arithmetic and RDS
  Proxy. `[X-REF 08]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

**Every example, service name, status code and number comes from the QuizStakes domain in
`src/scenario/scenario.md`.** The AWS surfaces the bible must design against are Appendix B's
platform mapping: `ApplicationGateway` (2 GB heap, 12→40 instances, autoscaled), `RouterInt`
(HAProxy or equivalent), `JwtService`, `ClientRestrictions` (4 GB × 8, 30 ms budget on every money
path), `AccountOpening`/`AccountActivation`/`AccountMaintenance`, `DocumentVerification` (8 GB × 6,
2–6 MB image buffers → object storage), `ScreeningService`, `BankDeposits` (file-arrival trigger →
worker pool, idle 23 hours a day), `BankWithdrawal` (scheduled run job, single leader, 4 windows/day),
`FundsLedger` (12 GB × 3, deliberately **not** function-based), `BonusService`, `InternalPlatforms`
(session-affine, operator-facing), and the read models `BalanceView`/`ProfileService`/`PendingActions`.
Never `my-bucket`, `foo-service`, `example.com` or `Dog extends Animal`.

**The load figures the bible must use are the real ones from Appendix A:** 2.4M registered clients;
380k monthly active; 14k concurrent sessions rising to **55k** on a major event; 95k card deposits/day
at **40/sec**; 6.5k bank deposits/day in batch; 2.8M stake reservations/day at **1,200/sec**; 2.8M
settlements/day with **3,400/sec** bursts; 19.8M ledger entries/day, **230 writes/sec sustained and
13,600/sec peak**, ~180 bytes/row, ~1.3 TB/year, 7.2B rows/year, 90-day hot window, 7-year retention;
11k card withdrawals/day at 12/sec; 7k bank withdrawals/day across **4 `PaymentRun` windows/day** of
~1.8k records each; a bank statement file of **40k records (500k at month end)**; **24k document
uploads/day at 2–6 MB each = 68 GB/day**; 2.6M `ApplicationHistory` records/day at ~400 bytes; 38k
restriction records/day at ~300 bytes; a **30 ms** restriction-decision budget, an **80 ms** balance
read, a **150 ms** stake reservation, a **hard 500 ms** self-exclusion, a **4 s** card deposit
end-to-end, a **2 s** document upload accept, **90 s** async document verification, and a **24 h**
withdrawal-submit budget; PSP capture p50 180 ms / p99 6 s / timeout 10 s at 500/sec; identity vendor
p50 900 ms / p99 38 s at 600/min estate-wide; banking-partner payout file p50 2 s / p99 45 s /
timeout 60 s.

**The four architectural rules from scenario § 5.1 constrain every design in this guide** and the
bible must say so at the point of decision: only `FundsLedger` writes money; tokens carry identity
and authority is asked for synchronously (so `ClientRestrictions` is a synchronous call and its
30 ms budget is a hard infrastructure constraint, not a soft target); every external vendor sits
behind exactly one owning service (so **only `CardPayments` may egress to the PSP** — a network and
IAM boundary, not a convention); and no cross-schema joins. Add Appendix B.4's rules: workload
identity with short-lived credentials and mTLS, secrets in a managed store never in config,
configuration versioned and promoted never edited in place, scheduled work behind a central
scheduler plus leader election never per-instance cron, rolling deployment with
**drain-before-terminate on the payment run**, and object lifecycle policies plus partition
detach-and-archive on the ledger.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument or the arithmetic through; do not state the result and move on |
| `[SOURCE]` | quote real documentation, an AWS post-event summary, SDK javadoc or actual source (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is IAM JSON / Terraform / CloudFormation / CLI) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, quota, price or byte/throughput arithmetic explicitly |
| `[CFG]` | give the exact configuration key / property / attribute name and its default |
| `[API]` | give the exact Java/Spring type, method signature or annotation attribute |
| `[IAM]` | must show a real policy JSON document, not a description of one |
| `[CLI]` | show the exact `aws …` command and read its output |
| `[METRIC]` | name the exact CloudWatch metric/namespace/dimension and what a bad value looks like |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — an error message, a `describe` dump, a Flow Log line — and read it line by line |
| `[TABLE]` | must be rendered as a table |
| `[COST]` | must show the money arithmetic against QuizStakes volumes, not a rate card |
| `[INCIDENT]` | must name a real, published incident and cite the first-party post-event summary |

---

# PART 1 — BASICS

## §1.1 Why any of this exists at all

1.1.1 The origin problem: capacity had to be bought in units of *racks* and *quarters*, so every
      system was provisioned for a peak that arrived twice a year and idled the rest of the time.
      Worked against QuizStakes: 14k concurrent sessions steady, **55k on a major sporting event**
      — a 3.9× ratio you cannot buy hardware for. `[NUM]` `[PROVE]`
1.1.2 **Elasticity** as reason one — capacity as an API call with a minute's lead time, not a
      purchase order with a quarter's.
1.1.3 **Capital expenditure → operating expenditure** as reason two, and why that changes who can
      approve an architecture decision.
1.1.4 **Operational transfer** as reason three — the real product is *not running the thing*: no
      one is paged at 3 a.m. for a failed RAID controller.
1.1.5 **Geographic reach** as reason four — a region in eight hours instead of a data-centre
      contract in eight months.
1.1.6 **Managed primitives** as reason five — a durable queue, a replicated database and a global
      CDN as line items rather than as projects.
1.1.7 The costs, enumerated and non-negotiable: a variable bill you can lose control of, lock-in
      proportional to how proprietary the primitive is, opaque debugging (you cannot `strace` a
      managed service), noisy-neighbour and multi-tenant failure modes, quota ceilings you did not
      choose, and a very large surface area of things to misconfigure. `[TABLE]`
1.1.8 When **not** to move to cloud: steady predictable load at large scale where the multiple is
      millions (the Dropbox and 37signals repatriation arguments), hard data-residency rules with no
      local region, and specialised hardware. `[TRAP]`
1.1.9 The honest framing of what AWS is: **a very large multi-tenant computer with an HTTP API in
      front of every subsystem.** Every service is `POST` to an endpoint with a SigV4 signature; the
      console, the CLI and the SDK are all clients of the same API. `[PROVE]`
1.1.10 What "cloud native" does and does not mean, and why the phrase is usually a smell in an
      interview answer.
1.1.11 IaaS vs PaaS vs FaaS vs SaaS as a spectrum of *how much of the stack you stopped owning*,
      mapped to EC2 / Elastic Beanstalk & App Runner / Lambda / Cognito. `[TABLE]`
1.1.12 AWS vs Azure vs GCP in one paragraph: the honest differences (breadth and maturity, identity
      model, networking model, pricing granularity) and why "we're multi-cloud" is usually a claim
      about procurement, not architecture. `[TABLE]`

## §1.2 The global infrastructure model

1.2.1 **Region** — a geographic area with its own control plane and its own failure domain.
      `eu-west-1` (Ireland), `us-east-1` (N. Virginia), `eu-west-2` (London). ~36 regions.
      `[NUM]`
1.2.2 Regions are **isolated by design**: separate control planes, separate endpoints, separate
      quotas, and no data movement unless you move it. The GDPR / data-residency consequence for
      QuizStakes PII. `[X-REF 13]`
1.2.3 **`us-east-1` is not just another region.** It hosts global-service control planes (IAM, Route 53,
      CloudFront, Organizations, `sts.amazonaws.com`'s global endpoint, S3 global endpoints and
      Billing), it is where new services launch first, and it is the largest and most failure-prone.
      `[TRAP]`
1.2.4 **Availability Zone** — one or more discrete data centres with independent power, cooling and
      networking, physically separated by kilometres, connected by dedicated low-latency private
      fibre. 3–6 AZs per region. Round-trip **typically well under 1 ms, single-digit ms worst
      case**. `[NUM]`
1.2.5 Why the AZ construct exists at all: it is the largest failure domain that is still close enough
      for **synchronous** replication. Cross-region synchronous replication is not practical — an
      80 ms RTT inside every commit — so cross-region is asynchronous, which is exactly why a regional
      failover can lose recent writes. `[PROVE]`
1.2.6 **AZ names are randomised per account** (`eu-west-1a` in your account is a different physical
      zone from mine). **AZ IDs** (`euw1-az1`) are stable and are what you correlate on across
      accounts. Why AWS did this: to stop everyone piling into "a". `[TRAP]` `[CLI]`
1.2.7 The design rule: **spread every tier across at least two, preferably three AZs** — instances in
      multiple subnets behind a multi-AZ load balancer, RDS Multi-AZ, an ASG spanning three subnets.
1.2.8 **Why three rather than two, as arithmetic.** With 2 AZs, losing one removes 50% of capacity so
      you must run at 200%; with 3, losing one removes 33% so 150% suffices. Quorum systems (etcd,
      ZooKeeper, Kafka RF=3, RDS Multi-AZ cluster's Raft) *require* three to keep a majority after
      losing one. Worked for `FundsLedger`'s 3 instances at 12 GB. `[PROVE]` `[NUM]`
1.2.9 **Edge locations / points of presence** — 700+ globally, serving CloudFront, Route 53, AWS
      Global Accelerator and AWS WAF. Far more numerous than regions and a different kind of thing.
      `[NUM]`
1.2.10 **Regional edge caches** — a mid-tier between edge PoPs and the origin, and what they do to
      CloudFront's origin-request rate.
1.2.11 **Local Zones** — a compute/storage extension of a region placed in a metro, for single-digit
      millisecond latency to a city. S3 directory buckets in Local Zones for data residency.
      `[RESEARCH]`
1.2.12 **Wavelength Zones** (inside telco 5G networks) and **Outposts** (AWS racks in your data
      centre, with the `OUTPOSTS` S3 storage class and no SSE-KMS). Name them, bound them, move on.
1.2.13 **AWS Global Accelerator** — anycast static IPs at the edge that enter the AWS backbone
      immediately, as the alternative to DNS-based global routing. Contrast with Route 53
      latency-based routing. `[X-REF 10]`
1.2.14 **The AWS backbone** — why cross-region traffic between AWS services usually does not touch
      the public internet, and why that is a security argument as well as a latency one.
1.2.15 **Multi-region is a different and much larger commitment**: replication with conflict
      resolution, global routing, duplicated infrastructure, cross-region cost, and a substantially
      harder operational model. Justify it with an actual RTO/RPO, residency or latency requirement —
      never with "for high availability", because multi-AZ already gives you that. `[TRAP]`
1.2.16 The sentence that lands in an interview: *"multi-AZ by default; multi-region only when the
      requirement demands it, and then only for the tier that demands it."*

## §1.3 The shared responsibility model

1.3.1 The formulation: AWS is responsible for security **of** the cloud; you are responsible for
      security **in** the cloud.
1.3.2 Where the line actually falls, per service model, as a table: EC2 (you own OS, patching,
      firewall rules, data) vs RDS (you own schema, credentials, network access, encryption choice)
      vs Lambda (you own code and IAM only) vs S3 (you own bucket policy, encryption, access).
      `[TABLE]`
1.3.3 The corollary nobody states: **the line moves as you move up the abstraction**, so "who patches
      this" is a question with a different answer per service in the same architecture.
1.3.4 What AWS never takes responsibility for, in any model: your IAM policies, your data
      classification, your keys' usage, your application code, and your bill.
1.3.5 The **shared responsibility model for resilience** — AWS gives you the AZ construct; deciding
      to use three of them is yours. An AZ failure that takes you down is your design's failure.
      `[TRAP]`
1.3.6 Compliance inheritance: SOC 2 / ISO 27001 / PCI-DSS attestations you inherit vs the controls
      you must still implement. Relevant to QuizStakes' regulated status. `[X-REF 13]`
1.3.7 **AWS Artifact** as where the attestations actually live.

## §1.4 The account, organization and identity boundary

1.4.1 **The AWS account is the strongest isolation boundary AWS offers** — stronger than any IAM
      policy inside one account. Separate quotas, separate billing, separate blast radius.
1.4.2 The **root user**: one per account, tied to an email address, holds unremovable permissions,
      and can perform ~10 operations nothing else can (close the account, change support plan,
      restore an IAM-locked bucket policy). Enable hardware MFA, delete its access keys, never use it.
      `[TRAP]`
1.4.3 **AWS Organizations** — a management account plus member accounts arranged in **Organizational
      Units (OUs)**, with consolidated billing and volume-discount pooling.
1.4.4 **Service Control Policies (SCPs)** — an OU/account-level *filter* on what any principal in
      that account may do. They can only **restrict**, never grant. A `Deny` in an SCP beats every
      `Allow` beneath it. `[IAM]`
1.4.5 **Resource Control Policies (RCPs)** — the resource-side mirror of an SCP, capping what may be
      done *to* resources in the org regardless of the caller. Newer than SCPs and frequently
      unknown. `[RESEARCH]`
1.4.6 **Declarative policies** — org-wide configuration enforcement (e.g. "IMDSv2 required on every
      EC2 launch") applied at the service level rather than as a permission check. `[RESEARCH]`
1.4.7 The standard account topology: `management` (billing and org only, nothing runs in it),
      `log-archive`, `security-tooling`, `shared-services`, then `prod` / `staging` / `dev` per
      workload. Mapped to QuizStakes: card data isolation (§B.4) is an account boundary, not a
      subnet. `[TABLE]`
1.4.8 **AWS Control Tower** and **landing zones** as the automation of that topology.
1.4.9 **AWS IAM Identity Center** (formerly AWS SSO) — permission sets, account assignments, and how
      a human gets short-lived credentials into 40 accounts without a single IAM user. `[VERSION-TRAP]`
1.4.10 **Consolidated billing**: one payer, pooled Savings Plans and Reserved Instance coverage,
      pooled free tier. Why this is an argument *for* many accounts rather than against.
1.4.11 **Cross-account access** — `sts:AssumeRole` with a trust policy on the target side, vs
      resource-based policies (S3, SQS, KMS, Lambda) that grant directly without an assume.
      `[TABLE]` `[IAM]`
1.4.12 **Service quotas are per account per region.** Naming the ones that bite: 1,000 Lambda
      concurrency, 5 VPCs, 5 EIPs, 200 rules per security group, 20 on-demand vCPUs on a fresh
      account. `[NUM]` `[CLI]`
1.4.13 **Tagging as the substitute for structure you didn't build**: `Environment`, `Team`,
      `Service`, `CostCentre`, `DataClassification`. Tag policies to enforce the schema. `[CFG]`
1.4.14 **ARNs** — the universal resource name and its grammar:
      `arn:partition:service:region:account-id:resource-type/resource-id`. Where each field is empty
      and why (S3 has no region or account in the ARN; IAM has no region). `[PROVE]`
1.4.15 Partitions: `aws`, `aws-cn`, `aws-us-gov`. Why an ARN written for one does not work in another.
1.4.16 **Principals**: IAM user, IAM role (and its session), AWS service principal
      (`ecs-tasks.amazonaws.com`), federated principal, account principal, anonymous.

## §1.5 The API model — everything is an HTTP request

1.5.1 The claim, stated first: **every AWS action is an HTTPS request to a regional endpoint,
      authenticated by a Signature Version 4 signature.** Console, CLI and SDK are three clients of
      one API.
1.5.2 **Endpoints** — `service.region.amazonaws.com`, the dual-stack and FIPS variants, and
      **VPC endpoint DNS** overriding the name inside a VPC. `[CFG]`
1.5.3 **SigV4 at a glance**: canonical request → string to sign → derived signing key
      (`AWS4` + secret → date → region → service → `aws4_request`) → HMAC-SHA256 signature in the
      `Authorization` header. Why the derived key is scoped to one day, one region and one service.
      `[PROVE]` `[WIRE]`
1.5.4 **The session token** (`X-Amz-Security-Token`) as the third credential component that makes
      temporary credentials work.
1.5.5 **Clock skew** breaks SigV4 — a request more than 5 minutes off is rejected with
      `SignatureDoesNotMatch` / `RequestTimeTooSkewed`. The symptom on a container with a bad clock.
      `[TRAP]` `[DIAG]` `[NUM]`
1.5.6 **Control plane vs data plane** — the single most useful distinction in AWS reliability
      thinking. `RunInstances` / `CreateFunction` / `PutBucketPolicy` are control plane; an HTTP GET
      to an object, an invoke, a query are data plane. Control planes are more complex, less
      redundant, and fail first. `[PROVE]`
1.5.7 The design rule that falls out of it: **a failover must not depend on a control-plane call.**
      Pre-provision capacity; do not plan to `RunInstances` during a regional event. The October 2025
      outage is the proof. `[TRAP]` `[INCIDENT]`
1.5.8 **Control planes are eventually consistent.** An IAM policy change, a Route 53 record and a
      security-group rule all take effect *soon*, not *now*. What "soon" means per service.
1.5.9 **Idempotency in AWS APIs** — `ClientToken`, `client-request-token`, conditional writes, and
      which APIs have none. `[X-REF 12]`
1.5.10 **Throttling and `ThrottlingException` / `429` / `503 SlowDown`** as first-class API responses
      you must handle, not as errors. `[X-REF 12]`
1.5.11 **Retries and exponential backoff with jitter** as an SDK responsibility — and the SDK's
      defaults (see §2.22). `[X-REF 10]`
1.5.12 **Eventual consistency of the resource itself vs of the API**: `CreateRole` then immediately
      `AssumeRole` fails; `PutObject` then `GetObject` does not (strong since Dec 2020).
      `[VERSION-TRAP]`
1.5.13 **CloudTrail records the API call, not the effect.** Every one of the above appears in the
      audit log with the principal, the source IP, the user agent and the request parameters.
      `[X-REF 20]`

## §1.6 IAM — the model

1.6.1 The model in one sentence: a **principal** requests an **action** on a **resource** under a
      set of **conditions**, and IAM evaluates every applicable **policy** to allow or deny.
1.6.2 **User** — a permanent identity with long-lived credentials (console password, access keys).
      For humans without SSO. **Avoid entirely for applications.** `[TABLE]`
1.6.3 **Group** — a collection of users; a policy-attachment convenience, never a principal.
      You cannot make a group the principal of anything. `[TRAP]`
1.6.4 **Role** — an identity with **no permanent credentials**, assumed to obtain temporary ones.
      The correct answer for applications, services, cross-account and federated humans.
1.6.5 **Policy** — a JSON document: `Version`, `Statement[]` with `Sid`, `Effect`, `Action`,
      `NotAction`, `Resource`, `NotResource`, `Principal`, `Condition`. `[IAM]`
1.6.6 The `"Version": "2012-10-17"` string is a **policy language version, not a date**, and omitting
      it silently drops variable substitution. `[TRAP]`
1.6.7 **The six policy types** and what each does: identity-based, resource-based, permissions
      boundary, SCP, RCP, session policy. `[TABLE]` `[SOURCE]`
1.6.8 **Evaluation order, stated as the rule that gets asked**: explicit `Deny` anywhere wins →
      otherwise an explicit `Allow` in an applicable policy grants → otherwise **implicit deny**.
      `[PROVE]`
1.6.9 The set arithmetic underneath it: identity-based ∪ resource-based (same account), ∩ permissions
      boundary, ∩ SCP, ∩ RCP, ∩ session policy. Union for the first pair, intersection for the rest.
      `[PROVE]` `[SOURCE]`
1.6.10 **The instance-profile mechanism, as an ordered trace.** Attach an instance profile (a wrapper
      around a role) → the SDK's default credential provider chain queries IMDS at
      `169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>` → receives
      `AccessKeyId`, `SecretAccessKey`, `Token` and `Expiration` → **refreshes automatically before
      expiry** → nothing is ever written to disk. `[FLOW]` `[WIRE]`
1.6.11 The same mechanism, five different plumbings: **ECS task role** (a container-local endpoint at
      `169.254.170.2`, addressed by `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`, per *task*),
      **Lambda execution role** (env vars injected and refreshed by the runtime), **EKS Pod Identity**
      (node-local agent) and **IRSA** (projected service-account token exchanged via
      `AssumeRoleWithWebIdentity`), **cross-account** (`sts:AssumeRole`), **humans** (Identity Center
      → short-lived role credentials). `[TABLE]`
1.6.12 The result stated as a rule: **applications should never have access keys.** No long-lived
      secrets anywhere, automatic rotation, per-workload scoping, and a full CloudTrail trail of who
      assumed what and when.
1.6.13 **IAM Roles Anywhere** — X.509-based role assumption for workloads outside AWS, so the rule
      survives hybrid. `[RESEARCH]`
1.6.14 **STS operations by name**: `AssumeRole`, `AssumeRoleWithWebIdentity`, `AssumeRoleWithSAML`,
      `GetSessionToken`, `GetFederationToken`, `GetCallerIdentity`. Session duration 15 min – 12 h
      (1 h default, capped by `MaxSessionDuration`), and **role chaining caps at 1 hour**. `[NUM]`
      `[TRAP]`
1.6.15 `aws sts get-caller-identity` as the first command in any "who am I actually" debugging
      session. `[CLI]` `[DIAG]`
1.6.16 **Least privilege in practice, as a procedure**: start restrictive → run the workload → read
      the `AccessDenied` messages, each of which names the exact missing action → tighten with
      conditions. Or generate a policy from CloudTrail with **IAM Access Analyzer**. `[FLOW]`
1.6.17 The `AccessDenied` message format, read line by line: which principal, which action, which
      resource, and — when present — **which policy type produced the deny**. `[DIAG]`
1.6.18 Baseline hygiene that a review will check: MFA on every human, root unused and MFA'd,
      CloudTrail on in all regions with a `log-archive` account destination, access keys rotated or
      eliminated, and one account per environment. `[TABLE]`

## §1.7 EC2 and the compute substrate

1.7.1 **What an EC2 instance actually is**: a virtual machine on the **Nitro System** — a hardware
      offload card plus a minimal hypervisor, with networking, EBS and security in hardware.
1.7.2 **The instance-type naming grammar**, parsed character by character: family letter, generation
      number, optional capability suffixes (`g` Graviton, `i` Intel, `a` AMD, `d` local NVMe, `n`
      network-optimised, `b` block-storage-optimised, `e` extra memory, `flex`), then size.
      `m7g.2xlarge` decoded. `[PROVE]`
1.7.3 **The families and their trade-off**: `t` burstable, `m` balanced, `c` compute, `r`/`x`/`z`
      memory, `i`/`d` storage, `g`/`p`/`inf`/`trn` accelerated, `hpc`. `[TABLE]`
1.7.4 **`t` instances and the CPU-credit machine**: a baseline percentage of a vCPU, credits accrued
      per hour, credits spent above baseline, and **throttling to baseline when the balance hits
      zero**. `standard` vs `unlimited` mode, and the surprise bill `unlimited` produces. Excellent
      for `BankDeposits` (idle 23 hours a day); dangerous for `ClientRestrictions`. `[TRAP]` `[NUM]`
      `[METRIC]`
1.7.5 **Graviton** — Arm64, `*g` suffix, generations 1–5 (Graviton4 → `M8g`/`C8g`/`R8g`; **Graviton5
      → `M9g`/`C9g`, GA 2026**), roughly 30–40% better price-performance per generation. For a JVM
      workload the port is usually a base-image change; the exceptions are JNI libraries and
      x86-only native dependencies. `[VERSION-TRAP]` `[RESEARCH]`
1.7.6 **Storage attached to an instance, three kinds**: EBS (network block, persists, snapshot-able,
      **AZ-scoped**), **instance store** (physically attached NVMe, far faster, **lost on stop or
      terminate**), and EFS/FSx (network filesystems). Never put state on instance store. `[TRAP]`
1.7.7 **Purchasing models**: On-Demand, **Spot** (up to 90% off, reclaimed with a **2-minute**
      interruption notice delivered via IMDS and an EventBridge event), **Reserved Instances**
      (1 or 3 year, standard vs convertible), **Savings Plans** (Compute / EC2 Instance / SageMaker;
      1 or 3 year; 30–72% off), **Dedicated Hosts** and **Dedicated Instances**, **Capacity
      Reservations**. `[TABLE]` `[NUM]`
1.7.8 Spot's fit: stateless, batch, CI, anything with a checkpoint. Its non-fit: a stateful singleton,
      a leader, `FundsLedger`. QuizStakes mapping: the `BankDeposits` worker pool is a Spot candidate;
      `BankWithdrawal`'s `PaymentRun` leader is not.
1.7.9 **User data** — a script run at first boot (`cloud-init`), 16 KB limit, base64-encoded, visible
      via IMDS **to anything on the instance**. Never put a secret there. `[TRAP]` `[NUM]`
1.7.10 **Instance metadata service (IMDS)** at `169.254.169.254` — instance identity document,
      placement, network config, and **the role's temporary credentials**.
1.7.11 **IMDSv1 vs IMDSv2.** v1 is a plain unauthenticated `GET`; v2 requires a `PUT` to
      `/latest/api/token` with `X-aws-ec2-metadata-token-ttl-seconds`, returning a token used on every
      subsequent request, and sets a **default hop limit of 1** so a container or a proxy cannot reach
      it. This is the SSRF defence. `[WIRE]` `[NUM]`
1.7.12 **The Capital One breach (2019)** as the named incident: an SSRF in a WAF let an attacker make
      the host fetch `169.254.169.254/...`, steal the instance role's credentials, and read 100M
      records from S3. IMDSv2 exists because of it. `[INCIDENT]` `[X-REF 13]`
1.7.13 **IMDSv2 is now the default for newly released instance types (mid-2024) and can be enforced
      account-wide per region**, and via a declarative policy org-wide. Setting the account default
      does **not** change existing instances. `[VERSION-TRAP]` `[CLI]`
1.7.14 **Placement groups**: `cluster` (one AZ, lowest latency, highest correlated failure),
      `spread` (distinct hardware, max 7 per AZ per group), `partition` (partition-aware, for
      HDFS/Cassandra/Kafka). `[TABLE]` `[NUM]`
1.7.15 **AMIs** — the image, its snapshot lineage, region-scoping and copying, deprecation dates,
      and **EC2 Image Builder** / Packer as the pipeline. Golden AMI vs bake-at-boot.
1.7.16 **Instance lifecycle states**: `pending → running → stopping → stopped → terminated`, plus
      `hibernate`. What survives each: EBS root yes, instance store no, public IPv4 no (unless
      Elastic IP), private IP yes within a stop/start on the same subnet. `[TABLE]` `[TRAP]`
1.7.17 **Status checks**: system status (AWS's problem) vs instance status (yours) vs attached-EBS
      status, and auto-recovery. `[METRIC]`
1.7.18 **Elastic IPs** — a static public IPv4, and the fact that you are charged **precisely when it
      is not associated** (and, since Feb 2024, for all public IPv4 addresses at ~$0.005/hour).
      `[VERSION-TRAP]` `[COST]`
1.7.19 **EC2 Instance Connect**, **Session Manager** and **why a bastion host is now usually the wrong
      answer** — SSM removes the inbound port, the key material, and the public subnet. `[TRAP]`
1.7.20 **Nitro Enclaves** as the isolated-compute primitive, named for completeness (card-data
      isolation in scenario B.4 is one plausible use). `[X-REF 13]`

## §1.8 Block, file and object storage — the three shapes

1.8.1 The distinction that generates real bugs: **block** (a device you format and mount), **file**
      (a POSIX namespace, shared, with locking), **object** (a key-addressed immutable blob over
      HTTP). `[TABLE]` `[PROVE]`
1.8.2 **EBS**, one level deep: network-attached, replicated within one AZ, `gp3`/`gp2`/`io2 Block
      Express`/`io1`/`st1`/`sc1`, snapshots to S3 (incremental, region-scoped, copyable).
1.8.3 **The EBS volume-type table with real numbers**: `gp3` 1 GiB–64 TiB, **80,000 IOPS**,
      **2,000 MiB/s**, 3,000 IOPS + 125 MiB/s baseline included, IOPS and throughput provisioned
      *independently of size*; `gp2` 1 GiB–16 TiB, 16,000 IOPS, 250 MiB/s, **3 IOPS per GiB** so
      performance is coupled to size; `io2 Block Express` 4 GiB–64 TiB, **256,000 IOPS**,
      4,000 MiB/s, **99.999% durability**, sub-500-microsecond latency, Multi-Attach and NVMe
      reservations; `io1` 64,000 IOPS / 1,000 MiB/s; `st1` 500 IOPS / 500 MiB/s; `sc1` 250 IOPS /
      250 MiB/s. `[TABLE]` `[NUM]` `[SOURCE]` `[VERSION-TRAP]`
1.8.4 **`gp2` → `gp3` is nearly always a free win**: ~20% cheaper per GB and decoupled performance.
      The migration is an online `ModifyVolume`. `[COST]`
1.8.5 EBS durability is **99.8–99.9% annual** for `gp3`/`gp2`/`io1` — an 0.1–0.2% annual failure rate.
      **That is not S3's eleven nines**, and it is why snapshots exist. `[TRAP]` `[NUM]`
1.8.6 **An EBS volume cannot cross an AZ** (Multi-Attach is same-AZ, multi-instance). Snapshot-and-
      restore is the cross-AZ move, and it is not instant.
1.8.7 **EBS-optimised instances** and the instance-level EBS bandwidth ceiling — you can provision
      more IOPS than the instance can carry. `[TRAP]`
1.8.8 **EFS** — managed NFSv4, multi-AZ, elastic, POSIX semantics. Performance modes, throughput
      modes (Elastic / Provisioned / Bursting), and lifecycle to IA. Slow relative to EBS; expensive
      relative to S3. The honest advice: ask hard whether you need shared filesystem semantics at all.
1.8.9 **FSx** (Windows File Server, Lustre, NetApp ONTAP, OpenZFS) named and bounded.
1.8.10 **AWS Backup** as the cross-service backup plane, with vault lock for immutability.
1.8.11 **Storage Gateway** and **DataSync** named for hybrid completeness.

## §1.9 S3 — object storage, not a filesystem

1.9.1 The comparison table, stated precisely because the confusion produces bugs: unit
      (immutable object = key + bytes + metadata vs mutable byte ranges), partial write
      (**impossible** vs seek-and-write), append (**not supported** except in Express One Zone
      directory buckets vs yes), directories (**do not exist** — `a/b/c.txt` is one flat key and
      "folders" are a console illusion over prefix listing vs a real hierarchy), rename
      (**not an operation** — copy then delete, O(size) not O(1) vs an atomic metadata change),
      listing (a paginated API call over a prefix, expensive at scale vs a cheap directory read),
      consistency (**strong read-after-write since December 2020** vs strong). `[TABLE]`
      `[VERSION-TRAP]`
1.9.2 The practical consequences, spelled out: you cannot append to a log file in S3 (write many
      objects and compact); a "move" of a 5 GB object costs a full copy; `ListObjectsV2` over
      10M keys is not a lookup mechanism — keep an index in a database. QuizStakes: 24k document
      images/day means an index in `DocumentVerification`'s schema, not a prefix scan. `[TRAP]`
1.9.3 **Buckets** — globally unique names across all AWS accounts, DNS-compatible, region-pinned at
      creation, 100 per account soft (10,000 hard). Two bucket types: **general purpose** and
      **directory buckets** (Express One Zone). `[NUM]` `[VERSION-TRAP]`
1.9.4 **Keys** — up to 1,024 UTF-8 bytes, no real delimiter, and the `/` convention.
1.9.5 **Object size**: 0 bytes to **50 TB** (raised from 5 TB at re:Invent 2025). Single `PutObject`
      is capped at **5 GB**; above that you must use multipart. `[NUM]` `[VERSION-TRAP]`
1.9.6 **Multipart upload**: 5 MiB minimum part (last part exempt), **10,000 parts maximum**, parts
      uploadable in parallel and retryable individually, `CompleteMultipartUpload` assembles.
      `[NUM]` `[PROVE]`
1.9.7 **Incomplete multipart uploads are invisible and billable forever.** The lifecycle rule
      `AbortIncompleteMultipartUpload: DaysAfterInitiation: 7` is the fix, and its absence is one of
      the most common silent costs in an inherited account. `[TRAP]` `[COST]`
1.9.8 **ETag** is an MD5 for a single-part PUT and **`<md5-of-concatenated-part-md5s>-<partcount>`
      for a multipart** — so an ETag is not a content hash you can compare across upload methods.
      `[TRAP]` `[PROVE]`
1.9.9 **Durability: 99.999999999% (eleven nines)** via redundant storage across ≥3 AZs. Availability
      SLA is a separate and much smaller number (99.9% service commitment; 99.99% design target for
      Standard). `[NUM]`
1.9.10 **Durability is not backup.** S3 will faithfully preserve the empty object you overwrote and
      the deletion you performed. Versioning, MFA Delete, Object Lock and replication are the actual
      answers. `[TRAP]`
1.9.11 **The full storage-class table with real numbers** — Standard (no minimum, ≥3 AZ, 99.99%
      availability), Standard-IA (30-day minimum, **128 KB minimum billable size**, retrieval fee,
      99.9%), One Zone-IA (**1 AZ**, 99.5%), Intelligent-Tiering (no minimum, no retrieval fee, a
      per-object monitoring fee, **objects under 128 KB are never monitored**), Express One Zone
      (1 AZ, 99.95%, single-digit-ms, ~50% lower request cost, 10× faster access), Glacier Instant
      Retrieval (90-day minimum, 128 KB minimum, millisecond access), Glacier Flexible Retrieval
      (90-day minimum, minutes-to-hours, **40 KB of metadata overhead per object**), Glacier Deep
      Archive (**180-day** minimum, hours, 40 KB overhead), Reduced Redundancy (99.99% durability,
      do not use), Outposts. `[TABLE]` `[NUM]` `[SOURCE]`
1.9.12 **Intelligent-Tiering's tiers**: Frequent → Infrequent at **30 days** → Archive Instant Access
      at **90 days**, plus the two opt-in asynchronous tiers Archive Access (90 d) and Deep Archive
      Access (180 d). Usually the correct default when the access pattern is unknown. `[NUM]`
1.9.13 **Lifecycle rules** as the automation, written out for QuizStakes' 68 GB/day of document
      images: transition to `STANDARD_IA` at 30 days, `GLACIER_IR` at 90 (matching the scenario's
      "cold after 90 days"), retain 7 years, expire noncurrent versions after 30 days, and abort
      incomplete multipart uploads after 7. `[CFG]` `[COST]`
1.9.14 **Versioning** — enabled/suspended (never *off* again), version IDs, **delete markers**, and
      the fact that a `DELETE` on a versioned bucket writes a marker rather than removing bytes.
      `[TRAP]`
1.9.15 **Noncurrent-version storage is the versioning cost trap**: without an expiry rule you pay for
      every overwrite forever. `[COST]`
1.9.16 **Object Lock** — WORM, governance vs compliance mode, retention periods and legal holds.
      Requires versioning. The answer to "prove you cannot alter the regulatory artefact" for the
      bank files QuizStakes keeps 7 years. `[X-REF 13]`
1.9.17 **Replication** — SRR and CRR, `ReplicationConfiguration`, replication of existing objects via
      Batch Replication, **S3 Replication Time Control (RTC)** with a **15-minute** SLA, and the
      fact that replication is asynchronous and does not replicate deletes by default. `[NUM]`
      `[TRAP]`
1.9.18 **Presigned URLs** as the pattern to know: instead of proxying a 500 MB upload through your
      service (consuming bandwidth, memory, threads and the request timeout), sign a time-limited URL
      and let the client talk to S3 directly. Sized against QuizStakes' 24k document uploads/day at
      2–6 MB and its 2 s upload-accept budget. `[API]` `[NUM]`
1.9.19 The presigned-URL caveats: the URL **carries your permissions**, so scope it to one operation
      and one key with a short expiry; the maximum life is bounded by the signing credential's own
      life (a role session's expiry truncates a 7-day signature); and you constrain content type and
      size with a **POST policy**, not with `presignPutObject`. `[TRAP]`
1.9.20 **Security defaults**: buckets are private, **Block Public Access is on by default at the
      account and bucket level since April 2023**, and ACLs are disabled by default (Bucket Owner
      Enforced object ownership). Public buckets remain a leading breach cause and essentially always
      because someone turned these off. `[VERSION-TRAP]` `[TRAP]`
1.9.21 **The four access-control mechanisms and their precedence**: IAM identity policy, bucket
      policy, ACL (legacy, disabled by default), Access Points / Object Lambda Access Points. Plus
      Block Public Access as an override that beats all of them. `[TABLE]` `[IAM]`
1.9.22 **Encryption**: SSE-S3 (`AES256`, automatic and free since January 2023), SSE-KMS (`aws:kms`,
      auditable, **and rate-limited by KMS quotas**), **S3 Bucket Keys** (which cut KMS requests by up
      to 99%), SSE-C, and client-side. `[VERSION-TRAP]` `[NUM]`
1.9.23 **Event notifications** — to SQS, SNS, Lambda, or EventBridge; the event types
      (`s3:ObjectCreated:*`, `s3:ObjectRemoved:*`), the at-least-once delivery, and the fact that
      **notifications can be lost** without EventBridge. The QuizStakes bank-file arrival trigger
      (scenario B.3) is exactly this. `[X-REF 14]` `[TRAP]`
1.9.24 **Conditional writes** — `If-None-Match: *` for create-if-absent (412 on conflict, 409 on a
      concurrent conflicting operation), `If-Match: <etag>` for optimistic overwrite, conditional
      copy, and the `s3:if-match` / `s3:if-none-match` bucket-policy condition keys. This makes S3 a
      legitimate CAS store. `[VERSION-TRAP]` `[RESEARCH]` `[NUM]`
1.9.25 **Requester Pays**, **Transfer Acceleration** (CloudFront edge ingest), **S3 Batch Operations**,
      **S3 Inventory**, **Storage Lens**, **Storage Class Analysis** — the operational surface most
      guides skip. `[TABLE]`
1.9.26 **Mountpoint for Amazon S3** and **S3 File Gateway** as the "I really do want a filesystem"
      escape hatches, with their honest limitations (no random writes, no rename).
1.9.27 **S3 Tables** (managed Apache Iceberg) and **S3 Vectors** (native vector storage and query, GA
      re:Invent 2025) — named, bounded, and flagged as the direction of travel. `[RESEARCH]`
1.9.28 **Access logging**: server access logs vs **CloudTrail data events** for S3, and why the
      latter costs money but is the one you want for an investigation. `[COST]`

## §1.10 Relational databases — RDS and Aurora

1.10.1 What RDS actually is: AWS runs the **engine process** (PostgreSQL, MySQL, MariaDB, SQL Server,
      Oracle, Db2) — provisioning, patching, backups, PITR, Multi-AZ failover, read replicas,
      metrics. You still own schema, indexes, queries and **connection count**.
1.10.2 **The knobs, by name**: automated backups with a 0–35 day retention window, PITR to any second
      in it, snapshot vs automated backup lifecycle, **maintenance windows (patching causes a
      failover — plan for it and make the app reconnect cleanly)**, **Parameter Groups** and which
      parameters are `static` (requiring a reboot) vs `dynamic`, **Option Groups**, Performance
      Insights, Enhanced Monitoring. `[CFG]` `[TRAP]`
1.10.3 **Three deployment shapes, not two**: Single-AZ; **Multi-AZ instance** (one synchronous idle
      standby, 60–120 s failover); **Multi-AZ DB cluster** (one writer + **two readable standbys**
      across three AZs, Raft-based, **failover under 35 seconds**, MySQL/PostgreSQL only).
      `[TABLE]` `[VERSION-TRAP]` `[NUM]`
1.10.4 **Read replicas** — asynchronous, up to 5 (RDS) / 15 (Aurora), promotable to independent
      databases, **and available cross-region** as a DR option.
1.10.5 **Multi-AZ vs read replica**, the comparison that gets asked and is constantly confused, as a
      full table: purpose (availability vs read scaling), replication (synchronous vs asynchronous),
      whether the standby serves traffic, failover behaviour (automatic DNS flip vs manual
      promotion), data loss on failover (none vs possible), cross-region support, and cost.
      `[TABLE]` `[TRAP]`
1.10.6 They solve different problems and are routinely used **together**: Multi-AZ for the primary's
      availability plus read replicas for reporting. QuizStakes' `BalanceView` is the read-replica
      case; `FundsLedger`'s writer is the Multi-AZ case.
1.10.7 **Read-replica gotchas the application must handle**: replica lag → read-after-write
      inconsistency (a client saves a profile, is routed to a replica, sees stale data); lag grows
      under heavy write load and long replica queries — precisely when you rely on it; monitor
      `ReplicaLag` and alert. Routing fresh reads to the primary is the fix.
      `[METRIC]` `[X-REF 09]`
1.10.8 **Failover is DNS-based**, which brings the JVM DNS-cache problem straight back: set
      `networkaddress.cache.ttl` (or `-Dsun.net.inetaddr.ttl`) to something small, and make the pool
      validate and discard broken connections (HikariCP `maxLifetime`, `validationTimeout`).
      `[TRAP]` `[X-REF 10]` `[X-REF 08]`
1.10.9 **Aurora** as a reimplementation, not a configuration: a distributed, log-structured storage
      layer of **6 copies across 3 AZs**, a **4-of-6 write quorum and 3-of-6 read quorum**, 10 GB
      segments, ~30 s failover, up to 15 low-lag readers on shared storage, and a cluster/reader
      endpoint pair. `[NUM]` `[PROVE]`
1.10.10 **Aurora Serverless v2** — ACU-based autoscaling (0.5 ACU granularity, **scale-to-zero**
      supported since 2024), and when the cost model beats provisioned.
1.10.11 **Aurora Global Database** — cross-region, sub-second typical replica lag, RPO ~1 s,
      RTO < 1 min managed failover, write forwarding.
1.10.12 **Aurora I/O-Optimized** as the pricing mode that removes per-I/O charges — worth checking
      at QuizStakes' 19.8M ledger entries/day. `[COST]`
1.10.13 **Aurora DSQL** — serverless, distributed, active-active multi-Region, strongly consistent,
      PostgreSQL-compatible; GA 27 May 2025. Its hard limits are the interesting part: Repeatable
      Read only, **one DDL statement per transaction**, DDL and DML in separate transactions,
      **3,000 rows modified per transaction**, 1-hour connection timeout, no triggers, no PL/pgSQL,
      no extensions, no sequences, no temporary tables, no `LISTEN`/`NOTIFY`, no PostGIS/pgvector.
      99.99% single-Region / 99.999% multi-Region availability targets. `[VERSION-TRAP]` `[RESEARCH]`
      `[NUM]`
1.10.14 Why Aurora DSQL is the wrong answer for `FundsLedger` as specified: the ledger's four-bucket
      model posts 4 entries per movement at 13,600/sec peak, and its invariants want ordinary
      Serializable-shaped reasoning plus sequences. State the analysis rather than the slogan.
      `[PROVE]`
1.10.15 **Connection management is the thing backend engineers get wrong.** `max_connections` on RDS
      Postgres is derived from instance memory (`LEAST({DBInstanceClassMemory/9531392}, 5000)`).
      With QuizStakes' 8 `PaymentService` pods × a 10-connection HikariCP pool you have consumed 80
      connections before serving a request, and a scale-out event to 40 `ApplicationGateway`
      instances can exhaust the limit instantly and take down **every service sharing the
      instance**. `[PROVE]` `[NUM]` `[TRAP]`
1.10.16 The rule: `Σ(pods × poolSize) + admin headroom + maintenance headroom < max_connections`,
      and the second rule that a pool should be **small** — a database saturates at far fewer
      connections than people expect. `[X-REF 08]`
1.10.17 **RDS Proxy** — multiplexes many client connections onto few database connections, survives
      failover by holding the client connection open, and is close to mandatory for Lambda and for
      high pod counts. Its costs: per-vCPU-hour pricing, a latency addition, and **pinning** (a
      session-state-setting statement pins a client to a backend connection and destroys the
      multiplexing benefit). `[TRAP]` `[NUM]`
1.10.18 **Blue/Green Deployments** for RDS/Aurora — a synchronised green environment, switchover in
      about a minute with no endpoint change, and its limitations. Combined with RDS Proxy it removes
      the DNS-propagation gap entirely. `[RESEARCH]`
1.10.19 **Storage autoscaling**, `gp3` vs `io1` for RDS, the **`FreeStorageSpace` cliff**, and the
      fact that you cannot shrink RDS storage — ever. `[TRAP]` `[METRIC]`
1.10.20 **The metrics that matter**: `CPUUtilization`, `DatabaseConnections`, `FreeableMemory`,
      `ReadIOPS`/`WriteIOPS`, `ReadLatency`/`WriteLatency`, `ReplicaLag`, `BurstBalance`,
      `DiskQueueDepth`, `DeadlockRate`. `[METRIC]`

## §1.11 Non-relational data services

1.11.1 **DynamoDB** — a managed key-value and document store with single-digit-millisecond latency at
      any scale, no servers, no version, no connection pool.
1.11.2 The data model: table → **partition key** (mandatory) and optional **sort key**, items up to
      **400 KB**, schemaless beyond the key attributes. `[NUM]`
1.11.3 **Capacity modes**: provisioned (with autoscaling) vs **on-demand** (per-request, now with
      configurable maximum throughput). **RCU** = one strongly consistent read of up to 4 KB per
      second (or two eventually consistent); **WCU** = one write of up to 1 KB per second.
      `[NUM]` `[PROVE]`
1.11.4 **Consistency**: eventually consistent by default, strongly consistent reads on request (at
      2× RCU cost and only from the leader replica), and **transactions** (`TransactGetItems` /
      `TransactWriteItems`, up to 100 items, 2× cost).
1.11.5 **GSI** (different partition key, eventually consistent, its own capacity, **can throttle the
      base table's writes**) vs **LSI** (same partition key, different sort key, must be created with
      the table, shares the 10 GB item-collection limit, strongly consistent). `[TABLE]` `[NUM]`
      `[TRAP]`
1.11.6 **Hot partitions**: a single physical partition serves at most **3,000 RCU and 1,000 WCU** and
      holds at most **10 GB**. No amount of table-level capacity fixes an uneven key. Adaptive
      capacity and **split-for-heat** mitigate, they do not remove the ceiling. `[NUM]` `[PROVE]`
      `[TRAP]`
1.11.7 **Key design**: high cardinality, even distribution, write sharding by suffix, and composite
      sort keys. The QuizStakes analogue is the ledger's client-id partitioning and its whale problem.
      `[X-REF 22]`
1.11.8 **Single-table design** — what it is, why it exists (one request per access pattern, no
      joins), and the honest counter-argument (unreadable, migration-hostile, and usually premature).
      `[TRAP]`
1.11.9 **DynamoDB Streams** and **Kinesis Data Streams for DynamoDB** — change capture, the
      24-hour retention, the four `StreamViewType` values, and the Lambda event source mapping.
      `[X-REF 14]`
1.11.10 **TTL** — a per-item epoch attribute, deletion within ~48 hours, free, and it emits a stream
      record. The correct mechanism for QuizStakes' idempotency-key expiry. `[NUM]`
1.11.11 **Global Tables** — multi-region active-active with **last-writer-wins** conflict resolution,
      and why LWW is unacceptable for money. `[TRAP]` `[X-REF 22]`
1.11.12 **DAX** — a DynamoDB-specific write-through cache with microsecond reads, and its
      consistency caveat. `[X-REF 15]`
1.11.13 **PartiQL**, `Query` vs `Scan` (and why `Scan` is almost always a design failure),
      pagination with `LastEvaluatedKey`, and `ConditionExpression` for optimistic concurrency.
      `[API]` `[TRAP]`
1.11.14 **ElastiCache** (Redis OSS / Valkey / Memcached) and **MemoryDB** (durable, multi-AZ,
      Redis-compatible, with a transaction log) — the distinction being durability, not speed.
      `[X-REF 15]`
1.11.15 **OpenSearch Service** and **OpenSearch Serverless** — named and bounded; search is not a
      database.
1.11.16 **Neptune** (graph), **Timestream** (time series), **Keyspaces** (Cassandra), **DocumentDB**
      (MongoDB-compatible), **QLDB** (deprecated — worth knowing the ledger-database idea was tried
      and withdrawn). `[TABLE]` `[RESEARCH]`
1.11.17 **Redshift** and **Athena** as the analytical plane, with **Glue** as the catalogue and
      **Lake Formation** as its permission model. Where QuizStakes' cold columnar ledger archive
      (7.2B rows/year) actually lives. `[X-REF 09]`

## §1.12 VPC — the network model

1.12.1 A **VPC** is a logically isolated virtual network, defined by an IPv4 **CIDR** block
      (`/16` to `/28`; `10.0.0.0/16` ≈ 65,536 addresses), scoped to **one region**, spanning all its
      AZs. Up to 5 secondary CIDRs. `[NUM]`
1.12.2 **Subnets** are CIDR sub-ranges, each pinned to **exactly one AZ**. That is the mechanical
      reason "spread across AZs" means "put resources in subnets in different AZs." `[PROVE]`
1.12.3 **AWS reserves 5 addresses in every subnet**: network, VPC router, DNS (base+2), future use
      (base+3), broadcast. A `/28` gives you 11 usable, not 16 — and this is a real outage cause when
      an ASG cannot launch. `[NUM]` `[TRAP]`
1.12.4 **CIDR planning** as a design decision you cannot easily undo: non-overlapping ranges across
      VPCs and with on-prem (peering and Transit Gateway both forbid overlap), room for growth, and a
      per-AZ allocation scheme. Sized for QuizStakes' 40-instance `ApplicationGateway` peak.
1.12.5 **Public subnet** = a route table with `0.0.0.0/0 → igw-…`. **Private subnet** = no IGW route;
      egress via a **NAT Gateway** in a public subnet; **inbound from the internet is impossible**.
      That is the entire distinction — it is a *route table* property, not a subnet attribute.
      `[TRAP]` `[PROVE]`
1.12.6 **The standard three-tier layout**: public subnets (ALB, NAT) → private app subnets
      (ECS/EC2) → private data subnets (RDS, ElastiCache), each replicated across 3 AZs. Databases
      never in a public subnet, reachable only from the app tier's security group. Mapped onto
      QuizStakes' service catalogue. `[TABLE]`
1.12.7 **Internet Gateway** — a horizontally scaled, redundant, region-level component that performs
      1:1 NAT between a private IP and a public IPv4. It has no bandwidth limit and costs nothing
      itself.
1.12.8 **NAT Gateway** — AZ-scoped, managed, 5 Gbps scaling to 100 Gbps, ~55,000 simultaneous
      connections per unique destination. **Deploy one per AZ** or a zonal failure takes out egress
      for every AZ routing through it — and cross-AZ NAT traffic is billed. `[NUM]` `[TRAP]` `[COST]`
1.12.9 **Egress-only Internet Gateway** as the IPv6 equivalent of a NAT Gateway (IPv6 has no NAT).
1.12.10 **Security groups vs NACLs — the comparison that gets asked**, as a full table: attaches to
      (an **ENI** vs a **subnet**), rules (**allow only** vs allow **and** deny), state
      (**stateful** — return traffic automatically permitted — vs **stateless** — you must write both
      directions), evaluation (all rules, any match allows, vs **numbered order, first match wins**),
      defaults (deny all inbound + allow all outbound vs the default NACL allowing everything), and
      typical use. `[TABLE]`
1.12.11 **Stateful vs stateless is the crux.** With a security group, allowing inbound 443
      automatically allows the response out. With a NACL you must also allow outbound on the
      **ephemeral port range (1024–65535)** or replies are silently dropped — and the symptom is a
      connection that establishes and then hangs, which is baffling if you do not know the mechanism.
      `[TRAP]` `[DIAG]`
1.12.12 **Security groups can reference other security groups**, which is the idiomatic pattern:
      `sg-alb` allows 443 from `0.0.0.0/0`; `sg-app` allows 8080 **from `sg-alb`**; `sg-rds` allows
      5432 **from `sg-app`**. This expresses intent, survives IP churn and scaling, and reads as
      documentation. `[IAM]` `[CFG]`
1.12.13 Security-group quotas: 5 SGs per ENI (adjustable to 16), **60 inbound and 60 outbound rules
      per SG**, and the fact that a referenced SG counts as one rule regardless of member count.
      `[NUM]`
1.12.14 **VPC Endpoints, and why they are not optional.** **Gateway endpoints** (S3 and DynamoDB
      only) are **free**, are a route-table entry, and remove NAT Gateway data-processing charges
      entirely. **Interface endpoints (PrivateLink)** are an ENI in your subnet with private DNS,
      billed per hour per AZ plus per GB, and available for most services. `[NUM]` `[COST]`
1.12.15 The arithmetic that makes this the single most common avoidable cost: QuizStakes writes
      **68 GB/day of document images** to S3. Through a NAT Gateway at $0.045/GB that is
      68 × 0.045 × 365 ≈ **$1,117/year in NAT processing alone**, plus the hourly NAT charge, for
      traffic that never needed to leave AWS. A free S3 Gateway Endpoint removes all of it.
      `[PROVE]` `[COST]`
1.12.16 **PrivateLink** in the other direction: exposing *your* service to another VPC or another
      account via an **endpoint service** behind an NLB, without peering and without route
      exchange.
1.12.17 **VPC Peering** — 1:1, **non-transitive**, no overlapping CIDRs, cross-region and
      cross-account supported, and its O(n²) growth problem. `[TRAP]`
1.12.18 **Transit Gateway** — the hub-and-spoke answer, with route tables, attachments, appliance
      mode, inter-region peering, and per-attachment plus per-GB pricing.
1.12.19 **Site-to-Site VPN** (IPsec over the internet) vs **Direct Connect** (a dedicated private
      circuit) vs **Direct Connect + VPN** for encryption. `[TABLE]`
1.12.20 **VPC DNS**: the Amazon-provided resolver at **base+2**, `enableDnsSupport` and
      `enableDnsHostnames`, **Route 53 Resolver endpoints** (inbound/outbound) for hybrid, and
      **private hosted zones**. `[CFG]` `[X-REF 10]`
1.12.21 **VPC Flow Logs** — connection-level records to CloudWatch Logs or S3, the field list, the
      `ACCEPT`/`REJECT` action, and the fact that they answer "why can't A reach B" (the answer is a
      security group or a route table roughly every time). Read a real log line field by field.
      `[DIAG]` `[SOURCE]`
1.12.22 **Reachability Analyzer** and **Network Access Analyzer** as the static answer to the same
      question, and why they beat guessing. `[CLI]`
1.12.23 **IPv6 in a VPC** — dual-stack, no NAT, `/56` per VPC and `/64` per subnet, and the growing
      cost pressure to adopt it now that public IPv4 is billed. `[COST]` `[RESEARCH]`
1.12.24 **ENIs** — the primary/secondary distinction, the per-instance-type limits that cap pod
      density on EKS, and how an ENI carries the security group.
1.12.25 **MTU and jumbo frames** — 9001 bytes inside a VPC, 1500 over an IGW and most VPN paths, and
      the black-hole symptom of a path-MTU mismatch. `[TRAP]` `[X-REF 10]`

## §1.13 Load balancing and edge

1.13.1 The four load balancer types: **ALB** (L7), **NLB** (L4), **GWLB** (L3, for appliance
      insertion), and **Classic** (deprecated). `[TABLE]`
1.13.2 **ALB** — path- and host-based routing, HTTP header/method/query/source-IP conditions,
      TLS termination with **ACM certificates (free and auto-renewing)**, SNI multi-cert,
      HTTP/2 and gRPC, WebSockets, sticky sessions, weighted target groups, authentication actions
      (OIDC/Cognito), fixed-response and redirect actions, and native ECS/EKS/Lambda/IP targets.
      The default for an HTTP service. `[TABLE]`
1.13.3 **NLB** — L4, ultra-low latency, millions of requests/sec, **static IP per AZ and Elastic IP
      support** (which ALB does not offer and some corporate firewalls require), TLS passthrough or
      termination, UDP, preserved source IP, and no idle-connection cost. `[TABLE]`
1.13.4 **The L4-vs-L7 consequence that matters for gRPC/HTTP-2**: an NLB pins a TCP connection to one
      backend for its lifetime, so long-lived multiplexed connections do not rebalance across a
      scale-out. `[TRAP]` `[X-REF 10]`
1.13.5 **Target groups**: target type (`instance` / `ip` / `lambda` / `alb`), protocol version
      (HTTP1 / HTTP2 / GRPC), health check parameters (`HealthCheckIntervalSeconds`,
      `HealthyThresholdCount`, `UnhealthyThresholdCount`, `Matcher`), **deregistration delay
      (connection draining, default 300 s)**, slow start, and stickiness. `[CFG]` `[NUM]`
1.13.6 **Deregistration delay is the drain-before-terminate mechanism** scenario B.4 requires for the
      payment run: the LB stops sending new requests, in-flight ones finish, then the target leaves.
      It must be longer than your longest request and shorter than your termination grace period.
      `[PROVE]` `[X-REF 19]`
1.13.7 **Cross-zone load balancing** — **on by default for ALB (free), off by default for NLB (and
      billed as cross-AZ data transfer when enabled)**. Without it, an AZ with fewer targets gives
      each of its targets disproportionate load. `[TRAP]` `[NUM]` `[COST]`
1.13.8 **The ALB is itself multi-AZ and scales by adding nodes**, which is why its DNS name resolves
      to multiple changing IPs and why you must never hard-code them or cache the resolution.
      `[TRAP]` `[X-REF 10]`
1.13.9 **Idle timeout** (ALB default 60 s) and the classic 502 from a backend `keepAliveTimeout`
      **shorter** than the LB's idle timeout — the race that produces intermittent 502s under no
      load. `[TRAP]` `[DIAG]` `[NUM]`
1.13.10 **ALB access logs** and the **`ELB 5XX` vs `Target 5XX`** distinction, which tells you
      instantly whether the LB or your app produced the error. `[METRIC]` `[DIAG]`
1.13.11 **CloudFront** — the CDN: origins (S3, ALB, any HTTP), behaviours and precedence, cache
      policies and origin request policies, TTL fields, invalidations vs versioned object keys,
      compression, HTTP/3, signed URLs and signed cookies, **Origin Access Control (OAC)**, geo
      restriction, and **CloudFront Functions vs Lambda@Edge**. `[TABLE]` `[X-REF 15]`
1.13.12 **OAC replaces OAI** and is the current answer for "serve a private S3 bucket through
      CloudFront." `[VERSION-TRAP]`
1.13.13 **AWS WAF** (managed rule groups, rate-based rules, the association points) and **Shield
      Standard vs Advanced**. `[X-REF 13]`
1.13.14 **Route 53** — authoritative DNS: hosted zones (public/private), record types, health checks,
      and the routing policies (simple, weighted, latency-based, geolocation, geoproximity,
      failover, multi-value, IP-based). `[TABLE]`
1.13.15 **Alias records** solve the zone-apex CNAME restriction, resolve to AWS targets, are free of
      query charges, and follow the target's health. The single most useful Route 53 feature.
      `[X-REF 10]`
1.13.16 **DNS-based failover is slow and unreliable** because clients — JVMs above all — ignore TTLs.
      Route 53 failover is a region-level disaster-recovery mechanism, **not** an instance-level
      availability mechanism; that is the load balancer's job. `[TRAP]` `[X-REF 10]`
1.13.17 **Route 53 Application Recovery Controller** (readiness checks, routing controls, zonal
      shift) as the actual answer for evacuating an AZ or region deliberately. `[RESEARCH]`
1.13.18 **ARC zonal shift / zonal autoshift** — the one-command "take this AZ out of rotation" that
      the October 2025 NLB failure argues for. `[RESEARCH]` `[INCIDENT]`

## §1.14 Serverless compute

1.14.1 **Lambda** — event-driven functions, per-request billing in **GB-seconds plus a per-request
      charge**, automatic scaling, no instances.
1.14.2 **The quota table with the real numbers**: memory **128 MB – 10,240 MB in 1 MB increments**
      (one vCPU-equivalent at **1,769 MB**), timeout **900 s**, `/tmp` **512 MB – 10,240 MB**,
      **6 MB** synchronous request and response payload (**200 MB** for a streamed response, **1 MB**
      asynchronous), env vars **4 KB total**, **5 layers**, deployment package **50 MB zipped /
      250 MB unzipped** or **10 GB** as a container image, **1,024 file descriptors** and
      **1,024 processes/threads**, **625 Mbps** network per environment, default **1,000** concurrent
      executions, **75 GB** (now 300 GB) code storage, **500 ENIs per VPC**. `[TABLE]` `[NUM]`
      `[SOURCE]`
1.14.3 **CPU scales linearly with memory** — so raising memory can make a function *cheaper* by
      finishing faster. The AWS Lambda Power Tuning state machine as the way to find the optimum.
      `[PROVE]` `[COST]`
1.14.4 **The execution environment lifecycle**: `Init` (download code, start runtime, run static
      initialisers and constructors) → `Invoke` (run the handler) → `Shutdown`. **Init is billed
      differently and is where a JVM spends its cold start.** `[FLOW]`
1.14.5 **Cold start** as the defining characteristic: 800–1,500 ms for an uninstrumented Java 21
      function, and worse with Spring. It happens on the first invoke **and on every scale-out**, not
      just the first ever. `[NUM]` `[TRAP]`
1.14.6 **The four mitigations, ranked**: **SnapStart** (snapshot the initialised JVM with CRaC and
      restore it — **50–90 ms**, Java 11/17/21, x86_64 and arm64, **no additional charge**),
      smaller deployment packages and fewer classes, **Provisioned Concurrency** (pre-warmed, but you
      now pay for idle capacity, which undercuts the model), and choosing a lighter runtime or
      GraalVM native image. `[TABLE]` `[VERSION-TRAP]` `[NUM]`
1.14.7 **SnapStart's three hazards**, which is what an interviewer actually probes: **stale
      connections** in the snapshot, **duplicated randomness** (every restored environment shares the
      seeded `SecureRandom` state unless you use the CRaC hooks), and **cached credentials/state**
      captured at snapshot time. The `Resource` / `beforeCheckpoint` / `afterRestore` hooks are the
      fix. `[TRAP]` `[API]` `[RESEARCH]`
1.14.8 **Concurrency**: account-level (default 1,000), **reserved concurrency** (a guaranteed floor
      *and* a hard ceiling for one function — setting it to 0 is the kill switch), **provisioned
      concurrency** (pre-initialised environments), and the **burst rate of 1,000 environments every
      10 seconds per function**. `[VERSION-TRAP]` `[NUM]` `[CFG]`
1.14.9 **The concurrency formula**: `concurrency = requests/sec × average duration in seconds`.
      Worked against QuizStakes' 40/sec card deposits at 180 ms PSP capture. `[PROVE]` `[NUM]`
1.14.10 **Statelessness with a twist**: environments are **reused**, so globals persist between
      invocations. Good for connection reuse and caching (initialise the SDK client outside the
      handler); dangerous if you accidentally leak request state between invocations. `[TRAP]`
1.14.11 **Invocation models**: synchronous (`RequestResponse`), asynchronous (`Event` — with an
      internal queue, **2 automatic retries**, a configurable maximum event age, and an
      on-failure destination), and **event source mappings** (a Lambda-managed poller for SQS,
      Kinesis, DynamoDB Streams, MSK, Kafka, MQ, DocumentDB). `[TABLE]` `[X-REF 14]`
1.14.12 **Destinations vs DLQ** — `OnSuccess`/`OnFailure` destinations carry the full invocation
      record and are the modern replacement for the async DLQ. `[VERSION-TRAP]`
1.14.13 **Lambda in a VPC**: Hyperplane ENIs shared per (subnet, security group) combination removed
      the old per-execution ENI cold-start penalty, but a VPC-attached function **still has no
      internet access without a NAT Gateway or a VPC endpoint**. `[VERSION-TRAP]` `[TRAP]`
1.14.14 **Layers, extensions (internal and external), the Lambda Runtime API, and custom runtimes**
      (`bootstrap`, `provided.al2023`).
1.14.15 **Lambda Durable Functions** — checkpointed, resumable executions with a durable-operation
      SDK, up to **3,000 durable operations** and **100 MB of persisted state** per execution, and
      millions of concurrent running executions. This is the answer to "but Lambda is only 15
      minutes" in 2026. `[VERSION-TRAP]` `[RESEARCH]` `[NUM]`
1.14.16 **Lambda MicroVMs** — Arm64, up to **8 hours (28,800 s)** per execution, image-based, with
      per-vCPU connection and RPS ceilings. `[RESEARCH]` `[NUM]`
1.14.17 **Lambda Managed Instances** — a Bottlerocket-based execution environment with higher file
      descriptor (4,096) and thread limits. `[RESEARCH]`
1.14.18 **Good fits**: S3/SQS/EventBridge event processing, scheduled jobs, glue code, spiky or
      unpredictable traffic, genuinely low-volume services. **Bad fits**: sustained high throughput
      (containers win past a crossover), long-running work, anything needing a large connection pool,
      and strict low-latency APIs. Mapped to QuizStakes: the bank-file arrival trigger is a Lambda;
      `FundsLedger` explicitly is not (scenario B.1). `[TABLE]`
1.14.19 **API Gateway** — three flavours: **REST API** (full-featured: request/response mapping
      templates, usage plans and API keys, WAF, private endpoints, caching), **HTTP API** (cheaper,
      faster, fewer features, JWT authorizers), and **WebSocket API**. `[TABLE]`
1.14.20 **Integration timeouts**: REST API default **29 s**, raisable via Service Quotas to
      **300 s** for Regional and private APIs but **not** edge-optimized; HTTP API a hard **30 s**.
      `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
1.14.21 **Authorizers**: IAM (SigV4), Cognito user pools, JWT (HTTP API), and Lambda authorizers
      (token vs request, with a policy cache TTL). `[X-REF 13]`
1.14.22 **Throttling and usage plans** — account-level 10,000 rps with a 5,000 burst, per-stage,
      per-method and per-API-key limits, and the `429 TooManyRequests` response. Note the mismatch
      with Lambda's 1,000 default concurrency. `[NUM]` `[X-REF 12]`
1.14.23 **Lambda Function URLs** as the zero-infrastructure HTTP front door, and what you give up
      (no WAF association directly, no usage plans, no request mapping).
1.14.24 **Step Functions** — Standard vs **Express** workflows (duration, pricing model, exactly-once
      vs at-least-once), the Amazon States Language, `Task`/`Choice`/`Map`/`Parallel`/`Wait`, retry
      and catch blocks, **Distributed Map** for large-scale fan-out, direct SDK integrations, and
      **callback patterns with a task token**. The managed alternative to a hand-rolled saga
      orchestrator. `[TABLE]` `[X-REF 14]`
1.14.25 The Step Functions cost trap: Standard workflows bill **per state transition**, so a chatty
      state machine at QuizStakes' 2.8M settlements/day is arithmetically indefensible; Express bills
      per request and duration. `[COST]` `[PROVE]`
1.14.26 **EventBridge** — the event bus: default vs custom vs partner buses, **content-based rule
      patterns**, targets, input transformers, archive and replay, the **schema registry**,
      **EventBridge Pipes** (source → filter → enrich → target), and **EventBridge Scheduler** (the
      modern replacement for CloudWatch Events cron, with one-time schedules and a flexible time
      window). `[X-REF 14]`
1.14.27 **EventBridge Scheduler + a distributed lock** is the QuizStakes `PaymentRun` trigger
      (scenario B.3), and the reason "central scheduler plus leader election, never per-instance
      cron" is written into B.4. `[X-REF 14]`
1.14.28 **AWS AppSync** (managed GraphQL) and **App Runner** / **Elastic Beanstalk** / **Amplify** as
      the remaining managed-compute options, named and bounded. `[X-REF 12]`

## §1.15 Containers on AWS

1.15.1 **ECR** — the registry: private and public repositories, image scanning (basic vs enhanced via
      Inspector), lifecycle policies, immutable tags, replication, and pull-through cache.
      `[X-REF 19]`
1.15.2 **ECS** — AWS's own orchestrator: a **task definition** (image, CPU/memory at task and
      container level, environment, secrets, **task role** and **execution role**, log configuration,
      health check, `essential`, port mappings) and a **service** (desired count, deployment
      configuration, load-balancer registration, autoscaling, placement strategies). `[TABLE]`
1.15.3 **The two IAM roles on every ECS task, and the distinction people get wrong**: the
      **execution role** is used by the ECS *agent* to pull the image and fetch secrets before the
      container starts; the **task role** is what your application code assumes at runtime.
      `[TRAP]` `[IAM]`
1.15.4 **Launch types**: **EC2** (you own the fleet: cheaper at scale, bin-packing, more control,
      more work), **Fargate** (serverless per-task, no instances to patch or bin-pack, higher unit
      price but often cheaper in total once engineering time counts), and now **ECS Managed
      Instances** (AWS provisions and patches the EC2 fleet, you keep EC2 pricing) and **ECS Express
      Mode** (image + two roles → Fargate + ALB + HTTPS + autoscaling + an `*.ecs.*.on.aws` URL, up
      to 25 services per ALB). `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
1.15.5 **Fargate's valid CPU/memory combinations are a fixed lattice**, not arbitrary: 256 (.25 vCPU)
      → 512 MB/1/2 GB; 512 → 1–4 GB; 1024 → 2–8 GB; 2048 → 4–16 GB in 1 GB steps; 4096 → 8–30 GB in
      1 GB steps; 8192 → 16–60 GB in 4 GB steps; 16384 → 32–120 GB in 8 GB steps. Requesting an
      invalid pair fails the task definition. `[TABLE]` `[NUM]` `[TRAP]`
1.15.6 Mapping QuizStakes' heap profile onto that lattice: `FundsLedger` at 12 GB heap needs a
      16 GB+ task (4096/16384 CPU/mem) with headroom for metaspace, code cache, thread stacks and
      direct buffers; `DocumentVerification` at 8 GB with 2–6 MB humongous buffers needs more.
      `[PROVE]` `[X-REF 06]`
1.15.7 **`awsvpc` network mode** gives every task its own ENI, its own private IP and its own
      security group — which is what makes SG-to-SG rules work for containers, and what caps task
      density on EC2 launch type. Contrast `bridge` and `host`. `[TABLE]`
1.15.8 **Service deployment**: rolling update with `minimumHealthyPercent` / `maximumPercent`,
      **deployment circuit breaker with automatic rollback**, blue/green via CodeDeploy, and
      **ECS Service Connect** vs the older Service Discovery (Cloud Map). `[CFG]` `[RESEARCH]`
1.15.9 **Capacity providers** — `FARGATE`, `FARGATE_SPOT`, and ASG-backed providers with managed
      scaling and managed termination protection. The mechanism behind "run the batch on Spot".
1.15.10 **EKS** — managed Kubernetes control plane; you own the data plane unless you use
      **EKS Auto Mode** (AWS manages nodes, autoscaling with Karpenter, and core add-ons).
      `[X-REF 19]`
1.15.11 **IRSA vs EKS Pod Identity**, as a table: OIDC provider per cluster + trust-policy JSON vs a
      single service trust and an EKS-side mapping; projected JWT volume vs a node-local agent;
      role session tags supported only by Pod Identity; Pod Identity is EKS-only while IRSA also
      covers EKS Anywhere, ROSA and self-managed clusters; Pod Identity is built into Auto Mode.
      `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
1.15.12 **The VPC CNI and pod IP exhaustion** — every pod gets a VPC IP from the subnet, ENIs per
      instance type cap pod density, and prefix delegation is the mitigation. The reason a `/24` app
      subnet is a mistake. `[TRAP]` `[NUM]` `[X-REF 19]`
1.15.13 **Karpenter vs Cluster Autoscaler**, named with the one-line difference (provision the right
      instance for the pending pods vs scale a predefined ASG).
1.15.14 **ECS vs EKS as a decision**, argued rather than asserted: ECS has no control plane to run,
      native IAM per task, a fraction of the concept count and a lower operational floor; EKS gives
      portability, an ecosystem, and an existing team's muscle memory. `[X-REF 19]`

## §1.16 Configuration and secrets

1.16.1 **The twelve-factor rule**: configuration that varies by environment lives in the environment,
      not in the code. The **same artefact** — the same image, the same JAR — is promoted from dev to
      staging to prod with only configuration differing. If you rebuild per environment you are
      testing one artefact and shipping another. Scenario B.4: "versioned, promoted through
      environments, never edited in place." `[TRAP]`
1.16.2 **Environment variables** — universal and simple; fine for non-secret configuration; visible
      to anything that can describe the task definition or read `/proc/<pid>/environ`.
1.16.3 **SSM Parameter Store** — hierarchical (`/quizstakes/prod/fundsledger/db/host`), versioned,
      IAM-controlled, with `String` / `StringList` / **`SecureString`** (KMS-encrypted) types.
      **Standard parameters are free** (4 KB, 10,000 per account); advanced parameters cost per
      parameter per month and allow 8 KB and policies. `[NUM]` `[CFG]`
1.16.4 **Secrets Manager** — Parameter Store plus **native rotation** (managed rotation for RDS,
      Redshift and DocumentDB; a Lambda rotation function for everything else), cross-region
      replication, resource policies, and a per-secret monthly charge plus per-10,000-API-calls
      charge. `[NUM]` `[COST]`
1.16.5 **The rule of thumb**: Parameter Store for configuration and low-churn secrets; Secrets
      Manager where **rotation** matters — which for QuizStakes means the PSP, identity-vendor and
      banking-partner credentials scenario B.4 says are "rotated, never in config or environment."
1.16.6 **AppConfig** — validated, gradually-rolled-out dynamic configuration with automatic rollback
      on a CloudWatch alarm. For values you change at runtime: feature flags, the identity vendor's
      timeout, the orphan-stake reaper interval. `[RESEARCH]`
1.16.7 **Injecting secrets by ARN**, not by value: ECS `secrets` blocks and Lambda's Parameters and
      Secrets extension resolve at start without the value ever appearing in the definition, the
      console, CloudTrail or an error report. Show the ECS task-definition YAML. `[CFG]` `[TRAP]`
1.16.8 **A secret fetched at startup and cached forever defeats rotation.** Either fetch on a TTL or
      handle the auth failure by re-fetching. This is the bug rotation introduces. `[TRAP]`
1.16.9 **Never in Git** — and what to do when it happens anyway: rotate first, clean history second.
      `[X-REF 17]` `[X-REF 13]`
1.16.10 **Spring's three integration points**: `spring.config.import=aws-parameterstore:/…`,
      `aws-secretsmanager:…`, and `@ConfigurationProperties` binding over them. `[API]` `[X-REF 07]`

## §1.17 Observability primitives

1.17.1 **CloudWatch Metrics** — namespace, metric name, up to 30 dimensions, statistics, 1-minute
      standard and **1-second high resolution**, retention that rolls up (1 s for 3 hours, 1 min for
      15 days, 5 min for 63 days, 1 hour for **15 months**). `[NUM]`
1.17.2 **Every unique dimension combination is a separately billed metric.** Putting a client id or a
      request id in a dimension produces a five-figure bill from one line of code. The cardinality
      trap. `[TRAP]` `[COST]` `[X-REF 20]`
1.17.3 **Custom metric pricing**: $0.30/metric/month for the first 10,000, $0.10 for the next
      240,000, $0.05 for the next 750,000, $0.02 above 1,000,000; first 10 free. `[NUM]` `[COST]`
1.17.4 **Embedded Metric Format (EMF)** as the way to emit metrics from a log line without a
      `PutMetricData` call — cheaper, asynchronous, and dimension-aware. `[RESEARCH]`
1.17.5 **CloudWatch Logs** — log groups → log streams → events, **retention that must be set
      explicitly or you pay to store forever**, Logs Insights query syntax, metric filters,
      subscription filters (to Kinesis/Firehose/Lambda/OpenSearch), and the Standard vs **Infrequent
      Access** log class. `[TRAP]` `[COST]`
1.17.6 **CloudWatch Alarms** — the `EvaluationPeriods` / `DatapointsToAlarm` (M-of-N) pair,
      `TreatMissingData`, composite alarms, anomaly detection, and alarm actions (SNS, Auto Scaling,
      EC2 actions). `[CFG]` `[X-REF 20]`
1.17.7 **Dashboards**, **Metric Math**, **Contributor Insights**, and **Synthetics canaries**.
1.17.8 **CloudWatch Application Signals** — auto-instrumented RED metrics and SLOs for EC2, ECS, EKS
      and Lambda, with **Transaction Search** giving 100% span retention. `[RESEARCH]`
1.17.9 **X-Ray** — segments, subsegments, the trace header (`X-Amzn-Trace-Id`), sampling rules, the
      service map, and **the fact that the X-Ray SDKs are in maintenance mode with OpenTelemetry /
      ADOT as the recommended path, including an X-Ray OTLP endpoint**. `[VERSION-TRAP]`
      `[RESEARCH]` `[X-REF 20]`
1.17.10 **CloudTrail** — management events (free for the first copy), **data events** (S3 object-level,
      Lambda invoke — billed and off by default), Insights events, organization trails, and the
      Event history vs a trail. This is your audit log and your incident evidence. `[X-REF 13]`
1.17.11 **AWS Config** — resource configuration history, rules, conformance packs, and remediation.
      The "was this bucket ever public" question. `[X-REF 13]`
1.17.12 **AWS Health Dashboard** (personal and public) and the **Post-Event Summary** as first-party
      incident sources. `[INCIDENT]`
1.17.13 **Amazon Managed Service for Prometheus** and **Amazon Managed Grafana** as the escape hatch
      when CloudWatch's high-cardinality querying is the constraint. `[X-REF 20]`

## §1.18 The AWS SDK for Java v2 surface

1.18.1 **v1 vs v2** — `com.amazonaws` vs `software.amazon.awssdk`; v1 reached **end of support on
      31 December 2025**. v2 is modular (one artifact per service), non-blocking-capable, builder-based
      and immutable. `[VERSION-TRAP]`
1.18.2 **Client construction**: `S3Client.builder().region(Region.EU_WEST_1).credentialsProvider(...).build()`,
      and the rule that a client is **thread-safe, expensive to create and must be a singleton**
      (a Spring `@Bean`). Creating one per request is the most common performance bug. `[API]` `[TRAP]`
1.18.3 **The default credentials provider chain, in order**: Java system properties → environment
      variables → web identity token (`AWS_WEB_IDENTITY_TOKEN_FILE`) → the shared profile file →
      the ECS container credentials endpoint → **IMDS**. Knowing the order is how you debug "it works
      locally but not in the task." `[FLOW]` `[TRAP]`
1.18.4 **Region resolution** and endpoint overrides — the equivalent chain, and
      `endpointOverride(URI)` for LocalStack. `[CFG]`
1.18.5 **Sync vs async clients**: `S3Client` (Apache HTTP client by default) vs `S3AsyncClient`
      (Netty by default), `AwsCrtAsyncHttpClient` and `AwsCrtHttpClient` (faster startup, smaller
      memory footprint, lower p90 latency, connection health monitoring and DNS load balancing —
      GA since SDK 2.20.0, GraalVM native-image support since 2.28.7). `[TABLE]` `[RESEARCH]`
1.18.6 **The CRT-based S3 client** (`S3AsyncClient.crtBuilder()`) — automatic multipart and
      byte-range parallelism, and the `S3TransferManager` on top of it. The right answer for
      QuizStakes' 2–6 MB document images. `[API]`
1.18.7 **`S3Presigner`** for presigned URLs, and `S3Utilities` for URL parsing. `[API]`
1.18.8 **`ClientOverrideConfiguration`** — `retryStrategy` / `RetryPolicy`, `apiCallTimeout`,
      `apiCallAttemptTimeout`, `addExecutionInterceptor`, and the metric publisher. The **default
      retry mode** (`legacy` → `standard` → **`adaptive`**) and what each does to a throttled call.
      `[CFG]` `[NUM]` `[X-REF 10]`
1.18.9 **`SdkException` taxonomy**: `AwsServiceException` (with `awsErrorDetails()`, the error code,
      the request id) vs `SdkClientException` vs the per-service typed exceptions
      (`NoSuchKeyException`, `ConditionalCheckFailedException`, `ProvisionedThroughputExceededException`).
      Retryable vs not. `[API]` `[TABLE]`
1.18.10 **Paginators** — `listObjectsV2Paginator()` returning an `SdkIterable`, and why manual
      `NextToken` loops are a bug factory. `[API]`
1.18.11 **Waiters** — `S3Waiter`, `DynamoDbWaiter` — for control-plane eventual consistency. `[API]`
1.18.12 **DynamoDB Enhanced Client** — `DynamoDbTable<T>`, `TableSchema.fromBean` /
      `StaticTableSchema` / `fromImmutableClass` for Java **records**, `@DynamoDbPartitionKey`,
      `@DynamoDbSecondaryPartitionKey`, `Expression` and `ConditionCheck`. `[API]`
1.18.13 **`software.amazon.awssdk.metrics`** — publishing SDK client metrics to CloudWatch, and what
      `ApiCallDuration` vs `ServiceCallDuration` vs `MarshallingDuration` tell you. `[METRIC]`
1.18.14 **`aws-crt` and GraalVM native image** — what compiles, what needs reflection configuration,
      and the startup-time payoff for Lambda. `[X-REF 06]`
1.18.15 **The `aws` CLI v2** as the other client: profiles, `--query` (JMESPath), `--output`,
      `assume-role` in a profile, and `aws sso login`. `[CLI]`

## §1.19 Spring Cloud AWS

1.19.1 **What it is and is not**: an auto-configuration layer over the AWS SDK v2, maintained by the
      community `io.awspring.cloud` project — not by AWS, and not the same thing as the deprecated
      `spring-cloud-aws` from Spring Cloud proper. `[VERSION-TRAP]`
1.19.2 **The compatibility matrix**: 3.0.x → Boot 3.0–3.1; 3.1.x → 3.2; 3.2.x–3.3.x → 3.2–3.3;
      **3.4.x → Boot 3.4/3.5, Spring Framework 6.2, Spring Cloud 2024.0/2025.0**; **4.0.x → Boot
      4.0, Spring Framework 7.0, Spring Cloud 2025.1**. All 3.x and 4.x use AWS SDK **v2**.
      `[TABLE]` `[RESEARCH]`
1.19.3 **The starters by artifact id**: `spring-cloud-aws-starter-s3`, `-sqs`, `-sns`, `-ses`,
      `-dynamodb`, `-parameter-store`, `-secrets-manager`, `-cloudwatch`, plus 4.x's Spring
      Integration for AWS and the Kinesis Stream binder. **RDS, EC2, ElastiCache and CloudFormation
      support were removed in 3.x.** `[TABLE]` `[VERSION-TRAP]`
1.19.4 **`S3Template`** — `store`/`read`/`download`/`upload`/`createSignedGetURL`/`createSignedPutURL`,
      and the `s3://bucket/key` `Resource` protocol resolver. `[API]`
1.19.5 **`@SqsListener`** — the listener container, acknowledgement modes, batch listeners,
      `@SqsListener(queueNames, maxConcurrentMessages, pollTimeoutSeconds)`, visibility extension,
      and `SqsTemplate`. `[API]` `[X-REF 14]`
1.19.6 **`DynamoDbTemplate`** over the Enhanced Client. `[API]`
1.19.7 **`spring.config.import`** for Parameter Store and Secrets Manager, including optional
      imports, prefixes and reload. `[CFG]`
1.19.8 **`spring.cloud.aws.region.static`**, `spring.cloud.aws.credentials.*`,
      `spring.cloud.aws.endpoint` (the single knob that points everything at LocalStack). `[CFG]`
1.19.9 **Micrometer + Spring Boot Actuator** health indicators contributed per integration.
      `[X-REF 20]`
1.19.10 The honest positioning: for a single service using two AWS APIs, the raw SDK plus two `@Bean`
      definitions is often clearer than the starter. Say when each wins. `[TRAP]`

## §1.20 Infrastructure as code

1.20.1 The origin problem: a console-built environment cannot be reviewed, reproduced, diffed or
      rolled back, and the person who built it is the documentation.
1.20.2 **CloudFormation** — the substrate everything else compiles to. Template anatomy
      (`Parameters`, `Mappings`, `Conditions`, `Resources`, `Outputs`, `Transform`), stacks,
      **change sets**, **drift detection**, stack policies, `DeletionPolicy` and
      `UpdateReplacePolicy`, nested stacks, StackSets, and the intrinsic functions (`Ref`,
      `Fn::GetAtt`, `Fn::Sub`, `Fn::ImportValue`). `[TABLE]`
1.20.3 **Drift-aware change sets** — the three-way comparison of new template, old template and
      actual resource state, so a console change is no longer silently overwritten.
      `[VERSION-TRAP]` `[RESEARCH]`
1.20.4 **The update failure mode**: `UPDATE_ROLLBACK_FAILED` and what it means to be stuck. `[TRAP]`
1.20.5 **CDK** — imperative code (TypeScript, Python, **Java**, C#, Go) synthesising CloudFormation.
      Constructs L1/L2/L3, the app/stack/construct tree, `cdk diff`, `cdk deploy`, bootstrapping and
      the `CDKToolkit` stack, assets, and context.
1.20.6 **`cdk diff` does not detect drift** — it diffs the synthesised template against the deployed
      template, not against reality. `[TRAP]` `[RESEARCH]`
1.20.7 **SAM** — the Lambda-shaped CloudFormation transform, `sam local invoke` / `start-api`, and
      when it beats CDK (small serverless services) and when it does not. `[TABLE]`
1.20.8 **Terraform** — HCL, providers, **state** (and remote state locking in S3+DynamoDB or S3 with
      native locking), `plan`/`apply`, modules, workspaces, `import`, and the fact that it is the
      default when the estate is not AWS-only. **CDKTF** as the hybrid. `[TABLE]`
1.20.9 **The comparison table**: state management (CloudFormation-managed vs self-managed), drift
      handling, multi-cloud, language, blast radius of a bad apply, ecosystem, and team ramp.
      `[TABLE]`
1.20.10 **Immutable infrastructure** as the underlying principle, and why "just SSH in and fix it"
      is how environments diverge.
1.20.11 **Where IaC does not belong**: data (a database's contents), and anything with a lifecycle
      longer than the stack.
1.20.12 **CI/CD on AWS**: CodePipeline / CodeBuild / CodeDeploy / CodeArtifact, and the honest note
      that most teams use GitHub Actions with **OIDC federation into an IAM role** rather than
      long-lived keys. `[IAM]` `[X-REF 17]`

## §1.21 The cost model

1.21.1 The framing to use in an interview: **cost is a design constraint like latency.** "We chose X
      over Y because it was 3× cheaper at our volume and the latency difference did not matter" is a
      strong, senior-sounding sentence.
1.21.2 **The four things you are billed for**, always: compute time, storage volume, **data
      transfer**, and requests/operations. Everything else is a variation.
1.21.3 **Data transfer, the one people miss**, with the 2026 numbers: **ingress free**; internet
      egress **first 100 GB/month free**, then ~$0.09/GB to 10 TB, $0.085 to 50 TB, $0.07 to 150 TB,
      $0.05 beyond; **cross-AZ $0.01/GB in *each* direction**; cross-region $0.02–$0.09/GB; same-AZ
      over private IPv4 free. `[TABLE]` `[NUM]` `[VERSION-TRAP]`
1.21.4 **The cross-AZ charge is in tension with the multi-AZ resilience rule**, and the resolution is
      AZ-aware routing for high-volume internal chatter (topology-aware hints, zonal endpoints), not
      fewer AZs. `[PROVE]` `[TRAP]`
1.21.5 **NAT Gateway** — ~$0.045/hour **plus ~$0.045/GB processed**, per NAT, and you want one per AZ.
      Worked against QuizStakes' 68 GB/day of image traffic. `[COST]` `[PROVE]`
1.21.6 **Forgotten resources**: unattached EBS volumes (you pay for the volume, not the attachment),
      old snapshots, idle load balancers (~$16–20/month each with zero traffic), **unassociated
      Elastic IPs and now all public IPv4 addresses**, oversized non-prod running 24/7, CloudWatch log
      groups with no retention, and abandoned accounts. Individually small, collectively enormous.
      `[TABLE]`
1.21.7 **Over-provisioning** — instances sized for a peak that never comes, RDS at 8% CPU, and
      high-cardinality CloudWatch metrics.
1.21.8 **No commitment discounts** — steady-state workloads on On-Demand pay 30–72% more than
      necessary. Savings Plans are the largest single easy win. Compute SP vs EC2 Instance SP vs
      Reserved Instances vs **Database Savings Plans** (new). `[TABLE]` `[RESEARCH]`
1.21.9 **Per-request services at volume** — Lambda, API Gateway, Step Functions and DynamoDB
      on-demand are wonderfully cheap at low volume and cross over past a threshold. Do the
      arithmetic before the architecture is fixed. `[PROVE]` `[COST]`
1.21.10 **The tooling**: Cost Explorer, **Cost and Usage Report (CUR 2.0)** into Athena, Budgets with
      alerts and actions, Compute Optimizer, Trusted Advisor, **Cost Optimization Hub**, and
      Anomaly Detection. `[TABLE]`
1.21.11 **Tagging for attribution** — `Environment`, `Team`, `Service`, `CostCentre` — enforced with
      tag policies and cost-allocation tag activation, because untagged spend is unownable spend.
1.21.12 **Practices that actually move the number**: S3 lifecycle policies, log retention, non-prod on
      a schedule (nights and weekends off is roughly a **65%** saving), Spot for CI and batch,
      Graviton, `gp2 → gp3`, S3 Gateway Endpoints, and right-sizing. `[TABLE]` `[NUM]`
1.21.13 **FinOps as a practice**, and the one organisational point: cost accountability has to sit
      with the team that can change the architecture. `[X-REF 22]`

## §1.22 The Well-Architected Framework

1.22.1 **The six pillars**: Operational Excellence, Security, Reliability, Performance Efficiency,
      Cost Optimization, **Sustainability**. Naming all six — most candidates name five. `[SOURCE]`
      `[TRAP]`
1.22.2 The **general design principles**: stop guessing capacity, test at production scale, automate
      to make architectural experimentation easier, allow for evolutionary architectures, drive
      architectures using data, and improve through game days.
1.22.3 Each pillar's design principles, one leaf per pillar, with the QuizStakes decision each one
      would challenge. `[TABLE]`
1.22.4 **The Well-Architected Tool and lenses** (Serverless, SaaS, Financial Services), and the
      review as a real meeting rather than a document.
1.22.5 How to use the pillars **as an interview scaffold**: when asked "critique this architecture",
      walking the six pillars is a defensible structure that never runs dry.
1.22.6 The **SAA-C03 domain weights** as an independent completeness probe: Secure 30%, Resilient
      26%, High-Performing 24%, Cost-Optimized 20%. If your answer never mentions security, you are
      missing the largest domain. `[RESEARCH]`

---

# PART 2 — INTERMEDIATE

## §2.1 Choosing compute — the decision procedure

2.1.1 The ordered question list, asked in this order and not another: (1) is the work
      request/response or event-driven? (2) what is the duration distribution? (3) what is the
      concurrency shape — steady, spiky, or idle-with-bursts? (4) does it need a warm connection
      pool or local state? (5) what is the latency budget, including cold start? (6) what does the
      team already operate? `[FLOW]`
2.1.2 **The master compute table**: EC2, ECS on EC2, ECS on Fargate, ECS Managed Instances, ECS
      Express Mode, EKS, EKS Auto Mode, Lambda, Lambda MicroVMs, App Runner, Elastic Beanstalk,
      Batch — scored on unit cost, operational burden, cold start, max duration, state tolerance,
      scaling granularity and lock-in. `[TABLE]`
2.1.3 **The crossover arithmetic between Lambda and Fargate**, worked: at what request rate ×
      duration does a Lambda bill exceed one always-on 1 vCPU/2 GB Fargate task? Do it with real
      numbers for QuizStakes' 40/sec card deposits and its 1,200/sec stake reservations. `[PROVE]`
      `[COST]`
2.1.4 Applying the procedure to each QuizStakes service and defending Appendix B.1's answers:
      `ApplicationGateway` long-running autoscaled containers; `BankDeposits` file-arrival trigger
      → worker pool (idle 23 hours a day makes this the strongest Lambda/Fargate-Spot case in the
      estate); `FundsLedger` **explicitly not function-based** because a cold connection pool on the
      hottest write path and lost locality for the reservation index cost more than elastic scaling
      buys; `BankWithdrawal` a scheduled run job with a single leader. `[PROVE]`
2.1.5 **Where "serverless" stops being cheaper**, stated as a rule with the arithmetic behind it,
      not as an opinion.
2.1.6 **The operational-cost term nobody prices**: on-call surface, patch cadence, and the number of
      concepts a new joiner must learn. Argue that Fargate's unit-price premium is frequently
      negative once this is counted.
2.1.7 **Right-sizing as a procedure**: measure, use Compute Optimizer, change one dimension, measure
      again. And the JVM-specific twist that a container's CPU limit changes
      `Runtime.availableProcessors()`, GC thread counts and ForkJoin pool sizing. `[X-REF 06]`
      `[X-REF 19]`

## §2.2 Choosing storage

2.2.1 The decision tree: does it need POSIX semantics? → EFS/FSx. Does one instance own it and need
      block-level IO? → EBS. Is it write-once-read-many, large, or shared by many readers? → S3.
      Is it structured and queried? → a database, not storage. `[FLOW]`
2.2.2 **The master storage table**: instance store, EBS gp3/io2, EFS, FSx, S3 Standard, S3 IA,
      Glacier tiers, S3 Express One Zone — scored on latency, throughput, durability, AZ scope,
      shareability, cost per GB-month, and cost per operation. `[TABLE]`
2.2.3 **The QuizStakes storage map, defended**: 68 GB/day of 2–6 MB document images in S3 with a
      90-day transition (never in a database, never on EBS); bank files in S3, immutable and
      checksummed, under Object Lock as a regulatory artefact; the 7.2B-row/year ledger in a
      relational store with monthly range partitions and detach-and-archive to columnar cold storage.
      `[PROVE]` `[COST]`
2.2.4 **Cost per GB-month arithmetic across the classes**, worked on 68 GB/day × 7 years, showing
      what lifecycle policy actually saves. `[PROVE]` `[COST]`
2.2.5 **The retrieval-fee trap**: IA and Glacier are cheaper to store and more expensive to read, so
      a class transition that predates an unexpected access pattern *increases* the bill. Model it.
      `[TRAP]` `[COST]`
2.2.6 **The 128 KB minimum billable size** means IA is actively worse than Standard for small
      objects. QuizStakes' 400-byte `ApplicationHistory` records must never be individual S3 objects.
      `[PROVE]` `[TRAP]`
2.2.7 **Snapshot economics**: incremental, but you pay for the unique blocks across the whole chain,
      and deleting the "oldest" snapshot does not free what later ones reference. `[TRAP]`

## §2.3 Choosing a database

2.3.1 The procedure: access patterns first, then consistency requirement, then scale, then
      operational fit — never "we'll use DynamoDB because it scales." `[FLOW]` `[X-REF 22]`
2.3.2 **The master database table**: RDS Postgres, Aurora Postgres, Aurora Serverless v2, Aurora
      DSQL, DynamoDB, ElastiCache/Valkey, MemoryDB, DocumentDB, Keyspaces, Neptune, Timestream,
      OpenSearch, Redshift, Athena-over-S3 — scored on data model, consistency, transactional scope,
      scaling axis, latency, ops burden and lock-in. `[TABLE]`
2.3.3 **The relational default argument**: constraints and transactions *are* the product for
      QuizStakes (scenario B.2 says exactly this), and a database that cannot express "these four
      ledger entries commit together or not at all" is disqualified regardless of its scaling story.
      `[PROVE]`
2.3.4 **When DynamoDB genuinely wins**: known access patterns, extreme scale, single-item atomicity,
      no cross-entity invariants, and a willingness to model backwards from queries. QuizStakes'
      idempotency-key table is a legitimate DynamoDB candidate; the ledger is not. `[PROVE]`
2.3.5 **The `ApplicationHistory` contested decision** (scenario B.2 marks it "Yes"): 2.6M
      records/day, ~400 bytes, write-heavy, read-light, never updated, 7-year retention. Argue both
      the append-only wide-column answer and the relational-partition answer with the arithmetic.
      `[PROVE]` `[NUM]`
2.3.6 **Polyglot persistence and its real cost**: each additional store is another backup story,
      another failover story, another set of credentials, and another on-call runbook. `[X-REF 22]`
2.3.7 **Migration paths and DMS** — homogeneous vs heterogeneous, CDC mode, and the Schema
      Conversion Tool. Named and bounded. `[X-REF 09]`

## §2.4 EC2 capacity, purchasing and Spot in depth

2.4.1 **Savings Plans arithmetic**: commitment in $/hour, coverage vs utilisation, the difference
      between a Compute SP (flexible across region, family, and even Fargate/Lambda) and an EC2
      Instance SP (deeper discount, family- and region-locked). Worked against QuizStakes' 44
      steady-state instances. `[PROVE]` `[COST]`
2.4.2 **Reserved Instances** — standard vs convertible, the marketplace, and why Savings Plans have
      largely superseded them for compute.
2.4.3 **Spot mechanics**: the Spot price, capacity pools, the **two-minute interruption notice**
      delivered as an IMDS field and an EventBridge event, `rebalance recommendation` (which arrives
      *earlier*), interruption behaviours (terminate/stop/hibernate), and **capacity-optimized**
      vs `lowest-price` allocation strategies. `[FLOW]` `[CFG]`
2.4.4 **Designing for Spot**: diversify across instance types and AZs, checkpoint, drain on the
      notice, keep a small On-Demand base, and never put a leader on it. `[BUILD-adjacent]`
2.4.5 **Capacity Reservations** (On-Demand Capacity Reservations, zonal, and their interaction with
      Savings Plans) as the answer to "will there actually be capacity in `eu-west-1b` at 20:00 on
      match night?" — a real question at QuizStakes' 55k concurrent-session peak. `[TRAP]`
2.4.6 **`InsufficientInstanceCapacity`** as a real error class, and why an ASG spanning three AZs and
      four instance types is a capacity strategy, not just a resilience one. `[DIAG]` `[TRAP]`
2.4.7 **Burstable credit arithmetic**: a `t3.medium` earns 24 credits/hour with a 20% baseline per
      vCPU; compute how long it survives at 60% CPU and when it throttles. `[PROVE]` `[NUM]`
      `[METRIC]`

## §2.5 S3 in depth

2.5.1 **Presigned URL design, end to end**, for the QuizStakes document-upload path inside its 2 s
      accept budget: the client asks the service for a URL, the service authorises the *client* and
      scopes the key to `applications/{applicationId}/documents/{documentId}`, the client PUTs
      directly, and S3 emits an event that starts verification. `[FLOW]`
2.5.2 **Why the presigned-URL pattern exists**: proxying a 6 MB upload through `ApplicationGateway`
      (2 GB heap, 12–40 instances) consumes heap, threads, bandwidth and the request timeout, and it
      turns a stateless tier into a bandwidth-bound one. Compute the heap and thread cost at 24k
      uploads/day. `[PROVE]` `[NUM]` `[X-REF 06]`
2.5.3 **POST policy uploads** — the mechanism that lets you constrain content-length range and
      content type, which `presignPutObject` cannot. `[API]` `[TRAP]`
2.5.4 **Multipart upload orchestration**: part sizing arithmetic (a 50 TB object across 10,000 parts
      requires ≥ 5 GB parts), parallelism, retry of individual parts, and `S3TransferManager`.
      `[PROVE]` `[NUM]`
2.5.5 **Byte-range fetches** as the read-side mirror, and their use for parallel download and for
      reading a header without the body.
2.5.6 **Prefix partitioning and 503 SlowDown**: 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD per
      second **per partitioned prefix**, unlimited prefixes, scaling that is gradual rather than
      instantaneous, and the `503 Slow Down` you see while it happens. The correct response is
      backoff plus prefix spreading, not a support ticket. `[NUM]` `[SOURCE]` `[TRAP]`
2.5.7 **The obsolete advice**: prefixing keys with a random hash was mandatory before July 2018 and
      is now actively harmful to prefix-based lifecycle rules and to listing. `[VERSION-TRAP]`
2.5.8 **Strong consistency, and what it does *not* cover**: bucket configuration changes
      (lifecycle, policy, replication) remain eventually consistent, and so do the results of a
      cross-region replica. `[TRAP]`
2.5.9 **Conditional writes as a concurrency primitive**: `If-None-Match: *` gives create-if-absent,
      `If-Match: <etag>` gives compare-and-swap, and the 412 vs 409 distinction (409 means retry).
      Building an S3-backed lease with them. `[PROVE]` `[RESEARCH]`
2.5.10 **S3 as an event source**: notification configuration, the SQS/SNS/Lambda/EventBridge targets,
      **at-least-once delivery**, the possibility of lost notifications without EventBridge, and the
      fact that a notification carries the key and size but not the object. The QuizStakes bank-file
      arrival path. `[X-REF 14]`
2.5.11 **Access Points and Object Lambda Access Points** — per-tenant or per-workload access surfaces
      over one bucket, and the transformation hook. Relevant to QuizStakes' per-field PII
      authorisation. `[X-REF 13]`
2.5.12 **Bucket policy patterns worth memorising**: deny non-TLS (`aws:SecureTransport`), deny
      unencrypted PUT (`s3:x-amz-server-side-encryption`), restrict to a VPC endpoint
      (`aws:SourceVpce`), restrict to an org (`aws:PrincipalOrgID`), and grant CloudFront OAC access.
      `[IAM]`
2.5.13 **Cross-account S3 and the object-ownership trap**: an object PUT by account B into account
      A's bucket used to be owned by B, making it unreadable by A. **Bucket Owner Enforced** fixed
      it; understand the failure because you will meet old buckets. `[TRAP]` `[VERSION-TRAP]`
2.5.14 **Replication in depth**: what is and is not replicated (existing objects no, deletes no by
      default, Glacier-class objects no), the replication IAM role, RTC's 15-minute SLA, bidirectional
      replication and its loop, and **replication is not a backup either**. `[TRAP]`
2.5.15 **S3 Storage Lens and Inventory** as the tools that answer "what is actually in this bucket
      and what is it costing me" without a `ListObjects` marathon. `[CLI]`
2.5.16 **Request-cost arithmetic**: PUT/COPY/POST/LIST and GET are priced per 1,000 requests, and a
      chatty small-object workload can cost more in requests than in storage. Compute it for
      QuizStakes' 2.6M `ApplicationHistory` records/day if they were stored as objects. `[PROVE]`
      `[COST]`

## §2.6 IAM in depth

2.6.1 **The full evaluation flowchart**, walked node by node: organizations SCP → RCP → resource
      policy → identity policy → permissions boundary → session policy, with the deny short-circuit
      at each. `[FLOW]` `[SOURCE]`
2.6.2 **Cross-account evaluation is different**: the request must be allowed in *both* accounts —
      an identity policy in the caller's account **and** a resource policy or role trust in the
      target's. This is the single most common cross-account debugging failure. `[PROVE]` `[TRAP]`
2.6.3 **Role trust policies** — the `Principal` element, `sts:AssumeRole` as the action, `ExternalId`
      for the **confused-deputy** problem, and `aws:PrincipalOrgID` as the modern alternative.
      `[IAM]` `[X-REF 13]`
2.6.4 **The confused deputy, worked**: a third-party SaaS with a role in your account, the attack
      when `ExternalId` is absent, and why `sts:ExternalId` is a condition and not a secret.
      `[PROVE]` `[TRAP]`
2.6.5 **Permissions boundaries** — the intersection semantics, and their real purpose: delegating
      role creation to a team without letting them create an admin role. Show the boundary policy and
      the delegating policy together. `[IAM]` `[PROVE]`
2.6.6 **SCPs in practice**: deny regions outside `eu-west-1`/`eu-west-2`, deny root actions, deny
      disabling CloudTrail/GuardDuty/Config, deny leaving the org, require IMDSv2. Show the JSON.
      `[IAM]`
2.6.7 **Condition keys worth knowing by name**: `aws:SourceIp`, `aws:SourceVpc`, `aws:SourceVpce`,
      `aws:SecureTransport`, `aws:PrincipalTag`, `aws:RequestTag`, `aws:ResourceTag`,
      `aws:PrincipalOrgID`, `aws:MultiFactorAuthPresent`, `aws:CurrentTime`,
      `aws:ViaAWSService`, `aws:CalledVia`. `[TABLE]`
2.6.8 **Condition operators and the null/if-exists subtleties**: `StringEquals` vs `StringLike`,
      `ForAllValues:` vs `ForAnyValue:`, `IfExists` suffixes, and `Null`. Getting these wrong writes
      a policy that allows everything. `[TRAP]`
2.6.9 **ABAC** — tag-based access control: `"Resource": "arn:aws:s3:::quizstakes-documents/${aws:PrincipalTag/tenant}/*"`,
      session tags, and why ABAC scales where RBAC's role count explodes. `[IAM]` `[PROVE]`
2.6.10 **Policy variables** (`${aws:username}`, `${aws:PrincipalTag/x}`) and their dependence on the
      `2012-10-17` version string.
2.6.11 **`NotAction` and `NotResource`** — powerful, almost always wrong, and a review finding.
      `[TRAP]`
2.6.12 **Wildcards and the action namespace**: `s3:Get*` includes actions that did not exist when you
      wrote it. The forward-compatibility hazard of wildcard actions. `[TRAP]`
2.6.13 **IAM Access Analyzer** — external-access findings, unused-access findings, **policy
      generation from CloudTrail**, and policy validation/custom policy checks in CI. `[CLI]`
2.6.14 **The credential report and Access Advisor** (last-accessed data) as the two artefacts that
      turn "least privilege" from an intention into a task list. `[CLI]`
2.6.15 **Service-linked roles** — what they are, why you cannot edit them, and why deleting one
      breaks the service.
2.6.16 **Resource-based policies by service**: S3 bucket policies, SQS queue policies, SNS topic
      policies, KMS key policies (**and the fact that a KMS key policy is mandatory — an empty one
      locks the key permanently**), Lambda resource policies, Secrets Manager, ECR, EventBridge bus
      policies. `[TABLE]` `[TRAP]`
2.6.17 **Cognito** — user pools (authentication, hosted UI, triggers) vs identity pools (exchanging a
      token for AWS credentials), and where each belongs relative to QuizStakes' own `JwtService`.
      `[X-REF 13]`
2.6.18 **GuardDuty, Security Hub, Inspector, Macie, Detective** — the security services, one line
      each, and which finding each produces. `[TABLE]` `[X-REF 13]`

## §2.7 VPC in depth

2.7.1 **Route table evaluation**: longest-prefix match wins, `local` for the VPC CIDR is implicit and
      cannot be removed or overridden, and the main vs custom route table default. `[PROVE]` `[TRAP]`
2.7.2 **A worked packet trace**: a request from a client to `ApplicationGateway` behind an ALB, into
      `ClientRestrictions`, into RDS — naming every route table, security group and NACL decision on
      the path, in order. `[FLOW]`
2.7.3 **The debugging decision tree for "A cannot reach B"**: route table → security group (both
      sides) → NACL (both directions) → DNS → the application's own bind address → the target's
      health check. Every step with the command that checks it. `[FLOW]` `[CLI]`
2.7.4 **VPC Flow Log field reference** and reading a `REJECT` line to identify whether an SG or a
      NACL dropped it (SG rejects show no return record; NACL rejects show the outbound attempt).
      `[DIAG]` `[PROVE]`
2.7.5 **NAT Gateway failure modes**: port exhaustion at ~55,000 connections per unique destination
      (the symptom is `ErrorPortAllocation`), single-AZ dependency, and the bandwidth ceiling.
      `[METRIC]` `[NUM]` `[TRAP]`
2.7.6 **NAT instance vs NAT Gateway** — the self-managed alternative that is cheaper at low volume
      and a single point of failure. Worth knowing exists; rarely the right answer.
2.7.7 **Interface endpoint economics**: per-endpoint per-AZ hourly charge plus per-GB, so a VPC with
      three AZs and twelve endpoints has a meaningful fixed cost. When NAT is actually cheaper.
      `[PROVE]` `[COST]`
2.7.8 **Private DNS on interface endpoints** — how `secretsmanager.eu-west-1.amazonaws.com` resolves
      to a private IP inside the VPC, why that breaks if `enableDnsHostnames` is off, and the
      split-horizon consequence. `[TRAP]`
2.7.9 **Endpoint policies** — restricting *which* buckets or *which* actions may go through an
      endpoint, as a genuine data-exfiltration control. `[IAM]` `[X-REF 13]`
2.7.10 **Transit Gateway route tables and appliance mode**, and the asymmetric-routing bug appliance
      mode exists to fix.
2.7.11 **Overlapping CIDRs** — what you actually do when an acquisition brings `10.0.0.0/16`: NAT,
      PrivateLink, or renumber. `[TRAP]`
2.7.12 **IPAM** as the answer once you have more than a handful of VPCs.
2.7.13 **Network performance**: baseline vs burst bandwidth per instance type, ENA and ENA Express,
      placement groups, and the fact that a `t3.micro` cannot saturate anything. `[NUM]`
2.7.14 **Security-group rule limits as an architectural constraint**: 60 inbound rules × 5 SGs, and
      why SG-referencing rather than CIDR listing is what keeps you under it. `[PROVE]`
2.7.15 **The `0.0.0.0/0` inbound rule** as a review finding, and the two legitimate cases (a public
      ALB, and an instance behind a WAF). `[TRAP]` `[X-REF 13]`

## §2.8 Load balancing and traffic management in depth

2.8.1 **ALB routing evaluation order**: listener → rules by priority → conditions → actions, with
      the default action last. The debugging consequence when two rules overlap. `[FLOW]`
2.8.2 **Health check tuning arithmetic**: detection time = `Interval × UnhealthyThreshold`, and the
      trade-off against flapping. Sized for `ClientRestrictions`' 30 ms budget and for a JVM that
      takes 90 s to warm. `[PROVE]` `[NUM]`
2.8.3 **The JVM warm-up problem, stated properly**: a target that passes its health check before the
      JIT has compiled its hot paths receives full traffic and times out. Slow start on the target
      group, a deeper readiness check, and warm-up requests are the three fixes. `[TRAP]`
      `[X-REF 06]` `[X-REF 19]`
2.8.4 **Connection draining / deregistration delay** sized against QuizStakes' longest request (the
      60 s banking-partner payout file) and its termination grace period. `[PROVE]`
2.8.5 **Sticky sessions** — duration-based vs application-based cookies, and the argument that they
      are a crutch that fails on deploy, on scale-in and on instance loss, and defeats even load
      distribution. The one legitimate use in this estate: `InternalPlatforms` is explicitly
      session-affine (scenario B.1). `[TRAP]` `[PROVE]`
2.8.6 **Weighted target groups** for canary and blue/green at the LB layer, and why this beats DNS
      weighting (instant, no client caching).
2.8.7 **NLB target-group flow hashing** (5-tuple for TCP, 3-tuple for UDP) and the consequence for
      long-lived connections. `[X-REF 10]`
2.8.8 **Client IP preservation**: `X-Forwarded-For` on ALB, proxy protocol v2 on NLB, and the
      `RemoteIpValve` / `ForwardedHeaderFilter` configuration a Spring Boot app needs or every log
      line records the load balancer's IP. `[API]` `[TRAP]` `[X-REF 07]`
2.8.9 **The `502` / `503` / `504` triage table for an ALB**: 502 = target closed the connection or
      returned a malformed response (usually the keep-alive race); 503 = no healthy targets; 504 =
      target did not respond within the idle timeout. `[TABLE]` `[DIAG]`
2.8.10 **CloudFront cache design**: cache key composition (which headers, cookies and query strings
      participate), and why including `Authorization` in the cache key gives you a 0% hit rate while
      excluding it gives you a security incident. `[TRAP]` `[X-REF 15]`
2.8.11 **CloudFront invalidation costs and versioned keys** — why `app.a1b2c3.js` beats invalidating
      `app.js`. `[COST]` `[X-REF 15]`
2.8.12 **Global Accelerator vs Route 53 latency routing vs CloudFront**, as a three-way table:
      anycast IPs into the backbone vs DNS resolution vs edge caching. Different problems.
      `[TABLE]`

## §2.9 RDS, Aurora and the connection problem in depth

2.9.1 **The full failover sequence for Multi-AZ instance deployment**, as an ordered trace: failure
      detection → promote standby → **flip the CNAME behind the endpoint** → new standby provisioned
      → application reconnects. 60–120 s, and where each second goes. `[FLOW]` `[NUM]`
2.9.2 **The Multi-AZ DB cluster sequence** by contrast: Raft-based, two readable standbys,
      **under 35 seconds**, and a separate reader endpoint. `[VERSION-TRAP]` `[NUM]`
2.9.3 **What the application must do to survive a failover**, enumerated: short JVM DNS TTL,
      HikariCP `maxLifetime` below any infrastructure idle timeout, a validation query or JDBC4
      `isValid`, retry of idempotent statements, and a circuit breaker so the reconnect storm does
      not become the outage. `[TABLE]` `[X-REF 08]` `[X-REF 10]`
2.9.4 **`sun.net.inetaddr.ttl` / `networkaddress.cache.ttl`**, the default of `-1` (cache forever)
      when a `SecurityManager` is installed and `30` otherwise, and how to set it correctly in a
      container. `[CFG]` `[TRAP]` `[NUM]`
2.9.5 **Reader endpoint vs writer endpoint vs custom endpoints** in Aurora, and the fact that the
      reader endpoint load-balances **per connection, not per query** — so a pool pins itself to one
      replica. `[TRAP]` `[PROVE]`
2.9.6 **Read/write splitting in Spring**: `AbstractRoutingDataSource` keyed on
      `TransactionSynchronizationManager.isCurrentTransactionReadOnly()`, and the read-after-write
      hazard it introduces. `[API]` `[X-REF 08]`
2.9.7 **Replica lag mitigation** as a menu: route must-be-fresh reads to the writer, hold a client on
      the writer for N seconds after a write, use a session/LSN token, or accept staleness
      deliberately per endpoint. Applied to QuizStakes' 80 ms `BalanceView` budget. `[TABLE]`
      `[X-REF 09]`
2.9.8 **RDS Proxy in depth**: connection borrowing, the `MaxConnectionsPercent` and
      `MaxIdleConnectionsPercent` knobs, **pinning triggers** (`SET`, temporary tables, prepared
      statements in some engines, advisory locks), the `DatabaseConnectionsBorrowLatency` metric,
      IAM authentication, and its behaviour during failover. `[CFG]` `[METRIC]` `[TRAP]`
2.9.9 **IAM database authentication** — a 15-minute token instead of a password, its connection-rate
      limits, and why it does not remove the need for a pool. `[NUM]`
2.9.10 **Backups, snapshots and PITR**: the backup window, the I/O impact on single-AZ, the retention
      ceiling of 35 days, manual snapshots surviving instance deletion, cross-region and
      cross-account snapshot copy, and **restoring creates a new instance with a new endpoint**.
      `[TRAP]`
2.9.11 **The 7-year retention requirement** QuizStakes has cannot be met by automated backups
      (35-day max) — it needs exported snapshots to S3 with a lifecycle policy, or logical archival.
      `[PROVE]` `[TRAP]`
2.9.12 **Parameter groups**: static vs dynamic parameters, the pending-reboot state, and the
      parameters worth knowing (`max_connections`, `shared_buffers`, `work_mem`,
      `log_min_duration_statement`, `rds.force_ssl`, `idle_in_transaction_session_timeout`).
      `[CFG]` `[X-REF 09]`
2.9.13 **Performance Insights** — DB load in average active sessions, top SQL, top waits, and the
      free 7-day vs paid long-term retention. The right first tool for "the database is slow."
      `[METRIC]` `[X-REF 09]`
2.9.14 **Aurora's storage model as an operational fact**: 10 GB segments, six copies, storage that
      auto-grows to 128 TiB and (since 2020) shrinks, backups that do not touch the compute node,
      and **replicas that share storage so adding one does not copy data**. `[PROVE]`
2.9.15 **Aurora failover with `failover_priority` tiers**, and the fast-failover client
      configuration (the AWS JDBC Driver for MySQL/PostgreSQL, which reads cluster topology and
      fails over in single-digit seconds without waiting for DNS). `[API]` `[RESEARCH]` `[TRAP]`
2.9.16 **Aurora Serverless v2 scaling behaviour** — ACU granularity, scale-up speed, scale-to-zero
      and its cold-start, and the min-ACU floor that determines your buffer cache. `[TRAP]`
2.9.17 **Blue/Green Deployments** — how the green environment is kept in sync, what the switchover
      actually does, the guardrails it enforces, and the operations it does not support.
      `[RESEARCH]`
2.9.18 **The QuizStakes connection budget, computed end to end**: 8 `PaymentService` + 3 `FundsLedger`
      + 8 `ClientRestrictions` + 12→40 `ApplicationGateway` pods, each with a pool, against a
      `db.r6g.2xlarge`'s `max_connections`. Show the number, show the scale-out failure, then show
      the fix. `[PROVE]` `[NUM]`

## §2.10 DynamoDB in depth

2.10.1 **Capacity arithmetic worked**: QuizStakes' idempotency-key table at 95k card deposits/day
      plus 2.8M stake reservations/day, with a ~200-byte item and a 24-hour TTL — compute WCU, RCU,
      storage and on-demand vs provisioned cost. `[PROVE]` `[COST]` `[NUM]`
2.10.2 **On-demand vs provisioned as a decision**, including the ~7× per-request price premium and
      the crossover utilisation (roughly 15–20%) at which provisioned + autoscaling wins.
      `[PROVE]` `[COST]`
2.10.3 **Autoscaling's lag**: target tracking reacts in minutes, so a 3,400/sec settlement burst
      against a provisioned table throttles before it scales. On-demand or a pre-scaled schedule is
      the answer. `[TRAP]` `[PROVE]`
2.10.4 **`ProvisionedThroughputExceededException` vs `ThrottlingException` vs
      `RequestLimitExceeded`**, and the SDK's automatic retry of the first. `[API]` `[DIAG]`
2.10.5 **Condition expressions as optimistic concurrency**:
      `attribute_not_exists(pk)` for insert-once (the idempotency guarantee),
      `#version = :expected` for CAS, and `ConditionalCheckFailedException` as the success signal
      rather than an error. `[API]` `[PROVE]`
2.10.6 **`TransactWriteItems`** — up to 100 items, all-or-nothing, 2× cost, a
      `TransactionCanceledException` carrying per-item reasons, and the idempotency `ClientRequestToken`.
      `[API]` `[NUM]`
2.10.7 **Streams + Lambda ESM**: shard-per-partition parallelism, `ParallelizationFactor`,
      `BisectBatchOnFunctionError`, `MaximumRetryAttempts`, `DestinationConfig` for the failure
      destination, and the fact that a poison record blocks its shard until it ages out.
      `[CFG]` `[TRAP]` `[X-REF 14]`
2.10.8 **GSI write amplification**: every base-table write costs WCU on every GSI whose projected
      attributes changed, so five GSIs is a 6× write bill. `[PROVE]` `[COST]` `[TRAP]`
2.10.9 **GSI throttling back-pressures the base table** in provisioned mode — the failure that makes
      no sense until you know it. `[TRAP]`
2.10.10 **Item-collection size limit**: an LSI caps a partition-key's item collection at 10 GB, and
      exceeding it fails writes. `[NUM]` `[TRAP]`
2.10.11 **Pagination**: 1 MB per `Query`/`Scan` page regardless of `Limit`, `LastEvaluatedKey`, and
      why a filter expression does **not** reduce consumed capacity. `[NUM]` `[TRAP]`
2.10.12 **Backup and PITR** — on-demand backups, 35-day PITR, export to S3 in Parquet, and
      **incremental export**. `[RESEARCH]`
2.10.13 **DynamoDB as a lock table**: `attribute_not_exists` + TTL + a fencing token, and its honest
      comparison with Redis and with a relational advisory lock for QuizStakes' `PaymentRun` leader.
      `[X-REF 14]` `[X-REF 15]`
2.10.14 **DynamoDB Local and the Testcontainers module** for tests. `[X-REF 16]`

## §2.11 Lambda in depth

2.11.1 **The full invocation trace, cold and warm**, as an ordered list: request → concurrency check →
      environment selection or creation → download code → start runtime → **static init and Spring
      context refresh** → handler → response → freeze. Where the Java time actually goes. `[FLOW]`
2.11.2 **What to put outside the handler**: SDK clients, the Spring context, connection pools,
      compiled regexes, parsed configuration. What must stay inside: anything request-scoped.
      `[TRAP]` `[API]`
2.11.3 **Spring Cloud Function and `spring-cloud-function-adapter-aws`** — the supported way to run
      a Spring application in Lambda, and the honest note about its cold-start cost even with
      SnapStart. `[API]` `[X-REF 07]`
2.11.4 **SnapStart mechanics**: `Init` runs once at version publish, a Firecracker microVM snapshot
      is taken, and each cold start **restores** the snapshot instead of re-initialising. CRaC's
      `Resource` interface with `beforeCheckpoint` and `afterRestore`. `[PROVE]` `[API]`
2.11.5 **SnapStart's three correctness hazards, each with a fix**: network connections captured open
      and now dead (close in `beforeCheckpoint`, reopen in `afterRestore`); **`SecureRandom` and any
      seeded state duplicated across every restored environment** (the SDK and JDK handle their own,
      your code may not); and time-sensitive cached values (credentials, JWKS, feature flags) frozen
      at snapshot time. `[TRAP]` `[PROVE]`
2.11.6 **SnapStart's constraints**: published versions only (not `$LATEST`), a `Init` phase capped at
      ~15 s (with a higher ceiling for SnapStart), and cost — restore itself is not billed extra.
      `[NUM]` `[RESEARCH]`
2.11.7 **Provisioned concurrency** — how it interacts with versions and aliases, the
      `ProvisionedConcurrencyUtilization` metric, application autoscaling on it, and the arithmetic
      showing when it is more expensive than simply accepting a cold start. `[PROVE]` `[COST]`
      `[METRIC]`
2.11.8 **Event source mappings in depth**: `BatchSize`, `MaximumBatchingWindowInSeconds`,
      `FunctionResponseTypes: ReportBatchItemFailures` (partial batch response), scaling behaviour
      for SQS (5 additional pollers per minute up to 1,000 concurrent), `ScalingConfig`'s
      `MaximumConcurrency`, and filter criteria. `[CFG]` `[NUM]` `[X-REF 14]`
2.11.9 **The SQS + Lambda concurrency stampede**: a backlog makes Lambda scale to the account limit,
      which exhausts RDS connections and takes down services that have nothing to do with the queue.
      Reserved concurrency or `MaximumConcurrency` is the fix. `[TRAP]` `[PROVE]`
2.11.10 **Lambda in a VPC, in depth**: Hyperplane ENI sharing per (subnet, SG) tuple, the ENI quota
      of 500 per VPC, the loss of internet access, and the argument for interface endpoints rather
      than a NAT. `[NUM]` `[TRAP]`
2.11.11 **Error handling by invocation model**, as a table: synchronous (the caller sees it),
      asynchronous (2 retries, max event age, on-failure destination, DLQ), and ESM (per-source
      retry semantics, which are not the same for SQS, Kinesis and DynamoDB Streams). `[TABLE]`
      `[X-REF 14]`
2.11.12 **Lambda cost arithmetic**: `$0.0000166667 per GB-second` plus `$0.20 per 1M requests`
      (x86, on-demand), and the crossover against Fargate computed for QuizStakes' bank-file
      ingestion (40k records once a day) versus its stake settlement (2.8M/day). `[PROVE]` `[COST]`
2.11.13 **Lambda Power Tuning** as the empirical answer to the memory/cost question, and the
      counter-intuitive result that more memory is often cheaper. `[PROVE]`
2.11.14 **Lambda observability**: the `REPORT` line's `Duration` / `Billed Duration` /
      `Memory Size` / `Max Memory Used` / **`Init Duration`** / `Restore Duration`, the
      `Throttles` / `ConcurrentExecutions` / `IteratorAge` metrics, and Lambda Insights. Read a real
      `REPORT` line field by field. `[DIAG]` `[METRIC]`
2.11.15 **Lambda Durable Functions** in depth — the durable-operation model, checkpointing, the
      3,000-operation and 100 MB ceilings, and how it compares with Step Functions for the same job.
      `[TABLE]` `[RESEARCH]`
2.11.16 **When Lambda is wrong for QuizStakes**, argued: `FundsLedger` (connection pool locality and
      pause sensitivity), `ClientRestrictions` (a 30 ms p99 budget with no cold-start tolerance), and
      `DocumentVerification` (2–6 MB payloads and 90 s work). `[PROVE]`

## §2.12 Containers in depth

2.12.1 **The ECS task lifecycle** as an ordered trace: `PROVISIONING` (ENI attach) → `PENDING`
      (image pull, secrets fetch) → `ACTIVATING` (container dependencies, health checks) →
      `RUNNING` → `DEACTIVATING` → `STOPPING` (SIGTERM, `stopTimeout`, SIGKILL) → `DEPROVISIONING` →
      `STOPPED`. Where a failed deployment gets stuck at each step. `[FLOW]` `[DIAG]`
2.12.2 **`stopTimeout` and graceful shutdown**: the default 30 s, the maximum 120 s on Fargate, and
      how it must relate to deregistration delay and to the JVM's shutdown hook. This is
      scenario B.4's drain-before-terminate, mechanically. `[NUM]` `[PROVE]` `[X-REF 19]`
2.12.3 **`STOPPED` reason strings you will actually see**: `CannotPullContainerError`,
      `ResourceInitializationError` (usually a missing NAT or endpoint for secrets),
      `OutOfMemoryError: Container killed due to memory usage`, `Essential container in task
      exited`. Read each and name its cause. `[DIAG]` `[TRAP]`
2.12.4 **Task-level vs container-level CPU and memory**, soft (`memoryReservation`) vs hard
      (`memory`) limits, and the fact that on Fargate task-level is what you pay for. `[CFG]`
2.12.5 **The JVM in a container**: `UseContainerSupport` (on by default since 10),
      `MaxRAMPercentage`, why `-Xmx` equal to the container limit gets you OOM-killed, and the
      metaspace + code cache + thread stacks + direct buffers overhead. Sized for `FundsLedger`'s
      12 GB heap. `[PROVE]` `[X-REF 06]` `[X-REF 19]`
2.12.6 **Service autoscaling for ECS**: target tracking on `ECSServiceAverageCPUUtilization`,
      `ALBRequestCountPerTarget`, or a custom metric; step scaling; scheduled scaling; and the
      cooldown asymmetry. `[CFG]` `[METRIC]`
2.12.7 **The deployment circuit breaker** and automatic rollback, and why `minimumHealthyPercent=100`
      with `maximumPercent=200` is the safe default and doubles your task count during a deploy.
      `[PROVE]` `[NUM]`
2.12.8 **ECS Service Connect** — a managed service mesh: the namespace, client-side load balancing,
      retries, and the metrics it emits without instrumentation. Compared with Cloud Map DNS
      discovery and with an ALB per service. `[TABLE]` `[RESEARCH]`
2.12.9 **`awslogs` vs `awsfirelens`** log drivers, and the throughput ceiling of `awslogs` that makes
      a chatty service drop lines. `[CFG]` `[TRAP]` `[X-REF 20]`
2.12.10 **ECS Exec** as the `kubectl exec` equivalent, its SSM dependency, and its audit trail.
      `[CLI]`
2.12.11 **Fargate platform versions**, ephemeral storage (20 GB default, up to 200 GB), and the
      absence of privileged mode, host networking, GPU (until recently) and daemon-set-style
      sidecars. `[NUM]` `[TABLE]`
2.12.12 **Fargate Spot** — the interruption model (a 2-minute SIGTERM), and the workloads that
      qualify in QuizStakes (bank-file record matching) and those that do not (`PaymentRun`).
2.12.13 **EKS in depth, bounded to the AWS-specific parts**: the managed control plane and its
      endpoint access modes, managed node groups vs Karpenter vs Fargate profiles, add-ons (VPC CNI,
      CoreDNS, kube-proxy, EBS CSI), the aws-auth ConfigMap vs **EKS access entries**, and Auto Mode.
      `[X-REF 19]` `[VERSION-TRAP]`
2.12.14 **The EKS cost floor** — $0.10/hour per cluster plus nodes — versus ECS's $0. A real input to
      the ECS-vs-EKS decision for a 12-service estate. `[COST]` `[PROVE]`
2.12.15 **Image build and supply chain**: multi-stage builds for a JVM, jlink/jdeps custom runtimes,
      distroless bases, ECR enhanced scanning, and image signing. `[X-REF 19]` `[X-REF 13]`

## §2.13 Scaling and the statelessness requirement

2.13.1 **Vertical scaling** — a bigger instance. Simple, no code change, and the right first move
      surprisingly often; many "we need to scale out" situations are one instance size or one index
      away from resolution. Limits: a hard ceiling, a restart or failover to change, and
      super-linear cost at the top end. `[TRAP]`
2.13.2 **Horizontal scaling** — more instances. Effectively unbounded, gives fault tolerance as a
      side effect, enables rolling deploys, and **requires statelessness**.
2.13.3 **What "stateless" actually requires**, as the four things that commonly break it, each with
      the bug it causes and the fix: (1) **sessions in local memory** — a client logs in on pod A,
      the LB routes them to pod B, they are logged out; fix with Spring Session over
      ElastiCache/Valkey or a stateless JWT. (2) **files on local disk** — an upload written to
      `/tmp` exists on one instance and vanishes on scale-in; fix with S3 and presigned URLs, or EFS
      if you genuinely need shared POSIX. (3) **in-process caches diverging** — each instance has a
      different view; fix with a distributed cache or deliberately accept short-TTL divergence.
      (4) **scheduled jobs on every instance** — N replicas run the job N times; fix with
      idempotency, a distributed lock, a leader, or a dedicated scheduler. `[TABLE]` `[X-REF 15]`
      `[X-REF 14]`
2.13.4 **The three that get forgotten**: in-memory rate limiters (your limit is silently N×),
      in-memory WebSocket connection registries (you need a backplane), and startup work that
      assumes it is the only instance (a migration, a seed, a cache warm). `[TRAP]` `[X-REF 10]`
2.13.5 **Sticky sessions as a crutch** — they break on deploy, on scale-in and on instance failure,
      and they defeat even load distribution. Legitimate only where the state genuinely cannot move
      (`InternalPlatforms`). `[TRAP]`
2.13.6 **Auto Scaling Groups**: launch templates, desired/min/max, health check type (EC2 vs ELB)
      and grace period, termination policies, **instance refresh**, warm pools, and lifecycle hooks.
      `[CFG]`
2.13.7 **Scaling policies**: target tracking (the default choice — pick a metric that is
      *proportional to load per instance*: CPU or `ALBRequestCountPerTarget`, never total request
      count), step scaling, simple scaling, scheduled, and predictive. `[TABLE]` `[TRAP]`
2.13.8 **Scale out fast, scale in slow** — a premature scale-in during a lull causes a second
      scale-out and churn. Asymmetric cooldowns are the mechanism. `[PROVE]`
2.13.9 **Warm-up time is a scaling parameter.** If a JVM takes 90 s to start and warm, a CPU-triggered
      scale-out arrives 90 s *after* you needed it. Provision headroom accordingly and treat startup
      time as a first-class SLO. Sized against QuizStakes' 12→40 `ApplicationGateway` scale-out on a
      55k-session event. `[PROVE]` `[NUM]` `[X-REF 06]`
2.13.10 **Do not scale the tier that is not the bottleneck.** Doubling the app tier when the database
      is saturated makes things strictly worse by adding connections and load. The QuizStakes version:
      autoscaling `ApplicationGateway` cannot fix `AA-700`'s human review queue, which Appendix A
      identifies as the binding constraint. `[TRAP]` `[PROVE]`
2.13.11 **Little's Law applied to autoscaling**: `concurrency = arrival rate × latency`, so a latency
      regression looks exactly like a traffic increase to a concurrency-based scaler — and scaling
      out amplifies the real cause. `[PROVE]` `[X-REF 22]`
2.13.12 **Queue-depth-based scaling** for `BankDeposits`' worker pool, and the oscillation it causes
      when the scaling metric and the processing rate feed back into each other. `[X-REF 14]`
2.13.13 **Scaling limits you will hit before you hit the instance limit**: RDS connections, NAT
      Gateway ports, ENIs per subnet, Lambda concurrency, and the subnet's free IP count. `[TABLE]`
      `[TRAP]`

## §2.14 Resilience, availability and disaster recovery

2.14.1 **RTO and RPO defined precisely**, and the observation that every DR strategy is a point on a
      cost/RTO curve rather than a binary. `[PROVE]`
2.14.2 **The four DR strategies** with their RTO/RPO and cost: backup and restore (hours, hours),
      pilot light (tens of minutes, minutes), warm standby (minutes, seconds), **multi-site
      active/active** (near zero, near zero). `[TABLE]`
2.14.3 **Choosing one for QuizStakes** with the regulator's and the business's numbers, not with
      "we want high availability."
2.14.4 **Availability arithmetic**: series vs parallel composition, why a chain of five 99.9%
      dependencies is 99.5%, and why adding a dependency to a critical path is an availability
      decision. `[PROVE]` `[X-REF 22]`
2.14.5 **AWS SLAs are not availability guarantees**, they are refund schedules. Read what an SLA
      credit actually is. `[TRAP]`
2.14.6 **Static stability** — the AWS term for a system that keeps working when the control plane is
      unavailable, because it does not need to *change* anything to survive. Pre-provisioned
      standby capacity rather than scale-on-failure. The October 2025 outage as the proof.
      `[PROVE]` `[INCIDENT]`
2.14.7 **Cell-based architecture and shuffle sharding** as AWS's own blast-radius techniques, with
      the combinatorial argument for why shuffle sharding isolates a noisy tenant. `[PROVE]`
      `[X-REF 22]`
2.14.8 **Graceful degradation** for QuizStakes: what the platform does when the identity vendor is
      down for hours (Appendix A says the watchlist provider's characteristic failure is exactly
      that), when the PSP is degraded, and when `ClientRestrictions` cannot be reached — and why the
      last one must **fail closed** because self-exclusion is a hard 500 ms regulatory guarantee.
      `[PROVE]` `[TRAP]`
2.14.9 **Timeouts, retries, backoff and jitter, circuit breakers and bulkheads** as the client-side
      resilience set, with the AWS-specific note that the SDK already implements the first four and
      you must not double them. `[TRAP]` `[X-REF 10]`
2.14.10 **Retry storms and the retry budget** — why a naive retry on every layer multiplies load by
      the product of the retry counts. `[PROVE]` `[X-REF 14]`
2.14.11 **Health checks that lie**: a shallow `/health` that returns 200 while the database is
      unreachable, and a deep one that turns a dependency blip into a full outage. The
      readiness/liveness split is the resolution. `[TRAP]` `[X-REF 19]` `[X-REF 20]`
2.14.12 **Chaos engineering and AWS Fault Injection Service** — AZ power interruption, API throttling,
      and network disruption experiments, plus **game days** as a Well-Architected principle.
2.14.13 **Backup strategy beyond snapshots**: AWS Backup plans, vault lock, cross-account copy (so a
      compromised account cannot delete its own backups), and the restore test that nobody runs.
      `[TRAP]`
2.14.14 **Multi-region, honestly**: what actually has to be solved (data replication and conflict
      resolution, global routing, session and idempotency-key locality, cross-region cost, deployment
      ordering, and testing) and the observation that the hardest part is the *data*, not the
      compute. `[TABLE]` `[X-REF 22]`
2.14.15 **Region evacuation as a practised procedure** — ARC routing controls, pre-created capacity,
      and a runbook that has been executed at least once.

## §2.15 Configuration and secrets in depth

2.15.1 **The four config stores compared**: environment variables, Parameter Store standard,
      Parameter Store advanced, Secrets Manager, AppConfig — on cost, size limit, versioning,
      rotation, change notification, and IAM granularity. `[TABLE]` `[NUM]`
2.15.2 **Parameter Store hierarchy design** for this estate: `/quizstakes/{env}/{service}/{key}`,
      `GetParametersByPath` with `recursive` and `withDecryption`, and why the path is the IAM
      boundary. `[IAM]` `[CLI]`
2.15.3 **Parameter Store throughput** — the default 40 TPS standard tier, the higher-throughput
      setting, and the fact that 40 pods all calling `GetParametersByPath` at startup can throttle
      a deployment. `[NUM]` `[TRAP]`
2.15.4 **Rotation, end to end**: the four-step Lambda rotation contract (`createSecret`, `setSecret`,
      `testSecret`, `finishSecret`), the `AWSCURRENT` / `AWSPENDING` / `AWSPREVIOUS` staging labels,
      and the dual-user strategy that makes rotation zero-downtime. `[FLOW]` `[RESEARCH]`
2.15.5 **What the application must do to survive rotation**: a TTL'd cache rather than a
      fetch-once-at-startup, and a re-fetch on an authentication failure. Both, not either.
      `[TRAP]` `[PROVE]`
2.15.6 **The `PaymentService` credential set** in this estate — PSP, identity vendor, watchlist
      provider, banking partner — each behind exactly one owning service, each rotated, each with a
      distinct IAM path. `[IAM]`
2.15.7 **Change propagation**: a Parameter Store change does not restart your pods. EventBridge on
      the parameter-change event, AppConfig polling, or an explicit refresh endpoint are the three
      mechanisms. `[TABLE]` `[TRAP]`
2.15.8 **AppConfig deployment strategies** — linear/exponential bake times, a CloudWatch alarm as the
      rollback trigger, and validators (JSON Schema or a Lambda) that reject a bad value before it
      ships. `[CFG]`
2.15.9 **Secrets in CI/CD**: GitHub Actions OIDC → an IAM role with a narrow trust condition on the
      repository and branch, and no long-lived keys anywhere. Show the trust policy. `[IAM]`
      `[X-REF 17]`

## §2.16 Deployment and release

2.16.1 **Rolling, blue/green, canary and feature-flagged** releases as four different things people
      call "zero downtime", with the rollback speed and blast radius of each. `[TABLE]`
2.16.2 **How each is implemented on AWS**: ECS rolling with circuit breaker; ECS/Lambda blue-green
      via CodeDeploy with linear/canary traffic shifting; ALB weighted target groups; Lambda alias
      weights; Route 53 weighted records; AppConfig for flags. `[TABLE]`
2.16.3 **Database migrations under live traffic** — expand/contract, backwards-compatible schema
      changes, and the fact that a blue/green deployment of code does not blue/green the database.
      `[X-REF 09]` `[X-REF 22]`
2.16.4 **Immutable deployments and instance refresh**, versus in-place updates.
2.16.5 **The deployment safety checklist**: automated rollback trigger, a CloudWatch alarm wired to
      the deploy, deregistration delay ≥ longest request, a drain hook, and a canary that runs long
      enough to see the p99.
2.16.6 **`PaymentRun` deployment specifically** — scenario B.4's drain-before-terminate requirement,
      and what must be true for a rolling deploy not to abandon a half-generated payout file.
      `[PROVE]`

## §2.17 Encryption and key management

2.17.1 **KMS model**: CMKs (AWS-managed, customer-managed, AWS-owned), key policies (mandatory —
      an empty one permanently locks the key), grants, aliases, automatic annual rotation, multi-region
      keys, and the **`kms:ViaService`** condition. `[IAM]` `[TRAP]`
2.17.2 **Envelope encryption** as the mechanism: KMS never encrypts your data — it encrypts a data
      key, which encrypts the data. `GenerateDataKey` returns both plaintext and ciphertext versions.
      Why this exists (KMS's 4 KB payload limit and its request rate). `[PROVE]` `[NUM]`
2.17.3 **KMS request quotas** as a real production constraint: shared quotas per region per account
      (e.g. 5,500–50,000 requests/sec depending on operation and region), and the
      `ThrottlingException` that surfaces as slow S3 reads. **S3 Bucket Keys** cut this by up to 99%.
      `[NUM]` `[TRAP]` `[RESEARCH]`
2.17.4 **Encryption at rest by service**: S3 (SSE-S3 default, SSE-KMS, SSE-C, DSSE-KMS), EBS
      (volume-level, and the account-wide default-encryption setting), RDS (must be enabled at
      creation — **you cannot encrypt an existing unencrypted instance in place**), DynamoDB (always
      on), SQS/SNS, EFS, Secrets Manager. `[TABLE]` `[TRAP]`
2.17.5 **Encryption in transit**: TLS everywhere, `aws:SecureTransport` as the policy enforcement,
      RDS `rds.force_ssl` and the certificate bundle a JVM needs, and the fact that **cross-AZ
      traffic on the AWS network is encrypted at the physical layer on Nitro instances**.
      `[X-REF 10]` `[X-REF 13]`
2.17.6 **CloudHSM** and **Payment Cryptography** named for the regulated-payments case.
2.17.7 **The QuizStakes key hierarchy**: separate CMKs per data classification (PII, card, ledger,
      documents), key policies that name the owning service's role, and the audit requirement that
      every PII read reaches an append-only sink (scenario B.4). `[IAM]` `[X-REF 13]`

## §2.18 Observability in depth

2.18.1 **What to instrument on AWS specifically**: SDK client metrics, ALB target metrics, RDS
      metrics, queue depth and age, Lambda `Init Duration` and `Throttles`, ECS task-level CPU and
      memory, and the four golden signals per service. `[TABLE]` `[X-REF 20]`
2.18.2 **Structured JSON logging to CloudWatch** and Logs Insights queries that actually work,
      including `parse`, `filter`, `stats by`, and `bin()`. Write the query that finds the p99
      latency of `ClientRestrictions` per hour. `[CLI]` `[X-REF 20]`
2.18.3 **Correlation across services** — the trace id in a log line, `X-Amzn-Trace-Id`, W3C
      `traceparent`, and propagating it through SQS message attributes and EventBridge detail.
      `[X-REF 14]` `[X-REF 20]`
2.18.4 **Micrometer → CloudWatch vs Micrometer → Prometheus** and the cardinality cost difference
      that decides it. `[COST]` `[X-REF 20]`
2.18.5 **The alert set for this estate**, with thresholds: ALB `TargetResponseTime` p99 against each
      budget, `HTTPCode_ELB_5XX_Count`, `UnHealthyHostCount`, RDS `DatabaseConnections` at 80% of
      max, `ReplicaLag`, `FreeStorageSpace`, SQS `ApproximateAgeOfOldestMessage`, Lambda `Throttles`
      and `Errors`, NAT `ErrorPortAllocation`, and a **billing anomaly alarm**. `[TABLE]` `[METRIC]`
2.18.6 **Cost of observability** as a design input: Transaction Search's 100% span retention vs
      sampled X-Ray, log Infrequent Access class, metric cardinality, and the fact that observability
      can plausibly reach 20–30% of a small estate's bill. `[COST]` `[TRAP]`
2.18.7 **The incident toolkit, ordered**: Health Dashboard → CloudWatch dashboard → Logs Insights →
      X-Ray/Transaction Search service map → Flow Logs → CloudTrail. What each answers and in what
      order to reach for them. `[FLOW]`
2.18.8 **CloudTrail forensics** — finding who deleted the bucket, who changed the security group, and
      who assumed which role, including the `userIdentity` block's `sessionContext`. Read a real
      event. `[DIAG]` `[X-REF 13]`

## §2.19 Cost engineering in depth

2.19.1 **Building the QuizStakes bill from first principles**: compute (44 steady instances across
      12 services), RDS (writer + 2 standbys + replicas), S3 (68 GB/day growing, 7-year retention),
      data transfer (cross-AZ chatter at 1,200 stake reservations/sec), NAT, load balancers,
      CloudWatch, and KMS. Produce a monthly figure and rank the line items. `[PROVE]` `[COST]`
2.19.2 **The cross-AZ arithmetic for a chatty mesh**: `ClientRestrictions` is consulted on the
      deposit, stake and withdrawal paths — at 1,200/sec with a 2 KB round trip and random AZ
      placement, two thirds of that traffic crosses an AZ boundary and is billed twice. Compute the
      annual figure and then compute what topology-aware routing saves. `[PROVE]` `[COST]`
2.19.3 **The rightsizing pass**: Compute Optimizer's recommendations, the `gp2 → gp3` migration, the
      Graviton migration, and non-prod scheduling — with the saving from each. `[TABLE]` `[COST]`
2.19.4 **The commitment pass**: coverage target, the 1-year vs 3-year decision under uncertainty, and
      why you commit to the *floor* rather than the average. `[PROVE]`
2.19.5 **Unit economics** — cost per card deposit, cost per stake, cost per active client — as the
      metric that survives growth, where total spend does not. `[PROVE]` `[X-REF 20]`
2.19.6 **The showback/chargeback question** and why tagging discipline is an engineering
      responsibility rather than a finance one.
2.19.7 **Cost anti-patterns catalogue**: per-request services at sustained volume, cross-AZ chatter,
      NAT for AWS-service traffic, high-cardinality metrics, `ListObjects` polling, DynamoDB scans,
      over-provisioned RDS, forgotten non-prod, unbounded log retention, and idle load balancers.
      `[TABLE]`

## §2.20 The managed-service trade-off

2.20.1 **Managed gives you**: operational work you do not do (patching, backups, failover, scaling,
      monitoring), a tested HA story, an SLA, faster delivery, and less on-call surface. **That last
      one is the real value** — the cost of a self-managed database is not the EC2 bill, it is the
      engineer paged at 3 a.m. for a failed failover.
2.20.2 **Managed costs you**: money (typically 2–5× raw compute), control (no custom extension, no
      kernel parameter, no arbitrary version), a slower upgrade cadence, lock-in proportional to how
      proprietary the service is, and opaque debugging.
2.20.3 **Where to draw the line, as a rule**: always managed — databases, queues, object storage,
      DNS, certificates, secrets, load balancers. Usually managed — Kafka (MSK), Redis
      (ElastiCache/MemoryDB), the Kubernetes control plane (EKS), search (OpenSearch). Self-manage
      when a specific requirement cannot be met, when the multiple is millions of dollars, when
      multi-cloud portability is a genuine requirement, or when the expertise already exists and the
      marginal ops cost is near zero. `[TABLE]`
2.20.4 **Lock-in is a spectrum, not a binary.** S3 and SQS have simple, widely-cloned APIs — porting
      is work, not a rewrite. Step Functions, DynamoDB single-table designs, Aurora DSQL and deep IAM
      integration are much stickier. `[TABLE]` `[PROVE]`
2.20.5 The discipline that makes it survivable: keep the **business logic free of vendor types** even
      where the infrastructure is not. A hexagonal port for `DocumentStore` costs nothing and buys
      the option. `[X-REF 22]`
2.20.6 **Trading lock-in for velocity is usually correct** for a product team; being *accidental*
      about it is not.

## §2.21 Multi-tenancy, quotas and noisy neighbours

2.21.1 **Service quotas as an architectural constraint**, not a support ticket: know the ones on your
      critical path, monitor them with the `AWS/Usage` namespace, and raise them **before** the
      launch. `[METRIC]` `[CLI]`
2.21.2 **The quotas that bite this estate**: Lambda concurrency, RDS `max_connections`, SES sending
      rate, KMS request rate, SQS in-flight, ENIs per VPC, subnet IPs, ALB rules per listener, and
      API Gateway account throttle. `[TABLE]` `[NUM]`
2.21.3 **Throttling as a shared-fate mechanism** — your neighbour's burst and yours contend for the
      same regional pool, and the SDK's adaptive retry mode is a cooperative response to it.
2.21.4 **Tenant isolation models** for a regulated platform: silo (account per tenant), pool (shared
      with row-level scoping), bridge. Where QuizStakes sits and why. `[TABLE]` `[X-REF 22]`

## §2.22 The Java service, wired to AWS

2.22.1 **The credential-resolution debugging procedure**, in order, with the command that proves each
      step: `aws sts get-caller-identity`, the env vars actually present in the container, the ECS
      credential endpoint response, and the SDK's `DefaultCredentialsProvider` logging. `[FLOW]`
      `[CLI]` `[DIAG]`
2.22.2 **Timeout layering** — `apiCallTimeout` vs `apiCallAttemptTimeout` vs the HTTP client's
      connect/read timeouts vs the caller's own budget — and the rule that each outer layer must
      exceed the inner one times the retry count, or your retries never happen. Worked against the
      PSP's 10 s capture timeout. `[PROVE]` `[CFG]` `[TRAP]` `[X-REF 10]`
2.22.3 **Retry configuration**: the `standard` vs `adaptive` retry mode, `numRetries`, the
      token-bucket retry quota, and why adaptive mode's client-side rate limiting is the right
      default against a throttling service. `[CFG]` `[NUM]`
2.22.4 **Connection pooling in the SDK's HTTP client** — `maxConcurrency`, `connectionMaxIdleTime`,
      `connectionTimeToLive`, and the interaction with a load balancer's idle timeout. `[CFG]`
      `[X-REF 10]`
2.22.5 **Virtual threads and the AWS SDK** — where blocking clients become cheap, where the Netty
      async client is still better, and the pinning hazards. `[X-REF 04]` `[X-REF 05]`
2.22.6 **Testing against AWS**: LocalStack via `LocalStackContainer`, the `endpointOverride`
      configuration, DynamoDB Local, `S3Mock`, and **what none of them can prove** — IAM policy
      correctness, real throttling behaviour, real consistency timing, and cross-AZ failure.
      `[TABLE]` `[TRAP]` `[X-REF 16]`
2.22.7 **Testing IAM specifically**: `iam simulate-principal-policy`, Access Analyzer policy
      validation in CI, and a `cdk-nag` / `checkov` / `tfsec` static pass. `[CLI]` `[X-REF 16]`
2.22.8 **Local development** — an `aws` profile with SSO, `AWS_PROFILE`, a `dev` account with real
      services versus LocalStack, and the honest trade-off between the two. `[TABLE]`
2.22.9 **Graceful shutdown in a Spring Boot service on ECS**, end to end: `SIGTERM` →
      `server.shutdown=graceful` → `spring.lifecycle.timeout-per-shutdown-phase` → in-flight requests
      finish → SDK clients closed → exit before `stopTimeout`. The code and the configuration.
      `[API]` `[CFG]` `[X-REF 07]`
2.22.10 **Configuration precedence in a Spring Boot service on AWS**: command line → env vars from
      the task definition → `spring.config.import` from Parameter Store/Secrets Manager → profile
      properties → defaults. Getting this order wrong is why "the secret didn't take."
      `[FLOW]` `[X-REF 07]`

---

# PART 3 — UNDER THE HOOD

## §3.1 The Nitro System — what an EC2 instance really is

3.1.1 The pre-Nitro problem: Xen's dom0 ran networking, storage and management **on the same CPUs
      you were paying for**, costing roughly 30% of the host and making performance non-deterministic.
      `[PROVE]`
3.1.2 **Nitro Cards** — dedicated hardware for VPC networking, EBS, instance storage and the
      controller — offloading the entire I/O path off the main CPUs.
3.1.3 **The Nitro Security Chip** — a hardware root of trust that gates all writes to non-volatile
      storage on the host, so a compromised instance cannot persist.
3.1.4 **The Nitro Hypervisor** — a minimal KVM-based hypervisor whose only job is CPU and memory
      allocation, with a tiny attack surface and near-bare-metal performance.
3.1.5 What this buys you as an engineer: near-native performance, **bare-metal instance types**
      (`*.metal`), hardware-terminated encryption for EBS and for VPC traffic between Nitro
      instances, and the ability for AWS to ship a new instance family without a hypervisor change.
3.1.6 **The consequence for `FundsLedger`**: pause sensitivity and I/O determinism are hypervisor
      properties, and Nitro is why a 12 GB-heap JVM on a modern instance behaves predictably.
      `[X-REF 06]`
3.1.7 **Firecracker** — the microVM technology underneath Lambda and Fargate: ~125 ms boot, ~5 MiB
      memory overhead per microVM, a minimal device model, and the jailer. Named with its numbers.
      `[NUM]` `[RESEARCH]`

## §3.2 EBS as a network storage system

3.2.1 **EBS is network storage.** Every read and write is a round trip over the Nitro card to a
      replicated storage service in the AZ. This is why latency is measured in hundreds of
      microseconds rather than tens, and why instance-store NVMe is an order of magnitude faster.
      `[PROVE]`
3.2.2 **Replication within an AZ** — synchronous mirroring across storage nodes, and why that gives
      99.8–99.9% annual durability rather than S3's eleven nines. `[PROVE]` `[NUM]`
3.2.3 **The `gp3` decoupling**: baseline 3,000 IOPS and 125 MiB/s included at any size, with IOPS and
      throughput provisioned independently — versus `gp2`'s **3 IOPS per GiB** with a burst bucket.
      Why the `gp2` burst bucket produced the classic "the database is fast for an hour then falls
      off a cliff" incident. `[PROVE]` `[METRIC]` `[TRAP]`
3.2.4 **`BurstBalance`** as the metric that predicts that cliff, and its absence on `gp3`.
      `[METRIC]`
3.2.5 **Snapshots are incremental block-level copies to S3**, chained by reference. The first
      snapshot is full, subsequent ones store only changed blocks, and deleting a middle snapshot
      frees only blocks no other snapshot references. **Fast Snapshot Restore** and the lazy-load
      penalty of a restored volume without it. `[PROVE]` `[TRAP]`
3.2.6 **Instance-level EBS bandwidth** as a separate ceiling from the volume's, and the `EBSIOBalance`
      / `EBSByteBalance` metrics on burstable-EBS instance types. `[METRIC]` `[NUM]`
3.2.7 **Multi-Attach and NVMe reservations** on `io2` — how two instances can share a volume without
      corrupting it, and why a clustered filesystem is still required. `[TRAP]`

## §3.3 S3 internals

3.3.1 **The index and the data plane are separate systems.** A key lookup goes through a distributed,
      strongly consistent metadata index; the bytes live in a separate replicated store. Almost every
      S3 behaviour follows from this split. `[PROVE]`
3.3.2 **How strong consistency was achieved in December 2020 without a performance cost** — the index
      already had the necessary ordering; AWS's own description is that it required no additional
      cost and no performance impact. Explain what changed and what did not. `[SOURCE]`
      `[VERSION-TRAP]`
3.3.3 **Prefix partitioning**: the index is range-partitioned by key, S3 splits a hot partition
      automatically, splitting takes minutes to hours, and `503 SlowDown` is what you observe while it
      happens. This is why 3,500/5,500 is per partitioned prefix and why the number of prefixes is
      unbounded. `[PROVE]` `[NUM]`
3.3.4 **Why listing is expensive**: `ListObjectsV2` is a range scan over the index, paginated at
      1,000 keys, with no count and no random access. A bucket is not a directory tree and cannot be
      made to behave like one. `[PROVE]` `[TRAP]`
3.3.5 **Eleven nines, derived.** State the redundancy assumption (≥3 AZ, erasure coding with
      independent device failure), do the arithmetic, and then state honestly which assumption is the
      load-bearing one — correlated failure, not device failure, is the real risk, which is why
      versioning and replication exist. `[PROVE]` `[NUM]`
3.3.6 **Erasure coding vs replication** as the durability mechanism, and the storage-overhead
      difference that makes eleven nines affordable.
3.3.7 **Directory buckets and S3 Express One Zone** — a different architecture: a session-token
      authentication model (`CreateSession`), a hierarchical namespace, single-AZ placement, and
      appendable objects. Why the trade-off is latency for durability scope. `[PROVE]` `[RESEARCH]`
3.3.8 **Conditional writes' implementation** — the index's compare-and-set, why 409 exists in
      addition to 412, and what "retry on 409" is actually retrying. `[PROVE]` `[RESEARCH]`
3.3.9 **The ETag algorithm** derived: single-part = MD5 of the body; multipart = MD5 of the
      concatenated binary MD5s of each part, suffixed with `-N`. Compute one by hand for a 3-part
      upload. `[PROVE]`
3.3.10 **Lifecycle transitions are asynchronous and batched** — a rule that says "30 days" acts
      shortly after day 30, not at the instant, and transitions are billed per object.
      `[TRAP]` `[COST]`

## §3.4 VPC internals

3.4.1 **The VPC is not a network, it is a mapping service.** Packets on the physical substrate are
      encapsulated; the Nitro card consults a distributed mapping service to translate a VPC IP into
      a physical host, and the encapsulated packet is forwarded. There are no VLANs and no
      broadcast domain. `[PROVE]`
3.4.2 The consequences that follow directly and surprise people: **no broadcast, no multicast**
      (without Transit Gateway multicast), promiscuous mode is useless, and you cannot sniff another
      instance's traffic even on the same host. `[PROVE]` `[TRAP]`
3.4.3 **Security groups are enforced in the Nitro card, per ENI, as a distributed stateful firewall**
      — which is why there is no central chokepoint, why the rules apply before the packet reaches
      the guest OS, and why an SG reference to another SG can be evaluated at all. `[PROVE]`
3.4.4 **Connection tracking** — the state table that makes a security group stateful, its per-ENI
      capacity, and the fact that a rule of `0.0.0.0/0` on *both* directions makes a flow
      **untracked**, which is a performance optimisation with a correctness consequence. `[TRAP]`
      `[RESEARCH]`
3.4.5 **NACLs are enforced at the subnet boundary in the network fabric**, which is why they are
      stateless — there is no per-flow state to consult.
3.4.6 **The Amazon DNS resolver at base+2** is itself a distributed service with a **per-ENI limit of
      1,024 packets per second to the Route 53 Resolver**, which is a real and frequently-hit ceiling
      for a chatty service with a short DNS TTL. `[NUM]` `[TRAP]` `[METRIC]`
3.4.7 **Gateway endpoints are a route-table entry with a prefix list** (`pl-…`), which is why they
      are free and why they only work for S3 and DynamoDB — the service's public IP ranges are
      routed to the VPC's own gateway. Interface endpoints are an ENI and DNS override instead.
      `[PROVE]`
3.4.8 **NAT Gateway internals** — a managed, horizontally scaled service in one AZ performing port
      address translation, with a per-destination port space of ~55,000 and a hard failure mode when
      it is exhausted. Why "one per AZ" is a correctness requirement and not a cost preference.
      `[PROVE]` `[NUM]`
3.4.9 **MTU and encapsulation overhead** — why 9001 works inside a VPC and 1500 does not survive
      certain paths, and how path-MTU discovery failure manifests as "small requests work, large
      ones hang." `[TRAP]` `[X-REF 10]`

## §3.5 Load balancer internals

3.5.1 **An ALB is a fleet of nodes, one or more per enabled AZ**, registered in DNS with a low TTL,
      scaling by adding nodes. This is why its IPs change, why you cannot firewall it by IP, and why
      warm-up requests to a load test are a real thing. `[PROVE]` `[TRAP]`
3.5.2 **NLB is built on AWS Hyperplane**, a distributed flow-state layer rather than a fleet of
      proxies — which is why it has a static IP per AZ, why it does not terminate the connection by
      default, and why it scales to millions of flows without a warm-up. `[PROVE]` `[RESEARCH]`
3.5.3 **Flow hashing on NLB** — the 5-tuple hash pins a flow to a target for its lifetime, so
      HTTP/2 and gRPC connections do not rebalance and a scale-out does not shed load from existing
      connections. `[PROVE]` `[X-REF 10]`
3.5.4 **Cross-zone load balancing, mechanically**: without it, DNS distributes clients across AZ
      nodes evenly and each node only sends to its own AZ's targets — so an AZ with 2 targets and one
      with 8 give each of the 2 four times the load. Prove it with the arithmetic. `[PROVE]`
3.5.5 **Connection multiplexing on ALB** — the LB maintains its own keep-alive pool to targets, which
      is why the target's `keepAliveTimeout` must exceed the LB's idle timeout or you get 502s on
      the race. Trace the race packet by packet. `[PROVE]` `[TRAP]` `[X-REF 10]`
3.5.6 **Health checking is per LB node**, so a target can be healthy from one AZ's node and unhealthy
      from another's — which is exactly the failure mode that made the October 2025 NLB behaviour
      worse. `[INCIDENT]`
3.5.7 **Slow start** as the mechanism that ramps traffic to a newly healthy target over a configured
      window, and why it is the correct fix for JVM warm-up rather than a longer health-check
      interval. `[PROVE]` `[X-REF 06]`

## §3.6 Credentials, SigV4 and STS internals

3.6.1 **SigV4 derived step by step**: canonical request (method, canonical URI, canonical query
      string, canonical headers, signed headers, hashed payload) → string to sign (algorithm,
      timestamp, credential scope, hash of the canonical request) → signing key
      (`HMAC(HMAC(HMAC(HMAC("AWS4"+secret, date), region), service), "aws4_request")`) → signature.
      Compute one by hand for a `GetObject`. `[PROVE]` `[WIRE]`
3.6.2 **Why the key is derived rather than used directly**: scope limitation. A leaked signing key
      is useful for one day, one region and one service — that is the entire point. `[PROVE]`
3.6.3 **`UNSIGNED-PAYLOAD` and streaming chunked signing** for large S3 uploads, and why a
      presigned URL uses a query-string signature (`X-Amz-Algorithm`, `X-Amz-Credential`,
      `X-Amz-Date`, `X-Amz-Expires`, `X-Amz-SignedHeaders`, `X-Amz-Signature`) rather than a header.
      `[WIRE]`
3.6.4 **Presigned URL expiry is `min(requested duration, remaining credential lifetime)`** — which
      is why a 7-day presigned URL signed with a role's session credentials silently expires in an
      hour. This is the most-missed presigned-URL fact. `[PROVE]` `[TRAP]`
3.6.5 **SigV4a** — the multi-region variant using asymmetric signing, used by S3 Multi-Region Access
      Points. `[RESEARCH]`
3.6.6 **IMDSv2's session protocol, on the wire**: `PUT /latest/api/token` with
      `X-aws-ec2-metadata-token-ttl-seconds: 21600` → a token → `GET /latest/meta-data/...` with
      `X-aws-ec2-metadata-token`. Why requiring a `PUT` defeats SSRF (most SSRF primitives can only
      issue a `GET`), and why the **hop limit of 1** defeats a containerised attacker. `[WIRE]`
      `[PROVE]`
3.6.7 **The ECS task credential endpoint** — `169.254.170.2$AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`,
      served by the agent, scoped per task, and why the same SSRF class applies to it. `[WIRE]`
      `[TRAP]`
3.6.8 **How the SDK refreshes**: the credentials carry an `Expiration`, the provider refreshes
      **asynchronously before expiry with a jittered lead time**, and a refresh failure surfaces as a
      sudden `ExpiredToken` under load. `[PROVE]` `[DIAG]`
3.6.9 **`AssumeRole` internally** — the trust-policy evaluation, the session name in CloudTrail, the
      session policy as a further restriction, and role chaining's 1-hour cap. `[PROVE]`
3.6.10 **Regional vs global STS endpoints** — why `sts.amazonaws.com` is a `us-east-1` dependency and
      why setting `AWS_STS_REGIONAL_ENDPOINTS=regional` is a resilience decision. The October 2025
      outage made this concrete. `[TRAP]` `[INCIDENT]` `[CFG]`

## §3.7 The IAM policy evaluation engine

3.7.1 **The full algorithm as pseudocode**: collect the request context → gather all applicable
      policies by type → evaluate SCP (deny wins, then must be allowed) → RCP → resource policy →
      identity policy → boundary → session policy → return `Allow` only if every required gate
      allows and no gate denies. `[PROVE]` `[SOURCE]`
3.7.2 **Why the union/intersection asymmetry exists**: identity and resource policies are two
      *grants* of the same permission (union), while boundaries, SCPs and RCPs are *caps* on it
      (intersection). Stating this makes the whole model memorable. `[PROVE]`
3.7.3 **The same-account shortcut** — a resource policy that names the account root as principal
      delegates to the identity policy, which is why an S3 bucket policy saying
      `"Principal": {"AWS": "arn:aws:iam::123456789012:root"}` does not grant everyone in that
      account everything. `[PROVE]` `[TRAP]`
3.7.4 **Cross-account is the exception that proves the rule**: both sides must allow, and neither
      union nor delegation applies. `[PROVE]`
3.7.5 **Condition evaluation** — how a missing context key behaves for each operator, why `Null` and
      `…IfExists` exist, and how `ForAllValues` on a single-valued key silently allows.
      `[PROVE]` `[TRAP]`
3.7.6 **Policy size limits** as a real design constraint: 6,144 characters for a managed policy,
      2,048 for an inline user policy, 10 managed policies per role, 20 KB for an S3 bucket policy.
      They force you toward ABAC. `[NUM]` `[PROVE]`
3.7.7 **Eventual consistency of IAM** — a new role is not immediately assumable, a policy change is
      not immediately effective, and `AccessDenied` immediately after `CreateRole` is expected, not a
      bug. Waiters and retries are the answer. `[TRAP]`

## §3.8 DNS, Route 53 and the JVM

3.8.1 **Route 53 is anycast** — the same nameserver IPs announced from many locations, which is what
      makes it fast and resilient, and why there is no "Route 53 region."
3.8.2 **Alias records are resolved inside Route 53**, not by the client, which is why they can point
      at a zone apex, cost nothing per query, and follow target health. Contrast with a CNAME's
      DNS-level indirection. `[PROVE]` `[X-REF 10]`
3.8.3 **Health checks** — the checker fleet, the 18%-of-checkers threshold, calculated and
      CloudWatch-alarm health checks, and the failover record's dependence on them. `[NUM]`
3.8.4 **The JVM DNS cache, precisely**: `networkaddress.cache.ttl` defaults to `-1` (cache forever)
      when a security manager is installed and to an implementation default (typically 30 s)
      otherwise; `networkaddress.cache.negative.ttl` defaults to 10. Setting it correctly is a
      one-line change that decides whether your app survives an RDS failover. `[NUM]` `[PROVE]`
      `[TRAP]` `[X-REF 10]`
3.8.5 **Where the JVM cache is not the only cache**: the OS resolver, the container's, the connection
      pool's held sockets, and an HTTP client's own pool. A failover has to invalidate all four.
      `[PROVE]` `[TRAP]`
3.8.6 **Why DNS failover is slow even when everything is configured correctly**: TTL + resolver
      caching + client caching + connection pool lifetime, summed. Compute the worst case.
      `[PROVE]` `[NUM]`
3.8.7 **The VPC resolver's 1,024 packets/second per ENI limit** as the reason a very short TTL is not
      free. `[NUM]` `[TRAP]`

## §3.9 Lambda internals

3.9.1 **The architecture**: a frontend that authenticates and routes, an **Assignment Service** that
      places invocations onto execution environments, a **Worker fleet** of Firecracker microVMs, and
      a Placement Service. `[RESEARCH]`
3.9.2 **The execution environment**, precisely: a Firecracker microVM with your runtime, your code,
      and a `/tmp`, frozen between invocations (the process is `SIGSTOP`-equivalent, so background
      threads do not run between invokes). This is why a fire-and-forget thread in a Lambda handler
      is a bug. `[PROVE]` `[TRAP]`
3.9.3 **Cold start decomposed**: environment creation → **code download** → runtime bootstrap →
      **static init / constructor / Spring context** → handler init → first invoke. Measure each for
      a Spring Boot 3.x function and show where the seconds go. `[PROVE]` `[NUM]`
3.9.4 **Why Java is worst**: class loading, verification, the absence of JIT-compiled code, and
      framework reflection — all in the `Init` phase, on a cold JIT. `[PROVE]` `[X-REF 06]`
3.9.5 **SnapStart mechanically**: `Init` runs at version publish, Firecracker takes a **snapshot of
      the microVM's memory and disk state**, the snapshot is encrypted and chunked, and restore is a
      lazy page-load from the snapshot with a copy-on-write overlay. This is CRaC's checkpoint/restore
      with AWS's plumbing. `[PROVE]` `[RESEARCH]`
3.9.6 **The uniqueness problem, proved**: if the snapshot is taken once and restored N times, every
      restored environment starts with byte-identical memory — including any seeded PRNG state,
      cached UUID generators, and connection identifiers. AWS patched the JDK's `SecureRandom`; your
      code and your libraries are your problem. `[PROVE]` `[TRAP]`
3.9.7 **`beforeCheckpoint` / `afterRestore`** as the CRaC hooks, `Core.getGlobalContext().register()`,
      and what belongs in each. `[API]`
3.9.8 **Scaling internals**: the burst quota of 1,000 environments per 10 seconds per function, the
      account concurrency pool, and how reserved concurrency partitions that pool. Trace what
      happens when 3,400 settlements arrive in one second. `[PROVE]` `[NUM]`
3.9.9 **Throttling behaviour differs by invocation model**: synchronous returns `429
      TooManyRequestsException` immediately; asynchronous retries internally for up to 6 hours; ESM
      backs off and retries. `[TABLE]` `[TRAP]`
3.9.10 **Hyperplane ENIs** — how Lambda's VPC attachment went from a per-environment ENI (a 10-second
      cold-start penalty) to a shared, pre-created ENI per (subnet, security-group) tuple with a
      NAT-like mapping. This is why the old "never put Lambda in a VPC" advice is dead.
      `[PROVE]` `[VERSION-TRAP]`
3.9.11 **Billing granularity**: 1 ms rounding, `Init` billed for SnapStart-restore but not for a
      standard cold start's init on some runtimes, and the `Billed Duration` vs `Duration` line in
      the `REPORT`. Read one. `[DIAG]` `[NUM]`

## §3.10 DynamoDB internals

3.10.1 **The partition is the unit of everything**: a hash of the partition key selects a partition;
      each partition is a replicated storage unit with a leader; each caps at **10 GB, 3,000 RCU and
      1,000 WCU**. `[PROVE]` `[NUM]`
3.10.2 **Replication and leadership** — three copies across AZs with a Paxos-elected leader per
      partition group; strongly consistent reads go to the leader, eventually consistent reads may go
      to any replica. This is precisely why a strongly consistent read costs 2× and cannot be served
      from the nearest AZ. `[PROVE]`
3.10.3 **Partition splitting**: by size (when the 10 GB limit is reached) and **split for heat**
      (when a partition is consistently throttled). Splits are not instantaneous and do not help a
      single hot *key*, only a hot *range*. `[PROVE]` `[TRAP]`
3.10.4 **Adaptive capacity** — bursting and instantaneous adaptive capacity absorb short-term skew
      but do not raise the per-partition ceiling. State exactly what it does and does not fix.
      `[PROVE]` `[TRAP]` `[RESEARCH]`
3.10.5 **Write sharding, derived**: to serve a 5,000 WCU hot key you need ≥5 shards
      (`pk#0`…`pk#4`), and the read side must fan out and merge. Do the arithmetic and show the read
      cost you just bought. `[PROVE]` `[NUM]`
3.10.6 **GSIs are asynchronously maintained by a background process reading the partition's write
      stream**, which is why they are eventually consistent, why they consume their own WCU, and why
      a throttled GSI backs pressure onto base-table writes. `[PROVE]`
3.10.7 **Streams are the same write log exposed** — which is why Streams ordering is per partition
      key and why a shard maps to a partition. `[PROVE]` `[X-REF 14]`
3.10.8 **`TransactWriteItems`** is implemented as a two-phase protocol across partitions, which is
      why it costs 2× and why it can be cancelled with per-item reasons. `[PROVE]`
3.10.9 **Item size and capacity rounding**: WCU rounds up to 1 KB, RCU to 4 KB, so a 1.1 KB item
      costs 2 WCU. Compute the real cost of QuizStakes' 400-byte and 180-byte records under each.
      `[PROVE]` `[NUM]`
3.10.10 **Why `Scan` costs what a full read costs even with a filter** — filtering happens after the
      read, on the server, after capacity has been consumed. `[PROVE]` `[TRAP]`

## §3.11 Aurora internals

3.11.1 **"The log is the database."** Aurora ships redo log records to the storage layer instead of
      pages; the storage nodes materialise pages from the log. This removes the write amplification
      of full-page writes, double-writes and the doublewrite buffer. `[PROVE]` `[SOURCE]`
3.11.2 **The 6/3 quorum**: six copies across three AZs, a **4-of-6 write quorum** and a
      **3-of-6 read quorum**. Prove that this tolerates the loss of an entire AZ plus one additional
      node for writes, and an entire AZ for reads. `[PROVE]` `[NUM]`
3.11.3 **10 GB protection groups**, and why repair is fast: rebuilding one 10 GB segment rather than
      a whole volume.
3.11.4 **Replicas share the storage volume**, so adding a reader copies no data and replica lag is
      typically tens of milliseconds — but it is **not zero**, because the reader must apply the log
      to its own buffer cache. `[PROVE]` `[TRAP]`
3.11.5 **Failover as a promotion, not a rebuild** — around 30 seconds, and why the cluster endpoint's
      DNS TTL (5 s) is deliberately low.
3.11.6 **Backtrack** (MySQL) as a rewind of the log rather than a restore, and its limits.
3.11.7 **Aurora's I/O billing model** and why I/O-Optimized changes the arithmetic for a
      write-heavy workload like a 19.8M-entry/day ledger. `[PROVE]` `[COST]`
3.11.8 **Aurora DSQL's architecture, one level deep** — a disaggregated design with an optimistic
      concurrency control layer and a distributed time authority, which is *why* it is Repeatable
      Read only and *why* the 3,000-row transaction limit exists rather than being an arbitrary
      quota. `[PROVE]` `[RESEARCH]`

## §3.12 CloudWatch and the metric pipeline

3.12.1 **A metric is identified by namespace + name + the exact set of dimensions.** Change one
      dimension value and it is a different metric — that is the whole cardinality story, stated
      mechanically rather than as a warning. `[PROVE]`
3.12.2 **Resolution and rollup**: 1-second data retained 3 hours, 1-minute 15 days, 5-minute 63 days,
      1-hour 15 months. A query over a long window is served from a coarser aggregate, which is why
      a p99 over 3 months is not the p99 you think. `[PROVE]` `[TRAP]` `[NUM]`
3.12.3 **Percentiles in CloudWatch are computed from a sketch, not from raw values**, and are not
      available for every metric. What that does to an SLO built on p99. `[TRAP]`
3.12.4 **`PutMetricData` batching, the 40 KB payload limit, and the API cost** versus EMF's
      log-embedded path. `[NUM]` `[COST]`
3.12.5 **Alarm evaluation**: the `M of N` datapoints rule, the evaluation range extension when data
      is missing, `TreatMissingData` semantics, and why an alarm on a low-traffic metric flaps.
      `[PROVE]` `[TRAP]`
3.12.6 **Logs ingestion pricing dominates** — $0.50/GB ingested is usually larger than storage, which
      is why sampling and log levels are cost decisions. Compute it for QuizStakes' 2.8M
      settlements/day at one log line each. `[PROVE]` `[COST]`
3.12.7 **Logs Insights charges per GB scanned**, so an unbounded time range on a large log group is
      an expensive query. `[COST]` `[TRAP]`

## §3.13 The failure catalogue

3.13.1 **`us-east-1`, 20 October 2025 — the DynamoDB DNS race.** The full mechanism from the
      first-party post-event summary: a **DNS Planner** generates plans; three redundant **DNS
      Enactors** apply them via Route 53 transactions; one Enactor stalled, a second applied a newer
      plan and ran cleanup, the stalled Enactor then overwrote with its stale plan, and cleanup
      deleted it as obsolete — leaving **`dynamodb.us-east-1.amazonaws.com` with an empty record set**
      and the automation unable to repair it. `[INCIDENT]` `[SOURCE]` `[FLOW]`
3.13.2 The cascade, in order: DynamoDB unreachable → EC2's **DropletWorkflow Manager (DWFM)** loses
      its droplet leases (it state-checks via DynamoDB) → on recovery DWFM enters **congestive
      collapse** as its queues overflow → EC2 launches fail → Lambda, ECS, EKS and Fargate all fail
      because they launch EC2 capacity → NLB health checks against newly launched instances lacking
      propagated network state alternate pass/fail → the health-check subsystem degrades → NLB's
      automatic AZ DNS failover **removes healthy capacity** → connection errors until engineers
      disabled automatic failover. 14+ hours end to end. `[FLOW]` `[INCIDENT]`
3.13.3 **The five lessons a candidate should draw**, each stated as a design rule: (1) a failover must
      not depend on a control-plane call — **static stability**; (2) `us-east-1` is a dependency even
      for workloads elsewhere, so set `AWS_STS_REGIONAL_ENDPOINTS=regional` and avoid global
      endpoints; (3) automated remediation needs a **velocity control** or it becomes the outage —
      which is exactly the NLB fix AWS shipped; (4) recovery is a different workload from steady state
      and must be load-tested (AWS's own remediation was a DWFM recovery test suite); (5) a race
      condition in a *control* system is as dangerous as one in the data path. `[PROVE]` `[TABLE]`
3.13.4 **Capital One, 2019** — SSRF against IMDSv1, stolen instance-role credentials, 100M records
      from S3. The reason IMDSv2 exists and the reason hop-limit-1 is the default.
      `[INCIDENT]` `[X-REF 13]`
3.13.5 **The S3 `us-east-1` outage of 28 February 2017** — a typo in a runbook command removed too
      much index-subsystem capacity, and the restart took hours because the subsystem had not been
      fully restarted in years. The lesson is about **restart-time as an untested property**.
      `[INCIDENT]`
3.13.6 **The Kinesis `us-east-1` outage of 25 November 2020** — a front-end fleet exceeding the OS
      thread limit after a capacity addition, cascading into Cognito and CloudWatch. The lesson is
      about **OS-level limits as a scaling ceiling**. `[INCIDENT]` `[X-REF 11]`
3.13.7 **Public S3 bucket breaches** as a class rather than an incident, and the exact
      misconfiguration each required. `[X-REF 13]`
3.13.8 **The consolidated symptom → cause → metric → fix catalogue** for this estate, at least 25
      entries: intermittent 502s (keep-alive race), 503 with no targets (health check too strict or
      warm-up too slow), `Connection refused` from RDS (`max_connections`), sudden `ExpiredToken`
      (credential refresh failure), `AccessDenied` after a policy change (IAM eventual consistency),
      Lambda `IteratorAge` growing (a poison record blocking a shard), `ErrorPortAllocation` (NAT port
      exhaustion), `503 SlowDown` from S3 (prefix partitioning), `ProvisionedThroughputExceeded`
      (hot partition), tasks stuck in `PROVISIONING` (no free subnet IPs),
      `ResourceInitializationError` (no route to Secrets Manager), `CannotPullContainerError` (no
      route to ECR or a missing execution-role permission), a 12-hour-old CloudWatch alarm that never
      fired (`TreatMissingData`), a five-figure metric bill (dimension cardinality), a scheduled job
      running N times (no leader), a client logged out at random (local sessions), an upload that
      vanishes (local disk), a stale read after write (replica lag), a JVM pinned to the old primary
      (DNS cache), a Spot task killed mid-payout (wrong workload on Spot), a presigned URL expiring
      early (role session lifetime), a snapshot restore that is slow (no FSR), a `gp2` volume that
      falls off a cliff (`BurstBalance`), a cross-account read failing (both-sides rule), and an SCP
      denying something that looks allowed. `[TABLE]` `[DIAG]`

## §3.14 The proofs and the arithmetic

3.14.1 **`[PROVE]` Eleven nines**, with the assumptions stated and the correlated-failure caveat.
3.14.2 **`[PROVE]` The 2-AZ vs 3-AZ capacity argument** — 200% vs 150% provisioning to survive one
      loss, generalised to N AZs as `N/(N-1)`.
3.14.3 **`[PROVE]` Availability composition** — series `Πaᵢ` and parallel `1−Π(1−aᵢ)`, applied to
      QuizStakes' deposit path (gateway → restrictions → payment → PSP → ledger) to show where the
      availability actually goes.
3.14.4 **`[PROVE]` Aurora's 4/6 write and 3/6 read quorum** — show that `W + R > N` holds
      (4 + 3 > 6) and that the configuration survives an AZ loss (2 nodes) plus one more.
3.14.5 **`[PROVE]` Little's Law for Lambda concurrency and for connection pools** —
      `L = λW`, applied to 1,200 stake reservations/sec at 150 ms and to 40 card deposits/sec at
      180 ms PSP capture.
3.14.6 **`[PROVE]` The utilisation/latency curve** — `W = S/(1−ρ)` — and why an RDS instance at 80%
      CPU has 5× the queueing delay of one at 50%, which is the real reason "just add load" fails
      non-linearly. `[X-REF 22]`
3.14.7 **`[PROVE]` The connection-count ceiling** — `Σ(pods × poolSize) + headroom < max_connections`
      computed for the full QuizStakes service list at both steady state and peak.
3.14.8 **`[PROVE]` DynamoDB capacity arithmetic** — item size → WCU/RCU rounding → partition count →
      per-partition ceiling → whether the design works.
3.14.9 **`[PROVE]` The S3 lifecycle saving** — 68 GB/day × 7 years under Standard vs a
      Standard → IA(30d) → Glacier IR(90d) policy, including transition request costs.
3.14.10 **`[PROVE]` The NAT-versus-endpoint arithmetic** at 68 GB/day, and the break-even data volume
      at which an interface endpoint beats NAT.
3.14.11 **`[PROVE]` Cross-AZ transfer cost for a chatty mesh** — 1,200 req/sec × 2 KB × 2/3
      cross-AZ × 2 directions × $0.01/GB, annualised.
3.14.12 **`[PROVE]` The Lambda/Fargate crossover** as an equation in requests-per-second and duration,
      solved for a 512 MB and a 2 GB function.
3.14.13 **`[PROVE]` The Savings Plan break-even** under a probability of downsizing.
3.14.14 **`[PROVE]` Failover detection time** — `HealthCheckInterval × UnhealthyThreshold` plus DNS
      TTL plus connection-pool lifetime, summed for a realistic worst case.
3.14.15 **`[PROVE]` The retry-amplification factor** — `Π(1 + rᵢ)` across N layers, showing how three
      layers of "just three retries" multiplies load by 64. `[X-REF 14]`
3.14.16 **`[PROVE]` Why `t3` credits run out** — an accrual/consumption differential equation with
      real numbers.
3.14.17 **`[PROVE]` Memory arithmetic for a container**: heap + metaspace + code cache + thread stacks
      (`threads × Xss`) + direct buffers + native + the JVM's own overhead, summed for
      `FundsLedger`'s 12 GB heap to justify a 16 GB task. `[X-REF 06]`

## §3.15 Version history — what changed and when

3.15.1 A dated table of every version-dependent claim in this file: S3 strong consistency (Dec 2020),
      S3 prefix auto-partitioning (Jul 2018), Block Public Access on by default (Apr 2023), ACLs
      disabled by default (Apr 2023), SSE-S3 automatic (Jan 2023), conditional writes (Aug 2024),
      conditional copy (2025), 50 TB objects (Dec 2025); `gp3` launch (Dec 2020) and its 80,000 IOPS
      uplift; IMDSv2 default for new instance types (mid-2024) and account-level default (Mar 2024);
      public IPv4 charging (Feb 2024); Lambda SnapStart (Nov 2022), arm64 and Python/.NET SnapStart
      (2024), Durable Functions / MicroVMs / Managed Instances (Dec 2025); Lambda VPC Hyperplane ENIs
      (Sep 2019); API Gateway 300 s timeout (Jun 2024); RDS Multi-AZ DB cluster (2021) and Blue/Green
      (2022); Aurora Serverless v2 scale-to-zero (2024); Aurora DSQL GA (May 2025) and multi-Region
      expansion (2026); EKS Pod Identity (Nov 2023) and Auto Mode (Dec 2024); ECS Managed Instances
      and Express Mode (Nov 2025); AWS SDK for Java v1 end of support (31 Dec 2025); Spring Cloud AWS
      3.0 (May 2023) → 3.4 (2025) → 4.0 (Boot 4); X-Ray SDK maintenance mode (2026); RCPs and
      declarative policies (2024–2025); Graviton4 (2024) and Graviton5 (2026). `[TABLE]`
      `[VERSION-TRAP]` `[RESEARCH]`
3.15.2 **The meta-lesson**: AWS documentation is the only reliable source for a number, and an answer
      that quotes a constant should say which release it is from. Interviewers notice this.
3.15.3 **How to keep current** — the What's New feed, the AWS Blog, `aws-news`, the service release
      notes, and the SDK changelog. `[RESEARCH]`

---

# PART 4 — BUILD IT

Every item here ships **complete, compiling Java 21** (or a complete IAM/Terraform/CloudFormation/CLI
artifact where that is the artifact) and is followed by a **Diff vs the real one** table covering
what the production implementation does that this does not, why it bothers, and what breaks first at
scale.

4.1 **`SigV4Signer`** — compute a Signature Version 4 header from scratch for a `GetObject`:
    canonical request, string to sign, the four-stage derived key, and the `Authorization` header.
    Verify it against a real S3 request. `[BUILD]` `[PROVE]`
4.1.1 Diff vs `software.amazon.awssdk.auth.signer.AwsV4Signer` / the new `HttpSigner` SPI: chunked
    and unsigned payloads, SigV4a, header normalisation edge cases, clock-skew correction from the
    server's response, and credential-scope caching. `[TABLE]`

4.2 **`ImdsCredentialsProvider`** — an `AwsCredentialsProvider` that performs the IMDSv2 token `PUT`,
    fetches the role name, fetches the credentials, parses the `Expiration`, and refreshes
    asynchronously with jitter ahead of expiry. Includes the hop-limit and connect-timeout handling
    that makes it fail fast off-instance. `[BUILD]` `[WIRE]`
4.2.1 Diff vs `InstanceProfileCredentialsProvider`: the full provider chain, stale-credential
    tolerance during a refresh failure, endpoint-mode (IPv4/IPv6) configuration,
    `AWS_EC2_METADATA_DISABLED`, and the shared async refresh executor. `[TABLE]`

4.3 **`PresignedUploadService`** — a Spring Boot 3.x/4.x service that authorises a QuizStakes client,
    derives the key `applications/{applicationId}/documents/{documentId}`, issues a 15-minute
    presigned `PUT` with a content-type constraint, and a matching POST-policy variant that enforces
    a 2–6 MB content-length range. Includes the `S3Presigner` bean and the expiry-truncation guard.
    `[BUILD]` `[API]`
4.3.1 Diff vs a production upload path: virus scanning, checksum verification (`x-amz-checksum-sha256`),
    the S3 event → verification pipeline, tenant-scoped access points, and abuse rate limiting.
    `[TABLE]`

4.4 **`S3ConditionalStore`** — a generic compare-and-swap store over S3 using `If-None-Match: *` for
    create-once and `If-Match: <etag>` for update, with `PreconditionFailedException` and 409 handling,
    a retry policy, and a `compareAndSet(key, expectedEtag, bytes)` API. Then a lease built on it.
    `[BUILD]` `[PROVE]` `[RESEARCH]`
4.4.1 Diff vs DynamoDB conditional writes and vs a Redis `SET NX PX` lock: latency, cost per
    operation, TTL support, fencing tokens, and what each does under a partition. `[TABLE]`

4.5 **`IdempotentPaymentRecorder`** — a DynamoDB Enhanced Client implementation of QuizStakes'
    idempotency-key table: a Java `record` with `@DynamoDbImmutable`, `attribute_not_exists(pk)` as
    the insert-once condition, a TTL attribute sized to the redelivery window, and the
    `ConditionalCheckFailedException` short-circuit that returns the stored response. Full table
    definition included. `[BUILD]` `[API]` `[X-REF 14]`
4.5.1 Diff vs the scenario's stated design (a cache fast path backed by a unique DB constraint):
    why the cache alone fails open under eviction, what the constraint buys, and where DynamoDB sits
    between them. `[TABLE]`

4.6 **`FencedSchedulerLock`** — a DynamoDB-backed leader lease for the `PaymentRun` trigger:
    conditional acquire on `expiresAt < now`, a monotonically increasing **fencing token**, a
    watchdog renewing the lease, compare-and-delete release, and a `FencedPaymentRun` that rejects a
    write bearing a stale token. Plus a test that *forces* the stale-holder scenario. `[BUILD]`
    `[PROVE]` `[X-REF 14]`
4.6.1 Diff vs ShedLock, Redisson and a Postgres advisory lock: storage backend, `lockAtMostFor` /
    `lockAtLeastFor`, `@SchedulerLock` integration, watchdog defaults, and the honest note that
    none of them provides fencing tokens. `[TABLE]`

4.7 **`ResilientAwsClientConfig`** — a `@Configuration` producing correctly-configured singleton
    `S3Client`, `S3AsyncClient` (CRT), `DynamoDbEnhancedClient`, `SqsAsyncClient` and
    `SecretsManagerClient` beans with `apiCallTimeout`, `apiCallAttemptTimeout`, adaptive retry mode,
    an `ExecutionInterceptor` that propagates the trace id, a Micrometer metric publisher, and a
    `LocalStack` endpoint override behind a profile. `[BUILD]` `[CFG]`
4.7.1 Diff vs Spring Cloud AWS auto-configuration: what the starter gives you for free, what it
    hides, and which properties override which builder call. `[TABLE]`

4.8 **`RotationAwareSecretSupplier`** — a `Supplier<DbCredentials>` with a TTL cache over Secrets
    Manager, an on-auth-failure invalidate-and-refetch path, a single-flight guard so 40 pods do not
    stampede the API, and metrics for cache age and refetch count. `[BUILD]` `[PROVE]`
4.8.1 Diff vs the AWS Parameters and Secrets Lambda Extension and vs Spring Cloud AWS's
    `spring.config.import`: process-local caching, refresh semantics, and why neither handles the
    rotation failure path for you. `[TABLE]`

4.9 **`GracefulShutdownConfig`** — the complete ECS-safe shutdown for a Spring Boot service:
    `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase`, a `SmartLifecycle`
    that deregisters from the load balancer first, SDK client closure, and an executor drain — with
    the `stopTimeout`, deregistration delay and JVM shutdown-hook timings shown to be consistent.
    This is scenario B.4's drain-before-terminate, implemented. `[BUILD]` `[PROVE]` `[X-REF 19]`
4.9.1 Diff vs Kubernetes `preStop` + `terminationGracePeriodSeconds`: who signals first, the
    endpoint-removal race, and why both platforms need a sleep before SIGTERM handling.
    `[TABLE]`

4.10 **`SpotInterruptionHandler`** — a component that polls IMDS for
    `/latest/meta-data/spot/instance-action` (and consumes the EventBridge rebalance recommendation),
    flips a readiness flag, drains in-flight work, checkpoints, and exits inside the two-minute
    window. Wired to the `BankDeposits` record-matching worker. `[BUILD]` `[FLOW]`
4.10.1 Diff vs the ECS/EKS managed drain (`ECS_ENABLE_SPOT_INSTANCE_DRAINING`, the Node Termination
    Handler): who observes the notice, how the scheduler is told, and what happens to a task that
    ignores it. `[TABLE]`

4.11 **`S3LifecyclePolicy` + `bucket-policy.json`** — the complete infrastructure artifact for the
    QuizStakes document bucket: versioning, Block Public Access, default SSE-KMS with a Bucket Key,
    the lifecycle rules (IA at 30 d, Glacier IR at 90 d, expire noncurrent at 30 d, abort incomplete
    multipart at 7 d), Object Lock on the bank-file prefix, and a bucket policy denying non-TLS,
    denying unencrypted PUT, and restricting to the VPC endpoint. Expressed in both Terraform and
    CloudFormation. `[BUILD]` `[IAM]` `[CFG]`
4.11.1 Diff vs a hand-clicked bucket: what drift detection catches, what it does not, and the three
    settings a console user reliably forgets. `[TABLE]`

4.12 **`LeastPrivilegePolicySet`** — the actual IAM artifacts for one QuizStakes service
    (`DocumentVerification`): the task role policy scoped to one bucket prefix and one KMS key, the
    execution role policy scoped to ECR and to two secret ARNs, the trust policies for both, and an
    SCP guardrail. Each statement annotated with why it is scoped that way. `[BUILD]` `[IAM]`
4.12.1 Diff vs `AmazonS3FullAccess`: blast radius, what an Access Analyzer finding would say, and
    the exact CloudTrail evidence you would use to tighten it further. `[TABLE]`

4.13 **`ThreeTierVpc`** — a complete Terraform module for the standard layout: a `/16`, three AZs,
    public/private-app/private-data subnets with a documented CIDR plan, one NAT Gateway per AZ, an
    S3 and a DynamoDB gateway endpoint, interface endpoints for Secrets Manager, ECR and CloudWatch
    Logs, security groups referencing each other, and flow logs. `[BUILD]` `[CFG]`
4.13.1 Diff vs the AWS VPC module and vs `Vpc` in the CDK: IPv6, subnet sizing heuristics,
    endpoint-policy defaults, and per-AZ NAT versus single NAT as a cost switch. `[TABLE]`

4.14 **`CloudWatchAlarmSet`** — the alarm definitions for this estate as code, each with the metric,
    the statistic, the threshold justified by a budget from Appendix A, `DatapointsToAlarm`,
    `TreatMissingData`, and the SNS action. Includes a composite alarm that suppresses the
    downstream noise when the upstream alarm is firing. `[BUILD]` `[METRIC]`
4.14.1 Diff vs Prometheus alerting rules: `for:` duration vs M-of-N, label-based routing vs SNS
    topics, and where CloudWatch's cardinality limits force a different design. `[TABLE]`
    `[X-REF 20]`

4.15 **`LocalStackIntegrationTest`** — a Testcontainers test class proving three properties end to
    end: (1) a presigned PUT actually stores the object and the S3 event fires; (2) the idempotent
    recorder writes once for two identical requests; (3) the fenced lock admits exactly one leader
    across two concurrent threads. Uses `LocalStackContainer`, `@DynamicPropertySource` and
    awaitility. `[BUILD]` `[X-REF 16]`
4.15.1 Diff vs testing against a real `dev` account: IAM fidelity, throttling behaviour, consistency
    timing, service-feature coverage, and cost. State plainly what LocalStack cannot prove.
    `[TABLE]`

4.16 **`CostEstimator`** — a small Java program that takes the Appendix A volumes and emits a monthly
    cost breakdown for compute, RDS, S3 (by storage class after lifecycle), data transfer (with the
    cross-AZ fraction as a parameter), NAT, load balancers and CloudWatch, then prints the top five
    line items and the saving from each of four interventions. `[BUILD]` `[COST]` `[PROVE]`
4.16.1 Diff vs the AWS Pricing Calculator and the Cost and Usage Report: regional price variation,
    the Pricing API, commitment modelling, and why a model that disagrees with the bill is more
    useful than no model. `[TABLE]`

4.17 **`SqsWorker`** — a Spring Cloud AWS `@SqsListener` worker for the bank-deposit record queue
    with batch listening, `ReportBatchItemFailures` partial-batch responses, visibility extension for
    long work, an exception taxonomy driving retry vs DLQ, and trace-id propagation from the message
    attributes. `[BUILD]` `[API]` `[X-REF 14]`
4.17.1 Diff vs the Lambda SQS event source mapping: who owns the poller, scaling behaviour, the
    partial-batch-failure contract, and the concurrency-stampede risk. `[TABLE]`

4.18 **`SnapStartAwareFunction`** — a Lambda handler with CRaC `Resource` hooks that close and reopen
    the JDBC/HTTP connections around the checkpoint, reseed anything that must be unique per
    environment, and refresh cached credentials on restore. With a test that asserts two restored
    environments produce different identifiers. `[BUILD]` `[PROVE]` `[TRAP]`
4.18.1 Diff vs a naive Spring Cloud Function Lambda: what the framework snapshots for you, what it
    does not, and the measured cold-start difference. `[TABLE]`

4.19 **`RdsFailoverResilientDataSource`** — the complete configuration proving survival of a
    failover: JVM DNS TTL, HikariCP `maxLifetime` / `keepaliveTime` / `validationTimeout`, the AWS
    JDBC Driver's failover plugin, a retry template scoped to idempotent statements, and a
    `@Transactional(readOnly = true)` routing DataSource for the reader endpoint. `[BUILD]`
    `[CFG]` `[X-REF 08]`
4.19.1 Diff vs the plain PostgreSQL JDBC driver: topology awareness, failover detection speed,
    reader load balancing, and what the plain driver does when the endpoint's CNAME flips.
    `[TABLE]`

4.20 **`EcsTaskDefinition`** — the complete task definition for `FundsLedger` as JSON/Terraform:
    16 GB task memory justified against a 12 GB heap, `MaxRAMPercentage`, secrets injected by ARN,
    `awslogs` configuration with a retention policy, a health check, `stopTimeout: 120`, the task
    and execution roles, and `awsvpc` networking with a referencing security group. Every field
    annotated. `[BUILD]` `[CFG]` `[PROVE]`
4.20.1 Diff vs a Kubernetes Deployment + ServiceAccount + Secret + PDB: the field-by-field mapping
    and the three things ECS does that Kubernetes does not (and vice versa). `[TABLE]` `[X-REF 19]`

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "What is an Availability Zone, and why do you need three?" — the failure-domain definition, the
      synchronous-replication justification, and the `N/(N-1)` capacity arithmetic.
5.1.2 "Design a highly available web application on AWS." — the three-tier multi-AZ answer, and the
      discipline of naming the failure each component removes rather than listing services.
5.1.3 "Why should an application never have IAM access keys?" — the temporary-credential mechanism,
      end to end, and the four plumbings.
5.1.4 "Walk me through IAM policy evaluation." — deny wins, union for grants, intersection for caps,
      and the cross-account exception.
5.1.5 "A pod cannot reach S3. Debug it." — the ordered decision tree: credentials → IAM → route
      table → endpoint/NAT → DNS → bucket policy → Block Public Access. `[FLOW]`
5.1.6 "Security group versus NACL." — stateful/stateless, allow-only/allow-and-deny, ENI/subnet, and
      the ephemeral-port symptom.
5.1.7 "Why is S3 not a filesystem?" — the seven-row table and the three bugs it causes.
5.1.8 "How do you upload a 5 GB file from a browser?" — presigned URL or POST policy, multipart,
      and why not through your service.
5.1.9 "Multi-AZ versus read replica." — different problems, the full table, and "usually both."
5.1.10 "Your database is at 100% connections after a scale-out. What happened and what do you do?" —
      the arithmetic, RDS Proxy, and the pool-sizing rule.
5.1.11 "Why are Java Lambda cold starts slow, and what do you do about it?" — the `Init` phase
      decomposition and the four ranked mitigations with SnapStart first.
5.1.12 "What does SnapStart break?" — connections, uniqueness, and cached time-sensitive state.
5.1.13 "Lambda or a container for this workload?" — the six-question procedure and the crossover
      arithmetic.
5.1.14 "How do you scale a stateless service, and what makes it stateless?" — the four breakages and
      the three forgotten ones.
5.1.15 "Your bill doubled. Find out why." — Cost Explorer by service then by usage type, the top-five
      suspects, and the tagging prerequisite. `[FLOW]`
5.1.16 "Where does data transfer cost money?" — ingress free, 100 GB egress free, cross-AZ both ways,
      NAT per GB, and the gateway endpoint that eliminates the last one.
5.1.17 "What is the most expensive line item people don't expect?" — NAT data processing and cross-AZ
      chatter, with the arithmetic.
5.1.18 "How do you store secrets?" — Parameter Store vs Secrets Manager, injection by ARN, and the
      cached-forever rotation bug.
5.1.19 "How do you do zero-downtime deploys?" — the four release strategies, drain-before-terminate,
      and the database-migration caveat.
5.1.20 "What is static stability and why does it matter?" — the control-plane-dependency argument
      and the October 2025 outage as evidence.
5.1.21 "Design for RTO of 15 minutes and RPO of 1 minute." — the four DR strategies and which one
      those numbers select.
5.1.22 "When would you use DynamoDB over Postgres, and when would that be a mistake?" — access
      patterns, invariants, and the hot-partition ceiling.
5.1.23 "Explain a hot partition." — 3,000 RCU / 1,000 WCU, adaptive capacity's limits, and write
      sharding with its read cost.
5.1.24 "What is the difference between an ALB and an NLB, and when does the difference bite?" — L7
      vs L4, static IPs, and the gRPC connection-pinning consequence.
5.1.25 "Why did we get intermittent 502s from the ALB?" — the keep-alive race, traced.
5.1.26 "How does an EC2 instance get credentials?" — IMDSv2, the trace, and why IMDSv1 plus SSRF is
      the Capital One breach.
5.1.27 "What is in the shared responsibility model for RDS specifically?" — the line, per service.
5.1.28 "You inherited an AWS account. What are the first ten things you check?" — root MFA,
      CloudTrail, Block Public Access, unattached volumes and EIPs, log retention, S3 gateway
      endpoints, security groups open to `0.0.0.0/0`, Savings Plan coverage, IMDSv2, and untagged
      spend. `[TABLE]`
5.1.29 "How do you test AWS integrations?" — LocalStack, Testcontainers, a `dev` account, and the
      explicit list of what none of them proves.
5.1.30 "How do you keep a Spring Boot service's config out of the image?" — twelve-factor, Parameter
      Store, injection by ARN, and the precedence chain.
5.1.31 "CloudFormation, CDK or Terraform?" — the honest table and a recommendation with a reason.
5.1.32 "What is the Well-Architected Framework?" — the six pillars, named, and one design principle
      each.
5.1.33 "Tell me about an AWS outage and what you would have done differently." — the October 2025
      DynamoDB DNS race, the DWFM cascade, and the five design rules that follow.
5.1.34 "How would you run QuizStakes on AWS?" — the full estate mapped, with the three decisions you
      would defend and the two you would flag as contested.
5.1.35 "Multi-region: yes or no, and why?" — the RTO/RPO/residency test, the data problem, and the
      cost.

## §5.2 The consolidated trap list

5.2.1 Fifty-plus one-line traps, each in "the wrong belief → the symptom → the fix" form, gathered
      from every `[TRAP]` above, including at minimum: AZ names are not stable across accounts;
      `us-east-1` is a dependency you did not choose; a subnet is in exactly one AZ; AWS reserves 5
      IPs per subnet; a public subnet is a route-table property; NACLs need an ephemeral-port rule;
      SGs cannot deny; S3 has no directories and no rename; S3 is strongly consistent now; durability
      is not backup; an ETag is not always an MD5; incomplete multipart uploads bill forever;
      Block Public Access is on by default; a presigned URL expires with its signing credential;
      IA costs more for small objects; `gp2` has a burst bucket and `gp3` does not; instance store is
      lost on stop; an EBS volume cannot cross an AZ; `t` instances throttle; Elastic IPs and now all
      public IPv4 are billed; NAT is per-AZ for correctness; gateway endpoints are free and interface
      endpoints are not; cross-AZ transfer is billed in both directions; the first 100 GB egress is
      free; a group is not a principal; explicit deny always wins; cross-account needs both sides;
      SCPs cannot grant; a KMS key policy is mandatory; IAM is eventually consistent; role chaining
      caps at one hour; Lambda globals persist between invocations; a Lambda background thread is
      frozen; Lambda in a VPC has no internet without NAT or an endpoint; SnapStart duplicates
      randomness; async Lambda retries twice; reserved concurrency is a ceiling as well as a floor;
      RDS failover is DNS-based and the JVM caches DNS; a read replica is not a standby; you cannot
      shrink RDS storage; automated backups cap at 35 days; RDS Proxy pinning defeats multiplexing;
      Aurora's reader endpoint balances per connection; DynamoDB `Scan` costs full capacity even with
      a filter; a GSI can throttle the base table; DynamoDB Global Tables resolve conflicts
      last-writer-wins; ALB IPs change; cross-zone is off by default on NLB; deregistration delay must
      exceed your longest request; a health check that passes before JIT warm-up sheds errors; sticky
      sessions break on deploy; CloudWatch dimension cardinality is billed; log groups can retain
      forever; `TreatMissingData` decides whether your alarm ever fires; `cdk diff` is not drift
      detection; and a control-plane call in your failover path is the failure. `[TABLE]` `[TRAP]`

## §5.3 The cheat sheet

5.3.1 **The constants table** — every number in this file on one page: eleven nines, 3,500/5,500 per
      prefix, 5 MiB/10,000 parts/50 TB, 128 KB IA minimum, 30/90/180-day minimum durations, 400 KB
      DynamoDB item, 3,000 RCU / 1,000 WCU / 10 GB per partition, 1 KB WCU and 4 KB RCU rounding,
      900 s / 10,240 MB / 1,769 MB-per-vCPU / 6 MB / 512 MB–10 GB `/tmp` / 1,000 concurrency /
      1,000-per-10 s burst for Lambda, 29 s and 300 s and 30 s API Gateway timeouts, 60 rules per SG,
      5 reserved IPs per subnet, 55,000 NAT ports, 1,024 DNS packets/sec per ENI, 80,000 IOPS gp3 and
      256,000 io2, 6-of-3 Aurora quorum with 4/6 writes, 35 s Multi-AZ cluster failover, 3,000
      DSQL rows per transaction, $0.09/GB egress after 100 GB free, $0.01/GB cross-AZ each way,
      $0.045/GB NAT, $0.30 per custom metric. `[TABLE]` `[NUM]`
5.3.2 **The master cost table** — every priced dimension in this guide in one place, with the
      QuizStakes annual figure beside each. `[TABLE]` `[COST]`
5.3.3 **The master decision table** — compute, storage, database, messaging, config store, IaC tool,
      DR strategy: the question that selects each and the default when the question has no answer
      yet. `[TABLE]`
5.3.4 **The service-to-problem index** — for each of ~60 named services, the one problem it solves,
      in one line. The reverse lookup an interview actually needs. `[TABLE]`
5.3.5 **The debugging decision trees**, collected: "A cannot reach B", "the service is slow", "the
      deploy is stuck", "the bill went up", "I get AccessDenied". `[FLOW]`
5.3.6 **The QuizStakes reference architecture diagram in words** — every service placed in a subnet
      tier, every data store named, every trust boundary marked, and the four architectural rules
      annotated where they constrain it.

## §5.4 The verbal answers

5.4.1 The 60-second answer to "explain AWS's global infrastructure."
5.4.2 The 60-second answer to "explain IAM roles versus users."
5.4.3 The 90-second answer to "how would you make this application highly available and
      cost-efficient?" — a reusable structure: requirement → failure domain → tier-by-tier → cost
      levers → what you would measure.
5.4.4 The 30-second answer to each of the ten most common single-fact questions.
5.4.5 **The seniority ladder for one question** ("how do you handle secrets?") — the junior answer
      (environment variables), the mid answer (Secrets Manager), and the senior answer (rotation,
      the caching bug, the IAM path as the boundary, the CI/CD OIDC story, and the blast-radius
      argument for per-service keys). Repeat the exercise for three more questions. `[TABLE]`
5.4.6 **What a Staff-level answer adds** in every case: the failure mode, the cost, the
      organisational consequence, and the explicit statement of what you would *not* do.

## §5.5 Retention

5.5.1 The **spaced-repetition set**: the 40 facts most likely to be asked and most likely to be
      forgotten, phrased as questions.
5.5.2 The **self-quiz procedure** — read only the atomic concept checklist; if you cannot state the
      mechanism in one sentence, return to that section.
5.5.3 The **hands-on exercises** that make each part stick: create a VPC by hand once, break a NACL
      deliberately and read the symptom, exhaust a NAT's ports in a load test, watch a `t3` throttle,
      trigger a `503 SlowDown`, force an RDS failover and observe the JVM, and deploy the same
      service on Lambda and Fargate and compare the bill. `[TABLE]`
5.5.4 The **checklist of things to verify before an interview**: which region, which SDK version,
      which Spring Boot version, and which of the seventeen version deltas you can state correctly.

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| AWS post-event summary — DynamoDB service disruption, us-east-1, 19–20 Oct 2025 | https://aws.amazon.com/message/101925/ | The DNS Planner / DNS Enactor race condition, the empty record set for `dynamodb.us-east-1.amazonaws.com`, the full timeline, EC2 DropletWorkflow Manager lease expiry and congestive collapse, the NLB health-check degradation and automatic-AZ-failover behaviour, and the four remediation actions including NLB velocity control |
| AWS Lambda quotas | https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html | Every Lambda number in §1.14: 128–10,240 MB, 1,769 MB per vCPU, 900 s, 4 KB env vars, 5 layers, **1,000 environments per 10 seconds per function**, 6 MB sync / 200 MB streamed / 1 MB async payloads, 625 Mbps, 50/250 MB and 10 GB packages, 512 MB–10,240 MB `/tmp`, 1,024 fds and threads, 300 GB code storage, 500 ENIs per VPC — plus **Durable Functions** (5M/10M executions, 3,000 operations, 100 MB state) and **MicroVMs** (8 h, per-vCPU connection and RPS ceilings) and **Managed Instances** (Bottlerocket, 4,096 fds) |
| IAM policy evaluation logic | https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html | The three-step request flow, the union of identity- and resource-based policies, the intersection with permissions boundaries, and the intersection with SCPs **and RCPs** — the exact wording for §1.6.9 and §3.7 |
| Amazon S3 storage classes | https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html | The complete storage-class comparison table: durability, availability, AZ counts, minimum storage durations (30/90/180 days), 128 KB minimum billable sizes, Intelligent-Tiering's 30/90/180-day tier transitions and its 128 KB monitoring floor, Express One Zone's 99.95%, and the 40 KB Glacier metadata overhead |
| S3 performance best practices | https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html | 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD **per partitioned prefix**, unlimited prefixes, gradual (not instantaneous) scaling, `503 Slow Down` during scaling, 100 Gb/s single-instance transfer, 100–200 ms small-object latency, Transfer Acceleration, and the KMS request-rate interaction |
| Amazon EBS volume types | https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html | The full volume-type table: `gp3` **80,000 IOPS / 2,000 MiB/s / 64 TiB**, `gp2` 16,000 / 250 MiB/s / 16 TiB, `io2 Block Express` **256,000 / 4,000 MiB/s / 99.999% durability / sub-500 µs**, `io1` 64,000 / 1,000 MiB/s, `st1` and `sc1`, Multi-Attach and NVMe reservation support, and the 99.8–99.9% durability figure for everything except `io2` |
| AWS Well-Architected Framework — the pillars | https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html | Confirmation of **six** pillars including Sustainability, and their canonical ordering |
| Spring Cloud AWS project README and compatibility matrix | https://github.com/awspring/spring-cloud-aws | The version matrix (3.4.x → Boot 3.4/3.5 + Framework 6.2 + Spring Cloud 2024.0/2025.0; **4.0.x → Boot 4.0 + Framework 7.0 + Spring Cloud 2025.1**), the supported integrations per line, DynamoDB from 3.x, Spring Integration for AWS and the Kinesis binder in 4.x, and the removal of RDS/EC2/ElastiCache/CloudFormation support in 3.x |
| Spring Cloud AWS 3.x reference documentation | https://docs.awspring.io/spring-cloud-aws/docs/3.0.0/reference/html/index.html | Starter artifact ids, `S3Template`, `DynamoDbTemplate`, `@SqsListener`, and the Parameter Store / Secrets Manager `spring.config.import` model |
| AWS SDK for Java 2.x — CRT-based S3 client | https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/crt-based-s3-client.html | Automatic multipart and byte-range parallelism, and the `S3TransferManager` relationship |
| AWS SDK for Java 2.x — HTTP client configuration | https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/http-configuration.html | Apache vs URLConnection vs Netty vs `AwsCrtAsyncHttpClient`/`AwsCrtHttpClient`, and the connection-pool settings named in §2.22.4 |
| AWS CRT HTTP client GA announcement | https://aws.amazon.com/about-aws/whats-new/2023/02/aws-crt-http-client-sdk-java-2-x | GA at SDK 2.20.0, faster startup, smaller memory footprint, lower p90 latency, connection health monitoring and DNS load balancing; GraalVM native-image support from CRT 0.31.1 / SDK 2.28.7 |
| API Gateway integration timeout quota increase | https://repost.aws/knowledge-center/api-gateway-timeout-limit | REST API default 29 s raisable to **300 s** for Regional and private APIs since June 2024, **not** for edge-optimized, with a possible account throttle reduction; HTTP API a hard 30 s |
| Amazon EC2 IMDSv2 by default | https://aws.amazon.com/blogs/aws/amazon-ec2-instance-metadata-service-imdsv2-by-default/ | IMDSv2-only for newly released instance types from mid-2024, the account-level regional default (March 2024), the fact that existing instances are unaffected, and the hop-limit mechanism |
| Amazon Aurora DSQL product page and documentation | https://aws.amazon.com/rds/aurora/dsql/ and https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-migration-guide.html | GA 27 May 2025, active-active multi-Region with a writable endpoint in each peered Region, 99.99%/99.999% availability targets, and the limitation set: Repeatable Read only, one DDL per transaction, DDL and DML separated, **3,000 rows per transaction**, 1-hour connection timeout, no triggers/PL-pgSQL/temp tables/sequences/custom types/extensions/PostGIS/pgvector/`LISTEN`/`NOTIFY` |
| RDS Multi-AZ DB cluster comparison | https://www.pluralsight.com/resources/blog/tech-operations/rds-instances-single-multi-az-cluster | One writer plus **two readable standbys** across three AZs, Raft-based replication, **failover under 35 seconds**, MySQL and PostgreSQL only — to be re-verified against the RDS User Guide before writing |
| RDS Proxy with Blue/Green Deployments | https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-blue-green.html | RDS Proxy's switchover awareness removing the DNS-propagation gap, and the Aurora Serverless v1 exclusion |
| Amazon ECS task definition parameters for Fargate | https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html | The exact valid CPU/memory lattice from 256/512 MB to 16384/120 GB, the increment rules per tier, and the platform-version requirements for the 8 and 16 vCPU sizes |
| Announcing Amazon ECS Express Mode | https://www.amazonaws.cn/en/new/2026/announcing-amazon-ecs-express-mode/ | Express Mode's inputs (image plus two IAM roles), what it provisions (Fargate, ALB, HTTPS, autoscaling, an `*.ecs.*.on.aws` URL), the 25-services-per-ALB sharing, and the absence of a surcharge |
| Amazon ECS Managed Instances announcements | https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-ecs-managed-instances-gpu-price/ | ECS Managed Instances as a re:Invent 2025 launch, the AWS-managed EC2 fleet with EC2 pricing, and the July 2026 GPU management-fee reductions |
| Amazon EKS Pod Identity announcement | https://aws.amazon.com/blogs/containers/amazon-eks-pod-identity-a-new-way-for-applications-on-eks-to-obtain-iam-credentials/ | The Pod Identity agent model, removal of the per-cluster OIDC provider, the decoupling of roles from service accounts, role session tags, EKS-only availability, and the Auto Mode integration |
| AWS re:Invent 2025 recap coverage | https://www.eweek.com/news/aws-reinvent-2025-roundup-neuron/ and https://virtualizationreview.com/articles/2025/12/16/cloud-expert-details-best-stuff-from-aws-reinvent-2025.aspx | Graviton5, Lambda Durable Functions, **S3 single objects up to 50 TB**, S3 Vectors GA, and Database Savings Plans — each to be re-verified against a first-party AWS announcement before a number is written |
| S3 conditional writes | https://simonwillison.net/2024/Nov/26/s3-conditional-writes/ and https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html | `If-None-Match: *` semantics, the 412 Precondition Failed and 409 ConditionalRequestConflict distinction and the retry rule, `If-Match` for overwrite, and Express One Zone support |
| S3 conditional copy | https://www.amazonaws.cn/en/new/2025/amazon-s3-adds-conditional-write-functionality-to-copy-operations/ | Conditional copy in 2025 and the `s3:if-match` / `s3:if-none-match` bucket-policy condition keys |
| AWS data transfer pricing guides (2026) | https://blog.besharp.it/aws-data-transfer-costs-in-a-nutshell/ and https://www.usage.ai/blogs/aws/networking-cost/data-transfer-costs/ | **First 100 GB/month egress free**, then $0.09 → $0.085 → $0.07 → $0.05 per GB by tier; cross-AZ $0.01/GB each way; cross-region $0.02–$0.09; NAT $0.045/GB processing — all to be re-verified against the AWS pricing pages before a figure is written |
| Amazon CloudWatch pricing | https://aws.amazon.com/cloudwatch/pricing/ | Custom-metric tiering ($0.30 for the first 10,000, then $0.10 / $0.05 / $0.02), the 10 free metrics, and the logs ingestion/storage/scan meters |
| CloudWatch Application Signals and Transaction Search | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Transaction-Search-search-analyze-spans.html | Application Signals' RED metrics and SLOs, Transaction Search's 100% span retention, and the ADOT/OpenTelemetry enablement paths |
| AWS X-Ray OpenTelemetry / OTLP endpoint | https://docs.aws.amazon.com/xray/latest/devguide/xray-opentelemetry.html | The X-Ray OTLP endpoint and AWS's recommendation of OpenTelemetry over the X-Ray SDKs (maintenance mode) |
| DynamoDB partition and capacity guidance | https://newsletter.simpleaws.dev/p/partitions-sharding-split-for-heat-dynamodb and https://repost.aws/questions/QUGa1yY0HnQVOp-LDcRQjXQQ | The 3,000 RCU / 1,000 WCU / 10 GB per-partition ceilings, adaptive capacity's behaviour, split-for-heat, and the confirmation that adaptive capacity does not raise the ceiling — to be re-verified against the DynamoDB Developer Guide |
| Lambda SnapStart cold-start measurements | https://lcmh.fr/en/articles/2026/aws-lambda-snapstart-cold-starts-java-production/ and https://masturbyte.com/lambda-snapstart.html | Java 21 cold start 800–1,500 ms without SnapStart versus 50–90 ms with it, Java 11/17/21 and x86_64/arm64 support, and the zero-additional-charge claim — the figures are secondary sources and must be re-verified against the Lambda SnapStart documentation |
| AWS Certified Solutions Architect – Associate (SAA-C03) exam guide | https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Exam-Guide_C03.pdf | The four domains and their weights (Secure 30%, Resilient 26%, High-Performing 24%, Cost-Optimized 20%), used purely as a completeness probe against the leaf list |
| Common AWS infrastructure mistakes (2026) | https://squareops.com/blog/the-most-common-aws-infrastructure-mistakes-and-how-to-avoid-them/ | The adversarial/completeness probe: over-provisioning, no IaC, over-permissive IAM, skipped multi-AZ, absent autoscaling, and missing cost-allocation tagging — each mapped to an existing leaf |
| Infrastructure as code on AWS (2026) | https://towardsthecloud.com/blog/infrastructure-as-code | CloudFormation **drift-aware change sets** (three-way comparison), the confirmation that `cdk diff` does not detect drift, and the CDK/SAM/Terraform selection guidance |
| AWS Graviton technical guide | https://aws.github.io/graviton/ and https://github.com/aws/aws-graviton-getting-started | Graviton generations and their Neoverse cores, the `g` suffix convention, managed-service Graviton support, and the JVM porting guidance |
| AWS EC2 instance types history | https://hidekazu-konishi.com/entry/amazon_ec2_instance_types_history_and_timeline.html | The instance-family naming grammar and the generation timeline including Graviton5 `M9g`/`C9g` GA in 2026 — to be re-verified against the EC2 instance-types documentation |

**Searches that returned nothing usable.** No first-party AWS page was located that states a single
authoritative "current" AWS SDK for Java v2 patch version, because the artifact is released
continuously; the write pass must cite the SDK's GitHub releases page and state the version it
verified against rather than quoting a fixed number. No published, named, first-party postmortem was
found for a customer-side AWS cost incident with a specific figure, so §2.19's cost claims must be
derived from the Appendix A volumes and the published rate cards rather than attributed to an
anecdote. No canonical university syllabus for "cloud computing on AWS" was located; the curriculum
angle was covered instead by the SAA-C03 exam guide's domain weights and the Well-Architected
pillars.

---

## Gaps vs the current guide

`src/topics/18-cloud-aws.md` is 619 lines across 9 sections plus a 59-item atomic concept checklist.
**Every concept in it survives as a leaf.** The table below is the work order.

| Syllabus area | Present in `src/topics/18-cloud-aws.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why cloud exists | absent | **the entire origin section** — elasticity, capex/opex, operational transfer, the costs, when not to move, the IaaS/PaaS/FaaS spectrum, the "AWS is an HTTP API" framing | — |
| §1.2 regions and AZs | § 1 — strong: isolation, AZ definition, why the construct exists, three-vs-two arithmetic, AZ ID randomisation, multi-region caution | `us-east-1` as a special case; Local Zones, Wavelength, Outposts; Global Accelerator; the backbone; regional edge caches; ARC zonal shift | edge locations mentioned in one line |
| §1.3 shared responsibility | absent | **the entire subject** — the per-service line, the resilience corollary, compliance inheritance, Artifact | — |
| §1.4 accounts and Organizations | § 3 closing paragraph — one sentence on account-per-environment; SCPs named | the whole org model: root user, OUs, RCPs, declarative policies, Control Tower, Identity Center, consolidated billing, the standard topology, ARN grammar, partitions, quotas as per-account | SCPs described in one sentence |
| §1.5 the API model | absent | **the entire subject** — endpoints, SigV4, session tokens, clock skew, **control plane vs data plane**, control-plane eventual consistency, idempotency tokens, throttling as a normal response | — |
| §1.6 IAM model | § 3 — strong: the four concepts, the role mechanism, the five plumbings, policy structure, evaluation order, SCPs/boundaries/resource policies, least privilege, MFA/root/CloudTrail | the six policy types as a table; the set arithmetic; the `2012-10-17` trap; STS operations and session limits; role chaining's 1-hour cap; IAM Roles Anywhere; `get-caller-identity`; reading an `AccessDenied` | boundaries and resource policies get one sentence each |
| §1.7 EC2 | § 2 — families, `t` credits, EBS vs instance store, Spot/RI/Savings Plans, user data, IMDS, IMDSv2, Capital One | the naming grammar; Graviton generations; placement groups; AMIs; the lifecycle state table; status checks; EIP and public-IPv4 charging; Session Manager vs bastions; Nitro Enclaves; the IMDSv2 wire protocol; **IMDSv2 default and account-level enforcement** | purchasing models listed without the Savings Plan arithmetic |
| §1.8 block/file/object | § 2 — one paragraph on EBS vs instance store | the three-shapes distinction; **the full EBS volume-type table with current numbers**; `gp2 → gp3`; EBS durability being 99.8–99.9%; EBS-optimised bandwidth ceilings; EFS/FSx; AWS Backup | EBS described in two sentences |
| §1.9 S3 | § 2 — strong: the not-a-filesystem table, consequences, durability-is-not-backup, storage classes, lifecycle, incomplete multipart, presigned URLs, Block Public Access, encryption defaults | object/bucket/key limits and **50 TB objects**; multipart mechanics and the ETag algorithm; the full storage-class table with minimum durations and billable sizes; Intelligent-Tiering's tiers; versioning and delete markers; Object Lock; replication and RTC; the four access-control mechanisms; **conditional writes**; event notifications; Access Points; Requester Pays/Inventory/Storage Lens/Batch; Mountpoint; S3 Tables and Vectors; data-event logging | storage classes listed without numbers; presigned URLs lack the expiry-truncation trap and the POST policy |
| §1.10 RDS/Aurora | § 2 and § 9 — the managed-service description, key knobs, Aurora's 6/3, connection management, RDS Proxy, and the full Multi-AZ vs read-replica table with its gotchas | **Multi-AZ DB cluster**; Aurora Serverless v2 and scale-to-zero; Global Database; I/O-Optimized; **Aurora DSQL**; Blue/Green; IAM auth; storage autoscaling and the no-shrink rule; parameter-group static/dynamic; Performance Insights; the metric set; the 35-day backup ceiling against a 7-year requirement | connection arithmetic stated as a rule but not computed for this estate |
| §1.11 non-relational | absent apart from DynamoDB in the index scope line | **the entire subject** — DynamoDB's model, capacity, consistency, GSI/LSI, hot partitions, key design, single-table, Streams, TTL, Global Tables, DAX; ElastiCache/MemoryDB; OpenSearch; the specialist stores; Redshift/Athena/Glue | — |
| §1.12 VPC | § 4 — strong: CIDR, subnets-per-AZ, public/private, three-tier, the SG-vs-NACL table, stateful/stateless, SG referencing, gateway vs interface endpoints, peering/TGW/Flow Logs | the 5 reserved IPs; CIDR planning; IGW mechanics; **NAT per AZ and port exhaustion**; egress-only IGW; SG quotas; endpoint policies; PrivateLink as a provider; VPN vs Direct Connect; VPC DNS and the resolver limit; Reachability Analyzer; IPv6; ENIs and pod density; MTU | endpoints covered well but without the cost arithmetic |
| §1.13 load balancing and edge | § 2 — ALB/NLB feature lists, cross-zone, Route 53 policies, Alias records, DNS-failover caution | GWLB; target-group parameters and **deregistration delay as drain-before-terminate**; idle timeout and the 502 keep-alive race; ELB-vs-Target 5XX; access logs; **the entire CloudFront section**; WAF/Shield; ARC and zonal shift; Global Accelerator | Route 53 policies listed without the health-check mechanism |
| §1.14 serverless | § 2 — Lambda cold start, mitigations, limits, globals persisting, good/bad fits; SQS/SNS/EventBridge in outline | the full quota table; the execution-environment lifecycle; **SnapStart's three hazards**; concurrency types and the burst rate; the concurrency formula; invocation models and destinations; VPC Hyperplane; layers and extensions; **Durable Functions, MicroVMs, Managed Instances**; **the entire API Gateway section**; **the entire Step Functions section**; EventBridge in depth; App Runner/AppSync | cold-start numbers are approximate and pre-SnapStart-arm64 |
| §1.15 containers | § 2 — task definition, service, EC2 vs Fargate, the ECS-vs-Kubernetes positioning | ECR; **the two IAM roles and their distinction**; **ECS Managed Instances and Express Mode**; the Fargate CPU/memory lattice; `awsvpc`; deployment circuit breaker and Service Connect; capacity providers; **the entire EKS section including IRSA vs Pod Identity**; the VPC CNI IP-exhaustion problem; Karpenter; the EKS cost floor | launch types described without the lattice or the pricing arithmetic |
| §1.16 config and secrets | § 6 — twelve-factor, env vars, Parameter Store, Secrets Manager, AppConfig, the rule of thumb, injection by ARN, the cached-forever trap | Parameter Store throughput and the startup stampede; the four-step rotation contract and staging labels; change propagation; AppConfig strategies and validators; CI/CD OIDC; the Spring `spring.config.import` surface | rotation named but its mechanism absent |
| §1.17 observability | § 2 — CloudWatch metrics/logs/alarms/dashboards/Synthetics, retention default, the cardinality trap | the resolution/rollup table; EMF; Logs Insights; alarm evaluation semantics; **Application Signals and Transaction Search**; **X-Ray and its maintenance-mode status**; CloudTrail management vs data events; AWS Config; the Health Dashboard; AMP/AMG | alarms and metrics get one line each |
| §1.18 AWS SDK for Java v2 | one presigned-URL code fragment | **the entire subject** — v1 EOL, client singletons, the credential provider chain, sync vs async vs CRT, `ClientOverrideConfiguration`, the exception taxonomy, paginators, waiters, the Enhanced Client, SDK metrics, GraalVM, the CLI | — |
| §1.19 Spring Cloud AWS | absent | **the entire subject** — the compatibility matrix, the starters, `S3Template`, `@SqsListener`, `DynamoDbTemplate`, `spring.config.import`, the endpoint override | — |
| §1.20 infrastructure as code | named in the index scope line only, absent from the file | **the entire subject** — CloudFormation, drift-aware change sets, CDK, SAM, Terraform, the comparison, immutable infrastructure, CI/CD and OIDC | — |
| §1.21 cost | § 8 — strong: the six surprise categories with numbers, the practices list, the "cost is a design constraint" framing | the four billing dimensions; **the current egress tiering including the 100 GB free allowance**; the cross-AZ/multi-AZ tension resolved with AZ-aware routing; public IPv4 charging; Database Savings Plans; CUR 2.0 and Cost Optimization Hub; unit economics; the FinOps ownership point | data-transfer numbers predate the 2024–2026 changes |
| §1.22 Well-Architected | absent | **the entire subject** — the six pillars, the general design principles, the tool and lenses, and its use as an interview scaffold | — |
| §2.1–2.3 selection procedures | absent | **the entire subject** — the ordered questions and master tables for compute, storage and database, with the crossover arithmetic | — |
| §2.4 EC2 capacity | § 2 — pricing models listed | Savings Plan arithmetic; Spot mechanics and rebalance recommendations; Capacity Reservations; `InsufficientInstanceCapacity`; credit arithmetic | — |
| §2.5 S3 in depth | § 2 — presigned URLs and lifecycle | the upload flow; POST policies; multipart sizing; byte-range fetches; **prefix partitioning and 503**; the obsolete hash-prefix advice; what strong consistency excludes; conditional writes as a primitive; event sourcing; Access Points; the bucket-policy pattern set; the cross-account ownership trap; replication in depth; request-cost arithmetic | — |
| §2.6 IAM in depth | § 3 — the evaluation rule and least-privilege procedure | the full flowchart; **cross-account requiring both sides**; trust policies and `ExternalId`; the confused deputy worked; boundaries with the delegation example; SCP patterns; the condition-key catalogue; operator subtleties; ABAC; `NotAction`; wildcard forward-compatibility; Access Analyzer; credential report and Access Advisor; service-linked roles; resource policies per service; Cognito; the security-service set | — |
| §2.7 VPC in depth | § 4 | route-table evaluation; the worked packet trace; the debugging tree; Flow Log field reading; NAT failure modes; endpoint economics; private DNS; endpoint policies; TGW appliance mode; overlapping CIDRs; IPAM; network performance; the SG rule-limit constraint | — |
| §2.8 LB in depth | § 2 | routing evaluation; health-check arithmetic; **the JVM warm-up problem and slow start**; draining sized against a real request; sticky sessions argued; weighted target groups; NLB flow hashing; client-IP preservation in Spring; the 502/503/504 triage table; CloudFront cache-key design; invalidation economics; the GA/Route 53/CloudFront three-way | — |
| §2.9 RDS in depth | § 9 — the comparison table, replica-lag gotchas, DNS-cache warning, pool validation | the failover traces for both deployment shapes; the survival checklist; the exact DNS TTL defaults; reader-endpoint per-connection balancing; Spring read/write splitting; the lag-mitigation menu; RDS Proxy pinning; IAM auth; backups vs a 7-year requirement; parameter groups; Performance Insights; Aurora storage as an operational fact; the AWS JDBC driver; Serverless v2 behaviour; Blue/Green; **the computed connection budget** | — |
| §2.10 DynamoDB in depth | absent | **the entire subject** | — |
| §2.11 Lambda in depth | § 2 | the invocation trace; what goes outside the handler; Spring Cloud Function; SnapStart mechanics and hazards and constraints; provisioned-concurrency arithmetic; ESM configuration; **the SQS+Lambda connection stampede**; VPC internals; the error-handling table; cost arithmetic; Power Tuning; reading a `REPORT` line; Durable Functions | — |
| §2.12 containers in depth | § 2 | the task lifecycle and its stuck states; `stopTimeout` and graceful shutdown; the `STOPPED` reason catalogue; task vs container limits; **the JVM-in-a-container memory arithmetic**; service autoscaling; the circuit breaker; Service Connect; log drivers; ECS Exec; Fargate platform details; Fargate Spot; EKS in depth; the EKS cost floor; image supply chain | — |
| §2.13 scaling | § 7 — strong: vertical vs horizontal, the four statelessness breakages, the extra three, sticky sessions, target tracking, scale-out-fast, warm-up time, the wrong-tier warning | ASG mechanics (launch templates, instance refresh, warm pools, lifecycle hooks); the policy-type table and the proportional-metric rule; Little's Law applied to autoscaling; queue-depth scaling oscillation; **the list of limits you hit before the instance limit** | policies named without the metric-selection rule |
| §2.14 resilience and DR | absent | **the entire subject** — RTO/RPO, the four strategies, availability arithmetic, SLAs as refunds, **static stability**, cells and shuffle sharding, graceful degradation, the client-side resilience set, retry storms, lying health checks, FIS and game days, backup strategy, multi-region honestly, region evacuation | — |
| §2.15 config in depth | § 6 | the four-store table; hierarchy design; throughput and the startup stampede; the rotation contract; the survival requirement; change propagation; AppConfig strategies; CI/CD OIDC | — |
| §2.16 deployment | absent | **the entire subject** — the four release strategies, their AWS implementations, migrations under live traffic, immutable deployments, the safety checklist, and the `PaymentRun` case | — |
| §2.17 encryption and KMS | § 2 — one line on SSE-S3 vs SSE-KMS | **the entire subject** — the KMS model, envelope encryption, KMS request quotas and Bucket Keys, encryption-at-rest per service, encryption in transit, CloudHSM, and the QuizStakes key hierarchy | — |
| §2.18 observability in depth | § 2 | what to instrument; Logs Insights queries; correlation across services; Micrometer routing; **the alert set with thresholds**; the cost of observability; the incident toolkit ordering; CloudTrail forensics | — |
| §2.19 cost engineering | § 8 | building the bill from first principles; the cross-AZ arithmetic; the rightsizing and commitment passes; unit economics; showback; the anti-pattern catalogue | — |
| §2.20 managed-service trade-off | § 5 — strong: what managed gives and costs, where to draw the line, lock-in as a spectrum, keeping business logic vendor-free | the on-call-surface argument quantified; the hexagonal-port discipline as code | — |
| §2.21 multi-tenancy and quotas | absent | **the entire subject** | — |
| §2.22 the Java service wired to AWS | absent | **the entire subject** — credential debugging, timeout layering, retry configuration, SDK pooling, virtual threads, LocalStack and what it cannot prove, IAM testing, local development, graceful shutdown, configuration precedence | — |
| §3.1–3.12 internals | absent | **the entire Part 3** — Nitro, EBS as network storage, S3's index/data split and prefix partitioning and eleven-nines derivation, the VPC mapping service and connection tracking, ALB/NLB/Hyperplane internals, SigV4 derived, IMDSv2 on the wire, the IAM evaluation engine, Route 53 anycast and the JVM DNS cache, Lambda's Firecracker/Assignment Service/SnapStart, DynamoDB partitions and split-for-heat, Aurora's log-is-the-database and 4/6 quorum, and the CloudWatch metric pipeline | — |
| §3.13 failure catalogue | § 2 mentions Capital One | **the October 2025 outage in full**, the S3 2017 and Kinesis 2020 incidents, and a consolidated 25-entry symptom → cause → metric → fix table | Capital One named in one sentence |
| §3.14 proofs | § 1 states the three-AZ arithmetic informally | every proof worked: eleven nines, N/(N−1), availability composition, Aurora's quorum, Little's Law, the utilisation curve, the connection ceiling, DynamoDB capacity, the lifecycle saving, NAT vs endpoint, cross-AZ chatter, the Lambda/Fargate crossover, Savings Plan break-even, failover detection time, retry amplification, `t3` credits, container memory | — |
| §3.15 version history | absent | **the entire subject** — and it is where every `[VERSION-TRAP]` lives | — |
| §4 build it | one 6-line presigned-URL snippet and one ECS YAML fragment | all 20 implementations and their Diff tables | — |
| §5 interview and retention | the atomic checklist only (59 lines) | the 35 questions, the 50-plus trap list, the constants/cost/decision/service cheat sheets, the debugging trees, the verbal answers, the seniority ladder, and the retention plan | the checklist is good and must be carried forward verbatim-plus-expansion |

**Corrections the write pass must make to existing text** (not additions — the current file is wrong
or stale here):

1. § 1's "sub-millisecond, single-digit ms worst case" for inter-AZ latency is right but should carry
   the *reason* it matters (synchronous replication feasibility) rather than being stated as trivia.
2. § 2's EC2 storage paragraph gives no EBS volume types or numbers; it must gain the current table,
   in which **`gp3` is 80,000 IOPS / 2,000 MiB/s** and `io2 Block Express` is 256,000 / 4,000, and
   must state that EBS durability is **99.8–99.9% annual, not eleven nines**.
3. § 2's Lambda paragraph says cold starts are "1–10 seconds" and offers SnapStart as one option
   among several. Restate: **800–1,500 ms for Java 21**, **50–90 ms with SnapStart**, SnapStart is
   free and supports Java 11/17/21 on x86_64 **and arm64**, and it should be the *default* answer,
   with Provisioned Concurrency as the fallback.
4. § 2's Lambda limits list ("15-minute max execution") must note **Durable Functions** and
   **MicroVMs (8 hours)** as the 2026 answers to that constraint.
5. § 2's CloudWatch paragraph says log groups default to "never expire". Verify against the current
   console/API behaviour and state it precisely, including the Infrequent Access log class.
6. § 3's role-mechanism walkthrough contains a typo — it writes `169.254.169.253` before correcting
   itself to `169.254.169.254`. Remove the error and give the IMDSv2 `PUT`-then-`GET` sequence
   rather than the v1 `GET`.
7. § 3 lists SCPs, permission boundaries and resource-based policies in one paragraph; it must gain
   **RCPs** and the union/intersection arithmetic.
8. § 8's data-transfer figures omit the **100 GB/month free egress allowance** and the **public IPv4
   hourly charge introduced in February 2024**; both change the arithmetic.
9. § 9's Multi-AZ row says "the standby is invisible and idle (Multi-AZ *cluster* deployments are the
   exception: two readable standbys)". Promote that parenthetical: state the **Raft-based protocol
   and the sub-35-second failover** explicitly.
10. § 2's ECS section describes only the EC2/Fargate launch-type pair; it must add **ECS Managed
    Instances** and **ECS Express Mode**.
11. § 2's presigned-URL code uses `S3Presigner.create()` with no region or credentials configuration
    and no note that the URL's life is capped by the signing credential's life. Both must be fixed.
12. Every reference to the AWS SDK must be explicitly **v2**, with a note that **v1 is end-of-support
    as of 31 December 2025**.

---

**Leaf counts.**

| Part | Leaves |
|---|---|
| PART 1 — Basics | 342 |
| PART 2 — Intermediate | 231 |
| PART 3 — Under the hood | 131 |
| PART 4 — Build it | 40 (20 implementations + 20 Diff tables) |
| PART 5 — Interview & retention | 62 |
| **Total** | **806** |

**`[RESEARCH]` leaves: 61.** They cluster in the version-delta areas — the October 2025 post-event
summary, Lambda Durable Functions / MicroVMs / Managed Instances quotas, SnapStart's arm64 support
and measured cold-start figures, S3 conditional writes and conditional copy and the 50 TB object
limit, S3 Tables and S3 Vectors, Express One Zone's directory-bucket semantics, `gp3`'s current IOPS
and throughput ceilings, Aurora DSQL's limitation set, the RDS Multi-AZ DB cluster's failover figure,
Blue/Green deployments, ECS Managed Instances and Express Mode, EKS Pod Identity and Auto Mode, the
Fargate CPU/memory lattice, API Gateway's 300-second timeout, IMDSv2 default enforcement, RCPs and
declarative policies, the 2026 data-transfer and CloudWatch price tiers, KMS request quotas,
CloudWatch Application Signals and Transaction Search, the X-Ray maintenance-mode status, Spring
Cloud AWS 4.0's compatibility matrix, the CRT client's GA and GraalVM versions, CloudFormation
drift-aware change sets, Graviton5 availability, and DynamoDB's adaptive-capacity behaviour. Every
one must be re-fetched from its cited source before the write pass commits a number.

**`[VERSION-TRAP]` leaves: 38.** **`[PROVE]` leaves: 96.** **`[BUILD]` leaves: 20.**
**`[TRAP]` leaves: 118** (of which 50-plus are consolidated in §5.2). **`[SOURCE]` leaves: 11.**
**`[INCIDENT]` leaves: 8.** **`[COST]` leaves: 27.** **`[X-REF]` leaves: 63.**
