# Medium Paper 2 — Answer Key

**Q1.** Growth doubles capacity (~1.5× in ArrayList), so copies happen at
geometrically increasing intervals: total copy work across n adds is
n/2 + n/4 + ... ≈ n → O(n) total, O(1) per add on average. Term: amortized
analysis.

**Q2.** One pass with a `HashMap<Integer,Integer>` of value→index: for each
`nums[i]`, if `target - nums[i]` is in the map return both indices, else
put `nums[i] → i`. O(n): single pass, O(1) average map operations. Handles
duplicates correctly because the complement is checked before inserting.

**Q3.** Throws `ConcurrentModificationException` (usually): the for-each
uses an `Iterator`; `list.remove` bumps `modCount`; the iterator's next
`hasNext()/next()` detects the mismatch (fail-fast). Correct ways:
`l.removeIf(s -> s.equals("b"))`; explicit iterator with `it.remove()`.
(Streams-filter-to-new-list also acceptable.)

**Q4.** Generic type parameters exist only at compile time; the compiler
erases them to their bound (usually `Object`) and inserts casts — hence no
`new T[]`, no `instanceof List<String>`, no runtime knowledge of `T`. PECS:
`copy(List<? super T> dest, List<? extends T> src)` — the source PRODUCES
Ts (extends: can read T, can't safely add), the destination CONSUMES Ts
(super: can add T, reads only as Object). Maximizes caller flexibility.

**Q5.** Lock-order deadlock: transfer(A,B) and transfer(B,A) concurrently —
each holds one lock, waits on the other, forever. Fix: acquire in a global
canonical order, e.g., lock the account with the smaller id first
regardless of direction. (tryLock-with-timeout-and-retry also accepted.)

**Q6.** Tasks first fill core threads; once all core threads are busy, new
tasks go to the QUEUE; only when the queue is FULL are threads added up to
max; beyond that, the rejection policy fires. Unbounded queue → the queue
is never full → max pool size is never reached (extra threads never
created) and the queue can grow until OOM under sustained overload.

**Q7.** Problem 1: shared mutable state in a singleton accessed by
concurrent request threads + the scheduler → race conditions/corruption
(ArrayList isn't thread-safe). Problem 2: state is in-memory only — lost
on restart/deploy, wrong with >1 instance (each has its own list).
Restructure: persist pending work (DB table with status, or a queue);
if in-memory is truly acceptable, at minimum a concurrent structure — but
the durable/multi-instance answer is the real one.

**Q8.** Transient: new object, JPA unaware. Managed: attached to the
persistence context — the session-scoped identity map/first-level cache
that tracks entities and guarantees one instance per id. Detached: context
closed/cleared; changes no longer tracked. Removed: scheduled for delete.
Managed entities are dirty-checked at flush/commit — modifications are
written automatically, so `save()` adds nothing (it's a merge/no-op on an
already-managed instance).

**Q9.** Returns 0 rows regardless of data. `NOT IN (…NULL…)` means
`dept_id <> NULL AND ...` — comparison with NULL is UNKNOWN, so no row
satisfies the predicate. Safe rewrite: `NOT EXISTS (SELECT 1 FROM
excluded_departments x WHERE x.dept_id = e.dept_id)` (or filter NULLs in
the subquery).

**Q10.** Any four: (1) low selectivity — predicate matches a large fraction
of rows, sequential scan is cheaper than index + heap fetches; (2) function
or cast on the column (`lower(email) = ...`) — doesn't match the plain
index, needs a functional index; (3) leading-wildcard `LIKE '%@x.com'` —
B-tree can't seek without a prefix; (4) stale statistics misestimating
row counts; (5) type mismatch forcing implicit conversion; (6) table so
small the scan is cheaper.

**Q11.** Each closed connection leaves the client-side socket in TIME_WAIT
(~60s) holding an ephemeral port; high connection churn exhausts the
ephemeral port range → new connections can't bind. Structural fix:
connection reuse — keep-alive with a pooled HTTP client (one warm
connection instead of thousands of one-shot ones). Kernel tunables are a
band-aid, pooling is the answer.

**Q12.** Goals: (1) authenticate the server — certificate chain validated
against trusted CAs; (2) agree on fresh symmetric session keys — key
exchange; (3) integrity — MAC'd records. Asymmetric crypto is orders of
magnitude slower, so it's used only to authenticate and establish the
shared secret; bulk traffic is encrypted symmetrically with the session
keys.

**Q13.** Validate: signature against the expected algorithm and key (reject
`alg: none`, pin expected alg — prevents algorithm-confusion attacks),
`exp` (and `nbf`), `iss` is your trusted issuer, `aud` is this service
(a valid token for service A must not work at service B). Base64 payload is
by design: JWTs provide integrity/authenticity, not confidentiality — the
signature proves the trusted issuer created it and nothing was altered;
never put secrets in claims.

**Q14.** The request is non-simple (Authorization header + JSON
content-type) → the browser first sends an `OPTIONS` preflight with
`Origin`, `Access-Control-Request-Method/-Headers`. The API must respond
with `Access-Control-Allow-Origin: https://app.example.com`,
`-Allow-Methods`, `-Allow-Headers` (and `-Max-Age` to cache the decision);
only then does the browser send the real request. No — CORS is enforced by
browsers to protect users; curl/scripts ignore it entirely. API protection
= authentication.

**Q15.** The event carries a stable unique id (producer-assigned event id /
business key). Consumer inserts into a `processed_events(event_id UNIQUE)`
table — or writes the business row keyed by it — IN THE SAME DATABASE
TRANSACTION as the business write. Redelivery hits the unique constraint →
skip/no-op. Race-proof because the constraint is enforced by the DB
atomically with the write; an in-memory "seen" set fails on restart and
across instances.

**Q16.** Cache stampede / thundering herd. Mitigations (any three): TTL
jitter — randomize expiries so hot keys don't expire in sync; single-flight
/ per-key mutex — one request loads, others wait or serve stale;
refresh-ahead — asynchronously renew before expiry; serve-stale-while-
revalidate; request coalescing; negative caching for not-found storms.

**Q17.** Any four with matching fix: order/shared-state dependence → isolate
fixtures, reset state per test; async race (`Thread.sleep`) → Awaitility /
latches / deterministic executors; time dependence → injected fixed Clock;
external service/network → Testcontainers or fakes; leftover DB rows →
per-test transaction rollback or truncation; concurrency in code under
test → control the executor.

**Q18.** Merge: ties branches with a merge commit, history preserved as it
happened. Rebase: replays your commits onto a new base — rewrites them
(new SHAs), linear history. Golden rule: never rebase commits others may
have based work on (shared branches). Force-push acceptable only on your
own feature branch after a deliberate rewrite; `--force-with-lease` refuses
to overwrite commits you haven't seen (someone else pushed meanwhile) —
always prefer it over blind `--force`.

**Q19.** Any four: (1) `openjdk:latest` — unpinned base, unreproducible
builds, surprise upgrades; (2) secret baked via ENV — visible in
`docker history`/inspect and to anyone with the image; inject at runtime;
(3) `COPY . ` before the build — any source change invalidates the
dependency-download layer (and likely no `.dockerignore`, bloating
context); copy pom, resolve deps, then copy src; (4) runs as root — larger blast radius if the
container is compromised; add a non-root user; (5) single-stage — ships JDK +
sources; multi-stage with a JRE runtime image is smaller and safer; (6) no
HEALTHCHECK/JVM memory flags.

**Q20.** Build once, configure at runtime (12-factor). Non-secret config:
environment variables or mounted config (per-environment values in the
deploy platform / parameter store). Secrets: a secrets manager
(AWS Secrets Manager / Vault / K8s Secrets) injected at runtime as env vars
or mounted files by the platform, access-controlled via the service's IAM
role. Never in (any two): source control, image layers (ENV/ARG at build),
logs, client-visible payloads.

---

**Interpretation:** 16+ strong; 11–15 typical with gaps to list; < 11
record failed sections as findings.
