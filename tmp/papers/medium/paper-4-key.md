# Medium Paper 4 — Answer Key

**Q1.** Binary search on the boundary:
```java
int firstBad(int n) {
    int lo = 1, hi = n;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (isBad(mid)) hi = mid; else lo = mid + 1;
    }
    return lo;
}
```
Marks: converges without infinite loop, `lo + (hi-lo)/2` overflow guard,
correct at both boundaries. Off-by-one fixed only after testing = 0.5.

**Q2.** (a) `TreeSet`/`TreeMap` — `ceiling(x)` in O(log n) with sorted
inserts. (b) `HashMap` counts + min-heap of size 10 — O(n log 10). (c)
`HashMap` (value→index) + `ArrayList` with swap-to-end deletion — the
classic RandomizedSet design. (d) monotonic deque — front always holds the
window max, amortized O(1) per step.

**Q3.** Correct: `Optional<User> findByEmail(String email)` — forces
callers to handle absence. Abuses (any two): `Optional` fields in entities/
DTOs (not serializable-friendly, wrong tool); `Optional` method parameters
(callers pass `Optional.empty()` — just overload); calling `.get()` without
checking; wrapping collections (return empty collection instead).
`orElse(loadDefault())` ALWAYS evaluates `loadDefault()` even when the
optional is present; `orElseGet` evaluates the supplier only on empty —
matters when the default is expensive or has side effects.

**Q4.** Binary floating point can't represent most decimal fractions
exactly (0.1 has no finite base-2 representation) — cents drift under
arithmetic. `new BigDecimal(0.1)` converts the ALREADY-inexact double →
0.1000000000000000055511...; use `new BigDecimal("0.1")` or `valueOf`.
`equals` compares value AND scale — `1.0` ≠ `1.00`; `compareTo` compares
numeric value only — `compareTo == 0`. Hence `isEqualByComparingTo` in
tests and never `equals` for amount comparison (nor as HashMap keys with
mixed scales).

**Q5.** `synchronized` block around the increment — correct for compound
invariants involving multiple fields; costs lock contention.
`AtomicInteger.incrementAndGet()` — lock-free CAS, ideal at low/moderate
contention for a single variable. `LongAdder` — striped cells summed on
read; wins under HIGH write contention where CAS retry-storms hurt, at the
cost of heavier reads and no compareAndSet semantics. Choice axis:
invariant complexity and contention level.

**Q6.** Per-thread variable — each thread sees its own copy. Legitimate:
per-request context (user id, correlation id, transaction resources —
Spring uses it heavily), non-thread-safe helpers like `SimpleDateFormat`
(historically). Pool leak: pooled threads never die, so a ThreadLocal set
during request A survives and is visible to unrelated request B (stale
data/security bleed) and pins referenced objects forever (memory leak).
Discipline: `try { set } finally { remove() }` on every request boundary.

**Q7.** The persistence context is an identity map: the second
`findById(42)` finds the managed instance and runs ZERO additional SQL —
one query total. The batch job: every loaded entity stays strongly
referenced (and snapshot-copied for dirty checking) in the context for the
whole transaction → memory grows linearly → OOM, and flushes get slower.
Fix: process in chunks with periodic `entityManager.flush(); clear();`
(or use streaming with detach, or read-only/stateless sessions, or
paginate with separate transactions).

**Q8.** `merge` loads (or creates) a MANAGED copy of the entity, copies the
detached object's state onto it, and returns the managed copy — the
argument remains detached. Classic bug: continuing to mutate the original
argument after merge — changes silently ignored; always use the return
value. Spring Data `save`: if the entity "is new" (null id / new
`Persistable.isNew()`), `persist`; otherwise `merge`.

**Q9.**
(a)
```sql
SELECT * FROM (
  SELECT p.*, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) rn
  FROM payments p
) t WHERE rn = 1;
```
(`DISTINCT ON (user_id) ... ORDER BY user_id, created_at DESC` also full
mark for Postgres.)
(b)
```sql
SELECT user_id, created_at::date AS day, COUNT(*)
FROM payments WHERE status = 'FAILED'
GROUP BY user_id, created_at::date
HAVING COUNT(*) >= 2;
```

**Q10.** Check-then-act across two statements: two concurrent requests both
SELECT-find-nothing and both INSERT → duplicate-key error (or double row
without the constraint). The race window can't be closed in app code
without locks. Postgres:
`INSERT ... ON CONFLICT (key_col) DO UPDATE SET ...` — atomic in one
statement, backed by the unique constraint. (MySQL:
`INSERT ... ON DUPLICATE KEY UPDATE`.)

**Q11.** Layers: (1) the JVM's own InetAddress cache — historically caches
successful lookups FOREVER when a security manager was present, or per
`networkaddress.cache.ttl`; (2) OS/resolver caches honoring (or a local
resolver ignoring) the record's TTL; (also connection pools holding
ESTABLISHED connections to the old IP — pools don't re-resolve until
connections are recycled). JVM fix: set `networkaddress.cache.ttl` to a
small value (and cap connection max-lifetime so pooled connections get
re-established, forcing re-resolution).

**Q12.** `top`/`htop`: load average vs cores — load 8 on 8 cores ≈
saturated, on 32 cores ≈ fine; %us (app) vs %sy (kernel) vs %wa (waiting
on disk I/O). High %wa with modest %us = disk-bound, not CPU-bound —
check `iostat -x` (utilization, await). Memory: `free -h` — read
"available" (page cache is reclaimable; low "free" alone is normal);
swapping (`vmstat` si/so) = real memory pressure. Per-process:
`ps aux --sort=-%cpu` / `--sort=-%mem`.

**Q13.** (a) Sessions need shared server-side state — sticky sessions or a
session store (Redis) to scale; JWT is self-contained — any instance
validates with the key: trivially scalable. (b) Sessions revoke instantly —
delete the server record; JWTs can't be revoked without reintroducing
state (denylist, short expiry + refresh tokens) — revocation is JWT's
structural weakness. (c) Session: id in cookie, data on server; JWT: claims
in the token itself (readable! no secrets). Choose sessions for classic
same-origin web apps needing instant revocation; JWT for APIs,
service-to-service, multi-service SSO — with short TTLs.

**Q14.** The SQL text (with `?` placeholders) is parsed and planned FIRST;
parameter values are sent separately afterward and bound as pure data into
the already-compiled plan — they are never re-parsed as SQL, so input can't
change the query's structure. Concatenation mixes data into code before
parsing. XSS analog: contextual output encoding (+ CSP) — treat data as
data at the point of rendering, never concatenate it into executable
HTML/JS context.

**Q15.** After an outage, all failed clients retry on synchronized
schedules — identical backoff means they return in waves that re-flatten
the recovering service (retry storm / thundering herd). Jitter randomizes
each client's delay, spreading the wave into a smooth trickle. Full answer
mentions: backoff caps (max delay), retry budgets/circuit breaking so
retries stop amplifying a dying dependency.

**Q16.** (1) Distributed lock around the job (Redis SETNX / ShedLock /
DB advisory lock) — simple, but lock expiry vs long jobs needs care.
(2) Leader election — one instance runs all scheduled work; extra moving
part. (3) Extract the job to a dedicated single-instance worker (or
platform-level cron: K8s CronJob, EventBridge) — cleanest, costs infra.
(Also acceptable: make the job idempotent so triple-running is harmless —
plus any one mechanism.)

**Q17.** Shape (marks for all three behaviors + fixed Clock + exception
assertion):
```java
Clock fixed = Clock.fixed(Instant.parse("2025-06-01T00:00:00Z"), ZoneOffset.UTC);
// due: stub repo.findById → active sub expiring 2025-06-05 → assertTrue,
//      verify(repo).save(...) or state change
// not due: expiring 2025-08-01 → assertFalse, verify no save
// unknown: repo returns Optional.empty() →
//      assertThrows(NotFoundException.class, () -> service.renewIfDue("x"))
```
`Thread.sleep`, real `now()`, or missing verify on the not-due case → 0.5.

**Q18.** Not gone (yet). Commits are objects in `.git`; `reset --hard` only
moved the branch pointer — the commits became unreferenced, garbage-
collected only much later. `git reflog` records every HEAD movement: find
the pre-reset entry, then `git reset --hard HEAD@{1}` (or cherry-pick /
branch from the SHA). Reflog as "the undo log for git" is the mark.

**Q19.** Each Dockerfile instruction produces a layer; a layer is rebuilt
only if the instruction or its input files changed — and all LATER layers
rebuild with it. Order stable → volatile: base image, then dependency
manifests (`pom.xml`) + dependency resolution (`mvnw dependency:go-offline`),
THEN `COPY src` + build. Result: editing source re-runs only compile, not
dependency download. (Multi-stage build noted = bonus.)

**Q20.** New instance starts → readiness probe held until warm (context up,
pools connected) → LB adds it to the target group. Old instance: LB marks
it draining — no NEW requests, in-flight requests get a drain window →
platform sends SIGTERM → app stops accepting, finishes in-flight work,
closes pools (graceful shutdown enabled), exits → grace period expiry
would bring SIGKILL if it hung → instance terminated. Order matters:
deregister BEFORE terminate, readiness gate BEFORE receiving traffic.

---

**Interpretation:** 16+ strong; 11–15 typical with gaps to list; < 11
record failed sections as findings.
