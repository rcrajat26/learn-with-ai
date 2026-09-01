# Valuation — Easy Paper 1

**Answers:** `tmp/papers/answers/E1-paper.txt` · **Key:** `tmp/papers/easy/paper-1-key.md`
**Score: 14.5 / 20** → band 12–16: solid baseline, review the misses.
Scoring: 1 = matches key's key points · 0.5 = right idea, gap/imprecision · 0 = wrong or blank.

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | Complexities | **1** | All four correct with correct reasoning; the LinkedList aside on (d) is right for insert-at-head. |
| 2 | FIFO/LIFO classes | **0.5** | Queue/stack logic right. Class recall failed: `LinearQueue` doesn't exist. The answer is **`ArrayDeque`** for BOTH (as queue: `offer`/`poll`; as stack: `push`/`pop`). `Stack.class` is legacy — synchronized, discouraged. |
| 3 | `==` vs `equals` | **1** | Correct results, correct pool-vs-heap reasoning. Your parenthetical question: yes — the string pool lives **in the heap since Java 7** (it was in PermGen before). |
| 4 | String immutability | **0.5** | Definition arrives (content at a location never changes), but two gaps: (a) the loop consequence isn't "memory overload" from literals — concatenation results are **ordinary heap objects, not pooled literals**; (b) the real cost is each `+=` copying the entire string → **O(n²)**, fixed with `StringBuilder`. That named fix is what the question was fishing for. |
| 5 | Process vs thread | **0** | Both halves off. A process is a **running instance of a program with its own isolated memory space**; threads are execution units *inside* it. Threads share the **HEAP** (objects, static fields) — each thread has its **own stack**. You answered the sharing exactly backwards; this is a high-frequency interview check. |
| 6 | Race condition | **0.5** | Definition serviceable, example (`result += 1`) correct. Missing the mechanism that makes it non-atomic: it's a **read → modify → write** of three steps, and interleaving between them loses updates. Without the decomposition the answer doesn't survive a follow-up. |
| 7 | DI + constructor injection | **1** | IoC, decoupling, testability, dependencies-resolved-before-bean-creation — all present. |
| 8 | Stereotypes | **0.5** | "Same mechanics, semantic markers" is right as far as it goes. Missing: **`@Repository` additionally enables persistence-exception translation** (DB exceptions → Spring's `DataAccessException`) — the one that isn't purely decorative. |
| 9 | WHERE vs HAVING | **0.5** | Both definitions correct, but the question asked **which runs first** and that went unanswered: WHERE first (row filter), then grouping, then HAVING (aggregate filter). |
| 10 | INNER vs LEFT JOIN | **0.5** | General distinction right (wording rough). But the concrete question — does the orphan `orders` row survive? — was never explicitly answered: **LEFT JOIN keeps it** (orders on the left, customer columns NULL); INNER drops it. In interviews, answer the asked instance, not just the concept. |
| 11 | TCP vs UDP | **1** | Ordering + delivery guarantees, HTTP/TCP and video-calls/UDP. |
| 12 | DNS + A record | **0.5** | DNS half right; A record blank. An **A record maps a hostname → IPv4 address** (AAAA → IPv6, CNAME → another name). Two-minute fix. |
| 13 | 401/403/404 | **1** | All three correct. (Bonus trivia: 401's official name really is "Unauthorized" even though it means *unauthenticated* — your distinction was the right one.) |
| 14 | CRUD mapping | **1** | Complete and correct, including collection vs item and PUT/PATCH. |
| 15 | Why a queue | **1** | Delivery survival across consumer/network trouble + async — both accepted. |
| 16 | Cache / Redis vs Postgres | **1** | In-memory vs disk is the essential point. ("CPU buffer memories" — not really; Redis is ordinary RAM. Don't say that part in an interview.) |
| 17 | Unit vs integration | **0.5** | Unit test and speed reasoning fine. Integration definition inverted: integration tests use **real collaborators** (real DB via Testcontainers, real HTTP servers) — "actual dependencies in mocked format / calls to a mocked entity" describes unit/component tests with test doubles, which is the opposite of the point. |
| 18 | Mocks | **1** | Behavior-mimicking, conditional returns, DB example — accepted. |
| 19 | EC2/S3/RDS | **1** | All three right. |
| 20 | Docker image vs container | **0.5** | Template-vs-running-instance distinction: right. Two corrections: an image is **not "an OS's copy"** — containers share the **host kernel** (that's the entire difference from a VM); an image is an immutable stack of filesystem **layers**. And Docker itself is a containerization platform, not "a service defined by a file" (that's the Dockerfile). |

## Section rollup

| Section | Score | Read |
|---|---|---|
| DSA | 1.5/2 | Concepts solid; Java Collections **class-name recall** is the gap |
| Java Core | 1.5/2 | Pool/equality strong; immutability consequence imprecise |
| **Concurrency & JVM** | **0.5/2** | **Weakest section — confirmed by your own flag** |
| Spring & JPA | 1.5/2 | Conceptually strong |
| SQL & DB | 1/2 | Definitions OK; answers didn't land on the asked specifics |
| Networking & OS | 1.5/2 | TCP fine; DNS record vocabulary missing |
| API & Security | 2/2 | Strongest section |
| Messaging & Caching | 2/2 | Strong |
| Testing & Craft | 1.5/2 | Integration-test concept inverted |
| Cloud & DevOps | 1.5/2 | Working knowledge; precision gaps (kernel sharing) |

## Findings → feed into `qbank/13-scoring-and-report.md`

1. **CONFIRMED GAP (high): Concurrency fundamentals.** 0.5/2 at the *easy* tier + self-declared. Process/thread memory model answered backwards. This confirms gaps.md §2.4 and raises its severity — the medium/hard concurrency sections will score 0 until this is repaired. Remediate before E2: process vs thread, heap-vs-stack sharing, what `synchronized` does, thread lifecycle (~2–3 focused hours).
2. **NEW FINDING (medium): recall-vs-recognition gap in Java Collections.** You reason about the right structure but can't name the class (`ArrayDeque`). This is exactly what the stdlib micro-drills in gaps.md §3.4 fix — they're now confirmed necessary, not speculative.
3. **NEW FINDING (medium): answering the concept instead of the asked instance** (Q9 "which runs first", Q10 "which join keeps it"). Interview-costly habit: correct knowledge, unfinished answers. Drill: re-read the question after answering and check every clause got addressed.
4. **CONFIRMED GAP (medium): SQL/DB self-flagged + imprecise.** Consistent with gaps.md §2.2. E2's write-the-query questions will test whether it's rusty recall or a real writing gap — that distinction decides drill volume.
5. **Misconception log** (correct these once, they're cheap): threads share heap not stack; loop-concatenated strings aren't pooled literals; integration tests use real collaborators; containers share the host kernel; Redis is RAM, not CPU cache.

## Decision on modifying the next papers

**No structural changes made — the remaining papers already do the right thing.** The 5-papers-per-tier design sweeps each topic with different questions, and E2–E5's existing sections directly re-probe today's misses: E2 Q5–6 (thread pools, `synchronized`), E3 Q5 (heap vs stack — a direct retest of your Q5 zero), E3 Q6 (deadlock), E4 Q5 (Runnable/start-vs-run), E5 Q5–6 (volatile, thread states), plus write-the-query SQL in E2/E5. Injecting extra remedial questions now would break the no-overlap design and blur the retest signal.

**One process change instead:** treat E2 as a *verification* paper — study the concurrency micro-list above and the misconception log first (~half a day), then take E2 closed-book. If Section 3 lands 2/2 there, the gap was shallow; if it's ≤1 again after study, we escalate it to CRITICAL in gaps.md and build a dedicated concurrency primer before anything else.
