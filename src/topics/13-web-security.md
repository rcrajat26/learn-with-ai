# 13 — Web Security

Security answers are graded on mechanism. "Use bcrypt" earns nothing; "bcrypt is deliberately slow
with a tunable cost factor and a per-password salt, so an attacker with the dump can't run a fast
GPU dictionary attack, and identical passwords don't produce identical hashes" earns the point. Every
section here is written to be stated that way.

---

## 1. Authentication vs authorization

- **Authentication (AuthN)** — *who are you?* Verifying identity: password, token, certificate.
  Failure → **401**.
- **Authorization (AuthZ)** — *what may you do?* Checking permission on a resource. Failure → **403**.

They are separate layers and separate failures. The most common real-world vulnerability is broken
authorization, specifically **IDOR / broken object-level authorization**: `GET /invoices/1234`
returns someone else's invoice because the code checked "is logged in" but never "does this invoice
belong to this user". Every query that fetches a user-owned resource must filter by owner —
`findByIdAndUserId(...)`, not `findById(...)` followed by a forgotten check.

Models: **RBAC** (roles → permissions; simple, coarse), **ABAC** (policy over attributes: department,
time, resource owner), **ReBAC** (relationship graph, e.g. Google Zanzibar). Start with RBAC plus an
explicit ownership check.

---

## 2. Sessions vs tokens

**Server-side sessions.** A random opaque session id in a cookie; state lives server-side (Redis).
- Revocation is instant — delete the row.
- Every request needs a session-store lookup.
- Scaling needs a shared store (sticky sessions are a fragile alternative).
- Cookies are automatically sent by browsers → **CSRF applies** (§ 8).

**Self-contained tokens (JWT).** Claims plus a signature; the server verifies with a key and holds
no state.
- Scales trivially, works across services and domains.
- **Cannot be revoked** before expiry without reintroducing state. That's the whole trade-off.

**The standard resolution:** short-lived access token (5–15 min) plus a long-lived, *stateful*,
rotating refresh token. Revocation happens at refresh time, so the worst-case exposure is one access
token lifetime. Add a denylist of `jti` values for emergency revocation if you need faster.

Cookie flags when you do use cookies (and for browser apps, an `HttpOnly` cookie is a better token
store than `localStorage`, which any XSS can read):
`HttpOnly` (no JS access), `Secure` (HTTPS only), `SameSite=Lax|Strict` (CSRF defence), `Path`,
short `Max-Age`.

---

## 3. JWT

Three base64url segments: `header.payload.signature`.

```
{"alg":"RS256","typ":"JWT","kid":"key-1"}     header
{"sub":"42","iss":"https://auth.acme.com","aud":"orders-api",
 "exp":1767225600,"iat":1767224700,"jti":"...","scope":"orders:read"}   payload
HMAC/RSA over base64(header) + "." + base64(payload)                     signature
```

**The payload is base64, not encryption — anyone can read it.** Never put PII, secrets, or anything
you wouldn't publish in a JWT. (JWE encrypts, and is rare.) The signature guarantees integrity and
origin, not confidentiality.

**Validation checklist — every item is a real CVE class:**
1. Signature verifies against the expected key (fetched by `kid` from the issuer's JWKS, cached).
2. **`alg` matches what you expect** — do not let the token choose. See below.
3. `exp` not passed, `nbf` not future (small clock skew allowance).
4. `iss` is your issuer.
5. `aud` includes **your** service. Without this, a valid token minted for another service is accepted.
6. Scopes/roles actually authorize the specific action.

**Attack — `alg: none`.** Early libraries honoured `{"alg":"none"}` and skipped verification. Attacker
edits `sub` to an admin id, strips the signature, done.

**Attack — algorithm confusion (RS256 → HS256).** The server's *public* key is, well, public. An
attacker changes `alg` to HS256 and signs with the public key as the HMAC secret. A naive
`verify(token, publicKey)` that infers the algorithm from the header accepts it. **Fix: pin the
expected algorithm at verification time**, never read it from the token.

Other rules: no `alg`-guessing, reject `none` explicitly, keep tokens short-lived, don't accept
tokens in query strings (they land in logs), and rotate signing keys with `kid`.

---

## 4. OAuth 2.0 and OIDC

**OAuth 2.0 is a delegated *authorization* framework**, not a login protocol. Roles:

| Role | Who |
|---|---|
| Resource owner | the user |
| Client | the app requesting access |
| Authorization server | issues tokens (Okta, Auth0, Cognito, Keycloak) |
| Resource server | your API, which validates the token |

**Authorization Code + PKCE — the default flow for everything user-facing** (web apps, SPAs, mobile):

1. Client redirects the user to the auth server with a `code_challenge` = SHA256(`code_verifier`),
   plus a random `state`.
2. User authenticates and consents.
3. Redirect back with a short-lived `code` and the `state` (**verify `state` matches — that's the CSRF
   defence for the flow**).
4. Client POSTs `code` + the original `code_verifier` to the token endpoint (back channel).
5. Auth server checks SHA256(verifier) == challenge, returns tokens.

**PKCE's purpose:** an attacker who intercepts the authorization code (via a malicious app registering
the same custom URI scheme, or a referer leak) still cannot exchange it, because they don't have the
verifier. Originally for mobile; now recommended for **all** clients including confidential ones.

**Client credentials** — machine-to-machine, no user involved: the service authenticates with its own
id/secret (or a signed assertion / mTLS) and gets a token. This is the right flow for backend-to-backend.

**Deprecated flows and why:**
- **Implicit** — returned the access token directly in the URL fragment: it lands in browser history,
  referers, and logs, and has no refresh mechanism. Replaced by auth code + PKCE.
- **Resource Owner Password Credentials** — the app handles the user's actual password, defeating the
  entire point of delegation and blocking MFA/SSO. Only ever a migration crutch.

**OIDC** is a thin identity layer *on top of* OAuth 2.0. It adds the **ID token** (a JWT about *who
the user is*, with `sub`, `email`, `nonce`), a standard `/userinfo` endpoint, and discovery via
`/.well-known/openid-configuration`.

**The distinction to state:** the access token is for calling APIs and is opaque to the client; the
ID token is for the client to learn who logged in and must **never** be sent to an API as
authorization. "Log in with Google" is OIDC. "Let this app read your Google Drive" is OAuth 2.

---

## 5. Password storage

**Never store passwords recoverably.** Encryption is wrong because it is *reversible* — a key
compromise (and keys live in the same infrastructure) reveals every password in plaintext. There is
no legitimate reason to ever recover a user's password; "email me my password" is a design defect.

**Never plain hashing.** MD5/SHA-256 are designed to be *fast*: billions of guesses per second on a
GPU, and identical passwords produce identical hashes, so one rainbow table cracks the whole dump at
once.

**Correct: a slow, salted, memory-hard KDF.**
- **Salt** — unique random value per password, stored alongside the hash. Defeats rainbow tables and
  makes identical passwords hash differently. bcrypt/argon2 generate and embed it automatically.
- **Slow / work factor** — bcrypt's cost is a power of two (12 is a reasonable 2026 default, ~250ms);
  raise it as hardware improves. The legitimate user pays 250ms once; the attacker pays it per guess.
- **Memory hard** — Argon2id and scrypt also require significant RAM, which blunts GPU/ASIC
  parallelism. **Argon2id is the current first choice**; bcrypt is fine and everywhere; PBKDF2 when
  FIPS compliance demands it. Note bcrypt truncates input at 72 bytes.

```java
PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
// stores "{bcrypt}$2a$12$..." — the prefix lets you migrate algorithms without invalidating logins
```

Also: **pepper** (a secret key applied in addition to the salt, stored outside the DB) adds defence
if only the database leaks. Always compare with a constant-time function. Verify against
breached-password lists rather than enforcing baroque composition rules — NIST 800-63B now
recommends length and breach-checking over forced rotation and special characters.

---

## 6. Transport: HTTPS/TLS and mTLS

TLS gives three things: **confidentiality** (nobody reads it), **integrity** (nobody modifies it),
and **server authentication** (you're talking to the real host, proven by a CA-signed certificate).
It gives you *nothing* about who the client is, and nothing about the safety of the payload.

Practicals: TLS 1.2 minimum, prefer 1.3 (faster handshake, bad ciphers removed); HSTS
(`Strict-Transport-Security`) so browsers refuse plaintext; redirect HTTP→HTTPS; encrypt
**internal** traffic too (network segmentation is not a boundary — assume the network is hostile).

**mTLS** adds client certificate verification, so both sides authenticate. It's the standard for
service-to-service auth inside a mesh (Istio/Linkerd do it transparently) and for high-assurance
B2B APIs. Cost: certificate distribution and rotation.

---

## 7. CORS — a browser rule, not a server defence

**Mechanism.** The browser's same-origin policy stops JavaScript on `evil.com` from *reading*
responses from `api.acme.com`. CORS is how a server opts in to allowing that read: it returns
`Access-Control-Allow-Origin`, and **the browser** decides whether to hand the response to the script.

**Preflight:** for anything beyond a "simple" request (non-simple method like PUT/DELETE/PATCH, or
custom headers like `Authorization`, or a JSON content type), the browser first sends
`OPTIONS` with `Access-Control-Request-Method`/`-Headers`. The server must answer with
`Access-Control-Allow-Methods`, `-Headers`, and optionally `-Max-Age` to cache the preflight.
`Access-Control-Allow-Credentials: true` is required to send cookies — and it is **illegal in
combination with `Allow-Origin: *`**.

**The critical framing:** CORS does not protect your server. `curl`, Postman, and any server-side
client ignore it entirely — the request still reaches your endpoint and still executes. CORS only
governs whether *browser JavaScript* may read the response. Authorization is what protects the API.

**Trap:** reflecting the `Origin` header back with credentials allowed. That's equivalent to
`*`-with-credentials and hands any site full authenticated access. Use an allowlist.

---

## 8. CSRF

**Mechanism.** The browser attaches cookies for `bank.com` to *any* request to `bank.com`, including
one triggered by a form on `evil.com`. The attacker can't read the response, but the state-changing
side effect already happened — that's enough for a transfer.

**CSRF only applies to ambient credentials** — cookies, HTTP Basic, client certs. An API that takes
`Authorization: Bearer <token>` is not vulnerable, because the browser never attaches that header
automatically. This is the reasoning behind `http.csrf(csrf -> csrf.disable())` on a stateless
token API — and you must be able to justify it, not just copy it.

**Defences:**
1. **`SameSite` cookies.** `Lax` (the modern browser default) blocks cookies on cross-site POSTs while
   still allowing top-level GET navigation. `Strict` is stronger but breaks inbound links.
2. **Synchronizer token.** A random per-session token in a hidden form field/header that the attacker
   cannot read (same-origin policy stops them). Spring Security's default for session apps.
3. **Double-submit cookie.** Token in both a cookie and a header; server compares. Stateless variant.
4. Verify `Origin`/`Referer` as a secondary check.

---

## 9. Injection

**SQL injection.** String-concatenating user input into SQL lets input become code:
`'; DROP TABLE users; --`.

**The fix is prepared statements, and the mechanism matters:** the SQL text with `?` placeholders is
sent to the database and **parsed into a query plan first**; parameter values are then bound as
*data* to that already-fixed plan. There is no path by which a value becomes syntax. This is
categorically different from escaping, which is a blocklist you can get wrong.

```java
jdbc.query("SELECT * FROM users WHERE email = ?", rs -> ..., email);   // safe
em.createQuery("... where u.email = :e").setParameter("e", email);      // safe
"... WHERE email = '" + email + "'"                                     // vulnerable
```

**What parameters cannot do:** table names, column names, and `ORDER BY` direction are not
parameterizable — they're part of the syntax. For a dynamic sort column, **validate against an
allowlist** of known column names. Also note JPA/Hibernate protect you only while you use parameters;
a concatenated `@Query(nativeQuery = true)` is just as vulnerable.

Related injections with the same shape: command injection (`ProcessBuilder` with a list of args, not
a shell string), LDAP, XPath, template injection (SpEL/Thymeleaf on user input), and log injection
(strip newlines from user input before logging).

---

## 10. XSS

Attacker-supplied content executes as JavaScript in another user's browser, stealing session
cookies/tokens or acting as them.

- **Stored** — persisted (a comment) and served to everyone.
- **Reflected** — echoed from a URL parameter.
- **DOM-based** — client-side JS writes untrusted data into `innerHTML`/`eval`.

**Primary defence: context-aware output encoding at render time.** The same string is encoded
differently in HTML body, in an attribute, in a URL, and inside a `<script>` block. Modern template
engines (Thymeleaf `th:text`, React's `{}`) escape by default — the vulnerabilities appear where you
bypass them (`th:utext`, `dangerouslySetInnerHTML`, jQuery `.html()`).

Defence in depth: sanitize rich HTML input with an allowlist library (OWASP Java HTML Sanitizer,
DOMPurify) rather than a regex; `HttpOnly` cookies so a successful XSS can't read the session; and
**CSP** (`Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123'`) which stops
inline and third-party script execution even if injection succeeds. `X-Content-Type-Options: nosniff`
and a correct `Content-Type` prevent an uploaded file from being interpreted as HTML.

---

## 11. Secrets hygiene

Never in: source code, git history (a deleted secret is still in the history — **rotate it, don't
just delete the line**), Dockerfiles or image layers (`docker history` shows them), CI logs,
application logs or error messages, URLs/query strings, client-side code, or a config file committed
"temporarily".

Do: a secrets manager (AWS Secrets Manager, Vault, GCP Secret Manager) or injected environment
variables; IAM roles / workload identity so there's no long-lived credential at all; rotation on a
schedule and immediately on suspicion; least-privilege scoping so one leak isn't total; and a
pre-commit/CI scanner (gitleaks, trufflehog) so this is enforced, not remembered.

---

## 12. OWASP Top 10 (2021) orientation

| # | Category | The one-line version for backend Java |
|---|---|---|
| A01 | Broken Access Control | IDOR — always filter by owner, never trust a client-supplied id |
| A02 | Cryptographic Failures | plaintext/weak hashing, no TLS, secrets in code |
| A03 | Injection | SQL/command/template — parameterize, allowlist identifiers |
| A04 | Insecure Design | missing rate limits, no threat model, no idempotency |
| A05 | Security Misconfiguration | default creds, debug endpoints, verbose errors, open actuator |
| A06 | Vulnerable Components | unpatched libs — Dependabot/OWASP dependency-check in CI (Log4Shell) |
| A07 | Identification & AuthN Failures | weak passwords, no MFA, session fixation, credential stuffing |
| A08 | Software & Data Integrity | unsigned artifacts, unsafe deserialization, supply chain |
| A09 | Logging & Monitoring Failures | no audit trail, so a breach goes undetected for months |
| A10 | SSRF | server fetches a user-supplied URL → reaches `169.254.169.254` metadata or internal services |

For **SSRF** specifically: allowlist destination hosts, block link-local/private ranges *after* DNS
resolution (a hostname can resolve to `127.0.0.1`), disable redirects or re-validate each hop, and
use IMDSv2 on EC2.

**Unsafe deserialization:** Java native deserialization of untrusted bytes gives remote code
execution via gadget chains. Never `ObjectInputStream.readObject()` on external input; use JSON with
explicit types and disable Jackson's polymorphic default typing.

---

## 13. Credential stuffing and enumeration

Attackers replay username/password pairs from other breaches. Defences that actually work:

- **Rate limit on the right key.** Per-IP alone is useless against a botnet spreading one attempt per
  IP. Limit **per account** (protects the target), **per IP**, and globally on the login endpoint —
  and alert on a spike in the *failure rate*, which is the real signal.
- **Breached-password checks** at registration and password change (Have I Been Pwned's k-anonymity
  range API sends only a 5-character hash prefix).
- **MFA** — the only defence that actually defeats a correct stolen password.
- **CAPTCHA / proof of work** after a threshold, not on every attempt.

**Enumeration-proof responses.** Login must return the same message ("invalid email or password") and
**the same timing** whether or not the account exists — hash a dummy password when the user is
missing, otherwise the fast failure leaks account existence. The same applies to
registration ("if that address is new, check your email"), password reset ("if an account exists,
we've sent a link"), and any 404-vs-403 decision on a private resource.

Related: **account lockout is a double-edged tool** — it turns credential stuffing into a denial of
service against your users. Prefer progressive delays and MFA over hard lockouts.

---

## Atomic concept checklist

- [ ] I distinguish authentication (401, who are you) from authorization (403, may you).
- [ ] I know broken object-level authorization (IDOR) is the most common real vulnerability, and I filter queries by owner.
- [ ] I can state the sessions-vs-tokens trade-off as revocation-and-state versus statelessness-and-scale.
- [ ] I know the standard resolution is a short-lived access token plus a stateful rotating refresh token.
- [ ] I know a JWT payload is base64 and readable by anyone, so no secrets go in it.
- [ ] I can list the JWT validation checklist: signature, pinned algorithm, exp/nbf, iss, aud, scope.
- [ ] I can explain `alg: none` and RS256→HS256 confusion, and that the fix is pinning the algorithm server-side.
- [ ] I know OAuth2 is delegated authorization and can name all four roles.
- [ ] I can walk authorization code + PKCE and say what PKCE and `state` each defend against.
- [ ] I know client credentials is the machine-to-machine flow, and why implicit and password grants are deprecated.
- [ ] I know OIDC adds the ID token, and that an ID token must never be used to call an API.
- [ ] I can explain why encrypting passwords is wrong: reversibility, and there is no legitimate need to recover one.
- [ ] I can explain salt (per-password uniqueness, defeats rainbow tables) and work factor (attacker pays per guess) separately.
- [ ] I know Argon2id/bcrypt/scrypt are the correct choices and that memory-hardness blunts GPU attacks.
- [ ] I know TLS gives confidentiality, integrity, and server authentication only, and that mTLS adds client identity.
- [ ] I know CORS is enforced by the browser and does not protect the server; curl ignores it entirely.
- [ ] I can describe the preflight OPTIONS request and why `Allow-Origin: *` cannot be combined with credentials.
- [ ] I know CSRF only applies to ambient credentials, so a Bearer-token API is not vulnerable.
- [ ] I can name three CSRF defences: SameSite cookies, synchronizer token, double-submit cookie.
- [ ] I can explain prepared statements mechanically: the plan is parsed before values bind, so data can never become syntax.
- [ ] I know table and column names cannot be parameterized and require an allowlist.
- [ ] I know XSS is fixed by context-aware output encoding, with CSP and HttpOnly cookies as defence in depth.
- [ ] I know a secret committed to git must be rotated, not just deleted.
- [ ] I can list the OWASP Top 10 categories and give a concrete Java example for at least half.
- [ ] I can explain SSRF and that private-range blocking must happen after DNS resolution.
- [ ] I never deserialize untrusted input with `ObjectInputStream`.
- [ ] I rate limit login per account as well as per IP, and I keep responses and timing identical for existing and non-existing accounts.