# 22 — System Design

Scope: the **composition layer**. Guides 09, 10, 12, 14, 15, 18, 19 and 20 each explain one
component's mechanism. This guide is about assembling them under a stated load, defending the
choices with arithmetic, and knowing which failure each choice buys you.

System design interviews go badly for two opposite reasons. Either the candidate draws boxes without
numbers ("we'll put Kafka here") and cannot say what breaks, or they dive into one component's
internals for 20 minutes and never produce a working system. The bar is: a design that survives the
stated load, whose bottleneck you can name, whose failure modes you have priced, delivered in 45
minutes.

---

## 1. What the interview actually measures

Five signals, roughly in scoring order:

| Signal | What it looks like when present |
|---|---|
| **Requirement discipline** | You extract QPS, data size, read/write ratio, latency target and consistency need *before* drawing anything. |
| **Quantitative reasoning** | Every component count is derived from a number, not asserted. "3 shards" follows from "6 TB / 2 TB per node". |
| **Trade-off articulation** | You name what you gave up, not just what you chose. |
| **Failure thinking** | For every box: what happens when it dies, when it's slow, when it's full. |
| **Communication / driving** | You structure the time, state assumptions out loud, and check in before moving on. |

The 45-minute clock, as a default budget:

| Phase | Minutes | Output |
|---|---|---|
| Requirements + scope cut | 5–8 | Functional list, non-functional numbers, explicit out-of-scope |
| Estimation | 3–5 | QPS, storage/yr, bandwidth, and the resulting bottleneck |
| API + data model | 5 | Endpoint signatures, table/collection shapes, the primary key |
| High-level design | 10 | Boxes and arrows that satisfy the requirements |
| Deep dive | 10–15 | The one or two components the interviewer steers you to |
| Failure, scale, ops | 5 | Bottleneck, single points of failure, what you'd monitor |

**Trap:** treating this as a knowledge quiz. Naming DynamoDB, Kafka and Redis scores nothing on its
own. The score comes from "Dynamo because the access pattern is a point lookup by user ID and I need
predictable p99 at 40k QPS; the cost is that the leaderboard query becomes a separate read model."

**[Senior vs Staff framing]** At L5 the design must be *correct and complete* for the stated load.
At L6 the interviewer additionally wants scope negotiation ("I'd cut the analytics path from v1 and
here's why"), migration path from an existing system, and organisational consequences (who owns the
new datastore, what the on-call surface becomes).

---

## 2. Requirements: the numbers you must leave with

Never start drawing. Ask until you have all of these — and if the interviewer says "you decide",
state an assumption *with a number* and move on.

**Functional:** the 3–5 operations that define the system. Write them as verbs with an actor.
"A user posts a tweet." "A follower reads their feed." Anything beyond five, propose cutting.

**Non-functional — the six numbers:**

| Number | Why it decides architecture |
|---|---|
| **DAU / MAU** | Converts to QPS; the single most load-bearing input. |
| **Read:write ratio** | 100:1 → cache and read replicas dominate. 1:1 → write path is the design. |
| **Object size** | 500-byte rows and 5-MB videos are different systems (row store vs object store + CDN). |
| **Retention** | 30 days vs forever changes storage by 100×, and decides whether you need tiering. |
| **Latency target (p99, not average)** | p99 < 100 ms forbids synchronous cross-region calls and multi-hop fan-out. |
| **Consistency need per operation** | Not per system. "Follower count may be 30 s stale, account balance may not." |

**Availability**, stated as nines, mostly matters as a translation:

| Target | Downtime / year | Downtime / month | Practical implication |
|---|---|---|---|
| 99% | 3.65 d | 7.2 h | Single box, manual recovery |
| 99.9% | 8.8 h | 43 min | Multi-AZ, automated restart |
| 99.99% | 52 min | 4.3 min | Multi-AZ active-active, no manual step in the recovery path |
| 99.999% | 5.3 min | 26 s | Multi-region, and every dependency must also be five-nines |

**Trap:** claiming five nines casually. Availability multiplies across serial dependencies — six
four-nines services in a request path give 99.94%, not 99.99%. Every synchronous dependency you add
subtracts availability; that is the strongest argument for making a call asynchronous.

---

## 3. Back-of-the-envelope estimation

Memorise the conversions, then the arithmetic is trivial.

**Time:** 1 day ≈ **86,400 s ≈ 10⁵ s**. So *X per day ÷ 10⁵ = X per second*. 1 M/day ≈ 12/s.
1 B/day ≈ 12,000/s. That one identity does most of the work.

**Peak factor:** peak QPS ≈ **2–3× average** for a global consumer product, up to 10× for an event-
driven one (ticket sales, live sport). State which you're using.

**Sizes:** 1 KB tweet-ish row, 100 KB thumbnail, 1–5 MB photo, 50 MB/min of 1080p video.
1 M × 1 KB = 1 GB. 1 B × 1 KB = 1 TB.

**Latency ladder** (order of magnitude is what matters):

| Operation | Time |
|---|---|
| L1 / L2 cache reference | 1–10 ns |
| Main memory reference | ~100 ns |
| Mutex lock/unlock uncontended | ~20 ns |
| Read 1 MB sequentially from memory | ~10 µs |
| SSD random read | ~100 µs |
| Read 1 MB from SSD | ~200 µs–1 ms |
| Round trip within a datacentre / AZ | ~0.5 ms |
| Redis GET, same AZ | ~0.5 ms |
| Indexed Postgres point lookup, warm | 1–5 ms |
| Disk seek (spinning) | ~10 ms |
| Round trip cross-region (US→EU) | ~80–150 ms |

**Capacity rules of thumb** to derive box counts (say "order of magnitude" when you use them):

| Component | Sustainable per node |
|---|---|
| Stateless JVM service, simple JSON, 4 vCPU | 2k–10k RPS |
| Nginx / L7 proxy | 20k–50k RPS |
| Redis, single-threaded, simple commands | ~100k ops/s |
| Postgres single primary, simple indexed writes | 5k–15k writes/s |
| Postgres read replica, cached point reads | 20k–50k reads/s |
| Kafka broker | ~100k msgs/s, ~100 MB/s |
| Node storage before it's operationally painful | 1–2 TB |

**Worked example — 1 M DAU social feed:**
- Each user posts 0.5/day, reads their feed 20/day.
- Writes: 500 k/day ÷ 10⁵ = **5/s avg, ~15/s peak** — trivially small.
- Reads: 20 M/day ÷ 10⁵ = **200/s avg, ~600/s peak** — also small.
- Storage: 500 k posts/day × 1 KB = 500 MB/day ≈ **180 GB/yr** — fits one node for years.
- **Conclusion you should state out loud:** at this scale the interesting problem is not throughput,
  it's the **fan-out read amplification** — a user following 1,000 people means one feed read touches
  1,000 authors. The design problem is query shape, not capacity.

Now change one input: 500 M DAU. Writes become 2,500/s, reads 100 k/s, storage 90 TB/yr. Now you
need sharding, a materialised feed, and a CDN. **The value of the estimate is that it tells you which
problem you're solving** — this is the single highest-leverage habit in the whole interview.

---

## 4. The scale-up ladder, and where each rung breaks

Start simple, then break it deliberately. This sequence is a defensible narrative for any design.

| Rung | Configuration | Breaks when |
|---|---|---|
| 0 | One box: app + DB | CPU or connections saturate; any deploy is downtime |
| 1 | App and DB split, DB vertically scaled | Vertical scaling hits price/availability limits; still one SPOF |
| 2 | N stateless app instances behind an LB | Session state in memory; DB is now the bottleneck |
| 3 | Cache + read replicas | Write throughput, and replica lag becomes visible to users |
| 4 | Async writes via a queue | Ordering and idempotency now the app's problem; eventual consistency user-visible |
| 5 | Shard the data | Cross-shard queries, transactions and rebalancing become hard |
| 6 | Multi-region | Cross-region write conflicts and 100-ms replication windows |

Two rules that follow:

- **Statelessness is the enabler for rung 2 onward.** Any per-user state in app memory (session,
  in-progress upload, WebSocket registry) must move to Redis or a database, or be made sticky
  deliberately with a named cost.
- **Each rung buys throughput with consistency or complexity.** Say which one every time you climb.

**Trap:** starting at rung 6. Jumping to "multi-region active-active with CRDTs" for a 1 M-DAU app
reads as inability to size a problem, which is a stronger negative than under-designing.

---

## 5. API and data model before boxes

Designing the contract first constrains everything downstream and makes the deep dive concrete.
Depth on REST semantics lives in **12**; here only the design-level consequences.

Write endpoints as signatures with the pagination and idempotency decisions visible:

```
POST /v1/posts                 Idempotency-Key: <uuid>   → 201 {postId}
GET  /v1/feed?cursor=<opaque>&limit=50                    → 200 {items[], nextCursor}
GET  /v1/users/{id}/posts?cursor=...&limit=50             → 200 {items[], nextCursor}
```

Three design-level API decisions worth stating:

- **Cursor pagination, not offset.** `LIMIT 50 OFFSET 100000` makes the database scan and discard
  100,000 rows — cost grows with page number. A cursor is `WHERE (created_at, id) < (:ts, :id)
  ORDER BY created_at DESC, id DESC LIMIT 50`, which is one index seek regardless of depth. Offset
  pagination also *skips and duplicates* rows when items are inserted while the user pages.
- **Idempotency key on every non-idempotent write.** The client generates it; the server stores
  `key → (status, response body)` with a TTL and replays the stored response on a repeat. Without
  it, a client retry after a timeout creates a second order (§13).
- **Opaque cursors and IDs.** Sequential integer IDs leak volume and enumerate your data; they also
  make sharding harder later.

**Data model** — say the primary key and the access patterns it serves out loud, because that single
choice determines the storage engine:

```
posts(post_id PK, author_id, body, created_at)
  index (author_id, created_at DESC)          -- a user's own timeline
follows(follower_id, followee_id) PK(follower_id, followee_id)
  index (followee_id, follower_id)            -- reverse: "who follows me", for fan-out
feed(user_id, created_at DESC, post_id) PK(user_id, created_at, post_id)  -- materialised read model
```

**The rule:** in a distributed store you design the key from the query, not the query from the key.
A partition key that isn't in the read path forces a scatter-gather over every node.

---

## 6. Storage selection as a decision procedure

Don't recite database features. Run this in order:

1. **What is the access pattern?** Point lookup by key / range scan within a key / arbitrary
   multi-attribute filter / full-text / graph traversal / aggregation over history.
2. **Does any operation need a multi-entity transaction?** If yes, you want a relational store or a
   store with single-partition transactions and a key design that co-locates the entities.
3. **What is the data volume and growth?** Under ~1 TB, "just use Postgres" is a *correct* answer and
   you should say it confidently.
4. **What's the write rate vs a single primary's ceiling?** Above ~10k writes/s sustained, plan for
   sharding or a store that shards natively.
5. **What's the consistency requirement per operation?** (§9.)

| Access pattern | Fit | Why |
|---|---|---|
| Relational, joins, transactions, < 1 TB | Postgres / MySQL | ACID, mature indexing, cheap to operate |
| Point read/write by known key, huge volume, predictable p99 | DynamoDB / Cassandra | Partition-key routing, linear horizontal scale |
| Write-heavy time series / append log | Cassandra, Timescale, ClickHouse | LSM writes, time-ordered partitions |
| Full-text / faceted search | Elasticsearch / OpenSearch | Inverted index; never your source of truth |
| Sub-ms, ephemeral, structured values | Redis | In-memory, rich types (see 15) |
| Immutable blobs > 100 KB | S3 + CDN | Never put binaries in a row store |
| Analytics / aggregation over history | Columnar warehouse (Snowflake, BigQuery, ClickHouse) | Column pruning + compression |
| Multi-hop relationships | Neo4j, or an adjacency table with a bounded traversal depth | Recursive joins are expensive |

**Trap:** "NoSQL scales better" as an unqualified claim. It scales *writes on a known partition key*
better. It makes ad-hoc queries, joins and multi-entity transactions worse or impossible. The
trade is query flexibility for scale, and you should say it in exactly those terms.

**Polyglot persistence is the normal answer at scale**, and its cost is the thing to name: two stores
means a synchronisation path, and that path has lag and a failure mode. Prefer one source of truth
plus derived read models fed by CDC or an event log (§19), never dual writes (§22).

---

## 7. Replication

Replication buys read throughput and durability. It always costs you a lag window.

| Model | Mechanism | Cost |
|---|---|---|
| **Single-leader, async** | Leader applies, ships log to followers | Reads from a follower can be stale by ms–seconds; failover can lose acknowledged writes |
| **Single-leader, semi-sync** | Leader waits for ≥1 follower ack | Write latency += one round trip; no data loss on single-node failure |
| **Multi-leader** | Both accept writes, replicate to each other | Write conflicts are now yours to resolve; only justified for multi-region write locality |
| **Leaderless (quorum)** | Client/coordinator writes to W nodes, reads R | Requires conflict resolution and repair (§10) |

**Replica lag is user-visible, and the fixes are worth knowing by name:**

- **Read-your-writes:** after a user's own write, route that user's reads to the leader (or to a
  replica whose log position ≥ the write's) for a short window. This is the single most common
  "user posted a comment and it vanished" bug.
- **Monotonic reads:** pin a user to one replica (by hashing the user ID) so they never see time move
  backwards by hopping between replicas at different positions.
- **Consistent prefix reads:** ensure causally-related writes land on the same partition, or they can
  be observed out of order.

**Failover mechanics** — the parts candidates skip:
- Detection is a timeout, so it's a **false-positive/latency trade-off**: aggressive timeouts cause
  spurious failovers, generous ones extend the outage.
- **Split brain:** the old leader may not know it was demoted. You need fencing — a monotonically
  increasing epoch/term that storage rejects writes below, or STONITH.
- Unreplicated writes on the old leader are **lost or must be discarded**; with async replication
  there is no third option.

---

## 8. Partitioning, consistent hashing, hot keys

Sharding is what you do when one node can no longer hold the data or absorb the writes.

| Scheme | How | Weakness |
|---|---|---|
| **Range** | Key ranges per shard (a–f, g–m …) | Skew and sequential-write hotspots — a timestamp key sends 100% of writes to the last shard |
| **Hash** | `hash(key) mod N` | Range scans impossible; **changing N remaps almost every key** |
| **Consistent hashing** | Key and nodes on a ring; key → next node clockwise | Only ~K/N keys move when a node joins/leaves |
| **Directory / lookup** | Explicit key→shard table | Flexible, rebalances precisely; the directory is a new SPOF and a hop |

**Consistent hashing, the mechanism:** hash nodes and keys into the same 2³²-ish space. A key belongs
to the first node clockwise from it. Adding a node steals only the arc between it and its
predecessor — so 1/N of the keys move, not all of them. Naive placement gives uneven arcs, so each
physical node is placed at **V virtual node positions** (typically 100–256); this both flattens the
distribution and makes a departing node's load spread over all survivors rather than dumping onto one
neighbour. Virtual nodes also let you weight heterogeneous hardware by giving big nodes more tokens.

**Hot partitions are the dominant real failure**, and they are not solved by adding nodes — one
celebrity user's key lives on exactly one partition.

Mitigations, in order of preference:
- **Cache the hot key** in front of the store (this handles most read hotspots outright).
- **Salt the key**: write to `celebrity_id:{0..15}` chosen at random, read by fanning out to all 16.
  Buys write throughput, costs 16× read work — so apply it only to keys detected as hot.
- **Split by a second dimension**: partition key `(video_id, hour)` instead of `video_id`.
- **Give the outlier its own dedicated path** (a separate cache/service tier for top-N entities).

**Cross-shard operations are the tax you pay** and you should price them explicitly: a query without
the partition key becomes a scatter-gather whose latency is the *slowest* shard's (p99 of a 10-shard
fan-out ≈ the p99.9 of one shard), and a transaction across shards needs 2PC (blocking, coordinator
failure risk) or a saga (compensations, no isolation — see 14).

**Resharding** is the operationally hardest thing in this guide. The workable pattern: pick a large
fixed number of **logical** partitions up front (e.g. 1,024) and map many logical partitions onto
each physical node. Growth then becomes "move logical partitions between nodes" — no rehashing, no
key migration logic. Kafka partitions, Elasticsearch shards and Vitess keyspaces all work this way.

---

## 9. CAP, PACELC, and consistency models

**CAP, stated precisely:** when a network **partition** occurs, a system must choose between
remaining **available** (serving possibly-stale or conflicting data) and remaining **consistent**
(refusing requests on the side that cannot reach a quorum). It says nothing about the no-partition
case, and "CA" is not a deployment option — partitions are not optional.

**PACELC is the more useful formulation:** if **P**artitioned, choose **A** or **C**; **E**lse (normal
operation) choose **L**atency or **C**onsistency. This captures the everyday trade-off CAP omits —
a synchronous quorum write costs latency on every single request, partition or not.

| System | Classification |
|---|---|
| DynamoDB (default eventually-consistent reads) | PA/EL |
| Cassandra (tunable, typically QUORUM) | PA/EL, configurable toward EC |
| Postgres single primary | PC/EC (unavailable on the minority side) |
| Spanner / etcd / ZooKeeper | PC/EC (consensus; pays latency for linearizability) |

**Consistency models, strongest to weakest:**

| Model | Guarantee | Typical cost |
|---|---|---|
| **Linearizable** | Every read sees the latest committed write; the system behaves as one copy | Consensus round trip per op; unavailable in a minority partition |
| **Sequential / serializable** | A single global order exists (serializable = for transactions) | Coordination; contention aborts |
| **Causal** | Operations that are causally related are seen in order; concurrent ones may differ | Version vectors; no global coordination |
| **Read-your-writes / monotonic** | Per-session guarantees only | Session pinning / log positions |
| **Eventual** | Replicas converge if writes stop | Application must tolerate stale and conflicting reads |

**Trap:** calling eventual consistency "usually a few milliseconds so it doesn't matter." State the
*window* and the *user-visible symptom*. "Replication lag is p99 200 ms, so a user could refresh and
not see their own comment — I handle that with read-your-writes routing" is the answer that scores.

**Choose per operation, not per system.** A single design routinely mixes: linearizable for
"reserve the last seat" and "debit the account", causal for messaging, eventual for view counts and
follower totals.

---

## 10. Quorums and the R + W > N arithmetic

In a leaderless/tunable store with **N** replicas, a write goes to **W** and a read to **R**.

If **R + W > N**, the read and write sets must overlap in at least one node, so a read sees at least
one copy of the latest write — *provided* it can pick the newest of the values it gets back (via a
version/timestamp).

| N | W | R | Property |
|---|---|---|---|
| 3 | 2 | 2 | The standard quorum. Tolerates 1 node down for both reads and writes. |
| 3 | 3 | 1 | Fast reads, no write availability if any node is down. |
| 3 | 1 | 1 | Fastest, eventual only. `R+W=2 ≤ 3`. |
| 3 | 1 | 3 | Fast writes, slow reads, quorum satisfied. |

Two things quorums still need:

- **Read repair / anti-entropy:** a read that observes divergent versions writes the newest back
  (read repair), plus a background Merkle-tree comparison for keys nobody reads (anti-entropy). Skip
  both and rarely-read keys never converge.
- **Conflict resolution** for genuinely concurrent writes. Last-write-wins on wall-clock timestamps
  is the default and it **silently discards data** under clock skew — acceptable for a cache entry,
  not for a shopping cart. The alternatives are version vectors with application-level merge (union
  the cart) or CRDTs (counters, sets, registers whose merge is provably commutative and idempotent).

**Trap:** "quorum reads give strong consistency." Sloppy quorums with hinted handoff (Dynamo-style)
let a write land on nodes *outside* the intended replica set during a partition, which breaks the
overlap argument. Quorum gives you a strong *probability*, not linearizability; linearizability needs
consensus (Raft/Paxos), which is a different and more expensive machine.

---

## 11. Caching in a design

Mechanisms, races and Redis internals are in **15**. At design level, place the tiers and state what
each buys:

| Tier | Latency | Buys you | Cost |
|---|---|---|---|
| Client / browser | 0 | Zero network | No invalidation control |
| CDN / edge | 10–50 ms | Bandwidth, geographic latency, origin offload | Only for cacheable, mostly-public responses |
| API gateway / reverse proxy | ~1 ms | Whole-response reuse | Coarse keys |
| In-process (Caffeine) | ~100 ns | Absorbs hot keys entirely | Per-instance, so N copies of the staleness problem |
| Distributed (Redis) | ~0.5 ms | Shared, survives restarts | A network hop and a new dependency |
| Database buffer pool | ~1 ms | Free | Not yours to control |

Two design-level rules worth stating in any interview:

- **A cache you cannot survive losing is an undocumented critical dependency.** Compute what happens
  at 0% hit ratio: if 99% hit ratio means the DB is sized for 1% of read traffic, a cache flush hands
  it 100× its capacity. So: rate-limit or circuit-break the origin, warm behind a failing readiness
  probe, and prefer serve-stale-on-error over fail.
- **Every input that changes the output belongs in the key** — tenant, user, role, locale, schema
  version, filter set. Omitting the user from a key is how one user's data gets served to another.

---

## 12. Asynchrony: what to move off the request path

Mechanisms are in **14**. The design question is *which* work goes async, and the test is a single
question: **does the user need the result to continue?**

Move off the request path: notifications, emails, image/video transcoding, search indexing,
analytics, feed materialisation, webhook delivery, third-party sync, anything fan-out shaped.

Keep synchronous: anything the response body must contain, and anything whose failure must be
reported to the user as a failure.

What asynchrony buys and costs:

| Buys | Costs |
|---|---|
| Lower and more stable p99 (slow work leaves the path) | The user sees an intermediate state; you need a status/notification mechanism |
| Load levelling — the queue absorbs spikes | Queue depth becomes an SLO and a monitoring surface |
| Independent scaling and failure isolation of the consumer | At-least-once delivery ⇒ consumers must be idempotent |
| Retries without the user waiting | Ordering is only per-partition; DLQs need an owner and a replay path |

**Choosing queue vs log:** a queue (SQS, RabbitMQ) gives competing consumers, per-message ack and
easy retry — right for work distribution. A log (Kafka) gives retention, replay and multiple
independent consumer groups over the same stream — right when several systems need the same events,
or when you'll want to rebuild a read model. "Several consumers need this event" is the clearest
signal for a log.

**Backpressure is a design decision, not an accident.** When the consumer can't keep up you must
choose: bound the queue and reject producers (load shedding), drop by priority, or grow unboundedly
and convert a throughput problem into an out-of-memory outage. Pick explicitly, and say which.

---

## 13. Idempotency, and "exactly once" at the design layer

Every network call has three outcomes: success, failure, and **unknown** (timeout). The unknown case
forces retries, retries cause duplicates, and duplicates are the most common correctness bug in a
distributed design. Exactly-once *delivery* is impossible; exactly-once *effect* is achievable and is
what you should claim.

The three mechanisms:

1. **Idempotency key** (client-supplied, for user-facing writes). Server stores
   `key → (state, response)`; a repeat returns the stored response. Insert the key row in the *same
   transaction* as the effect, so a crash between them can't lose the record.
2. **Natural dedupe key** (server-side, for consumers). Insert `(consumer_group, message_id)` into a
   uniquely-indexed table and let the unique-constraint violation mean "already processed".
3. **Idempotent-by-construction operations.** `SET balance = 100` is naturally idempotent;
   `balance = balance + 10` is not. Where you can express the operation as a set or an upsert keyed
   on a version, do — it removes the problem instead of managing it.

```java
@Transactional
public PaymentResult charge(String idempotencyKey, ChargeRequest req) {
    Optional<Idempotency> prior = idempotencyRepo.findById(idempotencyKey);
    if (prior.isPresent()) {
        return prior.get().replay();              // same response, no second effect
    }
    PaymentResult result = gateway.charge(req);   // the effect
    idempotencyRepo.save(new Idempotency(idempotencyKey, result));  // same tx as the effect
    return result;
}
```

**Trap:** two concurrent requests with the same key. `findById` then `save` is a check-then-act race.
Insert the key **first** with a unique constraint and treat the violation as "in flight or done" —
that makes the database the arbiter instead of the application.

**The dual-write problem and the outbox.** Writing to the database and publishing to Kafka are two
systems with no shared transaction; a crash between them leaves them permanently disagreeing. The
fix is to write the event into an `outbox` table **in the same transaction** as the state change, and
have a separate relay (poller or CDC/Debezium reading the WAL) publish it. That converts an atomicity
problem into an at-least-once delivery problem, which idempotent consumers already handle.

---

## 14. Unique ID generation

An ID scheme is a real design decision because it constrains sharding, sorting and information leakage.

| Scheme | Bytes | Sortable | Coordination | Notes |
|---|---|---|---|---|
| DB auto-increment | 8 | Yes | Single writer | Simple, but a sharding and enumeration problem |
| UUIDv4 | 16 | **No** | None | Random ⇒ index write amplification: every insert hits a random B-tree leaf |
| UUIDv7 / ULID | 16 | Yes (time-prefixed) | None | The modern default — no coordination *and* locality |
| Snowflake | 8 | Yes | Node-ID assignment | 41-bit ms timestamp + 10-bit node + 12-bit sequence |
| Ticket server / range allocation | 8 | Yes | Central, but batched | Hand out blocks of 10k; SPOF unless replicated |

**Snowflake arithmetic worth knowing:** 41 bits of milliseconds ≈ 69 years from a custom epoch;
10 bits ⇒ 1,024 workers; 12 bits ⇒ 4,096 IDs per worker per millisecond ⇒ ~4 M IDs/s per worker.
Its weaknesses are node-ID assignment (needs ZooKeeper, etcd or a config plane) and **clock skew**: a
backwards NTP step can produce duplicate IDs, so the generator must refuse to move backwards.

**Trap:** UUIDv4 as a clustered primary key in MySQL/InnoDB. Random keys mean every insert lands in a
random leaf page, destroying the buffer-pool locality that sequential inserts get. The result is
page splits, write amplification and an index that's much larger than necessary. Use UUIDv7/ULID, or
keep an internal sequential PK with the UUID as an external identifier.

---

## 15. Rate limiting and admission control

Rate limiting protects capacity, enforces fairness and prices your API. The algorithm choice is
about burst behaviour.

| Algorithm | Mechanism | Burst behaviour | Memory |
|---|---|---|---|
| **Fixed window** | Counter per (key, minute) | **2× the limit at a window boundary** | 1 counter |
| **Sliding window log** | Sorted set of timestamps, trim old | Exact | O(limit) per key |
| **Sliding window counter** | Weighted blend of current + previous window | Good approximation | 2 counters |
| **Token bucket** | Tokens refill at rate R, capacity B | Allows a burst of B, then steady R | 2 numbers |
| **Leaky bucket** | Queue drains at fixed rate | Smooths completely, adds queueing delay | Queue |

**Token bucket is the usual right answer** because it matches how traffic really is — bursty but
bounded on average — and it's two numbers per key (`tokens`, `lastRefillMicros`), computed lazily on
access.

Distributed enforcement: keep counters in Redis and make the check-and-decrement atomic with a Lua
script (a `GET` then `SET` from N instances leaks the limit). Per-instance local limits with
`limit / instanceCount` are cheaper but wrong under uneven load balancing and during autoscaling.

Design-level requirements: return **429** with `Retry-After` and `X-RateLimit-Remaining`; choose the
key deliberately (API key > user ID > IP — IP punishes users behind NAT and is trivially rotated);
and fail **open or closed** by explicit decision when Redis is down.

**Load shedding is the sibling mechanism and it's the one that saves you in an incident.** When
concurrency or queue depth passes a threshold, reject cheap-to-reject requests immediately by
priority (health checks and paying customers before batch and analytics). A fast 503 preserves
capacity for the requests you keep; queueing everything converts overload into total collapse,
because by the time you serve a request the client has already timed out and retried.

---

## 16. Load balancing and request routing

Protocol mechanics are in **10**; here the design consequences.

| Layer | Sees | Can do | Cost |
|---|---|---|---|
| **DNS** | Hostname | Geo/region routing, coarse weighting | TTL caching means minutes to shift traffic |
| **L4 (NLB)** | IP/port | Very high throughput, TCP passthrough, TLS passthrough | No path/header awareness |
| **L7 (ALB/Envoy/nginx)** | HTTP | Path/header routing, retries, TLS termination, circuit breaking | More CPU, another hop |

Algorithms: round-robin (default), **least-connections** (better with variable request cost),
**least-outstanding-requests / EWMA** (best when backends are heterogeneous or one is degrading),
and consistent hashing (for cache affinity or sticky stateful connections).

**Health checks decide whether the LB helps or hurts.** Shallow checks (`/health` returns 200) keep
traffic on a broken instance whose database connection is gone; deep checks that test dependencies
cause **correlated removal** — a slow database fails every instance's check and the LB removes the
entire fleet. The practical answer: liveness shallow, readiness moderate, and *never* remove more
than a configured fraction of the fleet at once (Envoy's panic threshold: if fewer than ~50% of hosts
are healthy, ignore health status and use all of them, on the theory that a degraded service beats no
service).

**Statelessness again:** sticky sessions make deploys and autoscaling drop user state and cause
persistent imbalance. Externalise the session (Redis, or a signed token) and let any instance serve
any request.

---

## 17. Resilience patterns

The failure of one dependency must not become the failure of your service. Six mechanisms, and the
specific failure each prevents:

- **Timeouts.** Every network call, always. A missing timeout is how one slow dependency exhausts
  your thread pool and takes down endpoints that don't even use it. Set them from the dependency's
  measured p99, not by guess, and make the caller's timeout *shorter* than the total budget it was
  given (a timeout budget passed down the call chain).
- **Retries with exponential backoff and full jitter.** `sleep = random(0, min(cap, base·2^n))`.
  Without jitter, all clients retry in synchronised waves and you get a self-inflicted DDoS.
  **Only retry idempotent operations** (§13), cap attempts at 2–3, and never retry a 4xx.
- **Retry amplification** is the subtle killer: 3 retries at each of 3 layers is 27 requests for one
  user action. Retry at **one** layer — usually the outermost that can still act on the result — and
  use a **retry budget** (e.g. retries ≤ 10% of requests) to make it self-limiting.
- **Circuit breaker.** Track the failure rate over a rolling window; at a threshold, open and fail
  fast for a cooldown; then half-open and let a few probes through. This stops you from spending your
  own capacity on calls that are going to fail anyway, and gives the downstream room to recover.
- **Bulkheads.** Separate connection/thread pools per dependency so a saturated one can't consume
  all your capacity. Same idea as watertight compartments.
- **Graceful degradation.** Decide in advance, per feature, what the reduced-function answer is:
  recommendations fall back to "most popular", personalised feed falls back to chronological, a
  missing avatar renders a placeholder. **Say this out loud in the interview** — it's what
  distinguishes a design that has been thought about operationally.

**Trap:** describing retries without mentioning idempotency or jitter. It reads as having heard of
resilience rather than having operated it.

---

## 18. Multi-region

Multi-region is expensive and adds a class of bug you cannot avoid. Justify it with one of three
reasons: **latency** (users far from one region), **regulatory data residency**, or **regional
disaster tolerance**. If none applies, multi-AZ within a region gets you 99.99% and is far simpler.

| Topology | Writes | RPO / RTO | Difficulty |
|---|---|---|---|
| Active–passive, async replication | One region | RPO = lag (seconds); RTO = failover time (minutes) | Low |
| Active–active, partitioned by key (cells) | Each region owns a key range | RPO ≈ 0 for owned keys | Medium — needs routing by home region |
| Active–active, full replication | Both regions, any key | Conflicts guaranteed | High — LWW, CRDTs, or app-level merge |
| Synchronous consensus across regions (Spanner-style) | Anywhere | RPO = 0 | Every write pays cross-region RTT (~100 ms) |

**Cell/partition-by-key is the pattern that actually works** for consumer systems: give each user a
home region, serve their writes there, replicate asynchronously for read locality and DR. Conflicts
disappear because only one region ever writes a given key. The cost is a routing layer and a
user-migration procedure.

Numbers you must respect: cross-region RTT is 80–150 ms, so a single synchronous cross-region hop
blows a 100-ms p99 budget on its own. Also price the cross-region data transfer — it is often the
largest surprise line on the bill.

**And DR is only real if it's rehearsed.** State RPO (how much data you can lose) and RTO (how long
you can be down) as numbers, and say that the failover is exercised on a schedule — an untested
failover path is a hypothesis, not a capability.

---

## 19. Read models, CQRS, and search

When one write model can't serve every read shape, split them instead of contorting the schema.

**The pattern:** writes go to the source of truth; a change stream (CDC from the WAL, or your outbox
events) feeds one or more purpose-built read models — Elasticsearch for text search, a columnar store
for analytics, a denormalised `feed` table for timelines, Redis for counters.

Properties to state:
- The read model is **eventually consistent** with the source of truth. Name the lag budget and the
  user-visible symptom ("a new post is searchable within ~2 s").
- It is **rebuildable**, and that's the main reason to prefer a log over dual writes: to fix a bug in
  the projection, you replay the log rather than migrate data.
- **Elasticsearch is never the source of truth.** It has no transactions and reindexes are routine;
  keep the authoritative copy in the primary store.

**Counters** deserve a specific note because they show up in almost every design. Incrementing a row
per view serialises on one row and destroys write throughput at scale. Options, in order:
increment in Redis and flush aggregates periodically; write an append-only event and aggregate
asynchronously; or use approximate structures (HyperLogLog for unique counts) when exactness isn't
required. Ask whether the count must be exact — usually it must not.

---

## 20. Blobs, uploads and delivery

Never route large media through your application.

**Upload:** the client asks your API for a **pre-signed URL** and PUTs the bytes directly to object
storage; storage emits an event on completion, which triggers processing (virus scan, transcode,
thumbnailing) asynchronously. Your service handles metadata only. Multipart upload for large files
gives per-part retry instead of restarting a 5-GB upload.

**Delivery:** object storage behind a CDN. Content-addressed or fingerprinted URLs
(`/assets/app.9f2c1e.js`) can be cached immutably forever, which means you never purge — you
publish a new URL. Signed URLs with a short expiry handle private media.

**Metadata in the database, bytes in object storage.** Storing binaries in a relational store bloats
backups, thrashes the buffer pool and makes replication expensive.

---

## 21. Observability and capacity

Mechanisms are in **20**. In a design review, three things must appear:

- **The SLI/SLO you'd hold the system to**, phrased as a ratio over a window: "99.9% of feed reads
  under 300 ms over 28 days." That definition is what makes the design falsifiable.
- **The metrics that would tell you which component is failing:** per-dependency latency and error
  rate, queue depth and consumer lag, cache hit ratio, connection-pool saturation, replication lag.
  Note that these are the *derived* signals — saturation and lag lead the user-visible symptoms, so
  they're what you alert on.
- **Percentiles, never averages.** An average hides the tail entirely; with fan-out, the tail is the
  common case, because a request touching 100 shards is slower than the p99 of one shard almost
  always. Measure and quote p99, and remember that client-observed latency includes queueing your
  server-side timer never saw.

Capacity: state the **bottleneck resource** and its headroom. "We're at 40% of Postgres write
capacity; the next scaling step at 70% is to shard by tenant, which takes a quarter." A design with a
named bottleneck and a named next step reads as owned; one without reads as guessed.

---

## 22. Migration: how you actually get there

Interviewers at the Staff bar frequently ask "and how would you roll this out to an existing system
with live traffic?" The answer is never "big-bang cutover".

The standard sequence for replacing a datastore or a service:

1. **Dual write behind a flag** — write to old and new, read from old. Accept that dual writes can
   diverge (§13) and reconcile continuously rather than assuming they won't.
2. **Backfill** historical data in idempotent, resumable batches, rate-limited so it doesn't
   starve live traffic.
3. **Shadow read / dark launch** — serve from old, also read from new, compare and log mismatches.
   This is where you find the bugs, with zero user impact.
4. **Flip reads incrementally** — 1% → 10% → 50% → 100%, per-tenant or per-user-hash, with a
   documented rollback that is a flag flip and not a deploy.
5. **Stop the dual write**, keep the old path readable for a defined period, then decommission.

**Expand/contract for schema changes:** add the new nullable column, write both, backfill, switch
reads, then drop the old — never a single migration that renames a column an old deploy still reads.
Every step must be safe with both old and new code running, because during a rolling deploy they are.

**Trap:** proposing a maintenance window. Sometimes correct, but say why the online path was rejected;
at scale a window is usually not available.

---

## 23. Worked design — URL shortener (the arithmetic-driven one)

**Requirements:** shorten a URL, redirect; 100 M new URLs/day; 100:1 read:write; links live 5 years;
redirect p99 < 50 ms.

**Estimation:** writes 100 M/10⁵ = **1,000/s** (peak 3,000/s). Reads **100,000/s** (peak 300 k/s).
Storage: 100 M/day × 365 × 5 = 182 B records × ~500 B = **~90 TB**.

**Key length:** base62 (`[0-9a-zA-Z]`) — 62⁷ ≈ 3.5 × 10¹² and we need 1.8 × 10¹¹, so **7 characters**
suffices with headroom. Show this calculation; it's the point of the question.

**Key generation:** do *not* hash the long URL and take a prefix — collisions require a
read-before-write on the hot path, and the same URL from two users can't get distinct keys or
per-user analytics. Instead pre-allocate: each shortener instance takes a block of 10⁶ counter values
from a central allocator, base62-encodes them, and (if guessability matters) scrambles the value with
a bijection. Zero coordination on the request path.

**Storage:** the access pattern is a point lookup by 7-char key, at 100 k/s, with no joins. That is
exactly a key-value store — DynamoDB or Cassandra, partition key = short code. 90 TB says sharded
from day one.

**Read path:** the workload is extremely skewed (a small fraction of links serve most traffic), so
the design is cache-first: CDN/edge for the redirect where possible, then Redis, then the store.
Even 50 GB of Redis holding the hot set will serve >95% of reads at ~0.5 ms.

**Redirect semantics:** `301` is cached by browsers forever — great for load, fatal for analytics and
for ever changing the target. `302` keeps every redirect coming to you. Choose by whether
click-tracking is a requirement, and say so.

**Analytics:** never increment a counter row per redirect at 100 k/s. Emit an event to Kafka and
aggregate asynchronously (§19).

**Bottleneck:** read fan-out on hot keys, handled by caching; the write path is comfortable.

---

## 24. Worked design — news feed (the fan-out choice)

**The one decision that matters:** materialise the feed on write (push) or assemble it on read (pull)?

| | Fan-out on write (push) | Fan-out on read (pull) |
|---|---|---|
| Post cost | O(followers) writes | 1 write |
| Read cost | 1 range scan of a precomputed list | O(followees) queries + merge |
| Read latency | Excellent, predictable | Poor and variable |
| Celebrity problem | A 50 M-follower post = 50 M writes | None |
| Inactive users | You materialise feeds nobody reads | Nothing wasted |

**The answer is hybrid**, and the reasoning is what's being tested: reads outnumber writes ~100:1, so
pay on write — but exempt accounts above a follower threshold (say 100 k) from fan-out and merge
their posts in at read time. Also skip materialisation for users inactive for 30+ days and
backfill lazily on their return.

**Mechanics:** post → write to `posts` → emit event → fan-out workers read the follower list and push
`post_id` into each follower's feed list (Redis list/ZSET capped at ~1,000 entries, with the
authoritative feed in the store). Feed read = one range read of IDs + a batched multi-get of post
bodies + a merge of any celebrity authors.

**Ranking** turns the feed from a merge into a scoring problem; scope it out of v1 explicitly, or the
design balloons. If it's in scope, say the shape: candidate generation (recent + affinity) → feature
lookup → model scoring → diversity/dedupe pass, with the model served behind a strict timeout and a
chronological fallback (§17).

**Bottleneck:** fan-out write volume at peak. Queue absorbs the spike; feed writes are eventually
consistent by design, and the user-visible symptom is "a friend's post appears a second or two late."

---

## 25. Worked design — chat and presence (the stateful one)

The distinguishing property: **long-lived connections**, so the usual "stateless app tier" assumption
breaks and you must say how you route a message to a socket held by one specific instance.

- **Transport:** WebSocket for bidirectional messaging (long polling as a fallback). Use an L4 LB or
  L7 with WebSocket support, and expect connections to be pinned for hours — which makes deploys and
  autoscaling interesting: drain by refusing new connections and letting clients reconnect with
  jittered backoff, never all at once.
- **Connection registry:** `user_id → gateway_instance` in Redis with a TTL and heartbeat. To deliver
  to a user, look up their gateway and forward; if absent, they're offline, so persist and push a
  notification instead.
- **Message storage:** the access pattern is "range scan of one conversation, newest first, forever",
  so partition by `conversation_id` with a clustering key of `(created_at DESC, message_id)`. That's
  a wide-column store's home turf.
- **Ordering:** wall-clock ordering across devices is unreliable. Use a per-conversation monotonic
  sequence number assigned server-side, and let clients sort by it.
- **Delivery semantics:** at-least-once plus a client-generated message ID for dedupe (§13). Read
  receipts and delivery receipts are their own (much higher-volume) write stream — batch them.
- **Group chat:** fan-out per member, and the same celebrity problem as §24 for very large groups —
  above a size threshold, switch from push to pull.
- **Presence:** heartbeat every ~30 s with a slightly longer TTL. Broadcasting every presence change
  to every contact is the scaling trap: it's O(contacts) per flap. Debounce, batch, and only push
  presence for conversations the user currently has open.

---

## 26. Worked design — payments / ledger (the correctness-first one)

Here the trade-offs invert: availability yields to correctness, and eventual consistency is not on
the table for balances.

- **Double-entry ledger, append-only.** Never `UPDATE balance`. Insert paired debit/credit entries;
  balance is a derived value (a materialised running total maintained transactionally, or a snapshot
  plus subsequent entries). This gives you auditability and makes reconciliation possible.
- **Money is `BigDecimal` or integer minor units — never `double`.** (See 03.)
- **Idempotency is mandatory** on every write, keyed by a client-supplied key, with the key row
  inserted in the same transaction as the entries (§13).
- **Atomicity across accounts:** keep both accounts in one database/partition and use a single
  transaction where you can. Across services, use a **saga** with explicit compensating transactions
  (refund, release-hold) and accept that there is no isolation — an intermediate state is observable,
  so model it (`PENDING`, `HELD`, `SETTLED`, `REVERSED`) rather than pretending it doesn't exist.
- **External gateway calls** are the classic unknown-outcome problem: a timeout means you do not know
  whether the charge happened. Never blind-retry; query the gateway's status endpoint by your
  idempotency key, and design a reconciliation job that compares your ledger to the provider's
  settlement report daily. The reconciliation job is not optional plumbing — it is the mechanism by
  which you find out you were wrong.
- **Consistency choice:** serializable or explicit row locking for balance-affecting transactions;
  accept lower availability during a partition (PC/EC) because double-spending is worse than downtime.

---

## 27. Language that scores

Rehearse these shapes; they're the difference between having the right design and being credited with it.

- **Assumption, stated:** "You haven't given me DAU, so I'll assume 10 M with a 3× peak factor —
  tell me if that's off, because it changes whether we shard."
- **Derivation, not assertion:** "1,000 writes/s against ~10k/s per primary means one primary is fine
  for now; I'd revisit at 5,000."
- **Trade-off, both sides:** "I'm choosing eventual consistency for the follower count. It buys a
  10 ms read instead of a quorum round trip; the cost is the count can be 30 seconds stale, which
  the product can tolerate. I would not make that choice for the account balance."
- **Failure, priced:** "If Redis dies, the hit ratio goes to zero and Postgres sees 100× read load,
  so I need an origin circuit breaker and a warm-up path — otherwise the cache is a hidden SPOF."
- **Scope, negotiated:** "Search, moderation and analytics are each their own design. I'll leave them
  as named interfaces and go deep on the feed path unless you'd rather I do the other."
- **Bottleneck, named:** "The bottleneck is fan-out write volume at peak. The next thing that breaks
  is the fan-out worker pool, and the fix is partitioning by author with more consumers."

---

## 28. How candidates actually lose this round

| Failure | What it looks like | Fix |
|---|---|---|
| No requirements phase | Drawing boxes in minute 2 | Spend 5–8 minutes; extract the six numbers (§2) |
| No numbers | "We'll add caching and sharding" | Derive every component count from arithmetic (§3) |
| Over-engineering | Kafka, Kubernetes, multi-region for 1k users | Start at the right rung of §4 and climb on demand |
| One-way trade-offs | Naming only the benefit | Every choice states what it costs |
| Rabbit-holing | 20 minutes on the ID generator | Time-box; offer the depth, let the interviewer pick |
| Silent thinking | Long pauses with no narration | Think out loud; the reasoning is the artifact |
| No failure analysis | Every box assumed healthy | For each box: dies / slow / full |
| Ignoring steering | Missing "how would you handle a hot key?" as the real question | Interviewer questions are the rubric, not interruptions |
| Undefined magic | "Then the service reconciles it" | Say the mechanism, table or algorithm |
| Won't commit | Listing four options, choosing none | Pick one, defend it, name when you'd switch |

---

## Atomic concept checklist

- [ ] The round measures requirement discipline, arithmetic, trade-off articulation, failure thinking and driving — in that order.
- [ ] I budget the 45 minutes: requirements 5–8, estimation 3–5, API/data 5, high level 10, deep dive 10–15, ops 5.
- [ ] I leave requirements with six numbers: DAU, read:write, object size, retention, p99 target, consistency need per operation.
- [ ] Availability multiplies across serial dependencies — six four-nines services give 99.94%.
- [ ] 1 day ≈ 10⁵ s, so per-day ÷ 10⁵ = per-second. Peak ≈ 2–3× average.
- [ ] Memory ~100 ns, SSD random read ~100 µs, same-AZ RTT ~0.5 ms, cross-region RTT ~100 ms.
- [ ] One Postgres primary ≈ 5k–15k writes/s; one Redis ≈ 100k ops/s; a node holds 1–2 TB comfortably.
- [ ] The estimate's purpose is to tell me **which problem I'm solving** — capacity or query shape.
- [ ] The scale ladder: one box → split → stateless N → cache/replicas → async → shard → multi-region; each rung buys throughput with consistency or complexity.
- [ ] Statelessness is what makes horizontal scaling and safe deploys possible; sticky sessions cost both.
- [ ] Cursor pagination is one index seek at any depth; `OFFSET 100000` scans and discards 100,000 rows and can skip/duplicate items.
- [ ] In a distributed store I design the key from the query; a read without the partition key is a scatter-gather.
- [ ] Under ~1 TB with joins and transactions, "just use Postgres" is a correct and confident answer.
- [ ] NoSQL trades query flexibility for scale on a known partition key — not "better scaling" in general.
- [ ] Prefer one source of truth plus derived read models fed by CDC/events over dual writes.
- [ ] Async replication means failover can lose acknowledged writes; semi-sync costs one RTT per write.
- [ ] Replica lag is user-visible: read-your-writes, monotonic reads and consistent-prefix reads are the named fixes.
- [ ] Failover needs fencing (epoch/term) or the demoted leader causes split brain.
- [ ] `hash(key) mod N` remaps almost every key when N changes; consistent hashing moves ~K/N.
- [ ] Virtual nodes (100–256 per physical node) flatten distribution and spread a departing node's load.
- [ ] Hot partitions are not fixed by adding nodes — cache, salt the key, add a partition dimension, or dedicate a tier.
- [ ] Pre-allocate many logical partitions (e.g. 1,024) mapped onto fewer physical nodes so resharding is a move, not a rehash.
- [ ] A fan-out query's latency is its slowest shard's: p99 across 10 shards ≈ p99.9 of one.
- [ ] CAP is only about the partition case; "CA" isn't a deployment option.
- [ ] PACELC adds the everyday trade-off: else, latency or consistency.
- [ ] Consistency is chosen **per operation**: linearizable for the last seat, eventual for view counts.
- [ ] `R + W > N` guarantees read/write set overlap; N=3, W=2, R=2 is the standard quorum.
- [ ] Quorums still need read repair plus anti-entropy, or unread keys never converge.
- [ ] LWW on wall clocks silently discards data under clock skew; version vectors or CRDTs when that matters.
- [ ] Quorum ≠ linearizable — sloppy quorums with hinted handoff break the overlap argument; linearizability needs consensus.
- [ ] A cache I can't survive losing is an undocumented critical dependency; compute the 0%-hit-ratio load.
- [ ] Every input that changes the output belongs in the cache key, including tenant, user and role.
- [ ] Async test: does the user need the result to continue? If not, it leaves the request path.
- [ ] Queue = competing consumers and work distribution; log = retention, replay and multiple consumer groups.
- [ ] Backpressure is a decision: shed, drop by priority, or OOM. Pick one out loud.
- [ ] Exactly-once *delivery* is impossible; exactly-once *effect* via idempotency keys, dedupe tables, or naturally idempotent operations.
- [ ] Insert the idempotency key first under a unique constraint — `findById` then `save` is a check-then-act race.
- [ ] The outbox pattern (event written in the same transaction, relayed by poller or CDC) is the fix for dual writes.
- [ ] UUIDv4 as a clustered PK causes random-leaf index write amplification; UUIDv7/ULID gives uncoordinated *and* sortable.
- [ ] Snowflake = 41-bit ms + 10-bit node + 12-bit sequence ⇒ ~4 M IDs/s/node, 69 years, and it must refuse to move backwards.
- [ ] Fixed-window rate limiting admits 2× the limit at a boundary; token bucket is the usual right answer.
- [ ] Distributed rate limiting needs an atomic check-and-decrement (Redis Lua), not GET-then-SET.
- [ ] Load shedding by priority preserves capacity; queueing everything under overload causes collapse.
- [ ] Shallow health checks keep traffic on broken instances; deep ones cause correlated fleet removal — cap how much of the fleet can be removed.
- [ ] Every network call gets a timeout derived from the dependency's measured p99, shorter than the inherited budget.
- [ ] Retries need full jitter, an attempt cap, idempotency, and a retry budget; 3 retries at 3 layers is 27 requests.
- [ ] Circuit breakers stop spending my capacity on calls that will fail; bulkheads stop one dependency consuming all of it.
- [ ] Graceful degradation is decided per feature in advance, and saying it out loud is a scoring signal.
- [ ] Multi-region needs one of three justifications: latency, data residency, regional DR. Otherwise multi-AZ.
- [ ] Partition-by-key with a home region eliminates write conflicts; full active-active guarantees them.
- [ ] One synchronous cross-region hop (~100 ms) blows a 100-ms p99 budget by itself.
- [ ] RPO and RTO are numbers, and an unrehearsed failover is a hypothesis.
- [ ] Read models are eventually consistent, rebuildable from the log, and Elasticsearch is never the source of truth.
- [ ] High-volume counters go to Redis or an event stream, never an `UPDATE` per event; ask whether exactness is required.
- [ ] Large media: pre-signed direct upload, event-driven processing, object storage behind a CDN, metadata in the DB.
- [ ] Fingerprinted immutable URLs beat CDN purges.
- [ ] I quote p99, never averages, and I alert on leading signals: saturation, queue depth, consumer lag, replication lag.
- [ ] A design is owned when I can name the bottleneck resource, its headroom, and the next scaling step.
- [ ] Migration is dual write → backfill → shadow read/compare → incremental read flip → decommission, with flag-flip rollback.
- [ ] Expand/contract for schema changes, because old and new code both run during a rolling deploy.
- [ ] URL shortener: 7 base62 chars (62⁷ ≈ 3.5×10¹²), counter blocks not hash prefixes, KV store, cache-first reads, 301 vs 302 by analytics need.
- [ ] Feed: hybrid fan-out — push by default, pull for celebrities above a follower threshold and for long-inactive users.
- [ ] Chat: WebSocket plus a `user → gateway` registry in Redis; per-conversation server-assigned sequence numbers for ordering.
- [ ] Payments: append-only double-entry ledger, integer minor units, mandatory idempotency, sagas with compensations, daily reconciliation.
- [ ] The losing moves are: no requirements, no numbers, over-engineering, one-sided trade-offs, rabbit-holing, and refusing to commit to a choice.
