# 13 — Scoring, Report & gaps.md Enhancement Protocol

Fill this AFTER completing files 01–12. This file turns raw scores into an
evidence-based rewrite of `tmp/gaps.md`.

---

## Step 1 — Aggregate results table

For each topic: level attained (per the ≥50%-per-level rule in 00-README),
the reference level from the healthy 3–4 YOE profile, and the delta.

| # | Topic | Level attained | Reference | Delta | [CORE] checklist items at 0–1 |
|---|---|---|---|---|---|
| 01 | DSA readiness | | L2 (+ Part A placement) | | |
| 02 | Java core | | L3 | | |
| 03 | Concurrency & JVM | | L2 | | |
| 04 | Spring framework | | L3 | | |
| 05 | JPA / persistence | | L3 (if daily-use) | | |
| 06 | SQL & databases | | L3 | | |
| 07 | Networking & OS | | L2 | | |
| 08 | API & web security | | L2–L3 | | |
| 09 | Messaging & caching | | L1–L2 msg / L2 cache | | |
| 10 | Testing & craft | | L3 | | |
| 11 | Cloud/AWS/DevOps | | L2 | | |
| 12 | Behavioral inventory | usable-story count: ___ | ≥ 8 usable | | |

Also record: **DSA Part A placement** (0–5 solved → which compression tier),
and any question where you scored 0 on something you USE DAILY (these are
the highest-value findings — depth illusions).

## Step 2 — Severity classification

Assign each negative delta and each [CORE]-at-0–1 item a severity:

- **CRITICAL** — L0/L1 in a daily-use area (Java, Spring, JPA, SQL, testing),
  or SQL Part A ≤ 2.5, or usable stories < 8. These block interview
  readiness regardless of the plan.
- **HIGH** — one level below reference in any topic; deploy-literacy or
  debugging-methodology zeros (10/Q10, 11/Q5, 03/Q12–13); [CORE] items at 0
  in areas interviews probe directly (password hashing, 401-vs-403,
  prepared statements, thread dumps).
- **MEDIUM** — at reference but with a hollow spot (e.g., L3 Java but
  0 on erasure); clusters of [CORE] items at 1; L4 questions all at 0 in
  otherwise-healthy topics.
- **INFO** — below reference in acceptable-low areas (messaging internals,
  K8s, virtual threads) that the prep plan already teaches from scratch.
  Record but don't add remediation — the plan covers it; just confirm the
  plan's starting floor matches yours.

## Step 3 — Convert findings to gap entries

For every CRITICAL/HIGH/MEDIUM finding, write an entry in this format
(collect them in `answers/13-findings.md` first):

```markdown
### GAP: <short name>
- **Evidence:** <which questions failed — e.g., "04/Q4 proxy model L0, Q6 self-invocation 0">
- **Severity:** CRITICAL | HIGH | MEDIUM
- **Type:** depth-illusion (use daily, can't explain) | unknown-unknown (checklist) | confirmed-anticipated (already in gaps.md) | disproved (gaps.md predicted it; test shows it's fine)
- **Remediation shape:** <what kind of work fixes it: drills / hands-on lab / reading+explain-back / prerequisite session before plan Day N>
- **Plan hook:** <where it attaches to the 28-week plan or gaps.md section>
```

## Step 4 — Three-way merge into gaps.md

Walk `tmp/gaps.md` section by section against your findings:

1. **CONFIRM** — gaps.md predicted it AND the test shows it (e.g., §2.1
   Spring foundations predicted; 04/Q4–Q6 failed). Action: keep, attach the
   evidence line, upgrade/downgrade severity to match the test.
2. **ADD** — the test found it and gaps.md never mentioned it (typical
   candidates: SQL write-fluency vs theory-only, deploy-pipeline literacy,
   debugging methodology, password/secrets hygiene, story-count shortfall
   in a specific category). Action: new subsection with evidence.
3. **DELETE/DOWNGRADE** — gaps.md predicted it but you scored at/above
   reference (e.g., it assumed SQL weakness and you aced Part A). Action:
   remove the remediation or mark "verified — not a gap," and RECLAIM the
   plan-hours it had allocated.

Then update the **Top-10 priority list** in gaps.md: order by
(severity, how early the plan needs it). A CRITICAL Spring-foundations gap
outranks a HIGH networking gap because the plan's JSD-D track hits it at
Day 55.

## Step 5 — Sanity checks before finalizing

- [ ] Every ladder has a recorded level (no "skipped" topics without a reason).
- [ ] Every [CORE] checklist item at 0–1 appears in a finding or was
      consciously waived (say why).
- [ ] At least the top-3 findings have a concrete remediation shape, not
      "study X more."
- [ ] Anything you scored 0 on but DISAGREE with the rubric about — flag for
      discussion instead of silently regrading yourself.
- [ ] The behavioral counts made it into gaps.md §4 as numbers, not vibes.
- [ ] Re-test hooks: for each CRITICAL gap, note which 2–3 questions you'll
      re-attempt after remediation to verify closure.

## Output

The deliverable of this whole exercise is the updated `tmp/gaps.md` +
`answers/13-findings.md`. The 28-week plan then gets adjusted from THAT —
prerequisites inserted, drills added, verified non-gaps reclaimed as hours.
