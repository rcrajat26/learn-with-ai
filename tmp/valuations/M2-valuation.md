# Valuation — Medium Paper 2

**Answers:** `tmp/papers/answers/M2-paper.txt` · **Key:** `tmp/papers/medium/paper-2-key.md`
**Score: 3.0 / 19** (Q2 code deferred). Medium-tier run so far:
M5-preview 3.5 → M1 6.5 → **M2 3.0**, all without the between-tier study.

## The finding that matters more than any question

Three medium papers have now measured the same unstudied state three
times. M2 produced almost no information we didn't already have — 13 of 19
scored answers were "not aware"-class, and of those, at least four are
topics whose written chapters already exist and were named as this exact
paper's retests:

| M2 question | Score | The chapter that covers it, already written |
|---|---|---|
| Q14 CORS preflight | 0 | primer-2 part 3 (flagged "retest: M2 Q14") |
| Q15 idempotent consumer | 0 | primer-2 part 2 + primer-3 §4 |
| Q5 deadlock explanation | 0.5 | primer-1 §6 (the transfer example, verbatim) |
| Q16 stampede mitigations | 0.5 | E5-wrap syllabus / M2 key (single-flight, jitter) |

This is no longer a knowledge measurement — it's a study-execution
measurement. The instrument budget is also nearly spent: **M3 and M4 are
the only fresh medium papers left.** If they're taken in the same state,
there will be nothing left to verify the study against, and the hard tier
is (correctly, per every data point) far out of reach.

## Per-question (compressed — blanks grouped)

**Scored 0 — blank/unaware (11):** Q1 amortized analysis (empty — possibly
an accidental skip: you answered ArrayList growth fine in E4; if you knew
this one, say so and I'll re-mark), Q3 ConcurrentModificationException,
Q4 erasure/PECS, Q6 ThreadPoolExecutor, Q8 entity states, Q9 NOT-IN-NULL,
Q10 planner reasons, Q11 port exhaustion ("thread pool exhausted" — wrong
mechanism; it's TIME_WAIT ephemeral-port exhaustion, fix = connection
pooling/keep-alive), Q12 TLS goals, Q13 JWT validation, Q17 flaky tests
(your "need a guide on test types" request is noted — see study plan).

**Partial credit (6):**
- **Q5 (0.5):** deadlock recognized on sight — that's primer-1 §6 working
  at recognition level. The missing explanation is two sentences: T1 holds
  A wants B, T2 holds B wants A → circular wait; fix = acquire locks in a
  global order (e.g., lower account id first).
- **Q7 (0.5):** race identified; "synchronized list" fixes only half. The
  second, bigger problem: the pending list is **in-memory state in a
  singleton** — lost on restart/deploy, wrong with >1 instance. Restructure
  = persist the work (DB table / queue), not just lock the list.
- **Q16 (0.5):** thundering herd correctly NAMED — genuinely good. The
  mitigations: TTL jitter, single-flight per-key lock (one loader, others
  wait/serve stale), refresh-ahead.
- **Q18 (0.5):** merge/rebase direction roughly right. Golden rule: never
  rebase shared history; `--force-with-lease` refuses to overwrite commits
  you haven't seen — always prefer it over `--force`.
- **Q19 (0.5):** hardcoded password ✓. "target won't be present" is wrong —
  `mvnw package` creates it. The other three: `openjdk:latest` unpinned,
  `COPY .` before build busts dependency cache, runs as root, single-stage
  ships JDK+sources.
- **Q20 (0.5):** env vars ✓ for config; the missing distinction: secrets
  come from a **secrets manager** injected at runtime (not committed env
  files), and must never appear in git or image layers (`docker history`
  shows ENV values — ties to Q19's finding).

## Actions taken

- `tmp/primers/study-plan.md` — **created: a single ordered pre-M3
  program** consolidating everything already written (primers 1–3,
  quick-notes, the between-tier syllabus scattered across valuations)
  into one checklist with self-checks and the exact M3/M4 questions each
  item unlocks. Includes the test-types guide you requested at Q17.
- `tmp/gaps.md` §9 — M2 evidence appended.
- **No paper modifications** — M3/M4 must stay fresh; they are the last
  clean instruments at this tier.
- Deferred code list: E2 Q2, E4 Q2, E5 Q10, M5 Q1, M1 Q9, **M2 Q2**.

## Recommendation — stated as plainly as I can

Stop taking papers. Not as a judgment — as arithmetic: papers cost a fresh
instrument each and are returning ~zero new findings, while the five
written artifacts (3 primers, quick-notes, study-plan) sit unverified.
The complete loop that worked (concurrency: 0.5 → 0.5 → primer → 1.5 → 2.0)
is: **study → self-check aloud → paper.** Run `study-plan.md` top to
bottom (realistically 7–10 focused days), do the deferred code batch, then
take M3. Target for M3 after the program: 10+/19. If M3 lands there, the
loop is working and M4 becomes the confirmation paper; if it doesn't, the
problem is the study method and we fix that — but either way M3 will have
measured something new.