# 09 — Messaging & Caching

**What this decides:** where the prep plan's Kafka track starts (concepts vs
zero), and whether caching gets promoted from side-mentions to a study block.
L1–L2 here is acceptable at 3–4 YOE if you haven't worked with queues; L0 on
the caching half is a gap (caching is universal).

---

## Part A — Messaging ladder

### Q1 [L1] explain-back — Why put a queue between two services?
Give the benefits AND what you give up.
**Strong answer:** decoupling (temporal + availability), buffering bursts,
independent scaling of consumers, retryability. Costs: eventual consistency
(caller doesn't know outcome), operational surface, harder debugging/
tracing, ordering questions. Both directions required — benefits-only = 0.5.

### Q2 [L2] explain-back — Delivery semantics
At-most-once vs at-least-once vs exactly-once: define each, say which is the
practical default, and why exactly-once is hard.
**Strong answer:** at-most-once = ack before process (may lose);
at-least-once = ack after process (may duplicate — the practical default);
exactly-once requires coordination between message system and your side
effects (a DB write + an ack are two systems — can't be atomic without
transactions/idempotency). "Exactly-once processing is really at-least-once
+ idempotent handling" = full credit.

### Q3 [L3] scenario — The duplicate
Your consumer processed a payment event, wrote to the DB, then crashed
before acknowledging. The broker redelivers. Design idempotent handling
concretely.
**Strong answer:** event carries a stable id/idempotency key; consumer
does `INSERT ... ON CONFLICT DO NOTHING` or checks a processed-events table
with a UNIQUE constraint IN THE SAME transaction as the business write;
redelivery becomes a no-op. Bonus: dedup window/TTL, why an in-memory "seen"
set fails (restarts, multiple instances). The same-transaction detail is the
discriminator.

### Q4 [L3] scenario — The poison message
One malformed message crashes the consumer, which restarts, reads the same
message, crashes again — forever. The queue backs up. Fix the design.
**Strong answer:** bounded retries with backoff, then dead-letter queue;
alert on DLQ depth; distinguish retryable (downstream timeout) from
non-retryable (parse error — straight to DLQ); DLQ needs a replay/inspection
story, it's not a trash can. Bonus: this blocking behavior differs by
system — ordered-partition consumers (Kafka) get head-of-line blocking,
SQS-style queues just redeliver independently.

### Q5 [L2] explain-back — Ordering
Why is global ordering across a distributed queue basically unavailable, and
what's the standard compromise?
**Strong answer:** parallelism requires multiple lanes (partitions/shards/
consumers) — total order would serialize everything; compromise: order
within a partition, partition by the entity that needs ordering (key =
user-id/order-id). Bonus: hot-key skew as the new problem this creates.

### Q6 [L2] discriminator — Queue vs log
SQS-style queue vs Kafka-style log: what's the fundamental model difference?
**L1 tier:** "Kafka is faster / for streaming." **L2 tier (=1.0):** queue —
message consumed & deleted, broker tracks delivery, competing consumers; log
— append-only, messages retained by policy, CONSUMERS track their own
offsets → replay is free, multiple independent consumer groups read the same
stream. **L4 bonus:** replay as a superpower (reprocessing, new consumers,
debugging); when a plain queue is simply the right tool (task distribution,
no fan-out/replay needs). Score 0 here is fine pre-plan; it calibrates the
Kafka track's starting floor.

### Q7 [L4] probe — The dual-write problem
Your service, in one method, saves an order to Postgres AND publishes
`OrderCreated` to a broker. What can go wrong, and do you know a pattern for
it? *(L0 expected if you haven't met it — answer honestly; this calibrates
the plan's Day 74.)*
**Strong answer:** two systems, no shared transaction: commit-then-publish
can lose the event (publish fails); publish-then-commit emits events for
rolled-back writes. Pattern: transactional outbox (event row written in the
same DB transaction, relayed asynchronously) or CDC. Naming the failure
windows correctly, even without the pattern name = 0.5.

---

## Part B — Caching ladder

### Q8 [L2] explain-back — Cache-aside walkthrough
Describe the read and write paths of cache-aside for a `getProduct(id)`
call, and where staleness sneaks in.
**Strong answer:** read: try cache → miss → load DB → populate with TTL →
return. Write: update DB → INVALIDATE (delete) cache key — why delete beats
update-in-place (race between two writers setting stale values). Staleness:
between DB write and invalidation, or invalidation failure; TTL as the
backstop. Bonus: contrast write-through/write-behind in one line each.

### Q9 [L3] scenario — Stampede
A hot cache key (product page of the day) expires; 5,000 requests miss
simultaneously and hammer the DB, which browns out. Name three mitigations.
**Strong answer (any 3):** TTL jitter (stagger expiry); single-flight /
per-key lock so one loader populates while others wait or serve stale;
refresh-ahead (renew before expiry); serve-stale-while-revalidate; request
coalescing at the client. Bonus: negative caching for "not found" storms.

### Q10 [L4] discriminator — What do you cache, and how do you know it's working?
Pick a real endpoint from your current job. What would you cache, with what
key, TTL, and invalidation? What metrics prove it helps?
**Strong answer:** concrete key design (includes every input that changes
the response — the cache-key-too-narrow bug), TTL justified by staleness
tolerance, explicit invalidation path for writes; metrics: hit ratio,
origin/DB load delta, p99 latency; knows a low hit ratio can make a cache a
net negative (extra hop). Grounding in a real endpoint with a defensible
key = 1; generic textbook answer = 0.5.

---

## Breadth checklist (rate 0–3)

- [CORE] Retries with exponential backoff + jitter — why jitter
- [CORE] Redis — used it? For what? Data structures beyond GET/SET (hash, sorted set, TTL)?
- [CORE] Async processing in your current job — is there ANY queue/scheduled-job flow you can describe end-to-end?
- Kafka hands-on (produced/consumed anything, even tutorial-level)
- SQS / RabbitMQ / any broker hands-on
- Consumer groups / competing consumers (concept)
- Pub/sub vs point-to-point (fan-out concept)
- Backpressure — what happens when producers outrun consumers (heard of?)
- Message schema evolution — what happens when the producer adds a field? (heard of the problem?)
- Outbox pattern (heard of? — pairs with Q7)
- Event-driven vs request-driven architecture trade-offs (can you argue either side?)
- Scheduled jobs: cron/`@Scheduled` — the multiple-instances double-run problem (heard of?)
- Distributed locks (Redis SETNX-style) — heard of, and heard why they're tricky?
- Local/in-process cache (Caffeine/Guava) vs distributed cache — trade-off
- CDN caching as a layer (ties to 07)
- Eviction policies: LRU/LFU — what your cache does when full
