# 09 — SQL and Relational Databases

Two skills are tested here and they fail for different reasons. **SQL fluency** fails on NULL logic
and on not recognising that a word problem is a GROUP BY. **Database mechanics** fails on ACID
letters being confused, isolation anomalies not being named, and indexes being treated as magic.
This guide covers both, with the traps marked. Examples are PostgreSQL-flavoured; MySQL differences
are noted where they bite.

---

## 1. Joins

| Join | Returns |
|---|---|
| `INNER` | rows matching on both sides |
| `LEFT` | all left rows; right columns NULL when unmatched |
| `RIGHT` | mirror of LEFT (rewrite as LEFT for readability) |
| `FULL OUTER` | all rows both sides, NULLs where unmatched |
| `CROSS` | cartesian product |
| self join | a table joined to itself, e.g. employee → manager |

**Trap — the LEFT JOIN killed by WHERE.**

```sql
-- Intent: all customers, with their 2026 orders
SELECT c.id, o.id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.created_at >= '2026-01-01';        -- silently an INNER JOIN
```

Unmatched customers have `o.created_at = NULL`, `NULL >= '2026-01-01'` is UNKNOWN, the row is
dropped. **Filters on the outer table belong in the ON clause:**

```sql
LEFT JOIN orders o ON o.customer_id = c.id AND o.created_at >= '2026-01-01'
```

The only `WHERE` clause that is legitimate on the outer side is `WHERE o.id IS NULL` — the
anti-join idiom for "customers with no orders".

---

## 2. Aggregation, GROUP BY, HAVING

Execution order — this explains nearly every "unknown column" error:

```
FROM → JOIN → WHERE → GROUP BY → HAVING → SELECT (aliases created here) → DISTINCT → ORDER BY → LIMIT
```

- `WHERE` filters **rows before grouping**; `HAVING` filters **groups after**.
- Any non-aggregated column in `SELECT` must be in `GROUP BY` (Postgres enforces it; MySQL with
  `ONLY_FULL_GROUP_BY` off returns an arbitrary row — a silent wrong answer).
- **Trap — alias in HAVING/WHERE.** `SELECT COUNT(*) AS n ... HAVING n > 5` fails in Postgres because
  `SELECT` runs after `HAVING`; repeat the expression: `HAVING COUNT(*) > 5`. Aliases *are* usable in
  `ORDER BY` and `GROUP BY`, since those run after / are special-cased.
- `COUNT(*)` counts rows; `COUNT(col)` skips NULLs; `COUNT(DISTINCT col)` deduplicates. The
  difference between the first two is a standard interview probe.
- `SUM` over zero rows returns NULL, not 0 — wrap in `COALESCE(SUM(x), 0)`.

**Recognising aggregation in a word problem.** These phrases mean GROUP BY:
"per / for each / by <noun>" → that noun is the grouping key.
"total, average, count, highest, number of" → the aggregate.
"only those with more than N" → HAVING.
"top N per <noun>" → window function (§ 3), not GROUP BY.

---

## 3. Window functions

A window function computes across a set of rows **without collapsing them**.

```sql
SELECT id, dept, salary,
       ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) AS rn,
       RANK()       OVER (PARTITION BY dept ORDER BY salary DESC) AS rnk,
       DENSE_RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS drnk,
       LAG(salary)  OVER (PARTITION BY dept ORDER BY hired_at)    AS prev_salary,
       SUM(salary)  OVER (PARTITION BY dept ORDER BY hired_at
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM employees;
```

- `ROW_NUMBER` — always distinct (1,2,3,4).
- `RANK` — ties share a rank and leave gaps (1,1,3).
- `DENSE_RANK` — ties share, no gaps (1,1,2).
- `LAG`/`LEAD` — previous/next row's value; the tool for deltas and gap detection.
- Running total needs the frame clause; the default frame with `ORDER BY` is
  `RANGE UNBOUNDED PRECEDING AND CURRENT ROW`, which treats ties as one group — use `ROWS` when you
  mean row-by-row.

**Top-N per group** — the canonical pattern:

```sql
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) rn
  FROM employees
)
SELECT * FROM ranked WHERE rn <= 3;
```

You cannot filter on a window function in `WHERE` (windows are computed after WHERE) — hence the CTE
or subquery. In Postgres, `DISTINCT ON (dept) ... ORDER BY dept, salary DESC` is a faster top-1.

CTEs (`WITH`) name intermediate results and enable recursion (`WITH RECURSIVE` for org charts and
graph walks). Postgres 12+ inlines them; before that they were optimization fences.

---

## 4. NULL and three-valued logic

SQL logic is TRUE / FALSE / **UNKNOWN**, and `WHERE` keeps only TRUE.

- `x = NULL` is UNKNOWN → **zero rows, always**. Use `IS NULL`.
- `NULL <> 'a'` is UNKNOWN, so `WHERE status <> 'active'` **excludes rows where status is NULL**.
  Write `WHERE status IS DISTINCT FROM 'active'` or `(status <> 'active' OR status IS NULL)`.
- `NULL + 1`, `CONCAT` with NULL → NULL (Postgres `||`; MySQL `CONCAT` too).
- Aggregates ignore NULLs; `COUNT(*)` doesn't.
- `UNIQUE` constraints allow multiple NULLs (they aren't equal to each other).
- `ORDER BY` puts NULLs last ascending in Postgres — configurable with `NULLS FIRST/LAST`.

### The NOT IN trap

```sql
SELECT * FROM orders
WHERE customer_id NOT IN (SELECT id FROM banned_customers);   -- returns ZERO rows if any id is NULL
```

`x NOT IN (1, 2, NULL)` expands to `x<>1 AND x<>2 AND x<>NULL` → the last term is UNKNOWN → the whole
AND is UNKNOWN (never TRUE) → nothing matches. `IN` with a NULL is fine for matches but can never
return FALSE, only UNKNOWN.

**Fix — use `NOT EXISTS`**, which is NULL-safe and usually optimizes better (anti-join):

```sql
SELECT * FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM banned_customers b WHERE b.id = o.customer_id);
```

`LEFT JOIN ... WHERE b.id IS NULL` is the third equivalent form.

---

## 5. Constraints are business rules

| Constraint | Guarantees |
|---|---|
| `PRIMARY KEY` | unique + not null + (usually) clustered/indexed identity |
| `FOREIGN KEY` | referential integrity; `ON DELETE CASCADE/RESTRICT/SET NULL` |
| `UNIQUE` | no duplicates — and a **concurrency-safe idempotency mechanism** |
| `CHECK` | domain rule (`amount > 0`, `status IN (...)`) |
| `NOT NULL` | required field |

The point worth making in an interview: **a UNIQUE constraint is the only reliable way to prevent
duplicates under concurrency.** A `SELECT ... if not exists then INSERT` in application code is a
race — two threads both see nothing and both insert. The DB constraint is the arbiter; catch the
duplicate-key error and treat it as success. That is exactly how idempotency keys work
(`12-api-design.md`).

`INSERT ... ON CONFLICT (key) DO UPDATE SET ...` (Postgres) / `INSERT ... ON DUPLICATE KEY UPDATE`
(MySQL) is the atomic upsert; `MERGE` is the standard form.

---

## 6. Indexes

### B-tree mechanics

A balanced tree, typically 3–4 levels deep for millions of rows, with sorted keys in internal nodes
and leaves holding key → row pointer, leaves linked for range scans. Lookup is O(log n) page reads —
in practice 3–4 I/Os instead of scanning the whole table. Because leaves are *sorted*, a B-tree also
serves `ORDER BY`, `>`/`<` ranges, `BETWEEN`, and prefix `LIKE 'abc%'`.

Other types: **hash** (equality only), **GIN** (arrays, JSONB, full-text), **GiST** (geometric,
ranges), **BRIN** (huge append-only tables, tiny index).

### Composite indexes and the leftmost prefix

`INDEX (a, b, c)` sorts by a, then b, then c. It can serve:
- `WHERE a = ?`
- `WHERE a = ? AND b = ?`
- `WHERE a = ? AND b = ? AND c = ?`
- `WHERE a = ? AND b > ?` (range on the last used column)

It **cannot** efficiently serve `WHERE b = ?` alone or `WHERE c = ?` — no leftmost prefix.

**Ordering rule:** equality columns first, then the range/sort column. Once you hit a range predicate,
columns after it can't be used for seeking (only as a filter). So for
`WHERE tenant_id = ? AND created_at > ? ORDER BY created_at`, the index is `(tenant_id, created_at)`.

**Covering index:** if the index contains every column the query needs, the table isn't touched at
all — "index-only scan". `CREATE INDEX ... (tenant_id, created_at) INCLUDE (status)` in Postgres, or
just add the column to the key.

**Partial index:** `CREATE INDEX ON orders (created_at) WHERE status = 'PENDING'` — tiny index for a
hot query over a small subset.

### Why the planner ignores your index

1. **Low selectivity.** Matching >5–20% of the table makes a sequential scan cheaper — random I/O per
   row beats sequential reads only when few rows qualify. This is correct behaviour, not a bug.
2. **Function on the column.** `WHERE LOWER(email) = ?` or `WHERE DATE(created_at) = ?` can't use an
   index on `email`/`created_at`. Fix: an expression index `CREATE INDEX ON users (LOWER(email))`, or
   rewrite as a range (`created_at >= d AND created_at < d+1`).
3. **Leading wildcard.** `LIKE '%foo'` is unindexable by a B-tree (use trigram/full-text).
4. **Implicit type cast.** `WHERE varchar_col = 123` may cast the column, killing the index.
5. **Stale statistics.** The planner's row estimates come from sampled stats; run `ANALYZE`.
6. **`OR` across columns** often defeats a single index; a bitmap OR of two indexes or a `UNION ALL`
   rewrite helps.

### Cost of indexes

Every index must be updated on INSERT/UPDATE/DELETE, consumes memory and disk, and slows writes.
Unused indexes are pure cost — check `pg_stat_user_indexes.idx_scan = 0`. Rule of thumb: index
foreign keys (Postgres does not do it automatically, and unindexed FKs make parent deletes scan),
index high-selectivity WHERE/JOIN/ORDER BY columns, and delete the rest.

---

## 7. Reading a query plan

`EXPLAIN` gives the plan; **`EXPLAIN (ANALYZE, BUFFERS)` actually runs it** and gives real times and
row counts.

Scan nodes, cheapest first: **Index Only Scan** (answered from the index alone), **Index Scan** (seek
then a heap fetch per row; good for few rows), **Bitmap Index Scan + Bitmap Heap Scan** (bitmap of
pages read in physical order — the choice for a medium row count), **Seq Scan** (read everything; fine
for small tables or low selectivity, a red flag on a large table with a selective predicate). Join
nodes: **Nested Loop** (indexed inner side, small outer), **Hash Join** (big unsorted sets),
**Merge Join** (both inputs already sorted).

**What to look at first:** `rows=<estimated>` versus `actual rows=<real>`. A 1000× discrepancy means the
planner is working from bad information — that, not the node type, is the root cause (stale stats,
correlated columns, an unestimable function). Then look for `Sort` with `external merge Disk:` (raise
`work_mem`) and a high `Rows Removed by Filter` (your index isn't selective enough).

---

## 8. Transactions and ACID

A transaction is a unit of work that is all-or-nothing.

| Letter | Meaning | Disambiguator |
|---|---|---|
| **Atomicity** | all statements commit or none do | *partial failure* — crash halfway through a transfer |
| **Consistency** | the DB moves from one valid state to another; constraints hold | *invariants* — a CHECK/FK/uniqueness rule can't be violated by a committed tx |
| **Isolation** | concurrent transactions don't see each other's intermediate state | *concurrency* — two users at once |
| **Durability** | committed data survives a crash | *power loss* — WAL/fsync |

**The confusion to avoid:** "consistency" here is *not* the C in CAP (that one is about replicas
agreeing) and *not* "the data is correct". If the scenario involves two concurrent users, the answer
is **Isolation**, not Consistency. If it's a crash mid-transaction, **Atomicity**. If it's a crash
after the commit returned, **Durability**.

---

## 9. Isolation levels and anomalies

| Anomaly | Meaning |
|---|---|
| **Dirty read** | reading another transaction's uncommitted change |
| **Non-repeatable read** | re-reading the same row gives a different value (someone committed an UPDATE) |
| **Phantom read** | re-running the same query returns new rows (someone committed an INSERT) |
| **Lost update** | two read-modify-writes; the second overwrites the first |
| **Write skew** | both read an overlapping set, both write disjoint rows, jointly violating an invariant |

| Level | Dirty | Non-repeatable | Phantom |
|---|---|---|---|
| READ UNCOMMITTED | possible | possible | possible |
| READ COMMITTED | no | possible | possible |
| REPEATABLE READ | no | no | possible per standard (**not in Postgres/MySQL**) |
| SERIALIZABLE | no | no | no |

Defaults: **Postgres and Oracle = READ COMMITTED. MySQL InnoDB = REPEATABLE READ.** Know your
default; it changes what your code must defend against.

Reality notes: Postgres's REPEATABLE READ is snapshot isolation and does prevent phantoms, but
allows **write skew** (the classic on-call example: two doctors each check "at least one other doctor
is on call" and both go off shift). Postgres SERIALIZABLE (SSI) detects this and aborts one
transaction with a serialization failure — so **your code must be prepared to retry**. MySQL's
REPEATABLE READ prevents phantoms for locking reads via gap locks.

**Lost update is the one you'll be asked about.** `SELECT balance` → compute → `UPDATE balance = ?`
from two sessions loses one. Three fixes:
1. Atomic statement: `UPDATE accounts SET balance = balance - 100 WHERE id = ?` — do arithmetic in SQL.
2. Pessimistic: `SELECT ... FOR UPDATE` before the read.
3. Optimistic: a version column, `UPDATE ... WHERE version = ?`, retry on 0 rows (`08-spring-data-jpa.md`).

---

## 10. Locking, deadlocks, and queues

- `SELECT ... FOR UPDATE` — exclusive row lock until the transaction ends. Others block.
- `FOR NO KEY UPDATE` / `FOR SHARE` — weaker variants.
- `NOWAIT` — error instead of blocking. `SKIP LOCKED` — silently skip locked rows.

**`FOR UPDATE SKIP LOCKED` is how you build a database-backed job queue**, and it's a strong answer
in a design interview:

```sql
UPDATE jobs SET status = 'RUNNING', worker = :id
WHERE id IN (
  SELECT id FROM jobs WHERE status = 'PENDING'
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 10
)
RETURNING *;
```

Each worker grabs a disjoint batch with no coordination, no double processing, no queue infrastructure.

**Deadlock** = two transactions each holding a lock the other wants. The DB detects the cycle and
kills one (`deadlock detected`, SQLState 40P01). Prevention, in order of effectiveness:
1. **Consistent lock ordering** — always touch rows in the same order (e.g. ascending id). Most
   deadlocks are `A then B` versus `B then A`.
2. Keep transactions short; never do network I/O inside one.
3. Lower isolation where safe; use a single atomic statement instead of read-then-write.
4. Retry on deadlock — it's a transient error by definition.

---

## 11. Pagination

`LIMIT 20 OFFSET 100000` must scan and discard 100,000 rows — cost grows linearly with page number,
and rows shift under you when new data is inserted (a user sees the same row twice).

**Keyset (cursor) pagination:**

```sql
SELECT * FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)   -- row-value comparison breaks ties
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Constant time with an index on `(created_at, id)`, stable under concurrent inserts. Cost: no random
page access ("jump to page 500"), which is almost never a real requirement. API-level treatment in
`12-api-design.md`.

Also: `COUNT(*)` for a total on a large table is expensive. Use an estimate (`reltuples`), cache it,
or return "has more" instead of a total.

---

## 12. Connection pooling

Opening a TCP connection + auth + Postgres backend process fork is ~10–100ms. A pool (HikariCP in
Spring Boot) keeps them open.

**Sizing.** The counter-intuitive rule: **small pools are faster.** The often-cited starting formula
is `connections ≈ (core_count × 2) + effective_spindle_count` — roughly 10–20 for a typical service,
not 200. Beyond the DB's ability to run queries in parallel, extra connections just add context
switching and memory (each Postgres connection is a process with its own work_mem).

Fleet math matters: `instances × pool_size` must stay below the server's `max_connections`
(Postgres default 100). Ten replicas × 50 = 500 → connection refused. Use PgBouncer for large fleets.

Key Hikari settings: `maximumPoolSize`, `connectionTimeout` (how long a thread waits before
`SQLTransientConnectionException` — the "pool exhausted" error), `maxLifetime` (must be *less* than
the DB/proxy idle timeout), `leakDetectionThreshold`.

**Pool deadlock:** a request holds a connection and needs a second one (e.g. `REQUIRES_NEW`, or a
transaction that calls a service which opens its own). With N threads each holding one and waiting
for another, the pool is exhausted and nobody can proceed. Rule: a thread that may need two
connections requires `pool_size >= 2 × concurrent_such_threads`, or restructure to need one.

---

## 13. Replication and read-your-writes

A read replica applies the primary's WAL asynchronously — **lag** is typically milliseconds but
spikes under write load. Consequence: write to the primary, immediately read from a replica, and
the user doesn't see their own change.

Fixes: route reads within a session/short window to the primary after a write ("sticky primary");
wait for the LSN the write returned; or use synchronous replication for that path (costs write
latency). In Spring, a routing `DataSource` keyed off `@Transactional(readOnly = true)` is the usual
implementation.

Failover: promoting a replica can lose the un-replicated tail with async replication. Say that
out loud when someone proposes async replication for financial data.

---

## 14. MVCC and VACUUM (Postgres)

Every row version carries `xmin`/`xmax` transaction ids. An UPDATE writes a **new row version** and
marks the old one dead; a DELETE just marks it dead. Readers see the version visible to their
snapshot, so **readers never block writers and writers never block readers**. That's the core of
MVCC and the reason Postgres doesn't need read locks.

The cost is **bloat**: dead tuples accumulate. `VACUUM` reclaims them for reuse (autovacuum does this
in the background); `VACUUM FULL` rewrites the table and takes an `ACCESS EXCLUSIVE` lock — never on a
live table. Long-running transactions are the enemy: they hold back the snapshot horizon, so vacuum
cannot remove tuples any open transaction might still see. An idle-in-transaction connection can bloat
a table until the disk fills. MySQL InnoDB does the same via undo logs and the purge thread.

---

## 15. Zero-downtime schema migrations

Old and new application versions run simultaneously during a rolling deploy, so every migration must
be compatible with both. **Expand / contract:**

1. **Expand** — add the new nullable column / new table. Deploy code that writes both old and new.
2. **Backfill** — in batches, not one statement (a single UPDATE over 50M rows locks and bloats).
3. **Migrate reads** — deploy code that reads the new column.
4. **Contract** — stop writing the old column; in a *later* release, drop it.

Never: rename a column in one step (old pods break instantly), drop a column in the same release
that stops using it, or add a `NOT NULL` column with a default on an old MySQL version (full table
rewrite under lock; Postgres 11+ and MySQL 8 handle the default case instantly via metadata).

Index creation locks writes — use `CREATE INDEX CONCURRENTLY` (Postgres; slower, can't run in a
transaction, can leave an `INVALID` index that you must drop and retry) or `pt-online-schema-change`/
`gh-ost` on MySQL. Always set a short `lock_timeout` on migrations so a blocked DDL doesn't queue
every subsequent query behind it — that specific pattern takes whole services down.

---

## Atomic concept checklist

- [ ] I know a `WHERE` predicate on the outer table of a LEFT JOIN converts it into an INNER JOIN, and I move it to `ON`.
- [ ] I know the logical execution order and can explain why an alias works in ORDER BY but not in HAVING or WHERE.
- [ ] I know `WHERE` filters rows and `HAVING` filters groups.
- [ ] I know `COUNT(*)` counts rows, `COUNT(col)` skips NULLs, and `SUM` of nothing is NULL.
- [ ] I recognise "per/for each X" as GROUP BY and "top N per X" as a window function.
- [ ] I can distinguish ROW_NUMBER, RANK, and DENSE_RANK by their tie behaviour.
- [ ] I know a window function can't be filtered in WHERE, so top-N-per-group needs a CTE or subquery.
- [ ] I know `= NULL` returns zero rows and only `IS NULL` works.
- [ ] I know `<> 'x'` silently excludes NULL rows.
- [ ] I can explain why `NOT IN` with a NULL in the subquery returns zero rows, and I use `NOT EXISTS`.
- [ ] I know a UNIQUE constraint is the only race-free duplicate prevention, and I catch the duplicate-key error rather than pre-checking.
- [ ] I can describe B-tree structure and why lookups are 3–4 page reads.
- [ ] I can state the leftmost-prefix rule and order composite index columns equality-first, range-last.
- [ ] I know what a covering index and a partial index are and when each pays.
- [ ] I can list five reasons the planner skips an index: selectivity, a function on the column, a leading wildcard, a type cast, stale statistics.
- [ ] I know every index taxes writes and that unused indexes are pure cost.
- [ ] I read `EXPLAIN ANALYZE` by comparing estimated rows to actual rows first.
- [ ] I can tell seq scan, index scan, and bitmap heap scan apart and say when each is correct.
- [ ] I can disambiguate ACID: crash mid-transaction is Atomicity, two concurrent users is Isolation, constraint violation is Consistency, crash after commit is Durability.
- [ ] I can name dirty read, non-repeatable read, phantom, lost update, and write skew, and map them to isolation levels.
- [ ] I know Postgres defaults to READ COMMITTED and MySQL InnoDB to REPEATABLE READ.
- [ ] I know snapshot isolation allows write skew and that SERIALIZABLE requires retry logic.
- [ ] I can give three fixes for lost update: atomic UPDATE arithmetic, `FOR UPDATE`, or a version column with retry.
- [ ] I know `FOR UPDATE SKIP LOCKED` implements a job queue with no double processing.
- [ ] I know consistent lock ordering is the primary deadlock prevention, and that deadlock is a retryable error.
- [ ] I know OFFSET pagination costs grow with page number and shift under inserts; keyset pagination is constant time.
- [ ] I can do Hikari sizing math: small pools, `instances × pool_size < max_connections`, `maxLifetime` under the DB idle timeout.
- [ ] I can describe pool deadlock from a thread needing two connections.
- [ ] I know replication lag breaks read-your-writes and can name the sticky-primary fix.
- [ ] I can explain MVCC row versions, why readers don't block writers, and how long transactions block VACUUM and cause bloat.
- [ ] I can walk through expand/contract migration and know `CREATE INDEX CONCURRENTLY` and `lock_timeout`.