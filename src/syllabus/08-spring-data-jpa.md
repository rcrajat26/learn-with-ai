# Syllabus — 08 Spring Data JPA and Hibernate

**Target version: Jakarta Persistence 3.1 / Hibernate ORM 6.6.x / Spring Data JPA 3.5.x
(Spring Boot 3.5.x, Spring Framework 6.2.x) on Java 21.**
Every annotation, property key, default value, constant and class name below is stated against that
baseline. Three newer lines exist and change several things this topic teaches, so every divergence
is marked `[VERSION-TRAP]` inline and the write pass must state what is true in the 6.6/3.5 baseline
*and* what changed after:

- **Hibernate ORM 7.0** (May 2025) — requires Jakarta Persistence **3.2**, removes `@Where`,
  `@WhereJoinTable`, `@OrderBy` (Hibernate's), `@Proxy`, `@LazyToOne`, `@LazyCollection`,
  `@SelectBeforeUpdate`, `@Loader`, `@Persister`, `org.hibernate.annotations.@Table`, `@Target`,
  `@ForeignKey`, `@Index`, `@IndexColumn`, `@GeneratorType`; drops `Session#save/update/delete/load/get`
  in favour of `persist/merge/remove/getReference/find`; drops `CascadeType.SAVE_UPDATE` and
  `CascadeType.DELETE`; makes `StatelessSession` use the second-level cache **by default**; makes
  `refresh()` on a detached entity throw; makes immutable-entity update queries throw by default;
  maps `char`/`Character` to `varchar(1)` instead of `char(1)`; defaults native-query temporal
  results to `java.time` rather than `java.sql`. `[RESEARCH]`
- **Spring Data JPA 4.0** (Spring Data 2025.1.0, November 2025) — Spring Framework 7, Jakarta EE 11
  (JPA 3.2), **AOT-generated repositories enabled by default**, JSpecify null-safety, Jackson 3,
  vector-search repository methods via `hibernate-vector`. `[RESEARCH]`
- **Jakarta Persistence 3.2** — pervasive type parameters on the Criteria and entity-graph APIs,
  `EntityManagerFactory#getSchemaManager`, nullable `Transaction#getTimeout`.

The four deltas that most often produce a stale answer in an interview are: **`javax.persistence.*`
→ `jakarta.persistence.*`** (Hibernate 5.6 → 6.0 / Boot 2 → 3), **`@GenericGenerator` deprecated in
favour of `@IdGeneratorType`** (Hibernate 6.5), **HQL/Criteria now compile through SQM rather than
Criteria→HQL→SQL string manipulation** (Hibernate 6.0), and **`getOne()`/`getById()` deprecated in
favour of `getReferenceById()`** (Spring Data JPA 2.5/2.7).

Scope boundary against the sibling guides. This file owns **the persistence context, the mapping
model, the query pipeline, and the Spring Data repository layer**: entity states, dirty checking,
flush ordering, identifier generation, mappings and associations, fetching and N+1, JPQL/HQL/Criteria/
native queries, repository proxies, projections, specifications, pagination, `@Transactional`'s
*interaction with the EntityManager*, JPA-level locking, the three caches, bytecode enhancement,
auditing, multi-tenancy, statement batching, and the JPA testing and migration surface.

Owned elsewhere:

- The container, the proxy mechanism itself, `@Transactional`'s *interceptor* mechanics, propagation
  semantics, self-invocation, `PersistenceExceptionTranslationPostProcessor` and auto-configuration
  live in `07-spring-core.md`. This guide states the persistence-context consequence of each and
  points there for the container mechanism. `[X-REF 07]`
- Isolation levels and their anomalies, MVCC, index selection, query plans, deadlock analysis,
  connection-pool sizing arithmetic and zero-downtime schema migration live in
  `09-sql-databases.md`. `[X-REF 09]`
- Cache stores themselves (Redis, Caffeine, stampede, invalidation topology) live in
  `15-caching.md`. `[X-REF 15]`
- Test slices, Mockito, Testcontainers mechanics and flakiness live in `16-testing.md`.
  `[X-REF 16]`
- `equals`/`hashCode` contract fundamentals and `HashSet` bucket mechanics live in
  `02-java-collections.md`; this guide owns only the *entity* variant of the problem. `[X-REF 02]`
- Heap sizing, OOM taxonomy, GC pressure from large result sets and heap-dump workflow live in
  `06-jvm-internals.md`. `[X-REF 06]`
- Records, `Optional`, streams and sealed types as language features live in `04-modern-java.md`;
  this guide owns their use as projections and repository return types. `[X-REF 04]`
- API pagination contracts, error payloads and versioning live in `12-api-design.md`. `[X-REF 12]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real Hibernate/Spring Data source, spec text or javadoc (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling, generic Java 21 code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 6.6/3.5 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte arithmetic explicitly |
| `[PROP]` | give the exact property key and its default |
| `[API]` | give the exact type/method/attribute signature |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[SQL]` | must show the generated SQL, not just describe it |
| `[DIAG]` | must show real output — a stack trace, a log line, a statistics dump — and read it line by line |

---

# PART 1 — BASICS

## §1.1 Why an ORM exists at all

1.1.1 The impedance-mismatch statement, precisely: five specific mismatches — granularity (objects
      are finer-grained than tables), inheritance (SQL has none), identity (`==` vs `equals` vs
      primary key), associations (references are directional, foreign keys are not), and data
      navigation (objects walk graphs, SQL wants set operations). `[PROVE]`
1.1.2 What ORM buys, enumerated and each one attributed to a mechanism: object-graph navigation
      (proxies), dirty checking (no hand-written UPDATE), the identity map (L1 cache), dialect
      portability, a query language over entities, optimistic locking for free.
1.1.3 What ORM costs: a leaky abstraction you must know the SQL of; implicit behaviour (auto-flush,
      cascade, dirty checking) that surprises; poor fit for bulk and analytic work; a learning curve
      where "working" and "correct under load" are far apart.
1.1.4 The mature interview position: ORM for transactional CRUD on an object graph; JDBC/jOOQ/native
      SQL for reporting, bulk updates and anything where the query shape matters more than the object
      shape. Mixing is normal and correct, not a failure. `[PROVE]`
1.1.5 The pre-JPA history worth one paragraph: hand-rolled DAOs, EJB 2.x entity beans (container-
      managed persistence, remote interfaces, deployment descriptors), Hibernate 1.0 (2001) as the
      open-source revolt, JDO as the competing spec, and JPA 1.0 (2006) as Hibernate's model
      standardised into EJB 3.0.
1.1.6 Why Gavin King's Hibernate won the standardisation: POJO entities, no container interfaces,
      testable outside an app server — the same thesis as Spring's. `[X-REF 07]`
1.1.7 "ORM is not a SQL generator, it is a *state-synchronisation engine*." State this before
      anything else; it is the single sentence that makes every later surprise predictable. `[PROVE]`
1.1.8 The three layers this guide keeps distinct, with the boundary named: **Jakarta Persistence**
      (the spec: annotations, `EntityManager`, JPQL), **Hibernate ORM** (the implementation: SQM,
      persistence context internals, extra annotations), **Spring Data JPA** (the repository layer:
      proxies, derived queries, projections, pagination). Most "JPA" questions are really about one
      specific layer. `[TRAP]`
1.1.9 Hibernate is not *only* a JPA provider: `SessionFactory`/`Session` predate and exceed the spec
      (`StatelessSession`, `@SQLRestriction`, `@Filter`, `@NaturalId`, multi-tenancy, Envers), and
      Hibernate can be used without JPA bootstrap at all. `[TRAP]`
1.1.10 The alternatives and when each wins: **Spring Data JDBC** (no lazy loading, no dirty checking,
       aggregate-root model), **jOOQ** (typesafe SQL, no state machine), **MyBatis** (SQL in XML/
       annotations, explicit mapping), **plain `JdbcTemplate`/`JdbcClient`**, **R2DBC** (reactive,
       no JPA). One-line trade for each. `[RESEARCH]`
1.1.11 The other JPA providers you may meet: **EclipseLink** (the spec's reference implementation),
       **OpenJPA** (retired), **DataNucleus**. Every "JPA says" claim should be checked against
       whether Hibernate actually does it that way.
1.1.12 The interview framing this whole guide serves: turning "the query fired twice / didn't fire /
       fired 400 times" into a named mechanism — a flush, a proxy, a cascade, a fetch plan, or a
       repository-proxy decision.

*(12 leaves)*

## §1.2 The spec, the versions and the package names

1.2.1 The version timeline with dates and headline change: JPA 1.0 (2006, EJB 3.0), 2.0 (2009,
      Criteria API, `@ElementCollection`, pessimistic locking, metamodel), 2.1 (2013, entity graphs,
      stored procedures, `@Converter`, criteria bulk update/delete, schema generation), 2.2 (2017,
      `java.time`, `@Repeatable`, streaming results), **Jakarta Persistence 3.0 (2020, package
      rename only)**, **3.1 (2022, `GenerationType.UUID`, numeric functions, `AutoCloseable`)**,
      **3.2 (2024, generics on Criteria/entity graphs, `SchemaManager`)**. `[NUM]` `[RESEARCH]`
1.2.2 The `javax.persistence` → `jakarta.persistence` rename: forced by Oracle's retention of the
      `javax` trademark when Java EE moved to the Eclipse Foundation. It is a *pure* rename in 3.0 —
      no behavioural change — and it is why every pre-2022 code sample fails to compile.
      `[VERSION-TRAP]` `[TRAP]`
1.2.3 Jakarta Persistence 3.1's additions, named: `GenerationType.UUID` and `java.util.UUID` as a
      basic type; the numeric functions **`CEILING`, `EXP`, `FLOOR`, `LN`, `POWER`, `ROUND`, `SIGN`**
      in JPQL and the matching `CriteriaBuilder` methods; `LOCAL DATE`/`LOCAL TIME`/`LOCAL DATETIME`
      functions; `EntityManager` and `EntityManagerFactory` extending `java.lang.AutoCloseable`;
      `ClassTransformer.transform` throwing a JPA exception. `[API]` `[RESEARCH]`
1.2.4 Jakarta Persistence 3.2's additions worth knowing: type parameters throughout the Criteria API
      and `EntityGraph`, `EntityManagerFactory#getSchemaManager`, `Order#getNullPrecedence()`
      returning `Nulls`, nullable `Transaction#getTimeout`, and the union/intersect/except additions.
      `[VERSION-TRAP]` `[RESEARCH]`
1.2.5 Hibernate's own version timeline: 3.x (annotations), 4.x (`ServiceRegistry`), 5.x
      (`StatementInspector`, slow-query log in 5.4.5, delayed connection acquisition in 5.2.10),
      **6.0 (2022 — SQM, new type system, Jakarta, read-by-position)**, 6.2 (CTEs), 6.4
      (`@SoftDelete`, `@EmbeddedColumnNaming`), 6.5 (`@GenericGenerator` deprecated), 6.6
      (embeddable inheritance, `array_includes`), **7.0 (2025 — JPA 3.2, mass annotation removal)**.
      `[NUM]` `[RESEARCH]`
1.2.6 Spring Data JPA's version timeline and the release-train naming: `2021.x` → Spring Data JPA
      2.6, `2022.0` → 3.0 (Boot 3.0), `2024.1` → 3.4, `2025.0` → **3.5 (this baseline)**,
      `2025.1` → **4.0** (Boot 4.0, Framework 7). Say why the train name and the module version
      differ. `[RESEARCH]` `[VERSION-TRAP]`
1.2.7 The Spring Boot ↔ Hibernate ↔ Spring Data compatibility matrix in three rows: Boot 2.7 →
      Hibernate 5.6 / `javax`; Boot 3.0–3.3 → Hibernate 6.1–6.4 / `jakarta`; Boot 3.4–3.5 →
      Hibernate 6.6; Boot 4.0 → Hibernate 7.x. You do not choose the Hibernate version — the Boot
      BOM does. `[NUM]` `[RESEARCH]`
1.2.8 Where to read the spec itself: the Jakarta Persistence 3.1 PDF, section numbering (chapter 2
      entities, 3 EntityManager, 4 JPQL, 6 Criteria, 11 annotations), and why quoting the spec beats
      quoting a blog. `[SOURCE]`
1.2.9 Hibernate's three documentation artefacts and what each is for: the **User Guide** (mapping and
      configuration), **A Guide to Hibernate Query Language** (HQL reference), and the **Introduction
      to Hibernate 6** (the tutorial). Plus the **migration guide** per minor version — the single
      most under-read document in the ecosystem. `[SOURCE]` `[RESEARCH]`
1.2.10 The dependency coordinates you actually add: `spring-boot-starter-data-jpa` pulls
       `spring-data-jpa`, `spring-orm`, `hibernate-core`, `jakarta.persistence-api`,
       `jakarta.transaction-api`, `spring-boot-starter-jdbc` (which pulls **HikariCP**), and
       `spring-aspects`. Name what you get for free and what you must add (driver, Flyway,
       `hibernate-jpamodelgen`, `hibernate-envers`, a JCache provider). `[API]`
1.2.11 `hibernate-jpamodelgen` as an annotation processor: generates `Order_`, `Customer_` static
       metamodel classes used by Criteria and Specifications. Forgetting it is why
       `Order_.status` "doesn't exist". `[TRAP]`

*(11 leaves)*

## §1.3 Bootstrap — from `application.yml` to a `SessionFactory`

1.3.1 The two spec bootstrap modes: **Java SE** (`Persistence.createEntityManagerFactory("unit")`
      reading `META-INF/persistence.xml`) versus **container** (the container builds the
      `EntityManagerFactory` and injects `@PersistenceContext`). Spring uses neither literally — it
      is a *third* mode. `[TRAP]`
1.3.2 `persistence.xml`'s element inventory, read once even though you will never write one:
      `<persistence-unit name transaction-type>`, `<provider>`, `<jta-data-source>`,
      `<non-jta-data-source>`, `<class>`, `<exclude-unlisted-classes>`, `<shared-cache-mode>`,
      `<validation-mode>`, `<properties>`. `[SOURCE]`
1.3.3 `LocalContainerEntityManagerFactoryBean` — Spring's replacement. It is a `FactoryBean<EMF>`
      (so `&entityManagerFactory` gets the bean itself), and it does packages-to-scan discovery
      instead of `<class>` listing. `[API]` `[X-REF 07]`
1.3.4 `LocalEntityManagerFactoryBean` vs `LocalContainerEntityManagerFactoryBean` vs a JNDI lookup:
      three ways, only the middle one used in Boot, and the reason (it lets Spring supply the
      `DataSource` and the `PersistenceUnitInfo`). `[API]`
1.3.5 The Boot auto-configuration chain, named class by class: `DataSourceAutoConfiguration` →
      `HibernateJpaConfiguration` (inside `HibernateJpaAutoConfiguration`) →
      `JpaBaseConfiguration` → `entityManagerFactory` bean + `transactionManager` bean;
      `JpaRepositoriesAutoConfiguration` → `JpaRepositoryConfigExtension` registers repositories.
      `[API]` `[FLOW]` `[X-REF 07]`
1.3.6 `EntityScanPackages` and how `@SpringBootApplication` decides which packages hold entities;
      `@EntityScan` as the override. Same leaf-package trap as component scanning. `[TRAP]`
1.3.7 `HibernatePropertiesCustomizer` and `EntityManagerFactoryBuilder` as the two supported
      extension points; why setting `spring.jpa.properties.*` beats replacing the whole bean.
      `[API]` `[PROP]`
1.3.8 The `SessionFactory` under the `EntityManagerFactory`:
      `entityManagerFactory.unwrap(SessionFactory.class)`, and why unwrapping is legitimate rather
      than a hack. `[API]`
1.3.9 Hibernate's own bootstrap objects, in order: `BootstrapServiceRegistry` →
      `StandardServiceRegistryBuilder` → `MetadataSources` → `Metadata` → `SessionFactoryBuilder` →
      `SessionFactoryImpl`. Named here, walked in §3.1. `[API]` `[FLOW]`
1.3.10 What happens at startup, cost-wise: annotation reading, metadata binding, proxy class
       generation, SQL pre-generation for CRUD, query-plan cache warm-up, and `ddl-auto` execution.
       This is why a 400-entity app pays seconds of startup. `[NUM]`
1.3.11 `@PersistenceContext` vs `@Autowired EntityManager`: Spring's
       `PersistenceAnnotationBeanPostProcessor` handles the former;
       `SharedEntityManagerCreator` produces the thread-bound proxy either way in Boot. `[API]`
1.3.12 **The shared `EntityManager` proxy is the most under-known object in the stack.** The
       `EntityManager` you inject is not an `EntityManager` — it is a proxy that, per call, looks up
       the transaction-bound one via `TransactionSynchronizationManager`, or opens a throwaway one.
       `[TRAP]` `[SOURCE]`
1.3.13 `@PersistenceUnit EntityManagerFactory` and `EntityManagerFactoryInfo` — when you genuinely
       need the factory (multi-tenancy, statistics, `createEntityManager` for a batch job). `[API]`
1.3.14 Two data sources / two persistence units: `@Primary`, two
       `LocalContainerEntityManagerFactoryBean`s, two `JpaTransactionManager`s,
       `@EnableJpaRepositories(basePackages, entityManagerFactoryRef, transactionManagerRef)`, and
       the `@Qualifier` on `@Transactional`. `[API]`
1.3.15 `spring.jpa.*` versus `spring.jpa.properties.*` versus `spring.jpa.hibernate.*`: the first is
       Boot's own typed surface (`JpaProperties`), the second is passed verbatim to Hibernate, the
       third is Boot's Hibernate-specific block. Putting a Hibernate key under `spring.jpa.` and
       having it silently ignored is a top-five configuration bug. `[PROP]` `[TRAP]`
1.3.16 The `JpaProperties` fields, named: `databasePlatform`, `database`, `generateDdl`, `showSql`,
       `openInView` (**default `true`**), `mappingResources`, `properties`. `[API]` `[NUM]`
       `[RESEARCH]`
1.3.17 Shutdown: `EntityManagerFactory.close()`, connection-pool close ordering, and why
       `create-drop` plus a failed shutdown leaves a dirty database.

*(17 leaves)*

## §1.4 The `EntityManager` API surface

1.4.1 The full method inventory, grouped, with signatures: **state** — `persist`, `merge`, `remove`,
      `detach`, `refresh`, `contains`, `clear`; **lookup** — `find` (4 overloads),
      `getReference`; **sync** — `flush`, `setFlushMode`, `getFlushMode`; **locking** —
      `lock` (2 overloads); **query** — `createQuery` (4), `createNamedQuery` (2),
      `createNativeQuery` (3), `createNamedStoredProcedureQuery`, `createStoredProcedureQuery`,
      `createEntityGraph`, `getEntityGraph`, `getEntityGraphs`; **meta** — `getMetamodel`,
      `getEntityManagerFactory`, `getCriteriaBuilder`, `getDelegate`, `unwrap`,
      `getProperties`/`setProperty`; **tx** — `getTransaction`, `joinTransaction`,
      `isJoinedToTransaction`; **lifecycle** — `isOpen`, `close`. `[API]` `[SOURCE]`
1.4.2 `find(Class, Object)` vs `find(Class, Object, LockModeType)` vs
      `find(Class, Object, Map<String,Object> properties)` vs the 4-arg form — the properties map is
      how you pass `jakarta.persistence.fetchgraph` / `loadgraph` / `lock.timeout` /
      `query.timeout`. `[API]` `[NUM]`
1.4.3 `find` returns `null` for a missing row; `getReference` returns a proxy and throws
      `EntityNotFoundException` *later*. State the design intent of each. `[TRAP]`
1.4.4 `FlushModeType.AUTO` (default) vs `COMMIT`, and Hibernate's extra `FlushMode.MANUAL` /
      `ALWAYS` on `Session`. Set at factory, session, or per-query level; per-query wins. `[API]`
      `[NUM]`
1.4.5 `Session`'s extras over `EntityManager`, named: `saveOrUpdate` (removed in 7), `byId`,
      `byMultipleIds`, `byNaturalId`, `bySimpleNaturalId`, `createQuery(CriteriaQuery)`,
      `setDefaultReadOnly`, `setHibernateFlushMode`, `getStatistics`, `doWork`, `doReturningWork`,
      `evict`, `isDirty`, `getIdentifier`, `getLobHelper`, `enableFilter`,
      `setCacheMode`, `getEntityGraph`. `[API]` `[VERSION-TRAP]`
1.4.6 `StatelessSession`: no persistence context, no dirty checking, no cascades, no L1, no lifecycle
      events, no auto-flush. `insert`/`update`/`delete`/`get`/`refresh`/`upsert`, and 7.0's
      `insertMultiple`/`updateMultiple`/`deleteMultiple`. The right tool for a 10-million-row ETL.
      `[API]` `[RESEARCH]` `[VERSION-TRAP]`
1.4.7 `EntityManager.getDelegate()` and `unwrap(Session.class)` — two ways down to Hibernate, and
      why `unwrap` is the correct one. `[API]`
1.4.8 `EntityTransaction` (`begin`, `commit`, `rollback`, `setRollbackOnly`, `getRollbackOnly`,
      `isActive`, `getTimeout`) — the resource-local API you *never* call under Spring, and what
      happens if you do (`TransactionRequiredException`, or a silently separate transaction).
      `[TRAP]`
1.4.9 `EntityManagerFactory`'s surface: `createEntityManager` (4 overloads), `getCriteriaBuilder`,
      `getMetamodel`, `getCache`, `getPersistenceUnitUtil`, `addNamedQuery`,
      `addNamedEntityGraph`, `unwrap`, `getProperties`, `isOpen`, `close`, and 3.2's
      `getSchemaManager`. `[API]`
1.4.10 `Cache` (the L2 handle): `contains`, `evict(Class)`, `evict(Class, Object)`, `evictAll`, and
       Hibernate's `unwrap(org.hibernate.Cache.class)` extras
       (`evictQueryRegions`, `evictCollectionData`, `evictNaturalIdData`). `[API]`
1.4.11 `PersistenceUnitUtil.getIdentifier(entity)` and `isLoaded(entity[, attributeName])` — the
       spec-portable way to ask "is this proxy initialised" without touching it. Hibernate's
       equivalent is `Hibernate.isInitialized` / `Hibernate.isPropertyInitialized`. `[API]`
1.4.12 The `Query` interface surface: `setParameter` (positional, named, typed, temporal),
       `setMaxResults`, `setFirstResult`, `setHint`, `setFlushMode`, `setLockMode`,
       `getResultList`, `getResultStream`, `getSingleResult`, `getSingleResultOrNull` (Hibernate /
       JPA 3.2), `executeUpdate`, `unwrap`. `[API]` `[VERSION-TRAP]`
1.4.13 `TypedQuery<T>` vs `Query`: type safety only, no behaviour change; `SelectionQuery` and
       `MutationQuery` as Hibernate 6's split of the two intents. `[API]` `[RESEARCH]`
1.4.14 `getSingleResult()` throws `NoResultException` on zero rows and
       `NonUniqueResultException` on more than one — both **unchecked**, both roll a transaction
       back by default. `getSingleResultOrNull()` fixes the first half. `[TRAP]`
1.4.15 `getResultStream()` and why it is a trap without a cursor: Hibernate implements it over a
       scrollable result set on some dialects and over a materialised list on others, and the stream
       must be closed inside the transaction. `[TRAP]` `[RESEARCH]`
1.4.16 `LockModeType`'s six values named here for reference, mechanics in §1.28: `NONE`,
       `OPTIMISTIC`, `OPTIMISTIC_FORCE_INCREMENT`, `PESSIMISTIC_READ`, `PESSIMISTIC_WRITE`,
       `PESSIMISTIC_FORCE_INCREMENT` (plus deprecated `READ`/`WRITE` aliases). `[API]`
1.4.17 `CacheRetrieveMode` (`USE`, `BYPASS`) and `CacheStoreMode` (`USE`, `BYPASS`, `REFRESH`) as
       query hints `jakarta.persistence.cache.retrieveMode` / `storeMode`. `[API]` `[PROP]`

*(17 leaves)*

## §1.5 The entity state machine

1.5.1 The four states with the two questions that define each — *is it in a persistence context?* and
      *does a row exist?*: **transient/new**, **managed/persistent**, **detached**, **removed**.
      Render as the table the current guide already has and keep it. `[SOURCE]`
1.5.2 Every transition, named, with the call that causes it: `new` → transient; `persist` →
      managed; `find`/`getReference`/query → managed; `merge(detached)` → *a different* managed
      instance; `remove(managed)` → removed; `flush`+commit on removed → transient; `detach`/`clear`/
      context close → detached; `refresh(managed)` → managed with DB state; `merge(transient)` →
      managed copy **plus an INSERT**. `[FLOW]`
1.5.3 The state diagram as a picture the reader must be able to redraw from memory in 60 seconds.
1.5.4 "Managed" is a property of *the pair (instance, context)*, not of the instance. The same row
      loaded in two contexts gives two managed instances that are `!=`. `[PROVE]` `[TRAP]`
1.5.5 What "removed" actually means: still in the context, still returned by `contains`, DELETE not
      yet issued, and `persist()` on it resurrects it. `[TRAP]`
1.5.6 `detach` vs `clear` vs `close` vs `evict`: one entity, all entities, the whole manager,
      Hibernate's synonym for detach. And what happens to pending changes in each case (they are
      **discarded**, silently). `[TRAP]`
1.5.7 `contains(entity)` semantics — true only for managed and removed, false for detached and
      transient; it does not hit the database.
1.5.8 `refresh(entity)` — overwrites in-memory state from the database, **discarding your unflushed
      changes**, and cascades along `REFRESH`. In Hibernate 7 it throws on a detached entity.
      `[TRAP]` `[VERSION-TRAP]`
1.5.9 Read-only entities: `Session.setReadOnly(entity, true)`, `setDefaultReadOnly`,
      `@Immutable`, and the query hint `org.hibernate.readOnly`. Mechanism: Hibernate skips taking
      the loaded-state snapshot, halving memory and skipping dirty checking. `[API]` `[PROVE]`
1.5.10 The consequence people get wrong, kept verbatim from the current guide: a managed entity
       mutated inside a transaction is flushed at commit **whether or not you call `save`**, and
       returning early does not undo it. `[TRAP]` `[SOURCE]`
1.5.11 The inverse: treating an entity as a DTO and mutating it "just for the response" writes to the
       database. Fix: map to a DTO, or detach, or don't mutate until you have decided. `[TRAP]`
1.5.12 Why `save()` on a managed entity is a no-op, proved: `SimpleJpaRepository.save` calls
       `merge`, `merge` on an already-managed instance returns it unchanged, and the UPDATE was
       coming from dirty checking anyway. `[PROVE]`
1.5.13 The `TransactionRequiredException` boundary: `persist`, `merge`, `remove`, `refresh` and
       `flush` require an active transaction; `find` and read-only queries do not. What Spring's
       shared `EntityManager` does when there is no transaction — opens and closes one per call,
       so everything is detached immediately. `[TRAP]` `[PROVE]`

*(13 leaves)*

## §1.6 The persistence context

1.6.1 Definition in one sentence: a transaction-scoped, in-memory map from
      `(entity type, identifier)` to a managed instance, plus the bookkeeping needed to compute what
      changed. It is a **transactional write-behind cache**. `[SOURCE]`
1.6.2 Property one — **the identity map**. Within one context, one row is one object: two `find`
      calls for the same id return the *same instance* (`==` is true) and issue *one* SELECT.
      `[PROVE]` `[SQL]`
1.6.3 Why the identity map is not optional: without it, two references to the same row could hold
      divergent state and both be flushed, and cyclic graphs could not be loaded. `[PROVE]`
1.6.4 Property two — **dirty checking**. On load, Hibernate keeps a *loaded-state* snapshot
      (an `Object[]` of hydrated values); at flush it compares field by field and issues UPDATE for
      the differences. Mechanism walked in §3.4. `[NUM]`
1.6.5 The memory cost of the snapshot: every managed entity is held twice (the instance plus the
      hydrated `Object[]`), which is the arithmetic behind "don't load 100k entities". Show the
      byte estimate for a 10-field entity. `[NUM]` `[PROVE]` `[X-REF 06]`
1.6.6 Property three, rarely named — **the action queue**: pending insert/update/delete/collection
      actions in a defined order, described in §3.5.
1.6.7 Property four — **write-behind**: SQL is deferred to flush so it can be batched, ordered and
      deduplicated. This is why "the exception came from `commit`, not from `save`". `[TRAP]`
1.6.8 Property five — **entity-level locking bookkeeping**: which entities hold which `LockMode`,
      needed for `OPTIMISTIC_FORCE_INCREMENT` and `lock()`.
1.6.9 The two spec context types: **transaction-scoped** (`PersistenceContextType.TRANSACTION`, the
      default — everything detaches at commit) versus **extended**
      (`PersistenceContextType.EXTENDED`, survives across transactions, only meaningful for stateful
      session beans / conversations). `[API]` `[TRAP]`
1.6.10 Hibernate's stateful equivalents of the extended context: a long `Session` with
       `FlushMode.MANUAL`, used for wizard-style conversations. Why almost nobody should.
1.6.11 L1 cache = the persistence context. The phrase "first-level cache" adds nothing except
       symmetry with L2; the *identity map* is the accurate name. `[TRAP]`
1.6.12 What the persistence context is *not*: it is not shared between threads, not shared between
       requests, not a query cache, and it does not cache query *results* — only entities by id.
       A repeated query re-hits the database and then *reuses* the existing instances. `[PROVE]`
       `[TRAP]`
1.6.13 The consequence of §1.6.12 that surprises people: after a bulk `@Modifying` UPDATE, a
       subsequent `find` returns the **stale in-memory instance**, because the row was changed
       behind the context's back. `[TRAP]`
1.6.14 `Session.isDirty()` — asks the context whether a flush would produce SQL, without flushing.
       The debugging tool nobody uses. `[API]`
1.6.15 Context size as an operational metric: `SessionStatistics` (`getEntityKeys`,
       `getCollectionKeys`), and Hibernate's `Statistics` counters. Basis of §2.21. `[API]`
1.6.16 The `@Transactional(readOnly = true)` optimisation restated precisely: Spring sets Hibernate's
       flush mode to `MANUAL`, so **no dirty-check pass and no automatic flush happens at all**, and
       it sets the JDBC connection read-only (a hint the driver may use to route to a replica).
       `[PROVE]` `[SOURCE]` `[RESEARCH]`
1.6.17 **Trap:** `readOnly = true` does not make entities immutable and does not prevent writes — an
       explicit `flush()`, a `@Modifying` query or a nested writable transaction still writes. Some
       databases reject writes on a read-only connection, most do not. `[TRAP]`

*(17 leaves)*

## §1.7 Flush — what it is and exactly when it happens

1.7.1 Flush is "write the pending SQL now", **not** commit. Nothing is durable, nothing is visible to
      other transactions, and a rollback still undoes it. `[TRAP]`
1.7.2 The three triggers under `FlushModeType.AUTO`: transaction commit; before a JPQL/HQL/Criteria
      query whose result **could be affected** by pending changes; an explicit `flush()`.
1.7.3 The "could be affected" rule, precisely: Hibernate computes the query space (the tables the
      query touches) and compares it to the tables with pending actions. Only overlapping ones force
      a flush. `[PROVE]` `[SOURCE]`
1.7.4 **The native-query hole.** Hibernate cannot parse a native SQL string to learn its query space,
      so it does **not** auto-flush before one, and you read stale data. Fix:
      `query.unwrap(NativeQuery.class).addSynchronizedEntityClass(Order.class)` or
      `addSynchronizedQuerySpace("orders")`, or flush explicitly. `[TRAP]` `[API]`
1.7.5 `FlushModeType.COMMIT` — flush only at commit; queries may then see stale data. When it is
      legitimate (read-heavy code paths where you know nothing pending overlaps). `[TRAP]`
1.7.6 Hibernate's `FlushMode.MANUAL` — never flush automatically at all, not even at commit. This is
      what `readOnly = true` sets. A `save()` under `MANUAL` without an explicit flush **does
      nothing**, which is the most confusing symptom in this guide. `[TRAP]` `[PROVE]`
1.7.7 `FlushMode.ALWAYS` — flush before every query regardless of query space. The correctness
      sledgehammer.
1.7.8 Per-query flush mode: `query.setFlushMode(FlushModeType.COMMIT)`, and precedence
      (query > session > factory). `[API]`
1.7.9 What flush does *not* do: it does not clear the context, does not detach anything, and does not
      release the connection. `flush()` and `clear()` are separate calls for separate reasons.
      `[TRAP]`
1.7.10 The `flush()` + `clear()` idiom and why order matters: clearing before flushing discards the
       pending SQL entirely. `[TRAP]`
1.7.11 Auto-flush inside a `findBy...` derived query: Spring Data query methods are JPQL, so they
       **do** trigger the auto-flush, which is why a `save` followed by a `findBy` in the same
       transaction unexpectedly emits the INSERT early — and can surface a constraint violation at
       the *find*. `[TRAP]` `[SQL]`
1.7.12 `saveAndFlush` vs `save`: the former forces the SQL out now so you can catch a
       `DataIntegrityViolationException` at a known line instead of at commit. `[API]`
1.7.13 Constraint violations at commit: what the stack trace looks like when the INSERT fails during
       `AbstractPlatformTransactionManager.processCommit`, why your `try/catch` around `save` never
       saw it, and how `TransactionSystemException` wraps it. `[DIAG]` `[X-REF 07]`
1.7.14 Flush inside a lifecycle callback or an `@EntityListener` — why it is unsupported and what
       breaks (`ConcurrentModificationException` on the action queue). `[TRAP]`

*(14 leaves)*

## §1.8 `persist`, `merge`, `remove` and Spring Data `save`

1.8.1 `persist(e)` — for **new** entities. Makes *the argument* managed, schedules an INSERT, and
      cascades along `PERSIST`. Returns `void`, which is the API telling you the argument was
      mutated. `[API]`
1.8.2 `persist` on a detached instance throws `EntityExistsException` (or a
      `PersistenceException` at flush). `persist` on an already-managed instance is a no-op.
      `persist` on a removed instance un-removes it. `[TRAP]`
1.8.3 When the INSERT actually runs: **immediately** for `GenerationType.IDENTITY` (Hibernate must
      have the key to build the entity key), **at flush** for `SEQUENCE`/`TABLE`/assigned. This one
      fact explains half of §2.11. `[PROVE]` `[SQL]`
1.8.4 `merge(e)` — for **detached** entities. Loads (or finds in the context) the managed instance
      for that id, copies state onto it, and **returns that managed instance**. The argument stays
      detached. Cascades along `MERGE`. `[API]`
1.8.5 The returned-copy bug, kept verbatim from the current guide: mutating the argument after
      `merge` changes nothing. `[TRAP]` `[SOURCE]`
1.8.6 `merge` does a **hidden SELECT** to load the row it is merging onto — unless the entity is
      already in the context or the L2 cache has it. This is the cost people don't see. `[PROVE]`
      `[SQL]` `[RESEARCH]`
1.8.7 `merge` on a *transient* instance (null id) behaves like `persist` **but** returns a copy and
      leaves your argument transient — so the id you were waiting for never appears on your object.
      `[TRAP]`
1.8.8 Hibernate 6.6 change: merging a **versioned** detached entity whose row no longer exists now
      throws `OptimisticLockException` instead of inserting a new row — for generated `@Id` or
      non-primitive `@Version` only. `[VERSION-TRAP]` `[RESEARCH]`
1.8.9 `remove(e)` — requires a **managed** entity; on a detached one it throws
      `IllegalArgumentException`. The idiom is therefore `remove(find(id))` or
      `remove(getReference(id))`, and the latter avoids the SELECT only if there are no cascades or
      callbacks. `[TRAP]`
1.8.10 Delete ordering surprises: the DELETE runs at flush, *after* pending INSERTs and UPDATEs in
       the action-queue order (§3.5), which is why "delete then insert the same unique key in one
       transaction" fails with a constraint violation. Fix: explicit `flush()` between them.
       `[TRAP]` `[PROVE]`
1.8.11 `SimpleJpaRepository.save` in full: `if (entityInformation.isNew(entity)) { em.persist(entity);
       return entity; } else { return em.merge(entity); }`. Quote it and explain each line.
       `[SOURCE]` `[API]`
1.8.12 The three `isNew` strategies Spring Data uses, in order: **`@Version` + `@Id` inspection**
       (a non-primitive `@Version` that is `null` ⇒ new; else fall back to `@Id` null ⇒ new),
       **`Persistable.isNew()`** if the entity implements it, and a **custom `EntityInformation`**
       via a `JpaRepositoryFactory` subclass. `[SOURCE]` `[RESEARCH]`
1.8.13 Why a **primitive** `@Version` cannot detect newness: JPA treats `0` as a valid first version,
       so `0` is ambiguous between "new" and "version 0". Use `Long`, not `long`. `[PROVE]` `[TRAP]`
1.8.14 **Trap: assigned identifiers.** With a natural or application-generated UUID key, the id is
       non-null on a brand-new entity, so `save()` routes to `merge`, which fires a pointless
       **SELECT before every INSERT**. `[TRAP]`
1.8.15 The `Persistable<UUID>` fix in full: `@Transient boolean isNew = true` plus
       `@PostPersist @PostLoad void markNotNew()`. Ship the `@MappedSuperclass`. `[BUILD]` `[SOURCE]`
1.8.16 **Trap: `save()` on a detached entity built from a web request.** `merge` copies *all* fields,
       so nulls in the request object overwrite good columns — the classic "editing a form nulled out
       three columns" bug. Fix: load the managed entity and copy only the fields the request owns.
       `[TRAP]`
1.8.17 `saveAll` — a loop over `save`, not a batch. It does not enable JDBC batching by itself and it
       holds every entity in the context. `[TRAP]`
1.8.18 `saveAllAndFlush`, `saveAndFlush`, `flush` on the repository — what each adds. `[API]`
1.8.19 The `CrudRepository` / `ListCrudRepository` / `JpaRepository` delete family and their exact
       semantics: `delete(entity)`, `deleteById(id)`, `deleteAllById(ids)`, `deleteAll()`,
       `deleteAll(entities)`, `deleteAllInBatch()`, `deleteAllByIdInBatch(ids)`,
       `deleteInBatch(entities)`. `[API]`
1.8.20 `deleteAll()` loads every entity and removes them one at a time so callbacks, cascades and
       orphan removal fire; `deleteAllInBatch()` issues a single `delete from Order` and skips all of
       it — leaving orphans and stale L1/L2. Know which you called. `[TRAP]` `[SQL]`
1.8.21 `deleteById` on a missing id: silently returns in Spring Data 2.x+, throws
       `EmptyResultDataAccessException` in older versions — verify against 3.5 before asserting.
       `[VERSION-TRAP]` `[RESEARCH]`
1.8.22 `existsById` and `count` as the cheap alternatives to `findById().isPresent()` and
       `findAll().size()`. Show the SQL of each. `[SQL]`

*(22 leaves)*

## §1.9 Declaring an entity — the mapping minimum

1.9.1 The `@Entity` requirements the spec actually imposes: a no-arg constructor (public or
      protected), a non-final class, non-final persistent methods/fields for proxying, an `@Id`, and
      `Serializable` only if you detach it across a wire. `[SOURCE]` `[TRAP]`
1.9.2 `@Entity(name = "...")` names the **entity in JPQL**, not the table. `@Table(name = ...)` names
      the table. Confusing the two is a routine error. `[TRAP]`
1.9.3 `@Table`'s attributes: `name`, `catalog`, `schema`, `uniqueConstraints`, `indexes`. What they
      do and do not do at runtime (nothing — they are DDL-generation metadata only). `[API]` `[TRAP]`
1.9.4 `@Column`'s attributes in full: `name`, `unique`, `nullable`, `insertable`, `updatable`,
      `columnDefinition`, `table`, `length` (**default 255**), `precision`, `scale`. `[API]` `[NUM]`
1.9.5 `insertable = false, updatable = false` as the read-only-column tool — and the trap that
      Hibernate then never writes it even if you set it. `[TRAP]`
1.9.6 **Access type**: field access (annotations on fields) vs property access (annotations on
      getters), determined by where `@Id` sits, overridable with `@Access(AccessType.FIELD|PROPERTY)`
      at class or attribute level. Mixing them silently ignores half your annotations. `[TRAP]`
1.9.7 Why field access is the default recommendation: property access invokes your getters during
      hydration and flush, so any logic in a getter runs at surprising times. `[PROVE]`
1.9.8 `@Transient` (JPA) vs `transient` (Java) vs `@Basic(optional=false)`: three different meanings,
      one of them serialization-only. `[TRAP]`
1.9.9 `@Basic(fetch = FetchType.LAZY)` on a scalar column — only honoured with **bytecode
      enhancement**; without it the annotation is silently ignored. The `@Lob` column you thought was
      lazy is not. `[TRAP]` `[PROVE]`
1.9.10 `@Id` and the legal identifier types: the eight primitives/wrappers, `String`,
       `java.util.Date`, `java.sql.Date`, `BigDecimal`, `BigInteger`, and (3.1) `java.util.UUID`.
       `[SOURCE]` `[RESEARCH]`
1.9.11 Naming strategies: Hibernate's `ImplicitNamingStrategy` and `PhysicalNamingStrategy`, and
       Boot's `SpringImplicitNamingStrategy` +
       `CamelCaseToUnderscoresNamingStrategy` (formerly `SpringPhysicalNamingStrategy`) which
       lower-cases and inserts underscores at camel-case boundaries — so `orderLineItem` becomes
       `order_line_item`. Override with
       `spring.jpa.hibernate.naming.physical-strategy` / `implicit-strategy`. `[PROP]` `[RESEARCH]`
       `[VERSION-TRAP]`
1.9.12 The reserved-word problem: a column named `order` or `user` needs
       `spring.jpa.properties.hibernate.globally_quoted_identifiers=true` or backticks in
       `@Column(name = "\"order\"")`. `[PROP]` `[TRAP]`
1.9.13 `@Enumerated(EnumType.STRING)` vs `ORDINAL` (**the default is `ORDINAL`**). Ordinal breaks
       permanently the first time someone inserts a new constant in the middle of the enum. Always
       `STRING`, or a converter to an explicit code. `[TRAP]` `[NUM]`
1.9.14 `@Temporal` and why it is obsolete: with `java.time` types (JPA 2.2+) Hibernate infers the SQL
       type, and `@Temporal` is only for the legacy `java.util.Date`/`Calendar`. `[VERSION-TRAP]`
1.9.15 `@Lob` for `String`/`byte[]`/`Clob`/`Blob`, the streaming alternatives, and why a `@Lob` on a
       frequently-read entity is a performance bug. `[X-REF 09]`
1.9.16 `@Formula` (Hibernate) — a read-only derived column computed by SQL, evaluated on every load
       and unusable in a `where` clause of a derived query. `[API]` `[TRAP]`
1.9.17 `@Generated` / `@GeneratedColumn` for database-computed values, and `@ColumnDefault`.
       `[API]` `[RESEARCH]`
1.9.18 `@DynamicInsert` and `@DynamicUpdate`: without them Hibernate uses one pre-generated INSERT/
       UPDATE listing **every** column; with them it builds the statement per flush from the changed
       columns. The trade: no statement caching, extra SQL generation per flush. When each wins.
       `[PROVE]` `[SQL]`
1.9.19 `@OptimisticLocking(type = OptimisticLockType.ALL|DIRTY|VERSION|NONE)` as versionless
       optimistic locking, and why `DIRTY` requires `@DynamicUpdate`. `[API]` `[RESEARCH]`
1.9.20 `@Immutable` on an entity or collection — Hibernate skips dirty checking and rejects updates;
       in Hibernate 7 an update query against an immutable entity throws by default.
       `[VERSION-TRAP]`
1.9.21 `@MappedSuperclass` — shares mapped state without being an entity: no table, not queryable,
       cannot be the target of an association. The right home for `id`, `createdAt`, `version`.
       `[API]` `[TRAP]`
1.9.22 `@AttributeOverride` / `@AttributeOverrides` and `@AssociationOverride` for renaming inherited
       or embedded columns. `[API]`
1.9.23 `@SQLRestriction` (6.3+, replacing `@Where`) and `@SQLJoinTableRestriction` (replacing
       `@WhereJoinTable`) — a static SQL predicate glued onto every load of the entity or collection.
       The soft-delete implementation everybody hand-rolled before `@SoftDelete`.
       `[VERSION-TRAP]` `[TRAP]`
1.9.24 `@Filter` / `@FilterDef` and `session.enableFilter(...)` — the *dynamic*, parameterised
       version of `@SQLRestriction`, enabled per session. Note it does **not** apply to `find()` by
       id. `[API]` `[TRAP]`
1.9.25 `@NaturalId` and `@NaturalIdCache`, `session.byNaturalId(...)`,
       `bySimpleNaturalId(...)` — a second, cacheable lookup key. Under-used and interview-worthy.
       `[API]`
1.9.26 `@SoftDelete` (Hibernate 6.4+), its `strategy` (`DELETION`/`ACTIVE`), `columnName`,
       `converter`, and how it rewrites both the DELETE and every SELECT. Compare with the
       `@SQLRestriction` hand-roll. `[VERSION-TRAP]` `[RESEARCH]`
1.9.27 Record entities: **you cannot** — records are final with final fields and no no-arg
       constructor. Records are for projections and DTOs only. `[TRAP]` `[X-REF 04]`
1.9.28 Kotlin entities: `open` classes required, `data class` on an entity is the same mistake as
       Lombok `@Data`, and `allopen`/`no-arg` compiler plugins. `[RESEARCH]`

*(28 leaves)*

## §1.10 Basic types, converters and the Hibernate 6 type system

1.10.1 The spec's basic-type list: primitives and wrappers, `String`, `BigDecimal`, `BigInteger`,
       `byte[]`/`Byte[]`/`char[]`/`Character[]`, `java.util.Date`/`Calendar`, the three
       `java.sql` temporal types, `java.time` (`LocalDate`, `LocalTime`, `LocalDateTime`,
       `OffsetTime`, `OffsetDateTime`, `Instant`, `Duration`, `Year`), enums, `UUID` (3.1), and any
       `Serializable`. `[SOURCE]`
1.10.2 Hibernate 6's rebuilt type system: `JavaType<J>` + `JdbcType` replacing 5.x's monolithic
       `BasicType`/`UserType`, with `BasicTypeRegistry` composing them. Why this rewrite is why
       6.0 was a major version. `[RESEARCH]` `[VERSION-TRAP]`
1.10.3 `@JdbcTypeCode(SqlTypes.JSON)` / `SqlTypes.VARBINARY` / `SqlTypes.UUID` etc. as the modern
       way to pin the JDBC type; `SqlTypes`' constant inventory. `[API]` `[RESEARCH]`
1.10.4 `@JavaType`, `@JdbcType`, `@Type(MyUserType.class)` and `@CompositeType` — the four extension
       hooks, and which one to reach for. `[API]`
1.10.5 `AttributeConverter<X, Y>` + `@Converter(autoApply = true)` + `@Convert(converter = ...)`:
       the portable, spec-blessed way. Signatures `convertToDatabaseColumn` /
       `convertToEntityAttribute`. `[API]` `[BUILD]`
1.10.6 What a converter cannot do: it cannot apply to an `@Id`, a `@Version`, or an association, it
       cannot map one attribute to multiple columns, and **JPQL sees the converted value only in
       Hibernate's own extensions**, so predicates on converted columns are a known sharp edge.
       `[TRAP]` `[RESEARCH]`
1.10.7 The money case done right: `BigDecimal` with `precision`/`scale`, never `double`; and the
       minor-units-as-`long` alternative with a converter. `[X-REF 03]`
1.10.8 The timestamp case done right: store `Instant`/`timestamptz`, never `LocalDateTime` for an
       event time; `hibernate.jdbc.time_zone` and `spring.jpa.properties.hibernate.jdbc.time_zone=UTC`.
       `[PROP]` `[TRAP]`
1.10.9 JSON columns: `@JdbcTypeCode(SqlTypes.JSON)` on a record/POJO field, dialect support, and why
       you cannot index or query into it from JPQL portably. `[RESEARCH]`
1.10.10 Array and collection-of-basic mappings: `@Array(length = ...)`, native array types per
        dialect, and Hibernate 6.6's implicit array-type naming change (`BigIntegerArray` →
        `BigIntegerBigDecimalArray`) which is a **schema-affecting** behaviour change.
        `[VERSION-TRAP]` `[RESEARCH]`
1.10.11 `hibernate.type.preferred_instant_jdbc_type`, `preferred_uuid_jdbc_type`,
        `preferred_duration_jdbc_type` — the settings that silently change your column types across
        minor versions. `[PROP]` `[RESEARCH]`
1.10.12 Hibernate 7's `char`/`Character` → `varchar(1)` change and the native-query
        `java.time`-by-default change, both schema/behaviour affecting. `[VERSION-TRAP]` `[RESEARCH]`

*(12 leaves)*

## §1.11 Identifier generation

1.11.1 The four spec strategies with the SQL each produces: `AUTO`, `IDENTITY`, `SEQUENCE`, `TABLE`,
       plus 3.1's `UUID`. `[API]` `[SQL]`
1.11.2 `GenerationType.AUTO`'s dialect resolution: on PostgreSQL it becomes a **sequence**, on
       MySQL/MariaDB an **identity/auto-increment**, and in Hibernate 6 `AUTO` on a `UUID`-typed id
       becomes UUID generation. Hibernate 5's `AUTO` used to mean a single shared
       `hibernate_sequence`; 6 gives each entity **its own** `<table>_seq`. `[VERSION-TRAP]`
       `[RESEARCH]` `[TRAP]`
1.11.3 `GenerationType.IDENTITY` — the database assigns the key on INSERT, retrieved with
       `getGeneratedKeys()`. Consequence: **the INSERT cannot be deferred**, so it runs at `persist`
       time and **JDBC insert batching is impossible**. `[PROVE]` `[TRAP]`
1.11.4 `GenerationType.SEQUENCE` with `@SequenceGenerator(name, sequenceName, initialValue,
       allocationSize, catalog, schema)`. `allocationSize` **defaults to 50**. `[API]` `[NUM]`
1.11.5 The `allocationSize` contract: Hibernate calls `nextval` once and then hands out
       `allocationSize` identifiers in memory. Therefore the **database sequence's `INCREMENT BY`
       must match `allocationSize`**, or two application instances collide. Show the failing
       Flyway script and the correct one. `[PROVE]` `[TRAP]` `[SQL]`
1.11.6 The optimizers, named with their `hibernate.id.optimizer` values: `none`, `hilo`, `legacy-hilo`,
       `pooled`, `pooled-lo`, `pooled-lotl`. `[API]` `[RESEARCH]`
1.11.7 `pooled` vs `pooled-lo`, mechanically: `pooled` treats the returned value as the **top** of the
       block (hands out `value - allocationSize + 1 .. value`), `pooled-lo` treats it as the
       **bottom** (`value .. value + allocationSize - 1`). `pooled-lo` is the one that interoperates
       with a plain `INSERT` by another application. `[PROVE]` `[NUM]` `[RESEARCH]`
1.11.8 Hibernate's default: **`pooled` when `allocationSize > 1`**, `none` when it is 1. Configure
       globally with `hibernate.id.optimizer.pooled.preferred=pooled-lo`; there is currently **no
       per-generator way** to select `pooled-lo` since `@GenericGenerator`'s deprecation.
       `[NUM]` `[PROP]` `[RESEARCH]` `[TRAP]`
1.11.9 `hilo` and `legacy-hilo` — the historical algorithms (`hi * allocationSize + lo`) and why they
       are database-hostile (nothing else can insert into the table). `[PROVE]`
1.11.10 `SequenceStyleGenerator` — the actual class behind `SEQUENCE`; it falls back to a
        **table-backed** sequence emulation when the dialect has no sequences, which is why "we use
        SEQUENCE" is not the same as "the database has a sequence". `[SOURCE]` `[RESEARCH]`
1.11.11 `GenerationType.TABLE` and `@TableGenerator(name, table, pkColumnName, valueColumnName,
        pkColumnValue, initialValue, allocationSize)` — portable, and a contention hotspot because
        every id acquisition takes a row lock. Effectively never the right answer. `[API]` `[TRAP]`
1.11.12 `GenerationType.UUID` (JPA 3.1) and Hibernate's `@UuidGenerator(style = AUTO|RANDOM|TIME)`.
        `RANDOM` is v4; `TIME` is Hibernate's time-based variant. `[API]` `[RESEARCH]`
1.11.13 Why random UUID primary keys hurt: 16 bytes instead of 8 in every index and every FK, and
        **random insertion order fragments the B-tree / kills insert locality**. The fix is a
        time-ordered UUID (UUIDv7, ULID) so inserts append. `[PROVE]` `[NUM]` `[X-REF 09]`
1.11.14 The single genuine advantage of client-assigned UUIDs: you know the id before the INSERT, so
        you can build a whole object graph and emit events without a round trip.
1.11.15 `@GenericGenerator` — **deprecated in Hibernate 6.5**, replaced by `@IdGeneratorType` +
        a custom annotation, or `@GenericGenerator`'s spec equivalents. Show the modern custom
        generator: an annotation meta-annotated `@IdGeneratorType(MyGenerator.class)` and a
        `BeforeExecutionGenerator`/`IdentifierGenerator` implementation. `[VERSION-TRAP]` `[BUILD]`
        `[RESEARCH]`
1.11.16 `IdentifierGenerator` vs Hibernate 6's `Generator` / `BeforeExecutionGenerator` /
        `OnExecutionGenerator` split, and `@ValueGenerationType` for non-id generated values.
        `[API]` `[RESEARCH]`
1.11.17 Composite identifiers, three ways: `@IdClass`, `@EmbeddedId`, and multiple `@Id` fields
        (legacy). Requirements on the id class: public no-arg constructor, `equals`/`hashCode`,
        `Serializable`. `[API]`
1.11.18 `@MapsId` for a derived identifier — a child whose PK *is* the parent's FK. The best
        `@OneToOne` mapping and the fix for lazy one-to-one. `[API]`
1.11.19 Business/natural keys as primary keys: when they are right (immutable, narrow, never
        reused — e.g. ISO currency code) and why they usually are not (they change; JPA has no
        first-class id-change support).
1.11.20 `hibernate.id.new_generator_mappings` — the Hibernate 5-era switch that everybody's old
        `application.properties` still carries and that no longer exists. `[VERSION-TRAP]`
1.11.21 The identifier-visibility rule: after `persist` the id is populated **immediately** for
        `IDENTITY` and for in-memory sequence allocations, but only **at flush** in the general case.
        Do not build a URL from it before you are sure. `[TRAP]`
1.11.22 Master decision table: which generator for which database/workload, with the batching
        consequence in a column. `[NUM]`

*(22 leaves)*

## §1.12 Embeddables, composite keys and value types

1.12.1 `@Embeddable` / `@Embedded` — a value type with no identity, mapped into the owner's table.
       The vocabulary distinction that JPA under-teaches: **entity = identity + lifecycle**,
       **value type = no identity, lifecycle owned by the parent**. `[PROVE]`
1.12.2 Why embeddables are the single most under-used mapping: `Money`, `Address`, `DateRange`,
       `AuditInfo` as embeddables give you a domain model instead of eleven flat columns.
1.12.3 Column naming inside an embeddable, `@AttributeOverride`, and Hibernate 6.4's
       `@EmbeddedColumnNaming("shipping_%s")` for prefixing without listing every column.
       `[VERSION-TRAP]` `[RESEARCH]`
1.12.4 Embedding the same type twice (billing and shipping address) and why you must override
       columns; the error you get if you don't. `[TRAP]`
1.12.5 Embeddables must be immutable-ish in practice: Hibernate dirty-checks them by value, and a
       shared mutable embeddable instance assigned to two entities writes to both. `[TRAP]`
1.12.6 `@Embeddable` with a record: possible in Hibernate 6 for **read** paths via
       `@EmbeddableInstantiator`, but not the default. Verify before asserting. `[RESEARCH]`
       `[TRAP]`
1.12.7 Hibernate 6.6's **embeddable type inheritance** — polymorphic `@Embeddable` hierarchies with
       an automatic discriminator column stored in the entity mapping. New, incubating, worth
       naming. `[VERSION-TRAP]` `[RESEARCH]`
1.12.8 `@EmbeddedId` in full: the id class is `@Embeddable`, `equals`/`hashCode` are **mandatory**,
       and access is `order.getId().getCustomerId()`. `[API]`
1.12.9 `@IdClass` in full: fields are duplicated on the entity and on the id class, names must match,
       and JPQL refers to the entity fields directly. Compare the two in a table. `[API]`
1.12.10 `@MapsId` inside a composite key for a `@ManyToOne` that is part of the PK — the correct
        join-table-as-entity mapping (e.g. `OrderLine(orderId, productId)`). `[BUILD]`
1.12.11 `@ElementCollection` + `@CollectionTable` + `@Column`/`@AttributeOverride` — a collection of
        basics or embeddables with **no entity identity**. Mechanism: Hibernate deletes all rows and
        re-inserts them on any change unless there is an `@OrderColumn`. `[PROVE]` `[SQL]` `[TRAP]`
1.12.12 `@OrderColumn` vs `@OrderBy` on a collection: the first persists position in a column (and
        makes middle-insertions rewrite the tail), the second sorts at query time. `[TRAP]` `[SQL]`
1.12.13 When `@ElementCollection` is right (tags, phone numbers, small fixed sets) and when it must
        become an entity (anything you need to query, reference, or paginate).
1.12.14 `@MapKeyColumn`, `@MapKeyEnumerated`, `@MapKeyJoinColumn`, `@MapKeyClass` for `Map`-valued
        collections. `[API]`

*(14 leaves)*

## §1.13 Associations

1.13.1 The four cardinalities and the SQL each implies: `@ManyToOne` (FK on this table),
       `@OneToMany` (FK on the other table, or a join table), `@OneToOne` (FK either side, or shared
       PK), `@ManyToMany` (join table). `[SQL]`
1.13.2 **Owning side vs inverse side**, precisely: the owning side is the one that holds the foreign
       key and is the *only* side Hibernate reads when generating SQL. `mappedBy` marks the inverse
       side. `[PROVE]`
1.13.3 The most common association bug in existence: adding to the inverse collection only, and
       nothing being persisted, because the owning `@ManyToOne` was never set. `[TRAP]`
1.13.4 The `addX`/`removeX` helper-method idiom that keeps both sides consistent, and why you should
       make the collection field `private` with no setter. `[BUILD]`
1.13.5 `@JoinColumn`'s attributes: `name`, `referencedColumnName`, `nullable`, `insertable`,
       `updatable`, `foreignKey`, `table`, `unique`. `[API]`
1.13.6 `@JoinColumns` for composite FKs, and `@ForeignKey(ConstraintMode.NO_CONSTRAINT)` for
       suppressing DDL constraint generation. `[API]`
1.13.7 `@ManyToOne`'s attributes: `targetEntity`, `cascade`, `fetch` (**default EAGER**), `optional`
       (**default true**). `optional = false` is what makes an inner join possible and lazy
       one-to-one proxyable. `[API]` `[NUM]`
1.13.8 **A unidirectional `@OneToMany` without `@JoinColumn` silently creates a join table.** Show
       the generated DDL. Fix: `@JoinColumn` on the `@OneToMany`, or better, make it bidirectional.
       `[TRAP]` `[SQL]`
1.13.9 Why a unidirectional `@OneToMany` with `@JoinColumn` still performs badly: Hibernate inserts
       the children with a null FK and then issues an UPDATE per child to set it. Show the three
       statements. `[PROVE]` `[SQL]` `[TRAP]`
1.13.10 The `@OneToMany(mappedBy=...)` + `@ManyToOne` bidirectional pair as the default correct
        mapping, and the "don't map the collection at all" alternative when the child count is
        unbounded. `[PROVE]`
1.13.11 `@OneToOne` on both sides: owning side with `@JoinColumn`, inverse with `mappedBy`. And the
        three variants: FK-based, shared-PK (`@MapsId`), and join-table.
1.13.12 **The `@OneToOne` lazy caveat**, mechanically: on the *inverse* side of an **optional**
        one-to-one Hibernate must know whether the row exists to decide between `null` and a proxy,
        so it issues a SELECT anyway — the `fetch = LAZY` is ineffective. Three fixes:
        `optional = false`, `@MapsId` (shared PK), or model it as `@ManyToOne`. Bytecode enhancement
        with `@LazyToOne(NO_PROXY)` was the fourth and is **removed in Hibernate 7**.
        `[PROVE]` `[TRAP]` `[VERSION-TRAP]`
1.13.13 `@ManyToMany` mechanics: `@JoinTable(name, joinColumns, inverseJoinColumns,
        uniqueConstraints)`, and the **delete-all-then-reinsert** behaviour on the owning side when
        the collection is a `List`. `[SQL]` `[TRAP]`
1.13.14 Why you should nearly always replace `@ManyToMany` with two `@OneToMany`s and an explicit
        join entity: you get to add columns (`addedAt`, `quantity`), you get id-based updates instead
        of delete-all, and you can paginate. `[PROVE]`
1.13.15 `@ManyToMany` with `Set` vs `List`: `Set` gives targeted delete/insert, `List` gives
        delete-all-reinsert. Measure it. `[NUM]`
1.13.16 Self-referencing associations (a category tree, a manager hierarchy) and the recursive-query
        problem they create; `@ManyToOne` to self plus a CTE query (§1.19). `[X-REF 09]`
1.13.17 `@Any` / `@AnyDiscriminator` / `@AnyKeyJavaClass` — Hibernate's polymorphic association to
        *unrelated* entity types. Rare, but the answer to "how do I model a comment on any entity".
        `[API]` `[RESEARCH]`
1.13.18 Association direction is a **modelling decision, not a database one**: the FK is the same
        either way. Choose direction by which side you navigate from. `[PROVE]`

*(18 leaves)*

## §1.14 Collections — the persistent collection contract

1.14.1 The six collection mappings JPA supports: `List`, `Set`, `SortedSet`, `Map`, `SortedMap`,
       `Collection`. `[API]`
1.14.2 Hibernate's replacement wrappers, by name: `PersistentBag` (unordered `List`),
       `PersistentList` (`List` with `@OrderColumn`), `PersistentSet`, `PersistentSortedSet`,
       `PersistentMap`, `PersistentSortedMap`, `PersistentIdentifierBag` (`@CollectionId`).
       Every mapped collection field is replaced by one of these at load time. `[API]` `[SOURCE]`
1.14.3 **Bag vs list vs set**, and why the distinction matters: a bag has no index and no uniqueness,
       so Hibernate cannot address a single element and must delete-all-reinsert on change; a set can
       target individual rows; a list with `@OrderColumn` can too, at the cost of rewriting indices.
       `[PROVE]` `[SQL]`
1.14.4 The reason `MultipleBagFetchException` exists at all: two bags joined in one query cannot be
       disambiguated into the right parent buckets. This is the *mechanism*, not just the symptom.
       `[PROVE]`
1.14.5 `Set` requires working `equals`/`hashCode` on the element, which drags in §2.6 — and a
       `HashSet` of entities with generated ids is the exact bug §2.6 describes. `[X-REF 02]`
1.14.6 Initialising collection fields at declaration (`= new ArrayList<>()`) — required, because
       Hibernate replaces the *instance* on load but not on a transient entity, and a null collection
       NPEs your helper method. `[TRAP]`
1.14.7 **Never replace a managed collection instance** (`order.setItems(new ArrayList<>(...))`) —
       Hibernate loses the `PersistentBag` wrapper and issues a full delete-and-reinsert, or throws
       `HibernateException: A collection with cascade="all-delete-orphan" was no longer referenced`.
       Mutate in place instead. `[TRAP]` `[DIAG]`
1.14.8 `@OrderBy("createdAt desc")` vs `@SQLOrder` (Hibernate 6.5+, replacing Hibernate's
       `@OrderBy`) vs `@OrderColumn` vs `SortedSet` + `@SortComparator`/`@SortNatural`. Four
       distinct mechanisms, one confusing name overlap. `[VERSION-TRAP]` `[TRAP]`
1.14.9 `@CollectionId` with `@GeneratedValue` — an id-bag, giving a bag targeted updates. Obscure but
       the correct answer when you must keep a `List` and cannot afford delete-all. `[RESEARCH]`
1.14.10 Collection-level `@BatchSize`, `@Fetch(FetchMode.SUBSELECT)` and `@Cache` — the three
        annotations you can put on a collection and their distinct effects.
1.14.11 The empty-collection question: does accessing an initialised-but-empty lazy collection hit
        the database? Yes, once, to learn it is empty; Hibernate then caches emptiness in the
        wrapper. `[PROVE]`
1.14.12 `collection.size()` on a lazy bag loads the whole collection; on a `PersistentSet` with
        `@LazyCollection(EXTRA)` (removed in 7) it issued a `count`. In 6.6 the portable answer is a
        derived `countBy` repository method. `[TRAP]` `[VERSION-TRAP]`
1.14.13 `collection.contains(x)` triggers a full load for the same reason. Prefer an `existsBy`
        query. `[TRAP]`

*(13 leaves)*

## §1.15 Inheritance mapping

1.15.1 The three strategies and their DDL: `InheritanceType.SINGLE_TABLE` (default), `JOINED`,
       `TABLE_PER_CLASS`. Plus `@MappedSuperclass` as the non-polymorphic fourth option.
       `[API]` `[SQL]`
1.15.2 `SINGLE_TABLE`: one table, a `@DiscriminatorColumn(name = "dtype", discriminatorType =
       STRING)` (**default column name `DTYPE`**), `@DiscriminatorValue` per subclass. Fastest
       polymorphic query — no joins, no unions. `[NUM]` `[SQL]`
1.15.3 `SINGLE_TABLE`'s cost, stated as a hard constraint: **subclass columns must be nullable**, so
       you lose `NOT NULL` on every field that is not on the root. This is a data-integrity
       trade, not a performance one. `[PROVE]` `[TRAP]`
1.15.4 The `@Check` constraint workaround for §1.15.3 and why almost nobody does it. `[RESEARCH]`
1.15.5 Hibernate 6.6 change: `@Table` on a `SINGLE_TABLE` subclass now raises a mapping exception
       instead of being ignored. `[VERSION-TRAP]` `[RESEARCH]`
1.15.6 `@DiscriminatorFormula` and `@DiscriminatorOptions(force = true)` — a discriminator derived by
       SQL, and forcing the discriminator predicate onto every query even when it looks redundant.
       `[API]`
1.15.7 `JOINED`: root table plus one table per subclass, joined by PK. Preserves `NOT NULL` and
       normalises; costs a join per level on read and an extra INSERT per level on write. `[SQL]`
1.15.8 `JOINED`'s polymorphic query cost: an `n`-subclass hierarchy produces an `n`-way `LEFT JOIN`
       when you query the root. Show the SQL for a 4-subclass hierarchy. `[SQL]` `[PROVE]`
1.15.9 `TABLE_PER_CLASS`: one independent table per concrete class, no shared table. Polymorphic
       queries become a `UNION ALL`, and **`GenerationType.IDENTITY` is impossible** because ids must
       be unique across the union. `[PROVE]` `[TRAP]` `[SQL]`
1.15.10 `@MappedSuperclass`: shared columns, no polymorphism, no polymorphic query, cannot be an
        association target. The right choice for `BaseEntity { id, version, createdAt }`. `[TRAP]`
1.15.11 The master comparison table: read cost, write cost, polymorphic query cost, `NOT NULL`
        support, FK support to the hierarchy, id-generation support, schema evolution cost, and
        recommendation. `[NUM]`
1.15.12 The decision rule: `SINGLE_TABLE` by default; `JOINED` when subclasses have many mandatory
        columns or the hierarchy is deep and wide; `TABLE_PER_CLASS` essentially never;
        `@MappedSuperclass` when you never query polymorphically. `[PROVE]`
1.15.13 `@Polymorphism(type = EXPLICIT)` (deprecated/removed in 7) and the `hibernate.` equivalent of
        making a supertype non-queryable. `[VERSION-TRAP]` `[RESEARCH]`
1.15.14 Polymorphic queries in JPQL: `select o from Order o where type(o) = ExpressJob`,
        `treat(o as ExpressJob).slaMinutes`, and `o.class` as the Hibernate shorthand.
        `[API]` `[SQL]`
1.15.15 The proxy/`instanceof` problem in a hierarchy: a lazy `@ManyToOne` to the root type is a proxy
        of the *root*, so `instanceof Subclass` is **false** even when the row is a subclass. Fixes:
        `Hibernate.unproxy`, eager fetch, `treat()`, or the fact that Hibernate 6.2+ can sometimes
        resolve the concrete type from the discriminator. `[TRAP]` `[PROVE]` `[RESEARCH]`
1.15.16 The design alternative interviewers want to hear: composition plus a `type` enum column
        instead of a class hierarchy, when the "subclasses" differ only in data. `[PROVE]`

*(16 leaves)*

## §1.16 Cascade and orphan removal

1.16.1 The seven `CascadeType` values: `PERSIST`, `MERGE`, `REMOVE`, `REFRESH`, `DETACH`, `ALL`, and
       (Hibernate 5, **removed in 7**) `SAVE_UPDATE` / `DELETE` / `REPLICATE` / `LOCK`.
       `[API]` `[VERSION-TRAP]`
1.16.2 Cascade is a **JPA-operation propagation rule**, not a database `ON DELETE CASCADE`. Both
       exist, they are independent, and mixing them produces surprises. `[TRAP]` `[X-REF 09]`
1.16.3 Cascade travels along the *mapped* association from the side it is declared on. Declaring it
       on the `@ManyToOne` (child → parent) means removing a child removes the parent — almost always
       a bug. `[TRAP]`
1.16.4 `CascadeType.ALL` on a `@ManyToOne` as a named anti-pattern; the review rule: cascade goes on
       the aggregate root's collection, never on the child's back-reference.
1.16.5 `orphanRemoval = true` versus `CascadeType.REMOVE`: the first deletes a child **removed from
       the collection**, the second deletes children when the **parent** is deleted. Different
       triggers, commonly conflated. `[PROVE]` `[TRAP]`
1.16.6 What orphan removal costs: Hibernate must load the collection to know what left it, so
       `orphanRemoval` forces a collection initialisation on flush. `[PROVE]`
1.16.7 The aggregate-root discipline from DDD as the actual answer to "where do I put cascade": one
       entity owns the lifecycle of its parts; parts have no independent repository. `[X-REF 22]`
1.16.8 `@OnDelete(action = OnDeleteAction.CASCADE)` — Hibernate emitting a database-level
       `ON DELETE CASCADE` in the DDL, which then makes the JPA-level cascade unnecessary *and* the
       L1/L2 caches wrong. `[API]` `[TRAP]`
1.16.9 The `ConstraintViolationException` on parent delete when there is neither JPA cascade nor DB
       cascade — read the trace and name the fix. `[DIAG]`
1.16.10 Cascade on `merge` reachability: `merge` cascades into detached children and can silently
        insert duplicates when a child has an assigned id it thinks is new. `[TRAP]`
1.16.11 `CascadeType.PERSIST` + `@Id` derived by `@MapsId`: Hibernate 7 **removed** the implicit
        `cascade = PERSIST` that `@MapsId` used to add, so existing code that relied on it breaks.
        `[VERSION-TRAP]` `[RESEARCH]`
1.16.12 `TransientObjectException` / `object references an unsaved transient instance` — the exact
        message, what it means (a reachable transient entity with no `PERSIST` cascade), and the two
        fixes. `[DIAG]` `[TRAP]`

*(12 leaves)*

## §1.17 Fetch types, proxies and lazy loading

1.17.1 The default fetch table, kept from the current guide: `@ManyToOne` **EAGER**, `@OneToOne`
       **EAGER**, `@OneToMany` LAZY, `@ManyToMany` LAZY, `@Basic` EAGER, `@ElementCollection` LAZY.
       `[NUM]` `[SOURCE]`
1.17.2 Why the `*ToOne` eager defaults are a spec mistake: they make every load of an entity load its
       whole upstream graph, they are invisible in the code that triggers them, and they cannot be
       overridden per query without an entity graph. The rule: **set every association to
       `fetch = LAZY` explicitly**. `[PROVE]` `[TRAP]`
1.17.3 `FetchType` is a *default*, not a constraint: a `JOIN FETCH` or entity graph overrides LAZY,
       and (in Hibernate) nothing overrides EAGER downward — EAGER is a promise you cannot revoke
       per query. This asymmetry is the whole argument for LAZY-everywhere. `[PROVE]` `[TRAP]`
1.17.4 The lazy `*ToOne` mechanism: the field holds a **`HibernateProxy`** — a ByteBuddy-generated
       subclass whose only initialised state is the identifier, delegating every other call to a
       `LazyInitializer`. `[SOURCE]` `[API]`
1.17.5 The lazy collection mechanism: the field holds a `PersistentBag`/`PersistentSet` whose
       `initialized` flag is false; the first method call runs `session.initializeCollection(...)`.
1.17.6 `Hibernate.initialize(x)`, `Hibernate.isInitialized(x)`, `Hibernate.unproxy(x)`,
       `Hibernate.getClass(x)`, `Hibernate.isPropertyInitialized(x, "name")`. `[API]`
1.17.7 `LazyInitializationException: could not initialize proxy [Order#42] - no Session` — the exact
       message, the three lines of the trace that matter, and what the reader should conclude.
       `[DIAG]` `[TRAP]`
1.17.8 The ranked fixes, preserved from the current guide and expanded: (1) fetch what you need
       inside the transaction — `JOIN FETCH` or `@EntityGraph`; (2) **map to a DTO inside the
       transactional method** — the design fix; (3) `Hibernate.initialize` / touch it inside the tx;
       (4) widen the transaction — usually wrong; (5) `spring.jpa.open-in-view=true` — makes the
       symptom vanish and creates worse problems (§2.12). `[SOURCE]` `[PROVE]`
1.17.9 **Trap:** `getReference()`/`getOne()`/`getReferenceById()` returns a proxy without a SELECT.
       `proxy.getId()` is safe; anything else triggers a load, and a missing row throws
       `EntityNotFoundException` at a random later line. `[TRAP]`
1.17.10 **Trap:** `proxy.getClass()` is `Order$HibernateProxy$xyz`, so `getClass() == other.getClass()`
        in `equals` fails, `instanceof Subclass` fails, `switch` pattern matching on sealed types
        fails, and Jackson serialises a `handler` field. Fixes: `Hibernate.getClass`,
        `Hibernate.unproxy`, `instanceof` with a pattern, and Jackson's
        `Hibernate6Module`/`@JsonIgnoreProperties("hibernateLazyInitializer","handler")`.
        `[TRAP]` `[X-REF 04]`
1.17.11 The legitimate use of `getReference`: setting a `@ManyToOne` FK without loading the parent —
        `order.setCustomer(em.getReference(Customer.class, id))` produces one INSERT and zero
        SELECTs. `[PROVE]` `[SQL]`
1.17.12 `@Fetch(FetchMode.JOIN | SELECT | SUBSELECT)` — Hibernate's *global*, per-mapping fetch
        strategy, distinct from `FetchType`. `JOIN` applies to `find()` but is **ignored by JPQL**,
        which is the single most confusing interaction in the fetching chapter. `[TRAP]` `[PROVE]`
        `[RESEARCH]`
1.17.13 `@FetchProfile` / `@FetchProfiles` and `session.enableFetchProfile("with-items")` — named
        fetch plans predating entity graphs; still the only way to change a `find()`'s plan without
        a query. `[API]`
1.17.14 `@LazyGroup("details")` with bytecode enhancement — grouping lazy basic attributes so one
        touch loads the group rather than the column. `[API]` `[RESEARCH]`
1.17.15 `@BatchSize(size = n)` on an entity or a collection, and the global
        `hibernate.default_batch_fetch_size` — turn N proxy loads into `ceil(N/n)` `IN (...)`
        queries. `[PROP]` `[NUM]`
1.17.16 `hibernate.batch_fetch_style` (`LEGACY` / `PADDED` / `DYNAMIC`) and why it matters for
        statement-cache hit rate: `PADDED` rounds the `IN` list to a power of two so the SQL string
        repeats. Verify whether the setting still exists in 6.6. `[PROP]` `[RESEARCH]`
        `[VERSION-TRAP]`
1.17.17 The interview one-liner: "lazy means *a proxy plus a session*; the exception is always one of
        those two missing."

*(17 leaves)*

## §1.18 Lifecycle callbacks and entity listeners

1.18.1 The seven callback annotations and exactly when each fires: `@PrePersist`, `@PostPersist`,
       `@PreUpdate`, `@PostUpdate`, `@PreRemove`, `@PostRemove`, `@PostLoad`. `[API]` `[FLOW]`
1.18.2 The precise firing points: `@PrePersist` at `persist()` (not at flush), `@PostPersist` after
       the INSERT, `@PreUpdate` **only if the entity is actually dirty**, `@PostLoad` after
       hydration and after the constructor. `[PROVE]` `[TRAP]`
1.18.3 **Trap:** `@PreUpdate` does not fire when nothing changed, and does not fire for a bulk
       `@Modifying` update at all. An audit column maintained only by `@PreUpdate` will silently
       diverge. `[TRAP]`
1.18.4 What you may **not** do inside a callback: call `EntityManager` operations, modify other
       entities, or flush. The spec forbids it; Hibernate mostly tolerates it and then fails
       unpredictably. `[TRAP]` `[SOURCE]`
1.18.5 `@EntityListeners(MyListener.class)` on the entity, and `<entity-listeners>` /
       `@ExcludeDefaultListeners` / `@ExcludeSuperclassListeners`. `[API]`
1.18.6 Making a listener Spring-managed: `SpringBeanContainer` wiring so Hibernate resolves listener
       beans from the context; otherwise `new`-ed with no dependencies. `[TRAP]` `[RESEARCH]`
1.18.7 Hibernate's *event* system as the more powerful alternative:
       `PreInsertEventListener`, `PostInsertEventListener`, `PreUpdateEventListener`,
       `PostUpdateEventListener`, `PreDeleteEventListener`, `PostDeleteEventListener`,
       `PostLoadEventListener`, `FlushEventListener`, registered via an
       `Integrator`/`EventListenerRegistry`. Full mechanism in §3.6. `[API]`
1.18.8 Domain events done properly instead of callbacks: `AbstractAggregateRoot`,
       `registerEvent(...)`, and `@DomainEvents` + `@AfterDomainEventPublication` in Spring Data —
       events published when the repository `save` runs. `[API]` `[RESEARCH]`
1.18.9 Why callbacks are the wrong place to publish an event to Kafka: they run inside the flush, so
       a rollback after them leaves you having published a lie. The outbox pattern is the fix.
       `[PROVE]` `[X-REF 14]`
1.18.10 `@PostLoad` as the legitimate place to compute a `@Transient` derived field.
1.18.11 Ordering between callbacks, entity listeners, default listeners and superclass listeners:
        listeners run before the entity's own callback, superclass before subclass, default before
        entity-specific. `[FLOW]` `[SOURCE]`

*(11 leaves)*

## §1.19 JPQL and HQL

1.19.1 JPQL is a query language over the **entity model**, not the tables: you name entities and
       attributes, and joins follow mapped associations. State the consequence — a JPQL query is
       invalid if the mapping is wrong, and it is validated at startup. `[PROVE]`
1.19.2 The clause inventory: `select`, `from`, `join`/`left join`/`join fetch`, `where`,
       `group by`, `having`, `order by`, and (Hibernate) `with` for CTEs. `[API]`
1.19.3 Implicit joins (`o.customer.name`) vs explicit joins (`join o.customer c`): the implicit form
       generates an **inner join** and silently drops rows with a null FK. This is a correctness bug,
       not a style issue. `[TRAP]` `[PROVE]` `[SQL]`
1.19.4 `join fetch` vs `join`: the first adds the association to the select list and initialises it,
       the second only makes it available to predicates. Using `join` and then navigating still
       gives N+1. `[TRAP]` `[PROVE]`
1.19.5 `left join fetch` for optional associations, and why plain `join fetch` on a nullable
       association loses parents.
1.19.6 The parameter forms: `?1` positional, `:name` named. Named is the only defensible choice.
       `Query.setParameter` overloads for temporal types. `[API]`
1.19.7 **JPQL cannot be built by string concatenation of user input** any more than SQL can — a
       parameter is a parameter. But note the one genuine JPQL injection surface: `order by` clauses
       and `JpaSort.unsafe`. `[TRAP]` `[X-REF 13]`
1.19.8 Constructor expressions: `select new com.quizstakes.OrderSummary(o.id, c.name) from Order o
       join o.customer c` — the DTO projection that loads no entities. Requires an FQN and a matching
       constructor. `[API]`
1.19.9 Aggregate functions: `count`, `count(distinct)`, `sum`, `avg`, `min`, `max`, and the
       `count(*)` vs `count(o)` distinction in JPQL.
1.19.10 The string, arithmetic and datetime function inventory: `concat`, `substring`, `trim`,
        `lower`, `upper`, `length`, `locate`, `abs`, `sqrt`, `mod`, `size`, `index`,
        `current_date`, `current_time`, `current_timestamp`, `coalesce`, `nullif`, `case`, `type`,
        `treat`, `function('native_fn', args)`. `[API]`
1.19.11 JPA 3.1's numeric additions: **`CEILING`, `EXP`, `FLOOR`, `LN`, `POWER`, `ROUND`, `SIGN`**,
        plus `LOCAL DATE` / `LOCAL TIME` / `LOCAL DATETIME`. `[API]` `[RESEARCH]`
1.19.12 Subqueries: `exists`, `not exists`, `in`, `all`, `any`/`some`, correlated subqueries, and the
        `member of` collection predicate. `[API]`
1.19.13 Bulk `update` and `delete` in JPQL: no joins allowed (except in Hibernate), no cascades, no
        version increment unless you write it, and the L1 cache goes stale. Detailed in §2.10.
        `[TRAP]`
1.19.14 HQL's superset over JPQL, named: `insert ... select`, set operations `union` / `union all` /
        `intersect` / `except`, **CTEs** (`with x as (...)`, including `materialized` hints and
        `recursive`), **window functions** (`over (partition by ... order by ... rows between ...)`),
        `filter` clauses, tuple/array constructors, `cast`, `format`, `str`, ordinal/named
        function registry, `limit`/`offset`/`fetch first` in the query text, and lateral joins.
        `[VERSION-TRAP]` `[RESEARCH]` `[API]`
1.19.15 Window functions in Hibernate 6: `row_number()`, `rank()`, `dense_rank()`, `lag`, `lead`,
        `first_value`, `last_value`, `nth_value`, `ntile`, `percent_rank`, `cume_dist`, and how
        `over` is written in HQL. The "top N per group" query without native SQL. `[RESEARCH]`
        `[SQL]`
1.19.16 CTE support arrived in Hibernate **6.2**; set operations in **6.0**; window functions in
        **6.0**. Before that all three required native SQL. `[VERSION-TRAP]` `[RESEARCH]`
1.19.17 Named queries: `@NamedQuery(name, query, lockMode, hints)`, `@NamedQueries`,
        `@NamedNativeQuery`, and `orm.xml`'s `<named-query>`. Named queries are **parsed at
        startup**, so a typo fails the boot — the strongest reason to use them. `[API]` `[PROVE]`
1.19.18 The Spring Data naming convention that makes named queries automatic:
        `@NamedQuery(name = "Order.findByStatus")` is picked up by
        `OrderRepository.findByStatus(...)` with no `@Query`. `[TRAP]`
1.19.19 Query hints: `setHint("org.hibernate.readOnly", true)`, `"org.hibernate.cacheable"`,
        `"org.hibernate.fetchSize"`, `"org.hibernate.comment"`, `jakarta.persistence.query.timeout`,
        `jakarta.persistence.lock.timeout`, `jakarta.persistence.fetchgraph`, `loadgraph`,
        `cache.retrieveMode`, `cache.storeMode`. `[API]` `[PROP]`
1.19.20 `setFirstResult` / `setMaxResults` and the SQL they generate per dialect
        (`LIMIT/OFFSET`, `FETCH FIRST ... ROWS ONLY`, `ROW_NUMBER()` windowing on old SQL Server).
        `[SQL]`
1.19.21 Hibernate 7 change: "queries with implicit select and no explicit result type are no longer
        accepted", and the raw-`Query` overload deprecation. Old `createQuery("from Order")` code
        breaks. `[VERSION-TRAP]` `[RESEARCH]`
1.19.22 `hibernate.query.plan_cache_max_size` (**default 2048**) and
        `hibernate.query.plan_parameter_metadata_max_size` (**default 128**) — the query-plan cache,
        and why dynamically-built query strings blow it out. Mechanism in §3.13. `[PROP]` `[NUM]`
        `[RESEARCH]`

*(22 leaves)*

## §1.20 The Criteria API and the static metamodel

1.20.1 Why the Criteria API exists: type-safe, composable, dynamically-built queries — the answer to
       "seven optional filters" without string concatenation. `[PROVE]`
1.20.2 The object model: `CriteriaBuilder` → `CriteriaQuery<T>` → `Root<T>` → `Join`/`Fetch` →
       `Predicate` → `Order` → `em.createQuery(cq)`. `[API]` `[FLOW]`
1.20.3 `CriteriaBuilder`'s surface, grouped: comparison (`equal`, `notEqual`, `gt`, `ge`, `lt`, `le`,
       `between`, `like`, `in`, `isNull`, `isNotNull`, `isEmpty`, `isMember`), boolean (`and`, `or`,
       `not`, `conjunction`, `disjunction`), aggregate (`count`, `countDistinct`, `sum`, `avg`,
       `min`, `max`, `greatest`, `least`), construction (`construct`, `tuple`, `array`,
       `selectCase`, `coalesce`, `nullif`, `function`), and the 3.1 numeric additions. `[API]`
1.20.4 `Root.get("status")` (string, unsafe) versus `Root.get(Order_.status)` (metamodel, safe).
       The `hibernate-jpamodelgen` annotation processor generates `Order_`. `[TRAP]`
1.20.5 `Metamodel`, `EntityType<T>`, `SingularAttribute`, `PluralAttribute`, `ListAttribute`,
       `SetAttribute`, `MapAttribute` — the runtime metamodel behind the generated classes. `[API]`
1.20.6 `root.join("customer", JoinType.LEFT)` vs `root.fetch("items", JoinType.LEFT)` — the same
       `join` vs `join fetch` distinction as JPQL, and the cast dance
       `(Join<X,Y>) root.fetch(...)` needed when you want both. `[TRAP]`
1.20.7 `CriteriaQuery.distinct(true)` and why it is needed with a collection fetch, plus what it does
       to the SQL (`select distinct`) versus what Hibernate 6 does in memory. `[VERSION-TRAP]`
       `[RESEARCH]`
1.20.8 `CriteriaUpdate<T>` and `CriteriaDelete<T>` (JPA 2.1) for typed bulk operations. `[API]`
1.20.9 `Subquery<T>`, `cb.exists(subquery)`, and correlation via `subquery.correlate(root)`. `[API]`
1.20.10 `Tuple` and `CompoundSelection` for multi-column results, versus `cb.construct(Dto.class,
        ...)` for a DTO. `[API]`
1.20.11 Why Criteria is verbose and where that verbosity is worth it: dynamic search endpoints, and
        nowhere else. For static queries `@Query` is shorter and reviewable. `[PROVE]`
1.20.12 Hibernate 6's `HibernateCriteriaBuilder` (`JpaCriteriaQuery`, `JpaRoot`, `JpaExpression`,
        `JpaPredicate`) extensions: `ilike`, set operations, CTEs, window functions from Criteria,
        `cast`. `[API]` `[RESEARCH]`
1.20.13 Hibernate 6.6 change: `Expression.as()` now does **unsafe typecasting only**; use
        `JpaExpression.cast()` for real conversion. Code that relied on `as()` converting is now
        wrong. `[VERSION-TRAP]` `[RESEARCH]`
1.20.14 The old `org.hibernate.Criteria` API (`session.createCriteria(...)`, `Restrictions.eq`,
        `Example`) — **removed in Hibernate 6**. Any tutorial using it is pre-2022. `[VERSION-TRAP]`
1.20.15 Criteria queries and the query-plan cache: each distinct predicate shape produces a distinct
        plan, so a dynamic builder can thrash the plan cache. `[PROVE]` `[X-REF 09]`
1.20.16 JPA 3.2's generified Criteria/`EntityGraph` API and why it is a source-breaking change.
        `[VERSION-TRAP]` `[RESEARCH]`

*(16 leaves)*

## §1.21 Native queries, stored procedures and result mapping

1.21.1 `createNativeQuery(sql)` (untyped `Object[]`), `createNativeQuery(sql, Class)` (entity
       mapping), `createNativeQuery(sql, "mappingName")` (`@SqlResultSetMapping`). `[API]`
1.21.2 `@SqlResultSetMapping` with `@EntityResult` + `@FieldResult`, `@ConstructorResult` +
       `@ColumnResult`, and `@ColumnResult(type = ...)`. `[API]` `[BUILD]`
1.21.3 A native query returning entities makes them **managed** and dirty-checked, which is usually
       not what a reporting query wants; a native query returning columns returns detached data.
       `[PROVE]`
1.21.4 The auto-flush hole restated: native queries do not auto-flush.
       `addSynchronizedEntityClass` / `addSynchronizedQuerySpace` /
       `addSynchronizedEntityName` are the fix. `[TRAP]` `[API]`
1.21.5 Native queries are **not validated at startup** — `nativeQuery = true` moves the failure from
       boot time to request time. This is the strongest argument for keeping them few and tested.
       `[TRAP]` `[PROVE]`
1.21.6 Pagination with a native query in Spring Data requires `countQuery`, and `Sort` is not
       applied — you must interpolate order yourself (or use `#{#sort}` / a `QueryRewriter`).
       `[TRAP]` `[RESEARCH]`
1.21.7 `@NativeQuery` (Spring Data 3.4+) as the dedicated annotation replacing
       `@Query(nativeQuery = true)`, with `countQuery`, `resultSetMapping`, `queryRewriter`.
       `[VERSION-TRAP]` `[RESEARCH]` `[API]`
1.21.8 Returning `Map<String,Object>` or `Tuple` from a native query in Spring Data 3.x. `[API]`
       `[RESEARCH]`
1.21.9 Stored procedures: `@NamedStoredProcedureQuery`, `@StoredProcedureParameter(mode = IN|OUT|
       INOUT|REF_CURSOR)`, `StoredProcedureQuery`, `em.createStoredProcedureQuery`, and Spring
       Data's `@Procedure`. `[API]`
1.21.10 `Session.doWork(Connection -> ...)` / `doReturningWork` — dropping to raw JDBC on the same
        transaction and connection. The escape hatch for `COPY`, `LOAD DATA`, and vendor features.
        `[API]`
1.21.11 Mixing `JdbcTemplate`/`JdbcClient` with JPA in the same transaction: it works because both
        use `DataSourceUtils` to get the transaction-bound connection — but JPA's pending changes are
        invisible to it until you flush. `[PROVE]` `[TRAP]` `[X-REF 07]`
1.21.12 When to reach for native SQL, as a checklist: window functions on an old Hibernate, vendor
        hints, `INSERT ... ON CONFLICT`, bulk `COPY`, recursive CTEs pre-6.2, `EXPLAIN`, and
        reporting aggregates over many tables.

*(12 leaves)*

## §1.22 Spring Data JPA repositories — the basics

1.22.1 The interface hierarchy, exactly: `Repository<T,ID>` (marker) → `CrudRepository` →
       `ListCrudRepository` (3.0+) → `PagingAndSortingRepository` / `ListPagingAndSortingRepository`
       → `JpaRepository` → your interface. Plus `QueryByExampleExecutor`,
       `JpaSpecificationExecutor`, `QuerydslPredicateExecutor`, `RevisionRepository`. `[API]`
       `[VERSION-TRAP]`
1.22.2 The Spring Data 3.0 split that trips people: `PagingAndSortingRepository` **no longer
       extends** `CrudRepository`. Extending only the former loses `save`. `[VERSION-TRAP]` `[TRAP]`
1.22.3 `CrudRepository`'s methods: `save`, `saveAll`, `findById`, `existsById`, `findAll`,
       `findAllById`, `count`, `deleteById`, `delete`, `deleteAllById`, `deleteAll(Iterable)`,
       `deleteAll()`. `[API]`
1.22.4 `JpaRepository`'s additions: `findAll()` returning `List`, `flush`, `saveAndFlush`,
       `saveAllAndFlush`, `deleteAllInBatch`, `deleteAllByIdInBatch`, `deleteInBatch`,
       `getReferenceById`, `findAll(Example)`, `findBy(Example, Function)`. `[API]`
1.22.5 `getOne` (deprecated 2.5) → `getById` (deprecated 2.7) → **`getReferenceById`**. All three are
       `em.getReference`, i.e. a proxy. `[VERSION-TRAP]` `[TRAP]`
1.22.6 `@NoRepositoryBean` for intermediate base interfaces, and why omitting it makes Spring try to
       instantiate your abstract repository. `[TRAP]`
1.22.7 `@Repository` on a Spring Data interface is **unnecessary** — the proxy already gets exception
       translation via `PersistenceExceptionTranslationPostProcessor` wired by the repository
       factory. `[TRAP]` `[X-REF 07]`
1.22.8 `@EnableJpaRepositories`'s attributes in full: `basePackages`, `basePackageClasses`,
       `includeFilters`, `excludeFilters`, `repositoryImplementationPostfix` (**default `Impl`**),
       `namedQueriesLocation` (**default `META-INF/jpa-named-queries.properties`**),
       `queryLookupStrategy` (**default `CREATE_IF_NOT_FOUND`**), `repositoryFactoryBeanClass`,
       `repositoryBaseClass`, `entityManagerFactoryRef` (**default `entityManagerFactory`**),
       `transactionManagerRef` (**default `transactionManager`**), `considerNestedRepositories`,
       `enableDefaultTransactions`, `bootstrapMode`, `escapeCharacter` (**default `\`**).
       `[API]` `[NUM]` `[PROP]` `[RESEARCH]`
1.22.9 `BootstrapMode.DEFAULT | LAZY | DEFERRED` and `spring.data.jpa.repositories.bootstrap-mode` —
       what each does to startup time and to fail-fast behaviour. `[PROP]` `[TRAP]` `[RESEARCH]`
1.22.10 `spring.data.jpa.repositories.enabled` and turning repositories off entirely. `[PROP]`
1.22.11 Custom repository implementations: the `XxxCustom` interface + `XxxCustomImpl` class naming
        rule, how the fragment is composed into the proxy, and the ordering when two fragments define
        the same method. `[API]` `[BUILD]`
1.22.12 `repositoryBaseClass` — replacing `SimpleJpaRepository` globally (e.g. to add a
        `findAllReadOnly`). `[API]` `[BUILD]`
1.22.13 Query by Example: `Example.of(probe)`, `ExampleMatcher` (`matchingAll`, `matchingAny`,
        `withIgnorePaths`, `withStringMatcher`, `withIgnoreCase`, `withIgnoreNullValues`), and its
        hard limits — no ranges, no `or` across nesting, no `null` matching. `[API]` `[TRAP]`
1.22.14 The `Streamable<T>` return type and `StreamableWrapper`s; `Slice` vs `Page` vs `Window` vs
        `List`. `[API]`
1.22.15 Nullability: `@Nullable`, `Optional<T>`, `org.springframework.lang.NonNullApi` on a
        `package-info.java`, and Spring Data 4's move to **JSpecify**. What happens when a
        non-nullable method returns null (`EmptyResultDataAccessException`).
        `[VERSION-TRAP]` `[RESEARCH]`
1.22.16 Repository method return type `void` for a derived delete and why it hides the row count.

*(16 leaves)*

## §1.23 Derived query methods

1.23.1 The method-name grammar: `[subject][By][predicate][OrderBy...]`. Named parts:
       **subject keywords** `find`, `read`, `get`, `query`, `search`, `stream`, `exists`, `count`,
       `delete`, `remove`; and the `Distinct`/`Top`/`First` modifiers inside the subject.
       `[SOURCE]` `[API]`
1.23.2 The full predicate keyword table with the JPQL each produces: `Is`, `Equals`, `Between`,
       `LessThan`, `LessThanEqual`, `GreaterThan`, `GreaterThanEqual`, `After`, `Before`, `IsNull`,
       `Null`, `IsNotNull`, `NotNull`, `Like`, `NotLike`, `StartingWith`, `EndingWith`,
       `Containing`, `NotContaining`, `OrderBy`, `Not`, `In`, `NotIn`, `True`, `False`,
       `IgnoreCase`, `AllIgnoreCase`, `And`, `Or`, `IsEmpty`, `IsNotEmpty`, `Regex`/`Matches`.
       `[SOURCE]` `[API]` `[RESEARCH]`
1.23.3 `findTop3ByOrderByTotalDesc`, `findFirstBy...`, `findTop10ByStatus(Pageable)` — limiting, and
       the interaction between `Top`/`First` and a `Pageable`. `[TRAP]`
1.23.4 `findDistinctBy...` and why `distinct` plus a collection fetch is a different thing from
       `distinct` in the SQL.
1.23.5 Property-path resolution and its ambiguity algorithm: `findByAddressZipCode` tries
       `address.zipCode`, then `addressZip.code`, then `addressZipCode`. Fix an ambiguity with an
       underscore: `findByAddress_ZipCode`. `[SOURCE]` `[TRAP]`
1.23.6 A typo in a derived method name fails at **startup**, not at call time, because the
       `PartTree` is parsed while the repository proxy is built. This is the feature's best
       property. `[PROVE]`
1.23.7 The readability ceiling: `findByCustomerEmailAndStatusInAndCreatedAtBetweenOrderByCreatedAtDesc`
       is the point at which you switch to `@Query` or a `Specification`. State a rule (three
       predicates).
1.23.8 Derived **delete** queries: `deleteByStatus` and `removeByStatus` load the entities and delete
       them one by one (so callbacks fire), unlike a `@Modifying` bulk delete. Return `long` or the
       deleted list. `[TRAP]` `[SQL]`
1.23.9 Derived **count** and **exists** queries and their SQL. `[SQL]`
1.23.10 `Stream<T>` return type: requires an open transaction and a `try-with-resources`, and holds a
        cursor. `@Transactional(readOnly = true)` plus `hibernate.jdbc.fetch_size` for a real
        server-side cursor on PostgreSQL. `[TRAP]` `[PROP]`
1.23.11 Async return types `Future<T>`, `CompletableFuture<T>`, `ListenableFuture<T>` with `@Async`,
        and why they are almost always a mistake in a JPA repository (the transaction and the
        `EntityManager` do not follow the thread). `[TRAP]` `[X-REF 07]`
1.23.12 `Sort` and `Pageable` as the **last** parameter, `Sort.by(...).ascending()`,
        `Sort.Order.nullsFirst()`, `Sort.TypedSort`, and `JpaSort.unsafe("LENGTH(firstname)")` for a
        function — with the injection warning attached. `[API]` `[TRAP]`
1.23.13 `Limit` (Spring Data 3.2+) as a first-class parameter alongside `Sort`. `[VERSION-TRAP]`
        `[RESEARCH]`
1.23.14 `ScrollPosition` / `OffsetScrollPosition` / `KeysetScrollPosition` as a parameter and
        `Window<T>` as the return type — the Scroll API. Detailed in §2.9. `[API]` `[RESEARCH]`
1.23.15 `@Query` overrides derivation entirely; `QueryLookupStrategy.CREATE_IF_NOT_FOUND` is why both
        can coexist. The three strategies: `CREATE`, `USE_DECLARED_QUERY`, `CREATE_IF_NOT_FOUND`.
        `[API]` `[NUM]`
1.23.16 Query-method **parameter binding** for a derived query is positional by declaration order —
        so reordering two same-typed parameters silently swaps the predicate. `[TRAP]`

*(16 leaves)*

## §1.24 `@Query`, `@Modifying` and the annotation surface

1.24.1 `@Query`'s attributes: `value`, `countQuery`, `countProjection`, `nativeQuery`, `name`,
       `countName`, `queryRewriter`. `[API]` `[RESEARCH]`
1.24.2 JPQL in `@Query` is validated at startup (unless `BootstrapMode.LAZY`); native SQL is not.
       `[PROVE]`
1.24.3 `#{#entityName}` as the SpEL template variable that makes a generic base repository possible;
       `?#{...}` and `:#{...}` for SpEL parameters; `#{#sort}`; `?#{escape([0])}` +
       `?#{escapeCharacter()}` for `LIKE` sanitisation; `?${property.name}` for configuration
       properties. `[API]` `[SOURCE]` `[RESEARCH]`
1.24.4 SpEL in `@Query` is evaluated with the method arguments and the security principal in scope —
       and is therefore also the one place a `@Query` can be injected into. `[TRAP]` `[X-REF 13]`
1.24.5 `@Param("name")` and when it is required (before `-parameters`, always; with it, only when
       names differ). `[X-REF 07]`
1.24.6 `@Modifying`'s attributes: `flushAutomatically` (**default false**) and `clearAutomatically`
       (**default false**). What each fixes and what it costs. `[API]` `[NUM]` `[PROVE]`
1.24.7 `@Modifying` is **required** for `update`/`delete` JPQL and forbidden for `select`; the error
       when you get it wrong (`InvalidDataAccessApiUsageException: Not supported for DML
       operations`). `[DIAG]` `[TRAP]`
1.24.8 A `@Modifying` query needs a writable transaction: on a `@Transactional(readOnly = true)`
       repository it fails or silently does nothing depending on the driver. `[TRAP]`
1.24.9 `@QueryHints({@QueryHint(name, value)}, forCounting = false)` — and `forCounting` as the
       reason a hint mysteriously does not apply to the count query of a `Page`. `[API]` `[TRAP]`
1.24.10 `@EntityGraph(value = "name", type = FETCH|LOAD, attributePaths = {...})` on a repository
        method — the declarative fetch plan. Semantics in §2.3. `[API]`
1.24.11 `@Lock(LockModeType...)` on a repository method, including on an **overridden `findById`**.
        `[API]`
1.24.12 `@Meta(comment = "...")` and `hibernate.use_sql_comments=true` — putting the method name in
        the SQL so a DBA can attribute a slow query to your code. Genuinely useful, almost unknown.
        `[PROP]` `[RESEARCH]`
1.24.13 `@Procedure` for stored procedures from a repository. `[API]`
1.24.14 `QueryRewriter` — `String rewrite(String query, Sort sort)`, registered per method, for
        vendor hints and dynamic table names. `[API]` `[RESEARCH]`
1.24.15 `@DynamicUpdate`-style behaviour is **not** available per query; the annotation is on the
        entity. Do not look for it on the repository. `[TRAP]`

*(15 leaves)*

## §1.25 Projections

1.25.1 The four projection shapes and their SQL: **the entity** (all columns, managed),
       **interface projection** (selected columns), **DTO/record projection** (selected columns via
       constructor), **`Tuple`/`Object[]`** (selected columns, untyped). Master comparison table.
       `[SQL]` `[NUM]`
1.25.2 **Closed** interface projection — every accessor maps to a property, so Spring Data can
       restrict the select list. **Open** projection — any `@Value` SpEL accessor, so **the whole
       entity must be loaded** and the optimisation is lost. This is the single most important
       projection fact. `[PROVE]` `[SOURCE]` `[TRAP]`
1.25.3 Interface projections are backed by a **JDK dynamic proxy** over a `Map`/`Tuple`; nested
       interfaces are supported and recursive. `[SOURCE]`
1.25.4 `@Value("#{target.firstName + ' ' + target.lastName}")`, `#{@myBean.compute(target)}`,
       `#{args[0]}` — the three SpEL forms in an open projection. `[API]` `[RESEARCH]`
1.25.5 `default` methods on a projection interface as the type-safe alternative to `@Value`, and the
       fact that they *still* make the projection open. `[TRAP]` `[RESEARCH]`
1.25.6 Nullable wrappers in projections: `Optional<String>`, and the supported third-party
       `com.google.common.base.Optional`, `scala.Option`, `io.vavr.control.Option`. `[RESEARCH]`
1.25.7 Class-based (DTO) projections: a `record` or a class with an all-args constructor;
       `@PersistenceCreator` when there are several constructors; no proxying and **no nested
       projections**. `[API]` `[RESEARCH]`
1.25.8 Spring Data 3.x **automatic constructor-expression rewriting**: a `@Query("select u from User
       u")` declared to return `List<UserDto>` is rewritten to
       `select new UserDto(u.firstname, u.lastname) ...`, and a multi-select
       `select u.firstname, u.lastname` likewise. Constraints: no aliases in the rewritten
       expression, and it backs off if you already wrote a constructor expression. `[RESEARCH]`
       `[VERSION-TRAP]` `[PROVE]`
1.25.9 **Dynamic projections**: `<T> List<T> findByStatus(Status s, Class<T> type)` — one method,
       any projection, chosen at the call site. `[API]`
1.25.10 Native-query DTO mapping: positional column order must match the constructor, or use
        `@SqlResultSetMapping` with `@ConstructorResult`. `[TRAP]`
1.25.11 **The nested-property trap:** a projection whose accessor returns a nested projection over an
        association *still materialises the whole join* — projections limit top-level properties
        only. Quote the reference doc. `[TRAP]` `[SOURCE]` `[RESEARCH]`
1.25.12 Projections and the persistence context: projected results are **not managed**, so mutating
        them does nothing and `@Version` is not tracked. That is the point. `[PROVE]`
1.25.13 The performance argument with numbers: a 30-column entity versus a 3-column projection —
        columns fetched, bytes over the wire, no snapshot, no dirty check, no proxy. Show the
        arithmetic. `[NUM]` `[PROVE]`
1.25.14 When the entity is still right: you are going to modify it. Read-only endpoint ⇒ projection;
        write path ⇒ entity. State it as a rule. `[PROVE]`
1.25.15 Blaze-Persistence entity views as the third-party answer to "projections but with updates and
        deep graphs". Name it, do not teach it. `[RESEARCH]`

*(15 leaves)*

## §1.26 Pagination and sorting

1.26.1 `Pageable` / `PageRequest.of(page, size[, Sort])`, `Page<T>` (`getContent`,
       `getTotalElements`, `getTotalPages`, `hasNext`, `getNumber`, `getSize`, `getSort`, `map`),
       `Slice<T>` (no total), `Window<T>` (scroll), `Unpaged`. `[API]`
1.26.2 `Page` costs **two queries** — the content query plus a `count(*)`. `Slice` costs one (it
       fetches `size + 1` rows to learn `hasNext`). Choose `Slice` for infinite scroll. `[PROVE]`
       `[SQL]`
1.26.3 `countQuery` on `@Query` and `countProjection` — how to make the count query cheap (drop the
       joins and the order by). `[SQL]`
1.26.4 `PageableDefault`/`@PageableDefault`, `PageableHandlerMethodArgumentResolver`,
       `spring.data.web.pageable.*` (`default-page-size` **20**, `max-page-size` **2000**,
       `one-indexed-parameters`, `page-parameter` `page`, `size-parameter` `size`, `prefix`,
       `qualifier-delimiter`), and `SortHandlerMethodArgumentResolver`. `[PROP]` `[NUM]`
       `[RESEARCH]` `[X-REF 12]`
1.26.5 **Never return `Page<Entity>` from a controller**: it serialises the entity graph, triggers
       lazy loads during rendering, and Spring Boot 3.3+ warns that `PageImpl`'s JSON structure is
       unstable — use `PagedModel` or a DTO page. `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]` `[X-REF 12]`
1.26.6 `Page.map(this::toDto)` as the correct one-liner.
1.26.7 Sorting by an association property generates a join; sorting by an unmapped/aliased expression
       needs `JpaSort.unsafe`. `[TRAP]`
1.26.8 `Sort` on a native query is ignored — one of the sharpest edges in Spring Data JPA. `[TRAP]`
1.26.9 The deep-offset problem: `OFFSET 100000` makes the database materialise and discard 100k rows.
       The fix is keyset pagination (§2.9). `[PROVE]` `[X-REF 09]`
1.26.10 Pagination stability: without a total order (a tiebreaker on a unique column) rows shift
        between pages. Always append the id to the sort. `[TRAP]` `[PROVE]`
1.26.11 The collection-fetch pagination trap, preserved from the current guide: `HHH000104` /
        `HHH90003004` `firstResult/maxResults specified with collection fetch; applying in memory` —
        the whole result set is loaded and paginated in Java. Detailed in §2.5. `[DIAG]` `[TRAP]`
1.26.12 `Pageable.unpaged()` and `Sort.unsorted()` as the "no pagination" sentinels.

*(12 leaves)*

## §1.27 Transactions and the persistence context

1.27.1 The one-sentence relationship: **the persistence context's lifetime is the transaction's
       lifetime** (in the default transaction-scoped mode). Every "detached" surprise is this
       sentence. `[PROVE]`
1.27.2 `@Transactional`'s attributes for reference, mechanics in `07-spring-core.md`: `propagation`,
       `isolation`, `timeout`, `timeoutString`, `readOnly`, `rollbackFor`, `noRollbackFor`,
       `transactionManager`/`value`, `label`. `[API]` `[X-REF 07]`
1.27.3 `JpaTransactionManager` vs `DataSourceTransactionManager` vs `JtaTransactionManager`: which
       one Boot configures, and why using `DataSourceTransactionManager` with JPA means
       `JdbcTemplate` and the `EntityManager` end up on **different** connections. `[TRAP]`
       `[PROVE]`
1.27.4 `EntityManagerHolder` and `TransactionSynchronizationManager` — how the `EntityManager` is
       bound to the thread and found by the shared proxy. Mechanism in §3.20. `[API]`
1.27.5 The default rollback rule (unchecked and `Error` roll back, **checked exceptions commit**) and
       its persistence consequence: a checked exception after a mutation commits the mutation.
       `[TRAP]` `[X-REF 07]`
1.27.6 The boundary rule, preserved and expanded from the current guide: **the service method**. It
       is the unit of business work, so it is the unit of atomicity. Repositories give one
       transaction per call — no atomicity across two writes. Controllers hold a connection through
       serialisation. `[PROVE]`
1.27.7 `SimpleJpaRepository` is annotated `@Transactional(readOnly = true)` at class level with
       writes overridden by plain `@Transactional`; derived query methods get **no** transaction
       unless you add one. Quote the class. `[SOURCE]` `[RESEARCH]`
1.27.8 `enableDefaultTransactions = false` on `@EnableJpaRepositories` to turn that off and force
       callers to own transactions. `[API]`
1.27.9 What happens with **no** transaction: Spring's shared `EntityManager` opens one per repository
       call and closes it, so every returned entity is detached immediately, every lazy field
       throws, and `save` runs in its own auto-commit. `[PROVE]` `[TRAP]`
1.27.10 Propagation's persistence-context semantics, per value: `REQUIRED` (same context),
        `REQUIRES_NEW` (**a second `EntityManager` and a second connection**), `NESTED` (savepoint,
        same context), `SUPPORTS`/`NOT_SUPPORTED`/`NEVER`/`MANDATORY`. `[PROVE]` `[X-REF 07]`
1.27.11 `REQUIRES_NEW`'s two costs nobody mentions: a second pooled connection held simultaneously
        (so a pool of 10 supports 5 such calls), and invisibility of the outer transaction's
        unflushed changes to the inner one. `[PROVE]` `[NUM]` `[X-REF 09]`
1.27.12 Isolation and JPA: `@Transactional(isolation = ...)` is passed to the JDBC connection;
        Hibernate does not implement isolation, the database does. The L1 cache means you get
        *repeatable reads within a context* regardless of the isolation level — which is a common
        source of "we have read-committed but I saw the same value twice". `[PROVE]` `[TRAP]`
        `[X-REF 09]`
1.27.13 `hibernate.connection.isolation` as the global default and why setting it per
        `@Transactional` is better.
1.27.14 Transaction timeout: `@Transactional(timeout = 5)` sets the JDBC statement timeout via
        Hibernate; `jakarta.persistence.query.timeout` sets it per query;
        `spring.jpa.properties.jakarta.persistence.query.timeout` globally. Units differ (seconds vs
        milliseconds) — the classic mistake. `[NUM]` `[PROP]` `[TRAP]`
1.27.15 `TransactionSynchronization` / `TransactionSynchronizationManager.registerSynchronization`
        and `@TransactionalEventListener(phase = AFTER_COMMIT)` as the correct place to publish after
        a successful write. Note there is no persistence context in `AFTER_COMMIT`. `[TRAP]`
        `[X-REF 07]`
1.27.16 The self-invocation rule restated for repositories: `this.someTransactionalMethod()` inside
        the same bean skips the proxy, so there is no transaction and every entity is detached.
        `[TRAP]` `[X-REF 07]`
1.27.17 `TransactionTemplate` and `TransactionalOperator` when you need a programmatic boundary
        (a loop that commits every 1000 rows). `[API]`

*(17 leaves)*

## §1.28 Locking

1.28.1 The concurrency problem statement: lost update, dirty read, non-repeatable read, phantom.
       Which of those the database's isolation level handles, and which JPA locking handles.
       `[PROVE]` `[X-REF 09]`
1.28.2 `@Version` and the legal types: `int`, `Integer`, `short`, `Short`, `long`, `Long`,
       `java.sql.Timestamp`, and (Hibernate) `Instant`/`LocalDateTime`. Prefer a non-primitive
       integer. `[API]` `[TRAP]`
1.28.3 The optimistic mechanism, exactly: every UPDATE carries `where id = ? and version = ?` and
       sets `version = version + 1`; **zero rows updated ⇒ somebody else won ⇒ throw**. `[PROVE]`
       `[SQL]`
1.28.4 The exception zoo and which layer throws which: JPA's `OptimisticLockException`, Hibernate's
       `StaleObjectStateException` / `StaleStateException`, Spring's
       `ObjectOptimisticLockingFailureException` / `OptimisticLockingFailureException`. `[API]`
       `[DIAG]`
1.28.5 Why a version column is *free* correctness: no locks are held, so it scales; you pay only
       under actual contention, with a failed transaction. `[PROVE]`
1.28.6 Handling it properly means **retrying the whole transaction** — re-read, re-apply, re-commit —
       not catching and ignoring. Preserve the `@Retryable` example from the current guide, including
       the note that the retry must sit **outside** the transaction boundary. `[SOURCE]` `[TRAP]`
1.28.7 Version and detached entities: this is what makes optimistic locking work across an HTTP
       conversation (send the version to the client, get it back, `merge`). Show it. `[PROVE]`
1.28.8 `LockModeType.OPTIMISTIC` — forces a version *check* at commit even for an entity you only
       read (protects against a phantom-ish read-then-decide). `OPTIMISTIC_FORCE_INCREMENT` —
       bumps the version of an entity you only read, to lock an aggregate through its root.
       `[PROVE]` `[SQL]`
1.28.9 The aggregate-root locking pattern: incrementing the `Order`'s version when you add an
       `OrderLine`, so two concurrent line additions conflict. This is the interview-grade use of
       `OPTIMISTIC_FORCE_INCREMENT`. `[PROVE]`
1.28.10 `LockModeType.PESSIMISTIC_WRITE` → `SELECT ... FOR UPDATE`; `PESSIMISTIC_READ` →
        `FOR SHARE`/`LOCK IN SHARE MODE`; `PESSIMISTIC_FORCE_INCREMENT` → `FOR UPDATE` plus a
        version bump. Show the SQL per dialect. `[SQL]` `[NUM]`
1.28.11 `@Lock(LockModeType.PESSIMISTIC_WRITE)` on a repository method, including on an overridden
        `findById`; `em.find(Class, id, lockMode)`; `em.lock(entity, mode)`;
        `query.setLockMode(mode)`. Four entry points. `[API]`
1.28.12 The lock lifetime rule: a pessimistic lock is held **until the transaction ends**, so the
        transaction length *is* the lock length. This is why a `@Transactional` method that calls an
        HTTP API while holding `FOR UPDATE` is an outage. `[PROVE]` `[TRAP]`
1.28.13 `jakarta.persistence.lock.timeout` (milliseconds; `0` = `NOWAIT`, `-2` = `SKIP LOCKED` in
        Hibernate) and Hibernate's `Timeouts` constants in 7.0. Failing fast beats blocking.
        `[PROP]` `[NUM]` `[RESEARCH]` `[VERSION-TRAP]`
1.28.14 `SKIP LOCKED` as the job-queue primitive: `select ... for update skip locked limit 10` gives
        N workers disjoint batches with no coordination. The single most useful pessimistic pattern.
        `[SQL]` `[PROVE]` `[X-REF 14]`
1.28.15 `PessimisticLockScope.NORMAL` vs `EXTENDED` — whether the lock extends to join-table and
        element-collection rows. `[API]`
1.28.16 `LockAcquisitionException` / `CannotAcquireLockException` /
        `PessimisticLockingFailureException` / `DeadlockLoserDataAccessException` and the retry
        decision for each. `[API]` `[DIAG]`
1.28.17 Deadlock avoidance rule: acquire locks in a consistent order (e.g. always ascending id), keep
        transactions short, and prefer optimistic. `[X-REF 09]`
1.28.18 The decision table: optimistic vs pessimistic vs `SKIP LOCKED` vs a database constraint vs an
        application-level lock, by contention level and cost of a retry. `[NUM]`
1.28.19 **What locking cannot do:** it cannot protect an invariant across rows that are not read
        (the phantom insert). That needs a constraint, a serializable transaction, or a lock on a
        parent row. `[PROVE]` `[TRAP]` `[X-REF 09]`

*(19 leaves)*

## §1.29 The three caches

1.29.1 The taxonomy in one table: **L1** = persistence context, always on, per-transaction, entity
       identity map. **L2** = `SessionFactory`-scoped, opt-in, shared across transactions, per entity
       type. **Query cache** = query-string+params → list of **identifiers**, needs L2 to be useful.
       Plus the **natural-id cache** and the **timestamp cache** nobody names. `[SOURCE]` `[NUM]`
1.29.2 What L2 stores: a **dehydrated `Object[]`** of state keyed by entity id — not your instance.
       On a hit Hibernate rebuilds an entity from it, which is why L2 hits still allocate. `[PROVE]`
1.29.3 Enabling L2: `hibernate.cache.use_second_level_cache=true`,
       `hibernate.cache.region.factory_class`, a provider on the classpath, and `@Cache` or
       `@Cacheable` per entity plus `jakarta.persistence.sharedCache.mode`
       (`ALL`/`NONE`/`ENABLE_SELECTIVE`/`DISABLE_SELECTIVE`/`UNSPECIFIED`). `[PROP]` `[API]`
1.29.4 `@Cache(usage = ..., region = ..., include = ...)` — and `include` **removed in Hibernate 7**.
       `[API]` `[VERSION-TRAP]`
1.29.5 The four `CacheConcurrencyStrategy` values with mechanism: `READ_ONLY` (no updates allowed),
       `NONSTRICT_READ_WRITE` (invalidate after commit; a small inconsistency window),
       `READ_WRITE` (**soft locks**, strong consistency without a transactional cache),
       `TRANSACTIONAL` (requires an XA/JTA-capable cache). `[SOURCE]` `[RESEARCH]`
1.29.6 The soft-lock mechanism in `READ_WRITE`, since this is the interview question: on update
       Hibernate replaces the cached entry with a **lock marker** until commit; concurrent readers
       that see a lock marker **go to the database**. Walked in §3.15. `[PROVE]` `[RESEARCH]`
1.29.7 Collection caching is separate from entity caching: `@Cache` on the collection field, and it
       stores only the **identifiers** of the members. `[PROVE]`
1.29.8 The providers and their positioning: **Ehcache 3 / JCache (JSR-107)**, **Infinispan**,
       **Hazelcast**, **Redis via a JCache provider or Redisson**, and the removed
       `hibernate-ehcache` (2.x) module. `[RESEARCH]` `[VERSION-TRAP]`
1.29.9 The query cache: `hibernate.cache.use_query_cache=true` plus a per-query
       `org.hibernate.cacheable` hint. It stores **ids**, so a hit still loads entities (from L2 or
       the database), and any write to any table in the query space invalidates the whole region via
       the **timestamps cache**. `[PROVE]` `[TRAP]`
1.29.10 Why the query cache is usually a net loss: the invalidation granularity is a whole table's
        worth of queries, so a write-heavy table makes every cached query miss while still paying the
        write cost. `[PROVE]`
1.29.11 **Why L2 is dangerous in a multi-instance deployment**, preserved from the current guide:
        each JVM has its own L2 unless the cache is clustered; instance A updates, instance B serves
        stale — indefinitely, until TTL. Any write that bypasses Hibernate (a `@Modifying` bulk
        update, a native query, Flyway, a DBA, another service) invalidates nothing. `[TRAP]`
        `[SOURCE]`
1.29.12 The default recommendation, preserved: **no L2**; cache at the application layer with
        explicit keys and TTLs you control. Then the exception: immutable reference data
        (`@Cache(usage = READ_ONLY)` on a `Currency` table) is exactly what L2 is for. `[PROVE]`
        `[X-REF 15]`
1.29.13 `CacheMode` / `CacheRetrieveMode` / `CacheStoreMode` per session and per query, and
        `session.setCacheMode(CacheMode.IGNORE)` for a batch job that must not pollute the cache.
        `[API]`
1.29.14 `hibernate.generate_statistics=true` plus `SecondLevelCacheStatistics`
        (`getHitCount`, `getMissCount`, `getPutCount`, `getElementCountInMemory`) — measure before
        and after, or you are guessing. `[PROP]` `[API]`
1.29.15 `Cache.evict*` and the manual-invalidation surface you will need after any bulk operation.
        `[API]`
1.29.16 Hibernate 7 change: **`StatelessSession` now uses L2 by default**, so an ETL job that used
        to bypass the cache now populates and reads it. `[VERSION-TRAP]` `[RESEARCH]`

*(16 leaves)*

## §1.30 Schema management and migrations

1.30.1 `spring.jpa.hibernate.ddl-auto` values: `none`, `validate`, `update`, `create`, `create-drop`,
       and Boot's default (**`create-drop` for an embedded database, `none` otherwise**). `[PROP]`
       `[NUM]` `[RESEARCH]`
1.30.2 The underlying Hibernate settings: `hibernate.hbm2ddl.auto`,
       `jakarta.persistence.schema-generation.database.action` (`none`/`create`/`drop`/
       `drop-and-create`), `...scripts.action`, `...create-source`,
       `...create-script-source`, `...drop-script-source`, `...create-target`. `[PROP]`
1.30.3 **Production: `validate` (or `none`) with Flyway/Liquibase owning the schema.** The four
       arguments, preserved from the current guide: `update` never drops or renames, silently
       diverges between environments, gives no review artifact, and can lock a big table at startup
       on every instance simultaneously. `[PROVE]` `[SOURCE]`
1.30.4 What `validate` actually checks (tables, columns, types, sequences) and what it does **not**
       (indexes, constraints, nullability in some dialects, defaults). Its value is fail-fast on the
       common drift. `[PROVE]` `[RESEARCH]`
1.30.5 Flyway mechanics: `V<version>__<description>.sql` naming, `flyway_schema_history`, checksum
       validation, `baseline`, `repair`, `outOfOrder`, `flyway.locations`, and the **advisory lock**
       that makes concurrent replicas safe (first one wins, the rest wait). `[NUM]` `[RESEARCH]`
1.30.6 Liquibase mechanics for contrast: XML/YAML/SQL changelogs, `databasechangelog`,
       `databasechangeloglock`, preconditions, contexts, labels, rollback statements.
1.30.7 Flyway vs Liquibase decision in one table: SQL-first vs abstraction, rollback support,
       multi-database, review readability, tooling. `[NUM]`
1.30.8 Migration discipline, preserved: versioned, immutable once merged, forward-only, checked into
       git, applied by one process at startup. Plus: never edit a merged migration (the checksum
       fails), and put data backfills in a separate migration from DDL.
1.30.9 Ordering: Flyway/Liquibase run **before** the `EntityManagerFactory` is created (Boot's
       auto-configuration orders it), which is why `validate` sees the migrated schema. Name the
       `@DependsOn`/`FlywayMigrationInitializer` mechanism. `[FLOW]` `[RESEARCH]`
1.30.10 `spring.jpa.defer-datasource-initialization=true` — delays `schema.sql`/`data.sql` until
        after Hibernate's DDL so seed data can rely on the generated tables. `[PROP]` `[RESEARCH]`
1.30.11 `spring.sql.init.mode` (`always`/`embedded`/`never`), `schema.sql`, `data.sql`,
        `import.sql` (Hibernate's own, run after `create`) — three different mechanisms people
        confuse. `[PROP]` `[TRAP]`
1.30.12 Generating a starting migration from the entities: `ddl-auto=create` against a scratch
        database with `jakarta.persistence.schema-generation.scripts.action=create`, then hand-edit.
        The legitimate use of DDL generation. `[PROVE]`
1.30.13 Zero-downtime schema change patterns (expand/contract, add-nullable-then-backfill-then-
        enforce, dual-write, rename via view) — named here, worked in `09-sql-databases.md`.
        `[X-REF 09]`
1.30.14 The entity/schema drift detector in CI: boot the app with `validate` against a
        Flyway-migrated Testcontainer and fail the build. The single highest-value JPA test.
        `[PROVE]` `[X-REF 16]`

*(14 leaves)*

## §1.31 The configuration property surface

1.31.1 The Boot-owned keys: `spring.jpa.hibernate.ddl-auto`, `spring.jpa.open-in-view`,
       `spring.jpa.show-sql`, `spring.jpa.generate-ddl`, `spring.jpa.database`,
       `spring.jpa.database-platform`, `spring.jpa.mapping-resources`,
       `spring.jpa.defer-datasource-initialization`,
       `spring.jpa.hibernate.naming.physical-strategy`,
       `spring.jpa.hibernate.naming.implicit-strategy`,
       `spring.jpa.hibernate.use-new-id-generator-mappings` (gone in Boot 3).
       `[PROP]` `[NUM]` `[VERSION-TRAP]`
1.31.2 The Hibernate keys you will actually set, with defaults:
       `hibernate.jdbc.batch_size` (**default none/0**), `hibernate.order_inserts` (**false**),
       `hibernate.order_updates` (**false**),
       `hibernate.jdbc.batch_versioned_data` (**true in 5+**),
       `hibernate.default_batch_fetch_size` (**-1/none**),
       `hibernate.jdbc.fetch_size`, `hibernate.generate_statistics` (**false**),
       `hibernate.format_sql`, `hibernate.highlight_sql`, `hibernate.use_sql_comments` (**false**),
       `hibernate.query.in_clause_parameter_padding` (**false**),
       `hibernate.query.plan_cache_max_size` (**2048**),
       `hibernate.connection.provider_disables_autocommit` (**false**),
       `hibernate.log_slow_query`, `hibernate.id.optimizer.pooled.preferred`,
       `hibernate.jdbc.time_zone`, `hibernate.globally_quoted_identifiers`,
       `hibernate.enable_lazy_load_no_trans` (**false — and never turn it on**).
       `[PROP]` `[NUM]` `[RESEARCH]`
1.31.3 `hibernate.enable_lazy_load_no_trans=true` as a named anti-pattern: it opens a **temporary
       session per lazy load**, silently converting a `LazyInitializationException` into an N+1 with
       N separate transactions. `[TRAP]` `[PROVE]`
1.31.4 `spring.jpa.show-sql=true` versus `logging.level.org.hibernate.SQL=DEBUG` versus
       `logging.level.org.hibernate.orm.jdbc.bind=TRACE` (6.x; formerly
       `org.hibernate.type.descriptor.sql.BasicBinder=TRACE`). Only the last shows bind parameters.
       `[PROP]` `[VERSION-TRAP]` `[TRAP]`
1.31.5 The logger inventory worth knowing: `org.hibernate.SQL`, `org.hibernate.orm.jdbc.bind`,
       `org.hibernate.orm.jdbc.extract`, `org.hibernate.SQL_SLOW`, `org.hibernate.stat`,
       `org.hibernate.cache`, `org.hibernate.orm.results`,
       `org.springframework.orm.jpa`, `org.springframework.transaction`,
       `org.springframework.data.jpa`. `[PROP]` `[DIAG]`
1.31.6 `spring.datasource.hikari.*` keys that interact with JPA: `maximum-pool-size` (**10**),
       `minimum-idle`, `connection-timeout` (**30000 ms**), `idle-timeout` (**600000**),
       `max-lifetime` (**1800000**), `auto-commit` (**true**), `leak-detection-threshold`
       (**0 = off**), `data-source-properties`. `[PROP]` `[NUM]` `[X-REF 09]`
1.31.7 The driver-level properties that matter for JPA throughput: PostgreSQL
       `reWriteBatchedInserts=true`, `prepareThreshold`, `defaultRowFetchSize`; MySQL
       `rewriteBatchedStatements=true`, `cachePrepStmts`, `useServerPrepStmts`.
       **Without these, `hibernate.jdbc.batch_size` buys much less than you think.** `[PROP]`
       `[NUM]` `[TRAP]` `[RESEARCH]`
1.31.8 Where each property can be set and who wins: `application.yml`, `spring.jpa.properties.*`,
       a `HibernatePropertiesCustomizer`, a query hint, an annotation. `[X-REF 07]`
1.31.9 `/actuator/configprops` and `/actuator/metrics/hikaricp.connections.*` as the way to check
       what is actually in effect rather than what you wrote. `[DIAG]`

*(9 leaves)*

---

**PART 1 total: 12+11+17+17+13+17+14+22+28+12+22+14+18+13+16+12+17+11+22+16+12+16+16+15+15+12+17+19+16+14+9 = 486 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **Master cost table** — for every read/write operation, the statement count and the row count
      it touches: `find` (hit L1 / hit L2 / miss), `getReference`, `find` with an eager `*ToOne`,
      derived query, `join fetch`, `@EntityGraph`, `@BatchSize`, projection, `Page`, `Slice`,
      keyset scroll, `persist` with IDENTITY, `persist` with SEQUENCE+pooled, `merge`, dirty-check
      UPDATE, `@DynamicUpdate` UPDATE, `remove`, `orphanRemoval`, `deleteAll`, `deleteAllInBatch`,
      bulk `@Modifying`, `StatelessSession.insert`. Columns: SELECTs, INSERT/UPDATE/DELETEs,
      entities held in the context, snapshot memory, batchable (Y/N). This is the table the whole
      guide is for. `[NUM]` `[PROVE]`
2.1.2 **Fetch-strategy decision table**: `join fetch` / `@EntityGraph` / `@BatchSize` /
      `FetchMode.SUBSELECT` / two queries / projection / L2 — by association cardinality, number of
      parents, whether you paginate, and whether you mutate. `[NUM]`
2.1.3 **Statement-count budget table**: what "good" looks like per endpoint shape (a detail page:
      1–3 statements; a list page: 2; a write: 1 + N batched). Anything above budget is a bug with a
      name. `[NUM]`
2.1.4 **Entity-state × operation matrix**: for each of the four states, what `persist`, `merge`,
      `remove`, `refresh`, `detach`, `flush` and `save` do — including the throws. `[NUM]`
2.1.5 **Exception → cause → fix table** covering the twenty exceptions in this guide.
2.1.6 **Annotation ownership table**: which annotations are Jakarta Persistence, which are Hibernate,
      which are Spring Data — because interviewers ask "is that JPA or Hibernate?". `[NUM]`
2.1.7 **Memory-footprint table**: bytes per managed entity for a 10-field entity, with the
      arithmetic: object header 12–16 B, field storage, the hydrated `Object[]` snapshot, the
      `EntityKey`, the `EntityEntry`, the `IdentityHashMap` entries. Then multiply by 100k.
      `[NUM]` `[PROVE]` `[X-REF 06]`
2.1.8 **Property → default → effect table** for the twenty settings in §1.31. `[PROP]` `[NUM]`
2.1.9 **JPA vs Spring Data JDBC vs jOOQ vs MyBatis vs JdbcClient** decision table by workload.
2.1.10 **Version-delta table**: for each of thirty behaviours, what it does in Hibernate 5.6, 6.6 and
       7.0, and in Spring Data 2.7, 3.5 and 4.0. `[VERSION-TRAP]`

*(10 leaves)*

## §2.2 N+1 — the full taxonomy

2.2.1 The canonical case, preserved from the current guide: `findAll()` then navigating a lazy
      `@ManyToOne` in a loop — 1 + N queries. `[SOURCE]` `[SQL]`
2.2.2 The **five** distinct N+1 shapes, each with a different fix, because "N+1" is used for all of
      them: (a) lazy `*ToOne` in a loop; (b) lazy collection in a loop; (c) **eager** `*ToOne` on an
      entity returned by a *query* (JPQL ignores `FetchType.EAGER`'s join and issues a secondary
      select per row); (d) `@ElementCollection` per row; (e) N+1 **inside serialisation** under
      open-session-in-view. `[PROVE]` `[TRAP]`
2.2.3 Why case (c) surprises everyone: `em.find` honours the eager association with a join, but a
      JPQL `select o from Order o` does **not** — it issues one extra SELECT per row to satisfy the
      eager mapping. Same mapping, different statement count. `[PROVE]` `[SQL]` `[TRAP]`
2.2.4 The second-order case: N+1 on a *cached* association where L2 turns N queries into N cache
      hits, so the metric improves and the design bug remains.
2.2.5 Detection, ranked by usefulness: (1) a **query-count assertion in a test** that fails the
      build; (2) `hibernate.generate_statistics` + `Statistics.getQueryExecutionCount()` /
      `getPrepareStatementCount()`; (3) datasource-proxy or p6spy with a per-request count;
      (4) `logging.level.org.hibernate.SQL=DEBUG` read by eye; (5) `spring.jpa.show-sql`. `[DIAG]`
      `[PROVE]`
2.2.6 The query-count assertion in code: capture `getPrepareStatementCount()` before and after,
      assert an exact number, and treat a change as a review event. `[BUILD]` `[X-REF 16]`
2.2.7 The fix table, preserved from the current guide and extended: `JOIN FETCH`, `@EntityGraph`,
      DTO projection, `@BatchSize`, `hibernate.default_batch_fetch_size`, `FetchMode.SUBSELECT`,
      two-query id-then-fetch, L2, denormalisation. Columns: statements, memory, works with
      pagination, works with multiple collections, declarative. `[NUM]` `[SOURCE]`
2.2.8 `@BatchSize` arithmetic: 1000 parents with `@BatchSize(50)` is `1 + 20` queries, not `1001`.
      Show the `IN (?,?,...)` SQL and the padding behaviour. `[NUM]` `[SQL]` `[PROVE]`
2.2.9 Why `hibernate.default_batch_fetch_size` is the single highest-value blanket setting in the
      whole guide: it converts every unfixed N+1 in the codebase into `N/size` queries with no code
      change. Recommend a value and justify it. `[PROP]` `[NUM]` `[PROVE]`
2.2.10 `hibernate.query.in_clause_parameter_padding=true` — pads `IN` lists to powers of two so the
       statement cache and the database's plan cache hit. Interacts with §2.2.8. `[PROP]`
       `[RESEARCH]`
2.2.11 `FetchMode.SUBSELECT`: one extra query that re-runs the original query as a subselect to load
       all collections at once. Best when the original query is cheap and selective; terrible when it
       is a full scan. `[PROVE]` `[SQL]`
2.2.12 **Trap: two collection `join fetch`es in one query** → `MultipleBagFetchException`, and with
       `Set`s a **cartesian product** instead. Preserve the current guide's wording, add the
       mechanism from §1.14.4 and the row arithmetic (10 items × 5 payments = 50 rows per order).
       `[TRAP]` `[NUM]` `[SOURCE]`
2.2.13 The correct multi-collection strategy: one collection per query in the same persistence
       context, relying on the identity map to stitch them; or `@BatchSize`/`SUBSELECT` for the
       second. `[PROVE]`
2.2.14 `distinct` in a `join fetch` query: it de-duplicates *entities*, and since Hibernate 6 the
       `select distinct` is no longer pushed to SQL for this purpose
       (`hibernate.query.passDistinctThrough` was the 5.x knob). Verify. `[VERSION-TRAP]`
       `[RESEARCH]`
2.2.15 The "just make everything eager" non-fix: it turns N+1 into one giant join graph, loads the
       whole database for a detail page, and cannot be turned off per query. `[TRAP]` `[PROVE]`
2.2.16 The design-level fix: stop returning entities from read endpoints. Most N+1 disappears when
       the read model is a projection. `[PROVE]`

*(16 leaves)*

## §2.3 Entity graphs

2.3.1 What an entity graph is: a **fetch plan** attached to a query or a `find`, overriding the
      mapping's `FetchType` for that call. `[PROVE]`
2.3.2 `@NamedEntityGraph(name, attributeNodes, subgraphs)`, `@NamedAttributeNode(value, subgraph,
      keySubgraph)`, `@NamedSubgraph(name, type, attributeNodes)`. `[API]`
2.3.3 The **fetch graph** vs **load graph** distinction, precisely: with
      `jakarta.persistence.fetchgraph` every attribute *not* in the graph is treated as `LAZY`; with
      `jakarta.persistence.loadgraph` attributes not in the graph keep their mapped fetch type. Show
      the different SQL. `[PROVE]` `[SQL]` `[TRAP]`
2.3.4 Hibernate's deviation: it has historically treated `fetchgraph` less strictly than the spec for
      `*ToOne` associations that are non-optional. Verify against 6.6 before asserting. `[RESEARCH]`
      `[TRAP]`
2.3.5 `@EntityGraph(attributePaths = {"customer", "items.product"})` on a repository method — the
      ad-hoc form, no `@NamedEntityGraph` needed; dotted paths create subgraphs. `[API]`
2.3.6 `@EntityGraph(type = EntityGraphType.FETCH | LOAD)` maps to the two hints in §2.3.3;
      **`FETCH` is Spring Data's default**. `[NUM]`
2.3.7 Programmatic graphs: `em.createEntityGraph(Order.class)`, `addAttributeNodes`,
      `addSubgraph`, `em.getEntityGraph("name")`, and passing it in the `find` properties map.
      `[API]` `[BUILD]`
2.3.8 Entity graphs compose with derived queries, which is their advantage over `@Query("... join
      fetch ...")`: you keep the derivation and change only the fetch plan. `[PROVE]`
2.3.9 Entity graphs **do not** fix the collection-pagination problem — a `Page`-returning method with
      an `@EntityGraph` on a collection produces the same `HHH90003004` in-memory pagination.
      Preserve this from the current guide. `[TRAP]` `[SOURCE]`
2.3.10 Multiple collections in one graph reproduces `MultipleBagFetchException`/cartesian product.
       Same mechanism, different syntax. `[TRAP]`
2.3.11 Graphs on a `@ManyToOne` chain are the safe, high-value case: three levels of `*ToOne` in one
       query with no row multiplication. `[PROVE]`
2.3.12 Hibernate 7's `@NamedEntityGraph` (Hibernate's own, string-based
       `@NamedEntityGraph("customer, items(product)")`) as a terser alternative. `[VERSION-TRAP]`
       `[RESEARCH]`
2.3.13 JPA 3.2's generified `EntityGraph<T>` and the source-breaking change it causes.
       `[VERSION-TRAP]`
2.3.14 The decision rule: `@EntityGraph` for reusable declarative plans on `*ToOne` chains,
       `join fetch` for one bespoke query, projections for read-only, `@BatchSize` for the long
       tail. `[PROVE]`

*(14 leaves)*

## §2.4 Views, copies, snapshots and lifetime

2.4.1 The distinction this guide must make explicitly, because it is where the bugs live:
      **a managed entity is a live view of a row**, **a detached entity is a stale copy**,
      **a projection is a snapshot**, and **the loaded-state array is an internal snapshot you never
      see**. Each mistake has a signature bug. `[PROVE]`
2.4.2 Mutating a detached entity: nothing happens. Symptom — "my update silently did nothing".
      `[TRAP]`
2.4.3 Mutating a managed entity you only meant to read: an UPDATE you never wrote. Symptom —
      unexplained writes and version bumps. `[TRAP]`
2.4.4 Mutating a projection: nothing happens, and there is no error. `[TRAP]`
2.4.5 Holding a managed entity beyond its transaction (a field, a cache, a `ThreadLocal`, an HTTP
      session): a detached instance that lazily explodes, and a **memory leak** because it holds its
      whole loaded graph. `[TRAP]` `[X-REF 06]`
2.4.6 Putting entities in a Spring `@Cacheable` cache: you are caching detached instances with lazy
      proxies whose session is gone. Cache DTOs. `[TRAP]` `[X-REF 15]`
2.4.7 Serialising an entity to JSON: proxies, `hibernateLazyInitializer`, bidirectional cycles
      (`StackOverflowError` or `@JsonManagedReference`/`@JsonBackReference`/`@JsonIgnore` band-aids),
      and the correct answer (a DTO). `[TRAP]` `[X-REF 12]`
2.4.8 Sending an entity over a message queue: the same problems plus schema coupling between
      services. `[X-REF 14]`
2.4.9 `em.detach(entity)` as the deliberate "give me a snapshot" tool, and `clear()` for the whole
      context.
2.4.10 A defensive copy of a collection returned from a getter
       (`return List.copyOf(items)`) — how it protects the `PersistentBag` from §1.14.7. `[BUILD]`
2.4.11 The lifetime table: for each of L1, the entity instance, the proxy, the collection wrapper,
       the projection, the `EntityManager`, the connection and the transaction — when it is created
       and when it dies. `[NUM]`

*(11 leaves)*

## §2.5 Pagination with collection fetch

2.5.1 The reproduction, preserved verbatim from the current guide: `@Query("select o from Order o
      join fetch o.items") Page<Order> findAllWithItems(Pageable p)`. `[SOURCE]`
2.5.2 The log line, preserved: **`HHH000104: firstResult/maxResults specified with collection fetch;
      applying in memory`** — and Hibernate 6's renumbered code **`HHH90003004`**. Both must appear
      so a reader greps either. `[DIAG]` `[NUM]` `[RESEARCH]`
2.5.3 Why Hibernate does this rather than being wrong: the join multiplies rows, so a SQL `LIMIT`
      would truncate a parent's children. Hibernate chooses correctness and paginates in Java —
      after fetching **the entire result set**. `[PROVE]`
2.5.4 The consequence with numbers: 200k orders × 5 items = 1M rows into heap to serve page 3 of 20.
      Show the byte estimate and the OOM. `[NUM]` `[X-REF 06]`
2.5.5 **The fix — two queries**, preserved: (1) page the ids with the `Pageable`; (2) fetch the graph
      with `where o.id in :ids`, re-applying the sort. Ship both queries and the assembly code.
      `[BUILD]` `[SOURCE]`
2.5.6 Why the second query must re-apply the `order by`: `IN` does not preserve order. The bug this
      causes is "pagination works but rows are shuffled". `[TRAP]`
2.5.7 The `countQuery` for step (1) and why the default generated count with a fetch join is wrong or
      expensive. `[SQL]`
2.5.8 Alternative fixes and when each is better: `@BatchSize` on the collection (page parents only,
      let the collection batch-load); a projection with an aggregate (`count(items)`) when you only
      need a number; a separate endpoint for the children. `[PROVE]`
2.5.9 Hibernate 6 can sometimes rewrite this into a windowed subquery — **do not rely on it**,
      preserved from the current guide, and say how to check (read the SQL). `[TRAP]` `[RESEARCH]`
2.5.10 The general rule: **`Pageable` and a collection `join fetch` are mutually exclusive.** Put it
       in the review checklist. `[PROVE]`
2.5.11 "Any `HHH000104`/`HHH90003004` in your logs is a production incident waiting for the table to
       grow" — preserve this sentence. Add: alert on it. `[SOURCE]` `[X-REF 20]`

*(11 leaves)*

## §2.6 `equals` and `hashCode` on entities

2.6.1 The problem restated precisely, preserved from the current guide: a new entity has `id == null`,
      is added to a `HashSet`, and the id is assigned at flush — its hash changes and it is **lost
      inside the set** (present in a bucket that no longer matches its hash). `[PROVE]` `[SOURCE]`
      `[X-REF 02]`
2.6.2 The second problem: the same row loaded in two persistence contexts gives two instances that
      are `!=` and, with default `Object.equals`, unequal — so a detached and a managed version of
      the same row both live in a set. `[PROVE]`
2.6.3 The third problem: a proxy's `getClass()` is a generated subclass, so
      `getClass() != o.getClass()` fails for equal rows. `[PROVE]`
2.6.4 The three working strategies, preserved and ranked: (1) a **business key** (natural unique
      immutable field); (2) an **application-assigned UUID** set in the constructor; (3) the
      surrogate id with `equals` returning false when either id is null, and a **constant
      `hashCode`**. `[SOURCE]`
2.6.5 Why a constant `hashCode` is correct rather than a hack: `hashCode` must be stable for the
      object's lifetime; `getClass().hashCode()` is stable and legal, and the cost is a linear scan
      within one class's bucket — irrelevant for the collection sizes involved. `[PROVE]`
2.6.6 The complete implementation to ship, using `instanceof` pattern matching and
      `Hibernate.getClass(o)` so a proxy compares equal to its target. `[BUILD]` `[SOURCE]`
2.6.7 **Trap:** Lombok `@Data` / `@EqualsAndHashCode` on an entity includes every field, so it
      triggers lazy loads inside `equals`, recurses through bidirectional associations, and breaks on
      collections. Never put `@Data` on an entity. Preserve verbatim. `[TRAP]` `[SOURCE]`
2.6.8 **Trap:** Lombok `@ToString` on an entity for the same reason — a log line that initialises the
      whole graph. Use `@ToString(onlyExplicitlyIncluded = true)` or write it. `[TRAP]`
2.6.9 The `@NoArgsConstructor(access = PROTECTED)` + `@Getter` + explicit setters Lombok subset that
      *is* safe on an entity. `[PROVE]`
2.6.10 `records` cannot be entities (§1.9.27), so the record `equals` question does not arise — but
       records are the ideal *projection*, where value equality is exactly right. `[X-REF 04]`
2.6.11 The interview answer in three sentences: "generated ids change after construction; hash-based
       collections cache the hash; therefore either the hash must not depend on the id, or the id
       must not be generated."

*(11 leaves)*

## §2.7 Entities, DTOs and the layer boundary

2.7.1 The rule: **entities do not leave the transactional service layer.** Everything crossing out is
      a DTO/record. This single rule eliminates `LazyInitializationException`, OSIV,
      serialisation N+1, accidental writes, and API/schema coupling at once. `[PROVE]`
2.7.2 The four objections and the answers: "boilerplate" (records + a mapper), "duplication" (the
      shapes genuinely differ), "we'd need two models" (yes — that is CQRS-lite), "performance"
      (projections are faster, not slower). `[PROVE]`
2.7.3 Mapping options ranked: a hand-written static factory / `record` canonical constructor,
      MapStruct (compile-time), ModelMapper/Dozer (reflection — avoid), and a JPQL constructor
      expression (no entity loaded at all — best). `[NUM]`
2.7.4 The request-side mirror: never bind an HTTP body straight onto an entity. Mass-assignment lets
      a caller set `role` or `version`. Bind to a command record and copy explicitly. `[TRAP]`
      `[X-REF 13]`
2.7.5 Read model vs write model: the read path uses projections and needs no persistence context;
      the write path loads the aggregate and mutates it. Different shapes, different code.
      `[X-REF 22]`
2.7.6 Where validation lives: `@NotNull` on the DTO for input validation, database constraints for
      invariants, and Bean Validation on the entity via
      `hibernate.check_nullability` / the `BeanValidationEventListener` — which fires at flush and
      throws `ConstraintViolationException` from `commit`. `[TRAP]` `[RESEARCH]`
2.7.7 `spring.jpa.properties.jakarta.persistence.validation.mode` (`AUTO`/`CALLBACK`/`NONE`) and
      `hibernate.validator.apply_to_ddl` — entity validation and its DDL side effects. `[PROP]`
      `[RESEARCH]`
2.7.8 The anaemic-domain-model debate in one paragraph, with the practical position: behaviour on the
      entity is fine and good; JPA does not prevent it; what it prevents is *constructor* invariants
      (no-arg constructor required). `[PROVE]`
2.7.9 Package-by-feature so the entity, repository, service and DTOs sit together and the entity's
      visibility can be package-private. `[PROVE]`
2.7.10 ArchUnit rules that enforce §2.7.1 mechanically: no `jakarta.persistence` import in the
       controller package, no entity type in a controller signature. `[BUILD]` `[X-REF 16]`

*(10 leaves)*

## §2.8 Dynamic queries — Specifications, Query by Example and QueryDSL

2.8.1 The problem: a search endpoint with seven optional filters. Enumerate the four bad answers
      (string concatenation, `if`-chains of derived methods, `coalesce`-everything JPQL, a native
      query built by hand) before the good ones. `[PROVE]`
2.8.2 `JpaSpecificationExecutor<T>`: `findOne(Specification)`, `findAll(Specification)`,
      `findAll(Specification, Pageable)`, `findAll(Specification, Sort)`, `count(Specification)`,
      `exists(Specification)`, `delete(Specification)`, `findBy(Specification, Function)`.
      `[API]` `[RESEARCH]`
2.8.3 `Specification<T>`'s single method
      `Predicate toPredicate(Root<T>, CriteriaQuery<?>, CriteriaBuilder)`, and the combinators
      `where`, `and`, `or`, `not`, `allOf`, `anyOf`, `unrestricted`. `[API]` `[RESEARCH]`
2.8.4 The idiom to ship: a `OrderSpecifications` class of static factory methods, each returning a
      `Specification<Order>`, composed with `Specification.allOf(...)` filtered for nulls.
      `[BUILD]`
2.8.5 Specifications and joins: `root.join("customer", JoinType.LEFT)` inside a specification, and
      the **duplicate-join problem** when two specifications each join the same association —
      `query.getRoots()` inspection or a shared join helper as the fix. `[TRAP]` `[PROVE]`
2.8.6 Specifications and `distinct`: `query.distinct(true)` inside a specification, and why it also
      applies to the count query (and breaks it). `[TRAP]`
2.8.7 Specifications and fetch joins: `root.fetch(...)` inside a specification throws on the **count
      query** for a `Page`. The fix is `if (Long.class != query.getResultType())`. This is the single
      most-searched Specification problem. `[TRAP]` `[BUILD]` `[PROVE]`
2.8.8 Spring Data 3.5's `SelectionSpecification`/`DeleteSpecification`/`UpdateSpecification` split
      and `PredicateSpecification` — the newer, cleaner API. Verify names against 3.5.
      `[VERSION-TRAP]` `[RESEARCH]`
2.8.9 QueryDSL: `QuerydslPredicateExecutor<T>` (`findOne(Predicate)`, `findAll(Predicate[, Sort |
      OrderSpecifier | Pageable])`, `count`, `exists`), the `Q`-class annotation processor
      (`com.querydsl:querydsl-apt` with `jakarta` classifier), `JPAQueryFactory`,
      `BooleanBuilder`, `Expressions`, and `@QuerydslPredicate` in a controller. `[API]`
      `[RESEARCH]`
2.8.10 QueryDSL vs Specifications in a table: readability, join handling, projection support
       (`Projections.constructor`), sub-queries, build complexity, maintenance status of the
       project. `[NUM]` `[RESEARCH]`
2.8.11 Query by Example's limits restated (§1.22.13) as the reason it is not an answer here.
2.8.12 Blaze-Persistence and Spring Data's `QueryRewriter` as the escape hatches; native SQL as the
       last resort with a `countQuery`.
2.8.13 The plan-cache cost of dynamic queries: each distinct predicate combination is a distinct
       plan on both Hibernate's side (`hibernate.query.plan_cache_max_size`, default **2048**) and
       the database's. Bound the combinations. `[PROVE]` `[NUM]` `[X-REF 09]`
2.8.14 The pragmatic recommendation: derived methods for ≤3 fixed predicates, `@Query` for a fixed
       complex one, Specifications for genuinely dynamic search, QueryDSL if the team already has
       it, native SQL for reporting. `[PROVE]`

*(14 leaves)*

## §2.9 Keyset pagination and the Scroll API

2.9.1 Why offset pagination degrades: the database must produce and discard `offset` rows, so page
      *n* costs O(n·size). Show the `EXPLAIN` shape. `[PROVE]` `[X-REF 09]`
2.9.2 The second offset problem — **instability**: an insert or delete before your offset shifts every
      subsequent page, so rows are duplicated or skipped. `[PROVE]` `[TRAP]`
2.9.3 Keyset (seek) pagination: `where (created_at, id) < (:lastCreatedAt, :lastId) order by
      created_at desc, id desc limit 20`. Constant cost, stable, index-friendly. `[SQL]` `[PROVE]`
2.9.4 The requirement keyset imposes: a **total order** on a unique tuple, and a matching composite
      index. Without the tiebreaker it silently loses rows. `[TRAP]` `[X-REF 09]`
2.9.5 The row-value comparison and its portability: PostgreSQL supports `(a,b) < (?,?)`, others need
      the expanded `a < ? or (a = ? and b < ?)` form. Show both. `[SQL]` `[RESEARCH]`
2.9.6 What keyset cannot do: jump to page 47, or show a total count. State this as the trade — and
      note that a UI that needs both should reconsider the requirement. `[PROVE]` `[X-REF 12]`
2.9.7 Spring Data's Scroll API: `ScrollPosition`, `OffsetScrollPosition.initial()`,
      `ScrollPosition.keyset()`, `KeysetScrollPosition`, `Window<T>` (`hasNext`,
      `positionAt(index)`, `getContent`), `WindowIterator.of(fn).startingAt(pos)`. `[API]`
      `[RESEARCH]`
2.9.8 The repository signature: `Window<Order> findFirst20ByStatusOrderByCreatedAtDesc(Status s,
      ScrollPosition pos)` — and the fact that the **sort must be part of the method or the query**
      because the keyset predicate is derived from it. `[API]` `[PROVE]`
2.9.9 The known limitation: keyset scrolling with an **interface projection** could not extract
      values from the `Tuple` in earlier 3.x versions. Verify status in 3.5 before recommending it.
      `[TRAP]` `[RESEARCH]`
2.9.10 The hand-rolled alternative when the Scroll API does not fit: a `@Query` with explicit
       `:lastId` parameters and a `Limit`/`Pageable.ofSize`. Ship it. `[BUILD]`
2.9.11 Encoding the cursor for an API: base64 of the ordered tuple, opaque to the client, versioned.
       `[X-REF 12]`
2.9.12 The decision rule: offset for admin screens with page numbers and small tables; keyset for
       feeds, exports, and anything unbounded. `[PROVE]`

*(12 leaves)*

## §2.10 Bulk operations and `@Modifying`

2.10.1 The four ways to change many rows, with statement counts: entity-by-entity through the
       context, JPQL bulk `update`/`delete`, native SQL, `StatelessSession`. `[NUM]`
2.10.2 **`@Modifying` bypasses the persistence context**, preserved from the current guide: no dirty
       checking, no cascades, no `@Version` increment, no lifecycle callbacks, no L2 invalidation,
       and the L1 cache now holds stale entities. `[TRAP]` `[SOURCE]`
2.10.3 `clearAutomatically = true` and `flushAutomatically = true` — what each fixes: the first
       clears L1 *after* so subsequent reads are fresh, the second flushes pending changes *before*
       so the bulk statement sees them. Neither is on by default. `[PROVE]` `[NUM]`
2.10.4 The cost of `clearAutomatically = true`: it detaches **everything**, including entities the
       caller is still holding, so a subsequent `save` becomes a `merge` with a SELECT. Prefer to run
       bulk statements in a transaction that holds nothing. `[TRAP]` `[PROVE]`
2.10.5 `@Version` and bulk updates: the version is **not** bumped, so an optimistic-locking client
       holding an old version will still succeed. Fix: `set version = version + 1` explicitly in the
       JPQL. `[TRAP]` `[SQL]`
2.10.6 L2 and bulk updates: nothing is invalidated. Fix: `Cache.evict(Order.class)` after, or accept
       staleness, or don't use L2. `[TRAP]`
2.10.7 Bulk delete and cascades: children are **not** deleted, so you get orphans or an FK violation.
       Order the statements children-first yourself. `[TRAP]` `[PROVE]`
2.10.8 JPQL bulk update restrictions: no joins in the spec (Hibernate allows some), no `order by`, no
       `limit`. The "update the top 100" query therefore needs a subquery or native SQL. `[TRAP]`
2.10.9 Multi-table bulk operations on an inheritance hierarchy: Hibernate uses a **temporary table**
       (`hibernate.query.mutation_strategy`, `LocalTemporaryTableMutationStrategy`,
       `GlobalTemporaryTableMutationStrategy`, `PersistentTableMutationStrategy`,
       `CteMutationStrategy`, `InlineMutationStrategy`). H2 in 6.6 switched from local to **global**
       temporary tables. `[PROP]` `[VERSION-TRAP]` `[RESEARCH]`
2.10.10 `StatelessSession` for a true bulk path: no context, no snapshots, no cascades, constant
        memory. `insert`, `update`, `delete`, `upsert`, and 7.0's `*Multiple` variants. Show a
        1M-row job. `[BUILD]` `[RESEARCH]`
2.10.11 The genuinely large load: `JdbcTemplate.batchUpdate`, PostgreSQL `COPY`, MySQL
        `LOAD DATA LOCAL INFILE`. Preserve the current guide's advice and add the numbers.
        `[NUM]` `[PROVE]`
2.10.12 Upsert options and their JPA status: `INSERT ... ON CONFLICT` (native or Hibernate 6.5's
        `upsert`), `merge` (a SELECT + INSERT/UPDATE), and a unique constraint plus catch-and-retry.
        `[RESEARCH]`
2.10.13 Chunked processing with a commit per chunk: `TransactionTemplate` in a loop, why
        `@Transactional` on the loop is wrong, and idempotency so a mid-way failure is resumable.
        `[BUILD]` `[X-REF 22]`
2.10.14 Reading a large table without OOM: `Stream` with a fetch size, keyset chunking, or
        `ScrollableResults` — and `clear()` every N rows in all three. `[PROVE]`
2.10.15 The review rule: every `@Modifying` method must state, in a comment or a test, what it does
        to L1, L2, `@Version` and children.

*(15 leaves)*

## §2.11 Statement batching

2.11.1 The problem: 100k `persist` calls in one context means 100k managed entities plus 100k
       snapshots in memory, and a dirty-check pass over all of them at **every** flush — quadratic.
       Preserve the current guide's framing. `[PROVE]` `[SOURCE]`
2.11.2 The `flush()` + `clear()` loop, preserved verbatim, with the `i % 50 == 0` batch boundary and
       an explanation of why both calls are needed. `[SOURCE]` `[BUILD]`
2.11.3 The properties that make JDBC batching actually happen, preserved:
       `hibernate.jdbc.batch_size=50`, `hibernate.order_inserts=true`,
       `hibernate.order_updates=true`. Add `hibernate.jdbc.batch_versioned_data=true` and explain
       each. `[PROP]` `[NUM]` `[SOURCE]`
2.11.4 Why `order_inserts` matters: Hibernate batches only **consecutive** statements against the
       same table, so an interleaved `Order, OrderLine, Order, OrderLine` sequence yields batches of
       one. Ordering groups them. `[PROVE]` `[NUM]`
2.11.5 **Trap, preserved: `GenerationType.IDENTITY` disables insert batching entirely** — Hibernate
       must execute each INSERT immediately to learn the generated key. Use `SEQUENCE` with a pooled
       optimizer (`allocationSize = 50`): one sequence call per 50 rows, and batching works.
       `AUTO` on MySQL resolves to IDENTITY; on Postgres to SEQUENCE. `[TRAP]` `[PROVE]` `[SOURCE]`
2.11.6 The driver half of the story: PostgreSQL needs `reWriteBatchedInserts=true` to turn a JDBC
       batch into a single multi-row `INSERT`; MySQL needs `rewriteBatchedStatements=true`.
       **Without them the batch is still N round trips.** Show the measured difference.
       `[PROP]` `[NUM]` `[TRAP]` `[RESEARCH]`
2.11.7 Batching updates and deletes: same settings, plus the `@Version` interaction
       (`batch_versioned_data` must be true for versioned entities to batch, and the driver must
       report per-statement update counts). `[PROVE]`
2.11.8 What silently disables batching: IDENTITY ids, a `@GeneratedValue` on a non-id column, an
       interleaved query forcing a flush, `@DynamicUpdate` (different SQL per row), a
       `@PreUpdate` that queries, and mixing entity types without ordering. Make this a checklist.
       `[TRAP]`
2.11.9 How to **verify** batching rather than assume it: `hibernate.generate_statistics` and
       `Statistics.getPrepareStatementCount()` vs `getEntityInsertCount()`, or datasource-proxy's
       batch logging. If prepare-count ≈ row-count, batching is off. `[DIAG]` `[PROVE]`
2.11.10 Batch size selection: too small wastes round trips, too large blows the driver's packet limit
        and the transaction's lock footprint. 20–100 as the working range, measured. `[NUM]`
2.11.11 `hibernate.jdbc.fetch_size` on the read side and its dialect-dependence (PostgreSQL needs
        auto-commit off and a fetch size for a server-side cursor). `[PROP]` `[X-REF 09]`
2.11.12 The interaction with transaction length and locks: a 100k-row batch in one transaction holds
        100k row locks and a huge undo/redo footprint. Chunk into transactions. `[PROVE]`
        `[X-REF 09]`
2.11.13 For genuinely large loads, skip JPA — preserved from the current guide. `[SOURCE]`

*(13 leaves)*

## §2.12 Transactions in practice and open-session-in-view

2.12.1 The boundary decision restated with the three candidate layers and what each costs:
       repository (no atomicity), service (correct), controller (a connection held through
       serialisation). `[SOURCE]` `[PROVE]`
2.12.2 Mark read paths `@Transactional(readOnly = true)`: skips dirty checking (flush mode `MANUAL`),
       flags the JDBC connection, may route to a replica. Preserve from the current guide and add
       the §1.6.17 caveat. `[SOURCE]`
2.12.3 **Open Session In View**, preserved and expanded: `spring.jpa.open-in-view`, **default
       `true`** in Boot, implemented by `OpenEntityManagerInViewInterceptor` (MVC) /
       `OpenEntityManagerInViewFilter`. The four reasons to turn it off, preserved verbatim:
       lazy loads fire during JSON serialisation (N+1 in the rendering path, invisible in service
       tests); a DB connection is held for the entire request including slow client writes → pool
       exhaustion; those queries run outside any transaction, each in its own auto-commit; and it
       hides the design error of entities escaping the service layer. `[SOURCE]` `[TRAP]` `[NUM]`
2.12.4 The startup warning Boot logs (`spring.jpa.open-in-view is enabled by default...`) and why it
       exists — preserve the current guide's closing sentence. `[DIAG]` `[SOURCE]`
2.12.5 The migration recipe: set it to `false`, run the test suite, fix each
       `LazyInitializationException` with a fetch plan or a DTO, and you have a correct application.
       Preserve. `[SOURCE]` `[PROVE]`
2.12.6 The counter-argument to be fair about: OSIV makes prototyping fast and is survivable on a
       low-traffic internal app. State the condition under which it is defensible, then the
       condition under which it is not. `[PROVE]`
2.12.7 The connection-holding arithmetic: with `maximum-pool-size=10` and a 200 ms request, OSIV
       caps you near 50 rps *per instance* and turns any slow client into pool exhaustion. Show the
       Little's-law calculation. `[NUM]` `[PROVE]` `[X-REF 09]`
2.12.8 `hibernate.connection.provider_disables_autocommit=true` + `spring.datasource.hikari.
       auto-commit=false` — **delayed connection acquisition**: without it, the connection is taken
       at transaction start (Hibernate must inspect auto-commit); with it, at the first statement.
       This shortens lease time and raises throughput. Both settings are required together, and
       setting only the Hibernate one runs your SQL **outside a transaction**. `[PROP]` `[PROVE]`
       `[TRAP]` `[RESEARCH]`
2.12.9 `REQUIRES_NEW` for an audit row, worked: two connections held at once, the pool arithmetic,
       and the deadlock risk against the suspended outer transaction's locks. The alternatives —
       an `AFTER_COMMIT` listener, an outbox row in the same transaction, or a log line.
       `[PROVE]` `[X-REF 07]`
2.12.10 The catch-and-continue trap in JPA terms: catching an exception inside a `@Transactional`
        method leaves the context in an **undefined state** (Hibernate marks the transaction for
        rollback on many exceptions), so continuing to use the `EntityManager` is unsupported and
        commit throws. `[TRAP]` `[PROVE]` `[X-REF 07]`
2.12.11 `UnexpectedRollbackException`'s JPA flavour: an inner `REQUIRED` method threw, the outer
        caught it, and commit fails because the transaction was already marked rollback-only.
        `[DIAG]` `[X-REF 07]`
2.12.12 Long transactions as the root operational sin: they hold a connection, hold locks, grow the
        context, delay vacuum/undo cleanup, and time out mid-write. Never call an HTTP API inside
        one. `[PROVE]` `[X-REF 09]`
2.12.13 The read-your-own-writes question: within a transaction, `find` sees your unflushed change
        (L1), a JPQL query sees it (auto-flush), a native query does not (§1.7.4), and another
        transaction sees nothing until commit. Four answers, one question. `[PROVE]`
2.12.14 Testing transactional behaviour: `@Transactional` on a test rolls back, so `AFTER_COMMIT`
        listeners never fire and the database is never actually written. `TestTransaction`,
        `@Commit`, or a `TransactionTemplate` in the test. `[TRAP]` `[X-REF 16]`

*(14 leaves)*

## §2.13 Concurrency and locking in practice

2.13.1 The lost-update walkthrough with two threads, a `@Version` column, and the exact SQL each
       thread emits — the canonical whiteboard question. `[SQL]` `[PROVE]`
2.13.2 The retry loop done properly: `@Retryable` (Spring Retry) or a manual loop, **outside** the
       transaction, with jittered backoff, a max attempt count, and idempotent business logic. Ship
       it. `[BUILD]` `[SOURCE]`
2.13.3 Why the retry must re-read: the detached entity's version is stale, so re-applying the same
       object retries the same conflict forever. `[PROVE]` `[TRAP]`
2.13.4 When optimistic retry is the wrong answer: a hot counter under constant contention retries
       forever. Then: pessimistic lock, an atomic `update ... set n = n + 1` bulk statement, sharded
       counters, or move it out of the database. `[PROVE]` `[X-REF 22]`
2.13.5 The atomic-decrement pattern for stock: `@Modifying @Query("update Item set stock = stock - 1
       where id = :id and stock > 0")` returning `int`, checked for `1`. No locking, no retry, no
       lost update. Present it as the answer interviewers want. `[SQL]` `[PROVE]`
2.13.6 The job-queue pattern with `SKIP LOCKED` in Spring Data: `@Lock(PESSIMISTIC_WRITE)` plus
       `@QueryHints(@QueryHint(name = "jakarta.persistence.lock.timeout", value = "-2"))`.
       `[BUILD]` `[NUM]` `[RESEARCH]`
2.13.7 Idempotency keys as the alternative to locking for external requests. `[X-REF 12]`
2.13.8 Two concurrent `merge`s of the same detached entity, and why the second silently overwrites
       without a `@Version`. `[PROVE]`
2.13.9 Insert-race handling: catch `DataIntegrityViolationException` on a unique constraint and treat
       it as "already exists" rather than pre-checking with `existsBy` (which is a TOCTOU race).
       `[PROVE]` `[TRAP]`
2.13.10 Isolation-level interaction with the L1 cache, restated as a testable claim: under
        `READ_COMMITTED`, two `find` calls for the same id in one transaction return the same
        instance and never re-read — so JPA gives you repeatable reads the database does not
        promise. `refresh()` is the only way out. `[PROVE]` `[TRAP]` `[X-REF 09]`
2.13.11 The thread-safety statement: `EntityManagerFactory` is thread-safe, `EntityManager`/`Session`
        and every managed entity are **not**. Passing an entity between threads is a data race.
        `[PROVE]` `[X-REF 05]`
2.13.12 Virtual threads and JPA: the `EntityManager` is bound to the thread via `ThreadLocal`, which
        works with virtual threads, but the connection pool becomes the bottleneck and pinning was a
        concern in older drivers. `spring.threads.virtual.enabled=true` and what to measure.
        `[RESEARCH]` `[X-REF 04]` `[X-REF 05]`
2.13.13 `@Async` + repository: no transaction, no `EntityManager`, detached everything. The correct
        pattern is to pass ids, not entities. `[TRAP]` `[X-REF 07]`

*(13 leaves)*

## §2.14 Caching decisions

2.14.1 The decision procedure: is the data immutable? is it read-mostly? is the read path hot? do you
       control every writer? is the deployment single-instance? Only "yes" to the last two makes L2
       safe. `[PROVE]`
2.14.2 The three-layer choice in a table: L1 (free, automatic), L2 (entity-level, invalidation-hard),
       application cache (explicit keys and TTL, DTO-shaped), plus HTTP caching and a materialised
       read model. `[NUM]` `[X-REF 15]`
2.14.3 The clustered-L2 option: Infinispan/Hazelcast replicated or invalidation mode, and the cost
       (network chatter on every write, split-brain semantics). `[X-REF 15]`
2.14.4 Why an application-level cache of **DTOs** beats L2 for most read paths: one key, one TTL, one
       invalidation point, no proxies, no detached entities, and it caches the *result* not the
       *entity*. `[PROVE]`
2.14.5 The natural-id cache as the underrated middle ground: cache `email → id` and let L1/L2 handle
       the entity. `[PROVE]`
2.14.6 The measurement discipline: `hibernate.generate_statistics`, hit/miss/put ratios per region,
       and a rule (below ~80% hit rate, a cache is usually costing you). `[NUM]` `[DIAG]`
2.14.7 Cache-related staleness incidents to name: a bulk update, a DBA fix, a second service, a
       Flyway data migration, a rolling deploy with two versions of the mapping. `[TRAP]`
2.14.8 `@Cacheable` on a repository method: it caches the **entity instance**, which is then detached
       and shared across threads — a data race plus `LazyInitializationException`. Cache in the
       service, on DTOs. `[TRAP]` `[X-REF 15]`

*(8 leaves)*

## §2.15 The connection pool and JPA

2.15.1 The chain of ownership: HikariCP holds `Connection`s; Spring's
       `DataSourceTransactionManager`/`JpaTransactionManager` binds one to the thread; Hibernate's
       `LogicalConnection` uses it; the `EntityManager` wraps that. Four layers, one connection.
       `[FLOW]`
2.15.2 When the connection is acquired and released, per `ConnectionAcquisitionMode` /
       `PhysicalConnectionHandlingMode` (`IMMEDIATE_ACQUISITION_AND_HOLD`,
       `DELAYED_ACQUISITION_AND_HOLD`, `DELAYED_ACQUISITION_AND_RELEASE_AFTER_TRANSACTION`,
       `DELAYED_ACQUISITION_AND_RELEASE_AFTER_STATEMENT`). Spring forces hold-until-transaction-end.
       `[API]` `[NUM]` `[RESEARCH]`
2.15.3 The delayed-acquisition setting from §2.12.8 restated as a pool-throughput lever with numbers.
       `[NUM]`
2.15.4 Pool sizing for a JPA app: `maximum-pool-size` default **10**, the
       `connections = cores × 2 + effective_spindles` heuristic, and why a bigger pool usually makes
       things worse. `[NUM]` `[X-REF 09]`
2.15.5 `HikariPool-1 - Connection is not available, request timed out after 30000ms` — read the
       trace, and the five causes: OSIV, `REQUIRES_NEW`, a long transaction, a leak, and a
       `Stream`/`ScrollableResults` never closed. `[DIAG]` `[TRAP]`
2.15.6 `leak-detection-threshold` and how it names the offending stack. `[PROP]` `[DIAG]`
2.15.7 `spring.datasource.hikari.auto-commit=false`'s interaction with everything: JPA is fine,
       `JdbcTemplate` outside a transaction now needs an explicit commit, and Flyway has its own
       connection. `[TRAP]`
2.15.8 Two pools, one database (read-write and read-only replicas), `AbstractRoutingDataSource`,
       `@Transactional(readOnly = true)` as the routing signal, and the replica-lag hazard.
       `[BUILD]` `[X-REF 09]` `[X-REF 22]`
2.15.9 `hikaricp.connections.*` Micrometer metrics (`active`, `idle`, `pending`, `usage`,
       `acquire`, `timeout`) as the dashboard that catches §2.15.5 before it pages you.
       `[X-REF 20]`
2.15.10 Statement caching: HikariCP does not cache statements (it delegates to the driver);
        `cachePrepStmts`/`prepStmtCacheSize` on MySQL, `prepareThreshold` on PostgreSQL. What
        Hibernate's own `PreparedStatement` reuse does and does not do. `[PROP]` `[RESEARCH]`

*(10 leaves)*

## §2.16 Auditing

2.16.1 Spring Data JPA auditing: `@EnableJpaAuditing`, `AuditingEntityListener`, and the four
       annotations `@CreatedDate`, `@LastModifiedDate`, `@CreatedBy`, `@LastModifiedBy`. `[API]`
2.16.2 The wiring: `@EntityListeners(AuditingEntityListener.class)` on the entity (or on a
       `@MappedSuperclass`), plus an `AuditorAware<String>` bean reading
       `SecurityContextHolder`. Ship the `@MappedSuperclass`. `[BUILD]` `[RESEARCH]`
2.16.3 `@EnableJpaAuditing`'s attributes: `auditorAwareRef`, `setDates`, `modifyOnCreate`,
       `dateTimeProviderRef`. `[API]` `[RESEARCH]`
2.16.4 The `DateTimeProvider` / `Clock` injection point that makes auditing testable. `[BUILD]`
       `[X-REF 16]`
2.16.5 The Hibernate-native alternative: `@CreationTimestamp` / `@UpdateTimestamp` (and 6.x's
       `source = SourceType.DB` for database time). Note they are Hibernate, not JPA. `[API]`
2.16.6 The database-native alternative: `default now()` plus a trigger — the only one that also
       covers writers who bypass the application. `[PROVE]`
2.16.7 The three fail cases of listener-based auditing: bulk `@Modifying` updates,
       `deleteAllInBatch`, and a native SQL write. All three leave `lastModifiedDate` stale.
       `[TRAP]`
2.16.8 Hibernate Envers: `@Audited`, the `_AUD` tables and `REVINFO`, `RevisionEntity`,
       `AuditReader`/`AuditQuery`, Spring Data's `RevisionRepository<T,ID,N>`
       (`findLastChangeRevision`, `findRevisions`, `findRevision`), and `@NotAudited`. `[API]`
       `[RESEARCH]`
2.16.9 Envers' costs: a second write per change, table bloat, schema coupling on every mapping
       change, and no help for bulk statements. When it is right (regulated change history) and when
       an append-only event table is better. `[PROVE]`
2.16.10 The event-sourcing / outbox alternative for audit-as-a-business-requirement. `[X-REF 14]`
2.16.11 Soft delete as an audit-adjacent concern: `@SoftDelete` (§1.9.26) versus a `deleted_at`
        column plus `@SQLRestriction`, and the four things soft delete breaks — unique constraints,
        FK integrity, index selectivity, and every `count`. `[TRAP]` `[PROVE]`

*(11 leaves)*

## §2.17 Multi-tenancy

2.17.1 The three tenancy models and their isolation/cost trade: **database per tenant**,
       **schema per tenant**, **discriminator column** (shared everything). `[NUM]` `[PROVE]`
2.17.2 Hibernate's support surface: `hibernate.multiTenancy` (`DATABASE` / `SCHEMA` / `DISCRIMINATOR`,
       and in 6.x the setting is effectively inferred), `hibernate.tenant_identifier_resolver`,
       `hibernate.multi_tenant_connection_provider`. `[PROP]` `[RESEARCH]`
2.17.3 `CurrentTenantIdentifierResolver<T>`: `resolveCurrentTenantIdentifier()` and
       `validateExistingCurrentSessions()`, backed by a `ThreadLocal` tenant context set by a
       filter. Ship both. `[API]` `[BUILD]` `[RESEARCH]`
2.17.4 `MultiTenantConnectionProvider<T>` /
       `AbstractDataSourceBasedMultiTenantConnectionProviderImpl.selectDataSource(tenantId)` and
       `getAnyConnection()` — the second method is what `ddl-auto` and startup use, and forgetting it
       breaks boot. `[API]` `[TRAP]` `[RESEARCH]`
2.17.5 The Spring integration and its friction: Boot does not auto-configure multi-tenancy, so you
       build the `LocalContainerEntityManagerFactoryBean` yourself; the Spring blog post is the
       canonical recipe. Note the known Spring Data issue where the `SessionFactory` cannot be
       created without a tenant at startup. `[RESEARCH]` `[TRAP]`
2.17.6 `@TenantId` (Hibernate 6.0+) — the discriminator field annotation that makes Hibernate add the
       tenant predicate automatically and populate it on insert. Much better than a hand-rolled
       `@Filter`. `[API]` `[RESEARCH]` `[VERSION-TRAP]`
2.17.7 The discriminator model's failure mode: one missing `where tenant_id = ?` is a cross-tenant
       data leak. Enforcement options: `@TenantId`, a `@Filter` enabled in an interceptor, database
       row-level security, and a test that asserts every query carries the predicate. `[TRAP]`
       `[X-REF 13]`
2.17.8 Migrations under multi-tenancy: Flyway per schema/database, the loop, and the "1000 tenants ×
       one migration" operational problem. `[PROVE]`
2.17.9 L2 caching under multi-tenancy: cache keys include the tenant identifier — verify, because
       getting this wrong is also a data leak. `[TRAP]` `[RESEARCH]`
2.17.10 Connection pooling under database-per-tenant: N pools × M connections, and why schema-per-
        tenant with one pool scales further. `[NUM]` `[PROVE]`

*(10 leaves)*

## §2.18 Bytecode enhancement

2.18.1 What it is: a build-time (or agent-time) rewrite of your entity classes so that field access
       is intercepted, rather than relying on a proxy subclass. `[PROVE]`
2.18.2 The four capabilities it enables: **lazy basic attributes** (`@Basic(fetch = LAZY)`,
       `@LazyGroup`), **lazy `*ToOne` without a proxy** (so `instanceof` and `getClass` work),
       **in-line dirty tracking** (no snapshot comparison — the entity records its own changes), and
       **association management** (auto-maintaining both sides). `[API]` `[PROVE]`
2.18.3 The Gradle/Maven plugin configuration: `org.hibernate.orm` Gradle plugin or
       `hibernate-enhance-maven-plugin` with `enableLazyInitialization`,
       `enableDirtyTracking`, `enableAssociationManagement`. `[API]` `[RESEARCH]`
2.18.4 What in-line dirty tracking buys: flush cost drops from O(fields × entities) to O(changed
       fields), which matters at 10k+ managed entities. Show the arithmetic. `[NUM]` `[PROVE]`
2.18.5 What it costs: a build step, harder debugging, class-file divergence from source, and the
       Hibernate 6.0 note that **the enhanced bytecode format changed and applications must
       re-run enhancement**. `[VERSION-TRAP]` `[RESEARCH]`
2.18.6 `hibernate.bytecode.use_reflection_optimizer` — default flipped to **true** and deprecated for
       removal. Not the same thing as enhancement. `[PROP]` `[VERSION-TRAP]` `[RESEARCH]`
2.18.7 Runtime enhancement via a `-javaagent` and why nobody does it any more.
2.18.8 The honest recommendation: skip enhancement unless you have measured a dirty-checking or
       lazy-column problem; the lazy `*ToOne`-without-proxy benefit is better obtained with
       `@MapsId` and DTOs. `[PROVE]`
2.18.9 ByteBuddy vs Javassist as the proxy/enhancement library — Hibernate 5.3+ defaults to
       ByteBuddy, `hibernate.bytecode.provider` was the switch, Javassist support is gone.
       `[VERSION-TRAP]` `[RESEARCH]` `[X-REF 06]`

*(9 leaves)*

## §2.19 Testing the persistence layer

2.19.1 The four levels and what each catches: a pure unit test of a mapper (no JPA), a
       `@DataJpaTest` against a real database, a full `@SpringBootTest` slice, and a schema-drift
       check. `[NUM]` `[X-REF 16]`
2.19.2 `@DataJpaTest`: what it auto-configures (JPA, repositories, `TestEntityManager`), what it
       replaces (an embedded database, unless `@AutoConfigureTestDatabase(replace = NONE)`), and
       that it is **`@Transactional` and rolls back** by default. `[API]` `[NUM]`
2.19.3 **Trap: H2 is not your database.** Different SQL dialect, different constraint semantics,
       different sequence behaviour, different type coercion, no `SKIP LOCKED` parity, no JSONB.
       Every H2-only test is a false negative. `[TRAP]` `[PROVE]`
2.19.4 Testcontainers as the fix: `@Testcontainers`, `@Container static PostgreSQLContainer`,
       `@ServiceConnection` (Boot 3.1+) instead of `@DynamicPropertySource`, reuse and
       `singleton container` patterns for suite speed. `[API]` `[RESEARCH]` `[X-REF 16]`
2.19.5 `TestEntityManager`: `persistAndFlush`, `persistFlushFind`, `find`, `flush`, `clear`,
       `detach`, `getId`. Its purpose is to let a test **clear the context** so the next read is a
       real read. `[API]` `[PROVE]`
2.19.6 The most important pattern in JPA testing: `flush()` + `clear()` between the write and the
       assertion. Without it you are asserting against L1 and the test passes even when the mapping
       is broken. `[TRAP]` `[PROVE]`
2.19.7 The query-count assertion (§2.2.6) as a first-class test, and where to put the budget.
       `[BUILD]`
2.19.8 Asserting on generated SQL: `@Sql` for fixtures, `hibernate.generate_statistics`,
       datasource-proxy's `assertSelectCount`, or a `StatementInspector`. `[API]` `[RESEARCH]`
2.19.9 The schema-drift test: Flyway-migrate a Testcontainer, boot with `ddl-auto=validate`, fail on
       mismatch. Highest value per line of test code in the whole guide. `[BUILD]` `[PROVE]`
2.19.10 Testing optimistic locking: two `EntityManager`s, or a `TransactionTemplate` in two threads,
        asserting `ObjectOptimisticLockingFailureException`. `[BUILD]`
2.19.11 Testing lazy loading: a test that asserts `LazyInitializationException` **is** thrown outside
        the transaction, so the fetch plan is pinned by a test rather than by a comment. `[BUILD]`
        `[PROVE]`
2.19.12 `@Transactional` on a test rolls back, so `AFTER_COMMIT` listeners and real constraint timing
        are not exercised — the `@Commit` / `TestTransaction` / non-transactional-test escape hatches.
        `[TRAP]` `[X-REF 16]`
2.19.13 Test data builders over `@Sql` dumps, and why a shared `data.sql` becomes unmaintainable.
2.19.14 `@DirtiesContext` and the context cache: one property difference per test class spawns a new
        `EntityManagerFactory` and multiplies suite time. `[X-REF 07]` `[X-REF 16]`

*(14 leaves)*

## §2.20 Observability of the persistence layer

2.20.1 The four questions to instrument: how many statements per request, how long each takes, how
       many connections are in use, and how big the persistence context gets. `[PROVE]`
2.20.2 `hibernate.generate_statistics=true` and the `Statistics` surface:
       `getQueryExecutionCount`, `getQueryExecutionMaxTime`, `getQueryExecutionMaxTimeQueryString`,
       `getPrepareStatementCount`, `getEntityLoadCount`, `getEntityInsertCount`/`UpdateCount`/
       `DeleteCount`, `getCollectionLoadCount`, `getSecondLevelCacheHitCount`/`MissCount`/`PutCount`,
       `getQueryCacheHitCount`, `getFlushCount`, `getTransactionCount`,
       `getSuccessfulTransactionCount`, `getSessionOpenCount`, `getOptimisticFailureCount`.
       `[API]` `[PROP]` `[RESEARCH]`
2.20.3 The cost of statistics (a few percent) and the recommendation (on in staging and in tests,
       sampled in production).
2.20.4 The **slow query log**: `hibernate.log_slow_query=<ms>` (Hibernate 5.4.5+; also
       `hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS`), logged at INFO to
       `org.hibernate.SQL_SLOW`. The single cheapest production diagnostic here. `[PROP]`
       `[DIAG]` `[RESEARCH]`
2.20.5 The logger matrix from §1.31.5 with what each shows and its cost. `[DIAG]`
2.20.6 datasource-proxy vs p6spy vs `spring-boot-data-source-decorator`: per-query timing, bind
       parameters, batch grouping, duplicate detection, slow-query callbacks, and query-count
       assertions in tests. Pick one and say why. `[NUM]` `[RESEARCH]`
2.20.7 `StatementInspector` (`hibernate.session_factory.statement_inspector`) as the in-process hook
       for tagging or counting SQL without a proxy datasource. `[API]` `[BUILD]`
2.20.8 Micrometer metrics that matter: `hibernate.*` (via `HibernateMetrics` /
       `management.metrics.enable.hibernate`), `hikaricp.connections.*`, `jdbc.connections.*`, and
       per-endpoint statement counts as a custom metric. `[API]` `[RESEARCH]` `[X-REF 20]`
2.20.9 Distributed tracing: the JDBC/Hibernate spans Micrometer Tracing produces, and how a
       trace waterfall makes N+1 visually obvious. `[X-REF 20]`
2.20.10 `@Meta(comment = ...)` + `hibernate.use_sql_comments` so `pg_stat_statements` and the DBA's
        slow-query report attribute SQL back to a method name. `[PROP]` `[PROVE]`
2.20.11 The database side: `pg_stat_statements`, `EXPLAIN (ANALYZE, BUFFERS)`, `auto_explain`, and
        the MySQL `performance_schema` equivalents. `[X-REF 09]`
2.20.12 A concrete diagnostic runbook for "the endpoint got slow": statement count → slow query log →
        `EXPLAIN` → pool metrics → heap. `[FLOW]` `[DIAG]`

*(12 leaves)*

## §2.21 Version history and the stale-answer sweep

2.21.1 The `javax` → `jakarta` boundary and everything it invalidated. `[VERSION-TRAP]`
2.21.2 Hibernate 6.0's four headline changes and why each matters to you: **SQM** (Criteria and HQL
       share one tree; SQL is generated from it rather than from a string), the **new type system**
       (`JavaType`/`JdbcType`), **read-by-position** instead of read-by-name in the result-set
       reader, and the removal of the legacy `Criteria` API. `[RESEARCH]` `[VERSION-TRAP]`
2.21.3 Hibernate 6.x per-minor deltas worth naming: 6.2 CTEs and `@SQLRestriction`; 6.3
       `@SQLOrder`; 6.4 `@SoftDelete`, `@EmbeddedColumnNaming`; 6.5 `@GenericGenerator` deprecated,
       `upsert`; 6.6 embeddable inheritance, versioned-merge `OptimisticLockException`,
       H2 global temp tables, `Expression.as()` narrowing, `array_includes`, Oracle array naming.
       `[VERSION-TRAP]` `[RESEARCH]`
2.21.4 Hibernate 7.0's removal list as a migration checklist (the full list from the header) and the
       two behaviour changes most likely to bite: `StatelessSession` using L2, and `@MapsId` losing
       its implicit `PERSIST` cascade. `[VERSION-TRAP]` `[RESEARCH]`
2.21.5 Spring Data JPA deltas: 2.5 `getOne` deprecated; 2.7 `getById` deprecated,
       `getReferenceById` added; 3.0 `ListCrudRepository`, the `PagingAndSortingRepository` split,
       Jakarta; 3.1 `@ServiceConnection`-friendly testing; 3.2 `Limit`, scroll refinements;
       3.4 `@NativeQuery`; 3.5 the specification API split; 4.0 AOT repositories, JSpecify, vector
       search. `[VERSION-TRAP]` `[RESEARCH]`
2.21.6 Spring Boot deltas that change JPA behaviour: 2.0 HikariCP default; 2.5 `spring.sql.init.*`
       replacing `spring.datasource.initialization-*`; 3.0 Jakarta + Hibernate 6; 3.1
       `@ServiceConnection`; 3.3 the `PageImpl` serialisation warning and `PagedModel`; 3.4/3.5
       Hibernate 6.6. `[VERSION-TRAP]` `[RESEARCH]`
2.21.7 The stale-answer sweep list — fifteen claims a candidate is likely to repeat that are now
       wrong: "`@GenericGenerator` is how you do pooled-lo", "`AUTO` uses a single
       `hibernate_sequence`", "use `session.save()`", "`@Where` for soft delete", "Criteria means
       `Restrictions.eq`", "`getOne` is the lazy getter", "`@LazyCollection(EXTRA)` for `size()`",
       "`hibernate.hbm2ddl.auto=update` is fine in prod", "`@MockBean` for the repository",
       "`javax.persistence`", "`passDistinctThrough` fixes duplicates", "HQL cannot do window
       functions", "`@ManyToMany` is fine", "`spring.jpa.show-sql` shows parameters", and
       "`open-in-view` is off by default". `[VERSION-TRAP]` `[TRAP]`

*(7 leaves)*

## §2.22 The anti-pattern catalogue

2.22.1 Entities in the web layer (and therefore OSIV, N+1 in serialisation, mass assignment).
2.22.2 `EAGER` everywhere as an N+1 "fix".
2.22.3 `CascadeType.ALL` on every association including `@ManyToOne`.
2.22.4 Bidirectional associations mapped for symmetry rather than because you navigate both ways.
2.22.5 `@ManyToMany` where a join entity belongs.
2.22.6 `@Data` / `@EqualsAndHashCode` / `@ToString` on entities.
2.22.7 A `List<Child>` on an aggregate with unbounded growth (an `Order` with 2M `AuditRow`s).
2.22.8 `findAll()` on a large table, in any form.
2.22.9 `Page<Entity>` returned from a controller.
2.22.10 `open-in-view=true` left at the default.
2.22.11 `ddl-auto=update` in production.
2.22.12 `enable_lazy_load_no_trans=true`.
2.22.13 L2 enabled "for performance" in a multi-instance deployment.
2.22.14 The query cache enabled without measuring.
2.22.15 `@Transactional` on the controller, or on the repository, or nowhere.
2.22.16 `@Transactional` around an HTTP call.
2.22.17 A transaction per row in a batch job, or one transaction for a million rows.
2.22.18 `IDENTITY` ids plus a configured `batch_size` (batching silently off).
2.22.19 `allocationSize` mismatched with the sequence's `INCREMENT BY`.
2.22.20 Random UUID primary keys on a high-insert table.
2.22.21 `@Enumerated` left at `ORDINAL`.
2.22.22 `LocalDateTime` for an event timestamp.
2.22.23 `double` for money.
2.22.24 Soft delete without accounting for unique constraints and counts.
2.22.25 Catching `OptimisticLockException` and ignoring it.
2.22.26 Pre-checking with `existsBy` instead of catching the constraint violation.
2.22.27 `@Modifying` without `clearAutomatically`, then reading the same entities.
2.22.28 A `Specification` with a `fetch` that breaks the count query.
2.22.29 `Sort` on a native query, expected to work.
2.22.30 Interface projections with `@Value` everywhere, expecting a narrow select.
2.22.31 A `Stream` repository method never closed.
2.22.32 H2 as the only test database.
2.22.33 `@DataJpaTest` assertions without `flush()`/`clear()`.
2.22.34 `@Async` or a new thread handed a managed entity.
2.22.35 An entity cached in a `@Cacheable` or a static map.
2.22.36 Publishing a Kafka event from `@PostPersist`.
2.22.37 Mixing `JdbcTemplate` writes and JPA reads without a flush.
2.22.38 Building JPQL by string concatenation.
2.22.39 `JpaSort.unsafe` with a request parameter.
2.22.40 Two hundred repositories, no service layer, transactions per call.
2.22.41 A 40-line derived method name.
2.22.42 `nativeQuery = true` with no test, so the failure is at request time.
2.22.43 Entities with 60 columns because "it is one table".
2.22.44 No index behind the association you fetch by, so the fixed N+1 is still slow. `[X-REF 09]`
2.22.45 Believing the ORM removed the need to read SQL.

*(45 leaves)*

## §2.23 When not to use JPA at all

2.23.1 The five workloads JPA is wrong for: bulk ETL, reporting/analytics, anything with window
       functions and no entity, high-throughput writes to a single table, and CQRS read models.
       `[PROVE]`
2.23.2 The migration path off it, incrementally: introduce `JdbcClient`/jOOQ for reads first, keep
       JPA for the write model. Both can share the transaction. `[PROVE]`
2.23.3 Spring Data JDBC as the "JPA without the state machine" option: aggregate roots, no lazy
       loading, no dirty checking, explicit `save` semantics, and its consequences (full-aggregate
       writes). `[RESEARCH]`
2.23.4 jOOQ's positioning: typesafe SQL from the schema, no entities, excellent for reporting; the
       licensing consideration for commercial databases. `[RESEARCH]`
2.23.5 `JdbcClient` (Spring 6.1+) as the modern `JdbcTemplate`, and why it is now a serious default
       for read paths. `[API]` `[RESEARCH]`
2.23.6 The honest summary for an interview: "I use JPA for the transactional write model and SQL for
       everything else, and I can defend the boundary." `[PROVE]`

*(6 leaves)*

---

**PART 2 total: 10+16+14+11+11+11+10+14+12+15+13+14+13+8+10+11+10+9+14+12+7+45+6 = 316 leaves**

---

# PART 3 — UNDER THE HOOD

Every leaf in this part names a real class in `org.hibernate.*`, `org.springframework.orm.jpa.*` or
`org.springframework.data.jpa.*`. The write pass must open the class on the **6.6** / **3.5** branch
and quote the relevant method before asserting any field name, constant or call order. Where this
syllabus states a name from recall it is tagged `[RESEARCH]`.

## §3.1 Bootstrap internals — from metadata to `SessionFactoryImpl`

3.1.1 The bootstrap sequence in order: `BootstrapServiceRegistryBuilder` →
      `StandardServiceRegistryBuilder` → `MetadataSources.addAnnotatedClass(...)` →
      `MetadataBuilder` → `InFlightMetadataCollector` → `Metadata` →
      `SessionFactoryBuilder` → `SessionFactoryImpl`. `[FLOW]` `[SOURCE]` `[RESEARCH]`
3.1.2 The `ServiceRegistry` as Hibernate's own DI container: `Service`, `ServiceInitiator`,
      `ServiceContributor`, and the services you might replace (`ConnectionProvider`,
      `JdbcServices`, `Dialect`, `RegionFactory`, `JtaPlatform`, `BeanContainer`). `[API]`
      `[RESEARCH]`
3.1.3 `SpringBeanContainer` as the `BeanContainer` implementation that lets Hibernate resolve
      `@Converter`s, entity listeners and `IdentifierGenerator`s from the Spring context. This is
      the leaf that explains "why is my `@Autowired` null in a converter". `[API]` `[TRAP]`
      `[X-REF 07]`
3.1.4 Hibernate 7's **Hibernate Models** layer replacing the old annotation-reading code, and why the
      change was made (a mapping model independent of reflection, for build-time processing).
      `[VERSION-TRAP]` `[RESEARCH]`
3.1.5 The **`Dialect`**: what it actually supplies — the identity/sequence support flags, the
      `LimitHandler`, the SQL function registry, the type mappings, the lock-hint strings, and the
      temp-table strategy. Naming one is a 40-method class, not a string. `[API]` `[SOURCE]`
3.1.6 Dialect auto-detection via `DatabaseMetaData` versus `spring.jpa.database-platform`, and why
      the version-specific dialects (`PostgreSQLDialect` with a `DatabaseVersion`) replaced the old
      `PostgreSQL95Dialect` family in 6.x. `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
3.1.7 The `EntityPersister` (`SingleTableEntityPersister`, `JoinedSubclassEntityPersister`,
      `UnionSubclassEntityPersister`) — one per entity, holding the pre-generated SQL for insert,
      update, delete and load-by-id. This is where the "SQL is pre-generated at startup" fact lives.
      `[API]` `[SOURCE]` `[PROVE]`
3.1.8 The `CollectionPersister` (`OneToManyPersister`, `BasicCollectionPersister`) and the SQL it
      pre-generates for recreate/remove/update/insert-row/delete-row. `[API]`
3.1.9 `EntityMetamodel`, `Type[] propertyTypes`, `boolean[] propertyUpdateability`,
      `propertyNullability`, `propertyVersionability` — the arrays that dirty checking and SQL
      generation index into. `[SOURCE]` `[RESEARCH]`
3.1.10 What `ddl-auto` runs and when: `SchemaManagementToolCoordinator`,
       `SchemaCreatorImpl`/`SchemaValidatorImpl`/`SchemaMigratorImpl`, and the fact that `update`
       reads `DatabaseMetaData` and diffs — which is why it cannot know about renames. `[SOURCE]`
       `[PROVE]` `[RESEARCH]`
3.1.11 The startup cost breakdown to state with numbers: annotation scan, persister construction,
       proxy class generation, SQL string generation, and validation round trips. `[NUM]`
3.1.12 `Integrator` / `IntegratorProvider` as the supported hook for registering event listeners at
       bootstrap. `[API]`

*(12 leaves)*

## §3.2 `StatefulPersistenceContext` — the actual data structures

3.2.1 The class: `org.hibernate.engine.internal.StatefulPersistenceContext`, reached via
      `SessionImpl.getPersistenceContextInternal()`. Quote its field declarations. `[SOURCE]`
      `[RESEARCH]`
3.2.2 The core maps, by name and purpose: `entitiesByKey` (`EntityKey` → entity),
      `entitiesByUniqueKey`, `entityEntryContext` (entity → `EntityEntry`), `proxiesByKey`,
      `collectionsByKey`, `collectionEntries`, `arrayHolders`, `nullifiableEntityKeys`,
      `entitySnapshotsByKey`, `parentsByChild`, `unownedCollections`. `[SOURCE]` `[NUM]`
      `[RESEARCH]`
3.2.3 `EntityKey` = `(identifier, EntityPersister)` with `equals`/`hashCode` over the identifier and
      the root entity name. This is the identity map's key, and it is why two contexts give two
      instances. `[SOURCE]` `[PROVE]`
3.2.4 `EntityEntry` — the per-entity bookkeeping record. Its fields, named: `status`
      (`Status.MANAGED`/`READ_ONLY`/`DELETED`/`GONE`/`LOADING`/`SAVING`), `previousStatus`,
      `loadedState` (**the snapshot `Object[]`**), `id`, `version`, `lockMode`,
      `existsInDatabase`, `persister`, `entityKey`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.2.5 `EntityEntryContext` and the `ManagedEntity` interface: with bytecode enhancement the
      `EntityEntry` is stored **on the entity itself** (an intrusive linked list) instead of in an
      `IdentityHashMap` — a real allocation win at scale. `[PROVE]` `[RESEARCH]`
3.2.6 `Status`'s state values mapped back to the four JPA states of §1.5, so the reader sees the
      spec's abstraction and Hibernate's implementation side by side. `[PROVE]`
3.2.7 `loadedState` is the dirty-checking snapshot: it holds **hydrated** values (the values as
      Hibernate's `Type`s see them), not the raw JDBC values and not your field values. `[PROVE]`
3.2.8 Memory arithmetic for the context, done properly: for 10k managed entities with 10 fields,
      count the entity, the `Object[10]` snapshot, the `EntityKey`, the `EntityEntry` and the map
      entries. State the total. `[NUM]` `[PROVE]` `[X-REF 06]`
3.2.9 `CollectionEntry` and `PersistentCollection`'s `snapshot` — collections are snapshotted too,
      which is why a 10k-element collection is a 20k-object problem. `[NUM]`
3.2.10 `clear()`'s implementation: it empties every map and calls `unsetSession` on every
       `PersistentCollection` and proxy, which is precisely why previously-loaded proxies throw
       afterwards. `[SOURCE]` `[PROVE]`
3.2.11 `getCachedDatabaseSnapshot` / `getDatabaseSnapshot` — the extra round trip Hibernate makes for
       `merge` and for versionless optimistic locking. `[RESEARCH]`
3.2.12 `SessionImpl`'s own state: `actionQueue`, `persistenceContext`, `jdbcCoordinator`,
       `loadQueryInfluencers` (filters, fetch profiles, entity graph, tenant id), `flushMode`,
       `cacheMode`. `[SOURCE]` `[RESEARCH]`
3.2.13 `LoadQueryInfluencers` as the object that carries a fetch plan into query generation — the
       plumbing behind `@EntityGraph`, `@FetchProfile`, `@Filter` and `@TenantId`. `[API]` `[PROVE]`

*(13 leaves)*

## §3.3 Loading an entity — hydration and two-phase load

3.3.1 The `find(Class, id)` decision tree in order: (1) the persistence context (`entitiesByKey`);
      (2) the L2 entity region; (3) the database. Each step named with the class that does it.
      `[FLOW]` `[PROVE]`
3.3.2 `DefaultLoadEventListener.onLoad` and the `LoadEventListener.LoadType` values
      (`RELOAD`, `GET`, `IMMEDIATE_LOAD`, `INTERNAL_LOAD_EAGER`, `INTERNAL_LOAD_LAZY`,
      `INTERNAL_LOAD_NULLABLE`). `[SOURCE]` `[RESEARCH]`
3.3.3 The two-phase load, which is the mechanism nobody can explain in interviews:
      **phase 1** — instantiate the entity, put it in the context with `Status.LOADING`, and
      hydrate its scalar values; **phase 2** — resolve associations, which may recurse into loading
      other entities that can now find *this* one in the context. `[PROVE]` `[SOURCE]`
3.3.4 Why two phases are necessary: without the entity being visible before its associations
      resolve, a cyclic graph (`Order → Customer → Order`) would recurse forever. This is the same
      proof shape as Spring's early-reference cache. `[PROVE]` `[X-REF 07]`
3.3.5 `TwoPhaseLoad.initializeEntity` (5.x) and its 6.x replacement in the
      `org.hibernate.sql.results.graph` initializer tree
      (`EntityInitializer`, `CollectionInitializer`, `EmbeddableInitializer`,
      `BasicResultAssembler`). Name the 6.x design: a **result graph of initializers**, driven once
      per row. `[SOURCE]` `[VERSION-TRAP]` `[RESEARCH]`
3.3.6 Hibernate 6's **read-by-position** change: the result-set reader indexes columns positionally
      instead of by alias, which removed the alias-mangling of 5.x and is a measurable win.
      `[VERSION-TRAP]` `[PROVE]` `[RESEARCH]`
3.3.7 Where the loaded-state snapshot is taken: after hydration, `TwoPhaseLoad`/the initializer calls
      `persistenceContext.addEntity(..., loadedState, ...)` with the hydrated array. **This is the
      exact line that costs you 2× memory.** `[SOURCE]` `[PROVE]`
3.3.8 `@Immutable` / `setReadOnly` short-circuits §3.3.7 — no snapshot is stored, so no dirty check
      is possible and memory halves. `[PROVE]`
3.3.9 The `Loader` hierarchy in 6.x: `SingleIdEntityLoaderStandardImpl`,
      `SingleIdEntityLoaderProvidedQueryImpl`, `MultiIdEntityLoaderStandardImpl`,
      `CollectionLoaderSingleKey`, `CollectionLoaderBatchKey`, `CollectionLoaderSubSelectFetch`.
      Each corresponds to a fetching strategy from §1.17. `[API]` `[RESEARCH]`
3.3.10 Batch loading internals: `BatchFetchQueue` holds the ids of un-initialised proxies and
       collections; a batch loader drains it into an `IN (...)` list. This is the actual mechanism of
       `@BatchSize`. `[SOURCE]` `[PROVE]`
3.3.11 `SubselectFetch` internals for `FetchMode.SUBSELECT`: Hibernate stores the original query's
       SQL and re-issues it as a subquery. `[PROVE]`
3.3.12 `EntityUniqueKey` and `byNaturalId` resolution against `entitiesByUniqueKey`. `[RESEARCH]`
3.3.13 What happens on a **duplicate** load of the same row in one context with different state:
       Hibernate keeps the existing instance and **discards** the freshly-read values (unless
       `refresh`). This is why a query cannot "update" your in-memory entity. `[PROVE]` `[TRAP]`
3.3.14 `NonUniqueObjectException: A different object with the same identifier value was already
       associated with the session` — the exact cause (two *different* instances with the same id,
       typically from `save`-ing a detached copy) and the fix (`merge`). `[DIAG]` `[TRAP]`

*(14 leaves)*

## §3.4 Dirty checking — the algorithm

3.4.1 The default algorithm, stated as pseudocode: for each `EntityEntry` in the context, for each
      property index `i` where `propertyCheckable[i]`, compare `currentState[i]` to
      `loadedState[i]` using `Type.isDirty(...)`. Collect the dirty indices. `[PROVE]` `[SOURCE]`
3.4.2 `Type.isDirty` / `isModified` / `isEqual` and why the comparison is **type-aware**, not
      `equals`: `BigDecimal` scale, `byte[]` content, embeddables component-wise, associations by
      identifier. `[PROVE]` `[SOURCE]`
3.4.3 The cost: O(entities × properties) **per flush**, and there can be several flushes per
      transaction. Do the arithmetic for 10k entities × 20 properties × 3 flushes. `[NUM]` `[PROVE]`
3.4.4 `DefaultFlushEntityEventListener.dirtyCheck` and the `FlushEntityEvent`'s
      `dirtyProperties`/`hasDirtyCollection` outputs. `[SOURCE]` `[RESEARCH]`
3.4.5 `CustomEntityDirtinessStrategy` — the SPI to replace the whole algorithm (e.g. ask the entity
      itself). `[API]`
3.4.6 In-line dirty tracking with bytecode enhancement: the enhanced entity implements
      `SelfDirtinessTracker` (`$$_hibernate_getDirtyAttributes`,
      `$$_hibernate_hasDirtyAttributes`, `$$_hibernate_clearDirtyAttributes`), so flush reads a set
      instead of scanning. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.4.7 Why in-line tracking is not the default: the bytecode format is version-coupled and the win
      only shows at scale. `[PROVE]`
3.4.8 The `@DynamicUpdate` interaction: without it the dirty *set* is discarded and the
      pre-generated all-column UPDATE is used; with it the UPDATE is built from the dirty indices.
      So dirty checking runs either way — `@DynamicUpdate` only changes the SQL. `[PROVE]` `[TRAP]`
3.4.9 Versionless optimistic locking (`OptimisticLockType.ALL`/`DIRTY`) uses the `loadedState` array
      to build a `where` clause of old values. Show the SQL. `[SQL]` `[PROVE]`
3.4.10 Why a *detached* entity cannot be dirty-checked: there is no `EntityEntry` and no
       `loadedState`, so `merge` must re-read the row to compute a diff. This closes the loop with
       §1.8.6. `[PROVE]`
3.4.11 Collections are dirty-checked separately: `PersistentCollection.isDirty()` and the snapshot
       comparison in `AbstractPersistentCollection`/`CollectionType.isDirty`. `[SOURCE]`
3.4.12 The mutable-embeddable and mutable-`byte[]` cases where dirty checking behaves surprisingly,
       and `@Immutable` on an embeddable as the fix. `[TRAP]`
3.4.13 `Session.isDirty()` runs the check without flushing — and therefore costs the same. `[PROVE]`

*(13 leaves)*

## §3.5 Flush internals and the `ActionQueue`

3.5.1 `DefaultFlushEventListener.onFlush` → `AbstractFlushingEventListener.flushEverythingToExecutions`
      → `performExecutions`. Quote the three-method skeleton. `[SOURCE]` `[FLOW]` `[RESEARCH]`
3.5.2 `flushEverythingToExecutions`' steps in order: `prepareEntityFlushes` (cascade),
      `prepareCollectionFlushes`, `flushEntities` (dirty check → schedule updates),
      `flushCollections` (schedule collection actions), then `logFlushResults`. `[FLOW]` `[SOURCE]`
3.5.3 **The `ActionQueue` execution order**, which is the highest-value internals fact in this part.
      In order: `OrphanRemovalAction`, `AbstractEntityInsertAction`
      (`EntityInsertAction`/`EntityIdentityInsertAction`), `EntityUpdateAction`,
      `QueuedOperationCollectionAction`, `CollectionRemoveAction`, `CollectionUpdateAction`,
      `CollectionRecreateAction`, `EntityDeleteAction`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.4 Why the order is what it is, and the bug it explains: **deletes run last**, so
      "delete row with unique key X then insert a new row with key X" fails in one transaction. The
      fix is an explicit `flush()` between them, or a bulk delete. `[PROVE]` `[TRAP]` `[SQL]`
3.5.5 The second consequence: inserts run before updates, so an insert that depends on an updated
      parent value can see the old one at the database level (though not in memory). `[PROVE]`
3.5.6 `ActionQueue.sortActions`, `hibernate.order_inserts` and `hibernate.order_updates` — the
      `InsertActionSorter` groups actions by entity type so JDBC batching can form. This is the
      mechanism behind §2.11.4. `[SOURCE]` `[PROVE]`
3.5.7 `ExecutableList` and the `unScheduleDeletion`/`unScheduleUnloadedDeletion` methods —
      how a re-`persist` of a removed entity cancels a queued delete. `[RESEARCH]`
3.5.8 `performExecutions`'s three phases: prepare (flush the JDBC batch), execute each list in the
      §3.5.3 order, then `afterTransactionCompletion` callbacks for L2 invalidation. `[FLOW]`
3.5.9 Auto-flush internals: `DefaultAutoFlushEventListener.onAutoFlush` computes
      `querySpaces` from the query plan and calls `flushIsReallyNeeded(event, source)` —
      the exact predicate behind §1.7.3. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.5.10 Why a native query has an **empty** query space and therefore never triggers §3.5.9 — the
       proof of §1.7.4. `[PROVE]`
3.5.11 `EntityInsertAction` vs `EntityIdentityInsertAction`: the latter is executed **immediately**
       at `persist` rather than queued, which is the proof of §1.8.3 and §2.11.5. `[PROVE]`
       `[SOURCE]`
3.5.12 Cascade traversal: `Cascade.cascade(CascadingAction, ...)` walking the persister's property
       types, and `CascadingActions.PERSIST_ON_FLUSH` as the action used during flush. `[SOURCE]`
       `[RESEARCH]`
3.5.13 Flush and the L2 cache: entries are **soft-locked** during `performExecutions` and released
       in `afterTransactionCompletion`, which is the tie-in to §3.15. `[PROVE]`
3.5.14 `TransactionCoordinator` / `JdbcResourceLocalTransactionCoordinatorImpl` and where the
       `beforeCompletion` flush is invoked from. `[SOURCE]` `[RESEARCH]`

*(14 leaves)*

## §3.6 The event system

3.6.1 Hibernate's architecture is event-driven: every session operation raises an event handled by a
      listener list, which is why every behaviour in this guide is replaceable. `[PROVE]`
3.6.2 `EventType`'s inventory worth naming: `PERSIST`, `PERSIST_ONFLUSH`, `MERGE`, `DELETE`,
      `REFRESH`, `LOAD`, `RESOLVE_NATURAL_ID`, `FLUSH`, `AUTO_FLUSH`, `FLUSH_ENTITY`, `CLEAR`,
      `EVICT`, `LOCK`, `DIRTY_CHECK`, `INIT_COLLECTION`, `PRE_INSERT`/`PRE_UPDATE`/`PRE_DELETE`,
      `POST_INSERT`/`POST_UPDATE`/`POST_DELETE`, `POST_LOAD`, plus the `*_COMMIT_*` variants.
      `[API]` `[SOURCE]` `[RESEARCH]`
3.6.3 The `Default*EventListener` implementations as the *actual* implementation of `persist`,
      `merge`, `delete`, `flush` and `load` — the point being that `EntityManager.persist` is a
      three-line delegation into `DefaultPersistEventListener`. `[SOURCE]` `[PROVE]`
3.6.4 `EventListenerRegistry` (`appendListeners`, `prependListeners`, `setListeners`) and
      registering via an `Integrator`. `[API]` `[BUILD]`
3.6.5 The difference between a JPA `@EntityListeners` callback and a Hibernate event listener:
      the former is invoked by `JpaCallbackRegistry`/`CallbackRegistryImpl` from inside the
      corresponding event listener, so JPA callbacks are a *subset* of the event system. `[PROVE]`
3.6.6 `PRE_*` listeners can **veto** by returning `true`, which is how Envers and Bean Validation
      hook in. `[PROVE]` `[API]`
3.6.7 `POST_COMMIT_*` listeners as the correct place for "publish after the row is durable" — and
      the fact that they run with no session. `[PROVE]`
3.6.8 Envers' implementation as the worked example: an `AuditEventListener` on the `POST_*` events
      writing to `_AUD` tables in the same transaction. `[RESEARCH]`
3.6.9 `BeanValidationEventListener` on `PRE_INSERT`/`PRE_UPDATE` — the proof of §2.7.6's "validation
      fires at flush, not at `save`". `[PROVE]`
3.6.10 `Interceptor` / `EmptyInterceptor` (deprecated) and `SessionFactoryBuilder.applyInterceptor` —
       the older, coarser hook. `[VERSION-TRAP]`

*(10 leaves)*

## §3.7 Proxies and lazy initialisation internals

3.7.1 `HibernateProxy`'s contract: `getHibernateLazyInitializer()` and `writeReplace()`. Every lazy
      `*ToOne` value implements it. `[SOURCE]` `[API]`
3.7.2 `LazyInitializer`'s surface: `getIdentifier`, `setIdentifier`, `getEntityName`,
      `getPersistentClass`, `isUninitialized`, `initialize`, `getImplementation`, `getSession`,
      `setSession`, `unsetSession`, `isReadOnly`. `[API]` `[SOURCE]`
3.7.3 Proxy generation: `ByteBuddyProxyFactory` / `ByteBuddyProxyHelper` generates a subclass whose
      every method delegates to the `LazyInitializer`, **except** the identifier getter (which is
      answered from the initializer directly — the proof of §1.17.9's "`getId()` is safe").
      `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.7.4 `final` methods cannot be intercepted, so a `final` getter on an entity **silently returns
      null/garbage on a proxy**. This is the concrete reason for the "no final methods" rule in
      §1.9.1. `[PROVE]` `[TRAP]`
3.7.5 `initialize()`'s path: `LazyInitializer.initialize` → `session.immediateLoad(entityName, id)`
      → `DefaultLoadEventListener` with `LoadType.IMMEDIATE_LOAD` → SELECT → `setImplementation`.
      `[FLOW]` `[SOURCE]`
3.7.6 The `LazyInitializationException` throw site: `AbstractLazyInitializer.initialize()` when
      `session == null` or `!session.isOpen()`. Quote the message construction so the reader can
      recognise it. `[SOURCE]` `[DIAG]`
3.7.7 `unsetSession` is called by `PersistenceContext.clear()` and by session close — which is why
      the exception happens on *use*, not on close. `[PROVE]`
3.7.8 `AbstractPersistentCollection.initialize(boolean writing)` and the
      `withTemporarySessionIfNeeded` path that `enable_lazy_load_no_trans=true` activates — the
      proof of §1.31.3. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.7.9 `PersistentBag`'s implementation: a delegate `List`, an `initialized` flag, a `snapshot`, and a
      `session` reference; every mutator calls `write()` which initialises and marks dirty.
      `[SOURCE]`
3.7.10 The `queued operations` mechanism (`QueuedOperationCollectionAction`): adding to an
       **uninitialised** bag with `@LazyCollection`/enhancement can queue the add without loading —
       which is why `list.add(x)` sometimes does not trigger a SELECT. `[PROVE]` `[RESEARCH]`
3.7.11 `Hibernate.unproxy(o)` and `Hibernate.getClass(o)`'s implementations, and why
       `o.getClass()` on an initialised proxy is *still* the proxy class. `[PROVE]`
3.7.12 Proxy `equals`/`hashCode`: they are intercepted and delegate, so a proxy and its target are
       equal **if** your `equals` is id-based and uses `Hibernate.getClass`. Close the loop with
       §2.6.6. `[PROVE]`
3.7.13 `EnhancementAsProxyLazinessInterceptor` — the enhanced-entity alternative to a proxy subclass,
       where the entity instance itself is the "proxy" with an interceptor field. This is what makes
       `instanceof` work under enhancement. `[SOURCE]` `[RESEARCH]`
3.7.14 Serialising a proxy: `writeReplace()` and `SerializableProxy`, and why a detached proxy
       deserialised elsewhere is a landmine. `[TRAP]`

*(14 leaves)*

## §3.8 Identifier generation internals

3.8.1 `Generator` (6.2+) with `BeforeExecutionGenerator` and `OnExecutionGenerator` as the two
      sub-contracts — before-execution for sequences/UUIDs, on-execution for identity columns and
      database defaults. `[API]` `[SOURCE]` `[RESEARCH]`
3.8.2 `SequenceStyleGenerator`'s configuration parameters: `sequence_name`, `increment_size`,
      `initial_value`, `opt` (the optimizer), `force_table_use`, `value_column`,
      `prefer_sequence_per_entity`, `sequence_per_entity_suffix` (**default `_SEQ`**). `[SOURCE]`
      `[NUM]` `[RESEARCH]`
3.8.3 The `Optimizer` hierarchy: `NoopOptimizer`, `HiLoOptimizer`, `LegacyHiLoAlgorithmOptimizer`,
      `PooledOptimizer`, `PooledLoOptimizer`, `PooledLoThreadLocalOptimizer`. Quote
      `PooledOptimizer.generate` and walk the arithmetic. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.8.4 `PooledOptimizer`'s invariant proved: the database value is the **upper** bound of the block,
      so the first `nextval` returning 50 with `increment_size = 50` hands out 1..50. Show why a
      mismatched `INCREMENT BY` collides. `[PROVE]` `[NUM]`
3.8.5 `PooledLoOptimizer`'s invariant proved: the database value is the **lower** bound, so
      `nextval → 1` hands out 1..50 and the next call returns 51. This is what makes external
      inserts safe. `[PROVE]` `[NUM]`
3.8.6 `IdentityGenerator` + `InsertReturningDelegate` / `GetGeneratedKeysDelegate` /
      `UniqueKeySelectingDelegate` — how the generated key is retrieved per dialect, and why this
      forces an immediate execute. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.8.7 `TableGenerator`'s implementation: a `select ... for update` on the value row per allocation,
      in a **separate transaction** (`hibernate.id.generator.isolate_transaction`-style behaviour) —
      the source of its contention. `[PROVE]` `[RESEARCH]`
3.8.8 `UuidGenerator` and the `UuidValueGenerator` strategies (`StandardRandomStrategy`,
      `CustomVersionOneStrategy`). `[SOURCE]` `[RESEARCH]`
3.8.9 `@IdGeneratorType` and `AnnotationBasedGenerator`/`GeneratorCreationContext` — the 6.5+ way to
      write a custom generator, with a complete example. `[BUILD]` `[RESEARCH]`
3.8.10 Where the generator is invoked from: `DefaultPersistEventListener` →
       `AbstractSaveEventListener.saveWithGeneratedId` → the generator → the entity key is computed →
       the entity enters the context. `[FLOW]` `[SOURCE]`
3.8.11 The `hibernate_sequence`-per-entity change in 6.0 (`prefer_sequence_per_entity` semantics) and
       the migration hazard for existing schemas. `[VERSION-TRAP]` `[RESEARCH]`

*(11 leaves)*

## §3.9 The query pipeline — HQL to SQL

3.9.1 The 6.x pipeline in five stages: **HQL text** → ANTLR 4 parse tree (`HqlParser`) →
      **SQM** (`SqmStatement`, semantic query model) → **SQL AST**
      (`SqlAstTranslator`, `SelectStatement`, `TableGroup`, `Predicate`) →
      `JdbcOperationQuerySelect` (SQL string + parameter binders + a result-graph of initializers) →
      execution. `[FLOW]` `[SOURCE]` `[RESEARCH]`
3.9.2 Why SQM was the point of Hibernate 6: **Criteria and HQL now produce the same tree**, so the
      old Criteria→HQL-string→SQL path with its string manipulation is gone. This also gives
      Criteria access to CTEs, window functions and set operations. `[PROVE]` `[RESEARCH]`
3.9.3 The SQM node vocabulary worth naming: `SqmSelectStatement`, `SqmRoot`, `SqmJoin`
      (`SqmAttributeJoin`, `SqmEntityJoin`, `SqmCrossJoin`, `SqmDerivedJoin`), `SqmPath`,
      `SqmParameter`, `SqmPredicate`, `SqmSelectClause`, `SqmOrderByClause`, `SqmCteStatement`,
      `SqmWindowFunction`. `[API]` `[RESEARCH]`
3.9.4 `SqmTranslator` / `StandardSqmTranslator` producing the SQL AST, and the per-dialect
      `SqlAstTranslator` (`AbstractSqlAstTranslator`, `PostgreSQLSqlAstTranslator`) producing the
      final string. Two translations, two extension points. `[SOURCE]` `[RESEARCH]`
3.9.5 `TableGroup` / `TableReference` / `TableGroupJoin` — how a mapped association becomes a join,
      and how `join fetch` differs (it adds a `Fetch` to the domain result graph as well).
      `[PROVE]` `[SOURCE]`
3.9.6 The result graph: `DomainResult`, `Fetch`, `EntityResult`, `BasicResult`,
      `DynamicInstantiationResult` (constructor expressions), `TupleResult`, and the matching
      `Initializer`/`Assembler` at execution time. This is how one SQL row becomes an object graph.
      `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.9.7 Parameter binding: `JdbcParameterBinder`, `QueryParameterBinding`,
      `hibernate.criteria.value_handling_mode` (`BIND` vs `INLINE`) and why Criteria literals are
      bound by default (plan-cache friendliness) — and the `INLINE` case for `IN` lists. `[PROP]`
      `[RESEARCH]`
3.9.8 The `LimitHandler` per dialect turning `setMaxResults` into `LIMIT`/`FETCH FIRST`/`ROWNUM`.
      `[SOURCE]`
3.9.9 Where JPQL validation happens at startup: `NamedObjectRepository.checkNamedQueries` /
      `QueryEngine`'s named-query checking, invoked from `SessionFactoryImpl`'s constructor. This is
      the mechanism behind "a `@Query` typo fails the boot". `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.9.10 Bulk mutation translation: `SqmMutationStrategy` implementations
       (`CteMutationStrategy`, `InlineMutationStrategy`, `PersistentTableMutationStrategy`,
       `LocalTemporaryTableMutationStrategy`, `GlobalTemporaryTableMutationStrategy`) and how a
       multi-table `delete` on a `JOINED` hierarchy becomes three statements plus a temp table.
       `[SOURCE]` `[SQL]` `[RESEARCH]`
3.9.11 Native queries: `NativeQueryImpl`, `ResultSetMapping`, and the absence of any parsing — hence
       no query space, no auto-flush, no validation. `[PROVE]`
3.9.12 `StatementInspector` as the last hook before the string reaches JDBC. `[API]`

*(12 leaves)*

## §3.10 The query plan cache and statement reuse

3.10.1 `QueryInterpretationCache` (`QueryInterpretationCacheStandardImpl`) keyed by the HQL string
       (or the Criteria's computed key), holding the `SqmStatement` and the compiled plan.
       `[SOURCE]` `[RESEARCH]`
3.10.2 `hibernate.query.plan_cache_max_size` (**default 2048**) and
       `hibernate.query.plan_parameter_metadata_max_size` (**default 128**). `[PROP]` `[NUM]`
       `[RESEARCH]`
3.10.3 What a cache miss costs: ANTLR parse + SQM build + SQL AST translation + string generation,
       per execution. Measurable at high throughput. `[PROVE]` `[NUM]`
3.10.4 Why a dynamically-concatenated query string defeats the cache entirely and a parameterised one
       does not — the performance argument for parameters that is separate from the injection
       argument. `[PROVE]`
3.10.5 Criteria plan keys: Hibernate computes a key from the tree, so structurally identical
       Criteria queries share a plan; `value_handling_mode=INLINE` breaks that. `[PROVE]`
       `[RESEARCH]`
3.10.6 `IN`-list cardinality and the plan cache: each distinct list length is a distinct SQL string;
       `hibernate.query.in_clause_parameter_padding=true` rounds to powers of two, cutting the
       distinct-string count from N to log₂N. Show the arithmetic. `[PROP]` `[NUM]` `[PROVE]`
3.10.7 The database's own plan cache and prepared-statement reuse
       (PostgreSQL `prepareThreshold=5` → server-side prepare after 5 executions; MySQL
       `cachePrepStmts`). Two caches, both need stable SQL. `[PROP]` `[NUM]` `[X-REF 09]`
3.10.8 `@DynamicUpdate`'s cost restated in these terms: a distinct UPDATE string per dirty-column
       combination, so 2^n possible statements and a cold plan cache. This is the real trade.
       `[PROVE]` `[NUM]`
3.10.9 Monitoring: `Statistics.getQueryPlanCacheHitCount()` / `MissCount` and
       `getQueryPlanCacheMissCount`. Verify names. `[API]` `[RESEARCH]`

*(9 leaves)*

## §3.11 JDBC layer internals and batching

3.11.1 `JdbcCoordinator`, `LogicalConnectionManagedImpl`, `ResourceRegistry` — Hibernate's
       connection and statement bookkeeping, including "who closes the `ResultSet`". `[API]`
       `[RESEARCH]`
3.11.2 `PhysicalConnectionHandlingMode`'s four values (§2.15.2) and where Spring pins it. `[NUM]`
3.11.3 `Batch` / `BatchKey` / `BatchBuilder` and `MutationExecutor`
       (`MutationExecutorStandard`, `MutationExecutorPostInsert`,
       `MutationExecutorSingleBatched`) — Hibernate 6's rewritten write path. `[SOURCE]`
       `[RESEARCH]`
3.11.4 The batching invariant proved: a batch is keyed by `(statement SQL, expectation)`, so a
       differing SQL string starts a new batch — which is why interleaved entity types and
       `@DynamicUpdate` break batching. `[PROVE]`
3.11.5 `Expectation` (`RowCount`, `OutParameter`, `None`) and how a batched versioned update verifies
       its row count — hence `hibernate.jdbc.batch_versioned_data` and the driver requirement to
       report per-statement counts. `[PROVE]` `[RESEARCH]`
3.11.6 `StaleStateException: Batch update returned unexpected row count from update [0]; actual row
       count: 0; expected: 1` — read this trace line by line; it is the optimistic-lock failure in
       batched form. `[DIAG]` `[TRAP]`
3.11.7 Where the batch is flushed: `Batch.execute()` from `performExecutions`, at transaction commit,
       and whenever the batch size is reached. A query in the middle forces it early. `[PROVE]`
3.11.8 Driver-level rewriting (`reWriteBatchedInserts`) turning N `INSERT`s into one multi-row
       statement — and why Hibernate's batch count and the round-trip count then differ. `[PROVE]`
       `[NUM]`
3.11.9 `hibernate.jdbc.fetch_size` and `ResultSet` streaming: PostgreSQL requires auto-commit off,
       a non-`TYPE_SCROLL` result set and a fetch size for a server-side cursor. Otherwise the whole
       result lands in the driver's memory. `[PROVE]` `[TRAP]` `[X-REF 09]`
3.11.10 `ScrollableResults` and `ScrollMode` as the pre-`Stream` cursor API, and why it still beats
        `Stream` for a 10M-row export. `[API]`
3.11.11 `SqlExceptionHelper` and `SQLExceptionConverter`/`SQLStateConversionDelegate` — how a vendor
        `SQLException` becomes a `ConstraintViolationException` or a `LockAcquisitionException`
        before Spring ever sees it. `[SOURCE]` `[PROVE]`

*(11 leaves)*

## §3.12 Second-level cache internals

3.12.1 The SPI: `RegionFactory`, `DomainDataRegion`, `EntityDataAccess`, `CollectionDataAccess`,
       `NaturalIdDataAccess`, `QueryResultsRegion`, `TimestampsRegion`. `[API]` `[SOURCE]`
3.12.2 The `AccessType` enum mapped to the four `CacheConcurrencyStrategy` values, and the
       `EntityDataAccess` method set (`get`, `putFromLoad`, `lockItem`, `unlockItem`,
       `insert`/`afterInsert`, `update`/`afterUpdate`, `remove`, `evict`). `[API]` `[SOURCE]`
3.12.3 What is stored: `CacheEntry` — a **disassembled** `Object[]` plus the version and the
       subclass name, produced by `EntityPersister.getCacheEntryStructure()`. Not your instance.
       `[SOURCE]` `[PROVE]`
3.12.4 The `READ_WRITE` soft-lock protocol, step by step: `lockItem` replaces the entry with a
       `SoftLock` (a lock marker with a timeout and a version), concurrent `get`s that see a
       `SoftLock` return `null` (so the reader goes to the database), and
       `afterUpdate`/`unlockItem` at transaction completion either installs the new value or leaves
       the region to re-read. Prove that this gives strong consistency without a transactional
       cache. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.12.5 The `NONSTRICT_READ_WRITE` protocol: **invalidate after commit** with no lock, hence a
       genuine window where a reader can populate the cache with the pre-update value. Prove the
       window exists and bound it. `[PROVE]` `[RESEARCH]`
3.12.6 `READ_ONLY`'s protocol and the `UnsupportedOperationException` on update. `[PROVE]`
3.12.7 `TRANSACTIONAL`'s requirement (a JTA/XA-capable cache enlisted in the same transaction) and
       why almost nobody runs it. `[PROVE]`
3.12.8 The **timestamps region**: `UpdateTimestampsCache` records the last update time per query
       space; a cached query result is served only if all its spaces are older than the entry. This
       is the entire query-cache invalidation mechanism. `[PROVE]` `[SOURCE]`
3.12.9 Why the timestamps mechanism makes the query cache useless on a write-heavy table — the proof
       of §1.29.10. `[PROVE]`
3.12.10 `QueryKey` composition: the SQL/HQL, the parameter values, the first/max results, the tenant
        id, the enabled filters. Any difference is a miss. `[PROVE]`
3.12.11 `putFromLoad`'s `minimalPutOverride` and `hibernate.cache.use_minimal_puts`. `[PROP]`
3.12.12 The clustering question answered mechanically: an in-process region (Ehcache local) is
        per-JVM; invalidation-mode Infinispan broadcasts invalidations; replicated mode broadcasts
        values. Only the latter two are safe multi-instance — the proof of §1.29.11. `[PROVE]`
3.12.13 What bypasses L2 entirely and leaves it stale: bulk HQL, native SQL, `StatelessSession`
        (before 7.0), another application, and a DBA. `[TRAP]`

*(13 leaves)*

## §3.13 Optimistic and pessimistic locking internals

3.13.1 Where the version predicate is added: `EntityPersister`'s pre-generated update SQL includes
       `where id = ? and version = ?` when the entity is versioned; the `Expectation` then asserts a
       row count of 1. `[SOURCE]` `[PROVE]` `[SQL]`
3.13.2 The version increment: `VersionType`/`VersionJavaType.next(...)` and where the in-memory field
       is updated — **after** the statement succeeds, which is why a failed flush leaves the entity
       with the old version. `[PROVE]`
3.13.3 `StaleObjectStateException` vs `StaleStateException` vs `OptimisticLockException`: which layer
       raises which, and how `EntityManagerFactoryUtils.convertJpaAccessExceptionIfPossible` /
       `HibernateExceptionTranslator` map them to Spring's
       `ObjectOptimisticLockingFailureException`. `[SOURCE]` `[PROVE]`
3.13.4 `OPTIMISTIC` lock mode's implementation: at `beforeCompletion` Hibernate issues
       `select version from t where id = ?` and compares — a **read-time** version check.
       `[PROVE]` `[SQL]`
3.13.5 `OPTIMISTIC_FORCE_INCREMENT`'s implementation: an `EntityIncrementVersionProcess` queued to
       run at flush, issuing `update t set version = version + 1 where id = ? and version = ?`.
       `[PROVE]` `[SQL]` `[RESEARCH]`
3.13.6 Pessimistic locking: `Dialect.getWriteLockString`/`getReadLockString`/`getForUpdateString`,
       the `LockOptions` object (`lockMode`, `timeout`, `scope`, `followOnLocking`), and where the
       hint is appended. `[SOURCE]` `[API]`
3.13.7 **Follow-on locking**: when a dialect cannot combine `FOR UPDATE` with the query's shape
       (outer joins, `DISTINCT`, pagination on some dialects), Hibernate issues a **separate
       `SELECT ... FOR UPDATE` per row** — an N+1 of locks. `LockOptions.setFollowOnLocking(false)`
       and the log warning. This is a genuinely obscure, genuinely important leaf. `[PROVE]`
       `[TRAP]` `[RESEARCH]`
3.13.8 `em.lock(entity, PESSIMISTIC_WRITE)` on an already-loaded entity issues a
       `select ... for update` for that row only. `[SQL]`
3.13.9 Lock timeout translation per dialect: PostgreSQL `NOWAIT` / `SKIP LOCKED`, Oracle
       `WAIT n`/`NOWAIT`, MySQL `NOWAIT`/`SKIP LOCKED` (8.0+), and what Hibernate does when the
       dialect has no support (it ignores the timeout). `[TRAP]` `[NUM]` `[RESEARCH]`
3.13.10 Locking and the L2 cache: a pessimistic lock forces a database read and soft-locks the cache
        entry. `[PROVE]`
3.13.11 `versionless` optimistic locking's SQL from §3.4.9 shown against `OptimisticLockType.ALL` and
        `DIRTY`, with the `@DynamicUpdate` requirement proved. `[SQL]` `[PROVE]`

*(11 leaves)*

## §3.14 Spring's JPA integration internals

3.14.1 `SharedEntityManagerCreator.createSharedEntityManager` — the `EntityManager` you inject is a
       **JDK dynamic proxy** whose `SharedEntityManagerInvocationHandler` resolves the target per
       call via `EntityManagerFactoryUtils.doGetTransactionalEntityManager`. Quote the handler.
       `[SOURCE]` `[PROVE]`
3.14.2 What the shared proxy does when there is **no** transaction: it creates a new `EntityManager`,
       runs the single call, and closes it — hence "everything comes back detached". Prove §1.27.9
       from the source. `[PROVE]` `[SOURCE]`
3.14.3 Which methods the shared proxy rejects (`close`, `getTransaction`, `joinTransaction` outside a
       transaction) and the `IllegalStateException` messages. `[DIAG]`
3.14.4 `EntityManagerHolder` and `TransactionSynchronizationManager.bindResource(emf, holder)` —
       the thread-local map from `EntityManagerFactory` to `EntityManager`. `[SOURCE]` `[X-REF 07]`
3.14.5 `JpaTransactionManager.doBegin`'s sequence: obtain an `EntityManager`, begin the JPA
       transaction, expose the underlying JDBC `Connection` as a `ConnectionHolder` bound to the
       `DataSource`, apply isolation and read-only, set the timeout. Quote it. `[SOURCE]` `[FLOW]`
3.14.6 Why step 3 of §3.14.5 is the leaf that makes `JdbcTemplate` and JPA share a transaction, and
       why using `DataSourceTransactionManager` instead breaks it — the proof of §1.27.3.
       `[PROVE]`
3.14.7 `doCommit`/`doRollback`/`doCleanupAfterCompletion` and where flush happens relative to the
       JDBC commit. `[FLOW]`
3.14.8 `HibernateJpaDialect` (a `JpaDialect`) — `beginTransaction` applying the isolation level and
       flush mode, `getJdbcConnection`, and
       `translateExceptionIfPossible` mapping Hibernate exceptions to `DataAccessException`.
       `[SOURCE]` `[API]`
3.14.9 `EntityManagerFactoryUtils.convertJpaAccessExceptionIfPossible` and the full JPA →
       `DataAccessException` mapping table (`EntityNotFoundException` →
       `JpaObjectRetrievalFailureException`, `OptimisticLockException` →
       `JpaOptimisticLockingFailureException`, `PersistenceException` → `JpaSystemException`, …).
       `[SOURCE]` `[API]` `[X-REF 07]`
3.14.10 `OpenEntityManagerInViewInterceptor.preHandle`/`afterCompletion` — it binds an
        `EntityManagerHolder` for the request and marks it as *not* transaction-owned, which is why
        the lazy loads it enables run outside any transaction. Prove §2.12.3's third bullet.
        `[SOURCE]` `[PROVE]`
3.14.11 `PersistenceExceptionTranslationPostProcessor` and why a Spring Data repository proxy already
        has it. `[X-REF 07]`
3.14.12 `LocalContainerEntityManagerFactoryBean`'s `PersistenceUnitManager` /
        `DefaultPersistenceUnitManager` / `MutablePersistenceUnitInfo` and the packages-to-scan
        implementation (`PersistenceManagedTypesScanner`). `[SOURCE]` `[RESEARCH]`
3.14.13 `spring.jpa.properties` flowing through `JpaProperties.getProperties()` into
        `EntityManagerFactoryBuilder`, and the exact reason a mistyped key is silently ignored — the
        proof of §1.3.15. `[PROVE]`

*(13 leaves)*

## §3.15 The Spring Data repository proxy

3.15.1 The registration path: `@EnableJpaRepositories` → `JpaRepositoriesRegistrar`
       (an `ImportBeanDefinitionRegistrar`) → `RepositoryConfigurationDelegate` →
       one `JpaRepositoryFactoryBean` bean definition per interface. Prove that *no* class is
       generated at build time in 3.5 (unlike 4.0's AOT repositories). `[SOURCE]` `[FLOW]`
       `[X-REF 07]`
3.15.2 `RepositoryFactoryBeanSupport.afterPropertiesSet` → `RepositoryFactorySupport.getRepository` →
       a `ProxyFactory` with the repository interface plus the fragments. `[SOURCE]`
3.15.3 The advice chain on the proxy, in order: `ExposeInvocationInterceptor`,
       `DefaultMethodInvokingMethodInterceptor` (Java 8 `default` methods),
       `TransactionalRepositoryProxyPostProcessor`'s `TransactionInterceptor`,
       `PersistenceExceptionTranslationInterceptor`, `CrudMethodMetadataPostProcessor`, and finally
       `QueryExecutorMethodInterceptor`. `[SOURCE]` `[FLOW]` `[RESEARCH]`
3.15.4 `QueryExecutorMethodInterceptor.invoke`'s three-way decision: is it a fragment/custom-impl
       method → delegate; is it a base-class (`SimpleJpaRepository`) method → delegate; otherwise →
       look up the pre-built `RepositoryQuery`. `[SOURCE]` `[PROVE]`
3.15.5 `RepositoryComposition` / `RepositoryFragments` — how `XxxCustomImpl` and the base class are
       composed, and the resolution order when both define a method. `[SOURCE]` `[PROVE]`
3.15.6 `QueryLookupStrategy`'s three implementations (`CreateQueryLookupStrategy`,
       `DeclaredQueryLookupStrategy`, `CreateIfNotFoundQueryLookupStrategy`) and
       `JpaQueryLookupStrategy` as the JPA binding. `[SOURCE]` `[API]`
3.15.7 `PartTree` — the derived-query parser. Its structure: `Subject` (with
       `LIMITED_QUERY_TEMPLATE`, `COUNT_QUERY_TEMPLATE`, `EXISTS_QUERY_TEMPLATE`,
       `DELETE_QUERY_TEMPLATE` regexes), `Predicate`, `OrPart`, `Part`, and `Part.Type` with its
       keyword lists. Quote the regex and the keyword enum. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.15.8 `PropertyPath.from(...)` and the greedy-then-backtracking resolution algorithm that produces
       §1.23.5's ambiguity and the underscore escape. Quote it. `[SOURCE]` `[PROVE]`
3.15.9 `JpaQueryCreator` turning a `PartTree` into a **Criteria** query (not a JPQL string) —
       so derived queries go through the Criteria/SQM path. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.15.10 `PartTreeJpaQuery` vs `SimpleJpaQuery` vs `NativeJpaQuery` vs `StoredProcedureJpaQuery` vs
        `DeclaredQuery` — the `AbstractJpaQuery` implementations, one per query source. `[API]`
3.15.11 `JpaQueryMethod`, `QueryMethod`, `Parameters`/`JpaParameters`, `ParameterBinder`,
        `ParametersParameterAccessor` — how method arguments become query parameters, and how
        `Pageable`/`Sort`/`Limit`/`ScrollPosition` are detected as *special* parameters.
        `[SOURCE]` `[API]`
3.15.12 `JpaQueryExecution`'s subclasses as the return-type strategies:
        `CollectionExecution`, `SlicedExecution`, `PagedExecution`, `SingleEntityExecution`,
        `ModifyingExecution`, `StreamExecution`, `ProcedureExecution`, `DeleteExecution`,
        `ExistsExecution`, `ScrollExecution`. Each one explains a return type's SQL behaviour —
        including `PagedExecution` issuing the count query. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.15.13 `SlicedExecution` fetching `pageSize + 1` rows to compute `hasNext` — the proof of §1.26.2.
        `[PROVE]`
3.15.14 `ModifyingExecution` and where `flushAutomatically`/`clearAutomatically` are applied
        (before/after `executeUpdate`). `[SOURCE]` `[PROVE]`
3.15.15 `QueryEnhancer` / `QueryUtils` — the string surgery Spring Data does to a JPQL query to
        append `order by` for a `Sort` and to derive a count query
        (`QueryUtils.createCountQueryFor`, `applySorting`, `getExistsQueryString`,
        `DEFAULT_ALIAS`, the alias-detection regex). This is why `Sort` works on JPQL and not on
        native SQL — the proof of §1.26.8. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.15.16 `JSqlParser`-based `QueryEnhancer` for native queries (Spring Data 2.6+) and what it can and
        cannot rewrite. `[RESEARCH]`
3.15.17 `SimpleJpaRepository` read in full: the class-level `@Transactional(readOnly = true)`, the
        `findById`→`em.find`, `getReferenceById`→`em.getReference`, `save`'s `isNew` branch,
        `deleteAllInBatch`'s single `delete from` statement, `findAll(Specification)` building a
        `CriteriaQuery`, and `CrudMethodMetadata`'s lock-mode/query-hint application. `[SOURCE]`
3.15.18 `JpaEntityInformation` / `JpaMetamodelEntityInformation` — how `isNew` reads the `@Version`
        and `@Id` attributes from the JPA metamodel. `[SOURCE]` `[PROVE]`
3.15.19 Projection internals: `ProjectionFactory` / `SpelAwareProxyProjectionFactory` /
        `ProxyProjectionFactory` creating a JDK proxy with a `MapAccessingMethodInterceptor` +
        `ProjectingMethodInterceptor` + `PropertyAccessingMethodInterceptor`, and
        `ProjectionInformation.isClosed()` — the exact bit that decides whether the select list can
        be narrowed. Prove §1.25.2 from here. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.15.20 `ReturnedType` / `ResultProcessor` / `Converters` — where a `Tuple` becomes a DTO, a record,
        or a projection proxy. `[SOURCE]`
3.15.21 `AuditingEntityListener` + `AuditingHandler` + `AuditingBeanFactoryPostProcessor` +
        `JpaAuditingRegistrar` — how `@EnableJpaAuditing` gets a Spring-managed listener into a JPA
        listener slot (`SpringBeanContainer` again). Prove why auditing silently does nothing if
        `@EntityListeners` is missing. `[SOURCE]` `[PROVE]` `[TRAP]`
3.15.22 `BootstrapMode.DEFERRED`/`LAZY` internals: `Lazy<Repository>` and a
        `DeferredRepositoryInitializationListener` on `ContextRefreshedEvent` — and the consequence
        that a bad `@Query` no longer fails at boot. `[PROVE]` `[TRAP]` `[RESEARCH]`
3.15.23 Spring Data 4.0's **AOT repositories**: generated implementation classes instead of a runtime
        proxy, `spring.aot.repositories.enabled` (now default on). What this changes for debugging
        and for startup. `[VERSION-TRAP]` `[RESEARCH]`

*(23 leaves)*

## §3.16 Failure modes read at source level

3.16.1 The decision tree for "the SQL I expected did not run": is there a transaction → is the entity
       managed → is the flush mode `MANUAL` → is the field dirty by `Type.isDirty` → is the property
       updatable → did the action queue run. Six checks, each a named mechanism. `[FLOW]` `[DIAG]`
3.16.2 The decision tree for "SQL ran that I did not write": dirty checking on a mutated managed
       entity → cascade → orphan removal → collection recreate → auditing/Envers → `@PreUpdate`.
       `[FLOW]` `[DIAG]`
3.16.3 The decision tree for "too many statements": eager `*ToOne` under a query → lazy in a loop →
       collection per row → OSIV serialisation → follow-on locking → `@ElementCollection` recreate.
       `[FLOW]` `[DIAG]`
3.16.4 `LazyInitializationException` anatomy: the message, the `AbstractLazyInitializer.initialize`
       frame, the proxy class name, and the getter that triggered it. Read a real trace.
       `[DIAG]`
3.16.5 `MultipleBagFetchException: cannot simultaneously fetch multiple bags` — the message, the two
       association names in it, and the fix. `[DIAG]`
3.16.6 `NonUniqueObjectException` anatomy (§3.3.14). `[DIAG]`
3.16.7 `TransientObjectException` / `object references an unsaved transient instance - save the
       transient instance before flushing` anatomy (§1.16.12). `[DIAG]`
3.16.8 `HibernateException: A collection with cascade="all-delete-orphan" was no longer referenced by
       the owning entity instance` anatomy (§1.14.7). `[DIAG]`
3.16.9 `StaleStateException: Batch update returned unexpected row count` anatomy (§3.11.6).
       `[DIAG]`
3.16.10 `ConstraintViolationException` at commit wrapped in `TransactionSystemException` — the
        three-layer stack and where to catch it. `[DIAG]`
3.16.11 `QueryTimeoutException` / `CannotAcquireLockException` /
        `DeadlockLoserDataAccessException` and what each says about the database's state.
        `[DIAG]` `[X-REF 09]`
3.16.12 `HikariPool-1 - Connection is not available` anatomy (§2.15.5). `[DIAG]`
3.16.13 `HHH000104` / `HHH90003004` anatomy (§2.5.2). `[DIAG]`
3.16.14 `PropertyValueException: not-null property references a null or transient value` and the
        `hibernate.check_nullability` interaction. `[DIAG]`
3.16.15 The silent-failure catalogue — the cases with **no** exception and no log line: a mutation on
        a detached entity, a mutation on a projection, `save` under flush mode `MANUAL`, an
        unowned-side-only collection add, `insertable=false` on a field you set, a `@PreUpdate` that
        did not fire, `Sort` on a native query, and a mistyped `spring.jpa.*` key. These are the
        hardest bugs in the topic and they deserve their own section. `[TRAP]` `[PROVE]`

*(15 leaves)*

---

**PART 3 total: 12+13+14+13+14+10+14+11+12+9+11+13+11+13+23+15 = 208 leaves**

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf below ships **complete, compiling Java 21** and is followed by a
**Diff vs the real one** table. The point is not to write a competitor to Hibernate; it is that
having implemented the identity map, the dirty check, the action queue, the proxy and the derived-
query parser, none of PART 3 is mysterious any more. All domain examples use the QuizStakes entities
from `src/scenario/scenario.md`.

## §4.1 A mini persistence context

4.1.1 `EntityKey` as a `record EntityKey(Class<?> type, Object id)` with the correct `equals`/
      `hashCode`. `[BUILD]`
4.1.2 `MiniEntityEntry` holding `status`, `id`, `loadedState` (an `Object[]`) and a persister
      reference. `[BUILD]`
4.1.3 `MiniPersistenceContext` with `Map<EntityKey,Object> entitiesByKey` and
      `IdentityHashMap<Object,MiniEntryEntry> entries`: `add`, `getEntity`, `getEntry`, `contains`,
      `detach`, `clear`. `[BUILD]`
4.1.4 `MiniPersister<T>` built from reflection: the id field, the persistent fields, `hydrate`,
      `getPropertyValues`, `setPropertyValues`. `[BUILD]`
4.1.5 `MiniEntityManager.find(Class, id)` implementing the §3.3.1 decision tree against a
      `Map<EntityKey,Object[]>` stand-in database, and returning the **same instance** on the
      second call. A test asserting `==`. `[BUILD]` `[PROVE]`
4.1.6 `persist` assigning an id from an in-memory sequence and registering an insert action.
      `[BUILD]`
4.1.7 **Diff vs the real one:** `EntityEntryContext`'s intrusive list under enhancement, the
      `entitiesByUniqueKey`/`proxiesByKey`/`collectionEntries` maps, `Status.LOADING` for two-phase
      load, `nullifiableEntityKeys`, read-only entities skipping `loadedState`, the L2 lookup between
      L1 and the database, and the interceptor/event indirection. `[NUM]`

*(7 leaves)*

## §4.2 Dirty checking and the flush

4.2.1 `dirtyProperties(entity, entry)` comparing `getPropertyValues(entity)` against
      `entry.loadedState()` index by index and returning the changed indices. `[BUILD]`
4.2.2 A type-aware comparison for `BigDecimal` (`compareTo`), `byte[]` (`Arrays.equals`) and
      everything else (`Objects.equals`) — the miniature of §3.4.2. `[BUILD]` `[PROVE]`
4.2.3 `flush()` walking every managed entry, computing the dirty set, and emitting a full-column
      UPDATE string; then a `dynamicUpdate` flag that emits only the changed columns. `[BUILD]`
      `[SQL]`
4.2.4 A test proving the §1.5.10 claim: mutate a managed entity, never call `save`, flush, and see
      the UPDATE. `[BUILD]` `[PROVE]`
4.2.5 A test proving the §1.5.12 claim: calling `save` on a managed entity produces exactly the same
      SQL as not calling it. `[BUILD]` `[PROVE]`
4.2.6 A `SelfDirtinessTracker`-style variant where the entity records its own dirty fields, and a
      JMH-shaped comparison of the two at 10k entities. `[BUILD]` `[NUM]` `[X-REF 06]`
4.2.7 **Diff vs the real one:** `Type.isDirty` per Hibernate `Type` rather than per Java class,
      `propertyUpdateability`/`propertyVersionability` arrays, embeddable component-wise comparison,
      collection dirtiness via `PersistentCollection.isDirty`, `CustomEntityDirtinessStrategy`, the
      `FlushEntityEvent` indirection, and pre-generated SQL held on the persister. `[NUM]`

*(7 leaves)*

## §4.3 The action queue with real ordering

4.3.1 `sealed interface Action permits InsertAction, UpdateAction, DeleteAction,
      CollectionRecreateAction, OrphanRemovalAction` with an `execute(Connection)` method.
      `[BUILD]` `[X-REF 04]`
4.3.2 `MiniActionQueue` with one `List` per action type and an `executeActions()` that runs them in
      the exact §3.5.3 order. `[BUILD]`
4.3.3 A test that reproduces the §3.5.4 bug: delete a row with unique key `X`, insert a new row with
      key `X`, flush once, and watch the constraint violation because deletes run last. Then fix it
      with an intermediate flush. `[BUILD]` `[PROVE]`
4.3.4 `sortActions()` grouping inserts by entity type, and a test showing the batch count before and
      after — the miniature of §3.5.6 and §2.11.4. `[BUILD]` `[NUM]` `[PROVE]`
4.3.5 An auto-flush implementation: a `querySpaces(String hql)` approximation and
      `flushIsReallyNeeded`, plus a test showing a **native** query skipping the flush.
      `[BUILD]` `[PROVE]`
4.3.6 **Diff vs the real one:** `ExecutableList`'s sorting and `unScheduleDeletion`,
      `EntityIdentityInsertAction`'s immediate execution, the `BatchKey`/`MutationExecutor` layer,
      L2 soft-locking in `afterTransactionCompletion`, cascade traversal via `Cascade.cascade`, and
      the real query-space computation from the SQM tree. `[NUM]`

*(6 leaves)*

## §4.4 A lazy proxy

4.4.1 A `LazyInitializer` interface with `getIdentifier`, `isUninitialized`, `getImplementation`,
      `setSession`, `unsetSession`. `[BUILD]`
4.4.2 A JDK-dynamic-proxy version over an interface (`CustomerView`) that answers `getId()` from the
      initializer and loads on any other call. `[BUILD]`
4.4.3 A ByteBuddy version over the **class** `Customer`, showing the generated subclass name and why
      a `final` getter breaks it — the demonstration of §3.7.4. `[BUILD]` `[PROVE]` `[X-REF 06]`
4.4.4 A `MiniLazyInitializationException` thrown when the session is unset, with a message that
      mirrors Hibernate's. `[BUILD]` `[DIAG]`
4.4.5 A `MiniPersistentBag` implementing `List<T>` by delegation with an `initialized` flag and a
      `write()`/`read()` guard, plus a test showing `size()` triggering a load. `[BUILD]` `[PROVE]`
4.4.6 A `BatchFetchQueue` that collects uninitialised proxy ids and loads them in one
      `IN (...)` batch — the miniature of `@BatchSize`, with the `1 + ceil(N/size)` count asserted.
      `[BUILD]` `[NUM]` `[PROVE]`
4.4.7 **Diff vs the real one:** ByteBuddy caching and `ProxyFactory` per persister, `writeReplace`
      serialisation, `EnhancementAsProxyLazinessInterceptor`, read-only proxies, the
      `getIdentifier`-without-init optimisation being persister-driven, `PersistentBag`'s snapshot
      and queued operations, and `SubselectFetch`. `[NUM]`

*(7 leaves)*

## §4.5 A derived-query parser

4.5.1 A `Part.Type` enum with the keyword lists from §1.23.2 and each type's JPQL template.
      `[BUILD]`
4.5.2 A `Subject` parser handling `find`/`read`/`get`/`query`/`search`/`stream`/`count`/`exists`/
      `delete`, plus `Distinct`, `Top<n>` and `First<n>`. `[BUILD]`
4.5.3 A `PartTree` parser splitting on `Or`/`And` and resolving each `Part` to a property path,
      including the greedy-then-backtrack algorithm and the `_` escape. `[BUILD]` `[PROVE]`
4.5.4 A JPQL emitter turning the tree into `select o from Order o where o.status = ?1 and
      o.createdAt > ?2 order by o.createdAt desc`. `[BUILD]` `[SQL]`
4.5.5 Parameter-count validation that fails at *construction* time with a readable message — the
      miniature of "a typo fails the boot". `[BUILD]` `[PROVE]`
4.5.6 A test suite over twenty method names including the ambiguous `findByAddressZipCode` case.
      `[BUILD]`
4.5.7 **Diff vs the real one:** `PartTree`'s actual regexes, `PropertyPath`'s metamodel-driven
      resolution, `JpaQueryCreator` producing a **Criteria** query rather than a string, `IgnoreCase`
      and `AllIgnoreCase`, `In` collection handling, null handling per type, and the
      `Pageable`/`Sort`/`Limit`/`ScrollPosition` special-parameter detection. `[NUM]`

*(7 leaves)*

## §4.6 A repository proxy

4.6.1 A `@MiniRepository` annotation and a `MiniRepositoryFactory.getRepository(Class<T>)` returning
      a JDK proxy. `[BUILD]`
4.6.2 An invocation handler implementing the §3.15.4 three-way decision: a base-class method, a
      custom-fragment method, or a derived query. `[BUILD]` `[PROVE]`
4.6.3 A `MiniSimpleRepository<T,ID>` base with `findById`, `save` (with an `isNew` check), `findAll`,
      `count`, `deleteById`. `[BUILD]`
4.6.4 `default` method support on the interface, and why it must be dispatched specially. `[BUILD]`
      `[PROVE]`
4.6.5 Fragment composition: a `CustomerRepositoryCustom` + `CustomerRepositoryCustomImpl` resolved by
      name, with the ordering rule. `[BUILD]`
4.6.6 A return-type strategy layer mirroring `JpaQueryExecution`: `List`, `Optional`, `Page` (with
      the count query), `Slice` (with `size + 1`), `long`, `boolean`. Assert the statement counts.
      `[BUILD]` `[NUM]` `[PROVE]`
4.6.7 A closed/open interface-projection proxy: build a JDK proxy over a `Map<String,Object>`, and
      show that an `@Value`-annotated accessor forces loading the whole row — the demonstration of
      §1.25.2. `[BUILD]` `[PROVE]`
4.6.8 **Diff vs the real one:** the full advice chain from §3.15.3, `RepositoryComposition`,
      `QueryLookupStrategy`, `CrudMethodMetadata` for `@Lock`/`@QueryHints`, exception translation,
      `ResultProcessor`/`ReturnedType`, `SpelAwareProxyProjectionFactory`, `BootstrapMode`, and
      4.0's AOT-generated implementations. `[NUM]`

*(8 leaves)*

## §4.7 A pooled-lo sequence generator

4.7.1 An `IdentifierGenerator`-shaped interface and a `PooledLoOptimizer` implementation holding
      `lastSourceValue`, `value` and `upperLimit`. `[BUILD]`
4.7.2 A `PooledOptimizer` implementation for contrast, with the upper-bound semantics. `[BUILD]`
4.7.3 A test asserting the exact identifier sequence each produces for
      `allocationSize = 50` over 120 allocations, and the number of `nextval` calls (**3**).
      `[BUILD]` `[NUM]` `[PROVE]`
4.7.4 A test proving the collision when the database's `INCREMENT BY` is 1 but `allocationSize` is
      50, with two "instances" allocating concurrently. `[BUILD]` `[PROVE]`
4.7.5 A thread-safety test: the optimizer must be synchronised, and a race produces duplicate ids.
      `[BUILD]` `[X-REF 05]`
4.7.6 A UUIDv7-style time-ordered generator and a comparison of insert locality against random v4 by
      measuring key ordering. `[BUILD]` `[NUM]` `[X-REF 09]`
4.7.7 **Diff vs the real one:** `SequenceStyleGenerator`'s table fallback, `AccessCallback`/
      `IntegralDataTypeHolder` for type-generic arithmetic, the `pooled-lotl` thread-local variant,
      `initialValue` handling, database-metadata validation of the sequence, and
      `@IdGeneratorType` wiring. `[NUM]`

*(7 leaves)*

## §4.8 A keyset paginator

4.8.1 A `Cursor` record over the sort tuple, plus base64 encode/decode. `[BUILD]`
4.8.2 A JPQL/SQL builder emitting both the row-value form and the expanded
      `a < ? or (a = ? and b < ?)` form. `[BUILD]` `[SQL]`
4.8.3 A `Window<T>` equivalent with `hasNext` computed from `size + 1`. `[BUILD]`
4.8.4 A test comparing offset page 5000 with keyset page 5000: statement plans, row counts examined,
      and wall time against a Testcontainer. `[BUILD]` `[NUM]` `[PROVE]` `[X-REF 09]`
4.8.5 A test proving the instability of offset pagination under concurrent inserts, and keyset's
      stability. `[BUILD]` `[PROVE]`
4.8.6 A test proving that omitting the unique tiebreaker loses rows. `[BUILD]` `[PROVE]`
4.8.7 **Diff vs the real one:** Spring Data's `KeysetScrollDelegate`, `ScrollPosition` backward
      scrolling, `WindowIterator`, projection support, and the sort-derived predicate generation.
      `[NUM]`

*(7 leaves)*

## §4.9 A batch-insert harness and a query counter

4.9.1 A `StatementCounter` built on a `StatementInspector` (or a `ProxyDataSource`) that records
      per-thread counts and exposes `assertMax(n)`. `[BUILD]`
4.9.2 A JUnit 5 extension that fails a test when a method exceeds its statement budget. `[BUILD]`
      `[X-REF 16]`
4.9.3 A batch-insert benchmark of 100k rows across five configurations: no batching + IDENTITY;
      `batch_size=50` + IDENTITY (**no improvement — the proof of §2.11.5**); `batch_size=50` +
      SEQUENCE pooled; plus `order_inserts`; plus `reWriteBatchedInserts`. Report statements, round
      trips and wall time. `[BUILD]` `[NUM]` `[PROVE]`
4.9.4 The `flush()`+`clear()` loop with a heap measurement showing the difference at 100k rows.
      `[BUILD]` `[NUM]` `[X-REF 06]`
4.9.5 A `StatelessSession` variant of the same job, with the memory and time comparison. `[BUILD]`
      `[NUM]`
4.9.6 A `JdbcTemplate.batchUpdate` variant and a PostgreSQL `COPY` variant as the upper bound.
      `[BUILD]` `[NUM]`
4.9.7 An N+1 reproduction and its four fixes, each with the asserted statement count:
      `join fetch`, `@EntityGraph`, `@BatchSize(50)`, projection. `[BUILD]` `[NUM]` `[PROVE]`
4.9.8 **Diff vs the real one:** datasource-proxy's listener API, Hibernate `Statistics`'
      counter set, JMH's warmup/fork discipline versus a naive timer, and why a single-JVM benchmark
      understates network round-trip cost. `[NUM]` `[X-REF 06]`

*(8 leaves)*

## §4.10 Optimistic locking with retry

4.10.1 A versioned entity plus a hand-written `update ... where id = ? and version = ?` and a row-count
       check that throws — the mechanism without Hibernate. `[BUILD]` `[SQL]`
4.10.2 A two-thread test that reliably produces the conflict (a `CountDownLatch` between read and
       write). `[BUILD]` `[X-REF 05]`
4.10.3 A retry wrapper: re-read, re-apply a function, re-commit, with jittered exponential backoff
       and a max-attempts cap; then the `@Retryable` equivalent with the boundary note from §1.28.6.
       `[BUILD]`
4.10.4 A test proving §2.13.3: a retry that does **not** re-read loops until it exhausts attempts.
       `[BUILD]` `[PROVE]`
4.10.5 The atomic-decrement alternative from §2.13.5 with a 100-thread test showing zero oversell and
       zero retries. `[BUILD]` `[NUM]` `[PROVE]`
4.10.6 A `SKIP LOCKED` job-queue poller with N workers, asserting disjoint claim sets. `[BUILD]`
       `[PROVE]` `[X-REF 14]`
4.10.7 **Diff vs the real one:** `EntityUpdateAction`'s `Expectation`, `VersionJavaType.next`,
       `OPTIMISTIC_FORCE_INCREMENT`'s `EntityIncrementVersionProcess`, batched-update row-count
       verification, Spring's exception translation layer, and Spring Retry's interceptor.
       `[NUM]`

*(7 leaves)*

## §4.11 A mini second-level cache with soft locks

4.11.1 A `MiniRegion` interface (`get`, `putFromLoad`, `lockItem`, `unlockItem`, `remove`,
       `evictAll`) mirroring `EntityDataAccess`. `[BUILD]`
4.11.2 A `NonStrictReadWriteRegion`: plain map, invalidate after commit. `[BUILD]`
4.11.3 A `ReadWriteRegion` with a `SoftLock` marker, a lock timeout, and readers that fall through to
       the database on a lock. `[BUILD]` `[PROVE]`
4.11.4 A two-thread test showing the `NONSTRICT_READ_WRITE` staleness window actually occurring, and
       the same test passing under `READ_WRITE` — the empirical proof of §3.12.4 and §3.12.5.
       `[BUILD]` `[PROVE]` `[X-REF 05]`
4.11.5 A timestamps region and a query-result cache on top of it, plus a test showing one write to a
       table invalidating every cached query over it — the proof of §3.12.9. `[BUILD]` `[PROVE]`
4.11.6 A test showing a bulk update leaving the cache stale, and the manual `evict` that fixes it.
       `[BUILD]` `[PROVE]`
4.11.7 **Diff vs the real one:** `RegionFactory`/`DomainDataRegion` SPI shape, `CacheEntry`
       disassembly via the persister, the real `SoftLock` implementation with a lock counter and
       expiry, tenant-aware keys, cluster invalidation, and `use_minimal_puts`. `[NUM]`

*(7 leaves)*

## §4.12 A schema-drift and mapping-audit tool

4.12.1 A test that boots the app against a Flyway-migrated Testcontainer with `ddl-auto=validate`
       and asserts success — the §2.19.9 test, shipped. `[BUILD]`
4.12.2 A metamodel walker that reports every association with `FetchType.EAGER`, every `@ManyToMany`,
       every collection with no `@BatchSize`, every entity with a Lombok `@Data`, and every
       `@Enumerated` left at `ORDINAL`. Fail the build on the ones you have banned. `[BUILD]`
       `[PROVE]`
4.12.3 An ArchUnit rule set enforcing §2.7.1 and §2.22 (no entity in a controller signature, no
       `jakarta.persistence` import outside the persistence package, no `@Transactional` on a
       controller). `[BUILD]` `[X-REF 16]`
4.12.4 A startup report that logs, per entity, the pre-generated insert/update SQL and the fetch
       plan — so a reviewer sees what the mapping actually produced. `[BUILD]` `[DIAG]`
4.12.5 **Diff vs the real one:** `SchemaValidatorImpl`'s metadata comparison, what `validate` does not
       check (§1.30.4), and why a real tool would compare against a migration-generated snapshot
       rather than live metadata. `[NUM]`

*(5 leaves)*

---

**PART 4 total: 7+7+6+7+7+8+7+7+8+7+7+5 = 83 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question set

Grouped by block. Each carries the expected depth: **[L1]** name it, **[L2]** explain the mechanism,
**[L3]** prove it or trace it to source.

### Persistence context and states

5.1.1 What is the persistence context, and what two jobs does it do? **[L2]**
5.1.2 Name the four entity states and every transition. **[L1]**
5.1.3 Why does an UPDATE happen when I never called `save`? **[L2]**
5.1.4 I mutated an entity and returned early without saving — what is in the database? **[L2]**
5.1.5 Is flush the same as commit? What exactly does each do? **[L2]**
5.1.6 When does auto-flush fire, and when does it not? **[L3]**
5.1.7 Why does a native query see stale data, and how do you fix it? **[L3]**
5.1.8 What does `readOnly = true` actually change? **[L3]**
5.1.9 Two `find` calls for the same id in one transaction — how many SELECTs, and are the objects
      `==`? **[L2]**
5.1.10 The same row loaded in two transactions — are the objects equal? **[L2]**
5.1.11 What is stored in the loaded-state snapshot, and what does it cost? **[L3]**
5.1.12 What does `clear()` do to a proxy you are already holding? **[L3]**
5.1.13 Difference between `detach`, `clear`, `evict` and `close`. **[L1]**
5.1.14 What is an extended persistence context and why do you not use one? **[L2]**
5.1.15 Why does my exception come from `commit` instead of from `save`? **[L2]**

### persist / merge / save

5.1.16 `persist` vs `merge` — arguments, return values, and which one mutates what. **[L2]**
5.1.17 Show me the returned-copy bug. **[L2]**
5.1.18 Why does `merge` issue a SELECT? **[L3]**
5.1.19 How does Spring Data `save` decide between persist and merge? **[L3]**
5.1.20 I use assigned UUID keys and every insert does a SELECT first. Why, and how do you fix it?
       **[L3]**
5.1.21 Why must a `@Version` field be `Long` and not `long` for `isNew` detection? **[L3]**
5.1.22 A form edit nulled three columns. What happened? **[L2]**
5.1.23 When does the INSERT actually execute for IDENTITY vs SEQUENCE? **[L3]**
5.1.24 `deleteAll()` vs `deleteAllInBatch()` — statements, callbacks, orphans. **[L2]**
5.1.25 `remove()` on a detached entity? **[L1]**
5.1.26 Delete then insert the same unique key in one transaction — what happens and why? **[L3]**

### Mapping

5.1.27 What does JPA require of an entity class, and why each requirement? **[L2]**
5.1.28 Field access vs property access — how is it decided and why does it matter? **[L2]**
5.1.29 `@Entity(name=...)` vs `@Table(name=...)`. **[L1]**
5.1.30 Why is `@Enumerated` dangerous at its default? **[L2]**
5.1.31 `@Transient` vs `transient`. **[L1]**
5.1.32 Is `@Basic(fetch = LAZY)` honoured? Under what condition? **[L3]**
5.1.33 `@MappedSuperclass` vs `@Embeddable` vs an inheritance strategy. **[L2]**
5.1.34 The three inheritance strategies: SQL, cost, and the constraint each imposes. **[L2]**
5.1.35 Why can't `TABLE_PER_CLASS` use IDENTITY ids? **[L3]**
5.1.36 `@IdClass` vs `@EmbeddedId` vs `@MapsId`. **[L2]**
5.1.37 What does `@ElementCollection` do on update, and why? **[L3]**
5.1.38 `@OrderColumn` vs `@OrderBy` vs `@SQLOrder` vs `SortedSet`. **[L2]**
5.1.39 What is a `PersistentBag` and why does it matter? **[L3]**
5.1.40 What breaks if you replace a managed collection instance? **[L3]**
5.1.41 Owning side vs inverse side — which one produces the SQL? **[L2]**
5.1.42 I added to the collection and nothing was saved. Why? **[L2]**
5.1.43 What does a unidirectional `@OneToMany` without `@JoinColumn` generate? **[L2]**
5.1.44 Why does a unidirectional `@OneToMany` with `@JoinColumn` issue extra UPDATEs? **[L3]**
5.1.45 Why should you replace `@ManyToMany` with a join entity? **[L2]**
5.1.46 `CascadeType.REMOVE` vs `orphanRemoval`. **[L2]**
5.1.47 What does `orphanRemoval` cost at flush? **[L3]**
5.1.48 What is `TransientObjectException` telling you? **[L2]**
5.1.49 An `AttributeConverter` — what can it not do? **[L2]**
5.1.50 How do you store money, and how do you store an event timestamp? **[L1]**

### Identifiers

5.1.51 The five generation strategies and the SQL each produces. **[L1]**
5.1.52 What does `AUTO` resolve to on PostgreSQL and on MySQL? **[L2]**
5.1.53 Why does IDENTITY disable batching? **[L3]**
5.1.54 What is `allocationSize` and what must match it in the database? **[L3]**
5.1.55 `pooled` vs `pooled-lo` — which value does the database hold? **[L3]**
5.1.56 Why are random UUID primary keys a performance problem? **[L3]**
5.1.57 When is a natural key an acceptable primary key? **[L2]**
5.1.58 When is the id populated — at `persist` or at flush? **[L3]**

### Fetching and N+1

5.1.59 The default fetch type of each association, and which defaults are wrong. **[L1]**
5.1.60 Can you make an EAGER association lazy for one query? **[L3]**
5.1.61 Explain `LazyInitializationException` in one sentence. **[L1]**
5.1.62 Rank the fixes for it. **[L2]**
5.1.63 Why can an optional inverse `@OneToOne` not be lazy? **[L3]**
5.1.64 What does `getReferenceById` return, and when does it blow up? **[L2]**
5.1.65 Why does `instanceof` fail on a lazy association in a hierarchy? **[L3]**
5.1.66 Name five distinct shapes of N+1. **[L3]**
5.1.67 Why does `em.find` join an eager association but a JPQL query does not? **[L3]**
5.1.68 How do you detect N+1 in CI rather than in production? **[L2]**
5.1.69 `join fetch` vs `@EntityGraph` vs `@BatchSize` vs projection — pick one for each of four
       scenarios. **[L2]**
5.1.70 What is `@BatchSize(50)`'s statement count for 1000 parents? **[L2]**
5.1.71 What is the single highest-value global setting for N+1? **[L2]**
5.1.72 Fetch graph vs load graph. **[L3]**
5.1.73 Why does `MultipleBagFetchException` exist at all? **[L3]**
5.1.74 Two collection fetches with `Set`s — what do you get instead? **[L2]**
5.1.75 Explain `HHH000104` and fix it. **[L3]**
5.1.76 What does `FetchMode.SUBSELECT` do and when is it the right choice? **[L2]**

### Queries and repositories

5.1.77 How does a derived query method become SQL? **[L3]**
5.1.78 Why does a typo in a method name fail at startup? **[L3]**
5.1.79 Why is `findByAddressZipCode` ambiguous, and how do you disambiguate it? **[L2]**
5.1.80 What is validated at startup and what is not? **[L2]**
5.1.81 Closed vs open projection — what changes in the SQL? **[L3]**
5.1.82 What is the interface projection at runtime? **[L3]**
5.1.83 Why does a nested projection still materialise the join? **[L2]**
5.1.84 `Page` vs `Slice` vs `Window` — statement counts. **[L2]**
5.1.85 Why is `Sort` ignored on a native query? **[L3]**
5.1.86 Why is offset pagination slow and unstable, and what replaces it? **[L2]**
5.1.87 What does keyset pagination require of your sort? **[L2]**
5.1.88 `@Modifying` — what does it bypass, and what do the two attributes fix? **[L2]**
5.1.89 A bulk update and a `@Version` column — what goes wrong? **[L3]**
5.1.90 Why does a `Specification` with a `fetch` break a `Page` query? **[L3]**
5.1.91 Specifications vs QueryDSL vs Query by Example — pick and defend. **[L2]**
5.1.92 What is the query-plan cache and how do you defeat it? **[L3]**
5.1.93 HQL features that JPQL lacks — name five. **[L2]**
5.1.94 How do you write "top 3 per group" in Hibernate 6? **[L2]**
5.1.95 How does the repository proxy decide what to do with a method call? **[L3]**
5.1.96 How is a custom `XxxImpl` fragment composed in? **[L2]**
5.1.97 What does `BootstrapMode.LAZY` cost you? **[L2]**

### Transactions, locking, concurrency

5.1.98 Where do transaction boundaries belong and why? **[L2]**
5.1.99 What happens if you call a repository with no transaction at all? **[L3]**
5.1.100 Which transaction manager does Boot configure, and what breaks with the wrong one? **[L3]**
5.1.101 Is the injected `EntityManager` thread-safe? What is it actually? **[L3]**
5.1.102 What does `REQUIRES_NEW` cost in connections? **[L3]**
5.1.103 Why is a checked exception a rollback hazard? **[L2]**
5.1.104 Explain open-session-in-view and give four reasons to disable it. **[L2]**
5.1.105 What is delayed connection acquisition and what two settings enable it? **[L3]**
5.1.106 Under READ_COMMITTED, why did two reads in one transaction return the same value? **[L3]**
5.1.107 Explain `@Version` end to end, including the SQL. **[L2]**
5.1.108 How do you handle `OptimisticLockException` correctly? **[L2]**
5.1.109 When is optimistic locking the wrong choice? **[L2]**
5.1.110 `OPTIMISTIC` vs `OPTIMISTIC_FORCE_INCREMENT` — why would you bump a version you only read?
        **[L3]**
5.1.111 `PESSIMISTIC_WRITE`'s SQL and lock lifetime. **[L2]**
5.1.112 What is `SKIP LOCKED` for? **[L2]**
5.1.113 What is follow-on locking and how would you notice it? **[L3]**
5.1.114 Design an oversell-proof stock decrement. **[L3]**
5.1.115 Insert race on a unique constraint — pre-check or catch? **[L2]**

### Caching, batching, operations

5.1.116 L1 vs L2 vs query cache — scope, contents, invalidation. **[L2]**
5.1.117 What is actually stored in L2? **[L3]**
5.1.118 Explain the `READ_WRITE` soft-lock protocol. **[L3]**
5.1.119 Why is `NONSTRICT_READ_WRITE` inconsistent, and for how long? **[L3]**
5.1.120 Why is the query cache usually a net loss? **[L3]**
5.1.121 Why is L2 dangerous across instances, and what invalidates nothing? **[L2]**
5.1.122 What settings does JDBC insert batching require — including on the driver? **[L3]**
5.1.123 Why does `order_inserts` matter? **[L3]**
5.1.124 How do you verify batching is actually happening? **[L2]**
5.1.125 Insert one million rows — describe your approach. **[L2]**
5.1.126 What does `StatelessSession` give up, and what does it buy? **[L2]**
5.1.127 `ddl-auto` values, and what belongs in production. **[L1]**
5.1.128 What does `validate` check and not check? **[L3]**
5.1.129 How do two replicas both running Flyway not corrupt the schema? **[L2]**
5.1.130 How do you find the slowest query in production? **[L2]**
5.1.131 What do you put on a persistence-layer dashboard? **[L2]**
5.1.132 Why is H2 a bad test database? **[L2]**
5.1.133 Why does a `@DataJpaTest` assertion pass when the mapping is broken? **[L3]**

### Design and judgement

5.1.134 When would you not use JPA? **[L2]**
5.1.135 Entities or DTOs at the layer boundary — defend your answer against the boilerplate
        objection. **[L2]**
5.1.136 Design the equals/hashCode for an entity, and prove your choice. **[L3]**
5.1.137 Why is `@Data` on an entity wrong — name three separate failures. **[L2]**
5.1.138 Model a multi-tenant schema and say what enforces isolation. **[L2]**
5.1.139 You inherit a service with 400 ms p99 on a detail endpoint. Walk your diagnosis. **[L3]**
5.1.140 What changed between Hibernate 5 and 6 that matters to you? **[L2]**
5.1.141 What breaks when you move to Hibernate 7? **[L2]**
5.1.142 Explain ORM to a sceptic who wants raw SQL, fairly. **[L2]**

*(142 leaves)*

## §5.2 The trap index

One line each. This is the daily-review list.

5.2.1 Mutating a managed entity commits, even with no `save` and an early return.
5.2.2 `save()` on a managed entity is a no-op, not a "make sure".
5.2.3 Flush is not commit.
5.2.4 Auto-flush does not fire before a native query.
5.2.5 `readOnly = true` sets flush mode `MANUAL`, so an explicit `save` may do nothing.
5.2.6 `merge` returns a new instance; changes to the argument are lost.
5.2.7 `merge` does a hidden SELECT.
5.2.8 `merge` of a partially-populated detached entity nulls columns.
5.2.9 An assigned id makes `save` do `merge`, so a SELECT precedes every INSERT.
5.2.10 A primitive `@Version` cannot signal newness.
5.2.11 `remove()` on a detached entity throws.
5.2.12 Deletes run **last** in the flush order, so delete-then-insert on a unique key fails.
5.2.13 `persist` on a removed entity resurrects it.
5.2.14 `refresh()` discards your unflushed changes.
5.2.15 `clear()` silently discards pending changes.
5.2.16 The exception surfaces at `commit`, not at `save`, so your `try/catch` misses it.
5.2.17 `getSingleResult()` throws on zero rows.
5.2.18 `getResultStream()` must be closed inside the transaction.
5.2.19 `@ManyToOne` and `@OneToOne` default to EAGER.
5.2.20 EAGER cannot be made lazy per query; LAZY can be made eager. The asymmetry is the argument.
5.2.21 An optional inverse `@OneToOne` is never really lazy.
5.2.22 `@Basic(fetch = LAZY)` is ignored without bytecode enhancement.
5.2.23 A `final` getter on an entity returns garbage on a proxy.
5.2.24 `proxy.getClass()` is a generated subclass; `instanceof` and naive `equals` break.
5.2.25 `getReferenceById` throws `EntityNotFoundException` far from the call site.
5.2.26 `em.find` joins an eager association; a JPQL query issues N extra selects instead.
5.2.27 Two collection `join fetch`es throw `MultipleBagFetchException`.
5.2.28 Two collection fetches with `Set`s give a cartesian product instead of an exception.
5.2.29 `Pageable` plus a collection fetch loads the whole table into heap (`HHH000104`).
5.2.30 `@EntityGraph` on a `Page` method has the same problem.
5.2.31 `distinct` in a fetch query does not mean `select distinct` in Hibernate 6.
5.2.32 A `HashSet` of entities with generated ids loses members.
5.2.33 Entity `hashCode` must not depend on a generated id.
5.2.34 Lombok `@Data`/`@EqualsAndHashCode`/`@ToString` on an entity triggers lazy loads and recursion.
5.2.35 Records cannot be entities.
5.2.36 Replacing a managed collection instance breaks orphan removal.
5.2.37 A null-initialised collection field NPEs your helper method.
5.2.38 Adding to the inverse side only persists nothing.
5.2.39 A unidirectional `@OneToMany` without `@JoinColumn` creates a join table.
5.2.40 A unidirectional `@OneToMany` with `@JoinColumn` issues an UPDATE per child.
5.2.41 `@ManyToMany` on a `List` deletes and re-inserts the whole join table.
5.2.42 `@ElementCollection` deletes and re-inserts all rows on any change.
5.2.43 `CascadeType.ALL` on a `@ManyToOne` deletes the parent.
5.2.44 `orphanRemoval` forces the collection to load at flush.
5.2.45 `@OnDelete(CASCADE)` bypasses JPA and leaves the caches wrong.
5.2.46 `@Enumerated` defaults to `ORDINAL`.
5.2.47 A `SINGLE_TABLE` hierarchy cannot have `NOT NULL` on subclass columns.
5.2.48 `TABLE_PER_CLASS` cannot use IDENTITY ids.
5.2.49 `@MappedSuperclass` is not polymorphically queryable.
5.2.50 `@Table` on a `SINGLE_TABLE` subclass now throws (Hibernate 6.6).
5.2.51 `IDENTITY` ids silently disable insert batching.
5.2.52 `allocationSize` must equal the sequence's `INCREMENT BY`.
5.2.53 `pooled` and `pooled-lo` disagree about what the database value means.
5.2.54 `GenerationType.AUTO` means different things per database and changed in Hibernate 6.
5.2.55 Random UUID primary keys fragment every index.
5.2.56 `hibernate.jdbc.batch_size` without `reWriteBatchedInserts`/`rewriteBatchedStatements` is
       still N round trips.
5.2.57 `@DynamicUpdate` defeats statement caching.
5.2.58 A query in the middle of a batch loop forces an early flush and breaks the batch.
5.2.59 `saveAll` is a loop, not a batch.
5.2.60 100k entities in one context is quadratic dirty checking, then OOM.
5.2.61 `@Modifying` bypasses the context: no dirty check, no cascade, no version, stale L1.
5.2.62 `clearAutomatically = true` detaches everything the caller was holding.
5.2.63 A bulk update does not bump `@Version` or fire `@PreUpdate`.
5.2.64 A bulk delete leaves orphans or violates an FK.
5.2.65 `deleteAllInBatch` skips callbacks, cascades and orphan removal.
5.2.66 `open-in-view` is **true** by default in Boot.
5.2.67 OSIV runs lazy loads outside any transaction, in the serialisation path.
5.2.68 OSIV holds a pooled connection for the whole request.
5.2.69 `enable_lazy_load_no_trans=true` converts an exception into N single-transaction queries.
5.2.70 `@Transactional` on a repository gives no cross-write atomicity.
5.2.71 No transaction at all means everything is detached immediately.
5.2.72 `DataSourceTransactionManager` with JPA splits `JdbcTemplate` and the `EntityManager` onto two
       connections.
5.2.73 `REQUIRES_NEW` holds two connections and cannot see the outer transaction's pending writes.
5.2.74 A checked exception commits the transaction.
5.2.75 Catching inside a `@Transactional` method leaves the context undefined and commit throws.
5.2.76 The L1 cache gives repeatable reads the isolation level never promised.
5.2.77 `@Transactional(timeout)` is seconds; `jakarta.persistence.query.timeout` is milliseconds.
5.2.78 An HTTP call inside a transaction holds a connection and locks for the remote timeout.
5.2.79 Catching `OptimisticLockException` without re-reading retries the same conflict forever.
5.2.80 A retry inside the transaction boundary is not a retry.
5.2.81 `existsBy` then `save` is a TOCTOU race.
5.2.82 Follow-on locking turns one `FOR UPDATE` into N.
5.2.83 A lock timeout is silently ignored on dialects that do not support it.
5.2.84 L2 is per-JVM unless the cache is clustered.
5.2.85 Nothing invalidates L2 after a bulk update, a native write, Flyway, or a DBA.
5.2.86 The query cache stores ids, not rows, and one write invalidates the whole space.
5.2.87 `@Cacheable` on a repository method caches detached entities with dead proxies.
5.2.88 An entity in a static map or an HTTP session is a leak plus a landmine.
5.2.89 Sending an entity to another thread is a data race.
5.2.90 `@Async` repositories have no transaction and no `EntityManager`.
5.2.91 Publishing an event from `@PostPersist` publishes before durability.
5.2.92 Bean Validation on an entity throws from `commit`, not from `save`.
5.2.93 An `@Autowired` field in an `AttributeConverter` or listener is null without
       `SpringBeanContainer`.
5.2.94 Auditing silently does nothing without `@EntityListeners(AuditingEntityListener.class)`.
5.2.95 Auditing misses every bulk statement.
5.2.96 Envers doubles your writes and couples to every mapping change.
5.2.97 Soft delete breaks unique constraints, FKs, index selectivity and every count.
5.2.98 `ddl-auto=update` never drops or renames and diverges silently.
5.2.99 `spring.jpa.*` keys that Hibernate owns are silently ignored — use `spring.jpa.properties.*`.
5.2.100 `spring.jpa.show-sql` shows no bind parameters.
5.2.101 An `@EntityScan`/main-class package mistake means no entities are found.
5.2.102 `PagingAndSortingRepository` no longer extends `CrudRepository` (Spring Data 3.0).
5.2.103 `@NoRepositoryBean` missing on a base interface breaks startup.
5.2.104 `Sort` is ignored on a native query.
5.2.105 Native queries are not validated at startup.
5.2.106 A `Specification` with `root.fetch` breaks the generated count query.
5.2.107 Two specifications joining the same association produce a duplicate join.
5.2.108 An open projection loads the whole entity.
5.2.109 A nested projection materialises the whole join.
5.2.110 Mutating a projection does nothing, silently.
5.2.111 `Page<Entity>` from a controller serialises the graph and has unstable JSON.
5.2.112 Pagination without a unique tiebreaker shuffles rows between pages.
5.2.113 Keyset pagination without the tiebreaker loses rows.
5.2.114 `BootstrapMode.LAZY` moves query validation from boot to first call.
5.2.115 `JpaSort.unsafe` with request input is an injection surface.
5.2.116 SpEL in `@Query` is an injection surface.
5.2.117 A dynamically-built query string thrashes both plan caches.
5.2.118 H2 is not your database.
5.2.119 A `@DataJpaTest` assertion without `flush()`/`clear()` asserts against L1.
5.2.120 A `@Transactional` test rolls back, so `AFTER_COMMIT` never fires.
5.2.121 `javax.persistence` does not exist any more.
5.2.122 `session.save/update/delete/load/get` are gone in Hibernate 7.
5.2.123 `@GenericGenerator` is deprecated; `@Where`/`@OrderBy` (Hibernate's) are removed in 7.
5.2.124 `StatelessSession` uses L2 by default in Hibernate 7.
5.2.125 `@MapsId` no longer implies `cascade = PERSIST` in Hibernate 7.
5.2.126 Fixing N+1 does not help if the FK has no index.
5.2.127 The ORM did not remove the need to read the SQL.

*(127 leaves)*

## §5.3 Drills and retention

5.3.1 **The 30-second persistence-context story:** an identity map plus a snapshot; at flush it
      diffs, orders the actions, and writes.
5.3.2 **The 30-second lazy-loading story:** the field holds a proxy or a collection wrapper; touching
      it needs its session; no session, exception.
5.3.3 **The 30-second N+1 story:** one query for parents, one per parent for the association; fix by
      declaring the fetch plan or by not loading entities.
5.3.4 **The 30-second `save` story:** `isNew` decides persist or merge; merge selects then copies;
      dirty checking makes both redundant on a managed entity.
5.3.5 **The 30-second repository story:** a proxy; the method name is parsed into a Criteria query at
      startup; the return type picks an execution strategy.
5.3.6 **The 30-second flush-order story:** orphan removals, inserts, updates, collection actions,
      deletes — deletes last.
5.3.7 **Numbers drill** — recite from memory: `@Column(length)` **255**, `allocationSize` **50**,
      sequence suffix `_SEQ`, `plan_cache_max_size` **2048**, `plan_parameter_metadata_max_size`
      **128**, Hikari `maximum-pool-size` **10**, `connection-timeout` **30000 ms**,
      `max-lifetime` **1800000 ms**, `spring.data.web.pageable.default-page-size` **20**,
      `max-page-size` **2000**, `repositoryImplementationPostfix` `Impl`,
      `escapeCharacter` `\`, discriminator column `DTYPE`, lock timeout `0` = NOWAIT / `-2` =
      SKIP LOCKED, batch size working range **20–100**. `[NUM]`
5.3.8 **Class-name drill** — for each behaviour name the class: holds the identity map; holds the
      dirty-check snapshot; orders flush actions; creates lazy proxies; parses HQL; translates SQM to
      SQL; caches query plans; generates ids in blocks; implements `save`; parses a derived method
      name; decides whether a projection is closed; binds the `EntityManager` to the thread; opens
      the session for the whole request; converts a Hibernate exception to a Spring one.
5.3.9 **Ordering drill** — put in order: `@PrePersist`, the INSERT, `@PostPersist`, the version
      increment, the dirty check, `@PreUpdate`, the UPDATE, the DELETE, orphan removal, the L2 soft
      lock, `beforeCompletion`, the JDBC commit, `@TransactionalEventListener(AFTER_COMMIT)`.
5.3.10 **SQL-prediction drill** — for fifteen code snippets, write the exact SQL Hibernate emits and
       the count, before running it. `[SQL]`
5.3.11 **Statement-count drill** — for ten endpoint shapes, state the budget and the actual count.
       `[NUM]`
5.3.12 **Diagnosis drill** — for each of twelve symptoms, name the first log category or command you
       would run. `[DIAG]`
5.3.13 **Version drill** — for each of the fifteen claims in §2.21.7, say whether it is true in
       Hibernate 6.6 / Spring Data 3.5 and what changed. `[VERSION-TRAP]`
5.3.14 **Whiteboard drill** — draw the entity state machine (4 states, 9 transitions) and the flush
       order (8 action types) from memory in under three minutes.
5.3.15 **Code-review drill** — a 120-line service + entity + repository with fifteen planted bugs
       from §5.2; find them all in fifteen minutes.
5.3.16 **Mapping-review drill** — a 60-line entity with eight mapping mistakes (EAGER defaults,
       `@Data`, `ORDINAL`, `@ManyToMany`, unidirectional `@OneToMany`, cascade on the child side,
       `LocalDateTime`, `double` money).
5.3.17 **The two-minute answer template** for any "why did this query happen / not happen" question:
       is there a transaction → is the entity managed → what is the flush mode → is the field dirty →
       what does the fetch plan say → what does the action queue order say.
5.3.18 Spaced repetition plan: §5.2 daily, §5.1 by block weekly, PART 3 once before the onsite, and
       the SQL-prediction drill (§5.3.10) twice.
5.3.19 The one-sentence summary of the whole guide: **the persistence context is a write-behind cache
       with an identity map, and every surprise in JPA is that cache doing its job at a moment you
       did not expect.**

*(19 leaves)*

---

**PART 5 total: 142+127+19 = 288 leaves**

---

## Sources consulted

Primary sources first. Where a fetch failed or a search returned only secondary material, that is
stated rather than padded. Every `[RESEARCH]` leaf must be re-verified against the source named here
before the write pass commits a constant, a default or an API shape to the page.

**Jakarta Persistence specification (primary)**

- <https://jakarta.ee/specifications/persistence/3.1/> — the spec landing page. Source of the 3.1
  feature set used in §1.2.3 and §1.19.11: `GenerationType.UUID` and `java.util.UUID` as a basic
  type, the `CEILING`/`EXP`/`FLOOR`/`LN`/`POWER`/`ROUND`/`SIGN` numeric functions in JPQL and the
  matching `CriteriaBuilder` methods, `LOCAL DATE`/`LOCAL TIME`/`LOCAL DATETIME`, and
  `EntityManager`/`EntityManagerFactory` extending `AutoCloseable`. Consulted via search summary
  plus the Eclipse newsletter below; **the PDF itself was not fetched — the write pass must open it
  for the `EntityManager` method list (§1.4.1), the legal `@Id` types (§1.9.10) and the entity
  requirements (§1.9.1) rather than quoting recall.**
- <https://newsroom.eclipse.org/eclipse-newsletter/2022/march/what%E2%80%99s-new-jakarta-persistence-31>
  and <https://projects.eclipse.org/projects/ee4j.jpa/releases/3.1> — corroborated the 3.1 feature
  list above. `[RESEARCH]`
- Jakarta Persistence **3.2** was reached only through the Hibernate 7.0 migration guide (below):
  the generified Criteria/`EntityGraph` API, `EntityManagerFactory#getSchemaManager`,
  `Order#getNullPrecedence()` returning `Nulls`, and nullable `Transaction#getTimeout`. Every 3.2
  claim in §1.2.4 and §1.20.16 is `[VERSION-TRAP]` + `[RESEARCH]` and must be checked against the
  3.2 spec text.

**Hibernate ORM documentation (primary)**

- <https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html> — the 6.6
  User Guide, the baseline document for this file. The **Fetching** chapter was fetched and is the
  source of §1.17's concept inventory: `FetchType`, the `@Fetch` annotation, `FetchMode.SELECT` /
  `SUBSELECT` / `JOIN`, `@BatchSize`, the `LEGACY`/`PADDED`/`DYNAMIC` batch-fetch styles behind
  `hibernate.batch_fetch_style`, `hibernate.default_batch_fetch_size`, fetch-graph vs load-graph
  semantics, `@LazyCollection`, `HibernateProxy`, `Hibernate.initialize()`, and bytecode-enhanced
  lazy attribute loading. **The chapters on flushing, locking, caching, batching, multi-tenancy,
  bootstrap and mapping were not fetched in full in this pass** — §1.9–§1.16, §1.29, §2.11, §2.17
  and all of PART 3 that names a User Guide concept are tagged `[RESEARCH]` and must be read against
  this document before the write pass asserts a setting name or default.
- <https://docs.hibernate.org/orm/6.6/migration-guide/> — fetched in full. Source of every
  6.6-specific delta in §1.10.10, §1.12.7, §1.15.5, §1.20.13, §1.8.8 and §2.10.9: the Oracle
  implicit array-type renaming (`BigIntegerArray` → `BigIntegerBigDecimalArray`), the
  `OptimisticLockException` on merging a versioned detached entity with no matching row (generated
  `@Id` or non-primitive `@Version` only), automatic `@Embeddable` type inheritance with a
  discriminator, H2 switching to **global** temporary tables for multi-table bulk mutations,
  `Expression.as()` becoming an unsafe typecast with `JpaExpression.cast()` as the replacement,
  `@Table` on a `SINGLE_TABLE` subclass now raising a mapping exception, the `array_contains()`
  deprecation in favour of `array_includes()`/`INCLUDES`, `UserDefinedType` becoming an interface
  with `UserDefinedObjectType`/`UserDefinedArrayType`, and the "either `@MappedSuperclass`,
  `@Embeddable`, or `@Entity`" validation.
- <https://docs.hibernate.org/orm/7.0/migration-guide/migration-guide.html> — fetched in full.
  Source of the entire Hibernate 7 block in the header, §1.4.5–§1.4.6, §1.5.8, §1.16.1, §1.16.11,
  §1.19.21, §1.29.4, §1.29.16 and §2.21.4: the removal list (`@Persister`, `@Proxy`,
  `@SelectBeforeUpdate`, `@Loader`, `org.hibernate.annotations.@Table`, `@Where`,
  `@WhereJoinTable`, `@OrderBy`, `@ForeignKey`, `@Index`, `@IndexColumn`, `@GeneratorType`,
  `@LazyToOne`, `@LazyCollection`, `@Target`, `@Cache#include`), the replacements
  (`@TargetEmbeddable`, `@SQLRestriction`, `@SQLJoinTableRestriction`, `@SQLOrder`,
  `CacheMode` for `CacheModeType`), the `Session` method renames, the `CascadeType.SAVE_UPDATE`/
  `DELETE` removals, the implicit-select query rejection, the detached-`refresh` prohibition,
  `StatelessSession` using L2 by default and no longer honouring `hibernate.jdbc.batch_size`,
  `@MapsId` losing its implicit `PERSIST` cascade, native-query temporals defaulting to `java.time`
  with `hibernate.query.native.prefer_jdbc_datetime_types` as the opt-out, immutable-entity update
  queries throwing with
  `hibernate.query.immutable_entity_update_query_handling_mode=allow` as the opt-out,
  `char`→`varchar(1)`, the new `FindOption`/`LockOption`/`Timeouts`/`PessimisticLockScope` options,
  `SelectionSpecification.sort()`, `StatelessSession#insertMultiple/updateMultiple/deleteMultiple`,
  and the removed `hibernate.mapping.precedence` / `hibernate.allow_refresh_detached_entity`
  settings.
- <https://docs.hibernate.org/orm/7.0/whats-new/> and <https://hibernate.org/orm/releases/7.0/> —
  consulted via search summary for the 7.0 headline list (Java 17 baseline, Jakarta Persistence 3.2,
  Hibernate Models, `@SoftDelete` with `TIMESTAMP`, `@EmbeddedColumnNaming`, Hibernate's own
  `@NamedEntityGraph`, `findMultiple()`/`getMultiple()`). Basis of §3.1.4 and §2.3.12.
  **Not fetched — re-verify.** `[RESEARCH]`
- <https://docs.hibernate.org/orm/6.5/migration-guide/> and
  <https://docs.hibernate.org/orm/6.2/migration-guide/> — reached via the migration-guide index only.
  The `@GenericGenerator` deprecation (6.5), CTE support (6.2) and `@SQLRestriction` (6.2/6.3) in
  §1.2.5, §1.11.15 and §2.21.3 come from search summaries and are `[RESEARCH]`.
- <https://docs.hibernate.org/orm/6.2/querylanguage/html_single/> — *A Guide to Hibernate Query
  Language*, named in §1.2.9. **Not fetched.** It is the correct source for §1.19.14–§1.19.16 (set
  operations, CTEs, window functions, the function registry) and the write pass must read it rather
  than trusting the blog summaries below. `[RESEARCH]`
- <https://docs.hibernate.org/stable/core/javadocs/org/hibernate/annotations/CacheConcurrencyStrategy.html>
  and
  <https://github.com/hibernate/hibernate-orm/blob/main/hibernate-core/src/main/java/org/hibernate/annotations/CacheConcurrencyStrategy.java>
  — consulted via search summary. Source of the four concurrency strategies and their javadoc
  wording used in §1.29.5, §3.12.4 and §3.12.5, including the `READ_WRITE` soft-lock description
  ("a soft lock is stored in the cache … released after the transaction is committed, and all
  concurrent transactions that access soft-locked entries will fetch the corresponding data directly
  from the database") and the `NONSTRICT_READ_WRITE` inconsistency window. **The write pass should
  quote the javadoc directly from the 6.6 branch.** `[RESEARCH]`
- <https://docs.hibernate.org/orm/6.0/javadocs/org/hibernate/id/enhanced/SequenceStyleGenerator.html>
  — consulted via search summary for §3.8.2's parameter names and the table-fallback behaviour.
  `[RESEARCH]`
- <https://docs.hibernate.org/stable/core/javadocs/org/hibernate/cfg/JdbcSettings.html> — surfaced
  as the authoritative home of the `hibernate.connection.*` and `hibernate.jdbc.*` setting names in
  §1.31.2 and §2.12.8. **Not fetched — this is the single best source for the write pass to verify
  every JDBC-related property key and default.** `[RESEARCH]`
- <https://in.relation.to/2022/03/31/orm-60-final/> and
  <https://in.relation.to/2023/02/20/hibernate-orm-62-ctes/> — the Hibernate team's own release
  posts. Consulted via search summary for §2.21.2 (SQM, the new type system, read-by-position) and
  CTE support. `[RESEARCH]`
- **Hibernate source not fetched in this pass.** Every leaf in §3.2–§3.15 that names a field, a map,
  a listener, an action-queue list, an optimizer method or a constant
  (`StatefulPersistenceContext`, `EntityEntry`, `EntityEntryContext`, `ActionQueue`,
  `AbstractFlushingEventListener`, `Default*EventListener`, `TwoPhaseLoad`, the 6.x
  `sql.results.graph` initializer tree, `BatchFetchQueue`, `AbstractLazyInitializer`,
  `PersistentBag`, `PooledOptimizer`/`PooledLoOptimizer`, `SequenceStyleGenerator`,
  `QueryInterpretationCacheStandardImpl`, `MutationExecutor*`, `SqlAstTranslator`,
  `EntityDataAccess`, `UpdateTimestampsCache`, `LockOptions`, `SqlExceptionHelper`) is tagged
  `[RESEARCH]` **wholesale**. The write pass must open each class on the `6.6` branch of
  <https://github.com/hibernate/hibernate-orm> and quote the relevant method before asserting
  anything. The highest-risk items are the **`ActionQueue` execution order** (§3.5.3), the
  `StatefulPersistenceContext` field list (§3.2.2), the `EntityEntry` field list (§3.2.4), the
  `PooledOptimizer`/`PooledLoOptimizer` arithmetic (§3.8.4–§3.8.5), and the query-plan cache
  defaults (§3.10.2).

**Spring Data JPA reference documentation (primary)**

- <https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html> — fetched in full.
  Source of §1.23.1–§1.23.2 (the complete subject-keyword and predicate-keyword tables with the JPQL
  each produces), the supported return types including `Window<T>`, the `@Query` attribute list
  (`value`, `nativeQuery`, `countQuery`, `name`, `queryRewriter`), `@NativeQuery` with
  `countQuery`/`resultSetMapping` and `Map<String,Object>` results, named queries via annotation and
  `orm.xml`, `Sort`/`JpaSort.unsafe`/sort-by-alias, `findTop10`/`findFirst10`, `Stream`,
  `Future`/`CompletableFuture`/`ListenableFuture`, the full SpEL surface (`#{#entityName}`,
  `?#{[0]}`, `?#{escape([0])}` + `?#{escapeCharacter()}`, `?${property:default}`), `@Modifying` with
  `clearAutomatically`, `@QueryHints(forCounting = false)`, `@Meta(comment = ...)` with
  `hibernate.use_sql_comments=true`, `@EntityGraph` with `EntityGraphType.LOAD`, the offset and
  keyset **Scroll API** (`Window`, `WindowIterator`, `OffsetScrollPosition`, `KeysetScrollPosition`,
  `ScrollPosition.keyset()`), and `QueryRewriter.rewrite(String, Sort)`. Basis of §1.23, §1.24,
  §1.26 and §2.9.7–§2.9.8.
- <https://docs.spring.io/spring-data/jpa/reference/repositories/projections.html> — fetched in full.
  Source of all of §1.25: interface projections as runtime proxies, the **closed vs open**
  distinction and the explicit statement that open projections lose the query optimisation, the three
  open-projection forms (`@Value` with `target`, `@Value` with `@bean`, `@Value` with `args[0]`),
  `default` methods, the four nullable wrappers (`java.util.Optional`,
  `com.google.common.base.Optional`, `scala.Option`, `io.vavr.control.Option`), class-based DTO
  projections with records and `@PersistenceCreator`, dynamic projections via a `Class<T>` parameter,
  nested interface projections, the JPQL **constructor-expression rewriting** with its
  no-aliases/backs-off constraints, native-query DTO mapping and `@SqlResultSetMapping`, and the
  statement that "projections limit the selection to top-level properties … any nested properties
  resolving to joins select the entire nested property causing the full join to materialize"
  (§1.25.11).
- <https://docs.spring.io/spring-data/jpa/reference/jpa/entity-persistence.html> — fetched in full.
  Source of §1.8.11–§1.8.15: `save` delegating to `persist`/`merge`, the **three** new-entity
  detection strategies in order (version-and-id inspection, `Persistable.isNew()`, a custom
  `EntityInformation` via a `JpaRepositoryFactory` subclass), the note that a **primitive** version
  property cannot detect newness because JPA treats `0` as the first version, and the
  `@MappedSuperclass implements Persistable<ID>` + `@Transient boolean isNew` +
  `@PostPersist @PostLoad markNotNew()` recipe quoted verbatim.
- <https://docs.spring.io/spring-data/jpa/reference/jpa/transactions.html> — fetched in full.
  Source of §1.27.7, §1.27.8 and §2.12.2: `SimpleJpaRepository` supplying `readOnly = true` for
  reads and plain `@Transactional` for writes, redeclaring an inherited method to change its
  transaction attributes, the service-facade pattern, the statement that **declared query methods
  get no transaction configuration by default**, and the precise `readOnly` semantics — a JDBC-driver
  hint, plus Hibernate setting the **flush mode to `MANUAL`** and skipping dirty checks, with the
  explicit caveat that it does *not* prevent manipulating queries.
- <https://docs.spring.io/spring-data/jpa/reference/jpa/specifications.html> — consulted via search
  summary only. Basis of §2.8.2–§2.8.3. **The write pass must fetch this page to confirm the
  `JpaSpecificationExecutor` method list and the 3.5 `SelectionSpecification`/`DeleteSpecification`/
  `UpdateSpecification`/`PredicateSpecification` split (§2.8.8).** `[RESEARCH]`
- <https://docs.spring.io/spring-data/jpa/reference/data-commons/repositories/scrolling.html> —
  consulted via search summary. Corroborated §2.9.1's statement that offset scrolling makes most
  databases materialise the whole result before returning, and the keyset alternative. `[RESEARCH]`
- <https://docs.spring.io/spring-data/jpa/docs/current/api/org/springframework/data/jpa/domain/support/AuditingEntityListener.html>
  — surfaced in search; basis of §2.16.1. `[RESEARCH]`
- **Spring Data JPA source not fetched.** Every leaf in §3.15 naming a class
  (`JpaRepositoriesRegistrar`, `RepositoryConfigurationDelegate`, `RepositoryFactorySupport`,
  `QueryExecutorMethodInterceptor`, `RepositoryComposition`, `JpaQueryLookupStrategy`, `PartTree`,
  `PropertyPath`, `JpaQueryCreator`, `PartTreeJpaQuery`, `JpaQueryExecution` and its subclasses,
  `QueryUtils`/`QueryEnhancer`, `SimpleJpaRepository`, `JpaMetamodelEntityInformation`,
  `SpelAwareProxyProjectionFactory`, `ProjectingMethodInterceptor`, `AuditingHandler`) is
  `[RESEARCH]`. The write pass must read them on the `3.5.x` branch of
  <https://github.com/spring-projects/spring-data-jpa> and
  <https://github.com/spring-projects/spring-data-commons>. The highest-risk items are the
  **advice-chain order** (§3.15.3), the `PartTree` regexes (§3.15.7), the `PropertyPath` resolution
  algorithm (§3.15.8), the `JpaQueryExecution` subclass list (§3.15.12), and
  `ProjectionInformation.isClosed()` (§3.15.19).

**Spring Boot / Spring Framework (primary)**

- <https://docs.spring.io/spring-boot/3.4/api/java/org/springframework/boot/autoconfigure/orm/jpa/JpaProperties.html>
  — surfaced in search as the authoritative field list for §1.3.16. **Not fetched; verify the 3.5
  javadoc.** `[RESEARCH]`
- Boot reference *Data* chapter and *howto* database-initialization pages (several versions surfaced,
  including <https://docs.enterprise.spring.io/spring-boot/docs/3.1.14/reference/html/data.html>) —
  consulted via search summary. Source of the `ddl-auto` value list, the
  `OpenEntityManagerInViewInterceptor` registration and the "set `spring.jpa.open-in-view` to false"
  guidance (§2.12.3), `spring.jpa.defer-datasource-initialization` (§1.30.10),
  `spring.sql.init.mode` (§1.30.11), and `SpringPhysicalNamingStrategy`/
  `CamelCaseToUnderscoresNamingStrategy` (§1.9.11). **Only pre-3.5 versions of these pages were
  reachable in this pass — re-fetch the 3.5 pages; the naming-strategy class name and the
  `ddl-auto` default in particular changed across versions.** `[RESEARCH]` `[VERSION-TRAP]`
- **Spring's ORM source not fetched.** §3.14's classes (`SharedEntityManagerCreator`,
  `EntityManagerFactoryUtils`, `EntityManagerHolder`, `JpaTransactionManager`,
  `HibernateJpaDialect`, `OpenEntityManagerInViewInterceptor`,
  `LocalContainerEntityManagerFactoryBean`, `PersistenceManagedTypesScanner`) are `[RESEARCH]` and
  must be read on the `6.2.x` branch of <https://github.com/spring-projects/spring-framework>.
  The highest-risk items are `JpaTransactionManager.doBegin`'s exact sequence (§3.14.5) and the
  JPA→`DataAccessException` mapping table (§3.14.9).

**Version-delta sources**

- <https://spring.io/blog/2025/11/14/spring-data-2025-1-goes-ga/> and
  <https://github.com/spring-projects/spring-data-commons/wiki/Spring-Data-2026.0-Release-Notes> —
  consulted via search summary for the Spring Data **4.0** delta in the header, §1.22.15, §2.21.5
  and §3.15.23: Spring Framework 7, Jakarta EE 11 (JPA 3.2, Servlet 6.1), **AOT-generated
  repositories enabled by default** (the `spring.aot.repositories.enabled` property no longer needed),
  JSpecify null-safety across all modules, Jackson 3 with Jackson 2 deprecated, and vector-search
  repository methods backed by `hibernate-vector`. **Neither page was fetched directly; every 4.0
  claim is `[VERSION-TRAP]` + `[RESEARCH]`.**
- <https://spring.io/blog/2025/05/16/spring-data-2025-0-goes-ga/> — the 2025.0 (Spring Data JPA 3.5)
  GA post, which is this file's baseline. Consulted via search listing only. **Fetch it in the write
  pass to confirm the 3.5 specification-API split named in §2.8.8.** `[RESEARCH]`
- <https://github.com/spring-projects/spring-data-jpa/issues/3406> — the multi-tenancy
  "SessionFactory cannot be created without a tenant" issue referenced in §2.17.5. `[RESEARCH]`
- <https://github.com/spring-projects/spring-data-jpa/issues/3077> — keyset scrolling failing to
  extract values from a `Tuple` with interface projections, the basis of §2.9.9. **Check whether it
  is resolved in 3.5 before recommending the combination.** `[RESEARCH]`

**Expert deep-dives (secondary — used for concept names and failure taxonomies only)**

- <https://vladmihalcea.com/hibernate-facts-knowing-flush-operations-order-matters/> — the
  `ActionQueue` order list in §3.5.3 (`OrphanRemovalAction`, `AbstractEntityInsertAction`,
  `EntityUpdateAction`, `QueuedOperationCollectionAction`, `CollectionRemoveAction`,
  `CollectionUpdateAction`, `CollectionRecreateAction`, `EntityDeleteAction`) and the
  "transactional write-behind cache" framing in §1.6.1. **This is the single highest-value
  secondary source in the file and the single item most in need of source verification** — the write
  pass must confirm the order against `ActionQueue` itself. `[RESEARCH]`
- <https://vladmihalcea.com/hibernate-hidden-gem-the-pooled-lo-optimizer/> and
  <https://vladmihalcea.com/migrate-hilo-hibernate-pooled/> — the `pooled` vs `pooled-lo` semantics
  (§1.11.7–§1.11.8, §3.8.4–§3.8.5), the default being `pooled` when `allocationSize > 1`, the
  `hibernate.id.optimizer.pooled.preferred` global setting, and the absence of a per-generator way
  to select `pooled-lo` after `@GenericGenerator`'s deprecation. Corroborated by
  <https://discourse.hibernate.org/t/how-to-use-idgeneratortype-to-use-pooled-lo/9956> and
  <https://ntsim.uk/posts/how-to-use-hibernate-identifier-sequence-generators-properly/>.
  `[RESEARCH]`
- <https://vladmihalcea.com/why-you-should-always-use-hibernate-connection-provider_disables_autocommit-for-resource-local-jpa-transactions/>
  and <https://vladmihalcea.com/spring-transaction-connection-management/> — §2.12.8 and §2.15.2–
  §2.15.3: why the connection is acquired eagerly (Hibernate must inspect auto-commit), the
  `spring.datasource.hikari.auto-commit=false` +
  `hibernate.connection.provider_disables_autocommit=true` pairing, and the explicit warning that
  setting the Hibernate flag without the pool flag runs SQL **outside any transaction**.
  `[RESEARCH]`
- <https://vladmihalcea.com/how-does-hibernate-read_write-cachecoherencystrategy-work/> (and the
  matching `NONSTRICT_READ_WRITE` and `TRANSACTIONAL` posts) — the soft-lock protocol walked in
  §3.12.4–§3.12.7. `[RESEARCH]`
- <https://vladmihalcea.com/the-best-way-to-implement-equals-hashcode-and-tostring-with-jpa-and-hibernate/>
  and <https://vladmihalcea.com/hibernate-facts-equals-and-hashcode/> — §2.6: the two failure
  mechanisms (a generated id changing the hashed bucket; two persistence contexts producing two
  objects) and the business-key / assigned-UUID / constant-`hashCode` strategies.
- <https://vladmihalcea.com/hibernate-slow-query-log/> and
  <https://thorben-janssen.com/hibernate-slow-query-log/> — §2.20.4: `hibernate.log_slow_query`
  available since **5.4.5**, the
  `hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS` alias, and the
  `org.hibernate.SQL_SLOW` INFO category. `[RESEARCH]`
- <https://vladmihalcea.com/hibernate-jpql-window-functions/>,
  <https://vladmihalcea.com/hibernate-union-intersect-except/> and
  <https://thorben-janssen.com/using-window-functions-with-hibernate-5-6/> — §1.19.14–§1.19.16:
  window functions, set operations and their availability from Hibernate 6 onward. Used for concept
  names only; the HQL guide is the authority. `[RESEARCH]`
- <https://vladmihalcea.com/spring-data-windowiterator/> and
  <https://thorben-janssen.com/offset-and-keyset-pagination-with-spring-data-jpa/> — §2.9's keyset
  material and the `WindowIterator` usage shape.
- <https://vladmihalcea.com/hibernate-database-schema-multitenancy/> and
  <https://spring.io/blog/2022/07/31/how-to-integrate-hibernates-multitenant-feature-with-spring-data-jpa-in-a-spring-boot-application/>
  — §2.17: the three tenancy models, `CurrentTenantIdentifierResolver`,
  `AbstractDataSourceBasedMultiTenantConnectionProviderImpl.selectDataSource`, the
  `getAnyConnection()` startup requirement, and the `hibernate.multiTenancy` /
  `hibernate.tenant_identifier_resolver` / `hibernate.multi_tenant_connection_provider` settings.
  The Spring blog post is the canonical recipe and **should be fetched in the write pass**.
  `[RESEARCH]`
- <https://thorben-janssen.com/fix-multiplebagfetchexception-hibernate/>,
  <https://www.baeldung.com/java-hibernate-multiplebagfetchexception> and
  <https://github.com/jlmc/hibernate-tunings/blob/master/docs/FixingMultipleBagFetchException.md>
  — §1.14.3–§1.14.4 and §2.2.12: the bag/set/list distinction, the `Set` "fix" producing a cartesian
  product instead, and the multiple-query alternative.
- <https://thorben-janssen.com/complete-guide-inheritance-strategies-jpa-hibernate/> and
  <https://martinelli.ch/inheritance-in-jpa/> — §1.15's per-strategy cost and constraint analysis,
  including `TABLE_PER_CLASS`'s `UNION` and the `SINGLE_TABLE` nullability trade.
- <https://stackify.com/find-hibernate-performance-issues/> and
  <https://codewiz.info/blog/jpa-performance-anti-patterns/> — mined purely for anti-pattern
  *names* to check §2.22 against. No number or claim was taken from them.
- <https://jdbc-observations.github.io/datasource-proxy/docs/snapshot/user-guide/index.html> and
  <https://github.com/gavlyukovskiy/spring-boot-data-source-decorator> — §2.20.6: query logging,
  slow-query callbacks, query-execution statistics and the assertion API used in §4.9.1–§4.9.2.
  `[RESEARCH]`
- <https://jpa-buddy.com/blog/hibernate6-whats-new-and-why-its-important/> and
  <https://vladmihalcea.com/hibernate-sqm-semantic-query-model/> — §2.21.2 and §3.9.1–§3.9.2: SQM as
  a shared internal representation for HQL and Criteria, replacing the 5.x
  Criteria→HQL-string→SQL path. `[RESEARCH]`

**Interview / curriculum / adversarial angles**

- <https://www.interviewbit.com/jpa-interview-questions/>,
  <https://jpa-buddy.com/blog/spring-data-jpa-interview-questions-and-answers/>,
  <https://dzone.com/articles/spring-data-jpa-interview-questions-and-answers>,
  <https://amigoscode.com/quiz/spring-data-jpa-interview-questions>,
  <https://www.codingshuttle.com/mock-tests/spring-data-jpa-for-interviews/> and
  <https://www.hirist.tech/blog/top-20-java-jpa-interview-questions-and-answers/> — mined **only for
  question names not already in §5.1**. They contributed the "L1 is the persistence context"
  framing, the entity-lifecycle-and-dirty-checking pairing, the "persistence context and its
  performance impact" senior framing, and the `EntityManagerFactory`-vs-`EntityManager` and
  attached-vs-detached questions. No prose, constant or mechanism claim was taken from any of them.
- <https://www.petrikainulainen.net/interviews/high-performance-java-persistence-by-vlad-mihalcea/>
  and <https://dev.to/stephenflavin/jpa-the-good-the-bad-and-the-ugly-5e9m> — the adversarial angle.
  Contributed §1.1.3's cost list, the "the most common issue is fetching too much data" framing in
  §2.2.16, the "verify the generated SQL" discipline that §2.20 is built on, the "you usually do not
  need a `Set`" point behind §1.14.3, and the "`merge` does a hidden SELECT" framing in §1.8.6.
- *High-Performance Java Persistence* (Mihalcea) is the book-length treatment of PART 2 and PART 3
  and is named in §References as the reader's next step. It was **not** consulted directly in this
  pass — no claim in this syllabus rests on it.

**Searches that returned nothing usable**

- No published **university course syllabus** on JPA/Hibernate was found; the curriculum angle was
  covered instead by the Spring Certified Professional objective weights already recorded in
  `src/syllabus/07-spring-core.md` (Data/JDBC/Transactions **14%**) and by the book/blog tables of
  contents above.
- No primary source was located for the **current** `hibernate.batch_fetch_style` status — the
  setting may be deprecated or removed in 6.6, so §1.17.16 instructs the write pass to check the
  6.6 configuration appendix rather than asserting the three values.
- No primary source was located for Boot 3.5's exact **`ddl-auto` default** or the current
  physical-naming-strategy **class name**; §1.30.1 and §1.9.11 must both be verified against the
  3.5 reference documentation. `[RESEARCH]`
- No authoritative published benchmark was found for the batching configurations in §4.9.3 or the
  `pooled-lo` round-trip savings in §4.7.3; those leaves must be written as "measure it with this
  harness" rather than quoting a number.
- No primary source was located for the claim that Hibernate 6 rewrites collection-fetch pagination
  into a windowed subquery (§2.5.9); the leaf is therefore written as "do not rely on it, read the
  SQL".

## Gaps vs the current guide

`src/topics/08-spring-data-jpa.md` is **404 lines** across 14 numbered sections plus a 22-item
atomic concept checklist. For its length it is a good guide: its persistence-context, `persist`/
`merge`/`save`, `LazyInitializationException`, N+1, `HHH000104`, `equals`/`hashCode`, batching and
open-session-in-view sections are already mechanism-first, and **every one of its `**Trap:**` markers
is real and must survive**. It is nonetheless not a bible: it has no mapping content at all beyond
fetch defaults (no `@Column`, no access type, no embeddables, no inheritance, no cascade, no
associations, no identifier generation beyond one sentence about IDENTITY), no JPQL/HQL/Criteria
content, no repository-layer content beyond thirteen bullets, no projections beyond one bullet, no
pagination beyond the collection-fetch trap, no internals whatsoever, no version history, no
build-it content, and no interview set.

| Syllabus area | Present in `src/topics/08-spring-data-jpa.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why ORM exists, impedance mismatch, history, alternatives | §1 (buys/costs/mature position — 3 short paragraphs) | ✅ the five mismatches, the pre-JPA history, the three-layer distinction, the alternatives table | ✅ the buys/costs lists and the "mature position" paragraph are strong and must be preserved verbatim |
| §1.2 spec versions, `javax`→`jakarta`, Hibernate/Spring Data timelines, dependency coordinates | — | ✅ entire section | |
| §1.3 bootstrap, `LocalContainerEntityManagerFactoryBean`, Boot auto-config, the shared `EntityManager` proxy, `spring.jpa.*` vs `spring.jpa.properties.*` | — | ✅ entire section — and §1.3.12/§1.3.15 are among the highest-value missing leaves in the file | |
| §1.4 the `EntityManager` API surface, `Session` extras, `StatelessSession`, flush modes | §2 (names `EntityManager`/`Session` in passing) | ✅ the whole method inventory, `getSingleResultOrNull`, `StatelessSession`, `LockModeType`'s six values, cache modes | ✅ severely |
| §1.5 the entity state machine | §2 (the four-state table + transitions in one line) | ✅ every transition individually, removed-state semantics, `detach`/`clear`/`evict`/`close`, `refresh`, read-only entities, `TransientObjectException` boundary | ✅ the four-state table and the two code examples must be preserved verbatim |
| §1.6 the persistence context | §2 (identity map + dirty checking, 2 bullets) | ✅ the action queue, write-behind, the two context types, the memory arithmetic, `isDirty`, the `readOnly` mechanism | ✅ the two bullets are correct and must be expanded, not rewritten |
| §1.7 flush | §2 (one short sub-section, 4 lines) | ✅ the query-space rule, all four flush modes, per-query mode, `flush` vs `clear` ordering, `saveAndFlush`, commit-time constraint violations | ✅ the "not before a native query" sentence is the single best line in the current guide and must be kept and proved |
| §1.8 persist/merge/remove/save | §3 (the whole section — excellent) | ✅ `EntityExistsException`, when the INSERT runs, the hidden SELECT, `merge(transient)`, 6.6's versioned-merge change, delete ordering, the full delete family | ✅ the returned-copy code block, both `**Trap:**` markers and the `Persistable` fix must be preserved verbatim |
| §1.9 declaring an entity, `@Column`, access type, `@Enumerated`, `@DynamicUpdate`, `@SQLRestriction`, `@SoftDelete` | — | ✅ entire section (28 leaves) | |
| §1.10 basic types, converters, the Hibernate 6 type system | — | ✅ entire section | |
| §1.11 identifier generation | §11 (IDENTITY-disables-batching + `allocationSize = 50` in one paragraph) | ✅ the five strategies, `AUTO`'s dialect resolution, the six optimizers, `pooled` vs `pooled-lo`, UUID costs, composite ids, `@MapsId`, `@IdGeneratorType` | ✅ the IDENTITY/SEQUENCE trap is correct and must be preserved verbatim and proved |
| §1.12 embeddables, composite keys, `@ElementCollection` | — | ✅ entire section | |
| §1.13 associations, owning vs inverse, `@OneToOne` lazy caveat | §4 (the `@OneToOne` lazy caveat only) | ✅ owning/inverse, the inverse-only-add bug, join-table-by-accident, the extra-UPDATE problem, `@ManyToMany` replacement | ✅ the `@OneToOne` caveat paragraph is correct and must be preserved verbatim |
| §1.14 collections and `PersistentBag` | §6 (`MultipleBagFetchException` symptom only) | ✅ the wrapper inventory, bag-vs-list-vs-set mechanics, the collection-replacement bug, ordering annotations, `size()`/`contains()` costs | ✅ severely — the guide gives the symptom without the mechanism |
| §1.15 inheritance | — | ✅ entire section (16 leaves) | |
| §1.16 cascade and orphan removal | — | ✅ entire section | |
| §1.17 fetch types, proxies, lazy loading | §4 + §5 (the defaults table, the proxy mechanism, the ranked fixes, two traps) | ✅ the EAGER-cannot-be-undone asymmetry, `HibernateProxy`/`LazyInitializer`, `@Fetch` vs `FetchType`, `@FetchProfile`, `@LazyGroup`, batch-fetch style | ✅ the defaults table, the mechanism paragraph, the ranked fix list and both traps are the guide's best content and must be preserved verbatim |
| §1.18 lifecycle callbacks and listeners | — | ✅ entire section | |
| §1.19 JPQL and HQL | §13 (`@Query` validated at startup, one line) | ✅ entire section — the guide never mentions implicit joins, `join fetch` vs `join`, constructor expressions, window functions, CTEs or set operations | |
| §1.20 Criteria API and the metamodel | — | ✅ entire section | |
| §1.21 native queries, stored procedures, result mapping | §13 (native not validated, one clause) | ✅ entire section | ✅ severely |
| §1.22 repository interfaces and `@EnableJpaRepositories` | §13 (first bullet: "interfaces only; Spring generates a proxy") | ✅ the hierarchy, the 3.0 split, `getReferenceById`, every `@EnableJpaRepositories` attribute and default, `BootstrapMode`, custom implementations, Query by Example | ✅ severely |
| §1.23 derived queries | §13 (one bullet + the startup-failure point) | ✅ the full keyword tables, property-path ambiguity, derived deletes, `Stream`, `Limit`, `ScrollPosition`, `QueryLookupStrategy` | ✅ the "a typo fails at startup, which is good" point is right and must be kept and proved |
| §1.24 `@Query`, `@Modifying`, `@QueryHints`, `@Meta` | §13 (`@Query` + `@Modifying` bullets) | ✅ the attribute lists, SpEL, `@QueryHints(forCounting)`, `@Meta`, `QueryRewriter` | ✅ the `@Modifying` bullet is excellent and must be preserved verbatim and expanded |
| §1.25 projections | §13 (one bullet: "interface with getters … cheapest read path") | ✅ closed vs open, the proxy mechanism, DTO/record projections, constructor-expression rewriting, dynamic projections, the nested-join trap, the byte arithmetic | ✅ severely — closed-vs-open is the single most important missing fact |
| §1.26 pagination and sorting | §7 (the collection-fetch trap only) | ✅ `Page` vs `Slice` vs `Window`, the count query, `spring.data.web.*` defaults, the `Page<Entity>` controller trap, sort stability | ✅ |
| §1.27 transactions and the persistence context | §14 (boundary placement, `readOnly`, repository transactionality) | ✅ the manager comparison, `EntityManagerHolder`, no-transaction behaviour, propagation's context semantics, isolation × L1, timeouts, synchronisations | ✅ the boundary paragraph and the `SimpleJpaRepository` observation are correct and must be preserved verbatim |
| §1.28 locking | §9 (optimistic + pessimistic, with the `@Retryable` example) | ✅ the version types, the exception zoo, `OPTIMISTIC`/`OPTIMISTIC_FORCE_INCREMENT`, `SKIP LOCKED`, `PessimisticLockScope`, the decision table, what locking cannot do | ✅ the `@Version` mechanism, the retry-the-whole-transaction point and the lock-ordering warning must be preserved verbatim |
| §1.29 the three caches | §10 (L1/L2/query cache + the multi-instance danger + "default to no L2") | ✅ what L2 stores, the four concurrency strategies, soft locks, the timestamps cache, collection caching, providers, `CacheMode`, statistics | ✅ the multi-instance-danger paragraph and the "default to no L2" recommendation are the guide's best judgement calls and must be preserved verbatim |
| §1.30 schema management | §12 (ddl-auto values, `validate` + Flyway, migration discipline) | ✅ the underlying Hibernate settings, what `validate` does not check, Flyway/Liquibase mechanics and comparison, ordering, `defer-datasource-initialization`, the CI drift test | ✅ the four arguments against `update` and the migration-discipline list must be preserved verbatim |
| §1.31 the configuration property surface | §11 + §14 (four properties) | ✅ the whole surface with defaults, the logger inventory, the Hikari keys, the **driver-level** batching properties, `enable_lazy_load_no_trans` | ✅ severely |
| §2.1 the master tables | — | ✅ all ten, including the master cost table and the memory arithmetic | |
| §2.2 N+1 taxonomy | §6 (the canonical case, detection, the fix table, the two-bag trap) | ✅ the five shapes, the eager-under-JPQL case, the query-count assertion, `@BatchSize` arithmetic, `in_clause_parameter_padding` | ✅ the fix table and the detection ranking are strong and must be preserved verbatim and extended |
| §2.3 entity graphs | §6 (one row in the fix table) | ✅ fetch vs load graph, the attribute/subgraph API, the pagination interaction, the decision rule | ✅ severely |
| §2.4 views, copies, snapshots, lifetime | — | ✅ entire section | |
| §2.5 pagination with collection fetch | §7 (the whole section — excellent) | ✅ the row arithmetic, the count query, `@BatchSize` as an alternative, alerting on the log line | ✅ the log line, the mechanism and the two-query fix must be preserved verbatim |
| §2.6 `equals`/`hashCode` | §8 (the whole section — excellent) | ✅ the two-contexts and proxy-class failures, the constant-`hashCode` proof, the safe Lombok subset | ✅ the rules list, the code block, the `Hibernate.getClass` note and the `@Data` trap must be preserved verbatim |
| §2.7 entities vs DTOs | §5 (fix #2: "map to a DTO — this is the design fix") | ✅ the rule, the four objections, mapping options, the request-side mirror, validation placement, ArchUnit enforcement | ✅ the one-line design fix is right and must be expanded into the section it deserves |
| §2.8 Specifications, QueryDSL, Query by Example | — | ✅ entire section — including the `fetch`-breaks-the-count-query trap | |
| §2.9 keyset pagination and the Scroll API | — | ✅ entire section | |
| §2.10 bulk operations | §13 (`@Modifying` bullet + `deleteAll` vs `deleteAllInBatch`) | ✅ the four approaches, `@Version`/L2/cascade consequences, temp-table strategies, `StatelessSession`, chunked processing, upserts | ✅ both bullets are excellent and must be preserved verbatim |
| §2.11 statement batching | §11 (the whole section — excellent) | ✅ `order_inserts`' mechanism, the **driver-level** rewrite properties, what silently disables batching, how to verify, size selection, lock footprint | ✅ the loop, the three properties and the IDENTITY trap must be preserved verbatim |
| §2.12 transactions in practice and OSIV | §14 (the whole section — excellent) | ✅ the connection-holding arithmetic, delayed connection acquisition, the `REQUIRES_NEW` audit-row case, catch-and-continue, read-your-own-writes, testing | ✅ the four OSIV bullets, the migration recipe and the closing sentence must be preserved verbatim |
| §2.13 concurrency in practice | §9 (the `@Retryable` example) | ✅ the two-thread walkthrough, the re-read requirement, the atomic-decrement pattern, `SKIP LOCKED`, insert races, isolation × L1, thread safety, virtual threads | ✅ |
| §2.14 caching decisions | §10 (the recommendation) | ✅ the decision procedure, the layer table, natural-id caching, measurement, the `@Cacheable`-on-repository trap | ✅ |
| §2.15 the connection pool | §14 (connection-held-for-the-request point) | ✅ the ownership chain, the handling modes, sizing, the pool-timeout diagnosis, leak detection, replica routing, metrics | ✅ severely |
| §2.16 auditing | — | ✅ entire section including Envers and the three fail cases | |
| §2.17 multi-tenancy | — | ✅ entire section | |
| §2.18 bytecode enhancement | §4 (mentioned once, as a `@OneToOne` fix) | ✅ entire section | ✅ severely |
| §2.19 testing the persistence layer | — | ✅ entire section — the H2 trap and the `flush()`/`clear()` rule are the highest-value missing test facts | |
| §2.20 observability | §6 (three logging options in one paragraph) | ✅ the `Statistics` surface, the slow-query log, the logger matrix, proxy datasources, `StatementInspector`, Micrometer, the runbook | ✅ the detection ranking must be preserved and expanded |
| §2.21 version history | — | ✅ entire section including the fifteen-item stale-answer sweep | |
| §2.22 the anti-pattern catalogue | scattered `**Trap:**` markers (9 of them) | ✅ all forty-five consolidated; every existing trap maps to an entry and must survive | ✅ |
| §2.23 when not to use JPA | §1 (the mature position, 2 sentences) | ✅ the five workloads, the incremental exit path, Spring Data JDBC / jOOQ / `JdbcClient` | ✅ the mature-position paragraph is the seed and must be preserved verbatim |
| PART 3 — bootstrap internals (§3.1) | — | ✅ | |
| PART 3 — `StatefulPersistenceContext` internals (§3.2) | §2 (the concept only) | ✅ the field list, `EntityKey`, `EntityEntry`, `Status`, the memory arithmetic | ✅ severely |
| PART 3 — hydration and two-phase load (§3.3) | — | ✅ entire section, including the cyclic-graph proof and `NonUniqueObjectException` | |
| PART 3 — the dirty-checking algorithm (§3.4) | §2 (one sentence: "compares each managed entity to its snapshot") | ✅ the algorithm, `Type.isDirty`, the cost arithmetic, `SelfDirtinessTracker`, the `@DynamicUpdate` interaction, versionless locking | ✅ severely — this is the most-asked internals question in the topic |
| PART 3 — flush internals and the `ActionQueue` (§3.5) | — | ✅ entire section; §3.5.3's ordering and §3.5.4's delete-then-insert bug are the two highest-value leaves in PART 3 | |
| PART 3 — the event system (§3.6) | — | ✅ entire section | |
| PART 3 — proxy internals (§3.7) | §5 (the mechanism in two sentences) | ✅ `HibernateProxy`/`LazyInitializer`, ByteBuddy generation, the `final`-method failure, the throw site, `PersistentBag`, queued operations, enhancement-as-proxy | ✅ the two-sentence mechanism is correct and must be expanded, not rewritten |
| PART 3 — identifier-generation internals (§3.8) | — | ✅ entire section including the optimizer arithmetic proofs | |
| PART 3 — the HQL→SQM→SQL pipeline (§3.9) | — | ✅ entire section | |
| PART 3 — the query-plan cache (§3.10) | — | ✅ entire section | |
| PART 3 — JDBC layer and batching internals (§3.11) | §11 (the properties only) | ✅ `MutationExecutor`, `BatchKey`, `Expectation`, the `StaleStateException` trace, driver rewriting, fetch-size/cursor mechanics | ✅ |
| PART 3 — L2 cache internals (§3.12) | §10 (the taxonomy only) | ✅ the SPI, `CacheEntry`, the soft-lock protocol, the timestamps region, `QueryKey`, clustering modes | ✅ severely |
| PART 3 — locking internals (§3.13) | §9 (the version predicate in one sentence) | ✅ where the predicate is added, the exception mapping, `OPTIMISTIC_FORCE_INCREMENT`'s process, **follow-on locking**, dialect timeout translation | ✅ |
| PART 3 — Spring's JPA integration internals (§3.14) | §14 (the OSIV filter mentioned) | ✅ entire section — `SharedEntityManagerCreator` and `JpaTransactionManager.doBegin` are the two leaves that explain half the guide's traps | |
| PART 3 — the Spring Data repository proxy (§3.15) | §13 ("Spring generates a proxy implementation at startup") | ✅ all 23 leaves — the registration path, the advice chain, `PartTree`, `PropertyPath`, `JpaQueryExecution`, `QueryUtils`, `SimpleJpaRepository`, projection factories, auditing wiring, AOT repositories | ✅ severely — one clause stands in for the entire layer |
| PART 3 — failure modes at source level (§3.16) | scattered symptoms | ✅ the three decision trees, the twelve trace anatomies, and the **silent-failure catalogue** | ✅ |
| PART 4 — every `[BUILD]` (§4.1–§4.12) | — | ✅ all 83 leaves; the current guide contains no implementable content whatsoever | |
| PART 5 — the 142-question set | — | ✅ | |
| PART 5 — the 127-item trap index | 9 `**Trap:**` markers inline | ✅ all nine must be preserved and 118 added | |
| PART 5 — the drills | the 22-item atomic concept checklist | ✅ the numbers/class-name/ordering/SQL-prediction/statement-count/diagnosis/version/whiteboard/review drills | ✅ the checklist is good and must be preserved verbatim and extended |

Four corrections the write pass **must** make to existing text, not merely additions:

1. §4 of the current guide says the optional non-owning `@OneToOne` "stays eager in practice" and
   lists three fixes. That is right, but the checklist line says the fix is "`@MapsId` **or bytecode
   enhancement**" — and the bytecode-enhancement route (`@LazyToOne(NO_PROXY)`) is **removed in
   Hibernate 7**. State the 6.6 truth and the 7.0 change (§1.13.12).
2. §11 says "`AUTO` on MySQL resolves to IDENTITY; on Postgres, to SEQUENCE." True, but incomplete in
   a way that matters: in Hibernate **5** `AUTO`+SEQUENCE meant one shared `hibernate_sequence`,
   while Hibernate **6** gives each entity its own `<table>_seq`. Anyone migrating hits this, and
   the current wording gives no warning (§1.11.2).
3. §7 says "Hibernate 6 can sometimes rewrite this; do not rely on it." Keep the advice, but the
   guide must also give the reader the **log code to grep for in both numbering schemes**
   (`HHH000104` *and* `HHH90003004`), because a 6.x reader searching for the 5.x code finds nothing
   (§2.5.2).
4. §13 says "`@Query` JPQL is validated at startup". True by default, but **not** under
   `spring.data.jpa.repositories.bootstrap-mode=lazy|deferred`, which several teams enable for
   startup time and thereby lose the property the guide is recommending. The caveat must be stated
   (§1.22.9, §3.15.22).

Nine passages in the current guide are strong and must survive **verbatim or expanded**, never
rewritten: the buys/costs/mature-position framing (§1), the four-state table with both code examples
and the flush sub-section (§2), the whole `persist`/`merge`/`save` section including both traps and
the `Persistable` fix (§3), the fetch-defaults table and the `@OneToOne` caveat (§4), the proxy
mechanism paragraph with the ranked fixes and both traps (§5), the N+1 detection ranking and fix
table with the two-bag trap (§6), the `HHH000104` section entire (§7), the `equals`/`hashCode`
section entire (§8), the batching section entire (§11), and the transaction-boundary and OSIV
section entire (§14). The 22-item atomic concept checklist must be carried forward line for line and
extended, not replaced.

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.31 | 485 |
| PART 2 — Intermediate | §2.1–§2.23 | 296 |
| PART 3 — Under the hood | §3.1–§3.16 | 208 |
| PART 4 — Build it | §4.1–§4.12 | 83 |
| PART 5 — Interview and retention | §5.1–§5.3 | 288 |
| **Total** | **85 sections** | **1360 leaves** |

Counts above are audited against disk (`grep -cE '^[0-9]+\.[0-9]+\.[0-9]+'` per part).

`[RESEARCH]` occurrences: **258** (PART 1: 98, PART 2: 52, PART 3: 70, PART 4: 0, PART 5: 35,
front matter: 3).
Each must be re-verified against its cited source during the write pass before any constant from it
is written down. The highest-risk clusters, in order:

1. **All of §3.2–§3.15.** No Hibernate or Spring Data *source file* was fetched in this pass; every
   field name, map name, listener name, action-queue entry, optimizer method and constant in PART 3
   comes from documentation, javadoc summaries, expert write-ups or recall. The five items most
   likely to be wrong if not checked are the `ActionQueue` order (§3.5.3), the
   `StatefulPersistenceContext` field list (§3.2.2), the `EntityEntry` field list (§3.2.4), the
   Spring Data repository advice-chain order (§3.15.3), and the `PartTree` regexes (§3.15.7).
2. **Every Hibernate 7.0 and Spring Data 4.0 claim.** The Hibernate 7 migration guide *was* fetched
   and is reliable; the Hibernate 7 "What's New" page and both Spring Data 4.0 pages were **not**,
   so §3.1.4, §2.3.12 and §3.15.23 are `[VERSION-TRAP]` + `[RESEARCH]`.
3. **Version-dependent defaults.** `spring.jpa.hibernate.ddl-auto`'s Boot 3.5 default (§1.30.1), the
   physical-naming-strategy class name (§1.9.11), `hibernate.batch_fetch_style`'s continued
   existence (§1.17.16), `hibernate.query.plan_cache_max_size` = 2048 and
   `plan_parameter_metadata_max_size` = 128 (§1.19.22, §3.10.2), `@SequenceGenerator`'s
   `allocationSize` = 50 (§1.11.4), and the `@EnableJpaRepositories` attribute defaults (§1.22.8).
   Verify each with `/actuator/configprops` on a real 3.5 app or against the 6.6 configuration
   appendix — not from recall.
4. **The `pooled` vs `pooled-lo` arithmetic** (§1.11.7–§1.11.8, §3.8.4–§3.8.5). The direction of the
   off-by-`allocationSize` is easy to state backwards, and getting it wrong inverts the whole
   argument. Read `PooledOptimizer.generate` and `PooledLoOptimizer.generate`.
5. **The L2 concurrency-strategy protocols** (§1.29.5, §3.12.4–§3.12.7). Quote
   `CacheConcurrencyStrategy`'s javadoc rather than paraphrasing the blog posts.
6. **Follow-on locking** (§3.13.7) and the **dialect lock-timeout translation** (§3.13.9) — both are
   genuinely obscure and both are stated here from secondary material.
7. **Spring Data 3.5's specification API split** (§2.8.8) and the **keyset-projection limitation**
   (§2.9.9) — both are recent enough that the version boundary must be pinned before recommending
   either.

Target version restated for the write pass: **Jakarta Persistence 3.1 / Hibernate ORM 6.6.x /
Spring Data JPA 3.5.x on Spring Boot 3.5.x and Java 21**, with every Hibernate 7.0 / Jakarta
Persistence 3.2 / Spring Data 4.0 divergence marked `[VERSION-TRAP]` inline. The deltas that most
often produce a stale answer are `javax.persistence` (gone in Hibernate 6.0 / Boot 3.0),
`@GenericGenerator` (deprecated in 6.5), `session.save/update/delete/load/get` (gone in 7.0),
`@Where`/`@OrderBy`/`@LazyToOne`/`@LazyCollection` (gone in 7.0), `GenerationType.AUTO`'s
per-entity sequence (changed in 6.0), the legacy `org.hibernate.Criteria` API (gone in 6.0),
`getOne`/`getById` (superseded by `getReferenceById`), and `PagingAndSortingRepository` no longer
extending `CrudRepository` (Spring Data 3.0).

