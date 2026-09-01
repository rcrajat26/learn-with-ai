# 05 — JPA / Hibernate Persistence

**What this decides:** whether the prep plan's JPA sharp-edges sessions (N+1,
locking, L1/L2 cache) land on solid foundations or need prerequisite material
(entity lifecycle, persistence context, proxies).

---

## Ladder

### Q1 [L1] explain-back — What does an ORM buy you and what does it cost?
**Strong answer:** buys: object↔row mapping, dirty checking, portability,
less boilerplate. Costs: hidden SQL (N+1), impedance mismatch (inheritance,
identity), performance surprises, learning the ORM itself. Both sides
required; one-sided answer = 0.5.

### Q2 [L2] explain-back — Entity lifecycle + persistence context
Name the entity states and explain what the persistence context is.
**Strong answer:** transient (new, unknown to JPA) → managed (attached,
tracked in the persistence context = session-scoped first-level cache /
identity map) → detached (context closed/cleared) → removed. The context
guarantees one instance per id per session and powers dirty checking.
**L0–L1 here mandates the JPA-foundations prerequisite in gaps.md** — the
whole sharp-edges track assumes this vocabulary.

### Q3 [L2] explain-back — `persist` vs `merge` (vs Spring Data `save`)
**Strong answer:** `persist` makes a transient instance managed (fails/
undefined on detached); `merge` copies a detached instance's state onto a
managed copy AND RETURNS THE MANAGED COPY — the argument stays detached
(classic bug: keep using the argument). Spring Data `save` = persist when
id is null/new, else merge.

### Q4 [L2] explain-back — Lazy vs eager, and what a proxy has to do with it
**Strong answer:** LAZY returns a Hibernate proxy/`PersistentBag` that loads
on first access — requires an open session; EAGER loads with the owner (join
or extra select). Defaults: `@ManyToOne`/`@OneToOne` EAGER,
`@OneToMany`/`@ManyToMany` LAZY. Bonus: why "LAZY everywhere + explicit
fetching" is the sane strategy.

### Q5 [L3] scenario — LazyInitializationException
A controller returns an `Order` entity; serialization of
`order.getItems()` throws `LazyInitializationException`. Why exactly, and
name three different fixes with their trade-offs.
**Strong answer:** the persistence context closed when the transactional
service method returned; the proxy has no session to load from. Fixes:
fetch explicitly in the query (`JOIN FETCH`/`@EntityGraph`) — preferred; map
to a DTO inside the transaction — preferred; `@Transactional` on a broader
scope or open-session-in-view — works but drags sessions through the web
layer (know why OSIV is contested). "Mark it EAGER" alone = 0.5 (fixes this
symptom, degrades everything else).

### Q6 [L3] spot-the-bug — N+1
```java
List<Author> authors = authorRepo.findAll();           // 1 query
for (Author a : authors) {
    total += a.getBooks().size();                       // ?
}
```
What SQL does this produce for 200 authors, and what are your fix options?
**Strong answer:** 1 + 200 queries (one per lazy `books` access). Fixes:
`JOIN FETCH` JPQL, `@EntityGraph`, DTO projection with aggregate
(`select a.id, count(b)... group by`), or `@BatchSize`/batch fetching to
turn 200 into a few IN-queries. Naming the count "1+N" plus ≥2 fixes = 1.

### Q7 [L3] predict-output — Dirty checking
```java
@Transactional
public void touch(long id) {
    User u = repo.findById(id).orElseThrow();
    u.setLastSeen(Instant.now());
    // no repo.save(u)
}
```
Does the database get updated?
**Strong answer:** Yes — `u` is managed; at flush/commit Hibernate compares
snapshots and issues the UPDATE automatically. `save()` is unnecessary for
managed entities. Bonus: this is also how *accidental* updates happen —
mutating an entity in a read path inside a transaction writes to the DB.

### Q8 [L3] discriminator — equals/hashCode on entities
Why is implementing `equals`/`hashCode` on a JPA entity with a generated id
tricky? What's your policy?
**Strong answer:** id is null before persist → hash changes after save →
breaks HashSet membership (ties to 01/C5); using all fields breaks on any
mutation; proxy classes break `getClass()` comparison. Policies: business/
natural key if one exists; or id-based with constant hashCode (Vlad
Mihalcea's approach); or don't put entities in hash collections. Any
coherent policy + the null-id mechanism = 1.

### Q9 [L4] scenario — Concurrent updates
Two users edit the same product simultaneously; last write silently wins and
support tickets appear. Compare optimistic vs pessimistic locking for this,
and describe concretely what you'd implement.
**Strong answer:** optimistic — `@Version` column; concurrent commit throws
`OptimisticLockException`; catch → retry or surface a conflict to the user;
right when conflicts are rare. Pessimistic — `SELECT ... FOR UPDATE`
(`PESSIMISTIC_WRITE`); blocks contenders; right for hot rows/financial
invariants; costs: held locks, timeouts, deadlock risk. Picks one for this
case with a reason. Bonus: version field also travels to the UI (stale-form
detection).

---

## Breadth checklist (rate 0–3)

- [CORE] `@EntityGraph` or `JOIN FETCH` — used at least one in anger
- [CORE] DTO projections (interface/record projections, `select new`)
- [CORE] Flyway or Liquibase — schema migrations as code
- [CORE] Transaction boundary placement — service layer, why not repository/controller
- [CORE] Reading Hibernate's SQL log (`show-sql`/logger) — ever debugged with it?
- Cascade types (`PERSIST`, `MERGE`, `REMOVE`) + `orphanRemoval` — and their dangers
- Flush modes / when flush happens (commit, before queries)
- `getReferenceById` vs `findById` (proxy without select)
- Pagination via `Pageable` — and its count-query cost
- `@BatchSize` / `default_batch_fetch_size`
- Second-level cache — concept + why it's off by default (0–1 fine)
- Open-session-in-view — the debate (heard of it?)
- Batch inserts (`saveAll` ≠ batching; JDBC batch settings, id generation impact)
- Native queries + result mapping — escape hatch fluency
- Soft deletes / auditing (`@CreatedDate`, Envers heard-of)
- Composite keys (`@EmbeddedId`) (0–1 fine)
- When to drop the ORM: reporting queries, bulk updates (`@Modifying`)
