# 08 — Spring Data JPA and Hibernate

JPA's difficulty is that it is *stateful*. The persistence context sits between your code and the
database, and almost every surprising behaviour — `save()` doing nothing, `save()` doing something
you didn't ask for, `LazyInitializationException`, N+1, an UPDATE you never wrote — is explained by
knowing what that context is doing. Read § 2 until it's automatic; the rest follows.

---

## 1. What ORM buys and what it costs

**Buys:** object graph navigation, dirty checking (no hand-written UPDATE), caching, dialect
portability, a query language over entities, optimistic locking for free.

**Costs:** a leaky abstraction — you must know the SQL it emits; implicit behaviour that surprises
(auto-flush, cascade); poor fit for bulk operations and analytic queries; a learning curve where
"working" and "correct under load" are far apart.

**The mature position for an interview:** ORM for transactional CRUD on an object graph; drop to
JDBC/jOOQ/native SQL for reporting, bulk updates, and anything where the query shape matters more
than the object shape. It is not all-or-nothing — mixing is normal and correct.

---

## 2. Entity states and the persistence context

The **persistence context** (`EntityManager`, Hibernate's `Session`) is a short-lived cache scoped to
the transaction. Two things it does:

- **Identity map**: within one context, one row = one object. `em.find(User.class, 1L)` twice returns
  the *same instance* (`==` is true) and issues one SELECT.
- **Dirty checking**: it keeps a snapshot of the loaded state. At flush time it compares each managed
  entity to its snapshot and issues UPDATEs for what changed.

Four states:

| State | Meaning | In persistence context? | Row exists? |
|---|---|---|---|
| **Transient / new** | just `new`-ed, no id | no | no |
| **Managed / persistent** | tracked, dirty-checked | yes | yes (at flush) |
| **Detached** | was managed, context closed or `detach()`/`clear()` | no | yes |
| **Removed** | scheduled for DELETE at flush | yes | until flush |

Transitions: `persist()` transient→managed; `find()`/query load → managed; commit/close → detached;
`merge(detached)` → returns a managed *copy*; `remove(managed)` → removed.

### The consequence people get wrong

```java
@Transactional
public void rename(Long id, String name) {
    User u = repo.findById(id).orElseThrow();  // managed
    u.setName(name);                            // dirty
    // no save() call — the UPDATE still happens at commit
}
```

**Dirty checking makes `save()` unnecessary on a managed entity, and calling it is a no-op.** The
inverse trap is worse:

```java
@Transactional
public void applyDiscount(Long id) {
    Order o = repo.findById(id).orElseThrow();
    o.setTotal(o.getTotal().multiply(new BigDecimal("0.9")));
    if (!isEligible(o)) return;   // "I didn't save, so nothing happened" — WRONG, it commits
}
```

The mutation is flushed at commit regardless. To discard, don't mutate until you've decided (or
detach). **Trap:** treating an entity like a DTO and mutating it "just for the response".

### Flush

Flush = "write pending SQL to the DB", **not** commit. It happens: at commit; before a JPQL/HQL query
whose result could be affected (`FlushModeType.AUTO`); on explicit `flush()`. Not before a native
query unless you tell Hibernate the affected tables — a real source of stale reads.

---

## 3. `persist` vs `merge` vs Spring Data `save`

- `persist(e)` — for **new** entities. Makes the passed instance managed (the argument itself). Throws
  if the entity already has an identifier that exists.
- `merge(e)` — for **detached** entities. Copies state onto a managed instance (loading it by id if
  needed) and **returns that managed instance**. The argument stays detached.

```java
// The returned-copy bug
User detached = ...;
em.merge(detached);
detached.setEmail("new@x.com");   // changes NOTHING — detached is not managed
// correct:
User managed = em.merge(detached);
managed.setEmail("new@x.com");
```

**`repository.save(entity)` decides for you** via `isNew()`:
- Default (`JpaEntityInformation`): if the `@Id` field is `null` (or a primitive `0`) → `persist`,
  otherwise → `merge`.
- If the entity implements `Persistable`, your `isNew()` is used instead.

**Trap: assigned IDs.** With a natural/UUID key you set yourself, the id is non-null on a brand-new
entity, so `save()` calls `merge`, which fires a pointless **SELECT before every INSERT**. Fix:
implement `Persistable<UUID>` with an `@Transient boolean isNew` flag flipped in `@PostPersist`/`@PostLoad`.

**Trap: `save()` on a detached entity with unloaded fields** — merge copies *all* fields, so nulls in
the detached object overwrite good data. This is the classic "editing a form nulled out three columns"
bug. Fix: load the managed entity and copy only the fields the request owns.

---

## 4. Fetch types and defaults

| Association | Default fetch |
|---|---|
| `@ManyToOne` | **EAGER** |
| `@OneToOne` | **EAGER** |
| `@OneToMany` | LAZY |
| `@ManyToMany` | LAZY |

The `*ToOne` eager defaults are a JPA spec mistake and the biggest silent source of N+1 and giant
join graphs. **Set every association to `fetch = LAZY` explicitly** and fetch what you need per query.

```java
@ManyToOne(fetch = FetchType.LAZY)
private Customer customer;
```

**`@OneToOne` lazy caveat:** an *optional* one-to-one on the non-owning side cannot be proxied
(Hibernate must know whether the row exists to return null vs a proxy), so it stays eager in practice.
Fixes: make it non-optional, share the primary key (`@MapsId`), or model it as `@ManyToOne`.

---

## 5. Proxies and `LazyInitializationException`

**Mechanism.** A lazy `@ManyToOne` field holds a Hibernate proxy — a generated subclass with only the
id populated. Touching any other property triggers a SELECT *through the session that created it*.
A lazy collection holds a `PersistentBag`/`PersistentSet` wrapper that loads on first access.

If the session is closed (transaction ended), that initialization throws
`LazyInitializationException: could not initialize proxy — no Session`.

**Ranked fixes:**

1. **Fetch what you need inside the transaction** — `JOIN FETCH` or `@EntityGraph`. Correct and explicit.
2. **Map to a DTO inside the transactional service method.** The web layer then never touches entities.
   This is the design fix.
3. `Hibernate.initialize(x)` / touching the collection inside the tx. Works, easy to forget.
4. Widen the transaction to cover serialization. Usually wrong — long transactions hold connections.
5. `spring.jpa.open-in-view=true` (Boot's default!). Makes the symptom vanish and creates worse
   problems — see § 14.

**Trap:** `getReference()`/`getOne()` returns a proxy without hitting the DB. `proxy.getId()` is safe;
anything else triggers a load, and if the row doesn't exist you get `EntityNotFoundException` at a
random later line. Also `proxy.getClass()` is `Customer$HibernateProxy`, so `instanceof` on subclasses
and naive `equals` break.

---

## 6. The N+1 problem

```java
List<Order> orders = orderRepo.findAll();          // 1 query
orders.forEach(o -> log(o.getCustomer().getName())); // N queries
```

**How to spot it:** turn on SQL logging in tests — `spring.jpa.show-sql`, better
`logging.level.org.hibernate.SQL=DEBUG`, best a query-count assertion (Hibernate `Statistics`, or
datasource-proxy) that fails the build when a call exceeds its budget.

**Fixes, with trade-offs:**

| Fix | How | When |
|---|---|---|
| `JOIN FETCH` | `@Query("select o from Order o join fetch o.customer")` | one or two associations, known query |
| `@EntityGraph` | `@EntityGraph(attributePaths = {"customer","items"})` on the repo method | declarative, reuses derived queries |
| DTO projection | `select new com.x.OrderDto(o.id, c.name) from Order o join o.customer c` or an interface projection | read-only endpoints — fastest, no entities loaded |
| `@BatchSize(size = 50)` | on the entity/collection | turns N queries into N/50 `IN (...)` queries; great blanket mitigation |
| `hibernate.default_batch_fetch_size` | global property | same, applied everywhere |

`FetchMode.SUBSELECT` is the other option: one extra query re-running the original as a subselect.

**Trap: two collection JOIN FETCHes in one query** → `MultipleBagFetchException`, and even if you use
`Set`s you get a cartesian product. Fix: fetch one collection per query (Hibernate merges them in the
identity map across two calls in the same session), or use `@BatchSize`.

---

## 7. Pagination with collection fetch — the in-memory trap

```java
@Query("select o from Order o join fetch o.items")
Page<Order> findAllWithItems(Pageable p);
```

Log line: **`HHH000104: firstResult/maxResults specified with collection fetch; applying in memory`**

The join multiplies rows, so `LIMIT` would cut a parent's children in half. Hibernate protects
correctness by fetching **the entire result set** and paginating in Java. On a large table this is an
OOM waiting to happen. (Hibernate 6 can sometimes rewrite this; do not rely on it.)

**Fix — two queries:**
1. Page the ids: `select o.id from Order o order by o.createdAt` with the `Pageable`.
2. Fetch the graph: `select distinct o from Order o join fetch o.items where o.id in :ids`.

`@EntityGraph` on a `Page`-returning method has the same problem. Any `HHH000104` in your logs is a
production incident waiting for the table to grow.

---

## 8. `equals` / `hashCode` on entities

The problem: a new entity has `id == null`, gets added to a `HashSet`, then the id is assigned at
flush. Its hash changes and it is **lost inside the set**.

Rules that work:

- Best: use a **business key** (natural unique field — email, order number) if one exists.
- Otherwise: assign a UUID in the constructor and use that.
- If you must use the surrogate id: `equals` returns false when either id is null (or `this == o`),
  and `hashCode()` returns a **constant** (e.g. `getClass().hashCode()`), so the hash never changes.

```java
@Override public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Order other)) return false;   // handles the proxy subclass poorly — see below
    return id != null && id.equals(other.getId());
}
@Override public int hashCode() { return getClass().hashCode(); }
```

Compare with `Hibernate.getClass(o)` rather than `getClass()` so a proxy compares equal to its target.
**Trap:** Lombok `@Data` / `@EqualsAndHashCode` on an entity — it includes every field, so it triggers
lazy loads and breaks on collections. Never put `@Data` on an entity.

---

## 9. Locking

### Optimistic — the default choice

```java
@Version private Long version;
```

Hibernate adds `WHERE id = ? AND version = ?` to every UPDATE and increments the version. Zero rows
updated → someone else changed it → `OptimisticLockException` /
`ObjectOptimisticLockingFailureException`. No database locks held, so it scales; you pay with a
failed transaction under contention.

Handling it properly means **retrying the whole transaction** (re-read, re-apply, re-commit) — not
catching and ignoring:

```java
@Retryable(retryFor = OptimisticLockingFailureException.class, maxAttempts = 3,
           backoff = @Backoff(delay = 50, multiplier = 2))
@Transactional
public void adjustStock(Long id, int delta) { ... }
```

Note the retry must be *outside* the transaction boundary — so the annotated method must be the outer
one (proxy rules from `07-spring-core.md` apply).

### Pessimistic — when contention is high or the work is expensive

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)   // SELECT ... FOR UPDATE
Optional<Account> findById(Long id);
```

Holds a row lock for the rest of the transaction. Correct for a hot counter or a job queue; risky for
throughput and deadlock — always acquire multiple locks in a consistent order (see `09-sql-databases.md`).
`PESSIMISTIC_READ` is a shared lock; add `jakarta.persistence.lock.timeout` to fail fast instead of blocking.

---

## 10. Caches

- **L1 = the persistence context.** Always on, per-transaction, not shared. This is the identity map.
- **L2 = shared across sessions** (Ehcache, Hazelcast, Infinispan, Redis), per entity type, opt-in
  with `@Cache`.
- **Query cache** — caches result *ids* for a query; needs L2 to be useful; easily a net loss.

**Why L2 is dangerous in a multi-instance deployment:** each JVM has its own L2 unless it is a
clustered/distributed cache. Instance A updates a row, instance B serves the stale cached entity —
indefinitely, until TTL. Any write path that bypasses Hibernate (a bulk `@Modifying` update, a native
query, Flyway, a DBA) also invalidates nothing.

Default to **no L2**. Cache at the application layer with explicit keys and TTLs where you control
invalidation (`15-caching.md`).

---

## 11. Batch writes: flush, clear, and batch_size

Inserting 100k rows in one persistence context means 100k managed entities held in memory and dirty
checked on every flush — O(n²) behaviour, then OOM.

```java
for (int i = 0; i < rows.size(); i++) {
    em.persist(rows.get(i));
    if (i % 50 == 0) { em.flush(); em.clear(); }   // push to DB, then evict from L1
}
```

For JDBC batching to actually happen:

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

**Trap: `GenerationType.IDENTITY` disables insert batching entirely.** Hibernate must execute each
INSERT immediately to learn the generated key, so it can't queue them. Use `GenerationType.SEQUENCE`
with a pooled optimizer (`allocationSize = 50`) — one sequence call per 50 rows, and batching works.
`AUTO` on MySQL resolves to IDENTITY; on Postgres, to SEQUENCE.

For genuinely large loads, skip JPA: `JdbcTemplate.batchUpdate`, or `COPY`/`LOAD DATA`.

---

## 12. Schema management: Flyway vs `ddl-auto`

`spring.jpa.hibernate.ddl-auto`: `none` | `validate` | `update` | `create` | `create-drop`.

**Production: `validate` (or `none`) with Flyway/Liquibase owning the schema.** `update` never drops
or renames, silently diverges between environments, gives no review artifact, and can lock a big
table at startup on every instance simultaneously. `validate` is valuable — it fails fast when the
entity and the migrated schema disagree.

Migration discipline: versioned, immutable once merged, forward-only, checked into git, run by one
process at startup (Flyway takes a lock, so concurrent replicas are safe but the first one wins).
Zero-downtime migration patterns are in `09-sql-databases.md`.

---

## 13. Spring Data repository mechanics

- Interfaces only; Spring generates a proxy implementation at startup.
- **Derived queries**: the method name is parsed into a criteria tree —
  `findByCustomerEmailAndStatusOrderByCreatedAtDesc`. Compile-safe-ish (a typo fails at *startup*, which
  is good). Stop when the name exceeds readability; switch to `@Query`.
- `@Query` JPQL is validated at startup; native (`nativeQuery = true`) is not.
- Projections: an interface with getters (`interface OrderView { Long getId(); String getCustomerName(); }`)
  makes Hibernate select only those columns. Cheapest read path.
- **`@Modifying`** is required for bulk `UPDATE`/`DELETE` JPQL. It **bypasses the persistence context**:
  no dirty checking, no cascades, no `@Version` increment, and the L1 cache now holds stale entities.
  Use `@Modifying(clearAutomatically = true, flushAutomatically = true)` and prefer to do it in a
  transaction that doesn't hold those entities.
- `deleteAll()` loads every entity and deletes one by one (so callbacks/cascades fire);
  `deleteAllInBatch()` issues one statement and skips all of it. Know which you called.

---

## 14. Transaction boundaries and open-session-in-view

**Boundary placement: the service method.** It is the unit of business work, so it is the unit of
atomicity. Repositories are already transactional individually (`SimpleJpaRepository` is
`@Transactional(readOnly=true)` at class level with writes overridden) — relying on that gives you one
transaction per call, which means no atomicity across two writes. Controllers are the wrong boundary
(a transaction spanning JSON serialization holds a pooled connection for the whole response).

Mark read paths `@Transactional(readOnly = true)`: skips dirty checking, may route to a replica.

**Open Session In View** (`spring.jpa.open-in-view`, default **true** in Boot): a filter keeps the
`EntityManager` open for the whole request, so lazy loads work in the view/serialization layer. Why to
turn it off:
- Lazy loads fire *during* JSON serialization — N+1 in the rendering path, invisible in service tests.
- A DB connection is held for the entire request, including slow client writes → pool exhaustion.
- Those queries run outside any transaction, each in its own auto-commit.
- It hides the design error (entities escaping the service layer).

Set `spring.jpa.open-in-view=false`, fix the `LazyInitializationException`s that appear, and you have
a correct application. That noisy Boot warning at startup exists for this reason.

---

## Atomic concept checklist

- [ ] I can name the four entity states and every transition between them.
- [ ] I can explain the persistence context as an identity map plus a dirty-checking snapshot store.
- [ ] I know `save()` is unnecessary on a managed entity — and that mutating one commits even if I never call save.
- [ ] I know flush is not commit, and that auto-flush fires before a JPQL query but not before a native one.
- [ ] I know `persist` is for new entities and mutates the argument; `merge` is for detached and returns a managed copy.
- [ ] I can state the returned-copy bug: changes applied to the argument after `merge` are lost.
- [ ] I know Spring Data `save()` picks persist vs merge from `isNew()`, and that assigned IDs cause a SELECT before every INSERT.
- [ ] I know `@ManyToOne` and `@OneToOne` default to EAGER and I override them to LAZY.
- [ ] I know an optional non-owning `@OneToOne` cannot be lazy without `@MapsId` or bytecode enhancement.
- [ ] I can explain `LazyInitializationException` as touching a proxy after its session closed, and rank the fixes with DTO mapping near the top.
- [ ] I know `getReference()` returns an id-only proxy that can throw `EntityNotFoundException` far from the call site.
- [ ] I can spot N+1 from SQL logs and fix it with JOIN FETCH, `@EntityGraph`, DTO projection, or `@BatchSize`.
- [ ] I know two collection JOIN FETCHes give `MultipleBagFetchException` or a cartesian product.
- [ ] I recognise `HHH000104` as "the whole table was loaded into memory to paginate" and fix it with the two-query id-then-fetch pattern.
- [ ] I know why entity `hashCode` must be constant when the id is generated, and never put Lombok `@Data` on an entity.
- [ ] I can explain `@Version`: the UPDATE carries `WHERE version = ?`, zero rows means a conflict, and the fix is retrying the whole transaction.
- [ ] I know `PESSIMISTIC_WRITE` is `SELECT ... FOR UPDATE` held to the end of the transaction.
- [ ] I know L1 is the per-transaction persistence context and L2 is shared, opt-in, and stale-prone across instances and bulk writes.
- [ ] I know batching needs `flush()` + `clear()` in a loop, `hibernate.jdbc.batch_size`, and that IDENTITY generation disables batching.
- [ ] I use Flyway with `ddl-auto=validate` and can explain why `update` is unsafe in production.
- [ ] I know `@Modifying` bulk queries bypass the persistence context and leave stale L1 entities.
- [ ] I place transactions on service methods, mark reads `readOnly = true`, and turn `open-in-view` off.