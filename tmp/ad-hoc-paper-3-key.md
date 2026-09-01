# Ad-hoc Paper 3 — Answer Key

Scoring: 1 = matches the key's marks · 0.5 = right idea with a named gap ·
0 = wrong or blank · — = `[CODE]` deferred to the code batch.

**Q1.** **Idempotency keys**, end to end:
- **Client sends** a header `Idempotency-Key: <UUID>` that it generates **once
  per logical operation** and **reuses across retries** (a new UUID per retry
  defeats the whole thing).
- **Server, first thing, in one transaction:** `INSERT` a row into an
  `idempotency_keys` table keyed on the key as **primary key**, with status
  `IN_PROGRESS` and a hash of the request body. Insert-first is what makes it
  race-free — the **unique constraint**, not an application-level check, is the
  arbiter. A `SELECT`-then-`INSERT` has a window between the two.
- **On success:** do the work and record the response body and status **in the
  same transaction** as flipping the row to `COMPLETED`. If the charge and the
  key are committed separately, a crash between them loses the protection.
- **Replay (key exists, `COMPLETED`):** do not re-charge; return the **stored
  response**, byte-identical, with the original status code.
- **Concurrent replay (key exists, `IN_PROGRESS`):** the insert fails on the
  primary key; return **409 Conflict** (425 Too Early or 202 with a status URL
  are defensible) — do not block or duplicate.
- **Same key, different body:** the stored request hash doesn't match; return
  **422/400** — the client has a bug, and silently returning the old response
  would be worse.
- Plus: TTL/expiry on the table (24h is typical), and mention that this makes
  the endpoint safe for the client to retry with backoff.
Marks: header + client reuse (0.25), insert-first on a PK constraint (0.25),
work and record in one transaction (0.25), the three branches
replay/in-flight/hash-mismatch (0.25).

**Q2.** (a) **Safe (additive):** adding a new field to a response, adding a new
optional request field, adding a new endpoint, adding a new enum value *only if*
clients were told to tolerate unknowns. **Not safe:** removing or renaming a
field, changing a type (`"12"` → `12`), changing semantics or units, making an
optional request field required, changing a default, tightening validation,
removing an enum value. The rule for this case: **add `firstName`/`lastName` and
keep `customerName` populated** — expand now, contract later. That is
expand/contract for an API, and it means you often need no version at all.
(b) **URI** (`/v2/orders`) — most visible, trivially routable and cacheable,
ugliest, and it versions the whole surface at once. **Header**
(`Accept: application/vnd.acme.v2+json`) — clean URLs, proper content
negotiation, but invisible in a browser and easy to get wrong in caches/CDNs.
**Query** (`?version=2`) — easiest to adopt, but it pollutes the cache key and
is easy to drop accidentally.
(c) Retirement sequence: **announce** with a date and a migration guide → serve
**`Deprecation`** and **`Sunset`** response headers (and log a warning per call)
→ **measure** who is still calling it, by client/API key → **contact** the
remaining callers directly → **brownout**: fail the endpoint for short scheduled
windows so the stragglers notice → **remove**. Never skip the measurement step;
you cannot delete what you can't see.
Marks: (a) 0.5 with at least three of each and the expand/contract answer for
this case; (b) 0.25; (c) 0.25.

**Q3.** (a) It lies to every layer that reads only the status line: proxies,
CDNs and load balancers cache it, client HTTP libraries treat it as success and
never enter their error path, retry and circuit-breaker logic never trips, and
your own error-rate metric reads 0% during an outage. Use the status code — the
protocol already has one.
(b) **RFC 7807 / RFC 9457 problem details**, content type
**`application/problem+json`**. Fields: `type` (a stable URI identifying the
error class — the machine-readable part clients switch on), `title` (short human
summary), `status`, `detail` (this occurrence), `instance`, plus extensions —
crucially a **`traceId`/correlation id** so a user can quote it and you can find
the request, and a structured `errors` array for field violations.
(c) **Stack traces** and **SQL / internal query text** — both are attacker
reconnaissance and neither helps the caller. (Also acceptable: internal
hostnames, other users' data, secrets.)
(d) **All three at once**, in one 400/422 response with a per-field list
(`{"field": "email", "code": "INVALID_FORMAT", "message": "..."}`) — not the
first one and stop. Returning them one at a time turns a form into a
guessing game and N round trips.
Marks: 0.25 each.

**Q4.** (a) **201 Created**, with a **`Location`** header pointing at the new
resource (and usually the representation in the body). (b) **409 Conflict** —
the request conflicts with the current state of the resource; with `ETag`/
`If-Match` optimistic concurrency it is **412 Precondition Failed**. Both
accepted; 400 is not, because the request was well-formed. (c) **403
Forbidden** — identity is established, authorisation failed. 401 would be wrong
and is the classic confusion. (d) **429 Too Many Requests**, with a
**`Retry-After`** header — omitting that header is the half-answer. (e) **202
Accepted**, with a status URL (in `Location` or the body) the client can poll.
Marks: 0.2 each; (b)'s and (d)'s parenthetical are required for the full fifth.

**Q5.** (a) `OFFSET 200000` still **reads and discards 200,000 rows** before
returning 20 — the database cannot skip without counting, so cost grows
linearly with page depth and the last page is the most expensive one. The second
problem is **drift**: if rows are inserted or deleted while the client pages,
the offset window shifts underneath them, so they see duplicates or silently
miss rows. Both are invisible in testing with 1,000 rows.
(b) **Keyset / cursor pagination** — remember the last row's sort key and ask
for what comes after it:
```sql
SELECT * FROM orders
WHERE customer_id = ?
  AND (created_at, id) < (?, ?)     -- the cursor
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
The cursor is the sort key of the last row returned, **opaque and encoded**
(base64 of `created_at|id`) so clients can't construct or depend on it. Backed
by an index on `(customer_id, created_at, id)`, every page costs the same — an
index seek, not a scan. The **tiebreaker** (`id`) is mandatory because
`created_at` is not unique: without it, rows sharing a timestamp straddle the
page boundary and get skipped or repeated, and the ordering isn't deterministic.
(c) Offset gives you **jump-to-page-N and a total count**; cursor gives you
neither, which is why offset survives in admin UIs. Regardless: enforce a
**server-side maximum page size** (a client asking for `limit=1000000` must get
100, not an outage) — and a default when it is omitted.
Marks: (a) 0.25, (b) 0.5 with the tiebreaker justified, (c) 0.25.

**Q6.** (a) A **webhook**. The direction is server→server (your system to the
partner's), it is event-driven and infrequent, and it crosses a **trust
boundary** to a third party you don't control. Polling wastes calls and adds
latency; SSE and WebSocket are browser/client-facing patterns that need a
persistent connection your partner won't hold open. (The general rule: polling
for simple/low-frequency, SSE for server→client streaming to a browser,
WebSocket only when you genuinely need bidirectional, webhook for
server-to-server callbacks.)
(b) The sender must: **retry with exponential backoff and jitter** on failure;
**sign** each payload with an HMAC over the body **plus a timestamp** in a
header (the timestamp is what stops replay); include a stable **event id** and
event type so the receiver can deduplicate; keep a **replayable delivery log**
with attempt history and a manual redelivery path; and treat a slow receiver as
their problem, not yours — timeout aggressively. Also: never send the resource
in the payload only — send an id the receiver can fetch, or accept that payloads
arrive out of order.
(c) The receiver must be **idempotent** (dedupe on the event id — retries and
duplicates are guaranteed), **verify the signature** before doing anything with
the body, and **respond fast**: acknowledge with 2xx immediately and queue the
work, rather than processing inline and timing out the sender into a retry
storm.
Marks: (a) 0.25 with the trust-boundary reasoning, (b) 0.5 for four,
(c) 0.25 for idempotency + signature verification.

**Q7.** (a) **Yes** — `reset --hard` moves the branch pointer and clears the
working tree, but the commit objects are still in the object database and,
crucially, the **reflog** still records where `HEAD` was. Reflog records **every
movement of HEAD**, and unreferenced objects survive until `git gc` prunes
them (default ~30 days for unreachable, 90 for reflog entries).
(b)
```bash
git reflog                       # find the entry, e.g. "HEAD@{1}: commit: ..."
git reset --hard HEAD@{1}        # or: git reset --hard <sha> from the reflog
```
Safer variant: `git branch recovered <sha>` first, inspect it, then reset. If
the reflog has been pruned or you are recovering someone else's branch:
`git fsck --lost-found` finds dangling commits.
(c) **Work that was never committed.** Reflog and fsck only see objects git was
told about; uncommitted working-tree changes destroyed by `reset --hard`, and
untracked files destroyed by `git clean -fd`, are gone irrecoverably. Hence:
commit early and often (and squash later), or `git stash` before anything
destructive.
Marks: reflog named (0.5), correct commands (0.25), the
never-committed exception (0.25).

**Q8.** **`revert`** creates a **new commit** that applies the inverse change —
history is preserved and nothing anyone else has is rewritten. **`reset`** moves
the branch pointer backwards, rewriting local history: `--soft` keeps the index
and working tree, `--mixed` (default) keeps the working tree, `--hard` destroys
both. **`restore`/`checkout`** operates on **files**, not history — discarding
working-tree changes or pulling a file's content from another commit. For a bad
commit already pushed to main: **`git revert <sha>`** — always. Resetting a
shared branch and force-pushing rewrites history other people have based work
on, which is the golden-rule violation.

Reverting a **merge** commit needs a parent: `git revert -m 1 <merge-sha>`
(`-m 1` = keep the first parent, usually main). The trap afterwards: from git's
point of view the branch's commits are still **reachable and already merged**,
so a later `git merge` of that branch is a no-op — it brings nothing back, and
you get a "merged" branch whose changes aren't in the tree. To re-merge you must
**revert the revert** (`git revert <revert-sha>`) and then merge, or rebase the
branch onto new commits.
Marks: three definitions (0.5), revert for pushed (0.25), the re-merge trap
(0.25).

**Q9.** (a) **`git bisect`** — a binary search over history. Each test halves
the candidate range, so it takes **~log₂(300) ≈ 8** tests instead of walking 300
commits. It finds the **first bad commit**, which usually makes the diff small
enough to read directly.
(b)
```bash
git bisect start
git bisect bad                 # current HEAD is broken
git bisect good v2.4           # this tag was fine
# git checks out a midpoint; test it, then:
git bisect good     # or: git bisect bad
# ...repeat ~8 times...
git bisect reset               # return to where you were
```
Automated: `git bisect run ./test.sh` — git drives the whole search itself.
(c) Preconditions: a **deterministic reproducer** (a flaky test bisects to
noise), and **every commit in the range must build and run** — which is the
practical argument for keeping `main` green and for squash-merging one coherent
unit per PR. Exit codes for `bisect run`: **0 = good, 1 = bad, 125 = skip** this
commit (it can't be tested — doesn't build), and 128+ aborts.
Marks: tool + log₂ reasoning (0.25), commands incl. `bisect run` (0.5),
preconditions + 125 (0.25).

**Q10.** (a) **`git push --force-with-lease`.** It checks that the remote ref
still points where your **remote-tracking ref** says it does — i.e. that nobody
has pushed since you last fetched — and **refuses** the push otherwise. Plain
`--force` overwrites unconditionally and silently destroys whatever was there.
Sharp edge worth naming: a blind `git fetch` between your last look and the push
updates the tracking ref and **defeats the lease**; `--force-if-includes`
(git 2.30+) closes that hole.
(b) **Never rebase commits that others have based work on.** Rebasing rewrites
hashes, so everyone else's branch now descends from commits that no longer
exist, and their next merge duplicates everything. Rebase your own unpushed
work freely; merge (or squash-merge) shared history.
(c) During a **rebase**, "ours" and "theirs" are **swapped** relative to
intuition: rebase replays *your* commits on top of the upstream branch, so at
each step "ours" is the **upstream/target** branch (the thing being replayed
onto) and "theirs" is **your commit**. During a normal merge it is the other way
round. Resolve by **reading the content**, never by trusting the label — and
`--ours`/`--theirs` shortcuts during a rebase are where people silently discard
their own work.
Marks: 1/3 each.

**Q11.** (a) **No.** Deleting a secret in a later commit removes it from the
current tree only. It remains in **history** — reachable by `git log -p`, in
every **clone** every colleague has, in **forks**, in **CI caches and build
artifacts**, in GitHub's dangling-object views (a deleted branch's commits stay
reachable by SHA), and in any mirror or backup. Assume it has been scraped:
public repositories are crawled for keys within minutes.
(b) In order:
1. **Rotate the credential** — first, before anything else, and before you tell
   anyone. This is not a git command, and it is the only step that actually
   ends the exposure. Everything after it is cleanup.
2. **Audit for use** — check provider access logs / CloudTrail for calls made
   with that key since the commit date, and treat anything unexpected as an
   incident.
3. **Revoke** the old credential once the new one is deployed.
4. **Rewrite history** with `git filter-repo` (or BFG) to purge the blob, then
   force-push and have every collaborator re-clone; ask the host to garbage-
   collect and expire cached views.
5. Document it in a **blameless postmortem**.
Note the ordering argument: many teams do step 4 first and feel safe — history
rewriting is disruptive, coordination-heavy, and does nothing about a key that
was already copied.
(c) Prevention: **pre-commit secret scanning** (gitleaks, `detect-secrets`) plus
server-side **push protection**; a real **secret store** (Secrets Manager,
Vault) with runtime injection so secrets never exist in the repo shape at all;
`.gitignore` for `.env` files; and periodic history scanning. (Note
`.gitignore` only affects **untracked** files — an already-tracked file needs
`git rm --cached`.)
Marks: (a) 0.25, (b) 0.5 with rotate-first, (c) 0.25.

**Q12.** (a) The loop: **observe precisely** (exact error, exact rate, exact
timing — not "it's broken") → **reproduce** reliably, or instrument until you
can → form a **falsifiable hypothesis** → **predict** what you'd see if it were
true → **test one variable** at a time → **fix the cause**, not the symptom →
add a **regression test** that fails without the fix. Between steps, binary-
search the problem space — code path, timeline, input, environment — rather than
reading everything.
(b) **What changed:** a **deploy** (code), **config or a feature flag**,
**traffic** (volume, shape, a new client), **data** (a new record shape, a
volume threshold crossed, a bad migration), and **infrastructure** (a node,
network, dependency, certificate, or provider change). The sixth, often the
answer: **the date** — month/quarter boundaries, DST, certificate and token
expiry, leap day.
(c) Patterns behind a "random" 1%: it is **one bad instance** (a failure rate
matching **1/(instance count)** is the giveaway — 1 of 8 pods ≈ 12.5%, 1 of 100
≈ 1%); a **specific input** (a null, a unicode name, an empty collection, a
timezone); **timing** (a race, a cold cache after each deploy, a scheduled job,
an hourly token refresh); **stale pooled connections** past an idle timeout;
**clock skew**; or **out-of-order messages**. Techniques to amplify: raise load
or concurrency, inject latency, run the suspect path in a tight loop, shrink
pool sizes and timeouts to make the edge common, or — when you can't reproduce
it at all — **instrument and wait**: log the inputs and correlation id at the
failure point and let production produce the sample. Verify the fix
**statistically with a metric**, because one successful run of a 1% bug proves
nothing.
Marks: (a) 0.25 for an ordered loop with "falsifiable hypothesis" or "one
variable", (b) 0.25 for four-plus categories, (c) 0.5 for three patterns plus an
amplification technique.

**Q13.** (a) H2 is a **different database**, so it passes tests your production
Postgres would fail and vice versa: **dialect and SQL feature differences**
(`ON CONFLICT`, `RETURNING`, JSONB, arrays, CTEs, window-function edge cases,
`ILIKE`) — often papered over by H2's Postgres *compatibility mode*, which is an
approximation, not Postgres; **type and precision differences** (JSON, UUID,
timestamptz, numeric scale, string collation and case sensitivity in `ORDER BY`);
**locking, isolation and MVCC behaviour** — you cannot test `SELECT ... FOR
UPDATE`, `SKIP LOCKED`, deadlock handling, or a lost update honestly on H2; and
**planner behaviour** — no realistic `EXPLAIN`, so index and N+1 problems are
invisible. Net effect: green tests, broken production, and the failures land in
exactly the areas (concurrency and SQL) that are hardest to debug live.
(b) **Testcontainers** with the real Postgres image, pinned to the production
major version. The configuration that keeps it fast: a **static, shared
container** reused across the whole suite (a `static` field with the
JDBC-URL/`@ServiceConnection` wiring, or Testcontainers' reuse flag) so you pay
one startup, **combined with Spring context caching** — the container starts
once, the context is cached, and per-test isolation comes from transaction
rollback or truncation, not from restarting anything.
Marks: (a) 0.5 for three distinct categories, (b) 0.5 for Testcontainers +
static/shared container.

**Q14.** (a) Any four:
- **`@WebMvcTest`** — the web layer only: `DispatcherServlet`, your controllers,
  argument resolvers, Jackson, filters, and Spring Security config. **Not**
  services, repositories, or the data source — collaborators are supplied as
  `@MockitoBean`/`@MockBean`.
- **`@DataJpaTest`** — JPA only: entities, repositories, the `EntityManager`, a
  data source (embedded by default — override for Testcontainers), and Flyway/
  Liquibase. **Not** controllers or `@Service` beans. Each test is wrapped in a
  transaction and **rolled back**.
- **`@JsonTest`** — Jackson/Gson serialisation config, `JacksonTester`. Nothing
  else.
- **`@RestClientTest`** — `RestTemplate`/`RestClient` builders plus
  `MockRestServiceServer`, for testing an outbound HTTP client.
- **`@SpringBootTest`** — the **whole** context (optionally with a real port);
  the integration end of the ladder, not a slice.
(b) The cache key is the **configuration** of the context: the set of
configuration classes, active **profiles**, property sources and
`@TestPropertySource` values, the `ContextCustomizer`s, the web environment
type, and **the set of mock bean definitions**. Two tests with identical keys
share one context; anything that varies the key starts a new one — and each
start costs seconds. The two classic destroyers: **`@DirtiesContext`** (throws
the context away deliberately — sometimes necessary, usually a workaround for a
test that mutates shared state), and **ad-hoc `@MockBean`/`@MockitoBean`
declarations scattered across test classes**, since each distinct combination is
a distinct key. Also: per-class `@TestPropertySource` values and inconsistent
profile sets. Fix: standardise on a small number of context shapes, put shared
mocks in a shared base class or test configuration.
Marks: (a) 0.5 for four with loads/doesn't-load, (b) 0.5 for the key plus two
destroyers.

**Q15.** `[CODE]`
```java
@ExtendWith(MockitoExtension.class)
class ChargeServiceTest {

    private static final Instant NOW = Instant.parse("2026-01-15T10:00:00Z");

    @Mock CustomerRepository customers;
    @Mock PaymentGateway gateway;
    @Mock ReceiptRepository receipts;
    Clock clock = Clock.fixed(NOW, ZoneOffset.UTC);
    ChargeService service;

    @BeforeEach
    void setUp() {
        service = new ChargeService(customers, gateway, receipts, clock);
    }

    @Test
    void savesReceiptWithGatewayReferenceAndFixedTimestamp() {
        var customer = new Customer("c1", "tok_123");
        when(customers.findById("c1")).thenReturn(Optional.of(customer));
        when(gateway.charge("tok_123", new BigDecimal("25.00"))).thenReturn("ref_9");
        when(receipts.save(any(Receipt.class))).thenAnswer(inv -> inv.getArgument(0));

        service.charge("c1", new BigDecimal("25.00"));

        var captor = ArgumentCaptor.forClass(Receipt.class);
        verify(receipts).save(captor.capture());
        Receipt saved = captor.getValue();
        assertThat(saved.reference()).isEqualTo("ref_9");
        assertThat(saved.customerId()).isEqualTo("c1");
        assertThat(saved.amount()).isEqualByComparingTo("25.00");
        assertThat(saved.chargedAt()).isEqualTo(NOW);
    }

    @Test
    void rejectsNonPositiveAmountWithoutCallingGateway() {
        assertThatThrownBy(() -> service.charge("c1", BigDecimal.ZERO))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("positive");
        verifyNoInteractions(customers, gateway, receipts);
    }

    @Test
    void throwsWhenCustomerMissingAndDoesNotCharge() {
        when(customers.findById("nope")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.charge("nope", new BigDecimal("10.00")))
            .isInstanceOf(CustomerNotFound.class);
        verifyNoInteractions(gateway);
        verify(receipts, never()).save(any());
    }
}
```
Marks: **`Clock.fixed` injected** so the timestamp is assertable at all (0.25 —
asserting "not null" or using `Instant.now()` in the test loses this);
**`ArgumentCaptor`** used to assert on the saved object's fields rather than
`verify(receipts).save(any())` (0.25); all three cases present with the
exception type asserted, not just that *something* threw (0.25); the negative
verifications — the gateway must not be called when validation or lookup fails,
which is the whole point of those two tests — and `isEqualByComparingTo` for the
BigDecimal rather than `equals` (0.25). Compiles and runs, or it is scored as
the code session was.

**Q16.** (a) 85% line coverage says **85% of your lines were executed** while
the tests ran. It does **not** say they were **asserted** — a test that calls
every method and asserts nothing scores identically to a thorough one. It also
says nothing about branch or path coverage, about whether the assertions check
the right thing, or about the value of the untested 15% (which is often the
error handling that matters most). Coverage is useful as a **floor and a
trend**, useless as a target — Goodhart applies the moment it becomes a gate.
The technique that measures the difference is **mutation testing** (PIT for
Java): it mutates the bytecode — flips a conditional, changes a return — and
checks whether any test **fails**. A surviving mutant is a line that is executed
but not actually verified.
(b) Four, with fixes:
- **Timing / `Thread.sleep`** — waiting a fixed period for async work. Fix:
  **Awaitility's `untilAsserted`** with a timeout, or inject a synchronous
  executor so the work happens inline.
- **Shared mutable state or test-order dependence** — one test leaves a row, a
  static, or a mocked singleton behind. Fix: isolate — fresh fixtures per test,
  transaction rollback, `@DirtiesContext` as a last resort, and run the suite in
  random order to expose it.
- **Real clock / date dependence** — a test that breaks at month end, across
  DST, or at midnight UTC. Fix: **inject `Clock`** (and any random/UUID source).
- **Real network or external services** — DNS, a sandbox API, a public
  container registry. Fix: mock the boundary, or use Testcontainers/WireMock so
  the dependency is local and deterministic.
- (Also accepted: concurrency races in the code under test — the test is
  honestly reporting a real bug; unordered collection assertions —
  `assertThat(list).containsExactlyInAnyOrder(...)`; hardcoded ports —
  use port 0.)
(c) Because **retrying hides the signal without removing the cause**. If the
flake is a real race, a stale connection, or an ordering bug, retrying means
production hits it and the test suite promised you it wouldn't — the retry
converts a caught defect into an uncaught one. And it decays the suite: once
retries are normal, nobody investigates, the flake rate creeps up, and the team
stops trusting red builds at all. A flaky test is **worse than no test**,
because it costs attention and returns noise. Quarantine it (out of the blocking
build, with an owner and a deadline) or delete it — but do not paper over it.
Marks: 1/3 each.

**Q17.** (a) The task definition names a **task role**; the ECS agent obtains
**temporary credentials** for it from **STS** via `AssumeRole`, and exposes them
on a link-local **credentials endpoint** — the SDK finds it through the
`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` environment variable (on EC2 it is the
**IMDSv2** endpoint at `169.254.169.254`; on EKS it is IRSA/Pod Identity via a
projected service-account token). The credentials are an access key, secret and
**session token**, valid for a short period (roughly an hour), and the SDK's
default credential provider chain **refreshes them automatically** before
expiry. **Nothing is on disk** and nothing is in your configuration — that is
the point.
(b) A long-lived access key in an env var is a **static secret**: it appears in
the task definition (readable by anyone with `ecs:DescribeTaskDefinition`), in
CI logs, in `docker history` if baked into the image, in heap dumps and crash
reports; it does not expire, so a leak is permanent until someone notices; it
must be rotated manually, which means in practice it isn't; and it is
indistinguishable from a legitimate call once stolen. Role credentials expire on
their own, are scoped to the workload, and produce CloudTrail entries tied to
the role session.
(c) **The explicit Deny wins.** Evaluation order: an **explicit `Deny`
anywhere** (identity policy, resource policy, SCP, permissions boundary, session
policy) overrides everything → otherwise an **explicit `Allow`** grants it →
otherwise **implicit deny**, the default for anything not allowed. Corollary:
you cannot grant your way out of a Deny, which is what makes SCPs and
permissions boundaries useful as guardrails.
Marks: 1/3 each; naming "temporary credentials, auto-rotated, nothing on disk"
is the core of (a).

**Q18.** (a) The connection **establishes and then hangs** — that is the
signature of a **NACL** problem, not a security group one. Security groups are
**stateful**: allowing inbound on 8080 automatically permits the return traffic.
**NACLs are stateless**: each direction is evaluated separately, so if the
subnet's NACL allows inbound 8080 but has no **outbound rule for the ephemeral
port range** (1024–65535), the SYN and the handshake get through but the
responses are dropped. Layer: the subnet/network ACL. (Also accepted with
reasoning: an application-layer hang — B accepted the connection and is blocked
on a lock or a downstream, and your client has **no read timeout** so it waits
forever. A good answer distinguishes the two by whether *any* other request to B
succeeds.)
(b) An immediate **timeout with no response** means packets are being
**dropped silently** — the two likely causes are a **security group** that
doesn't allow the inbound port (the default behaviour for a disallowed packet is
drop, not reject) and a **route table / subnet** problem (no route to the
target, wrong subnet, no NAT for egress, or the wrong VPC entirely). Contrast
with **connection refused**, which is an RST from a reachable host with nothing
listening — that is an app or port problem, not a network one. The tool:
**VPC Flow Logs** — they show ACCEPT/REJECT per flow, and the answer is almost
always a security group or a route table. (`VPC Reachability Analyzer` is the
better modern answer if offered.)
(c) **JVM DNS caching.** RDS failover is **DNS-based**: the endpoint name is
repointed at the standby's IP, and the DB is back in ~40 s. But the JVM caches
successful DNS lookups **according to `networkaddress.cache.ttl`**, which with a
security manager historically defaulted to **`-1` — cache forever** — so the JVM
keeps dialling the dead IP indefinitely, long after the OS resolver and every
other client have moved on. Compounding it, the connection **pool** holds
sockets to the old address and hands them out without validating them.
Fix: set `networkaddress.cache.ttl` explicitly (30–60 s) as a JVM property or in
`java.security`, set `networkaddress.cache.negative.ttl` low too, and configure
the pool to **validate connections** on borrow (Hikari's `connectionTestQuery`/
validation plus a `maxLifetime` shorter than any upstream idle timeout) so stale
sockets are discarded rather than reused. This is the same mechanism the
networking guide flags for any DNS-based failover, not just RDS.
Marks: 1/3 each; (a) requires the stateful/stateless contrast to score full.

---

## Section mapping (for the valuation)

| Section | Questions | Topic guide |
|---|---|---|
| 1 API contracts and evolution | Q1–Q6 | `12-api-design.md` |
| 2 Git craft and debugging | Q7–Q12 | `17-git-craft.md` |
| 3 Testing in practice | Q13–Q16 | `16-testing.md` |
| 4 AWS mechanics | Q17–Q18 | `18-cloud-aws.md` |

Expected range: **6–9/18.** API basics have scored consistently well (E1 Q13/Q14,
E2 Q11/Q13, E4 Q13, M1 Q13 all full marks), so Section 1 is the one that could
surprise upward — if Q1–Q5 land above 3.5, topic 12 is stronger than
"UNMEASURED specifics" implies and the LLD-round concern in `tmp/gaps.md` §3.1
softens. Section 2 contains the direct retest for the M5 Q18 blank (git
recovery, Q7/Q8) and should be read as the measurement for that HIGH gap.
Q15 follows the deferred-code policy — batch it, do not skip it, since it is the
same shape as M4 Q17.