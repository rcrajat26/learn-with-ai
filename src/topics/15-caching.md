# 15 — Caching

Scope: the mechanisms, the race conditions, and the operational discipline. Caching interviews go
badly when a candidate can name "cache-aside" but can't say what happens when two requests miss at
the same moment, or what the cache key should contain.

---

## 1. Why cache, and the economics of hit ratio

A cache trades **memory and staleness** for **latency and load**. It is worth it when reads
substantially outnumber writes and the same data is read repeatedly — which describes most systems.

Latency reality check, order of magnitude:

| Source | Typical latency |
|---|---|
| In-process (heap) cache | ~50–100 ns |
| Redis, same AZ | ~0.2–1 ms |
| Postgres, indexed point lookup, warm | ~1–5 ms |
| Postgres, complex join / cold | 20–500 ms |
| Cross-region call | 50–150 ms |

**Hit ratio is non-linear and this is the key insight.** Suppose a hit costs 1 ms and a miss costs
50 ms (cache lookup + DB). Average latency:

| Hit ratio | Average latency | DB load (relative) |
|---|---|---|
| 0% | 50 ms | 100% |
| 50% | 25.5 ms | 50% |
| 90% | 5.9 ms | 10% |
| 95% | 3.5 ms | 5% |
| 99% | 1.5 ms | 1% |
| 99.9% | 1.05 ms | 0.1% |

Two consequences people miss:

1. **The last few percent of hit ratio matter most for the *backend*.** Going from 90% to 99% barely
   changes average latency (5.9 → 1.5 ms) but cuts database load **tenfold**. Cache sizing decisions
   should usually be justified by origin load, not by user-facing latency.
2. **Going the other way is a cliff.** A cache flush drops you from 99% to 0% instantly. Your database
   was sized for 1% of read traffic and now receives 100× — it falls over. **A cache your system
   cannot survive losing is not a cache, it is an undocumented critical dependency.** Always ask: if
   Redis vanishes right now, do we degrade or do we die? Design so it's degrade (see §12, §13).

Also worth caching for: expensive computation (aggregations, rendered fragments), rate-limited or
paid third-party APIs, and protecting a downstream that scales worse than you do.

**When not to cache:** low read/write ratio (you'll invalidate more than you serve), data that must be
strictly fresh (account balance at the moment of a trade), data with no reuse (unique per request),
and anything where the correctness cost of staleness exceeds the latency benefit. "Add a cache" is
also the wrong answer to a missing index — fix the query first, then cache.

---

## 2. Cache-aside (lazy loading) — the default pattern

The application owns the cache. The cache knows nothing about the database.

### Read path
```java
public Product getProduct(String id) {
    String key = "product:v2:" + id;
    Product cached = cache.get(key);
    if (cached != null) {
        return cached;                        // HIT
    }
    Product fromDb = repository.findById(id)  // MISS
            .orElseThrow(() -> new NotFoundException(id));
    cache.set(key, fromDb, Duration.ofMinutes(10));
    return fromDb;
}
```

Properties: only requested data is cached (memory-efficient), a cache failure degrades to a slow-but-
correct path, and it's simple. Costs: every miss pays cache-lookup + DB (a small tax), the first
request for any key is always slow, and stale data persists until TTL or invalidation.

### Write path — **delete, don't update**
```java
@Transactional
public void updateProduct(Product p) {
    repository.save(p);
    cache.delete("product:v2:" + p.id());   // invalidate, don't write
}
```

**Why delete beats update.** Two concurrent writers:

```
Writer A: save(v1) ────────────────────────► cache.set(v1)
Writer B:      save(v2) ──► cache.set(v2)
Result: DB has v2 (B wrote last), cache has v1. Permanently wrong until TTL.
```
With delete, both writers delete; the next read repopulates from whatever the DB actually holds. The
cache converges to the truth instead of latching onto a stale value. Delete is also cheaper (no
serialisation), and it avoids caching values nobody will read.

### The read/write race that delete does *not* fix

```
t0  Reader:  cache MISS for product:42
t1  Reader:  SELECT → gets v1
t2  Writer:  UPDATE → DB now has v2
t3  Writer:  cache.delete("product:42")     ← deletes nothing; it's already empty
t4  Reader:  cache.set("product:42", v1)    ← writes STALE v1, with a full TTL
```

The cache now holds v1 while the DB holds v2, and it will stay wrong for the whole TTL. This is the
canonical cache-aside race, and you should be able to draw it.

**Mitigations, in increasing order of cost:**
- **A TTL always** — bounds the damage to a known window. This is why "TTL as a backstop" is a rule,
  not an optimisation (§4).
- **Delete after commit, not inside the transaction.** Deleting inside means a reader can repopulate
  from the pre-commit state; also, if the transaction rolls back you've evicted for nothing. Use
  `TransactionSynchronization.afterCommit`.
- **Delayed double delete** — delete, commit, then delete again after a short delay (e.g. 500 ms) to
  clear anything a concurrent reader repopulated. Crude but effective and widely used.
- **Version/CAS on write-back** — only set the cache if the version you read is still current.
- **Single-flight on the read path** (§5) — dramatically narrows the window by allowing only one
  in-flight DB read per key.
- **CDC-driven invalidation** — invalidate from the database's replication log, so invalidation
  strictly follows the commit. The most correct option; the most infrastructure.

The honest framing: cache-aside gives **eventual consistency with a bounded staleness window**. If a
requirement genuinely cannot tolerate that, don't cache it — or read through a mechanism that is
transactionally consistent.

---

## 3. Write-through, write-behind, read-through

| Pattern | Write path | Read path | Trade-off |
|---|---|---|---|
| **Cache-aside** | app writes DB, invalidates cache | app checks cache, loads on miss | simple, resilient, stale window; the default |
| **Read-through** | — | cache library loads from DB on miss | tidier code (Caffeine `LoadingCache`, `@Cacheable`); the cache becomes a dependency of reads |
| **Write-through** | app writes cache, cache writes DB **synchronously** | always from cache | cache is never stale relative to DB; adds latency to every write; caches data that may never be read |
| **Write-behind (write-back)** | app writes cache, cache flushes to DB **asynchronously** | always from cache | fastest writes, batches DB load; **risks data loss if the cache dies before flush** |
| **Refresh-ahead** | — | proactively reload hot keys before expiry | hides miss latency for hot keys; wasted work for cold ones |

Write-through is often paired with cache-aside reads to keep the cache warm. Write-behind is rare in
application code and mostly appears inside databases and storage engines, where the durability
concern is handled by a write-ahead log. **Do not invent write-behind for business data** — you have
built an unreplicated, unbacked-up primary store and called it a cache.

`@Cacheable` / `@CacheEvict` in Spring is read-through + explicit invalidation. It's convenient but
hides the mechanism, which is exactly why people using it can't answer the race-condition question.
Know what it compiles down to.

---

## 4. TTL discipline

**Every cache entry gets a TTL. No exceptions.** The TTL is not primarily an eviction mechanism — it
is a **correctness backstop**. Invalidation logic will eventually be missed: a new write path, a batch
job, a manual DB fix, a bug. TTL bounds how long any of those can hurt you.

Choosing one: ask "how stale can this be before someone is harmed?" then pick something under that.

| Data | Typical TTL | Reasoning |
|---|---|---|
| Reference data (countries, categories) | hours–days | changes almost never |
| Product catalogue | 5–60 min | changes occasionally; staleness is cosmetic |
| User profile | 5–15 min | with explicit invalidation on update |
| Pricing / inventory | seconds–1 min | staleness has money consequences |
| Session | sliding, 30 min | refreshed on access |
| Auth tokens / JWK sets | tied to token lifetime | never cache past validity |
| Feature flags | seconds, or push-invalidated | must react quickly |
| Negative (not-found) results | 30 s–2 min | short, deliberately (§15) |

**TTL jitter — the thing that separates people who've operated caches.** If you populate 10,000 keys
during a deploy or a warm-up, all with a 10-minute TTL, they all expire in the *same second*. Ten
minutes later, 10,000 simultaneous misses hit the database. You've built a synchronised stampede
generator with a 10-minute period, and it will look like a mysterious periodic latency spike.

```java
Duration ttl = Duration.ofMinutes(10)
        .plusSeconds(ThreadLocalRandom.current().nextInt(120));  // ±10-20% spread
```

Add 10–20% random jitter to every TTL. It is one line and it eliminates an entire class of incident.

**Sliding vs absolute expiry.** Sliding (reset on access) keeps hot data resident indefinitely — good
for sessions, bad for data that must eventually refresh, because a permanently-hot key never expires
and never picks up changes. Prefer absolute for correctness-relevant data; sliding for sessions.

---

## 5. Stampede / thundering herd

**Mechanism.** A hot key expires (or is evicted, or the cache restarts). Between the moment it
disappears and the moment the first loader repopulates it, *every* concurrent request for that key
misses and independently queries the database. At 5,000 rps on one key with a 200 ms query, that's
1,000 concurrent identical queries. The database saturates, queries slow down, the repopulation takes
even longer, more requests pile in. A single expiring key can take down a database.

This is the most important cache failure mode and it has four standard mitigations.

### 5.1 Single-flight (request coalescing / mutex)
Allow exactly one loader per key; everyone else waits for its result.

```java
// Caffeine does this natively: concurrent get() calls for the same absent key
// execute the mapping function ONCE; the others block and receive the same value.
LoadingCache<String, Product> cache = Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(Duration.ofMinutes(10))
        .refreshAfterWrite(Duration.ofMinutes(8))     // refresh-ahead, see 5.2
        .build(id -> repository.findById(id).orElseThrow());
```

For a **distributed** cache you need a distributed lock, because the coalescing must span instances:
```
SET lock:product:42 <token> NX PX 5000
  acquired  → load from DB, populate cache, release
  not acquired → brief sleep and re-read the cache (it should be populated),
                 or serve the stale value if you kept one
```
Note this inherits the lock-expiry hazard from topic 14 §12 — but here a duplicate load is merely
wasteful, not incorrect, so a simple TTL lock is fine. Per-instance coalescing (in-process lock per
key) already removes ~90% of the load with none of the complexity; do that first.

### 5.2 Refresh-ahead (probabilistic early expiry)
Refresh the entry *before* it expires, while still serving the old value. Caffeine's
`refreshAfterWrite` does exactly this: after the refresh interval, the next request triggers an async
reload and **immediately returns the stale value**. Nobody waits, and the key never actually vanishes.

The probabilistic variant (XFetch) refreshes with a probability that rises as expiry approaches,
computed from the last load's duration — this staggers refreshes across instances without
coordination.

### 5.3 Serve-stale on error
Keep the expired value and serve it if the origin fails or times out. A slightly stale response is
almost always better than a 500. This is `stale-while-revalidate` / `stale-if-error` in HTTP caching,
and it's the single most valuable resilience behaviour a cache can have. Combine with a circuit
breaker so you stop hammering a dead origin and keep serving stale until it recovers.

### 5.4 Never expire hot keys; refresh them out-of-band
For a small set of genuinely critical keys, run a background job that rewrites them on a schedule.
They have no TTL, so they can never stampede. Trade-off: if the refresher dies, the data silently
ossifies — so you must alert on refresher staleness. Reserve this for a handful of keys.

**Related: cache penetration and cache avalanche.** *Penetration* is requests for keys that don't
exist in the DB either, so nothing is ever cached and every request hits the DB — the fix is negative
caching (§15) or a Bloom filter. *Avalanche* is mass simultaneous expiry (the jitter problem, §4) or
a cache-cluster restart taking every key at once. Different causes, same symptom: sudden origin load.

---

## 6. Invalidation strategies

> "There are only two hard things in Computer Science: cache invalidation and naming things."
> — Phil Karlton

The joke is accurate, and it's worth saying *why*: invalidation requires knowing every place data is
cached and every code path that changes it, forever, as both sets grow independently. It is a global
coupling problem in a codebase designed for local reasoning.

| Strategy | Mechanism | Good | Bad |
|---|---|---|---|
| **TTL only** | let it expire | trivial; no coupling | guaranteed staleness window |
| **Explicit invalidation on write** | delete the key in the write path | fresh almost immediately | every new write path must remember; misses are silent |
| **Event-driven** | write emits an event; subscribers invalidate | decoupled; works across services | eventually consistent; needs a broker (topic 14) |
| **CDC-driven** | tail the WAL/binlog → invalidate | catches *every* change, including manual SQL | most infrastructure |
| **Versioned keys** | `product:v2:42`; bump `v2` to invalidate everything | atomic mass invalidation, no delete storm | old entries linger until evicted (memory cost) |
| **Tag-based** | group keys by tag, invalidate the tag | matches "everything for this user" | needs support (Redis sets as tag indexes) |
| **Write-through** | cache updated as part of the write | never stale w.r.t. DB | doesn't help other instances' local caches |

**Versioned keys deserve emphasis** because they solve problems the others can't. Embedding a schema
or content version in the key prefix means a deploy that changes the cached object's shape can bump
the version and instantly "invalidate" everything — with no delete storm, no key enumeration, and no
risk of a new pod deserialising an old-format value. Old entries simply age out. Use this every time
you change a cached DTO; forgetting it causes deserialisation exceptions across the fleet during a
rolling deploy.

**The rule that prevents most invalidation bugs:** put all writes for a given entity behind **one**
method, and invalidate there. If eight services can write to `products`, you need event- or CDC-driven
invalidation, because you will never keep eight write paths in sync.

---

## 7. In-process vs distributed

| | **In-process (Caffeine, Guava)** | **Distributed (Redis, Memcached)** |
|---|---|---|
| Latency | ~50–100 ns — a hash lookup | ~0.2–1 ms — a network round trip |
| Capacity | bounded by heap; competes with your app for memory and GC | tens of GB, independent |
| Consistency across instances | **none — each instance has its own copy** | shared, single source |
| Survives restart | no — cold on every deploy | yes |
| Failure mode | disappears with the process | a network dependency that can be down |
| Serialisation | none — object references | serialise/deserialise every access |
| Ops burden | zero | a cluster to run, monitor, and pay for |

**The multi-instance staleness problem** is the reason in-process caching is dangerous by default. Ten
pods, each with a 5-minute local cache. You update a product. Even with perfect invalidation logic,
the pod that handled the write invalidates *its own* cache; the other nine keep serving the old value
for up to five minutes. The user hits a different pod on refresh and sees the old price, refreshes
again and sees the new one, and files a bug titled "data randomly wrong".

This flapping is far more confusing to users and to you than uniform staleness. Rules:

- In-process caching is safe for **immutable or effectively-immutable** data (reference data,
  configuration loaded at startup, computed constants, parsed schemas).
- For mutable shared state, use a distributed cache so all instances see one value — or accept the
  staleness *explicitly*, with a TTL short enough that the flapping window is tolerable, and document
  it.
- Never in-process cache anything security-relevant (permissions, feature entitlements, revoked
  tokens) with a long TTL. Revocation that takes 5 minutes to propagate to some pods but not others
  is a security finding.

Caffeine specifics worth knowing: W-TinyLFU eviction (better hit rates than LRU on real workloads),
`maximumSize` vs `maximumWeight`, `expireAfterWrite` vs `expireAfterAccess`, `refreshAfterWrite`
(§5.2), and `recordStats()` + `cache.stats()` to expose hit ratio — **always** wire that to your
metrics, because an unmeasured cache is a cache you can't reason about.

---

## 8. The hybrid / near-cache pattern

Two tiers: a small in-process L1 in front of a shared Redis L2.

```
request → L1 (Caffeine, ~100 ns, 30s TTL)
            miss ↓
          L2 (Redis, ~0.5 ms, 10min TTL)
            miss ↓
          Database
```

Why: L1 absorbs the extremely hot keys (a handful of items often serve most traffic), eliminating both
network round trips and Redis CPU. L2 gives cross-instance sharing, survives deploys, and holds the
long tail. Typical result: p50 drops to near-zero and Redis load falls by an order of magnitude.

The cost is **two levels of staleness**, and L1 is the hard one — you can't delete a key from another
pod's heap.

### Pub/sub invalidation

Broadcast invalidations so every instance can evict its L1:

```java
// On write
repository.save(product);
redis.del("product:v2:" + product.id());              // clear L2
redis.convertAndSend("cache-invalidate", product.id()); // tell every L1

// Every instance subscribes
@EventListener
public void onInvalidate(String id) {
    localCache.invalidate("product:v2:" + id);
}
```

> **Trap — Redis pub/sub is fire-and-forget.** It has **no delivery guarantee, no persistence, and no
> replay**. A subscriber that is briefly disconnected (network blip, GC pause, rolling restart, still
> starting up) simply **misses the message forever** and keeps serving stale data indefinitely. There
> is no error, no retry, and no way to detect it from the publisher.
>
> Therefore: **pub/sub invalidation is an optimisation, never a guarantee.** It must always be backed
> by a **short L1 TTL** (30–60 s) that bounds the damage when a message is missed. Design the system
> to be correct with the TTL alone; treat pub/sub as the thing that usually makes it faster.
>
> If you need reliable invalidation, use Kafka (durable, replayable, consumers resume from their
> offset) or Redis Streams with consumer groups — not pub/sub.

Redis 6+ **client-side caching (tracking)** implements this pattern natively: the server remembers
which keys each client has cached and sends invalidation messages. Same caveat class, but handled by
the client library rather than your code.

**Rules for the hybrid pattern:** L1 TTL much shorter than L2 TTL; L1 small (hundreds to low
thousands of entries — it's for hot keys, not coverage); pub/sub as best-effort; and never L1-cache
data where a 60-second stale window is unacceptable.

---

## 9. Redis: data structures and what they're for

Redis is a single-threaded (for command execution) in-memory data-structure server. Single-threaded
matters: **every command is atomic**, which is why `INCR`, `SETNX`, and `LPUSH` are safe without
locks — and why one `KEYS *` on a large database blocks *everything*.

| Structure | Key commands | Real uses |
|---|---|---|
| **String** | `GET/SET/SETEX/INCR/SETNX` | cached objects (JSON), counters, distributed locks, rate limiters |
| **Hash** | `HGET/HSET/HGETALL/HINCRBY` | objects with independently-updated fields; **session data** (update one field without re-serialising the whole object) |
| **List** | `LPUSH/RPOP/BLPOP/LRANGE` | simple queues (`BLPOP` = blocking pop), recent-activity feeds, capped logs with `LTRIM` |
| **Set** | `SADD/SISMEMBER/SINTER/SCARD` | unique-visitor tracking, tags, permissions, "have I seen this ID", set algebra |
| **Sorted set (ZSET)** | `ZADD/ZRANGE/ZRANGEBYSCORE/ZREVRANK` | **leaderboards**, priority queues, sliding-window rate limiting (score = timestamp), time-series indexes, delayed-job scheduling |
| **Bitmap** | `SETBIT/BITCOUNT` | daily-active-user flags at ~1 bit/user — extremely compact |
| **HyperLogLog** | `PFADD/PFCOUNT` | approximate cardinality (unique visitors) in 12 KB regardless of count |
| **Stream** | `XADD/XREADGROUP/XACK` | an append-only log with consumer groups — the Kafka-lite option |
| **Geo** | `GEOADD/GEOSEARCH` | nearby-things queries (ZSET underneath) |

**TTL is per key** (`EXPIRE`, `SETEX`, `SET ... EX`), and expiry is **lazy plus a sampling background
job** — an expired key is removed when accessed, or when the sampler happens to find it. So `INFO
memory` can show memory held by keys that are logically expired. This matters when you're debugging
memory usage.

Note also: you cannot set a TTL on individual **hash fields** (before Redis 7.4's `HEXPIRE`). This
regularly surprises people who model a cache as one big hash — the whole hash expires together, or not
at all.

### Redis honesty: what it is and isn't good at

**As a cache:** excellent. This is the primary use, and everything below is a qualification of using
it for *other* things.

**As a queue:** possible (`BLPOP`, or Streams), but be honest about the guarantees. A plain
`LPUSH`/`BRPOP` queue is **at-most-once**: pop removes the item, and if the consumer dies the work is
gone. `RPOPLPUSH` into a processing list gets you at-least-once but you must write the reclaim logic
for abandoned items yourself. Redis **Streams** with consumer groups (`XACK`, `XPENDING`,
`XAUTOCLAIM`) do give proper at-least-once with a real pending-entries list — that's the one to use if
you must queue on Redis. For anything important, use SQS or Kafka (topic 14): a purpose-built broker
gives you DLQs, redrive, retention, and visibility timeouts you'd otherwise reimplement badly.

**As a session store:** very good, and a standard choice. Enables stateless app instances (topic 18
§7). Use a hash, set a sliding TTL, and accept that a Redis failure logs everyone out — which is
usually acceptable, and is why you replicate.

**As pub/sub:** fire-and-forget only. See §8's trap. No persistence, no replay, no acks.

**Persistence defaults — the part people get wrong.** Redis is an in-memory store; persistence is
optional and, by default, **lossy**:
- **RDB snapshots** (the default): a point-in-time fork-and-dump on a schedule (e.g. "every 5 min if
  ≥100 keys changed"). A crash loses everything since the last snapshot — **potentially minutes of
  writes**.
- **AOF** (append-only file): logs every write. `appendfsync everysec` (the usual setting) loses up to
  1 second; `always` is durable but slow. Not enabled by default in many configurations.
- **ElastiCache/managed Redis** frequently ships with persistence off entirely.

So: **never treat Redis as a system of record.** It is a cache, a coordination point, and a fast
ephemeral store. Anything you cannot afford to lose belongs in a database. Also know that replication
is **asynchronous**, so a failover can lose recent writes even with persistence on — which is exactly
why Redlock-style locking is contested (topic 14 §12).

**Redis vs Memcached, briefly:** Memcached is simpler, multi-threaded, strings only, no persistence,
no replication — genuinely faster for pure string caching at scale. Redis wins on data structures,
persistence, replication, pub/sub, and scripting, which is why it's the default choice for almost
everyone.

---

## 10. Eviction policies

When memory hits `maxmemory`, Redis applies `maxmemory-policy`:

| Policy | Behaviour |
|---|---|
| `noeviction` | **writes fail with an error** (the default — surprising and important) |
| `allkeys-lru` | evict least-recently-used across all keys — **the right choice for a pure cache** |
| `allkeys-lfu` | evict least-*frequently*-used; better when access frequency is skewed and stable |
| `allkeys-random` | random; cheap, occasionally fine |
| `volatile-lru` / `-lfu` / `-random` / `-ttl` | same, but only among keys **that have a TTL** |

> **Trap:** Using a `volatile-*` policy while some keys have no TTL. When only non-TTL keys remain,
> Redis has nothing eligible to evict and behaves like `noeviction` — writes start failing. If you're
> using Redis purely as a cache, use `allkeys-lru` and stop thinking about it.

**LRU vs LFU.** LRU evicts what hasn't been touched recently; it is vulnerable to **scan pollution** —
a batch job reading a million rows once evicts your entire hot set. LFU tracks access frequency (with
decay) and resists that, so it's better for workloads with a stable hot set plus periodic scans.
Redis's LRU is *approximated* by sampling a few keys, not exact — good enough, and much cheaper.
Caffeine's W-TinyLFU is a hybrid that generally beats both.

**Eviction is not expiry.** Expiry is "this entry's TTL passed"; eviction is "I need memory and chose
a victim." A key can be evicted long before its TTL. That's fine for a cache and catastrophic if you
were storing something that must persist — another reason not to store state in Redis.

Watch `evicted_keys` in `INFO stats`. A sudden rise means the working set outgrew memory, and your hit
ratio is about to fall off the cliff described in §1.

---

## 11. Key design

**The rule: every input that changes the output must appear in the key.**

Violating this is the source of the worst class of cache bug — **serving one user's data to another**.

```java
// WRONG — the result depends on the caller's permissions, but the key doesn't say so
cache.get("documents:" + folderId);

// RIGHT
cache.get("documents:v1:" + folderId + ":role:" + role);
```

Inputs people forget: user or tenant ID, role/permission scope, locale and currency, feature-flag
variant, API version, pagination offset and page size, sort order, filter parameters, and the
`Accept`/`Accept-Encoding` content negotiation. Anything the response varies on.

**Naming conventions** (Redis has a flat keyspace, so the convention *is* the schema):
```
{app}:{entity}:{version}:{id}[:{qualifier}]
orders:order:v2:12345
users:profile:v1:9876:locale:en-GB
ratelimit:api:v1:user:9876:2026-08-21T14:32
```
- Include a **version** so a schema change can invalidate en masse (§6) — this also prevents a new pod
  from deserialising an old-shape value during a rolling deploy.
- Use `:` as the separator (tooling and Redis UIs expect it).
- Keep keys short-ish — millions of keys means key strings themselves cost real memory.
- Prefix by application/service so a shared Redis is debuggable and you can scope a flush.

**Operational note:** to find keys, use `SCAN` (cursor-based, non-blocking), **never `KEYS *`** —
`KEYS` is O(n) and blocks Redis's single command thread, stalling every client on the instance. Same
warning for `FLUSHALL` in production and for large `DEL`s (use `UNLINK`, which frees memory in a
background thread).

**Don't cache the whole world under one key.** A single key holding a 50 MB list means every read
transfers 50 MB and every change invalidates everything. Cache at the granularity you read at.

---

## 12. Negative caching

If a lookup misses in the DB too, nothing gets cached, so every subsequent identical request hits the
DB again. An attacker (or a broken client in a retry loop) requesting nonexistent IDs bypasses your
cache entirely and pounds the database directly — **cache penetration**.

Cache the absence:
```java
Object cached = cache.get(key);
if (cached == NULL_SENTINEL) return Optional.empty();   // cached miss
if (cached != null) return Optional.of((Product) cached);

Optional<Product> fromDb = repository.findById(id);
cache.set(key,
          fromDb.isPresent() ? fromDb.get() : NULL_SENTINEL,
          fromDb.isPresent() ? Duration.ofMinutes(10) : Duration.ofSeconds(30));
return fromDb;
```

Use a distinct **sentinel** value, not `null` — otherwise you cannot distinguish "cached as absent"
from "not in the cache". This is the single most common implementation error in negative caching.

**Keep negative TTLs short** (30 s – 2 min). A resource that doesn't exist now often exists in a
moment (just-created records, replication lag), and a long negative TTL turns a race into a
user-visible "your new item doesn't exist" bug. This mirrors the DNS negative-caching hazard in topic
10 §3.

At very large scale, a **Bloom filter** in front ("definitely not present" vs "maybe present") avoids
storing a key per bogus ID — relevant when the space of invalid IDs is unbounded.

---

## 13. Warming, cold start, and readiness gating

**Cold start.** Every deploy, restart, scale-out, or cache failover starts with an empty cache. Hit
ratio is 0%, and every request goes to the database. Recall §1: if the DB is provisioned for 1% of
read traffic, it now gets 100×. A rolling deploy that replaces pods slowly is fine. A simultaneous
restart of the whole fleet, or a Redis cluster failover, is an outage.

**Cache warming** — preload the known-hot set before serving traffic:
- On startup, load reference data and a curated hot-key list (from yesterday's access logs).
- Replicate the cache across AZs so a failover finds a warm replica rather than an empty one.
- For a planned Redis migration, dual-write to the new cluster before cutting over.
- For a fleet restart, stagger it so the origin sees load gradually.

**Readiness gating — the mechanism that makes warming actually work.** In Kubernetes, a pod receives
traffic as soon as its **readiness** probe passes. If you warm the cache asynchronously after startup,
the pod goes ready immediately and takes full traffic with an empty cache — the warming was pointless.

Make the readiness probe fail until warm-up completes:

```java
@Component
class CacheWarmupIndicator implements HealthIndicator {   // wired into /actuator/health/readiness
    private final AtomicBoolean warm = new AtomicBoolean(false);

    @EventListener(ApplicationReadyEvent.class)
    void warm() {
        referenceDataCache.loadAll();
        hotKeyLoader.preload(500);
        warm.set(true);
    }

    @Override public Health health() {
        return warm.get() ? Health.up().build() : Health.down().withDetail("cache", "warming").build();
    }
}
```

Now the rolling deploy waits for each pod to be warm before shifting traffic to it and before killing
the next old pod. Bound the warm-up with a timeout so a broken warm-up doesn't block the deploy
forever — and make sure the **liveness** probe does *not* include this check, or Kubernetes will kill
the pod mid-warm-up and loop. (Topic 19 §6, topic 20 §6.)

**Design for cache loss.** Rate-limit or circuit-break the origin behind the cache, so a mass miss
degrades (slower responses, some shed load) instead of destroying the database. Load-test with the
cache disabled at least once so you know what actually happens; most teams find out during an
incident.

---

## 14. HTTP and CDN caching — the layer above

The browser and CDN tiers are caches too, and they're free capacity if you use the headers correctly
(see topic 10 §13).

```
Cache-Control: public, max-age=300, stale-while-revalidate=60, stale-if-error=86400
Cache-Control: private, no-cache          # may store, must revalidate before use
Cache-Control: no-store                   # never store — for anything sensitive
ETag: "a1b2c3"                            # revalidation token
```

- `max-age` for the browser, `s-maxage` to override it for shared caches (the CDN).
- `stale-while-revalidate` is §5.3 as a standard header — serve stale, refresh in the background.
- `ETag` + `If-None-Match` yields **304 Not Modified**: still a round trip, but no body transferred.
- `Vary: Accept-Encoding` correct; `Vary: Cookie` destroys your hit ratio (every user is a distinct
  cache entry).
- **`private` vs `public` is a security control.** A `public` response containing user data can be
  cached by a shared proxy or CDN and served to a different user. Authenticated responses should be
  `private` or `no-store`.
- **Versioned/fingerprinted URLs** (`app.a1b2c3.js`, `max-age=31536000, immutable`) beat purging every
  time — change the key rather than invalidating.

The general point: cache as close to the user as the correctness of the data allows. The cheapest
request is the one that never reaches your infrastructure.

---

## Atomic concept checklist

- [ ] A cache trades memory + staleness for latency + origin load.
- [ ] Hit ratio is non-linear: 90%→99% barely moves latency but cuts DB load **10×**.
- [ ] A cache flush drops you to 0% instantly — if your system can't survive losing the cache, it's a critical dependency, not a cache.
- [ ] Don't cache low read/write-ratio data, must-be-fresh data, or a missing index.
- [ ] Cache-aside read: check cache → miss → load DB → populate → return.
- [ ] Cache-aside write: **delete the key, don't update it** — concurrent updates can leave a permanently stale value.
- [ ] The read/write race: a reader that missed can repopulate a stale value *after* the writer's delete.
- [ ] Mitigate with: mandatory TTL, delete-after-commit, delayed double delete, single-flight, CDC invalidation.
- [ ] Cache-aside gives eventual consistency with a bounded staleness window — say so explicitly.
- [ ] Read-through hides the load; write-through writes both synchronously; write-behind is fast and can lose data.
- [ ] Never invent write-behind for business data — that's an unbacked primary store.
- [ ] **Every entry gets a TTL**, as a correctness backstop against missed invalidation.
- [ ] **Add 10–20% jitter to every TTL** or mass-populated keys expire together and stampede.
- [ ] Sliding expiry never refreshes a permanently-hot key; prefer absolute for correctness-relevant data.
- [ ] Stampede: a hot key expires and every concurrent request queries the DB simultaneously.
- [ ] Single-flight/coalescing: one loader per key; Caffeine does it in-process, Redis needs a lock for cross-instance.
- [ ] Refresh-ahead (`refreshAfterWrite`) reloads asynchronously and serves the stale value meanwhile.
- [ ] **Serve-stale on error** (`stale-if-error`) is the highest-value resilience behaviour a cache has.
- [ ] Penetration = misses that don't exist in the DB either; avalanche = mass simultaneous expiry.
- [ ] Invalidation is hard because it couples every write path to every cache site, forever.
- [ ] **Versioned key prefixes** give atomic mass invalidation and prevent old-shape deserialisation during rolling deploys.
- [ ] Route all writes for an entity through one method, or use event/CDC-driven invalidation.
- [ ] In-process ≈ 100 ns but **per-instance**; distributed ≈ 0.5 ms but shared and restart-surviving.
- [ ] Multi-instance staleness makes data appear to *flap* between old and new on refresh.
- [ ] In-process cache immutable/reference data freely; be very careful with mutable or security-relevant data.
- [ ] Always expose cache hit ratio as a metric (`recordStats()` in Caffeine).
- [ ] Hybrid/near-cache: small short-TTL L1 (Caffeine) in front of a shared L2 (Redis).
- [ ] **Redis pub/sub is fire-and-forget** — a disconnected subscriber misses invalidations forever.
- [ ] Therefore pub/sub invalidation is an optimisation; a **short L1 TTL is the actual guarantee**.
- [ ] For reliable invalidation use Kafka or Redis Streams, not pub/sub.
- [ ] Redis command execution is single-threaded, so every command is atomic — and one `KEYS *` blocks everyone.
- [ ] Hash for partially-updated objects/sessions; ZSET for leaderboards, priority queues, sliding-window rate limits.
- [ ] Set for membership/uniqueness; List for simple queues; Bitmap/HyperLogLog for compact counting; Streams for a log.
- [ ] TTL is per key; expiry is lazy + sampled, so expired keys can still occupy memory.
- [ ] Redis-as-queue: `BLPOP` is at-most-once; use **Streams + consumer groups** if you must, real brokers if you can.
- [ ] **Redis persistence is lossy by default**: RDB loses minutes, AOF `everysec` loses ~1 s, managed Redis often has it off.
- [ ] Replication is async, so failover can lose recent writes — never a system of record.
- [ ] Default `maxmemory-policy` is `noeviction`, which makes **writes fail** when full.
- [ ] For a pure cache use `allkeys-lru` (or `-lfu`); `volatile-*` does nothing if keys lack TTLs.
- [ ] LFU resists scan pollution (a batch job evicting your hot set); Redis LRU is sampled/approximate.
- [ ] Eviction ≠ expiry; watch `evicted_keys` as an early warning.
- [ ] **Every input that changes the output belongs in the key** — user, tenant, role, locale, version, paging, filters.
- [ ] Omitting the user/role from the key can serve one user's data to another.
- [ ] Key convention `{app}:{entity}:{version}:{id}`; use `SCAN` not `KEYS`, `UNLINK` not big `DEL`.
- [ ] Negative-cache misses with a **distinct sentinel** and a short TTL (30 s–2 min) to prevent penetration.
- [ ] Bloom filters handle an unbounded space of invalid IDs.
- [ ] Cold start = 0% hit ratio = full traffic to the origin; a fleet restart or cache failover can be an outage.
- [ ] Warm the cache **behind a failing readiness probe** so the pod doesn't take traffic while empty.
- [ ] Keep warm-up out of the **liveness** probe or the pod gets killed mid-warm-up in a loop.
- [ ] Rate-limit/circuit-break the origin so cache loss degrades rather than destroys.
- [ ] HTTP caching is the free outer tier: `max-age`/`s-maxage`, `ETag`→304, `stale-while-revalidate`.
- [ ] `public` on an authenticated response can leak it via a shared cache — use `private`/`no-store`.
- [ ] Fingerprinted immutable URLs beat CDN purges.