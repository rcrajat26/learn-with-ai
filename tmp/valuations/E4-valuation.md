# Valuation — Easy Paper 4

**Answers:** `tmp/papers/answers/E4-paper.txt` · **Key:** `tmp/papers/easy/paper-4-key.md`
**Score: 14.5 / 20** (21 questions; Q2 code deferred, out of denominator).
Trajectory: 14.5 → 12.5/19 → 14.5 → **14.5** — stable band.
**Two headlines: concurrency verification COMPLETE (2/2), password retest PASSED. One new hole: ACID scored 0.**

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | ArrayList growth | **1** | Mechanism (grow + copy) and pre-sizing rationale right. One constant to fix: `ArrayList` grows **~1.5×**, not 2× (HashMap doubles; the two get conflated). |
| 2 | `[CODE]` char frequencies | **—** | Deferred to end-of-tier code session (list: E2 Q2, E4 Q2). |
| 3 | `static` | **0.5** | The *what* is right (class-level, single copy, no instance needed). The asked *why* went unanswered: a static method has **no `this`** — there is no particular instance whose fields it could read. |
| 4 | Stream predict | **1** | Correct output (1) with exact pipeline reasoning — lowercase → filter → distinct. |
| 5 | Runnable vs Thread, start vs run | **1** | Both halves right, including the hedged guess: `run()` executes synchronously on the current thread; `start()` spawns. **This was a concurrency verification item — passed.** |
| 6 | Garbage collection | **1** | Unreachability, eligibility, and `System.gc()`-is-a-hint all correct. |
| 7 | Profiles | **1** | Profile-overrides-base-when-active is the mark, and you had it. (Note: the properties-vs-yml verbosity contrast wasn't the question — both are just formats; the real distinction is base defaults vs per-environment overrides.) |
| 8 | LAZY vs EAGER | **0.5** | Definitions both right. Defaults unknown — the answer: `@OneToMany`/`@ManyToMany` → LAZY; `@ManyToOne`/`@OneToOne` → EAGER. Worth memorizing: it's a top-3 JPA interview check and the root of half of all N+1 stories. |
| 9 | NULL predict | **0.5** | (b) and the NULL-is-absence reasoning: right. (a) wrong — `WHERE middle_name = NULL` does **not** throw; it runs fine and returns **zero rows** (the comparison evaluates to UNKNOWN for every row, silently). The silence is exactly why it's a dangerous bug. |
| 10 | ACID | **0** | **The paper's big miss.** Correct meanings: **A**tomicity — all of a transaction's changes commit or none do (crash mid-transfer → no half-transfer); **C**onsistency — constraints/invariants hold before and after each transaction; **I**solation — concurrent transactions don't see each other's intermediate state; **D**urability — once committed, survives crashes. Your "atomicity" was actually closer to a data-modeling notion, and "same output every time" isn't consistency. At 3–4 YOE this is a must-know — it underpins every `@Transactional` conversation you'll have. |
| 11 | localhost | **1** | Loopback + machine-locality reasoning accepted. |
| 12 | SSH | **0.5** | Purpose right; auth half missing: password vs **public/private key pair** — keys preferred for automation (no interactive secret, per-key revocation). |
| 13 | Path/query/body | **1** | All three placements right with correct rationale. |
| 14 | SQL injection | **0.5** | Concept sketched (malicious input reaching the WHERE clause), but the question asked to *show* the vulnerable and safe one-liners and the fix never appeared. The safe version is a **`PreparedStatement` with `?` placeholders** — parameters travel as data, never re-parsed as SQL. The mechanism gets a proper retest in medium paper 4. |
| 14b | **Password retest** | **1** | **Retest passed — the E2 misconception is corrected.** Key-compromise flaw identified, hash-and-compare verification described, irreversibility named as the distinguishing property. Refinement for full interview strength: say **salted, deliberately-slow** hashing and name **bcrypt/argon2** — salt defeats rainbow tables, slowness defeats brute force. |
| 15 | DLQ | **0.5** | Monitoring/replay rationale good. The path is off, though: DLQs hold messages that **repeatedly failed PROCESSING** (consumer errors → redelivery → after N attempts, broker moves them), not messages that "couldn't be sent." Second broker-mechanics slip in two papers (E3 Q15 was the other). |
| 16 | In-process vs external cache | **1** | Speed vs shared, and per-instance inconsistency at 4 instances — the core marks. |
| 17 | assertEquals order | **0.5** | No-assertion half: right. The order half is not mere convention: failure messages print **"expected X but was Y"** — swapped arguments produce lying diagnostics and slow every future debugging session. |
| 18 | CI | **0.5** | Definition confused CI with continuous **deployment**: CI = automatically **building and validating** every change as it's pushed (PR checks), saying nothing about deploying. Checks partially right; the standard trio: build/compile, unit+integration tests, lint/static analysis (+ security scan, coverage gate). |
| 19 | Container logs | **1** | CloudWatch destination + logs-die-with-the-container — both marks despite the hedging. The underlying principle to keep: apps write to **stdout/stderr**; the platform ships them. |
| 20 | Health check | **0.5** | Definition fine; callers missing: **load balancer** (stops routing to unhealthy instances) and **orchestrator** (ECS/K8s — restarts failed containers, gates deploys); monitoring/alerting as the third. |

## Section rollup (trend)

| Section | E4 | E3 | E2 | E1 | Read |
|---|---|---|---|---|---|
| DSA | 1/1 | 2/2 | 1/1 | 1.5/2 | Steady; code items pending in the deferred session |
| Java Core | 1.5/2 | 2/2 | 1/2 | 1.5/2 | Good; "why" clauses keep costing halves |
| **Concurrency & JVM** | **2/2** | 1.5/2 | 0.5/2 | 0.5/2 | **0.5 → 0.5 → 1.5 → 2.0: gap closed at easy tier** |
| Spring & JPA | 1.5/2 | 0.5/2 | 2/2 | 1.5/2 | Solid; memorize the fetch defaults |
| **SQL & DB** | **0.5/2** | 1.5/2 | 1/2 | 1/2 | **Weakest section this paper — ACID zero** |
| Networking & OS | 1.5/2 | 0.5/2 | 2/2 | 1.5/2 | Fine; SSH auth vocabulary missing |
| API & Security | 2.5/3 | 1.5/2 | 1/2 | 2/2 | Password misconception CLOSED; injection fix still owed |
| Messaging & Caching | 1.5/2 | 1/2 | 2/2 | 2/2 | Cache side strong; **broker mechanics now a 2-paper pattern** |
| Testing & Craft | 1/2 | 2/2 | 1.5/2 | 1.5/2 | CI-vs-CD confusion new |
| Cloud & DevOps | 1.5/2 | 2/2 | 0.5/2 | 1.5/2 | Concept-level OK; caller/tooling specifics thin |

## Findings → `qbank/13-scoring-and-report.md`

1. **CLOSED: Concurrency (easy tier).** 0.5 → 0.5 → 1.5 → 2.0 across four papers; primer verified twice (E3 heap/stack, E4 start-vs-run). The gaps.md entry moves to "resolved at easy tier — medium tier measures depth" (E5's volatile/thread-states remain as bonus confirmation; medium papers test pools/CAS/deadlock properly).
2. **CLOSED: password-storage misconception.** Retest passed with the property (irreversibility) named. Residual polish: salt + slow + bcrypt/argon2 vocabulary.
3. **NEW GAP (high): ACID unknown.** Two of four properties blank, two misdefined — while `@Transactional` behavior (E3 Q7) is understood operationally. Classic use-it-can't-define-it gap; DB fundamentals are interview tiebreakers at this YOE. Retest added to E5 (Q10b, scenario-framed). Study: 30 minutes, then explain all four aloud against the transfer example.
4. **UPGRADED (medium): broker mechanics now a pattern, not a slip.** E3 (messages-wait-in-broker answered wrong) + E4 (DLQ = "failed to send"). Cache-side answers are consistently strong; the queue side (delivery attempts, redelivery, DLQ path) is shaky. Medium paper 3 Q15 is the depth retest; the qbank 09 ladder will size it precisely.
5. **NEW (small): CI vs CD conflated.** Cheap fix; matters because "what does your CI run?" is a standard screen (and gaps.md already flags deploy-pipeline literacy).
6. **SQL precision thread continues:** `= NULL` "throws" (it silently returns nothing), injection fix absent. Consistent with §2.2's refined shape: concepts present, mechanics imprecise.

## Actions taken with this valuation

- `tmp/gaps.md` §9 — E4 evidence appended: concurrency closed at easy tier, password gap closed, ACID gap added (high), broker-mechanics pattern upgraded, CI/CD noted.
- `tmp/papers/easy/paper-5.md` — **modified**: added Q10b, an ACID retest in scenario form (+ key entry); E5 now 21 questions. (If you'd rather keep E5 untouched, say so and I'll revert — last E5 edit was interrupted, so this one is flagged explicitly.)
- Deferred code list: **E2 Q2 (palindrome), E4 Q2 (char frequencies)**; E5 Q10 joins if left blank. One session at tier end, one answer file.

## Sequencing instruction

Before E5 (~45 min): (1) ACID — learn all four against the bank-transfer example, out loud; (2) fetch defaults — the four association types and their LAZY/EAGER defaults; (3) skim: DLQ path (fail → redeliver → N attempts → DLQ), CI vs CD one-liner, `PreparedStatement` example once. Then E5 closed-book — it's the last easy paper; after it, the deferred code session, then the easy-tier wrap-up and medium-tier entry decision.