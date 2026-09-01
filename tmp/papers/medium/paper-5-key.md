# Medium Paper 5 — Answer Key

**Q1.** Sliding window with `Map<Character,Integer>` (char → last index) or
a set: right pointer advances; on seeing a repeat inside the window, left
jumps to `max(left, lastIndex + 1)`; answer = max window size seen.
Invariant: `[left..right]` never contains a duplicate. O(n): each pointer
moves forward only. Marks: all three test cases pass; the `max(left, ...)`
guard (not just `lastIndex + 1`) shows real understanding.

**Q2.** Array-backed binary min-heap (complete tree via index math:
children at 2i+1/2i+2). `peek` O(1); `offer`/`poll` O(log n) (sift up/
down). `remove(Object)` must first FIND the element — the heap property
orders parent/child only, so search is linear O(n). Direct iteration gives
array order, NOT sorted order — only `poll`-ing drains in priority order.

**Q3.** (1) `final` class (or all constructors private + static factories)
— prevent subclass mutability; (2) `final` fields, no setters; (3)
defensive copy of mutable constructor args (`this.start = new
Date(start.getTime())`) — caller can't mutate your state via the reference
they kept; (4) defensive copy (or immutable view) in getters — never hand
out the internal mutable object; (5) validate invariants in the
constructor (start ≤ end). Any four; using immutable types instead
(`LocalDate`) as the modern fix earns the defensive-copy point if the
reasoning is stated.

**Q4.** Any four with concrete use: records — DTOs/value objects without
boilerplate, auto equals/hashCode; sealed interfaces — closed event/command
hierarchies; pattern-matching switch — exhaustive handling over sealed
types, compiler catches missing cases; virtual threads — thread-per-request
for I/O-heavy services without pool tuning; text blocks — readable SQL/JSON
in tests; `var` — noise reduction on obvious local types; Streams
`toList()`; `Optional` returns for maybe-absent lookups.

**Q5.**
```java
private static volatile Config instance;
static Config get() {
    if (instance == null)
        synchronized (Config.class) {
            if (instance == null) instance = new Config();
        }
    return instance;
}
```
Without `volatile`: instruction reordering can publish the reference BEFORE
the constructor's writes complete — another thread sees non-null `instance`
and reads a half-constructed object. `volatile` forbids that reordering
(happens-before on the write). (Bonus: enum singleton / holder-class idiom
as simpler alternatives.)

**Q6.** (1) `Java heap space` — heap exhausted: leak or undersized heap;
(2) `unable to create new native thread` — thread count hit OS/memory
limits: unbounded thread creation; (3) `Metaspace` — class-metadata growth:
classloader leaks (redeploys, dynamic proxies). (Also accepted: `GC
overhead limit exceeded` — GC thrashing; direct buffer memory.) Flag:
`-XX:+HeapDumpOnOutOfMemoryError` (+ `HeapDumpPath`) — capture the dump at
the moment of death for MAT analysis.

**Q7.** The service method's transaction ended → the persistence context
closed → the `items` collection is an uninitialized Hibernate proxy with no
session to load from; Jackson touches it during serialization → exception.
Fixes ranked: (1) map to a DTO inside the transaction — best: explicit
boundary, no entity leakage; (2) fetch eagerly FOR THIS QUERY (`JOIN
FETCH` / `@EntityGraph`) when items are genuinely needed; (3)
open-session-in-view or broadening `@Transactional` to the controller —
works but drags DB sessions through rendering (OSIV trade-off); (global
EAGER is the wrong fix — degrades every other query).

**Q8.** As written: 1 (findAll) + 200 (one per `getBooks()` access) = 201
queries. Fixes: (1) `@Query("select a from Author a join fetch a.books")`
or `@EntityGraph(attributePaths = "books")` — one joined query; (2)
aggregate DTO projection — `select a.name, count(b) ... group by a.name`
(best here: only the COUNT is needed, skip loading books entirely); (3)
batch fetching — `@BatchSize(size = 50)` / global batch size → 1 + 4
IN-queries. Any three mechanisms.

**Q9.** OFFSET doesn't skip — the engine walks the index/heap through all
1,000,020 rows, discarding the first million, every single page. Keyset:
```sql
SELECT * FROM t
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
Seeks directly into the composite index at the cursor position — O(log n +
20) regardless of depth. `id` is the tie-breaker making the sort total and
the cursor stable.

**Q10.** Lost update: both read 100, both write 40 — one debit vanished
(final balance should be −20 or the second should fail). READ COMMITTED
only guarantees you read committed data; the read and the write are
separate statements — nothing links the UPDATE to the value read. Fixes
(any two): atomic in-database update — `UPDATE accounts SET balance =
balance - 60 WHERE id = 1 AND balance >= 60` (check rows affected);
pessimistic — `SELECT ... FOR UPDATE` then update in the same transaction;
optimistic — version column, `UPDATE ... WHERE version = :read_version`,
retry on 0 rows.

**Q11.** WebSocket: starts as an HTTP GET with `Upgrade: websocket` +
`Connection: Upgrade` headers; server responds `101 Switching Protocols`;
the TCP connection is then reused as a persistent full-duplex frame
channel. Polling better: infrequent updates, simplest infra, proxies/LBs
everywhere work — e.g., checking a batch-job status every 30s. SSE better:
server→client only, auto-reconnect built in, plain HTTP — e.g., live feed/
notifications where the client never sends upstream. WebSocket earns its
complexity for true bidirectional low-latency (chat, collaborative
editing, games).

**Q12.** Readiness-based I/O multiplexing: `epoll` (Linux). The thread
registers thousands of sockets with the kernel and makes ONE blocking call
(`epoll_wait`) that returns the handful of sockets ready RIGHT NOW; it
services those and loops. No thread ever blocks on an individual idle
connection. Thread-per-connection parks one thread (stack + scheduling
cost) per idle socket — 10k connections = 10k mostly-sleeping threads;
epoll = a few event-loop threads total, connections are just fd
registrations. (kqueue/IOCP as platform analogs = bonus.)

**Q13.** Token bucket: bucket of capacity B refilled at R tokens/sec; each
request takes a token; empty bucket → reject. Allows short bursts (B) with
sustained rate R. Client sees `429 Too Many Requests` + `Retry-After` (and
ideally `X-RateLimit-Limit/-Remaining/-Reset`). Ten instances: per-instance
buckets give 10× the intended limit and inconsistent behavior → centralize
state (Redis with atomic Lua/INCR-EXPIRE) or accept approximation (local
buckets at limit/10, or sticky routing by API key).

**Q14.** Client credentials grant. (1) Partner's backend authenticates
directly to the authorization server with its client_id + client_secret
(no user, no browser); (2) AS returns an access token scoped to that
client; (3) partner calls your API with the bearer token, which you
validate like any JWT (issuer, audience, scopes). Implicit: tokens exposed
in browser URL fragments, no client authentication — superseded by auth
code + PKCE. Password grant: the client handles the user's raw credentials
— breaks the entire delegation model and trains users to type passwords
into third parties.

**Q15.** After consumption: queue — message deleted, gone for everyone;
log — message remains until retention expiry, consumer just advances its
offset. Second consumer app: queue — it would compete for/steal messages
(you'd need to add fan-out infrastructure like SNS in front); log — new
consumer group reads the full stream independently, zero producer changes.
Reprocessing: queue — impossible, messages are gone; log — rewind offsets
to yesterday and replay. Implication: queue for one-consumer task
distribution (simpler ops); log when multiple readers, replay, or
event-history matter.

**Q16.** Local: no network hop (microsecond reads), no extra infra, no
serialization cost. Distributed: one coherent copy across all 6 instances,
survives instance restarts, memory paid once not 6×. Hybrid (near cache):
small short-TTL local cache in front of Redis — hot keys served locally,
Redis as the shared source. Remaining problem: local layers can serve
stale values within their TTL after another instance updates Redis —
cross-instance invalidation needs a pub/sub broadcast or acceptance of
bounded staleness.

**Q17.** (a) `when(mock.method())` actually CALLS the method while
stubbing — on spies (real objects) or void methods that throw, use
`doReturn/doThrow/doNothing().when(mock).method()`. (b) A captor grabs the
ACTUAL argument object passed to the mock for detailed assertions
afterward — e.g., capture the `EmailMessage` sent to `mailer.send(...)` and
assert its subject, recipient, and body separately; matchers can only gate
the call, not inspect the object richly. (c) Verifying every stubbed
interaction restates the implementation — tests become change-detectors
that break on refactors; verify only interactions that ARE the behavior
(the side effect you promised), assert state/results otherwise.

**Q18.** (a) `git revert <sha>` — creates a new inverse commit; safe on
shared history, no force-push. (b) `git restore path` (or legacy
`git checkout -- path`), with `git restore --staged` first if staged —
targets one file's working state. (c) `git reset --hard HEAD~2` —
rewriting is fine because the commits were never shared; the branch
pointer simply moves back.

**Q19.** OOMKilled = the KERNEL killed the process for exceeding the
container's cgroup memory limit — the JVM gets no chance to throw anything;
`OutOfMemoryError` = the JVM itself failing to allocate within ITS heap
limit. Beyond heap, the container limit counts: metaspace, thread stacks,
direct/NIO buffers, code cache, GC overhead, native libs — a 512MB-heap
JVM can easily use 800MB+. Fixes: set `-XX:MaxRAMPercentage` (e.g., 75%)
so the JVM sizes itself off the container limit (modern JVMs are
container-aware), and/or raise the container limit to heap + realistic
off-heap headroom; explicitly cap metaspace/direct memory where relevant.

**Q20.** Page on symptoms users feel, at thresholds indicating action:
error rate above X% for N minutes; p99 latency breaching SLO; (also
accepted: checkout success-rate drop, dependency hard-down). Dashboard
only: CPU utilization, GC time, cache hit ratio, disk space trends —
causes, not symptoms; they explain a page, they shouldn't BE one (they
fire without user impact → alert fatigue → real pages ignored). p99 over
average: averages hide the tail — 1% of checkouts timing out is invisible
in the mean but is exactly the pain (and often the highest-value users);
alerting must see the distribution's edge.

---

**Interpretation:** 16+ strong; 11–15 typical with gaps to list; < 11
record failed sections as findings.
