# 26 — Behavioral & Leadership Interviews

Scope: the non-coding half of a senior/staff loop — how the behavioral round is actually scored, what
a "signal" is in a hiring packet, how to build a story bank that covers the rubric instead of covering
your resume, and how to deliver a story under follow-up pressure without losing the thread.

Every other guide in this set explains a mechanism inside a machine. This one explains a mechanism
inside a *hiring process*, and it is a machine: a rubric, a set of trained interviewers, a written
debrief, and a committee that reads the debrief without ever meeting you. Candidates fail behavioral
rounds not because their careers are thin but because they answer the *question asked* instead of
supplying the *evidence the rubric needs*. Those are different targets.

The three sentences that summarise this whole guide:

1. The interviewer is not judging your story; they are **writing down evidence** and mapping it to
   named competencies. Your job is to make that transcription easy and quotable.
2. Scope of ownership, not seniority of title, is what separates a Senior (L5) verdict from a Staff
   (L6) verdict. Scope shows up in *who else was affected by your decision*.
3. A story without a decision you personally made, a trade-off you personally weighed, and a number
   you personally moved is not a story. It is a project description, and project descriptions score
   "no signal" — the worst possible outcome, worse than a story with a bad outcome.

Related guides: `22-system-design.md` for the design round the behavioral round is often interleaved
with, `24-design-patterns-architecture.md` for the architectural-judgment vocabulary your technical
stories will use, `20-observability-operations.md` for the incident/postmortem material that supplies
the best ownership and failure stories.

---

## 1. What the round actually measures

### 1.1 The pipeline your answer travels through

```text
you speak (2–3 min)
   → interviewer types notes DURING your answer (partial, lossy, verbatim-ish quotes)
   → interviewer asks 2–5 follow-ups to test whether the story is load-bearing
   → within ~24h interviewer writes a debrief: competency ratings + evidence quotes + hire/no-hire
   → hiring committee / bar raiser reads ONLY the debriefs, never meets you
   → decision, plus a level recommendation
```

Four consequences that change how you should speak:

| Stage | Consequence for you |
|---|---|
| Notes typed live | Front-load the headline. If your first 20 seconds are context, the notes start empty. |
| Follow-ups | Depth must be real. A story you cannot go three questions deep on will be marked "shallow / possibly not their work". |
| Written debrief | The interviewer needs *quotable specifics*. "Cut p99 from 2.1 s to 240 ms" survives transcription. "Improved performance a lot" does not. |
| Committee never meets you | Charisma does not transfer through a document. Structure and numbers do. |

**Trap:** optimising for rapport in the room. Warmth helps the interviewer *want* to advocate for you;
it does not give them anything to write. Both matter, but only one is scored.

### 1.2 The rubric shape (near-universal, whatever the company calls it)

Companies differ in vocabulary and identically in structure. Every behavioral rubric is some
partition of these five axes:

| Axis | The question behind it | What "strong" looks like |
|---|---|---|
| **Impact / results** | Did outcomes change because you were there? | Quantified delta, attributed to your action, durable after you left |
| **Ownership / drive** | What do you do when it is nobody's job? | Took on unassigned problems; followed through past the fun part |
| **Judgment / technical direction** | Do you make good calls under uncertainty? | Named the alternatives, stated the trade-off, chose, revisited with data |
| **Collaboration / influence** | Do you make the people around you more effective? | Changed someone's mind with evidence; mentored with a named outcome |
| **Growth / self-awareness** | Do you learn from being wrong? | A real failure, owned in the first person, with a systemic (not personal-resolve) fix |

Named variants you will actually meet:

- **Amazon** — 16 Leadership Principles, one or two per interviewer, explicitly asked for by name; a
  dedicated **Bar Raiser** who is outside the hiring org and can veto.
- **Google** — "Googleyness & Leadership" round; leadership is defined as *emergent* leadership
  (leading without the title), plus role-related knowledge and "general cognitive ability".
- **Meta** — usually two behavioral-heavy rounds framed around *career narrative*: "Tell me about a
  project you're proud of", drilled hard, plus conflict and feedback questions.
- **Microsoft / others** — "as-appropriate" round with the hiring manager, heavily weighted toward
  culture fit and growth mindset.

Learn one rubric properly (Amazon's is the most explicit and therefore the best training set) and the
rest are re-labellings. See § 5 for the mapping.

### 1.3 "Signal" and "no signal"

The interviewer records one of four verdicts per competency:

```text
strong positive  — specific evidence, at or above the level's bar
positive         — evidence present, bar met
no signal        — nothing to write down (question dodged, story vague, all "we")
negative         — evidence of the opposite (blame-shifting, no ownership, dishonesty)
```

`no signal` is the silent killer. It feels like a fine conversation. It produces a debrief that says
"pleasant, hard to assess" and a committee that declines because there is nothing to argue with.

**Trap:** believing a rambling answer is safer than a wrong one. A wrong-but-specific answer gets a
follow-up and a chance to recover. A vague answer gets a polite nod and a dead line in the debrief.

---

## 2. Level calibration: what makes a story L5 vs L6

This is the single most misunderstood part of the loop. The *same event* can be told as an L4, L5, or
L6 story. What moves it is the **blast radius of the decision you owned**.

| Dimension | L4 (mid) | L5 (senior) | L6 (staff / tech lead) |
|---|---|---|---|
| Unit of work | a task/ticket | a project or service | a *problem area* spanning teams or quarters |
| Ambiguity | requirements given | requirements negotiated | problem itself was undefined; you defined it |
| Who you convinced | your reviewer | your team + PM | peer teams, other seniors/staff, sometimes directors |
| Technical artefact | code merged | design chosen and shipped | direction others now build on (standard, platform, migration path) |
| Time horizon | sprint | quarter | 2–4 quarters, with a stated end state |
| Failure handling | fixed the bug | fixed the class of bug | changed the process/tooling so the class stops recurring |
| Success statement | "I delivered X" | "I delivered X, hit metric M" | "X is now how N teams do this, and metric M moved for the org" |

Worked re-framing of one true event — a slow endpoint:

- **L4 telling:** "Our search endpoint was slow, I profiled it and found a missing index, added it,
  latency dropped." (Correct, complete, and unhireable at senior.)
- **L5 telling:** "p99 on `GET /search` was 2.1 s against a 300 ms SLO. I ruled out GC and the
  network with the flame graph, found a full scan on a 40 M-row table, and had to choose between a
  covering index (write-amplification on our hottest write path) and a denormalised read model
  (consistency lag). I took the index because the write path had 20× headroom and the read model was
  two weeks of work. p99 went to 240 ms; I added a query-plan regression test so it can't come back."
- **L6 telling:** everything above, *plus*: "The same full-scan pattern existed in three other
  services because our shared repository template generated `findAll`-shaped queries. I wrote the
  plan-check into the shared CI template, ran the migration with the two owning teams over a
  quarter, and the org's count of >1 s endpoints went from 14 to 3. I also wrote the guidance doc
  that new services are reviewed against."

Notice what did **not** change: the technical difficulty. What changed: named alternatives, an
explicit trade-off with a reason, a number, and — for L6 — generalisation, other teams, and a
durable artefact.

**Trap:** manufacturing L6 scope by inflating team size ("I led 12 engineers" when you reviewed their
PRs). Interviewers probe headcount claims immediately: *who reported to you, who did you write
feedback for, what happened when someone disagreed*. Claimed scope you cannot drill into reads as
dishonesty, which is a **negative** signal, not a neutral one. Real narrow scope told with real depth
beats fake wide scope every time.

**The scope ladder you can honestly climb at 6 YOE:** most 6-YOE candidates have L6 *moments* inside
L5 *jobs* — the migration nobody owned, the incident you took over, the standard you wrote because you
were tired of arguing. Those moments are your Staff evidence. Hunt for them deliberately (§ 4.2).

---

## 3. Story architecture

### 3.1 STAR, and why the L and the R are where points are won

```text
S  Situation   — 2 sentences. Business context + the stakes. Not org history.
T  Task        — 1 sentence. YOUR specific charge, in the first person.
A  Action      — 60–90 seconds. 3–5 discrete decisions, each with a WHY.
R  Result      — 2–3 sentences. Numbers. Before → after. Plus what became permanent.
L  Learning    — 1–2 sentences. What you now do differently, stated as a rule.
```

Time budget for a 2.5-minute spoken answer (rehearse against a timer — most people's Situation runs
90 seconds unrehearsed):

| Part | Target | Words (~150 wpm) |
|---|---|---|
| S | 20 s | ~50 |
| T | 10 s | ~25 |
| A | 80 s | ~200 |
| R | 25 s | ~60 |
| L | 15 s | ~35 |

**The headline sentence.** Before S, lead with one sentence that tells the interviewer what they are
about to hear: *"The one I'd pick is when I killed a project I'd spent two months building."* This is
not fluff — it lets the interviewer file the story under the right competency immediately, and it
tells them whether to redirect you before you spend two minutes on the wrong axis.

**Trap:** the Action section that describes the *system* instead of *your decisions*. Listen to your
own recording: if the subject of most sentences is a component ("the consumer then read from the
queue…"), you are giving an architecture talk. The subject must be **I**, and the verb must be a
decision verb: chose, rejected, escalated, measured, negotiated, wrote, cut, deferred.

### 3.2 "I" vs "we", handled honestly

You cannot say "I" about work you did not do — interviewers catch it and it is fatal. You also cannot
say "we" about your own decisions — that produces `no signal`. The resolution is explicit attribution:

> "The team built the consumer. **My** part was the idempotency design — I argued for a dedup table
> keyed on the producer's message id over Kafka's transactional writes, because our sink was Postgres
> and we'd have kept exactly-once only up to the DB boundary anyway."

Rule: **"we" for the work, "I" for the decisions, and never a decision without a reason.**

### 3.3 The number problem

Most candidates believe they have no metrics. Almost always they have inputs to metrics and never did
the arithmetic. Derive one:

| You know | Derive |
|---|---|
| Requests/day and error rate before/after | failed requests prevented per month |
| Manual step you automated + frequency + people | engineer-hours/month reclaimed → FTE fraction |
| p99 before/after and traffic | user-seconds of latency removed per day |
| Incidents before/after | pages/quarter, MTTR delta, on-call hours |
| Instance count/size removed | $/month (list price is fine — say "list") |
| Build/deploy time before/after × deploys/day | dev-hours/week, deploy frequency change |
| Review/onboarding time for a doc you wrote | onboarding days saved × new joiners |

State the basis when a number is estimated: *"roughly 30 engineer-hours a month — that's the 12 people
on the rota times about 2.5 hours each, from the on-call handover notes."* An estimate with a visible
derivation is credible and scores. A precise-sounding number you cannot derive is a trap you set for
yourself, because the follow-up is *"how did you measure that?"*

**Trap:** claiming business revenue you did not influence ("saved the company $2M"). Claim the metric
closest to your actual lever, and let the interviewer extrapolate the business value themselves.

### 3.4 Stories about failure, without self-destructing

The failure story is scored on **ownership and systemic learning**, not on the size of the disaster.
The shape:

```text
1. What I decided, and why it was defensible at the time  (shows judgment, not luck)
2. What actually happened, stated plainly, no hedging     (shows honesty)
3. What I did in the next hour / day                      (shows response)
4. What I got wrong — a decision, not a circumstance      (shows ownership)
5. The systemic fix, not "I'll be more careful"           (shows learning)
```

Item 4 is where candidates fail. Compare:

- **Negative signal:** "The requirements changed and QA missed it." (Blame outward.)
- **No signal:** "I learned to communicate better." (Unfalsifiable, no mechanism.)
- **Strong positive:** "My mistake was treating a schema change as backwards-compatible because the
  *code* tolerated the missing column — I never checked the replicas' replay path. Now any schema
  change in that repo requires an expand/contract plan in the PR description, and the CI check I
  added fails a migration that drops a column in the same release that stops writing it."

**Trap:** choosing a fake failure ("I once worked too hard"). It reads as evasion and burns the round's
best opportunity to show seniority. Also avoid a failure that was purely someone else's with you as
bystander — no ownership to demonstrate.

**Trap (the other direction):** a failure so severe and so recent that it raises a competence flag —
e.g. you shipped a security hole and never noticed. Pick failures of *judgment under real trade-offs*,
not of basic diligence.

---

## 4. The story bank

### 4.1 Structure and target

The master plan's target: **20 stories, in full STAR, by Day 85**, in six categories. That is not
20 events — it is roughly **8–12 real events, each told for 2–3 different competencies.** One good
event (a migration you led, an incident you owned, a project you cancelled) legitimately answers
"technical direction", "influence", "hard call", *and* "ambiguity" — with a different Task sentence,
a different Action emphasis, and a different Learning each time.

| Cat | Theme | Count | Sample prompts it must cover |
|---|---|---|---|
| A | Technical direction | 4 | set direction for a team; a strategy you drove; a technology bet (right or wrong); simplified an over-engineered system |
| B | Influence without authority | 4 | convinced others of an architectural change; a senior engineer disagreed with you; negotiated scope with PM/leadership; raised the team's technical bar |
| C | Mentorship & people | 3 | developed a junior engineer; gave hard feedback; helped someone struggling |
| D | Hard calls | 4 | said no to a project; a failure you owned; a calculated risk; chose between two bad options |
| E | Delivery & ownership | 3 | owned something end to end; missed a deadline; found and fixed a problem nobody asked you to |
| F | Ambiguity | 2 | operated with unclear requirements; defined the problem before solving it |

Per story, store exactly this — it is what makes a bank *usable* under pressure:

```markdown
### <short handle, e.g. "Kafka dual-write kill">
- **One-liner:** cancelled a half-built dual-write path after 6 weeks; replaced with outbox.
- **Competencies:** hard call (primary), technical direction, influence.
- **LPs / values:** Are Right A Lot, Have Backbone, Invent & Simplify.
- **Metrics:** 6 weeks sunk; dedup bug rate → 0; 2 weeks to ship replacement.
- **STAR (spoken, 2.5 min):** …
- **60-second version:** …
- **Three deepest follow-ups I expect, with answers:**
  1. What would you have done differently at week 1? …
  2. Who disagreed, and how did you handle it? …
  3. What did the numbers say at the point you decided? …
```

The **60-second version** matters: interviewers running behind will say "briefly". The
**follow-up answers** matter more than the STAR itself — that is where depth is tested.

### 4.2 Mining your history for the stories you think you don't have

Run these prompts over the last 3–4 years; write down everything, filter later. Aim for 25 candidates,
keep the best 20 (the master plan's Day-16 exercise).

- What did you *stop* doing, delete, or cancel? (Simplification and hard-call stories hide here.)
- What did you build that nobody asked for? (Ownership.)
- What argument did you lose — and what did you do next? (Disagree & commit; this is a top-tier
  Staff story and almost nobody prepares one.)
- What argument did you win, with evidence rather than seniority? (Influence.)
- What was on fire at 2am, and what did you change so it never was again? (Ownership + systemic fix;
  see `20-observability-operations.md` for the postmortem vocabulary.)
- Who is better at their job because of you, specifically? (Mentorship — needs a *named outcome*, e.g.
  "she now owns that service's on-call".)
- What did you say no to, and what was the cost of saying yes? (Prioritisation judgment.)
- What did you not know how to do at all when you started it? (Ambiguity, growth.)
- What decision are you still not sure was right? (Self-awareness; excellent answer to "are right a
  lot" done honestly.)
- What did you have to migrate while it was running? (Delivery under constraint — pairs with the
  live-migration section of `22-system-design.md`.)

### 4.3 The coverage matrix

Build a grid: rows = your stories, columns = the target company's competencies/LPs. Two failure modes
it catches immediately:

1. **A hole** — a column with no story. Fix by re-telling an existing event with a new Task/emphasis,
   or by mining harder. Holes are what get you asked a question you've never thought about.
2. **A monoculture** — one event covering eight columns. If you tell the same project four times in a
   loop, interviewers compare notes in the debrief and mark "narrow experience". Cap it: **no single
   event more than 3 times across a loop**, and never twice in the same interview.

Also tag each story with the **time period**. A bank where everything happened in one 8-month window
reads as a single lucky project.

---

## 5. Amazon's 16 Leadership Principles, and the mapping to everyone else

Memorise all 16 (the master plan puts this at Day 141). For each, know your **two default stories** —
a primary and a backup, because the interviewer may say "another one".

| LP | The signal it probes | What a weak answer looks like |
|---|---|---|
| Customer Obsession | you started from user impact, not from tech elegance | "the API was ugly so I refactored it" |
| Ownership | acted beyond your remit; thought past your tenure | "I raised a ticket for the other team" |
| Invent and Simplify | removed complexity, or invented rather than adopted | new framework with no baseline comparison |
| Are Right, A Lot | judgment under incomplete data; also revising with new data | a story with no uncertainty in it |
| Learn and Be Curious | went and learned the thing properly | "I read the docs" |
| Hire and Develop the Best | a named person got measurably better | "I mentor juniors" (no name, no outcome) |
| Insist on the Highest Standards | you refused something that met spec but not the bar | gold-plating with no cost awareness |
| Think Big | proposed the 10× version, not the 10% one | grandiosity with no first step |
| Bias for Action | shipped reversible decisions fast, said so explicitly | recklessness with no reversibility argument |
| Frugality | got the outcome for less | cheapness that cost engineer-time |
| Earn Trust | took criticism well; was candid early | "everyone liked me" |
| Dive Deep | you personally looked at the data/code/logs | "the team investigated" |
| Have Backbone; Disagree and Commit | disagreed *and then committed fully* | disagreed and sulked, or never disagreed |
| Deliver Results | shipped under changed constraints | shipped, no constraints, no numbers |
| Strive to be Earth's Best Employer | you improved how it felt to work there | HR language |
| Success and Scale Bring Broad Responsibility | second-order consequences considered | not considered |

Highest-weight for a Staff/L6 target (per the master plan): **Ownership, Bias for Action, Think Big,
Earn Trust, Are Right A Lot, Have Backbone, Deliver Results, Hire & Develop the Best, Insist on
Highest Standards, Invent & Simplify.**

Mapping to other loops — same stories, different framing sentence:

| Amazon LP cluster | Google | Meta | Generic HM round |
|---|---|---|---|
| Ownership, Deliver Results | emergent leadership, "role-related knowledge" | "drive/impact" | "tell me about your biggest impact" |
| Have Backbone, Earn Trust | Googleyness (collaboration, comfort with ambiguity) | "conflict / feedback" round | "a disagreement with a colleague" |
| Are Right A Lot, Dive Deep | general cognitive ability, technical judgment | project deep dive | "a technical decision you made" |
| Hire & Develop, Highest Standards | leadership without authority | "growing others" | "how do you mentor" |
| Think Big, Invent & Simplify | leadership / navigating ambiguity | "long-term thinking" | "where should this system be in 2 years" |

**Trap:** naming the LP out loud as a label ("this shows my Customer Obsession"). Demonstrate it; the
interviewer maps it. Naming it sounds coached and invites scepticism. The exception is Amazon
explicitly asking "tell me about a time you showed Bias for Action" — then you match the frame, but
still don't narrate the mapping.

---

## 6. Question taxonomy: what is really being asked

| Question | The real probe | Answer must contain |
|---|---|---|
| "Tell me about yourself" | can you frame a career narrative with a direction? | 90 s: arc → current scope → why this role is the next step |
| "Most impactful project" | scope + attribution + metrics | your specific decisions, the number, why it mattered to the business |
| "A technical decision you made" | judgment | the alternatives *you rejected* and the reason, not just the choice |
| "A time you disagreed with your manager" | backbone + professionalism | disagreement raised with data, then either persuaded or committed fully |
| "A time you failed" | ownership + systemic learning | your decision error, the systemic fix (§ 3.4) |
| "A conflict with a teammate" | do you make conflict smaller or bigger? | you sought their model first; resolution mechanism, not who won |
| "Feedback you received" | coachability | specific, unflattering, and what you changed |
| "Feedback you gave" | courage + care | the hard bit said plainly; the outcome for that person |
| "How do you prioritise?" | judgment at scope | an actual framework applied to a real conflict, with what you dropped |
| "A time you influenced without authority" | staff-defining | evidence, a pilot/prototype, coalition-building — not escalation |
| "Something you'd do differently" | self-awareness | a real alternative you now believe was better |
| "Why leaving / why us" | risk + motivation | forward-looking pull, never a complaint about people |
| "Where do you want to be in 3 years" | level fit + retention | scope growth consistent with the level you're applying for |
| "Questions for me?" | seniority of what you're curious about | 2–3 real ones (see § 9.3) |

### 6.1 Influence without authority — the mechanism

This is the question that most reliably separates L5 from L6, and the wrong answer pattern is
escalation ("I took it to my manager"). The mechanisms that score:

1. **Find their objective, not their objection.** The other team resisting your migration is defending
   a roadmap commitment, not disliking your design. Re-frame your proposal in the currency they are
   measured in.
2. **Make it cheap to say yes.** Do the first slice yourself. A working prototype changes the
   conversation from "should we" to "should we keep it".
3. **Bring evidence, in their units.** Latency graph, cost delta, incident count — not architectural
   taste. See `20-observability-operations.md` for what evidence to have on hand.
4. **Build the coalition before the meeting.** Pre-align the two people whose objection would sink it.
   Meetings ratify decisions; they rarely make them.
5. **Write it down.** A one-page design doc with alternatives and a recommendation is the durable
   artefact; it also survives your absence, which is exactly the L6 signal.
6. **Name the reversal condition.** "If p99 doesn't improve by 30% in two weeks, we roll back" removes
   most of the fear that drives resistance.

**Trap:** telling an influence story where you were right and everyone else was foolish. Interviewers
hear arrogance and, worse, hear that you cannot model other people's constraints. Give the opposing
view its strongest form before you say why you disagreed.

### 6.2 Disagree and commit, told correctly

```text
1. The decision, and why I disagreed — with the data I had
2. How I raised it: to whom, in what forum, once or twice (not five times)
3. The outcome: I did not win
4. What I did next: committed FULLY and visibly — and here is the specific thing I did
   to make the chosen path succeed
5. What happened, and what I'd concede now with hindsight
```

Step 4 is the whole answer. A story that ends at step 3 is a complaint.

---

## 7. Surviving the follow-ups

Follow-ups exist to test whether the story is yours and whether it is as deep as it sounded. Expect
the interviewer to pick the single vaguest sentence you said and push on it.

| Follow-up | What it's testing | How to be ready |
|---|---|---|
| "What was *your* specific contribution?" | attribution | have the boundary of your work pre-drawn |
| "Why not <obvious alternative>?" | did you consider it | know 2 rejected options per technical story, with reasons |
| "How did you measure that?" | is the number real | know the source: dashboard, load test, ticket count |
| "What would you do differently?" | self-awareness | never "nothing"; have a real answer |
| "Who disagreed?" | conflict handling | name a real objection and its strongest form |
| "What happened after you left it?" | durability | the artefact/process that persisted |
| "Walk me through the code/schema/plan" | dive deep | be able to go one level below where you stopped |

Three tactics:

- **Answer the question asked, then stop.** Volunteering more surface area invites deeper drilling into
  the parts you know least.
- **Say "I don't remember the exact figure" rather than inventing one.** Then give the bound: *"it was
  the low hundreds of milliseconds, and the SLO was 300 — I can't give you the exact p99."* Fabricated
  numbers collapse under one more question and turn a positive into a negative signal.
- **If you don't have the story, say so and pivot deliberately:** *"I haven't managed anyone, so I
  don't have a hiring story. The closest is when I owned onboarding for two new joiners — is that
  useful?"* Honest pivot > forced non-answer. Never invent an event.

**Trap:** treating a follow-up as an accusation and getting defensive. Follow-ups are engagement; the
interviewer is trying to find evidence to write down. Defensiveness is itself a scored signal.

---

## 8. Delivery mechanics

The content can be perfect and the round still fail on delivery. What actually moves the score:

- **Length discipline.** 2–3 minutes per story. Past 4 minutes, the interviewer is managing you
  instead of assessing you, and you'll cover 3 stories in a round instead of 5.
- **Structure signposting.** "Three things I did — first…, second…, third…". This makes the notes
  structured, and structured notes get quoted in the debrief.
- **Rehearse out loud, recorded.** The master plan schedules this from Day 21 onward for a reason:
  the gap between a written STAR and a spoken one is enormous. Listen back for: how long the Situation
  ran, how many "we"s, whether the number is actually said out loud, filler density.
- **Do not memorise word-for-word.** Memorise the *beats* (headline, 3 actions, the number, the rule).
  Recited answers sound rehearsed and, critically, break entirely when the question is a variant.
- **Silence is allowed.** "Let me pick the right example" for three seconds is better than starting the
  wrong story and abandoning it halfway.
- **Remote-specific:** camera at eye level, notes as 5-word bullets only (reading is audible in your
  voice and visible in your eyes), and confirm audio before the round.

Practice progression that works:

```text
week 1  write STAR text        → 5 stories
week 2  speak to a recorder    → same 5, timed, listen back once each
week 3  speak to a human       → they ask 2 follow-ups you didn't prepare
week 4  cold random draw       → pick a card, 10 s to think, deliver
```

The cold-random-draw drill is the one that transfers. Loops do not ask questions in your bank's order.

---

## 9. The rest of the loop that behavioral leaks into

### 9.1 The design round is partly behavioral

In a senior/staff design round, roughly a third of the signal is behavioral: how you handle a
requirement change mid-design, whether you ask before designing, whether you say "I don't know" about
a technology, whether you take a hint. `22-system-design.md` owns the technical content; the
behavioral read is: *do I want this person driving a design review?*

### 9.2 The hiring manager round

Different objective from the competency rounds: the HM is deciding whether they want you *on their
team, on their problems*. So they weigh motivation, level fit, and how you talk about your last team.
Two rules: never criticise a former colleague as a person (criticise a system or a decision), and be
able to state concretely why *this* team's problem interests you.

### 9.3 Your questions for them

Scored, whether or not they admit it. Junior questions ask about perks; senior questions ask about how
decisions get made. Good ones:

- "How does a technical decision that spans two teams get made here — who has to agree?"
- "What's the thing about this codebase or system that a new senior engineer is always surprised by?"
- "What would you want the person in this role to have changed in twelve months?"
- "How does on-call work, and what does the last quarter's page volume look like?"
- "What's currently the biggest source of unplanned work for the team?"

**Trap:** asking something answered on the careers page. It reads as no preparation.

---

## 10. Anti-pattern catalogue

| Anti-pattern | Why it fails | The fix |
|---|---|---|
| All "we", no "I" | no attributable evidence → `no signal` | "we" for work, "I" for decisions (§ 3.2) |
| No numbers | impact unverifiable | derive one (§ 3.3), state the basis |
| Situation runs 90 seconds | Action gets squeezed, notes stay empty | timed rehearsal; 2-sentence Situation |
| Architecture talk instead of a story | subject is components, not you | decision verbs in the first person |
| Fake failure | reads as evasion, burns the best slot | real judgment error + systemic fix |
| Blame in the failure story | negative signal on ownership | own the decision, not the circumstances |
| One project told four times | "narrow experience" in the debrief | max 3 uses per event per loop (§ 4.3) |
| Inflated scope | collapses under drilling; reads dishonest | narrow scope, real depth |
| Escalation as the influence story | reads as no influence | evidence + prototype + coalition (§ 6.1) |
| Naming the LP out loud | sounds coached | demonstrate, let them map |
| Rehearsed to the word | breaks on question variants | memorise beats, not sentences |
| Complaining about the last job | reads as a risk to team health | criticise systems and decisions, not people |
| "Nothing, I'd do it the same" | no self-awareness signal | always have the real alternative |
| Prep only for behavioral in week 25 | stories need months of rehearsal to sound natural | 1–1.5h/week from week 4 (the plan's cadence) |

The master plan's own prep anti-pattern #4 is the summary of this table: *behavioral on autopilot —
"we" instead of "I", vague impact, no metrics → senior-bar fail before you even reach the Staff signal
questions.*

---

## 11. Self-scoring rubric

Score each story 0–2 on each row. A story below 12/16 is not loop-ready. Re-score after recording it,
not after writing it — the written version always scores higher than the spoken one.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Headline in the first sentence | absent | vague | states the point |
| 2 | Situation ≤ 25 s | rambles | slightly long | tight |
| 3 | First-person decisions | all "we" | mixed | clear ownership |
| 4 | Alternatives rejected, with reasons | none | named, no reason | named + reasoned |
| 5 | Quantified result | none | qualitative | number + basis |
| 6 | Scope matches the target level | L4 | L5 | L6 evidence present |
| 7 | Durable artefact / what persisted | none | mentioned | specific and named |
| 8 | Learning as a rule, not a sentiment | none | "communicate better" | concrete rule I now apply |

Track coverage separately: **stories written / 20**, **categories with ≥ target count**, **stories
recorded out loud**, **stories drilled by a human**.

---

## 12. Operating cadence (mapped to the 28-week plan)

| Plan point | Behavioral deliverable |
|---|---|
| Day 16 | brainstorm 25 candidates, pick 15, write 5 in full STAR |
| Day 21 | 5 more (10 total), each tagged with 2 LPs |
| Day 26 | 3 stories out loud, recorded, refined |
| Day 31 | 15 total; "Tell me about yourself" 90-second version |
| Day 40 | 18 total; re-tagged for Staff LPs |
| Weeks 9–16 | project-narrative stories from Projects 1–2; "a technical decision" and "a system you designed" |
| Day 85 | **20 stories complete** |
| Day 108 | full behavioral mock, Staff signals |
| Day 141 | all 16 LPs memorised, two default stories each |
| Day 146+ | per-company value rehearsal, "why this company" × 5 versions |

Weekly steady-state from week 4: **1–1.5 hours**, one of {write 2 new stories, record and re-score 3
existing, run a cold-draw drill with a partner}. Behavioral is the one area where cramming is visibly
detectable, because unrehearsed stories are long and unrehearsed *follow-ups* are empty.

---

## Atomic concept checklist

- [ ] I know the round's output is a written debrief read by people who never meet me, so I speak in
      quotable specifics rather than rapport.
- [ ] I can name the four verdicts (strong positive / positive / no signal / negative) and I know
      `no signal` — not a bad story — is the most common way to fail.
- [ ] I can state the five rubric axes: impact, ownership, judgment, collaboration, growth.
- [ ] I can tell the same event as an L4, L5, and L6 story, and I know the difference is blast radius
      of the decision I owned, not technical difficulty.
- [ ] I know inflated scope reads as dishonesty (negative), not as ambition.
- [ ] I hit the STAR-L time budget: 20 s / 10 s / 80 s / 25 s / 15 s, headline first.
- [ ] My Action sentences have "I" as the subject and a decision verb, each with a reason.
- [ ] I use "we" for the work and "I" for the decisions, and never state a decision without its why.
- [ ] I can derive a metric from inputs I actually have, and I state the basis when it's an estimate.
- [ ] My failure story owns a *decision* error and ends in a systemic fix, not "I'll be more careful".
- [ ] I have 20 stories from 8–12 events, ≤ 3 uses of any one event per loop, spread over time.
- [ ] I have a coverage matrix against the target company's competencies and no empty columns.
- [ ] For each of Amazon's 16 LPs I have a primary and a backup story, and I never name the LP aloud.
- [ ] I have a prepared "disagree and commit" story that ends in what I did to make the *other* path
      succeed.
- [ ] My influence stories run on evidence, prototypes, and coalitions — not escalation.
- [ ] For every story I know two rejected alternatives, the measurement source, and what persisted
      after I left it.
- [ ] I say "I don't remember the exact number" with a bound instead of inventing a figure.
- [ ] I have rehearsed out loud, recorded, timed, and cold-drawn — not just written.
- [ ] I have 2–3 senior-flavoured questions for the interviewer about how decisions actually get made.
- [ ] I self-score stories 0–2 across the eight criteria and treat < 12/16 as not loop-ready.
