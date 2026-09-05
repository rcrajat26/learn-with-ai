# Syllabus — 20 Observability & Operations

**Target versions, all checked 2026-09-05:**

| Layer | Release this file targets | Also covered because estates run it |
|---|---|---|
| OpenTelemetry Java SDK | **1.65.0** (2026-08-07) | 1.4x–1.5x (`opentelemetry-exporter-zipkin` still published) |
| OpenTelemetry Java agent | **2.x** — `http/protobuf` is the default OTLP protocol from 2.0, **not** `grpc` | 1.x agents, where `grpc` was the default |
| OpenTelemetry spec | Trace SDK with **composable samplers** (development), `ProbabilitySampler` (development, W3C Level 2 consistent probability sampling), stable `TraceIdRatioBased` (now marked deprecated) | pre-composable spec: only AlwaysOn/AlwaysOff/TraceIdRatioBased/ParentBased |
| Semantic conventions | **HTTP semconv stable**: `http.server.request.duration` / `http.client.request.duration` in **seconds** | the pre-1.21 `http.server.duration` in **milliseconds** with `http.method`/`http.status_code` |
| W3C Trace Context | **Level 1 — W3C Recommendation, 23 Nov 2021**, version `00` only | Level 2 (in progress: random-trace-id flag, `ot` tracestate for consistent sampling) |
| Prometheus | **3.14.0** (2026-08-17). UTF-8 metric/label names by default, left-open range selectors, native histograms stable | 2.x: legacy metric-name charset, right-open ranges, native histograms behind `--enable-feature=native-histograms` |
| Prometheus native histograms | **stable in 3.8**; scraping requires explicit `scrape_native_histograms: true` since 3.8; both scrape and `send_native_histograms` **default to `true` from v4** | 2.4x behind the feature flag |
| Remote write | **Remote-Write 2.0** (`io.prometheus.write.v2.Request`, symbols table) | Remote-Write 1.0 (`prometheus.WriteRequest`) |
| Micrometer | **1.17.x GA**, 1.18.0-M1 in flight; 1.16.x / 1.15.x in maintenance | 1.12–1.14 (pre-Observation-API-maturity) |
| Spring Boot | **3.5.x** is the baseline for all code in this repo (project convention: Spring Boot 3.x). **4.1.x** deltas called out per leaf | 2.7 (`micrometer-core` only, no Observation API, no `management.tracing.*`) |
| async-profiler | **4.5** | 2.x/3.x (`profiler.sh` era) |
| Java runtime for all code | **Java 21 LTS** | — |

**The version deltas that most often produce a stale answer in a 2026 observability
interview** — each carries `[VERSION-TRAP]` at its leaf:

1. **HTTP metric names and units changed.** Stable semconv is
   `http.server.request.duration` in **seconds** with attributes `http.request.method`,
   `http.response.status_code`, `http.route`, `url.scheme`, `error.type`. The old
   `http.server.duration` in **milliseconds** with `http.method`/`http.status_code` is gone.
   Spring Boot's own Micrometer name is a *third* thing: `http.server.requests`. `[RESEARCH]`
2. **The OTel Java agent defaults to `http/protobuf`, not `grpc`, from 2.0.** Answering
   "OTLP defaults to gRPC on 4317" is right for the *SDK* autoconfigure default and wrong for
   the *agent* 2.x default (4318). `[RESEARCH]`
3. **`TraceIdRatioBased` is stable but deprecated** and the spec says its "exact algorithm was
   never specified" — use it for root spans only. The successor is `ProbabilitySampler` /
   composable samplers using 56 bits of randomness. `[RESEARCH]`
4. **Prometheus 3.x range selectors and the lookback delta are left-open.** `[5m]` at time `t`
   now covers `(t-5m, t]`, not `[t-5m, t]`. Off-by-one-sample differences in `increase()` come
   from this. `[RESEARCH]`
5. **Prometheus 3.x allows all UTF-8 in metric and label names by default.** The
   `[a-zA-Z_:][a-zA-Z0-9_:]*` rule is a 2.x answer; quoting syntax (`{"my.metric"}`) exists now.
   `[RESEARCH]`
6. **Native histograms are stable and are the recommended default** — "if you can, use native
   histograms and prefer them over both classic histograms and summaries." But since 3.8 you
   must set `scrape_native_histograms: true`; it only defaults on in v4. `[RESEARCH]`
7. **Remote-Write 2.0 exists** with a symbols/string-interning table, mandatory
   `X-Prometheus-Remote-Write-Samples-Written` style response headers, and created-timestamp +
   metadata + native histogram + exemplar support. `[RESEARCH]`
8. **`opentelemetry-exporter-zipkin` stopped being published in 1.65.0.** `[RESEARCH]`
9. **Actuator endpoints are governed by `management.endpoints.access.default` /
   `management.endpoint.<id>.access` (`none`/`read-only`/`unrestricted`) plus
   `management.endpoints.access.max-permitted`**, not only by the older `.enabled` flags.
   `[RESEARCH]`
10. **`management.observations.annotations.enabled=true` is what turns on `@Observed`,
    `@Timed`, `@Counted`, `@MeterTag`, `@NewSpan`** — plus an `aspectjweaver` dependency. The
    annotations are inert without it. `[RESEARCH]`
11. **`spring.task.execution.propagate-context=true` / a `ContextPropagatingTaskDecorator` bean
    is the supported fix for MDC-and-trace-context across `@Async`**, and
    `spring.reactor.context-propagation=auto` for reactive. Hand-rolled `TaskDecorator`s are
    the 2.7-era answer. `[RESEARCH]`
12. **DORA is five metrics, not four**: Deployment Frequency, Change Lead Time, Change Fail
    Rate, Failed Deployment Recovery Time, and **Deployment Rework Rate** — split into
    throughput and instability. "MTTR" is not the current name. `[RESEARCH]`
13. **`-XX:+UseContainerCpuShares` was removed in JDK 21** (relevant to every
    `availableProcessors()`-derived pool-size metric you will look at). `[X-REF 19]`
14. **OTel `isEnabled()` on Tracer/Logger/instruments is stable (1.61.0)** — the supported way
     to skip building expensive attributes when nothing is listening. `[RESEARCH]`

---

# PART 1 — BASICS: why observability exists, the model, the vocabulary, the full API surface, the guarantees

## 1A. Origin and framing

1. Why observability exists at all: distributed systems have **no single place to put a
   breakpoint**; the debugger died at the process boundary. `[PROVE]` — an argument, not a slogan.
2. Control-theory origin of the word: observability = can you infer internal state from external
   outputs. Where the borrowed definition helps and where it is hand-waving.
3. **Monitoring vs observability**, stated without buzzwords: monitoring checks failure modes you
   predicted; observability answers questions you did not anticipate, from data you already emit,
   **without shipping code**.
4. The practical test for the distinction: "can I find out whether this affects only customers on
   the new pricing plan in the EU, right now?" If that needs a deploy, you have monitoring.
5. Known-knowns / known-unknowns / unknown-unknowns as the taxonomy the distinction maps onto.
6. What observability replaced: SSH-to-the-box + `tail -f`, Nagios-style host checks, per-host
   dashboards. Why each broke at the point of horizontal scaling and ephemeral compute.
7. Telemetry vs observability vs monitoring vs APM vs SRE — four words people use
   interchangeably and what each actually names.
8. The economic frame: observability spend is typically 10–30% of infra spend, which is why every
   design decision in this topic is also a cost decision. Forward pointer to §2H.
9. **[TRAP]** "We have Datadog, so we have observability." Tooling is not instrumentation; a
   vendor cannot emit a field your code never wrote.

## 1B. The three pillars, and why three is the wrong number

10. **Logs** — "what exactly happened in this one case?" Discrete timestamped events, arbitrary
    detail, unlimited cardinality, billed per GB ingested/stored.
11. **Metrics** — "how is the system behaving in aggregate over time?" Numeric time series with
    labels, cardinality must stay low, billed per time series.
12. **Traces** — "where did the time go, across services, for this request?" A tree of spans
    sharing a trace ID, high cardinality, usually sampled, billed per span.
13. The **workflow the three form together**: metric alerts → trace localises the hop → log
    explains the cause. Each pillar answers a different question in a fixed order.
14. The two symmetric anti-patterns: computing rates by counting log lines; putting a user ID in
    a metric label.
15. **Profiles as the fourth pillar** — "where did the CPU/allocation go, inside one process."
    OTLP Profiles data model released in **alpha in OTel Java 1.62.0**. `[RESEARCH]`
16. **Events / wide events** as the argument that the three pillars are an artefact of storage
    engines, not of questions. One wide event per unit of work with 300+ dimensions, from which
    metrics and traces are **derived** rather than separately emitted.
17. **High cardinality** — definition: number of distinct values a field can take. Why it is the
    resource metrics systems cannot afford and event stores can.
18. **High dimensionality** — number of *fields* per event, distinct from cardinality of any one
    field. Why both matter for unknown-unknowns.
19. Pre-aggregation as **irreversible information loss**: once you have `count by status`, no
    query can recover "which user, on which build, in which region."
20. "Observability 2.0" as the marketing name for the single-wide-event-store position; what is
    substantive in it and what is positioning. `[RESEARCH]` — Honeycomb's own concepts page did
    not carry the term; treat as vendor vocabulary, not spec.
21. **Correlation as the real deliverable**: exemplars (metric→trace), trace ID in logs
    (log→trace), span links (trace→trace), and resource attributes (everything→deployment).
22. **[TRAP]** Emitting all three pillars separately for the same event and getting three
    inconsistent answers, because each was filtered/sampled/aggregated differently.

## 1C. Logging — the API surface and the contract

23. Unstructured vs structured logging, with the concrete before/after: a greppable string vs a
    JSON object with typed fields.
24. Why structure is the whole point: "error rate by `errorCode` for `gateway=stripe` over the
    last hour, excluding `card_declined`" is a query, not a regex.
25. **Rule: variables go in fields, the message string stays a stable constant** so you can group
    by it.
26. The mandatory field set: ISO-8601 UTC timestamp, level, logger, service name,
    **version / git SHA**, environment, trace ID, span ID.
27. Why version/build SHA is load-bearing: correlating a symptom with a deploy is the highest-hit
    diagnostic move there is.
28. Log the **inputs** that caused a failure, not just the exception:
    "validation failed, field=expiryDate, value=13/2026" is a fix; "validation failed" is not.
29. **`log.error(e.getMessage())` throws away the stack trace** — the only part that says where it
    happened. Pass the throwable as the last argument.
30. **Never log secrets or PII**: passwords, tokens, full PANs, national IDs, `Authorization`
    headers, session cookies. Compliance issue, not a style issue. `[X-REF 13]`
31. Redaction as a layer (a Logback/Log4j2 rewrite policy or a converter), plus a review check —
    not "remember not to."
32. SLF4J as the facade; Logback vs Log4j2 vs `java.util.logging` as bindings; why exactly one
    binding must be on the classpath.
33. **Parameterised logging** `log.debug("x={}", x)` vs string concatenation, and what
    `isDebugEnabled()` still buys you (argument construction, not formatting).
34. Logger naming by fully-qualified class name, and why that is what makes per-package level
    control possible.
35. Log levels: `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE` — the meaning and the required action
    for each, as a table.
36. `ERROR` should be rare and **every ERROR should be actionable**. The test: "would I want to
    be woken up for this?"
37. **[TRAP]** Everything at ERROR. Validation failures on user input are expected business
    outcomes; logging them at ERROR trains the team to ignore the channel.
38. **[TRAP]** Log-and-rethrow at three layers produces three stack traces for one failure. Log
    where you handle, or rethrow with context — not both.
39. **[TRAP]** Logging in a hot loop: a per-item line at 10k/s can cost more than the work.
40. **[TRAP]** Unbounded log growth from a retry storm — volume spikes 100× exactly when the
    pipeline must keep working. Rate-limit repetitive error logging.
41. Runtime-adjustable levels via `/actuator/loggers` (`POST {"configuredLevel":"DEBUG"}` on one
    package, on one pod, no deploy).
42. **Log to stdout/stderr in containers, as a stream, and nothing else** — twelve-factor: logs
    are an event stream; the app does not route or store them.
43. What writing to a file in a container costs you: it dies with the pod, it fills the node's
    disk (a real way to kill every pod on that node), it needs a redundant sidecar, and
    `kubectl logs` shows nothing. `[X-REF 19]`
44. Corollaries: no Logback file appenders in a container profile; no unbounded async queues; the
    log driver itself can apply backpressure and slow the application.
45. MDC (Mapped Diagnostic Context) as a `ThreadLocal<Map<String,String>>` the framework injects
    into every line; `%X{key}` in the pattern.
46. `MDC.put` / `MDC.get` / `MDC.remove` / `MDC.clear` / `MDC.getCopyOfContextMap` /
    `MDC.setContextMap` — the whole surface.
47. **`MDC.clear()` (or scoped put/remove) in a `finally`** — mandatory, because threads are
    pooled and reused. `[X-REF 05]`
48. Correlation ID: generate at the edge or accept inbound, put in MDC, **return it in a response
    header** so users can quote it, propagate on every outbound call.
49. Propagation surfaces: `RestClient`/`WebClient`/`RestTemplate` interceptors, Feign
    request interceptors, Kafka record headers, SQS message attributes, gRPC metadata.
50. **[TRAP]** MDC does not cross `@Async`, executor, or reactive boundaries without context
    propagation — the single most common gap, and it vanishes exactly for the operations you most
    want to trace.
51. Scheduled jobs and message consumers must **generate their own ID** at the start of each unit
    of work.
52. Prefer the OTel `traceId` as the correlation ID rather than inventing a parallel one, so logs
    and traces join.
53. Trace-ID injection into MDC by the OTel Java agent
    (`trace_id`, `span_id`, `trace_flags`) and the corresponding Micrometer Tracing behaviour
    (`traceId`, `spanId`). Names differ — pick one and put it in the pattern. `[RESEARCH]`

## 1D. Metrics — the model and the instrument types

54. A **time series** = metric name + a set of label key/value pairs; one series per unique
    combination. This one sentence is the source of every cardinality problem.
55. **Counter** — monotonically increasing, reset only on process restart. Query the `rate()`, never
    the raw value.
56. **Gauge** — an instantaneous value that moves both ways: queue depth, active connections, pool
    utilisation, heap used.
57. **Histogram** — bucketed distribution, aggregatable, quantiles computed at query time.
58. **Summary** — client-computed quantiles, **not aggregatable**.
59. **Choosing a gauge where you needed a counter loses information irrecoverably between scrapes.**
    `[PROVE]` — show the sampling argument.
60. Micrometer meter types in full: `Counter`, `Gauge`, `Timer`, `LongTaskTimer`,
    `DistributionSummary`, `FunctionCounter`, `FunctionTimer`, `TimeGauge`, `MultiGauge`.
    `[RESEARCH]`
61. `Timer` vs `LongTaskTimer`: a `Timer` records only completed durations, so a task that has run
    for 40 minutes and not finished is **invisible**; `LongTaskTimer` reports in-flight duration.
62. `FunctionCounter` / `FunctionTimer` / `TimeGauge` as **thin wrappers over an existing
    monotonic source** you do not own (a JDBC pool's counters, a Kafka consumer's metrics).
63. `MultiGauge` for a set of gauges whose label values come and go, and its `register(rows, true)`
    overwrite semantics.
64. **Gauges hold weak references to the object being measured** — the classic "my gauge reports
    NaN after a while" bug.
65. `MeterRegistry` as the interface; `SimpleMeterRegistry`, `CompositeMeterRegistry`,
    `PrometheusMeterRegistry`, `OtlpMeterRegistry`, `CloudWatchMeterRegistry`.
66. Micrometer naming convention: dot-separated lowercase (`http.server.requests`), and the
    registry's **naming convention** translates to each backend's charset
    (`http_server_requests_seconds_count` for Prometheus).
67. Base units: Micrometer records durations in the registry's base unit and appends a unit
    suffix; Prometheus base unit is **seconds**, not milliseconds.
68. `Tags` / `Tag` / `KeyValues`, and `MeterRegistry.config().commonTags(...)` for
    `application`, `region`, `env`, `version`.
69. **`MeterFilter`**: `deny`, `denyNameStartsWith`, `accept`, `rename`, `ignoreTags`,
    `replaceTagValues`, `maximumAllowableMetrics`, `maximumAllowableTags`,
    `map(id -> ...)`, `commonTags`, `distributionStatisticConfig`. `[RESEARCH]`
70. `MeterFilter.maximumAllowableTags` as the **cardinality circuit breaker** you install before
    you need it.
71. Micrometer distribution config: `publishPercentiles`, `publishPercentileHistogram`,
    `serviceLevelObjectives`, `minimumExpectedValue`, `maximumExpectedValue`,
    `percentilePrecision`, `expiry`, `bufferLength`. `[RESEARCH]`
72. Prometheus exposition format: `# HELP`, `# TYPE`, sample lines, label syntax, `le` and
    `quantile` reserved labels, the `+Inf` bucket, `_total`/`_sum`/`_count`/`_bucket` suffixes.
73. Metric types in the Prometheus data model: `counter`, `gauge`, `histogram`, `summary`,
    `untyped`/`unknown`, and OpenMetrics' `info`, `stateset`, `gaugehistogram`.
74. `Content-Type` negotiation between text exposition, OpenMetrics, and protobuf (**protobuf is
    required for native histograms; the text format was never extended and there is no plan to
    extend it**). `[SOURCE]` `[RESEARCH]`
75. **[VERSION-TRAP]** Prometheus 3.x accepts all UTF-8 in metric and label names by default; the
    `[a-zA-Z_:][a-zA-Z0-9_:]*` rule and the "no dots in metric names" claim are 2.x. `[RESEARCH]`
76. The `up` metric, `scrape_duration_seconds`, `scrape_samples_scraped`,
    `scrape_samples_post_metric_relabeling`, `scrape_series_added` — the per-target
    meta-metrics Prometheus synthesises.
77. `/actuator/prometheus` (needs `micrometer-registry-prometheus`) and `/actuator/metrics/{name}`
    with `?tag=` drill-down.

## 1E. Tracing — the model and the vocabulary

78. **Trace** = one request's journey; **span** = one unit of work, with name, start time,
    duration, parent span ID, trace ID, attributes, events, links, status.
79. What tracing gives you that logs and metrics cannot: the **causal structure**. Each service's
    own p99 can look fine while only the composition is slow.
80. Traces reveal **cross-service N+1** patterns that are invisible in any single service.
81. **Span kinds**: `SERVER`, `CLIENT`, `PRODUCER`, `CONSUMER`, `INTERNAL` — and why the kind
    changes how a backend computes service-level metrics from spans.
82. **Span status**: `UNSET`, `OK`, `ERROR`, plus `error.type` and recorded exceptions.
83. **Span events** (timestamped annotations inside a span; `recordException` is one) vs
    **span attributes** vs **span links**.
84. **Span links** — the mechanism for fan-in/batch: a consumer span processing 500 Kafka records
    links to 500 producer contexts rather than pretending to have one parent. `[X-REF 14]`
85. **Resource** — the immutable attributes of the emitting entity: `service.name`,
    `service.version`, `service.namespace`, `service.instance.id`,
    `deployment.environment.name`, `host.name`, `k8s.pod.name`, `cloud.region`.
86. `OTEL_SERVICE_NAME` default is **`unknown_service:java`** — the value that shows up when you
    forget. `[SOURCE]` `[RESEARCH]`
87. **Instrumentation scope** (name + version + schema URL) — how a backend attributes a span to
    the library that produced it.
88. **Baggage** — key/value context propagated to *all* downstream services, distinct from span
    attributes (which are local). Use cases: tenant ID, experiment arm, request priority.
89. **[TRAP]** Baggage is on the wire on every hop: putting anything large or secret in it is a
    performance and security bug. Also, W3C `baggage` has its own size limits.
90. **W3C `traceparent`** exact format: `version-trace-id-parent-id-trace-flags`, e.g.
    `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`. `[SOURCE]` `[RESEARCH]`
91. Field sizes: version 2 hex digits (`ff` invalid), trace-id **32 lowercase hex** (16 bytes,
    all-zero forbidden), parent-id **16 lowercase hex** (8 bytes, all-zero invalid), trace-flags
    2 hex (8-bit field). `[SOURCE]` `[RESEARCH]`
92. Only the **least significant bit** of trace-flags is defined: `sampled`. Reserved flags must
    be zero. Wording matters: sampled means the caller **may have** recorded. `[SOURCE]`
93. **`tracestate`** — comma-separated `key=value` list members; simple keys and
    `tenant-id@system-id` multi-tenant keys; keys ≤ 256 chars beginning with a lowercase letter
    or digit; values printable ASCII 0x20–0x7E excluding `,` and `=`, ≤ 256 chars. `[SOURCE]`
94. `tracestate` limits and mutation rules: **max 32 list members**, propagate ≥ 512 chars, on
    truncation drop members > 128 chars first then from the end; modified/new keys move to the
    **left**; delete only your own keys; preserve order otherwise. `[SOURCE]` `[RESEARCH]`
95. Other propagation formats you will meet: B3 single (`b3`) and multi
    (`X-B3-TraceId`/`SpanId`/`ParentSpanId`/`Sampled`), Jaeger `uber-trace-id`,
    AWS `X-Amzn-Trace-Id`, `ot-tracer-*`. Configured via `OTEL_PROPAGATORS`.
96. `OTEL_PROPAGATORS` default is **`tracecontext,baggage`**; valid values `tracecontext`,
    `baggage`, `b3`, `b3multi`, `jaeger`, `ottrace`, `xray`, `xray-lambda`. `[SOURCE]` `[RESEARCH]`
97. Propagation across message brokers goes in **message headers**, and it is the same problem as
    the correlation ID with the same solution. `[X-REF 14]`
98. Sampling, first pass: **head-based** decides at the root and propagates; **tail-based**
    buffers the whole trace and decides after seeing it.
99. **Consistent sampling across services is mandatory** — inconsistent decisions produce broken
    partial traces.
100. **OpenTelemetry** as the vendor-neutral standard: API / SDK / Collector / semantic
     conventions / OTLP, and the CNCF-project framing.
101. The **API vs SDK** split and why it exists: libraries depend on the API only, so an
     application that never installs an SDK pays (nearly) nothing and has no vendor coupling.
102. **OTLP** — the wire protocol: gRPC on **4317**, HTTP/protobuf on **4318**, paths
     `/v1/traces`, `/v1/metrics`, `/v1/logs`.
103. **[VERSION-TRAP]** SDK autoconfigure defaults `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`, but the
     **Java agent 2.0+ defaults to `http/protobuf`**. `[SOURCE]` `[RESEARCH]`
104. OTel Java agent basics: `-javaagent:opentelemetry-javaagent.jar`, what it auto-instruments
     (Spring MVC/WebFlux, JDBC, HTTP clients, Kafka, JMS, Redis, gRPC, Logback/Log4j2), and the
     "agent plus a handful of manual business spans" pragmatic path.
105. Agent-only config: `otel.javaagent.configuration-file`, `otel.javaagent.extensions`,
     `otel.javaagent.logging` (`simple`/`none`/`application`), `otel.javaagent.enabled`,
     `otel.javaagent.exclude-classes`. `[SOURCE]` `[RESEARCH]`
106. Cloud resource providers are **disabled by default** on the agent:
     `otel.resource.providers.aws.enabled`, `.gcp.enabled`, `.azure.enabled`. `[SOURCE]` `[RESEARCH]`

## 1F. Health, probes, and lifecycle

107. **Shallow / liveness** — "is this process alive and able to respond?" Cheap, dependency-free.
108. **Deep / readiness** — "can this instance actually serve?" Includes **hard** dependencies only.
109. **Startup probe** — the correct tool for slow JVM warm-up, instead of a long
     `initialDelaySeconds`. `[X-REF 19]`
110. **[TRAP]** Deep checks must never drive restarts: a 30-second DB blip fails every pod's
     liveness probe at once, Kubernetes restarts the whole fleet, and the restarts make recovery
     harder (cold caches, connection storms, no capacity). Restarting your pod does not fix
     someone else's database. `[X-REF 19]`
111. The symmetric readiness caveat: if a **soft** dependency (a cache) takes every pod
     not-ready, the Service has zero endpoints and you are fully down when you could have served
     degraded.
112. Spring Boot health surface: `HealthIndicator`, `ReactiveHealthIndicator`,
     `HealthContributor`, `CompositeHealthContributor`, `AbstractHealthIndicator`, and the
     `Status` values `UP`, `DOWN`, `OUT_OF_SERVICE`, `UNKNOWN`.
113. `management.endpoint.health.show-details` (`never`/`when-authorized`/`always`),
     `show-components`, `roles`. `[SOURCE]` `[RESEARCH]`
114. **Health groups**: `management.endpoint.health.group.<name>.include/exclude`,
     `.show-details`, `.status.http-mapping`, and
     `management.endpoint.health.group.liveness.additional-path=server:/livez`. `[RESEARCH]`
115. `management.endpoint.health.probes.enabled=true` produces `/actuator/health/liveness` and
     `/actuator/health/readiness`; readiness automatically reports `OUT_OF_SERVICE` during
     graceful shutdown. `[X-REF 19]`
116. `ApplicationAvailability`, `LivenessState`, `ReadinessState`, and
     `AvailabilityChangeEvent.publish(...)` as the programmatic way to fail readiness.
117. **[TRAP]** Health endpoints in access logs and latency metrics: a probe every 5 s from
     several sources dominates the data and flatters your percentiles. Exclude them.
118. **[TRAP]** A probe endpoint that requires auth — the kubelet is unauthenticated. `[X-REF 19]`
119. `/actuator/info` with build version, git SHA, build time (`spring-boot-maven-plugin`
     `build-info`, `git-commit-id-plugin`). "Which version is on that pod?" is an incident question.

## 1G. The Actuator endpoint surface, exhaustively

120. Default base path `/actuator`, the discovery page, and `management.endpoints.web.base-path`.
121. Only **`health`** is exposed over HTTP and JMX by default. `[SOURCE]` `[RESEARCH]`
122. Technology-agnostic endpoints: `auditevents`, `beans`, `caches`, `conditions`, `configprops`,
     `env`, `flyway`, `health`, `httpexchanges`, `info`, `integrationgraph`, `liquibase`,
     `loggers`, `mappings`, `metrics`, `quartz`, `scheduledtasks`, `sessions`, `shutdown`,
     `startup`, `threaddump`. `[SOURCE]` `[RESEARCH]`
123. Web-only endpoints: `heapdump` (HPROF on HotSpot, PHD on OpenJ9), `logfile` (supports the
     HTTP `Range` header), `prometheus`. `[SOURCE]` `[RESEARCH]`
124. Exposure control: `management.endpoints.web.exposure.include/exclude`,
     `management.endpoints.jmx.exposure.include/exclude`, and the `*` wildcard.
125. **[VERSION-TRAP]** Access control in current Boot: `management.endpoints.access.default`
     (`none`), `management.endpoint.<id>.access` (`none`/`read-only`/`unrestricted`),
     `management.endpoints.access.max-permitted`. `[SOURCE]` `[RESEARCH]`
126. `shutdown` is disabled by default and jar-only; `management.endpoint.shutdown.access=unrestricted`
     to enable. `[RESEARCH]`
127. Endpoint response **caching**: `management.endpoint.<name>.cache.time-to-live` for read
     operations. `[RESEARCH]`
128. Sanitisation of `env`, `configprops`, `quartz` by default, and `SanitizingFunction` to extend it.
129. CSRF applies to actuator POST/PUT/DELETE by default — the reason your `/actuator/loggers`
     curl 403s. `[RESEARCH]` `[X-REF 13]`
130. `management.server.port` / `management.server.address` — separate management port, and why
     that is the standard hardening move. `[X-REF 13]`
131. **[TRAP]** `/actuator/env`, `/actuator/configprops`, `/actuator/heapdump`,
     `/actuator/threaddump` are an exfiltration surface: heapdump contains credentials, tokens,
     and customer data in plaintext. Restrict or disable. `[X-REF 13]`
132. Securing actuator with `EndpointRequest.toAnyEndpoint()` and a role. `[SOURCE]`
133. Custom endpoints: `@Endpoint`, `@ReadOperation`, `@WriteOperation`, `@DeleteOperation`,
     `@WebEndpoint`, `@JmxEndpoint`, `@Selector`.

## 1H. SLI / SLO / SLA and the error budget

134. **SLI** — the measurement: "proportion of requests served successfully in under 300 ms."
135. **SLO** — the internal target: "99.9% of requests over a rolling 30 days."
136. **SLA** — the contractual promise with financial consequences, always **looser** than the SLO.
137. The **error budget** = `1 − SLO`, expressed as allowed bad events or allowed minutes.
138. Availability table to memorise: 99% = 7.2 h/30 d, 3.65 d/yr; 99.9% = 43 min/30 d, 8.76 h/yr;
     99.95% = 21.6 min/30 d, 4.38 h/yr; 99.99% = 4.3 min/30 d, 52.6 min/yr; 99.999% = 26 s/30 d.
     `[PROVE]` — derive one of them.
139. **The error budget is a resource you are meant to spend**, not waste to be minimised.
140. The policy that makes it real: budget remaining → ship, take risks, run migrations; budget
     exhausted → feature freeze, reliability work until it recovers.
141. **100% is the wrong target**: unachievable (your dependencies are not 100%), each nine costs
     roughly an order of magnitude more, and it means you are shipping too slowly. `[PROVE]`
142. **Measure the SLI from the user's vantage point** — LB > app; synthetic or RUM better still.
     An SLO measured inside the service reports 99.99% while the ingress returns 502s.
143. 99.99% means detecting *and* recovering in under 4 minutes a month, which is a statement
     about **automation**, not effort. `[PROVE]`
144. SLI types: availability, latency, throughput, correctness/quality, freshness, coverage,
     durability.
145. **Request-based vs windows-based SLIs** — count good events / total events, vs count good
     minutes / total minutes; when each is the right choice and how they disagree.
146. Rolling window vs calendar window SLOs, and the "budget resets on the 1st" failure mode.
147. **Aspirational vs achievable SLO**, and the discipline of setting the SLO from measured past
     performance, then negotiating.
148. **[TRAP]** An SLO nobody has authority to act on is a dashboard, not an SLO. The error-budget
     *policy* — agreed with product, in writing — is the artefact.

## 1I. The golden signals, RED, USE

149. **RED** for request-driven services: **Rate**, **Errors**, **Duration**.
150. **USE** for resources: **Utilisation**, **Saturation**, **Errors** — Brendan Gregg's method.
151. Google's **four golden signals**: latency, traffic, errors, **saturation**.
152. How the three overlap and where they differ: golden signals = RED + saturation; USE is
     resource-major, RED is request-major.
153. Latency must be split **success vs error** — fast 500s flatter your latency SLI.
154. The standard instrumentation set: RED per endpoint, RED per downstream dependency, and
     saturation of **every pool you own** (thread pool, connection pool, queue depth, consumer lag).
155. **Business metrics**: orders/min, payments succeeded, signups. A deploy that breaks the
     checkout button shows perfect CPU, latency, and error rate while orders drop to zero.
156. **Four golden signals for a queue/stream** instead of a request: arrival rate, lag,
     processing duration, DLQ rate. `[X-REF 14]`

---

# PART 2 — INTERMEDIATE: cost models, the which-one-and-why decisions, the utility surface

## 2A. Percentiles and the statistics of latency

1. Why **averages lie**: 10,000 requests, 9,900 at 10 ms and 100 at 5,000 ms → mean 59 ms, which
   looks fine while 100 users waited five seconds. `[PROVE]`
2. Track **p50 / p90 / p95 / p99 / p99.9**, and read the **p50→p99 gap** as its own signal:
   widening means queueing, GC pauses, lock contention, or one bad instance — often before the
   average moves.
3. **You cannot average percentiles.** The mean of each pod's p99 is not the fleet p99. `[PROVE]`
4. The correct procedure: aggregate the underlying **bucket counts**, then compute the quantile —
   which is exactly why `histogram_quantile()` operates on `_bucket` sums.
5. **Percentiles compose badly across fan-out**: 5 independent calls each 1% likely to be slow
   ⇒ ~5% chance at least one is slow. `1 − 0.99^5 = 4.9%`. `[PROVE]`
6. Therefore **your p99 is your dependencies' p99.9** — tail latency amplifies with fan-out.
   Dean & Barroso, "The Tail at Scale."
7. **Coordinated omission**: a load generator that waits for a slow response stops issuing
   requests, so the slow period is under-sampled and the measured percentile is optimistic.
8. Why coordinated omission also affects **in-process** timers: a request blocked on a saturated
   pool is often not being timed at all yet.
9. Micrometer's **pause detection** (LatencyUtils) as the in-JVM mitigation, and the optional
   dependency it requires. `[RESEARCH]`
10. **HdrHistogram** and the significant-figures idea; why `percentilePrecision` trades memory for
    accuracy.
11. **Sliding-window vs cumulative** distribution statistics: Micrometer's `expiry` and
    `bufferLength`, and why a cumulative Prometheus histogram means "since process start."
12. **Trimmed mean / median absolute deviation** as alternatives, and why the industry still uses
    percentiles anyway.
13. **[TRAP]** Reporting p99 over a 24-hour window. A percentile over a long window hides a
    10-minute total outage. Percentiles need a stated window.
14. **[TRAP]** Comparing p99 across services with different traffic volumes as if it were the same
    statistic.
15. **Little's Law**: `L = λ · W` — concurrency = arrival rate × latency. Use it to size pools and
    to sanity-check metrics. `[PROVE]`
16. Little's Law applied backwards: if you observe `L` in-flight and `λ` arrivals/s, then
    `W = L/λ` gives you latency without a timer — a cross-check on your instrumentation.
17. **Utilisation law and the queueing knee**: `W = S / (1 − ρ)` for M/M/1; at 80% utilisation
    latency is 5× service time, at 90% it is 10×. `[PROVE]` Why "CPU is only at 85%" is not
    reassurance.
18. **Universal Scalability Law**, briefly: contention and coherency terms, and why throughput can
    *decrease* with more nodes.
19. **Apdex** as a threshold-based alternative to percentiles, and `histogram_fraction`-based
    Apdex on native histograms. `[SOURCE]` `[RESEARCH]`

## 2B. Metrics cost, cardinality, and the economics

20. **The cardinality trap**, stated as arithmetic: series count = ∏ (distinct values per label).
    Six labels with 10 values each = 1,000,000 series.
21. `meterRegistry.counter("orders.placed", "userId", userId)` — one series per user, forever.
    Catastrophic.
22. The full list of things that must never be a label: `userId`, `orderId`, `requestId`,
    `traceId`, email, raw URL path with IDs, raw exception message, timestamps, session IDs,
    full SQL text, IP address, user agent.
23. What Prometheus does when you do it: active series are held in memory in the head block, RAM
    climbs, ingestion slows, and **the monitoring dies exactly when you need it**.
24. What CloudWatch does: bills **per metric** per DimensionSet, producing a five-figure invoice
    from one line of code. Datadog: per custom metric. `[RESEARCH]`
25. Rules for labels: **bounded and low-cardinality** — templated endpoint (`/orders/{id}`, never
    `/orders/12345`), method, status class, service, region, version, tenant *class*.
26. The pre-commit question: "how many distinct values can this have, ever?" If not a small
     number you can name, it does not go in a label.
27. High-cardinality identifiers belong in **logs, traces, and exemplars** — built for it.
28. `http.route` / `uri` templating: how Spring's `WebMvcTags`/`ServerRequestObservationConvention`
    produces `/orders/{id}`, and the `UNKNOWN` bucket for unmatched paths.
29. **[TRAP]** A 404-scanning bot creating one series per bogus path, because your instrumentation
    used the raw path for unmatched requests.
30. Cardinality budget as a real budget: a per-service series cap, `maximumAllowableMetrics` /
    `maximumAllowableTags`, and an alert on `prometheus_tsdb_head_series`.
31. Finding the offender: `topk(10, count by (__name__)({__name__=~".+"}))`,
    `count by (job) ({__name__=~".+"})`, `prometheus_tsdb_symbol_table_size_bytes`, and the TSDB
    status page's top-cardinality report.
32. **Retention tiers** as a cost lever: raw 15 s for 15 days, 5 m downsampled for 90 days, 1 h for
    a year. Thanos/Mimir/Cortex downsampling.
33. Log cost levers: sampling, dropping DEBUG at the agent, dropping high-volume fields,
    index-vs-store split (Loki indexes labels only), S3/object-store tiers, retention by log class.
34. Trace cost levers: head sampling rate, tail sampling policies, span attribute limits, dropping
    internal spans, span-to-metrics conversion so you can sample aggressively.
35. **The cost paradox**: the cheapest way to cut observability spend is usually to *stop emitting
    something nobody queries*, and nobody knows what nobody queries. Query-usage telemetry as the
    answer.
36. **[TRAP]** Sampling metrics. Metrics are already aggregates; sampling them breaks counts and
    rates. Sample traces and logs, never counters.

## 2C. Histograms: classic, native, and the choice

37. Classic histogram on the wire: `_bucket{le="0.1"}`, cumulative counts, `+Inf` bucket equals
    `_count`, plus `_sum`. `[SOURCE]`
38. `histogram_quantile()` does **linear interpolation inside the chosen bucket** — so the error is
    bounded by bucket width, not by φ. `[PROVE]`
39. The worked error comparison: true spike at 220 ms → native histogram estimates p95 ≈ 228 ms
    (~8 ms error), classic histogram with a 200–300 ms bucket estimates 295 ms (~75 ms error).
    `[SOURCE]` `[RESEARCH]`
40. Therefore: **pick buckets around your SLO threshold**, because that is the only place the
    number must be accurate.
41. Summary error is in the **φ dimension** (0.95 ± 0.01 = somewhere between p94 and p96);
    histogram error is in the **value** dimension. Different failure shapes.
42. **Summaries cannot be aggregated** — "averaging the quantiles yields statistically nonsensical
    values." `[SOURCE]`
43. Instrumentation cost: summary = expensive streaming quantile computation; classic and native
    histogram = a bucket increment.
44. Series count: summary = `_sum`, `_count`, one per quantile; classic = `_sum`, `_count`, one per
    bucket; **native = a single composite sample**. `[SOURCE]`
45. **Native (exponential) histograms**: schema −4…+8 for standard exponential schemas, −53
    reserved for custom bucket boundaries. Schema *n* has **half the resolution of** *n*+1.
    `[SOURCE]` `[RESEARCH]`
46. Bucket boundary formula: upper inclusive limit of positive bucket *i* is `(2^(2^-n))^i`;
    negative buckets mirror it. `[SOURCE]` `[PROVE]` — show that schema 0 gives factor-of-2
    buckets and schema 3 gives ~9% buckets.
47. **Zero bucket** and its threshold: observations in the closed interval `[-t, +t]` go to the
    zero bucket; **default threshold is zero**, capturing exact zeros only. `[SOURCE]` `[RESEARCH]`
48. **NHCB** (native histograms with custom bucket boundaries, schema **−53**): lets a classic
    histogram be stored as a native one. Histograms with different custom boundaries are
    **generally not mergeable**. `[SOURCE]` `[RESEARCH]`
49. **Counter reset hints** as histogram flags: `GaugeType`, `CounterReset`, `NotCounterReset`,
    `UnknownCounterReset`. `[SOURCE]` `[RESEARCH]`
50. **Exposition**: native histograms require **protobuf**; the text format was not extended and
    will not be. `[SOURCE]` `[RESEARCH]`
51. **[VERSION-TRAP]** Stable in Prometheus **3.8**; scraping needs `scrape_native_histograms: true`
    from 3.8; remote write needs `send_native_histograms`; **both default to `true` from v4**.
    `[SOURCE]` `[RESEARCH]`
52. OTel's equivalent: `base2_exponential_bucket_histogram` aggregation, `max_scale`, `max_size`,
    and `OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`
    (`EXPLICIT_BUCKET_HISTOGRAM` default, or `BASE2_EXPONENTIAL_BUCKET_HISTOGRAM`).
    `[SOURCE]` `[RESEARCH]`
53. Micrometer's `publishPercentileHistogram()` generates **276 buckets by default**, clamped to
    **~73 per dimension** by `minimumExpectedValue`/`maximumExpectedValue`. `[SOURCE]` `[RESEARCH]`
54. Only **Prometheus, Atlas, and Wavefront** support histogram-based percentile approximation in
    Micrometer; on others, `serviceLevelObjectives` is the histogram you get. `[SOURCE]` `[RESEARCH]`
55. `serviceLevelObjectives(Duration.ofMillis(300))` producing an `le="0.3"` bucket — the SLO
    bucket you actually alert on.
56. **Aggregation temporality**: **cumulative** vs **delta**, `LOWMEMORY` preference, and which
    backends want which (Prometheus: cumulative; CloudWatch/Datadog: delta).
57. Prometheus 3.x OTLP receiver has **primitive support for ingesting OTLP delta metrics as-is**.
    `[RESEARCH]`
58. **Exemplars**: a sample value plus a trace ID attached to a bucket, giving one-click
    metric→trace. `OTEL_METRICS_EXEMPLAR_FILTER` = `TRACE_BASED` (default), `ALWAYS_ON`,
    `ALWAYS_OFF`. Exemplar filter stabilised in OTel Java **1.56.0**. `[SOURCE]` `[RESEARCH]`
59. Exemplar exposition syntax in OpenMetrics (`# {trace_id="..."} 0.67 1520879607.789`) and the
    storage/query support required.

## 2D. PromQL, exhaustively enough to alert with

60. Data types: instant vector, range vector, scalar, string.
61. Selectors: `=`, `!=`, `=~`, `!~`; the `__name__` label; UTF-8 quoting `{"my.metric", job="x"}`.
62. Range selectors `[5m]`, offset modifier `offset 1h`, `@` modifier with `start()`/`end()`.
63. **[VERSION-TRAP]** Prometheus 3.x range selectors and lookback delta are **left-open**:
    `[5m]` at `t` covers `(t-5m, t]`. `[RESEARCH]`
64. `rate()` — per-second average rate over the range, **extrapolated**, counter-reset aware.
    Best for alerts and slow counters. `[SOURCE]`
65. `irate()` — instant rate from the **last two** samples; volatile; fast-moving counters only.
    `[SOURCE]`
66. `increase()` — total increase over the range, reset-aware; equals `rate() × range`. `[SOURCE]`
67. `delta()` / `idelta()` for gauges, and why using them on counters is wrong. `[SOURCE]`
68. `resets()` (counts counter resets by detecting decreases) and `changes()`. `[SOURCE]` `[RESEARCH]`
69. **`rate()` extrapolation artefacts**: fractional results on integer counters, and why
    `increase()` over a short range can report 1.6 events.
70. **`rate()` needs at least two samples in the window** — hence the "range at least 4× the scrape
    interval" rule of thumb.
71. `histogram_quantile(φ, sum by (le, job) (rate(x_bucket[5m])))` — the canonical form, and why
    `le` must survive the aggregation. `[SOURCE]`
72. Native-histogram functions: `histogram_count`, `histogram_sum`, `histogram_avg`,
    `histogram_fraction(lower, upper, v)`, `histogram_stddev`, `histogram_stdvar`, and
    experimental `histogram_quantiles`. `[SOURCE]` `[RESEARCH]`
73. Aggregation operators: `sum`, `min`, `max`, `avg`, `group`, `stddev`, `stdvar`, `count`,
    `count_values`, `bottomk`, `topk`, `quantile`, `limitk`, `limit_ratio`; the `by`/`without`
    modifiers.
74. `_over_time` family: `avg_over_time`, `min_over_time`, `max_over_time`, `sum_over_time`,
    `count_over_time`, `quantile_over_time`, `stddev_over_time`, `last_over_time`,
    `present_over_time`, `mad_over_time`, `ts_of_max_over_time`.
75. `absent()` / `absent_over_time()` — the functions that let you alert on **missing data**.
    `[SOURCE]`
76. `predict_linear()` for "disk full in 4 hours" alerts; the correct form
    `predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0`.
77. `double_exponential_smoothing()` (formerly `holt_winters`) — **experimental**, needs
    `--enable-feature=promql-experimental-functions`. `[SOURCE]` `[RESEARCH]`
78. `label_replace()` / `label_join()` for reshaping, and `sort_by_label()` /
    `sort_by_label_desc()` — **experimental**. `[SOURCE]` `[RESEARCH]`
79. `info()` — **experimental** enrichment from info metrics; `clamp`/`clamp_min`/`clamp_max`;
    `min_of`/`max_of`, `start()`/`end()`/`range()`/`step()` — experimental. `[SOURCE]` `[RESEARCH]`
80. Vector matching: `on`/`ignoring`, `group_left`/`group_right`, and the "many-to-many matching
    not allowed" error.
81. The error-ratio idiom:
    `sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))`
    and the `or vector(0)` trick for when the numerator has no series.
82. **[TRAP]** Dividing by a numerator-only series set and getting *no result* instead of zero,
    so the alert silently never fires.
83. `and`/`or`/`unless` set operators, and using `unless` to suppress an alert during a
    maintenance window.
84. **Recording rules**: `groups[].name`, `interval`, `limit`, `query_offset`, `labels`;
    `record`/`expr`/`labels`. Naming convention **`level:metric:operations`**, e.g.
    `code:prometheus_http_requests_total:sum`. `[SOURCE]` `[RESEARCH]`
85. **Alerting rules**: `alert`, `expr`, `for`, `keep_firing_for`, `labels`, `annotations`, Go
    templating with `{{ $value }}` / `{{ $labels.job }}`. `[SOURCE]` `[RESEARCH]`
86. Alert states `inactive` → `pending` → `firing`, and the synthetic **`ALERTS`** and
    `ALERTS_FOR_STATE` metrics. `[RESEARCH]`
87. `rule_group_iterations_missed_total` and the "evaluation took longer than the interval, so a
    cycle was skipped and there is a gap" failure. `promtool check rules`. `[SOURCE]` `[RESEARCH]`
88. `query_offset` / `--rules.alert.for-grace-period` and the "rule evaluated before the scrape
    landed" race. `[RESEARCH]`
89. `promtool` surface: `check config`, `check rules`, `check metrics`, `test rules`
    (**unit tests for alerts** — the part nobody uses and should), `query instant`, `tsdb analyze`.

## 2E. Prometheus operationally

90. Pull vs push, and the honest trade-off table: service discovery, target health for free,
    firewall direction, short-lived jobs.
91. **Pushgateway** — for batch jobs only, its "metrics never disappear" semantics, and why it is
    not a general push endpoint.
92. `scrape_config`: `job_name`, `scrape_interval`, `scrape_timeout`, `metrics_path`, `scheme`,
    `honor_labels`, `honor_timestamps`, `sample_limit`, `label_limit`,
    `target_limit`, `scrape_native_histograms`.
93. Service discovery: `static_configs`, `kubernetes_sd_configs` (roles `node`, `pod`, `service`,
    `endpoints`, `endpointslice`, `ingress`), `ec2_sd_configs`, `file_sd_configs`, `dns_sd_configs`,
    and (3.14) `oci_sd_configs`. `[RESEARCH]`
94. `relabel_configs` vs `metric_relabel_configs`: the first shapes **targets** before scraping,
    the second shapes **samples** after. Actions: `replace`, `keep`, `drop`, `labelmap`,
    `labeldrop`, `labelkeep`, `hashmod`, `keepequal`, `dropequal`, `lowercase`, `uppercase`.
95. `metric_relabel_configs` with `action: drop` as the **emergency cardinality brake** you can
    apply without touching the application.
96. `hashmod` + `keep` as the standard **scrape-sharding** pattern across Prometheus replicas.
97. `external_labels` and why they must be unique per Prometheus for remote-write/Thanos dedup.
98. **Staleness**: when a series disappears from a scrape, Prometheus writes a **stale marker**, and
    queries return no value rather than the last value. The 5-minute lookback delta and what
    changes with left-open ranges. `[RESEARCH]`
99. **[TRAP]** A gauge that stops being exported does not go to zero — it goes *absent*, and your
    `> threshold` alert stops firing rather than firing. This is the "alert stopped working
    because the thing broke" class of bug.
100. Out-of-order ingestion (`out_of_order_time_window`) and why it exists for agent/edge
     buffering. `[RESEARCH]`
101. **Remote write 1.0 vs 2.0**: `prometheus.WriteRequest` vs `io.prometheus.write.v2.Request`
     with a **symbols table / string interning** (labels referenced by index). `[SOURCE]` `[RESEARCH]`
102. RW2.0 headers: `Content-Type: application/x-protobuf;proto=io.prometheus.write.v2.Request`,
     `X-Prometheus-Remote-Write-Version: 2.0.0` (or `0.1.0` for 1.x compatibility), and mandatory
     `X-Prometheus-Remote-Write-{Samples,Histograms,Exemplars}-Written` response headers.
     `[SOURCE]` `[RESEARCH]`
103. RW2.0 semantics: created timestamps for counters/cumulative histograms, native histograms,
     exemplars with optional `trace_id`, metadata (type/help/unit); **partial writes return 5xx**
     so the sender retries the whole request; 4xx = permanent, 429 optional. `[SOURCE]` `[RESEARCH]`
104. Remote **read** and why it is much less used; `remote_read` vs a federation hierarchy.
105. Federation (`/federate`) and `honor_labels`, and its limits (why Thanos/Mimir exist).
106. **Snappy** compression on the wire; WAL-based remote write queue
     (`queue_config`: `capacity`, `max_shards`, `min_shards`, `max_samples_per_send`,
     `batch_send_deadline`, `min_backoff`, `max_backoff`, `retry_on_http_429`).
107. Long-term storage options compared: Thanos, Cortex, **Mimir**, VictoriaMetrics, managed AMP —
     on the axes of dedup, downsampling, multi-tenancy, and query federation.
108. Alertmanager: `route` tree, `group_by`, `group_wait`, `group_interval`, `repeat_interval`,
     `inhibit_rules`, `silences`, `receivers`, `matchers`, and high availability via gossip.
109. `group_by: [alertname, cluster]` and the "1,000 pods down = one notification" property that
     makes paging survivable.
110. `inhibit_rules` so a cluster-down alert suppresses the 200 service-down alerts under it.
111. **[TRAP]** `repeat_interval: 5m` on a page — you have built your own alert-fatigue machine.
112. Prometheus HA in practice: two identical replicas, dedup at the query layer
     (Thanos Querier / Mimir), and **why Prometheus itself is not clustered**.
113. Sizing arithmetic: ~1–2 bytes per sample after compression; series × samples/s × bytes → disk
     and RAM. `[PROVE]` — work one example end to end.
114. `--storage.tsdb.retention.time` / `.size`, block compaction, and the head block.

## 2F. Tracing decisions

115. **Auto-instrumentation vs manual**: coverage and zero code change vs semantic meaning and
     business attributes. The correct answer is both.
116. What the OTel Java agent cannot know: your business identifiers, your domain operation names,
     your notion of "one unit of work."
117. Manual spans: `Tracer.spanBuilder(...)`, `setSpanKind`, `setParent`, `setAttribute`,
     `addLink`, `startSpan`, `makeCurrent()` (a `Scope`, must be closed), `end()`.
118. **[TRAP]** Forgetting `scope.close()` / not using try-with-resources leaks the current
     context into the next task on that pooled thread — the tracing equivalent of the MDC leak.
119. `@WithSpan` / `@SpanAttribute` (agent) vs `@Observed` / `@NewSpan` (Micrometer) — three
     annotation vocabularies for the same idea, and which requires which dependency.
120. **Micrometer Observation API** as the "instrument once, emit metrics + traces + logs" layer:
     `Observation`, `ObservationRegistry`, `ObservationHandler`, `ObservationConvention`,
     `Observation.Context`. `[RESEARCH]`
121. `lowCardinalityKeyValue` → **metrics and traces**; `highCardinalityKeyValue` → **traces only**.
     This single API distinction encodes the entire cardinality lesson. `[SOURCE]` `[RESEARCH]`
122. `ObservationPredicate` (all must return true), `GlobalObservationConvention`,
     `ObservationFilter`, `ObservationHandler`, `ObservationRegistryCustomizer` — auto-registered
     bean types in Spring Boot. `[SOURCE]` `[RESEARCH]`
123. `management.observations.enable.<prefix>=false` and
     `management.observations.key-values.<k>=<v>` (common low-cardinality tags). `[SOURCE]` `[RESEARCH]`
124. `management.observations.annotations.enabled=true` + `aspectjweaver` for `@Observed`,
     `@Timed`, `@Counted`, `@MeterTag`, `@NewSpan`. `[SOURCE]` `[RESEARCH]`
125. **[TRAP]** Annotating an already-instrumented method (a Spring Data repository) produces
     **duplicate observations**; disable one side. `[SOURCE]` `[RESEARCH]`
126. Micrometer Tracing bridges: `micrometer-tracing-bridge-brave` vs
     `micrometer-tracing-bridge-otel`, and why you pick exactly one. `[RESEARCH]`
127. `management.tracing.sampling.probability` (default **1.0**),
     `management.tracing.propagation.type` (`w3c` default, `b3`, `jaeger`, ...),
     `management.tracing.enabled`. `[SOURCE]` `[RESEARCH]`
128. `management.opentelemetry.resource-attributes.*`, `management.opentelemetry.enabled`, and
     `management.opentelemetry.map-environment-variables` (Boot maps a subset of `OTEL_*` env
     vars onto Spring properties). `[SOURCE]` `[RESEARCH]`
129. Spring Boot metric/observation names to know: `http.server.requests`, `http.client.requests`,
     `spring.data.repository.invocations`, `jvm.memory.used`, `jvm.gc.pause`,
     `jvm.threads.states`, `process.cpu.usage`, `hikaricp.connections.*`,
     `spring.kafka.listener`, `tasks.scheduled.execution`, `resilience4j.*`. `[RESEARCH]`
130. JDBC observability needs **datasource-micrometer**; R2DBC needs `io.r2dbc:r2dbc-proxy`.
     `[SOURCE]` `[RESEARCH]`
131. Context propagation config in Spring: `spring.reactor.context-propagation=auto`,
     `spring.task.execution.propagate-context=true`, or a `ContextPropagatingTaskDecorator` bean.
     `[SOURCE]` `[RESEARCH]`
132. `io.micrometer:context-propagation` library: `ThreadLocalAccessor`, `ContextSnapshot`,
     `ContextSnapshotFactory` — the mechanism underneath all of the above.
133. Sampling strategies compared: always-on, always-off, probabilistic head, rate-limiting,
     adaptive/remote (`jaeger_remote`), tail-based, and **span-to-metrics + aggressive sampling**.
134. Head sampling economics: 1% keeps cost linear and predictable but **misses the rare slow
     request you actually care about**.
135. Tail sampling economics: full-fidelity selection but the collector must **buffer every trace**
     for `decision_wait`, so memory ∝ trace rate × trace size × wait.
136. **Consistent probability sampling** and the `p`/`r` (`ot`) tracestate values: how a
     downstream can up-sample and the backend can still compute unbiased counts. W3C Level 2 +
     OTel `ProbabilitySampler` (development). `[RESEARCH]`
137. `ParentBased` sampler parameters: `root` (required), `remoteParentSampled`,
     `remoteParentNotSampled`, `localParentSampled`, `localParentNotSampled` — defaults AlwaysOn /
     AlwaysOff respectively. `[SOURCE]` `[RESEARCH]`
138. **[TRAP]** `parentbased_always_on` (the default) means **any caller that sets `sampled=1` can
     make you record 100%** — including a malicious or misconfigured client. Rate-limit or use a
     root-only ratio.
139. `AlwaysRecordSampler` (OTel Java incubator, 1.59.0): converts `DROP` to `RECORD_ONLY` so
     processors see all spans without exporting — the enabler for span-to-metrics.
     `[SOURCE]` `[RESEARCH]`
140. Trace context across Kafka: `traceparent` in record headers, producer `PRODUCER` span,
     consumer `CONSUMER` span, and **links rather than parent** for batch consumption. `[X-REF 14]`
141. **[TRAP]** A long-lived consumer poll loop modelled as one span produces a 6-hour span and a
     useless waterfall. One span per record (or per batch), not per poll.
142. Trace context across scheduled jobs, retries, and outbox dispatch: a retry is a **new trace
     with a link** to the original, not a resurrection of the old span. `[X-REF 14]`
143. Trace context across an async HTTP client, a `CompletableFuture` chain, and virtual threads.
     `[X-REF 04]` `[X-REF 05]`
144. Sampling and **SLO measurement are incompatible**: never compute an SLI from sampled traces.
     Derive SLIs from metrics or from unsampled span-metrics.

## 2G. Logging pipelines and query languages

145. The shipping topologies: stdout → runtime log driver → agent (Fluent Bit / Vector / Promtail /
     `awslogs`) → store; vs in-process appender → store (and why the second couples your app's
     availability to your log backend).
146. Logback: `ConsoleAppender`, `RollingFileAppender`, `AsyncAppender`
     (`queueSize`, `discardingThreshold`, `neverBlock`, `includeCallerData`),
     `PatternLayout`, `LogstashEncoder`, `MDCConverter`, `%X{}`, filters, `TurboFilter`.
147. **[TRAP]** `AsyncAppender` defaults: `queueSize=256` and `discardingThreshold=queueSize/5`
     silently **drop INFO and below** when the queue is 80% full. Your missing logs are a
     configuration default. `[RESEARCH]`
148. **[TRAP]** `includeCallerData=true` on an async appender costs a stack walk per event.
149. Log4j2 `AsyncLogger` with **LMAX Disruptor**, `AsyncAppender`, `RingBufferSize`,
     `AsyncQueueFullPolicy` (`Default`/`Discard`/`Enqueue`), and why it outperforms Logback's
     `AsyncAppender`.
150. `JsonTemplateLayout` (Log4j2) and `logstash-logback-encoder` — the two standard ways to emit
     JSON, plus Spring Boot's built-in **structured logging**
     (`logging.structured.format.console=ecs|gelf|logstash`) in Boot 3.4+. `[RESEARCH]`
151. Structured-log schemas: **ECS** (Elastic Common Schema), **GELF**, OTel log data model, and
     why picking a schema up front saves a migration.
152. **OTel logs**: `LogRecord`, severity number/text, body, attributes, and the appenders
     (`opentelemetry-logback-appender`, `log4j-appender`) that bridge SLF4J into OTLP.
153. `OTEL_LOGS_EXPORTER` (`otlp` default, `console`, `logging-otlp`, `none`) and
     `OTEL_BLRP_SCHEDULE_DELAY=1000` / `OTEL_BLRP_MAX_QUEUE_SIZE=2048` /
     `OTEL_BLRP_MAX_EXPORT_BATCH_SIZE=512`. `[SOURCE]` `[RESEARCH]`
154. **Loki's model**: index only labels, store compressed chunks in object storage; therefore
     labels are the cardinality budget and everything else is a grep at query time.
155. **LogQL**: stream selector `{app="checkout"}`, line filters `|= != |~ !~`, parsers
     `| json | logfmt | pattern | regexp`, label filters, `| line_format`, `| label_format`,
     unwrapped range aggregations (`rate`, `count_over_time`, `sum_over_time`,
     `quantile_over_time`), and metric queries from logs.
156. **[TRAP]** Putting a high-cardinality field in a Loki label. Same bug as Prometheus, different
     product.
157. Elasticsearch/OpenSearch model contrast: inverted index over every field, ILM hot/warm/cold,
     shard sizing, and why mapping explosions are the equivalent failure.
158. **CloudWatch Logs**: log groups, log streams, retention settings, subscription filters,
     metric filters, `PutLogEvents` limits, and **Logs Insights** query syntax
     (`fields`, `filter`, `stats ... by`, `parse`, `sort`, `limit`, `dedup`).
159. **CloudWatch metric filters vs EMF**: filter-based extraction (regex over log text, cheap,
     limited) vs EMF (structured, richer, dimension-controlled). `[X-REF 18]`
160. **EMF spec**: `_aws.Timestamp` (ms since epoch) + `_aws.CloudWatchMetrics[]` with
     `Namespace`, `Dimensions` (array of DimensionSets, each ≤ **30** keys, may be empty),
     `Metrics` (≤ **100** MetricDefinitions, each `Name` + optional `Unit` +
     `StorageResolution` 1 or 60, default 60). `[SOURCE]` `[RESEARCH]`
161. EMF constraints: targets must be **root-level, non-nested** members; metric targets numeric
     or numeric arrays (≤ 100 members); dimension values are strings ≤ 1024 chars; document
     limited to CloudWatch Logs' **1 MB** event size; **at-least-once** delivery, so duplicates
     are possible. `[SOURCE]` `[RESEARCH]`
162. **[TRAP]** EMF with `requestId` in `Dimensions` — "by design create a custom metric
     corresponding to each unique dimension combination." The spec itself warns about your bill.
     `[SOURCE]` `[RESEARCH]`
163. EMF **entity** fields (`Service` + `Environment`, or `ResourceType` + `Identifier`) and
     platform attributes (`EKS.Cluster`, `K8s.Namespace`, `ECS.Cluster`, `Lambda.Function`,
     `EC2.InstanceId`, `Host`) that let CloudWatch build a service map. `[SOURCE]` `[RESEARCH]`
164. `AWS/Logs` namespace metrics that tell you **EMF parsing/validation failed** — the
     observability of your observability. `[SOURCE]` `[RESEARCH]`
165. Log sampling strategies: level-based, per-logger rate limits, deterministic hash on trace ID
     (so a sampled trace keeps *all* its logs), and always-keep-on-error.
166. **[TRAP]** Independent random sampling of logs and traces guarantees that the trace you kept
     has no logs and the logs you kept have no trace. Sample on the **same** key.
167. PII handling in logs: field allowlists, tokenisation, hashing with a pepper, and the fact
     that **deletion requests apply to logs too**. `[X-REF 13]`

## 2H. Observability of the platform

168. **kube-state-metrics** — metrics from the Kubernetes **API objects** (`kube_pod_status_phase`,
     `kube_deployment_status_replicas_unavailable`, `kube_pod_container_status_restarts_total`).
     `[X-REF 19]`
169. **cAdvisor** (in the kubelet) — metrics from the **containers** (`container_cpu_usage_seconds_total`,
     `container_memory_working_set_bytes`, `container_cpu_cfs_throttled_seconds_total`).
170. **node_exporter** — metrics from the **host** (CPU, memory, disk, filesystem, network,
     `node_filesystem_avail_bytes`).
171. The distinction that matters: *desired state* (kube-state-metrics) vs *actual usage*
     (cAdvisor) vs *host capacity* (node_exporter). Three sources, three questions.
172. **`container_memory_working_set_bytes` is what the OOM killer reads**, not RSS and not
     `container_memory_usage_bytes` (which includes reclaimable page cache). `[X-REF 19]`
173. **CPU throttling** as the metric everyone misses:
     `rate(container_cpu_cfs_throttled_periods_total[5m]) / rate(container_cpu_cfs_periods_total[5m])`.
     Latency with normal CPU usage and high throttling is a limits problem. `[X-REF 19]`
174. The Prometheus Operator surface: `ServiceMonitor`, `PodMonitor`, `PrometheusRule`,
     `Probe`, `ScrapeConfig`, and `kube-prometheus-stack` as the standard install.
175. **CloudWatch Container Insights** — what it collects, its enhanced-observability mode, and
     the cost model. `[X-REF 18]`
176. **AWS X-Ray**: segments, subsegments, `X-Amzn-Trace-Id`, **sampling rules** (fixed rate +
     reservoir), the service/trace map, annotations (indexed, filterable) vs metadata (not).
     `[X-REF 18]`
177. **ADOT** (AWS Distro for OpenTelemetry) as the supported OTel Collector/agent distribution;
     `xray` and `xray-lambda` propagators; the `awsxray` exporter. `[RESEARCH]`
178. **CloudWatch Application Signals** — auto-instrumentation built on ADOT that produces
     latency/throughput/error signals plus **SLO objects and burn-rate alarms** without code
     changes; relationship to Container Insights and Transaction Search. `[RESEARCH]` — the AWS
     doc page did not render for this pass; **re-verify against AWS docs in the write pass.**
179. **JMX**: MBeans, `ObjectName`, platform MXBeans (`MemoryMXBean`, `ThreadMXBean`,
     `GarbageCollectorMXBean`, `OperatingSystemMXBean`, `RuntimeMXBean`),
     `jmx_exporter` as the bridge to Prometheus. `[X-REF 06]`
180. **[TRAP]** Exposing JMX/RMI on a network port is remote code execution. Local `jcmd` or the
     jmx_exporter agent, never an open JMX port. `[X-REF 13]`
181. **Grafana**: data sources, panels, variables/templating, `$__rate_interval`, transformations,
     Explore, dashboards-as-code (JSON, Grafonnet, Terraform provider), and **deploy annotations**.
182. **LGTM stack** positioning: **L**oki (logs), **G**rafana, **T**empo (traces), **M**imir
     (metrics), plus Pyroscope (profiles). `[RESEARCH]`
183. **Tempo**: object-storage-backed trace store, **Parquet columnar block format** (required for
     TraceQL), and metrics-generation from traces. `[SOURCE]` `[RESEARCH]`
184. **TraceQL**: designed after PromQL/LogQL; selects traces by span/resource attributes and
     intrinsics, supports structural operators and aggregations, and can produce metrics.
     `[RESEARCH]` — the Grafana docs page for this pass did not enumerate operators; **re-verify
     the operator list (`>>`, `>`, `~`, `select()`, `rate()`, `quantile_over_time()`) in the write
     pass.**
185. **Jaeger** as the reference OSS tracing backend: collector, query, dependency graph, the
     all-in-one image, and its OTLP-native mode.
186. **eBPF**-based observability: kernel-side instrumentation with no application changes;
     `bpftrace`, `bcc`, Pixie, Cilium/Hubble, Parca, Grafana Beyla for zero-code HTTP/gRPC RED
     metrics and traces.
187. What eBPF **cannot** do: see inside your business logic, name your domain operations, or
     decrypt TLS without uprobes. It is a floor, not a ceiling.
188. **Continuous profiling**: always-on, low-overhead sampling profilers shipping to a store —
     Pyroscope, Parca, Datadog/Grafana Cloud Profiles, and the OTLP Profiles signal (alpha).
189. **Synthetic monitoring** (scripted probes from outside: Blackbox exporter, CloudWatch
     Synthetics, Pingdom) vs **RUM** (real-user monitoring in the browser/app: Core Web Vitals,
     LCP/INP/CLS). What each sees that the other cannot.
190. **Blackbox exporter** module types (`http_2xx`, `tcp_connect`, `icmp`, `dns`, `grpc`), the
     multi-target exporter pattern with `params_target`, and `probe_ssl_earliest_cert_expiry` —
     the certificate-expiry alert everyone wishes they had had. `[X-REF 10]`
191. **[TRAP]** Synthetics from one region tell you about one region's network. A global product
     needs multi-region probes, or your "all green" is a lie.

---

# PART 3 — UNDER THE HOOD: implementations, constants, algorithms, proofs, failure modes

## 3A. OpenTelemetry SDK internals

1. `TracerProvider` → `Tracer` → `SpanBuilder` → `Span`: the object graph and where each lives.
2. `Context` and `ContextStorage`: the default `ThreadLocalContextStorage`, `ContextStorageProvider`
   SPI, and how the agent swaps it. `[SOURCE]`
3. `Scope` as an `AutoCloseable` that restores the previous context — the whole reason
   `makeCurrent()` must be used in try-with-resources.
4. **`Sampler.shouldSample(parentContext, traceId, name, spanKind, attributes, parentLinks)` →
   `SamplingResult`** (decision, attributes to add, tracestate to set). `[SOURCE]` `[RESEARCH]`
5. The three decisions: **`DROP`** (`isRecording()==false`, discarded), **`RECORD_ONLY`**
   (`isRecording()==true`, `sampled` flag **not** set — processors see it, exporters do not),
   **`RECORD_AND_SAMPLE`** (both true). `[SOURCE]` `[RESEARCH]`
6. **The forbidden combination**: `sampled==true` with `isRecording()==false` — it creates gaps in
   distributed traces. `[PROVE]` — show the broken-trace scenario. `[SOURCE]` `[RESEARCH]`
7. `AlwaysOnSampler` / `AlwaysOffSampler` descriptions are **specified strings**, because backends
   key off them. `[SOURCE]`
8. `TraceIdRatioBased` description must render as `"TraceIdRatioBased{0.000100}"`; the spec notes
   the **exact algorithm was never specified** and recommends root-span-only use.
   `[SOURCE]` `[RESEARCH]`
9. `TraceIdRatioBased` mechanics: take the low 8 bytes of the trace ID as an unsigned value and
   compare to `ratio × 2^64`. Why using the trace ID (not a random draw) is what makes the
   decision **consistent across services**. `[PROVE]`
10. `ProbabilitySampler` (development): **56 bits of randomness** from the trace ID
    (W3C Level 2 random flag), ratios from `2^-56` to 1.0, threshold encoding in tracestate.
    `[SOURCE]` `[RESEARCH]`
11. **Composable samplers** (development): `CompositeSampler` delegates to a `ComposableSampler`
    via `getSamplingIntent`, which returns a **threshold**, a reliability indicator, an attribute
    provider, and a tracestate provider — but makes no final decision. `[SOURCE]` `[RESEARCH]`
12. Built-in composables: `ComposableAlwaysOn`, `ComposableAlwaysOff`, `ComposableProbability`,
    `ComposableParentThreshold`, `ComposableRuleBased`, `ComposableAnnotating`.
    `[SOURCE]` `[RESEARCH]`
13. **`AlwaysRecordSampler`** converts `DROP` → `RECORD_ONLY` so span processors (span-to-metrics)
    see every span while exporters see few. `[SOURCE]` `[RESEARCH]`
14. `SpanProcessor` interface: `onStart`, `onEnd`, `isStartRequired`, `isEndRequired`,
    `shutdown`, `forceFlush`.
15. `SimpleSpanProcessor`: exports each finished span immediately, **synchronising export calls**;
    correct for tests, catastrophic in production (one network round trip per span). `[SOURCE]`
16. **`BatchSpanProcessor` defaults, exactly**: `maxQueueSize = 2048`,
    `scheduledDelayMillis = 5000`, `exportTimeoutMillis = 30000`, `maxExportBatchSize = 512`.
    `[SOURCE]` `[RESEARCH]`
17. Export triggers: queue reaches `maxExportBatchSize`, `scheduledDelay` elapses, or `forceFlush()`.
    `[SOURCE]` `[RESEARCH]`
18. **What happens when the queue is full**: spans are **dropped**, and the SDK's own
    `queueSize`/`processedSpans{dropped=true}` metrics are the only place you will see it.
    `[PROVE]` — derive max sustainable span rate from `maxQueueSize / scheduledDelay`.
19. **Span limits defaults, exactly**: `AttributeCountLimit = 128`, `EventCountLimit = 128`,
    `LinkCountLimit = 128`, `AttributePerEventCountLimit = 128`,
    `AttributePerLinkCountLimit = 128`; attribute value length unlimited by default.
    `[SOURCE]` `[RESEARCH]`
20. SDKs must log **at most once per span** when a limit causes a discard — so silent truncation
    is the normal case. `[SOURCE]` `[RESEARCH]`
21. **[TRAP]** Attaching a 200-element list or a full SQL body as an attribute: silently truncated,
    and the exporter payload balloons.
22. `MetricReader` / `PeriodicMetricReader` (`OTEL_METRIC_EXPORT_INTERVAL = 60000` ms default) vs
    `PrometheusHttpServer` (pull). `[SOURCE]` `[RESEARCH]`
23. **Views**: instrument selection (name/type/unit/scope) → stream configuration (name,
    description, attribute keys allowlist, aggregation). The supported mechanism for **dropping
    attributes to control cardinality**.
24. Aggregations: `Drop`, `Default`, `Sum`, `LastValue`, `ExplicitBucketHistogram`,
    `Base2ExponentialBucketHistogram`.
25. **Cardinality limits** in the metrics SDK: the `2000`-per-instrument default in the spec and
    the overflow attribute set `{otel.metric.overflow=true}`. `[RESEARCH]` — verify the exact
    default in the write pass.
26. Instruments: `Counter`, `UpDownCounter`, `Histogram`, `Gauge` (synchronous gauge stabilised in
    **1.38.0**), `ObservableCounter`, `ObservableUpDownCounter`, `ObservableGauge`, and the
    batch callback. `[RESEARCH]`
27. **Bound instruments** (bound counter / histogram / up-down counter / gauge) added to the
    metrics API in **1.65.0** — pre-resolve the attribute set once to avoid per-record map lookup.
    `[SOURCE]` `[RESEARCH]`
28. `isEnabled()` on `Tracer`, `Logger`, and metric instruments — **stabilised in 1.61.0** — the
    supported way to skip building expensive attributes. `[SOURCE]` `[RESEARCH]`
29. `LogRecordProcessor` / `BatchLogRecordProcessor` and its own defaults
    (`OTEL_BLRP_SCHEDULE_DELAY = 1000` ms — **shorter than spans**, deliberately). `[SOURCE]`
30. OTLP exporter internals: protobuf marshalling, **low-allocation marshalers** (1.6x work),
     gzip, retry with exponential backoff, `Retry-After`, mTLS, and the export-queue interaction.
     `[RESEARCH]`
31. **Declarative configuration** (`opentelemetry-sdk-extension-declarative-config`, aligned with
     `opentelemetry-configuration` **v1.1.0** in 1.65.0): YAML file config with env-var
     substitution and escaping, schema URLs, and composable sampler config (parent-threshold and
     rule-based) added in **1.58.0**. `[SOURCE]` `[RESEARCH]`
32. Autoconfigure SPI: `AutoConfigurationCustomizerProvider`, `ResourceProvider`,
     `ConfigurablePropagatorProvider`, `ConfigurableSpanExporterProvider` — how you extend the
     agent without forking it.
33. Full autoconfigure default table to memorise: `OTEL_TRACES_EXPORTER=otlp`,
     `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp`,
     `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`, endpoint `http://localhost:4317`,
     `OTEL_EXPORTER_OTLP_TIMEOUT=10000`, `OTEL_TRACES_SAMPLER=parentbased_always_on`,
     `OTEL_PROPAGATORS=tracecontext,baggage`,
     `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=CUMULATIVE`,
     `OTEL_METRICS_EXEMPLAR_FILTER=TRACE_BASED`. `[SOURCE]` `[RESEARCH]`
34. `OTEL_SDK_DISABLED`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_RESOURCE_DISABLED_KEYS`,
     `OTEL_EXPERIMENTAL_*` — the escape hatches. `[SOURCE]` `[RESEARCH]`
35. How the Java agent actually works: `premain`, **ByteBuddy** bytecode instrumentation,
     `Instrumenter` API, `VirtualField` for carrying state across instrumented frames, the
     **shaded/isolated classloader** so agent dependencies cannot collide with the app's.
36. Agent overhead: typical 3–10% CPU, added startup time, and the class-retransformation cost;
     what to measure before believing either a vendor or a skeptic.
37. **[TRAP]** Two agents (vendor APM + OTel) instrumenting the same methods: double spans,
     conflicting context, and occasionally a crash.
38. **[VERSION-TRAP]** `opentelemetry-exporter-zipkin` stopped being published in **1.65.0**.
     `[SOURCE]` `[RESEARCH]`
39. Baggage W3C compliance details fixed across 1.64.0 (empty values) — why a "harmless" baggage
     value can break a strict parser downstream. `[SOURCE]` `[RESEARCH]`

## 3B. Collector internals

40. Pipeline shape: **receivers → processors → exporters**, one pipeline per signal type
    (traces/metrics/logs), plus **connectors** (an exporter on one pipeline that is a receiver on
    another) and **extensions** (no data path: health check, pprof, zpages, auth, file storage).
41. The `service` section: `pipelines`, `extensions`, `telemetry` (the Collector's own metrics and
    logs), and the fact that **components not referenced in `service` are inert**.
42. Fan-out property: the same receiver can appear in multiple pipelines and multiple pipelines can
    share an exporter. `[SOURCE]` `[RESEARCH]`
43. **Agent vs gateway** deployment: daemon/sidecar/DaemonSet next to the workload, vs a central
    aggregation tier. `[SOURCE]` `[RESEARCH]`
44. Why the gateway exists at all: tail sampling, egress-point auth and cost control, retry with
    disk buffering, and shielding the backend from N thousand direct clients.
45. Core distribution vs **contrib** distribution vs vendor distributions (ADOT, Splunk, Grafana
    Alloy) and the OpenTelemetry Collector Builder (`ocb`).
46. Key receivers: `otlp`, `prometheus`, `filelog`, `hostmetrics`, `kafka`, `jaeger`, `zipkin`,
    `awsxray`, `k8sobjects`, `kubeletstats`.
47. Key processors and their **required ordering**: `memory_limiter` **first**,
    `resourcedetection`/`k8sattributes` early, `filter`/`transform`/`attributes` in the middle,
    `tail_sampling` before `batch`, **`batch` last**. `[PROVE]` — argue why each constraint holds.
48. `memory_limiter` — `check_interval`, `limit_mib`, `spike_limit_mib`: applies **backpressure**
    by refusing data rather than OOMing. The only processor whose job is to fail.
49. `batch` — `send_batch_size`, `send_batch_max_size`, `timeout`: why batching is what makes OTLP
    cheap, and why it must be last (so sampling decisions are made on whole traces).
50. `transform` with **OTTL** (OpenTelemetry Transformation Language): contexts
    (`resource`, `span`, `spanevent`, `metric`, `datapoint`, `log`), statements, conditions,
    functions (`set`, `delete_key`, `keep_keys`, `replace_pattern`, `convert_sum_to_gauge`,
    `truncate_all`, `limit`).
51. OTTL as the **redaction and cardinality-control point you can deploy without a code change** —
    strip PII, drop attributes, template URLs, at the collector.
52. `k8sattributes` processor — enriches telemetry with pod/namespace/deployment/node from the
    Kubernetes API, and the RBAC it needs.
53. **`spanmetrics` connector** — derives RED metrics (`calls`, `duration`) from spans, with
    `dimensions` you choose. The mechanism behind "sample traces aggressively but keep exact
    metrics."
54. **[TRAP]** `spanmetrics` `dimensions` including `http.url` — you have moved the cardinality
    bomb from the app to the collector.
55. `servicegraph` connector — derives a service dependency graph and edge-level latency/error
    metrics from client/server span pairs.
56. `routing` connector, `forward` connector, `count` connector, `datadog` connector.
57. **Tail sampling processor**, full policy list: `always_sample`, `latency`
    (`threshold_ms`, `upper_threshold_ms`), `numeric_attribute` (`min_value`/`max_value`),
    `probabilistic`, `status_code` (`OK`/`ERROR`/`UNSET`), `string_attribute` (exact or regex),
    `trace_state`, `trace_flags`, `rate_limiting` (token bucket, spans/s),
    `bytes_limiting`, `span_count` (min/max), `boolean_attribute`, `ottl_condition`,
    `and`, `not`, `drop`, `composite`. `[SOURCE]` `[RESEARCH]`
58. Tail sampling config and defaults: **`decision_wait = 30s`**, **`num_traces = 50000`**,
    `expected_new_traces_per_sec = 0`, `sampling_strategy` = `trace-complete` | `span-ingest`.
    `[SOURCE]` `[RESEARCH]`
59. `decision_cache.sampled_cache_size` / `non_sampled_cache_size` (default **0**) — LRU caches so
    late-arriving spans of an already-decided trace follow the decision. `[SOURCE]` `[RESEARCH]`
60. `composite` policy: `max_total_spans_per_second`, `policy_order`, `rate_allocation` —
    percentage of the budget per policy, in order. `[SOURCE]` `[RESEARCH]`
61. `and` policy semantics: all sub-policies must match, and sub-policies return a final
    `Sampled`/`NotSampled` rather than an inverted outcome. `[SOURCE]` `[RESEARCH]`
62. **The tail-sampling correctness problem**: all spans of a trace must reach the **same**
    collector instance. Load-balancing exporter with `routing_key: traceID` is the fix; without
    it you get partial traces. `[PROVE]`
63. **The tail-sampling memory model**: `num_traces × avg spans × avg span size` held for
    `decision_wait`. Derive the RAM for 10k traces/s, 20 spans, 500 B, 30 s wait. `[PROVE]`
64. **[TRAP]** `decision_wait` shorter than your slowest trace: the slow traces you were trying to
    keep are decided before their slow span arrives.
65. Collector self-telemetry: `otelcol_receiver_accepted_spans`, `otelcol_receiver_refused_spans`,
    `otelcol_processor_dropped_spans`, `otelcol_exporter_send_failed_spans`,
    `otelcol_exporter_queue_size`, `otelcol_processor_batch_batch_send_size`. **Monitor the
    monitor.**
66. Persistent queue via the `file_storage` extension — the only thing that survives a collector
    restart with data intact.
67. `zpages` (`/debug/tracez`, `/debug/pipelinez`) and `pprof` extensions for debugging the
    collector itself.

## 3C. Micrometer and Actuator internals

68. `MeterRegistry` structure: a `ConcurrentHashMap<Meter.Id, Meter>`, the `Meter.Id`
    (name + tags + base unit + type + description), and why tag **order does not matter** but tag
    **set** does.
69. `Meter.Id` equality is what creates or reuses a series — the same one-sentence rule as
    Prometheus, expressed in Java. `[SOURCE]`
70. **[TRAP]** Calling `registry.counter(...)` inside a hot loop: it is a map lookup with tag
    construction every time. Hoist the `Counter` reference (or use a bound instrument).
71. `NamingConvention` per registry: `dot` → `snake_case` for Prometheus, camelCase for others, and
    the tag-key sanitisation that silently merges two tags into one.
72. **[TRAP]** Tags `user.id` and `user_id` collapse to the same Prometheus label — a silent
    aggregation bug.
73. `PrometheusMeterRegistry` internals: `prometheus-metrics-core` `CollectorRegistry`,
    `scrape()`, and the 1.17-era support for **meters sharing a name with differing tag key sets**.
    `[RESEARCH]`
74. **[TRAP]** Historically, two meters with the same name but different tag *keys* threw or were
    dropped. This is the "my second counter never appears" bug. `[RESEARCH]`
75. `StepMeterRegistry` (`step` interval) vs cumulative registries: how Datadog/CloudWatch
    registries compute deltas per step, and why a restart loses a partial step.
76. `DistributionStatisticConfig` merge order: registry defaults → `MeterFilter` → per-meter
    builder.
77. HdrHistogram-backed `TimeWindowPercentileHistogram` and `TimeWindowFixedBoundaryHistogram`:
    memory per timer, `bufferLength` ring of `expiry`-length windows.
78. **The 276 → 73 bucket clamp**: `publishPercentileHistogram()` generates a fixed 276-bucket
    ladder, and `minimumExpectedValue`/`maximumExpectedValue` trims it to ~73 per dimension.
    Do the series arithmetic for 20 endpoints × 5 statuses. `[PROVE]` `[SOURCE]` `[RESEARCH]`
79. `Timer.record(Runnable)` / `record(Supplier)` / `Timer.Sample start(registry)` +
    `sample.stop(timer)` — and why `Sample` is what you need when the tags depend on the outcome.
80. `Timer.builder(...).publishPercentiles(0.5, 0.95, 0.99)` produces
    `http_server_requests_seconds{quantile="0.99"}` — **client-side, non-aggregable**. `[SOURCE]`
81. `@Timed` / `@Counted` internals: `TimedAspect`, `CountedAspect`, `@MeterTag` with SpEL or a
    `ValueExpressionResolver`, and the AOP proxy requirement (so **self-invocation skips it** —
    the same proxy trap as `@Transactional`). `[X-REF 07]`
82. `ObservationHandler` chain: `onStart`, `onScopeOpened`, `onScopeClosed`, `onError`, `onStop`;
    `DefaultMeterObservationHandler` (metrics), `TracingObservationHandler` (spans),
    and how one `Observation` produces both.
83. `ObservationRegistry.ObservationConfig` — where predicates, filters and handlers are attached,
    and the Spring Boot auto-registration of those bean types. `[SOURCE]` `[RESEARCH]`
84. Observation scope validation for parallel observations and the deprecated scope methods in
    recent Micrometer. `[RESEARCH]`
85. Actuator endpoint infrastructure: `EndpointDiscoverer`, `ExposableWebEndpoint`,
    `WebOperation`, `OperationInvoker`, `@EndpointExtension`, and how `/actuator` builds its
    discovery links page.
86. `HealthEndpoint` aggregation: `StatusAggregator` order
    (`DOWN` > `OUT_OF_SERVICE` > `UP` > `UNKNOWN` by default) and
    `HttpCodeStatusMapper` (`DOWN` → 503, `OUT_OF_SERVICE` → 503).
87. **Health indicator timeouts**: a `HealthIndicator` with no timeout blocks the probe, so a
    hung dependency turns readiness into a hang rather than a failure. `[PROVE]`
88. `DataSourceHealthIndicator` runs a validation query — the reason a deep health check can
    exhaust the connection pool under probe load. `[X-REF 08]`
89. `/actuator/threaddump` output format vs `jstack`, and what it can and cannot show
    (no native frames, no safepoint-free snapshot). `[X-REF 06]`
90. `/actuator/heapdump` mechanics (`HotSpotDiagnosticMXBean.dumpHeap`), the **stop-the-world
    pause it causes**, and the file size ≈ heap size. `[X-REF 06]`
91. `/actuator/metrics/{name}?tag=k:v` drill-down and why it is a debugging tool, not a scrape API.

## 3D. Instrumentation cost and JVM-level mechanics

92. What a `Counter.increment()` actually costs: a `LongAdder`-style striped add — nanoseconds,
    contention-free at low core counts. `[X-REF 05]`
93. What a `Timer.record()` costs: `System.nanoTime()` twice plus a histogram bucket increment
    plus, if percentiles are on, an HdrHistogram record.
94. `System.nanoTime()` vs `System.currentTimeMillis()`: monotonic vs wall clock, resolution, and
    why you must never compute a duration from wall clock. `[PROVE]`
95. **Clock skew** across hosts and what it does to a trace waterfall: negative durations, child
    spans starting before parents. NTP/PTP, and why backends clamp.
96. **[TRAP]** Reading a trace waterfall across two hosts as if the timeline were exact.
97. `ThreadLocal` cost and the leak shape: a pooled thread retains the last request's MDC/context
    forever if nothing clears it, which is both a correctness bug and a heap retention bug.
    `[X-REF 05]`
98. **Virtual threads and observability**: `ThreadLocal` still works but is per-virtual-thread, so
    thread-name-based and thread-count-based metrics become meaningless;
    `Thread.currentThread().getName()` is empty by default. `[X-REF 04]`
99. **Pinning and carrier threads** as things you must instrument for: JFR's
     `jdk.VirtualThreadPinned` event. `[X-REF 04]`
100. `ScopedValue` / structured concurrency as the forward-looking context mechanism. `[X-REF 04]`
101. **GC pause instrumentation**: `GarbageCollectorMXBean` notification listeners,
     `jvm.gc.pause` (Micrometer), and why a max-over-time of `jvm_gc_pause_seconds_max` is the
     right query. `[X-REF 06]`
102. **GC log analysis**: `-Xlog:gc*,safepoint:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=20M`;
     reading allocation rate, promotion rate, humongous allocations, and
     `Pause Full (Allocation Failure)`. GCViewer / GCeasy. `[X-REF 06]`
103. **Safepoint** and time-to-safepoint: why a long TTSP looks like a GC pause in every metric and
     needs `-Xlog:safepoint` to distinguish. `[X-REF 06]`
104. **Thread dump analysis workflow**: `jcmd <pid> Thread.print` ×3 at 5 s intervals; classify
     `RUNNABLE` / `BLOCKED` (with the lock owner) / `WAITING` / `TIMED_WAITING`; look for many
     threads blocked on one monitor, or all pool threads in `SocketRead`. `[X-REF 06]`
105. **Heap dump analysis workflow**: `jcmd <pid> GC.heap_dump`, MAT dominator tree, leak
     suspects, retained vs shallow heap, and `-XX:+HeapDumpOnOutOfMemoryError`
     `-XX:HeapDumpPath=`. `[X-REF 06]`
106. `jcmd` surface for operations: `VM.uptime`, `VM.flags`, `VM.system_properties`,
     `VM.native_memory summary` (needs `-XX:NativeMemoryTracking=summary`),
     `GC.class_histogram`, `Thread.print`, `JFR.start/dump/stop`. `[X-REF 06]`
107. **JFR**: event-based, always-on-capable, ~1% overhead with the `default` profile;
     `-XX:StartFlightRecording=duration=60s,filename=r.jfr,settings=profile`;
     `jfr summary` / `jfr print --events` CLI; JMC for analysis.
108. Key JFR events for operations: `jdk.ExecutionSample`, `jdk.ObjectAllocationSample`,
     `jdk.JavaMonitorEnter`, `jdk.ThreadPark`, `jdk.SocketRead`/`SocketWrite`,
     `jdk.GCPhasePause`, `jdk.SafepointBegin`, `jdk.NativeMemoryUsage`, `jdk.CPULoad`.
109. **JFR event streaming** (`jdk.jfr.consumer.RecordingStream`) — turning JFR into a live metric
     source in-process.
110. **`AsyncGetCallTrace` and the safepoint-bias problem**: JVMTI-based profilers can only sample
     at safepoints, which are biased toward specific bytecodes, so the flame graph lies.
     async-profiler uses the HotSpot-specific API to sample anywhere. `[PROVE]` `[SOURCE]`
111. **async-profiler 4.5** modes: `cpu`, `alloc`, `nativemem` (allocations and leaks), `lock`,
     `wall`, `itimer`, `ctimer`, and hardware/software perf counters (cache misses, page faults,
     context switches). `[SOURCE]` `[RESEARCH]`
112. async-profiler outputs: interactive **flame graph HTML**, **JFR**, collapsed stacks,
     heatmaps. `asprof -d 30 -f flamegraph.html <pid>`. `[SOURCE]` `[RESEARCH]`
113. Why async-profiler sees **native and kernel frames and non-Java threads** (GC, JIT) that a
     JVMTI profiler misses. `[SOURCE]` `[RESEARCH]`
114. `-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints` and `-XX:+PreserveFramePointer` —
     the flags that make the flame graph correct.
115. **Reading a flame graph**: width = samples (time), y-axis = stack depth **not** time, colour
     is arbitrary, plateaus are hot leaves. Differential/`--diff` flame graphs for before/after.
116. **Wall-clock vs CPU profiling**: a service that is slow because it is *waiting* shows nothing
     in a CPU profile. Choose `wall` for latency, `cpu` for throughput/cost. `[PROVE]`
117. Continuous profiling architecture: sample at 100 Hz, aggregate by label set
     (service/version/pod), store as a pprof-style profile, diff across deploys.
118. **[TRAP]** Profiling in production with `perf`-based modes and no `--fdtransfer`/permissions:
     `perf_event_paranoid`, missing kernel symbols, and containers without `CAP_PERFMON`.
     `[X-REF 11]`
119. `-XX:NativeMemoryTracking` and the OOM taxonomy for containers: heap vs metaspace vs code
     cache vs thread stacks vs direct/mapped buffers vs malloc arenas — and which one
     `container_memory_working_set_bytes` includes. `[X-REF 06]` `[X-REF 19]`

## 3E. Alerting mathematics and failure modes

120. **Burn rate** definition: the multiple of the budget-consumption rate that would exactly
     exhaust the budget over the SLO window. Constant 0.1% error rate against a 99.9% SLO = burn
     rate **1**. `[SOURCE]` `[PROVE]`
121. `budget consumed = burn rate × window ÷ SLO period`. `[SOURCE]` `[PROVE]` — derive 14.4.
122. The **six alerting approaches** in ascending order: (1) target error rate over a short window,
     (2) increased alert window, (3) incrementing alert duration, (4) burn rate, (5) multiple burn
     rates, (6) **multiwindow multi-burn-rate**. `[SOURCE]` `[RESEARCH]`
123. Why (1) fails: 10-minute window at the SLO threshold → terrible precision, pages on a
     1-minute blip.
124. Why (2) fails: a 36-hour window has good precision but a **reset time** measured in hours —
     the alert keeps firing long after you fixed it.
125. Why (3) fails: a fixed `for:` duration gives poor recall (a slow burn never satisfies it) and
     poor detection time.
126. The **recommended table for a 99.9% SLO**, exactly: page at burn rate **14.4** over a
     **1 h** long / **5 min** short window (**2%** of budget); page at **6** over **6 h** /
     **30 min** (**5%**); ticket at **1** over **3 d** / **6 h** (**10%**).
     `[SOURCE]` `[RESEARCH]` `[PROVE]`
127. **The short window is ~1/12 of the long window**, and its job is to ensure the budget is
     *still actively being consumed* — which is what fixes the reset-time problem. `[SOURCE]`
128. Precision and recall as the formal frame for alert quality: precision = fraction of pages
     that were real; recall = fraction of real incidents that paged. Every knob trades them.
129. **Detection time** and **reset time** as the other two axes; a four-axis evaluation of any
     proposed alert. `[PROVE]`
130. The PromQL shape of a multiwindow burn-rate alert, with recording rules for the SLI ratio at
     each window and `and` to combine long and short.
131. Why you record the **SLI ratio**, not the raw counters, at multiple windows: rule evaluation
     cost, and consistency between the alert and the dashboard.
132. **Alert on symptoms, not causes**, with the argument: cause space is unbounded and mostly
     uncorrelated with impact; symptom space is small, stable, and always meaningful. `[PROVE]`
133. `CPU > 80%` as the canonical bad alert: a batch job at 90% meeting its deadline is *good*.
134. Page / ticket / dashboard classification, with the criterion for each: page = user-visible
     impact **and** immediate human action required.
135. **Every page must be actionable.** "Look at it and go back to sleep" is a ticket.
136. **Alert fatigue** as the dominant failure mode of on-call: 30 pages a night and the rotation
     stops reading them, so the one that mattered is lost.
137. Alert on **absence**: no orders in 10 minutes, no heartbeat from a nightly job, zero traffic.
     `absent_over_time()` / dead-man's-switch (`Watchdog` alert + an external check that the
     Watchdog is still arriving). `[PROVE]` — why the dead man's switch is the only alert that
     detects a dead monitoring system.
138. Alert on **saturation** (queue depth, consumer lag, pool utilisation) because it warns before
     users are affected.
139. `for:` durations so a 30-second blip pages nobody, and the interaction between `for:`,
     `group_wait`, and detection time — total time-to-page is the **sum**.
140. **[TRAP]** `for: 5m` on an alert whose expression uses `[5m]` — you have a 10-minute detection
     time you did not intend.
141. **Counter reset** handling: `rate()`/`increase()` treat any decrease as a reset and add the
     pre-reset value. Consequence: a pod restart inflates `increase()` slightly, and a
     *legitimate* gauge decrease read as a counter is nonsense. `[PROVE]`
142. **Missing-data alerts**: `absent()`, `up == 0`, and the two opposite policies
     (`no data → alarm` vs `no data → notBreaching`) in CloudWatch alarms.
143. **CloudWatch alarm specifics**: evaluation periods, datapoints-to-alarm, `M out of N`,
     `TreatMissingData` (`missing`/`ignore`/`breaching`/`notBreaching`), anomaly-detection bands,
     composite alarms. `[X-REF 18]`
144. **[TRAP]** A CloudWatch alarm on a metric that is only published when the event happens: with
     `TreatMissingData: notBreaching`, total failure looks healthy.
145. **Metric staleness** vs **absence** vs **zero** — three different states that most alerting
     expressions conflate. Enumerate what each looks like in Prometheus and in CloudWatch.
146. **Cardinality bomb** as an incident class, with its signature: ingestion latency rises,
     `prometheus_tsdb_head_series` climbs, scrapes start failing, then the whole monitoring stack
     is down and you have no visibility into the thing that caused it.
147. **Log volume incident** as an incident class: a debug flag or a retry storm 100×'s log volume,
     the pipeline throttles, the log driver backpressures the app, and **the application slows
     down because of logging**.
148. **Observability outage as a correlated failure**: the monitoring runs in the same cluster,
     the same region, behind the same DNS. The argument for an out-of-band paging path and an
     external status check.
149. **[TRAP]** Alerting on a metric that your own service produces about itself, so a total
     failure of the service means no alert.

## 3F. Deployment safety mechanics

150. **CI vs Continuous Delivery vs Continuous Deployment** — three things, constantly conflated,
     with the exact distinctions.
151. **CI is a development practice**: every developer merges to a shared mainline at least daily,
     and every merge is automatically built and tested. The **integrating** is the practice.
152. **A beautiful pipeline running on two-week-old feature branches is not CI.** The pipeline is
     the feedback mechanism, not the practice.
153. **Continuous Delivery**: every passing change is deployed to a production-like environment and
     is always releasable; production deploy is a **business decision executed by a button**.
154. **Continuous Deployment**: every passing change is released to production with **no human
     approval**. No button.
155. The comparison table across: what it is, merge cadence, automated build/test, always-releasable
     artefact, prod deploy mechanism, prerequisites.
156. The verbatim one-liner: "CI is about merging and testing frequently. Continuous Delivery means
     it's always *ready* to release. Continuous Deployment means it *does* release, automatically."
157. **Continuous Deployment is not automatically the goal**: it requires trusted tests, feature
     flags, fast automated rollback, and monitoring that catches problems in minutes. Saying
     "Continuous Delivery with a human gate is right for most teams" is a maturity signal.
158. Pipeline stages in order: commit → build (one immutable artefact) → unit tests → static
     analysis → security scan (CVE, secret scanning, SAST) → package (image tagged with git SHA)
     → integration tests (Testcontainers) → publish → staging deploy → smoke/contract/e2e →
     production deploy (manual = CD-delivery, automatic = CD-deployment) → post-deploy
     verification. `[X-REF 16]`
159. **Build the artefact once and promote the same artefact** through every environment.
     Rebuilding per environment means you tested one binary and shipped another. `[X-REF 18]`
160. **Fail fast**: cheapest checks first. A 40-minute pipeline failing on lint at minute 38
     destroys the feedback loop that makes CI valuable.
161. **A red build is stop-the-line.** A pipeline failing for two days is not a pipeline.
162. **Flaky tests are worse than no tests** — they teach re-run-and-ignore, which is exactly the
     habit that lets a real failure through. Quarantine and fix. `[X-REF 16]`
163. Pipeline definitions in the repo (`.github/workflows/`, `.gitlab-ci.yml`), reviewed like code.
     Under 10 minutes to a deployable artefact as a target.
164. Deployment strategies table: **recreate** (downtime), **rolling** (no downtime, both versions
     live, slow rollback), **blue/green** (instant cutover and rollback, 2× infra, migrations are
     the hard part), **canary** (bounded blast radius, real traffic validation, needs
     traffic-splitting and automated analysis), **feature flags** (deploy ≠ release, instant
     off-switch, flag debt).
165. Rolling is the Kubernetes default; **canary is the strongest option for risky changes**
     because it is the only one that validates against real production traffic with a bounded
     blast radius. `[X-REF 19]`
166. **Both versions run at once** in rolling and canary, so every change must be backward
     compatible: API contracts, message schemas, database schemas. This constraint is the source
     of most deployment incidents. `[X-REF 12]` `[X-REF 14]`
167. **Progressive delivery** as the umbrella term; Argo Rollouts / Flagger `AnalysisTemplate`
     with Prometheus queries as the automated gate.
168. **Automated canary analysis**: define success as "error rate and p99 of the canary are not
     statistically worse than baseline", the required minimum sample size, and the
     Mann-Whitney/Kayenta-style comparison. `[PROVE]` — why comparing canary to *baseline running
     now* beats comparing to yesterday.
169. **[TRAP]** A 1% canary on a service doing 10 req/s: you will not accumulate enough samples to
     detect a 5% error-rate regression before the canary window expires. Canary needs traffic.
170. **Automated rollback** triggers, and the rule that rollback must not require the person who
     deployed.
171. Rollback enablers: immutable versioned artefacts with retained image history, backward-
     compatible migrations, feature flags, **no irreversible side effects on startup**, and a
     **practised** procedure. `[X-REF 19]`
172. **Fast rollback is worth more than careful deployment** — you will get it wrong eventually,
     and MTTR is what users experience.
173. **Feature flags** mechanics: flag evaluation (local vs remote), targeting rules, percentage
     rollout with a **sticky hash on user ID**, kill switches, and OpenFeature as the standard.
174. Flag debt, the combinatorial test surface, and a flag-removal SLA.
175. **[TRAP]** A flag whose default on evaluation failure is "on". Flags must fail to the safe
     side, and the safe side is usually the old behaviour.
176. **Zero-downtime chain**, all nine links: multiple replicas across AZs → rolling/blue-green
     with `maxUnavailable: 0` → readiness probe that only passes when genuinely serving (including
     cache warm-up) → `preStop` hook (~5 s) so LB deregistration propagates before SIGTERM →
     **exec-form `ENTRYPOINT`** so the JVM receives SIGTERM → graceful shutdown in the app →
     `terminationGracePeriodSeconds` > preStop + longest in-flight request → backward-compatible
     schemas → client retries with backoff and jitter. `[X-REF 19]` `[X-REF 10]`
177. Break any one link and you get the classic "a few 502s on every deploy" that teams live with
     for years. `[PROVE]` — trace the packet through each broken link.
178. **Graceful shutdown internals**: `server.shutdown=graceful`,
     `spring.lifecycle.timeout-per-shutdown-phase`, `SmartLifecycle` phases, and the order
     stop-accepting → drain in-flight → flush buffers → close pools → exit 0. `[X-REF 19]`
179. **Graceful shutdown of a Kafka consumer** is a different problem: stop polling, commit
     offsets, leave the group cleanly to avoid a rebalance storm. `[X-REF 14]`
180. **Flush your telemetry on shutdown**: `SdkTracerProvider.close()` / `forceFlush()`, or the
     last 5 seconds of spans and logs — the ones describing the shutdown — are lost. `[PROVE]`
181. **Expand/contract migrations**, all four deploys: expand (add nullable column, write both,
     read old) → backfill in batches → migrate reads (read new, still write both) → contract (use
     new only; drop old in a *later* release). `[X-REF 09]`
182. Rules that fall out: never ship a schema change and the code depending on it in the same
     deploy; additive changes are safe (new nullable column, new table, `CREATE INDEX
     CONCURRENTLY`), destructive ones are not (drop, rename, narrow, `NOT NULL` without default);
     test every migration against a production-sized dataset. `[X-REF 09]`
183. **Observability of a migration**: a metric for rows backfilled, a metric for "reads that
     found the new column null", and an alert on the second. The thing that makes expand/contract
     verifiable rather than hopeful.
184. **DORA metrics**, all five with definitions: **Deployment Frequency**, **Change Lead Time**
     (commit → deployed), **Change Fail Rate** (deployments requiring immediate intervention),
     **Failed Deployment Recovery Time**, **Deployment Rework Rate** (unplanned deployments caused
     by a production incident). Grouped as **throughput** (first two) and **instability** (last
     three). `[SOURCE]` `[RESEARCH]`
185. **[VERSION-TRAP]** DORA renamed "MTTR" to **Failed Deployment Recovery Time** and added
     **Deployment Rework Rate** as a fifth metric. `[RESEARCH]`
186. **[RESEARCH — INCOMPLETE]** The elite/high/medium/low numeric bands were not on the fetched
     DORA page. **The write pass must fetch the current State of DevOps report for the bands or
     state that they are report-year-specific and omit numbers.**
187. **MTTD / MTTA / MTTR / MTBF** — the four incident metrics, what each measures, and the honest
     warning that MTTR is a **median of a long-tailed distribution** and is easily gamed.
188. Why "reduce MTTR" is a better goal than "reduce incident count": the next incident will be
     different, but detection and recovery are reusable. `[PROVE]`
189. **Chaos engineering**: the principles (steady-state hypothesis, vary real-world events, run in
     production, automate, minimise blast radius), the experiment template, and the ordering rule
     — you must have observability *before* you have chaos.
190. Chaos primitives: instance termination, latency injection, error injection, resource
     exhaustion, network partition, dependency blackhole, clock skew, AZ evacuation.
     Chaos Monkey / Gremlin / Litmus / AWS FIS. `[X-REF 18]`
191. **GameDays** and the specific value of practising a rollback, a failover, and an on-call
     handover before you need them.
192. **[TRAP]** Running a chaos experiment without a stop condition and an abort button. The
     experiment becomes the incident.

---

# PART 4 — BUILD IT: from-scratch implementations that mirror the real thing

1. `[BUILD]` **A counter, gauge, and histogram registry from scratch** — `MeterId`
   (record with name + sorted tag list), `ConcurrentHashMap<MeterId, Meter>`, `LongAdder`-backed
   counter, supplier-backed gauge, fixed-boundary cumulative histogram with a `+Inf` bucket, and
   a `scrape()` that emits valid Prometheus text exposition. Followed by
   **Diff vs Micrometer**: naming conventions, `MeterFilter`, HdrHistogram percentiles,
   step registries, weak-reference gauges, thread-safe re-registration, cardinality limits.
2. `[BUILD]` **`histogram_quantile` from scratch** — given cumulative bucket counts and φ, find the
   bucket, linearly interpolate, handle `+Inf` (return the last finite bound), handle φ=0 and φ=1,
   handle a histogram with all observations in one bucket. Followed by **Diff vs Prometheus**:
   native-histogram path, NaN semantics, `le` sorting, monotonicity repair for non-monotonic
   buckets from a racing scrape, and the `histogram_quantile` warning annotations Prometheus emits.
3. `[BUILD]` **An exponential (native) histogram** — schema-based bucket index
   `index = ceil(log(v) / log(base))` with `base = 2^(2^-schema)`, a zero bucket with threshold,
   positive and negative bucket arrays, and **automatic scale reduction** when bucket count
   exceeds `maxSize` (merge adjacent buckets, decrement schema). Followed by
   **Diff vs the OTel/Prometheus implementations**: the exact index formula using
   `Math.getExponent` for the base-2 fast path, sub-normal handling, mergeability rules, and the
   protobuf encoding with delta-encoded bucket spans.
4. `[BUILD]` **A W3C `traceparent` parser and serialiser** — strict validation (length, lowercase
   hex, forbidden all-zero trace-id and span-id, version `ff` rejected, forward-compatible
   handling of unknown versions with extra fields), `sampled` flag extraction, and a
   `tracestate` parser enforcing 32 members, 256-char keys/values, `tenant@system` keys, and
   left-insertion mutation. Followed by **Diff vs OTel's `W3CTraceContextPropagator`**: the
   `SpanContext.isValid()` contract, invalid-header-means-start-new-trace behaviour, allocation
   avoidance, and `TraceStateBuilder`'s ordering guarantees.
5. `[BUILD]` **A consistent-probability head sampler** — take the low 64 bits of the trace ID,
   compare against `ratio × 2^64` using unsigned arithmetic, and prove the decision is identical
   on every service for the same trace. Followed by **Diff vs `TraceIdRatioBased`**: 56-bit
   randomness and the W3C random flag, description-string format, `ParentBased` wrapping,
   threshold propagation in tracestate, and why the spec deprecated the simple version.
6. `[BUILD]` **A `BatchSpanProcessor`** — bounded `ArrayBlockingQueue(2048)`, a worker thread
   exporting on `size >= 512` or every 5000 ms, non-blocking `offer` with a `dropped` counter,
   `forceFlush()` with a `CompletableFuture`, and `shutdown()` that drains. Followed by
   **Diff vs the real one**: `JcTools` queues, `isRecording` short-circuit, export timeout
   handling, self-telemetry (`queueSize`, `processedSpans`), re-entrancy guard so exporting does
   not create spans, and `close()` semantics.
7. `[BUILD]` **A tail-sampling buffer** — `Map<TraceId, List<Span>>` plus a delay queue keyed by
   first-seen time, a `decisionWait` of 30 s, a `numTraces` cap of 50,000 with LRU eviction, a
   policy chain (`latency > 500ms` OR `status == ERROR` OR `probabilistic 1%`), and a decision
   LRU cache for late spans. Followed by **Diff vs the collector's processor**: the
   trace-affinity/load-balancing requirement, `span-ingest` vs `trace-complete` strategies,
   composite rate allocation, OTTL conditions, and memory accounting.
8. `[BUILD]` **A burn-rate SLO evaluator** — given a good-events counter and a total-events
   counter sampled over time, compute the SLI ratio over an arbitrary window, the burn rate
   against a target SLO, and evaluate the full multiwindow multi-burn-rate rule set (14.4/1h+5m,
   6/6h+30m, 1/3d+6h) returning `OK` / `TICKET` / `PAGE`. Followed by
   **Diff vs Prometheus recording+alerting rules**: counter-reset handling, left-open ranges,
   `for:`/`keep_firing_for`, staleness, and rule-group evaluation ordering.
9. `[BUILD]` **A correlation-ID + trace-context filter and propagation chain** — an
   `OncePerRequestFilter` that accepts or generates the ID, puts it in MDC, echoes it in the
   response header, and clears in `finally`; a `RestClient` request interceptor; a Kafka
   `ProducerInterceptor`/`ConsumerInterceptor` pair using record headers; and a `TaskDecorator`
   that copies the MDC map across an executor boundary. Followed by
   **Diff vs Micrometer/OTel**: `ContextSnapshot`/`ThreadLocalAccessor`, `Scope` restoration
   rather than clear, propagator composition, and `ContextPropagatingTaskDecorator`.
10. `[BUILD]` **A JSON structured-log encoder** — a Logback `EncoderBase<ILoggingEvent>` emitting
    a flat JSON object with `ts`, `level`, `logger`, `thread`, `msg`, `service`, `version`,
    `env`, MDC fields, `traceId`, `spanId`, a `stack` field for throwables, and a redaction
    allowlist. Followed by **Diff vs `logstash-logback-encoder` / `JsonTemplateLayout`**:
    ECS/GELF schema conformance, streaming JSON generation without intermediate strings,
    caller-data cost, marker and structured-argument support, and exception-chain rendering.
11. `[BUILD]` **A rate-limited, sampling logger wrapper** — token bucket per
    (logger, level, message template) so a retry storm logs the first N and then a periodic
    summary with a suppressed count; plus deterministic sampling keyed on trace ID so a sampled
    trace keeps all its lines. Followed by **Diff vs Logback's `DuplicateMessageFilter` /
    Log4j2's `BurstFilter`**: allocation, thread-safety, and where in the pipeline filtering
    should live.
12. `[BUILD]` **A cardinality guard `MeterFilter`** — track distinct tag values per (metric, tag
    key), and once a configurable ceiling is exceeded, replace the value with `"__overflow__"`
    and increment a `metrics.cardinality.overflow` counter. Followed by
    **Diff vs `MeterFilter.maximumAllowableTags` and the OTel cardinality limit**: overflow
    attribute-set semantics, per-instrument vs per-registry scope, and why replacing beats
    dropping.
13. `[BUILD]` **A `HealthIndicator` with a timeout and a cached result** — run the check on a
    bounded executor with a 2-second timeout, cache the last result for 5 seconds, degrade to the
    last known value with a `stale=true` detail, and never let a hung dependency hang the probe.
    Followed by **Diff vs Spring's `HealthContributor` infrastructure**: `StatusAggregator`,
    `HttpCodeStatusMapper`, health groups, reactive contributors, and why Spring deliberately
    does *not* time out for you.
14. `[BUILD]` **A minimal Prometheus exposition endpoint on the JDK `HttpServer`** — content
     negotiation between text and OpenMetrics, `# HELP`/`# TYPE` emission, label escaping, gzip,
     and a `scrape_duration` self-metric. Followed by **Diff vs `PrometheusHttpServer` /
     `PrometheusMeterRegistry`**: protobuf and native-histogram negotiation, exemplars,
     name-collision handling, and UTF-8 name quoting.
15. `[BUILD]` **A synthetic prober** — a scheduled job that performs a real end-to-end business
     transaction against production (create a QuizStakes quiz, submit an answer, verify the
     score), emits `probe_success`, `probe_duration_seconds`, and `probe_step_duration_seconds{step}`,
     and cleans up after itself. Followed by **Diff vs Blackbox exporter / CloudWatch
     Synthetics**: the multi-target exporter pattern, TLS-expiry metrics, multi-region execution,
     and canary artefact/screenshot capture.

---

# PART 5 — INTERVIEW & RETENTION

## 5A. The one-line assertions (the checklist the write pass must end with)

1. Every leaf in Parts 1–4 that carries a `[TRAP]` becomes one checklist line.
2. Every constant in this syllabus becomes one checklist line with its value.
3. **Nothing already in the current guide's `## Atomic concept checklist` may be dropped** — all
   65 existing lines survive, expanded.

## 5B. Definition-and-distinction questions

4. "Logs, metrics, traces — what question does each answer, and what is the cost model of each?"
5. "Monitoring vs observability, without buzzwords."
6. "SLI vs SLO vs SLA. Which one has lawyers involved?"
7. "What is an error budget and what do you *do* with it?"
8. "Histogram vs summary. Which can you aggregate, and why?"
9. "Counter vs gauge — give me a case where choosing wrong loses data permanently."
10. "Head-based vs tail-based sampling. What does tail-based require that head-based does not?"
11. "Liveness vs readiness vs startup probe. What goes in each?"
12. "CI vs Continuous Delivery vs Continuous Deployment."
13. "RED vs USE vs the four golden signals."
14. "Baggage vs span attributes vs resource attributes."
15. "Span links vs parent-child. When do you need a link?"
16. "`rate()` vs `irate()` vs `increase()`."
17. "Recording rule vs alerting rule."
18. "Metric filter vs EMF in CloudWatch."
19. "Synthetic monitoring vs RUM."
20. "MTTD vs MTTA vs MTTR vs MTBF."
21. "Continuous profiling vs on-demand profiling. Why would you run a profiler all the time?"
22. "Wall-clock vs CPU profiling — which one finds a slow database call?"

## 5C. Mechanism questions

23. "Walk me through what happens, byte by byte, when service A calls service B with tracing on."
24. "Draw the `traceparent` header and name every field with its length."
25. "How does a Prometheus histogram let you compute a fleet-wide p99 that a summary cannot?"
26. "What exactly does `histogram_quantile` do inside the bucket?"
27. "How does `TraceIdRatioBased` make the same decision in five different services?"
28. "What are the four exact defaults of `BatchSpanProcessor` and what happens when the queue
    fills?"
29. "Why does `RECORD_ONLY` exist as a sampling decision?"
30. "What does the OTel Java agent actually do at JVM startup?"
31. "How does MDC end up in every log line, and why does it vanish across `@Async`?"
32. "How does Prometheus know a series has gone away, and what does a query return then?"
33. "Trace the nine links of the zero-downtime chain and tell me which 502 each broken link
    produces."
34. "Walk me through expand/contract for renaming a column, deploy by deploy."
35. "Derive the burn rate 14.4 from a 99.9% SLO and a 1-hour window."
36. "Derive the number of Prometheus series a Spring Boot app with 20 endpoints and
    `publishPercentileHistogram` produces."
37. "Why does the collector's `batch` processor have to come after `tail_sampling`?"
38. "Why must all spans of a trace reach the same collector instance?"

## 5D. Design and judgement questions

39. "Design observability for the QuizStakes checkout flow from scratch. What do you instrument,
    what do you alert on, and what do you *not* alert on?"
40. "You have $50k/year for observability and a 200-service estate. Where does the money go?"
41. "Your on-call rotation gets 30 pages a night. Give me a 90-day plan."
42. "Define three SLOs for a quiz-submission API and justify each number."
43. "You can only keep one pillar. Which, and why?"
44. "Your p99 is 2 s but every downstream reports p99 under 50 ms. What is happening and how do
    you prove it?"
45. "Latency is up 3× and CPU, memory, GC, and error rate all look normal. Enumerate causes."
46. "Orders dropped 80% and every infrastructure metric is green. What do you do first?"
47. "A deploy went out 8 minutes before the alert. What is your first action and why is it not
    'read the logs'?"
48. "Your Prometheus fell over. What did the last person to merge probably do?"
49. "How would you find out whether this problem affects only EU customers on the new pricing
    plan — right now, without a deploy?"
50. "Roll out a risky pricing change to 40M users. Describe the delivery mechanics."
51. "How do you know your monitoring is working?"
52. "Design the alert set for a Kafka consumer that must not fall behind." `[X-REF 14]`
53. "You need 99.99% availability. What does that force you to automate?"
54. "How do you instrument a service that uses virtual threads?" `[X-REF 04]`

## 5E. The traps, as questions that catch people

55. "What is wrong with `meterRegistry.counter("orders", "userId", userId)`?"
56. "What is wrong with averaging p99 across pods?"
57. "What is wrong with putting a DB check in the liveness probe?"
58. "What is wrong with `log.error(e.getMessage())`?"
59. "What is wrong with `catch (e) { log.error(e); throw e; }`?"
60. "What is wrong with an alert on `CPU > 80%`?"
61. "What is wrong with a `RollingFileAppender` in a container?"
62. "What is wrong with `AsyncAppender`'s defaults?"
63. "What is wrong with sampling logs and traces independently?"
64. "What is wrong with `parentbased_always_on` on an internet-facing service?"
65. "What is wrong with a CloudWatch alarm using `TreatMissingData: notBreaching` on an
    error-count metric?"
66. "What is wrong with computing an SLI from sampled traces?"
67. "What is wrong with a gauge alert of the form `queue_depth > 1000` when the exporter dies?"
68. "What is wrong with one span per Kafka poll loop?"
69. "What is wrong with a 1% canary on a 10 req/s service?"
70. "What is wrong with `@Timed` on a method called from within the same class?" `[X-REF 07]`
71. "What is wrong with exposing `/actuator/heapdump`?"
72. "What is wrong with running your monitoring in the cluster it monitors?"
73. "What is wrong with a postmortem whose action items have no owner?"
74. "What is wrong with `for: 5m` on an expression over `[5m]`?"

## 5F. Incident response, on-call, and postmortem content

75. **The sequence**: acknowledge and declare → assess blast radius and severity → **mitigate
    before diagnosing** → ask what changed → communicate → verify recovery → postmortem.
76. **Incident Commander** — one person coordinating who is explicitly *not* debugging. Unowned
    incidents produce five people chasing one theory and nobody talking to stakeholders.
77. The ICS-derived role set: Incident Commander, Operations/Ops Lead, Communications Lead,
    Planning/Scribe, and subject-matter experts.
78. **Severity levels** and what each triggers, defined in advance; "how many users, doing what"
     as the commander's first question.
79. **Data loss or corruption is a different and worse category** than unavailability, because it
     is not fixed by restoring service.
80. **Mitigate before diagnosing**, with the full menu: roll back the deploy, shift traffic away
    from an AZ, flip the feature flag, kill the bad pod, shed load, serve stale, raise a limit,
    fail open, fail closed.
81. The argument for it: diagnosis is much easier in an hour, from logs and traces, with users
    unaffected and nobody watching. **The instinct to find root cause first is a developer
    instinct; suppressing it is what operational maturity looks like.** `[PROVE]`
82. **"What changed?"** as the highest-yield question: deploys, config, feature flags,
    infrastructure changes, traffic shifts, a dependency's deploy, **certificate expiry**, a data
    migration, or the calendar (month-end, DST, leap day). `[X-REF 17]`
83. **Communicate on a fixed cadence** (every 15–30 min) even when the update is "no new
    information." Silence makes people escalate, join the call, and slow you down. Say what is
    affected, what you are doing, and when you will next update. Status page for customer-visible
    impact.
84. **Verify recovery with metrics, not vibes** — and check that a **backlog** is not about to
    cause a second incident. A two-hour consumer outage leaves a queue that can take far longer
    than the outage to drain. `[X-REF 14]`
85. **The thundering herd on recovery**: every client retrying at once, every cache cold, every
    connection pool re-establishing. Jittered backoff and staged capacity restoration.
    `[X-REF 10]` `[X-REF 15]`
86. **Blameless postmortems** and the concrete reason: **if naming a cause gets someone punished,
    people stop telling you what actually happened**, and you lose the information you need to fix
    the system.
87. Systems that permit a single human error to cause an outage are broken systems — a missing
    guardrail, not a missing person. "Why was it possible for one command to do that?" is the
    productive question.
88. Postmortem contents: timeline with timestamps (detection → mitigation → resolution), impact
    (users, duration, revenue, SLO burn), **contributing factors, plural**, what went well, what
    did not, and action items with **owners and dates**.
89. Distinguish **detection** failures ("we found out from a customer") from **response** failures
    ("the runbook was wrong") from **prevention** failures — they have different fixes.
90. "5 whys" for depth, plus the caveat that it forces a single linear chain onto a multi-causal
    event; **Cynefin / STAMP / "how complex systems fail"** as the counterweight.
91. Always ask **"how could we have detected this sooner?"** and **"how could we have recovered
    faster?"** — more reusable than root-cause elimination, because the next incident is different
    but detection and recovery are not.
92. A postmortem with no action items, or with action items nobody owns, is **theatre**. Track them
    like any other work, with a completion SLA by severity.
93. **Runbook contents**: what the alert means in plain language, how to assess severity and blast
    radius, the first three things to check with copy-pasteable commands and dashboard links,
    known causes and fixes, how to mitigate (with "roll back" as an explicit named option), when
    and who to escalate to, and links to the dashboard, repo, and past incidents.
94. **Link the runbook from the alert itself.** A runbook nobody can find during an incident does
    not exist. Update it after every incident that used it.
95. **Dashboard design**: one dashboard per question and per reader. Service overview (RED per
    endpoint, dependency health, saturation, **deploy annotations**) that loads fast and fits one
    screen; business dashboard; per-subsystem deep dives.
96. **Deploy annotations are the highest-value, lowest-effort addition to any dashboard.** Most
    important panel top-left; consistent time ranges; a few well-chosen panels over forty.
97. **[TRAP]** A dashboard nobody can parse under stress is worse than three graphs everyone can.
98. **On-call basics**: ≥1-in-6 rotation (never 1-in-2), clear primary and secondary, explicit
    escalation path, **compensation or time off in lieu**, and a hard rule that the person paged
    overnight does not work a normal day after.
99. Shift handover contents: what is currently degraded, what changed, what to watch.
100. **On-call load is a metric to be driven down**, not an endurance test. A painful rotation is a
     signal about system quality and alert hygiene. A standing agenda item to review last week's
     pages and delete or fix the useless ones is what keeps it from degrading.
101. **Follow-the-sun vs single-region on-call**, and the honest trade-off (context handover cost
     vs nobody being woken).
102. **Error-budget policy as the escalation authority**: what happens, organisationally, when the
     budget is gone — and who signs it.

## 5G. Retention scaffolding

103. **One master cost/characteristics table** covering, for every telemetry type: what it answers,
     cardinality tolerance, cost unit, typical retention, aggregation properties, sampling
     legitimacy, and query latency.
104. **One master cost table for operations**: for each of counter increment, timer record,
     histogram record with percentiles, span create+end, log line (sync), log line (async), MDC
     put/clear, and heap dump — the order-of-magnitude cost and whether it is on the request path.
105. **Availability arithmetic table** (99% → 99.999%) with per-30-days and per-year downtime.
106. **Burn-rate table** (14.4/6/1 with windows and budget percentages).
107. **Constants flashcard set**: `maxQueueSize=2048`, `scheduledDelay=5000ms`,
     `exportTimeout=30000ms`, `maxExportBatchSize=512`, span limits `128`,
     `OTEL_METRIC_EXPORT_INTERVAL=60000ms`, `OTEL_BLRP_SCHEDULE_DELAY=1000ms`,
     OTLP `4317`/`4318`, `decision_wait=30s`, `num_traces=50000`, traceparent `32`/`16` hex,
     tracestate `32` members / `256` chars, native histogram schemas `-4..8` and `-53`,
     Micrometer `276`→`73` buckets, semconv HTTP buckets
     `[0.005 … 10]`, EMF `30` dimensions / `100` metrics / `1 MB`, burn rates `14.4`/`6`/`1`.
108. **The five-sentence answer** for each of: what observability is, why cardinality matters, why
     you cannot average percentiles, what an error budget is for, and why you mitigate before you
     diagnose.
109. **A 60-second whiteboard diagram** to be able to draw from memory: app → SDK/agent → collector
     (agent) → collector (gateway, tail sampling) → {metrics store, trace store, log store} →
     query layer → dashboard/alert → pager, with the correlation IDs annotated on each edge.
110. **The QuizStakes worked example thread**: every code sample in the write pass uses QuizStakes
     entities, status codes, and numbers from `src/scenario/scenario.md`. `[X-REF scenario]`

---

## Gaps vs the current guide

`src/topics/20-observability-operations.md` is 709 lines and covers ten sections. Assessment per
syllabus area:

| Syllabus area | Present in `src/topics/20-observability-operations.md` | Missing | Shallow |
|---|---|---|---|
| Three pillars + workflow + monitoring-vs-observability | §1 | — | — |
| Wide events / high cardinality / observability 2.0 | — | **missing** | — |
| Profiles as a fourth pillar | — | **missing** | — |
| Structured logging rules + PII | §2 | — | — |
| Correlation IDs and MDC | §2 | — | — |
| Logback/Log4j2 appender internals, async queue defaults, JSON encoders | — | **missing** | — |
| Spring Boot structured logging (`logging.structured.format.*`) | — | **missing** | — |
| Log levels, stdout in containers | §3 | — | — |
| Log sampling / rate limiting | §3 (one bullet) | — | **shallow** |
| LogQL / Loki / Logs Insights / metric filters | — | **missing** | — |
| EMF spec and its limits | — | **missing** | — |
| RED / USE / golden signals | §4 | Little's Law, utilisation law, queue-flavoured signals | — |
| Percentiles, averages lie, cannot average percentiles, fan-out | §4 | coordinated omission, HdrHistogram, pause detection | — |
| Histogram vs summary | §4 (one paragraph) | native/exponential histograms, schemas, NHCB, error arithmetic | **shallow** |
| Cardinality trap | §4 | series arithmetic, `maximumAllowableTags`, finding the offender, cost models | — |
| Meter types | §4 (three types) | `LongTaskTimer`, `FunctionCounter`, `FunctionTimer`, `TimeGauge`, `MultiGauge`, filters, naming conventions | **shallow** |
| Business metrics | §4 | — | — |
| Prometheus exposition format, PromQL, rules, remote write, staleness, relabeling, Alertmanager | — | **missing entirely** | — |
| Micrometer/Actuator configuration surface, Observation API, `@Observed` | mentioned only | **missing** | — |
| Trace/span model, causal structure | §5 | span kinds, links, events, status, resource, scope | — |
| OpenTelemetry API/SDK/Collector split, OTLP, semconv | §5 (one paragraph) | **missing** | **shallow** |
| `traceparent` field-level detail, `tracestate` limits, other propagators | §5 (named only) | **missing** | **shallow** |
| Baggage | — | **missing** | — |
| Sampling: samplers, decisions, composable, consistent probability | §5 (head vs tail) | **missing** | **shallow** |
| Collector architecture, processors, tail-sampling policies and defaults | — | **missing** | — |
| Health endpoints, liveness/readiness traps | §6 | startup probe, health groups, `ApplicationAvailability`, indicator timeouts | — |
| Actuator endpoint inventory and access control | §6 (five endpoints) | full inventory, `access` properties, CSRF, caching, custom endpoints | **shallow** |
| CI vs CD vs CD, pipeline stages, principles | §7 | — | — |
| Deployment strategies, rollback enablers, zero-downtime chain | §7 | progressive delivery, automated canary analysis, OpenFeature | — |
| Expand/contract | §7 | migration observability | — |
| Incident response sequence, IC, mitigate-first, what changed, comms | §8 | ICS role set, severity definitions, recovery thundering herd | — |
| Postmortems | §8 | — | — |
| Alerting design, page/ticket/dashboard, absence, saturation | §9 | — | — |
| Burn-rate alerting | §9 (one paragraph) | the six approaches, the exact 14.4/6/1 table, precision/recall/detection/reset axes, PromQL form | **shallow** |
| Dashboards, runbooks, on-call | §9 | error-budget policy authority, follow-the-sun | — |
| SLI/SLO/SLA, error budget, availability table | §10 | request- vs windows-based SLIs, SLI types, rolling vs calendar | — |
| DORA / MTTD / MTTA / MTBF | — | **missing** | — |
| Profiling: async-profiler, JFR, flame graphs, safepoint bias | — | **missing** | — |
| Thread dump / heap dump / GC log analysis | — | **missing** (owned by 06, needs a paragraph + `[X-REF 06]`) | — |
| JMX / MXBeans / jmx_exporter | — | **missing** | — |
| eBPF, continuous profiling, Beyla/Pixie | — | **missing** | — |
| k8s observability (kube-state-metrics, cAdvisor, node_exporter, throttling) | — | **missing** | — |
| AWS observability (CloudWatch, X-Ray, ADOT, Application Signals, Container Insights) | — | **missing** | — |
| Grafana / LGTM / Tempo / TraceQL / Jaeger | — | **missing** | — |
| Synthetic monitoring, RUM, Blackbox exporter, cert expiry | — | **missing** | — |
| Chaos engineering, GameDays | — | **missing** | — |
| Observability cost model, retention tiers, sampling economics | one line in the §1 table | **missing** | — |
| Correctness/failure modes: counter resets, clock skew, staleness, cardinality bomb, log-volume incident, monitoring-outage correlation | cardinality only | **missing** | — |
| Clock skew and `nanoTime` vs `currentTimeMillis` | — | **missing** | — |
| Virtual threads and observability | — | **missing** | — |
| From-scratch builds | — | **missing entirely** (Part 4) | — |
| Interview question bank and trap-as-question set | checklist only | **missing** (Part 5) | — |

**Nothing in the existing guide is dropped.** All ten sections map onto Part 1/2/3 leaves, and all
65 lines of its `## Atomic concept checklist` are carried through Part 5A.

---

## Sources consulted

`WebSearch` was **unavailable for this pass** — the session's 200-query budget was already spent by
sibling agents, so the research phase was conducted entirely via `WebFetch` against primary
sources (specs, changelogs, and official docs), which is the stronger of the two anyway. Every URL
below was fetched, not inferred. Two fetches returned little usable content and are flagged for
re-verification in the write pass.

| URL | What it contributed |
|---|---|
| https://raw.githubusercontent.com/open-telemetry/opentelemetry-java/main/CHANGELOG.md | OTel Java release train and dates (1.65.0 = 2026-08-07 … 1.60.1 = 2026-03-08); bound instruments added in 1.65.0; exemplar filter stable 1.56.0; synchronous gauge stable 1.38.0; `isEnabled()` stable 1.61.0; `AlwaysRecordSampler` 1.59.0; composable/parent-threshold/rule-based samplers in declarative config 1.58.0; `opentelemetry-configuration` v1.1.0 alignment; Zipkin exporter unpublished from 1.65.0; low-allocation OTLP marshalers |
| https://github.com/open-telemetry/opentelemetry-java/releases | Corroborated the above; Prometheus exporter default host change 0.0.0.0 → localhost; OTLP Profiles alpha in 1.62.0; declarative-config artifact split |
| https://opentelemetry.io/docs/specs/otel/trace/sdk/ | Sampler interface signature; the three sampling decisions and the forbidden `sampled && !recording` combination; AlwaysOn/AlwaysOff/TraceIdRatioBased (stable, deprecated, "exact algorithm never specified")/ParentBased parameters; `ProbabilitySampler` with 56 bits of randomness; `CompositeSampler`/`getSamplingIntent` and the six built-in composables; `AlwaysRecord`; Simple vs Batching span processor; **BatchSpanProcessor defaults 2048 / 5000 ms / 30000 ms / 512**; **span limits all 128**; the "log at most once per span" rule |
| https://opentelemetry.io/docs/languages/java/configuration/ | The full autoconfigure env-var table with defaults: `unknown_service:java`, exporter defaults, `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`, timeout 10000, sampler `parentbased_always_on` and the seven sampler values, propagator list and `tracecontext,baggage` default, BSP/BLRP tunables, `OTEL_METRIC_EXPORT_INTERVAL=60000`, temporality preference incl. `LOWMEMORY`, `EXPLICIT_BUCKET_HISTOGRAM` vs `BASE2_EXPONENTIAL_BUCKET_HISTOGRAM`, `OTEL_METRICS_EXEMPLAR_FILTER=TRACE_BASED` |
| https://opentelemetry.io/docs/zero-code/java/agent/configuration/ | Agent-only properties (`otel.javaagent.configuration-file`, `.extensions`, `.logging`); cloud resource providers disabled by default; **agent 2.0+ defaults to `http/protobuf`, not `grpc`** |
| https://opentelemetry.io/docs/specs/semconv/http/http-metrics/ | Stable `http.server.request.duration` / `http.client.request.duration` in **seconds**; required vs conditional attributes; **default bucket boundaries `[0.005 … 10]`**; active-request and body-size metrics still in development |
| https://www.w3.org/TR/trace-context/ | `traceparent` grammar and exact field sizes; forbidden all-zero IDs; version `ff` invalid; only the LSB of trace-flags defined and its "may have recorded" wording; `tracestate` key/value charsets and 256-char limits, `tenant@system` keys, **32 list members**, 512-char propagation floor, 128-char truncation rule, left-insertion mutation rules; W3C Recommendation 23 Nov 2021, version `00` only |
| https://raw.githubusercontent.com/prometheus/prometheus/main/CHANGELOG.md | Latest releases (3.14.0 = 2026-08-17 back to 3.11.0 = 2026-04-02); 3.0.0 UTF-8 names by default, **left-open range selectors and lookback delta**, native histograms promoted, legacy feature flags removed; Remote Write 2.0 RC in 2.54.0; OTLP delta-temporality ingest; out-of-order ingestion; `oci_sd_configs` in 3.14 |
| https://prometheus.io/docs/specs/native_histograms/ | Schemas −4…+8 and −53 for NHCB; resolution halving per schema step; boundary formula `(2^(2^-n))^i`; zero bucket and threshold (default 0); NHCB mergeability limits; the four counter-reset hint flags; **protobuf-only exposition, text format never extended**; stable in 3.8, `scrape_native_histograms` / `send_native_histograms` required from 3.8 and default `true` from v4 |
| https://prometheus.io/docs/practices/histograms/ | The histogram/summary/native comparison across instrumentation cost, aggregability, series count, flexibility; `_bucket`/`le`/`+Inf`/`_sum`/`_count` structure; the 220 ms worked error example (228 ms vs 295 ms); "averaging quantiles yields statistically nonsensical values"; φ-dimension vs value-dimension error; `histogram_fraction`-based Apdex; the "prefer native histograms" recommendation |
| https://prometheus.io/docs/prometheus/latest/querying/functions/ | The function inventory: `rate`/`irate`/`increase`/`delta`/`idelta`/`resets`/`changes`, all `histogram_*` functions, `absent`/`absent_over_time`, `predict_linear`, `clamp*`, `label_replace`/`label_join`; and the experimental set behind `--enable-feature=promql-experimental-functions` (`double_exponential_smoothing`, `sort_by_label*`, `info`, `histogram_quantiles`, `start`/`end`/`range`/`step`, `min_of`/`max_of`) |
| https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/ | Rule-group fields (`name`, `interval`, `limit`, `query_offset`, `labels`); `record`/`expr`/`labels` and the `level:metric:operations` naming convention; `alert`/`for`/`keep_firing_for`/`labels`/`annotations`; `ALERTS`; `rule_group_iterations_missed_total` and the skipped-iteration gap; `promtool check rules` |
| https://prometheus.io/docs/specs/remote_write_spec_2_0/ | `io.prometheus.write.v2.Request`, symbols table / string interning; `Content-Type` proto parameter and `X-Prometheus-Remote-Write-Version` (2.0.0 / 0.1.0); mandatory `*-Written` response headers; created timestamps, native histograms, exemplars with `trace_id`, metadata; **partial write ⇒ 5xx and full retry**; 4xx permanent, 429 optional; Snappy |
| https://docs.spring.io/spring-boot/reference/actuator/endpoints.html | Spring Boot **4.1.1** docs; the full endpoint inventory incl. `httpexchanges`, `quartz`, `startup`, `sessions`, `integrationgraph`, `logfile` (Range header), `heapdump` (HPROF/PHD); only `health` exposed by default on HTTP and JMX; `management.endpoints.access.default` / `.<id>.access` / `.max-permitted`; endpoint response caching TTL; sanitisation; CSRF on write operations; health groups incl. `additional-path=server:/livez`; `EndpointRequest.toAnyEndpoint()` |
| https://docs.spring.io/spring-boot/reference/actuator/observability.html | Observation API autoconfig; `lowCardinalityKeyValue` → metrics+traces vs `highCardinalityKeyValue` → traces only; auto-registered `ObservationPredicate`/`GlobalObservationConvention`/`ObservationFilter`/`ObservationHandler`/`ObservationRegistryCustomizer`; `management.observations.enable.*` and `.key-values.*`; `management.observations.annotations.enabled` + `aspectjweaver` for `@Observed`/`@Timed`/`@Counted`/`@MeterTag`/`@NewSpan` and the duplicate-observation warning; `management.tracing.sampling.probability` (default 1.0) and `.propagation.type`; Brave vs OTel bridge artifacts; `management.opentelemetry.*` incl. `map-environment-variables`; metric names `http.server.requests`, `http.client.requests`, `jvm.*`; datasource-micrometer for JDBC and `r2dbc-proxy` for R2DBC; `spring.reactor.context-propagation=auto`, `spring.task.execution.propagate-context`, `ContextPropagatingTaskDecorator` |
| https://docs.micrometer.io/micrometer/reference/concepts/histogram-quantiles.html | `publishPercentiles` (non-aggregable) vs `publishPercentileHistogram`; **276 default buckets clamped to ~73** by min/max expected value; `serviceLevelObjectives`; only **Prometheus, Atlas, Wavefront** support histogram-based percentiles |
| https://docs.micrometer.io/micrometer/reference/concepts.html | Meter-type inventory (Counter, Gauge, Timer, LongTaskTimer, DistributionSummary, plus FunctionCounter/FunctionTimer/TimeGauge/MultiGauge); meter filters (deny/rename/map/metric limits); optional LatencyUtils (pause detection) and HdrHistogram (client percentiles) dependencies |
| https://github.com/micrometer-metrics/micrometer/releases | Current GA line **1.17.x** with 1.16.x/1.15.x in maintenance and 1.18.0-M1 in flight; Prometheus registry support for same-name meters with differing tag key sets; OTLP exporter exemplar support; Observation scope-validation changes |
| https://sre.google/workbook/alerting-on-slos/ | The six alerting approaches and why 1–5 fail; the recommended multiwindow multi-burn-rate table for a 99.9% SLO (**14.4 / 1 h / 5 min / 2%**, **6 / 6 h / 30 min / 5%**, **1 / 3 d / 6 h / 10%**); `budget consumed = burn rate × window ÷ period`; burn rate 1 ⇔ a constant 0.1% error rate; the **short window ≈ 1/12 of the long window** rule and its purpose |
| https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/tailsamplingprocessor/README.md | The complete tail-sampling policy list (18 policy types incl. `bytes_limiting`, `ottl_condition`, `drop`, `and`, `not`, `composite`); **`decision_wait=30s`, `num_traces=50000`, `expected_new_traces_per_sec=0`**; `sampling_strategy` `trace-complete` vs `span-ingest`; `decision_cache.sampled_cache_size`/`non_sampled_cache_size` default 0; composite `max_total_spans_per_second`/`policy_order`/`rate_allocation`; `and` policy decision semantics |
| https://opentelemetry.io/docs/collector/architecture/ | Receivers/processors/exporters and pipeline composition; the same receiver in multiple pipelines and shared exporters; agent vs gateway deployment patterns. (This page did **not** cover connectors, extensions, the `service` section, or processor ordering — those leaves are from established Collector documentation and must be re-verified in the write pass against https://opentelemetry.io/docs/collector/configuration/) |
| https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html | Full EMF spec: `_aws.Timestamp` in epoch ms, `CloudWatchMetrics` MetricDirective with `Namespace`/`Dimensions`/`Metrics`; **≤ 30 dimension keys per DimensionSet**, **≤ 100 MetricDefinitions**, metric arrays ≤ 100 members, dimension values ≤ 1024 chars, namespace ≤ 1024, **1 MB** document limit; `Unit` enum and `StorageResolution` 1 or 60 (default 60); root-level non-nested target rule; **at-least-once delivery with possible duplicates**; the explicit high-cardinality-dimension billing warning; entity fields and platform attributes; `AWS/Logs` namespace metrics for EMF parse/validation failures |
| https://github.com/async-profiler/async-profiler | **Version 4.5**; modes (CPU, Java heap alloc, native memory alloc and leaks, contended locks, hardware/software perf counters); the HotSpot-specific API and the **safepoint-bias** problem it solves; visibility of native/kernel frames and non-Java threads; output formats (flame graph HTML, JFR, collapsed, heatmap); `asprof -d 30 -f flamegraph.html <pid>`; Linux/macOS x64+arm64 |
| https://dora.dev/guides/dora-metrics-four-keys/ | **Five** metrics with definitions — Change Lead Time, Deployment Frequency, Failed Deployment Recovery Time (throughput/instability split), Change Fail Rate, **Deployment Rework Rate**. **The elite/high/medium/low numeric bands were NOT on this page** — flagged at leaf 3F.186 for the write pass |
| https://grafana.com/docs/tempo/latest/traceql/ | TraceQL exists, is modelled on PromQL/LogQL, requires Tempo's **Parquet columnar block format** (the default), and supports metrics-from-traces. **The operator/intrinsic inventory was not on this page** — flagged at leaf 2H.184 for the write pass |
| https://docs.honeycomb.io/get-started/basics/observability/concepts/ | **Low yield.** Confirmed only that Honeycomb frames observability around OpenTelemetry, distributed tracing, high cardinality, and structured instrumentation. It did **not** carry "wide events", "observability 2.0", BubbleUp, or the pre-aggregation argument. Leaves 1B.16–1B.20 are therefore marked as conceptual/vendor-vocabulary rather than spec, and the write pass should cite Charity Majors' writing or the Honeycomb LLM index (https://docs.honeycomb.io/llms.txt) instead |
| https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html | **Failed to render** — the fetch returned a model-generated overview rather than page content, so nothing from it is treated as verified. Leaf 2H.178 is flagged `[RESEARCH]` with an explicit instruction to re-fetch in the write pass |

**Searches not performed:** `WebSearch` returned "this session has used its web search budget
(200 of 200)". The angles that would normally be covered by search — interview-question lists,
gotcha/postmortem writeups, published curricula, adversarial "what people get wrong" articles —
were substituted by (a) the primary specs above, which name concepts directly, and (b) the trap
inventory already in `src/topics/20-observability-operations.md`. **This is the one weakness of
this pass**: the Part 5 question bank is derived from the mechanism leaves rather than harvested
from real interview corpora. If the budget is raised, a follow-up Mode A sweep on the
interview-surface and adversarial angles would be worth one run.

---

## Leaf counts

| Part | Leaves | of which `[RESEARCH]` |
|---|---|---|
| Version-delta preamble | 14 | 12 |
| PART 1 — Basics | 156 | 21 |
| PART 2 — Intermediate | 191 | 41 |
| PART 3 — Under the hood | 192 | 33 |
| PART 4 — Build it | 15 (all `[BUILD]`) | 0 |
| PART 5 — Interview & retention | 110 | 0 |
| **Total** | **678** | **107** |

Other tag counts: `[PROVE]` 44, `[SOURCE]` 61, `[TRAP]` 48, `[BUILD]` 15, `[VERSION-TRAP]` 9,
`[X-REF]` 38 (to guides 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, and
`src/scenario/scenario.md`).

Three leaves are deliberately marked incomplete for the write pass to resolve against a source:
3F.186 (DORA performance bands), 2H.178 (CloudWatch Application Signals), 2H.184 (TraceQL
operator inventory), plus 3A.25 (OTel metrics cardinality-limit default) and 3B.41–3B.67
(Collector `service` section and processor ordering, to be re-verified against
`opentelemetry.io/docs/collector/configuration/`).

`src/topics/` was not modified by this pass.
