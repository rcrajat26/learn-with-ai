# 14 — Messaging & Queues

Scope: how brokers actually behave, what the delivery guarantees really mean, and the failure modes
that come up in every async-architecture interview. Section 2 is the most important thing on this
page — it is the single most-missed concept in the diagnostic papers.

---

## 1. Why queues exist

Three reasons, and you should be able to name which one applies to any given design:

1. **Decoupling.** The producer doesn't know or care who consumes, how many consumers there are, or
   whether they're up right now. You can add a second consumer (analytics, audit, search indexing)
   without touching the producer. Synchronous HTTP couples the caller to the callee's availability,
   latency, and interface.
2. **Buffering / load levelling.** Traffic is spiky; capacity is not. A queue absorbs a 10× burst and
   lets consumers drain it at a sustainable rate. Without it, a burst either drops requests or
   overwhelms the database. The queue converts a *throughput* problem into a *latency* problem, which
   is usually the better problem to have.
3. **Asynchrony.** The user doesn't need to wait for the email to send, the PDF to render, or the
   warehouse to be notified. Ack the request in 50 ms and do the slow work off the hot path.

Also: **retries with durability**. If the consumer crashes mid-processing, the message is still there.
An in-process `@Async` executor loses everything on restart — that is the core reason not to use one
for work that matters.

**Cost of adopting a queue:** eventual consistency (the caller no longer knows the work succeeded),
harder debugging (the flow spans processes and time), duplicate delivery you must handle, ordering
you mostly don't get, and a new piece of infrastructure to operate. Don't add a queue where a
synchronous call is honest and adequate.

---

## 2. THE BROKER LIFECYCLE — read this twice

> ### The single most important fact on this page
>
> **When consumers are down, messages sit in the queue, durably, waiting.**
> **They do NOT go to the dead-letter queue.**
>
> A message reaches a DLQ **only** after it has been **delivered to a consumer** and that consumer
> **failed to process it N times** (or the message exceeded its retention/max-receives policy).
>
> No delivery attempt → no failure → no DLQ. A queue with no consumers running is a queue that is
> **filling up**, not a queue that is dead-lettering.

Walk the lifecycle explicitly:

```
producer.send(msg)
    │
    ▼
[ broker persists the message to disk / replicates it ]        ← durable now
    │
    ├── no consumers connected?  →  message WAITS.  Queue depth grows.
    │                               Nothing is lost until the retention
    │                               period expires (SQS: up to 14 days,
    │                               Kafka: retention.ms, default 7 days).
    │
    ▼
[ consumer connects and polls ]
    │
    ▼
delivery attempt #1  ──► success ──► ack/commit ──► message removed (SQS)
    │                                              or offset advances (Kafka)
    ├─► exception / no ack before visibility timeout
    │
    ▼
delivery attempt #2, #3, ... (with backoff)
    │
    ▼
attempt N fails  ──►  DLQ  ← the ONLY normal path into a dead-letter queue
```

**Why people get this wrong.** "Consumers are down" *feels* like a failure, and DLQ is where failures
go, so the association is intuitive and wrong. The broker has no concept of "the consumer is down."
It has a queue of messages and a set of connected consumers. Zero connected consumers is a
completely legitimate state — it is exactly what happens during every deploy of your consumer
service, for 30 seconds, several times a day.

**What actually happens when consumers are down, in order:**

1. Producers keep publishing successfully. They are unaffected — that's the decoupling working.
2. **Queue depth / consumer lag grows.** This is your alert signal (see §12).
3. Broker disk usage grows. On a self-managed broker this can eventually fill the disk and take the
   broker down — a real, if slower, failure.
4. When consumers come back, they drain the backlog. Throughput is now the constraint: a 2-hour
   outage on a 1,000 msg/s topic leaves 7.2 M messages, and if your consumers only do 1,200 msg/s
   you need 10 hours to catch up. **You must scale consumers out to recover**, which for Kafka means
   you needed enough partitions provisioned ahead of time (§8).
5. Messages older than the retention period are **deleted** — silently. That is the real data-loss
   risk of a long consumer outage, and it has nothing to do with the DLQ.

**Corollary questions you should be ready for:**
- *"Consumers are down for 3 hours — where are the messages?"* → In the queue, durable, unread.
  Depth is up; nothing is in the DLQ.
- *"How do you know?"* → Queue depth / consumer lag metric, and DLQ depth being flat.
- *"What breaks first?"* → Broker disk (self-managed) or retention expiry, not the DLQ.
- *"A message is in the DLQ. What do you know for certain?"* → It was **delivered** at least N times
  and processing **threw** every time. The bug is in the consumer or the message, not the transport.

---

## 3. The three roles

**Producer.** Serialises a message and sends it. Cares about: did the broker durably accept it
(acks/confirms), which partition/queue, and what to do on send failure (retry, buffer, fail the
request). A producer that fires-and-forgets with `acks=0` has no idea whether anything was stored.

**Broker.** Receives, **persists**, replicates, and hands out messages. Tracks who has consumed what
(SQS: per-message in-flight state; Kafka: a committed offset per consumer group per partition).
Enforces retention, visibility timeouts, and DLQ redrive policies. This is the durable, stateful part
of the system and it is why "just use a queue" means "operate another database."

**Consumer.** Polls (both SQS and Kafka are pull-based; the "push" feel of a Spring listener is a
poll loop underneath), processes, and then **acknowledges**. The position of that acknowledgement
relative to the processing is the entire delivery-semantics question (§4).

---

## 4. Delivery semantics — determined by where you ack

This is the whole topic in one idea: **the guarantee you get is a consequence of when you
acknowledge, relative to when you do the work.**

### At-most-once — ack *before* processing
```java
var msg = consumer.poll();
acknowledge(msg);          // ack first
process(msg);              // crash here → message is gone forever
```
Possible loss, no duplicates. Only acceptable when the data is genuinely disposable (metrics samples,
best-effort telemetry). Almost never right for business events.

### At-least-once — ack *after* processing
```java
var msg = consumer.poll();
process(msg);              // do the work
acknowledge(msg);          // crash between these two lines → redelivery
```
No loss, **duplicates possible**. The window is small but it is always there: the process can die
after the DB commit and before the ack, and the broker will redeliver. This is the default of SQS and
of Kafka with manual commit-after-process, and it is **the correct default for virtually every
production system**.

### Exactly-once — the honest answer

End-to-end exactly-once *delivery* over an unreliable network is impossible: the two-generals problem
means the sender can never be certain its ack arrived. What is achievable is **exactly-once
processing semantics** — at-least-once delivery combined with an **idempotent consumer**, so
duplicate deliveries have no duplicate effect.

Kafka's "exactly-once semantics" is real but narrow: transactional producers plus
`isolation.level=read_committed` give atomic consume-transform-produce **within Kafka**. The moment
your side effect is an external database, an email, or a payment API, that transaction doesn't cover
it and you are back to idempotency.

**Say this in an interview:** *"I'd design for at-least-once delivery with an idempotent consumer.
Exactly-once delivery isn't achievable across a network; exactly-once *effect* is, and idempotency is
how you get it."*

### Idempotent consumer — the concrete design

The mechanism that actually works: give every message a stable **event ID** (assigned by the
producer, not by the broker — a broker-assigned ID may differ across redeliveries), and record
processed IDs in the **same transaction** as the side effect.

```java
@Transactional
public void handle(OrderPlaced event) {
    try {
        processedEvents.insert(event.eventId());   // UNIQUE constraint on event_id
    } catch (DuplicateKeyException e) {
        log.debug("Duplicate event {}, skipping", event.eventId());
        return;                                    // already processed — no-op
    }
    orders.create(event);                          // the actual side effect
    // both rows commit together, or neither does
}
```

```sql
CREATE TABLE processed_events (
    event_id    UUID PRIMARY KEY,
    consumer    TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Why the same transaction is non-negotiable.** If you insert the ID first and commit, then do the
work in a second transaction, a crash between them means the ID says "done" and the work never
happened — you have converted at-least-once into at-most-once, which is strictly worse. If you do the
work first and record the ID after, a crash between them means a duplicate. Atomicity is what makes
the pattern correct.

**Alternatives, ranked:**
1. **Naturally idempotent operations.** `SET status = 'SHIPPED'` is idempotent by construction. Best
   possible answer — no bookkeeping at all. `balance = balance + 10` is **not**.
2. **Upsert on a business key.** `INSERT ... ON CONFLICT (order_id) DO UPDATE`. Excellent when the
   message maps to one row.
3. **The dedup table above.** General purpose. Needs a cleanup job (delete rows older than the
   redelivery window — typically retention period + margin), or the table grows forever.
4. **Redis SETNX with a TTL.** Fast, but it's a *separate* system from your DB, so it cannot be in the
   same transaction — there's a window where Redis says "done" and the DB rolled back. Acceptable for
   low-stakes deduplication; not for money.
5. **Optimistic concurrency / version numbers.** Reject an event whose version is ≤ the stored
   version. Good for state-machine updates and handles out-of-order delivery too.

> **Trap:** Making the *side effect* idempotent but not the *whole handler*. If the handler writes to
> the DB idempotently and then sends an email, a redelivery skips the DB write and sends a second
> email. Every non-idempotent effect in the handler needs covering — which is a strong argument for
> handlers that do exactly one thing.

---

## 5. Poison messages, retries, and the DLQ

A **poison message** is one that will fail every time it's processed: malformed JSON, a schema the
consumer doesn't understand, a reference to a deleted entity, an unsatisfiable business rule. Retries
cannot help it, and without a DLQ it blocks the queue forever (Kafka) or cycles indefinitely (SQS),
burning capacity and filling logs.

### Classify the failure before you retry

| Failure | Retry? | Action |
|---|---|---|
| Transient — timeout, 503, deadlock, connection reset | **Yes**, with backoff | it will probably work in 2 s |
| Poison — deserialisation error, validation failure, 400 | **No** | send straight to DLQ; retrying wastes capacity and delays everything behind it |
| Ambiguous — 500 from a downstream | Yes, bounded | might be transient; cap the attempts |

Retrying a message that can never succeed is the most common wasteful pattern. Fail fast on
non-retryable errors.

### Backoff with jitter

Immediate retries hammer a struggling dependency at exactly the moment it needs relief. Exponential
backoff (1 s, 2 s, 4 s, 8 s, 16 s) spaces attempts out. **Jitter** is what stops synchronised retry
storms: without it, 5,000 messages that all failed at t=0 all retry at t=1, t=2, t=4 — a coordinated
wave that re-kills the recovering service.

```java
long base = 1000L << attempt;                       // 1s, 2s, 4s, 8s...
long capped = Math.min(base, 60_000L);
long delay = ThreadLocalRandom.current().nextLong(capped);   // full jitter
```
Full jitter (uniform in `[0, capped]`) is the standard recommendation; it spreads load best.

**Where to retry matters.** In-process retry (Spring Retry, Resilience4j) holds the consumer thread
and blocks the partition. Broker-level retry (SQS visibility timeout, or a Kafka retry-topic chain
with increasing delays) releases the thread and lets other messages proceed. For anything beyond a
couple of fast attempts, prefer broker-level.

### DLQ operations — the part people forget

A DLQ that nobody looks at is a data-loss mechanism with extra steps.

- **Alert on DLQ depth > 0.** Not on a threshold — on *any* message. One poison message today is a
  schema bug that becomes 100,000 tomorrow.
- **Keep enough context to diagnose:** the original message, the exception and stack trace, the number
  of attempts, timestamps, the correlation ID (topic 20), and the consumer version. Without these,
  triage is guesswork.
- **Have a replay path** — a tool or endpoint that moves messages from DLQ back to the main queue
  (SQS has native redrive; Kafka needs a small replay app). Test it before you need it at 3am.
- **Replay is only safe if consumers are idempotent** — and after a fix, replayed messages are
  frequently duplicates of ones that partially succeeded. §4 is the prerequisite for §5.
- **Set retention on the DLQ** (SQS max 14 days) and treat expiry as real data loss.

> **Trap:** DLQ-ing a message but committing the offset in a way that loses it if the DLQ send fails.
> Order of operations: send to DLQ, confirm the send succeeded, *then* ack the original. If the DLQ
> send fails, don't ack — let it redeliver.

---

## 6. Ordering

**The honest statement: ordering is guaranteed only within a partition (Kafka) or a message group
(SQS FIFO), and only if you have one consumer processing it serially.**

Why global ordering is unavailable: it requires a single serialisation point, which means one
partition and one consumer — no parallelism, no scaling. Ordering and throughput are directly
opposed. Any system offering "total ordering at scale" is either lying or very slow.

**Partition-key choice is a design decision.** Kafka hashes the message key to pick a partition, so
all messages with the same key land in the same partition and are therefore ordered relative to each
other. Choose the key to match your ordering requirement:

- Need per-order events in order? Key = `orderId`.
- Need per-customer in order? Key = `customerId`.
- Don't need ordering? Use `null` (round-robin/sticky batching) for the best balance.

Pick the **narrowest** key that satisfies the requirement — a broader key means fewer effective
parallel streams.

**Hot-key skew.** If one key is far more active than the rest — a celebrity user, a whale customer, a
`null` tenant ID, a "default" account — its partition gets a disproportionate share of traffic. That
one consumer becomes the bottleneck while the others idle. Symptoms: lag concentrated on a single
partition, uneven CPU across consumer instances.

Mitigations: composite keys (`customerId + ":" + bucket` where bucket is `hash(orderId) % 4`) if
ordering can be relaxed to sub-streams; route the hot key to a dedicated topic/consumer; or accept it
and provision for the peak. There is no elegant fix — this is a real design constraint.

> **Trap:** Assuming a single-partition topic gives you ordering with multiple consumer instances. It
> gives you ordering *and* a hard cap of one active consumer for that topic. The other instances sit
> idle. You have chosen ordering over all scalability, usually without meaning to.

> **Trap:** Ordering guarantees vanish if you process messages concurrently *within* a consumer. A
> handler that hands each message to an executor pool destroys per-partition ordering even though the
> broker delivered them in order.

Also worth stating: **out-of-order arrival across partitions is normal**, so downstream logic should
be order-tolerant where possible (version numbers, `updated_at` comparisons, last-write-wins on a
timestamp) rather than assuming sequence.

---

## 7. Queue vs log — SQS vs Kafka

This is the highest-leverage distinction in the topic, because it determines what you can build.

| | **Queue (SQS, RabbitMQ)** | **Log (Kafka, Kinesis, Pulsar)** |
|---|---|---|
| Model | messages in a work queue | an append-only, ordered, immutable log |
| After consumption | **message is deleted** | **message stays** until retention expires |
| Consumer position | broker tracks per-message in-flight state | consumer tracks an **offset** per partition |
| Second independent consumer | needs fan-out (SNS→SQS, or a second queue) | just a new **consumer group** reading the same log |
| Replay | impossible — it's gone | trivial — reset the offset |
| Ordering | none (standard SQS); per-group (FIFO) | per-partition, always |
| Scaling consumers | add consumers freely, any number | capped at partition count |
| Throughput | high | very high (sequential disk I/O, zero-copy, batching) |
| Operational load | fully managed, near zero | significant unless you buy MSK/Confluent |

**The mental test — post-consumption fate:** in a queue, consuming *removes*. In a log, consuming
*advances a pointer*. Everything else follows from that one difference.

**Consequences that decide your architecture:**

- **Adding a consumer later.** Kafka: new consumer group, start from offset 0, replay all history —
  zero impact on existing consumers. SQS: the messages are gone; you must have set up the fan-out
  (SNS topic with multiple SQS subscribers, or EventBridge) *in advance*. Retrofitting fan-out onto a
  point-to-point SQS design is a genuine migration.
- **Reprocessing after a bug.** You shipped a consumer that miscalculated something for 3 days.
  Kafka: fix the code, reset the offset 3 days back, replay. SQS: the data is unrecoverable from the
  queue; you need the source system.
- **Event sourcing / stream processing / building a new read model** requires a log. A queue cannot
  do it.

**Choose a queue when:** the work is a task ("send this email", "resize this image"), one logical
consumer, no replay need, and you want zero ops. **Choose a log when:** the message is an *event* that
multiple systems care about, you need replay, ordering matters, or you're building stream processing.

Naming discipline helps: **commands** ("do this", one handler, queue-shaped) vs **events** ("this
happened", many interested parties, log-shaped).

---

## 8. Kafka essentials

**Topic** — a named stream. **Partition** — the unit of parallelism *and* ordering; a topic is split
into N partitions, each an ordered append-only log on disk, replicated to `replication.factor`
brokers with one **leader** handling reads/writes.

**Offset** — a monotonically increasing position per partition. The consumer's committed offset (in
the internal `__consumer_offsets` topic) is the only state the broker keeps about progress.

**Consumer group** — a set of consumer instances sharing a `group.id`. Kafka assigns partitions
across the group so that:

> **Each partition is consumed by exactly one consumer in the group at any time.**

That's the rule that determines your scaling ceiling: **a consumer group cannot usefully have more
instances than the topic has partitions.** 12 partitions, 20 instances → 8 sit idle. This is the most
common Kafka scaling surprise, and it's why you over-provision partitions up front (you can add
partitions later, but doing so **changes the key→partition mapping** and breaks ordering for existing
keys — so it's not a free operation).

**Rebalancing.** When an instance joins, leaves, or is deemed dead (`session.timeout.ms` /
`max.poll.interval.ms`), partitions are reassigned. Historically this was "stop the world" for the
whole group; cooperative/incremental rebalancing reduces the disruption. A consumer whose processing
exceeds `max.poll.interval.ms` gets kicked out mid-batch, the partition is reassigned, the work is
redone elsewhere — and you see a group stuck in a **rebalance loop**, consuming nothing while
appearing "up". Fix: process faster, reduce `max.poll.records`, or raise the interval.

**Head-of-line blocking.** Within a partition, messages are processed in order. One slow or failing
message blocks **everything behind it in that partition**. There's no "skip it and come back". This is
the price of ordering, and it's why the retry-topic pattern exists: on failure, publish the message to
`orders.retry.5s`, commit the offset, and move on — the main partition keeps flowing while a separate
consumer handles the delayed retry. After the last retry topic, it goes to `orders.dlq`.

**Consumer lag** = (log-end offset) − (committed offset), per partition. It is *the* health metric for
a Kafka consumer:
- Lag flat and near zero → healthy.
- Lag rising steadily → consumers slower than producers; scale out (up to partition count) or make
  processing faster.
- Lag rising on **one partition only** → hot key (§6) or one stuck instance.
- Lag frozen (not rising, not falling) with producers active → consumers are stuck or rebalancing.

**Producer durability.** `acks=0` (fire and forget, can lose), `acks=1` (leader only — loses data if
the leader dies before replication), `acks=all` + `min.insync.replicas=2` (durable; the standard for
anything that matters). `enable.idempotence=true` prevents duplicates from producer-side retries.

**Retention** is time- or size-based (`retention.ms`, default 7 days), or **compaction** (keep only
the latest value per key — turns the topic into a changelog/snapshot, ideal for CDC and state
restore).

---

## 9. SQS specifics

**Standard queues:** virtually unlimited throughput, **at-least-once** delivery, **best-effort
ordering** (i.e. none). The default and the right choice most of the time.

**FIFO queues:** exactly-once *processing* within a 5-minute dedup window, strict ordering **within a
message group ID**. Throughput is capped (300 msg/s, 3,000 with batching per group, higher with
high-throughput mode). Message group ID plays the same role as a Kafka partition key.

**Visibility timeout — the core SQS mechanism.** When a consumer receives a message, it is not
deleted; it becomes **invisible** to other consumers for the visibility timeout (default 30 s). Then:
- Consumer calls `DeleteMessage` → gone for good.
- Consumer crashes or the timeout expires → the message becomes **visible again** and is redelivered.

This is how SQS gets at-least-once without tracking consumer liveness. Consequences:

> **Trap:** Processing takes longer than the visibility timeout. The message reappears and a *second*
> consumer starts working on it while the first is still going. Now you have genuine concurrent
> duplicate processing — not just a duplicate, but two workers racing. Fix: set the visibility timeout
> above your p99.9 processing time, and/or call `ChangeMessageVisibility` to extend a heartbeat while
> working. This is the #1 SQS bug.

Other SQS mechanics worth knowing:
- **`maxReceiveCount`** in the redrive policy is exactly the "N" from §2: after N receives without
  deletion, SQS moves the message to the DLQ.
- **Long polling** (`WaitTimeSeconds=20`) — always use it. Short polling burns API calls (money) and
  can return empty even when messages exist, because it samples a subset of servers.
- **Delay queues** and per-message `DelaySeconds` (up to 15 min) for simple scheduled work.
- **Batching** — up to 10 messages per API call, a 10× cost and throughput improvement. Note partial
  batch failures need `ReportBatchItemFailures` or you'll re-deliver the whole batch.
- **256 KB max message size.** Larger payloads use the claim-check pattern: put the blob in S3, send
  the key.
- No replay, no fan-out on its own — pair with SNS or EventBridge for multiple subscribers (§7).

---

## 10. The dual-write problem and the transactional outbox

**The problem.** A handler must do two things: write to the database and publish an event.

```java
// BROKEN — two systems, no shared transaction
@Transactional
public void placeOrder(Order order) {
    orderRepository.save(order);          // commits to Postgres
    kafkaTemplate.send("orders", event);  // separate system, separate failure domain
}
```

There is no atomicity across a database and a broker. Four things can happen, two of them bad:
- DB commits, publish fails (broker down, network blip, pod killed between the lines) → **the order
  exists but no downstream system ever hears about it.** Silent, permanent inconsistency.
- Publish succeeds, DB rolls back → **downstream systems act on an order that doesn't exist.**

Wrapping it in `@Transactional` does not help — the Kafka send isn't part of the DB transaction. Nor
does sending *after* commit (`TransactionSynchronization.afterCommit`), which shrinks the window but
doesn't close it: the process can die immediately after commit.

Distributed transactions (XA/2PC) technically solve it and are rejected in practice: they need
support from both systems (Kafka has none), they hold locks across a network round trip, and a
coordinator failure leaves in-doubt transactions blocking everything.

### Transactional outbox — the standard answer

Write the event **into the same database, in the same transaction**, then publish it separately.

```sql
CREATE TABLE outbox (
    id             UUID PRIMARY KEY,
    aggregate_type TEXT        NOT NULL,
    aggregate_id   TEXT        NOT NULL,
    event_type     TEXT        NOT NULL,
    payload        JSONB       NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at   TIMESTAMPTZ
);
CREATE INDEX ON outbox (created_at) WHERE published_at IS NULL;
```

```java
@Transactional
public void placeOrder(Order order) {
    orderRepository.save(order);
    outboxRepository.save(OutboxEvent.of(order));   // same TX — atomic with the order
}
```

A separate **relay** polls unpublished rows, publishes to Kafka, and marks them published. If the
relay crashes after publishing but before marking, the event is published twice — which is fine,
because the consumer is idempotent (§4). **The outbox converts an unsolvable atomicity problem into a
duplicate-delivery problem, which you already know how to solve.** That trade is the whole insight.

**CDC as the relay.** Instead of polling, tail the database's replication log (Postgres WAL, MySQL
binlog) with **Debezium** and stream changes into Kafka. Advantages: no polling load, lower latency,
no missed rows, and it captures changes made by code paths that forgot to write to the outbox. It's
more infrastructure, but it's the production-grade version. You can even CDC the business tables
directly and skip the outbox — though the outbox gives you control over the *event schema* rather than
leaking your table schema to consumers, which is usually worth keeping.

**Inbox pattern** is the mirror image: record incoming event IDs in the DB transactionally to
deduplicate. That is exactly the `processed_events` table from §4.

---

## 11. Retry storms and cascading failure

**Mechanism.** A downstream service slows down. Callers time out and retry. Retries add load to the
already-struggling service, making it slower, causing more timeouts, causing more retries. Load
increases precisely when capacity is lowest. The service never recovers on its own, and when it does
come back, the accumulated backlog immediately re-kills it.

**Amplification is multiplicative across layers.** Three layers each retrying 3× = 27× the original
load. This is why "we added retries for resilience" is a common cause of outages rather than a cure.

**Defences, all of which you should be able to name:**

1. **Retry at one layer only.** Decide where — usually closest to the failure — and make the others
   pass errors through.
2. **Exponential backoff with jitter** (§5). Non-negotiable.
3. **Circuit breaker.** After a failure threshold, **open** the circuit and fail fast without calling
   the dependency at all. After a cooldown, go **half-open** and let a trickle through to test
   recovery; close on success, re-open on failure. This is what actually lets a downstream recover:
   it removes the load.
4. **Retry budgets / token buckets.** Cap retries at e.g. 10% of total requests. Bounds amplification
   even when everything is failing.
5. **Bulkheads.** Separate connection pools/thread pools per dependency so a hung dependency can't
   consume all your capacity (topic 10 §7).
6. **Load shedding.** Under overload, reject cheaply and immediately rather than queueing. A fast 503
   is much better than a slow timeout, both for the client and for you.
7. **Don't retry non-retryable errors** (4xx). It cannot succeed.

The queue version of the same failure: consumers fail, messages return to the queue, redelivery adds
load on top of new arrivals, and you get a redelivery storm. Backoff and DLQ-ing poison messages are
what break the loop.

---

## 12. Scheduled jobs, double-runs, and distributed locks

Run a `@Scheduled` job on 3 replicas and it runs 3 times. Sometimes harmless, sometimes you send
three invoices.

**Options, worst to best:**

1. **Pin to one instance** (a "leader" flag, or a separate single-replica deployment). Simple, but
   creates a single point of failure and drifts from your deployment model.
2. **Distributed lock.** Everyone tries to acquire; one wins and runs.
   ```java
   // Redis: SET key value NX PX 30000  — atomic acquire-if-absent with expiry
   if (redis.set(key, token, SetParams.setParams().nx().px(30_000)) != null) {
       try { runJob(); } finally { releaseIfOwner(key, token); }
   }
   ```
   Or ShedLock, which does this over your existing DB with no new infrastructure — usually the right
   pragmatic choice for Spring apps.

   > **Trap — the lock expiry hazard.** A lock must have a TTL, or a crashed holder blocks the job
   > forever. But a TTL means the lock can expire **while the holder is still working** (long GC
   > pause, slow query, stalled I/O). Now a second instance acquires it and both run concurrently —
   > exactly what the lock was for. Mitigations: set the TTL well above the worst-case runtime, extend
   > it with a heartbeat (a watchdog thread renewing while work proceeds), use a fencing token that
   > the resource checks so a stale holder's writes are rejected, and always release with a
   > compare-and-delete on your own token (Lua script) so you never delete someone else's lock.
   >
   > There is no lock design that is both safe and live under arbitrary pauses. Redlock in particular
   > is contested for exactly this reason. Locks reduce the probability of a double-run; they do not
   > eliminate it.

3. **Make the job idempotent.** `WHERE status = 'PENDING'` with an atomic claim, upserts, unique
   constraints on (job, period). Then a double-run is harmless and you can stop worrying about locks
   entirely. **This is the best answer** and the one interviewers are looking for.
4. **Use a real scheduler.** Kubernetes `CronJob` with `concurrencyPolicy: Forbid`, Quartz with a JDBC
   job store, or a managed scheduler (EventBridge Scheduler → SQS → workers). Note that Kubernetes
   `CronJob` guarantees *at-least-once*, not exactly-once, so idempotency still applies.

**When to avoid locks entirely:** high-frequency jobs (lock overhead dominates), work that can be
partitioned by key (each instance handles its own shard — no coordination needed), or anything where
the operation is naturally idempotent. Partitioning is underrated: it scales, whereas a lock
serialises.

---

## 13. Backpressure, end to end

**Backpressure** is a slow consumer's ability to make a fast producer slow down. Without it, the
buffer between them grows until something breaks — memory, disk, or latency.

**Where it exists naturally:**
- **TCP** — the receive window. A slow reader shrinks the window and the sender blocks. Free, and
  it's why blocking I/O has decent backpressure by default.
- **Pull-based brokers** (Kafka, SQS) — the consumer decides when to poll, so it can never be
  overwhelmed *by the broker*. But the broker's queue absorbs unlimited producer output, so the
  producer feels no pressure at all. **The queue converts backpressure into unbounded lag.**
- **Bounded thread pools with bounded queues** — `ThreadPoolExecutor` with an
  `ArrayBlockingQueue` and `CallerRunsPolicy`, which makes the submitting thread do the work and
  thereby slows the producer. `LinkedBlockingQueue` with the default unbounded capacity is a memory
  leak with a rejection policy that never fires.
- **Connection pool limits** (HikariCP) — a natural admission-control point.
- **Reactive Streams** (`request(n)`) — explicit, demand-driven backpressure in WebFlux/RxJava.

**Where it's missing and you must add it:**
- Unbounded in-memory queues anywhere in the pipeline. Every one is an OOM waiting for a traffic
  spike.
- Fire-and-forget async producers.
- **Virtual threads** — removing the thread limit removed an accidental concurrency cap. You now need
  explicit semaphores or `StructuredTaskScope` limits to avoid opening 50,000 concurrent DB
  connections (topic 10 §15).

**End-to-end thinking:** backpressure must propagate all the way to the *source*, or you've just moved
the queue. If the API layer keeps accepting requests and dropping them into a queue that consumers
can't drain, the system is failing — it just fails later and with worse symptoms (stale data, timed-out
clients, a backlog too large to ever catch up). The honest responses at the edge are **rate limiting**
and **load shedding**: reject work you cannot do, fast, with a `429`/`503` and a `Retry-After`.

Rule of thumb: **every buffer must be bounded, and every bound must have a defined behaviour when
hit** (block, reject, or drop — chosen deliberately, never by default).

---

## Atomic concept checklist

- [ ] Queues exist for decoupling, buffering/load-levelling, and asynchrony — know which one you're using.
- [ ] A queue trades a throughput problem for a latency problem, plus eventual consistency and duplicates.
- [ ] **Consumers down ⇒ messages WAIT in the queue, durably. They do NOT go to the DLQ.**
- [ ] **DLQ is reached ONLY after delivery + N processing failures.** No delivery, no DLQ.
- [ ] Consumers down: queue depth/lag rises, broker disk fills, and messages die at **retention expiry**.
- [ ] Recovering from a consumer outage is a throughput problem — you must scale out to drain the backlog.
- [ ] A message in the DLQ proves it was delivered and failed repeatedly — the bug is in the consumer or payload.
- [ ] Broker roles: producer sends, broker **persists and tracks progress**, consumer polls and acks.
- [ ] Both Kafka and SQS are **pull**-based; "push" listeners are poll loops.
- [ ] Delivery semantics are decided by **where you ack** relative to processing.
- [ ] At-most-once = ack first (can lose). At-least-once = ack after (can duplicate). Default to the latter.
- [ ] Exactly-once *delivery* is impossible across a network; exactly-once *effect* via idempotency is achievable.
- [ ] Kafka EOS only covers Kafka-to-Kafka; external side effects still need idempotency.
- [ ] Idempotent consumer: producer-assigned **event ID** + UNIQUE constraint, inserted in the **same transaction** as the side effect.
- [ ] Splitting the dedup insert and the work into two transactions converts at-least-once into at-most-once.
- [ ] Prefer naturally idempotent operations and upserts over a dedup table; dedup tables need cleanup.
- [ ] Redis-based dedup can't join the DB transaction — fine for low stakes, not for money.
- [ ] Poison messages fail forever; classify retryable vs non-retryable before retrying.
- [ ] Exponential backoff **with jitter** — jitter is what prevents synchronised retry waves.
- [ ] Full jitter: `random(0, min(base * 2^attempt, cap))`.
- [ ] In-process retry blocks the partition; broker-level retry (visibility timeout, retry topics) does not.
- [ ] Alert on DLQ depth > 0, keep the exception + attempts + correlation ID, and have a tested replay path.
- [ ] Replay is only safe with idempotent consumers.
- [ ] Send to DLQ *and confirm* before acking the original.
- [ ] Ordering exists only per Kafka partition / per SQS FIFO message group — never globally at scale.
- [ ] Ordering and throughput are directly opposed; pick the narrowest partition key that satisfies the need.
- [ ] Hot keys skew partitions: one consumer saturates while others idle; check per-partition lag.
- [ ] A single-partition topic caps you at one active consumer.
- [ ] Handing messages to an executor inside the consumer destroys the ordering the broker gave you.
- [ ] **Queue vs log:** consuming *deletes* vs consuming *advances an offset*. Everything follows from this.
- [ ] Kafka supports replay and new consumer groups reading history; SQS does not — plan fan-out (SNS/EventBridge) up front.
- [ ] Commands → queue; events → log.
- [ ] Kafka: topic → partitions (unit of parallelism *and* ordering) → offsets → consumer groups.
- [ ] **One partition is consumed by exactly one consumer per group** — partition count is your scaling ceiling.
- [ ] Adding partitions later changes key→partition mapping and breaks existing key ordering.
- [ ] Exceeding `max.poll.interval.ms` triggers eviction and a rebalance loop — the group looks up but consumes nothing.
- [ ] Head-of-line blocking within a partition; retry topics keep the main partition flowing.
- [ ] Consumer lag is the health metric; rising on one partition = hot key or a stuck instance.
- [ ] Durability: `acks=all` + `min.insync.replicas=2`; `enable.idempotence` for producer retries.
- [ ] Log compaction keeps the latest value per key — a changelog/snapshot.
- [ ] SQS visibility timeout: received ≠ deleted; expiry = redelivery.
- [ ] **Processing longer than the visibility timeout causes concurrent duplicate processing** — extend it or heartbeat.
- [ ] `maxReceiveCount` is the N that sends a message to the DLQ.
- [ ] Always use long polling; batch up to 10; 256 KB limit → claim-check via S3.
- [ ] Dual write (DB + broker) has no atomicity; `@Transactional` does not cover the broker send.
- [ ] Transactional outbox: write the event to the same DB in the same transaction, relay it separately.
- [ ] The outbox converts an atomicity problem into a duplicate problem — which idempotency already solves.
- [ ] CDC (Debezium tailing WAL/binlog) is the polling-free, production-grade relay.
- [ ] The inbox pattern is just the `processed_events` dedup table.
- [ ] Retry storms: load rises exactly when capacity falls; 3 layers × 3 retries = 27× amplification.
- [ ] Defences: retry at one layer, backoff+jitter, **circuit breaker**, retry budgets, bulkheads, load shedding.
- [ ] Scheduled jobs on N replicas run N times.
- [ ] A lock TTL can expire mid-work (GC pause) and permit a concurrent second run — locks reduce, never eliminate, double-runs.
- [ ] Mitigate with generous TTL + heartbeat renewal + fencing tokens + compare-and-delete release.
- [ ] **Idempotent jobs beat locks**; partitioning by key beats both, because it scales.
- [ ] Kubernetes `CronJob` is at-least-once even with `concurrencyPolicy: Forbid`.
- [ ] Backpressure = a slow consumer slowing a fast producer; TCP's receive window is the canonical example.
- [ ] A broker absorbs producer output, so it removes backpressure and converts it into unbounded lag.
- [ ] Unbounded in-memory queues are OOMs waiting to happen; virtual threads removed an accidental limit.
- [ ] Every buffer bounded, every bound with a deliberate policy: block, reject, or drop.
- [ ] At the edge, the honest form of backpressure is rate limiting and load shedding (`429`/`503` + `Retry-After`).