# Syllabus — 09 SQL and Relational Databases

**Target version: PostgreSQL 18 (GA 25 September 2025) as the primary flavour, MySQL 8.4 LTS /
InnoDB as the contrast flavour, SQL:2016 as the language baseline with SQL:2023 additions marked.**
Every constant, GUC name, default value, lock name, catalog column and error code below is stated
against that baseline. Three newer lines exist and change several things this topic teaches, so every
divergence is marked `[VERSION-TRAP]` inline and the write pass must state what is true in the
PG 18 / MySQL 8.4 baseline *and* what changed after:

- **PostgreSQL 19** (beta 1 released 4 June 2026, GA expected late 2026) — SQL/PGQ property-graph
  queries, `GROUP BY ALL`, `ON CONFLICT DO SELECT`, parallel autovacuum
  (`autovacuum_max_parallel_workers`) plus an autovacuum scoring system, the new `REPACK` command for
  online table rewrite, `pg_plan_advice`/`pg_stash_advice` for plan stabilisation, auto-scaling
  `io_method=worker`, and ~2× faster inserts when foreign-key checks are present. `[RESEARCH]`
- **MySQL 9.7.0 LTS** (April 2026) — first LTS after 8.4; folds the 9.x innovation stream in.
  Hypergraph optimizer support for complex queries, in-database JavaScript, JSON duality views with
  DML, OpenID authentication, dynamic data masking (Enterprise), and several previously-Enterprise
  replication observability features (applier metrics, Group Replication flow-control statistics,
  resource manager, primary election, telemetry) moved into Community Edition. `[RESEARCH]`
- **SQL:2023** — a new `JSON` data type with dot-notation access, `JSON_SERIALIZE`, `JSON_SCALAR`,
  `IS JSON`, 14 new SQL/JSON methods, and **Part 16: Property Graph Queries (SQL/PGQ)** with
  `GRAPH_TABLE`/`MATCH`. Almost none of it is in PostgreSQL 18 or MySQL 8.4; say so rather than
  teaching it as available. `[RESEARCH]`

The five deltas that most often produce a stale answer in an interview are: **PostgreSQL's
`REPEATABLE READ` is snapshot isolation and does not permit phantoms** (so the textbook anomaly
table is wrong for the two databases you will actually use), **`EXPLAIN ANALYZE` now prints
`BUFFERS` by default in PG 18** (so every "always add BUFFERS" blog post is now noise),
**`effective_io_concurrency` and `maintenance_io_concurrency` defaults changed from 1 to 16 in
PG 18** (with the whole new AIO subsystem behind `io_method`), **B-tree *skip scan* in PG 18 means
"a composite index is useless without its leading column" is now only mostly true**, and
**`SERIAL` is superseded by identity columns** while `md5` password authentication is deprecated with
warnings.

Scope boundary against the sibling guides. This file owns **the relational model, the SQL language,
the query pipeline, indexing, physical storage, transactions and concurrency control, durability and
recovery, operational maintenance, replication, partitioning, and the SQL-layer face of a Java
client**.

Owned elsewhere:

- The persistence context, entity states, dirty checking, lazy loading, JPQL/Criteria, repository
  derivation, `@Transactional`'s interaction with the `EntityManager`, JPA-level locking annotations
  and the ORM's N+1 problem live in `08-spring-data-jpa.md`. This guide owns the SQL those
  mechanisms emit and the database behaviour underneath them. `[X-REF 08]`
- The `@Transactional` interceptor, proxy mechanics, propagation semantics and self-invocation live
  in `07-spring-core.md`. `[X-REF 07]`
- CAP/PACELC, quorum arithmetic, consistent hashing, the outbox pattern as a distributed-systems
  primitive, storage-selection procedure and the SQL-vs-NoSQL decision at architecture level live in
  `22-system-design.md`. This guide states each mechanism once and points there. `[X-REF 22]`
- Cache stores (Redis, Caffeine), stampede prevention and invalidation topology live in
  `15-caching.md`; this guide owns only the database's own caches. `[X-REF 15]`
- TCP, TLS, keep-alive, DNS and network timeouts live in `10-networking.md`. `[X-REF 10]`
- Page cache, `fsync` at the kernel level, the OOM killer, cgroup memory accounting, `iostat`/`strace`
  live in `11-operating-systems-linux.md`. `[X-REF 11]`
- Heap sizing, GC pressure from large result sets and heap-dump workflow live in
  `06-jvm-internals.md`. `[X-REF 06]`
- AuthN/AuthZ, OWASP, secrets management and TLS configuration live in `13-web-security.md`; this
  guide owns SQL injection at the SQL/JDBC layer, privileges, and row-level security.
  `[X-REF 13]`
- API pagination contracts, error payloads and idempotency-key HTTP semantics live in
  `12-api-design.md`. `[X-REF 12]`
- Kafka, queues, delivery semantics and CDC consumption live in `14-messaging-queues.md`; this guide
  owns logical decoding as a database mechanism. `[X-REF 14]`
- Testcontainers mechanics and test slices live in `16-testing.md`. `[X-REF 16]`
- RDS/Aurora specifics, parameter groups and managed-failover behaviour live in `18-cloud-aws.md`.
  `[X-REF 18]`
- Metrics/tracing practice, SLOs and alerting live in `20-observability-operations.md`; this guide
  owns the database's own statistics views. `[X-REF 20]`
- Big-O, B-tree as an abstract data structure and heap/hashing fundamentals live in
  `01-dsa-fundamentals.md`; this guide owns the *disk-oriented* variants. `[X-REF 01]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

**Every example, table name, column name, status code and number comes from the QuizStakes domain in
`src/scenario/scenario.md`** — `fundsledger.ledger_entry`, `fundsledger.position`,
`fundsledger.reservation`, `cardpayments.transactions`, `bankwithdrawal.transactions`,
`bankwithdrawal.payment_run`, `accountopening.application`, `accountmaintenance.account`,
`clientrestrictions.restriction`, `documentrequirements.document_requirement`. Never `employees`,
`orders`, `customers`, `foo`, or `dept`. The load figures the bible must use are the real ones from
Appendix A: **19.8M ledger entries/day, 7.2B/year, 230 writes/sec sustained, 13,600/sec peak,
~180 bytes/row, ~1.3 TB/year growth, 90-day hot window, 7-year retention, 2.8M stake reservations/day
at 1,200/sec with 3,400/sec settlement bursts, 95k card deposits/day at 40/sec, 2.4M registered
clients, 3 `FundsLedger` instances at 12 GB heap, a 30 ms restriction-decision budget, a 150 ms
stake-reservation budget and a hard 500 ms self-exclusion budget.**

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real documentation, spec text, source comment or catalog definition (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or complete runnable SQL where the artifact is SQL) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in PG 18 / MySQL 8.4 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte arithmetic explicitly |
| `[GUC]` | give the exact PostgreSQL parameter / MySQL system variable name and its default |
| `[SQL]` | must show real SQL, not a description of SQL |
| `[PLAN]` | must show real `EXPLAIN`/`EXPLAIN ANALYZE`/`EXPLAIN FORMAT=JSON` output and read it line by line |
| `[DIAG]` | must show real diagnostic output — an error message with SQLSTATE, a `pg_locks` row, a `SHOW ENGINE INNODB STATUS` excerpt, a log line — and read it line by line |
| `[MYSQL]` | the MySQL/InnoDB behaviour differs and must be stated alongside, not omitted |
| `[JDBC]` | must state the exact JDBC API, property or driver behaviour |

---

# PART 1 — BASICS

## §1.1 Why a relational database exists at all

1.1.1 The 1970 problem statement: applications were coupled to the physical layout of their data
      (IMS hierarchies, CODASYL network sets), so every schema change broke every program. Codd's
      answer was **physical/logical independence** — declare *what* you want, let the system decide
      *how*. `[PROVE]`
1.1.2 Codd's 1970 paper "A Relational Model of Data for Large Shared Data Banks" as the origin
      document, and the two things it actually contributed: the relation as the sole data structure,
      and a closed algebra over relations. `[SOURCE]`
1.1.3 What a relational database buys you, each attributed to a mechanism: declarative querying (the
      optimizer), physical independence (the planner and access methods), invariant enforcement
      (constraints), all-or-nothing units of work (transactions), crash survival (WAL), and
      concurrency without hand-written locking (MVCC / the lock manager).
1.1.4 What it costs: a fixed schema you must migrate, a planner that can pick badly and does so
      opaquely, single-writer scaling limits, and an abstraction that leaks the moment the data
      exceeds one machine.
1.1.5 The **QuizStakes framing for this whole guide**: `FundsLedger` chooses a relational store not
      for convenience but because "entries sum to zero", "`CASH_AVAILABLE` never negative" and
      "one idempotency key produces one effect" are *constraints and transactions*, which is
      precisely what this technology is. Appendix B states it plainly: "Constraints and transactions
      *are* the product." `[SOURCE]`
1.1.6 The three-schema architecture (ANSI/SPARC): external (views), conceptual (logical schema),
      internal (physical storage). Naming it explains why `CREATE VIEW` and `CREATE INDEX` are
      different kinds of change. `[PROVE]`
1.1.7 The pipeline end to end, named at every arrow, because every later section is one arrow on
      this diagram: client → wire protocol → parser → analyser/rewriter → planner (cost model +
      statistics) → executor → access methods → buffer pool → storage, with WAL, the lock manager,
      MVCC and vacuum running underneath. `[FLOW]`
1.1.8 SQL is a *standard* with no conforming implementation. Every claim in this guide must be
      attributed: standard SQL, PostgreSQL, or InnoDB. Saying "SQL does X" without saying which is
      the most common way to be confidently wrong. `[TRAP]`
1.1.9 The engine taxonomy you should be able to place any product in: disk-oriented row store
      (PostgreSQL heap, InnoDB), log-structured (RocksDB/MyRocks), column store (ClickHouse, Redshift,
      Parquet-backed), in-memory (VoltDB, SAP HANA), and where "NewSQL" (CockroachDB, Spanner, TiDB,
      Yugabyte) sits. `[X-REF 22]`
1.1.10 Why *this* guide is PostgreSQL-first: process-per-connection, heap + separate indexes, MVCC by
       row versioning in the heap, and a visible planner — every mechanism is inspectable from SQL.
       Then why InnoDB must be learned as a contrast: clustered index, undo-log MVCC, gap locks,
       `REPEATABLE READ` default. `[MYSQL]`
1.1.11 The interview framing this guide serves: turning "the query is slow / returned the wrong rows /
       deadlocked / lost an update" into a named mechanism — a plan node, a missing statistic, a
       lock mode, a snapshot, or a constraint that was never declared.
1.1.12 The reading list, ranked, with what each is for: the PostgreSQL manual (normative, and the best
       database documentation in existence), *Designing Data-Intensive Applications* ch. 7 (isolation
       done right), Markus Winand's *SQL Performance Explained* / use-the-index-luke.com (indexing as
       a development task), *Database Internals* (storage and replication), Suzuki's *The Internals of
       PostgreSQL* (interdb.jp — MVCC, SSI, vacuum), CMU 15-445 lectures (the systems curriculum), and
       Hironobu/Postgres Pro's *Queries in PostgreSQL* series (planner and statistics). `[SOURCE]`
      `[RESEARCH]`

*(12 leaves)*

## §1.2 The relational model, precisely

1.2.1 The vocabulary in both registers, mapped one-to-one: relation/table, tuple/row,
      attribute/column, domain/type, relation schema/table definition, relation instance/table
      contents, degree/column count, cardinality/row count.
1.2.2 A relation is a **set** of tuples: no duplicates, no order. SQL tables are **bags** with
      optional order — the single most consequential deviation of SQL from the model, and the reason
      `DISTINCT`, `UNION` vs `UNION ALL` and `ORDER BY` exist at all. `[TRAP]` `[PROVE]`
1.2.3 Codd's twelve rules (0–12) named, with the three that matter in practice: rule 2 (guaranteed
      access by table + column + primary key), rule 3 (systematic NULL treatment), rule 8/9
      (physical and logical data independence). No product satisfies all thirteen. `[RESEARCH]`
1.2.4 The **information principle**: all information is represented as values in relations — no
      hidden pointers, no positional identity. This is why "the row's rowid" is an implementation
      detail (`ctid`, `ROWID`) and never part of your model. `[TRAP]`
1.2.5 Relational algebra, the eight operators with their symbols and SQL spellings: selection (σ →
      `WHERE`), projection (π → `SELECT` list), rename (ρ → `AS`), union (∪), difference (−
      → `EXCEPT`), intersection (∩), cartesian product (× → `CROSS JOIN`), natural join (⋈).
      `[SQL]`
1.2.6 Derived operators and what they are shorthand for: theta join, equi-join, semi-join (⋉ →
      `EXISTS`/`IN`), anti-join (▷ → `NOT EXISTS`), outer joins, division (→ "clients who hold every
      required document type"), aggregation (γ). `[SQL]`
1.2.7 **Closure**: every operator takes relations and returns a relation, which is why subqueries,
      CTEs and views compose without special cases. `[PROVE]`
1.2.8 Relational calculus (tuple and domain) as the declarative counterpart, and Codd's completeness
      theorem: the algebra and the calculus express exactly the same queries. Why this matters — it
      licenses the optimizer to replace your algebra with a different, equivalent algebra.
      `[PROVE]`
1.2.9 What the algebra **cannot** express, and therefore what SQL had to add non-algebraically:
      transitive closure (hence `WITH RECURSIVE`), aggregation, ordering, and windowing.
1.2.10 The QuizStakes model expressed as relations: `account(id, client_id, lifecycle, opened_at)`,
       `position(account_id, type, balance, version)`, `movement(id, idempotency_key, reason,
       posted_at)`, `ledger_entry(id, movement_id, position_ref, direction, amount, posted_at)`.
       Read §11.1 and Appendix C.2 for the field lists and use them verbatim. `[SQL]`
1.2.11 The functional-dependency notation `X → Y` and how to read it aloud, because §1.3 is
       unintelligible without it. In QuizStakes: `movement_id → idempotency_key`, and
       `(account_id, type) → balance`.
1.2.12 Armstrong's axioms — reflexivity, augmentation, transitivity — plus the derived union,
       decomposition and pseudo-transitivity rules, and the closure algorithm `X⁺` that they license.
       This is the machinery that makes normalization decidable rather than a matter of taste.
       `[PROVE]`
1.2.13 Candidate key defined via FDs: a minimal attribute set whose closure is every attribute.
       Superkey = any set whose closure is everything; candidate key = a minimal superkey.
1.2.14 What "the relational model" does *not* say anything about: indexes, storage, order, physical
       clustering, or performance. Every performance decision in this guide is therefore outside the
       model — which is exactly why it is legitimate to change it without changing query results.
       `[PROVE]`

*(14 leaves)*

## §1.3 Normalization

1.3.1 The problem normalization solves, stated as three named anomalies, each with a QuizStakes
      instance: **insertion** anomaly (cannot record a `PaymentRun` before any withdrawal exists in
      it), **update** anomaly (the client's legal name copied into every `ledger_entry` row must be
      changed 7.2B times), **deletion** anomaly (removing the last withdrawal for a run erases the
      run's approver record). `[PROVE]`
1.3.2 **1NF**: every attribute holds a single atomic value from its domain; no repeating groups, no
      arrays-as-CSV. The honest caveat: "atomic" is domain-relative, and PostgreSQL arrays/JSONB
      deliberately break 1NF for good reasons. `[TRAP]`
1.3.3 **2NF**: 1NF plus no non-prime attribute is functionally dependent on a *proper subset* of a
      candidate key. Only ever violated when the key is composite. QuizStakes example: a
      `payment_run_item(run_id, withdrawal_id, run_opened_at)` where `run_opened_at` depends on
      `run_id` alone.
1.3.4 **3NF**: 2NF plus no transitive dependency of a non-prime attribute on a key. Example: keeping
      `jurisdiction_age_threshold` on `application` when it depends on `jurisdiction`.
1.3.5 **BCNF**: every non-trivial FD's determinant is a superkey. The difference from 3NF stated
      precisely, with the classic overlapping-candidate-key example, and the honest fact that BCNF
      can force you to lose dependency preservation. `[PROVE]`
1.3.6 **4NF** and multi-valued dependencies: the QuizStakes case is the genuine many-to-many between
      `document_requirement` and `document` (§8.6 — one document satisfies several requirements, one
      requirement needs several documents). Storing both in one table produces a cartesian mess.
1.3.7 **5NF / project-join normal form** and join dependencies: rare, worth naming once so you can
      say what it is and why you have never needed it.
1.3.8 **6NF** and the anti-join-decomposition extreme, plus where it does show up in practice:
      temporal/bitemporal modelling and column stores.
1.3.9 **DKNF** (domain-key normal form) as the theoretical limit: every constraint is a consequence
      of domain and key constraints alone.
1.3.10 The **lossless-join** property and how to check a binary decomposition (the common attribute
       set must be a superkey of one fragment). Show a lossy decomposition producing spurious rows.
       `[PROVE]`
1.3.11 **Dependency preservation** and the 3NF synthesis algorithm (minimal cover → one relation per
       FD → add a key relation) versus the BCNF decomposition algorithm. State that 3NF synthesis
       always preserves dependencies and BCNF decomposition may not. `[PROVE]` `[RESEARCH]`
1.3.12 The practical rule the bible must land: **normalize to 3NF/BCNF by default, denormalize only
       against a measured read path, and only where you can name the mechanism that keeps the copy
       correct** (trigger, materialized view, application write-both, CDC).
1.3.13 Denormalization catalogue with the correctness mechanism for each: the pre-aggregated counter,
       the materialized view, the duplicated lookup column, the JSONB blob, the array column, the
       wide read model.
1.3.14 **The QuizStakes anti-denormalization decision, stated as the canonical example**: `Stakeable`
       and `Withdrawable` are *derived, never stored* (§11.1). "A stored total is a second source of
       truth that can disagree with the entries. Every disagreement is a reconciliation break."
       Reading four positions is cheap; being wrong about money is not. `[SOURCE]` `[PROVE]`
1.3.15 The counter-case in the same domain, so the reader sees the trade honestly: `BalanceView`
       exists precisely because reading four positions on every screen at 380k monthly actives is
       *not* free — but it is non-authoritative, which is the price of the copy. `[X-REF 15]`
1.3.16 **Trap: "normalization is about eliminating redundancy."** It is about eliminating *anomalies*
       caused by redundancy that FDs make removable. Some redundancy (a foreign key value) is
       unavoidable and harmless. `[TRAP]`
1.3.17 **Trap: "3NF means slow, so we denormalize."** Joins on indexed keys are cheap; the expensive
       thing is usually row count and I/O volume, and denormalization increases both write volume and
       correctness risk. Name the measurement you would take before deciding. `[TRAP]`
1.3.18 Modelling patterns that are not normal forms but get confused with them: surrogate vs natural
       keys, star/snowflake schemas for analytics, slowly changing dimensions (type 1/2/3), EAV and
       why it is almost always wrong, single-table inheritance vs class-table vs concrete-table
       (and how they map onto `08-spring-data-jpa.md`'s inheritance strategies). `[X-REF 08]`
1.3.19 **Trap: the EAV table.** `restriction_attribute(restriction_id, key, value)` looks flexible and
       destroys type safety, constraints, indexing and the planner's statistics simultaneously. The
       QuizStakes alternative is a typed `restriction` row with a composite `(type, source)` identity
       (§9.3). `[TRAP]`
1.3.20 Temporal modelling: valid-time vs transaction-time, and PostgreSQL 18's
       `PRIMARY KEY (room_id, period WITHOUT OVERLAPS)` plus `FOREIGN KEY (..., PERIOD ...)` as the
       first standard-SQL temporal support in the engine. In QuizStakes this is exactly the shape of
       `restriction(client_id, type, source, applied_at, expires_at)` overlap prevention.
       `[RESEARCH]` `[NUM]`
1.3.21 Append-only modelling as a first-class choice: `ledger_entry` and `application_history` are
       insert-only by invariant (§11.7 #7 — "a correction is a new compensating movement, never an
       update or delete"), which removes the update anomaly by construction rather than by
       decomposition. `[SOURCE]`

*(21 leaves)*

## §1.4 Keys, identity and identifier generation

1.4.1 The five key terms disambiguated: superkey, candidate key, primary key, alternate key, foreign
      key. Plus "natural key" and "surrogate key", which are design labels, not model concepts.
1.4.2 `PRIMARY KEY` = `UNIQUE` + `NOT NULL` + at most one per table + the default target of a
      `REFERENCES` clause. In InnoDB it additionally decides physical row order; in PostgreSQL it
      does not. `[MYSQL]` `[TRAP]`
1.4.3 Surrogate-key options with the cost of each: `bigint` identity/sequence, `uuid` v4, `uuid` v7,
      ULID, Snowflake-style composite ids, and natural composite keys. One-line trade each.
1.4.4 `SERIAL` vs `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY`: `SERIAL` is a macro that creates a
      sequence with an ownership dependency and leaves the column defaultable and grantable
      separately; identity columns are the standard-SQL form and the PostgreSQL wiki's *Don't Do
      This* explicitly says don't use `SERIAL`. `[SOURCE]` `[VERSION-TRAP]` `[RESEARCH]`
1.4.5 Sequences are **non-transactional by design**: `nextval` is never rolled back, so gaps are
      normal and "the ids must be contiguous" is not a requirement a sequence can satisfy.
      `[TRAP]` `[PROVE]`
1.4.6 Sequence mechanics and knobs: `CACHE n` (per-session block, and the gap it creates),
      `INCREMENT BY`, `CYCLE`, `setval`, `currval`, `pg_get_serial_sequence`, and how `CACHE`
      interacts with Hibernate's `allocationSize = 50` pooled optimizer. `[GUC]` `[X-REF 08]`
1.4.7 `AUTO_INCREMENT` in InnoDB and the three `innodb_autoinc_lock_mode` values —
      `0` traditional (table-level AUTO-INC lock for the whole statement), `1` consecutive (default
      in 8.0+: bulk inserts take the lock, simple inserts use a mutex), `2` interleaved. The
      replication consequence of mode 2 with statement-based binlog. `[MYSQL]` `[NUM]`
      `[RESEARCH]`
1.4.8 UUIDv4's cost, quantified against QuizStakes: 16 bytes vs 8 for `bigint`, and random insert
      position in every B-tree — at 19.8M `ledger_entry` inserts/day that is page splits and cache
      misses across the whole index rather than at the right-hand edge. `[NUM]` `[PROVE]`
1.4.9 **`uuidv7()` is native in PostgreSQL 18** (alongside an explicit `uuidv4()`): a 48-bit
      Unix-millisecond prefix makes the value time-ordered, restoring right-edge insert locality
      while keeping the client-generatable, globally-unique property. This is the correct answer for
      `movement.id` in a system where the id must be known before the write. `[RESEARCH]` `[NUM]`
      `[VERSION-TRAP]`
1.4.10 Client-generated vs server-generated identity, and why QuizStakes needs the former:
       `IdempotencyKey` is caller-supplied (Appendix C.1), and the ledger must be able to detect a
       replay *before* it writes. `[SOURCE]`
1.4.11 Composite/natural keys done right: `position(account_id, type)` is a genuine natural key, and
       `restriction(client_id, type, source)` is the composite identity §9.3 insists on — "type alone
       is not identity". Getting this wrong means activation silently clears an operator's block.
       `[SOURCE]` `[TRAP]`
1.4.12 Foreign keys: `REFERENCES`, the referential actions `ON DELETE/UPDATE {NO ACTION | RESTRICT |
       CASCADE | SET NULL | SET DEFAULT}`, `MATCH FULL | PARTIAL | SIMPLE`, and
       `DEFERRABLE INITIALLY DEFERRED`. `NO ACTION` vs `RESTRICT` differ *only* in deferrability.
       `[SQL]` `[TRAP]`
1.4.13 The FK enforcement mechanism: PostgreSQL implements it as system-level `AFTER` triggers with
       `RI_FKey_check_ins`-family functions, taking a `FOR KEY SHARE` lock on the parent row — which
       is why an unindexed child column makes parent deletes scan and why FK checks show up as lock
       waits. PG 19 claims ~2× faster inserts with FK checks present. `[SOURCE]` `[RESEARCH]`
1.4.14 **Trap: PostgreSQL does not automatically index the referencing column of a foreign key**
       (it indexes the referenced side, which must be unique). InnoDB *does* auto-create an index on
       the child column. Unindexed child columns are the classic cause of a slow `DELETE` on a parent.
       `[TRAP]` `[MYSQL]`
1.4.15 **The QuizStakes rule that removes most FK questions**: §5.1 rule 4 and §7.2 — no cross-schema
       joins, ever, so `cardpayments.transactions.account_id` has *no* database-enforced reference to
       `accountmaintenance.account`. §15.3 names the consequence: "referential integrity across
       services — nothing enforces it." The bible must state what you do instead (validate at the
       boundary, reconcile, and accept orphan detection as an operational job). `[SOURCE]`
       `[X-REF 22]`
1.4.16 Where identity generation is owned: the ORM-side story (`GenerationType`, optimizers,
       `@MapsId`, batching interaction) is in `08-spring-data-jpa.md`; this guide owns the sequence,
       identity column and `AUTO_INCREMENT` mechanics. `[X-REF 08]`

*(16 leaves)*

## §1.5 Types, domains and the ones that cause outages

1.5.1 The type-category map, with why each category has its own gotcha: exact numeric, approximate
      numeric, character, binary, boolean, temporal, interval, enumerated, composite/row, array,
      range/multirange, JSON, UUID, network, geometric, full-text (`tsvector`), and bit string.
1.5.2 **Money must be `numeric`/`DECIMAL`, never `float`/`double`/`real`, and never PostgreSQL's
      `money` type.** The `money` type carries a locale-dependent, `lc_monetary`-driven fixed scale
      and cannot represent all currencies; `float` cannot represent 0.1. QuizStakes'
      `Money(amount: Decimal, currency: Currency)` says "**Never floating point**" (Appendix C.1).
      `[SOURCE]` `[TRAP]` `[X-REF 03]`
1.5.3 `numeric(p, s)` semantics: exact decimal arithmetic, variable storage (~2 bytes per 4 digits
      plus 3–8 bytes overhead), and the rounding rules of `ROUND`/`TRUNC`/division. Prove why the
      QuizStakes bonus split of a 3.33 stake must round the bonus leg **down** so the two legs sum to
      exactly the stake (§11.4 rounding rule, invariant #6). `[NUM]` `[PROVE]`
1.5.4 Integer widths and their real limits: `smallint` ±32,767, `integer` ±2,147,483,647,
      `bigint` ±9.22×10¹⁸. At 19.8M `ledger_entry` rows/day an `integer` surrogate key exhausts in
      **~108 days**; show the arithmetic. This is the outage that a `bigint` default prevents.
      `[NUM]` `[PROVE]`
1.5.5 `char(n)` vs `varchar(n)` vs `text` in PostgreSQL: identical storage, `char(n)` blank-pads
      (and is slower), `varchar(n)` differs from `text` only by a length check that requires a table
      rewrite to relax before PG 9.2 and a catalog-only change after. The wiki's guidance: use `text`,
      add a `CHECK`. `[SOURCE]` `[VERSION-TRAP]`
1.5.6 `varchar(n)` in MySQL is a different animal: `n` is characters, the row-format and index-prefix
      limits (767/3072 bytes) bite, and `utf8mb3` vs `utf8mb4` changes the byte cost per character.
      `[MYSQL]` `[NUM]`
1.5.7 **`timestamptz`, always.** `timestamp without time zone` stores no zone and silently
      reinterprets; `timestamptz` stores a UTC instant and renders in the session `TimeZone`. The
      wiki lists four separate "don't" entries here: don't use `timestamp`, don't use `timestamp` to
      store UTC, don't use `timetz`, don't use `CURRENT_TIME`. `[SOURCE]` `[TRAP]`
1.5.8 `date`, `time`, `interval`, and the `AT TIME ZONE` operator's two directions (applied to
      `timestamp` it *localises*, applied to `timestamptz` it *renders*) — the most commonly inverted
      operator in SQL. `[PROVE]` `[TRAP]`
1.5.9 **Don't use `BETWEEN` on timestamps**: `BETWEEN a AND b` is closed on both ends, so
      `BETWEEN '2026-06-01' AND '2026-06-30'` loses 23:59:59.999999 of June 30. Use
      `>= '2026-06-01' AND < '2026-07-01'`. The wiki says this explicitly. `[SOURCE]` `[TRAP]`
1.5.10 `timestamp(0)`/`timestamptz(0)` rounds rather than truncates, so a value can round *up* into
       the next second/day; use `date_trunc('second', x)`. `[SOURCE]` `[TRAP]`
1.5.11 The Java mapping table the write pass must give, because half of the temporal bugs are here:
       `timestamptz` ↔ `OffsetDateTime`/`Instant`, `timestamp` ↔ `LocalDateTime`, `date` ↔
       `LocalDate`, `time` ↔ `LocalTime`, `interval` ↔ `Duration`/`Period` (driver-specific),
       `numeric` ↔ `BigDecimal`, `uuid` ↔ `java.util.UUID`, `jsonb` ↔ `String`/`PGobject`.
       `[JDBC]` `[X-REF 03]`
1.5.12 `boolean` and the three-valued reality: `TRUE`/`FALSE`/`NULL`, the accepted literals, and
       MySQL's `BOOLEAN` being `tinyint(1)` so `= 2` is legal. `[MYSQL]` `[TRAP]`
1.5.13 `enum` types: cheap and readable, but `ALTER TYPE ... ADD VALUE` cannot run inside a
       transaction block before PG 12 and values cannot be removed. The alternative is a lookup table
       with an FK, or a `text` column with a `CHECK`. For QuizStakes' 12 state machines and
       `AO-`/`AA-`/`DEP-`/`BDP-` code sets, state which you would choose and why. `[VERSION-TRAP]`
1.5.14 Arrays: `integer[]`, `text[]`, subscripting from 1, `ANY`/`ALL`, `unnest`, `array_agg`, and PG
       18's new `array_sort()`/`array_reverse()`. The 1NF trade-off and when an array beats a child
       table (small, always-read-together, never independently queried). `[RESEARCH]`
1.5.15 Ranges and multiranges: `int4range`, `tsrange`, `daterange`, the `&&` overlap operator, and
       `EXCLUDE USING gist (client_id WITH =, validity WITH &&)` as the *declarative* way to stop two
       overlapping `restriction` rows for the same `(type, source)`. This is a constraint doing work
       that application code usually gets wrong. `[SQL]` `[PROVE]`
1.5.16 `json` vs `jsonb`: `json` keeps the text verbatim (order, whitespace, duplicate keys), `jsonb`
       parses to a binary tree (no duplicate keys, no order, indexable with GIN). Use `jsonb` unless
       you need byte-exact round-tripping. `[TRAP]`
1.5.17 `uuid` as a native 16-byte type versus `char(36)`: 16 bytes vs 36, plus a real comparison
       operator. In MySQL the equivalent is `BINARY(16)` with `UUID_TO_BIN(uuid, 1)` for the
       swap-flag byte reordering that restores time ordering. `[MYSQL]` `[NUM]`
1.5.18 Domains (`CREATE DOMAIN money_amount AS numeric(19,4) CHECK (VALUE >= 0)`) and composite
       types: how to give `Money` and `IdempotencyKey` type identity in the database rather than only
       in Java. `[SQL]`
1.5.19 `CREATE CAST`, implicit vs assignment vs explicit casts, and why implicit casts are the reason
       `WHERE varchar_col = 123` can silently disable an index (§2.7). `[PROVE]`
1.5.20 Collations: `LC_COLLATE`, ICU vs libc providers, deterministic vs nondeterministic collations,
       and the fact that **an index is only usable for a comparison in the collation it was built
       with** — changing `COLLATE` invalidates index usability. PG 18 changed full-text search to use
       the cluster default provider instead of always libc and recommends reindexing FTS and
       `pg_trgm` indexes after upgrade. `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]`
1.5.21 Character sets: `SQL_ASCII` is a lie (it stores bytes and validates nothing) and the wiki says
       don't; use UTF-8. In MySQL, `utf8` means `utf8mb3` historically and `utf8mb4` is the one you
       want, with `utf8mb4_0900_ai_ci` the 8.0+ default collation. `[SOURCE]` `[MYSQL]`
1.5.22 Type resolution and overload rules: how PostgreSQL picks a function/operator when arguments
       are of "unknown" type (a bare literal), and why `WHERE created_at > '2026-01-01'` works but
       `WHERE created_at > $1` with a string parameter may not. `[JDBC]`
1.5.23 Generated columns: `GENERATED ALWAYS AS (expr) STORED` vs — **new default in PG 18** —
       *virtual* (computed on read). Virtual generated columns cannot be indexed; stored ones can. Use
       one for the derived-total temptation only when you accept it is not a second truth.
       `[RESEARCH]` `[VERSION-TRAP]` `[NUM]`

*(23 leaves)*

## §1.6 DDL — the definition surface

1.6.1 The DDL verb inventory: `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COMMENT`, `RENAME`,
      `CREATE ... IF NOT EXISTS`, `CREATE OR REPLACE` (and which objects support it).
1.6.2 `CREATE TABLE` clause by clause: column definitions, column and table constraints,
      `LIKE parent (INCLUDING ...)`, `INHERITS` (and why the wiki says don't), `PARTITION BY`,
      `TABLESPACE`, `WITH (storage parameters)`, `UNLOGGED`, temporary tables and `ON COMMIT`
      behaviour. `[SQL]` `[SOURCE]`
1.6.3 Storage parameters worth knowing by name and default: `fillfactor` (**100 for tables, 90 for
      B-tree indexes**), `autovacuum_vacuum_scale_factor`, `autovacuum_enabled`,
      `toast_tuple_target`, `parallel_workers`, `log_autovacuum_min_duration`. `[GUC]` `[NUM]`
1.6.4 `UNLOGGED` tables: no WAL, therefore fast, therefore truncated on crash and unavailable on
      replicas. The only legitimate QuizStakes use is a bank-file staging table during ingestion of
      the 500k-record month-end file, and even that must be restartable. `[NUM]`
1.6.5 Temporary tables: session-scoped, in `pg_temp_nnn`, never autovacuumed by the autovacuum
      daemon, and a per-connection catalog-bloat source when a pooled connection creates one per
      request. `[TRAP]`
1.6.6 `ALTER TABLE` sub-command inventory grouped by what it costs: catalog-only, needs a scan, needs
      a rewrite. This is the table that makes §2.25 (online DDL) mechanical rather than folklore.
      `[NUM]`
1.6.7 `TRUNCATE` vs `DELETE`: `TRUNCATE` takes `ACCESS EXCLUSIVE`, is transactional in PostgreSQL
      (and *not* in MySQL, where it is an implicit-commit DDL), resets the identity with
      `RESTART IDENTITY`, does not fire row triggers, and cannot be used on a table referenced by an
      FK without `CASCADE`. `[MYSQL]` `[TRAP]`
1.6.8 Schemas and `search_path`: `CREATE SCHEMA`, qualified names, the default `"$user", public`
      search path, and PG 15's change of `public` schema privileges (no longer `CREATE` for all).
      QuizStakes is schema-per-service (§7.2) so every statement in the bible should be
      schema-qualified. `[VERSION-TRAP]` `[SOURCE]`
1.6.9 Databases vs schemas vs catalogs, and the cross-database join rule: PostgreSQL cannot join
      across databases in one query (you need FDW/dblink); MySQL's "database" *is* a schema, so it
      can. This single difference explains most confusion when a MySQL developer reads PostgreSQL
      documentation. `[MYSQL]` `[TRAP]`
1.6.10 `CREATE VIEW`, `CREATE OR REPLACE VIEW`'s column-compatibility restriction,
       `WITH CHECK OPTION`, `WITH (security_barrier)`, `security_invoker` (PG 15+), auto-updatable
       views and `INSTEAD OF` triggers. `[VERSION-TRAP]`
1.6.11 `CREATE MATERIALIZED VIEW`, `REFRESH MATERIALIZED VIEW [CONCURRENTLY]` and the unique-index
       precondition for `CONCURRENTLY`. The QuizStakes candidate is a per-client daily deposit
       aggregate for limit checks — and the reason it is *not* used for the limit decision is §14.2
       invariant 12. `[SQL]` `[X-REF 15]`
1.6.12 Sequence, index, trigger, function, procedure, type, extension, publication, subscription,
       foreign table, statistics object: the full `CREATE` object list, so nothing in later sections
       arrives unnamed.
1.6.13 `CREATE EXTENSION` and the extensions this guide actually uses: `pg_stat_statements`,
       `pg_trgm`, `btree_gin`, `btree_gist`, `pgcrypto`, `pg_repack`, `postgres_fdw`, `pgstattuple`,
       `pg_buffercache`, `auto_explain`, `hypopg`, `pg_partman`, `amcheck`. One line on what each
       gives you. `[RESEARCH]`
1.6.14 DDL transactionality: PostgreSQL DDL is transactional (you can `BEGIN; ALTER; ROLLBACK;`),
       MySQL 8.0 DDL is atomic per-statement but each statement implicitly commits. This is why a
       failed Flyway migration leaves MySQL half-migrated and PostgreSQL clean, and why
       `CREATE INDEX CONCURRENTLY` is the one PostgreSQL statement that cannot run in a transaction.
       `[MYSQL]` `[PROVE]` `[TRAP]`
1.6.15 `COMMENT ON` as documentation that ships with the schema, and `\d+`/`information_schema` as
       where it surfaces.
1.6.16 Object naming: the 63-byte `NAMEDATALEN - 1` identifier limit, quoted vs unquoted identifiers
       (PostgreSQL folds unquoted to lower case; the standard says upper), and the wiki's "don't use
       upper case table or column names" — because `"Camel"` then requires quoting forever.
       `[SOURCE]` `[NUM]` `[TRAP]`

*(16 leaves)*

## §1.7 Constraints as executable business rules

1.7.1 The five constraint kinds and what each guarantees: `NOT NULL`, `UNIQUE`, `PRIMARY KEY`,
      `FOREIGN KEY`, `CHECK` — plus `EXCLUDE` (PostgreSQL-only) as the sixth that nobody mentions.
1.7.2 The claim the whole section serves: **a `UNIQUE` constraint is the only race-free way to
      prevent duplicates.** `SELECT`-then-`INSERT` in application code is a race under every
      isolation level; the index is the arbiter. `[PROVE]`
1.7.3 The idempotency implementation that follows: a `UNIQUE` index on
      `fundsledger.movement(idempotency_key)`, insert first, and treat SQLSTATE **23505**
      (`unique_violation`) as success. QuizStakes invariant #11 — "the same idempotency key never
      produces two effects" — and Appendix B.2's note that the cache is the fast path while "the
      unique constraint is the correctness mechanism". `[SOURCE]` `[DIAG]` `[X-REF 12]`
1.7.4 `UNIQUE` allows multiple NULLs because NULLs are not equal to each other; PG 15 added
      `UNIQUE NULLS NOT DISTINCT` for when you wanted the other behaviour. `[VERSION-TRAP]`
      `[TRAP]`
1.7.5 `CHECK` constraints: row-level only, must be immutable (no subqueries, no `now()`), and
      `NOT VALID` + `VALIDATE CONSTRAINT` as the two-step way to add one to a large table without a
      long `ACCESS EXCLUSIVE` hold. `[SQL]` `[NUM]`
1.7.6 The QuizStakes constraint set, written out, because it is the best answer to "what would you
      put in the schema": `CHECK (amount > 0)` on `ledger_entry`,
      `CHECK (direction IN ('DEBIT','CREDIT'))`, `CHECK (balance >= 0)` on client positions
      (invariants #2–#4), `CHECK (signed_off_by <> authorised_by)` on `payment_run` (§13.2's
      segregation of duties as a field-level constraint), and
      `CHECK (lifecycle <> 'CLOSED' OR balance = 0)` for invariant #10. `[SQL]` `[SOURCE]`
1.7.7 What a `CHECK` cannot do, and therefore what needs a trigger or a transaction: cross-row
      invariants. "Every movement's entries sum to zero" (invariant #1) is not expressible as a
      `CHECK`; it needs a constraint trigger, a deferred check, or the write path's own discipline.
      `[PROVE]` `[TRAP]`
1.7.8 `DEFERRABLE INITIALLY DEFERRED` and `SET CONSTRAINTS ALL DEFERRED`: the mechanism that lets a
      circular insert or an intra-transaction imbalance exist transiently. The sum-to-zero check is
      the textbook use. `[SQL]`
1.7.9 Constraint triggers (`CREATE CONSTRAINT TRIGGER ... AFTER ... DEFERRABLE`) as the enforcement
      route for invariant #1, and the honest cost: per-statement overhead on the hottest write path in
      the system (13,600 entries/sec peak). State the trade rather than recommending it blindly.
      `[NUM]` `[PROVE]`
1.7.10 `EXCLUDE USING gist` restated as a constraint: non-overlapping `restriction` validity periods,
       non-overlapping `payment_run` windows. This is the constraint most engineers do not know
       exists. `[SQL]`
1.7.11 `NOT ENFORCED` constraints — **new in PG 18** — declare a constraint the planner may know about
       but the engine does not check. Useful for documenting a cross-service reference you cannot
       enforce (§1.4.15); dangerous if anyone believes it. `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]`
1.7.12 `NOT NULL` constraints became named catalog objects in `pg_constraint` in PG 18, supporting
       `NOT VALID` and `[NO] INHERIT` — which finally makes "add a `NOT NULL` to a huge table without
       a full validating scan" a two-step operation. `[RESEARCH]` `[VERSION-TRAP]` `[NUM]`
1.7.13 The SQLSTATE map every Java service must handle, by class: **23000** integrity constraint
       violation, **23502** not-null violation, **23503** foreign-key violation, **23505** unique
       violation, **23514** check violation, **40001** serialization failure, **40P01** deadlock
       detected, **55P03** lock not available, **57014** query canceled, **53300** too many
       connections, **08003/08006** connection failure. `[DIAG]` `[NUM]` `[JDBC]`
1.7.14 How those map into Java: `SQLIntegrityConstraintViolationException`,
       `SQLTransientConnectionException`, `SQLTimeoutException`, and Spring's translation to
       `DataIntegrityViolationException` / `DuplicateKeyException` /
       `CannotAcquireLockException` / `ConcurrencyFailureException` via
       `SQLExceptionSubclassTranslator` and `SQLErrorCodeSQLExceptionTranslator`. `[JDBC]`
       `[X-REF 08]`
1.7.15 **Trap: catching the duplicate-key error only works if the transaction can continue.** In
       PostgreSQL any error aborts the transaction — subsequent statements fail with
       "current transaction is aborted"; you need a `SAVEPOINT` before the insert or
       `ON CONFLICT DO NOTHING`. In MySQL the statement fails but the transaction survives. This
       difference silently breaks ported code. `[TRAP]` `[MYSQL]` `[PROVE]` `[DIAG]`
1.7.16 Constraint naming discipline: default names (`tablename_colname_key`,
       `tablename_colname_fkey`, `tablename_pkey`) versus explicit names, and why the error message
       your service logs is only useful if the constraint has a name you chose. `[DIAG]`
1.7.17 Where to enforce: database, application, or both. The rule the bible must state — invariants
       that money depends on go in the database *as well as* the application, because the database is
       the only participant that sees every writer. `[PROVE]`
1.7.18 The `information_schema` and `pg_constraint` introspection queries that answer "what
       constraints does this table actually have" and "which are `NOT VALID`". `[SQL]`

*(18 leaves)*

## §1.8 DML — writing rows

1.8.1 `INSERT` forms: single row, multi-row `VALUES`, `INSERT ... SELECT`, `INSERT ... DEFAULT
      VALUES`, `OVERRIDING SYSTEM VALUE` for identity columns. `[SQL]`
1.8.2 `RETURNING` as PostgreSQL's answer to "I need the generated id and the computed columns without
      a second round trip", and PG 18's `OLD`/`NEW` aliases in `RETURNING` for `INSERT`, `UPDATE`,
      `DELETE` and `MERGE` — the audit-row pattern in one statement. `[RESEARCH]`
      `[VERSION-TRAP]` `[SQL]`
1.8.3 `UPDATE` forms: `SET` list, row-value `SET (a,b) = (x,y)`, `UPDATE ... FROM` (PostgreSQL) vs
      `UPDATE t1 JOIN t2` (MySQL), and the fact that `UPDATE` sees a single snapshot so it cannot
      read its own changes. `[MYSQL]` `[SQL]`
1.8.4 `DELETE` forms: `DELETE ... USING` (PostgreSQL) vs `DELETE t1 FROM t1 JOIN t2` (MySQL), and
      `DELETE ... WHERE ctid IN (...)` / `LIMIT`-less-ness in PostgreSQL versus MySQL's
      `DELETE ... LIMIT`. `[MYSQL]`
1.8.5 The **chunked delete/update** pattern that the QuizStakes 90-day hot window requires: a single
      `DELETE` over a month of `ledger_entry` rows (~600M) holds locks, bloats, and generates WAL
      proportional to the table. Show the `DELETE ... WHERE id IN (SELECT id ... LIMIT 10000)` loop
      with a commit per batch, and then show why `DETACH PARTITION` is strictly better (§2.24).
      `[NUM]` `[PROVE]` `[SQL]`
1.8.6 Upsert: PostgreSQL `INSERT ... ON CONFLICT (cols) DO UPDATE SET ... WHERE ...` with the
      `EXCLUDED` pseudo-table, `ON CONFLICT DO NOTHING`, and `ON CONFLICT ON CONSTRAINT name`.
      `[SQL]`
1.8.7 `ON CONFLICT` requires a *unique index* to arbitrate, cannot use a non-unique index, and takes
      a row lock on conflict — so a high-conflict upsert serialises. Prove the difference between
      `DO NOTHING` (no lock taken on the conflicting row in the general case) and `DO UPDATE`.
      `[PROVE]` `[TRAP]`
1.8.8 MySQL's three near-equivalents and how they differ: `INSERT ... ON DUPLICATE KEY UPDATE`
      (checks every unique key, not one you nominate), `INSERT IGNORE` (swallows *all* errors,
      including data truncation — a data-corruption footgun), and `REPLACE INTO` (delete + insert, so
      it fires delete triggers and cascades). `[MYSQL]` `[TRAP]`
1.8.9 Standard `MERGE` (PG 15+): `MERGE INTO ... USING ... ON ... WHEN MATCHED THEN UPDATE / DELETE /
      DO NOTHING WHEN NOT MATCHED THEN INSERT`, plus `WHEN NOT MATCHED BY SOURCE` (PG 17).
      What `MERGE` does *not* do that `ON CONFLICT` does: it is not atomic against a concurrent
      inserter, so it can raise a unique violation under concurrency. `[VERSION-TRAP]` `[PROVE]`
      `[TRAP]`
1.8.10 PG 19's `ON CONFLICT DO SELECT` — returns the conflicting row so an idempotent write can read
       the existing effect without a second query. This is exactly the QuizStakes replay path.
       `[RESEARCH]` `[VERSION-TRAP]`
1.8.11 Bulk load: `COPY ... FROM STDIN` (and its `FORMAT csv`, `HEADER`, `FREEZE`, `ON_ERROR`,
       PG 18's `REJECT_LIMIT`), `\copy` in psql, `LOAD DATA INFILE` in MySQL, and the order-of-
       magnitude difference against row-by-row `INSERT`. The bank statement feed (40k records/day,
       500k at month-end) is the example. `[RESEARCH]` `[NUM]` `[SQL]`
1.8.12 `COPY` from Java: the pgJDBC `CopyManager` API (`copyIn(String, Reader)`), what it costs, and
       when it beats `addBatch`/`executeBatch`. `[JDBC]` `[BUILD]`
1.8.13 The write-amplification arithmetic the bible must show for one QuizStakes card deposit
       (§15.3): a payment record, a rail record, four-plus ledger entries, a history record, a bonus
       record, a notification — plus every index on each of those tables, plus WAL for all of it.
       "One user action" is a double-digit number of physical writes. `[NUM]` `[PROVE]`
1.8.14 Triggers: `BEFORE`/`AFTER`/`INSTEAD OF`, `FOR EACH ROW` vs `FOR EACH STATEMENT`,
       `WHEN` conditions, transition tables (`REFERENCING NEW TABLE AS`), execution order (alphabetical
       by name — a genuine surprise), and the honest position: triggers are the right tool for audit
       and for cross-row invariants, and the wrong tool for business logic you will need to debug.
       `[SQL]` `[TRAP]`
1.8.15 `RULE`s exist and the PostgreSQL wiki says don't use them — use a trigger. Name them once so
       you recognise them in old code. `[SOURCE]`
1.8.16 Stored procedures and functions: `CREATE FUNCTION` (cannot control transactions) vs
       `CREATE PROCEDURE` (PG 11+, can `COMMIT`), `LANGUAGE plpgsql|sql|c`, volatility categories
       (`IMMUTABLE`/`STABLE`/`VOLATILE`) and why the category changes both planning and index
       eligibility, `PARALLEL SAFE`, and `SECURITY DEFINER` as a privilege-escalation surface.
       `[VERSION-TRAP]` `[NUM]` `[X-REF 13]`
1.8.17 The mature position on business logic in the database, stated with both sides: it is the only
       place that sees every writer (so invariants belong there), and it is the hardest place to
       version, test and review (so orchestration does not).
1.8.18 `SELECT ... INTO`, `CREATE TABLE AS SELECT` and `INSERT ... SELECT` for the backfill step of an
       expand/contract migration, with the WAL and lock consequences of each. `[X-REF 08]`

*(18 leaves)*

## §1.9 `SELECT` and the logical order of operations

1.9.1 The logical processing order, memorised, because it explains nearly every "column does not
      exist" error: `FROM` → `JOIN`/`ON` → `WHERE` → `GROUP BY` → `HAVING` → `WINDOW` →
      `SELECT` (aliases created here) → `DISTINCT` → `UNION`/`INTERSECT`/`EXCEPT` → `ORDER BY` →
      `LIMIT`/`OFFSET`. `[FLOW]` `[PROVE]`
1.9.2 Logical order is not physical order. The optimizer will reorder anything it can prove
      equivalent, so "the `WHERE` runs before the `JOIN`" is a statement about *semantics*, not about
      the plan. `[TRAP]` `[PROVE]`
1.9.3 Where an alias defined in `SELECT` may be used: `ORDER BY` yes, `GROUP BY` yes in PostgreSQL
      (a documented extension) and MySQL, `HAVING` no, `WHERE` no. The write pass must prove each
      from §1.9.1 rather than asserting the list. `[PROVE]` `[TRAP]` `[MYSQL]`
1.9.4 `SELECT *` and why it is a production problem rather than a style issue: it breaks index-only
      scans, transports TOASTed columns you did not want, and changes result shape when someone adds
      a column. The Winand *Myth Directory* counterpoint — `SELECT *` is not *inherently* slow — must
      also be stated, so the reader argues correctly. `[SOURCE]` `[TRAP]`
1.9.5 Table expressions in `FROM`: base table, view, subquery (derived table, which must be aliased),
      `LATERAL` subquery, `VALUES` list, function call (`unnest`, `generate_series`,
      `jsonb_to_recordset`), `WITH` reference, `ONLY parent`, `TABLESAMPLE`.
1.9.6 Column and table aliasing rules, `AS` optionality, and the fact that a derived table without an
      alias is a syntax error in PostgreSQL and legal in MySQL. `[MYSQL]`
1.9.7 `DISTINCT` (whole row) vs `DISTINCT ON (expr)` (PostgreSQL: first row per group per
      `ORDER BY`) vs `GROUP BY`. `DISTINCT ON` is the fastest "latest row per client" in PostgreSQL
      and has no standard equivalent. `[SQL]` `[PROVE]`
1.9.8 `ORDER BY` details: expression or output-column position, `ASC`/`DESC`, `NULLS FIRST|LAST`
      (PostgreSQL defaults to `NULLS LAST` for `ASC` and `NULLS FIRST` for `DESC`; MySQL sorts NULLs
      first for `ASC`), `COLLATE`, `USING operator`, and ordering stability. `[MYSQL]` `[NUM]`
      `[TRAP]`
1.9.9 **A query without `ORDER BY` has no order.** Not "usually insertion order", not "the primary
      key" — none. The plan can change and silently reorder your API responses; the symptom is a page
      of results that repeats a row. `[TRAP]` `[PROVE]`
1.9.10 `LIMIT`/`OFFSET` vs standard `FETCH FIRST n ROWS ONLY` / `OFFSET n ROWS`, `WITH TIES`, and
       MySQL's `LIMIT offset, count` argument order. `[MYSQL]`
1.9.11 The full `FROM`-less `SELECT`, `SELECT 1`, and why `SELECT 1 FROM ... WHERE EXISTS` is not
       faster than `SELECT *` inside `EXISTS` (the planner discards the target list either way).
       `[TRAP]` `[PROVE]`
1.9.12 Row constructors and row-value comparison: `(created_at, id) < (?, ?)` is a single
       lexicographic comparison, not three, and it is the key to keyset pagination (§2.13). Show
       the expansion the planner performs. `[SQL]` `[PROVE]`
1.9.13 `TABLESAMPLE SYSTEM (n)` / `BERNOULLI (n)` and `REPEATABLE (seed)` — the right way to sample
       a 7.2B-row table for a spot check, and why `ORDER BY random() LIMIT 10` is not.
       `[SQL]` `[NUM]`
1.9.14 `GROUP BY ALL` (PG 19) as the coming shorthand for "group by every non-aggregate output
       column". `[RESEARCH]` `[VERSION-TRAP]`

*(14 leaves)*

## §1.10 Joins

1.10.1 The join type table with exact semantics: `INNER`, `LEFT OUTER`, `RIGHT OUTER`, `FULL OUTER`,
       `CROSS`, and the self join. Include what each returns for unmatched rows on each side.
1.10.2 `ON` vs `USING` vs `NATURAL JOIN`: `USING` merges the join columns into one output column;
       `NATURAL` infers the join columns by name and is a latent bug the moment anyone adds a column.
       Never ship `NATURAL JOIN`. `[TRAP]`
1.10.3 **The LEFT JOIN killed by WHERE** — the single most-tested join trap. A predicate on the outer
       table in `WHERE` evaluates `NULL >= '2026-01-01'` → UNKNOWN → row dropped → the join is
       silently an `INNER JOIN`. Filters on the outer side belong in `ON`. Show both the broken and
       the fixed query against `bankwithdrawal.transactions`. `[TRAP]` `[PROVE]` `[SQL]`
1.10.4 The one legitimate `WHERE` on the outer side: `WHERE t.id IS NULL` — the anti-join idiom for
       "reservations with no settlement message" (§12.6's `ORPHANED` detection). `[SQL]`
1.10.5 `ON` clause placement in a chain of three or more joins, and why moving a predicate between
       `ON` and `WHERE` changes results only for outer joins and never for inner ones. `[PROVE]`
1.10.6 Semi-join and anti-join as first-class concepts with their three spellings each:
       `IN (subquery)` / `EXISTS` / `INNER JOIN + DISTINCT` for semi; `NOT IN` / `NOT EXISTS` /
       `LEFT JOIN ... IS NULL` for anti. State which the planner recognises as a semi/anti-join node.
       `[PLAN]` `[PROVE]`
1.10.7 The three anti-join spellings are **not** equivalent: `NOT IN` breaks on NULL (§1.12.4),
       `NOT EXISTS` is NULL-safe, `LEFT JOIN ... IS NULL` is NULL-safe but can lose rows if the join
       is not on a unique key. Show all three against the same data with a NULL present. `[TRAP]`
       `[PROVE]`
1.10.8 Join *elimination*: the planner can drop a join entirely when the joined table is
       unreferenced, the FK guarantees a match, or the join is a provably-unique self join —
       PG 18's `enable_self_join_elimination` (default `on`) is exactly this. Why this makes the
       "views with unnecessary joins" objection weaker than it looks. `[GUC]` `[RESEARCH]`
1.10.9 Join order and associativity: inner joins are freely reorderable, outer joins are not (in
       general), and the planner's search space is therefore much smaller when outer joins are
       present. `[PROVE]`
1.10.10 `LATERAL` joins: a subquery in `FROM` that may reference earlier `FROM` items, i.e. a
        correlated subquery producing a *set*. The canonical use is top-N per group —
        "last 3 movements for each of these 50 clients" — and it is often faster than a window
        function because the inner query can stop early. `[SQL]` `[PROVE]`
1.10.11 `CROSS JOIN LATERAL` vs `LEFT JOIN LATERAL ... ON true`, and why the latter is required when
        the inner query may return zero rows. `[TRAP]`
1.10.12 `CROSS JOIN` legitimate uses: `generate_series` calendar spines for gap-filling a daily
        deposit report, and small dimension explosion. Plus the accidental cartesian product — a
        missing join predicate on 2.4M × 2.4M rows — and how it shows in the plan (`rows=` in the
        trillions). `[PLAN]` `[NUM]`
1.10.13 Non-equi joins: range joins (`ON a.period && b.period`), inequality joins, and why they force
        nested loop or merge rather than hash. `[PROVE]`
1.10.14 The **QuizStakes join that cannot exist**: "show me all my withdrawals" spans
        `cardpayments.transactions` and `bankwithdrawal.transactions`, in different schemas that
        never join (§7.3). The bible must show the SQL you *would* write, then state why the answer
        is a fan-out and merge in `ProfileService`, and what that costs (ordering after merge,
        pagination across two sources). `[SOURCE]` `[X-REF 22]`
1.10.15 Joining across databases when you must: `postgres_fdw`, `dblink`, and why pushdown
        (`use_remote_estimate`) decides whether it is usable or catastrophic. `[RESEARCH]`
1.10.16 Where the *algorithms* live: nested loop, hash join and merge join selection is §2.10 and
        their internals are §3.14. This section is semantics only.

*(16 leaves)*

## §1.11 Predicates, filters and the operator surface

1.11.1 Comparison operators, `BETWEEN` (inclusive both ends), `IN (list)`, `IN (subquery)`,
       `ANY`/`SOME`/`ALL` with an array or subquery, and `IS DISTINCT FROM` / `IS NOT DISTINCT FROM`
       as the NULL-safe equality pair. MySQL's `<=>` is the same operator with a different spelling.
       `[MYSQL]` `[SQL]`
1.11.2 `LIKE` / `ILIKE` / `SIMILAR TO` / POSIX regex `~ ~* !~ !~*` and the escape rules; `LIKE`'s
       `_` and `%` wildcards; `ESCAPE` clause. `[SQL]`
1.11.3 The indexability rule for pattern matching, stated once and proved: a B-tree can serve
       `LIKE 'DEP-30%'` (left-anchored, in a suitable operator class) and cannot serve `LIKE '%30%'`.
       `text_pattern_ops` exists for non-C collations. Leading-wildcard search needs `pg_trgm` GIN or
       full-text. `[PROVE]` `[TRAP]`
1.11.4 Boolean composition, short-circuit expectations, and the fact that **SQL does not guarantee
       evaluation order** — so `WHERE amount > 0 AND 1/amount < 1` can still divide by zero. Use
       `CASE` when you need ordering. `[TRAP]` `[PROVE]`
1.11.5 Subquery predicates: `EXISTS`, `NOT EXISTS`, scalar subqueries in `SELECT`/`WHERE`, and the
       "more than one row returned by a subquery used as an expression" error (SQLSTATE 21000).
       `[DIAG]`
1.11.6 `CASE` expressions (simple and searched), `COALESCE`, `NULLIF`, `GREATEST`/`LEAST` and their
       NULL behaviour, which differs between engines. `[MYSQL]` `[TRAP]`
1.11.7 Obfuscated conditions — Winand's catalogue, each with the QuizStakes rewrite: a function
       wrapped around the column (`DATE(posted_at) = ?` → a half-open range), arithmetic on the
       column (`amount * 100 > ?` → `amount > ?/100`), string/number type mixing, concatenated
       columns, and "smart logic" (`WHERE (:p IS NULL OR status = :p)`) which produces one plan for
       every parameter combination. `[SOURCE]` `[TRAP]` `[PROVE]`
1.11.8 Access predicate vs index filter predicate vs table filter predicate — the three-level
       distinction that explains why an index is "used" and the query is still slow. This is the
       single most useful concept from *SQL Performance Explained* and the plan lines that reveal it
       (`Index Cond` vs `Filter` vs `Rows Removed by Filter`). `[SOURCE]` `[PLAN]` `[PROVE]`
1.11.9 `OR` and why it defeats a single index: the planner needs a bitmap OR of two index scans or a
       `UNION ALL` rewrite. Show both, with plans. `[PLAN]` `[SQL]`
1.11.10 `IN` list length effects: constant-folding, `= ANY (ARRAY[...])` rewriting, and the plan
        instability caused by a variable-length `IN` list generating a new plan-cache entry per
        length. `[PROVE]` `[X-REF 08]`
1.11.11 Bind parameters vs literals: security (§2.28), plan caching (§3.10), and the *cost* of
        parameters — the planner cannot see the value, so a generic plan may be chosen for a skewed
        predicate. Both directions must be stated. `[JDBC]` `[PROVE]` `[TRAP]`
1.11.12 `IS TRUE` / `IS NOT TRUE` / `IS FALSE` / `IS UNKNOWN`, and why `NOT (x = TRUE)` differs from
        `x IS NOT TRUE` when `x` is NULL. `[PROVE]`

*(12 leaves)*

## §1.12 NULL and three-valued logic

1.12.1 SQL logic is TRUE / FALSE / **UNKNOWN**, and `WHERE`, `ON` and `HAVING` keep only TRUE. That
       one sentence generates every trap in this section. `[PROVE]`
1.12.2 The full AND/OR/NOT truth tables with UNKNOWN, written out. `NULL OR TRUE` = TRUE;
       `NULL AND FALSE` = FALSE; everything else with a NULL is UNKNOWN. `[PROVE]`
1.12.3 `x = NULL` is UNKNOWN, therefore zero rows, always. Only `IS NULL` works. In MySQL the
       `sql_mode` does not change this; nothing changes this. `[TRAP]`
1.12.4 **The `NOT IN` trap, proved**: `x NOT IN (1, 2, NULL)` expands to
       `x<>1 AND x<>2 AND x<>NULL`; the last term is UNKNOWN so the conjunction can never be TRUE;
       the query returns zero rows. `IN` with a NULL can match but can never return FALSE. The fix is
       `NOT EXISTS`, which the PostgreSQL wiki's *Don't Do This* states as a flat rule. `[TRAP]`
       `[PROVE]` `[SOURCE]` `[SQL]`
1.12.5 `<> 'ACTIVE'` silently excludes rows where the column is NULL. Write
       `status IS DISTINCT FROM 'ACTIVE'` or `(status <> 'ACTIVE' OR status IS NULL)`. In QuizStakes
       this is how a `restriction` with a NULL `expires_at` disappears from a "not expired" filter.
       `[TRAP]` `[SQL]`
1.12.6 NULL in aggregates: every aggregate except `COUNT(*)` ignores NULLs; `SUM` over zero rows
       returns NULL not 0; `AVG` divides by the non-NULL count. `COALESCE(SUM(x), 0)` is the fix, and
       it matters because a NULL balance rendered as blank is a support ticket. `[PROVE]`
1.12.7 NULL in `GROUP BY`: all NULLs form **one** group, even though they are not equal to each
       other. State the inconsistency plainly — it is deliberate. `[TRAP]` `[PROVE]`
1.12.8 NULL in `UNIQUE`: multiple NULLs allowed (they are not equal), unless
       `UNIQUE NULLS NOT DISTINCT` (PG 15+). `[VERSION-TRAP]`
1.12.9 NULL in `ORDER BY`: the `NULLS FIRST|LAST` defaults per engine (§1.9.8), and the interaction
       with an index's declared ordering — an index built `ASC NULLS LAST` cannot serve
       `ORDER BY ... ASC NULLS FIRST` without a sort. `[PROVE]`
1.12.10 NULL in indexes: PostgreSQL B-trees **do** store NULLs (so `WHERE x IS NULL` can use an
        index), Oracle's do not. Winand's *Myth Directory* entry "Oracle cannot index NULL" exists
        because this differs per engine. `[SOURCE]` `[TRAP]`
1.12.11 NULL in string concatenation and arithmetic: `'a' || NULL` is NULL in PostgreSQL, while
        MySQL's `CONCAT` also returns NULL but `CONCAT_WS` skips NULLs. `NULL + 1` is NULL.
        `[MYSQL]`
1.12.12 NULL through joins: an outer join *manufactures* NULLs, so a column declared `NOT NULL` can
        arrive NULL in a result set. This is why `08-spring-data-jpa.md`'s primitive-typed projection
        fields blow up. `[TRAP]` `[X-REF 08]`
1.12.13 NULL and `CHECK`: a `CHECK` constraint that evaluates to UNKNOWN **passes**. `CHECK (amount >
        0)` does not reject a NULL amount; you need `NOT NULL` as well. This is a real invariant hole.
        `[TRAP]` `[PROVE]`
1.12.14 The three meanings people cram into NULL — unknown, not applicable, and not yet supplied —
        and the modelling alternatives (a separate boolean, a sentinel row, a child table, a
        `state` enum). In QuizStakes, `expires_at IS NULL` means "never expires", which is a
        *third* meaning again; say so and give the `CHECK` that documents it.
1.12.15 NULL in JDBC: `ResultSet.getInt` returns `0` for NULL and you must call `wasNull()`;
        `getObject(int, Integer.class)` returns `null` properly; `setNull(i, Types.X)` vs
        `setObject(i, null)`. This is where a NULL becomes a silent zero in a Java service —
        and in a money column, a silent zero is a wrong balance. `[JDBC]` `[TRAP]` `[NUM]`
1.12.16 The design position: `NOT NULL` by default, nullable only where you can say what the NULL
        means. Every nullable money column in QuizStakes would be a bug.

*(16 leaves)*

## §1.13 Aggregation, `GROUP BY`, `HAVING`, `GROUPING SETS`

1.13.1 The aggregate inventory: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `STRING_AGG`, `ARRAY_AGG`,
       `JSON_AGG`/`JSONB_AGG`, `JSONB_OBJECT_AGG`, `BOOL_AND`/`BOOL_OR`, `EVERY`, `BIT_AND`/`BIT_OR`,
       `STDDEV`/`VARIANCE` (samp and pop), `CORR`/`REGR_*`, `PERCENTILE_CONT`/`PERCENTILE_DISC` (as
       ordered-set aggregates with `WITHIN GROUP`), and `MODE()`. `[SQL]`
1.13.2 `COUNT(*)` counts rows, `COUNT(col)` counts non-NULL values, `COUNT(DISTINCT col)`
       deduplicates, `COUNT(1)` is identical to `COUNT(*)`. The first two differing is a standard
       probe. `[PROVE]`
1.13.3 `WHERE` filters rows *before* grouping; `HAVING` filters groups *after*. A predicate that can
       go in `WHERE` should, because it reduces the input to the aggregate. `[PROVE]`
1.13.4 The `GROUP BY` rule: every non-aggregated `SELECT` expression must be functionally dependent
       on the grouping columns. PostgreSQL enforces it (and accepts a primary key as sufficient,
       per SQL:1999 functional-dependency detection); MySQL without `ONLY_FULL_GROUP_BY` returns an
       **arbitrary row** — a silent wrong answer, and the reason that sql_mode is on by default from
       5.7.5. `[MYSQL]` `[TRAP]` `[NUM]`
1.13.5 `FILTER (WHERE ...)` on an aggregate: the standard way to compute several conditional
       aggregates in one pass. `count(*) FILTER (WHERE status = 'RESERVED')` beats
       `sum(CASE WHEN ... THEN 1 ELSE 0 END)` for readability and equals it for cost. `[SQL]`
1.13.6 `DISTINCT` inside an aggregate (`COUNT(DISTINCT client_id)`) forces a sort or hash of the whole
       input per group and cannot be combined with `FILTER` cheaply; at 2.8M stakes/day this is the
       difference between a report and an incident. `[NUM]` `[PROVE]`
1.13.7 `GROUPING SETS`, `ROLLUP` and `CUBE`: the exact expansion of each (`ROLLUP(a,b)` = 3 sets,
       `CUBE(a,b)` = 4 sets, `CUBE` over *n* columns = 2ⁿ sets), the `GROUPING(col)` function for
       telling a subtotal row from a real NULL, and the fact that one `GROUPING SETS` scan replaces a
       `UNION ALL` of *n* aggregations. `[SQL]` `[NUM]` `[PROVE]` `[RESEARCH]`
1.13.8 **Trap: distinguishing a `ROLLUP` subtotal row from a genuine NULL group.** Both render as
       NULL; only `GROUPING()` tells them apart, and reports that skip this are silently wrong.
       `[TRAP]`
1.13.9 Empty `GROUP BY ()` and the difference between an aggregate over zero rows with grouping
       (zero result rows) and without (one row containing NULL/0). This is why "the dashboard shows
       no data" and "the dashboard shows zero" are different bugs. `[PROVE]`
1.13.10 Aggregate implementation choice — `HashAggregate` vs `GroupAggregate` (which needs sorted
        input) vs `MixedAggregate` (for grouping sets) — and PG 13+'s hash-aggregate spill to disk
        with `hash_mem_multiplier` (default **2.0**). `[PLAN]` `[GUC]` `[NUM]`
1.13.11 Recognising aggregation in a word problem, as a decision procedure: "per / for each / by
        <noun>" → that noun is the grouping key; "total / average / count / highest / number of" →
        the aggregate; "only those with more than N" → `HAVING`; "top N per <noun>" → a window
        function or `LATERAL`, **not** `GROUP BY`. `[PROVE]`
1.13.12 Aggregates on the QuizStakes ledger, written out: position balance as
        `SUM(CASE direction WHEN 'CREDIT' THEN amount ELSE -amount END)`, the sum-to-zero
        reconciliation check as `SUM(...) = 0` per `movement_id`, and daily cumulative deposit per
        client for the limit gate. Each with the index that makes it viable. `[SQL]` `[SOURCE]`
1.13.13 User-defined aggregates (`CREATE AGGREGATE` with `sfunc`/`stype`/`finalfunc`/`combinefunc`)
        and why `combinefunc` is what makes an aggregate parallel-safe. `[RESEARCH]`
1.13.14 Ordered-set and hypothetical-set aggregates: `percentile_cont(0.99) WITHIN GROUP (ORDER BY
        latency_ms)` for the p99 numbers in Appendix A.4/A.7, and `rank() WITHIN GROUP`.
        `[SQL]` `[NUM]`

*(14 leaves)*

## §1.14 Set operations

1.14.1 `UNION` vs `UNION ALL`: `UNION` deduplicates (a sort or hash over the whole result),
       `UNION ALL` does not. Default to `UNION ALL` and add `UNION` only when you need the
       dedupe — this is a common free performance win. `[PROVE]`
1.14.2 `INTERSECT`, `EXCEPT` (`MINUS` in Oracle), and their `ALL` variants with bag semantics —
       `EXCEPT ALL` subtracts multiplicities. `[SQL]`
1.14.3 Compatibility rules: same column count, compatible types positionally, output names from the
       first branch, and `ORDER BY`/`LIMIT` applying to the *whole* set operation unless parenthesised.
       `[TRAP]`
1.14.4 NULLs are treated as equal for deduplication in set operations — the opposite of `=`. Prove it
       and note the inconsistency with §1.12. `[PROVE]` `[TRAP]`
1.14.5 Operator precedence: `INTERSECT` binds tighter than `UNION` and `EXCEPT`; parenthesise
       always.
1.14.6 The **`UNION ALL` fan-out as the QuizStakes withdrawal answer**, and why it is *not*
       available: the two `transactions` tables are in schemas that never join (§7.3), so the union
       happens in `ProfileService`, in application code, with ordering imposed after the merge. Show
       the SQL you would write in a single-schema world and then the shape of the code that replaces
       it. `[SOURCE]` `[SQL]`
1.14.7 `UNION ALL` as a planner tool: rewriting an `OR` across two indexed columns into two indexable
       branches, and rewriting a partitioned scan. Show plans before and after. `[PLAN]`
1.14.8 `VALUES` as a table constructor in `FROM`, in `INSERT`, and joined against — the cheapest way
       to pass 50 client ids from Java without a temp table, and how it interacts with
       `setArray`/`unnest`. `[JDBC]` `[SQL]`
1.14.9 Recursive `UNION ALL` inside `WITH RECURSIVE` is a different construct with different
       semantics (§1.16); do not confuse the two. `[TRAP]`

*(9 leaves)*

## §1.15 Subqueries

1.15.1 The taxonomy: scalar subquery (one row one column), row subquery, table subquery/derived table,
       correlated vs uncorrelated, and by position — `SELECT` list, `FROM`, `WHERE`, `HAVING`,
       `GROUP BY`, `ON`, `VALUES`, `LIMIT`.
1.15.2 Uncorrelated subqueries can be evaluated once (and often are, via an `InitPlan`); correlated
       subqueries are evaluated per outer row unless the planner can decorrelate them. Show both in a
       plan, naming `SubPlan` and `InitPlan`. `[PLAN]` `[PROVE]`
1.15.3 **Decorrelation / subquery flattening** is the single most valuable rewrite the planner does:
       `IN (subquery)` becomes a semi-join, `EXISTS` becomes a semi-join, and a scalar aggregate
       subquery in `SELECT` usually does *not* get flattened — which is why the "N+1 in SQL" shape of
       §2.16 exists. `[PROVE]`
1.15.4 A scalar subquery in the `SELECT` list executes once per output row. At 50 rows on the operator
       queue screen that is the §15.6 N+1 example expressed in one statement instead of fifty round
       trips — still 50 index lookups, but one round trip. Say which cost you actually removed.
       `[NUM]` `[PROVE]` `[X-REF 08]`
1.15.5 `EXISTS` vs `IN` vs `= ANY` vs join: when they are equivalent, when they are not (NULLs,
       duplicates), and what each looks like in the plan. Give the decision rule rather than the
       folklore. `[PROVE]` `[TRAP]`
1.15.6 The duplicate-row hazard of rewriting a semi-join as a join: `INNER JOIN` multiplies rows when
       the inner side is not unique, so `EXISTS` → `JOIN` requires `DISTINCT` and then you have paid
       for a dedupe. `[TRAP]` `[PROVE]`
1.15.7 Derived tables and the alias requirement; correlated derived tables requiring `LATERAL`; and
       the fact that a derived table is *not* an optimization fence in PostgreSQL — it will be pulled
       up. `[PROVE]`
1.15.8 `ANY`/`ALL` with subqueries, their NULL behaviour, and `> ALL (empty set)` being TRUE, which
       surprises everyone. `[PROVE]` `[TRAP]`
1.15.9 The QuizStakes subquery set, written out with plans: "reservations with no settlement"
       (anti-join for `ORPHANED`), "clients whose cumulative deposits crossed the threshold"
       (correlated aggregate vs window), "the latest `application_history` row per application"
       (`DISTINCT ON` vs `LATERAL` vs window), and "positions that disagree with the sum of their
       entries" (the reconciliation query). `[SQL]` `[PLAN]`
1.15.10 Subquery limits worth knowing: no `LIMIT` in a subquery used with `IN` in old MySQL,
        `LIMIT` inside `IN` unsupported in MySQL before 8.0, and MySQL's historically poor
        `IN (subquery)` handling — the reason so much Java code was written with two round trips.
        `[MYSQL]` `[VERSION-TRAP]`

*(10 leaves)*

## §1.16 Common table expressions, including recursive

1.16.1 `WITH name AS (query)` — naming an intermediate result, multiple CTEs in one `WITH`, later
       CTEs referencing earlier ones, and a CTE referenced twice.
1.16.2 The **optimization-fence change**: before PostgreSQL 12 every CTE was materialised (an
       optimization fence); from 12 a CTE that is referenced once, is not recursive and has no
       side effects is *inlined* by default, with `MATERIALIZED` / `NOT MATERIALIZED` as the explicit
       override. Every pre-2019 blog post about "CTEs are a fence" is stale. `[VERSION-TRAP]`
       `[PROVE]` `[NUM]`
1.16.3 When you *want* `MATERIALIZED`: an expensive CTE referenced many times, or a deliberate fence
       to stop the planner pushing a predicate into a volatile function. `[SQL]`
1.16.4 Data-modifying CTEs (`WITH moved AS (DELETE ... RETURNING *) INSERT INTO archive SELECT * FROM
       moved`) — PostgreSQL-only, all statements see the *same* snapshot, and the execution order
       between branches is unspecified. This is the archival move for the 90-day hot window in one
       statement, with the caveat stated. `[SQL]` `[TRAP]` `[NUM]`
1.16.5 `WITH RECURSIVE` anatomy: the non-recursive seed term, `UNION ALL` (or `UNION` for
       deduplication), the recursive term referencing the CTE name exactly once, and the working-table
       algorithm that evaluates it. `[FLOW]` `[PROVE]`
1.16.6 The evaluation algorithm spelled out: evaluate seed → working table; loop { evaluate recursive
       term against the working table → intermediate table; append to result; working table :=
       intermediate } until empty. Naming this makes the cycle and depth problems obvious.
       `[PROVE]`
1.16.7 Cycle protection: a `path` array with `NOT (id = ANY(path))`, or the standard `CYCLE col SET
       is_cycle USING path` clause (PG 14+). Without one, a cycle in the data is an infinite loop that
       consumes disk until the query is killed. `[VERSION-TRAP]` `[TRAP]` `[SQL]`
1.16.8 Depth limiting and `SEARCH BREADTH FIRST BY col SET ord` / `SEARCH DEPTH FIRST BY col SET ord`
       (PG 14+) as the standard way to get a deterministic traversal order. `[VERSION-TRAP]`
1.16.9 Recursive CTE use cases in QuizStakes: walking the `application_history` chain of transitions
       for one application, expanding a hierarchy of `restriction` reasons, generating the four daily
       `PaymentRun` windows, and gap-filling a date series. `[SQL]`
1.16.10 `generate_series` as the non-recursive alternative for the series cases, and why it is
        strictly better when you are only counting. `[PROVE]`
1.16.11 Recursive query cost: the planner has almost no idea how many rows a recursive term produces
        (it guesses), so recursive CTEs are the single most common source of catastrophic
        misestimation. Show `rows=` vs `actual rows=` on a real recursion. `[PLAN]` `[TRAP]`
1.16.12 MySQL 8.0+ supports `WITH` and `WITH RECURSIVE` with `cte_max_recursion_depth` (default
        **1000**) as a safety valve — a mechanism PostgreSQL does not have. `[MYSQL]` `[NUM]`
        `[RESEARCH]`
1.16.13 CTEs as readability, not performance: state plainly that a CTE chain and a nested-subquery
        chain usually produce the same plan post-12, so choose on legibility. `[TRAP]`

*(13 leaves)*

## §1.17 Window functions

1.17.1 The definition that separates them from aggregates: a window function computes across a set of
       rows **without collapsing them**. Same row count in, same row count out. `[PROVE]`
1.17.2 The `OVER` clause anatomy: `PARTITION BY`, `ORDER BY`, and the frame clause, each optional and
       each changing the answer.
1.17.3 The ranking family with exact tie behaviour: `ROW_NUMBER` (always distinct: 1,2,3,4),
       `RANK` (ties share, gaps follow: 1,1,3), `DENSE_RANK` (ties share, no gaps: 1,1,2),
       `PERCENT_RANK`, `CUME_DIST`, `NTILE(n)`. `[NUM]` `[PROVE]`
1.17.4 The offset family: `LAG(expr, offset, default)`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`,
       `NTH_VALUE(expr, n)`. `LAG`/`LEAD` are the tool for deltas, gap detection and
       state-transition durations. `[SQL]`
1.17.5 **`LAST_VALUE` returns the current row by default** because the default frame ends at
       `CURRENT ROW`. This is the most-reported "window function is broken" bug; the fix is
       `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. `[TRAP]` `[PROVE]`
1.17.6 Any aggregate can be used as a window function: `SUM(amount) OVER (...)`,
       `COUNT(*) OVER ()`, `AVG(...) OVER (...)`, and `array_agg` for a running collection.
1.17.7 The frame clause in full: `{ROWS | RANGE | GROUPS} BETWEEN frame_start AND frame_end` with
       `UNBOUNDED PRECEDING`, `n PRECEDING`, `CURRENT ROW`, `n FOLLOWING`, `UNBOUNDED FOLLOWING`,
       plus `EXCLUDE {CURRENT ROW | GROUP | TIES | NO OTHERS}` (PG 11+). `[NUM]`
       `[VERSION-TRAP]`
1.17.8 **The default frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` when `ORDER BY` is
       present, and `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` when it is not.**
       `RANGE` treats peer rows (equal `ORDER BY` values) as one unit, so a running total over a
       timestamp with duplicate values jumps. Use `ROWS` when you mean row-by-row. `[TRAP]`
       `[PROVE]` `[NUM]`
1.17.9 `ROWS` vs `RANGE` vs `GROUPS`, with the same data producing three different running totals —
       the write pass must show the three side by side. `[PROVE]` `[SQL]`
1.17.10 `RANGE` with a numeric or interval offset (`RANGE BETWEEN INTERVAL '7 days' PRECEDING AND
        CURRENT ROW`) — the 7-day rolling deposit total for the AML velocity check, expressed
        exactly. `[SQL]` `[SOURCE]`
1.17.11 Named windows: `WINDOW w AS (PARTITION BY client_id ORDER BY posted_at)` and reuse via
        `OVER w`, including `OVER (w ROWS ...)` to refine a named window. `[SQL]`
1.17.12 **You cannot filter on a window function in `WHERE` or `GROUP BY`** — windows are computed
        after both. Hence the CTE/subquery wrapper for top-N-per-group. Prove it from §1.9.1.
        `[TRAP]` `[PROVE]`
1.17.13 The canonical top-N-per-group pattern with `ROW_NUMBER` in a CTE and `WHERE rn <= 3`, plus
        the two alternatives and when each wins: `DISTINCT ON` (PostgreSQL, top-1, fastest) and
        `LATERAL` with `LIMIT n` (best when the outer set is small and an index supports the inner
        `ORDER BY ... LIMIT`). `[SQL]` `[PROVE]`
1.17.14 `QUALIFY` exists in Snowflake/Teradata/DuckDB and **not** in PostgreSQL or MySQL; know the
        name so you recognise it, and know the CTE rewrite. `[TRAP]` `[RESEARCH]`
1.17.15 Window functions in the QuizStakes domain, each with the index that makes it viable: running
        balance per position from `ledger_entry` (and why you would still not store it), time between
        `AO-400` and `AA-801` per application via `LAG`, detecting a `RETURNED` arriving after
        `SUCCESS`, the deposit-to-stake ratio per client per rolling window (§10.3's AML trigger), and
        ranking operator queue cases by age. `[SQL]` `[SOURCE]`
1.17.16 Execution mechanics: a `WindowAgg` node requires input sorted by
        `PARTITION BY` then `ORDER BY`, so an index on `(client_id, posted_at)` can remove the sort
        entirely — and PG 18 reports `WindowAgg` memory/disk usage in `EXPLAIN ANALYZE`.
        `[PLAN]` `[RESEARCH]`
1.17.17 Cost model: one pass per distinct window definition, so three windows with the same `OVER`
        clause cost one sort and three with different clauses cost three. Consolidate window
        definitions deliberately. `[PROVE]` `[NUM]`
1.17.18 MySQL support: window functions arrived in 8.0, and `EXCLUDE` is not supported. Anything
        written for MySQL 5.7 uses the user-variable emulation, which is why you will still meet
        `@rownum := @rownum + 1` in old code. `[MYSQL]` `[VERSION-TRAP]`

*(18 leaves)*

## §1.18 Ordering, limiting and the shape of a result set

1.18.1 `ORDER BY` cost: a `Sort` node with `work_mem`-bounded quicksort, or an external merge sort on
       disk (`external merge Disk: nnnkB` in the plan), or no sort at all if an index provides the
       order. The three cases and how to tell which you got. `[PLAN]` `[NUM]`
1.18.2 The **pipelined order-by** insight: an index that satisfies `ORDER BY` lets `LIMIT n` stop
       after *n* rows, turning an O(N log N) sort into O(n) — Winand's "third power of indexing".
       `[SOURCE]` `[PROVE]`
1.18.3 The conditions for a B-tree to serve `ORDER BY`: the sort columns must be a prefix of the
       index columns, in the same or exactly-inverted direction, with matching `NULLS FIRST|LAST`.
       Mixed `ASC`/`DESC` needs an index declared the same way. `[PROVE]` `[SQL]`
1.18.4 `LIMIT` without `ORDER BY` is nondeterministic; `LIMIT` with a non-unique `ORDER BY` is also
       nondeterministic across pages. Every paginated API needs a unique tiebreaker column. This is
       the bug that shows a user the same withdrawal twice. `[TRAP]` `[PROVE]`
1.18.5 `OFFSET`'s cost model: the executor produces and discards the offset rows, so cost grows
       linearly with page number. `LIMIT 20 OFFSET 100000` reads 100,020 rows. `[NUM]` `[PROVE]`
1.18.6 `FETCH FIRST n ROWS WITH TIES` and its interaction with `ORDER BY`. `[VERSION-TRAP]`
1.18.7 `LIMIT` interacts with the planner's *fractional* cost estimation: a `LIMIT` makes a
       start-up-cheap plan (nested loop, index scan) preferable to a total-cost-cheap plan (hash
       join), which is why adding `LIMIT 1` can change the whole plan shape and occasionally make it
       far worse. PG 18 reports fractional row counts in `EXPLAIN`. `[PROVE]` `[PLAN]`
       `[RESEARCH]`
1.18.8 Cursors as the other way to bound a result: `DECLARE ... CURSOR`, `FETCH n`, `WITH HOLD`, and
       `cursor_tuple_fraction` (default **0.1**) telling the planner you only want the first 10%.
       `[GUC]` `[NUM]`
1.18.9 The JDBC face of the same problem: `Statement.setFetchSize(n)` on PostgreSQL requires
       `autoCommit = false` *and* a forward-only result set to actually use a cursor — otherwise the
       driver buffers the whole result in the JVM heap. On MySQL the equivalent is
       `setFetchSize(Integer.MIN_VALUE)` plus `useCursorFetch`. This is the most common OOM in a
       reporting job. `[JDBC]` `[TRAP]` `[NUM]` `[X-REF 06]`
1.18.10 `SELECT ... FOR UPDATE` with `LIMIT` and why the locking happens after the limit, plus
        `FOR UPDATE` being disallowed with `DISTINCT`, `GROUP BY`, window functions and set
        operations. `[TRAP]`
1.18.11 Result-set metadata and column ordering: `SELECT *` column order is `attnum` order minus
        dropped columns — never rely on positional access with `*`. `[JDBC]` `[TRAP]`

*(11 leaves)*

## §1.19 Views, materialized views and generated columns

1.19.1 A view is a stored query, not stored data: it is expanded (inlined) into the referencing query
       by the *rewriter*, before planning. That single fact answers most view performance questions.
       `[PROVE]`
1.19.2 Auto-updatable views: the conditions (one base table, no aggregates/DISTINCT/set
       ops/window functions/GROUP BY/HAVING/LIMIT, no duplicate columns) and `WITH CHECK OPTION`
       (`LOCAL` vs `CASCADED`). `[NUM]`
1.19.3 `INSTEAD OF` triggers for non-updatable views — the mechanism behind an "API view" over a
       normalised schema.
1.19.4 `security_barrier` and `security_invoker` (PG 15+) views: without a barrier, a
       `LEAKPROOF`-violating function in the caller's `WHERE` can be evaluated before the view's own
       filter and leak rows. This is the mechanism that makes a "view as access control" safe.
       `[VERSION-TRAP]` `[X-REF 13]` `[PROVE]`
1.19.5 Materialized views: physically stored, stale by definition, `REFRESH` takes `ACCESS
       EXCLUSIVE`, `REFRESH ... CONCURRENTLY` needs a unique index and does a diff-based update at
       roughly double the cost. There is no incremental maintenance in core PostgreSQL.
       `[NUM]` `[TRAP]`
1.19.6 The QuizStakes decision: a materialized view is legitimate for `ProfileService`-shaped cold,
       wide, human-triggered reads and illegitimate for `BalanceView`'s hot path and outright
       forbidden as a stake/withdrawal decision input (§14.2 invariant 12, §15.4 "never cache").
       `[SOURCE]` `[X-REF 15]`
1.19.7 Generated columns as the third option: `STORED` (indexable, costs write time and space) vs
       **virtual, the new PG 18 default** (free to write, not indexable, costs read time). Use a
       stored generated column for `lower(email)`-style search keys where you would otherwise need an
       expression index. `[RESEARCH]` `[VERSION-TRAP]`
1.19.8 `WITH ORDINALITY`, set-returning functions in `FROM`, and why a set-returning function in the
       `SELECT` list is deprecated behaviour you should not write. `[TRAP]`
1.19.9 System views vs user views: `pg_stat_*`, `information_schema` and `pg_catalog` are views over
       C functions and shared memory, so querying them is not free and some of them take locks.
       `[TRAP]`
1.19.10 Foreign tables and `postgres_fdw`/`file_fdw` as a view onto data you do not own — the honest
        option for reading a bank statement file in place. `[RESEARCH]`

*(10 leaves)*

## §1.20 JSON in a relational database

1.20.1 `json` vs `jsonb` restated with the operational consequence: only `jsonb` is indexable and
       only `jsonb` normalises keys. `[TRAP]`
1.20.2 The operator surface: `->`, `->>`, `#>`, `#>>`, `@>`, `<@`, `?`, `?|`, `?&`, `||`, `-`, `#-`,
       and PG 14+'s subscripting `data['key']`. `[SQL]`
1.20.3 SQL/JSON path: `jsonb_path_query`, `jsonb_path_exists`, `@?`, `@@`, and the `jsonpath` type's
       filter syntax. `[SQL]` `[VERSION-TRAP]`
1.20.4 SQL:2016 constructors and SQL/JSON functions in PG 16/17: `JSON_EXISTS`, `JSON_QUERY`,
       `JSON_VALUE`, `JSON_TABLE`, `JSON_ARRAY`, `JSON_OBJECT`, `IS JSON`. State which arrived in
       which release rather than assuming. `[VERSION-TRAP]` `[RESEARCH]`
1.20.5 Indexing JSONB: GIN with the default `jsonb_ops` (keys and values) vs `jsonb_path_ops`
       (smaller, only `@>`-style containment), plus a B-tree expression index on one extracted key as
       the cheaper option when you always query the same field. `[PROVE]` `[NUM]`
1.20.6 Statistics on JSONB are effectively absent — the planner cannot estimate
       `data @> '{"k":"v"}'` well, which is why JSONB-heavy queries misestimate and pick bad joins.
       This is the strongest technical argument against a JSONB-as-schema design. `[PROVE]`
       `[TRAP]`
1.20.7 When JSONB is right in QuizStakes: the vendor payload from `DocumentVerification` (an
       anti-corruption boundary where the shape is theirs, not ours) and an audit `before`/`after`
       snapshot in `application_history`. When it is wrong: anything with an invariant — a `Money`
       amount in JSONB cannot carry `CHECK (amount > 0)` usefully. `[SOURCE]` `[PROVE]`
1.20.8 TOAST interaction: a large JSONB value is compressed and out-of-lined, so `data->>'k'` on a
       10 KB document detoasts the whole thing per row. Show the cost against a 24k-uploads/day
       verification payload. `[NUM]` `[PROVE]`
1.20.9 MySQL's `JSON` type: binary, validated, with `->` / `->>` sugar,
       `JSON_EXTRACT`/`JSON_SET`/`JSON_CONTAINS`, no GIN — indexing requires a *generated column* plus
       an index on it, or a multi-valued index (8.0.17+) for array containment. `[MYSQL]`
       `[VERSION-TRAP]` `[RESEARCH]`
1.20.10 JSONB from Java: pgJDBC needs `PGobject` or `?::jsonb` casting, `stringtype=unspecified` as
        the connection-property workaround, and the Jackson boundary. `[JDBC]` `[X-REF 08]`
1.20.11 SQL:2023's `JSON` data type, dot-notation access, `JSON_SERIALIZE`, `JSON_SCALAR` and the 14
        new SQL/JSON methods — named, with the statement that PostgreSQL 18 and MySQL 8.4 do not
        implement the type. `[RESEARCH]` `[VERSION-TRAP]`
1.20.12 The design rule: JSONB for *data whose shape you do not control*, columns for data whose shape
        you do. Anything you filter, join or constrain on becomes a column.

*(12 leaves)*

## §1.21 Text search and pattern matching

1.21.1 The three levels, with what each can and cannot do: `LIKE`/`ILIKE` (substring, no ranking),
       trigram similarity via `pg_trgm` (fuzzy, leading wildcards, `%` operator and `similarity()`),
       and full-text search (`tsvector`/`tsquery`, stemming, ranking, phrase search).
1.21.2 Full-text mechanics: `to_tsvector(config, text)`, `to_tsquery`, `plainto_tsquery`,
       `phraseto_tsquery`, `websearch_to_tsquery`, the `@@` match operator, `ts_rank`/`ts_rank_cd`,
       `ts_headline`, and text search configurations/dictionaries. `[SQL]`
1.21.3 Indexing FTS: GIN (fast lookup, slow update, exact) vs GiST (smaller, lossy, needs recheck),
       and the stored-`tsvector`-column-plus-trigger pattern versus an expression index. `[PROVE]`
1.21.4 `pg_trgm` GIN/GiST for `LIKE '%...%'` — the only way to index a leading wildcard — with the
       index-size cost stated. `[NUM]`
1.21.5 The QuizStakes case that needs it: §15.3's "find the unmatched bank deposit mentioning this
       reference" over 5B rows, where the reference is embedded in free-text remittance
       information. State exactly which of the three levels solves it and why. `[SOURCE]` `[NUM]`
1.21.6 Collation and case-insensitivity: `citext`, `lower()` expression index, and PG 12+'s
       nondeterministic ICU collations with `deterministic = false` for case- and accent-insensitive
       comparison — including the fact that a nondeterministic collation disables some optimisations
       and that PG 18 added `LIKE` support with them. `[VERSION-TRAP]` `[RESEARCH]`
1.21.7 `casefold()` — new in PG 18 — as the Unicode-correct alternative to `lower()` for
       case-insensitive matching. `[RESEARCH]` `[VERSION-TRAP]`
1.21.8 MySQL's contrast: `FULLTEXT` indexes on InnoDB with `MATCH ... AGAINST`, natural language vs
       boolean vs query expansion modes, `ngram` parser for CJK, `innodb_ft_min_token_size`
       (default **3**) — and the fact that MySQL collations are case-insensitive *by default*, which
       silently changes every `=` comparison relative to PostgreSQL. `[MYSQL]` `[NUM]` `[TRAP]`
1.21.9 When to leave the database: the honest boundary where Elasticsearch/OpenSearch earns its
       place, and the cost you take on (a second store to keep in sync). `[X-REF 22]`

*(9 leaves)*

## §1.22 Dates, times and the arithmetic that breaks

1.22.1 The type set and what each stores: `date`, `time`, `timetz` (don't), `timestamp`,
       `timestamptz`, `interval`. `timestamptz` stores a UTC instant with microsecond resolution and
       **no** zone — the zone is a rendering concern. `[TRAP]` `[PROVE]`
1.22.2 `now()` / `CURRENT_TIMESTAMP` / `transaction_timestamp()` are **transaction start**;
       `statement_timestamp()` is statement start; `clock_timestamp()` is the actual wall clock.
       Using `now()` to time a loop inside one transaction returns the same value every iteration.
       `[TRAP]` `[PROVE]`
1.22.3 Interval arithmetic and its non-associativity: `+ INTERVAL '1 month'` is calendar-aware and
       `+ INTERVAL '30 days'` is not, so the two differ and neither is wrong. The QuizStakes bonus
       expiry ("30 days from grant") and coupon validity ("14 days from registration") must pick one
       and document it. `[NUM]` `[SOURCE]` `[PROVE]`
1.22.4 `date_trunc`, `date_part`/`EXTRACT`, `age`, `justify_interval`, `overlaps`, `generate_series`
       over timestamps, and `make_timestamptz`.
1.22.5 The indexability rule restated for dates: `WHERE date_trunc('day', posted_at) = ?` cannot use
       an index on `posted_at`; `WHERE posted_at >= ? AND posted_at < ? + INTERVAL '1 day'` can. This
       is the single most common index-defeating rewrite in reporting code. `[TRAP]` `[SQL]`
       `[PROVE]`
1.22.6 Time-zone handling end to end for a regulated system: store `timestamptz`, compute in UTC,
       render in the client's jurisdiction zone, and never let the *session* `TimeZone` decide a
       business boundary — because "the daily deposit limit resets at midnight" needs a named zone,
       not the connection's default. `[TRAP]` `[SOURCE]`
1.22.7 DST hazards: a local time that does not exist (spring forward) and one that occurs twice
       (autumn back), and what each does to a "4 payment run windows per day" schedule.
       `[NUM]` `[PROVE]`
1.22.8 MySQL's contrast: `DATETIME` (no zone) vs `TIMESTAMP` (stored UTC, converted using
       `time_zone`, and limited to 1970–2038), `explicit_defaults_for_timestamp`, and the 2038
       problem being real for a system with 7-year retention. `[MYSQL]` `[NUM]` `[TRAP]`
1.22.9 Java mapping and the `java.time` boundary: `OffsetDateTime`/`Instant` for `timestamptz`,
       never `java.util.Date`, never `LocalDateTime` for an instant. `[JDBC]` `[X-REF 03]`
1.22.10 Clock skew as a correctness problem, not a formatting one: §15.2's "self-exclusion timestamped
        by one service, the stake by another — which came first?" The database's own clock is the only
        one all writers share, which is an argument for `now()` defaults on audit columns.
        `[SOURCE]` `[X-REF 22]`

*(10 leaves)*

## §1.23 Transactions and ACID

1.23.1 A transaction is a unit of work that is all-or-nothing. `BEGIN`/`START TRANSACTION`, `COMMIT`,
       `ROLLBACK`, `SAVEPOINT name`, `ROLLBACK TO SAVEPOINT`, `RELEASE SAVEPOINT`,
       `SET TRANSACTION`, `SET TRANSACTION SNAPSHOT`, and `BEGIN READ ONLY | DEFERRABLE`.
       `[SQL]`
1.23.2 The four letters with a **disambiguator** for each, because the exam question is always "which
       letter": **Atomicity** = partial failure (crash halfway through a movement);
       **Consistency** = invariants (a `CHECK`/FK/unique rule cannot be violated by a committed
       transaction); **Isolation** = concurrency (two users at once);
       **Durability** = the commit survives power loss. `[PROVE]`
1.23.3 The confusion to kill: this **C is not the C in CAP** (that one is about replicas agreeing) and
       is not "the data is correct". If the scenario has two concurrent users, the answer is
       Isolation. Crash mid-transaction → Atomicity. Crash after commit returned → Durability.
       `[TRAP]` `[X-REF 22]`
1.23.4 Which mechanism implements which letter, so the letters stop being vocabulary: Atomicity =
       undo (WAL + abort processing / InnoDB undo log); Consistency = constraint checking;
       Isolation = MVCC + the lock manager; Durability = WAL + `fsync` at commit. `[PROVE]`
1.23.5 Autocommit: every bare statement is its own transaction in both engines and in JDBC by
       default. `Connection.setAutoCommit(false)` is what opens a transaction from Java, and Spring's
       `@Transactional` does exactly that. `[JDBC]` `[X-REF 07]`
1.23.6 Implicit transaction start in PostgreSQL (a statement outside a block runs in its own
       transaction) versus MySQL's `autocommit=1` system variable, and the DDL implicit-commit
       difference (§1.6.14). `[MYSQL]`
1.23.7 Read-only transactions (`BEGIN READ ONLY`): they cannot write, they never take a serialization
       failure under SSI, and `DEFERRABLE` makes a read-only serializable transaction wait for a
       safe snapshot instead of risking an abort. This is the right mode for a reconciliation sweep
       over the ledger. `[PROVE]` `[SOURCE]`
1.23.8 Savepoints: nested-transaction emulation, what a rollback to savepoint releases (locks taken
       after it are dropped; the transaction id survives), and the cost — each savepoint is a
       subtransaction with its own `xid`, and >64 subtransactions per transaction overflows the
       per-backend cache and hurts every other backend via `SubtransSLRU` contention. This is the
       hidden cost of `Propagation.NESTED` and of catching an exception per row.
       `[NUM]` `[PROVE]` `[TRAP]` `[X-REF 07]`
1.23.9 Transaction size as an operational variable: a long transaction holds a snapshot (blocking
       vacuum, §3.18), holds locks, holds a connection, and grows the undo/WAL it must be able to
       roll back. "Keep transactions short" is a mechanism claim, not advice.
1.23.10 `idle_in_transaction_session_timeout` (default **0** = off),
        `statement_timeout` (default **0**), `lock_timeout` (default **0**),
        `transaction_timeout` (PG 17+), and `deadlock_timeout` (default **1s**). Every production
        system sets the first three. `[GUC]` `[NUM]` `[VERSION-TRAP]`
1.23.11 **Never do network I/O inside a transaction.** The QuizStakes proof: `DEP-301 → DEP-400`
        spans a PSP call whose p99 is 6s and whose timeout is 10s; holding a ledger transaction across
        it would hold row locks on the client's positions for up to ten seconds at 1,200 stakes/sec.
        The compensation-based design in §12.2 exists because of this constraint.
        `[SOURCE]` `[NUM]` `[PROVE]` `[TRAP]`
1.23.12 Two-phase commit at the SQL layer: `PREPARE TRANSACTION 'gid'`, `COMMIT PREPARED`,
        `ROLLBACK PREPARED`, `max_prepared_transactions` (default **0**, i.e. disabled), and
        `pg_prepared_xacts`. A prepared transaction holds its locks and its snapshot **forever** if
        nobody resolves it — the classic way to freeze a database with XA. The QuizStakes position
        (§15.2) is that the PSP will never join your transaction, so XA is not the answer.
        `[GUC]` `[NUM]` `[TRAP]` `[X-REF 22]`
1.23.13 `SET TRANSACTION SNAPSHOT` and exported snapshots (`pg_export_snapshot`): how `pg_dump`
        parallel workers all see one consistent state, and how you would take a consistent
        multi-table extract for reconciliation. `[SQL]`
1.23.14 Where the transaction boundary belongs in a Java service, stated once here and cross-referenced:
        at the application-service method, never in the controller, never around a vendor call.
        `[X-REF 07]` `[X-REF 08]`

*(14 leaves)*

## §1.24 Isolation levels and the anomalies they permit

1.24.1 The anomaly catalogue with a precise definition and a QuizStakes instance each:
       **dirty read** (reading uncommitted data), **dirty write** (overwriting uncommitted data),
       **non-repeatable read** (re-read gives a different value), **phantom read** (re-run gives new
       rows), **lost update** (two read-modify-writes, one overwrites), **read skew** (two reads see
       mutually inconsistent states), **write skew** (both read an overlapping set, both write
       disjoint rows, jointly violating an invariant), **serialization anomaly** (the result matches
       no serial order). `[NUM]` `[PROVE]`
1.24.2 The standard's table: RU allows all three named anomalies; RC forbids dirty reads; RR forbids
       non-repeatable reads; SERIALIZABLE forbids phantoms. Then the correction that matters —
       **the standard defines levels by the anomalies they forbid, which was a mistake**, because it
       described 2PL implementations and left snapshot isolation unclassifiable. `[SOURCE]`
       `[PROVE]` `[TRAP]`
1.24.3 **PostgreSQL 18's actual table, quoted**: Read Uncommitted behaves as Read Committed; Repeatable
       Read does *not* allow phantom reads ("allowed, but not in PG"); only Serializable forbids the
       serialization anomaly. So the textbook answer "RR allows phantoms" is wrong for the database
       in front of you. `[SOURCE]` `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
1.24.4 Defaults, memorised: **PostgreSQL = READ COMMITTED**, **Oracle = READ COMMITTED**,
       **MySQL InnoDB = REPEATABLE READ**, **SQL Server = READ COMMITTED (lock-based, or snapshot
       with `READ_COMMITTED_SNAPSHOT ON`)**. Your code must defend against your default.
       `[NUM]` `[MYSQL]`
1.24.5 PostgreSQL internally has **three** implementations for four level names, and setting Read
       Uncommitted silently gives you Read Committed. `[SOURCE]` `[TRAP]`
1.24.6 READ COMMITTED semantics in detail: a **new snapshot per statement**, so two identical
       `SELECT`s in one transaction can differ; a `UPDATE` that finds a row concurrently modified
       re-evaluates its `WHERE` against the *new* version (the "EvalPlanQual" recheck), which can make
       an update apply to a row that no longer matches your original predicate. This is subtle and it
       is the level you are running in. `[PROVE]` `[TRAP]` `[SOURCE]`
1.24.7 REPEATABLE READ / snapshot isolation semantics: one snapshot taken at first statement, held for
       the transaction; a write conflict raises `ERROR: could not serialize access due to concurrent
       update` (SQLSTATE **40001**) rather than blocking-then-overwriting. So RR in PostgreSQL
       *already* requires retry logic — most people do not know this. `[DIAG]` `[NUM]`
       `[TRAP]`
1.24.8 SERIALIZABLE (SSI) semantics: snapshot isolation plus rw-antidependency tracking; conflicts
       abort with `ERROR: could not serialize access due to read/write dependencies among
       transactions`, hint "The transaction might succeed if retried". Predicate locks do not block.
       `[DIAG]` `[SOURCE]`
1.24.9 **Write skew, worked**: the on-call doctors example, and the QuizStakes version — two concurrent
       stake reservations each reading `CASH_AVAILABLE = 100` and each writing a different reservation
       row, jointly overdrawing. Show why RR permits it and SSI aborts one.
       `[PROVE]` `[SOURCE]` `[SQL]`
1.24.10 The documentation's own write-skew example (`SELECT SUM(value) ... class=1` / `class=2` then
        cross-inserting) as the minimal reproduction, quoted and explained. `[SOURCE]`
        `[RESEARCH]`
1.24.11 **Retry is mandatory, and the docs say so**: "it should abort the current transaction and
        retry the whole transaction from the beginning." Retrying only the failed statement is wrong,
        because the snapshot is the thing that must be re-taken. `[SOURCE]` `[PROVE]`
        `[TRAP]`
1.24.12 Read-only transactions never take a serialization failure, and `SERIALIZABLE READ ONLY
        DEFERRABLE` trades a wait for a guarantee of no abort. `[SOURCE]`
1.24.13 InnoDB's REPEATABLE READ: a consistent read view established at the first read, **but**
        locking reads (`SELECT ... FOR UPDATE/SHARE`, `UPDATE`, `DELETE`) read the *latest* committed
        version and take next-key locks. So InnoDB RR mixes snapshot and locking semantics in one
        transaction, which is why lost updates behave differently there. `[MYSQL]` `[PROVE]`
        `[TRAP]`
1.24.14 InnoDB's phantom prevention is by **gap locks**, not by snapshot, for locking reads — and
        `SERIALIZABLE` in InnoDB simply promotes every plain `SELECT` to `SELECT ... FOR SHARE`.
        That is a completely different mechanism from PostgreSQL SSI, with completely different
        failure modes (blocking and deadlocks rather than aborts). `[MYSQL]` `[PROVE]`
1.24.15 The isolation-level cost table the bible must give: what each level costs in aborts, in
        blocking, in bookkeeping memory, and in code complexity — plus the honest note that SSI's
        overhead is proportional to the read set. `[NUM]` `[PROVE]`
1.24.16 The selection procedure: default RC and defend the specific invariant with an atomic
        statement, a constraint, or an explicit lock; escalate to RR when a transaction reads the
        same data twice; escalate to SERIALIZABLE when the invariant spans rows you did not write,
        and only if you have retry logic. `[PROVE]`
1.24.17 `SET TRANSACTION ISOLATION LEVEL` vs `default_transaction_isolation` (default
        `read committed`) vs JDBC's `Connection.setTransactionIsolation(...)` vs
        `@Transactional(isolation = ...)` — four places, and the pooled-connection hazard that the
        setting leaks to the next borrower if the pool does not reset it. HikariCP's
        `transactionIsolation` property exists for this. `[GUC]` `[JDBC]` `[TRAP]`
        `[X-REF 08]`
1.24.18 The QuizStakes isolation decision, stated: the ledger runs READ COMMITTED and defends money
        with a version column on `position` (Appendix C.2) plus an atomic conditional `UPDATE` — not
        with SERIALIZABLE — because a 3,400/sec settlement burst cannot absorb SSI's abort rate. Say
        what that choice costs and what test proves it is safe. `[SOURCE]` `[NUM]` `[PROVE]`

*(18 leaves)*

## §1.25 Locking — the user-visible surface

1.25.1 The two lock families to keep distinct: **row-level** locks taken by DML and `SELECT ... FOR
       ...`, and **table-level** locks taken by DDL and by DML implicitly. Confusing them is why
       people think a `SELECT` can block an `ALTER`. (It can — via the lock queue, §2.25.)
1.25.2 The row-lock modes in PostgreSQL, weakest to strongest, with what each conflicts with:
       `FOR KEY SHARE`, `FOR SHARE`, `FOR NO KEY UPDATE`, `FOR UPDATE`. An `UPDATE` that does not
       touch a unique key takes `FOR NO KEY UPDATE`; an FK check takes `FOR KEY SHARE`. This is why
       an FK check no longer blocks a plain `UPDATE` (since 9.3). `[NUM]` `[VERSION-TRAP]`
1.25.3 The eight table-lock modes and the conflict matrix: `ACCESS SHARE`, `ROW SHARE`,
       `ROW EXCLUSIVE`, `SHARE UPDATE EXCLUSIVE`, `SHARE`, `SHARE ROW EXCLUSIVE`, `EXCLUSIVE`,
       `ACCESS EXCLUSIVE` — with which statement takes which. The write pass must reproduce the
       matrix, because §2.25 is unreadable without it. `[SOURCE]` `[NUM]`
1.25.4 `LOCK TABLE ... IN mode MODE [NOWAIT]` as the explicit form, and why you almost never need it.
1.25.5 `NOWAIT` (error 55P03 instead of waiting) and `SKIP LOCKED` (silently skip locked rows) as the
       two escape hatches, and the semantic difference: `NOWAIT` fails, `SKIP LOCKED` returns fewer
       rows. `[DIAG]` `[NUM]`
1.25.6 `SELECT ... FOR UPDATE OF table` in a join, and the fact that `FOR UPDATE` locks *all* rows the
       query returns from the lockable tables, including rows you only joined for display.
       `[TRAP]`
1.25.7 Advisory locks: `pg_advisory_lock(key)` / `pg_try_advisory_lock` / `pg_advisory_xact_lock` /
       `pg_advisory_unlock_all`, session vs transaction scope, and the 64-bit or two-32-bit key
       space. This is the database-native distributed lock — the honest answer to "only one
       `PaymentRun` may be open" (§13.4, invariant #14) when you do not want a separate coordinator.
       `[SQL]` `[SOURCE]` `[PROVE]`
1.25.8 **Trap: a session-scoped advisory lock on a pooled connection is a leak.** The connection goes
       back to the pool still holding it; the next borrower cannot take it and the holder never
       releases. Use `pg_advisory_xact_lock`, always, from a pooled application.
       `[TRAP]` `[X-REF 08]`
1.25.9 MySQL's equivalents: `SELECT ... FOR UPDATE` / `FOR SHARE` (`LOCK IN SHARE MODE` pre-8.0),
       `NOWAIT`/`SKIP LOCKED` (8.0+), table locks via `LOCK TABLES`, metadata locks (MDL) which are
       the real reason DDL blocks, and `GET_LOCK()`/`RELEASE_LOCK()` as the advisory pair.
       `[MYSQL]` `[VERSION-TRAP]`
1.25.10 Optimistic vs pessimistic as a *choice*, not a feature: pessimistic (`FOR UPDATE`) serialises
        and cannot fail late; optimistic (a `version` column and a conditional `UPDATE`) never
        blocks and can fail at write time. QuizStakes §15.1 names both and where each is used:
        pessimistic on positions during a reservation ("correct, and it serialises every stake for
        that client"), optimistic version-stamping on `Application` and `ReviewCase`.
        `[SOURCE]` `[PROVE]`
1.25.11 Lock granularity and escalation: PostgreSQL never escalates row locks to table locks (row
        locks live in the tuple header, so there is no per-row memory to run out of); SQL Server and
        DB2 do escalate. Naming this kills a common cross-engine misconception. `[TRAP]`
        `[PROVE]`
1.25.12 How to *see* locks: `pg_locks` joined to `pg_stat_activity`, the blocking-tree query with
        `pg_blocking_pids()`, `SHOW ENGINE INNODB STATUS`, and
        `performance_schema.data_locks`/`data_lock_waits`. Show real output.
        `[DIAG]` `[MYSQL]` `[SQL]`
1.25.13 Deadlock at the user level: what the error looks like (SQLSTATE **40P01**,
        `ERROR: deadlock detected`, with the `DETAIL` naming both processes and both statements), and
        that it is a **retryable** error by definition. `[DIAG]` `[NUM]`
1.25.14 The four deadlock preventions in order of effectiveness: consistent lock ordering (most
        deadlocks are "A then B" versus "B then A"), short transactions with no network I/O, a single
        atomic statement instead of read-then-write, and retry. The QuizStakes instance is exact:
        §15.1 "two concurrent movements acquiring cash and bonus positions in opposite order" — so
        every movement must acquire positions in a fixed order (e.g. by position type ordinal).
        `[SOURCE]` `[PROVE]`
1.25.15 `FOR UPDATE SKIP LOCKED` as a job queue, written out against `bankwithdrawal.transactions`:
        each worker claims a disjoint batch with no coordination, no double processing and no queue
        infrastructure. Then the honest limits (no priority ageing, no delayed retry without extra
        columns, `ORDER BY` + `SKIP LOCKED` re-sorting cost). `[SQL]` `[PROVE]` `[X-REF 14]`
1.25.16 What locking cannot do: it cannot protect a row that does not exist yet (that is a unique
        index or a gap lock), and it cannot make a non-transactional participant atomic (that is
        compensation). Both are QuizStakes failures if forgotten. `[PROVE]` `[TRAP]`

*(16 leaves)*

## §1.26 Indexes — the basics

1.26.1 What an index is: a separate, ordered, redundant data structure whose only purpose is to
       reduce the number of pages read. It changes no query result — which is why adding one is
       safe and why the planner is free to ignore it. `[PROVE]`
1.26.2 The `CREATE INDEX` surface: `UNIQUE`, `CONCURRENTLY`, `IF NOT EXISTS`, `USING method`,
       column list with `COLLATE`/`opclass`/`ASC|DESC`/`NULLS FIRST|LAST`, `INCLUDE (cols)`,
       `NULLS [NOT] DISTINCT`, `WITH (fillfactor, deduplicate_items, ...)`, `TABLESPACE`, and
       `WHERE predicate`. Every clause matters later. `[SQL]` `[NUM]`
1.26.3 B-tree structure at the level needed to reason: a balanced tree of fixed-size pages, internal
       nodes holding separator keys, leaves holding key → row pointer, leaves in a doubly-linked
       list. Height 3–4 for hundreds of millions of rows, so a lookup is 3–4 page reads.
       `[NUM]` `[PROVE]`
1.26.4 The fanout arithmetic that produces "3–4 levels", done explicitly: an 8 kB page, ~16 bytes per
       entry for a `bigint` key plus a 6-byte pointer plus overhead → several hundred entries per
       page → 300³ ≈ 27M and 300⁴ ≈ 8.1B, which covers the 7.2B-row `ledger_entry` table at four
       levels. The write pass must show this calculation, not assert the result.
       `[NUM]` `[PROVE]`
1.26.5 Why "B-tree" means B+ tree in every real database: only leaves hold data pointers, internal
       nodes are pure routing, and the leaf list makes range scans sequential. `[TRAP]`
       `[X-REF 01]`
1.26.6 What a B-tree can therefore serve: `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `IN`, `IS NULL`,
       `IS NOT NULL`, left-anchored `LIKE`, `ORDER BY`, `GROUP BY` (as sorted input), `MIN`/`MAX`
       (as a one-row scan), and uniqueness enforcement. `[SOURCE]`
1.26.7 What it cannot: leading-wildcard patterns, arbitrary function results, unrelated columns of a
       composite key without skip scan, and non-B-tree-ordered operators like `&&`.
1.26.8 Clustered vs non-clustered/secondary, stated as the fundamental PostgreSQL/InnoDB divergence:
       PostgreSQL has a **heap** plus independent indexes whose leaves hold a `ctid`; InnoDB stores
       the whole row in the **primary-key B-tree**, and every secondary index leaf holds the primary
       key, so a secondary lookup is two B-tree descents. `[MYSQL]` `[PROVE]` `[NUM]`
1.26.9 The consequences of InnoDB's clustered design that follow immediately: PK order is physical
       order (so a random UUID PK fragments the table itself, not just an index), a wide PK inflates
       *every* secondary index, and index-only scans on a secondary index come free for PK columns.
       `[MYSQL]` `[NUM]` `[PROVE]`
1.26.10 PostgreSQL's `CLUSTER table USING index` as a one-off physical reorder that is not maintained,
        and `pg_stats.correlation` as the measure of how ordered a column currently is.
        `[NUM]` `[TRAP]`
1.26.11 Composite indexes and the **leftmost prefix rule**: `INDEX (a, b, c)` sorts by a, then b,
        then c, and can serve `a`, `(a,b)`, `(a,b,c)` and `a = ? AND b > ?`. Prove why `b` alone
        cannot be seeked. `[PROVE]` `[SQL]`
1.26.12 **The PG 18 correction**: B-tree *skip scan* lets a multicolumn index be used when the leading
        column is unconstrained, by iterating its distinct values — so "useless without the leading
        column" becomes "usable, at a cost proportional to the leading column's cardinality". State
        both the old rule and the new caveat. `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]`
1.26.13 Column-ordering rule: **equality columns first, then the range or sort column**. Once a range
        predicate is used, later columns can only filter, not seek. So
        `WHERE client_id = ? AND posted_at > ? ORDER BY posted_at` wants `(client_id, posted_at)`.
        `[PROVE]` `[SQL]`
1.26.14 **Trap: "most selective column first."** Winand's *Myth Directory* lists this explicitly as a
        myth. Selectivity does not decide order; the *predicate shape* does — equality before range,
        and the `ORDER BY` requirement last. `[SOURCE]` `[TRAP]` `[PROVE]`
1.26.15 Covering indexes and index-only scans: if the index contains every column the query needs,
        the heap is never touched. `INCLUDE (cols)` adds payload columns to the leaf without making
        them part of the key (so they do not affect ordering or uniqueness). `[SQL]` `[PROVE]`
1.26.16 The PostgreSQL caveat that makes index-only scans conditional: the visibility map must show
        the page as all-visible, otherwise the heap is consulted anyway. So an index-only scan
        degrades on a heavily-updated table until vacuum runs. InnoDB has no such caveat.
        `[PROVE]` `[TRAP]` `[MYSQL]`
1.26.17 Partial indexes: `CREATE INDEX ... ON fundsledger.reservation (expires_at) WHERE state =
        'AWAITING_SETTLEMENT'` — a tiny index over the only rows the orphan sweep cares about. The
        predicate must be *implied* by the query's `WHERE` for the planner to use it.
        `[SQL]` `[PROVE]` `[SOURCE]`
1.26.18 Expression indexes: `CREATE INDEX ON accountopening.application (lower(email))`, usable only
        when the query uses the identical expression, and requiring the function to be `IMMUTABLE`.
        `[SQL]` `[TRAP]`
1.26.19 Unique indexes vs unique constraints: a constraint is implemented *by* an index, but only a
        constraint can be an FK target and only an index can be partial. So a partial unique index is
        the way to say "at most one open `PaymentRun`". `[SQL]` `[PROVE]` `[SOURCE]`
1.26.20 The other access methods named with their one-line use: **hash** (equality only, WAL-logged
        since PG 10), **GIN** (arrays, JSONB, full-text, trigram — many keys per row),
        **GiST** (geometric, ranges, nearest-neighbour `ORDER BY x <-> y`),
        **SP-GiST** (quadtrees, radix trees, non-balanced), **BRIN** (block-range min/max summaries,
        tiny, for naturally-ordered append-only data), plus the `bloom` extension.
        `[SOURCE]` `[RESEARCH]`
1.26.21 **BRIN is the right answer for the QuizStakes ledger's time column**: 7.2B append-only rows
        where `posted_at` correlates almost perfectly with physical order. Show the size comparison
        against a B-tree on the same column and the query shapes it does and does not serve.
        `[NUM]` `[PROVE]` `[SOURCE]`
1.26.22 Multicolumn support per access method: B-tree up to 32 columns, GIN and GiST yes, hash and
        BRIN limited — plus `btree_gin`/`btree_gist` for mixing a scalar equality with a GIN/GiST
        operator in one index. `[NUM]` `[RESEARCH]`
1.26.23 The cost of an index, stated so it is never forgotten: every `INSERT` and every `UPDATE` of an
        indexed column must maintain it, it consumes buffer cache that the table wanted, it inflates
        WAL, and it prevents HOT updates (§3.4). At 19.8M ledger inserts/day, each extra index is
        19.8M extra index insertions/day. `[NUM]` `[PROVE]`
1.26.24 The index inventory rule: index FK child columns, index high-selectivity `WHERE`/`JOIN`/
        `ORDER BY` columns, and delete everything else — with `pg_stat_user_indexes.idx_scan = 0` as
        the evidence and `pg_index.indisvalid`/`pgstattuple` for health.
        `[SQL]` `[DIAG]`
1.26.25 Duplicate and redundant indexes: `(a)` is redundant given `(a, b)`; `(b, a)` is not.
        The query that finds redundant indexes from `pg_index`. `[SQL]` `[PROVE]`
1.26.26 `REINDEX`, `REINDEX CONCURRENTLY` (PG 12+), and `DROP INDEX CONCURRENTLY` — plus the
        `INVALID` index left behind by a failed `CREATE INDEX CONCURRENTLY` that you must drop and
        retry. `[VERSION-TRAP]` `[DIAG]`

*(26 leaves)*

## §1.27 `EXPLAIN` — reading a plan

1.27.1 `EXPLAIN` gives the plan without running it; **`EXPLAIN ANALYZE` runs the query** (including
       the write, unless you wrap it in a transaction you roll back) and reports actual times and row
       counts. Saying this out loud has saved production tables. `[TRAP]`
1.27.2 The option list: `ANALYZE`, `VERBOSE`, `COSTS`, `SETTINGS`, `GENERIC_PLAN` (PG 16+),
       `BUFFERS`, `WAL`, `TIMING`, `SUMMARY`, `MEMORY` (PG 17+), `SERIALIZE` (PG 17+),
       `FORMAT {TEXT|XML|JSON|YAML}`. `[SQL]` `[VERSION-TRAP]`
1.27.3 **`BUFFERS` is on by default with `ANALYZE` from PG 18** — so the ubiquitous advice "always add
       BUFFERS" is now a no-op, and older plans in blog posts lack the numbers you need.
       `[RESEARCH]` `[VERSION-TRAP]` `[NUM]`
1.27.4 How to read the tree: children before parents, indentation = nesting, each node's cost
       *includes* its children, and `(cost=startup..total rows=n width=b)` means exactly what it
       says — startup cost is what you pay before the first row, which is why `LIMIT` cares.
       `[PROVE]` `[PLAN]`
1.27.5 `actual time=first..total rows=n loops=k`, and the crucial arithmetic: **per-loop values are
       averages; multiply by `loops` to get the real total.** Missing this makes a nested loop look
       cheap. `[NUM]` `[PROVE]` `[TRAP]`
1.27.6 **What to look at first: `rows=` estimated versus `actual rows=`.** A 100× or 1000×
       discrepancy means the planner is working from bad information, and *that* is the root cause —
       not the node type. Then look at where the discrepancy first appears in the tree, because
       everything above it is downstream of the mistake. `[PROVE]` `[PLAN]`
1.27.7 The scan nodes, cheapest first, with when each is correct: `Index Only Scan`, `Index Scan`,
       `Bitmap Index Scan` + `Bitmap Heap Scan` (with `recheck` and `lossy` explained),
       `Seq Scan`, `Tid Scan`, `Function Scan`, `Values Scan`, `Subquery Scan`, `CTE Scan`,
       `WorkTable Scan`, `Sample Scan`, `Foreign Scan`. `[PLAN]`
1.27.8 The join nodes and their preconditions: `Nested Loop` (indexed inner side, small outer),
       `Hash Join` (build the smaller side into a hash table; equality only),
       `Merge Join` (both inputs sorted), plus the `Semi`/`Anti`/`Left`/`Full` qualifiers and
       `Memoize` (PG 14+) as the nested-loop result cache. `[PLAN]` `[VERSION-TRAP]`
1.27.9 The other nodes worth naming: `Sort` (with `Sort Method: quicksort | top-N heapsort |
       external merge Disk: nnnkB`), `Incremental Sort`, `HashAggregate`/`GroupAggregate`/
       `MixedAggregate`, `WindowAgg`, `Unique`, `Limit`, `Append`/`MergeAppend`, `Materialize`,
       `Gather`/`Gather Merge`, `Result`, `ProjectSet`, `LockRows`, `ModifyTable`,
       `SetOp`, `Recursive Union`, `Group`. `[PLAN]`
1.27.10 The lines that name a problem directly: `Rows Removed by Filter` (the index is not selective
        enough, or the predicate is a filter not an access predicate), `Rows Removed by Join Filter`,
        `Heap Fetches` (an index-only scan that is not, §1.26.16), `Sort Method: external merge`
        (raise `work_mem`), `Buffers: shared read=` vs `hit=` (cache miss volume), `read=` on a
        temp file (spill), `Filter` vs `Index Cond` (§1.11.8). `[PLAN]` `[DIAG]`
1.27.11 `EXPLAIN (ANALYZE, BUFFERS)` unit arithmetic: buffers are counted in 8 kB blocks, so
        `shared read=131072` is 1 GB of I/O. Converting to bytes is what turns a plan into a
        capacity statement. `[NUM]` `[PROVE]`
1.27.12 `EXPLAIN (GENERIC_PLAN)` for a parameterised statement — how you see the plan your JDBC
        prepared statement will actually get, without values. `[JDBC]` `[VERSION-TRAP]`
1.27.13 `auto_explain` (`auto_explain.log_min_duration`, `log_analyze`, `log_buffers`,
        `log_nested_statements`, `sample_rate`) as the way to capture plans for queries you cannot
        reproduce — the only realistic tool for a 30 ms-budget path. `[GUC]` `[DIAG]`
1.27.14 MySQL's equivalents: `EXPLAIN`, `EXPLAIN FORMAT=JSON`, `EXPLAIN ANALYZE` (8.0.18+),
        `EXPLAIN FORMAT=TREE`, the `type` column values (`system`, `const`, `eq_ref`, `ref`,
        `fulltext`, `ref_or_null`, `index_merge`, `unique_subquery`, `index_subquery`, `range`,
        `index`, `ALL`) ranked, and the `Extra` strings that matter (`Using index`,
        `Using index condition`, `Using where`, `Using filesort`, `Using temporary`).
        `[MYSQL]` `[NUM]` `[PLAN]` `[VERSION-TRAP]`
1.27.15 Plan visualisation tools and what they add: `explain.depesz.com`, `explain.dalibo.com`,
        pgMustard, PEV2 — and the one thing they all do that reading text does not: highlight where
        the estimate first diverges. `[RESEARCH]`
1.27.16 Reading a plan is a *procedure*, not an art. The write pass must give it as an ordered
        checklist: (1) find the node where estimate and actual first diverge; (2) check whether that
        node's input is a bad statistic, a correlated predicate, or an unestimable expression;
        (3) only then look at node types; (4) check `Buffers` for whether the cost is I/O or CPU;
        (5) check for spills; (6) check `loops` multiplication. `[FLOW]` `[PROVE]`

*(16 leaves)*

## §1.28 The Java client's view — JDBC at the SQL layer

This section owns the *SQL-layer* behaviour of the driver. Repository derivation, the persistence
context and `@Transactional`'s interceptor live in `08-spring-data-jpa.md` and `07-spring-core.md`.
`[X-REF 08]` `[X-REF 07]`

1.28.1 What a JDBC `Connection` actually is: a TCP socket plus a server-side session. In PostgreSQL
       that session is an **OS process** forked at connect time (~10–100 ms including auth); in MySQL
       it is a thread. This single fact drives every pooling decision. `[NUM]` `[PROVE]`
1.28.2 `Statement` vs `PreparedStatement` vs `CallableStatement`, and the two independent things
       "prepared" can mean: client-side parameter binding (always) and a **server-side named
       prepared statement** (only sometimes). `[JDBC]` `[TRAP]`
1.28.3 **pgJDBC's `prepareThreshold` defaults to 5**: the driver executes a statement with the
       unnamed/one-shot protocol until the same `PreparedStatement` SQL has run five times, then
       issues a server-side `Prepare` and reuses it. `0` disables server-side prepares entirely.
       `[JDBC]` `[NUM]` `[RESEARCH]` `[SOURCE]`
1.28.4 `preparedStatementCacheQueries` (default **256**) and `preparedStatementCacheSizeMiB`
       (default **5**) bound the per-connection cache; exceeding them evicts LRU, so a service with
       400 distinct queries silently loses server-side preparation. `[JDBC]` `[NUM]`
       `[RESEARCH]`
1.28.5 A batching `PreparedStatement` server-prepares immediately once it holds at least two batched
       statements, rather than waiting for the threshold. `[JDBC]` `[RESEARCH]`
1.28.6 The consequence that surprises people: a server-side prepared statement gets a **generic
       plan** after five executions (§3.10), so query performance can *change* on the sixth
       execution. This is a real production shape and `EXPLAIN (GENERIC_PLAN)` is how you see it
       coming. `[PROVE]` `[TRAP]` `[JDBC]`
1.28.7 Server-side prepares are per-connection, so they interact badly with a transaction-pooling
       proxy: PgBouncer only supports protocol-level named prepared statements from **1.21+** with
       `max_prepared_statements` set (default **200**). Before that, `prepareThreshold=0` was
       mandatory. `[RESEARCH]` `[TRAP]` `[NUM]`
1.28.8 `autoCommit`: JDBC's default is `true`, so every statement is its own transaction and its own
       commit `fsync`. Turning it off is what starts a transaction; leaving it on inside a loop of
       10,000 inserts costs 10,000 commits. `[JDBC]` `[NUM]` `[PROVE]`
1.28.9 `setFetchSize` semantics per driver, restated as a data-loss-of-heap hazard (§1.18.9), with
       the exact preconditions on each side. `[JDBC]` `[TRAP]`
1.28.10 Batching: `addBatch`/`executeBatch`, `executeLargeBatch`, the returned update counts and
        `Statement.SUCCESS_NO_INFO`, and `BatchUpdateException`. What a batch does *not* do by
        itself: it is still N statements on the wire unless the driver rewrites them. `[JDBC]`
        `[PROVE]`
1.28.11 **`reWriteBatchedInserts=true`** in pgJDBC turns N single-row `INSERT`s into one multi-row
        `INSERT`, which is the property that makes batching actually fast; MySQL's equivalent is
        `rewriteBatchedStatements=true`. Both are **off by default**. `[JDBC]` `[NUM]`
        `[RESEARCH]` `[TRAP]`
1.28.12 `Connection.setReadOnly(true)` maps to `SET TRANSACTION READ ONLY` (and is what a
        read-replica-routing `DataSource` keys off) — and is *not* a performance hint on its own.
        `[JDBC]` `[X-REF 08]`
1.28.13 Timeouts, all four, and which layer each lives at: `Statement.setQueryTimeout` (driver-side
        cancel), `socketTimeout` (connection property, kills the socket), server `statement_timeout`
        (authoritative, survives a dead client), and pool `connectionTimeout` (waiting for a
        connection, not for the query). A service without the third can leave a query running after
        the client is gone. `[JDBC]` `[GUC]` `[PROVE]` `[TRAP]`
1.28.14 Cancellation: `Statement.cancel()` opens a *second* connection to send the cancel request,
        PG 18's wire protocol 3.2 widens the cancel key from 64 to 256 bits, and a cancel is
        advisory — the server checks for it at interrupt points. `[JDBC]` `[RESEARCH]`
        `[NUM]`
1.28.15 Connection properties worth knowing by name: `ApplicationName` (shows in
        `pg_stat_activity` — set it, always), `options=-c statement_timeout=...`,
        `assumeMinServerVersion`, `binaryTransfer`, `stringtype`, `targetServerType`
        (`primary`/`preferSecondary` for driver-level replica routing), `loadBalanceHosts`,
        `sslmode`, `tcpKeepAlive`, `loggerLevel`. `[JDBC]` `[DIAG]`
1.28.16 `LISTEN`/`NOTIFY` from Java: `PGConnection.getNotifications`, the payload limit
        (**8000 bytes**), the fact that notifications are delivered on commit and are *not* durable —
        so it is a cache-invalidation signal, never a queue. `[JDBC]` `[NUM]`
        `[X-REF 15]` `[TRAP]`
1.28.17 `ResultSet` types and concurrency (`TYPE_FORWARD_ONLY` vs scrollable, `CONCUR_READ_ONLY` vs
        updatable) and why only forward-only read-only is worth using. `[JDBC]`
1.28.18 Getting the generated key: `RETURNING` + `executeQuery` on PostgreSQL beats
        `getGeneratedKeys` semantics-wise, because `RETURNING` can return computed and defaulted
        columns too. `[JDBC]` `[SQL]`
1.28.19 What to log and how: `pgJDBC` logging vs `datasource-proxy`/`p6spy` for statement capture,
        and the server-side alternatives (`log_statement`, `log_min_duration_statement`) which see
        the *real* SQL including the driver's own round trips. `[DIAG]` `[X-REF 20]`
1.28.20 R2DBC in one paragraph: the same SQL, a different (non-blocking) client contract, no
        `ThreadLocal`-bound transaction, and therefore no `@Transactional` as you know it. Named so
        the reader can place it. `[X-REF 04]`

*(20 leaves)*

## §1.29 Connections, sessions and server-side resources

1.29.1 The session-scoped things a pooled connection carries between borrowers, each of which is a
       leak if not reset: `SET` parameters, `search_path`, isolation level, prepared statements,
       temp tables, advisory locks, cursors `WITH HOLD`, and `SET ROLE`. HikariCP's
       `connectionInitSql` and the pool's own reset behaviour are the mitigation.
       `[TRAP]` `[PROVE]`
1.29.2 `max_connections` (PostgreSQL default **100**) as a hard cap, `superuser_reserved_connections`
       (**3**) and `reserved_connections` (PG 16+), and SQLSTATE **53300**
       `too many clients already`. `[GUC]` `[NUM]` `[DIAG]`
1.29.3 Why raising `max_connections` is not the fix: each PostgreSQL backend is a process with its
       own `work_mem` allowance, its own catalog caches (several MB) and a slot in every snapshot
       computation, so connection count has a super-linear cost. `[PROVE]` `[NUM]`
1.29.4 `work_mem` (default **4MB**) is **per sort/hash node per parallel worker**, not per query — so
       a query with three sorts and four workers can use 12× `work_mem`. This is the single most
       misunderstood memory parameter. `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
1.29.5 `hash_mem_multiplier` (default **2.0**), `maintenance_work_mem` (**64MB**),
       `autovacuum_work_mem` (**-1**), `temp_buffers` (**8MB**), `shared_buffers` (**128MB** default,
       25% of RAM as the usual starting point), `effective_cache_size` (**4GB**), and
       `temp_file_limit` (**-1**). `[GUC]` `[NUM]`
1.29.6 The memory arithmetic for a QuizStakes ledger instance, worked: `shared_buffers` +
       (`max_connections` × per-backend overhead) + (concurrent sorts × `work_mem`) must fit inside
       the container limit, and the OS page cache wants the rest. Show the sum for a 3-instance
       ledger fleet. `[NUM]` `[PROVE]` `[X-REF 19]`
1.29.7 `pg_stat_activity` as the session inventory: `state` (`active`, `idle`,
       `idle in transaction`, `idle in transaction (aborted)`, `fastpath function call`, `disabled`),
       `wait_event_type`/`wait_event`, `backend_xid`/`backend_xmin`, `query_start`,
       `xact_start`, `state_change`, `client_addr`, `application_name`. `[SQL]` `[DIAG]`
1.29.8 **`idle in transaction` is the most dangerous state in the view**: it holds a snapshot (so
       vacuum cannot advance), holds any locks taken, and holds a connection.
       `idle_in_transaction_session_timeout` exists for exactly this. `[PROVE]` `[TRAP]`
1.29.9 The wait-event taxonomy, named because it is how you attribute slowness: **LWLock**, **Lock**,
       **IO**, **IPC**, **Client**, **Timeout**, **BufferPin**, **Extension**, **Activity** — plus
       `pg_wait_events` (PG 17+) as the catalog of every event name. Persistent `LWLock` waits mean a
       shared-memory hot spot, not a slow query. `[SOURCE]` `[RESEARCH]` `[DIAG]`
1.29.10 `pg_terminate_backend` vs `pg_cancel_backend`, and why terminating a backend in the middle of
        a transaction is safe (the transaction aborts and WAL undoes nothing, because nothing was
        committed). `[SQL]` `[PROVE]`
1.29.11 MySQL's contrast: `max_connections` (default **151**), thread-per-connection with an optional
        thread pool, `SHOW PROCESSLIST` / `performance_schema.threads`, `wait_timeout`
        (**28800 s**) and `interactive_timeout`, `KILL QUERY` vs `KILL CONNECTION`.
        `[MYSQL]` `[NUM]`
1.29.12 The pooling section proper is §2.22; this section is only about what a *session* is and what
        it costs.

*(12 leaves)*

## §1.30 Privileges, roles and security at the SQL layer

1.30.1 The role model: roles are both users and groups (`LOGIN` attribute distinguishes them),
       `GRANT role TO role` for membership, `SET ROLE`, `CURRENT_USER` vs `SESSION_USER`, and role
       attributes `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, `BYPASSRLS`, `INHERIT`,
       `CONNECTION LIMIT`, `VALID UNTIL`. `[SQL]`
1.30.2 The privilege set per object type: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`,
       `REFERENCES`, `TRIGGER` on tables; column-level `SELECT`/`UPDATE`; `USAGE` on schemas,
       sequences and types; `EXECUTE` on routines; `CONNECT`/`TEMPORARY`/`CREATE` on databases;
       `MAINTAIN` (PG 17+). `[NUM]` `[VERSION-TRAP]`
1.30.3 `GRANT`/`REVOKE`, `WITH GRANT OPTION`, `ALL PRIVILEGES`, `PUBLIC` as the implicit
       everyone-role, and `ALTER DEFAULT PRIVILEGES` as the only way to make grants apply to objects
       created *later* — the omission that causes "the new table is not readable by the app user".
       `[TRAP]` `[SQL]`
1.30.4 The three-role pattern the bible should recommend: an owner role that owns the schema and runs
       migrations, an application role with DML only, and a read-only role for analytics — plus the
       QuizStakes reason it matters (§7.2: `PersonalDetails` and `FundsLedger` have their own
       instances with "different credentials"). `[SOURCE]`
1.30.5 **Never connect as a superuser from an application.** The wiki-level rule, plus what a
       superuser bypasses (RLS, permissions, `security_barrier`) and PG 18's `md5` deprecation
       warnings (`md5_password_warnings`, default on) pushing everyone to `scram-sha-256`.
       `[SOURCE]` `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]`
1.30.6 Row-level security: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`,
       `CREATE POLICY name ON t FOR {ALL|SELECT|INSERT|UPDATE|DELETE} TO role USING (read_predicate)
       WITH CHECK (write_predicate)`, `PERMISSIVE` vs `RESTRICTIVE`, and the fact that the table owner
       bypasses RLS unless `FORCE`d. `[SQL]` `[NUM]`
1.30.7 RLS as multi-tenancy: `USING (client_id = current_setting('app.client_id')::uuid)` with the
       setting established per transaction via `SET LOCAL`. The pooled-connection hazard is the same
       as §1.29.1 — `SET` not `SET LOCAL` leaks the tenant to the next borrower, which is a data
       breach, not a bug. `[TRAP]` `[PROVE]` `[X-REF 08]`
1.30.8 RLS costs: the policy predicate is added to every query and *is* subject to planning, so a
       non-indexable policy makes every query a seq scan; and a policy expression that calls a
       non-`LEAKPROOF` function can leak rows through error messages. `[PROVE]` `[TRAP]`
1.30.9 **The QuizStakes position on RLS, stated honestly**: it is a good fit for per-client isolation
       inside one service's schema and a *bad* substitute for `ClientRestrictions`, because §9 is a
       policy decision point queried synchronously per action, not a row filter — restrictions are
       "read live, every time" (§9.4) and are never a query predicate. `[SOURCE]`
       `[PROVE]`
1.30.10 SQL injection at the SQL layer: what a parameterised statement actually does (the value never
        enters the parse tree), why string concatenation with escaping is not equivalent, and the
        three places parameterisation is impossible — identifiers, `ORDER BY` column, and `LIMIT` in
        some drivers — with the allow-list/`quote_ident`/`format(%I)` answers.
        `[PROVE]` `[SQL]` `[X-REF 13]`
1.30.11 Second-order injection, injection through a dynamic PL/pgSQL `EXECUTE`, and
        `SECURITY DEFINER` functions with a mutable `search_path` as a privilege-escalation vector
        (`SET search_path` on the function is the fix). `[TRAP]` `[X-REF 13]`
1.30.12 Encryption boundaries: TLS in transit (`sslmode=verify-full`), at rest (filesystem/volume,
        not a database feature in core PostgreSQL), `pgcrypto` for column-level encryption and the
        reason it kills indexing and searching, and where a tokenised reference beats encryption —
        which is exactly QuizStakes' card handling (§15.7: "card details never touch our systems; we
        hold a reference"). `[SOURCE]` `[X-REF 13]`
1.30.13 Auditing: `pgaudit`, `log_statement = 'ddl'|'mod'|'all'`, MySQL's audit plugin, and the
        application-level alternative (`application_history` as an append-only table) — with the
        QuizStakes requirement that "every override records who, when, which role, and why"
        (§15.7). `[SOURCE]` `[GUC]`
1.30.14 Data minimisation and column privileges: the operator queue "needs to know a case exists, not
        the client's full DoB" (§15.7), which is a column-level `GRANT` and a narrow view, not a
        policy discussion. `[SOURCE]`
1.30.15 Right-to-erasure vs 7-year retention as a genuinely unresolvable conflict (§15.3, §15.7), and
        the mechanisms that partially address it: crypto-shredding a per-client key, tombstoning PII
        while retaining transaction records, and pseudonymisation. State plainly that the storage
        choice does not solve it. `[SOURCE]` `[X-REF 13]`

*(15 leaves)*

## §1.31 The catalog and introspection

1.31.1 `pg_catalog` vs `information_schema`: the former is PostgreSQL's real metadata (fast, complete,
       non-portable), the latter is the SQL-standard view layer (portable, incomplete, slower).
       `[TRAP]`
1.31.2 The catalog tables you will actually use: `pg_class` (relations, with `relpages`, `reltuples`,
       `relkind`, `relfrozenxid`), `pg_attribute`, `pg_index` (`indisvalid`, `indisready`,
       `indpred`, `indexprs`), `pg_constraint`, `pg_namespace`, `pg_type`, `pg_proc`, `pg_depend`,
       `pg_stats`, `pg_statistic`, `pg_am`, `pg_operator`, `pg_partitioned_table`, `pg_inherits`.
       `[SOURCE]` `[SQL]`
1.31.3 The statistics views: `pg_stat_user_tables` (`n_live_tup`, `n_dead_tup`, `last_autovacuum`,
       `n_mod_since_analyze`, `seq_scan`, `idx_scan`), `pg_stat_user_indexes` (`idx_scan`,
       `idx_tup_read`, `idx_tup_fetch`), `pg_statio_*` (`heap_blks_hit`/`read`),
       `pg_stat_database` (`xact_commit`, `xact_rollback`, `blks_hit`, `deadlocks`, `temp_bytes`,
       `conflicts`), `pg_stat_bgwriter`/`pg_stat_checkpointer` (PG 17+), `pg_stat_wal`,
       `pg_stat_io` (PG 16+), `pg_stat_replication`, `pg_stat_progress_*`, `pg_aios` (PG 18).
       `[SOURCE]` `[RESEARCH]` `[VERSION-TRAP]`
1.31.4 Size functions: `pg_relation_size`, `pg_table_size`, `pg_indexes_size`,
       `pg_total_relation_size`, `pg_size_pretty`, `pg_column_size`, and the query that lists the
       ten largest relations with their index overhead. Run it against the ledger and show ~1.3 TB/year.
       `[SQL]` `[NUM]`
1.31.5 `pg_stat_statements`: what it aggregates (normalised `queryid`, `calls`, `total_exec_time`,
       `mean_exec_time`, `stddev_exec_time`, `rows`, `shared_blks_hit/read/dirtied/written`,
       `temp_blks_*`, `wal_records`/`wal_bytes`, `min/max_exec_time`, plan time columns from PG 13),
       `pg_stat_statements.max` (default **5000**), `pg_stat_statements_reset()`, and the fact that
       the extension itself can be an `LWLock` contention source. `[SOURCE]` `[RESEARCH]`
       `[NUM]`
1.31.6 The three queries that answer "what is wrong right now": top statements by `total_exec_time`,
       the current blocking tree from `pg_locks` + `pg_blocking_pids()`, and the longest-running
       transaction from `pg_stat_activity`. The write pass must ship all three, runnable.
       `[SQL]` `[DIAG]`
1.31.7 `psql` as a diagnostic tool: `\d+`, `\di+`, `\dt+`, `\df`, `\dp`, `\l+`, `\x auto`, `\timing`,
       `\watch`, `\gexec`, `\copy`, `\set ECHO_HIDDEN on` to see the catalog query behind any
       backslash command. `[DIAG]`
1.31.8 MySQL's contrast: `information_schema` (with the 8.0 rewrite onto the transactional data
       dictionary), `performance_schema` (`events_statements_summary_by_digest`, `data_locks`,
       `table_io_waits_summary_by_table`), `sys` schema helper views, `SHOW` commands, and
       `SHOW ENGINE INNODB STATUS` as the single most information-dense diagnostic in MySQL.
       `[MYSQL]` `[DIAG]`
1.31.9 `pgstattuple` / `pgstatindex` for real bloat measurement, `pg_buffercache` for what is
       actually cached, `amcheck` for index corruption, and PG 18's `gin_index_check()`.
       `[RESEARCH]` `[DIAG]`
1.31.10 Introspection as a build-time asset: a CI test that asserts the live schema matches the
        migration-generated snapshot (the SQL-layer counterpart of
        `08-spring-data-jpa.md`'s `ddl-auto=validate` drift test). `[X-REF 08]` `[X-REF 16]`

*(10 leaves)*

## §1.32 Dialect map — what differs and where it bites

1.32.1 The comparison table the bible must give, PostgreSQL vs MySQL/InnoDB row by row: storage
       (heap vs clustered), MVCC (in-heap versions vs undo log), default isolation (RC vs RR),
       phantom prevention (snapshot / SSI vs gap locks), DDL transactionality, sequence vs
       `AUTO_INCREMENT`, `ON CONFLICT` vs `ON DUPLICATE KEY UPDATE`, index types available,
       partial/expression index support (PostgreSQL only), `RETURNING` (PostgreSQL only),
       CTE materialisation, window-function `EXCLUDE`, `SKIP LOCKED` availability, replication model
       (WAL streaming vs binlog), and connection model (process vs thread).
       `[MYSQL]` `[NUM]`
1.32.2 The MySQL-only behaviours that silently change results: case-insensitive default collation,
       implicit type coercion (`'10 apples' = 10` is true with a warning),
       `ONLY_FULL_GROUP_BY` off in older configurations, zero dates (`0000-00-00`), and
       `INSERT IGNORE` swallowing truncation. Each is a correctness difference, not a syntax one.
       `[MYSQL]` `[TRAP]`
1.32.3 `sql_mode` as MySQL's behaviour switch: `STRICT_TRANS_TABLES`, `ONLY_FULL_GROUP_BY`,
       `NO_ZERO_DATE`, `NO_ENGINE_SUBSTITUTION`, `ERROR_FOR_DIVISION_BY_ZERO`, and what the 8.0
       default set contains. Two servers with different `sql_mode` are two different databases.
       `[MYSQL]` `[NUM]` `[TRAP]`
1.32.4 InnoDB configuration constants worth knowing: `innodb_buffer_pool_size`,
       `innodb_flush_log_at_trx_commit` (**1** = durable; 2 and 0 trade durability for throughput),
       `innodb_flush_method`, `innodb_log_file_size`/`innodb_redo_log_capacity`,
       `innodb_page_size` (**16 KB** default), `innodb_lock_wait_timeout` (**50 s**),
       `innodb_deadlock_detect`, `innodb_print_all_deadlocks`,
       `innodb_autoinc_lock_mode`, `transaction_isolation`. Note that MySQL 8.4 changed the defaults
       of `innodb_adaptive_hash_index`, `innodb_buffer_pool_instances`, `innodb_change_buffering`,
       `innodb_doublewrite_files`/`_pages`, `innodb_flush_method` and
       `innodb_io_capacity`/`_max`. `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
       `[VERSION-TRAP]`
1.32.5 MySQL 8.4 removals that break old runbooks: `mysql_upgrade`, `mysqlpump`,
       `INFORMATION_SCHEMA.TABLESPACES`, `AUTO_INCREMENT` on `FLOAT`/`DOUBLE`, and
       `LOW_PRIORITY` in `LOCK TABLES` (now a syntax error). `[MYSQL]` `[RESEARCH]`
       `[VERSION-TRAP]`
1.32.6 The other engines in one line each, so a design conversation can place them: Oracle
       (undo tablespaces, no NULL in indexes, `MINUS`), SQL Server (lock-based RC by default,
       `READ_COMMITTED_SNAPSHOT`, clustered indexes, `TOP`), SQLite (single-writer, WAL mode, type
       affinity), MariaDB's divergence from MySQL, Aurora's log-structured storage layer and the
       6-way quorum, CockroachDB/Spanner (serializable by default, interleaved ranges).
       `[X-REF 18]` `[X-REF 22]`
1.32.7 Writing portable SQL: what actually is portable (the core `SELECT`, joins, aggregates, window
       functions, CTEs) versus what never is (upsert, pagination, locking hints, JSON, sequences,
       type names, `LIMIT`), and the mature position — target one dialect, isolate the rest, and do
       not pretend a JPA dialect abstraction makes the differences go away. `[X-REF 08]`
1.32.8 The MySQL 9.7 LTS deltas relevant to this guide: hypergraph optimizer support for complex
       queries (a different join-ordering algorithm from the greedy one in 8.x), replication applier
       metrics and Group Replication flow-control statistics moving into Community Edition, and
       JSON duality views with DML. State that these are 2026-era and not present in 8.4.
       `[MYSQL]` `[RESEARCH]` `[VERSION-TRAP]`

*(8 leaves)*

---

**PART 1 total: 12+14+21+16+23+16+18+18+14+16+12+16+14+9+10+13+18+11+10+12+9+10+14+18+16+26+16+20+12+15+10+8 = 467 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

Ten tables the bible must contain exactly once, each referenced from everywhere else rather than
repeated.

2.1.1 **The master cost table**: for every access path and every operation — seq scan, index scan,
      index-only scan, bitmap scan, nested loop, hash join, merge join, sort, hash aggregate, group
      aggregate, window agg, insert, update (HOT and non-HOT), delete, unique-index check, FK check —
      give the cost in pages read and CPU terms, with **amortised versus worst case split out** and
      the condition that produces each. `[NUM]` `[PROVE]`
2.1.2 **The index-type selection table**: B-tree, hash, GIN, GiST, SP-GiST, BRIN, bloom × the query
      shapes (equality, range, sort, prefix, containment, similarity, nearest-neighbour, array
      membership, full-text), with size and maintenance cost per row. `[NUM]`
2.1.3 **The isolation-level table**: level × anomaly, for the *standard*, for PostgreSQL 18, and for
      InnoDB 8.4 — three columns, because they differ. `[MYSQL]` `[SOURCE]`
2.1.4 **The lock conflict matrix**: the eight PostgreSQL table modes against each other, plus the
      four row modes, plus InnoDB's S/X/IS/IX/gap/next-key/insert-intention matrix.
      `[MYSQL]` `[SOURCE]`
2.1.5 **The DDL cost table**: every `ALTER TABLE` sub-command × lock taken × scan/rewrite required ×
      whether it is safe on a 7.2B-row table. `[NUM]`
2.1.6 **The memory-footprint table with arithmetic shown**: an 8 kB page's usable space, the 24-byte
      heap tuple header, the line-pointer array, alignment padding, the null bitmap, and a worked
      byte count for one `ledger_entry` row against the stated ~180 bytes — proving whether the
      figure is plausible and how many rows fit per page. `[NUM]` `[PROVE]`
2.1.7 **The failure-mode table**: symptom → mechanism → first diagnostic → fix, for the twenty
      failures this guide teaches (slow query, wrong rows, deadlock, lock timeout, bloat, wraparound,
      replication lag, pool exhaustion, plan flip, spill to disk, OOM in the client, connection
      refused, hot partition, index unused, `idle in transaction`, duplicate insert, lost update,
      write skew, stale replica read, migration lock queue). `[DIAG]`
2.1.8 **The QuizStakes schema table**: every table this guide uses, its owning service, its schema,
      its row count and growth rate from Appendix A, its keys, and its indexes.
      `[SOURCE]` `[NUM]`
2.1.9 **The PostgreSQL ↔ MySQL translation table** for the constructs a Java engineer writes daily.
      `[MYSQL]`
2.1.10 **The parameter table**: every GUC and system variable named in this guide, with its default
       and the unit it is measured in — so the reader never has to trust a remembered number.
       `[GUC]` `[NUM]`

*(10 leaves)*

## §2.2 Index design as a procedure

2.2.1 The procedure, in order, so it is repeatable: (1) collect the actual query shapes from
      `pg_stat_statements`, not from the code; (2) for each, write the predicate as
      equality-set + range + sort; (3) derive the candidate index; (4) merge candidates that share a
      prefix; (5) check for redundancy; (6) measure with `EXPLAIN (ANALYZE)` before and after;
      (7) delete the losers. `[FLOW]` `[PROVE]`
2.2.2 The three-part index formula stated as a rule: **equality columns (any order among themselves)
      → the range/sort column → included payload columns**. Everything else follows from it.
      `[PROVE]`
2.2.3 Choosing the order *among* equality columns: it does not affect the seek, but it does affect
      which *other* queries the index can also serve as a prefix, and it affects deduplication and
      compressibility. This is the only place selectivity legitimately enters the decision.
      `[PROVE]`
2.2.4 Designing for `ORDER BY ... LIMIT`: the index must supply the sort order for the pipeline to
      short-circuit, so the sort columns must follow the equality columns *in the same direction*.
      Show the plan with and without. `[PLAN]` `[PROVE]`
2.2.5 Designing for a join: index the *inner* side's join column, because that is the side a nested
      loop probes. Indexing the outer side does nothing for the join. `[PROVE]` `[TRAP]`
2.2.6 Designing for aggregation: `(group_key, agg_column)` lets a `GroupAggregate` read sorted input
      and can enable an index-only scan of the whole aggregate. `[PROVE]`
2.2.7 The QuizStakes index set, derived from the real access patterns rather than guessed, with the
      derivation shown for each: `ledger_entry(movement_id)` for the sum-to-zero check,
      `ledger_entry(position_ref, posted_at)` for statement queries and BRIN on `posted_at` for the
      archival sweep, `movement(idempotency_key) UNIQUE` for replay detection,
      `reservation(state, expires_at) WHERE state = 'AWAITING_SETTLEMENT'` for the orphan sweep,
      `cardpayments.transactions(account_id, created_at DESC)` for the client history screen,
      `bankwithdrawal.transactions(run_id)` for run item lookup,
      `bankwithdrawal.transactions(state) WHERE state = 'APPROVED'` for run collection,
      `restriction(client_id) WHERE state = 'ACTIVE'` for the 30 ms decision path,
      `application(status, updated_at)` for the operator queue. `[SQL]` `[SOURCE]`
      `[NUM]`
2.2.8 The write-cost budget: with the ledger at 19.8M inserts/day, state how many indexes the table
      can afford and show the arithmetic (index insertions/day, WAL bytes/day, buffer pages
      dirtied/day) rather than asserting a number. `[NUM]` `[PROVE]`
2.2.9 Index-only-scan design: which columns to promote into `INCLUDE`, and the size/benefit trade
      when the payload is wide. `[NUM]`
2.2.10 Over-indexing symptoms and the measurement that proves it: `idx_scan = 0` after a full
       business cycle, insert latency regression, and index size exceeding table size.
       `[DIAG]` `[SQL]`
2.2.11 `hypopg` for hypothetical indexes — testing an index's effect on a plan without building it,
       which on a 7.2B-row table is the difference between a five-minute experiment and a four-hour
       one. `[RESEARCH]` `[NUM]`
2.2.12 Index bloat and B-tree deduplication (PG 13+, `deduplicate_items`), the right-growing index
       special case, and why `REINDEX CONCURRENTLY` is now usually better than `pg_repack` for an
       index alone. `[VERSION-TRAP]` `[NUM]`
2.2.13 **Trap: "indexes can degenerate and need periodic rebuilds."** Winand's *Myth Directory*
       covers this — B-trees stay balanced by construction, and the real phenomena are bloat from
       dead entries and reduced correlation, both of which have specific measurements.
       `[SOURCE]` `[TRAP]` `[PROVE]`
2.2.14 Index-creation cost: `maintenance_work_mem`, parallel index build (`max_parallel_maintenance_
       workers`), and the runtime estimate for a B-tree over 7.2B rows — plus what
       `CONCURRENTLY` adds (two full passes plus a wait for all transactions older than the build).
       `[NUM]` `[GUC]` `[PROVE]`

*(14 leaves)*

## §2.3 Why the planner ignores your index

2.3.1 **Low selectivity.** Matching more than roughly 5–20% of the table makes a seq scan cheaper,
      because the index path costs one random page per row while a seq scan reads sequentially. Prove
      the crossover from `seq_page_cost = 1.0` and `random_page_cost = 4.0`, and state that this is
      correct behaviour, not a bug. `[NUM]` `[PROVE]` `[GUC]`
2.3.2 **A function or expression wrapping the column.** `WHERE lower(email) = ?`,
      `WHERE date(posted_at) = ?`, `WHERE amount::text = ?`. Fix: an expression index, a stored
      generated column, or a rewrite to a range. `[TRAP]` `[SQL]`
2.3.3 **A leading wildcard.** `LIKE '%DEP-301'` is unindexable by a B-tree; use `pg_trgm` GIN or a
      reversed-string expression index. `[TRAP]`
2.3.4 **An implicit type cast on the column side.** `WHERE varchar_col = 123` casts the column, not
      the literal; `WHERE bigint_col = '123'` casts the literal and is fine. The direction of the
      cast is the whole difference. `[PROVE]` `[TRAP]`
2.3.5 **Stale statistics.** The planner's row estimate comes from a sample; after a bulk load or a
      mass update the estimate can be orders out. `ANALYZE`, and check
      `pg_stat_user_tables.last_analyze` / `n_mod_since_analyze`. `[DIAG]`
2.3.6 **`OR` across columns.** One index cannot seek two disjuncts; the planner needs a `BitmapOr`
      of two indexes, or you rewrite as `UNION ALL`. `[PLAN]`
2.3.7 **A `NULL`-sensitive predicate the index cannot express**, and the partial-index fix.
2.3.8 **Collation mismatch** between the index and the comparison (§1.5.20) — including the
      after-upgrade case where the FTS/trgm indexes must be rebuilt because PG 18 changed the
      provider. `[RESEARCH]` `[TRAP]`
2.3.9 **The table is small.** Below a few hundred pages a seq scan is unbeatable, and the planner
      knowing this is why a unit-test-sized table never uses your index — the single most common
      false alarm. `[NUM]` `[TRAP]`
2.3.10 **A generic plan from a prepared statement** chose a different path than a custom plan would
       (§3.10). `EXPLAIN (GENERIC_PLAN)` proves it. `[JDBC]` `[PROVE]`
2.3.11 **Correlated predicates.** The planner multiplies selectivities assuming independence, so
       `WHERE rail = 'BANK' AND state = 'RETURNED'` (where `RETURNED` only exists on the bank rail,
       §7.3) is estimated far too low. Fix: `CREATE STATISTICS ... (dependencies, ndistinct, mcv)`.
       `[PROVE]` `[SQL]` `[SOURCE]`
2.3.12 **An unestimable expression**: a `VOLATILE` function, a JSONB containment, a `LIKE` with a
       parameter, a subquery in the predicate — all get hardcoded default selectivities
       (0.5 for a boolean function, 0.005 for an equality on an unknown, 0.0333 for a range).
       Naming the constants makes the misestimate predictable. `[NUM]` `[SOURCE]`
       `[RESEARCH]`
2.3.13 **The index exists but is `INVALID`** after a failed `CREATE INDEX CONCURRENTLY`. Check
       `pg_index.indisvalid`. `[DIAG]`
2.3.14 **The predicate does not imply the partial index's predicate**, so the planner cannot prove
       the index is applicable even though a human can see it. `[PROVE]` `[TRAP]`
2.3.15 **Skip scan changes the "no leading column" answer in PG 18** — so re-test rather than
       repeating the rule. `[RESEARCH]` `[VERSION-TRAP]`
2.3.16 The forcing tools and why they are diagnostics, not fixes: `enable_seqscan = off`,
       `enable_indexscan = off`, `SET LOCAL` around one statement, `pg_hint_plan`, and PG 19's
       `pg_plan_advice`. Using them in production hides the cause; using them for five minutes
       identifies it. `[GUC]` `[RESEARCH]` `[TRAP]`
2.3.17 MySQL's contrast: `FORCE INDEX`/`USE INDEX`/`IGNORE INDEX` are supported hints (not just
       debugging), optimizer hints in `/*+ ... */` comments, `optimizer_switch` flags, and
       `ANALYZE TABLE`/histograms (`ANALYZE TABLE ... UPDATE HISTOGRAM ON col`).
       `[MYSQL]` `[RESEARCH]`
2.3.18 The diagnostic order for "my index is not used", as a decision tree: is the index valid → does
       the predicate match its expression and collation → does the estimate say many rows → is the
       estimate right → is the table big enough → is it a generic plan → is it an `OR`.
       `[FLOW]` `[DIAG]`

*(18 leaves)*

## §2.4 Statistics and cardinality estimation in practice

2.4.1 What `ANALYZE` collects: a random sample of `300 × default_statistics_target` rows
      (**target 100** → 30,000 rows), from which it derives `null_frac`, `avg_width`, `n_distinct`,
      `most_common_vals`/`most_common_freqs`, `histogram_bounds`, `correlation`, and the
      elem-frequency arrays for arrays. `[NUM]` `[SOURCE]` `[RESEARCH]`
2.4.2 `pg_stats` as the readable view over `pg_statistic`, column by column, with a real row for
      `ledger_entry.amount` read aloud. `[SOURCE]` `[SQL]`
2.4.3 How an equality estimate is computed: if the value is in `most_common_vals`, use its frequency
      directly; otherwise assume the non-MCV mass is spread over `n_distinct - len(MCV)` values.
      Work a number. `[PROVE]` `[NUM]` `[SOURCE]`
2.4.4 How a range estimate is computed: locate the bound in the equal-frequency `histogram_bounds`
      and linearly interpolate within the containing bucket, then add the MCV contributions. Work a
      number. `[PROVE]` `[SOURCE]` `[RESEARCH]`
2.4.5 The selectivity function lookup path: the planner reads `pg_operator.oprrest` for the operator
      and calls that function (`eqsel`, `scalarltsel`, `scalargtsel`, `patternsel`, …). Naming this
      explains why a custom operator estimates badly. `[SOURCE]` `[RESEARCH]`
2.4.6 `n_distinct`'s known weakness: it is estimated from a sample, so a high-cardinality column can
      be badly underestimated on a huge table. `ALTER TABLE ... ALTER COLUMN ... SET (n_distinct =
      -0.5)` is the manual override, and the negative-value convention (a fraction of the row count)
      must be explained. `[NUM]` `[PROVE]`
2.4.7 `default_statistics_target` (**100**) and per-column
      `ALTER TABLE ... SET STATISTICS n` (up to 10,000): more buckets and more MCVs cost planning
      time and `ANALYZE` time, and buy accuracy on skewed columns. State the trade with numbers.
      `[GUC]` `[NUM]`
2.4.8 Extended statistics (`CREATE STATISTICS`): `ndistinct` (multi-column distinct counts),
      `dependencies` (soft functional dependencies), `mcv` (multi-column MCV lists), and
      expression statistics (PG 14+). The QuizStakes case is
      `(rail, state)` on withdrawals and `(client_id, position_type)` on positions.
      `[SQL]` `[SOURCE]` `[VERSION-TRAP]`
2.4.9 The independence assumption, proved wrong with numbers: `P(rail='BANK') × P(state='RETURNED')`
      versus the true joint frequency, and the estimate error that follows into join size and
      therefore into join algorithm choice. `[PROVE]` `[NUM]`
2.4.10 Join cardinality estimation: the classic `|A| × |B| / max(ndistinct_A, ndistinct_B)` formula,
       where it comes from, and why estimation error compounds multiplicatively through a chain of
       joins — the single reason deep join trees plan badly. `[PROVE]` `[NUM]`
       `[RESEARCH]`
2.4.11 Autovacuum's analyze trigger: `autovacuum_analyze_threshold` (**50**) +
       `autovacuum_analyze_scale_factor` (**0.1**) × row count. On a 7.2B-row table that is 720M
       modifications before an automatic `ANALYZE` — which is why big tables need per-table overrides.
       `[GUC]` `[NUM]` `[PROVE]`
2.4.12 The post-bulk-load rule: `ANALYZE` immediately after a `COPY`, because the planner otherwise
       plans against a table it believes is empty. This is the classic "the migration was fast and
       then everything was slow" cause. `[TRAP]` `[PROVE]`
2.4.13 `pg_upgrade` now preserves statistics in PG 18 (`--no-statistics` to opt out), which removes
       the historical "run `ANALYZE` on the whole cluster before letting traffic in" step — extended
       statistics are still not preserved. `[RESEARCH]` `[VERSION-TRAP]` `[NUM]`
2.4.14 MySQL's model: InnoDB's persistent statistics (`innodb_stats_persistent`,
       `innodb_stats_persistent_sample_pages` default **20**), `mysql.innodb_table_stats`/
       `innodb_index_stats`, optional column histograms via `ANALYZE TABLE ... UPDATE HISTOGRAM`
       with a bucket count, and the fact that MySQL has *no* MCV list — a materially weaker estimator.
       `[MYSQL]` `[NUM]` `[RESEARCH]`
2.4.15 What to do when the estimate cannot be fixed: restructure the query (materialise an
       intermediate result so the planner sees a real row count), split it, or accept a hint. This is
       the honest end of the section. `[PROVE]`

*(15 leaves)*

## §2.5 Join algorithms and join ordering in practice

2.5.1 **Nested loop**: for each outer row, probe the inner side. Cost = outer rows × inner probe
      cost. Wins when the outer side is small *and* the inner probe is an index lookup; catastrophic
      when the outer estimate is wrong by 1000×. `[NUM]` `[PROVE]`
2.5.2 `Materialize` under a nested loop (caching a small inner scan) and `Memoize` (PG 14+, an
      LRU cache of inner results keyed by the join parameter) — the latter is what turns a repeated
      nested loop into something acceptable, and its `Hits`/`Misses`/`Evictions` counters in the plan
      tell you whether it worked. `[PLAN]` `[VERSION-TRAP]`
2.5.3 **Hash join**: build a hash table from the smaller ("build") side, probe with the larger side.
      Equality only. Cost is roughly linear in both inputs, and it is the right answer for a large
      unsorted join. `[PROVE]`
2.5.4 Hash join memory and **batching**: when the build side exceeds `work_mem × hash_mem_multiplier`
      the executor partitions into batches spilled to temp files. The plan shows `Batches: n`
      (>1 means spill) and `Memory Usage`. A misestimated build side is how you get 1,024 batches.
      `[PLAN]` `[NUM]` `[PROVE]`
2.5.5 **Merge join**: both inputs sorted on the join key, then a single co-ordinated pass. Free if
      indexes already supply the order, expensive if it requires two sorts, and the only algorithm
      that handles inequality range joins well. `[PROVE]`
2.5.6 The selection rules, as a table: which algorithm the planner picks given (join type, predicate
      shape, input sizes, available orders, available indexes), plus the `enable_*` flags that let
      you test the counterfactual. `[GUC]` `[NUM]`
2.5.7 Semi/anti-join execution: `Hash Semi Join`, `Hash Anti Join`, `Nested Loop Semi Join` — and
      the fact that a semi-join can stop at the first match, which is why `EXISTS` is often faster
      than `IN` on a duplicate-heavy inner side. `[PROVE]`
2.5.8 Join ordering: the planner enumerates left-deep (and some bushy) trees with dynamic
      programming, up to `geqo_threshold` (**12** relations), after which the **genetic** optimizer
      GEQO takes over and becomes non-deterministic. So a 15-table query can produce a different
      plan on each planning. `[NUM]` `[GUC]` `[PROVE]` `[SOURCE]`
2.5.9 `join_collapse_limit` (**8**) and `from_collapse_limit` (**8**): above these the planner stops
      flattening subqueries/explicit joins, which *fixes* your join order as written. This is the
      documented, supported way to hand-order a join. `[GUC]` `[NUM]`
      `[PROVE]`
2.5.10 Parallel joins: `Gather`/`Gather Merge`, `Parallel Hash Join` (a shared hash table),
       `Parallel Seq Scan`, and the worker limits `max_parallel_workers_per_gather` (**2**),
       `max_parallel_workers` (**8**), `max_worker_processes` (**8**),
       `min_parallel_table_scan_size` (**8MB**), `min_parallel_index_scan_size` (**512kB**),
       `parallel_setup_cost` (**1000**), `parallel_tuple_cost` (**0.1**). `[GUC]` `[NUM]`
       `[RESEARCH]`
2.5.11 When parallelism does not happen and why: a `LIMIT` with a small fraction, a
       non-`PARALLEL SAFE` function, a `FOR UPDATE`, a CTE with a data-modifying statement, a cursor,
       or a table below the minimum size. `[NUM]` `[TRAP]`
2.5.12 The N-way join reality check: the estimate error compounds, so the answer to "this 12-table
       report plans badly" is usually to break it into two statements with a materialised
       intermediate, not to tune the planner. `[PROVE]`
2.5.13 MySQL's contrast: block nested-loop and hash join (8.0.18+), no merge join at all,
       `index_merge` as its bitmap-ish access path, greedy join ordering with
       `optimizer_search_depth`, and the **hypergraph optimizer** in 9.x as the replacement.
       `[MYSQL]` `[RESEARCH]` `[VERSION-TRAP]`
2.5.14 The QuizStakes join that must be a nested loop and the one that must be a hash join, with the
       plans: joining 50 operator-queue `application` rows to `review_case` (nested loop, indexed)
       versus a nightly reconciliation joining a day of `ledger_entry` to `movement` (hash).
       `[PLAN]` `[SOURCE]` `[NUM]`

*(14 leaves)*

## §2.6 Query rewrites that actually change the plan

2.6.1 The rewrite catalogue, each with a before/after plan: `NOT IN` → `NOT EXISTS`;
      `OR` → `UNION ALL`; correlated scalar subquery → `LEFT JOIN` on a pre-aggregated derived table;
      `DISTINCT` → `EXISTS`; window function → `LATERAL` with `LIMIT`; `OFFSET` → keyset;
      function-wrapped predicate → range; `COUNT(*)` → an estimate;
      `IN (huge list)` → `= ANY(array)` or a `VALUES` join. `[SQL]` `[PLAN]`
2.6.2 Predicate pushdown: what the planner can push into a subquery, a view, a UNION branch, or a
      partition — and the three things that block it (a volatile function, a window function, a
      `LIMIT` inside the subquery). `[PROVE]`
2.6.3 Aggregate pushdown and partial aggregation, including partitionwise aggregate
      (`enable_partitionwise_aggregate`, default **off**) and why turning it on matters for a
      month-partitioned ledger. `[GUC]` `[NUM]`
2.6.4 Partitionwise join (`enable_partitionwise_join`, default **off**) — the same argument.
      `[GUC]` `[NUM]`
2.6.5 The rewriter's own transformations, named so you know they are not your job: view expansion,
      `RULE` application, sublink pull-up, constant folding, `IN`-to-`ANY`, outer-join reduction
      (an outer join whose NULLs are filtered becomes an inner join), and self-join elimination
      (PG 18). `[PROVE]` `[RESEARCH]`
2.6.6 Rewrites that look clever and do nothing: `SELECT 1` instead of `SELECT *` inside `EXISTS`,
      reordering `AND` terms, `COUNT(1)` versus `COUNT(*)`, adding `DISTINCT` "to be safe". State
      them as a negative list so the reader stops doing them. `[TRAP]` `[PROVE]`
2.6.7 Rewrites that change semantics silently and must be verified: `IN` → `JOIN` (duplicates),
      `NOT EXISTS` → `LEFT JOIN IS NULL` (non-unique join key), `UNION` → `UNION ALL` (duplicates),
      moving a predicate from `ON` to `WHERE` on an outer join. `[TRAP]` `[PROVE]`
2.6.8 The "smart logic" rewrite done properly: instead of
      `WHERE (:status IS NULL OR state = :status)`, build the SQL dynamically so each shape gets its
      own plan — which is what a JPA `Specification` or a `CriteriaBuilder` is for.
      `[SOURCE]` `[X-REF 08]`
2.6.9 Rewriting for the QuizStakes 30 ms restriction decision: the query must be a single index-only
      scan on `restriction(client_id) WHERE state = 'ACTIVE'` returning a handful of rows, with no
      join, no function on the column and no `OR`. Show the plan and the buffer count that proves it
      fits the budget. `[SOURCE]` `[NUM]` `[PLAN]`
2.6.10 Measuring a rewrite honestly: same data, warm cache both times, `EXPLAIN (ANALYZE, BUFFERS)`
       for both, and `pg_stat_statements` before/after in production — not a single timed run.
       `[PROVE]` `[X-REF 16]`

*(10 leaves)*

## §2.7 Pagination

2.7.1 `LIMIT/OFFSET`'s two defects, stated separately because they have different fixes: cost grows
      with page number (§1.18.5) and the result **shifts under concurrent inserts**, so a user sees a
      row twice or misses one entirely. `[PROVE]` `[TRAP]`
2.7.2 **Keyset (seek/cursor) pagination**, written out with the row-value comparison and the unique
      tiebreaker, against `cardpayments.transactions`:
      `WHERE (created_at, id) < (:last_created_at, :last_id) ORDER BY created_at DESC, id DESC LIMIT
      20`, with the index `(created_at DESC, id DESC)` or `(created_at, id)`. `[SQL]`
      `[PROVE]`
2.7.3 Why it is constant time: the index seek positions directly at the cursor and reads 20 leaf
      entries, regardless of page number. Show the buffer counts for page 1 and page 5000 side by
      side. `[NUM]` `[PROVE]` `[PLAN]`
2.7.4 The expanded form for engines without row-value comparison:
      `a < ? OR (a = ? AND b < ?)` — and why the planner may handle it worse. `[SQL]`
      `[MYSQL]`
2.7.5 What keyset pagination costs: no random page access ("jump to page 500"), harder
      bidirectional navigation, and a cursor token that must encode the full sort tuple. State that
      random page access is almost never a real requirement, and when it is (an admin table), say so.
      `[PROVE]`
2.7.6 Cursor token design: base64 of the sort tuple, why it must be opaque, and why it must be
      validated (an attacker-supplied cursor is an input to a `WHERE` clause).
      `[X-REF 12]` `[X-REF 13]`
2.7.7 Mixed-direction sorts break the simple row-value form (`ORDER BY a ASC, b DESC` cannot be
      expressed as one tuple comparison) — the fix is an index declared in matching directions.
      `[TRAP]` `[PROVE]`
2.7.8 Stable pagination requires a **total order**: a non-unique sort key without a tiebreaker loses
      and duplicates rows across pages. Prove it with two rows sharing a timestamp.
      `[PROVE]` `[TRAP]`
2.7.9 Server-side cursors (`DECLARE ... CURSOR WITH HOLD`) as the third option, and why they do not
      survive a stateless HTTP API or a connection pool. `[TRAP]` `[X-REF 12]`
2.7.10 **The QuizStakes pagination problem that has no clean SQL answer**: "all my withdrawals" merges
       two independently-sorted sources from two schemas (§7.3, §15.2), so the ordering is imposed
       after the merge and neither keyset nor offset works across the pair. The bible must state the
       actual technique — fetch `n` from each source by keyset, merge, emit `n`, and carry a composite
       cursor holding both positions. `[SOURCE]` `[PROVE]` `[X-REF 22]`
2.7.11 Deep-pagination alternatives when a total count and random access are both demanded: a
       materialised page index, a pre-computed ranking column, or refusing the requirement.
       `[PROVE]`
2.7.12 The API contract side (page tokens, `Link` headers, max page size) is `12-api-design.md`; this
       section owns only the SQL. `[X-REF 12]`

*(12 leaves)*

## §2.8 Counting

2.8.1 Why `COUNT(*)` on a large table is slow in PostgreSQL specifically: visibility must be checked
      per row, so there is no O(1) count — an index-only scan over the smallest index is the best
      case and still reads the whole index. On a 7.2B-row ledger this is minutes.
      `[PROVE]` `[NUM]`
2.8.2 InnoDB is no better for the same reason (MVCC), which is why `SELECT COUNT(*)` in MySQL is also
      a scan — but MyISAM kept an exact row count, which is where the myth comes from.
      `[MYSQL]` `[TRAP]`
2.8.3 The estimate: `pg_class.reltuples` (accurate only after `ANALYZE`/`VACUUM`), the
      `EXPLAIN`-based estimate for a filtered count, and `pg_stat_user_tables.n_live_tup`.
      `[SQL]` `[NUM]`
2.8.4 The "has more" pattern that removes the need for a total: fetch `pageSize + 1` and report
      whether the extra row existed. This is what `Slice` does in Spring Data.
      `[PROVE]` `[X-REF 08]`
2.8.5 Maintained counters: a `counter` table updated by trigger or by the write path, the row-lock
      contention it creates on a hot key, and the two standard mitigations — sharded counters
      (N rows summed) and a periodic rollup. At 1,200 stakes/sec a single counter row is a
      serialisation point. `[NUM]` `[PROVE]` `[X-REF 15]`
2.8.6 Approximate distinct counts: `count(DISTINCT x)` cost versus HyperLogLog (`postgresql-hll`,
      `datasketches`), and when an approximation is acceptable (a dashboard) and when it is not
      (a limit gate). `[RESEARCH]` `[PROVE]`
2.8.7 Counting for the QuizStakes limit gate specifically: "cumulative deposit crosses threshold"
      (§10.3) must be *exact* because it applies a restriction, so it is a maintained, transactional
      figure — and §15.1 names it as the CAS/lock-free example where "exactness matters but ordering
      does not". `[SOURCE]` `[PROVE]`
2.8.8 The count query patterns and their costs, tabulated: `COUNT(*)` unfiltered, `COUNT(*)` with an
      indexed predicate, `COUNT(*)` with a non-indexed predicate, `COUNT(DISTINCT)`,
      `EXISTS`, `LIMIT 1`. `[NUM]`
2.8.9 `COUNT(*)` inside a `Page<T>` query is the hidden second statement — the ORM-side of this is in
      `08-spring-data-jpa.md`, but the SQL cost is here. `[X-REF 08]`

*(9 leaves)*

## §2.9 Bulk operations and batching

2.9.1 The five ways to write many rows, ranked by throughput with the mechanism for each: row-by-row
      `INSERT` with autocommit, row-by-row inside one transaction, JDBC batch, JDBC batch with
      `reWriteBatchedInserts`, multi-row `INSERT ... VALUES`, and `COPY`. State the order of
      magnitude between the ends. `[NUM]` `[PROVE]` `[JDBC]`
2.9.2 Why autocommit-per-row is the worst: one WAL flush (`fsync`) per row. With `synchronous_commit
      = on` that is one disk sync per row; the QuizStakes 500k-record month-end file would take hours.
      `[NUM]` `[PROVE]`
2.9.3 `synchronous_commit = off` as the deliberate durability trade for a *restartable* bulk load
      (you lose the last `wal_writer_delay`-ish window on crash, and the file can be re-ingested).
      Say exactly what you are risking. `[GUC]` `[PROVE]`
2.9.4 Group commit: `commit_delay` (**0** µs) and `commit_siblings` (**5**) as the built-in
      amortisation of `fsync` across concurrent committers, and why it only helps under concurrency.
      `[GUC]` `[NUM]` `[PROVE]`
2.9.5 `COPY ... FREEZE` inside the same transaction as the table's creation/truncation — rows are
      written already frozen, skipping a future freeze pass. The restriction and the payoff on a
      7.2B-row archival load. `[NUM]` `[PROVE]`
2.9.6 Loading order: create the table, `COPY`, then create indexes and add constraints — because
      building an index once over N rows beats maintaining it N times. Show the arithmetic.
      `[NUM]` `[PROVE]`
2.9.7 The unlogged-table trick and its exact cost (no WAL, no replica, truncated on crash), plus
      `ALTER TABLE ... SET LOGGED` afterwards writing the whole table to WAL anyway — so the saving
      is smaller than it looks. `[PROVE]` `[TRAP]`
2.9.8 Batch **updates** and deletes: chunking with a bounded key range, committing per chunk,
      `ORDER BY` inside the chunk selector to keep lock order consistent, and a sleep between chunks
      to let autovacuum and replicas keep up. `[SQL]` `[PROVE]`
2.9.9 The lock footprint of a batch: a 10,000-row `UPDATE` holds 10,000 row locks until commit, so
      chunk size is a *lock* decision as much as a performance one. `[NUM]` `[PROVE]`
2.9.10 WAL volume of a bulk operation and its downstream effects: replica lag, archive backlog,
       `max_wal_size` overshoot forcing extra checkpoints, and a full disk. The 500k-record file is
       the worked example. `[NUM]` `[PROVE]` `[X-REF 20]`
2.9.11 `pg_bulkload`, `pgloader`, `COPY` with `ON_ERROR ignore` / `REJECT_LIMIT` (PG 18) for a file
       with 400 bad rows out of 500,000 — which is exactly §15.5's partial-failure scenario, where
       "499,600 must still credit". `[RESEARCH]` `[SOURCE]` `[NUM]`
2.9.12 MySQL's equivalents: `LOAD DATA INFILE`, `INSERT` with multiple `VALUES` and
       `bulk_insert_buffer_size`, `rewriteBatchedStatements`, `innodb_flush_log_at_trx_commit = 2`
       during a load, and `ALTER TABLE ... DISABLE KEYS` (MyISAM only — a common wrong answer for
       InnoDB). `[MYSQL]` `[TRAP]`
2.9.13 Idempotent bulk load: the file-level idempotency reference §13.4 demands ("file submitted
       twice — bank may accept both"), implemented as a `UNIQUE` on `(file_ref, record_no)` so a
       re-ingest is a no-op via `ON CONFLICT DO NOTHING`. `[SQL]` `[SOURCE]`
2.9.14 Where the ORM's batching story lives (`hibernate.jdbc.batch_size`, `order_inserts`, IDENTITY
       disabling batching) — `08-spring-data-jpa.md`. This section owns the driver and server side.
       `[X-REF 08]`

*(14 leaves)*

## §2.10 N+1 and round-trip cost at the SQL layer

2.10.1 The N+1 shape without an ORM: a loop in Java issuing one `SELECT` per id. The cost is not CPU
       in the database, it is **N network round trips** — at 0.5 ms RTT, 50 rows is 25 ms of pure
       latency against a 30 ms budget. `[NUM]` `[PROVE]`
2.10.2 The QuizStakes instance, exactly as §15.6 states it: "the operator queue screen showing 50
       cases, each fetching PII individually" — and the additional twist that PII lives in another
       *service*, so the fix is a batch API, not a join. `[SOURCE]` `[X-REF 22]`
2.10.3 The four SQL-layer fixes with their costs: an `IN`/`= ANY(array)` batch, a join, a
       `LATERAL` per-parent limit, and a single round trip with multiple result sets.
       `[SQL]` `[PROVE]`
2.10.4 `= ANY(?::uuid[])` with `setArray`/`createArrayOf` versus a generated `IN (?,?,?...)` list —
       the array form has one plan for all list lengths, which matters for the plan cache
       (§1.11.10, §3.10). `[JDBC]` `[PROVE]`
2.10.5 Chunking the batch: a 10,000-element `IN` list is one statement and a bad plan; 200-element
       chunks keep the plan sane. State how you would pick the chunk size.
       `[NUM]` `[PROVE]`
2.10.6 Measuring round trips rather than guessing: a `StatementInspector`/`datasource-proxy` counter,
       `pg_stat_statements.calls` deltas, and a per-endpoint statement budget asserted in a test.
       `[DIAG]` `[X-REF 16]`
2.10.7 The inverse anti-pattern: collapsing everything into one giant join that returns
       parent × child × grandchild rows, transferring the parent columns N×M times. State the row
       arithmetic that makes it worse than two queries. `[NUM]` `[PROVE]` `[X-REF 08]`
2.10.8 Server-side batching of *writes*: one statement with `unnest` over arrays, or
       `INSERT ... SELECT FROM unnest(...)`, as the pattern that posts all four legs of a stake
       reservation in one round trip. `[SQL]` `[SOURCE]`
2.10.9 Pipelining as the third axis: JDBC has no pipelining, so the only ways to reduce round trips
       are batching and fewer statements. Naming this closes the option space.
       `[JDBC]` `[PROVE]`

*(9 leaves)*

## §2.11 Lost update, and the four things you can do about it

2.11.1 The anatomy, spelled out with two sessions and a timeline: `SELECT balance` → compute in Java
       → `UPDATE balance = :new`. Both read 100, both write 50, one decrement vanishes. This happens
       at **every** isolation level in PostgreSQL RC and is the most-asked concurrency question.
       `[PROVE]` `[NUM]`
2.11.2 **Fix 1 — do the arithmetic in SQL**: `UPDATE fundsledger.position SET balance = balance -
       :amount WHERE account_id = :id AND type = 'CLIENT_CASH_AVAILABLE' AND balance >= :amount`,
       then check the row count. One statement, no read-modify-write, and the `balance >= :amount`
       predicate enforces invariant #2 atomically. This is the best answer.
       `[SQL]` `[PROVE]` `[SOURCE]`
2.11.3 Why the row count is the whole mechanism: zero rows updated means "insufficient funds", which
       is a *business* outcome, not an error — matching Appendix C.6's note that
       `InsufficientFundsException` should be a result type, not an exception.
       `[SOURCE]` `[PROVE]`
2.11.4 **Fix 2 — pessimistic**: `SELECT ... FOR UPDATE` before the read, so the second session blocks
       until the first commits. Correct, and §15.1 states the cost plainly: "it serialises every
       stake for that client". At 1,200 stakes/sec across 380k actives that is usually fine and for a
       whale it is not. `[SOURCE]` `[NUM]` `[PROVE]`
2.11.5 **Fix 3 — optimistic**: a `version` column, `UPDATE ... WHERE id = ? AND version = ?`, retry
       on zero rows. Appendix C.6 puts `version` on `Position`, `Application` and `ReviewCase`
       for exactly this. The retry **must re-read**, and a retry that does not is an infinite loop.
       `[SQL]` `[PROVE]` `[TRAP]` `[X-REF 08]`
2.11.6 **Fix 4 — raise isolation**: `REPEATABLE READ` turns the second write into a 40001
       serialization failure instead of a silent overwrite; `SERIALIZABLE` additionally catches write
       skew. Both require the same retry loop, so this is not a way to avoid retry logic.
       `[PROVE]` `[TRAP]`
2.11.7 The decision table: which fix for which shape — single-row arithmetic (fix 1), multi-row
       invariant (fix 2 or 4), long think-time between read and write including a human (fix 3),
       cross-row invariant nobody wrote (fix 4). `[NUM]` `[PROVE]`
2.11.8 The retry loop done correctly: bounded attempts, jittered exponential backoff, idempotent
       operation, and a metric on attempts — because a rising retry rate is a contention signal, not
       a bug. `[BUILD]` `[X-REF 20]`
2.11.9 The QuizStakes lost-update example that is *not* about money: §15.1's "two operators open the
       same `AA-700` case; both save a decision; the second overwrites, and the audit trail shows one
       approval where two happened." Optimistic locking on `ReviewCase.version` is the fix, and the
       reason it matters is regulatory evidence, not correctness of a number.
       `[SOURCE]` `[PROVE]`
2.11.10 Insert races (the "lost insert"): two sessions both check-then-insert. No isolation level
        below SERIALIZABLE prevents it, because there is no row to lock — only a unique index does.
        Back to §1.7.2. `[PROVE]` `[TRAP]`
2.11.11 The `INSERT ... ON CONFLICT DO UPDATE` version and its lock behaviour under contention, plus
        the deadlock that two upserts touching two keys in opposite order can produce.
        `[PROVE]` `[SQL]`
2.11.12 InnoDB's different behaviour for the same code: under RR a locking read sees the latest
        committed row (§1.24.13), so `SELECT ... FOR UPDATE` + `UPDATE` behaves as you expect, but a
        plain `SELECT` then `UPDATE` still loses the update. The same Java code has different failure
        characteristics on the two engines. `[MYSQL]` `[PROVE]` `[TRAP]`

*(12 leaves)*

## §2.12 Deadlocks in practice

2.12.1 The definition and the minimal reproduction: two transactions, two rows, opposite acquisition
       order. The write pass must ship a runnable two-session script.
       `[BUILD]` `[SQL]`
2.12.2 How the database resolves it: PostgreSQL runs a deadlock detector after `deadlock_timeout`
       (**1s**) on a *blocked* waiter, finds the cycle in the wait-for graph, and aborts one victim
       with **40P01**. InnoDB detects immediately (`innodb_deadlock_detect = ON`) and chooses the
       victim by the smallest transaction weight; with detection off it relies on
       `innodb_lock_wait_timeout` (**50 s**). `[NUM]` `[MYSQL]` `[SOURCE]`
2.12.3 Reading a PostgreSQL deadlock message line by line: both process ids, both statements, the
       `DETAIL` showing which lock each waits for and holds, and the `HINT`. Then the same for
       `SHOW ENGINE INNODB STATUS`'s `LATEST DETECTED DEADLOCK` section.
       `[DIAG]` `[MYSQL]`
2.12.4 `log_lock_waits` (default **off** — turn it on) with `deadlock_timeout` as the threshold, and
       `innodb_print_all_deadlocks` as the MySQL equivalent. Without these you find out from users.
       `[GUC]` `[DIAG]`
2.12.5 The deadlock sources, enumerated: opposite row order in two transactions, an FK check
       acquiring a parent lock, two upserts on overlapping keys, index-page-level conflicts, a
       trigger touching a second table, `ALTER TABLE` versus DML, and — InnoDB-specific — gap locks
       conflicting with insert-intention locks. `[MYSQL]` `[NUM]`
2.12.6 The QuizStakes deadlock, exactly: §15.1 "two concurrent movements acquiring cash and bonus
       positions in opposite order". The fix is a **total order over positions** (sort by position
       type ordinal before locking), which the write pass must show as code.
       `[SOURCE]` `[BUILD]` `[PROVE]`
2.12.7 Why "just lock the whole client row first" works and what it costs: it makes every movement
       for one client serial (§15.1 "lock granularity: per-position vs per-client vs whole-ledger —
       the last is trivially correct and unusable"). `[SOURCE]` `[PROVE]`
2.12.8 Deadlock **is not** the same as a lock wait timeout, and neither is the same as
       `statement_timeout`. Three different errors, three different diagnoses:
       40P01, 55P03/`innodb_lock_wait_timeout`, 57014. `[DIAG]` `[NUM]` `[TRAP]`
2.12.9 Retryability: a deadlock victim's transaction is fully rolled back, so retry is safe *if the
       operation is idempotent*. Which, in QuizStakes, it is — every movement carries a key
       (invariant #11). Say why that pre-existing design choice is what makes retry legal.
       `[SOURCE]` `[PROVE]`
2.12.10 Deadlock-free by construction: single-statement writes, no user think-time inside a
        transaction, consistent ordering, and short transactions. Ranked, with the honest note that
        you cannot eliminate them entirely once triggers and FKs are involved.
2.12.11 Gap-lock deadlocks in InnoDB as their own species: an `INSERT` into a gap another transaction
        holds a next-key lock on, and the classic "two transactions insert into the same range after
        a failed `SELECT`" cycle. Why the same code deadlocks in MySQL RR and does not in PostgreSQL.
        `[MYSQL]` `[PROVE]` `[TRAP]`
2.12.12 Monitoring: `pg_stat_database.deadlocks` as a rate, an alert on any non-zero rate change,
        and the distinction between "one deadlock a week" (noise) and "a hundred an hour" (a lock
        ordering bug). `[DIAG]` `[X-REF 20]`

*(12 leaves)*

## §2.13 The database as a job queue

2.13.1 The claim, stated so it can be defended: for moderate rates, `FOR UPDATE SKIP LOCKED` on a
       table is a correct, transactional, zero-infrastructure queue — and it is a strong answer in a
       design interview precisely because it removes a component. `[PROVE]` `[X-REF 14]`
2.13.2 The canonical claim statement, written against `bankwithdrawal.transactions`:
       `UPDATE ... SET state = 'LEDGER_POSTING_PENDING', run_id = :run WHERE id IN (SELECT id FROM
       ... WHERE state = 'APPROVED' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 300) RETURNING
       *` — 300 being one `PaymentRun`'s ~1.8k-record file divided across workers.
       `[SQL]` `[SOURCE]` `[NUM]`
2.13.3 Why it is race-free: `SKIP LOCKED` means each worker's `SELECT` returns rows no other worker
       has locked, and the row locks are held to commit — so batches are disjoint with no coordination.
       `[PROVE]`
2.13.4 The properties you must add yourself: a visibility timeout (a `claimed_at` column plus a
       reaper), a retry counter with a dead-letter state, priority (an index prefix), delay
       (`available_at > now()`), and per-consumer fairness. Each is a column and an index, and the
       bible must show them. `[SQL]` `[PROVE]`
2.13.5 The index that makes it viable: a partial index on the claimable predicate, so the queue scan
       does not degrade as the table grows to millions of completed rows.
       `[SQL]` `[NUM]` `[PROVE]`
2.13.6 The bloat problem specific to queue tables: every claim is an `UPDATE`, so a high-throughput
       queue table is the fastest-bloating object in the database and needs an aggressive per-table
       `autovacuum_vacuum_scale_factor` (e.g. 0.01) and a low `fillfactor`.
       `[NUM]` `[PROVE]` `[GUC]`
2.13.7 When the database queue stops being the right answer: fan-out to multiple independent
       consumers (each needs its own offset — Appendix B.3 says "log, not queue"), retention beyond
       the operational window, cross-region delivery, or rates where the queue table's write volume
       rivals the business tables. `[SOURCE]` `[X-REF 14]`
2.13.8 `LISTEN`/`NOTIFY` as the wake-up signal that removes polling latency, with its
       non-durability caveat (§1.28.16) — so it is an optimisation over polling, never the delivery
       mechanism. `[TRAP]` `[PROVE]`
2.13.9 The **transactional outbox** at the SQL layer: write the business row and the outbox row in one
       transaction, then a poller claims outbox rows with `SKIP LOCKED` and publishes. QuizStakes
       needs it for `AccountActivated` (§15.2: "must both happen or neither"), and Appendix B.3
       specifies "transactional outbox + poller". The architecture-level treatment is in
       `22-system-design.md`; the SQL mechanics are here. `[SOURCE]` `[SQL]`
       `[X-REF 22]` `[X-REF 14]`
2.13.10 The outbox alternative at the database level: logical decoding / CDC reading the WAL directly
        (§3.23), which removes the poller and the outbox table at the cost of a replication slot you
        must monitor. State both sides. `[PROVE]` `[X-REF 14]`
2.13.11 The leader-election requirement §13.4 states — "two runs open simultaneously → duplicate
        payouts; leader election is the only defence" — implemented with
        `pg_try_advisory_xact_lock` or a `SELECT ... FOR UPDATE NOWAIT` on a singleton row. Show both
        and say which you would ship. `[SOURCE]` `[SQL]` `[PROVE]`

*(11 leaves)*

## §2.14 Idempotency at the SQL layer

2.14.1 The definition that matters: the same request applied twice produces one effect. Not "the
       second call errors" — "the second call returns the first call's outcome".
       `[PROVE]` `[X-REF 12]`
2.14.2 The mechanism: a `UNIQUE` index on the key, an insert-first write path, and a read-back of the
       original effect on conflict. PG 19's `ON CONFLICT DO SELECT` collapses this to one statement.
       `[SQL]` `[RESEARCH]`
2.14.3 Scoping the key: per operation type, per client, and with a TTL — QuizStakes' `IdempotencyKey`
       is `String(64)`, "caller-supplied, scoped per operation type" (Appendix C.1).
       `[SOURCE]`
2.14.4 **Why a cache alone is wrong**, quoted from Appendix B.2: "a cache alone is an optimisation
       that fails *open* under eviction or partition — and failing open on a card capture means
       double-charging. The unique constraint is the correctness mechanism; the cache only makes the
       common case fast." This is the single best justification for a database constraint in the
       whole domain. `[SOURCE]` `[PROVE]`
2.14.5 The in-flight problem: two concurrent requests with the same key. The first insert wins, the
       second blocks on the unique index until the first commits, then sees the conflict — which is
       exactly the behaviour you want and is *only* available from the index.
       `[PROVE]` `[NUM]`
2.14.6 The failure case: the first request inserted the key and then crashed before completing the
       effect. Now the key exists and the effect does not. The fix is to make the key row and the
       effect part of the same transaction, which is why the key lives in the same database as the
       ledger. `[PROVE]` `[TRAP]`
2.14.7 Retention: idempotency keys must expire, or the table grows forever. A partitioned or
       TTL-swept key table, with the retention window matched to the maximum client retry window.
       `[NUM]`
2.14.8 The QuizStakes replay set the design must survive: "the PSP webhook delivered five times for
       one capture" (§15.2), "`SettleStake` arrives twice for one round", "`AccountActivated` consumed
       twice — restrictions must not be lifted twice", and "a captured `ReserveStake` replayed to
       double-stake" (§15.7's replay attack). Each maps to a key scope and a unique index; the write
       pass must tabulate them. `[SOURCE]` `[SQL]`
2.14.9 Natural idempotency as the cheaper alternative where it exists: a state-machine transition
       guarded by `WHERE state = :expected` is idempotent without a key, because the second attempt
       updates zero rows. Show it for `DEP-301 → DEP-400`. `[SQL]` `[PROVE]`

*(9 leaves)*

## §2.15 Connection pooling and server-side limits

2.15.1 Why a pool exists, with the number: a PostgreSQL connection costs a process fork plus auth, on
       the order of **10–100 ms**, and a pool amortises that to microseconds. `[NUM]`
2.15.2 **The counter-intuitive rule: small pools are faster.** Beyond the number of queries the
       server can genuinely run concurrently, extra connections add context switching, memory and
       lock contention while adding no throughput — they only add queueing latency.
       `[PROVE]` `[NUM]`
2.15.3 The often-cited starting formula `connections ≈ (core_count × 2) + effective_spindle_count`,
       stated as a *starting point* with the honest caveat that it predates SSDs and that the real
       answer comes from a saturation test. Roughly **10–20** for a typical service, not 200.
       `[NUM]` `[PROVE]`
2.15.4 The fleet arithmetic that causes the outage: `instances × pool_size` must stay below
       `max_connections` (default **100**) minus superuser reserve. Ten replicas × 50 = 500 →
       SQLSTATE 53300. Work it for the QuizStakes fleet from Appendix A.6 — `ApplicationGateway` 12→40
       instances, `ClientRestrictions` 8, `PaymentService` 8, `FundsLedger` 3 — and show that a naive
       pool size of 20 each already exceeds a default cluster. `[NUM]` `[PROVE]`
       `[SOURCE]`
2.15.5 HikariCP's settings by name with defaults: `maximumPoolSize` (**10**), `minimumIdle`
       (= max), `connectionTimeout` (**30000 ms**), `idleTimeout` (**600000 ms**),
       `maxLifetime` (**1800000 ms**), `keepaliveTime` (**0**), `validationTimeout` (**5000 ms**),
       `leakDetectionThreshold` (**0**), `initializationFailTimeout` (**1**),
       `connectionInitSql`, `transactionIsolation`, `readOnly`, `autoCommit` (**true**).
       `[NUM]` `[RESEARCH]` `[X-REF 08]`
2.15.6 `maxLifetime` **must be shorter** than any idle timeout imposed by the database, a proxy, or a
       load balancer — otherwise the pool hands out a socket the other end has already closed and the
       first statement fails with a broken pipe. `[PROVE]` `[TRAP]`
2.15.7 The pool-exhaustion diagnosis: `SQLTransientConnectionException: ... request timed out after
       30000ms`, what it does and does not mean (the database may be idle; the pool is the
       bottleneck), and the three causes — pool too small, connections held too long (long
       transactions, OSIV, network I/O inside a transaction), and a leak.
       `[DIAG]` `[PROVE]` `[X-REF 08]`
2.15.8 **Pool deadlock**: a thread holding one connection needs a second (a `REQUIRES_NEW`, a nested
       transaction, or a service call that opens its own). With N threads each holding one and waiting
       for another, nobody proceeds. The rule: `pool_size >= 2 × concurrent_such_threads`, or
       restructure to need one. `[PROVE]` `[NUM]` `[X-REF 07]`
2.15.9 External pooling: **PgBouncer** modes — `session` (connection returned at disconnect),
       `transaction` (returned at commit/rollback — the useful one), `statement` (returned per
       statement; no multi-statement transactions). Defaults: `max_client_conn` **2048** (some builds
       ship 100), `default_pool_size` **20**, `max_prepared_statements` **200** (1.21+), plus
       `query_wait_timeout`, `server_idle_timeout`, `pool_mode` per-database.
       `[NUM]` `[RESEARCH]` `[SOURCE]`
2.15.10 What breaks under transaction pooling, enumerated: session-level `SET`, `SET ROLE`,
        advisory session locks, `WITH HOLD` cursors, `LISTEN`, temp tables, and (pre-1.21)
        server-side prepared statements. Each is a real outage someone has had.
        `[TRAP]` `[PROVE]`
2.15.11 Pgpool-II, RDS Proxy and Odyssey named as alternatives with the one thing each adds; and
        MySQL's ProxySQL. `[MYSQL]` `[X-REF 18]`
2.15.12 The layered picture: application pool → external pooler → server backends, and why you must
        size all three consistently. Draw the QuizStakes numbers through it.
        `[NUM]` `[PROVE]`
2.15.13 Metrics that tell you the pool is wrong: `hikaricp_connections_pending`,
        `hikaricp_connections_usage_seconds`, `hikaricp_connections_acquire_seconds`,
        `pg_stat_database.numbackends`, and the saturation test that finds the knee.
        `[DIAG]` `[X-REF 20]`
2.15.14 Connection storms after a failover or a deploy, and the mitigations: staggered startup,
        `initializationFailTimeout`, jittered reconnect, and a pooler that queues rather than the
        application retrying. `[PROVE]` `[X-REF 22]`

*(14 leaves)*

## §2.16 Replication

2.16.1 The two kinds, kept strictly apart: **physical** (byte-level WAL shipping; the replica is an
       exact copy, all databases, same major version) and **logical** (row-level change stream per
       publication; selective, cross-version, cross-schema).
       `[PROVE]`
2.16.2 Physical replication mechanics: `wal_level = replica` (default), a WAL sender on the primary, a
       WAL receiver plus startup process on the standby, `primary_conninfo`, replication slots
       (`pg_replication_slots`) to stop WAL recycling, `wal_keep_size`, and archive-based fallback.
       `[GUC]` `[NUM]`
2.16.3 Synchronous options and exactly what each waits for: `synchronous_commit = off` (no wait, not
       even local flush), `local` (local flush only), `remote_write` (standby received and wrote to
       OS), `on` (standby flushed to disk), `remote_apply` (standby *applied*, so a read on that
       standby sees it). Plus `synchronous_standby_names` with `FIRST k (...)` / `ANY k (...)`.
       `[GUC]` `[NUM]` `[PROVE]` `[SOURCE]`
2.16.4 The latency arithmetic: `remote_apply` adds a full network round trip plus apply time to every
       commit. For the QuizStakes ledger at 13,600 writes/sec peak that is a throughput decision, not
       a configuration preference. `[NUM]` `[PROVE]`
2.16.5 **Replication lag**: measured as `pg_stat_replication.write_lag`/`flush_lag`/`replay_lag` and
       LSN deltas (`sent_lsn`, `write_lsn`, `flush_lsn`, `replay_lsn`), typically milliseconds and
       spiking under write bursts — the 3,400/sec settlement burst being the exact trigger.
       `[SQL]` `[NUM]` `[DIAG]` `[SOURCE]`
2.16.6 **Read-your-writes breaks on a replica.** Write to the primary, read from the replica, and the
       client does not see their own change. §15.2 names it: "client uploads a document and refreshes;
       the replica has not caught up and the banner still says required."
       `[SOURCE]` `[PROVE]`
2.16.7 The four fixes, with the cost of each: sticky-primary reads for a short window after a write;
       LSN tokens (capture `pg_current_wal_insert_lsn()` on write, then
       `pg_wal_replay_lsn() >= token` or `pg_wal_wait_lsn` before the read); `remote_apply` for that
       path only; or accept staleness with an explicit UI contract.
       `[SQL]` `[PROVE]` `[X-REF 22]`
2.16.8 Spring implementation: a routing `DataSource` keyed off `@Transactional(readOnly = true)`, and
       the trap that a read-only transaction opened *before* the write in the same request routes to
       a replica. `[X-REF 08]` `[TRAP]`
2.16.9 Hot standby conflicts: a query on the standby can be cancelled because replay needs to remove
       a row it still sees (`ERROR: canceling statement due to conflict with recovery`), controlled
       by `max_standby_streaming_delay` (**30 s**) and `hot_standby_feedback` (**off** by default —
       turning it on protects standby queries at the cost of bloat on the primary).
       `[GUC]` `[NUM]` `[DIAG]` `[TRAP]`
2.16.10 Failover with async replication **loses the unreplicated tail**. Say this out loud when
        someone proposes async replication for financial data — and note that QuizStakes' §14.2
        invariant 1 makes that loss a regulatory event, not a data-loss statistic.
        `[SOURCE]` `[PROVE]`
2.16.11 Failover mechanics: `pg_promote()`, timeline switches, `recovery_target_timeline`, the
        split-brain risk and the fencing/STONITH requirement, and the tooling (Patroni, repmgr,
        pg_auto_failover) — plus what a managed service does for you.
        `[X-REF 18]` `[X-REF 22]`
2.16.12 Logical replication: `CREATE PUBLICATION`/`CREATE SUBSCRIPTION`, `wal_level = logical`,
        `REPLICA IDENTITY {DEFAULT|FULL|USING INDEX|NOTHING}` and why a table without a primary key
        needs `FULL` for updates/deletes to replicate, initial sync, and the row filters and column
        lists added in PG 15. PG 18 changed the `CREATE SUBSCRIPTION streaming` default from `off` to
        `parallel` and added `publish_generated_columns`.
        `[SQL]` `[NUM]` `[RESEARCH]` `[VERSION-TRAP]`
2.16.13 Logical replication's known gaps: no DDL, no sequences (until PG 16's failover slots work),
        no `TRUNCATE` before PG 11, conflict handling is "stop and wait for a human", and a stuck
        subscription holds WAL forever. PG 18 added `idle_replication_slot_timeout` (**1 hour**) to
        auto-invalidate abandoned slots — a genuinely new safety valve.
        `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]` `[NUM]`
2.16.14 **A forgotten replication slot fills the disk.** The mechanism (WAL cannot be recycled while
        a slot needs it), the monitoring query (`pg_replication_slots.active`, `restart_lsn` age),
        and `max_slot_wal_keep_size` as the bound that sacrifices the slot instead of the primary.
        `[GUC]` `[TRAP]` `[DIAG]`
2.16.15 MySQL's model in full contrast: the **binary log** (`binlog_format` `ROW`/`STATEMENT`/`MIXED`,
        `binlog_row_image`), an IO thread + relay log + one or more SQL applier threads,
        `GTID_MODE = ON` with `gtid_executed`/`gtid_purged` making replica re-pointing and
        "which transactions are missing" tractable, `SOURCE_AUTO_POSITION`, multi-threaded applier
        with `replica_parallel_type = LOGICAL_CLOCK` and writeset dependency tracking
        (`binlog_transaction_dependency_tracking = WRITESET`), and `Seconds_Behind_Source`'s
        well-known unreliability. `[MYSQL]` `[NUM]` `[RESEARCH]`
2.16.16 MySQL semi-synchronous replication: `rpl_semi_sync_source_enabled`,
        `rpl_semi_sync_source_wait_for_replica_count` (**1**),
        `rpl_semi_sync_source_wait_point` (`AFTER_SYNC` vs `AFTER_COMMIT` — the difference decides
        whether a failover can expose a phantom read of a lost transaction), the automatic degradation
        to async when no replica acknowledges, and Group Replication as the synchronous option.
        `[MYSQL]` `[NUM]` `[PROVE]` `[RESEARCH]`
2.16.17 The consistency vocabulary this section supplies to `22-system-design.md`: read-your-writes,
        monotonic reads, bounded staleness, and per-operation consistency choice — with the
        QuizStakes ruling that "cash available authorises spending, so it cannot be eventually
        consistent" (§15.2) while `BalanceView` display reads can be.
        `[SOURCE]` `[X-REF 22]`

*(17 leaves)*

## §2.17 Partitioning and sharding

2.17.1 The distinction that must be made first: **partitioning** splits a table inside one database;
       **sharding** splits data across databases. They solve different problems and are constantly
       conflated. `[TRAP]` `[X-REF 22]`
2.17.2 Declarative partitioning: `PARTITION BY RANGE | LIST | HASH`, `CREATE TABLE ... PARTITION OF
       ... FOR VALUES FROM ... TO ...`, `DEFAULT` partition, sub-partitioning, and `ATTACH`/`DETACH`.
       `[SQL]`
2.17.3 What partitioning actually buys, ranked: **cheap bulk deletion by `DETACH`** (the real reason),
       partition pruning reducing scanned data, smaller per-partition indexes, per-partition vacuum
       and maintenance, and per-partition storage/tablespace placement.
       `[PROVE]` `[NUM]`
2.17.4 **The QuizStakes case is decided by the numbers**: 7.2B rows/year at 7-year retention with a
       90-day hot window (Appendix A.3) "makes partitioning and archival mandatory rather than
       preferable", and Appendix B.2 specifies "relational, own instance, **range-partitioned by
       month**". Show the arithmetic: ~600M rows and ~108 GB per monthly partition.
       `[SOURCE]` `[NUM]` `[PROVE]`
2.17.5 Partition pruning: at plan time (constant predicates) and at execution time
       (`enable_partition_pruning`, default **on**; runtime pruning for parameters and for nested-loop
       join keys), shown in the plan as `Subplans Removed: n`. `[GUC]` `[PLAN]`
2.17.6 Pruning only works when the query filters on the **partition key**. A ledger query by
       `movement_id` with no `posted_at` predicate touches all 84 partitions — which is why the
       partition key must be chosen from the query patterns, not from the data's shape.
       `[PROVE]` `[TRAP]` `[NUM]`
2.17.7 Hash partitioning prunes only for equality, not for ranges or inequalities — so hash is for
       spreading write hot spots, and range is for time-based lifecycle.
       `[RESEARCH]` `[PROVE]`
2.17.8 The limitation that decides your keys: **a primary key or unique constraint on a partitioned
       table must include the partition key**. So `ledger_entry` partitioned by `posted_at` cannot
       have a global `UNIQUE (id)` — it gets `UNIQUE (id, posted_at)`, and every FK and lookup must
       carry the date. This is the single biggest design consequence and it must be stated early.
       `[RESEARCH]` `[PROVE]` `[TRAP]` `[SOURCE]`
2.17.9 Other limitations, current as of PG 18: no `CREATE INDEX CONCURRENTLY` directly on a
       partitioned table (build per-partition then attach), foreign keys *to* a partitioned table
       supported only from PG 12, no automatic partition creation (hence `pg_partman` or a cron
       job), no `SPLIT`/`MERGE` partition commands, `ATTACH PARTITION` validating the constraint under
       `ACCESS EXCLUSIVE` unless a matching `CHECK` already exists, and `DETACH PARTITION
       CONCURRENTLY` requiring only `SHARE UPDATE EXCLUSIVE`.
       `[RESEARCH]` `[VERSION-TRAP]` `[NUM]`
2.17.10 The `ATTACH` trick that makes it online: add a `CHECK` constraint matching the partition bound
        *before* attaching, so the validation scan is skipped. This is the difference between a
        second and an hour. `[PROVE]` `[SQL]` `[NUM]`
2.17.11 Partition maintenance as an operational routine: pre-create next month, `DETACH CONCURRENTLY`
        + archive + `DROP` the month leaving the 90-day window, and the monitoring that alerts when
        the next partition does not exist (rows landing in `DEFAULT`, or an insert error).
        `[DIAG]` `[NUM]`
2.17.12 `VACUUM ONLY` / `ANALYZE ONLY` — **new in PG 18**, because 18 changed the default to process
        inheritance children. A maintenance script written for 17 now vacuums 84 partitions when it
        meant one. `[RESEARCH]` `[VERSION-TRAP]` `[TRAP]`
2.17.13 Planning cost of many partitions: the planner considers every partition until pruning, so
        thousands of partitions inflate planning time measurably. State the practical ceiling and the
        trade against partition size. `[NUM]` `[PROVE]`
2.17.14 The pre-declarative history you will still meet: `INHERITS` plus `CHECK` constraints plus
        triggers, and constraint exclusion (`constraint_exclusion = partition`). The wiki says don't
        use table inheritance for new work. `[SOURCE]` `[VERSION-TRAP]`
2.17.15 MySQL partitioning contrast: `PARTITION BY RANGE/LIST/HASH/KEY`, all partitions must be in the
        same storage engine, the same "unique keys must include the partition key" rule,
        `ALTER TABLE ... EXCHANGE PARTITION`, and no partitioning of tables with foreign keys.
        `[MYSQL]` `[NUM]`
2.17.16 Sharding: the key choice, routing (application-side, proxy, or middleware), rebalancing, and
        the two operations that become hard — cross-shard joins and cross-shard transactions.
        `[X-REF 22]`
2.17.17 **Why the QuizStakes ledger resists sharding**, quoted: §15.6 "the ledger resists sharding
        because of cross-position invariants", and Appendix B.5 "cross-position invariants resist
        sharding. The bottleneck is architectural." A shard boundary between a client's cash and
        bonus positions would make the sum-to-zero invariant a distributed transaction.
        `[SOURCE]` `[PROVE]`
2.17.18 The shard key that *would* work and its cost: `client_id`, giving per-client transactional
        integrity and creating §15.3's "putting the whale's entire history on one partition" hot spot,
        plus §15.6's rebalancing problem when 3 instances become 4.
        `[SOURCE]` `[X-REF 22]`
2.17.19 Hot partitions, quantified: §15.3 "one popular round settling ten thousand stakes at once"
        and Appendix A.2's 3,400/sec settlement burst — a single round id concentrating writes. The
        mitigations (key salting, buffering, batching the settlement) and their costs.
        `[SOURCE]` `[NUM]` `[X-REF 22]`
2.17.20 Citus/Vitess/CockroachDB named as the "someone else does the sharding" options, with the one
        constraint each imposes on your schema. `[X-REF 22]` `[RESEARCH]`
2.17.21 Archival as the alternative to sharding for a growth problem: cold columnar storage that is
        "still queryable" (Appendix B.2) via partition detach-and-archive plus a foreign table, so
        the hot table stays 90 days. `[SOURCE]` `[NUM]`

*(21 leaves)*

## §2.18 Vacuum, bloat and the maintenance you cannot skip

2.18.1 Why bloat exists at all: PostgreSQL's MVCC keeps old row versions in the heap, so an `UPDATE`
       writes a new tuple and leaves the old one dead. Space is reclaimed for **reuse**, not returned
       to the OS. `[PROVE]`
2.18.2 What `VACUUM` does, step by step: scan (or use the visibility map to skip), collect dead
       tuple ids, remove matching index entries, mark heap line pointers reusable, update the
       free-space map and visibility map, advance `relfrozenxid`, and update statistics counters.
       `[FLOW]` `[PROVE]`
2.18.3 `VACUUM` vs `VACUUM FULL` vs `CLUSTER` vs `pg_repack` vs PG 19's `REPACK`: the first reclaims
       for reuse and is online; the next two rewrite the table under `ACCESS EXCLUSIVE` and need
       double the disk; `pg_repack`/`REPACK` rewrite online. **Never `VACUUM FULL` a live table.**
       `[NUM]` `[TRAP]` `[RESEARCH]`
2.18.4 Autovacuum's trigger arithmetic, with every constant: vacuum when
       `n_dead_tup > autovacuum_vacuum_threshold (50) + autovacuum_vacuum_scale_factor (0.2) ×
       reltuples`, capped by **`autovacuum_vacuum_max_threshold` = 100,000,000** (a newer parameter);
       insert-triggered vacuum via `autovacuum_vacuum_insert_threshold` (**1000**) +
       `autovacuum_vacuum_insert_scale_factor` (**0.2**); analyze when
       `n_mod_since_analyze > 50 + 0.1 × reltuples`. `[GUC]` `[NUM]` `[SOURCE]`
       `[RESEARCH]`
2.18.5 Prove the consequence on the QuizStakes ledger: 0.2 × 7.2B = **1.44 billion** dead tuples
       before the default threshold fires — and even the 100M cap is 100M. Per-table overrides are
       mandatory, not optional. `[NUM]` `[PROVE]` `[SOURCE]`
2.18.6 Autovacuum worker settings: `autovacuum` (**on**), `autovacuum_max_workers` (**3**),
       **`autovacuum_worker_slots` (16, new in PG 18, resizable at runtime)**,
       `autovacuum_naptime` (**1min**), `autovacuum_vacuum_cost_delay` (**2 ms**),
       `autovacuum_vacuum_cost_limit` (**-1**, inheriting `vacuum_cost_limit` = 200), and the cost
       accounting (`vacuum_cost_page_hit` 1, `_miss` 2 (10 pre-14), `_dirty` 20).
       `[GUC]` `[NUM]` `[RESEARCH]`
2.18.7 The cost-delay arithmetic that explains "autovacuum never finishes": at the default limit and
       delay, autovacuum's throughput ceiling is a few MB/s — far below the 1.3 TB/year ledger's
       churn. Show the calculation and the tuned values. `[NUM]` `[PROVE]`
2.18.8 **Long-running transactions are the enemy of vacuum.** Vacuum cannot remove a tuple any
       snapshot might still see, so one `idle in transaction` connection stops cleanup across the
       *whole database*. An idle-in-transaction session can bloat a table until the disk fills.
       `[PROVE]` `[TRAP]` `[SOURCE]`
2.18.9 The other three things that hold back the horizon, which people forget: an abandoned
       **replication slot**, a **prepared transaction**, and `hot_standby_feedback` from a standby
       running a long query. The query that shows all four at once
       (`pg_stat_activity.backend_xmin`, `pg_replication_slots.xmin`, `pg_prepared_xacts`).
       `[SQL]` `[DIAG]` `[PROVE]`
2.18.10 Measuring bloat honestly: `pgstattuple` (accurate, expensive), the estimation queries from
        `pg_class`/`pg_stats` (fast, approximate), `pg_stat_user_tables.n_dead_tup`, and
        `pg_stat_progress_vacuum` for a run in flight. `[SQL]` `[DIAG]`
2.18.11 Index bloat versus table bloat, and why an index can bloat while its table does not
        (right-growing indexes, `HOT` updates missing, deleted key ranges).
        `[PROVE]`
2.18.12 **Transaction ID wraparound**, the outage: XIDs are 32-bit, so the visible space is ~2 billion
        (`2^31`); vacuum must **freeze** old tuples to keep them visible. `autovacuum_freeze_max_age`
        (**200,000,000**) triggers an anti-wraparound vacuum that cannot be skipped or cancelled
        safely; `vacuum_freeze_min_age` (**50,000,000**),
        `vacuum_freeze_table_age` (**150,000,000**),
        `autovacuum_multixact_freeze_max_age` (**400,000,000**). At the wraparound limit PostgreSQL
        **stops accepting writes** and the database is read-only until a manual vacuum completes.
        `[NUM]` `[SOURCE]` `[RESEARCH]` `[PROVE]`
2.18.13 The real incidents to cite: Sentry's write outage when autovacuum could not keep up with
        freezing, and Figma's January 2020 disruption where a long-running query produced a vacuum
        backlog that crossed into aggressive anti-wraparound vacuuming with a heavier locking and
        write impact. Both are public postmortems and both are the same mechanism.
        `[RESEARCH]` `[SOURCE]` `[DIAG]`
2.18.14 Monitoring wraparound: `age(relfrozenxid)` per table and `datfrozenxid` per database against
        `autovacuum_freeze_max_age`, the alert threshold, and the emergency procedure (find and kill
        the blocker, then `VACUUM (FREEZE, VERBOSE)` the worst tables, in single-user mode if
        necessary). `[SQL]` `[DIAG]` `[RESEARCH]`
2.18.15 Why the QuizStakes ledger is unusually *safe* from wraparound and unusually exposed to bloat:
        it is append-only (invariant #7), so there are almost no dead tuples from updates — but
        `position` (updated on every movement) and `reservation` (state transitions) are the opposite,
        and `reservation` rows live "seconds to hours" (Appendix A.6). Point the tuning at those two
        tables. `[SOURCE]` `[PROVE]` `[NUM]`
2.18.16 `VACUUM` options: `FULL`, `FREEZE`, `VERBOSE`, `ANALYZE`, `DISABLE_PAGE_SKIPPING`,
        `SKIP_LOCKED`, `INDEX_CLEANUP {AUTO|ON|OFF}`, `PROCESS_TOAST`, `TRUNCATE`,
        `PARALLEL n`, `BUFFER_USAGE_LIMIT` (PG 16), `ONLY` (PG 18).
        `[SQL]` `[RESEARCH]` `[VERSION-TRAP]`
2.18.17 PG 19's autovacuum changes worth flagging for the write pass: parallel autovacuum workers
        (`autovacuum_max_parallel_workers`) and a scoring system that prioritises tables — which
        changes the tuning advice this section gives.
        `[RESEARCH]` `[VERSION-TRAP]`
2.18.18 **InnoDB's equivalent problem, differently shaped**: old versions live in the **undo log**, a
        purge thread (`innodb_purge_threads`, default 4) removes them, and a long transaction grows
        the **history list length** instead of bloating the table. `SHOW ENGINE INNODB STATUS`'s
        "History list length" is the metric, `innodb_max_undo_log_size` and undo truncation
        (`innodb_undo_log_truncate`) are the controls, and the failure mode is a growing undo
        tablespace plus slow reads that must walk long version chains — not wraparound.
        `[MYSQL]` `[NUM]` `[PROVE]` `[DIAG]`
2.18.19 The maintenance runbook the bible must ship: what to check daily (bloat ratio on the top ten
        tables, oldest transaction, oldest slot, `age(relfrozenxid)` max), weekly (unused indexes,
        `pg_stat_statements` top 20), and per release (index redundancy, partition pre-creation).
        `[DIAG]` `[X-REF 20]`

*(19 leaves)*

## §2.19 Schema migrations and online DDL

2.19.1 The constraint that makes this hard: during a rolling deploy **old and new application versions
       run simultaneously**, so every migration must be compatible with both — which means no
       migration may be a single atomic swap. `[PROVE]`
2.19.2 **Expand / contract**, the four phases with the deployment boundary between each: (1) expand —
       add the nullable column/new table, deploy code that writes both; (2) backfill in batches;
       (3) migrate reads — deploy code that reads the new column; (4) contract — stop writing the
       old, and drop it in a *later* release. `[FLOW]` `[PROVE]`
2.19.3 The three things you must never do, with the exact failure: rename a column in one step (old
       pods break instantly), drop a column in the same release that stops using it (a rollback
       breaks), and add a `NOT NULL` column with a default on an engine that rewrites the table.
       `[TRAP]`
2.19.4 The default-value history that is now safe: PostgreSQL **11+** and MySQL **8.0+** add a column
       with a constant default as a catalog-only change (the value is materialised on read); a
       *volatile* default still rewrites. State the version boundary, because pre-11 advice is still
       widely repeated. `[VERSION-TRAP]` `[NUM]` `[PROVE]`
2.19.5 **The lock queue is the mechanism people miss**: PostgreSQL lock acquisition is FIFO, so a
       DDL statement waiting for `ACCESS EXCLUSIVE` blocks *every* subsequent query behind it —
       including plain `SELECT`s that would not have conflicted with the running query. The table is
       effectively down while the DDL waits. This specific pattern takes whole services offline.
       `[RESEARCH]` `[SOURCE]` `[PROVE]` `[TRAP]`
2.19.6 The fix is two settings, always, on every migration: `SET lock_timeout = '3s'` (fail fast
       rather than queue) and a bounded retry loop; plus `statement_timeout` for the operation
       itself. Show the migration preamble. `[GUC]` `[SQL]` `[PROVE]`
2.19.7 The DDL-to-lock map, as the operational table: `ACCESS EXCLUSIVE` for `DROP COLUMN`,
       `ALTER COLUMN TYPE`, `SET NOT NULL` (pre-12), non-concurrent `CREATE INDEX`, `TRUNCATE`,
       `VACUUM FULL`, `CLUSTER`, and most `ALTER TABLE`; `SHARE ROW EXCLUSIVE` for
       `ADD FOREIGN KEY`; `SHARE UPDATE EXCLUSIVE` for `ADD COLUMN` (nullable, constant default),
       `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`, `DETACH PARTITION CONCURRENTLY`,
       `ANALYZE`, and plain `VACUUM`. `[RESEARCH]` `[SOURCE]` `[NUM]`
2.19.8 `CREATE INDEX CONCURRENTLY`: two table passes, waits for all older transactions, cannot run
       inside a transaction block, cannot be used on a partitioned table directly, and leaves an
       `INVALID` index on failure that you must drop and retry. Same for
       `REINDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY`. `[NUM]` `[TRAP]`
2.19.9 The safe two-step patterns, each written out: `NOT NULL` via `CHECK ... NOT VALID` +
       `VALIDATE` (or PG 18's named `NOT NULL ... NOT VALID`); FK via `ADD CONSTRAINT ... NOT VALID`
       + `VALIDATE CONSTRAINT`; type change via a new column + backfill + swap;
       column rename via add + dual-write + drop; unique constraint via
       `CREATE UNIQUE INDEX CONCURRENTLY` + `ALTER TABLE ... ADD CONSTRAINT ... USING INDEX`.
       `[SQL]` `[RESEARCH]` `[PROVE]`
2.19.10 Backfill discipline: batched by key range, committing per batch, with a bounded rate, a
        resumable cursor, and a check that autovacuum and replicas keep up. A single `UPDATE` over
        600M ledger rows locks, bloats and floods WAL. `[NUM]` `[PROVE]`
2.19.11 MySQL's online DDL model: `ALGORITHM = {INSTANT | INPLACE | COPY}` and
        `LOCK = {NONE | SHARED | EXCLUSIVE}`, the instant-DDL operation list (add column at the end,
        rename, add/drop virtual column, modify enum), the metadata lock (MDL) that still requires a
        moment of exclusivity, and `innodb_online_alter_log_max_size` overflow aborting a long
        `INPLACE` alter. `[MYSQL]` `[NUM]` `[RESEARCH]`
2.19.12 The MySQL external tools and exactly how they work: `pt-online-schema-change` (shadow table +
        triggers + chunked copy + atomic rename) and `gh-ost` (shadow table + **binlog** tailing
        instead of triggers, so no write amplification on the original). State the trade — triggers
        add latency to every write; binlog tailing adds lag and requires row-based binlog.
        `[MYSQL]` `[PROVE]`
2.19.13 PostgreSQL's equivalents: `pg_repack` for a bloat rewrite, `pgroll`/`Reshape` for versioned
        expand-contract with views, and PG 19's `REPACK`. `[RESEARCH]`
2.19.14 Migration tooling at the SQL layer: Flyway (versioned + repeatable, `flyway_schema_history`,
        checksums, out-of-order, baseline) and Liquibase (changelogs, preconditions, rollback), plus
        the two rules that matter more than the tool — migrations are **immutable once applied**, and
        every migration must be forward-only with a separately-written revert.
        `[X-REF 08]`
2.19.15 Transactional migrations: PostgreSQL wraps each migration in a transaction so a failure
        leaves nothing behind — *except* for `CREATE INDEX CONCURRENTLY`, which must be marked
        non-transactional. MySQL cannot do this at all, so a failed multi-statement migration leaves
        a half-migrated schema you must repair by hand. `[MYSQL]` `[PROVE]` `[TRAP]`
2.19.16 Testing migrations: run them against a production-sized snapshot to measure duration and lock
        time, assert the resulting schema matches the ORM's expectation, and rehearse the rollback.
        `[X-REF 16]`
2.19.17 The QuizStakes migration that is genuinely hard: §15.3's "`AgreementVersionPublished` adds a
        required field; in-flight journeys hold the old shape". The bible must walk the expand/contract
        for it including what happens to applications sitting at `AO-200` during the deploy.
        `[SOURCE]` `[PROVE]`
2.19.18 Data migrations versus schema migrations: a data migration is a business operation with an
        audit trail (and in a regulated system, an approval), not a `flyway` script. Say so.
        `[SOURCE]`

*(18 leaves)*

## §2.20 Performance work as a procedure

2.20.1 The procedure, ordered, because ad-hoc tuning is how people waste weeks: (1) establish the
       symptom and its SLO (Appendix A.7 gives real budgets); (2) find the top offenders in
       `pg_stat_statements` by **total** time, not mean; (3) get a plan with `auto_explain`;
       (4) classify the cause (estimate, access path, I/O, lock, spill, round trips); (5) apply the
       narrowest fix; (6) verify in production with the same metric; (7) write down the number.
       `[FLOW]` `[PROVE]`
2.20.2 Rank by `total_exec_time`, not `mean_exec_time`: a 2 ms query called 40M times a day is a
       bigger problem than a 4-second report run twice. Show the QuizStakes arithmetic — the 30 ms
       restriction decision sits on every money path, so "every millisecond is paid on every money
       action in the system". `[SOURCE]` `[NUM]` `[PROVE]`
2.20.3 The slow-query log done right: `log_min_duration_statement` (start at 1000 ms, then lower),
       `log_min_duration_sample` + `log_statement_sample_rate` for high-volume statements,
       `log_parameter_max_length`, `log_lock_waits`, `log_temp_files` (**-1**; set to 0 to catch every
       spill), `log_autovacuum_min_duration`, and `log_line_prefix` including
       `%a %u %d %p %x` so a line is attributable. `[GUC]` `[NUM]` `[DIAG]`
2.20.4 MySQL's equivalents: the slow query log with `long_query_time`,
       `log_queries_not_using_indexes`, `min_examined_row_limit`, `pt-query-digest`, and
       `performance_schema.events_statements_summary_by_digest`. `[MYSQL]` `[DIAG]`
2.20.5 Attribution by wait event: use `pg_stat_activity`'s `wait_event_type`/`wait_event` sampled over
       time (or `pg_wait_sampling`/`pgsentinel`) to say whether time went to CPU, I/O, a lock, or an
       `LWLock`. This is the difference between "the query is slow" and "the query waits".
       `[RESEARCH]` `[DIAG]` `[PROVE]`
2.20.6 Cache-hit ratio and why it is a weak metric: `blks_hit / (blks_hit + blks_read)` ignores the OS
       page cache, so a 99% ratio can coexist with heavy I/O. Use `pg_stat_io` (PG 16+) and
       `Buffers:` in plans instead. `[NUM]` `[TRAP]`
2.20.7 The seven causes of a slow query, as a classification with the diagnostic for each: bad
       estimate, wrong access path, too much I/O, lock wait, spill to disk, too many round trips,
       and "the query is fine, the server is saturated". `[FLOW]` `[DIAG]`
2.20.8 Server-level parameters that actually move the needle, with defaults and how to set them:
       `shared_buffers` (**128MB**; 25% of RAM), `effective_cache_size` (**4GB**; ~75% of RAM),
       `work_mem` (**4MB**), `maintenance_work_mem` (**64MB**), `random_page_cost` (**4.0**; lower
       to ~1.1 on SSD/NVMe), `seq_page_cost` (**1.0**), `effective_io_concurrency` (**16 in PG 18**,
       was 1), `maintenance_io_concurrency` (**16**), `max_wal_size` (**1GB**),
       `checkpoint_timeout` (**5min**), `checkpoint_completion_target` (**0.9**),
       `default_statistics_target` (**100**), `jit` (**on**) and `jit_above_cost` (**100000**).
       `[GUC]` `[NUM]` `[RESEARCH]`
2.20.9 **`random_page_cost = 4.0` encodes spinning rust.** On NVMe the true ratio is close to 1, so
       leaving the default systematically biases the planner toward seq scans. This is the
       highest-value single parameter change on modern hardware, and it must be argued with the cost
       model (§3.11), not asserted. `[PROVE]` `[NUM]`
2.20.10 PG 18's AIO subsystem as a performance lever: `io_method` (`worker` everywhere, `io_uring` on
        Linux, `sync` to disable), `io_combine_limit` (**16**), `io_max_combine_limit` (**256**),
        `io_workers`, and the `pg_aios` view; up to ~3× improvement on sequential and bitmap heap
        scans and vacuum. This changes the "seq scans are slow" intuition.
        `[RESEARCH]` `[VERSION-TRAP]` `[GUC]` `[NUM]`
2.20.11 JIT as a footgun: enabled by default above a cost threshold, and on a query with a badly
        overestimated cost it adds compilation time to a query that then runs in milliseconds.
        Turning `jit = off` has fixed real latency regressions. `[GUC]` `[TRAP]`
        `[PROVE]`
2.20.12 Benchmarking honestly: `pgbench` (built-in, custom scripts, `-M prepared`), `sysbench`, and
        the rules — warm the cache, run long enough to cross a checkpoint, report percentiles not
        means, and change one thing at a time. `[X-REF 16]`
2.20.13 The latency budget as the target, not "faster": Appendix A.7's numbers — 30 ms restriction
        decision, 80 ms balance read, 150 ms stake reservation, 4 s card deposit end to end, and the
        **hard 500 ms self-exclusion**. Every tuning decision in the bible should be evaluated against
        one of these. `[SOURCE]` `[NUM]`
2.20.14 Tail latency: p99 is where checkpoints, autovacuum, lock waits and plan flips show up, so a
        mean-based dashboard hides every problem in this guide. §15.6: "card deposits average 300ms;
        p99 is 12s; those clients complain." `[SOURCE]` `[X-REF 20]`
2.20.15 When to stop tuning and change the design: when the cost is inherent (a 7.2B-row scan), when
        the bottleneck is human (§15.6's operator queue — "autoscaling is meaningless"), or when the
        write path is a single serialisation point by invariant. Naming this prevents infinite tuning.
        `[SOURCE]` `[PROVE]`

*(15 leaves)*

## §2.21 Views, copies, snapshots and lifetime

The distinction that causes silent data bugs, applied to every SQL-layer construct.

2.21.1 The taxonomy: a **view** re-executes (always current), a **materialized view** is a copy
       (stale from the moment it is refreshed), a **snapshot** is a consistent point-in-time read
       (a transaction), and a **result set** is a copy already detached from the database.
       `[PROVE]`
2.21.2 A `ResultSet` is a copy: the rows you hold in Java may already be wrong, and holding them
       across a transaction boundary makes "check then act" a race. This is the SQL-layer statement
       of the same bug the ORM's detached entities cause. `[JDBC]` `[X-REF 08]`
2.21.3 A read-committed transaction is a *sequence* of snapshots, so two `SELECT`s in one transaction
       can disagree — the "read skew" anomaly, and the reason a multi-statement report needs
       `REPEATABLE READ`. `[PROVE]` `[TRAP]`
2.21.4 A repeatable-read transaction is one snapshot: consistent, and increasingly stale as it runs —
       and it holds back vacuum for its whole life (§2.18.8). Both properties come from the same
       mechanism. `[PROVE]`
2.21.5 `SELECT ... FOR UPDATE` upgrades a read to a *reservation*: the value you read is guaranteed
       not to change under you. This is the only read whose result is still true when you write.
       `[PROVE]`
2.21.6 A cursor is a snapshot plus a position; `WITH HOLD` makes it survive commit by materialising
       the remaining rows — which is a copy, with the memory cost that implies.
       `[NUM]` `[TRAP]`
2.21.7 A replica read is a *lagged* snapshot; a `BalanceView` read is a lagged copy of a lagged
       snapshot. The QuizStakes rule follows directly: neither may authorise a money movement
       (§14.2 invariant 12, Appendix C.5 "Authority: **None**").
       `[SOURCE]` `[PROVE]`
2.21.8 The bug table this section exists to produce: for each of the seven constructs above, the
       wrong belief, the symptom in production, and the fix. `[TRAP]`
2.21.9 The rule to carry away: **any value you intend to write based on must be read inside the same
       transaction as the write, and either locked or re-validated in the write predicate.** Every
       correct money path in QuizStakes obeys it. `[PROVE]` `[SOURCE]`

*(9 leaves)*

## §2.22 The anti-pattern catalogue

One entry per line: the pattern, the symptom, the fix. Every `**Trap:**` in the current guide maps
to one of these and must survive.

2.22.1 A `WHERE` predicate on the outer table of a `LEFT JOIN`. `[TRAP]`
2.22.2 `NOT IN` with a nullable subquery. `[TRAP]`
2.22.3 `<>` on a nullable column expecting NULL rows to survive. `[TRAP]`
2.22.4 `= NULL` instead of `IS NULL`. `[TRAP]`
2.22.5 An alias used in `HAVING` or `WHERE`. `[TRAP]`
2.22.6 `SUM` over zero rows rendered as a balance without `COALESCE`. `[TRAP]`
2.22.7 `SELECT`-then-`INSERT` to prevent duplicates. `[TRAP]`
2.22.8 Read-modify-write for a balance instead of `SET balance = balance - :amount`. `[TRAP]`
2.22.9 A retry loop that does not re-read. `[TRAP]`
2.22.10 `OFFSET` pagination on a growing table. `[TRAP]`
2.22.11 Pagination without a unique tiebreaker. `[TRAP]`
2.22.12 `LIMIT` without `ORDER BY`. `[TRAP]`
2.22.13 A function wrapped around an indexed column. `[TRAP]`
2.22.14 `BETWEEN` on a timestamp range. `[TRAP]`
2.22.15 `timestamp` instead of `timestamptz`. `[TRAP]`
2.22.16 `float`/`double`/`money` for money. `[TRAP]`
2.22.17 `char(n)` and arbitrary `varchar(n)` limits. `[TRAP]`
2.22.18 `SERIAL` instead of an identity column. `[TRAP]`
2.22.19 `integer` for a high-volume surrogate key. `[TRAP]`
2.22.20 Random UUIDv4 as a clustered/primary key on a hot insert table. `[TRAP]`
2.22.21 An EAV table instead of typed columns. `[TRAP]`
2.22.22 JSONB for data you filter, join and constrain on. `[TRAP]`
2.22.23 A stored derived total alongside the entries that produce it. `[TRAP]`
2.22.24 `SELECT *` in application code and in views. `[TRAP]`
2.22.25 `NATURAL JOIN`. `[TRAP]`
2.22.26 An unindexed foreign-key child column in PostgreSQL. `[TRAP]`
2.22.27 More indexes than the write path can afford. `[TRAP]`
2.22.28 Redundant indexes with the same leading columns. `[TRAP]`
2.22.29 `VACUUM FULL` on a live table. `[TRAP]`
2.22.30 Default autovacuum thresholds on a billion-row table. `[TRAP]`
2.22.31 A long-running or `idle in transaction` session left open. `[TRAP]`
2.22.32 Network I/O inside a transaction. `[TRAP]`
2.22.33 A DDL statement with no `lock_timeout`. `[TRAP]`
2.22.34 A single-statement backfill over hundreds of millions of rows. `[TRAP]`
2.22.35 Renaming or dropping a column in one release. `[TRAP]`
2.22.36 A pool sized so `instances × pool_size > max_connections`. `[TRAP]`
2.22.37 `maxLifetime` longer than the server or proxy idle timeout. `[TRAP]`
2.22.38 A thread that needs two connections from a pool sized for one. `[TRAP]`
2.22.39 A session-scoped advisory lock or `SET` on a pooled connection. `[TRAP]`
2.22.40 Reading your own write from a replica. `[TRAP]`
2.22.41 Async replication for money with a promise of no data loss. `[TRAP]`
2.22.42 An abandoned replication slot or prepared transaction. `[TRAP]`
2.22.43 A partitioned table queried without the partition key. `[TRAP]`
2.22.44 A unique constraint that omits the partition key and is therefore not global. `[TRAP]`
2.22.45 `COUNT(*)` for a total on every page of a large list. `[TRAP]`
2.22.46 `setFetchSize` without `autoCommit = false` on PostgreSQL. `[TRAP]`
2.22.47 JDBC batching without `reWriteBatchedInserts`. `[TRAP]`
2.22.48 Autocommit inside a bulk insert loop. `[TRAP]`
2.22.49 `ResultSet.getInt` on a nullable money column. `[TRAP]`
2.22.50 String-concatenated SQL. `[TRAP]`
2.22.51 An application connecting as a superuser or the schema owner. `[TRAP]`
2.22.52 RLS as a substitute for an authorisation service. `[TRAP]`
2.22.53 Trusting `information_schema` for PostgreSQL-specific metadata. `[TRAP]`
2.22.54 `EXPLAIN ANALYZE` run on a write statement outside a rolled-back transaction. `[TRAP]`
2.22.55 Reading a plan by node type before checking estimate versus actual. `[TRAP]`
2.22.56 Averaging away the p99. `[TRAP]`
2.22.57 Ranking slow queries by mean instead of total time. `[TRAP]`
2.22.58 Forcing a plan with `enable_*` flags in production. `[TRAP]`
2.22.59 Believing `Seconds_Behind_Source` in MySQL. `[TRAP]` `[MYSQL]`
2.22.60 `INSERT IGNORE` / `REPLACE INTO` used as an upsert. `[TRAP]` `[MYSQL]`
2.22.61 Relying on MySQL's `GROUP BY` without `ONLY_FULL_GROUP_BY`. `[TRAP]` `[MYSQL]`
2.22.62 Assuming `REPEATABLE READ` means the same thing in both engines. `[TRAP]` `[MYSQL]`
2.22.63 Assuming the textbook anomaly table describes your database. `[TRAP]`
2.22.64 Using `SERIALIZABLE` without a retry loop. `[TRAP]`
2.22.65 Treating a deadlock as a bug rather than a retryable event. `[TRAP]`
2.22.66 More than 64 subtransactions/savepoints per transaction. `[TRAP]`
2.22.67 A `CHECK` constraint on a nullable column believed to be an invariant. `[TRAP]`
2.22.68 Cross-schema joins in a schema-per-service system. `[TRAP]` `[SOURCE]`
2.22.69 A cache as the correctness mechanism for idempotency. `[TRAP]` `[SOURCE]`
2.22.70 Caching a restriction decision. `[TRAP]` `[SOURCE]`

*(70 leaves)*

## §2.23 When not to use a relational database

2.23.1 The workloads a row-store OLTP engine is genuinely bad at, each with the alternative and the
       cost of adopting it: full-text relevance search at scale, wide-column time-series at high
       cardinality, analytical scans over billions of rows, blob storage, graph traversal beyond a
       few hops, ephemeral high-churn state, and pub/sub fan-out. `[X-REF 22]`
2.23.2 The QuizStakes decisions that go the other way, from Appendix B.2, each with its stated
       rationale: document images → object storage ("large binaries never belong in a database"),
       `ApplicationHistory` → append-only wide-column **or** a relational partition (marked
       **contested** — the only contested row in the table), ledger archive → cold columnar "still
       queryable", session state → in-memory cache, idempotency keys → cache **backed by a unique DB
       constraint**. `[SOURCE]` `[PROVE]`
2.23.3 The decision procedure to state once: what are the access patterns, what invariants must hold
       atomically, what is the write rate, what is the retention, and what is the consistency
       requirement *per operation*. Only then pick a store. `[X-REF 22]`
2.23.4 The honest counter-argument to premature polyglot persistence: every additional store is a
       second consistency problem, a second failure domain, a second operational skill set, and a
       reconciliation job. QuizStakes already has four reconciliations (§14.3) for the stores it has.
       `[SOURCE]` `[PROVE]`
2.23.5 What "NoSQL is faster" actually means when it is true (no joins, no constraints, no
       multi-key transactions — you moved the work to the application) and when it is false (a
       single-key read from an indexed relational table is already a single index lookup).
       `[PROVE]` `[TRAP]`
2.23.6 Where PostgreSQL is a legitimate substitute for a specialised store, with the boundary: JSONB
       for documents, `pg_trgm`/FTS for search, `pgvector` for embeddings, arrays and ranges,
       `LISTEN`/`NOTIFY` and `SKIP LOCKED` for queues, BRIN plus partitioning for time-series, and
       `ltree`/recursive CTEs for hierarchies. State when each stops being enough.
       `[RESEARCH]` `[X-REF 22]`
2.23.7 The migration path off, when you do need it: dual-write behind a feature flag, backfill,
       shadow-read comparison, then cut over — the same expand/contract shape as §2.19.
       `[PROVE]`

*(7 leaves)*

## §2.24 Version history and the stale-answer sweep

2.24.1 The PostgreSQL feature timeline worth reciting, with the release: 9.1 SSI and synchronous
       replication and extensions; 9.2 index-only scans and JSON and cascading replication; 9.3
       materialized views and lateral joins and updatable FDW; 9.4 JSONB and logical decoding and
       `REFRESH ... CONCURRENTLY`; 9.5 upsert and BRIN and grouping sets and row-level security;
       9.6 parallel query and multi-column extended statistics groundwork; 10 declarative
       partitioning, logical replication, identity columns, WAL-logged hash indexes; 11 stored
       procedures, JIT, `ADD COLUMN` with a default without a rewrite, covering indexes with
       `INCLUDE`; 12 CTE inlining, generated columns, `REINDEX CONCURRENTLY`, pluggable table AM;
       13 B-tree deduplication, incremental sort, parallel vacuum of indexes; 14 `Memoize`, cycle and
       search clauses, expression statistics; 15 `MERGE`, `UNIQUE NULLS NOT DISTINCT`, security
       invoker views; 16 `pg_stat_io`, logical replication from a standby; 17 incremental backup,
       `MERGE ... WHEN NOT MATCHED BY SOURCE`, new vacuum dead-TID store, `pg_wait_events`;
       **18 async I/O, `uuidv7()`, B-tree skip scan, virtual generated columns by default,
       `WITHOUT OVERLAPS` temporal constraints, `OLD`/`NEW` in `RETURNING`, `NOT ENFORCED`
       constraints, `NOT NULL NOT VALID`, `BUFFERS` on by default, checksums on by default,
       OAuth auth, statistics preserved by `pg_upgrade`**.
       `[NUM]` `[RESEARCH]` `[VERSION-TRAP]`
2.24.2 The MySQL timeline: 5.6 online DDL and GTIDs; 5.7 JSON, generated columns, `ONLY_FULL_GROUP_BY`
       by default, native partitioning; 8.0 CTEs, window functions, `SKIP LOCKED`/`NOWAIT`, atomic
       DDL and the transactional data dictionary, histograms, hash joins (8.0.18), `EXPLAIN ANALYZE`,
       instant DDL, multi-valued indexes; **8.4 LTS with changed InnoDB defaults and the removal of
       `mysql_upgrade`, `mysqlpump`, `AUTO_INCREMENT` on floats and `LOW_PRIORITY` in `LOCK
       TABLES`**; **9.7 LTS with the hypergraph optimizer, JSON duality views and Community-Edition
       replication observability**. `[MYSQL]` `[NUM]` `[RESEARCH]`
2.24.3 The SQL standard timeline: SQL-86, SQL-89, SQL-92 (the baseline everyone means by "standard
       SQL"), SQL:1999 (recursive queries, triggers, types), SQL:2003 (window functions, XML,
       `MERGE`), SQL:2008, SQL:2011 (temporal), SQL:2016 (JSON, row pattern matching),
       SQL:2023 (the `JSON` type, SQL/PGQ). `[NUM]` `[RESEARCH]`
2.24.4 **The stale-answer sweep** — fifteen claims that were true once and are now wrong, each to be
       stated with what is true in PG 18 / MySQL 8.4: "RR allows phantoms"; "CTEs are an optimization
       fence"; "a composite index is useless without its leading column"; "always add BUFFERS";
       "adding a column with a default rewrites the table"; "`SERIAL` is how you make an id";
       "PostgreSQL cannot do upsert"; "MySQL has no CTEs or window functions"; "hash indexes are not
       crash-safe"; "`effective_io_concurrency` should be 1"; "you must `ANALYZE` the whole cluster
       after `pg_upgrade`"; "`VACUUM FULL` is how you reclaim space"; "MySQL has no hash join";
       "generated columns are always stored"; "`REPEATABLE READ` is the same in both engines".
       `[VERSION-TRAP]` `[TRAP]` `[PROVE]`
2.24.5 How to check a version-dependent claim in thirty seconds: `SELECT version()`,
       `SHOW ALL`/`pg_settings`, the release-notes page for the exact minor version, and
       `information_schema.sql_features`. Teach the habit, not the facts.
       `[SQL]` `[DIAG]`
2.24.6 Support lifecycle as an engineering constraint: PostgreSQL supports five major versions
       (one per year, EOL after five), MySQL LTS lines get eight years. A cluster on an EOL version is
       a security decision, not an inertia problem. `[NUM]` `[RESEARCH]`
2.24.7 PG 19's shape, so the reader is not surprised in six months: SQL/PGQ, `GROUP BY ALL`,
       `ON CONFLICT DO SELECT`, `REPACK`, parallel autovacuum, `pg_plan_advice`, auto-scaling
       `io_method=worker`, and faster FK-checked inserts. Every one of these changes an answer in
       this guide. `[RESEARCH]` `[VERSION-TRAP]`

*(7 leaves)*

---

**PART 2 total: 10+14+18+15+14+10+12+9+14+9+12+12+11+9+14+17+21+19+18+15+9+70+7+7 = 366 leaves**

---

# PART 3 — UNDER THE HOOD

PART 2 answered "which one and why". PART 3 answers "what does the machine actually do, in which
function, to which byte". Every leaf here names a real page field, a real source file, a real
constant with its value, or a real algorithm with its published name. Nothing in this part may be
written from recall: `[SOURCE]` leaves quote PostgreSQL source (`src/backend/**`, the access-method
`README` files, `pg_stat`/catalog definitions) or MySQL source and reference-manual text, and every
number is stated against **PostgreSQL 18 / MySQL 8.4 LTS with `innodb_page_size = 16384` and
`BLCKSZ = 8192`**. Where a value is build-time (`BLCKSZ`, `RELSEG_SIZE`, `innodb_page_size`) the
leaf says so, because half the "PostgreSQL facts" on the internet are 8 kB-page facts stated as
universals.

The reader's target after PART 3 is not trivia recall. It is the ability to answer "why did this
happen" for the four QuizStakes incidents that recur in this domain: `fundsledger.ledger_entry`
bloating faster than it grows, a `reservation` update path that deadlocks under settlement bursts,
a `cardpayments.transactions` query whose plan flipped overnight, and a replica whose lag went
vertical while its CPU sat idle.

## §3.1 How to read a database's source, and the tools that show you the bytes

3.1.1 The PostgreSQL source-tree map, by directory and what lives there:
      `src/backend/access/{heap,nbtree,brin,gin,gist,hash,spgist,transam,common}`,
      `src/backend/storage/{buffer,ipc,lmgr,smgr,freespace,page,aio}`,
      `src/backend/optimizer/{path,plan,prep,util}`, `src/backend/executor`,
      `src/backend/replication/{logical,walsender.c,walreceiver.c}`,
      `src/backend/commands/vacuum.c`, `src/backend/postmaster/{autovacuum.c,checkpointer.c,
      bgwriter.c,walwriter.c}`. `[SOURCE]`
3.1.2 The `README` files as first-class documentation, and the five worth reading end to end:
      `access/nbtree/README`, `access/transam/README`, `access/heap/README.HOT`,
      `storage/buffer/README`, `optimizer/README`. Each is a design document written by the
      implementer. `[SOURCE]` `[RESEARCH]`
3.1.3 `src/include/pg_config_manual.h` and `src/include/storage/bufpage.h` as the authoritative home
      of `BLCKSZ` (8192), `RELSEG_SIZE` (131072 blocks = 1 GB), `XLOG_BLCKSZ` (8192) and
      `NAMEDATALEN` (64). **This is how you verify a constant instead of trusting a blog.**
      `[SOURCE]` `[NUM]` `[PROVE]`
3.1.4 `doxygen.postgresql.org` as the navigable cross-reference (every struct, every caller), and
      `git log -S<symbol>` as the way to find *why* a constant has its value. `[SOURCE]`
3.1.5 The MySQL equivalents: `dev.mysql.com/doc/dev/mysql-server/latest/` (Doxygen for
      `storage/innobase/**`, `sql/join_optimizer/**`), the InnoDB source layout
      (`storage/innobase/{btr,buf,lock,log,trx,row,page,fsp,srv,dict}`) and the worklog (`WL#`)
      entries that document each feature's design. `[SOURCE]` `[MYSQL]` `[RESEARCH]`
3.1.6 `pageinspect` as the byte-level microscope: `heap_page_items`, `heap_page_item_attrs`,
      `page_header`, `bt_metap`, `bt_page_stats`, `bt_page_items`, `bt_multi_page_stats`,
      `brin_page_items`, `gin_metapage_info`, `fsm_page_contents`. Every §3.2–§3.8 claim can be
      *shown* with these, not asserted. `[SQL]` `[DIAG]`
3.1.7 `pgstattuple` and `pgstatindex` for bloat measurement (`tuple_count`, `dead_tuple_percent`,
      `free_percent`, `avg_leaf_density`, `leaf_fragmentation`), and `pgstattuple_approx` for the
      cheap version that skips all-visible pages. `[SQL]` `[NUM]`
3.1.8 `pg_visibility` (`pg_visibility_map`, `pg_check_frozen`, `pg_check_visible`) as the way to see
      the visibility map's two bits per page rather than reason about them. `[SQL]` `[DIAG]`
3.1.9 `pg_buffercache` (and `pg_buffercache_summary`/`pg_buffercache_usage_counts` in PG 16+) for
      what is actually resident, per relation, with usage counts. `[SQL]` `[RESEARCH]`
3.1.10 `pg_freespacemap`, `pg_walinspect` (`pg_get_wal_record_info`, `pg_get_wal_stats`) and
       `pg_waldump` — reading the WAL stream as records, which is how §3.17 is verified rather than
       described. `[SQL]` `[DIAG]`
3.1.11 The MySQL byte-level tools: `innodb_ruby` (`innodb_space`, `innodb_log`), `innochecksum`,
       `ibd2sdi`, `INFORMATION_SCHEMA.INNODB_*` tables (`INNODB_BUFFER_PAGE`,
       `INNODB_TABLESPACES`, `INNODB_TRX`, `INNODB_METRICS`) and `SHOW ENGINE INNODB STATUS`.
       `[MYSQL]` `[DIAG]`
3.1.12 The discipline for this whole part: a claim about internals is either quoted from source, shown
       with one of the tools above, or labelled a guess. In an interview, "I would check
       `bt_page_stats`" beats a confidently wrong constant. `[PROVE]`

*(12 leaves)*

## §3.2 The PostgreSQL page: a slotted page, field by field

3.2.1 Why a **slotted page** at all: rows are variable-length and must be movable within the page
      without invalidating external references, so external references point at a *slot index*, not
      an offset. Every row-store on disk converges on this design. `[PROVE]`
3.2.2 `PageHeaderData` (`src/include/storage/bufpage.h`), 24 bytes, field by field: `pd_lsn`
      (8 bytes — the LSN of the last WAL record touching this page), `pd_checksum` (2),
      `pd_flags` (2), `pd_lower` (2), `pd_upper` (2), `pd_special` (2), `pd_pagesize_version` (2),
      `pd_prune_xid` (4). `[SOURCE]` `[NUM]`
3.2.3 What each field is *for*, not just its width: `pd_lsn` is the recovery interlock ("do not write
      this page until WAL up to `pd_lsn` is flushed"); `pd_lower`/`pd_upper` bound the free space in
      the middle; `pd_special` marks the AM-specific area at the end; `pd_prune_xid` is the hint that
      opportunistic pruning may be worthwhile. `[PROVE]` `[SOURCE]`
3.2.4 `pd_flags` bits with their names: `PD_HAS_FREE_LINES`, `PD_PAGE_FULL`, `PD_ALL_VISIBLE`.
      `PD_ALL_VISIBLE` is the page-level twin of the visibility-map bit, and the two disagreeing is
      a corruption signal `pg_check_visible` exists to find. `[SOURCE]` `[NUM]`
3.2.5 The line-pointer array: `ItemIdData`, 4 bytes each, three bit-fields — `lp_off` (15 bits),
      `lp_flags` (2 bits), `lp_len` (15 bits). The array grows **forward** from byte 24. `[SOURCE]`
      `[NUM]`
3.2.6 The four `lp_flags` states and their meanings: `LP_UNUSED`, `LP_NORMAL`, `LP_REDIRECT`,
      `LP_DEAD`. `LP_REDIRECT` is the HOT-chain root indirection of §3.4; `LP_DEAD` is the "known
      dead, index entries may still point here" state. `[SOURCE]` `[PROVE]`
3.2.7 Tuples grow **backward** from `pd_special`, so free space is the hole between `pd_lower` and
      `pd_upper`, and "the page is full" means that hole is smaller than the aligned tuple plus one
      line pointer. `[PROVE]` `[NUM]`
3.2.8 `MaxHeapTuplesPerPage` = 291 on an 8 kB build, derived: `(8192 − 24) / (4 + MAXALIGN(23))` =
      `8168 / 28` = 291. Work the arithmetic; do not quote the number. `[PROVE]` `[NUM]` `[SOURCE]`
3.2.9 `PageAddItemExtended` and `PageRepairFragmentation` — the two functions that insert into and
      compact a page, and the fact that compaction requires a **cleanup lock** (a pin count of one),
      which is why a page a cursor is sitting on cannot be defragmented. `[SOURCE]` `[PROVE]`
3.2.10 Page checksums: `pg_checksum_page` over the page with `pd_checksum` zeroed, verified on read
       into shared buffers. **`initdb` enables data checksums by default from PG 18**; before that it
       was `--data-checksums` and most clusters ran without them.
       `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.2.11 What a checksum failure actually looks like and what it does *not* prove: `WARNING: page
       verification failed, calculated checksum X but expected Y`, `ignore_checksum_failure`
       (default `off`), and `pg_stat_database.checksum_failures`. It detects; it never repairs.
       `[DIAG]` `[GUC]` `[TRAP]`
3.2.12 Empty-page representation and `PageIsNew` (a page of all zeroes), and why a new page is legal
       mid-relation after a crash between extension and initialisation. `[PROVE]`
3.2.13 Relation files on disk: segment files of `RELSEG_SIZE` (1 GB), `_fsm`, `_vm` and `_init`
       forks, `pg_relation_filepath()`, and the fact that `fundsledger.ledger_entry` at 1.3 TB/year
       is ~1,300 segment files per year before partitioning. `[NUM]` `[SQL]` `[PROVE]`
3.2.14 The `[DIAG]` exercise this section exists for: dump one real
       `fundsledger.ledger_entry` page with `page_header` + `heap_page_items` and account for all
       8,192 bytes — header, line pointers, hole, tuples, and any special space. `[DIAG]` `[NUM]`
       `[PROVE]`

*(14 leaves)*

## §3.3 The heap tuple: header, alignment, and the byte arithmetic for `ledger_entry`

3.3.1 `HeapTupleHeaderData` field by field: `t_choice` (a union of `t_heap` = `t_xmin` (4),
      `t_xmax` (4), `t_field3`/`t_cid`/`t_xvac` (4) and `t_datum` for in-memory composites),
      `t_ctid` (6 bytes = block number 4 + offset 2), `t_infomask2` (2), `t_infomask` (2),
      `t_hoff` (1). `[SOURCE]` `[NUM]`
3.3.2 The size arithmetic: `SizeofHeapTupleHeader` = **23 bytes**, `MAXALIGN`ed to **24** on a
      64-bit build, so `t_hoff` is 24 with no nulls bitmap. `[PROVE]` `[NUM]`
3.3.3 The nulls bitmap: present only when `HEAP_HASNULL` is set, `ceil(natts/8)` bytes appended to
      the header, then `MAXALIGN` again — so 8 columns cost 1 byte and push `t_hoff` to 32 on a
      64-bit build. **A nullable column is not free.** `[PROVE]` `[NUM]` `[TRAP]`
3.3.4 `t_infomask` bits by name: `HEAP_HASNULL`, `HEAP_HASVARWIDTH`, `HEAP_HASEXTERNAL`,
      `HEAP_HASOID_OLD`, `HEAP_XMAX_KEYSHR_LOCK`, `HEAP_COMBOCID`, `HEAP_XMAX_EXCL_LOCK`,
      `HEAP_XMAX_LOCK_ONLY`, `HEAP_XMIN_COMMITTED`, `HEAP_XMIN_INVALID`, `HEAP_XMAX_COMMITTED`,
      `HEAP_XMAX_INVALID`, `HEAP_XMAX_IS_MULTI`, `HEAP_UPDATED`, `HEAP_MOVED_OFF`, `HEAP_MOVED_IN`.
      `[SOURCE]` `[NUM]`
3.3.5 `HEAP_XMIN_FROZEN` as the *combination* `HEAP_XMIN_COMMITTED | HEAP_XMIN_INVALID` — the trick
      that lets freezing be recorded without a fourth xid field. `[SOURCE]` `[PROVE]`
3.3.6 `t_infomask2` bits: `HEAP_NATTS_MASK` (the low 11 bits — the attribute count, hence the
      1,600-column limit's real origin), `HEAP_KEYS_UPDATED`, `HEAP_HOT_UPDATED`,
      `HEAP_ONLY_TUPLE`. `[SOURCE]` `[NUM]` `[PROVE]`
3.3.7 **Hint bits** as a mechanism, not an implementation detail: the first reader to resolve a
      transaction's fate writes `HEAP_XMIN_COMMITTED`/`HEAP_XMAX_COMMITTED` into the tuple so later
      readers skip the commit-log lookup. This is why a `SELECT` can dirty pages and produce write
      I/O. `[PROVE]` `[TRAP]` `[SOURCE]`
3.3.8 Why hint-bit writes are safe without WAL, and the one interlock that makes them safe: the
      write is idempotent and reconstructible from `pg_xact`, but it may not be set before WAL is
      flushed to the page's `pd_lsn` (the `TransactionIdSetCommitTs`/`XLogNeedsFlush` deferral, and
      the group-of-32 CLOG hint mechanism). `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.3.9 Column alignment: `char`/`bool` = 1, `int2` = 2, `int4`/`date`/`float4` = 4,
      `int8`/`timestamptz`/`float8`/pointer types = 8, and `attalign` in `pg_attribute` as the
      authority. `[SOURCE]` `[NUM]`
3.3.10 **Column-order padding** worked properly: a `(bool, bigint, bool, bigint)` row wastes 14 bytes
       to alignment that `(bigint, bigint, bool, bool)` does not. Show the arithmetic, then show it
       with `pg_column_size` and `heap_page_item_attrs`. `[PROVE]` `[NUM]` `[SQL]`
3.3.11 Varlena headers: 4-byte header for values > 126 bytes (`varattrib_4b`), **1-byte header** for
       short values (`varattrib_1b`, up to 126 bytes), and the 18-byte `varatt_external` TOAST
       pointer. `numeric` and `text` therefore have a variable per-value overhead. `[SOURCE]` `[NUM]`
3.3.12 `numeric` internals: `NumericShort`/`NumericLong`, base-10000 digit groups
       (`NumericDigit` = `int16`), and the resulting sizes — `numeric(18,2)` holding `120.00` is
       far smaller than `numeric` holding a 40-digit value. **This is the cost of the correct money
       type, and it is small.** `[PROVE]` `[NUM]` `[X-REF 01]`
3.3.13 The full byte budget for one `fundsledger.ledger_entry` row: 24 header +
       `entry_id bigint` 8 + `movement_id uuid` 16 + `client_id bigint` 8 + `position` (enum 4 /
       short varlena) + `amount numeric(18,2)` + `currency char(3)` + `created_at timestamptz` 8 +
       `idempotency_key text`, aligned, plus 4 bytes of line pointer. Reconcile the total against
       the domain's stated **~180 bytes/row**. `[NUM]` `[PROVE]` `[SOURCE]`
3.3.14 From bytes/row to the numbers the business quotes: rows per 8 kB page =
       `(8192 − 24) / (180 + 4)` ≈ 44; 19.8M entries/day ≈ 450k pages/day ≈ 3.5 GB/day of heap;
       ×365 ≈ 1.3 TB/year — the figure Appendix A states. **Derive it; do not quote it.**
       `[PROVE]` `[NUM]`
3.3.15 The same arithmetic for the indexes, which is where the surprise is: an `IndexTupleData`
       header is 8 bytes, so a two-column `(client_id, created_at)` B-tree entry is 8 + 8 + 8 = 24
       bytes plus a 4-byte line pointer, at `fillfactor = 90` → ~262 entries/leaf page → ~75k leaf
       pages/day → ~600 MB/day for **one** index. Three indexes cost more than the table.
       `[PROVE]` `[NUM]` `[TRAP]`
3.3.16 `pg_column_size`, `pg_relation_size`, `pg_table_size`, `pg_indexes_size`,
       `pg_total_relation_size` — which one includes TOAST, which includes the FSM/VM forks, and why
       the four never agree. `[SQL]` `[NUM]` `[TRAP]`

*(16 leaves)*

## §3.4 Update in place is a lie: HOT, pruning, line pointers, FSM and the visibility map

3.4.1 The base mechanism: an `UPDATE` is an insert of a new tuple plus a stamp of `t_xmax` on the
      old one, with the old tuple's `t_ctid` pointing forward to the new version — a **version
      chain** in the heap. `[PROVE]` `[SOURCE]`
3.4.2 The cost that follows: every index on the table must gain an entry for the new tuple, even for
      columns that did not change. This is the "write amplification" number that decides whether
      `fundsledger.position` can be updated 1,200 times/second. `[PROVE]` `[NUM]`
3.4.3 **HOT** (`README.HOT`) as the fix, with its exact preconditions: no *indexed* column changed,
      and the new version fits on the same page. If either fails, it is a normal update. `[SOURCE]`
      `[PROVE]`
3.4.4 The two flags that implement it: `HEAP_HOT_UPDATED` on the predecessor and `HEAP_ONLY_TUPLE`
      on the successor, and the invariant that a heap-only tuple has **no index entries pointing at
      it** and is reachable only by following the chain from the root line pointer. `[SOURCE]`
      `[NUM]`
3.4.5 The **root line pointer** and `LP_REDIRECT`: after pruning, the root slot becomes a redirect to
      the surviving version, so index entries stay valid without being rewritten. This is the whole
      trick. `[PROVE]` `[SOURCE]`
3.4.6 **Opportunistic pruning** (`heap_page_prune_opt`): a plain `SELECT` that touches a page whose
      `pd_prune_xid` says pruning may help will shorten HOT chains and defragment the page, taking a
      cleanup lock if it can get one for free. Reads do maintenance. `[SOURCE]` `[PROVE]` `[TRAP]`
3.4.7 Why HOT is not free: chain traversal costs page-local hops, long chains slow every read of that
      row, and `heap_page_items` shows them. `[NUM]` `[DIAG]`
3.4.8 `fillfactor` (heap default **100**, B-tree default **90**) as the knob that makes HOT possible:
      reserving 20–30% of each page is what buys same-page updates for a hot table.
      `[GUC]` `[NUM]` `[PROVE]`
3.4.9 The QuizStakes application: `fundsledger.position` (2.8M reservations/day, 1,200/sec, bursts to
      3,400/sec) is a small, hot, frequently-updated table with few indexed columns — the exact
      shape that wants `fillfactor = 70` and no index on the mutable balance columns.
      `[SQL]` `[NUM]` `[PROVE]`
3.4.10 The counter-case: `fundsledger.ledger_entry` is append-only, so `fillfactor = 100` is right
       and any lower value is pure waste at 1.3 TB/year. Same database, opposite answer.
       `[PROVE]` `[NUM]`
3.4.11 The **Free Space Map** (`_fsm` fork): a three-level tree of one-byte per-page availability
       categories (32-byte granularity), `fsm_page_contents`, `GetPageWithFreeSpace`, and the fact
       that it is **approximate and not crash-critical** — it can be rebuilt. `[SOURCE]` `[NUM]`
3.4.12 Why the FSM is only updated by vacuum (and by `RecordPageWithFreeSpace` on some paths), and
       the consequence: freed space is not reused until vacuum publishes it, which is one half of
       "bloat". `[PROVE]` `[TRAP]`
3.4.13 The **visibility map** (`_vm` fork): **two bits per heap page** —
       `VISIBILITYMAP_ALL_VISIBLE` and `VISIBILITYMAP_ALL_FROZEN` — so one 8 kB VM page covers
       ~32,700 heap pages ≈ 256 MB of heap. Do the arithmetic. `[SOURCE]` `[NUM]` `[PROVE]`
3.4.14 What the VM buys, precisely: **index-only scans** (skip the heap fetch when the page is
       all-visible) and **vacuum page skipping**. This is why a read-heavy `BalanceView` query gets
       dramatically faster right after a vacuum. `[PROVE]` `[PLAN]`
3.4.15 Reading the evidence in a plan: `Heap Fetches: 0` on an `Index Only Scan` means the VM bits
       were set; a large `Heap Fetches` on an "index-only" scan means they were not, and the fix is
       vacuum, not a new index. `[PLAN]` `[TRAP]` `[DIAG]`
3.4.16 `t_ctid` pointing to itself as the end-of-chain marker, and why `ctid` is therefore **not** a
       stable row identifier — the single most common misuse of a physical address as a key.
       `[PROVE]` `[TRAP]`

*(16 leaves)*

## §3.5 TOAST: what happens to a value that does not fit

3.5.1 The constraint that forces TOAST to exist: a tuple may not span pages, so with an 8 kB page the
      largest possible tuple is ~8 kB and PostgreSQL targets **four tuples per page**. `[PROVE]`
      `[NUM]`
3.5.2 `TOAST_TUPLE_THRESHOLD` — the size above which the TOAST machinery engages, documented as
      "normally 2 kB" and computed as `MaximumBytesPerTuple(4)` = **2032 bytes** on an 8 kB build.
      State both, and say which is the code. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.3 `TOAST_MAX_CHUNK_SIZE` — the out-of-line chunk payload, chosen so four chunk rows fit a page
      (~2000 bytes; **1996** in the code on a standard build). Verify against
      `src/include/access/heaptoast.h` before writing a number. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.4 The four per-column storage strategies and exactly what each permits:
      `PLAIN` (neither compress nor move), `EXTENDED` (compress then move — the default for
      toastable types), `EXTERNAL` (move, do not compress), `MAIN` (compress, move only as a last
      resort). `ALTER TABLE ... ALTER COLUMN ... SET STORAGE`. `[SQL]` `[SOURCE]` `[NUM]`
3.5.5 The algorithm in order (`toast_tuple_externalize`/`heap_toast_insert_or_update`): compress the
      largest attribute first, re-check the threshold, move out of line if still too large, repeat.
      It is a loop, not a single decision. `[SOURCE]` `[PROVE]`
3.5.6 The TOAST table itself: `pg_toast.pg_toast_<oid>` with columns `chunk_id`, `chunk_seq`,
      `chunk_data`, and a unique index on `(chunk_id, chunk_seq)` — so fetching a large value is an
      index scan over N chunk rows. `[SQL]` `[SOURCE]` `[NUM]`
3.5.7 The 18-byte `varatt_external` pointer left in the main tuple (`va_rawsize`, `va_extinfo`,
      `va_valueid`, `va_toastrelid`) and what it means for `SELECT *`: the pointer is cheap, the
      dereference is not. `[SOURCE]` `[NUM]` `[PROVE]`
3.5.8 `default_toast_compression` — **`pglz` in PG 18**, with `lz4` available since PG 14 and
      `ALTER TABLE ... SET COMPRESSION` per column. pglz demands a ≥25% ratio to keep the
      compressed form; lz4 only demands "not larger". PG 19 changes the default to `lz4`.
      `[GUC]` `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.5.9 `toast_tuple_target` as the per-table storage parameter that changes the threshold, and the
      real reason to lower it: keeping medium-size text out of the main heap so sequential scans stay
      fast. `[GUC]` `[NUM]` `[RESEARCH]`
3.5.10 `varattrib_1b_e` and the "toasted values are decompressed lazily" property: slicing
       (`substr` on a `text`, `->` on a `jsonb`) can fetch **only the needed chunks** for
       `EXTERNAL` storage but must fetch and decompress everything for `EXTENDED`. This is the
       single most useful TOAST fact. `[PROVE]` `[SQL]` `[TRAP]`
3.5.11 Why an unchanged TOASTed column is **not** rewritten on `UPDATE` (the pointer is copied), and
       the corollary that updating a row with a 2 MB JSONB column is cheap while inserting it is
       not. `[PROVE]` `[NUM]`
3.5.12 The QuizStakes decision this section settles: the `accountopening.application` payload and the
       `documentrequirements.document_requirement` evidence blobs. Appendix B.2 sends document
       *images* to object storage ("large binaries never belong in a database"); TOAST explains why
       that rule is right even though the database would technically accept them.
       `[SOURCE]` `[PROVE]`
3.5.13 The observability face: `pg_total_relation_size` minus `pg_table_size` minus
       `pg_indexes_size`, `pg_relation_size(reltoastrelid)`, and the query that finds which column is
       actually in the TOAST table. `[SQL]` `[NUM]`
3.5.14 **`[TRAP]`** — "JSONB is free because it is compressed". The trap: a 3 kB JSONB column moves
       every row's payload out of line, so a query that reads it does an extra index scan plus N
       chunk fetches per row, and a query that does not read it now scans a *smaller* heap and looks
       faster than it should. Symptom: p99 collapses when one column joins the `SELECT` list.
       `[TRAP]` `[NUM]`

*(14 leaves)*

## §3.6 nbtree structure and page splits

3.6.1 The physical shape: page 0 is the **meta page** (`BTMetaPageData` — `btm_root`, `btm_level`,
      `btm_fastroot`, `btm_fastlevel`, `btm_last_cleanup_num_delpages`, `btm_version`), and every
      other page is root, internal or leaf. `bt_metap` shows all of it. `[SOURCE]` `[SQL]` `[NUM]`
3.6.2 `BTPageOpaqueData` in the page's special space: `btpo_prev`, `btpo_next`, `btpo_level`,
      `btpo_flags`, `btpo_cycleid`. Sibling links make range scans and page recycling possible.
      `[SOURCE]` `[NUM]`
3.6.3 `btpo_flags` by name: `BTP_LEAF`, `BTP_ROOT`, `BTP_DELETED`, `BTP_META`, `BTP_HALF_DEAD`,
      `BTP_SPLIT_END`, `BTP_HAS_GARBAGE`, `BTP_INCOMPLETE_SPLIT`. Each names a state the tree can be
      caught in. `[SOURCE]` `[NUM]`
3.6.4 **`BTREE_VERSION` = 4** (PG 12+, the suffix-truncation/deduplication-capable format) versus 3
      versus 2, and the consequence: an index built by `pg_upgrade` from PG 11 keeps the old version
      until reindexed, so *the feature you read about does not exist in that index*.
      `[VERSION-TRAP]` `[NUM]` `[TRAP]`
3.6.5 The **Lehman & Yao** algorithm as the concurrency design, and the two properties it buys:
      a scan never holds more than one page lock at a time, and a page split is *visible* to a
      concurrent scan through the right-link rather than blocking it. `[SOURCE]` `[PROVE]`
3.6.6 The **high key** as the mechanism: every page except the rightmost holds an upper bound on the
      keys it may contain, so a scan that walks off the end knows to follow `btpo_next` and where to
      resume. `[SOURCE]` `[PROVE]`
3.6.7 **Pivot tuples** versus leaf tuples: internal pages store separator keys plus a downlink
      (`BT_PIVOT_HEAP_TID` handling), and a pivot's heap TID is not a row pointer. Confusing the two
      is why "the index stores the row" is wrong. `[SOURCE]` `[TRAP]`
3.6.8 The split algorithm step by step: choose a split point, write the new right page, insert the
      new high key into the left page, atomically WAL-log the pair, then insert the downlink into the
      parent — with `BTP_INCOMPLETE_SPLIT` covering the window between the two.
      `[SOURCE]` `[PROVE]` `[FLOW]`
3.6.9 **Incomplete splits** and who finishes them: the next inserter to descend through the affected
      parent completes the split (`_bt_finish_split`), which is why a crash mid-split needs no
      offline repair. `[SOURCE]` `[PROVE]`
3.6.10 The **rightmost-page split heuristic**: for a monotonically increasing key the split is
       **90/10, not 50/50** (`_bt_findsplitloc`'s `SPLIT_SINGLE_VALUE`/rightmost handling), because
       the left half will never receive another insert. This is the reason a `created_at` index on
       `fundsledger.ledger_entry` does not waste half its space. `[SOURCE]` `[PROVE]` `[NUM]`
3.6.11 The **fastpath insert optimisation** (`_bt_search`'s cached rightmost leaf via
       `rd_amcache`): a strictly ascending insert stream skips the root-to-leaf descent entirely.
       At 230 inserts/sec sustained and 13,600/sec peak, this is the difference between one page
       access and four. `[SOURCE]` `[PROVE]` `[NUM]`
3.6.12 The corresponding *anti*-optimisation: a random UUIDv4 primary key defeats the fastpath, dirties
       a random leaf per insert, and turns a 4-level tree into a random-write workload. This is the
       mechanism behind the §2.22.20 trap and behind `uuidv7()` existing in PG 18.
       `[PROVE]` `[TRAP]` `[NUM]`
3.6.13 The **split interval** and how PostgreSQL picks a split point to maximise how much suffix
       truncation can remove — a deliberate trade of space balance for a shorter high key.
       `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.6.14 Tree height arithmetic for real numbers: with ~262 entries per leaf page and ~370 pivots per
       internal page, 7.2B index entries need `ceil(log_370(7.2e9/262))` ≈ 4 levels. Derive the
       "3–4 I/Os" claim the current guide asserts. `[PROVE]` `[NUM]`
3.6.15 `bt_page_stats` field by field (`live_items`, `dead_items`, `avg_item_size`, `page_size`,
       `free_size`, `btpo_prev`, `btpo_next`, `btpo_level`) as the way to *see* a split's aftermath.
       `[SQL]` `[DIAG]`
3.6.16 Why B-tree and not a hash table or an LSM tree, in one place: ordered range scans, bounded
       height, in-place updates, and predictable worst case — plus the honest cost (random writes,
       no compression of the key space). `[X-REF 01]` `[PROVE]`

*(16 leaves)*

## §3.7 nbtree space management: truncation, deduplication, deletion, bloat

3.7.1 **Suffix truncation** (PG 12+): when a leaf splits, trailing attributes that are not needed to
      distinguish the two halves are truncated out of the new pivot tuple, raising fan-in.
      Bayer & Unterauer's Prefix B-Trees is the origin paper. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.7.2 Why it matters more than it sounds: a shorter pivot means more pivots per internal page, which
      means a shallower tree for the *same* data — a level saved is an I/O saved on every lookup.
      `[PROVE]` `[NUM]`
3.7.3 The heap TID as the implicit final index column (PG 12+), making every index entry unique and
      giving `_bt_findsplitloc` something to truncate to. `[SOURCE]` `[PROVE]`
3.7.4 **Deduplication** (PG 13+): duplicate keys are merged into a **posting list** tuple holding one
      key plus an array of heap TIDs, applied *lazily* — only when a leaf page would otherwise split.
      `[SOURCE]` `[NUM]` `[PROVE]`
3.7.5 The `deduplicate_items` storage parameter (default **on** for eligible operator classes), and
      the types it cannot apply to (`numeric`'s display scale, `float`'s `-0`, non-deterministic
      collations, `jsonb`). `[GUC]` `[NUM]` `[TRAP]` `[RESEARCH]`
3.7.6 **Posting list splits** — inserting a TID into the middle of an existing posting list, and why
      the format keeps TIDs sorted. `[SOURCE]`
3.7.7 What deduplication does for QuizStakes concretely: an index on
      `fundsledger.ledger_entry (client_id)` for 2.4M clients over 7.2B entries is almost all
      duplicates; deduplication is the difference between an index that fits in cache and one that
      does not. `[NUM]` `[PROVE]`
3.7.8 **`kill_prior_tuple` / `LP_DEAD` marking**: an index scan that follows a pointer to a
      definitively-dead heap tuple marks the index item dead in passing, so the *next* scan skips it
      and a later insert can reclaim the space. Reads maintain the index too. `[SOURCE]` `[PROVE]`
3.7.9 **Simple deletion** versus **bottom-up index deletion** (PG 14+): the former clears
      already-known-dead items, the latter is triggered by an imminent page split and deliberately
      visits the heap to find version-churn duplicates it can remove. The "generational hypothesis"
      is the stated rationale. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.7.10 Why bottom-up deletion is the most important index change of the last decade for OLTP:
       non-HOT updates on a table with a non-indexed-column update pattern no longer grow the index
       without bound. Name the version so the reader does not claim it on PG 12.
       `[VERSION-TRAP]` `[PROVE]`
3.7.11 **Page deletion** as a two-stage process: mark `BTP_HALF_DEAD` and unlink from the parent,
       then unlink from the siblings and mark `BTP_DELETED`; the page is only *recycled* once no
       possible scan can still be following a stale pointer to it. `[SOURCE]` `[PROVE]`
3.7.12 The recycling interlock: `btpo_level`/`btpo_cycleid` and the vacuum cycle ID, plus the
       `btm_last_cleanup_num_delpages` bookkeeping that lets a later vacuum put the page back in the
       FSM. This is Lanin & Shasha's "drain" idea. `[SOURCE]` `[RESEARCH]`
3.7.13 Why an index does **not** shrink when you delete rows: pages are emptied and recycled inside
       the index, never returned to the filesystem, unless the index is rebuilt. This is index bloat,
       stated mechanically. `[PROVE]` `[TRAP]`
3.7.14 Measuring it honestly: `pgstatindex.avg_leaf_density` (compare to `fillfactor`),
       `leaf_fragmentation`, `pgstattuple` on the index, and the "estimate bloat" queries' known
       inaccuracy. `[SQL]` `[NUM]` `[TRAP]`
3.7.15 Fixing it: `REINDEX CONCURRENTLY` (PG 12+) — three phases, an extra index built alongside,
       an `INVALID` index left behind on failure, and the fact that it needs disk space for both
       copies. Compare with `pg_repack` and with PG 19's `REPACK`.
       `[SQL]` `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.7.16 The MySQL mirror: InnoDB index pages merge when occupancy falls below
       `MERGE_THRESHOLD` (default **50%**, settable per index), and `OPTIMIZE TABLE` on InnoDB is
       an online `ALTER TABLE ... FORCE` rebuild, not an in-place compaction.
       `[MYSQL]` `[NUM]` `[RESEARCH]` `[TRAP]`

*(16 leaves)*

## §3.8 nbtree scan machinery

3.8.1 The two kinds of scan key the README distinguishes: **search** scan keys (from the query's
      predicates) and the **insertion** scan key (`BTScanInsert`, used to find a position), and why
      they are not the same object. `[SOURCE]` `[PROVE]`
3.8.2 `_bt_first` → `_bt_search` → `_bt_binsrch` → `_bt_readpage` → `_bt_next`: the actual call
      chain of an index scan, and where the per-page binary search happens. `[SOURCE]` `[FLOW]`
3.8.3 `BTScanPosData` and the fact that a scan **copies the matching items off the page** and drops
      the lock before returning them — so an index scan does not hold a page lock while the executor
      works. `[SOURCE]` `[PROVE]`
3.8.4 Boundary handling: `_bt_binsrch`'s `nextkey`, `goback`, and the `>=` versus `>` asymmetry that
      makes keyset pagination's `(created_at, entry_id) > (:ts, :id)` a single descent.
      `[SOURCE]` `[SQL]` `[PROVE]`
3.8.5 `ScalarArrayOpExpr` (`= ANY(...)`) handling inside nbtree (PG 17's rewrite): the array is
      preprocessed into a set of ordered probes executed in one scan rather than N scans. This is why
      `WHERE client_id = ANY(:ids)` is now cheap. `[SOURCE]` `[VERSION-TRAP]` `[RESEARCH]`
3.8.6 **Skip scan (PG 18)**: nbtree preprocessing turns `WHERE created_at >= :t` on an index
      `(position, created_at)` into `WHERE position = ANY(<every distinct value>) AND created_at >=
      :t`, iterating the omitted prefix's distinct values. Support function **number 6** in the
      operator family (`src/include/utils/skipsupport.h`) is what makes the iteration possible.
      `[SOURCE]` `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.8.7 Why skip scan does **not** repeal the leftmost-prefix rule: the cost is proportional to the
      number of distinct prefix values, so it wins for `position` (11 values) and loses for
      `client_id` (2.4M values). State the boundary numerically. `[PROVE]` `[NUM]` `[TRAP]`
3.8.8 **Index-only scan** mechanics: `amcanreturn`, the `INCLUDE` payload living only in leaf
      tuples, and the VM check per page (`Heap Fetches`). An `INCLUDE` column cannot be a scan key —
      that is the whole distinction. `[SOURCE]` `[PLAN]` `[PROVE]`
3.8.9 **Bitmap scan** internals: `TIDBitmap` with per-page bitmaps, **lossification** when
      `work_mem` is exceeded (the page is kept, the offsets are dropped), and the `Recheck Cond` and
      `lossy=` counters in `EXPLAIN (ANALYZE, BUFFERS)` that prove it happened.
      `[SOURCE]` `[PLAN]` `[NUM]` `[PROVE]`
3.8.10 `BitmapAnd`/`BitmapOr` as the reason two single-column indexes are sometimes genuinely
       enough, and the reason they are usually not (per-row recheck, no ordering, no index-only).
       `[PLAN]` `[PROVE]`
3.8.11 The `amcostestimate` interface and `btcostestimate`: how much of "will the planner use my
       index" is decided inside the access method rather than in the planner.
       `[SOURCE]` `[PROVE]`
3.8.12 **Index correlation** (`pg_stats.correlation`) as the input that makes the same index scan cost
       4× more on an unclustered column, and `CLUSTER`/`pg_repack` as the (rarely correct) fix.
       `[NUM]` `[PROVE]` `[SQL]`
3.8.13 `indcheckxmin` and the `indisvalid`/`indisready`/`indislive` triple — the state machine behind
       `CREATE INDEX CONCURRENTLY`'s three-phase build, and what each phase waits for.
       `[SOURCE]` `[PROVE]` `[SQL]`
3.8.14 Scans on a standby: `ignore_killed_tuples` and why `kill_prior_tuple` is disabled during
       recovery — a read-only replica cannot mark index items dead. A subtle asymmetry in replica
       performance. `[SOURCE]` `[PROVE]` `[RESEARCH]`

*(14 leaves)*

## §3.9 The other access methods, at implementation depth

3.9.1 The pluggable index AM interface (`IndexAmRoutine`): `ambuild`, `aminsert`, `ambeginscan`,
      `amgettuple`, `amgetbitmap`, `ambulkdelete`, `amvacuumcleanup`, `amcostestimate`, and the
      capability flags (`amcanorder`, `amcanreturn`, `amcanunique`, `amcanmulticol`,
      `amsearcharray`, `amoptionalkey`). Reading the flags tells you what an AM can be used for.
      `[SOURCE]` `[NUM]`
3.9.2 **Hash** index internals: bucket pages, overflow pages, the bitmap page tracking free overflow
      pages, and the fact that hash indexes have been **WAL-logged and crash-safe since PG 10**.
      Equality only, no ordering, no uniqueness. `[SOURCE]` `[VERSION-TRAP]` `[TRAP]`
3.9.3 **GIN** internals: the entry tree over keys, the posting *tree* or posting *list* per key,
      and `fastupdate` (default **on**) with its **pending list** (`gin_pending_list_limit`,
      default 4 MB) that batches inserts and is drained by vacuum or by a reader that finds it too
      large. `[SOURCE]` `[GUC]` `[NUM]`
3.9.4 The two GIN consequences nobody expects: a *read* can pay for someone else's pending-list
      drain, and `gin_pending_list_limit` therefore controls read latency variance, not just write
      throughput. `[PROVE]` `[TRAP]`
3.9.5 `gin_fuzzy_search_limit` (default 0 = unlimited) and the "GIN index scan cost" formula's
      dependence on the number of keys the query decomposes into. `[GUC]` `[NUM]` `[RESEARCH]`
3.9.6 **GiST** internals: a generalised search tree parameterised by `consistent`, `union`,
      `compress`, `decompress`, `penalty`, `picksplit`, `same` and `distance` — the last one being
      what makes KNN (`ORDER BY x <-> y`) an index scan. Overlapping bounding boxes mean a GiST
      lookup may need multiple subtrees. `[SOURCE]` `[NUM]` `[PROVE]`
3.9.7 **SP-GiST** internals: space-partitioning trees (quadtree, k-d tree, radix tree) with
      non-overlapping partitions, and the `text` radix-tree opclass as the reason it beats B-tree
      for long common prefixes. `[SOURCE]` `[RESEARCH]`
3.9.8 **BRIN** internals: the revmap, one summary tuple per *range* of `pages_per_range` pages
      (default **128**), `minmax` versus `minmax_multi` (PG 14+, tolerant of outliers) versus
      `bloom` opclasses, and `brin_summarize_new_values`/`autosummarize`.
      `[SOURCE]` `[GUC]` `[NUM]` `[RESEARCH]`
3.9.9 The BRIN arithmetic that makes it interesting for QuizStakes: 7.2B rows ≈ 164M heap pages ≈
      1.28M range summaries ≈ a few tens of MB of index for a 1.3 TB/year table — versus ~200 GB for
      the equivalent B-tree. State both numbers. `[NUM]` `[PROVE]`
3.9.10 Why BRIN is useless the moment physical order stops matching logical order, and why an
       append-only `ledger_entry` is the *one* table shape where it works. Correlation is the whole
       precondition. `[PROVE]` `[TRAP]`
3.9.11 The `bloom` extension index and `pg_trgm`'s GIN/GiST opclasses (`gin_trgm_ops`,
       `gist_trgm_ops`) — the mechanism behind indexed `LIKE '%foo%'` and similarity search.
       `[SQL]` `[RESEARCH]`
3.9.12 `pgvector`'s HNSW and IVFFlat as index AMs written entirely outside core, and why they prove
       the AM interface is the real extension point. `[RESEARCH]` `[X-REF 22]`
3.9.13 The MySQL contrast: InnoDB has **only** B+trees (plus FULLTEXT and R-tree/SPATIAL), no
       partial indexes, no expression indexes before 8.0.13's functional key parts, and no covering
       `INCLUDE`. Half the PostgreSQL indexing playbook simply does not port.
       `[MYSQL]` `[NUM]` `[TRAP]`
3.9.14 The decision table this section must produce: AM × supported operators × ordered? ×
       index-only? × build cost × size × update cost, with the QuizStakes column that would use each.
       `[NUM]`

*(14 leaves)*

## §3.10 InnoDB physical layout: spaces, pages, records

3.10.1 The storage hierarchy, each level with its size: **tablespace → segment → extent (1 MB = 64
       pages at the default `innodb_page_size = 16384`) → page (16 kB) → row**. Every number here is
       page-size-dependent. `[MYSQL]` `[NUM]` `[SOURCE]`
3.10.2 The tablespace zoo: the system tablespace (`ibdata1`), file-per-table `.ibd`, general
       tablespaces, the global temporary tablespace, session temp tablespaces, and the separate
       **undo tablespaces** (`innodb_undo_tablespaces`, minimum 2, truncatable).
       `[MYSQL]` `[NUM]` `[RESEARCH]`
3.10.3 The **FIL header (38 bytes)** field by field: `FIL_PAGE_SPACE_OR_CHKSUM`, `FIL_PAGE_OFFSET`
       (the page number), `FIL_PAGE_PREV`, `FIL_PAGE_NEXT`, `FIL_PAGE_LSN`, `FIL_PAGE_TYPE`,
       `FIL_PAGE_FILE_FLUSH_LSN`, `FIL_PAGE_SPACE_ID`. `[MYSQL]` `[SOURCE]` `[NUM]`
3.10.4 The **FIL trailer (8 bytes)**: an old-style checksum plus the low 4 bytes of the LSN, whose
       whole purpose is **torn-page detection** — if header LSN and trailer LSN disagree, the write
       was partial. Compare with PostgreSQL's `pd_checksum`. `[MYSQL]` `[PROVE]` `[NUM]`
3.10.5 `FIL_PAGE_TYPE` values worth knowing: `FIL_PAGE_INDEX`, `FIL_PAGE_UNDO_LOG`,
       `FIL_PAGE_INODE`, `FIL_PAGE_IBUF_FREE_LIST`, `FIL_PAGE_IBUF_BITMAP`, `FIL_PAGE_TYPE_FSP_HDR`,
       `FIL_PAGE_TYPE_XDES`, `FIL_PAGE_TYPE_BLOB`, `FIL_PAGE_SDI`, `FIL_PAGE_TYPE_LOB_*`.
       `[MYSQL]` `[SOURCE]` `[NUM]` `[RESEARCH]`
3.10.6 Page 0/1/2 of every `.ibd`: FSP header + extent descriptors, the insert-buffer bitmap, and the
       inode (segment) page. This is why an `.ibd` has a floor of ~96 kB even when empty.
       `[MYSQL]` `[NUM]`
3.10.7 The **INDEX page** layout: 38-byte FIL header, **56-byte page header**
       (`PAGE_N_DIR_SLOTS`, `PAGE_HEAP_TOP`, `PAGE_N_HEAP`, `PAGE_FREE`, `PAGE_GARBAGE`,
       `PAGE_LAST_INSERT`, `PAGE_DIRECTION`, `PAGE_N_DIRECTION`, `PAGE_N_RECS`, `PAGE_MAX_TRX_ID`,
       `PAGE_LEVEL`, `PAGE_INDEX_ID`, `PAGE_BTR_SEG_LEAF`, `PAGE_BTR_SEG_TOP`), the **infimum** and
       **supremum** pseudo-records, user records, free space, the page directory, and the trailer.
       `[MYSQL]` `[SOURCE]` `[NUM]`
3.10.8 **Infimum and supremum** as sentinels that make the in-page singly-linked record list
       terminate without null checks — and as the *lock targets* that `SHOW ENGINE INNODB STATUS`
       reports when a gap lock covers the start or end of a page. `[MYSQL]` `[PROVE]` `[DIAG]`
3.10.9 The **page directory**: a dynamically-sized array of 16-bit record offsets growing *downward*
       from the trailer, with one slot per 4–8 records, so an in-page lookup is a binary search over
       slots followed by a short linked-list walk. Contrast with PostgreSQL's one-slot-per-tuple line
       pointer array. `[MYSQL]` `[SOURCE]` `[NUM]` `[PROVE]`
3.10.10 Records are stored **in insertion order in the heap** and ordered only through the linked
        list and directory — so "InnoDB pages are physically sorted" is false at the byte level and
        true at the logical level. `[MYSQL]` `[TRAP]` `[PROVE]`
3.10.11 The **COMPACT record header (5 bytes)**: `info_bits` (including the **delete-mark** bit and
        `min_rec` flag), `n_owned`, `heap_no`, `record_type` (0 conventional, 1 node pointer,
        2 infimum, 3 supremum), and `next_record` as a *relative* offset. Preceded by the
        variable-length length array and the nullable-column bitmap, both stored in reverse order.
        `[MYSQL]` `[SOURCE]` `[NUM]`
3.10.12 The three hidden system columns and their exact widths: `DB_ROW_ID` (6 bytes, only when
        there is no user primary key or unique-not-null key), `DB_TRX_ID` (**6 bytes**),
        `DB_ROLL_PTR` (**7 bytes**). Every clustered-index row carries 13–19 bytes of MVCC metadata.
        `[MYSQL]` `[SOURCE]` `[NUM]` `[PROVE]`
3.10.13 The four **row formats** and their differences stated as behaviour, not names: `REDUNDANT`
        (pre-5.0, 2-byte offsets), `COMPACT`, `DYNAMIC` (the **default**), `COMPRESSED`
        (`KEY_BLOCK_SIZE`, page-level zlib with a modification log).
        `[MYSQL]` `[NUM]` `[RESEARCH]`
3.10.14 Off-page storage: `COMPACT` keeps the first **768 bytes** inline plus a **20-byte** pointer;
        `DYNAMIC` keeps only the 20-byte pointer and pushes the whole value to a singly-linked list
        of overflow (`LOB`) pages; only values longer than **40 bytes** are candidates. This is why
        `DYNAMIC` exists and why `ROW_FORMAT=COMPACT` wastes 768 bytes per BLOB per row.
        `[MYSQL]` `[NUM]` `[PROVE]` `[TRAP]`
3.10.15 The **hard row-size limit**: a row must fit in roughly **half a page** (~8,126 bytes usable
        at 16 kB), producing `ERROR 1118 (42000): Row size too large` — an error with no PostgreSQL
        equivalent, because PostgreSQL TOASTs instead of failing. `[MYSQL]` `[DIAG]` `[NUM]` `[TRAP]`
3.10.16 The index-key length limits that follow from page size: **3072 bytes** per index key with
        `DYNAMIC`/`COMPRESSED` at 16 kB, 767 with `COMPACT`/`REDUNDANT`, and the resulting
        `varchar(255)` + `utf8mb4` prefix-index folklore. `[MYSQL]` `[NUM]` `[RESEARCH]` `[TRAP]`

*(16 leaves)*

## §3.11 InnoDB index internals and the auxiliary structures

3.11.1 The **clustered index is the table**: the leaf level of the PK B+tree holds the full row, so
       there is no separate heap and no `ctid` equivalent. Every consequence in this section follows
       from that one sentence. `[MYSQL]` `[PROVE]` `[SOURCE]`
3.11.2 What that buys: PK lookups touch one structure, PK range scans are physically sequential, and
       there is no visibility-map/index-only-scan distinction to make. `[MYSQL]` `[PROVE]`
3.11.3 What it costs: **every secondary index leaf entry stores the full primary key** as its row
       pointer, so a 16-byte UUID PK adds 16 bytes to every entry of every secondary index. Do the
       arithmetic for `cardpayments.transactions` with three secondary indexes.
       `[MYSQL]` `[NUM]` `[PROVE]` `[TRAP]`
3.11.4 The **double lookup** for a non-covering secondary-index read (secondary → PK → clustered
       index), and why MySQL's "covering index" advice is stronger than PostgreSQL's.
       `[MYSQL]` `[PROVE]` `[PLAN]`
3.11.5 Secondary index entries have **no `DB_TRX_ID`**, only a delete-mark and the page-level
       `PAGE_MAX_TRX_ID`; a read that cannot prove visibility from the page must visit the clustered
       index. This is the mechanism behind MySQL's index-only-scan limitations.
       `[MYSQL]` `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.11.6 Insert-ordering: `PAGE_LAST_INSERT`/`PAGE_DIRECTION`/`PAGE_N_DIRECTION` drive InnoDB's
       sequential-insert detection, which splits **at the insertion point** rather than the middle —
       InnoDB's equivalent of the 90/10 rightmost split. `[MYSQL]` `[SOURCE]` `[PROVE]`
3.11.7 The **change buffer** (`ibuf`): non-unique **secondary** index page modifications for pages
       not in the buffer pool are buffered and merged later. **`innodb_change_buffering` default
       changed from `all` to `none` in MySQL 8.4** — the entire mechanism is off by default now.
       `[MYSQL]` `[GUC]` `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.11.8 Why it was turned off, and the lesson: it optimised for spinning disks and became a recovery
       and concurrency liability on NVMe. A tuning default is an era, not a truth.
       `[MYSQL]` `[PROVE]`
3.11.9 The **adaptive hash index** (AHI): a hash index over frequently-accessed B+tree page
       positions, built at runtime. **`innodb_adaptive_hash_index` default changed from `ON` to
       `OFF` in MySQL 8.4** because of `btr_search_latch` contention.
       `[MYSQL]` `[GUC]` `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.11.10 The doublewrite/AHI/change-buffer trio as the answer to "what is in the InnoDB buffer pool
        besides pages" — plus the lock table, the dictionary cache, and the log buffer.
        `[MYSQL]` `[NUM]`
3.11.11 Online DDL internals: the three algorithms (`INSTANT`, `INPLACE`, `COPY`), the row log that
        `INPLACE` uses to capture concurrent DML, `innodb_online_alter_log_max_size` (default
        **128 MB**) and the `ERROR 1799`/`1478` failures when it overflows.
        `[MYSQL]` `[NUM]` `[DIAG]` `[RESEARCH]`
3.11.12 `ALGORITHM=INSTANT` mechanics: since 8.0.29 a column can be added in the *middle* of a row
        with a row-version counter stored per row, so old and new row layouts coexist in one
        tablespace. This is the closest thing MySQL has to PostgreSQL's `ADD COLUMN` fast path.
        `[MYSQL]` `[VERSION-TRAP]` `[RESEARCH]`
3.11.13 The transactional **data dictionary** (8.0+): dictionary tables in InnoDB, SDI pages inside
        each `.ibd`, atomic DDL, and the death of `.frm` files — the reason a crashed `ALTER` no
        longer leaves an orphan table. `[MYSQL]` `[PROVE]` `[RESEARCH]`
3.11.14 `AUTO_INCREMENT` internals: the in-memory counter, `innodb_autoinc_lock_mode` (default
        **2 = interleaved** since 8.0), the persistence of the counter across restart (8.0+, via the
        redo log), and the gaps that all three facts guarantee.
        `[MYSQL]` `[GUC]` `[NUM]` `[TRAP]` `[VERSION-TRAP]`
3.11.15 The QuizStakes port of §3.3's arithmetic: the same `ledger_entry` row in InnoDB — 5-byte
        record header + 13 bytes of hidden columns + payload, in a 16 kB page with a page directory,
        and three secondary indexes each carrying the 8-byte PK. Compare totals with PostgreSQL's and
        state which engine stores this table more compactly and why.
        `[MYSQL]` `[NUM]` `[PROVE]`

*(15 leaves)*

## §3.12 PostgreSQL MVCC internals

3.12.1 The three pieces of state a visibility decision needs: the tuple's `t_xmin`/`t_xmax`, the
       transaction's **snapshot**, and the **commit log**. Everything in this section is one of the
       three. `[PROVE]` `[SOURCE]`
3.12.2 XID assignment is **lazy**: a transaction gets a `VirtualTransactionId`
       (`procNumber` + a backend-local counter) at start and a real `TransactionId` only when it
       first writes. A read-only transaction consumes no XID space. `[SOURCE]` `[PROVE]` `[NUM]`
3.12.3 `SnapshotData` field by field: `xmin` (oldest still-running xid), `xmax` (next xid to be
       assigned), `xip[]` (the in-progress list), `subxip[]`, `curcid`, and the flags. A snapshot is
       ~"everything below `xmin` is decided, everything at or above `xmax` is future, and this list
       in between is running". `[SOURCE]` `[NUM]` `[PROVE]`
3.12.4 `GetSnapshotData` walking the **`ProcArray`** under `ProcArrayLock` in shared mode, and why
       this is an O(`max_connections`) operation on every statement in `READ COMMITTED` — the
       original reason connection counts matter beyond memory. `[SOURCE]` `[PROVE]` `[NUM]`
       `[X-REF 11]`
3.12.5 The PG 14 `GetSnapshotData` scalability rewrite (the dense `ProcGlobal` xid/subxid arrays) and
       what it changed in practice for high-connection workloads. `[VERSION-TRAP]` `[RESEARCH]`
3.12.6 `HeapTupleSatisfiesMVCC` as the actual visibility function, walked branch by branch: check
       `t_xmin`'s hint bits, else consult `pg_xact`; if `t_xmin` is not committed-and-visible the
       tuple is invisible; then the same for `t_xmax`, with the lock-only and multixact cases.
       **This function is the definition of an isolation level.** `[SOURCE]` `[PROVE]`
3.12.7 The other snapshot types and where each is used: `SnapshotSelf`, `SnapshotAny`,
       `SnapshotToast`, `SnapshotDirty` (used by unique-constraint checks to see uncommitted rows),
       `SnapshotHistoricMVCC` (logical decoding). `SnapshotDirty` is why a unique violation can block
       on another transaction. `[SOURCE]` `[PROVE]` `[TRAP]`
3.12.8 `pg_xact` (formerly `pg_clog`): **2 bits per transaction**, four states
       (`IN_PROGRESS`, `COMMITTED`, `ABORTED`, `SUB_COMMITTED`), `CLOG_XACTS_PER_PAGE` = 32,768 on
       an 8 kB page → ~2 KB of clog per million transactions. Do the arithmetic.
       `[SOURCE]` `[NUM]` `[PROVE]`
3.12.9 The SLRU caches (`transaction_buffers`, `subtransaction_buffers`, `multixact_*_buffers`,
       `commit_timestamp_buffers`, `notify_buffers`, `serializable_buffers` — all configurable and
       auto-sized from PG 17) and the `SLRU` wait events that appear when they thrash.
       `[GUC]` `[VERSION-TRAP]` `[DIAG]` `[RESEARCH]`
3.12.10 **Subtransactions**: `pg_subtrans`, the `TransactionState` stack, and
        `PGPROC_MAX_CACHED_SUBXIDS` = **64** — beyond which the snapshot is marked
        `suboverflowed` and every visibility check must consult `pg_subtrans`. This is the mechanism
        behind the §2.22.66 trap and behind `SubtransSLRU`/`SubtransControlLock` waits.
        `[SOURCE]` `[NUM]` `[PROVE]` `[TRAP]`
3.12.11 **Multixacts**: `pg_multixact/{offsets,members}`, `HEAP_XMAX_IS_MULTI`, and why they exist —
        multiple sessions holding *share* locks on one row cannot all fit in a 4-byte `t_xmax`.
        `FOR KEY SHARE` on `fundsledger.position` from many concurrent stake checks creates them.
        `[SOURCE]` `[PROVE]` `[NUM]`
3.12.12 Multixact members have their **own wraparound** (`autovacuum_multixact_freeze_max_age`
        default **400,000,000**, `vacuum_multixact_failsafe_age` **1,600,000,000**) and their own
        outage mode, which is the failure nobody sees coming. `[GUC]` `[NUM]` `[TRAP]` `[RESEARCH]`
3.12.13 The **32-bit XID** and modular comparison: `TransactionIdPrecedes` compares modulo 2³², so
        the visible window is **2³¹ ≈ 2.1 billion** transactions, and "wraparound" means a past
        transaction appearing to be in the future. `[SOURCE]` `[PROVE]` `[NUM]`
3.12.14 **Freezing** as the fix: set `HEAP_XMIN_FROZEN` so the tuple is unconditionally visible and
        its xid can be reused. `vacuum_freeze_min_age` (**50,000,000**),
        `vacuum_freeze_table_age` (**150,000,000**), `autovacuum_freeze_max_age`
        (**200,000,000**), `vacuum_failsafe_age` (**1,600,000,000**).
        `[GUC]` `[NUM]` `[SOURCE]` `[PROVE]`
3.12.15 `relfrozenxid`/`relminmxid` per relation, `datfrozenxid` per database,
        `age(relfrozenxid)`, and the exact escalation ladder: warning, then
        `WARNING: database "x" must be vacuumed within N transactions`, then a **refusal to accept
        commands** requiring single-user-mode vacuum. State the thresholds and verify them.
        `[DIAG]` `[NUM]` `[SQL]` `[RESEARCH]`
3.12.16 PG 18's **eager freezing / eager scanning** of all-visible-but-not-all-frozen pages, and why
        it exists: to convert a future anti-wraparound cliff into steady background work.
        `[VERSION-TRAP]` `[RESEARCH]` `[GUC]`
3.12.17 Why long-running transactions are *mechanically* toxic, in one causal chain: an old snapshot
        pins `xmin` → `GetOldestNonRemovableTransactionId` cannot advance → vacuum may not remove
        newer dead tuples anywhere in the cluster → heap and index bloat → worse plans and more
        I/O. `pg_stat_activity.backend_xmin`, `xact_start`, `state = 'idle in transaction'`.
        `[PROVE]` `[SQL]` `[DIAG]` `[TRAP]`
3.12.18 The QuizStakes rule this produces: a 30 ms restriction-decision budget and a 150 ms
        stake-reservation budget mean **no transaction in this system has any business living
        longer than a second**, and `idle_in_transaction_session_timeout` should enforce it rather
        than trust it. `[GUC]` `[PROVE]` `[SOURCE]`

*(18 leaves)*

## §3.13 InnoDB MVCC internals

3.13.1 The design difference in one sentence: PostgreSQL keeps **old versions in the table**, InnoDB
       keeps the **current version in the table and old versions in the undo log**. Every difference
       in bloat, vacuum and rollback cost follows. `[MYSQL]` `[PROVE]`
3.13.2 `DB_TRX_ID` (the last transaction to modify the row) and `DB_ROLL_PTR` (a pointer into an undo
       record) as the on-row MVCC state, and the **undo chain** they form.
       `[MYSQL]` `[SOURCE]` `[NUM]`
3.13.3 The **read view** (`ReadView`): `m_low_limit_id`, `m_up_limit_id`, `m_creator_trx_id`,
       `m_ids` (the active transaction list). Map each field onto PostgreSQL's snapshot fields so the
       reader sees they are the same idea. `[MYSQL]` `[SOURCE]` `[NUM]` `[PROVE]`
3.13.4 The visibility algorithm: if `DB_TRX_ID` is invisible under the read view, follow
       `DB_ROLL_PTR` to the previous version and repeat — so **reading old data costs more the more
       churn there is**, the exact opposite of PostgreSQL's cost curve.
       `[MYSQL]` `[PROVE]` `[NUM]`
3.13.5 When the read view is taken: **once at the first read** under `REPEATABLE READ`, **per
       statement** under `READ COMMITTED`. This one line is the whole isolation difference in
       InnoDB. `[MYSQL]` `[PROVE]` `[SOURCE]`
3.13.6 **Rollback segments** and undo tablespaces: 128 rollback segments per undo tablespace, 1024
       undo slots per segment, insert-undo versus update-undo, and the resulting concurrent-write
       transaction ceiling. `[MYSQL]` `[NUM]` `[RESEARCH]`
3.13.7 `trx_undo_update_cleanup` moving a committed transaction's update-undo onto the **history
       list**, ordered by `trx_no` — the queue the purge threads drain.
       `[MYSQL]` `[SOURCE]` `[PROVE]`
3.13.8 **History list length** (`trx_rseg_history_len`, shown in `SHOW ENGINE INNODB STATUS` and
       `INNODB_METRICS`) as InnoDB's single best "am I in trouble" metric — the direct analogue of
       PostgreSQL's dead-tuple count. Under ~1,000 is normal; millions means purge is losing.
       `[MYSQL]` `[DIAG]` `[NUM]`
3.13.9 The **purge** pipeline: the purge coordinator plus `innodb_purge_threads` (default **4**),
       `innodb_purge_batch_size` (default **300**), `innodb_max_purge_lag` and
       `innodb_max_purge_lag_delay` as the back-pressure valve that deliberately slows DML.
       `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.13.10 Why a long-running `REPEATABLE READ` transaction is toxic in InnoDB too, by a different
        mechanism: undo cannot be purged → undo tablespaces grow → every read of a churned row walks
        a longer chain → CPU rises with no change in query volume.
        `[MYSQL]` `[PROVE]` `[TRAP]`
3.13.11 **ROLLBACK is expensive in InnoDB and cheap in PostgreSQL**, and the reason is structural:
        InnoDB must apply undo records to restore the row, PostgreSQL only has to not-commit. The
        practical rule: do not build a workflow that rolls back 10M-row transactions.
        `[MYSQL]` `[PROVE]` `[NUM]` `[TRAP]`
3.13.12 Crash recovery of uncommitted transactions: redo is applied first, then undo is applied to
        roll back what was in flight, and `SHOW ENGINE INNODB STATUS` reports the rollback progress —
        a startup that appears to hang. `[MYSQL]` `[DIAG]` `[PROVE]`
3.13.13 Secondary-index visibility revisited (§3.11.5): with no `DB_TRX_ID` on the entry, InnoDB uses
        `PAGE_MAX_TRX_ID` to decide whether the *page* is old enough to trust, else it visits the
        clustered index. `[MYSQL]` `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.13.14 Delete-marking rather than deleting: a `DELETE` sets the record's delete-mark bit; purge
        physically removes it later, which is why space is not reclaimed at commit and why
        `information_schema.TABLES.DATA_FREE` moves late.
        `[MYSQL]` `[NUM]` `[PROVE]` `[TRAP]`
3.13.15 The side-by-side table this section exists to produce: version location, read cost of churn,
        write amplification, rollback cost, space reclamation mechanism, "vacuum" equivalent, the
        metric to watch, and the failure mode — PostgreSQL versus InnoDB, one row each.
        `[MYSQL]` `[NUM]` `[PROVE]`

*(15 leaves)*

## §3.14 The PostgreSQL lock manager

3.14.1 The three layers, distinguished by purpose and cost: **spinlocks** (a few instructions, no
       queue, no deadlock detection), **LWLocks** (shared/exclusive, a wait queue, no deadlock
       detection, used for shared-memory structures), and **heavyweight locks** (the `lmgr`, with
       modes, a queue, and deadlock detection). Confusing them is why "PostgreSQL locking" questions
       go wrong. `[SOURCE]` `[PROVE]` `[NUM]`
3.14.2 **Latch versus lock**, stated as the general principle: a latch protects a *physical
       structure* for the duration of an operation and is invisible in the transaction model; a lock
       protects a *logical object* for the duration of a transaction. Buffer content locks are
       latches; row locks are locks. `[PROVE]`
3.14.3 The heavyweight lock structures: `LOCKTAG` (`locktag_field1..4`, `locktag_type`,
       `locktag_lockmethodid`), `LOCK` (per lockable object), `PROCLOCK` (per holder per object),
       `LOCALLOCK` (the backend-local cache), all in `src/backend/storage/lmgr/lock.c`.
       `[SOURCE]` `[NUM]`
3.14.4 `LOCKTAG_*` types as the full inventory of what can be locked: `RELATION`,
       `RELATION_EXTEND`, `DATABASE_FROZEN_IDS`, `PAGE`, `TUPLE`, `TRANSACTION`, `VIRTUALTRANSACTION`,
       `SPECULATIVE_TOKEN`, `OBJECT`, `USERLOCK` (advisory), `ADVISORY`, `APPLY_TRANSACTION`.
       Every row in `pg_locks` is one of these. `[SOURCE]` `[SQL]` `[NUM]`
3.14.5 The **eight table-level modes** and the conflict matrix, read as a matrix rather than
       memorised: `ACCESS SHARE`, `ROW SHARE`, `ROW EXCLUSIVE`, `SHARE UPDATE EXCLUSIVE`, `SHARE`,
       `SHARE ROW EXCLUSIVE`, `EXCLUSIVE`, `ACCESS EXCLUSIVE`. `[SOURCE]` `[NUM]` `[PROVE]`
3.14.6 The lock table is **partitioned into `NUM_LOCK_PARTITIONS` = 16** (`LOG2_NUM_LOCK_PARTITIONS`
       = 4), hashed by `LOCKTAG`, each partition guarded by its own LWLock — so contention on one hot
       relation cannot be spread across partitions. `[SOURCE]` `[NUM]` `[PROVE]`
3.14.7 **Fast-path locking**: the three "weak" relation modes (`AccessShareLock`, `RowShareLock`,
       `RowExclusiveLock`) are recorded in the backend's own `PGPROC` rather than the shared table,
       when no conflicting strong lock could exist. `FP_LOCK_SLOTS_PER_BACKEND` was **16**;
       **PG 18 makes the array variable-sized and scaled from `max_locks_per_transaction`
       (default 64)**. `[SOURCE]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.14.8 The failure mode this creates, and the reason it is the most-reported PostgreSQL scalability
       incident of the last five years: a query touching a partitioned table with several indexes per
       partition **overflows the fast-path slots**, falls back to the shared table, and produces
       `LWLock:LockManager` waits that scale with concurrency. `[DIAG]` `[PROVE]` `[NUM]` `[TRAP]`
3.14.9 The QuizStakes instance of exactly that: `fundsledger.ledger_entry` partitioned by month with
       a 90-day hot window and three indexes per partition — count the locks a single unpruned query
       takes and compare with the slot budget. `[NUM]` `[PROVE]` `[SQL]`
3.14.10 The strong-lock interlock (`FastPathStrongRelationLocks`): acquiring a strong lock forces
        every backend holding fast-path locks on that relation to transfer them into the shared
        table, which is why one `ALTER TABLE` can briefly stall a whole cluster.
        `[SOURCE]` `[PROVE]`
3.14.11 **Row locks are not in the lock manager.** A row lock is stored *in the tuple* (`t_xmax` plus
        the `HEAP_XMAX_*` mode bits, or a multixact), and a waiter blocks on the
        `LOCKTAG_TRANSACTION` lock of the holder. This is the single most important lock-manager
        fact, and it explains why `pg_locks` never shows millions of row locks — and why
        PostgreSQL has **no lock escalation at all**. `[SOURCE]` `[PROVE]` `[NUM]` `[TRAP]`
3.14.12 The four row-lock modes and their conflicts: `FOR UPDATE`, `FOR NO KEY UPDATE`,
        `FOR SHARE`, `FOR KEY SHARE` — and the fact that a plain foreign-key check takes
        `FOR KEY SHARE`, which is why FK checks conflict with `FOR UPDATE` but not with ordinary
        updates. `[SOURCE]` `[PROVE]` `[SQL]`
3.14.13 `LOCKTAG_TUPLE` as the short-lived intermediate that serialises *waiters* on one row so they
        acquire it in arrival order, and `LOCKTAG_SPECULATIVE_TOKEN` as the mechanism behind
        `INSERT ... ON CONFLICT`'s speculative insertion. `[SOURCE]` `[PROVE]`
3.14.14 The **deadlock detector**: on a lock wait exceeding `deadlock_timeout` (default **1s**) the
        waiter builds the waits-for graph from the lock queues and searches for a cycle
        (`DeadLockCheck` in `deadlock.c`); a cycle is broken by aborting **the detecting
        transaction**, with SQLSTATE **40P01**. `[SOURCE]` `[NUM]` `[PROVE]` `[DIAG]`
3.14.15 The subtle part worth stating: the detector also performs **soft-edge reordering** — if the
        cycle can be resolved by re-ordering the wait queue instead of aborting anyone, it does that.
        Not every cycle is a deadlock error. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.14.16 Reading a real deadlock log line by line: `ERROR: deadlock detected`,
        `DETAIL: Process 4021 waits for ShareLock on transaction 918273; blocked by process 4022`,
        `HINT`, and the statement list — mapping each to a `pg_locks` row.
        `[DIAG]` `[SOURCE]` `[PROVE]`
3.14.17 `log_lock_waits` (with `deadlock_timeout` as its trigger), `pg_blocking_pids()`,
        `pg_locks` joined to `pg_stat_activity`, and `lock_timeout` as the way to make lock waits
        loud and bounded instead of silent and unbounded. `[GUC]` `[SQL]` `[DIAG]`

*(17 leaves)*

## §3.15 InnoDB locking internals

3.15.1 The architecture: `lock_sys` with a hash table keyed by (space id, page number), holding
       **per-page bitmaps** of record locks — so one lock object can cover many records on a page.
       This is why InnoDB's lock memory is compact and why lock reporting is page-oriented.
       `[MYSQL]` `[SOURCE]` `[PROVE]` `[NUM]`
3.15.2 **Locks are on index records, never on rows.** Every InnoDB locking behaviour, including all
       the surprising ones, follows from that: no usable index means locking every record the scan
       touches. `[MYSQL]` `[PROVE]` `[TRAP]`
3.15.3 The lock type inventory with the internal names: `LOCK_REC_NOT_GAP` (record only),
       `LOCK_GAP` (the gap before a record), `LOCK_ORDINARY` (**next-key** = record + preceding gap),
       `LOCK_INSERT_INTENTION`, plus `LOCK_S`/`LOCK_X` modes and the table-level
       `LOCK_IS`/`LOCK_IX` intention locks. `[MYSQL]` `[SOURCE]` `[NUM]`
3.15.4 **Next-key locking** as the phantom-prevention mechanism under `REPEATABLE READ`, and its
       cost: a range read locks gaps, so inserts into those gaps block even though no existing row
       conflicts. `[MYSQL]` `[PROVE]` `[NUM]`
3.15.5 **Insert intention locks**: gap locks that signal intent and do **not** conflict with each
       other, so many concurrent inserts into one gap proceed — but they *do* conflict with a gap
       lock held by a reader. This asymmetry is the source of most InnoDB deadlocks.
       `[MYSQL]` `[PROVE]` `[NUM]` `[TRAP]`
3.15.6 What changes at `READ COMMITTED`: gap locks are (mostly) not taken, and non-matching records
       are unlocked after evaluation — which is why many shops run RC to reduce deadlocks and accept
       the anomalies. State the trade explicitly. `[MYSQL]` `[PROVE]` `[TRAP]`
3.15.7 **Implicit versus explicit locks**: a transaction that has already written a row holds an
       implicit exclusive lock recorded only in `DB_TRX_ID`; the lock object is materialised only
       when someone else asks. This is why lock counts are lower than expected.
       `[MYSQL]` `[SOURCE]` `[PROVE]`
3.15.8 **Metadata locks (MDL)** at the server layer, not InnoDB: taken by every statement, released
       at end of transaction, and the reason `ALTER TABLE` can be blocked by a long-running
       `SELECT` and then block every subsequent query — the "Waiting for table metadata lock" pileup.
       `[MYSQL]` `[DIAG]` `[PROVE]` `[TRAP]`
3.15.9 The `AUTO-INC` table lock in `innodb_autoinc_lock_mode = 0/1` versus the lightweight mutex in
       mode 2, and the replication consequence that made mode 1 the old default.
       `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.15.10 Deadlock detection: `innodb_deadlock_detect` (default **ON**) runs a wait-for-graph search on
        every lock wait; turning it off converts deadlocks into `innodb_lock_wait_timeout` waits
        (default **50 seconds** — absurdly long for a 150 ms stake-reservation budget).
        `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.15.11 The victim-selection rule: InnoDB rolls back the transaction with the **fewest rows
        modified/locked** — the opposite of PostgreSQL's "abort the detector", so retry logic must
        live in different places in the two engines. `[MYSQL]` `[PROVE]` `[TRAP]`
3.15.12 `innodb_rollback_on_timeout` (default **OFF**): a lock-wait timeout rolls back **only the
        last statement**, leaving the transaction alive and partially applied. This is a correctness
        landmine with no PostgreSQL equivalent. `[MYSQL]` `[GUC]` `[NUM]` `[TRAP]`
3.15.13 Reading `SHOW ENGINE INNODB STATUS`'s `LATEST DETECTED DEADLOCK` section line by line:
        `*** (1) TRANSACTION`, `LOCK WAIT`, `RECORD LOCKS space id N page no N n bits N index ...`,
        `lock_mode X locks rec but not gap`, `lock_mode X locks gap before rec`,
        `lock mode S waiting`, `*** WE ROLL BACK TRANSACTION (2)`.
        `[MYSQL]` `[DIAG]` `[SOURCE]` `[PROVE]`
3.15.14 The `performance_schema` lock tables that replaced log-scraping: `data_locks`,
        `data_lock_waits`, `metadata_locks`, and the `sys` views (`innodb_lock_waits`,
        `schema_table_lock_waits`). `[MYSQL]` `[SQL]` `[DIAG]`
3.15.15 `innodb_print_all_deadlocks` (default **OFF**) — the setting that turns "we had a deadlock
        last Tuesday" into data, and why it should be on in any system that moves money.
        `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.15.16 The comparison table: what is locked, where the lock lives, how phantoms are prevented, gap
        locking, escalation, detection trigger, victim choice, timeout default, and the observability
        surface — PostgreSQL versus InnoDB. `[MYSQL]` `[NUM]` `[PROVE]`

*(16 leaves)*

## §3.16 Serializable Snapshot Isolation, worked through

3.16.1 The problem SSI solves: snapshot isolation permits **write skew** and the read-only anomaly,
       which strict two-phase locking would not — but 2PL costs read locks. Cahill, Röhm and
       Fekete's insight was that SI anomalies always contain a **dangerous structure**.
       `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.16.2 The dangerous structure, stated precisely: two consecutive **rw-dependency** edges
       `T1 → T2 → T3` in the conflict graph, where `T3` commits first and `T2` is concurrent with
       both. Every SI anomaly contains one; therefore aborting one participant is sufficient.
       `[PROVE]` `[SOURCE]`
3.16.3 Why this is a *sufficient* condition and not an *exact* one: not every dangerous structure is
       an actual cycle, so PostgreSQL's `SERIALIZABLE` produces **false-positive serialisation
       failures**. This is the honest cost of the design, and the reason a retry loop is mandatory.
       `[PROVE]` `[TRAP]`
3.16.4 **SIREAD locks** (`predicate.c`): pairs of (object, transaction) recorded for everything a
       serializable transaction reads. They are held by a *separate lock manager* that supports only
       one mode, **never blocks, and cannot deadlock**. `[SOURCE]` `[PROVE]` `[NUM]`
3.16.5 Granularity and its promotion ladder: tuple → page → relation, controlled by
       `max_pred_locks_per_relation` (default **-2**, meaning `max_pred_locks_per_transaction / -2`)
       and `max_pred_locks_per_page` (default **2**), with `max_pred_locks_per_transaction` default
       **64**. Coarser granularity means fewer locks and *more* false positives.
       `[GUC]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.16.6 How phantoms are caught without gap locks: **index-range predicate locks** — an nbtree scan
       takes SIREAD locks on the pages it traverses, so an insert into that key range creates a
       conflict. Only B-tree (plus gin/gist/hash from PG 11) supports predicate locking; a
       **sequential scan takes a relation-level predicate lock**. `[SOURCE]` `[PROVE]` `[TRAP]`
3.16.7 The consequence that decides whether `SERIALIZABLE` is usable: a query with no usable index
       predicate-locks the whole table, so **adding the right index reduces false serialisation
       failures**. Indexing is a concurrency decision under SSI. `[PROVE]` `[NUM]`
3.16.8 The two conflict-detection directions: read-before-write is caught by the SIREAD lock;
       write-before-read is caught by examining the MVCC chain when the reader encounters a newer
       version. Both feed the same `rw-conflict` structures. `[SOURCE]` `[PROVE]`
3.16.9 The per-transaction state: `SERIALIZABLEXACT` with its in/out conflict flags, the
       `SerializableXidHash`, and the "committed but still tracked" transactions retained until no
       concurrent transaction can be affected. `[SOURCE]` `[RESEARCH]`
3.16.10 Why SSI must keep some state after commit, and the resulting failure mode:
        `serializable_buffers`/`pg_serial` exhaustion under long-running serializable transactions,
        surfacing as `ERROR: out of shared memory` with a `HINT` about
        `max_pred_locks_per_transaction`. `[DIAG]` `[TRAP]` `[RESEARCH]`
3.16.11 `SERIALIZABLE READ ONLY DEFERRABLE`: waits until it can take a snapshot that is provably safe,
        then never aborts and never causes others to abort. **The right tool for the QuizStakes
        end-of-day ledger reconciliation report.** `[SQL]` `[PROVE]` `[SOURCE]`
3.16.12 Cost, measured rather than feared: `pg_stat_database.xact_rollback` versus commits,
        SQLSTATE **40001** rates, and the published finding that SSI's overhead is small for
        workloads with short transactions and appropriate indexes. `[NUM]` `[DIAG]` `[RESEARCH]`
3.16.13 The InnoDB contrast: `SERIALIZABLE` there is implemented by converting plain `SELECT` into
        `SELECT ... FOR SHARE` (locking reads), i.e. real 2PL — so it **blocks and deadlocks**
        instead of aborting at commit. The same keyword, two entirely different mechanisms.
        `[MYSQL]` `[PROVE]` `[TRAP]` `[NUM]`

*(13 leaves)*

## §3.17 PostgreSQL WAL, checkpoints and crash recovery

3.17.1 The **WAL-before-data rule**, quoted from `access/transam/README`: "log entries must reach
       stable storage before the data-page changes they describe". Everything else in this section
       is machinery to enforce it cheaply. `[SOURCE]` `[PROVE]`
3.17.2 Why WAL is faster than writing data pages synchronously, argued rather than asserted:
       sequential append of a few hundred bytes versus random writes of 8 kB pages, and one fsync
       amortised over a group of commits. `[PROVE]` `[NUM]`
3.17.3 The **LSN** as a byte position in the logical WAL stream (`pg_lsn`, printed as `X/Y`),
       `pg_current_wal_lsn()`, `pg_wal_lsn_diff()`, and the per-page `pd_lsn` interlock: a dirty
       buffer may not be written until WAL is flushed past its `pd_lsn`.
       `[SOURCE]` `[SQL]` `[PROVE]`
3.17.4 WAL file geography: `pg_wal/` segments of **`wal_segment_size` = 16 MB** (settable at
       `initdb`), the 24-character hex name (timeline + logical id + segment), `.partial`,
       `.history` and `.backup` files, and `pg_walfile_name()`. `[NUM]` `[SQL]` `[SOURCE]`
3.17.5 The **record format**: `XLogRecord` (`xl_tot_len`, `xl_xid`, `xl_prev`, `xl_info`,
       `xl_rmid`, `xl_crc`) followed by block references (`XLogRecordBlockHeader`, up to **5** block
       references by default) and record data (up to **20** registered chunks).
       `[SOURCE]` `[NUM]` `[RESEARCH]`
3.17.6 Resource managers (`rmgr`) as the dispatch table for redo: `Heap`, `Heap2`, `Btree`, `Gin`,
       `Gist`, `XLOG`, `Transaction`, `CLOG`, `Standby`, `Sequence`, `LogicalMessage` — and
       `pg_waldump`'s per-rmgr statistics as the way to see **which subsystem is generating your
       WAL**. `[SOURCE]` `[DIAG]` `[NUM]`
3.17.7 The insertion protocol: `START_CRIT_SECTION` → modify the buffer → `XLogInsert` →
       `END_CRIT_SECTION`, with the rule that any error inside the critical section is a **PANIC**
       because shared buffers now hold unlogged changes. Quote the README on this.
       `[SOURCE]` `[PROVE]`
3.17.8 `NUM_XLOGINSERT_LOCKS` = **8**: WAL insertion is parallel across eight slots reserving space in
       the shared buffer, then serialised only for the copy. `WALInsert` wait events are the tell
       that this is the bottleneck. `[SOURCE]` `[NUM]` `[DIAG]` `[RESEARCH]`
3.17.9 `REGBUF_*` flags and what each suppresses: `REGBUF_FORCE_IMAGE`, `REGBUF_NO_IMAGE`,
       `REGBUF_WILL_INIT`, `REGBUF_STANDARD` (omit the hole between `pd_lower` and `pd_upper`),
       `REGBUF_KEEP_DATA`. This is how PostgreSQL keeps full-page images from being 8 kB each.
       `[SOURCE]` `[NUM]` `[PROVE]`
3.17.10 **Full-page writes** (`full_page_writes`, default **on**): the first modification of a page
        after a checkpoint logs the whole page, so replay can reconstruct a torn page from scratch.
        `RedoRecPtr` is the comparison point. `[GUC]` `[SOURCE]` `[PROVE]` `[NUM]`
3.17.11 **Torn pages** explained physically: an 8 kB page write is not atomic on a 4 kB-sector device,
        so a crash mid-write leaves a mixture of old and new. Full-page writes are the answer;
        turning them off is only safe if the storage guarantees atomic 8 kB writes. `[PROVE]`
        `[TRAP]` `[X-REF 11]`
3.17.12 The cost of full-page writes, with the arithmetic: at 230 `ledger_entry` inserts/sec spread
        over many pages just after a checkpoint, WAL volume spikes — the reason WAL rate is bursty
        and correlates with `checkpoint_timeout`. `wal_compression` (`off`/`pglz`/`lz4`/`zstd`)
        compresses **only** full-page images. `[GUC]` `[NUM]` `[PROVE]`
3.17.13 **Checkpoints**: what one actually does, in order — write all dirty buffers as of the redo
        point, fsync, write the checkpoint record, update `pg_control`, and recycle WAL below the
        redo point. `[SOURCE]` `[FLOW]` `[PROVE]`
3.17.14 The checkpoint GUCs with defaults and what each trades: `checkpoint_timeout` (**5 min**),
        `max_wal_size` (**1 GB**), `min_wal_size` (**80 MB**), `checkpoint_completion_target`
        (**0.9** since PG 14), `checkpoint_flush_after` (**256 kB**), `checkpoint_warning`
        (**30 s**). `[GUC]` `[NUM]`
3.17.15 The diagnosis loop: `log_checkpoints` (**on by default since PG 15**), the
        `checkpoint complete: wrote N buffers` log line read field by field, and
        `pg_stat_checkpointer`'s `num_timed` versus `num_requested` — *requested* checkpoints mean
        `max_wal_size` is too small. `[DIAG]` `[GUC]` `[VERSION-TRAP]` `[NUM]`
3.17.16 **ARIES** as the algorithm being implemented, with the three phases named:
        **analysis** (from the checkpoint record, find the redo point and the dirty-page/transaction
        tables), **redo** (replay forward, physiologically, idempotently via the page LSN check),
        **undo** (PostgreSQL does not need it — uncommitted tuples are simply never visible).
        `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.17.17 Why PostgreSQL has no undo phase and InnoDB does, traced back to §3.13.1 — MVCC-in-heap makes
        rollback a no-op. State this as the single deepest structural difference between the two
        engines. `[PROVE]`
3.17.18 `synchronous_commit`'s five values and exactly what each waits for: `off` (nothing —
        `wal_writer_delay`, default **200 ms**, bounds the loss window), `local` (local flush),
        `remote_write`, `on` (**default**: local flush + standby flush when
        `synchronous_standby_names` is set), `remote_apply`. Per-transaction settable.
        `[GUC]` `[NUM]` `[PROVE]` `[SQL]`
3.17.19 **Group commit** in PostgreSQL: `commit_delay` (default **0** µs) and `commit_siblings`
        (default **5**) deliberately delay a flush to batch it, plus the natural batching the WAL
        writer already performs. Contrast with MySQL's explicit group-commit stages.
        `[GUC]` `[NUM]` `[PROVE]`
3.17.20 `wal_sync_method` (`fdatasync` on Linux by default), `wal_buffers` (**-1** = 1/32 of
        `shared_buffers`, capped at 16 MB), `wal_writer_flush_after` (**1 MB**), and the
        **fsync-gate class of bugs**: pre-4.13 Linux discarded dirty pages after an I/O error and
        reported success to the *next* fsync, which is why PostgreSQL now PANICs on fsync failure
        (`data_sync_retry`, default **off**). `[GUC]` `[NUM]` `[TRAP]` `[X-REF 11]` `[RESEARCH]`

*(20 leaves)*

## §3.18 InnoDB durability internals

3.18.1 **Mini-transactions (mtr)** as InnoDB's unit of physical atomicity: a set of page
       modifications plus their redo records, committed together with the page latches held. Every
       B+tree operation is an mtr. There is no PostgreSQL construct with this name; the closest is
       the critical section. `[MYSQL]` `[SOURCE]` `[PROVE]`
3.18.2 The **redo log** as a fixed-size **ring** (historically `ib_logfile0/1`, since 8.0.30 the
       `#innodb_redo/` directory of 32 files), addressed by a monotonically increasing **LSN** that
       maps to a physical offset by modular arithmetic. `[MYSQL]` `[SOURCE]` `[NUM]`
3.18.3 `innodb_redo_log_capacity` (8.0.30+) replacing `innodb_log_file_size` ×
       `innodb_log_files_in_group`, resizable **online**, and **auto-sized in MySQL 8.4 to
       (logical processors / 2) GB capped at 16 GB**. Verify against the 8.4 reference manual.
       `[MYSQL]` `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.18.4 Why a ring means "the log can fill": if the oldest un-checkpointed LSN cannot advance,
       InnoDB throttles and then stalls all writes — the classic
       `Log writer overwriting data ... waiting` / async flush storm. A PostgreSQL WAL directory
       grows instead; InnoDB's blocks. `[MYSQL]` `[PROVE]` `[DIAG]` `[TRAP]`
3.18.5 The log buffer and the writer pipeline: `innodb_log_buffer_size` (default **16 MB**), the
       dedicated log writer/flusher/write-notifier/flush-notifier threads introduced in 8.0, and
       `innodb_log_wait_for_flush_spin_hwm`. `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.18.6 `innodb_flush_log_at_trx_commit`'s three values with their exact loss windows: **1**
       (default — write + fsync at commit, no loss), **2** (write to OS at commit, lose on OS
       crash only), **0** (flush once per second, lose up to a second). Map each to the QuizStakes
       ledger requirement and eliminate two of them. `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.18.7 The **doublewrite buffer**: every page is written twice — first sequentially to the
       doublewrite area, then to its real location — so a torn page can be recovered from the
       sequential copy. This is InnoDB's answer to §3.17.11's problem, and it is a *different*
       answer from full-page writes. `[MYSQL]` `[SOURCE]` `[PROVE]`
3.18.8 The comparison worth making explicitly: full-page writes put the copy **in the log** (bigger
       log, no extra write path); doublewrite puts it **in a separate file** (constant log size,
       double the page writes). Same problem, opposite trade. `[MYSQL]` `[PROVE]` `[NUM]`
3.18.9 Doublewrite in 8.0.20+: separate `#ib_16384_*.dblwr` files, `innodb_doublewrite_dir`,
       `innodb_doublewrite_files`, `innodb_doublewrite_pages`, `innodb_doublewrite_batch_size`, and
       `innodb_doublewrite = DETECT_ONLY` — detect torn pages without paying for the copy.
       `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.18.10 **Fuzzy checkpointing**: InnoDB never stops the world to checkpoint; it advances the
        checkpoint LSN as the **flush list** (pages ordered by oldest modification LSN) drains.
        `[MYSQL]` `[SOURCE]` `[PROVE]`
3.18.11 The flush machinery and its knobs: page cleaner threads, `innodb_lru_scan_depth` (default
        **1024**), `innodb_io_capacity` (**changed from 200 to 10000 in MySQL 8.4**),
        `innodb_io_capacity_max`, `innodb_max_dirty_pages_pct` (**90**),
        `innodb_max_dirty_pages_pct_lwm`, `innodb_flush_neighbors` (**0** on 8.0+),
        `innodb_adaptive_flushing`. `[MYSQL]` `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.18.12 **Binary log versus redo log**: two logs, two purposes (replication/PITR versus crash
        recovery), and therefore **two fsyncs per commit** unless they are grouped.
        `[MYSQL]` `[PROVE]` `[NUM]`
3.18.13 The **XA two-phase commit** between the binlog and InnoDB, step by step: InnoDB prepare
        (redo write + flush) → binlog write → binlog fsync → InnoDB commit. The binlog is the
        coordinator, and the binlog fsync is the commit point.
        `[MYSQL]` `[SOURCE]` `[FLOW]` `[PROVE]`
3.18.14 **Binlog group commit's three stages** — flush, sync, commit — with
        `binlog_group_commit_sync_delay` and `binlog_group_commit_sync_no_delay_count` as the
        deliberate-latency-for-throughput knobs, and `binlog_order_commits` (default **ON**).
        `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.18.15 `sync_binlog` (**default 1** since 5.7) plus `innodb_flush_log_at_trx_commit = 1` as the only
        configuration that loses nothing, and the exact inconsistency you get otherwise: a
        transaction present in the binlog but absent from the redo log, i.e. a replica ahead of its
        source. `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.18.16 Crash recovery in order: scan the redo log from the last checkpoint, apply redo to pages
        (using doublewrite for torn ones), then roll back uncommitted transactions using undo, then
        resolve XA-prepared transactions against the binlog. `innodb_force_recovery`'s six levels as
        the last resort, and why 4+ is data-destroying. `[MYSQL]` `[NUM]` `[FLOW]` `[TRAP]`
3.18.17 The durability comparison table: torn-page defence, log shape, log growth failure mode,
        commit fsync count, group commit mechanism, undo requirement, recovery phases, and the
        single setting that breaks durability in each engine.
        `[MYSQL]` `[NUM]` `[PROVE]`

*(17 leaves)*

## §3.19 PostgreSQL shared buffers, the clock sweep, and PG 18 asynchronous I/O

3.19.1 The three-part structure: the **buffer pool** (an array of `BLCKSZ` blocks), the **buffer
       descriptors** (`BufferDesc`: tag, state, wait-lock, content lock, `io_in_progress` condition
       variable), and the **buffer mapping hash table** (`buf_table`) keyed by `BufferTag`
       (relfilelocator, fork, block number). `[SOURCE]` `[NUM]`
3.19.2 `BufferTag` as the identity of a page and the reason a buffer lookup is a hash probe under one
       of the `BufMappingLock` partitions (**128** partitions), not a scan. `[SOURCE]` `[NUM]`
3.19.3 The atomic `state` word: 18-bit **refcount** (pins), 4-bit **`usage_count`**, and the
       `BM_*` flags — `BM_LOCKED`, `BM_DIRTY`, `BM_VALID`, `BM_TAG_VALID`, `BM_IO_IN_PROGRESS`,
       `BM_IO_ERROR`, `BM_JUST_DIRTIED`, `BM_PIN_COUNT_WAITER`, `BM_CHECKPOINT_NEEDED`,
       `BM_PERMANENT`. `[SOURCE]` `[NUM]`
3.19.4 **Pin versus content lock**, the distinction the README insists on: a pin says "this buffer
       may not be evicted or moved"; a content lock (shared / exclusive / share-exclusive) says
       "these bytes may not change under me". A scan holds pins across executor calls but not
       content locks. `[SOURCE]` `[PROVE]`
3.19.5 The **cleanup lock** as exclusive-content-lock-plus-sole-pin, and the three operations that
       need it: HOT pruning, page defragmentation, and vacuum's line-pointer truncation. A cursor
       parked on a page defers all three. `[SOURCE]` `[PROVE]` `[TRAP]`
3.19.6 **Clock sweep**, not LRU: `nextVictimBuffer` advances circularly; each pass decrements
       `usage_count`; a buffer with `usage_count = 0` and `refcount = 0` is the victim.
       `BM_MAX_USAGE_COUNT` = **5**, so a buffer survives at most five sweeps of neglect.
       `[SOURCE]` `[NUM]` `[PROVE]`
3.19.7 Why clock sweep instead of LRU lists, argued: LRU needs a lock on every access to reorder a
       list; the clock approximates recency with an atomic increment. Compare with InnoDB's
       midpoint-insertion LRU in §3.20 and state what each pays. `[PROVE]` `[NUM]`
3.19.8 `BufferAccessStrategy` **ring buffers** and their exact sizes, from the README: `BAS_BULKREAD`
       = **256 kB** ("to fit in L2 cache"), `BAS_BULKWRITE` = **16 MB** but not more than 1/8th of
       `shared_buffers`, `BAS_VACUUM` = `vacuum_buffer_usage_limit` (PG 16+, default **2 MB**).
       `[SOURCE]` `[GUC]` `[NUM]` `[RESEARCH]`
3.19.9 What the ring buys and the misconception it kills: a large sequential scan of
       `fundsledger.ledger_entry` **cannot** flush the whole buffer pool, because it reuses its own
       256 kB ring. "A big report evicted my cache" is a pre-8.3 fact. `[VERSION-TRAP]` `[TRAP]`
       `[PROVE]`
3.19.10 **Synchronize sequential scans** (`synchronize_seqscans`, default **on**): a second scan of
        the same relation starts where an in-progress scan currently is, so two concurrent reports
        share pages instead of doubling the I/O — and return rows in a different order, which is
        one legitimate source of "the same query returned rows in a different order".
        `[GUC]` `[PROVE]` `[TRAP]`
3.19.11 Dirty-page writeback paths, all four: the **checkpointer**, the **background writer**
        (`bgwriter_delay` **200 ms**, `bgwriter_lru_maxpages` **100**, `bgwriter_lru_multiplier`
        **2.0**), a **backend** evicting a dirty victim itself, and vacuum. Backend-performed writes
        are the pathological one, visible as `buffers_backend`/`pg_stat_io` writes by client
        backends. `[GUC]` `[NUM]` `[DIAG]` `[PROVE]`
3.19.12 `shared_buffers` (default **128 MB**) sizing, done honestly: the 25%-of-RAM heuristic, why it
        is a heuristic, and the **double-buffering** interaction with the OS page cache — a page can
        exist in both, and `effective_cache_size` (**4 GB** default) is the planner's estimate of
        *both* combined. `[GUC]` `[NUM]` `[PROVE]` `[X-REF 11]`
3.19.13 Huge pages: `huge_pages` (`try` by default), `huge_page_size`, the TLB-miss argument, and
        `/proc/meminfo`'s `HugePages_*` as the verification. A 12 GB heap alongside a large
        `shared_buffers` makes this measurable. `[GUC]` `[NUM]` `[X-REF 11]` `[RESEARCH]`
3.19.14 Prefetching before PG 18: `effective_io_concurrency` driving `posix_fadvise(WILLNEED)` for
        **bitmap heap scans only**, which is why "PostgreSQL does not prefetch" was half-true.
        `[GUC]` `[VERSION-TRAP]` `[PROVE]`
3.19.15 **PG 18's AIO subsystem**: `io_method` with `worker` (**the default**), `io_uring` (Linux
        5.1+, build-time `--with-liburing`) and `sync`; `io_workers` (default **3**);
        `io_max_concurrency`; `io_combine_limit` (**128 kB**, PG 17+). Backends submit into a shared
        queue and consume completions. `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.19.16 The default changes that follow and invalidate old advice: **`effective_io_concurrency` and
        `maintenance_io_concurrency` both moved from 1 to 16 in PG 18**, and sequential scans,
        bitmap scans and vacuum now issue readahead. PG 19 adds auto-scaling `io_method=worker`.
        `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.19.17 `pg_stat_io` (PG 16+) as the observability payoff: rows per backend type × object × context
        (`normal`, `vacuum`, `bulkread`, `bulkwrite`) with `reads`, `writes`, `writebacks`,
        `extends`, `hits`, `evictions`, `reuses`, `fsyncs`, and (PG 18) byte counters. This view is
        how §3.19.8–§3.19.11 are *proved* on a live system. `[SQL]` `[DIAG]` `[NUM]` `[RESEARCH]`
3.19.18 The QuizStakes buffer-pool arithmetic: a 90-day hot window of `ledger_entry` at 3.5 GB/day is
        ~315 GB — it does not fit in any buffer pool, so the cache-hit strategy must be
        **index + partition pruning**, not memory. State what *does* fit: `position`, `reservation`,
        and the hot partitions' index pages. `[NUM]` `[PROVE]`

*(18 leaves)*

## §3.20 The InnoDB buffer pool

3.20.1 Structure: `innodb_buffer_pool_size` (default **128 MB**) divided into
       `innodb_buffer_pool_instances` (default 1 below 1 GB, else 8), each instance an independent
       LRU list + free list + flush list with its own mutex, allocated in
       `innodb_buffer_pool_chunk_size` (**128 MB**) chunks. `[MYSQL]` `[GUC]` `[NUM]`
3.20.2 The consequence of chunking: `innodb_buffer_pool_size` is rounded to a multiple of
       chunk × instances, so the value you set is not always the value you get — and it is
       **resizable online**. `[MYSQL]` `[NUM]` `[TRAP]`
3.20.3 **Midpoint-insertion LRU**: the list is split into a **young (new)** sublist and an **old**
       sublist, with new pages inserted at the *midpoint* — the head of the old sublist — not the
       head of the list. `[MYSQL]` `[SOURCE]` `[PROVE]`
3.20.4 The two knobs and exactly what they defend against: `innodb_old_blocks_pct` (default **37**,
       i.e. 3/8 of the list is "old") and `innodb_old_blocks_time` (default **1000 ms** — a page
       must survive that long in the old sublist before a second access promotes it). Together they
       stop a one-off full scan from evicting the working set. `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.20.5 Compare directly with §3.19.8: PostgreSQL solves scan resistance with a **ring buffer**,
       InnoDB with **midpoint insertion plus a time gate**. Same goal, different mechanism, different
       failure mode. `[MYSQL]` `[PROVE]`
3.20.6 The **flush list** ordered by oldest modification LSN, driving §3.18.10's fuzzy checkpoint,
       and the **free list** as the source of clean frames. Three lists, three purposes.
       `[MYSQL]` `[SOURCE]` `[NUM]`
3.20.7 Read-ahead: **linear** (`innodb_read_ahead_threshold`, default **56** of the 64 pages in an
       extent accessed sequentially triggers prefetch of the next extent) and **random**
       (largely disabled in modern versions). `[MYSQL]` `[GUC]` `[NUM]` `[RESEARCH]`
3.20.8 `innodb_flush_method` (`fsync` historically, `O_DIRECT` recommended, and the 8.4-era
       `fsync`/`O_DIRECT` default question) and the double-buffering argument: with `O_DIRECT`
       InnoDB bypasses the OS page cache because it manages its own, unlike PostgreSQL which
       deliberately relies on the kernel's. **This is the single biggest architectural difference in
       memory management between the two engines.** `[MYSQL]` `[GUC]` `[PROVE]` `[RESEARCH]`
3.20.9 Buffer-pool warmup: `innodb_buffer_pool_dump_at_shutdown` /
       `innodb_buffer_pool_load_at_startup` (both **ON** by default) and
       `innodb_buffer_pool_dump_pct` (**25**) — a restart that does not start cold. PostgreSQL has
       no built-in equivalent (`pg_prewarm` is an extension).
       `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.20.10 Observability: `SHOW ENGINE INNODB STATUS`'s `BUFFER POOL AND MEMORY` block read field by
        field (`Free buffers`, `Database pages`, `Old database pages`, `Modified db pages`,
        `Buffer pool hit rate`, `young/s`, `not young/s`, `evicted without access`), plus
        `INFORMATION_SCHEMA.INNODB_BUFFER_POOL_STATS` and `INNODB_BUFFER_PAGE`.
        `[MYSQL]` `[DIAG]` `[SQL]`
3.20.11 `Innodb_buffer_pool_wait_free` as the "pool is too small / flushing is too slow" counter, and
        why hit rate alone is a bad signal. `[MYSQL]` `[DIAG]` `[NUM]` `[TRAP]`
3.20.12 The sizing rule that differs from PostgreSQL's: InnoDB wants **most** of RAM (70–80%) because
        it does not share caching duty with the kernel; PostgreSQL wants ~25% because it does.
        Applying the MySQL number to PostgreSQL is a real and common misconfiguration.
        `[MYSQL]` `[NUM]` `[TRAP]` `[PROVE]`
3.20.13 The rest of InnoDB's memory: the log buffer, the lock table, the dictionary cache
        (`innodb_dictionary_cache`/table definition cache), the AHI, and the change buffer — the
        answer to "why does MySQL use more RAM than `innodb_buffer_pool_size`".
        `[MYSQL]` `[NUM]` `[DIAG]`
3.20.14 `innodb_dedicated_server` as the auto-tuner that sets buffer pool, redo capacity and flush
        method from detected RAM, and why MySQL 8.4's new defaults reduce the need for it.
        `[MYSQL]` `[GUC]` `[VERSION-TRAP]` `[RESEARCH]`

*(14 leaves)*

## §3.21 Planner internals

3.21.1 The pipeline by function name: `pg_parse_query` → `parse_analyze` (raw parse tree → `Query`)
       → `pg_rewrite_query` (rule/view expansion) → `planner`/`standard_planner` → `PlannedStmt` →
       `ExecutorStart`. Each stage has an inspectable output. `[SOURCE]` `[FLOW]`
3.21.2 `subquery_planner` and the **prep** phase's rewrites in order:
       `pull_up_sublinks`, `pull_up_subqueries` (flattening a subquery-in-FROM into the parent
       jointree), `preprocess_expression`, constant folding (`eval_const_expressions`),
       `reduce_outer_joins`, `remove_useless_joins`, and (PG 18) `enable_self_join_elimination`.
       `[SOURCE]` `[NUM]` `[RESEARCH]`
3.21.3 Why a subquery sometimes cannot be pulled up — `LIMIT`, `DISTINCT ON`, volatile functions,
       set-returning functions, grouping — and the fact that a non-pulled-up subquery becomes an
       **optimisation barrier**. This is the honest version of the "CTEs are a fence" folklore.
       `[PROVE]` `[TRAP]`
3.21.4 CTE inlining (PG 12+): a CTE referenced once, without `MATERIALIZED`, side effects or
       recursion, is inlined like a subquery; `MATERIALIZED`/`NOT MATERIALIZED` are the explicit
       controls. State the version, because the old behaviour is still widely taught.
       `[VERSION-TRAP]` `[SQL]` `[PROVE]`
3.21.5 The core planner objects: `PlannerInfo`, `RelOptInfo` (one per base or join relation, holding
       `pathlist`, `cheapest_total_path`, `rows`, `reltarget`), `Path`/`AccessPath`, `RestrictInfo`,
       `EquivalenceClass`, `PathKey`, `SpecialJoinInfo`, `PlaceHolderVar`. `[SOURCE]` `[NUM]`
3.21.6 **`EquivalenceClass`** as the mechanism behind transitive predicate propagation: from
       `a.client_id = b.client_id AND a.client_id = 4711`, the planner derives
       `b.client_id = 4711` and can index-scan `b`. Nobody writes that predicate; the planner does.
       `[SOURCE]` `[PROVE]` `[SQL]`
3.21.7 **`PathKey`** as the representation of sort order, and the two things it buys: merge joins
       without an explicit sort, and `ORDER BY` satisfied by an index. An `ORDER BY` that disappears
       from a plan did not vanish — it was matched by a `PathKey`. `[SOURCE]` `[PROVE]` `[PLAN]`
3.21.8 The **path inventory** worth naming, because each is a plan node the reader will meet:
       `IndexPath`, `BitmapHeapPath`, `TidPath`, `TidRangePath`, `AppendPath`, `MergeAppendPath`,
       `MaterialPath`, `MemoizePath`, `GatherPath`, `GatherMergePath`, `SortPath`,
       `IncrementalSortPath`, `AggPath`, `GroupingSetsPath`, `MinMaxAggPath`, `WindowAggPath`,
       `SetOpPath`, `RecursiveUnionPath`, `LockRowsPath`, `ModifyTablePath`, `LimitPath`,
       `NestPath`, `MergePath`, `HashPath`. `[SOURCE]` `[NUM]`
3.21.9 `add_path`'s **pruning rule**, which is where most plans are actually decided: a path survives
       only if it wins on total cost, startup cost, sort order (`PathKeys`), parameterisation, or
       parallel-safety. A path dominated on *all* dimensions is discarded immediately.
       `[SOURCE]` `[PROVE]`
3.21.10 **`standard_join_search`**: System-R style bottom-up dynamic programming —
        `join_search_one_level` builds level-*k* joins from level-(*k*−1) results, keeping only the
        cheapest path per relation set, and `join_is_legal` enforces outer-join ordering
        constraints. `[SOURCE]` `[PROVE]` `[FLOW]`
3.21.11 Why the search space is what it is: without pruning, N-relation join orders grow as
        `(2N−2)! / (N−1)!`; DP over subsets reduces it to `O(3^N)` — 12 relations is ~531k subsets,
        which is where `geqo_threshold` comes from. **Do this arithmetic.** `[PROVE]` `[NUM]`
3.21.12 `from_collapse_limit` (**8**) and `join_collapse_limit` (**8**): explicit `JOIN` syntax is
        flattened into a single FROM list only up to this many items, so **query text can change the
        plan** — the reason a 15-table join sometimes needs the join order written by hand.
        `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.21.13 **GEQO**: above `geqo_threshold` (**12**) the planner switches to a genetic algorithm
        (`geqo_effort` **5**, `geqo_pool_size`, `geqo_generations`, `geqo_selection_bias`,
        `geqo_seed` **0.0**), which is **non-deterministic unless the seed is fixed** — a real cause
        of "the same query got a different plan". `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.21.14 The cost model constants with their PG 18 defaults, and what each unit means:
        `seq_page_cost` **1.0** (the unit), `random_page_cost` **4.0**, `cpu_tuple_cost` **0.01**,
        `cpu_index_tuple_cost` **0.005**, `cpu_operator_cost` **0.0025**,
        `parallel_setup_cost` **1000**, `parallel_tuple_cost` **0.1**,
        `min_parallel_table_scan_size` **8 MB**, `min_parallel_index_scan_size` **512 kB**,
        `effective_cache_size` **4 GB**. `[GUC]` `[NUM]` `[SOURCE]`
3.21.15 The cost **formulas**, written out and evaluated for one real QuizStakes query:
        sequential scan = `relpages × seq_page_cost + reltuples × cpu_tuple_cost`; index scan adds
        the index-page cost, the per-tuple index cost, and a **correlation-interpolated** heap cost;
        nested loop = `outer_cost + outer_rows × inner_cost`; hash join = build + probe + batch
        spill; merge join = sort or index scan on both sides plus the merge.
        `[PROVE]` `[NUM]` `[SOURCE]`
3.21.16 Why `random_page_cost = 4.0` is "wrong" on SSDs but not by 40×: the value models
        random-versus-sequential *net of caching*, which the docs state explicitly. The honest advice
        is 1.1–2.0 on NVMe **with `effective_cache_size` set correctly**, not 1.0.
        `[NUM]` `[PROVE]` `[TRAP]`
3.21.17 Selectivity from statistics, with the actual arithmetic: `null_frac`, `n_distinct`
        (negative values meaning "a fraction of rows"), `most_common_vals`/`most_common_freqs`
        (MCV) for equality on frequent values, `1/n_distinct` for equality on non-MCVs, and
        equi-depth `histogram_bounds` interpolation for ranges. `default_statistics_target` **100**
        buckets, per-column overridable to **10000**. `[SOURCE]` `[NUM]` `[PROVE]` `[SQL]`
3.21.18 Join selectivity: `eqjoinsel` using both sides' MCV lists and `n_distinct`, and the
        independence assumption that makes multi-predicate estimates collapse
        (`sel(A ∧ B) = sel(A) × sel(B)`). **This assumption is the single largest source of bad
        plans.** `[PROVE]` `[NUM]` `[TRAP]`
3.21.19 **Extended statistics** as the fix: `CREATE STATISTICS ... (ndistinct, dependencies, mcv)`,
        what each kind corrects, `pg_stats_ext`, and the limitation that they are not used for join
        selectivity. The QuizStakes case: `(position, currency)` on `ledger_entry`, which are
        strongly correlated. `[SQL]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.21.20 `ANALYZE`'s internals: a **random sample of `300 × statistics_target` rows** (30,000 at the
        default), two-stage sampling (blocks then rows), and the consequence that `n_distinct` on a
        7.2B-row table is an extrapolation that can be badly wrong — hence
        `ALTER TABLE ... ALTER COLUMN ... SET (n_distinct = ...)`.
        `[SOURCE]` `[NUM]` `[PROVE]` `[TRAP]`
3.21.21 **Plan caching**: the extended-query protocol's `PREPARE`/`BIND`, custom plans for the first
        **five** executions, then a generic plan if its cost is not worse than the average custom
        cost; `plan_cache_mode` (`auto` / `force_custom_plan` / `force_generic_plan`). This is the
        mechanism behind "the sixth execution got slow", and it reaches JDBC through
        `prepareThreshold`. `[GUC]` `[NUM]` `[PROVE]` `[JDBC]` `[TRAP]`
3.21.22 The MySQL planner, contrasted at the same depth: the classic greedy `optimizer_search_depth`
        (**62** = automatic) join optimizer, `optimizer_switch`'s flag list, condition filtering
        (`condition_fanout_filter`), histograms via `ANALYZE TABLE ... UPDATE HISTOGRAM`,
        `optimizer_trace` as a JSON dump of the actual decisions, and the **hypergraph optimizer**
        (DPhyp, `JoinHypergraph`, `CostingReceiver`) — experimental in 8.x,
        **available in Community Edition from MySQL 9.7**.
        `[MYSQL]` `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`

*(22 leaves)*

## §3.22 Executor internals

3.22.1 The **Volcano/iterator model**: every node implements `ExecProcNode` returning one
       `TupleTableSlot` at a time, so the plan tree is a pull-based pipeline and memory use is
       bounded by the blocking nodes, not the result size. `[SOURCE]` `[PROVE]`
3.22.2 The cost of the model, quantified: one indirect call per tuple per node — which is why PG 10+
       switched `ExecProcNode` to a per-node function pointer set at init, and why vectorised engines
       exist at all. `[SOURCE]` `[PROVE]` `[NUM]`
3.22.3 **Blocking versus streaming nodes**, and the practical rule that follows: `Sort`, `Hash`,
       `Materialize`, `HashAggregate` and `Unique`-over-sort must consume their input fully;
       `SeqScan`, `IndexScan`, `NestLoop`, `Limit` and `Append` stream. `LIMIT` is only cheap above
       streaming nodes. `[PROVE]` `[PLAN]` `[NUM]`
3.22.4 `TupleTableSlot`'s four flavours (`heaptuple`, `minimaltuple`, `virtual`, `buffer`) and why
       `Materialize` exists: converting a slot that references a pinned buffer into one that owns its
       memory. `[SOURCE]` `[PROVE]`
3.22.5 **Expression evaluation**: `ExprState` compiled into a linear array of `ExprEvalStep`s
       (PG 10+) rather than a recursive tree walk — the change that made expression-heavy queries
       measurably faster. `[SOURCE]` `[VERSION-TRAP]` `[PROVE]`
3.22.6 **JIT**: LLVM compilation of expression evaluation and tuple deforming, gated by
       `jit_above_cost` (**100000**), `jit_inline_above_cost` (**500000**),
       `jit_optimize_above_cost` (**500000**), `jit` (**on**), `jit_provider`. The cost gates are
       *plan* costs, not times. `[GUC]` `[NUM]` `[SOURCE]`
3.22.7 Why JIT is the most common cause of an inexplicable regression after an upgrade: a bad row
       estimate inflates the plan cost past the threshold, and the query pays 50–200 ms of
       compilation to save 5 ms of execution. `EXPLAIN ANALYZE`'s `JIT:` block (functions, timings)
       is the proof, and per-query `SET jit = off` is the fix. `[PLAN]` `[TRAP]` `[NUM]` `[DIAG]`
3.22.8 **Hash join** internals: build the hash table on the (estimated) smaller side, partition into
       `nbatch` batches when the table exceeds `work_mem × hash_mem_multiplier`, spill batches to
       temporary files, then probe batch by batch. `[SOURCE]` `[PROVE]` `[NUM]`
3.22.9 The batching numbers in the plan, read line by line: `Buckets: 8192 Batches: 4 Memory Usage:
       4096kB`. **`Batches > 1` means it spilled to disk**; `Batches` far above the estimate means
       the estimate was wrong. `[PLAN]` `[DIAG]` `[NUM]` `[PROVE]`
3.22.10 `hash_mem_multiplier` (**2.0** since PG 15; 1.0 when introduced in PG 13) and the reason it
        exists: hash tables have worse spill behaviour than sorts, so they deserve more memory than
        `work_mem` alone. State both defaults and their versions.
        `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.22.11 **Hash aggregate spilling** (PG 13+): before it, a mis-estimated `HashAggregate` could exceed
        `work_mem` without bound and OOM the backend; after it, it spills and merely gets slow.
        `enable_hashagg_disk`'s removal. This is a real "why did PG 12 crash and PG 13 not" answer.
        `[VERSION-TRAP]` `[PROVE]` `[TRAP]`
3.22.12 **Sort** internals: `tuplesort` with quicksort in memory, **external merge sort** with
        `work_mem`-sized runs and a merge pass when it spills, plus `Sort Method:` in the plan
        (`quicksort`, `top-N heapsort`, `external merge`) and `Disk: NkB`.
        `[SOURCE]` `[PLAN]` `[NUM]` `[PROVE]`
3.22.13 `top-N heapsort` as the `ORDER BY ... LIMIT n` specialisation (a bounded heap, `O(N log n)`),
        and why it disappears the moment `n` grows past `work_mem` — the mechanism behind
        `OFFSET` pagination degrading nonlinearly. `[PROVE]` `[NUM]` `[PLAN]`
3.22.14 **Incremental sort** (PG 13+): when the input is already sorted by a prefix of the requested
        keys, sort only within each group. `Presorted Key:` and `Full-sort Groups:` in the plan.
        `[VERSION-TRAP]` `[PLAN]` `[PROVE]`
3.22.15 **Memoize** (PG 14+): a hash cache of inner-side results for a parameterised nested loop,
        with `Cache Key`, `Hits`, `Misses`, `Evictions` and `Overflows` in `EXPLAIN ANALYZE`. It is
        not `Materialize`; state the difference. `[VERSION-TRAP]` `[PLAN]` `[NUM]` `[PROVE]`
3.22.16 **Parallel query** internals: `Gather`/`Gather Merge`, `parallel_leader_participation`
        (**on**), the shared tuple queue, `max_parallel_workers_per_gather` (**2**),
        `max_parallel_workers` (**8**), `max_worker_processes` (**8**), worker count scaling as
        `log₃(table size / min_parallel_table_scan_size)`, and Parallel Hash's shared hash table.
        `[GUC]` `[NUM]` `[PROVE]` `[SOURCE]`
3.22.17 What is **not** parallel-safe and therefore silently serialises a plan: `VOLATILE`/`PARALLEL
        UNSAFE` functions, writes, cursors, `FOR UPDATE`, and anything inside a serializable
        transaction. `EXPLAIN`'s absent `Gather` is the only symptom. `[PROVE]` `[TRAP]` `[PLAN]`
3.22.18 The MySQL executor for contrast: the 8.0 **iterator executor** (`EXPLAIN FORMAT=TREE`,
        `EXPLAIN ANALYZE` with `actual time`/`loops`), hash join (8.0.18+) with
        `join_buffer_size` and disk spill, no parallel query for general SELECTs (only
        `innodb_parallel_read_threads` for clustered-index scans and `COUNT(*)`), and the
        `temptable`/`internal_tmp_mem_storage_engine` on-disk-temp-table rules.
        `[MYSQL]` `[GUC]` `[NUM]` `[PLAN]` `[RESEARCH]`

*(18 leaves)*

## §3.23 Vacuum and purge internals

3.23.1 What `VACUUM` does, in the order it does it: prune HOT chains, collect dead TIDs, remove index
       entries pointing at them, mark line pointers `LP_UNUSED`, update the FSM and VM, freeze
       eligible tuples, advance `relfrozenxid`, and truncate trailing empty pages.
       `[SOURCE]` `[FLOW]` `[PROVE]`
3.23.2 The **two-pass** structure and why it is two passes: index entries must be removed *before*
       heap line pointers are reused, or an index entry would point at an unrelated row. This
       ordering is the whole reason vacuum is not a single scan. `[PROVE]` `[SOURCE]`
3.23.3 The dead-TID store: a sorted `ItemPointerData` array capped at **1 GB** before PG 17, replaced
       by **`TidStore`** — an adaptive radix tree keyed by block number with a per-block offset
       bitmap — which removed the cap and cut memory use dramatically. Multiple index passes on a
       large table are now rare. `[VERSION-TRAP]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.23.4 Why the old 1 GB cap mattered: `maintenance_work_mem` / 6 bytes per TID bounded a single pass,
       so vacuuming a table with 200M dead tuples scanned **every index multiple times**. Do the
       arithmetic for `fundsledger.ledger_entry`. `[NUM]` `[PROVE]`
3.23.5 `maintenance_work_mem` (**64 MB**), `autovacuum_work_mem` (**-1** = use
       `maintenance_work_mem`), and `max_parallel_maintenance_workers` (**2**) for
       `VACUUM (PARALLEL n)` — which parallelises **index** vacuuming only, and never for autovacuum.
       `[GUC]` `[NUM]` `[TRAP]`
3.23.6 The autovacuum architecture: the **launcher** wakes every `autovacuum_naptime` (**1 min**),
       divides it by the number of databases, and starts up to `autovacuum_max_workers` (**3**)
       workers; each worker picks tables from `pg_stat_all_tables`. `[SOURCE]` `[GUC]` `[NUM]`
3.23.7 The trigger formulas, written out: vacuum when
       `n_dead_tup > autovacuum_vacuum_threshold (50) + autovacuum_vacuum_scale_factor (0.2) ×
       reltuples`; analyze at `50 + 0.1 × reltuples`; and the insert-only trigger (PG 13+)
       `autovacuum_vacuum_insert_threshold` (**1000**) + `insert_scale_factor` (**0.2**).
       `[GUC]` `[NUM]` `[PROVE]`
3.23.8 Why the default scale factor is catastrophic at QuizStakes scale: 0.2 × 7.2B rows means
       **1.44 billion** dead tuples before autovacuum starts. The fix is per-table
       `autovacuum_vacuum_scale_factor = 0.01` plus a threshold, or partitioning so each partition is
       small. **Do the arithmetic before recommending anything.** `[NUM]` `[PROVE]` `[TRAP]` `[SQL]`
3.23.9 **Cost-based delay** internals: `vacuum_cost_page_hit` (**1**), `vacuum_cost_page_miss`
       (**2** since PG 14, previously 10), `vacuum_cost_page_dirty` (**20**), `vacuum_cost_limit`
       (**200**), `autovacuum_vacuum_cost_delay` (**2 ms** since PG 12), and the resulting
       **throughput ceiling in MB/s** — derive it, because it is why autovacuum "never finishes".
       `[GUC]` `[NUM]` `[PROVE]` `[VERSION-TRAP]`
3.23.10 The **failsafe** mode: past `vacuum_failsafe_age` (**1.6B**) vacuum abandons cost delays and
        **skips index vacuuming entirely** to get freezing done. Seeing this in the log means the
        cluster nearly died. `[GUC]` `[NUM]` `[DIAG]` `[PROVE]`
3.23.11 `VACUUM`'s option surface and what each is for: `FULL`, `FREEZE`, `ANALYZE`, `DISABLE_PAGE_SKIPPING`,
        `INDEX_CLEANUP { AUTO | ON | OFF }`, `TRUNCATE`, `PARALLEL`, `SKIP_LOCKED`, `BUFFER_USAGE_LIMIT`,
        `ONLY_DATABASE_STATS`, `PROCESS_TOAST`, `PROCESS_MAIN`, `SKIP_DATABASE_STATS`.
        `[SQL]` `[NUM]` `[RESEARCH]`
3.23.12 `VACUUM FULL` versus `CLUSTER` versus `pg_repack` versus PG 19's `REPACK`: which take
        `ACCESS EXCLUSIVE`, which need 2× disk, which rebuild indexes, and which can be interrupted
        safely. `[NUM]` `[PROVE]` `[VERSION-TRAP]` `[RESEARCH]`
3.23.13 The **progress views** as the answer to "is it stuck or slow": `pg_stat_progress_vacuum`
        (phase, `heap_blks_scanned`, `dead_tuple_bytes`, `indexes_total`, `indexes_processed`),
        `pg_stat_progress_analyze`, `pg_stat_progress_create_index`, `pg_stat_progress_cluster`,
        `pg_stat_progress_basebackup`, `pg_stat_progress_copy`. `[SQL]` `[DIAG]` `[NUM]`
3.23.14 `VACUUM VERBOSE`'s output read line by line: pages scanned/removed, tuples removed/remaining,
        `dead tuples cannot be removed yet, oldest xmin: N` (the long-transaction fingerprint),
        index scans, and the buffer/WAL/I/O timing block. `[DIAG]` `[SOURCE]` `[PROVE]`
3.23.15 Measuring bloat three ways and trusting them appropriately: `pg_stat_all_tables.n_dead_tup`
        (cheap, statistics-based), `pgstattuple` (exact, expensive, reads every page), and the
        popular estimate queries (fast, systematically wrong on tables with varying row width).
        `[SQL]` `[NUM]` `[TRAP]`
3.23.16 PG 19's **parallel autovacuum** (`autovacuum_max_parallel_workers`) and the new autovacuum
        scoring system that replaces "first eligible table wins" with prioritisation — the fix for
        the failure mode where one huge table starves everything else.
        `[VERSION-TRAP]` `[RESEARCH]` `[GUC]`
3.23.17 The InnoDB mirror, so the reader can answer the question in either engine: purge threads
        (§3.13.9) instead of autovacuum, undo tablespace truncation
        (`innodb_undo_log_truncate`, `innodb_max_undo_log_size` **1 GB**) instead of table
        truncation, `history list length` instead of `n_dead_tup`, and `OPTIMIZE TABLE` instead of
        `VACUUM FULL`. `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.23.18 The runbook this section must end with: the ten-minute "vacuum is not keeping up" diagnosis —
        check `n_dead_tup` and `last_autovacuum`, check for a long transaction or an abandoned
        replication slot or a prepared transaction, check the cost-delay ceiling, then decide between
        per-table settings, partitioning, and a manual vacuum window. `[DIAG]` `[SQL]` `[PROVE]`

*(18 leaves)*

## §3.24 PostgreSQL replication internals

3.24.1 The physical-replication pipeline by process: a backend inserts WAL → the **WAL sender**
       reads it (from the buffer or from disk) → the streaming replication protocol
       (`START_REPLICATION`, `XLogData`/`'w'` messages, keepalives, standby status updates) → the
       **WAL receiver** writes and flushes it → the **startup process** replays it.
       `[SOURCE]` `[FLOW]` `[NUM]`
3.24.2 `wal_level`'s three values and exactly what each adds: `minimal` (crash recovery only, no
       replication), `replica` (**default** — enough for streaming and archiving), `logical`
       (adds the information logical decoding needs, at a WAL-volume cost).
       `[GUC]` `[NUM]` `[PROVE]`
3.24.3 The **three LSNs per standby** in `pg_stat_replication` — `sent_lsn`, `write_lsn`,
       `flush_lsn`, `replay_lsn` — plus `write_lag`, `flush_lag`, `replay_lag`. Lag is four numbers,
       not one, and confusing them is why "the replica is caught up" is usually unverified.
       `[SQL]` `[DIAG]` `[NUM]` `[PROVE]`
3.24.4 **Replication slots**: persistent (`pg_create_physical_replication_slot`) versus temporary,
       `restart_lsn` and `xmin` retention, and the failure mode that fills the disk — an inactive
       slot pins WAL forever. `max_slot_wal_keep_size` (**-1** = unlimited, i.e. the dangerous
       default) is the safety valve. `[GUC]` `[SQL]` `[NUM]` `[TRAP]`
3.24.5 `wal_keep_size` (**0**), `archive_mode`/`archive_command`/`archive_library`,
       `wal_sender_timeout` (**60 s**), `wal_receiver_timeout`, `wal_receiver_status_interval`
       (**10 s**), and `primary_conninfo` — the configuration surface of a standby.
       `[GUC]` `[NUM]`
3.24.6 **Synchronous replication**: `synchronous_standby_names` grammar
       (`FIRST k (a,b,c)`, `ANY k (a,b,c)`, the bare list), the interaction with
       `synchronous_commit = on|remote_write|remote_apply`, and the property that matters — a
       committing transaction **waits for an ack, and is not cancellable without breaking the
       guarantee**. `[GUC]` `[SQL]` `[PROVE]` `[TRAP]`
3.24.7 The QuizStakes application: money-moving writes on `fundsledger` require
       `synchronous_commit = on` with `ANY 1 (...)` across two standbys; the `BalanceView` projection
       does not. **Per-transaction `synchronous_commit` is the tool that makes both true in one
       cluster.** `[SQL]` `[PROVE]` `[SOURCE]`
3.24.8 **Hot standby** internals: the startup process replaying while backends read, the
       `Standby` resource manager's `RUNNING_XACTS` records that let a standby build snapshots, and
       `KnownAssignedXids`. A read on a replica needs a snapshot, and that snapshot comes from WAL.
       `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.24.9 **Recovery conflicts** — the mechanism behind `ERROR: canceling statement due to conflict with
       recovery` / `DETAIL: User query might need to see row versions that must be removed`:
       replay of a vacuum record that removes rows a standby query still needs.
       `[DIAG]` `[PROVE]` `[TRAP]`
3.24.10 The two ways out and their costs: `max_standby_streaming_delay` (**30 s** — delay replay,
        increasing lag) and `hot_standby_feedback` (**off** by default — tell the primary to retain
        those rows, increasing *primary* bloat). There is no free option; state the trade.
        `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.24.11 `pg_stat_database_conflicts` and the conflict taxonomy (tablespace, lock, snapshot,
        bufferpin, deadlock) as the way to see which kind is happening. `[SQL]` `[DIAG]`
3.24.12 **Timelines**: promotion increments the timeline ID, writes a `.history` file, and makes the
        old primary's WAL divergent — which is why you cannot just restart the old primary as a
        standby, and what `pg_rewind` is for. `[SOURCE]` `[PROVE]` `[NUM]`
3.24.13 **Logical decoding** internals: the WAL sender runs the decoding machinery, `XLogReader`
        feeds records into the **`ReorderBuffer`** (a hash table keyed by xid, buffering changes per
        transaction and emitting them **only at COMMIT, in commit order**), which calls an **output
        plugin** (`pgoutput` for native logical replication, `wal2json`/`decoderbufs` for CDC).
        `[SOURCE]` `[FLOW]` `[PROVE]`
3.24.14 `logical_decoding_work_mem` (**64 MB**) and the spill-to-disk behaviour, plus **streaming of
        in-progress transactions** (PG 14+, `streaming = on`) that decodes before commit —
        the fix for a 10M-row backfill stalling every CDC consumer.
        `[GUC]` `[NUM]` `[VERSION-TRAP]` `[PROVE]`
3.24.15 `REPLICA IDENTITY` (`DEFAULT` / `USING INDEX` / `FULL` / `NOTHING`) as the setting that
        decides what an `UPDATE`/`DELETE` looks like downstream, and the failure it causes:
        `ERROR: cannot update table ... because it does not have a replica identity`. `FULL` logs
        every old column, at a real WAL cost. `[SQL]` `[NUM]` `[DIAG]` `[TRAP]`
3.24.16 Logical replication's limits, stated plainly because they decide architecture: sequences are
        not replicated (until PG 19-era work), DDL is not replicated, large objects are not, and
        conflicts stop the apply worker with `ERROR: duplicate key value violates unique
        constraint` until resolved (`ALTER SUBSCRIPTION ... SKIP`, or PG 18's conflict
        logging/`pg_stat_subscription_stats`).
        `[NUM]` `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
3.24.17 What replication cannot fix, connected back to §2.21.7: a replica is a lagged snapshot, so
        read-your-own-writes must be solved by routing (`pg_current_wal_lsn()` +
        `pg_wal_replay_wait()` in PG 18, or primary-pinning), never by hope. `[PROVE]` `[X-REF 22]`

*(17 leaves)*

## §3.25 MySQL replication internals

3.25.1 The pipeline by thread: the source's **dump thread** → the replica's **I/O (receiver)
       thread** → the **relay log** → the **SQL (applier) coordinator** → **worker threads**.
       Four moving parts, each with its own lag. `[MYSQL]` `[SOURCE]` `[FLOW]`
3.25.2 The **binary log** as a *logical* log (not a physical page log), which is the structural
       difference from PostgreSQL's WAL and the reason MySQL needs two logs where PostgreSQL needs
       one. `[MYSQL]` `[PROVE]`
3.25.3 `binlog_format`: `ROW` (**default since 5.7**), `STATEMENT`, `MIXED`, and the
       non-determinism problems (`NOW()`, `UUID()`, `LIMIT` without `ORDER BY`) that killed
       statement-based replication. `[MYSQL]` `[GUC]` `[NUM]` `[TRAP]`
3.25.4 `binlog_row_image` (`FULL` default, `MINIMAL`, `NOBLOB`) as MySQL's `REPLICA IDENTITY`
       equivalent, with the same trade: smaller log versus downstream usability.
       `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]`
3.25.5 Binlog event types worth naming because CDC consumers see them: `FORMAT_DESCRIPTION`,
       `PREVIOUS_GTIDS`, `GTID_LOG_EVENT`, `QUERY_EVENT`, `TABLE_MAP_EVENT`, `WRITE_ROWS`,
       `UPDATE_ROWS`, `DELETE_ROWS`, `XID_EVENT`, `ROTATE_EVENT`. `mysqlbinlog` as the reader.
       `[MYSQL]` `[DIAG]` `[NUM]`
3.25.6 **GTIDs**: `source_uuid:transaction_id`, `gtid_mode`, `enforce_gtid_consistency`,
       `gtid_executed`/`gtid_purged`, the `mysql.gtid_executed` table, and what GTIDs actually buy —
       failover without hand-computing binlog file/position.
       `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.25.7 What GTIDs forbid, and why it surprises people: no `CREATE TABLE ... SELECT` (before 8.0.21),
       no non-transactional/transactional mixing, no `CREATE TEMPORARY TABLE` inside a transaction.
       `[MYSQL]` `[TRAP]` `[RESEARCH]`
3.25.8 The **relay log** and its metadata: `relay_log_info_repository = TABLE` (the default since
       8.0, storing position in `mysql.slave_relay_log_info` **transactionally**) versus the old
       file-based repository — the change that made crash-safe replication possible.
       `[MYSQL]` `[NUM]` `[VERSION-TRAP]` `[PROVE]`
3.25.9 **Multi-threaded apply**: `replica_parallel_workers` (**default 4 in 8.4**, i.e. parallel by
       default), `replica_parallel_type = LOGICAL_CLOCK`, and
       `replica_preserve_commit_order` (**ON**) which keeps commit order identical to the source.
       `[MYSQL]` `[GUC]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
3.25.10 **Writeset-based dependency tracking**
        (`binlog_transaction_dependency_tracking = WRITESET`, computed on the *source* by hashing
        modified rows) as what makes parallel apply effective on workloads with a single hot
        schema — plus its deprecation status in 8.4. Verify before writing.
        `[MYSQL]` `[GUC]` `[VERSION-TRAP]` `[RESEARCH]`
3.25.11 **Semi-synchronous replication**: the `rpl_semi_sync_source_*` plugin variables —
        `wait_point` (`AFTER_SYNC` default versus `AFTER_COMMIT`),
        `timeout` (**10000 ms**), `wait_for_replica_count` (**1**) — and the property that makes it
        *semi*: on timeout it **silently falls back to asynchronous** and stops guaranteeing
        anything. `[MYSQL]` `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.25.12 Why `AFTER_SYNC` versus `AFTER_COMMIT` is a correctness question and not a tuning question:
        with `AFTER_COMMIT` other sessions can see a transaction the replica has not acknowledged,
        so a failover can lose a *read-visible* commit. `[MYSQL]` `[PROVE]` `[TRAP]`
3.25.13 **`Seconds_Behind_Source` is a lie**, mechanically: it measures the timestamp difference of
        the event the applier is currently executing, so it reads 0 while the I/O thread is
        disconnected and jumps wildly during long transactions. Use
        `performance_schema.replication_applier_status_by_worker` and GTID set differences instead.
        `[MYSQL]` `[DIAG]` `[TRAP]` `[PROVE]`
3.25.14 **Group Replication** internals in outline: a Paxos-derived group communication system,
        certification-based conflict detection at commit, single-primary versus multi-primary mode,
        flow control, and `group_replication_consistency`'s levels. The MySQL answer to
        consensus-backed HA. `[MYSQL]` `[X-REF 22]` `[RESEARCH]`
3.25.15 The comparison table for the two replication stacks: log type, one log or two, slot/retention
        mechanism, sync options and their guarantees, parallel apply, conflict handling, failover
        mechanics, DDL handling, and the lag metric you should actually trust.
        `[MYSQL]` `[NUM]` `[PROVE]`

*(15 leaves)*

## §3.26 Distributed internals: 2PC, sharding and consensus, at the SQL layer

3.26.1 **`PREPARE TRANSACTION`** internals: the transaction's state is written to WAL and shared
       memory, and — if it survives a checkpoint — to a file in `pg_twophase/` named by the
       hexadecimal xid, restored at startup. `max_prepared_transactions` (**default 0 — the
       feature is off**). `[SOURCE]` `[GUC]` `[NUM]` `[SQL]`
3.26.2 What a prepared transaction holds while it waits, and why it is more dangerous than a long
       transaction: locks, an xid that pins `xmin`, and **no session to kill**. It survives restart.
       `pg_prepared_xacts` plus `ROLLBACK PREPARED` is the only exit.
       `[PROVE]` `[SQL]` `[DIAG]` `[TRAP]`
3.26.3 XA in Java, concretely: `XADataSource`, `XAResource.prepare/commit/rollback`, Narayana or
       Atomikos as the coordinator, and the recovery log the coordinator must keep — because an XA
       system without a durable coordinator log is strictly worse than no XA.
       `[JDBC]` `[PROVE]` `[X-REF 07]`
3.26.4 MySQL's `XA START/END/PREPARE/COMMIT`, its historical bugs (prepared transactions lost on
       binlog rotation before 5.7), and the internal XA of §3.18.13 that every commit already uses.
       Two different things share the name. `[MYSQL]` `[NUM]` `[TRAP]` `[RESEARCH]`
3.26.5 Why QuizStakes does **not** use 2PC across services, argued from the domain: `FundsLedger` is
       the sole writer of money (§4.5), and the outbox pattern plus idempotency keys gives
       eventual consistency with a bounded reconciliation instead of a distributed lock across
       payment rails. `[SOURCE]` `[PROVE]` `[X-REF 22]`
3.26.6 The **outbox** at the database level, which is the part this guide owns: the same transaction
       writes `ledger_entry` and an `outbox` row; a relay reads the outbox (`FOR UPDATE SKIP
       LOCKED`) or the WAL (logical decoding) and publishes. The atomicity comes from the
       transaction, not from the broker. `[SQL]` `[PROVE]` `[X-REF 14]`
3.26.7 `SELECT ... FOR UPDATE SKIP LOCKED` internals: the row lock is attempted, the tuple is skipped
       on conflict rather than waited on, so N workers get disjoint sets without coordination. State
       what it does **not** give you: ordering, and exactly-once. `[SQL]` `[PROVE]` `[NUM]`
3.26.8 Sharding coordinators, at mechanism level: Citus (a coordinator node, distributed tables,
       reference tables, shard placement, `citus_shards`), Vitess (VTGate/VTTablet, vindexes),
       and PgDog/pgcat-style proxies — and the one query shape each cannot do well (a cross-shard
       join with an unpushable predicate). `[X-REF 22]` `[RESEARCH]`
3.26.9 Why cross-shard transactions cost what they cost: 2PC latency is at least two round trips
       plus a durable coordinator write, so a 150 ms stake-reservation budget forbids it. Compute
       the budget explicitly. `[NUM]` `[PROVE]`
3.26.10 Consensus-backed SQL, in one paragraph each with the mechanism named: CockroachDB
        (Raft per range, MVCC on RocksDB/Pebble, hybrid-logical clocks), Spanner (Paxos, TrueTime,
        external consistency), YugabyteDB (Raft, PostgreSQL-compatible query layer), Aurora
        (a shared log-structured storage layer under an unmodified engine).
        `[X-REF 22]` `[X-REF 18]` `[RESEARCH]`
3.26.11 **Clocks and commit order**, because it is the deepest reason distributed SQL is hard:
        wall-clock skew means "later" is not well-defined without a mechanism — TrueTime's
        uncertainty interval, hybrid logical clocks, or a single serialisation point. A single-node
        database gets this free from the WAL's LSN order. `[PROVE]` `[X-REF 22]`
3.26.12 What "read your own write" means across a sharded system, and the three implementations:
        sticky routing, LSN/GTID token passing, and read-at-timestamp. Each is a different API
        contract, not just a config. `[PROVE]` `[X-REF 12]`
3.26.13 The honest conclusion for this domain: 7.2B rows/year and 13,600 writes/sec at peak are
        **within single-primary PostgreSQL's reach** with partitioning and correct indexing, so the
        distributed options above are answers to a question QuizStakes does not yet have. Say so,
        with the arithmetic. `[NUM]` `[PROVE]` `[SOURCE]`

*(13 leaves)*

## §3.27 Observability internals

3.27.1 The **wait-event taxonomy** as the organising idea of database diagnosis: every backend is
       either on CPU or waiting on exactly one named thing, and the class tells you which subsystem
       to look at. Classes: `LWLock`, `Lock`, `BufferPin`, `Activity`, `Extension`, `Client`,
       `IPC`, `Timeout`, `IO`. `[SOURCE]` `[NUM]` `[PROVE]`
3.27.2 `pg_wait_events` (PG 17+) as the in-database catalogue of every event with its description —
       so "what is `LWLock:WALWrite`" is a query, not a search. `[SQL]` `[VERSION-TRAP]` `[RESEARCH]`
3.27.3 The dozen wait events worth recognising on sight and what each means:
       `Lock:transactionid` (row contention), `Lock:relation` (DDL), `LWLock:LockManager`
       (§3.14.8), `LWLock:BufferMapping`, `LWLock:WALInsert`, `LWLock:WALWrite`,
       `IO:DataFileRead`, `IO:WALSync`, `IPC:ClientRead` (the client is slow, not the database),
       `Timeout:VacuumDelay`, `BufferPin`, `LWLock:SubtransSLRU`.
       `[DIAG]` `[NUM]` `[PROVE]`
3.27.4 How PostgreSQL samples them: `pg_stat_activity.wait_event_type`/`wait_event` is an
       **instantaneous** value, so useful diagnosis means **sampling** it (1 Hz) into a history —
       the Active Session History pattern that `pg_wait_sampling`/`pgsentinel` implement.
       `[PROVE]` `[TRAP]` `[RESEARCH]`
3.27.5 **`pg_stat_statements` internals**: the **query jumble** walks the parse tree hashing
       structure while replacing constants with `$n`, producing a 64-bit `queryid` — which is
       therefore stable across constant values, **unstable across object renames or OID changes**,
       and can be negative. `compute_query_id` (**`auto`**). `[SOURCE]` `[NUM]` `[PROVE]`
3.27.6 The consequences of jumbling nobody expects: `IN (1,2,3)` and `IN (1,2,3,4)` were different
       entries before PG 16's list-normalisation; utility statements were not normalised before
       PG 16; and `pg_stat_statements.max` (**5000**) evicting entries silently loses history.
       `[VERSION-TRAP]` `[NUM]` `[TRAP]` `[RESEARCH]`
3.27.7 The columns that matter and the order to read them in: `total_exec_time` (rank by this, not
       `mean_exec_time`), `calls`, `rows`, `shared_blks_hit`/`read`/`dirtied`/`written`,
       `wal_bytes`, `temp_blks_*`, and the PG 17+ `stddev`/percentile-adjacent fields.
       `[SQL]` `[DIAG]` `[NUM]`
3.27.8 The overhead, stated honestly: a shared hash table plus an exclusive LWLock on entry update,
       visible as `LWLock:pg_stat_statements` under extreme statement rates — and still worth it.
       `[NUM]` `[PROVE]` `[TRAP]`
3.27.9 `auto_explain` internals: `log_min_duration`, `log_analyze`, `log_buffers`, `log_timing`
       (the expensive one — per-node `gettimeofday` calls), `log_nested_statements`,
       `sample_rate`. The recipe for production is `log_analyze = on`, `log_timing = off`,
       `sample_rate < 1`. `[GUC]` `[NUM]` `[PROVE]` `[TRAP]`
3.27.10 The statistics collector's redesign in **PG 15**: cumulative statistics moved from a
        collector process to **shared memory**, `pg_stat_reset*` semantics, and the fact that
        statistics now survive restart (and are preserved by `pg_upgrade` in PG 18).
        `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
3.27.11 `track_io_timing` (**off** by default) as the switch that turns plan and statistics I/O
        numbers from block counts into milliseconds, and `pg_test_timing` as the way to check
        whether your clock source makes it cheap. `[GUC]` `[DIAG]` `[NUM]`
3.27.12 The view inventory to know by purpose: `pg_stat_activity`, `pg_stat_database`,
        `pg_stat_all_tables`/`_indexes`, `pg_statio_*`, `pg_stat_bgwriter`/`pg_stat_checkpointer`,
        `pg_stat_io`, `pg_stat_wal`, `pg_stat_replication`/`_slots`/`_subscription`,
        `pg_stat_user_functions`, `pg_locks`, `pg_prepared_xacts`, `pg_stat_ssl`.
        `[SQL]` `[NUM]`
3.27.13 MySQL's `performance_schema` internals: instruments and consumers, `setup_instruments` /
        `setup_consumers` / `setup_objects` / `setup_threads`, and the memory it costs
        (`performance_schema_max_*` sizing). Instrumentation you enable, not instrumentation you get.
        `[MYSQL]` `[SQL]` `[NUM]` `[RESEARCH]`
3.27.14 The `performance_schema` tables that answer the same questions as above:
        `events_statements_summary_by_digest` (the `pg_stat_statements` equivalent, with
        `DIGEST`/`DIGEST_TEXT` as MySQL's normalisation), `events_waits_*`, `file_summary_by_*`,
        `table_io_waits_summary_by_*`, `data_locks`, `replication_applier_status_by_worker`, plus
        the `sys` schema views built on them. `[MYSQL]` `[SQL]` `[DIAG]` `[NUM]`
3.27.15 `EXPLAIN ANALYZE`'s own cost as an internals fact: per-node timing calls can dominate a
        cheap-node-heavy plan, which is why `EXPLAIN (ANALYZE, TIMING OFF)` exists and why
        `actual time` on a 10M-loop nested node is inflated. Measure the measurement.
        `[PLAN]` `[NUM]` `[PROVE]` `[TRAP]`
3.27.16 The QuizStakes observability contract this section must produce: for each of the four
        incidents named in the PART 3 preamble, the *one* view or command that identifies it in
        under a minute, and the number that confirms it. `[DIAG]` `[SQL]` `[PROVE]`

*(16 leaves)*

---

**PART 3 total: 12+14+16+16+14+16+16+14+14+16+15+18+15+17+16+13+20+17+18+14+22+18+18+17+15+13+16
= 430 leaves**

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf below ships **complete, compiling Java 21** — records, sealed interfaces,
pattern matching, `ByteBuffer`/`FileChannel` for the page layer, no pseudocode and no `...`
elisions — and is followed by a **Diff vs the real one** table. The point is not to write a
competitor to PostgreSQL; it is that having implemented the slotted page, the B+tree split, the WAL
and its recovery loop, the visibility check, the lock manager and the join-order enumerator, none of
PART 3 is mysterious any more. All domain examples use the QuizStakes entities and numbers from
`src/scenario/scenario.md`.

## §4.1 A slotted page and a disk-oriented B+tree

4.1.1 `[BUILD]` `SlottedPage` over a `ByteBuffer` of 8,192 bytes, mirroring §3.2 exactly: a 24-byte
      header with `lsn`, `checksum`, `flags`, `lower`, `upper`, `special`, a forward-growing
      4-byte slot array, backward-growing records, `insert`, `read`, `delete` (tombstone the slot),
      `compact`, and `freeSpace`. `[BUILD]` `[NUM]`
4.1.2 `[BUILD]` `PageFile` — a `FileChannel`-backed pager with `readPage(int)`/`writePage(int,
      SlottedPage)`/`allocatePage()`, so the tree below it works on real bytes, not on objects.
      `[BUILD]`
4.1.3 `[BUILD]` `BPlusTree<K extends Comparable<K>, V>` with a real disk layout: internal pages
      holding `n` keys and `n+1` child page numbers, leaf pages holding key/value pairs plus a
      `nextLeaf` pointer, a meta page holding the root page number and height.
      `[BUILD]` `[NUM]`
4.1.4 `[BUILD]` `search`, `rangeScan(from, to)` following `nextLeaf`, `insert` with a recursive
      split that propagates a separator upward and grows the root when it splits, and `delete` with
      merge-or-redistribute when occupancy falls below half. `[BUILD]` `[PROVE]`
4.1.5 `[BUILD]` The **rightmost-page 90/10 split** of §3.6.10 implemented as a branch in
      `chooseSplitPoint`, plus a benchmark that inserts 1M sequential keys and 1M random keys and
      prints pages allocated and average fill for each. The gap between the two numbers *is* the
      lesson. `[BUILD]` `[NUM]` `[PROVE]`
4.1.6 `[BUILD]` **Suffix truncation** on split for a composite key
      `record LedgerKey(long clientId, long createdAtMicros, long entryId)`: emit the shortest
      separator that still distinguishes the halves, and report fan-in with and without it.
      `[BUILD]` `[NUM]` `[PROVE]`
4.1.7 `[BUILD]` A `height()` and `pageCount()` assertion test that loads 7.2M `LedgerKey`s and
      verifies the height matches the §3.6.14 arithmetic. A build exercise that does not check
      against the theory is a toy. `[BUILD]` `[PROVE]`
4.1.8 **Diff vs the real one**: no Lehman & Yao right-links or latch crabbing (this tree is
      single-threaded), no WAL and therefore no crash safety, no `LP_DEAD` marking, no
      deduplication or posting lists, no incomplete-split repair, no vacuum/recycling interlock, no
      `amcostestimate`, no `TOAST`, no operator classes or collations, `Comparable` instead of
      three-way `support` functions, and no bulk-load path (`ambuild` sorts and builds bottom-up
      rather than inserting). State **why** the real one bothers with each.
      `[NUM]` `[PROVE]`

*(8 leaves)*

## §4.2 A WAL with ARIES-style crash recovery

4.2.1 `[BUILD]` `record LogRecord(long lsn, long prevLsn, long txnId, RecordType type, int pageId,
      byte[] before, byte[] after)` with a `sealed interface RecordType` covering `BEGIN`,
      `UPDATE`, `COMMIT`, `ABORT`, `CHECKPOINT_BEGIN`, `CHECKPOINT_END`, `FULL_PAGE_IMAGE`, plus a
      CRC32 per record. `[BUILD]` `[NUM]`
4.2.2 `[BUILD]` `WalWriter` with an append buffer, `flushUpTo(lsn)`, an explicit
      `FileChannel.force(true)` as the fsync, and a counter of fsyncs performed — so group commit
      can be measured rather than believed. `[BUILD]` `[NUM]`
4.2.3 `[BUILD]` The **WAL-before-data** interlock: `BufferManager.write(page)` refuses to write a
      page whose `pageLsn` exceeds `walWriter.flushedLsn`, throwing rather than silently violating
      the rule. Assert it in a test. `[BUILD]` `[PROVE]`
4.2.4 `[BUILD]` `Checkpointer` writing a fuzzy checkpoint (a `CHECKPOINT_BEGIN`, the dirty-page
      table and active-transaction table, a `CHECKPOINT_END`) and truncating the log below the
      redo point. `[BUILD]` `[FLOW]`
4.2.5 `[BUILD]` `RecoveryManager` with the three ARIES phases as three methods — `analysis()`
      rebuilding the tables from the last checkpoint, `redo()` replaying every record whose
      `lsn > page.lsn`, `undo()` walking `prevLsn` chains backwards for losers and writing
      compensation records. `[BUILD]` `[PROVE]`
4.2.6 `[BUILD]` A **crash test harness**: run 10,000 `ledger_entry` inserts, kill the process at a
      random point (`Runtime.halt`, in a spawned JVM), recover, and assert that the set of visible
      entries is exactly the set of committed ones and that entries still sum to zero. Run it 100
      times. `[BUILD]` `[PROVE]` `[SOURCE]`
4.2.7 `[BUILD]` A **torn-page simulator**: write only the first half of a page, then recover with
      and without full-page images, and show that one recovers and one detects corruption. This is
      §3.17.11 made real. `[BUILD]` `[PROVE]` `[NUM]`
4.2.8 **Diff vs the real one**: no physiological logging (this is a physical before/after image, so
      records are far larger), no `rmgr` dispatch, no parallel insertion slots
      (`NUM_XLOGINSERT_LOCKS`), no timeline handling, no archiving or PITR, no replication stream,
      no `synchronous_commit` levels, no doublewrite alternative, no PANIC-on-fsync-failure policy,
      and no `pg_control`. `[NUM]` `[PROVE]`

*(8 leaves)*

## §4.3 An MVCC visibility engine

4.3.1 `[BUILD]` `record Version(long xmin, long xmax, int nattsFlags, byte[] payload)` and a
      `HeapTable` of version chains keyed by row id, mirroring §3.3's header semantics with real
      `XMIN_COMMITTED`/`XMAX_INVALID`/`XMIN_FROZEN` flag bits. `[BUILD]` `[NUM]`
4.3.2 `[BUILD]` `TransactionManager` with lazy xid assignment, a `CommitLog` of two-bit states
      (`IN_PROGRESS`, `COMMITTED`, `ABORTED`, `SUB_COMMITTED`) packed into a byte array, and
      `Snapshot(xmin, xmax, long[] xip)` built by scanning the active-transaction array.
      `[BUILD]` `[NUM]`
4.3.3 `[BUILD]` `isVisible(Version v, Snapshot s)` implementing `HeapTupleSatisfiesMVCC`'s branches
      in the same order as §3.12.6, including hint-bit short-circuiting and the lock-only case, with
      a unit test per branch. `[BUILD]` `[PROVE]`
4.3.4 `[BUILD]` Two isolation levels from the *same* engine, proving §3.12's central claim: `READ
      COMMITTED` takes a new snapshot per statement, `REPEATABLE READ` reuses one — and a test that
      reproduces read skew under the first and not the second. `[BUILD]` `[PROVE]`
4.3.5 `[BUILD]` `Vacuum.run(oldestSnapshotXmin)` removing versions invisible to every live snapshot,
      plus a `bloat()` metric, plus a test that opens a long-lived `REPEATABLE READ` transaction and
      shows vacuum reclaiming **nothing** — §3.12.17 in 30 lines. `[BUILD]` `[PROVE]` `[NUM]`
4.3.6 `[BUILD]` The **write-skew** demonstration on the domain's real invariant: two concurrent
      stake reservations each read `CLIENT_CASH_AVAILABLE = 120.00` and each reserve 100.00; show
      the negative balance under snapshot isolation, then show it prevented by (a) a `CHECK`
      constraint, (b) `FOR UPDATE`, and (c) the atomic conditional `UPDATE`. Three fixes, one bug.
      `[BUILD]` `[PROVE]` `[SOURCE]`
4.3.7 **Diff vs the real one**: no on-disk pages or TOAST, no SLRU paging of the commit log, no
      subtransactions or multixacts, no 32-bit xid wraparound or freezing pressure, no HOT or
      pruning, no index visibility or index-only scans, no SSI, and a global lock instead of
      partitioned latches. `[NUM]` `[PROVE]`

*(7 leaves)*

## §4.4 A lock manager with a deadlock detector

4.4.1 `[BUILD]` `LockTable` with a `LOCKTAG`-style `record LockTag(TagType type, long a, long b)`,
      a conflict matrix over the eight PostgreSQL table modes as a `boolean[8][8]`, per-object wait
      queues, and 16 hash partitions each with its own `ReentrantLock` — mirroring §3.14.6.
      `[BUILD]` `[NUM]`
4.4.2 `[BUILD]` `acquire(txn, tag, mode, timeoutMillis)` implementing grant-if-compatible,
      FIFO-queue-otherwise, and `lock_timeout` as a real timeout, with `release(txn)` releasing
      everything at transaction end (strict 2PL). `[BUILD]` `[PROVE]`
4.4.3 `[BUILD]` `DeadlockDetector.check(waiter)` building the waits-for graph from the queues and
      running an iterative DFS for a cycle, invoked only after `deadlockTimeoutMillis = 1000` —
      the same optimistic-waiting design as §3.14.14. `[BUILD]` `[NUM]` `[PROVE]`
4.4.4 `[BUILD]` **Soft-edge reordering**: before aborting anyone, try to resolve the cycle by
      reordering a wait queue, and report which resolution was used. `[BUILD]` `[PROVE]`
4.4.5 `[BUILD]` A **fast-path** tier: weak modes recorded in a per-transaction 16-slot array with
      an overflow counter, plus a benchmark showing throughput collapse once overflow starts —
      §3.14.8 reproduced on a laptop. `[BUILD]` `[NUM]` `[PROVE]`
4.4.6 `[BUILD]` The QuizStakes deadlock reproduction: two threads reserving stakes against
      `CLIENT_CASH_AVAILABLE` and `CLIENT_BONUS_AVAILABLE` in opposite order, then the fix
      (a canonical lock order by position name) with an assertion that no deadlock occurs in 10,000
      iterations. `[BUILD]` `[PROVE]` `[SOURCE]`
4.4.7 **Diff vs the real one**: no `PROCLOCK`/`LOCALLOCK` split, no row locks in tuple headers, no
      multixacts, no predicate locks, no lock granularity promotion, no `pg_locks` projection, no
      recovery-time lock reacquisition, and a `ReentrantLock` where the real one uses spinlocks and
      LWLocks with wait queues in shared memory. `[NUM]` `[PROVE]`

*(7 leaves)*

## §4.5 A cost-based join-order enumerator

4.5.1 `[BUILD]` The catalog input: `record RelStats(String name, long rows, int pages, Map<String,
      Double> ndistinct)` populated with the domain's real cardinalities — `ledger_entry`
      7.2e9, `position` 2.4e6 × 11, `reservation` 2.8e6/day, `transactions` 95e3/day,
      `application` 2.4e6, `restriction` — so the enumerator plans real queries.
      `[BUILD]` `[NUM]` `[SOURCE]`
4.5.2 `[BUILD]` `Selectivity` with the §3.21.17 formulas: MCV lookup, `1/ndistinct` for equality,
      histogram interpolation for ranges, and the independence assumption made explicit and
      *labelled* in the output. `[BUILD]` `[PROVE]` `[NUM]`
4.5.3 `[BUILD]` `Cost` implementing the §3.21.15 formulas with PostgreSQL's real constants
      (`seq_page_cost = 1.0`, `random_page_cost = 4.0`, `cpu_tuple_cost = 0.01`,
      `cpu_index_tuple_cost = 0.005`, `cpu_operator_cost = 0.0025`) for `SeqScan`, `IndexScan`,
      `NestLoop`, `HashJoin` and `MergeJoin` as a sealed interface of `Plan` records.
      `[BUILD]` `[NUM]`
4.5.4 `[BUILD]` `DPJoinOrder.search(rels, joinPredicates)` — System-R dynamic programming over
      subsets encoded as a bitmask, keeping the cheapest plan per subset and per interesting sort
      order (`PathKey`-equivalent), and enforcing a connectivity check so Cartesian products are
      only considered when nothing else applies. `[BUILD]` `[PROVE]`
4.5.5 `[BUILD]` A left-deep-only mode and a bushy mode, with a printout of **subsets examined** for
      both at 4, 8 and 12 relations — the §3.21.11 arithmetic measured instead of quoted.
      `[BUILD]` `[NUM]` `[PROVE]`
4.5.6 `[BUILD]` A `geqoThreshold = 12` fallback: a small genetic search (population, crossover,
      mutation, fixed seed) that reports the best plan found and its cost gap versus the DP optimum
      on a 10-relation query. `[BUILD]` `[NUM]` `[PROVE]`
4.5.7 `[BUILD]` A **plan explainer** that prints the chosen tree in `EXPLAIN`-like indented form
      with estimated rows and cost per node, side by side with the real PostgreSQL plan for the
      same query against the same statistics. Where they diverge, explain which model is missing
      what. `[BUILD]` `[PLAN]` `[PROVE]`
4.5.8 **Diff vs the real one**: no `EquivalenceClass` inference or transitive predicates, no
      parameterised/LATERAL paths, no partial (parallel) paths, no `PathKey` machinery beyond a
      string, no outer-join legality checks (`SpecialJoinInfo`), no subquery pull-up, no partition
      pruning or partitionwise joins, no extended statistics, no plan caching, and no
      `amcostestimate` delegation. `[NUM]` `[PROVE]`

*(8 leaves)*

## §4.6 A buffer pool: clock sweep versus LRU versus midpoint insertion

4.6.1 `[BUILD]` `BufferPool` with a `BufferDesc[]` (`tag`, `pin`, `usageCount`, `dirty`, `valid`),
      a `HashMap<BufferTag, Integer>` mapping table split into 128 partitions, and
      `pin`/`unpin`/`markDirty`/`flush` — the §3.19.1 structure, no more.
      `[BUILD]` `[NUM]`
4.6.2 `[BUILD]` `ClockSweepStrategy` with `nextVictimBuffer`, decrement-on-pass, and
      `BM_MAX_USAGE_COUNT = 5`; `LruStrategy` with a real intrusive list; and
      `MidpointLruStrategy` with a young/old split at `oldBlocksPct = 37` and an
      `oldBlocksTimeMs = 1000` gate. Three strategies behind one interface.
      `[BUILD]` `[NUM]`
4.6.3 `[BUILD]` `RingStrategy` implementing the 256 kB `BAS_BULKREAD` ring (32 buffers at 8 kB) for
      sequential scans. `[BUILD]` `[NUM]`
4.6.4 `[BUILD]` A workload generator over the domain: 90% Zipfian point reads of
      `fundsledger.position` (2.4M clients, hot 1%), 10% appends to `ledger_entry`, and one
      full-table report scan every 30 seconds. `[BUILD]` `[NUM]` `[SOURCE]`
4.6.5 `[BUILD]` The measurement: hit rate and evictions-of-hot-pages per strategy, with and without
      the ring, printed as a table. **The report scan must destroy the LRU and leave clock-sweep +
      ring and midpoint-LRU intact** — §3.19.9 and §3.20.4 proved on the same harness.
      `[BUILD]` `[NUM]` `[PROVE]`
4.6.6 `[BUILD]` A `BackgroundWriter` thread with `bgwriterDelayMs = 200` and
      `lruMaxPages = 100`, plus a counter of backend-performed dirty evictions — showing that the
      counter rises when the writer is too slow, which is exactly what
      `pg_stat_io` writes-by-client-backend means. `[BUILD]` `[DIAG]` `[NUM]`
4.6.7 **Diff vs the real one**: no shared memory or multiple processes, no atomic state word or
      header spinlock, no content locks or cleanup locks, no `io_in_progress` condition variables,
      no checkpointer/fsync-request queue, no AIO or `io_uring`, no OS-page-cache interaction, and
      no per-relation `smgr` layer. `[NUM]` `[PROVE]`

*(7 leaves)*

## §4.7 The diagnostic harnesses

4.7.1 `[BUILD]` A JDBC + Testcontainers harness (`postgres:18`) that runs one SQL script and dumps
      `pageinspect` output for a chosen relation: `page_header`, `heap_page_items`, and
      `bt_page_stats` for every level — a repeatable "show me the bytes" tool.
      `[BUILD]` `[JDBC]` `[SQL]` `[X-REF 16]`
4.7.2 `[BUILD]` A HOT-versus-non-HOT experiment: create `fundsledger.position` at
      `fillfactor = 100` and at `70`, run 100,000 updates of a non-indexed column, and report
      `n_tup_hot_upd / n_tup_upd`, table size, and index size for both. Assert the ratio.
      `[BUILD]` `[SQL]` `[NUM]` `[PROVE]`
4.7.3 `[BUILD]` A bloat-and-vacuum experiment: delete 50% of a 10M-row table, measure with
      `pgstattuple`, vacuum, measure again, `VACUUM FULL`, measure again — three numbers that
      settle the "vacuum reclaims space" argument permanently. `[BUILD]` `[SQL]` `[NUM]` `[PROVE]`
4.7.4 `[BUILD]` A snapshot-and-xmin observer: open a `REPEATABLE READ` transaction, then poll
      `pg_stat_activity.backend_xmin`, `pg_stat_all_tables.n_dead_tup` and
      `pg_database.datfrozenxid` from another connection on a 1-second timer while a writer churns.
      Plot the divergence. `[BUILD]` `[SQL]` `[DIAG]`
4.7.5 `[BUILD]` A deadlock/serialisation-failure retry harness: a `@Retryable`-equivalent loop that
      distinguishes SQLSTATE `40001` from `40P01` from `23505`, re-reads inside the retry, caps
      attempts, and records the retry-rate metric — plus a test that induces each of the three.
      `[BUILD]` `[JDBC]` `[NUM]` `[PROVE]` `[X-REF 08]`
4.7.6 `[BUILD]` A plan-stability regression test: for the five hot QuizStakes queries, run
      `EXPLAIN (FORMAT JSON)` in CI, assert on node types and estimated-versus-actual row ratios
      (not on timings), and fail the build when a `Seq Scan` appears where an `Index Scan` was
      asserted. `[BUILD]` `[PLAN]` `[X-REF 16]` `[PROVE]`
4.7.7 `[BUILD]` A WAL-volume attribution tool: sample `pg_stat_wal` and `pg_waldump --stats` before
      and after a workload and print WAL bytes per rmgr and per statement class, so "which query
      generates our WAL" is answerable. `[BUILD]` `[DIAG]` `[NUM]`

*(7 leaves)*

---

**PART 4 total: 8+8+7+7+8+7+7 = 52 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

Every question in §5.1 is an internals question, so the depth floor is the sibling syllabi's
**[L2]** — explain the mechanism — and the write pass marks each answer **[L2]** or **[L3]**
(prove it or trace it to source) as it writes; nothing here is answerable by naming a thing.
§5.2's assertions are what you should be able to state cold, with no preamble; §5.3 is the schedule
that keeps all of it available six months from now.

## §5.1 The internals question bank

One question per leaf. The write pass answers each in 3–10 lines with the mechanism, the constant,
and the source — never "it depends".

5.1.1 Walk me through what is on an 8 kB PostgreSQL heap page, byte 0 to byte 8191.
5.1.2 How wide is a heap tuple header, and what makes it 24 rather than 23?
5.1.3 Why does adding a nullable column change `t_hoff`?
5.1.4 Reorder these six columns to minimise padding, and state the bytes saved.
5.1.5 Where does `~180 bytes/row` for `ledger_entry` actually go?
5.1.6 What is a hint bit, and why can a `SELECT` produce write I/O?
5.1.7 What is a HOT update, and what are its two preconditions?
5.1.8 What does `LP_REDIRECT` do, and what would break without it?
5.1.9 Why does `fillfactor = 70` help `position` and hurt `ledger_entry`?
5.1.10 What are the two bits per page in the visibility map, and what does each enable?
5.1.11 `Index Only Scan` with `Heap Fetches: 4102` — what is wrong and what is the fix?
5.1.12 Why is `ctid` not a row identifier?
5.1.13 At what size does a value get TOASTed, and what are the four storage strategies?
5.1.14 Why is `substr()` on an `EXTERNAL` column cheaper than on an `EXTENDED` one?
5.1.15 Why does updating a row with a 2 MB JSONB column not rewrite the JSONB?
5.1.16 What is a high key, and how does it make Lehman & Yao's concurrency work?
5.1.17 Why is a rightmost B-tree split 90/10?
5.1.18 What is `BTREE_VERSION = 4`, and which features require it?
5.1.19 What is suffix truncation, and what does it buy?
5.1.20 What is a posting list, and when is one formed?
5.1.21 Explain bottom-up index deletion and the version it arrived in.
5.1.22 Why does an index not shrink when you delete rows?
5.1.23 How would you measure index bloat, and how would you fix it online?
5.1.24 What does `kill_prior_tuple` do, and why is it disabled on a standby?
5.1.25 What does PG 18 skip scan change about the leftmost-prefix rule, and what does it not?
5.1.26 When does a bitmap scan go lossy, and how do you see it?
5.1.27 Why is BRIN ~50 MB where the B-tree is ~200 GB, and when is BRIN useless?
5.1.28 What is GIN's pending list, and why can a read pay for a write?
5.1.29 What is in an InnoDB 16 kB index page?
5.1.30 What is the page directory for, and how does it differ from PostgreSQL's line pointers?
5.1.31 What are `DB_TRX_ID` and `DB_ROLL_PTR`, and how wide are they?
5.1.32 Why does a UUID primary key cost more in InnoDB than in PostgreSQL?
5.1.33 What is the difference between `COMPACT` and `DYNAMIC` for a BLOB column?
5.1.34 Why does InnoDB raise `Row size too large` where PostgreSQL silently TOASTs?
5.1.35 Construct a `SnapshotData` for three concurrent transactions and evaluate one tuple's
        visibility against it.
5.1.36 Why is `GetSnapshotData` a reason to care about connection count?
5.1.37 What happens at 65 savepoints in one transaction?
5.1.38 What is a multixact, and how does one get created in this domain?
5.1.39 Why is the XID window 2.1 billion and not 4.3 billion?
5.1.40 What does freezing do, and name the four age thresholds with values.
5.1.41 Trace the exact causal chain from `idle in transaction` to a bad query plan.
5.1.42 Where does InnoDB keep old row versions, and what does that change about rollback cost?
5.1.43 What is `history list length`, and what is a bad value?
5.1.44 Why is a next-key lock necessary at `REPEATABLE READ`, and what does it cost?
5.1.45 What is an insert-intention lock, and why does it cause deadlocks?
5.1.46 Where does PostgreSQL store a row lock, and why does `pg_locks` not show millions of rows?
5.1.47 Why is `deadlock_timeout` not "how long a deadlock is tolerated"?
5.1.48 Who gets aborted in a PostgreSQL deadlock, and who in InnoDB?
5.1.49 What is `LWLock:LockManager` contention, and how does a partitioned table cause it?
5.1.50 Explain SSI's dangerous structure and why false positives are unavoidable.
5.1.51 Why does adding an index reduce serialisation failures?
5.1.52 What does `SERIALIZABLE` mean in InnoDB, and why is that a different mechanism?
5.1.53 State the WAL-before-data rule and the field that enforces it.
5.1.54 What is a full-page write, and what problem does it solve?
5.1.55 Doublewrite versus full-page writes — same problem, what is the trade?
5.1.56 Why does MySQL fsync twice per commit, and how does group commit help?
5.1.57 Why does PostgreSQL have no undo phase in recovery?
5.1.58 Walk through clock sweep, and say why it is not LRU.
5.1.59 Why can a full-table report not flush the whole PostgreSQL buffer pool?
5.1.60 What does `io_method = worker` change in PG 18, and which two defaults moved from 1 to 16?
5.1.61 Why is `random_page_cost = 4.0` not simply wrong on NVMe?
5.1.62 Derive the number of join-order subsets for 12 relations and explain `geqo_threshold`.
5.1.63 How does `join_collapse_limit` let query text change a plan?
5.1.64 Estimate the selectivity of `position = 'CLIENT_CASH_AVAILABLE' AND currency = 'GBP'` and say
        why the planner gets it wrong.
5.1.65 What does `ANALYZE` sample, and why can `n_distinct` be badly wrong at 7.2B rows?
5.1.66 What is a generic plan, when is it chosen, and how does that reach JDBC?
5.1.67 `Batches: 16` on a hash join — what happened and what do you change?
5.1.68 Why did a query get slower after an upgrade turned on JIT?
5.1.69 What does `Memoize` do that `Materialize` does not?
5.1.70 Compute autovacuum's dead-tuple trigger for a 7.2B-row table and say what you would set.
5.1.71 Derive autovacuum's throughput ceiling from the cost constants.
5.1.72 What changed about vacuum's dead-TID storage in PG 17, and why did it matter?
5.1.73 What is failsafe vacuum, and what does it skip?
5.1.74 Which four LSNs does `pg_stat_replication` expose, and which one is "caught up"?
5.1.75 How does an inactive replication slot fill a disk, and which GUC bounds it?
5.1.76 What is a recovery conflict, and what are the two cures and their costs?
5.1.77 Explain the reorder buffer and why logical decoding emits at COMMIT.
5.1.78 What is `REPLICA IDENTITY FULL` for, and what does it cost?
5.1.79 Why is `Seconds_Behind_Source` untrustworthy, and what do you use instead?
5.1.80 What does semi-synchronous replication guarantee after its timeout expires?
5.1.81 Why is `AFTER_COMMIT` a correctness problem and not a tuning choice?
5.1.82 What does a prepared transaction hold, and why is it worse than a long transaction?
5.1.83 Why does QuizStakes use an outbox instead of 2PC across services?
5.1.84 What exactly does `FOR UPDATE SKIP LOCKED` guarantee, and what does it not?
5.1.85 Given the domain's numbers, do you need to shard? Show the arithmetic.
5.1.86 What is a query jumble, and name two things that change a `queryid`.
5.1.87 How do you rank slow queries correctly, and why is `mean_exec_time` the wrong column?
5.1.88 Which wait event would you expect for each of the four incidents in the preamble?
5.1.89 What does `EXPLAIN ANALYZE` itself cost, and when do you turn timing off?
5.1.90 You have five minutes and one connection to a production PostgreSQL that is "slow". What do
        you run, in order, and what does each answer rule out?

*(90 leaves)*

## §5.2 One-line assertions to be able to state cold

5.2.1 A heap page is a slotted page: 24-byte header, forward-growing 4-byte line pointers,
       backward-growing tuples, and the free hole between `pd_lower` and `pd_upper`.
5.2.2 A heap tuple header is 23 bytes, `MAXALIGN`ed to 24; a nulls bitmap pushes `t_hoff` to 32.
5.2.3 `MaxHeapTuplesPerPage` = 291 on an 8 kB build.
5.2.4 Hint bits mean a read can dirty a page.
5.2.5 HOT requires no indexed column to change and the new version to fit on the same page.
5.2.6 The visibility map is two bits per page and is what makes index-only scans possible.
5.2.7 `ctid` is a physical address, not an identity.
5.2.8 TOAST engages above ~2 kB per row and stores chunks of ~2000 bytes in a side table.
5.2.9 `default_toast_compression` is `pglz` in PG 18 and `lz4` from PG 19.
5.2.10 A rightmost B-tree split is 90/10; a middle split is 50/50.
5.2.11 Deduplication forms posting lists lazily, only to avoid a page split.
5.2.12 Bottom-up index deletion (PG 14+) is what stops version churn from growing indexes forever.
5.2.13 An index never returns space to the filesystem without a rebuild.
5.2.14 PG 18 skip scan helps when the omitted prefix has few distinct values, and only then.
5.2.15 InnoDB's clustered index *is* the table, and every secondary entry carries the full PK.
5.2.16 InnoDB locks index records, never rows.
5.2.17 A next-key lock is a record lock plus the gap before it.
5.2.18 Insert-intention locks do not conflict with each other but do conflict with gap locks.
5.2.19 PostgreSQL row locks live in `t_xmax`, so there is no lock escalation and no lock memory
        limit.
5.2.20 `NUM_LOCK_PARTITIONS` is 16; the fast path was 16 slots and is `max_locks_per_transaction`-
        scaled in PG 18.
5.2.21 PostgreSQL aborts the deadlock's *detector*; InnoDB aborts the *smallest* transaction.
5.2.22 SSI uses SIREAD locks that never block and can therefore never deadlock.
5.2.23 `SERIALIZABLE` is optimistic in PostgreSQL and pessimistic (2PL) in InnoDB.
5.2.24 WAL must reach stable storage before the data pages it describes; `pd_lsn` enforces it.
5.2.25 Full-page writes put the torn-page defence in the log; doublewrite puts it in a file.
5.2.26 PostgreSQL needs no undo phase because uncommitted tuples are simply never visible.
5.2.27 MySQL commits with two fsyncs — redo and binlog — coordinated by internal XA.
5.2.28 `sync_binlog = 1` plus `innodb_flush_log_at_trx_commit = 1` is the only lossless setting.
5.2.29 PostgreSQL evicts by clock sweep with `BM_MAX_USAGE_COUNT = 5`; InnoDB uses midpoint-insertion
        LRU at `innodb_old_blocks_pct = 37`.
5.2.30 A big sequential scan uses a 256 kB ring buffer and cannot evict the working set.
5.2.31 InnoDB wants most of RAM; PostgreSQL wants about a quarter, because one bypasses the page
        cache and the other relies on it.
5.2.32 The planner assumes predicate independence; extended statistics is how you tell it otherwise.
5.2.33 `ANALYZE` samples 300 × `statistics_target` rows — 30,000 by default, regardless of table
        size.
5.2.34 A prepared statement gets custom plans for five executions, then possibly a generic one.
5.2.35 `Batches > 1` on a hash join means it spilled to disk.
5.2.36 Autovacuum's default 0.2 scale factor means 1.44 billion dead rows on a 7.2B-row table.
5.2.37 A long transaction, an inactive replication slot, and a prepared transaction all block vacuum
        the same way.
5.2.38 Lag is four LSNs, not one number.
5.2.39 Logical decoding emits at commit, in commit order, buffering in the reorder buffer until then.
5.2.40 `Seconds_Behind_Source` measures the applier's current event timestamp, not the backlog.

*(40 leaves)*

## §5.3 Retention drills

5.3.1 **The page drill** — draw an 8 kB heap page from memory with every header field and its width,
       then check it against `page_header`. Weekly until it is automatic.
5.3.2 **The arithmetic drill** — from `~180 bytes/row` and 19.8M rows/day, derive pages/day, GB/day,
       TB/year and index bytes/day, without notes.
5.3.3 **The visibility drill** — given a tuple's `t_xmin`/`t_xmax`/flags and a snapshot, decide
       visibility in under 15 seconds; ten randomised cases.
5.3.4 **The lock drill** — for six statement pairs on `fundsledger.position`, state whether they
       block, in which engine, and which lock names appear in `pg_locks`/`data_locks`.
5.3.5 **The plan drill** — read one unfamiliar `EXPLAIN (ANALYZE, BUFFERS)` per day and state, in
       order: estimate versus actual on the worst node, the node that dominates time, and one change.
5.3.6 **The constants drill** — recite the twelve numbers that matter (`BLCKSZ`,
       `MaxHeapTuplesPerPage`, `TOAST_TUPLE_THRESHOLD`, `BM_MAX_USAGE_COUNT`, `deadlock_timeout`,
       `random_page_cost`, `geqo_threshold`, `autovacuum_vacuum_scale_factor`,
       `autovacuum_freeze_max_age`, `innodb_lock_wait_timeout`, `innodb_old_blocks_pct`,
       `replica_parallel_workers`) with their values and units.
5.3.7 **The version-trap drill** — for each of the fifteen stale claims in §2.24.4, state the year
       and version in which it stopped being true.
5.3.8 **The incident drill** — given one of the four preamble incidents, produce the diagnosis
       sequence and the confirming number, out loud, in 90 seconds.
5.3.9 **The teach-back drill** — explain MVCC, WAL and the buffer pool to a non-database engineer in
       three minutes each, with no jargon and one number each.
5.3.10 **The build drill** — re-implement §4.3's `isVisible` from scratch, from memory, once a
        month. If it takes more than 20 minutes, PART 3 has not landed yet.

*(10 leaves)*

---

**PART 5 total: 90+40+10 = 140 leaves**

---

## Diagram manifest

Diagrams the write pass must produce as standalone SVGs (never inline `<svg>`, never ASCII art),
embedded at the point of explanation. Numbered `D-NN-slug.svg`, topic-scoped.

| ID | Diagram | Anchored at |
|---|---|---|
| D-01 | The relational query pipeline: parse → rewrite → plan → execute, with the artifact of each stage | §1.13, §3.21.1 |
| D-02 | Logical execution order of a `SELECT` versus written order | §1.9 |
| D-03 | The four join types as set diagrams over `position` and `reservation` | §1.4 |
| D-04 | Index B-tree over `(client_id, created_at)` with a range scan traced through it | §1.20, §3.6 |
| D-05 | The 8 kB heap page, byte-accurate: header, line pointers, hole, tuples | §3.2 |
| D-06 | One `ledger_entry` tuple's byte layout, header field by header field | §3.3 |
| D-07 | A HOT update chain with a `LP_REDIRECT` root, before and after pruning | §3.4 |
| D-08 | TOAST: main tuple, 18-byte pointer, chunk rows in the side table | §3.5 |
| D-09 | A leaf split with the high key and the parent downlink insertion | §3.6.8 |
| D-10 | 90/10 versus 50/50 split for a sequential key stream | §3.6.10 |
| D-11 | An InnoDB 16 kB index page with infimum/supremum and the page directory | §3.10.7 |
| D-12 | Clustered versus secondary index in InnoDB, showing the double lookup | §3.11.4 |
| D-13 | PostgreSQL version chain in the heap versus InnoDB undo chain, side by side | §3.12, §3.13 |
| D-14 | Snapshot construction: `ProcArray` → `xmin`/`xmax`/`xip` → a visibility decision | §3.12.3 |
| D-15 | XID space as a circle, with the 2.1B visible window and freezing | §3.12.13 |
| D-16 | Record, gap, next-key and insert-intention locks over one index page | §3.15.3 |
| D-17 | The SSI dangerous structure: `T1 → T2 → T3` with commit order marked | §3.16.2 |
| D-18 | WAL insertion, flush, checkpoint and redo point on one LSN timeline | §3.17 |
| D-19 | Full-page writes versus doublewrite as two answers to a torn page | §3.18.8 |
| D-20 | MySQL commit: redo prepare → binlog write → binlog fsync → InnoDB commit | §3.18.13 |
| D-21 | Clock sweep with `usage_count` decrementing, and the 256 kB ring | §3.19.6 |
| D-22 | InnoDB midpoint-insertion LRU with young/old sublists | §3.20.3 |
| D-23 | DP join-order search over four relations, subsets as a lattice | §3.21.10 |
| D-24 | Hash join with `nbatch` partitions spilling to temp files | §3.22.8 |
| D-25 | Vacuum's two passes: heap prune → index cleanup → line pointers → FSM/VM | §3.23.1 |
| D-26 | The four blockers of vacuum, all pinning the same horizon | §3.23.18 |
| D-27 | Physical replication: WAL sender → receiver → startup process, with the four LSNs | §3.24.1 |
| D-28 | Logical decoding: WAL → reorder buffer → output plugin → subscriber | §3.24.13 |
| D-29 | MySQL replication threads: dump → I/O → relay log → coordinator → workers | §3.25.1 |
| D-30 | The QuizStakes stake-reservation path with every lock, snapshot and WAL write marked | §2.21, §3.14 |

## Overall leaf totals

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — BASICS | §1.1–§1.32 (32) | 467 |
| PART 2 — INTERMEDIATE | §2.1–§2.24 (24) | 366 |
| PART 3 — UNDER THE HOOD | §3.1–§3.27 (27) | 430 |
| PART 4 — BUILD IT | §4.1–§4.7 (7) | 52 |
| PART 5 — INTERVIEW AND RETENTION | §5.1–§5.3 (3) | 140 |
| **Total** | **93 sections** | **1455 leaves** |

Tag census for PARTS 3–5 (approximate, for the write pass's planning): every PART 3 section carries
`[SOURCE]` leaves; `[BUILD]` appears in §4.1–§4.7 (45 leaves plus 7 diff tables); `[MYSQL]` in §3.10–§3.11,
§3.13, §3.15, §3.18, §3.20, §3.25 and in contrast leaves throughout; `[VERSION-TRAP]` on every
PG 18 / MySQL 8.4 default change; `[RESEARCH]` on **91** PART 3 leaves that exist because of the
research phase below and must be re-verified before a constant is committed to the page.

## Sources consulted

Primary sources first. Where a source was reached only through a search summary rather than fetched,
that is stated, and the leaves that depend on it carry `[RESEARCH]`. No URL below is invented; where
nothing usable was found, that is said outright.

**PostgreSQL source (primary — fetched in full)**

- <https://raw.githubusercontent.com/postgres/postgres/master/src/backend/access/nbtree/README> —
  fetched. Source of §3.6 and §3.7 in their entirety: Lehman & Yao and Lanin & Shasha as the named
  algorithms, the high key, pivot tuples, suffix truncation (with Bayer & Unterauer's Prefix B-Trees
  as the origin), deduplication and posting lists, posting-list splits, the split interval,
  incomplete splits, the fast root, the fastpath insert optimisation via `rd_amcache`, `LP_DEAD` /
  `kill_prior_tuple`, simple versus bottom-up deletion and the "generational hypothesis",
  half-dead pages, the vacuum cycle ID and cleanup-lock interlock, the "drain" recycling technique,
  the two ScanKey kinds and `BTScanInsert`, and `ignore_killed_tuples` on standbys. **The write pass
  must re-open this file for exact function names (`_bt_findsplitloc`, `_bt_finish_split`) before
  quoting them.** `[RESEARCH]`
- <https://raw.githubusercontent.com/postgres/postgres/master/src/backend/storage/buffer/README> —
  fetched. Source of §3.19: `BufMappingLock`, `buffer_strategy_lock`, the buffer header spinlock,
  the three content-lock modes, `buf_table`, `usage_count`, `nextVictimBuffer`, `BM_IO_IN_PROGRESS`,
  the pin-versus-content-lock distinction, and the ring sizes — **256 kB for sequential scans ("to
  fit in L2 cache"), 16 MB for bulk writes but not more than 1/8th of `shared_buffers`, and
  `vacuum_buffer_usage_limit` for vacuum**. The README does **not** state `BM_MAX_USAGE_COUNT`'s
  value numerically; §3.19.6's `5` must be verified against `src/include/storage/buf_internals.h`.
  `[RESEARCH]`
- <https://raw.githubusercontent.com/postgres/postgres/master/src/backend/access/transam/README> —
  fetched. Source of §3.17 and much of §3.12: the WAL-before-data rule (quoted), LSNs, full-page
  writes and `RedoRecPtr`, torn pages, CLOG/`pg_xact` with its four states including
  `sub-committed`, `pg_subtrans`, lazy XID assignment, VXIDs formed from `procNumber` plus a
  backend-local counter, `SubTransactionId` numbering (1 for top level, 2+ below,
  `InvalidSubTransactionId` = 0), the snapshot-consistency requirement quoted verbatim,
  `ProcArrayLock` usage in `GetSnapshotData`/`ProcArrayEndTransaction`, `START_CRIT_SECTION` and the
  PANIC rule, `XLogRegisterBuffer` and the five `REGBUF_*` flags, hint-bit deferral against the
  page LSN, asynchronous commit and `XLogBackgroundFlush`/`wal_writer_delay`, and the record limits
  (**highest block ID 4 → five block references**, **20 registered data chunks**, **CLOG group size
  32**). `PGPROC_MAX_CACHED_SUBXIDS = 64` and `NUM_XLOGINSERT_LOCKS = 8` were **not** confirmed from
  this fetch and must be checked in `src/include/storage/proc.h` and `xlog.c`. `[RESEARCH]`
- <https://raw.githubusercontent.com/postgres/postgres/master/src/backend/access/heap/README.HOT> —
  fetched. Source of §3.4: `HEAP_ONLY_TUPLE`, `HEAP_HOT_UPDATED`, `LP_REDIRECT`, `LP_DEAD`, the
  root-tuple and redirecting-line-pointer definitions, the HOT preconditions ("changes none of the
  tuple's indexed columns", fits on the same page, does not affect non-summarising indexes),
  pruning and `PageRepairFragmentation`, `pd_prune_xid`, the buffer cleanup-lock requirement,
  `MaxHeapTuplesPerPage`, `fillfactor`, and `indcheckxmin`/`indisvalid`/`indisready`/`indislive`.
- <https://raw.githubusercontent.com/postgres/postgres/master/src/backend/optimizer/README> —
  fetched. Source of §3.21's object and function inventory: `RelOptInfo`, `Path` and every
  `*Path` subtype, `RestrictInfo`, `EquivalenceClass`, `PathKey`, `SpecialJoinInfo`,
  `PlaceHolderVar` and `varnullingrels`, the `UPPERREL_*` stages, and the call chain
  `planner` → `subquery_planner` → `grouping_planner` → `query_planner` → `make_one_rel` →
  `make_rel_from_joinlist` → `standard_join_search` → `join_search_one_level` →
  `make_rels_by_clause_joins` / `make_rels_by_clauseless_joins` → `add_path` / `add_partial_path` →
  `set_cheapest`, plus `join_is_legal`, geqo, parameterised paths, subquery pull-up, predicate
  push-down, partitionwise join and aggregate, eager aggregation, memoisation and LATERAL.

**PostgreSQL documentation (primary)**

- <https://www.postgresql.org/docs/18/runtime-config-query.html> — fetched. Source of every planner
  constant in §3.21.14 and §3.22.6 with its PG 18 default: `seq_page_cost` 1.0,
  `random_page_cost` 4.0, `cpu_tuple_cost` 0.01, `cpu_index_tuple_cost` 0.005,
  `cpu_operator_cost` 0.0025, `parallel_setup_cost` 1000, `parallel_tuple_cost` 0.1,
  `min_parallel_table_scan_size` 8 MB, `min_parallel_index_scan_size` 512 kB,
  `effective_cache_size` 4 GB, `jit_above_cost` 100000, `jit_inline_above_cost` 500000,
  `jit_optimize_above_cost` 500000, `geqo_threshold` 12, `geqo_effort` 5,
  `from_collapse_limit` 8, `join_collapse_limit` = `from_collapse_limit`, `plan_cache_mode` auto,
  `recursive_worktable_factor` 10.0, `default_statistics_target` 100,
  `constraint_exclusion` partition, `cursor_tuple_fraction` 0.1, and the full `enable_*` list
  including PG 18's `enable_self_join_elimination` and `enable_distinct_reordering`, with
  `enable_partitionwise_join`/`_aggregate` **off** by default.
- <https://www.postgresql.org/docs/current/storage-page-layout.html> — reached via search summary.
  Basis of §3.2.2 and §3.3.1–§3.3.2: the `PageHeaderData` field list, `ItemIdData`, and the
  `HeapTupleHeaderData` field widths with the "row data starts at byte 24, first 23 bytes are the
  header" statement. **Fetch it before writing §3.2–§3.3.** `[RESEARCH]`
- <https://www.postgresql.org/docs/current/storage-vm.html> — reached via search summary. Source of
  the visibility map's two bits per page (all-visible, all-frozen) in §3.4.13. `[RESEARCH]`
- <https://www.postgresql.org/docs/current/runtime-config-vacuum.html> and
  <https://www.postgresql.org/docs/current/routine-vacuuming.html> — reached via search summary.
  Basis of §3.23's parameter list and §3.12.14–§3.12.16's freezing thresholds, including
  `autovacuum_freeze_max_age`, `vacuum_freeze_min_age`, `vacuum_freeze_table_age`,
  `vacuum_failsafe_age` and PG 18's eager scanning of all-visible-not-all-frozen pages.
  **Every one of those numbers must be re-read from this page.** `[RESEARCH]`
- <https://www.postgresql.org/docs/current/btree.html> — reached via search summary. Source of
  §3.8.6's skip-scan description and the **support function number 6** /
  `src/include/utils/skipsupport.h` detail. `[RESEARCH]`
- <https://www.postgresql.org/docs/current/release-18.html> and
  <https://www.postgresql.org/about/news/postgresql-18-beta-1-released-3070/> — reached via search
  summary. Basis of the PG 18 delta leaves throughout PART 3 (AIO, skip scan, checksums by default,
  `BUFFERS` by default, `uuidv7()`). `[RESEARCH]`
- <https://www.postgresql.org/docs/current/row-estimation-examples.html> — reached via search
  summary. Basis of §3.21.17's selectivity walk-through, `scalarltsel`, `pg_operator` lookup and
  histogram interpolation. **Fetch it; §3.21.17 is a `[PROVE]` leaf.** `[RESEARCH]`
- <https://www.postgresql.org/docs/current/two-phase.html> and
  <https://www.postgresql.org/docs/devel/two-phase.html> — reached via search summary. Source of
  §3.26.1–§3.26.2: `pg_twophase` files named by hexadecimal xid, written at checkpoint, restored at
  startup; `max_prepared_transactions` default 0; `pg_prepared_xacts`. `[RESEARCH]`
- <https://www.postgresql.org/docs/current/pgvisibility.html> and
  <https://www.postgresql.org/docs/current/storage-toast.html> — reached via search summary for
  §3.1.8 and §3.5. The TOAST numbers (`TOAST_TUPLE_THRESHOLD` "normally 2 kB" / 2032,
  `TOAST_MAX_CHUNK_SIZE` ~2000 / 1996) come from secondary summaries of these pages and
  **must be verified in `src/include/access/heaptoast.h`**. `[RESEARCH]`

**PostgreSQL research and expert sources (secondary — used only for concept discovery)**

- <https://postgres.ai/blog/20251008-postgres-marathon-2-004> — fast-path locking explained.
  Source of §3.14.7–§3.14.9: `FP_LOCK_SLOTS_PER_BACKEND = 16`, the three weak modes, and the
  **PG 18 change (commit `c4d5cb71d`) to variable-sized fast-path arrays scaled from
  `max_locks_per_transaction`**. `[RESEARCH]`
- <https://postgres.ai/blog/20251007-postgres-marathon-2-003> and
  <https://ardentperf.com/2024/03/03/postgres-indexes-partitioning-and-lwlocklockmanager-scalability/>
  — `LWLock:LockManager` contention with partitioned tables; the empirical basis of §3.14.8.
  `[RESEARCH]`
- <https://doxygen.postgresql.org/lwlock_8h_source.html> — `LOG2_NUM_LOCK_PARTITIONS 4` →
  `NUM_LOCK_PARTITIONS = 16` in §3.14.6. Reached via search result; verify in the header.
  `[RESEARCH]`
- <https://www.postgresql.org/message-id/5946.979867205@sss.pgh.pa.us> and
  <http://www.inf.fu-berlin.de/lehre/SS10/DBS-Intro/Reader/DeadlockDetection.txt> — Tom Lane's
  deadlock reimplementation notes and the deadlock-detection design document. Source of §3.14.14's
  optimistic-waiting design and §3.14.15's soft-edge reordering. **The best available primary
  material on the detector; fetch before writing those leaves.** `[RESEARCH]`
- <https://drkp.net/papers/ssi-vldb12.pdf> (also mirrored at <https://arxiv.org/pdf/1208.4179>) —
  Ports & Grittner, "Serializable Snapshot Isolation in PostgreSQL", VLDB 2012. The primary source
  for all of §3.16: SIREAD locks, the dangerous structure, the non-blocking SSI lock manager,
  index-range predicate locks, granularity promotion, and the measured overhead.
  **Fetch and read before writing §3.16.** `[RESEARCH]`
- <https://www.interdb.jp/pg/pgsql05/09.html> (Suzuki, *The Internals of PostgreSQL*) — corroborates
  §3.16's SIREAD/rw-conflict machinery; also the best secondary source for §3.12's visibility rules.
  `[RESEARCH]`
- <https://www.postgresql.org/docs/current/transaction-iso.html> — the isolation chapter; the
  authority for the PG-specific claim that `REPEATABLE READ` is snapshot isolation.
- <https://wiki.postgresql.org/wiki/Key_normalization>,
  <https://wiki.postgresql.org/wiki/NBTree_Prefix_Truncation>, and Peter Geoghegan's
  <https://www.postgresql.org/message-id/CAH2-Wzn5XbCzk6u0GL+uPnCp1tbrp2pJHJ=3bYT4yQ0_zzHxmw@mail.gmail.com>
  ("Why B-Tree suffix truncation matters") — the design discussion behind §3.7.1–§3.7.3. `[RESEARCH]`
- <https://www.postgresql.org/message-id/E1j73sn-0003FQ-KO@gemulon.postgresql.org> — the
  "Add deduplication to nbtree" commit message; §3.7.4's lazy-application claim. `[RESEARCH]`
- <https://erthalion.info/2020/11/28/evolution-of-tree-data-structures-for-indexing/> — a survey of
  the nbtree AM's evolution; used to check §3.6–§3.8 for missed concepts. `[RESEARCH]`
- <https://pganalyze.com/blog/5mins-postgres-17-faster-vacuum-adaptive-radix-trees> and
  <https://boringsql.com/posts/vacuum-at-the-page-level/> — the PG 17 `TidStore`/radix-tree change
  and the removal of the 1 GB dead-TID cap in §3.23.3–§3.23.4. `[RESEARCH]`
- <https://percona.community/blog/2026/07/01/postgresql-autovacuum-internals-benchmark/> —
  autovacuum internals and cost-delay benchmarking; the basis for §3.23.9's throughput-ceiling
  derivation. `[RESEARCH]`
- <https://pganalyze.com/blog/postgres-18-async-io>,
  <https://www.cybertec-postgresql.com/en/postgresql-18-better-i-o-performance-with-aio/> and
  <https://www.dbi-services.com/blog/postgresql-18-support-for-asynchronous-i-o/> — PG 18 AIO:
  `io_method` with `worker`/`io_uring`/`sync`, `io_workers` default 3, the submission/completion
  queues, and the `effective_io_concurrency`/`maintenance_io_concurrency` default move to 16.
  §3.19.15–§3.19.16. **Verify each default against the PG 18 docs.** `[RESEARCH]`
- <https://neon.com/postgresql/18/skip-scan-btree> and
  <https://www.pgedge.com/blog/postgres-18-skip-scan-breaking-free-from-the-left-most-index-limitation>
  — skip-scan behaviour and its cardinality boundary in §3.8.6–§3.8.7. `[RESEARCH]`
- <https://techcommunity.microsoft.com/blog/adforpostgresql/understanding-hash-join-memory-usage-and-oom-risks-in-postgresql/4500308>
  and <https://www.enterprisedb.com/blog/parallel-hash-postgresql> — hash-join batching, spill
  behaviour, `hash_mem_multiplier`, and Parallel Hash's shared table in §3.22.8–§3.22.10 and
  §3.22.16. **`hash_mem_multiplier`'s default differs by version (1.0 at introduction in PG 13,
  2.0 later); confirm the PG 18 value in the docs.** `[RESEARCH]`
- <https://boringsql.com/posts/pg-stat-statements/> and
  <https://pganalyze.com/blog/postgres-in-production-pg-stat-statements-deep-dive-part-2> and
  <https://paquier.xyz/postgresql-2/postgres-16-pgstatstatements-norm/> — query jumbling,
  `compute_query_id`, negative `queryid`s, OID-based (not name-based) jumbling, and PG 16's
  normalisation of utility statements and `IN` lists. §3.27.5–§3.27.6. `[RESEARCH]`
- <https://stormatics.tech/blogs/understanding-wait-events-in-postgresql> and
  <https://runbooks.gitlab.com/patroni/wait-events-analisys/> — the wait-event taxonomy and the
  Active Session History sampling pattern in §3.27.1–§3.27.4. `[RESEARCH]`
- <https://www.postgresql.fastware.com/blog/how-to-gain-insight-into-the-pg-stat-replication-slots-view-by-examining-logical-replication>,
  <https://streamkap.com/resources-and-guides/postgresql-logical-replication-internals> and
  <https://www.enterprisedb.com/blog/logical-decoding-large-progress-transactions-postgresql> —
  the walsender/`XLogReader`/`ReorderBuffer`/`pgoutput` pipeline, `logical_decoding_work_mem`
  (default 64 MB) and PG 14 in-progress streaming. §3.24.13–§3.24.14. `[RESEARCH]`
- <https://www.cybertec-postgresql.com/en/prepared-transactions/> and
  <https://www.highgo.ca/2020/01/28/understanding-prepared-transactions-and-handling-the-orphans/>
  — the orphaned-prepared-transaction failure mode in §3.26.2. `[RESEARCH]`
- <https://www.crunchydata.com/blog/postgres-19-compression-from-pglz-to-lz4> — the PG 19 change of
  `default_toast_compression` to `lz4`, and therefore the PG 18 baseline value of `pglz`.
  §3.5.8. `[RESEARCH]`
- <https://blog.anayrat.info/en/2022/02/14/postgresql-toast-compression-and-toast_tuple_target/> and
  <https://hakibenita.com/sql-medium-text-performance> — `toast_tuple_target` and the
  medium-size-text performance effect in §3.5.9 and §3.5.14. `[RESEARCH]`

**MySQL / InnoDB sources**

- <https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html> and
  <https://dev.mysql.com/doc/refman/5.7/en/innodb-locks-set.html> — the primary reference for
  §3.15.3–§3.15.6: `LOCK_REC_NOT_GAP`, `LOCK_GAP`, `LOCK_ORDINARY` (next-key), insert-intention
  locks and their non-conflict property, and the locks set by each statement type. **The 8.4
  version of these pages must be used for the write pass.** `[RESEARCH]`
- <https://blog.jcole.us/2013/01/10/btree-index-structures-in-innodb/> and
  <https://blog.jcole.us/2013/01/03/the-basics-of-innodb-space-file-layout/> — Jeremy Cole's
  InnoDB page-format series. Source of §3.10.3–§3.10.11: the 38-byte FIL header with
  `FIL_PAGE_PREV`/`FIL_PAGE_NEXT`, the 8-byte trailer, the 56-byte INDEX page header, infimum and
  supremum, and the page directory as a downward-growing array of 16-bit offsets with one slot per
  4–8 records. Old but still the best published description; **cross-check field widths against
  `storage/innobase/include/page0page.h`**. `[RESEARCH]`
- <https://docs.oracle.com/cd/E17952_01/mysql-8.0-en/innodb-row-format.html> — row formats. Source
  of §3.10.13–§3.10.14: `DYNAMIC` as the default, the 768-byte inline prefix plus 20-byte pointer
  under `COMPACT`, the 20-byte-pointer-only behaviour under `DYNAMIC`, overflow-page lists, and the
  40-byte candidacy floor. `[RESEARCH]`
- <https://lefred.be/content/mysql-8-4-lts-new-production-ready-defaults-for-innodb/> and
  <https://docs.percona.com/percona-server/8.4/8.4-defaults-and-tuning.html> — the MySQL 8.4
  default changes used in §3.11.7, §3.11.9, §3.18.3 and §3.18.11:
  **`innodb_change_buffering` all → none**, **`innodb_adaptive_hash_index` ON → OFF**,
  **`innodb_io_capacity` 200 → 10000**, and **`innodb_redo_log_capacity` auto-sized to
  (logical processors / 2) GB capped at 16 GB**. These are the highest-value `[VERSION-TRAP]`
  numbers in PART 3 and **every one must be re-verified in the 8.4 reference manual's
  "Changes in MySQL 8.4" page before publication**. `[RESEARCH]`
- <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.MySQL.CommonDBATasks.Config.Size.8.4.html>
  — corroborates the 8.4 buffer-pool and redo-capacity sizing behaviour. `[RESEARCH]`
- <https://docs.oracle.com/cd/E17952_01/mysql-8.0-en/innodb-purge-configuration.html> — purge
  configuration: `innodb_purge_threads` (4), `innodb_purge_batch_size` (300),
  `innodb_max_purge_lag`, `innodb_max_purge_lag_delay`. §3.13.9. `[RESEARCH]`
- <https://www.mydbops.com/blog/an-overview-to-innodb-undo-log> and
  <https://lefred.be/content/a-graph-a-day-keeps-the-doctor-away-mysql-history-list-length/> —
  rollback segments, undo-log lists, `trx_undo_update_cleanup`, `rseg->history_len` and the
  `trx_rseg_history_len` metric with its "normally under 1,000" guidance. §3.13.6–§3.13.8.
  `[RESEARCH]`
- <https://dev.mysql.com/doc/refman/8.4/en/replication-threads.html>,
  <https://dev.mysql.com/doc/refman/8.4/en/replica-logs.html> and
  <https://dev.mysql.com/doc/refman/8.4/en/replication-options-replica.html> — the 8.4 replication
  reference. Source of §3.25.1, §3.25.8 and §3.25.9, including **`replica_parallel_workers`
  default 4** and the coordinator-plus-N-workers model. `[RESEARCH]`
- <https://mariadb.com/docs/server/server-management/server-monitoring-logs/binary-log/group-commit-for-the-binary-log>
  and <https://bugs.mysql.com/bug.php?id=73214> — binlog group commit's three stages and the
  fsync-count arithmetic in §3.18.12–§3.18.15. MariaDB documentation used as the clearest published
  description of a mechanism MySQL shares; **the MySQL 8.4 manual is the authority for the variable
  names and defaults.** `[RESEARCH]`
- <https://dev.mysql.com/doc/dev/mysql-server/latest/make__join__hypergraph_8cc.html> and
  <https://blogs.oracle.com/mysql/the-hypergraph-optimizer-is-now-available-in-mysql-9-7-community-edition>
  — `JoinHypergraph`, `CostingReceiver`, DPhyp, and the **9.7 Community Edition availability** in
  §3.21.22. `[RESEARCH]`
- <https://www.alibabacloud.com/blog/code-explanation-of-mysql-8-0-23-hypergraph-join-optimizer_600430>
  — a code walk of the hypergraph optimizer; used for concept discovery only. `[RESEARCH]`

**Searches that returned nothing usable, stated rather than padded**

- No primary source was located for `BM_MAX_USAGE_COUNT`'s numeric value (the buffer README omits
  it); §3.19.6 must be verified in `src/include/storage/buf_internals.h`.
- No primary confirmation was found in this pass for `NUM_XLOGINSERT_LOCKS = 8`,
  `PGPROC_MAX_CACHED_SUBXIDS = 64`, `CLOG_XACTS_PER_PAGE = 32768`, `MERGE_THRESHOLD = 50`,
  the InnoDB rollback-segment/undo-slot counts (128 / 1024), or `optimizer_search_depth = 62`.
  All six are tagged `[RESEARCH]` and must be read from source or the reference manual.
- No authoritative published figure was found for the exact XID-exhaustion warning thresholds
  (the "must be vacuumed within N transactions" ladder); §3.12.15 must quote
  `src/backend/access/transam/varsup.c` rather than recall.
- No primary source was consulted for `innodb_flush_method`'s default in 8.4; §3.20.8 states the
  behaviour and defers the default to verification.
- No benchmark of sufficient quality was found for the "JIT costs 50–200 ms" figure in §3.22.7; it
  must be written as "measure it with the §4.7 harness", not quoted.

## Gaps vs the current guide

`src/topics/09-sql-databases.md` is **~440 lines** across 15 numbered sections plus a 22-item atomic
concept checklist. It is a competent breadth-first guide: the join, NULL, window-function,
isolation, pagination, pooling and migration sections are all correct and mechanism-aware, and
**every `**Trap:**` and every checklist line in it must survive into the bible**. It is not,
however, an internals document. Its only internals-adjacent content is §6's "B-tree mechanics"
(9 lines: balanced tree, 3–4 levels, sorted leaves, linked leaves) and §14's "MVCC and VACUUM"
(12 lines: `xmin`/`xmax`, new row version on update, bloat, `VACUUM FULL`, long transactions,
one sentence on InnoDB undo). Everything else in PART 3 is absent.

| Syllabus area | Present in `src/topics/09-sql-databases.md` | Missing | Shallow |
|---|---|---|---|
| §3.1 reading the source; `pageinspect`/`pgstattuple`/`pg_visibility`/`pg_buffercache`/`pg_walinspect`/`innodb_ruby` | — | ✅ entire section | |
| §3.2 the slotted page, `PageHeaderData`, `ItemIdData`, `lp_flags`, checksums | — | ✅ entire section | |
| §3.3 tuple header, `t_infomask` bits, hint bits, alignment, varlena, the `ledger_entry` byte budget | — | ✅ entire section — and §3.3.13–§3.3.15 are the highest-value missing leaves in the file | |
| §3.4 HOT, pruning, `LP_REDIRECT`, fillfactor, FSM, visibility map | §14 (one sentence: an UPDATE writes a new row version) | ✅ HOT and all its preconditions, pruning, the FSM, both VM bits, `Heap Fetches`, the `ctid` trap | ✅ severely — the guide gives the consequence without the mechanism |
| §3.5 TOAST thresholds, strategies, chunking, compression, slicing | — | ✅ entire section | |
| §3.6 nbtree structure, high keys, L&Y, splits, 90/10, fastpath, tree-height arithmetic | §6 "B-tree mechanics" (3–4 levels, sorted leaves, linked leaves) | ✅ the meta page, `BTPageOpaqueData`, `BTREE_VERSION`, L&Y, high keys, pivot tuples, the split algorithm, incomplete splits, the rightmost heuristic, the fastpath, the UUID anti-case | ✅ the "3–4 I/Os" claim is right and must be **derived** rather than asserted |
| §3.7 suffix truncation, deduplication, bottom-up deletion, page deletion, bloat, `REINDEX CONCURRENTLY` | §6 "Cost of indexes" (indexes slow writes; unused indexes are cost) | ✅ every mechanism; the guide never says an index cannot shrink | ✅ the unused-index and FK-index advice is correct and must be preserved verbatim |
| §3.8 scan machinery, array keys, skip scan, index-only scans, bitmap scans, `CIC` states | §6 ("covering index", "partial index", "why the planner ignores your index") | ✅ `_bt_first`/`_bt_search`/`_bt_readpage`, `BTScanPosData`, skip scan, lossy bitmaps, `amcostestimate`, correlation, the `CIC` state machine | ✅ the six "why the planner ignores your index" reasons are excellent and must be preserved verbatim and given their mechanisms |
| §3.9 the other access methods at implementation depth | §6 (one line: hash, GIN, GiST, BRIN with one-word use cases) | ✅ the AM interface, GIN's pending list, GiST's seven support functions, BRIN's revmap and arithmetic, SP-GiST, `pg_trgm`, `pgvector`, the MySQL contrast | ✅ severely |
| §3.10 InnoDB spaces, pages, FIL header/trailer, page directory, row formats, off-page BLOBs | — | ✅ entire section | |
| §3.11 clustered-index layout, PK amplification, change buffer, AHI, online DDL, `AUTO_INCREMENT` | — | ✅ entire section | |
| §3.12 snapshot construction, `HeapTupleSatisfiesMVCC`, clog, subtransactions, multixacts, wraparound, freezing | §14 (`xmin`/`xmax` exist; readers don't block writers) | ✅ snapshots, the visibility function, `pg_xact`, SLRUs, subtransaction overflow, multixacts, the 2.1B window, all four freeze ages, the causal chain from a long transaction to a bad plan | ✅ the "readers never block writers" line is right and must be kept and proved |
| §3.13 InnoDB read views, undo chains, purge, history list length, rollback cost | §14 (one sentence: "MySQL InnoDB does the same via undo logs and the purge thread") | ✅ read-view fields, the chain walk, rollback segments, the history list, purge throttling, delete-marking, the side-by-side table | ✅ severely — "does the same" is the misconception this section exists to kill |
| §3.14 lock manager, `LOCKTAG`s, partitions, fast-path locks, row locks in tuples, the deadlock detector | §10 (lock modes named, deadlock example, ordering advice) | ✅ the three lock layers, latch versus lock, `LOCKTAG` types, the 16 partitions, fast-path overflow, row locks in `t_xmax`, no escalation, soft-edge reordering, the log walk-through | ✅ the deadlock-ordering advice and the queue advice are correct and must be preserved verbatim |
| §3.15 InnoDB `lock_sys`, gap/next-key/insert-intention locks, MDL, deadlock victim choice, timeouts | §10 (mentions InnoDB gap locks in passing) | ✅ the lock bitmap, all four record-lock types, RC versus RR gap behaviour, implicit locks, MDL pileups, `innodb_rollback_on_timeout`, the status walk-through | ✅ severely |
| §3.16 SSI: dangerous structures, SIREAD locks, granularity, predicate locks, `READ ONLY DEFERRABLE` | §9 (SERIALIZABLE listed in the isolation table) | ✅ entire mechanism, the false-positive argument, the indexing-as-concurrency insight, the InnoDB contrast | ✅ severely |
| §3.17 WAL record format, LSNs, full-page writes, torn pages, checkpoints, ARIES, `synchronous_commit`, the fsync gate | §8 (durability named as the D in ACID) | ✅ entire section | |
| §3.18 InnoDB mini-transactions, redo ring, doublewrite, fuzzy checkpoints, binlog 2PC, group commit | — | ✅ entire section | |
| §3.19 buffer descriptors, clock sweep, pins versus content locks, ring buffers, bgwriter, PG 18 AIO, `pg_stat_io` | — | ✅ entire section | |
| §3.20 InnoDB buffer pool, midpoint LRU, flush list, read-ahead, `O_DIRECT`, sizing | — | ✅ entire section | |
| §3.21 planner objects, join-order DP, geqo, cost formulas, selectivity math, extended statistics, plan caching, MySQL optimizer | §6 "Why the planner ignores your index" + §7 (how to read a plan) | ✅ the whole planner: `RelOptInfo`/`Path`/`EquivalenceClass`/`PathKey`, `standard_join_search`, the search-space arithmetic, `join_collapse_limit`, geqo, every cost constant, MCV/histogram math, extended statistics, generic plans, the hypergraph optimizer | ✅ §7's estimate-versus-actual advice is the guide's best plan-reading rule and must be preserved verbatim and extended |
| §3.22 iterator executor, JIT, hash-join batching, sort methods, memoize, parallel query | §7 (node types and `EXPLAIN (ANALYZE, BUFFERS)`) | ✅ the execution model, blocking versus streaming, `ExprEvalStep`, JIT and its regression mode, batching and spilling, `top-N heapsort`, incremental sort, `Memoize`, parallel-unsafe cases | ✅ severely |
| §3.23 vacuum phases, `TidStore`, autovacuum triggers and cost delay, failsafe, progress views, InnoDB purge | §14 (autovacuum exists; `VACUUM FULL` takes `ACCESS EXCLUSIVE`) | ✅ the two-pass structure, the trigger arithmetic at 7.2B rows, the cost-delay ceiling, PG 17's `TidStore`, failsafe, every progress view, the runbook | ✅ the `VACUUM FULL` warning and the long-transaction warning are right and must be preserved verbatim and quantified |
| §3.24 PG replication internals, slots, sync levels, recovery conflicts, timelines, logical decoding | §13 (async replication, replica lag, read-your-writes) | ✅ the process pipeline, the four LSNs, slot retention and disk-fill, `synchronous_standby_names` grammar, recovery conflicts and both cures, timelines, the reorder buffer, `REPLICA IDENTITY` | ✅ the read-your-own-writes rule is correct and must be preserved verbatim |
| §3.25 MySQL binlog formats, GTIDs, relay logs, parallel apply, semi-sync, Group Replication | §13 (mentions `Seconds_Behind_Source` unreliability in the trap list) | ✅ everything else — the whole thread pipeline, binlog formats, GTIDs and their restrictions, writeset tracking, semi-sync's timeout fallback, the `AFTER_SYNC` correctness point | ✅ the `Seconds_Behind_Source` trap is right and must be preserved verbatim and given its mechanism |
| §3.26 2PC internals, XA, outbox, `SKIP LOCKED`, sharding coordinators, consensus SQL, clocks | §10 (queues with `SKIP LOCKED`) | ✅ `pg_twophase`, orphaned prepared transactions, XA in Java, the outbox mechanism, sharding coordinators, consensus engines, clock/commit-order reasoning, the do-we-need-to-shard arithmetic | ✅ the `SKIP LOCKED` queue pattern is correct and must be preserved verbatim |
| §3.27 wait events, `pg_stat_statements` jumbling, `auto_explain`, `pg_stat_io`, `performance_schema` | §7 (read plans), §14 (implicitly) | ✅ entire section — the guide has no observability content beyond `EXPLAIN` | |
| PART 4 (§4.1–§4.7) build-it exercises | — | ✅ all seven (45 leaves plus 7 diff tables) | |
| PART 5 (§5.1–§5.3) internals question bank, cold assertions, retention drills | 22-item atomic concept checklist (all of which must survive) | ✅ all 140 leaves | ✅ the existing checklist is a good breadth checklist and becomes the PART 1/2 half of the final one |

