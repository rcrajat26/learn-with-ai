# Syllabus — 14 Messaging & Queues

**Target version baseline.** Every constant, config name, default value, quota, header, class name
and API signature below is stated against this set of releases, and every leaf that depends on a
version says so:

| Layer | Release this file targets |
|---|---|
| Apache Kafka | **4.3.0** (22 May 2026). KRaft-only since 4.0.0 (18 Mar 2025); 4.1.0 (4 Sep 2025); 4.2.0 (17 Feb 2026) |
| Kafka consumer protocol | **KIP-848** GA since 4.0 (`group.protocol=consumer`); classic protocol deprecated by **KIP-1274** |
| Kafka queues | **KIP-932 share groups** — early access 4.0, preview 4.1, **production-ready 4.2**, extended in 4.3 (KIP-1240) |
| Kafka tiered storage | **KIP-405** GA since 3.9; KIP-1176 (active-segment tiering) and KIP-1150 (diskless topics) still proposals |
| RabbitMQ | **4.3.x** (23 Apr 2026). 4.0 (18 Sep 2024) removed classic mirrored queues; 4.2 (28 Oct 2025) made Khepri default; 4.3 removed Mnesia and CQv1 entirely |
| AMQP | **AMQP 0-9-1** (the RabbitMQ protocol spec + errata) and **AMQP 1.0** (OASIS / ISO 19464), a core always-on protocol in RabbitMQ ≥ 4.0 |
| Java messaging API | **Jakarta Messaging 3.1** (`jakarta.jms.*`) — the renamed, pruned successor to JMS 2.0 (`javax.jms.*`) |
| Spring | **Spring Boot 4.0.x / Spring Framework 7.0.x**; **Spring for Apache Kafka 4.1.x** (GA Jun 2026, also 4.0.6 / 3.3.16); **Spring AMQP 4.0.x** (GA 19 Nov 2025) with the new `spring-rabbitmq-client` AMQP 1.0 module |
| AWS | **Amazon SQS / SNS / EventBridge** as documented September 2026 — 1 MiB payloads, fair queues, 120,000 in-flight for both queue types |
| CDC | **Debezium 3.3.x** (3.3.0.Final, 1 Oct 2025) — `EventRouter` outbox SMT |
| Java runtime | **Java 21** for all code; Kafka 4.x clients require Java 11+, brokers Java 17+, and 4.2 added Java 25 support |

The **twelve deltas that most often produce a stale answer in an interview**, all marked
`[VERSION-TRAP]` inline:

1. **SQS messages are 1 MiB, not 256 KiB.** The maximum payload rose from 262,144 bytes to
   **1,048,576 bytes** in August 2025, for both standard and FIFO queues, and Lambda's SQS event
   source mapping followed. The current guide `src/topics/14-messaging-queues.md` § 9 states
   "256 KB max message size" and must be corrected. The claim-check pattern is still right above
   1 MiB, and the Extended Client Library still tops out at 2 GB via S3.
2. **SQS FIFO in-flight limit is 120,000, not 20,000.** Both standard and FIFO queues now cap
   in-flight (received-but-not-deleted) messages at 120,000; `OverLimit` is the error.
3. **`linger.ms` defaults to 5, not 0** (KIP-1030, Kafka 4.0). Every "the producer sends
   immediately by default" answer is 3.x-and-earlier. `num.recovery.threads.per.data.dir` went
   1 → 2 and `message.timestamp.after.max.ms` went `Long.MAX_VALUE` → 3600000 in the same KIP.
4. **ZooKeeper does not exist in Kafka 4.x.** KRaft is the only mode; `--zookeeper` flags,
   `EmbeddedKafkaZKBroker` and the ZK-based controller are all gone. Any answer mentioning the
   ZooKeeper ensemble, `/brokers/ids` znodes or the ZK-based controller election describes 3.x.
5. **Rebalancing is broker-driven now.** Under `group.protocol=consumer`, `session.timeout.ms`,
   `heartbeat.interval.ms`, `partition.assignment.strategy` and `enforceRebalance()` are inert;
   the broker-side `group.consumer.session.timeout.ms`, `group.consumer.heartbeat.interval.ms` and
   `group.consumer.assignors` replace them. "Stop-the-world rebalance" describes the classic
   protocol, which KIP-1274 has now deprecated.
6. **Kafka has queues.** KIP-932 share groups are production-ready as of 4.2: per-record
   acknowledgement, delivery counts, `KafkaShareConsumer`, and *more consumers than partitions*.
   "Kafka can't do competing consumers within a partition" is now false.
7. **RabbitMQ classic mirrored queues no longer exist.** Removed in 4.0 after three years of
   deprecation. Quorum queues (Raft) are the only replicated queue type; classic queues are
   non-replicated. `ha-mode`, `ha-params`, `ha-sync-mode` policies are dead configuration.
8. **RabbitMQ's metadata store is Khepri, not Mnesia.** Default since 4.2, sole option since 4.3,
   which also removed CQv1 (`x-queue-version: 1` now fails declaration) and disabled
   `transient_nonexcl_queues` by default. `cluster_partition_handling` (`pause_minority`,
   `autoheal`, `ignore`) no longer has any effect.
9. **Spring Kafka dropped Spring Retry.** 4.0 moved to Spring Framework 7's `org.springframework.core.retry`;
   `@Backoff` became `@BackOff`, `BinaryExceptionClassifier` became `ExceptionMatcher`,
   `RecoveryCallback` now takes a `RetryException` rather than a `RetryContext`, and
   `BackOffValuesGenerator` works against `BackOff` instead of `BackOffPolicy`.
10. **Spring AMQP has two stacks.** `spring-boot-starter-amqp` (AMQP 0-9-1, `RabbitTemplate`) and
    the new `spring-rabbitmq-client` module (AMQP 1.0, `RabbitAmqpTemplate`,
    `RabbitAmqpListenerContainer`, `RabbitAmqpAdmin`) over `com.rabbitmq.client:amqp-client`.
11. **SQS standard queues have a `MessageGroupId` now.** Supplying it enables **fair queues**
    (2025), which throttle a noisy tenant's delivery rather than the queue's. This is not FIFO —
    it does not order anything.
12. **SQS default message retention is 4 days**, not 14. 14 days is the maximum; 60 seconds is the
    minimum.

**Scope boundary against the sibling guides.** This file owns **the asynchronous transport**: what
a broker durably promises, what the consumer must therefore do, how the guarantee is implemented,
and what breaks. Owned elsewhere:

- CAP/PACELC, consistent hashing, quorum arithmetic `R+W>N`, the outbox as an architecture-level
  primitive, the 45-minute design structure, back-of-envelope sizing and the storage-selection
  procedure live in `22-system-design.md`. This guide owns the outbox's *mechanism* — the table,
  the relay, the CDC alternative, the duplicate it converts the problem into. `[X-REF 22]`
- Isolation levels, MVCC, `SELECT ... FOR UPDATE SKIP LOCKED`, logical decoding / WAL / binlog as
  database mechanisms, and the index the outbox poller needs live in `09-sql-databases.md`.
  `[X-REF 09]`
- `@Transactional` propagation, the proxy model, self-invocation, `TransactionSynchronization`,
  and Boot auto-configuration live in `07-spring-core.md`. This guide owns the messaging-shaped
  subset: `KafkaTransactionManager`, `ChainedKafkaTransactionManager`'s removal, container
  transactions, `@TransactionalEventListener`. `[X-REF 07]`
- The persistence context, `@Version`, `OptimisticLockException` and dirty checking live in
  `08-spring-data-jpa.md`. `[X-REF 08]`
- HTTP semantics, `Idempotency-Key`, webhooks as a published contract, `RateLimit` headers and
  status-code choice live in `12-api-design.md`. This guide owns the webhook *ingestion* side —
  verify, enqueue, return 200 fast. `[X-REF 12]`
- TCP, the receive window, Nagle, TLS handshakes, keep-alive, connection pooling and DNS live in
  `10-networking.md`. This guide owns what those change about broker behaviour. `[X-REF 10]`
- `BlockingQueue`, `ThreadPoolExecutor` queueing order, `CallerRunsPolicy`, `Semaphore`, virtual
  threads and `StructuredTaskScope` live in `05-multithreading-concurrency.md` and
  `04-modern-java.md`. This guide owns backpressure *across a broker*. `[X-REF 05]` `[X-REF 04]`
- Heap sizing, G1 humongous allocation, GC pause effects on a lock TTL, heap dumps and
  `max.poll.records` × record size arithmetic against the heap live in `06-jvm-internals.md`.
  `[X-REF 06]`
- Redis data structures, `SETNX`, Redlock as a cache-store feature, stampede prevention and
  invalidation topology live in `15-caching.md`. This guide owns Redis only as a dedup/lock
  substrate and states why it cannot join a DB transaction. `[X-REF 15]`
- SQS/SNS as AWS primitives, IAM policies, VPC endpoints, KMS, MSK/MSK Serverless provisioning,
  Kinesis, Lambda event source mappings and cost modelling live in `18-cloud-aws.md`. This guide
  owns their *messaging semantics*. `[X-REF 18]`
- Kubernetes `CronJob`, `concurrencyPolicy`, StatefulSets for brokers, PodDisruptionBudgets,
  `terminationGracePeriodSeconds` and drain-before-terminate live in `19-docker-kubernetes.md`.
  `[X-REF 19]`
- Metrics/logging/tracing practice, Micrometer, Prometheus, SLI/SLO, alert design and postmortem
  discipline live in `20-observability-operations.md`. This guide owns which messaging metrics
  exist and what each one means. `[X-REF 20]`
- Testcontainers mechanics, test slices and contract testing live in `16-testing.md`. This guide
  owns `EmbeddedKafkaKraftBroker`, `@EmbeddedKafka` and what a messaging test must assert.
  `[X-REF 16]`
- mTLS, SASL mechanisms as auth protocols, OAuth 2.x, secret rotation and TLS configuration live
  in `13-web-security.md`. This guide owns broker ACL semantics and the ingestion-side signature
  check. `[X-REF 13]`
- Big-O, heaps, hashing and consistent hashing as data structures live in `01-dsa-fundamentals.md`.
  `[X-REF 01]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the
mechanism in one paragraph *before* pointing away — it never sends the reader off empty-handed.

**Every example, topic name, queue name, status code and number comes from the QuizStakes domain
in `src/scenario/scenario.md`.** The messaging surfaces the bible must design against are the 21
domain events of § 14.1 (`ApplicationCreated`, `AccountShellCreated`, `DocumentVerdictIssued`,
`ScreeningVerdictIssued`, `AccountActivated`, `RestrictionApplied`, `RestrictionLifted`,
`PaymentStatusChanged`, `InstrumentVerified`, `BonusGranted`, `BonusExpired`,
`LedgerMovementPosted`, `LimitThresholdBreached`, `PaymentRunStatusChanged`, …), the PSP webhook
ingestion path, the bank-deposit file ingestion pipeline (`BDP-000` … `BDP-900`), the
`PaymentRun` scheduler with its leader-election requirement, the stake reserve/settle/void
boundary against the Quiz Engine black box, and the `DEP-301 → DEP-400` dual-write seam. The
services are `PaymentService`, `FundsLedger`, `CardPayments`, `BankDeposits`, `BankWithdrawal`,
`BonusService`, `ClientRestrictions`, `AccountActivation`, `NotificationService`,
`InternalPlatforms`, `ProfileService`, `PendingActions`. Never `orders`, `user-events`, `foo`,
`my-topic`, or `Dog extends Animal`.

**The load figures the bible must use are the real ones from Appendix A:** 2.4M registered
clients; 380k monthly active; 95k card deposits/day at **40/sec**; 6.5k bank deposits/day in
batch; 2.8M stake reservations/day at **1,200/sec**; 2.8M settlements/day with **3,400/sec**
bursts; 19.8M ledger entries/day, **230 writes/sec sustained and 13,600/sec peak**, ~180 bytes/row,
~1.3 TB/year, 90-day hot window, 7-year retention; 11k card withdrawals/day at 12/sec; 7k bank
withdrawals/day across **4 `PaymentRun` windows/day** of ~1.8k records each; a bank statement file
of 40k records (500k at month end); 24k document uploads/day at 2–6 MB each; 2.6M
`ApplicationHistory` records/day at ~400 bytes; 38k restriction records/day; a **30 ms**
restriction-decision budget, a **150 ms** stake-reservation budget, a **hard 500 ms**
self-exclusion budget, a **4 s** card-deposit end-to-end budget, and a **24 h** withdrawal-submit
budget; three `FundsLedger` instances at 12 GB heap; PSP capture p50 180 ms / p99 6 s / timeout
10 s at 500/sec; banking-partner payout file p50 2 s / p99 45 s / timeout 60 s.

**The four architectural rules from scenario § 5.1 constrain every design in this guide** and the
bible must say so at the point of decision: only `FundsLedger` writes money; tokens carry identity
and authority is asked for synchronously (so `ClientRestrictions` is **never** consulted over
messaging — scenario B.3 says so explicitly); every external vendor sits behind exactly one owning
service; and no cross-schema joins, which is why events exist at all. Add the fifth, from
scenario § 14.1: **the domain-event partition key is client id**, which buys per-client ordering
and creates the whale hot-partition problem in the same decision.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real spec text, KIP text, documentation, Kafka/RabbitMQ source or javadoc (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is SQL/YAML/CLI) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value, quota or byte/throughput arithmetic explicitly |
| `[CFG]` | give the exact configuration property name and its default value |
| `[API]` | give the exact Java/Spring type, method signature or annotation attribute |
| `[WIRE]` | show the actual bytes/frames/request names on the wire, not a description of them |
| `[CLI]` | show the exact command (`kafka-consumer-groups.sh`, `rabbitmqctl`, `aws sqs …`) and read its output |
| `[METRIC]` | name the exact metric (JMX MBean, CloudWatch metric, Prometheus series) and what a bad value looks like |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — a log line, an exception, a `describe` dump — and read it line by line |
| `[TABLE]` | must be rendered as a table |
| `[SPEC]` | cite the specific spec/KIP section, not just the number |

---

# PART 1 — BASICS

## §1.1 Why asynchronous messaging exists at all

1.1.1 The origin problem: two services on two release cadences, one of which is slow, unreliable
      or absent, must still exchange work without the caller's fate being tied to the callee's.
      `[PROVE]`
1.1.2 **Decoupling** as reason one — the producer does not know who consumes, how many consumers
      exist, or whether any is running. Worked against `AccountActivated`, which
      `AccountMaintenance`, `ClientRestrictions`, `PaymentService` and `NotificationService` all
      consume without `AccountActivation` knowing.
1.1.3 The three axes decoupling actually buys, named separately: **temporal** (they need not be up
      at the same time), **spatial** (no address knowledge), **format** (schema, not signature).
      `[TABLE]`
1.1.4 **Buffering / load levelling** as reason two — the settlement burst of 3,400/sec against a
      ledger provisioned for 230/sec sustained. `[NUM]`
1.1.5 The core trade restated precisely: a queue converts a **throughput** problem into a
      **latency** problem, and that is usually the better problem to have. `[PROVE]`
1.1.6 **Asynchrony** as reason three — ack the card deposit at `DEP-400 CREDITED` and let
      `NotificationService` send the email off the hot path, inside the 4 s budget. `[NUM]`
1.1.7 **Retries with durability** as reason four — an in-process `@Async` executor or
      `ThreadPoolExecutor` loses every queued task on pod restart; a broker does not. `[X-REF 05]`
1.1.8 **Fan-out / read-model construction** as reason five — `BalanceView`, `ProfileService` and
      `PendingActions` are all projections fed by events.
1.1.9 **Buffer against a rate-limited dependency** as reason six — the identity vendor's 600/min
      estate-wide cap against 24k uploads/day. `[NUM]`
1.1.10 The costs, enumerated and non-negotiable: eventual consistency, duplicate delivery,
      near-total loss of ordering, debugging across processes and time, schema versioning, a new
      stateful system to operate, and the cost of the message itself. `[TABLE]`
1.1.11 When **not** to add a queue: the caller needs the answer (the `ClientRestrictions` decision
      at 30 ms), the operation is cheap and reliable, or the added indirection buys nothing.
      Scenario B.3's "restriction decisions: synchronous call, never messaging" as the canonical
      example. `[TRAP]`
1.1.12 "A queue is another database" — the broker is durable, stateful, replicated, has a storage
      engine and needs capacity planning, backups, upgrades and on-call.
1.1.13 The honest framing of what a broker is: a **replicated write-ahead log with a delivery
      policy bolted on**. Every difference between Kafka, RabbitMQ and SQS is a difference in the
      delivery policy, not in the log. `[PROVE]`
1.1.14 Messaging vs streaming vs eventing vs RPC — four words people use interchangeably and the
      distinction that actually matters (who owns the position). `[TABLE]`

## §1.2 The vocabulary, stated once

1.2.1 **Message** vs **event** vs **command** vs **document** — four intents, three of which get
      different infrastructure. `[TABLE]`
1.2.2 Command (`ReserveStake`, imperative, one handler, may be refused) vs event
      (`LedgerMovementPosted`, past tense, many listeners, cannot be refused). Naming discipline
      as a design tool.
1.2.3 **Producer / publisher / sender** — the same role under three protocol vocabularies.
1.2.4 **Consumer / subscriber / receiver / worker**.
1.2.5 **Broker / server / node / cluster**.
1.2.6 **Topic** (Kafka, JMS, SNS) vs **queue** (SQS, AMQP, JMS) vs **exchange** (AMQP) vs
      **stream** (RabbitMQ Streams, Kinesis). `[TABLE]`
1.2.7 **Partition** (Kafka) vs **shard** (Kinesis) vs **message group** (SQS FIFO/fair) vs
      **queue instance** (AMQP) as the four spellings of "the unit of parallelism and ordering".
1.2.8 **Offset** vs **delivery tag** vs **receipt handle** vs **acquisition lock** — the four
      spellings of "the consumer's position or claim". `[TABLE]`
1.2.9 **Acknowledgement** — the single most overloaded word in the topic. Producer ack (durability)
      vs consumer ack (progress) are unrelated mechanisms with the same name. `[TRAP]`
1.2.10 **Durability** vs **persistence** vs **replication** vs **availability** — four separate
      properties, each configured separately.
1.2.11 **Retention** vs **deletion on ack** as the two lifecycle models.
1.2.12 **Backlog / queue depth / lag / dwell time** — four metrics, three of which are not
      interchangeable. `[METRIC]`
1.2.13 **In-flight** / **unacked** / **acquired** / **invisible** — one state under four names.
1.2.14 **DLQ** vs **DLX** vs **DLT** vs **parking lot** — dead-lettering under four vocabularies,
      plus "quarantine topic" as the Confluent name.
1.2.15 **Fan-out** vs **fan-in** vs **competing consumers** vs **pub-sub**.
1.2.16 **Replay** vs **redelivery** vs **retry** — three different operations people call "retry".
      `[TRAP]`
1.2.17 **Idempotence** vs **deduplication** vs **exactly-once** — three claims of different
      strength.
1.2.18 **Poison message**, **head-of-line blocking**, **backpressure**, **retry storm** as the
      four named failure vocabularies used throughout.

## §1.3 The three roles and what each is actually responsible for

1.3.1 **Producer** responsibilities enumerated: serialise, choose the destination and key, obtain
      a durability guarantee, decide the failure policy (retry / buffer / fail the request /
      outbox), and attach the correlation id and event id.
1.3.2 The producer's only real question: *did the broker durably accept this?* — and the three
      answers (`acks=0/1/all` in Kafka, publisher confirms in AMQP, HTTP 200 from `SendMessage`
      in SQS). `[CFG]`
1.3.3 **Broker** responsibilities: receive, persist, replicate, index, hand out, track progress,
      expire, dead-letter, enforce quotas and authorise.
1.3.4 What state the broker keeps about the consumer, per system: Kafka a committed offset in
      `__consumer_offsets`; SQS a per-message in-flight state plus receive count; AMQP a per-channel
      unacked delivery-tag set; Kafka share groups a per-record acquisition state in
      `__share_group_state`. `[TABLE]`
1.3.5 **Consumer** responsibilities: fetch, deserialise, validate, process idempotently,
      acknowledge, handle poison, and report health.
1.3.6 **Both Kafka and SQS are pull-based.** The "push" feel of `@KafkaListener` and
      `@SqsListener` is a poll loop on a container thread. `[TRAP]`
1.3.7 **AMQP 0-9-1 is genuinely push** — `basic.consume` registers a consumer and the broker pushes
      `basic.deliver` frames, throttled by `basic.qos` prefetch. `basic.get` is the polling
      alternative and is a documented anti-pattern for throughput. `[WIRE]`
1.3.8 Push vs pull as a design decision: pull gives the consumer natural flow control and easy
      batching; push gives lower latency and needs an explicit credit mechanism. Kafka's design
      document argues this explicitly. `[SOURCE]`
1.3.9 The fourth role nobody names: the **coordinator** — Kafka's group coordinator and
      transaction coordinator, RabbitMQ's Ra leader, SQS's internal placement. It is where the
      interesting failures live.
1.3.10 The fifth role: the **operator** — retention policy, partition count, alert thresholds,
      replay tooling. Every one of those is a design decision that outlives the code.
1.3.11 Where each role lives in QuizStakes: `PaymentService` produces `PaymentStatusChanged`,
      `NotificationService` and `ProfileService` consume it, and neither knows the other exists.
1.3.12 Client-library responsibilities that are easy to mistake for broker responsibilities:
      batching, compression, partition selection, retry, metadata refresh, and offset commit are
      all **client-side** in Kafka. `[TRAP]`

## §1.4 Topologies and the messaging patterns that name them

1.4.1 **Point-to-point / competing consumers** — one message, one handler, N workers scaling
      throughput. Bank-deposit file record matching.
1.4.2 **Publish–subscribe** — one message, N independent subscribers each getting a copy.
1.4.3 **Fan-out** — SNS → many SQS queues, or one Kafka topic → many consumer groups. Why the two
      are structurally different (copy vs shared log). `[PROVE]`
1.4.4 **Fan-in / aggregator** — many producers, one queue; and the ordering consequence.
1.4.5 **Request–reply over messaging** — correlation id, reply-to queue, and why this is usually a
      sign you wanted RPC. AMQP `reply_to` + `correlation_id`; RabbitMQ **direct reply-to**
      (`amq.rabbitmq.reply-to`), extended to AMQP 1.0 in RabbitMQ 4.2. `[RESEARCH]`
1.4.6 Spring's `ReplyingKafkaTemplate` and `RabbitTemplate.convertSendAndReceive` as the two Java
      surfaces for request–reply. `[API]`
1.4.7 **Content-based router** and **message filter** — SNS subscription filter policies,
      EventBridge event patterns, RabbitMQ topic/headers exchanges, RabbitMQ 4.2 SQL filter
      expressions on streams. `[RESEARCH]`
1.4.8 **Splitter / aggregator** — the 40k-record bank statement file split into per-record
      messages, and the month-end 500k variant.
1.4.9 **Scatter–gather** — `ProfileService` assembling eight owners; why it is done over HTTP here
      and not over messaging. `[X-REF 12]`
1.4.10 **Claim check** — payload in object storage, reference in the message. The document-image
      case at 2–6 MB, well past even the 1 MiB SQS limit. `[NUM]`
1.4.11 **Priority queue** — AMQP `x-max-priority`, quorum queues' fixed 0–31 priority levels in
      RabbitMQ 4.x, and why Kafka has no priority (and the multi-topic workaround).
1.4.12 **Delay / scheduled message** — SQS `DelaySeconds` (0–900 s), delay queues, the RabbitMQ
      delayed-message-exchange plugin, quorum queues' `x-delayed-retry-*` in 4.3, and the Kafka
      retry-topic-with-sleep approach. `[CFG]` `[RESEARCH]`
1.4.13 **Dead-letter channel** — the pattern behind DLQ/DLX/DLT.
1.4.14 **Guaranteed delivery / store-and-forward** — the property every broker sells.
1.4.15 **Transactional client / channel** — AMQP `tx.select` (and why it is slow and unused),
      Kafka transactions, JMS transacted sessions.
1.4.16 **Message bus vs message broker vs event mesh vs service mesh** — vocabulary hygiene.
1.4.17 **Choreography vs orchestration** as the topology-level version of the same choice.
      Forward-referenced to §2.13.
1.4.18 **Change data capture** as a topology: the database itself becomes the producer.
      `[X-REF 09]`
1.4.19 **Webhook ingestion** as a topology: HTTP in, verify signature, enqueue, return 200 in
      milliseconds, process asynchronously. Scenario B.3: "never process on the webhook thread."
      The PSP delivering the same capture webhook five times is scenario § 15.2's example.
      `[X-REF 12]`
1.4.20 **Outbox** as a topology: the database is the queue of record and the broker is downstream.

## §1.5 THE BROKER LIFECYCLE — the single most-missed concept

1.5.1 The assertion, stated first and unhedged: **when consumers are down, messages sit in the
      queue, durably, waiting. They do NOT go to the dead-letter queue.** `[TRAP]`
1.5.2 The DLQ precondition, stated as a rule: a message reaches a DLQ **only** after being
      **delivered to a consumer** and **failing N times**, or by exceeding a max-receives /
      delivery-limit policy. No delivery attempt → no failure → no DLQ. `[PROVE]`
1.5.3 The full lifecycle as an ordered trace: `send` → broker persists and replicates → durable →
      (no consumers → waits, depth grows) → consumer polls → attempt #1 → ack/commit → removed
      (SQS) or offset advances (Kafka); or exception / visibility expiry → attempt #2, #3 … →
      attempt N fails → DLQ. `[FLOW]`
1.5.4 Why people get it wrong: "consumers are down" *feels* like a failure, and DLQ is where
      failures go. The broker has no concept of "the consumer is down" — it has a queue and a set
      of connections, and zero connections is a legitimate, routine state. `[PROVE]`
1.5.5 Zero connected consumers happens on **every deploy**, for tens of seconds, several times a
      day. That is the argument that makes the point land.
1.5.6 What actually happens when consumers are down, in order: (1) producers keep succeeding;
      (2) queue depth / consumer lag rises; (3) broker disk grows; (4) on recovery, throughput is
      the constraint; (5) messages past retention are **silently deleted**. `[FLOW]`
1.5.7 The recovery arithmetic, worked: a 2-hour outage on the 1,200/sec stake-event stream leaves
      8.64M messages; consumers doing 1,500/sec drain the backlog only 300/sec faster than it
      arrives, so catch-up takes **8 hours**. Scaling out is bounded by partition count.
      `[NUM]` `[PROVE]`
1.5.8 The real data-loss risk of a long consumer outage is **retention expiry**, and it has
      nothing to do with the DLQ. `[NUM]`
1.5.9 Retention numbers to state: Kafka `retention.ms` default 604800000 (7 days); SQS
      `MessageRetentionPeriod` default 345600 (4 days), min 60, max 1209600 (14 days); RabbitMQ
      queues have no default retention at all (they grow until `x-max-length` / `overflow` /
      disk alarm). `[CFG]` `[NUM]` `[VERSION-TRAP]`
1.5.10 The second failure mode nobody mentions: **`offsets.retention.minutes` = 10080** (7 days).
      If a consumer group is empty for longer than that, its committed offsets are deleted and the
      group restarts at `auto.offset.reset` — which for `latest` is silent data loss and for
      `earliest` is a full replay. `[CFG]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.5.11 Broker-side back-pressure when nobody drains: Kafka `log.retention.bytes` /
      `retention.bytes` and the disk filling; RabbitMQ **memory and disk alarms** blocking
      publishers; SQS's absence of any such limit (it is AWS's disk, not yours). `[CFG]` `[TABLE]`
1.5.12 The corollary questions, each with the one-line answer: "consumers down 3 hours — where are
      the messages?"; "how do you know?"; "what breaks first?"; "a message is in the DLQ — what do
      you know for certain?" `[TABLE]`
1.5.13 What a DLQ message proves: it was **delivered** at least N times and processing **threw**
      every time. The bug is in the consumer or the payload, not the transport. `[PROVE]`
1.5.14 The three *other* ways a message can leave a queue without being processed, so the reader
      does not over-generalise: TTL/retention expiry, `x-max-length` overflow with `drop-head`,
      and an operator purge. Only the middle one is configurable per-queue. `[TABLE]`
1.5.15 The AMQP variant of the same lifecycle, because the mechanism differs: the message sits in
      the queue; a consumer registers; delivery is pushed; `basic.ack` removes it; `basic.nack`
      with `requeue=false` or exceeding `x-delivery-limit` (default **20** in RabbitMQ 4.x)
      dead-letters it. `[CFG]` `[NUM]` `[RESEARCH]`
1.5.16 The alert that proves you understand the lifecycle: alert on **queue depth / lag rising**,
      not on DLQ depth, for a consumer outage — and alert on **DLQ depth > 0** for a poison
      message. Two different symptoms, two different alarms. `[METRIC]`
1.5.17 What the `ORPHANED` stake state teaches: a broker's redelivery mechanism cannot help you
      when the *other* party never replies. Timeouts and ageing, not retries, are the tool.
1.5.18 A worked "what does the graph look like" reading: depth up-and-right with DLQ flat = outage;
      depth flat with DLQ climbing = poison; both flat with producers active and lag frozen =
      stuck or rebalancing consumers. `[DIAG]`

## §1.6 Delivery semantics — determined by where you acknowledge

1.6.1 The single idea: **the guarantee you get is a consequence of when you acknowledge relative
      to when you do the work.** `[PROVE]`
1.6.2 **At-most-once** — ack before processing. Possible loss, no duplicates. Code, plus the exact
      crash point. `[BUILD]`
1.6.3 When at-most-once is genuinely right: disposable telemetry, sampled metrics, best-effort
      cache warmers. Never for a `LedgerMovementPosted`.
1.6.4 **At-least-once** — ack after processing. No loss, duplicates possible. The window between
      the DB commit and the ack can never be closed. `[PROVE]`
1.6.5 At-least-once is the default of SQS, of Kafka with commit-after-process, and of AMQP with
      manual ack — and it is the correct default for virtually every production system.
1.6.6 **Exactly-once delivery is impossible** across an unreliable network. The two-generals
      argument, worked properly: the sender can never be certain its ack arrived, so it must
      either resend (duplicate) or not (loss). `[PROVE]`
1.6.7 **Exactly-once *processing/effect*** is achievable: at-least-once delivery + an idempotent
      consumer. The distinction between *delivery* and *effect* is the whole answer. `[PROVE]`
1.6.8 Kafka's EOS is real but narrow: transactional producer + `isolation.level=read_committed`
      gives atomic consume-transform-produce **within Kafka**. An external DB, an email or a PSP
      call is not covered. `[TRAP]`
1.6.9 The sentence to say in an interview, verbatim: *"I'd design for at-least-once delivery with
      an idempotent consumer. Exactly-once delivery isn't achievable across a network; exactly-once
      effect is, and idempotency is how you get it."*
1.6.10 The fourth semantic nobody names: **at-least-once with ordering**, which is strictly harder
      than either alone, because a retry that reorders breaks the second guarantee.
1.6.11 The producer-side mirror: at-most-once send (`acks=0`), at-least-once send (retries without
      idempotence), exactly-once send (`enable.idempotence=true` deduplicating on PID + sequence
      number per partition). `[CFG]`
1.6.12 Where each system's default sits. `[TABLE]`
1.6.13 Auto-commit as the trap that silently changes your semantics:
      `enable.auto.commit=true` with `auto.commit.interval.ms=5000` commits on a timer inside
      `poll()`, which means offsets can advance past records you have not finished — at-most-once
      by accident. It is also not guaranteed to fire before partition revocation. `[CFG]` `[TRAP]`
      `[RESEARCH]`
1.6.14 The AMQP mirror: `autoAck=true` on `basic.consume` is at-most-once and the message is gone
      the moment it hits the socket. `[WIRE]` `[TRAP]`
1.6.15 The SQS mirror: `DeleteMessage` before processing is at-most-once; after processing is
      at-least-once; and the visibility timeout is what makes the second one work without the
      broker tracking liveness.
1.6.16 "Effectively once" as a marketing term, and what it actually decomposes into.

## §1.7 The idempotent consumer — the concrete design

1.7.1 The mechanism that works: a stable **event id** assigned by the **producer**, recorded in the
      **same transaction** as the side effect. `[PROVE]`
1.7.2 Why the producer must assign it: a broker-assigned id (SQS `MessageId`, Kafka
      topic-partition-offset) may differ across redeliveries or across a replay. `[TRAP]`
1.7.3 The `processed_events` table: `event_id UUID PRIMARY KEY`, `consumer TEXT`, `processed_at
      TIMESTAMPTZ`. Why the consumer name is part of the design when several services consume the
      same event. `[BUILD]`
1.7.4 The handler: insert-then-catch-`DuplicateKeyException`-and-return, both statements inside one
      `@Transactional`. `[BUILD]`
1.7.5 **Why the same transaction is non-negotiable**, proved both ways: id-first-then-work converts
      at-least-once into at-most-once; work-first-then-id yields duplicates. Atomicity is the
      correctness argument. `[PROVE]`
1.7.6 Alternative 1 — **naturally idempotent operations**. `SET status = 'ACTIVE'` is idempotent by
      construction; `balance = balance + 10` is not. Best possible answer: no bookkeeping.
1.7.7 Alternative 2 — **upsert on a business key**: `INSERT … ON CONFLICT (payment_id) DO UPDATE`.
      `[SQL]`
1.7.8 Alternative 3 — the **dedup table**, general purpose, needing a cleanup job sized to the
      redelivery window (retention + margin) or it grows forever. At 19.8M ledger movements/day
      with a 7-day window that is ~139M rows. `[NUM]`
1.7.9 Alternative 4 — **Redis `SET key val NX PX`**, fast but a separate system, so it cannot join
      the DB transaction; there is a window where Redis says done and the DB rolled back.
      Acceptable for low stakes, never for money. Scenario B.2 states the rule: the cache is the
      fast path, the **unique constraint is the guarantee**. `[X-REF 15]`
1.7.10 Alternative 5 — **optimistic concurrency / version numbers**: reject an event whose version
      is ≤ the stored version. Handles out-of-order delivery too. `[X-REF 08]`
1.7.11 Alternative 6 — **conditional writes** (DynamoDB `ConditionExpression`, `UPDATE … WHERE
      status = 'PENDING'`) as the claim-based form.
1.7.12 Alternative 7 — **broker-side dedup**: SQS FIFO `MessageDeduplicationId` with a **5-minute**
      window, or content-based dedup via SHA-256 of the body. Why 5 minutes is far too short to be
      your only defence. `[NUM]` `[TRAP]`
1.7.13 **Trap: idempotent side effect, non-idempotent handler.** The DB write is skipped on
      redelivery but the email still sends. Every non-idempotent effect needs covering — which is
      the strongest argument for handlers that do exactly one thing. `[TRAP]`
1.7.14 The QuizStakes cases, each with the right technique: PSP webhook delivered five times → one
      credit (dedup on the PSP event id); `AccountActivated` consumed twice → restrictions must
      lift idempotently; `SettleStake` twice for one round → the ledger idempotency key
      (invariant 8/11).
1.7.15 The idempotency **key scope** question: per-consumer, per-topic, or global? Getting this
      wrong makes two different consumers of the same event silently skip each other's work.
      `[TRAP]`
1.7.16 The idempotency **key lifetime** question, and why "forever" is a real answer for money.
1.7.17 The **inbox pattern** named: `processed_events` is the inbox, and it is the exact mirror of
      the outbox.
1.7.18 Testing idempotency: the only honest test replays the same message twice and asserts one
      effect. `[X-REF 16]`

## §1.8 Poison messages, retries and the dead-letter queue

1.8.1 Definition of a **poison message**: one that will fail every time — malformed payload,
      unknown schema, a reference to a deleted entity, an unsatisfiable business rule.
1.8.2 What a poison message does without a DLQ: blocks the partition forever (Kafka) or cycles
      indefinitely (SQS/AMQP), burning capacity and filling logs.
1.8.3 The failure taxonomy that must precede any retry decision: transient / poison / ambiguous.
      `[TABLE]`
1.8.4 Transient — timeout, 503, deadlock, connection reset, throttling: **retry with backoff**.
1.8.5 Poison — deserialisation failure, validation failure, 400, `ClassCastException`: **do not
      retry**; go straight to the DLQ. Retrying wastes capacity and delays everything behind it.
1.8.6 Ambiguous — a 500 from a downstream: retry, bounded.
1.8.7 The fourth category nobody lists: **the message that must never be retried because retry is
      itself dangerous** — the PSP capture that timed out. Scenario A.4: "Timeout ≠ failure."
      `[TRAP]`
1.8.8 **Exponential backoff** — 1 s, 2 s, 4 s, 8 s, 16 s — and why immediate retry hammers a
      struggling dependency at exactly the moment it needs relief.
1.8.9 **Jitter** as the thing that prevents synchronised retry waves. Full jitter:
      `random(0, min(base * 2^attempt, cap))`. `[BUILD]` `[PROVE]`
1.8.10 The jitter families named: none, full, equal, decorrelated. Which one AWS recommends and
      why full jitter spreads load best. `[TABLE]`
1.8.11 **Where to retry matters**: in-process retry (Spring Retry / Resilience4j) holds the thread
      and blocks the partition; broker-level retry (visibility timeout, retry topics, quorum-queue
      delayed retry) releases it.
1.8.12 The retry-attempt budget: `maxReceiveCount` (SQS), `x-delivery-limit` (RabbitMQ quorum,
      default 20), `maxAttempts` in `@RetryableTopic` (default 3), `DefaultErrorHandler`'s
      `FixedBackOff(0L, 9L)` default of 10 total attempts. `[CFG]` `[NUM]` `[RESEARCH]`
1.8.13 DLQ operations, part 1 — **alert on depth > 0**, not on a threshold. One poison message
      today is a schema bug that becomes 100,000 tomorrow. `[METRIC]`
1.8.14 DLQ operations, part 2 — **keep enough context**: the original message and its headers, the
      exception class and stack trace, the attempt count, timestamps, the correlation id
      (`[X-REF 20]`), the consumer version, and the original topic/partition/offset. Spring's
      `DeadLetterPublishingRecoverer` writes exactly this set as `KafkaHeaders.DLT_*` headers.
      `[API]` `[TABLE]`
1.8.15 DLQ operations, part 3 — **a tested replay path**. SQS has native DLQ redrive
      (`StartMessageMoveTask`); Kafka needs a replay app; RabbitMQ needs a shovel or a script.
      Test it before 3 a.m. `[CLI]`
1.8.16 DLQ operations, part 4 — **replay is only safe with idempotent consumers**, and after a fix
      replayed messages are frequently duplicates of partially-succeeded ones. §1.7 is the
      prerequisite for §1.8.
1.8.17 DLQ operations, part 5 — **set and monitor DLQ retention**, and treat expiry as real data
      loss. SQS DLQs inherit the original enqueue timestamp on standard queues, so a message that
      spent 1 day in the source queue only gets 3 more in a 4-day DLQ. On FIFO queues the timestamp
      **resets**. `[NUM]` `[TRAP]` `[RESEARCH]`
1.8.18 **Trap: DLQ-then-ack ordering.** Send to the DLQ, confirm the send, *then* ack the original.
      If the DLQ send fails, do not ack — let it redeliver. `[TRAP]`
1.8.19 The DLQ-of-the-DLQ question and the honest answer (log + alert + stop; do not build a
      tower).
1.8.20 **Parking lot / quarantine topic** as the name for a DLQ you intend to triage manually.
1.8.21 The obscure SQS rule: on a **standard** queue with `maxReceiveCount > 3`, a message received
      3+ times without deletion is moved to the **back of the queue**, and
      `ApproximateAgeOfOldestMessage` then reflects the next message instead. `[NUM]` `[RESEARCH]`
1.8.22 Why a FIFO queue plus a DLQ is a contradiction you must think about: dead-lettering one
      message of a group breaks the very ordering you paid for. AWS documents the warning.
      `[TRAP]` `[RESEARCH]`

## §1.9 Ordering

1.9.1 The honest statement: ordering is guaranteed **only within a Kafka partition / SQS message
      group / single AMQP queue with one consumer**, and only if you process serially.
1.9.2 Why global ordering is unavailable: it requires a single serialisation point, which means one
      partition and one consumer — no parallelism. Ordering and throughput are directly opposed.
      `[PROVE]`
1.9.3 Partition-key choice as a design decision: Kafka hashes the key (`murmur2`) modulo the
      partition count, so same key → same partition → ordered relative to each other. `[NUM]`
1.9.4 Choosing the key to match the requirement: per-payment ordering → `paymentId`; per-client
      ordering → `clientId` (which is what scenario § 14.1 actually specifies); no ordering
      requirement → `null`.
1.9.5 Pick the **narrowest** key that satisfies the requirement — a broader key means fewer
      effective parallel streams. `[PROVE]`
1.9.6 **Hot-key skew**: the whale client, the `null` tenant, the "default" account. One consumer
      saturates while the others idle. Symptoms: lag concentrated on one partition, uneven CPU.
      Scenario names it: "partition key is client id … creates the whale hot-partition problem.
      Same decision, both consequences."
1.9.7 Hot-key mitigations, each with its cost: composite keys with a bucket suffix (relaxes
      ordering to sub-streams), a dedicated topic/consumer for the hot key, provisioning for the
      peak. There is no elegant fix. `[TABLE]`
1.9.8 **Trap: a single-partition topic gives ordering *and* a hard cap of one active consumer.**
      Every other instance idles. You chose ordering over all scalability, usually without meaning
      to. `[TRAP]`
1.9.9 **Trap: handing messages to an executor inside the consumer destroys per-partition
      ordering**, even though the broker delivered them in order. `[TRAP]` `[X-REF 05]`
1.9.10 **Trap: producer retries reorder.** Without `enable.idempotence=true`, a failed batch
      retried while a later batch succeeded flips their order — which is why
      `max.in.flight.requests.per.connection > 1` is unsafe for non-idempotent producers, and safe
      up to 5 with idempotence. `[CFG]` `[NUM]` `[PROVE]` `[TRAP]`
1.9.11 Out-of-order arrival across partitions is **normal**; downstream logic should be
      order-tolerant (version numbers, `updated_at` comparison, last-write-wins on a timestamp).
1.9.12 The QuizStakes ordering hazard, stated in full: `RestrictionApplied(SELF_EXCLUDED)` arriving
      after `PaymentStatusChanged(CREDITED)` means an excluded client was credited — and the
      500 ms hard budget is why self-exclusion is **not** delivered over messaging at all.
      `[PROVE]`
1.9.13 Clock skew as the reason "which came first" is not answerable from timestamps.
      `[X-REF 22]`
1.9.14 Total order broadcast as the theoretical name, and its equivalence to consensus — which is
      why nobody offers it cheaply. `[PROVE]`
1.9.15 Causal ordering, vector clocks and sequence numbers per aggregate as the practical
      alternatives when you need "after X" rather than "in absolute order".
1.9.16 **Single Active Consumer** (RabbitMQ) and **SQS FIFO message group** as the two
      productised forms of "ordering without a single global queue".

## §1.10 Queue vs log — the highest-leverage distinction

1.10.1 The mental test: in a **queue**, consuming *removes*; in a **log**, consuming *advances a
      pointer*. Everything else follows from that one difference. `[PROVE]`
1.10.2 The full comparison across model, post-consumption fate, position ownership, second
      consumer, replay, ordering, consumer scaling, throughput, operational load, retention and
      cost. `[TABLE]`
1.10.3 Consequence 1 — **adding a consumer later**. Kafka: new `group.id`, start at offset 0.
      SQS: the messages are gone; the fan-out (SNS/EventBridge) had to exist *in advance*.
      Retrofitting fan-out onto point-to-point SQS is a genuine migration.
1.10.4 Consequence 2 — **reprocessing after a bug**. Kafka: reset the offset three days back and
      replay. SQS: unrecoverable from the queue; go to the source system.
1.10.5 Consequence 3 — **event sourcing, stream processing and building a new read model require a
      log.** A queue cannot do it. Scenario § 15.2: `ApplicationHistory` is already an event log
      and status is a projection over it.
1.10.6 Consequence 4 — **backlog is cheap in a log and expensive in a queue**, because the log was
      going to store the bytes anyway.
1.10.7 Consequence 5 — **the queue can tell you its depth; the log can only tell you your lag.**
      Two different questions. `[METRIC]`
1.10.8 Choose a queue when: the message is a *task*, one logical consumer, no replay need, zero-ops
      wanted, per-message retry/delay/priority wanted.
1.10.9 Choose a log when: the message is an *event* many systems care about, replay matters,
      per-key ordering matters, or you are building stream processing.
1.10.10 The naming discipline that makes the choice obvious: **commands → queue, events → log.**
1.10.11 The hybrid systems that blur it: RabbitMQ **Streams** (append-only, offset-based,
      non-destructive read) and Kafka **share groups** (queue semantics over a log). Both exist
      because the two models genuinely converge under pressure. `[VERSION-TRAP]` `[RESEARCH]`
1.10.12 Scenario B.3's mapping as the worked decision: domain events → durable log partitioned by
      client id; work distribution → queue with visibility timeout + DLQ; fan-out → log, not queue,
      "because each consumer needs its own offset".
1.10.13 The cost model that decides it in practice: SQS at $0.40 per million requests versus a
      3-broker MSK cluster's fixed monthly floor. Below a threshold, a queue is simply cheaper.
      `[X-REF 18]`

## §1.11 Kafka — the essential model

1.11.1 **Topic** — a named, partitioned, append-only stream; a logical name only, with no storage
      of its own.
1.11.2 **Partition** — the unit of parallelism *and* ordering; an ordered, immutable, append-only
      log on one broker's disk, replicated to `replication.factor` brokers. `[CFG]`
1.11.3 **Record** — key, value, timestamp, headers, offset, and the partition leader that assigned
      it.
1.11.4 **Offset** — a monotonically increasing 64-bit position *within a partition*. Not global,
      not a timestamp, not an id. `[TRAP]`
1.11.5 **Leader and followers** — all reads and writes go to the leader; followers fetch.
      (`replica.selector.class` and follower fetching for rack locality as the exception.)
      `[CFG]`
1.11.6 **ISR — in-sync replicas** — the subset of replicas caught up within
      `replica.lag.time.max.ms` (default 30000). `[CFG]` `[NUM]`
1.11.7 **High watermark** — the highest offset replicated to all ISR members; consumers cannot read
      past it. This is *why* `acks=all` and consumer visibility are the same mechanism. `[PROVE]`
1.11.8 **Consumer group** — a set of instances sharing `group.id`, across which partitions are
      assigned. `[CFG]`
1.11.9 The rule that determines your scaling ceiling: **each partition is consumed by exactly one
      consumer in the group at any time**, so a group cannot usefully exceed the partition count.
      12 partitions, 20 instances → 8 idle. `[PROVE]` `[NUM]`
1.11.10 Adding partitions later **changes the key→partition mapping** and breaks ordering for
      existing keys — and you cannot remove partitions at all. Over-provision up front.
      `[TRAP]`
1.11.11 **Rebalancing** — what triggers it (join, leave, crash, topic metadata change), and the
      two protocols: classic (eager / cooperative-sticky) and the KIP-848 broker-driven protocol.
      `[VERSION-TRAP]`
1.11.12 The eviction configs that cause the classic **rebalance loop**: `max.poll.interval.ms`
      (default 300000), `session.timeout.ms` (default 45000), `heartbeat.interval.ms`
      (default 3000), `max.poll.records` (default 500). Under `group.protocol=consumer` the first
      still applies but the others move server-side. `[CFG]` `[NUM]` `[VERSION-TRAP]`
1.11.13 The rebalance-loop symptom: a group that is "up", consuming nothing, logging
      `CommitFailedException`, with lag frozen. Fixes: process faster, lower `max.poll.records`,
      raise the interval, or move the work off the poll thread. `[DIAG]`
1.11.14 **Head-of-line blocking** within a partition — one slow or failing record blocks everything
      behind it, and there is no "skip and come back". This is the price of ordering.
1.11.15 The retry-topic pattern as the answer: on failure, publish to `payments.retry.5s`, commit,
      move on; a separate consumer handles the delay; the last hop is `payments.dlt`.
1.11.16 **Consumer lag** = log-end offset − committed offset, per partition. The four readings:
      flat near zero (healthy), rising steadily (under-provisioned), rising on one partition (hot
      key or stuck instance), frozen with producers active (stuck or rebalancing). `[METRIC]`
1.11.17 Producer durability: `acks=0` / `acks=1` / `acks=all`, with `min.insync.replicas` (default
      1, should be 2) and `replication.factor` (3). `[CFG]` `[NUM]`
1.11.18 **Trap: `acks=all` alone does not mean durable.** With `min.insync.replicas=1` it means
      "the leader has it". The pair `acks=all` + `min.insync.replicas=2` + `replication.factor=3`
      is the actual configuration. `[TRAP]` `[PROVE]`
1.11.19 `enable.idempotence` — default **true** since 3.0 — deduplicating producer retries per
      partition via PID + sequence number, and the configs it forces (`acks=all`, `retries>0`,
      `max.in.flight ≤ 5`). `[CFG]` `[VERSION-TRAP]`
1.11.20 **Retention**: time (`retention.ms`, 7 days), size (`retention.bytes`, −1), or
      **compaction** (`cleanup.policy=compact`) keeping the latest value per key. `compact,delete`
      as the combined mode. `[CFG]`
1.11.21 **Log compaction** as the changelog/snapshot model — ideal for CDC, state restore and
      `__consumer_offsets` itself.
1.11.22 **`__consumer_offsets`** — the internal compacted topic, 50 partitions by default
      (`offsets.topic.num.partitions`), where committed offsets actually live. `[CFG]` `[NUM]`
1.11.23 **KRaft** — the controller quorum that replaced ZooKeeper; `__cluster_metadata` as the
      metadata log; controller vs broker vs combined roles. `[VERSION-TRAP]`
1.11.24 **Share groups (KIP-932)** — `group.type=share`, `KafkaShareConsumer`, per-record
      acknowledgement (`ACCEPT`/`RELEASE`/`REJECT`), delivery counts, acquisition locks, and *more
      consumers than partitions*. Production-ready in 4.2. `[VERSION-TRAP]` `[RESEARCH]`
1.11.25 The CLI surface every engineer must have used: `kafka-topics.sh --describe`,
      `kafka-consumer-groups.sh --describe --group`, `--reset-offsets` with
      `--to-earliest/--to-datetime/--shift-by`, `kafka-console-consumer.sh`,
      `kafka-configs.sh --alter`, `kafka-groups.sh`, `kafka-share-groups.sh`. `[CLI]`
1.11.26 What Kafka is **not**: not a database, not a task queue with per-message delay/priority
      (until share groups), not a request-reply transport, and not free to operate.

## §1.12 RabbitMQ and AMQP — the essential model

1.12.1 **AMQP 0-9-1** as a wire-level protocol with a defined object model — the thing that makes
      RabbitMQ structurally different from both Kafka and SQS. `[SPEC]`
1.12.2 **Connection** (TCP) vs **channel** (a multiplexed logical session). Why you share
      connections and never share channels between threads. `[TRAP]`
1.12.3 **Exchange** — the router. Producers publish to an exchange, **never** to a queue.
      `[TRAP]`
1.12.4 The four exchange types: **direct**, **fanout**, **topic**, **headers**. The spec requires
      fanout and direct and recommends the other two. `[TABLE]` `[SPEC]`
1.12.5 The **default exchange** (`""`, a direct exchange with every queue bound by its own name)
      and why "publishing to a queue" appears to work.
1.12.6 **Binding** and **routing key**; topic wildcards `*` (one word) and `#` (zero or more).
      `[NUM]`
1.12.7 **Queue** — the only thing that stores messages, with `durable`, `exclusive`,
      `auto-delete` and `arguments` at declaration. Declaration is idempotent but **conflicting
      redeclaration fails the channel** with a 406 `PRECONDITION_FAILED`. `[TRAP]`
1.12.8 **Queue types** in RabbitMQ 4.x: **classic** (non-replicated), **quorum** (Raft-replicated),
      **stream** (append-only, offset-based). `x-queue-type` picks one. `[CFG]`
      `[VERSION-TRAP]`
1.12.9 **Classic mirrored queues are gone** (removed in 4.0). `ha-mode`, `ha-params`,
      `ha-sync-mode` are dead policy keys. `[VERSION-TRAP]`
1.12.10 **Message properties**: `delivery_mode` (1 transient / 2 persistent), `content_type`,
      `correlation_id`, `reply_to`, `message_id`, `timestamp`, `expiration`, `priority`, `headers`.
      `[TABLE]` `[SPEC]`
1.12.11 **Trap: persistent ≠ durable ≠ replicated.** `delivery_mode=2` on a non-durable queue, or a
      durable classic queue on a single node, still loses data on node loss. Three independent
      flags. `[TRAP]` `[PROVE]`
1.12.12 **Consumer acknowledgement**: `basic.ack`, `basic.nack` (with `multiple` and `requeue`),
      `basic.reject` (single message only). `[WIRE]` `[SPEC]`
1.12.13 **`basic.qos` prefetch** — the maximum number of unacknowledged deliveries on a channel;
      `0` means unlimited, and unlimited prefetch is how you OOM a consumer. Recommended 100–300.
      `global` flag (channel-wide vs per-consumer) — and quorum queues do **not** support global
      QoS. `[CFG]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.12.14 **Automatic requeue on channel/connection close** — every unacked delivery returns to the
      queue with `redelivered=true`. This is RabbitMQ's equivalent of the visibility timeout, and
      it is *event-driven*, not time-driven.
1.12.15 **`consumer_timeout`** (default 1800000 ms = 30 min) — a consumer that holds a delivery
      longer has its channel closed. The RabbitMQ analogue of `max.poll.interval.ms`.
      `[CFG]` `[NUM]` `[TRAP]`
1.12.16 **Publisher confirms** (`confirm.select` → `basic.ack` with a delivery tag, `multiple`
      flag, `basic.nack` on failure) as the producer durability mechanism. Confirmed only once
      every destination queue has accepted, which for persistent+durable means fsynced.
      `[WIRE]` `[SPEC]`
1.12.17 **Mandatory publish and `basic.return`** — the only way to learn a message matched no
      binding. Without it, an unroutable message is **silently discarded and still confirmed**.
      `[TRAP]` `[PROVE]`
1.12.18 **Alternate exchange** (`alternate-exchange`) as the declarative form of the same
      protection.
1.12.19 **Dead-letter exchange** — `x-dead-letter-exchange`, `x-dead-letter-routing-key`, and the
      four reasons a message dead-letters: `rejected`, `expired`, `maxlen`, `delivery_limit`. The
      `x-death` header array that records them. `[CFG]` `[TABLE]`
1.12.20 **`dead-letter-strategy`** — `at-most-once` (default) vs `at-least-once` on quorum queues,
      and the durability difference that name implies. `[CFG]` `[RESEARCH]`
1.12.21 **`x-delivery-limit`** (default **20** in RabbitMQ 4.x, `-1` disables) and the
      `x-delivery-count` header — the poison-message defence quorum queues have and classic queues
      historically did not. `[CFG]` `[NUM]` `[RESEARCH]`
1.12.22 **TTL** — `x-message-ttl` per queue, `expiration` per message, `x-expires` for the queue
      itself. Per-message TTL only expires from the **head** of a classic queue, which surprises
      people. `[TRAP]`
1.12.23 **Length limits and overflow**: `x-max-length`, `x-max-length-bytes`, `overflow` =
      `drop-head` | `reject-publish` | `reject-publish-dlx`. `[CFG]`
1.12.24 **Priority**: `x-max-priority` on classic queues; quorum queues in 4.x always support
      **32 levels (0–31)** and 4.3 adds strict priority with per-priority counts.
      `[NUM]` `[RESEARCH]`
1.12.25 **Single Active Consumer** (`x-single-active-consumer`) — ordering with a hot standby.
1.12.26 **Lazy queues**, and the fact that they are effectively the default behaviour in 4.x with
      CQv2 / quorum queues. `[VERSION-TRAP]`
1.12.27 **Policies** vs **queue arguments** — the operator-controlled versus the
      application-controlled surface, and why policies win for anything you might need to change
      without a deploy. `[CLI]`
1.12.28 **Virtual hosts**, users, permissions (`configure`/`write`/`read` regexes) and the
      management plugin / HTTP API.
1.12.29 **Memory and disk alarms** (`vm_memory_high_watermark`, `disk_free_limit`) blocking
      publishers — RabbitMQ's built-in backpressure, and the reason a "hung producer" is often a
      full disk. `[CFG]` `[DIAG]`
1.12.30 **Shovel** and **Federation** plugins for cross-cluster movement; 4.2 made Shovel
      cluster-aware and protocol-transparent. `[RESEARCH]`
1.12.31 **RabbitMQ Streams** — the log-shaped queue type, with offsets, non-destructive reads, a
      dedicated binary protocol, `x-stream-offset` consumer arguments, and 4.2's SQL filter
      expressions for AMQP 1.0 clients. `[RESEARCH]`
1.12.32 **AMQP 1.0** as a core always-on protocol since 4.0, with more than double the 3.13 peak
      throughput on some workloads — and the fact that AMQP 1.0 and 0-9-1 are entirely different
      protocols that share a name. `[TRAP]` `[RESEARCH]`
1.12.33 The CLI surface: `rabbitmqctl list_queues name messages messages_unacknowledged`,
      `rabbitmq-queues quorum_status`, `rabbitmqctl list_consumers`,
      `rabbitmq-diagnostics status`, `rabbitmqadmin` v2. `[CLI]` `[VERSION-TRAP]`

## §1.13 SQS, SNS and EventBridge — the essential model

1.13.1 **Standard queues** — nearly unlimited throughput, **at-least-once**, best-effort ordering
      (i.e. none). The default and the right choice most of the time.
1.13.2 **FIFO queues** — exactly-once *processing* within a 5-minute dedup window, strict ordering
      **within a message group id**. `.fifo` suffix required. `[NUM]`
1.13.3 FIFO throughput: 300 TPS per API action per partition without batching; 3,000 msg/s with
      10-message batches; high-throughput mode raising this to **70,000 TPS / 700,000 msg/s** in
      us-east-1, us-west-2 and eu-west-1, with lower regional tiers down to 2,400 TPS.
      `[NUM]` `[TABLE]` `[RESEARCH]`
1.13.4 **`MessageGroupId`** as the FIFO ordering unit — the direct analogue of a Kafka partition
      key. Required on FIFO; optional on standard, where it enables **fair queues**.
      `[VERSION-TRAP]` `[RESEARCH]`
1.13.5 **Fair queues** (2025) — SQS detects a tenant with a disproportionate share of in-flight
      messages and prioritises delivery for quiet tenants. No consumer change required. It is
      *not* ordering. `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
1.13.6 **`MessageDeduplicationId`** and content-based deduplication (SHA-256 of the body) with the
      **5-minute** window. `[NUM]`
1.13.7 **Visibility timeout — the core SQS mechanism.** Received ≠ deleted; the message becomes
      invisible for `VisibilityTimeout` (default **30 s**, min 0, max **12 hours**) and reappears
      if not deleted. `[CFG]` `[NUM]`
1.13.8 How visibility timeout gets at-least-once *without the broker tracking consumer liveness* —
      the elegance worth stating explicitly. `[PROVE]`
1.13.9 **Trap — the #1 SQS bug**: processing that outlives the visibility timeout causes a second
      consumer to start on the same message while the first is still working. Not merely a
      duplicate — two workers racing. Fix: set the timeout above p99.9 processing time and/or
      heartbeat with `ChangeMessageVisibility`. `[TRAP]`
1.13.10 **`ReceiptHandle`** — required to delete or change visibility, and **different on every
      receive** of the same message. Storing it and reusing a stale one fails. `[TRAP]`
1.13.11 **`maxReceiveCount`** in the redrive policy — exactly the "N" from §1.5.
1.13.12 **Redrive allow policy** — `allowAll` (default), `byQueue` (up to 10 source ARNs),
      `denyAll`. `[CFG]` `[NUM]` `[RESEARCH]`
1.13.13 **Long polling** — `WaitTimeSeconds` up to **20**. Short polling samples a subset of
      servers and can return empty even when messages exist, and it burns API calls (money).
      Always use long polling. `[CFG]` `[NUM]` `[TRAP]`
1.13.14 **Batching** — `SendMessageBatch` / `ReceiveMessage(MaxNumberOfMessages)` /
      `DeleteMessageBatch`, up to **10** messages, a 10× cost and throughput improvement.
      `[NUM]`
1.13.15 **Partial batch failure** — `ReportBatchItemFailures` (Lambda) or per-entry results, or you
      will redeliver the whole batch. `[TRAP]`
1.13.16 **Message size 1 MiB** (1,048,576 bytes), min 1 byte; the Extended Client Library for S3
      offload up to 2 GB. `[NUM]` `[VERSION-TRAP]`
1.13.17 **Message attributes** — up to **10** metadata attributes, counted against the size limit;
      plus system attributes (`AWSTraceHeader`). `[NUM]`
1.13.18 **In-flight limit — 120,000** for both standard and FIFO queues; `OverLimit` error;
      `ApproximateNumberOfMessagesNotVisible` is the metric. `[NUM]` `[VERSION-TRAP]` `[METRIC]`
1.13.19 **Delay queues** (`DelaySeconds`, queue-level) and **message timers** (per-message), 0–900
      seconds. Not supported per-message on FIFO. `[NUM]`
1.13.20 **Retention**: `MessageRetentionPeriod` default 345600 s (4 days), min 60 s, max 1209600 s
      (14 days). `[NUM]` `[VERSION-TRAP]`
1.13.21 The CloudWatch metric set: `ApproximateNumberOfMessagesVisible`,
      `…NotVisible`, `…Delayed`, `ApproximateAgeOfOldestMessage`, `NumberOfMessagesSent/Received/
      Deleted`, `NumberOfEmptyReceives`, `SentMessageSize`. What each one tells you.
      `[METRIC]` `[TABLE]`
1.13.22 **SQS has no replay and no fan-out of its own.** Pair with SNS or EventBridge.
1.13.23 **SNS** — topics, subscriptions (SQS, Lambda, HTTP/S, email, SMS, Kinesis Firehose),
      **up to 100 subscriptions** in the default fan-out framing, **raw message delivery**
      (`RawMessageDelivery=true`) to strip the SNS JSON envelope, **subscription filter policies**
      on attributes or body, **delivery retry policies**, and **SNS DLQ per subscription**.
      `[NUM]` `[TABLE]` `[RESEARCH]`
1.13.24 **SNS FIFO topics** — FIFO in, FIFO or standard SQS out (since 2023), plus **in-place
      message archiving and replay** via an archive policy on the topic and a replay policy on the
      subscription. This is the closest AWS gets to Kafka replay without Kinesis.
      `[VERSION-TRAP]` `[RESEARCH]`
1.13.25 **The SNS→SQS fan-out pattern** as the canonical AWS architecture, and the IAM/queue-policy
      detail that makes it work. `[X-REF 18]`
1.13.26 **EventBridge** — event buses, rules with content-based patterns, targets, archive and
      replay, schema registry, and **Pipes** (source → filter → enrich → target). Where it beats
      SNS and where it is slower.
1.13.27 **Kinesis Data Streams** as AWS's log: shards, sequence numbers, 24 h to 365 d retention,
      enhanced fan-out, and its 2 MB/s per-shard read limit — the reason people reach for MSK
      instead. `[NUM]` `[X-REF 18]`
1.13.28 **Amazon MQ** (managed RabbitMQ/ActiveMQ) and **MSK / MSK Serverless** as the managed
      escapes, and the operational-load argument for each. `[X-REF 18]`
1.13.29 What SQS is **not**: not ordered (standard), not replayable, not a log, not able to fan out,
      and not free of the per-request cost that batching exists to amortise.

## §1.14 JMS / Jakarta Messaging — the API layer, not a broker

1.14.1 What JMS is: a **Java API specification**, not a wire protocol and not a broker. Two
      providers that both implement JMS still cannot talk to each other. `[TRAP]`
1.14.2 The rename: `javax.jms` → **`jakarta.jms`** at Jakarta Messaging 3.0, with 3.1 (March 2022)
      pruning the long-optional chapters. `[VERSION-TRAP]`
1.14.3 The classic object model: `ConnectionFactory`, `Connection`, `Session`, `Destination`
      (`Queue` / `Topic`), `MessageProducer`, `MessageConsumer`. `[API]`
1.14.4 The simplified 2.0+ model: `JMSContext`, `JMSProducer`, `JMSConsumer`, and
      `try (JMSContext ctx = cf.createContext())`. `[API]`
1.14.5 The six message types: `TextMessage`, `BytesMessage`, `MapMessage`, `StreamMessage`,
      `ObjectMessage`, and the bare `Message`. Why `ObjectMessage` is a deserialisation
      vulnerability. `[TRAP]` `[X-REF 13]`
1.14.6 The four acknowledgement modes: `AUTO_ACKNOWLEDGE`, `CLIENT_ACKNOWLEDGE`,
      `DUPS_OK_ACKNOWLEDGE`, and `SESSION_TRANSACTED`. Each maps directly onto §1.6.
      `[TABLE]` `[API]`
1.14.7 **`Message.acknowledge()` acknowledges every message consumed on that session**, not just
      the one you called it on. `[TRAP]` `[SPEC]`
1.14.8 **Durable subscriptions** (`createDurableConsumer`) vs non-durable, and the client-id +
      subscription-name identity that makes them resumable.
1.14.9 **Shared subscriptions** (`createSharedConsumer` / `createSharedDurableConsumer`, JMS 2.0+)
      — competing consumers on a topic, which is the JMS spelling of a Kafka consumer group.
      `[API]` `[RESEARCH]`
1.14.10 **Message selectors** — a SQL-92-like predicate over headers and properties, evaluated
      broker-side.
1.14.11 **`JMSRedelivered`**, `JMSXDeliveryCount`, `JMSPriority` (0–9), `JMSExpiration`,
      `JMSCorrelationID`, `JMSReplyTo`. `[API]` `[NUM]`
1.14.12 **Delivery delay** (`setDeliveryDelay`) and **asynchronous send** with
      `CompletionListener`, both added in 2.0. `[API]` `[RESEARCH]`
1.14.13 `@JmsListener`, `JmsTemplate`, `DefaultJmsListenerContainerFactory` and
      `JmsMessagingTemplate` as the Spring surface. `[API]`
1.14.14 Why JMS matters to a Kafka engineer at all: it is the vocabulary older systems and older
      interviewers use, and ActiveMQ Artemis / IBM MQ / Amazon MQ are all still in production.
1.14.15 The mapping table: JMS concept → Kafka concept → AMQP concept → SQS concept.
      `[TABLE]`

## §1.15 Message anatomy, serialisation and schema

1.15.1 The parts of a message everywhere: **key**, **body/payload**, **headers/attributes/
      properties**, **metadata the broker adds**.
1.15.2 What belongs in a header and what belongs in the body: routing, tracing, schema id, event
      id, content type, and the version → headers. Business data → body. `[TABLE]`
1.15.3 The header set every event in QuizStakes should carry: `eventId`, `eventType`,
      `eventVersion`, `occurredAt`, `producer`, `correlationId`, `causationId`, `partitionKey`,
      `schemaId`, `contentType`. `[TABLE]`
1.15.4 **`correlationId` vs `causationId` vs `traceparent`** — three different identity questions.
      `[X-REF 20]`
1.15.5 Serialisation formats: JSON, Avro, Protobuf, Thrift, MessagePack, CBOR, plain bytes.
      Size, speed, schema support, human readability and tooling. `[TABLE]`
1.15.6 Why JSON is the default and why it stops being the default: no schema enforcement, no
      compact encoding, 3–10× the bytes of Avro for the same record, and no compile-time contract.
      `[NUM]`
1.15.7 **Avro** — writer schema vs reader schema, schema resolution, defaults, unions, logical
      types, and the 5-byte Confluent wire format (magic byte `0x00` + 4-byte schema id).
      `[WIRE]` `[NUM]`
1.15.8 **Protobuf** — field numbers as the contract, `optional`/`repeated`, reserved ranges, and
      why renaming a field is safe but renumbering is not. `[X-REF 12]`
1.15.9 **Schema Registry** — subject naming strategies (`TopicNameStrategy`,
      `RecordNameStrategy`, `TopicRecordNameStrategy`) and the seven compatibility modes:
      `BACKWARD` (default), `BACKWARD_TRANSITIVE`, `FORWARD`, `FORWARD_TRANSITIVE`, `FULL`,
      `FULL_TRANSITIVE`, `NONE`. `[TABLE]` `[RESEARCH]`
1.15.10 What each compatibility mode permits, and the upgrade-order consequence: `BACKWARD` means
      consumers upgrade first, `FORWARD` means producers upgrade first. `[PROVE]` `[RESEARCH]`
1.15.11 The safe-change list for an event schema: add an optional field with a default, never
      change a type, never reuse a field name with a new meaning, never make an optional field
      required. `[TABLE]`
1.15.12 **Trap: `spring.json.trusted.packages`.** Spring's `JsonDeserializer` will refuse types
      outside the trusted list, and setting it to `*` re-opens a deserialisation attack surface.
      `[TRAP]` `[API]` `[X-REF 13]`
1.15.13 **Trap: type headers coupling producer and consumer.** `__TypeId__` written by
      `JsonSerializer` makes the consumer need the producer's class name. `JsonMessageConverter`
      with an explicit `setTypeMapper` or `useTypeHeaders(false)` is the fix. `[TRAP]` `[API]`
1.15.14 **`ErrorHandlingDeserializer`** — the only correct way to survive a poison record at
      deserialisation time, because a throw inside the deserialiser happens before your listener
      is ever called and the container will spin forever. `[TRAP]` `[API]`
1.15.15 Compression: `compression.type` (`none`, `gzip`, `snappy`, `lz4`, `zstd`), where it
      happens (producer batch), what it costs, and the broker-side recompression trap when the
      broker's `compression.type` differs. `[CFG]` `[TABLE]`
1.15.16 **Trap: `max.request.size` is checked before compression** on the client, so a record that
      would compress under the limit is still rejected. And librdkafka silently drops the
      compressed batch if it came out larger than the original. `[TRAP]` `[RESEARCH]`
1.15.17 Message size limits that must line up: producer `max.request.size` (1048576), broker
      `message.max.bytes` (1048588), topic `max.message.bytes`, consumer `fetch.max.bytes`
      (57671680) and `max.partition.fetch.bytes` (1048576). A mismatch produces
      `RecordTooLargeException` at one layer and a stuck consumer at another. `[CFG]` `[NUM]`
      `[TRAP]`
1.15.18 Payload design: event-carried state transfer vs thin event with a callback. The trade
      between coupling and chattiness, worked against `PaymentStatusChanged`.
1.15.19 The **claim check** for the 2–6 MB document images: object storage + a reference, because
      even 1 MiB does not fit them. `[NUM]`
1.15.20 PII in messages — the retention conflict (7-year transaction retention vs right to erasure)
      and why you put a reference to `PersonalDetails`, never the values, on the bus.
      `[X-REF 13]`

## §1.16 The Spring listener surface, at first contact

1.16.1 `@KafkaListener` — `topics`, `groupId`, `containerFactory`, `concurrency`, `id`,
      `errorHandler`, `filter`. `[API]`
1.16.2 `ConcurrentMessageListenerContainer` and what `concurrency=N` actually creates: N
      `KafkaMessageListenerContainer`s, each with its own consumer and its own thread. Setting it
      above the partition count creates idle containers. `[API]` `[TRAP]`
1.16.3 `KafkaTemplate` — `send`, `send` returning `CompletableFuture<SendResult<K,V>>`,
      `sendDefault`, `executeInTransaction`, `setObservationEnabled`. `[API]`
1.16.4 `AckMode` — `RECORD`, `BATCH` (default), `TIME`, `COUNT`, `COUNT_TIME`, `MANUAL`,
      `MANUAL_IMMEDIATE` — the single knob that sets your delivery semantics in Spring.
      `[API]` `[TABLE]` `[TRAP]`
1.16.5 `Acknowledgment.acknowledge()` and `nack(Duration)` under `MANUAL_IMMEDIATE`. `[API]`
1.16.6 `DefaultErrorHandler` (which replaced `SeekToCurrentErrorHandler`), its default
      `FixedBackOff(0L, 9L)`, `addNotRetryableExceptions`, `setBackOffFunction`, and the
      `DeadLetterPublishingRecoverer` it recovers into. `[API]` `[NUM]` `[VERSION-TRAP]`
1.16.7 `@RetryableTopic` / `RetryTopicConfiguration` — non-blocking retries via generated retry
      topics with suffixes, `attempts`, `backOff` (renamed from `backoff` in 4.0), `dltStrategy`,
      `SameIntervalTopicReuseStrategy`, `fixedDelayTopicStrategy`. Not supported with batch
      listeners or container transactions. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.16.8 `CommonErrorHandler`, `RecordInterceptor`, `BatchInterceptor`,
      `ConsumerAwareRebalanceListener`. `[API]`
1.16.9 `@RabbitListener`, `RabbitTemplate`, `SimpleMessageListenerContainer` vs
      `DirectMessageListenerContainer`, `AcknowledgeMode` (`NONE`/`MANUAL`/`AUTO`),
      `prefetchCount`, `RepublishMessageRecoverer`. `[API]`
1.16.10 The new `spring-rabbitmq-client` AMQP 1.0 module: `RabbitAmqpTemplate`,
      `RabbitAmqpListenerContainer`, `RabbitAmqpMessageListenerAdapter`, `RabbitAmqpAdmin`, and
      the Boot starter split (`spring-boot-starter-rabbitmq` for 0-9-1 versus
      `spring-boot-starter-amqp-rabbitmq` for 1.0). `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.16.11 `@SqsListener` (Spring Cloud AWS) — `pollTimeoutSeconds`, `maxConcurrentMessages`,
      `messageVisibility`, `acknowledgementMode`, and the batch listener form. `[API]`
1.16.12 Spring Cloud Stream's binder abstraction, its `Supplier`/`Function`/`Consumer` binding
      model, and the honest assessment of when the abstraction earns its cost.
1.16.13 `@TransactionalEventListener(phase = AFTER_COMMIT)` — the tempting near-miss for the
      dual-write problem, and exactly why it does not solve it. `[TRAP]` `[X-REF 07]`
1.16.14 `KafkaTransactionManager`, container `transactionManager`, and the removal of
      `ChainedKafkaTransactionManager` — what to do instead. `[API]` `[VERSION-TRAP]`
1.16.15 `EmbeddedKafkaKraftBroker` / `@EmbeddedKafka` (ZooKeeper attributes removed in Spring Kafka
      4.0) and Testcontainers as the two testing substrates. `[API]` `[X-REF 16]`
1.16.16 Micrometer integration: `setObservationEnabled(true)`, `KafkaTemplate.Observation`,
      `spring.kafka.template.observation-enabled`, and the `kafka.consumer.fetch.manager.*` meter
      set. `[METRIC]` `[X-REF 20]`

---

# PART 2 — INTERMEDIATE

## §2.1 The master comparison and the selection procedure

2.1.1 **The master guarantee-and-cost table** — one row per system (Kafka topic, Kafka share
      group, RabbitMQ classic, RabbitMQ quorum, RabbitMQ stream, SQS standard, SQS FIFO, SNS,
      EventBridge, Kinesis, JMS/ActiveMQ Artemis), one column per property: delivery guarantee,
      ordering unit, position ownership, replay, fan-out, per-message retry, per-message delay,
      priority, max message size, throughput ceiling, latency floor, operational load, cost shape.
      `[TABLE]` `[NUM]`
2.1.2 The selection procedure as an ordered set of questions, not a preference: (1) does a second
      consumer need this later? (2) do you need replay? (3) do you need per-key ordering? (4) do
      you need per-message delay/priority/retry? (5) what is your ops budget? (6) what is the peak
      rate and the p99 latency requirement? `[FLOW]`
2.1.3 The three answers that are almost always right for a mid-size backend: SQS+SNS for tasks,
      Kafka for events, and *no broker at all* for anything the caller must wait on.
2.1.4 The anti-pattern catalogue: a broker used as an RPC transport, a broker used as a database,
      a broker used to hide a synchronous dependency, and one topic per consumer.
      `[TABLE]` `[TRAP]`
2.1.5 The "one topic or many" decision: one topic per event type, per aggregate, or per bounded
      context — and the ordering consequence of each. Worked against QuizStakes' 21 events.
2.1.6 Topic/queue naming conventions that survive: `<domain>.<aggregate>.<event>.<version>`,
      lowercase, dot-separated, with the retry/DLT suffix convention stated. Kafka's
      `.`-versus-`_` metric-name collision as the reason not to mix them. `[TRAP]`
2.1.7 Multi-tenancy: one topic with a tenant key, one topic per tenant, or one cluster per tenant.
      The partition-count arithmetic that kills option two at scale. `[NUM]`
2.1.8 The QuizStakes worked selection: domain events → Kafka (log, client-id key); bank file
      records → SQS (task, competing consumers, per-message retry); PSP webhooks → SQS after HTTP
      ingest; `PaymentRun` trigger → scheduler + lock, **not** a queue; restriction decisions →
      synchronous HTTP, never messaging. `[TABLE]`

## §2.2 Kafka producer configuration, in depth

2.2.1 `bootstrap.servers` and what actually happens on first connect (metadata request, then
      direct leader connections). Why listing one broker is legal but fragile. `[CFG]`
2.2.2 `acks` = `0` | `1` | `all` (`-1`) and the exact failure each admits. `[CFG]` `[TABLE]`
2.2.3 `enable.idempotence` — default **true** since 3.0 — and the constraint set it enforces.
      `[CFG]` `[VERSION-TRAP]`
2.2.4 `retries` (default `Integer.MAX_VALUE`) and why it is *not* the retry limit that matters —
      `delivery.timeout.ms` (default 120000) is. `[CFG]` `[NUM]` `[TRAP]`
2.2.5 The timeout relationship that must hold: `delivery.timeout.ms >= request.timeout.ms +
      linger.ms`. `[CFG]` `[PROVE]`
2.2.6 `request.timeout.ms` (30000), `max.block.ms` (60000), `metadata.max.age.ms` (300000).
      `[CFG]` `[NUM]`
2.2.7 `batch.size` (16384 bytes) and `linger.ms` (**5** since Kafka 4.0, previously 0) as the two
      halves of "send when full or when bored". `[CFG]` `[NUM]` `[VERSION-TRAP]`
2.2.8 The batching arithmetic: at 40 card deposits/sec with 400-byte events, a 16 KB batch never
      fills, so `linger.ms` is the only thing that batches at all — and at 1,200 stake events/sec
      it fills in ~34 ms. Two very different regimes on one cluster. `[NUM]` `[PROVE]`
2.2.9 `buffer.memory` (33554432 = 32 MB) and `BufferExhaustedException` / the `max.block.ms` stall
      as the producer's backpressure mechanism. `[CFG]` `[NUM]`
2.2.10 `max.in.flight.requests.per.connection` (5) and its interaction with ordering and
      idempotence. `[CFG]` `[NUM]`
2.2.11 `compression.type` (`none` default on the producer; `producer` on the broker) and the
      trade table for gzip/snappy/lz4/zstd. `[CFG]` `[TABLE]`
2.2.12 `partitioner.class`, the default partitioner's behaviour with and without a key, and the
      **sticky partitioner** (KIP-480) that replaced round-robin for null keys —
      `partitioner.adaptive.partitioning.enable` and `partitioner.availability.timeout.ms`, with
      the misspelled `PARTITIONER_ADPATIVE_PARTITIONING_ENABLE` constant deprecated in 4.2.
      `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
2.2.13 A custom partitioner for the whale-client problem, and why you almost always regret one.
2.2.14 `client.id` — why setting it is not optional if you ever want to read a metric or a quota
      log line. `[METRIC]`
2.2.15 `transactional.id`, `transaction.timeout.ms` (60000) and `enable.idempotence` as the
      transaction prerequisites. `[CFG]` `[NUM]`
2.2.16 `interceptor.classes` and the `ProducerInterceptor` hook (tracing, auditing, PII scrubbing).
      `[API]`
2.2.17 Callback vs `Future.get()` vs fire-and-forget as the three send styles, with the
      throughput/latency/correctness consequence of each. `[BUILD]` `[TABLE]`
2.2.18 **Trap: `send()` does not throw on broker failure.** It returns a future and calls your
      callback. Ignoring both is how a "durable" pipeline silently drops. `[TRAP]`
2.2.19 **Trap: `flush()` from inside a send callback deadlocks** — Kafka 4.1 added explicit
      protection, but the pattern is still wrong. `[TRAP]` `[RESEARCH]`
2.2.20 Producer thread-safety: one `KafkaProducer` is thread-safe and should be shared; one per
      request is a resource leak and destroys batching. `[TRAP]`
2.2.21 The producer metric set worth alerting on: `record-error-rate`, `record-retry-rate`,
      `request-latency-avg`, `buffer-available-bytes`, `batch-size-avg`,
      `records-per-request-avg`, `compression-rate-avg`. `[METRIC]` `[TABLE]`
2.2.22 A production-grade `ProducerConfig` for `FundsLedger`'s `LedgerMovementPosted` at 230/sec
      sustained and 13,600/sec peak, every value justified. `[BUILD]` `[NUM]`

## §2.3 Kafka consumer configuration, in depth

2.3.1 `group.id`, `client.id`, `group.instance.id` (static membership, KIP-345) and what static
      membership buys during a rolling restart. `[CFG]`
2.3.2 `group.protocol` = `classic` | `consumer`, and the exact set of configs that becomes inert
      under `consumer`. `[CFG]` `[VERSION-TRAP]`
2.3.3 `auto.offset.reset` = `earliest` | `latest` | `none`, and when each one is applied (only
      when there is no committed offset, or the committed offset is out of range). `[CFG]`
2.3.4 **Trap: `auto.offset.reset` is not "where I start".** It is the fallback when the offset is
      missing or invalid, and combined with `offsets.retention.minutes` expiry it becomes a silent
      data-loss or full-replay event. `[TRAP]` `[PROVE]`
2.3.5 `enable.auto.commit` (true) and `auto.commit.interval.ms` (5000), and the precise reason
      auto-commit is at-most-once-ish. `[CFG]` `[NUM]` `[TRAP]`
2.3.6 `commitSync` vs `commitAsync` vs the "async in the loop, sync in `finally`" idiom.
      `[BUILD]` `[API]`
2.3.7 **Committed offset semantics: you commit the offset of the *next* record to read, not the
      last one processed.** Off-by-one here reprocesses or skips exactly one record per commit.
      `[TRAP]` `[PROVE]`
2.3.8 `max.poll.records` (500) and `max.poll.interval.ms` (300000) as the pair that decides
      whether you get evicted. The arithmetic: 500 records × 40 ms each = 20 s, comfortably inside
      300 s — but 500 × 700 ms is 350 s and you are out. `[CFG]` `[NUM]` `[PROVE]`
2.3.9 `fetch.min.bytes` (1), `fetch.max.wait.ms` (500), `fetch.max.bytes` (57671680),
      `max.partition.fetch.bytes` (1048576) as the fetch-shaping set. `[CFG]` `[NUM]`
2.3.10 The latency-versus-efficiency trade of `fetch.min.bytes`: raising it batches better and
      costs up to `fetch.max.wait.ms` of latency. `[PROVE]`
2.3.11 `session.timeout.ms` (45000) and `heartbeat.interval.ms` (3000) under the classic protocol;
      the rule `heartbeat.interval.ms ≈ session.timeout.ms / 3`. `[CFG]` `[NUM]`
      `[VERSION-TRAP]`
2.3.12 `partition.assignment.strategy`: `RangeAssignor` (the historical default and its skew
      problem), `RoundRobinAssignor`, `StickyAssignor`, `CooperativeStickyAssignor`. Server-side
      `uniform` and `range` under KIP-848. `[CFG]` `[TABLE]` `[VERSION-TRAP]`
2.3.13 `isolation.level` = `read_uncommitted` (default) | `read_committed`, and the **Last Stable
      Offset** that `read_committed` consumers cannot advance past. `[CFG]` `[TRAP]`
2.3.14 `ConsumerRebalanceListener` — `onPartitionsRevoked` (commit here), `onPartitionsAssigned`,
      `onPartitionsLost` (do not commit here). `[API]` `[TRAP]`
2.3.15 `seek`, `seekToBeginning`, `seekToEnd`, `offsetsForTimes` — programmatic replay, and
      Spring's `ConsumerSeekAware`. `[API]`
2.3.16 `pause` / `resume` as the correct way to slow down without being evicted, and Spring's
      container `pause()` / `isPauseRequested()`. `[API]`
2.3.17 `assign()` (manual partition assignment, no group management, no rebalancing) versus
      `subscribe()` — and when manual assignment is the right answer. `[API]`
2.3.18 Consumer thread-safety: `KafkaConsumer` is **not** thread-safe; the only legal cross-thread
      call is `wakeup()`. `[TRAP]` `[API]`
2.3.19 The two concurrency models: one consumer per thread (Kafka's recommendation) versus one
      consumer feeding a worker pool (which you must pair with pause/resume and which destroys
      ordering). `[TABLE]` `[TRAP]`
2.3.20 The consumer metric set: `records-lag-max`, `records-lead-min`, `fetch-latency-avg`,
      `commit-latency-avg`, `rebalance-rate-per-hour`, `failed-rebalance-rate-per-hour`,
      `last-rebalance-seconds-ago`, `time-between-poll-avg/max`. `[METRIC]` `[TABLE]`
2.3.21 A production-grade `ConsumerConfig` for the `LedgerMovementPosted` reconciliation consumer,
      every value justified against the 150 ms stake budget and the 3,400/sec settlement burst.
      `[BUILD]` `[NUM]`

## §2.4 Consumer groups, rebalancing and scaling

2.4.1 What the group coordinator is, which broker hosts it (`hash(group.id) %
      offsets.topic.num.partitions`, then that partition's leader), and why that matters when a
      broker dies. `[PROVE]` `[NUM]`
2.4.2 The classic protocol as a five-phase dance: `FindCoordinator` → `JoinGroup` (the leader is
      elected) → the leader computes the assignment client-side → `SyncGroup` → `Heartbeat`.
      `[FLOW]` `[WIRE]`
2.4.3 Why the classic protocol is "stop the world": the global synchronisation barrier at
      `SyncGroup` means nobody consumes until everybody has rejoined. `[PROVE]`
2.4.4 **Eager** rebalancing (revoke everything, then reassign) vs **incremental cooperative**
      rebalancing (KIP-429: revoke only what moves, in two rounds). `[TABLE]`
2.4.5 The KIP-848 protocol: the **coordinator computes the assignment**, members reconcile
      incrementally via a heartbeat-carried target assignment, and there is no barrier at all.
      `[FLOW]` `[RESEARCH]`
2.4.6 The new server-side knobs: `group.consumer.session.timeout.ms`,
      `group.consumer.heartbeat.interval.ms`, `group.consumer.assignors` (default `uniform,range`),
      `group.consumer.max.size`, and the client's `group.remote.assignor`. `[CFG]` `[RESEARCH]`
2.4.7 The migration path: online rolling upgrade by setting `group.protocol=consumer` per instance;
      the group converts when the first new-protocol member joins and converts back when the last
      one leaves. Offline upgrade as the alternative. `[FLOW]` `[RESEARCH]`
2.4.8 What KIP-848 still does not support: client-side assignors and full rack-aware assignment.
      `[RESEARCH]`
2.4.9 **Static membership** (`group.instance.id`) — the consumer keeps its assignment across a
      restart within `session.timeout.ms`, so a rolling deploy causes zero rebalances. The cost:
      a genuinely dead instance is not detected until the timeout. `[CFG]` `[TRAP]`
2.4.10 The rebalance storm: N instances restarting one at a time causes N rebalances, each
      revoking everything. The arithmetic for a 20-instance deploy. `[NUM]` `[PROVE]`
2.4.11 Scaling out: add instances up to the partition count. Scaling up: raise `max.poll.records`,
      batch the downstream write, or parallelise inside the record. `[TABLE]`
2.4.12 Partition-count planning arithmetic: target throughput ÷ per-consumer throughput, with
      headroom for the peak and for the future, bounded by the per-broker partition limit and the
      rebalance cost. Worked for the 3,400/sec settlement burst. `[NUM]` `[PROVE]`
2.4.13 The cost of too many partitions: more open file handles, more replication fetches, longer
      controller failover, longer rebalances, more end-to-end latency. `[TABLE]`
2.4.14 `kafka-consumer-groups.sh --describe --group` output read column by column: `TOPIC`,
      `PARTITION`, `CURRENT-OFFSET`, `LOG-END-OFFSET`, `LAG`, `CONSUMER-ID`, `HOST`, `CLIENT-ID`.
      `[CLI]` `[DIAG]`
2.4.15 Reading a rebalance from the logs: `Attempt to heartbeat failed since group is rebalancing`,
      `Revoke previously assigned partitions`, `CommitFailedException`, `Member … sending
      LeaveGroup request`. `[DIAG]`
2.4.16 Consumer group states: `Empty`, `PreparingRebalance`, `CompletingRebalance`, `Stable`,
      `Dead`, and (share groups) `Assigning`. `[TABLE]`
2.4.17 The four ways a consumer group ends up consuming nothing while looking healthy: rebalance
      loop, `read_committed` blocked at the LSO, a paused container, and an assignment of zero
      partitions. `[TABLE]` `[TRAP]`
2.4.18 Draining a consumer correctly on shutdown: `wakeup()`, commit in `onPartitionsRevoked`,
      close with a timeout, and `Consumer.close(CloseOptions)` / `GroupMembershipOperation` in
      4.1+ to control whether a `LeaveGroup` is sent. `[API]` `[RESEARCH]`
2.4.19 Why sending `LeaveGroup` on a rolling deploy is often the wrong choice, and static
      membership is the right one.
2.4.20 **Share groups as the escape from the partition ceiling**: `group.type=share`, more
      consumers than partitions, per-record acquisition and acknowledgement, `share.delivery.limit`
      and record-lock configs added by KIP-1240 in 4.3, and the ordering you give up in exchange.
      `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`

## §2.5 Partitioning and key design

2.5.1 The three jobs a partition key does at once: routing, ordering, and load distribution. They
      conflict. `[PROVE]`
2.5.2 `murmur2(keyBytes) & 0x7fffffff % numPartitions` as the exact default mapping, and the fact
      that it is a client-side decision the broker never validates. `[SOURCE]` `[NUM]`
2.5.3 Why adding partitions breaks the mapping, worked with real numbers: key `K` at
      `hash % 12 = 7` moves to `hash % 24 = 19`, so its history is in one partition and its future
      in another. `[PROVE]` `[NUM]`
2.5.4 The safe ways to add capacity: over-provision at creation, create a new topic and
      dual-write, or accept a re-key migration window with the producer stopped. `[TABLE]`
2.5.5 Null key behaviour: sticky partitioner batching, not round-robin per record. What that means
      for even distribution at low rates. `[VERSION-TRAP]`
2.5.6 Key cardinality arithmetic: 2.4M clients across 24 partitions averages 100k clients per
      partition, but the top client's share is what actually matters. `[NUM]`
2.5.7 Hot-partition detection: per-partition lag, per-partition bytes-in, and the
      `kafka.log:type=Log,name=Size` MBean. `[METRIC]`
2.5.8 Composite keys with a bucket suffix as the standard mitigation, and the exact ordering
      guarantee you retain (per client-bucket, not per client). `[PROVE]`
2.5.9 The "route the whale to a dedicated topic" mitigation and its operational cost.
2.5.10 Time-based keys as the anti-pattern that puts all of today on one partition. `[TRAP]`
2.5.11 SQS `MessageGroupId` cardinality: the same argument, with the additional twist that fair
      queues actively penalise the hot group rather than starving the others.
      `[VERSION-TRAP]`
2.5.12 RabbitMQ's answer — **consistent hash exchange**, **sharding plugin**, and (4.3) the
      `x-modulus-hash` exchange type promoted into core. `[RESEARCH]`
2.5.13 Rack awareness: `broker.rack`, `client.rack`, `RackAwareReplicaSelector`, and the
      cross-AZ data-transfer bill that motivates them. `[CFG]` `[X-REF 18]`

## §2.6 Retry topology design

2.6.1 The four places a retry can live: in the handler, in the container, in the broker, in a
      separate topic/queue. `[TABLE]`
2.6.2 **Blocking retry** — `DefaultErrorHandler` with a `BackOff`, holding the consumer thread and
      the partition. Correct only for sub-second, small-attempt-count retries. `[API]`
2.6.3 **Non-blocking retry** — the retry-topic chain, with the partition freed immediately.
      `@RetryableTopic` generating `-retry-0`, `-retry-1`, … `-dlt` suffixed topics. `[API]`
2.6.4 How the delay is actually enforced in a retry topic: the consumer reads the record, sees
      that its due-time header has not arrived, and **pauses the partition** until it has.
      Spring throws `KafkaBackOffException` and seeks. `[PROVE]` `[API]`
2.6.5 `SameIntervalTopicReuseStrategy` and `fixedDelayTopicStrategy` — why N attempts do not
      necessarily need N topics. `[API]` `[RESEARCH]`
2.6.6 The SQS retry topology: visibility timeout as the delay, `maxReceiveCount` as the attempt
      budget, and `ChangeMessageVisibility` with an exponential value as the per-message backoff.
      `[BUILD]`
2.6.7 The RabbitMQ retry topologies, all three: `basic.nack(requeue=true)` (immediate, hot loop),
      a TTL'd wait queue with a DLX pointing back at the work queue (the classic delayed-retry
      trick), and 4.3's native `x-delayed-retry-type` / `x-delayed-retry-min` /
      `x-delayed-retry-max`. `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
2.6.8 Combining blocking and non-blocking retries in Spring, and the attempt-count multiplication
      that surprises people (3 blocking × 4 topics = 12 attempts). `[NUM]` `[TRAP]`
2.6.9 The retry budget as a capacity decision: at 1,200 msg/s with 10% failing and 5 retries each,
      the retry path carries 600 msg/s of extra load. Provision for it. `[NUM]` `[PROVE]`
2.6.10 Deciding the attempt count from the dependency profile rather than by habit: the PSP capture
      at p99 6 s and a 10 s timeout supports maybe 3 attempts inside the 4 s deposit budget — which
      is to say the retry must be asynchronous. `[NUM]`
2.6.11 Retry with a **deadline** rather than an attempt count, and why that is usually the better
      contract.
2.6.12 Where the DLQ sits in each topology, and the "confirm the DLQ write before acking" rule
      restated in each. `[TRAP]`
2.6.13 The replay tool's contract: read the DLQ, re-key, republish to the original topic, record
      what was replayed, and be safely re-runnable. `[BUILD]`

## §2.7 Kafka transactions and the true scope of EOS

2.7.1 What a Kafka transaction actually covers: writes to multiple topic-partitions **plus** the
      offset commit, atomically. `[PROVE]`
2.7.2 The API: `initTransactions`, `beginTransaction`, `send`, `sendOffsetsToTransaction`,
      `commitTransaction`, `abortTransaction`. `[API]`
2.7.3 `transactional.id` as the fencing identity, and why it must be **stable across restarts** and
      **unique per producer instance** — the two requirements that conflict under autoscaling.
      `[TRAP]` `[PROVE]`
2.7.4 `isolation.level=read_committed` on the consumer as the other half; without it, the reader
      sees aborted records. `[CFG]`
2.7.5 **Control records** (commit and abort markers) written into the partitions, consuming offsets
      that contain no data — which is why offsets can skip. `[TRAP]` `[WIRE]`
2.7.6 **Last Stable Offset (LSO)** — a `read_committed` consumer cannot advance past the earliest
      open transaction, so **one hung transaction stalls every reader of that partition**.
      `[PROVE]` `[TRAP]` `[RESEARCH]`
2.7.7 `transaction.timeout.ms` (60000) versus the broker's
      `transaction.max.timeout.ms` (900000), and how a hung transaction resolves.
      `[CFG]` `[NUM]`
2.7.8 The consume-transform-produce loop as the *only* pattern EOS was designed for, written out
      in full. `[BUILD]` `[FLOW]`
2.7.9 **The boundary: EOS covers Kafka-to-Kafka only.** A DB write, an email, an S3 put or a PSP
      call inside the transaction is not covered and will be re-executed on abort-and-retry.
      `[PROVE]` `[TRAP]`
2.7.10 KIP-98 (the original transactions), KIP-447 (`sendOffsetsToTransaction` with the consumer
      group metadata, enabling one producer per thread instead of one per partition), KIP-890
      (server-side defence against hanging transactions, identifying a transaction by
      `{producerId, epoch}`), KIP-939 (participation in an external 2PC). `[RESEARCH]`
2.7.11 **KIP-939 as the thing that changes the outbox answer** — Kafka can now be a participant
      whose fate an external coordinator decides, which makes an atomic DB+Kafka dual write
      technically possible for the first time. State clearly that it is not the default answer and
      why. `[VERSION-TRAP]` `[RESEARCH]`
2.7.12 The performance cost of transactions: extra coordinator round trips, control records, and
      the LSO stall. Numbers to quote and the honest "measure it" caveat. `[NUM]`
2.7.13 Kafka Streams `processing.guarantee=exactly_once_v2` and what it does under the hood
      (transactional producer + changelog topics + standby tasks). `[CFG]`
2.7.14 Spring's `KafkaTransactionManager`, container `transactionManager`, `executeInTransaction`,
      and the removal of `ChainedKafkaTransactionManager` with the "best-effort 1PC" ordering
      pattern that replaced it. `[API]` `[VERSION-TRAP]`
2.7.15 The decision rule stated plainly: **use transactions for Kafka-to-Kafka pipelines; use
      idempotency for everything else.**

## §2.8 RabbitMQ queue types and routing, in depth

2.8.1 Classic vs quorum vs stream — the full property comparison: replication, durability,
      ordering, throughput, memory profile, feature support, and use case. `[TABLE]`
2.8.2 Quorum queues in depth: Raft, `x-quorum-initial-group-size` (default 3),
      `x-quorum-target-group-size` and continuous membership reconciliation, `(N/2)+1` majority,
      and the fault tolerance arithmetic (3 members tolerate 1, 5 tolerate 2). `[NUM]` `[PROVE]`
2.8.3 Why quorum queues cost more memory and disk per message than classic ones, and 4.3's
      "halving per-message memory overhead in many scenarios". `[RESEARCH]`
2.8.4 What quorum queues do **not** support: non-durable, exclusive, server-named,
      global QoS, consumer exclusivity (use Single Active Consumer), transient/high-churn use.
      `[TABLE]` `[RESEARCH]`
2.8.5 Quorum-queue sizing guidance: review beyond ~5,000 queues per cluster; use streams above
      ~5M-message backlogs or large fanout. `[NUM]` `[RESEARCH]`
2.8.6 `x-queue-leader-locator` = `client-local` | `balanced`, and why leader placement is a real
      throughput decision. `[CFG]`
2.8.7 `rabbit.quorum_commands_soft_limit` (32) as the per-channel flow-control window into Raft.
      `[CFG]` `[NUM]` `[RESEARCH]`
2.8.8 WAL and segment sizing: `quorum_queue.wal_max_size_bytes` (512 MB),
      `quorum_queue.segment_max_size_bytes` (64 MB), checkpoints and recovery snapshots.
      `[CFG]` `[NUM]` `[RESEARCH]`
2.8.9 **Khepri** — the Raft-based metadata store replacing Mnesia: default in 4.2, sole option in
      4.3. The availability consequence stated bluntly: **a majority of nodes must be online at
      all times**, and `cluster_partition_handling` no longer exists. `[VERSION-TRAP]`
      `[RESEARCH]`
2.8.10 Streams in depth: append-only, offset-addressed, `x-max-age`, `x-stream-max-segment-size-bytes`,
      `x-stream-offset` (`first`, `last`, `next`, an absolute offset, a timestamp, an interval), the
      dedicated stream protocol versus AMQP access, super streams as the partitioned form, and
      single active consumer for streams. `[CFG]` `[RESEARCH]`
2.8.11 Routing design: when to use direct vs topic vs fanout vs headers, with the QuizStakes
      mapping (`payments.card.deposit.captured` on a topic exchange, consumed by three different
      binding patterns). `[TABLE]`
2.8.12 Exchange-to-exchange bindings as the underused composition tool.
2.8.13 The `x-death` header and how to read a message's dead-lettering history. `[DIAG]`
2.8.14 Connection and channel sizing: `channel_max`, `frame_max`, `heartbeat` (60 s default),
      `handshake_timeout`, and the "one connection per process, one channel per thread" rule.
      `[CFG]` `[NUM]`
2.8.15 Flow control: per-connection credit-based flow, the `flow` connection state, and what
      "blocked" and "blocking" mean in `rabbitmqctl list_connections`. `[DIAG]`
2.8.16 Cluster topology: nodes, disc vs (removed) RAM nodes, quorum-queue member placement, and
      why an even node count is a bad idea. `[VERSION-TRAP]`
2.8.17 Message interceptors (4.2) as the cross-protocol hook for stamping timestamps and client
      ids. `[RESEARCH]`
2.8.18 Migration from classic mirrored queues to quorum queues: the blue/green queue approach,
      the shovel approach, and the feature gaps that block it. `[RESEARCH]`

## §2.9 SQS mechanics, in depth

2.9.1 The visibility-timeout state machine as an explicit trace: `ReceiveMessage` → invisible →
      (`DeleteMessage` → gone) | (`ChangeMessageVisibility(0)` → immediately visible) |
      (timeout expires → visible, `ApproximateReceiveCount`++). `[FLOW]`
2.9.2 Setting the visibility timeout from the processing-time distribution, not from the average:
      p99.9 plus margin, or a heartbeat. Worked against the identity vendor's p99 of 38 s.
      `[NUM]` `[PROVE]`
2.9.3 The heartbeat pattern: a scheduled `ChangeMessageVisibility` extension while work proceeds,
      with the total capped at 12 hours. `[BUILD]` `[NUM]`
2.9.4 `ApproximateReceiveCount` and `ApproximateFirstReceiveTimestamp` as the two system attributes
      that make retry visible to the handler. `[API]`
2.9.5 Long polling internals: why short polling can return empty with messages present (it samples
      a subset of the distributed servers) and what `WaitTimeSeconds=20` changes. `[PROVE]`
2.9.6 The `NumberOfEmptyReceives` metric as the direct measure of money wasted on short polling.
      `[METRIC]`
2.9.7 Batch semantics: `SendMessageBatch` returns `Successful` and `Failed` lists — partial success
      is the normal case and must be handled. `[TRAP]` `[API]`
2.9.8 Lambda event source mapping specifics: batch size, batch window, maximum concurrency,
      `ReportBatchItemFailures`, and the fact that a Lambda failure returns the **whole batch** to
      the queue without it. `[TRAP]` `[X-REF 18]`
2.9.9 FIFO deduplication in depth: `MessageDeduplicationId` scope is the **queue** (or the message
      group for high-throughput mode), the window is 5 minutes, and content-based dedup hashes the
      body only — not the attributes. `[NUM]` `[TRAP]`
2.9.10 FIFO ordering in depth: within a group, a message that is in flight blocks the rest of its
      group; different groups proceed in parallel. This is head-of-line blocking with the same
      shape as Kafka's. `[PROVE]`
2.9.11 High-throughput FIFO mode: `DeduplicationScope=messageGroup`,
      `FifoThroughputLimit=perMessageGroupId`, and the partition model underneath it.
      `[CFG]` `[RESEARCH]`
2.9.12 Fair queues in depth: how SQS identifies a noisy tenant (disproportionate in-flight share),
      what it does (prioritise quiet tenants' messages to polling consumers), and what it does not
      do (order, throttle the producer, or guarantee anything). `[VERSION-TRAP]` `[RESEARCH]`
2.9.13 DLQ redrive as an API: `StartMessageMoveTask`, `ListMessageMoveTasks`,
      `CancelMessageMoveTask`, and the console flow. `[CLI]` `[RESEARCH]`
2.9.14 Queue policies, `SendMessage` permissions for SNS, and cross-account/cross-region rules (the
      DLQ must be in the same account and region as the source). `[X-REF 18]`
2.9.15 Server-side encryption (SSE-SQS vs SSE-KMS) and the KMS cost of a high-rate queue.
      `[X-REF 18]`
2.9.16 Cost modelling: $/million requests, the 64 KB request-chunk billing rule, and why batching
      by 10 is a 10× cost cut on the same throughput. `[NUM]`
2.9.17 The temporary-queue and virtual-queue patterns for request–reply over SQS, and why they are
      usually a mistake.
2.9.18 What SQS gives you for free that Kafka does not: infinite consumer scaling, per-message
      delay, per-message retry, zero ops, and a DLQ with one config field. State it, because the
      Kafka-by-default habit is real. `[TABLE]`

## §2.10 The dual-write problem and the transactional outbox

2.10.1 The problem, stated exactly: a handler must write to the database **and** publish an event,
      and there is no atomicity across two systems.
2.10.2 The four outcomes, two of them bad: DB commits + publish fails (the order exists, nobody
      hears); publish succeeds + DB rolls back (downstream acts on nothing).
      `[TABLE]` `[PROVE]`
2.10.3 Why `@Transactional` does not help: the broker send is not enlisted in the DB transaction.
      `[X-REF 07]`
2.10.4 Why `TransactionSynchronization.afterCommit` / `@TransactionalEventListener(AFTER_COMMIT)`
      does not help: it shrinks the window, it does not close it. The process can die immediately
      after commit. `[PROVE]` `[TRAP]`
2.10.5 Why XA / 2PC is rejected in practice: both systems must support it (Kafka historically did
      not), locks are held across a network round trip, and a coordinator failure leaves in-doubt
      transactions blocking everything. `[PROVE]`
2.10.6 KIP-939 as the qualification to that rejection, and why it still is not the default answer.
      `[VERSION-TRAP]`
2.10.7 **The transactional outbox**: write the event into the same database, in the same
      transaction, and publish it separately. `[BUILD]`
2.10.8 The outbox schema: `id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload`,
      `headers`, `created_at`, `published_at`, plus the partial index
      `WHERE published_at IS NULL`. `[SQL]` `[X-REF 09]`
2.10.9 **The insight to state out loud: the outbox converts an unsolvable atomicity problem into a
      duplicate-delivery problem, which idempotency already solves.** `[PROVE]`
2.10.10 The polling relay: `SELECT … WHERE published_at IS NULL ORDER BY id FOR UPDATE SKIP LOCKED
      LIMIT n`, publish, mark, commit. Why `SKIP LOCKED` is what makes it safely multi-instance.
      `[SQL]` `[X-REF 09]`
2.10.11 Relay ordering: `ORDER BY id` gives you per-table order, and using the aggregate id as the
      partition key gives you per-aggregate order downstream. `[PROVE]`
2.10.12 Relay failure modes: publishes then crashes before marking (duplicate — fine); marks then
      crashes before publishing (**loss** — so never mark first); marks in a separate transaction
      from the publish (the same dual write, one level down). `[TRAP]` `[PROVE]`
2.10.13 Outbox table growth and cleanup: 19.8M ledger movements/day, so a delete-after-publish or
      a partitioned outbox is mandatory, not optional. `[NUM]`
2.10.14 Polling cost: a relay polling every 100 ms against a partial index is cheap; every 10 ms
      is not. The latency-versus-load curve. `[NUM]`
2.10.15 **CDC as the relay** — Debezium tailing the PostgreSQL WAL via logical decoding
      (`pgoutput`, replication slots) or the MySQL binlog. No polling load, lower latency, no
      missed rows, and it also captures writes from code paths that forgot the outbox.
      `[X-REF 09]`
2.10.16 Debezium's `EventRouter` outbox SMT: the expected column names
      (`aggregatetype`, `aggregateid`, `type`, `payload`), `route.by.field`,
      `table.expand.json.payload`, and how it turns one outbox table into many topics.
      `[CFG]` `[RESEARCH]`
2.10.17 CDC-the-business-tables versus CDC-the-outbox: the outbox gives you control of the *event
      schema* rather than leaking your table schema to consumers, which is usually worth keeping.
      `[PROVE]`
2.10.18 The replication-slot hazard: a stalled Debezium connector holds the WAL and fills the
      primary's disk. This is the outbox's real production failure mode. `[TRAP]` `[X-REF 09]`
2.10.19 The **listen-to-yourself** variant: publish first, consume your own event, then write the
      DB. When it is legitimate and why it usually is not.
2.10.20 The **inbox** as the mirror image, and the fact that it is literally the
      `processed_events` table from §1.7.
2.10.21 The QuizStakes worked case: `AccountActivated` must be published if and only if the
      activation committed (scenario § 15.2 names it), and `DEP-301 → DEP-400` as the seam that
      the outbox *cannot* fix because the PSP is not a database. `[PROVE]`

## §2.11 Sagas and long-running transactions

2.11.1 Definition: a sequence of local transactions, each publishing an event or message that
      triggers the next, with compensating transactions to undo on failure. `[SPEC]`
2.11.2 **ACD, not ACID** — a saga gives atomicity, consistency and durability but **not isolation**,
      which is the source of every saga anomaly. `[PROVE]` `[RESEARCH]`
2.11.3 **Choreography** — each service reacts to events. Low coupling, no central component, and
      no single place that knows the state of the whole flow. `[TABLE]`
2.11.4 **Orchestration** — a central orchestrator issues commands and tracks state. Explicit,
      testable, debuggable, and a new component to own. `[TABLE]`
2.11.5 The decision rule: choreography for 2–3 steps, orchestration for 4+ or wherever a human
      will ask "where is this stuck?". `[PROVE]`
2.11.6 **Compensating transactions** are not rollbacks: they are new business operations with their
      own failure modes, their own audit trail, and their own possibility of being impossible.
2.11.7 The compensation-that-cannot-complete case, straight from scenario § 15.2: a chargeback
      after the client withdrew the proceeds and the bonus converted to cash. There is nothing to
      reverse; the loss must land in `CHARGEBACK_LOSS` and `PROMOTIONAL_EXPENSE`. `[PROVE]`
2.11.8 The three step types: **compensatable**, **pivot**, **retriable** — and why every saga must
      be ordered so that everything after the pivot is retriable. `[PROVE]` `[TABLE]`
2.11.9 The isolation countermeasures, named and explained: **semantic lock**, **commutative
      updates**, **pessimistic view**, **reread value**, **version file**, **by value**.
      `[TABLE]` `[RESEARCH]`
2.11.10 `RESERVED` as a semantic lock in QuizStakes: the reservation is exactly a semantic lock over
      the client's funds, and `ORPHANED` is what happens when the lock is never released.
      `[PROVE]`
2.11.11 Saga state persistence: a saga instance table with a state machine, timeouts per step, and
      an idempotency key per step. `[BUILD]` `[SQL]`
2.11.12 Saga timeouts: every step needs one, and the timeout action is a compensation, not a retry.
2.11.13 The frameworks named: Axon, Eventuate Tram, Camunda/Zeebe, Temporal, AWS Step Functions,
      and Spring Statemachine — with the honest note that most teams should write the state machine
      by hand first. `[TABLE]`
2.11.14 **Process manager** vs **saga** vs **workflow engine** — vocabulary hygiene.
2.11.15 The QuizStakes card-deposit saga written out end to end: restriction check → limit check →
      authorise → capture → ledger credit → bonus grant, with the compensation for each step and
      the pivot identified (`DEP-301 CAPTURED`). `[FLOW]` `[TABLE]`
2.11.16 The `PaymentRun` saga: two-operator sign-off, file generation between the approvals,
      `SENT_TO_BANK` as the irreversible pivot, and `PARTIALLY_ACCEPTED` as the outcome that proves
      run state and item state must be separate machines. `[FLOW]`

## §2.12 Event modelling and contract evolution

2.12.1 **Event notification** vs **event-carried state transfer** vs **event sourcing** vs **CQRS**
      — four patterns people call "event driven". `[TABLE]`
2.12.2 What belongs in an event: the facts as of the moment it happened, an identifier, a
      timestamp, a version — and never a computed value the consumer could derive differently.
2.12.3 Thin events force a callback (chatty, and the callback may see newer state); fat events
      duplicate data (stale, but self-contained and replayable). The trade, worked. `[PROVE]`
2.12.4 **Event versioning strategies**: additive-only, upcasting on read, a version field with a
      dispatch, or a new topic per major version. `[TABLE]`
2.12.5 The consumer-side rule: **ignore unknown fields**, never fail on them. Tolerant reader.
      `[PROVE]`
2.12.6 The producer-side rule: never remove or repurpose a field a consumer might read; deprecate
      with a sunset date. `[X-REF 12]`
2.12.7 Schema compatibility enforcement in CI as the only mechanism that actually holds — a
      registry check on every build. `[X-REF 16]`
2.12.8 Event ownership: the producing service owns the schema; consumers do not get to add fields.
      The governance failure this prevents.
2.12.9 The consumer-driven-contract counterargument, and where it belongs. `[X-REF 16]`
2.12.10 **Event sourcing** properly defined: the event log is the source of truth and state is a
      fold over it. `ApplicationHistory` in QuizStakes is already this. `[PROVE]`
2.12.11 Event sourcing's real costs: snapshots, replay time, schema evolution over a 7-year log,
      GDPR erasure against an append-only store, and the difficulty of ad-hoc queries.
      `[TABLE]`
2.12.12 **CQRS** and the read models it produces: `BalanceView` over the ledger, `ProfileService`
      over eight owners, `PendingActions` over requirements and restrictions. Different shapes,
      different freshness needs. `[PROVE]`
2.12.13 **Projection lag** as the CQRS failure mode: `PendingActions` still showing a banner for a
      satisfied requirement. How to measure it and what to promise the user. `[METRIC]`
2.12.14 **Read-your-writes** across a projection, and the three fixes: read from the write model
      for your own writes, sticky routing, or a version token the client sends back.
      `[X-REF 22]`
2.12.15 The **event catalogue** as an artifact: name, owner, schema, partition key, expected rate,
      consumers, retention. QuizStakes § 14.1 is exactly this table and the bible should say so.
      `[TABLE]`
2.12.16 Naming: past-tense verbs, aggregate-first, no "Command" in an event name, no
      "Event" suffix noise.

## §2.13 Retry storms, cascading failure and resilience

2.13.1 The mechanism: a downstream slows, callers time out and retry, retries add load, load
      increases exactly when capacity is lowest, and the accumulated backlog re-kills it on
      recovery. `[PROVE]`
2.13.2 **Amplification is multiplicative across layers**: three layers each retrying 3× is 27× the
      original load. `[NUM]` `[PROVE]`
2.13.3 Defence 1 — **retry at one layer only**, usually closest to the failure; the others pass
      errors through.
2.13.4 Defence 2 — **exponential backoff with jitter**. Non-negotiable.
2.13.5 Defence 3 — **circuit breaker**: closed → open (fail fast, no call at all) → half-open
      (a trickle) → closed. What actually lets a downstream recover is the *removal of load*.
      Resilience4j `CircuitBreakerConfig` with `failureRateThreshold`,
      `slidingWindowSize`, `waitDurationInOpenState`, `permittedNumberOfCallsInHalfOpenState`.
      `[API]` `[CFG]`
2.13.6 Defence 4 — **retry budgets / token buckets**: cap retries at e.g. 10% of total requests, so
      amplification is bounded even when everything fails. `[NUM]`
2.13.7 Defence 5 — **bulkheads**: separate pools per dependency. Scenario § 15.1: the identity
      vendor slowing must not exhaust the pool serving card deposits. `[X-REF 05]`
2.13.8 Defence 6 — **load shedding**: reject cheaply and immediately under overload. A fast 503
      beats a slow timeout for both sides. `[X-REF 12]`
2.13.9 Defence 7 — **do not retry non-retryable errors** (4xx, validation, deserialisation).
2.13.10 Defence 8 — **timeouts everywhere**, and the rule that a caller's timeout must be shorter
      than its own caller's. `[X-REF 10]`
2.13.11 The messaging-specific form: consumers fail, messages return to the queue, redelivery adds
      to new arrivals, and you get a **redelivery storm**. Backoff and DLQ-ing poison messages are
      what break the loop.
2.13.12 The rebalance-storm form: slow processing → eviction → rebalance → work redone elsewhere →
      slower processing.
2.13.13 The **thundering herd on recovery**: 8.64M backlogged messages hitting a just-recovered
      database. Rate-limit the consumer during catch-up rather than maximising throughput.
      `[PROVE]`
2.13.14 Circuit-breaking a *consumer*: pause the container when the downstream circuit opens
      instead of failing every message into the DLQ. `[API]` `[TRAP]`
2.13.15 Graceful degradation, from scenario § 15.5: screening provider down → hold applications at
      `AA-500` rather than refusing new applicants.
2.13.16 The QuizStakes failure case study to write up: PSP timing out at 500/sec with a 10 s
      timeout, 95k deposits/day, and what each defence would have changed.

## §2.14 Scheduled jobs, double runs and distributed locks

2.14.1 The problem: a `@Scheduled` job on 3 replicas runs 3 times. Sometimes harmless; sometimes
      three `PaymentRun`s and duplicate payouts.
2.14.2 Option 1 — **pin to one instance**. Simple, a single point of failure, and it drifts from
      your deployment model.
2.14.3 Option 2 — **distributed lock**. Redis `SET key val NX PX 30000`, or ShedLock over the
      existing database. `[BUILD]`
2.14.4 **The lock-expiry hazard, in full**: a lock must have a TTL or a crashed holder blocks
      forever; a TTL means the lock can expire *while the holder is still working* (a long GC
      pause, a slow query, stalled I/O), so a second instance acquires it and both run.
      `[PROVE]` `[TRAP]` `[X-REF 06]`
2.14.5 The four mitigations: a TTL well above worst-case runtime, heartbeat renewal by a watchdog,
      a **fencing token** the resource checks so a stale holder's writes are rejected, and
      compare-and-delete release via a Lua script so you never delete someone else's lock.
      `[BUILD]`
2.14.6 **There is no lock design that is both safe and live under arbitrary pauses.** Redlock is
      contested for exactly this reason. Locks reduce, they do not eliminate. `[PROVE]`
2.14.7 Option 3 — **make the job idempotent**: `WHERE status = 'PENDING'` with an atomic claim,
      upserts, and a unique constraint on `(job, period)`. **This is the best answer** and the one
      interviewers are looking for. `[SQL]`
2.14.8 Option 4 — **use a real scheduler**: Kubernetes `CronJob` with `concurrencyPolicy: Forbid`
      (still at-least-once), Quartz with a JDBC job store and its own clustering, or a managed
      scheduler (EventBridge Scheduler → SQS → workers). `[X-REF 19]`
2.14.9 Option 5 — **leader election**: a lease in etcd/ZooKeeper/Kubernetes, or Kafka's own group
      protocol repurposed. Scenario § 13.4: "Two runs open simultaneously → duplicate payouts.
      Leader election is the only defence."
2.14.10 When to avoid locks entirely: high-frequency jobs where lock overhead dominates, work
      partitionable by key (each instance owns its shard — no coordination), and naturally
      idempotent operations. Partitioning is underrated: it scales, a lock serialises.
      `[PROVE]`
2.14.11 The claim-based work queue as the database-native alternative:
      `UPDATE … SET claimed_by = ?, claimed_at = now() WHERE id IN (SELECT … FOR UPDATE SKIP
      LOCKED LIMIT n) RETURNING *`. `[SQL]` `[X-REF 09]`
2.14.12 Reaping abandoned claims (`claimed_at < now() - interval`) and why that is the same expiry
      hazard in a different costume.
2.14.13 The `PaymentRun` worked case: four windows/day, one leader, drain-before-terminate on
      deploy, and the specific failure of a run killed between `SENT_TO_BANK` and the item updates.
      `[FLOW]`
2.14.14 File-level idempotency for the bank payout file: submitting the same file twice may be
      accepted twice by the bank, so a file-level reference is mandatory. Scenario § 13.4.

## §2.15 Backpressure, end to end

2.15.1 Definition: backpressure is a slow consumer's ability to make a fast producer slow down.
      Without it, the buffer between them grows until memory, disk or latency breaks.
2.15.2 Where it exists naturally — **TCP's receive window**: a slow reader shrinks the window and
      the sender blocks. Free, and it is why blocking I/O has decent backpressure by default.
      `[X-REF 10]`
2.15.3 Where it exists naturally — **pull-based brokers**: the consumer decides when to poll, so it
      cannot be overwhelmed *by the broker*.
2.15.4 **The broker converts backpressure into unbounded lag.** It absorbs the producer's output,
      so the producer feels nothing. This is the single most important sentence in the section.
      `[PROVE]`
2.15.5 Where it exists naturally — **bounded thread pools with bounded queues** and
      `CallerRunsPolicy`, which makes the submitting thread do the work and thereby slows the
      producer. `LinkedBlockingQueue` at default unbounded capacity is a memory leak with a
      rejection policy that never fires. `[X-REF 05]` `[TRAP]`
2.15.6 Where it exists naturally — **connection pool limits** (HikariCP) as an admission-control
      point. `[X-REF 09]`
2.15.7 Where it exists naturally — **AMQP prefetch** and **Kafka's `max.poll.records` +
      `max.partition.fetch.bytes`**, which are the broker-protocol forms of a credit window.
2.15.8 Where it exists naturally — **Reactive Streams `request(n)`** in WebFlux/RxJava/Reactor
      Kafka. `[X-REF 04]`
2.15.9 Where it is missing and you must add it: unbounded in-memory queues anywhere in the
      pipeline, fire-and-forget async producers, and **virtual threads** (removing the thread limit
      removed an accidental concurrency cap, so you now need explicit semaphores or
      `StructuredTaskScope` limits). `[X-REF 04]` `[X-REF 05]`
2.15.10 Producer-side backpressure in Kafka: `buffer.memory` + `max.block.ms` is the only
      mechanism, and it blocks the calling thread — which is backpressure, but only if you are not
      calling from a request thread you cannot afford to block. `[PROVE]`
2.15.11 RabbitMQ's producer-side backpressure: credit-based flow control plus memory/disk alarms
      blocking `basic.publish`.
2.15.12 SQS's producer-side backpressure: **none**. Which is exactly what you are paying for and
      exactly the risk.
2.15.13 **End-to-end thinking**: backpressure must propagate to the *source*, or you have just
      moved the queue. If the API layer keeps accepting requests and dropping them into a queue
      consumers cannot drain, the system is failing — later, and with worse symptoms.
      `[PROVE]`
2.15.14 The honest edge responses: **rate limiting** and **load shedding** — reject work you cannot
      do, fast, with `429`/`503` and `Retry-After`. `[X-REF 12]`
2.15.15 The rule of thumb: **every buffer bounded, and every bound with a defined behaviour when
      hit** — block, reject, or drop — chosen deliberately, never by default. `[PROVE]`
2.15.16 Scenario § 15.1's case: a month-end file of 500,000 movements against workers that cannot
      keep up. Work the numbers and pick the bound. `[NUM]`
2.15.17 Lag-based autoscaling as the productised form (KEDA on Kafka lag or SQS depth), and its
      instability: scaling on a lagging indicator oscillates unless damped. `[X-REF 19]`

## §2.16 Observability for messaging

2.16.1 The four questions monitoring must answer: is anything stuck, is anything lost, is anything
      duplicated, and how far behind are we? `[TABLE]`
2.16.2 **Consumer lag** — per partition and per group, from `kafka-consumer-groups.sh`, Burrow,
      Kafka Exporter or the client's `records-lag-max`. Why the *maximum across partitions* is the
      number to alert on, not the sum. `[METRIC]` `[PROVE]`
2.16.3 **Time lag versus offset lag**: 1M records of lag means nothing without the rate. Compute
      lag-in-seconds and alert on that. `[NUM]` `[PROVE]`
2.16.4 **Queue depth** and **age of oldest message** as the SQS equivalents, with
      `ApproximateAgeOfOldestMessage` being the one that maps to a user-visible promise.
      `[METRIC]`
2.16.5 **DLQ depth** — alert on > 0. `[METRIC]`
2.16.6 **Redelivery / receive-count distribution** as the early-warning signal that a dependency is
      degrading before the DLQ fills.
2.16.7 **End-to-end latency**: `occurredAt` in the event header versus processing time, which is
      the only metric that reflects what the user experiences. `[BUILD]`
2.16.8 Broker-side metrics: `UnderReplicatedPartitions` (must be 0),
      `OfflinePartitionsCount` (must be 0), `ActiveControllerCount` (must be exactly 1),
      `UncleanLeaderElectionsPerSec` (**any non-zero value is a data-loss event**),
      `RequestHandlerAvgIdlePercent`, `NetworkProcessorAvgIdlePercent`,
      `IsrShrinksPerSec`/`IsrExpandsPerSec`, `LogFlushRateAndTimeMs`, `BytesInPerSec`/
      `BytesOutPerSec`, `TotalTimeMs` per request type, `RequestQueueSize`, `PurgatorySize`.
      `[METRIC]` `[TABLE]` `[RESEARCH]`
2.16.9 RabbitMQ metrics: `messages_ready`, `messages_unacknowledged`, `message_stats.publish_details.rate`,
      `consumer_utilisation`, `disk_free`, `mem_used`, per-queue and per-node, plus the Prometheus
      plugin. `[METRIC]`
2.16.10 **Distributed tracing across a broker**: `traceparent`/`b3` in message headers, the
      producer span, the consumer span, and the fact that the parent–child link is *not* automatic
      because the two are separated in time. Micrometer/OpenTelemetry Kafka instrumentation.
      `[X-REF 20]`
2.16.11 The correlation id as the thing that makes a multi-hop async flow debuggable at 3 a.m.
2.16.12 Log lines a consumer must emit: on receive (id, key, partition, offset, attempt), on
      success (duration), on failure (exception, attempt, next action), on DLQ. Nothing else.
      `[DIAG]`
2.16.13 The alert set with thresholds, not just names: lag-seconds > SLA, DLQ > 0,
      `UnderReplicatedPartitions` > 0, `UncleanLeaderElectionsPerSec` > 0, rebalance rate > N/hour,
      `ApproximateAgeOfOldestMessage` > SLA, empty-receive ratio > 90%. `[TABLE]` `[METRIC]`
2.16.14 Kafka's own client telemetry (KIP-714/KIP-1076) pushing client metrics to the broker, and
      KIP-1100's metric-naming correction to `kafka.COMPONENT`. `[VERSION-TRAP]` `[RESEARCH]`
2.16.15 What to record in an audit trail rather than a metric, when the messages are money:
      `LedgerMovementPosted` reconciliation (scenario § 14.3) as the real detection mechanism, of
      which monitoring is only the fast path.

## §2.17 Security, multi-region and operations

2.17.1 Kafka authentication: SASL/PLAIN, SASL/SCRAM-SHA-256/512, SASL/GSSAPI, SASL/OAUTHBEARER
      (with 4.1's jwt-bearer grant and 4.3's client assertion), and mTLS. `[X-REF 13]`
2.17.2 Kafka authorisation: ACLs on `Topic`/`Group`/`Cluster`/`TransactionalId` resources, the
      `Read`/`Write`/`Describe`/`Create`/`Alter`/`ClusterAction` operations, prefixed ACLs, and
      `allow.everyone.if.no.acl.found`. `[CFG]` `[TABLE]`
2.17.3 **The ACL people forget**: a transactional producer needs `Write` on `TransactionalId`, and
      a consumer group needs `Read` on `Group`. `[TRAP]`
2.17.4 Encryption in transit versus at rest, and the fact that Kafka has **no field-level
      encryption** — payload encryption is the producer's job. `[X-REF 13]`
2.17.5 Quotas: `producer_byte_rate`, `consumer_byte_rate`, `request_percentage`, applied per
      user/client-id, and the `throttle_time_ms` the client is told to wait. The obscure detail:
      throttled requests skip purgatory and return immediately. `[CFG]` `[RESEARCH]`
2.17.6 RabbitMQ security: vhosts, user tags, permission regexes, TLS, and the management API's
      exposure.
2.17.7 SQS/SNS security: IAM identity policies vs queue/topic resource policies, VPC endpoints,
      and the cross-account `SendMessage` grant that makes SNS→SQS work. `[X-REF 18]`
2.17.8 Multi-region Kafka: MirrorMaker 2, Cluster Linking, and active-active's duplicate/loop
      problem solved by `IdentityReplicationPolicy` or topic prefixing. `[TABLE]`
2.17.9 Offset translation across clusters (`RemoteClusterUtils.translateOffsets`, checkpoint
      topics) and why failover is never seamless. `[RESEARCH]`
2.17.10 RTO/RPO for a messaging tier, stated as numbers rather than adjectives.
2.17.11 Broker upgrades: rolling restart, `inter.broker.protocol.version` (and its removal under
      KRaft feature levels), and the client-compatibility matrix (Kafka 4.0 dropped protocol
      versions older than 2.1). `[VERSION-TRAP]`
2.17.12 Partition reassignment and rebalancing storage: `kafka-reassign-partitions.sh`, throttles,
      and 4.3's broker/log-dir **cordoning** (`cordoned.log.dirs`) for decommissioning.
      `[CLI]` `[RESEARCH]`
2.17.13 Capacity planning for QuizStakes: 19.8M ledger events/day at ~400 bytes = ~7.9 GB/day raw,
      ×3 replication = ~24 GB/day, ×7-day retention = ~166 GB, before compression. Do the
      arithmetic in the bible. `[NUM]` `[PROVE]`
2.17.14 Testing messaging: Testcontainers (`KafkaContainer`, `RabbitMQContainer`, LocalStack),
      `@EmbeddedKafka`/`EmbeddedKafkaKraftBroker`, awaitility for async assertions, and the two
      tests every consumer needs — the duplicate test and the poison test. `[X-REF 16]`
2.17.15 Local development: `docker compose` with a single-node KRaft broker, `kafka-ui`/`akhq`, and
      LocalStack for SQS. `[CLI]`

---

# PART 3 — UNDER THE HOOD

## §3.1 The Kafka storage engine

3.1.1 The on-disk layout: `<log.dirs>/<topic>-<partition>/` containing `.log`, `.index`,
      `.timeindex`, `.snapshot`, `.txnindex`, and `leader-epoch-checkpoint`. `[DIAG]`
3.1.2 **Segments**: the active segment plus sealed segments, named by their base offset
      (`00000000000000012345.log`). `segment.bytes` (1073741824 = 1 GB) and `segment.ms`
      (604800000 = 7 days) as the roll triggers, with 4.0's new minimums of 1 MB and 1 minute.
      `[CFG]` `[NUM]` `[VERSION-TRAP]`
3.1.3 **Only sealed segments are eligible for deletion.** A topic with a 1-hour retention and a
      1 GB segment size keeps data far longer than an hour, and this surprises people every time.
      `[TRAP]` `[PROVE]`
3.1.4 **The obscure one: segment rolling and retention both use the *message* timestamp**, not
      broker wall-clock. A single record with a far-future timestamp immortalises its segment.
      `message.timestamp.type` (`CreateTime` default vs `LogAppendTime`) and 4.0's
      `message.timestamp.after.max.ms` (3600000) as the guard. `[TRAP]` `[NUM]` `[RESEARCH]`
3.1.5 **The sparse `.index`**: offset → physical byte position, one entry every
      `index.interval.bytes` (4096). Lookup is a binary search in the index followed by a linear
      scan of at most 4 KB in the log. `[PROVE]` `[NUM]`
3.1.6 **The `.timeindex`**: timestamp → offset, which is what `offsetsForTimes` and
      `--to-datetime` use. `[API]`
3.1.7 `segment.index.bytes` / `log.index.size.max.bytes` (10485760) and its new 1 KB minimum, plus
      the fact that a full index forces a segment roll. `[CFG]` `[NUM]`
3.1.8 **The record batch format v2** on the wire and on disk, field by field: base offset, batch
      length, partition leader epoch, magic, CRC32C, attributes (compression codec, timestamp
      type, transactional flag, control flag), last offset delta, first/max timestamp, producer id,
      producer epoch, base sequence, record count, then the varint-encoded records with delta
      offsets and delta timestamps. `[WIRE]` `[SOURCE]`
3.1.9 Why the batch is the unit of everything — compression, CRC, replication, and the idempotence
      sequence number are all per batch, not per record. `[PROVE]`
3.1.10 Message format v0 and v1 were **removed in Kafka 4.0**; the broker no longer down-converts
      for ancient clients. `[VERSION-TRAP]`
3.1.11 **Sequential I/O** as the performance thesis: append-only writes turn random I/O into
      sequential I/O, and a spinning disk does ~100 KB/s random versus ~600 MB/s sequential.
      `[PROVE]` `[NUM]`
3.1.12 **The page cache is the read cache.** Kafka deliberately keeps no application-level cache,
      writes go to the OS page cache, and `fsync` is left to the kernel (`log.flush.interval.messages`
      default `Long.MAX_VALUE`). Durability comes from **replication, not from fsync**.
      `[PROVE]` `[CFG]` `[TRAP]`
3.1.13 Why that is safe and when it is not: a whole-datacentre power loss can lose unflushed data
      on every replica simultaneously. `[PROVE]`
3.1.14 **Zero-copy** via `sendfile(2)` / `FileChannel.transferTo`: the page cache goes straight to
      the socket without a user-space copy. What disables it — TLS, and any broker-side
      recompression or down-conversion. `[PROVE]` `[TRAP]` `[X-REF 11]`
3.1.15 Why a consumer reading the tail is nearly free (page-cache hit, zero copy) and a consumer
      reading from offset 0 is expensive (disk read, cache eviction for everyone else). The
      "one backfill consumer degrades the whole cluster" incident shape. `[PROVE]`
3.1.16 The heap-versus-page-cache sizing rule: give the broker a small heap (6 GB) and leave the
      rest of RAM to the page cache. `[NUM]` `[X-REF 06]`
3.1.17 Retention enforcement: the log-retention thread, `log.retention.check.interval.ms` (300000),
      and deletion by rename-to-`.deleted` then delete after `log.segment.delete.delay.ms` (60000).
      `[CFG]` `[NUM]`
3.1.18 Recovery on unclean shutdown: `num.recovery.threads.per.data.dir` (**2** since 4.0, was 1),
      the `.kafka_cleanshutdown` marker, and CRC re-verification of the last segment.
      `[CFG]` `[VERSION-TRAP]`
3.1.19 Reading a segment by hand: `kafka-dump-log.sh --files … --print-data-log`, and what each
      column means. `[CLI]` `[DIAG]`
3.1.20 Disk footprint arithmetic for QuizStakes' `LedgerMovementPosted`: 19.8M/day × ~400 bytes ×
      3 replicas × 7 days ≈ 166 GB before compression, ~50 GB with zstd at 3:1. Show the working.
      `[NUM]` `[PROVE]`

## §3.2 The Kafka network layer and request pipeline

3.2.1 The reactor pattern: one `Acceptor` per listener, `num.network.threads` (3) processors doing
      NIO, a shared `RequestChannel` queue, and `num.io.threads` (8) request handlers.
      `[CFG]` `[NUM]` `[FLOW]`
3.2.2 `queued.max.requests` (500) and what a full request queue does to latency. `[CFG]`
3.2.3 **Purgatory** — the delayed-operation structure holding `Fetch` requests waiting for
      `fetch.min.bytes` and `Produce` requests waiting for `acks=all`. A hierarchical timing wheel
      plus a watcher map. `[PROVE]` `[SOURCE]`
3.2.4 Why purgatory exists at all: it turns "wait for a condition" into O(1) insertion and
      expiration instead of a thread per waiter. `[PROVE]`
3.2.5 The obscure detail: **quota-throttled requests bypass the purgatory wait** and return
      immediately with `throttle_time_ms`, which is why throttling and `fetch.max.wait.ms` do not
      compose the way you would guess. `[TRAP]` `[RESEARCH]`
3.2.6 The binary protocol: size-prefixed requests, a request header (api key, api version,
      correlation id, client id), and per-API versioned schemas negotiated by `ApiVersions`.
      `[WIRE]`
3.2.7 The API surface names worth knowing: `Produce`, `Fetch`, `ListOffsets`, `Metadata`,
      `OffsetCommit`, `OffsetFetch`, `FindCoordinator`, `JoinGroup`, `SyncGroup`, `Heartbeat`,
      `LeaveGroup`, `ConsumerGroupHeartbeat` (KIP-848), `ShareFetch`/`ShareAcknowledge` (KIP-932),
      `InitProducerId`, `AddPartitionsToTxn`, `EndTxn`, `WriteTxnMarkers`. `[WIRE]` `[TABLE]`
3.2.8 KIP-896's removal of pre-2.1 protocol versions in 4.0, and the bidirectional client/broker
      version floor it creates. `[VERSION-TRAP]`
3.2.9 `RequestQueueTimeMs` / `LocalTimeMs` / `RemoteTimeMs` / `ResponseQueueTimeMs` /
      `ResponseSendTimeMs` as the five-part latency breakdown that tells you *where* a slow
      request is slow. `[METRIC]` `[DIAG]`
3.2.10 Connection handling: `connections.max.idle.ms` (600000),
      `max.connections.per.ip`, and `socket.request.max.bytes` (104857600). `[CFG]` `[NUM]`
3.2.11 Metadata refresh on the client: `metadata.max.age.ms`, `NOT_LEADER_OR_FOLLOWER` triggering
      an immediate refresh, and KIP-1102's proactive rebootstrap. `[RESEARCH]`

## §3.3 The replication protocol

3.3.1 Followers are consumers: a follower issues a `Fetch` against the leader exactly like a
      consumer does, with `replica.fetch.max.bytes` and `replica.fetch.wait.max.ms`.
      `[CFG]` `[PROVE]`
3.3.2 **LEO (log end offset)** and **HW (high watermark)** — the leader's HW is the minimum LEO
      across the ISR, and it is propagated back to followers in fetch responses. `[PROVE]`
3.3.3 Why consumers cannot read past the HW: a record above it might not survive a leader change.
      `[PROVE]`
3.3.4 The commit rule: a record is **committed** when every ISR member has it, and only committed
      records are ever exposed. `acks=all` waits for exactly this. `[PROVE]`
3.3.5 **ISR membership**: `replica.lag.time.max.ms` (30000) as the sole criterion since KIP-107
      removed the message-count criterion. Shrink and expand events, and
      `IsrShrinksPerSec` as the early warning. `[CFG]` `[METRIC]`
3.3.6 `min.insync.replicas` semantics: it is checked **only for `acks=all`** and produces
      `NotEnoughReplicasException` / `NotEnoughReplicasAfterAppendException` when the ISR is too
      small. `[CFG]` `[TRAP]`
3.3.7 **The obscure one: the broker caps the effective `min.insync.replicas` at
      `replication.factor`.** Setting `min.insync.replicas=3` on an RF=2 topic silently behaves as
      2, so your "3 copies" guarantee is fiction. `[TRAP]` `[SOURCE]` `[RESEARCH]`
3.3.8 The availability arithmetic: RF=3 + `min.insync.replicas=2` tolerates **one** broker loss
      for writes and two for reads. RF=3 + ISR=3 tolerates zero. `[PROVE]` `[NUM]`
3.3.9 **Unclean leader election**: `unclean.leader.election.enable` (default false) — electing an
      out-of-sync replica trades committed data for availability. Any non-zero
      `UncleanLeaderElectionsPerSec` is a data-loss event, and the newly-elected replica becomes a
      singleton ISR that *hides* the data only the old ISR had. `[CFG]` `[PROVE]` `[TRAP]`
      `[RESEARCH]`
3.3.10 **Leader epochs** (KIP-101, KIP-279): the epoch-based truncation protocol that replaced
      high-watermark truncation and fixed two real log-divergence bugs. The
      `leader-epoch-checkpoint` file and `OffsetsForLeaderEpoch`. `[PROVE]` `[SOURCE]`
3.3.11 **Eligible Leader Replicas (KIP-966)** — a tracked subset of replicas known to be safe for
      election even after falling out of the ISR, previewed in Kafka 4.0. `[VERSION-TRAP]`
      `[RESEARCH]`
3.3.12 Preferred leader election and `auto.leader.rebalance.enable` (true) — why leadership drifts
      after a restart and why an unbalanced leader distribution shows up as one hot broker.
      `[CFG]`
3.3.13 Rack-aware replica placement and the guarantee it gives (no two replicas in the same rack
      while `replication.factor <= racks`). `[PROVE]`
3.3.14 `KafkaProducer` durability end to end, as a single ordered trace: `send` → accumulator →
      `Produce` request → leader appends to the active segment → followers fetch → leader advances
      the HW → response with `acks=all` → callback. Where each `acks` value returns. `[FLOW]`
3.3.15 **How to lose a message in Kafka**, enumerated exhaustively: `acks=0`; `acks=1` + leader
      failure; `min.insync.replicas=1`; unclean leader election; `retries` exhausted with an
      ignored callback; the producer buffer lost on a hard kill; retention expiry before
      consumption; `offsets.retention.minutes` expiry with `auto.offset.reset=latest`; auto-commit
      ahead of processing; a manual `seekToEnd`. `[TABLE]` `[PROVE]`

## §3.4 KRaft — the metadata layer

3.4.1 What KRaft replaced and why: ZooKeeper's write bottleneck, the O(partitions) controller
      failover, and two systems to operate. `[VERSION-TRAP]`
3.4.2 The controller quorum: an odd number of controllers running Raft over the internal
      `__cluster_metadata` topic, with one **active controller** as the Raft leader.
3.4.3 Metadata as a log: brokers *replay* the metadata log rather than being pushed watches, so
      failover is bounded by log replay from a snapshot, not by a full ZooKeeper read.
      `[PROVE]`
3.4.4 Roles: `process.roles=broker`, `controller`, or `broker,controller` (combined mode, for
      development only). `node.id`, `controller.quorum.voters` /
      `controller.quorum.bootstrap.servers`. `[CFG]`
3.4.5 `kafka-storage.sh format --cluster-id` and the `meta.properties` file as the bootstrap step
      that has no ZooKeeper analogue. `[CLI]`
3.4.6 **Feature levels** replacing `inter.broker.protocol.version`: `metadata.version` and the
      per-feature levels queried and set with `kafka-features.sh`. `[CLI]` `[VERSION-TRAP]`
3.4.7 Metadata snapshots, `metadata.log.max.record.bytes.between.snapshots`, and controller
      catch-up.
3.4.8 KIP-996 **pre-vote** — a node checks whether it could win before disrupting the current
      leader, eliminating a class of spurious elections. `[RESEARCH]`
3.4.9 Dynamic quorum membership: `AddRaftVoter`/`RemoveRaftVoter`, auto-join, and 4.2's
      `AckWhenCommitted` flag. `[RESEARCH]`
3.4.10 KRaft metrics: `ActiveControllerCount` (must be exactly 1 cluster-wide),
      `MetadataLoader` `AvgIdleRatio` (4.2), controller `AvgIdleRatio` (4.2),
      `LastAppliedRecordLagMs`. `[METRIC]` `[RESEARCH]`
3.4.11 The KRaft failure mode to understand: **lose the controller quorum majority and the cluster
      cannot change metadata** — no leader elections, no topic creation — even though existing
      leaders keep serving. `[PROVE]`
3.4.12 The obscure detail: in dedicated-controller mode the `controllerId` returned in metadata is
      a placeholder, because the controller plane is not client-reachable. `[TRAP]` `[RESEARCH]`
3.4.13 Migration from ZooKeeper (3.4–3.9 dual-write mode) as history, and the fact that 4.x can
      only be reached via a 3.9 KRaft cluster. `[VERSION-TRAP]`

## §3.5 The group coordinator and `__consumer_offsets`

3.5.1 `__consumer_offsets`: 50 partitions (`offsets.topic.num.partitions`), replication factor
      `offsets.topic.replication.factor` (3), `cleanup.policy=compact`. `[CFG]` `[NUM]`
3.5.2 The coordinator selection function: `abs(group.id.hashCode()) % offsets.topic.num.partitions`,
      and the leader of that partition is the group coordinator. `[PROVE]` `[SOURCE]`
3.5.3 The record shape: key = `(group, topic, partition)`, value = `(offset, leaderEpoch, metadata,
      commitTimestamp, expireTimestamp)`. Compaction keeps the latest per key, which is why the
      topic does not grow without bound. `[WIRE]` `[PROVE]`
3.5.4 Group metadata records (members, assignment, protocol) in the same topic, keyed by group id.
3.5.5 `kafka-console-consumer.sh --topic __consumer_offsets --formatter
      "kafka.coordinator.group.GroupMetadataManager\$OffsetsMessageFormatter"` — reading the
      internal topic by hand. `[CLI]` `[DIAG]`
3.5.6 **`offsets.retention.minutes` = 10080** and the exact rule: the clock starts when the group
      becomes **empty**, not at the commit. This is the mechanism behind "our consumer restarted
      after a long weekend and replayed everything / skipped everything".
      `[CFG]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.5.7 The new coordinator (KIP-848): a state machine per group replicated through the same topic,
      computing target assignments server-side and reconciling members incrementally via
      `ConsumerGroupHeartbeat`. `[RESEARCH]`
3.5.8 KIP-1263 assignment batching and KIP-1196 `group.coordinator.append.max.buffer.size` as the
      4.2/4.3 scaling work on the coordinator. `[CFG]` `[RESEARCH]`
3.5.9 The share-group state topic (`__share_group_state`) and the share coordinator, plus 4.2's
      adaptive batching (KIP-1224) which removed the 5 ms linger floor. `[RESEARCH]`
3.5.10 What the group coordinator does **not** do: it does not track per-message state, does not
      know whether you processed anything, and does not detect a consumer that polls but never
      works. `[TRAP]`
3.5.11 Manual offset manipulation as an operational tool: `kafka-consumer-groups.sh
      --reset-offsets --to-earliest|--to-latest|--to-offset|--shift-by|--to-datetime|
      --by-duration --execute`, which requires the group to be **empty**. `[CLI]` `[TRAP]`
3.5.12 External offset storage as the historical alternative, and why it is a bad idea now.

## §3.6 Kafka producer client internals

3.6.1 The two-thread design: the application thread calling `send()`, and the single background
      **Sender** (`kafka-producer-network-thread`) doing all the I/O. `[SOURCE]`
3.6.2 `send()` step by step: serialise key and value → fetch/await cluster metadata (blocking up to
      `max.block.ms`) → run the partitioner → append into the `RecordAccumulator` → return a
      `Future`. `[FLOW]`
3.6.3 **`RecordAccumulator`** — a `ConcurrentMap<TopicPartition, Deque<ProducerBatch>>` over a
      `BufferPool` of `batch.size`-sized buffers, so allocation is pooled rather than per record.
      `[SOURCE]` `[PROVE]`
3.6.4 `BufferPool` exhaustion: `send()` blocks for up to `max.block.ms` and then throws
      `TimeoutException` (historically `BufferExhaustedException`). This is the producer's only
      backpressure. `[PROVE]` `[TRAP]`
3.6.5 The Sender's drain loop: find ready nodes (batch full, or `linger.ms` elapsed, or flushing,
      or the accumulator is out of memory), drain one batch per partition per node, group into one
      `ProduceRequest` per node, and respect
      `max.in.flight.requests.per.connection`. `[FLOW]` `[PROVE]`
3.6.6 KIP-782 expandable batches, and why `batch.size` is an initial allocation rather than a hard
      cap. `[RESEARCH]`
3.6.7 **The sticky partitioner** (KIP-480): for null keys, stick to one partition until the batch
      is sent, then pick another. This is why "null key = round robin per record" is wrong, and
      why enabling it improved p99 latency dramatically. `[PROVE]` `[VERSION-TRAP]`
3.6.8 Adaptive partitioning: `partitioner.adaptive.partitioning.enable` weighting partitions by
      broker responsiveness, and `partitioner.availability.timeout.ms`. `[CFG]` `[RESEARCH]`
3.6.9 **Idempotence internals**: `InitProducerId` returns a `producerId` (PID) and epoch; each
      batch carries a base sequence number per partition; the broker keeps the last 5 batches'
      metadata per PID per partition and rejects `DuplicateSequenceException` /
      `OutOfOrderSequenceException`. That "5" is exactly why
      `max.in.flight.requests.per.connection ≤ 5`. `[PROVE]` `[NUM]` `[SOURCE]`
3.6.10 `OutOfOrderSequenceException` as a **fatal** error that requires a new producer, and why it
      is the symptom of a lost batch on the broker. `[TRAP]`
3.6.11 The retry path and why in-order retry is preserved: the accumulator re-inserts the failed
      batch at the **head** of the deque and blocks later batches for that partition.
      `[PROVE]` `[SOURCE]`
3.6.12 `delivery.timeout.ms` as the true end-to-end producer deadline covering batching, retries
      and in-flight time, and the exact expiry point. `[PROVE]`
3.6.13 Callback execution happens **on the Sender thread** — blocking in a callback stalls all
      production. `[TRAP]`
3.6.14 `flush()` semantics: block until every buffered record has completed, and 4.1's deadlock
      protection against calling it from a callback. `[API]` `[RESEARCH]`
3.6.15 `close(Duration)` versus `close()` and the records you lose by getting it wrong on shutdown.
      `[TRAP]`

## §3.7 Kafka consumer client internals

3.7.1 The single-threaded design and the `ConsumerNetworkClient`: everything happens inside
      `poll()`, including heartbeats under the classic protocol until KIP-62 moved them to a
      background thread. `[PROVE]` `[VERSION-TRAP]`
3.7.2 `poll(Duration)` step by step: maybe rejoin the group → send fetches for assigned partitions
      → wait up to the timeout → return buffered records → possibly auto-commit. `[FLOW]`
3.7.3 The `Fetcher` and its prefetch behaviour: fetches are issued for partitions with no buffered
      data, so `max.poll.records` slices an already-fetched buffer rather than triggering a fetch
      per call. `[PROVE]` `[TRAP]`
3.7.4 Why `max.poll.records` does **not** limit network transfer — `max.partition.fetch.bytes`
      does — and why a large record can therefore blow up the heap despite a small
      `max.poll.records`. `[PROVE]` `[TRAP]` `[X-REF 06]`
3.7.5 The heap arithmetic: `max.partition.fetch.bytes` (1 MB) × assigned partitions × in-flight
      fetches. 24 partitions on one instance is ~24 MB of buffer at minimum. `[NUM]` `[PROVE]`
3.7.6 `max.poll.interval.ms` enforcement: the background heartbeat thread stops sending heartbeats
      (classic) or the member is fenced (KIP-848) once the deadline passes, and the next
      `commitSync` throws `CommitFailedException`. `[PROVE]` `[DIAG]`
3.7.7 The KIP-848 client: a background thread owning the network and a `ConsumerGroupHeartbeat`
      carrying the member epoch and target assignment, with reconciliation callbacks on the
      application thread. `[RESEARCH]`
3.7.8 KIP-1251 member-epoch validation as the fencing mechanism that stops a zombie member from
      committing. `[RESEARCH]`
3.7.9 Offset commit internals: `OffsetCommit` to the coordinator, the leader epoch carried with
      the offset (so a commit against a stale epoch is rejected), and the async callback.
      `[WIRE]`
3.7.10 `wakeup()` and `WakeupException` as the only thread-safe way to interrupt a poll.
      `[API]`
3.7.11 Deserialisation happens on the poll thread, inside `poll()`, **before** your listener sees
      anything — which is why a bad record throws where you cannot catch it and
      `ErrorHandlingDeserializer` exists. `[PROVE]` `[TRAP]`
3.7.12 `pause`/`resume` internals: paused partitions are excluded from fetch requests, so the
      consumer keeps heartbeating while doing no work — the correct slow-down mechanism.
      `[PROVE]`
3.7.13 Spring's container loop mapped onto all of the above: `KafkaMessageListenerContainer`'s
      `ListenerConsumer` run loop, `pollAndInvoke`, the `AckMode` switch, and where
      `DefaultErrorHandler` intercepts. `[SOURCE]` `[API]`

## §3.8 Transaction coordinator internals

3.8.1 `__transaction_state` — the internal compacted topic holding transaction metadata, with its
      own coordinator selected by `hash(transactional.id)`. `[PROVE]`
3.8.2 `InitProducerId` semantics: allocate or fence a PID for the `transactional.id`, **bump the
      epoch**, and abort any in-flight transaction from the previous incarnation. This is zombie
      fencing. `[PROVE]`
3.8.3 The transaction state machine: `Empty` → `Ongoing` → `PrepareCommit`/`PrepareAbort` →
      `CompleteCommit`/`CompleteAbort`. `[TABLE]`
3.8.4 `AddPartitionsToTxn` and `AddOffsetsToTxn` registering participants before any write.
      `[WIRE]`
3.8.5 `EndTxn` → the coordinator writes a prepare record → sends `WriteTxnMarkers` to every
      participating partition leader → writes the complete record. Two-phase commit **inside
      Kafka**. `[FLOW]` `[PROVE]`
3.8.6 **Control records** as the commit/abort markers, occupying offsets that contain no data —
      the reason consumer offsets can jump by more than the record count. `[TRAP]` `[PROVE]`
3.8.7 The `.txnindex` aborted-transaction index that lets a `read_committed` fetch filter aborted
      batches client-side. `[PROVE]`
3.8.8 **LSO computation** and the stall: the LSO is the first offset of the earliest open
      transaction, so a producer that dies mid-transaction blocks every `read_committed` consumer
      of that partition until `transaction.timeout.ms` expires. `[PROVE]` `[TRAP]`
3.8.9 Hanging transactions: the pre-KIP-890 failure where an old producer's write landed after a
      new epoch began, permanently pinning the LSO, and the
      `kafka-transactions.sh --find-hanging` / `--abort` tooling. `[CLI]` `[RESEARCH]`
3.8.10 KIP-890's fix: identify a transaction by `{producerId, epoch}` and verify partition
      membership on every append, plus 4.2's `TransactionVersion` field in `WriteTxnMarkers`
      (KIP-1228). `[RESEARCH]`
3.8.11 KIP-447: `sendOffsetsToTransaction(offsets, ConsumerGroupMetadata)` lets the coordinator
      fence by group generation, which removed the "one producer per input partition" requirement
      and made EOS scale. `[PROVE]` `[RESEARCH]`
3.8.12 KIP-939's 2PC participation: `transaction.two.phase.commit.enable`, no proactive
      timeout-based abort, and `PreparedTxnState` for resuming — the mechanics of letting an
      external coordinator decide Kafka's fate. `[RESEARCH]`
3.8.13 Why EOS costs latency: two extra coordinator round trips per transaction plus a marker write
      per partition, which is why you batch many records per transaction. `[PROVE]`

## §3.9 Log compaction internals

3.9.1 `cleanup.policy` = `delete` (default) | `compact` | `compact,delete`. `[CFG]`
3.9.2 The guarantee compaction makes: **the latest value for every key that was ever written is
      retained**; the log's *tail* is compacted while the *head* (the active segment) is not.
      `[PROVE]`
3.9.3 The log cleaner threads (`log.cleaner.threads`, 1) and the dirty-ratio trigger:
      `min.cleanable.dirty.ratio` (**0.5**) — compaction runs when half the log is uncompacted.
      `[CFG]` `[NUM]` `[RESEARCH]`
3.9.4 The two-pass algorithm: build an offset map of key → highest offset for the dirty section,
      then rewrite the segments keeping only records whose offset matches the map.
      `[PROVE]` `[SOURCE]`
3.9.5 `log.cleaner.dedupe.buffer.size` (134217728) as the offset-map memory, and what happens when
      the key space does not fit — the cleaner does partial passes and never fully converges.
      `[CFG]` `[NUM]` `[TRAP]`
3.9.6 **Tombstones**: a record with a key and a `null` value marks a delete.
      `delete.retention.ms` (**86400000** = 24 hours) is how long the tombstone survives after its
      first cleaning, and the race it protects against — a slow consumer that would otherwise never
      see the delete. `[CFG]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.9.7 `min.compaction.lag.ms` (0) and `max.compaction.lag.ms` (`Long.MAX_VALUE`, minimum raised to
      60000 in 4.0) as the two bounds on when a record may be compacted. `[CFG]` `[VERSION-TRAP]`
3.9.8 **Compaction does not guarantee uniqueness on read**: a consumer reading the head can see
      several versions of the same key. Compaction is eventual, not a constraint. `[TRAP]`
      `[PROVE]`
3.9.9 **Offsets are preserved, not renumbered** — a compacted log has gaps, and any code assuming
      contiguous offsets breaks. `[TRAP]`
3.9.10 What compaction is for: changelog topics, `__consumer_offsets`, CDC snapshots, Kafka Streams
      state restore, and the "current state of every client" topic. `[TABLE]`
3.9.11 A compacted `client-restrictions-state` topic in QuizStakes would be the wrong design, and
      the bible should say why: restrictions must be read live and never projected for a decision
      (scenario § 9.4, invariant 12). `[TRAP]`
3.9.12 `LogCleaner` metrics: `max-dirty-percent`, `cleaner-recopy-percent`, `time-since-last-run-ms`,
      and the dead-cleaner-thread failure that silently stops compaction forever.
      `[METRIC]` `[TRAP]`

## §3.10 Share groups (KIP-932) internals

3.10.1 What a share group is: a group whose members **cooperatively consume the same partitions**,
      with per-record delivery state held by the broker rather than a single offset per partition.
      `[PROVE]` `[RESEARCH]`
3.10.2 The share-partition state machine per record: `Available` → `Acquired` (with an acquisition
      lock and a timeout) → `Acknowledged` | `Released` | `Rejected` | `Archived`.
      `[TABLE]` `[RESEARCH]`
3.10.3 The three acknowledgement types plus 4.2's fourth: `ACCEPT`, `RELEASE`, `REJECT`, and
      **`RENEW`** (KIP-1222) for extending the acquisition lock — the exact analogue of
      `ChangeMessageVisibility`. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
3.10.4 `KafkaShareConsumer` and `share.acknowledgement.mode` = `implicit` | `explicit`.
      `[API]` `[RESEARCH]`
3.10.5 The **share coordinator** and `__share_group_state`, plus 4.2's adaptive batching
      (KIP-1224) removing the 5 ms latency floor. `[RESEARCH]`
3.10.6 Delivery counts and the delivery limit as the poison-message defence, configurable per group
      by KIP-1240 in 4.3. `[CFG]` `[RESEARCH]`
3.10.7 `ShareAcquireMode` (KIP-1206): `batch_optimized` (soft record-count limit) versus
      `record_limit` (strict). `[CFG]` `[RESEARCH]`
3.10.8 Share-partition lag metrics (KIP-1226) and why "lag" means something different when there is
      no single offset. `[METRIC]` `[RESEARCH]`
3.10.9 **What you give up**: ordering. A share group is explicitly out-of-order consumption, which
      is the whole point and the whole cost. `[PROVE]`
3.10.10 The cross-version incompatibility: 4.0 early-access share consumers and 4.1+ share consumers
      cannot talk to each other's brokers. `[VERSION-TRAP]` `[RESEARCH]`
3.10.11 When a share group is genuinely the right answer — long, variable per-record processing
      where partition-count parallelism is the bottleneck (the document-verification vendor call
      at p50 900 ms / p99 38 s) — and when it is not. `[NUM]`
3.10.12 `kafka-share-groups.sh` and `group.type=share` as the operational surface. `[CLI]`

## §3.11 Tiered storage internals

3.11.1 The two tiers: local disk for recent segments, remote object storage for sealed ones.
      `remote.storage.enable` per topic, `remote.log.storage.system.enable` per broker.
      `[CFG]` `[RESEARCH]`
3.11.2 `RemoteStorageManager` and `RemoteLogMetadataManager` as the two pluggable SPIs, with the
      default metadata manager backed by the `__remote_log_metadata` topic. `[API]`
3.11.3 `local.retention.ms` / `local.retention.bytes` versus `retention.ms` / `retention.bytes` —
      the pair that decides how much stays on disk. `[CFG]` `[TRAP]`
3.11.4 The copy path: a rolled segment plus its indexes are uploaded by the copier thread pool
      (`remote.log.manager.copier.thread.pool.size`, **10** since 4.0), then the local copy becomes
      eligible for deletion. `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
3.11.5 The read path: a fetch below the local start offset is served from remote storage, with
      much higher and more variable latency — and **zero-copy is impossible** for those reads.
      `[PROVE]` `[TRAP]`
3.11.6 Why tiered storage changes the retention conversation: 7-year ledger-event retention becomes
      affordable without a 7-year disk bill. Do the arithmetic against 166 GB/week. `[NUM]`
3.11.7 What it does not fix: the local disk still holds the hot window, and a full-history replay
      now costs object-storage GETs and egress. `[X-REF 18]`
3.11.8 4.3's `follower.fetch.last.tiered.offset.enable` (KIP-1023) — bootstrapping a new follower
      from the tiered offset instead of replicating the whole history. `[CFG]` `[RESEARCH]`
3.11.9 KIP-1176 (active-segment tiering) and KIP-1150 (diskless topics) as the direction of travel,
      and the honest note that diskless removes the page cache that made Kafka fast in the first
      place. `[RESEARCH]`
3.11.10 `remote.log.manager.thread.pool.size` (**2** since 4.0, was 10),
      `remote.log.manager.expiration.thread.pool.size` (10), and 4.2's
      `remote.log.manager.follower.thread.pool.size`. `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`

## §3.12 RabbitMQ internals

3.12.1 The Erlang/OTP process model: one Erlang process per queue, per connection and per channel,
      preemptively scheduled, which is why RabbitMQ degrades gracefully under thousands of queues
      and badly under millions. `[PROVE]`
3.12.2 Classic queue v2 (CQv2) storage: the message store, the queue index, and the removal of the
      lazy/normal distinction. CQv1 was **removed entirely in 4.3**. `[VERSION-TRAP]`
      `[RESEARCH]`
3.12.3 Quorum queues on **Ra**, RabbitMQ's Raft implementation: the WAL, segment files, snapshots,
      and the fact that every enqueue is a Raft log entry replicated to a majority before the
      publisher confirm. `[PROVE]` `[RESEARCH]`
3.12.4 Why a quorum queue's publish latency has a floor: one disk fsync plus one network round trip
      to a majority. `[PROVE]`
3.12.5 Checkpointing and sub-linear recovery on node startup (4.0), recovery snapshots and snapshot
      throttling (4.3). `[RESEARCH]`
3.12.6 Ra 3.x in RabbitMQ 4.3: strict priority queues, per-priority counts, priority-aware
      expiration, delayed retry, and consumer timeout with protocol-specific handling.
      `[RESEARCH]`
3.12.7 **Khepri** internals: a Raft-replicated tree store for metadata, replacing Mnesia's
      eventually-consistent, partition-tolerant-but-inconsistent model with a
      majority-required-but-correct one. The availability trade stated plainly. `[PROVE]`
      `[RESEARCH]`
3.12.8 The credit-based flow-control chain: publisher → channel → queue → message store, with each
      stage granting credit to the previous one. This is real end-to-end backpressure and it is
      why a slow disk blocks a publisher. `[PROVE]`
3.12.9 Memory and disk alarms as the coarse fallback: `vm_memory_high_watermark` (0.6 of system
      memory by default) and `disk_free_limit`. When they fire, publishers are blocked, not
      throttled. `[CFG]` `[NUM]` `[DIAG]`
3.12.10 The **fanout exchange routing optimisation** in 4.2 (up to 42% throughput gain) and gradual
      leadership transfer for large quorum-queue clusters. `[RESEARCH]`
3.12.11 Stream storage internals: segment files, an offset index, non-destructive reads, and the
      dedicated stream protocol's use of `sendfile` — Kafka's design arriving in RabbitMQ.
      `[PROVE]`
3.12.12 4.2's **SQL filter expressions** for AMQP 1.0 stream consumers as broker-side filtering
      that saves network rather than CPU. `[RESEARCH]`
3.12.13 Message interceptors (4.2) as an internal extension point across AMQP 0-9-1, AMQP 1.0,
      MQTT 3 and MQTT 5. `[RESEARCH]`
3.12.14 What `rabbitmq-queues quorum_status` and `rabbitmq-diagnostics observer` actually show, read
      field by field. `[CLI]` `[DIAG]`

## §3.13 SQS internals, as far as they are observable

3.13.1 The published architecture: messages are stored redundantly across multiple servers in
      multiple availability zones, and `ReceiveMessage` samples a subset of servers. That single
      fact explains short-polling empty responses, best-effort ordering, and duplicate delivery all
      at once. `[PROVE]`
3.13.2 Why standard SQS cannot promise ordering: there is no single serialisation point, by design,
      which is exactly what buys the unlimited throughput. `[PROVE]`
3.13.3 Why duplicates happen even without a visibility-timeout overrun: a `DeleteMessage` that was
      applied but whose response was lost. `[PROVE]`
3.13.4 The FIFO partition model: a FIFO queue is internally partitioned, message groups map onto
      partitions, and the 300 TPS figure is per partition — which is what high-throughput mode
      exposes. `[PROVE]` `[NUM]` `[RESEARCH]`
3.13.5 The fair-queues mechanism: SQS tracks per-group in-flight share and biases dispatch toward
      quiet groups. It is a **dispatch** change, not a storage change, which is why no consumer
      change is needed. `[PROVE]` `[RESEARCH]`
3.13.6 The obscure standard-queue behaviour: with `maxReceiveCount > 3`, a message received 3+
      times moves to the **back** of the queue, which changes what
      `ApproximateAgeOfOldestMessage` is measuring. `[TRAP]` `[RESEARCH]`
3.13.7 The DLQ enqueue-timestamp rule: preserved on standard queues, reset on FIFO — with the
      arithmetic worked (1 day in the source + a 4-day DLQ retention = 3 days left).
      `[NUM]` `[PROVE]` `[RESEARCH]`
3.13.8 Why `ApproximateNumberOfMessages*` is approximate, and what "eventually consistent metrics"
      means for an alert threshold. `[METRIC]` `[TRAP]`
3.13.9 The receipt handle as an opaque, per-receive token, and what that implies for storing work
      state across a restart. `[TRAP]`
3.13.10 The billing model as an internals fact: requests are billed in 64 KB chunks, so a 256 KB
      message is 4 requests. `[NUM]`

## §3.14 The proofs and impossibility results

3.14.1 **The two generals problem** — worked properly, with the induction showing no finite
      protocol establishes common knowledge over a lossy channel, and the conclusion that
      acknowledgement is always uncertain. `[PROVE]`
3.14.2 **Why exactly-once delivery is therefore impossible**, and the precise sense in which
      exactly-once *processing* escapes the result (it changes the effect, not the delivery).
      `[PROVE]`
3.14.3 **FLP impossibility** — no deterministic consensus in an asynchronous system with one
      faulty process — and why Raft/KRaft/Ra are legal anyway (partial synchrony + randomised
      timeouts). `[PROVE]` `[X-REF 22]`
3.14.4 **Total order broadcast is equivalent to consensus**, which is the formal reason global
      ordering is expensive and per-partition ordering is cheap. `[PROVE]`
3.14.5 **Ordering versus throughput is a hard trade**, proved: any total order requires a single
      sequencer, whose throughput bounds the system. `[PROVE]`
3.14.6 **The dual-write impossibility**: without a common transaction coordinator, no protocol
      makes a DB write and a broker publish atomic, which is why the outbox exists. `[PROVE]`
3.14.7 **Amortised analysis of the outbox relay**: per-event cost is one extra row insert plus an
      amortised share of a batched publish, so the outbox is O(1) additional work per event, not
      O(n). `[PROVE]`
3.14.8 **The at-least-once + idempotence = effectively-once argument**, stated as a theorem with
      the two required conditions (a stable id, and atomicity of the dedup record with the effect).
      `[PROVE]`
3.14.9 **The lock-safety impossibility**: under arbitrary process pauses, no TTL-based lock is both
      safe and live; fencing tokens move the safety requirement to the resource, which is the only
      construction that works. `[PROVE]`
3.14.10 **Little's Law applied to a queue**: `L = λW`, so backlog = arrival rate × dwell time. Use
      it to derive the required consumer count from a latency SLA — 1,200 msg/s at a 150 ms budget
      needs 180 concurrent in-process messages. `[PROVE]` `[NUM]`
3.14.11 **Queueing theory's utilisation curve**: latency grows as `1/(1-ρ)`, so a consumer pool at
      90% utilisation has 10× the queueing delay of one at 50%. This is the arithmetic behind
      "never size for the average". `[PROVE]` `[NUM]`
3.14.12 **The recovery-time formula**: with arrival rate λ, drain rate μ and an outage of length T,
      catch-up time is `λT / (μ − λ)`, undefined when `μ ≤ λ`. Worked for the 8.64M-message
      backlog. `[PROVE]` `[NUM]`
3.14.13 **Why `min.insync.replicas = ⌈(RF+1)/2⌉` is the durability sweet spot**, argued from the
      overlap of any two quorums. `[PROVE]` `[X-REF 22]`
3.14.14 **Why the retry-amplification factor is `∏(1 + rᵢ)` across layers**, not the sum.
      `[PROVE]` `[NUM]`

## §3.15 The failure-mode catalogue

3.15.1 **Consumer outage** — depth up, DLQ flat, retention the real risk. Detection, mitigation,
      recovery. `[TABLE]`
3.15.2 **Poison message** — DLQ climbing, one partition stalled. Detection via DLQ depth and
      per-partition lag.
3.15.3 **Rebalance loop** — group "up", lag frozen, `CommitFailedException` in the logs.
3.15.4 **Hot partition** — lag on one partition only, uneven CPU across instances.
3.15.5 **Slow consumer / head-of-line blocking** — dwell time up with depth flat.
3.15.6 **Retry storm / redelivery storm** — receive-count distribution shifting right, downstream
      error rate climbing with load.
3.15.7 **Unclean leader election** — `UncleanLeaderElectionsPerSec > 0`; committed data gone.
      The fintech incident shape: `unclean.leader.election.enable=true` during a datacentre outage
      producing unreconciled payment events. `[RESEARCH]`
3.15.8 **Under-replicated partitions** — a broker down, a slow disk, or a network partition;
      `acks=all` producers start failing with `NotEnoughReplicas`.
3.15.9 **Hanging transaction** — `read_committed` consumers stuck at the LSO with the producers
      apparently healthy.
3.15.10 **Offset expiry** — a group empty past `offsets.retention.minutes`, then a silent skip or a
      full replay. `[TRAP]`
3.15.11 **Disk full** — the broker shuts down the log dir or the whole broker; on RabbitMQ the disk
      alarm blocks every publisher instead.
3.15.12 **Replication-slot stall** (CDC) — Debezium stopped, WAL retained, primary disk fills.
      `[X-REF 09]`
3.15.13 **Visibility-timeout overrun** — genuine concurrent duplicate processing, not just a
      duplicate.
3.15.14 **Schema-incompatible deploy** — every consumer instance crash-looping on deserialisation.
3.15.15 **Serialisation-format drift** — a producer switching from JSON to Avro without a
      dual-read window.
3.15.16 **Queue-depth-driven autoscaling oscillation**.
3.15.17 **The whale client** — one `clientId` producing a disproportionate share of stake events,
      pinning one partition and one ledger instance.
3.15.18 **Split brain** — two ledger instances both believing they own a client's partition; both
      authorise a stake (scenario § 15.2).
3.15.19 **Clock skew** — self-exclusion timestamped by one service and the stake by another;
      "which came first" is unanswerable.
3.15.20 **Duplicate file submission** — the bank accepting the same payout file twice
      (scenario § 13.4).
3.15.21 **Orphaned reservation** — the black box never settles; funds held indefinitely; ageing out
      too early lets the client stake the same money twice.
3.15.22 **The chaos question** to close on: kill the ledger between the bonus leg and the cash leg
      of a stake — what detects it, and how fast? (Scenario § 15.5.)

## §3.16 Memory, footprint and cost arithmetic

3.16.1 Broker memory: a small JVM heap (6 GB) plus everything else to the page cache; per-partition
      overhead for the active segment buffer, the index mmap, and the replica fetcher state.
      `[NUM]` `[X-REF 06]`
3.16.2 Per-partition disk overhead: an active segment allocation plus a 10 MB index preallocation
      per segment, which is why 10,000 tiny partitions cost real disk. `[NUM]`
3.16.3 Producer memory: `buffer.memory` (32 MB) plus compression buffers plus in-flight request
      buffers. `[NUM]`
3.16.4 Consumer memory, worked: `max.partition.fetch.bytes` × partitions × in-flight fetches, plus
      the deserialised object graph for `max.poll.records`. 500 records × 400 bytes is trivial;
      500 records × 900 KB documents is 450 MB and an OOM. `[NUM]` `[PROVE]` `[X-REF 06]`
3.16.5 Spring container memory: `concurrency=N` multiplies all of the above by N in one JVM.
      `[TRAP]`
3.16.6 Dedup-table footprint: 19.8M rows/day × 7 days × (16-byte UUID + overhead) ≈ 139M rows,
      several GB with the index. Plan the cleanup job. `[NUM]`
3.16.7 Outbox footprint and the delete-versus-partition decision at 19.8M rows/day.
      `[X-REF 09]`
3.16.8 Cost comparison at QuizStakes' volume: SQS at ~$0.40/million requests for 19.8M events/day
      (with and without batching by 10) versus a 3-broker MSK cluster's fixed monthly cost. Show
      both numbers and the crossover. `[NUM]` `[PROVE]` `[X-REF 18]`
3.16.9 Cross-AZ data transfer as the hidden Kafka bill, and `client.rack` as the mitigation.
      `[NUM]`
3.16.10 The document-image case: 24k uploads/day × 2–6 MB = 68 GB/day, which must never touch a
      broker — claim check only. `[NUM]`

## §3.17 Version history — what changed and why

3.17.1 Kafka 0.8 replication, 0.9 the new consumer and the group coordinator, 0.10 timestamps and
      the `.timeindex`, 0.11 the v2 record batch + idempotent producer + transactions (KIP-98).
      `[TABLE]`
3.17.2 Kafka 1.x–2.x: `DeleteRecords`, KIP-101 leader epochs, KIP-320 offset leader epochs,
      KIP-345 static membership, KIP-392 follower fetching.
3.17.3 Kafka 2.4–2.8: KIP-429 incremental cooperative rebalancing, KIP-447 scalable EOS, KIP-480
      sticky partitioner, KIP-500 KRaft's early access.
3.17.4 Kafka 3.0: `enable.idempotence` and `acks=all` become the producer defaults —
      the single most-missed default change. `[VERSION-TRAP]`
3.17.5 Kafka 3.3 KRaft production-ready; 3.5 the migration path; 3.9 tiered storage GA and the last
      ZooKeeper release.
3.17.6 Kafka 4.0 (Mar 2025): ZooKeeper removed, KRaft only, KIP-848 GA, KIP-932 early access,
      KIP-966 ELR preview, KIP-1030 default changes (`linger.ms` 0 → 5), message formats v0/v1
      removed, KIP-896 old protocol versions removed, Java 11/17 floors, Log4j2.
      `[VERSION-TRAP]`
3.17.7 Kafka 4.1 (Sep 2025): KIP-932 preview, KIP-1071 Streams rebalance protocol early access,
      `Monitorable` plugin metrics, OAuth jwt-bearer, `Consumer.close(CloseOptions)`, producer
      `flush()` deadlock protection. `[RESEARCH]`
3.17.8 Kafka 4.2 (Feb 2026): share groups **production-ready**, `RENEW` acknowledgement
      (KIP-1222), `ShareAcquireMode` (KIP-1206), adaptive coordinator batching (KIP-1224), share
      lag metrics (KIP-1226), Streams DLQ in exception handlers (KIP-1034), metric renaming to
      `kafka.COMPONENT` (KIP-1100), Java 25 support. `[RESEARCH]`
3.17.9 Kafka 4.3 (May 2026): 25 KIPs — tiered-offset follower bootstrap (KIP-1023), log-dir
      cordoning (KIP-1066), share-group configs (KIP-1240), classic-rebalance-protocol deprecation
      warnings (KIP-1274), Streams header preservation (KIP-1271/1285), OAuth client assertion
      (KIP-1258). `[RESEARCH]`
3.17.10 What is coming and should be named as *not yet available*: KIP-1150 diskless topics,
      KIP-1176 active-segment tiering, KIP-1255 remote read replicas, and the removal of the
      classic rebalance protocol in 5.0. `[RESEARCH]`
3.17.11 RabbitMQ 3.8 quorum queues introduced; 3.9 streams; 3.13 the last release with classic
      mirrored queues. `[TABLE]`
3.17.12 RabbitMQ 4.0 (Sep 2024): classic mirroring removed, AMQP 1.0 core and 2× faster, quorum
      queue priorities, sub-linear recovery via checkpoints, `x-delivery-limit` default 20.
      `[VERSION-TRAP]`
3.17.13 RabbitMQ 4.1 (Apr 2025), 4.2 (Oct 2025): Khepri default, SQL filter expressions for streams,
      message interceptors, cluster-aware Shovel, AMQP 1.0 direct reply-to, fanout routing
      optimisation. `[RESEARCH]`
3.17.14 RabbitMQ 4.3 (Apr 2026): Mnesia removed entirely, CQv1 removed, `x-modulus-hash` in core,
      Ra 3.x with strict priorities and delayed retry, non-durable non-exclusive queues disabled by
      default, `rabbitmqadmin` v1 endpoint removed. `[VERSION-TRAP]` `[RESEARCH]`
3.17.15 SQS history: 2006 launch, FIFO queues 2016, high-throughput FIFO 2021, DLQ redrive API
      2023, **1 MiB payloads Aug 2025**, **fair queues 2025**, **FIFO in-flight limit raised to
      120,000**. `[VERSION-TRAP]` `[RESEARCH]`
3.17.16 SNS history: FIFO topics 2020, message filtering on the body 2022, archive-and-replay for
      FIFO topics 2023, FIFO-to-standard-SQS delivery 2023, EventBridge SQS fair-queue targets
      Nov 2025. `[RESEARCH]`
3.17.17 JMS 1.1 → JMS 2.0 (`JMSContext`, shared subscriptions, delivery delay, async send) →
      Jakarta Messaging 3.0 (the `javax`→`jakarta` rename) → 3.1 (pruning the optional chapters).
      `[VERSION-TRAP]`
3.17.18 Spring for Apache Kafka 2.7 (`@RetryableTopic`), 2.8 (`DefaultErrorHandler` replacing
      `SeekToCurrentErrorHandler`), 3.0 (Boot 3, Jakarta), 3.2 (class-level `@KafkaListener`),
      4.0 (Kafka 4 client, share consumers, Spring Retry removed, Jackson 3, ZooKeeper test support
      removed), 4.1 (Jun 2026). `[VERSION-TRAP]` `[RESEARCH]`
3.17.19 Spring AMQP 3.x → 4.0 (Nov 2025): the `spring-rabbitmq-client` AMQP 1.0 module, Jackson 3,
      JSpecify nullability, Spring core retry — and Boot's starter split. `[RESEARCH]`
3.17.20 Debezium 2.x → 3.3 (Oct 2025) and the Quarkus outbox extension's Hibernate 7 compatibility.
      `[RESEARCH]`

---

# PART 4 — BUILD IT

Every item here ships **complete, compiling, generic Java 21** (or a complete SQL/YAML artifact
where that is the artifact) and is followed by a **Diff vs the real one** table covering: what the
real implementation does that this does not, why it bothers, and what breaks first at scale.

4.1 **`InMemoryQueueBroker`** — a single-node queue with `send`, `receive(maxMessages,
    visibilityTimeout)`, `delete(receiptHandle)`, `changeVisibility`, `maxReceiveCount` and a DLQ.
    A `DelayQueue` for the visibility timers, a `ConcurrentHashMap` of in-flight entries, and a
    per-receive receipt handle. This is SQS's semantics in 200 lines. `[BUILD]`
4.1.1 Diff vs Amazon SQS: multi-AZ redundancy, sampled receives, approximate metrics, the
    64 KB billing chunk, IAM, KMS, fair-queue dispatch bias, and the 120,000 in-flight ceiling.
    `[TABLE]`

4.2 **`SegmentedLog`** — an append-only log with a base-offset-named active segment, a roll at
    `segmentBytes`, a **sparse offset index** written every `indexIntervalBytes`, binary search over
    the index followed by a linear scan, `read(offset, maxBytes)`, and time-based retention that
    deletes only sealed segments. `[BUILD]`
4.2.1 Diff vs Kafka's `Log`/`LocalLog`: memory-mapped indexes, the `.timeindex`, the leader-epoch
    checkpoint, CRC32C per batch, `sendfile` zero-copy, the recovery path, the transaction index,
    preallocation, and `FileRecords`. `[TABLE]`

4.3 **`RecordBatchCodec`** — encode and decode the Kafka v2 record batch header (base offset, CRC,
    attributes, producer id/epoch/base sequence, delta offsets, varint records) against a
    `ByteBuffer`, with a round-trip test. `[BUILD]`
4.3.1 Diff vs `DefaultRecordBatch`: compression codecs, the control-record flag, down-conversion,
    the `Records` abstraction, and zero-copy slicing. `[TABLE]`

4.4 **`ConsumerGroupCoordinator`** — group membership, generation ids, heartbeat expiry, and
    pluggable assignors implementing `range`, `round-robin`, `sticky` and `cooperative-sticky` over
    `(members, partitions)`. Prove that sticky minimises movement on a single-member departure.
    `[BUILD]` `[PROVE]`
4.4.1 Diff vs the real coordinator: `__consumer_offsets` persistence, the KIP-848 server-side
    reconciliation loop, member epochs and fencing, static membership, rack awareness, and the
    protocol negotiation. `[TABLE]`

4.5 **`IdempotentConsumer<T>`** — a generic wrapper taking an event-id extractor and a
    `Consumer<T>`, inserting into `processed_events` and running the effect inside one
    `@Transactional`, with the `DuplicateKeyException` short-circuit and a scheduled cleanup of
    rows older than the redelivery window. Full DDL plus a Spring Boot 3.x/4.x handler for
    `LedgerMovementPosted`. `[BUILD]` `[SQL]`
4.5.1 Diff vs a framework implementation (Eventuate Tram, Axon's `DeadlineManager`, Spring
    Integration's `MetadataStore` idempotent receiver): storage abstraction, per-consumer scoping,
    metrics, and TTL management. `[TABLE]`

4.6 **`TransactionalOutbox`** — the DDL with the partial index, an `OutboxEvent` record, a
    `@Transactional` service that writes `accountmaintenance.account` and the outbox row together,
    and a `OutboxRelay` polling with `FOR UPDATE SKIP LOCKED`, publishing in a batch, marking
    published, and exporting a lag metric. Runnable against PostgreSQL. `[BUILD]` `[SQL]`
4.6.1 Diff vs Debezium + the `EventRouter` SMT: no polling load, WAL-level completeness, ordering
    by LSN, snapshotting, the replication-slot hazard, schema handling, and multi-table routing.
    `[TABLE]`

4.7 **`RetryTopicChain`** — a hand-rolled non-blocking retry: publish to `payments.retry.<delay>`
    with a `retry-due-at` header, a retry consumer that pauses the partition until the due time,
    an attempt counter, and a terminal DLT publish that carries the exception, the attempt count
    and the original coordinates. `[BUILD]`
4.7.1 Diff vs `@RetryableTopic`: topic auto-provisioning, `DestinationTopicResolver`,
    `SameIntervalTopicReuseStrategy`, `KafkaBackOffException` handling, container-factory wiring,
    exception classification and DLT strategies. `[TABLE]`

4.8 **`BackoffPolicy`** — full, equal and decorrelated jitter as an interface with three
    implementations, plus a simulation harness that shows the retry-arrival histogram for 5,000
    simultaneously-failed messages under each policy. `[BUILD]` `[PROVE]`
4.8.1 Diff vs Resilience4j `IntervalFunction` and Spring's `ExponentialBackOff`: max elapsed time,
    the `BackOffExecution` contract, and integration with the retry registry. `[TABLE]`

4.9 **`FencedDistributedLock`** — acquire with `SET NX PX` (or a SQL upsert), a monotonically
    increasing **fencing token**, a watchdog thread renewing the TTL, compare-and-delete release
    via a Lua script, and a `FencedResource` that rejects writes bearing a stale token. Then a
    test that *forces* the stale-holder scenario and shows the fence rejecting it. `[BUILD]`
    `[PROVE]`
4.9.1 Diff vs ShedLock and Redisson: storage backends, `lockAtMostFor`/`lockAtLeastFor`, the
    Spring `@SchedulerLock` integration, watchdog defaults, and the honest note that neither
    provides fencing tokens. `[TABLE]`

4.10 **`SagaOrchestrator`** — a persisted state machine for the card-deposit saga (restriction
    check → limit check → authorise → capture → ledger credit → bonus grant) with per-step
    idempotency keys, per-step timeouts, compensation handlers, and the pivot step marked so
    everything after it is retry-only. Includes the SQL for the saga-instance table. `[BUILD]`
    `[SQL]`
4.10.1 Diff vs Temporal / Step Functions / Camunda: durable execution, replay-based recovery,
    versioning of in-flight workflows, visibility tooling, and timers as first-class state.
    `[TABLE]`

4.11 **`BoundedBridge<T>`** — a backpressure-preserving bridge from a poll loop to a worker pool:
    an `ArrayBlockingQueue` of known capacity, a `Semaphore` sized to it, container `pause()` when
    the permits run out and `resume()` when they free up, and an ordering-preserving mode keyed by
    partition. `[BUILD]` `[X-REF 05]`
4.11.1 Diff vs Reactor Kafka / Spring's `ContainerProperties` pause support and virtual-thread
    executors: demand propagation, `request(n)`, and what each one does on shutdown. `[TABLE]`

4.12 **`ConsumerLagExporter`** — an `AdminClient`-based exporter computing per-partition lag
    (`listOffsets(LATEST)` minus `listConsumerGroupOffsets`), converting it to **lag-seconds**
    using the measured arrival rate, and publishing both as Micrometer gauges. `[BUILD]`
    `[METRIC]`
4.12.1 Diff vs Burrow and `kafka_exporter`: evaluation windows, sliding-window status rules,
    handling of empty groups, and multi-cluster support. `[TABLE]`

4.13 **`DlqReplayTool`** — a CLI that reads a DLT/DLQ, filters by exception type or time range,
    optionally transforms, republishes to the original topic with a `replayed-from` header, records
    what it replayed, and is safely re-runnable. `[BUILD]` `[CLI]`
4.13.1 Diff vs `StartMessageMoveTask` (SQS) and RabbitMQ Shovel: server-side execution, rate
    control, cancellation and the absence of transformation. `[TABLE]`

4.14 **`ClaimCheckSerializer`** — a `Serializer`/`Deserializer` pair that transparently offloads
    payloads above a threshold to object storage and substitutes a reference, with the reference
    envelope, a TTL alignment against message retention, and a cleanup story. Sized for the 2–6 MB
    document images. `[BUILD]` `[NUM]`
4.14.1 Diff vs the Amazon SQS Extended Client Library: `S3Pointer` format, the 2 GB ceiling,
    `deleteMessage` cleanup semantics, and its sync-only limitation. `[TABLE]`

4.15 **`WebhookIngestEndpoint`** — a Spring Boot 3.x/4.x controller for PSP capture callbacks:
    constant-time HMAC signature verification, a replay-window timestamp check, persistence of the
    raw body, an outbox insert, and a 200 within milliseconds — with all processing asynchronous.
    `[BUILD]` `[X-REF 12]` `[X-REF 13]`
4.15.1 Diff vs Standard Webhooks / a managed ingest: retry semantics from the sender's side,
    signature-scheme negotiation, and endpoint rotation. `[TABLE]`

4.16 **`ShareGroupWorker`** — a `KafkaShareConsumer` worker with explicit acknowledgement mode,
    `ACCEPT`/`RELEASE`/`REJECT` decisions driven by the exception taxonomy, and a `RENEW` heartbeat
    for long-running work. Requires Kafka ≥ 4.2. `[BUILD]` `[VERSION-TRAP]`
4.16.1 Diff vs a classic consumer group and vs an SQS worker: ordering, the acquisition-lock
    timeout, delivery-count-based dead-lettering, and the partition-count ceiling that disappears.
    `[TABLE]`

4.17 **`OutboxToRabbitRelay`** — the same outbox relay against AMQP: publisher confirms with a
    `ConfirmCallback`, mandatory publishing with a `ReturnsCallback`, and marking published only on
    a positive confirm. Shows why the AMQP version needs *two* callbacks to be correct.
    `[BUILD]` `[PROVE]`
4.17.1 Diff vs `RabbitTemplate`'s `CorrelationData` future-based confirms and `spring-rabbitmq-client`'s
    AMQP 1.0 disposition handling. `[TABLE]`

4.18 **`MessagingTestKit`** — a Testcontainers-based test class proving three properties for one
    consumer: (1) processing the same event twice produces one effect; (2) a poison record lands in
    the DLT with the exception header set; (3) a consumer restart mid-batch reprocesses rather than
    skipping. Uses `KafkaContainer`, awaitility, and `@EmbeddedKafka` as the lightweight
    alternative. `[BUILD]` `[X-REF 16]`
4.18.1 Diff vs `@EmbeddedKafka`/`EmbeddedKafkaKraftBroker`: startup cost, KRaft-only behaviour,
    version fidelity, and what an embedded broker cannot reproduce (rebalances under real network
    failure, unclean elections). `[TABLE]`

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "Consumers have been down for three hours — where are the messages?" The complete answer,
      including depth, disk, retention and the DLQ being flat. `[TABLE]`
5.1.2 "A message is in the DLQ. What do you know for certain?"
5.1.3 "Explain the delivery semantics and which one you'd pick."
5.1.4 "Is exactly-once possible?" — the delivery/effect split, the two-generals reason, and what
      Kafka's EOS actually covers.
5.1.5 "How do you make a consumer idempotent?" — the event id, the same transaction, and the ranked
      alternatives.
5.1.6 "How do you guarantee ordering?" — per-partition only, key choice, and the throughput cost.
5.1.7 "Kafka or SQS for this?" — the six-question procedure from §2.1.2.
5.1.8 "You need to publish an event and write to the database atomically." — the outbox, and why
      `@Transactional` and `afterCommit` do not work.
5.1.9 "Your consumer lag is growing. Walk me through the diagnosis." — a decision tree from lag
      shape to root cause. `[FLOW]`
5.1.10 "How many partitions?" — the arithmetic, the ceiling, and the cost of too many.
5.1.11 "What happens during a rebalance, and why is your group consuming nothing?"
5.1.12 "How do you handle a poison message?" — classify, do not retry, DLQ with context, alert,
      replay.
5.1.13 "Design a retry strategy for a flaky third-party call." — classification, backoff with
      jitter, non-blocking retry, budget, circuit breaker.
5.1.14 "How would you replay three days of events after a bug?" — offset reset, a new group, the
      idempotency prerequisite, and the downstream-load problem.
5.1.15 "Your scheduled job runs three times." — idempotency first, lock second, the fencing token,
      and partitioning as the scalable answer.
5.1.16 "Explain backpressure and where it is missing in your system."
5.1.17 "Can you lose a message with Kafka?" — the ten-way enumeration from §3.3.15.
5.1.18 "What is `acks=all` actually promising?" — and the `min.insync.replicas` follow-up.
5.1.19 "Why is Kafka fast?" — sequential I/O, page cache, zero-copy, batching, compression, and the
      binary protocol — plus what disables each.
5.1.20 "Difference between a queue and a log?" — post-consumption fate, and everything downstream
      of it.
5.1.21 "When would you not use a message broker?"
5.1.22 "Design an event-driven order/payment pipeline." — the QuizStakes card-deposit flow as the
      answer, with the outbox, the saga, the idempotency and the DLQ all placed.
5.1.23 "Kafka vs RabbitMQ vs SQS in one minute." `[TABLE]`
5.1.24 "How do you evolve an event schema without breaking consumers?"
5.1.25 "What is head-of-line blocking and how do you avoid it?"
5.1.26 "How do you monitor a messaging system?" — the four questions and the alert set.
5.1.27 "What is a hot partition and how do you fix it?"
5.1.28 "How does Kafka do exactly-once, mechanically?" — PID, epoch, sequence numbers, control
      records, LSO.
5.1.29 "What did Kafka 4.0 change?" — the KRaft/KIP-848/defaults answer, which is the
      currency-check question. `[VERSION-TRAP]`
5.1.30 "Kafka now has queues — what changed?" — share groups, and the ordering you trade away.
      `[VERSION-TRAP]`
5.1.31 "Your DLQ has 100,000 messages. What do you do, in order?" `[FLOW]`
5.1.32 "The broker is up but nothing is being consumed. Where do you look?" `[FLOW]`

## §5.2 The trap list — every misconception in one place

5.2.1 Consumers down ⇒ DLQ. **No.** `[TRAP]`
5.2.2 `acks=all` alone means durable. **No** — `min.insync.replicas` decides. `[TRAP]`
5.2.3 `min.insync.replicas=3` on an RF=2 topic gives three copies. **No** — silently capped.
      `[TRAP]`
5.2.4 Kafka's exactly-once covers your database write. **No.** `[TRAP]`
5.2.5 More consumers means more throughput. **Only up to the partition count** — and share groups
      are the exception. `[TRAP]`
5.2.6 `auto.offset.reset` decides where you start. **No** — only when no valid offset exists.
      `[TRAP]`
5.2.7 Auto-commit is safe. **No** — timer-based, and unreliable at revocation. `[TRAP]`
5.2.8 Committed offset = last processed. **No** — it is the next offset to read. `[TRAP]`
5.2.9 `max.poll.records` bounds memory. **No** — `max.partition.fetch.bytes` does. `[TRAP]`
5.2.10 Adding partitions is free. **No** — it re-maps keys and breaks per-key ordering.
      `[TRAP]`
5.2.11 A single-partition topic scales. **No** — one active consumer, forever. `[TRAP]`
5.2.12 The broker delivered them in order, so I process them in order. **Not if you hand them to a
      pool.** `[TRAP]`
5.2.13 Producer retries preserve order. **Only with `enable.idempotence=true`.** `[TRAP]`
5.2.14 Compaction guarantees one record per key on read. **No.** `[TRAP]`
5.2.15 Compacted logs have contiguous offsets. **No.** `[TRAP]`
5.2.16 `retention.ms=3600000` means data is gone in an hour. **No** — only sealed segments are
      deleted. `[TRAP]`
5.2.17 Retention uses wall-clock time. **No** — it uses the message timestamp. `[TRAP]`
5.2.18 Kafka fsyncs every write. **No** — durability comes from replication. `[TRAP]`
5.2.19 Offsets live forever. **No** — `offsets.retention.minutes` = 7 days for an empty group.
      `[TRAP]`
5.2.20 `read_committed` is free. **No** — one hung transaction stalls the partition at the LSO.
      `[TRAP]`
5.2.21 `@Transactional` covers `kafkaTemplate.send`. **No.** `[TRAP]`
5.2.22 `afterCommit` solves the dual write. **No** — it shrinks the window. `[TRAP]`
5.2.23 SQS messages are 256 KB. **No — 1 MiB since August 2025.** `[TRAP]` `[VERSION-TRAP]`
5.2.24 SQS FIFO in-flight limit is 20,000. **No — 120,000.** `[TRAP]` `[VERSION-TRAP]`
5.2.25 SQS default retention is 14 days. **No — 4 days.** `[TRAP]` `[VERSION-TRAP]`
5.2.26 Receiving an SQS message deletes it. **No** — it makes it invisible. `[TRAP]`
5.2.27 The receipt handle is stable. **No** — new on every receive. `[TRAP]`
5.2.28 `MessageGroupId` on a standard queue orders messages. **No** — it enables fair queues.
      `[TRAP]` `[VERSION-TRAP]`
5.2.29 FIFO dedup protects you. **Only for 5 minutes.** `[TRAP]`
5.2.30 Short polling is fine at low volume. **No** — it returns empty with messages present.
      `[TRAP]`
5.2.31 Lambda handles partial batch failures automatically. **Only with
      `ReportBatchItemFailures`.** `[TRAP]`
5.2.32 RabbitMQ mirrored queues give you HA. **They were removed in 4.0.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.33 `delivery_mode=2` means the message survives anything. **Not without a durable, replicated
      queue.** `[TRAP]`
5.2.34 An unroutable AMQP message errors. **No** — silently dropped and still confirmed unless you
      publish `mandatory`. `[TRAP]`
5.2.35 Prefetch is a performance knob. **It is also your memory bound, and `0` means unlimited.**
      `[TRAP]`
5.2.36 Publishing to a queue. **You publish to an exchange.** `[TRAP]`
5.2.37 JMS is a protocol. **It is an API.** `[TRAP]`
5.2.38 `Message.acknowledge()` acks one message. **It acks the whole session.** `[TRAP]`
5.2.39 A distributed lock prevents double runs. **It reduces the probability.** `[TRAP]`
5.2.40 Kubernetes `CronJob` with `Forbid` runs exactly once. **At-least-once.** `[TRAP]`
5.2.41 A broker gives you backpressure. **It removes it and converts it into lag.** `[TRAP]`
5.2.42 Retries make a system more resilient. **Unbudgeted retries are a common cause of outages.**
      `[TRAP]`
5.2.43 Idempotent side effect = idempotent handler. **No — the second email still sends.**
      `[TRAP]`
5.2.44 Dedup in Redis is as good as a unique constraint. **It cannot join the transaction.**
      `[TRAP]`
5.2.45 An event id from the broker is stable across redeliveries. **Not necessarily.** `[TRAP]`
5.2.46 Kafka needs ZooKeeper. **Not since 4.0.** `[TRAP]` `[VERSION-TRAP]`
5.2.47 `linger.ms` defaults to 0. **5 since 4.0.** `[TRAP]` `[VERSION-TRAP]`
5.2.48 Rebalances stop the world. **Not under KIP-848.** `[TRAP]` `[VERSION-TRAP]`
5.2.49 Kafka cannot do competing consumers within a partition. **Share groups can, since 4.2.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.50 A `null` key round-robins per record. **The sticky partitioner batches per partition.**
      `[TRAP]`
5.2.51 Unclean leader election is a tuning knob. **Any occurrence is a data-loss event.**
      `[TRAP]`
5.2.52 Restriction state can be cached or projected. **Scenario invariant 12 forbids it — read
      live, every time.** `[TRAP]`

## §5.3 The one-line assertions to recall under pressure

5.3.1 A cheat-sheet block of every constant and default in the file, grouped by system, on one
      screen: Kafka producer, Kafka consumer, Kafka broker/topic, RabbitMQ, SQS. `[TABLE]`
      `[NUM]`
5.3.2 The master cost-and-guarantee table, reproduced. `[TABLE]`
5.3.3 The decision tree from requirement to broker, on one page. `[FLOW]`
5.3.4 The lag-diagnosis decision tree, on one page. `[FLOW]`
5.3.5 The failure-mode → symptom → metric → fix table. `[TABLE]`
5.3.6 The five sentences that carry the whole topic: consuming deletes versus advances a pointer;
      the guarantee follows the ack position; exactly-once delivery is impossible and exactly-once
      effect is not; ordering and throughput are opposed; every buffer bounded with a deliberate
      policy.
5.3.7 A 60-second verbal answer for "tell me how you'd design the async side of a payments
      platform", using QuizStakes end to end.
5.3.8 Twelve self-quiz questions whose answers are numbers, so recall is testable.
      `[NUM]`

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| Apache Kafka 4.0.0 release announcement | https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/ | ZooKeeper removal, KRaft default, KIP-848 GA, KIP-932 early access, KIP-966 ELR, KIP-896 protocol removal, message format v0/v1 removal, Java 11/17 floors, Log4j2, KIP-1030 reference |
| Apache Kafka 4.1.0 release announcement | https://kafka.staged.apache.org/blog/2025/09/04/apache-kafka-4.1.0-release-announcement/ | KIP-932 preview, KIP-1071 Streams rebalance protocol, `Monitorable` metrics, OAuth jwt-bearer, `Consumer.close(CloseOptions)`, `flush()` deadlock protection, deprecations |
| Apache Kafka 4.2.0 release announcement | https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/ | Share groups production-ready, KIP-1222 `RENEW`, KIP-1206 `ShareAcquireMode`, KIP-1224 adaptive batching, KIP-1226 share lag metrics, KIP-1100 metric renaming, KIP-1034 Streams DLQ, KIP-1179 follower thread pool, Java 25 |
| Apache Kafka 4.3.0 release announcement | https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/ | The 4.3 KIP list: KIP-1023 tiered-offset follower bootstrap, KIP-1066 cordoning, KIP-1240 share-group configs, KIP-1274 classic-protocol deprecation, KIP-1251 member-epoch validation, KIP-1258 OAuth client assertion, KIP-1257 retention metrics |
| KIP-1030 (constraints and default values) | https://cwiki.apache.org/confluence/display/KAFKA/KIP-1030%3A+Change+constraints+and+default+values+for+various+configurations | `linger.ms` 0 → 5, `num.recovery.threads.per.data.dir` 1 → 2, `message.timestamp.after.max.ms` → 1 h, remote-log thread-pool defaults, and the new minima for `segment.ms`, `segment.bytes`, `segment.index.bytes`, `max.compaction.lag.ms` |
| Kafka consumer rebalance protocol docs (4.1) | https://kafka.apache.org/41/operations/consumer-rebalance-protocol/ | `group.protocol=consumer`, `group.consumer.session.timeout.ms`, `group.consumer.heartbeat.interval.ms`, `group.consumer.assignors` (`uniform,range`), `group.remote.assignor`, the inert client configs, online/offline upgrade paths, unsupported features |
| KIP-932 preview release notes | https://cwiki.apache.org/confluence/x/CIq3FQ | Share-group semantics, `KafkaShareConsumer`, `share.acknowledgement.mode=explicit`, delivery counts, and the 4.0/4.1 cross-version incompatibility |
| KIP-939 (participation in 2PC) | https://cwiki.apache.org/confluence/display/KAFKA/KIP-939:+Support+Participation+in+2PC | External-coordinator 2PC, no proactive timeout abort, resumable transactions, and its dependency on KIP-890's `{producerId, epoch}` identity |
| KIP-405 / tiered storage | https://cwiki.apache.org/confluence/spaces/KAFKA/pages/97554472/KIP-405+Kafka+Tiered+Storage | Local vs remote tiers, GA in 3.9, `RemoteStorageManager`/`RemoteLogMetadataManager` |
| KIP-1150 diskless topics | https://cwiki.apache.org/confluence/display/KAFKA/KIP-1150:+Diskless+Topics | Direction of travel, and the explicit point that removing local storage removes the page cache Kafka's speed depends on |
| Conduktor — 11 Kafka production pitfalls | https://www.conduktor.io/blog/kafka-production-pitfalls | `effectiveMinIsr()` capping at `replication.factor`, `offsets.retention.minutes`=10080 expiry on empty groups, LSO stalls, future-timestamp segment immortalisation, segment rolling by message time, unclean-election ISR reset, KRaft placeholder `controllerId`, quota bypass of purgatory, auto-commit at rebalance, librdkafka compression discard, pre-compression `max.request.size` check |
| Kafka log compaction configuration (aggregated) | https://www.conduktor.io/kafka/kafka-topic-configuration-log-compaction | `min.cleanable.dirty.ratio`=0.5, `delete.retention.ms`=24 h, tombstone semantics |
| RabbitMQ release information | https://www.rabbitmq.com/release-information | Current series and dates: 4.3 (23 Apr 2026, 4.3.5), 4.2 (28 Oct 2025), 4.1 (15 Apr 2025), 4.0 (18 Sep 2024), 3.13 |
| RabbitMQ 4.3.0 release notes | https://github.com/rabbitmq/rabbitmq-server/blob/main/release-notes/4.3.0.md | Mnesia removed, Khepri sole metadata store, CQv1 removed, `x-modulus-hash` in core, Ra 3.x strict priorities and delayed retry, deprecated-feature denials, `rabbitmqadmin` v1 removal, upgrade constraints |
| RabbitMQ quorum queues doc | https://www.rabbitmq.com/docs/quorum-queues | Every `x-` argument and policy key, `x-delivery-limit` default 20, 32 priority levels, `dead-letter-strategy`, `x-quorum-initial-group-size`, `quorum_commands_soft_limit`, WAL/segment sizing, Raft mechanics, the unsupported-feature list, the ~5,000-queue guidance |
| RabbitMQ confirms doc | https://www.rabbitmq.com/docs/confirms | Ack modes, `basic.ack`/`nack`/`reject` with `multiple` and `requeue`, prefetch semantics and the 100–300 recommendation, automatic requeue on channel close, publisher confirms and their timing, unroutable-message confirmation |
| RabbitMQ 4.0 "what's new" | https://blog.rabbitmq.com/docs/4.0/whats-new | Classic mirroring removal, AMQP 1.0 as a core protocol, quorum-queue priorities, checkpoint-based recovery |
| AMQP 0-9-1 model and spec | https://www.rabbitmq.com/tutorials/amqp-concepts and https://www.rabbitmq.com/resources/specs/amqp0-9-1.pdf | Exchange types and which are mandatory, bindings, `basic.qos` prefetch semantics, `confirm.select`, the frame/method vocabulary |
| Amazon SQS message quotas | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html | 1 MiB max size, 10 attributes, 10-message batches, 4-day default / 60 s min / 14-day max retention, 30 s default / 12 h max visibility timeout, 0–15 min timers, FIFO 300 TPS and the high-throughput regional tiers, `MessageGroupId` enabling fair queues |
| SQS 1 MiB payload announcement | https://www.amazonaws.cn/en/new/2025/amazon-sqs-increases-maximum-message-payload-size-to-1mib/ | The 256 KiB → 1 MiB change (Aug 2025) and the matching Lambda ESM update |
| SQS fair queues | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html | Noisy-neighbour detection by in-flight share, dispatch prioritisation for quiet tenants, no consumer changes required |
| SQS dead-letter queues | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html | Redrive policy and `maxReceiveCount`, redrive allow policy (`allowAll`/`byQueue` up to 10/`denyAll`), the standard-queue "move to back after 3 receives" rule, enqueue-timestamp preservation on standard vs reset on FIFO, the FIFO+DLQ ordering warning, same-account/same-region constraint |
| SQS in-flight limit increase | https://aws-news.com/article/01935003-7cb6-8228-81c6-70c10c26b18e | FIFO in-flight raised from 20,000 to 120,000 |
| SNS FIFO archive and replay | https://www.amazonaws.cn/en/new/2023/amazon-sns-supports-in-place-message-archiving-and-replay-for-fifo-topics/ | Topic archive policy, subscription replay policy, filter policies scoping a replay |
| Jakarta Messaging 3.1 specification | https://jakarta.ee/specifications/messaging/3.1/jakarta-messaging-spec-3.1.html | Shared subscriptions (`createSharedConsumer`/`createSharedDurableConsumer`), delivery delay, async send with `CompletionListener`, the pruning of optional chapters, `JMSContext` |
| Spring for Apache Kafka 4.0 "what's new" | https://docs.spring.io/spring-kafka/reference/4.0-SNAPSHOT/whats-new.html | Spring Retry removal and the `@Backoff` → `@BackOff` rename, `BinaryExceptionClassifier` → `ExceptionMatcher`, `RecoveryCallback` signature change, `EmbeddedKafkaZKBroker` removal, share-consumer support, Jackson 3 class mapping table, `ConsumerRecords` constructor change |
| Spring for Apache Kafka 4.0 GA announcement | https://spring.io/blog/2025/11/18/spring-kafka-4/ | GA date, Kafka 4.1.1 client, KIP-848 and KIP-932 support, Spring Framework 7 alignment |
| Spring Kafka retry-topic reference | https://docs.spring.io/spring-kafka/reference/retrytopic.html | `@RetryableTopic`, `RetryTopicConfiguration`, `DeadLetterPublishingRecoverer`, `DefaultDestinationTopicResolver`, `RetryTopicConfigurationSupport`, `KafkaBackOffException`, the batch-listener and container-transaction limitations |
| Spring AMQP 4.0.0 announcement | https://spring.io/blog/2025/11/19/spring-amqp-4-0-0-available/ and https://spring.io/blog/2025/03/18/spring-amqp-4-0-0-m2-available/ | `spring-rabbitmq-client`, `RabbitAmqpTemplate`, `RabbitAmqpListenerContainer`, `RabbitAmqpAdmin`, the `com.rabbitmq.client:amqp-client` dependency, Jackson 3, JSpecify, Spring core retry, and the Boot starter split |
| Confluent Schema Registry — schema evolution | https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html | The seven compatibility modes, `BACKWARD` as default, transitive variants, and the upgrade-order consequence of each |
| Debezium 3.3.0.Final release | https://debezium.io/blog/2025/10/01/debezium-3-3-final-released/ | Current version and the Quarkus outbox extension's Hibernate 7 compatibility |
| Debezium Outbox Event Router | https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html | The expected outbox column names, `route.by.field`, `table.expand.json.payload`, and the one-table-to-many-topics routing |
| microservices.io — saga pattern | https://microservices.io/patterns/data/saga.html | Choreography vs orchestration, compensating transactions, ACD-not-ACID, the countermeasures pointer, and the related-pattern set |
| hellointerview — Kafka deep dive | https://www.hellointerview.com/learn/system-design/deep-dives/kafka | Interview-surface concept checklist used as a completeness probe: murmur2 partitioning, sticky partitioner, compound keys, random salting, back pressure, retention configs, single-broker throughput heuristics |
| bravenewgeek — "You Cannot Have Exactly-Once Delivery" | https://bravenewgeek.com/you-cannot-have-exactly-once-delivery/ | The impossibility framing and the delivery-versus-processing distinction to prove rather than assert |
| Kafka producer client internals write-up | https://cefboud.com/posts/kafka-producer-client-internals/ | `RecordAccumulator`/`BufferPool`/Sender drain conditions and the `max.in.flight` interaction — to be re-verified against `org.apache.kafka.clients.producer.internals` source before writing |
| KIP-782 expandable batch size | https://cwiki.apache.org/confluence/display/KAFKA/KIP-782:+Expandable+batch+size+in+producer | `batch.size` as an initial allocation rather than a hard cap |
| Datadog — lessons from running Kafka | https://www.datadoghq.com/blog/kafka-at-datadog/ | Operational failure modes and the metric set that catches them |

**Searches that returned nothing usable.** No primary source was found for a published, named,
public postmortem of a Kafka data-loss incident with the "$2.3M unreconciled transactions" figure
that circulates in secondary blog posts; the write pass must either find a first-party incident
report or drop the figure and use the *mechanism* (unclean leader election during a datacentre
outage) without the invented number. No canonical university syllabus for "messaging systems" was
located; the curriculum angle was covered instead by the Confluent/Pluralsight course outlines and
the Kafka documentation's own section ordering.

---

## Gaps vs the current guide

`src/topics/14-messaging-queues.md` is 690 lines and covers 13 sections. Every concept in it
survives as a leaf. The table below is the work order.

| Syllabus area | Present in `src/topics/14-messaging-queues.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why queues exist | § 1 — decoupling, buffering, asynchrony, durable retries, costs | temporal/spatial/format decoupling axes; fan-out and rate-limit-buffering as reasons; "a broker is a replicated WAL with a delivery policy" | when-not-to (one sentence only) |
| §1.2 vocabulary | scattered | the entire vocabulary section: command/event/document, the four spellings of position, ack overloading, replay vs redelivery vs retry | — |
| §1.3 roles | § 3 — producer/broker/consumer, pull-based note | the coordinator as a fourth role; AMQP push vs pull; what is client-side vs broker-side | broker responsibilities listed but not the per-system state table |
| §1.4 topologies / EIP | implicit only | the whole pattern catalogue: competing consumers, request-reply, splitter/aggregator, priority, delay, claim check, webhook ingestion, CDC-as-topology | — |
| §1.5 broker lifecycle | § 2 — the flagship section, strong | `offsets.retention.minutes` expiry; the three other exits (TTL, overflow, purge); RabbitMQ's variant; the graph-reading diagnostic | retention numbers are stated but SQS default is wrong elsewhere in the file |
| §1.6 delivery semantics | § 4 — at-most/at-least/exactly-once, the ack-position idea | at-least-once-with-ordering; the producer-side mirror; auto-commit as an accidental semantics change; AMQP/SQS mirrors | "effectively once" not addressed |
| §1.7 idempotent consumer | § 4 — the table, the ranked alternatives, the trap | conditional writes; broker-side dedup and its 5-minute window; key scope and lifetime; testing idempotency | cleanup job mentioned in passing, no sizing |
| §1.8 poison/retry/DLQ | § 5 — classification, jitter, DLQ ops, both traps | jitter families; the attempt-budget defaults per system; the SQS "back of queue after 3 receives" rule; the DLQ retention arithmetic; FIFO+DLQ contradiction; parking lot | DLQ context list present but not mapped to `KafkaHeaders.DLT_*` |
| §1.9 ordering | § 6 — partition keys, hot keys, both traps | producer-retry reordering; total-order-broadcast equivalence; causal ordering; Single Active Consumer; clock skew | mitigation table exists as prose |
| §1.10 queue vs log | § 7 — the comparison table and consequences | the hybrid systems (RabbitMQ Streams, share groups); the cost crossover; depth-vs-lag as different questions | — |
| §1.11 Kafka essentials | § 8 — partitions, offsets, groups, rebalancing, HOL, lag, acks, retention | ISR, high watermark, leader/follower, `__consumer_offsets`, KRaft, share groups, the CLI surface, `enable.idempotence` default change | rebalancing described pre-KIP-848 |
| §1.12 RabbitMQ / AMQP | one mention in the § 7 table | **the entire subject** — exchanges, bindings, channels, prefetch, confirms, DLX, quorum queues, streams, Khepri, alarms, the CLI | — |
| §1.13 SQS / SNS | § 9 — standard vs FIFO, visibility timeout, `maxReceiveCount`, long polling, batching, 256 KB | 1 MiB payload, fair queues, 120,000 in-flight, redrive allow policy, DLQ redrive API, the metric set, SNS in any depth, EventBridge, Kinesis, Amazon MQ | FIFO throughput figures are stale/partial |
| §1.14 JMS | absent | **the entire subject** | — |
| §1.15 message anatomy / schema | absent | **the entire subject** — headers, serialisation formats, Avro/Protobuf, Schema Registry compatibility modes, `ErrorHandlingDeserializer`, size-limit alignment, PII | — |
| §1.16 Spring surface | scattered code fragments | `AckMode`, `DefaultErrorHandler`, `@RetryableTopic`, container concurrency, `ConsumerSeekAware`, the Spring AMQP and Spring Cloud AWS surfaces, observation | — |
| §2.1 selection procedure | § 7 closing paragraph | the ordered question list, the master table, naming conventions, multi-tenancy, the QuizStakes mapping | — |
| §2.2–2.3 producer/consumer config | § 8 — `acks`, `enable.idempotence`, `retention.ms`, `max.poll.interval.ms` | ~40 named configs with defaults, the timeout relationships, the batching arithmetic, thread-safety, the metric sets | — |
| §2.4 groups and rebalancing | § 8 — the rule and the loop | the coordinator, the five-phase protocol, eager vs cooperative, KIP-848, static membership, partition-count planning, group states, drain-on-shutdown | — |
| §2.5 partitioning | § 6 | the exact murmur2 mapping, the re-map proof, cardinality arithmetic, rack awareness, RabbitMQ's hash exchanges | — |
| §2.6 retry topology | § 5 — in-process vs broker-level | the four retry locations, how a retry topic enforces delay, the SQS/RabbitMQ topologies, the attempt-multiplication trap, retry as a capacity decision | — |
| §2.7 Kafka transactions | § 4 — one paragraph | the API, `transactional.id` fencing, control records, LSO, the KIP history, KIP-939, Spring's transaction manager, the cost | scope stated correctly but not mechanically |
| §2.8 RabbitMQ in depth | absent | **the entire subject** | — |
| §2.9 SQS in depth | § 9 | the visibility state machine, heartbeat sizing, long-polling internals, batch partial success, Lambda ESM, high-throughput FIFO, redrive API, cost model | — |
| §2.10 outbox | § 10 — the problem, the schema, the relay, CDC, inbox | `SKIP LOCKED`, relay ordering and failure modes, table growth, polling cost, the Debezium SMT, the replication-slot hazard, listen-to-yourself | CDC covered as a paragraph |
| §2.11 saga | absent (index promises it) | **the entire subject** — choreography vs orchestration, compensations, ACD, step types, countermeasures, state persistence, the worked QuizStakes sagas | — |
| §2.12 event modelling / schema evolution | absent | **the entire subject** | — |
| §2.13 retry storms | § 11 — mechanism, amplification, seven defences | timeouts as a defence; the rebalance-storm form; thundering herd on recovery; circuit-breaking a consumer; graceful degradation | defences listed without config names |
| §2.14 scheduled jobs / locks | § 12 — options, the expiry hazard, fencing, idempotency-first | leader election as a named option; the claim-based work queue; claim reaping; the `PaymentRun` worked case; file-level idempotency | — |
| §2.15 backpressure | § 13 — sources, gaps, the rule | producer-side mechanisms per system; Little's Law sizing; lag-based autoscaling oscillation | AMQP prefetch and Kafka fetch configs not named as credit windows |
| §2.16 observability | § 2 and § 5 mention alerting | the whole metric catalogue, lag-seconds vs offset lag, tracing across a broker, the alert set with thresholds, log-line discipline | — |
| §2.17 security / multi-region / ops | absent | **the entire subject** — SASL/ACLs, quotas, MirrorMaker 2, upgrades, reassignment, capacity planning, testing, local dev | — |
| §3.1–3.13 internals | absent | **the entire Part 3** — storage engine, network layer, replication, KRaft, coordinators, client internals, transactions, compaction, share groups, tiered storage, RabbitMQ internals, SQS internals | — |
| §3.14 proofs | § 4 asserts two-generals in one sentence | every proof worked: two generals, FLP, total-order-broadcast equivalence, the dual-write impossibility, Little's Law, the utilisation curve, the recovery formula, quorum overlap, retry amplification | — |
| §3.15 failure catalogue | scattered across §§ 2, 5, 8, 11 | a consolidated symptom → cause → metric → fix catalogue with 22 entries | — |
| §3.16 memory / cost | absent | **the entire subject** — broker, producer and consumer memory arithmetic; dedup and outbox footprints; the SQS-vs-MSK cost crossover; cross-AZ transfer | — |
| §3.17 version history | absent | **the entire subject** — and it is where every `[VERSION-TRAP]` lives | — |
| §4 build it | absent | all 18 implementations and their Diff tables | — |
| §5 interview and retention | the atomic checklist only (60 lines) | the 32 questions, the 52-item trap list, the cheat sheet, the two decision trees, the verbal answer | checklist is good and must be carried forward verbatim-plus-expansion |

**Corrections the write pass must make to existing text** (not additions — the current file is
wrong here):

1. § 9's "256 KB max message size" → **1 MiB (1,048,576 bytes)**, with the claim-check threshold
   restated accordingly.
2. § 9's FIFO throughput ("300 msg/s, 3,000 with batching, higher with high-throughput mode") is
   incomplete: state that 300 TPS is **per API action per partition**, that batching gives 3,000
   msg/s, and give the regional high-throughput tiers (70,000 TPS / 700,000 msg/s at the top).
3. § 2's "SQS: up to 14 days" for retention must say **default 4 days**, max 14.
4. § 8's rebalancing paragraph describes the classic protocol only; it must state that KIP-848 is
   GA and default-capable in 4.x and that the classic protocol is deprecated.
5. § 8 must state that Kafka 4.x has **no ZooKeeper**.
6. § 8's `acks`/`min.insync.replicas` paragraph must add that `enable.idempotence` has defaulted to
   `true` since 3.0 and that the broker caps effective `min.insync.replicas` at
   `replication.factor`.
7. § 7's table row "Ordering | none (standard SQS)" should note that `MessageGroupId` on a standard
   queue now enables fair queues without providing ordering.
8. Every producer-tuning statement must reflect `linger.ms=5` as the 4.x default.

---

**Leaf counts.**

| Part | Leaves |
|---|---|
| PART 1 — Basics | 306 |
| PART 2 — Intermediate | 278 |
| PART 3 — Under the hood | 236 |
| PART 4 — Build it | 36 (18 implementations + 18 Diff tables) |
| PART 5 — Interview & retention | 92 |
| **Total** | **948** |

**`[RESEARCH]` leaves: 96.** They cluster in the version-delta areas — Kafka 4.1/4.2/4.3 KIPs,
share groups, KIP-848 configuration, tiered-storage thread pools, RabbitMQ 4.2/4.3, quorum-queue
arguments, SQS 1 MiB / fair queues / 120,000 in-flight / DLQ timestamp rules, SNS archive-replay,
Spring Kafka 4.0 and Spring AMQP 4.0, Schema Registry compatibility modes, and Debezium 3.3. Every
one must be re-fetched from its cited source before the write pass commits a number.

**`[VERSION-TRAP]` leaves: 47.** **`[PROVE]` leaves: 78.** **`[BUILD]` leaves: 18.**
**`[TRAP]` leaves: 111** (of which 52 are consolidated in §5.2). **`[SOURCE]` leaves: 14.**

**Target version restated for the write pass:** Kafka 4.3.0, RabbitMQ 4.3.x, Jakarta Messaging 3.1,
Spring Boot 4.0.x / Spring Kafka 4.1.x / Spring AMQP 4.0.x, AWS SQS/SNS/EventBridge as of September
2026, Debezium 3.3.x, Java 21. State the baseline in the bible's header and mark every
version-dependent claim.

**Split guidance.** At this leaf count the bible will exceed ~2,500 lines. Split into
`src/topics/14-messaging-queues.md` (PARTS 1–2) and
`src/topics/14-messaging-queues-internals.md` (PARTS 3–5), cross-link both at the top, keep an
`## Atomic concept checklist` in each, and add the new file to `src/topics/00-index.md`.
