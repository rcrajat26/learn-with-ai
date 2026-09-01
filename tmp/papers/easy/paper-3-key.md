# Easy Paper 3 — Answer Key

**Q1.** HashMap: no defined iteration order; get/put O(1) average. TreeMap:
sorted by key (natural order or comparator); get/put O(log n) (red-black
tree).

**Q2.** Data must be sorted (on the search key). The halving step relies on
"if mid < target, the target can only be right of mid" — unsorted data
breaks that inference. 1,000,000 elements → ~20 comparisons (log₂ 10⁶).

**Q3.** Variable: no reassignment after initialization. Method: no override
in subclasses. Class: no subclassing at all. A `final List` field: the
REFERENCE can't be reassigned, but the list contents can still be mutated —
final ≠ immutable.

**Q4.** Differences (any two): primitives hold values, wrappers are objects
(heap, can be null); primitives can't be null; boxing/unboxing cost;
wrappers have methods/constants. Only-wrapper: generic collections —
`List<Integer>`, not `List<int>` (also nullable DB columns mapped to
entities).

**Q5.** Heap: all objects and arrays, shared across threads →
`OutOfMemoryError: Java heap space`. Stack: per-thread frames — local
variables, call chain → `StackOverflowError` (typically runaway recursion).

**Q6.** Each of two threads holds one lock and waits forever for the other's.
Thread 1: holds A, wants B; Thread 2: holds B, wants A — circular wait,
neither releases. (Any correct two-lock, opposite-order narrative.)

**Q7.** Opens (or joins) a database transaction before the method body.
Endings: normal return → commit; a runtime exception escaping the method →
rollback. (Bonus if noted: checked exceptions do NOT roll back by default.)

**Q8.** Makes "might not exist" explicit in the type — callers are forced
to handle absence (`orElseThrow`, `map`, `isPresent`) instead of forgetting
a null check and getting a `NullPointerException` far from the cause.

**Q9.** Primary key: unique + non-null identifier of each row, one per
table. Foreign key: value must match an existing key in the referenced
table (referential integrity). Unique constraint: no duplicate values in the
column(s), but unlike PK it's not the row's identity and (in most DBs)
allows NULLs.

**Q10.** A separate sorted structure (typically B-tree) mapping column
values → rows, letting the DB find matches without scanning the table.
Speeds: lookups, range queries, sorts, joins on that column. Costs: extra
storage and slower writes (every INSERT/UPDATE/DELETE maintains it).

**Q11.** HTTPS = HTTP over TLS: encryption (confidentiality), integrity,
and server authentication (certificate). Against plain HTTP an on-path
attacker can: read everything (credentials, cookies, tokens) and modify
traffic (inject content, redirect, tamper).

**Q12.** `top` (or `htop`) — live per-process CPU/memory, sortable. Stop:
`kill <PID>` sends SIGTERM (polite — process may clean up); `kill -9 <PID>`
sends SIGKILL (forceful — immediate, no cleanup).

**Q13.** Authentication: establishing who the caller is (credentials,
token) — failure → 401. Authorization: whether that identity may perform
this action — failure → 403.

**Q14.** Executing it once or N times leaves the same end state. Idempotent
by contract: GET, PUT, DELETE (HEAD/OPTIONS too); POST is not. Matters
because clients and proxies retry on timeout — retrying an idempotent call
is safe, retrying a POST may duplicate the effect.

**Q15.** Producer: publishes messages. Consumer: receives/processes them.
Broker: the middleman that stores and routes (SQS, Kafka, RabbitMQ). If
consumers are down, messages accumulate in the broker (up to
retention/queue limits) and are processed when consumers return — nothing
is lost in the meantime.

**Q16.** Hit: requested key found in cache; miss: not found → fetch from
source. 15% is probably not helping — 85% of reads pay cache lookup + the
DB read. Check: TTL too short, key design mismatched to access pattern
(over-specific keys), caching data that's rarely re-read, or cache too
small (evictions).

**Q17.** Verifies GOLD-tier customers get 10% off (100 → 90). Good practice
(any one): given-when-then/AAA structure; behavior-describing test name;
`isEqualByComparingTo` for BigDecimal (value, not scale, comparison —
`equals` would fail on 90.0 vs 90.00).

**Q18.** Any two: changes are reviewed before landing (quality, knowledge
sharing); `main` stays releasable — broken work-in-progress is isolated;
CI validates the branch before merge; enables discussion/audit trail.

**Q19.** Region: a geographic area (e.g., eu-west-1) containing multiple
AZs. AZ: one or more physically separate datacenters within the region,
independent power/network. Two AZs → a datacenter-level failure doesn't
take your service down (and LB/RDS failover work across AZs).

**Q20.** Reverting production to the previous known-good version. Enablers
(any two): immutable versioned artifacts/images (redeploy the old tag —
no rebuild); previous version kept warm (blue/green); DB migrations kept
backward-compatible so old code runs against the new schema; automated
deploy pipeline (rollback is one command, not a manual ritual).

---

**Interpretation:** 17+ solid; 12–16 targeted review; < 12 record section
losses as findings.
