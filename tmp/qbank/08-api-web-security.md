# 08 — API Design & Web Security

**What this decides:** readiness for the LLD/API-design round (often a
dedicated round at L4/L5), and whether web-security fundamentals need a
dedicated track before the plan's Week 15 auth deep-dive.

---

## Ladder

### Q1 [L1] rapid-fire — HTTP semantics
(a) PUT vs PATCH vs POST — semantic difference. (b) Which methods are
idempotent? Safe? (c) One-liner each: 200, 201, 204, 400, 401, 403, 404,
409, 429, 500, 503.
**Strong answer:** PUT = full replace, idempotent; PATCH = partial, not
guaranteed idempotent; POST = create/process, not idempotent. Safe: GET/HEAD.
Idempotent: GET/PUT/DELETE. Codes: 401 = unauthenticated vs 403 =
unauthorized (the classic pair — must get this right), 409 conflict,
429 rate-limited, 503 temporarily unavailable/overloaded.
**Score:** 1 if ≤2 slips; 0.5 if 401/403 confused or ≥3 slips.

### Q2 [L2] explain-back — Resource modeling
Design endpoint paths for: list a customer's orders, cancel an order, and
"retry a failed payment" (an action that isn't CRUD). Defend your choices.
**Strong answer:** `GET /customers/{id}/orders`, cancel as state change —
`POST /orders/{id}/cancel` or `PATCH` status with rationale (DELETE implies
resource removal); actions-as-subresources for non-CRUD verbs
(`POST /payments/{id}/retries`). Consistency + plural nouns + no verbs in
CRUD paths. Any coherent, defended convention = 1.

### Q3 [L2] explain-back — Pagination: offset vs cursor
Design the request/response shape for paginating an orders list. Which style
and why?
**Strong answer:** cursor/keyset (`?cursor=...&limit=50`, response carries
`next_cursor`): stable under concurrent inserts, O(1)-ish at depth (ties to
06/B6); offset: random page access but drifts and slows at depth. Response
envelope with `items` + cursor + has_more. Choosing cursor with both reasons = 1.

### Q4 [L2] explain-back — AuthN vs AuthZ + session vs token
Distinguish the two. Then: cookie-session auth vs bearer-token auth — how
does each work end-to-end, and one pro/con each.
**Strong answer:** AuthN = who you are, AuthZ = what you may do. Session:
server-side state, cookie carries session id; revocation trivial, CSRF
applies, horizontal scale needs shared store. Token (JWT): stateless,
self-contained claims; scale-friendly; revocation hard, theft = full access
until expiry.

### Q5 [L3] explain-back + trap — JWT mechanics
Structure of a JWT; what does the signature protect against; can you read
the claims without the key? What must a resource server validate, and name
one classic implementation vulnerability.
**Strong answer:** header.payload.signature, base64url — payload is READABLE
by anyone (encoding ≠ encryption); signature protects integrity/authenticity,
not confidentiality. Validate: signature against expected alg + key, `exp`,
`iss`, `aud`. Classic vulns: accepting `alg: none`; HS256/RS256 confusion
(verifying an RSA token with the public key as HMAC secret); no `aud` check
(token for service A replayed at service B). Payload-is-readable + ≥2
validations + 1 vuln = 1.

### Q6 [L3] predict-output — CORS
An SPA on `https://app.example.com` calls `https://api.example.com/orders`
with `fetch`, sending `Authorization` and `Content-Type: application/json`.
What happens at the browser/network level before your handler runs, and
what must the server return? Is CORS protecting the server?
**Strong answer:** browser sends OPTIONS preflight (non-simple request due to
the headers); server must answer `Access-Control-Allow-Origin` (+
`-Headers`, `-Methods`); browser then sends the real request. CORS is a
BROWSER protection for users — curl ignores it entirely; it is not server
access control. That last point is the discriminator.

### Q7 [L3] explain-back — CSRF
What's the attack, when are you vulnerable, when not, and what are defenses?
**Strong answer:** attacker page triggers a state-changing request; browser
auto-attaches cookies → vulnerable when auth rides on cookies. Not
vulnerable with bearer tokens in headers (attacker JS can't set them
cross-origin). Defenses: CSRF tokens, `SameSite=Lax/Strict` cookies, checking
Origin. The cookie-vs-header distinction is the whole answer.

### Q8 [L3] explain-back — Injection & XSS basics
Why do prepared statements stop SQL injection (mechanism, not slogan)? What
is stored XSS and the two main defenses?
**Strong answer:** parameters travel out-of-band of the SQL text — parsed
plan treats them as data, never re-parsed as SQL; concatenation mixes code
and data. XSS: attacker-supplied content served to other users executes as
script; defenses: output encoding per context + CSP; (input validation helps
but is not the primary defense). Mechanism-level answers required.

### Q9 [L4] scenario — Design an idempotent payment endpoint
`POST /payments` must survive client retries (timeout → retry) without
double-charging. Design it concretely.
**Strong answer:** client-generated `Idempotency-Key` header; server stores
key + request hash + response (with TTL) — unique constraint enforces
single execution; replay returns the SAME response (status + body);
concurrent duplicate: second request blocks or gets 409/425 until first
completes; different body with same key = 422. Bonus: scoping keys per
endpoint+client, expiry policy, ties to 09 (exactly-once is a lie, this is
the compensation). Unique-constraint + response-replay + concurrent case = 1.

### Q10 [L4] discriminator — Error contract & versioning judgment
Design your error response body, and state your API-versioning position.
**L2 answer:** `{code, message}` and `/v1/`. **L4 answer:** structured errors
(machine `code`, human `message`, `field_errors[]`, `trace_id` for support —
RFC 7807-shaped), never leak stack traces; versioning: version only on
breaking changes, additive changes don't break well-behaved clients
(tolerant reader), URL vs header trade-off stated with a pick. Score by tier
(L2 = 0.5).

---

## Breadth checklist (rate 0–3)

- [CORE] Password storage: bcrypt/argon2 vs MD5/SHA — and WHY (slow + salted)
- [CORE] Secrets hygiene: no secrets in code/git/logs; where they live instead
- [CORE] HTTPS-only mindset; what HSTS does (heard-of fine)
- [CORE] Content-Type / Accept — content negotiation basics
- [CORE] Request validation at the boundary (Bean Validation ties to 04)
- OAuth2 flows — can you name authorization-code flow's steps? (0–1 fine, calibrates Day 73)
- OIDC vs OAuth2 (0–1 fine)
- API keys vs tokens vs mTLS — heard of the spectrum?
- Rate limiting: token bucket concept, 429 + Retry-After
- ETags / conditional requests (If-None-Match) — caching + optimistic concurrency over HTTP
- Cache-Control directives (no-store vs no-cache vs max-age)
- OpenAPI/Swagger — written or generated one?
- Webhooks: signing/verifying (HMAC) — heard of?
- OWASP Top 10 — how many can you name? (list them, count honestly)
- Same-origin policy — can you state it?
- Security headers (CSP, X-Content-Type-Options) (0–1 fine)
- gRPC/protobuf API design (0–1 fine)
