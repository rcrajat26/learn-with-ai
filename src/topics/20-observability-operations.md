# 20 — Observability & Operations

Scope: how you know what your system is doing, how you ship changes safely, and what you do when it
breaks. This is the topic where "6 years of experience" is most visible or most obviously absent —
anyone can describe a REST endpoint; far fewer can describe how they'd know it was failing.

---

## 1. Logs, metrics, traces — three different questions

They are not interchangeable, and the distinguishing question is what makes them click.

| Pillar | Answers | Shape | Cardinality | Cost model |
|---|---|---|---|---|
| **Logs** | *"What exactly happened in this one case?"* | discrete timestamped events with arbitrary detail | unlimited | per GB ingested/stored — the expensive one |
| **Metrics** | *"How is the system behaving in aggregate, over time?"* | numeric time series with labels | must stay **low** | per time series |
| **Traces** | *"Where did the time go, across services, for this request?"* | a tree of spans with a shared trace ID | high (usually sampled) | per span, sampled |

**The workflow they form together:**
1. A **metric** alerts you — error rate is up, p99 latency doubled. Metrics are cheap enough to keep
   for everything, always, and to alert on.
2. A **trace** localises it — the latency is in the `payments` service's call to the fraud API, not in
   your code. Traces answer "which hop".
3. A **log** explains it — `PaymentClient: timeout after 5000ms calling POST /v2/score,
   correlationId=abc-123`. Logs answer "what and why".

Trying to do all three with one tool is the common anti-pattern in both directions: computing rates by
counting log lines (expensive, slow, and it breaks when logging is throttled) or putting a user ID in
a metric label (cardinality explosion, §4).

**"Monitoring vs observability"** is worth being able to state without buzzwords: *monitoring* is
checking known failure modes you predicted in advance (CPU > 80%, disk full). *Observability* is
being able to answer questions you **didn't** anticipate, from the data you already emit, without
shipping new code. The practical test: "can I find out whether this problem affects only customers on
the new pricing plan in the EU, right now?" If that needs a deploy, you have monitoring.

---

## 2. Structured logging, correlation IDs, and MDC

**Unstructured logs are strings; structured logs are data.**

```
# Unstructured — greppable at best, not queryable
2026-08-21 14:32:11 ERROR Payment failed for order 12345 after 3 retries

# Structured (JSON)
{"ts":"2026-08-21T14:32:11.412Z","level":"ERROR","logger":"PaymentService",
 "msg":"Payment failed","orderId":"12345","attempts":3,"gateway":"stripe",
 "errorCode":"card_declined","durationMs":4211,
 "traceId":"4bf92f3577b34da6","service":"checkout","version":"1.4.2"}
```

With structure you can ask: "error rate by `errorCode` for `gateway=stripe` over the last hour,
excluding `card_declined`" — a query, not a regex. Without it, you're writing awk pipelines against
free text whose format changes whenever someone edits a log statement.

**Rules:**
- Put variables in **fields**, not in the message string. The message should be a stable constant so
  you can group by it.
- Always include: timestamp (ISO-8601, UTC), level, logger, service name, **version/build SHA**
  (essential for correlating problems with deploys), environment, and the **trace/correlation ID**.
- Log the **inputs** that caused a failure, not just the exception. "Validation failed" is useless;
  "validation failed, field=expiryDate, value=13/2026" is a fix.
- Log exceptions with the stack trace as a field, and never `log.error(e.getMessage())` — that throws
  away the stack trace, which is the only part that tells you where it happened.
- **Never log secrets or PII**: passwords, tokens, full card numbers, national IDs, auth headers. Logs
  are widely readable, shipped to third parties, and retained for months. This is a compliance issue,
  and a redaction layer plus a review check is the practical defence.

### Correlation IDs / trace IDs

One request touches six services and produces log lines interleaved with thousands of others. Without
a shared identifier, reconstructing that request is impossible.

**Mechanism:** generate an ID at the edge (or accept an inbound one), store it in **MDC** (Mapped
Diagnostic Context — a `ThreadLocal` map that the logging framework automatically includes in every
line), and **propagate it on every outbound call**.

```java
@Component
class CorrelationIdFilter extends OncePerRequestFilter {
    static final String HEADER = "X-Correlation-Id";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        String id = Optional.ofNullable(req.getHeader(HEADER))
                            .filter(s -> !s.isBlank())
                            .orElseGet(() -> UUID.randomUUID().toString());
        MDC.put("correlationId", id);
        res.setHeader(HEADER, id);          // return it so users can quote it in bug reports
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.clear();                    // MANDATORY — threads are pooled and reused
        }
    }
}
```

```xml
<pattern>%d{ISO8601} %-5level [%X{correlationId}] %logger{36} - %msg%n</pattern>
```

**Propagation is the part that's easy to get wrong:**
- Outbound HTTP: add the header in a `RestTemplate`/`WebClient` interceptor, not by hand at each call
  site.
- Messages: put it in a message attribute/header so async consumers can continue the chain (and
  include it in DLQ'd messages — topic 14 §5).
- **MDC is `ThreadLocal`, so it does NOT cross `@Async`, executor, or reactive boundaries** without a
  `TaskDecorator` that copies the context. This is the single most common gap, and the symptom is
  correlation IDs that mysteriously vanish for exactly the operations you most want to trace.
- Scheduled jobs and consumers should generate their own ID at the start of each unit of work.

If you adopt OpenTelemetry (§5), use its `traceId` as the correlation ID rather than inventing a
parallel one, so logs and traces join up.

---

## 3. Log levels and stdout in containers

| Level | Meaning | Action |
|---|---|---|
| `ERROR` | something failed that needs human attention | should be rare; **every ERROR should be actionable** |
| `WARN` | unexpected but handled — a retry succeeded, a fallback fired, deprecated usage | worth a dashboard, not a page |
| `INFO` | significant business events — request received, order placed, job completed | the production default |
| `DEBUG` | detailed flow for diagnosing a specific problem | off in production, enabled temporarily |
| `TRACE` | extremely verbose — payloads, per-iteration state | development only |

**Discipline problems and their consequences:**
- **Everything at ERROR.** Validation failures on user input are not errors — they're expected
  business outcomes. Logging them at ERROR trains everyone to ignore the ERROR channel, and then the
  real error is invisible. Ask: "would I want to be woken up for this?" If not, it isn't ERROR.
- **Logging and rethrowing.** `catch (e) { log.error(...); throw e; }` at three levels produces three
  stack traces for one failure. **Log where you handle it, or rethrow with context — not both.**
- **Logging in a hot loop.** A per-item log line at 10k/s costs real CPU, real money, and can be
  slower than the work itself. Log summaries, sample, or use DEBUG.
- **Unbounded log growth from a retry storm.** When something breaks, logging volume often spikes 100×
  precisely when you need the logging pipeline to work. Rate-limit repetitive error logging.

**Make levels runtime-adjustable.** Spring Boot's `/actuator/loggers` lets you turn DEBUG on for one
package on one pod without a deploy — invaluable mid-incident, and it means you don't need to
pre-emptively log at DEBUG "just in case."

### Log to stdout in containers

**The rule: containerised applications log to stdout/stderr, as a stream, and nothing else.**

Why: the container runtime captures stdout and hands it to the platform's log driver, which ships it
to CloudWatch/Loki/Elasticsearch. That's the contract (twelve-factor: logs are an event stream, and
the app should not concern itself with routing or storage).

Writing to a file inside a container instead means:
- The file lives in the container's ephemeral writable layer and **disappears when the pod dies** —
  taking with it exactly the logs from the crash you're investigating.
- It fills the node's disk (a genuine way to take down a whole node and every pod on it).
- You need a sidecar or log-rotation setup that duplicates what the platform already does.
- `kubectl logs` shows nothing, which is disorienting for everyone else on the team.

Corollaries: don't configure Logback file appenders in a container profile; don't use async appenders
with unbounded queues (an OOM waiting for a log spike); and be aware that at very high volume the log
driver itself can apply backpressure and slow your application — another reason not to log per-item
in hot paths.

---

## 4. Metrics

### RED and the golden signals

**RED** (for request-driven services — the one to memorise):
- **Rate** — requests per second.
- **Errors** — failed requests per second, and as a proportion.
- **Duration** — the latency distribution.

**USE** (for resources): **Utilisation**, **Saturation** (queue depth — often the earliest warning),
**Errors**.

Google's **four golden signals** are RED plus **saturation** — how full the system is.

Instrument every service with RED per endpoint, plus dependency-level RED (per downstream call), plus
saturation of every pool you own (thread pool, connection pool, queue depth, consumer lag). That set
answers most questions.

### Percentiles, and why averages lie

> Average latency is the most misleading number in operations.

10,000 requests: 9,900 at 10 ms, 100 at 5,000 ms. Average = 59 ms — looks fine. But 100 users waited
five seconds, and if a page makes 10 backend calls, roughly **one in ten page loads** hits at least one
of them.

Track **p50** (typical experience), **p95**, **p99**, and **p99.9** (your worst-affected users, and
often the canary for saturation). The gap between p50 and p99 is itself the signal: a widening gap
means queueing, GC pauses, lock contention, or a bad instance — often before the average moves at all.

Two things people get wrong:
1. **You cannot average percentiles.** The mean of each pod's p99 is not the fleet p99. Aggregate the
   underlying **histograms**, then compute the percentile. (This is exactly why Prometheus histograms
   exist, and why `histogram_quantile()` operates on bucket sums.)
2. **Percentiles compose badly across a fan-out.** If a request calls 5 services each with a 1% chance
   of being slow, the chance of *at least one* slow call is ~5%. Your p99 depends on your
   dependencies' p99.9. Tail latency amplifies as fan-out grows.

**Histograms vs summaries:** a **histogram** records counts in pre-defined buckets, is aggregatable
across instances, and computes quantiles at query time (Prometheus). A **summary** computes quantiles
client-side and **cannot be aggregated**. Prefer histograms almost always; the cost is choosing
sensible buckets. Micrometer's `@Timed` / `Timer` with `publishPercentileHistogram()` is the standard
Spring setup.

### The cardinality trap

> **Trap:** A time series is created for **every unique combination of metric name and label values**.
> Adding a label with unbounded values multiplies your series count without bound.
>
> ```java
> // CATASTROPHIC — one time series per user, forever
> meterRegistry.counter("orders.placed", "userId", userId).increment();
> // Also bad: orderId, requestId, email, full URL path with IDs, raw exception message,
> //           timestamps, session IDs.
> ```
>
> A million users means a million time series. Prometheus keeps active series in memory and falls
> over; CloudWatch bills **per metric** and produces a five-figure invoice; Datadog bills per custom
> metric. This is one of the few mistakes that can take down your monitoring *and* generate a
> surprise bill from one line of code — and the monitoring dies exactly when you need it.

**Rules:** labels must be **bounded and low-cardinality** — endpoint (templated: `/orders/{id}`, never
`/orders/12345`), method, status class, service, region, version. High-cardinality identifiers belong
in **logs and traces**, which are built for it. Before adding a label, ask "how many distinct values
can this have, ever?" If the answer isn't a small number you can name, it doesn't go in a label.

### Types
**Counter** (monotonic — requests, errors; you query `rate()` of it), **Gauge** (a point-in-time value
that goes up and down — queue depth, active connections, pool utilisation), **Histogram/Timer**
(distributions — latency, payload size). Choosing a gauge where you needed a counter loses information
irrecoverably between scrapes.

**Business metrics matter too**: orders placed per minute, payments succeeded, signups. These often
detect problems that infrastructure metrics miss entirely — a deploy that breaks the checkout button
shows perfect CPU, latency, and error rates while orders quietly drop to zero. "Orders per minute
dropped 80%" is the alert that catches what nothing else does.

---

## 5. Tracing

A **trace** represents one request's journey; a **span** is one unit of work within it (an HTTP
handler, a DB query, a downstream call), with a start time, duration, parent span, and attributes.
Spans form a tree, and the visual waterfall immediately shows where time went.

**What tracing gives you that logs and metrics can't:** the *causal structure*. "This request took
3.2 s: 40 ms in the API gateway, 60 ms in checkout, then **2.9 s waiting on the inventory service**,
which spent it in a single query." You cannot get that from per-service latency metrics, because each
service's own p99 might look fine — only the composition is slow. It also reveals accidental N+1
patterns across service boundaries, which are invisible locally.

**OpenTelemetry (OTel)** is the vendor-neutral standard: one set of APIs, SDKs, and auto-instrumentation
agents, exporting to Jaeger, Tempo, Honeycomb, Datadog, or X-Ray. The pragmatic path for a Spring Boot
service is the **OTel Java agent** (`-javaagent:opentelemetry-javaagent.jar`), which auto-instruments
Spring MVC, JDBC, HTTP clients, and Kafka with no code changes, plus a handful of manual spans around
business-meaningful operations.

**Context propagation** uses the W3C `traceparent` header (and `tracestate`); across message brokers
it goes in message headers. This is the same problem as §2's correlation ID, and the same solution —
which is why you should use the OTel trace ID *as* your correlation ID and log it in every line. Then
a trace links to its logs and a log links to its trace.

**Sampling** is necessary because tracing everything at scale is expensive. **Head-based** sampling
decides at the start (simple, e.g. 1%, but you'll miss the rare slow request you actually care about).
**Tail-based** sampling buffers the whole trace and decides after seeing it — keep 100% of errors and
slow traces, 1% of successful fast ones. Tail-based is much more useful and needs a collector to do
the buffering. Always sample **consistently across services** (the decision propagates), or you get
broken partial traces.

---

## 6. Health endpoints

**Shallow (liveness):** "is this process alive and able to respond?" Returns 200 if the HTTP server
is up. Cheap, dependency-free, fast.

**Deep (readiness):** "can this instance actually serve requests?" Checks critical dependencies — the
database connection pool, a required downstream.

The critical design point is in topic 19 §8, and it bears repeating because it's the trap:

> **Deep checks must never drive restarts.** If liveness checks the database, a brief DB blip fails
> every pod's liveness probe simultaneously, Kubernetes restarts the entire fleet, and the restarts
> make recovery *harder* (cold caches, connection storms, no capacity). Restarting your pod does not
> fix someone else's database.

And the readiness caveat: if every pod reports not-ready because a *soft* dependency (a cache) is
down, the Service has zero endpoints and you're fully down when you could have served degraded. Only
**hard** dependencies belong in readiness.

**Practical setup** (Spring Boot):
- `/actuator/health/liveness` — shallow. Wired to the liveness probe.
- `/actuator/health/readiness` — includes hard dependencies and any warm-up gate (topic 15 §13).
  Wired to the readiness probe and to load-balancer target-group health checks.
- `/actuator/info` — build version, git SHA, build time. Surprisingly valuable: "which version is
  actually running on that pod?" is a question you'll ask during incidents.
- `/actuator/prometheus` — metrics scrape endpoint.
- Restrict actuator endpoints to an internal port or authenticated access; `/actuator/env` and
  `/actuator/heapdump` leak configuration and memory contents.

Also: health-check endpoints should be excluded from access logs and from latency metrics, or a probe
every 5 seconds from every source dominates your data and flatters your percentiles.

---

## 7. Deployment: CI vs CD, pipelines, and strategies

### CI vs CD — get this distinction exactly right

These are three different things and they are constantly conflated.

**Continuous Integration (CI)** is a **development practice**: every developer merges to a shared
mainline **frequently** (at least daily), and every merge is automatically **built and tested**. The
goal is to catch integration problems within minutes of them being created, rather than at the end of
a three-week branch.

> The essential part of CI is the *integrating* — merging small changes into trunk often. The
> automated build is the feedback mechanism that makes it safe. **A team with a beautiful Jenkins
> pipeline that runs on two-week-old feature branches is not doing CI.** The pipeline is not the
> practice.

**Continuous Delivery (CD)** means every change that passes the pipeline is **automatically deployed
to a production-like environment and is always in a releasable state**. Deploying to production is a
**business decision, executed by pressing a button**. The engineering work is done; the release is
gated on a human choosing when.

**Continuous Deployment (also CD)** goes one step further: every change that passes the pipeline is
**automatically released to production with no human approval**. No button.

| | Continuous Integration | Continuous Delivery | Continuous Deployment |
|---|---|---|---|
| What it is | a development practice | a pipeline property | a pipeline property |
| Merge to trunk | frequently, ≥ daily | ✔ (prerequisite) | ✔ (prerequisite) |
| Automated build + test | ✔ | ✔ | ✔ |
| Always releasable artefact | — | ✔ | ✔ |
| Deploy to prod | manual | **one button, any time** | **automatic, no button** |
| Requires | tests you trust | plus automated deploy + rollback | plus strong monitoring, feature flags, and real confidence |

The one-line version, worth being able to say verbatim: **"CI is about merging and testing frequently.
Continuous Delivery means it's always *ready* to release. Continuous Deployment means it *does*
release, automatically."**

The other thing to know is that **Continuous Deployment is not automatically the goal.** It requires
a test suite you genuinely trust, feature flags to decouple deploy from release, fast automated
rollback, and monitoring that catches problems in minutes. Continuous Delivery with a human gate is
the right answer for most teams, and saying so is a maturity signal, not a lack of ambition.

### Pipeline stages

```
commit
  → build                (compile, produce ONE immutable artefact)
  → unit tests           (fast: seconds; run on every commit)
  → static analysis      (lint, SpotBugs, SonarQube quality gate)
  → security scan        (dependency CVEs, secret scanning, SAST)
  → package              (container image, tagged with the git SHA)
  → integration tests    (Testcontainers: real Postgres, real Kafka)
  → publish to registry
  → deploy to staging    (automatic)
  → smoke / contract / e2e tests
  → deploy to production (manual gate = Continuous Delivery;
                          automatic = Continuous Deployment)
  → post-deploy verification (health, key metrics, canary analysis)
```

**Principles that matter more than the tool:**
- **Build the artefact once** and promote the *same* artefact through every environment. Rebuilding
  per environment means you test one binary and ship another (topic 18 §6).
- **Fail fast:** cheapest, fastest checks first. A 40-minute pipeline that fails on a lint error at
  minute 38 destroys the feedback loop that makes CI valuable.
- **A red build is stop-the-line.** A pipeline that's been failing for two days is not a pipeline.
- **Flaky tests are worse than no tests** — they teach the team to re-run and ignore, which is exactly
  the habit that lets a real failure through. Quarantine and fix them.
- Pipeline definitions live in the repo (`.gitlab-ci.yml`, `.github/workflows/`), reviewed like code.
- Keep it fast. Under 10 minutes to a deployable artefact is a reasonable target; parallelise and
  cache dependencies aggressively.

### Deployment strategies

| Strategy | Mechanism | Pros | Cons |
|---|---|---|---|
| **Recreate** | stop all old, start all new | simple | **downtime** |
| **Rolling** | replace pods incrementally (topic 19 §10) | no downtime, no extra infra | both versions run simultaneously; slow rollback |
| **Blue/green** | run two full environments; **switch traffic at the LB** | instant cutover, **instant rollback**, full test of green before traffic | 2× infrastructure during the switch; database migrations are the hard part |
| **Canary** | route a small % (1% → 5% → 25% → 100%) to the new version, watching metrics at each step | limits blast radius, real production validation | needs traffic-splitting and automated analysis; slower |
| **Feature flags** | deploy dark, enable per-user/percentage at runtime | decouples deploy from release; instant off-switch; per-user targeting | flag debt; combinatorial test surface |

Rolling is the Kubernetes default and fine for most services. **Canary is the strongest option for
risky changes** because it's the only one that validates against real production traffic with a
bounded blast radius. Blue/green is excellent when you need an instant, complete rollback and can
afford the duplicate capacity.

**Both versions run at once** in rolling and canary — which means every change must be **backward
compatible** with the version it's replacing: API contracts, message schemas, and database schemas
(see expand/contract below). This constraint is the source of most deployment incidents.

### Rollback enablers

Fast rollback is worth more than careful deployment, because you will get it wrong eventually and
mean-time-to-recovery is what users experience. What makes rollback possible:

- **Immutable, versioned artefacts** and a retained image history (topic 19 §6) — `kubectl rollout
  undo` or `set image` to the previous tag, in seconds.
- **Backward-compatible database migrations** — the hard part, below.
- **Feature flags** — turning a flag off is faster and safer than any deploy, and it's the only
  "rollback" that doesn't touch the artefact.
- **No irreversible side effects on startup** (a migration that drops a column, a one-way data
  transform).
- **A practised procedure.** Rollback that has never been tested is a hypothesis.

### Zero-downtime, and the graceful shutdown chain

Zero downtime requires **all** of the following, and the chain is only as strong as its weakest link
(topics 11 §6, 19 §10):

1. **Multiple replicas** across AZs.
2. A **rolling or blue/green** strategy with `maxUnavailable: 0`.
3. A **readiness probe** that only passes when the pod can genuinely serve (including cache warm-up).
4. A **`preStop` hook** (~5 s) so load-balancer deregistration propagates *before* SIGTERM.
5. **Exec-form `ENTRYPOINT`** so the JVM actually receives SIGTERM (not a shell).
6. **Graceful shutdown in the app**: stop accepting → drain in-flight → flush → close pools → exit 0.
7. **`terminationGracePeriodSeconds`** longer than preStop + the longest in-flight request.
8. **Backward-compatible** API, message, and database schema changes.
9. **Client-side retries with backoff and jitter** for the residual failures.

Break any one and you get the classic "a few 502s on every deploy" that teams live with for years.

### Expand/contract database migrations

The one pattern that makes schema changes compatible with rolling deploys and rollbacks. Renaming
`user_name` to `full_name` in one migration breaks the old pods the instant it runs, and breaks the
new pods if you roll back.

**Expand → migrate → contract, across three separate deploys:**

1. **Expand.** Add the new column `full_name` as **nullable**. Deploy code that **writes both** columns
   and **reads the old** one. Both old and new pods work; a rollback is safe.
2. **Backfill.** Copy `user_name` → `full_name` for existing rows, in batches to avoid locking.
3. **Migrate reads.** Deploy code that **reads the new** column and still writes both. Verify.
4. **Contract.** Deploy code that only uses `full_name`. *Then*, in a later release, drop `user_name`.

Rules that fall out of this: **never combine a schema change and a code change that depends on it in
the same deploy**; additive changes (new nullable column, new table, new index built concurrently) are
safe, destructive ones (drop, rename, narrow a type, add `NOT NULL` without a default) are not; and
every migration should be run against a production-sized dataset first, because a lock-taking
migration on a 200-million-row table is an outage regardless of how correct it is.

---

## 8. Incident response

The goal during an incident is **restore service**, not understand the bug. Those are different
activities and confusing them extends outages.

### The sequence

1. **Acknowledge and declare.** Someone is the **Incident Commander** — one person coordinating, who
   is explicitly *not* debugging. Unowned incidents produce five people investigating the same theory
   and nobody talking to stakeholders.
2. **Assess blast radius and severity.** Who is affected — all users or one tenant? Which
   functionality? Is data being lost or corrupted (that's a different, worse category)? Is it getting
   worse? Severity drives the response, and "how many users, doing what" is the first question a
   commander should ask.
3. **Mitigate before diagnosing.** This is the point people find counter-intuitive and it is the most
   important operational habit there is.

   > **Restore service first. Understand it afterwards.** If a deploy went out 10 minutes before the
   > alert, **roll it back** — you do not need to know which line broke. If one AZ is unhealthy, shift
   > traffic away. If a feature flag correlates, turn it off. If one bad pod is serving errors, kill
   > it. If a downstream is failing, shed load or serve stale.
   >
   > The diagnosis will be much easier in an hour, from logs and traces, with users unaffected and
   > nobody watching over your shoulder. Debugging in production while customers are down is slower,
   > more error-prone, and produces worse decisions. The instinct to find root cause first is a
   > developer instinct; suppressing it is what operational maturity looks like.

4. **What changed?** (Topic 17 §12.) Deploys, config, feature flags, infrastructure changes, traffic
   shifts, a dependency's deploy, certificate expiry, a data migration, or the calendar (month-end,
   DST). Correlate the symptom's start time with the change log. This resolves a large fraction of
   incidents in minutes.
5. **Communicate.** Regular updates on a fixed cadence (every 15–30 minutes), even when the update is
   "still investigating, no new information." Silence makes people escalate, join the call, and slow
   you down. Say what's affected, what you're doing, and when you'll next update. Post to the status
   page for customer-visible impact.
6. **Verify recovery** with metrics, not vibes. The error rate is back to baseline, the queue has
   drained, latency is normal — and check that a *backlog* isn't about to cause a second incident
   (topic 14 §2: a two-hour consumer outage leaves a backlog that can take much longer to drain than
   the outage lasted).
7. **Write a postmortem.**

### Postmortems

**Blameless** is the load-bearing word. Not because people should never be accountable, but for a
concrete practical reason: **if naming a cause gets someone punished, people stop telling you what
actually happened**, and you lose the information you need to fix the system. Systems that permit a
single human error to cause an outage are broken systems — a missing guardrail, not a missing
person. "Why was it possible for one command to do that?" is the productive question.

Contents: timeline (detection → mitigation → resolution, with timestamps), impact (users affected,
duration, revenue/SLO burn), contributing factors (plural — real incidents rarely have one cause),
what went well, what didn't, and **action items with owners and dates**. Distinguish *detection*
failures ("we found out from a customer") from *response* failures ("the runbook was wrong") from
*prevention* failures — they have different fixes.

Techniques: "5 whys" for depth (but beware it forces a single linear chain onto a multi-causal
event), and always ask **"how could we have detected this sooner?"** and **"how could we have
recovered faster?"** — those two usually produce better action items than root-cause elimination,
because the next incident will be different but detection and recovery are reusable.

A postmortem with no action items, or with action items nobody owns, is theatre. Track them like any
other work.

---

## 9. On-call, runbooks, and alerting design

### Alerting design — the principles that keep a rotation sustainable

**Alert on symptoms, not causes.**

- ✗ "CPU > 80%" — so what? A batch job at 90% CPU that's meeting its deadline is *good*. This pages
  you for a non-problem.
- ✓ "p99 latency > 2 s for 5 minutes" / "error rate > 1% for 5 minutes" / "checkout success rate
  dropped 20% week-over-week" — these mean **users are affected**, which is the only thing worth
  waking someone for.

Cause-based alerts are unbounded (there are infinitely many ways to break) and mostly don't correlate
with impact. Symptom-based alerts are few, stable, and always meaningful. Keep cause metrics on
**dashboards** for diagnosis, not in the paging path.

**Page vs dashboard vs ticket — every alert must be classified:**

| Route | Criterion |
|---|---|
| **Page** (wake someone) | user-visible impact **and** requires immediate human action |
| **Ticket** (business hours) | needs a human but not right now — a disk at 70%, a certificate expiring in 20 days, a slow memory leak |
| **Dashboard only** | context for diagnosis; no action implied |

**Every page must be actionable.** If the response is "look at it and go back to sleep", it isn't a
page — it's a ticket or a dashboard. Alert fatigue is the dominant failure mode of on-call: a rotation
receiving 30 pages a night stops reading them, and the one that mattered is lost in the noise. Ruthlessly
delete alerts that have never led to action.

**Burn-rate alerting** (briefly): rather than a static threshold, alert on the **rate at which you're
consuming your error budget**. Fast burn (e.g. 2% of the monthly budget in an hour) → page. Slow burn
(10% over three days) → ticket. This automatically scales the urgency to the actual impact and largely
solves the "threshold too sensitive vs too insensitive" problem. Multi-window, multi-burn-rate alerts
are the SRE-book standard, and knowing the term is a good signal.

Other essentials: alert on **absence** too (no orders in 10 minutes, no heartbeat from a job, zero
traffic — a silent failure is still a failure); alert on **saturation** (queue depth, consumer lag,
pool utilisation) because it warns you *before* users are affected; and require a `for:` duration so a
30-second blip doesn't page anyone.

### Dashboards

Design for a specific question and a specific reader.

- **Service overview** — RED metrics per endpoint, dependency health, saturation, deploy markers.
  This is the one you open first during an incident, so it must load fast and fit on one screen.
- **Business** — orders, signups, revenue per minute. Catches what infrastructure metrics miss.
- **Deep-dive per subsystem** — for diagnosis once you know roughly where the problem is.

**Deploy annotations are the highest-value, lowest-effort addition to any dashboard**: a vertical line
at each deploy makes "what changed?" answerable at a glance. Put the most important panel top-left
(people read in that order), use consistent time ranges, and prefer a few well-chosen panels over
forty — a dashboard nobody can parse under stress is worse than three graphs that everyone can.

### Runbooks

A runbook is written for someone at 3am with no context — possibly you, tired, six months from now.

Each should contain: **what the alert means** in plain language, **how to assess severity and blast
radius**, **the first three things to check** (with copy-pasteable commands and dashboard links),
**known causes and their fixes**, **how to mitigate** (including "roll back" as an explicit named
option), **when and who to escalate to**, and **links** to the dashboard, the service's repo, and past
incidents.

Link the runbook **from the alert itself** — a runbook nobody can find during an incident does not
exist. Update it after every incident that used it; the best time to write a runbook is immediately
after you've just needed one.

### On-call basics

Sustainable rotations have: enough people (a 1-in-6 or better rotation, never 1-in-2), a clear primary
and secondary, an explicit escalation path, **compensation or time off in lieu**, and a hard rule that
**the person paged overnight does not work a normal day afterwards**.

Handover between shifts should cover what's currently degraded, what changed, and what to watch. And
the most important cultural rule: **on-call load is a metric to be driven down.** If the rotation is
painful, that's a signal about system quality and alert hygiene, not a personal endurance problem. A
standing agenda item to review last week's pages and delete or fix the useless ones is what keeps it
from degrading.

---

## 10. SLOs and error budgets

- **SLI** (indicator) — the measurement: "proportion of requests served successfully in under 300 ms."
- **SLO** (objective) — the internal target: "99.9% of requests, over 30 days."
- **SLA** (agreement) — the contractual promise with financial consequences. Always **looser** than
  your SLO, so you have margin before breaching a contract.

**The error budget is the point.** 99.9% over 30 days = **43 minutes** of allowed failure. That budget
is not waste — it is a **resource you are meant to spend** on shipping features, running experiments,
and doing risky migrations. This reframes the perpetual argument between product ("ship faster") and
operations ("stop breaking things") into a shared, quantitative decision:

- **Budget remaining** → ship. Take the risk. Deploy on Friday if you want.
- **Budget exhausted** → the team stops feature work and spends it on reliability until the budget
  recovers.

Two things worth stating:
1. **100% is the wrong target.** It's unachievable (your dependencies aren't 100%), infinitely
   expensive, and it means you're shipping too slowly. Every nine costs roughly an order of magnitude
   more than the last. Pick the level users actually notice.
2. **Measure the SLI from the user's perspective**, as close to them as possible. Your load balancer's
   view is better than your app's (it sees requests your app never received); a synthetic canary or
   real-user monitoring is better still. An SLO measured only inside the service will happily report
   99.99% while the ingress is returning 502s.

Availability targets in real terms, worth memorising:

| SLO | Downtime / 30 days | Downtime / year |
|---|---|---|
| 99% | 7.2 hours | 3.65 days |
| 99.9% | 43 minutes | 8.76 hours |
| 99.95% | 21.6 minutes | 4.38 hours |
| 99.99% | 4.3 minutes | 52.6 minutes |

Note that 99.99% means detecting *and* recovering in under 4 minutes per month — which is impossible
with a human in the loop. Anything above 99.9% is a statement about automation, not about effort.

---

## Atomic concept checklist

- [ ] **Logs = what happened in one case; metrics = aggregate behaviour over time; traces = where time went across services.**
- [ ] Workflow: metric alerts → trace localises → log explains.
- [ ] Monitoring answers questions you predicted; **observability answers ones you didn't**, without a deploy.
- [ ] Structured (JSON) logs turn grep into query — put variables in **fields**, keep the message constant.
- [ ] Always log: timestamp, level, service, **version/git SHA**, environment, trace ID.
- [ ] Log the inputs that caused the failure, and never `log.error(e.getMessage())` — you lose the stack trace.
- [ ] **Never log secrets or PII.**
- [ ] Correlation ID: generate at the edge, store in **MDC**, return in a response header, propagate on every call.
- [ ] **`MDC.clear()` in a `finally`** — pooled threads leak context otherwise.
- [ ] MDC doesn't cross `@Async`/executor/reactive boundaries without a `TaskDecorator` — the most common gap.
- [ ] Use the OTel `traceId` as the correlation ID so logs and traces join.
- [ ] Level discipline: ERROR only if actionable; validation failures are not errors.
- [ ] Don't log-and-rethrow at every layer; log where you handle.
- [ ] Make log levels runtime-adjustable (`/actuator/loggers`) so you can debug without deploying.
- [ ] **Containers log to stdout/stderr** — files vanish with the pod, fill the node, and bypass `kubectl logs`.
- [ ] **RED** = Rate, Errors, Duration; **USE** = Utilisation, Saturation, Errors; golden signals = RED + saturation.
- [ ] Instrument RED per endpoint, per dependency, plus saturation of every pool you own.
- [ ] **Averages lie** — track p50/p95/p99/p99.9; a widening p50→p99 gap signals queueing or contention.
- [ ] **You cannot average percentiles** — aggregate histograms, then compute the quantile.
- [ ] Tail latency amplifies with fan-out: your p99 depends on your dependencies' p99.9.
- [ ] Histograms aggregate across instances; summaries don't. Prefer histograms.
- [ ] **Cardinality trap: never put user/order/request IDs in metric labels** — it kills Prometheus and inflates the bill.
- [ ] High-cardinality identifiers belong in logs and traces, which are designed for it.
- [ ] Counter (monotonic) vs gauge (up/down) vs histogram (distribution) — choose deliberately.
- [ ] **Business metrics** catch failures infrastructure metrics miss (orders drop to zero, CPU looks perfect).
- [ ] A trace is a tree of spans and reveals **causal structure** across services that per-service metrics can't.
- [ ] OpenTelemetry is the vendor-neutral standard; the Java agent auto-instruments most of a Spring app.
- [ ] Propagation via W3C `traceparent`; message headers for async hops.
- [ ] **Tail-based sampling** keeps 100% of errors and slow traces; sample consistently across services.
- [ ] Liveness = shallow and local; readiness = can I serve now (hard dependencies only).
- [ ] **Deep checks must never drive restarts** — a DB blip would restart the whole fleet and prevent recovery.
- [ ] Expose `/actuator/info` with the git SHA; restrict `/actuator/env` and `/heapdump`.
- [ ] Exclude health checks from access logs and latency metrics.
- [ ] **CI = merge to trunk frequently + automated build/test.** The practice is the merging, not the pipeline.
- [ ] **Continuous Delivery = always releasable; deploy is one button.** **Continuous Deployment = no button, it deploys itself.**
- [ ] Continuous Deployment isn't automatically the goal — it needs trusted tests, flags, fast rollback, and real monitoring.
- [ ] **Build the artefact once** and promote the same one through every environment.
- [ ] Fail fast: cheapest checks first; a red build is stop-the-line; flaky tests are worse than no tests.
- [ ] Strategies: recreate (downtime), rolling (default), blue/green (instant rollback, 2× infra), canary (bounded blast radius), feature flags (deploy ≠ release).
- [ ] Rolling and canary run **both versions simultaneously** — every change must be backward compatible.
- [ ] Rollback enablers: immutable tags, retained images, compatible migrations, feature flags, no irreversible startup side effects, a **practised** procedure.
- [ ] Zero-downtime chain: replicas → `maxUnavailable: 0` → readiness → `preStop` → exec-form ENTRYPOINT → graceful shutdown → grace period → compatible schemas → client retries.
- [ ] **Expand/contract**: add nullable column → write both → backfill → read new → drop old, across separate deploys.
- [ ] Never ship a schema change and the code that depends on it in the same deploy.
- [ ] Incident: declare a commander who coordinates rather than debugs; assess blast radius first.
- [ ] **Mitigate before diagnosing** — roll back, shift traffic, flip the flag. Understand it later, calmly.
- [ ] **Ask "what changed?"** and correlate with the deploy/config timeline.
- [ ] Communicate on a fixed cadence even with no news; silence causes escalation.
- [ ] Verify recovery with metrics, and check the backlog isn't about to cause a second incident.
- [ ] **Blameless postmortems** — because punishment destroys the information you need.
- [ ] Ask "how could we have detected this sooner / recovered faster?" — more reusable than root-cause elimination.
- [ ] Action items need owners and dates, or the postmortem is theatre.
- [ ] **Alert on symptoms (user impact), not causes (CPU).**
- [ ] Classify every alert: **page** (impact + immediate action), **ticket**, or **dashboard only**.
- [ ] Every page must be actionable; alert fatigue is the main way on-call fails.
- [ ] **Burn-rate alerting** scales urgency to error-budget consumption: fast burn pages, slow burn tickets.
- [ ] Alert on **absence** (no orders, no heartbeat) and on **saturation** (queue depth, consumer lag).
- [ ] Dashboards: RED + dependencies + saturation, with **deploy annotations**, on one screen.
- [ ] Runbooks: what the alert means, first three checks with commands, known causes, how to mitigate, escalation — **linked from the alert**.
- [ ] Sustainable on-call: ≥1-in-6, clear escalation, compensation, no normal workday after a night of pages.
- [ ] **On-call load is a metric to drive down**, not an endurance test.
- [ ] SLI (measurement) → SLO (internal target) → SLA (contract, always looser than the SLO).
- [ ] **The error budget is a resource to spend**: budget left → ship; budget gone → fix reliability.
- [ ] 100% is the wrong target; measure the SLI from the **user's** vantage point, not inside the service.
- [ ] 99.9% = 43 min/month; 99.99% = 4.3 min/month, which implies automated detection and recovery.