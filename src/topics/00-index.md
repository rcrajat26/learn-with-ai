# Topic Guides — Index

Twenty-six mechanism-level guides for backend Java interview prep (3–4 YOE, FAANG/senior-tier bar).
Each guide explains *how the thing actually works*, not just how to use it, and ends with an
`## Atomic concept checklist` you can self-quiz against.

## How to use these

1. Read a guide top to bottom once. Do not skim the **Trap:** markers — they are the exact places
   diagnostic papers showed knowledge breaking down (volatile mistaken for atomicity, Integer cache,
   HashMap constants, Spring proxy self-invocation).
2. Re-read only the atomic concept checklist before an interview. If you cannot state the mechanism
   in one sentence, go back to that section.
3. Guides cross-reference each other. Concurrency mechanics live in 05 even when collections (02)
   or Spring (07) touch them.

## The twenty-six guides

| # | File | Scope in one line |
|---|---|---|
| 01 | `01-dsa-fundamentals.md` | Big-O incl. amortized, arrays/strings, hashing, two pointers & sliding window, stacks/monotonic stacks, queues/deques, linked lists, trees/BST, BFS/DFS, heaps, binary search variants, recursion, and intros to DP, greedy, graphs, tries, union-find — plus the signals that tell you which pattern a problem wants. |
| 02 | `02-java-collections.md` | The full `Collection`/`Map` hierarchy and the internals underneath it: ArrayList/LinkedList/ArrayDeque growth, HashMap buckets and treeification, LinkedHashMap as an LRU, TreeMap red-black navigation, PriorityQueue sift mechanics, the equals/hashCode contract, fail-fast iterators, and Comparator fluency. |
| 03 | `03-java-core.md` | The language substrate: primitives vs wrappers and the Integer cache, String pool and immutability, `==` vs `equals`, static/final semantics, exceptions and try-with-resources, generics erasure and PECS, interfaces vs abstract classes, enums, immutability design, BigDecimal for money, the java.time model, and pass-by-value-of-reference. |
| 04 | `04-modern-java.md` | Java 8 through 21: lambdas and functional interfaces, the Stream pipeline and collectors, Optional discipline, `var`, records, sealed types with pattern-matching switch, text blocks, switch expressions, virtual threads and pinning, and structured concurrency. |
| 05 | `05-multithreading-concurrency.md` | Threads and the memory model: races, `synchronized`'s two guarantees, what `volatile` does and does not do, happens-before, CAS and atomics, deadlock, ThreadPoolExecutor's queueing order, CompletableFuture, BlockingQueue backpressure, ThreadLocal leaks, safe publication, and ConcurrentHashMap's compound-action rules. |
| 06 | `06-jvm-internals.md` | Runtime memory areas and which error each throws, generational GC and G1, the OOM taxonomy, classloading (CNFE vs NoClassDefFoundError), JIT warmup, and the diagnostic toolkit — jstack/jcmd/jmap/jstat, thread-dump and heap-dump workflows, container memory flags, JMH. |
| 07 | `07-spring-core.md` | The container: bean lifecycle, dependency injection styles, scopes, the proxy model and why self-invocation silently skips `@Transactional`/`@Cacheable`, AOP, configuration and profiles, Spring Boot auto-configuration and conditionals. |
| 08 | `08-spring-data-jpa.md` | Persistence context and entity states, dirty checking, lazy loading and `LazyInitializationException`, the N+1 problem and its fixes, fetch strategies, transaction propagation and isolation in practice, locking, ID generation, and repository query derivation. |
| 09 | `09-sql-databases.md` | Relational modelling and normalization, joins, indexes (B-tree, composite, covering) and why an index goes unused, query plans, ACID and isolation-level anomalies, MVCC, locking and deadlocks, transactions, and when NoSQL earns its place. |
| 10 | `10-networking.md` | TCP/IP and the handshake, TLS, HTTP/1.1 vs 2 vs 3, DNS, load balancing, connection pooling and keep-alive, timeouts and retries, latency budgets, and the failure modes each layer produces. |
| 11 | `11-operating-systems-linux.md` | Processes, threads and scheduling, virtual memory and paging, file descriptors, signals, the OOM killer, and the working command set — top/htop, ps, lsof, netstat/ss, strace, dmesg, journalctl — for diagnosing a sick box. |
| 12 | `12-api-design.md` | REST resource modelling, HTTP verbs and status codes, idempotency, versioning, pagination, error contracts, HATEOAS in practice, gRPC and GraphQL trade-offs, rate limiting, and backward-compatible evolution. |
| 13 | `13-web-security.md` | AuthN vs AuthZ, sessions vs JWT, OAuth 2.x and OIDC flows, password storage, the OWASP Top 10 with concrete Java exploits and fixes, CORS, CSRF, XSS, SQL injection, secrets management, and TLS configuration. |
| 14 | `14-messaging-queues.md` | Queues vs logs, Kafka mechanics (partitions, offsets, consumer groups, rebalancing), delivery semantics and exactly-once, ordering guarantees, idempotent consumers, dead-letter queues, RabbitMQ contrasts, and outbox/saga patterns. |
| 15 | `15-caching.md` | Cache-aside vs read/write-through vs write-behind, eviction policies, TTL and staleness, Redis data structures and persistence, distributed cache invalidation, stampede and thundering-herd prevention, and Spring Cache abstraction. |
| 16 | `16-testing.md` | The test pyramid, JUnit 5 mechanics, Mockito (stubbing vs verification, argument captors, common misuse), Spring Boot test slices, Testcontainers, contract testing, flaky-test causes, mutation testing, and what coverage does and does not tell you. |
| 17 | `17-git-craft.md` | The object model, branching strategies, merge vs rebase, interactive rebase, cherry-pick, reflog recovery, bisect, hooks, conflict resolution, and reviewable commit hygiene. |
| 18 | `18-cloud-aws.md` | Core AWS primitives (EC2, S3, RDS, DynamoDB, SQS/SNS, Lambda), IAM roles and policies, VPC and subnets, ALB/NLB, autoscaling, availability zones and regional failure, cost drivers, and infrastructure as code. |
| 19 | `19-docker-kubernetes.md` | Images, layers and caching, Dockerfile discipline for JVM apps, container resource limits, Kubernetes objects (Pod, Deployment, Service, Ingress, ConfigMap, Secret), probes, rolling updates, HPA, and debugging a CrashLoopBackOff. |
| 20 | `20-observability-operations.md` | The three pillars (metrics, logs, traces), structured logging, Micrometer and Prometheus, distributed tracing and context propagation, SLI/SLO/error budgets, alerting that does not page falsely, incident response, and postmortems. |
| 21 | `21-ai-for-coding.md` | Claude Code as an engineered system: the agent loop and the context window as a budget, `.claude/` anatomy and settings precedence, the five channels that supply context (system prompt, CLAUDE.md, slash commands, skills, tool results), subagents as context isolation, hooks as the deterministic escape hatch, headless `claude -p` with turn/time/dollar ceilings, plugins and marketplaces, and the deterministic-vs-agentic decision rule. Worked against a real multi-agent SDLC harness. |
| 22 | `22-system-design.md` | The composition layer: the 45-minute structure, requirement extraction and back-of-envelope arithmetic, the scale-up ladder, storage selection as a procedure, replication and replica-lag fixes, partitioning/consistent hashing/hot keys, CAP–PACELC and per-operation consistency, quorum `R+W>N`, idempotency and the outbox, ID generation, rate limiting and load shedding, resilience patterns, multi-region, read models, migration under live traffic, and four worked designs (shortener, feed, chat, ledger). |
| 23 | `23-terraform.md` | Infrastructure as code runtime: the state file as the single authority (not a cache), the plan-graph-apply execution model, why state locking prevents concurrent-apply corruption, resource replace vs. update and why provider versions matter, for_each stability and drift detection, sensitive output redaction vs. state encryption, and debugging orphaned resources. |
| 24 | `24-design-patterns-architecture.md` | Patterns as forces and consequences: the creational family (incl. the JVM singleton idioms and why DCL needs `volatile`), the adapter/facade/proxy/decorator intent boundary, JDK proxy vs CGLIB and what neither can intercept, strategy/template/state trade-offs, visitor's double dispatch and its sealed-switch replacement, SOLID stated as mechanisms (LSP violations that compile, DIP as the enabler of hexagonal), the anti-pattern catalogue with failure mechanisms (anemic model, transaction script, fragile base class, cycles), architecture styles (layered, hexagonal/clean/onion, package-by-feature, DDD tactical patterns and the aggregate invariant boundary, CQRS/event sourcing, modular monolith vs microservices arithmetic), resilience patterns by the failure each was invented for, and refactoring smell → smallest safe move → protecting test. |
| 25 | `25-java-performance.md` | Performance as a method, not a bag of tricks: goals stated as a percentile, why averages lie and coordinated omission corrupts load tests, USE/Amdahl/Little's-law arithmetic worked with numbers, why a naive `nanoTime` loop measures nothing and what each JMH construct defends against, JIT as a cost model (tiering, inlining budgets, mono/bi/megamorphic call sites, escape analysis, deopt storms, AOT/CRaC/native-image), allocation rate and write barriers and time-to-safepoint as latency sources, collector selection by SLO and GC-log arithmetic, object layout and the 32 GB compressed-oop cliff, cache lines and false sharing and the latency numbers table, contention cost curves and pool sizing, the application-layer costs that actually dominate (serialisation, logging, regex, boxing, DTO copying), sampling vs safepoint-biased profiling with async-profiler and JFR, flame-graph reading, and the ordered script for a p99 regression. |
| 26 | `26-behavioral-leadership.md` | The non-coding half of the loop as a scored mechanism: the note→debrief→committee pipeline and why `no signal` (not a bad story) is the common failure, the five rubric axes, L4/L5/L6 calibration by blast radius of the decision you owned (one event re-told at all three levels), STAR-L with a per-part time budget, the "we for work / I for decisions" rule, deriving a metric from inputs you already have, the failure story that owns a decision error and ends in a systemic fix, the 20-story bank from 8–12 events with a coverage matrix, Amazon's 16 LPs with weak-answer signatures and the Google/Meta/HM mapping, question taxonomy with the real probe behind each, influence-without-authority and disagree-and-commit as mechanisms, surviving follow-up drilling, delivery/rehearsal mechanics, the anti-pattern catalogue, an 8-criterion self-scoring rubric, and the cadence mapped to the 28-week plan's behavioral milestones. |

## Reading order suggestions

- **Language depth first (most common interview weight):** 03 → 02 → 04 → 05 → 06.
- **Performance track:** 03 → 05 → 06 → **25**. Read 25 last of the four — it assumes the runtime areas
  and GC vocabulary from 06 and the concurrency mechanics from 05, and only teaches the cost model on
  top of them.
- **Backend system design track:** 09 → 10 → 12 → 14 → 15 → 18 → 19 → 20 → **22**. Read 22 last —
  it assumes the component mechanisms from those guides and only teaches how to compose them.
- **Framework track:** 07 → 08 → 16.
- **Design / architecture track:** 03 → 07 → **24** → 22. Read 24 after 07 (it assumes the proxy
  model) and before 22 (22 composes services; 24 is what happens inside one).
- **Algorithms are orthogonal:** run 01 in parallel with everything else, daily.
- **Behavioral is orthogonal and slow-burning:** read **26** once in the first month, then spend
  1–1.5h/week on it for the rest of prep. Stories need months of rehearsal to sound unrehearsed, and
  26 assumes 22 (design-round behavioral leakage) and 20 (incident/postmortem material) as sources.
- **Tooling / craft track:** 17 → 21. Read 21 once early — it changes how you use the tool you are
  studying with, and its cost/verification arguments compound over the whole 28 weeks.

## Format contract every guide follows

- 250–450 lines.
- One mechanism explanation per concept — what the runtime/library actually does, with the numbers
  (load factor 0.75, treeify threshold 8, Integer cache −128..127) stated explicitly.
- **Trap:** markers on the specific misconceptions that fail candidates.
- A closing `## Atomic concept checklist` of one-line assertions.

## Atomic concept checklist

- [ ] I know which of the 26 guides owns each topic, so I do not hunt for concurrency in the collections guide.
- [ ] I know the guides are mechanism-first: the answer to "how does it work" is the deliverable, not "how do I call it".
- [ ] I treat every **Trap:** marker as a known past failure, not trivia.
- [ ] I use the atomic concept checklists as the pre-interview review layer, not the full text.
