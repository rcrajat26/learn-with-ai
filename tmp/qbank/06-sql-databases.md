# 06 — SQL & Databases

**What this decides:** whether SQL drills become mandatory in the prep plan
(ORM-only experience is the common 3–4 YOE blind spot), and how much runway
indexing/transactions theory needs.

Schema for Part A (create it in a scratch Postgres/SQLite or solve on paper):

```sql
CREATE TABLE departments (id INT PRIMARY KEY, name TEXT);
CREATE TABLE employees (
  id INT PRIMARY KEY, name TEXT, dept_id INT REFERENCES departments(id),
  salary NUMERIC, hired_on DATE, manager_id INT REFERENCES employees(id)
);
CREATE TABLE orders (
  id INT PRIMARY KEY, employee_id INT REFERENCES employees(id),
  amount NUMERIC, created_at TIMESTAMP
);
```

---

## Part A — Write the query `[OPEN-EDITOR]` (5 min each)

### A1 [L2] Join + filter
Employees (name, department name) hired in 2024 in departments named
'Engineering' or 'Platform', newest hire first.
**Key points:** correct JOIN, `IN`/OR on dept name, `ORDER BY hired_on DESC`.

### A2 [L2] Aggregate + HAVING
Departments with more than 5 employees and average salary above 100000 —
return dept name, headcount, avg salary.
**Key points:** GROUP BY, HAVING (not WHERE) for aggregate conditions,
joining back to get the name. Bonus: knows WHERE-vs-HAVING evaluation order.

### A3 [L3] Top-N per group
The top 2 earners in each department (name, dept, salary).
**Key points:** window function —
`ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC)` in a
subquery/CTE, filter `<= 2`. Correlated-subquery solutions score 0.5 (work,
but window fluency is what's being tested). **This is the highest-signal
query in the file** — window-function blindness is the classic ORM-only tell.

### A4 [L3] Duplicates
Find employee names that appear more than once, with their counts.
**Key points:** `GROUP BY name HAVING COUNT(*) > 1`. Fast and clean = 1.

### A5 [L3] Second-highest + running total (two short queries)
(a) Second-highest distinct salary. (b) Per employee: orders with a running
total of `amount` by `created_at`.
**Key points:** (a) `OFFSET 1` on ordered DISTINCT, or `DENSE_RANK` — must
handle ties; (b) `SUM(amount) OVER (PARTITION BY employee_id ORDER BY
created_at)`.

**Part A placement:** 4.5–5 → SQL fluent, drills optional. 3–4 → drills
recommended. ≤ 2.5 → **SQL drills mandatory, add to gaps.md as high severity**
(some companies run a dedicated SQL screen).

---

## Part B — Mechanisms & traps

### B1 [L2] explain-back — Why does a B-tree index make range queries fast,
and why does column order matter in a composite index?
**Strong answer:** sorted tree, O(log n) descent to the start of a range then
sequential leaf scan; composite `(a, b)` is sorted by `a` then `b` within —
usable for `a=`, `a= AND b=`, `a` range; NOT for `b` alone (leftmost-prefix
rule). Bonus: index-only scans when the index covers the query.

### B2 [L2] explain-back — Five reasons the optimizer ignores your index
**Strong answer (any 4):** low selectivity (predicate matches a large
fraction — seq scan cheaper); function/cast on the column
(`WHERE lower(email) = ...` without a functional index); leading-wildcard
`LIKE '%x'`; stale statistics; type mismatch; tiny table. Naming
*selectivity* explicitly is the discriminator.

### B3 [L3] predict-output — NULL traps
```sql
SELECT count(*) FROM employees WHERE dept_id NOT IN (SELECT id FROM departments WHERE name <> 'HR');
```
The `departments` subquery result happens to contain a NULL id (bad data).
What does the outer query return? Also: does `WHERE salary <> 100000` include
rows where salary IS NULL?
**Strong answer:** `NOT IN` with a NULL in the list returns no rows —
`x <> NULL` is UNKNOWN, so nothing satisfies the predicate; use `NOT EXISTS`.
And no — NULL fails every comparison; needs `IS NULL` handling. Three-valued
logic by name = bonus.

### B4 [L3] matching — Isolation levels ↔ anomalies
Define dirty read, non-repeatable read, phantom read; state which of
READ COMMITTED / REPEATABLE READ / SERIALIZABLE permit which. What's
Postgres's default?
**Strong answer:** correct matrix; RC default in Postgres; bonus: Postgres
RC never dirty-reads (MVCC), REPEATABLE READ in PG is snapshot isolation
(no phantoms, but write skew possible — naming write skew is L4 signal).

### B5 [L3] spot-the-bug — LEFT JOIN quietly becomes INNER
```sql
SELECT d.name, count(e.id)
FROM departments d
LEFT JOIN employees e ON e.dept_id = d.id
WHERE e.hired_on > '2024-01-01'
GROUP BY d.name;
```
The report is supposed to show ALL departments, zero-count included. What's
wrong?
**Strong answer:** the WHERE filter on the right table discards the
NULL-extended rows → inner-join semantics; move the condition into the ON
clause (or filter with `COUNT(*) FILTER (...)`). Also `count(e.id)` vs
`count(*)` distinction earns bonus.

### B6 [L4] discriminator — Pagination at depth
`ORDER BY created_at DESC LIMIT 20 OFFSET 1000000` is slow. Why, and what's
the fix?
**Strong answer:** OFFSET scans and discards a million rows every page;
keyset/seek pagination — `WHERE (created_at, id) < (:last_seen_at, :last_id)
ORDER BY ... LIMIT 20` with a matching composite index; needs a stable tie-
breaker column; trade-off: no random page jumps. Cursor-vs-offset from the
API side ties to file 08.

### B7 [L4] scenario — Connection pool sizing
Your service has HikariCP `maximum-pool-size=100` against a Postgres with
`max_connections=100`, and three more service instances are being added.
What goes wrong and how do you size properly?
**Strong answer:** 4×100 threatens 400 connections against a 100 cap →
connection storms/refusals; each PG connection is a process with real memory
cost; pools should be small (cores-based intuition, Hikari's guidance —
often < 20); size = per-instance pool × instances < max_connections with
headroom; PgBouncer when many services share a DB. The "more connections ≠
more throughput" insight is the point.

---

## Breadth checklist (rate 0–3)

- [CORE] `EXPLAIN` / `EXPLAIN ANALYZE` — have you ever actually run one?
- [CORE] Transactions from application code — where BEGIN/COMMIT actually happen with Spring
- [CORE] CTEs (`WITH`) — read and write
- [CORE] Indexes on foreign keys — why they don't come free (in Postgres) and what missing ones cost
- [CORE] UNIQUE constraints as business rules (idempotency keys, natural keys)
- Window functions beyond ROW_NUMBER (LAG/LEAD, RANK vs DENSE_RANK)
- UPSERT (`INSERT ... ON CONFLICT`)
- Normalization (1NF–3NF concept) + when you'd deliberately denormalize
- DB-level deadlocks — seen one? how detected/resolved?
- Locking reads (`FOR UPDATE`, `FOR UPDATE SKIP LOCKED` for queues)
- JSON/JSONB columns — when reasonable, when a schema smell
- Views / materialized views
- Query plans: seq scan vs index scan vs bitmap heap scan (recognize the words?)
- VACUUM / autovacuum, table bloat (0–1 fine)
- Partitioning (0–1 fine)
- Read replicas + replication lag — what breaks read-your-own-writes
- NoSQL exposure: used DynamoDB/Mongo/Redis as a datastore? Which, how deep?
