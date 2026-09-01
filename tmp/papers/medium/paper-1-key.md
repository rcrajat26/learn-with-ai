# Medium Paper 1 — Answer Key

**Q1.** Contract: equal objects (per `equals`) MUST return equal hashCodes;
unequal objects may share a hashCode; both must be consistent across calls
(on unmutated state). Without `hashCode` override, two logically-equal keys
get different (identity) hashes → land in different buckets → `get(equalKey)`
looks in the wrong bucket and misses; logically-duplicate keys coexist.

**Q2.** `hashCode()` is called and spread (XOR of high bits), bucket index
= `(capacity - 1) & hash` (capacity is a power of two). Collision: entry
appended to that bucket's linked list (after checking `equals` for
replace); a bucket exceeding 8 entries treeifies to a red-black tree
(O(log n)). Past load factor (0.75 × capacity): array doubles and all
entries are rehashed/redistributed.

**Q3.** Throws `IndexOutOfBoundsException`. Overload resolution picks
`remove(int index)` over `remove(Object)` for the primitive literal `10` —
it tries to remove index 10 from a 3-element list. Fix:
`list.remove(Integer.valueOf(10))`.

**Q4.** `true`, `false`, `true`. `Integer` autoboxing caches −128..127, so
both 127s are the same object; 500 boxes to two distinct objects and `==`
compares references; `equals` compares value. Moral: never `==` on wrappers.

**Q5.** `synchronized`: mutual exclusion + visibility (happens-before edge
between monitor release and acquire). `volatile`: visibility + ordering
only — no atomicity. Sufficient: a `volatile boolean running` flag one
thread sets and another polls. Insufficient: `volatile int counter` with
`counter++` (read-modify-write race) — needs `AtomicInteger` or a lock.

**Q6.** Check-then-act is a compound action — the concurrent map makes
individual calls atomic, not the pair: two threads can both see "absent"
and both run the expensive load. Fix:
`return cache.computeIfAbsent(key, this::loadFromDb);` — atomic per key.
(Noting that a long load inside `computeIfAbsent` blocks that bin is bonus.)

**Q7.** Spring wraps the bean in a proxy (JDK dynamic proxy for interfaces,
CGLIB subclass otherwise); callers hold the proxy, which runs the
transactional/caching interceptor around the real method. Limitations (any
one): self-invocation (`this.method()`) bypasses the proxy so the
annotation is ignored; `private`/`final` methods can't be intercepted;
only public external calls get the behavior.

**Q8.** No — `this.audit(o)` is a direct call on the target object,
bypassing the proxy, so `REQUIRES_NEW` is silently ignored and audit joins
`process`'s transaction (a rollback rolls both back). Fixes: move `audit`
into a separate bean and inject it; or self-inject the proxy
(`@Lazy @Autowired OrderService self; self.audit(o)`).

**Q9.**
```sql
SELECT name, dept_name, salary FROM (
  SELECT e.name, d.name AS dept_name, e.salary,
         ROW_NUMBER() OVER (PARTITION BY e.dept_id ORDER BY e.salary DESC) AS rn
  FROM employees e JOIN departments d ON d.id = e.dept_id
) ranked WHERE rn <= 2;
```
Window function is the expected tool (`DENSE_RANK` acceptable — states the
tie behavior). A correlated-subquery solution that works = 0.5.

**Q10.** (a) Yes — leftmost prefix. (b) Yes — equality on the first column,
then range on the second: ideal composite usage. (c) No — the index is
sorted by `customer_id` first; `created_at` values are scattered across it
(leftmost-prefix rule); needs a separate index on `created_at`.

**Q11.** DNS: stub asks recursive resolver → root → .com TLD →
authoritative NS → A record; cached at each layer per TTL (browser, OS,
resolver). TCP: 3-way handshake (SYN, SYN-ACK, ACK) to the IP on port 443.
TLS: certificate chain verified against trusted CAs, key exchange
establishes symmetric session keys. HTTP: request over the encrypted
channel; response status + headers + body; connection reused (keep-alive)
for subsequent assets.

**Q12.** Connect timeout: TCP connection couldn't be established — host
down, wrong port, firewall/security group, network path. Read timeout:
connected fine, but no response bytes within the window — server slow,
stuck, or overloaded. Different failures, different investigations. Many
Java clients default both to infinite (or very large) — unconfigured
timeouts = threads hanging forever.

**Q13.** PUT: full replacement of the resource — idempotent (same body N
times = same state). PATCH: partial update — not guaranteed idempotent
(depends on semantics, e.g., increments). POST: create/process — not
idempotent. On timeout the client doesn't know if the request executed;
retrying an idempotent method is safe, retrying POST risks duplicates —
hence idempotency keys for POST.

**Q14.** Offset: `?page=3&size=50` → `OFFSET 100 LIMIT 50`. Failure modes:
(1) rows shift under concurrent inserts/deletes — items skipped or repeated
across pages; (2) deep offsets scan-and-discard all preceding rows — slow.
Cursor: response includes an opaque cursor encoding the last item's sort
key (e.g., `(created_at, id)`); next request `?cursor=...&limit=50` does an
indexed `WHERE (created_at, id) < (...)`. Body: `items`, `next_cursor`
(null when done) — plus stable sort with a tie-breaker column.

**Q15.** At-most-once: ack/commit BEFORE processing — a crash mid-process
loses the message. At-least-once: ack AFTER processing — a crash between
process and ack causes redelivery → duplicates. Exactly-once: requires
atomicity across the broker and your side effects — not achievable with a
plain DB write + ack (two systems). Practical default: at-least-once;
obligation: idempotent processing (dedup key/unique constraint).

**Q16.** Read: check cache → hit: return → miss: load DB, populate with
TTL, return. Write: update DB, then DELETE the cache key; next read
repopulates. Delete over update: two concurrent writers can interleave so
the cache ends up holding the older value forever (stale-set race);
delete-then-repopulate converges. Also the cached shape may be derived —
recomputing on read is simpler than recomputing on write.

**Q17.** Stub: returns canned data. Mock: additionally verifies
interactions (was `save` called with X). Fake: real working lightweight
implementation (in-memory repo). (a) mock/stub it — it's a boundary you
own; (b) don't mock the third-party client directly — wrap it in your own
interface and mock the wrapper ("don't mock what you don't own"); (c) use
the real calculator — it's pure logic; mocking it would weld the test to
implementation and verify nothing.

**Q18.** Hidden non-deterministic dependency: tests can't control "today,"
so date-boundary behavior (anniversary, expiry, month-end) is untestable
and fails only when the calendar cooperates. Fix: inject `java.time.Clock`;
production wiring uses `Clock.systemUTC()`, code calls
`LocalDate.now(clock)`; tests pass
`Clock.fixed(Instant.parse("2025-03-01T00:00:00Z"), ZoneOffset.UTC)`.

**Q19.** Static keys are long-lived secrets: they leak (git, logs, laptops),
need manual rotation, and grant access from anywhere. A role is an
assumable identity: the platform vends TEMPORARY, auto-rotated credentials
to the instance/task (via instance profile / task role, fetched from the
metadata endpoint) — nothing static to steal, permissions scoped
least-privilege, revocable centrally.

**Q20.** Liveness: "is this process stuck beyond recovery?" → orchestrator
RESTARTS it. Readiness: "can it serve traffic right now?" → load balancer
routes to it or not. Storm: if liveness checks a dependency (DB), a DB
outage makes ALL instances "dead" → the orchestrator restarts perfectly
healthy pods in a loop, adding churn and cold starts to an outage they
can't fix — the dependency belongs (carefully) in readiness, not liveness.

---

**Interpretation:** 16+ strong at this tier; 11–15 typical with gaps to
list; < 11 medium tier is the working boundary — record failed sections.
