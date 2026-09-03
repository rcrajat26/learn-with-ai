# Syllabus — 15 Caching

**Currency anchor: Q3 2026 state of practice.** Every constant, config directive, default value,
command name, annotation attribute and class name below is stated against this set of releases, and
every leaf that depends on a version says so with `[CURRENCY]` or `[VERSION-TRAP]`:

| Layer | Release this file targets |
|---|---|
| Redis Open Source | **8.6** (Feb 2026) — adds `allkeys-lrm`/`volatile-lrm`, `HOTKEYS`, `XADD … IDMP/IDMPAUTO`, `key-memory-histograms`, `cluster-slot-stats-enabled`. Built on 8.4; 8.0 was the first unified distribution |
| Redis licence | **AGPLv3 since May 2025** (tri-licence AGPLv3 / SSPLv1 / RSALv2). BSD → SSPL/RSAL was March 2024 |
| Valkey | **9.x** — Linux Foundation BSD-3 fork of Redis 7.2.4 (March 2024). Default engine for new AWS ElastiCache and Google Memorystore instances |
| Caffeine | **3.2.4** (4 May 2026); 3.2.0 (17 Jan 2025), 3.2.3 (28 Oct 2025) |
| Guava cache | still shipped, still LRU-ish, still the thing Caffeine replaced |
| Memcached | **1.6.x** with `lru_maintainer`, `lru_crawler`, `slab_reassign`, `slab_automove`, `extstore` |
| Spring | **Spring Boot 4.1.x / Spring Framework 7.0.x** (Boot 4.0.0 GA 20 Nov 2025, 4.1.0 GA 10 Jun 2026, 4.1.1 Aug 2026). Boot **3.5.x** is the previous generation and is what most codebases are on — both are covered |
| Spring Data Redis | **4.1.x** (`RedisCacheManager`, `RedisCacheConfiguration`, `CacheKeyPrefix`, `RedisCacheWriter`) |
| Hibernate ORM | **7.x** — `@Cache`, `CacheConcurrencyStrategy`, `jakarta.persistence.sharedCache.mode` |
| JCache | **JSR-107 1.1** (`javax.cache`), provider Ehcache **3.10.x** |
| HTTP caching | **RFC 9111** (caching), **RFC 9110** (semantics — `Vary`, conditional requests), **RFC 5861** (`stale-while-revalidate`, `stale-if-error`), **RFC 8246** (`immutable`), **RFC 9211** (`Cache-Status`), **RFC 9213** (`CDN-Cache-Control`) |
| Java runtime | **Java 21** for all code |

**The eleven deltas that most often produce a stale answer in an interview**, all marked
`[VERSION-TRAP]` inline:

1. **Redis has two more eviction policies than every blog says.** `allkeys-lrm` and `volatile-lrm`
   (Least Recently Modified — timestamp updated on write only, not read) arrived in **Redis 8.6**.
   The canonical eight-policy list is now ten. `[RESEARCH]`
2. **Redis has a first-class hot-key command.** `HOTKEYS` (8.6) replaces the old
   `redis-cli --hotkeys` scan-and-guess workflow. Any answer that says "you can't find a hot key in
   Redis without sampling `MONITOR`" is pre-8.6. `[RESEARCH]`
3. **`hash-max-listpack-entries` is documented as 512 but shipped as 128.** The docs page and the
   distributed `redis.conf` disagree; the write pass must state both and say which one a running
   server reports via `CONFIG GET`. This is exactly the class of number that gets a candidate marked
   down for false confidence. `[RESEARCH]`
4. **Redis is not BSD any more, and the default managed engine is usually Valkey.** ElastiCache and
   Memorystore default new instances to Valkey; Redis OSS returned to an OSI licence (AGPLv3) only
   in May 2025. "Redis is BSD-licensed" is a 2023 answer.
5. **Hash fields can expire.** `HEXPIRE`/`HPEXPIRE`/`HEXPIREAT`/`HPERSIST`/`HTTL` landed in **7.4**.
   The current guide's § 9 says "you cannot set a TTL on individual hash fields (before Redis 7.4's
   `HEXPIRE`)" — correct but parenthesised; the bible must lead with the capability.
6. **Client-side caching is a supported client feature, not a DIY pattern.** Jedis ≥ **5.2.0** and
   redis-py ≥ 5.1.0 implement RESP3 tracking end to end. Lettuce's `CacheFrontend` predates it.
7. **Spring Boot 4.x moved the caching auto-configuration package.**
   `org.springframework.boot.autoconfigure.cache.CacheAutoConfiguration` →
   `org.springframework.boot.cache.autoconfigure.CacheAutoConfiguration`, and
   `CacheManagerCustomizer` moved with it. Any 3.x import path is now wrong. `[RESEARCH]`
8. **`@Cacheable(sync = true)` is not universally supported and is not a distributed lock.** It
   coalesces within one JVM, on providers that implement `Cache#get(key, Callable)` natively
   (Caffeine yes, `ConcurrentMapCacheManager` yes, `RedisCache` only since Spring Data Redis 3.2 and
   only per-JVM). It has never coordinated across pods.
9. **`stale-while-revalidate` and `stale-if-error` are RFC 5861, not RFC 9111.** RFC 9111 obsoleted
   RFC 7234 and defines only the ten response directives; the stale extensions, `immutable`,
   `Cache-Status` and `CDN-Cache-Control` are four separate RFCs. Getting the spec boundary right is
   a cheap credibility signal.
10. **Eviction research moved past LRU/LFU.** S3-FIFO (SOSP 2023) and **SIEVE** (NSDI 2024) beat
    LRU on the majority of production traces with a fraction of the metadata, and SIEVE has been
    merged into production cache libraries. "LRU or LFU" is a 2015 answer. `[RESEARCH]`
11. **Caffeine's window is adaptive.** The window/main split is not a fixed 1%/99% — it is
    hill-climbed at runtime from measured hit rate. Answers that quote fixed percentages describe the
    2016 paper, not the shipped code. `[RESEARCH]`

**Scope boundary against the sibling guides.** This file owns **the cache as a mechanism**: what a
cache promises, what it therefore cannot promise, how each implementation actually stores and evicts
bytes, and every way it fails. Owned elsewhere:

- B-tree/heap-page mechanics, the **DB buffer pool**, `shared_buffers`, MVCC, isolation levels, query
  plans and "add an index before you add a cache" live in `09-sql-databases.md`. This guide owns the
  buffer pool only as the innermost cache tier and the arithmetic that says whether your working set
  fits it. `[X-REF 09]`
- TCP, TLS handshakes, keep-alive, HTTP/1.1 vs 2 vs 3, DNS and its **negative caching**, load
  balancing and connection pooling live in `10-networking.md`. This guide owns HTTP *caching
  semantics* and CDN behaviour. `[X-REF 10]`
- The **OS page cache**, `mmap`, dirty-page writeback, `vm.swappiness`, transparent huge pages,
  `free`/`vmstat` reading and the OOM killer live in `11-operating-systems-linux.md`. This guide owns
  why THP wrecks a Redis fork and why swap is fatal to a cache. `[X-REF 11]`
- REST resource modelling, `ETag` as an **API contract**, `Idempotency-Key`, pagination contracts,
  versioning and error shapes live in `12-api-design.md`. This guide owns what the cache does with
  those headers. `[X-REF 12]`
- Session vs JWT, token revocation, OWASP, secrets handling and TLS configuration live in
  `13-web-security.md`. This guide owns cache-specific security: `private` vs `public` leakage, key
  collisions across tenants, web cache deception, and cached authorisation as an invariant breach.
  `[X-REF 13]`
- Kafka, Debezium/CDC as a **transport**, outbox, consumer groups, DLQs and Redis-Streams-as-a-queue
  live in `14-messaging-queues.md`. This guide owns invalidation-over-a-broker and why Redis pub/sub
  cannot be the guarantee. `[X-REF 14]`
- Heap sizing, G1 humongous allocation, off-heap/`ByteBuffer`, `SoftReference`/`WeakReference`
  semantics, GC pause effects on a lock TTL and heap-dump workflow live in `06-jvm-internals.md`.
  This guide owns cache-shaped heap arithmetic and why an in-process cache is a GC decision.
  `[X-REF 06]`
- `ConcurrentHashMap` compound-action rules, `computeIfAbsent`, `synchronized`, CAS, `CompletableFuture`,
  `ReentrantLock` and virtual threads live in `05-multithreading-concurrency.md`. This guide owns
  single-flight *as a cache pattern*. `[X-REF 05]`
- `LinkedHashMap` as an LRU, `HashMap` treeification, `equals`/`hashCode`, `TreeMap` and
  `ConcurrentHashMap` bucket internals live in `02-java-collections.md`. This guide owns cache-grade
  hashing and sketch structures. `[X-REF 02]`
- Bean lifecycle, the **proxy model**, self-invocation, AOP order, `@EnableCaching`'s
  `mode`/`proxyTargetClass`, and Boot auto-configuration mechanics live in `07-spring-core.md`. This
  guide owns the caching-shaped subset. `[X-REF 07]`
- Entity mapping, persistence context, dirty checking, N+1 and `@Version` live in
  `08-spring-data-jpa.md`. This guide owns L1/L2/query-cache mechanics. `[X-REF 08]`
- ElastiCache/MemoryDB/CloudFront provisioning, IAM, VPC endpoints, cost modelling and multi-AZ
  failover live in `18-cloud-aws.md`. This guide owns their *caching semantics*. `[X-REF 18]`
- Probes, rolling updates, `terminationGracePeriodSeconds`, HPA and `CrashLoopBackOff` debugging live
  in `19-docker-kubernetes.md`. This guide owns readiness-gated warm-up. `[X-REF 19]`
- Micrometer, Prometheus, tracing, SLI/SLO, alert design and postmortems live in
  `20-observability-operations.md`. This guide owns which cache metrics exist and what a bad value
  looks like. `[X-REF 20]`
- Test slices, Testcontainers mechanics and contract testing live in `16-testing.md`. This guide owns
  what a cache test must assert. `[X-REF 16]`
- CAP/PACELC, consistent hashing as an architecture primitive, the read-model/CQRS decision, quorum
  arithmetic and back-of-envelope procedure live in `22-system-design.md`. This guide owns the
  mechanism and the numbers. `[X-REF 22]`
- Big-O, hashing, Bloom filters as data structures live in `01-dsa-fundamentals.md`. `[X-REF 01]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in **one paragraph** before pointing away — it never sends the reader off empty-handed.

**Every example, key name, status code and number comes from the QuizStakes domain in
`src/scenario/scenario.md`.** The caching surfaces the bible must design against are scenario § 15.4
verbatim: the **current agreement version text** (safe to cache — ~180 versions, 40–900 KB each,
changes almost never, read on every journey); **cash available and restriction decisions** (never
cacheable — invariant 12 says restriction decisions are read live, never from a cache or token);
`BalanceView` as the derived display path against `FundsLedger` as the authoritative decision path
(the same number at two trust levels); the agreement-version publish that makes every cached copy
**legally wrong**; the cached-clear restriction against a client who self-excluded 30 seconds ago;
the agreement cache expiring while ten thousand in-flight journeys fetch it at once; `"this client
has no requirements"` cached just before a rule raises one; write-behind limit counters losing a
deposit against the daily limit; `PendingActions` still showing a banner for a satisfied
requirement; and `ProfileService` assembling eight owners where latency is the slowest and
availability is the product. The services are `ApplicationGateway`, `RouterInt`, `JwtService`,
`AccountOpening`, `PersonalDetails`, `ClientAgreements`, `AssessmentService`, `AccountActivation`,
`DocumentVerification`, `DocumentRequirements`, `ScreeningService`, `ApplicationHistory`,
`AccountMaintenance`, `ClientRestrictions`, `InternalPlatforms`, `PaymentService`, `FundsLedger`,
`CardPayments`, `BankDeposits`, `BankWithdrawal`, `BonusService`, `BalanceView`, `ProfileService`,
`PendingActions`, `NotificationService`. Never `product:42`, `user:1234`, `foo`, or
`Dog extends Animal`.

**The load figures the bible must use are the real ones from Appendix A:** 2.4M registered clients;
380k monthly active; **14k concurrent sessions, 55k peak**; 12k registrations/day (40k on campaign
launch); 7.2k applications reaching `AO-400`/day, 24k peak; 95k card deposits/day at **40/sec**;
2.8M stake reservations/day at **1,200/sec**; 2.8M settlements/day with **3,400/sec** bursts; 19.8M
ledger entries/day, **230 writes/sec sustained and 13,600/sec peak**, ~180 bytes/row; 24k document
uploads/day at 2–6 MB; 2.6M `ApplicationHistory` records/day at ~400 bytes; 38k restriction records
applied and lifted/day at ~300 bytes; ~180 agreement document versions at 40–900 KB; 2.4M PII
records at ~2 KB; a **30 ms** restriction-decision budget, a **150 ms** stake-reservation budget, a
**hard 500 ms** self-exclusion budget, a **4 s** card-deposit end-to-end budget; `ClientRestrictions`
at **4 GB heap × 8 instances** with "extreme request rate, trivial objects"; `FundsLedger` at
**12 GB heap × 3 instances** with partition affinity by client id; `ApplicationGateway` at 2 GB heap
scaling 12 → 40; operator session state living **30–90 minutes**; the identity vendor's
**600/min estate-wide** cap against p50 900 ms / p99 38 s.

**The scenario rules that constrain every caching decision in this guide**, to be restated at the
point of decision, not in a preamble:

- **Invariant 12: restriction decisions are read live, never from a cache or token.** Consequence if
  violated: "stale permission authorises a blocked action." This is the guide's hardest constraint
  and the reason § 1.8 exists.
- **Invariant 8: self-exclusion takes effect before the next stake** — "the most serious client-harm
  failure possible", with a hard 500 ms budget. It is the one thing in the domain that "genuinely
  cannot be eventually consistent" (§ 10.4).
- **`BalanceView` must never be the source for a stake or withdrawal decision** (§ 4.6). It owns
  arithmetic; the ledger owns authority.
- **Balances are always derived from positions, never stored** (assumption #20) — a stored total is
  a second source of truth, and a cache of a balance is exactly that.
- **`ProfileService` and `PendingActions` may project restrictions for *display*, but a display
  projection must never be the input to an authorisation** (§ 9.4).
- **Only `FundsLedger` writes money**, and **no cross-schema joins** — which is why `ProfileService`
  exists, and why caching the composite view is the tempting wrong answer.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real spec text, RFC text, documentation, or Redis/Caffeine/memcached source (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is config/CLI/HTTP) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[CURRENCY]` | vendor number, quota, price or limit that drifts; state the date it was checked |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte/latency arithmetic explicitly |
| `[CFG]` | give the exact configuration directive/property name and its default value |
| `[API]` | give the exact Java/Spring type, method signature or annotation attribute |
| `[WIRE]` | show the actual protocol bytes/headers/commands, not a description of them |
| `[CLI]` | show the exact command (`redis-cli …`, `curl -I …`, `memcached-tool`) and read its output |
| `[METRIC]` | name the exact metric and what a bad value looks like |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — a log line, an `INFO` dump, an exception — and read it line by line |
| `[TABLE]` | must be rendered as a table |
| `[SPEC]` | cite the specific RFC/JSR section number, not just the document number |

---

# PART 1 — BASICS

## §1.1 Why a cache exists at all, and the economics of hit ratio

1.1.1 The origin problem stated as a trade, not a technique: a cache spends **memory and staleness**
      to buy **latency and origin load**. Naming what you spend is the whole discipline. `[PROVE]`
1.1.2 The three distinct things a cache actually buys, separated because they have different
      justifications: lower **latency** for the user, lower **load** on the origin, and **protection**
      of a dependency that scales worse than you do (the identity vendor's 600/min estate-wide cap).
      `[TABLE]` `[NUM]`
1.1.3 The fourth thing, usually unnamed: **cost**. Serving a read from 4 GB of RAM is cheaper than
      provisioning a database to serve it.
1.1.4 The fifth: **availability**. A cache that serves stale data during an origin outage converts a
      500 into a slightly-wrong 200. This is the highest-value property and the least used.
1.1.5 **Locality** as the precondition. Temporal locality (the same key again soon) and popularity
      skew (a small fraction of keys serve most traffic) are what make a cache work; a workload with
      neither cannot be cached, and no configuration fixes that. `[PROVE]`
1.1.6 **Zipf / power-law access** as the shape that actually occurs, and why "the top 1% of keys
      serve 40–60% of requests" is the assumption behind every cache-sizing decision. `[NUM]`
      `[RESEARCH]`
1.1.7 The latency-tier table, order of magnitude, as the numbers to have memorised: L1/L2 CPU cache,
      main memory, in-process heap lookup ~50–100 ns, same-AZ Redis 0.2–1 ms, cross-AZ Redis +0.5–1 ms,
      Postgres warm indexed point lookup 1–5 ms, Postgres cold or joining 20–500 ms, cross-region
      call 50–150 ms, the identity vendor at p50 900 ms / p99 38 s. `[TABLE]` `[NUM]`
1.1.8 **Hit ratio, miss ratio, miss penalty** defined separately, and the average-latency formula
      `L = h·L_hit + (1-h)·(L_hit + L_miss)` — note the miss pays *both*. `[PROVE]` `[NUM]`
1.1.9 The non-linearity, worked as a table against a 1 ms hit and a 50 ms miss: 0% → 50 ms / 100%
      origin load; 50% → 25.5 ms / 50%; 90% → 5.9 ms / 10%; 95% → 3.5 ms / 5%; 99% → 1.5 ms / 1%;
      99.9% → 1.05 ms / 0.1%. `[TABLE]` `[NUM]` `[PROVE]`
1.1.10 **Consequence one: the last few percent of hit ratio matter to the origin, not to the user.**
      90% → 99% barely moves average latency (5.9 → 1.5 ms) and cuts origin load **tenfold**. Cache
      sizing is therefore usually justified by origin load, not by user-facing latency. `[PROVE]`
1.1.11 **Consequence two: the reverse is a cliff, not a slope.** A flush drops you from 99% to 0%
      instantly, and a database sized for 1% of read traffic receives 100×. `[PROVE]` `[NUM]`
1.1.12 The assertion that follows, stated in the guide's own words and preserved verbatim: **a cache
      your system cannot survive losing is not a cache, it is an undocumented critical dependency.**
      Always ask: if Redis vanishes right now, do we degrade or do we die?
1.1.13 **Amdahl's law applied to caching**: if the cached call is 40% of request time, a perfect
      cache gives at most a 1.67× speedup. Compute the ceiling before building. `[PROVE]` `[NUM]`
1.1.14 Hit ratio is a **property of the workload and the size**, not a target you can set. The miss
      ratio curve (miss ratio as a function of cache size) is the honest way to reason about it.
      `[PROVE]` `[RESEARCH]`
1.1.15 **Working set** defined, and why "cache size ≥ working set" is the only sizing rule that
      matters: below it you thrash, above it you waste RAM. The knee of the miss-ratio curve is the
      answer. `[NUM]`
1.1.16 Why hit ratio alone is a misleading KPI, with the counterexample: 99% hit ratio while every
      miss is a 40-second identity-vendor call means the p99 is entirely determined by the 1%.
      `[TRAP]` `[METRIC]`
1.1.17 The other reasons to cache, each with a QuizStakes instance: expensive **computation**
      (`ProfileService` assembling eight owners), rendered **fragments**, **rate-limited or paid**
      third-party APIs (identity vendor, watchlist provider at 200/min), and shielding a
      **contended** resource (the per-client position lock).
1.1.18 **When not to cache**, enumerated: low read/write ratio (you invalidate more than you serve);
      data that must be strictly fresh; data with no reuse (unique per request); and anything where
      the correctness cost of staleness exceeds the latency benefit. `[TABLE]`
1.1.19 **"Add a cache" is the wrong answer to a missing index.** Fix the query first; a cache in
      front of an unindexed query hides an O(n) scan that returns on the first miss after a deploy.
      `[TRAP]`
1.1.20 "Add a cache" is also the wrong answer to an N+1 (`08-spring-data-jpa.md`): the operator queue
      screen fetching PII for 50 cases individually wants a batch fetch, not 50 cache entries.
      `[X-REF 08]`
1.1.21 The QuizStakes decision worked end to end: the agreement version text is **read on every
      journey** (12k–40k registrations/day, plus every `AO-200` re-check), changes ~180 times ever,
      and is legally identical for all readers. Read/write ratio in the millions. That is the
      textbook cacheable object. `[NUM]` `[PROVE]`
1.1.22 The mirror decision: `CASH_AVAILABLE` is read on every screen and written on every one of 2.8M
      daily stake reservations. Read/write ratio ~1. It also authorises spending. Two independent
      reasons not to cache it, and the bible must give both. `[PROVE]`
1.1.23 The **cache-as-optimisation vs cache-as-architecture** distinction: an optimisation can be
      switched off in production; an architecture cannot. Know which one you built, and prove it by
      load-testing with the cache disabled at least once.

## §1.2 The vocabulary, stated once

1.2.1 **Cache** vs **buffer** vs **pool** vs **memo** — four things people call a cache, only one of
      which is allowed to lose data. `[TABLE]`
1.2.2 **Hit** / **miss** / **compulsory (cold) miss** / **capacity miss** / **conflict miss** /
      **coherence miss** — the five-way miss taxonomy borrowed from CPU caches, and which ones you
      can actually fix. `[TABLE]` `[PROVE]`
1.2.3 **Eviction** vs **expiry** vs **invalidation** vs **flush** vs **purge** — four different
      mechanisms and one operator verb, routinely conflated. `[TRAP]` `[TABLE]`
1.2.4 **TTL** (time to live, absolute) vs **TTI** (time to idle, sliding) vs **refresh-after**, and
      the fact that all three can be set on the same entry with different values.
1.2.5 **Stale** vs **inconsistent** vs **wrong** — bounded staleness is a design output;
      unbounded inconsistency is a bug.
1.2.6 **Fresh** / **stale** / **revalidation** as the HTTP vocabulary for the same three states, so
      the reader can move between § 1.6 and § 2.7 without relearning. `[SPEC]`
1.2.7 **Read-through** vs **cache-aside** vs **write-through** vs **write-behind** vs **write-around**
      vs **refresh-ahead** — six patterns, and the observation that they answer two independent
      questions (who loads, who writes). `[TABLE]`
1.2.8 **Local / in-process / near** vs **remote / distributed / shared** vs **client-side** — three
      placements and three completely different failure modes.
1.2.9 **L1 / L2** as a tier vocabulary, and why borrowing CPU terminology is helpful right up to the
      point where you assume coherence.
1.2.10 **Cache key** vs **cache name** vs **namespace** vs **prefix** vs **tag** vs **surrogate key**
      — six things that all end up concatenated into one Redis key. `[TABLE]`
1.2.11 **Cardinality** of the key space, and why it is the number that decides whether a cache is
      possible at all.
1.2.12 **Warm** / **cold** / **warming** / **pre-warming** / **shadow warming**.
1.2.13 **Stampede** / **thundering herd** / **dogpile** / **cache miss storm** — one phenomenon,
      four names, and the reason a candidate and an interviewer can talk past each other.
1.2.14 **Penetration** vs **avalanche** vs **breakdown** — the Chinese-language cache vocabulary
      (`缓存穿透`/`缓存雪崩`/`缓存击穿`) that has entered global interview practice, mapped onto the
      English terms precisely, because the mapping is not one-to-one. `[TABLE]` `[TRAP]`
      `[RESEARCH]`
1.2.15 **Hot key** vs **big key** vs **hot partition** — three different resource exhaustions.
1.2.16 **Single-flight** / **request coalescing** / **request collapsing** / **mutex load** /
      **lock-and-load** — one technique, five names.
1.2.17 **Negative caching** / **null caching** / **absence caching** / **sentinel**.
1.2.18 **Admission** vs **eviction** as separate policies — the distinction most eviction discussions
      omit entirely, and the one W-TinyLFU is built on. `[PROVE]`
1.2.19 **Scan resistance** and **cache pollution** defined, with the batch job that reads a million
      rows once as the canonical polluter.
1.2.20 **Coherence** vs **consistency** for caches: coherence is "all copies agree"; consistency is
      "reads obey an ordering rule". Multi-pod in-process caches are incoherent by construction.
      `[PROVE]`
1.2.21 **Write amplification** and **invalidation storm** as the two costs of aggressive freshness.
1.2.22 **Serialisation** vs **marshalling** vs **encoding**, and the fact that for a distributed cache
      this is often the dominant cost, not the network.
1.2.23 **Idempotent read** vs **memoisation** vs **caching**: memoisation assumes a pure function;
      caching assumes a mutable origin. Confusing them is how you get an unbounded `HashMap` leak.
      `[X-REF 06]`
1.2.24 **Cache stampede** vs **retry storm** vs **backpressure** — cross-reference the messaging
      vocabulary so the reader has one model. `[X-REF 14]`

## §1.3 Where caches live — every tier, named, with what it can and cannot cache

1.3.1 The tier list as an ordered pipeline from user to disk, so the reader can place any cache
      question: browser memory/disk cache → service worker → OS DNS cache → CDN/edge PoP → reverse
      proxy / API gateway → application in-process cache → distributed cache → database result
      cache → DB buffer pool → OS page cache → storage-device cache. `[TABLE]` `[FLOW]`
1.3.2 The governing principle: **cache as close to the user as the correctness of the data allows.**
      The cheapest request is the one that never reaches your infrastructure. `[PROVE]`
1.3.3 **Browser cache** — heap/memory cache vs disk cache, back/forward cache, and why the browser
      obeys `Cache-Control` but not your intentions. `[X-REF 10]`
1.3.4 **Service worker / Cache Storage API** as a programmable cache you do not control from the
      server.
1.3.5 **DNS cache** as a cache with a TTL you cannot purge, and its negative-caching hazard (SOA
      minimum TTL). One paragraph, then point away. `[X-REF 10]`
1.3.6 **CDN / edge PoP** — shared cache, `s-maxage`, surrogate keys, and the fact that its hit ratio
      is a function of your `Vary` header. `[SPEC]`
1.3.7 **Reverse proxy** (nginx `proxy_cache`, Varnish) as the tier you run yourself, with the
      grace/stale behaviour that predates `stale-while-revalidate`.
1.3.8 **API gateway cache** — and why `ApplicationGateway` caching an authenticated response is the
      most dangerous cache in the QuizStakes architecture, given that it holds the client token
      before the strip. `[TRAP]` `[X-REF 13]`
1.3.9 **In-process / on-heap** cache — nanoseconds, no serialisation, per-instance, dies with the
      process, competes with your app for heap and GC. `[X-REF 06]`
1.3.10 **Off-heap** in-process cache (Ehcache `offheap` tier, Chronicle Map, `MemorySegment`) — no GC
      pressure, serialisation cost per access, sized outside `-Xmx` and therefore outside the
      container limit you set. `[X-REF 06]` `[X-REF 19]`
1.3.11 **Disk tier** in-process (Ehcache `disk`, memcached `extstore`) — the tier nobody remembers
      exists, and when it is the right answer (large, cold, expensive-to-recompute).
1.3.12 **Distributed cache** — Redis/Valkey/Memcached/Hazelcast: shared, survives deploys,
      network-latency-bound, a dependency that can be down.
1.3.13 **Database-internal caches**, enumerated so the reader stops double-counting: the buffer pool,
      the plan cache, the MySQL query cache (removed in 8.0 — a `[VERSION-TRAP]` in itself),
      materialised views as a manual cache. `[X-REF 09]` `[VERSION-TRAP]`
1.3.14 **OS page cache** — why a "disk read" in your latency budget is usually a RAM read, and why
      Redis's `fork` interacts violently with it. One paragraph, then point away. `[X-REF 11]`
1.3.15 **Client-library caches** you did not know you had: connection pools, DNS resolver caches,
      JWKS caches, Hibernate L1, the JVM's `String` pool, `Integer` cache.
      `[X-REF 03]`
1.3.16 **Multi-tier is the norm, and every tier adds a staleness window that composes additively.**
      Two 60 s tiers is a 120 s worst case, not 60. `[PROVE]` `[TRAP]`
1.3.17 The QuizStakes tier map, drawn explicitly: agreement text is cacheable at CDN + in-process +
      Redis; `PendingActions` banners at Redis only; restriction decisions at **no tier at all**;
      document images in object storage behind a CDN with a signed URL. `[TABLE]`
1.3.18 The tier-selection procedure as an ordered set of questions: does it vary per user? can it be
      stale, and for how long? how large? how expensive to recompute? how bad is a leak? Each answer
      eliminates tiers. `[FLOW]`

## §1.4 Read patterns

1.4.1 **Cache-aside (lazy loading)** — the application owns the cache; the cache knows nothing about
      the database. The default, and the one to be able to write on a whiteboard. `[BUILD]`
1.4.2 The cache-aside read path as an ordered trace: build key → `get` → hit? return → miss? load
      origin → populate with TTL → return. Note that a miss pays cache RTT **plus** origin.
      `[FLOW]`
1.4.3 Cache-aside properties: only requested data is cached (memory-efficient), a cache failure
      degrades to slow-but-correct, and it is simple enough to reason about under pressure.
1.4.4 Cache-aside costs: every miss pays the lookup tax, the first request for any key is always
      slow, and stale data persists until TTL or invalidation.
1.4.5 **Read-through** — the cache library loads on miss (`Caffeine.build(loader)`, `@Cacheable`,
      JCache `CacheLoader`). Tidier code; the cache becomes a dependency of reads and a failure in it
      now fails the read unless you handle it. `[API]`
1.4.6 The read-through/cache-aside distinction is **who owns the loader**, and the practical
      consequence: read-through gives you free single-flight, cache-aside does not. `[PROVE]`
1.4.7 **Refresh-ahead** — reload before expiry while serving the old value
      (`refreshAfterWrite`). Hides miss latency for hot keys; wastes work on cold ones. `[API]`
1.4.8 **Cache warming / preloading** as a read pattern rather than an operational chore: `loadAll`,
      a curated hot-key list from yesterday's access logs, and the reference data every service needs
      at startup.
1.4.9 **Serve-stale-on-error** as a read pattern: keep the expired value, serve it if the origin
      fails or times out. The single highest-value resilience behaviour a cache has. `[PROVE]`
1.4.10 **Negative caching** as a read pattern, deferred in mechanism to § 2.4 but named here so the
      read-path taxonomy is complete.
1.4.11 **Read-your-own-writes** on a cache: the client uploads a document and refreshes; the write
      invalidated Redis but the pod's L1 still holds the banner. Scenario § 15.2's exact case, and
      why "invalidate then read" is not enough. `[TRAP]` `[PROVE]`
1.4.12 Comparison table across all read patterns: who loads, single-flight for free?, failure
      behaviour, code shape, when to choose. `[TABLE]`

## §1.5 Write patterns

1.5.1 **Write-around (write-invalidate)** — write the origin, delete the key. The default, and the
      one the current guide correctly insists on. `[BUILD]`
1.5.2 **Why delete beats update**, proved with the two-writer interleaving: A saves v1, B saves v2, B
      sets cache v2, A sets cache v1 → DB has v2, cache has v1, permanently wrong until TTL. With
      delete, both delete, and the next read repopulates from whatever the DB actually holds.
      `[PROVE]` `[FLOW]`
1.5.3 The three secondary reasons delete beats update: no serialisation cost on the write path, no
      caching of values nobody will read, and no risk of writing a partially-constructed object.
1.5.4 **Write-through** — write cache and origin synchronously, origin write inside the same logical
      operation. Cache is never stale relative to the origin; every write pays cache latency; you
      cache data that may never be read.
1.5.5 **Write-through is still a dual write** unless the cache and the origin share a transaction —
      which they never do. If the cache write succeeds and the DB write fails, or the reverse, you
      are inconsistent with no error raised. `[PROVE]` `[TRAP]` `[RESEARCH]`
1.5.6 **Write-behind (write-back)** — write the cache, flush to the origin asynchronously. Fastest
      writes, batched origin load, **loses data if the cache dies before flush**.
1.5.7 The rule preserved verbatim from the current guide: **do not invent write-behind for business
      data** — you have built an unreplicated, unbacked-up primary store and called it a cache.
1.5.8 Where write-behind is legitimate: inside databases and storage engines, where a write-ahead log
      supplies the durability the cache lacks. Name the mechanism so the reader sees the difference.
      `[X-REF 09]`
1.5.9 The QuizStakes write-behind case from § 15.4, worked: **limit counters**. Write-behind loses a
      deposit against the daily limit if the node dies — which is a compliance failure
      (`DEPOSIT_LIMITED`, § 10.4), not a rounding error. `[PROVE]`
1.5.10 **Write-invalidate vs write-update vs write-allocate** as the CPU-cache vocabulary for the
      same three choices, for readers who met it there first.
1.5.11 **Delete after commit, not inside the transaction** — deleting inside means a reader can
      repopulate from the pre-commit state, and a rollback has evicted for nothing. The mechanism is
      `TransactionSynchronization.afterCommit` / `@TransactionalEventListener(AFTER_COMMIT)`.
      `[API]` `[X-REF 07]`
1.5.12 **The read/write race that delete does not fix**, preserved as the guide's flagship trace and
      expanded: t0 reader misses; t1 reader reads v1; t2 writer commits v2; t3 writer deletes
      (nothing there); t4 reader sets v1 with a full TTL. Cache now holds v1 while the DB holds v2,
      for the whole TTL. `[PROVE]` `[FLOW]` `[TRAP]`
1.5.13 Mitigations in increasing order of cost, each with what it actually buys: mandatory TTL (bounds
      damage); delete-after-commit (removes one window); **delayed double delete** (delete, commit,
      delete again after ~500 ms); version/CAS on write-back; single-flight on the read path; CDC-driven
      invalidation. `[TABLE]`
1.5.14 Why the window can be narrowed but never closed without a shared transaction, stated as an
      impossibility rather than a to-do. `[PROVE]`
1.5.15 The honest framing, preserved verbatim: cache-aside gives **eventual consistency with a
      bounded staleness window**. If a requirement genuinely cannot tolerate that, do not cache it.
1.5.16 `@Cacheable` + `@CacheEvict` is read-through plus explicit invalidation. It is convenient and
      it hides the mechanism, which is exactly why people using it cannot answer the race-condition
      question. Know what it compiles down to. `[TRAP]`
1.5.17 The write-pattern comparison table across write path, read path, staleness relative to origin,
      durability risk, write latency, and when to choose. `[TABLE]`

## §1.6 Expiry — TTL, TTI, jitter, and the correctness argument

1.6.1 **Every cache entry gets a TTL. No exceptions.** The TTL is not primarily an eviction
      mechanism — it is a **correctness backstop** against invalidation logic that will eventually be
      missed. `[PROVE]`
1.6.2 The four ways invalidation gets missed, so the backstop argument is concrete: a new write path,
      a batch job, a manual DB fix, a bug.
1.6.3 Choosing a TTL as one question: "how stale can this be before someone is harmed?" — then pick
      something under that.
1.6.4 The TTL table, preserved and extended to QuizStakes objects: reference data (jurisdictions,
      restriction types) hours–days; **agreement version text** hours, push-invalidated on publish;
      `ProfileService` composite 30–60 s; `PendingActions` projection seconds; JWKS tied to key
      rotation; feature flags seconds or push-invalidated; negative results 30 s–2 min; operator
      session 30–90 min sliding; **`CASH_AVAILABLE` and restriction decisions: no TTL, because no
      cache.** `[TABLE]` `[NUM]`
1.6.5 **Absolute (`expireAfterWrite`) vs sliding (`expireAfterAccess`)** expiry, and the failure mode
      of each: absolute expires hot data you still want; sliding **never refreshes a permanently-hot
      key**, so it never picks up changes. `[PROVE]` `[TRAP]`
1.6.6 The rule: absolute for correctness-relevant data, sliding for sessions. Both together
      (`expireAfterWrite` + `expireAfterAccess`) when you want "at most N, and drop it if unused".
1.6.7 **Variable per-entry expiry** (`Caffeine.expireAfter(Expiry)`, JCache `ExpiryPolicy`) for
      objects whose freshness requirement is data-dependent — an agreement version that has been
      superseded (`AO-290`) should have a shorter TTL than the current one. `[API]`
1.6.8 **TTL jitter** — the operator's signature. Populating 10,000 keys during a deploy with an
      identical 10-minute TTL builds a synchronised stampede generator with a 10-minute period, and
      it presents as a mysterious periodic latency spike. `[PROVE]` `[NUM]`
1.6.9 The fix in one line: 10–20% random jitter on every TTL. Show the arithmetic that turns a single
      10,000-miss second into 10,000 misses spread over 120 s. `[BUILD]` `[NUM]`
1.6.10 The QuizStakes instance: 55k concurrent sessions on a major sporting event, all fetching the
      agreement text after a synchronised cache population, against a `ClientAgreements` service
      sized for steady state. `[NUM]`
1.6.11 **TTL is not a substitute for invalidation** and invalidation is not a substitute for TTL. You
      need both, for different reasons: invalidation for freshness, TTL for the failure of
      invalidation. `[PROVE]`
1.6.12 **Expiry is lazy almost everywhere.** An expired entry usually occupies memory until it is
      touched or a background job finds it, so "expired" and "gone" are different states and your
      memory graph knows it. `[TRAP]`
1.6.13 Where each system does its expiry work, named now and dissected in Part 3: Redis lazy +
      active-expire cycle; Caffeine on read/write plus a hierarchical timer wheel; memcached lazy plus
      `lru_crawler`; HTTP freshness computed by the client on every use. `[TABLE]`
1.6.14 **Negative TTLs are short on purpose** (30 s – 2 min). A resource that does not exist now often
      exists in a moment — a just-created record, replication lag — and a long negative TTL turns a
      race into a user-visible "your new item doesn't exist" bug. `[PROVE]`
1.6.15 The QuizStakes negative-caching hazard from § 15.4 stated exactly: `"this client has no
      requirements"` cached, then a rule raises one — and the client sees no banner for the whole
      negative TTL while `AA-600 DOCUMENTS_REQUESTED` is already true. `[TRAP]`
1.6.16 **Expiry-on-write vs expiry-on-read semantics** for a value that is refreshed rather than
      replaced (`INCR` on a Redis key with a TTL leaves the TTL untouched; `SET` clears it). `[CFG]`
      `[TRAP]` `[SOURCE]`

## §1.7 Key design

1.7.1 **The rule: every input that changes the output must appear in the key.** Everything else in
      this section is a consequence. `[PROVE]`
1.7.2 The failure this prevents, stated at full severity: **serving one user's data to another.**
1.7.3 The inputs people forget, enumerated: client/tenant id, **role and permission scope**, locale
      and currency, feature-flag variant, API version, pagination offset and page size, sort order,
      filter parameters, `Accept` / `Accept-Encoding` content negotiation, and time bucket.
      `[TABLE]`
1.7.4 The QuizStakes version of the bug, which is worse than the generic one: `ProfileService`
      assembles PII, balances and compliance state for a *specific operator role*
      (§ 6.3 checks roles, § 15.7 names the privilege concentration). Cache that composite without
      the role in the key and a reviewer sees an approver's view. `[TRAP]` `[X-REF 13]`
1.7.5 **Naming convention as schema**: Redis has a flat keyspace, so the convention *is* the schema.
      `{app}:{entity}:{version}:{id}[:{qualifier}]`, with the QuizStakes examples:
      `agreements:version:v1:current`, `pendingactions:client:v2:9876`,
      `profile:composite:v3:9876:role:reviewer`, `ratelimit:vendor:idv:v1:2026-09-03T14:32`.
      `[TABLE]`
1.7.6 **Include a version segment** so a schema change invalidates en masse — and so a new pod cannot
      deserialise an old-shape value during a rolling deploy. `[PROVE]`
1.7.7 Use `:` as the separator, because every Redis UI, `redis-cli --scan` workflow and monitoring
      tool assumes it.
1.7.8 **Keep keys short-ish.** With millions of keys the key strings themselves cost real memory, and
      the arithmetic is worth showing: 2.4M keys × 60 bytes of key = 144 MB before any values.
      `[NUM]` `[PROVE]`
1.7.9 **Prefix by application/service** so a shared cache is debuggable and a flush can be scoped.
1.7.10 **Hash the key when it would otherwise be unbounded** (a filter set, a long query string), and
      the two costs of doing so: you can no longer read the keyspace, and you must keep the hash
      collision-resistant enough that two distinct inputs cannot share an entry. `[PROVE]`
1.7.11 **Do not cache the whole world under one key.** A single key holding a 50 MB list means every
      read transfers 50 MB and every change invalidates everything. Cache at the granularity you
      read at. `[TRAP]`
1.7.12 The counter-pressure: too fine a granularity means N round trips per request, which is where
      pipelining and `MGET` earn their place. State the trade rather than a rule. `[PROVE]`
1.7.13 **Key collision across tenants** as a security finding, not a bug: `documents:{folderId}` with
      no tenant segment in a multi-tenant system is a cross-tenant read. `[TRAP]` `[X-REF 13]`
1.7.14 **Canonicalise before you key.** `?b=2&a=1` and `?a=1&b=2` are the same request and must be
      the same key; `/Agreements` and `/agreements` may or may not be. Trailing slashes, default
      parameter values, and case are all real cache-key bugs. `[TRAP]`
1.7.15 **Time-bucketed keys** as a deliberate pattern (rate limiters, per-minute aggregates), and why
      they self-expire without invalidation.
1.7.16 **Key naming for taggability**: if you will ever need "everything for this client", the key
      must either embed the client id in a scannable position or be registered in a tag index. Decide
      this at design time, because retrofitting it means enumerating the keyspace. `[PROVE]`

## §1.8 What must never be cached — the invariant-driven exclusion list

1.8.1 The general rule: **anything that authorises an action** must be read live. A cache in front of
      an authorisation decision converts a permission check into a permission *memory*. `[PROVE]`
1.8.2 **Scenario invariant 12, quoted**: "Restriction decisions are read live, never from a cache or
      token. Consequence if violated: stale permission authorises a blocked action." This is the
      guide's hardest constraint. `[SOURCE]`
1.8.3 The harm, made concrete from § 15.4: "Cached restriction state says clear; the client
      self-excluded thirty seconds ago; a stake is accepted." Invariant 8 calls this "the most
      serious client-harm failure possible."
1.8.4 Why a short TTL does not rescue it: the requirement is a **hard 500 ms** budget on
      self-exclusion taking effect, and no TTL short enough to satisfy that leaves any cache benefit.
      Work the arithmetic. `[PROVE]` `[NUM]`
1.8.5 Why the pub/sub-invalidated L1 does not rescue it either: pub/sub is best-effort (§ 2.6), so the
      guarantee would rest on the TTL, which § 1.8.4 already eliminated. `[PROVE]`
1.8.6 **`CASH_AVAILABLE` is not cacheable** for a second, independent reason: § 15.2 lists it under
      "strong consistency requirement — it authorises spending, so it cannot be eventually
      consistent."
1.8.7 The distinction that makes the rule usable rather than paralysing: **`BalanceView` may cache
      for display and preview; `FundsLedger` serves decisions.** The same number at two trust levels,
      and the cache lives only on the display side. `[PROVE]` `[TABLE]`
1.8.8 The same distinction for restrictions: `ProfileService` and `PendingActions` may project them
      for display; **a display projection must never be the input to an authorisation.** The bible
      must state how you enforce that in code, not just in prose — separate types, separate methods,
      and a name that makes misuse obvious. `[BUILD]`
1.8.9 The other never-cache categories, generalised: revoked-token lists and permission grants;
      one-time tokens and nonces; anything whose staleness is a regulatory breach; anything you cannot
      name a bounded staleness window for.
1.8.10 **Never in-process cache anything security-relevant with a long TTL.** Revocation that takes
      five minutes to reach some pods but not others is a security finding, and it presents as
      "intermittent authorisation failures". `[TRAP]` `[X-REF 13]`
1.8.11 The write pass must give the reader the sentence to say in an interview: *"I'd cache the
      display projection and read the authority live. If the requirement is a hard latency budget on
      a permission change taking effect, the answer is a faster authority, not a cache."*
1.8.12 The counter-argument to steelman and then answer: "but `ClientRestrictions` is 8 instances at
      4 GB with an extreme request rate — surely it caches internally?" It may cache its own storage
      reads, because it remains the authority and can invalidate its own memory synchronously with
      its own writes. That is a different claim from a *caller* caching the decision. `[PROVE]`

## §1.9 The cache API surface, and the guarantees each method actually gives

1.9.1 The read methods and their differences: `get(key)`, `getIfPresent(key)`, `get(key, loader)`,
      `getAll(keys)`, `getAllPresent(keys)`. Only one of them loads. `[API]`
1.9.2 `get(key, Function)` as the **atomic compute-on-miss** primitive, and the guarantee it gives:
      the mapping function runs at most once per absent key, concurrent callers block and receive the
      same value. This is single-flight for free. `[PROVE]` `[API]`
1.9.3 The write methods: `put`, `putAll`, `asMap().putIfAbsent`, and the fact that `put` on a
      read-through cache is usually a mistake (you are asserting a value the loader did not produce).
1.9.4 The removal methods: `invalidate(key)`, `invalidateAll(keys)`, `invalidateAll()`, and the very
      different cost of the third one.
1.9.5 `asMap()` as the escape hatch, and the `ConcurrentMap` semantics it exposes — including the
      compound-action rules that apply to it. `[X-REF 05]` `[API]`
1.9.6 **Statistics**: `recordStats()`, `cache.stats()`, `hitRate()`, `missCount()`, `loadFailureRate()`,
      `averageLoadPenalty()`, `evictionWeight()`. Always wired to metrics — an unmeasured cache is a
      cache you cannot reason about. `[API]` `[METRIC]`
1.9.7 **Size and weight**: `maximumSize` vs `maximumWeight` + `Weigher`, `estimatedSize()`,
      `cleanUp()`, and why `estimatedSize()` is estimated. `[API]` `[NUM]`
1.9.8 **Removal listeners**: `removalListener` vs `evictionListener` — one fires for every removal
      including explicit invalidation, the other only for policy-driven eviction, and they run on
      different threads. Getting this wrong is how a "cache eviction metric" ends up counting your own
      `invalidate` calls. `[API]` `[TRAP]` `[RESEARCH]`
1.9.9 `RemovalCause` as an enumerable set — `EXPLICIT`, `REPLACED`, `COLLECTED`, `EXPIRED`, `SIZE` —
      and why exposing it as a metric tag turns "why is my hit rate falling" into a one-glance answer.
      `[API]` `[METRIC]`
1.9.10 **Async surfaces**: `AsyncCache`, `AsyncLoadingCache`, `CompletableFuture`-valued entries, and
      the in-flight-entry semantics (an entry exists while its future is incomplete). `[API]`
      `[X-REF 05]`
1.9.11 **Reference-based eviction** (`weakKeys`, `weakValues`, `softValues`) and why `softValues` is
      almost always the wrong answer: it hands your eviction policy to the garbage collector, which
      optimises for heap, not hit rate. `[TRAP]` `[X-REF 06]`
1.9.12 What the API deliberately does not offer, and why: no iteration order guarantee, no size
      guarantee, no "is this fresh" query, no cross-node coherence.
1.9.13 The Redis-side equivalent surface for the same operations, so the reader can map one to the
      other: `GET`/`MGET`, `SET … EX … NX/XX/KEEPTTL/GET`, `GETEX`, `DEL`/`UNLINK`, `EXISTS`, `TTL`,
      `EXPIRE … NX|XX|GT|LT`, `SCAN`, `OBJECT ENCODING`, `MEMORY USAGE`. `[CLI]` `[API]`
1.9.14 `SET key val EX 600 NX GET KEEPTTL` read argument by argument, because each flag exists to
      close a specific race. `[WIRE]` `[PROVE]`

## §1.10 Serialisation — the cost everyone omits from the latency budget

1.10.1 The framing: for a distributed cache, serialisation is frequently a larger cost than the
      network hop, and it is paid twice (write and read). `[PROVE]` `[NUM]`
1.10.2 The format options with their real trade-offs: Java native serialisation, JSON (Jackson),
      CBOR/Smile, Protobuf, Avro, Kryo, MessagePack, and raw bytes for primitives. `[TABLE]`
1.10.3 **Java native serialisation is disqualified** for a cache: slow, verbose, brittle across class
      changes, and a **deserialisation-gadget attack surface** on any cache an attacker can write to.
      `[TRAP]` `[X-REF 13]`
1.10.4 JSON as the default: human-debuggable in `redis-cli`, schema-tolerant, 2–5× larger and
      5–20× slower than binary. Say the numbers and where they came from. `[NUM]` `[RESEARCH]`
1.10.5 **Schema evolution in a cache is a rolling-deploy problem**, not a data problem: for the
      duration of the deploy, old pods read new values and new pods read old ones. `[PROVE]`
1.10.6 The two fixes, and why one is strictly better: tolerant readers (ignore unknown fields, default
      missing ones), and a **version segment in the key** so the two shapes never meet. `[PROVE]`
1.10.7 **Compression** — when it pays (large JSON, cross-AZ transfer costs) and when it does not
      (small values, CPU-bound service). LZ4/Snappy vs gzip/zstd, and the fact that you are now
      trading the cache's CPU for its bandwidth. `[NUM]`
1.10.8 **What you serialise matters as much as how.** Caching a Hibernate entity graph serialises the
      proxies, the collections and the lazy initialisers; caching a purpose-built DTO or record
      serialises the fields you actually read. `[TRAP]` `[X-REF 08]`
1.10.9 The QuizStakes shape: cache a `AgreementVersionView` record with `version`, `publishedAt`,
      `documentUri` and a rendered hash — not the `ClientAgreements` entity. Show both and measure the
      difference. `[BUILD]` `[NUM]`
1.10.10 `null` cannot be serialised as a value in several providers, which is exactly why negative
      caching needs a sentinel and why `RedisCacheConfiguration.disableCachingNullValues()` exists.
      `[API]` `[TRAP]`
1.10.11 Spring's serializer surface named precisely: `RedisSerializer`, `StringRedisSerializer`,
      `GenericJackson2JsonRedisSerializer`, `Jackson2JsonRedisSerializer`,
      `JdkSerializationRedisSerializer` (the default, and the one to replace),
      `RedisSerializationContext.SerializationPair`. `[API]` `[CURRENCY]`
1.10.12 Jackson 3 in Spring Boot 4.x: the `tools.jackson` package move and what it does to a
      serializer bean you copied from a 3.x blog post. `[VERSION-TRAP]` `[RESEARCH]`
1.10.13 Serialised size arithmetic for capacity planning: measure one real object with
      `MEMORY USAGE`, multiply by cardinality, add key bytes and per-key overhead. Do this before
      choosing an instance size. `[NUM]` `[CLI]`

---

# PART 2 — INTERMEDIATE

## §2.1 The master cost model

2.1.1 **One master table for the whole topic**, covering every operation of every cache variant with
      amortised and worst case split out: in-process get/put/invalidate/eviction, Redis
      GET/SET/DEL/UNLINK/MGET/pipelined-batch/SCAN/KEYS/FLUSHALL/EXPIRE, memcached get/set/multiget,
      HTTP hit / 304 revalidation / full miss, and the composite two-tier path. Columns: amortised,
      worst case, why the worst case happens, what it blocks. `[TABLE]` `[NUM]`
2.1.2 **Amortised vs worst case for an in-process cache get**: O(1) hash lookup amortised; worst case
      is a resize, a treeified bucket, an eviction cascade, or the read buffer draining under lock.
      `[PROVE]` `[X-REF 02]`
2.1.3 **Amortised vs worst case for a Redis GET**: O(1) plus one network RTT amortised; worst case is
      the command queued behind a `KEYS`, a big-key `DEL`, an `activeExpireCycle` burst, an
      `fsync`-blocked AOF write, or a fork-induced page-fault storm. **The worst case is not about
      your command.** `[PROVE]`
2.1.4 The latency budget arithmetic for the 30 ms restriction-decision path and the 150 ms
      stake-reservation path: how many cache round trips fit, and why `ProfileService`'s eight-owner
      fan-out cannot be one of them. `[NUM]` `[PROVE]`
2.1.5 **Little's Law applied to a cache tier**: `concurrency = arrival rate × latency`. At 1,200/sec
      with a 0.5 ms Redis call you need 0.6 concurrent connections; at 1,200/sec with a 50 ms origin
      call on a cold cache you need 60. This is the number that sizes your connection pool and
      explains the pool exhaustion that follows a flush. `[PROVE]` `[NUM]` `[X-REF 05]`
2.1.6 The **cost of a miss** decomposed: cache RTT + origin latency + serialisation + cache write
      RTT. A miss is more expensive than no cache at all, which is why a cache with a bad hit ratio
      is a net negative. `[PROVE]` `[NUM]`
2.1.7 The break-even hit ratio, derived: with hit cost `h`, miss cost `m` and uncached cost `u`, the
      cache pays only when `h·H + m·(1−H) < u`. Solve for `H`. `[PROVE]`
2.1.8 **Throughput ceilings** to have in mind: a single Redis instance's realistic ops/sec and where
      it becomes CPU-bound on one core, pipelined vs unpipelined, and the 8.6 figure (3.5M ops/sec
      at pipeline 16, >5× Redis 7.2) with the caveat that it is a benchmark, not your workload.
      `[NUM]` `[CURRENCY]` `[RESEARCH]`
2.1.9 **The N+1 round trip** as the dominant real-world cache cost: 50 sequential `GET`s at 0.5 ms is
      25 ms, which blows the 30 ms budget on its own. `MGET`, pipelining and batch loaders are the
      fix. `[PROVE]` `[NUM]`
2.1.10 Cross-AZ and cross-region cost: added latency **and** data-transfer charges, and why a cache
      replica in each AZ is often cheaper than the transfer. `[X-REF 18]` `[CURRENCY]`

## §2.2 Eviction — every policy, its internals summarised, and how to choose

2.2.1 The frame that makes eviction tractable: an eviction policy is a **prediction** of future reuse
      from past behaviour, and every policy is a different bet about which past signal predicts best.
      `[PROVE]`
2.2.2 **Belady's optimal (MIN/OPT/clairvoyant)** — evict the entry reused furthest in the future.
      Unimplementable, and therefore the yardstick every real policy is measured against. `[PROVE]`
2.2.3 **FIFO** — evict in insertion order. No per-access metadata, no locks on read, and a
      surprisingly competitive baseline on modern traces. `[RESEARCH]`
2.2.4 **LRU** — evict least recently used. Exact LRU needs a doubly-linked list plus a hash map, and
      every read is a write to that list, which is the concurrency problem. `[PROVE]` `[X-REF 02]`
2.2.5 **LRU's failure mode: scan pollution.** One batch job reading a million rows once evicts the
      entire hot set. This is not a tuning problem, it is what LRU means. `[PROVE]` `[TRAP]`
2.2.6 **LRU-K / 2Q / LIRS** — use the *K*-th most recent reference rather than the most recent, to
      distinguish a one-off touch from real reuse. Named, mechanism in one paragraph each.
2.2.7 **SLRU (segmented LRU)** — probation and protected segments, with promotion on second hit. The
      structure Caffeine's main space uses and memcached's HOT/WARM/COLD generalises.
2.2.8 **LFU** — evict least frequently used. Resists scan pollution; suffers **cache pollution by
      historical popularity** unless it decays. `[PROVE]`
2.2.9 **Windowed / decaying LFU** as the fix, and the two ways to decay: halving on a schedule
      (Caffeine's sketch reset) and probabilistic decay per sample (Redis's `lfu-decay-time`).
2.2.10 **TinyLFU** — an *admission* policy, not an eviction policy: on a miss, compare the candidate's
      estimated frequency against the victim's and admit only if the candidate wins. `[PROVE]`
      `[SOURCE]`
2.2.11 **W-TinyLFU** — an LRU admission window in front of a TinyLFU-guarded SLRU main space, which
      fixes TinyLFU's weakness on sparse bursts. Caffeine's policy. Mechanism here; internals in
      § 3.2.
2.2.12 **ARC (adaptive replacement cache)** — four lists (T1, T2, B1, B2) balancing recency against
      frequency with a self-tuning target size. Named, mechanism in one paragraph, plus the note that
      its IBM patent is why it is absent from many open-source caches. `[RESEARCH]`
2.2.13 **CLOCK / second-chance** and **CLOCK-Pro** — approximate LRU with a reference bit and a
      circular scan, which is what an OS page cache actually does. `[X-REF 11]`
2.2.14 **Random** and **random-with-sampling** — cheap, lock-free, and much better than intuition
      suggests. Redis's approximated LRU is exactly this plus a candidate pool.
2.2.15 **S3-FIFO** (SOSP 2023) — small FIFO + main FIFO + ghost queue, exploiting the observation
      that most objects are never reused. `[RESEARCH]`
2.2.16 **SIEVE** (NSDI 2024) — one FIFO queue, one visited bit, a moving hand; simpler than LRU,
      lower miss ratio than nine state-of-the-art algorithms on >45% of 1,559 traces, and 17%/125%
      higher throughput than optimised LRU at 1/16 threads. `[NUM]` `[RESEARCH]` `[SOURCE]`
2.2.17 **Lazy promotion and quick demotion** as the two properties that explain *why* the modern
      algorithms win, stated as a principle the reader can apply rather than two more names.
      `[PROVE]` `[RESEARCH]`
2.2.18 **TTL-based eviction (`volatile-ttl`)** — evict the shortest remaining TTL. Only sensible when
      your TTLs encode value.
2.2.19 **Size/weight-aware eviction** — `Weigher` and `maximumWeight`, and why byte-bounded is the
      correct bound when entry sizes vary by 100× (agreement documents at 40–900 KB).
      `[API]` `[NUM]`
2.2.20 **Admission control as the missing half of every eviction discussion**, restated: a cache with
      a good eviction policy and no admission policy still lets a scan in. `[PROVE]`
2.2.21 **The eviction comparison table**: metadata per entry, read-path cost, write-path cost, scan
      resistance, burst resistance, concurrency friendliness, where it ships. `[TABLE]`
2.2.22 **Choosing one, as a procedure**: stable hot set + periodic scans → LFU-family; strong recency,
      little reuse → FIFO/SIEVE; unknown or shifting → W-TinyLFU or adaptive; keys with meaningful
      TTLs → `volatile-ttl`; genuinely uniform access → random.
2.2.23 **Eviction is not expiry.** Expiry is "this entry's TTL passed"; eviction is "I need memory and
      chose a victim." A key can be evicted long before its TTL, which is fine for a cache and
      catastrophic if you were storing state. `[PROVE]` `[TRAP]`
2.2.24 **Eviction is a capacity signal, and `evicted_keys` rising is an early warning** that the
      working set has outgrown memory and the hit ratio is about to fall off the § 1.1.11 cliff.
      `[METRIC]`

## §2.3 Invalidation — strategies, and why it is genuinely hard

2.3.1 Karlton's line preserved, and then the actual reason it is true: invalidation requires knowing
      every place data is cached and every code path that changes it, forever, as both sets grow
      independently. It is a global coupling problem in a codebase designed for local reasoning.
      `[PROVE]`
2.3.2 **TTL only** — let it expire. Trivial, no coupling, guaranteed staleness window.
2.3.3 **Explicit invalidation on write** — delete the key in the write path. Fresh almost
      immediately; every new write path must remember; **misses are silent**, which is the whole
      problem.
2.3.4 **Event-driven** — the write emits an event and subscribers invalidate. Decoupled, works across
      services, eventually consistent, needs a broker. `[X-REF 14]`
2.3.5 **CDC-driven** — tail the WAL/binlog and invalidate from the replication stream. Catches *every*
      change including manual SQL and batch jobs, and invalidation strictly follows the commit. The
      most correct option and the most infrastructure. `[X-REF 09]` `[X-REF 14]`
2.3.6 **Versioned keys** — bump a version segment to invalidate everything at once. Atomic mass
      invalidation, no delete storm, no key enumeration; old entries linger until evicted, which is a
      memory cost you must plan for. `[PROVE]`
2.3.7 The versioned-key case the current guide makes and the bible must keep: a deploy that changes a
      cached object's shape bumps the version and instantly invalidates everything, with no risk of a
      new pod deserialising an old-format value. **Forgetting this causes deserialisation exceptions
      across the fleet during a rolling deploy.**
2.3.8 **Generation / epoch counters** as the same idea with the version held in the cache itself:
      read `gen:agreements`, prefix keys with it, `INCR` it to invalidate. One round trip added to
      every read; one command to invalidate a whole class. `[PROVE]` `[BUILD]`
2.3.9 **Tag-based invalidation** — group keys by tag and invalidate the tag. Matches "everything for
      this client". Needs support: Redis sets as tag indexes, `@CacheEvict(allEntries = true)` per
      cache name, CDN surrogate keys. `[TABLE]`
2.3.10 Tag-index mechanics and their cost: the index is itself state that can leak (tags accumulating
      keys that no longer exist), so it needs its own TTL or a reaper. `[PROVE]`
2.3.11 **Write-through as invalidation** — the cache is updated as part of the write, so it is never
      stale relative to the origin. Does not help other instances' local caches.
2.3.12 **Namespace flush** (`FLUSHDB`, `SCAN`-and-delete by prefix) as the blunt instrument, and why
      `SCAN` + `UNLINK` in batches is the only production-safe form. `[CLI]` `[TRAP]`
2.3.13 The invalidation-strategy comparison table: mechanism, freshness, coupling, failure mode when
      it is missed, infrastructure required. `[TABLE]`
2.3.14 **The rule that prevents most invalidation bugs**, preserved verbatim: put all writes for a
      given entity behind **one** method and invalidate there. If eight services can write, you need
      event- or CDC-driven invalidation, because you will never keep eight write paths in sync.
2.3.15 The QuizStakes invalidation case, worked in full: `AgreementVersionPublished`
      (§ 14.1, published by `ClientAgreements`, consumed by `AccountOpening` and `PendingActions`)
      makes every cached copy of the agreement text **legally wrong**, and `AO-290
      AGREEMENTS_SUPERSEDED` requires re-acceptance. Trace the invalidation across CDN, Redis, and
      every pod's L1, and say what the correctness argument is at each tier. `[FLOW]` `[PROVE]`
2.3.16 The second QuizStakes case: `DocumentRequirementSatisfied` must clear the `PendingActions`
      banner, and § 15.4's "projection lag" is what you see when it does not. `[TRAP]`
2.3.17 **The dual-write problem named properly**: writing the origin and the cache are two writes to
      two systems with no shared transaction, so any pair of orderings has a failure that leaves them
      disagreeing. This is the same problem as § 14's outbox, and the bible must say so and reuse the
      vocabulary. `[PROVE]` `[X-REF 14]`
2.3.18 Why Redis cannot join a database transaction, stated mechanically: no XA participation, no
      2PC, `MULTI/EXEC` is not a distributed transaction, and a `SET` that succeeded cannot be rolled
      back by a DB rollback. `[PROVE]`
2.3.19 **Invalidation ordering hazards**: two invalidations for the same key arriving out of order,
      and an invalidation racing a repopulation. Version-stamping the cached value so a stale write
      loses is the general fix. `[PROVE]`
2.3.20 **Invalidation is not free.** A hot entity invalidated on every write turns the cache into a
      write-amplifier with a 0% hit ratio. Measure invalidations per second next to hits.
      `[METRIC]` `[TRAP]`
2.3.21 **`@CacheEvict(beforeInvocation = true)` vs `false`**, and the precise consequence of each: the
      default (`false`) skips eviction if the method throws, leaving a stale entry after a partial
      failure; `true` evicts even on failure, at the cost of an unnecessary miss. `[API]` `[PROVE]`
2.3.22 What to do when you cannot invalidate at all — third-party caches, browser caches already
      served, a CDN mid-flight: change the key (fingerprinted URLs), not the value. `[PROVE]`

## §2.4 The failure modes, each with its mitigations

2.4.1 **Stampede / thundering herd — mechanism.** A hot key expires, is evicted, or the cache
      restarts; between disappearance and repopulation every concurrent request for that key misses
      and independently queries the origin. `[FLOW]`
2.4.2 The arithmetic that makes it land: 5,000 rps on one key with a 200 ms origin query gives 1,000
      concurrent identical queries; the origin saturates, queries slow, repopulation takes longer,
      more requests pile in. **A single expiring key can take down a database.** `[NUM]` `[PROVE]`
2.4.3 The QuizStakes instance from § 15.4, quantified: the agreement cache expires and **ten thousand
      in-flight journeys** fetch it at once, against `ClientAgreements` — which is a legal evidence
      store, not a high-throughput read service. `[NUM]`
2.4.4 **Mitigation 1 — single-flight / request coalescing.** One loader per key; everyone else waits
      for its result. In-process this is `get(key, loader)`; the guarantee is that the mapping
      function runs once. `[BUILD]` `[PROVE]`
2.4.5 **Per-instance coalescing already removes most of the load**, and it has none of the
      complexity: with 40 `ApplicationGateway` pods, in-process coalescing turns 10,000 concurrent
      misses into 40 origin calls. Do this first. `[PROVE]` `[NUM]`
2.4.6 **Mitigation 1b — distributed single-flight**, when 40 origin calls is still too many:
      `SET lock:<key> <token> NX PX 5000`, winner loads and populates, losers sleep briefly and
      re-read or serve stale. `[BUILD]` `[WIRE]`
2.4.7 The lock's hazards, inherited from `14-messaging-queues.md` § 12 but re-argued here: expiry
      before the load finishes, the non-atomic release, and the GC pause that makes both worse. The
      saving grace is that **a duplicate load is wasteful, not incorrect**, so a simple TTL lock is
      adequate — and you must say why, or you have accidentally claimed correctness. `[PROVE]`
      `[X-REF 14]`
2.4.8 The correct release: delete only if the token matches, via a Lua script, because `GET`-then-`DEL`
      can delete someone else's lock. `[BUILD]` `[PROVE]`
2.4.9 **Mitigation 2 — refresh-ahead.** Refresh before expiry while still serving the old value;
      `refreshAfterWrite` triggers an async reload on the next access and **immediately returns the
      stale value**. Nobody waits, and the key never vanishes. `[API]` `[PROVE]`
2.4.10 **Mitigation 2b — probabilistic early expiry (XFetch).** Refresh with a probability that rises
      as expiry approaches, computed from the last load's duration, so refreshes stagger across
      instances with no coordination. State the actual criterion from the paper —
      `now − delta·beta·log(rand()) ≥ expiry` — and explain each term. `[PROVE]` `[NUM]`
      `[RESEARCH]` `[SOURCE]` `[BUILD]`
2.4.11 **Mitigation 3 — serve stale on error.** Keep the expired value and serve it if the origin
      fails or times out; combine with a circuit breaker so you stop hammering a dead origin. The
      HTTP spelling is `stale-while-revalidate` / `stale-if-error`. `[SPEC]`
2.4.12 **Mitigation 4 — never expire hot keys; refresh them out of band.** A background job rewrites a
      handful of critical keys on a schedule so they can never stampede. The cost: if the refresher
      dies the data silently ossifies, so you must alert on refresher staleness. Reserve this for a
      handful of keys. `[METRIC]`
2.4.13 **Mitigation 5 — jittered TTLs** (§ 1.6.8), which prevents the synchronised form rather than
      the single-key form.
2.4.14 **Mitigation 6 — admission-controlled warm-up**: rate-limit or circuit-break the origin behind
      the cache so a mass miss degrades instead of destroying it. `[X-REF 22]`
2.4.15 The mitigation comparison table: what it prevents, added latency, added complexity, what it
      does *not* prevent. `[TABLE]`
2.4.16 **Cache penetration — mechanism.** Requests for keys that do not exist in the origin either, so
      nothing is ever cached and every request reaches the origin. An attacker or a broken client in a
      retry loop bypasses the cache entirely. `[PROVE]`
2.4.17 Penetration fix 1 — **negative caching with a distinct sentinel**, short TTL. Use a sentinel,
      not `null`, or you cannot distinguish "cached as absent" from "not cached". **This is the single
      most common implementation error in negative caching.** `[BUILD]` `[TRAP]`
2.4.18 Penetration fix 2 — **Bloom filter** in front ("definitely not present" vs "maybe present"),
      for when the space of invalid ids is unbounded. State the false-positive arithmetic:
      `m/n ≈ 10` bits per element gives ~1% FPR at `k ≈ 7`. `[NUM]` `[PROVE]` `[X-REF 01]`
2.4.19 The Bloom filter's fatal limitation for this use — **you cannot delete** — and the two answers:
      counting Bloom filters, or rebuild on a schedule. Redis's `BF.*` (RedisBloom, now core in the
      unified distribution) and Cuckoo filters as the productised forms. `[PROVE]` `[RESEARCH]`
2.4.20 Penetration fix 3 — **validate the key shape before you look it up.** A client id that is not
      a valid UUID cannot exist, and rejecting it at the edge costs nothing. The cheapest fix, and
      the one nobody mentions.
2.4.21 **Cache avalanche — mechanism.** Mass simultaneous expiry (the jitter problem) or a
      cache-cluster restart taking every key at once. Different cause from penetration, same symptom:
      sudden origin load. `[PROVE]`
2.4.22 Avalanche fixes: jitter, staggered warm-up, replica-based failover to a warm node, tiered
      caches so L1 absorbs the L2 restart, and origin rate limiting as the backstop. `[TABLE]`
2.4.23 **Hot key — mechanism.** One key receives a disproportionate share of traffic; in a sharded
      cache it lands on one shard, and in single-threaded Redis it saturates one core while the rest
      idle. `[PROVE]`
2.4.24 Hot-key detection: `HOTKEYS` (Redis 8.6), `redis-cli --hotkeys` (which requires an LFU policy),
      `MONITOR` sampling (and why it is dangerous on a busy instance), `cluster-slot-stats-enabled`
      per-slot statistics, and client-side per-key counters. `[CLI]` `[RESEARCH]` `[VERSION-TRAP]`
2.4.25 Hot-key mitigations, each with its cost: **local L1 shielding** (the best answer and the reason
      § 2.6 exists), **key splitting/replication** (`key:0`…`key:N` with a random read), read replicas,
      and client-side caching via tracking. `[TABLE]`
2.4.26 The QuizStakes hot key is `agreements:version:v1:current` — one key, read by every one of
      12k–40k daily registrations and every `AO-200` check. It is the canonical case for L1 shielding
      because it is tiny, hot, and rarely changes. `[NUM]`
2.4.27 **Big key — mechanism.** A single large value (a 5 MB JSON blob, a sorted set with 500k
      members) makes every read a large transfer, every `DEL` a long block, and every replication
      cycle lumpy. `DEL` on a multi-million-element collection can block Redis for hundreds of
      milliseconds. `[NUM]` `[PROVE]` `[RESEARCH]`
2.4.28 Big-key detection and fixes: `redis-cli --bigkeys` / `--memkeys`, `MEMORY USAGE`,
      `key-memory-histograms` (8.6), splitting by field or range, and **`UNLINK` instead of `DEL`** so
      the free happens on a background thread. `[CLI]` `[CFG]` `[RESEARCH]`
2.4.29 The QuizStakes big-key temptation: caching a whole `ProfileService` composite (PII + balances +
      compliance + transactions from two schemas) under one key. Large, per-role, invalidated by eight
      different events. Name it as the wrong answer and give the right one — cache the *parts*,
      compose on read. `[TRAP]` `[PROVE]`
2.4.30 **Cache breakdown / hot-key expiry (`缓存击穿`)** as a distinct named failure from avalanche:
      one *hot* key expiring, not many keys expiring. The mitigation set is § 2.4.4–2.4.12, not
      § 2.4.22, and mapping them correctly is the point. `[TRAP]` `[RESEARCH]`
2.4.31 **Cache-as-critical-dependency**: the failure mode where the cache is up but slow, which is
      worse than down because your timeouts are tuned for fast. Name the fix — a short cache timeout
      and a fall-through to origin. `[BUILD]` `[PROVE]`
2.4.32 **Failing open vs failing closed on a cache error**, and the rule: fail *open* (go to origin)
      for a read cache; fail *closed* for anything the cache was enforcing (a rate limiter). The
      QuizStakes contrast is § 15.5's "Cannot reach `ClientRestrictions`. Refuse the stake. Always."
      `[PROVE]` `[TABLE]`
2.4.33 The **failure-mode → symptom → metric → fix** master table, consolidated, so a reader can
      diagnose from a graph. `[TABLE]` `[METRIC]`

## §2.5 Consistency models for caches

2.5.1 The question to ask before choosing a model: **what is the maximum staleness this data may
      have, and who is harmed at the boundary?** Everything else follows.
2.5.2 **Strong consistency with a cache** is achievable only by making the cache part of the write
      path's atomicity domain — which, across a network, means consensus. State the price so the
      reader stops looking for a cheap version. `[PROVE]`
2.5.3 **Eventual consistency with a bounded staleness window** — the honest description of
      cache-aside, and the phrase to use in an interview.
2.5.4 **Read-your-writes** for a cached read path, and the three implementations: write-through to the
      tier you will read, sticky routing to the writing instance, and a version token the client
      carries. `[PROVE]` `[X-REF 22]`
2.5.5 **Monotonic reads** and the flapping failure when you do not have them: the user refreshes and
      sees old, new, old. `[PROVE]`
2.5.6 The current guide's flapping argument preserved and sharpened: ten pods with a five-minute local
      cache, one write, and nine pods serving the old value. The user hits a different pod on refresh,
      sees the old price, refreshes again and sees the new one, and files a bug titled "data randomly
      wrong". **This flapping is far more confusing than uniform staleness.** `[PROVE]`
2.5.7 **Session consistency** as the practical compromise, and how you get it cheaply (route a session
      to one instance — which is exactly `RouterInt`'s session-affinity strategy for
      `InternalPlatforms`). `[X-REF 22]`
2.5.8 **Causal consistency** for a cache: if the client saw `AA-801 ACTIVATED`, they must not
      subsequently see the pre-activation restriction set. § 15.2's exact case — "Client sees
      `ACTIVATED` but `ClientRestrictions` has not yet processed the lift, so their first deposit is
      refused." `[PROVE]`
2.5.9 The consistency-model table: model, what a client can observe, how you implement it with a
      cache, what it costs. `[TABLE]`
2.5.10 **Cache coherence protocols** as the thing you are *not* going to build: MSI/MESI as the CPU
      analogue, invalidation-based vs update-based, and the reason distributed caches use
      invalidation. One paragraph, then the practical consequence. `[PROVE]`
2.5.11 **Staleness composes across tiers** (§ 1.3.16), restated as a budget you can compute: browser
      60 s + CDN 300 s + Redis 600 s is a 960 s worst case for a user's view. Show the arithmetic.
      `[NUM]` `[PROVE]`
2.5.12 **Bounded staleness as a documented contract**, not an accident: the bible must show what
      writing it down looks like — a table of cached object, tier, TTL, invalidation trigger, worst-case
      staleness, and who signed off. `[TABLE]`
2.5.13 The QuizStakes consistency table, filled in: agreement text (minutes, push-invalidated),
      `PendingActions` (seconds), `ProfileService` composite (30–60 s, display only), restriction
      decision (**zero — not cached**), `CASH_AVAILABLE` (**zero — not cached**),
      `BalanceView` display (seconds, explicitly labelled as a preview). `[TABLE]`

## §2.6 Multi-level caching and the near-cache pattern

2.6.1 The structure: a small in-process L1 in front of a shared L2, with the origin behind both.
      `[FLOW]`
2.6.2 Why it works: L1 absorbs the extremely hot keys, eliminating both the network round trip and
      L2 CPU; L2 gives cross-instance sharing, survives deploys, and holds the long tail. Typical
      result: p50 near zero and an order-of-magnitude drop in L2 load. `[PROVE]` `[NUM]`
2.6.3 The cost: **two levels of staleness, and L1 is the hard one** — you cannot delete a key from
      another pod's heap.
2.6.4 The sizing rule: L1 small (hundreds to low thousands of entries — it is for hot keys, not
      coverage) and L1 TTL much shorter than L2 TTL. Give the reasoning for both, not just the rule.
      `[PROVE]` `[NUM]`
2.6.5 **Pub/sub invalidation** for L1: the writer publishes the key, every instance evicts its L1.
      `[BUILD]`
2.6.6 **The trap, preserved verbatim and expanded: Redis pub/sub is fire-and-forget.** No delivery
      guarantee, no persistence, no replay. A subscriber briefly disconnected — network blip, GC
      pause, rolling restart, still starting up — **misses the message forever** and keeps serving
      stale data indefinitely. No error, no retry, no way to detect it from the publisher. `[TRAP]`
      `[PROVE]`
2.6.7 The consequence, stated as a rule: **pub/sub invalidation is an optimisation, never a
      guarantee.** It must always be backed by a short L1 TTL that bounds the damage. Design the
      system to be correct with the TTL alone; treat pub/sub as the thing that usually makes it
      faster.
2.6.8 For reliable invalidation use Kafka (durable, replayable, offset-resumable) or Redis Streams
      with consumer groups — not pub/sub. And note what that costs: every pod needs its own consumer
      group, which is a group per pod, which is its own operational problem. `[X-REF 14]` `[PROVE]`
2.6.9 **Redis client-side caching (tracking)** as the native implementation of this pattern: the
      server remembers which keys each client read and pushes invalidation. Same caveat class,
      handled by the client library instead of your code. Mechanism in § 3.10. `[API]`
2.6.10 The near-cache rules, preserved: L1 TTL ≪ L2 TTL; L1 small; pub/sub best-effort; and **never
      L1-cache data where a 60-second stale window is unacceptable** — which, in QuizStakes, excludes
      every authorisation input by construction.
2.6.11 **Cache-through vs cache-around composition**: whether L1's loader is L2 or the application
      checks both. The first is tidier; the second lets you apply different serialisation and
      different failure policy per tier. `[TABLE]`
2.6.12 **Two-tier metrics must be per-tier.** A single "hit ratio" over a two-tier cache is
      meaningless; you need L1 hit ratio, L2 hit ratio, and end-to-end miss ratio, and the write pass
      must show how they compose. `[PROVE]` `[METRIC]`
2.6.13 **Negative results must be cached at only one tier**, or a fixed absence propagates twice.
      `[TRAP]`
2.6.14 When *not* to build a near cache: low key skew (L1 gets no hits and you have paid heap for
      nothing), tight consistency requirements, or an L2 that is already fast enough for the budget.
      `[PROVE]`

## §2.7 HTTP and CDN caching, in full

2.7.1 The framing: the browser and CDN tiers are caches too, they are free capacity, and the only
      interface to them is response headers. The cheapest request is the one that never reaches your
      infrastructure. `[X-REF 10]`
2.7.2 **RFC 9111's model**, stated precisely: a cache stores responses, computes **freshness
      lifetime** and **current age**, and serves while `age < lifetime`. Everything else is detail.
      `[SPEC]` `[PROVE]`
2.7.3 **Freshness lifetime precedence** (RFC 9111 § 4.2.1): `s-maxage` (shared caches) → `max-age` →
      `Expires − Date` → heuristic freshness. `[SPEC]` `[SOURCE]`
2.7.4 **Heuristic freshness** (§ 4.2.2) — what a cache does when you gave it no directives, typically
      10% of `Date − Last-Modified`, and why "I didn't set any cache headers so nothing is cached" is
      false. `[TRAP]` `[SPEC]`
2.7.5 **Age calculation** (§ 4.2.3) term by term: `age_value`, `date_value`, `request_time`,
      `response_time`, `apparent_age`, `corrected_age_value`, `corrected_initial_age`,
      `resident_time`, `current_age`. Show why a response can arrive already stale. `[SPEC]`
      `[PROVE]` `[NUM]`
2.7.6 **Response directives, all ten** (§ 5.2.2): `max-age`, `must-revalidate`, `must-understand`,
      `no-cache`, `no-store`, `no-transform`, `private`, `proxy-revalidate`, `public`, `s-maxage`.
      Each with what it actually does, not what its name suggests. `[TABLE]` `[SPEC]`
2.7.7 **Request directives, all seven** (§ 5.2.1): `max-age`, `max-stale`, `min-fresh`, `no-cache`,
      `no-store`, `no-transform`, `only-if-cached`. `[TABLE]` `[SPEC]`
2.7.8 **`no-cache` does not mean "do not cache".** It means "store it, but revalidate before every
      use". `no-store` is the one that means do not store. This is the single most common HTTP caching
      error. `[TRAP]` `[PROVE]`
2.7.9 **`private` vs `public` is a security control**, not a hint: a `public` response containing
      client data can be cached by a shared proxy or CDN and served to a different client.
      Authenticated responses are `private` or `no-store`. `[TRAP]` `[X-REF 13]`
2.7.10 **`must-revalidate`** and the stale-serving prohibition it creates, versus the default
      permission to serve stale under some conditions. `[SPEC]`
2.7.11 **Header fields defined by RFC 9111** (§ 5): `Age`, `Cache-Control`, `Expires`, `Pragma`
      (deprecated), `Warning` (deprecated and to be removed from implementations). `[SPEC]`
2.7.12 **`Vary`** — defined in RFC 9110 § 12.5.5, *not* 9111 — and the fact that it multiplies your
      cache entries by the cardinality of the varied headers. `[SPEC]` `[PROVE]`
2.7.13 `Vary: Accept-Encoding` correct; **`Vary: Cookie` destroys your hit ratio** because every
      client becomes a distinct entry; `Vary: *` means never reusable; a missing `Vary` on a
      content-negotiated response means a client gets the wrong representation. `[TRAP]` `[TABLE]`
2.7.14 **Validators and conditional requests** (RFC 9111 § 4.3, RFC 9110 § 8.8/13):
      `ETag` + `If-None-Match`, `Last-Modified` + `If-Modified-Since`, and `304 Not Modified` — still
      a round trip, no body transferred. `[SPEC]` `[WIRE]`
2.7.15 **Strong vs weak ETags** (`W/"…"`), what each permits (range requests need strong), and how to
      generate one that is cheap and correct — a content hash, a version column, or `updated_at` plus
      an id. `[PROVE]` `[BUILD]`
2.7.16 The ETag trap: generating the ETag *after* rendering means you did all the work to save the
      bytes. Generating it from a version column means you save the work too. `[PROVE]` `[TRAP]`
2.7.17 **`stale-while-revalidate` and `stale-if-error`** — RFC **5861**, not 9111. Serve stale for N
      seconds while revalidating in the background, and serve stale for N seconds when the origin
      errors. Worked example: `Cache-Control: public, max-age=600, stale-while-revalidate=30`.
      `[SPEC]` `[SOURCE]` `[NUM]`
2.7.18 **`immutable`** — RFC **8246**: the origin will not change this representation during its
      freshness lifetime, so clients should not revalidate even on reload. The fingerprinted-asset
      pattern. `[SPEC]`
2.7.19 **`Cache-Status`** — RFC **9211**: a structured-field list, one member per cache that handled
      the response, **first member closest to the origin, last closest to the user**, with
      `hit`/`fwd`/`fwd-status`/`ttl`/`stored`/`collapsed`/`key`/`detail` parameters. This is how you
      debug a CDN without guessing. `[SPEC]` `[WIRE]` `[DIAG]`
2.7.20 **`CDN-Cache-Control`** — RFC **9213**: targeted cache control, so you can tell the CDN
      something different from the browser without abusing `s-maxage`. The general form is
      `<target>-Cache-Control`. `[SPEC]`
2.7.21 **Vendor headers that predate the RFCs**: `Surrogate-Control` / `Surrogate-Key` (Fastly),
      `Cache-Tag` (Cloudflare), `x-amz-cf-pop` and CloudFront's behaviour set. Named as
      vendor-specific so the reader does not quote them as standards. `[CURRENCY]` `[X-REF 18]`
2.7.22 **Surrogate keys / cache tags** as the CDN's tag-based invalidation (§ 2.3.9), and why they are
      the only sane way to purge "every page mentioning this agreement version". `[PROVE]`
2.7.23 **Purge vs soft-purge vs versioned URL**: purge is a global invalidation with propagation delay
      and rate limits; soft-purge marks stale so `stale-while-revalidate` still shields the origin;
      **a versioned URL needs no purge at all**. Prefer the third. `[TABLE]` `[PROVE]`
2.7.24 **Fingerprinted immutable URLs** (`app.a1b2c3.js`, `max-age=31536000, immutable`) beat purging
      every time — change the key rather than invalidating it. `[PROVE]`
2.7.25 `max-age=31536000` is one year, which is the documented maximum a cache is required to
      respect; larger values are permitted but pointless. `[NUM]` `[SPEC]`
2.7.26 **Which methods and status codes are cacheable by default**: `GET` and `HEAD` yes; `POST` only
      with explicit freshness; `200`, `203`, `204`, `206`, `300`, `301`, `308`, `404`, `405`, `410`,
      `414`, `501` are heuristically cacheable. The `404` entry is the surprise, and it is HTTP's
      negative caching. `[TABLE]` `[SPEC]` `[RESEARCH]`
2.7.27 **Request collapsing at the CDN** as HTTP's single-flight, and the fact that it only works if
      the requests are keyed identically — which brings you back to `Vary`. `[PROVE]`
2.7.28 **Cache-key normalisation at the edge**: query-string ordering, ignored marketing parameters,
      cookie stripping, and device-class bucketing. Each is a deliberate hit-ratio decision.
2.7.29 **CDN tiering / shield origins**: a mid-tier PoP so 200 edge PoPs produce one origin request,
      not 200. `[PROVE]` `[NUM]`
2.7.30 **Web cache deception** as the security failure of this tier: `/api/profile/foo.css` served
      through a CDN configured to cache `.css` regardless of `Cache-Control` caches an authenticated
      response under a public key. Name it, show the mechanism, give the fix. `[TRAP]`
      `[X-REF 13]`
2.7.31 **Cache poisoning via unkeyed input** — a header that changes the response but is not in the
      cache key. The mirror image of § 1.7.1, at the HTTP tier. `[TRAP]` `[X-REF 13]`
2.7.32 Spring's server-side surface for all of this: `CacheControl` builder,
      `ResponseEntity.ok().cacheControl(...)`, `ShallowEtagHeaderFilter` (and why it saves bandwidth
      but not work), `WebContentInterceptor`, `ResourceHttpRequestHandler` +
      `VersionResourceResolver` / `ContentVersionStrategy`, and `WebRequest.checkNotModified(...)` for
      the version-column ETag. `[API]` `[BUILD]`
2.7.33 The QuizStakes HTTP-caching decisions, stated per endpoint: the agreement document
      (`public, max-age=3600, immutable` on a versioned URI); `GET /clients/{id}/pending-actions`
      (`private, no-cache` — a projection that must revalidate); `GET /clients/{id}/balance`
      (`no-store` — it is money and it authorises nothing, but it must never sit in a proxy);
      any restriction endpoint (`no-store`, and it should not be a `GET` a browser can cache at all).
      `[TABLE]` `[PROVE]`
2.7.34 `curl -I` and a read of the resulting headers, line by line, as the verification step nobody
      does. `[CLI]` `[DIAG]`

## §2.8 The Java in-process cache landscape

2.8.1 **`HashMap`/`ConcurrentHashMap` as a cache** — the starting point, and its three fatal defects:
      unbounded (an OOM waiting for a traffic spike), no expiry, no statistics. Name it as a cache so
      the reader recognises it in their own codebase. `[TRAP]` `[X-REF 06]`
2.8.2 **`LinkedHashMap` with `removeEldestEntry`** as the 15-line LRU everyone writes once, its
      `accessOrder` constructor argument, and its lack of thread safety. `[API]` `[X-REF 02]`
2.8.3 **`Collections.synchronizedMap` around it** and why that is a single global lock on every read
      — which is the concurrency problem every real cache library exists to solve. `[PROVE]`
2.8.4 **Guava `CacheBuilder`/`LoadingCache`** — the previous default: segmented locking,
      `maximumSize`, `expireAfterWrite`/`Access`, `refreshAfterWrite`, `weakKeys`/`softValues`,
      `CacheStats`, `RemovalListener`. Still shipped, still fine, strictly worse hit rate and
      throughput than Caffeine. `[API]`
2.8.5 **Guava's maintenance model** — work happens on calling threads, expiry is checked on access,
      and there is no background thread by default. This is why an unread Guava cache never expires
      anything. `[PROVE]` `[TRAP]`
2.8.6 **Caffeine** as the current answer, written by Guava's cache maintainer, API-compatible enough
      to be a near drop-in via `com.github.ben-manes.caffeine:guava`. `[CURRENCY]`
2.8.7 The Caffeine builder surface, every knob named: `maximumSize`, `maximumWeight` + `weigher`,
      `expireAfterWrite`, `expireAfterAccess`, `expireAfter(Expiry)`, `refreshAfterWrite`,
      `recordStats`, `removalListener`, `evictionListener`, `executor`, `scheduler`, `ticker`,
      `weakKeys`, `weakValues`, `softValues`, `initialCapacity`, `buildAsync`. `[API]` `[TABLE]`
2.8.8 `Caffeine.newBuilder().build()` vs `.build(loader)` vs `.buildAsync(loader)` — three different
      returned types (`Cache`, `LoadingCache`, `AsyncLoadingCache`) with three different guarantee
      sets. `[API]`
2.8.9 **`Scheduler.systemScheduler()`** as the thing that makes expiry prompt rather than
      access-triggered, and why you want it when a removal listener has side effects. `[API]`
      `[RESEARCH]`
2.8.10 **`Ticker`** as the reason Caffeine is testable: inject a fake clock instead of sleeping.
      `[API]` `[X-REF 16]`
2.8.11 **Caffeine's stated advantages over Guava**, with the mechanism for each: W-TinyLFU hit rate,
      ring-buffered reads instead of lock-per-read, `CompletableFuture`-native async, and a
      hierarchical timer wheel for variable expiry. Internals in § 3.1. `[PROVE]`
2.8.12 **Ehcache 3** — the multi-tier one: `heap` / `offheap` / `disk` / `clustered` tiers, sizing by
      entries or bytes, `ResourcePools`, `CacheManagerBuilder`, XML or programmatic config, and full
      JSR-107 compliance. When it is the right answer: you need off-heap or disk, or you need JCache.
      `[API]` `[CURRENCY]`
2.8.13 **JCache / JSR-107** — the standard API: `CachingProvider`, `CacheManager`, `Cache`,
      `Cache.Entry`, `ExpiryPolicy`, `CacheLoader`, `CacheWriter`, the four
      `CacheEntry*Listener` interfaces, `EntryProcessor` for atomic compound operations, and the
      annotations `@CacheResult`, `@CachePut`, `@CacheRemove`, `@CacheRemoveAll`. `[API]` `[SPEC]`
2.8.14 What JSR-107 does **not** standardise, which is why the abstraction leaks: eviction policy,
      sizing units, statistics beyond a minimum, and anything distributed. `[PROVE]`
2.8.15 Spring's JSR-107 support and the precedence rule when both Spring and JCache annotations are
      present. `[API]` `[X-REF 07]`
2.8.16 **Hazelcast / Infinispan / Apache Ignite** as the embedded-distributed category — a cache that
      is *also* a cluster member, with near-cache, partitioned entries and its own split-brain
      behaviour. Named with the one reason each exists, plus the honest warning that adopting one
      means adopting a distributed system into your JVM. `[TABLE]`
2.8.17 **`ConcurrentLinkedHashMap`, `cache2k`, `Expiring Map`** as the also-rans, so the reader
      recognises them in a dependency tree.
2.8.18 **`SoftReference`-based caches** and why they are a trap: the GC frees soft references only
      under pressure, all at once, which is an avalanche with extra steps, and `-XX:SoftRefLRUPolicyMSPerMB`
      is a knob nobody tunes correctly. `[TRAP]` `[CFG]` `[X-REF 06]`
2.8.19 The in-process cache comparison table: hit-rate policy, concurrency mechanism, tiers, expiry
      mechanics, async support, JSR-107, statistics, dependency weight, when to choose. `[TABLE]`
2.8.20 **In-process caching is safe for immutable or effectively-immutable data** — reference data,
      configuration loaded at startup, computed constants, parsed schemas. The rule preserved from the
      current guide, with the QuizStakes list: jurisdiction tables, restriction type definitions,
      status-code metadata, the agreement version *text* (immutable per version).
2.8.21 For mutable shared state, either use a distributed cache so all instances see one value, or
      accept the staleness **explicitly** — with a TTL short enough that the flapping window is
      tolerable, and documented. `[PROVE]`

## §2.9 The Spring Cache abstraction

2.9.1 What it is: a declarative façade over `Cache` and `CacheManager` with no cache of its own, so
      the abstraction's behaviour is the intersection of what providers offer. `[API]`
2.9.2 **`@EnableCaching`** and its attributes: `mode` (`PROXY` | `ASPECTJ`), `proxyTargetClass`,
      `order`. Each changes what gets intercepted. `[API]` `[CFG]`
2.9.3 **`@Cacheable`** and every attribute: `value`/`cacheNames`, `key`, `keyGenerator`,
      `cacheManager`, `cacheResolver`, `condition`, `unless`, `sync`. `[API]` `[TABLE]`
2.9.4 **`condition` vs `unless`** — the difference that trips everyone: `condition` is evaluated
      *before* invocation on the arguments; `unless` is evaluated *after*, and can see `#result`.
      `[PROVE]` `[TRAP]`
2.9.5 **`@CachePut`** — always invokes, always writes. The tool for a write path that wants the cache
      populated rather than evicted, and the reason § 1.5.2 says be careful.
2.9.6 **`@CacheEvict`** and its two extra attributes: `allEntries` and `beforeInvocation` (§ 2.3.21).
      `[API]`
2.9.7 **`@Caching`** for combining several operations on one method, and the ordering the interceptor
      applies. `[API]`
2.9.8 **`@CacheConfig`** at class level for shared `cacheNames`, `keyGenerator`, `cacheManager`,
      `cacheResolver`. `[API]`
2.9.9 **SpEL key expressions** — the available root object and its properties: `#root.method`,
      `#root.target`, `#root.caches`, `#root.methodName`, `#root.targetClass`, `#root.args`,
      argument names (`#clientId`), `#result` (in `unless` and `@CachePut`), and `#p0`/`#a0`
      positional forms. `[API]` `[TABLE]`
2.9.10 **Argument names require `-parameters`** at compile time or you are stuck with `#p0`. A real
      build-configuration gotcha. `[TRAP]` `[CFG]`
2.9.11 **`SimpleKeyGenerator` and `SimpleKey`** — the default: no args → `SimpleKey.EMPTY`; one arg →
      that arg itself; several → a `SimpleKey` wrapping them. `[PROVE]` `[API]`
2.9.12 **The default key generator's silent hazards**: the key is only as good as the arguments'
      `equals`/`hashCode`, an argument that is not part of the result's identity still changes the
      key, and **an argument the result depends on but that is not a parameter (the current
      principal, the tenant, the locale) is invisible to it.** This is § 1.7.1's failure, delivered by
      a default. `[TRAP]` `[PROVE]` `[X-REF 03]`
2.9.13 A custom `KeyGenerator` vs an explicit `key` SpEL expression, and why the explicit expression
      is usually better: it is local, reviewable, and cannot be silently reused by another method.
      `[PROVE]`
2.9.14 **`CacheManager` implementations**: `ConcurrentMapCacheManager`, `SimpleCacheManager`,
      `CaffeineCacheManager`, `RedisCacheManager`, `JCacheCacheManager`, `EhCacheCacheManager`,
      `CompositeCacheManager`, `TransactionAwareCacheManagerProxy`, `NoOpCacheManager`. `[API]`
      `[TABLE]`
2.9.15 **`TransactionAwareCacheManagerProxy`** — defers cache writes to after commit, which is
      § 1.5.11 as a bean rather than as discipline. `[API]` `[PROVE]`
2.9.16 **`CompositeCacheManager`** for a genuine two-tier setup, and `NoOpCacheManager` for switching
      caching off in a test or an incident. `[API]` `[X-REF 16]`
2.9.17 **`CacheResolver`** for choosing the cache at runtime (per tenant, per environment). `[API]`
2.9.18 **`CacheErrorHandler`** and the default: **`SimpleCacheErrorHandler` rethrows.** A Redis
      timeout therefore fails the request rather than falling through to the origin, which is the
      opposite of § 2.4.32's rule for a read cache. Overriding this is one of the highest-value
      configuration changes in a Spring caching setup, and almost nobody does it. `[TRAP]` `[API]`
      `[PROVE]`
2.9.19 **`@Cacheable(sync = true)`** — what it actually promises: a single loader per key **within one
      JVM**, implemented via `Cache#get(key, Callable)`, and only on providers that implement it. Not
      supported with `unless`, and not supported for multiple caches on one operation. It is not a
      distributed lock. `[TRAP]` `[PROVE]` `[VERSION-TRAP]`
2.9.20 **The self-invocation trap**, restated for caching specifically: a call from one method to
      another on the same bean does not pass through the proxy, so `@Cacheable` does nothing and
      there is no warning. The three fixes (extract the method to another bean, self-inject,
      `AopContext.currentProxy()`) with their costs. `[TRAP]` `[X-REF 07]`
2.9.21 **Only `public` methods are advised** under proxy mode, and `final` classes/methods cannot be
      CGLIB-proxied. Both are silent failures. `[TRAP]` `[X-REF 07]`
2.9.22 **Proxy ordering with `@Transactional`** — if the caching advice runs outside the transaction
      advice, a cached value can be served from a transaction that later rolls back, and an eviction
      can happen before commit. Say which order you get by default and how to change it. `[PROVE]`
      `[X-REF 07]`
2.9.23 **`spring.cache.type`** and the auto-detection order Boot uses when it is absent
      (`generic`, `jcache`, `ehcache`, `hazelcast`, `infinispan`, `couchbase`, `redis`, `caffeine`,
      `cache2k`, `simple`, `none`). `[CFG]` `[RESEARCH]`
2.9.24 **`spring.cache.cache-names`** and `spring.cache.caffeine.spec` / `spring.cache.redis.*`
      (`time-to-live`, `key-prefix`, `use-key-prefix`, `cache-null-values`, `enable-statistics`).
      `[CFG]` `[TABLE]`
2.9.25 **`CacheManagerCustomizer`** as the supported way to tune an auto-configured manager, and its
      package move in Boot 4.x. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
2.9.26 **`RedisCacheManager` / `RedisCacheConfiguration`** in detail: `entryTtl(Duration)`
      (`Duration.ZERO` means eternal), `computePrefixWith(CacheKeyPrefix)`, `prefixCacheNameWith`,
      `disableCachingNullValues()` (and its exact behaviour — the `put` errors, nothing is written,
      an existing key is left untouched), `disableKeyPrefix()`, `serializeKeysWith` /
      `serializeValuesWith`, `enableTimeToIdle()`, and `enableStatistics()` on the builder plus
      `RedisCache#getStatistics()`. `[API]` `[TABLE]` `[RESEARCH]`
2.9.27 **`CacheKeyPrefix`** as a functional interface, and its default — `cacheName` followed by a
      double colon — which is why your Redis keyspace is full of `agreements::current`. `[API]`
2.9.28 **`RedisCacheWriter`** and the lock-based `lockingRedisCacheWriter` variant used for
      `clear()`, plus what that lock does and does not protect. `[API]` `[RESEARCH]`
2.9.29 What the abstraction **cannot express**, and therefore when to drop to the native client:
      per-entry TTL from the value, refresh-ahead, cross-instance single-flight, tag invalidation,
      two-tier composition with different TTLs, and anything needing a pipeline. `[TABLE]` `[PROVE]`
2.9.30 The QuizStakes wiring, written out: a `CaffeineCacheManager` for `agreementVersions` (L1,
      60 s, 200 entries, `recordStats`), a `RedisCacheManager` for `profileComposite` and
      `pendingActions` (L2, 60 s / 10 s, JSON, `disableCachingNullValues` off because negative
      caching is deliberate), a `CacheErrorHandler` that logs and falls through, and **no cache bean
      anywhere near `ClientRestrictions`**. `[BUILD]`
2.9.31 **Testing the abstraction**: `@AutoConfigureCache`, asserting on `CacheManager` contents rather
      than on timing, and the fact that a cache makes a test order-dependent unless you clear it.
      `[API]` `[X-REF 16]`

## §2.10 Hibernate caching — L1, L2 and the query cache

2.10.1 **First-level cache (the persistence context)** is not optional and is not configurable: it is
      the `Session`/`EntityManager`'s identity map, scoped to the transaction. Calling it "a cache"
      confuses people about its purpose, which is identity and dirty tracking. `[PROVE]`
      `[X-REF 08]`
2.10.2 L1's consequences you must know: `find` twice returns the same instance without a query;
      `flush` ordering; and the fact that a `Query` bypasses L1 for the *lookup* but populates it with
      the results. `[TRAP]`
2.10.3 **Second-level cache (L2)** — `SessionFactory`-scoped, shared across sessions and optionally
      across nodes, keyed by entity type and identifier, storing **dehydrated state, not object
      graphs**. `[PROVE]`
2.10.4 Enabling it, with the exact property names: `hibernate.cache.use_second_level_cache`,
      `hibernate.cache.region.factory_class`, `jakarta.persistence.sharedCache.mode`
      (`ALL` | `NONE` | `ENABLE_SELECTIVE` | `DISABLE_SELECTIVE` | `UNSPECIFIED`),
      `@Cacheable` (the JPA one), `@Cache(usage = …, region = …)` (the Hibernate one). `[CFG]`
      `[API]`
2.10.5 **`CacheConcurrencyStrategy`**, all four, with what each guarantees: `READ_ONLY` (immutable,
      fastest, safest — modification throws), `NONSTRICT_READ_WRITE` (no locks, invalidates after
      commit, tolerates a stale window), `READ_WRITE` (soft locks giving strong consistency),
      `TRANSACTIONAL` (XA-synchronised, needs a transactional provider). `[TABLE]` `[PROVE]`
      `[RESEARCH]`
2.10.6 **`READ_WRITE`'s soft lock**, in mechanism: on update the entry is replaced by a lock marker
      until commit, and concurrent readers miss and go to the database rather than reading stale.
      Explain why that is a *correct* design and not a bug. `[PROVE]` `[SOURCE]`
2.10.7 The practical rule: `READ_ONLY` for reference tables the application never updates,
      `READ_WRITE` for everything else worth caching, `NONSTRICT_READ_WRITE` only when you can name
      the tolerable staleness, `TRANSACTIONAL` almost never. `[RESEARCH]`
2.10.8 **Collection caching** is separate from entity caching and needs its own `@Cache` on the
      association — and it caches *identifiers*, so a collection hit still needs the entities cached
      to avoid N queries. This is the most-missed detail in Hibernate caching. `[TRAP]` `[PROVE]`
2.10.9 **Natural-id caching** (`@NaturalId`, `@NaturalIdCache`) as the way to cache a lookup by
      business key rather than surrogate id — which is what `AccountOpening`'s uniqueness check at
      `AO-099` actually does. `[API]`
2.10.10 **Query cache** — `hibernate.cache.use_query_cache`, `@QueryHints(@QueryHint(name = "org.hibernate.cacheable"))`,
      `setCacheable(true)`, `setCacheRegion(...)`, and the fact that it caches **identifier lists**,
      not rows. `[CFG]` `[API]` `[PROVE]`
2.10.11 Why the query cache is usually a net loss, argued rather than asserted: it is invalidated by
      **any** write to any table it touches (via the update-timestamps region), and its results still
      require the entities to be in L2 or you get an id list plus N selects. `[PROVE]` `[TRAP]`
2.10.12 The **update-timestamps region** and `hibernate.cache.use_minimal_puts`, so the invalidation
      mechanism is named rather than magic. `[CFG]` `[RESEARCH]`
2.10.13 **`CacheMode`** / `jakarta.persistence.cache.retrieveMode` / `storeMode`
      (`USE`/`BYPASS`/`REFRESH`) for per-operation control — the tool for a batch job that must not
      pollute L2. `[API]` `[PROVE]`
2.10.14 **L2 is invalidated by Hibernate's own writes only.** A native query, a JDBC statement, a
      migration, or another service writing the same table leaves L2 stale with no signal. This is
      the single strongest argument against Hibernate L2 in a microservice estate — and QuizStakes
      has 22 services. `[TRAP]` `[PROVE]`
2.10.15 Statistics: `hibernate.generate_statistics`, `SessionFactory#getStatistics()`,
      `getSecondLevelCacheHitCount`/`MissCount`/`PutCount`, per-region statistics, and the Micrometer
      binding. `[METRIC]` `[X-REF 20]`
2.10.16 **When Hibernate L2 is the right answer**: a monolith or single-writer service, small
      slow-changing reference tables, `READ_ONLY`. When it is not: anything multi-writer, anything
      write-heavy, or as a substitute for fixing a query plan. `[TABLE]`
2.10.17 The QuizStakes judgement: `ClientAgreements`' agreement-version rows are the one legitimate
      `READ_ONLY` L2 candidate in the estate; nothing in `FundsLedger` is, and the bible must say why
      in one sentence tied to invariant 1. `[PROVE]`

## §2.11 Redis as a cache — the operational surface

2.11.1 The one-sentence model: Redis is an in-memory data-structure server whose **command execution
      is single-threaded**, which is why every command is atomic and why one slow command stalls
      everybody. `[PROVE]`
2.11.2 The data types and when each is the right *cache* shape, not just what it can hold: **String**
      (a serialised object, a counter, a lock token), **Hash** (an object whose fields are updated
      independently — session state, without re-serialising the whole thing), **List** (a capped
      recent-activity feed with `LTRIM`), **Set** (membership, tag indexes, "have I seen this id"),
      **Sorted set** (leaderboards, sliding-window rate limiters with score = timestamp, delayed-job
      indexes), **Bitmap** (daily-active flags at ~1 bit/user), **HyperLogLog** (approximate
      cardinality in 12 KB regardless of count, ~0.81% standard error), **Stream** (an append-only
      log with consumer groups), **Geo** (ZSET underneath), **JSON**, **Bloom/Cuckoo/Count-Min/Top-K**
      (RedisBloom, core since the 8.0 unified distribution), **Vector set**. `[TABLE]` `[NUM]`
      `[CURRENCY]`
2.11.3 The QuizStakes mapping for each type that earns its place: Hash for the `ProfileService`
      composite parts; Sorted set for the identity vendor's 600/min sliding-window limiter; Bitmap
      for "which clients have an outstanding requirement"; String for the agreement text; Bloom for
      "is this client id even real" at the penetration boundary. `[TABLE]`
2.11.4 **TTL is per key** (`EXPIRE`, `PEXPIRE`, `EXPIREAT`, `SETEX`, `SET … EX/PX/EXAT/PXAT`,
      `GETEX`, `PERSIST`, `TTL`, `PTTL`), and `EXPIRE`'s `NX`/`XX`/`GT`/`LT` conditions (7.0+) with
      the rule that a non-volatile key is treated as an infinite TTL for `GT`/`LT`. `[CFG]` `[API]`
      `[SOURCE]`
2.11.5 **Hash-field TTLs exist since 7.4**: `HEXPIRE`, `HPEXPIRE`, `HEXPIREAT`, `HPEXPIREAT`, `HTTL`,
      `HPTTL`, `HPERSIST`, `HGETEX`, `HGETDEL`. The "you can't expire a hash field" answer is now
      wrong, and the bible must lead with the capability and then say what it cost to add.
      `[VERSION-TRAP]` `[RESEARCH]`
2.11.6 **`SET` clears a TTL; `INCR`/`HSET`/`LPUSH` do not.** The rule is that operations replacing the
      value reset the expiry and operations mutating it in place leave it. `KEEPTTL` exists precisely
      because this bites. `[TRAP]` `[SOURCE]`
2.11.7 **`maxmemory` and `maxmemory-policy`** — all ten policies as of 8.6: `noeviction`,
      `allkeys-lru`, `allkeys-lfu`, `allkeys-lrm`, `allkeys-random`, `volatile-lru`, `volatile-lfu`,
      `volatile-lrm`, `volatile-random`, `volatile-ttl`. `[CFG]` `[TABLE]` `[RESEARCH]`
      `[VERSION-TRAP]`
2.11.8 **`noeviction` is the default, and it makes writes fail with an OOM error** when the limit is
      reached while reads keep working. Surprising, and the first thing to change on a cache
      instance. `[TRAP]` `[CFG]`
2.11.9 **The `volatile-*` trap, preserved**: with a `volatile-*` policy and some keys lacking a TTL,
      once only non-TTL keys remain Redis has nothing eligible and behaves like `noeviction` — writes
      start failing. For a pure cache, use `allkeys-lru` and stop thinking about it. `[TRAP]`
      `[SOURCE]`
2.11.10 **`maxmemory-samples`** (default 5, 10 is near-true-LRU at a small CPU cost) and the fact that
      Redis's LRU is *approximated by sampling plus a candidate pool since 3.0*. `[CFG]` `[NUM]`
      `[SOURCE]`
2.11.11 **LFU tuning**: `lfu-log-factor` (default 10) and `lfu-decay-time` (default 1 minute, `0`
      never decays), the 8-bit Morris counter saturating around one million requests, and the
      factor→hits table (factor 0: 104 at 100 hits; factor 10: 10 at 100 hits, 142 at 100K; factor
      100: 49 at 100K, 143 at 1M). `[CFG]` `[NUM]` `[SOURCE]`
2.11.12 **`allkeys-lrm`** (8.6) — timestamp updated on **write only**, so read-hot but never-modified
      data survives. State the workload it is for: read-heavy with a clear read/write distinction.
      `[RESEARCH]` `[VERSION-TRAP]`
2.11.13 **`mem_not_counted_for_evict`** and the replication/persistence buffer that is excluded from
      the `maxmemory` comparison — and therefore the reason to leave headroom. `[NUM]` `[SOURCE]`
2.11.14 **Setting `maxmemory` correctly**: leave room for the replication backlog, the AOF buffer, the
      client output buffers and the fork's copy-on-write pages. The common failure is `maxmemory` set
      equal to the container limit, which gets you OOM-killed rather than evicted. `[PROVE]`
      `[X-REF 19]`
2.11.15 **`INFO` sections that matter**, read field by field: `memory` (`used_memory`,
      `used_memory_rss`, `used_memory_dataset`, `mem_fragmentation_ratio`, `maxmemory_policy`),
      `stats` (`keyspace_hits`, `keyspace_misses`, `evicted_keys`, `expired_keys`,
      `current_eviction_exceeded_time`, `total_net_input_bytes`), `clients`
      (`blocked_clients`, `client_output_buffer_limit` violations), `replication`, `persistence`,
      `commandstats`, `latencystats`. `[CLI]` `[DIAG]` `[METRIC]`
2.11.16 The hit-ratio formula from the docs, exactly: `keyspace_hits / (keyspace_hits +
      keyspace_misses) × 100`, plus the caveat that an `EXISTS` on an absent key counts as a miss.
      `[NUM]` `[SOURCE]`
2.11.17 The diagnostic decision tree the docs actually give: low hit ratio + high `evicted_keys` →
      wrong policy or too small; low hit ratio + low `evicted_keys` + high `expired_keys` → TTL too
      short. Reproduce it as a decision procedure. `[FLOW]` `[SOURCE]`
2.11.18 **`SCAN` not `KEYS`.** `KEYS` is O(n) and blocks the single command thread, stalling every
      client on the instance; `SCAN` is cursor-based with `MATCH`, `COUNT` and `TYPE`, and gives
      guarantees only about elements present throughout the iteration. `[TRAP]` `[CLI]` `[PROVE]`
2.11.19 **`UNLINK` not `DEL`** for large values, and `lazyfree-lazy-eviction` /
      `lazyfree-lazy-expire` / `lazyfree-lazy-server-del` / `lazyfree-lazy-user-del` /
      `lazyfree-lazy-user-flush` as the config equivalents. `[CFG]` `[RESEARCH]`
2.11.20 **`FLUSHALL`/`FLUSHDB` in production** — the `ASYNC`/`SYNC` argument, and the fact that this
      is the command that manufactures § 1.1.11's cliff on demand. `[CLI]` `[TRAP]`
2.11.21 **Pipelining** — batch N commands into one RTT; the arithmetic (50 keys sequentially at
      0.5 ms = 25 ms; pipelined = ~0.6 ms) and the memory cost of the reply buffer. `[NUM]`
      `[PROVE]`
2.11.22 **`MGET`/`MSET` vs pipelining vs Lua** — three ways to batch with three different atomicity
      properties. `[TABLE]` `[PROVE]`
2.11.23 **`MULTI`/`EXEC`/`DISCARD`/`WATCH`** — what Redis transactions actually are (queued commands
      executed without interleaving, no rollback), and `WATCH` as optimistic concurrency. Say plainly
      that this is not a database transaction. `[PROVE]` `[TRAP]`
2.11.24 **Lua scripting** — `EVAL`/`EVALSHA`/`SCRIPT LOAD`, atomicity, the requirement to declare
      keys, the cluster single-slot restriction, and the fact that a slow script blocks everything.
      Functions (`FUNCTION LOAD`, 7.0+) as the successor. `[API]` `[TRAP]`
2.11.25 **`SETNX`/`SET … NX PX` as a lock**, and the correctness argument: the token, the Lua release,
      the TTL, and the reason the TTL is both necessary and unsafe. `[PROVE]` `[BUILD]`
2.11.26 **Redlock and its critique**, both sides, fairly: the algorithm (N independent masters,
      majority acquisition, elapsed-time validity check); Kleppmann's objections (no fencing token,
      and the assumption of bounded network delay, bounded process pauses and bounded clock error);
      antirez's reply (the elapsed-time check covers acquisition delay; Redlock targets efficiency,
      not correctness). The conclusion the bible must reach: **for correctness use a fencing token
      against a resource that can reject stale writers; for avoiding duplicate work, a single Redis
      lock is fine.** `[PROVE]` `[SOURCE]` `[X-REF 14]`
2.11.27 The QuizStakes application of that conclusion: the single-flight lock on the agreement cache
      is an *efficiency* lock and a plain `SET NX PX` is correct; the "only one `PaymentRun` open at a
      time" requirement (invariant 14) is a *correctness* lock and must not rest on Redis alone.
      `[PROVE]`
2.11.28 **Persistence and what it means for a cache**: `RDB` (fork-and-dump on a `save` schedule — a
      crash loses everything since the last snapshot, potentially minutes), `AOF` with
      `appendfsync` `always`/`everysec`/`no` (`everysec` loses up to a second), `aof-use-rdb-preamble`,
      and the fact that managed Redis frequently ships with persistence off. `[CFG]` `[NUM]`
2.11.29 **Never treat Redis as a system of record.** Replication is asynchronous, so a failover can
      lose recent writes even with persistence on — which is exactly why Redlock-style locking is
      contested. `[PROVE]`
2.11.30 **For a pure cache, turning persistence off is often correct**, and the bible must say so
      explicitly: no fork, no COW spike, no `fsync` latency, and nothing lost that matters. State the
      one exception — you wanted a warm restart. `[PROVE]`
2.11.31 **Replication for a cache**: read replicas for hot-key read scaling, `replica-read-only`,
      `WAIT`, and the staleness a replica read introduces (which is a *second* staleness window on
      top of the cache's own). `[CFG]` `[PROVE]`
2.11.32 **Sentinel** vs **Cluster** vs **managed failover**, and what each does to an in-flight
      client: the failover window, the client's topology refresh, and the burst of misses that
      follows. `[TABLE]`
2.11.33 **Redis Cluster**: 16,384 hash slots, `CRC16(key) mod 16384`, slot ownership per node,
      `MOVED` (permanent, update your map) vs `ASK` (one-shot, do not update), and resharding by
      moving slots. `[NUM]` `[WIRE]` `[SOURCE]`
2.11.34 Why 16,384 and not 65,536 — the cluster bus bitmap size (2 KB vs 8 KB per heartbeat). A
      genuinely satisfying "why is this constant that number" answer. `[NUM]` `[PROVE]`
      `[RESEARCH]`
2.11.35 **`CROSSSLOT` errors and hash tags**: multi-key operations must be in one slot; `{clientId}`
      braces force co-location. The consequence for cache design — you must decide co-location at
      key-design time. `[WIRE]` `[PROVE]`
2.11.36 What Cluster **breaks** for a cache: `MGET` across slots, Lua across slots, `SCAN` needing
      per-node iteration, `FLUSHALL` per node, and pub/sub semantics (`SPUBLISH`/`SSUBSCRIBE` as the
      sharded alternative). `[TABLE]` `[TRAP]`
2.11.37 **Keyspace notifications** — `notify-keyspace-events` flag characters (`K`, `E`, `g`, `$`,
      `l`, `s`, `h`, `z`, `x`, `e`, `t`, `n`, `m`, `d`, `A`), the `__keyspace@0__:` and
      `__keyevent@0__:` channels, and the `expired`/`evicted` events. The honest caveat: they ride
      pub/sub, so § 2.6.6 applies in full and you cannot build a guarantee on them. `[CFG]`
      `[TRAP]` `[WIRE]`
2.11.38 The `expired` event's timing: it fires when the key is actually removed (lazily or by the
      active cycle), **not when it logically expired**, so it is not a timer. `[TRAP]` `[PROVE]`
2.11.39 **Latency diagnostics**: `SLOWLOG GET`, `slowlog-log-slower-than`, `LATENCY DOCTOR`,
      `LATENCY HISTORY`, `LATENCY RESET`, `latency-monitor-threshold`, `redis-cli --latency` /
      `--latency-history` / `--latency-dist`, `--intrinsic-latency`. `[CLI]` `[CFG]` `[DIAG]`
2.11.40 **The latency traps, enumerated**: `KEYS`/`SMEMBERS`/`HGETALL` on big collections, big-key
      `DEL`, fork for RDB/AOF-rewrite, `appendfsync always`, THP, swap, `maxmemory` thrash,
      `CONFIG SET` on a large keyspace, a slow Lua script, an over-large pipeline, and cross-AZ
      round trips. `[TABLE]` `[X-REF 11]`
2.11.41 **Client output buffer limits** (`client-output-buffer-limit normal/replica/pubsub`) and the
      failure they cause: a slow consumer of a large `SCAN`/pub/sub stream gets disconnected, or the
      replica link resets. `[CFG]` `[TRAP]` `[RESEARCH]`
2.11.42 **Connection and pool sizing** for Lettuce (one shared multiplexed connection, thread-safe,
      pooling usually unnecessary except for blocking or transactional use) vs Jedis (connection per
      thread, `JedisPool` with `maxTotal`/`maxIdle`/`minIdle`/`maxWait`). Getting this backwards is a
      standard production mistake. `[PROVE]` `[TRAP]` `[X-REF 05]`
2.11.43 **Timeouts** — command timeout, connect timeout, socket timeout, and the rule that a cache
      timeout must be much shorter than the origin timeout or the cache adds latency on failure
      instead of removing it. `[PROVE]` `[NUM]`
2.11.44 **Redisson** as the higher-level option: `RMap`, `RMapCache` (per-entry TTL over a hash),
      `RLocalCachedMap` (near cache with invalidation), `RLock`/`RedissonRedLock`/`RFencedLock`,
      `RRateLimiter`, and a Spring Cache manager. What it buys and what it hides. `[API]`
      `[CURRENCY]`
2.11.45 **Spring Data Redis** surface: `RedisTemplate` / `StringRedisTemplate`,
      `ValueOperations`/`HashOperations`/`ZSetOperations`, `executePipelined`,
      `RedisConnectionFactory` (Lettuce vs Jedis), `ReactiveRedisTemplate`. `[API]`
2.11.46 **Valkey as the drop-in**: protocol- and command-compatible with Redis 7.2.4 plus divergence
      since; the licence difference (BSD-3 vs AGPLv3); the performance claims; and the practical
      question a candidate should ask — which one is my managed service actually running?
      `[CURRENCY]` `[VERSION-TRAP]` `[RESEARCH]`
2.11.47 **The Redis licence timeline** as an engineering fact, not trivia: BSD until March 2024 →
      SSPLv1/RSALv2 → AGPLv3 added May 2025; Valkey forked from 7.2.4 under the Linux Foundation.
      It changed which engine your cloud provider defaults to. `[CURRENCY]` `[RESEARCH]`
2.11.48 **Managed-service semantics that differ from self-hosted**, named so the reader checks:
      persistence defaults, `CONFIG SET` restrictions, disabled commands, reserved memory percentage,
      failover behaviour, and serverless pricing minimums. `[X-REF 18]` `[CURRENCY]`
2.11.49 **`HOTKEYS`** (8.6) and `cluster-slot-stats-enabled` as the first-party hot-key and hot-slot
      tools. `[CLI]` `[CFG]` `[RESEARCH]` `[VERSION-TRAP]`
2.11.50 **`key-memory-histograms`** and the `db0_distrib_*_sizes` metrics (8.6) as the first-party
      big-key detector. `[CFG]` `[METRIC]` `[RESEARCH]`

## §2.12 Memcached, and why it still exists

2.12.1 The one-paragraph positioning: simpler, **multi-threaded**, strings only, no persistence, no
      replication, no scripting — and genuinely faster and more memory-predictable for pure
      key→blob caching at scale. `[PROVE]`
2.12.2 The protocol surface: `get`, `gets`, `set`, `add`, `replace`, `append`, `prepend`, `cas`,
      `incr`/`decr`, `delete`, `touch`, `gat`, `flush_all`, `stats`, and the binary/meta protocols.
      `[WIRE]` `[TABLE]`
2.12.3 **`cas` (check-and-set)** as memcached's optimistic concurrency, and the one thing it gives you
      that a naive `set` does not. `[PROVE]`
2.12.4 **No server-side clustering** — sharding is entirely client-side by consistent hashing, which
      is why memcached scaling discussions are really client-library discussions. `[PROVE]`
2.12.5 **Item size limit** (default 1 MB, `-I` to raise) and why raising it is usually the wrong fix.
      `[CFG]` `[NUM]`
2.12.6 **`extstore`** — flash-backed values with keys and metadata in RAM, for large cold datasets.
      `[CURRENCY]` `[RESEARCH]`
2.12.7 **The Redis-vs-memcached decision table**: data structures, atomic operations, persistence,
      replication, clustering, threading model, memory efficiency for small values, memory
      predictability, operational surface, and the honest verdict — Redis unless you have a specific
      reason. `[TABLE]`
2.12.8 The one specific reason: extremely high throughput on a fixed small-object workload where the
      multi-threaded model and slab predictability matter more than any feature. `[PROVE]`
2.12.9 Java clients: `spymemcached`, `XMemcached`, AWS's `ElastiCacheClusterClient` with auto
      discovery, and the absence of a Spring Boot auto-configuration (so a `CacheManager` is
      hand-rolled or via JCache). `[API]` `[CURRENCY]`

## §2.13 Distributed cache topology, sharding and consistent hashing

2.13.1 The three topologies: **client-side sharded** (memcached), **server-side sharded with
      redirection** (Redis Cluster), and **proxy-fronted** (twemproxy, Envoy, managed endpoints).
      `[TABLE]`
2.13.2 **Why `hash(key) mod N` is disqualified**: changing N remaps almost every key, so a scale-out
      is a full cache flush and therefore § 1.1.11's cliff. Prove the remap fraction. `[PROVE]`
      `[NUM]`
2.13.3 **Consistent hashing** — the ring, virtual nodes, and the property that adding one node of N
      remaps only ~1/N of keys. One paragraph of mechanism, the arithmetic, then point away for the
      general treatment. `[PROVE]` `[NUM]` `[X-REF 22]`
2.13.4 **Virtual nodes / replicas per node** as the fix for ring imbalance, with the standard figure
      (100–200 vnodes per physical node) and what happens without them. `[NUM]` `[RESEARCH]`
2.13.5 **Rendezvous (HRW) hashing** and **jump consistent hash** as the two better-behaved
      alternatives, named with their one advantage each. `[RESEARCH]`
2.13.6 **Redis Cluster's fixed 16,384 slots** as a deliberately different design: slots are
      re-assigned rather than re-hashed, so a resharding moves data without changing the key→slot
      function. Explain why that is easier to operate. `[PROVE]`
2.13.7 The QuizStakes tie-in that must not be overclaimed: `RouterInt`'s **partition affinity by
      client id** for `FundsLedger` "buys *nothing for correctness*" (§ 6.4) — it is a state-locality
      optimisation, and the rebalancing problem when 3 instances become 4 is its cost. The bible must
      reproduce that honesty rather than presenting consistent hashing as inevitable. `[SOURCE]`
      `[PROVE]`
2.13.8 **Replication vs sharding for a cache**: sharding buys capacity, replication buys read
      throughput and hot-key relief. They solve different problems and people ask for the wrong one.
      `[PROVE]` `[TABLE]`
2.13.9 **Multi-region caching**: local cache per region with regional origins, and the reason
      cross-region cache invalidation is usually the wrong design (the propagation delay exceeds the
      TTL you would have chosen). `[PROVE]` `[X-REF 22]`
2.13.10 **Cache instance sizing vs count**: fewer larger instances have better hit ratios (one pool,
      no duplication) and worse blast radius. State the trade with numbers. `[PROVE]` `[NUM]`
2.13.11 **Multi-tenancy on a shared cache**: key prefixing, `SELECT`-based database numbers (and why
      not to), ACL-scoped users, per-tenant memory accounting, and the noisy-neighbour failure.
      `[TABLE]` `[X-REF 13]`

## §2.14 Sizing and capacity arithmetic

2.14.1 The procedure, ordered: identify the cacheable objects → measure one serialised object →
      estimate cardinality → decide the working-set fraction to hold → add key bytes and per-entry
      overhead → add headroom for buffers and fragmentation → pick an instance. `[FLOW]`
2.14.2 **Measuring one object properly**: `MEMORY USAGE key` for Redis, `ObjectSizeCalculator`/JOL
      for the heap, and why `sizeof` intuition is wrong by 2–5× in both directions. `[CLI]`
      `[X-REF 06]`
2.14.3 **Per-entry overhead is not negligible.** State it for each: a Redis key with a TTL, a
      Caffeine entry with its policy fields, a `ConcurrentHashMap.Node`. `[NUM]` `[PROVE]`
2.14.4 **The `ProfileService` composite worked end to end**: 2.4M clients × ~2 KB PII + balances +
      compliance ≈ the arithmetic that tells you caching all of it is 5+ GB and caching the active
      380k is under 1 GB. Show both and pick. `[NUM]` `[PROVE]`
2.14.5 **The agreement cache worked**: ~180 versions × 40–900 KB ≈ 7–160 MB for *every* version, and
      one current version is under 1 MB. This is the case where you cache everything without
      thinking, and the arithmetic is why. `[NUM]`
2.14.6 **The `PendingActions` projection worked**: 380k monthly-active clients × a small banner list,
      with 38k restriction changes/day driving invalidations. Compute both the footprint and the
      invalidation rate. `[NUM]`
2.14.7 **The negative-cache footprint**: an unbounded space of invalid ids means an unbounded key
      count, which is why § 2.4.18's Bloom filter exists. Compute the Bloom filter's size for 2.4M
      valid ids at 1% FPR and compare. `[NUM]` `[PROVE]`
2.14.8 **Heap arithmetic for an in-process cache**: `ClientRestrictions` at 4 GB heap × 8 instances
      with "extreme request rate, trivial objects" — how much of that 4 GB can a cache take before GC
      pause time breaches the 30 ms decision budget? Work it. `[NUM]` `[PROVE]` `[X-REF 06]`
2.14.9 **Fragmentation**: `mem_fragmentation_ratio`, why RSS stays high after a large delete, why the
      ratio is unreliable after a peak, `activedefrag` and its cost. `[NUM]` `[CFG]` `[SOURCE]`
2.14.10 **Provision for peak, not average.** The docs say it plainly: if the workload sometimes needs
      10 GB you must provision 10 GB even if 5 GB usually suffices, because the allocator will not
      return the pages. `[PROVE]` `[SOURCE]`
2.14.11 **Cost arithmetic**: RAM per GB-month vs the database instance it displaces vs the
      data-transfer charge for cross-AZ reads. The break-even is usually obvious once written down,
      and almost never written down. `[NUM]` `[CURRENCY]` `[X-REF 18]`
2.14.12 **Small-object memory tricks**: Redis's hash-bucketing trick from the docs (split
      `object:1234` into key `object:12` field `34`, ~100 fields per hash, 11 MB → 1.7 MB for 100k
      objects) — an order of magnitude, and a real technique with a real cost (no per-field TTL
      before 7.4, no per-field eviction). `[NUM]` `[SOURCE]` `[PROVE]`

## §2.15 Observability

2.15.1 The rule: **an unmeasured cache is a cache you cannot reason about.** `recordStats()` is not
      optional.
2.15.2 The metric set that actually matters, each with what a bad value looks like: hit ratio, miss
      ratio, request rate, load (miss) latency p50/p99, load failure rate, eviction count and cause
      breakdown, expiry count, entry count, weighted size, invalidation rate, and stale-serve count.
      `[TABLE]` `[METRIC]`
2.15.3 **Hit ratio must be per cache, per tier and per key-prefix.** An aggregate hit ratio hides the
      one cache that is doing nothing. `[PROVE]` `[METRIC]`
2.15.4 **Latency percentiles, not averages** — § 1.1.16's case, where a 99% hit ratio with a 40-second
      miss determines the whole p99. `[PROVE]` `[METRIC]`
2.15.5 **Redis server metrics**: `keyspace_hits`/`misses`, `evicted_keys`, `expired_keys`,
      `used_memory` vs `maxmemory`, `mem_fragmentation_ratio`, `connected_clients`,
      `blocked_clients`, `instantaneous_ops_per_sec`, `rejected_connections`, `sync_full`,
      `latest_fork_usec`, `rdb_last_bgsave_status`, `aof_last_write_status`,
      `current_eviction_exceeded_time`. `[METRIC]` `[TABLE]`
2.15.6 **Keyspace metrics** — `INFO keyspace` per-db key and expiring-key counts, and what a rising
      key count with a flat memory figure tells you.
2.15.7 **Micrometer wiring**: `CaffeineCacheMetrics`, `CacheMetricsRegistrar`,
      `spring.cache.redis.enable-statistics` / `RedisCache#getStatistics()`,
      `HibernateMetrics`, and the `cache` meter naming convention. `[API]` `[X-REF 20]`
2.15.8 **Tracing a cache**: a span per cache operation with hit/miss as an attribute, and the reason
      it is worth the cardinality — it is the only way to see the two-tier path in one request.
      `[X-REF 20]`
2.15.9 **Cardinality discipline**: never tag a cache metric with the key. § 15.8's "Tagging metrics by
      client id. Millions of series." `[TRAP]` `[X-REF 20]`
2.15.10 **The alerts that are worth paging on**: hit ratio dropping below a baseline (not an absolute
      threshold), `evicted_keys` rising from zero, `used_memory / maxmemory` above a ceiling,
      cache-error rate above zero, and load-latency p99 breaching the budget. `[METRIC]`
2.15.11 **The alerts that are not worth paging on**, and why: absolute hit ratio, memory usage on a
      cache with an eviction policy (it is *supposed* to be full), and eviction count on a
      steady-state cache.
2.15.12 **Reading the graphs**, as a diagnostic: hit ratio falling with evictions rising = too small;
      hit ratio falling with expiries rising = TTL too short; hit ratio flat with origin latency
      rising = the origin, not the cache; hit ratio at 100% and staleness complaints = invalidation
      broken. `[DIAG]` `[FLOW]`
2.15.13 **`redis-cli --stat`, `--bigkeys`, `--memkeys`, `--hotkeys`, `--scan`, `MONITOR`** — the
      first-line toolkit, with the warning attached to `MONITOR`. `[CLI]`
2.15.14 The QuizStakes observability tie-in: § 15.8's "business vs system metric" — the cache is
      healthy while every deposit fails at `DEP-190`, and only a business metric notices. `[PROVE]`

## §2.16 Warming, cold start and readiness gating

2.16.1 **Cold start** — every deploy, restart, scale-out and cache failover begins at 0% hit ratio,
      and § 1.1.11's arithmetic applies immediately.
2.16.2 A rolling deploy that replaces pods slowly is fine; **a simultaneous fleet restart or a cache
      failover is an outage.** State the difference in one sentence. `[PROVE]`
2.16.3 **Warming techniques**, each with its cost: load reference data at startup; preload a curated
      hot-key list from yesterday's access logs; replicate across AZs so a failover finds a warm
      replica; dual-write to a new cluster before a migration cutover; stagger a fleet restart.
      `[TABLE]`
2.16.4 **Readiness gating is the mechanism that makes warming work.** A pod receives traffic when its
      readiness probe passes; if you warm asynchronously after startup, the pod goes ready
      immediately and takes full traffic with an empty cache — the warming was pointless. `[PROVE]`
2.16.5 The implementation: a `HealthIndicator` wired into `/actuator/health/readiness` that reports
      DOWN until warm-up completes, plus a bound on the warm-up so a broken loader does not block the
      deploy forever. `[BUILD]` `[API]`
2.16.6 **Keep warm-up out of the liveness probe**, or Kubernetes kills the pod mid-warm-up in a loop.
      `[TRAP]` `[X-REF 19]`
2.16.7 **`ApplicationReadyEvent` vs `@PostConstruct` vs `SmartInitializingSingleton`** for the
      warm-up hook, and why the event is right (the context is up, so the loader's dependencies
      work). `[API]` `[X-REF 07]`
2.16.8 **Design for cache loss**: rate-limit or circuit-break the origin so a mass miss degrades
      (slower responses, some shed load) instead of destroying the database. `[X-REF 22]`
2.16.9 **Load-test with the cache disabled at least once**, so you know what actually happens. Most
      teams find out during an incident. `[X-REF 16]`
2.16.10 The QuizStakes warm-up set, named: agreement current version, jurisdiction table, restriction
      type definitions, and the top-N `PendingActions` for currently-active sessions. Note that this
      is a small, bounded, fast list — which is what makes gating on it safe. `[NUM]`

## §2.17 Testing a cache

2.17.1 The three things worth asserting, and nothing else: the cache is *used* (one origin call for
      two reads), the cache is *invalidated* (a write makes the next read fresh), and the cache
      *fails open* (an unavailable cache still serves correct data). `[BUILD]`
2.17.2 **Never assert on timing.** Inject a `Ticker`/`Clock` and advance it. A test that
      `Thread.sleep`s for a TTL is a flaky test with a long runtime. `[TRAP]` `[X-REF 16]`
2.17.3 **A cache makes tests order-dependent.** Clear all caches between tests, or assert on a fresh
      `CacheManager` per test. `[TRAP]`
2.17.4 **Testing the proxy actually applied** — the self-invocation trap (§ 2.9.20) is invisible to a
      unit test that calls the method directly, so the test must go through the Spring context.
      `[PROVE]` `[X-REF 16]`
2.17.5 Testcontainers Redis vs an embedded in-memory fake, and the honest trade: the fake is fast and
      lies about eviction, expiry mechanics and cluster behaviour. `[X-REF 16]`
2.17.6 **Testing idempotent invalidation**: publish the same invalidation twice and assert one effect,
      which is the same discipline as § 14's idempotent consumer. `[X-REF 14]`
2.17.7 **Testing the stampede mitigation**: N concurrent readers on a cold key must produce exactly
      one loader invocation. This is the one concurrency test in the topic that is genuinely worth
      writing. `[BUILD]` `[X-REF 05]`
2.17.8 **Testing serialisation round-trips across versions** — serialise with the old shape,
      deserialise with the new, assert it either works or is on a different key. This is the test that
      prevents § 2.3.7's fleet-wide deserialisation failure. `[BUILD]`
2.17.9 What you cannot usefully unit-test and must load-test instead: hit ratio, eviction behaviour,
      memory footprint, and the cliff.

## §2.18 Choosing, and the anti-patterns

2.18.1 **The decision procedure, as an ordered set of questions**: is the read/write ratio high? can
      it be stale, and for how long? does it authorise anything? is it the same for all callers? how
      large? how expensive to recompute? what happens if the cache is gone? Each answer eliminates
      options. `[FLOW]` `[TABLE]`
2.18.2 The **placement** decision: immutable and small → in-process; shared and mutable → distributed;
      per-user and public-safe → HTTP; hot and tiny → both tiers. `[TABLE]`
2.18.3 The **pattern** decision: default cache-aside with delete-on-write; read-through when the
      loader is trivial and you want free coalescing; write-through only when the cache is
      authoritative for reads; write-behind never for business data. `[TABLE]`
2.18.4 **Anti-pattern: caching to hide a missing index or an N+1.** `[TRAP]`
2.18.5 **Anti-pattern: caching raw entities.** Bloated payloads, lazy-loading landmines, and
      invalidation on every unrelated field change. Cache a purpose-built view. `[TRAP]`
      `[RESEARCH]`
2.18.6 **Anti-pattern: caching everything.** Every cached object is an invalidation obligation, and
      the architecture becomes opaque. `[TRAP]`
2.18.7 **Anti-pattern: caches of caches (recaching).** Cascading invalidation nobody can untangle.
      `[TRAP]` `[RESEARCH]`
2.18.8 **Anti-pattern: no TTL because "we invalidate properly".** § 1.6.1. `[TRAP]`
2.18.9 **Anti-pattern: unbounded cache.** A `HashMap` cache is an OOM with a delay. `[TRAP]`
      `[X-REF 06]`
2.18.10 **Anti-pattern: caching in the constructor / at startup as a hidden dependency**, which turns
      a slow dependency into a slow startup and a failed dependency into a failed deploy. `[TRAP]`
2.18.11 **Anti-pattern: the cache as the source of truth by accident.** The write path stopped writing
      the origin and nobody noticed until a flush. `[TRAP]`
2.18.12 **Anti-pattern: caching an authorisation decision.** Invariant 12. The one anti-pattern in
      this list that is a regulatory finding rather than an operational annoyance. `[TRAP]`
2.18.13 **Anti-pattern: rethrowing cache errors** (§ 2.9.18's default), which makes the cache a hard
      dependency by omission. `[TRAP]`
2.18.14 **Anti-pattern: a shared cache with no key namespacing across services**, so one team's flush
      is another team's outage. `[TRAP]`
2.18.15 **Anti-pattern: measuring hit ratio and nothing else.** § 2.15.4. `[TRAP]`
2.18.16 The **"do you even need a cache"** checklist: is the query indexed, is the payload minimal, is
      the connection pooled, is the response compressible, is the work batchable, is the origin
      actually the bottleneck. Ask all six before adding a cache. `[TABLE]`

## §2.19 Cache security

2.19.1 **Cached authorisation is the top item**, and it is invariant 12. `[X-REF 13]`
2.19.2 **Cross-tenant key collision** (§ 1.7.13) as an access-control failure. `[TRAP]`
2.19.3 **`public` on an authenticated response** (§ 2.7.9) and **web cache deception** (§ 2.7.30).
2.19.4 **Caching secrets**: tokens, JWKS, decrypted PII. What is legitimate (a JWKS set with a TTL
      tied to key rotation) and what is not (a decrypted PII blob in a shared Redis with no
      encryption at rest). `[TABLE]` `[X-REF 13]`
2.19.5 **Redis security posture for a cache**: `requirepass`/ACL users (`ACL SETUSER` with
      key patterns and command categories), TLS, `rename-command`/disabled commands,
      `protected-mode`, network isolation, and **TLS certificate-based automatic client
      authentication with `tls-auth-clients-user`** (8.6). `[CFG]` `[RESEARCH]`
2.19.6 **Redis 8.6's PII hiding in ACL and server logs** as a compliance-relevant change — the logs
      used to leak key names and arguments. `[RESEARCH]` `[CURRENCY]`
2.19.7 **Encryption at rest and in transit for a cache**, and the honest question: if the cache holds
      only derived public data, is either worth the latency? If it holds PII, the answer is not
      optional. `[PROVE]`
2.19.8 **Right to erasure vs a cache** — § 15.7's conflict, sharpened: a deletion request must reach
      every cache tier, including a CDN and a browser you do not control. The only workable answer is
      short TTLs on anything erasable, which is a design constraint, not an operational one.
      `[PROVE]` `[TRAP]`
2.19.9 **Deserialisation attacks** via a writable cache (§ 1.10.3), and the mitigation:
      never Java-serialise, and validate types on read. `[X-REF 13]`
2.19.10 **Cache-based side channels and timing oracles** — a hit/miss timing difference reveals
      whether a key exists, which is a user-enumeration vector on a login or "is this email taken"
      path (`AO-099`). Named, with the constant-time-response mitigation. `[TRAP]` `[RESEARCH]`
2.19.11 **Cache poisoning of an invalidation channel**: if any client can publish to your pub/sub
      invalidation channel, any client can force a fleet-wide flush. ACL the channel. `[TRAP]`

---

# PART 3 — UNDER THE HOOD

## §3.1 Caffeine internals

3.1.1 The top-level structure: a `ConcurrentHashMap` for storage plus a separate **policy** layer for
      eviction and expiry, deliberately decoupled so a read does not have to lock the policy.
      `[PROVE]` `[SOURCE]`
3.1.2 **`BoundedLocalCache`** as the generated class family, and the **code-generation** design: a
      class per feature combination (`SS`, `SSMS`, `SSLMSW`, …) so an entry carries only the fields
      its configuration needs. Explain the memory argument. `[SOURCE]` `[PROVE]`
3.1.3 **The read path**: hash lookup, then record the access into a **striped lossy ring buffer**
      rather than mutating a shared LRU list. Reads are therefore nearly lock-free. `[PROVE]`
      `[SOURCE]`
3.1.4 **Why the read buffer is allowed to be lossy**: a dropped read only slightly degrades the hit
      rate; it cannot corrupt the cache. This is the single cleverest decision in the design.
      `[PROVE]`
3.1.5 **Stripe growth on contention**: the read buffer adds stripes when it detects contention, up to
      a bound related to the number of CPUs. `[SOURCE]` `[RESEARCH]`
3.1.6 **The write path**: a growable circular array with forwarding links between chunks, which
      **must not lose writes**, so it spins and retries before yielding to let the consumer drain.
      `[PROVE]` `[SOURCE]`
3.1.7 **Lock amortisation**: a single consumer drains the buffers under one lock and applies the
      policy in batches, so the per-operation cost is amortised across many threads. `[PROVE]`
3.1.8 **The three entry states** — `alive` (in the hash table and the policy queues), `retired`
      (removed from the table, still queued), `dead` (removable) — and why the intermediate state has
      to exist given that the table and the queues are updated at different times. `[PROVE]`
      `[SOURCE]`
3.1.9 **The fastpath**: while occupancy is below 50% of maximum, the frequency sketch is not even
      initialised, so a cache that never fills pays nothing for the policy. `[NUM]` `[SOURCE]`
      `[RESEARCH]`
3.1.10 **Expiration via a hierarchical timer wheel** — O(1) scheduling for variable expiry, with
      buckets covering increasing time spans. Give the actual bucket spans from the source, or mark
      them unverified. `[SOURCE]` `[RESEARCH]` `[NUM]`
3.1.11 **`expireAfterWrite`/`expireAfterAccess` use fixed-order queues instead**, because a constant
      duration means the queue is already sorted — a nice example of picking the cheaper structure
      when the problem allows. `[PROVE]`
3.1.12 **`refreshAfterWrite` mechanics**: the reload is asynchronous on the configured `Executor`, the
      stale value is returned immediately, and a refresh in flight is deduplicated. Note the 3.2.4
      fix for head-of-line blocking of expiration queues caused by in-flight async entries.
      `[SOURCE]` `[CURRENCY]` `[RESEARCH]`
3.1.13 **The default executor is `ForkJoinPool.commonPool()`**, which means your cache refreshes
      share a pool with everything else that defaults to it. Say what to do instead. `[TRAP]`
      `[X-REF 05]`
3.1.14 **`AsyncCache` in-flight entries**: an entry whose value is an incomplete
      `CompletableFuture` is present in the map, which is what gives async caches their coalescing —
      and what makes a failed load need explicit removal. `[PROVE]`
3.1.15 **Weight-based eviction** internals: the weight is recorded at insertion, a `put` that changes
      weight adjusts the total, and eviction runs until the total is under the maximum — so a single
      heavy entry can evict many light ones. `[PROVE]`
3.1.16 **What Caffeine does not guarantee**: no iteration order, `estimatedSize()` may exceed
      `maximumSize` transiently, eviction is not immediate, and a removal listener runs
      asynchronously by default. Each with the reason. `[PROVE]` `[TRAP]`
3.1.17 **`cleanUp()`** as the manual drain, and the one situation where you need it (a test asserting
      on size).
3.1.18 Reading a real excerpt of `BoundedLocalCache`'s `afterRead`/`afterWrite`/`maintenance` and
      explaining every line. `[SOURCE]`

## §3.2 W-TinyLFU, TinyLFU and the frequency sketch

3.2.1 The problem TinyLFU solves, stated first: LFU needs a frequency count per key, which costs more
      memory than the cached value for small values. So you need an **approximate** frequency
      histogram. `[PROVE]`
3.2.2 **Count-Min Sketch** — d hash functions, w counters each, increment all d on access, estimate
      = min of the d counters. Why the minimum: every counter is an over-estimate due to collisions,
      so the smallest is the tightest bound. `[PROVE]` `[X-REF 01]`
3.2.3 The error bounds, stated properly: over-estimate only, with error `ε` and confidence `1−δ` for
      `w = ⌈e/ε⌉`, `d = ⌈ln(1/δ)⌉`. `[PROVE]` `[NUM]`
3.2.4 **Caffeine's `FrequencySketch` is a 4-bit Count-Min Sketch**, so each counter saturates at 15,
      packed into `long[]` — and the stated cost is **8 bytes per cache entry** for accuracy.
      `[NUM]` `[SOURCE]` `[RESEARCH]`
3.2.5 **The reset/aging step**: when the total increment count reaches a threshold proportional to the
      maximum size, every counter is **halved**. This is what makes it a *windowed* frequency rather
      than a lifetime one, and it is why a formerly-popular key can lose. `[PROVE]` `[SOURCE]`
3.2.6 **The sample size** — the reset threshold is a multiple of the maximum size (the paper's
      guidance is around 10×) — and the effect of getting it wrong in either direction. `[NUM]`
      `[RESEARCH]`
3.2.7 **Doorkeeper** — a small Bloom filter in front of the sketch so one-hit-wonders never consume a
      counter. Named, mechanism, and whether Caffeine ships it. `[RESEARCH]`
3.2.8 **TinyLFU as admission**: on a miss with a full cache, estimate `freq(candidate)` and
      `freq(victim)`; admit the candidate only if it wins. Prove why this is what defeats scan
      pollution — a scanned key has frequency 1 and loses to any real hot key. `[PROVE]`
3.2.9 **The tie-break** when frequencies are equal, and why a *randomised* tie-break matters: a
      deterministic one is attackable by an adversarial access pattern. `[PROVE]` `[RESEARCH]`
3.2.10 **W-TinyLFU's window**: a small LRU admission window in front, whose purpose is to let a
      genuine burst of new-but-hot keys establish frequency before facing the doorman. Without it,
      TinyLFU under-performs on bursty traces. `[PROVE]`
3.2.11 **The main space is SLRU** — probation and protected segments — with the classic 80/20 split
      as the paper's starting point. `[NUM]`
3.2.12 **The window/main split is adaptive, not fixed.** Caffeine hill-climbs the window size from
      measured hit rate at runtime, so quoting "1% window / 99% main" describes the paper's default,
      not the running cache. This is the `[VERSION-TRAP]` from the header. `[PROVE]` `[SOURCE]`
      `[RESEARCH]` `[VERSION-TRAP]`
3.2.13 **Hill climbing** mechanics: sample the hit rate over an interval, step the window in the
      direction that improved it, shrink the step as it converges, restart on a workload shift.
      `[PROVE]` `[RESEARCH]`
3.2.14 The measured result to quote honestly: W-TinyLFU is at or near optimal across a broad trace
      set, and the guide's existing claim ("better hit rates than LRU on real workloads") is true but
      should be replaced with a figure and a source. `[NUM]` `[RESEARCH]`
3.2.15 Reading an excerpt of `FrequencySketch.frequency`/`increment`/`reset` line by line — the
      seeding, the `indexOf`, the 4-bit packing, and the halving. `[SOURCE]`
3.2.16 **Why this belongs in a caching guide and not a data-structures guide**: the sketch is the
      reason a modern cache can afford an admission policy at all. `[PROVE]`

## §3.3 The eviction algorithms, worked properly

3.3.1 **Belady's proof of optimality** for MIN, and the reason it is unachievable online — it requires
      the future reference string. `[PROVE]`
3.3.2 **Stack algorithms** and the property that a larger cache never has more misses (inclusion
      property). LRU is a stack algorithm; **FIFO is not**, which is why FIFO can exhibit
      **Bélády's anomaly** — adding capacity increases misses. Prove it with a concrete reference
      string. `[PROVE]` `[NUM]`
3.3.3 **LRU's competitive ratio**: LRU is k-competitive against OPT for a cache of size k, and no
      deterministic online algorithm does better. State the theorem and what it means practically —
      the worst case is bad and the average case is fine. `[PROVE]` `[RESEARCH]`
3.3.4 **The scan-pollution proof**: a sequential scan of `n > k` distinct keys evicts every resident
      key under LRU, giving a 0% hit ratio for the scan *and* for everything after it until the hot
      set is re-established. `[PROVE]`
3.3.5 **Exact LRU's implementation cost**: a doubly-linked list plus a hash map, and the fact that
      *every read is a write* to the list — the concurrency bottleneck that motivates every
      approximation in this section. `[PROVE]` `[X-REF 02]`
3.3.6 **CLOCK as approximate LRU**: a reference bit per entry, a circular hand that clears bits and
      evicts the first entry it finds with the bit clear. One bit per entry instead of two pointers,
      and no write on read. `[PROVE]`
3.3.7 **CLOCK-Pro** and the reuse-distance idea, one paragraph.
3.3.8 **Redis's sampled LRU** as a third approximation: sample `maxmemory-samples` keys, evict the
      oldest, and since 3.0 keep a **pool of good candidates** across evictions so the approximation
      converges on true LRU. Explain why the pool improves it so much. `[PROVE]` `[SOURCE]`
3.3.9 The published comparison to quote: Redis 3.0 with 5 samples is much closer to true LRU than
      2.8, and with 10 samples it is very close to theoretical. `[NUM]` `[SOURCE]`
3.3.10 **Morris counters (approximate counting)** as the LFU equivalent trick: an 8-bit logarithmic
      counter that estimates a frequency up to ~1M with a probabilistic increment. `[PROVE]`
      `[SOURCE]`
3.3.11 The `lfu-log-factor` table read as a design tool: factor 0 gives resolution at low counts and
      saturates at 1,000 hits; factor 100 keeps distinguishing up to 1M. Choose by where your
      interesting distinctions are. `[NUM]` `[SOURCE]` `[PROVE]`
3.3.12 **`lfu-decay-time`** and the halving-on-sample mechanism, plus what `0` (never decay) does to a
      cache whose workload shifts. `[PROVE]`
3.3.13 **ARC's four lists** and the adaptation rule: a hit in the B1 ghost list grows T1's target, a
      hit in B2 grows T2's, so the policy tracks the workload's recency/frequency balance without
      tuning. `[PROVE]`
3.3.14 **2Q** as the simpler ancestor of the same idea, and **LIRS** as the reuse-distance-based one.
3.3.15 **S3-FIFO's structure** — a small FIFO (~10% of capacity) that most objects never leave, a main
      FIFO, and a ghost queue recording what the small queue evicted — plus the observation it exploits:
      most objects are never reused, so demoting fast is more valuable than promoting well.
      `[PROVE]` `[NUM]` `[RESEARCH]`
3.3.16 **SIEVE's structure and the exact algorithm**: one FIFO queue, a `visited` bit per object, and
      a **hand** that moves from tail to head; on eviction, if the object at the hand is visited, clear
      the bit and move on, else evict it. Note the difference from CLOCK — the hand does not reset to
      a fixed position, and objects are **not reinserted**. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.3.17 The SIEVE results to quote with their source: lower miss ratio than nine state-of-the-art
      algorithms on more than 45% of 1,559 traces; 17% and 125% higher throughput than optimised LRU
      at 1 and 16 threads; implemented in five production libraries with fewer than 20 lines changed
      on average. `[NUM]` `[RESEARCH]`
3.3.18 **Lazy promotion / quick demotion** stated as the unifying principle, with the derivation: if
      most objects are one-hit wonders, spending work on promotion is wasted and spending work on
      fast demotion is not. This single idea explains FIFO's competitiveness, S3-FIFO's small queue
      and SIEVE's hand. `[PROVE]` `[RESEARCH]`
3.3.19 **Why LRU persists despite all of the above**: it is the default everywhere, it is understood,
      and the difference only matters at scale. Say this plainly so the reader does not over-rotate.
3.3.20 **The miss-ratio curve** as the tool that decides between them, and how you actually obtain one
      (trace replay, or Mattson's stack-distance algorithm, or a sampled approximation like SHARDS).
      `[PROVE]` `[RESEARCH]`

## §3.4 Redis's execution model

3.4.1 **Single-threaded command execution** on an event loop (`ae.c`), with `epoll`/`kqueue`
      multiplexing, and the consequences enumerated: every command is atomic, there are no data races,
      there is no lock overhead, and **one slow command stalls every client**. `[PROVE]`
3.4.2 **The `serverCron` timer** at `hz` (default 10, `dynamic-hz` on by default) and everything it
      does: active expiry, eviction, incremental rehashing, client timeouts, replication housekeeping,
      and background saves. This is where the "background work" in a single-threaded server lives.
      `[CFG]` `[NUM]` `[SOURCE]` `[RESEARCH]`
3.4.3 **I/O threads** (`io-threads`, and the read/write offload) as the one place Redis is genuinely
      multi-threaded, and what it does *not* parallelise — command execution. `[CFG]` `[TRAP]`
      `[RESEARCH]`
3.4.4 **Background threads (`bio`)** for `close`, `fsync` and lazy free, and why `UNLINK` is fast
      because of them. `[SOURCE]`
3.4.5 **Why "atomic" does not mean "transactional"**: each command is atomic in isolation, so a
      read-modify-write across two commands is a race, which is why `INCR`, `SET NX` and Lua exist.
      `[PROVE]` `[TRAP]`
3.4.6 **The command table and `commandstats`/`latencystats`** as the way to find which command is
      costing you. `[CLI]` `[DIAG]`
3.4.7 **Incremental rehashing** of the main dict, and what it means for latency: the resize is spread
      across operations and the cron rather than done at once — the same problem Java's `HashMap`
      solves differently. `[PROVE]` `[X-REF 02]`
3.4.8 **The `dict` structure**: two hash tables during a rehash, chaining, `dictScan`'s reverse-binary
      cursor, and why that cursor design is what lets `SCAN` give its guarantee across a resize. This
      is the most elegant thing in the Redis codebase and worth the paragraph. `[PROVE]` `[SOURCE]`
3.4.9 **`SCAN`'s guarantees, precisely**: every element present from start to end of the iteration is
      returned at least once; elements added or removed during it may or may not be; a key may be
      returned more than once. Derive each from the cursor design. `[PROVE]` `[SOURCE]`
3.4.10 **`COUNT` is a hint, not a page size**, and `MATCH` filters *after* fetching, so a restrictive
      pattern still scans the whole keyspace. This is why "`SCAN` with a pattern" is not cheap.
      `[TRAP]` `[PROVE]`

## §3.5 Redis memory model and encodings

3.5.1 **`robj`** — type, encoding, LRU/LFU field, refcount, pointer — and the per-object overhead it
      implies. `[SOURCE]` `[NUM]`
3.5.2 **`sds`** (simple dynamic string) and its header variants (`sdshdr5/8/16/32/64`), chosen by
      length, so a short string has a 3-byte header rather than 16. `[SOURCE]` `[NUM]`
3.5.3 **`embstr` vs `raw` vs `int` string encodings**, with the 44-byte threshold for `embstr` and
      what shared integers do to `OBJECT REFCOUNT`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.5.4 **`listpack`** as the successor to `ziplist`, its layout, and the fact that operations on it are
      O(N) but cache-friendly — which is why it wins for small collections. `[PROVE]`
3.5.5 **The encoding thresholds and their defaults**, with the documented/shipped discrepancy called
      out: `hash-max-listpack-entries` (docs 512, `redis.conf` 128 — verify with `CONFIG GET`),
      `hash-max-listpack-value` 64, `zset-max-listpack-entries` 128, `zset-max-listpack-value` 64,
      `set-max-intset-entries` 512, `set-max-listpack-entries` 128, `set-max-listpack-value` 64
      (7.2+), `list-max-listpack-size` 128. `[CFG]` `[NUM]` `[SOURCE]` `[RESEARCH]`
3.5.6 **Conversion is one-way**: once a collection exceeds a threshold it converts to the full
      structure and **does not convert back** when it shrinks. This is a real memory-leak-shaped
      surprise. `[TRAP]` `[PROVE]`
3.5.7 **`quicklist`** for lists (a linked list of listpacks, with `list-compress-depth`), **`intset`**
      for integer-only sets, **`skiplist` + `dict`** for large sorted sets, **`hashtable`** for large
      hashes. `[TABLE]` `[SOURCE]`
3.5.8 **Redis 8.6's unified field/value and score/value structures** for hashtable-encoded hashes and
      skiplist-encoded sorted sets, giving "substantial memory reduction". Quantify it if the source
      does. `[CURRENCY]` `[RESEARCH]`
3.5.9 **`OBJECT ENCODING` and `MEMORY USAGE`** as the two commands that turn all of this from theory
      into a measurement. `[CLI]` `[DIAG]`
3.5.10 **The 10× memory saving** from small-object encodings that the docs claim (5× average), and the
      arithmetic behind the bucketing trick's 11 MB → 1.7 MB result. `[NUM]` `[SOURCE]`
3.5.11 **jemalloc** as the allocator, size classes, and why a 65-byte value occupies 80 bytes.
      `[NUM]` `[PROVE]`
3.5.12 **Fragmentation, properly explained**: `used_memory` is what Redis asked for, `used_memory_rss`
      is what the OS gave, and the ratio is unreliable after a peak because freed pages are not
      returned. `activedefrag` and its CPU cost. `[PROVE]` `[SOURCE]`
3.5.13 **Copy-on-write during a fork**, and the arithmetic that surprises people: a write-heavy
      instance can double its RSS during a `BGSAVE` because every touched page is duplicated.
      `[PROVE]` `[NUM]` `[X-REF 11]`
3.5.14 **Transparent huge pages turn a 4 KB COW fault into a 2 MB one**, which is why disabling THP is
      on the Redis admin checklist. State the mechanism, not just the instruction. `[PROVE]`
      `[X-REF 11]`
3.5.15 **Swap is fatal to a cache**: a page fault on a 100 ns lookup is a 10 ms disk read, and Redis's
      single thread is blocked for all of it. `vm.swappiness` and the memory-lock question.
      `[PROVE]` `[X-REF 11]`
3.5.16 **32-bit builds** using less memory per key with a 4 GB ceiling, as a documented curiosity that
      shows how much of a cache's memory is pointers. `[SOURCE]` `[NUM]`
3.5.17 **Where the memory actually goes**, as a worked breakdown for one QuizStakes cache entry: key
      string + `sds` header + `robj` + value + dict entry + expires-dict entry + jemalloc rounding.
      Sum it, then multiply by 380k. `[NUM]` `[PROVE]`

## §3.6 Redis expiry internals

3.6.1 **The expires dict** — a second hash table mapping key → absolute millisecond timestamp — which
      is why setting a TTL costs memory and why `allkeys-lru` is more memory-efficient than
      `volatile-lru`. `[PROVE]` `[SOURCE]`
3.6.2 **Absolute Unix timestamps, not durations**, so time flows while the instance is down and a
      clock jump expires keys immediately. The docs' RDB-across-desynced-clocks warning is the
      concrete failure. `[PROVE]` `[SOURCE]`
3.6.3 **Passive (lazy) expiry**: a key is checked on access and deleted if expired, which is why an
      expired key can hold memory indefinitely if nobody reads it. `[PROVE]`
3.6.4 **Active expiry (`activeExpireCycle`)**: sampled from the expires dict on the cron, with the
      fast and slow variants. Give the source constants — `ACTIVE_EXPIRE_CYCLE_KEYS_PER_LOOP` = 20,
      the ~25% still-expired continuation threshold, `ACTIVE_EXPIRE_CYCLE_FAST_DURATION`, and the CPU
      budget as a fraction of `hz` — and mark them for verification against `expire.c`. `[NUM]`
      `[SOURCE]` `[RESEARCH]`
3.6.5 The consequence to state numerically: with a sampling algorithm, the expected fraction of
      logically-expired-but-resident keys is bounded but non-zero, so `used_memory` legitimately
      exceeds the live dataset. `[PROVE]`
3.6.6 **Replicas do not expire keys themselves.** They keep the expire metadata, report a logically
      expired key as absent to clients, and wait for the primary's synthesised `DEL`. Explain why
      this centralisation is required for consistency. `[PROVE]` `[SOURCE]`
3.6.7 The corollary: **a promoted replica starts expiring independently**, so a failover can produce a
      burst of `DEL`s and `expired` events. `[PROVE]`
3.6.8 **Expiry in the AOF and the replication stream** is a synthesised `DEL`, not a timer — so a
      replayed AOF produces the same keyspace regardless of when it is replayed. `[SOURCE]`
3.6.9 **`EXPIRE` with a non-positive TTL deletes rather than expires**, and emits a `del` keyspace
      event, not `expired`. A real gotcha for anyone building on notifications. `[TRAP]` `[SOURCE]`
3.6.10 **Expiry accuracy**: 0–1 ms since 2.6 (0–1 s in 2.4). Quote it, because "Redis TTLs are
      approximate" is often said with no number attached. `[NUM]` `[SOURCE]`
3.6.11 **Hash-field expiry internals** (7.4+) and what they cost — a per-hash structure to track field
      TTLs, plus the interaction with listpack encoding. `[RESEARCH]`
3.6.12 **Why an expiry burst is a latency event**: 100,000 keys expiring in the same second means the
      cron does 100,000 deletes plus 100,000 replication `DEL`s plus 100,000 notifications, on the
      single command thread. This is § 1.6.8's jitter argument, proved from the internals. `[PROVE]`
      `[NUM]`

## §3.7 Redis eviction internals

3.7.1 **Where eviction happens**: `performEvictions` on the command path, before the command runs, in
      a loop until memory is under `maxmemory` or nothing more can be freed. So an eviction burst is
      latency on *your* command. `[PROVE]` `[SOURCE]`
3.7.2 **What counts toward `maxmemory`** and what does not (`mem_not_counted_for_evict`: replication
      backlog, AOF buffer, client output buffers) — and the feedback-loop argument the docs give for
      excluding them: evictions themselves generate replication traffic, so counting it would cause
      runaway eviction. `[PROVE]` `[SOURCE]`
3.7.3 **The eviction pool** (16 entries, best-candidate cache across calls) and why it turns random
      sampling into a good approximation. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.7.4 **The LRU clock** — a coarse global clock in the `robj`'s 24-bit `lru` field, its resolution and
      **wraparound period**, and what the wraparound does to eviction decisions. `[NUM]`
      `[SOURCE]` `[RESEARCH]`
3.7.5 **The LFU field layout**: 8 bits of Morris counter plus 16 bits of last-decrement minute, packed
      into the same 24 bits, which is why you cannot have both LRU and LFU information at once.
      `[PROVE]` `[SOURCE]`
3.7.6 **New keys start with a non-zero LFU counter** (`LFU_INIT_VAL`) so they are not evicted
      instantly — the same problem W-TinyLFU's window solves, solved differently. `[NUM]`
      `[SOURCE]` `[RESEARCH]`
3.7.7 **`volatile-ttl`'s implementation** — also sampled, also approximate, so it evicts *a* short-TTL
      key, not *the* shortest. `[PROVE]`
3.7.8 **`allkeys-lrm` internals** (8.6): the timestamp is updated on write paths only. State which
      commands count as a modification, or mark it for verification. `[RESEARCH]`
3.7.9 **What happens when eviction cannot free enough**: the OOM error, which commands are rejected
      (`is-denyoom-command`), and the fact that reads keep working. `[PROVE]` `[SOURCE]`
3.7.10 **`current_eviction_exceeded_time`** as the metric that tells you how long you have been over
      the limit — better than `evicted_keys` for spotting sustained pressure. `[METRIC]` `[SOURCE]`
3.7.11 **Eviction and replication**: an eviction on the primary is propagated as a `DEL`, so a replica
      never evicts on its own — the same centralisation as expiry, for the same reason. `[PROVE]`
3.7.12 **Eviction in Cluster** is per-node against per-node `maxmemory`, so an unbalanced slot
      distribution produces asymmetric eviction and a hit ratio that varies by key. `[PROVE]`
      `[TRAP]`

## §3.8 Redis persistence internals, and what they cost a cache

3.8.1 **RDB**: `fork`, the child serialises the dataset, the parent keeps serving with COW. The
      latency cost is the fork itself (`latest_fork_usec`) plus the COW page duplication.
      `[PROVE]` `[METRIC]`
3.8.2 The `save` schedule syntax and defaults (`save 3600 1`, `save 300 100`, `save 60 10000`), read
      as "seconds, changed keys". `[CFG]` `[NUM]` `[RESEARCH]`
3.8.3 **AOF**: the command log, `appendfsync always`/`everysec`/`no`, the rewrite (also a fork), and
      `aof-use-rdb-preamble` making the rewrite an RDB plus a tail. `[CFG]`
3.8.4 **Multi-part AOF** (7.0+): a manifest plus base and incremental files, replacing the single-file
      rewrite. `[RESEARCH]`
3.8.5 **`appendfsync always` puts an `fsync` in the command path**, which is how a cache acquires disk
      latency. Say the number. `[NUM]` `[PROVE]`
3.8.6 **The durability arithmetic**: RDB loses everything since the last snapshot (minutes); AOF
      `everysec` loses up to one second; AOF `always` loses nothing but costs an `fsync` per write.
      `[TABLE]` `[NUM]`
3.8.7 **Managed Redis frequently ships with persistence off**, so the guide's warning stands: never
      treat it as a system of record. `[CURRENCY]`
3.8.8 **For a pure cache, persistence off is usually right** (§ 2.11.30), and the internals section is
      where the reason becomes concrete: no fork, no COW, no `fsync`, no rewrite. `[PROVE]`
3.8.9 **Diskless replication** (`repl-diskless-sync`, `repl-diskless-load` with 8.6's new `flushdb`
      option) and 8.6's disabling of RDB compression during diskless replication for transfer speed.
      `[CFG]` `[RESEARCH]` `[CURRENCY]`
3.8.10 **Warm restart via RDB** as the one caching-relevant reason to keep persistence: a restart that
      loads a snapshot skips § 1.1.11's cliff. Weigh it against the fork cost. `[PROVE]`

## §3.9 Redis replication and Cluster internals

3.9.1 **Async replication**: the primary acknowledges the client before the replica has the write, so
      a failover can lose recent writes. This is the mechanism behind § 2.11.29. `[PROVE]`
3.9.2 **The replication backlog and partial resynchronisation** (`PSYNC`, replication id and offset),
      and `sync_full` as the metric that tells you the backlog was too small. `[CFG]` `[METRIC]`
3.9.3 **`WAIT numreplicas timeout`** as the only synchronous-ish primitive, and why it is not a
      quorum write. `[PROVE]` `[TRAP]`
3.9.4 **Replica reads** and their staleness (`replica-serve-stale-data`), which composes with the
      cache's own staleness. `[CFG]` `[PROVE]`
3.9.5 **Sentinel**: monitoring, quorum-based failure detection, leader election, promotion,
      client notification via pub/sub, and the client's responsibility to re-resolve the primary.
      `[PROVE]`
3.9.6 **Cluster**: the cluster bus, gossip, `PFAIL`→`FAIL` promotion of a failure verdict, slot
      ownership, epoch-based conflict resolution, and replica failover. `[PROVE]`
3.9.7 **`CRC16(key) mod 16384`** and the hash-tag rule (`{…}` selects the substring to hash), stated
      exactly because a candidate is often asked to compute it. `[NUM]` `[SOURCE]`
3.9.8 **`MOVED` vs `ASK`** and the correct client behaviour for each: `MOVED` updates the slot map,
      `ASK` applies to one command and requires `ASKING` first. Getting this wrong causes a
      redirection storm during a resharding. `[WIRE]` `[PROVE]`
3.9.9 **Resharding** moves whole slots (`CLUSTER SETSLOT MIGRATING`/`IMPORTING`, `MIGRATE`), so keys
      move without the key→slot function changing — § 2.13.6's point, from the internals. `[CLI]`
3.9.10 **`cluster-require-full-coverage`** and the availability decision it encodes: with it on, losing
      a slot range takes the whole cluster offline. For a cache, off is usually right, and the bible
      must say why. `[CFG]` `[PROVE]`
3.9.11 **What a client library must do** and therefore what can go wrong: initial topology discovery,
      slot map caching, refresh on `MOVED`, periodic refresh, and adaptive refresh triggers. Lettuce's
      `ClusterTopologyRefreshOptions` named. `[API]` `[RESEARCH]`
3.9.12 **Atomic slot migration** (referenced in the 8.6 notes) as the current direction of travel, and
      the `RedisBloom`/`RedisJSON` support for it. `[CURRENCY]` `[RESEARCH]`

## §3.10 Client-side caching (tracking) internals

3.10.1 The problem it solves, in Redis's own framing: the DIY pub/sub invalidation pattern is "tricky
      and costly from the point of view of the bandwidth used, because often such patterns involve
      sending the invalidation messages to every client, even if certain clients may not have any copy
      of the invalidated data." `[SOURCE]` `[PROVE]`
3.10.2 **Default (non-broadcasting) mode**: the server remembers which keys each client read and sends
      an invalidation only to clients that might hold them. Costs server memory, sends fewer messages.
      `[PROVE]`
3.10.3 **The Invalidation Table**: a single global table mapping key → set of client IDs. Note the two
      design decisions the docs call out — **client IDs, not pointers**, so a disconnect needs no
      garbage collection pass; and **a single key namespace across databases**, so a write to `foo` in
      db 3 invalidates a client caching `foo` from db 2. `[PROVE]` `[SOURCE]` `[TRAP]`
3.10.4 **The table is bounded, and overflow fabricates invalidations**: when full, the server evicts an
      entry by *pretending the key was modified*, forcing clients to drop a value that is still
      correct. Correct, and surprising. `[PROVE]` `[SOURCE]`
3.10.5 **`CLIENT TRACKING ON|OFF`** with every option: `REDIRECT <client-id>`, `PREFIX <prefix>`
      (repeatable), `BCAST`, `OPTIN`, `OPTOUT`, `NOLOOP`. `[API]` `[WIRE]` `[SOURCE]`
3.10.6 **Two-connection mode** for RESP2: one connection `SUBSCRIBE`s to `__redis__:invalidate`, the
      data connection uses `CLIENT TRACKING on REDIRECT <id>`, and many data connections can redirect
      to one invalidation connection — which is how a connection pool does this. `[WIRE]` `[FLOW]`
      `[SOURCE]`
3.10.7 **The pub/sub channel is a trick, not a broadcast**: only the redirected connection receives it,
      which is what makes the feature scalable. Say this explicitly, because the channel name implies
      otherwise. `[PROVE]` `[SOURCE]` `[TRAP]`
3.10.8 **RESP3 mode**: invalidations arrive as `push` messages on the same connection, so ordering
      relative to command replies is known — which eliminates § 3.10.12's race. `[PROVE]`
3.10.9 **The invalidation message payload is an array of keys**, so a batch is one message, and
      **a `FLUSHALL`/`FLUSHDB` sends `null`** meaning "drop everything". `[WIRE]` `[SOURCE]`
3.10.10 **What triggers an invalidation**: a write to the key, **expiry**, or **eviction by the
      `maxmemory` policy**. All three, which is more than most implementations of this pattern handle.
      `[PROVE]` `[SOURCE]`
3.10.11 **`OPTIN` + `CLIENT CACHING YES`** for explicit per-command caching, and the documented detail
      that `CACHING` affects the immediately following command — but if that command is `MULTI`, the
      whole transaction is tracked, and for a Lua script, every command it runs is tracked.
      `[PROVE]` `[SOURCE]`
3.10.12 **`OPTOUT` + `CLIENT UNTRACKING <key>`** as the inverse. `[API]` `[SOURCE]`
3.10.13 **`BCAST` + `PREFIX`**: no server-side memory, a **Prefixes Table** of prefix → client list,
      and the rule that **no two registered prefixes may overlap** (`foo` and `foob` are rejected
      because both match `foobar`). Server CPU grows with the number of prefixes; the server can build
      one reply and fan it out. `[PROVE]` `[SOURCE]` `[TRAP]`
3.10.14 **`NOLOOP`** — do not tell me about my own writes — plus the subtlety the docs spell out: with
      `NOLOOP` in default mode the key is still **untracked** for that connection after its own write,
      so it must read the key again to resume receiving invalidations. `[PROVE]` `[SOURCE]`
      `[TRAP]`
3.10.15 **The redirection race**, worked exactly as the docs do: `GET foo` sent; invalidation for `foo`
      arrives on the invalidation connection; the `GET` reply arrives afterwards and the client caches
      a value it was already told to drop. The fix is a **`caching-in-progress` placeholder** written
      before the request, deleted by the invalidation, and checked before the reply is stored.
      `[PROVE]` `[FLOW]` `[SOURCE]` `[TRAP]`
3.10.16 **Losing the invalidation connection means the local cache must be flushed**, and the docs'
      required behaviour: flush on disconnect, and **periodically `PING` the invalidation channel**
      (which works even in subscribe mode) so a broken connection is detected rather than assumed
      healthy. `[PROVE]` `[SOURCE]`
3.10.17 **Any disconnection in a pool flushes the whole client-side cache** — stated in the client docs
      — which makes the feature's hit ratio sensitive to connection churn. `[TRAP]` `[SOURCE]`
3.10.18 **Which commands are cacheable**: all `@read` ACL-category commands except probabilistic and
      time-series types, non-deterministic commands (`HRANDFIELD`, `HSCAN`, `ZRANDMEMBER`) and
      `FT.*`. `[TABLE]` `[SOURCE]`
3.10.19 **What gets cached per command**, which is subtler than people expect: `GET` caches the whole
      string but `SUBSTR` caches its result *separately*; `SISMEMBER` and `LLEN` are cached separately
      from the object; `MGET name:1 name:2` is a different entry from `MGET name:2 name:1` because
      order matters; hash/JSON/set/zset whole-object results are separate from field results.
      `[TABLE]` `[SOURCE]` `[PROVE]`
3.10.20 **`tracking-table-max-keys`** as the bound to configure, and the alternative of `BCAST` mode
      which costs no server memory at all. `[CFG]` `[RESEARCH]`
3.10.21 **`CLIENT TRACKINGINFO`** for verifying what a connection actually has enabled — the
      diagnostic for "why am I not getting invalidations". `[CLI]` `[DIAG]` `[RESEARCH]`
3.10.22 **Client support**: Jedis ≥ 5.2.0, redis-py ≥ 5.1.0, node-redis ≥ 5.1.0, go-redis ≥ 9.22.0;
      and the warning that "supports `CLIENT TRACKING`" is not the same as "implements client-side
      caching". `[CURRENCY]` `[SOURCE]` `[TRAP]`
3.10.23 **Sizing the client cache** with the docs' own arithmetic: 10 MB budget ÷ 80-byte average
      (measured with `MEMORY USAGE`) ≈ 131,072 entries. `[NUM]` `[SOURCE]`
3.10.24 **The docs' usage guidance**, which is the near-cache guidance from § 2.6 restated by the
      vendor: use a separate non-tracking connection for write-hot data like counters, because the
      invalidation traffic exceeds the saving; put a max TTL on every locally cached key even if the
      server key has none, as protection against a missed invalidation. `[PROVE]` `[SOURCE]`
3.10.25 **How this compares to the DIY pub/sub pattern** of § 2.6.5, feature by feature: delivery
      scope, memory cost, expiry/eviction coverage, disconnect handling, and whether you still need a
      TTL (you do). `[TABLE]` `[PROVE]`

## §3.11 Java client internals

3.11.1 **Lettuce**: Netty-based, a single **multiplexed** connection that is thread-safe and pipelines
      by default, sync/async/reactive APIs over the same connection. Therefore pooling is usually
      unnecessary — and pooling it can *reduce* throughput by defeating pipelining. `[PROVE]`
      `[TRAP]`
3.11.2 The exceptions that do need a pool or a dedicated connection: blocking commands, `MULTI`/`WATCH`
      transactions, `SUBSCRIBE`, and `CLIENT TRACKING` redirection. `[TABLE]`
3.11.3 **Lettuce's `ClientOptions`**: `autoReconnect`, `disconnectedBehavior`
      (`DEFAULT`/`ACCEPT_COMMANDS`/`REJECT_COMMANDS`), `requestQueueSize`, `timeoutOptions`,
      `pingBeforeActivateConnection`. `disconnectedBehavior` is the one that decides whether a
      reconnect window queues commands or fails fast — which is a cache-availability decision.
      `[API]` `[CFG]` `[PROVE]`
3.11.4 **The unbounded request queue as a failure mode**: with `autoReconnect` and a large
      `requestQueueSize`, a Redis blip becomes a memory spike and a thundering flush on reconnect.
      `[TRAP]` `[X-REF 06]`
3.11.5 **Lettuce's `CacheFrontend` / `ClientSideCaching`** as its client-side caching support, and how
      it maps onto § 3.10. `[API]` `[RESEARCH]`
3.11.6 **Jedis**: connection-per-thread, `JedisPool`/`JedisPooled`/`JedisCluster`, Apache Commons Pool
      parameters (`maxTotal`, `maxIdle`, `minIdle`, `maxWait`, `testOnBorrow`,
      `timeBetweenEvictionRuns`), and the sizing rule (`maxTotal` ≥ peak concurrent Redis-using
      threads). `[API]` `[CFG]` `[NUM]`
3.11.7 **`JedisExhaustedPoolException` / borrow timeouts** as the symptom of pool undersizing, and why
      it presents as a latency problem, not an error, until it does not. `[DIAG]` `[X-REF 05]`
3.11.8 **Jedis 5.2's client-side caching** and its cache interface. `[CURRENCY]` `[RESEARCH]`
3.11.9 **Redisson internals worth knowing**: `RMapCache` implements per-entry TTL over a hash plus a
      sorted-set index and a background expiry task — i.e. it *builds* what Redis does not offer, and
      you should know that before relying on it. `RLocalCachedMap`'s invalidation strategies
      (`INVALIDATE`, `UPDATE`, `NONE`, `LOAD`) and its reconnection strategies. `[API]` `[PROVE]`
      `[RESEARCH]`
3.11.10 **Redisson's lock implementation**: a hash holding the owner and reentrancy count, a Lua
      acquire/release, a **watchdog** that renews the lease while the holder lives
      (`lockWatchdogTimeout`), and `RFencedLock` for the fencing token § 2.11.26 says you need.
      `[PROVE]` `[API]` `[RESEARCH]`
3.11.11 **Virtual threads and a cache client**: pinning risk on synchronized sections in older clients,
      and why a per-thread connection model interacts badly with millions of virtual threads.
      `[X-REF 04]` `[X-REF 05]` `[RESEARCH]`
3.11.12 **RESP2 vs RESP3** (`HELLO 3`) — push messages, typed replies, attribute replies, client-side
      caching support, and what changes in your deserialisation when a library switches. `[WIRE]`
      `[VERSION-TRAP]`

## §3.12 Memcached internals

3.12.1 **The slab allocator**: memory divided into 1 MB pages, each assigned to a **slab class** with
      a fixed chunk size, chunk sizes growing by the **growth factor** (`-f`, default 1.25). Nothing
      is ever malloc'd per item. `[PROVE]` `[NUM]` `[CFG]`
3.12.2 **Slab calcification / the slab-class trap**: once pages are assigned to a class they stay
      there, so a workload whose item sizes shift leaves memory stranded in the wrong class and
      evictions occur while `free` memory exists. This is the memcached failure mode nobody predicts.
      `[TRAP]` `[PROVE]`
3.12.3 **`slab_reassign` and `slab_automove`** as the fix — pages can be moved between classes — and
      the fact that they are the recommended startup options. `[CFG]` `[SOURCE]`
3.12.4 **Internal fragmentation**: an item of 100 bytes in a 120-byte chunk wastes 20 bytes, so the
      growth factor is a memory-efficiency knob. Compute the average waste for a given factor.
      `[PROVE]` `[NUM]`
3.12.5 **`stats slabs` and `stats items`** as the way to see all of the above, and `memcached-tool` as
      the reader. `[CLI]` `[DIAG]`
3.12.6 **Segmented LRU (`lru_maintainer`)**: **HOT**, **WARM**, **COLD**, plus a fourth **TEMP** tier.
      New items enter HOT. `[PROVE]` `[SOURCE]`
3.12.7 **HOT as a probationary queue**: items are **never bumped within HOT**; on reaching the tail
      they move to WARM if active or COLD if not. Explain why never bumping is the point — it removes
      the LRU lock from the read path. `[PROVE]` `[SOURCE]`
3.12.8 **"Active" means hit at least twice**, and the `FETCHED`/`ACTIVE` item flags that encode it.
      `[SOURCE]` `[RESEARCH]`
3.12.9 **HOT and WARM are capped as a percentage of the slab class's memory; COLD is uncapped**, with
      the age-ratio rule ("HOT is capped at N% of memory, or 10% of the age of COLD"). The exact
      option names (`hot_lru_pct`, `warm_lru_pct`, `hot_max_factor`, `warm_max_factor`) and values
      could not be confirmed from the primary doc and must be verified against `memcached -o help`
      or the source. `[NUM]` `[CFG]` `[RESEARCH]`
3.12.10 **Items active in COLD are moved immediately to WARM**, which is the promotion path.
      `[SOURCE]`
3.12.11 **`temporary_ttl=N`** routes short-TTL items into the TEMP LRU, where they are **never bumped
      and never moved**, so they cannot displace long-lived data. This is a dedicated answer to a
      problem Redis handles with `volatile-*`. `[CFG]` `[PROVE]` `[SOURCE]`
3.12.12 **`lru_crawler`**: a background reaper that walks LRUs to free expired items, and the point the
      docs make — segmentation lets the crawler learn which segments are worth scanning. `[CFG]`
      `[SOURCE]`
3.12.13 **The throughput payoff**: items are not bumped on fetch, so a 500-key multiget takes no LRU
      lock, and LRU locks are used mostly on sets and by the maintainer thread. This is why memcached
      scales across cores where Redis does not. `[PROVE]` `[SOURCE]`
3.12.14 **The hash table and expansion**, and per-item overhead (`item` header ~48–56 bytes plus key
      plus suffix plus value) — the arithmetic that says memcached is less memory-efficient than a
      Redis listpack hash for tiny values and more predictable for large ones. `[NUM]` `[PROVE]`
      `[RESEARCH]`
3.12.15 **Lazy expiry** — memcached never actively expires without the crawler, so `stats` `curr_items`
      includes logically-expired items. Same class of surprise as § 3.6.3. `[PROVE]`
3.12.16 **`extstore` internals** in one paragraph: value on flash, key and metadata in RAM, with a
      configurable item-age/size threshold for what gets written out. `[RESEARCH]`

## §3.13 Spring Cache proxy internals

3.13.1 **`CacheInterceptor` / `CacheAspectSupport`** as the actual implementation, and the fact that
      the annotations are metadata read by `AnnotationCacheOperationSource` into
      `CacheOperation` objects. `[SOURCE]` `[API]`
3.13.2 **`ProxyCachingConfiguration`**, the `BeanFactoryCacheOperationSourceAdvisor` and the
      pointcut that decides which methods are advised — which is where "only public methods, only
      through the proxy" comes from mechanically rather than as folklore. `[SOURCE]` `[PROVE]`
      `[X-REF 07]`
3.13.3 **The execution order inside the interceptor**, as an ordered trace: collect operations →
      resolve caches → process `@CacheEvict(beforeInvocation = true)` → look for a `@Cacheable` hit →
      on hit, collect puts and evicts and return → on miss, invoke → apply `@CachePut` and
      `@Cacheable` puts subject to `unless` → process remaining evicts. `[FLOW]` `[SOURCE]`
3.13.4 **Why a hit still processes `@CachePut`/`@CacheEvict`** on the same method, and the surprising
      combination that follows.
3.13.5 **`sync = true`'s implementation** — it delegates to `Cache#get(key, Callable)` and therefore
      inherits whatever the provider's coalescing is, which is why support is uneven. `[SOURCE]`
      `[PROVE]`
3.13.6 **`CacheAspectSupport`'s restrictions on `sync`**: one cache only, no `unless`, and
      no combination with other operations. State them as thrown exceptions, not as advice.
      `[API]` `[RESEARCH]`
3.13.7 **`CacheEvaluationContext`** and lazy argument-name resolution, which is why SpEL key
      expressions can reference parameter names at all. `[SOURCE]`
3.13.8 **`SimpleValueWrapper` and the `null` distinction**: `Cache#get` returning `null` means absent,
      returning a wrapper containing `null` means "cached as absent". This is Spring's built-in
      sentinel and the reason `disableCachingNullValues` matters. `[PROVE]` `[API]` `[SOURCE]`
3.13.9 **`RedisCache`'s implementation** of `get`/`put`/`putIfAbsent`/`evict`/`clear`, the `SCAN`-based
      `clear`, and the lock the locking writer takes during `clear`. `[SOURCE]` `[RESEARCH]`
3.13.10 **Where the abstraction costs you performance**: a `SimpleKey` allocation and a SpEL
      evaluation per call, plus a serialiser round trip; measurable at the 1,200/sec stake rate, and
      the reason a hot path sometimes drops to the native client. `[NUM]` `[PROVE]`
3.13.11 **AspectJ mode** as the escape from every proxy limitation, and its cost (weaving, build
      complexity). `[X-REF 07]`

## §3.14 The tiers below your code — buffer pool and page cache

3.14.1 **The DB buffer pool** in one paragraph: pages of the table and index kept in RAM, with its own
      LRU-ish policy, so a "database read" of a hot row never touches disk. Then the pointer for the
      full treatment. `[X-REF 09]`
3.14.2 **Why this matters to a cache decision**: if the working set fits the buffer pool, your
      application cache is saving a network round trip and a query parse, not a disk read — which is
      a much smaller win than the latency table suggests. Compute both. `[PROVE]` `[NUM]`
3.14.3 **PostgreSQL's `shared_buffers` and its clock-sweep with usage counts**, plus the deliberate
      **ring buffer for large sequential scans** so a `VACUUM` or a big scan does not evict the hot
      set — scan resistance, implemented in a database, and worth naming as prior art for § 2.2.5.
      `[PROVE]` `[X-REF 09]` `[RESEARCH]`
3.14.4 **The OS page cache** beneath that, and the double-caching question (`O_DIRECT`, and why
      Postgres relies on the page cache while other engines bypass it). `[X-REF 11]`
3.14.5 **MySQL's query cache was removed in 8.0**, and *why*: a single global mutex and invalidation on
      any write to a referenced table made it a scalability anti-feature. This is the single best
      cautionary tale about caching query results, and it is a `[VERSION-TRAP]` because people still
      recommend it. `[PROVE]` `[VERSION-TRAP]` `[RESEARCH]`
3.14.6 **Materialised views** as the durable, refreshable, transactional alternative to a query cache,
      with its own staleness knob. `[X-REF 09]`
3.14.7 **Prepared-statement and plan caches** as caches with their own invalidation bug class (a plan
      cached for an unrepresentative parameter). `[X-REF 09]`
3.14.8 **CPU L1/L2/L3 and cache lines** as the bottom tier, named for completeness plus the one thing
      that matters upward: **false sharing**, which is exactly the effect Caffeine 3.2.4 fixed in its
      access-expiration timestamp update. `[PROVE]` `[X-REF 05]` `[CURRENCY]`

## §3.15 The proofs and the mathematics

3.15.1 **Average latency and origin-load formulas** derived from first principles, not asserted.
      `[PROVE]`
3.15.2 **Amdahl's law** for the cacheable fraction, with the QuizStakes numbers. `[PROVE]` `[NUM]`
3.15.3 **Little's Law** for cache-tier concurrency and connection-pool sizing (§ 2.1.5). `[PROVE]`
3.15.4 **The utilisation curve** `W = S/(1−ρ)`: at 80% origin utilisation the queue triples the wait,
      which is why a cache flush does not degrade linearly. `[PROVE]` `[NUM]`
3.15.5 **The stampede arithmetic** as a queueing result: concurrent duplicate loads = arrival rate ×
      load latency, so 5,000/sec × 200 ms = 1,000. `[PROVE]`
3.15.6 **Bélády's anomaly** demonstrated on a concrete reference string for FIFO. `[PROVE]`
3.15.7 **LRU's k-competitiveness** and its optimality among deterministic online algorithms.
      `[PROVE]` `[RESEARCH]`
3.15.8 **Count-Min Sketch error bounds**, derived. `[PROVE]`
3.15.9 **Bloom filter false-positive rate** `(1 − e^{−kn/m})^k`, the optimal `k = (m/n)ln2`, and the
      bits-per-element table (10 bits → ~1%, 15 → ~0.1%). `[PROVE]` `[NUM]` `[X-REF 01]`
3.15.10 **HyperLogLog's error** (~0.81% standard error at 12 KB) and why the 12 KB is independent of
      cardinality. `[PROVE]` `[NUM]`
3.15.11 **XFetch's optimality argument**: why an exponentially-distributed early-expiry decision
      weighted by recompute time minimises the expected number of concurrent recomputations.
      `[PROVE]` `[RESEARCH]`
3.15.12 **The staleness-composition bound** across tiers (§ 2.5.11), stated as a sum with the
      invalidation-propagation term included. `[PROVE]`
3.15.13 **Why the dual write cannot be made atomic** without a shared commit protocol — the same
      impossibility as § 14's outbox motivation, argued in cache terms. `[PROVE]` `[X-REF 14]`
3.15.14 **Why exactly-once invalidation is impossible over a lossy channel**, which is the formal
      version of § 2.6.6, and why the TTL is therefore the guarantee. `[PROVE]` `[X-REF 14]`
3.15.15 **Zipf's law and the hit-ratio integral**: with a Zipfian popularity exponent α, the hit ratio
      for a cache holding the top-k keys is computable — which is where "1% of keys, 50% of traffic"
      comes from and how to redo it for your own α. `[PROVE]` `[NUM]` `[RESEARCH]`
3.15.16 **The miss-ratio curve and the knee** as the formal statement of § 1.1.15, and why doubling a
      cache past the knee buys almost nothing. `[PROVE]`
3.15.17 **Consistent hashing's remap fraction** `1/N`, derived, versus modulo hashing's
      `(N−1)/N`. `[PROVE]` `[NUM]`

## §3.16 Memory footprint arithmetic

3.16.1 **One in-process cache entry, byte by byte**: object header, `ConcurrentHashMap.Node`, the
      Caffeine policy fields for the enabled features, the key, the value, and the alignment padding.
      Sum it for a `String` → record entry. `[NUM]` `[PROVE]` `[X-REF 06]`
3.16.2 **One Redis entry, byte by byte** (§ 3.5.17), including the expires-dict entry and jemalloc
      rounding. `[NUM]`
3.16.3 **One memcached item, byte by byte** (§ 3.12.14), including chunk rounding. `[NUM]`
3.16.4 The three compared for a 200-byte value at 1M keys, as a single table — this is the arithmetic
      that decides an instance size. `[TABLE]` `[NUM]` `[PROVE]`
3.16.5 **The frequency sketch's footprint**: 8 bytes per entry, so a 1M-entry Caffeine cache spends
      8 MB on the admission policy. Whether that is worth it, argued. `[NUM]` `[PROVE]`
3.16.6 **The Bloom filter's footprint** for the penetration guard, computed for 2.4M client ids.
      `[NUM]`
3.16.7 **The tag-index footprint**: a Redis set per tag holding key names, which can exceed the cached
      values it indexes. `[NUM]` `[TRAP]`
3.16.8 **The tracking table's footprint** (§ 3.10.3): proportional to keys tracked × clients tracking
      them, which is why `BCAST` exists. `[NUM]` `[PROVE]`
3.16.9 **Heap vs off-heap vs Redis for the same 4 GB**: GC pause impact, serialisation cost, and
      cross-instance sharing, as a decision table with the QuizStakes 30 ms budget as the constraint.
      `[TABLE]` `[NUM]` `[X-REF 06]`
3.16.10 **The COW spike** during a `BGSAVE` on a write-heavy instance, computed. `[NUM]`

## §3.17 The consolidated failure catalogue

3.17.1 Hit ratio slowly declining → working set grew → `evicted_keys`, miss-ratio curve → resize or
      improve admission. `[DIAG]`
3.17.2 Hit ratio collapsed instantly → flush, failover, key-format change, or a deploy that changed
      the key → `keyspace_misses` step change, deploy timeline. `[DIAG]`
3.17.3 Periodic latency spike at a fixed interval → synchronised TTL expiry or a `BGSAVE` schedule →
      `expired_keys` sawtooth, `latest_fork_usec`. `[DIAG]` `[NUM]`
3.17.4 p99 latency spike with p50 flat → hot key, big key, or a blocked event loop → `SLOWLOG`,
      `HOTKEYS`, `--bigkeys`. `[DIAG]`
3.17.5 Origin CPU spike with cache hit ratio unchanged → penetration (misses that never populate) →
      compare miss count against origin query count. `[DIAG]` `[PROVE]`
3.17.6 Writes failing with an OOM error → `maxmemory` reached under `noeviction` or `volatile-*` with
      no TTLs → `INFO memory`, `maxmemory_policy`. `[DIAG]`
3.17.7 Users reporting data "randomly wrong" → multi-instance L1 staleness flapping → per-pod
      comparison, `X-Served-By`-style instrumentation. `[DIAG]` `[PROVE]`
3.17.8 A stale value that never clears → a missed invalidation with no TTL, or a pub/sub message
      missed by a reconnecting subscriber → TTL audit. `[DIAG]`
3.17.9 Deserialisation exceptions across the fleet after a deploy → cached object shape changed
      without a key version bump → § 2.3.7. `[DIAG]`
3.17.10 Cache errors failing user requests → `SimpleCacheErrorHandler`'s rethrow default →
      § 2.9.18. `[DIAG]`
3.17.11 Memory rising while key count is flat → fragmentation, big keys growing, or client output
      buffers → `mem_fragmentation_ratio`, `MEMORY USAGE`, `INFO clients`. `[DIAG]`
3.17.12 Memory not falling after a mass delete → allocator behaviour, not a leak → § 3.5.12.
      `[DIAG]`
3.17.13 Connection-pool exhaustion after a cache blip → the miss path's concurrency (§ 2.1.5), not the
      cache itself. `[DIAG]` `[PROVE]`
3.17.14 A cache that is "up" but slow, timing out at the application → THP, swap, a `KEYS`, a fork, or
      a saturated core → `--latency`, `LATENCY DOCTOR`. `[DIAG]`
3.17.15 Eviction on one Cluster node only → slot imbalance or a hash-tag hotspot → per-node `INFO`,
      slot stats. `[DIAG]`
3.17.16 CDN hit ratio near zero → a `Vary` on a high-cardinality header, or a cookie in the cache key
      → `Cache-Status`, edge logs. `[DIAG]` `[SPEC]`
3.17.17 An authenticated response served to the wrong user → a missing key input or a `public`
      directive → § 1.7.1, § 2.7.9. `[DIAG]`
3.17.18 A cached "not found" outliving the record's creation → negative TTL too long → § 1.6.15.
      `[DIAG]`
3.17.19 A warm-up that never completes blocking a deploy → an unbounded warm-up behind a readiness
      probe → § 2.16.5. `[DIAG]`
3.17.20 Everything correct and the cache still not helping → the origin was never the bottleneck →
      § 2.18.16. `[DIAG]` `[PROVE]`
3.17.21 The full catalogue as one **symptom → cause → metric → fix** table, so it can be read in an
      incident. `[TABLE]` `[METRIC]`

## §3.18 Version history — what changed and why it matters

3.18.1 **Redis 2.2** — small-object encodings (ziplist/intset), the origin of § 3.5's whole section.
3.18.2 **Redis 2.6** — millisecond expiry precision, Lua scripting.
3.18.3 **Redis 3.0** — the eviction candidate pool making sampled LRU near-exact; Cluster GA.
      `[NUM]`
3.18.4 **Redis 4.0** — LFU eviction, `UNLINK`, lazy free, modules.
3.18.5 **Redis 5.0** — Streams.
3.18.6 **Redis 6.0** — RESP3, **client-side caching (tracking)**, ACLs, threaded I/O, TLS.
3.18.7 **Redis 6.2** — `GETEX`, `COPY`, `SINTERCARD`, `OBJECT FREQ`.
3.18.8 **Redis 7.0** — listpack replacing ziplist, `EXPIRE … NX/XX/GT/LT`, Functions, multi-part AOF,
      sharded pub/sub (`SPUBLISH`/`SSUBSCRIBE`).
3.18.9 **Redis 7.2** — `set-max-listpack-*`, and the version Valkey forked from.
3.18.10 **Redis 7.4** — **hash-field TTLs** (`HEXPIRE` family). `[VERSION-TRAP]`
3.18.11 **Redis 8.0** — the unified distribution (Search, JSON, TimeSeries, Bloom in core), major
      performance work. `[CURRENCY]`
3.18.12 **Redis 8.4** — the base 8.6 builds on. `[RESEARCH]`
3.18.13 **Redis 8.6** (Feb 2026) — `allkeys-lrm`/`volatile-lrm`, `HOTKEYS`, `XADD … IDMP/IDMPAUTO`
      with `stream-idmp-duration`/`stream-idmp-maxsize`, `tls-auth-clients-user`,
      `key-memory-histograms`, `cluster-slot-stats-enabled`, unified hash/zset structures, PII hidden
      from ACL and server logs, `repl-diskless-load flushdb`, and the `XADD IDMP` + non-default AOF
      limitation. `[CURRENCY]` `[RESEARCH]`
3.18.14 **The licence timeline** (§ 2.11.47) and the Valkey fork, as the change that most affects
      which engine you are actually running. `[CURRENCY]`
3.18.15 **Valkey 8.x → 9.x** — the performance and threading divergence from Redis, and the fact that
      ElastiCache/Memorystore default to it. `[CURRENCY]` `[RESEARCH]`
3.18.16 **Guava → Caffeine** as a design generation change: lock-per-read to ring buffers, LRU-ish to
      W-TinyLFU.
3.18.17 **Caffeine 2.x → 3.x** (Java 11 baseline) and the 3.2.x line: 3.2.4's access-expiration false
      sharing fix, the async in-flight head-of-line-blocking fix, and JCache
      `ObjectInputFilter` support. `[CURRENCY]` `[RESEARCH]`
3.18.18 **Ehcache 2 → 3** — a total API rewrite and full JSR-107 compliance; why a 2.x example does
      not compile against 3.x. `[VERSION-TRAP]`
3.18.19 **Spring Boot 2.x → 3.x → 4.x** for caching: `javax` → `jakarta`, the auto-configuration
      package move, `CacheManagerCustomizer`'s new home, Jackson 3, and Spring Framework 7's
      baseline. `[VERSION-TRAP]` `[RESEARCH]`
3.18.20 **Spring Data Redis 2.x → 4.x**: `RedisCacheConfiguration` additions
      (`enableStatistics`, `enableTimeToIdle`), the Jedis→Lettuce default switch, and
      `RedisCacheWriter` locking. `[VERSION-TRAP]` `[RESEARCH]`
3.18.21 **Hibernate 5 → 6 → 7** for caching: the region-factory rework, `jakarta.persistence`
      property prefixes, and what a 5.x `hibernate.cache.*` property block does now.
      `[VERSION-TRAP]` `[RESEARCH]`
3.18.22 **HTTP caching's RFC history**: RFC 2616 → RFC 7234 → **RFC 9111**, with RFC 5861, 8246, 9211
      and 9213 as separate extensions, and `Warning`/`Pragma` now deprecated. `[SPEC]`
      `[VERSION-TRAP]`
3.18.23 **MySQL query cache removed in 8.0** (§ 3.14.5). `[VERSION-TRAP]`
3.18.24 **The eviction-research timeline**: LRU (1960s) → ARC (2003) → TinyLFU (2015) → W-TinyLFU
      (2016) → S3-FIFO (2023) → SIEVE (2024), so the reader can place any paper they are handed.
      `[TABLE]` `[RESEARCH]`

---

# PART 4 — BUILD IT

Every implementation is complete, compiling Java 21 (records, sealed types, pattern matching, virtual
threads where relevant) against the QuizStakes domain, and every one is followed by a
**Diff vs the real one** table covering bounds checks, concurrency, memory layout, statistics,
failure handling, and why the real implementation bothers.

4.1.1 **`LruCache<K,V>` on `LinkedHashMap`** — `accessOrder = true`, `removeEldestEntry`, generic,
      with an explicit note on thread safety. The 15-line version, written properly. `[BUILD]`
4.1.2 Diff vs `LinkedHashMap`-based caches in the wild and vs Caffeine: no expiry, no stats, no
      weights, global lock if synchronised, `RemovalCause` absent. `[TABLE]`

4.2.1 **`LruCache<K,V>` from scratch** — an intrusive doubly-linked list plus a `HashMap`, `get`
      promoting to head, `put` evicting from tail, O(1) both. Written without `LinkedHashMap` so the
      mechanism is visible. `[BUILD]`
4.2.2 Diff vs the real one: sentinel nodes, node reuse, `null` policy, iterator invalidation, and why
      a production cache does not do this on the read path at all. `[TABLE]`

4.3.1 **`SegmentedLruCache<K,V>`** — probation and protected segments with promotion on second hit,
      to make § 2.2.7 concrete. `[BUILD]`
4.3.2 Diff vs Caffeine's main space: adaptive sizing, the frequency-based admission in front, and the
      buffered maintenance. `[TABLE]`

4.4.1 **`FrequencySketch`** — a 4-bit Count-Min Sketch over a `long[]`, with `increment`, `frequency`,
      and the halving reset at a size-proportional threshold. `[BUILD]`
4.4.2 Diff vs Caffeine's `FrequencySketch`: seed choice and mixing, table sizing to a power of two,
      the `ensureCapacity` fastpath, and the exact reset accounting. `[TABLE]`

4.5.1 **`TinyLfuCache<K,V>`** — the sketch from 4.4 wired as an **admission** policy in front of the
      LRU from 4.2, with a randomised tie-break. Demonstrates scan resistance in a test. `[BUILD]`
4.5.2 Diff vs W-TinyLFU: the admission window, the SLRU main space, hill climbing, and the lossy read
      buffer. `[TABLE]`

4.6.1 **`SieveCache<K,V>`** — one FIFO queue, a visited bit, a moving hand. Fewer than 40 lines, and
      it beats 4.2 on a Zipfian trace, which is the point. `[BUILD]`
4.6.2 Diff vs the reference implementation and vs CLOCK: hand placement on eviction, no reinsertion,
      and the concurrency story. `[TABLE]`

4.7.1 **`ExpiringCache<K,V>`** — absolute and sliding expiry, lazy eviction on access plus a scheduled
      reaper, with an injected `Clock` so it is testable. `[BUILD]`
4.7.2 Diff vs Caffeine: the hierarchical timer wheel, fixed-order queues for constant durations, the
      `Scheduler` abstraction, and prompt vs access-triggered expiry. `[TABLE]`

4.8.1 **`SingleFlight<K,V>`** — a `ConcurrentHashMap<K, CompletableFuture<V>>` with correct removal on
      completion and on failure, so one loader runs per key and failures are not cached. `[BUILD]`
      `[X-REF 05]`
4.8.2 Diff vs Caffeine's `AsyncLoadingCache` and Guava's `LoadingCache`: in-flight entries in the main
      map, cancellation, executor choice, and exception propagation semantics. `[TABLE]`

4.9.1 **`RedisSingleFlight`** — distributed coalescing with `SET lock:<key> <token> NX PX`, a Lua
      compare-and-delete release, bounded wait-and-recheck for the losers, and stale-serve fallback.
      `[BUILD]`
4.9.2 Diff vs Redisson's `RLock`: reentrancy, the watchdog lease renewal, pub/sub-based waiting instead
      of polling, and `RFencedLock`'s token. Plus the honest note that neither is a correctness lock.
      `[TABLE]`

4.10.1 **`XFetchCache`** — probabilistic early expiration: store value, computed-at, and delta;
      recompute when `now − delta·beta·log(random()) ≥ expiry`. `[BUILD]` `[RESEARCH]`
4.10.2 Diff vs the paper: the estimator for delta, per-key beta tuning, and what happens when the
      recompute time is bimodal. `[TABLE]`

4.11.1 **`AgreementVersionCache`** — the full QuizStakes cache-aside implementation for the agreement
      text: versioned key, jittered TTL, single-flight, serve-stale-on-error, negative sentinel,
      metrics, and a `CacheErrorHandler`-equivalent fall-through. This is the reference
      implementation the whole guide builds toward. `[BUILD]`
4.11.2 Diff vs a naive `@Cacheable` on the same method: which of the eight behaviours the annotation
      gives you and which it does not. `[TABLE]`

4.12.1 **`NearCache<K,V>`** — Caffeine L1 over a Redis L2, per-tier TTLs, per-tier metrics, pub/sub
      invalidation of L1, and a documented worst-case staleness. `[BUILD]`
4.12.2 Diff vs Redisson's `RLocalCachedMap` and Redis client-side caching: invalidation strategies,
      reconnection handling, and the placeholder that closes § 3.10.15's race. `[TABLE]`

4.13.1 **`TrackingNearCache`** — the same near cache built on RESP3 `CLIENT TRACKING` with
      `BCAST PREFIX`, including the flush-on-disconnect and the periodic `PING`. `[BUILD]`
      `[RESEARCH]`
4.13.2 Diff vs Jedis 5.2's and Lettuce's built-in client-side caching: what the library does for you
      and what it leaves to you. `[TABLE]`

4.14.1 **`TagIndexedCache`** — Redis sets as tag indexes so `RestrictionApplied` can invalidate
      everything cached for one client, with the reaper that stops the index leaking. `[BUILD]`
4.14.2 Diff vs a CDN's surrogate keys and vs `@CacheEvict(allEntries = true)`: atomicity, cost, and
      what happens to a tag whose keys have already expired. `[TABLE]`

4.15.1 **`GenerationCache`** — epoch/generation-counter invalidation: read `gen:agreements`, prefix
      with it, `INCR` to invalidate a whole class atomically. `[BUILD]`
4.15.2 Diff vs versioned keys in code: one extra round trip, runtime invalidation without a deploy,
      and the memory left behind. `[TABLE]`

4.16.1 **`NegativeCachingRepository`** — the sentinel pattern done correctly, with a distinct sentinel
      type, a short jittered negative TTL, and a Bloom pre-filter for the unbounded-id case.
      `[BUILD]`
4.16.2 Diff vs returning `Optional.empty()` from a naive cache and vs Spring's
      `SimpleValueWrapper(null)`: how each distinguishes absent-from-cache from cached-as-absent.
      `[TABLE]`

4.17.1 **`BloomFilter`** — a from-scratch bit-array Bloom filter with computed optimal `m` and `k`,
      sized for 2.4M client ids at 1% FPR, plus a measured FPR test. `[BUILD]` `[X-REF 01]`
4.17.2 Diff vs Guava's `BloomFilter` and Redis's `BF.*`: hashing strategy, serialisation, thread
      safety, and scalable/counting variants. `[TABLE]`

4.18.1 **`StampedeSafeLoader` as a Spring component** — `@Cacheable(sync = true)` versus the explicit
      implementation, side by side, with a concurrency test proving one loader invocation. `[BUILD]`
      `[X-REF 16]`
4.18.2 Diff: what `sync = true` covers (one JVM, one cache, no `unless`) and what the explicit version
      adds (cross-instance, stale-serve, metrics). `[TABLE]`

4.19.1 **`CacheConfig`** — the complete QuizStakes Spring configuration: two `CacheManager`s behind a
      `CompositeCacheManager`, `TransactionAwareCacheManagerProxy`, per-cache TTLs, a JSON serialiser,
      a logging fall-through `CacheErrorHandler`, `enableStatistics`, and Micrometer binding.
      `[BUILD]`
4.19.2 Diff vs Boot's auto-configuration: what `spring.cache.*` alone gives you and every gap this
      fills. `[TABLE]`

4.20.1 **`CacheWarmupIndicator`** — readiness-gated warm-up with a timeout, wired to
      `/actuator/health/readiness` and explicitly excluded from liveness. `[BUILD]` `[X-REF 19]`
4.20.2 Diff vs a `@PostConstruct` loader and an `ApplicationRunner`: when traffic arrives relative to
      when the cache is warm. `[TABLE]`

4.21.1 **`HttpCachingController`** — a Spring MVC endpoint set demonstrating `CacheControl` for each
      QuizStakes case: `immutable` versioned agreement document, `no-cache` projection with an ETag via
      `checkNotModified`, `no-store` money endpoint, and `stale-while-revalidate` on the composite.
      `[BUILD]`
4.21.2 Diff vs `ShallowEtagHeaderFilter`: bandwidth saved versus work saved, and why the version-column
      ETag is strictly better. `[TABLE]`

4.22.1 **`SlidingWindowRateLimiter`** — a Redis sorted set keyed to the identity vendor's 600/min
      estate-wide cap, in one Lua script for atomicity. The cache-adjacent build that the scenario
      explicitly demands. `[BUILD]` `[NUM]`
4.22.2 Diff vs a token bucket, a fixed window, and `RRateLimiter`: memory per client, boundary
      behaviour, and cluster-slot constraints. `[TABLE]`

4.23.1 **`CacheMetrics`** — a Micrometer binder exposing hit ratio, load latency, eviction cause
      breakdown and invalidation rate for both tiers, with the cardinality rules enforced. `[BUILD]`
      `[X-REF 20]`
4.23.2 Diff vs `CaffeineCacheMetrics`: what the built-in binder reports and what it omits. `[TABLE]`

4.24.1 **`CacheTest`** — the four tests from § 2.17: used, invalidated, fails open, coalesces; with an
      injected `Ticker` and a Testcontainers Redis. `[BUILD]` `[X-REF 16]`
4.24.2 Diff vs the typical cache test in the wild: no `Thread.sleep`, no shared static cache, and an
      assertion on origin invocations rather than on latency. `[TABLE]`

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "Walk me through cache-aside, on the whiteboard." — the read path, the write path, and the race,
      in that order.
5.1.2 "Two requests miss the same key at the same moment. What happens?" — the stampede, and the four
      mitigations ranked by cost. **This is the question the guide was written for.**
5.1.3 "What should the cache key contain?" — every input that changes the output, with the forgotten
      list.
5.1.4 "You update a row. How does the cache find out?" — the six invalidation strategies and the
      coupling argument.
5.1.5 "Why delete instead of update?" — the two-writer interleaving.
5.1.6 "Is there still a race after you delete?" — yes, § 1.5.12, drawn.
5.1.7 "How would you fix it?" — the ranked mitigation list, ending honestly at "you cannot close it
      without a shared transaction".
5.1.8 "What TTL would you pick, and why?" — the harm question, then jitter.
5.1.9 "Your cache just got flushed. What happens?" — the cliff, the arithmetic, and the origin
      protection you should already have.
5.1.10 "How do you size a cache?" — working set, miss-ratio curve, measured object size, headroom.
5.1.11 "What is your hit ratio and is it good?" — the answer is "compared to what", plus the p99
      caveat.
5.1.12 "LRU or LFU?" — scan pollution, decay, and then W-TinyLFU/SIEVE if the interviewer wants depth.
5.1.13 "How does Redis actually evict?" — sampling, the pool, `maxmemory-samples`, the LFU Morris
      counter.
5.1.14 "Redis is single-threaded. Is that a problem?" — atomicity for free, one slow command stalls
      everyone, and the hot-key consequence.
5.1.15 "What does `KEYS *` do on a 50 GB instance?" — and what you use instead.
5.1.16 "Is Redis durable?" — RDB minutes, AOF `everysec` one second, async replication, managed
      defaults, and therefore never a system of record.
5.1.17 "How do you invalidate an in-process cache across ten pods?" — pub/sub as an optimisation, TTL
      as the guarantee, Kafka or tracking if you need reliability.
5.1.18 "Design a two-tier cache." — sizes, TTLs, invalidation, metrics per tier, worst-case staleness.
5.1.19 "What would you never cache?" — the authorisation answer, with invariant 12 named.
5.1.20 "A client self-excludes and stakes 200 ms later. What must be true?" — the 500 ms budget, and
      why no cache survives it.
5.1.21 "How do you stop an attacker from bypassing your cache?" — penetration, negative caching, Bloom
      filter, and key validation.
5.1.22 "One key is getting 500k requests/sec. What do you do?" — L1 shielding first, then key
      splitting, then replicas.
5.1.23 "Your p99 spiked but p50 is flat. Where do you look?" — the § 3.17.4 path.
5.1.24 "What HTTP headers would you set on this endpoint?" — per-endpoint, with `private`/`no-store`
      reasoning.
5.1.25 "What is the difference between `no-cache` and `no-store`?" — the single most reliable HTTP
      caching discriminator.
5.1.26 "What does `Vary: Cookie` do to your CDN?" — and what to do instead.
5.1.27 "How does `ETag` save you work, and how does it not?" — the generate-before-render trap.
5.1.28 "Explain `@Cacheable` to me. What does it compile to?" — the interceptor, the key generator, the
      proxy.
5.1.29 "Why did `@Cacheable` not work?" — self-invocation, non-public method, missing `@EnableCaching`,
      wrong `CacheManager`, or an exception rethrown by the error handler.
5.1.30 "Does `sync = true` protect you across instances?" — no, and why people think it does.
5.1.31 "Should you use Hibernate's second-level cache?" — the multi-writer argument, and `READ_ONLY`
      as the one safe case.
5.1.32 "Redis or Memcached?" — the honest decision table, plus the one case for memcached.
5.1.33 "Is Redis a good queue / lock / session store?" — three separate answers with their guarantee
      levels. `[X-REF 14]`
5.1.34 "How do you test a cache?" — the four assertions, and never on timing.
5.1.35 "How do you warm a cache without serving an empty one?" — readiness gating.
5.1.36 "What does your cache do when Redis is down?" — fail open for reads, fail closed for
      enforcement, and the `CacheErrorHandler` that makes it so.
5.1.37 "Draw the whole QuizStakes caching architecture." — the tier map, the never-cache list, and the
      staleness contract table. The synthesis question.
5.1.38 The **three-axis trade-off drills**: (a) L1+L2 vs L2 only — latency, consistency, operational
      cost; (b) short TTL vs event invalidation — freshness, coupling, failure mode; (c) cache the
      composite vs cache the parts — round trips, invalidation blast radius, memory. Each with a full
      answer. `[TABLE]`
5.1.39 The 60-second verbal answer to "how would you cache a regulated payments platform", using
      QuizStakes end to end and leading with what you refuse to cache.
5.1.40 Twelve self-quiz questions whose answers are **numbers**, so recall is testable: default
      `maxmemory-policy`, `maxmemory-samples`, `lfu-log-factor`, `lfu-decay-time`, cluster slot count,
      `hash-max-listpack-value`, the Caffeine sketch's bits and bytes-per-entry, the HLL error and
      size, RFC 9111's response-directive count, the `max-age` one-year value, the hit-ratio table's
      90%/99% origin-load figures, and the QuizStakes self-exclusion budget. `[NUM]`

## §5.2 The trap list — the wrong belief, then the correction

5.2.1 A cache makes things faster. **A cache with a low hit ratio makes things slower.** `[TRAP]`
5.2.2 Hit ratio is the metric. **Miss latency at p99 is usually the metric.** `[TRAP]`
5.2.3 90% is a good hit ratio. **For the origin, 90% means ten times the load of 99%.** `[TRAP]`
5.2.4 We can survive losing the cache. **Only if you have load-tested it.** `[TRAP]`
5.2.5 Update the cache on write. **Delete it — two concurrent updates can latch a stale value.**
      `[TRAP]`
5.2.6 Delete-on-write eliminates staleness. **A reader that already missed can repopulate a stale
      value after your delete.** `[TRAP]`
5.2.7 Invalidation inside the transaction is safest. **It lets a reader repopulate pre-commit state.**
      `[TRAP]`
5.2.8 We invalidate properly, so we do not need a TTL. **The TTL is for the invalidation you missed.**
      `[TRAP]`
5.2.9 A TTL is an eviction mechanism. **It is a correctness backstop.** `[TRAP]`
5.2.10 Identical TTLs are fine. **They synchronise a stampede with a period equal to the TTL.**
      `[TRAP]`
5.2.11 Sliding expiry keeps data fresh. **A permanently-hot key never expires and never refreshes.**
      `[TRAP]`
5.2.12 Expired means gone. **It means "will be removed when noticed"; the memory is still yours.**
      `[TRAP]`
5.2.13 Eviction and expiry are the same. **A key can be evicted long before its TTL.** `[TRAP]`
5.2.14 Redis's default eviction policy evicts. **`noeviction` makes writes fail.** `[TRAP]`
5.2.15 `volatile-lru` is a safe default. **With keys that have no TTL it degenerates to
      `noeviction`.** `[TRAP]`
5.2.16 Redis LRU is real LRU. **It is sampled, with a candidate pool.** `[TRAP]`
5.2.17 Redis has eight eviction policies. **Ten, since 8.6 added `allkeys-lrm` and `volatile-lrm`.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.18 You cannot expire a hash field. **`HEXPIRE` since 7.4.** `[TRAP]` `[VERSION-TRAP]`
5.2.19 `INCR` on a key with a TTL clears the TTL. **`SET` does; in-place mutations do not.** `[TRAP]`
5.2.20 Redis is BSD-licensed. **SSPL/RSAL since March 2024, AGPLv3 added May 2025 — and your managed
      service is probably running Valkey.** `[TRAP]` `[VERSION-TRAP]`
5.2.21 Redis is single-threaded, so it is slow. **It does millions of ops/sec; the problem is that one
      slow command stalls all of them.** `[TRAP]`
5.2.22 Every Redis command is O(1). **`KEYS`, `SMEMBERS`, `HGETALL`, `LRANGE` and big-key `DEL` are
      not.** `[TRAP]`
5.2.23 `SCAN` with a `MATCH` pattern is cheap. **`MATCH` filters after fetching; you still walk the
      keyspace.** `[TRAP]`
5.2.24 `SCAN` gives a consistent snapshot. **It guarantees only elements present throughout, and may
      repeat.** `[TRAP]`
5.2.25 `DEL` is fine for a big collection. **`UNLINK` frees on a background thread.** `[TRAP]`
5.2.26 `MULTI`/`EXEC` is a transaction with rollback. **Queued commands, no rollback, no isolation
      level.** `[TRAP]`
5.2.27 Redis can join my database transaction. **It cannot — no XA, no 2PC, no rollback.** `[TRAP]`
5.2.28 Redis persistence means no data loss. **RDB loses minutes, AOF `everysec` loses a second,
      replication is async, and managed instances often have it off.** `[TRAP]`
5.2.29 A cache needs persistence. **For a pure cache, turning it off removes forks, COW spikes and
      `fsync` latency.** `[TRAP]`
5.2.30 Redis pub/sub delivers invalidations reliably. **Fire-and-forget: a disconnected subscriber
      misses them forever, silently.** `[TRAP]`
5.2.31 Keyspace notifications are a reliable event source. **They ride pub/sub, and `expired` fires on
      removal, not on expiry.** `[TRAP]`
5.2.32 Client-side caching removes the need for a TTL. **Redis's own docs say put a max TTL on every
      locally cached key.** `[TRAP]`
5.2.33 `CLIENT TRACKING` with two prefixes lets me scope precisely. **Overlapping prefixes are
      rejected.** `[TRAP]`
5.2.34 The invalidation channel is a broadcast. **Only the redirected connection receives it.**
      `[TRAP]`
5.2.35 Redis Cluster is consistent hashing. **It is fixed 16,384 slots, reassigned rather than
      rehashed.** `[TRAP]`
5.2.36 Multi-key commands work in Cluster. **Not across slots — `CROSSSLOT`, unless you hash-tag.**
      `[TRAP]`
5.2.37 `MOVED` and `ASK` mean the same thing. **One updates your slot map; the other must not.**
      `[TRAP]`
5.2.38 Pool your Lettuce connections for throughput. **One multiplexed connection pipelines; pooling
      can make it slower.** `[TRAP]`
5.2.39 A Redis blip is harmless because we auto-reconnect. **An unbounded request queue turns it into a
      memory spike and a reconnect flood.** `[TRAP]`
5.2.40 Redlock makes a lock safe. **No fencing token, and it assumes bounded delay, pauses and clock
      error. Efficiency lock, not correctness lock.** `[TRAP]`
5.2.41 In-process caching is just faster caching. **It is per-instance and therefore incoherent; users
      see values flap.** `[TRAP]`
5.2.42 Uniform staleness and flapping are equally bad. **Flapping is far more confusing to users and
      to you.** `[TRAP]`
5.2.43 A near cache with pub/sub invalidation is consistent. **The TTL is the guarantee; pub/sub is the
      optimisation.** `[TRAP]`
5.2.44 Two 60-second tiers give a 60-second worst case. **They compose to 120.** `[TRAP]`
5.2.45 `softValues` gives you a self-tuning cache. **It gives the GC control of your hit rate, and an
      avalanche when it collects.** `[TRAP]`
5.2.46 A `HashMap` is a fine cache. **Unbounded, no expiry, no stats — an OOM with a delay.**
      `[TRAP]`
5.2.47 Guava's cache expires entries in the background. **Maintenance happens on calling threads.**
      `[TRAP]`
5.2.48 Caffeine's window is 1% of the cache. **It is hill-climbed at runtime.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.49 W-TinyLFU is an eviction policy. **It is an admission policy in front of one.** `[TRAP]`
5.2.50 LFU fixes everything LRU gets wrong. **Without decay it locks in yesterday's popularity.**
      `[TRAP]`
5.2.51 FIFO is obviously worse than LRU. **It has no Bélády-anomaly-free guarantee but is competitive
      on real traces, and SIEVE beats LRU while being simpler.** `[TRAP]` `[RESEARCH]`
5.2.52 More cache is always better. **Past the knee of the miss-ratio curve you are paying for
      nothing.** `[TRAP]`
5.2.53 `@Cacheable` on a method in the same class works. **Self-invocation bypasses the proxy,
      silently.** `[TRAP]`
5.2.54 `@Cacheable` works on private methods. **Proxy mode advises public methods only.** `[TRAP]`
5.2.55 `@Cacheable(sync = true)` is a distributed lock. **It coalesces within one JVM, on providers
      that support it.** `[TRAP]`
5.2.56 A Redis timeout will fall through to the database. **`SimpleCacheErrorHandler` rethrows by
      default.** `[TRAP]`
5.2.57 The default key generator is safe. **It cannot see the principal, tenant or locale, so it
      silently omits them.** `[TRAP]`
5.2.58 `@CacheEvict` runs even if the method throws. **Only with `beforeInvocation = true`.**
      `[TRAP]`
5.2.59 `condition` and `unless` are the same with inverted logic. **`condition` runs before
      invocation; `unless` runs after and can see `#result`.** `[TRAP]`
5.2.60 Hibernate's L2 cache keeps up with the database. **Only with writes made through Hibernate —
      native SQL, migrations and other services leave it stale.** `[TRAP]`
5.2.61 The Hibernate query cache speeds up queries. **It caches id lists and is invalidated by any
      write to a referenced table; it is usually a net loss.** `[TRAP]`
5.2.62 Caching a collection caches the entities. **It caches identifiers; without entity caching you
      still get N selects.** `[TRAP]`
5.2.63 `no-cache` means do not cache. **It means store and revalidate; `no-store` means do not
      store.** `[TRAP]`
5.2.64 No cache headers means no caching. **Heuristic freshness applies.** `[TRAP]`
5.2.65 `public`/`private` is a hint. **It is an access-control decision — `public` on an authenticated
      response leaks it.** `[TRAP]`
5.2.66 `Vary` is harmless metadata. **It multiplies your cache entries by the varied headers'
      cardinality.** `[TRAP]`
5.2.67 A `304` costs nothing. **It is still a full round trip.** `[TRAP]`
5.2.68 `stale-while-revalidate` is in RFC 9111. **RFC 5861. `immutable` is 8246, `Cache-Status` is
      9211, `CDN-Cache-Control` is 9213.** `[TRAP]` `[SPEC]`
5.2.69 Purging is how you invalidate a CDN. **Changing the URL is; purge is the fallback.** `[TRAP]`
5.2.70 Only `200` responses are cached. **`404`, `301`, `410` and others are heuristically
      cacheable — HTTP does negative caching for you.** `[TRAP]`
5.2.71 Negative caching means caching `null`. **It means caching a distinct sentinel; `null` cannot be
      distinguished from a miss.** `[TRAP]`
5.2.72 A long negative TTL is harmless. **It turns a creation race into "your new item doesn't
      exist".** `[TRAP]`
5.2.73 A Bloom filter can be updated freely. **You cannot delete from a standard one.** `[TRAP]`
5.2.74 Write-through keeps the cache and DB consistent. **It is still a dual write with no shared
      transaction.** `[TRAP]`
5.2.75 Write-behind is a performance optimisation. **For business data it is an unbacked primary
      store.** `[TRAP]`
5.2.76 Memcached wastes less memory than Redis. **Slab calcification can strand memory while evicting
      live items.** `[TRAP]`
5.2.77 Memcached actively expires items. **Only lazily, and via `lru_crawler`.** `[TRAP]`
5.2.78 Memcached's LRU is a single list. **HOT/WARM/COLD plus TEMP, with items never bumped in HOT.**
      `[TRAP]`
5.2.79 Fragmentation ratio above 1 means a leak. **After a peak it means the allocator kept the
      pages.** `[TRAP]`
5.2.80 Set `maxmemory` to the container limit. **Leave headroom for buffers and COW, or be OOM-killed
      instead of evicting.** `[TRAP]`
5.2.81 Restriction state can be cached or projected for a decision. **Scenario invariant 12 forbids it
      — read live, every time.** `[TRAP]`
5.2.82 `BalanceView` can authorise a stake. **It serves display and preview only; the ledger serves
      decisions.** `[TRAP]`
5.2.83 The cache is a database if you turn on persistence. **It is a cache with a slow restart.**
      `[TRAP]`
5.2.84 A cache hides a slow query. **Until the first miss after a deploy, at full traffic.** `[TRAP]`

## §5.3 The one-line assertions to recall under pressure

5.3.1 The **cheat sheet** of every constant and default in the file on one screen, grouped by system:
      Redis (policies, samples, LFU factors, encodings, slots, `hz`), Caffeine (sketch bits, bytes per
      entry, fastpath threshold), memcached (growth factor, item limit, LRU segments), HTTP (directive
      lists, one-year `max-age`), Spring (annotation attributes, defaults). `[TABLE]` `[NUM]`
5.3.2 The **master cost table**, reproduced. `[TABLE]`
5.3.3 The **hit-ratio economics table**, reproduced — the one table to be able to redraw from memory.
      `[TABLE]`
5.3.4 The **decision tree from requirement to cache placement and pattern**, on one page. `[FLOW]`
5.3.5 The **failure-mode → symptom → metric → fix** table, on one page. `[TABLE]`
5.3.6 The **never-cache list** with the invariant that forbids each item. `[TABLE]`
5.3.7 The **staleness contract table** for QuizStakes, as the artifact to point at in a design review.
      `[TABLE]`
5.3.8 The **six sentences that carry the whole topic**: a cache trades memory and staleness for
      latency and origin load; hit ratio matters to the origin, not the user, and its collapse is a
      cliff; delete on write, and know the race that remains; every entry gets a jittered TTL because
      invalidation will be missed; one loader per key or a single expiring key takes down a database;
      and anything that authorises an action is read live.
5.3.9 The **anti-checklist**: six things to say you would *not* do, because refusing to cache the
      wrong thing is the strongest signal in a caching interview.

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| Redis — Key eviction (fetched as reference text) | https://redis.io/docs/latest/develop/reference/eviction/ | The complete ten-policy list including `allkeys-lrm`/`volatile-lrm`; `maxmemory` semantics; `mem_not_counted_for_evict`; the `volatile-*`-degenerates-to-`noeviction` rule; the approximated-LRU candidate pool since 3.0; `maxmemory-samples 5`; LFU as a Morris counter with `lfu-log-factor 10` / `lfu-decay-time 1` and the factor→hits table; the `keyspace_hits/(hits+misses)` formula; `evicted_keys` / `expired_keys` / `used_memory_dataset` / `current_eviction_exceeded_time` diagnostics; the LRM read-vs-write timestamp distinction |
| Redis 8.6 "What's new" | https://redis.io/docs/latest/develop/whats-new/8-6/ | `volatile-lrm`/`allkeys-lrm`; `HOTKEYS`; `XADD IDMP`/`IDMPAUTO` with `stream-idmp-duration`/`stream-idmp-maxsize`; `tls-auth-clients-user`; `key-memory-histograms` and `db0_distrib_*_sizes`; `cluster-slot-stats-enabled`; unified hash/zset field-value structures; PII hidden from ACL and server logs; `repl-diskless-load flushdb`; the `XADD IDMP` + non-default-AOF limitation; `acl_access_denied_tls_cert` |
| Redis 8.6 release announcement (secondary, for dates and figures) | https://redis.io/blog/announcing-redis-86-performance-improvements-streams/ | Feb 2026 release timing; the 3.5M ops/sec at pipeline 16 and >5× vs 7.2 claim — **to be re-verified before it is quoted as a number** |
| Redis — Memory optimization | https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/memory-optimization/ | The encoding directives and their documented defaults per version band (`hash-max-ziplist-*` ≤6.2, `hash-max-listpack-entries 512` / `-value 64`, `zset-max-listpack-entries 128` / `-value 64`, `set-max-intset-entries 512`, `set-max-listpack-entries 128` / `-value 64` from 7.2); one-way conversion on overflow; the 10×/5× saving claim; the hash-bucketing trick and its 11 MB → 1.7 MB measurement; 32-bit builds; the allocator's failure to return memory, provision-for-peak, and why `mem_fragmentation_ratio` is unreliable after a peak. **Note the docs/`redis.conf` disagreement on `hash-max-listpack-entries` (512 vs 128) — verify with `CONFIG GET`** |
| Redis — `EXPIRE` command reference | https://redis.io/docs/latest/commands/expire/ | `NX`/`XX`/`GT`/`LT` (7.0+) and the infinite-TTL treatment of non-volatile keys for `GT`/`LT`; which commands clear a TTL and which do not; expiry accuracy 0–1 ms since 2.6; absolute-timestamp storage and the clock-desync hazard; passive plus sampled-active expiry; the synthesised `DEL` in the AOF and replication link; replicas not expiring independently but expiring after promotion; non-positive TTL producing a `del` event rather than `expired` |
| Redis — Client-side caching introduction | https://redis.io/docs/latest/develop/clients/client-side-caching/ | Tracking as the invalidation mechanism; flush-on-disconnect including pool connections; the supported-client table (Jedis 5.2.0, redis-py 5.1.0, node-redis 5.1.0, go-redis 9.22.0) and the warning that `CLIENT TRACKING` support ≠ CSC support; which commands are cacheable and the exclusions; the per-command caching granularity rules including `MGET` key ordering; the separate-connection-for-write-hot-data and cache-sizing (10 MB ÷ 80 B ≈ 131,072) guidance |
| Redis — Client-side caching reference | https://redis.io/docs/latest/develop/reference/client-side-caching/ | The Invalidation Table and its client-ID/no-GC design; the single cross-database key namespace; table-overflow fabricating invalidations; the full `CLIENT TRACKING` option set (`REDIRECT`, `PREFIX`, `BCAST`, `OPTIN`, `OPTOUT`, `NOLOOP`); the RESP2 two-connection wire trace and `__redis__:invalidate`; the pub/sub-is-a-trick point; array payloads and `null` on flush; invalidation on write, expiry **and** eviction; `CLIENT CACHING YES` and its `MULTI`/Lua scope; `CLIENT UNTRACKING`; the Prefixes Table and the non-overlapping-prefix rule; `NOLOOP`'s untracking side effect; the redirection race and the `caching-in-progress` placeholder fix; flush-and-`PING`-on-disconnect; the max-local-TTL recommendation |
| Redis — Redis Cluster specification | https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/ | 16,384 slots, `CRC16(key) mod 16384`, hash tags, `MOVED` vs `ASK` and `ASKING`, slot migration, epochs, `PFAIL`→`FAIL`, `cluster-require-full-coverage` |
| Caffeine — Design wiki | https://github.com/ben-manes/caffeine/wiki/Design | W-TinyLFU as admission window + main space; the 4-bit CountMinSketch at 8 bytes per entry; **adaptive window sizing by hill climbing** (not a fixed percentage); the <50%-occupancy uninitialised-sketch fastpath; the striped lossy read ring buffer with contention-driven stripe growth; the growable chunked write buffer that never loses writes; lock amortisation via batched single-consumer draining; the alive/retired/dead state machine; the hierarchical TimerWheel for variable expiry; feature-driven code generation to cut per-entry fields |
| Caffeine releases / Maven metadata | https://github.com/ben-manes/caffeine/releases and https://mvnrepository.com/artifact/com.github.ben-manes.caffeine/caffeine | Version line and dates: 3.2.0 (17 Jan 2025), 3.2.1, 3.2.2, 3.2.3 (28 Oct 2025), **3.2.4 (4 May 2026)**; 3.2.4's access-expiration false-sharing fix, the async in-flight expiration head-of-line-blocking fix, and JCache `ObjectInputFilter` support |
| TinyLFU paper (Einziger, Friedman, Manes) | https://atsjp.github.io/JavaLearnMap/Java/Cache/Caffeine.assets/TinyLFU_PDP2014.pdf | TinyLFU as an admission policy; the sketch-plus-doorkeeper design; the reset/aging argument; the sample-size guidance |
| SIEVE — NSDI '24 paper and USENIX write-up | https://www.usenix.org/system/files/nsdi24-zhang-yazhuo.pdf and https://www.usenix.org/publications/loginonline/sieve-cache-eviction-can-be-simple-effective-and-scalable | The algorithm (one FIFO, one visited bit, a moving hand, no reinsertion); lazy promotion and quick demotion as the unifying principles; lower miss ratio than nine algorithms on >45% of 1,559 traces; 17%/125% higher throughput than optimised LRU at 1/16 threads; <20 lines of change in five production libraries; the S3-FIFO contrast |
| Harvard "Why FIFO is (almost) all you need" | https://systems.seas.harvard.edu/blog/fifo-is-all-you-need/ | S3-FIFO's small/main/ghost structure and the "most objects are never reused" observation |
| Vattani et al., *Optimal Probabilistic Cache Stampede Prevention* (VLDB 2015) | http://www.vldb.org/pvldb/vol8/p886-vattani.pdf | XFetch; the delta (recompute time) and beta parameters; the exponential early-expiry criterion. **The exact inequality must be taken from the paper, not from the blog restatements** |
| RFC 9111 — HTTP Caching | https://www.rfc-editor.org/rfc/rfc9111.txt | Section structure; the seven request and ten response directives with their subsection numbers; the header fields defined (`Age`, `Cache-Control`, `Expires`, `Pragma`, `Warning`); freshness-lifetime precedence (§ 4.2.1) and heuristic freshness (§ 4.2.2); the full age-calculation term list (§ 4.2.3); validators and conditional-request fields (§ 4.3.1) |
| RFC 5861 — Cache-Control Extensions for Stale Content | https://www.rfc-editor.org/rfc/rfc5861.html | `stale-while-revalidate` and `stale-if-error`, and the `max-age=600, stale-while-revalidate=30` worked example |
| RFC 8246 — HTTP Immutable Responses | https://www.rfc-editor.org/rfc/rfc8246.html | `immutable` semantics and the no-revalidation-during-freshness rule |
| RFC 9211 — The Cache-Status HTTP Response Header Field | https://www.rfc-editor.org/rfc/rfc9211.html | Structured-field list semantics and the origin-first / user-last member ordering |
| RFC 9213 — Targeted HTTP Cache Control | https://www.rfc-editor.org/rfc/rfc9213.html | The `<target>-Cache-Control` convention and `CDN-Cache-Control`; the observation that existing directives target inconsistently |
| Spring Framework — Cache Abstraction reference | https://docs.spring.io/spring-framework/reference/integration/cache.html | Every attribute of `@Cacheable`/`@CachePut`/`@CacheEvict`/`@Caching`/`@CacheConfig`/`@EnableCaching`; `SimpleKeyGenerator`/`SimpleKey`; `CacheResolver`/`SimpleCacheResolver`; `CacheErrorHandler`; the JSR-107 annotation set; the public-methods-and-proxy constraint; the `sync=true` support caveat |
| Spring Boot — Caching reference and API | https://docs.spring.io/spring-boot/reference/io/caching.html and https://docs.spring.io/spring-boot/api/java/org/springframework/boot/cache/autoconfigure/CacheAutoConfiguration.html | `spring.cache.type`, provider auto-detection, `CacheManagerCustomizer`, and the **Boot 4.x package move** to `org.springframework.boot.cache.autoconfigure` |
| Spring Boot / Framework release blogs | https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/ , https://spring.io/blog/2026/06/10/spring-boot-4/ , https://spring.io/blog/2025/11/13/spring-framework-7-0-general-availability/ | Boot 4.0.0 GA 20 Nov 2025, 4.1.0 GA 10 Jun 2026, 4.1.1 Aug 2026, 4.0.8 patch line; Framework 7.0 GA Nov 2025 and the 7.0.x patch cadence; Java 17 baseline through Java 26 |
| Spring Data Redis API — `RedisCacheConfiguration` / `RedisCacheManager` / `CacheKeyPrefix` | https://docs.spring.io/spring-data-redis/reference/api/java/org/springframework/data/redis/cache/RedisCacheConfiguration.html and .../RedisCacheManager.RedisCacheManagerBuilder.html | `entryTtl` (and `Duration.ZERO` = eternal), `computePrefixWith`, `disableCachingNullValues` and its exact behaviour, `enableStatistics` + `RedisCache#getStatistics()`, `CacheKeyPrefix.compute` and the double-colon default; current version line 4.1.x |
| Hibernate — `CacheConcurrencyStrategy` javadoc and Vlad Mihalcea's strategy series | https://docs.jboss.org/hibernate/orm/6.0/javadocs/org/hibernate/annotations/CacheConcurrencyStrategy.html and https://vladmihalcea.com/how-does-hibernate-read_write-cacheconcurrencystrategy-work/ | The four strategies and their guarantees; `READ_WRITE`'s soft-lock mechanism; `NONSTRICT_READ_WRITE`'s no-lock invalidation; `TRANSACTIONAL`'s XA requirement; the READ_ONLY-for-reference-data / READ_WRITE-for-the-rest guidance |
| JSR-107 javadoc and the Ehcache 3 JSR-107 provider docs | https://ignite.apache.org/jcache/1.0.0/javadoc/javax/cache/package-summary.html and https://www.ehcache.org/documentation/3.0/107.html | The five core interfaces; `ExpiryPolicy` on creation/access/modification; `CacheLoader`/`CacheWriter` for read/write-through; the four `CacheEntry*Listener` sub-interfaces; `EntryProcessor` for atomic lock-free compound operations; Ehcache 3's compliance |
| memcached — `doc/new_lru.txt` | https://github.com/memcached/memcached/blob/master/doc/new_lru.txt | `lru_maintainer`; HOT/WARM/COLD plus TEMP; new items entering HOT and never being bumped within it; "items hit at least twice are considered active"; items active in COLD moving immediately to WARM; HOT/WARM capped by percentage with the 10%-of-COLD's-age rule and COLD uncapped; `temporary_ttl` routing to a never-bumped TEMP LRU; `lru_crawler`'s per-segment selectivity; the no-LRU-lock-on-read throughput argument. **`hot_lru_pct` / `warm_lru_pct` / `hot_max_factor` / `warm_max_factor` and the `FETCHED`/`ACTIVE` flags were NOT confirmed here — verify against `memcached -o help` or `items.c`** |
| memcached — modern-LRU blog and release notes | https://memcached.org/blog/modern-lru/ and https://github.com/memcached/memcached/wiki/ReleaseNotes150 | The recommended `-o slab_reassign,slab_automove,lru_crawler,lru_maintainer` startup set |
| memcached — flash storage (extstore) docs | https://docs.memcached.org/features/flashstorage/ | `extstore`'s keys-in-RAM / values-on-flash model |
| Kleppmann, *How to do distributed locking* | https://pages.cs.wisc.edu/~remzi/Classes/739/Spring2003/Papers/leases-redis-problem.pdf | The two objections to Redlock: no fencing token, and the assumptions of bounded network delay, bounded process pauses and bounded clock error |
| antirez, *Is Redlock safe?* and the Redlock pattern page | https://antirez.com/news/101 and https://redis.antirez.com/fundamental/redlock.html | The algorithm itself and the rebuttal: the elapsed-time validity check, and the efficiency-vs-correctness framing that resolves the debate |
| Valkey / Redis licensing and managed-default reporting (secondary) | https://redisson.pro/blog/valkey-vs-redis-comparision.html and https://www.cloudmagazin.com/en/2026/04/10/valkey-9-redis-fork-cloud-cache-landscape/ | BSD → SSPL/RSAL (March 2024) → AGPLv3 added (May 2025); Valkey as a Linux Foundation fork of Redis 7.2.4 under BSD-3; Valkey 9 and the ElastiCache/Memorystore defaulting to it; the ElastiCache-for-Valkey pricing deltas. **All commercial figures are `[CURRENCY]` and must be re-checked against AWS/Google pricing pages before publication** |
| hellointerview — Caching for System Design Interviews | https://www.hellointerview.com/learn/system-design/core-concepts/caching | Used purely as a **completeness probe** against the interview surface: placement tiers, the four patterns, LRU/LFU/FIFO/TTL, stampede, hot keys, the dual-write problem, request coalescing, cache warming, hot-key replication, and the latency figures interviewers expect to hear |
| Confluent — Understanding the dual-write problem | https://www.confluent.io/blog/dual-write-problem/ | The dual-write framing applied to cache-plus-database, and why write-through does not escape it |
| Operational write-ups on Redis latency and big/hot keys (secondary, aggregated) | https://oneuptime.com/blog/post/2026-03-31-redis-troubleshoot-redis-intermittent-latency-spikes/view and https://oneuptime.com/blog/post/2026-01-21-redis-hot-keys/view | The operational failure catalogue: big-key `DEL` stalls, fork/COW spikes, THP turning 4 KB faults into 2 MB faults, swap, and hot-key single-core saturation. Mechanisms only — **no numbers from these sources may be quoted without a primary confirmation** |

**Searches that returned nothing usable.** No first-party, named public postmortem of a
caching-caused outage with attributable figures was located; the write pass must either find a
first-party incident report or present the failure catalogue (§ 3.17) as mechanisms without inventing
an incident. No canonical university syllabus for "caching" as a standalone subject was found; the
curriculum angle was covered instead by the Redis/Caffeine/memcached documentation's own section
ordering and by the interview-surface probe. The `hot_lru_pct` family of memcached options and the
`activeExpireCycle` constants (`ACTIVE_EXPIRE_CYCLE_KEYS_PER_LOOP`, the 25% continuation threshold,
`ACTIVE_EXPIRE_CYCLE_FAST_DURATION`) could not be verified from primary documentation and must be
read out of `items.c` / `expire.c` before any number is committed. The Redis eviction-pool size (16)
and the `robj` LRU-clock resolution and wraparound period likewise need `evict.c` / `server.h`
confirmation.

**Carried-forward unverified items — the write pass must re-check every one of these before writing
a number:**

1. `hash-max-listpack-entries`: docs say 512, `redis.conf` ships 128. Resolve with `CONFIG GET`.
2. `activeExpireCycle` constants and CPU budget (§ 3.6.4) — `expire.c`.
3. Eviction pool size and the LRU clock's resolution/wraparound (§ 3.7.3, § 3.7.4) — `evict.c`,
   `server.h`.
4. `LFU_INIT_VAL` (§ 3.7.6).
5. Caffeine's timer-wheel bucket spans (§ 3.1.10) and the sketch reset threshold multiplier
   (§ 3.2.6) — `TimerWheel.java`, `FrequencySketch.java`.
6. Whether Caffeine ships a doorkeeper (§ 3.2.7).
7. memcached's `hot_lru_pct` / `warm_lru_pct` / `hot_max_factor` / `warm_max_factor` and the
   `FETCHED`/`ACTIVE` flags (§ 3.12.8, § 3.12.9); memcached item-header size (§ 3.12.14).
8. Redis 8.6's 3.5M ops/sec and memory-reduction figures (§ 2.1.8, § 3.5.8).
9. `tracking-table-max-keys` default (§ 3.10.20).
10. `allkeys-lrm`'s exact set of timestamp-updating commands (§ 3.7.8).
11. Boot 4.x's exact caching auto-configuration package and `CacheManagerCustomizer` FQN
    (§ 2.9.25).
12. `spring.cache.type` auto-detection order in Boot 4.1 (§ 2.9.23).
13. The XFetch inequality's exact form (§ 2.4.10, § 3.15.11).
14. `io-threads` semantics in 8.x (§ 3.4.3) and `dynamic-hz` default (§ 3.4.2).
15. Redis default `save` schedule in 8.x (§ 3.8.2).
16. Which HTTP status codes are heuristically cacheable, against RFC 9110 § 15 (§ 2.7.26).
17. Every commercial/vendor figure tagged `[CURRENCY]`, especially ElastiCache-for-Valkey pricing
    and any managed-service default.
18. `virtual node` count guidance (§ 2.13.4) and Zipf exponent assumptions (§ 1.1.6, § 3.15.15) —
    both currently folklore-level.

---

## Gaps vs the current guide

`src/topics/15-caching.md` is **679 lines** across **14 numbered sections** plus a 53-item
`## Atomic concept checklist`. Every concept in it survives as a leaf. The table below is the work
order.

| Syllabus area | Present in `src/topics/15-caching.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why cache / hit-ratio economics | § 1 — the latency table, the hit-ratio/DB-load table, both consequences, the critical-dependency line, when-not-to-cache, the missing-index rule | locality and Zipf as preconditions; the average-latency formula derived; Amdahl's ceiling; the miss-ratio curve and working set; hit-ratio-as-KPI's p99 counterexample; cost and availability as reasons; the QuizStakes agreement-vs-balance worked decision | "expensive computation / rate-limited APIs" listed in one line with no arithmetic |
| §1.2 vocabulary | scattered | the whole section: the five-way miss taxonomy, eviction/expiry/invalidation/flush separated, admission vs eviction, scan resistance, coherence vs consistency, the penetration/avalanche/breakdown mapping, memoisation vs caching | — |
| §1.3 placement tiers | § 7 (in-process vs distributed) and § 14 (HTTP/CDN) only | the full tier pipeline; service worker; gateway cache; off-heap and disk tiers; DB-internal caches; the caches you did not know you had; additive staleness across tiers; the tier-selection procedure; the QuizStakes tier map | — |
| §1.4 read patterns | § 2 (cache-aside read), § 3 table (read-through, refresh-ahead) | the read-path taxonomy as a set; who-owns-the-loader as the real distinction; free single-flight from read-through; warming as a read pattern; read-your-own-writes on a cache | serve-stale mentioned in § 5.3 but not classified as a read pattern |
| §1.5 write patterns | § 2 (delete-don't-update, the two-writer proof, the read/write race, the six mitigations), § 3 (write-through/behind) | write-around named; write-through as a dual write; the CPU write-invalidate/update/allocate vocabulary; the QuizStakes limit-counter case; the impossibility statement | the mitigation list is present but unranked by what each actually buys |
| §1.6 expiry | § 4 — mandatory TTL, the TTL table, jitter with the code, sliding vs absolute | TTI named separately; variable per-entry expiry; where each system does its expiry work; expiry-on-write vs in-place mutation semantics; the QuizStakes negative-TTL hazard | "expiry is lazy" appears only inside § 9's Redis paragraph |
| §1.7 key design | § 11 — the rule, the forgotten-inputs list, the naming convention, versioning, `SCAN`/`UNLINK`, granularity | key-byte arithmetic; hashing an unbounded key; canonicalisation; time-bucketed keys; taggability as a design-time decision; the granularity counter-pressure (pipelining) | the multi-tenant collision is implied by the `documents:` example but not named as a security finding |
| §1.8 never-cache list | § 7's security bullet and § 1's "must be strictly fresh" | **the entire section** — invariant 12 quoted, the 500 ms budget arithmetic, the display-vs-authority split, how to enforce it in code, and the steelmanned counter-argument | — |
| §1.9 cache API surface | § 7's Caffeine bullet | the whole method-by-method surface, `get(key, loader)`'s guarantee, removal vs eviction listeners, `RemovalCause`, async surfaces, reference-based eviction, the Redis command mapping | `recordStats()` mentioned in one line |
| §1.10 serialisation | absent | **the entire subject** — formats, Java-serialisation disqualification, schema evolution across a rolling deploy, compression, DTO-vs-entity, the Spring serializer surface, sizing arithmetic | — |
| §2.1 master cost model | the § 1 latency table only | **the master cost table**; amortised vs worst case for every operation; Little's Law; the break-even hit ratio; the N+1 round-trip arithmetic; throughput ceilings | — |
| §2.2 eviction | § 10 — the Redis policy table, the `volatile-*` trap, LRU vs LFU, scan pollution, sampled LRU, eviction≠expiry, `evicted_keys` | Belady; FIFO; LRU-K/2Q/LIRS; SLRU; TinyLFU/W-TinyLFU as admission; ARC; CLOCK; S3-FIFO; **SIEVE**; lazy promotion / quick demotion; weight-aware eviction; the comparison table and the choosing procedure | the policy table omits `allkeys-lrm`/`volatile-lrm` and `maxmemory-samples` |
| §2.3 invalidation | § 6 — the Karlton quote, the strategy table, versioned keys, the one-write-path rule | generation/epoch counters; tag-index mechanics and their leak; namespace flush safely; the dual-write problem named; why Redis cannot join a transaction; ordering hazards; invalidation rate as a metric; `beforeInvocation`; what to do when you cannot invalidate | event- and CDC-driven each get one table row |
| §2.4 failure modes | § 5 — stampede mechanism and arithmetic, the four mitigations, penetration and avalanche in one closing paragraph | probabilistic early expiry with the actual criterion; the Lua compare-and-delete release; Bloom-filter arithmetic and its no-delete limitation; key-shape validation; **hot key** and **big key** as full subjects with detection commands; cache-breakdown vs avalanche; the slow-cache failure; fail-open vs fail-closed; the failure-mode master table | penetration/avalanche are a single paragraph; § 12 covers negative caching separately |
| §2.5 consistency models | § 2's closing "eventual consistency with a bounded staleness window" | the model table; read-your-writes; monotonic reads; session and causal consistency; coherence protocols; staleness composition arithmetic; the bounded-staleness contract as an artifact; the QuizStakes consistency table | flapping is described in § 7 but not tied to monotonic reads |
| §2.6 near cache | § 8 — the diagram, the rationale, pub/sub code, the fire-and-forget trap, the rules, Redis tracking mentioned | Kafka/Streams cost (a consumer group per pod); cache-through vs cache-around; per-tier metrics composition; negative results at one tier only; when *not* to build one | tracking gets two sentences |
| §2.7 HTTP/CDN | § 14 — a header block, `max-age`/`s-maxage`, ETag→304, `Vary`, `private` vs `public`, fingerprinted URLs | RFC 9111's model, precedence, heuristic freshness and age calculation; all 17 directives; `no-cache` vs `no-store`; strong vs weak ETags and the generate-after-render trap; RFC 5861/8246/9211/9213 as separate specs; surrogate keys; purge vs soft-purge; cacheable methods and status codes; request collapsing; edge key normalisation; shield origins; web cache deception; cache poisoning; the whole Spring server-side surface; the QuizStakes per-endpoint table | `stale-while-revalidate` is mentioned twice with no spec attribution |
| §2.8 Java cache landscape | § 7's Caffeine bullet | **almost the entire subject** — `HashMap`/`LinkedHashMap`/Guava/Caffeine/Ehcache/JCache/Hazelcast compared; Guava's calling-thread maintenance; the full Caffeine builder surface; `Scheduler`/`Ticker`; `softValues` as a trap; the comparison table | Caffeine's knobs are a single sentence |
| §2.9 Spring Cache | § 3's closing paragraph ("know what it compiles down to") | **the entire subject** — every annotation attribute, `condition` vs `unless`, SpEL root, `SimpleKeyGenerator`'s blind spots, all nine `CacheManager`s, `TransactionAwareCacheManagerProxy`, `CacheErrorHandler`'s rethrow default, `sync=true`'s real scope, self-invocation, proxy ordering with `@Transactional`, `spring.cache.*`, the whole `RedisCacheConfiguration` surface, and what the abstraction cannot express | — |
| §2.10 Hibernate caching | absent | **the entire subject** — L1 as identity map, L2 configuration and the four concurrency strategies, collection and natural-id caching, the query cache and why it usually loses, `CacheMode`, and the multi-writer argument | — |
| §2.11 Redis operational surface | § 9 (data structures, TTL, persistence, Redis-vs-Memcached), § 10 (eviction), § 11 (`SCAN`/`UNLINK`) | hash-field TTLs as a capability; `SET`'s flag set; all ten policies; `maxmemory-samples`/LFU tuning; `mem_not_counted_for_evict` and headroom; the `INFO` field-by-field read and the docs' diagnostic tree; pipelining arithmetic; `MULTI`/`WATCH`; Lua and Functions; locks and the Redlock debate; replication/Sentinel/Cluster/hash slots/`CROSSSLOT`; keyspace notifications; latency diagnostics and the trap list; client output buffers; pool sizing for Lettuce vs Jedis; timeouts; Redisson; Spring Data Redis; **Valkey and the licence change**; `HOTKEYS` and `key-memory-histograms` | persistence is covered well but pre-dates the managed-service and Valkey reality |
| §2.12 memcached | § 9's closing two-sentence comparison | the protocol surface, `cas`, client-side sharding, the item-size limit, `extstore`, the decision table, Java clients | — |
| §2.13 topology / sharding | absent (§ 7 contrasts in-process vs distributed only) | **the entire subject** — the three topologies, why modulo hashing is disqualified, consistent hashing and vnodes, rendezvous and jump hash, Redis Cluster's slot design as a contrast, the QuizStakes partition-affinity honesty, replication vs sharding, multi-region, instance sizing vs count, multi-tenancy | — |
| §2.14 sizing arithmetic | absent | **the entire subject** — the procedure, measuring an object, per-entry overhead, four worked QuizStakes cases, fragmentation, provision-for-peak, cost arithmetic, the hash-bucketing trick | — |
| §2.15 observability | § 7's `recordStats()` line and § 10's `evicted_keys` line | the metric catalogue with bad values; per-tier and per-prefix hit ratio; percentiles not averages; the Redis server metric set; Micrometer wiring; tracing; cardinality discipline; which alerts are worth paging on and which are not; graph-reading as a procedure; the CLI toolkit | — |
| §2.16 warming / readiness | § 13 — cold start, the warming list, the readiness-gating code, the liveness warning, design-for-loss, load-testing | `ApplicationReadyEvent` vs alternatives; the warm-up timeout; the QuizStakes warm-up set | the warming bullets are present but not costed |
| §2.17 testing | absent | **the entire subject** — the four assertions, `Ticker` over `sleep`, order dependence, testing through the proxy, Testcontainers vs fakes, the coalescing test, the serialisation round-trip test | — |
| §2.18 choosing / anti-patterns | § 1's when-not-to-cache and § 3's write-behind warning | the decision procedure; the placement and pattern decision tables; twelve named anti-patterns; the "do you even need a cache" checklist | — |
| §2.19 cache security | § 7's revocation bullet, § 11's cross-user-data warning, § 14's `private` warning | the consolidated subject — cross-tenant collisions, web cache deception, caching secrets, the Redis security posture and 8.6's changes, encryption decisions, right-to-erasure, deserialisation attacks, timing oracles, invalidation-channel poisoning | — |
| §3.1–3.3 Caffeine and eviction internals | § 7 names W-TinyLFU; § 10 names sampled LRU | **the entire Part 3 opening** — `BoundedLocalCache` and code generation, the lossy read ring buffer, the write buffer, lock amortisation, the entry state machine, the timer wheel, the sketch's 4-bit layout and reset, adaptive hill-climbed window sizing, and every eviction proof (Belady, Bélády's anomaly, k-competitiveness, scan pollution) | — |
| §3.4–3.9 Redis internals | § 9's "single-threaded (for command execution)" sentence and § 10's sampling sentence | **the entire subject** — the event loop and `serverCron`, `io-threads`, `bio`, `dict` and `dictScan`'s reverse-binary cursor, `robj`/`sds`/listpack/quicklist and every encoding threshold, the expires dict and `activeExpireCycle`, replica expiry centralisation, `performEvictions` and the eviction pool, the LRU/LFU field layout, RDB/AOF forks and COW, THP and swap, replication and Cluster mechanics | — |
| §3.10 client-side caching internals | § 8's two sentences | **the entire subject** — the Invalidation Table, the bounded-table fabricated invalidation, every `CLIENT TRACKING` option, the RESP2 wire trace, `BCAST` and the non-overlapping-prefix rule, `NOLOOP`'s untracking, the redirection race and its placeholder fix, flush-and-`PING`, the per-command caching granularity rules | — |
| §3.11 Java client internals | absent | **the entire subject** — Lettuce's multiplexing and `disconnectedBehavior`, the unbounded request queue, Jedis pool sizing, Redisson's `RMapCache`/`RLocalCachedMap`/watchdog lock, virtual-thread interaction, RESP2 vs RESP3 | — |
| §3.12 memcached internals | absent | **the entire subject** — the slab allocator, slab calcification, `slab_reassign`/`slab_automove`, segmented LRU with HOT/WARM/COLD/TEMP, `temporary_ttl`, `lru_crawler`, the no-lock-on-read argument, item overhead | — |
| §3.13 Spring proxy internals | absent | **the entire subject** — `CacheInterceptor`, the operation resolution order, `SimpleValueWrapper`'s null distinction, `RedisCache`'s `clear`, and the abstraction's per-call cost | — |
| §3.14 buffer pool / page cache | absent | **the entire subject** — and specifically the argument that a warm buffer pool shrinks the cache's win, Postgres's scan-resistant ring buffer as prior art, and the MySQL query cache's removal as the cautionary tale | — |
| §3.15 proofs | § 1's hit-ratio table (arithmetic shown, not derived) | every proof: the latency and load formulas, Amdahl, Little, the utilisation curve, Bélády's anomaly, LRU's competitiveness, CMS bounds, Bloom FPR, HLL error, XFetch optimality, staleness composition, dual-write impossibility, lossy-invalidation impossibility, the Zipf hit-ratio integral, the miss-ratio knee, consistent hashing's remap fraction | — |
| §3.16 memory arithmetic | absent | **the entire subject** — byte-by-byte entry costs for all three engines, the sketch's footprint, the Bloom filter's, the tag index's, the tracking table's, heap vs off-heap vs Redis, and the COW spike | — |
| §3.17 failure catalogue | symptoms scattered across §§ 5, 10, 13 | a consolidated 21-entry symptom → cause → metric → fix catalogue | — |
| §3.18 version history | § 9 mentions "before Redis 7.4's `HEXPIRE`" and "Redis 6+ client-side caching" | **the entire subject** — and it is where every `[VERSION-TRAP]` and `[CURRENCY]` item lives | — |
| §4 build it | § 2, § 5, § 8, § 12, § 13 have illustrative fragments | all 24 implementations and their 24 Diff-vs-the-real-one tables | the existing fragments are correct but partial and must be absorbed, not deleted |
| §5 interview & retention | the 53-item atomic checklist | the 40 questions with answer shapes, the 84-item trap list, the cheat sheet, the two decision trees, the three-axis drills, the 60-second verbal answer, the twelve numeric self-quiz items, the anti-checklist | the checklist is strong and must be carried forward expanded, never trimmed |

### Must survive verbatim (or verbatim-plus-expansion)

These passages are the current guide's best work and the bible must keep the exact framing:

1. **"A cache your system cannot survive losing is not a cache, it is an undocumented critical
   dependency."** Plus the follow-up question: "if Redis vanishes right now, do we degrade or do we
   die?"
2. The **hit-ratio / DB-load table** and both consequences, including "cache sizing decisions should
   usually be justified by origin load, not by user-facing latency."
3. **"Add a cache" is also the wrong answer to a missing index — fix the query first, then cache.**
4. The **two-writer delete-vs-update trace** and its conclusion: "the cache converges to the truth
   instead of latching onto a stale value."
5. The **t0–t4 read/write race trace** and "this is the canonical cache-aside race, and you should be
   able to draw it."
6. **"Cache-aside gives eventual consistency with a bounded staleness window."**
7. **"Do not invent write-behind for business data — you have built an unreplicated, unbacked-up
   primary store and called it a cache."**
8. **"Every cache entry gets a TTL. No exceptions."** and "the TTL is not primarily an eviction
   mechanism — it is a correctness backstop."
9. The **jitter paragraph**: "You've built a synchronised stampede generator with a 10-minute period,
   and it will look like a mysterious periodic latency spike." Plus "it is one line and it eliminates
   an entire class of incident."
10. **"A single expiring key can take down a database."**
11. **"Serve-stale on error … is the single most valuable resilience behaviour a cache can have."**
12. The **invalidation-is-hard explanation**: "it is a global coupling problem in a codebase designed
    for local reasoning."
13. The **versioned-keys paragraph**, including "forgetting it causes deserialisation exceptions
    across the fleet during a rolling deploy."
14. **"If eight services can write to `products`, you need event- or CDC-driven invalidation, because
    you will never keep eight write paths in sync."** (Re-domained to QuizStakes services.)
15. The **flapping paragraph**: "files a bug titled 'data randomly wrong'" and "this flapping is far
    more confusing to users and to you than uniform staleness."
16. **"an unmeasured cache is a cache you can't reason about."**
17. The **entire Redis pub/sub trap block** from § 8, including "pub/sub invalidation is an
    optimisation, never a guarantee" and "design the system to be correct with the TTL alone."
18. **"never treat Redis as a system of record."**
19. The **`volatile-*` trap block** from § 10.
20. **"Eviction is not expiry"** and "a key can be evicted long before its TTL."
21. **"The rule: every input that changes the output must appear in the key."** and "the source of the
    worst class of cache bug — serving one user's data to another."
22. **"Don't cache the whole world under one key."**
23. The **sentinel rule**: "Use a distinct sentinel value, not `null` … This is the single most common
    implementation error in negative caching."
24. The **readiness-gating paragraph** and "make sure the liveness probe does not include this check,
    or Kubernetes will kill the pod mid-warm-up and loop."
25. **"Load-test with the cache disabled at least once so you know what actually happens; most teams
    find out during an incident."**
26. **"`private` vs `public` is a security control."**
27. **"Cache as close to the user as the correctness of the data allows. The cheapest request is the
    one that never reaches your infrastructure."**
28. **"Versioned/fingerprinted URLs beat purging every time — change the key rather than invalidating
    it."**
29. All 53 atomic-checklist lines, expanded rather than replaced.

### Corrections the write pass must make to existing text

These are not additions — the current file is wrong, stale, or off-domain here:

1. **Every example must be re-domained.** §§ 2, 6, 11, 12 use `product:v2:`, `Product`,
   `repository.findById`, `documents:{folderId}`, `users:profile`, `orders:order:v2:12345`. The
   pipeline's rule is QuizStakes only: use `agreements:version:v1:current`,
   `pendingactions:client:v2:{clientId}`, `profile:composite:v3:{clientId}:role:{role}`,
   `ClientAgreements`, `PendingActions`, `ProfileService`.
2. **§ 10's eviction table lists eight policies.** There are **ten** since Redis 8.6 —
   `allkeys-lrm` and `volatile-lrm` must be added, and the LRM read-vs-write timestamp distinction
   explained.
3. **§ 10's "Redis's LRU is *approximated* by sampling a few keys"** must add `maxmemory-samples`
   (default 5, 10 for near-exact) and the **candidate pool since 3.0** that makes the approximation
   good.
4. **§ 10's LFU paragraph** must add `lfu-log-factor` (10) and `lfu-decay-time` (1 minute) and the
   8-bit Morris counter, or the reader cannot tune it.
5. **§ 9's hash-field TTL parenthesis** — "(before Redis 7.4's `HEXPIRE`)" — must be inverted to lead
   with the capability and name the whole family (`HEXPIRE`, `HPEXPIRE`, `HEXPIREAT`, `HPEXPIREAT`,
   `HTTL`, `HPTTL`, `HPERSIST`, `HGETEX`, `HGETDEL`).
6. **§ 9's `SETNX` mention** must be updated: `SETNX` is effectively superseded by
   `SET … NX PX`, and the lock must not be presented without the token and the Lua release.
7. **§ 7's "W-TinyLFU eviction (better hit rates than LRU on real workloads)"** is imprecise on two
   counts: W-TinyLFU is an **admission** policy in front of an SLRU eviction policy, and the claim
   needs a figure and a source.
8. **§ 9 must note `io-threads`** so "single-threaded" is not read as "one thread total".
9. **§ 9's HyperLogLog row** should carry the ~0.81% standard error alongside the 12 KB.
10. **§ 11's `SCAN` guidance** must add that `MATCH` filters *after* fetching, so a selective pattern
    still walks the keyspace, and that `COUNT` is a hint.
11. **§ 12's negative-caching code compares with `==` against `NULL_SENTINEL`.** That is correct
    in-process and **broken across a serialising cache**, where the sentinel arrives as a new object.
    The rewrite must use a distinct type or a marker value compared by equality, and say why.
12. **§ 14's header block needs spec attribution**: `stale-while-revalidate`/`stale-if-error` are RFC
    5861, `immutable` is RFC 8246, and `Cache-Status`/`CDN-Cache-Control` (RFC 9211/9213) are absent
    entirely.
13. **§ 14 must add `no-cache` vs `no-store`** explicitly — the current file shows both in a code
    block with terse comments and never states the misconception.
14. **§ 8's "Redis 6+ client-side caching (tracking) … handled by the client library"** must name the
    clients that actually implement it (Jedis ≥ 5.2.0, redis-py ≥ 5.1.0) and note that supporting the
    `CLIENT TRACKING` command is not the same thing.
15. **§ 9's persistence section must be re-anchored to managed reality**: "ElastiCache/managed Redis
    frequently ships with persistence off entirely" is right, but the file must also say that
    ElastiCache and Memorystore now default new instances to **Valkey**, and that Redis's licence is
    AGPLv3/SSPL/RSAL rather than BSD.
16. **§ 9's Redis-vs-Memcached paragraph** must add the slab allocator, segmented LRU and `extstore`,
    since "simpler, multi-threaded, strings only" understates both the strength and the failure mode.
17. **§ 1's latency table** must be labelled order-of-magnitude and dated, and the file must state its
      target versions in a header — the current file states none, which is why several of its numbers
      have quietly aged.
18. **§ 5.2's "The probabilistic variant (XFetch)"** must give the actual criterion and cite the VLDB
    paper rather than describing it in prose.
19. **§ 3's `@Cacheable` paragraph** must add that `SimpleCacheErrorHandler` rethrows by default, since
    the paragraph's whole point is what the annotation hides.
20. **§ 13's `CacheWarmupIndicator` example** should bound the warm-up with a timeout in the code, not
    only mention it in the following sentence.

---

**File size — disk-verified: 3,222 lines.**

**Leaf counts — disk-verified.** Counted against the written file with
`^<part>\.[0-9]+\.[0-9]+ ` per part; the total is independently confirmed by
`^[1-5]\.[0-9]+\.[0-9]+ ` = 978:

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics (§1.1–§1.10) | 10 | **165** |
| PART 2 — Intermediate (§2.1–§2.19) | 19 | **361** |
| PART 3 — Under the hood (§3.1–§3.18) | 18 | **271** |
| PART 4 — Build it (4.1–4.24) | 1 | **48** (24 implementations + 24 Diff tables) |
| PART 5 — Interview & retention (§5.1–§5.3) | 3 | **133** |
| **Total** | **50** + 1 build block | **978** |

**Tag inventory — disk-verified raw occurrence counts.** Each count is the number of literal
occurrences of the tag in the file, which includes **exactly one occurrence per tag from the
tag-legend table** and, for `[RESEARCH]`, `[CURRENCY]`, `[VERSION-TRAP]` and `[X-REF nn]`, a small
number of mentions in the header prose and the scope-boundary list. Subtract accordingly when
auditing leaf-attached tags:

| Tag | Raw occurrences |
|---|---|
| `[PROVE]` | 314 |
| `[TRAP]` | 192 |
| `[NUM]` | 130 |
| `[X-REF nn]` | 127 |
| `[RESEARCH]` | 115 |
| `[TABLE]` | 113 |
| `[SOURCE]` | 105 |
| `[API]` | 71 |
| `[BUILD]` | 46 |
| `[CFG]` | 44 |
| `[DIAG]` | 31 |
| `[VERSION-TRAP]` | 30 |
| `[CURRENCY]` | 30 |
| `[SPEC]` | 24 |
| `[METRIC]` | 21 |
| `[CLI]` | 19 |
| `[FLOW]` | 17 |
| `[WIRE]` | 14 |

**`[RESEARCH]` clustering.** The 115 `[RESEARCH]` occurrences concentrate in exactly the places where
recall is least trustworthy: Redis 8.6's new surface (LRM policies, `HOTKEYS`,
`key-memory-histograms`, `tls-auth-clients-user`, stream idempotency), the encoding-threshold
docs/config discrepancy, `activeExpireCycle` and `performEvictions` source constants, the LFU field
layout and `LFU_INIT_VAL`, Caffeine's timer wheel and sketch reset threshold and its adaptive window,
memcached's LRU percentage options and item overhead, the SIEVE/S3-FIFO results, the XFetch
criterion, Boot 4.x's package moves and auto-detection order, Spring Data Redis 4.x additions,
Hibernate 7's property prefixes, RFC 9110's cacheable-status-code list, Valkey/licence/managed-default
facts, and every commercial figure. **Every one must be re-fetched from its cited source before the
write pass commits a number.**

**Target version restated for the write pass:** Redis Open Source 8.6 (noting Valkey 9 as the
common managed default and the AGPLv3/SSPL/RSAL licence position), Caffeine 3.2.4, memcached 1.6.x,
Spring Boot 4.1.x / Spring Framework 7.0.x with Boot 3.5.x deltas called out, Spring Data Redis
4.1.x, Hibernate ORM 7.x, JCache 1.1 with Ehcache 3.10.x, RFC 9111 + 9110 + 5861 + 8246 + 9211 +
9213, Java 21. State the baseline in the bible's header and mark every version-dependent claim.

**Split guidance.** At 978 leaves the bible will comfortably exceed ~2,500 lines. Split into
`src/topics/15-caching.md` (PARTS 1–2 — fundamentals, patterns, failure modes, HTTP, the Java and
Redis operational surface) and `src/topics/15-caching-internals.md` (PARTS 3–5 — Caffeine, Redis and
memcached internals, the proofs, the memory arithmetic, the failure catalogue, the version history,
the builds, and the interview layer). Cross-link both at the top, keep an
`## Atomic concept checklist` in each, and add the new file to `src/topics/00-index.md` while updating
topic 15's scope line to match what the files now actually contain.
