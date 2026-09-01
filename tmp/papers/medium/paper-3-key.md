# Medium Paper 3 — Answer Key

**Q1.** Stack: push openers; on a closer, stack must be non-empty and top
must be the matching opener (pop it); at the end the stack must be empty
(catches `"("`). Map of closer→opener keeps it clean. O(n) time, O(n) space
worst case.

**Q2.** (a) O(n log n) time — outer loop runs log₂n times, inner n each;
O(1) space. (b) O(2ⁿ) time — each call spawns two; O(n) space — only one
root-to-leaf chain of frames is live at once (max recursion depth n), not
2ⁿ frames.

**Q3.**
(a) `list.stream().sorted(Comparator.comparing(Employee::dept)
.thenComparing(Comparator.comparingDouble(Employee::salary).reversed()))
.toList();`
(b) `list.stream().collect(groupingBy(Employee::dept,
averagingDouble(Employee::salary)));`
(c) `list.stream().collect(groupingBy(Employee::dept,
mapping(Employee::name, toList())));`
Full mark: all three structurally correct (minor syntax slips forgiven if
the collector choice is right).

**Q4.** (1) `peek` is designed for debugging; using it for side effects is
fragile — under short-circuiting or optimization it may not run for every
element, and mutation hidden mid-pipeline surprises readers. (2) It mutates
source objects as a hidden side effect of building an unrelated list — any
later code relying on `verified` being set now depends on this pipeline
having executed: invisible coupling. Do the mutation in an explicit loop or
separate, obvious step.

**Q5.** Nothing prints. The exception completes the future exceptionally;
`thenApply` and `thenAccept` are skipped on exceptional completion, and
since nobody calls `join()`/`get()` or attaches an error handler, the
exception is silently swallowed. Handle: `.exceptionally(ex -> fallback)`,
`.handle((v, ex) -> ...)`, or `.whenComplete((v, ex) -> log)` — or call
`join()` to surface it.

**Q6.** Hypothesis: most objects die young. Heap split: young generation
(eden + survivors) collected frequently and cheaply — live objects are few,
and copying-collection cost is proportional to SURVIVORS, not garbage;
survivors of several young GCs promote to the old generation, collected
rarely (and more expensively). Hence allocation is a pointer bump and
short-lived garbage costs almost nothing.

**Q7.** (1) Testability without magic: `new ReportService(mockClient,
mockRepo)` — no reflection, no container; this is what breaks first with
field injection (plain unit tests can't set the fields). (2) Fields can be
`final` → immutable, thread-safe wiring, no half-constructed states.
(3) Honest design feedback: a constructor with 8 params is visible pain
signaling the class does too much — field injection hides it. (Bonus:
constructor cycles fail fast at startup.)

**Q8.** `ParseException` is a CHECKED exception, and Spring's default only
rolls back on unchecked exceptions/Errors — so despite the exception
escaping the method, the transaction COMMITS on the way out: the header and
the partial set of body rows are persisted — a half-imported file. Fix:
`@Transactional(rollbackFor = Exception.class)` (or catch-and-rethrow
unchecked). Knowing the checked-vs-unchecked default is the mark.

**Q9.** The WHERE clause filters AFTER the join: departments with no
post-2025 hires have NULL `e.hired_on`, which fails the predicate — their
rows vanish, turning LEFT JOIN into de-facto INNER JOIN. Fix: move the
condition into the join —
`ON e.dept_id = d.id AND e.hired_on >= '2025-01-01'` (or use
`COUNT(*) FILTER (WHERE e.hired_on >= ...)`).

**Q10.** Dirty read: seeing another transaction's UNCOMMITTED write.
Non-repeatable read: re-reading a row within one transaction gives a
different (committed-meanwhile) value. Phantom: re-running a range query
returns new/missing rows. READ COMMITTED: permits non-repeatable +
phantoms, no dirty reads. SERIALIZABLE: permits none. Postgres default:
READ COMMITTED.

**Q11.** HTTP/1.1: one outstanding request per connection (responses in
order) — a slow response blocks everything behind it (application-level
head-of-line blocking). Workaround: ~6 parallel connections per host,
domain sharding, sprite/bundle hacks. HTTP/2: many concurrent streams
multiplexed on one connection + header compression. Remaining problem: TCP
head-of-line — one lost packet stalls ALL streams (single byte stream);
HTTP/3/QUIC runs over UDP with independent stream delivery.

**Q12.** The thread blocks in the kernel (waiting state) until data
arrives — it consumes no CPU but holds its stack (~1MB) and a pool slot.
(a) 10k concurrent slow clients = 10k parked threads = memory + scheduler
pressure — the thread-per-request ceiling; hence NIO/event loops/virtual
threads. (b) Sockets ARE file descriptors; leaking connections/streams
exhausts the per-process fd limit (`ulimit -n`) → "Too many open files."
Diagnose: `lsof -p <pid>` (count and categorize), find the unclosed
resource, fix with try-with-resources/pooling.

**Q13.** Attack: user is logged into `bank.com` (session cookie); attacker
page auto-submits a hidden form / triggers
`POST bank.com/transfer` — the BROWSER attaches the cookie automatically,
so the request is authenticated. Bearer tokens aren't attached
automatically — attacker JS on another origin can't read or set your
Authorization header. Cookie defenses: anti-CSRF tokens (synchronizer
token the attacker can't know), `SameSite=Lax/Strict` cookies; (also
Origin/Referer checking).

**Q14.** (a) `GET /customers/{id}/orders` (+ pagination/filter params).
(b) Cancel = state transition, not deletion: `POST /orders/{id}/cancel`
(action sub-resource) or `PATCH /orders/{id}` with `{"status":"CANCELLED"}`
— DELETE is wrong because the order still exists. (c)
`POST /payments/{id}/retries` — retries as a created sub-resource (gives
each retry an id, listable) or `POST /payments/{id}/retry`. Marks for: no
verbs in CRUD paths, deliberate non-CRUD convention, one-line
justification.

**Q15.** Bounded retries with exponential backoff (+ jitter), then move to
a dead-letter queue and continue the stream — never block forever.
Distinguish: transient/retryable failures (downstream timeout, deadlock) →
retry; permanent/non-retryable (parse error, validation) → straight to DLQ,
retrying can't help. DLQ end-state: alert on depth, human/tool inspects,
fix cause, replay. Bonus: note ordered-partition systems suffer
head-of-line blocking here, queue systems don't.

**Q16.** Total order requires a single serialization point — one lane, no
parallelism; throughput needs many lanes (partitions) processed
independently. Compromise: order guaranteed only WITHIN a partition;
partition by the entity whose events must stay ordered (order-id, user-id,
account-id). Bad key → hot partition: one giant customer's traffic lands on
one partition/consumer while others idle — skewed load, throttling, lag.

**Q17.** H2: fast, no Docker, but a different engine — dialect and feature
gaps mean tests pass while prod fails. Hidden-bug examples (any):
Postgres-specific SQL (`ON CONFLICT`, JSONB, window quirks), sequence/
identity behavior, constraint or transaction-isolation differences, subtle
type coercion. Testcontainers: real Postgres in Docker — slower, but tests
prove prod behavior; mitigate cost with singleton/reused containers.
Recommendation: Testcontainers for anything beyond trivial JPA derived
queries.

**Q18.** `git bisect`: mark `main` bad and `v2.3` good; git binary-searches
the range, checking out midpoints for you to test. ~log₂(400) ≈ 9 steps.
Automate: `git bisect run ./repro.sh` — script exits 0 for good/non-zero
for bad; git finds the culprit unattended.

**Q19.** (1) HTTP sessions → external store (Redis) or stateless tokens
(JWT); (2) local file writes (uploads, temp artifacts) → object storage
(S3); (3) in-process caches needing coherence → shared cache (Redis) or
accept per-instance TTL staleness deliberately; (4) scheduled jobs assuming
"only one of me" → distributed lock / leader election / move to a single
worker or queue. (Also acceptable: in-memory queues/buffers → real broker;
websocket/sticky state → pub-sub backplane.)

**Q20.** Logs: discrete, detailed event records — "what exactly happened in
THIS request?" (stack trace for one failed order — only logs have it).
Metrics: cheap numeric aggregates over time — "is error rate/p99 trending
up? alert me" (you can't alert on grep). Traces: one request's causal path
across services with timing — "where did this request's 3 seconds go, which
hop is slow?" (neither logs nor metrics show cross-service causality).

---

**Interpretation:** 16+ strong; 11–15 typical with gaps to list; < 11
record failed sections as findings.
