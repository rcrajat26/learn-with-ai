# 21 AI for Coding — built-ins, kill switches and the decision table — BASICS (§1.5.23–1.5.26)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [three real skills, read closely](05-cases.md) · Next: [PARTs 0 and 1 — the interview wrap-up](../90-interview-basics.md)

The last file grounded the whole model of a skill in real production files. This file closes PART 1
with the inventory that most reference material gets wrong — which command is a built-in and which is
a skill wearing a slash — the two switches that turn a skill's visibility off, one real skill built and
sized for this exact repository, and the decision table that the last five files (and the four subjects
before them — `.claude` tree, settings, memory, permissions) have all been building toward.

### §1.5.23 — built-ins vs. bundled skills: not the same kind of thing `[DOC]` `[RESEARCH]`

**Concept.** Every slash command the CLI accepts falls into exactly one of two kinds, and the split is
not cosmetic. Re-verified against the `commands` reference page immediately before writing this leaf
(the syllabus names `skills` and `cli-reference`; the actual command-by-command table lives at
`/docs/en/commands`, which both of those pages point to — noted here rather than silently substituted).
The page states the split itself: "Most are built-in commands whose behavior is coded into the CLI,"
and marks the rest inline with a **[Skill]** or **[Workflow]** tag — "a bundled skill... works like
skills you write yourself: a prompt handed to Claude."

**Why it exists.** A built-in like `/model` or `/permissions` opens an interactive interface or flips
an internal flag the CLI's own compiled code implements — there is no prose for the model to read or
misread, because the model is not involved in running it. A bundled skill like `/code-review` is,
underneath the slash, an ordinary `SKILL.md`-shaped prompt Anthropic ships with the product — the model
reads it and executes it the same way it would execute a project skill with the same shape. Collapsing
this into one flat list of "built-in commands" hides which of the two a reader is looking at.

**How it works.** `[DOC]` The table below is every command the syllabus named, re-verified row by row
against the live page rather than assumed from memory:

| Command | Kind | What it does |
|---|---|---|
| `/help` | Built-in | Show help and available commands |
| `/compact` | Built-in | Summarize the conversation so far to free context |
| `/clear` | Built-in | Start a new conversation with empty context (aliases `/reset`, `/new`) |
| `/context` | Built-in | Visualize current context usage as a colored grid |
| `/config` | Built-in | Open the Settings interface, or set `key=value` directly (alias `/settings`) |
| `/permissions` | Built-in | Manage allow/ask/deny rules (alias `/allowed-tools`) |
| `/hooks` | Built-in | View hook configurations for tool events |
| `/memory` | Built-in | Edit `CLAUDE.md` files, manage auto memory |
| `/init` | Built-in | Initialize a project with a `CLAUDE.md` guide |
| `/plugin` | Built-in | Manage plugins — list, install, enable, disable |
| `/agents` | Built-in | Manage subagent configurations (as of v2.1.198, prints a reminder rather than opening a UI) |
| `/cd` | Built-in | Move the session to a new working directory |
| `/add-dir` | Built-in | Add a working directory for file access |
| `/model` | Built-in | Switch the AI model |
| `/effort` | Built-in | Set the effort level (`low` through `xhigh`, `max`, `auto`) |
| `/run` | Built-in | Run a shell command and stream output in — no tool call, no permission ask |
| `/doctor` | **Bundled skill** | Setup checkup: diagnoses install problems, unused skills/MCP servers, slow hooks (alias `/checkup`) |
| `/rewind` | **Bundled skill** | Roll code and conversation back to a checkpoint |
| `/code-review` | **Bundled skill** | Review a diff, PR, branch, or path for correctness bugs and cleanup (alias `/review`) |
| `/security-review` | **Bundled skill** | Review the diff for security vulnerabilities |
| `/loop` | **Bundled skill** | Run a prompt repeatedly while the session stays open (alias `/proactive`) |

Sixteen built-ins, five bundled skills, twenty-one commands total in this inventory — not exhaustive
of the full command reference, but every one the syllabus named, correctly sorted.

**The correction worth stating plainly.** The syllabus that seeded this row placed `/doctor` and
`/rewind` among the built-ins and `/run` among the bundled skills. The live page says the opposite:
`/doctor` and `/rewind` both carry the **[Skill]** tag, and `/run` carries no tag at all — it is coded
into the CLI. This is exactly the kind of drift a `[RESEARCH]` tag exists to catch: the two commands
that *look* most like core plumbing (a health check, a time-travel control) turned out to be prompts,
and the one that looks most like "just a bundled convenience" turned out to be compiled behavior.

**Insight:** the practical test for which kind a command is has nothing to do with how it feels to use
and everything to do with §1.5.24 below — **only a bundled skill can be overridden by a same-named
project skill (§1.5.3's conflict order) or switched off by `disableBundledSkills`.** A built-in like
`/permissions` or `/model` cannot be shadowed by writing a skill named `permissions`; the CLI's own
compiled dispatch always wins that name. If you can't tell which kind a command is from its behavior,
try to override it — only one of the two will let you.

**Gotcha:** `/run`'s own listing is the sharpest illustration of "built-in" not meaning "safe" —
because the model never sees the command text and gets no chance to ask permission before it runs, a
`/run rm -rf node_modules` executes with no `tool_use` block, no permission prompt, and no entry a
`PreToolUse` hook (PART 2) could intercept, the same "bypasses the ordinary tool path" shape as
`` !`command` `` injection from `04-lifecycle-and-supporting-files.md` and this file's own
`03-substitution-and-injection.md`.

> A built-in command is compiled behavior the CLI dispatches directly; a bundled skill is a prompt
> Anthropic ships and the model executes — and only the second kind can be overridden or disabled.

### §1.5.24 — the visibility and kill switches `[DOC]`

**Concept.** Four settings decide whether a skill is seen or heard from at all, and they operate at
three different points: hiding a listing, turning off a whole category, stopping a sync, and killing
every slash command outright.

**How it works.** `[DOC]` Re-verified against `settings-reference` immediately before writing:

| Key | What it turns off | Scope | What the reader sees afterward |
|---|---|---|---|
| `skillOverrides` | Hides or collapses **one named skill's** visibility, without touching its `SKILL.md` on disk | Any settings file — resolves through the same five-layer precedence stack as every other setting (`01-basics-files-and-precedence.md`, D-20), not the four-location skill-discovery order of §1.5.3 | The named skill stops appearing in the listing (or appears collapsed); the file is untouched, so removing the override brings it straight back |
| `disableBundledSkills` | Turns off **every** bundled skill and bundled workflow that ships with Claude Code | Any settings file | `/code-review`, `/security-review`, `/loop`, `/doctor`, `/rewind` and the rest of §1.5.23's second table all stop resolving; built-ins are untouched because they were never in that category |
| `syncClaudeAiSkills` | Stops downloading the skills enabled on the user's `claude.ai` account and hides ones already synced | User, local, or managed settings only | Skills that used to appear from the claude.ai sync silently stop appearing; nothing local is deleted |
| `--disable-slash-commands` | Disables **all skills and commands** for the session — the CLI's own phrasing | CLI flag, session-scoped only, not a settings key | Every slash command, built-in and skill alike, stops resolving for that one invocation of `claude` |

`skillOverrides` is the one worth holding next to §1.5.3's four-location conflict order rather than
confusing with it: §1.5.3 decides **which skill wins the name** when two locations both define
`deploy`; `skillOverrides` is a separate settings key that decides **whether a resolved skill is shown
at all**, and it climbs the *settings* precedence stack (managed beats project-local beats
project-shared beats user, per D-20) rather than the *skill-discovery* stack (enterprise beats personal
beats project). Two different orderings, both "higher authority wins," easy to conflate, worth keeping
apart the same way §1.5.3 already warned not to carry its own rule forward into PART 2's subagent
precedence.

**Gotcha:** `disableBundledSkills` and `--disable-slash-commands` look like the same lever at different
strengths, but they are not nested — `disableBundledSkills` is scoped to the bundled category only
(your own project and personal skills keep working), while `--disable-slash-commands` is a blunt,
session-only flag that takes down a project's own `deploy` skill exactly as thoroughly as it takes down
`/code-review`. An org that wants "no bundled skills, but our own skills still work" reaches for the
settings key; a one-off debugging session that wants "nothing but raw conversation" reaches for the
flag.

> The visibility and kill switches operate at three different granularities — one skill
> (`skillOverrides`), one category (`disableBundledSkills`, `syncClaudeAiSkills`), or everything
> (`--disable-slash-commands`) — and none of them edit the files they affect.

### §1.5.25 — a real skill for this repository `[BUILD]` `[PROVE]`

**Concept.** This guide's own note sets, this one included, end each subject in a `92-interview-*.md`
file with a flat atomic-concept checklist — `src/notes/detailed/java-collections/`'s version is split
across `92a`–`92d` files and pins its own format rule: "one bullet per concept, `- <concept name>`, no
nesting, no trailing punctuation, no parentheses, no tier markers." That checklist is handwritten today
and drifts the moment a subject folder gains or loses a `###` heading. `checklist-refresh` is a project
skill that regenerates it from what is actually on disk.

**Why it exists.** A checklist is a procedure — walk every subject file, list every primary-concept
heading, rewrite one section — which is exactly what §1.5.26 below calls out as a skill's job, not a
`CLAUDE.md` fact and not a hook's must-happen. Nobody needs this to run on every keystroke; a writer
needs it on demand, after finishing a batch of files, which is the invoke-when-asked shape a skill is
built for.

**The artefact.** A complete `SKILL.md`, every field shown, using `$topic` (a named argument, per
§1.5.11), one inline `` !`command` `` injection, and a `references/` file:

```yaml
---
name: checklist-refresh
description: Regenerate a topic guide's atomic-concept checklist in src/notes/detailed/<topic>/ from the ### concept headings that actually exist on disk, so the checklist never drifts from the notes it indexes.
argument-hint: <topic-slug>
arguments: [topic]
allowed-tools: Bash(find:*) Bash(grep:*) Read Edit
---

## Where the checklist lives

**Concept files found:** !`find src/notes/detailed/$topic -mindepth 1 -name "*.md" ! -name "00-index.md" ! -regex '.*/9[0-9].*' | wc -l`

The atomic-concept checklist for topic `$topic` sits under a `## Atomic concept checklist` heading
inside whichever `9[0-9]*.md` file in `src/notes/detailed/$topic/` carries that exact heading — most
topics keep it at the end of `92-interview-internals.md`; a topic split across `92a`-`92d` files
(see `references/checklist-format.md`) keeps it in the last one instead. Find that file with
`grep -rl "## Atomic concept checklist" src/notes/detailed/$topic/`.

## Your task

1. List every subject-folder `.md` file under `src/notes/detailed/$topic/` — every file except
   `00-index.md` and the `9[0-9]*` interview/checklist files themselves (the count above already
   told you how many exist).
2. For each file, extract every `###`-level heading in the order it appears — each one names exactly
   one primary concept.
3. Read `references/checklist-format.md` and follow its bullet format exactly.
4. Open the checklist file located above and replace everything between `## Atomic concept checklist`
   and the next `---` with one freshly generated `- <concept name>` bullet per heading found in step 2,
   in the same folder order and file order as step 1's listing. Preserve every other section of that
   file untouched.
5. Report which concept names were added and which were removed relative to the previous version —
   never silently overwrite without saying what changed.

Do not touch any file outside `src/notes/detailed/$topic/`. Do not invent a concept that has no
`###` heading backing it.
```

And the `references/checklist-format.md` the skill's step 3 reads:

```markdown
# Checklist bullet format — pinned

This is the machine-readable surface of a topic's note set; downstream tooling parses it, so the
format below is not a style preference, it is a contract.

- One bullet per concept: `- <concept name>`.
- No nesting — every bullet sits at the top level, regardless of which subfolder its concept lives in.
- No trailing punctuation, no parentheses, no tier markers (`[BOTH]`, `[STAFF]`, etc.) in the bullet
  text itself — the checklist is tier-blind by design.
- Sort order: by subject subfolder, in the order that subfolder was written, then by the order the
  concept's heading appears inside that file.
- A concept name is the heading text itself, lowercased only where the heading was already
  lowercase-first (do not force-lowercase a proper noun or an API name like `TreeMap` or `SKILL.md`).

## Self-test before publishing a regenerated checklist

Read a bullet in isolation and say the mechanism out loud in one sentence, from memory, with the
source file closed. Any bullet you cannot do this for means the concept file under-explains that
heading, not that the checklist is wrong — go fix the file, then rerun this skill.
```

**The prove step.** The frontmatter's `allowed-tools` pre-approves exactly the four tool patterns the
body uses — no wildcard `Bash(*)` — so `/checklist-refresh 21-ai-for-coding` runs its `find` and its
`Read`/`Edit` calls without a permission prompt. The inline injection is not a claim: running the exact
command from the skill's body against this repository, right now, prints a real number:

```
$ find src/notes/detailed/21-ai-for-coding -mindepth 1 -name "*.md" ! -name "00-index.md" ! -regex '.*/9[0-9].*' | wc -l
25
```

That is the number `$topic` = `21-ai-for-coding` would see inlined into the skill's very first line —
proof the injection expands against real state, not a placeholder left for the model to interpret.

For the listing-versus-body split §1.5.19 already put a name to, measuring the real files on disk
rather than estimating them: the frontmatter's `name` (17 characters) plus `description` (198
characters) is 215 characters ≈ **54 tokens** at this guide's 4-characters-per-token estimate — that is
the only cost `/context` charges every single turn while the skill sits installed, whether or not it
ever fires. `SKILL.md` itself is 2,131 bytes ≈ **≈533 tokens**, paid once, only on the turn
`/checklist-refresh` actually runs. `references/checklist-format.md` is 1,339 bytes ≈ **≈335 tokens**,
paid only if that turn's `Read` for it actually happens — step 3 of the body, not automatic.

**Unverified:** I could not drive an interactive `/context` screen inside this writing session to
capture its literal before/after grid — there is no live Claude Code session available to this task for
that. The 54/533/335-token figures above are derived the same way `/context` itself derives them: real
byte counts off the files shown, through this guide's own 4-characters-per-token estimate, which
`05-cases.md` (§1.5.19) already used and cross-checked for the `playwright-cli` skill. Recorded in
`## Open questions`.

**What this costs.** At Sonnet 5's baseline **$2 per million input tokens** (this guide's
`ground-zero/01-basics-what-the-model-is.md`): the standing listing cost is 54 tokens × every turn of
every conversation in a project where this skill is installed — for a project running roughly 1,000
turns before its next `/clear`, that is 54,000 tokens ≈ **$0.108** for a skill that may never once fire.
The per-invocation body cost is a separate, one-time number: 533 tokens ≈ **$0.00107** each time
`/checklist-refresh` actually runs, plus another 335 tokens ≈ **$0.00067** on the invocations where the
model also reads the reference file. The standing cost scales with how long the project lives; the
body cost scales with how often the checklist is actually regenerated — conflating the two, as a bare
"a skill costs about half a cent" claim would, hides that one of them is paid whether you use the tool
or not.

### §1.5.26 — the decision table `[NUM]`

**Concept.** Six needs, six mechanisms, one axis this guide has stated twice already without turning
it into a procedure: `[BOTH]` §1.3.2 and this subject's own `04-lifecycle-and-supporting-files.md`
(§1.5.15) both established that an instruction file is *context* — Claude reads it and tries — while
only a hook is a *guarantee* the harness itself enforces. Six mechanisms below, each rated on that same
axis.

**How it works.** `[NUM]` Six rows, no more, no fewer:

| Need | Mechanism | Enforcement strength | Full treatment |
|---|---|---|---|
| A fact true everywhere, always | `CLAUDE.md` | Context — Claude reads it and tries | `memory/01-basics-claude-md.md` |
| A fact scoped to one file type | Path-scoped rule (`.claude/rules/`) | Context — narrows *when* the text appears, not *whether* it's obeyed | `memory/04-your-own-instruction-files.md` |
| A procedure — named steps, invoked on demand | Skill (`SKILL.md`) | Context — text injected on invocation; the model still executes it turn by turn | this file set, §1.5.1–1.5.26 |
| A must-happen, no exceptions | Hook | **Guaranteed** — the harness runs the command itself and can block on its exit code | `hooks/01-basics-what-a-hook-is.md` (PART 2) |
| Verbose work in, a small answer needed out | Subagent | Structural guarantee on the *return shape* (only the final message crosses back); the subagent's own brief is still context it can misread | `subagents/01-basics-definition-and-precedence.md` (PART 2) |
| Distribution of any of the above to a team | Plugin | Inherits whatever it packages — a plugin bundling a hook is guaranteed, one bundling only a skill is still context | `plugins/01-basics-structure.md` (PART 2) |

![D-41 — Which mechanism for which need. Each terminal carries its enforcement strength: context, or guaranteed.](../diagrams/D-41-mechanism-decision-tree.svg)

**D-41** — Which mechanism for which need. Each terminal carries its enforcement strength: context, or
guaranteed.

**Worked examples**, each run through the same procedure — ask what kind of need it is first, only then
pick the mechanism:

1. *"Every commit must pass `mvn test` before it lands — no exceptions."* This is a must-happen. A
   `CLAUDE.md` line saying "run tests before committing" is context — under time pressure or a long
   context window, the model can and does skip it, exactly the failure §1.3.2 already named. The
   correct answer is a `PreToolUse` hook on the `git commit` pattern that exits non-zero until tests
   pass — guaranteed, because the harness blocks the tool call itself rather than asking the model to
   remember.
2. *"Java code in this repo uses records, not classes with hand-written getters."* True everywhere,
   no file-type qualifier — `CLAUDE.md`.
3. *"Every `.tf` file must run through `terraform fmt` before it's considered done."* Scoped to one
   file type — a path-scoped rule in `.claude/rules/`, not a blanket `CLAUDE.md` line every non-Terraform
   file would also have to skip past.
4. *"Regenerate the checklist after a batch of notes files changes."* A named procedure invoked when a
   writer decides a batch is done — §1.5.25's `checklist-refresh`, a skill. **Pitfall:** the wrong
   belief is that phrasing it as "whenever a notes file changes, regenerate the checklist" turns it into
   the same skill — it does not, because "whenever X changes" is a must-happen trigger a skill cannot
   supply on its own; a skill only runs when named, on demand. Getting the *automatic* version of this
   requires pairing an automatic trigger — a hook on the write event — with the skill's steps, or moving
   the whole procedure into the hook's own script. **Why people believe it:** a skill's body reads like
   an instruction that could fire on any trigger, and nothing about `SKILL.md`'s shape signals that
   invocation is always a deliberate, named act.
5. *"Send the full `mvn test -X` output to Claude but keep only pass/fail plus the failing class names
   in the parent's context."* Verbose in, small answer out — a subagent, per this guide's own repeated
   framing of context isolation across the settings and memory subjects.
6. *"Every team in the org should get the same commit-message hook and the same `deploy` skill,
   versioned together."* Distribution, not a new enforcement need — a plugin, which packages the hook
   (guaranteed) and the skill (context) as one unit rather than asking each team to hand-copy files.

**Interview:** asked "when do you reach for a hook instead of just writing the instruction into
`CLAUDE.md`?" — the one-line answer is "when the instruction has to survive being ignored," because a
hook is the only mechanism on this table the harness runs regardless of what the model decided to pay
attention to that turn.

> Six needs, six mechanisms — `CLAUDE.md`, a path-scoped rule, a skill, a hook, a subagent, a plugin —
> and exactly one of the six, the hook, is enforced by the harness rather than merely read by the model.

## Pitfalls

- **Belief in action:** "I renamed my project skill `doctor` so it replaces the built-in health check."
  **Surprising outcome:** nothing happens — `/doctor` is itself a bundled *skill*, so a project `doctor`
  skill does correctly shadow it per §1.5.3's conflict order, but the same trick against a genuine
  built-in like `/permissions` or `/model` silently fails, because compiled dispatch never consults the
  skill-discovery locations at all. **What actually gets the guarantee:** check §1.5.23's table first —
  only a **[Skill]**-tagged command can be shadowed or disabled; a built-in cannot, at any scope.
  **Why people believe it:** every command looks identical at the prompt — same `/name`, same tab
  completion — so nothing in ordinary use exposes which of the two kinds it is.
- **Belief in action:** "A `CLAUDE.md` line telling Claude to always run the linter before finishing is
  the same guarantee as a hook." **Surprising outcome:** it is read, considered, and sometimes skipped —
  there is no error, no log entry, nothing that tells the reader it didn't happen. **What actually gets
  the guarantee:** a `PostToolUse` or `Stop` hook that runs the linter itself and blocks on failure.
  **Why people believe it:** the instruction reads exactly like a rule, and most of the time the model
  does follow it, so the gap only surfaces under exactly the conditions — a long session, a rushed turn —
  where the guarantee mattered most.

## Cheat sheet

| Item | Fact |
|---|---|
| Built-ins in this inventory | 16: `/help /compact /clear /context /config /permissions /hooks /memory /init /plugin /agents /cd /add-dir /model /effort /run` |
| Bundled skills in this inventory | 5: `/doctor /rewind /code-review /security-review /loop` |
| Only skills can be… | Overridden by a same-named skill (§1.5.3), or turned off by `disableBundledSkills` |
| `skillOverrides` | Hides/collapses one named skill; settings-precedence scoped (D-20) |
| `disableBundledSkills` | Kills every bundled skill/workflow; built-ins unaffected |
| `syncClaudeAiSkills` | Stops claude.ai skill sync; user/local/managed only |
| `--disable-slash-commands` | Kills *everything*, built-in and skill alike; session-only CLI flag |
| `checklist-refresh` standing cost | ≈54 tokens/turn (name+description), every turn, whether or not it fires |
| `checklist-refresh` invocation cost | ≈533 tokens body + ≈335 tokens if `references/` is read |
| Six mechanisms | `CLAUDE.md`, path-scoped rule, skill, hook, subagent, plugin |
| Only guaranteed mechanism | Hook — the harness runs it and can block on its exit code |

## Self-test

1. Which two commands does the live documentation classify as bundled skills that the syllabus for
   this leaf placed among the built-ins, and which one does it classify the other way?
<details><summary>Answer</summary>`/doctor` and `/rewind` are both bundled skills (tagged **[Skill]**),
not built-ins. `/run` is the reverse case — the syllabus grouped it with the bundled skills, but it
carries no tag and is coded directly into the CLI.</details>

2. Why can a project skill named `permissions` never shadow the built-in `/permissions`?
<details><summary>Answer</summary>Only a same-named *bundled skill* can be overridden by a project,
personal, or enterprise skill — that conflict rule (§1.5.3) only applies within the skill-discovery
system. A built-in command is dispatched by compiled CLI code that never consults skill-discovery
locations at all, so there is no name to collide with.</details>

3. What is the difference in scope between `disableBundledSkills` and `--disable-slash-commands`?
<details><summary>Answer</summary>`disableBundledSkills` is a settings key scoped to the bundled-skill
category only — a project's own skills keep working. `--disable-slash-commands` is a session-only CLI
flag that disables every skill and command, bundled or not, built-in or not, for that one invocation.
</details>

4. `skillOverrides` and §1.5.3's conflict order both implement "higher authority wins." Why are they
not the same stack?
<details><summary>Answer</summary>§1.5.3's order (enterprise beats personal beats project) decides
which skill among several same-named ones is discovered and run at all. `skillOverrides` is a settings
key that climbs the separate five-layer settings-precedence stack (D-20: managed beats project-local
beats project-shared beats user) to decide whether an already-resolved skill is shown in the listing.
</details>

5. In `checklist-refresh`'s frontmatter, what does `allowed-tools: Bash(find:*) Bash(grep:*) Read Edit`
buy the skill's author, and what would a bare `Bash(*)` have cost instead?
<details><summary>Answer</summary>It pre-approves exactly the four call shapes the body actually uses,
so the skill runs with no permission prompt while staying auditable — a reviewer can see the whole
blast radius from the frontmatter alone. `Bash(*)` would pre-approve every shell command the skill
might ever be tricked into running, trading a one-line audit for an unbounded one.</details>

6. A skill's standing cost and its body cost are two different numbers. Which one does a project pay
even if `checklist-refresh` never runs, and which one only shows up on the turn it fires?
<details><summary>Answer</summary>The listing cost — the `name` plus `description`, ≈54 tokens here —
is resident every single turn regardless of use. The body cost, ≈533 tokens for `SKILL.md` plus ≈335
more if `references/checklist-format.md` is read, is paid only on the turn the skill actually
invokes.</details>

7. Why is a "whenever a file changes, regenerate the checklist" instruction not something
`checklist-refresh` can supply on its own?
<details><summary>Answer</summary>A skill only ever runs on deliberate, named invocation (`/checklist-refresh <topic>`) or when the model decides mid-task that it applies — it has no automatic
trigger tied to a file-change event. "Whenever X happens" is a must-happen, which belongs to a hook;
pairing a hook's trigger with the skill's steps (or moving the steps into the hook's own script) is
what actually makes it automatic.</details>

8. Of the six mechanisms in the decision table, which one's enforcement strength depends on what it
happens to contain, rather than being fixed?
<details><summary>Answer</summary>The plugin. It is a distribution and packaging mechanism, not a new
enforcement primitive — a plugin that bundles a hook inherits the hook's guarantee, while one that
bundles only a skill or a `CLAUDE.md` snippet inherits that mechanism's context-level enforcement
instead.</details>

## Open questions

- **Unverified:** the exact `/context` before/after token deltas for `checklist-refresh` were computed
  from real on-disk byte counts and this guide's established 4-characters-per-token estimate, not read
  off a live interactive `/context` screen — no live Claude Code session was available inside this
  writing task to drive one. The underlying file sizes (2,131 bytes for `SKILL.md`, 1,339 bytes for
  `references/checklist-format.md`, 215 characters for the frontmatter listing) are real, measured
  values.

---

**Leaves covered:** 1.5.23–1.5.26 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-41
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 405
