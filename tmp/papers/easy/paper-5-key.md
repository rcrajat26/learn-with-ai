# Easy Paper 5 — Answer Key

**Q1.** (a) array O(1) by index; linked list O(n) walk. (b) list O(1) IF
you already hold the node (finding it is O(n)); array O(n) shifting.
(c) array contiguous; list scattered nodes with pointer overhead. Arrays
(`ArrayList`) usually win — contiguous memory is cache-friendly; pointer
chasing defeats CPU caches.

**Q2.** A function that solves a problem by calling itself on smaller
input. Needs: a base case (terminates) and progress toward it (each call
strictly smaller). Missing either → infinite recursion → stack frames pile
up → `StackOverflowError`.

**Q3.** List: ordered, duplicates allowed, index access — e.g., items in a
shopping cart in order added. Set: no duplicates — e.g., unique visitor
ids. Map: key→value lookup — e.g., config values by name, id→object cache.

**Q4.** Compile-time type safety for containers/APIs. `List<String>`:
compiler rejects `add(42)` and `get()` returns `String` without casting.
Prevents `ClassCastException` at runtime (the raw-list failure, discovered
far from the buggy insert).

**Q5.** Guarantees: visibility (a write is seen by subsequent reads on
other threads) and ordering around the access. Not guaranteed: atomicity of
compound actions. `counter++` is read-modify-write — still a race even on a
volatile; use `AtomicInteger` or synchronization.

**Q6.** NEW → RUNNABLE (running/ready) → BLOCKED / WAITING /
TIMED_WAITING → TERMINATED. BLOCKED: trying to enter a synchronized block
whose monitor another thread holds. WAITING: parked deliberately —
`wait()`, `join()`, `LockSupport.park` — until another thread signals it.

**Q7.** `@Controller` returns view names for template rendering (MVC);
`@RestController` = `@Controller` + `@ResponseBody` on every method —
return values are serialized (JSON) straight into the response body.
`@RequestBody` deserializes the request body into a parameter object.

**Q8.** Versioned, ordered SQL/change scripts applied automatically and
recorded (schema history table) — reviewable, repeatable across
environments, supports rollback planning. `ddl-auto=update` guesses diffs:
no review, no history, can't rename safely, may drop/alter destructively —
unacceptable against production data.

**Q9.** DELETE: removes rows matching WHERE — selective, row-by-row,
transactional/logged. TRUNCATE: empties the whole table fast (no WHERE),
resets identity in some DBs. DROP: removes the table itself — data AND
structure. Only DELETE is selective.

**Q10.**
```sql
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'
GROUP BY customer_id
HAVING SUM(amount) > 10000
ORDER BY total DESC;
```
Key points: WHERE for the date (row filter), HAVING for the total
(aggregate filter), ORDER BY the aggregate.

**Q10b.** Crash-with-no-lost-money → **Atomicity**: the transaction's
debit+credit commit together or not at all — the half-done debit rolls
back on recovery. Report never sees the intermediate state → **Isolation**:
concurrent transactions don't observe each other's uncommitted changes.
Confirmed transfer survives power failure → **Durability**: committed
work is persisted (WAL) before the confirmation is sent. Fourth property:
**Consistency** — every transaction moves the DB from one valid state to
another; constraints and invariants (e.g., `balance >= 0`, totals
conserved) hold before and after. Retest of E4 Q10 — record the outcome
in the valuation.

**Q11.** (1) DNS resolves example.com → IP; (2) TCP connection established
(3-way handshake); (3) TLS handshake (certificate verified, session keys
agreed); (4) HTTP request sent over the encrypted channel; (5) server
responds with status + headers + HTML body. That order, with DNS before
TCP before TLS before HTTP, is the mark.

**Q12.** A rule set allowing/blocking traffic by port/protocol/source.
Likely causes (any two): security group/firewall doesn't allow inbound
8080 (or 80/443); app bound to 127.0.0.1 instead of 0.0.0.0; no public
IP / wrong DNS; OS-level firewall (iptables/ufw).

**Q13.** A token whose mere possession grants access ("bearer" = whoever
carries it). Travels in the `Authorization: Bearer <token>` header. Over
plain HTTP anyone on the path can read and replay it — HTTPS is what keeps
the credential confidential.

**Q14.** Browsers block cross-origin responses by default; CORS headers
(`Access-Control-Allow-Origin`...) are the server saying "this origin may
read my responses." Enforced by the BROWSER. It does not protect against
curl/scripts at all — it protects browser users, not servers; server
protection is auth.

**Q15.** (a) Messages accumulate in the queue (durable, within retention);
when consumers return, they drain the backlog — nothing lost. (b) Retries
exhaust in seconds-to-minutes; requests fail and the data is gone unless
the caller keeps its own persistence. Queues decouple availability: the
producer's success doesn't depend on the consumer being up.

**Q16.** In-memory data-structure store used as cache/session store/queue.
Structures (any two): hash — object fields under one key (user session);
sorted set — leaderboards / rate-limit sliding windows; list — simple
queue/recent-items; set — unique membership (tags, seen-ids); TTL on keys
— expiring caches.

**Q17.** Explains WHAT changed and WHY, imperative subject ≤ ~70 chars,
body for context if needed. Example: `Fix double discount for gold-tier
customers` + body: `Discount was applied in both PricingService and
CheckoutService; removed the checkout-level application. Fixes ORD-1234.`
Any equivalent subject naming the bug and cause earns the mark.

**Q18.** Catch defects early, share knowledge, keep the codebase coherent.
Priority (accept close variants): (1) correctness — logic, edge cases,
error handling; (2) security/data safety — injection, secrets, PII;
(3) design/maintainability — naming, duplication, right layer; style/
formatting last (linter's job). Any three distinct items with sane ordering.

**Q19.** Vertical: bigger machine (more CPU/RAM) — limit: hardware ceiling
+ restart to resize + single point of failure. Horizontal: more instances —
limit: requires statelessness/shared state elsewhere; coordination
complexity. The load balancer enables horizontal.

**Q20.** Separate copies of the system for developing, validating, and
serving users. Staging must mirror prod (same infra shape, config
mechanism, data-ish volume) so validation actually predicts prod behavior.
Divergence bug classes (any one): works-on-H2-fails-on-Postgres (different
DB), config/secret present in staging but missing in prod, load-dependent
issues (pool exhaustion) invisible on tiny staging data.

---

**Interpretation (out of 21; 20 if Q10 is deferred):** 18+ solid; 13–17
targeted review; < 13 record section losses as findings. Q10b is the ACID
retest from E4 — score it honestly.
