# Hard Paper 1 — Answer Key

**Q1.** `Order.hashCode()` depends on mutated state (status). The object
was filed in the bucket for its OLD hash; after mutation, `contains`
computes the NEW hash and searches a different bucket → miss. Re-adding
stores a second copy in the new bucket → "duplicates." Fixes: (1) make
hashCode/equals depend only on immutable identity (order id) — simplest,
standard; (2) treat keys as immutable — remove from set, mutate, re-add
(fragile discipline); (3) use identity-based collections or a
`Map<OrderId, Order>` — sidesteps hashing on mutable state. Mechanism
(wrong-bucket) required for the mark.

**Q2.** `LinkedHashMap` route: extend with `(capacity, 0.75f, true)` —
access-order mode moves entries to the tail on `get`/`put`; override
`removeEldestEntry(...) { return size() > capacity; }`. Hand-rolled:
HashMap<K, Node> + doubly-linked list; invariants: list order = recency
(head = LRU, tail = MRU); every `get` unlinks and re-appends the node
(O(1) because the map jumps straight to it); `put` on full capacity evicts
head. Both O(1) per op. Marks: working code + eviction correct + stated
invariant.

**Q3.** Representation: `BigDecimal` amount (binary floating point can't
represent decimal fractions; cents drift) — or `long` minor units (fast,
exact, but scale/currency-exponent handling manual) — either with the
why. Plus `Currency`/currency code. API: immutable — `add/subtract/
multiply` return new instances; construction validates scale for the
currency. Rounding: never implicit — `RoundingMode` explicit at the
operations that need it (division, percentage), policy owned by Money, not
scattered callers. Currency mismatch: `add(USD, EUR)` throws — never
coerce. Equality: `equals` on BigDecimal is scale-sensitive (1.0 ≠ 1.00) —
normalize scale internally or compare via `compareTo`. JSON: serialize as
string (or minor-units integer), never a JSON float — precision loss at
the boundary.

**Q4.**
```java
sealed interface PaymentEvent permits Authorized, Captured, Refunded, Failed {}
record Authorized(BigDecimal amount, String authCode) implements PaymentEvent {}
record Captured(BigDecimal amount) implements PaymentEvent {}
record Refunded(BigDecimal amount, String reason) implements PaymentEvent {}
record Failed(String errorCode) implements PaymentEvent {}

String describe(PaymentEvent e) {
    return switch (e) {
        case Authorized a -> "auth " + a.authCode();
        case Captured c   -> "captured " + c.amount();
        case Refunded r   -> "refunded: " + r.reason();
        case Failed f     -> "failed: " + f.errorCode();
    };
}
```
Guarantee: exhaustiveness — the sealed hierarchy is closed, so the switch
needs no `default`; adding a fifth event type breaks COMPILATION at every
switch, forcing every handler to be updated. instanceof-chains and
enum+nullable-fields fail silently at runtime instead (forgotten branch /
fields that don't apply to a variant).

**Q5.** (1) `top -H -p <pid>` — thread view; note the TID(s) at ~100%.
(2) Convert TID to hex (`printf '%x'`). (3) `jstack <pid>` (or `jcmd
Thread.print`) 2–3 times, 5s apart. (4) Find the thread by `nid=0x<hex>`;
if the same frames appear across dumps, that's the hot code. GC vs app:
hot threads named "GC Thread"/"G1 Conc" → memory problem in CPU costume —
pivot to `jstat -gcutil` (back-to-back full GCs, old gen pinned near 100%)
and heap analysis. Repeated-sampling detail and the GC pivot are what earn
the mark; "check monitoring/restart it" without extraction = 0.5. Bonus:
async-profiler flame graph as the sharper tool.

**Q6.**
```java
BlockingQueue<Task> buf = new ArrayBlockingQueue<>(1024);
// producer: buf.put(t);      — blocks when full  → backpressure
// consumer: Task t = buf.take();  — blocks when empty
```
Marks: bounded `ArrayBlockingQueue` + blocking `put`/`take` (not
`offer`/`poll` without timeout), poison-pill or interruption story for
shutdown = bonus. `CallerRunsPolicy`: when executor queue is full, the
SUBMITTING thread executes the task itself — submission slows to
processing speed; producers are throttled instead of tasks being dropped
or queued unboundedly.

**Q7.** Audit method with `Propagation.REQUIRES_NEW`, in a SEPARATE bean
(`AuditService`) injected into the business service: the outer transaction
suspends, audit commits independently, outer can still roll back. Naive
same-class `this.audit(...)` fails silently — the call bypasses the Spring
proxy, so REQUIRES_NEW never applies and audit dies with the rollback.
Caveat worth stating: audit-before-failure still commits (may audit an
attempt, which is often the requirement — "attempted X"). Alternative
without nested transactions: publish an audit event and persist it
listener-side (`@TransactionalEventListener(phase = AFTER_ROLLBACK/
AFTER_COMPLETION)`), or write audits to an outbox/log pipeline
asynchronously.

**Q8.** Optimistic: both read seat v5; user A commits (v6); user B's commit
hits `OptimisticLockException` → B gets "seat just taken, pick another"
after doing the work. Cheap, no locks held, fine when conflicts are rare —
but retry-after-failure UX. Pessimistic: B's `SELECT ... FOR UPDATE`
blocks ~until A commits, then sees the seat taken immediately; no wasted
work, but locks held across user think-time would be deadly — only lock
within the short transactional claim, never across UI time. Real systems:
two-phase — HOLD: short transaction claims the seat (status=HELD,
holder, expiry ~5min, enforced by unique/conditional update); user pays
outside any DB transaction; CONFIRM converts HELD→BOOKED (verifying
holder); expiry sweeper releases stale holds. Why: never hold DB locks
across human time; holds give both correctness and honest UX.

**Q9.** Columns: `id, payload, status(pending/running/done/failed),
attempts, locked_by, locked_at, run_after`. Claim:
```sql
UPDATE jobs SET status='running', locked_by=:worker, locked_at=now()
WHERE id = (
  SELECT id FROM jobs
  WHERE status='pending' AND run_after <= now()
  ORDER BY id
  FOR UPDATE SKIP LOCKED
  LIMIT 1
) RETURNING *;
```
`FOR UPDATE SKIP LOCKED` is the designed clause: concurrent workers skip
rows already row-locked instead of blocking or double-claiming. Dead
worker: heartbeat/lease — a sweeper resets `running` rows whose
`locked_at` exceeds the lease (status→pending, attempts+1), with max
attempts → failed/DLQ table. Bonus: `LISTEN/NOTIFY` or short poll interval.

**Q10.** Naive `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT` on old
Postgres rewrote the whole table under an exclusive lock (minutes of
downtime); naive `CREATE INDEX` takes a lock blocking writes for the whole
build. Procedure: (1) `ADD COLUMN` nullable, no default (metadata-only,
instant) — on PG 11+ a static DEFAULT is also metadata-only, but the
NOT NULL step still needs care; (2) backfill in batches (`UPDATE ... WHERE
id BETWEEN ...`, throttled, avoiding long transactions); (3) `CREATE INDEX
CONCURRENTLY` (no write-block; note: can't run in a transaction, may leave
INVALID index on failure — check and retry); (4) add the constraint
without a full scan: `ADD CONSTRAINT ... CHECK (col IS NOT NULL) NOT
VALID` then `VALIDATE CONSTRAINT` (takes only a weak lock), or on modern
PG set `NOT NULL` after validating; (5) deploy code that writes the column
BEFORE the backfill (expand/contract ties to Q19).

**Q11.** Requests take ~55–65s; those crossing the ALB's 60s idle/response
timeout get killed AT THE ALB → client sees 504, but the backend keeps
processing and completes → its logs look fine. Retries then RE-EXECUTE a
request whose first attempt also completed → duplicate side effects
(double orders/charges) — the integrity hazard. Fix both sides:
(1) latency — the 60s work doesn't belong in a synchronous request: make
it async (202 + status polling/webhook) or optimize; align timeout chain
(client < LB < server) so the SERVER times out first and can fail
cleanly; (2) integrity — idempotency keys so unavoidable retries are safe.

**Q12.** Cold HTTPS call: DNS lookup, TCP handshake (1 RTT), TLS handshake
(1–2 RTTs + crypto), THEN the request — 3–4 round trips of pure overhead;
under bursts, connection setup also contends (and each one-shot connection
leaves TIME_WAIT behind). Fix: pooled keep-alive client (Apache HC /
OkHttp / JDK HttpClient): pool sized for burst concurrency, per-route
limits, connection TTL/max-lifetime, and validate-after-inactivity.
Pitfall: intermediate proxies/NAT/firewalls silently drop idle connections
without RST — the pool hands you a dead connection and the first use
fails/hangs; set pool idle-timeout BELOW the infrastructure's idle
timeout (and/or TCP keepalive, retry-on-stale).

**Q13.** Client sends `Idempotency-Key: <uuid>` (generated per logical
operation, reused on retry). Server table: `key (unique), request_hash,
status(in_progress/done), response_code, response_body, created_at`.
Flow: INSERT the key (unique constraint = atomic claim); on conflict —
if `done`, replay the STORED response (same status + body); if
`in_progress`, return 409/425 or block briefly (the concurrent-duplicate
case: never execute twice, never return half-state); same key + different
`request_hash` → 422 (client bug — a key identifies ONE operation).
Scope keys per client+endpoint; TTL/cleanup (24h typical). Execution and
the key's `done`-marking must be atomic with the business write (same
transaction/outbox).

**Q14.** Delivery: at-least-once — persist the event, retry with
exponential backoff + jitter on non-2xx/timeouts over hours (schedule:
e.g., 1m, 5m, 30m, 2h...), then park in a dead-letter state with customer
visibility and manual/automatic replay. Authenticity: HMAC-SHA256 of the
raw body with a per-customer secret in a header
(`X-Signature: t=<ts>,v1=<hmac>`); customer recomputes over the raw bytes
and constant-time-compares; include the timestamp IN the signed payload.
Replay protection: reject signatures whose timestamp is older than a few
minutes + idempotent event ids consumer-side. Ordering: not guaranteed
under retries — deliver event ids + sequence/occurred_at, consumers must
tolerate out-of-order (or fetch current state via API). Self-protection:
per-endpoint circuit breaker + delivery budget so one dead customer
endpoint doesn't monopolize workers/queues; isolate per-tenant queues.

**Q15.** Publish-then-commit: DB commit can fail after the event is out →
consumers act on an order that doesn't exist (phantom event). Commit-then-
publish: crash/broker outage between the two → order exists, event lost →
silent downstream divergence. Outbox: `outbox_events(id, aggregate_id,
type, payload jsonb, created_at, published_at null)` written IN THE SAME
transaction as the order insert — atomicity restored at the source.
Relay: (a) poller — `SELECT ... WHERE published_at IS NULL ORDER BY id
FOR UPDATE SKIP LOCKED`, publish, mark — simple, adds polling latency,
needs multi-instance care; (b) CDC (Debezium reading the WAL) — low
latency, captures everything, but new infrastructure + ops burden.
Relay is at-least-once either way → consumers must be idempotent
(event id dedup). Naming that residual guarantee is required for full mark.

**Q16.** Holder acquires lock (30s expiry), then stalls (GC pause, network
partition) past expiry → Redis expires the key → second client acquires →
TWO holders run the critical section; the first, resuming, still believes
it holds the lock. Expiry is necessary (crashed holders) but makes the
lock advisory. Fencing token: a monotonically increasing number issued
with each acquisition; the PROTECTED RESOURCE (DB, storage) checks it —
rejects writes carrying a token lower than the highest seen; the stale
holder's writes fail. Without a resource that can check tokens, the lock
alone cannot give safety. Avoid distributed locks when the invariant can
live where the data lives: DB unique constraints, conditional updates
(`WHERE version = ...`), `SKIP LOCKED` queues, or single-writer
partitioning — cheaper and actually correct.

**Q17.** (1) Pin current behavior: write characterization tests that
assert what the code DOES (not what the spec says) — feed representative
inputs, capture outputs, freeze them (golden/approval tests work at this
scale). (2) Get a seam first: the minimal, mechanical, no-behavior-change
edits that make construction possible — extract interface over the DB/HTTP
singletons, add a constructor accepting dependencies (keep the old one
delegating), break static calls via wrapper. (3) Coverage around the
pricing paths specifically — branch through discount/edge cases with
varied inputs. (4) Refactor in small steps UNDER the pinned tests —
commits that change structure never change behavior, and vice versa; the
tests stay green throughout. (5) Only then make the behavioral change —
now it's a visible, tested diff: update the specific characterization
tests deliberately. Separating refactor commits from behavior commits is
the discipline being tested.

**Q18.** Unit: domain/pricing/validation logic, mappers — fast, bulk of
tests. Slice: `@WebMvcTest` for controller contract (status codes,
validation, serialization) with mocked service; `@DataJpaTest` +
Testcontainers-Postgres for repositories/custom queries (not H2). 
Integration (`@SpringBootTest` + Testcontainers Postgres AND Kafka): the
few end-to-end paths — consume event → process → persist → publish.
Contract tests: the payment-service boundary (Pact/Spring Cloud Contract
or OpenAPI-validated stubs) — so your mock of THEIR API can't drift from
reality; never integration-test against their live sandbox in CI. Don't
test: framework behavior (Spring's DI, Jackson defaults), getters/
generated code, exhaustive permutations already unit-covered. Async trap:
asserting immediately after publishing to Kafka — the consumer hasn't run;
`Thread.sleep` makes it flaky-slow. Awaitility:
`await().atMost(10, SECONDS).untilAsserted(...)` — poll for the outcome.

**Q19.** Expand/contract: R1 (expand): add the NEW column/shape; code
writes BOTH old and new, reads old — migration adds schema, backfill runs
online. R2: verify parity (dual-write metrics/reconciliation); switch
reads to new. R3 (contract): stop writing old; later migration drops it.
Each release is individually roll-back-able and each schema works with
BOTH adjacent code versions. Why deploy-together fails under rolling
deploys: old and new pods run SIMULTANEOUSLY against one schema — if the
migration instantly changes the column's meaning, old pods misinterpret
data the moment it lands (health checks pass — the app is "up," it's just
writing wrong data). Backward compatibility must span the overlap window;
same logic applies to rollback (new data must not break old code).

**Q20.** Order: (1) blast radius — all endpoints or just checkout? all
instances/AZs or one? real users or one synthetic? (2) THE highest-value
question: what changed? — deploys, flags, config, dependency releases,
traffic pattern in the last ~30min; correlation with a deploy → roll back
NOW, diagnose later (rollback is cheap, diagnosis under fire is not).
(3) If nothing changed: dependency health (payment provider, DB) — is it
us or downstream? saturation check (pool exhaustion, memory, connections,
queue depth). (4) Mitigate before root-cause: rollback / scale out /
circuit-break the failing dependency / shed non-critical load. (5)
Communicate: status channel, severity, "investigating," periodic updates.
Do NOT: restart things at random (destroys evidence, may worsen), debug
line-by-line during impact, push a hot "fix" forward without confidence
(roll back instead), go silent. Timeline note-keeping for the postmortem =
bonus.

---

**Interpretation:** 14+ = strong senior-level judgment; 9–13 = solid with
specific gaps — list them; < 9 = hard tier is aspirational for now; the
medium tier is your working level. Feed section-level misses into
`qbank/13-scoring-and-report.md`.
