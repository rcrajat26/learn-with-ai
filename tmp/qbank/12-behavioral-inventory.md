# 12 — Behavioral Story Inventory (audit, not a quiz)

**What this decides:** the REAL count of interview-usable stories you have at
3–4 YOE — replacing guesswork about which behavioral categories are thin.
There are no L0–L4 levels here; the output is a per-category count plus a
quality rating per story.

**Rule: brutal honesty.** A story you'd have to inflate ("I led..." when you
participated) is worse than no story — interviewers calibrate follow-up
questions to your claimed scope, and inflated stories collapse under the
second follow-up. Count only what you can defend for 5 minutes of drilling.

---

## Step 1 — Story mining (60 min, do this BEFORE looking at categories)

Go through these prompts one by one. For each, write 1–2 lines per incident
that surfaces — project name, what happened, your role. Don't filter for
"impressive" — mundane-but-real beats shiny-but-vague. Target: 20+ raw
incidents in `answers/12-behavioral.md`.

**Fires and failures**
1. A deploy or release that went wrong. What broke, who noticed, what did you do?
2. A bug you caused that reached production. How was it found; what changed after?
3. A time you were on call / first responder for an incident (even informally).
4. A deadline you or your team missed. What happened next?
5. Data: a time something was wrong in the data and had to be fixed live.

**Building and ownership**
6. The piece of work you're most proud of. Why that one?
7. Something you built end-to-end — from ambiguous ask to running in prod.
8. A time you improved something nobody asked you to improve (tooling, tests, docs, a slow query).
9. The gnarliest bug you personally cracked. How did you find it?
10. A migration/upgrade you executed (framework, DB, API version).

**Friction and people**
11. A code-review disagreement — you pushed back or were pushed back on.
12. A time you disagreed with a technical decision and said so. Outcome?
13. A time you were clearly wrong and someone corrected you. What changed?
14. A time you worked with a difficult or unresponsive counterpart (person or team).
15. Hard feedback you RECEIVED. What did you do with it?

**Scope and judgment**
16. A time you had to choose between two imperfect technical options. How did you decide?
17. A time you negotiated scope — cut something, phased something, said "not now."
18. A time requirements were vague and you had to define the problem first.
19. A shortcut/tech-debt decision you made deliberately. Was it right?
20. A time you helped someone else get unstuck — new joiner, intern, teammate (counts even if informal).
21. Anything you did that changed how the TEAM works (a process, a convention, a check in CI).
22. Work of yours that got cancelled or shelved. How did you handle it?

## Step 2 — Categorize (the L4→L5-appropriate grid)

Place each incident in ONE primary category. Required = the minimum for a
credible loop at this level.

| Category | Required | What counts at 3–4 YOE |
|---|---|---|
| **E. Delivery & ownership** | 4–5 | Owned a feature/service end-to-end; unblocked yourself; shipped through obstacles (prompts 6–10) |
| **D. Hard calls & failure** | 3 | Owned a failure with real consequence + what changed; deliberate trade-off decisions (1–5, 16, 19, 22) |
| **F. Ambiguity** | 2 | Defined the problem before solving; operated without clear requirements (17, 18) |
| **B. Influence (team-scale)** | 2 | Changed a teammate's/team's mind with reasoning; productive disagreement (11, 12, 21) |
| **G. Growth & feedback** | 2 | Was wrong, took feedback, visibly changed (13, 15) |
| **C. Helping others** | 1–2 | Onboarding, unsticking, informal mentoring (20) |
| **A. Technical direction (stretch)** | 0–1 | A design YOU drove for your feature/service scope — do not inflate to team/org scope |

## Step 3 — Rate each candidate story (0–3 each, max 12)

- **Specificity:** Can you name the system, the numbers, the timeline? (3 = metrics from memory: "p99 went from 800ms to 200ms", "affected ~2K orders")
- **Your role:** Is YOUR contribution separable from the team's? (3 = clear "I" actions; 0 = story is really "we")
- **Consequence:** Did the outcome matter to anyone (users, money, team velocity)? (3 = stakes you can articulate)
- **Survivability:** Could you answer 3 hostile follow-ups ("why not X?", "what exactly did you do?", "what would you do differently?")? (3 = yes, comfortably)

**Interview-usable = total ≥ 8 AND no dimension at 0.**

## Step 4 — Record the results table

```
Category               | Usable | Raw-but-weak | Empty?
E. Delivery/ownership  |        |              |
D. Hard calls/failure  |        |              |
F. Ambiguity           |        |              |
B. Influence           |        |              |
G. Growth/feedback     |        |              |
C. Helping others      |        |              |
A. Direction (stretch) |        |              |
TOTAL usable           |        |              |
```

## Interpreting (feeds file 13)

- **Total usable ≥ 12, no required category empty** → behavioral gap is
  polish/rehearsal only.
- **8–11 usable** → typical. Gap = development work: strengthen
  raw-but-weak stories (dig up the metrics, reconstruct timelines from old
  PRs/tickets/Slack) before drafting STAR versions.
- **< 8 usable, or D/E under-filled** → material gap. Two remedies to note:
  (a) archaeology — old tickets, PRs, postmortems, 1:1 notes will resurrect
  forgotten incidents; (b) forward-manufacturing — in the months of prep
  runway, deliberately take on-call shifts, run a small migration, onboard
  someone: real stories can still be CREATED before interviews start.
- **Category A empty** → fine at this level; note it only to avoid
  applying to loops that demand it.
