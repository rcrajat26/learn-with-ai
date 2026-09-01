# 12 — API Design

API design questions test judgement, not recall. The interviewer wants to hear you reason about what
a client can safely retry, what a status code tells a caller to *do*, and how the contract survives
change. This guide gives the mechanisms and the defensible defaults.

---

## 1. REST, actually

REST is a set of constraints: client–server, stateless, cacheable, uniform interface, layered
system. Practically, an HTTP API is judged on:

- **Resources are nouns, plural, hierarchical:** `/orders`, `/orders/42`, `/orders/42/items`.
- **The verb lives in the HTTP method**, not the path. `POST /getOrder` and `/deleteUser?id=3` are
  RPC over HTTP, not REST — and they break every intermediary's assumptions about caching and retries.
- **Stateless:** every request carries its own auth and context. No server-side session affinity, so
  any instance can serve any request — that's what makes horizontal scaling trivial.

---

## 2. Methods: safe and idempotent

| Method | Safe (no state change) | Idempotent (N calls = 1 call) | Body | Cacheable |
|---|---|---|---|---|
| GET | yes | yes | no | yes |
| HEAD | yes | yes | no | yes |
| OPTIONS | yes | yes | no | no |
| PUT | no | **yes** | yes | no |
| DELETE | no | **yes** | no | no |
| PATCH | no | **no** (not required to be) | yes | no |
| POST | no | **no** | yes | rarely |

**Why this matters practically:** idempotency is what makes a **retry safe**. A load balancer,
an HTTP client with a retry policy, or a mobile app on a flaky network will re-send. If your `POST
/payments` isn't protected, a timeout that actually succeeded produces a double charge. This is the
single most valuable thing to say in an API design interview.

- **PUT** replaces the whole resource at a known URI. Sending the same representation twice leaves
  the same state → idempotent. PUT can create if the client chooses the id.
- **PATCH** applies a partial modification. `{"balance_delta": -10}` is not idempotent;
  `{"status": "SHIPPED"}` happens to be. The method makes no guarantee, so treat it as unsafe to retry
  unless you add an idempotency key.
- **POST** creates a subordinate resource; the server assigns the URI. Returns `201 Created` with a
  `Location` header.
- **DELETE** is idempotent in effect: deleting twice leaves the resource absent. Returning 404 on the
  second call is acceptable and common; 204 both times is friendlier to retrying clients.

**Trap:** "POST is not idempotent" is a statement about the *protocol's guarantee*, not a licence to
build non-idempotent endpoints. You make POST safe to retry with an idempotency key (§ 5).

---

## 3. Status codes

Choose the code by **what the client should do next**.

**2xx**
- `200 OK` — success with a body.
- `201 Created` — new resource; include `Location`.
- `202 Accepted` — accepted for **asynchronous** processing; the work is not done. Return a status
  URL so the client can poll: `202` + `Location: /jobs/abc` + `{"status":"PENDING"}`. This is the
  right answer for "the operation takes 30 seconds".
- `204 No Content` — success, deliberately no body (DELETE, PUT with no echo).

**4xx — the client must change something**
- `400 Bad Request` — malformed syntax or failed validation.
- `401 Unauthorized` — **you are not authenticated** (misnamed; it means unauthenticated). The client
  should log in / refresh the token. Must include `WWW-Authenticate`.
- `403 Forbidden` — **authenticated but not permitted**. Re-authenticating won't help.
- `404 Not Found` — no such resource. Also the correct answer for "exists but you may not know it
  exists" when 403 would leak information.
- `405 Method Not Allowed` — wrong verb for an existing path; include `Allow`.
- `409 Conflict` — the request conflicts with current state: duplicate unique key, optimistic-lock
  version mismatch, "can't cancel a shipped order". The client may resolve and retry.
- `410 Gone` — deleted permanently; useful for deprecated resources.
- `412 Precondition Failed` — `If-Match` ETag mismatch (conditional-update concurrency control).
- `415 Unsupported Media Type`, `422 Unprocessable Entity` (syntactically valid, semantically wrong —
  useful if you want it distinct from 400).
- `429 Too Many Requests` — rate limited; **include `Retry-After`**.

**5xx — the server failed; the client did nothing wrong**
- `500` internal error, `502` bad gateway, `503` service unavailable (with `Retry-After`),
  `504` gateway timeout.

**Trap:** returning `200 OK` with `{"error": "..."}` in the body. It breaks every generic client,
monitor, retry policy, and circuit breaker, all of which read the status line. Never do it.

**Trap:** 401 vs 403 confusion. Memorize: 401 = who are you, 403 = I know who you are and no.

---

## 4. Modelling non-CRUD actions

Not everything is a create/read/update/delete on a row. Options, in order of preference:

1. **Make the action a resource.** "Cancel an order" → `POST /orders/42/cancellations`, or the state
   change as a sub-resource: `PUT /orders/42/status {"status":"CANCELLED"}`.
2. **Model the intent as a first-class entity** when it has its own lifecycle: a refund is a
   `POST /refunds` resource, not a verb on an order — it has its own id, status, and audit trail.
3. **A controller-style action** when nothing else fits: `POST /orders/42/actions/retry-payment`.
   Pragmatic, and better than contorting the model. Be consistent.

Bulk operations: `POST /orders/bulk` returning `207 Multi-Status` or a per-item result array.
Search with too many parameters for a URL: `POST /orders/search` is an accepted pragmatic break from
purity (it costs you HTTP caching).

---

## 5. Idempotency keys, end to end

The design an interviewer wants to hear:

**Contract.** The client generates a UUID per logical operation and sends
`Idempotency-Key: <uuid>` on POST. Retries of that same operation reuse the same key; a genuinely new
operation gets a new key. The key is scoped per endpoint and per authenticated caller.

**Storage.**

```sql
CREATE TABLE idempotency_keys (
  key            TEXT PRIMARY KEY,
  user_id        BIGINT NOT NULL,
  endpoint       TEXT NOT NULL,
  request_hash   TEXT NOT NULL,      -- detect key reuse with a different body
  status         TEXT NOT NULL,      -- IN_PROGRESS | COMPLETED
  response_code  INT,
  response_body  JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Flow.**
1. `INSERT` the key with status `IN_PROGRESS`. The **primary key constraint** is what makes this
   race-free — do not `SELECT` first.
2. Insert succeeded → this is the first attempt. Do the work **in the same transaction** as the
   status update to `COMPLETED` with the stored response. That atomicity is the whole point: you can
   never have done the work without recording it.
3. Insert failed with a duplicate key → look up the row:
   - `COMPLETED` → **replay** the stored response verbatim (same status, same body).
   - `IN_PROGRESS` → a concurrent duplicate is running. Return `409 Conflict` (or `425 Too Early`)
     and let the client retry; do not run the work twice.
4. Different `request_hash` for the same key → `422` — the client is misusing the key.
5. Expire keys after 24h–7 days via a TTL job.

**Where the true idempotency lives:** if the downstream side effect is itself protected by a unique
constraint (an `order_number`, a payment provider's own idempotency key), you get defence in depth.
Pass your key through to the provider. Related: idempotent consumers in `14-messaging-queues.md`.

---

## 6. Pagination

**Offset:** `GET /orders?page=3&size=20`. Simple, supports jumping to a page and total counts. Costs
grow with depth and results shift when rows are inserted (`09-sql-databases.md` § 11).

**Cursor / keyset:** `GET /orders?limit=20&cursor=eyJ0IjoiMjAyNi0wOC0wMSIsImlkIjo0Mn0`. Constant time,
stable under concurrent writes. The cursor should be **opaque** (base64 of the sort key tuple) so you
can change the underlying scheme without breaking clients. No page numbers, no total.

Default to cursor for feeds, event streams, and anything large or real-time; offset for small admin
tables where users expect page numbers.

**Envelope shape** — be consistent across every collection endpoint:

```json
{
  "data": [ ... ],
  "page": { "next_cursor": "eyJ...", "has_more": true, "limit": 20 }
}
```

Always: enforce a **max limit** server-side (a client asking for `limit=100000` is a DoS), always
apply a deterministic total ordering including a tiebreaker, and document whether a total count is
exact or estimated.

---

## 7. Versioning and deprecation

| Strategy | Example | Notes |
|---|---|---|
| URI path | `/v1/orders` | most visible, easiest to route and cache; the common default |
| Header | `Accept: application/vnd.acme.v2+json` | purist, cache-key aware, harder to test by hand |
| Query param | `/orders?version=2` | easy, messy |

**The better move is to avoid versioning.** Additive changes are backward compatible: new optional
fields, new endpoints, new enum values (as long as clients are told to tolerate unknown values).
Breaking changes are removing/renaming a field, tightening validation, changing a type, or changing
default behaviour. Version only when you must break.

Deprecation process: announce with a date → send `Deprecation: true` and `Sunset: <date>` headers →
measure who is still calling (per-client metrics on the old version) → contact them → remove.
Never remove based on a calendar alone without traffic data.

---

## 8. Error contracts

Use **RFC 7807 `application/problem+json`** (Spring 6's `ProblemDetail` produces exactly this):

```json
{
  "type": "https://api.acme.com/problems/insufficient-funds",
  "title": "Insufficient funds",
  "status": 422,
  "detail": "Account 42 has balance 10.00, required 50.00",
  "instance": "/accounts/42/withdrawals",
  "traceId": "00-4bf92f...-01",
  "errors": [ {"field": "amount", "message": "must not exceed balance"} ]
}
```

Rules:
- **A stable machine-readable code** (`type`, or a `code` field). Clients must never parse `detail`.
- `detail` is human-readable and may change; `title` is stable per `type`.
- **Include a trace/correlation id** in every error response and log it server-side with the same
  value. This is the single highest-value operational detail — a user pastes the id and you find the
  request (`20-observability-operations.md`).
- Validation errors return **all** failures at once, not the first.
- **Never leak** stack traces, SQL, internal hostnames, or library versions to clients
  (`13-web-security.md`).

---

## 9. Rate limiting

**Token bucket** is the usual algorithm: a bucket of capacity `B` refills at `r` tokens/second; each
request consumes one; empty bucket → 429. It allows bursts up to `B` while bounding the sustained
rate. Alternatives: leaky bucket (smooths, no burst), fixed window (simple, but allows 2× at the
boundary), sliding window log/counter (accurate, more memory).

**Headers** (the emerging standard):

```
RateLimit-Limit: 100
RateLimit-Remaining: 12
RateLimit-Reset: 30
Retry-After: 30         # on the 429 itself
```

**The distributed complication.** With N instances, a per-instance counter means the real limit is
`N × limit`, and it changes when you autoscale. Options:
- **Shared store**: Redis with an atomic `INCR`+`EXPIRE` or a Lua token-bucket script. Correct;
  adds a network hop and a dependency on Redis's availability (decide fail-open vs fail-closed —
  fail-open for convenience features, fail-closed for abuse protection).
- **At the edge**: API gateway / CDN handles it before your service. Usually the right place.
- **Local approximation**: each instance limits to `limit/N` — cheap, wrong during scaling events.

Choose the **key** deliberately: API key or user id for fairness, IP for anonymous endpoints (NAT
means many users share one), and both for login endpoints. See credential stuffing in `13-web-security.md`.

---

## 10. Content negotiation, and where data goes

`Accept` (what the client wants) and `Content-Type` (what this body is) drive negotiation; the server
returns `406` if it can't satisfy `Accept` and `415` if it can't parse the body. `Accept-Encoding`
handles compression, `Accept-Language` localization.

**Path vs query vs body:**
- **Path** — identity and hierarchy: `/orders/42/items/7`. It's part of the resource's name.
- **Query** — filtering, sorting, pagination, projection: `?status=OPEN&sort=-createdAt&limit=20`.
  Optional and non-identifying.
- **Body** — the representation being created/updated, and large or sensitive payloads. **Never put
  secrets or tokens in a query string** — they end up in access logs, browser history, and Referer
  headers.
- **Headers** — cross-cutting metadata: auth, content type, tracing, idempotency key.

**Caching** (worth one sentence in an interview): `Cache-Control: max-age/no-store/private`, `ETag`
plus `If-None-Match` for conditional GETs returning `304`, and `If-Match` for optimistic concurrency
on writes (`412` on mismatch).

**HATEOAS** — responses embed links to available next actions (`_links: {cancel: {...}}`), so clients
discover transitions rather than hardcoding URLs. It's the highest REST maturity level (Richardson
level 3) and is rarely used in practice: it adds payload and most clients hardcode anyway. Know the
term, know why teams skip it.

---

## 11. Pushing data: webhooks, polling, SSE, WebSocket

| Mechanism | Direction | Use when | Watch out for |
|---|---|---|---|
| **Polling** | client pulls | simple, low-frequency updates, no infra | latency vs load trade-off; add `ETag`/conditional GETs |
| **Long polling** | client pulls, server holds | near-real-time without new protocols | holds a connection/thread per client |
| **SSE** | server → client, one way | live feeds, notifications, streaming tokens | HTTP/1.1 6-connection-per-origin limit; auto-reconnect is built in |
| **WebSocket** | bidirectional | chat, collaborative editing, trading | stateful — breaks the stateless-scaling story; needs sticky routing or a pub/sub backplane |
| **Webhooks** | your server → their server | server-to-server events across organizations | it's a distributed system you now operate |

**Webhook design** is a common follow-up. You must provide: retries with exponential backoff and
jitter, at-least-once delivery (so **the consumer must be idempotent** — send an event id), a
signature header (HMAC-SHA256 over the raw body with a shared secret, plus a timestamp to stop
replays), a delivery log the customer can inspect and replay, and a circuit breaker that disables
an endpoint failing persistently. Ordering is not guaranteed — include a sequence number or version
so consumers can drop stale events.

Decision rule: **server-to-server across trust boundaries → webhooks. Browser needs live updates,
one direction → SSE. Genuinely bidirectional and low latency → WebSocket. Everything else → poll.**

---

## Atomic concept checklist

- [ ] I model resources as plural nouns and put the verb in the HTTP method.
- [ ] I can define safe and idempotent separately and classify GET/PUT/DELETE/PATCH/POST correctly.
- [ ] I can explain that idempotency is what makes a retry safe, and name the double-charge failure it prevents.
- [ ] I know PATCH is not required to be idempotent even when a given payload happens to be.
- [ ] I return `201` with a `Location` header on create, and `202` with a status URL for async work.
- [ ] I know 401 means unauthenticated and 403 means authenticated-but-forbidden.
- [ ] I use 409 for state conflicts and version mismatches, and 429 with `Retry-After` for rate limits.
- [ ] I never return 200 with an error body.
- [ ] I can model non-CRUD actions as sub-resources, first-class entities, or explicit action endpoints.
- [ ] I can design idempotency keys end to end: client-generated UUID, insert-first on a primary key, work and response recorded in one transaction, replay on COMPLETED, 409 on IN_PROGRESS, request-hash mismatch rejected.
- [ ] I know cursor pagination is opaque, constant time, and stable, while offset supports page jumps and totals.
- [ ] I always enforce a server-side max page size and a deterministic total ordering with a tiebreaker.
- [ ] I can compare URI, header, and query versioning, and I know additive changes avoid versioning entirely.
- [ ] I know the deprecation sequence: announce, `Deprecation`/`Sunset` headers, measure traffic, contact, remove.
- [ ] I return RFC 7807 `application/problem+json` with a stable machine-readable type and a trace id.
- [ ] I never leak stack traces or SQL in an error response, and I return all validation errors at once.
- [ ] I can describe token bucket and say why distributed rate limiting needs a shared store or the edge.
- [ ] I choose rate-limit keys deliberately: user/API key for fairness, IP for anonymous, both for login.
- [ ] I put identity in the path, filters in the query, payloads in the body, and never secrets in a query string.
- [ ] I know `ETag`/`If-None-Match` gives 304 and `If-Match` gives 412 for optimistic concurrency.
- [ ] I can say what HATEOAS is and why most teams skip it.
- [ ] I can pick between polling, SSE, WebSocket, and webhooks from the direction and trust boundary.
- [ ] I know webhook delivery needs retries with backoff, HMAC signatures with a timestamp, event ids for idempotency, and a replayable delivery log.