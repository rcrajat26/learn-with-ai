# 21 AI for Coding — your own instruction files, costed — BASICS (§1.3.29)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [auto memory](03-auto-memory.md) · Next: [permission rules and their order](../permissions/01-basics-rules-and-order.md)

---

The previous file covered auto memory end to end: the four types Claude records, the on-disk index
and topic-file split, the 200-line/25 KB load gate, the subagent boundary, what a `/compact` does and
does not preserve, and the diagnostic ladder for "Claude ignored my `CLAUDE.md`." This file applies
all of that to one concrete case: the two `CLAUDE.md` files that load into every session run in this
repository, on this reader's own machine.

## §1.3.29 — The reader's own two-level setup, accounted for

**`[CASE]` `[BUILD]`, grounded in the reader's own machine, not sdlc-harness.** Every session run in
this repository loads two files, concatenated in the load order `01-basics-claude-md.md` already
established (broader scope first, narrower scope last, so the narrower file is read most recently):
the global user file at `/Users/rajat.chikkodikar/.claude/CLAUDE.md`, then the project file at
`/Users/rajat.chikkodikar/Desktop/My-files/rough/.claude/CLAUDE.md`. Both are **read-only for this
leaf** — the accounting below does not edit either file.

**Why this is worth a full leaf, not a footnote.** Every earlier leaf in this memory area explains a
mechanism in the abstract — an example rule, an example memory file. This one turns the same mechanism
on the actual configuration governing the very session writing these notes, which is the only way to
make "always-on `CLAUDE.md` content is paid every turn of every session" land as an arithmetic fact
about a real, present cost rather than a hypothetical one.

### The artefact: a per-entry token accounting

Both files were measured directly with `wc`, then converted to tokens using the same
4-characters-per-token estimate `02-rules-and-path-scoping.md` used for its own §1.3.15 arithmetic.
That estimate is a rule of thumb, not the harness's own tokenizer — the prove step below shows how to
get the authoritative figure for any given session.

**Global user file — `~/.claude/CLAUDE.md`, 160 lines, 6,973 characters total:**

| Entry | Lines | Chars | Est. tokens |
|---|---|---|---|
| Title / header | 1–3 | 127 | 32 |
| Output Rules | 4–12 | 610 | 153 |
| Context Management | 13–20 | 425 | 106 |
| Model Routing | 21–40 | 952 | 238 |
| Agent & Subagent Rules | 41–61 | 869 | 217 |
| Parallel Execution | 62–66 | 258 | 65 |
| Workflow with Plan Mode | 67–72 | 249 | 62 |
| Verification (TDD) | 73–76 | 153 | 38 |
| Document-Driven Development | 77–82 | 306 | 77 |
| Core Rules table | 83–93 | 602 | 151 |
| Error Learning | 94–97 | 156 | 39 |
| Skills vs CLAUDE.md | 98–101 | 191 | 48 |
| Security | 102–104 | 94 | 24 |
| SuperClaude Behaviors block (auto-managed) | 105–160 | 1,981 | 495 |

Sum check on the entry column: 32+153+106+238+217+65+62+38+77+151+39+48+24+495 = **1,745** tokens
(the 2-token gap against the 1,743 whole-file estimate below is rounding in fourteen separate
divisions rather than one; both numbers are the same measurement, not a discrepancy in the underlying
bytes). Sum check on the chars column: 127+610+425+952+869+258+249+153+306+602+156+191+94+1,981 =
**6,973**, matching the whole-file byte count exactly.

**Project file — `.claude/CLAUDE.md`, 155 lines, 9,021 characters total:**

| Entry | Lines | Chars | Est. tokens |
|---|---|---|---|
| Header / intro | 1–6 | 293 | 73 |
| Core artifacts table | 7–20 | 1,019 | 255 |
| Folder structure block | 21–67 | 2,922 | 731 |
| The two pipelines section | 68–108 | 2,216 | 554 |
| Generation rules | 109–125 | 1,144 | 286 |
| Audience tier discipline | 126–136 | 487 | 122 |
| Quality bar checklist | 137–150 | 726 | 182 |
| See also | 151–155 | 214 | 54 |

Sum check on the entry column: 73+255+731+554+286+122+182+54 = **2,257** tokens (again a 2-token
rounding gap against the 2,255 whole-file estimate below). Sum check on the chars column:
293+1,019+2,922+2,216+1,144+487+726+214 = **9,021**, matching the whole-file byte count exactly.

**Grand total: 1,743 + 2,255 = ≈3,998 tokens of `CLAUDE.md` content loaded before the first user turn
of every single session run in this repository**, on top of whatever the system prompt and tool
definitions add — a cost this leaf does not attempt to measure, since it is outside both files.

### The prove step

The real byte counts behind every row above, run directly against both files:

```
$ wc -l -c -w /Users/rajat.chikkodikar/.claude/CLAUDE.md \
              /Users/rajat.chikkodikar/Desktop/My-files/rough/.claude/CLAUDE.md
     160     973    6973 /Users/rajat.chikkodikar/.claude/CLAUDE.md
     154    1088    9021 /Users/rajat.chikkodikar/Desktop/My-files/rough/.claude/CLAUDE.md
     314    2061   15994 total
```

`[PROVE]` `[NUM]` The section-level rows were produced the same way, per line range, against the same
files — `sed -n '<range>p' <file> | wc -c` — which is why the two sum checks above land on the
whole-file byte counts exactly: they are the same measurement sliced fourteen and eight ways rather
than independent estimates. The arithmetic that turns bytes into the two file-level token totals:

```
6,973 chars ÷ 4 chars/token ≈ 1,743 tokens   (global user file)
9,021 chars ÷ 4 chars/token ≈ 2,255 tokens   (project file)
1,743 + 2,255 = 3,998 tokens loaded at launch, before any conversation
```

A reader who wants the authoritative figure for *their own* running session, rather than this
file-based estimate, runs `/context` and reads the token count listed against the **Memory files**
entry directly — that is the number the harness itself computed, against the tokenizer it actually
used, in place of this leaf's 4-characters-per-token approximation. The two numbers will not match
exactly; they answer the same question at two different levels of precision, the way this leaf's own
byte-derived estimate and its section-level sum both approximate the same measurement without landing
on an identical figure.

### What this costs

Because both files are project-root-scoped `CLAUDE.md` content with no `paths:` frontmatter, they are
**always-on**: paid on every turn of every session, exactly like the un-scoped rule file
`02-rules-and-path-scoping.md` walked through at §1.3.15, and — per `03-auto-memory.md`'s §1.3.26 —
re-read and re-injected after every `/compact`, so a long session never stops paying for them either.

Applying the same per-turn multiplication §1.3.15 used, for a 40-turn session where both files stay
resident the whole time (which they do, once loaded, because the whole conversation is re-sent every
turn):

```
3,998 tokens × 40 turns = 159,920 tokens for this pair of files, in this one session
```

**Unverified:** converting that figure to a dollar amount requires a specific model's published
input-token price, which is not one of this leaf's re-verifiable pages — `settings`,
`settings-reference`, and `memory` carry no model pricing, and this leaf's obligation is to re-verify
against exactly that page set, not to go hunting for a pricing page outside it. Using Sonnet's
commonly cited list price as of August 2026, **$3 per million input tokens**, as an illustrative
figure only, not an authoritative one:

```
159,920 tokens × ($3 ÷ 1,000,000) ≈ $0.48 for this pair of files, for this one 40-turn session
```

That is the standing tax this two-level setup charges on every session in this repository, regardless
of whether the session ever touches the day/week pipeline, the per-topic pipeline, or neither — the
same "paid whether or not the session needed it" property §1.3.15 used 84,000 tokens of API-rules
example to make, now measured against a real file instead of an example one.

### The excerpts, verbatim

The global file's Output Rules — the section actually governing this note's own prose, quoted exactly:

```
- NEVER narrate thinking process. Internal reasoning stays internal (use tools silently).
- NEVER use: "Let me check", "Actually", "Wait", "Looking at", "The issue might be", "I'll help", "Let me"
```

The global file's Model Routing table:

```
### Subagent Model Selection (ENFORCE)
When spawning Task agents, ALWAYS set model parameter:
- **model=haiku**: Web search, file search, codebase exploration, documentation lookup
- **model=sonnet**: Code writing, test writing, implementation, refactoring, build/test runs
- **model=opus**: Architecture review, complex debugging, security audit, multi-file analysis
DO NOT spawn agents without explicit model= parameter.
Escalation fallback: haiku → sonnet → opus
```

The auto-managed SuperClaude block re-states this same decision under a different heading, with a
narrower framing and a partially different rule set:

```
### Model Routing
|Task|Model|When|
|-|-|-|
|Explore,read,search|haiku|Read-only,<30 files|
|Summarize,analysis|haiku|Low complexity|
|Implementation|sonnet|Main dev work|
|Architecture|opus|Critical only|
**Rules:** Task→haiku(read-only), Subagents→haiku default, Escalate: haiku→sonnet→opus
```

The project file's Generation rule scoped to a pipeline this very leaf is not running:

```
8. **Write notes inline. NEVER delegate to subagents.** (Day/week pipeline only.
   The per-topic pipeline is explicitly orchestrated: `notes-generator` owns
   `00-index.md` and dispatches one writer per note file plus illustrators for
   the diagrams. See its Execution model.)
```

The project file's Document-Driven Development counterpart does not appear in the global file's
Document-Driven Development section by contrast — the global section instead names files this
project's own layout does not use, which the judgment table below treats as its own finding.

### Judging each entry: belongs here, or belongs in a skill or a path-scoped rule?

This is the leaf's actual question, so every entry in both files gets a verdict, not a general summary.

**Global file — 14 entries:**

| Entry | Verdict | Why |
|---|---|---|
| Title / header | Belongs | Not instructional content; negligible cost |
| Output Rules | Belongs | Governs every response regardless of task; no file-type or task-type scoping applies |
| Context Management | Belongs | Applies to every session, not conditional on what the session touches |
| Model Routing | **Move to a skill** | A multi-step decision procedure ("which model for which task") — exactly the category `02-rules-and-path-scoping.md`'s own gotcha names as a skill's job. Invoked only at the moment of spawning a subagent, not needed in context for the rest of a session's turns |
| Agent & Subagent Rules | **Move to a skill** | Same reasoning — a "when to use which agent shape, how many concurrently" procedure, not a fact every turn needs regardless of task |
| Parallel Execution | Belongs | Short, general, applies to any tool-calling turn |
| Workflow with Plan Mode | **Move to a skill** | A named multi-step workflow (`START → /plan → BRAINSTORM → …`) is precisely a procedure, invoked at the start of a planning cycle, not a standing fact needed every turn |
| Verification (TDD) | Belongs | Short, general standing rule |
| Document-Driven Development | **Does not belong at all** | References `PROGRESS.md` / `EXECUTION_PLAN.md` / `ARCHITECTURE.md` at the project root — files this actual project does not use. The project's own `CLAUDE.md` instead names `.claude/progress.md`, `.claude/conventions.md`, `.claude/workflow.md`. This entry is paid every turn of every session in this repository for a convention the repository does not follow, at roughly 77 tokens per turn for nothing in return |
| Core Rules table | Belongs | Short, general, standing; a table is the correct rendering for a comparison of seven named rules |
| Error Learning | Belongs | Short, general, no task-type or path scoping applies |
| Skills vs CLAUDE.md | Belongs | Short meta-rule about the mechanisms themselves — needed to make the right call on every other entry in this same table |
| Security | Belongs | Always-relevant, cheap, and exactly the kind of "never do X" the docs' own table recommends putting in `CLAUDE.md` as behavioral guidance (with `permissions.deny` reserved for the hard-enforced version) |
| SuperClaude Behaviors block | **Move or delete** | At 495 tokens it is the single largest entry in the file, and it duplicates Context Management, Model Routing, and the slash-command dispatch mechanism already covered above it under different headings and slightly different numbers — the exact "two files disagree, Claude may pick one arbitrarily" hazard `03-auto-memory.md`'s §1.3.28 names, self-inflicted within one file rather than across two |

**Project file — 8 entries:**

| Entry | Verdict | Why |
|---|---|---|
| Header / intro | Belongs | Short, orients every session regardless of task |
| Core artifacts table | Belongs | Referenced constantly across both pipelines; a table is the correct rendering for nine named files |
| Folder structure block | **Partially move** | At 731 tokens this is the single largest entry in either file. A bare directory tree is exactly the content the `/doctor` trim check (named on the memory documentation page) targets: content "Claude can derive from the codebase," such as directory layouts. The prose annotations explaining *why* each folder exists are not derivable from a directory listing and earn their place; the raw tree paths themselves largely do not |
| The two pipelines section | **Move to a skill** | A multi-step procedure per pipeline (which agent runs after which, what each stage reads and writes), invoked only when starting or continuing a pipeline run, not needed verbatim on every turn of an unrelated session |
| Generation rules | **Move to a path-scoped rule**, `paths: ["w*/day*-notes.md", "w*/week*-notes.md"]` | Explicitly marked "(Day/week pipeline only)" in its own text — the textbook case for `02-rules-and-path-scoping.md`'s §1.3.15 mechanism. This very leaf, writing under `src/notes/detailed/21-ai-for-coding/memory/`, pays for 286 tokens of day/week-only rules on every turn it will never act on |
| Audience tier discipline | **Move to the same path-scoped rule** | Same day/week-only scope as Generation rules; no reason to split the two into separate rule files since they always apply or don't apply together |
| Quality bar checklist | **Move to the same path-scoped rule** | Same day/week-only scope |
| See also | Belongs | Three lines, negligible, general orientation pointer to the other project files |

**The pattern across both files.** Content that is general and cheap stays where it is. Content that
names a multi-step procedure — Model Routing, Agent & Subagent Rules, Workflow with Plan Mode, the two
pipelines section — moves to a skill invoked at the moment it is needed, per the docs' own guidance
that a "multi-step procedure" belongs in a skill rather than in always-on `CLAUDE.md`. Content
explicitly scoped to one of the two pipelines — the project file's Generation rules, Audience tier
discipline, and Quality bar checklist, all three already marked "Day/week pipeline only" in the
project's own prose — is the clearest possible candidate for `paths:` frontmatter, because
§1.3.15's savings arithmetic applies to it exactly:

```
Combined cost of the three day/week-only entries: 286 + 122 + 182 = 590 tokens
Paid every turn today, in every session, including sessions that never touch w*/
As a path-scoped rule limited to w*/day*-notes.md and w*/week*-notes.md:
  a session that never opens a matching file pays 0 tokens for all three,
  for the entire session — this leaf's own session included.
```

One entry earns a verdict distinct from "move it somewhere else": the global file's Document-Driven
Development section is not misplaced, it is **describing a convention this specific project does not
use**. Moving it to a skill or a path-scoped rule would still leave it paid for by every project that
loads the global file and does not use `PROGRESS.md`/`EXECUTION_PLAN.md`/`ARCHITECTURE.md` — the
correct fix for that entry is deleting it from the global file, or rewriting it to name the file
triple this project's own `.claude/CLAUDE.md` actually specifies.

> The right home for a `CLAUDE.md` entry is decided by two questions, not one: does every session need
> it regardless of what it touches (stays in `CLAUDE.md`), and if so, is it a standing fact or a
> multi-step procedure (fact stays, procedure moves to a skill) — and if it is scoped to specific files
> rather than every session, does a `paths:`-scoped rule already exist to carry exactly that cost
> pattern for free.

## Pitfalls

- **Belief:** splitting a large `CLAUDE.md` into topic sections under headers, the way this reader's
  own global file is organized (Output Rules, Context Management, Model Routing, Agent & Subagent Rules), already
  captures most of the available savings, because the content is at least organized. **Outcome:** every
  one of those sections still loads at launch and stays resident for the whole session — organization
  on the page changes nothing about the token bill, which is exactly the entry-by-entry accounting
  above: a well-organized 3,998-token pair of files costs the same 3,998 tokens per turn as a
  disorganized one. **What actually gets the guarantee:** moving a multi-step procedure into a skill,
  or scoping a directory-specific section with `paths:` frontmatter — the two moves this leaf's
  judgment table applies entry by entry. **Why people believe it:** headers and bullet structure are
  genuinely good practice for *adherence* (the docs recommend exactly this), which makes it easy to
  conflate "well-structured" with "cheap."
- **Belief:** an auto-managed block like the SuperClaude section — installed by a tool, marked "DO NOT
  EDIT THIS SECTION MANUALLY" — is safe to leave alone indefinitely because it is not the reader's own
  prose to maintain. **Outcome:** it silently duplicates and partially contradicts hand-written content
  above it in the same file (two different Model Routing tables, two different Parallel Execution
  rules), which is the same "two files disagree, Claude may pick one arbitrarily" hazard, just
  self-inflicted within one file rather than across the managed/user/project boundary. **What actually
  gets the guarantee:** auditing an auto-managed block's content the same way any other `CLAUDE.md`
  section is audited, even though editing it directly is discouraged — the fix here is raising it with
  whatever installer manages the block, or overriding the duplicated guidance explicitly in the
  hand-written section above it. **Why people believe it:** "DO NOT EDIT" reads as "do not think about
  this," when it only means "do not hand-edit this specific block."

## Cheat sheet

| Fact | Value |
|---|---|
| Global file size | 160 lines, 6,973 chars, ≈1,743 tokens |
| Project file size | 155 lines, 9,021 chars, ≈2,255 tokens |
| Combined always-on load | ≈3,998 tokens, every session, before the first turn |
| Token estimate method | 4 chars/token (rule of thumb); `/context` gives the authoritative figure |
| Per-40-turn-session cost | 3,998 × 40 = 159,920 tokens |
| Illustrative dollar cost | ≈$0.48 at Sonnet's cited $3/MTok input list price (unverified against this leaf's doc set) |
| Largest single entry, global file | SuperClaude Behaviors block, 495 tokens — largely duplicative |
| Largest single entry, project file | Folder structure block, 731 tokens — largely derivable from the codebase |
| Global entries that should move to a skill | Model Routing, Agent & Subagent Rules, Workflow with Plan Mode |
| Global entry that should be deleted/rewritten | Document-Driven Development — names files this project doesn't use |
| Project entries that should move to a `paths:` rule | Generation rules, Audience tier discipline, Quality bar checklist (590 tokens combined, day/week-pipeline-only) |
| Project entry that should move to a skill | The two pipelines section (554 tokens) |
| Project entry that should partially shrink | Folder structure block — keep the annotations, cut the derivable bare tree |

## Self-test

1. What are the two numbers behind the ≈3,998-token combined figure, and what estimate converts bytes
   to tokens?
<details><summary>Answer</summary>
≈1,743 tokens for the 6,973-character global file, plus ≈2,255 tokens for the 9,021-character project
file, using a 4-characters-per-token rule of thumb (the same one `02-rules-and-path-scoping.md` used
for its §1.3.15 arithmetic).
</details>

2. Why does this leaf recommend running `/context` rather than trusting the 4-chars-per-token estimate
   as the final word?
<details><summary>Answer</summary>
Because 4 chars/token is a rule of thumb, not the harness's actual tokenizer. `/context` reports the
real token count the harness computed for the current session's Memory files, which will not match the
byte-derived estimate exactly even though both measure the same underlying content.
</details>

3. Which single entry in either file is the largest, and what is the specific reason it is flagged
   rather than left alone?
<details><summary>Answer</summary>
The project file's Folder structure block, at 731 tokens — the largest entry in either file. It is
flagged because a bare directory tree is exactly the kind of content the `/doctor` trim check targets:
material Claude can derive from the codebase itself, such as directory layouts.
</details>

4. Name the three project-file entries that share a single recommended fix, the fix itself, and the
   combined token figure they represent.
<details><summary>Answer</summary>
Generation rules, Audience tier discipline, and Quality bar checklist — all three explicitly marked
"(Day/week pipeline only)" in the project's own text. The fix is one shared `paths:`-scoped rule
targeting `w*/day*-notes.md` and `w*/week*-notes.md`, which would make their combined 590-token cost
zero for any session, such as this one, that never touches those files.
</details>

5. What is wrong with the global file's Document-Driven Development section specifically, as distinct
   from every other "move to a skill" or "move to a rule" verdict in this leaf's tables?
<details><summary>Answer</summary>
It names files (`PROGRESS.md`, `EXECUTION_PLAN.md`, `ARCHITECTURE.md`) this project's own layout does
not use — the project's actual `.claude/CLAUDE.md` specifies `.claude/progress.md`,
`.claude/conventions.md`, and `.claude/workflow.md` instead. Moving this entry to a skill or a
path-scoped rule would not fix the underlying problem; the entry needs to be deleted or rewritten to
match what this project actually does, since relocating it elsewhere still leaves every project that
loads the global file paying for a convention it may not follow.
</details>

6. Why is the SuperClaude Behaviors block a self-inflicted version of the same hazard
   `03-auto-memory.md`'s diagnostic ladder names for contradicting files across scopes?
<details><summary>Answer</summary>
Because it duplicates the hand-written Model Routing and Parallel Execution guidance above it in the
same file, with slightly different numbers and framing in each — the "if two rules contradict each
other, Claude may pick one arbitrarily" hazard, except both halves of the contradiction sit in one
491-line file rather than across, say, a user-scope and a project-scope file.
</details>

7. What single question, applied to any `CLAUDE.md` entry, distinguishes "keep it always-on" from "move
   it to a skill" from "move it to a path-scoped rule"?
<details><summary>Answer</summary>
Does every session need it regardless of what it touches? If yes and it is a standing fact, it stays in
`CLAUDE.md`. If yes but it is a multi-step procedure invoked at a specific moment (spawning an agent,
starting a pipeline run), it moves to a skill. If it only applies to sessions touching specific files
or directories, it moves to a `paths:`-scoped rule.
</details>

## Open questions

- **Unverified:** the ≈$0.48-per-session dollar figure in this leaf's "what this costs" note assumes
  Sonnet's commonly cited list price of $3 per million input tokens as of August 2026. This price was
  not re-verified against any of this topic's re-verifiable doc pages (`settings`,
  `settings-reference`, `memory`), none of which carry model pricing, and actual billed cost for any
  given session depends on the specific model in use, any prompt-caching discount applied, and the
  pricing in effect at the time the session runs.

---

**Leaves covered:** 1.3.29 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 380
