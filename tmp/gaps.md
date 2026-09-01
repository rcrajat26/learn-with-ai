# Gap Analysis — Adapting the v4 28-Week Plan for a 3–4 YOE Engineer

**Context:** `faang-staff-prep-v4-28week.md` is calibrated for a 6-YOE backend
engineer targeting Staff/Tech-Lead (L6), with Senior IC (L5) as the fallback
framing (Appendix A). This document identifies what breaks, what's missing,
and what needs rebalancing when the reader is instead a **3–4 YOE engineer
with decent working knowledge** (Java/Spring backend assumed, some AWS
exposure, DSA beginner-to-intermediate).

**Realistic target level at 3–4 YOE:** L4 (SDE-II / E4) to borderline L5
(Senior / E5). L6 is out of reach on tenure signal alone at most FAANGs.
This single fact drives most of the gaps below.

---

## 1. Level-Calibration Gaps (highest impact)

### 1.1 The plan optimizes for the wrong hire/no-hire signal

| Signal | Plan's weighting (Staff) | Reality at L4→L5 |
|---|---|---|
| DSA | Moderate (~160 problems), "not differentiating" | **Primary filter.** At 3–4 YOE, coding rounds carry the most weight — 2–3 coding rounds vs 1 HLD round is typical |
| HLD | Multiple rounds, deep trade-off debate | Usually **one** round, and the bar is "reasonable design with justified choices," not "debate the interviewer" |
| Past architecture impact | "The hire/no-hire signal" | Nice-to-have. Interviewers expect *scope ownership of a feature/service*, not org-level direction |
| Cross-team influence | Required | Not expected; collaboration signals suffice |
| Technical strategy | Asked directly | Not asked |

**Gap:** The plan deliberately caps DSA volume to free time for Staff signals
the 3–4 YOE candidate cannot credibly demonstrate and won't be asked about.

**Fix:** Rebalance time allocation. Target **220–250 problems** instead of
~160. Reclaim hours from: the Architecture Judgment blog track (halve it),
Staff-specific behavioral categories (see §4), and one of the three portfolio
projects (see §5). Keep the DSA *pattern-first* approach — it's the plan's
strongest asset for a DSA-weak reader.

### 1.2 Down-leveling risk is never discussed

**Gap:** The plan's Phase 4 (apply/negotiate) assumes leveling is settled.
At 3–4 YOE the most common bad outcome is an L4 offer when you performed at
L5, or being pipelined at L4 from the start because of YOE screens.

**Fix:** Add to Week 25 (Day 121 resume work):
- How recruiters map YOE → level per company (Google L4 ≈ Amazon SDE-II ≈ Meta E4).
- How to signal L5 scope on a resume with only 3–4 years: lead with a system
  you owned end-to-end, quantified blast radius (users, QPS, revenue), and
  any mentoring/onboarding you did.
- When to accept an L4 offer at a strong company vs hold out for L5
  (usually: take L4 at FAANG if the alternative is L5 at a weak brand —
  the L4→L5 internal promo at 3–4 YOE is a 1.5–2 year path).
- Ask the recruiter directly which level the loop targets *before* the loop.

---

## 2. Assumed-Knowledge Gaps (plan treats as refresher; reader needs first-pass learning)

The plan's 1-hour side-slots assume 6 years of accumulated context. At 3–4
YOE several of these are **first-time learning**, and 1 hour won't hold.

### 2.1 Spring/JPA internals — assumed fluency the reader may not have

The JSD-D track (Days 55, 60, 65, 80, 94, 109) is excellent but assumes the
reader has already *shipped and operated* Spring services for years — it
teaches the *sharp edges* (N+1, propagation traps, pool tuning), not the
foundations under them.

**Missing prerequisite material (add before Day 55, e.g., as 1-h slots in
Weeks 9–11):**
- How Spring DI actually works: bean lifecycle, `@Configuration` vs
  `@Component`, proxy creation (this is *why* the Day 65 self-invocation trap
  exists — the plan explains the trap, not the proxy model behind it, in depth).
- JPA entity lifecycle states (transient/managed/detached/removed) and what
  `persist`/`merge`/`flush` actually do. Day 80's L1-cache material lands
  flat without this.
- What a `PersistenceContext` is. The plan uses the term; a 3–4 YOE who has
  only used Spring Data repositories may never have met it.
- HTTP session vs stateless auth fundamentals — prerequisite for Day 72–73.

### 2.2 SQL fluency (not just DB theory)

**Gap:** The plan covers DBMS *theory* well (indexes, isolation levels,
EXPLAIN plans) but never verifies the reader can *write* non-trivial SQL.
At 3–4 YOE, ORM-only experience is common. Some companies (and most fintech)
include a SQL screen.

**Fix:** Add a recurring 30-min slot (Weeks 7–10): joins, aggregation,
window functions (`ROW_NUMBER`, `RANK`, running totals), `HAVING` vs `WHERE`,
correlated subqueries. LeetCode Database top-50 or pgexercises.com.
Day 55's EXPLAIN work assumes this exists.

### 2.3 OS / Networking depth mismatch

Weeks 3–4 give OS and networking 1 h/day — correct *scope*, but the plan
frames them as refreshers ("Understand trade-offs"). For a 3–4 YOE who
learned this once at university:

**Fix:** Same topics, but lower the bar per session and add a second pass:
- OS: prioritize threads/locks/context-switching (asked) over scheduling
  algorithms (rarely asked). Add: what actually happens on a blocking
  syscall — needed for Day 71 (virtual threads) and Day 104 (epoll/NIO) to
  make sense rather than being memorized.
- Networking: add one hands-on hour — actually run `curl -v`, watch a TLS
  handshake, trace DNS with `dig`. Reading about handshakes doesn't stick.

### 2.4 Concurrency needs more runway

Day 36–37 (1-h slots) + Day 75 (concurrency LeetCode) is thin for a reader
who hasn't debugged real race conditions in production.

**Fix:** Add 2–3 more concurrency LeetCode problems (Dining Philosophers
LC 1226, Bounded Blocking Queue LC 1188) and one hands-on session: write a
racy counter, observe the race, fix with `synchronized`, then `AtomicLong`,
then `LongAdder`, and benchmark. At L4/L5 loops, concurrency questions are
*more* common than at L6 (where design rounds dominate).

---

## 3. Missing Topics (absent from the plan, expected at L4/L5)

### 3.1 Practical engineering-craft signals

Interviewers at the L4/L5 bar probe craft directly; the plan assumes it.

- **Git beyond basics:** interactive rebase, bisect, resolving real
  conflicts, feature-branch hygiene. Occasionally screened; always visible
  in take-homes.
- **Code review skills:** how to review a PR (asked at Meta/Amazon
  behavioral: "tell me about feedback you gave on a design/PR").
- **Debugging/profiling toolchain:** thread dumps (`jstack`), heap dumps +
  MAT, `jcmd`, async-profiler flame graphs, finding a memory leak. The plan
  mentions GC theory (Day 78) but never *using* the tools. "How would you
  debug high CPU on a prod JVM?" is a standard L5 screen for Java candidates.
- **REST API design fundamentals as a first-class topic:** the plan does API
  design at Day 90 (Splitwise API) assuming years of API-building intuition.
  Add a prerequisite hour: resource modeling, status-code discipline,
  pagination patterns (offset vs cursor and why cursor wins), error body
  conventions (RFC 7807), idempotency keys. This *is* the L4/L5 LLD round
  at many companies.

### 3.2 Take-home assignments and pair-programming rounds

**Gap:** The plan preps only for whiteboard-style rounds. At 3–4 YOE
(especially non-FAANG-adjacent companies used as pipeline/warmup), take-homes
and pair-programming rounds are common.

**Fix:** Add one dry run in Phase 3: build a small CRUD service with tests
in a 3-hour timebox, as if submitted for review. Practice narrating while
coding (pairing simulation) during 2–3 mock sessions.

### 3.3 Testing as an interview topic, not just project hygiene

Day 94 covers testing *for the project*. At L4/L5, "how do you test X" comes
up in coding rounds directly — writing table-driven tests live, discussing
what to mock. One extra hour on writing tests *under time pressure* pays off.

### 3.4 Language fluency drills

At 3–4 YOE, hesitation with the standard library reads worse than at 6 YOE
(where design dialogue compensates). Add micro-drills (15 min, 3×/week,
Phases 1–2): `Comparator.comparing` chains, `computeIfAbsent`, stream
`groupingBy`/`partitioningBy`, `TreeMap` floor/ceiling ops, converting
between collections without looking anything up.

---

## 4. Behavioral Gaps (largest structural mismatch)

### 4.1 The story bank asks for stories the reader doesn't have

The 20-story bank (Categories A–F) requires: setting technical direction,
technology bets, raising the team's bar, developing junior engineers, saying
no to projects. A 3–4 YOE engineer typically has **8–12 honest stories**, and
Categories A (Technical Direction) and C (Mentorship) may be nearly empty.
Inflating scope here is the #1 way candidates fail behavioral rounds —
interviewers calibrate follow-ups to claimed scope and the story collapses.

**Fix — replace the category weighting:**

| Category | Plan (Staff) | Adjusted (L4→L5) |
|---|---|---|
| A: Technical direction | 4 | 1 (a design you drove for *your* feature/service) |
| B: Influence w/o authority | 4 | 2 (convincing your team/lead, not the org) |
| C: Mentorship | 3 | 1–2 (onboarding an intern/new hire counts) |
| D: Hard calls | 4 | 3 |
| E: Delivery & ownership | 3 | **5** (this is the L4→L5 differentiator) |
| F: Ambiguity | 2 | 2 |
| **NEW — Growth/learning** | 0 | 2 ("a time you were wrong / got hard feedback and changed") |

Total: ~15 stories, honestly scoped, beats 20 inflated ones.

### 4.2 Depth-over-breadth follow-up prep

At L4/L5 the behavioral risk isn't missing Staff signals — it's **shallow
STAR answers**. Interviewers drill: "what exactly did *you* do," "what was
the alternative," "what would you do differently." The plan's follow-up prep
(3 questions per story) is right; make it 5 for the top-5 stories.

---

## 5. Portfolio / Project Gaps

### 5.1 Three projects is over-scoped for the available signal

For an L4→L5 loop, projects serve one purpose: concrete material for "tell
me about something you built" and design-round credibility. **Two deep
projects beat three stretched ones**, and the reclaimed ~40–60 hours funds
the extra DSA volume (§1.1) and craft topics (§3).

**Recommendation:**
- **Keep Project 1** (URL shortener) — perfect scope, teaches AWS + operations.
- **Keep Project 2** (dual-path pipeline) — the ammunition-rich one; keep in
  full including the Week 15 security/outbox additions.
- **Cut Project 3 to a hardening pass on Project 2** instead of a new
  multi-region service: add Resilience4j, graceful shutdown, runbook,
  capacity notes *to Project 2's consumer service*. Multi-region failover is
  a Staff talking point; at L4/L5 it earns almost nothing per hour spent.
  Keep the K8s side-track (Days 96–118) — container literacy is expected.

### 5.2 IaC assumed

The plan says "IaC (Terraform or CDK)" as a throwaway line (Day 94). At 3–4
YOE the reader may have never written IaC. Add one 2-h intro session (what
state is, plan/apply loop, one module) before it's needed, or explicitly
permit console-first + IaC-later to avoid a Day-94 stall.

---

## 6. System Design Gaps (scope, not content)

The HLD list itself is right — the same canonical questions are asked at L4/L5.
The *bar* differs, and the plan should say so:

- **What L4/L5 rounds actually test:** requirements clarification, sane
  high-level architecture, one or two areas of depth (usually the DB and the
  queue/cache), back-of-envelope math, and honest trade-off statements.
  NOT: multi-constraint re-design iterations, org/cost trade-offs, "how
  would you set direction."
- **Fix:** For each HLD day, do the base design fully but treat the plan's
  "trade-off iteration" third passes (e.g., Day 88's triple Twitter
  iteration) as optional stretch. One iteration done crisply > three done
  vaguely.
- **DDIA:** keep Ch 1–3, 5, 6, 7 as-is (core). Ch 8, 9 (distributed trouble,
  consensus) can be read at summary depth — linearizability/consensus depth
  is L6 signal. Ch 4 + 11 stay (encoding/streams are practical).
- **Papers:** cut from "4 in full" to Raft + Dynamo, skim the rest. Paper
  fluency is Staff currency, not L5.
- **LLD gets MORE weight, not less:** at L4/L5 the LLD/OOP round is often a
  *coding* round (implement a parking lot / LRU / rate limiter in working
  code, not just class diagrams). Add "implement it runnable in 45 min"
  passes for: parking lot, LRU cache, rate limiter, and the Day 105 trio.

---

## 7. Timeline & Pacing Adjustments

- **28 weeks stands** — the DSA-beginner assumption dominates timeline, and
  that's unchanged. Redistribution, not compression.
- Phase-2/3 hours freed by §5.1 and §6 flow to: +60–90 DSA problems, SQL
  drills, JVM debugging session, API-design fundamentals, take-home dry run.
- **Mocks:** unchanged in count, but shift mix toward coding mocks (plan is
  design-mock-heavy): at least 4 coding mocks before first real interview.
- **Applications (Day 124+):** at 3–4 YOE, add mid-tier product companies as
  genuine targets, not just "safety/warmup" — the L5 offer at a strong
  mid-tier often beats L4 FAANG on scope growth, and competing offers are
  the only real negotiation lever at this YOE (levels.fyi comps for L4/E4
  bands, not the plan's Staff bands).

---

## 8. Summary — Top 10 Actions, Priority Order

1. Re-weight DSA up: 220–250 problems; add coding mocks. (§1.1)
2. Rebuild the behavioral bank around Delivery/Ownership + Growth categories;
   ~15 honest stories, kill inflated Staff-scope stories. (§4.1)
3. Cut Project 3 to a Project-2 hardening pass; keep Projects 1–2 full. (§5.1)
4. Add Spring/JPA foundations (proxy model, entity lifecycle,
   PersistenceContext) before the JSD-D sharp-edges track. (§2.1)
5. Add SQL fluency drills, Weeks 7–10. (§2.2)
6. Add JVM debugging/profiling hands-on session (thread dumps, heap dumps,
   flame graphs). (§3.1)
7. Add REST API design fundamentals hour before the LLD/API track. (§3.1)
8. Make LLD problems runnable-code exercises, not diagram-only. (§6)
9. Downgrade DDIA Ch 8–9 and papers to skim; keep the rest. (§6)
10. Add down-leveling awareness + L4/E4 comp research to Phase 4. (§1.2)

**What does NOT change:** pattern-first DSA progression, the Week 15
modern-Java/auth/outbox week (asked at every level), the Kafka track,
Testcontainers/testing discipline, DDIA core chapters, the trade-off
articulation cheatsheet (useful at any level — just deployed with less
debate-posture), and the 5-days-on/2-off cadence.

---

## 9. Diagnostic evidence updates (2026-07-11, after papers E1 + E2)

Evidence-based amendments per the protocol in
`tmp/qbank/13-scoring-and-report.md`. Sources:
`tmp/valuations/E1-valuation.md` (14.5/20), `E2-valuation.md` (12.5/20).

### Escalations

- **§2.4 Concurrency: MEDIUM → CRITICAL.** 0.5/2 on BOTH easy papers;
  thread-share model answered backwards (E1 Q5); thread pools "not aware"
  (E2 Q5); no improvement between papers despite the E1 flag. Remediation
  started: `tmp/primers/concurrency-primer.md` must precede paper E3;
  E3/E4/E5 concurrency questions serve as verification. The plan's Week 3
  OS slots and Day 13/36–37 Java-concurrency hours are NOT sufficient as
  refreshers for this reader — treat as first-time learning with extra
  reps (per §2.4's original recommendation, now confirmed).

### New gaps (not previously anticipated)

- **Security fundamentals misconception (HIGH):** password storage answered
  with reversible public-key encryption + Diffie-Hellman (E2 Q14) — a
  confident wrong mechanism, worse in interviews than a blank. Salted slow
  hashing (bcrypt/argon2) not known. Remediation: OWASP Password Storage
  Cheat Sheet once; retest injected as E4 Q14b. Watch for sibling
  misconceptions when the qbank 08 ladder is taken (encoding vs encryption
  vs hashing).
- **Answer-the-asked-instance habit (MEDIUM, 3 occurrences):** E1 Q9/Q10,
  E2 Q9/Q10/Q20 — correct concept, unanswered specific clause
  (`SELECT *` for "names and salaries"; "beyond spreading" answered with
  spreading). Interview-costly. Standing drill: re-read the question after
  answering, tick each clause.
- ~~Write-it avoidance~~ **WITHDRAWN (2026-08-18):** the E2 code blank was
  a declared policy, not avoidance — candidate defers ALL `[CODE]`
  questions to one end-of-tier session. Valuations mark them "—"
  (unscored, out of denominator) and maintain a deferred list
  (currently: E2 Q2 palindrome). DSA write-fluency judgment is deferred
  until that session — it remains UNMEASURED, not cleared.

### Downgrades / confirmations

- **Cloud/DevOps: real level ≈ L1, not L2.** E1 sampled strengths (1.5/2);
  E2 sampled operational depth (0.5/2 — 12-factor config, LB capabilities).
  Confirms §5.2 (IaC assumed) and extends it: even env-var config rationale
  is thin. The plan's Day 22–23 AWS on-ramp pacing is right; do not
  compress it.
- **SQL (§2.2) partially confirmed, refined:** concepts (GROUP BY/HAVING,
  joins) present — better than self-assessment; defects are in WRITE
  precision (projection lists, alias-in-HAVING portability). Drills should
  be write-the-query reps, not concept review.
- **Spring/JPA + Messaging/Caching consistently strong** at easy tier
  (2/2, 2/2 on E2): no change to §2.1's prerequisite plan yet — the
  proxy-model and entity-lifecycle questions live in the medium tier;
  judgment deferred until M-papers.

### E3 update (2026-07-12, paper E3: 14.5/20)

- **Concurrency: CRITICAL → HIGH (recovering).** Primer verified working:
  Section 3 went 0.5 → 1.5; the E1 heap/stack zero retested clean.
  Outstanding verification: deadlock setup (submitted as an unfilled
  placeholder), E4 start-vs-run/GC, E5 volatile/thread-states. Close the
  gap only after those land ≥1.5 combined.
- **NEW GAP (medium): hands-on Linux tooling.** `top`/`kill`/SIGTERM-vs-
  SIGKILL a flat zero (E3 Q12), consistent with E2's ops-depth dip while
  AWS *concepts* score 2/2. This is keyboard practice, not reading —
  30-minute terminal drill; retested by medium paper 4 Q12 (box triage),
  no paper modification. Reinforces the plan's hands-on bias for
  Weeks 3–4 side-slots (§2.3).
- **NEW (small): `Optional` purpose unknown** (E3 Q8) — feeds the §3.4
  stdlib-drills case; medium paper 4 retests, no paper change needed.
- **Indexing depth (medium):** self-flagged 0.5 — knows "faster + space,"
  missing range/sort/join speedups and write-maintenance cost. Study
  before the medium tier, which measures it properly (composite indexes,
  planner behavior). Confirms §2.2's theory-vs-practice split.
- **Asked-instance pattern: 4th occurrence** (E3 Q7 "what starts").
  New process defect: answer file submitted with an `ADD ANSWER HERE`
  placeholder — pre-submit ritual now: scan for placeholders + tick every
  question clause.
- **Trajectory:** E1 14.5 → E2 12.5 → E3 14.5 with concurrency recovering:
  consistent with "solid base, specific repairable gaps" — no change to
  the overall 28-week rebalancing conclusions yet.

### E4 update (2026-08-18, paper E4: 14.5/20, Q2 deferred)

- **CLOSED (easy tier): concurrency.** Section trajectory 0.5 → 0.5 →
  1.5 → 2.0; primer verified on two distinct retests (heap/stack,
  start-vs-run). Medium tier measures real depth (pools, CAS, deadlock
  code) — §2.4's extra-reps recommendation stands for plan purposes.
- **CLOSED: password-storage misconception.** E4 Q14b retest passed —
  irreversibility named, hash-and-verify described. Residual polish only:
  salt + slow + bcrypt/argon2 vocabulary.
- **NEW GAP (HIGH): ACID unknown.** I and D blank, A and C misdefined
  (E4 Q10) — while `@Transactional` semantics are operationally understood
  (E3 Q7). Use-it-can't-define-it: high interview risk at this YOE.
  Retest added as E5 Q10b (scenario-framed). Plan hook: Week 7 DBMS slots
  (Day 31 "ACID real understanding") must be treated as first-pass
  learning, not refresher.
- **UPGRADED (MEDIUM): broker mechanics — 2-paper pattern.** E3 Q15
  (consumers-down → answered "retry to consumers" instead of
  broker-buffers) + E4 Q15 (DLQ = "failed to send" instead of
  failed-processing-after-N-attempts). Cache-side consistently strong —
  the gap is queue-side delivery mechanics. Medium paper 3 Q15 + qbank 09
  ladder will size it.
- **NEW (small): CI conflated with CD** (E4 Q18) — feeds the existing
  deploy-pipeline-literacy gap; one-liner fix + will surface again in
  medium paper 4 Q5.
- **SQL precision thread:** `= NULL` believed to throw (it silently
  returns zero rows); PreparedStatement fix unknown by name. §2.2 shape
  confirmed again: concepts OK, mechanics imprecise.
- **Trajectory:** 14.5 → 12.5/19 → 14.5 → 14.5. Easy tier is nearly done
  (E5 + deferred code session remain); pattern across 81 scored answers:
  strong conceptual scaffolding, gaps cluster in (a) DB fundamentals,
  (b) mechanics-level precision, (c) hands-on ops tooling — matching and
  sharpening the original §2 assumed-knowledge thesis.

### M5 accidental preview (2026-08-19: medium paper 5 taken in place of easy 5 — 3.5/19)

- **Medium tier confirmed not yet accessible; gap map validated.** Blanks
  map one-to-one to already-flagged items — this is the between-tier
  syllabus: JPA sharp edges (LazyInit, N+1 — §2.1), transactions/isolation
  (lost update + still-pending ACID retest), indexing/pagination mechanics
  (§2.2/E3), broker mechanics (E3+E4 pattern), heap/PriorityQueue
  internals, git recovery tools (revert/reset/reflog), ops depth
  (OOMKilled, alerting), auth flows (plan Week 15 covers). Study these,
  not "everything," before M1.
- **Strength confirmed a tier up: caching design** — full marks on the
  Caffeine/Redis hybrid question including an unprompted staleness caveat.
  Banked strength; pairs with the consistently strong easy-tier cache
  results.
- **NEW (small):** WebSocket vs SSE vs webhook terminology conflated;
  DCL-volatile known as visibility-only (reordering/half-constructed
  story missing); modern Java (sealed, pattern matching, virtual threads,
  text blocks) self-flagged unknown — reinforces Week 15 as first-pass
  learning.
- **M5 is spent as an instrument** (questions + corrections seen). Medium
  tier proceeds with M1–M4; coverage unaffected (topics recur).
- **Process note:** answer-file was mislabeled E5; easy paper 5 (incl.
  ACID retest Q10b) still pending. Folder + header check added to the
  pre-sitting ritual.

### E5 + EASY-TIER WRAP-UP (2026-08-20: E5 = 14/20; tier aggregate ≈ 71%, 99 scored answers)

- **ACID: retest PARTIAL — stays HIGH/open.** Atomicity anchored (E4 0/4
  → E5 correct); Isolation↔Consistency swap persists; Durability
  unmapped. `tmp/primers/fundamentals-primer-2.md` part 1 written (user
  requested a chapter). Next retest: M3 Q10 isolation anomalies.
- **Broker message lifecycle: HIGH — 3 consecutive papers, one systematic
  wrong model** ("broker retries→DLQ regardless of consumers"). Correct
  model (consumers-down → messages wait; DLQ = repeated processing
  failures) is primer-2 part 2. Retests: M1 Q15, M3 Q15. Distinct from
  caching, which is a BANKED STRENGTH (full marks even on the accidental
  medium paper).
- **Concurrency closure carries an asterisk:** volatile/`counter++`
  answered "thread-safe" despite primer-1 §3 — visibility vs atomicity
  regressed. Primer-2 part 4 sharpens it; M1 Q5 is the retest.
- **CORS enforcement inverted** (said server; it's the browser) —
  primer-2 part 3; retest M2 Q14.
- **Asked-instance pattern: ~10 tier-total occurrences, ~2 marks/paper.**
  Cheapest single score lever. Drill unchanged: tick every clause.
- **NEW (mild): confidence miscalibration** — self-flagged answers
  (generics, scaling) scored full; confident ones (volatile, SQS→DLQ)
  were wrong. Interview implication: hedge less on knowledge, verify
  compound claims.
- **Tier verdict vs the original gap thesis:** ~71% at easy tier with
  strong conceptual scaffolding confirms the §1 "decent knowledge"
  premise; the residue clusters precisely where §2 predicted (DB
  fundamentals, mechanics precision, ops tooling) plus two discoveries
  the Q-Bank was built to find (broker lifecycle model, password/CORS
  security models). DSA write-fluency still UNMEASURED — deferred code
  session (E2 Q2, E4 Q2, E5 Q10, M5 Q1) is the gate before medium tier.

### Code session result (2026-08-21: 1/3 — write-fluency MEASURED, gap confirmed HIGH)

- **Widest theory-practice split of the tier:** ~71% on theory vs 0/3
  fully-correct code artifacts. Failure modes: pseudocode instead of code
  (E2 Q2), non-compiling code + unanswered complexity clause (E4 Q2 —
  missing `return`), and **failure to recognize an unprompted aggregation
  problem** (E5 Q10: row-filtered `amount > 10000` where "total per
  customer" required SUM/GROUP BY/HAVING — despite explaining
  WHERE-vs-HAVING correctly in E2). Prompted recall present; unprompted
  problem-shape recognition absent.
- **Upgrades to evidence-backed:** §1.1 (DSA volume/keyboard reps) and
  §2.2 (SQL drills = word-problem reps on pgexercises, not concept
  review). Plan hook: Phase-1 DSA runs exactly as written (no
  compression — the qbank 01 Part A placement question is now answered
  by proxy), and daily 20–30 min compile-and-run reps start immediately.
- **Rules going forward:** code answers must be compiled/run before
  submission; reference lookups marked (the candidate's honest
  `// checked for function name` notes are the right instinct) and
  budgeted to zero by medium tier.
- **Gate before M1:** redo session — isPalindrome (two variants, real
  Java), charFrequencies (compiling, complexity stated), the E5 SQL +
  two fresh word-problem variants, M5 Q1 with its timebox. Medium tier
  opens when all pass; primer-2 + between-tier syllabus run in parallel
  (3–5 days).

### M1 result (2026-08-21: 6.5/19 — taken without the gate/study; hypothesis confirmed)

- **Score matches the unprepped prediction** (M5 preview 3.5 → M1 6.5 vs
  predicted 10–12 *after* study). Misses cluster exactly on unstudied
  material: volatile examples (primer-2 §4 — SECOND miss), delivery
  semantics + cache-aside (blank, "need a chapter"), pagination, test
  doubles, proxy model. The instrument works; further papers before study
  re-measure the known state.
- **§2.1 CONFIRMED at medium tier: Spring proxy model = 0/2** (Q7 blank,
  Q8 wrong-mechanism on self-invocation). This is the highest-leverage
  single study item on the board — it unlocks
  @Transactional/@Cacheable/AOP questions across M2–M4 and the plan's
  Day 55–65 track. The prerequisite-sessions recommendation is now
  evidence-backed, not inferred.
- **Concurrency medium-layer gap distinct from repaired basics:**
  compound-action reasoning (check-then-act on ConcurrentHashMap answered
  "make it async") + volatile examples repeat-miss. qbank 03 ladder
  promoted from measurement to STUDY material.
- **New traps logged** (quick-notes.md created): Integer cache −128..127
  missed; HashMap constants (doubles/0.75/treeify); leftmost-prefix rule
  ((a)-alone judged unusable); Java clients' infinite default timeouts.
- **Strengths at medium tier:** PUT/PATCH/POST idempotency (1/1, with the
  PATCH-array nuance), remove-overload trap (1/1), HashMap rehash-split
  insight. The Java-core spine is holding a tier up.
- **Artifacts:** `tmp/primers/quick-notes.md` (running trap list — user
  requested), `tmp/primers/primer-3.md` (cache-aside, test doubles,
  keyset, delivery semantics, Clock — two were requested chapters).
- **Standing recommendation (stronger):** pause papers ~1 week; run the
  redo gate + primer-2 self-check + primer-3 + proxy-model study; then
  M2. Deferred code list: E2 Q2, E4 Q2, E5 Q10, M5 Q1, M1 Q9 (user will
  batch all medium code).

### M2 result (2026-08-21: 3.0/19 — third unprepped medium; instrument budget nearly spent)

- **No new knowledge findings.** 11 blanks, 6 partials; at least four
  misses (CORS, idempotent consumer, deadlock explanation, stampede
  mitigations) have existing written chapters that named this paper as
  their retest. The measurement now measures study-execution, not
  knowledge. Small positives: thundering herd NAMED, deadlock recognized
  on sight, merge/rebase direction, Dockerfile password spotted.
- **Escalated recommendation → formal program:**
  `tmp/primers/study-plan.md` created — ordered 7–10-day consolidation of
  primers 1–3 + quick-notes + the scattered syllabi, each block with a
  self-check and the M3/M4 questions it unlocks; includes the test-types
  guide the candidate requested (M2 Q17). M3/M4 are the LAST fresh medium
  instruments — hold both behind the program.
- **For the eventual plan rewrite, the meta-finding matters most:** the
  one completed study→verify loop (concurrency: 0.5→2.0) worked; every
  skipped-study measurement flatlined (3.5, 6.5, 3.0). The 28-week plan's
  structure for this reader must enforce study-before-measure gates, not
  just provide material — self-pacing without gates is the observed
  failure mode.
- Deferred code list now: E2 Q2, E4 Q2, E5 Q10, M5 Q1, M1 Q9, M2 Q2.

### Instrument inventory decision (2026-08-21)

- **Kept, full, untouched:** M3 + M4 — the last fresh medium instruments;
  M3 = post-study-plan verification (target ≥10/19), M4 = confirmation.
  Reducing their question count would blind exactly the sections being
  studied.
- **Kept as archive/study material:** all spent papers + keys (E1–E5, M1,
  M2, M5) — valuations cross-reference them and `study-plan.md` cites the
  medium keys as reading sources.
- **Kept one as benchmark:** hard paper 1 + key — a reference for what the
  target bar looks like; not to be taken until the medium tier is passed
  (both M3 and M4 ≥ 14/19).
- **Deleted:** hard papers 2–5 + keys (8 files). Rationale: at the
  measured level they'd return ~0–2/19 for months; by the time the hard
  bar is reachable (plan Phase 3), better instruments exist (mocks, plan
  checkpoints, qbank ladders) and fresh papers can be regenerated on
  demand — holding 4 stale instruments has no value.