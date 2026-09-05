# 27 — High-Level Design Drills

Scope: **repetition**. Guide 22 teaches the method — the 45-minute budget, the six requirement
numbers, estimation, storage selection, partitioning, quorums, resilience — and works four designs
(URL shortener, news feed, chat, payments ledger). This guide is ten more systems taken end to end,
each chosen because it forces a *different* decision. Read 22 first; nothing here re-teaches the
mechanisms.

The failure mode this guide exists to fix: knowing the method and still freezing on an unfamiliar
prompt, because every system practised so far was read/write-skewed CRUD. A rate limiter is an
atomicity problem, a metrics store is a write-amplification problem, seat booking is a
double-booking problem. Recognising which problem you were handed inside the first three minutes is
most of the score.

---

## 1. How to drill this file

Do **not** read a design straight through. Per system:

1. Read only the **Prompt** line. Start a 45-minute timer.
2. Do the whole thing on paper — requirements, numbers, API, data model, boxes, one deep dive,
   failure table, bottleneck. Talk out loud; record yourself if you can.
3. Then read the section. Score yourself against **Probes you must survive** — each is a real
   follow-up an interviewer uses to separate L4 from L5/L6 on that system.
4. Anything you missed is a *mechanism* gap, not a memory gap. Follow the cross-reference back to
   09/10/14/15/22 and read that section, not this one again.
5. Second pass a week later: 20 minutes, out loud, no paper. If you can't produce the arithmetic
   from scratch, you memorised the answer instead of the derivation — and interviewers change one
   number specifically to catch that.

Estimation constants used throughout (from 22 §3, memorise these instead of re-deriving):

| Constant | Value |
|---|---|
| Seconds per day | ~10⁵ (86,400) |
| Peak factor | 2–3× average |
| One Postgres primary | ~5k–15k writes/s, ~50k reads/s with a warm cache |
| One Redis node | ~100k ops/s, sub-ms p99 |
| One Kafka broker partition | ~10 MB/s sustained, 100k+ msg/s per broker |
| One node's comfortable disk | 1–2 TB (SSD), 10+ TB if it's cold/archival |
| Same-AZ RTT / cross-region RTT | ~0.5 ms / ~100 ms |
| Cassandra/Dynamo node | ~10k–50k writes/s, point lookups ~1–5 ms |

---

## 2. The compressed drill template

Nine slots. If a slot is empty at minute 40, that is where you lost points.

| # | Slot | Output it must produce | Minutes |
|---|---|---|---|
| 1 | Functional scope | 3–5 verbs with an actor; everything else named as out-of-scope | 3 |
| 2 | Non-functional numbers | DAU, read:write, object size, retention, p99 target, consistency per operation | 3 |
| 3 | Estimation | QPS avg/peak, storage/yr, bandwidth — **and the one resource that binds** | 4 |
| 4 | API | endpoint signatures incl. the idempotency and pagination shape | 3 |
| 5 | Data model | keys first. Partition key, sort key, the query each supports | 4 |
| 6 | High-level design | boxes and arrows that satisfy 1–5, sync path separated from async path | 8 |
| 7 | The one decision | the fork this system is actually about, both sides priced | 5 |
| 8 | Deep dive | whichever component the interviewer steers to, at mechanism level | 10 |
| 9 | Failure + ops | per box: dies / slow / full. Bottleneck named with headroom | 5 |

**Slot 7 is the one people skip.** Every system-design prompt has exactly one or two decisions that
determine the whole architecture; the rest is plumbing you could look up. Naming that fork out loud
("this design is really a choice between push and pull fan-out; here's the threshold where I switch")
is the single highest-scoring sentence in the round.

---

## 3. Forcing-function map — recognise the problem in three minutes

This table is the actual payload of this guide. Learn it as a lookup: prompt → the decision it hides.

| Prompt | Looks like | Actually tests | The fork (slot 7) |
|---|---|---|---|
| Rate limiter | Simple counter | Atomic read-modify-write across a fleet; per-key hot spots | Central exact vs. local approximate |
| Notification / push service | CRUD + a queue | Priority isolation and third-party quota management | One topic vs. per-priority topics |
| Typeahead / search | Autocomplete UI | Index build vs. query path separation; prefix data structures | Precomputed top-k vs. query-time ranking |
| Video upload + streaming | Big files | Async transcode pipeline and delivery economics | Bitrate ladder pre-transcode vs. on-the-fly |
| Nearby drivers (geo) | Map query | Spatial indexing + high-frequency location writes | Geohash/cell grid vs. quadtree/R-tree |
| Ad click aggregation | Counters | Exactly-once *effect* on aggregates, late/duplicate events | Streaming aggregate vs. batch recompute (lambda/kappa) |
| Metrics / time-series store | Write-heavy DB | Write amplification, cardinality explosion, downsampling | Row store vs. columnar/LSM with rollups |
| Distributed job scheduler | Cron | Exactly-once triggering under leader failover; time skew | Central leader-elected scheduler vs. sharded timer wheels |
| Seat / ticket booking | E-commerce | Serialised inventory decrement + hold expiry | DB row lock vs. reservation state machine |
| Collaborative editing | WebSockets | Concurrent-edit convergence | OT (server-ordered) vs. CRDT (peer-mergeable) |

**Trap:** solving the *visible* problem. "Nearby drivers" candidates design a beautiful REST API for
riders and never mention that 500k drivers each posting a location every 4 seconds is 125k writes/s
of throwaway data. Slot 3 exists to surface that before you draw anything.

---

## 4. Design — distributed rate limiter as a service

**Prompt:** design a rate-limiting service that every API gateway node in a 200-node fleet calls
before admitting a request.

**Functional:** decide allow/deny for `(api_key, route_class)`; support tiered limits
(free 100/min, pro 10k/min); return the standard headers. Out of scope: billing, WAF, bot detection.

**Non-functional numbers:**

| Number | Value | Consequence |
|---|---|---|
| Decisions/s | 500k peak | One Redis (~100k ops/s) is 5× short → shard |
| Added latency budget | p99 < 5 ms | One same-AZ round trip (~0.5 ms) is affordable; two are not |
| Keys | 1 M active | State is tiny — see below |
| Accuracy need | "roughly right" for marketing tiers, exact for paid quotas | This splits the design |
| On failure | Fail open (availability > protection) — say it explicitly | Redis outage must not 500 the whole API |

**Estimation, and why it matters here:** token-bucket state is two fields — `tokens` (float) and
`last_refill_ms` (long) — so ~100 B/key including overhead. 1 M keys = **~100 MB**. Memory is a
non-issue; *ops/s and RTT are the whole problem*. That inversion (tiny data, huge op rate) is the
insight the question is looking for, and it's why the answer is Redis and not a database.

Shard count: 500k ÷ ~80k ops/s per node (leaving headroom) = **7 → run 8–10 shards**, key routed by
`hash(api_key)`. No cross-shard operation exists, because a limit is scoped to one key.

**API:**

```
POST /v1/check  { key, route_class, cost: 1 }
  200 { allowed: true,  remaining: 8734, reset_at }
  200 { allowed: false, retry_after_ms: 420 }        // service returns data; gateway emits 429
```
Return `allowed:false` as a 200 from the limiter and let the gateway translate to `429` +
`Retry-After` + `X-RateLimit-Remaining` / `-Reset`. Mixing "the limiter is down" (5xx) with "you are
limited" (429) makes the gateway unable to fail open correctly.

**Algorithm choice — the table you must be able to draw:**

| Algorithm | State per key | Boundary behaviour | Verdict |
|---|---|---|---|
| Fixed window counter | 1 int + TTL | Admits **2× limit** across the boundary (100 at 11:59:59, 100 at 12:00:00) | Only when 2× burst is harmless |
| Sliding window log | ZSET of every timestamp | Exact | O(limit) memory/key — 10k/min tier = 10k entries/key. Rejected at scale |
| Sliding window counter | 2 ints (current + previous window, weighted) | Smooth, small error | Good default for "roughly right" |
| Token bucket | 2 fields, lazily refilled | Allows a controlled burst up to bucket size, then a steady rate | **The usual right answer** — burst is a feature |
| Leaky bucket (queue) | queue | Shapes rather than rejects; adds latency | Only when you may delay instead of reject |

**Lazy refill is the mechanism to state aloud:** no timer thread tops buckets up. On each check you
compute `tokens = min(capacity, tokens + (now - last_refill) * rate)`, then try to subtract `cost`.
1 M keys therefore cost zero background work; only touched keys are computed.

**Atomicity — this is the actual deep dive.** `GET tokens` → decide → `SET tokens` is a
check-then-act race: two gateway nodes read 1 remaining token and both allow. Fixes, in order of
preference:

1. **Redis Lua script** (or Redis Function): refill + compare + decrement + `PEXPIRE` in one
   server-side atomic step. One RTT, correct under any concurrency.
2. `INCR` + `EXPIRE` for the fixed-window variant — `INCR` is atomic, but setting the TTL is a
   second command, so a crash between them leaks an immortal key. Use `SET key 0 EX 60 NX` then
   `INCR`, or do both in Lua.
3. `WATCH`/`MULTI`/`EXEC` optimistic transaction — correct but retries under contention, which is
   exactly the hot-key case. Worse than Lua.

**Trap:** claiming Redis "is single-threaded so it's atomic". True per command, false across
commands — which is the only thing that matters here. Say *why* Lua fixes it: the script is one
command from the server's point of view.

**Two-tier design (the L6 answer for 500k/s):** each gateway node holds a local bucket granted a
slice of the global budget and only talks to Redis to refill its slice (e.g. asks for 200 tokens at
a time). Request-path RTT drops to zero for the common case; Redis ops fall by the batch factor.
The cost, stated as a number: worst-case over-admission ≈ `nodes × local_slice`, so 200 nodes × 200
tokens = up to 40k extra requests admitted in a window. Correct for tier throttling, **not** for
"exactly 5 free API calls per trial account" — that one needs the central path.

**Hot key:** one enterprise key at 100k/s lands on one Redis shard and one key inside it — sharding
by key doesn't help, because the *key* is the hot unit. Fix: split the key into N sub-buckets
(`key#0..key#7`), each granted `limit/N`, gateway picks one by `hash(node_id)`. Cost: a client whose
traffic is unevenly distributed across sub-buckets gets throttled below its nominal limit;
mitigate with more sub-buckets than nodes, or periodic rebalancing of the slices.

**Where to enforce:** cheapest layer first. CDN/edge WAF for volumetric abuse, gateway for per-key
quotas, service for per-operation cost limits. Rate limiting at the origin still spends origin
capacity on requests you reject — that's why L7/edge limits exist at all.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Redis shard | Gateway fails open to a conservative static local limit; alarm | Timeout at 5 ms → treat as unavailable, don't queue | Keys are TTL'd; eviction policy `volatile-ttl`, never `noeviction` |
| Gateway node | LB removes it; its local slice is simply unused | Its slice under-utilised (customer sees a low limit) | — |
| Clock | Skew makes refill grant too many/few tokens | — | Use Redis server time (`TIME`) inside the Lua script, never client time |

**Bottleneck:** Redis shard ops/s and the request-path RTT. Next step when it saturates: raise the
local-slice batch factor (cheap, costs accuracy) before adding shards (costs money, keeps accuracy).

**Probes you must survive:**
- Why not a database counter? (Row lock contention at 500k/s; ~10⁴ writes/s ceiling; durability you
  don't need for data that expires in 60 s.)
- What's the error of the local-slice design, as a number? (Above.)
- How do you rate limit *by IP* when a corporate NAT hides 50k users behind one? (Layer the limits:
  IP for abuse floor, key/account for quota; never IP alone.)
- Do you count rejected requests against the limit? (State a policy; usually no for token bucket,
  but say it — silent ambiguity reads as not having thought about it.)
- How do limits get updated without a deploy? (Config service / KV with a short-TTL local cache;
  bucket capacity changes must not reset current consumption.)

Cross-refs: 22 §15 (rate limiting theory), 15 (Redis mechanics, Lua, eviction), 12 (429 semantics
and headers).

---

## 5. Design — notification / push service

**Prompt:** design a service that delivers notifications over push (APNs/FCM), email, SMS and
in-app, for a product with 10 M DAU, including marketing campaigns.

**Functional:** `send(user, template, payload, priority)`; per-user channel preferences and quiet
hours; per-user dedupe; delivery-status tracking; campaign send to a segment of 10 M users.
Out of scope: template authoring UI, segmentation query engine (named as an upstream dependency).

**Non-functional numbers:**

| Number | Value | Consequence |
|---|---|---|
| Volume | 500 M notifications/day | 500M / 10⁵ = **5k/s average**, ~15k/s peak |
| Campaign spike | 10 M in 5 min | 10M / 300 = **33k/s** — 6× the organic peak, and it's bursty by nature |
| Payload | ~1 KB | 500 GB/day of events; 7-day log retention = 3.5 TB in Kafka |
| Latency | transactional p95 < 30 s (OTP < 5 s); marketing: hours are fine | Two different SLOs ⇒ two different paths |
| Delivery guarantee | at-least-once + dedupe | Duplicate OTP texts are a real production incident |

**The one decision (slot 7): priority isolation.** A single topic with a `priority` field does not
work — Kafka delivers a partition in order, so a 10 M-message campaign sitting ahead of an OTP in
the same partition delays it by the whole campaign drain time (head-of-line blocking). The design
is **separate topics with separate consumer pools and separate provider quotas**:
`notif.transactional`, `notif.digest`, `notif.marketing`. Sizing follows: transactional consumers
provisioned for peak with idle headroom, marketing consumers sized for cost and allowed to lag.

**API:**

```
POST /v1/notifications            Idempotency-Key: <uuid>
  { user_id, template_id, channel_hint, priority, data:{...}, dedupe_key?, ttl_s }
  202 { notification_id }                       // accepted, not delivered

POST /v1/campaigns                { segment_id, template_id, schedule_at, rate_limit_per_s }
  202 { campaign_id }                           // fan-out is a job, never an API loop
GET  /v1/notifications/{id}       -> { status: queued|sent|delivered|bounced|suppressed, attempts }
```

`202`, not `200` — the request path only durably enqueues. And a campaign is **one** API call that
creates a job; a client looping 10 M single sends is the wrong shape (no rate control, no
resumability, 10 M idempotency keys to manage).

**Data model:**

| Store | Key | Holds | Why |
|---|---|---|---|
| Preferences | `user_id` | per-channel opt-in, quiet hours + timezone, locale | Point lookup on the hot path → KV/Redis-cached |
| Device registry | `user_id` → list | device tokens, platform, app version, last_seen | Tokens expire; invalid ones must be reaped |
| Dedupe | `hash(user_id, dedupe_key)` | marker, TTL = dedupe window | Redis `SET NX EX` — atomic claim, not read-then-write |
| Delivery log | `(notification_id)`, and `(user_id, sent_at)` GSI | status transitions, provider message id | Cassandra/Dynamo: write-heavy, append-only, TTL 30–90 d |
| Suppression list | `email/phone hash` | hard bounces, unsubscribes, complaints | Legally load-bearing; checked before every send |

**High-level design:**

```
ingest API ──> [validate + idempotency claim] ──> Kafka: notif.{transactional|digest|marketing}
campaign job ─> segment reader ──> batch expander (1k users/message) ──┘

Kafka ──> notification workers  ──> preference/quiet-hours filter
                                ──> dedupe + suppression check
                                ──> template render (locale)
                                ──> channel router
                                      ├─ push worker  ─> APNs / FCM (per-provider token bucket)
                                      ├─ email worker ─> SES
                                      ├─ sms worker   ─> Twilio
                                      └─ in-app       ─> inbox store + websocket push
provider webhooks ──> status consumer ──> delivery log ──> metrics / DLQ
```

Note the **batch expander**: the campaign job emits messages carrying 1,000 user IDs, not 10 M
single-user messages. 10 M ÷ 1,000 = 10k messages to produce, which a single job does in seconds;
workers then expand in memory. Producing 10 M individual records at 33k/s is possible but pointless
and makes the campaign non-resumable at fine grain.

**Deep dives you should be ready for:**

*Third-party provider quota is the real bottleneck.* APNs, SES and especially SMS providers enforce
per-account rate limits (and SMS has per-country carrier limits). So each channel worker pool sits
behind a **per-provider token bucket** (§4) plus a circuit breaker; when the breaker opens you stop
consuming rather than burning retries. State the ceiling out loud: "our send rate is
min(worker capacity, provider quota), and it's the provider — so scaling workers past that just
grows a queue."

*Retry policy differs per notification class, and this is a scoring detail:*

| Class | Retry | TTL / give-up |
|---|---|---|
| OTP / 2FA | 2 fast retries, no backoff beyond seconds | 60 s — after that the code is useless, drop it |
| Transactional (receipt) | exponential backoff with jitter | 24 h |
| Marketing | 1 retry | drop; and never retry into the next quiet-hours window |

*Device-token hygiene:* APNs/FCM return `Unregistered`/`NotRegistered` for dead tokens. If you don't
consume that response and delete the token, your send volume inflates forever with silent
black-holed pushes and your delivery-rate metric is a lie. Same for email hard bounces → suppression
list, or your sender reputation degrades and *all* mail starts landing in spam.

*Dedupe:* `SET dedupe:{hash} 1 NX EX 3600` — claim before send. `EXISTS` then `SET` is the same
check-then-act race as §4, and it fires when a Kafka rebalance replays a batch.

*Quiet hours:* stored per user with a timezone, evaluated at *delivery* time, not enqueue time —
otherwise a 6-hour campaign drain sends at 3 a.m. to whoever is late in the queue. Deferred messages
go to a scheduled tier (§11's timer mechanism), not a `sleep` in the worker.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Ingest API | LB sheds; clients retry with the same `Idempotency-Key` | 202 path is a write to Kafka only — if Kafka is slow, fail fast, don't buffer in memory | — |
| Kafka | No ingest; API returns 503 (correct — never accept what you can't durably store) | Producer `acks=all` latency rises; watch p99 | Retention pressure — size for 7 days of peak |
| Worker pool | Consumer group rebalances, offsets replay → duplicates → dedupe layer earns its keep | Consumer lag alarm per topic (transactional lag is a paging alert; marketing lag is not) | — |
| Provider | Breaker opens; optionally fall back to another channel (push fails → in-app inbox) | Its p99 becomes your delivery latency | Quota exhausted → 429s from provider → back off, don't hammer |

**Bottleneck:** provider throughput, then worker-pool concurrency. Scaling step: more provider
accounts/pools per channel, partition by user so ordering per user is preserved.

**Probes you must survive:**
- Why not one topic with a priority field? (Head-of-line blocking, as above — this is *the* answer.)
- Guarantee exactly-once delivery? (You can't. At-least-once + idempotent effect via dedupe key;
  say it in those words — 22 §13.)
- 10 M-user campaign at 33k/s — where does it break? (Provider quota; so the campaign carries a
  `rate_limit_per_s` and drains over 30 min instead. Deliberate slow-down is the right answer.)
- Ordering: user gets "order shipped" before "order placed"? (Partition by `user_id` for
  per-user ordering; cross-channel ordering is not achievable — email and SMS have independent
  provider latencies. Solve it in copy, not in architecture.)
- How do you test this without spamming real users? (Sandbox provider adapters, seeded test
  segments, a global kill switch and per-template send caps — the ops face is part of the design.)

Cross-refs: 14 (Kafka partitions, consumer groups, DLQ), 15 (Redis `NX EX`), 22 §12/§13/§17.

## 6. Design — typeahead / search autocomplete

**Prompt:** design search autocomplete: as the user types, return the top 10 completions.

**Functional:** prefix → top 10 suggestions ranked by popularity; suggestions reflect trending
queries within the hour; handle one typo. Out of scope: the search results page itself, ranking of
documents (that's a different design).

**Non-functional numbers:**

| Number | Value | Derivation / consequence |
|---|---|---|
| Requests | 10 M DAU × 5 searches × ~5 keystrokes = 250 M/day → **2.5k/s avg, 7.5k peak** | A keystroke is a request; debouncing is a first-class design lever |
| Latency | p99 < 100 ms end-to-end, so **< 20 ms server** | Anything slower than typing is invisible to the user |
| Corpus | 100 M distinct queries with frequencies | Determines index size |
| Freshness | 1 hour is fine, except trending (minutes) | Two build paths |
| Read:write | ~10,000:1 | The index is effectively read-only; build offline |

**The one decision (slot 7): precompute the top-k per prefix, or rank at query time?** Autocomplete
is a *read-only, latency-critical, extremely skewed* workload, so the answer is precompute — the
query path must not sort candidates. Store the top-10 list **at every trie node**, so a lookup is
"walk `len(prefix)` pointers, return the attached array." No scan, no sort, no ranking at request
time.

**Index size arithmetic (do this out loud):** 100 M queries averaging ~20 characters, with heavy
prefix sharing, gives on the order of 10⁸ trie nodes. Each node storing 10 suggestions × ~30 B is
~300 B, so a naive trie is **~30 GB** — too big for one node's heap, fine for a sharded fleet or a
compressed FST/succinct trie (5–10× smaller). Shard by **first 1–2 characters** with each shard
replicated for read throughput; a request touches exactly one shard, so there's no scatter-gather.

**Two-path architecture:**

```
QUERY PATH (hot, read-only)
 client (debounce 50 ms, cancel in-flight) -> CDN/edge cache -> autocomplete servers (trie in RAM)

BUILD PATH (cold, offline)
 search logs -> Kafka -> hourly batch aggregation (Spark) -> weighted counts
             -> trie/FST build job -> immutable snapshot in S3 (versioned)
             -> servers download + load + atomic pointer swap
 5-min streaming window -> "trending" overlay merged at query time
```

**The cheapest big win is the CDN, and candidates miss it.** Prefixes of length 1–3 are a tiny set
(62³ ≈ 240k, and realistically only tens of thousands occur) but carry the large majority of
traffic, and their answers change hourly at most. Cache them at the edge with a 60-second TTL and
the origin fleet sees a fraction of the 7.5k/s. Say the number: "if 1–3 char prefixes are 70% of
traffic, the origin sees ~2.2k/s."

**Ranking:** score = `log(frequency) × recency_decay + personalisation`. Frequency-only ranking
freezes yesterday's queries in place, so decay (e.g. exponential with a 7-day half-life) is what
makes "trending" possible at all. If personalisation is required, the trie returns the **top 50**
candidates and a small query-time re-rank picks 10 using the user's history — keep the expensive
part bounded to 50 items.

**Trending fast path:** the hourly batch can't surface a term that started an hour ago. A streaming
job over a 5-minute window emits a small delta list (a few thousand terms) pushed to every server
and merged into results at query time. Two paths, one for the 99.9% of stable data and one tiny
mutable overlay — the same shape as the lambda split in §8.

**Typo tolerance:** don't run edit distance across 100 M terms at request time. Either
(a) precompute a **deletion-neighbourhood** index (SymSpell): store every term with up to k
characters deleted mapping back to the original, so lookup is a hash probe; or (b) fall back to a
BK-tree / n-gram candidate generation only when the exact prefix lookup returns fewer than 10 hits.
Cost of (a): index size grows by roughly the number of deletion variants (large but bounded); it
buys O(1) correction.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Autocomplete server | LB removes; peers serve (stateless w.r.t. user, index is a replica) | — | Heap pressure from index growth: alarm on snapshot size, cap suggestions/node |
| Build job | **Serve the previous snapshot.** Stale suggestions are invisible to users; a failed hard-swap is not | Snapshot lands late; freshness SLO breached, availability unaffected | — |
| Trending stream | Overlay goes empty → results fall back to hourly. Graceful degradation by construction | — | — |
| CDN | Origin takes full 7.5k/s — size the fleet for the no-cache case or admit the dependency | — | — |

**Bottleneck:** RAM per shard and index build time. Scaling step: finer prefix sharding, then a
compressed FST to buy another 5×.

**Probes you must survive:**
- Why is this not just `SELECT ... WHERE q LIKE 'pre%' ORDER BY freq LIMIT 10`? (A left-anchored
  `LIKE` *can* use a B-tree index for the range, but you then sort a potentially huge match set per
  keystroke at 7.5k/s; the precomputed top-k removes the sort entirely. Note the index is unusable
  for `'%pre%'` — 09.)
- Where does the debounce live and why does it matter? (Client, 50–100 ms + cancel in-flight
  requests: it cuts request volume several-fold for free. A design that ignores the client is
  incomplete.)
- How do you keep offensive or personally identifying queries out of suggestions? (Blocklist +
  minimum-frequency threshold (a query must be issued by N distinct users before it can ever be
  suggested) — this is a real, standard requirement.)
- Multi-language / non-Latin scripts? (Normalise and tokenise per locale, separate index per
  language; a byte trie over UTF-8 works but breaks on case/diacritic folding.)

Cross-refs: 15 (edge caching, TTL), 22 §19 (read models — Elasticsearch is never the source of
truth), 01 (tries).

---

## 7. Design — video upload and streaming

**Prompt:** design video upload, processing and playback for a video platform.

**Functional:** upload a file; process it into playable renditions; stream with adaptive quality;
count views. Out of scope: recommendations, comments, monetisation.

**Non-functional numbers — and here the *cost* number drives the architecture:**

| Number | Value | Derivation |
|---|---|---|
| Uploads | 50k/day × ~500 MB (10 min, 1080p) = **25 TB/day ingest** | Storage grows ~9 PB/yr before renditions |
| Rendition multiplier | ~1.5–2× the source across the ladder | So ~50 TB/day stored |
| Views | 50 M/day, ~5 min watched, ~3 Mbps 1080p | 50M × 300 s × 0.375 MB/s ≈ **5.6 PB/day egress** |
| Egress cost | at ~$0.02–0.08/GB off a CDN, PB/day is the dominant line item | Encoding efficiency and tiering are *architecture*, not optimisation |
| Skew | ~90% of videos get ~1% of views | Justifies treating popular and long-tail videos differently |

**The one decision (slot 7): pre-transcode the whole bitrate ladder for every video, or transcode
just-in-time for the long tail?** Pre-transcoding 50k videos/day × 6 renditions costs CPU and
storage for content that mostly never gets watched; JIT costs latency on first play and CPU at
serve time. The defensible answer is **hybrid**: on upload, produce a minimal ladder (e.g. 360p +
720p) so the video is playable immediately; produce the full ladder (240p → 4K) lazily, triggered
by view count crossing a threshold. Quote the saving: if 90% of videos never cross the threshold,
you avoid ~90% of the high-rendition encode cost.

**Upload path — never proxy bytes through your API:**

```
client -> POST /videos (metadata)        -> returns video_id + presigned multipart upload URLs
client -> PUT parts directly to S3       (5–100 MB parts, parallel, resumable, per-part retry)
client -> POST /videos/{id}:complete     -> S3 CompleteMultipartUpload
S3 event -> Kafka -> processing pipeline
```
Presigned direct upload removes your service from the 25 TB/day path entirely. Multipart gives
resumability on a flaky mobile connection — a single 500 MB `POST` that fails at 480 MB restarts
from zero, which is the actual user complaint this design exists to solve.

**Processing pipeline:**

```
validate (container, codec, duration, malware) ->
split into GOP-aligned chunks (~10 s) ->
fan out: N chunks × M renditions -> transcode workers (queue-driven, idempotent per chunk) ->
stitch per rendition -> package HLS + DASH (2–6 s segments + manifests) ->
generate thumbnails/sprites + captions (ASR) ->
publish: write manifest, flip status=READY, warm CDN
```
**GOP-aligned splitting is the mechanism to name:** you can only cut at a keyframe, so chunks are
independently decodable, which is what makes transcoding embarrassingly parallel — a 10-minute
video becomes 60 chunks transcoded concurrently, turning a 20-minute serial job into ~1 minute.
Each chunk job is keyed `(video_id, chunk_no, rendition)` and idempotent, so a worker crash costs
one chunk's work, not the video's.

**Playback:** the client fetches a manifest listing renditions and segment URLs, then picks a
rendition per segment based on measured throughput and buffer level (ABR). Segments and manifests
are immutable and fingerprinted, so they're CDN-cacheable forever — no purge logic. Access control
via short-lived signed CDN URLs (and DRM/AES-128 keys served separately if licensing demands it).

**Storage tiering** (this is where the cost number pays off):

| Age / popularity | Where | Renditions kept |
|---|---|---|
| New or popular | CDN edge + hot object storage | Full ladder |
| > 90 days, low views | Infrequent-access tier | 360p/720p only |
| Cold archive | Glacier-class, restore on demand | Source master only |
Keeping the source master forever is what makes re-encoding to a future codec (AV1) possible; drop
it and you can never improve efficiency on your back catalogue.

**View counts:** a view is not a page load — define it ("≥30 s or ≥50% watched"), dedupe by
`(user, video, 24h)`, and never `UPDATE videos SET views = views+1` at 50 M/day with celebrity skew
(row-lock hot spot). Emit playback heartbeat events → Kafka → stream aggregation → counter store,
displayed with a short cache. Approximate is acceptable for display; exact is required only if
someone is paid per view, in which case the batch recompute in §8 is the source of truth.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Transcode worker | Chunk job returns to the queue; idempotent key prevents double-publish | Queue depth is the leading indicator, alarm on it, autoscale on it | Spot-instance fleet + priority queue: paying-creator uploads before back-catalogue re-encodes |
| Packaging | Video stays `PROCESSING`; user sees an honest status, not a broken player | — | — |
| CDN edge | Next-nearest edge / origin shield absorbs it | Rebuffering ratio is the user-facing SLI, not server latency | — |
| Object store | Regional outage = playback outage; cross-region replication for popular content only (cost) | — | — |

**Bottleneck:** egress cost and transcode CPU, in that order. Neither is fixed by adding app servers
— which is precisely the point the interviewer is testing.

**Probes you must survive:**
- Why not transcode synchronously on upload? (Minutes of CPU per video; the request path would hold
  a connection for minutes and any failure loses the upload. Async + status polling is mandatory.)
- What's your first-play latency for a cold long-tail video under JIT, and is that acceptable?
  (Seconds; mitigate by always pre-baking one mid rendition.)
- How does the player recover from a bad segment? (Retry, then step down a rendition; manifests
  list alternates. ABR is failure handling, not just quality selection.)
- Live streaming instead of VOD — what changes? (Low-latency HLS/CMAF chunks, no full-file source,
  transcode is a real-time pipeline that must never fall behind, DVR window as a separate store,
  and you lose the "immutable and re-runnable" property that makes VOD easy.)

Cross-refs: 22 §20 (blobs, presigned upload, CDN), 14 (queue-driven fan-out), 18 (S3 storage
classes).

---

## 8. Design — nearby drivers (geo-proximity)

**Prompt:** design the backend that lets a rider see nearby available drivers and get matched.

**Functional:** driver publishes location; rider queries drivers within 3 km; dispatch offers a trip
to one driver at a time. Out of scope: pricing, routing/ETA engine (named as a dependency), payments.

**Non-functional numbers — the write rate is the whole question:**

| Number | Value | Derivation |
|---|---|---|
| Active drivers | 500k | — |
| Location updates | every 4 s ⇒ **125k writes/s** | 500k ÷ 4. This dwarfs the read path |
| Rider queries | 10k/s | Trivial by comparison |
| Payload | ~50 B (id, lat, lng, ts, heading) | 125k/s × 50 B ≈ 6 MB/s — bandwidth is fine, *op rate* is not |
| Durability of a location | **none** — it's worthless in 4 seconds | Unlocks the entire design |
| Query latency | p99 < 200 ms | Room for one store hop plus ranking |

**The one decision (slot 7): treat live locations as ephemeral state, not as data.** 125k writes/s
of last-write-wins values that expire in seconds must not touch a durable, indexed, replicated
database — you'd be paying for WAL, indexes and replication on rows you overwrite 15 times a minute.
Put them in **Redis (or an in-memory geo service) sharded by region, with a 30-second TTL**, and
stream a *copy* to Kafka for the durable telemetry needs (billing, replay, analytics). Two stores,
two purposes; conflating them is the classic wrong answer.

The TTL is doing real work: a driver whose app dies simply stops appearing in results after 30 s. No
health-check machinery, no reaper job — expiry *is* liveness detection.

**Spatial index choice:**

| Approach | Mechanism | Verdict |
|---|---|---|
| `WHERE lat BETWEEN .. AND lng BETWEEN ..` | Two independent B-tree ranges; the DB can only use one well, then filters | Fails at this scale; mention only to reject |
| **Geohash / S2 cell id** | Interleave lat/lng bits into one sortable string/int ⇒ a 2-D range becomes a 1-D prefix scan | **The answer.** Works in Redis, Dynamo, Postgres, anything sorted |
| Quadtree | Tree subdivides until a node holds ≤ N points; adapts to density | Great for static POIs; rebalancing under 125k writes/s is the problem |
| R-tree / PostGIS GiST | Bounding-box tree, rich geo queries | Right for "which polygon am I in"; wrong for churning points |
| Redis `GEOADD`/`GEOSEARCH` | Sorted set scored by a 52-bit geohash | The pragmatic implementation of the geohash answer |

**Precision arithmetic you should be able to recall:** geohash length 5 ≈ 4.9 km × 4.9 km, length 6
≈ 1.2 km × 0.6 km, length 7 ≈ 150 m × 150 m. For a 3 km radius, pick precision 5 and query the
**3 × 3 block of cells** (target cell + 8 neighbours), then filter by exact haversine distance and
cap the result set.

**Trap:** querying only the driver's own cell. A rider 20 m from a cell border misses every driver
on the other side — the bug is invisible in testing (it depends on where you stand) and instantly
recognisable to an interviewer. The 3×3 neighbour query is the fix, and stating *why* is the point.

**Hot cells:** downtown at rush hour puts 5,000 drivers in one cell, so a query fetches 5,000
members to return 10. Fixes: use a finer precision in dense areas (a per-city precision config, or
adaptive precision by cell population), cap and sample (`GEOSEARCH ... COUNT 50 ANY` — nearest-ish
is fine, since ranking re-orders anyway), and shard a dense cell's key by driver-id suffix.

**Reducing the 125k/s itself** — the most impressive lever, and it's client-side:

| Technique | Saving |
|---|---|
| Adaptive frequency: 2 s when moving fast, 30 s when parked/idle | Parked drivers are a large fraction — often a 3–5× cut |
| Suppress updates when displacement < 20 m and heading unchanged | Removes GPS jitter traffic |
| Batch 3 fixes per request (interpolate server-side) | 3× fewer round trips, at 12 s of staleness |
| Only publish while `status = available` | Drivers mid-trip don't need to be in the search index at all |

**Dispatch — the correctness part people forget:** two riders must not be offered the same driver.
Model the driver as a state machine `AVAILABLE → OFFERED → ASSIGNED → ON_TRIP` and make the
transition a **compare-and-set** (`SET driver:{id}:state OFFERED IF state == AVAILABLE`, or a
conditional write in Dynamo). The offer carries a 15-second timeout; on expiry, CAS back to
`AVAILABLE` and offer the next candidate. Ranking uses **road-network ETA, not haversine** — a
driver 500 m away across a river is 12 minutes out — so the geo index produces candidates and the
routing service orders them.

**Durable path:** every location fix also goes to Kafka, partitioned by `driver_id` (per-driver
ordering), landing in a time-series/columnar store for trip reconstruction, billing disputes and
demand heatmaps. This is where 10 TB/day of retained telemetry lives, not in Redis.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Redis geo shard | Locations for that region vanish; **fully repopulated within one update interval (4 s)** — the best failure story in this design, say it | Query p99 breach → degrade to a larger cap / coarser precision | 500k × ~100 B ≈ 50 MB. Memory is a non-issue; TTL bounds it |
| Location ingest | Drivers buffer locally and resend; stale > 30 s drops them from results (correct behaviour) | — | Shed low-priority updates (parked drivers) first |
| Dispatch | CAS state lives in the store, so a restarted dispatcher rebuilds nothing; offers time out and retry | — | — |
| Kafka | Telemetry gap; live matching unaffected — the two paths are independent by design | — | Retention sized for the analytics window |

**Bottleneck:** location write path (op rate), then dense-cell query cost. Scaling step: regional
sharding (a rider never queries across a metro boundary) and adaptive publish frequency, before
adding nodes.

**Probes you must survive:**
- Why not PostGIS? (Correct index, wrong write rate — 125k/s of updates on a GiST-indexed table
  means constant index churn and WAL for disposable data. Use it for geofences and zones, which
  *are* durable and low-churn.)
- Rider on a cell boundary — walk me through it. (3×3 cells, then haversine filter, then ETA rank.)
- How do you avoid double-offering a driver? (CAS state machine + offer TTL, above.)
- How stale can the map be? (Bounded by update interval + TTL; the UI interpolates between fixes so
  4 s of staleness is invisible — a product-level answer that scores.)
- Surge pricing input? (Cell-level supply/demand counters from the same stream, 1-minute windows —
  it reuses §9's aggregation pipeline rather than a new system.)

Cross-refs: 15 (Redis sorted sets, TTL), 14 (partition by key for per-entity ordering), 22 §8
(hot keys).

---

## 9. Design — ad click / event aggregation pipeline

**Prompt:** design a system that ingests ad impressions and clicks and serves both a near-real-time
dashboard and the numbers advertisers are billed on.

**Functional:** ingest events; aggregate by (ad, campaign, minute/hour/day, country); dashboard
within 1 minute; billing figures that are exact and reconcilable; suppress duplicate/fraudulent
clicks. Out of scope: ad serving/auction, fraud scoring models.

**Non-functional numbers:**

| Number | Value | Derivation |
|---|---|---|
| Events | 10 B impressions + 100 M clicks/day | 10.1 B ÷ 10⁵ = **~100k events/s avg, ~300k peak** |
| Event size | ~1 KB | **~10 TB/day** raw, 100 MB/s ingest — Kafka partition count follows from this |
| Dashboard freshness | < 1 min | Streaming, not batch |
| Billing accuracy | exact, auditable, restatable | Streaming alone is *not* sufficient |
| Retention | raw 30 d hot / 2 yr cold; aggregates 2 yr | Tiering required |

**The one decision (slot 7): you need two answers to the same question, and that is deliberate.**
A streaming aggregate is fast but approximate under late data, duplicates and job restarts. Billing
cannot be approximate. So:

| Path | Mechanism | Serves | Authority |
|---|---|---|---|
| **Speed layer** | Flink/Kafka Streams, 1-minute tumbling event-time windows → OLAP store (Druid/ClickHouse) | Dashboards, pacing, budget alerts | Advisory |
| **Batch layer** | Hourly/nightly recompute from the immutable raw log in object storage → same tables, overwrite by partition | Invoices, disputes, restatements | **Source of truth** |

Then **reconcile**: a job diffs speed-layer vs batch-layer totals per hour and alarms above a
threshold (say 0.1%). Being able to say "my dashboards are eventually-corrected and my invoices come
from a recomputable batch job over an immutable log" is a senior-level answer. The alternative
(kappa: one streaming path, replay the log through a new job version when you need to restate) is
also defensible — pick one and name what it costs (kappa needs exactly-once sinks and long Kafka
retention; lambda costs two implementations that can drift).

**Pipeline:**

```
edge collectors (thin, global, write-only) 
  -> Kafka  topic=events  partitioned by ad_id  (partitions >= 100 MB/s ÷ ~10 MB/s = 10+, in practice 100s)
  -> [tee 1] Flink: dedupe -> event-time windows -> aggregates -> ClickHouse/Druid  -> dashboard API
  -> [tee 2] raw sink -> S3/`s3://events/dt=2026-09-05/hr=14/` (Parquet, hour-partitioned, immutable)
                       -> nightly Spark recompute -> billing tables -> reconciliation job
```

**Idempotency and exactly-once *effect*:**
- Every event carries a `click_id` (UUID) minted at the edge. Dedupe in the stream job's keyed state
  (RocksDB) over a bounded window (e.g. 24 h), or with a Bloom filter fronting a KV store — bounded
  memory, small false-positive rate you must price ("a 1% FP rate drops 1% of legitimate clicks" is
  usually unacceptable, so use the exact keyed state and accept the state size).
- The sink must be idempotent: upsert keyed by `(window_start, ad_id, country)` so replaying a window
  after a restart overwrites rather than adds. This is the single most important detail — an
  at-least-once stream into an `INSERT`-only counter table produces silent over-billing.

**Late and out-of-order events:** mobile clients buffer offline and can deliver a click hours later.
Use **event time with watermarks**, an `allowedLateness` (say 1 hour) that re-fires updated windows,
and a **side output** for anything later than that, swept up by the batch layer. State the rule
plainly: "the dashboard is correct to within the watermark; the invoice is correct because it's
recomputed from the log."

**Hot keys:** a viral campaign concentrates on one `ad_id`, so one partition and one aggregation
task saturate. Fix with **two-phase aggregation**: key by `(ad_id, salt 0..15)` for the local
pre-aggregate, then re-key by `ad_id` to merge 16 partial sums. Volume through the second stage is
16 rows per window per ad instead of millions of events.

**Cardinality:** "unique users per campaign" cannot be a set — 10⁹ ids × 16 B is intractable per
group. Use **HyperLogLog** (~12 KB/counter, ~2% relative error, and mergeable across windows, which
is why it works with hierarchical roll-ups). Say the error out loud; approximate uniques are
standard, approximate *billing* is not.

**Storage layout for the OLAP side:** columnar, partitioned by time, pre-aggregated at multiple
granularities (minute → hour → day → month), with minute rollups expiring after ~7 days. Dashboard
queries hit the coarsest granularity that satisfies the range — a "last 90 days" chart must never
scan minute rows.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Edge collector | Regional DNS/LB failover; clients retry (same `click_id`, so dedupe absorbs it) | Client-side buffering | Shed impressions before clicks — clicks are the billable, rarer event |
| Kafka | Ingest stops = data loss at the edge; local disk buffering on collectors is the mitigation | Producer latency; watch ISR shrinkage | Retention is the safety net for replay — sizing it *is* the disaster plan (e.g. 7 days) |
| Flink | Restart from last checkpoint, replay from committed offsets; idempotent sink makes this safe | Backpressure → consumer lag alarm; scale parallelism | State size (dedupe window) is the real limit; incremental RocksDB checkpoints to S3 |
| OLAP store | Dashboards down; **billing unaffected** (different path) — a nice property to point out | Query concurrency limits; pre-aggregate harder | Tier old partitions to cold storage |
| Batch job | Yesterday's invoice is late; rerun is idempotent because it overwrites whole partitions | — | — |

**Bottleneck:** Kafka ingress bandwidth and stream-job state size. Scaling step: more partitions
(planned up front — you cannot cheaply repartition a keyed topic without breaking key locality) and
higher job parallelism.

**Probes you must survive:**
- Why can't the dashboard just query the raw log? (10 TB/day scanned per query; the pre-aggregation
  is the design.)
- How do you handle a duplicate click? (Edge-minted id + keyed dedupe + idempotent upsert. Name all
  three layers, not one.)
- An advertiser disputes yesterday's invoice — what do you do? (Recompute the hour partitions from
  the immutable raw log; that capability is exactly why the raw log exists.)
- What if you must repartition the Kafka topic? (Adding partitions changes `hash(key) % n` placement,
  so ordering and dedupe locality break for existing keys; you either over-provision partitions on
  day one or run a migration through a new topic.)
- Fraud filtering? (A separate scoring stage that marks rather than deletes; billing reads the
  filtered view, analytics reads both. Never destroy raw data at ingest.)

Cross-refs: 14 (partitions, transactions, consumer lag), 22 §13/§19, 20 (metrics and alerting on
lag).

## 10. Design — metrics / time-series store

**Prompt:** design the storage and query system behind a monitoring product (think Prometheus /
Datadog).

**Functional:** ingest `(metric_name, labels{}, timestamp, value)`; query a range with filters and
aggregations; retain 15 months. Out of scope: alerting rules engine, dashboard UI, tracing.

**Non-functional numbers — do the compression arithmetic, it *is* the design:**

| Number | Value | Derivation |
|---|---|---|
| Hosts × series | 50k hosts × 500 series = **25 M active series** | The number that actually binds (see below) |
| Scrape interval | 10 s ⇒ **2.5 M datapoints/s** | 25 M ÷ 10 |
| Naive size | 16 B/point (8 ts + 8 float) ⇒ 40 MB/s ⇒ **3.4 TB/day** | Untenable at 15-month retention |
| Compressed | **~1.4 B/point** with delta-of-delta + XOR | ⇒ ~300 GB/day, ~10× reduction |
| Query | p99 < 1 s for a 6-hour dashboard, tolerable seconds for 90-day | Forces downsampled roll-ups |

**The one decision (slot 7): a time-series store is not a row store, and the reason is
compressibility.** Because points arrive in timestamp order per series, you store each series as a
*column* of values in time-ordered chunks and encode:

- **Timestamps: delta-of-delta.** Scrapes are ~10 s apart, so the second-order delta is almost
  always 0 and costs *one bit*.
- **Values: XOR against the previous value** (Gorilla). Most gauges barely move, so the XOR has long
  runs of identical leading/trailing zero bits; encode only the meaningful window.
- **Counters** are monotonic, so delta encoding plus varints is near-free.

That is the 10× that makes the product viable. A candidate who says "put it in Postgres" hasn't
priced 3.4 TB/day; a candidate who names delta-of-delta and XOR has demonstrated the whole insight.

**Architecture:**

```
agents ──(push, or server pulls /metrics)──> ingest/relay tier (stateless; validates, drops
                                             high-cardinality labels, enforces per-tenant limits)
    -> series hash -> ingester shard (replication factor 2–3)
         head block: last ~2 h in memory + append-only WAL on local disk
         -> flush: immutable compressed block (2 h) on disk
         -> compaction: 2 h blocks -> 1 d -> and roll-ups (5 m, 1 h aggregates)
         -> ship blocks to object storage (long-term, queried by a store-gateway)
query ──> query frontend (split by time range, cache, fan out) -> ingesters (recent) + store-gateway (old)
                                                                 -> merge, dedupe replicas, aggregate
```

**The label index.** `http_requests{service="checkout",status="500"}` must be findable without
scanning all series. Each `label=value` pair maps to a **posting list** of series ids (an inverted
index, same structure as full-text search); a query intersects the posting lists of its matchers and
then reads only those series' chunks. Regex matchers (`status=~"5.."`) must expand to a set of
values first — which is why an unanchored regex over a high-cardinality label is the query that
kills the cluster.

**Cardinality is the failure mode of this entire product category — expect it as the deep dive.**
Every distinct label-value combination is a *new series* with fixed per-series overhead (index
entries, an in-memory head chunk, ~1–4 KB). Putting `user_id`, `request_id`, `trace_id`, a raw URL
path or an unbounded error message in a label turns 500 series into 5 M and OOMs the ingesters.
Defences, all of which you should be able to list:

| Defence | Mechanism |
|---|---|
| Per-tenant active-series limit | Reject new series past the quota, keep existing ones working, emit a `series_limit_exceeded` metric |
| Label allow/deny list at the relay | Drop or hash offending labels before they reach storage |
| Cardinality monitoring | A per-metric series counter, top-N dashboard, alert on the *rate of growth* |
| Exemplars / traces for high-cardinality identity | `request_id` belongs on a trace or a log line, never on a metric label — this is the one-sentence rule |

**Out-of-order writes:** the whole encoding assumes append-in-order per series. Accept a bounded
out-of-order window (minutes, into the head block) and reject anything older with an explicit
error; unbounded out-of-order support means rewriting immutable compressed blocks, which is a
different (and much more expensive) system.

**Downsampling / retention tiers:**

| Age | Resolution | Where |
|---|---|---|
| 0–2 h | raw 10 s | head block, memory + WAL |
| 2 h – 15 d | raw 10 s | local SSD blocks |
| 15 d – 90 d | 5 m roll-ups (min/max/sum/count/avg) | object storage |
| 90 d – 15 mo | 1 h roll-ups | object storage, cold |
Keep `count` and `sum` (not just `avg`) in roll-ups, or you can never re-aggregate correctly across
groups — averaging averages is wrong. Percentiles need histogram buckets, not values, for the same
reason (20 §, and it's a favourite follow-up).

**Replication and query dedupe:** the relay writes each series to 2–3 ingesters, so an ingester loss
loses nothing. Queries fan out to all replicas and **deduplicate by (series, timestamp)**, which also
patches gaps when one replica missed a scrape. This is cheaper than consensus and is the standard
answer: no quorum, just idempotent duplicate writes plus merge-on-read.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Ingester | Replica serves; on restart, replay the **WAL** to rebuild the head block; unflushed data beyond the WAL is lost (bounded, acceptable for metrics) | Backpressure to relay → relay buffers briefly then drops *oldest* samples (freshness > completeness for monitoring) | Local disk full = the classic monitoring outage; alarm on block-flush lag and disk headroom |
| Relay | Stateless, LB re-routes | — | Enforce limits here, not downstream |
| Object storage | Long-range queries fail; recent data (the on-call path) still works — correct priority ordering | — | — |
| Query frontend | Retry; results are idempotent | Split long ranges into sub-queries, cache per-step results, cap concurrent series per query | Return a partial-result flag rather than OOMing the cluster |

**Bottleneck:** **active series count** (memory + index), not datapoints per second. Say that
explicitly — it's the discriminating statement, because the naive answer optimises for write
throughput and then dies of cardinality.

**Probes you must survive:**
- Why not Cassandra with `(series_id, ts)`? (It works and has been done, but you pay per-cell
  overhead and lose the columnar chunk encoding, so you land back near 10× the storage. Also every
  query becomes a wide-row scan without a label index.)
- What does `rate()` over a counter need to be correct? (Counter-reset detection — a process restart
  sends the counter to 0, so the function must treat a decrease as a reset, plus extrapolation at
  window edges.)
- 25 M series over how many shards? (At ~2–4 M series per ingester, ~8–12 shards × replication 3.
  Derive it; don't assert it.)
- How do you support a 90-day p99 latency chart? (Histogram buckets recorded at ingest and
  aggregated; you cannot compute a percentile from stored averages, ever.)

Cross-refs: 20 (metrics types, histograms, SLIs), 09 (inverted index vs B-tree), 22 §19/§21.

---

## 11. Design — distributed job scheduler

**Prompt:** design a service that runs jobs on a schedule (cron expressions) and one-off delayed
jobs, for hundreds of internal teams.

**Functional:** register a schedule; fire the job at the right time; retry on failure; report status.
Out of scope: what the jobs do (they're HTTP/queue targets), workflow DAGs (name it as the layer
above).

**Non-functional numbers:**

| Number | Value | Consequence |
|---|---|---|
| Registered jobs | 10 M (mostly one-off delayed tasks) | Can't hold all in memory; needs a durable index by fire time |
| Triggers | 500/s average, **5k/s peak at :00 of the hour** | The peak is structural, not random — see thundering herd |
| Accuracy | ±1 s for cron, ±5 s for delayed | Rules out a 60-second polling loop as the only mechanism |
| Guarantee | at-least-once fire, **never** double-fire in the common case | Exactly-once is impossible; idempotent execution is mandatory |
| Job duration | ms to hours | Scheduling must be separated from execution |

**The one decision (slot 7): separate *scheduling* from *execution*, and shard the timer.** A single
leader scanning a table is simple and correct but caps at that node's scan rate and creates a
fail-over gap. The scalable shape is: partition the job space by `hash(job_id) % N`, give each
partition a **lease** held by one scheduler node, and have each node keep only the *next few minutes*
of its partition in an in-memory timer, backed by the durable store. Firing means **enqueueing a
message**, never running the job in the scheduler.

**The simple version you should present first (and it's the right answer up to a few thousand/s):**

```sql
-- durable index by fire time; the whole design in one statement
SELECT job_id, payload FROM jobs
 WHERE next_run_at <= now() AND state = 'READY'
 ORDER BY next_run_at
 LIMIT 100
 FOR UPDATE SKIP LOCKED;         -- multiple pollers, no contention, no double-claim
-- then: UPDATE jobs SET state='CLAIMED', claimed_until=now()+interval '30 s' ...
```
`FOR UPDATE SKIP LOCKED` is the mechanism to name: it lets N pollers work the same queue table
concurrently without lock convoys and without any of them claiming the same row. Index on
`(state, next_run_at)`. Say the ceiling out loud (~a few thousand claims/s on one primary, limited
by write amplification on the index) and *then* offer the sharded design for beyond it.

**The scaled version:**

| Layer | Mechanism |
|---|---|
| Durable store | `jobs` table/KV partitioned by `hash(job_id)`; or Redis ZSET per partition, `score = fire_time_ms` |
| Due scan | `ZRANGEBYSCORE now-∞ now LIMIT n` + `ZREM` **in one Lua script** (atomic claim; the two-command version double-fires) |
| Near-term timer | In-memory **hierarchical timing wheel** for the next 60 s ⇒ millisecond accuracy with O(1) insert, no polling |
| Partition ownership | Lease in etcd/ZooKeeper/Dynamo with a **fencing token**; a paused-GC owner that wakes up finds its token stale and stops |
| Fire | Produce to Kafka/SQS with dedupe key `(job_id, scheduled_epoch)`; a unique constraint or the queue's dedupe window absorbs a double-produce |
| Execute | Separate worker pool; visibility timeout + heartbeat for long jobs; retries with backoff; DLQ after N attempts |

**Why the fire key includes the scheduled time:** `(job_id, scheduled_epoch)` makes the *occurrence*
the unit of idempotency. `job_id` alone would suppress tomorrow's legitimate run; nothing would
suppress a duplicate of today's.

**Misfire policy — the question that separates candidates.** The scheduler was down 10 minutes;
a job scheduled every minute now has 10 missed occurrences. There is no universal right answer, so
it must be **configuration, declared per job**:

| Policy | Behaviour | Fits |
|---|---|---|
| `FIRE_ALL` | Run all 10 catch-ups | Idempotent aggregations that must not skip a period |
| `FIRE_ONCE` | Run once now, discard the rest | Cache refresh, health sweeps |
| `SKIP` | Drop them; wait for the next scheduled time | Anything time-sensitive (a 9 a.m. digest at 11 a.m. is spam) |

**Thundering herd:** everyone writes `0 * * * *`, so 5k jobs fire on the same second and the
downstream services see a spike 10× the average. Fixes: deterministic **jitter** derived from
`hash(job_id)` spread across the minute (deterministic so the offset is stable run to run), a
per-tenant fire-rate limit (§4 again), and admission smoothing in the executor pool. Naming this
unprompted is a strong signal.

**Clocks:** never compare a *client's* clock to a fire time. The scheduler's own clock, NTP-synced,
is the authority; log skew and alarm on it. A node whose clock jumps backwards must not re-fire the
window it already fired — which is exactly what the `(job_id, scheduled_epoch)` dedupe key protects.

**Time zones and DST — a real correctness trap:** `0 2 * * *` in a zone that skips 02:00 on a DST
transition never fires that day, and fires twice on the fall-back day. Store the schedule as
(cron expression + IANA zone), compute the next occurrence with a zone-aware library, and define
the DST policy explicitly (usual answer: run once, at the first valid instant).

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Scheduler node | Its lease expires; another node takes the partition and re-scans the durable store — the in-memory wheel is a cache, never the truth | Fires drift late; alarm on **fire lag** (`now - scheduled_at`), the key SLI of this system | Partition split |
| Lease store (etcd) | No ownership changes; existing owners keep firing until their lease expires, then everything stops. Fail *closed* is correct here — double-firing is worse than late firing | — | — |
| Queue | Jobs can't be dispatched; scheduler must not drop them — leave them claimed with a short `claimed_until` so they're retried | Backlog grows; consumer lag alarm | — |
| Worker | Visibility timeout expires → redelivery → **idempotent job code is the contract**, documented for tenants | Heartbeat extends the lease; a job with no heartbeat gets killed and retried | Autoscale on queue depth |

**Bottleneck:** due-scan rate against the durable store, then queue throughput. Scaling step: more
partitions (each an independent scan), and widen the in-memory horizon to shrink scan frequency.

**Probes you must survive:**
- Why not one node with an in-memory `ScheduledExecutorService`? (No durability — a restart loses
  every pending job; no horizontal scale; no failover. Fine for one process, not a platform. See 05.)
- How do you guarantee a job runs exactly once? (You don't. At-least-once firing + idempotent
  execution keyed on `(job_id, scheduled_epoch)`. Say the words "exactly-once *effect*".)
- Two nodes both think they own partition 7 — what happens? (Both fire; the dedupe key means the
  queue accepts one occurrence. Fencing tokens make it rare; idempotency makes it harmless. Defence
  in depth, not one mechanism.)
- A tenant registers 1 M jobs all at midnight. (Per-tenant quotas and rate limits, deterministic
  jitter, and a fair-share scan so one tenant can't starve a partition.)

Cross-refs: 05 (timers, executors), 09 (`SKIP LOCKED`, index on the claim predicate), 14 (visibility
timeout, DLQ), 22 §13/§17.

## 12. Design — seat / ticket booking

**Prompt:** design ticket booking for events — 50,000 seats, 500,000 people hitting "buy" the second
sales open.

**Functional:** browse the seat map; hold specific seats for 10 minutes while paying; confirm or
release. Out of scope: pricing/dynamic pricing, payment processor internals (a dependency), delivery
of tickets.

**Non-functional numbers — note the shape, it's the opposite of every other design here:**

| Number | Value | Consequence |
|---|---|---|
| Concurrent users at drop | 500k in the first 60 s | ~8k+ req/s of *reads* on one event's seat map |
| Inventory | 50k seats — a **tiny, intensely contended** dataset | The write path is small and must be *serialised*, not scaled out |
| Reserve attempts | > 50k against 50k seats, concentrated on the "good" ~2k seats | Contention, not throughput, is the problem |
| Correctness | **zero double-booking**; linearizable per seat | The one design in this file where eventual consistency is simply wrong |
| Hold TTL | 10 minutes | Expiry must be correct without depending on a background job |

**The one decision (slot 7): make the reservation a single conditional write, and shape the demand
in front of it.** Two halves:

*(a) The correctness core — one statement, no read-then-write:*

```sql
UPDATE seats
   SET state = 'HELD', hold_id = :hold, hold_expires_at = now() + interval '10 minutes'
 WHERE seat_id = :seat
   AND (state = 'AVAILABLE'
        OR (state = 'HELD' AND hold_expires_at < now()));   -- expiry is evaluated, not swept
-- rows affected = 1 -> you got it. 0 -> someone else did. That is the whole protocol.
```
Checking availability and then inserting a booking is a time-of-check/time-of-use race that *will*
double-book under this load; the atomic conditional update is the fix, and `rows_affected` is the
answer. Equivalent shapes: a Dynamo conditional write on the seat item, or `SETNX seat:{id}` with
a TTL when the inventory lives in Redis (with a durable reconciliation behind it, because money).

**The expiry trick worth stating explicitly:** an expired hold is treated as available *by the
predicate*, so correctness never depends on the sweeper running. A background job still tidies rows
(so the seat map renders correctly and metrics are sane), but if it dies, nothing breaks. Designs
that rely on a reaper to free inventory sell fewer tickets than they have whenever the reaper lags.

*(b) Demand shaping — a virtual waiting room.* Do not let 500k clients queue on your database.
Admit users through a token gate: on arrival, a client gets a position in a Redis queue and a
signed admission token released at a controlled rate (say 2,000/s), which is the rate the booking
path can serve comfortably. Everyone else sees an honest position and estimated wait. This is the
same token bucket from §4 applied to *users* instead of requests, and it converts a stampede into a
throughput problem you have already sized.

**Read path:** the seat map is served from cache/CDN with a few seconds of staleness and rendered
optimistically; a user clicking a seat that was taken 2 seconds ago gets a clean "taken, pick
another" from the conditional write. Trying to keep 500k clients' seat maps strongly consistent is
both impossible and unnecessary — **strong consistency at the commit point, eventual consistency in
the display** is the sentence that scores.

**Booking flow as a state machine (with the payment saga):**

```
AVAILABLE --hold--> HELD --payment authorised--> BOOKED
              ^        |                            |
              |        +--timeout/cancel-----------+ |
              +--payment failed (compensate: release)+
```
Payment is an external call with its own latency and failure modes, so it must not run inside the
seat-holding transaction (never hold a DB row lock across a third-party HTTP call — that's how you
turn a 300 ms payment p99 into a connection-pool exhaustion outage). Hold, commit, then authorise;
on failure, compensate by releasing. Every step carries an idempotency key so a client retry doesn't
buy two tickets (22 §13).

**Contention on the good seats:** if users pick exact seats, the top 100 seats receive thousands of
simultaneous conditional updates — all but one fail, and the losers immediately retry on the *next*
best seat, producing a retry storm that walks down the seat map. Mitigations, in increasing order of
product change:

| Mitigation | Effect |
|---|---|
| Server-side "best available" allocation | The server picks from a randomised candidate set — contention becomes a queue with near-uniform distribution instead of a hot row |
| Pre-partition inventory into blocks per app node | Each node hands out its own block, so no cross-node contention; steal a block when yours empties |
| Randomised candidate offer (offer 5 seats, user confirms one) | Spreads attempts across the hot set |
| Lottery / queue-based allocation for high-demand events | Removes real-time contention entirely; the industry answer for extreme drops |

**Sharding:** by `event_id`, which is natural — no query crosses events. The consequence, which you
should volunteer: **one hot event is one hot shard**, so a stadium drop concentrates on a single
primary. That's why the block-partitioning mitigation exists, and why the read path is cached
aggressively.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| Booking DB primary | Failover to a **synchronous** replica; async replication here can lose an acknowledged booking and double-sell the seat — the one place semi-sync is worth its RTT | Conditional updates queue; the waiting room is the pressure valve (drop the admission rate) | Inventory is 50k rows — size is never the issue, contention is |
| Waiting-room Redis | Fail closed to a conservative fixed admission rate; do **not** open the floodgates | Positions drift; cosmetic | — |
| Payment provider | Circuit breaker; holds expire naturally and inventory returns — the TTL is the compensation of last resort | Extend the hold? No — keep the TTL, tell the user to retry; long holds starve inventory | Queue authorisations, but never confirm a booking you haven't authorised |
| Seat-map cache | Origin read load spikes; serve a stale map with a banner | — | — |

**Bottleneck:** serialised writes per event shard (and per hot seat within it). Scaling step: block
partitioning of inventory and best-available allocation — *not* more replicas, which do nothing for
a write-contention problem.

**Probes you must survive:**
- Show me the exact statement that prevents double-booking. (The conditional `UPDATE`; explain
  `rows_affected`.)
- Why not `SELECT ... FOR UPDATE` then update? (It's correct, but it holds a lock for a round trip
  and serialises harder than needed; the single conditional statement is one round trip and no
  application-visible lock. Both beat check-then-act — know the difference.)
- What if the user's browser closes mid-payment? (Hold expires by predicate; the payment webhook
  arriving late must either find a still-valid hold or trigger a refund path — define it.)
- Is Redis alone enough for inventory? (For general admission counts with reconciliation, yes:
  `DECR` is atomic. For assigned seats plus money plus audit, the durable store owns the truth and
  Redis is at most a fast rejection filter.)
- 10 M-seat "general admission" event? (Now it's a counter, not rows: atomic `DECRBY` with a
  reservation record per success, reconciled against the counter — the problem changes shape, which
  is the point of the question.)

Cross-refs: 09 (isolation levels, lost update, `FOR UPDATE`), 15 (Redis atomics), 22 §9/§13/§17.

---

## 13. Design — collaborative document editing

**Prompt:** design a Google-Docs-style editor: multiple people editing one document simultaneously,
with cursors, offline support and version history.

**Functional:** apply concurrent edits and converge to the same document for everyone; show
collaborator cursors; merge edits made offline; browse history. Out of scope: rendering, comments,
permissions model (named as a dependency).

**Non-functional numbers:**

| Number | Value | Consequence |
|---|---|---|
| Active docs | 50k concurrent, ~2–3 editors each | Per-document state, so the fleet is partitioned by doc |
| Op rate | ~3 ops/s/editor ⇒ **~300k ops/s** fleet-wide, ~100 B/op | Tiny payloads, huge message count — WebSocket, not HTTP polling |
| Fan-out | each op to 2–3 peers, plus presence | Per-doc broadcast, not global pub/sub |
| Latency | local echo **0 ms** (optimistic), remote < 100 ms | Clients must apply their own ops immediately and reconcile later |
| Durability | no acknowledged edit may be lost | An append-only op log plus snapshots |

**The one decision (slot 7): OT or CRDT.** This is the entire question, and the interviewer wants
the trade-off, not a buzzword.

| | **OT** (operational transformation) | **CRDT** (e.g. RGA / Yjs) |
|---|---|---|
| Convergence mechanism | A server imposes a total order; each op is *transformed* against the concurrent ops that beat it (`insert@5` becomes `insert@6` if someone inserted before it) | Every character gets a globally unique, densely orderable id; operations commute, so any application order converges |
| Needs a central sequencer | **Yes** — all sessions for a doc must be pinned to one authority | No — peer-to-peer and offline-first work naturally |
| Document state | Plain text + a revision number. Small | Text + position ids + **tombstones** for deletes. Metadata can exceed the content |
| Hard part | The transformation functions — O(op-type²) cases, notoriously easy to get subtly wrong | Tombstone garbage collection (you can't drop a tombstone until every replica has seen past it) and memory growth |
| Offline for hours | Painful: a long op chain must be transformed against a long history | The natural case |
| Verdict | **Default for a server-mediated editor:** small payloads, small state, mature (it's what Docs uses) | Choose when offline-first, P2P, or multi-master-across-regions is a hard requirement |

State the decision as a rule: *server-mediated, always-online editor → OT; offline-first or
decentralised → CRDT.* Then note the cost you accepted (with OT: doc sessions are sticky and
failover needs care — which is the next section).

**Architecture:**

```
clients --WebSocket--> WS gateway (terminates TLS, auth, no doc state)
                          |  routes by doc_id via a registry: Redis  doc_id -> session_server
                          v
                  doc session server  (single owner per doc, holds in-memory doc state + revision)
                     - orders incoming ops, transforms, assigns revision numbers
                     - broadcasts transformed ops to the doc's other clients
                     - appends to the durable op log (Kafka/DB), snapshot every N ops or T seconds
                     - presence/cursors: ephemeral, Redis pub/sub with TTL, never persisted
history service <- snapshots + op ranges in object storage
```

**Single-writer-per-document is the load-bearing constraint of the OT design.** It gives you a
sequencer for free and makes ordering trivial, at the price of: (a) sticky routing (registry lookup
in Redis, gateway forwards), and (b) a failover story. Failover: the session lease expires, another
node claims the doc, loads the **latest snapshot + the tail of the op log**, and rebuilds state;
clients reconnect announcing their last known revision and receive the ops they missed. Clients
therefore must buffer unacknowledged local ops and resend them, tagged `(client_id, client_seq)` so
the server can drop duplicates idempotently.

**Client-side algorithm (say this out loud, it's the part that makes the UX work):** apply your own
op locally and immediately; send it with the revision you were at; keep it in a pending buffer;
when the server's transformed ops come back, transform your pending buffer against them and rebase.
Zero-latency typing with eventual convergence — the same optimistic-then-reconcile pattern as the
seat map in §12, applied to text.

**History and undo:** the op log *is* the history. Snapshot every N ops (say 1,000) so restoring a
version is "nearest snapshot + replay the ops after it" rather than replaying from creation. Undo is
not "apply the inverse op" naively — in a concurrent document the inverse must itself be transformed
against everything that happened since, and undo is scoped **per user** (undoing your own last edit,
not your collaborator's). Naming that subtlety is a strong signal.

**Large documents:** an in-memory doc plus an unbounded op log doesn't scale to a 500-page document
with a million ops. Compact: periodic snapshots plus op-log truncation, and for CRDTs, tombstone GC
once all replicas have acknowledged a version vector.

**Failure table:**

| Box | Dies | Slow | Full |
|---|---|---|---|
| WS gateway | Clients reconnect (with exponential backoff + jitter — 50k clients reconnecting at once is a self-inflicted DDoS); state lives in the session server, not here | Op latency rises; UX degrades gracefully because local echo is instant | Connection count per node is the capacity unit (~50–100k sockets/node, file-descriptor bound — 11) |
| Session server | Lease expires → new owner replays snapshot + log tail; clients resend unacked ops | The doc's ops queue; ordering is preserved, so correctness holds | Rebalance docs across nodes; a single doc with 500 editors is the hot-doc case (cap editors, or shard broadcast through a fan-out tier) |
| Op log (Kafka/DB) | **Stop accepting edits** — you must not acknowledge an edit you can't durably store; clients go read-only with a banner | Acks slow; batch appends | Retention: keep the log until snapshotted, then archive |
| Presence (Redis) | Cursors disappear, editing unaffected — correct blast-radius separation | — | TTL-bounded by construction |

**Bottleneck:** per-document single-owner throughput and socket fan-out. Scaling step: shard by doc
(trivially horizontal across docs), and for a pathological single doc, a broadcast fan-out tier plus
op batching (coalesce 50 ms of keystrokes into one message).

**Probes you must survive:**
- Two users type at the same position at the same time — walk through the exact resulting text.
  (Server order decides; the second insert is transformed to shift by the first's length; both
  clients converge to the same string. Be able to do it with concrete indices.)
- Why can't you just send the whole document on every keystroke? (Bandwidth × 300k ops/s, and
  last-write-wins silently discards a collaborator's edit — the classic wrong answer.)
- Why can't you use a plain CRUD `PUT /doc` with optimistic locking? (Version conflicts on every
  keystroke; the user experience is a merge dialog per character.)
- How does offline-for-a-day merge work in your OT design? (Honestly: badly. Either bound offline
  editing, or accept a CRDT for that path — the interviewer wants you to *own* the limitation of
  the choice you made.)
- Cursor positions after a remote insert? (Cursors are transformed by the same functions as ops;
  otherwise everyone's caret drifts. A detail that shows you've thought past the happy path.)

Cross-refs: 10 (WebSockets, connection management), 22 §12, 14 (log as the source of truth,
snapshot + replay).

---

## 14. More prompts, with only the fork named

Drill these the same way. The table gives you slot 7 and nothing else, on purpose — the value is in
deriving slots 1–6 and 8–9 yourself.

| Prompt | The fork, and the trap |
|---|---|
| **File sync (Dropbox)** | Chunk the file (4 MB, content-defined boundaries) and sync deltas, or sync whole files? Chunking + content-hash dedupe is the answer; the trap is ignoring conflict resolution on two offline edits (you keep both as "conflicted copy" — a product decision, not a technical one). |
| **Web crawler** | Politeness and frontier scheduling, not fetching. Per-domain rate limits, a URL frontier with priority queues, dedupe by URL *and* content hash (near-duplicate detection via simhash), and `robots.txt` caching. The trap is unbounded fan-out and re-crawling the same content forever. |
| **Object store (S3-like)** | Metadata plane vs data plane split. Erasure coding (e.g. 10+4) vs 3× replication: 1.4× storage overhead vs 3×, at the cost of CPU and repair-read amplification. Trap: treating "durability" and "availability" as one number. |
| **Distributed cache (Redis-as-a-service)** | Client-side consistent hashing vs a proxy tier. Trap: no answer for resharding without a mass-miss event. |
| **Leaderboard / ranking** | Exact global ranks vs approximate percentile buckets. Redis sorted sets give `ZREVRANK` cheaply per shard, but a *global* rank across shards is the hard part; the answer is usually bucketed approximation plus exact top-N. |
| **Multi-tenant API gateway** | Where isolation lives: per-tenant quotas (§4), noisy-neighbour containment (bulkheads), and per-tenant config hot-reload. Trap: one shared thread pool for all tenants. |
| **Payment reconciliation** | Not "how do you take a payment" (22 §26) but how you detect divergence: immutable ledger + provider settlement file + a daily three-way diff job with an exceptions queue. Trap: fixing mismatches by mutating balances instead of appending correcting entries. |
| **Feature-flag service** | Read-path availability: flags are evaluated thousands of times per request, so the design is local SDK evaluation with a streamed ruleset, not an RPC per check. Trap: making a flag lookup a synchronous network dependency of every request. |
| **Comment / social graph read path** | Fan-out again, but with depth: threaded comments need a materialised path (`ltree`/path-enumeration) or a nested-set model to avoid N recursive queries. Trap: adjacency-list recursion at read time. |
| **Idempotent webhook delivery (outbound)** | At-least-once with consumer-side dedupe: signed payloads, a per-endpoint retry schedule with exponential backoff over hours, a circuit breaker per subscriber, and a DLQ with manual replay. Trap: one slow subscriber blocking the shared worker pool. |

---

## 15. L5 vs L6 on the same drill

Same prompt, different bar. The mechanism content is identical; what changes is the frame.

| Dimension | L5 (Senior IC) answer | L6 (Staff / TL) addition |
|---|---|---|
| Scope | Solves the stated problem completely and correctly | Negotiates scope: "v1 drops the marketing path; here's the cut line and why" |
| Numbers | Derives capacity from the load | Also derives **cost** ($/month for the egress in §7, the storage in §10) and names the cheaper design |
| Migration | Greenfield design | "You already have a monolith doing this — here's the dual-write → backfill → shadow-read → flip sequence" (22 §22) |
| Failure | Per-box failure table | Blast radius, dependency SLO math, and what you'd deliberately degrade first |
| Org | — | Who owns this service, what the on-call surface is, how many teams it couples, what the interface contract is |
| Decision record | Picks and defends | States the review criteria and the conditions under which you'd revisit ("if writes exceed 5k/s or a second region appears") |

**Trap for experienced candidates:** answering an L5 prompt at L6 altitude — talking about
organisational ownership while the seat-booking design still double-books. Correctness first, then
altitude.

---

## 16. Self-scoring rubric for a drill

Score each 0/1/2 immediately after the timer, before reading the section. Below 14/20 means re-drill
the same system in a week, not move to the next one.

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Scope cut | Named 3–5 in-scope verbs *and* explicitly deferred the rest |
| 2 | The six numbers | All six, with units, inside 4 minutes |
| 3 | Derived QPS/storage | Arithmetic shown, peak factor applied, no asserted round numbers |
| 4 | Binding resource named | "The bottleneck is X" said out loud before drawing boxes |
| 5 | Keys before boxes | Partition key + sort key stated, with the query each serves |
| 6 | Slot 7 identified | Named the fork this system is about, unprompted |
| 7 | Both sides priced | Every choice stated what it costs, in a number or a named failure |
| 8 | Sync/async split | Clear about what leaves the request path and why |
| 9 | Failure table | Dies / slow / full for every box, plus one graceful-degradation decision |
| 10 | Time management | Reached ops/failure discussion with time left, no rabbit hole |

---

## Atomic concept checklist

- [ ] Guide 22 is the method; this guide is repetition on ten systems with ten different forks.
- [ ] Recognising *which* problem a prompt hides (atomicity, write amplification, contention, convergence) inside three minutes is most of the score.
- [ ] Estimation constants: 10⁵ s/day, 2–3× peak, ~10k writes/s per Postgres primary, ~100k ops/s per Redis node, 1–2 TB/node, 0.5 ms same-AZ / 100 ms cross-region.
- [ ] Slot 7 — naming the one decision the design turns on — is the highest-value sentence in the round.
- [ ] **Rate limiter:** tiny state (100 B/key), huge op rate — the inversion is the insight; token bucket with lazy refill; one atomic Lua script, because GET-then-SET is check-then-act.
- [ ] Fixed-window limiting admits 2× the limit at the boundary; sliding-window log is exact but O(limit) memory per key.
- [ ] Two-tier limiting (local slice + periodic global refill) removes the request-path RTT and costs `nodes × slice` of over-admission — quote it as a number.
- [ ] A hot rate-limit key is fixed by splitting the key into N sub-buckets of `limit/N`, not by adding shards.
- [ ] Fail-open vs fail-closed on limiter outage is a stated product decision, and the limiter returns data (200) while the gateway emits the 429.
- [ ] **Notifications:** one topic with a priority field causes head-of-line blocking; separate topics per priority class with separate consumer pools is the design.
- [ ] A campaign is one job that fan-outs in batches (1k users/message), never an API loop of 10 M sends; ingest returns 202.
- [ ] The real ceiling is third-party provider quota — per-provider token buckets and circuit breakers, and scaling workers past the quota just grows a queue.
- [ ] Retry policy differs per class: OTP gives up in 60 s, receipts retry for 24 h, marketing barely retries.
- [ ] Dead device tokens and email hard bounces must be consumed into a suppression list, or delivery metrics lie and sender reputation degrades.
- [ ] Dedupe with `SET key NX EX` claimed *before* send; quiet hours are evaluated at delivery time, not enqueue time.
- [ ] **Typeahead:** a keystroke is a request; precompute top-k *at every trie node* so the query path never sorts.
- [ ] 100 M queries ≈ 10⁸ trie nodes ≈ 30 GB naive → shard by first 1–2 chars, or compress with an FST; requests touch exactly one shard.
- [ ] Short prefixes are most of the traffic and change hourly — edge-cache them and quote the origin reduction.
- [ ] Ranking = `log(frequency) × recency decay`; personalisation re-ranks a bounded top-50, and trending is a small streaming overlay merged at query time.
- [ ] Typo tolerance is precomputed (deletion-neighbourhood/SymSpell), never edit distance over the corpus at request time.
- [ ] A failed index build serves the previous immutable snapshot; staleness is invisible, downtime is not.
- [ ] **Video:** the binding numbers are egress PB/day and transcode CPU, so cost is architecture; ~90% of videos get ~1% of views.
- [ ] Presigned multipart direct-to-object-store upload keeps 25 TB/day out of your service and makes uploads resumable.
- [ ] GOP-aligned chunking makes transcoding embarrassingly parallel; each chunk job is idempotent on `(video_id, chunk, rendition)`.
- [ ] Hybrid ladder: minimal renditions eagerly for playability, full ladder lazily above a view threshold; keep the source master forever for future codecs.
- [ ] Segments and manifests are immutable and fingerprinted, so the CDN needs no purge logic; ABR is the client's failure handling as well as its quality selector.
- [ ] Views are defined (≥30 s), deduped per user/day, and counted through a stream — never `UPDATE views = views + 1`.
- [ ] **Geo:** 500k drivers ÷ 4 s = 125k writes/s of data worthless in seconds — ephemeral Redis with a 30 s TTL, plus a Kafka copy for durable telemetry.
- [ ] TTL expiry *is* liveness detection; a Redis shard loss self-heals in one update interval.
- [ ] Geohash/S2 turns a 2-D range query into a 1-D prefix scan; precision 5 ≈ 4.9 km, 6 ≈ 1.2 km, 7 ≈ 150 m.
- [ ] Query the 3×3 neighbouring cells then filter by haversine — querying only the home cell silently misses drivers across a border.
- [ ] Dense cells are handled by finer precision, result caps/sampling, or suffix-sharding the cell key.
- [ ] The best lever on 125k writes/s is client-side: adaptive frequency, displacement thresholds, batching, and not publishing while on-trip.
- [ ] Dispatch needs a CAS state machine (`AVAILABLE → OFFERED → ASSIGNED`) with an offer TTL; ranking is road-network ETA, not straight-line distance.
- [ ] **Ad aggregation:** 10 B events/day ≈ 100k/s ≈ 10 TB/day; dashboards from a streaming speed layer, invoices from a batch recompute over an immutable raw log, plus a reconciliation job.
- [ ] Exactly-once effect = edge-minted `click_id` + bounded keyed dedupe + idempotent upsert on `(window, ad_id, …)`; at-least-once into an INSERT-only counter silently over-bills.
- [ ] Event-time windows with watermarks, `allowedLateness`, and a side output for stragglers; the batch layer is what makes restatement possible.
- [ ] A viral ad is a hot key — two-phase aggregation with a salt, then merge.
- [ ] Unique-user counts use HyperLogLog (~12 KB, ~2% error, mergeable); approximate uniques yes, approximate billing no.
- [ ] Adding partitions to a keyed Kafka topic breaks key locality — over-provision partitions on day one.
- [ ] **Metrics store:** delta-of-delta timestamps + XOR-encoded values take 16 B/point to ~1.4 B/point; that 10× is the design.
- [ ] The binding resource is **active series count** (memory + index), not datapoints per second.
- [ ] Labels are indexed as posting lists intersected per query; an unanchored regex over a high-cardinality label is the cluster-killing query.
- [ ] Cardinality explosion (`user_id`/`request_id` as a label) is the canonical outage: per-tenant series limits, relay-side label denylists, growth-rate alerts. Identity belongs on traces/logs.
- [ ] Head block + WAL for the recent window, immutable compressed blocks after, roll-ups (5 m, 1 h) for long ranges; keep `sum` and `count`, never average averages.
- [ ] Replication factor 2–3 with merge-and-dedupe on read is cheaper than consensus and patches missed scrapes.
- [ ] Percentiles require histogram buckets recorded at ingest; they cannot be recovered from stored averages.
- [ ] **Scheduler:** separate scheduling from execution; firing means enqueueing, never running the job.
- [ ] `SELECT ... WHERE next_run_at <= now() FOR UPDATE SKIP LOCKED` is the simple correct design and it scales to a few thousand claims/s.
- [ ] At scale: partitioned durable timer (Redis ZSET + atomic Lua pop) + in-memory hierarchical timing wheel for the next 60 s + leases with fencing tokens.
- [ ] The idempotency unit is the *occurrence*: `(job_id, scheduled_epoch)`, not `job_id`.
- [ ] Misfire policy (`FIRE_ALL` / `FIRE_ONCE` / `SKIP`) is per-job configuration, not a global default.
- [ ] Deterministic `hash(job_id)` jitter defuses the `0 * * * *` thundering herd; fire lag (`now - scheduled_at`) is the system's key SLI.
- [ ] Cron + IANA zone with an explicit DST policy — `0 2 * * *` otherwise skips a day and doubles another.
- [ ] The lease store failing should fail *closed*: late firing beats double firing.
- [ ] **Booking:** contention on a tiny hot dataset, not throughput; zero double-booking demands linearizability per seat.
- [ ] The whole protocol is one conditional `UPDATE ... WHERE state='AVAILABLE' OR hold_expires_at < now()` and checking `rows_affected`.
- [ ] Treating expired holds as available *in the predicate* means correctness never depends on the sweeper job.
- [ ] A virtual waiting room admits users at the rate the booking path can serve, converting a 500k stampede into a sized throughput problem.
- [ ] Strong consistency at the commit point, eventual consistency in the seat-map display.
- [ ] Never hold a row lock across a payment call: hold → authorise → confirm, with saga compensation and idempotency keys.
- [ ] Hot-seat contention is fixed by best-available allocation, per-node inventory blocks, or a lottery — not by replicas.
- [ ] Sharding by `event_id` means one hot event is one hot shard; volunteer that consequence.
- [ ] **Collaborative editing:** OT (server-ordered transforms, small state, sticky doc ownership) vs CRDT (commuting ops, tombstone growth, offline/P2P native).
- [ ] Server-mediated online editor → OT; offline-first or decentralised → CRDT, and own the limitation of whichever you pick.
- [ ] Single-owner-per-document gives a free sequencer; failover = snapshot + op-log tail replay, with clients resending unacked ops keyed `(client_id, client_seq)`.
- [ ] Client applies locally first, buffers pending ops, and rebases them against the server's transformed stream — zero-latency typing with convergence.
- [ ] The op log is the history; snapshot every N ops; undo is per-user and must itself be transformed.
- [ ] Presence/cursors are ephemeral (Redis pub/sub, TTL) and their loss must not affect editing; cursors are transformed like ops or carets drift.
- [ ] Never acknowledge an edit you cannot durably store — if the op log is down, the doc goes read-only.
- [ ] 50k clients reconnecting simultaneously is a self-inflicted DDoS: backoff with jitter, always.
- [ ] L6 adds scope negotiation, cost arithmetic, migration path, blast radius and ownership — but only on top of a correct L5 design.
- [ ] Score every drill on the 10-criterion rubric; below 14/20 re-drill the same system rather than moving on.

