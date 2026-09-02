# Syllabus — 22 System Design

**Target date: 2026-09-02.** This topic has no language version, so the currency anchor is the
state of practice as of Q3 2026: AWS/GCP primitives current to the 2024–2026 releases (Aurora DSQL
GA, DynamoDB global tables multi-Region strong consistency, Kafka 4.x on KRaft with tiered
storage), the post-2021 failure vocabulary (metastable failure, grey failure), the cell-based /
shuffle-sharding architecture guidance AWS published as formal Solutions Library guidance, and
DDIA 2nd edition (published February 2026) as the reference curriculum. Every constant that is a
vendor price, a service limit, or a product capability carries `[RESEARCH]` and must be
re-verified against its cited source in the write pass — those move faster than anything else in
this file. Physics numbers (RTT, memory latency, disk seek) do not move and are not tagged.

**Scope boundary.** This guide is the **composition layer**. It owns *how components are assembled
under a stated load, defended with arithmetic, and priced against the failures each choice buys*.
It does not own any component's internals:

| Owned elsewhere | Guide | What 22 still says |
|---|---|---|
| Relational modelling, indexes, plans, ACID, isolation, MVCC, online schema change | 09 | One paragraph on the design-level consequence, then point |
| TCP/TLS/HTTP versions, DNS, L4 vs L7 mechanics, keep-alive, epoll, WebSocket/SSE mechanics, CDN mental model | 10 | The routing/topology decision, not the protocol |
| REST resource modelling, verbs, status codes, versioning, error contracts, HATEOAS, gRPC/GraphQL | 12 | The three design-level API decisions and their downstream constraints |
| Kafka partitions/offsets/consumer groups/rebalance, delivery semantics, DLQ, RabbitMQ, outbox mechanics | 14 | Which work goes async, queue vs log, backpressure as a decision |
| Cache-aside/through/behind, eviction, TTL, stampede, Redis structures and persistence | 15 | Tier placement and the 0%-hit-ratio arithmetic |
| EC2/S3/RDS/DynamoDB/SQS/Lambda, IAM, VPC, ALB/NLB, autoscaling, AZ/region failure, cost drivers, IaC | 18 | The topology and the dollar axis |
| Images, Pods, Deployments, Services, probes, rolling updates, HPA | 19 | Rollout strategy as a design property |
| Metrics/logs/traces, Micrometer, Prometheus, tracing, SLI/SLO/error budgets, incident response, postmortems | 20 | The three things that must appear in a design review |
| Concurrency mechanics, memory model, thread pools, backpressure in-process | 05 | Only where a design-level pattern is implemented in Java |
| AuthN/AuthZ, OAuth/OIDC, OWASP | 13 | Multi-tenancy isolation and the auth hop in the request path |

Leaves owned elsewhere carry `[X-REF nn]`. The rule for the write pass: **state the mechanism in
one paragraph, then point.** A bible never sends the reader away empty-handed, and it never
silently re-owns a sibling's internals either.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through with real arithmetic, do not state the result |
| `[SOURCE]` | quote the real primary source (paper, spec, docs, config reference) and explain every line |
| `[BUILD]` | ship complete, compiling, generic Java 21 code plus a "Diff vs the real one" table |
| `[TRAP]` | must carry a `**Trap:**` marker — the wrong belief, the symptom, the fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[CURRENCY]` | a vendor number, limit or capability that changes between releases; date-stamp it |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number and show the arithmetic |
| `[DESIGN]` | a worked design cluster: estimation → key design → bottleneck → deep dive |
| `[SAY]` | a sentence the candidate should be able to say out loud, verbatim, under time pressure |

---

# PART 1 — BASICS

## §1.1 Why distributed systems exist at all

1.1.1 The four forcing functions, and the fact that only one of them is "scale": **volume** (the
      data does not fit one machine), **throughput** (the work does not fit one machine's CPU or
      I/O), **availability** (one machine's MTBF is not good enough), **locality/latency** (users
      are far from the machine). Regulatory data residency is a fifth, non-technical one.
1.1.2 The default answer is *one machine*, and it is a much bigger machine than most candidates
      think: a 2026 commodity server is 128–192 vCPU, 1–2 TB RAM, and NVMe at millions of IOPS.
      `[NUM]` `[TRAP]`
1.1.3 What you buy when you distribute: horizontal scale, fault isolation, geographic locality.
1.1.4 What you pay, itemised: partial failure becomes possible, the network is now in every call
      path, there is no global clock, consistency becomes a choice rather than a given,
      operations multiply, and the debug surface becomes distributed.
1.1.5 The **fallacies of distributed computing** (Deutsch/Gosling, 1994) enumerated with the
      concrete bug each one produces: the network is reliable / latency is zero / bandwidth is
      infinite / the network is secure / topology doesn't change / there is one administrator /
      transport cost is zero / the network is homogeneous. `[RESEARCH]`
1.1.6 **Partial failure** as the defining property: in a single process a call either returns or
      the process dies; over a network a call can also hang, return late, or succeed invisibly.
      That third outcome is the origin of every idempotency requirement in this guide. `[PROVE]`
1.1.7 The two-generals / unknown-outcome result, stated informally: no finite protocol makes a
      remote effect and a local record of it simultaneously certain. This is why "exactly once"
      is achieved at the effect layer, never at the delivery layer (§1.21). `[PROVE]`
1.1.8 Scale-up vs scale-out as an economics question, not an ideology: vertical scaling has a
      price cliff and a single failure domain; horizontal scaling has a complexity floor.
1.1.9 The design-review framing this whole guide serves: a design is a set of *decisions*, each
      with a stated input number, a chosen mechanism, and a named cost. Boxes and arrows are the
      artifact, not the deliverable. `[SAY]`
1.1.10 The reader's other use for this file: it is the checklist for reviewing a design document
       at work, not only for the interview. Every section should be usable as a review question.

*(10 leaves)*

## §1.2 What the system-design round actually measures

1.2.1 The five signals in scoring order: requirement discipline, quantitative reasoning, trade-off
      articulation, failure thinking, communication/driving.
1.2.2 Requirement discipline: QPS, data size, read:write ratio, latency target and consistency
      need extracted *before* anything is drawn.
1.2.3 Quantitative reasoning: every component count derived from a number. "3 shards" follows
      from "6 TB / 2 TB per node", never from taste. `[SAY]`
1.2.4 Trade-off articulation: naming what you gave up, not only what you chose.
1.2.5 Failure thinking: for every box, what happens when it **dies**, when it is **slow**, when it
      is **full**. Three questions, every box, no exceptions.
1.2.6 Communication and driving: structuring the time, stating assumptions aloud, checking in
      before moving on.
1.2.7 **Trap:** treating the round as a knowledge quiz. Naming DynamoDB, Kafka and Redis scores
      nothing alone; the score is in "Dynamo because the access pattern is a point lookup by user
      ID and I need predictable p99 at 40k QPS; the cost is that the leaderboard query becomes a
      separate read model." `[TRAP]` `[SAY]`
1.2.8 The interviewer's questions are the rubric, not interruptions. A steer toward hot keys means
      hot keys is the graded item. `[TRAP]`
1.2.9 Memorised architectures are detectable and score badly: the interviewer perturbs one input
      (10× the users, or "now it must be strongly consistent") and a memorised answer cannot
      move. `[RESEARCH]` `[TRAP]`
1.2.10 The round is a simulation of a design review with a skeptical senior colleague; the
       behaviours that pass are the behaviours that pass at work.

*(10 leaves)*

## §1.3 The clock: how the 45 minutes is spent

1.3.1 Requirements + scope cut: 5–8 minutes. Output: functional list, non-functional numbers,
      explicit out-of-scope list.
1.3.2 Estimation: 3–5 minutes. Output: QPS, storage/year, bandwidth, and the resulting bottleneck.
1.3.3 API + data model: 5 minutes. Output: endpoint signatures, table/collection shapes, the
      primary key and what query it serves.
1.3.4 High-level design: 10 minutes. Output: boxes and arrows that satisfy the requirements.
1.3.5 Deep dive: 10–15 minutes. Output: the one or two components the interviewer steers to.
1.3.6 Failure, scale, ops: 5 minutes. Output: bottleneck, single points of failure, what you'd
      monitor and alert on.
1.3.7 The 60-minute and 35-minute variants, and what gets cut from each: at 35 minutes the
      estimation compresses and the deep dive is one component; at 60 the interviewer usually
      adds a second deep dive or a migration question. `[RESEARCH]`
1.3.8 Whiteboard vs remote-doc mechanics: legible boxes, arrow direction meaning "calls", a
      persistent corner for the numbers, and a running out-of-scope list you can point back to.
1.3.9 The two-design-round loop at L6 and above, and why the second round is usually the
      operational/organisational one. `[RESEARCH]`
1.3.10 Time-boxing a rabbit hole aloud: "I can go three more minutes on the ID generator or move
       to the read path — which is more useful?" `[SAY]`

*(10 leaves)*

## §1.4 Requirements — the functional half

1.4.1 Write functional requirements as **verbs with an actor**: "a user posts", "a follower
      reads their feed", "an admin revokes a session".
1.4.2 The 3–5 rule: beyond five core operations, propose cutting, and say what you are cutting
      and why. `[SAY]`
1.4.3 Distinguishing the *core loop* from the *supporting cast* (auth, admin, moderation,
      billing, analytics) — the supporting cast is named as interfaces and deferred.
1.4.4 Out-of-scope must be **stated and written down**, not silently omitted; unstated omissions
      read as oversights.
1.4.5 Scope negotiation as an L6 signal: proposing the cut before the interviewer has to.
      `[RESEARCH]`
1.4.6 Actors beyond the end user that change the design: internal services, batch jobs, partner
      integrations, the mobile client's offline mode, the crawler/bot traffic share.
1.4.7 The "who is the client" question: browser, native mobile on a flaky network, another
      backend service, or a webhook receiver — each implies different retry, payload and
      auth behaviour. `[X-REF 12]`
1.4.8 Non-goals that are worth stating explicitly because interviewers probe them: no ML ranking
      in v1, no GDPR-grade deletion pipeline in v1, no multi-tenant isolation beyond row scoping.

*(8 leaves)*

## §1.5 Requirements — the six numbers

1.5.1 **DAU/MAU** — converts to QPS; the single most load-bearing input.
1.5.2 **Read:write ratio** — 100:1 makes cache and replicas the design; 1:1 makes the write path
      the design.
1.5.3 **Object size** — 500-byte rows and 5-MB videos are different systems (row store vs object
      store + CDN).
1.5.4 **Retention** — 30 days vs forever changes storage by 100× and decides whether tiering is
      needed.
1.5.5 **Latency target, p99 not average** — p99 < 100 ms forbids synchronous cross-region calls
      and deep fan-out.
1.5.6 **Consistency need per operation, not per system** — "follower count may be 30 s stale,
      account balance may not." `[SAY]`
1.5.7 The four numbers people forget: **peak-to-average ratio**, **growth rate** (what does this
      look like in two years), **geographic distribution of users**, and **the share of traffic
      that is bots/crawlers/retries**.
1.5.8 Durability as a separate axis from availability: "may we lose the last 5 seconds of writes"
      is a different question from "may we be down for 5 minutes". RPO vs RTO (§1.26).
1.5.9 Compliance inputs that change topology: data residency, right-to-erasure, audit retention,
      PCI/PII scoping. `[X-REF 13]`
1.5.10 The "you decide" response: state an assumption **with a number**, say what it changes, and
       move. "I'll assume 10 M DAU with a 3× peak factor — tell me if that's off, because it
       decides whether we shard." `[SAY]`
1.5.11 Writing the numbers in a persistent corner of the board so every later claim can point at
       them.
1.5.12 Cost as a stated requirement at L6: "under $50k/month at this scale" turns several
       otherwise-free choices into trade-offs (§2.2).

*(12 leaves)*

## §1.6 Availability arithmetic

1.6.1 The nines table: 99% = 3.65 d/yr = 7.2 h/mo; 99.9% = 8.8 h/yr = 43 min/mo; 99.99% = 52
      min/yr = 4.3 min/mo; 99.999% = 5.3 min/yr = 26 s/mo. `[NUM]`
1.6.2 What each tier implies architecturally: single box + manual recovery / multi-AZ with
      automated restart / multi-AZ active-active with no manual step in the recovery path /
      multi-region with every dependency also at five nines.
1.6.3 **Availability multiplies across serial dependencies.** Six four-nines services in one
      request path give 0.9999⁶ = 99.94%, not 99.99%. Work the multiplication. `[PROVE]` `[NUM]`
1.6.4 The corollary that scores: every synchronous dependency you add subtracts availability, so
      making a call asynchronous is an *availability* argument, not only a latency one. `[SAY]`
1.6.5 Redundancy composes the other way: two independent 99% replicas in parallel give
      1 − 0.01² = 99.99%, *if* the failures are independent. `[PROVE]` `[NUM]`
1.6.6 **Trap:** assuming independence. Correlated failure (same AZ, same deploy, same config
      push, same certificate expiry, same upstream DNS) is the normal case, and it is why "we
      have three replicas" is not an availability argument by itself. `[TRAP]`
1.6.7 Hard vs soft dependency: a dependency you can degrade around does not multiply into your
      availability. Classifying each dependency as hard or soft is a design deliverable.
1.6.8 MTBF, MTTR, and availability = MTBF/(MTBF+MTTR): the practical lever at four nines and
      above is almost always MTTR, not MTBF. `[PROVE]`
1.6.9 The SLA/SLO/SLI distinction, and why you never promise externally what you measure
      internally. `[X-REF 20]`
1.6.10 Error budget as the derived quantity: 99.9% over 28 days is 40 minutes of budget, and that
       budget is what pays for deploys and experiments. `[NUM]` `[X-REF 20]`
1.6.11 Availability is measured in *successful requests*, not uptime of boxes; the definition
       ("what counts as a failure") is part of the design. `[X-REF 20]`
1.6.12 **Trap:** claiming five nines casually. Five nines means 26 seconds a month, which forbids
       a human in the recovery path and forbids any single-region dependency. `[TRAP]`

*(12 leaves)*

## §1.7 The numbers you must have memorised

1.7.1 **Time:** 1 day ≈ 86,400 s ≈ 10⁵ s. So *X per day ÷ 10⁵ = X per second*. 1 M/day ≈ 12/s;
      1 B/day ≈ 12,000/s. This one identity does most of the arithmetic in the round. `[NUM]`
1.7.2 **Sizes:** 1 KB tweet-ish row, 100 KB thumbnail, 1–5 MB photo, ~50 MB/min of 1080p video.
      1 M × 1 KB = 1 GB; 1 B × 1 KB = 1 TB. `[NUM]`
1.7.3 **Powers:** 2¹⁰ ≈ 10³, 2²⁰ ≈ 10⁶, 2³⁰ ≈ 10⁹, 2⁴⁰ ≈ 10¹². KB/MB/GB/TB/PB as decimal
      approximations, and the fact that nobody will penalise the 2.4% error. `[NUM]`
1.7.4 The **latency ladder**, order of magnitude being the point: L1/L2 1–10 ns; main memory
      ~100 ns; uncontended mutex ~20 ns; 1 MB sequential from memory ~10 µs; SSD random read
      ~100 µs; 1 MB from SSD ~200 µs–1 ms; same-AZ RTT ~0.5 ms; Redis GET same AZ ~0.5 ms; warm
      indexed Postgres point lookup 1–5 ms; spinning-disk seek ~10 ms; cross-region US→EU RTT
      ~80–150 ms. `[NUM]`
1.7.5 The two derived facts that matter more than the ladder itself: **memory is ~1000× faster
      than SSD**, and **cross-region is ~200× a same-AZ hop**. `[PROVE]`
1.7.6 Bandwidth reference: 1 Gbps ≈ 125 MB/s, 10 Gbps ≈ 1.25 GB/s, and a single TCP stream's
      practical ceiling is set by window/RTT, not by link rate. `[NUM]` `[X-REF 10]`
1.7.7 Bandwidth-delay product as the reason a cross-region bulk copy needs parallel streams.
      `[PROVE]` `[X-REF 10]`
1.7.8 Storage physics: NVMe ~100k–1M IOPS, network-attached block storage typically capped by
      provisioned IOPS, and object storage measured in throughput not IOPS. `[CURRENCY]`
      `[X-REF 18]`
1.7.9 A **speed-of-light floor** for intuition: ~5 µs per km in fibre, so New York→London
      (~5,600 km) has a ~28 ms one-way floor and ~56 ms RTT before any equipment. `[PROVE]` `[NUM]`
1.7.10 **Trap:** quoting Jeff Dean's 2012 numbers verbatim as current. The *ratios* survive; some
       absolutes (disk seek, network throughput, SSD latency) have moved. Quote as orders of
       magnitude. `[TRAP]` `[RESEARCH]`

*(10 leaves)*

## §1.8 Back-of-the-envelope estimation as a procedure

1.8.1 The four-step procedure: (1) users → actions/user/day → actions/day; (2) ÷10⁵ → average
      QPS; (3) × peak factor → peak QPS; (4) × object size × retention → storage and bandwidth.
1.8.2 **Peak factor:** 2–3× average for a global consumer product; up to 10× for event-driven
      systems (ticket on-sale, live sport, flash sale). State which you're using and why.
      `[PROVE]`
1.8.3 Why the peak factor is a *design* input, not a fudge: you provision for peak, you pay for
      peak, and the difference between 3× and 10× is the difference between autoscaling and a
      queue in front of everything. `[SAY]`
1.8.4 Rounding discipline: round to one significant figure, keep powers of ten, never produce
      "1,247 QPS" — it implies false precision and wastes clock. `[TRAP]`
1.8.5 Storage arithmetic including the multipliers people drop: replication factor (×3),
      indexes (×1.3–2), and the row overhead of the storage engine. A "1 KB" row is rarely 1 KB
      on disk. `[NUM]` `[X-REF 09]`
1.8.6 Bandwidth arithmetic: egress = QPS × response size. 100k QPS × 10 KB = 1 GB/s = 8 Gbps,
      which is a real network-design and real-money number. `[PROVE]` `[NUM]`
1.8.7 Memory arithmetic for a cache tier: hot-set size × object size, and the working-set
      question ("what fraction of keys serve 90% of reads?"). `[NUM]`
1.8.8 Connection arithmetic: concurrent connections = QPS × average duration (Little's law), which
      is how you size WebSocket gateways and connection pools. `[PROVE]` `[NUM]`
1.8.9 **Worked example — 1 M DAU social feed:** 0.5 posts/user/day, 20 feed reads/user/day.
      Writes 500 k/day ÷ 10⁵ = 5/s avg, ~15/s peak. Reads 20 M/day ÷ 10⁵ = 200/s avg, ~600/s
      peak. Storage 500 k × 1 KB = 500 MB/day ≈ 180 GB/yr. `[PROVE]` `[NUM]`
1.8.10 The conclusion that must be said out loud from that example: at this scale the interesting
       problem is **fan-out read amplification**, not throughput — the design problem is query
       shape, not capacity. `[SAY]`
1.8.11 The same example at 500 M DAU: 2,500 writes/s, 100 k reads/s, 90 TB/yr — now you need
       sharding, a materialised feed, and a CDN. **The value of the estimate is that it tells you
       which problem you are solving.** `[PROVE]` `[SAY]`
1.8.12 Sanity checks against reality: compare the derived number to a known public system's
      order of magnitude and say if it looks wrong.
1.8.13 When *not* to estimate: if the interviewer says "assume it's huge", skip to the shape of
      the bottleneck and say you're skipping. Clock discipline beats completeness.
1.8.14 **Trap:** estimating and then never using the estimate. Every number must be spent on a
       decision later; an unused estimate is theatre. `[TRAP]`

*(14 leaves)*

## §1.9 Capacity rules of thumb per component

1.9.1 Stateless JVM service, simple JSON, 4 vCPU: 2k–10k RPS. `[NUM]`
1.9.2 Nginx / L7 proxy: 20k–50k RPS per node. `[NUM]`
1.9.3 Redis, single-threaded, simple commands: ~100k ops/s per instance. `[NUM]` `[X-REF 15]`
1.9.4 Postgres single primary, simple indexed writes: 5k–15k writes/s. `[NUM]` `[X-REF 09]`
1.9.5 Postgres read replica, cached point reads: 20k–50k reads/s. `[NUM]` `[X-REF 09]`
1.9.6 Kafka broker: ~100k msgs/s, ~100 MB/s. `[NUM]` `[X-REF 14]`
1.9.7 Node storage before it is operationally painful: 1–2 TB (rebuild time, backup time, and
      failover blast radius are what make bigger nodes painful, not capacity). `[PROVE]`
1.9.8 Elasticsearch shard sizing rule of thumb: 10–50 GB per shard, and shard count is fixed at
      index creation — a design-time decision, not a runtime one. `[RESEARCH]` `[CURRENCY]`
1.9.9 Object storage: effectively unbounded capacity, per-prefix request-rate scaling, and
      latency in the tens of milliseconds — not a database. `[CURRENCY]` `[X-REF 18]`
1.9.10 The honest framing for all of these: they are **order-of-magnitude sizing constants** whose
       purpose is to convert a load number into a box count in ten seconds. Say "order of
       magnitude" when you use them. `[SAY]`
1.9.11 How to derive a box count from them, with headroom: box count = peak QPS ÷ per-node
       capacity ÷ target utilisation (e.g. 0.5), then + N for AZ redundancy. `[PROVE]` `[NUM]`
1.9.12 Why target utilisation is around 50–70% and not 95%: queueing delay explodes as
       utilisation approaches 1 (§3.12), and you must survive losing an AZ. `[PROVE]`
1.9.13 The N+2 provisioning convention from the SRE literature: capacity for one planned removal
       plus one unplanned failure. `[RESEARCH]` `[SOURCE]`

*(13 leaves)*

## §1.10 The scale-up ladder and where each rung breaks

1.10.1 Rung 0 — one box, app + DB. Breaks when CPU or connections saturate, and any deploy is
       downtime.
1.10.2 Rung 1 — app and DB split, DB vertically scaled. Breaks at the price/availability limit of
       vertical scaling; still one SPOF.
1.10.3 Rung 2 — N stateless app instances behind a load balancer. Breaks on in-memory session
       state; the DB becomes the bottleneck.
1.10.4 Rung 3 — cache + read replicas. Breaks on write throughput, and replica lag becomes
       user-visible.
1.10.5 Rung 4 — async writes via a queue. Ordering and idempotency become the app's problem;
       eventual consistency becomes user-visible.
1.10.6 Rung 5 — shard the data. Cross-shard queries, transactions and rebalancing become hard.
1.10.7 Rung 6 — multi-region. Cross-region write conflicts and ~100 ms replication windows.
1.10.8 Rule 1: **statelessness is the enabler for rung 2 onward**; any per-user state in app
       memory must move out or be made sticky deliberately with a named cost.
1.10.9 Rule 2: **each rung buys throughput with consistency or complexity** — say which one, every
       time you climb. `[SAY]`
1.10.10 The ladder as a *narrative device*: starting at rung 0 and climbing on demand is the
        structure that makes a design defensible, because each step has a stated trigger.
1.10.11 **Trap:** starting at rung 6. Multi-region active-active with CRDTs for a 1 M-DAU app
        reads as inability to size a problem, which is a stronger negative than under-designing.
        `[TRAP]`
1.10.12 The inverse trap at L6: refusing to climb when the numbers demand it, or not naming the
        trigger at which you would. "One primary is fine at 1,000 writes/s; I revisit at 5,000."
        `[SAY]`
1.10.13 Rungs that are *not* on this ladder and are usually premature: microservice
       decomposition, service mesh, event sourcing, multi-cloud. Each is an organisational
       answer more often than a scaling one. `[TRAP]`

*(13 leaves)*

## §1.11 Statelessness and where state actually goes

1.11.1 Definition: a stateless service holds no request-spanning state in process memory; any
       instance can serve any request.
1.11.2 The four kinds of state that sneak in: HTTP session, in-progress multi-step operations
       (uploads, wizards), WebSocket/SSE connection registries, and in-process caches.
1.11.3 Where each goes: session → signed token or Redis; multi-step → a state row with an
       explicit status enum; connection registry → Redis with TTL + heartbeat (§5.3 chat); cache
       → accepted as a per-instance copy with a named staleness cost. `[X-REF 15]`
1.11.4 Sticky sessions: the mechanism (cookie or IP hash at the LB), and the three costs — deploys
       drop state, autoscaling rebalances badly, and one hot client pins to one node. `[X-REF 10]`
1.11.5 Signed-token sessions (JWT): stateless, but revocation becomes a problem you must design
       (short TTL + refresh, or a revocation list that reintroduces state). `[X-REF 13]`
1.11.6 Stateful services that legitimately exist: databases, caches, brokers, connection gateways,
       stream processors with local state. The rule is to make the *stateful set small and
       explicitly managed*, not to pretend it doesn't exist.
1.11.7 Graceful shutdown as the statelessness test: can an instance be killed with 30 seconds'
       notice without a user noticing? Connection draining, in-flight request completion, and
       queue-consumer rebalance are the three parts. `[X-REF 19]`
1.11.8 **Trap:** "stateless" claimed for a service that holds an in-memory rate-limit counter or
       an in-memory idempotency set. Both are correctness-bearing state and both break under N
       instances. `[TRAP]`

*(8 leaves)*

## §1.12 API design at the composition layer

1.12.1 Write endpoints as **signatures** with the pagination and idempotency decisions visible;
       a contract constrains everything downstream and makes the deep dive concrete.
       `[X-REF 12]`
1.12.2 The canonical shape to be able to write in 30 seconds:
       `POST /v1/posts` with `Idempotency-Key: <uuid>` → `201 {postId}`;
       `GET /v1/feed?cursor=<opaque>&limit=50` → `200 {items[], nextCursor}`.
1.12.3 **Cursor pagination, not offset.** `LIMIT 50 OFFSET 100000` makes the database scan and
       discard 100,000 rows, so cost grows with page number; a cursor is
       `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC LIMIT 50`, one
       index seek regardless of depth. `[PROVE]` `[X-REF 09]`
1.12.4 The second, less-quoted reason for cursors: offset pagination **skips and duplicates** rows
       when items are inserted while the user pages. `[TRAP]`
1.12.5 Cursor construction: the tuple must be a **total order** (timestamp alone is not unique),
       it should be opaque (base64 of the tuple, optionally signed), and it must encode the sort
       direction and filter set so a client cannot mix them. `[BUILD]`
1.12.6 **Idempotency key on every non-idempotent write** — client-generated, server-stored as
       `key → (status, response body)` with a TTL, replayed on repeat (§1.21). `[X-REF 12]`
1.12.7 **Opaque IDs.** Sequential integers leak volume, enumerate your data, and make sharding
       harder later (§1.22).
1.12.8 Batch endpoints and the N+1 client problem: `GET /users?ids=a,b,c` exists to stop a client
       making 50 round trips, and it needs a documented maximum batch size.
1.12.9 Partial failure in batch endpoints: 207-style per-item status, or all-or-nothing — decide
       and document, because the client's retry logic depends on it. `[X-REF 12]`
1.12.10 Long-running operations: return `202 Accepted` with a status URL, or a job ID plus a
        polling/notification channel. Never hold the connection open for a transcode. `[X-REF 12]`
1.12.11 Compatibility rules that shape the design: additive-only changes, tolerant readers,
        version in the path or media type, and a deprecation window with measurable client
        migration. `[X-REF 12]`
1.12.12 Client-side behaviour you must design for: retries (so idempotency), caching headers (so
        cache keys), and offline queues in mobile clients (so duplicate submissions arrive
        hours late). `[TRAP]`
1.12.13 gRPC vs REST vs GraphQL at the composition layer, as a three-line decision: REST for
        public and cacheable, gRPC for internal high-QPS with schema evolution, GraphQL when
        client-shaped aggregation is the actual requirement — and GraphQL's cost is that one
        query can become an unbounded backend fan-out. `[X-REF 12]` `[RESEARCH]`
1.12.14 API gateway vs BFF vs service mesh, and the north–south / east–west split: gateway owns
        client-facing concerns (authn, rate limit, quota, transformation), BFF is a per-client
        gateway that owns aggregation for one frontend, mesh owns service-to-service mTLS,
        retries and circuit breaking via sidecars. `[RESEARCH]` `[X-REF 19]`
1.12.15 **Trap:** "the north–south / east–west split" treated as a hard rule. Modern gateways do
        east–west and modern meshes do ingress; the real distinction is *whose policy* it is —
        product-facing contract vs platform-enforced transport. `[TRAP]` `[RESEARCH]`

*(15 leaves)*

## §1.13 Data model and key design

1.13.1 Say the **primary key and the access patterns it serves** out loud — that single choice
       determines the storage engine. `[SAY]`
1.13.2 The canonical feed schema to be able to write from memory: `posts(post_id PK, author_id,
       body, created_at)` with index `(author_id, created_at DESC)`;
       `follows(follower_id, followee_id)` with reverse index `(followee_id, follower_id)`;
       `feed(user_id, created_at DESC, post_id)` as the materialised read model.
1.13.3 **The rule: in a distributed store you design the key from the query, not the query from
       the key.** A partition key that is not in the read path forces a scatter-gather over every
       node. `[SAY]`
1.13.4 Partition key vs sort/clustering key: the partition key decides *which node*, the sort key
       decides *the order within the node* and enables range scans. `[X-REF 09]`
1.13.5 Composite keys and the single-table-design idea in a wide-column/document store: putting
       related entities under one partition key to make a multi-entity read one request — and
       its cost, which is that the model now serves exactly the queries you anticipated.
       `[RESEARCH]`
1.13.6 Secondary indexes in a distributed store: **local** (same partition, cheap, still requires
       the partition key) vs **global** (its own partition scheme, eventually consistent, and a
       second write). `[RESEARCH]` `[X-REF 09]`
1.13.7 Denormalisation as a deliberate write-amplification trade: you pay N writes to make one
       read cheap, and you now own the consistency of the copies.
1.13.8 Normalisation's remaining home: when writes dominate, when the entity is authoritative, and
       when ad-hoc query flexibility matters more than read latency. `[X-REF 09]`
1.13.9 Schema-on-write vs schema-on-read, and the operational consequence: a document store moves
       the migration cost from `ALTER TABLE` to every reader forever. `[TRAP]`
1.13.10 Time-series shaping: partition by `(entity, time bucket)` so the partition has bounded
        size and old buckets can be dropped or tiered wholesale. `[NUM]`
1.13.11 Soft delete, tombstones and retention: deletes in an LSM/append-only store are writes,
        and tombstone accumulation is a real operational failure mode. `[X-REF 09]`
1.13.12 The "what is one row worth" question: row size × count × replication × index overhead
        drives the storage estimate (§1.8.5), so the model and the estimate are the same exercise.
1.13.13 Data lifecycle as part of the model: hot / warm / cold tiers, TTL-driven expiry, and
        archival to object storage. `[X-REF 18]`
1.13.14 PII and the erasure requirement: crypto-shredding (delete the per-user key) is the
        practical answer when the data lives in immutable logs and backups. `[RESEARCH]`
        `[X-REF 13]`

*(14 leaves)*

## §1.14 Storage selection as a decision procedure

1.14.1 The procedure, in order: (1) what is the access pattern; (2) does any operation need a
       multi-entity transaction; (3) what is the volume and growth; (4) what is the write rate vs
       a single primary's ceiling; (5) what is the consistency requirement per operation.
1.14.2 Access-pattern taxonomy: point lookup by key / range scan within a key / arbitrary
       multi-attribute filter / full-text / graph traversal / aggregation over history.
1.14.3 Under ~1 TB with joins and transactions, **"just use Postgres" is a correct answer and you
       should say it confidently.** `[SAY]`
1.14.4 Above ~10k sustained writes/s on one primary, plan for sharding or a natively sharded
       store. `[NUM]`
1.14.5 The fit table (relational / KV-wide-column / time-series / search / in-memory / object /
       columnar / graph) with the *why* for each, not the feature list.
1.14.6 Relational, joins, transactions, < 1 TB → Postgres/MySQL: ACID, mature indexing, cheap to
       operate. `[X-REF 09]`
1.14.7 Point read/write by known key, huge volume, predictable p99 → DynamoDB/Cassandra:
       partition-key routing, linear horizontal scale.
1.14.8 Write-heavy time series / append log → Cassandra, Timescale, ClickHouse: LSM writes,
       time-ordered partitions.
1.14.9 Full-text / faceted search → Elasticsearch/OpenSearch: inverted index; **never your source
       of truth**.
1.14.10 Sub-ms ephemeral structured values → Redis: in-memory, rich types. `[X-REF 15]`
1.14.11 Immutable blobs > 100 KB → object storage + CDN. Never binaries in a row store.
1.14.12 Analytics/aggregation over history → columnar warehouse (Snowflake, BigQuery, ClickHouse):
        column pruning + compression.
1.14.13 Multi-hop relationships → a graph store, or an adjacency table with a bounded traversal
        depth; recursive joins are expensive.
1.14.14 NewSQL / distributed SQL as the fourth option most candidates omit: Spanner, CockroachDB,
        Vitess, Aurora DSQL — horizontal scale with SQL and transactions, paid for in write
        latency and operational novelty. `[RESEARCH]` `[CURRENCY]`
1.14.15 Vector stores as a 2026-era entry: embedding search with ANN indexes (HNSW/IVF), used
        alongside — never instead of — the source of truth. `[RESEARCH]` `[CURRENCY]`
1.14.16 **Trap:** "NoSQL scales better" unqualified. It scales *writes on a known partition key*
        better; it makes ad-hoc queries, joins and multi-entity transactions worse or impossible.
        The trade is **query flexibility for scale**, and you should say it in exactly those
        terms. `[TRAP]` `[SAY]`
1.14.17 **Polyglot persistence is the normal answer at scale**, and its cost is a synchronisation
        path with lag and a failure mode. Prefer one source of truth plus derived read models fed
        by CDC or an event log (§1.27), never dual writes (§1.21).
1.14.18 Managed vs self-hosted as a real design axis: the managed service's limits and quotas
        become your design constraints, and its failure modes become ones you cannot fix.
        `[X-REF 18]`
1.14.19 The operability questions that decide between two technically-adequate stores: backup and
        restore time, schema-change story, upgrade story, who on the team has run it at 3 a.m.
        `[SAY]`

*(19 leaves)*

## §1.15 Replication

1.15.1 What replication buys: read throughput, durability, and failure tolerance. What it always
       costs: a lag window.
1.15.2 **Single-leader async:** leader applies and ships the log to followers. Follower reads can
       be stale by ms–seconds; failover can lose acknowledged writes. `[X-REF 09]`
1.15.3 **Single-leader semi-sync:** leader waits for ≥1 follower ack. Write latency += one round
       trip; no data loss on single-node failure.
1.15.4 **Multi-leader:** both sides accept writes and replicate to each other. Write conflicts
       become yours to resolve; justified only for multi-region write locality or offline clients.
1.15.5 **Leaderless (quorum):** client/coordinator writes W, reads R. Requires conflict resolution
       and repair (§1.18).
1.15.6 Replication mechanisms: statement-based (unsafe with non-determinism), write-ahead-log
       shipping (version-coupled), logical/row-based (the modern default, and what CDC reads).
       `[X-REF 09]`
1.15.7 Synchronous replication's real cost is not the RTT but the **availability coupling**: a
       synchronous follower that is down blocks writes unless you degrade to async. `[PROVE]`
1.15.8 **Read-your-writes:** after a user's own write, route that user's reads to the leader (or a
       replica whose log position ≥ the write's) for a window. This is the "I posted a comment and
       it vanished" bug. `[TRAP]`
1.15.9 **Monotonic reads:** pin a user to one replica (hash the user ID) so time never moves
       backwards for them.
1.15.10 **Consistent prefix reads:** causally related writes must land on the same partition, or
        they can be observed out of order.
1.15.11 The implementation of read-your-writes without leader pinning: return the write's LSN /
        version token to the client, and have the replica wait for or reject below that token.
        `[BUILD]` `[RESEARCH]`
1.15.12 Failover detection is a **timeout**, therefore a false-positive/latency trade-off:
        aggressive timeouts cause spurious failovers, generous ones extend the outage. `[PROVE]`
1.15.13 **Split brain:** the old leader may not know it was demoted. You need fencing — a
        monotonically increasing epoch/term that storage rejects writes below — or STONITH.
        `[PROVE]`
1.15.14 Unreplicated writes on the old leader are **lost or must be discarded**; with async
        replication there is no third option. `[TRAP]`
1.15.15 Automatic vs manual failover, and why several mature operators choose manual: an automatic
        failover under a grey failure (§3.11) can be worse than the fault. `[RESEARCH]`
1.15.16 Replica lag as an SLI: measure it in seconds *and* in bytes, alert on it, and know what
        user-visible symptom it produces. `[X-REF 20]`
1.15.17 Chained/cascading replication and read-replica farms: each hop adds lag; a replica of a
        replica is two lag windows.
1.15.18 Backups are not replication: replication propagates your `DELETE FROM` in milliseconds.
        Point-in-time recovery and a *tested* restore are separate requirements. `[TRAP]`

*(18 leaves)*

## §1.16 Partitioning, consistent hashing, hot keys

1.16.1 Sharding is what you do when one node can no longer hold the data or absorb the writes —
       and only then.
1.16.2 **Range partitioning:** key ranges per shard. Weakness: skew and sequential-write hotspots
       — a timestamp key sends 100% of writes to the last shard. `[TRAP]`
1.16.3 **Hash partitioning:** `hash(key) mod N`. Weakness: range scans impossible, and **changing
       N remaps almost every key**. `[PROVE]`
1.16.4 **Consistent hashing:** key and nodes on a ring, key → next node clockwise. Only ~K/N keys
       move when a node joins or leaves. `[PROVE]`
1.16.5 **Directory / lookup partitioning:** an explicit key→shard table. Flexible and precise;
       the directory is a new SPOF and an extra hop.
1.16.6 Consistent hashing mechanism in full: hash nodes and keys into the same 2³²-ish space; a
       key belongs to the first node clockwise; adding a node steals only the arc between it and
       its predecessor. `[PROVE]`
1.16.7 **Virtual nodes:** each physical node placed at V ring positions (typically 100–256) to
       flatten the distribution and to spread a departing node's load across all survivors rather
       than dumping it on one neighbour. `[NUM]` `[PROVE]`
1.16.8 Virtual nodes also weight heterogeneous hardware: a bigger node gets more tokens.
1.16.9 Replica placement on the ring: the next R distinct *physical* nodes clockwise, skipping
       vnodes of the same host, and rack/AZ-aware placement so a rack loss does not take all R.
       `[RESEARCH]`
1.16.10 **Hot partitions are the dominant real failure**, and adding nodes does not fix them — a
        celebrity's key lives on exactly one partition. `[TRAP]`
1.16.11 Mitigation 1 — **cache the hot key** in front of the store; this handles most read
        hotspots outright. `[X-REF 15]`
1.16.12 Mitigation 2 — **salt the key**: write to `celebrity_id:{0..15}` at random, read by
        fanning out to all 16. Buys write throughput, costs 16× read work, so apply only to keys
        detected as hot. `[PROVE]` `[NUM]`
1.16.13 Mitigation 3 — **split by a second dimension**: partition key `(video_id, hour)` instead
        of `video_id`.
1.16.14 Mitigation 4 — **dedicate a path**: a separate cache or service tier for the top-N
        entities.
1.16.15 Detecting hot keys at all: per-key request counters sampled, a Count-Min Sketch / heavy
        hitters structure, or the store's own hot-partition metrics. Detection precedes
        mitigation. `[RESEARCH]`
1.16.16 **Cross-shard operations are the tax**, and you must price them: a query without the
        partition key becomes a scatter-gather whose latency is the *slowest* shard's, and a
        cross-shard transaction needs 2PC (blocking, coordinator risk) or a saga (compensations,
        no isolation). `[X-REF 14]`
1.16.17 Fan-out tail arithmetic: p99 of a 10-shard scatter-gather ≈ the p99.9 of one shard;
        with 100 shards the p99 of the request is roughly the p99.99 of a shard. `[PROVE]` `[NUM]`
1.16.18 **Resharding** is the operationally hardest thing here. The workable pattern: choose a
        large fixed number of **logical** partitions up front (e.g. 1,024) and map many onto each
        physical node, so growth is "move logical partitions", with no rehashing and no key
        migration logic.
1.16.19 Real systems that work this way: Kafka partitions, Elasticsearch shards, Vitess keyspaces,
        Citus shards, Riak/Cassandra vnodes. `[RESEARCH]`
1.16.20 The cost of over-partitioning: per-partition metadata, per-partition connections, more
        files/segments, and a scatter-gather that touches 1,024 things. Pick the number with the
        five-year size in mind. `[PROVE]`
1.16.21 Rebalancing mechanics: copy-then-cutover per partition, double-read/double-write during
        the move, and a routing layer that can point at either side. `[X-REF §2.19]`
1.16.22 Partitioning the *compute* as well as the data: consistent hashing for cache affinity,
        session affinity for stateful gateways, and partitioned consumers in a stream processor.
1.16.23 **Trap:** conflating a shard (a partition of data) with a replica (a copy of a partition).
        A design needs both numbers: P partitions × R replicas. `[TRAP]` `[NUM]`

*(23 leaves)*

## §1.17 CAP, PACELC, and consistency models

1.17.1 **CAP stated precisely:** when a network **partition** occurs, a system must choose between
       remaining **available** (serving possibly-stale or conflicting data) and remaining
       **consistent** (refusing requests on the side that cannot reach a quorum).
1.17.2 CAP says nothing about the no-partition case. `[TRAP]`
1.17.3 **"CA" is not a deployment option** — partitions are not optional. `[TRAP]` `[SOURCE]`
1.17.4 The formal statement (Gilbert–Lynch): the impossibility is about *every* node being
       consistent and available, not any node; and the "C" in CAP is specifically
       **linearizability**, not the "C" of ACID. `[PROVE]` `[SOURCE]` `[RESEARCH]`
1.17.5 Brewer's own 12-years-later correction: all three properties are continuous, not binary,
       and the useful design question is what you do *during* a partition and how you recover
       afterwards. `[SOURCE]` `[RESEARCH]`
1.17.6 **PACELC is the more useful formulation:** if **P**artitioned, choose **A** or **C**;
       **E**lse, choose **L**atency or **C**onsistency. It captures the everyday cost CAP omits —
       a synchronous quorum write pays latency on every request, partition or not. `[SOURCE]`
1.17.7 The PACELC classification table: DynamoDB default reads PA/EL; Cassandra tunable, typically
       PA/EL; Postgres single primary PC/EC; Spanner/etcd/ZooKeeper PC/EC. `[RESEARCH]`
1.17.8 Consistency models, strongest to weakest, each with its cost: linearizable (consensus round
       trip per op; unavailable in a minority partition), sequential/serializable (coordination;
       contention aborts), causal (version vectors; no global coordination), read-your-writes /
       monotonic (session pinning or log positions), eventual (the application tolerates stale and
       conflicting reads).
1.17.9 Linearizability vs serializability, precisely: linearizability is a **recency** guarantee
       on single objects; serializability is an **isolation** guarantee on transactions; strict
       serializability is both. Most candidates conflate them. `[PROVE]` `[TRAP]`
1.17.10 Causal consistency as the strongest model achievable with full availability under
        partition — the theoretical result worth knowing by name. `[RESEARCH]`
1.17.11 Session guarantees as the practically useful middle: read-your-writes, monotonic reads,
        monotonic writes, writes-follow-reads. These are cheap and they fix most user-visible
        anomalies. `[RESEARCH]`
1.17.12 **Choose per operation, not per system.** One design routinely mixes linearizable for
        "reserve the last seat" and "debit the account", causal for messaging, eventual for view
        counts and follower totals. `[SAY]`
1.17.13 **Trap:** calling eventual consistency "usually a few milliseconds so it doesn't matter".
        State the *window* and the *user-visible symptom*: "replication lag is p99 200 ms, so a
        user could refresh and not see their own comment — I handle that with read-your-writes
        routing." `[TRAP]` `[SAY]`
1.17.14 **Trap:** "we chose AP" as a whole-system statement. Availability and consistency are
        per-operation properties in every real system that has both a shopping cart and a payment.
        `[TRAP]`
1.17.15 What "eventually" means operationally: the convergence mechanism must exist (read repair,
        anti-entropy, re-delivery). Without one, "eventual" is "never" for unread keys (§1.18).
        `[PROVE]`

*(15 leaves)*

## §1.18 Quorums and the R + W > N arithmetic

1.18.1 The setup: N replicas, a write goes to W of them, a read to R of them.
1.18.2 **If R + W > N the read and write sets must overlap in at least one node**, so a read sees
       at least one copy of the latest write — *provided* it can identify the newest of the values
       it gets back, via a version or timestamp. Work the pigeonhole argument. `[PROVE]`
1.18.3 The configuration table: N=3,W=2,R=2 (standard; tolerates one node down for both);
       N=3,W=3,R=1 (fast reads, no write availability if any node is down); N=3,W=1,R=1 (fastest,
       eventual only, R+W=2 ≤ 3); N=3,W=1,R=3 (fast writes, slow reads, quorum satisfied). `[NUM]`
1.18.4 Latency consequence: W and R are **tail-latency multipliers** — waiting for 2 of 3 means
       waiting for the second-slowest of three, so quorum latency tracks a higher percentile of
       node latency than a single read. `[PROVE]`
1.18.5 **Read repair:** a read that observes divergent versions writes the newest value back.
1.18.6 **Anti-entropy:** a background Merkle-tree comparison between replicas, for keys nobody
       reads. Skip both and rarely-read keys never converge. `[PROVE]` `[SOURCE]`
1.18.7 **Hinted handoff:** when a replica is down, a substitute node accepts the write with a hint
       and forwards it on recovery. `[SOURCE]`
1.18.8 **Sloppy quorum:** the W nodes are the first W *healthy* nodes on the preference list, not
       necessarily the W home replicas — which is what makes hinted handoff possible. `[SOURCE]`
1.18.9 **Trap:** "quorum reads give strong consistency." A sloppy quorum lets a write land outside
       the intended replica set, breaking the overlap argument; even a strict quorum without
       consensus permits stale reads under concurrent writes and node failures. Quorum gives a
       strong *probability*, not linearizability. `[TRAP]` `[PROVE]`
1.18.10 Linearizability needs **consensus** (Raft/Paxos), which is a different and more expensive
        machine (§3.3). `[SAY]`
1.18.11 Conflict resolution 1 — **last-write-wins on wall clocks**: the default, and it silently
        discards data under clock skew. Acceptable for a cache entry, not for a shopping cart.
        `[TRAP]`
1.18.12 Conflict resolution 2 — **version vectors** with an application-level merge (union the
        cart), which surfaces conflicts instead of losing them.
1.18.13 Conflict resolution 3 — **CRDTs**: counters, sets and registers whose merge is provably
        commutative, associative and idempotent (§3.5).
1.18.14 Tunable consistency in practice: Cassandra's ONE / QUORUM / LOCAL_QUORUM / EACH_QUORUM /
        ALL, and why LOCAL_QUORUM is the multi-DC default. `[RESEARCH]` `[CURRENCY]`
1.18.15 DynamoDB's two read modes (eventually consistent, strongly consistent) and their cost
        ratio, as the managed-service version of the same dial. `[RESEARCH]` `[CURRENCY]`
1.18.16 Quorum with an even N, and why odd N is conventional: N=4, W=3, R=2 works but wastes a
        replica relative to N=3 for the same fault tolerance. `[PROVE]` `[NUM]`
1.18.17 Witness/tiebreaker replicas: a node that participates in the quorum without holding full
        data, used to get odd-numbered voting across two data centres. `[RESEARCH]`

*(17 leaves)*

## §1.19 Caching in a design

1.19.1 The tier table with latency, what each buys, and what each costs: client/browser (0 ms,
       zero network, no invalidation control); CDN/edge (10–50 ms, bandwidth + geography + origin
       offload, only for cacheable mostly-public responses); API gateway / reverse proxy (~1 ms,
       whole-response reuse, coarse keys); in-process Caffeine (~100 ns, absorbs hot keys
       entirely, N copies of the staleness problem); distributed Redis (~0.5 ms, shared and
       survives restarts, one network hop and a new dependency); DB buffer pool (~1 ms, free, not
       yours to control). `[NUM]` `[X-REF 15]`
1.19.2 **A cache you cannot survive losing is an undocumented critical dependency.** Compute the
       0%-hit-ratio load: at a 99% hit ratio the DB is sized for 1% of read traffic, so a flush
       hands it **100×** its capacity. `[PROVE]` `[NUM]` `[SAY]`
1.19.3 The three defences that follow: rate-limit or circuit-break the origin, warm behind a
       failing readiness probe, and prefer serve-stale-on-error over fail. `[X-REF 15]`
1.19.4 Hit-ratio non-linearity: going from 90% to 99% cuts origin load by 10×, and from 99% to
       99.9% by another 10× — origin load is (1 − h), so the *last* nine is worth as much as all
       the previous ones. `[PROVE]` `[NUM]`
1.19.5 **Every input that changes the output belongs in the key** — tenant, user, role, locale,
       schema version, filter set. Omitting the user is how one user's data is served to another.
       `[TRAP]`
1.19.6 Cache-aside as the design default, and the two writes-side alternatives (write-through,
       write-behind) with the durability question write-behind raises. `[X-REF 15]`
1.19.7 Invalidation strategies at design level: TTL-only (simple, bounded staleness), explicit
       delete on write (race-prone), versioned keys / key namespacing (no invalidation needed),
       and change-stream-driven invalidation. `[X-REF 15]`
1.19.8 Stampede/thundering herd on expiry, and the three fixes: request coalescing (single-flight),
       probabilistic early refresh, and a lock-plus-serve-stale. `[X-REF 15]` `[BUILD]`
1.19.9 Negative caching for "not found" so a scan for a nonexistent key does not hit the origin
       every time — and its cost, which is delayed visibility of newly created objects.
1.19.10 Cache warming and readiness gating as a deploy-time concern: an instance that joins the LB
        with a cold cache is a latency incident, and if the fleet rolls fast enough it is an
        outage. `[X-REF 19]`
1.19.11 The cache as a capacity *decision*, priced: memory is roughly 100× the cost per byte of
        SSD, so "cache everything" is a budget statement. `[NUM]` `[CURRENCY]`
1.19.12 What must **never** be cached: authorization decisions with a long TTL, anything whose
        staleness has a money or safety consequence, and per-request secrets.

*(12 leaves)*

## §1.20 Asynchrony: what leaves the request path

1.20.1 The single test: **does the user need the result to continue?** If not, it leaves the
       request path. `[SAY]`
1.20.2 The standard list of work that goes async: notifications, emails, image/video transcoding,
       search indexing, analytics, feed materialisation, webhook delivery, third-party sync,
       anything fan-out shaped.
1.20.3 What stays synchronous: anything the response body must contain, and anything whose failure
       must be reported to the user as a failure.
1.20.4 What asynchrony buys: lower and more stable p99, load levelling (the queue absorbs spikes),
       independent scaling and failure isolation of the consumer, retries without the user
       waiting.
1.20.5 What it costs: the user sees an intermediate state (so you need a status or notification
       mechanism), queue depth becomes an SLO and a monitoring surface, at-least-once delivery
       forces idempotent consumers, ordering is only per-partition, and DLQs need an owner and a
       replay path. `[X-REF 14]`
1.20.6 **Queue vs log:** a queue (SQS, RabbitMQ) gives competing consumers, per-message ack and
       easy retry — right for work distribution. A log (Kafka) gives retention, replay and
       multiple independent consumer groups over one stream — right when several systems need the
       same events, or when you will want to rebuild a read model. `[X-REF 14]`
1.20.7 The clearest signal for a log: "several consumers need this event". The clearest signal for
       a queue: "one worker should do this once". `[SAY]`
1.20.8 **Backpressure is a design decision, not an accident.** Bound the queue and reject
       producers (load shedding), drop by priority, or grow unboundedly and convert a throughput
       problem into an out-of-memory outage. Pick explicitly and say which. `[SAY]` `[X-REF 14]`
1.20.9 Queue depth as a leading indicator, and consumer lag as the number you alert on. The
       derived quantity that matters is **time-to-drain**, not depth. `[PROVE]` `[X-REF 20]`
1.20.10 Sync-over-async anti-pattern: publishing an event and then polling for the result inside
        the request, which keeps every cost of asynchrony and gives up its benefit. `[TRAP]`
1.20.11 The status-model requirement: async work needs a user-visible state machine (`PENDING`,
        `PROCESSING`, `DONE`, `FAILED`) with a terminal state and a way to observe it.
1.20.12 Priority and fairness across tenants inside one queue: separate queues per class, weighted
        consumption, or sidelining excess traffic from one noisy tenant to a slow lane.
        `[RESEARCH]`
1.20.13 Scheduled and delayed work: delay queues, visibility timeouts, and hierarchical timing
        wheels as the in-process structure that makes millions of timers cheap. `[RESEARCH]`
        `[BUILD]`
1.20.14 The event-schema question that bites later: event carries **state** (fat event, no
        callback, but stale by design) vs event carries **id only** (thin event, forces a callback
        to the source of truth, and that callback is a new synchronous dependency). `[X-REF 14]`
1.20.15 Choreography vs orchestration for multi-service flows, and why orchestration (an explicit
        coordinator) is easier to debug at the cost of a central component. `[X-REF 14]`

*(15 leaves)*

## §1.21 Idempotency, duplicates, and "exactly once"

1.21.1 Every network call has three outcomes: success, failure, and **unknown** (timeout). The
       unknown case forces retries, retries cause duplicates, and duplicates are the most common
       correctness bug in a distributed design. `[PROVE]`
1.21.2 Exactly-once **delivery** is impossible; exactly-once **effect** is achievable and is what
       you should claim. `[SAY]` `[TRAP]`
1.21.3 Mechanism 1 — **idempotency key**, client-supplied, for user-facing writes: server stores
       `key → (state, response)` and replays the stored response on a repeat.
1.21.4 The key row must be inserted in the **same transaction** as the effect, so a crash between
       them cannot lose the record. `[PROVE]`
1.21.5 **Trap:** `findById` then `save` is a check-then-act race under two concurrent requests with
       the same key. Insert the key **first** under a unique constraint and treat the violation as
       "in flight or done" — that makes the database the arbiter instead of the application.
       `[TRAP]` `[BUILD]`
1.21.6 The three states an idempotency record needs: `IN_PROGRESS`, `COMPLETED` (with the stored
       response), `FAILED`; plus a lease/expiry so a crashed in-progress record does not block the
       key forever. `[BUILD]`
1.21.7 Idempotency-key scope and TTL: scoped per (endpoint, tenant, key), TTL 24h–7d, and the
       request fingerprint stored so the same key with a *different* body is rejected as a client
       error rather than silently replaying. `[RESEARCH]` `[X-REF 12]`
1.21.8 Mechanism 2 — **natural dedupe key**, server-side, for consumers: insert
       `(consumer_group, message_id)` into a uniquely-indexed table and let the constraint
       violation mean "already processed".
1.21.9 Mechanism 3 — **idempotent by construction**: `SET balance = 100` is idempotent,
       `balance = balance + 10` is not. Expressing the operation as a set or a version-keyed
       upsert removes the problem instead of managing it. `[SAY]`
1.21.10 Conditional writes as the fourth mechanism: compare-and-set on a version column /
        `If-Match` ETag / DynamoDB condition expression — the write itself becomes the dedupe.
        `[X-REF 12]`
1.21.11 Dedupe-window sizing: a dedupe table is unbounded unless you bound it. Sizing = duplicate
        arrival window (retry horizon + broker retention) × rate, and the eviction policy must be
        stated. `[PROVE]` `[NUM]`
1.21.12 **The dual-write problem:** writing to the database and publishing to Kafka are two systems
        with no shared transaction; a crash between them leaves them permanently disagreeing.
        `[PROVE]`
1.21.13 **The transactional outbox:** write the event into an `outbox` table in the same
        transaction as the state change, and have a separate relay publish it. This converts an
        atomicity problem into an at-least-once delivery problem, which idempotent consumers
        already handle. `[X-REF 14]`
1.21.14 Two relay implementations: a **poller** (simple, adds latency, needs `SKIP LOCKED` and a
        claim column) and **CDC from the WAL** (Debezium; lower latency, no polling load, a new
        operational component). `[BUILD]` `[X-REF 14]`
1.21.15 The inbox pattern as the consumer-side mirror of the outbox.
1.21.16 Kafka's transactional/exactly-once-semantics support and its precise scope: exactly-once
        *within* a Kafka read-process-write cycle, not across an arbitrary external side effect.
        `[TRAP]` `[X-REF 14]` `[RESEARCH]`
1.21.17 Ordering and duplicates interact: a retry can reorder as well as duplicate, so a consumer
        may need a version/sequence check ("ignore anything older than what I have") in addition
        to a dedupe key. `[PROVE]`
1.21.18 The external-gateway case, where the unknown outcome is unavoidable: never blind-retry a
        charge; query the provider's status endpoint by your idempotency key, and reconcile
        against their settlement report on a schedule (§5.3 ledger).

*(18 leaves)*

## §1.22 Unique ID generation

1.22.1 Why it is a real design decision: the ID scheme constrains sharding, sorting, index
       locality, and information leakage.
1.22.2 The scheme table: DB auto-increment (8 B, sortable, single writer); UUIDv4 (16 B, **not**
       sortable, no coordination); UUIDv7/ULID (16 B, time-prefixed sortable, no coordination);
       Snowflake (8 B, sortable, needs node-ID assignment); ticket server / range allocation
       (8 B, sortable, central but batched). `[NUM]`
1.22.3 UUIDv4's cost: random ⇒ index write amplification, because every insert hits a random
       B-tree leaf. `[PROVE]` `[X-REF 09]`
1.22.4 **Trap:** UUIDv4 as a clustered primary key in MySQL/InnoDB. Random keys destroy the
       buffer-pool locality sequential inserts get; the result is page splits, write amplification
       and an index much larger than necessary. Use UUIDv7/ULID, or keep an internal sequential PK
       with the UUID as the external identifier. `[TRAP]`
1.22.5 UUIDv7 as the modern default: 48-bit Unix-millisecond prefix + version/variant bits +
       random tail, giving uncoordinated *and* sortable. `[RESEARCH]` `[SOURCE]` `[CURRENCY]`
1.22.6 ULID as the pre-standard equivalent: 48-bit timestamp + 80 bits of randomness, Crockford
       base32, 26 characters. `[NUM]` `[RESEARCH]`
1.22.7 **Snowflake arithmetic:** 41 bits of milliseconds ≈ 69 years from a custom epoch; 10 bits ⇒
       1,024 workers; 12 bits ⇒ 4,096 IDs per worker per millisecond ⇒ ~4 M IDs/s per worker.
       Work the 2⁴¹ ms → years conversion explicitly. `[PROVE]` `[NUM]`
1.22.8 Snowflake's two weaknesses: node-ID assignment (needs ZooKeeper, etcd or a config plane)
       and **clock skew** — a backwards NTP step can produce duplicate IDs, so the generator must
       refuse to move backwards. `[BUILD]`
1.22.9 The three legal responses to clock regression: block until the clock catches up, borrow
       from the sequence bits, or fail loudly. State which you chose. `[BUILD]`
1.22.10 Ticket server / range allocation: hand out blocks of 10⁴–10⁶ counter values so the hot path
        is coordination-free; the allocator is a SPOF unless replicated, and gaps appear when a
        holder dies. `[BUILD]`
1.22.11 Sortable IDs as a *feature*: `WHERE id > :cursor` becomes a valid pagination cursor, and
        an ID range becomes a time range for backfills.
1.22.12 Information leakage: sequential IDs let a competitor measure your growth rate (the German
        tank problem) and let an attacker enumerate objects; the fix is an opaque external ID or
        a bijective scramble of the internal one. `[X-REF 13]`
1.22.13 Short human-facing IDs: base62 / base58 encoding, alphabet choice (excluding lookalike
        characters), and length sizing from the required key space (§5.3 shortener). `[PROVE]`
1.22.14 IDs and sharding: an ID that embeds the shard (or from which the shard is derivable)
        avoids a lookup on every read; an ID that does not means a directory. `[PROVE]`
1.22.15 Composite/hierarchical IDs (`tenant:entity:seq`) as the multi-tenant version, and their
        effect on partition keys.

*(15 leaves)*

## §1.23 Rate limiting and admission control

1.23.1 The three purposes: protect capacity, enforce fairness between tenants, and price the API.
       Different purposes imply different keys and different responses. `[X-REF 12]`
1.23.2 **Fixed window:** one counter per (key, minute). Admits **2× the limit** across a window
       boundary. `[PROVE]` `[TRAP]`
1.23.3 **Sliding window log:** a sorted set of timestamps, trimmed. Exact, at O(limit) memory per
       key. `[NUM]`
1.23.4 **Sliding window counter:** a weighted blend of the current and previous window. Good
       approximation for two counters; work the weighting formula. `[PROVE]` `[BUILD]`
1.23.5 **Token bucket:** tokens refill at rate R up to capacity B; allows a burst of B then steady
       R. Two numbers per key (`tokens`, `lastRefillMicros`), computed lazily on access. `[BUILD]`
1.23.6 **Leaky bucket:** a queue draining at a fixed rate; smooths completely, adds queueing delay.
1.23.7 **Token bucket is the usual right answer** because it matches how traffic really is —
       bursty but bounded on average — and it is the cheapest to store. `[SAY]`
1.23.8 Distributed enforcement: counters in Redis with an **atomic** check-and-decrement via a Lua
       script; a `GET` then `SET` from N instances leaks the limit. `[BUILD]` `[TRAP]`
1.23.9 Per-instance local limits at `limit / instanceCount`: cheaper, but wrong under uneven load
       balancing and during autoscaling. The hybrid (local bucket refilled from a global
       allocator) is the production compromise. `[PROVE]`
1.23.10 The response contract: **429** with `Retry-After`, plus `X-RateLimit-Limit`,
        `X-RateLimit-Remaining`, `X-RateLimit-Reset`. `[X-REF 12]` `[RESEARCH]`
1.23.11 Key choice, in order of preference: API key > user ID > IP. IP punishes users behind NAT
        and is trivially rotated. `[TRAP]`
1.23.12 Layered limits: per-key, per-tenant, per-endpoint, and a global ceiling — with the global
        one existing to protect the *system*, not the customer.
1.23.13 Fail **open or closed** by explicit decision when the limiter's store is down; say which
        and why. A limiter that fails closed is a new SPOF; one that fails open is a capacity
        risk during exactly the incident where you need it. `[SAY]` `[TRAP]`
1.23.14 Quotas vs rate limits: quotas are billing-period budgets (monthly), rate limits are
        instantaneous. Different storage, different enforcement point.
1.23.15 **Load shedding is the sibling mechanism and the one that saves you in an incident:** when
        concurrency or queue depth passes a threshold, reject cheap-to-reject requests immediately
        by priority. A fast 503 preserves capacity; queueing everything converts overload into
        total collapse, because by the time you serve a request the client has already timed out
        and retried. `[PROVE]` `[SAY]`
1.23.16 Priority classes for shedding, from the SRE literature: CRITICAL_PLUS / CRITICAL /
        SHEDDABLE_PLUS / SHEDDABLE, with health checks and paying customers above batch and
        analytics. `[SOURCE]` `[RESEARCH]`
1.23.17 Where the shed signal comes from: CPU rate, executor load average, queue depth, or
        in-flight concurrency — measured locally, because a central limiter cannot react fast
        enough. `[SOURCE]` `[RESEARCH]`
1.23.18 Concurrency limiting (bounded in-flight requests) as often better than rate limiting for
        protecting a service, because it adapts automatically to work that got more expensive.
        `[PROVE]`
1.23.19 Client-side adaptive throttling as the complement: a client that rejects its own requests
        locally when `requests ≥ K × accepts` (K typically 2), so an overloaded server is not even
        asked. `[SOURCE]` `[NUM]` `[RESEARCH]`

*(19 leaves)*

## §1.24 Load balancing and request routing

1.24.1 The layer table: **DNS** (sees hostname; geo/region routing and coarse weighting; TTL
       caching means minutes to shift traffic); **L4/NLB** (sees IP/port; very high throughput,
       TCP and TLS passthrough; no path or header awareness); **L7/ALB/Envoy/nginx** (sees HTTP;
       path and header routing, retries, TLS termination, circuit breaking; more CPU and another
       hop). `[X-REF 10]`
1.24.2 Algorithms: round-robin (default), least-connections (better with variable request cost),
       least-outstanding-requests / EWMA (best when backends are heterogeneous or one is
       degrading), consistent hashing (cache affinity or sticky stateful connections),
       power-of-two-random-choices (near-optimal with O(1) state — the one candidates never
       name). `[RESEARCH]`
1.24.3 Why round-robin is actively bad when one backend is degraded: it keeps sending an equal
       share to the slowest node, so the slow node collects the queue. Least-outstanding-requests
       fixes this automatically. `[PROVE]` `[TRAP]`
1.24.4 **Health checks decide whether the LB helps or hurts.** Shallow checks keep traffic on a
       broken instance whose DB connection is gone; deep checks that test dependencies cause
       **correlated removal** — a slow database fails every instance's check and the LB removes
       the entire fleet. `[PROVE]` `[TRAP]`
1.24.5 The practical answer: liveness shallow, readiness moderate, and never remove more than a
       configured fraction of the fleet at once. `[X-REF 19]`
1.24.6 **Envoy's panic threshold** as the canonical implementation of that rule: when fewer than
       50% of hosts are healthy (`healthy_panic_threshold`, default 50), Envoy ignores health
       status and load-balances across all hosts, on the theory that a degraded service beats no
       service. `[SOURCE]` `[NUM]` `[RESEARCH]`
1.24.7 **Outlier detection** (passive health checking) as distinct from active health checks:
       eject a host after `consecutive_5xx` or a success-rate deviation, for a base ejection time
       that grows with repeat offences, capped by `max_ejection_percent`. `[SOURCE]` `[RESEARCH]`
1.24.8 Client-side load balancing (the mesh/gRPC model) vs a middle proxy: removes a hop and a
       component, at the cost of putting policy in every client and needing service discovery.
1.24.9 Service discovery options and their propagation delay: DNS (TTL-bound), a registry
       (Consul/Eureka), Kubernetes Services/EndpointSlices, or the mesh control plane.
       `[X-REF 19]` `[RESEARCH]`
1.24.10 Connection-level vs request-level balancing, and why HTTP/2 and gRPC break L4 balancing:
        one long-lived connection carries all requests, so an L4 LB pins a client to one backend
        forever. `[PROVE]` `[TRAP]` `[X-REF 10]`
1.24.11 Global traffic management: DNS-based geo routing, anycast, and the reason DNS is a poor
        failover mechanism (resolver TTL disrespect measured in minutes to hours). `[TRAP]`
        `[X-REF 10]`
1.24.12 Zone/AZ-aware routing: keep traffic in-zone for latency and cross-AZ data-transfer cost,
        with a spillover rule when in-zone capacity is insufficient. `[NUM]` `[X-REF 18]`
1.24.13 Draining and deregistration: connection draining timeout, `preStop` hooks, and the
        deregistration delay that must exceed the longest in-flight request. `[X-REF 19]`
1.24.14 **Statelessness again:** sticky sessions make deploys and autoscaling drop user state and
        cause persistent imbalance. Externalise the session and let any instance serve any
        request.
1.24.15 The LB itself as a SPOF and a capacity limit: it needs redundancy, and its connection and
        throughput ceilings are numbers in your capacity model. `[NUM]`

*(15 leaves)*

## §1.25 Resilience patterns

1.25.1 The framing: the failure of one dependency must not become the failure of your service.
       Six mechanisms, each preventing a specific failure.
1.25.2 **Timeouts on every network call, always.** A missing timeout is how one slow dependency
       exhausts your thread pool and takes down endpoints that do not even use it. `[PROVE]`
       `[TRAP]`
1.25.3 Setting the value: from the dependency's measured p99 (with headroom), not by guess. A
       timeout below the dependency's normal p99 turns a healthy system into a failing one.
       `[PROVE]`
1.25.4 The timeout taxonomy people collapse: connect timeout, TLS handshake timeout, socket/read
       timeout, total request timeout, and pool-acquisition timeout. Java's defaults for several
       of these are *infinite*. `[TRAP]` `[X-REF 10]`
1.25.5 **Deadline propagation:** the caller's remaining budget travels down the call chain, and
       each hop's timeout is shorter than what it inherited. Without it, a service does work
       nobody is waiting for. `[SOURCE]` `[BUILD]` `[RESEARCH]`
1.25.6 **Retries with exponential backoff and full jitter:**
       `sleep = random(0, min(cap, base·2^n))`. Without jitter, all clients retry in synchronised
       waves and you get a self-inflicted DDoS. `[PROVE]` `[SOURCE]` `[BUILD]`
1.25.7 The jitter variants and why full jitter usually wins: no jitter / equal jitter / full
       jitter / decorrelated jitter, compared on total work and completion time. `[RESEARCH]`
       `[NUM]`
1.25.8 **Only retry idempotent operations**, cap attempts at 2–3, and never retry a 4xx (except
       429 and 408). `[TRAP]`
1.25.9 **Retry amplification:** 3 retries at each of 3 layers is 27 requests for one user action.
       Retry at **one** layer — usually the outermost that can still act on the result. `[PROVE]`
       `[NUM]`
1.25.10 **Retry budget:** cap retries at a fraction of successful requests (10% is the published
        convention) so retrying is self-limiting under a broad failure. `[SOURCE]` `[NUM]`
        `[BUILD]` `[RESEARCH]`
1.25.11 **Circuit breaker:** track the failure rate over a rolling window; at a threshold, open and
        fail fast for a cooldown; then half-open and let a limited number of probes through. This
        stops you spending your own capacity on calls that will fail and gives the downstream room
        to recover. `[BUILD]`
1.25.12 Circuit-breaker parameters that must be named: window type (count-based vs time-based),
        window size, failure-rate threshold, slow-call-rate threshold, minimum number of calls,
        wait duration in open state, permitted calls in half-open. `[SOURCE]` `[RESEARCH]`
1.25.13 The breaker's own failure mode: a threshold low enough to trip on normal error rates turns
        a partial degradation into a total one, and a shared breaker across tenants lets one
        tenant's bad input open the circuit for everyone. `[TRAP]`
1.25.14 **Bulkheads:** separate connection/thread pools (or semaphores) per dependency, so a
        saturated one cannot consume all your capacity. Watertight compartments.
1.25.15 **Graceful degradation** decided in advance, per feature: recommendations fall back to
        "most popular", personalised feed to chronological, a missing avatar to a placeholder.
        Saying this out loud is a scoring signal. `[SAY]`
1.25.16 Fallbacks are dangerous when they are *another network call*: the fallback path is
        untested, correlated with the failure, and doubles load at the worst moment. Prefer a
        static or local fallback. `[SOURCE]` `[TRAP]` `[RESEARCH]`
1.25.17 Hedged requests as the tail-latency tool: issue a second request after the p95 has
        elapsed, take the first response, and accept ~5% extra load. `[SOURCE]` `[NUM]`
        `[RESEARCH]`
1.25.18 Tied requests: enqueue on two servers, tell each about the other, and cancel on first
        pickup — measured at 16% median and 40% p99.9 improvement in the source system.
        `[SOURCE]` `[NUM]` `[RESEARCH]`
1.25.19 Idempotency is the precondition for all of retries, hedging and tied requests (§1.21).
1.25.20 **Trap:** describing retries without mentioning idempotency or jitter. It reads as having
        heard of resilience rather than having operated it. `[TRAP]`
1.25.21 The complete per-dependency checklist to recite: timeout, retry policy + budget, breaker,
        bulkhead, fallback, and the metric that tells you it is happening. `[SAY]`

*(21 leaves)*

## §1.26 Multi-region

1.26.1 Multi-region is expensive and adds a class of bug you cannot avoid. Justify it with exactly
       one of three reasons: **latency** (users far from one region), **regulatory data
       residency**, or **regional disaster tolerance**. `[SAY]`
1.26.2 If none applies, multi-AZ within one region gets you 99.99% and is far simpler.
1.26.3 The topology table: active–passive async (one writer; RPO = lag in seconds, RTO = failover
       in minutes; low difficulty); active–active partitioned by key/cells (each region owns a key
       range; RPO ≈ 0 for owned keys; needs home-region routing); active–active fully replicated
       (conflicts guaranteed; LWW, CRDTs or app-level merge); synchronous consensus across regions
       (RPO = 0; every write pays cross-region RTT).
1.26.4 **Cell / partition-by-key is the pattern that actually works** for consumer systems: each
       user has a home region, writes are served there, replication is async for read locality and
       DR. Conflicts disappear because only one region writes a given key. The cost is a routing
       layer and a user-migration procedure. `[SAY]`
1.26.5 The numbers you must respect: cross-region RTT 80–150 ms, so **one synchronous cross-region
       hop blows a 100-ms p99 budget by itself**. `[PROVE]` `[NUM]`
1.26.6 Cross-region data transfer is often the largest surprise line on the bill; price it.
       `[NUM]` `[CURRENCY]` `[X-REF 18]`
1.26.7 **RPO and RTO stated as numbers**, and the fact that an unrehearsed failover is a
       hypothesis, not a capability. `[SAY]`
1.26.8 What must be in the failover runbook: DNS/traffic shift mechanism and its propagation time,
       data promotion, the fencing step, the "how do we know it worked" check, and the failback
       plan.
1.26.9 Failback is harder than failover, because the old primary has diverged and must be rebuilt
       or reconciled. `[TRAP]`
1.26.10 Read-local/write-global as the cheapest useful topology: replicas everywhere, a single
        write region, and an explicit "writes are slow for distant users" acceptance. `[PROVE]`
1.26.11 Cross-region messaging: mirrored topics, per-region ownership of consumer groups, and the
        duplicate/ordering consequences. `[X-REF 14]`
1.26.12 Data residency implementation: region-pinned storage, a routing layer that enforces it, and
        the awkward parts (global search indexes, analytics, backups). `[X-REF 13]`
1.26.13 The 2026-era managed primitives that change this conversation, all `[CURRENCY]`:
        DynamoDB global tables with multi-Region strong consistency (announced re:Invent 2024, GA
        2025; requires exactly three Regions — three replicas or two replicas plus a witness —
        within a single Region set), and Aurora DSQL (serverless distributed SQL with a stated
        99.999% multi-Region availability target). `[RESEARCH]` `[CURRENCY]`
1.26.14 Spanner-class synchronous consensus across regions as the "RPO=0 anywhere" option, and its
        price: every commit pays a cross-region quorum plus commit-wait (§3.4). `[RESEARCH]`
1.26.15 **Trap:** "multi-region for availability" without noticing that the dependency list did not
        also go multi-region. A single-region auth service makes the whole thing single-region.
        `[TRAP]` `[PROVE]`
1.26.16 Active-active also multiplies your *config* blast radius: a bad config or a bad deploy
        propagates to both regions in seconds, which is why staggered regional deploys exist.
        `[PROVE]` `[X-REF 20]`

*(16 leaves)*

## §1.27 Read models, CQRS, and search

1.27.1 The problem: one write model cannot serve every read shape, and contorting the schema to
       try makes both worse.
1.27.2 **The pattern:** writes go to the source of truth; a change stream (CDC from the WAL, or
       outbox events) feeds one or more purpose-built read models — Elasticsearch for text search,
       a columnar store for analytics, a denormalised `feed` table for timelines, Redis for
       counters.
1.27.3 The read model is **eventually consistent** with the source of truth. Name the lag budget
       and the user-visible symptom ("a new post is searchable within ~2 s"). `[SAY]`
1.27.4 It is **rebuildable**, and that is the main reason to prefer a log over dual writes: to fix
       a projection bug you replay the log rather than migrate data. `[PROVE]`
1.27.5 **Elasticsearch is never the source of truth.** No transactions, reindexes are routine.
       `[TRAP]`
1.27.6 CQRS proper vs "a read replica": CQRS means separate *models*, not separate hardware; the
       cost is a second schema and a synchronisation path, so do not reach for it by default.
       `[TRAP]`
1.27.7 Event sourcing as the adjacent, heavier pattern: the log of events *is* the source of truth,
       state is a fold. What it buys (audit, temporal queries, rebuildability) and what it costs
       (schema evolution of events forever, snapshotting, a much higher floor of complexity).
       `[RESEARCH]`
1.27.8 Materialised-view maintenance strategies: full periodic rebuild, incremental apply,
       versioned index with atomic alias swap (the standard zero-downtime reindex).
1.27.9 Backfill/replay mechanics: idempotent projections, a replay marker, and the ability to run
       the new projection alongside the old (dual-projection) before switching reads.
1.27.10 **Counters** deserve a specific note because they appear in almost every design.
        Incrementing a row per view serialises on one row and destroys write throughput.
1.27.11 Counter options in order: increment in Redis and flush aggregates periodically; write an
        append-only event and aggregate asynchronously; or use approximate structures
        (HyperLogLog for unique counts) when exactness is not required. `[X-REF 15]`
1.27.12 **Ask whether the count must be exact — usually it must not.** `[SAY]`
1.27.13 Search-specific design concerns at the composition layer: index freshness vs query
        throughput, the analyzer/schema being a *migration* concern, and relevance ranking as a
        separate system from retrieval.
1.27.14 The read-model failure mode nobody plans for: the projection falls behind, and there is no
        way to tell users. Lag must be exposed as a metric and, sometimes, in the UI. `[X-REF 20]`

*(14 leaves)*

## §1.28 Blobs, uploads and delivery

1.28.1 Never route large media through your application: it burns your bandwidth, your threads and
       your memory for zero added value. `[SAY]`
1.28.2 **Upload:** the client asks your API for a **pre-signed URL** and PUTs bytes directly to
       object storage; storage emits a completion event, which triggers processing (virus scan,
       transcode, thumbnail) asynchronously. Your service handles metadata only.
1.28.3 **Multipart upload** for large files gives per-part retry instead of restarting a 5-GB
       upload, plus parallelism; it needs an abort/cleanup policy for orphaned parts. `[X-REF 18]`
1.28.4 Resumable upload protocols and the client-side state they require.
1.28.5 The metadata state machine: `PENDING` on URL issue, `UPLOADED` on the storage event,
       `PROCESSED` after the pipeline — with a reaper for rows that never advance. `[TRAP]`
1.28.6 **Delivery:** object storage behind a CDN. Content-addressed or fingerprinted URLs
       (`/assets/app.9f2c1e.js`) can be cached immutably forever, so you never purge — you publish
       a new URL. `[SAY]`
1.28.7 Signed URLs with short expiry for private media, and the trade-off between expiry length
       and CDN cacheability. `[TRAP]`
1.28.8 **Metadata in the database, bytes in object storage.** Binaries in a relational store bloat
       backups, thrash the buffer pool and make replication expensive. `[PROVE]`
1.28.9 Range requests and byte-serving as the basis of video seeking and resumable downloads.
       `[X-REF 10]`
1.28.10 Deduplication by content hash: store once, reference many, and the reference-count/GC
        problem it creates.
1.28.11 Storage classes and lifecycle rules as the cost lever: hot → infrequent → archive by age,
        with retrieval latency and minimum-duration charges as the catch. `[CURRENCY]`
        `[X-REF 18]`
1.28.12 Durability vs availability for object storage: eleven nines of durability is an
        erasure-coding claim, not an uptime claim. `[TRAP]` `[NUM]` `[RESEARCH]`
1.28.13 The CDN's role in the *write* path too: edge upload acceleration terminates TLS close to
        the user and rides the backbone. `[X-REF 10]`
1.28.14 Cache-control and invalidation strategy at the CDN: immutable + long max-age for
        fingerprinted assets, short TTL + stale-while-revalidate for HTML, purge only as an
        emergency tool. `[X-REF 15]`

*(14 leaves)*

## §1.29 Observability and capacity in a design review

1.29.1 Three things must appear in any design review: the SLI/SLO, the failure-attribution
       metrics, and the named bottleneck with its headroom. `[X-REF 20]`
1.29.2 **The SLO phrased as a ratio over a window:** "99.9% of feed reads under 300 ms over 28
       days". That definition is what makes the design falsifiable. `[SAY]`
1.29.3 The metrics that tell you which component is failing: per-dependency latency and error rate,
       queue depth and consumer lag, cache hit ratio, connection-pool saturation, replication lag.
1.29.4 These are the **leading** signals — saturation and lag move before the user-visible symptom,
       so they are what you alert on. `[PROVE]` `[X-REF 20]`
1.29.5 **Percentiles, never averages.** An average hides the tail entirely. `[SAY]`
1.29.6 With fan-out, the tail *is* the common case: a request touching 100 shards is slower than
       one shard's p99 almost always. `[PROVE]` `[NUM]`
1.29.7 Client-observed latency includes queueing your server-side timer never saw — the reason
       server p99 and client p99 disagree during an incident. `[PROVE]`
1.29.8 **Percentiles do not average and do not add.** You cannot average p99s across instances or
       across time buckets; you need histograms/quantile sketches. `[PROVE]` `[TRAP]`
       `[RESEARCH]`
1.29.9 **Coordinated omission:** a closed-loop load generator stops issuing requests while the
       system stalls, silently deleting the worst samples before any percentile is computed, so
       the reported p99 is fiction. `[SOURCE]` `[PROVE]` `[TRAP]` `[RESEARCH]`
1.29.10 The fixes: constant-arrival-rate load generation, or HdrHistogram's
        `recordValueWithExpectedInterval` correction. `[SOURCE]` `[RESEARCH]`
1.29.11 The four golden signals (latency, traffic, errors, saturation) and the RED/USE method as
        the two checklists for what to instrument. `[X-REF 20]`
1.29.12 Distributed tracing as the tool for "which of the twelve hops is slow", and context
        propagation as the thing that must be designed in, not added later. `[X-REF 20]`
1.29.13 Capacity: state the **bottleneck resource** and its headroom. "We're at 40% of Postgres
        write capacity; the next scaling step at 70% is to shard by tenant, which takes a
        quarter." `[SAY]`
1.29.14 A design with a named bottleneck and a named next step reads as owned; one without reads as
        guessed. `[SAY]`
1.29.15 Load testing as the way you learn the real numbers: ramp to failure, note the failure mode,
        and record the knee of the latency curve — not just the throughput number. `[PROVE]`
1.29.16 Synthetic probes and real-user monitoring as complements: synthetics catch total outages
        during low traffic, RUM catches the experience your server metrics miss. `[X-REF 20]`

*(16 leaves)*

## §1.30 Migration: how you actually get there

1.30.1 Interviewers at the Staff bar ask "how would you roll this out to an existing system with
       live traffic?" The answer is never "big-bang cutover". `[SAY]`
1.30.2 Step 1 — **dual write behind a flag**: write old and new, read old. Accept that dual writes
       can diverge (§1.21) and reconcile continuously rather than assuming they will not.
1.30.3 Step 2 — **backfill** historical data in idempotent, resumable batches, rate-limited so it
       does not starve live traffic.
1.30.4 Step 3 — **shadow read / dark launch**: serve from old, also read new, compare and log
       mismatches. This is where the bugs are found, with zero user impact.
1.30.5 Step 4 — **flip reads incrementally**: 1% → 10% → 50% → 100%, per-tenant or per-user-hash,
       with a rollback that is a flag flip and not a deploy.
1.30.6 Step 5 — **stop the dual write**, keep the old path readable for a defined period, then
       decommission.
1.30.7 **Expand/contract for schema changes:** add the new nullable column, write both, backfill,
       switch reads, then drop the old — never a single migration that renames a column an old
       deploy still reads. `[X-REF 09]`
1.30.8 The reason: during a rolling deploy, old and new code both run, so every step must be safe
       with both. `[PROVE]`
1.30.9 Backfill throttling mechanics: batch by primary-key range, a bounded rate, a pause switch,
       and a progress marker that survives restart. `[BUILD]`
1.30.10 Comparison/reconciliation tooling: sampled diffing, a mismatch metric with a target of
        zero, and a decision rule for which side wins when they differ.
1.30.11 **Trap:** proposing a maintenance window. Sometimes correct, but say why the online path
        was rejected; at scale a window is usually not available. `[TRAP]`
1.30.12 The rollback question for each step: what is the undo, how long does it take, and is it
        still possible after the backfill? Some steps (dropping the old column) are one-way doors
        and must be named as such. `[SAY]`
1.30.13 Migrating *traffic* rather than data: strangler-fig routing at the proxy, per-route
        cutover, and keeping the old system running until its traffic is provably zero.
1.30.14 Data migration between stores with different consistency models: the new store may make
        guarantees the old one did not (or vice versa), and the application's assumptions must be
        audited, not assumed. `[TRAP]`

*(14 leaves)*

## §1.31 The vocabulary a design review assumes

1.31.1 Latency vs response time vs service time; throughput vs bandwidth; concurrency vs
       parallelism.
1.31.2 QPS/RPS/TPS, and the fact that "transactions" means different things in different rooms.
1.31.3 SLI / SLO / SLA / error budget. `[X-REF 20]`
1.31.4 RPO / RTO / MTBF / MTTR / MTTD.
1.31.5 Availability zone / region / cell / shard / partition / replica / node — six words
       candidates use interchangeably and interviewers do not.
1.31.6 Idempotent / commutative / associative / monotonic, and why the last three are the algebra
       behind CRDTs.
1.31.7 Fan-out / fan-in / scatter-gather / amplification (read, write, space).
1.31.8 Hot key / hot partition / skew / celebrity problem / thundering herd / stampede.
1.31.9 Head-of-line blocking, backpressure, admission control, load shedding, brownout.
1.31.10 Blast radius, bulkhead, cell, shuffle shard, failure domain, correlated failure.
1.31.11 Source of truth, read model, projection, derived data, materialised view, CDC.
1.31.12 At-most-once / at-least-once / exactly-once *delivery* vs *effect*.
1.31.13 Strong / eventual / causal / linearizable / serializable / strict serializable.
1.31.14 Push vs pull; polling vs long polling vs SSE vs WebSocket vs webhook. `[X-REF 10]`
1.31.15 North–south vs east–west traffic; ingress, egress, sidecar, control plane vs data plane.
1.31.16 Cold start, warm-up, steady state, knee of the curve, saturation point.

*(16 leaves)*

---

# PART 2 — INTERMEDIATE

## §2.1 The master reference tables

2.1.1 **Master table A — the latency/throughput/capacity reference.** One table combining §1.7's
      latency ladder, §1.9's per-node capacity, and the unit conversions, so the whole
      arithmetic toolkit is on one page. `[NUM]`
2.1.2 **Master table B — the per-pattern cost table.** For every pattern in this guide: what it
      buys, what it costs, the failure it introduces, and the condition under which you reach for
      it. Rows: read replica, cache tier, CDN, queue, log, shard, consistent hash, quorum,
      consensus, outbox, saga, 2PC, idempotency key, circuit breaker, bulkhead, rate limiter,
      load shedder, hedged request, cell, shuffle shard, multi-region active-passive,
      multi-region active-active, CQRS read model, event sourcing, CRDT, pre-signed upload,
      materialised counter, approximate counter. `[NUM]`
2.1.3 **Master table C — the amortised vs worst-case column.** For each pattern, the normal-case
      cost and the *incident-case* cost, which is the column that is always missing. Cache: 0.5 ms
      normal, 100× origin load on flush. Retry: +5% traffic normal, ×27 in a retry storm. Quorum:
      one extra RTT normal, unavailable in a minority partition.
2.1.4 **Master table D — consistency/availability per store**, PACELC classification plus what the
      store does during a partition on each side.
2.1.5 **Master table E — the failure catalogue**: for each component class, what "dies", "slow" and
      "full" look like, the metric that shows it, and the mitigation.
2.1.6 The rule for using these in an interview: the table is the *preparation* artifact; in the
      room you produce two rows of it, out loud, for the choice in front of you. `[SAY]`

*(6 leaves)*

## §2.2 Cost modelling — the dollar axis

2.2.1 Why the dollar axis belongs in a design: at L6 "it works" is table stakes; "it works and
      costs $40k/month instead of $400k" is the differentiating answer. `[SAY]`
2.2.2 The four cost drivers in order for most systems: **egress bandwidth**, **storage × retention
      × replication**, **compute at peak**, **managed-service request pricing**. `[NUM]`
2.2.3 Internet egress is the number that surprises people: order $0.05–$0.09 per GB at list price,
      which makes 1 PB/month of egress a seven-figure annual line. Work the arithmetic.
      `[PROVE]` `[NUM]` `[CURRENCY]` `[RESEARCH]`
2.2.4 The CDN's cost argument, not just its latency argument: offloading origin egress to a CDN is
      usually cheaper per GB, and origin-to-CDN transfer is often free. `[CURRENCY]` `[RESEARCH]`
2.2.5 Cross-AZ and cross-region transfer as internal costs that a chatty microservice topology
      multiplies; zone-aware routing is a cost control as much as a latency one. `[CURRENCY]`
      `[X-REF 18]`
2.2.6 NAT gateway / managed-endpoint data-processing charges as the classic hidden line, and the
      free gateway-endpoint alternative for object and KV storage. `[CURRENCY]` `[RESEARCH]`
2.2.7 Storage pricing ratios worth carrying: object storage is roughly an order of magnitude
      cheaper per GB-month than a managed NoSQL table's storage, and archive tiers another order
      below that — with retrieval fees and minimum durations as the catch. `[NUM]` `[CURRENCY]`
      `[RESEARCH]`
2.2.8 Request-priced stores: reads and writes are metered units, so a design that reads the same
      item 100 times per request is a *billing* bug before it is a latency bug. `[PROVE]`
2.2.9 On-demand vs provisioned vs reserved/committed-use as the three purchasing modes, and the
      utilisation break-even between them. `[PROVE]` `[X-REF 18]`
2.2.10 Cost per user / cost per request as the derived metric to state: total monthly cost ÷ MAU,
       and the fact that a healthy design's unit cost falls with scale.
2.2.11 The cost of *idle* redundancy: an active-passive second region costs nearly the full
       primary and serves no traffic; active-active at least earns its keep. `[PROVE]`
2.2.12 Where engineering time is the dominant cost: the operational burden of a self-hosted store
       versus a managed one usually dwarfs the price difference at small scale and inverts at
       large scale. `[SAY]`
2.2.13 **Trap:** optimising the cheap axis. Shaving compute while paying seven figures in egress is
       the most common real-world version. Start from the bill's largest line. `[TRAP]`

*(13 leaves)*

## §2.3 The estimation proofs

2.3.1 `[PROVE]` **Peak factor:** derive 2–3× from a diurnal curve — if traffic is roughly a sine
      over 16 waking hours, peak/mean lands near 2, and a global product flattens it further while
      a single-timezone product sharpens it.
2.3.2 `[PROVE]` **Availability multiplication:** 0.9999⁶ = 0.99940, i.e. 5.3 hours/year of
      unavailability from six four-nines dependencies. Show the binomial/first-order
      approximation 1 − n·(1−a) too. `[NUM]`
2.3.3 `[PROVE]` **Parallel redundancy:** 1 − (1−a)ⁿ, and the independence assumption that makes it
      a lie in practice.
2.3.4 `[PROVE]` **Fan-out p99 inflation:** if each of n shards independently exceeds its p99 with
      probability 0.01, P(no shard exceeds) = 0.99ⁿ; at n=10 that is 0.904, so ~10% of requests
      hit a slow shard — the request's p90, not its p99, is where the shard p99 shows up. Give the
      exact statement and the intuition. `[NUM]`
2.3.5 `[PROVE]` **Hit-ratio non-linearity:** origin load ∝ (1−h); the 90→99 step and the 99→99.9
      step each remove 90% of what remains.
2.3.6 `[PROVE]` **The 0%-hit-ratio blast:** origin capacity sized at (1−h) of read traffic sees a
      1/(1−h) multiplier on cache loss; at h=0.99 that is 100×.
2.3.7 `[PROVE]` **`R + W > N`:** the pigeonhole argument for set overlap, plus the explicit
      counter-example showing why overlap alone is not linearizability.
2.3.8 `[PROVE]` **Base62 key length:** need ≥ 1.8 × 10¹¹ keys; 62⁶ ≈ 5.7 × 10¹⁰ is too few,
      62⁷ ≈ 3.5 × 10¹² is enough — so 7 characters, with headroom stated as a ratio. `[NUM]`
2.3.9 `[PROVE]` **Snowflake bit arithmetic:** 2⁴¹ ms = 2.2 × 10¹² ms ≈ 69.7 years; 2¹⁰ = 1,024
      workers; 2¹² = 4,096 per ms per worker = 4.096 M/s per worker; total 4.2 × 10⁹ IDs/s
      cluster-wide. `[NUM]`
2.3.10 `[PROVE]` **Little's law** L = λW applied three ways: connection count from QPS × duration,
       thread-pool size from throughput × service time, and queue length from arrival rate ×
       wait. `[NUM]`
2.3.11 `[PROVE]` **Utilisation vs latency:** for an M/M/1 queue, mean wait = ρ/(1−ρ) × service
       time, so 50% utilisation doubles latency and 90% multiplies it by ten. This is the
       arithmetic behind "target 50–70%". `[NUM]`
2.3.12 `[PROVE]` **Retry amplification:** (1+r)^L requests per user action across L layers with r
       retries each; 3 layers × 3 attempts = 27.
2.3.13 `[PROVE]` **Bloom filter sizing:** m/n ≈ 9.6 bits per element and k = 7 for a 1% false
       positive rate; the general formulae m = −n·ln p / (ln 2)² and k = (m/n)·ln 2. `[NUM]`
       `[RESEARCH]`
2.3.14 `[PROVE]` **HyperLogLog error:** standard error ≈ 1.04/√m, so m = 2¹⁴ registers gives ~0.81%
       at ~12 KB. `[NUM]` `[RESEARCH]`
2.3.15 `[PROVE]` **Storage growth with replication and indexes:** raw × RF × (1 + index overhead) ×
       (1 + compaction headroom), worked once end-to-end so the write pass has a template.
2.3.16 `[PROVE]` **Shard count from two independent constraints** (storage and write throughput),
       taking the max and rounding up to the next power of two or to the logical-partition grid.
2.3.17 `[PROVE]` **Speed-of-light floor** for a cross-continent RTT, and why observed RTT is ~1.5–2×
       the fibre-path floor.
2.3.18 `[PROVE]` **Video bandwidth:** 1080p at ~5 Mbps × 1 M concurrent viewers = 5 Tbps, which is
       why live video is a CDN problem and not a server problem. `[NUM]`

*(18 leaves)*

## §2.4 Choosing consistency per operation

2.4.1 The procedure: list the operations, ask "what is the cost of serving a stale or conflicting
      value here", and assign the weakest model whose cost is acceptable.
2.4.2 The canonical assignments: money movement and inventory decrement → linearizable/serializable;
      messaging and comment threads → causal; counters, follower totals, view counts, search
      indexes → eventual.
2.4.3 Uniqueness constraints (username, email, seat) as the hidden linearizability requirement in
      otherwise-eventual systems. `[PROVE]` `[TRAP]`
2.4.4 The "compare-and-set on one partition" escape hatch: most uniqueness and inventory problems
      become single-partition conditional writes if you choose the partition key correctly.
      `[SAY]`
2.4.5 Session guarantees as the cheap fix for the common complaint, with the three
      implementations: leader pinning, replica pinning by user hash, and LSN/version tokens.
2.4.6 Bounded staleness as a contract: "reads may be up to 5 seconds old" is a designable,
      monitorable property, unlike "eventually".
2.4.7 Compensating for weak consistency in the UI: optimistic local echo, pending badges, and
      reconciliation on refresh — a design decision, not a frontend detail.
2.4.8 The cost of a linearizable operation, stated in numbers: one consensus round trip (same-AZ,
      ~1–2 ms; cross-region, ~100 ms+), unavailability on the minority side, and a throughput
      ceiling set by the leader. `[NUM]`
2.4.9 Isolation levels as the transactional axis that is orthogonal to the replication axis:
      read-committed vs repeatable-read vs serializable, and the anomalies each admits.
      `[X-REF 09]`
2.4.10 Write skew as the anomaly that snapshot isolation does *not* prevent, and the canonical
       on-call/booking example. `[PROVE]` `[TRAP]` `[X-REF 09]`
2.4.11 **Trap:** believing that a "strongly consistent read" flag in a managed store gives
       serializable transactions. It gives a recent single-item read. Different guarantee.
       `[TRAP]`

*(11 leaves)*

## §2.5 Skew, hot keys and fairness

2.5.1 The three skews: **data skew** (one partition holds more rows), **request skew** (one key
      gets more traffic), **temporal skew** (all traffic lands in the newest partition).
2.5.2 Zipf as the shape to expect: a small fraction of keys serve most traffic in nearly every
      consumer system, which is simultaneously why caching works and why hot partitions exist.
      `[PROVE]`
2.5.3 The celebrity problem in each of its guises: the follower fan-out, the viral video's
      counter, the one enormous tenant in a multi-tenant table.
2.5.4 Multi-tenant fairness: per-tenant quotas, per-tenant partitions for the largest tenants, and
      the "noisy neighbour" isolation options ranked by cost.
2.5.5 **Shuffle sharding** as the fairness mechanism worth naming: assign each customer a random
      *subset* of nodes so that two customers rarely share the same full set, which bounds the
      blast radius of one poisonous customer to a small fraction of others. `[PROVE]` `[SOURCE]`
      `[RESEARCH]`
2.5.6 The shuffle-shard combinatorics: with n nodes and shard size k, the number of distinct
      shards is C(n,k), and the probability that another customer shares your entire shard is
      1/C(n,k) — work a concrete case (n=100, k=2 → 4,950 combinations). `[PROVE]` `[NUM]`
2.5.7 Adaptive capacity in managed stores: the platform reallocates throughput toward hot
      partitions and splits partitions "for consumption" rather than only for size. `[SOURCE]`
      `[RESEARCH]` `[CURRENCY]`
2.5.8 Global admission control as the newer alternative to per-partition token buckets: a central
      service hands out short-lived token deposits so bursts are absorbed table-wide.
      `[SOURCE]` `[RESEARCH]` `[CURRENCY]`
2.5.9 Detecting skew before it pages you: per-partition throughput and storage percentiles,
      top-key sampling, and alerting on max/mean ratio rather than on totals. `[SAY]`
2.5.10 **Trap:** proving your key is "uniformly distributed" by hashing it, then serving a
       celebrity. Hashing fixes *data* skew, not *request* skew — hash(celebrity) is still one
       key. `[TRAP]`

*(10 leaves)*

## §2.6 Sharding strategy and the resharding project

2.6.1 The decision inputs: does every read carry the same key, is there a range-scan requirement,
      how many tenants, what is the growth curve, what is the largest single entity.
2.6.2 Shard-key candidates and their consequences: user ID (even, but cross-user queries scatter),
      tenant ID (natural isolation, terrible skew), entity ID (even, but relationships scatter),
      time (fatal for writes, ideal for retention), and composite keys.
2.6.3 The shard key is effectively immutable once data exists — treat choosing it as a one-way
      door and say so. `[SAY]` `[TRAP]`
2.6.4 Logical-partition indirection (§1.16.18) as the mechanism that makes it *not* a one-way door
      for physical placement — only for the key itself.
2.6.5 Routing implementations: client-side routing library, a proxy tier (Vitess, a custom router),
      or the store's own coordinator. Each puts the routing table in a different place with a
      different staleness problem.
2.6.6 The routing table's consistency: a stale router sends writes to the wrong shard during a
      move, so moves need a per-partition "frozen/redirect" state, not just a table update.
      `[PROVE]`
2.6.7 The split protocol end-to-end: mark source read-only or dual-write, copy, verify (checksums
      or row counts), cut over routing, drain the old copy, delete. `[BUILD]`
2.6.8 Online resharding with zero downtime: dual-write + backfill + shadow-read is the same
      five-step machine as §1.30, applied per partition.
2.6.9 Cross-shard queries and the three legal answers: denormalise so the query has a key, build a
      global secondary index (with its own consistency lag), or accept scatter-gather with a
      bounded fan-out and a hard timeout.
2.6.10 Cross-shard aggregation and pagination: merging N sorted streams with a global cursor is
       hard; the practical answers are per-shard cursors in a composite cursor, or a
       pre-aggregated read model.
2.6.11 Cross-shard transactions: 2PC (blocking, coordinator failure risk, latency of the slowest
       participant) vs saga (no isolation, compensations, observable intermediate state) vs
       redesigning the key so the transaction is single-partition. Prefer the third. `[SAY]`
2.6.12 Rebalancing triggers to state: partition size, partition throughput, node count change, and
       tenant growth. Automatic rebalancing during an incident is a known way to make it worse.
       `[TRAP]`
2.6.13 The organisational cost of sharding: every query in the codebase now needs the key, every
       new engineer must learn it, and the migration takes a quarter. That cost is a legitimate
       argument for buying a natively-sharded store instead. `[SAY]`

*(13 leaves)*

## §2.7 Distributed transactions and the alternatives

2.7.1 The default advice: **design so you do not need one**. Co-locate the entities under one
      partition key and use a local transaction. `[SAY]`
2.7.2 **2PC** mechanics at design level: prepare/vote, then commit/abort; participants hold locks
      through the whole window; the coordinator is a SPOF and an in-doubt participant blocks.
      `[PROVE]` `[X-REF 09]`
2.7.3 Why 2PC is rare in internet-scale systems: latency proportional to the slowest participant,
      lock hold times measured in round trips, and the blocking behaviour under coordinator
      failure. `[PROVE]`
2.7.4 Where 2PC is still right: within one database's partitions, between a broker and a database
      with XA, and in a stream processor's transactional sink.
2.7.5 **Saga**: a sequence of local transactions with a compensating action for each. No isolation,
      so intermediate states are observable and must be modelled (`PENDING`, `HELD`, `SETTLED`,
      `REVERSED`). `[X-REF 14]`
2.7.6 Saga orchestration vs choreography, with the debuggability argument for orchestration.
2.7.7 Compensations are not rollbacks: they are new business facts (a refund, a release), they can
      themselves fail, and some actions (an email sent) have no compensation. `[TRAP]`
2.7.8 Semantic locks / reservations as the way to get isolation back where it matters: hold the
      seat/inventory with a TTL before charging. `[BUILD]`
2.7.9 **TCC (try–confirm–cancel)** as the named pattern for that reservation shape. `[RESEARCH]`
2.7.10 The escrow / reservation pattern for inventory and balances: decrement into a hold, confirm
       or expire — which converts a distributed transaction into two idempotent single-partition
       operations plus a timer. `[BUILD]`
2.7.11 Idempotency and ordering requirements inside a saga: every step and every compensation must
       be idempotent, because the coordinator retries.
2.7.12 Timeout and stuck-saga handling: every step needs a deadline, and a saga that cannot advance
       or compensate needs an operator surface. This is the part designs omit. `[TRAP]`
2.7.13 The outbox as the transactional glue between the local transaction and the next step
       (§1.21.13).
2.7.14 Deterministic/single-shard transaction systems (Calvin-style) as the third architecture
       worth naming. `[RESEARCH]`

*(14 leaves)*

## §2.8 Streaming, windows and the analytics path

2.8.1 The three processing shapes: request/response, batch, and stream — with latency, cost and
      correctness properties for each.
2.8.2 **Lambda architecture** (batch layer + speed layer + serving layer) and its actual cost: two
      implementations of the same logic that must agree. `[RESEARCH]`
2.8.3 **Kappa architecture** (stream-only, reprocess by replaying the log) as the modern default,
      and its precondition: retention long enough to replay. `[RESEARCH]`
2.8.4 **Event time vs processing time**, and why every real aggregation is event-time.
2.8.5 **Watermarks** as the mechanism for "we believe we have seen everything up to T", and
      allowed lateness as the tunable that trades completeness against latency. `[SOURCE]`
      `[RESEARCH]`
2.8.6 Window types: tumbling, hopping/sliding, session — with the ad-click 1-minute tumbling
      window as the canonical example. `[RESEARCH]`
2.8.7 Late data: dropped, side-output, or a window re-fire with a corrected result — and the
      downstream requirement that the sink be able to *update* an already-published aggregate.
      `[TRAP]`
2.8.8 Exactly-once in a stream processor: checkpoint/snapshot of operator state plus a
      two-phase-commit sink, and the precise claim it supports (end-to-end exactly-once effect
      into a transactional sink, not into an arbitrary REST call). `[SOURCE]` `[TRAP]`
      `[RESEARCH]`
2.8.9 Stateful stream processing and where the state lives (embedded RocksDB + changelog topic),
      which makes rebalancing a state-transfer problem. `[RESEARCH]`
2.8.10 Backfill/reprocessing as a first-class requirement: replay from an offset with the same
       code, into a parallel output, then swap.
2.8.11 The pre-aggregation ladder for analytics: raw events → 1-minute rollups → hourly → daily,
       each cheaper to query and each with its own retention.
2.8.12 OLTP/OLAP separation and why the analytics query must never run on the serving store.
       `[X-REF 09]`
2.8.13 Approximate answers as the throughput lever in analytics: HLL for uniques, Count-Min for
       frequency, t-digest/DDSketch for percentiles, sampling for everything else. `[RESEARCH]`
2.8.14 Idempotency in the analytics path: dedupe by event ID within a bounded window, because
       at-least-once delivery otherwise inflates every count. `[PROVE]`

*(14 leaves)*

## §2.9 Tail latency

2.9.1 Why the tail dominates at scale: with fan-out, a request's latency is the max over its
      sub-requests, so a rare slow response becomes the common experience. `[PROVE]` `[SOURCE]`
2.9.2 The sources of variability: shared resources, background daemons (compaction, GC,
      log rotation), queueing, maintenance, energy management, and multi-tenancy. `[SOURCE]`
      `[RESEARCH]`
2.9.3 Within-request tail-tolerance techniques: **hedged requests**, **tied requests**, and
      **micro-partitions** (many more partitions than machines, so load sheds in ~5% increments
      with 20 partitions per machine). `[SOURCE]` `[NUM]` `[RESEARCH]`
2.9.4 **Selective replication** for detected-hot partitions, and **latency-induced probation**
      (remove a slow machine, keep shadowing it, reinstate when it recovers). `[SOURCE]`
      `[RESEARCH]`
2.9.5 Cross-request techniques: differentiating service classes, prioritising interactive over
      batch, and breaking long requests into pieces so a big one cannot head-of-line-block.
      `[SOURCE]`
2.9.6 GC and JIT as JVM-specific tail sources, and the design-level responses (heap sizing,
      collector choice, warm-up before joining the LB). `[X-REF 06]`
2.9.7 Timeouts as a tail-*creation* mechanism when set wrong: a timeout at the p99 turns 1% of
      requests into errors plus retries plus double load. `[PROVE]` `[TRAP]`
2.9.8 The tail-latency budget arithmetic for a chain: if a request touches five services serially,
      each service's p99 budget is roughly a fifth of the total minus network, and the *observed*
      end-to-end p99 is worse than the sum of p99s would suggest. `[PROVE]`
2.9.9 Measuring the tail honestly: histograms not averages, client-side measurement, and the
      coordinated-omission correction (§1.29.9).
2.9.10 The one-line interview assertion: "at 100-way fan-out I am living at the p99.99 of a single
       node, so I need hedging or micro-partitioning, not a faster average." `[SAY]`

*(10 leaves)*

## §2.10 Overload, shedding and the collapse dynamics

2.10.1 The core asymmetry: a system under overload does *less* useful work as load rises, because
      it spends capacity on requests whose clients have already gone. `[PROVE]`
2.10.2 **Queue management:** small queues (≤50% of the thread pool for steady traffic), and
      queueless-with-failover for latency-critical services. A big queue converts a throughput
      problem into a latency problem and then into a timeout storm. `[SOURCE]` `[NUM]`
      `[RESEARCH]`
2.10.3 LIFO queueing during overload as the counter-intuitive improvement: serving the newest
      request first means at least some requests complete within the client's deadline.
      `[PROVE]` `[RESEARCH]`
2.10.4 Dropping requests whose deadline has already expired, before doing any work on them —
      the cheapest capacity you will ever recover. `[SOURCE]`
2.10.5 **Graceful degradation as a step beyond shedding:** reduce the *work per request* (search a
      cache subset, use a cheaper ranking model) rather than rejecting the request. `[SOURCE]`
2.10.6 The load-shedding decision surface: what signal, what threshold, which requests, what
      response code, and how the client is told to back off. `[SAY]`
2.10.7 **Cascading failure** defined as a failure that grows through positive feedback, with the
      canonical sequence: overload → resource exhaustion → health-check failure → capacity
      removal → more overload on survivors. `[SOURCE]` `[PROVE]`
2.10.8 The triggering conditions catalogue: process death, a binary rollout, a resource-profile
      change, organic growth, a planned drain, a request-profile change, a dependency limit.
      `[SOURCE]` `[RESEARCH]`
2.10.9 **Metastable failure:** a trigger pushes the system into a degraded equilibrium that
      *persists after the trigger is removed*, sustained by a positive feedback loop — most often
      the retry policy. The outage is usually blamed on the trigger; the root cause is the
      sustaining effect. `[SOURCE]` `[PROVE]` `[RESEARCH]`
2.10.10 The practical consequence: recovery requires *reducing load below the level that caused the
        problem*, not merely removing the trigger — which is why "drop 99% of traffic and let it
        back in slowly" is the standard recovery. `[PROVE]` `[SAY]`
2.10.11 **Cold cache after restart** as a specific sustaining effect: the restarted fleet cannot
        serve at the rate the cold cache implies, so it fails again. Fixes: gradual traffic ramp,
        warm-up, and over-provisioning for the recovery window. `[SOURCE]`
2.10.12 Immediate incident steps from the SRE literature: add capacity, temporarily disable
        health-check-driven removal, restart wedged servers, drop traffic aggressively, enter a
        degraded mode, shed batch and non-critical load, block the expensive query. `[SOURCE]`
        `[RESEARCH]`
2.10.13 "Always go downward in the stack": intra-layer calls and backend-to-backend proxying create
        distributed deadlocks and amplify failure. `[SOURCE]`
2.10.14 Testing for it: load to failure, impulse tests, production capacity reduction, and
        verifying that non-critical backend loss really is survivable. `[SOURCE]`
2.10.15 **Trap:** autoscaling as the answer to overload. Scaling takes minutes, the collapse takes
        seconds, and a scaled-up fleet with a cold cache can make it worse. Shedding is the
        seconds-scale control; autoscaling is the minutes-scale one. `[TRAP]` `[PROVE]`

*(15 leaves)*

## §2.11 Health, failure detection and the removal death spiral

2.11.1 The three probe kinds and their distinct jobs: liveness (restart me), readiness (route to
      me), startup (do not judge me yet). `[X-REF 19]`
2.11.2 Shallow vs deep checks, and the correlated-removal failure they respectively cause
      (§1.24.4).
2.11.3 The fleet-removal cap as the standard mitigation, with Envoy's panic threshold as the
      reference implementation (§1.24.6). `[SOURCE]`
2.11.4 Passive detection (outlier ejection from real traffic) as the complement to active probes,
      because real requests find failures probes do not. `[SOURCE]`
2.11.5 **Grey failure:** a partial failure with **differential observability** — the health checker
      sees a healthy node while clients see a broken one. Packet loss, degraded disks, memory
      pressure, a thread pool wedged on one endpoint. `[SOURCE]` `[PROVE]` `[RESEARCH]`
2.11.6 The design response to grey failure: judge health from *client-observed* signals, close the
      observability gap between the app's view and the checker's view, and prefer gradual traffic
      reduction over binary in/out. `[SOURCE]` `[RESEARCH]`
2.11.7 Phi-accrual failure detection as the "suspicion level instead of a boolean" approach, and
      where it is used. `[RESEARCH]`
2.11.8 Heartbeats, leases and TTLs as the three ways a distributed system decides a peer is gone,
      and the fact that all three are timeouts with different names. `[PROVE]`
2.11.9 The unavoidable trade-off: no failure detector can distinguish a slow node from a dead one
      in an asynchronous network. Every design must choose which error it prefers. `[PROVE]`
      `[SAY]`
2.11.10 Fencing as the safety net that makes the wrong choice survivable (§1.15.13, §3.3).
2.11.11 The death spiral, written as a loop to recognise: slow dependency → deep health check fails
        → instances removed → survivors overloaded → more checks fail → zero capacity.
        `[TRAP]` `[SAY]`

*(11 leaves)*

## §2.12 Cells, blast radius and isolation architecture

2.12.1 **Cell-based architecture:** partition the *whole system* — compute, data, cache, queues —
      into independent instances, so a failure inside one cell cannot propagate. `[SOURCE]`
      `[RESEARCH]` `[CURRENCY]`
2.12.2 Blast radius becomes an explicit design parameter: 10 cells caps worst-case customer impact
      at 10%, 100 cells at 1%. `[PROVE]` `[NUM]` `[RESEARCH]`
2.12.3 The **cell router** as the only shared component, and the design rule that it must be the
      thinnest, dumbest, most-tested thing you own — because it is the one remaining correlated
      failure domain. `[SOURCE]` `[RESEARCH]`
2.12.4 Cell sizing: large enough to be efficient and to hold the biggest tenant, small enough that
      losing one is survivable and that it can be load-tested to destruction.
2.12.5 Cell placement and the mapping function: by tenant, by user hash, by region — and the
      migration procedure for moving a tenant between cells.
2.12.6 Deployment as the main *benefit*: roll a change one cell at a time and a bad deploy hits
      one cell's worth of customers. `[PROVE]`
2.12.7 Shuffle sharding layered on cells for further isolation (§2.5.5). `[SOURCE]`
2.12.8 The costs to state honestly: per-cell fixed overhead, harder cross-cell features (global
      search, cross-tenant analytics), more operational surface, and a routing layer to own.
2.12.9 Relationship to AZs, regions and Kubernetes namespaces/clusters: a cell is a *logical*
      failure domain that may or may not align with a physical one. `[X-REF 19]`
2.12.10 The interview usage: cells are the right answer when the question is "how do you stop one
        bad tenant, one bad deploy or one bad shard from taking down everyone", and the wrong
        answer when the question is throughput. `[SAY]`

*(10 leaves)*

## §2.13 Geospatial and other non-key access patterns

2.13.1 The problem: "find things near me" has no partition key, so the naive query is a full scan.
2.13.2 **Geohash:** interleave lat/long bits into a Z-order string; a prefix is a rectangle, so
      proximity becomes a prefix range query on a normal index. `[PROVE]` `[RESEARCH]`
2.13.3 Geohash's two defects: boundary fragmentation (near-neighbours across a cell edge have
      distant prefixes, so you must query the 8 neighbouring cells) and non-uniform cell size with
      latitude. `[TRAP]` `[RESEARCH]`
2.13.4 **Quadtree:** recursive subdivision that adapts to density — deeper where there are more
      points; in-memory, and rebuilding/rebalancing is the operational cost. `[RESEARCH]`
2.13.5 **S2:** sphere→cube projection plus a Hilbert curve, so nearby cells have nearby 64-bit IDs
      and a region becomes a set of ID ranges over a B-tree. `[RESEARCH]`
2.13.6 **H3:** hexagonal hierarchical cells, 16 resolutions, each ~7× the previous in count; all
      neighbours equidistant, which makes aggregation and ring queries clean. `[NUM]`
      `[RESEARCH]`
2.13.7 The choice rule: geohash when you want a string prefix in an existing index; S2 for
      global-scale range queries; H3 when you aggregate over cells or do ring/k-ring queries;
      quadtree when density varies wildly and the index is in memory. `[SAY]`
2.13.8 The write-heavy variant (live driver/rider locations): frequent updates make a persistent
      spatial index expensive, so the standard answer is an in-memory sharded grid with short TTLs
      plus a durable trail written asynchronously.
2.13.9 Non-key access patterns generally: full-text (inverted index), vector similarity (ANN
      index), and multi-attribute filtering (a search engine or a columnar scan) — each is
      "build a second, purpose-built index" (§1.27).
2.13.10 The recurring shape: **the primary store answers key lookups; every other question is a
        derived index.** `[SAY]`

*(10 leaves)*

## §2.14 Probabilistic and compact structures

2.14.1 **Bloom filter:** m bits, k hashes, no false negatives, tunable false positives, no deletes.
      Design uses: skip a disk/network read for a definitely-absent key, dedupe a crawler frontier,
      LSM SSTable membership. `[PROVE]` `[BUILD]`
2.14.2 Bloom sizing arithmetic and the ~9.6 bits/element at 1% figure (§2.3.13). `[NUM]`
2.14.3 Counting Bloom and cuckoo filters as the delete-supporting variants. `[RESEARCH]`
2.14.4 **HyperLogLog:** cardinality with ~0.81% error in ~12 KB at 2¹⁴ registers; mergeable, which
      is why it works across shards and time buckets. `[PROVE]` `[NUM]` `[BUILD]`
2.14.5 **Count-Min Sketch:** frequency estimation with one-sided overcounting; the heavy-hitters
      use case for hot-key detection. `[RESEARCH]`
2.14.6 Quantile sketches (t-digest, DDSketch) as the reason you can aggregate latency percentiles
      across hosts at all. `[RESEARCH]`
2.14.7 Top-K / space-saving for leaderboards of approximate popularity.
2.14.8 MinHash / SimHash for near-duplicate detection (crawler dedupe, plagiarism).
2.14.9 The decision rule: exactness costs storage and coordination linear in cardinality;
      approximation costs a stated error bar. **Ask whether exact is required** — for counters,
      uniques and trending, it usually is not. `[SAY]`
2.14.10 Where these live in a design: Redis modules, the stream processor's state, or the storage
        engine itself — and the fact that a mergeable sketch is what makes distributed
        aggregation cheap. `[PROVE]`

*(10 leaves)*

## §2.15 Real-time delivery and connection-oriented designs

2.15.1 The four transports and their costs: polling (simple, wasteful, bounded staleness), long
      polling (fewer requests, held connections), SSE (server→client only, HTTP-native,
      auto-reconnect), WebSocket (bidirectional, its own protocol and infrastructure).
      `[X-REF 10]`
2.15.2 Webhooks as the server→server case, with the delivery guarantees, retry policy, signing,
      and receiver-idempotency requirements that make them a design in themselves. `[X-REF 12]`
2.15.3 Connection capacity arithmetic: memory per connection × concurrent connections, file
      descriptors, and the resulting gateway node count. 1 M connections at ~10 KB each is ~10 GB
      of buffers before any application state. `[PROVE]` `[NUM]`
2.15.4 The connection registry (`user → gateway instance`) with heartbeat and TTL, and the routing
      hop it implies for delivery.
2.15.5 Deploy and autoscaling with long-lived connections: drain by refusing new connections,
      reconnect with jittered backoff, and never disconnect everyone at once — a synchronised
      reconnect is a self-inflicted DDoS. `[TRAP]` `[PROVE]`
2.15.6 Presence as the classic scaling trap: broadcasting every presence change to every contact is
      O(contacts) per flap; debounce, batch, and only push for conversations currently open.
      `[PROVE]`
2.15.7 Push notifications as the offline path: APNs/FCM, per-device tokens, token invalidation, and
      the fact that the push provider is a third-party dependency with its own failure mode.
2.15.8 Ordering and delivery for real-time: server-assigned per-conversation sequence numbers,
      client dedupe by client-generated message ID, and gap detection driving a resync.
2.15.9 Fan-out to connections vs fan-out to storage: the live path and the durable path are two
      different systems that must agree, and the reconciliation is "on reconnect, fetch since
      sequence N".

*(9 leaves)*

## §2.16 Security, tenancy and privacy at the design layer

2.16.1 Where authentication happens in the topology: at the edge/gateway, with a short-lived
      internal token thereafter — and the trade-off against per-service verification.
      `[X-REF 13]`
2.16.2 Authorization data placement: the permission check must not become a synchronous call to a
      distant service on every request; caching authz decisions has a staleness/security
      trade-off that must be stated. `[TRAP]`
2.16.3 Tenant isolation models ranked: shared table with a tenant column, schema per tenant,
      database per tenant, cell per tenant — cost and blast radius move in opposite directions.
2.16.4 The tenant ID must be in every key, every cache key, every log line and every metric label
      — and a missing tenant filter is the canonical multi-tenant data leak. `[TRAP]`
2.16.5 Encryption in transit (mTLS internally) and at rest, plus the key-management dependency each
      introduces. `[X-REF 13]`
2.16.6 Rate limiting and quota as an abuse control, not only a capacity control; bot traffic as a
      real fraction of the load estimate. `[X-REF 13]`
2.16.7 Data deletion and retention as design constraints: right-to-erasure across derived read
      models, backups and logs is a *pipeline*, not a `DELETE`. Crypto-shredding as the practical
      answer. `[RESEARCH]`
2.16.8 Audit logging as a durability requirement with its own retention and immutability
      properties.
2.16.9 The secrets and credential path in the design: no long-lived static credentials, rotation
      without downtime, and the fact that certificate expiry is a top cause of correlated outages.
      `[TRAP]` `[X-REF 13]`

*(9 leaves)*

## §2.17 Deployment, rollout and configuration as design properties

2.17.1 Rollout strategies and what each buys: rolling, blue/green, canary, and per-cell staggered.
      `[X-REF 19]`
2.17.2 Canary analysis needs a *comparison*, not a smoke test: error rate and latency of the canary
      versus the baseline, on the same traffic mix.
2.17.3 Feature flags as the decoupling of deploy from release, and the requirement that every risky
      design change has a flag with a documented off-switch. `[SAY]`
2.17.4 Configuration changes as the most dangerous deploy: they propagate faster than code, are
      often global, and frequently bypass canary. Treat config as code with the same rollout
      discipline. `[TRAP]` `[PROVE]`
2.17.5 Schema and API compatibility during a rolling deploy: both versions run simultaneously, so
      every change must be forward- and backward-compatible for one release (§1.30.7).
2.17.6 Regional and cell staggering to bound blast radius, and the deliberate "bake time" between
      stages.
2.17.7 Rollback as a first-class capability: measured in minutes, tested, and not blocked by a data
      migration. A design whose rollback requires a data restore has no rollback. `[SAY]`
2.17.8 Infrastructure as code and immutable infrastructure as the properties that make any of the
      above reproducible. `[X-REF 18]`

*(8 leaves)*

## §2.18 The organisational and operational face

2.18.1 **Who owns the new datastore?** A design that adds a component adds an on-call rotation, a
      backup policy, an upgrade path and a capacity forecast. Name the owner. `[SAY]`
2.18.2 The on-call surface as a design output: how many new alerts, what runbook, what is the
      3 a.m. failure mode, and can a generalist fix it. `[X-REF 20]`
2.18.3 Conway's law as a real design constraint: a service boundary that cuts across two teams'
      release cadence will be violated. `[RESEARCH]`
2.18.4 Build vs buy vs adopt-an-existing-internal-thing, with the honest cost of each including
      migration and training.
2.18.5 The migration project plan at the level an L6 is expected to give: phases, the reversible
      point, the metric that says it worked, and the estimated calendar time.
2.18.6 Deprecation of the old path as work that must be scheduled, or you keep both forever.
      `[TRAP]`
2.18.7 Documentation, runbooks and design docs as deliverables of the design, not afterthoughts.
2.18.8 Team-scaling consequences: the number of services one team can operate, and the fact that a
      microservice split is usually an organisational answer to a coordination problem, not a
      scaling answer. `[TRAP]`
2.18.9 Incremental delivery: what ships in v1 to get feedback, and what is explicitly deferred with
      a trigger for revisiting. `[SAY]`

*(9 leaves)*

## §2.19 Testing and validating a design

2.19.1 Load testing to failure, not to target: find the knee and the failure mode. `[PROVE]`
2.19.2 The load generator must be open-loop (constant arrival rate) or your numbers are fiction
      (§1.29.9).
2.19.3 Traffic replay / shadow traffic as the highest-fidelity test, with the write-side problem
      (shadowed writes must go somewhere harmless).
2.19.4 Chaos engineering as hypothesis-driven: state the expected behaviour, inject the fault,
      compare. Instance kill, AZ loss, dependency latency injection, packet loss, disk full,
      clock skew.
2.19.5 Game days and failover rehearsals as the thing that converts a DR plan into a DR capability
      (§1.26.7).
2.19.6 Capacity and dependency limit testing: hitting the quota of the managed service *on
      purpose*, so you learn its error shape before an incident does. `[X-REF 18]`
2.19.7 Correctness testing of distributed behaviour: deterministic simulation, fault injection at
      the RPC layer, and formal methods (TLA+/P) for the small, critical protocol. `[RESEARCH]`
2.19.8 Jepsen-style consistency testing as the reason to be skeptical of vendor consistency claims,
      and the standard finding that documented guarantees and delivered guarantees differ.
      `[RESEARCH]` `[TRAP]`
2.19.9 What "we tested it" must mean in a design review: the specific fault, the observed
      behaviour, and the date. `[SAY]`

*(9 leaves)*

## §2.20 The which-one-and-why decision tables

2.20.1 SQL vs NoSQL vs NewSQL vs search vs columnar vs object — by access pattern (§1.14).
2.20.2 Cache tier placement — by latency, sharing and invalidation control (§1.19).
2.20.3 Queue vs log vs direct call vs scheduled batch — by consumer count, replay need and ordering
      (§1.20).
2.20.4 Sync vs async — by "does the user need the result" (§1.20.1).
2.20.5 Push vs pull for fan-out — by follower distribution and read:write ratio (§5.3 feed).
2.20.6 Rate-limiting algorithm — by burst tolerance and memory (§1.23).
2.20.7 Partitioning scheme — by range-scan need and rebalance frequency (§1.16).
2.20.8 Replication topology — by write locality and conflict tolerance (§1.15).
2.20.9 Consistency model — per operation, by the cost of staleness (§2.4).
2.20.10 Transaction pattern — local vs 2PC vs saga vs reservation (§2.7).
2.20.11 ID scheme — by sortability, coordination and leakage (§1.22).
2.20.12 Multi-region topology — by RPO/RTO and write locality (§1.26).
2.20.13 Real-time transport — by directionality and connection cost (§2.15).
2.20.14 Spatial index — by query shape and update rate (§2.13).
2.20.15 Isolation architecture — shared / per-tenant / cell / shuffle shard, by blast radius
        target (§2.12).

*(15 leaves)*

## §2.21 Currency: what changed by 2026

2.21.1 Cell-based architecture moved from folklore to published, vendor-endorsed guidance with
      reference implementations. Expect an interviewer to know the term. `[CURRENCY]`
      `[RESEARCH]`
2.21.2 Multi-region strong consistency became a managed-service checkbox (DynamoDB global tables
      MRSC, Aurora DSQL), which changes the honest answer to "can I have RPO=0 across regions"
      from "only with Spanner" to "yes, with stated constraints and cost". `[CURRENCY]`
      `[RESEARCH]`
2.21.3 Kafka on KRaft (ZooKeeper removed) plus tiered storage changes the retention conversation:
      "keep the log forever" is now an economics question, not an impossibility. `[CURRENCY]`
      `[RESEARCH]` `[X-REF 14]`
2.21.4 Serverless as a legitimate default for spiky, low-baseline workloads, with cold start and
      per-invocation pricing as the counter-arguments. `[CURRENCY]` `[X-REF 18]`
2.21.5 Vector search and RAG-shaped systems entering the standard question bank; treat the vector
      index as a derived read model with an ANN recall/latency trade-off. `[CURRENCY]`
      `[RESEARCH]`
2.21.6 The interview rubric itself: two design rounds at L6+, more weight on operational maturity
      and driving, and explicit penalties for memorised architectures. `[CURRENCY]` `[RESEARCH]`
2.21.7 DDIA 2nd edition (Feb 2026) as the reference curriculum, with its new front-matter chapters
      on architecture trade-offs and non-functional requirements — i.e. the industry's own
      canonical text now leads with the same "requirements and trade-offs first" framing this
      guide does. `[CURRENCY]` `[RESEARCH]`
2.21.8 The numbers that have moved since the classic latency tables: SSD and network figures, node
      sizes, and per-node capacity rules. Re-verify §1.7 and §1.9 against a current source in the
      write pass. `[CURRENCY]` `[TRAP]`

*(8 leaves)*

---

# PART 3 — UNDER THE HOOD

## §3.1 Consistent hashing, properly

3.1.1 The original result (Karger et al., 1997): a hash function into a ring such that adding or
      removing one of N buckets remaps only ~K/N keys, designed for web caching. `[SOURCE]`
      `[RESEARCH]`
3.1.2 The monotonicity, balance, spread and load properties the paper actually proves, and which
      of them virtual nodes are needed for. `[PROVE]` `[SOURCE]`
3.1.3 Ring implementation: a sorted structure of token→node, lookup by `ceiling(hash(key))` with
      wraparound — O(log N) with a `TreeMap`, O(1) with a precomputed lookup table. `[BUILD]`
3.1.4 Virtual-node count as a variance/memory trade: with V vnodes per node the load standard
      deviation falls roughly as 1/√V; V=100–256 puts imbalance in the low single-digit percent.
      `[PROVE]` `[NUM]`
3.1.5 Hash-function requirements: uniformity and avalanche, not cryptographic strength; MurmurHash3
      / xxHash as the usual choices; and why `String.hashCode()` is a poor ring hash. `[TRAP]`
3.1.6 **Rendezvous (HRW) hashing:** compute `hash(key, node)` for every node and take the maximum.
      O(N) per lookup, no ring or vnodes, minimal disruption, and it handles weights cleanly.
      `[PROVE]` `[RESEARCH]` `[BUILD]`
3.1.7 **Jump consistent hash:** O(1) memory, O(log N) time, perfectly balanced — but buckets must
      be numbered 0..N−1, so it cannot remove an arbitrary node. Right for shard counts, wrong for
      a churning server set. `[PROVE]` `[RESEARCH]`
3.1.8 **Maglev hashing:** a precomputed permutation lookup table giving O(1) lookups with
      near-perfect balance and small disruption; used in high-throughput L4 load balancers.
      `[RESEARCH]`
3.1.9 **Multi-probe consistent hashing:** trades lookup time for the memory that vnodes would
      have cost. `[RESEARCH]`
3.1.10 **Consistent hashing with bounded loads:** a capacity cap of c = (1+ε)·average per node with
       forwarding to the next node when full; bounds the maximum load while keeping movement
       small. Implemented in production proxies. `[PROVE]` `[RESEARCH]`
3.1.11 The comparison table: ring, rendezvous, jump, Maglev, multi-probe, bounded-load — lookup
       cost, memory, balance quality, disruption on change, weight support, arbitrary removal.
3.1.12 **Power of two random choices** as the non-hashing alternative for stateless balancing:
       sample two backends, pick the less loaded; the maximum load drops from Θ(log n/log log n)
       to Θ(log log n). `[PROVE]` `[RESEARCH]`
3.1.13 Where each is actually used: Dynamo/Cassandra vnode rings, Memcached client rings, Envoy's
       ring-hash and Maglev balancers, Kafka's `hash mod partitions` (deliberately *not*
       consistent, because partitions do not move). `[RESEARCH]`
3.1.14 **Trap:** consistent hashing described as solving hot keys. It solves *rebalancing*, not
       skew; a single hot key is one point on the ring no matter how many vnodes exist. `[TRAP]`

*(14 leaves)*

## §3.2 The Dynamo lineage

3.2.1 The paper's premise: for the shopping cart, "always writeable" beats consistent, so
      conflict resolution moves to read time and to the application. `[SOURCE]` `[RESEARCH]`
3.2.2 The technique inventory, each mapped to the problem it solves: consistent hashing
      (partitioning), vector clocks (versioning), sloppy quorum + hinted handoff (temporary
      failures), Merkle trees (permanent failures/anti-entropy), gossip (membership and failure
      detection). `[SOURCE]`
3.2.3 The preference list and the "first N *healthy* nodes" rule that defines a sloppy quorum.
      `[SOURCE]`
3.2.4 Vector clocks in detail: `(node, counter)` pairs, the descends-from partial order, what
      "concurrent" means formally, and clock truncation as the practical hack that can lose
      causality. `[PROVE]` `[SOURCE]`
3.2.5 Why the shopping cart merge (union of adds) works and what it gets wrong (a removed item
      returns) — the honest limitation that motivated CRDTs. `[PROVE]` `[TRAP]`
3.2.6 Merkle-tree anti-entropy: per-range trees, compare roots, descend only where hashes differ,
      transfer only the differing keys. The cost is tree recomputation on write. `[PROVE]`
      `[SOURCE]` `[BUILD]`
3.2.7 Gossip-based membership and the eventual-consistency of the ring itself.
3.2.8 What DynamoDB (the service) kept and what it discarded relative to Dynamo (the paper):
      partitioned Multi-Paxos with leader leases per partition instead of leaderless quorums,
      managed partitioning instead of a client-visible ring, no vector clocks in the public API.
      **These are different systems with the same name.** `[TRAP]` `[SOURCE]` `[RESEARCH]`
3.2.9 DynamoDB's admission-control evolution as the case study in hot partitions: per-partition
      token buckets → burst capacity → adaptive capacity → **global admission control** with
      short-lived token deposits, plus **splitting for consumption** as well as for size.
      `[SOURCE]` `[RESEARCH]` `[CURRENCY]`
3.2.10 Its availability engineering worth quoting: formal methods for the replication protocols,
       log replicas that can join a group quickly without a full data copy, and a metadata service
       designed so a cold cache cannot stampede the metadata store. `[SOURCE]` `[RESEARCH]`
3.2.11 Cassandra as the open-source Dynamo descendant: tunable consistency levels, LOCAL_QUORUM in
       multi-DC, hinted handoff and read repair as operator-visible knobs, and the tombstone/
       compaction operational surface. `[RESEARCH]` `[X-REF 09]`
3.2.12 What Jepsen-style analysis repeatedly finds in this family: the delivered guarantee is
       weaker than the documented one under partition, clock skew or membership change. Design as
       if the weaker guarantee is the real one. `[RESEARCH]` `[TRAP]`

*(12 leaves)*

## §3.3 Consensus, leases and fencing

3.3.1 What consensus gives you that quorums do not: a **total order** of operations that survives
      failures, hence linearizability, leader election, and atomic configuration change.
      `[PROVE]`
3.3.2 FLP impossibility, stated usefully: no deterministic protocol guarantees consensus in an
      asynchronous system with one faulty process — which is why real systems use timeouts and
      settle for "terminates in practice". `[PROVE]` `[RESEARCH]`
3.3.3 **Raft** decomposed as the paper decomposes it: leader election, log replication, safety.
      `[SOURCE]` `[RESEARCH]`
3.3.4 Raft mechanics worth stating: terms as logical clocks, randomised election timeouts to avoid
      split votes, `AppendEntries` as both replication and heartbeat, commit index advancing when
      a majority has the entry, and the log-completeness restriction on who may become leader.
      `[SOURCE]` `[PROVE]`
3.3.5 Raft membership change (joint consensus / single-server changes) as the part everyone skips
      and every operator hits. `[SOURCE]`
3.3.6 Paxos, Multi-Paxos and Zab in one paragraph each, and why Raft won the implementation
      mindshare. `[RESEARCH]`
3.3.7 The 2f+1 arithmetic: tolerating f failures needs 2f+1 nodes, so 3 tolerates 1 and 5 tolerates
      2; and the reason clusters are 3 or 5, never 4 or 6. `[PROVE]` `[NUM]`
3.3.8 Latency cost: one round trip to a majority per committed entry, so same-AZ ~1 ms,
      cross-region ~100 ms — the number that decides whether consensus is on your request path.
      `[NUM]`
3.3.9 Throughput cost: a single leader is a serialisation point; scaling means many consensus
      groups (one per partition), which is exactly how Spanner, CockroachDB and DynamoDB scale.
      `[PROVE]`
3.3.10 **Leases** as consensus's practical output: a time-bounded exclusive right, which turns an
       unbounded coordination problem into a bounded one — and depends on bounded clock drift.
       `[PROVE]`
3.3.11 Leader leases and read optimisation: a leaseholder can serve linearizable reads without a
       round trip, *if* the lease's clock assumptions hold. `[PROVE]`
3.3.12 **Fencing tokens:** a monotonically increasing number issued with the lock, which the
       protected resource must check and reject when stale. Without it, a paused process can wake
       and corrupt state after its lease expired. `[SOURCE]` `[PROVE]` `[BUILD]`
3.3.13 ZooKeeper znode sequence numbers and etcd revisions as fencing tokens you get for free.
       `[SOURCE]` `[RESEARCH]`
3.3.14 **Redlock and the critique:** a Redis-based lock provides no monotonic fencing token and
       does not survive the process-pause/GC-pause scenario, so it is unsafe for correctness-
       critical mutual exclusion, though acceptable for efficiency-only locking. State which of
       the two you need. `[SOURCE]` `[TRAP]` `[RESEARCH]`
3.3.15 The design rule that follows: **if overlap corrupts state, the protected resource must
       reject stale writers.** A lock alone is never sufficient. `[SAY]`
3.3.16 Where consensus belongs in a typical design: configuration, membership, leader election,
       distributed locks, and the metadata plane — *not* the data plane of a high-throughput
       service. `[SAY]`
3.3.17 Coordination-avoidance as the alternative: partition the work so each item has one owner,
       and consensus is needed only to decide ownership. `[PROVE]`

*(17 leaves)*

## §3.4 Time, clocks and ordering

3.4.1 Why wall-clock time is not an ordering mechanism: NTP-synchronised clocks drift, step
      backwards, and disagree by milliseconds to seconds; leap seconds and VM pauses make it
      worse. `[PROVE]` `[TRAP]`
3.4.2 Monotonic vs wall clocks, and the rule: durations from the monotonic clock, timestamps from
      the wall clock, never mix. `[X-REF 03]`
3.4.3 **Lamport clocks:** a counter per node, `max(local, received)+1`; gives a total order
      consistent with causality but cannot detect concurrency. `[PROVE]`
3.4.4 **Vector clocks:** one counter per node; detects concurrency exactly, at O(N) size — which
      is why they are used with a bounded node set or truncated. `[PROVE]`
3.4.5 **Hybrid logical clocks (HLC):** physical time in the high bits, a logical counter in the
      low bits; close to wall-clock, monotonic, and causality-respecting. Used by CockroachDB
      and others. `[SOURCE]` `[RESEARCH]`
3.4.6 **TrueTime:** an interval `[earliest, latest]` rather than a point, backed by GPS and atomic
      clocks; Spanner commits by waiting out the uncertainty (`commit wait`) so that a timestamp
      is definitely in the past before the write is visible. ε has been reported around 7 ms.
      `[SOURCE]` `[PROVE]` `[NUM]` `[RESEARCH]`
3.4.7 The commit-wait proof sketch: if every transaction waits until `TT.after(s)`, then a later
      transaction's timestamp necessarily exceeds an earlier dependent one's, giving external
      consistency. `[PROVE]` `[SOURCE]`
3.4.8 CockroachDB's alternative: a configured `max_offset` (500 ms by default) with an
      **uncertainty interval**; reads that encounter a value inside the interval restart at a
      higher timestamp. Cheaper hardware, occasional retries. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.9 The design consequence: **synchronised clocks buy you cheaper coordination**, and the price
      is either special hardware or restarts. `[SAY]`
3.4.10 **Last-write-wins on wall clocks** as the default conflict resolver, and its exact failure:
       a node with a fast clock wins every conflict and silently deletes the other node's writes.
       `[PROVE]` `[TRAP]`
3.4.11 Clock skew as an *availability* bug too: certificate validation, token expiry, and lease
       expiry all break when clocks disagree.
3.4.12 What to monitor: clock offset per host, NTP sync status, and the rate of
       uncertainty-restarts if your store has them. `[X-REF 20]`

*(12 leaves)*

## §3.5 CRDTs

3.5.1 The requirement: a merge function that is **commutative, associative and idempotent** (a
      join semilattice), so replicas converge regardless of message order or duplication.
      `[PROVE]`
3.5.2 **State-based (CvRDT)** vs **operation-based (CmRDT)**: ship the whole state and join, versus
      ship operations that commute and require reliable causal delivery. `[RESEARCH]`
3.5.3 **G-Counter:** a vector of per-replica counters; merge is element-wise max; value is the sum.
      `[PROVE]` `[BUILD]`
3.5.4 **PN-Counter:** two G-Counters (increments and decrements). `[BUILD]`
3.5.5 **G-Set, 2P-Set** and the reason 2P-Set cannot re-add a removed element. `[PROVE]`
3.5.6 **LWW-Register** and **LWW-Element-Set**: simple, and they inherit every wall-clock problem
      from §3.4.10.
3.5.7 **OR-Set (observed-remove):** tag each add with a unique ID and remove only observed tags,
      so a concurrent add wins over a remove — the semantics the Dynamo cart wanted. `[PROVE]`
3.5.8 Sequence CRDTs for collaborative text (RGA, YATA/Yjs, Automerge) and the tombstone-growth
      and interleaving problems they must solve. `[RESEARCH]`
3.5.9 **OT vs CRDT** for collaborative editing: OT needs a central server and transforms
      operations against concurrent ones; CRDTs need no server but carry metadata overhead.
      Server-authoritative editors historically chose OT; local-first and P2P products choose
      CRDTs. `[RESEARCH]`
3.5.10 The costs nobody mentions in interviews: metadata growth, tombstones needing garbage
       collection, and the fact that convergence is not the same as *correct business semantics*
       (two convergent replicas can agree on an outcome the user did not intend). `[TRAP]`
3.5.11 Where CRDTs actually appear in production: Redis Enterprise active-active, Riak data types,
       Automerge/Yjs in editors, and presence/counter use cases. `[RESEARCH]`
3.5.12 The interview rule: reach for a CRDT only when multi-writer concurrency on the same key is
       *unavoidable*; the cheaper answer is almost always single-writer-per-key (§1.26.4).
       `[SAY]`

*(12 leaves)*

## §3.6 Storage-engine facts that decide designs

3.6.1 **B-tree vs LSM** as the read/write-amplification trade: B-trees pay write amplification on
      random inserts and give predictable reads; LSM trees give fast sequential writes and pay in
      read amplification and compaction. `[PROVE]` `[X-REF 09]`
3.6.2 Why this decides the ID scheme (§1.22.4) and the partition key (§1.13).
3.6.3 Compaction as an operational failure mode: write stalls, disk-space spikes to 2× during a
      major compaction, and the tail latency it injects. `[PROVE]`
3.6.4 Bloom filters inside the storage engine, and why a point read on a missing key is cheap in a
      well-tuned LSM. `[X-REF 09]`
3.6.5 WAL/redo log as the durability primitive, `fsync` as the real cost, and group commit as the
      throughput fix. `[PROVE]` `[X-REF 09]`
3.6.6 Page cache and buffer pool: the reason "warm" and "cold" latencies differ by 100×, and the
      reason a restart is a latency incident. `[NUM]`
3.6.7 MVCC and the long-running-transaction hazard (bloat, vacuum, snapshot retention).
      `[X-REF 09]`
3.6.8 Connection concurrency limits as the constraint that turns into a pooling design: a database
      handles far fewer concurrent connections than you have application threads, hence pooling,
      hence pool saturation as a leading indicator. `[PROVE]` `[X-REF 09]`
3.6.9 Columnar storage: column pruning, run-length and dictionary compression, and vectorised
      execution — why an analytics query is 100× cheaper there. `[PROVE]`
3.6.10 Inverted index mechanics enough to design around: analysis at index time, posting lists,
       segment merges, and near-real-time refresh interval as the freshness knob. `[RESEARCH]`
3.6.11 Object storage internals worth knowing: metadata service separate from data, erasure coding
       for durability, per-prefix scaling, and the consistency semantics of PUT/GET/LIST.
       `[RESEARCH]` `[CURRENCY]`
3.6.12 Erasure coding vs replication arithmetic: 3× replication is 200% overhead; a (10,4)
       Reed–Solomon scheme is 40% overhead for a comparable durability target, at the cost of
       reconstruct-on-read for degraded objects. `[PROVE]` `[NUM]` `[RESEARCH]`

*(12 leaves)*

## §3.7 Log/broker internals that bear on composition

3.7.1 The partitioned append-only log as the data structure: ordering per partition only,
      offsets as the consumer's cursor, retention by time or size. `[X-REF 14]`
3.7.2 Replication and ISR: `acks=all` plus `min.insync.replicas=2` on RF=3 as the durable
      configuration, and what each weaker setting actually risks. `[SOURCE]` `[NUM]`
      `[RESEARCH]` `[X-REF 14]`
3.7.3 Why RF=3/min.insync=2 and not RF=3/min.insync=3: the latter loses availability the moment
      one broker restarts. `[PROVE]` `[NUM]`
3.7.4 The idempotent producer (sequence numbers per producer/partition) and transactions
      (atomic multi-partition writes plus consumer offsets), and the exact guarantee boundary.
      `[X-REF 14]` `[RESEARCH]`
3.7.5 Consumer groups, rebalancing and the stop-the-world pause it causes; cooperative rebalancing
      as the mitigation. `[X-REF 14]` `[RESEARCH]`
3.7.6 Partition count as a design decision with a one-way-door quality: it sets maximum consumer
      parallelism, and increasing it breaks key→partition affinity. `[PROVE]` `[TRAP]`
3.7.7 Log compaction as the mechanism that turns a topic into a materialisable table.
3.7.8 Tiered storage and KRaft as the 2026-era changes to the retention and operations story.
      `[CURRENCY]` `[RESEARCH]`
3.7.9 Zero-copy and sequential I/O as the reason a broker sustains ~100 MB/s per node on
      unremarkable hardware. `[PROVE]`
3.7.10 Queue-family contrasts that matter at design time: visibility timeout and per-message ack
       (SQS), per-message TTL and DLQ routing (RabbitMQ/SQS), FIFO queues' throughput ceiling, and
       the absence of replay in a classic queue. `[X-REF 14]` `[CURRENCY]`

*(10 leaves)*

## §3.8 Edge, CDN and network internals that change a design

3.8.1 Anycast routing and why a CDN's "nearest PoP" is a BGP property, not a geography one.
      `[X-REF 10]`
3.8.2 TLS termination at the edge and session resumption as the reason edge termination cuts
      perceived latency by a full RTT or more. `[PROVE]` `[X-REF 10]`
3.8.3 Connection reuse and HTTP/2 multiplexing at the edge, and HTTP/3/QUIC's head-of-line-blocking
      fix for lossy mobile networks. `[X-REF 10]`
3.8.4 CDN cache-key composition, `Vary`, and the cardinality explosion that destroys hit ratio.
      `[TRAP]` `[X-REF 15]`
3.8.5 Origin shield / tiered caching as the mechanism that stops N PoPs each missing to origin.
      `[PROVE]`
3.8.6 Cache-control semantics that matter: `max-age`, `s-maxage`, `immutable`,
      `stale-while-revalidate`, `stale-if-error` — the last two being the graceful-degradation
      primitives of the web. `[SOURCE]` `[X-REF 12]`
3.8.7 Range requests, conditional requests (`ETag`/`If-None-Match`) and 304s as bandwidth control.
      `[SOURCE]` `[X-REF 12]`
3.8.8 Why a CDN cannot help you: personalised responses, authenticated content without careful key
      design, and write traffic.
3.8.9 TCP behaviours with design consequences: slow start (small responses never reach full
      bandwidth), congestion control, and the bandwidth-delay product for bulk transfer.
      `[X-REF 10]`
3.8.10 Ephemeral port and TIME_WAIT exhaustion on a busy proxy tier as a real capacity ceiling.
       `[X-REF 10]`

*(10 leaves)*

## §3.9 Rate-limiter and admission-control internals

3.9.1 Token bucket as a lazily-evaluated integral: tokens = min(B, tokens + (now − last)·R), so
      no timer thread is needed. Prove the equivalence to continuous refill. `[PROVE]` `[BUILD]`
3.9.2 The fixed-window boundary proof: `limit` requests at the end of window k plus `limit` at the
      start of k+1 gives 2× the limit inside one window-length interval. `[PROVE]` `[NUM]`
3.9.3 Sliding-window-counter weighting: `count = curr + prev · (1 − elapsed/window)`, and the
      bounded error of the approximation. `[PROVE]` `[BUILD]`
3.9.4 Sliding-window log with a Redis sorted set: `ZREMRANGEBYSCORE` then `ZCARD` then `ZADD`,
      atomic in one Lua script, and the memory cost. `[BUILD]`
3.9.5 Why the check-and-decrement must be atomic, with the interleaving that leaks the limit
      written out step by step. `[PROVE]` `[TRAP]`
3.9.6 Redis Lua atomicity guarantees and the `EVALSHA` caching, plus the cluster constraint that
      all keys touched must hash to one slot. `[SOURCE]` `[TRAP]` `[X-REF 15]`
3.9.7 Clock source for the limiter: Redis `TIME` inside the script rather than each client's clock,
      or the limit skews with client drift. `[TRAP]`
3.9.8 Distributed token bucket with local caching: each instance leases a batch of tokens, refills
      when low, and returns unused ones — reducing Redis round trips at the cost of burst
      precision. `[PROVE]` `[BUILD]`
3.9.9 GCRA (generic cell rate algorithm) as the O(1)-state exact alternative to token bucket, used
      in several production limiters. `[RESEARCH]`
3.9.10 Adaptive concurrency limiting (AIMD or gradient-based, Little's-law-derived) as the
       self-tuning alternative to a fixed rate. `[RESEARCH]` `[PROVE]`
3.9.11 The circuit breaker's internal state machine and storage: a ring bit buffer or a
       time-bucketed rolling window, the minimum-calls guard that prevents tripping on two
       samples, and the half-open permit counter. `[BUILD]` `[RESEARCH]`

*(11 leaves)*

## §3.10 Queueing theory, enough of it

3.10.1 **Little's law** L = λW: derivation sketch and the three applications (§2.3.10). `[PROVE]`
3.10.2 M/M/1 utilisation law: W = S/(1−ρ). Tabulate ρ = 0.5, 0.7, 0.8, 0.9, 0.95, 0.99 against the
      latency multiplier 2×, 3.3×, 5×, 10×, 20×, 100×. `[PROVE]` `[NUM]`
3.10.3 The consequence stated for the interview: **the knee is real and it is near 70–80%**, which
      is why capacity headroom is not waste. `[SAY]`
3.10.4 Multi-server (M/M/c) intuition: pooling servers beats partitioning them, which is the
      queueing argument for a shared pool over per-client pools — and bulkheads are the
      *deliberate* violation of it for isolation. `[PROVE]`
3.10.5 Variability's effect: high service-time variance inflates queueing far beyond the
      exponential model, which is why one slow endpoint poisons a shared pool. `[PROVE]`
3.10.6 **Universal scalability law** as the correction to linear scaling: contention plus coherency
      makes throughput peak and then *decline* with added concurrency. `[PROVE]` `[RESEARCH]`
      `[X-REF 05]`
3.10.7 Amdahl's law as the ceiling on parallel speedup, applied to a request that has a serial
      section. `[PROVE]` `[X-REF 05]`
3.10.8 Open vs closed systems, and why the distinction is the root of coordinated omission
      (§1.29.9). `[PROVE]`
3.10.9 Batching as a latency/throughput dial: batching raises throughput and adds up to one
      batch-interval of latency; the optimum depends on where you are on the utilisation curve.
      `[PROVE]`
3.10.10 Queue depth vs age: age (time-in-queue) is the actionable signal because it maps directly
        onto the client's deadline. `[SAY]`

*(10 leaves)*

## §3.11 The named failure pathologies

3.11.1 **Thundering herd:** N waiters woken for one resource; in a design it is N clients refilling
      one expired cache key. Fix: single-flight, jittered TTL, early refresh. `[X-REF 15]`
3.11.2 **Cache stampede** as the specific case, with the arithmetic of how much origin load one
      popular key produces. `[PROVE]`
3.11.3 **Retry storm:** the amplification loop of §1.25.9 plus the client's own timeout, ending in
      more traffic during the failure than before it. `[PROVE]`
3.11.4 **Metastable failure:** trigger + sustaining effect + a degraded equilibrium that survives
      the trigger's removal; retries are the sustaining effect in the majority of studied
      incidents. `[SOURCE]` `[RESEARCH]`
3.11.5 **Cascading failure:** the positive-feedback growth pattern, its triggers, and its
      recovery steps (§2.10.7–§2.10.12). `[SOURCE]`
3.11.6 **Grey failure** and differential observability (§2.11.5). `[SOURCE]`
3.11.7 **The health-check death spiral** (§2.11.11).
3.11.8 **Head-of-line blocking** at three layers: TCP (fixed by HTTP/3), a single-threaded consumer
      on one poison message, and a shared thread pool with one slow dependency. `[X-REF 10]`
3.11.9 **Poison message / poison pill:** one message that kills every consumer that touches it, and
      the DLQ + attempt-count design that contains it. `[X-REF 14]`
3.11.10 **Hot shard / celebrity** (§1.16.10) and **noisy neighbour** (§2.5.4).
3.11.11 **Split brain** (§1.15.13) and the data-divergence cleanup it forces.
3.11.12 **Deployment-correlated failure:** one bad config or binary reaching every instance because
        the rollout was fast and global. `[PROVE]`
3.11.13 **Expiry-correlated failure:** certificates, tokens, licences and leases expiring
        simultaneously because they were issued simultaneously. `[TRAP]`
3.11.14 **Dependency-cycle deadlock:** service A waits on B waits on A, usually via a shared
        cache or an auth service. `[SOURCE]`
3.11.15 **Unbounded growth:** an unbounded queue, an unbounded retry list, an unbounded in-memory
        cache — each converts a load problem into an OOM. `[TRAP]`
3.11.16 **Slow drift into failure:** a table that grew past its index's working set, a partition
        that grew past its node, a retention policy nobody enforced. The absence of a
        capacity-forecast alert is the root cause.

*(16 leaves)*

## §3.12 Case studies from real postmortems

3.12.1 The 2017 object-storage control-plane outage: a mistyped operational command removed far
      more capacity than intended, and the subsystems required a full restart that had not been
      exercised at that scale for years. Lessons: blast-radius limits on operational tooling,
      and *tested* restart paths. `[SOURCE]` `[RESEARCH]`
3.12.2 The 2019 edge-WAF regex outage: a rule with catastrophic backtracking deployed globally
      exhausted CPU across the fleet in seconds. Lessons: global config is a deploy, staged
      rollout applies to rules, and CPU-bound user input needs a bounded evaluator. `[SOURCE]`
      `[RESEARCH]`
3.12.3 The 2021 multi-day game-platform outage attributed to a service-discovery/streaming
      subsystem plus a storage-engine pathology under load: a textbook metastable failure that did
      not recover when load was removed. Lessons: recovery requires load reduction, and a
      coordination layer is a correlated dependency for everything. `[SOURCE]` `[RESEARCH]`
3.12.4 A major-provider DNS/control-plane incident as the "everything depends on one thing" case
      study, and the design response of static stability (data plane keeps working when the
      control plane is down). `[RESEARCH]` `[CURRENCY]`
3.12.5 The pattern extraction across all of them: the trigger is boring, the amplifier is a
      feedback loop, and the recovery is slower than anyone modelled. `[SAY]`
3.12.6 **Static stability** as the design principle those incidents produced: the data plane must
      continue with its last-known-good state when the control plane is unavailable. `[SOURCE]`
      `[RESEARCH]`
3.12.7 The postmortem discipline itself: blameless, with a timeline, contributing factors, and
      action items that have owners — and the fact that "add more monitoring" is rarely a real
      action item. `[X-REF 20]`
3.12.8 How to use a case study in an interview: one sentence of incident, one sentence of
      mechanism, one sentence of what you would design differently. Longer than that is
      story-telling. `[SAY]`

*(8 leaves)*

---

# PART 4 — BUILD IT

Every `[BUILD]` in this part is complete, compiling, generic Java 21 (records, sealed types,
pattern matching, `java.time`, virtual threads where relevant), followed by a **Diff vs the real
one** table naming the production library it mirrors. Every diff table must cover, at minimum:
bounds/argument checking, thread-safety and memory-visibility, metrics/observability hooks,
configuration surface, allocation behaviour, and the failure mode the real one handles that the
teaching version does not.

## §4.1 Consistent-hash ring with virtual nodes

4.1.1 `ConsistentHashRing<N>` over a `NavigableMap<Long, N>`, with `add(node, weight)`,
      `remove(node)`, `get(key)`, and `getReplicas(key, r)` skipping duplicate physical nodes.
      `[BUILD]`
4.1.2 Pluggable 64-bit hash (MurmurHash3 or a seeded `HashFunction` interface), and the vnode
      naming scheme `node#i`. `[BUILD]`
4.1.3 A test that measures key-distribution standard deviation at V = 1, 10, 100, 256 and prints
      the imbalance — turning §3.1.4 into an experiment. `[PROVE]` `[NUM]`
4.1.4 A test that measures the fraction of keys remapped when one node of N is removed, showing
      ~1/N. `[PROVE]`
4.1.5 A weighted variant and a bounded-load variant (cap = ⌈(1+ε)·avg⌉ with forward-on-full).
      `[BUILD]`
4.1.6 A rendezvous-hashing implementation of the same interface for comparison, with a benchmark
      of lookup cost against the ring at N = 10, 100, 1000. `[BUILD]` `[NUM]`
4.1.7 **Diff vs the real one** (Cassandra's token ring / Envoy's ring-hash): token allocation
      algorithms that minimise variance rather than random placement, rack/AZ-aware replica
      selection, ring state distributed by gossip and versioned, ring size and hash choice
      configurable, and the ring being consulted by the *coordinator* rather than by a client
      library.

*(7 leaves)*

## §4.2 Rate limiters

4.2.1 `TokenBucket` with lazy refill: `long tokens`, `long lastRefillNanos`, `tryAcquire(int)`,
      built on a `synchronized` block first and then on a CAS loop, with the difference measured.
      `[BUILD]` `[X-REF 05]`
4.2.2 `FixedWindowLimiter` — deliberately included so the 2× boundary violation can be
      demonstrated by a test that sends `limit` requests at t=59s and `limit` at t=61s.
      `[BUILD]` `[PROVE]`
4.2.3 `SlidingWindowCounterLimiter` implementing `curr + prev·(1 − elapsed/window)`. `[BUILD]`
4.2.4 `SlidingWindowLogLimiter` over a `Deque<Long>` with trim-on-access, plus its memory
      measurement. `[BUILD]` `[NUM]`
4.2.5 `LeakyBucketLimiter` as a fixed-rate drain with a bounded queue, to contrast smoothing
      against bursting. `[BUILD]`
4.2.6 `RedisTokenBucketLimiter`: the Lua script (read tokens+timestamp, refill from server `TIME`,
      conditionally decrement, write back with an expiry), the Java wrapper with `EVALSHA` and a
      `NOSCRIPT` fallback, and the returned `(allowed, remaining, retryAfterMillis)` triple.
      `[BUILD]` `[SOURCE]`
4.2.7 A concurrency test proving the non-atomic GET-then-SET version leaks the limit under N
      threads, and that the Lua version does not. `[PROVE]` `[TRAP]`
4.2.8 A local-lease layer on top: lease K tokens from Redis, spend locally, return the remainder —
      with the burst-precision cost measured. `[BUILD]` `[PROVE]`
4.2.9 A Spring Boot 3.x `HandlerInterceptor` (or `WebFilter`) that applies the limiter by API key,
      returns 429 with `Retry-After` and the `X-RateLimit-*` headers, and exposes Micrometer
      counters for allowed/denied. `[BUILD]` `[X-REF 20]`
4.2.10 **Diff vs the real one** (Bucket4j, Resilience4j `RateLimiter`, Envoy's global rate limit
       service): pluggable distributed backends with async token pre-fetch, verified-atomic
       scripts per backend, hierarchical/multi-bandwidth buckets, configurable refill strategies
       (greedy vs intervally), a metrics and event API, and the sharding/hash-tag handling needed
       under Redis Cluster.

*(10 leaves)*

## §4.3 Snowflake ID generator

4.3.1 `SnowflakeIdGenerator` with the exact bit layout: 1 unused sign bit, 41 timestamp bits from a
      custom epoch, 10 node bits, 12 sequence bits; the shift and mask constants named
      (`TIMESTAMP_SHIFT = 22`, `NODE_SHIFT = 12`, `SEQUENCE_MASK = 4095`). `[BUILD]` `[NUM]`
4.3.2 Sequence rollover within a millisecond: spin until the next millisecond
      (`tilNextMillis`). `[BUILD]`
4.3.3 Clock-regression handling with all three policies behind a strategy enum: `THROW`,
      `WAIT_UNTIL_CAUGHT_UP` (bounded), `BORROW_SEQUENCE_BITS`. `[BUILD]` `[TRAP]`
4.3.4 Thread safety: a `synchronized` generate method versus a per-thread generator with distinct
      node IDs, with the throughput difference measured. `[BUILD]` `[X-REF 05]`
4.3.5 Node-ID assignment: a pluggable `NodeIdProvider` with an ephemeral-znode/etcd-lease
      implementation sketch and a hostname-hash fallback that documents its collision risk.
      `[BUILD]` `[TRAP]`
4.3.6 A decoder that turns an ID back into `(Instant, nodeId, sequence)` — the operational tool
      that makes debugging possible. `[BUILD]`
4.3.7 A `UUIDv7` generator alongside it, plus a JMH-style comparison of insert performance into a
      B-tree-indexed table for v4, v7 and Snowflake. `[BUILD]` `[PROVE]` `[NUM]` `[X-REF 09]`
4.3.8 **Diff vs the real one** (Twitter/X's original Snowflake, Sonyflake, `java.util.UUID` v7 in
      the JDK, database `UUIDv7()` functions): ZooKeeper-backed worker-ID leases with liveness,
      different bit splits for different lifetimes, monotonic-per-process guarantees under
      concurrency, and the JDK's use of a cryptographically strong random source.

*(8 leaves)*

## §4.4 Idempotency store

4.4.1 The schema: `idempotency_key PK`, `tenant_id`, `endpoint`, `request_fingerprint`, `status`,
      `response_body`, `response_status`, `created_at`, `expires_at`, with a unique constraint that
      is the actual concurrency control. `[BUILD]`
4.4.2 `IdempotencyService.execute(key, fingerprint, Supplier<Result>)` implementing insert-first:
      attempt `INSERT ... IN_PROGRESS`, catch the duplicate-key exception, then branch on the
      existing row's status. `[BUILD]` `[TRAP]`
4.4.3 The three branches: `COMPLETED` → replay the stored response; `IN_PROGRESS` and lease valid
      → 409/425 with `Retry-After`; `IN_PROGRESS` and lease expired → take over. `[BUILD]`
4.4.4 Fingerprint mismatch → 422, so the same key with a different body is a client error and not
      a silent wrong replay. `[BUILD]` `[TRAP]`
4.4.5 Transaction boundaries done correctly with Spring `@Transactional`, including the
      `REQUIRES_NEW` needed for the key row when the effect calls an external system.
      `[BUILD]` `[X-REF 08]`
4.4.6 A concurrency test with two threads and one key, asserting exactly one effect. `[PROVE]`
4.4.7 A reaper for expired rows, and the arithmetic for sizing the table (§1.21.11). `[BUILD]`
      `[NUM]`
4.4.8 **Diff vs the real one** (Stripe's idempotency layer): idempotency scoped per API key with
      published 24-hour semantics, request-fingerprint conflict as a documented error code,
      results stored for replay including the error responses, and coverage of the case where the
      original request is still running.

*(8 leaves)*

## §4.5 Transactional outbox plus relay

4.5.1 The `outbox` table: `id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload`,
      `created_at`, `published_at`, `attempts`, `claimed_by`, `claimed_until`. `[BUILD]`
4.5.2 The producer side: a repository method that writes the domain change and the outbox row in
      one `@Transactional` unit, with a test that proves rolling back loses both. `[BUILD]`
      `[PROVE]`
4.5.3 The poller relay: `SELECT ... WHERE published_at IS NULL ORDER BY id FOR UPDATE SKIP LOCKED
      LIMIT 100`, publish, mark published; with the `SKIP LOCKED` explained as the reason multiple
      relays do not collide. `[BUILD]` `[SOURCE]` `[X-REF 09]`
4.5.4 Ordering: per-aggregate ordering preserved by using the aggregate ID as the message key, and
      the explicit acknowledgement that global ordering is not preserved. `[BUILD]` `[PROVE]`
4.5.5 Failure handling: attempt counting, exponential backoff on the row, and a dead-letter status
      with an operator query. `[BUILD]`
4.5.6 At-least-once semantics made safe by pairing with §4.4's dedupe on the consumer side.
      `[BUILD]`
4.5.7 A CDC alternative sketch: the same outbox table read by Debezium, with the routing
      transformation and the reason the payload column shape matters. `[RESEARCH]` `[X-REF 14]`
4.5.8 Latency and load measurement of poll-interval choices (100 ms vs 1 s vs 5 s) against database
      load. `[PROVE]` `[NUM]`
4.5.9 **Diff vs the real one** (Debezium + the Outbox Event Router SMT): reads the WAL rather than
      polling so there is no query load and no added latency, guarantees ordering per partition
      from the log, handles schema changes and snapshots, exposes offsets and restart semantics,
      and survives the connector itself restarting mid-stream.

*(9 leaves)*

## §4.6 Circuit breaker

4.6.1 `CircuitBreaker` with the three states as a sealed interface or enum plus an atomic state
      holder; `decorate(Supplier<T>)` and `execute` entry points. `[BUILD]`
4.6.2 A count-based rolling window as a ring bit buffer (`long[]` bitset plus a cursor), with the
      failure-rate computation. `[BUILD]` `[NUM]`
4.6.3 A time-based rolling window as an array of per-second buckets with lazy eviction. `[BUILD]`
4.6.4 Configurable: `failureRateThreshold`, `slowCallDurationThreshold`, `slowCallRateThreshold`,
      `minimumNumberOfCalls`, `waitDurationInOpenState`, `permittedNumberOfCallsInHalfOpenState`.
      `[BUILD]` `[RESEARCH]`
4.6.5 Half-open admission control with a permit counter, so exactly N probes go through and the
      rest fail fast. `[BUILD]`
4.6.6 Which exceptions count as failures (`recordExceptions` / `ignoreExceptions`), because
      counting a 404 as a failure is how a breaker trips on normal traffic. `[BUILD]` `[TRAP]`
4.6.7 Thread-safe state transitions under concurrency, and a test that hammers the breaker from
      many virtual threads to prove no double-transition. `[PROVE]` `[X-REF 05]`
4.6.8 Metrics: state gauge, transition counter, calls-not-permitted counter, wired to Micrometer.
      `[BUILD]` `[X-REF 20]`
4.6.9 **Diff vs the real one** (Resilience4j `CircuitBreaker`): a lock-free state machine with
      immutable metric snapshots, `Registry` with shared configuration and events, integration
      with retry/bulkhead/time-limiter decorators in a defined order, reactive and functional
      adapters, and the Spring Boot starter's actuator endpoints.

*(9 leaves)*

## §4.7 Retry with full jitter and a retry budget

4.7.1 `RetryPolicy` record: `maxAttempts`, `baseDelay`, `maxDelay`, a `Predicate<Throwable>` for
      retryability, and a `JitterStrategy` enum (`NONE`, `EQUAL`, `FULL`, `DECORRELATED`).
      `[BUILD]`
4.7.2 The four delay formulas implemented side by side, with a simulation that plots the request
      distribution over time for 1,000 synchronised clients under each. `[BUILD]` `[PROVE]`
      `[NUM]`
4.7.3 `RetryBudget` as a token bucket over successes: retries permitted only while
      `retries ≤ ratio × successes`, with the 10% convention as the default. `[BUILD]` `[SOURCE]`
4.7.4 Deadline propagation: a `Deadline` carried in a `ScopedValue`, checked before each attempt,
      so a retry that cannot finish within the caller's budget is not attempted. `[BUILD]`
      `[X-REF 04]` `[X-REF 05]`
4.7.5 Non-retryable classification: 4xx except 408/429, `IllegalArgumentException`, and any
      non-idempotent operation without an idempotency key — enforced at the type level if
      possible. `[BUILD]` `[TRAP]`
4.7.6 A simulation of retry amplification across three layers proving the 27× figure, and the same
      simulation with a budget showing the amplification bounded. `[PROVE]` `[NUM]`
4.7.7 **Diff vs the real one** (Resilience4j `Retry`, the AWS SDK v2 retry strategies, gRPC's
      retry policy with `RetryThrottling`): server-driven backoff hints, per-attempt vs per-call
      timeouts, transaction-level throttling shared across clients in a channel, retry-after
      header handling, and integration with the client's own circuit breaker.

*(7 leaves)*

## §4.8 Cursor pagination

4.8.1 `Cursor` record of `(Instant createdAt, long id)` with base64url encoding/decoding, plus an
      optional HMAC so a client cannot forge or mutate one. `[BUILD]`
4.8.2 The repository query with the row-value comparison
      `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC LIMIT :n+1`, and the
      `n+1` trick for `hasMore`. `[BUILD]` `[X-REF 09]`
4.8.3 Encoding the sort and filter set into the cursor so a client cannot change them mid-scan.
      `[BUILD]` `[TRAP]`
4.8.4 Bidirectional paging and the reversed-order query for `before`. `[BUILD]`
4.8.5 A benchmark against `OFFSET` at page 1, 100, 1,000 and 10,000 showing constant vs linear
      cost. `[PROVE]` `[NUM]`
4.8.6 A test that inserts rows mid-pagination and demonstrates the skip/duplicate behaviour of
      offset and its absence with a cursor. `[PROVE]` `[TRAP]`
4.8.7 **Diff vs the real one** (Spring Data's `Window`/`ScrollPosition` keyset pagination, the
      GraphQL Relay connection spec): typed keyset abstractions over arbitrary sort orders,
      automatic derivation from the sort specification, `PageInfo` with both cursors, and index
      requirements validated at query-construction time.

*(7 leaves)*

## §4.9 Bloom filter and HyperLogLog

4.9.1 `BloomFilter` over a `long[]` bitset with k derived hashes from two 64-bit hashes
      (Kirsch–Mitzenmacher double hashing: `h_i = h1 + i·h2`). `[BUILD]` `[PROVE]`
4.9.2 Constructor from `(expectedInsertions, falsePositiveRate)` computing m and k from the
      formulas in §2.3.13, with the computed values exposed. `[BUILD]` `[NUM]`
4.9.3 An empirical false-positive-rate test at the design load, asserting it lands within tolerance
      of the predicted rate. `[PROVE]`
4.9.4 `HyperLogLog` with `p = 14` (16,384 registers), the leading-zero-count register update, the
      harmonic-mean estimator with α_m, the small-range linear-counting correction, and `merge`.
      `[BUILD]` `[PROVE]` `[NUM]`
4.9.5 An accuracy test across cardinalities 10², 10⁴, 10⁶ asserting the error stays near
      1.04/√m. `[PROVE]` `[NUM]`
4.9.6 A `CountMinSketch` with `(depth, width)` derived from (ε, δ), plus a heavy-hitters wrapper
      that uses it for hot-key detection (§1.16.15). `[BUILD]`
4.9.7 **Diff vs the real one** (Guava `BloomFilter`, Redis `BF.*`/`PFADD`/`PFCOUNT`,
      stream-lib/Apache DataSketches): serialisation formats that survive version changes, sparse
      and dense HLL encodings with automatic promotion, SIMD-optimised register updates, strategy
      versioning for hash-function compatibility, and mergeability across language
      implementations.

*(7 leaves)*

## §4.10 Conflict resolution: LWW vs version vectors vs CRDT

4.10.1 `Versioned<T>` with an LWW merge on `(timestamp, nodeId)` tiebreak, and a test that
       demonstrates data loss under a skewed clock. `[BUILD]` `[PROVE]` `[TRAP]`
4.10.2 `VersionVector` as a `Map<NodeId, Long>` with `happensBefore`, `concurrentWith`, `merge`,
       and `increment`. `[BUILD]` `[PROVE]`
4.10.3 A shopping-cart replica type using version vectors that returns *siblings* on concurrent
       writes and an application-supplied merge to resolve them. `[BUILD]`
4.10.4 `GCounter` and `PNCounter` with `merge`, plus a randomised convergence test that applies
       operations in permuted orders and asserts identical final state. `[BUILD]` `[PROVE]`
4.10.5 `ORSet` with add-tags and observed-remove semantics, and the test that shows a concurrent
       add beating a remove — contrasted with `2PSet` failing the same test. `[BUILD]` `[PROVE]`
4.10.6 A tombstone-growth measurement over 10⁶ add/remove cycles, making the CRDT cost concrete.
       `[PROVE]` `[NUM]` `[TRAP]`
4.10.7 **Diff vs the real one** (Riak data types, Redis Enterprise CRDTs, Automerge/Yjs): delta
       state propagation instead of full state, causal-context compression, garbage collection of
       tombstones under a stability threshold, binary encodings tuned for size, and integration
       with the replication layer's causal-delivery guarantees.

*(7 leaves)*

## §4.11 Quorum read/write coordinator

4.11.1 A `Replica` interface (`get`, `put(value, version)`) with an in-memory implementation that
       can be told to be slow, to fail, or to partition. `[BUILD]`
4.11.2 `QuorumCoordinator` with configurable `N`, `W`, `R`, issuing requests to all N in parallel
       on virtual threads and completing as soon as W (or R) succeed. `[BUILD]` `[X-REF 04]`
4.11.3 Version selection on read: pick the highest version among the R responses; detect siblings
       when versions are concurrent. `[BUILD]`
4.11.4 **Read repair:** asynchronously write the winning value back to any replica that returned a
       stale version. `[BUILD]`
4.11.5 Hinted handoff: when a replica is unreachable, record a hint on a substitute and replay on
       recovery. `[BUILD]`
4.11.6 A Merkle-tree anti-entropy pass between two replicas over a key range. `[BUILD]`
4.11.7 A test suite that empirically demonstrates: `R+W>N` returns the latest write; `R+W≤N` can
       return stale; and a sloppy quorum can return stale even with `R+W>N`. This is the
       experimental version of §1.18.9. `[PROVE]` `[TRAP]`
4.11.8 A latency measurement showing quorum latency tracking a higher percentile than single-node
       latency (§1.18.4). `[PROVE]` `[NUM]`
4.11.9 **Diff vs the real one** (Cassandra's coordinator, DynamoDB's request routers): speculative
       retry policies, per-datacentre consistency levels, digest reads (hash first, full value only
       on mismatch) to save bandwidth, snitch-based replica ordering by latency, and
       throttled/scheduled repair rather than opportunistic repair alone.

*(9 leaves)*

## §4.12 Saga coordinator with compensations

4.12.1 A `SagaStep<C>` record of `(name, Function<C,StepResult> action, Consumer<C> compensation)`
       and a `Saga<C>` that runs steps forward and compensations in reverse on failure. `[BUILD]`
4.12.2 Persistent saga state: a `saga_instance` table with `current_step`, `status`,
       `context_json`, `updated_at`, so the coordinator survives a restart. `[BUILD]`
4.12.3 Idempotent step execution keyed by `(sagaId, stepName)`, reusing §4.4. `[BUILD]`
4.12.4 Compensation failure handling: retry with backoff, then a terminal `COMPENSATION_FAILED`
       state that raises an operator alert — because silently giving up is how money disappears.
       `[BUILD]` `[TRAP]`
4.12.5 Timeouts per step and a sweeper that advances or compensates stuck sagas. `[BUILD]`
4.12.6 A worked QuizStakes-shaped example: reserve inventory → charge payment → confirm order,
       with compensations release-inventory and refund, and a test that fails at each step in turn
       and asserts the compensating path. `[BUILD]` `[PROVE]`
4.12.7 The reservation/escrow variant (§2.7.10) implemented as a TTL hold, showing it needs no
       compensation for the timeout case. `[BUILD]`
4.12.8 **Diff vs the real one** (Temporal/Cadence, AWS Step Functions, Axon/Eventuate): durable
       execution with an event-sourced history and deterministic replay rather than a state
       column, built-in timers and signals, versioning of running workflows, visibility and
       query APIs, and horizontal scaling of the worker fleet with task queues.

*(8 leaves)*

## §4.13 Fan-out feed service

4.13.1 A `FanoutService` that, on post, reads the follower list in pages and enqueues per-follower
       feed writes, with a follower-count threshold above which it skips fan-out. `[BUILD]`
4.13.2 The feed store as a capped Redis ZSET per user (score = timestamp or Snowflake ID), with
       `ZADD` + `ZREMRANGEBYRANK` to cap at 1,000. `[BUILD]` `[X-REF 15]`
4.13.3 The read path: range-read IDs, batch multi-get bodies, merge celebrity authors' recent posts
       at read time, dedupe and sort. `[BUILD]`
4.13.4 The inactive-user optimisation: skip materialisation past a threshold, lazily backfill on
       return. `[BUILD]`
4.13.5 A benchmark of push vs pull vs hybrid over a synthetic follower distribution (Zipf), showing
       the crossover point. `[PROVE]` `[NUM]`
4.13.6 **Diff vs the real one** (production feed systems): ranking as a separate scoring service,
       feed storage in a purpose-built store rather than Redis alone, multi-tier caching of post
       bodies, per-follower delivery policies, and fan-out workers partitioned by author with
       backpressure into the queue.

*(6 leaves)*

## §4.14 Supporting builds

4.14.1 `SingleFlight` / request coalescing: one in-flight load per key using
       `ConcurrentHashMap<K, CompletableFuture<V>>`, with the removal-on-completion race handled.
       `[BUILD]` `[X-REF 05]` `[X-REF 15]`
4.14.2 A cache-aside loader with jittered TTL and probabilistic early refresh, and the test that
       shows stampede prevention. `[BUILD]` `[PROVE]` `[X-REF 15]`
4.14.3 A `HashRingRouter` that maps a key to a shard and a `ShardedRepository` façade, so the
       scatter-gather path can be measured. `[BUILD]`
4.14.4 A scatter-gather executor on virtual threads with a hard deadline and partial-result
       semantics, demonstrating the tail-inflation arithmetic of §1.16.17 empirically. `[BUILD]`
       `[PROVE]` `[X-REF 04]`
4.14.5 A hedged-request executor: issue the second call after the measured p95, cancel the loser,
       and measure the p99 improvement and the added load. `[BUILD]` `[PROVE]` `[NUM]`
4.14.6 A base62 encoder/decoder plus a bijective scramble (a Feistel network or multiplicative
       inverse mod 62⁷) for the URL shortener. `[BUILD]` `[PROVE]`
4.14.7 A counter-block allocator: a `counter_ranges` table, `SELECT ... FOR UPDATE`-free allocation
       via an atomic `UPDATE ... RETURNING`, and in-process consumption of a 10⁶ block. `[BUILD]`
4.14.8 A hierarchical timing wheel for the scheduler design, with `O(1)` insert and tick.
       `[BUILD]` `[RESEARCH]`
4.14.9 A `Deadline`/budget propagation utility using `ScopedValue`, plus a filter that reads and
       writes the deadline header at the service boundary. `[BUILD]` `[X-REF 04]`
4.14.10 A load-shedding filter: reject when in-flight concurrency exceeds a limit, by request
        priority read from a header, returning 503 with `Retry-After`, and exporting the shed
        rate. `[BUILD]` `[X-REF 20]`
4.14.11 A geohash encoder plus a neighbour-cell expansion for a proximity query. `[BUILD]`
4.14.12 A backfill runner: keyset-ranged, resumable via a checkpoint row, rate-limited by the
        limiter of §4.2, with a pause flag. `[BUILD]`

*(12 leaves)*

---

# PART 5 — INTERVIEW, WORKED DESIGNS AND RETENTION

## §5.1 Delivery mechanics — the language that scores

5.1.1 **Assumption, stated:** "You haven't given me DAU, so I'll assume 10 M with a 3× peak factor
      — tell me if that's off, because it changes whether we shard." `[SAY]`
5.1.2 **Derivation, not assertion:** "1,000 writes/s against ~10k/s per primary means one primary
      is fine for now; I'd revisit at 5,000." `[SAY]`
5.1.3 **Trade-off, both sides:** "Eventual consistency for the follower count buys a 10 ms read
      instead of a quorum round trip; the cost is a count that can be 30 seconds stale, which the
      product tolerates. I would not make that choice for the account balance." `[SAY]`
5.1.4 **Failure, priced:** "If Redis dies the hit ratio goes to zero and Postgres sees 100× read
      load, so I need an origin circuit breaker and a warm-up path — otherwise the cache is a
      hidden SPOF." `[SAY]`
5.1.5 **Scope, negotiated:** "Search, moderation and analytics are each their own design. I'll
      leave them as named interfaces and go deep on the feed path unless you'd rather I do the
      other." `[SAY]`
5.1.6 **Bottleneck, named:** "The bottleneck is fan-out write volume at peak. The next thing that
      breaks is the fan-out worker pool, and the fix is partitioning by author with more
      consumers." `[SAY]`
5.1.7 **Steering, accepted:** "That's the right question — let me go into hot keys properly."
      Treating the interviewer's question as the rubric. `[SAY]`
5.1.8 **Commitment:** "I'm choosing X. I'd switch to Y if Z happened." Never four options and no
      choice. `[SAY]`
5.1.9 **Correction, cheap:** "I said 2 TB earlier; recomputing, it's 20 TB, which changes the
      sharding answer." Recovering from an arithmetic error is a positive signal, hiding it is
      not. `[SAY]`
5.1.10 **Closing summary:** 60 seconds restating the design, the bottleneck, the top risk and the
       next thing you'd build. Ending well is worth disproportionate credit. `[SAY]`
5.1.11 Narrating while thinking: silence is unscoreable. State the option set, the criterion, and
       the choice.
5.1.12 Managing the board: a fixed region for requirements/numbers, a component diagram, and a
       running list of deferred items you can point at.
5.1.13 Handling "I don't know": name the closest thing you do know, state how you'd find out, and
       move — never invent a mechanism. `[SAY]`
5.1.14 Handling a hostile-sounding challenge: it is usually a probe, not a rejection. Restate the
       trade-off and ask which constraint they want optimised.

*(14 leaves)*

## §5.2 The L5 / L6 rubric difference

5.2.1 L5: the design must be **correct and complete for the stated load**, with major trade-offs
      named and at least two components explored in depth. `[RESEARCH]`
5.2.2 L6: additionally **drive** the conversation, surface non-obvious constraints before being
      asked, reason across systems, and demonstrate operational maturity. `[RESEARCH]`
5.2.3 The L6-specific content axes: scope negotiation, migration from an existing system,
      organisational consequences (who owns the new datastore, what the on-call surface becomes),
      multi-region and blast radius, and cost.
5.2.4 The single most common downlevel reason: an L6 candidate giving an L5-quality answer — a
      correct design with no ownership dimension. `[RESEARCH]` `[TRAP]`
5.2.5 Two design rounds at L6 and above at several companies, with the second typically weighted
      toward operations, scale evolution, or an ambiguous product-shaped problem. `[RESEARCH]`
5.2.6 What "identifies the constraint that drives the design before being pointed at it" looks
      like concretely, per design in §5.3.
5.2.7 The staff-level failure mode of over-abstraction: describing a platform instead of solving
      the problem asked. `[TRAP]`
5.2.8 What does *not* differentiate: knowing more technology names. `[TRAP]`

*(8 leaves)*

## §5.3 The worked-design catalogue

Every design below is a leaf cluster with the same five sub-leaves — **(a) requirements and the
one number that matters, (b) estimation, (c) the key design decision and why, (d) the deep dive an
interviewer will pick, (e) the bottleneck and the failure mode** — plus any design-specific extras
listed. The four designs already in the guide are marked *(existing)* and must be preserved and
expanded, not replaced.

5.3.1 **URL shortener** *(existing)* `[DESIGN]` — 100 M new URLs/day, 100:1 read:write, 5-year
      retention, redirect p99 < 50 ms. Writes 1,000/s (peak 3,000/s), reads 100,000/s (peak
      300k/s), storage 182 B records × ~500 B ≈ 90 TB. Key design: **base62 7 characters**
      (62⁷ ≈ 3.5 × 10¹² vs the 1.8 × 10¹¹ needed) generated from **pre-allocated counter blocks**,
      not a hash prefix — because hashing forces a read-before-write on the hot path and cannot
      give two users distinct keys for the same URL. KV store partitioned by short code;
      cache-first read path (CDN → Redis → store); **301 vs 302** decided by whether click
      analytics is a requirement. Analytics via an event stream, never a counter row at 100k/s.
      Bottleneck: hot-key read fan-out. Extras: custom aliases and the uniqueness check, link
      expiry and reclamation, abuse/malware scanning, and the bijective scramble for
      unguessability. `[PROVE]` `[NUM]`
5.3.2 **News feed** *(existing)* `[DESIGN]` — the one decision is **fan-out on write (push) vs on
      read (pull)**, with the comparison table (post cost, read cost, read latency, celebrity
      problem, inactive users). The answer is **hybrid**: push by default because reads outnumber
      writes ~100:1, exempt accounts above a follower threshold (~100k) and merge their posts at
      read time, and skip materialisation for users inactive 30+ days with lazy backfill.
      Mechanics: post → `posts` → event → fan-out workers → per-follower Redis list/ZSET capped
      at ~1,000, with the authoritative feed in the store; read = range of IDs + batched multi-get
      + celebrity merge. Ranking scoped out of v1 explicitly, or specified as candidate generation
      → feature lookup → scoring → diversity, behind a strict timeout with a chronological
      fallback. Bottleneck: fan-out write volume at peak. `[PROVE]`
5.3.3 **Chat and presence** *(existing)* `[DESIGN]` — the distinguishing property is **long-lived
      connections**, so the stateless-app-tier assumption breaks. WebSocket with long-polling
      fallback; `user_id → gateway_instance` registry in Redis with TTL and heartbeat; messages
      partitioned by `conversation_id` clustered on `(created_at DESC, message_id)`;
      **server-assigned per-conversation monotonic sequence numbers** for ordering, because
      wall-clock ordering across devices is unreliable; at-least-once plus a client-generated
      message ID for dedupe; group fan-out per member with a push→pull switch above a size
      threshold; presence by ~30 s heartbeat with a longer TTL, debounced and batched and pushed
      only for open conversations. Extras: drain and reconnect with jittered backoff, offline
      push, read receipts as a separate higher-volume stream, media messages via pre-signed
      upload, and end-to-end encryption's effect on server-side search. `[PROVE]`
5.3.4 **Payments / ledger** *(existing)* `[DESIGN]` — availability yields to correctness.
      Append-only **double-entry** ledger with balance as a derived value, never `UPDATE balance`;
      integer minor units or `BigDecimal`, never `double`; mandatory idempotency keyed by a
      client-supplied key inserted in the same transaction as the entries; atomicity across
      accounts inside one partition where possible, a **saga with explicit compensations** across
      services with modelled intermediate states (`PENDING`, `HELD`, `SETTLED`, `REVERSED`);
      external gateway timeouts resolved by querying the provider by idempotency key, never blind
      retry; a **daily reconciliation job** against the provider's settlement report as the
      mechanism by which you find out you were wrong; serializable or explicit row locking, and
      PC/EC because double-spending is worse than downtime. Extras: currency and FX,
      partial refunds, chargebacks, hold expiry, and the audit/immutability requirement.
      `[X-REF 03]` `[X-REF 09]`
5.3.5 **Rate limiter as a service** `[DESIGN]` — the design the guide currently teaches only as a
      mechanism (§1.23). Requirements: 1 M rules, sub-millisecond decision, fail-open policy.
      Key design: token bucket in Redis with atomic Lua, local lease caching, rules distributed by
      a config plane. Deep dive: consistency of counters under Redis failover, and what happens
      when the limiter is the thing that is overloaded. Bottleneck: the limiter's own Redis.
5.3.6 **Web crawler** `[DESIGN]` — politeness (per-domain rate limits), the frontier as a
      priority + per-host queue structure, URL dedupe at 10¹⁰ scale (Bloom filter plus a sharded
      seen-set), content dedupe by SimHash, robots.txt caching, DNS as a bottleneck, trap
      detection (infinite calendars), and recrawl scheduling by change rate. Bottleneck: DNS and
      politeness, not bandwidth. `[PROVE]`
5.3.7 **Search autocomplete / typeahead** `[DESIGN]` — p99 under ~50 ms on every keystroke.
      Key design: **precompute the top-k completions per prefix** and serve a lookup, not a
      traversal; a trie with top-k cached at each node, sharded by prefix, rebuilt offline from
      query logs on a cadence; ranking moved entirely off the request path. Extras: personalised
      vs global suggestions, typo tolerance, trending terms with a time-decayed count, and the
      debounce/caching done on the client. Bottleneck: request rate (one request per keystroke)
      and index rebuild time. `[RESEARCH]`
5.3.8 **Notification system** `[DESIGN]` — multi-channel (push/email/SMS/in-app), a template
      service, user preferences and quiet hours, per-channel providers with their own rate limits
      and failure modes, per-channel queues with independent retry and DLQ, deduplication and
      frequency capping, and delivery-status tracking. Deep dive: idempotency across a third-party
      provider that may have already sent, and fan-out to a very large audience. Bottleneck:
      provider throughput and the fan-out worker pool. `[RESEARCH]`
5.3.9 **Proximity / nearby service (Yelp, nearby friends)** `[DESIGN]` — spatial index choice
      (§2.13), read-heavy static POIs vs write-heavy live locations as two different designs, cell
      size vs result-set size trade-off, the boundary problem, and ranking by distance plus
      business rules. Deep dive: the write-heavy variant with in-memory sharded grids and TTLs.
      Bottleneck: location update rate. `[RESEARCH]`
5.3.10 **Ride-hailing dispatch** `[DESIGN]` — matching as a bounded optimisation over a spatial
       index, supply/demand state, the two-sided consistency problem (one driver must not be
       matched twice — a linearizable operation), surge as a derived signal, and trip state as a
       saga. Bottleneck: matching latency in dense cells. `[RESEARCH]`
5.3.11 **Collaborative document editing (Google Docs)** `[DESIGN]` — OT vs CRDT (§3.5.9),
       server-authoritative session with a per-document ordering authority, presence and cursors,
       persistence as periodic snapshots plus an operation log, offline editing, and access
       control per document. Deep dive: the convergence argument. Bottleneck: per-document write
       serialisation. `[RESEARCH]`
5.3.12 **Video streaming (YouTube/Netflix)** `[DESIGN]` — upload → pre-signed multipart → transcode
       pipeline producing an **ABR ladder** → packaging into HLS/DASH segments (2–10 s) →
       manifest → CDN. Watch path is entirely CDN; the origin serves manifests and cold content.
       Estimation dominated by egress: 1080p ≈ 5 Mbps, so 1 M concurrent viewers ≈ 5 Tbps.
       Deep dive: the transcoding pipeline as a DAG of parallel jobs, and the popularity-based
       pre-warm/pre-position decision. Bottleneck: CDN egress and transcode fleet.
       `[PROVE]` `[NUM]` `[RESEARCH]`
5.3.13 **Live streaming** as the variant with a latency requirement: low-latency HLS/LL-DASH or
       WebRTC, ingest → transcode in real time → edge, with the trade-off between latency and
       buffer resilience, plus live chat as a separate fan-out problem. `[RESEARCH]`
5.3.14 **File sync (Dropbox)** `[DESIGN]` — chunking with content-defined boundaries,
       block-level dedupe, a metadata service as the source of truth, delta sync, conflict
       handling (rename-on-conflict, not merge), and the client's local state machine. Deep dive:
       the metadata service's consistency and the notification path for other devices.
       Bottleneck: metadata operations, not bytes. `[RESEARCH]`

5.3.15 **Ticket booking with inventory reservation (Ticketmaster/BookMyShow)** `[DESIGN]` — the
       10× spike is the defining input. Key design: a **hold with a TTL** (§2.7.10) so the
       reservation is a single-partition conditional write, a virtual waiting room / queue in
       front of the on-sale, seat-map caching with optimistic UI, and payment as a saga.
       Deep dive: preventing double-booking under contention without holding a database lock for
       the user's checkout duration. Bottleneck: contention on one event's seat inventory.
       `[PROVE]` `[RESEARCH]`
5.3.16 **Ad click aggregation** `[DESIGN]` — the canonical streaming design. Click → Kafka →
       stream processor with event-time **1-minute tumbling windows** and watermarks → OLAP store
       → dashboard. Requirements: near-real-time for advertisers, exact-enough for billing, and
       replay for corrections. Key design: dedupe by event ID inside a bounded state window,
       aggregate keyed by `(window, campaign, ad, geo, device)`, and a reconciliation batch job
       for the billing-grade number. Deep dive: late data and allowed lateness, and exactly-once
       into the sink. Bottleneck: hot campaign keys and state size in the processor.
       `[RESEARCH]` `[X-REF 14]`
5.3.17 **Metrics and monitoring system** `[DESIGN]` — ingestion at millions of points/second,
       a time-series store with downsampling and retention tiers, cardinality as the dominant
       failure mode, push vs pull collection, query and alert evaluation as separate workloads,
       and the fact that the monitoring system must not depend on the thing it monitors.
       Bottleneck: cardinality. `[X-REF 20]` `[RESEARCH]`
5.3.18 **Distributed job scheduler / cron** `[DESIGN]` — requirements: at-least-once with an
       idempotent job contract, cron and fixed-delay, retries with backoff, and no double-run for
       "exactly once" jobs. Key design: leader election with leases for the scheduler, a due-job
       index or a **hierarchical timing wheel** in memory, a queue of ready jobs, stateless
       workers with visibility timeouts and heartbeats, and a fencing token for jobs where a
       double-run is unacceptable. Deep dive: what happens when a worker pauses and its lease
       expires mid-job. Bottleneck: the due-job scan at high job counts. `[RESEARCH]`
5.3.19 **Distributed cache** `[DESIGN]` — consistent-hash ring with vnodes, client-side routing
       vs a proxy, replication for hot keys, eviction policy, cache invalidation across nodes, and
       the cold-start/rehash problem. Deep dive: what happens when a node leaves during peak.
       `[X-REF 15]`
5.3.20 **Key-value store from scratch** `[DESIGN]` — the "build Dynamo" question: partitioning,
       replication, quorum with tunable N/W/R, versioning and conflict resolution, hinted handoff,
       anti-entropy, gossip membership, and the storage engine (LSM). This is §3.2 and §4.11 asked
       as one question. `[PROVE]`
5.3.21 **Object storage (S3-like)** `[DESIGN]` — flat namespace, metadata service separate from
       data plane, erasure coding, multipart upload, immutable objects with versioning, LIST as a
       separate index problem, and the consistency semantics. Deep dive: the durability
       arithmetic. `[PROVE]` `[RESEARCH]`
5.3.22 **Stock exchange / matching engine** `[DESIGN]` — the low-latency outlier: a single-threaded
       in-memory **limit order book** per symbol with price-time priority, sharded by symbol,
       durability by sequenced input log plus deterministic replay, and a hot-standby that replays
       the same input. Deep dive: why the matching core is single-threaded and why that is
       correct. Bottleneck: per-symbol throughput and the p99.9 in microseconds. `[RESEARCH]`
5.3.23 **Digital wallet** `[DESIGN]` — the ledger design (§5.3.4) plus the transfer-between-users
       case: same-partition transfer as one transaction, cross-partition as a saga with a hold,
       idempotency, and the reconciliation job. Deep dive: exactly-once money movement under
       client retries.
5.3.24 **Leaderboard** `[DESIGN]` — Redis ZSET for the top-N and rank queries, the problem of rank
       for a user outside the top-N at 100 M users (bucketed counts plus a two-level index),
       sharded ZSETs with periodic merge, time-windowed leaderboards, and the write-amplification
       of updating a score on every event. `[PROVE]` `[X-REF 15]`
5.3.25 **Hotel / flight reservation** `[DESIGN]` — inventory by (property, room type, date range),
       overbooking policy as a deliberate business decision, the date-range availability query, and
       idempotent booking. Contrast with §5.3.15 on contention shape. `[RESEARCH]`
5.3.26 **Online auction / bidding** `[DESIGN]` — per-item write serialisation, last-second bid
       spikes, soft-close/anti-sniping extension, and consistency of the "current highest bid"
       broadcast. `[RESEARCH]`
5.3.27 **Top-K / trending** `[DESIGN]` — heavy hitters over a stream with Count-Min plus a heap,
       time-decayed windows, per-region trending, and the batch reconciliation for the
       "official" list. `[RESEARCH]`
5.3.28 **Distributed message queue** `[DESIGN]` — the "build Kafka/SQS" question: partitioned
       append-only log, replication and ISR, consumer groups and offset commits, delivery
       semantics, retention and compaction, and the broker's zero-copy I/O path. `[X-REF 14]`
5.3.29 **Multiplayer game / real-time state sync** `[DESIGN]` — authoritative server per room,
       tick rate, state snapshots plus deltas, client prediction and reconciliation, region-based
       matchmaking, and UDP vs TCP. `[RESEARCH]` `[X-REF 10]`
5.3.30 **Code deployment / CI at scale**, **API gateway**, and **URL/content moderation pipeline**
       as three lower-frequency questions worth a paragraph each so they are not novel in the
       room. `[RESEARCH]`
5.3.31 The catalogue's meta-lesson: these thirty designs use the same twelve mechanisms. Build the
       mechanism inventory (§2.20) and the designs become recombinations. `[SAY]`

*(31 leaves)*

## §5.4 The question bank

5.4.1 The **estimation** questions: "how many servers", "how much storage in five years", "what's
      the bandwidth", "how big is the cache", "how many shards", "what does it cost per month".
      (6)
5.4.2 The **consistency** questions: CAP precisely; PACELC; why "CA" is not a thing; quorum vs
      linearizability; read-your-writes; what eventual consistency means to a user; when you'd
      accept a stale read; how you'd make a counter both fast and eventually correct. (8)
5.4.3 The **partitioning** questions: choose a shard key and defend it; what happens when you add
      a node; how do you fix a hot key; how do you reshard live; what breaks in a cross-shard
      query; how do you do a cross-shard transaction. (6)
5.4.4 The **failure** questions: what happens when the cache dies / the DB primary dies / a
      region dies / the queue backs up / a dependency is slow but not down / the network
      partitions; how do you detect it; how do you recover; how do you prevent the cascade. (9)
5.4.5 The **idempotency** questions: how do you avoid double-charging; how do you make a consumer
      idempotent; what is the dual-write problem; explain the outbox; is exactly-once possible. (5)
5.4.6 The **caching** questions: which tier and why; how do you invalidate; what is a stampede and
      how do you prevent it; what is the load on the origin at 0% hit ratio; what belongs in the
      key. (5)
5.4.7 The **queueing** questions: queue vs log; ordering guarantees; what's in the DLQ and who
      owns it; how do you replay; what is backpressure and what do you do when it happens. (5)
5.4.8 The **API** questions: pagination scheme and why; how do you version; how do you handle
      partial failure in a batch; where does rate limiting live; what status code and what
      headers. (5)
5.4.9 The **operations** questions: what do you monitor and alert on; what is the SLO; how do you
      deploy this safely; how do you roll it back; how do you migrate from the old system; who is
      on call. (6)
5.4.10 The **cost** questions: what is the largest line on the bill; what would you cut first; what
       does one user cost; when does the managed service stop being worth it. (4)
5.4.11 The **"what if" perturbations** an interviewer applies to any design: 100× the traffic; the
       read:write ratio inverts; it must now be strongly consistent; it must now be multi-region;
       the object size is 100× bigger; retention becomes forever; one customer is 40% of the load.
       (7)
5.4.12 The **staff-level** questions: how would you migrate 500 M rows live; how would you split
       this into services and why; what would you *not* build; how do you convince three teams to
       adopt it; what's the two-year evolution of this design. (5)
5.4.13 The **trick/precision** questions: is quorum linearizable; does a load balancer improve
       availability; is UUID a good primary key; does adding nodes fix a hot key; is Kafka a queue;
       does a circuit breaker help if the dependency is slow rather than failing; does retrying
       improve availability. (7)
5.4.14 A drill format for each: 90 seconds of spoken answer, containing one number, one mechanism
       and one cost. `[SAY]`

*(14 leaves, enumerating 92 questions)*

## §5.5 The trap index

Every `[TRAP]` in this file collected as a one-line "wrong belief → symptom → fix" table, so the
write pass can render it once as a review page. The set, at minimum:

5.5.1 Treating the round as a knowledge quiz (§1.2.7).
5.5.2 Memorised architectures that cannot absorb a perturbation (§1.2.9).
5.5.3 Claiming five nines casually; ignoring availability multiplication (§1.6.3, §1.6.12).
5.5.4 Assuming failure independence across replicas (§1.6.6).
5.5.5 Quoting 2012 latency numbers as current absolutes (§1.7.10).
5.5.6 Estimating and then never using the estimate (§1.8.14).
5.5.7 Starting at rung 6 of the ladder; and refusing to climb when the numbers demand it
      (§1.10.11–§1.10.12).
5.5.8 "Stateless" claimed for a service holding correctness-bearing memory state (§1.11.8).
5.5.9 Offset pagination's skip-and-duplicate behaviour (§1.12.4).
5.5.10 Forgetting that mobile clients retry hours later from an offline queue (§1.12.12).
5.5.11 Schema-on-read moving migration cost to every reader forever (§1.13.9).
5.5.12 "NoSQL scales better" unqualified (§1.14.16).
5.5.13 Async replication failover losing acknowledged writes; assuming a third option exists
       (§1.15.14).
5.5.14 Confusing shards with replicas (§1.16.23).
5.5.15 Believing adding nodes fixes a hot key (§1.16.10).
5.5.16 Hashing "fixes" skew — it fixes data skew, not request skew (§2.5.10).
5.5.17 "CA" as a deployment option (§1.17.3).
5.5.18 Conflating linearizability with serializability (§1.17.9).
5.5.19 "Eventual consistency is only a few milliseconds" (§1.17.13).
5.5.20 "We chose AP" as a whole-system statement (§1.17.14).
5.5.21 "Quorum reads give strong consistency" (§1.18.9).
5.5.22 LWW on wall clocks silently discarding data (§1.18.11, §3.4.10).
5.5.23 Omitting the user/tenant from a cache key (§1.19.5).
5.5.24 Treating the cache as optional when the origin is sized for 1% of traffic (§1.19.2).
5.5.25 Sync-over-async: publishing then polling inside the request (§1.20.10).
5.5.26 `findById`-then-`save` as an idempotency check (§1.21.5).
5.5.27 Claiming exactly-once delivery (§1.21.2).
5.5.28 Believing Kafka EOS covers arbitrary external side effects (§1.21.16).
5.5.29 UUIDv4 as a clustered primary key (§1.22.4).
5.5.30 Fixed-window rate limiting's 2× boundary burst (§1.23.2).
5.5.31 GET-then-SET distributed rate limiting (§1.23.8).
5.5.32 IP as the rate-limit key (§1.23.11).
5.5.33 Not deciding fail-open vs fail-closed for the limiter (§1.23.13).
5.5.34 Round-robin balancing onto a degraded backend (§1.24.3).
5.5.35 Deep health checks causing correlated fleet removal (§1.24.4).
5.5.36 L4 balancing in front of HTTP/2 or gRPC (§1.24.10).
5.5.37 DNS as a failover mechanism (§1.24.11).
5.5.38 Missing timeouts; Java's infinite defaults (§1.25.2, §1.25.4).
5.5.39 Timeouts set below the dependency's normal p99 (§1.25.3, §2.9.7).
5.5.40 Retries without jitter or idempotency (§1.25.20).
5.5.41 Retry amplification across layers (§1.25.9).
5.5.42 Fallbacks that are themselves network calls (§1.25.16).
5.5.43 Multi-region without multi-regioning the dependencies (§1.26.15).
5.5.44 Failback treated as symmetric with failover (§1.26.9).
5.5.45 Elasticsearch as the source of truth (§1.27.5).
5.5.46 CQRS/event sourcing adopted by default (§1.27.6, §1.27.7).
5.5.47 A counter row incremented per event (§1.27.10).
5.5.48 Blobs in the relational store (§1.28.8).
5.5.49 Confusing eleven nines of durability with availability (§1.28.12).
5.5.50 Averaging percentiles; using averages at all (§1.29.5, §1.29.8).
5.5.51 Coordinated omission in the load test (§1.29.9).
5.5.52 Proposing a maintenance window without justifying it (§1.30.11).
5.5.53 A "rollback" that requires a data restore (§2.17.7).
5.5.54 Config changes shipped without canary (§2.17.4).
5.5.55 Autoscaling as the answer to overload (§2.10.15).
5.5.56 Believing removing the trigger ends a metastable failure (§2.10.9).
5.5.57 The health-check death spiral (§2.11.11).
5.5.58 Consistent hashing described as a hot-key fix (§3.1.14).
5.5.59 Treating DynamoDB (the service) as Dynamo (the paper) (§3.2.8).
5.5.60 Redlock used where fencing is required (§3.3.14).
5.5.61 2P-Set / naive set merge losing intent; CRDT convergence mistaken for correctness
       (§3.2.5, §3.5.10).
5.5.62 Ignoring compaction, tombstones and vacuum as operational realities (§3.2.11, §3.6.3).
5.5.63 Increasing Kafka partition count and breaking key affinity (§3.7.6).
5.5.64 `Vary`/cache-key cardinality destroying CDN hit ratio (§3.8.4).
5.5.65 Compensations mistaken for rollbacks (§2.7.7).
5.5.66 Stuck sagas with no operator surface (§2.7.12).
5.5.67 Late data silently dropped in a windowed aggregation (§2.8.7).
5.5.68 Missing tenant filter in a multi-tenant query (§2.16.4).
5.5.69 Certificate/lease expiry as a correlated outage (§2.16.9, §3.11.13).
5.5.70 Over-abstraction at staff level: describing a platform instead of answering (§5.2.7).

*(70 leaves)*

## §5.6 Retention drills

5.6.1 **Numbers drill:** reproduce the latency ladder, the capacity table, the nines table and the
      conversion identities from memory in under three minutes. `[NUM]`
5.6.2 **Arithmetic drill:** given DAU, actions/user/day, object size and retention, produce QPS,
      peak QPS, storage/year, bandwidth and a box count in 90 seconds. `[PROVE]`
5.6.3 **Table drill:** reproduce five comparison tables from memory — fan-out push vs pull,
      rate-limiter algorithms, replication models, multi-region topologies, storage fit.
5.6.4 **Mechanism drill:** state in one sentence each, from memory: consistent hashing, quorum
      overlap, the outbox, the idempotency insert-first rule, the circuit-breaker state machine,
      cursor pagination, hedged requests, shuffle sharding, the panic threshold, commit-wait.
      `[SAY]`
5.6.5 **Proof drill:** reproduce three proofs from §2.3 with the arithmetic written out.
5.6.6 **Failure drill:** for a named component, produce the dies/slow/full answers plus the metric
      and the mitigation, in 60 seconds.
5.6.7 **Design drill:** pick a design from §5.3 at random, produce requirements + estimation + the
      key decision + the bottleneck in 10 minutes, out loud, timed.
5.6.8 **Perturbation drill:** take yesterday's design and apply one perturbation from §5.4.11;
      re-derive only what changes.
5.6.9 **Trap drill:** read §5.5 cold and, for each line, state the symptom and the fix without
      looking.
5.6.10 **Review drill:** take a real design document from work and run §1.29.1's three questions
       plus the §2.18 ownership questions against it.
5.6.11 The final self-check before an interview: can I name the bottleneck of every design I have
       studied, in one sentence each? `[SAY]`

*(11 leaves)*

## §5.7 The closing assertion set

5.7.1 The bible's `## Atomic concept checklist` must **preserve all ~70 existing assertions
      verbatim in meaning** and extend them to cover every new section: the fallacies, partial
      failure, cost modelling, Little's law and the utilisation knee, tail latency and hedging,
      cells and shuffle sharding, metastable and grey failure, consensus and fencing, clocks and
      commit-wait, CRDT algebra, spatial indexes, probabilistic structures, streaming windows, the
      L5/L6 rubric, and each of the thirty worked designs' single defining decision.
5.7.2 Format contract: one flat bullet per distinct concept, one assertion per line, no nesting —
      downstream agents parse it.
5.7.3 Every worked design contributes exactly one checklist line naming its key decision and its
      bottleneck.
5.7.4 Every `[PROVE]` leaf contributes one checklist line stating the *result* of the proof.
5.7.5 Every trap in §5.5 contributes one checklist line stating the correct belief, not the wrong
      one.

*(5 leaves)*

---

## Sources consulted

Primary sources first in each group. Where a fetch failed or a search returned nothing usable,
that is stated rather than padded. Every leaf tagged `[RESEARCH]` traces to one of these and must
be re-verified before its number is written down.

**Papers (primary)**

- <https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf> — Dynamo (SOSP 2007).
  Source for §3.2 in full: the technique-to-problem mapping, preference lists, the "first N
  *healthy* nodes" definition of a sloppy quorum, hinted handoff, vector clocks and truncation,
  Merkle-tree anti-entropy, gossip membership. Also §1.18.6–§1.18.8.
- <https://www.usenix.org/system/files/atc22-elhemali.pdf> — Amazon DynamoDB (USENIX ATC 2022).
  Source for §3.2.8–§3.2.10: partitioned Multi-Paxos with leases, adaptive capacity, splitting for
  consumption, global admission control, log replicas, formal methods, metadata-service cold-cache
  protection. **The PDF fetch returned binary that the fetch tool could not parse**; the content
  above comes from the search summary and from secondary write-ups
  (<https://brooker.co.za/blog/2022/07/12/dynamodb.html>,
  <http://muratbuffalo.blogspot.com/2022/07/amazon-dynamodb-scalable-predictably.html>). Every
  number from this paper is `[RESEARCH]` and must be re-read from the PDF in the write pass.
- <https://raft.github.io/raft.pdf> and <https://web.stanford.edu/~ouster/cgi-bin/papers/raft-atc14.pdf>
  — Raft. Source for §3.3.3–§3.3.5: the leader-election / log-replication / safety decomposition,
  terms, randomised election timeouts, the log-completeness restriction, membership change.
- <https://sigops.org/s/conferences/hotos/2021/papers/hotos21-s11-bronson.pdf> — "Metastable
  Failures in Distributed Systems" (HotOS 2021). Source for §2.10.9–§2.10.10 and §3.11.4: trigger
  vs sustaining effect, the degraded equilibrium that survives trigger removal, and the finding
  that retry policy is the sustaining effect in the majority of studied incidents
  (corroborated by <https://www.usenix.org/publications/loginonline/metastable-failures-wild>).
- <https://web.eecs.umich.edu/~ryanph/paper/grayfailure-hotos17.pdf> — "Gray Failure: The Achilles'
  Heel of Cloud-Scale Systems" (HotOS 2017). Source for §2.11.5–§2.11.6 and §3.11.6: differential
  observability, the Azure capacity-reporting example, and the design response.
- <https://www.barroso.org/publications/TheTailAtScale.pdf> — "The Tail at Scale" (CACM 2013).
  Source for §2.9 and §1.25.17–§1.25.18: hedged requests deferred to the p95 (~5% extra load),
  tied requests (16% median / 40% p99.9 improvement in the reported system), micro-partitions at
  ~20 per machine giving ~5% shedding granularity, selective replication, latency-induced
  probation.
- <https://research.google.com/pubs/archive/39966.pdf> — Spanner. Source for §3.4.6–§3.4.7:
  TrueTime as an interval, commit-wait, external consistency. The ~7 ms ε figure is corroborated
  by <https://docs.cloud.google.com/spanner/docs/true-time-external-consistency> and must be
  re-checked, since ε is an operational property and has been reported lower in recent years.
  `[CURRENCY]`
- <https://cse.buffalo.edu/tech-reports/2014-04.pdf> — Hybrid Logical Clocks. Source for §3.4.5.
- <https://arxiv.org/pdf/1608.01350> — "Consistent Hashing with Bounded Loads". Source for
  §3.1.10 and §4.1.5.
- <https://sites.cs.ucsb.edu/~rich/class/cs293b-cloud/papers/brewer-cap.pdf> — Brewer, "CAP Twelve
  Years Later". Source for §1.17.5 and the framing of §1.17.1–§1.17.3.
- <https://www.usenix.org/sites/default/files/conference/protected-files/nsdi16_slides_eisenbud.pdf>
  — Maglev. Source for §3.1.8.

**Operational canon (primary)**

- <https://sre.google/sre-book/addressing-cascading-failures/> — Google SRE ch. 22. Source for
  §2.10.7–§2.10.14 and §3.11.5: the positive-feedback definition, queue sizing at ≤50% of the
  thread pool, load shedding vs graceful degradation, deadline and cancellation propagation,
  bimodal latency, cold-cache slow start, "always go downward in the stack", the trigger
  catalogue, the test-to-failure guidance, and the immediate-mitigation list (including
  temporarily disabling health checks and dropping traffic to 1%).
- <https://sre.google/sre-book/handling-overload/> — Google SRE ch. 21. Source for §1.23.16–
  §1.23.19: the four criticality levels (CRITICAL_PLUS / CRITICAL / SHEDDABLE_PLUS / SHEDDABLE),
  utilisation signals including executor load average, client-side adaptive throttling with the
  `requests ≥ K × accepts` rule and K ≈ 2, the per-request cap of 3 attempts and the per-client
  10% retry budget, and per-customer CPU allocations.
- <https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/panic_threshold.html>
  — Envoy panic threshold, default 50%. Source for §1.24.6. Also the cluster runtime reference at
  <https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_runtime>
  for `healthy_panic_threshold` and the outlier-detection knobs behind §1.24.7. `[CURRENCY]`
- <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> — the AWS
  Architecture Blog's jitter analysis. Source for §1.25.6–§1.25.7 (full vs equal vs decorrelated
  jitter and their measured behaviour). The Builders' Library index itself
  (<https://aws.amazon.com/builders-library/>) 301-redirects to
  <https://builder.aws.com/learn/topics/builders-library>, which returned no article list to the
  fetch tool — the article titles cited here (timeouts/retries/backoff-with-jitter, load
  shedding, avoiding insurmountable queue backlogs, avoiding fallback, shuffle sharding) come from
  secondary coverage (<https://lumigo.io/blog/amazon-builders-library-in-focus-1-timeouts-retries-and-backoff-with-jitter/>
  and siblings) and are `[RESEARCH]`.
- <https://github.com/aws-solutions-library-samples/guidance-for-cell-based-architecture-on-aws>
  — official cell-based-architecture guidance. Source for §2.12: cells as complete independent
  instances, blast radius as an explicit parameter, the thin-cell-router rule, and shuffle
  sharding layered on top. `[CURRENCY]`
- <https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html> — the Redlock
  critique. Source for §3.3.12–§3.3.15: fencing tokens, the process-pause scenario, and the
  efficiency-vs-correctness distinction.
- <https://etcd.io/docs/v3.5/learning/why/> — etcd vs ZooKeeper, leases and revisions as fencing
  tokens. Source for §3.3.13. `[CURRENCY]`
- <https://nightlies.apache.org/flink/flink-docs-master/docs/dev/datastream/operators/windows/>
  and <https://flink.apache.org/2018/02/28/an-overview-of-end-to-end-exactly-once-processing-in-apache-flink-with-apache-kafka-too/>
  — windows, allowed lateness, and the two-phase-commit sink. Source for §2.8.5–§2.8.9.
- <https://groups.google.com/g/mechanical-sympathy/c/icNZJejUHfE> and
  <https://www.scylladb.com/2021/04/22/on-coordinated-omission/> plus
  <https://github.com/giltene/wrk2> — coordinated omission, the closed-loop generator's silent
  deletion of the worst samples, and the HdrHistogram/wrk2 corrections. Source for §1.29.9–
  §1.29.10 and §2.19.2.

**Curriculum and concept-name mining**

- <https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/> —
  DDIA 2nd edition (Feb 2026). The publisher page returned HTTP 403; the chapter list used here
  ("Trade-offs in Data Systems Architecture", "Defining Nonfunctional Requirements", "Encoding and
  Evolution", "The Trouble with Distributed Systems", "Consistency and Consensus", "A Philosophy
  of Streaming Systems") comes from search results and
  <https://blog.vonng.com/en/db/ddia-v2/>. It contributed §1.5 (non-functional requirements as a
  first-class chapter), §1.1.5–§1.1.7 (the trouble-with-distributed-systems framing) and §2.8.
  `[RESEARCH]` `[CURRENCY]`
- <https://www.hellointerview.com/learn/system-design/in-a-hurry/introduction> — a current
  published curriculum. Mined purely for concept and problem names absent from the existing guide.
  It contributed: dealing with contention, multi-step processes, scaling reads vs scaling writes
  as separate patterns, handling large blobs, managing long-running tasks, proximity search, time
  series databases, change data capture, and roughly twenty problem names now in §5.3 (Ticketmaster,
  Dropbox, YouTube, Uber, web crawler, ad click aggregator, job scheduler, notification system,
  metrics monitoring, distributed cache, online auction, Google Docs, payment system, LeetCode,
  top-K).
- <https://www.designgurus.io/blog/system-design-interview-questions-to-crack-your-next-faang-interview>,
  <https://www.educative.io/blog/system-design-interview-questions>,
  <https://igotanoffer.com/blogs/tech/system-design-interviews> — question-bank breadth for §5.4
  and the remaining §5.3 entries (typeahead, key-value store, object store, stock exchange, hotel
  reservation, digital wallet, leaderboard, distributed message queue).
- <https://www.hellointerview.com/guides/google/l6> and
  <https://designgurus.substack.com/p/faang-system-design-interviews-by> — the L5/L6 rubric split
  in §5.2: one design round at L5 and two at L6+, the shift in weighting toward operational
  maturity and driving, "surfaces the constraint before being pointed at it", and the
  downlevel-for-L5-quality-answer finding. `[CURRENCY]` `[RESEARCH]`
- <https://engineeringenablement.substack.com/p/common-mistakes-in-system-design> and
  <https://www.designgurus.io/blog/how-to-prepare-for-system-design-interview-2026> — §1.2.9 and
  §5.5's process traps, notably memorisation as the dominant failure mode and the
  infinite-uptime assumption.

**Mechanism references**

- <https://medium.com/@charleyjava/spatial-indexing-in-system-design-quadtree-geohash-and-h3-explained-35f8fb354ff8>
  and <https://joudwawad.medium.com/the-complete-guide-to-location-indexing-geohash-quadtree-google-s2-and-uber-h3-36a143569555>
  — §2.13: geohash's Z-order and boundary problem, S2's Hilbert curve and range-query property,
  H3's 16 resolutions with ~7× growth per level and equidistant neighbours. Secondary sources;
  the H3 resolution figures must be re-verified against the H3 documentation. `[RESEARCH]`
- <https://dgryski.medium.com/consistent-hashing-algorithmic-tradeoffs-ef6b8e2fcae8> — §3.1.6–
  §3.1.11: the ring / rendezvous / jump / Maglev / multi-probe / bounded-load comparison and their
  lookup-cost and removal-support differences.
- <https://www.iankduncan.com/engineering/2025-11-27-crdt-dictionary/> and
  <https://hackernoon.com/crdts-vs-operational-transformation-a-practical-guide-to-real-time-collaboration>
  — §3.5: the CvRDT/CmRDT split, the type inventory (G-Counter, PN-Counter, 2P-Set, OR-Set,
  LWW-Register, RGA/YATA), and the OT-vs-CRDT decision rule with real product examples.
- <https://www.javacodegeeks.com/2026/04/probabilistic-data-structures-the-theory-behind-bloom-filters-hyperloglog-and-count-min-sketch.html>
  — §2.14 and §2.3.13–§2.3.14: ~10 bits/element at 1% FPR, HLL at ~12 KB with sub-1% error, and
  the membership/cardinality/frequency decision rule. The exact 1.04/√m standard-error identity
  was **not** confirmed by any source fetched in this pass; it must be verified against the
  HyperLogLog paper or the Redis documentation before it is written down. `[RESEARCH]`
- <https://www.conduktor.io/glossary/kafka-replication-and-high-availability> and
  <https://blog.2minutestreaming.com/p/kafka-acks-min-insync-replicas-explained> — §3.7.2–§3.7.3:
  RF=3 with `min.insync.replicas=2` and `acks=all` as the durable configuration, and KRaft/tiered
  storage as the 4.x-era changes. `[CURRENCY]`
- <https://github.com/resilience4j/resilience4j> — §4.6.4 and §4.6.9: the circuit-breaker
  configuration surface (count-based vs time-based window, failure- and slow-call-rate thresholds,
  minimum calls, wait duration in open state, permitted calls in half-open). The internal ring-bit-
  buffer detail was not confirmed by a primary source in this pass and is `[RESEARCH]`.
- <https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer> — §3.4.8: HLC,
  `max_offset` (500 ms default) and the uncertainty-interval restart. `[CURRENCY]`
- <https://www.businesswire.com/news/home/20241203503287/en/AWS-Announces-New-Database-Capabilities-Including-Amazon-Aurora-DSQL-the-Fastest-Distributed-SQL-Database>
  and <https://jayendrapatil.com/aws-aurora-global-database-vs-dynamodb-global-tables/> — §1.26.13
  and §2.21.2: Aurora DSQL's stated 99.999% multi-Region availability, and DynamoDB global tables
  MRSC requiring exactly three Regions (three replicas, or two replicas plus a witness) within one
  Region set. Vendor claims and product constraints; both are `[CURRENCY]` and must be re-verified
  against AWS documentation, not a press release, in the write pass.
- <https://spendark.com/blog/cloud-egress-costs-guide/> and
  <https://www.usage.ai/blogs/s3-egress-cost/> — §2.2.3–§2.2.7: the ~$0.09/GB internet-egress list
  figure with volume tiers, object-storage vs managed-NoSQL storage price ratio, NAT-gateway data
  processing charges, and the free gateway-endpoint alternative. **List prices from secondary
  sources.** Every dollar figure in §2.2 is `[CURRENCY]` `[RESEARCH]` and must be re-checked
  against the vendor pricing page, dated, and presented as an order of magnitude.
- <https://github.com/danluu/post-mortems> — the postmortem collection behind §3.12; the specific
  incidents cited (2017 object-storage control plane, 2019 edge-WAF regex, 2021 game-platform
  multi-day outage) were confirmed only at summary level in this pass. Each must be traced to its
  official postmortem before §3.12 is written, and any detail that cannot be sourced must be
  dropped rather than reconstructed. `[RESEARCH]`

**Searched and not usable**

- The Amazon Builders' Library index page could not be enumerated: the canonical URL redirects and
  the destination returned only a page shell to the fetch tool. Article-level citations in §1.25,
  §1.23 and §2.5 therefore rest on secondary summaries and are tagged `[RESEARCH]`.
- No single authoritative, current source was found for the per-node capacity constants in §1.9
  (RPS per JVM instance, writes/s per Postgres primary, ops/s per Redis instance). These are
  folklore constants that are nonetheless the right order of magnitude; the write pass must
  present them as sizing heuristics with a stated basis, not as measured facts.
- No primary source was fetched for the H3 resolution table, the exact HLL standard-error
  constant, or the Resilience4j ring-bit-buffer internals; all three are flagged above.

## Gaps vs the current guide

`src/topics/22-system-design.md` is 937 lines across 28 sections plus a ~70-line checklist. The
table below is the work order. *Present* means the concept exists and is adequate as a summary but
must be deepened to bible depth; *shallow* means it exists at one to three lines where the syllabus
demands mechanism, numbers or proof; *missing* means it is not there at all.

| Syllabus area | Present in `src/topics/22-…md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why distributed at all, fallacies, partial failure | — | ✅ entire section | |
| §1.2 what the round measures | §1 | | ✅ table only, no memorisation trap |
| §1.3 the clock | §1 table | ✅ 35/60-min variants, board mechanics, two-round loop | |
| §1.4 functional requirements | §2 (3 lines) | ✅ actors, out-of-scope discipline, non-goals | ✅ |
| §1.5 the six numbers | §2 | ✅ the four forgotten numbers, durability, compliance, cost-as-requirement | |
| §1.6 availability arithmetic | §2 (table + one trap) | ✅ parallel redundancy, correlated failure, MTBF/MTTR, hard vs soft dependency, error budget | ✅ |
| §1.7 the memorised numbers | §3 | ✅ powers table, BDP, speed-of-light floor, the staleness trap | |
| §1.8 estimation as a procedure | §3 | ✅ the four-step procedure, rounding discipline, replication/index multipliers, connection arithmetic, when not to estimate | ✅ |
| §1.9 capacity rules of thumb | §3 table | ✅ ES shard sizing, object storage, box-count derivation, utilisation target, N+2 | |
| §1.10 the ladder | §4 | ✅ the not-on-the-ladder trap, the refusing-to-climb trap | |
| §1.11 statelessness | §4 (2 lines) | ✅ the four kinds of state, graceful shutdown, the false-stateless trap | ✅ |
| §1.12 API at design layer | §5 | ✅ cursor construction, batch endpoints, partial failure, 202 pattern, client behaviour, gateway/BFF/mesh | ✅ |
| §1.13 data model and key design | §5 | ✅ local vs global secondary index, single-table design, lifecycle, PII erasure, time-series shaping | ✅ |
| §1.14 storage selection | §6 | ✅ NewSQL, vector stores, managed vs self-hosted, the operability questions | |
| §1.15 replication | §7 | ✅ replication mechanisms, LSN tokens, automatic-vs-manual failover, chained replication, backups≠replication | ✅ |
| §1.16 partitioning | §8 | ✅ replica placement, hot-key detection, over-partitioning cost, rebalancing mechanics, shard-vs-replica trap | ✅ |
| §1.17 CAP/PACELC/models | §9 | ✅ Gilbert–Lynch precision, Brewer's revision, linearizable vs serializable, causal as the ceiling, session guarantees | ✅ |
| §1.18 quorums | §10 | ✅ latency consequence, even-N, witnesses, tunable-consistency vocabulary | ✅ |
| §1.19 caching in a design | §11 | ✅ hit-ratio non-linearity proof, negative caching, warming, the cost lever, never-cache list | ✅ |
| §1.20 asynchrony | §12 | ✅ time-to-drain, sync-over-async, status model, priority/fairness, delayed work, event-schema choice, choreography vs orchestration | ✅ |
| §1.21 idempotency | §13 | ✅ the three-state record, scope/TTL/fingerprint, conditional writes, dedupe-window sizing, inbox, Kafka-EOS boundary, reordering | ✅ |
| §1.22 ID generation | §14 | ✅ UUIDv7 detail, ULID, clock-regression policies, short IDs, IDs and sharding, hierarchical IDs | ✅ |
| §1.23 rate limiting | §15 | ✅ layered limits, quotas vs limits, criticality classes, shed signals, concurrency limiting, client-side adaptive throttling | ✅ |
| §1.24 load balancing | §16 | ✅ power-of-two-choices, outlier detection, client-side LB, service discovery, HTTP/2 pinning, draining, zone-aware routing | ✅ |
| §1.25 resilience | §17 | ✅ timeout taxonomy, deadline propagation, jitter variants, retry budget, breaker parameters, the fallback trap, hedged/tied requests | ✅ |
| §1.26 multi-region | §18 | ✅ failover runbook, failback, cross-region messaging, residency, 2026 managed primitives, the dependency trap | ✅ |
| §1.27 read models | §19 | ✅ CQRS vs replica, event sourcing, view-maintenance strategies, backfill/replay, lag as a UI concern | ✅ |
| §1.28 blobs | §20 | ✅ multipart detail, metadata state machine, range requests, dedupe, storage classes, durability≠availability | ✅ |
| §1.29 observability | §21 | ✅ percentiles don't average, coordinated omission, golden signals, tracing, load-testing-to-failure, synthetics | ✅ |
| §1.30 migration | §22 | ✅ backfill mechanics, reconciliation tooling, one-way doors, strangler routing, consistency-model change | ✅ |
| §1.31 vocabulary | — | ✅ entire section | |
| §2.1 master tables | — | ✅ all five, including the amortised-vs-incident column | |
| §2.2 cost modelling / dollar axis | — | ✅ entire section | |
| §2.3 the eighteen proofs | one worked example in §3 | ✅ all of them | ✅ |
| §2.4 consistency per operation | §9 (2 lines) | ✅ uniqueness as hidden linearizability, bounded staleness, UI compensation, write skew | ✅ |
| §2.5 skew and fairness | §8 | ✅ Zipf, multi-tenant fairness, shuffle sharding and its combinatorics, adaptive capacity, GAC, detection | ✅ |
| §2.6 sharding strategy project | §8 | ✅ key candidates, routing implementations, split protocol, cross-shard pagination, organisational cost | ✅ |
| §2.7 distributed transactions | §13/§26 (saga mentioned) | ✅ 2PC mechanics, TCC, escrow/reservation, stuck sagas, compensations≠rollbacks, Calvin | ✅ |
| §2.8 streaming and windows | §19 (CDC only) | ✅ lambda/kappa, event time, watermarks, window types, late data, EOS in the processor, pre-aggregation ladder | |
| §2.9 tail latency | §21 (one clause) | ✅ variability sources, hedged/tied/micro-partitions, probation, budget arithmetic | ✅ |
| §2.10 overload and collapse | §15 (load shedding) | ✅ queue management, LIFO, deadline dropping, cascading failure, metastable failure, recovery steps, the autoscaling trap | ✅ |
| §2.11 health and failure detection | §16 | ✅ probe kinds, outlier detection, grey failure, phi-accrual, the detector impossibility, the death spiral | ✅ |
| §2.12 cells and blast radius | §18 (one row) | ✅ entire section | ✅ |
| §2.13 geospatial | — | ✅ entire section | |
| §2.14 probabilistic structures | §19 (HLL named once) | ✅ entire section | ✅ |
| §2.15 real-time delivery | §25 (inside chat) | ✅ transport comparison, connection capacity arithmetic, webhooks, deploy/reconnect, live-vs-durable reconciliation | ✅ |
| §2.16 security and tenancy | — | ✅ entire section | |
| §2.17 deployment and rollout | — | ✅ entire section | |
| §2.18 organisational face | §1 (one paragraph on L6) | ✅ entire section | ✅ |
| §2.19 testing a design | — | ✅ entire section | |
| §2.20 decision tables | scattered | ✅ consolidated | ✅ |
| §2.21 currency 2026 | — | ✅ entire section | |
| §3.1 consistent hashing internals | §8 (one paragraph) | ✅ the properties, the variants, bounded loads, power-of-two, the hot-key trap | ✅ |
| §3.2 the Dynamo lineage | §10 (hinted handoff named) | ✅ entire section including Dynamo≠DynamoDB and the admission-control evolution | ✅ |
| §3.3 consensus, leases, fencing | §7/§10 (fencing named once) | ✅ entire section | ✅ |
| §3.4 time and clocks | §10 (clock skew named) | ✅ entire section: Lamport, vector, HLC, TrueTime, commit-wait, uncertainty intervals | ✅ |
| §3.5 CRDTs | §10 (one clause) | ✅ entire section | ✅ |
| §3.6 storage-engine facts | §6 (fit table only) | ✅ entire section | |
| §3.7 broker internals | §12 (queue vs log) | ✅ ISR arithmetic, partition-count one-way door, compaction, tiered storage, zero-copy | ✅ |
| §3.8 edge and CDN internals | §11/§20 | ✅ anycast, origin shield, cache-control semantics, slow start, TIME_WAIT | ✅ |
| §3.9 limiter internals | §15 | ✅ the lazy-integral proof, the boundary proof, the interleaving proof, Lua/cluster constraints, GCRA, adaptive concurrency, breaker internals | ✅ |
| §3.10 queueing theory | — | ✅ entire section: Little, M/M/1, USL, Amdahl, open vs closed, batching | |
| §3.11 failure pathologies | scattered traps | ✅ consolidated with the sixteen named pathologies | ✅ |
| §3.12 postmortem case studies | — | ✅ entire section, including static stability | |
| PART 4 — all fourteen build clusters | — | ✅ everything; the guide has no code beyond one 10-line idempotency snippet | ✅ |
| §5.1 delivery language | §27 | ✅ correction, closing summary, "I don't know", hostile challenge, board management | ✅ |
| §5.2 L5/L6 rubric | §1 (one paragraph) | ✅ the two-round loop, the downlevel finding, the over-abstraction trap | ✅ |
| §5.3 worked designs | §23–§26 (four) | ✅ twenty-six more, and the four existing ones need their extras added | ✅ |
| §5.4 question bank | — | ✅ entire section (~92 questions) | |
| §5.5 trap index | ~10 `**Trap:**` markers inline | ✅ all must be preserved and the remaining ~60 added | |
| §5.6 retention drills | — | ✅ entire section | |
| §5.7 checklist extension | closing checklist (~70 lines) | ✅ must be preserved verbatim in meaning and extended | ✅ |

Two things the write pass must do beyond adding content:

1. **Preserve every existing `**Trap:**` marker and every existing checklist assertion.** The
   guide's ten traps and ~70 assertions are all correct as written; nothing in this syllabus
   contradicts them. They are a floor, not a draft.
2. **Re-verify before writing, and drop rather than reconstruct.** Every `[CURRENCY]` leaf (vendor
   prices, service limits, product capabilities, Envoy and Kafka defaults, the TrueTime ε, the
   DynamoDB MRSC Region constraint) and every `[RESEARCH]` leaf whose source above is marked
   secondary must be re-fetched. Any number that cannot be confirmed is written as an order of
   magnitude with its basis stated, or omitted. No invented URLs, no invented constants, no
   reconstructed postmortem details.

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.31 | 446 |
| PART 2 — Intermediate | §2.1–§2.21 | 232 |
| PART 3 — Under the hood | §3.1–§3.12 | 144 |
| PART 4 — Build it | §4.1–§4.14 | 114 |
| PART 5 — Interview, worked designs, retention | §5.1–§5.7 | 153 |
| **Total** | **85 sections** | **1,089 leaves** |

Counts are grep-measured on numbered leaf lines, not estimated. Note that §5.3's 31 leaves are
design *clusters* of five sub-leaves each, and §5.4's 14 leaves enumerate ~92 questions, so the
write-pass workload in PART 5 is larger than its leaf count suggests.

Tag occurrences, also grep-measured (a leaf may carry several tags, and a handful of occurrences
fall in the legend, the gap table and the trap index rather than on a leaf):

| Tag | Occurrences |
|---|---|
| `[RESEARCH]` | 191 |
| `[PROVE]` | 227 |
| `[BUILD]` | 122 |
| `[TRAP]` | 120 |
| `[NUM]` | 110 |
| `[SAY]` | 94 |
| `[SOURCE]` | 87 |
| `[CURRENCY]` | 48 |

Every `[RESEARCH]` and every `[CURRENCY]` occurrence must be re-verified against its cited source
in the write pass before any constant from it is written down, and every `[CURRENCY]` claim must
additionally be date-stamped in the text. `[X-REF]` leaves point at guides 03, 04, 05, 06, 08, 09,
10, 11, 12, 13, 14, 15, 18, 19 and 20.

**Target restated for the write pass:** state of practice as of **2026-09-02**. The three deltas
most likely to make an otherwise-correct answer stale are (1) multi-Region strong consistency now
being a managed-service option rather than a Spanner-only capability, (2) cell-based architecture
and shuffle sharding having become published, expected vocabulary, and (3) the interview rubric's
shift toward operational maturity and explicit penalties for memorised architectures at L6.












