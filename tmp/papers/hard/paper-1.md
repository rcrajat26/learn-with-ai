# Hard Paper 1

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-1-key.md`. Suggested time: 2 hrs.
20 questions, 1 mark each. Scenario answers should be concrete — commands,
schemas, and specific mechanisms, not "I would investigate."

## Section 1 — DSA & Data Structures

**Q1.** A service keeps a `HashSet<Order>` of in-flight orders. After a
status update runs (`order.setStatus(...)`), `set.contains(order)` starts
returning false for orders that ARE in the set, and `set.size()` shows
duplicates after re-adds. Explain the exact mechanism and give two fixes
with their trade-offs.

**Q2.** `[CODE — 30 min]` Design and implement an LRU cache:
`get(key)` and `put(key, value)` both O(1), fixed capacity, least recently
used entry evicted. Either build on `LinkedHashMap` (explain what
access-order does) or hand-roll HashMap + doubly-linked list. State the
invariants.

## Section 2 — Java Core

**Q3.** Design a `Money` type for a payments codebase. Cover: internal
representation and why not `double`, arithmetic API shape, rounding policy
ownership, currency mismatch handling, equality semantics, and one
JSON-serialization concern.

**Q4.** Model this domain with sealed interfaces + records + pattern
matching: a payment event is exactly one of `Authorized(amount, authCode)`,
`Captured(amount)`, `Refunded(amount, reason)`, `Failed(errorCode)`.
Sketch the types and a `String describe(PaymentEvent e)` using switch.
What compile-time guarantee does this buy that an enum-plus-fields or
class-hierarchy-with-instanceof approach doesn't?

## Section 3 — Concurrency & JVM

**Q5.** Production incident: a JVM service is pinned at 100% CPU, requests
time out. Give your first 10 minutes as a concrete command sequence,
including how you go from "the process" to "the exact stack frames burning
CPU," and how you distinguish app code from GC as the culprit.

**Q6.** `[CODE — 20 min]` Implement a bounded producer-consumer handoff:
producers block when the buffer is full (backpressure), consumers block
when empty. Use `BlockingQueue` — and explain what
`ThreadPoolExecutor.CallerRunsPolicy` achieves in the same spirit for task
submission.

## Section 4 — Spring & JPA

**Q7.** You must write an audit record for every order operation — and the
audit row must survive even when the business transaction rolls back.
Design this with Spring transaction propagation: which propagation level,
placed where (same bean? different bean?), what goes wrong with the naive
same-class implementation, and one alternative design that avoids nested
transactions entirely.

**Q8.** A seat-booking flow: two users click the same seat within 50ms.
Compare optimistic (`@Version`) vs pessimistic (`SELECT ... FOR UPDATE`)
locking for this exact case — what does each user experience, what are the
throughput implications, and describe the two-phase HOLD→CONFIRM pattern
real ticketing systems use and why.

## Section 5 — SQL & Databases

**Q9.** Design the schema and queries for a job-queue table in Postgres
that multiple worker processes poll concurrently WITHOUT two workers
grabbing the same job. Give the claim query (there's a specific locking
clause designed for this), the columns you need, and how you handle a
worker that dies mid-job.

**Q10.** You need to add a NOT NULL column with a default to a 500M-row
table that serves live traffic, plus an index on it. Describe the
zero-downtime procedure (Postgres), naming what naive `ALTER TABLE` and
naive `CREATE INDEX` would each do wrong.

## Section 6 — Networking & OS

**Q11.** Intermittent `504 Gateway Timeout` from your ALB, but your
service's own logs show requests completing successfully in ~55–65s.
The ALB idle timeout is 60s and your client-side retries are ON. Explain
what's happening end-to-end, why "the service looks healthy," the
data-integrity hazard the retries introduce, and the two-sided fix.

**Q12.** Your service opens a fresh HTTPS connection to a partner API for
every call: p50 latency is fine but p99 is terrible and correlates with
call bursts. Break down the costs of a cold HTTPS call (list the round
trips), and design the fix — including the pool settings that matter and
one keep-alive pitfall with intermediate proxies/NATs.

## Section 7 — API & Web Security

**Q13.** Design `POST /payments` to be safe under client retries
(timeout → retry) — full mechanism: header, server-side storage and its
constraints, response replay semantics, the concurrent-duplicate case,
key scope/TTL, and what happens when the same key arrives with a different
body.

**Q14.** Design a webhook system (you SEND webhooks to customer endpoints):
delivery guarantees and retry policy, how customers verify authenticity
(mechanism, not just "sign it"), replay-attack protection, ordering
caveats, and one operational protection for YOUR system when a customer
endpoint is down for hours.

## Section 8 — Messaging & Caching

**Q15.** The dual-write problem: a service saves an `Order` to Postgres and
publishes `OrderCreated` to Kafka. Enumerate the failure windows in both
orderings (publish-then-commit, commit-then-publish), then design the
transactional outbox: table schema, the relay mechanism (two options with
trade-offs), and what delivery guarantee the consumer must now handle.

**Q16.** A distributed lock via Redis `SET key val NX EX 30`: walk through
why lock expiry + a paused/slow holder (GC pause, network stall) breaks
mutual exclusion, what a fencing token adds and where it must be checked,
and conclude with when you'd avoid distributed locking entirely.

## Section 9 — Testing & Craft

**Q17.** You inherit a 4,000-line service class with zero tests and must
change its pricing logic safely. Describe the characterization-testing
approach step by step, including how you get the untestable class under
test at all (seams), and the discipline about refactoring vs
behavior-changing commits.

**Q18.** Design the test strategy for a new order-processing microservice
(REST API + Postgres + Kafka consumer + calls to a payment service):
what gets unit tests vs slice tests vs integration tests vs contract
tests, where Testcontainers fits, what you deliberately do NOT test, and
the async-flow testing trap (with the tool that fixes it).

## Section 10 — Cloud & DevOps

**Q19.** Design zero-downtime deploys for a stateful-ish reality: the new
release changes a DB column's meaning. Explain the expand/contract
(parallel-change) migration pattern step by step across releases, and why
"deploy code and migration together" fails under rolling deploys even with
health checks.

**Q20.** It's 3 a.m.; pager: checkout 5xx rate 0.1% → 8% over 10 minutes.
Give your first 15 minutes as a decision tree: the order of questions you
answer, the single highest-value question early on, when you roll back vs
keep diagnosing, and what you explicitly do NOT do during the incident.
