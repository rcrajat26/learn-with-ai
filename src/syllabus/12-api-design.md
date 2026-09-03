# Syllabus — 12 API Design

**Target version baseline.** Every field name, status code, media type, directive, constant and
default below is stated against this set of specifications and releases, and every leaf that depends
on a version says so:

| Layer | Normative source this file targets |
|---|---|
| HTTP semantics | **RFC 9110** (June 2022) — obsoletes RFC 7231/7232/7233/7235 and the method/status/field registries |
| HTTP caching | **RFC 9111** (June 2022) — obsoletes RFC 7234 |
| HTTP/1.1 message syntax | **RFC 9112**; HTTP/2 **RFC 9113**; HTTP/3 **RFC 9114**; QPACK **RFC 9204** |
| Error payloads | **RFC 9457** (July 2023) — **obsoletes RFC 7807**; adds the IANA problem-type registry and multi-problem guidance |
| Structured field values | **RFC 8941**, superseded by **RFC 9651** (Sept 2024) |
| Web links | **RFC 8288** (`Link` header, relation registry) |
| Deprecation signalling | **RFC 9745** (March 2025, `Deprecation` as a Structured Field **Date**) + **RFC 8594** (`Sunset`, HTTP-date) |
| Rate limiting | **draft-ietf-httpapi-ratelimit-headers-11** (23 May 2026, expires 24 Nov 2026) — `RateLimit` and `RateLimit-Policy` |
| Idempotency | **draft-ietf-httpapi-idempotency-key-header-07** (Oct 2025, expired 18 April 2026) — `Idempotency-Key` |
| Safe method with body | **RFC 10008** (June 2026) — the `QUERY` method and `Accept-Query` |
| Partial update | **RFC 6902** JSON Patch, **RFC 7396** JSON Merge Patch, **RFC 6901** JSON Pointer |
| Preferences | **RFC 7240** (`Prefer` / `Preference-Applied`), **RFC 8297** (`103 Early Hints`) |
| Description format | **OpenAPI 3.1.1** as the workhorse, **OpenAPI 3.2.0** (23 Sept 2025) as the current release; **JSON Schema 2020-12** |
| RPC | gRPC over HTTP/2 (`PROTOCOL-HTTP2.md`), Protocol Buffers (proto3 + Editions), `google.rpc.Code` 0–16 |
| Graph | GraphQL specification **October 2021 edition**; GraphQL-over-HTTP draft; `@defer`/`@stream` still non-normative |
| Hypermedia formats | HAL (`draft-kelly-json-hal`), JSON:API **1.1**, Siren, Collection+JSON, JSON-LD/Hydra |
| Java runtime | **Java 21**, **Spring Boot 3.5.x / Spring Framework 6.2.x** as the baseline; **Spring Framework 7.0 / Boot 4.0** (Nov 2025) marked `[VERSION-TRAP]` because it adds first-class API versioning |
| Design guides | Google AIP (aip.dev), Microsoft REST API Guidelines + Azure/Graph patterns, Zalando RESTful API and Event Guidelines, Stripe API versioning, Standard Webhooks 1.0 |

The seven deltas that most often produce a **stale answer** in an interview, all marked
`[VERSION-TRAP]` inline:

1. **RFC 7807 is obsolete.** The media type is unchanged (`application/problem+json`) but the
   normative reference is **RFC 9457**, and it added the IANA `http-problem-types` registry plus the
   `about:blank` convention for "no semantics beyond the status code". Saying "RFC 7807" is not
   wrong-in-spirit but it is out of date, and every guide that predates July 2023 misses the
   registry.
2. **`Deprecation: true` is invalid.** RFC 9745 defines `Deprecation` as a Structured Field **Date**
   item — `Deprecation: @1688169599`. The boolean form circulated for years in blog posts and in
   the pre-RFC draft. The current guide `src/topics/12-api-design.md` § 7 states the boolean form and
   must be corrected.
3. **The rate-limit headers changed shape.** `RateLimit-Limit` / `RateLimit-Remaining` /
   `RateLimit-Reset` are *early-draft* names that remain widely deployed as a de facto convention;
   draft-11 defines exactly two fields — `RateLimit-Policy` (a List of policy Items with `q`, `qu`,
   `w`, `pk` parameters) and `RateLimit` (a List of service-limit Items with `r`, `t`, `pk`).
4. **`QUERY` is now a real, registered method** (RFC 10008, June 2026): safe, idempotent, **cacheable
   with the body in the cache key**, advertised via `Accept-Query`. "You have to use `POST /search`
   because GET can't have a body" is now only true where `QUERY` is unimplemented.
5. **Spring no longer needs a versioning hack.** Framework 7 / Boot 4 add `version` to
   `@RequestMapping` plus `ApiVersionStrategy` / `ApiVersionResolver` / `ApiVersionParser` /
   `ApiVersionDeprecationHandler`. Every "use a custom `RequestCondition`" answer is 6.2-and-earlier.
6. **OpenAPI 3.2.0 exists** and is not breaking against 3.1: it adds `QUERY`, `additionalOperations`,
   first-class streaming media types (`text/event-stream`, `application/jsonl`,
   `application/json-seq`, `multipart/mixed`), tag hierarchies, `deviceAuthorization` and
   `oauth2MetadataUrl` in the OAuth flows object, and deprecatable security schemes.
7. **GraphQL's status-code story changed** with `application/graphql-response+json`: the
   "GraphQL always returns 200" claim only holds for `application/json`. Under the newer media type a
   non-null `data` entry **MUST** be 2xx and request-validation failure is a 400.

**Scope boundary against the sibling guides.** This file owns **the contract**: what a caller sees,
what it may assume, what it may retry, what it costs to change, and the four wire styles (REST/HTTP,
RPC/gRPC, GraphQL, event push) it can be expressed in. Owned elsewhere:

- TCP, TLS handshakes, keep-alive, connection pooling, HTTP/1.1-vs-2-vs-3 multiplexing internals,
  DNS and load-balancer mechanics live in `10-networking.md`. This guide owns only what those
  properties *change about the contract* (head-of-line blocking → why you stop sharding domains;
  6-connections-per-origin → why SSE fanout breaks on HTTP/1.1). `[X-REF 10]`
- AuthN vs AuthZ, sessions vs JWT, the OAuth 2.x / OIDC grant flows, RFC 9700 (OAuth 2.0 Security
  BCP), password storage, CORS, CSRF, XSS, SQLi, secrets and TLS configuration live in
  `13-web-security.md`. This guide owns the *contract face*: which header carries the credential,
  which status code a failure maps to, `WWW-Authenticate`, scope-to-endpoint mapping, and the
  information-leak status-code choice. `[X-REF 13]`
- Kafka/RabbitMQ mechanics, partitions, offsets, consumer groups, delivery semantics, DLQs, outbox
  and saga live in `14-messaging-queues.md`. This guide owns webhooks as an *externally published
  contract* and the outbox as the thing that makes an API's side effects and its events atomic.
  `[X-REF 14]`
- Cache stores (Redis, Caffeine), eviction policies, stampede prevention and invalidation topology
  live in `15-caching.md`. This guide owns HTTP caching — `Cache-Control`, `ETag`, `Vary`, the
  freshness arithmetic — and the shared-store rate limiter as an API mechanism. `[X-REF 15]`
- Query plans, index choice, keyset-pagination SQL cost, isolation levels and optimistic locking at
  the row level live in `09-sql-databases.md`. This guide owns the cursor *contract* and the
  `If-Match` → `412` mapping on top of a version column. `[X-REF 09]`
- The `EntityManager`, `@Version`, `OptimisticLockException` and DTO projections live in
  `08-spring-data-jpa.md`. `[X-REF 08]`
- `DispatcherServlet` internals, `@ControllerAdvice` resolution order, the proxy model, the
  container lifecycle and Boot auto-configuration live in `07-spring-core.md`. This guide owns the
  API-shaped subset: `HttpMessageConverter` negotiation, `ProblemDetail`, `ResponseEntity`,
  `ApiVersionStrategy`. `[X-REF 07]`
- Contract testing (Pact, Spring Cloud Contract), WireMock, `@WebMvcTest`, Testcontainers and
  schema-compatibility CI *mechanics* live in `16-testing.md`. This guide owns what the contract test
  must assert. `[X-REF 16]`
- Metrics, structured logging, distributed tracing, `traceparent` propagation, SLI/SLO and error
  budgets live in `20-observability-operations.md`. This guide owns the correlation-id field in the
  error body and the RED metrics an API must emit. `[X-REF 20]`
- API gateway products, WAF, CDN and managed rate limiting at the edge live in `18-cloud-aws.md`;
  Ingress and service-mesh routing live in `19-docker-kubernetes.md`. `[X-REF 18]` `[X-REF 19]`
- CAP/PACELC, consistent hashing, quorum arithmetic, load shedding as a capacity strategy, the
  45-minute design structure and back-of-envelope sizing live in `22-system-design.md`. This guide
  states each API-visible mechanism once and points there. `[X-REF 22]`
- Virtual threads, `CompletableFuture`, `ThreadPoolExecutor` queueing and backpressure primitives
  live in `05-multithreading-concurrency.md` and `04-modern-java.md`. `[X-REF 05]` `[X-REF 04]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

**Every example, path, status code, field name and number comes from the QuizStakes domain in
`src/scenario/scenario.md`.** The API surfaces the bible must design against are: card deposit
(`DEP-000` … `DEP-910`), bank-deposit inbound push (`BDP-*`), withdrawal (two schemas, one
vocabulary), stake reservation (the black-box boundary), instrument verification, the restriction
decision call, onboarding application capture (`AO-*`), activation (`AA-*`), document requirements,
and the operator-facing `PaymentRun`. The services are `ApplicationGateway`, `RouterInt`,
`JwtService`, `AccountOpening`, `AccountMaintenance`, `ClientRestrictions`, `PaymentService`,
`FundsLedger`, `DocumentRequirements`, `InternalPlatforms`, `ProfileService`. Never `/orders`,
`/users`, `/pets`, `foo`, or `Dog extends Animal`. The load and latency figures are the real ones
from Appendix A: **2.4M registered clients, 95k card deposits/day at 40/sec, 2.8M stake reservations/
day at 1,200/sec with 3,400/sec settlement bursts, 19.8M ledger entries/day at 230 writes/sec
sustained and 13,600/sec peak, a 30 ms restriction-decision budget, a 150 ms stake-reservation
budget, a hard 500 ms self-exclusion budget, three `FundsLedger` instances at 12 GB heap, operator
sessions living 30–90 minutes.**

The four architectural rules from scenario § 5.1 constrain every design decision in this guide, and
the bible must say so at the point of decision: the client token is **stripped at the gateway** and
replaced with an application token; **no token carries permissions, restrictions or account status**;
`FundsLedger` uses **partition affinity by client id** which buys state locality and *nothing for
correctness*; and `PaymentRun` is **not a client state**.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real spec text, registry entry, source comment or javadoc (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is YAML/proto/SQL) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value, byte arithmetic or latency budget explicitly |
| `[HDR]` | give the exact HTTP field name, its Structured-Field type, and an example value |
| `[CODE]` | give the exact status code number and the client action it prescribes |
| `[API]` | give the exact Java/Spring type or method signature |
| `[WIRE]` | show the actual bytes/frames/headers on the wire, not a description of them |
| `[SPEC]` | cite the specific RFC/spec section number, not just the RFC number |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — a curl transcript, a response with headers, a log line — and read it line by line |
| `[TABLE]` | must be rendered as a table |

---

# PART 1 — BASICS

## §1.1 Why an API contract exists at all

1.1.1 The problem statement: two programs written by two teams on two release cadences must agree on
      a message shape, and neither can be recompiled by the other. An API is that agreement made
      explicit and independently deployable. `[PROVE]`
1.1.2 What "the contract" actually consists of, enumerated — it is much wider than the JSON shape:
      the URI space, the method semantics, the status-code vocabulary, the header set, the
      representation schema, the error schema, the authentication scheme, the concurrency-control
      scheme, the pagination scheme, the rate-limit policy, the ordering and delivery guarantees,
      and the *compatibility promise*. `[TABLE]`
1.1.3 Why the contract is the expensive artifact: implementation is replaceable, published contracts
      are not. Once a mobile client is in an app store you cannot recompile it, so the removal of one
      field is a permanent liability. `[PROVE]`
1.1.4 The two audiences that pull in opposite directions: the *first* integrator wants convenience
      and denormalised payloads; every *subsequent* integrator wants stability and orthogonality.
      Design for the second.
1.1.5 Coupling vocabulary applied to APIs: afferent coupling (who calls you) determines your
      freedom to change; a contract with 200 unknown external callers and one with 3 known internal
      callers are different engineering problems with the same syntax. `[PROVE]`
1.1.6 "Design-first" vs "code-first": what each produces, when each is defensible, and why
      design-first is the default for anything crossing an org boundary. `[TABLE]`
1.1.7 The QuizStakes framing for this whole guide: the platform is a black box whose *entire
      product* is a contract — a stake reservation either happened once or not at all, a restriction
      decision must answer inside 30 ms, and a self-exclusion must take effect inside 500 ms. Those
      three sentences are API design problems, not implementation problems. `[NUM]` `[SOURCE]`
1.1.8 The interview framing this guide serves: turning "how would you design this API" into a
      sequence of named, defensible decisions — resource model, method choice, status vocabulary,
      retry safety, page contract, error contract, compatibility promise — each with a stated
      alternative you rejected and why.
1.1.9 What API design is *not*: it is not naming. Interviewers who ask "singular or plural" are
      screening; interviewers who ask "what can the client safely retry" are interviewing.
1.1.10 The reading list, ranked, with what each is for: RFC 9110 (normative, and the single highest
       return-on-investment document in the topic), Fielding's dissertation ch. 5 (what REST
       actually claims), *Principles of Web API Design* (Higginbotham — the design process),
       *The Design of Web APIs* (Lauret — modelling), *RESTful Web API Patterns and Practices*
       (Amundsen), Google AIP (aip.dev — the most complete published rule set), Zalando's guidelines
       (the best MUST/SHOULD checklist), Microsoft's Azure/Graph patterns (LRO and delta), Stripe's
       versioning docs (the only widely-copied date-versioning scheme). `[SOURCE]` `[RESEARCH]`

*(10 leaves)*

## §1.2 The HTTP substrate, mapped

1.2.1 The RFC 9110–9114 reorganisation: what moved where when RFC 7230–7235 was replaced in June
      2022, and why every pre-2022 citation you will read points at an obsolete document. `[SPEC]`
      `[VERSION-TRAP]`
1.2.2 The split that matters conceptually: **semantics** (9110 — methods, status codes, fields,
      content negotiation, conditional requests, range requests, authentication) versus **syntax**
      (9112 HTTP/1.1, 9113 HTTP/2, 9114 HTTP/3) versus **caching** (9111). One contract, three wire
      formats. `[PROVE]`
1.2.3 The anatomy of a request as RFC 9110 defines it: method, target URI (and the four
      request-target forms — origin-form, absolute-form, authority-form, asterisk-form), header
      fields, content, trailer fields. `[SPEC]` `[WIRE]`
1.2.4 The anatomy of a response: status code, reason phrase (and why HTTP/2 and HTTP/3 dropped it),
      header fields, content, trailer fields. `[WIRE]`
1.2.5 "Resource", "representation", "target URI" and "selected representation" as RFC 9110 uses
      them, and why the distinction is load-bearing for `ETag`, `Vary`, `Content-Location` and
      conditional requests. `[SPEC]` `[PROVE]`
1.2.6 Field-name case-insensitivity, field-value ordering, and the rules for combining repeated
      fields with commas — plus the exceptions (`Set-Cookie`). `[SPEC]` `[TRAP]`
1.2.7 Structured Field Values (RFC 8941 → **RFC 9651**): the types — Item, List, Dictionary,
      Integer, Decimal, String, Token, Byte Sequence, Boolean, **Date**, Display String — and why
      new fields (`Deprecation`, `RateLimit`, `Accept-Query`, `Idempotency-Key`,
      `Signature-Input`) are all defined in these terms. `[SPEC]` `[RESEARCH]`
1.2.8 The `Date` structured type specifically: `@1688169599` is seconds since epoch, and that is why
      `Deprecation: true` cannot parse. `[HDR]` `[VERSION-TRAP]`
1.2.9 The IANA registries you should know exist, because "is this header/status/method standard?" is
      a lookup and not an opinion: HTTP Field Name Registry, HTTP Status Code Registry, HTTP Method
      Registry, HTTP Cache Directive Registry, HTTP Authentication Scheme Registry, Link Relation
      Types, Media Types, and the **HTTP Problem Types** registry. `[SOURCE]` `[RESEARCH]`
1.2.10 The current contents of the `http-problem-types` registry, verbatim: `about:blank`
       ("See HTTP Status Code", RFC 9457), `#date` ("Date Not Acceptable", 400, RFC 9458 § 6.5.2),
       `#ohttp-key` (400, RFC 9458 § 5.3), and the three digest-fields types
       `#digest-unsupported-algorithms`, `#digest-invalid-values`, `#digest-mismatched-values`
       (all 400). Registration policy: **Specification Required**. `[SOURCE]` `[RESEARCH]`
1.2.11 The `X-` prefix deprecation (RFC 6648): why `X-Request-Id` is a legacy spelling and what to do
       instead. `[TRAP]` `[SPEC]`
1.2.12 Trailer fields: what they are, when they are legal, why almost nothing reads them over
       HTTP/1.1 with chunked encoding, and the one place they are load-bearing — **gRPC's
       `grpc-status`**. `[WIRE]` `[TRAP]`
1.2.13 URI syntax per RFC 3986: scheme, authority, path, query, fragment; percent-encoding;
       reserved vs unreserved characters; why the **fragment never reaches the server**; and why
       `/` inside a path segment must be encoded as `%2F` (and why many servers reject it anyway).
       `[SPEC]` `[TRAP]`
1.2.14 Practical URI limits: no limit in the spec, but ~2,000 characters is the interoperable
       ceiling and 8 KB is a common server header/line limit — the concrete reason a big filter
       payload cannot live in a query string. `[NUM]` `[TRAP]`
1.2.15 What HTTP/2 and HTTP/3 change for API design specifically: multiplexing removes the
       6-connection-per-origin limit (so request-per-resource stops being expensive and *batching
       endpoints lose most of their justification*), HPACK/QPACK make repeated headers cheap, and
       server push is dead (removed from Chrome; `103 Early Hints` replaced it). `[X-REF 10]`
       `[VERSION-TRAP]`
1.2.16 `103 Early Hints` (RFC 8297): what it is for, and the interim-response model (1xx responses
       precede the final response). `[CODE]` `[RESEARCH]`

*(16 leaves)*

## §1.3 REST, precisely — Fielding's actual claims

1.3.1 The origin: REST is chapter 5 of Fielding's 2000 UC Irvine dissertation, and it is a
      *description of the Web's architectural style*, derived to explain why the Web scaled — not a
      recipe for JSON over HTTP. `[SOURCE]`
1.3.2 The six constraints, named, with what each buys and what each costs: **client–server**
      (separation of concerns), **stateless** (visibility, reliability, horizontal scale — at the
      cost of repeated per-request context), **cacheable** (latency and load — at the cost of
      staleness), **uniform interface** (independent evolution — at the cost of efficiency for
      specialised needs), **layered system** (intermediaries: proxies, gateways, CDNs, WAFs), and
      **code-on-demand** (the only *optional* one). `[TABLE]` `[PROVE]` `[RESEARCH]`
1.3.3 The four sub-constraints of the uniform interface, which is the one people skip: identification
      of resources, manipulation of resources through representations, self-descriptive messages,
      and **hypermedia as the engine of application state**. `[SPEC]` `[PROVE]`
1.3.4 "Self-descriptive message" made concrete: everything an intermediary needs to route, cache,
      retry or reject must be in the message — which is exactly why a verb in the URI and a `200`
      with an error body both break REST at the *intermediary* level, not at the aesthetic level.
      `[PROVE]`
1.3.5 Fielding's 2008 post "REST APIs must be hypertext-driven": a REST API should be enterable with
      **no prior knowledge beyond the initial URI and a set of standardised media types**. By this
      definition almost no production "REST API" is REST. `[SOURCE]` `[TRAP]` `[RESEARCH]`
1.3.6 The honest position to hold in an interview: what the industry calls REST is *HTTP-based
      resource-oriented RPC at Richardson level 2*, and that is a defensible engineering choice —
      but say that you know the difference. `[TRAP]`
1.3.7 Statelessness, dissected: what "stateless" does and does not forbid. Server-side *resource*
      state is fine; server-side *session* state keyed by connection is not. `[PROVE]` `[TRAP]`
1.3.8 The consequence of statelessness that actually pays: any instance serves any request, so
      `RouterInt` can use least-connections for `ApplicationGateway`, `AccountOpening`,
      `PaymentService` and `ProfileService`. The two exceptions in QuizStakes — session affinity for
      `InternalPlatforms` (30–90 minute operator sessions) and partition affinity for `FundsLedger`
      — are deliberate, documented violations, and the `FundsLedger` one buys **state locality only,
      not correctness**. `[SOURCE]` `[NUM]` `[PROVE]`
1.3.9 What statelessness costs: every request re-carries auth and context, so token size,
      re-authorisation cost and repeated lookups become the bill. Name the mitigations (short-lived
      application tokens, claim caching, gateway-side verification). `[X-REF 13]`
1.3.10 Layered system in practice: enumerate every intermediary that will read your response and
       what each reads — browser cache, corporate proxy, CDN, API gateway, service mesh sidecar,
       load balancer, WAF. Each one is a reason the status line and cache headers must be honest.
       `[TABLE]`
1.3.11 Code-on-demand's real-world descendants: JavaScript, and nothing else you will ship.

*(11 leaves)*

## §1.4 The maturity ladder and the style taxonomy

1.4.1 The Richardson Maturity Model, all four levels with a QuizStakes example of each: **Level 0**
      one URI one verb (`POST /gateway` with an action field — "the swamp of POX"); **Level 1**
      resources but one verb (`POST /deposits/42/capture`); **Level 2** resources plus HTTP verbs
      plus status codes (where essentially all production APIs sit); **Level 3** hypermedia controls.
      `[TABLE]` `[RESEARCH]`
1.4.2 What the model is *not*: it is not a quality score and Richardson never claimed level 3 is
      mandatory. Level 2 with a rigorous compatibility policy beats level 3 with none. `[TRAP]`
1.4.3 The four wire styles you must be able to choose between, and the axis each one optimises:
      **REST/HTTP** (uniform interface, caching, intermediary-friendly), **RPC/gRPC** (schema-first,
      binary, streaming, low latency), **GraphQL** (client-specified projection, one round trip),
      **event push** (server-initiated, decoupled in time). `[TABLE]`
1.4.4 The fifth and sixth styles worth naming: **SOAP/WS-*** (why it lost: XML envelope weight,
      WS-* sprawl, tooling coupling — and where it survives: banking, WS-Security, WS-AtomicTransaction)
      and **OData** (`$filter`, `$select`, `$expand`, `$top`, `$skip`, `$count`, `$orderby`,
      `$metadata`) as the most complete standardised query-over-REST attempt. `[RESEARCH]`
1.4.5 **Connect / gRPC-Web** as the "gRPC that works in a browser" tier, and **JSON-RPC 2.0** as
      the minimal RPC contract. `[RESEARCH]`
1.4.6 The decision procedure, as a ranked question list rather than a preference: who is the caller
      (browser / mobile / your own service / another company)? is there a trust boundary? is the
      shape of the read known at design time? does anything stream? is there an intermediary you
      need to cache at? can the client be recompiled with you? `[FLOW]`
1.4.7 The QuizStakes answer, per boundary, with reasons: **client → `ApplicationGateway` is
      REST/JSON** (public, browser and mobile, must survive uncoordinated client releases);
      **service → service behind `RouterInt` is a candidate for gRPC** (schema-first, both sides
      release together, the 30 ms restriction-decision budget makes serialisation cost visible);
      **`FundsLedger` stake reservation stays REST with a mandatory idempotency key** (the contract's
      whole value is the retry story); **PSP → us is webhooks** (they initiate, across an org
      boundary); **operator UI aggregation across nine services is the textbook BFF/GraphQL case**.
      `[NUM]` `[PROVE]`

*(7 leaves)*

## §1.5 Resource modelling and URI design

1.5.1 Finding the resources: from *capabilities* (what can a caller do) to *activities and steps*
      (Higginbotham's process) to nouns — not from your database tables. State plainly that
      table-per-endpoint is the most common failure mode and why it leaks your schema into your
      contract. `[PROVE]` `[RESEARCH]`
1.5.2 The three resource archetypes and the URI shape of each: **document** (`/applications/{id}`),
      **collection** (`/applications`), **store** (client-assigned keys — `PUT /clients/{id}/
      preferences/{key}`), plus **controller** (an action — `POST /deposits/{id}/captures`) and
      **singleton sub-resource** (`/clients/{id}/restriction-summary`). `[TABLE]` `[RESEARCH]`
1.5.3 Plural collection nouns, and the exceptions where singular is right: singletons
      (`/clients/{id}/profile`), and the AIP-156 singleton-resource pattern. `[RESEARCH]`
1.5.4 Casing and separators: `kebab-case` in path segments, `snake_case` **or** `camelCase` in JSON
      bodies (pick one and never mix), `Kebab-Case` for header field names, lowercase for enum
      values or `SCREAMING_SNAKE_CASE` — the rule is *consistency is worth more than which*.
      QuizStakes uses `SCREAMING_SNAKE_CASE` status names (`RESTRICTION_CLEAR`, `CAPTURE_FAILED`).
      `[TABLE]` `[SOURCE]`
1.5.5 Nesting depth: at most one level of containment (`/clients/{id}/withdrawals`), and the reason —
      deeper nesting encodes a relationship that may change and forces the client to know the
      hierarchy. Beyond one level, use a top-level collection with a filter
      (`/withdrawals?clientId=…`). `[PROVE]` `[TRAP]`
1.5.6 The dual-addressing rule: if a resource has its own identity it gets its own top-level
      collection, *and* may be reachable through a parent as a filtered view. Both
      `/withdrawals/{id}` and `/clients/{id}/withdrawals` are correct; only one is canonical, and the
      canonical one is what goes in `Location`, `self` links and events. `[PROVE]`
1.5.7 Identifier design: opaque vs meaningful ids, sequential integers as an enumeration and
      business-intelligence leak, UUIDv4 vs **UUIDv7** (time-ordered, RFC 9562) vs ULID vs a
      prefixed id (`dep_3f7a…`, Stripe-style) — with the index-locality argument for time-ordered
      ids. `[TABLE]` `[NUM]` `[X-REF 09]` `[RESEARCH]`
1.5.8 Why exposing a database primary key is a coupling decision, not a convenience: it survives
      into every client, log and support ticket, and it constrains your ability to shard or migrate.
      `[TRAP]`
1.5.9 Composite and natural keys in a URI: when a natural key is right (`/currencies/GBP`) and the
      encoding hazards of a composite one. `[TRAP]`
1.5.10 Google AIP-122 resource names: the `collection/id/collection/id` full-resource-name scheme
       (`clients/1042/withdrawals/778`), why it appears **in the payload** and not only in the URL,
       and how it makes a reference self-describing without a link. `[SOURCE]` `[RESEARCH]`
1.5.11 The action-in-URI antipattern, with each concrete form named: `POST /getWithdrawal`,
       `GET /deleteClient?id=3`, `POST /api/do?cmd=capture`. State the *mechanical* cost — every
       intermediary's caching, retry and idempotency assumptions are now wrong — not just the
       aesthetic cost. `[TRAP]` `[PROVE]`
1.5.12 Trailing slashes, file extensions (`/withdrawals/778.json`) as a poor man's content
       negotiation, and case sensitivity of paths. `[TRAP]`
1.5.13 What goes in the path vs the query vs the body vs a header, as a rule with a reason for each:
       **path** = identity and hierarchy (part of the resource's name); **query** = non-identifying
       selection — filter, sort, page, projection; **body** = the representation, and anything large
       or sensitive; **header** = cross-cutting metadata (auth, content type, trace, idempotency
       key, conditional request). `[TABLE]` `[PROVE]`
1.5.14 **Never put a secret in a query string.** The concrete leak paths: access logs, browser
       history, `Referer` header, CDN logs, APM traces, error-reporting screenshots, and shell
       history in a support ticket. `[TRAP]` `[X-REF 13]`
1.5.15 The base-path decision: `/api` prefix or a dedicated host (`api.quizstakes.example`), and what
       each costs in CORS, cookie scope, TLS certificates and CDN configuration. `[X-REF 13]`
1.5.16 Zalando's URL rules as a checklist to run your paths against: lowercase separate words with
       hyphens, `snake_case` never in paths, URL-friendly resource identifiers
       (`[a-zA-Z0-9:.\_\-/]*`), no trailing slashes, path segments must be nouns.
       `[SOURCE]` `[RESEARCH]`

*(16 leaves)*
## §1.6 The method surface, complete

1.6.1 The registered method set and what each *means* per RFC 9110 § 9.3: `GET`, `HEAD`, `POST`,
      `PUT`, `DELETE`, `CONNECT`, `OPTIONS`, `TRACE`, plus `PATCH` (RFC 5789) and `QUERY`
      (RFC 10008). `[TABLE]` `[SPEC]`
1.6.2 `GET`: transfer a current representation. No body semantics — a body on a GET is not forbidden
      by 9110 but "**a client SHOULD NOT generate content in a GET request**" and intermediaries
      will drop it, which is the real reason `GET` with a body does not work. `[SPEC]` `[TRAP]`
1.6.3 `HEAD`: identical to `GET` without the content. What it is genuinely used for — existence
      checks, `Content-Length` probing, cache validation — and why a server that returns a body on
      HEAD is broken. `[SPEC]`
1.6.4 `POST`: "process the representation according to the resource's own semantics." Note the width
      of that definition — POST is the escape hatch and is *not* defined as "create". `[SPEC]`
      `[TRAP]`
1.6.5 `PUT`: replace the target resource's state with the enclosed representation. Whole-resource
      semantics: **an omitted field means "clear it"**, not "leave it alone", and that is the single
      most common PUT bug. `[SPEC]` `[TRAP]` `[PROVE]`
1.6.6 `PUT` for creation: legal when the client chooses the URI. `201 Created` on first call,
      `200`/`204` on subsequent. With `If-None-Match: *` it becomes a race-free create. `[CODE]`
      `[PROVE]`
1.6.7 `DELETE`: remove the association between the target and its functionality. What the response
      should be (`204`, or `200` with a body, or `202` for asynchronous deletion), and why the
      second `DELETE` returning `404` is acceptable but `204` is friendlier to retrying clients.
      `[CODE]` `[TRAP]`
1.6.8 `PATCH` (RFC 5789): apply a described set of changes. **The description is a document with its
      own media type** — `PATCH` with `application/json` and a partial object is technically
      undefined and universally done anyway. `[SPEC]` `[TRAP]`
1.6.9 `OPTIONS`: request communication options. Its two real uses — CORS preflight, and returning
      `Allow`. Why the `*` request-target form exists. `[X-REF 13]`
1.6.10 `TRACE`: the loopback diagnostic, why it is disabled everywhere (Cross-Site Tracing / XST),
       and what "`405` on TRACE" tells a scanner. `[X-REF 13]` `[TRAP]`
1.6.11 `CONNECT`: the tunnel method — why it only appears in proxies and is irrelevant to your API.
1.6.12 `QUERY` (RFC 10008, June 2026): safe, idempotent, **cacheable with request content in the
       cache key**, body required, `Content-Type` mandatory, response `Content-Location` names a
       resource for the result set and `Location` names a resource that repeats the query. `[SPEC]`
       `[RESEARCH]` `[VERSION-TRAP]`
1.6.13 `Accept-Query` (RFC 10008): a Structured Field List of media types the resource accepts for
       QUERY — `Accept-Query: "application/jsonpath", application/sql;charset="UTF-8"`. `[HDR]`
       `[RESEARCH]`
1.6.14 The `Allow` response header (`[HDR]`) and its mandatory pairing with `405 Method Not Allowed`.
1.6.15 Method extension: `LINK`/`UNLINK`, WebDAV's `PROPFIND`/`MKCOL`/`LOCK`, and why inventing a
       method is almost always wrong (proxies, CDNs, client libraries and WAFs whitelist methods).
       `[TRAP]`
1.6.16 Method override tunnelling: `X-HTTP-Method-Override`, `_method` form field, and
       `POST ?_method=DELETE`. When you are forced into it (a hostile corporate proxy) and the
       security hazard it creates (CSRF surface, WAF bypass). `[TRAP]` `[X-REF 13]`
1.6.17 OpenAPI 3.2's `additionalOperations` keyword, which finally lets you document a non-standard
       method. `[RESEARCH]` `[VERSION-TRAP]`

*(17 leaves)*

## §1.7 Safe, idempotent, cacheable — three orthogonal properties

1.7.1 The three definitions, stated exactly as RFC 9110 does, because candidates routinely blur
      them. **Safe** (§ 9.2.1): "the defined semantics are essentially read-only" — the client does
      not request and does not expect a state change. **Idempotent** (§ 9.2.2): "the intended effect
      on the server of multiple identical requests … is the same as the effect for a single such
      request." **Cacheable** (§ 9.2.3): the response may be stored and reused. `[SPEC]` `[SOURCE]`
1.7.2 The implication chain and its direction: safe ⇒ idempotent, but idempotent ⇏ safe. `PUT` and
      `DELETE` are idempotent and unsafe. `[PROVE]`
1.7.3 The full classification table, with the fourth column people forget (cacheability by default)
      and the fifth (body semantics): `GET`, `HEAD`, `OPTIONS`, `TRACE`, `QUERY` safe; `PUT`,
      `DELETE`, `QUERY` idempotent-and-unsafe (QUERY is safe, listed for the contrast); `POST`,
      `PATCH`, `CONNECT` neither. `GET`/`HEAD`/`POST` (with explicit freshness) and `QUERY`
      cacheable. `[TABLE]` `[SPEC]`
1.7.4 **The sentence that earns the interview:** idempotency is the property that makes a **retry
      safe**, and a retry is not optional — a load balancer, an HTTP client's retry policy, a
      service mesh, a mobile radio handover and a user's double-tap will all re-send. `[PROVE]`
1.7.5 The concrete failure this prevents, in QuizStakes terms: `DEP-300 CAPTURING` times out after
      the PSP has actually captured; the naive retry produces a second capture and the client is
      charged twice. Scenario § 12.2 states it directly — "**capture retry is not idempotent by
      default … the idempotency key is mandatory, not an optimisation**." `[SOURCE]` `[NUM]`
1.7.6 Idempotency is about *effect on server state*, not about the response being byte-identical.
      A second `DELETE` may legitimately return `404`; the resource is still absent either way.
      `[PROVE]` `[TRAP]`
1.7.7 Why `PATCH` is not required to be idempotent, and why a *particular* payload may be:
      `{"status":"CANCELLED"}` is idempotent, `{"balanceDelta":-1000}` is not, and JSON Patch's
      `{"op":"add","path":"/tags/-"}` is not. The **method** carries the guarantee, so a generic
      client must assume the worst. `[PROVE]` `[TRAP]` `[RESEARCH]`
1.7.8 **Trap:** "POST is not idempotent" is a statement about the *protocol's guarantee*, not a
      licence to build a non-idempotent endpoint. You make POST retry-safe with an idempotency key
      (§1.17). `[TRAP]`
1.7.9 Idempotency vs commutativity vs at-most-once vs exactly-once: four different properties that
      get called "idempotent" in interviews. Define each and give the API example that distinguishes
      them. `[TABLE]` `[PROVE]`
1.7.10 The `idempotency_level` concept in protobuf/gRPC (`NO_SIDE_EFFECTS`, `IDEMPOTENT`,
       `IDEMPOTENCY_UNKNOWN`), and that `buf` treats a change to it as breaking
       (`RPC_SAME_IDEMPOTENCY_LEVEL`). `[RESEARCH]`
1.7.11 Where "safe" is *lied about* in practice: analytics side effects on GET, a GET that lazily
       provisions, a GET that consumes a one-time token. Each one breaks prefetchers, link scanners,
       email clients and CDN warmers. `[TRAP]` `[PROVE]`
1.7.12 The retry-safety decision table the bible must publish: for each QuizStakes endpoint, is it
       safe / idempotent / requires a key / must never be auto-retried. `[TABLE]`

*(12 leaves)*

## §1.8 The status code surface, complete

1.8.1 The class semantics and the one rule that follows from them: 1xx interim, 2xx success, 3xx
      redirection, 4xx client error, 5xx server error — and a client is required to treat an
      unrecognised code as `x00` of its class. That rule is why adding a new 4xx is not a breaking
      change. `[SPEC]` `[PROVE]`
1.8.2 The selection principle: choose the code by **what the client should do next**, not by what
      happened internally. `[PROVE]`
1.8.3 **1xx:** `100 Continue` (and the `Expect: 100-continue` handshake for large uploads),
      `101 Switching Protocols` (WebSocket upgrade), `102 Processing` (WebDAV, deprecated),
      `103 Early Hints`. `[CODE]` `[TABLE]`
1.8.4 **2xx, all of them:** `200 OK`, `201 Created` (+ mandatory `Location`), `202 Accepted`
      (asynchronous — the work is **not** done), `203 Non-Authoritative Information`,
      `204 No Content` (deliberately no body), `205 Reset Content`, `206 Partial Content` (+ `Range`/
      `Content-Range`), `207 Multi-Status` (WebDAV; the usual answer for bulk), `208 Already
      Reported`, `226 IM Used`. `[TABLE]` `[CODE]`
1.8.5 `201` in detail: what `Location` must contain (the canonical URI of the created resource), when
      to echo the representation vs return `204`, and the `Content-Location` distinction. `[CODE]`
      `[HDR]`
1.8.6 `202` in detail: the correct payload is a **job/operation resource** — `202` +
      `Location: /payment-runs/{id}` + `{"status":"PENDING"}` + optionally `Retry-After`. This is the
      right answer to "the operation takes 30 seconds". `[CODE]` `[FLOW]`
1.8.7 `204` vs `200`-with-empty-body vs `200`-with-`null`: what each does to a generated client, and
      why `204` must not carry `Content-Type`. `[TRAP]`
1.8.8 **3xx, all of them, and the distinction that actually matters:** `300 Multiple Choices`,
      `301 Moved Permanently`, `302 Found`, `303 See Other`, `304 Not Modified`, `305 Use Proxy`
      (deprecated), `307 Temporary Redirect`, `308 Permanent Redirect`. `[TABLE]` `[CODE]`
1.8.9 The method-rewriting hazard: `301`/`302` historically caused clients to rewrite POST to GET;
      `307`/`308` **preserve the method and body**. `303` deliberately rewrites to GET, which is
      exactly what you want after a POST that produced a result document. `[PROVE]` `[TRAP]`
      `[SPEC]`
1.8.10 `304 Not Modified` in detail: it is a *cache-validation* response, it must not carry content,
       and it must carry the headers a cache needs to update its stored entry (`ETag`,
       `Cache-Control`, `Date`, `Vary`). `[CODE]` `[SPEC]`
1.8.11 **4xx, all of them:** `400 Bad Request`, `401 Unauthorized`, `402 Payment Required`,
       `403 Forbidden`, `404 Not Found`, `405 Method Not Allowed` (+ `Allow`), `406 Not Acceptable`,
       `407 Proxy Authentication Required`, `408 Request Timeout`, `409 Conflict`, `410 Gone`,
       `411 Length Required`, `412 Precondition Failed`, `413 Content Too Large`,
       `414 URI Too Long`, `415 Unsupported Media Type`, `416 Range Not Satisfiable`,
       `417 Expectation Failed`, `418 I'm a Teapot` (RFC 2324; **not** a real code — do not ship it),
       `421 Misdirected Request`, `422 Unprocessable Content`, `423 Locked`, `424 Failed Dependency`,
       `425 Too Early` (RFC 8470), `426 Upgrade Required`, `428 Precondition Required` (RFC 6585),
       `429 Too Many Requests` (RFC 6585), `431 Request Header Fields Too Large` (RFC 6585),
       `451 Unavailable For Legal Reasons` (RFC 7725). `[TABLE]` `[CODE]` `[RESEARCH]`
1.8.12 `401` vs `403`, memorised properly: **401 = "I do not know who you are"** (unauthenticated
       — the name is a historical error) and **MUST** carry `WWW-Authenticate`; **403 = "I know who
       you are and the answer is no"**, and re-authenticating will not help. `[TRAP]` `[SPEC]`
1.8.13 `403` vs `404` as an **information-disclosure decision**: returning `404` for a resource that
       exists but is not yours prevents enumeration. State it as a deliberate trade (worse
       diagnostics for the legitimate caller) and name the QuizStakes case — an operator querying
       another operator's case. `[TRAP]` `[X-REF 13]`
1.8.14 `400` vs `422` vs `409`: syntax/parse failure → `400`; syntactically valid but semantically
       rejected → `422`; conflicts with *current resource state* → `409`. Note that `422` is now
       "Unprocessable **Content**" in RFC 9110 and that many teams use only `400` — which is
       defensible if the problem `type` distinguishes them. `[TABLE]` `[TRAP]` `[VERSION-TRAP]`
1.8.15 `409` in detail with all three of its real causes: unique-constraint violation, optimistic
       version mismatch, and an illegal state transition (`DEP-500 SETTLED` → cancel). All three tell
       the client "re-read and decide", which is why they share a code. `[CODE]` `[PROVE]`
1.8.16 `410 Gone` vs `404`: `410` asserts the resource *existed and is intentionally, permanently
       gone*. Use it for retired endpoints and hard-deleted resources; it tells crawlers and clients
       to stop asking. `[CODE]` `[TRAP]` `[RESEARCH]`
1.8.17 `412 Precondition Failed` vs `428 Precondition Required`: `412` means your `If-Match` did not
       match; `428` means you did not send one and the server insists (the "lost update" defence).
       `[CODE]` `[PROVE]`
1.8.18 `415` vs `406`: `415` = I cannot parse *your* body (`Content-Type` unsupported); `406` = I
       cannot produce what *you* asked for (`Accept` unsatisfiable). `[TRAP]`
1.8.19 `425 Too Early` (RFC 8470): its actual meaning is *TLS early-data replay risk*, not "a
       duplicate request is in flight". The current guide suggests `425` as an idempotency-conflict
       response; the idempotency draft says **409**. `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
1.8.20 `429 Too Many Requests` (RFC 6585): must be paired with `Retry-After`, and should carry
       `RateLimit`/`RateLimit-Policy`. `[CODE]` `[HDR]`
1.8.21 `413`/`414`/`431` as the DoS-defence codes, and the concrete server limits that produce them
       (`server.max-http-request-header-size` default **8 KB** in Spring Boot;
       `spring.servlet.multipart.max-file-size` default **1 MB**). `[NUM]` `[RESEARCH]`
1.8.22 **5xx, all of them:** `500 Internal Server Error`, `501 Not Implemented`, `502 Bad Gateway`,
       `503 Service Unavailable` (+ `Retry-After`), `504 Gateway Timeout`,
       `505 HTTP Version Not Supported`, `506 Variant Also Negotiates`,
       `507 Insufficient Storage`, `508 Loop Detected`, `510 Not Extended`,
       `511 Network Authentication Required`. `[TABLE]` `[CODE]`
1.8.23 The 5xx retry semantics that clients actually implement: `502`/`503`/`504` are retryable,
       `500` is ambiguous and usually is not, and `501` never is. Which is why returning `500` for a
       downstream timeout costs you the retry. `[PROVE]` `[TRAP]`
1.8.24 `503` vs `429`: overload of the *server* vs overload by *this client*. Load shedding returns
       `503`; quota enforcement returns `429`. `[TRAP]` `[X-REF 22]`
1.8.25 **Trap:** returning `200 OK` with `{"error": …}`. Enumerate every layer it breaks — the CDN
       caches the error, the load balancer's health check passes, the client's retry policy does not
       fire, the circuit breaker never opens, the dashboard shows 100% availability, and the
       generated client's typed error branch is unreachable. `[TRAP]` `[PROVE]`
1.8.26 **Trap:** the reverse mistake — mapping every failure to `500`. It converts a client bug into
       a pager alert and destroys your error-budget signal. `[TRAP]` `[X-REF 20]`
1.8.27 The status-code decision tree the bible must publish, as a flow: is it a state change? did it
       succeed? is it complete? can the client fix it? is it about identity, permission, state,
       format, or rate? `[FLOW]` `[TABLE]`
1.8.28 The QuizStakes status-code map: every `DEP-*`, `BDP-*`, `AO-*`, `AA-*` outcome mapped to the
       HTTP code the API returns. `DEP-190 RESTRICTED` → `403` (or `409`?), `DEP-199
       LIMIT_EXCEEDED` → `422`, `DEP-290 AUTH_DECLINED` → `402` or `422`, `DEP-390 CAPTURE_FAILED` →
       `502`, restriction service unreachable inside the 30 ms budget → `503` vs fail-closed. Each
       choice argued, not asserted. `[TABLE]` `[PROVE]` `[NUM]`
1.8.29 **Domain status codes are not HTTP status codes.** QuizStakes' `DEP-301` lives in the body;
       the HTTP status says whether the *request* worked. Conflating the two is how you end up with
       `200` + error body. `[TRAP]` `[PROVE]`

*(29 leaves)*

## §1.9 The header surface

1.9.1 The four functional groups, so you can place any header: **representation metadata**
      (`Content-Type`, `Content-Length`, `Content-Encoding`, `Content-Language`,
      `Content-Location`), **request preferences** (`Accept*`, `Prefer`, `Range`),
      **conditionals** (`If-Match`, `If-None-Match`, `If-Modified-Since`, `If-Unmodified-Since`,
      `If-Range`), and **control data** (`Authorization`, `Cache-Control`, `Host`, `Retry-After`,
      `Location`, `Allow`, `ETag`, `Vary`, `Date`, `Age`). `[TABLE]` `[SPEC]`
1.9.2 `Content-Type` and its parameters: `charset`, `boundary`, and the structured-suffix convention
      `+json` / `+xml` / `+cbor` — and why `application/vnd.quizstakes.deposit+json` parses as JSON
      to any correct client. `[HDR]` `[SPEC]`
1.9.3 The media-type registration tree: `application/json` (standards tree), `application/
      vnd.<vendor>.<type>+json` (vendor tree), `application/prs.…` (personal), `application/
      x-…` (unregistered legacy). `[TABLE]` `[SPEC]`
1.9.4 `Authorization` and its schemes: `Bearer` (RFC 6750), `Basic` (RFC 7617), `Digest`, `Negotiate`,
      `HOBA`, `Mutual`, plus AWS SigV4 as a non-registered example. `WWW-Authenticate` challenge
      syntax including `realm`, `error`, `error_description` and `scope` from RFC 6750 § 3.
      `[HDR]` `[X-REF 13]`
1.9.5 `Retry-After`: two syntaxes (delay-seconds and HTTP-date), and the three codes it belongs on —
      `429`, `503`, `301`/`3xx` with `Location`. `[HDR]` `[SPEC]`
1.9.6 `Location` vs `Content-Location`: `Location` names *another* resource (created, redirected-to,
      or a job); `Content-Location` names the specific resource whose representation is in this
      body. Zalando says prefer `Location`. `[TRAP]` `[SOURCE]`
1.9.7 `Prefer` (RFC 7240) and `Preference-Applied`: the registered preferences —
      `respond-async`, `return=representation`, `return=minimal`, `wait`, `handling=strict`,
      `handling=lenient`. `respond-async` + `202` is the standardised way for a client to *choose*
      the async path. `[HDR]` `[SPEC]` `[RESEARCH]`
1.9.8 `Idempotency-Key` (draft-07): an **Item Structured Header whose value MUST be a String** —
      `Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"`. Note the mandatory quotes, which
      almost every hand-rolled implementation gets wrong. `[HDR]` `[RESEARCH]` `[TRAP]`
1.9.9 `RateLimit-Policy` and `RateLimit` (draft-11), with every parameter: policy `q` (quota,
      required Integer), `qu` (quota unit, default `"requests"`; registry also has `content-bytes`
      and `concurrent-requests`), `w` (window seconds), `pk` (partition key, Byte Sequence);
      service-limit `r` (remaining, required), `t` (seconds until reset), `pk`. Example:
      `RateLimit-Policy: "burst";q=100;w=60,"daily";q=1000;w=86400` and `RateLimit: "default";r=50;t=30`.
      `[HDR]` `[NUM]` `[RESEARCH]`
1.9.10 The legacy trio still in the wild: `X-RateLimit-Limit` / `-Remaining` / `-Reset` and the
       unprefixed `RateLimit-Limit` / `-Remaining` / `-Reset` from drafts 00–06 — what GitHub,
       Twitter/X and Stripe actually send. Ship both during transition. `[VERSION-TRAP]` `[RESEARCH]`
1.9.11 `Deprecation` (RFC 9745) and `Sunset` (RFC 8594): `Deprecation` is a Structured Field Date
       (`@1688169599`), `Sunset` is an HTTP-date (`Sun, 30 Jun 2024 23:59:59 GMT`), and **`Sunset`
       MUST NOT be earlier than `Deprecation`**. The `deprecation` link relation carries the
       human-readable notice: `Link: <https://…/deprecation>; rel="deprecation"; type="text/html"`.
       `[HDR]` `[SPEC]` `[VERSION-TRAP]` `[RESEARCH]`
1.9.12 `Link` (RFC 8288): the header form of hypermedia, its parameters (`rel`, `type`, `title`,
       `hreflang`, `anchor`, `media`), the registered relations you will use (`self`, `next`, `prev`,
       `first`, `last`, `describedby`, `alternate`, `up`, `related`, `service-desc`,
       `deprecation`, `latest-version`, `successor-version`), and Zalando's rule that you **must not**
       use Link headers with JSON entities (put links in the body instead). `[HDR]` `[SOURCE]`
       `[RESEARCH]`
1.9.13 Correlation and tracing headers: W3C Trace Context `traceparent` / `tracestate`, W3C
       `baggage`, and the proprietary alternatives (`X-Request-Id`, `X-Correlation-Id`, Zalando's
       mandatory `X-Flow-ID`). The rule: **propagate what you receive, generate when absent, return
       it in every error body**. `[HDR]` `[X-REF 20]` `[RESEARCH]`
1.9.14 Integrity and signing headers, named so you recognise them: `Content-Digest` /
       `Repr-Digest` / `Want-*-Digest` (RFC 9530, which obsoletes the RFC 3230 `Digest` field),
       and `Signature` / `Signature-Input` / `Accept-Signature` (RFC 9421, HTTP Message Signatures).
       Where they matter: PSP callbacks, open-banking APIs, and webhook verification.
       `[HDR]` `[X-REF 13]` `[RESEARCH]`
1.9.15 `Expect: 100-continue`, `TE`, `Connection`, `Upgrade`, `Host` — the hop-by-hop and
       connection-management set, and why they must never be forwarded by a proxy. `[X-REF 10]`
1.9.16 Custom header discipline: no `X-` prefix (RFC 6648), `Kebab-Case-With-Capitals` by convention,
       document them in OpenAPI, and **propagate them across service boundaries** — Zalando makes
       propagation a MUST because a trace that stops at one hop is worthless. `[SOURCE]` `[RESEARCH]`
1.9.17 The QuizStakes header contract: what `ApplicationGateway` accepts from the client
       (`Authorization: Bearer <client token>`, `Idempotency-Key`, `traceparent`,
       `If-Match`, `Accept`), what it **strips** (the client token — scenario § 6.2, "the strip is
       the point"), and what it injects downstream (the application token with `subject = clientId`,
       the propagated trace, the operator role for `InternalPlatforms`). `[TABLE]` `[SOURCE]`
       `[X-REF 13]`
1.9.18 Header size budgets and why they matter for a stateless design: a JWT with 30 claims plus
       trace plus idempotency key is ~2 KB **per request**, multiplied by 1,200 stake reservations/
       sec. Do the arithmetic and name HPACK/QPACK as the mitigation. `[NUM]` `[PROVE]` `[X-REF 10]`

*(18 leaves)*
## §1.10 Representation design — the payload

1.10.1 Always return a JSON **object** at the top level, never a bare array or a scalar. The reason
       is extensibility: an object can grow a `page` or `warnings` sibling; an array cannot. Zalando
       makes this a MUST. `[SOURCE]` `[PROVE]` `[TRAP]`
1.10.2 The envelope decision: `{"data": …, "page": …}` vs a bare resource. What each costs, and the
       rule — **collections get an envelope, single resources do not need one**, but consistency
       across every endpoint outranks the debate. `[TABLE]`
1.10.3 Field naming: one casing convention, no abbreviations, no type suffixes (`amountStr`), boolean
       fields named as positive assertions (`selfExcluded`, not `notSelfExcluded`), and no
       double-negatives. `[TRAP]`
1.10.4 Nullability as a contract: `null` vs absent vs empty-string vs empty-array vs zero. Define
       which of the five your API uses and never mix. State the JSON Merge Patch consequence — `null`
       means *delete* there, so a "null means unset" API cannot use merge-patch cleanly. `[PROVE]`
       `[TRAP]`
1.10.5 Numbers in JSON: JSON has one number type, IEEE-754 double is what JavaScript will parse it
       as, and **2^53 − 1 = 9,007,199,254,740,991** is where a 64-bit id silently loses precision in
       a browser. The fix: serialise large ids and money as strings. `[NUM]` `[PROVE]` `[TRAP]`
1.10.6 Money, done correctly: minor units as an integer (`{"amount": 2500, "currency": "GBP"}`) or a
       decimal **string** (`"25.00"`), never a float. Java side: `BigDecimal` with an explicit scale
       and `RoundingMode`, never `double`. `[X-REF 03]` `[TRAP]` `[PROVE]`
1.10.7 Dates and times: **RFC 3339 / ISO 8601 with an explicit offset**, always UTC (`Z`) on the
       wire, `date` vs `date-time` vs `duration` vs `time` as separate JSON Schema formats, and why
       local-time-without-offset is the single most common cross-timezone bug. Java side:
       `Instant`/`OffsetDateTime`, never `Date`. `[X-REF 03]` `[TRAP]`
1.10.8 Durations and intervals: ISO 8601 `PT30S`, `P7D`; when an integer-plus-unit pair is clearer;
       and Google AIP-142's rule to suffix time fields with `_time` and durations with `_duration`.
       `[RESEARCH]`
1.10.9 Enumerations as an evolution hazard: **adding an enum value is a breaking change for a
       strict client and a non-breaking change for a tolerant one**, so you must publish which you
       expect. Zalando's rule: "SHOULD use an open-ended list of values for enumeration types" and
       "MUST prepare clients to accept compatible API extensions". `[PROVE]` `[TRAP]` `[SOURCE]`
       `[RESEARCH]`
1.10.10 The `UNSPECIFIED`/`UNKNOWN` zero-value convention (protobuf AIP-126 requires the zero value
        to be `<ENUM>_UNSPECIFIED`) and why it exists: proto3 cannot distinguish absent from
        default. `[RESEARCH]` `[PROVE]`
1.10.11 Booleans vs enums: a `boolean` that will later need a third state is a breaking change
        waiting to happen (`verified: true` → `verificationStatus: PENDING|VERIFIED|FAILED`). Prefer
        an enum for anything lifecycle-shaped. `[TRAP]` `[PROVE]`
1.10.12 Identifiers in payloads: return the id, return the canonical `self` URI or full resource
        name, and never make the client construct a URL by string concatenation. `[PROVE]`
1.10.13 Embedding vs linking related resources: the three options (id only, `_embedded` object,
        `?include=` on demand) and the N+1-round-trip vs payload-bloat trade. `[TABLE]`
1.10.14 Denormalisation for the client: when duplicating a field is right (`clientName` on a
        withdrawal, for an operator list view) and the staleness contract you take on by doing it.
        `[PROVE]`
1.10.15 The QuizStakes composite-view problem (scenario § 7.3–7.4): "show me all my withdrawals"
        spans two schemas with one vocabulary. The API must present one contract over two stores —
        that is a *read model*, and the API design decision is whether the contract admits it
        (`source` discriminator? unified `status`?). `[SOURCE]` `[X-REF 15]` `[PROVE]`
1.10.16 Sensitive fields in payloads: AIP-147's guidance, masking (`**** **** **** 4242`), the
        `input-only`/`output-only` field-behaviour distinction (AIP-203), and the rule that a
        write-only field must never be echoed. `[X-REF 13]` `[RESEARCH]`
1.10.17 Payload size discipline: hard-cap response size, cap array lengths, and state what happens
        past the cap (truncate + flag, or `413`). Give the QuizStakes arithmetic — a ledger-entry row
        is ~180 bytes, so a 10,000-row page is ~1.8 MB before JSON overhead and roughly 4–6 MB after.
        `[NUM]` `[PROVE]`
1.10.18 `additionalProperties`: allowing unknown fields on the way in (Postel's law, tolerant
        reader) vs rejecting them (fail fast, catch typos). The recommendation differs for requests
        and responses, and Zalando says avoid `additionalProperties` in *event* schemas
        specifically. `[TABLE]` `[SOURCE]` `[RESEARCH]`
1.10.19 The tolerant-reader pattern stated as an obligation on the *client*: ignore unknown fields,
        tolerate new enum values, do not depend on field order, do not depend on absent-vs-null
        unless documented. Jackson: `FAIL_ON_UNKNOWN_PROPERTIES` default `true` — which makes
        Spring's default client **intolerant**, and that is a real production hazard. `[API]`
        `[TRAP]` `[NUM]`
1.10.20 Alternative encodings and when they earn their place: JSON (default), Protocol Buffers
        (schema-first, ~3–10× smaller, no self-description), Avro (schema registry, evolution rules),
        MessagePack/CBOR (binary JSON), Smile, and JSONL / `application/json-seq` for streaming.
        `[TABLE]` `[RESEARCH]`

*(20 leaves)*

## §1.11 Partial update — the PATCH formats

1.11.1 Why PATCH exists at all: PUT forces the client to know and resend the whole representation,
      which is a lost-update generator and a bandwidth cost. `[PROVE]`
1.11.2 **JSON Merge Patch (RFC 7396)**, media type `application/merge-patch+json`: a partial document
      where present members replace, **`null` members delete**, and arrays are replaced wholesale.
      The algorithm is ten lines and the bible must state it. `[SPEC]` `[SOURCE]`
1.11.3 Merge Patch's two hard limits: you cannot set a member *to* `null`, and you cannot modify one
      array element. `[PROVE]` `[TRAP]` `[RESEARCH]`
1.11.4 **JSON Patch (RFC 6902)**, media type `application/json-patch+json`: an **array of operation
      objects** — `add`, `remove`, `replace`, `move`, `copy`, `test` — applied in order, atomically
      (all-or-nothing). `[SPEC]` `[TABLE]`
1.11.5 **JSON Pointer (RFC 6901)** as the addressing language JSON Patch depends on: `/`-separated
      tokens, `~0` for `~`, `~1` for `/`, `-` as the "end of array" index, and the empty pointer
      meaning the whole document. `[SPEC]` `[TRAP]`
1.11.6 The `test` operation as an in-band optimistic-concurrency check, and why it is strictly weaker
      than `If-Match` (it guards one path, not the whole representation). `[PROVE]`
1.11.7 Atomicity: RFC 6902 requires the whole patch to apply or none of it — which means your
      implementation must apply to a copy and commit, not mutate in place. `[SPEC]` `[PROVE]`
1.11.8 The comparison table: expressiveness, readability, array support, null semantics, idempotency,
      auditability, client library availability, and "can a human read it in a log". `[TABLE]`
1.11.9 The pragmatic third option everybody actually ships: `PATCH` with `application/json` and a
      partial object, i.e. merge-patch semantics without the media type. State that it is undefined
      by spec, that it is fine if documented, and what breaks (a client cannot tell "clear this
      field" from "leave it alone"). `[TRAP]` `[PROVE]`
1.11.10 The **field-mask** alternative (Google AIP-161): send the full object plus
        `update_mask=amount,currency`, or `?updateMask=`. It solves the clear-vs-omit ambiguity
        without a patch document, and it is what gRPC APIs use because proto3 cannot express absence.
        `[RESEARCH]` `[PROVE]`
1.11.11 `PATCH` and idempotency, concretely: merge patch and `replace` are idempotent; `add` to an
        array, `move`, and any delta field are not. So a `PATCH` endpoint that accepts array
        operations **needs an idempotency key**. `[PROVE]` `[TRAP]`
1.11.12 The Spring surface: `@PatchMapping`, `JsonPatch`/`JsonMergePatch` from `jakarta.json`
        (Jakarta JSON-P) or `com.github.java-json-tools:json-patch`, and how to apply a patch to a
        JPA entity without losing dirty-checking. `[API]` `[X-REF 08]`
1.11.13 The QuizStakes decision: `PATCH /clients/{id}/self-exclusion` must be idempotent and must
        take effect inside **500 ms**, so it is modelled as a `PUT` on a state sub-resource, not a
        patch. Argue it. `[NUM]` `[PROVE]`

*(13 leaves)*

## §1.12 Content negotiation

1.12.1 Proactive (server-driven) vs reactive (agent-driven) negotiation per RFC 9110 § 12, and the
      third kind nobody names — **transparent** negotiation at a cache. `[SPEC]`
1.12.2 The four `Accept*` request fields and what each selects: `Accept` (media type), `Accept-
      Encoding` (compression), `Accept-Language` (localisation), `Accept-Charset` (deprecated —
      always UTF-8). `[TABLE]` `[SPEC]`
1.12.3 Quality values: `q=0..1` with up to three decimal places, `q=0` meaning "not acceptable", and
      the **specificity ordering** rule — `text/html` beats `text/*` beats `*/*` regardless of `q`.
      Work an example: `Accept: application/json;q=0.9, application/problem+json`. `[NUM]` `[PROVE]`
      `[SPEC]`
1.12.4 What a server returns when it cannot satisfy `Accept`: `406 Not Acceptable`, or — legitimately
      — its default representation anyway. RFC 9110 permits both; pick one and document it. `[SPEC]`
      `[TRAP]`
1.12.5 `Vary`: the cache-correctness header. If your response depends on `Accept`,
      `Accept-Language`, `Authorization` or a custom version header, `Vary` must list it or a shared
      cache will serve the wrong variant to the wrong caller. This is the mechanism behind the
      "header versioning is cache-hostile" claim. `[HDR]` `[PROVE]` `[TRAP]`
1.12.6 `Vary: *` and the cardinality problem: every value in `Vary` multiplies your cache entries,
      so `Vary: Accept, Accept-Encoding, Accept-Language, Authorization` can make the cache useless.
      `[PROVE]` `[NUM]`
1.12.7 Compression as negotiation: `gzip`, `deflate`, `br` (Brotli), `zstd`; `Content-Encoding` on
      the response; and the security caveat (BREACH/CRIME — compression plus a secret in the body
      plus attacker-controlled input). `[X-REF 13]` `[RESEARCH]`
1.12.8 Compression arithmetic worth stating: JSON typically compresses 5–10×, so the "protobuf is 10×
      smaller" claim shrinks to roughly 2–3× once both are gzipped. `[NUM]` `[TRAP]` `[PROVE]`
1.12.9 Media-type versioning as negotiation: `Accept: application/vnd.quizstakes.deposit.v2+json`,
      how it interacts with `Vary`, and why it is the "purist" option that is hard to exercise with
      a browser or a curl one-liner. `[PROVE]`
1.12.10 Format negotiation via extension or query param (`?format=csv`, `.csv`) — the pragmatic
        break, and the export use case where it is genuinely right. `[TRAP]`
1.12.11 The Spring mechanism: `ContentNegotiationConfigurer`, `ContentNegotiationStrategy`,
        `HeaderContentNegotiationStrategy`, `ParameterContentNegotiationStrategy`,
        `PathExtensionContentNegotiationStrategy` (removed in 6.0), `produces`/`consumes` on
        `@RequestMapping`, and `HttpMediaTypeNotAcceptableException` → `406`. `[API]` `[X-REF 07]`
        `[VERSION-TRAP]`
1.12.12 OpenAPI 3.2's new first-class streaming media types — `text/event-stream`,
        `application/jsonl`, `application/json-seq`, `multipart/mixed` — and what they let you
        describe that 3.1 could not. `[RESEARCH]` `[VERSION-TRAP]`

*(12 leaves)*

## §1.13 Conditional requests, ETags and optimistic concurrency

1.13.1 The two validator kinds: **strong** and **weak** (`W/"…"`), and the exact rule — a strong
      validator changes whenever the representation's octets change; a weak one changes only on
      semantically significant change. Range requests require strong validators. `[SPEC]` `[PROVE]`
1.13.2 `ETag` syntax: an opaque quoted string, `W/` prefix for weak. **It is opaque** — the client
      must never parse it, so you are free to change it from a hash to a version number. `[HDR]`
      `[SPEC]` `[TRAP]`
1.13.3 `Last-Modified` and `If-Modified-Since`: one-second granularity is the fatal limit for an API
      whose resources change more than once a second — the QuizStakes ledger at 230 writes/sec makes
      it useless. `[NUM]` `[PROVE]` `[TRAP]`
1.13.4 The five conditional request headers and their precedence order per RFC 9110 § 13.2.2:
      `If-Match`, `If-Unmodified-Since`, `If-None-Match`, `If-Modified-Since`, `If-Range`. State the
      evaluation order — it is normative and non-obvious. `[SPEC]` `[FLOW]`
1.13.5 The read path: `If-None-Match: "abc"` on a GET → `304 Not Modified` with no body. What the
      client saves (bandwidth, deserialisation) and what it does not (the round trip and your
      server's work). `[CODE]` `[PROVE]`
1.13.6 The write path: `If-Match: "abc"` on a PUT/PATCH/DELETE → `412 Precondition Failed` on
      mismatch. **This is optimistic concurrency control expressed in HTTP**, and it is the answer to
      "two operators edit the same case". `[CODE]` `[PROVE]`
1.13.7 `If-None-Match: *` on a PUT as a race-free create: succeed only if the resource does not yet
      exist, `412` if it does. `[PROVE]`
1.13.8 `If-Match: *` as "must exist". `[SPEC]`
1.13.9 `428 Precondition Required` (RFC 6585) as the server-side enforcement: refuse unconditional
      writes so a client cannot lose an update by accident. `[CODE]` `[PROVE]`
1.13.10 Where the ETag comes from, four options with costs: a hash of the serialised body (correct,
        costs you the serialisation), a row version column (cheap, must be included in every
        projection), `updated_at` with sub-second precision (cheap, granularity risk), or a
        monotonic sequence. Map it onto JPA `@Version`. `[TABLE]` `[X-REF 08]` `[PROVE]`
1.13.11 The ETag/serialisation trap: computing the ETag from the serialised body means you serialise
        before you know whether you can return `304`, so the CPU saving is zero and only bandwidth is
        saved. Spring's `ShallowEtagHeaderFilter` does exactly this and its javadoc says so.
        `[TRAP]` `[SOURCE]` `[API]`
1.13.12 Lost update, demonstrated as a two-client interleaving on a QuizStakes restriction record,
        then fixed with `If-Match` — the same argument as a database `@Version` column, moved to the
        contract. `[PROVE]` `[FLOW]` `[X-REF 09]`
1.13.13 Optimistic vs pessimistic at the API layer: `If-Match`/`412` vs an explicit lock resource
        (`POST /cases/{id}/locks` → `423 Locked`). When a 30–90 minute operator session justifies a
        real lock. `[NUM]` `[TABLE]` `[SOURCE]`
1.13.14 ETags on collections: why they are usually a bad idea (any member change invalidates), and
        the alternative — a per-item ETag plus a collection-level `Last-Modified` or a change
        cursor. `[TRAP]` `[PROVE]`
1.13.15 The Spring surface: `ResponseEntity.ok().eTag(…)`, `ServletWebRequest.checkNotModified(String
        etag)` / `checkNotModified(long lastModified)`, `ShallowEtagHeaderFilter`, and
        `@RequestHeader("If-Match")`. `[API]`
1.13.16 Range requests (RFC 9110 § 14) as the other conditional family: `Range`,
        `Accept-Ranges`, `Content-Range`, `206`, `416`, `If-Range`, and multipart/byteranges. Where
        an API actually needs them — large document download from `DocumentRequirements`, resumable
        upload. `[SPEC]` `[CODE]`

*(16 leaves)*
## §1.14 HTTP caching for APIs (RFC 9111)

1.14.1 The cache taxonomy: **private** (in the user agent, one user) vs **shared** (proxy, CDN, API
      gateway, reverse proxy, many users). Every directive below behaves differently across that
      line, and getting it wrong is how you leak one client's balance to another. `[SPEC]` `[TRAP]`
1.14.2 What makes a response storable at all per RFC 9111 § 3: the method is understood and
      cacheable, the status code is final and cacheable, `no-store` is absent, `private` is absent
      (for a shared cache), the `Authorization` rule is satisfied, and explicit freshness or a
      heuristic exists. `[SPEC]` `[FLOW]`
1.14.3 The `Authorization` special case: a shared cache **must not** store a response to a request
      with `Authorization` unless `public`, `s-maxage` or `must-revalidate` is present. This is why
      an authenticated API is uncacheable by default — and it is the correct default. `[SPEC]`
      `[PROVE]` `[TRAP]`
1.14.4 **Every response cache directive, by name:** `max-age`, `s-maxage`, `no-cache`, `no-store`,
      `private`, `public`, `must-revalidate`, `proxy-revalidate`, `no-transform`,
      `must-understand`, `immutable` (RFC 8246), `stale-while-revalidate` and `stale-if-error`
      (RFC 5861). `[TABLE]` `[SPEC]` `[RESEARCH]`
1.14.5 **Every request cache directive, by name:** `max-age`, `max-stale`, `min-fresh`, `no-cache`,
      `no-store`, `no-transform`, `only-if-cached`. `[TABLE]` `[SPEC]` `[RESEARCH]`
1.14.6 `no-cache` vs `no-store`, the most-confused pair: `no-cache` means *store it but revalidate
      before reuse*; `no-store` means *do not write it down at all*. For a bank balance you want
      `no-store`; for a product catalogue you want `no-cache`. `[TRAP]` `[PROVE]`
1.14.7 The freshness arithmetic, worked: `freshness_lifetime` = `s-maxage` (shared only) else
      `max-age` else `Expires − Date` else heuristic; `apparent_age = max(0, response_time −
      date_value)`; `corrected_age_value = age_value + response_delay`; `current_age =
      corrected_initial_age + resident_time`; `response_is_fresh = (freshness_lifetime >
      current_age)`. `[SPEC]` `[PROVE]` `[NUM]` `[RESEARCH]`
1.14.8 Heuristic freshness: with no explicit lifetime a cache **may** invent one, conventionally
      ~10% of the time since `Last-Modified`. That is why an API that sets no cache headers is not
      "uncached" — it is *unpredictably* cached. `[NUM]` `[TRAP]` `[PROVE]` `[RESEARCH]`
1.14.9 `Age` and `Date`: how to tell from a response whether it came from a cache and how old it is —
      the first thing to check when a client reports stale data. `[HDR]` `[DIAG]`
1.14.10 `Expires` vs `Cache-Control: max-age`: `Cache-Control` wins where both are present;
        `Expires` in the past (or a malformed value) means "already stale". `[SPEC]` `[TRAP]`
1.14.11 Invalidation on unsafe methods per RFC 9111 § 4.4: a cache **must** invalidate the target URI
        when it sees a non-error response to `POST`/`PUT`/`DELETE`, and also the URIs in `Location`
        and `Content-Location` **if same-origin**. This is the only automatic invalidation HTTP
        gives you, and it is exactly why an action endpoint at a different URI leaves the collection
        stale. `[SPEC]` `[PROVE]` `[TRAP]`
1.14.12 The cache key: method + effective request URI + the fields named in `Vary`. Query-parameter
        ordering, case and unknown parameters all change the key, which is why `?a=1&b=2` and
        `?b=2&a=1` are two entries. `[PROVE]` `[TRAP]`
1.14.13 `stale-while-revalidate` and `stale-if-error` (RFC 5861) as availability tools: serve stale
        while refreshing in the background, and serve stale rather than propagate a 5xx. The
        stampede connection. `[X-REF 15]` `[RESEARCH]`
1.14.14 `Cache-Control: immutable` (RFC 8246) and where it belongs — versioned static assets, never
        an API resource. `[RESEARCH]`
1.14.15 The honest position for a JSON API: most authenticated API responses should be
        `Cache-Control: no-store` (or `private, no-cache`) plus an `ETag` for conditional GETs, and
        the caching you actually get comes from your own cache layer, not HTTP. Say why, then name
        the exceptions — reference data (`/currencies`, `/restriction-catalog`), public
        configuration, and CDN-fronted read models. `[PROVE]` `[X-REF 15]`
1.14.16 The QuizStakes application: the restriction *catalog* is `public, max-age=300` reference
        data; a restriction *decision* is `no-store` because it feeds a 30 ms gate and a wrong cached
        answer is a regulatory incident; the self-exclusion check is `no-store` with a hard 500 ms
        budget. `[NUM]` `[PROVE]` `[SOURCE]`
1.14.17 `POST` responses as cacheable: legal per RFC 9110 when explicit freshness is present, almost
        never implemented, and superseded in intent by `QUERY`. `[TRAP]` `[SPEC]`
1.14.18 Cache-related response headers you will see from a CDN and must be able to read:
        `X-Cache: HIT/MISS`, `CF-Cache-Status`, `X-Served-By`, `Surrogate-Control`, `Surrogate-Key`.
        `[DIAG]` `[X-REF 18]`

*(18 leaves)*

## §1.15 Collections — pagination, filtering, sorting, projection

1.15.1 Why pagination is mandatory and not an optimisation: an unbounded collection endpoint is a
      denial-of-service primitive against your own database, your own heap and your own network.
      With 19.8M ledger entries/day, `GET /ledger-entries` without a limit is an outage. `[NUM]`
      `[PROVE]`
1.15.2 **Offset pagination:** `?page=3&size=20` or `?offset=60&limit=20`. What it buys — random
      access to page N, a total count, trivially understood by users. `[PROVE]`
1.15.3 Offset's two defects, both stated mechanically: **cost grows with depth** (the database must
      count and discard `offset` rows, so page 10,000 is O(offset)) and **results shift** when rows
      are inserted or deleted under the reader, causing duplicates and skips. `[PROVE]` `[X-REF 09]`
      `[TRAP]`
1.15.4 **Keyset / cursor pagination:** `WHERE (created_at, id) < (:lastTs, :lastId) ORDER BY
      created_at DESC, id DESC LIMIT 20`. Constant time regardless of depth, stable under concurrent
      writes, no total. `[PROVE]` `[X-REF 09]`
1.15.5 Why the cursor must be **opaque**: base64 of the sort-key tuple means you can change the
      underlying scheme, add a tiebreaker, or switch stores without breaking a client that stored a
      cursor. A cursor that looks like `?after=42` is a contract you did not mean to sign. `[PROVE]`
      `[TRAP]`
1.15.6 What goes *inside* the cursor: the sort-key tuple, the sort direction, a schema version, the
      filter fingerprint (so a client cannot page with a cursor from a different filter), and
      optionally an expiry. Whether to sign or encrypt it, and why HMAC is usually enough.
      `[PROVE]` `[X-REF 13]`
1.15.7 The **deterministic total ordering** requirement: every pagination scheme needs a tiebreaker
      column, because a non-unique sort key produces duplicates and gaps even in keyset pagination.
      `ORDER BY created_at DESC` alone is a bug; `ORDER BY created_at DESC, id DESC` is not.
      `[PROVE]` `[TRAP]`
1.15.8 **Seek/`search_after` pagination** as the Elasticsearch spelling of keyset, and
      **point-in-time / snapshot pagination** (`scroll`, PIT id) as the third family — a consistent
      view at a fixed instant, at the cost of server-side state and a TTL. `[TABLE]` `[RESEARCH]`
1.15.9 **Time-window pagination** (`?from=…&to=…`) as the right answer for append-only feeds, and
      the QuizStakes ledger's 90-day hot window as the natural boundary. `[NUM]` `[SOURCE]`
1.15.10 Totals: exact counts are expensive (a full scan or an index-only count on a filtered
        predicate), estimates are cheap (`reltuples`, `EXPLAIN` row estimate), and Zalando says
        **"SHOULD avoid a total result count"**. If you return one, document whether it is exact,
        capped (`"1000+"`), or estimated. `[SOURCE]` `[X-REF 09]` `[RESEARCH]`
1.15.11 The response envelope, fixed across every collection endpoint. Compare the four published
        shapes: bare `{data, page:{next_cursor, has_more, limit}}`, JSON:API `{data, links:{self,
        next, prev}, meta}`, HAL `{_embedded, _links:{next}}`, and `Link:
        <…>; rel="next"` headers (GitHub's style). Pick one; justify. `[TABLE]` `[SOURCE]`
1.15.12 **Enforce a server-side maximum limit.** `limit=100000` is a DoS; clamp silently or reject
        with `400`. State the default and the max explicitly (e.g. default 20, max 200) and put them
        in the OpenAPI schema. `[NUM]` `[TRAP]` `[PROVE]`
1.15.13 Empty and terminal pages: `200` with an empty array (never `404`), and how the client knows
        it is done — `has_more: false`, an absent `next` link, or a short page. Prefer the explicit
        flag, because a full final page is indistinguishable otherwise. `[TRAP]` `[PROVE]`
1.15.14 Bidirectional cursors: `prev_cursor` and why it is genuinely harder (you must reverse the
        comparison and the ordering, then reverse the result set). `[PROVE]`
1.15.15 Google AIP-158 pagination: `page_size`, `page_token`, `next_page_token`, the rule that the
        server may return **fewer** results than `page_size` and the client must not treat that as
        the end, and `skip` as the offset escape hatch. `[SOURCE]` `[RESEARCH]`
1.15.16 **Filtering:** the four levels of ambition — fixed named parameters (`?status=CAPTURED`),
        bracketed operators (`?amount[gte]=1000`), a query DSL in a string (RSQL/FIQL:
        `?filter=amount=gt=1000;status==CAPTURED`, OData `$filter`, AIP-160's filter grammar,
        SCIM's filter), and a structured body via `POST /search` or `QUERY`. `[TABLE]` `[RESEARCH]`
1.15.17 The filtering trap: an expressive filter DSL is an unbounded query surface — it becomes an
        injection risk, an index-planning nightmare and an accidental analytics engine. Constrain
        the allowed fields and operators explicitly. `[TRAP]` `[X-REF 09]` `[X-REF 13]`
1.15.18 Multi-value and repeated parameters: `?status=A&status=B` vs `?status=A,B` vs
        `?status[]=A`. Pick one; note that they parse differently in every framework, and that
        Spring binds both `List<String>` forms. `[TRAP]` `[API]`
1.15.19 **Sorting:** `?sort=-createdAt,amount` (the `-` prefix convention) vs `?sort=createdAt&
        order=desc` vs OData `$orderby`. Whitelist sortable fields, because "sort by any column"
        means "full table sort on an unindexed column". `[TRAP]` `[X-REF 09]`
1.15.20 **Sparse fieldsets / projection:** `?fields=id,status,amount`, JSON:API's
        `?fields[deposits]=…` per-type form, AIP-157 partial responses via a read mask, and GraphQL
        as the fully general case. What it saves (payload, serialisation) and what it costs (cache
        fragmentation — every field combination is a new cache key, and `Vary` cannot express it).
        `[TABLE]` `[PROVE]` `[RESEARCH]`
1.15.21 **Expansion / inclusion:** `?include=client,instrument`, JSON:API compound documents with the
        **full-linkage** requirement (every included resource must be reachable via a relationship
        chain from primary data), and the depth/fan-out limit you must impose. `[SOURCE]`
        `[RESEARCH]`
1.15.22 The QuizStakes pagination decisions, argued: the client-facing withdrawal list is **cursor**
        (a feed, mutating under the reader, spans two schemas so offsets are meaningless across the
        union); the operator `PaymentRun` item list is **offset** (a bounded batch where operators
        expect page numbers and a total); the ledger entry export is **time-window + cursor** (7-year
        retention, 90-day hot window). `[NUM]` `[PROVE]` `[SOURCE]`

*(22 leaves)*

## §1.16 The error contract (RFC 9457)

1.16.1 Why a standard error format exists: without one, every API invents a different envelope and
      every client writes bespoke parsing, so a generic client, gateway or SDK cannot behave
      sensibly. `[PROVE]`
1.16.2 The media type: `application/problem+json` (and `application/problem+xml`). RFC **9457**,
      July 2023, **obsoletes RFC 7807**; the wire format is unchanged for typical JSON usage.
      `[SPEC]` `[VERSION-TRAP]` `[RESEARCH]`
1.16.3 The five standard members, each with its exact semantics: **`type`** (a URI reference
      identifying the problem type — the *stable machine-readable* identifier, default
      `about:blank`), **`title`** (short human-readable summary, **stable per `type`**),
      **`status`** (the HTTP status code, duplicated for convenience), **`detail`** (human-readable
      explanation of *this occurrence*, and explicitly **not** for programmatic consumption), and
      **`instance`** (a URI reference identifying this specific occurrence). `[TABLE]` `[SPEC]`
      `[SOURCE]`
1.16.4 The `type` URI rules: it need not be dereferenceable, RFC 9457 § 3.1.1 gives guidance for
      non-dereferenceable URIs, and using a `tag:` URI or a stable `https://` documentation URL are
      both fine. What is *not* fine is changing it. `[SPEC]` `[PROVE]` `[RESEARCH]`
1.16.5 `about:blank` as the "no additional semantics" sentinel, registered in the problem-types
      registry with the title "See HTTP Status Code". `[SOURCE]` `[RESEARCH]`
1.16.6 **Extension members**: any additional top-level field. RFC 9457's guidance on naming them,
      and the two you will always add — a per-field validation array and a correlation id.
      `[SPEC]`
1.16.7 **Multiple problems** (RFC 9457 § 3): the spec clarifies that a single problem detail should
      describe the primary problem, and multiple errors go in an extension array. So
      `{"errors":[{"field":"amount","code":"EXCEEDS_BALANCE"}]}` is the sanctioned shape.
      `[SPEC]` `[RESEARCH]`
1.16.8 Return **all** validation failures at once, not the first. The reason is round trips: a
      six-field form with fail-fast validation is six rejected submissions. `[PROVE]` `[TRAP]`
1.16.9 The **stable machine-readable code** rule: clients must branch on `type` (or a `code`
      extension), never on `detail`, never on `title`, never on a substring of a message. Say what
      breaks when they do — you cannot fix a typo in an error message without breaking a client.
      `[PROVE]` `[TRAP]`
1.16.10 The **correlation id** rule: every error response carries a trace id, and the same value is
        in your server log. A user pastes it into a support ticket and you find the request. This is
        the single highest-value operational field in the whole contract. `[PROVE]`
        `[X-REF 20]`
1.16.11 **Never leak**: stack traces, SQL text, internal hostnames, container ids, library versions,
        upstream vendor error text, or the existence of a resource the caller may not see. Each one
        named with what an attacker does with it. `[TRAP]` `[X-REF 13]`
1.16.12 Retryability signalling: whether the error is retryable, and how — `Retry-After` on `429`/
        `503`, a `retryable: true` extension, or a documented per-`type` policy. Google's rich error
        model has `google.rpc.RetryInfo` for exactly this. `[PROVE]` `[RESEARCH]`
1.16.13 Localisation: `title`/`detail` in the caller's language via `Accept-Language`, with `type`
        and `code` invariant. `google.rpc.LocalizedMessage` as the RPC equivalent. `[RESEARCH]`
1.16.14 The problem-type catalogue as a published artifact: a documented registry of your own
        `type` URIs with the status, title and remediation for each. This is what makes the error
        contract testable. `[PROVE]`
1.16.15 The IANA registry as prior art, and the rate-limit draft's three registered types with their
        recommended statuses: `#quota-exceeded` (429, with a `violated-policies` array),
        `#temporary-reduced-capacity` (503), `#abnormal-usage-detected` (429). `[SOURCE]`
        `[RESEARCH]`
1.16.16 The Spring surface, exactly: `ProblemDetail` (with `forStatus`, `forStatusAndDetail`,
        `setType`, `setTitle`, `setDetail`, `setInstance`, `setProperty`), the `ErrorResponse`
        interface, `ErrorResponseException`, `ResponseEntityExceptionHandler` as the base class for
        an `@ControllerAdvice`, and the Boot property **`spring.mvc.problemdetails.enabled`**
        (default `false`) which auto-registers a handler at **order 0** — so your own advice must be
        ordered ahead of it. `[API]` `[NUM]` `[RESEARCH]`
1.16.17 `@ExceptionHandler` / `@RestControllerAdvice` mechanics and ordering, `@ResponseStatus` on a
        custom exception, and Boot's `ErrorAttributes` / `/error` fallback with
        `server.error.include-stacktrace` (default `never`) and `include-message` (default `never`).
        `[API]` `[NUM]` `[X-REF 07]`
1.16.18 Bean Validation integration: `MethodArgumentNotValidException`,
        `HandlerMethodValidationException` (6.1+), `ConstraintViolationException`, and mapping
        `BindingResult.getFieldErrors()` into the `errors` extension array. The trap: `@Valid` on a
        `@RequestBody` produces a 400 while `@Validated` on a service parameter produces a 500 unless
        you handle it. `[API]` `[TRAP]` `[X-REF 07]`
1.16.19 The QuizStakes problem catalogue the bible must write out: `…/problems/client-restricted`
        (403, from `DEP-190`), `…/problems/deposit-limit-exceeded` (422, `DEP-199`, with
        `limitAmount`/`attemptedAmount`/`windowEnd` extensions), `…/problems/insufficient-funds`
        (422, with `available`/`required`), `…/problems/idempotency-key-reuse` (422),
        `…/problems/concurrent-request` (409), `…/problems/instrument-unverified` (409),
        `…/problems/quota-exceeded` (429), `…/problems/psp-unavailable` (502).
        `[TABLE]` `[SOURCE]`
1.16.20 The gRPC and GraphQL equivalents, so the concept transfers: `google.rpc.Status` with
        `code`/`message`/`details` and the standard detail types (`ErrorInfo`, `BadRequest` with
        `FieldViolation`, `QuotaFailure`, `PreconditionFailure`, `ResourceInfo`, `RequestInfo`,
        `Help`, `DebugInfo`, `RetryInfo`); GraphQL's top-level `errors` array with `message`,
        `locations`, `path` and `extensions`. `[TABLE]` `[RESEARCH]`

*(20 leaves)*
## §1.17 Idempotency keys, end to end

1.17.1 The problem restated precisely: a client cannot distinguish "the request never arrived",
      "the request arrived and failed", and "the request arrived, succeeded, and the response was
      lost". Only the third is dangerous, and it is indistinguishable from the first two. `[PROVE]`
1.17.2 The contract: the **client** generates a unique key per *logical operation*, sends it on
      every attempt of that operation, and generates a **new** key for a genuinely new operation.
      The server promises at-most-once effect per key. `[FLOW]`
1.17.3 The header: `Idempotency-Key`, a Structured Field **Item of type String** —
      `Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"`. UUIDv4 (RFC 9562) or equivalent
      random identifier is the recommended value. `[HDR]` `[SPEC]` `[RESEARCH]`
1.17.4 The **scope** of a key, which the draft leaves to the resource owner and which you must pin
      down: per authenticated caller **and** per endpoint at minimum. A composite lookup key
      combining the client-supplied key with server-side attributes is the draft's explicit security
      recommendation, because a low-entropy key from one tenant must not collide with another's.
      `[PROVE]` `[TRAP]` `[RESEARCH]`
1.17.5 The **fingerprint** (request hash): a checksum over the payload, or over selected fields, or a
      request digest/signature. Its job is to detect key reuse with a *different* body. `[SPEC]`
      `[RESEARCH]`
1.17.6 The three specified error responses, verbatim from the draft: missing key where required →
      **`400`**; key reused with a different payload → **`422 Unprocessable Content`**; a concurrent
      request with the same key still in flight → **`409 Conflict`**. All three should be
      `application/problem+json` with a `type` pointing at your idempotency documentation.
      `[CODE]` `[SPEC]` `[RESEARCH]`
1.17.7 The storage schema, with every column justified: `key` (primary key), `caller_id`, `endpoint`,
      `request_hash`, `status` (`IN_PROGRESS` | `COMPLETED`), `response_code`, `response_headers`,
      `response_body`, `created_at`, `expires_at`. `[BUILD]` `[X-REF 09]`
1.17.8 **The flow, and why the order is not negotiable:**
       (1) `INSERT` the key with `IN_PROGRESS` — the **primary-key constraint** is what makes this
       race-free, so you must **not** `SELECT` first;
       (2) insert succeeded → first attempt: do the work and write the response **in the same
       transaction** as the transition to `COMPLETED`;
       (3) insert failed on duplicate key → read the row: `COMPLETED` → **replay** the stored status,
       headers and body verbatim; `IN_PROGRESS` → `409`;
       (4) `request_hash` mismatch → `422`;
       (5) expire keys after 24 h–7 days via a TTL job.
       `[FLOW]` `[PROVE]`
1.17.9 **Why check-then-insert is broken**, proved as a two-thread interleaving: both threads
      `SELECT` and find nothing, both proceed, and the client is charged twice. The unique
      constraint is the only serialisation point you can trust. `[PROVE]` `[X-REF 05]` `[X-REF 09]`
1.17.10 **Why the work and the record must share one transaction**, proved: any ordering that
        commits the side effect outside the key's transaction admits a crash window in which the
        effect happened and the record did not — which is exactly the double-charge you were
        preventing. Where the side effect is *external* (a PSP capture) this is impossible, so name
        the two available tools: pass your key through to the provider, and reconcile. `[PROVE]`
        `[TRAP]`
1.17.11 The response-replay question: replay the **exact** stored response, including status code and
        `Location`. What about headers that must not be replayed (`Date`, `traceparent`, a fresh
        `RateLimit`)? State the rule. `[PROVE]` `[TRAP]`
1.17.12 `IN_PROGRESS` handling alternatives, compared: `409` immediately (simple, pushes the retry
        to the client), block-and-wait with a timeout (nicer client experience, holds a connection
        and a thread), or `202` + a status URL (most correct, most work). `[TABLE]`
1.17.13 Retention and expiry: 24 hours (Stripe) to 7 days, why the window must exceed your longest
        client retry schedule, and what happens when a key is reused *after* expiry. `[NUM]`
        `[TRAP]` `[RESEARCH]`
1.17.14 Storage choice: the transactional database (correct, shares the transaction, costs write
        throughput) vs Redis (fast, but a separate failure domain and you cannot share a transaction
        with it — so it can only ever be a cache in front of the real record). `[TABLE]` `[PROVE]`
        `[X-REF 15]`
1.17.15 **Defence in depth: where the *true* idempotency lives.** A unique constraint on the natural
        business key (`payment_reference`, `order_number`), the PSP's own idempotency key, and the
        ledger's position-version column are each independent guards. The HTTP key is the outermost
        and weakest layer. `[PROVE]` `[X-REF 09]`
1.17.16 Idempotency vs deduplication vs exactly-once, and the honest statement: HTTP gives you
        at-least-once delivery plus at-most-once *effect*, which composes to exactly-once *effect* —
        never exactly-once *delivery*. `[PROVE]` `[X-REF 14]`
1.17.17 The client's obligations, which are half the contract and are always omitted: persist the key
        with the pending operation before sending, reuse it across process restarts, use exponential
        backoff with jitter, cap attempts, and treat `409` as "wait and retry", not "fail".
        `[FLOW]` `[TRAP]`
1.17.18 Where a key is **not** needed and adding one is noise: `GET`, `PUT` on a client-chosen URI,
        `DELETE`, and any endpoint whose effect is already keyed by a natural unique constraint.
        `[TRAP]`
1.17.19 The QuizStakes application, end to end: `POST /deposits` with `Idempotency-Key` covering the
        `DEP-000 → DEP-301` span; the key **passed through** to the PSP on capture so `DEP-390 →
        DEP-300` retry ("retry with same key" is in the state machine); the stake-reservation
        endpoint at 1,200/sec with a 150 ms budget, where the idempotency lookup itself is on the
        critical path; and the ledger's own `position` version column as the innermost guard.
        `[NUM]` `[SOURCE]` `[PROVE]`
1.17.20 Stripe's published behaviour as the reference implementation to compare against: keys valid
        24 h, up to 255 characters, `Idempotency-Key` header, replayed responses flagged with
        `Idempotent-Replayed`/`Stripe-Should-Retry`, and a distinct error for reuse with different
        parameters. `[RESEARCH]`

*(20 leaves)*

## §1.18 Versioning and backward compatibility

1.18.1 The definition that settles most arguments: a change is **breaking** if a correct existing
      client stops working. Everything else is a judgement call about *how correct* your clients
      actually are. `[PROVE]`
1.18.2 The exhaustive **non-breaking** list: adding a new endpoint, adding an **optional** request
      field, adding a response field, adding a new enum value *if* clients were told to tolerate
      them, adding a new optional header, adding a new error `type`, relaxing a validation
      constraint, adding a new 4xx status in an existing class. `[TABLE]` `[PROVE]`
1.18.3 The exhaustive **breaking** list: removing or renaming a field, changing a field's type,
      changing a field's cardinality (scalar → array), making an optional request field required,
      **tightening** validation, removing an enum value, changing the meaning of an existing status
      code, changing default behaviour, changing the ordering guarantee, changing pagination
      semantics, changing an error `type` URI, removing an endpoint, changing authentication
      requirements. `[TABLE]` `[PROVE]`
1.18.4 The five sneaky breaking changes people ship by accident: tightening a regex, adding a
      required field with a default *on the server* only, changing a nullable field to non-nullable
      in the schema, reordering an array whose order was undocumented but relied upon, and changing
      a numeric field's precision. `[TRAP]` `[PROVE]`
1.18.5 **The better move is to avoid versioning.** Additive evolution plus a documented tolerant-
      reader obligation removes most of the need. Zalando states it as a rule: "**SHOULD avoid
      versioning**". `[SOURCE]` `[PROVE]` `[RESEARCH]`
1.18.6 **URI path versioning** (`/v1/deposits`): most visible, trivially routable at a gateway or
      load balancer, cacheable without `Vary`, testable with a browser. Cost: the version leaks into
      every link and every resource identity, so `/v1/deposits/778` and `/v2/deposits/778` look like
      two resources. `[TABLE]` `[PROVE]`
1.18.7 **Media-type versioning** (`Accept: application/vnd.quizstakes.deposit.v2+json`): purist,
      keeps one URI per resource, cache-correct **only if you set `Vary: Accept`**. Cost: hard to
      exercise by hand, and many intermediaries mangle `Accept`. Zalando mandates it and forbids URL
      versioning — an unusual position worth knowing about. `[SOURCE]` `[RESEARCH]`
1.18.8 **Custom header versioning** (`X-API-Version: 2`, `Stripe-Version: 2024-06-20`,
      `GitHub: X-GitHub-Api-Version: 2022-11-28`): the pragmatic middle. Needs `Vary`. `[RESEARCH]`
1.18.9 **Query-parameter versioning** (`?version=2`): easy, messy, pollutes cache keys and links.
1.18.10 **Date-based versioning (Stripe's scheme)**, in detail because it is the most-copied
        advanced answer: versions are dates with a release name (`2026-06-24.dahlia`), an **account
        is pinned** to the version current when it was created and the pin never moves unless the
        owner upgrades, a request may override with `Stripe-Version`, monthly releases are
        backward-compatible and named after the last major, and the server implements *version
        transformation layers* so the core is modern while old shapes are reconstructed on the way
        out. `[TABLE]` `[PROVE]` `[RESEARCH]`
1.18.11 The comparison table across all five schemes: discoverability, cacheability, routability,
        link stability, testability by hand, implementation cost, and how many versions you end up
        running. `[TABLE]`
1.18.12 **Versioning granularity:** whole API vs per-endpoint vs per-representation vs per-field
        (`amountV2`). What each does to your combinatorics — and why per-field versioning is a
        confession that you have no compatibility process. `[TABLE]` `[TRAP]`
1.18.13 Semantic versioning applied to an API: what MAJOR/MINOR/PATCH mean when the artifact is a
        contract rather than a library, and why only the MAJOR digit ever appears in a URI.
        `[PROVE]`
1.18.14 The number of live versions as a cost function: every version is a test matrix row, a
        migration surface, and a code path that can rot. Two is manageable, three is a smell, five
        is a project. `[PROVE]`
1.18.15 Implementation strategies for running two versions, compared: separate controllers, a
        version-transformation pipeline (Stripe), separate deployments behind gateway routing,
        request/response adapters, and expand-then-contract on the storage layer. `[TABLE]`
1.18.16 **The expand/contract (parallel change) migration**, as a named three-phase recipe: expand
        (add the new field, write both, read old), migrate (backfill, switch reads), contract (stop
        writing the old field, then remove it after the sunset). This is how you avoid a version
        bump entirely. `[FLOW]` `[PROVE]`
1.18.17 Compatibility of *events* is a separate and harder problem, because you cannot negotiate with
        a consumer that is offline. Zalando's event rules — semantic versioning of event schemas, a
        declared compatibility mode, `additionalProperties` avoided — and the schema-registry
        answer. `[SOURCE]` `[X-REF 14]` `[RESEARCH]`
1.18.18 **Spring Framework 7 / Boot 4 first-class versioning**, with every identifier: `version` on
        `@RequestMapping`/`@GetMapping`/`@PostMapping`/…, accepting no value (matches any), a fixed
        value (`"1.2"`), or a **baseline** value (`"1.2+"`, matches that and above);
        `ApiVersionConfigurer` with `useRequestHeader(String)`, `usePathSegment(int)`,
        `usePathSegment(int, Predicate<RequestPath>)`, `useQueryParam(String)`,
        `useMediaTypeParameter(String)`, `addSupportedVersions(String...)`,
        `setVersionRequired(boolean)` (default `true`), `setDefaultVersion(String)`,
        `detectSupportedVersions(boolean)` (default `true`), `deprecateVersion(String, Instant,
        String)`; the strategy SPI `ApiVersionStrategy` / `ApiVersionResolver` / `ApiVersionParser`
        (default `SemanticApiVersionParser`, `major[.minor[.patch]]` with minor and patch defaulting
        to 0) / `ApiVersionDeprecationHandler` (default `StandardApiVersionDeprecationHandler`, which
        emits RFC 9745 `Deprecation`, RFC 8594 `Sunset` and `Link`); and the exceptions
        `MissingApiVersionException` → **400**, `InvalidApiVersionException` → **400**,
        `NotAcceptableApiVersionException` → **406**. Client-side support in `RestClient`,
        `WebClient`, HTTP interfaces, `MockMvc` and `WebTestClient`. `[API]` `[NUM]`
        `[VERSION-TRAP]` `[RESEARCH]`
1.18.19 What you did **before** Spring 7, so you can answer the question at the 6.2 baseline: a
        custom `RequestCondition` / `RequestMappingHandlerMapping` subclass, `produces` with a
        vendor media type, `headers = "X-API-Version=2"` on the mapping, or gateway-level routing.
        `[API]` `[VERSION-TRAP]`
1.18.20 The QuizStakes versioning decision, argued: `ApplicationGateway`'s public client API uses
        **URI path versioning** because mobile clients cannot be recompiled and gateway routing is
        the cheapest lever; internal service-to-service contracts behind `RouterInt` use **no
        version at all** and rely on protobuf/OpenAPI compatibility checks in CI because both sides
        deploy together; webhook payloads to PSPs use **payload-embedded `schemaVersion`** because
        the consumer is another company. `[PROVE]` `[SOURCE]`

*(20 leaves)*

## §1.19 Deprecation and sunset

1.19.1 The lifecycle states an endpoint passes through: experimental/beta → stable → deprecated →
      sunset → gone. Name each and say what changes at each boundary. `[TABLE]`
1.19.2 Stability levels as a published contract (AIP-181): `alpha`, `beta`, `stable`,
      `deprecated`, and what each promises about breaking changes. `[RESEARCH]`
1.19.3 **`Deprecation` (RFC 9745)**: a Structured Field Date item — `Deprecation: @1688169599`. It
      is a **hint**, not a guarantee. It may be set to a future date (announcing) or a past date
      (already deprecated). `[HDR]` `[SPEC]` `[VERSION-TRAP]` `[RESEARCH]`
1.19.4 **`Sunset` (RFC 8594)**: an HTTP-date after which the resource is expected to become
      unresponsive. **`Sunset` MUST NOT be earlier than `Deprecation`.** `[HDR]` `[SPEC]`
      `[RESEARCH]`
1.19.5 The `deprecation` link relation and its siblings: `Link: <https://…/deprecation>;
      rel="deprecation"; type="text/html"`, plus `successor-version`, `latest-version` and
      `alternate` for pointing at the replacement. `[HDR]` `[SPEC]`
1.19.6 **Trap:** `Deprecation: true` does not parse as a Structured Field Date. It is the pre-RFC
      draft spelling and is what the current guide `src/topics/12-api-design.md` § 7 teaches. Fix it,
      and say why the boolean form is still everywhere. `[TRAP]` `[VERSION-TRAP]`
1.19.7 The `deprecated: true` flag in OpenAPI, on operations, parameters, schemas and (in 3.2)
      security schemes — the *documentation* half of the signal. `[RESEARCH]`
1.19.8 The seven-step deprecation process, which is the answer an interviewer wants: (1) decide and
      write down the replacement; (2) reflect it in the OpenAPI spec and the docs; (3) emit
      `Deprecation` + `Sunset` + `Link`; (4) **instrument per-client usage of the deprecated
      surface**; (5) contact the identified callers directly; (6) obtain consent or escalate for the
      ones that matter; (7) remove, and return `410 Gone` — not `404`. `[FLOW]`
      `[PROVE]`
1.19.9 **Never remove on a calendar alone.** You need traffic data keyed by *caller*, not just an
      aggregate request count. Zalando makes four of these MUSTs: obtain approval of clients before
      shutdown, collect external-partner consent on the time span, monitor usage of a deprecated API
      scheduled for sunset, and not start using deprecated APIs. `[SOURCE]` `[TRAP]` `[RESEARCH]`
1.19.10 The client side, which Zalando also makes a rule: **add monitoring for `Deprecation` and
        `Sunset` headers** in your own outbound clients, so you learn about someone else's sunset
        from a metric rather than from an incident. `[SOURCE]` `[PROVE]` `[RESEARCH]`
1.19.11 Brownout / progressive shutdown as a technique: return `503` for a rising percentage of
        requests on a schedule before the hard removal, so the remaining callers notice while it is
        still reversible. `[PROVE]`
1.19.12 Sunset windows in practice: 90 days for internal, 6–12 months for public, multi-year for
        regulated integrations, and "never" for anything a bank has hard-coded. `[NUM]`
1.19.13 The QuizStakes case: retiring the v1 withdrawal endpoint when the two-schema union is
        replaced by a read model — who the callers are (mobile app versions still in the wild, an
        operator tool, a partner), what the per-caller instrumentation looks like, and what `410`
        breaks. `[PROVE]` `[SOURCE]`

*(13 leaves)*
## §1.20 Rate limiting, quotas and throttling

1.20.1 The three distinct things people call "rate limiting", separated: **rate limiting** (requests
      per unit time per caller — fairness), **quota** (a budget over a long window — commercial),
      and **load shedding / admission control** (protecting the server regardless of who is calling
      — survival). Different codes, different keys, different owners. `[TABLE]` `[PROVE]`
      `[X-REF 22]`
1.20.2 **Token bucket**, stated exactly: capacity `B`, refill rate `r` tokens/second, each request
      consumes one token, empty bucket → reject. It permits a burst of `B` while bounding the
      sustained rate at `r`. `[PROVE]` `[NUM]`
1.20.3 **Leaky bucket** (as a queue): smooths output to a constant rate, no burst allowance, adds
      latency. The dual of token bucket. `[PROVE]`
1.20.4 **Fixed window counter**: trivially cheap, and admits **2× the limit at the window boundary**
      — prove it with a worked example (100/min limit, 100 requests at 00:59 and 100 at 01:00).
      `[PROVE]` `[NUM]` `[TRAP]`
1.20.5 **Sliding window log**: exact, memory O(requests in window) per key — do the arithmetic at
      1,200 req/sec. `[PROVE]` `[NUM]`
1.20.6 **Sliding window counter** (the weighted-two-window approximation): near-exact, O(1) memory,
      the usual production choice. State the interpolation formula. `[PROVE]`
1.20.7 **GCRA / virtual scheduling** as the fifth algorithm, and why Redis rate limiters
      (`redis-cell`) use it: token-bucket behaviour with a single stored timestamp. `[RESEARCH]`
1.20.8 The algorithm comparison table: burst tolerance, accuracy, memory per key, boundary
      behaviour, distributed cost. `[TABLE]`
1.20.9 **The key choice**, deliberately: API key or user id for fairness, IP for anonymous
      endpoints (**and NAT means one IP is many users** — a school, a corporate egress, a mobile
      carrier), tenant id for multi-tenant fairness, endpoint+key for expensive operations, and
      **both IP and account for login endpoints** (credential stuffing spreads across accounts from
      one IP and across IPs against one account). `[TABLE]` `[PROVE]` `[X-REF 13]`
1.20.10 Layered limits: a per-second burst limit, a per-minute sustained limit and a per-day quota
        simultaneously — which is exactly what `RateLimit-Policy`'s List syntax exists to express.
        `[PROVE]` `[HDR]`
1.20.11 The response contract: `429` + `Retry-After` + `RateLimit` + `RateLimit-Policy`, and the
        problem type `#quota-exceeded` with a `violated-policies` array so the client knows *which*
        limit it hit. `[CODE]` `[HDR]` `[RESEARCH]`
1.20.12 `Retry-After` takes precedence: the draft says explicitly that where both `Retry-After` and
        `RateLimit` are present, **`Retry-After` MUST take precedence** and the effective window may
        be ignored — and the server must not set `Retry-After` earlier than the window end.
        `[SPEC]` `[TRAP]` `[RESEARCH]`
1.20.13 Whether to send limit headers on **successful** responses: it lets a well-behaved client
        self-throttle, and it leaks your capacity to an attacker. State the trade and the usual
        answer (send them to authenticated callers, omit for anonymous). `[PROVE]`
1.20.14 **The distributed problem**: with N instances and a per-instance counter, the real limit is
        `N × limit`, and it changes every time you autoscale. With three `FundsLedger` instances a
        "1,000/min" limit is actually 3,000/min, and four instances makes it 4,000. `[PROVE]`
        `[NUM]`
1.20.15 The three answers, with costs: **shared store** (Redis `INCR`+`EXPIRE`, or a Lua token-bucket
        script for atomicity — correct, adds a network hop to every request and a hard dependency);
        **at the edge** (API gateway or CDN, before your service — usually the right place);
        **local approximation** (`limit/N` per instance — cheap, wrong during scaling, and wrong
        under uneven load balancing). `[TABLE]` `[X-REF 15]` `[X-REF 18]`
1.20.16 **Fail-open vs fail-closed** when the limiter's store is unavailable: fail-open for
        convenience features (availability wins), fail-closed for abuse protection and anything
        financial (correctness wins). Name the QuizStakes split — restriction checks fail **closed**,
        catalogue reads fail **open**. `[PROVE]` `[SOURCE]`
1.20.17 The latency budget objection: a Redis round trip is ~0.5–2 ms, which is 2–7% of the 30 ms
        restriction-decision budget and non-trivial at 1,200 stake reservations/sec. The mitigation
        is a local token bucket that syncs periodically, and the accuracy you give up. `[NUM]`
        `[PROVE]`
1.20.18 Concurrency limits as a different primitive: `concurrent-requests` is a registered quota unit
        in the draft, and a semaphore/bulkhead bounding in-flight work is often more protective than
        a rate limit. Spring Framework 7's `@ConcurrencyLimit`. `[RESEARCH]` `[X-REF 05]`
        `[VERSION-TRAP]`
1.20.19 Adaptive and priority-aware shedding: shed low-priority traffic first, use a criticality
        header, and prefer shedding to queueing (queueing converts a throughput problem into a
        latency problem and then into a timeout storm). `[PROVE]` `[X-REF 22]`
1.20.20 Where to enforce, ranked: CDN/WAF → API gateway → service filter → business-logic guard.
        Each layer catches what the previous cannot see, and the innermost one is the only one that
        knows about money. `[TABLE]`
1.20.21 Client-side obligations: honour `Retry-After`, exponential backoff **with jitter**, a
        circuit breaker, and never a tight retry loop on `429`. `[PROVE]` `[TRAP]`

*(21 leaves)*

## §1.21 Non-CRUD actions, async operations and bulk

1.21.1 The problem: not every operation is a create/read/update/delete on a row. Capture a payment,
      approve an application, retry a run, cancel a reservation, self-exclude. `[PROVE]`
1.21.2 The four modelling options **in order of preference**, each with a QuizStakes example:
      (1) make the action a **resource** — `POST /deposits/778/captures`;
      (2) model the intent as a **first-class entity** when it has its own lifecycle, id and audit
      trail — a refund is `POST /refunds`, not a verb on a deposit;
      (3) change **state via a sub-resource** — `PUT /deposits/778/status {"status":"CANCELLED"}`;
      (4) an explicit **controller-style action** when nothing else fits —
      `POST /payment-runs/91/actions/retry`. Be consistent. `[TABLE]` `[PROVE]`
1.21.3 Google AIP-136 custom methods: the `:verb` colon syntax
      (`POST /v1/deposits/778:capture`), when AIP permits them, and why the colon exists (it cannot
      collide with a resource id). `[SOURCE]` `[RESEARCH]`
1.21.4 State machines as API contracts: publish the legal transitions, return `409` for an illegal
      one, and let the client discover the currently-legal set (a `permittedActions` array, or
      HATEOAS links). QuizStakes' `DEP-*` diagram is exactly this artifact. `[PROVE]` `[SOURCE]`
1.21.5 **`202 Accepted` and the operation resource**, in full: `202` + `Location: /operations/{id}`
      + a body with `status`, then `GET /operations/{id}` returning `PENDING`/`RUNNING`/`SUCCEEDED`/
      `FAILED`, with `Retry-After` to pace the polling, and on success either the result inline or a
      `303 See Other` to the created resource. `[FLOW]` `[CODE]`
1.21.6 Microsoft's two LRO patterns, named: **RELO** (resource-based long-running operation — the
      resource itself carries a provisioning state, no separate operation resource) vs **stepwise**
      (a distinct operation resource with its own status), plus the **retention policy for operation
      results** rule. `[TABLE]` `[SOURCE]` `[RESEARCH]`
1.21.7 Google AIP-151 long-running operations: `google.longrunning.Operation` with `name`,
      `metadata`, `done`, `response`/`error`, the `operation_info` annotation, and the
      `Operations` service with `GetOperation`/`ListOperations`/`CancelOperation`/`DeleteOperation`/
      `WaitOperation`. `[SOURCE]` `[RESEARCH]`
1.21.8 `Prefer: respond-async` (RFC 7240) as the standardised way to let the **client** choose sync
      or async, with `Preference-Applied` echoing the decision. `[HDR]` `[RESEARCH]`
1.21.9 Cancelling an in-flight operation: `DELETE /operations/{id}` vs
      `POST /operations/{id}:cancel`, best-effort semantics, and the honest statement that
      cancellation is a request, not a guarantee. `[PROVE]`
1.21.10 Progress reporting: a percentage, a step name, an item count, or nothing. What each costs to
        maintain truthfully. `[TABLE]`
1.21.11 Polling cadence and cost arithmetic: 10,000 clients polling a job every second is
        10,000 req/sec of pure overhead. The alternatives — `Retry-After`-paced polling, long
        polling, SSE on the operation resource, or a webhook on completion. `[NUM]` `[PROVE]`
1.21.12 **Bulk vs batch, which are different things.** *Bulk* = the same operation over many items
        (`POST /deposits/bulk`); *batch* = many different operations in one envelope (a
        request-array, OData `$batch`, Graph `/$batch`). `[TABLE]` `[PROVE]`
1.21.13 The partial-failure problem, which is the whole difficulty of bulk: all-or-nothing
        (transactional, simple contract, poor throughput, and impossible across services) vs
        per-item results (`207 Multi-Status`, or `200` with a per-item status array). State how the
        client is expected to retry — and that per-item retry requires **per-item idempotency keys**.
        `[TABLE]` `[PROVE]` `[TRAP]`
1.21.14 `207 Multi-Status` in detail: WebDAV origin, the response shape, and why many teams prefer
        `200` with an explicit result array instead (generic clients do not understand 207).
        `[CODE]` `[TRAP]`
1.21.15 Google's batch methods (AIP-231/233/234/235): `BatchGet`, `BatchCreate`, `BatchUpdate`,
        `BatchDelete`, with the rule that batch methods are **atomic by default** and any relaxation
        must be explicit. `[SOURCE]` `[RESEARCH]`
1.21.16 Bulk size limits, and why they are not optional: cap the item count, cap the body size, and
        state what happens past the cap. With HTTP/2 multiplexing, N individual requests are often
        cheaper than one giant batch — which is the strongest argument against batch endpoints
        existing at all. `[NUM]` `[PROVE]` `[X-REF 10]`
1.21.17 **Search with too many parameters for a URL:** `POST /deposits/search` is the accepted
        pragmatic break, and it costs you HTTP caching, `Vary`-based negotiation and safe-retry
        semantics. `QUERY` (RFC 10008) is the standards-track fix — safe, idempotent, cacheable with
        the body in the cache key. `[PROVE]` `[VERSION-TRAP]` `[RESEARCH]`
1.21.18 **Import/export and jobs** as first-class resources (AIP-152 Jobs, AIP-153 Import and
        export), with the signed-URL handoff for large payloads so the bytes never traverse your API.
        `[RESEARCH]` `[X-REF 18]`
1.21.19 File upload contracts: `multipart/form-data`, direct `PUT` of the octet stream, presigned S3
        URLs, and **resumable/chunked upload** (`tus`, or `Content-Range` + a session resource).
        What each costs in memory, timeout and retry-ability. `[TABLE]` `[X-REF 18]`
1.21.20 The QuizStakes non-CRUD surface, mapped to the four options with a justification for each:
        `POST /deposits/{id}/captures` (option 1, retriable with the same key),
        `POST /refunds` (option 2, own lifecycle and audit trail),
        `PUT /clients/{id}/self-exclusion` (option 3, idempotent, 500 ms budget),
        `POST /payment-runs/{id}/actions/retry` (option 4, operator-only, role-checked at
        `InternalPlatforms`), and the **stake reservation** as its own resource with an expiry —
        because `PaymentRun` is explicitly *not* a client state (scenario § 13.1). `[TABLE]`
        `[SOURCE]` `[NUM]`

*(20 leaves)*

## §1.22 Hypermedia and HATEOAS

1.22.1 What HATEOAS actually claims: application state transitions are driven by **server-provided
      choices in the representation**, so the client needs only the entry URI and the media type.
      `[SPEC]` `[PROVE]`
1.22.2 The concrete payoff, stated so it does not sound theoretical: the server can move a URI,
      change a workflow, or gate an action by permission and state, **and the client needs no
      release**. `permittedActions` computed server-side is a real version of this.
      `[PROVE]`
1.22.3 The concrete costs: payload growth (often 2–5×), a client programming model almost nobody
      uses, cache fragmentation (links depend on the caller's permissions, so `Vary: Authorization`),
      and the fact that generated clients hardcode paths anyway. `[PROVE]` `[TRAP]`
1.22.4 The hypermedia format zoo, compared: **HAL** (`_links`, `_embedded`, `curies`, media type
      `application/hal+json`), **HAL-FORMS** (adds write affordances), **JSON:API 1.1**
      (`data`/`links`/`relationships`/`included`/`meta`, full linkage, `ext` and `profile` media-type
      parameters, and the rule that any other media-type parameter → **415**), **Siren**
      (`entities`, `actions`, `links`, `class`), **Collection+JSON**, **JSON-LD + Hydra**
      (`@context`, `@id`, `@type`, `hydra:operation`), and **plain `Link` headers** (RFC 8288).
      `[TABLE]` `[RESEARCH]`
1.22.5 The registered link relations you will actually use, and the rule that a custom relation
      should be a URI: `self`, `next`, `prev`/`previous`, `first`, `last`, `up`, `related`,
      `describedby`, `alternate`, `edit`, `service-desc`, `service-doc`, `deprecation`,
      `successor-version`, `latest-version`, `payment`. `[SPEC]` `[TABLE]`
1.22.6 Zalando's position, which is the most defensible published one: **"MUST use REST maturity
      level 2"**, **"MAY use REST maturity level 3 — HATEOAS"**, must use common hypertext controls,
      must use full absolute URIs for resource identification, should use simple hypertext controls
      for pagination and self-references, and **must not use `Link` headers with JSON entities**.
      `[SOURCE]` `[RESEARCH]`
1.22.7 The minimum viable hypermedia that is actually worth shipping: `self` on every resource,
      `next`/`prev` on every collection, and a state-dependent action list on anything with a
      lifecycle. Everything beyond that is optional. `[PROVE]`
1.22.8 **Spring HATEOAS** as the concrete API: `RepresentationModel`, `EntityModel<T>`,
      `CollectionModel<T>`, `PagedModel`, `Link`, `WebMvcLinkBuilder.linkTo`/`methodOn`, `Affordance`,
      `RepresentationModelAssembler`, and the supported media types (HAL, HAL-FORMS, Collection+JSON,
      ALPS, UBER, JSON:API via a separate project). Plus **Spring Data REST** as the
      "HATEOAS for free" option and why exposing your repositories is a coupling decision, not a
      shortcut. `[API]` `[TRAP]` `[X-REF 08]`
1.22.9 API discovery documents as the pragmatic substitute for level 3: `/.well-known/…`,
      `service-desc` pointing at the OpenAPI document, an OAuth/OIDC metadata document, and a root
      resource listing entry points. `[RESEARCH]`
1.22.10 **Trap:** "we're RESTful because we use JSON over HTTP." Know the term, know the level you
        are at, know why you chose it, and do not claim level 3 in an interview unless your links are
        real. `[TRAP]`
1.22.11 The QuizStakes case where hypermedia genuinely earns its place: the `DEP-*` state machine has
        ~22 states with different legal transitions in each, and the legality depends on
        restrictions, limits and PSP state that the client cannot compute. Returning the legal
        actions is cheaper and safer than publishing the machine. `[SOURCE]` `[PROVE]`

*(11 leaves)*
## §1.23 Contract-first: OpenAPI and JSON Schema

1.23.1 Why a machine-readable description changes the economics: client generation, server stubs,
      mock servers, request validation at the gateway, contract tests, breaking-change detection in
      CI, and documentation that cannot drift. Each one is a concrete artifact, not a slogan.
      `[TABLE]` `[PROVE]`
1.23.2 The lineage: Swagger 1.x/2.0 → OpenAPI 3.0 (donated to the Linux Foundation, 2017) → **3.1**
      (2021, full JSON Schema 2020-12 alignment, `webhooks`, `jsonSchemaDialect`) → **3.2.0**
      (23 Sept 2025). "Swagger" now means the tooling, not the spec. `[VERSION-TRAP]` `[RESEARCH]`
1.23.3 The document structure, object by object: `openapi`, `info`, `jsonSchemaDialect`, `servers`,
      `paths`, `webhooks`, `components`, `security`, `tags`, `externalDocs`. `[TABLE]` `[SPEC]`
1.23.4 `paths` → Path Item → Operation: `operationId` (unique, and it is what generators name your
      methods after), `summary`, `description`, `tags`, `parameters`, `requestBody`, `responses`,
      `callbacks`, `deprecated`, `security`, `servers`. `[SPEC]` `[API]`
1.23.5 The Parameter Object: `in` = `path` | `query` | `header` | `cookie`; `required`; `style` =
      `form` | `simple` | `spaceDelimited` | `pipeDelimited` | `deepObject` | `label` | `matrix`;
      `explode`; `allowReserved`; `allowEmptyValue`. `style`+`explode` is how you describe
      `?status=A&status=B` versus `?status=A,B` — and it is the part everyone hand-waves.
      `[TABLE]` `[SPEC]`
1.23.6 `components` and reuse: `schemas`, `responses`, `parameters`, `examples`, `requestBodies`,
      `headers`, `securitySchemes`, `links`, `callbacks`, `pathItems` (3.1+). `$ref` mechanics,
      internal vs external refs, and the durable-immutable-reference rule (Zalando's first general
      guideline). `[SPEC]` `[SOURCE]`
1.23.7 `securitySchemes` types: `apiKey`, `http` (with `scheme` = `basic`/`bearer` and
      `bearerFormat`), `oauth2` (flows: `implicit`, `password`, `clientCredentials`,
      `authorizationCode`, and 3.2's `deviceAuthorization`), `openIdConnect`, `mutualTLS`. Plus
      3.2's `oauth2MetadataUrl` and deprecatable schemes. `[TABLE]` `[X-REF 13]` `[RESEARCH]`
1.23.8 `webhooks` (3.1+) vs `callbacks` (3.0+): `webhooks` describes requests **you send** that are
      not tied to an operation; `callbacks` describes requests you send as a consequence of a
      specific operation. Knowing the difference is a genuine discriminator. `[SPEC]` `[PROVE]`
      `[RESEARCH]`
1.23.9 `links` (3.0+): the OpenAPI expression of hypermedia relationships between operations —
      runtime expressions like `$response.body#/id`. Rarely used, worth recognising. `[SPEC]`
1.23.10 **JSON Schema 2020-12** as the schema language: `type`, `properties`, `required`,
        `additionalProperties`, `patternProperties`, `enum`, `const`, `format`, `pattern`,
        `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum`, `multipleOf`,
        `minLength`/`maxLength`, `minItems`/`maxItems`/`uniqueItems`, `items`/`prefixItems`,
        `oneOf`/`anyOf`/`allOf`/`not`, `if`/`then`/`else`, `$defs`, `$dynamicRef`, `readOnly`/
        `writeOnly`, `deprecated`, `default`, `examples`. `[TABLE]` `[SPEC]`
1.23.11 The 3.0 → 3.1 schema deltas that trip people: `nullable: true` is **gone** (use
        `type: ["string","null"]`), `example` → `examples` (an array), `exclusiveMinimum` is now a
        number not a boolean, and `type` may be an array. `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
1.23.12 Polymorphism: `oneOf` + `discriminator` (with `propertyName` and `mapping`), and the
        generator behaviour it drives. Map it onto Java 21 **sealed interfaces + records** and
        Jackson's `@JsonTypeInfo`/`@JsonSubTypes`. `[API]` `[X-REF 04]`
1.23.13 OpenAPI 3.2's additions, enumerated: the `QUERY` method, `additionalOperations` for
        non-standard methods, first-class streaming media types (`text/event-stream`,
        `application/jsonl`, `application/json-seq`, `multipart/mixed`), **tag hierarchies**
        (`parent`/`kind`), `deviceAuthorization` and `oauth2MetadataUrl`, deprecatable security
        schemes, and expanded reusability. Non-breaking against 3.1. `[TABLE]` `[RESEARCH]`
        `[VERSION-TRAP]`
1.23.14 **AsyncAPI** as the event-driven sibling: `channels`, `operations`, `messages`, `bindings`
        (Kafka, AMQP, WebSocket, SSE), and where it belongs — the webhook and event contracts this
        guide's §1.25 and `14-messaging-queues.md` own. `[X-REF 14]` `[RESEARCH]`
1.23.15 The **design-first vs code-first** workflow, decided rather than debated: design-first for
        anything crossing a team or org boundary (the spec is the negotiation artifact), code-first
        for an internal service where the spec is documentation. And the hybrid that actually works —
        code-first generation plus a **committed spec snapshot** that CI diffs against. `[PROVE]`
1.23.16 The Java tooling surface: **springdoc-openapi** (`@Operation`, `@ApiResponse`, `@Schema`,
        `@Parameter`, `GroupedOpenApi`, `/v3/api-docs`, `/swagger-ui.html`), the older
        `springfox` (unmaintained — do not start there), **openapi-generator** and
        `swagger-codegen` for clients, `swagger-request-validator` for validating traffic against
        the spec in tests, and Spring's declarative **HTTP interfaces** (`@HttpExchange`,
        `HttpServiceProxyFactory`) as a hand-written alternative to generated clients. `[API]`
        `[RESEARCH]`
1.23.17 Spec linting and governance: **Spectral** rulesets, `vacuum`, Zalando's `zally`, and the
        practice of publishing your org's style guide as an executable ruleset rather than a wiki
        page. `[RESEARCH]`
1.23.18 **Breaking-change detection in CI**: `oasdiff`, `openapi-diff`, `buf breaking` for protobuf,
        and the practice of failing the build on a breaking diff against the last released spec.
        This is the mechanism that makes §1.18's rules enforceable rather than aspirational.
        `[PROVE]` `[RESEARCH]`
1.23.19 Examples and mock servers: `examples` on responses, Prism/`openapi-mock` for a mock server
        from the spec, and why a wrong example is worse than no example (clients copy it).
        `[TRAP]`
1.23.20 Documentation beyond the reference: a getting-started path, an authentication guide, an
        errors page listing every problem `type`, a changelog, a status page, and runnable examples.
        The reference is the smallest part of good docs. `[PROVE]`
1.23.21 The QuizStakes spec layout: one OpenAPI document per bounded context
        (`accountopening`, `paymentservice`, `fundsledger`, `clientrestrictions`), a shared
        `components` library for `Money`, `ProblemDetail`, `PageInfo` and the status enums, one
        AsyncAPI document for the `DEP-*`/`BDP-*` domain events, and a gateway-composed public
        document for the client-facing surface. `[SOURCE]` `[PROVE]`

*(21 leaves)*

## §1.24 The security face of the contract

1.24.1 The one-paragraph statement of the boundary: `13-web-security.md` owns the mechanisms; this
      guide owns which header carries the credential, which status code a failure maps to, and how
      permissions shape the *shape* of the API. `[X-REF 13]`
1.24.2 Credential transport: `Authorization: Bearer <token>` only. Not a query parameter, not a
      cookie for a cross-origin API, not a custom header that bypasses your framework's auth
      handling. `[TRAP]` `[X-REF 13]`
1.24.3 The status-code contract for auth: `401` + `WWW-Authenticate` for unauthenticated, `403` for
      unauthorised, `404` where existence is itself privileged, and `insufficient_scope` in the
      `WWW-Authenticate` parameters per RFC 6750. `[CODE]` `[X-REF 13]`
1.24.4 Scopes as an API design artifact: coarse (`payments:read`, `payments:write`) vs fine
      (per-endpoint), and the rule that scope granularity is a *contract* decision because a client
      requests scopes at registration time. `[PROVE]` `[X-REF 13]`
1.24.5 The **authentication vs authorisation split at the edge**: the gateway verifies *who*, the
      service decides *what*. QuizStakes states it as an architectural rule — no token carries
      permissions, restrictions or account status, so a service that trusts a claim for
      authorisation is violating the design. `[SOURCE]` `[PROVE]` `[TRAP]`
1.24.6 **Object-level authorisation is not the gateway's job** (OWASP API Security Top 10's #1,
      BOLA): "can this caller see *this* withdrawal" requires the resource, so it must be checked in
      the service. A gateway that tries becomes a mega-gateway coupled to business logic.
      `[TRAP]` `[X-REF 13]` `[RESEARCH]`
1.24.7 The OWASP **API** Security Top 10 as a design checklist, named: broken object-level
      authorisation, broken authentication, broken object property-level authorisation (mass
      assignment + excessive data exposure), unrestricted resource consumption, broken
      function-level authorisation, unrestricted access to sensitive business flows, SSRF, security
      misconfiguration, improper inventory management, unsafe consumption of APIs. Each one is an
      *API design* failure, not a coding failure. `[TABLE]` `[X-REF 13]` `[RESEARCH]`
1.24.8 **Mass assignment**, mechanically: binding a request body straight onto an entity lets a
      caller set `role`, `balance` or `restrictionStatus`. The fix is a request DTO/record with
      exactly the writable fields — which is an API design decision, not a validation one.
      `[TRAP]` `[PROVE]` `[X-REF 08]`
1.24.9 **Excessive data exposure**: returning the entity and letting the UI hide fields. The PAN,
      the internal risk score and the operator note all shipped. Response DTOs, not entities.
      `[TRAP]` `[PROVE]`
1.24.10 CORS as an API contract concern (the mechanism is in 13): the preflight, which headers you
        must allow for `Idempotency-Key` / `If-Match` / `traceparent` to work at all, and
        `Access-Control-Expose-Headers` for `ETag`, `Location`, `RateLimit` and `Deprecation` —
        because **a header the browser cannot read may as well not exist**. `[TRAP]` `[X-REF 13]`
        `[PROVE]`
1.24.11 Webhook and callback security as *your* obligation to the receiver: signatures, timestamps,
        replay windows, and the SSRF risk of letting a customer register an arbitrary URL (metadata
        endpoints, internal ranges). `[X-REF 13]` `[RESEARCH]`
1.24.12 Audit as a contract: which fields must be recorded per call, and QuizStakes' specific
        requirement that `InternalPlatforms` records **which operator role was exercised**, not just
        which person — because segregation of duties has to be auditable later. `[SOURCE]`
1.24.13 Sensitive-data handling in logs and traces: never log a full body, redact by field name at
        the serialiser, and keep the correlation id (which is safe) rather than the payload (which is
        not). `[X-REF 20]` `[X-REF 13]`

*(13 leaves)*

## §1.25 Pushing data: polling, long polling, SSE, WebSocket, webhooks

1.25.1 The five mechanisms and the axis each optimises, as a table with direction, protocol,
      statefulness, browser support, infrastructure cost and failure mode. `[TABLE]`
1.25.2 **Polling**: the client asks on a timer. Simple, no new infrastructure, and the latency-vs-load
      trade is explicit — halve the latency, double the load. Mitigate with conditional GETs
      (`ETag` → `304`) so the *cost* of a poll that finds nothing is near zero. `[PROVE]` `[NUM]`
1.25.3 **Long polling**: the server holds the request open until there is something to say or a
      timeout fires. Near-real-time with no new protocol; costs a held connection (and, on a
      thread-per-request server, a held thread — which is precisely what **virtual threads** and
      Spring MVC's async `DeferredResult`/`Callable` fix). `[PROVE]` `[X-REF 04]` `[X-REF 05]`
1.25.4 **SSE (Server-Sent Events)**: one-way server→client over a normal HTTP response with
      `Content-Type: text/event-stream`. The wire format — `event:`, `data:`, `id:`, `retry:`,
      double-newline framing, comment lines (`:`) as keep-alives. Built-in reconnection with
      `Last-Event-ID` for resumption. `[WIRE]` `[SPEC]`
1.25.5 SSE's two real constraints: the **6-connections-per-origin limit on HTTP/1.1** (so six tabs
      exhaust the browser's budget — fixed by HTTP/2 multiplexing), and no binary payloads.
      `[NUM]` `[TRAP]` `[X-REF 10]`
1.25.6 **WebSocket**: bidirectional, full-duplex, over a single TCP connection after an HTTP
      `Upgrade` handshake (`101 Switching Protocols`, `Sec-WebSocket-Key`/`-Accept`/`-Version`/
      `-Protocol`). Frame types, ping/pong, close codes. `[WIRE]` `[SPEC]`
1.25.7 WebSocket's architectural cost, stated as the thing it breaks: it is **stateful**, so the
      stateless-scaling story from §1.3 is gone — you need sticky routing or a pub/sub backplane,
      and a deploy disconnects every client at once. `[PROVE]` `[TRAP]`
1.25.8 The subprotocols worth naming: **STOMP** (what Spring's WebSocket support speaks), MQTT over
      WebSocket, GraphQL-WS / graphql-transport-ws for subscriptions, and SockJS as the fallback
      layer. `[API]`
1.25.9 **Webhooks**: your server calls *their* server. The point is decoupling in time and across
      organisations — and the consequence is that **you now operate a distributed system on their
      behalf**. `[PROVE]`
1.25.10 The webhook provider's obligations, enumerated as a contract: registration (URL, event
        types, secret), a stable payload envelope, **at-least-once delivery**, retries with
        exponential backoff and jitter, a signature, a timestamp, an event id for consumer
        idempotency, a sequence/version for ordering, a delivery log the customer can inspect, manual
        replay, and automatic disabling of a persistently failing endpoint. `[TABLE]` `[PROVE]`
1.25.11 **Standard Webhooks 1.0**, in full detail because it is the closest thing to a spec:
        headers `webhook-id`, `webhook-timestamp` (unix seconds), `webhook-signature`
        (space-delimited, so multiple signatures coexist); the signed content is
        `"{webhook_id}.{webhook_timestamp}.{body}"`; **v1** = HMAC-SHA256 with a base64 secret
        prefixed `whsec_` (24–64 bytes), base64 output with padding (RFC 4648) —
        `webhook-signature: v1,K5oZfzN95Z9UVu1EsfQmfVNQhnkZ2pj9o9NDN/H/pI4=`; **v1a** = asymmetric
        ed25519 with `whpk_`/`whsk_` prefixes; payload shape `{type, timestamp, data}` with
        period-delimited hierarchical event types over `[a-zA-Z0-9_]`; success is any `2xx`,
        **`410 Gone` signals permanent disable**, a 15–30 s request timeout is recommended, and the
        retry schedule spans seconds to 75+ hours. `[SPEC]` `[WIRE]` `[NUM]` `[RESEARCH]`
1.25.12 The security requirements from that spec, each with its attack: **verify the timestamp within
        a tolerance** (replay), **constant-time comparison** (signature oracle), **multiple
        signatures for zero-downtime key rotation**, **proxy outbound calls through a filtering
        proxy and isolate the workers** (SSRF into your own metadata service), HTTPS, and static
        egress IPs for customer firewalls. `[TRAP]` `[X-REF 13]` `[RESEARCH]`
1.25.13 **Ordering is not guaranteed** and cannot be, over independent HTTP requests with retries.
        Give the consumer what it needs to cope: a monotonic sequence number or a resource version,
        so a stale event can be dropped. `[PROVE]` `[TRAP]` `[X-REF 14]`
1.25.14 The consumer's obligations: respond `2xx` fast and process asynchronously (a slow handler
        causes the provider's retry storm), **be idempotent on `webhook-id`**, verify the signature
        before parsing, and tolerate out-of-order and duplicate delivery. `[FLOW]` `[X-REF 14]`
1.25.15 Thin vs fat payloads: send the event id and let the consumer fetch (small, always fresh,
        needs auth and a round trip, and leaks nothing if the URL is intercepted) vs send the full
        state (no round trip, may be stale on arrival, larger signature surface, and the data is now
        in their logs). `[TABLE]` `[PROVE]`
1.25.16 **Webhooks vs polling from the consumer's side**: a consumer that cannot expose an endpoint
        needs a poll API, so a serious provider ships both — plus a *delta/changes* endpoint
        (Microsoft Graph's `delta` query with `deltaLink`/`nextLink`) as the efficient middle.
        `[TABLE]` `[RESEARCH]`
1.25.17 The **decision rule**, memorisable: server-to-server across a trust boundary → webhooks;
        browser needs live updates in one direction → SSE; genuinely bidirectional and latency-
        sensitive → WebSocket; everything else → poll with conditional GETs. `[PROVE]`
1.25.18 The QuizStakes application: PSP → `PaymentService` deposit notifications are **inbound
        webhooks** (signature + timestamp + idempotency on their event id, feeding `DEP-500`/
        `DEP-690`); bank inbound push (`BDP-000 FUNDS_RECEIVED`) is a webhook whose `BDP-150
        UNMATCHED_SUSPENSE` state exists precisely because delivery carries no guarantee of
        matchability; the operator console's live `PaymentRun` progress is **SSE**; and a client
        balance change is **poll with `ETag`**, because 2.4M clients on WebSockets is a backplane
        problem you do not need. `[NUM]` `[SOURCE]` `[PROVE]`

*(18 leaves)*

## §1.26 gRPC as a contract

1.26.1 What gRPC is, precisely: protobuf-defined services over HTTP/2, with generated stubs on both
      sides. Schema-first is not optional — the `.proto` **is** the contract. `[PROVE]`
1.26.2 The four call types and what each is for: **unary**, **server streaming**, **client
      streaming**, **bidirectional streaming**. `[TABLE]`
1.26.3 The `.proto` surface you must be able to write: `syntax = "proto3"`, `package`, `option
      java_package`/`java_outer_classname`/`java_multiple_files`, `message`, `service`, `rpc`,
      `stream`, scalar types, `repeated`, `map<K,V>`, `oneof`, `optional` (reintroduced in 3.15 for
      explicit presence), `reserved`, `enum`, nested types, and `import`. `[API]` `[TABLE]`
1.26.4 The well-known types you should reach for instead of inventing: `google.protobuf.Timestamp`,
      `Duration`, `FieldMask`, `Struct`, `Any`, `Empty`, and the wrappers (`Int32Value`,
      `StringValue`, …) that exist purely to express presence. `[TABLE]`
1.26.5 **Field numbers are the contract**, not names: 1–15 encode in one byte (reserve them for the
      hot fields), 16–2047 in two, 19000–19999 are reserved by protobuf itself, and the maximum is
      536,870,911. `[NUM]` `[WIRE]` `[PROVE]`
1.26.6 The **compatibility rules**, exhaustively: never change a field number, never change a
      field's type (the wire type changes and every serialised message becomes unreadable), never
      reuse a deleted number, always `reserved` the number **and the name** (the name matters for
      JSON), do not change `json_name`, do not move a field into or out of a `oneof`, and adding a
      field is safe because unknown fields are preserved in `unknown_fields`. `[TABLE]` `[PROVE]`
      `[RESEARCH]`
1.26.7 `buf breaking`'s four rule categories as an executable statement of those rules: **FILE**
      (source-level: `FIELD_NO_DELETE`, `ENUM_VALUE_NO_DELETE`, `RPC_NO_DELETE`, `FILE_SAME_PACKAGE`,
      …), **PACKAGE**, **WIRE_JSON** (`FIELD_NO_DELETE_UNLESS_NAME_RESERVED`, `FIELD_SAME_JSON_NAME`,
      `FIELD_WIRE_JSON_COMPATIBLE_TYPE`, …), and **WIRE**
      (`FIELD_NO_DELETE_UNLESS_NUMBER_RESERVED`, `FIELD_WIRE_COMPATIBLE_TYPE`,
      `RPC_SAME_IDEMPOTENCY_LEVEL`, …). The category you enable *is* your compatibility promise.
      `[SOURCE]` `[TABLE]` `[RESEARCH]`
1.26.8 Protobuf **Editions** as the successor to `syntax = "proto2"/"proto3"`, and the feature-based
      model that replaces the syntax switch. `[VERSION-TRAP]` `[RESEARCH]`
1.26.9 The **17 canonical status codes** (`google.rpc.Code`, 0–16), each with its meaning and its
      nearest HTTP equivalent: `OK` 0, `CANCELLED` 1, `UNKNOWN` 2, `INVALID_ARGUMENT` 3,
      `DEADLINE_EXCEEDED` 4, `NOT_FOUND` 5, `ALREADY_EXISTS` 6, `PERMISSION_DENIED` 7,
      `RESOURCE_EXHAUSTED` 8, `FAILED_PRECONDITION` 9, `ABORTED` 10, `OUT_OF_RANGE` 11,
      `UNIMPLEMENTED` 12, `INTERNAL` 13, `UNAVAILABLE` 14, `DATA_LOSS` 15, `UNAUTHENTICATED` 16.
      `[TABLE]` `[SOURCE]` `[RESEARCH]`
1.26.10 The three codes people misuse: `FAILED_PRECONDITION` vs `ABORTED` vs `UNAVAILABLE` — the
        canonical distinction is whether the client should retry as-is (`UNAVAILABLE`), retry at a
        higher level (`ABORTED`), or fix state first (`FAILED_PRECONDITION`). `[TRAP]` `[PROVE]`
        `[SOURCE]`
1.26.11 `DEADLINE_EXCEEDED`'s honest caveat, quoted: for state-changing operations "this error may
        be returned even if the operation has completed successfully" — which is the gRPC restatement
        of §1.17.1 and the reason idempotency matters in RPC too. `[SOURCE]` `[PROVE]`
1.26.12 **Deadlines, not timeouts**: `grpc-timeout` carries an absolute budget that **propagates**
        down the call chain, so a 30 ms restriction budget can be enforced end to end rather than
        per hop. Units: `H`, `M`, `S`, `m`, `u`, `n`. This is a genuine advantage over naive HTTP.
        `[WIRE]` `[NUM]` `[PROVE]` `[RESEARCH]`
1.26.13 Metadata as gRPC's header equivalent: ASCII keys, `-bin` suffix for binary values,
        `Metadata`/`Context` in grpc-java, and the interceptor model (`ClientInterceptor`,
        `ServerInterceptor`). `[API]`
1.26.14 The rich error model: `google.rpc.Status` in the `grpc-status-details-bin` trailer, carrying
        `ErrorInfo`, `BadRequest.FieldViolation`, `QuotaFailure`, `PreconditionFailure`,
        `ResourceInfo`, `RequestInfo`, `Help`, `LocalizedMessage`, `DebugInfo`, `RetryInfo`.
        `[TABLE]` `[RESEARCH]`
1.26.15 Service config and retry policy: `methodConfig`, `retryPolicy`
        (`maxAttempts`, `initialBackoff`, `maxBackoff`, `backoffMultiplier`,
        `retryableStatusCodes`), `hedgingPolicy`, and per-method `timeout` — declarative resilience
        the client library implements for you. `[API]` `[RESEARCH]`
1.26.16 Health checking (`grpc.health.v1.Health` with `Check`/`Watch`), server reflection, and
        channelz — the operational surface. `[API]`
1.26.17 gRPC's browser problem and the three answers: **gRPC-Web** (trailers moved into the body via
        a proxy such as Envoy), **Connect** (one implementation speaking gRPC, gRPC-Web and its own
        HTTP/1.1-friendly JSON protocol), and **gRPC-JSON transcoding / grpc-gateway** (AIP-127 HTTP
        and gRPC transcoding, with `google.api.http` annotations generating a REST facade from the
        same proto). `[TABLE]` `[RESEARCH]`
1.26.18 The gRPC-vs-REST comparison as a table with an honest verdict per row: payload size,
        CPU cost, browser support, streaming, human debuggability (`curl` vs `grpcurl`), caching
        (gRPC has none), intermediary support (WAF, CDN, gateway), schema enforcement, code
        generation, load balancing (L7 required for long-lived HTTP/2 connections), and versioning
        story. `[TABLE]` `[PROVE]`
1.26.19 When gRPC is the wrong answer: a public API for unknown clients, anything a browser calls
        directly without a proxy, anything you want a CDN to cache, and anything whose main consumer
        is a human with `curl`. `[PROVE]` `[TRAP]`
1.26.20 The Java surface: `protobuf-maven-plugin`/`protoc`, generated `*Grpc` stubs, `ManagedChannel`,
        blocking vs async vs future stubs, `StreamObserver`, `grpc-spring-boot-starter`, and Spring
        Boot 3.5's own `spring-grpc` support. `[API]` `[RESEARCH]`
1.26.21 The QuizStakes decision: `ClientRestrictions.decide()` is the best gRPC candidate on the
        platform — internal, both sides deploy together, a 30 ms budget where serialisation and
        deadline propagation are measurable, and no browser or CDN involvement. Argue it against the
        cost: a second protocol to operate, a second observability pipeline, and no `curl`.
        `[NUM]` `[PROVE]` `[SOURCE]`

*(21 leaves)*
## §1.27 GraphQL as a contract

1.27.1 The problem GraphQL claims to solve: over-fetching (the endpoint returns 40 fields, the screen
      needs 4) and under-fetching (the screen needs three resources, so three round trips). Both are
      **client-diversity** problems, which is why GraphQL wins where clients are many and varied.
      `[PROVE]`
1.27.2 The Schema Definition Language surface: `type`, `input`, `interface`, `union`, `enum`,
      `scalar`, `schema`, `directive`, non-null `!`, list `[T]`, and the three root operation types
      `Query` / `Mutation` / `Subscription`. `[TABLE]` `[SPEC]`
1.27.3 The specified directives — `@skip`, `@include`, `@deprecated(reason:)`, `@specifiedBy` — and
      the non-normative but ubiquitous ones: `@defer`, `@stream`, `@oneOf`, plus federation's
      `@key`, `@external`, `@requires`, `@provides`, `@shareable`. `[TABLE]` `[RESEARCH]`
1.27.4 The execution model: parse → validate against the schema → execute field-by-field with a
      resolver per field, breadth-first per level, and the **field-resolution tree** as the unit of
      work. `[FLOW]` `[SPEC]`
1.27.5 The response shape and its consequence: `{data, errors, extensions}`, with **partial
      success** as a first-class outcome — `data` may be non-null while `errors` is non-empty, and a
      `null` propagates up to the nearest nullable parent. That nullability-propagation rule is the
      part everyone gets wrong. `[SPEC]` `[PROVE]` `[TRAP]`
1.27.6 The error object: `message`, `locations`, `path`, `extensions` (where you put your stable
      machine-readable code, since GraphQL has no status codes). `[SPEC]`
1.27.7 **The status-code story, corrected.** With `application/json` a GraphQL server returns
      `200` for everything, including validation failures — which is why "GraphQL breaks HTTP
      monitoring" became folklore. With **`application/graphql-response+json`** (GraphQL-over-HTTP),
      a response with a non-null `data` entry **MUST** be 2xx and a request-validation failure is
      **400**. Say which media type you are talking about. `[SPEC]` `[VERSION-TRAP]` `[TRAP]`
      `[RESEARCH]`
1.27.8 **The N+1 problem** and **DataLoader**: batching within a tick plus per-request caching, why
      it is *mandatory* rather than an optimisation, and the mapping onto Spring's
      `BatchLoaderRegistry` / `@BatchMapping`. `[PROVE]` `[API]` `[X-REF 08]`
1.27.9 **Query cost and depth limiting**: a malicious or careless nested query is an unbounded
      request. The controls — max depth, max complexity with per-field cost weights, node limits,
      timeout, and **persisted documents / allow-listing** (the only real answer for a public
      endpoint). `[PROVE]` `[TRAP]` `[X-REF 13]`
1.27.10 **Automatic Persisted Queries (APQ)** and persisted-document contracts: send a hash instead
        of the document, which restores cacheability and closes the arbitrary-query hole. `[PROVE]`
        `[RESEARCH]`
1.27.11 **Caching is GraphQL's weakest point**: one POST endpoint means HTTP caching is gone, so you
        need normalised client-side caching (Apollo/Relay), per-field server caching, or
        `@cacheControl` hints. Say this plainly — it is the honest cost. `[PROVE]` `[TRAP]`
1.27.12 **Authorisation in GraphQL** is per-field, not per-endpoint, which is a genuinely harder
        problem: a single query can traverse from an object you may see to one you may not. Field-level
        directives, resolver-level checks, and the schema-visibility question. `[PROVE]`
        `[X-REF 13]`
1.27.13 **Versioning in GraphQL**: the official position is "don't version — evolve the schema",
        using `@deprecated` plus field-usage telemetry to know when a field is dead. This works only
        because the client *declares* which fields it uses — that is the real innovation. `[PROVE]`
        `[RESEARCH]`
1.27.14 Subscriptions: the transport is not in the core spec —
        `graphql-transport-ws` / `graphql-ws` over WebSocket, or SSE. Which means "GraphQL
        subscriptions" inherits every WebSocket cost from §1.25.7. `[TRAP]` `[RESEARCH]`
1.27.15 `@defer` and `@stream` incremental delivery: initial payload plus later chunks over
        `multipart/mixed`, available in graphql-js v17 via `experimentalExecuteIncrementally()`, and
        **still not a ratified specification**. Do not present it as standard. `[VERSION-TRAP]`
        `[RESEARCH]`
1.27.16 **Federation and schema stitching**: Apollo Federation's `@key`-based entity resolution, the
        supergraph/subgraph split, and the alternative (a BFF that composes REST calls). What
        federation buys and what it costs organisationally. `[TABLE]` `[RESEARCH]`
1.27.17 Introspection as a feature and a liability: it powers every tool and it publishes your entire
        schema — disable it in production for a non-public graph. `[TRAP]` `[X-REF 13]`
1.27.18 The Java surface: `graphql-java`, **Spring for GraphQL** (`@QueryMapping`,
        `@MutationMapping`, `@SubscriptionMapping`, `@SchemaMapping`, `@BatchMapping`,
        `@Argument`, `DataFetcherExceptionResolver`, `GraphQlTester`), DGS, and the schema-first vs
        code-first choice. `[API]` `[RESEARCH]`
1.27.19 The REST-vs-GraphQL-vs-gRPC decision table on the axes that actually decide it: client
        diversity, caching need, read/write ratio, streaming, public vs internal, team maturity,
        and observability cost. `[TABLE]`
1.27.20 When GraphQL is the wrong answer: a single first-party client, a write-heavy transactional
        API, anything needing HTTP caching or CDN, a team without query-cost governance, and
        anything where per-field authorisation would be safety-critical. `[PROVE]` `[TRAP]`
1.27.21 The QuizStakes application: the operator console needs a client's application, documents,
        restrictions, positions, deposits and withdrawals in one view across **nine services and two
        schemas** — which is the textbook GraphQL/BFF case. And the counter-argument: the same view
        is better served by a purpose-built **read model** (scenario § 7.4, § C.5), because the
        composition is known and fixed. Argue both sides. `[SOURCE]` `[PROVE]` `[X-REF 15]`

*(21 leaves)*

## §1.28 The Spring surface for an HTTP API

1.28.1 `@RestController` = `@Controller` + `@ResponseBody`, and what the second one actually changes
      (view resolution is skipped and an `HttpMessageConverter` writes the return value).
      `[API]` `[X-REF 07]`
1.28.2 The mapping annotations and every attribute that matters: `@RequestMapping`'s `path`,
      `method`, `params`, `headers`, `consumes`, `produces`, and (in 7.0) `version`; plus
      `@GetMapping`/`@PostMapping`/`@PutMapping`/`@PatchMapping`/`@DeleteMapping`. `[API]`
1.28.3 The argument resolvers you will use: `@PathVariable` (and `Map<String,String>`),
      `@RequestParam` (and `MultiValueMap`), `@RequestBody`, `@RequestHeader`, `@CookieValue`,
      `@RequestPart`, `HttpEntity<T>`, `@ModelAttribute`, `UriComponentsBuilder`,
      `ServletWebRequest`, and `Principal`/`@AuthenticationPrincipal`. `[API]` `[TABLE]`
1.28.4 Return types and what each produces: a POJO/record, `ResponseEntity<T>` (the only way to set
      status and headers precisely), `void` + `@ResponseStatus`, `Optional<T>` (→ 404 semantics only
      if you write them), `CompletableFuture<T>`, `DeferredResult<T>`, `Callable<T>`,
      `StreamingResponseBody`, `SseEmitter`, `ResponseBodyEmitter`, and reactive `Mono`/`Flux`.
      `[TABLE]` `[API]`
1.28.5 `ResponseEntity` builders you should know cold: `ok()`, `created(URI)`, `noContent()`,
      `accepted()`, `status(HttpStatus)`, `.eTag()`, `.location()`, `.cacheControl(CacheControl)`,
      `.lastModified()`, `.headers()`, `.build()`, `.body()`. Plus `CacheControl.maxAge`,
      `noStore`, `noCache`, `cachePrivate`, `cachePublic`, `mustRevalidate`,
      `staleWhileRevalidate`, `staleIfError`. `[API]`
1.28.6 `HttpMessageConverter` and content negotiation in practice:
      `MappingJackson2HttpMessageConverter`, `StringHttpMessageConverter`,
      `ByteArrayHttpMessageConverter`, `ResourceHttpMessageConverter`, and how `produces` narrows the
      choice. `[API]` `[X-REF 07]`
1.28.7 Jackson configuration as contract configuration, not preference: `PropertyNamingStrategies.
      SNAKE_CASE`, `@JsonProperty`, `@JsonInclude(NON_NULL)`, `@JsonIgnore`, `@JsonView`,
      `FAIL_ON_UNKNOWN_PROPERTIES` (default **true** — the intolerant-reader default),
      `WRITE_DATES_AS_TIMESTAMPS` (Boot sets it **false**), `JavaTimeModule`, and
      `spring.jackson.*` properties. `[API]` `[NUM]` `[TRAP]`
1.28.8 Jackson 3 in Spring Framework 7 / Boot 4: the package move to `tools.jackson`, changed
      defaults, and why every `com.fasterxml.jackson` import in a tutorial is now version-specific.
      `[VERSION-TRAP]` `[RESEARCH]`
1.28.9 Java 21 records as DTOs: constructor binding, Jackson support, why `@Valid` works on a record,
      compact canonical constructors for validation, and the one gotcha — a record cannot be a JPA
      entity, so it forces the DTO/entity split you wanted anyway. `[API]` `[X-REF 04]`
      `[X-REF 08]`
1.28.10 Validation: `@Valid` vs `@Validated`, the constraint set (`@NotNull`, `@NotBlank`,
        `@NotEmpty`, `@Size`, `@Min`/`@Max`, `@Positive`, `@DecimalMin`, `@Digits`, `@Pattern`,
        `@Email`, `@Past`/`@Future`, `@AssertTrue`), groups, custom
        `ConstraintValidator`, cross-field validation at the class level, and the exception each path
        throws. `[API]` `[TABLE]`
1.28.11 Exception handling: `@ExceptionHandler`, `@RestControllerAdvice` (with `basePackages`,
        `assignableTypes`, `annotations`), `ResponseEntityExceptionHandler`, `@ResponseStatus`,
        `ErrorResponse`/`ErrorResponseException`, `ProblemDetail`, and Boot's `/error` +
        `ErrorAttributes`. `[API]`
1.28.12 The built-in exceptions and the statuses Spring already maps them to, so you do not
        double-handle: `HttpRequestMethodNotSupportedException` → 405,
        `HttpMediaTypeNotSupportedException` → 415, `HttpMediaTypeNotAcceptableException` → 406,
        `MissingServletRequestParameterException` → 400, `MethodArgumentTypeMismatchException` → 400,
        `MethodArgumentNotValidException` → 400, `HttpMessageNotReadableException` → 400,
        `NoResourceFoundException` → 404, `ErrorResponseException` → its own status,
        `AsyncRequestTimeoutException` → 503. `[TABLE]` `[API]` `[RESEARCH]`
1.28.13 Filters vs interceptors vs advice vs aspects, and which layer each API concern belongs in:
        idempotency (filter — needs the raw body), rate limiting (filter or gateway), auth (security
        filter chain), tracing (filter), audit (interceptor), validation (advice), business rules
        (service). `[TABLE]` `[X-REF 07]`
1.28.14 `OncePerRequestFilter` and the body-reading problem: an `HttpServletRequest` input stream is
        read-once, so an idempotency or signature filter needs
        `ContentCachingRequestWrapper`/`ContentCachingResponseWrapper` — and that buffers the body in
        memory, which is a size limit you must set. `[API]` `[TRAP]` `[NUM]`
1.28.15 The outbound side: `RestClient` (6.1+, the modern synchronous choice), `WebClient`
        (reactive), declarative HTTP interfaces (`@HttpExchange`, `@GetExchange`,
        `HttpServiceProxyFactory`), and `RestTemplate` (maintenance mode, not deprecated).
        Timeouts, `ClientHttpRequestInterceptor`, `RestClient.Builder.defaultHeader`, and error
        handling via `onStatus`. `[API]` `[VERSION-TRAP]`
1.28.16 Timeouts on the client that you must set because the defaults are wrong: connect timeout,
        read timeout, and the fact that **no timeout is the default** on several combinations —
        which turns one slow dependency into thread exhaustion. `[TRAP]` `[NUM]` `[X-REF 10]`
1.28.17 Resilience at the boundary: Resilience4j `@CircuitBreaker`, `@Retry`, `@RateLimiter`,
        `@Bulkhead`, `@TimeLimiter`; Spring Retry's `@Retryable`/`@Recover`; and Spring Framework
        7's built-in `@Retryable`/`@ConcurrencyLimit`. The rule that **retry must be paired with
        idempotency** or it is a duplication engine. `[API]` `[PROVE]` `[VERSION-TRAP]`
1.28.18 Async MVC: `DeferredResult`, `Callable`, `spring.mvc.async.request-timeout`,
        `AsyncRequestTimeoutException` → 503, and how **virtual threads**
        (`spring.threads.virtual.enabled=true`) change the long-polling arithmetic. `[API]`
        `[X-REF 04]` `[NUM]`
1.28.19 SSE in Spring: `SseEmitter`, `MediaType.TEXT_EVENT_STREAM_VALUE`,
        `SseEmitter.event().id().name().data().reconnectTime()`, completion and error callbacks, and
        the timeout/heartbeat requirement. `[API]`
1.28.20 WebSocket in Spring: `WebSocketHandler`, `@EnableWebSocketMessageBroker`,
        `@MessageMapping`, `SimpMessagingTemplate`, `@SendTo`, the simple broker vs a relay
        (RabbitMQ/ActiveMQ STOMP), and `HandshakeInterceptor` for auth. `[API]`
1.28.21 Testing the contract: `@WebMvcTest` + `MockMvc`, `MockMvcTester` (6.2+), `@SpringBootTest` +
        `TestRestTemplate`/`WebTestClient`, JSON assertions with JSONPath and JSONAssert,
        `swagger-request-validator` against the OpenAPI document, WireMock for the outbound side,
        and Spring Cloud Contract / Pact for consumer-driven contracts. `[API]` `[X-REF 16]`
1.28.22 The QuizStakes controller skeleton the bible must show once, complete: a
        `DepositController` with `@PostMapping` returning `201` + `Location`, an
        `Idempotency-Key` header, `@Valid` on a record request, an `If-Match` on the state
        transition, a `ProblemDetail` advice, an SSE endpoint for run progress, and a cursor-paged
        list. `[BUILD]` `[API]`

*(22 leaves)*

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master method table**: method × safe × idempotent × cacheable × body allowed × typical
      success code × typical failure codes × needs an idempotency key. Every row includes `QUERY`.
      `[TABLE]`
2.1.2 **The master status-code table**: every code from §1.8 × class × "what the client should do"
      × required companion header × retryable × typical cause in QuizStakes. `[TABLE]`
2.1.3 **The master header table**: field name × request/response × Structured Field type × who reads
      it (client, cache, gateway, server) × required companion. `[TABLE]`
2.1.4 **The master cost table** — the single required table for this topic. For each API mechanism,
      the per-request cost split into *typical* and *worst case*, with the resource consumed named:
      plain GET, conditional GET hit (`304`), conditional GET miss, offset page at depth 1 / 1,000 /
      100,000, cursor page, idempotency-key first attempt, idempotency-key replay, rate-limit check
      local, rate-limit check via Redis, ETag computation by body hash, ETag by version column,
      JSON serialisation per KB, protobuf serialisation per KB, gzip per KB, TLS handshake, HTTP/2
      stream setup, webhook delivery attempt, SSE connection held per client, WebSocket connection
      held per client, GraphQL query with and without DataLoader. Each with the QuizStakes volume
      multiplier applied. `[TABLE]` `[NUM]` `[PROVE]`
2.1.5 **The payload-size table**: a QuizStakes deposit representation in JSON verbose, JSON minified,
      JSON gzipped, protobuf, protobuf gzipped — with the byte arithmetic shown field by field.
      `[TABLE]` `[NUM]` `[PROVE]`
2.1.6 **The style comparison table**: REST / gRPC / GraphQL / SSE / WebSocket / webhooks across
      twelve axes (caching, streaming, browser, schema, codegen, human-debuggable, intermediary
      support, versioning story, latency, payload size, observability cost, ops burden). `[TABLE]`
2.1.7 **The pagination table**: offset / keyset / seek / snapshot / time-window across cost at depth,
      stability, total count, jump-to-page, resumability, server state. `[TABLE]`
2.1.8 **The versioning table**: URI / media type / custom header / query param / date-based across
      seven axes. `[TABLE]`
2.1.9 **The rate-limit algorithm table**: token bucket / leaky bucket / fixed window / sliding log /
      sliding counter / GCRA across burst, accuracy, memory, boundary behaviour, distributed cost.
      `[TABLE]`
2.1.10 **The breaking-change table**: change × breaking for a strict client × breaking for a
       tolerant client × detectable by `oasdiff` × detectable by `buf breaking`. `[TABLE]`
2.1.11 **The PATCH format table**: JSON Patch / Merge Patch / partial-JSON / field mask across
       expressiveness, arrays, null semantics, idempotency, atomicity, readability, tooling.
       `[TABLE]`
2.1.12 **The QuizStakes endpoint inventory**: every endpoint the bible designs, with method, path,
       success code, error codes, idempotency requirement, pagination scheme, cache policy, auth
       requirement and rate-limit key. This is the artifact a reader can copy into an interview.
       `[TABLE]`

*(12 leaves)*
## §2.2 Choosing the style — the decision procedure

2.2.1 The question order that makes the decision fall out, as a checklist rather than a preference:
      who calls it, can they be recompiled with you, is there a trust boundary, is the read shape
      known at design time, does anything stream, does an intermediary need to cache it, what is the
      latency budget, and who operates the client. `[FLOW]`
2.2.2 The "one API, two faces" pattern: gRPC internally with a generated REST facade
      (grpc-gateway / AIP-127 transcoding) externally. What it buys and the one thing it costs —
      your external contract is now a projection of an internal one, so internal refactors leak.
      `[PROVE]`
2.2.3 The BFF pattern properly stated: one backend **per client type**, owned by the client team,
      composing the domain APIs. Not a shared gateway. Its cost is duplication; its benefit is that
      the mobile team can change their payload without a domain-team ticket. `[PROVE]` `[RESEARCH]`
2.2.4 When *not* to add a BFF: one client, a stable payload, or a team that will not own it. An
      unowned BFF becomes a distributed monolith. `[TRAP]`
2.2.5 The three-axis trade-off drill the bible must run for each style choice: latency vs
      operability vs client-diversity; and separately, contract stability vs iteration speed vs
      payload efficiency. `[PROVE]`
2.2.6 Migrating styles under live traffic: REST → gRPC internally with a dual-write/dual-read period;
      REST → GraphQL with the graph as a facade over the existing endpoints first. `[FLOW]`
      `[X-REF 22]`

*(6 leaves)*

## §2.3 Idempotency in practice

2.3.1 The endpoint-by-endpoint audit: for every write endpoint, state whether a retry is safe today,
      and if not, which of the four fixes applies (natural unique key, client-supplied key, a
      client-chosen URI with PUT, or a state check). `[TABLE]` `[FLOW]`
2.3.2 The **natural-key** fix, which is always preferable when available: a `UNIQUE` constraint on
      `(client_id, payment_reference)` makes the operation idempotent with no extra table.
      `[PROVE]` `[X-REF 09]`
2.3.3 The **PUT-with-client-chosen-URI** fix: `PUT /reservations/{clientGeneratedId}` is idempotent
      by protocol and needs no key mechanism at all. Why more APIs should do this. `[PROVE]`
2.3.4 The **state-check** fix and why it is the weakest: "if already `CAPTURED`, return success" is
      a read-then-act race unless it is inside the same transaction as the write. `[TRAP]`
      `[PROVE]` `[X-REF 05]`
2.3.5 Idempotency across a distributed boundary: the key must be passed to the downstream provider,
      and if the provider has no key mechanism you must reconcile. Name the two reconciliation
      patterns — periodic sweep against the provider's records, and a provider-side query-by-
      reference before retry. `[PROVE]` `[X-REF 14]`
2.3.6 The **outbox** as the idempotency mechanism for *events*: the side effect and the event row
      commit together, so a retry cannot publish twice without also duplicating the effect.
      One paragraph here, full treatment in 14. `[X-REF 14]` `[PROVE]`
2.3.7 Testing idempotency: the three tests every keyed endpoint needs — same key twice returns the
      identical response, same key with a different body returns `422`, and two concurrent requests
      with the same key produce exactly one effect. The third needs a real concurrency test, not a
      mock. `[X-REF 16]` `[BUILD]`
2.3.8 Observability of idempotency: a counter for replays, a counter for `409`s, a counter for
      `422` key-reuse, and the key-table size. A replay rate that jumps is a client bug or a network
      problem, and you want to see it. `[X-REF 20]` `[PROVE]`
2.3.9 The key-table growth arithmetic: at 95k card deposits/day plus 2.8M stake reservations/day,
      a 7-day retention with a ~1 KB stored response is ~20 GB. Show the arithmetic and the three
      mitigations (shorter TTL, store only the status and a pointer, partition by day and drop
      partitions). `[NUM]` `[PROVE]` `[X-REF 09]`

*(9 leaves)*

## §2.4 Pagination in practice

2.4.1 The migration from offset to cursor without breaking clients: accept both parameters, return
      both `page` and `next_cursor` during transition, instrument which clients still send `page`,
      then deprecate. `[FLOW]` `[PROVE]`
2.4.2 Cursor stability under a schema change: because the cursor is opaque and versioned, you can
      change the sort tuple — but an in-flight old cursor must still decode or fail cleanly with a
      documented `400`, not a `500`. `[TRAP]`
2.4.3 Paginating across two stores, which is the QuizStakes withdrawal problem: you cannot
      offset-paginate a union, and a cursor must encode a position in *each* source. The three
      answers — merge-sort with a composite cursor, a materialised read model, or "page each source
      separately and let the client merge". `[PROVE]` `[SOURCE]` `[X-REF 15]`
2.4.4 Paginating a filtered aggregate where the filter is expensive: pre-compute, cap the result set,
      or return an estimated total with an explicit flag. `[X-REF 09]`
2.4.5 The deep-pagination denial-of-service: `?page=500000&size=200` on an unindexed sort is a table
      scan per request. Cap the reachable depth (GitHub caps search at 1,000 results) and say so in
      the error. `[NUM]` `[TRAP]` `[PROVE]`
2.4.6 Consistency guarantees you can actually promise: with cursor pagination, "no duplicates and no
      skips for rows that existed at the start and were not modified" — and nothing about rows
      inserted mid-iteration. State the promise; do not imply a snapshot you do not have.
      `[PROVE]` `[TRAP]`
2.4.7 Testing pagination: the properties worth asserting — every item appears exactly once across a
      full traversal, insertion during traversal does not duplicate an item, the last page is
      identifiable, and `limit` is clamped. `[X-REF 16]`

*(7 leaves)*

## §2.5 Compatibility in practice

2.5.1 The compatibility policy as a **written, published document**: which changes you promise never
      to make, what notice you give, and how the client is expected to behave. Without it, "breaking"
      is a matter of opinion during an incident. `[PROVE]`
2.5.2 The tolerant-reader obligation, published and enforced: unknown fields ignored, unknown enum
      values mapped to a documented fallback, no dependence on field order, and a stated
      absent-vs-null rule. Plus the enforcement mechanism — a conformance test suite you give to
      integrators. `[PROVE]`
2.5.3 The **CI gate**: generate the spec, `oasdiff` against the released spec, fail on breaking.
      For protobuf, `buf breaking` with the category matching your promise. This is the single
      highest-leverage practice in the whole topic. `[FLOW]` `[PROVE]` `[RESEARCH]`
2.5.4 Consumer-driven contract testing as the complement: the consumer publishes what it actually
      uses, and the provider's build fails when it breaks a real consumer rather than a hypothetical
      one. Where it beats schema diffing (it catches semantic breaks) and where it is worse (only
      known consumers). `[TABLE]` `[X-REF 16]`
2.5.5 Field-usage telemetry as the third leg: instrument which fields are actually read (trivial in
      GraphQL, hard in REST — sample response serialisation or require projection). You cannot
      safely remove what you cannot measure. `[PROVE]` `[X-REF 20]`
2.5.6 The **GitHub REST versioning incident** as the case study: production behaviour on an existing
      endpoint diverged from the published OpenAPI schema and documented HTTP semantics, breaking
      downstream tooling that treated the schema and status codes as the source of truth. The lesson
      is that *the spec is the contract*, and drift between implementation and spec is a breaking
      change even when the code "works". `[SOURCE]` `[RESEARCH]`
2.5.7 The enum-value incident pattern: a provider adds `IN_PROGRESS` to a status enum; a strict
      generated client throws on deserialisation; the mobile app crashes on a state it has never
      seen. The fix on both sides — open enums server-side, fallback values client-side. `[TRAP]`
      `[PROVE]` `[RESEARCH]`
2.5.8 The "optional field that was actually required" pattern: a field documented as optional that
      every client happened to send, then a client stops sending it and the server 500s. Nullability
      must be tested, not documented. `[TRAP]`
2.5.9 Deprecation without removal as a legitimate end state: some fields you keep forever because the
      cost of removal exceeds the cost of carrying them. Say so explicitly rather than pretending a
      sunset will happen. `[PROVE]`
2.5.10 The QuizStakes worked migration: splitting the unified withdrawal vocabulary into two
       schema-specific representations behind one contract, using expand/contract, with the
       compatibility gate, the telemetry and the sunset schedule spelled out. `[FLOW]` `[SOURCE]`

*(10 leaves)*

## §2.6 Error contracts in practice

2.6.1 Designing the problem-type taxonomy: one `type` per *client action*, not one per exception
      class. If two problems require the same client response, they are one type. `[PROVE]`
2.6.2 The granularity trap in both directions: too coarse (`/problems/bad-request` for everything —
      the client can do nothing with it) and too fine (a type per validation rule — an unmaintainable
      registry). `[TRAP]`
2.6.3 Mapping domain errors to HTTP without leaking the domain: the QuizStakes `DEP-*`/`AA-*` codes
      go in the body as a stable `code` extension; the HTTP status is chosen from the client-action
      table. Show the mapping layer as code. `[PROVE]` `[BUILD]`
2.6.4 The exception-to-response layer as an architectural boundary: domain exceptions must not know
      about HTTP, so the translation lives in the web layer. What happens when it does not — a
      service throwing `ResponseStatusException` is a layering violation that becomes visible the
      first time you expose the same service over gRPC. `[PROVE]` `[TRAP]`
2.6.5 The validation-error payload, fully specified: `errors: [{field, code, message, rejectedValue?}]`
      with a JSON Pointer for nested paths (`/lines/0/amount`), and the decision about whether to
      echo `rejectedValue` (helpful, and a PII leak for a card number). `[PROVE]` `[TRAP]`
2.6.6 Errors from a downstream dependency: never pass through the upstream body, never pass through
      the upstream status blindly. `502` for a bad response, `504` for a timeout, `503` for a
      circuit open — and always a problem `type` of your own. `[PROVE]` `[TRAP]`
2.6.7 Testing the error contract: a test per problem type asserting status, `Content-Type`, `type`
      URI and the presence of the trace id; plus a test that no 5xx response contains a stack trace.
      `[X-REF 16]`
2.6.8 Observability of errors: split 4xx by `type` and by caller so a spike in one client's
      validation failures is visible, and alert on 5xx rate rather than count. `[X-REF 20]`
2.6.9 The support workflow the contract must enable, end to end: user sees an error → pastes the
      `instance`/trace id → you find the request in logs and the trace in the tracing backend →
      you see which downstream failed. Write the whole chain out; it is what "operable API" means.
      `[FLOW]` `[X-REF 20]`

*(9 leaves)*

## §2.7 Rate limiting and quotas in practice

2.7.1 Choosing the numbers, which is the part always skipped: derive the limit from capacity, not
      from a round number. With three `FundsLedger` instances, a 150 ms stake-reservation budget and
      3,400/sec settlement bursts, what is the defensible per-client limit? Show the arithmetic.
      `[NUM]` `[PROVE]`
2.7.2 Different limits for different endpoints, because cost differs by orders of magnitude: a
      cursor page read vs a stake reservation vs an export job. Weighted cost accounting
      ("this endpoint costs 10 tokens") as the generalisation. `[PROVE]`
2.7.3 Tenant fairness vs global protection: a per-tenant limit prevents one noisy tenant, and a
      global admission controller prevents all tenants together. You need both. `[PROVE]`
      `[X-REF 22]`
2.7.4 Burst allowance as a product decision: a mobile app that syncs on resume needs a burst; an
      abusive scraper looks identical. What distinguishes them (authenticated identity, historical
      pattern) and what does not (rate alone). `[PROVE]`
2.7.5 Rollout without breaking anyone: observe-only mode first (count what *would* have been
      rejected), then per-client allowlists, then enforcement. Never ship a limit straight to
      enforce. `[FLOW]` `[PROVE]`
2.7.6 Communicating limits: documentation, the response headers, a dashboard for the integrator, and
      a `429` body that names the violated policy. `[PROVE]`
2.7.7 The retry-storm failure mode: every client hits `429`, every client retries after exactly
      `Retry-After` seconds, and the next second is a synchronised thundering herd. **Jitter is not
      optional** — prove that full jitter flattens the spike. `[PROVE]` `[TRAP]` `[X-REF 15]`
2.7.8 Rate limiting an unauthenticated endpoint you cannot key well: the login and
      instrument-verification endpoints. IP plus account plus a proof-of-work or CAPTCHA escalation,
      and the honest admission that IP-only is defeatable. `[TRAP]` `[X-REF 13]`

*(8 leaves)*

## §2.8 Caching in practice

2.8.1 The decision procedure per endpoint: is the response identical for all callers (public
      cacheable), identical per caller (private), or unique per request (no-store)? That one question
      determines every header. `[FLOW]`
2.8.2 The three-layer cache picture and who owns each: CDN/edge (public reference data), the API
      gateway or service cache (per-caller computed results), and the client. Where an ETag helps at
      each layer. `[TABLE]` `[X-REF 15]`
2.8.3 Cache-key design when the response depends on the caller's permissions: `Vary: Authorization`
      makes the shared cache useless, so either move the permission check outside the cached
      fragment or cache per-principal deliberately. `[PROVE]` `[TRAP]`
2.8.4 Invalidation strategies at the API layer: TTL only (simple, stale), event-driven purge (fast,
      needs a purge API and a reliable event), and versioned URLs (perfect, requires clients to
      re-read a pointer). `[TABLE]` `[X-REF 15]`
2.8.5 The stale-data incident pattern: a CDN caches an authenticated response because the origin
      omitted `Cache-Control`, and one client's balance is served to another. The fix and the
      defence in depth (`private, no-store` by default at the framework level, opt-in per endpoint).
      `[TRAP]` `[PROVE]`
2.8.6 Conditional GETs as a bandwidth-and-battery optimisation for mobile: the arithmetic on a
      polling client — a `304` is ~200 bytes against a ~4 KB representation, so a 20× reduction on
      the common case. `[NUM]` `[PROVE]`
2.8.7 The read-model / CQRS answer when caching is not enough: the QuizStakes composite view is not a
      cache problem, it is a projection problem. State the boundary between the two. `[SOURCE]`
      `[X-REF 15]` `[X-REF 22]`

*(7 leaves)*

## §2.9 Timeouts, retries and backpressure at the API boundary

2.9.1 Timeout budgets as a contract: publish a per-endpoint SLO, set the server-side timeout below
      the client's, and make the budget **decrease** down the call chain so an inner call cannot
      outlive its caller. `[PROVE]` `[NUM]` `[X-REF 10]`
2.9.2 Deadline propagation in HTTP, which has no standard mechanism: the options are a custom
      header (`X-Request-Deadline`), `grpc-timeout` if you are on gRPC, or nothing — and "nothing" is
      why a cancelled client request keeps burning server capacity. `[TRAP]` `[PROVE]`
2.9.3 Retry policy design: which status codes are retryable (`408`, `429`, `502`, `503`, `504`, plus
      connect errors), which are not (`400`, `401`, `403`, `404`, `409`, `422`), exponential backoff
      with full jitter, a total attempt cap and a total time cap. `[TABLE]` `[PROVE]`
2.9.4 **Retry amplification**, proved: three layers each retrying three times is 27 requests from one
      client action. Retry at exactly one layer, and make it the outermost one that can be
      idempotent. `[PROVE]` `[TRAP]` `[NUM]`
2.9.5 Retry budgets and adaptive retry (retry only if the recent success rate is high enough) as the
      fix for retries making an overload worse. `[PROVE]` `[X-REF 22]`
2.9.6 Circuit breakers at the API boundary: what the client sees when the breaker is open (`503` +
      `Retry-After`), and the half-open probe. `[X-REF 22]`
2.9.7 Backpressure at the API layer: bounded queues, a concurrency limit, `429`/`503` as the
      backpressure signal, and the rule that **queueing without a bound is a latency bomb**.
      `[PROVE]` `[X-REF 05]` `[X-REF 22]`
2.9.8 Client cancellation: what HTTP gives you (connection close, HTTP/2 `RST_STREAM`), what Spring
      MVC does with it (usually nothing — the handler runs to completion), and why a 30-second query
      whose client left is pure waste. `[TRAP]` `[X-REF 10]`
2.9.9 The QuizStakes budget chain, worked: 500 ms self-exclusion hard budget → gateway timeout → the
      restriction call's 30 ms budget → the ledger's 150 ms reservation budget. Show what each hop
      may spend and what happens on overrun. `[NUM]` `[FLOW]` `[SOURCE]`

*(9 leaves)*

## §2.10 Webhooks in practice

2.10.1 The registration contract: per-endpoint secrets, event-type subscription, URL validation at
       registration (a challenge-response handshake), and endpoint verification before first
       delivery. `[FLOW]`
2.10.2 The delivery pipeline architecture: an outbox → a queue → workers → per-endpoint rate limiting
       → an attempt log. Why the outbox is required (the event must not exist without the state
       change, and vice versa). `[FLOW]` `[X-REF 14]` `[PROVE]`
2.10.3 The retry schedule as a published number: e.g. 5 s, 5 min, 30 min, 2 h, 5 h, 10 h, … spanning
       ~75 hours with jitter (Standard Webhooks' example). Publish it so the consumer can reason
       about duplicates. `[NUM]` `[RESEARCH]`
2.10.4 Automatic disabling: after N consecutive failures or T hours of failure, disable and notify.
       `410 Gone` from the consumer means disable immediately. What the re-enable flow is.
       `[NUM]` `[RESEARCH]`
2.10.5 The delivery log as a product feature: every attempt with request headers, body, response
       status, response body (truncated) and timing, visible to the customer, with a **replay**
       button. This is the difference between a webhook you can support and one you cannot.
       `[PROVE]`
2.10.6 Key rotation with zero downtime: send two signatures in `webhook-signature` during the
       overlap window, and document the verification rule (accept if *any* signature matches).
       `[PROVE]` `[RESEARCH]`
2.10.7 Fan-out arithmetic: one `DEP-500` event to 200 subscribed endpoints is 200 HTTP requests with
       independent retry state. Size the worker pool and the queue, and cap per-endpoint
       concurrency so one slow consumer cannot starve the rest. `[NUM]` `[PROVE]`
2.10.8 The slow-consumer failure mode: a consumer that takes 25 s per delivery, at 15–30 s timeouts,
       consumes a worker for the whole window. The fix — per-endpoint concurrency caps and a
       dedicated slow lane. `[TRAP]` `[PROVE]`
2.10.9 Testing webhooks on both sides: a local receiver (`ngrok`, `webhook.site`), a signature
       fixture with a known secret and a fixed timestamp, a replay test, and a clock-skew test.
       `[X-REF 16]`
2.10.10 The inbound side in QuizStakes: PSP callbacks arriving for `DEP-500`/`DEP-690` months after
        the deposit, with signature verification, timestamp tolerance, idempotency on the provider's
        event id, and an "unknown reference" path that must not 500 — because a `BDP-150
        UNMATCHED_SUSPENSE` equivalent is a legitimate outcome. `[SOURCE]` `[PROVE]`

*(10 leaves)*
## §2.11 The edge — gateway, BFF and what belongs where

2.11.1 The API gateway's legitimate responsibilities, enumerated: TLS termination, routing,
       authentication (verify the token once), rate limiting, request/response transformation,
       protocol translation, request validation against the spec, observability injection, and
       selective aggregation. `[TABLE]` `[RESEARCH]`
2.11.2 What must **not** move into the gateway: object-level authorisation, business validation,
       domain state transitions, and anything that needs the resource to decide. The
       "**mega-gateway**" anti-pattern is exactly this drift. `[TRAP]` `[PROVE]` `[RESEARCH]`
2.11.3 "Verify once, propagate" and its risk: downstream services trusting injected headers
       (`X-User-Id`) means **any** path that reaches the service without the gateway is a full
       authentication bypass. Name the mitigations — network policy, mTLS, and a signed internal
       token. QuizStakes does the last one: the client token is stripped and an application token
       issued. `[TRAP]` `[SOURCE]` `[X-REF 13]` `[X-REF 19]`
2.11.4 The gateway-as-single-point-of-failure question, and the honest answer: it is one, and the
       mitigations are horizontal scale, health-check-driven removal, and a bypass path for
       break-glass. `[X-REF 22]`
2.11.5 Where rate limiting, caching, retries and circuit breaking belong when you have both a
       gateway and a service mesh: a responsibility table, because doing it in both places
       multiplies the effect. `[TABLE]` `[X-REF 19]`
2.11.6 API composition at the edge vs a read model: the gateway aggregating five calls has the
       latency of the slowest and the availability of the product of all five. Show the arithmetic —
       five dependencies at 99.9% is 99.5%. `[NUM]` `[PROVE]` `[X-REF 22]`
2.11.7 The QuizStakes routing map as the concrete example: `ApplicationGateway` for clients
       (strip + re-issue), `InternalPlatforms` for operators (strip + re-issue + **role check** +
       record the role exercised), `RouterInt` with three strategies — least-connections for the
       stateless services, session affinity for `InternalPlatforms`, partition affinity by client id
       for `FundsLedger`. Restate the honest caveat: **affinity buys state locality, not
       correctness**, and it costs rebalancing. `[SOURCE]` `[PROVE]` `[TABLE]`

*(7 leaves)*

## §2.12 Observing and operating an API

2.12.1 The four golden signals expressed as API metrics: latency (p50/p95/p99 **per endpoint**, never
       aggregate), traffic (RPS per endpoint per caller), errors (4xx and 5xx **split**, by problem
       type), saturation (in-flight requests, queue depth, pool utilisation). `[TABLE]`
       `[X-REF 20]`
2.12.2 Why aggregate latency lies: one slow endpoint at 1% of traffic is invisible in a global p99.
       Label by route template (`/deposits/{id}`, never the expanded path — that is a cardinality
       explosion). `[TRAP]` `[NUM]` `[X-REF 20]`
2.12.3 The metrics an API should emit that most do not: idempotency replay rate, rate-limit rejection
       rate by key, cursor-page depth distribution, payload-size distribution, deprecated-endpoint
       usage **per caller**, and per-field read counts. `[PROVE]`
2.12.4 Micrometer/Spring specifics: `http.server.requests` with `uri`/`method`/`status`/`outcome`
       tags, `management.metrics.tags`, `@Timed`, `ObservationRegistry`, and the URI-templating rule
       that prevents cardinality blowup. `[API]` `[X-REF 20]`
2.12.5 Tracing an API call end to end: `traceparent` in, span per hop, the `instance`/trace id in the
       error body, and the support workflow from §2.6.9. `[X-REF 20]`
2.12.6 Access logs as an API artifact: what to log (method, route template, status, duration, caller
       id, trace id, response size, idempotency key **hash**), what never to log (bodies, tokens,
       PANs, full query strings with secrets). `[TRAP]` `[X-REF 13]`
2.12.7 Health and readiness as part of the contract: `/actuator/health` with liveness vs readiness
       groups, and the rule that a readiness probe must reflect dependencies while a liveness probe
       must not (or a dependency outage restarts your fleet). `[TRAP]` `[X-REF 19]`
2.12.8 Synthetic monitoring and contract canaries: a scheduled job exercising the documented happy
       path of every public endpoint, asserting the *contract* (status, headers, schema) rather than
       liveness. `[PROVE]`
2.12.9 The API-inventory problem (OWASP's "improper inventory management"): undocumented endpoints,
       forgotten `/v1`, staging hosts on the internet, and the discovery techniques — gateway route
       dumps, `RequestMappingHandlerMapping` introspection, spec-vs-runtime diffing. `[TRAP]`
       `[API]` `[RESEARCH]`
2.12.10 Runtime inspection of your own API surface: `/actuator/mappings`, `/v3/api-docs`,
        `curl -v` reading, `grpcurl -plaintext … describe`, and browser devtools' network panel as
        the fastest contract-debugging tool that exists. `[DIAG]` `[API]`

*(10 leaves)*

## §2.13 Governance, style and developer experience

2.13.1 Why a style guide exists: consistency is worth more than optimality because a caller learns
       your API once and applies it everywhere. Zalando's guidelines exist for exactly this reason.
       `[PROVE]` `[SOURCE]`
2.13.2 The MUST/SHOULD/MAY discipline (RFC 2119 keywords) applied to internal rules, and why a rule
       without a level is unenforceable. `[SOURCE]`
2.13.3 The chapter structure of a real style guide, as a template to steal: principles, terminology,
       general, meta-information, security, data formats, URLs, JSON payload, HTTP requests, HTTP
       status codes, HTTP headers, hypermedia, performance, pagination, compatibility, deprecation,
       operation, events. `[SOURCE]` `[TABLE]` `[RESEARCH]`
2.13.4 Automated enforcement: Spectral/`zally` in CI on every spec change, and the practice of making
       the linter the arbiter so review is about design, not commas. `[PROVE]`
2.13.5 The API design review as a process: what artifacts are required (the spec, the use cases, the
       compatibility promise), who reviews, and the questions the review asks. Google's AIP-100 API
       Design Review FAQ as prior art. `[RESEARCH]`
2.13.6 Developer experience as an engineering concern: time-to-first-successful-call as the metric,
       and the things that move it — a copy-pasteable curl, a sandbox with test credentials,
       idempotent test data, clear errors, and an SDK. `[PROVE]`
2.13.7 SDKs: generated vs hand-written, versioning the SDK independently of the API, and the
       obligation an SDK creates (you now own retry, backoff and idempotency-key generation on
       behalf of every caller). `[PROVE]`
2.13.8 The naming decisions worth centralising once so nobody re-litigates them: casing, date format,
       money representation, pagination parameter names, sort syntax, filter syntax, error envelope,
       id format, and enum casing. `[TABLE]`
2.13.9 Google's AIP catalogue as a completeness checklist to run your own guide against — the full
       index by number: AIP-121 resource-oriented design, 122 resource names, 123 resource types,
       124 resource association, 126 enumerations, 127 HTTP/gRPC transcoding, 128
       declarative-friendly interfaces, 129 server-modified values, 130 methods, 131–135 standard
       Get/List/Create/Update/Delete, 136 custom methods, 140 field names, 141 quantities, 142 time
       and duration, 143 standardized codes, 144 repeated fields, 145 ranges, 146 generic fields,
       147 sensitive fields, 148 standard fields, 149 unset values, 151 long-running operations,
       152 jobs, 153 import/export, 154 resource freshness validation, 155 request identification,
       156 singleton resources, 157 partial responses, 158 pagination, 159 reading across
       collections, 160 filtering, 161 field masks, 162 resource revisions, 163 change validation,
       164 soft delete, 165 criteria-based delete, 180 backwards compatibility, 181 stability levels,
       184 API version identifiers, 185 API versioning, 190 naming conventions, 192 documentation,
       193 errors, 194 automatic retry configuration, 202 fields, 203 field behavior documentation,
       211 authorization checks, 214 resource expiration, 216 states, 217 unreachable resources,
       231/233/234/235 batch methods. `[SOURCE]` `[TABLE]` `[RESEARCH]`
2.13.10 **AIP-155 request identification** and **AIP-154 resource freshness validation** specifically,
        because they are the gRPC spellings of §1.17 and §1.13 — `request_id` and `etag` as message
        fields. `[RESEARCH]` `[PROVE]`
2.13.11 **AIP-164 soft delete** and **AIP-162 resource revisions**: `DELETE` that sets
        `delete_time`, `UndeleteX`, `show_deleted` on List, `expire_time`, and the revision suffix
        `name@revision`. The contract consequence — a soft-deleted resource still returns `404` to a
        normal read, or it does not, and you must say which. `[RESEARCH]` `[PROVE]`
2.13.12 Multi-tenancy in the contract: tenant in the path, in the token, or in a header. What each
       does to routing, caching and the risk of cross-tenant leakage. `[TABLE]` `[X-REF 13]`

*(12 leaves)*

## §2.14 Version delta — what changed and when

2.14.1 The HTTP timeline with dates, because a candidate who knows it sounds different: HTTP/1.0
       (RFC 1945, 1996), HTTP/1.1 (RFC 2068 → 2616, 1997/1999 → 7230–7235, 2014 → **9110–9112,
       2022**), HTTP/2 (RFC 7540, 2015 → **9113, 2022**), HTTP/3 (**RFC 9114, 2022**). `[NUM]`
       `[TABLE]`
2.14.2 The API-spec timeline: RFC 5789 PATCH (2010), RFC 6585 additional status codes (2012),
       RFC 6902/7396 patch formats (2013/2014), RFC 7807 problem details (2016), RFC 8288 links
       (2017), RFC 8594 Sunset (2019), RFC 8941 structured fields (2021), **RFC 9457 (2023,
       obsoletes 7807)**, RFC 9530 digest fields (2024), RFC 9421 message signatures (2024),
       RFC 9651 structured fields (2024), **RFC 9745 Deprecation (2025)**, **RFC 10008 QUERY
       (2026)**. `[NUM]` `[TABLE]` `[RESEARCH]`
2.14.3 The description-format timeline: Swagger 2.0 (2014), OpenAPI 3.0 (2017), 3.1 (2021),
       **3.2.0 (Sept 2025)**; JSON Schema draft-04 → 2019-09 → **2020-12**; AsyncAPI 2.x → 3.0.
       `[NUM]` `[RESEARCH]`
2.14.4 The still-in-draft set, and the honest way to talk about it: `Idempotency-Key` (draft-07,
       **expired April 2026**), `RateLimit`/`RateLimit-Policy` (draft-11, May 2026),
       GraphQL incremental delivery, Standard Webhooks (a community spec, not IETF). A draft is a
       convention, not a standard — say "widely implemented draft". `[VERSION-TRAP]` `[RESEARCH]`
2.14.5 The Spring timeline for this topic: `RestTemplate` → `WebClient` (5.0) → `RestClient`
       (6.1); `ProblemDetail`/`ErrorResponse` (6.0); `HandlerMethodValidationException` (6.1);
       `MockMvcTester` (6.2); **API versioning, built-in `@Retryable`, `@ConcurrencyLimit`,
       Jackson 3, JSpecify (7.0 / Boot 4.0, Nov 2025)**. `[VERSION-TRAP]` `[RESEARCH]`
2.14.6 The **stale-answer sweep list** — claims that were true, are commonly repeated, and are now
       wrong: "use RFC 7807"; "`Deprecation: true`"; "`RateLimit-Limit`/`-Remaining`/`-Reset` are the
       standard headers"; "you can't send a body with a safe method"; "GraphQL always returns 200";
       "Spring has no built-in API versioning"; "`nullable: true` in OpenAPI"; "server push solves
       the round-trip problem"; "HTTP/2 needs domain sharding"; "`422` is not a real HTTP code";
       "protobuf is 10× smaller than JSON" (before gzip). `[TABLE]` `[VERSION-TRAP]`

*(6 leaves)*

## §2.15 The anti-pattern catalogue

2.15.1 `200 OK` with an error body. `[TRAP]`
2.15.2 Verbs in URIs / RPC-over-HTTP pretending to be REST. `[TRAP]`
2.15.3 An unversioned, uncontracted, undocumented endpoint that three teams now depend on.
       `[TRAP]`
2.15.4 Exposing the database schema as the API (entity-as-DTO), with mass assignment and excessive
       data exposure as the two consequences. `[TRAP]`
2.15.5 Unbounded collection endpoints. `[TRAP]`
2.15.6 No idempotency on a money-moving POST. `[TRAP]`
2.15.7 Retrying a non-idempotent operation. `[TRAP]`
2.15.8 A chatty API forcing N+1 client round trips, and the over-correction (a god endpoint with
       `?include=everything`). `[TRAP]`
2.15.9 Inconsistent naming, casing, date formats and pagination across endpoints of the same API.
       `[TRAP]`
2.15.10 Leaking stack traces, SQL, hostnames or upstream vendor errors. `[TRAP]`
2.15.11 `null`-vs-absent ambiguity, and a `boolean` that needed to be an enum. `[TRAP]`
2.15.12 Breaking changes shipped as "minor": a tightened regex, a new required field, a removed enum
        value. `[TRAP]`
2.15.13 A synchronous endpoint doing 30 seconds of work behind a 30-second client timeout.
        `[TRAP]`
2.15.14 A `GET` with side effects. `[TRAP]`
2.15.15 Secrets in query strings; tokens in URLs shared in support tickets. `[TRAP]`
2.15.16 Custom auth schemes and hand-rolled signature verification with `==` string comparison.
        `[TRAP]` `[X-REF 13]`
2.15.17 The mega-gateway holding business logic. `[TRAP]`
2.15.18 Per-instance rate limiting presented as a global limit. `[TRAP]`
2.15.19 An error message as the machine-readable contract (clients parsing `detail`). `[TRAP]`
2.15.20 Documentation that is a wiki page maintained by hand, diverging from the running code.
        `[TRAP]`
2.15.21 Offset pagination on a live feed. `[TRAP]`
2.15.22 A webhook with no signature, no timestamp, no event id and no retry log. `[TRAP]`
2.15.23 `Optional<T>` as a JSON field type, and `Optional` in a request record. `[TRAP]`
        `[X-REF 04]`
2.15.24 Returning a `Page<Entity>` straight from a Spring Data repository through the controller —
        the Jackson-serialisation warning, the lazy-loading exception, and the contract you did not
        mean to publish. `[TRAP]` `[X-REF 08]`

*(24 leaves)*

---

# PART 3 — UNDER THE HOOD

## §3.1 A request on the wire, byte by byte

3.1.1 An HTTP/1.1 request and response for `POST /deposits` shown as literal bytes: request line,
      CRLF-separated fields, blank line, body; then the status line, fields, body. Read every line.
      `[WIRE]` `[SOURCE]`
3.1.2 `Transfer-Encoding: chunked` framing: the hex length line, the chunk, the terminating `0`
      chunk, and the optional trailer section. Why this is the only way to send a body of unknown
      length in HTTP/1.1. `[WIRE]`
3.1.3 `Content-Length` vs chunked, and the request-smuggling class of vulnerability that lives in
      their disagreement (CL.TE / TE.CL). One paragraph; the security treatment is in 13.
      `[WIRE]` `[X-REF 13]`
3.1.4 The same request in HTTP/2: `HEADERS` frame with HPACK-compressed pseudo-headers (`:method`,
      `:path`, `:scheme`, `:authority`, `:status`), `DATA` frames, stream ids, and the absence of a
      reason phrase. `[WIRE]` `[X-REF 10]`
3.1.5 HPACK's static table and dynamic table: why the second request on a connection sends ~20 bytes
      of headers instead of ~800, and what that does to the §1.9.18 header-budget arithmetic.
      `[NUM]` `[PROVE]` `[X-REF 10]`
3.1.6 HTTP/3 over QUIC: streams without TCP head-of-line blocking, QPACK's encoder/decoder streams,
      and the one API-visible consequence — 0-RTT and the replay hazard that `425 Too Early` exists
      for. `[WIRE]` `[X-REF 10]`
3.1.7 A `curl -v` transcript of the full QuizStakes deposit call, annotated line by line: TLS
      handshake lines, request headers, `100-continue` if present, response status, every response
      header explained, and the body. `[DIAG]` `[WIRE]`

*(7 leaves)*

## §3.2 The gRPC wire protocol

3.2.1 The message grammar, quoted from `PROTOCOL-HTTP2.md`:
      `Request → Request-Headers *Length-Prefixed-Message EOS` and
      `Response → (Response-Headers *Length-Prefixed-Message Trailers) / Trailers-Only`.
      `[SOURCE]` `[WIRE]` `[RESEARCH]`
3.2.2 The **Length-Prefixed-Message** frame: one **compressed-flag byte** (0 or 1) followed by a
      **big-endian uint32 length**, then the protobuf bytes. Five bytes of framing per message, then
      fragmentation into HTTP/2 `DATA` frames. `[WIRE]` `[NUM]` `[SOURCE]`
3.2.3 The request headers: `:method POST`, `:scheme`, `:path /package.Service/Method`,
      `content-type: application/grpc+proto`, `grpc-encoding`, `grpc-accept-encoding`,
      `grpc-timeout`, `te: trailers`, plus custom metadata. `[WIRE]` `[SOURCE]`
3.2.4 **The `:status: 200` trap**: the HTTP status is almost always 200 even when the RPC failed,
      because the real status is `grpc-status` in the **trailers**. This is why an HTTP-level
      monitor, a WAF or a naive load balancer reports 100% success on a totally broken gRPC service.
      `[TRAP]` `[WIRE]` `[PROVE]` `[RESEARCH]`
3.2.5 `Trailers-Only` responses: when the server fails before sending any message, the status arrives
      in the initial `HEADERS` frame with `END_STREAM` — and this is the case that breaks several
      client implementations. `[WIRE]` `[TRAP]` `[RESEARCH]`
3.2.6 `grpc-status`, `grpc-message` (percent-encoded), and `grpc-status-details-bin` (a base64
      `google.rpc.Status`) as the three trailer fields. `[WIRE]` `[SOURCE]`
3.2.7 `grpc-timeout` on the wire: `TimeoutValue TimeoutUnit` with units `H`, `M`, `S`, `m`, `u`, `n`
      — and how a server derives the remaining budget and re-emits a smaller one downstream.
      `[WIRE]` `[NUM]` `[PROVE]` `[RESEARCH]`
3.2.8 The protobuf wire format itself: field tag = `(field_number << 3) | wire_type`, the wire types
      (0 varint, 1 64-bit, 2 length-delimited, 5 32-bit; 3/4 deprecated groups), varint encoding
      with 7 bits per byte and a continuation bit, and zigzag for `sint32`/`sint64`. Encode a
      QuizStakes deposit message by hand. `[WIRE]` `[NUM]` `[PROVE]`
3.2.9 Why unknown fields are preserved and what that buys: a proxy can deserialise, modify one field
      and re-serialise without destroying fields it does not know about — the mechanism behind
      protobuf's forward compatibility. `[PROVE]` `[WIRE]`
3.2.10 Why a field-number change is catastrophic, demonstrated on the bytes: the same bytes parse
       into a different field, silently, with no error. `[PROVE]` `[TRAP]`
3.2.11 gRPC-Web's transformation: trailers encoded as a final framed message in the body (a frame
       with the MSB set in the flag byte), so JavaScript can read them. What the proxy (Envoy,
       grpcwebproxy) actually does. `[WIRE]` `[RESEARCH]`
3.2.12 The load-balancing consequence of long-lived HTTP/2 connections: an L4 balancer pins all
       streams from one client to one backend forever, so you need L7 balancing, client-side
       load balancing with a resolver, or periodic `GOAWAY`. `[PROVE]` `[TRAP]` `[X-REF 10]`

*(12 leaves)*
## §3.3 The idempotency mechanism, proved

3.3.1 The formal statement of what the mechanism must guarantee: for a given key, **at most one**
      state-changing effect, and every attempt observes either the effect's result or a defined
      "in progress" answer. `[PROVE]`
3.3.2 The interleaving proof that `SELECT`-then-`INSERT` fails: write out the two-thread schedule
      with the exact SQL statements and the isolation level, and show the window. Then show the
      same schedule with `INSERT` first and the unique-violation branch. `[PROVE]` `[X-REF 09]`
      `[X-REF 05]`
3.3.3 Why `INSERT … ON CONFLICT DO NOTHING` plus `rowCount` inspection is the clean Postgres
      spelling, and what the MySQL equivalent (`INSERT IGNORE` / `ON DUPLICATE KEY UPDATE`) does
      differently. `[SOURCE]` `[X-REF 09]`
3.3.4 The isolation-level analysis: does the mechanism need `SERIALIZABLE`? Prove that it does not —
      the unique index provides the serialisation point at any isolation level, which is why this
      design is robust. `[PROVE]` `[X-REF 09]`
3.3.5 The crash-window analysis, state by state: crash after insert but before work (row stuck
      `IN_PROGRESS` — the recovery rule), crash after work but before the status update (impossible
      if same transaction — prove it), crash after commit but before the response reaches the client
      (the replay path handles it). `[PROVE]` `[FLOW]`
3.3.6 The stuck-`IN_PROGRESS` recovery: a lease with an expiry timestamp, or a sweeper that resolves
      rows older than the maximum request duration by querying the downstream provider. Say plainly
      that without one, a crash leaves the client permanently `409`-blocked. `[TRAP]` `[PROVE]`
3.3.7 Why the response body must be stored and not recomputed: recomputation is not guaranteed to
      produce the same answer (a nested resource may have changed), and the contract promised
      replay. `[PROVE]`
3.3.8 The external-side-effect gap, stated as the theorem it is: no protocol makes a call to a
      third party and a local commit atomic. The three available tools — pass the key through,
      record intent before calling (the `DEP-300 CAPTURING` state exists for exactly this), and
      reconcile. `[PROVE]` `[X-REF 14]` `[SOURCE]`
3.3.9 Reading the QuizStakes deposit state machine as an idempotency design: why `DEP-300
      CAPTURING` is a persisted state and not a transient one, why `DEP-390 → DEP-300` is annotated
      "retry with same key", and why `DEP-301 → DEP-400` is called "the dangerous seam".
      `[SOURCE]` `[PROVE]`

*(9 leaves)*

## §3.4 Cursor pagination internals

3.4.1 The cursor encode/decode algorithm: serialise the sort tuple to a canonical form, append the
      schema version and the filter fingerprint, HMAC it, base64url it without padding. Show the
      exact bytes for a QuizStakes withdrawal cursor. `[WIRE]` `[BUILD]`
3.4.2 The SQL the cursor generates, with the row-value comparison that most implementations get
      wrong: `WHERE (created_at, id) < (?, ?)` is **not** the same as
      `WHERE created_at <= ? AND id < ?`. Prove the difference with a three-row example.
      `[SOURCE]` `[PROVE]` `[TRAP]` `[X-REF 09]`
3.4.3 The index requirement: the composite index must match the ORDER BY tuple in order and
      direction, or the database sorts. Show the plan difference. `[X-REF 09]` `[PLAN-equivalent]`
3.4.4 Mixed-direction sorts (`ORDER BY created_at DESC, id ASC`) and why they need either a matching
      index with mixed direction or a rewrite. `[X-REF 09]` `[TRAP]`
3.4.5 `NULL`s in the sort key: `NULLS FIRST`/`NULLS LAST` changes the comparison, and a nullable
      sort column silently breaks keyset pagination. `[TRAP]` `[X-REF 09]`
3.4.6 Offset's cost proved: the executor must produce and discard `offset` rows, so page N costs
      O(N × pageSize). Show the arithmetic at page 100,000 with 20 per page — 2,000,000 rows
      produced to return 20. `[PROVE]` `[NUM]` `[X-REF 09]`
3.4.7 The shifting-window failure proved: a row inserted before the reader's position causes the
      last item of page 1 to reappear as the first item of page 2. Walk it with concrete rows.
      `[PROVE]`
3.4.8 Merge-paginating two sources with one cursor: the algorithm (fetch `limit` from each, merge,
      truncate, record both positions), its cost, and its failure mode when one source is far
      denser than the other. This is the QuizStakes two-schema withdrawal problem. `[PROVE]`
      `[SOURCE]`

*(8 leaves)*

## §3.5 Rate limiter internals

3.5.1 Token bucket as code, with the lazy-refill trick: store `(tokens, lastRefillNanos)` and
      compute the refill on read instead of running a timer. Prove that this is equivalent to
      continuous refill. `[PROVE]` `[BUILD]`
3.5.2 The floating-point and clock hazards: monotonic clock (`System.nanoTime`) vs wall clock,
      negative elapsed time on clock adjustment, and integer vs fractional tokens. `[TRAP]`
      `[X-REF 11]`
3.5.3 The Redis Lua token bucket, line by line: why the whole check-and-decrement must be one
      script (Redis executes a script atomically), the `TIME` command vs a passed-in timestamp for
      determinism and replication safety, and the `EXPIRE` that garbage-collects idle keys.
      `[SOURCE]` `[BUILD]` `[X-REF 15]`
3.5.4 The sliding-window-counter formula: `count = current * elapsedFraction + previous * (1 −
      elapsedFraction)`, and the bound on its error. `[PROVE]` `[NUM]`
3.5.5 The fixed-window boundary burst, proved with timestamps. `[PROVE]`
3.5.6 Memory arithmetic for a distributed limiter: 2.4M clients × one Redis hash of ~100 bytes is
      ~240 MB, plus expiry bookkeeping. Compare against a sliding-window log at 1,200 req/sec.
      `[NUM]` `[PROVE]`
3.5.7 The Redis round-trip on the hot path: pipeline it with the other lookups, or use a local
      bucket with periodic reconciliation, and quantify the accuracy loss. `[NUM]` `[PROVE]`
3.5.8 Bucket4j / Resilience4j `RateLimiter` internals at a glance, and what `Bucket4j`'s
      distributed mode does (CAS on a compare-and-swap-capable backend). `[API]` `[RESEARCH]`

*(8 leaves)*

## §3.6 Caching and conditional-request internals

3.6.1 The cache lookup algorithm from RFC 9111 § 4, as an ordered procedure: match method and URI,
      match every field in `Vary`, check `no-cache`, compute freshness, decide fresh/stale/
      revalidate. `[FLOW]` `[SPEC]`
3.6.2 The revalidation round trip: cache sends `If-None-Match` (and/or `If-Modified-Since`), origin
      returns `304` with updated freshness headers, cache updates its stored entry's headers without
      touching the body. Show both messages. `[WIRE]` `[FLOW]`
3.6.3 `Age` computation walked through with real timestamps across two caches in series.
      `[NUM]` `[PROVE]`
3.6.4 Weak vs strong validator comparison functions per RFC 9110 § 8.8.3.2: strong comparison for
      `If-Match` and `If-Range`, weak comparison for `If-None-Match`. This is why `W/"x"` matches
      `"x"` in one direction and not the other. `[SPEC]` `[PROVE]` `[TRAP]`
3.6.5 `ShallowEtagHeaderFilter` internals: it buffers the whole response, MD5-hashes it, compares
      with `If-None-Match`, and returns `304` with an empty body. Read its javadoc's own admission
      that it saves bandwidth but not server work. `[SOURCE]` `[API]` `[TRAP]`
3.6.6 Spring's `checkNotModified` internals in `ServletWebRequest`: how it short-circuits the
      handler, sets the status, and what happens if you also write a body. `[SOURCE]` `[API]`
3.6.7 The cache-poisoning mechanism in one paragraph: an unkeyed input (a header the origin reflects
      but does not `Vary` on) lets an attacker store a response for other users. It is the same
      `Vary` bug as §2.8.5, weaponised. `[TRAP]` `[X-REF 13]`

*(7 leaves)*

## §3.7 SSE and WebSocket internals

3.7.1 The SSE wire format in bytes: `data: {...}\n\n`, multi-line `data:` concatenation, `event:`
      naming, `id:` setting the last-event id, `retry:` in milliseconds, and `:` comment lines as
      keep-alive. Show a real stream. `[WIRE]` `[SPEC]`
3.7.2 Reconnection: the browser's `EventSource` reconnects automatically after `retry` ms and sends
      `Last-Event-ID`, so **resumability is a server obligation** — you must be able to replay from
      an id. `[PROVE]` `[TRAP]`
3.7.3 Buffering hazards: an intermediary proxy that buffers the response breaks SSE entirely. The
      mitigations — `X-Accel-Buffering: no`, disabling gzip on the stream, and periodic padding.
      `[TRAP]` `[DIAG]`
3.7.4 The connection-cost arithmetic: N clients each hold a connection, a socket, a buffer and (on
      a platform thread model) a thread. 10,000 SSE clients at 8 KB of buffers is 80 MB before you
      count threads; with virtual threads the thread cost collapses. `[NUM]` `[PROVE]`
      `[X-REF 04]`
3.7.5 The WebSocket handshake, byte by byte: `GET` + `Upgrade: websocket` +
      `Sec-WebSocket-Key: <base64 16 random bytes>` + `Sec-WebSocket-Version: 13`, then `101` +
      `Sec-WebSocket-Accept: base64(SHA1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))`.
      `[WIRE]` `[SPEC]` `[NUM]`
3.7.6 The WebSocket frame layout: FIN, RSV1–3, 4-bit opcode (`0x0` continuation, `0x1` text, `0x2`
      binary, `0x8` close, `0x9` ping, `0xA` pong), MASK bit, 7/16/64-bit payload length, the
      4-byte masking key (mandatory client→server), payload. `[WIRE]` `[SPEC]`
3.7.7 Why client frames are masked (cache-poisoning of intermediaries that mistake a frame for an
      HTTP request), and the close-code registry (`1000` normal, `1001` going away, `1006` abnormal
      — never sent, only inferred, `1011` internal error). `[NUM]` `[SPEC]`
3.7.8 The scaling backplane: with N app instances and clients connected to arbitrary instances, a
      message for client X must reach the instance holding X — hence Redis pub/sub, a STOMP relay,
      or a session registry. Show why sticky routing alone is insufficient. `[PROVE]`
      `[X-REF 15]`
3.7.9 Deployment behaviour: a rolling restart disconnects every client, and they all reconnect at
      once. The mitigations — staggered draining, a jittered client reconnect, and a connection
      lifetime cap so reconnection is continuous rather than synchronised. `[PROVE]` `[TRAP]`
      `[X-REF 19]`

*(9 leaves)*

## §3.8 The Spring MVC path for an API request

3.8.1 The full ordered trace for `POST /deposits`, as a numbered flow: servlet container →
      `Filter` chain (`OncePerRequestFilter`s: tracing, security, idempotency) →
      `DispatcherServlet.doDispatch` → `HandlerMapping` (`RequestMappingHandlerMapping`) →
      `HandlerInterceptor.preHandle` → `HandlerAdapter` → argument resolvers →
      `HttpMessageConverter.read` → validation → the handler method → return-value handler →
      `HttpMessageConverter.write` → `postHandle` → `afterCompletion` → filter unwinding.
      `[FLOW]` `[X-REF 07]`
3.8.2 `RequestMappingInfo` and how a request is matched: the `RequestCondition` composition
      (`PatternsRequestCondition`, `RequestMethodsRequestCondition`, `ParamsRequestCondition`,
      `HeadersRequestCondition`, `ConsumesRequestCondition`, `ProducesRequestCondition`, and in 7.0
      the version condition), and the ordering that decides between two matching mappings.
      `[SOURCE]` `[API]`
3.8.3 `PathPattern` vs `AntPathMatcher`: the 5.3+ default change, `{*path}` capture-the-rest, and the
      trailing-slash-matching default flip in 6.0 (`setUseTrailingSlashMatch(false)`) — which
      broke a lot of clients. `[VERSION-TRAP]` `[TRAP]` `[API]`
3.8.4 Where an exception thrown in each phase surfaces, which determines whether your
      `@RestControllerAdvice` even sees it: a filter exception does **not** reach the advice, a
      converter exception does, and a `HandlerInterceptor` exception depends on the phase. This is
      why an idempotency filter must format its own problem+json. `[PROVE]` `[TRAP]`
3.8.5 `HandlerExceptionResolver` chain internals:
      `ExceptionHandlerExceptionResolver` → `ResponseStatusExceptionResolver` →
      `DefaultHandlerExceptionResolver`, and how `@ControllerAdvice` ordering plugs into the first.
      `[SOURCE]` `[API]` `[X-REF 07]`
3.8.6 `ProblemDetail` serialisation internals: how extension properties are flattened to top-level
      members via `@JsonAnyGetter`, and why the `Content-Type` becomes `application/problem+json`.
      `[SOURCE]` `[API]`
3.8.7 `ApiVersionStrategy` resolution internals (Spring 7): resolve → parse → validate against
      supported versions → match the mapping condition → apply the deprecation handler. Where each
      of the three exceptions is thrown. `[FLOW]` `[API]` `[VERSION-TRAP]` `[RESEARCH]`
3.8.8 Content negotiation internals: `ProducesRequestCondition` narrowing at mapping time versus
      `AbstractMessageConverterMethodProcessor.writeWithMessageConverters` choosing the converter at
      write time, and why a `406` can come from either. `[SOURCE]` `[API]`
3.8.9 The read-once body problem in detail: `ServletInputStream` cannot be re-read, so an
      idempotency or signature filter must wrap with `ContentCachingRequestWrapper` **before** the
      converter reads it, and that wrapper's buffer size is a memory-per-request cost. Show the
      arithmetic at 1,200 req/sec with a 4 KB body. `[NUM]` `[PROVE]` `[TRAP]`
3.8.10 Async dispatch internals: how `DeferredResult` releases the container thread, the
       `ASYNC` dispatch that re-enters the filter chain (and why `OncePerRequestFilter` exists), and
       `spring.mvc.async.request-timeout`. `[SOURCE]` `[API]`

*(10 leaves)*

## §3.9 Failure modes read at the protocol level

3.9.1 The double-charge: a `curl` transcript of a timed-out capture, the PSP's record showing
      success, the local record showing failure, and the reconciliation report. Read all three.
      `[DIAG]` `[PROVE]`
3.9.2 The lost update: two `PUT`s without `If-Match`, the resulting row, and the same two with
      `If-Match` producing a `412`. `[DIAG]` `[PROVE]`
3.9.3 The cross-tenant cache leak: the response headers that caused it and the corrected headers.
      `[DIAG]` `[TRAP]`
3.9.4 The enum-deserialisation crash: the response payload, the client's exception, and the two
      fixes. `[DIAG]` `[TRAP]`
3.9.5 The gRPC "everything is fine" outage: an HTTP-level dashboard at 100% success while
      `grpc-status` is `UNAVAILABLE` on every call. `[DIAG]` `[TRAP]`
3.9.6 The retry storm: a request-rate graph showing the synchronised spike after a `Retry-After`
      without jitter. `[DIAG]` `[PROVE]`
3.9.7 The deep-pagination outage: the slow-query log line for page 100,000 and the fix.
      `[DIAG]` `[X-REF 09]`
3.9.8 The webhook backlog: one slow consumer, a growing queue, and the per-endpoint concurrency cap
      that fixes it. `[DIAG]`
3.9.9 The SSE-through-a-buffering-proxy silence: the client receiving nothing for 60 seconds and the
      `X-Accel-Buffering` fix. `[DIAG]` `[TRAP]`
3.9.10 The `Deprecation: true` non-event: a client's header parser ignoring an unparseable
       structured field, so the sunset warning was never seen. `[DIAG]` `[VERSION-TRAP]`
3.9.11 The stuck `IN_PROGRESS` idempotency key: a client permanently receiving `409` after a server
       crash, and the lease-expiry fix. `[DIAG]` `[TRAP]`
3.9.12 The `Vary`-less content-negotiated response: a cache serving XML to a JSON client.
       `[DIAG]` `[TRAP]`

*(12 leaves)*

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf ships complete, compiling Java 21 (records, sealed types, pattern matching,
Spring Boot 3.5), and each is followed by a **Diff vs the real one** table naming what a production
implementation adds and why.

## §4.1 An idempotency filter, complete

4.1.1 `IdempotencyFilter extends OncePerRequestFilter`: header parse (including the Structured-Field
      quoted-string form), scope key composition, `ContentCachingRequestWrapper` for the fingerprint,
      the insert-first store call, the replay path, the `409` path, the `422` path, and the response
      capture on success. `[BUILD]`
4.1.2 `IdempotencyStore` as an interface with a JDBC implementation: the DDL, the
      `INSERT … ON CONFLICT DO NOTHING`, the `SELECT` on conflict, the `COMPLETED` update, and the
      TTL delete. `[BUILD]` `[X-REF 09]`
4.1.3 The transactional boundary: why the store update must join the business transaction, and the
      `TransactionSynchronization`/`TransactionTemplate` wiring that makes it so. `[BUILD]`
      `[X-REF 07]`
4.1.4 A concurrency test that actually proves it: N threads, one key, assert exactly one effect.
      `[BUILD]` `[X-REF 16]`
4.1.5 **Diff vs a production implementation** (Stripe/AWS-grade): key length and charset validation,
      per-caller quota on key creation, response-header allow-listing on replay, an
      `Idempotent-Replayed` marker, a lease with expiry for crash recovery, partitioned storage with
      partition drop instead of `DELETE`, metrics, and passing the key downstream. `[TABLE]`

*(5 leaves)*

## §4.2 A cursor-pagination library, complete

4.2.1 `Cursor` as a sealed record hierarchy with encode/decode, HMAC signing, a schema version, and
      a filter fingerprint. `[BUILD]`
4.2.2 `Page<T>` / `PageRequest` records, the `limit` clamp with a named default and maximum, and the
      response envelope serialisation. `[BUILD]` `[NUM]`
4.2.3 The repository query with the row-value comparison, in both JPQL-with-a-native-fallback and
      plain JDBC forms, plus the composite index DDL. `[BUILD]` `[X-REF 09]` `[X-REF 08]`
4.2.4 A property-based test: full traversal yields every row exactly once, insertion mid-traversal
      never duplicates, and a truncated cursor fails with `400` not `500`. `[BUILD]`
      `[X-REF 16]`
4.2.5 **Diff vs the real one** (Spring Data's `Slice`/`Window`/`ScrollPosition`, JSON:API
      implementations): `KeysetScrollPosition` support, dialect-specific SQL generation, reverse
      paging, `Sort` integration, projection support, and metrics on page depth. `[TABLE]`
      `[X-REF 08]`

*(5 leaves)*

## §4.3 A problem-detail error layer, complete

4.3.1 A `ProblemType` enum/registry holding the URI, title, status and default detail template for
      every QuizStakes problem, so the catalogue is code rather than prose. `[BUILD]`
4.3.2 `GlobalExceptionHandler extends ResponseEntityExceptionHandler` with handlers for the domain
      exception hierarchy, `MethodArgumentNotValidException` → the `errors` array,
      `ConstraintViolationException`, `OptimisticLockingFailureException` → `409`,
      `HttpMessageNotReadableException` → `400`, and a catch-all that logs and returns a bare `500`
      with only a trace id. `[BUILD]`
4.3.3 Trace-id injection into every `ProblemDetail` from the current `Observation`/MDC. `[BUILD]`
      `[X-REF 20]`
4.3.4 A test asserting every problem type's status, `Content-Type`, `type` URI and trace id, plus a
      test that no 5xx body contains a stack trace or SQL. `[BUILD]` `[X-REF 16]`
4.3.5 **Diff vs Spring Boot's own** `spring.mvc.problemdetails.enabled` handler: ordering, the
      built-in exception coverage, `ErrorResponse` interface support, i18n via `MessageSource`, and
      the WebFlux variant. `[TABLE]`

*(5 leaves)*

## §4.4 A rate limiter, complete

4.4.1 A local `TokenBucket` with lazy refill on `System.nanoTime`, generic over the key type, plus a
      `ConcurrentHashMap` registry with eviction. `[BUILD]` `[X-REF 05]`
4.4.2 A `RateLimitFilter` emitting `429` + `Retry-After` + `RateLimit` + `RateLimit-Policy` +
      the `#quota-exceeded` problem type with `violated-policies`. `[BUILD]`
4.4.3 The distributed version: a Redis Lua script, the `RedisTemplate`/Lettuce call, the fail-open
      vs fail-closed switch, and a timeout on the Redis call so the limiter cannot become the
      outage. `[BUILD]` `[X-REF 15]`
4.4.4 A multi-policy limiter enforcing burst + sustained + daily simultaneously and reporting all
      three. `[BUILD]`
4.4.5 **Diff vs Bucket4j / Resilience4j / an API gateway**: multi-node consistency guarantees,
      metrics, per-route configuration, warm-up, blocking vs non-blocking acquisition, and the
      gateway's ability to reject before your process is involved at all. `[TABLE]`

*(5 leaves)*

## §4.5 Webhook signing, verification and delivery, complete

4.5.1 A Standard-Webhooks-compatible signer: `whsec_` secret parsing, the
      `"{id}.{timestamp}.{body}"` signed content, HMAC-SHA256, base64 with padding, and the
      `v1,<sig>` header format with multiple signatures for rotation. `[BUILD]`
4.5.2 The verifier: parse all signatures, constant-time compare (`MessageDigest.isEqual`), timestamp
      tolerance check, and a typed result. `[BUILD]` `[X-REF 13]`
4.5.3 The delivery worker: outbox poll, per-endpoint concurrency limit, HTTP call with a 20 s
      timeout, exponential backoff with jitter, attempt logging, `410` → disable, and the
      circuit-breaker on persistent failure. `[BUILD]`
4.5.4 The inbound receiver: a filter that verifies before parsing, dedupes on `webhook-id`, responds
      `2xx` immediately and enqueues, and handles the unknown-reference case without a 500.
      `[BUILD]`
4.5.5 **Diff vs Svix/Stripe**: signature schemes including ed25519, per-endpoint secrets with
      rotation windows, static egress IPs, the customer-facing delivery log UI with replay, SSRF
      filtering proxy, rate limiting per endpoint, and a full retry schedule with dead-lettering.
      `[TABLE]`

*(5 leaves)*

## §4.6 ETag and conditional-request support, complete

4.6.1 A version-column-based `ETag` producer and an `If-Match` verifier that maps a mismatch to
      `412` and a missing header to `428`. `[BUILD]`
4.6.2 A conditional-GET handler using `ServletWebRequest.checkNotModified` and returning `304`
      correctly (no body, correct headers). `[BUILD]`
4.6.3 A JPA-integrated version: `@Version` → `ETag`, and translating
      `ObjectOptimisticLockingFailureException` into `409` versus `412` — and why they are
      different. `[BUILD]` `[X-REF 08]`
4.6.4 **Diff vs `ShallowEtagHeaderFilter`**: body buffering, MD5 cost, no server-work saving, and
      why a strong entity-derived ETag beats it. `[TABLE]`

*(4 leaves)*

## §4.7 A JSON Merge Patch and JSON Patch applier, complete

4.7.1 The RFC 7396 merge-patch algorithm implemented recursively over Jackson `JsonNode`, with the
      `null`-deletes rule and array-replace rule. `[BUILD]`
4.7.2 An RFC 6902 applier for `add`/`remove`/`replace`/`move`/`copy`/`test` with RFC 6901 pointer
      resolution including `~0`/`~1` unescaping and the `-` array index, applied atomically to a
      copy. `[BUILD]`
4.7.3 A controller wiring both media types on one `@PatchMapping`, with schema validation of the
      patched result before persisting (so a patch cannot bypass Bean Validation). `[BUILD]`
      `[TRAP]`
4.7.4 **Diff vs `json-patch` / Jakarta JSON-P**: error reporting with pointers, `test` semantics for
      numeric equality, performance on large documents, and streaming application. `[TABLE]`

*(4 leaves)*

## §4.8 An async operation (`202`) resource, complete

4.8.1 The `Operation` record and table (`id`, `status`, `resultRef`, `error`, `createdAt`,
      `updatedAt`, `expiresAt`), the `202` + `Location` + `Retry-After` response, and the
      `GET /operations/{id}` handler returning `303 See Other` on completion. `[BUILD]`
4.8.2 `Prefer: respond-async` support with `Preference-Applied`, so the same endpoint can be
      synchronous or asynchronous by client choice. `[BUILD]`
4.8.3 A cancellation endpoint with best-effort semantics and a documented race.
      `[BUILD]`
4.8.4 An SSE progress endpoint on the same operation, with heartbeats and `Last-Event-ID`
      resumption. `[BUILD]`
4.8.5 **Diff vs Azure/Graph LRO and `google.longrunning.Operations`**: metadata typing, the RELO
      variant, result-retention policy, a standard `Operations` service surface, and
      `WaitOperation` long-polling. `[TABLE]`

*(5 leaves)*

## §4.9 Contract tooling you build yourself

4.9.1 A CI step that generates the OpenAPI document from the running app, diffs it against the
      committed baseline with `oasdiff`, and fails on a breaking change — including the allow-list
      mechanism for an intentional break. `[BUILD]`
4.9.2 A test that validates every recorded request/response pair against the OpenAPI schema
      (`swagger-request-validator`), so drift between code and spec is a test failure. `[BUILD]`
      `[X-REF 16]`
4.9.3 A deprecation-usage reporter: a filter that records `(callerId, route, version)` for anything
      marked deprecated, and the query that answers "who is still calling v1". `[BUILD]`
      `[X-REF 20]`
4.9.4 A tolerant-reader conformance test you hand to integrators: a response with an extra field, an
      unknown enum value, a reordered array and a new optional header — all must parse.
      `[BUILD]`
4.9.5 **Diff vs a governance platform** (Zally, Spectral in a portal, Buf Schema Registry): rule
      authoring, org-wide reporting, PR annotation, and registry-backed dependency management.
      `[TABLE]`

*(5 leaves)*

## §4.10 The QuizStakes API, built

4.10.1 `POST /deposits` end to end: the request record with validation, `Idempotency-Key`, the
       `DEP-*` state machine transitions, `201` + `Location`, and every error path mapped to a
       problem type. `[BUILD]`
4.10.2 `POST /deposits/{id}/captures` with key pass-through to the PSP, the `DEP-390 → DEP-300`
       retry path, and the reconciliation hook. `[BUILD]`
4.10.3 `GET /clients/{id}/withdrawals` as a cursor-paged union over two schemas, with the composite
       cursor. `[BUILD]`
4.10.4 `PUT /clients/{id}/self-exclusion` as an idempotent state transition inside the 500 ms
       budget, with `If-Match`. `[BUILD]` `[NUM]`
4.10.5 `POST /stake-reservations` at 1,200/sec with a 150 ms budget: the minimal payload, the
       idempotency lookup on the hot path, and the expiry contract. `[BUILD]` `[NUM]`
4.10.6 The `ClientRestrictions.decide` call as **both** a REST endpoint and a gRPC method from one
       domain service, so the reader sees the same contract in two styles side by side.
       `[BUILD]`
4.10.7 The complete OpenAPI 3.1 document for the client-facing surface, with `components` for
       `Money`, `ProblemDetail`, `PageInfo`, the status enums, and the security scheme.
       `[BUILD]`
4.10.8 The `.proto` for the internal restriction service, with `reserved` numbers, field-number
       discipline and a `buf.yaml` breaking-change configuration. `[BUILD]`
4.10.9 The AsyncAPI document for the `DEP-*`/`BDP-*` webhook events. `[BUILD]`

*(9 leaves)*
---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question set, with the answer shape

Each leaf is one question plus the two-to-four sentence shape of a strong answer, plus the follow-up
the interviewer asks if you answer well.

**REST and HTTP fundamentals**

5.1.1 What is REST? (A strong answer names the constraints, not "JSON over HTTP".)
5.1.2 Name the six constraints and say which one is optional.
5.1.3 What does "stateless" forbid, and what does it *not* forbid?
5.1.4 What is the uniform interface's fourth sub-constraint, and does your API satisfy it?
5.1.5 Define safe and idempotent separately, then classify all nine methods.
5.1.6 Why is `PUT` idempotent but `POST` not — and what does that let a load balancer do?
5.1.7 Is `PATCH` idempotent? Defend your answer with two payloads.
5.1.8 Is `DELETE` idempotent if the second call returns 404?
5.1.9 What does `PUT` do to a field you omit?
5.1.10 Can a `GET` have a body? What actually happens if you send one?
5.1.11 What is the `QUERY` method and what problem does it solve? `[VERSION-TRAP]`
5.1.12 Which methods are cacheable by default, and what makes a response storable at all?
5.1.13 What is Richardson level 2 versus level 3, and which level is your API?
5.1.14 Where does the verb belong, and give the mechanical (not aesthetic) cost of putting it in the
       path.
5.1.15 Path, query, body or header — where does each of these go: the resource id, a status filter,
       a page cursor, an auth token, an idempotency key, a 40 KB search predicate?

**Status codes**

5.1.16 What is the difference between 401 and 403, and which header is mandatory on one of them?
5.1.17 When would you return 404 instead of 403, and what are you trading away?
5.1.18 400 vs 422 vs 409 — give a QuizStakes example of each.
5.1.19 What are the three distinct causes of a 409?
5.1.20 404 vs 410 — what does 410 assert that 404 does not?
5.1.21 412 vs 428.
5.1.22 415 vs 406.
5.1.23 When do you return 202, and what must the response contain?
5.1.24 What does a client do differently on 502/503/504 versus 500?
5.1.25 429 vs 503 — who is overloaded?
5.1.26 Why is `200 OK` with an error body wrong? Name four layers it breaks.
5.1.27 Is adding a new 4xx code a breaking change? Why not?
5.1.28 301/302 vs 307/308 — what changes about the method?

**Idempotency**

5.1.29 Design an idempotency-key mechanism end to end.
5.1.30 Why do you insert before you select?
5.1.31 What is the scope of a key, and what goes wrong if you scope it globally?
5.1.32 What do you return when the same key arrives while the first request is still running?
5.1.33 What do you return when the same key arrives with a different body?
5.1.34 Why must the work and the key record share a transaction? What if the effect is external?
5.1.35 How long do you keep keys, and what constrains the minimum?
5.1.36 A crash leaves a key `IN_PROGRESS`. What happens to the client, and how do you recover?
5.1.37 Where is the *real* idempotency in a payment system?
5.1.38 Can you achieve exactly-once delivery? Exactly-once effect?

**Pagination**

5.1.39 Compare offset and cursor pagination on four axes.
5.1.40 Why is offset pagination O(offset)?
5.1.41 Show me the bug when a row is inserted between page 1 and page 2.
5.1.42 Why must the cursor be opaque? What goes inside it?
5.1.43 Why does every pagination scheme need a tiebreaker?
5.1.44 How do you paginate a union across two databases?
5.1.45 Should you return a total count?
5.1.46 A client sends `limit=100000`. What do you do?
5.1.47 What consistency do you actually promise a paginating client?

**Versioning and compatibility**

5.1.48 What makes a change breaking?
5.1.49 Is adding an enum value breaking? Whose fault is it if a client crashes?
5.1.50 Compare URI, media-type, header and date-based versioning.
5.1.51 Explain Stripe's versioning scheme and what the server must implement to support it.
5.1.52 How do you remove a field that 200 unknown clients might be reading?
5.1.53 Walk the expand/contract migration.
5.1.54 How do you *detect* a breaking change before it ships?
5.1.55 Which header signals deprecation, and what is its exact syntax? `[VERSION-TRAP]`
5.1.56 What is the relationship between `Deprecation` and `Sunset`?
5.1.57 How do you know it is safe to switch a version off?
5.1.58 Does Spring have built-in API versioning? `[VERSION-TRAP]`

**Errors**

5.1.59 What is the standard error format, and which RFC? `[VERSION-TRAP]`
5.1.60 Name the five members of a problem detail and say which one a client may branch on.
5.1.61 Why can a client never parse `detail`?
5.1.62 Where do you return multiple validation errors, and why all at once?
5.1.63 What must every error response contain for support to be possible?
5.1.64 What must an error response never contain?
5.1.65 A downstream service returns a 500. What do you return, and why not 500?
5.1.66 How do you signal retryability?

**Rate limiting**

5.1.67 Describe token bucket, and say what `B` and `r` control.
5.1.68 Why does a fixed window allow 2× at the boundary?
5.1.69 You have three instances and a per-instance counter. What is the real limit?
5.1.70 Where do you store the counter, and what does that cost on a 30 ms budget?
5.1.71 Fail-open or fail-closed when Redis is down? Defend it per endpoint.
5.1.72 What do you key the limit on for a login endpoint?
5.1.73 Which headers accompany a 429? `[VERSION-TRAP]`
5.1.74 Every client retries at exactly `Retry-After`. What happens?

**Caching and concurrency**

5.1.75 How does `ETag` + `If-None-Match` save work? How much work does it actually save?
5.1.76 How does `If-Match` prevent a lost update?
5.1.77 Strong vs weak validators — where does it matter?
5.1.78 `no-cache` vs `no-store`.
5.1.79 What does `Vary` do, and what happens if you omit it on a negotiated response?
5.1.80 Why is a shared cache forbidden from storing a response to an `Authorization`-bearing request?
5.1.81 What cache headers do you set on an authenticated JSON API, and why?

**Modelling**

5.1.82 Model "cancel an order" four ways and rank them.
5.1.83 Design an endpoint for an operation that takes 30 seconds.
5.1.84 How do you model a bulk operation where 3 of 100 items fail?
5.1.85 The client needs to filter on 12 fields with ranges. Where does that go?
5.1.86 How deep should you nest resources, and why?
5.1.87 PUT or PATCH for a partial update, and which patch format?
5.1.88 Design the URI for "all withdrawals for client 1042".
5.1.89 Should a resource id be a database primary key?

**Styles**

5.1.90 REST vs gRPC vs GraphQL — pick one for three named scenarios and defend it.
5.1.91 Why can't a browser call gRPC directly? Name three workarounds.
5.1.92 Why does gRPC return HTTP 200 on a failed RPC?
5.1.93 What is a gRPC deadline and how is it better than a timeout?
5.1.94 What breaks if you change a protobuf field number? What if you delete a field?
5.1.95 What is the N+1 problem in GraphQL and what fixes it?
5.1.96 How do you stop a malicious GraphQL query?
5.1.97 Why is GraphQL hard to cache?
5.1.98 Does GraphQL need versioning?

**Push**

5.1.99 Polling vs long polling vs SSE vs WebSocket vs webhooks — give the decision rule.
5.1.100 Design a webhook system. What are your obligations to the consumer?
5.1.101 How do you sign a webhook, and why does the timestamp matter?
5.1.102 How does a consumer handle duplicate and out-of-order deliveries?
5.1.103 Why does WebSocket break the stateless-scaling story, and what do you do about it?
5.1.104 How does SSE reconnect, and what does that require of your server?

**Security and operations of the contract**

5.1.105 Where does authentication happen, and where does authorisation happen?
5.1.106 Why can't the gateway do object-level authorisation?
5.1.107 What is mass assignment and what is the API-design fix?
5.1.108 Why is a JWT with a permissions claim a design smell in this architecture?
5.1.109 Which response headers must be in `Access-Control-Expose-Headers` for your contract to work
        in a browser?
5.1.110 What metrics does an API need, and why is a global p99 useless?
5.1.111 A user reports an error. Walk me from their screenshot to the failing downstream call.

**Design exercises (whiteboard)**

5.1.112 Design the QuizStakes card-deposit API, `DEP-000` through `DEP-500`.
5.1.113 Design the stake-reservation API for 1,200/sec with a 150 ms budget and a hard
        no-double-reservation requirement.
5.1.114 Design the operator case-review API where two operators may open the same case.
5.1.115 Design the public partner API for a third party that needs deposit notifications.
5.1.116 Design a URL shortener's API (the classic), and say which of this guide's mechanisms apply.
5.1.117 Design a file-upload API for 500 MB documents.
5.1.118 You inherit an API with 200 unknown callers, no spec and no versioning. What do you do
        first, second, third?

*(118 leaves)*

## §5.2 The trap index

One line per trap, each stating the wrong belief, the symptom it produces, and the fix. Every one is
a `[TRAP]` leaf the write pass must render with a `**Trap:**` marker.

5.2.1 "POST is not idempotent, so a non-idempotent POST endpoint is fine."
5.2.2 "PATCH is idempotent because my payload is."
5.2.3 "`PUT` leaves omitted fields alone."
5.2.4 "401 means forbidden."
5.2.5 "403 is always the right answer for an unauthorised read."
5.2.6 "422 isn't a real HTTP status code."
5.2.7 "`425 Too Early` is for duplicate in-flight requests." `[VERSION-TRAP]`
5.2.8 "Return 200 with an error object so the client always gets a body."
5.2.9 "Map every failure to 500 so the client knows something went wrong."
5.2.10 "302 and 307 are the same thing."
5.2.11 "A GET can't have side effects, so analytics on GET is fine."
5.2.12 "`Deprecation: true`." `[VERSION-TRAP]`
5.2.13 "RFC 7807 is the error standard." `[VERSION-TRAP]`
5.2.14 "`RateLimit-Limit`/`-Remaining`/`-Reset` are the standardised headers." `[VERSION-TRAP]`
5.2.15 "You can't send a body with a safe method." `[VERSION-TRAP]`
5.2.16 "Spring can't do API versioning without a custom `RequestCondition`." `[VERSION-TRAP]`
5.2.17 "`nullable: true` is how you express null in OpenAPI." `[VERSION-TRAP]`
5.2.18 "GraphQL always returns 200." `[VERSION-TRAP]`
5.2.19 "Protobuf is 10× smaller than JSON." (Before gzip.)
5.2.20 "HTTP/2 server push fixes the round-trip problem." `[VERSION-TRAP]`
5.2.21 "Adding a field is always safe." (Not for a strict client, and not for an event consumer with
       `additionalProperties: false`.)
5.2.22 "Adding an enum value is always safe."
5.2.23 "Cursor pagination gives you a consistent snapshot."
5.2.24 "Offset pagination is fine, we only have a few thousand rows." (Until you do not.)
5.2.25 "The cursor is just the last id, so clients can construct it."
5.2.26 "`ORDER BY created_at` is a deterministic sort."
5.2.27 "`SELECT` then `INSERT` on the idempotency key is fine under `READ COMMITTED`."
5.2.28 "Store the idempotency key in Redis so it's fast." (Different failure domain, no shared
       transaction.)
5.2.29 "Replay the response by recomputing it."
5.2.30 "The gateway validated the token, so the service can trust `X-User-Id`."
5.2.31 "The JWT has the user's permissions in it, so we're done."
5.2.32 "The UI hides that field, so it's fine to return it."
5.2.33 "Bind the request body straight to the entity — Spring does the mapping for free."
5.2.34 "`ShallowEtagHeaderFilter` saves server work."
5.2.35 "We don't set cache headers, so nothing caches it."
5.2.36 "`Vary` is a browser thing."
5.2.37 "Our rate limit is 1,000/min." (Per instance, times N, changing with autoscale.)
5.2.38 "Retry three times at every layer for reliability."
5.2.39 "`Retry-After: 30` is enough — no jitter needed."
5.2.40 "Webhooks are just an HTTP POST."
5.2.41 "Webhook order is preserved because we send them in order."
5.2.42 "Signature comparison with `equals` is fine."
5.2.43 "WebSocket is strictly better than SSE."
5.2.44 "gRPC is faster, so use it everywhere."
5.2.45 "gRPC health is fine — HTTP 200 on every call."
5.2.46 "Renaming a protobuf field is safe because numbers are what matter." (JSON name breaks.)
5.2.47 "GraphQL removes the need for a BFF, a read model and versioning."
5.2.48 "HATEOAS is the goal; level 2 is incomplete REST."
5.2.49 "We're RESTful — we use JSON over HTTP."
5.2.50 "Expose the repositories with Spring Data REST and the API is done."
5.2.51 "Return `Page<Entity>` from the controller."
5.2.52 "The wiki page is the documentation."
5.2.53 "It's an internal API, so the contract doesn't matter."
5.2.54 "We can remove `/v1` — the calendar says the sunset passed."
5.2.55 "Secrets in a query parameter are fine over HTTPS."
5.2.56 "`Optional<T>` is a good JSON field type."

*(56 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The full one-line-assertion set, in the `## Atomic concept checklist` register, covering every
      §1–§4 mechanism — the pre-interview review layer. Must include every line already present in
      `src/topics/12-api-design.md`'s existing checklist, verbatim or expanded, plus one line per new
      mechanism. `[TABLE]`
5.3.2 The 60-second whiteboard sequence for any "design an API" prompt: resources → methods →
      status vocabulary → retry story → page contract → error contract → auth → limits →
      compatibility promise. Memorise the order, not the answers. `[FLOW]`
5.3.3 The five numbers to have on instant recall: 2^53−1 (JS integer limit), ~2,000 characters
      (practical URI limit), 8 KB (default header limit), the 6-connection HTTP/1.1 per-origin
      limit, and the 17 gRPC status codes. `[NUM]`
5.3.4 The five headers to name unprompted in any API design answer: `Idempotency-Key`, `ETag`/
      `If-Match`, `Retry-After`, `RateLimit`, `Deprecation`/`Sunset`. `[HDR]`
5.3.5 The three sentences that most reliably signal seniority, and why each does: "what can the
      client safely retry"; "that's a breaking change for a strict client, so here's how we detect
      it in CI"; "I'd return 202 with an operation resource rather than hold the connection".
      `[PROVE]`
5.3.6 A ten-question rapid-fire self-test with answers, drawn from §5.2's traps.
5.3.7 The "explain it to a client integrator" drill: write the three paragraphs of documentation a
      third party needs for retries, pagination and errors. If you cannot, you have not designed it.
      `[PROVE]`

*(7 leaves)*

---

## Sources consulted

Primary sources first. Where a fetch failed or a search returned nothing usable, that is stated
rather than padded. **Every `[RESEARCH]` leaf must be re-verified against the source named here
before the write pass commits a constant, a header syntax, a status code or an API shape to the
page.**

**IETF specifications (primary, normative)**

- <https://www.rfc-editor.org/rfc/rfc9111.html> — fetched in full. Source of the complete request and
  response `Cache-Control` directive lists (§1.14.4–§1.14.5), the storability conditions, the
  freshness arithmetic (`apparent_age`, `corrected_age_value`, `current_age`,
  `response_is_fresh`) in §1.14.7, heuristic freshness and the ~10% convention (§1.14.8), the
  `Age`/`Expires`/`Vary` definitions, the unsafe-method invalidation rule including `Location` and
  `Content-Location` (§1.14.11), the private-vs-shared distinction, and the pointer to RFC 5861 for
  `stale-while-revalidate`/`stale-if-error`. Basis of §1.14 and §3.6.1.
- <https://www.rfc-editor.org/rfc/rfc9745.txt> — fetched in full. Source of the **`Deprecation`
  field being a Structured Field Date** (`Deprecation: @1688169599`), the explicit confirmation that
  a boolean value is invalid, the `deprecation` link relation with its `Link` header form, the rule
  that `Sunset` **MUST NOT** be earlier than `Deprecation`, and the "treat deprecation as a hint"
  guidance. Basis of §1.9.11, §1.19.3–§1.19.6, §5.2.12. **This is the single most
  important version correction to the existing guide.**
- <https://datatracker.ietf.org/doc/html/rfc10008> — fetched. Source of the `QUERY` method's
  publication as **RFC 10008, June 2026, Proposed Standard**, its safe **and** idempotent
  classification, the cacheability rule that "the cache key for a QUERY request MUST incorporate the
  request content and related metadata", the mandatory `Content-Type`, the `Accept-Query`
  Structured-Field response header with its example
  (`Accept-Query: "application/jsonpath", application/sql;charset="UTF-8"`), and the
  `Content-Location`-names-the-result-set / `Location`-repeats-the-query distinction. Basis of
  §1.6.12–§1.6.13, §1.21.17.
- <https://greenbytes.de/tech/specs/draft-ietf-httpapi-idempotency-key-header-latest.html> —
  fetched in full. Source of the `Idempotency-Key` field being an **Item Structured Header whose
  value MUST be a String** with the quoted-UUID example, the "MUST be unique and MUST NOT be reused
  with another request with a different request payload" rule, the resource-owner-defined uniqueness
  scope, the **idempotency fingerprint** options (whole-payload checksum, selected-element checksum,
  field matching, request digest/signature), the three error mappings **400 / 422 / 409**, the
  expiration-policy requirement, and the security recommendations (fixed format, validate before
  processing, **composite cache lookup key combining the client key with server-side attributes**).
  Basis of §1.9.8, §1.17.3–§1.17.6, §1.17.13.
- <https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers> — fetched. Confirmed
  **draft-11, 23 May 2026, expires 24 Nov 2026**. Source of the two-field design
  (`RateLimit-Policy` and `RateLimit`, replacing the earlier three-header shape), every parameter —
  policy `q` (required non-negative Integer), `qu` (String, default `"requests"`), `w` (window
  seconds), `pk` (Byte Sequence partition key); service-limit `r` (required), `t`, `pk` — the
  examples `RateLimit-Policy: "burst";q=100;w=60,"daily";q=1000;w=86400` and
  `RateLimit: "default";r=50;t=30`, the three registered quota units (`requests`, `content-bytes`,
  `concurrent-requests`), the quota-partition and service-limit definitions, the rule that
  **`Retry-After` MUST take precedence** over the effective window, and the three IANA problem types
  `#quota-exceeded` / `#temporary-reduced-capacity` / `#abnormal-usage-detected` with the
  `violated-policies` extension member. Basis of §1.9.9–§1.9.10, §1.16.15, §1.20.11–§1.20.12.
- <https://www.iana.org/assignments/http-problem-types/http-problem-types.xhtml> — fetched. Source
  of the complete current problem-type registry contents in §1.2.10: `about:blank`, `#date`,
  `#ohttp-key`, `#digest-unsupported-algorithms`, `#digest-invalid-values`,
  `#digest-mismatched-values`, and the **Specification Required** registration policy.
- <https://www.rfc-editor.org/info/rfc9457/> and <https://www.ietf.org/rfc/rfc9457.pdf> — consulted
  via search plus the RFC-Editor info page. Confirmed **RFC 9457, July 2023, Standards Track,
  obsoletes RFC 7807**, authored by Nottingham, Wilde and Dalal, and the three substantive changes:
  the common-problem-type registry (§4.2), the multiple-problems clarification (§3), and guidance for
  non-dereferenceable type URIs (§3.1.1); the wire format and media type are unchanged for typical
  JSON usage. Basis of §1.16.2–§1.16.7. **The write pass must re-fetch the RFC body to quote the
  member definitions verbatim.**
- <https://datatracker.ietf.org/doc/html/rfc9110> — consulted for the method and status registries,
  the safe/idempotent/cacheable definitions in §§9.2.1–9.2.3, the conditional-request precedence
  order in §13.2.2, the validator comparison rules in §8.8.3.2, and the presence of `308`, `421`
  and `426` in the RFC 9110 registry tables. Basis of §1.2, §1.6, §1.7, §1.8, §1.13.
  **The write pass must quote §9.2.2's idempotency definition verbatim.**
- RFC 8594 (`Sunset`), RFC 8288 (`Link`), RFC 9651 / RFC 8941 (Structured Field Values), RFC 7240
  (`Prefer`), RFC 8297 (`103 Early Hints`), RFC 6585 (`428`/`429`/`431`), RFC 8470 (`425`),
  RFC 7725 (`451`), RFC 6902 / RFC 7396 / RFC 6901 (patch formats and JSON Pointer), RFC 5789
  (`PATCH`), RFC 5861 (`stale-while-revalidate`), RFC 8246 (`immutable`), RFC 6648 (`X-` prefix
  deprecation), RFC 9530 (digest fields), RFC 9421 (HTTP message signatures), RFC 3986 (URI),
  RFC 3339 (date-time), RFC 9562 (UUIDv7) — cited by number for the leaves that name them. These
  were **not individually fetched in this pass**; the write pass must verify any exact syntax it
  quotes from them.

**Design guides and rule sets (primary)**

- <https://opensource.zalando.com/restful-api-guidelines/> — fetched. Source of the complete chapter
  list used as a completeness checklist in §2.13.3, and of the verbatim rule titles for
  **compatibility** ("MUST not break backward compatibility", "SHOULD prefer compatible extensions",
  "MUST prepare clients to accept compatible API extensions", "**SHOULD avoid versioning**",
  "**MUST use media type versioning**", "**MUST not use URL versioning**", "MUST always return JSON
  objects as top-level data structures", "SHOULD use open-ended list of values for enumeration
  types"), **deprecation** (the four MUSTs on client approval, partner consent, usage monitoring and
  not using deprecated APIs, plus the two SHOULDs on emitting and monitoring
  `Deprecation`/`Sunset`), **pagination** ("SHOULD prefer cursor-based pagination", "**SHOULD avoid a
  total result count**", the page object and pagination links), **hypermedia** ("MUST use REST
  maturity level 2", "MAY use REST maturity level 3 — HATEOAS", "MUST use full, absolute URI",
  "**MUST not use link headers with JSON entities**"), **common headers** (including "MAY consider to
  support `Prefer`", "MAY consider to support `ETag` together with `If-Match`/`If-None-Match`",
  "MAY consider to support `Idempotency-Key`"), **proprietary headers** ("MUST propagate proprietary
  headers", "MUST support `X-Flow-ID`"), **operation** ("MUST publish OpenAPI specification",
  "SHOULD monitor API usage"), and the full **event** rule set. Basis of §1.5.16, §1.10.1,
  §1.10.9, §1.15.10, §1.18.5, §1.18.7, §1.18.17, §1.19.9–§1.19.10, §1.22.6, §2.13.1–§2.13.3.
- <https://google.aip.dev/general> — fetched. Source of the **complete AIP index by number** in
  §2.13.9, and of the specific leaves on resource names (AIP-122), custom methods (AIP-136),
  enumerations (AIP-126), pagination (AIP-158), filtering (AIP-160), field masks (AIP-161), partial
  responses (AIP-157), long-running operations (AIP-151), request identification (AIP-155), resource
  freshness validation (AIP-154), soft delete (AIP-164), resource revisions (AIP-162), backwards
  compatibility (AIP-180), stability levels (AIP-181), errors (AIP-193), automatic retry
  configuration (AIP-194), sensitive fields (AIP-147), field behavior (AIP-203), HTTP/gRPC
  transcoding (AIP-127), and the batch methods (AIP-231/233/234/235). Basis of §1.5.10, §1.10.10,
  §1.10.16, §1.11.10, §1.15.15, §1.21.3, §1.21.7, §1.21.15, §2.13.9–§2.13.11.
- <https://google.aip.dev/151> and <https://google.aip.dev/133> / <https://google.aip.dev/134> —
  consulted via search for `google.longrunning.Operation`'s shape, the `operation_info` annotation,
  and the standard-method contracts. Basis of §1.21.7. **Re-fetch to confirm the `Operations`
  service method list before writing it.**
- <https://github.com/microsoft/api-guidelines/blob/vNext/graph/patterns/long-running-operations.md>
  and the Azure/Graph guidelines — consulted via search. Source of the **RELO vs stepwise** LRO
  distinction, the operation-result retention-policy rule, the collections section structure, and
  the **delta query** pattern with `deltaLink`/`nextLink`. Basis of §1.21.6, §1.25.16.
  **Re-fetch before quoting.**
- <https://docs.stripe.com/sdks/versioning> and Stripe's API versioning docs — consulted via search.
  Source of the date-plus-release-name scheme (`2026-06-24.dahlia`, `2025-08-27.basil`,
  `2024-12-18.acacia`), the account-pinning model, the per-request `Stripe-Version` override, the
  "monthly releases are backward compatible and share the last major's name" rule, and the
  best-practice advice to pin explicitly in code. Basis of §1.18.10. **The exact key lifetime
  (24 h) and maximum key length (255 characters) in §1.17.20 are from recall and must be verified
  against Stripe's idempotency documentation before writing.**
- <https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md> —
  fetched. Source of the payload shape (`type`, `timestamp`, `data`), the three `webhook-*` headers,
  the `msg_id.timestamp.payload` signed content, the **v1 HMAC-SHA256** scheme with `whsec_` secrets
  of 24–64 bytes and base64-with-padding output, the **v1a ed25519** scheme with `whpk_`/`whsk_`,
  the space-delimited multi-signature form for key rotation, the retry schedule spanning 5 seconds
  to 75+ hours with jitter, `2xx` = success and **`410 Gone` = permanent disable**, the 15–30 s
  timeout recommendation, the period-delimited event-type naming over `[a-zA-Z0-9_]`, and the
  security requirements (timestamp tolerance, constant-time comparison, **SSRF filtering proxy and
  isolated workers**, HTTPS, static egress IPs). Basis of §1.25.11–§1.25.12, §2.10.3–§2.10.6,
  §4.5.
- <https://buf.build/docs/breaking/rules/> — fetched in full. Source of the **four rule categories**
  (`FILE`, `PACKAGE`, `WIRE_JSON`, `WIRE`) and the rule identifiers used in §1.26.7:
  `FIELD_NO_DELETE`, `FIELD_SAME_TYPE`, `FIELD_SAME_NAME`, `FIELD_SAME_JSON_NAME`,
  `FIELD_SAME_CARDINALITY`, `FIELD_SAME_ONEOF`, `ENUM_VALUE_NO_DELETE`, `ENUM_SAME_TYPE`,
  `RPC_NO_DELETE`, `RPC_SAME_REQUEST_TYPE`, `RPC_SAME_RESPONSE_TYPE`,
  **`RPC_SAME_IDEMPOTENCY_LEVEL`**, `RPC_SAME_CLIENT_STREAMING`/`_SERVER_STREAMING`,
  `FILE_SAME_PACKAGE`, `FILE_SAME_SYNTAX`, `MESSAGE_SAME_REQUIRED_FIELDS`,
  `FIELD_NO_DELETE_UNLESS_NAME_RESERVED`, `FIELD_NO_DELETE_UNLESS_NUMBER_RESERVED`,
  `FIELD_WIRE_COMPATIBLE_TYPE`, `FIELD_WIRE_JSON_COMPATIBLE_TYPE`, `RESERVED_ENUM_NO_DELETE`,
  `RESERVED_MESSAGE_NO_DELETE`. Basis of §1.7.10 and §1.26.7.

**Specifications for the non-REST styles**

- <https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md> — consulted via search summary.
  Source of the message grammar (`Request → Request-Headers *Length-Prefixed-Message EOS`;
  `Response → (Response-Headers *Length-Prefixed-Message Trailers) / Trailers-Only`), the
  **compression-flag byte + big-endian uint32 length** framing, the `grpc-timeout`
  `TimeoutValue TimeoutUnit` syntax with units `H`/`M`/`S`/`m`/`u`/`n`, the trailer-carried status,
  and the `:status: 200`-despite-failure behaviour. Basis of §3.2. **The write pass must fetch this
  document directly and quote the grammar verbatim rather than relying on the summary.**
- <https://grpc.github.io/grpc/core/md_doc_statuscodes.html> and
  <https://grpc.github.io/grpc-java/javadoc/io/grpc/Status.Code.html> — consulted via search.
  Source of the **17 codes 0–16** enumerated in §1.26.9, the `FAILED_PRECONDITION` /
  `ABORTED` / `UNAVAILABLE` distinction, and the `DEADLINE_EXCEEDED` caveat that a state-changing
  operation "may be returned even if the operation has completed successfully" (§1.26.11).
  **Re-fetch to quote the caveat exactly.**
- <https://github.com/graphql/graphql-over-http/blob/main/spec/GraphQLOverHTTP.md> and
  <https://graphql.github.io/graphql-over-http/draft/> — consulted via search. Source of the
  `application/graphql-response+json` media type (renamed from `application/graphql+json` in 2022),
  the rule that a non-null `data` entry **MUST** get a 2xx, the 400-for-validation-failure behaviour,
  and the contrast with `application/json` always returning 200. Basis of §1.27.7.
  **Re-fetch before writing the status-code claim.**
- <https://github.com/graphql/graphql-over-http/blob/main/rfcs/IncrementalDelivery.md> and
  <https://www.graphql-js.org/docs/defer-stream/> — consulted via search. Confirmed `@defer`/
  `@stream` are available in graphql-js v17 via `experimentalExecuteIncrementally()`, use
  `multipart/mixed`, and **have no ratified specification**. Basis of §1.27.15.
- <https://jsonapi.org/format/1.1/> — consulted via search. Source of sparse fieldsets
  (`?fields[type]=…` applying to primary and included resources), compound documents with the
  **full-linkage** requirement and its sparse-fieldset exception, and the rule that a media type with
  any parameter other than `ext` or `profile` gets a **415**. Basis of §1.22.4, §1.15.20–§1.15.21.

**OpenAPI**

- <https://learn.openapis.org/upgrading/v3.1-to-v3.2.html> and
  <https://www.openapis.org/blog/2025/09/23/announcing-openapi-v3-2> — consulted via search.
  Confirmed **OpenAPI 3.2.0 released 23 September 2025, non-breaking against 3.1**, and the feature
  list used in §1.23.13: the `QUERY` method, `additionalOperations` for non-standard methods,
  first-class streaming media types (`text/event-stream`, `application/jsonl`,
  `application/json-seq`, `multipart/mixed`), tag hierarchies, `deviceAuthorization` in the OAuth
  flows object, `oauth2MetadataUrl`, and deprecatable security schemes. Basis of §1.12.12,
  §1.23.2, §1.23.13. **Re-fetch the upgrading guide before writing the feature table.**

**Spring**

- <https://docs.spring.io/spring-framework/reference/web/webmvc-versioning.html> — fetched in full.
  Source of the entire §1.18.18 identifier list: the `version` attribute's three forms (absent,
  fixed, `"1.2+"` baseline); `ApiVersionConfigurer`'s `useRequestHeader`, `usePathSegment(int)`,
  `usePathSegment(int, Predicate<RequestPath>)`, `useQueryParam`, `useMediaTypeParameter`,
  `addSupportedVersions`, `setVersionRequired` (**default `true`**), `setDefaultVersion`,
  `detectSupportedVersions` (**default `true`**), `deprecateVersion(String, Instant, String)`;
  the `ApiVersionStrategy` / `ApiVersionResolver` / `ApiVersionParser` /
  `ApiVersionDeprecationHandler` SPI; `SemanticApiVersionParser` with `major[.minor[.patch]]` and
  minor/patch defaulting to 0; `StandardApiVersionDeprecationHandler` emitting **RFC 9745
  `Deprecation`, RFC 8594 `Sunset` and `Link`**; the exceptions `MissingApiVersionException` → 400,
  `InvalidApiVersionException` → 400, `NotAcceptableApiVersionException` → 406; and client/test
  support in `RestClient`, `WebClient`, HTTP interfaces, `MockMvc` and `WebTestClient`. Basis of
  §1.18.18 and §3.8.7.
- <https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html> and
  <https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/servlet/mvc/method/annotation/ResponseEntityExceptionHandler.html>
  — consulted via search. Source of `ProblemDetail`, `ErrorResponse`, `ErrorResponseException`,
  `ResponseEntityExceptionHandler` as the `@ControllerAdvice` base class handling all Spring MVC
  exceptions and any `ErrorResponse`, the `Content-Type: application/problem+json` behaviour, and
  the **`spring.mvc.problemdetails.enabled`** property whose auto-configured handler is at
  **order 0** so a custom advice must be ordered ahead of it. Basis of §1.16.16–§1.16.17,
  §3.8.5–§3.8.6. **Re-fetch to confirm the property default and the built-in
  exception→status table in §1.28.12.**

**Curriculum, interview surface and adversarial angles**

- <https://www.hellointerview.com/learn/system-design/core-concepts/api-design> — fetched. Mined
  purely for concept names, and it contributed the design-principles list ("design around resources
  not actions", "principle of least surprise", "safe retries and idempotency", "security by
  default", "actionable error messages"), the API-type taxonomy including RPC/Thrift, and the
  reminder that field-level authorisation and the N+1 problem are the two GraphQL items interviewers
  reliably probe. Cross-checked against the leaf list; the RPC/Thrift and field-level-authorisation
  leaves (§1.4.4, §1.27.12) exist because of it. Basis of parts of §5.1.
- <https://ptgmedia.pearsoncmg.com/images/9780137355631/samplepages/9780137355631_Sample.pdf> and
  the *Principles of Web API Design* table of contents (Higginbotham, Addison-Wesley, Dec 2021) —
  consulted via search. Contributed the **capability → activity → step → API boundary** design
  process in §1.5.1, the "REST-based vs RPC-based vs query-based" chapter split behind §1.4.3, the
  developer-experience chapter behind §2.13.6, and the "designing for change" chapter behind §1.18.
  Basis of §1.1.10's reading list.
- Search: "REST API gotchas pitfalls production incident postmortem breaking change enum client" —
  contributed the **GitHub REST schema-drift incident** (§2.5.6: production behaviour diverged from
  the published OpenAPI schema and documented HTTP semantics, breaking downstream tooling that
  treated the schema as the source of truth), the **enum-value removal/addition** incident pattern
  (§2.5.7), the mobile-clients-never-update constraint behind §1.1.3, and the
  `oasdiff`/`openapi-diff`-in-CI practice (§1.23.18, §2.5.3, §4.9.1).
- Searches: "what most people get wrong about REST", "PUT vs PATCH idempotent", "404 vs 410",
  "Richardson maturity model" — contributed the precise framing of §1.7.7 (the *instructions in the
  payload* determine PATCH idempotency, not the method), §1.8.16 (410 asserts prior existence and
  intentional permanent removal; use 404 when you do not know whether it is temporary), and
  §1.4.2 / §1.22.10 (level 2 is where essentially every production API sits, and level 3 is not
  mandatory).
- <https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm> — consulted via search.
  Source of the six constraints with **code-on-demand as the only optional one**, and of Fielding's
  2008 "REST APIs must be hypertext-driven" position that an API must be enterable "with no prior
  knowledge beyond the initial URI and set of standardized media types". Basis of §1.3.
  **The write pass must fetch chapter 5 directly to quote the constraint definitions.**
- Search: "API gateway backend for frontend pattern responsibilities" — contributed the gateway
  responsibility list (§2.11.1), the **"verify once, propagate"** pattern and its
  trusted-header hazard (§2.11.3), the explicit statement that **object-level authorisation must
  stay in the service** (§1.24.6, §2.11.2), and the **mega-gateway** anti-pattern name
  (§2.15.17).
- Search: "protobuf backward compatibility rules field numbers reserved" — contributed the
  field-number immutability rule, the "reserve the number **and** the name" rule (the name matters
  for JSON), the unknown-fields preservation behaviour, and the `json_name` breakage. Basis of
  §1.26.6.

**Searches that returned nothing usable**

- No published **university course syllabus** specifically on web API design was found; the
  curriculum angle was covered by the book tables of contents (Higginbotham, Lauret, Amundsen,
  Masse) and by Google's and Zalando's rule indexes instead.
- No authoritative primary source was found for the exact **Spring Boot default values** cited in
  §1.8.21 (`server.max-http-request-header-size` = 8 KB,
  `spring.servlet.multipart.max-file-size` = 1 MB) or for the `spring.mvc.problemdetails.enabled`
  default in §1.16.16. These are tagged `[NUM]` and the write pass **must** confirm them against
  the Boot common-application-properties appendix before printing them.
- No primary source was located for **Stripe's idempotency key lifetime and length limits**
  (§1.17.20); the leaf instructs the write pass to verify against Stripe's own documentation or
  drop the numbers.
- No stable published number was found for **per-request overhead of an idempotency lookup** or for
  JSON-vs-protobuf sizes on a realistic payload; §2.1.4 and §2.1.5 therefore instruct the write
  pass to compute the arithmetic from the QuizStakes payload rather than quote a benchmark.
- The IETF **`Idempotency-Key` draft has expired** (18 April 2026) with no successor located. The
  write pass must present it as "a widely-implemented expired draft plus a de facto industry
  convention", not as a standard.

## Gaps vs the current guide

`src/topics/12-api-design.md` is **327 lines** across 11 sections plus a 23-item checklist. Its
idempotency-key section, its safe/idempotent table, its `200`-with-error-body trap and its push-
mechanism decision rule are genuinely good and **must survive verbatim and expanded**. It is not a
bible: it has no HTTP-substrate layer, no complete status-code or header surface, no conditional
requests beyond one sentence, no caching arithmetic, no representation-design section, no PATCH
formats, no OpenAPI/contract tooling, no gRPC or GraphQL content **despite `00-index.md` promising
"gRPC and GraphQL trade-offs"**, no proofs, no build-it content, no interview set, and — most
importantly — it teaches the **invalid `Deprecation: true`** and cites the **obsolete RFC 7807**.

| Syllabus leaf group | Present in `src/topics/12-api-design.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why a contract exists, what it consists of, design-first, reading list | intro paragraph (3 lines) | ✅ the whole origin section, the contract inventory, coupling framing, the reading list | ✅ |
| §1.2 the HTTP substrate, RFC 9110–9114 map, structured fields, IANA registries, URI syntax, HTTP/2–3 impact | — | ✅ **entire section** — the guide never names an RFC except 7807 | |
| §1.3 Fielding's six constraints, uniform interface sub-constraints, hypertext-driven, statelessness dissected | § 1 (five constraints listed in one sentence) | ✅ code-on-demand, the four sub-constraints, the 2008 post, the intermediary list, the QuizStakes affinity exceptions | ✅ severely |
| §1.4 Richardson levels, the style taxonomy, SOAP/OData/JSON-RPC/Connect, the decision procedure | § 10 (level 3 named once, in the HATEOAS paragraph) | ✅ all four levels, the taxonomy, the decision procedure, the per-boundary answer | ✅ severely |
| §1.5 resource modelling, archetypes, nesting, ids, path-vs-query-vs-body-vs-header, Zalando URL rules | § 1 + § 10 (nouns/plural/hierarchical; the path/query/body/header list) | ✅ archetypes, discovery process, nesting depth rule, dual addressing, id design incl. UUIDv7, AIP-122 resource names, casing, base path | ✅ the path/query/body/header list and the no-secrets-in-query trap are strong and must be preserved verbatim |
| §1.6 the complete method surface incl. `QUERY`, `Allow`, override tunnelling | § 2 (seven methods, PUT/PATCH/POST/DELETE paragraphs) | ✅ `CONNECT`, `TRACE`, `QUERY`, `Accept-Query`, `Allow`, method extension, override tunnelling, `additionalOperations` | ✅ the PUT/PATCH/POST/DELETE paragraphs must be preserved verbatim and expanded |
| §1.7 safe/idempotent/cacheable as three orthogonal properties, with proofs | § 2 (the table + "why this matters practically" + the POST trap) | ✅ the RFC definitions verbatim, the implication chain, idempotency-vs-commutativity-vs-exactly-once, `idempotency_level`, the lying-about-safe cases, the per-endpoint retry table | ✅ **the table, the double-charge paragraph and the POST trap are the guide's best content and must be preserved verbatim** |
| §1.8 the complete status-code surface, 1xx–5xx, with the decision tree | § 3 (about 25 codes across 2xx/4xx/5xx + two traps) | ✅ all 1xx, all 3xx incl. the method-rewriting rule, ~15 missing 4xx, ~7 missing 5xx, `425`'s real meaning, the 400/422/409 split, the decision tree, the domain-vs-HTTP-code distinction, the QuizStakes mapping | ✅ the 401/403 trap and the 200-with-error-body trap must be preserved verbatim |
| §1.9 the header surface, all four groups, incl. `Prefer`, `Link`, digest/signature, trace | scattered mentions (`Location`, `Retry-After`, `WWW-Authenticate`, `Allow`, rate-limit headers) | ✅ **entire structured section** — the four groups, media-type trees, `Prefer`, `Link` + relations, RFC 9530/9421, `X-` deprecation, propagation, the header-size arithmetic, the QuizStakes header contract | ✅ |
| §1.10 representation design — envelopes, naming, nullability, numbers, money, time, enums, tolerant reader, encodings | § 6 (the pagination envelope only) | ✅ **entire section** — the 2^53 trap, money, RFC 3339, the enum-evolution hazard, `UNSPECIFIED`, boolean-vs-enum, `additionalProperties`, `FAIL_ON_UNKNOWN_PROPERTIES`, payload-size arithmetic | |
| §1.11 PATCH formats — JSON Patch, Merge Patch, JSON Pointer, field masks | § 2 (one line: "PATCH applies a partial modification") | ✅ **entire section** — both RFCs, the media types, the null-deletes rule, the operation list, atomicity, field masks, the Spring surface | ✅ severely |
| §1.12 content negotiation, q-values, `Vary`, compression | § 10 (three sentences) | ✅ q-value ordering worked, the 406-vs-default choice, `Vary` cardinality, compression arithmetic, media-type versioning interaction, the Spring SPI, 3.2 streaming types | ✅ severely |
| §1.13 conditional requests, ETags, optimistic concurrency, ranges | § 10 (one sentence on `ETag`/`If-None-Match`/`If-Match`) | ✅ strong-vs-weak validators, the precedence order, `If-None-Match: *`, `428`, the four ETag sources, the `ShallowEtagHeaderFilter` trap, collection ETags, the lost-update proof, ranges | ✅ severely — **this is the highest-value missing mechanism in the guide** |
| §1.14 HTTP caching — every directive, the freshness arithmetic, invalidation, the `Authorization` rule | § 10 (one sentence naming `max-age`/`no-store`/`private`) | ✅ **entire section** — the storability conditions, both directive lists, `no-cache` vs `no-store`, the age formulas, heuristic freshness, unsafe-method invalidation, `stale-while-revalidate`, the no-store default argument, the QuizStakes policy | ✅ severely |
| §1.15 collections — pagination, filtering, sorting, sparse fieldsets, inclusion | § 6 (offset vs cursor, the envelope, max limit, tiebreaker) | ✅ seek/snapshot/time-window schemes, cursor contents, totals policy, the four envelope shapes compared, empty/terminal pages, bidirectional cursors, AIP-158, all four filtering levels, sorting whitelists, sparse fieldsets, JSON:API inclusion and full linkage, the QuizStakes per-endpoint decisions | ✅ the offset/cursor paragraphs, the envelope and the max-limit/tiebreaker rules are strong and must be preserved verbatim |
| §1.16 the error contract | § 8 (RFC 7807 example + 5 rules) | ✅ **RFC 9457 correction**, the five members' exact semantics, `about:blank`, the type-URI rules, multiple-problems guidance, the problem-type catalogue as an artifact, the IANA registry, retryability, i18n, the full Spring surface, the gRPC/GraphQL equivalents, the QuizStakes catalogue | ✅ **the stable-code rule, the trace-id rule, the all-validation-errors rule and the no-leak rule must be preserved verbatim and expanded** |
| §1.17 idempotency keys end to end | § 5 (contract, DDL, 5-step flow, defence in depth) | ✅ the draft's exact header syntax and three error codes, scope/fingerprint definitions, the crash-window analysis, `IN_PROGRESS` alternatives, storage-choice comparison, the client's obligations, where a key is *not* needed, Stripe's reference behaviour, the key-table growth arithmetic | ✅ **this is the guide's strongest section — the DDL, the five-step flow, the insert-first rule, the same-transaction rule and the defence-in-depth paragraph must all be preserved verbatim and expanded** |
| §1.18 versioning and compatibility | § 7 (the three-scheme table, additive-vs-breaking, deprecation process) | ✅ the exhaustive breaking/non-breaking lists, the five sneaky breaks, date-based versioning in full, granularity, live-version cost, implementation strategies, expand/contract, event compatibility, **Spring 7's whole versioning API**, the pre-7 workarounds, the QuizStakes per-boundary decision | ✅ the "avoid versioning" argument and the additive-change list must be preserved verbatim |
| §1.19 deprecation and sunset | § 7 (the four-step process; **`Deprecation: true` is wrong**) | ✅ the lifecycle states, stability levels, **the corrected RFC 9745 syntax**, the `deprecation` link relation, the seven-step process, Zalando's four MUSTs, client-side monitoring, brownout, window guidance | ✅ **the `Deprecation: true` line must be corrected, not preserved**; the "never remove on a calendar alone" rule must be preserved verbatim |
| §1.20 rate limiting and quotas | § 9 (token bucket, three alternatives, the legacy headers, the distributed problem, key choice, fail-open/closed) | ✅ the rate/quota/shedding split, GCRA, the boundary-burst proof, the algorithm table, layered limits, **the current `RateLimit`/`RateLimit-Policy` syntax**, `Retry-After` precedence, the header-disclosure trade, the latency-budget arithmetic, concurrency limits, adaptive shedding, the enforcement-layer ranking, client obligations | ✅ the token-bucket definition, the distributed-complication paragraph and the key-choice paragraph are strong and must be preserved verbatim; **the header block must be corrected to draft-11** |
| §1.21 non-CRUD, async, bulk | § 4 (three modelling options, bulk `207`, `POST /search`) | ✅ AIP-136 custom methods, state machines as contracts, the full `202` + operation-resource flow, RELO vs stepwise, `google.longrunning.Operation`, `Prefer: respond-async`, cancellation, progress, polling arithmetic, bulk-vs-batch, the partial-failure table, AIP batch methods, size limits, **`QUERY` as the search fix**, import/export, upload contracts | ✅ the three modelling options and the `POST /search` pragmatism note must be preserved verbatim |
| §1.22 hypermedia and HATEOAS | § 10 (one paragraph: what it is, why teams skip it) | ✅ the actual claim, the payoff, the format zoo (HAL/HAL-FORMS/JSON:API/Siren/Collection+JSON/Hydra), the link-relation registry, Zalando's position, minimum viable hypermedia, **Spring HATEOAS's whole API**, discovery documents, the QuizStakes state-machine case | ✅ the "know the term, know why teams skip it" framing must be preserved |
| §1.23 OpenAPI, JSON Schema, AsyncAPI, linting, breaking-change CI | — | ✅ **entire section** — and it is the largest single omission after gRPC/GraphQL | |
| §1.24 the security face of the contract | scattered `13-web-security.md` pointers | ✅ the credential-transport rule, the auth status contract, scopes as a design artifact, the gateway/service split, **BOLA**, the OWASP API Top 10 as a design checklist, mass assignment, excessive data exposure, the CORS `Access-Control-Expose-Headers` trap, audit | ✅ |
| §1.25 polling / long polling / SSE / WebSocket / webhooks | § 11 (the five-row table, the webhook-design paragraph, the decision rule) | ✅ the SSE wire format and reconnection contract, the 6-connection limit, the WebSocket handshake and framing, subprotocols, the provider-obligation table, **Standard Webhooks in full**, its security requirements, thin-vs-fat payloads, the delta-query middle ground, the QuizStakes mapping | ✅ **the table, the webhook-design paragraph and the decision rule are excellent and must be preserved verbatim and expanded** |
| §1.26 gRPC as a contract | — (`00-index.md` promises it) | ✅ **entire section** — proto surface, field-number rules, the 17 status codes, deadlines, metadata, the rich error model, service config, gRPC-Web/Connect/transcoding, the comparison table, the Java surface | |
| §1.27 GraphQL as a contract | — (`00-index.md` promises it) | ✅ **entire section** — SDL, execution, partial success and null propagation, the media-type status-code correction, DataLoader, cost limiting, persisted queries, caching, per-field authz, versioning, subscriptions, `@defer`/`@stream`, federation, introspection, Spring for GraphQL | |
| §1.28 the Spring surface for an HTTP API | § 8 (one mention of Spring 6's `ProblemDetail`) | ✅ **entire section** — mappings, resolvers, return types, `ResponseEntity`/`CacheControl`, converters, Jackson-as-contract, records as DTOs, validation, exception handling, the built-in exception→status table, filters vs interceptors, the read-once body problem, `RestClient`/`WebClient`/HTTP interfaces, timeouts, resilience, async MVC, SSE, WebSocket, testing | ✅ severely |
| PART 2 — the master tables (incl. **the master cost table**) | — | ✅ all twelve | |
| PART 2 — style choice, BFF, migration | § 11 (the push decision rule only) | ✅ the rest | ✅ |
| PART 2 — idempotency in practice | § 5 (the defence-in-depth paragraph) | ✅ the endpoint audit, the natural-key and PUT-with-client-URI fixes, cross-boundary keys, the outbox pointer, the three tests, observability, the growth arithmetic | ✅ |
| PART 2 — pagination in practice | § 6 (partial) | ✅ the offset→cursor migration, cursor stability under schema change, the two-store union, deep-pagination DoS, the honest consistency promise, the property tests | ✅ |
| PART 2 — compatibility in practice | § 7 (partial) | ✅ the written policy, the tolerant-reader obligation, the CI gate, contract testing, field-usage telemetry, the GitHub incident, the enum incident, the QuizStakes migration | ✅ |
| PART 2 — error contracts in practice | § 8 (partial) | ✅ taxonomy design, the granularity trap, domain-to-HTTP mapping as a layer, the layering violation, the validation payload spec, downstream errors, the tests, the support workflow | ✅ |
| PART 2 — rate limiting in practice | § 9 (partial) | ✅ deriving the numbers, per-endpoint weights, tenant fairness, burst as a product decision, observe-only rollout, communication, the retry-storm proof, the unauthenticated-endpoint problem | ✅ |
| PART 2 — caching in practice | § 10 (one sentence) | ✅ the whole section including the cross-tenant leak and the read-model boundary | ✅ severely |
| PART 2 — timeouts, retries, backpressure | — | ✅ **entire section** including the retry-amplification proof and the QuizStakes budget chain | |
| PART 2 — webhooks in practice | § 11 (the design paragraph) | ✅ registration, the delivery pipeline, the published retry schedule, auto-disable, the delivery log, key rotation, fan-out arithmetic, the slow-consumer failure, testing, the inbound side | ✅ |
| PART 2 — the edge, gateway and BFF | — | ✅ **entire section** including the trusted-header bypass and the QuizStakes routing map | |
| PART 2 — observing and operating an API | § 8 (the trace-id rule) | ✅ the golden signals per endpoint, the cardinality trap, the missing metrics, Micrometer specifics, access-log rules, health vs readiness, synthetic contract canaries, the API-inventory problem, runtime introspection | ✅ |
| PART 2 — governance, style, DX | — | ✅ **entire section** including the full AIP index as a checklist | |
| PART 2 — version delta and the stale-answer sweep | — | ✅ **entire section** — and it is what makes the guide's own errors correctable | |
| PART 2 — the anti-pattern catalogue | scattered traps (5) | ✅ consolidated to 24, including the Spring-specific ones | ✅ |
| PART 3 — the wire (HTTP/1.1, 2, 3, curl transcript) | — | ✅ | |
| PART 3 — the gRPC wire protocol | — | ✅ | |
| PART 3 — the idempotency proof, crash windows, recovery | § 5 (asserts race-freeness without proving it) | ✅ the interleaving proof, the isolation analysis, the crash-window table, stuck-key recovery, the external-effect theorem | ✅ severely |
| PART 3 — cursor internals, row-value comparison, index requirement | § 6 (asserts constant time) | ✅ the encode/decode algorithm, the row-value-comparison trap, index and NULL requirements, the offset-cost proof, the shifting-window proof, the merge algorithm | ✅ severely |
| PART 3 — rate limiter internals, the Lua script, memory arithmetic | § 9 (names Redis `INCR`/Lua) | ✅ lazy refill, clock hazards, the script line by line, the sliding-window formula, the memory arithmetic, the round-trip cost | ✅ |
| PART 3 — caching and conditional-request internals | — | ✅ | |
| PART 3 — SSE and WebSocket internals | § 11 (one table row each) | ✅ both wire formats, reconnection, buffering hazards, connection-cost arithmetic, the handshake, frames, masking, close codes, the backplane, deploy behaviour | ✅ severely |
| PART 3 — the Spring MVC path for an API request | — | ✅ | |
| PART 3 — failure modes read at protocol level | — | ✅ all twelve | |
| PART 4 — build it (10 sections, 52 leaves) | — | ✅ **entirely absent** — no code in the current guide except the DDL and two JSON snippets | |
| PART 5 — the interview set, the trap index, the drills | — | ✅ **entirely absent** | |
| The existing 23-item `## Atomic concept checklist` | present | — | must survive **line for line**, with the `Deprecation` line corrected and one new line per mechanism above |

**Corrections the write pass must make to preserved content** (as opposed to additions):

1. § 7's `Deprecation: true` → RFC 9745's Structured Field Date form.
2. § 8's "RFC 7807" → RFC 9457, noting that 7807 is obsoleted and the media type is unchanged.
3. § 9's `RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset` block → draft-11's
   `RateLimit-Policy` + `RateLimit`, with the legacy trio kept and labelled as the de facto
   convention.
4. § 5's suggestion of `425 Too Early` for a concurrent duplicate → `409`, with `425`'s real
   TLS-early-data meaning stated.
5. § 4's `POST /orders/search` framing → keep the pragmatism, add `QUERY` as the standards-track
   answer.
6. Every `/orders`, `/orders/42`, `/orders/42/items`, `/payments`, `/refunds`, `/accounts/42` and
   `/jobs/abc` example → the QuizStakes equivalent.

---

## Leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.28 (28 sections) | **478** |
| PART 2 — Intermediate | §2.1–§2.15 (15 sections) | **146** |
| PART 3 — Under the hood | §3.1–§3.9 (9 sections) | **82** |
| PART 4 — Build it | §4.1–§4.10 (10 sections) | **52** |
| PART 5 — Interview and retention | §5.1–§5.3 (3 sections) | **181** |
| **Total** | **65 sections** | **939** |

Per-section leaf counts are stated inline after each section as `*(N leaves)*` and sum to 939.

Tag totals, counted across the file: **`[RESEARCH]` 159 leaves**, `[PROVE]` 285, `[TRAP]` 201
(including the 56 in §5.2), `[SOURCE]` 93, `[BUILD]` 52, `[VERSION-TRAP]` 50, plus `[SPEC]`,
`[NUM]`, `[HDR]`, `[CODE]`, `[API]`, `[WIRE]`, `[TABLE]`, `[FLOW]` and `[DIAG]` throughout.
`[X-REF]` leaves point at guides 03, 04, 05, 07, 08, 09, 10, 11, 13, 14, 15, 16, 18, 19, 20 and 22.

Every `[RESEARCH]` leaf carries a named source in `## Sources consulted` and must be re-verified
before the write pass commits a constant. The five numbers explicitly flagged as **unverified** —
Spring Boot's header/multipart/problemdetails defaults and Stripe's idempotency key limits — must be
confirmed or dropped, not guessed.

