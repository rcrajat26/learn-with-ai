# FAANG Staff/Tech-Lead Prep — Final Day-by-Day Plan (v4, 28 weeks)

> **This is the final consolidated plan.** It supersedes v2 + v3-supplement and adds two new weeks (10 days) to close the highest-priority topic gaps identified in the topic audit.
>
> **What's new vs the v3 consolidated:**
> - **NEW Week 15: Modern Spring + Auth + Distributed Patterns** — Java 21 Virtual Threads, Spring Security, OAuth2/OIDC/JWT/mTLS, Saga+Outbox+CDC, Dijkstra + concurrency LeetCode.
> - **NEW Week 21: Canonical HLD + LLD + DDIA gaps** — News Feed, Web Crawler, File Storage HLD; DDIA Ch 4 (Encoding) + Ch 11 (Streams) + WebSockets/NIO; Elevator + Logging Framework + BookMyShow LLD.
> - **Slot-ins** (no new days): Kinesis added to Kafka sessions, Schema Registry to Kafka #2, Helm basics to K8s #2, CAP/PACELC to DDIA Ch 9, reverse interview questions to Day 123, expanded negotiation in Week 28.
> - All days from Day 71 onward have been renumbered to absorb the two new weeks. Total: **140 days, 28 weeks, ~560 hours**.

**Profile:** Backend Dev, 6 yrs · Java/Spring Boot · DSA beginner · Targeting **Staff / Tech Lead** roles
**Commitment:** 4 hrs/day × 5 days/week × 28 weeks = **140 days, ~560 hours**
**Focus areas:** Pure backend services + Distributed systems · Real AWS portfolio · Some prior lead experience

**Tech defaults:**
- Spring Boot 3.x · Java 21 (LTS) · Maven · GitHub Actions
- PostgreSQL on RDS (Project 2) and Aurora PostgreSQL (Project 3)
- HikariCP · Hibernate · Spring Kafka · Spring Security · Flyway
- Local Kubernetes via `kind` or `minikube`
- Testcontainers for integration tests

---

## Why this plan targets Staff, not Senior IC

You're targeting Staff/Tech Lead, not Senior IC. The interview signals shift:

| Signal | Senior (L5) | Staff (L6) |
|---|---|---|
| DSA | Critical | Important, but not differentiating |
| HLD | One round, "design X" | Multiple rounds, deep dives, *trade-off debate* |
| LLD / API design | Sometimes | Often a dedicated round |
| Past architecture impact | Nice to have | **The hire/no-hire signal** |
| Cross-team influence | Some | Required |
| Technical strategy | Not asked | "How would you set direction for this team?" |

This plan keeps DSA volume moderate (~160 problems) to free time for what actually gets you Staff offers: deep system design, architectural judgment, real built systems, Java/Spring/JPA fluency, and a story bank that demonstrates leadership.

---

## How to use this plan

- **Day types over time-slicing.** Each study day has a *primary focus* (DSA day, HLD day, Build day, etc.) — go deep on one track for ~3 hrs, with 1 hr of complementary work. Far better than 4 × 1-hr blocks.
- **5 study days/week. Pick your 2 rest days. Don't break them.**
- **If you miss a day, push the calendar.** Never compress.
- **End of each day:** 5-min log. **End of each week:** 30-min review.

## Day-type legend

- **DSA-D:** DSA-Heavy (3h DSA + 1h theory/Java/reading)
- **HLD-D:** System Design Heavy (3h HLD + 1h DSA review)
- **LLD-D:** LLD / API / Schema design (3h LLD + 1h DSA)
- **Build-D:** AWS portfolio project work (4h focused build)
- **Review-D:** Weekly review + behavioral + mock (mixed)
- **Mock-D:** Mock interview + post-mortem (Phase 3 onward)
- **DS-D:** Distributed Systems deep — papers, DDIA, blogs (Phase 2+)
- **JSD-D:** Java/Spring Deep Dive (3h focused topic + 1h project application)
- **Auth-D:** Authentication/Authorization deep dive (Phase 2 only)
- **DistTx-D:** Distributed Transaction Patterns (Phase 2 only)
- **Kafka session:** ~2h hands-on, woven into Project 2 build days
- **K8s session:** 1–2h side-work, woven into Phase 3 slots

---

## Resources

### Core
- **NeetCode 150 / Roadmap** — DSA progression (neetcode.io)
- **LeetCode** — practice + company-tagged problems
- **CTCI** — warmups for Phase 1
- **Alex Xu "System Design Interview" Vol. 1 & 2** — HLD scaffolding
- **DDIA (Kleppmann)** — read 60% of it over Phases 2–3. Non-negotiable for Staff.
- **"Designing Distributed Systems" by Brendan Burns** (optional, for patterns)
- **Refactoring Guru** — design patterns
- **Effective Java (Bloch)** — skim 20 most relevant items
- **Spring Boot reference docs** — your second textbook for Phase 2–3
- **Spring Security reference** — for Week 15 (`docs.spring.io/spring-security/reference/`)
- **OAuth 2.1 spec** + **OWASP JWT Cheat Sheet** — for Day 73

### Engineering blogs (Architecture Judgment track)
Read 1 deeply per week. Take notes on *why* they chose what they chose.
- Netflix Tech Blog
- Uber Engineering (H3, Schemaless, DOMA, Cadence)
- Discord Engineering (5M concurrent, trillion messages, Elixir/Rust posts)
- Stripe (API design, idempotency, Sorbet)
- Cloudflare (Workers, edge compute)
- AWS Builders' Library
- High Scalability blog
- ByteByteGo newsletter

### Distributed systems papers (Phase 3)
Read at least 4 in full, skim others:
- **Dynamo** (Amazon, 2007) — eventual consistency, gossip, vector clocks
- **Bigtable** (Google, 2006) — wide-column store
- **Spanner** (Google, 2012) — globally distributed, TrueTime
- **Raft** (Ongaro & Ousterhout, 2014) — readable consensus
- **MapReduce** (Google, 2004) — skim for mental model
- **The Google File System** (2003) — skim
- **Kafka: A Distributed Messaging System for Log Processing** — Kreps et al

### AWS
- Stephane Maarek's SAA-C03 course (Udemy) — reference, not start-to-finish
- AWS Well-Architected Framework
- AWS This Week newsletter

### Mocks
- Pramp (free, peer-to-peer)
- interviewing.io (paid, real FAANG engineers — worth it Phase 3 onward)
- Hello Interview (system design specific)
- Exponent (system design + behavioral mocks)

### Behavioral
- Amazon's 16 Leadership Principles — memorize, especially these for Staff:
  - Ownership, Bias for Action, Think Big, Earn Trust, **Are Right A Lot**, Have Backbone Disagree & Commit, Deliver Results, **Hire & Develop the Best**, **Insist on Highest Standards**, **Invent & Simplify**

---

## The Three Portfolio Projects (overview)

**Project 1 (Weeks 5–10): Production-Grade URL Shortener**
Built incrementally. By end: deployed on AWS with monitoring, custom rate limiting, multi-tier caching, custom domain, CI/CD, decisions doc. Containerized for K8s side-project in Phase 3.

**Project 2 (Weeks 9–19): Distributed Event Processing Pipeline — Dual Path (SQS *and* Kafka) with Spring Security + Outbox**
Async ingestion with **two parallel paths**: API Gateway → SQS → Lambda → DynamoDB *and* publishes to Kafka → Spring Boot consumer → Postgres. Idempotency on both paths, JPA depth, connection pool tuning, observability, load testing, cost analysis, SQS-vs-Kafka-vs-Kinesis decision doc, Spring Security on management endpoints, OAuth2 resource server on public API, virtual threads in the consumer, **Outbox pattern for downstream events**.

**Project 3 (Weeks 17–24): Multi-Region Backend Service (production-hardened)**
Spring Boot microservice on ECS/Fargate with Aurora PostgreSQL, multi-region failover via Route 53, full observability (CloudWatch + Micrometer + X-Ray), Resilience4j (circuit breakers/retries/bulkheads), graceful shutdown, comprehensive testing strategy (slice + Testcontainers), runbook, capacity plan.

Detailed specs at the end of this document.

---

## Time allocation by phase

| Phase | Days | DSA | HLD | LLD | Build (AWS) | DS deep | Spring/Auth | Reading/Beh |
|---|---|---|---|---|---|---|---|---|
| 1: Foundation | 1–40 | 60% | 5% | 10% | 15% | — | — | 10% |
| 2: Build | 41–85 | 35% | 20% | 8% | 12% | 5% | 15% | 5% |
| 3: Synthesis | 86–120 | 18% | 30% | 18% | 12% | 12% | 5% | 5% |
| 4: Apply | 121–140 | 15% | 25% | 10% | 5% | 5% | — | 40% (mocks/apply/beh) |

---
---

# PHASE 1: FOUNDATION (Days 1–40, Weeks 1–8)

**Goal:** Build DSA from near-zero. Refresh Java/CS fundamentals. Begin AWS. Draft architecture story bank. Start Project 1.

**Phase 1 unchanged.** No v4 modifications.

---

## Week 1 — Java + Big O + Arrays I

- **Day 1 — DSA-D:** Big O fundamentals (CTCI Ch VI + Abdul Bari video). Analyze 10 snippets. (1h)
  - DSA practice (2h): Two Sum, Valid Anagram, Contains Duplicate in Java.
  - Java refresh (1h): Collections — `ArrayList`, `HashMap`, `HashSet`, `Deque`, `PriorityQueue`. Write usage examples.

- **Day 2 — DSA-D:** Hashmap pattern. Group Anagrams, Top K Frequent Elements (bucket sort). (3h)
  - Java (1h): `equals()` + `hashCode()` contract. Implement a custom-key HashMap.

- **Day 3 — DSA-D:** Product of Array Except Self, Valid Sudoku. (3h)
  - Java (1h): Generics with bounded wildcards. `<T extends Comparable<T>>`, PECS rule.

- **Day 4 — DSA-D:** Encode/Decode Strings, Longest Consecutive Sequence. (3h)
  - Architecture Judgment (1h): **First blog read.** Netflix or Uber post. Write 1-paragraph "What did they decide and why."

- **Day 5 — Review-D:**
  - DSA (1.5h): Re-do 4 random Week 1 problems from scratch, timed.
  - Behavioral (1.5h): Brainstorm 25 candidate stories. Pick top 15. Write 5 in full STAR.
  - Reflection (1h).

---

## Week 2 — Two Pointers + Java Streams

- **Day 6 — DSA-D:** Two pointers intro. Valid Palindrome, Two Sum II. (3h)
  - Java (1h): `Arrays` utility, common pitfalls (`Arrays.asList(int[])`, boxed vs primitive).

- **Day 7 — DSA-D:** 3Sum (milestone — 45-min real effort first). (3h)
  - Reading (1h): CTCI Big O chapter, second pass.

- **Day 8 — DSA-D:** Container With Most Water, Trapping Rain Water. (3h)
  - Java (1h): Streams basics. Solve 3 prior problems using streams. Note when streams *hurt* readability.

- **Day 9 — DSA-D:** Sort Colors (Dutch Flag), Remove Duplicates from Sorted Array. (3h)
  - Architecture Judgment (1h): Discord — "How Discord Stores Billions of Messages." Note their evolution path.

- **Day 10 — Review-D:**
  - DSA (1.5h): Self-mock — 2 unseen mediums, timed.
  - Behavioral (1.5h): Write 5 more STAR stories (10 total). Tag each with 2 Amazon LPs.
  - Reflection (1h).

---

## Week 3 — Sliding Window + OS Fundamentals

- **Day 11 — DSA-D:** Sliding window intro. Best Time to Buy/Sell, Longest Substring Without Repeating Chars. (3h)
  - OS (1h): Process vs Thread. OSTEP Ch 4–5.

- **Day 12 — DSA-D:** Longest Repeating Char Replacement, Permutation in String. (3h)
  - OS (1h): Context switching, scheduling. Understand trade-offs.

- **Day 13 — DSA-D:** Minimum Window Substring (HARD). 45 min real effort. (3h)
  - OS (1h): Java threads — `ExecutorService`, `Future`, `CompletableFuture`. Write a small parallel program.

- **Day 14 — DSA-D:** Sliding Window Maximum (Deque). (3h)
  - OS (1h): Locks, semaphores, monitors. Java `synchronized` semantics.

- **Day 15 — Review-D:**
  - DSA (1.5h): Sliding window template from memory. Re-do 3 problems.
  - Behavioral (1.5h): Practice 3 stories OUT LOUD with audio recording. Refine.
  - Reflection (1h).

---

## Week 4 — Stack + Networking

- **Day 16 — DSA-D:** Valid Parentheses, Min Stack. (3h)
  - Networking (1h): OSI vs TCP/IP model. Why HTTP needs TCP.

- **Day 17 — DSA-D:** Evaluate RPN, Generate Parentheses. (3h)
  - Networking (1h): TCP vs UDP, 3-way handshake. Why TCP for HTTP, why QUIC moved off.

- **Day 18 — DSA-D:** Daily Temperatures, Car Fleet (monotonic stack). (3h)
  - Networking (1h): HTTP/1.1 vs 2 vs 3. What problem did each solve?

- **Day 19 — DSA-D:** Largest Rectangle in Histogram (HARD monotonic stack). (3h)
  - Networking (1h): DNS resolution, TLS handshake. CDN basics.

- **Day 20 — Review-D:**
  - DSA (1.5h): Re-do largest rectangle from scratch. Trapping Rain Water using stack.
  - Architecture Judgment (1h): Stripe API design philosophy — read + dissect.
  - Behavioral (1.5h): 5 more stories (total 15). Practice "Tell me about yourself" 90-sec version.

---

## Week 5 — Recursion + AWS Begins + Project 1 Kickoff

- **Day 21 — DSA-D:** Recursion fundamentals. Factorial, Fibonacci, sum-digits, recursive reverse. Draw call stacks. (3h)
  - Java (1h): How Java stack frames work. StackOverflowError, tail-call (lack of) optimization.

- **Day 22 — DSA-D:** Power(x,n), recursive binary search, recursive string reversal. (3h)
  - AWS intro (1h): Free-tier setup. IAM — non-root user, MFA. Maarek IAM section.

- **Day 23 — DSA-D:** Subsets, Permutations. (3h)
  - AWS (1h): EC2 — launch t2.micro. SSH in. Terminate. S3 — bucket creation, CLI uploads.

- **Day 24 — Build-D: PROJECT 1 KICKOFF.**
  - (4h) Design URL shortener on paper. Requirements, scale, components, data model, alternatives. First "design doc."
  - GitHub repo + README skeleton + IaC intent (SAM or CDK).

- **Day 25 — Review-D:**
  - DSA (1.5h): Recursion review. Re-do 3 problems on paper before keyboard.
  - Behavioral (1.5h): Stories 16–18 (target 18 by Day 40). Re-tag for Staff LPs.
  - Reflection (1h).

---

## Week 6 — Linked Lists + AWS Compute + Project 1 Build

- **Day 26 — DSA-D:** LL basics. Reverse LL (iter + recursive), Merge Two Sorted Lists. (3h)
  - Java (1h): `LinkedList` vs `ArrayList` — when does LL actually win?

- **Day 27 — DSA-D:** Reorder List, Remove Nth Node from End. (3h)
  - AWS (1h): Lambda — first function via console + SAM CLI. API Gateway basics.

- **Day 28 — DSA-D:** LL Cycle (Floyd's). Write the proof on paper. (3h)
  - Java (1h): When you'd use a `Deque` in real code. Spring's use of LinkedList internally.

- **Day 29 — Build-D: PROJECT 1 BUILD.**
  - (4h) Core URL shortener Lambda. API GW → Lambda → DynamoDB. Test E2E. Push to GitHub.

- **Day 30 — Review-D:**
  - DSA (1.5h): LL templates from memory.
  - Architecture Judgment (1h): AWS Builders' Library — retries or timeouts article.
  - Reflection (1.5h): Project 1 progress check. *Why* decisions, not just *what*?

---

## Week 7 — Binary Search + DBMS + Project 1 Continues

- **Day 31 — DSA-D:** Binary search template. Search Insert Position. Write the template 10 times. (3h)
  - DBMS (1h): RDBMS vs NoSQL. ACID (real understanding).

- **Day 32 — DSA-D:** Search in Rotated Sorted Array, Find Min in Rotated. (3h)
  - DBMS (1h): Indexes — B-tree vs Hash. Composite index order.

- **Day 33 — DSA-D:** Search 2D Matrix, Koko Eating Bananas (search on *answer*). (3h)
  - DBMS (1h): Isolation levels. Anomalies (dirty, non-repeatable, phantom).

- **Day 34 — Build-D: PROJECT 1 BUILD.**
  - (4h) CloudWatch metrics, alarms, structured logging. Custom domain + Route 53. Document each decision in README.

- **Day 35 — Review-D:**
  - DSA (1.5h): BS templates from memory. Re-do Koko untimed.
  - LLD prep (1h): SOLID intro.
  - Behavioral (1.5h): "Tell me about a technical decision" with Project 1. Record.

---

## Week 8 — Trees Intro + Java Concurrency + Project 1 Polish

- **Day 36 — DSA-D:** Trees — traversals (pre/in/post). Invert BT, Max Depth. (3h)
  - Java Concurrency (1h): `volatile`, `synchronized`, `Atomic*`. Memory visibility.

- **Day 37 — DSA-D:** Diameter, Balanced BT. (3h)
  - Java Concurrency (1h): `ExecutorService` patterns, `CompletableFuture` chaining.

- **Day 38 — DSA-D:** Same Tree, Subtree of Another Tree, LCA of BST. (3h)
  - AWS (1h): DynamoDB internals — partition key design, hot partitions, GSIs vs LSIs.

- **Day 39 — Build-D: PROJECT 1 v1 COMPLETE.**
  - (4h) Custom rate limiting (token bucket in DDB or Lambda + ElastiCache). CI via GitHub Actions. Write "Decisions & Alternatives" doc.

- **Day 40 — Review-D + PHASE 1 CHECKPOINT.**
  - DSA (1h): Self-mock — fresh medium array problem, 45 min, talk aloud.
  - Project 1 demo (1h): Does README explain *why*, not just *what*?
  - Phase 1 audit (2h):
    - [ ] ~50 LeetCode problems
    - [ ] Comfortable: Big O, hashmap internals, TCP handshake, indexes, ACID, threading basics
    - [ ] Project 1 deployed and documented
    - [ ] 18 STAR stories drafted
    - [ ] 4 engineering blog posts dissected

---
---

# PHASE 2: BUILD (Days 41–85, Weeks 9–17)

**Goal:** Pattern-level DSA. Begin serious HLD. Start LLD track. Project 2 (dual-path SQS + Kafka + Spring Boot consumer). Begin DDIA. Java/Spring depth (JSD-D), Kafka hands-on, modern Spring + Auth + distributed transaction patterns.

**Phase 2 has expanded from 40 days to 45 days** to absorb the new Week 15 (Modern Spring + Auth + Distributed Patterns).

---

## Week 9 — Trees II + HLD Track Begins

- **Day 41 — DSA-D:** Construct Binary Tree from Preorder + Inorder. (3h)
  - Java (1h): Spring Boot internals — `@SpringBootApplication`, auto-configuration mechanics.

- **Day 42 — HLD-D:** **System Design starts here.**
  - HLD (3h): Alex Xu Vol 1 Ch 1 + Ch 2 ("Scale from Zero to Millions", "Back-of-Envelope"). Draw every diagram. 3 estimation problems.
  - DSA review (1h): Re-do 2 tree problems.

- **Day 43 — DSA-D:** Binary Tree Maximum Path Sum (HARD). (3h)
  - DS Reading (1h): "The Tail at Scale" (Dean & Barroso 2013) — short, foundational.

- **Day 44 — Build-D: PROJECT 2 KICKOFF (dual-path design).**
  - (4h) Design event pipeline on paper. Requirements: 10K events/sec, idempotency, retries, dead letters, observability. **Sketch BOTH paths:**
    - **Path A (serverless):** API Gateway → Ingest Lambda → SQS (standard) → Lambda consumer → DynamoDB
    - **Path B (JVM service):** Ingest Lambda also publishes to Kafka topic → Spring Boot consumer → Postgres (RDS) via JPA/Hibernate
  - Identify trade-offs. Create Maven multi-module repo: `producer-lambda`, `consumer-service`, `infrastructure`.

- **Day 45 — Review-D:**
  - DSA (1.5h): Self-mock + post-mortem.
  - HLD (1h): URL shortener at 10x scale from scratch. Compare to Project 1. Where would yours break?
  - Behavioral (1.5h): "Tell me about a system you designed" — Project 1 narrative, refined.

---

## Week 10 — Heap + Load Balancing & Caching

- **Day 46 — DSA-D:** Heap basics. Kth Largest, Last Stone Weight. (3h)
  - Java (1h): `PriorityQueue` internals — heap, custom comparators.

- **Day 47 — HLD-D:**
  - HLD (3h): Load balancers (L4 vs L7), caching strategies (write-through/back/around), eviction (LRU/LFU/ARC). Re-design URL shortener with multi-tier caching.
  - DSA review (1h): K Closest Points to Origin.

- **Day 48 — DSA-D:** Task Scheduler, Design Twitter (heap + design). (3h)
  - DS reading (1h): AWS Builders' Library — caching strategies.

- **Day 49 — Build-D: PROJECT 2 BUILD (both paths scaffolded).**
  - (4h) Implement Path A core: API GW → SQS → Lambda producer → DynamoDB → DDB Stream → Lambda consumer. E2E happy path.
  - **Scaffold the Spring Boot consumer service** alongside: project structure, basic `@KafkaListener` skeleton (wired Day 67), JPA entity stubs, Flyway baseline, Testcontainers test-support module. No real Kafka yet — that's Day 64.

- **Day 50 — Review-D:**
  - DSA (1.5h): Find Median from Data Stream (two-heaps — Google asks this).
  - HLD (1.5h): **Trade-off drill** — URL shortener "Decisions & Alternatives" doc. Each decision → 3 alternatives → why → what changes at 10x.
  - Behavioral (1h): "Have Backbone, Disagree & Commit" — write a story.

---

## Week 11 — Backtracking + DB Sharding & Replication

- **Day 51 — DSA-D:** Backtracking template. Subsets (re-do), Combination Sum. (3h)
  - Java (1h): Spring `@Transactional` preview. Propagation levels. Self-invocation problem. *Full deep dive Day 65.*

- **Day 52 — HLD-D:**
  - HLD (3h): Alex Xu Ch 4 ("Rate Limiter"). Token bucket vs leaky bucket vs sliding window. Distributed rate limiting.
  - DSA review (1h): Permutations, Subsets II.

- **Day 53 — DSA-D:** Combination Sum II, Word Search. (3h)
  - DS reading (1h): Database sharding — range vs hash vs directory. Trade-offs.

- **Day 54 — Build-D: PROJECT 2 BUILD (dual-idempotency).**
  - (4h) Add idempotency on **both paths**:
    - Path A: idempotency keys + DynamoDB conditional writes
    - Path B: idempotency keys + Postgres `UNIQUE` constraint on `(idempotency_key)`
  - Dual implementation = direct comparison ammo. Add DLQs. CloudWatch dashboard (queue depth, latency, error rate).

- **Day 55 — JSD-D #1: N+1 Query Problem + EXPLAIN plans.** *[v3 + small v4 add]*
  - **Setup (30 min):** Project 2's consumer-service entities — `Event`, `EventAttribute` (one-to-many), `EventTag` (many-to-many). Map naively with default fetch types.
  - **Hit the problem (45 min):** "get all events" query. Enable Hibernate SQL logging. Watch the explosion.
  - **Understand (30 min):** Lazy loading semantics. When `@OneToMany(fetch=LAZY)` vs `EAGER` bites.
  - **Fix 3 ways (60 min):** `@EntityGraph`, JPQL `JOIN FETCH`, DTO projection.
  - **EXPLAIN plans (30 min):** Postgres `EXPLAIN (ANALYZE, BUFFERS)`. Read the plan for your queries. Seq scan vs index scan vs bitmap heap scan. *Staff-level expectation.*
  - **Benchmark (30 min):** 1000 events, time each approach.
  - **Write up (15 min):** ADR.
  - **Interview ammo:** "Describe the N+1 problem and how you'd fix it" + "Walk me through reading a Postgres query plan."

---

## Week 12 — Tries + Search & Indexing

- **Day 56 — DSA-D:** Implement Trie from scratch in Java. (3h)
  - LLD intro (1h): SOLID — concrete Java examples per principle.

- **Day 57 — HLD-D:**
  - HLD (3h): Alex Xu Ch — Design Search Autocomplete. Inverted indexes. Skim Elasticsearch architecture (sharding, replication, refresh interval).
  - DSA review (1h): Add and Search Words.

- **Day 58 — DSA-D:** Word Search II (HARD — Trie + backtracking). (3h)
  - LLD (1h): Strategy + Factory with real examples.

- **Day 59 — Build-D: PROJECT 2 BUILD (load test to expose N+1).**
  - (4h) Add load testing with Artillery or k6. Push 10K events/min.
  - **Specifically expose N+1** in the consumer-service `/events` listing endpoint. Watch Hibernate SQL logs explode under load. Apply DTO projection fix from Day 55. Re-run. Measure before/after.
  - Observe failure modes across both paths. Document.

- **Day 60 — JSD-D #2: Connection Pool Tuning.**
  - **HikariCP fundamentals (30 min):** Brett Wooldridge's formula. Why "more is better" is wrong.
  - **Default audit (30 min):** Spring Boot's HikariCP defaults. What you'd change for prod.
  - **Load test (60 min):** k6 against Project 2's consumer. Watch HikariCP metrics. Crash the pool.
  - **Tune (45 min):** Adjust `maximum-pool-size`, `connection-timeout`, `idle-timeout`, `max-lifetime`. Re-run.
  - **Postgres side (30 min):** `max_connections`. PgBouncer overview.
  - **Write up (15 min):** ADR.
  - **Interview ammo:** "How do you size a connection pool?" → math + load test.

---

## Week 13 — Graphs I + Messaging Systems

- **Day 61 — DSA-D:** Graph representations. Number of Islands (DFS). (3h)
  - LLD (1h): Observer + Singleton (and why Singleton is often anti-pattern).

- **Day 62 — HLD-D:**
  - HLD (3h): Alex Xu Vol 2 — Design Chat System. WebSockets, message delivery semantics. *Foreshadows Kafka delivery semantics — Day 69.*
  - DSA review (1h): Clone Graph.

- **Day 63 — DSA-D:** Pacific Atlantic Water Flow (multi-source BFS), Surrounded Regions. (3h)
  - DS reading (1h): Discord — "Two and a Half Million Concurrent Voice Users."

- **Day 64 — Kafka #1: Concepts + Local Setup + Kinesis comparison.** *[v4: added Kinesis]*
  - **Theory (60 min):** Topics, partitions, consumer groups, offsets, log retention, replication factor. Confluent's "Kafka in 100 Seconds" + official intro.
  - **Local setup (45 min):** `docker-compose up` with Kafka + Zookeeper (or KRaft). Verify with `kafka-console-producer`/`consumer`.
  - **Mental model (30 min):** Kafka as distributed commit log, not a queue. Consumers control position, replay is free.
  - **Compare to SQS and Kinesis (45 min):** Three-way mental model. Kinesis shard model, retention defaults (24h default, max 365 days), throughput limits per shard, KCL framework. When AWS users default to Kinesis. *(Full trade-off doc on Day 70.)*

- **Day 65 — JSD-D #3: Transaction Propagation.**
  - **Theory (30 min):** All 7 propagation modes. When each makes sense.
  - **Self-invocation trap (30 min):** Build it — `methodA()` calls `this.methodB()` where B is `@Transactional(REQUIRES_NEW)`. Watch annotation get silently ignored. Spring AOP proxies.
  - **Fixes (45 min):** Self-injection; refactor; AspectJ load-time weaving (mention only).
  - **Exception rollback rules (45 min):** Default unchecked-only. Build a case where checked exceptions silently fail to roll back. Fix with `rollbackFor`.
  - **Read-only optimization (30 min):** `@Transactional(readOnly=true)` — what it actually does.
  - **Apply to Project 2 (30 min):** Service method that needs REQUIRES_NEW for audit logging.
  - **Interview ammo:** "What's tricky about `@Transactional` in Spring?"

---

## Week 14 — Graphs II + Notifications & DDIA Starts

- **Day 66 — DS-D: DDIA officially starts.**
  - DDIA (2.5h): Ch 1 ("Reliable, Scalable, Maintainable") + Ch 2 ("Data Models"). Take notes — these set the vocabulary.
  - DSA (1.5h): Course Schedule (cycle detection). Topo sort intro.

- **Day 67 — DSA-D + Kafka #2: Spring Kafka + Schema Registry intro.** *[v4: added Schema Registry]*
  - DSA (2h): Course Schedule II, Redundant Connection (Union Find intro).
  - **Kafka #2 (2h):**
    - Spring Kafka setup (30 min): `spring-kafka`. `KafkaTemplate`, `@KafkaListener`.
    - Wire the producer to publish events to Kafka alongside SQS path (30 min). Jackson serializer.
    - **Schema Registry intro (45 min):** Why JSON-in-Kafka bites in teams. Confluent Schema Registry purpose. Avro vs Protobuf vs JSON Schema. Backward/forward/full compatibility checks. Read official quickstart — don't deploy Schema Registry locally (overkill for solo project), but understand the model. *Pairs naturally with DDIA Ch 4 on Day 109.*
    - Run E2E (15 min): produce → consume → write to Postgres via JPA. Verify.

- **Day 68 — HLD-D:**
  - HLD (3h): Alex Xu — Notification System. Push notifications (APNs, FCM). Fan-out architectures.
  - DSA review (1h): Number of Connected Components (Union Find).

- **Day 69 — Build-D: PROJECT 2 v1 COMPLETE + Kafka #3: Delivery Semantics.**
  - **Kafka #3 (2.5h):**
    - At-most-once vs at-least-once vs exactly-once (45 min): what each costs.
    - Idempotent producer (30 min): `enable.idempotence=true` — PID + sequence numbers.
    - Transactional consumer (30 min): `isolation.level=read_committed`. For our case, simpler: idempotent processing via Postgres `UNIQUE` constraint — in place from Day 54.
    - Implement (30 min): Project 2 Kafka consumer fully idempotent. Test by replaying messages.
    - Document (15 min): ADR — duplicate handling on both paths.
  - **Project 2 v1 polish (1.5h):** Full README with architecture diagram (both paths), decisions doc, cost report skeleton, load test results. **Public GitHub.** Optional LinkedIn post.

- **Day 70 — Review-D + Kafka #4: SQS vs Kafka vs Kinesis Trade-off Doc.** *[v4: now three-way]*
  - **Kafka #4 (2.5h):**
    - Write the doc (90 min): 3 pages. For Project 2's use case, compare SQS vs Kafka vs Kinesis on: latency, throughput, ordering, replay, ops complexity, cost, vendor lock-in. Pick one as "primary," explain why, document when you'd switch.
    - Self-review (30 min): Pretend senior reviewer. What questions would they ask? Add FAQ.
    - Push to GitHub (30 min): Portfolio.
  - DSA (1h): Word Ladder (BFS on word graph).

---

## Week 15 — Modern Spring + Auth + Distributed Patterns *[NEW IN v4]*

**Theme:** Close the modern Java, auth, and distributed-transaction gaps. Everything here lands directly in Project 2.

- **Day 71 — JSD-D #7: Java 21 Virtual Threads + Modern Features.** *[NEW]*
  - **Virtual threads theory (45 min):** Platform threads vs OS threads vs virtual threads. Mounting/unmounting on carrier threads. Why they exist (high concurrency without async). When NOT to use them (CPU-bound, blocking inside `synchronized` blocks that pin the carrier).
  - **Practical (60 min):** `Thread.ofVirtual().start()`, `Executors.newVirtualThreadPerTaskExecutor()`. **Convert one Project 2 endpoint** that does blocking I/O (e.g., a sync HTTP call to a downstream service) to virtual threads. Measure throughput delta with k6.
  - **Records (30 min):** Apply to Project 2 DTOs — replace lombok'd POJOs where records fit. Note where they don't (mutable state, frameworks needing setters).
  - **Sealed classes + pattern matching for switch (30 min):** Event type hierarchy as a sealed interface. Exhaustive switch over event subtypes. Why this is a huge win for backend domain modeling.
  - **Structured concurrency (preview, 30 min):** `StructuredTaskScope` API. Why it matters (cancellation propagation, scope-bound tasks).
  - **Apply + ADR (30 min):** Document the virtual threads decision for the consumer service. "Why we chose virtual threads for I/O-bound work, why we kept the existing thread pool for CPU-bound paths."
  - **Interview ammo:** "How does Java 21 change concurrency?" / "Where would you NOT use virtual threads?"

- **Day 72 — JSD-D #8: Spring Security Deep Dive.** *[NEW]*
  - **Architecture (45 min):** `SecurityFilterChain`, `AuthenticationManager`, providers, `SecurityContextHolder`. Modern config (no `WebSecurityConfigurerAdapter`, that's Spring Security 5 — Spring Boot 3 uses the lambda DSL).
  - **AuthN flows (45 min):** Form login, HTTP Basic, JWT bearer. Stateful (session) vs stateless. When each makes sense.
  - **Method security (30 min):** `@PreAuthorize`, `@PostAuthorize`, SpEL expressions for fine-grained checks (`hasRole('ADMIN')`, `#user.id == authentication.principal.id`).
  - **Authorization patterns (30 min):** RBAC vs ABAC. Role hierarchies. Custom expression handlers for ABAC.
  - **CSRF + CORS (30 min):** When CSRF protection is needed (stateful sessions) vs not (stateless JWT). CORS config for SPAs.
  - **Apply to Project 2 (60 min):** Secure the Spring Boot consumer service's management/Actuator endpoints. Add a simple admin login (form-based) for ops endpoints.
  - **Interview ammo:** "Walk me through Spring Security's filter chain" / "RBAC vs ABAC, when each?"

- **Day 73 — Auth-D / JSD-D #9: OAuth2 / OIDC / JWT / mTLS.** *[NEW]*
  - **OAuth2 fundamentals (45 min):** Roles (RO, RS, Client, AS). Grant types — Authorization Code (with PKCE), Client Credentials, Device Flow. Why Implicit and Password flows are deprecated.
  - **OIDC vs OAuth2 (30 min):** OIDC adds *identity* via the ID token. OAuth2 is purely *authorization*. When you need each.
  - **JWT structure (45 min):** Header, payload, signature. HS256 (symmetric) vs RS256 (asymmetric). Common pitfalls: **algorithm confusion attack** (don't accept `alg: none`), not validating `aud`/`iss`/`exp`, leaking tokens in logs. OWASP JWT Cheat Sheet.
  - **Spring Boot as OAuth2 resource server (45 min):** `spring-boot-starter-oauth2-resource-server`. Configure JWT validation. **Apply to Project 2's public API path** — protect with a bearer token validated against a (mock) issuer.
  - **mTLS for service-to-service (30 min):** When you reach for it — PCI-DSS, zero-trust networks, service mesh. Certificate rotation challenges (cert-manager, SPIRE).
  - **Token storage + rotation (15 min):** Refresh tokens, sliding expiration, token revocation lists. Why short-lived access tokens matter.
  - **Apply + ADR (30 min):** "Why OAuth2 + JWT for the public API, why Spring Security session-based for admin." Document trade-offs.
  - **Interview ammo:** "How does JWT work end-to-end?" / "When mTLS over JWT?" / "Walk me through OAuth2 authorization code flow with PKCE."

- **Day 74 — DistTx-D: Saga + Outbox + CDC Patterns.** *[NEW]*
  - **The problem (30 min):** Why 2PC doesn't scale across microservices. The dual-write problem (write to DB + publish to Kafka without 2PC). Why "just publish before commit" is wrong (you'll publish events for failed transactions). Why "just publish after commit" is also wrong (the publish might fail).
  - **Saga pattern (60 min):**
    - Choreography vs orchestration
    - Compensating transactions
    - When sagas fail (compensation also fails) — at-least-once compensation, idempotent compensators
    - Canonical example: order → payment → inventory → shipping with compensations at each step
    - When choreography breaks down (visibility, debugging) and you reach for orchestration (e.g., Temporal, Step Functions)
  - **Outbox pattern (60 min):**
    - Outbox table in same transaction as business write
    - Polling-based publisher (simple, latency cost) vs CDC-based publisher (lower latency, ops cost)
    - **Apply to Project 2:** add an `outbox_events` table. Write a `@Scheduled` poller in the consumer service that publishes pending outbox rows to a downstream Kafka topic and marks them sent. This is the practical pattern.
  - **CDC + Debezium (30 min):**
    - How CDC works (logical replication, WAL reading in Postgres)
    - Debezium Postgres connector — high-level setup
    - When to use CDC vs explicit Outbox (CDC if you need to capture ALL changes including direct SQL; Outbox if you want explicit control over what's published)
  - **Document (15 min):** ADR — "Why Outbox over direct publishing" + "When we'd switch to Debezium for CDC."
  - **Interview ammo:** "How do you handle distributed transactions in microservices?" → real answer with code from Project 2. "What's the dual-write problem?" → can explain *and* show your fix.

- **Day 75 — DSA-D: Dijkstra, Shortest Paths + Concurrency LeetCode.** *[NEW]*
  - **Dijkstra (90 min):**
    - Theory: greedy choice, why it fails on negative weights
    - Implementation with PriorityQueue in Java
    - **Network Delay Time** (LC 743)
    - **Path With Minimum Effort** (LC 1631)
  - **Bellman-Ford brief (15 min):** Handle negative weights, single-source. Understand when you'd need it; don't implement.
  - **Cheapest Flights Within K Stops (45 min):** Constrained Dijkstra variant — important for Google.
  - **Concurrency LeetCode (60 min):**
    - **Print in Order** (LC 1114) — semaphores or locks
    - **Building H2O** (LC 1117) — barrier coordination
    - **Web Crawler Multithreaded** (LC 1242) — thread pool design (good prep for Day 102's Web Crawler HLD)
  - **Review (30 min):** What's the strongest signal in a problem statement that says "this is Dijkstra"? (Single source + non-negative weights + shortest path.)

---

## Week 16 — DP 1D + DDIA Ch 3 (Storage)

- **Day 76 — DSA-D:** DP intro. Climbing Stairs, House Robber. Memo vs tabulation. (3h)
  - Java (1h): JVM memory model — heap, stack, metaspace. OOM vs stack overflow.

- **Day 77 — DS-D:**
  - DDIA (2.5h): Ch 3 ("Storage and Retrieval"). LSM trees vs B-trees. **Critical for Staff** — why Cassandra/RocksDB exist.
  - DSA (1.5h): House Robber II, Min Cost Climbing Stairs.

- **Day 78 — DSA-D:** Longest Palindromic Substring (expand-around-center), Palindromic Substrings. (3h)
  - Java (1h): GC fundamentals — generational hypothesis, G1 vs ZGC at a high level. When GC tuning actually matters.

- **Day 79 — HLD-D:**
  - HLD (3h): Design a Key-Value Store (Alex Xu Ch 6). Choose consistency model. Replication strategy. Conflict resolution.
  - DSA review (1h): Decode Ways.

- **Day 80 — JSD-D #4: L1/L2 Cache + Locking.**
  - **L1 cache / Hibernate Session (30 min):** Session-scope cache. Same entity loaded twice in one transaction → second is cached. Demonstrate.
  - **`entityManager.clear()` and `refresh()` (30 min):** When to use each. Batch-processing OOM bug.
  - **L2 cache (45 min):** Ehcache or Caffeine via Hibernate's 2nd-level cache. Pros (cross-transaction). Cons (invalidation in distributed systems).
  - **Optimistic locking (45 min):** `@Version` annotation. `OptimisticLockException`. Retry pattern with backoff. Apply to Project 2.
  - **Pessimistic locking (30 min):** `PESSIMISTIC_WRITE`, `PESSIMISTIC_READ`. High-contention rows, financial. Lock timeout config. Deadlock risks.
  - **Decision framework (30 min):** Optimistic vs pessimistic vs eventual consistency.
  - **Interview ammo:** "How do you handle concurrent updates?"

---

## Week 17 — DP 1D More + LLD Practice + Phase 2 Wrap

- **Day 81 — DSA-D:** Maximum Product Subarray, Word Break. (3h)
  - LLD (1h): Patterns review — Strategy, Observer, Decorator, Factory, Adapter. Map each to a Spring/Java stdlib example.

- **Day 82 — HLD-D:**
  - HLD (3h): Design URL Shortener round 2 — optimize for write-heavy (100K writes/sec). Compare to your Project 1. What breaks?
  - DSA review (1h): LIS (O(n²) version).

- **Day 83 — DSA-D:** LIS O(n log n) (patience sorting). Partition Equal Subset Sum. (3h)
  - DS reading (1h): Dynamo paper — first 4 sections. Take notes.

- **Day 84 — LLD-D:**
  - LLD (3h): Design Splitwise (LLD). Class diagram, key methods, edge cases (currency, multi-party splits, graph optimization).
  - DSA review (1h): Mixed DP review.

- **Day 85 — Review-D + PHASE 2 CHECKPOINT.**
  - DSA (1h): Self-mock — medium DP problem, timed, talk aloud.
  - Phase 2 audit (3h):
    - [ ] ~115 LeetCode problems
    - [ ] 8+ HLD walkthroughs (URL shortener × 2, rate limiter, chat, autocomplete, notifications, KV store, etc.)
    - [ ] Project 1 + Project 2 deployed, public, documented
    - [ ] DDIA Ch 1–3 done
    - [ ] 18+ STAR stories tagged
    - [ ] 8+ engineering blog posts dissected
    - **v3 items (Spring/Kafka pillar):**
    - [ ] Spring Boot consumer service running end-to-end (Kafka → Postgres)
    - [ ] N+1 demonstrated + fixed; ADR written; EXPLAIN plans understood
    - [ ] Connection pool tuning done with load test results
    - [ ] Transaction propagation applied to at least one service method
    - [ ] Kafka producer + consumer with idempotent processing
    - [ ] SQS vs Kafka vs Kinesis trade-off doc published
    - **v4 items (Modern Spring + Auth + DistTx pillar):**
    - [ ] Virtual threads applied to at least one Project 2 endpoint; throughput delta measured
    - [ ] Records + sealed classes used in domain modeling
    - [ ] Spring Security wired on management endpoints
    - [ ] OAuth2 resource server protecting public API path
    - [ ] Outbox pattern implemented in Project 2 with `outbox_events` table + scheduled poller
    - [ ] Dijkstra solved on 3+ problems; concurrency LeetCode (Print in Order, Building H2O, Web Crawler MT) done
    - **Big self-mock:** 75 min — 1 DSA medium + 1 system design (unseen). Brutal critique.

---
---

# PHASE 3: SYNTHESIS (Days 86–120, Weeks 18–24)

**Goal:** Hard DSA. Deep HLD with trade-off drills. Distributed systems papers. LLD mastery. Project 3 (production Spring + testing). Mocks ramp up. Staff-level behavioral. K8s side-project. **Canonical HLD/LLD trio + DDIA encoding/streams gaps** (NEW Week 21).

**Phase 3 expands from 30 days to 35 days** to absorb the new Week 21.

---

## Week 18 — DP 2D + DDIA Replication + Project 3 Kickoff

- **Day 86 — DSA-D:** 2D DP. Unique Paths, Longest Common Subsequence. (3h)
  - LLD (1h): API design fundamentals — REST vs gRPC. When to use which. Versioning strategies.

- **Day 87 — DS-D:**
  - DDIA (2.5h): Ch 5 ("Replication") — single-leader, multi-leader, leaderless. Replication lag. Quorums.
  - DSA review (1.5h): Best Time to Buy/Sell with Cooldown.

- **Day 88 — HLD-D:**
  - HLD (3h): **Trade-off drill** — Design Twitter. Then re-design with constraint: celebrity fan-out (1M followers). Then re-design with constraint: p99 feed load <200ms. *Three iterations.*
  - DSA review (1h): Coin Change II.

- **Day 89 — Build-D: PROJECT 3 KICKOFF (incl. testing strategy ADR draft).**
  - (4h) Design multi-region backend on paper. Pick domain (e.g., feature flag service, metadata API, user preferences). Requirements: <100ms p99 globally, multi-region failover, 99.95% SLA. Sketch architecture.
  - **Draft Testing Strategy ADR** as part of kickoff: test pyramid you'll target, slice annotations where, Testcontainers commitment, what *not* to test. Living doc through Phase 3.

- **Day 90 — LLD-D:**
  - LLD (3h): API design round — Splitwise REST API. Endpoints, request/response shapes, error codes, idempotency, pagination, versioning.
  - DSA review (1h): Target Sum.

---

## Week 19 — DP Hard + DDIA Partitioning + Mocks Begin

- **Day 91 — DSA-D:** Longest Increasing Path in a Matrix (DP + DFS + memo). (3h)
  - Architecture Judgment (1h): Netflix's Hystrix circuit breaker — read & dissect. *(For Project 3 you'll use Resilience4j — patterns transfer directly.)*

- **Day 92 — DS-D:**
  - DDIA (2.5h): Ch 6 ("Partitioning") — by key range, hash, by secondary indexes. Rebalancing.
  - DSA (1.5h): Distinct Subsequences (HARD).

- **Day 93 — Mock-D: FIRST SYSTEM DESIGN MOCK.**
  - Mock (1.5h): Pramp or interviewing.io system design.
  - Post-mortem (1.5h): Full debrief.
  - DSA (1h): Edit Distance.

- **Day 94 — Build-D + JSD-D #5: Testing Strategy + Testcontainers.**
  - **Build-D / Project 3 (1.5h):** IaC (Terraform or CDK). Deploy ECS/Fargate service in one region. Aurora RDS. Basic health endpoint.
  - **JSD-D #5 (2.5h) — applied to Project 3:**
    - Test pyramid (30 min): unit / slice / integration / E2E. Where most tests live.
    - Mockito patterns (30 min): when to mock. "Don't mock what you don't own." `ArgumentCaptor`, `@MockBean` vs `@Mock`.
    - Slice tests (60 min): `@DataJpaTest` with Testcontainers Postgres (NOT H2 — dialect difference = false confidence). `@WebMvcTest` with MockMvc. `@RestClientTest`.
    - Testcontainers setup (30 min): `@Testcontainers`, `PostgreSQLContainer`, `@DynamicPropertySource`.
    - Apply to Project 3 (20 min): test infrastructure. One slice + one integration as templates.
  - **Interview ammo:** "How do you test Spring services?"

- **Day 95 — HLD-D:**
  - HLD (3h): Design Yelp / location search. Geohash, quadtrees. Compare.
  - LLD (1h): API versioning deep — URL vs header vs media-type.

---

## Week 20 — Tries Review + DDIA Transactions + K8s Begins

- **Day 96 — DSA-D + K8s #1: Local cluster + first Pod.**
  - DSA (2.5h): Tries — Word Search II re-do. Accounts Merge (Union Find or DFS).
  - **K8s #1 (1.5h side-work):**
    - Install `kind` — 15 min.
    - Create cluster, deploy nginx Pod, exec into it — 30 min.
    - Mental model: Pod → Node → Cluster, control plane — 30 min.
    - `kubectl` basics — 15 min.

- **Day 97 — DS-D:**
  - DDIA (2.5h): Ch 7 ("Transactions") — isolation levels deep. Snapshot isolation, serializable.
  - DSA (1.5h): Min Cost to Connect All Points (MST + Union Find).

- **Day 98 — HLD-D:**
  - HLD (3h): Design Uber / ride-sharing. Driver-rider matching, ETA, surge. Trade-off drill: offline-first for low-connectivity drivers.
  - DSA review (1h): Burst Balloons (HARD interval DP).

- **Day 99 — Build-D: PROJECT 3 BUILD.**
  - (4h) Add second region. Route 53 failover. Cross-region Aurora replication. Test failover manually.

- **Day 100 — LLD-D:**
  - LLD (3h): Schema design — Uber DB (users, drivers, trips, payments, ratings). Indexes? Partitioning? Audit trail?
  - DSA review (1h): Regular Expression Matching (HARD).

---

## Week 21 — Canonical HLD + LLD + DDIA Encoding/Streams *[NEW IN v4]*

**Theme:** Cover the three most-asked HLD problems that were missing, the three most-asked LLD problems that were missing, and the two DDIA chapters that were missing — plus WebSockets/NIO fundamentals.

- **Day 101 — HLD-D: News Feed (Facebook/Instagram).** *[NEW]*
  - **Requirements + estimation (20 min):** Functional + non-functional. Read-heavy. Estimate fan-out at scale (avg 200 followers, celebs with 100M).
  - **Fan-out on write (push) (45 min):** Writer pushes to followers' feeds at post time. Pros: low read latency. Cons: **celebrity hot-spotting** (Justin Bieber problem), storage amplification (one post × N followers).
  - **Fan-out on read (pull) (30 min):** Reader queries each followed user at feed-load time. Pros: no amplification. Cons: read latency high, expensive for power-followers.
  - **Hybrid (production answer) (30 min):** Push for normal users, pull for celebs. Threshold = follower count. How you'd tune the threshold from metrics.
  - **Ranking layer (20 min):** Chronological → algorithmic ranking. Where ML inference happens (online vs offline). How freshness signals interact with relevance.
  - **Storage (20 min):** Timeline cache (Redis sorted set per user, TTL). Durable store (HBase/Cassandra or DDB). Why a separate cache.
  - **Trade-off iteration (15 min):** Now optimize for "see new content within 5 sec of post." What breaks? What changes?
  - **Connect to Project 2 (10 min):** Your event pipeline IS the fan-out infrastructure. Cite it explicitly when discussing.
  - **Interview ammo:** "Design Facebook News Feed" / "How do you handle the celebrity fan-out problem?"

- **Day 102 — HLD-D: Web Crawler.** *[NEW]*
  - **Requirements + scale (20 min):** 1B pages/month, 10TB raw HTML, **politeness** (don't hammer one host), freshness, dedup.
  - **URL frontier (45 min):**
    - Priority queue (PQ) + per-host queue (politeness layer)
    - Two layers: a back-queue per host ensuring at-most-one-in-flight per host, plus a front-queue ordered by priority
    - **Bloom filter** for "have we seen this URL?" dedup at scale (lossy, but the lossiness is acceptable here)
  - **Crawler workers (30 min):** Horizontal scaling. Politeness enforced via per-host rate limit. `robots.txt` caching (refresh every 24h).
  - **Content storage (30 min):** S3 for raw HTML (cheap, infinite). Metadata (URL, last-crawled, content-hash, status) in DDB or Postgres. Why content-hash deduplication saves storage.
  - **Failure handling (30 min):** Retries with exponential backoff + jitter, DNS failures, dead links, 4xx vs 5xx differentiation. Re-crawl scheduling (priority based on freshness signals — news sites every hour, archives monthly).
  - **Distributed coordination (30 min):** How workers coordinate. Stateless workers + shared queue (SQS or Kafka) is the easy answer. ZooKeeper / leader election if you need master coordination.
  - **Trade-off (15 min):** How would you do real-time crawling (e.g., breaking news) vs scheduled batch crawling? What's the architecture difference?
  - **Interview ammo:** "Design a web crawler" — fluent answer with priority queue layer, politeness, Bloom filter.

- **Day 103 — HLD-D: File Storage (Dropbox / Google Drive).** *[NEW]*
  - **Requirements (20 min):** Upload, sync, share, version, offline. The hard part is the **sync protocol**, not the storage.
  - **Chunking + dedup (45 min):**
    - 4 MB chunks (Dropbox's actual chunk size historically)
    - Content-addressed storage: chunks named by SHA-256 of content
    - **Cross-user dedup:** controversial. Saves storage but has privacy implications (can leak existence of files); some providers do per-user dedup only
  - **Metadata service (30 min):** File → list of chunks mapping. Version history. Postgres or DDB? Metadata is the smart bit — most of the system logic lives here, not in block storage.
  - **Block storage (30 min):** S3 or equivalent for chunks. Tiering for old versions (S3 → S3-IA → Glacier).
  - **Sync protocol (45 min):**
    - Client polls vs server pushes (long-poll vs WebSocket)
    - **Conflict resolution:** Operational Transform (OT) vs CRDTs for collaborative documents; LWW for opaque files
    - Why most file-sync products use LWW for files but more sophisticated approaches (OT/CRDT) for collaborative docs
  - **Mobile / offline (20 min):** Differential sync (only send changed chunks). Local-first design. How to reconcile when reconnecting.
  - **Trade-off (10 min):** How would design change for large video files (>100GB) vs small text docs?
  - **Interview ammo:** "Design Dropbox" — fluent answer with chunking, content-addressed storage, metadata-vs-block separation.

- **Day 104 — DS-D: DDIA Ch 4 + Ch 11 + WebSockets/NIO.** *[NEW]*
  - **DDIA Ch 4: Encoding & Evolution (90 min):**
    - Language-specific encodings (Java serialization) — why they're a trap
    - Text formats (JSON, XML, CSV) — common pitfalls (large numbers in JSON, charset issues)
    - Schema-based binary: Thrift, Protobuf, Avro
    - **Schema evolution** in depth: adding/removing fields, optional vs required, default values
    - Backward vs forward compatibility — definitions matter. *Backward* = new code reads old data. *Forward* = old code reads new data. Most systems need both.
    - When to use each format: gRPC ↔ Protobuf, Kafka ↔ Avro often, REST ↔ JSON
    - **Ties to Schema Registry from Day 67** — now you have the full picture.
  - **DDIA Ch 11: Stream Processing (60 min):**
    - Event streams as the unifying abstraction
    - **Change Data Capture (CDC)** as a stream — directly relevant to Day 74's Debezium discussion
    - Event sourcing as a philosophy (system of record = the log, not the table)
    - Stream-stream joins, stream-table joins (basics)
    - Time semantics: event time vs processing time, watermarks for handling late data
    - Frameworks: Kafka Streams, Flink (mental model only — not implementation)
  - **WebSockets + I/O multiplexing (60 min):**
    - WebSocket handshake (HTTP Upgrade with `Connection: Upgrade`)
    - Frame protocol, ping/pong, close codes
    - Backend implementation: Spring's `@MessageMapping` + STOMP, or raw WS
    - I/O multiplexing: `epoll` (Linux), `kqueue` (BSD/Mac), `IOCP` (Windows). Why one thread can handle 10K+ connections this way.
    - **Why Netty matters** for high-connection servers (Node's I/O model in Java).
    - **C10K problem → C10M problem.** What virtual threads change in this story (Day 71's content now connects).
  - **Interview ammo:** "How does schema evolution work in Kafka?" / "What's the difference between event time and processing time?" / "Why can one Netty thread handle 100K WebSocket connections?"

- **Day 105 — LLD-D: Elevator + Logging Framework + BookMyShow.** *[NEW]*
  - **Elevator system (75 min):**
    - Requirements: N elevators, M floors, scheduling, direction of travel, capacity limits
    - State machines per elevator (IDLE, MOVING_UP, MOVING_DOWN, DOORS_OPEN, MAINTENANCE)
    - Scheduler: **Strategy pattern** — simple (nearest-elevator), SCAN/LOOK algorithm (classic disk-scheduling adaptation), or destination-dispatch (modern, used in high-rises)
    - Class diagram, interfaces, concurrency (multiple elevators, multiple request sources)
    - Edge cases: full elevator skips floors, fire mode (all return to ground), maintenance mode, VIP elevator
    - This is the canonical "design an elevator" question. Practice it cold.
  - **Logging framework (75 min):**
    - Requirements: log levels (TRACE/DEBUG/INFO/WARN/ERROR), multiple sinks (file, console, network, syslog), formatters (plain, JSON, custom), async logging with backpressure
    - **Strategy pattern** for sinks; **Decorator** for formatters; **Chain of Responsibility** for filters; **Singleton** for the LoggerFactory (one of the few legit Singleton uses)
    - Async appender: bounded buffer + worker thread; what happens when the buffer fills (drop, block, error)?
    - This is the "design Log4j/SLF4J" question — classic at Amazon LLD round.
  - **BookMyShow as design exercise (60 min, lighter touch):**
    - Data model: Cinemas, Screens, Shows, Bookings, Seats
    - **Concurrent booking** — the core problem. Pessimistic locking on seats (`SELECT ... FOR UPDATE` on the seat row) vs optimistic locking (`@Version` on the Booking, fail-and-retry).
    - **Two-phase booking** flow: HOLD (5-min temporary lock) → CONFIRM (becomes booking) → expire if not confirmed. This is the real-world pattern.
    - Idempotency: prevent double-bookings under client retry (idempotency key on the booking POST).

---

## Week 22 — Greedy + DDIA Distributed Trouble + K8s #2

- **Day 106 — DSA-D + K8s #2: Deployment + Service + ConfigMap + Secret + Helm intro.** *[v4: added Helm]*
  - DSA (2.5h): Jump Game, Jump Game II, Gas Station (greedy + proof).
  - **K8s #2 (1.5h side-work):**
    - Containerize Project 1 — Dockerfile, push to local registry (or `kind load docker-image`) — 25 min.
    - Write a Deployment manifest (replicas, container spec, resource requests/limits) — 20 min.
    - Write a Service manifest (ClusterIP, NodePort, LoadBalancer — understand the difference) — 15 min.
    - ConfigMap for non-secret config + Secret for DB connection string — 15 min.
    - **Helm basics (15 min):** Why raw YAML doesn't scale (templating, environments, releases). `helm create`, `helm install`, `helm upgrade`. Convert one of your manifests to a tiny Helm chart. Don't go deep — table-stakes only.

- **Day 107 — DS-D:**
  - DDIA (2.5h): Ch 8 ("Trouble with Distributed Systems") — clocks, partial failures. **Foundational for Staff.**
  - DSA (1.5h): Hand of Straights, Insert Interval.

- **Day 108 — Mock-D: BEHAVIORAL MOCK.**
  - Mock (1.5h): Behavioral mock with friend or interviewing.io. Focus on Staff signals.
  - HLD (1.5h): Design Stock Exchange — order matching, latency criticality. *Teaches end-to-end latency budgets.*
  - DSA (1h): Merge Intervals, Non-overlapping Intervals.

- **Day 109 — Build-D + JSD-D #6: Production Spring Boot.**
  - **Build-D / Project 3 (1h):** Observability scaffolding — CloudWatch + X-Ray traces wired up.
  - **JSD-D #6 (3h) — applied to Project 3:**
    - Actuator deep (45 min): default endpoints. Custom `HealthIndicator`s (DB health, downstream health, disk, business signal).
    - Micrometer custom metrics (60 min): Counters, Gauges, Timers, DistributionSummary. Tag strategies — high cardinality is a trap. Wire to CloudWatch via `micrometer-registry-cloudwatch2`. Build the dashboard.
    - Graceful shutdown (30 min): `server.shutdown=graceful` + `spring.lifecycle.timeout-per-shutdown-phase=30s` + ALB pre-stop hook.
    - Resilience4j (30 min): Circuit breaker, retries with jitter, bulkheads, timeouts. Decide where each applies.
    - Profiles + config externalization (15 min): `application-{profile}.yml`, Parameter Store / Secrets Manager.
  - **Interview ammo:** "What does production-readiness look like for a Spring Boot service?"

- **Day 110 — HLD-D:**
  - HLD (3h): Design Payment Gateway. Idempotency at every layer. Reconciliation pipeline. Fraud detection async path.
  - DS reading (1h): Stripe's "Idempotency in distributed systems."

---

## Week 23 — Bit + DDIA Consistency + Papers + K8s #3

- **Day 111 — DSA-D + K8s #3: HPA + Resource Limits + Observability.**
  - DSA (2.5h): Bit manipulation. Reverse Bits, Missing Number (XOR), Sum of Two Integers without `+`.
  - **K8s #3 (1.5h side-work):**
    - Add resource requests + limits. Watch what happens with bad values — 30 min.
    - Install metrics-server. Create HPA — 30 min.
    - Generate load (`hey` or `k6`), watch pods scale — 30 min.

- **Day 112 — DS-D: DDIA Ch 9 + CAP/PACELC explicit framing.** *[v4: added CAP/PACELC]*
  - DDIA (1.5h): Ch 9 ("Consistency and Consensus") — linearizability, total order broadcast, distributed transactions.
  - **CAP and PACELC (45 min):**
    - CAP: under network partition, you must choose Consistency or Availability. The catch — CAP only describes the partition case, which is rare.
    - **PACELC** (more useful framing): Under Partition: A or C? Else (normal operation): Latency or Consistency? Most systems are forced into a quadrant.
    - Examples: DynamoDB (AP + EL), Spanner (CP + EC), Cassandra (configurable), Postgres (CA in single-region, becomes PA under WAN partition with sync replication)
    - **Why Staff interviews specifically ask "what's wrong with CAP?"** — it ignores the non-partitioned latency-vs-consistency trade-off, which is the more common decision.
  - DS reading (1h): Raft paper — sections 1–6. Short and readable, do it in one sitting.
  - DSA (15 min): Single Number variants.

- **Day 113 — HLD-D:**
  - HLD (3h): Design YouTube. Video upload, encoding pipeline, CDN, view counts at scale. Trade-off: re-design for live streaming.
  - DSA (1h): Pow(x, n) — recursive vs iterative trade-offs.

- **Day 114 — LLD-D:**
  - LLD (3h): Design Chess game (re-do if seen). State, move validation, special rules (castling, en passant). Extend to multiplayer online.
  - DSA review (1h): Happy Number, Detect Squares.

- **Day 115 — Build-D: PROJECT 3 BUILD (runbook + graceful shutdown demo + Resilience4j).**
  - (4h) Production-readiness deliverables landing together:
    - **Runbook** (90 min): deploy, rollback, scaling event, DB failover. Common alerts and playbooks. **Real Staff work.**
    - **Graceful shutdown demo** (60 min): rolling deploy via blue/green or ALB target-group swap. Capture before/after metrics — zero dropped requests. Markdown writeup or short screen recording.
    - **Resilience4j config in code** (60 min): wire circuit breaker + retry + bulkhead around your outbound call. ADR per pattern.
    - **Capacity planning doc** (30 min): current capacity, expected growth, when to add region 3.

---

## Week 24 — Hard Mix + Mocks Heavy + K8s Wrap

- **Day 116 — Mock-D + K8s #4: Production Deploy Simulation.**
  - Mocks (2h): Pramp DSA + system-design mock with different partner. Brief post-mortem.
  - **K8s #4 (2h side-work):**
    - Readiness + liveness probes — 30 min.
    - Rolling update with `kubectl set image` — no downtime — 30 min.
    - Rollback with `kubectl rollout undo` — 15 min.
    - PodDisruptionBudget — 15 min.
    - Basic Ingress (nginx-ingress controller) — 30 min.

- **Day 117 — HLD-D:**
  - HLD (3h): Design Distributed Cache (build your own Redis). Sharding, replication, eviction, consistency. Compare to ElastiCache (and when *not* to).
  - DSA (1h): LFU Cache (hard variant — practice).

- **Day 118 — DSA-D + K8s #5: ECS vs K8s Trade-off Doc.**
  - DSA (2.5h): Design problems — Design Twitter (re-do, faster), LRU Cache (re-do without looking), Insert Delete GetRandom O(1).
  - LLD (30 min): Cache design — sketch your own LRU (no library).
  - **K8s #5 (1h side-work):**
    - 1-page doc comparing Project 3 (ECS/Fargate) with your local K8s deploy of Project 1. Cover: ops complexity, vendor lock-in, learning curve, cost model, ecosystem.
    - Interview ammo: "When would you choose ECS vs EKS?"

- **Day 119 — Build-D: PROJECT 3 v1 COMPLETE.**
  - (4h) Final polish. The Project 3 deliverable set:
    - Architecture doc + diagram
    - Runbook (from Day 115)
    - Capacity plan (from Day 115)
    - SLA doc — target SLOs (p99, availability), measurement strategy
    - ADRs — one per major decision
    - **Testing strategy ADR**
    - **Resilience patterns doc** — Resilience4j config + reasoning
    - **Custom metrics dashboard** export + screenshot
    - **Graceful shutdown demo** writeup
    - Cost analysis
    - Decisions log
  - Push everything public. LinkedIn post.

- **Day 120 — Review-D + PHASE 3 CHECKPOINT.**
  - Self-mock (2h): 60-min HLD on unseen problem ("Design Distributed Job Scheduler") + 30-min LLD design.
  - Phase 3 audit (2h):
    - [ ] ~160 LeetCode problems
    - [ ] 21+ HLD walkthroughs (incl. News Feed, Web Crawler, File Storage)
    - [ ] 11+ LLD designs (incl. Elevator, Logging Framework, BookMyShow)
    - [ ] All 3 portfolio projects public + documented
    - [ ] DDIA: Ch 1–9, plus Ch 4 (Encoding) and Ch 11 (Streams) done
    - [ ] 2+ distributed systems papers read in full
    - [ ] 6+ mock interviews
    - [ ] 20 STAR stories tagged & rehearsed
    - [ ] Project 3's testing strategy ADR written
    - [ ] Testcontainers integrated
    - [ ] Slice tests on controllers/repositories/clients
    - [ ] Custom Actuator + Micrometer metrics in Project 3
    - [ ] Resilience4j configured
    - [ ] Graceful shutdown demonstrated
    - [ ] Project 1 deployed to local K8s with Helm chart
    - [ ] ECS vs K8s trade-off doc written
    - [ ] CAP/PACELC framing fluent

---
---

# PHASE 4: APPLY (Days 121–140, Weeks 25–28)

**Goal:** Heavy mocks. Polish. Start real interviews. Iterate based on feedback.

---

## Week 25 — Resume + Heavy Mocks

- **Day 121:**
  - Resume polish (2h): 3 versions (ATS, FAANG-style, startup-style). Lead each bullet with measurable impact. Reference Project 1/2/3 specifically.
  - LinkedIn (1h): Update, "Open to Work" (recruiter-only). Reach out to 5 referrals for target companies.
  - Behavioral (1h): Memorize all 16 LPs. For each, name your 2 default stories.

- **Day 122 — Mock-D:**
  - Mock (1.5h): interviewing.io DSA (real FAANG engineer).
  - Mock (1.5h): system design.
  - Post-mortem (1h).

- **Day 123 — Company research + Reverse interview questions.** *[v4: reverse questions added]*
  - Company research (2h): For top 5 target companies, read their engineering blogs. Identify tech stack, recent challenges, what they value.
  - Behavioral (1h): "Why this company?" — write 5 versions, one per target.
  - **Reverse interview questions (1h):** Prepare a tiered list of "questions for the interviewer" — they'll ask you at the end of every round. Tiers:
    - **For ICs:** "What does a typical week look like?" "What's the team's biggest tech debt?" "How are technical decisions made — RFC process, ADRs?"
    - **For managers:** "What does success look like in 90 days?" "What's the team's biggest organizational challenge?" "How do you do performance calibration?"
    - **For Staff/Principal interviewers:** "Where do you see architectural direction going for this team?" "What's a technical bet the team is making that you're not sure about?" — these signal you can engage at their level.
    - **Avoid:** generic questions you could've Googled, anything about benefits/comp this early.
  - DSA (skip — replaced with reverse questions prep).

- **Day 124 — Mock-D:**
  - Mock (1.5h): Behavioral mock.
  - Mock (1.5h): system design mock.
  - Apply (1h): 10 applications. Mix dream + safety + warmup.

- **Day 125 — Review-D:**
  - Watch back mock recordings (2h). Note patterns. Top 3 things to fix.
  - Targeted work (2h) on those 3 things.

---

## Week 26 — First Real Interviews

- **Day 126:**
  - Light DSA (1h).
  - Daily HLD pass-through (1h) of a familiar design (rotate through your repertoire).
  - Apply / follow up (2h).

- **Day 127:**
  - Company-specific prep (3h) for next interviewing company. Read every relevant blog post.
  - Behavioral rehearsal (1h) for their LPs / values.

- **Day 128 — Mock-D:**
  - Final hard mock before real interviews (3h with post-mortem).
  - Behavioral polish (1h).

- **Day 129 — REAL INTERVIEW likely.**
  - Pre-interview (1h): Warmup problem, skim notes, breathe.
  - Interview block (varies).
  - Post-mortem (1h): Write *everything*. Each question, your response, what you'd do differently.

- **Day 130:**
  - DSA (1h) reinforcing gaps from real interviews.
  - HLD (1h) variants of what was asked.
  - Behavioral refinement (1h) based on real signals.
  - Apply (1h): Replenish pipeline — keep 15+ active applications.

---

## Week 27 — Active Interviewing

- **Day 131–135: Event-driven days.**

  On **interview days:** 30-min warmup → interview → 1-hr post-mortem → rest. Don't study more.

  On **non-interview days (4h):**
  - 1h DSA (review problems you've struggled with in interviews)
  - 1h HLD (practice variants of what's coming up)
  - 1h company-specific prep
  - 1h behavioral or apply pipeline maintenance

  **Maintain pipeline:** keep 15–20 applications active.

  **Negotiate later:** if an offer arrives, don't accept immediately. Use it as leverage. Decisions made under offer-pressure are usually bad. Standard move: thank them, ask for 1–2 weeks.

---

## Week 28 — Close It Out + Negotiation Deep *[v4: expanded negotiation]*

- **Day 136–140: Final stretch.**

  **Light maintenance only** — 30-min DSA warmup, occasional HLD refresher. **Sleep > studying.** A well-rested brain solves what a tired one can't.

  **Final-round prep** when scheduled — review your "Decisions & Alternatives" docs from Projects 1–3. Walk through Project 2's architecture diagram and Outbox/Saga implementation; walk through Project 3's runbook. These are your interview ammo.

  **Negotiation playbook (the part most candidates botch):**

  - **Comp research:** levels.fyi for total comp data at target levels in your region. Get the **range**, not just the mean. Salary, equity (refresh + sign-on grant), bonus structure, sign-on bonus. *Total comp, not base.*
  - **Walk-away number:** decide before the conversation. The number where you'd genuinely walk. Without one, you'll cave under pressure.
  - **Competing offers:** never lie about them — recruiters call each other and check. But absolutely **use real ones**. "I have an offer from X with total comp at $Y. I'd rather be at your company, but the numbers need to be closer."
  - **The pause:** after they make an offer, **don't accept on the call**. "Thank you — I'm excited. Can I have 24 hours to review with my family?" This isn't stalling, it's standard. Recruiters expect it.
  - **Counter on multiple dimensions:** base, equity, sign-on, start date, vacation, remote flexibility. Don't fixate on base — equity refresh and sign-on are often where they have the most room.
  - **Get it in writing:** verbal offers don't count. Always ask for the written offer letter before resigning anywhere.
  - **The bird-in-hand mistake:** don't accept the first decent offer just because it's tangible. If your pipeline has 3 more loops in flight, finish them.
  - **Recruiter dynamics:** the recruiter is paid to close you, but they're also your advocate inside the company. Be friendly, professional, never combative. They tell hiring managers about your demeanor.
  - **When to walk:** if comp is meaningfully below your walk-away after negotiation, walk politely. "I appreciate the offer; the numbers aren't quite where they need to be for this move. Please keep in touch — I'd love to revisit in 6 months."
  - **The exploding offer trap:** "You have 48 hours" is a negotiation tactic, not a real constraint at FAANG (it does happen at smaller startups). Politely push back: "I'm in late-stage conversations with two other companies — I can give you a decision by [reasonable date]."

  **Decompress between rounds** — walk, eat real food, hydrate.

---
---

# DETAILED PROJECT SPECS

## Project 1: Production-Grade URL Shortener (Weeks 5–10)

**Goal:** Demonstrate you can build *and operate* a real service end-to-end.

**Tech:**
- API Gateway + Lambda (Java) + DynamoDB
- ElastiCache (Redis) for hot URLs
- CloudFront for redirect endpoint
- Custom domain via Route 53 + ACM
- Custom token bucket rate limiting
- CloudWatch dashboards + alarms
- GitHub Actions CI/CD
- AWS SAM or CDK

**Deliverables:**
- Deployed working service
- Public GitHub repo with comprehensive README
- **Decisions & Alternatives doc**: each major decision → 3 alternatives → why → what changes at 10x
- Architecture diagram
- One short blog post or LinkedIn post

**Phase 3 add-on:** containerized + deployed to local `kind` Kubernetes cluster with a Helm chart (Days 96–106) for the ECS-vs-EKS trade-off doc.

**Interview ammo:**
- "Tell me about a system you built" → this
- "Design a URL shortener" → "I built one — here's what I'd change"
- "When ECS vs EKS?" → "I ran the same service on both — here's the trade-off doc"
- "Tell me about a technical decision" → any from this project

---

## Project 2: Distributed Event Processing Pipeline — Dual Path + Security + Outbox (Weeks 9–19)

**Goal:** Demonstrate distributed systems thinking + Java/Spring/JPA depth + Kafka + Spring Security + Outbox pattern. The single most ammunition-rich project in your portfolio.

### Architecture

```
                                                  ┌─── (Spring Security / OAuth2 RS) ───┐
                                                  ▼                                      │
┌─────────────┐                          ┌─────────────────┐
│ API Gateway │ ─────────────────────────►│ Ingest Lambda   │
└─────────────┘                          └────────┬────────┘
                                                  │
                          writes to ───────────────┼─────────► SQS (standard) ──► Lambda consumer ──► DynamoDB
                                                  │
                          publishes to ──────────► Kafka topic ──► Spring Boot consumer ──► Postgres (RDS)
                                                                          │ JPA / Hibernate
                                                                          │ + Virtual Threads (Java 21)
                                                                          │ + Spring Security on mgmt endpoints
                                                                          │
                                                                          ├─► outbox_events table ─► poller ─► downstream Kafka topic
                                                                          │   (Outbox pattern)
                                                                          │
                                                                          └─► (intentional N+1, txn issues,
                                                                                cache scenarios — all fixed
                                                                                in JSD-D sessions)
```

**Two parallel processing paths on purpose:**
- **SQS → Lambda → DynamoDB** — serverless, eventual consistency, AWS-native
- **Kafka → Spring Boot consumer → Postgres** — long-running JVM service, JPA depth, virtual threads, Outbox

### Tech stack

- **Producer side:** Java 21, Spring Boot 3.x, AWS SDK v2
- **AWS:** API Gateway, Lambda, SQS (FIFO + standard), DynamoDB, IAM
- **Kafka:** MSK or local Docker Kafka for dev
- **Consumer side:** Spring Boot 3.x on Fargate, Spring Kafka, Spring Data JPA, Hibernate, HikariCP, Flyway, **Spring Security** (mgmt + OAuth2 resource server on public API), **virtual threads** (`Executors.newVirtualThreadPerTaskExecutor()`) for I/O-bound paths
- **DB:** PostgreSQL on RDS
- **Observability:** CloudWatch + structured logging (logback-spring.xml) + Micrometer

### Intentional problems you'll hit + fix

| Problem | Day | Fix |
|---|---|---|
| N+1 queries | 55, 59 | `@EntityGraph`, `JOIN FETCH`, DTO projections |
| EXPLAIN plan literacy | 55 | Read Postgres `EXPLAIN (ANALYZE, BUFFERS)` |
| Connection pool exhaustion | 60 | HikariCP tuning, Wooldridge formula |
| Transaction propagation bug | 65 | Self-injection or refactor; REQUIRED vs REQUIRES_NEW |
| Kafka at-least-once duplicates | 69 | Idempotency keys + Postgres unique constraint |
| Optimistic lock failures | 80 | `@Version`, retry with backoff |
| L1 cache surprise | 80 | Session-scope cache; `entityManager.clear()` |
| Insecure mgmt endpoints | 72 | Spring Security wiring |
| Public API without auth | 73 | OAuth2 resource server + JWT validation |
| Dual-write to DB + Kafka | 74 | Outbox pattern with scheduled poller |

### Deliverables

- Maven multi-module repo: `producer-lambda`, `consumer-service`, `infrastructure` (public)
- Deployed working pipeline (both paths)
- Spring Boot consumer service deployed and documented
- Architecture diagram showing both paths + Outbox flow
- **Load test report**: throughput, latency distributions, bottlenecks
- **Cost analysis**: $/million events broken down by service, for *both* paths
- **Failure modes doc**: chaos-test results
- **SQS vs Kafka vs Kinesis trade-off doc** (Day 70)
- **JPA decisions doc**: every intentional problem + fix + benchmark
- **Connection pool tuning doc**: math + load test results
- **Security ADR**: Spring Security setup, OAuth2 flow, JWT validation rationale
- **Outbox pattern ADR**: why Outbox over direct publishing, when you'd switch to CDC
- **Virtual threads ADR**: where applied, throughput delta measured, where NOT applied
- ADR set covering: idempotency, duplicate handling, txn boundaries, fetch strategy

### Interview ammo unlocked

- "Design an event-driven system" → "I built one — here are the trade-offs"
- "Tell me about a time you debugged something hard" → chaos-test findings
- "How do you handle failures in distributed systems" → from real experience
- "Tell me about a tricky DB problem" → N+1 or txn propagation, with metrics
- "Kafka consumer crashes mid-batch?" → from real experience, with code
- "When Kafka vs SQS vs Kinesis?" → "Here's the doc I wrote"
- "Connection pool sizing?" → "Here's the math and load test"
- "How do you secure a Spring Boot service?" → mgmt + OAuth2 + JWT validation
- "How does Java 21 change concurrency?" → virtual threads, measured impact
- "Distributed transactions in microservices?" → Outbox pattern with code
- "What's the dual-write problem?" → explain *and* show the fix

---

## Project 3: Multi-Region Backend Service — Production-Hardened (Weeks 18–24)

**Goal:** Demonstrate operational maturity at Staff level. This signals "can lead a team."

### Architecture

- ECS/Fargate running Spring Boot microservice
- Aurora PostgreSQL with cross-region read replicas
- Route 53 health-checked failover between two regions
- ALB, ECR, Terraform or CDK for IaC
- Observability stack: CloudWatch + Micrometer + X-Ray + structured logs
- Blue/green deployment via CodeDeploy or manual ALB target-group swap
- Secrets via AWS Secrets Manager

**Pick a domain:** feature flag service, metadata API, user preferences, leaderboard, or rate-limit service.

### Production Spring depth (JSD-D #6, Day 109)

- **Actuator deep:** custom `HealthIndicator`s; Micrometer business metrics
- **Graceful shutdown:** `server.shutdown=graceful` + ALB pre-stop hook
- **Resilience4j:** circuit breakers, retries with jitter, bulkheads, timeouts
- **Configuration management:** profiles, Parameter Store / Secrets Manager

### Testing strategy (JSD-D #5, Day 94)

- Unit (JUnit 5 + Mockito)
- Slice (`@DataJpaTest` with Testcontainers Postgres, `@WebMvcTest`, `@RestClientTest`)
- Integration (`@SpringBootTest` with Testcontainers Postgres + Kafka)
- Contract (Spring Cloud Contract or OpenAPI-based)
- Pyramid documented as ADR

### Deliverables

- Deployed working service (multi-region), public GitHub
- **Runbook**: deploy, rollback, latency-spike investigation, manual failover, scale-up, alert playbooks
- **Capacity plan**: current capacity, growth, when to add region 3
- **SLA doc**: target SLOs, measurement strategy
- **ADRs**: one per major decision
- **Testing strategy ADR**
- **Resilience patterns doc**: Resilience4j config + reasoning
- **Custom metrics dashboard**: business KPIs via Micrometer → CloudWatch
- **Graceful shutdown demonstration**: rolling deploy with zero dropped requests

### Interview ammo unlocked

- "Make a service multi-region" → from experience
- "Operational excellence" → real runbook + ADRs
- "Design X with HA" → constant reference to your real system
- "Test Spring Boot services" → testing strategy ADR
- "Zero-downtime deploys" → graceful shutdown + blue/green
- "Make a service resilient" → circuit breaker config, with reasoning
- "Know your service is healthy in prod" → custom health indicators + business metrics

---
---

# Engineering Blog Reading List

Read at least one per week throughout Phases 1–3. Take notes on *decisions and trade-offs*.

**Must-reads (rank-ordered for Staff signal):**

1. **Uber Engineering** — "Domain-Oriented Microservice Architecture" — how Uber organizes after microservice fatigue
2. **Discord Engineering** — "How Discord Stores Billions of Messages" — Cassandra journey
3. **Netflix Tech Blog** — "Tuning Tomcat for a High-Throughput, Fail-Fast System"
4. **AWS Builders' Library** — "Timeouts, Retries, and Backoff with Jitter" — foundational
5. **Stripe** — "Designing robust and predictable APIs with idempotency"
6. **Cloudflare** — "How we built rate limiting capable of scaling to millions of domains"
7. **Discord** — "Why Discord is switching from Go to Rust"
8. **Uber** — "H3: Uber's Hexagonal Hierarchical Spatial Index"
9. **Netflix** — "Active-Active for Multi-Regional Resiliency" — what Project 3 references
10. **WhatsApp** — "1 million is so 2011" (Erlang scaling)
11. **Stripe** — "APIs as ladders"
12. **Pinterest** — "Building a real-time user action counting system for ads"

---

# Distributed Systems Papers

Read at least 4 fully. Skim the rest.

1. **Dynamo: Amazon's Highly Available Key-value Store** (2007) — eventual consistency, gossip, vector clocks
2. **The Raft Consensus Algorithm** (2014) — *the* readable consensus paper. Read in full.
3. **Spanner: Google's Globally Distributed Database** (2012) — TrueTime, external consistency
4. **Bigtable: A Distributed Storage System** (2006) — wide column stores
5. **The Tail at Scale** (Dean & Barroso, 2013) — short, foundational. Read in Phase 2.
6. **MapReduce** (2004) — skim for mental model
7. **The Google File System** (2003) — skim
8. **Kafka: A Distributed Messaging System for Log Processing** — Kreps et al

---

# Staff-Level Behavioral Story Bank

You need **20 stories** by Day 85.

**Category A — Technical Direction (4)**
- A time you set technical direction for a team/project
- A technical strategy you proposed and drove
- A technology bet you made (right or wrong)
- A time you simplified an over-engineered system

**Category B — Influence Without Authority (4)**
- A time you convinced others of an architectural change
- A time you handled a senior engineer disagreeing with you
- A time you negotiated scope with PM/leadership
- A time you raised the technical bar for your team

**Category C — Mentorship & People (3)**
- A specific case where you developed a junior engineer
- A time you gave hard feedback
- A time you helped a struggling teammate

**Category D — Hard Calls (4)**
- A time you said no to a project
- A failure you owned
- A time you took a calculated risk
- A time you had to choose between two bad options

**Category E — Delivery & Ownership (3)**
- A time you owned a project end-to-end
- A time you missed a deadline (and what you did)
- A time you discovered a problem nobody asked you to solve, then fixed it

**Category F — Ambiguity (2)**
- A time you operated with unclear requirements
- A time you defined a problem before solving it

**For each story:**
- 1-line summary
- Full STAR (2.5 min spoken)
- 2 Amazon LPs it maps to
- Specific metrics in Result (not "improved performance" but "reduced p99 from 800ms to 120ms")
- 3 follow-up questions an interviewer might ask + your answers

---

# Trade-off Articulation Cheatsheet

**The single highest-leverage Staff interview skill.** Drill these phrases until they're second nature.

Instead of: *"I would use Kafka."*
Say: *"It depends on the throughput and ordering requirements. For ordered, high-throughput log-like ingestion I'd reach for Kafka. For task-style work with retries and DLQs, I'd use SQS — simpler ops. For change-data-capture from a database, I'd consider Debezium feeding into either. For AWS-native shops with built-in shard-based throughput, Kinesis. Let's pick based on the actual needs — what's the volume and ordering guarantee?"*

**The 3-axis answer template:**
> "There are three things I'd think about: [X], [Y], and [Z]. If we're optimizing for X, then [A]. If Y matters more, [B]. In this case I'd lean toward [C] because [reason from problem statement] — but I'd want to validate that assumption."

**Common axes:**
- Latency vs throughput
- Consistency vs availability (and what kind of consistency)
- Cost vs operational complexity vs performance
- Build vs buy
- Move fast vs build for scale
- Vertical vs horizontal scaling

**Phrases to use:**
- "Let me first clarify the requirements before designing."
- "What's the read/write ratio?"
- "Is this latency-sensitive or throughput-sensitive?"
- "I'd start simple. Here's the simplest thing that could work, and here's when I'd evolve it."
- "I'd validate this assumption with [metric / experiment / load test]."
- "I'd be wrong if [condition] — let me check."

**Phrases to avoid:**
- "Obviously..."
- "Just use X."
- "I would never do Y." (Staff knows there's a case for almost anything.)
- "I'm not sure" *as a closing statement* (fine as an opener, then think out loud)

## Staff signals you've earned through this plan

**JPA / Persistence:**
- "Default fetch type matters — I'd actually pick LAZY for everything and load explicitly via `@EntityGraph` or DTO projection where I need to."
- "For high-contention rows I'd reach for optimistic locking first — let it fail and retry — and only consider pessimistic if the retry rate gets unacceptable."
- "I treat L2 cache as a last resort, not a default — invalidation in distributed systems is one of the harder problems."

**Messaging:**
- "Kafka if I need replay, high throughput, or ordered processing within a partition. SQS for simple work-queue. Kinesis if I'm AWS-locked and shard-based throughput model fits my pattern."
- "Exactly-once in distributed systems is marketing unless you control both producer and consumer with idempotent operations — most of the time you want at-least-once + idempotent processing."

**Production Spring:**
- "Slice tests over `@SpringBootTest` by default — the latter is slow enough to discourage writing tests at all."
- "H2 for tests is a trap — different SQL dialect, false confidence. Testcontainers Postgres is worth the slowness."
- "Graceful shutdown is a deploy-time concern, not just a Spring config — your load balancer also needs to deregister before SIGTERM."

**Modern Java (v4):**
- "Virtual threads are great for I/O-bound work — wrong choice for CPU-bound or when you have a lot of `synchronized` blocks that pin the carrier."
- "I use records for DTOs and sealed interfaces for domain hierarchies — pattern matching makes exhaustive handling enforceable at compile time."

**Auth (v4):**
- "OAuth2 is authorization, OIDC is identity. If your AuthN logic depends on it, you want OIDC. If you just need 'is this caller allowed,' OAuth2 is enough."
- "JWT validation done wrong is worse than no auth. Always validate `aud`, `iss`, `exp`, and refuse `alg: none`."
- "mTLS over JWT when you can't trust the network — service mesh, PCI-DSS, zero-trust environments."

**Distributed Patterns (v4):**
- "2PC doesn't scale across microservices, so we reach for sagas — with the trade-off that compensations have to be idempotent and may themselves fail."
- "The dual-write problem is real — Outbox solves it without introducing 2PC. CDC is Outbox automated, with the added complexity of running Debezium."

**Consistency framing (v4):**
- "CAP only describes partition cases. PACELC is more useful — most decisions are about latency vs consistency in normal operation, not partitions."

**K8s vs ECS:**
- "ECS if I want to ship and the team isn't deep on K8s. EKS if I'm at scale where the K8s ecosystem pays for the ops cost. The decision usually comes down to team expertise, not technology."

---

# Anti-patterns (Staff-specific)

1. **Designing without asking.** Senior engineers solve the problem given. Staff questions the problem first.
2. **"We" everywhere.** At Staff, interviewers want *your* contribution and judgment.
3. **No metrics in results.** "Improved performance" is junior. "Reduced p99 from 800ms to 120ms across 12 services" is Staff.
4. **Picking a tool without trade-off framing.** "I'd use Kafka" → "It depends on..."
5. **Memorizing system designs.** Interviewers can tell. They'll throw a constraint and watch you flounder.
6. **Avoiding ambiguity.** Junior complains; Staff solves.
7. **Reading DDIA without doing system designs.** Book is reference. Designs are curriculum.
8. **Not having opinions.** Staff is hired to have opinions backed by reasoning.

---

# Weekly Tracking Template

| Day | Type | Topics covered | Problems solved | Confidence 1–5 | Notes |
|---|---|---|---|---|---|

**End-of-week reflection:**
- What's the strongest thing I did this week?
- What confused me?
- What pattern keeps coming up that I haven't internalized?
- What story landed well? What didn't?
- One thing to change next week.

---

# Final Notes

This plan is intense but calibrated to the Staff bar.

**On time:** 4 hrs/day × 5 days × 28 weeks = 560 hours. Enough if you do the work in Months 1–2.

**On Projects:** Project 2's dual path (SQS + Kafka + Spring Security + virtual threads + Outbox) is the single most ammunition-rich element of the portfolio. By the end of Phase 2 you'll have written, debugged, load-tested, secured, and tuned a real Java service. Most candidates can only *describe* doing those things; you'll be able to point at code and metrics.

**On DDIA:** Read it. Ch 1–9, plus 4 and 11 added in v4. No shortcut.

**On mocks:** Non-negotiable. The first 2–3 will be brutal. That's the point.

**On lifestyle:** Sleep 7+ hrs, eat decently, move occasionally. If those go, the plan fails. Cut DSA before sleep.

**On scope:** Staff isn't about knowing more facts. It's about *making better decisions under uncertainty*. When in doubt about whether a study task is worth it, ask: *will this make me better at making technical decisions under uncertainty?* If yes, do it.

**On the v4 expansion:** The added topics (modern Java, Spring Security, OAuth2/JWT, Saga/Outbox, canonical HLD/LLD, DDIA Ch 4 + 11) are directly asked at FAANG, Indian product companies, and fintech. The two new weeks aren't padding — they're closing genuine gaps that would otherwise cost offers.

Good luck.

---
---

# Appendix A — Senior IC (L5 / SDE-II / E5) Framing

The main plan targets Staff/Tech-Lead. The same plan also covers the Senior IC bar — Senior IC requires the same skills with less emphasis on cross-team strategy and architectural opinion-having. This appendix captures the Senior IC perspective for readers using the dual-audience daily-notes format.

**Senior IC bar at 6 YOE:**

- **DSA:** Medium-to-Hard LeetCode level. Quality > quantity. ~200 problems done *well* beats 500 done shallowly.
- **System Design:** This is where 6 YOE candidates win or lose offers. Expect 1–2 rounds, including deep dives.
- **Fundamentals:** Used as tiebreakers. Don't be the senior who can't explain TCP handshake or DB indexing.
- **AWS:** For backend roles outside AWS-the-company, "solid working knowledge" is enough — you don't need the SAA cert unless you want it.
- **Behavioral:** At this level, ~30% of the loop. Amazon's Leadership Principles bar is high but not Staff-bar high.

**Senior IC vs Staff differentiators (recap of plan's "Why Staff" table):**

| Signal | Senior (L5) | Staff (L6) |
|---|---|---|
| DSA | Critical | Important, not differentiating |
| HLD | One round | Multiple rounds with deep dives |
| LLD / API | Sometimes | Often a dedicated round |
| Past impact | Nice to have | The hire/no-hire signal |
| Cross-team influence | Some | Required |
| Technical strategy | Not asked | "How would you set direction?" |

If you're targeting Senior IC only, you can de-prioritize the [STAFF]-tagged sections in the daily notes (still recommended to read them for completeness — they make you stronger even at Senior bar).

---

# Appendix B — General Prep Anti-Patterns (apply to both Senior IC and Staff)

The main plan's "Anti-patterns (Staff-specific)" list covers interview-shaped failures (designing without asking, missing metrics, etc.). These are *prep-shaped* failures — process anti-patterns that derail study regardless of target level.

1. **Grinding LeetCode without reviewing.** A problem you solved 2 weeks ago and can't re-solve = unsolved. Spaced repetition matters more than raw volume.
2. **Reading System Design instead of practicing.** You learn it by drawing, not by watching. Books and videos are reference; you become fluent by doing.
3. **Memorizing AWS service names.** Interviewers ask trade-offs (SQS vs Kinesis, RDS vs DynamoDB), not definitions. If your AWS notes are bullet lists, you're studying wrong.
4. **Behavioral on autopilot.** "We" instead of "I", vague impact, no metrics → senior-bar fail before you even reach Staff signal questions.
5. **Skipping fundamentals because they're "boring".** At 6 YOE, a junior-level miss on indexes or TCP is a deal-breaker. The basics are tiebreakers, not throwaways.
6. **Applying too early.** First real interview should come after at least 2 solid mocks. Burning fresh applications on an unprepared self wastes pipeline.

These overlap with but don't replace the plan's Staff-specific anti-patterns; both lists apply.

---

# Appendix C — Daily Hours Breakdown by Phase (operational view)

The main plan's "Time allocation by phase" table gives percentages. This appendix translates to **absolute hours per day** at the 4 hrs/day cadence — more actionable when planning a single study day.

| Phase | DSA | Theory / Java / Fundamentals | System Design (HLD + LLD + DDIA) | AWS / Build | Behavioral / Mocks |
|---|---|---|---|---|---|
| Phase 1 (Days 1–40) | 2.5 h | 1 h | — | 0.5 h (from Day 21) | 15 min |
| Phase 2 (Days 41–85) | 2 h | 0.5 h | 1 h | 0.5 h | — |
| Phase 3 (Days 86–120) | 1.5 h | — | 1.5 h | 0.5 h | 0.5 h |
| Phase 4 (Days 121–140) | 1 h (review) | — | 1 h | — | 1 h + mocks |

Use this when deciding *what* to do on a given study day, especially when the plan's day-type (DSA-D, HLD-D, etc.) leaves room for complementary work.
