# 21 AI for Coding — skill frontmatter and who may invoke — BASICS (§1.5.6–1.5.10)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [what a skill is](01-basics-what-a-skill-is.md) · Next: [substitution and dynamic injection](03-substitution-and-injection.md)

The previous file established that a custom command *is* a skill in degenerate form, what a
`SKILL.md` is (a markdown file, not code, not a tool, not a plugin), the four discovery locations
and their conflict order, and progressive disclosure — only `description` (+`when_to_use`) sits in
context until the skill fires. This file stays inside that same frontmatter block and finishes it:
the number that governs how many skills' worth of `description` text actually fits in context, every
field the block can hold, the single most consequential wrong belief in this whole subject, the rule
that decides whether the frontmatter is read at all, and the three settings that decide who is even
allowed to invoke a skill.

## §1.5.6 — the listing budget, and what happens past the cut `[DOC]` `[NUM]`

**Concept.** Every session with any skills installed carries a **listing** — one line per skill,
built from its `description` (plus `when_to_use` if set) — that stays resident in context for the
whole session, per §1.5.5. Two different numbers govern how big that listing is allowed to get, and
they are not the same number: a **per-entry cap** on one skill's own text, and a **total pool budget**
across every skill's entries combined.

**Why it exists.** A repository can accumulate dozens of skills over time — personal, project,
plugin, enterprise, all merged into one listing. Nothing stops that count from growing, so Claude
Code needs a hard ceiling on both a single entry's size and the whole listing's size, or a large skill
library would silently eat an ever-larger, unbounded slice of every single turn's context — the exact
always-on cost that progressive disclosure exists to avoid in the first place.

**How it works.** `[DOC]` Two independent limits, confirmed against the current skills page:

1. **Per-entry cap.** "The combined `description` and `when_to_use` text is truncated at **1,536
   characters** in the skill listing to reduce context usage." This applies to one skill's own entry,
   regardless of how many other skills exist. It is configurable with the `skillListingMaxDescChars`
   setting.
2. **Total pool budget.** Separately, the whole listing — every skill's entry, summed — has its own
   ceiling: "The budget scales at 1% of the model's context window." Raise it with the
   `skillListingBudgetFraction` setting (for example `0.02` for 2%) or fix it to an exact character
   count with the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable.

**Clarify a easy-to-conflate pair:** `skillListingMaxDescChars` tunes limit 1 (one entry's cap, default
1,536); `skillListingBudgetFraction` tunes limit 2 (the whole pool, default 1% of the context window).
They are two different dials on two different numbers, not two names for the same setting.

**The practical consequence — this is the point of the leaf.** `[NUM]` When the *total* pool
overflows (many skills, most near their 1,536-character cap), Claude Code does not truncate every
entry a little; it drops full descriptions entirely, "starting with the skills you invoke least, so
the skills you use most keep their full text" — those low-priority entries become **name-only**. A
skill whose trigger phrase — the sentence that was supposed to make Claude recognize "summarize my
diff" or "run the module's tests" — sat in the part of `description` that got cut, silently stops
being auto-invocable. Nothing errors. `/skill-name` still works, because the directory name is not
part of the truncated text; only the model's ability to *find* the skill on its own degrades.

**Code.** `/doctor` reports the listing's real cost; raising the pool budget for a repository that
has outgrown the default looks like this, a complete two-key project settings file:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "skillListingBudgetFraction": 0.02
}
```

**Gotcha:** the `/context` command's Skills row reports the listing size *after* the budget is
applied — before Claude Code v2.1.196 that row instead reported the full, untruncated text of every
description, which could show a number several times larger than what the model actually received.
Reading an old screenshot or a colleague's `/context` output from before that version as if it were
today's real cost overstates the problem.

> The skill listing is capped twice — 1,536 characters per entry (`skillListingMaxDescChars`) and
> roughly 1% of the context window across all entries combined (`skillListingBudgetFraction`) — and a
> skill that loses to the second cap loses its trigger text entirely, not gradually.

## §1.5.7 — every frontmatter field `[DOC]`

**Concept.** A `SKILL.md`'s frontmatter is a flat set of optional `key: value` pairs between two `---`
fences. Twenty fields exist at the target version; every one of them was checked against the current
skills page while writing this leaf, and the syllabus's list of twenty names matches the documentation
table exactly — no field to add, none to drop.

**Why it exists.** Splitting configuration into named, optional fields — instead of one free-text
instruction block — lets the harness enforce the parts that need enforcing (who invokes, what tools
are pre-approved, which model runs) mechanically, outside the model's control, while leaving the body
as plain prose for everything else.

**How it works.** `[DOC]` All twenty, at the target version. Five of them (`context`, `agent`,
`background`, `hooks`, `paths`) get their full mechanism in later files — the fourth column points
forward rather than repeating that material here.

| Field | Accepted values | What it does | Commonly misunderstood |
|---|---|---|---|
| `name` | string | Display label in listings; for a personal/project skill the **directory name**, not this field, is what you type after `/` | Yes — readers assume `name:` sets the invocation command everywhere; it only does for a plugin skill |
| `description` | string (recommended) | What the skill does and when to use it; the primary text Claude matches against your request | Yes — see §1.5.6's truncation cap |
| `when_to_use` | string | Extra trigger phrases/examples, appended to `description` in the listing | No |
| `argument-hint` | string, e.g. `[issue-number]` | Autocomplete display hint only — cosmetic | No |
| `arguments` | space-separated string or YAML list | Names positional arguments for `$name` substitution (file 03) | No |
| `disable-model-invocation` | boolean | Human-only: Claude cannot fire it on its own; also excludes it from subagent skill-preload and from firing when a scheduled task names it | Yes — read as "keeps it out of autocomplete," which is `user-invocable`'s job, not this one |
| `user-invocable` | boolean, default `true` | `false` hides it from `/` entirely and from manual `/name` — model-only | No |
| `allowed-tools` | space/comma string or YAML list | Pre-approves the listed tools for the **invoking turn only** | **Yes — this file's known-defective claim, §1.5.8** |
| `disallowed-tools` | space/comma string or YAML list | Removes the listed tools from the pool while the skill is active, for that turn only | No, once §1.5.8 is read |
| `model` | a `/model` value, or `inherit` | Overrides the model **for the rest of the current turn only** — not saved to settings | Yes — read as a permanent per-skill model pin |
| `effort` | `low` \| `medium` \| `high` \| `xhigh` \| `max` | Overrides effort level while the skill is active | No |
| `context` | `fork` | Runs the skill in a forked subagent instead of inline — full treatment in the subagents area (PART 2) | Pointer forward |
| `agent` | subagent type name | Which subagent type `context: fork` uses — PART 2 | Pointer forward |
| `background` | boolean, default `true`, needs v2.1.218+ | With `context: fork`, `false` waits for the subagent's result inline instead of backgrounding it — PART 2 | Pointer forward |
| `hooks` | object | Registers hooks for the rest of the session once the skill fires — full treatment in the hooks area (PART 2) | Pointer forward |
| `paths` | comma string or YAML list of globs | Gates **automatic** activation to matching files — §1.5.10 | Yes — see §1.5.10's Pitfall |
| `shell` | `bash` (default) \| `powershell` | Which shell runs `` !`command` `` injection lines (file 03) | No |
| `metadata` | free-form YAML map | Your own tooling's key–value data; Claude Code reads nothing from it | No |
| `license` | string | Agent Skills spec field; Claude Code accepts but never acts on it | No |
| `compatibility` | string, ≤500 chars | Agent Skills spec field for environment requirements; accepted, unused by Claude Code | No |

**Code.** A skill using a representative slice of the table — a project convention-checker that only
Claude fires (never a human command), pinned to a cheaper model since the check is mechanical:

```yaml
---
name: java-conventions
description: Checks new or edited Java files against this repository's naming, package, and null-handling conventions. Use automatically after any Java file is written or edited.
disable-model-invocation: false
user-invocable: false
model: haiku
paths: ["**/*.java"]
---

Check the edited Java file against these conventions:
- Package matches the directory under `src/main/java`.
- No field is left uninitialized without an explicit `@Nullable` or a constructor assignment.
- Public methods that can fail declare a specific checked or unchecked exception type, never bare
  `Exception`.

Report violations as a list of `file:line — rule — fix`. Report nothing if the file is clean.
```

`disable-model-invocation: false` (the default, written here only to make the intent explicit) plus
`user-invocable: false` together mean: Claude may fire this on its own, a human never types
`/java-conventions` because there is nothing worth typing it for — the trigger is "a Java file
changed," which `paths` expresses directly (§1.5.10 gives this exact combination its own row).

**Gotcha:** if the YAML between the fences is malformed, Claude Code does not refuse to load the
file — it loads the body with **empty metadata**. `/name` still works, because the command name comes
from the directory, but Claude has no `description` to match your conversation against, so automatic
invocation silently stops. `claude plugin validate .claude/skills` (Claude Code v2.1.233+) catches a
parse error like this; `--debug` shows it too.

> Twenty optional fields, all in the same `---`-fenced block: five control identity and triggering
> (`name`, `description`, `when_to_use`, `argument-hint`, `arguments`), four control who may invoke it
> and with which tools (`disable-model-invocation`, `user-invocable`, `allowed-tools`,
> `disallowed-tools`), four control execution context (`model`, `effort`, `context`, `agent`,
> `background`), one wires session-scoped automation (`hooks`), one gates auto-activation by file
> (`paths`), one picks the injection shell (`shell`), and three are inert outside the open Agent
> Skills spec (`metadata`, `license`, `compatibility`).

## §1.5.8 — `allowed-tools` pre-approves; it does not restrict `[TRAP]` `[DOC]`

**Concept.** `allowed-tools` looks, at a glance, like a sandbox: list `Read` and `Grep`, and surely a
skill so configured cannot touch `Bash`. It cannot do that. `allowed-tools` is a **grant**, not a
**fence**.

**Why it exists.** Some skills run commands a human would otherwise have to approve individually,
every time — `git add`, `git commit`, a project's own build script. Re-approving the same command on
every invocation of a skill that always needs it is friction with no security benefit, so
`allowed-tools` exists to pre-clear exactly those specific tool calls for the turn that invokes the
skill, without touching the permission settings for the rest of the session.

**How it works.** `[DOC]` Quoted directly from the skills page, re-verified immediately before writing
this leaf: "The `allowed-tools` field grants permission for the listed tools during the turn that
invokes the skill, so Claude can use them without prompting you for approval. The grant clears when
you send your next message, even though the skill content stays in context... **It does not restrict
which tools are available: every tool remains callable, and your permission settings still govern
tools that are not listed.**" The field the reader wants for restriction is a different one entirely:
"To remove tools from Claude's available pool while a skill is active, list them in `disallowed-tools`
in the skill's frontmatter. The restriction clears when you send your next message." Two independent
mechanisms, easy to mistake for one: `allowed-tools` widens the pre-approved set for one turn;
`disallowed-tools` narrows the available set for as long as the skill is active, also clearing on the
next message. Neither is permanent, and only the second one removes anything.

One more asymmetry worth carrying forward from §1.4 (permissions): `disallowed-tools` behaves like a
deny rule in one specific respect — "like deny rules, the field can't remove `EndConversation` while
any other tool remains" — the harness will not let a skill strip away the one tool that lets Claude
end the turn cleanly while every other tool is still live.

![D-38 — `allowed-tools` pre-approves for the invoking turn only; `disallowed-tools` is the field that restricts.](../diagrams/D-38-allowed-tools-vs-disallowed-tools.svg)

**D-38** — `allowed-tools` pre-approves for the invoking turn only; `disallowed-tools` is the field
that restricts.

**Code.** A skill whose author believed `allowed-tools` was a sandbox, and the fixed version beside
it:

```yaml
---
name: readonly-reviewer
description: Reviews the open diff for correctness issues without changing any file.
allowed-tools: Read Grep Glob
---

Review the current diff for correctness issues only. Quote the file and line for each finding, most
severe first. Do not modify any file.
```

The prose says "do not modify any file," and `allowed-tools: Read Grep Glob` reads, to most authors,
like it backs that promise mechanically. It does not: `allowed-tools` only pre-clears `Read`, `Grep`,
and `Glob` for the invoking turn — `Bash`, `Write`, and `Edit` are all still callable exactly as your
ordinary permission settings allow them, and if those settings are set to `ask` rather than `deny`,
Claude asking "may I run `Bash(git checkout -- file.java)`" and the human absent-mindedly approving it
defeats the stated intent instantly. The version that actually enforces read-only:

```yaml
---
name: readonly-reviewer
description: Reviews the open diff for correctness issues without changing any file.
allowed-tools: Read Grep Glob
disallowed-tools: Write Edit Bash
---

Review the current diff for correctness issues only. Quote the file and line for each finding, most
severe first.
```

`disallowed-tools: Write Edit Bash` removes exactly those three from the pool for as long as this
skill is active, which is the actual sandboxing mechanism — and per §1.4, a project-level
`permissions.deny` rule for the same tools is the one guarantee here that survives even a compromised
or malicious skill body, because `deny` is enforced by the harness independent of anything the skill's
own frontmatter says about itself.

**Pitfall:** believing `allowed-tools: [Read]` fences a skill to reading files. **Symptom:** the same
skill runs `Bash(rm -rf build/)` mid-session without a second thought, because `allowed-tools`
pre-approved `Read` and left every other tool exactly as available as it always was — nothing in the
skill's frontmatter ever told the harness to remove `Bash`. **Fix:** add the tools you actually want
removed to `disallowed-tools`, or, for a guarantee that holds even against a hostile skill body, add a
`permissions.deny` rule in project settings — the one control in this whole area that is absolute
regardless of what any skill's frontmatter claims about itself.

**Interview:** "Does `allowed-tools: [Read]` mean this skill can only read files?" — one-line answer:
no; it pre-approves `Read` for the invoking turn so it needs no prompt, but every other tool the
session already has permission for stays callable — actual restriction is `disallowed-tools`, or a
`permissions.deny` rule for a guarantee that survives a hostile skill body.

> `allowed-tools` grants pre-approval for the tools it names, for the single turn that invokes the
> skill, and clears on the next message; it never removes any other tool from the pool —
> `disallowed-tools` is the field that does that, for exactly as long as the skill stays active.

## §1.5.9 — the first line rule, and boolean spellings `[DOC]` `[VERSION]` `[TRAP]`

**Concept.** Frontmatter is not "the YAML block near the top of the file" — it is specifically **the
block whose opening `---` is the file's literal first line**. Move that fence down by even one blank
line or one comment, and there is no frontmatter at all: the whole file, fences included, becomes the
skill's body text.

**Why it exists.** The parser needs an unambiguous signal for "frontmatter starts here" rather than
scanning the file looking for something YAML-shaped, because a skill's body is free-form prose that
could itself contain a line that looks like `---` (a markdown horizontal rule, for instance). Anchoring
the rule to line one removes the ambiguity entirely, at the cost of being unforgiving about anything
placed before it.

**How it works.** `[DOC]` Quoted directly, re-verified immediately before writing: "Claude Code reads
the frontmatter only when the opening `---` is the file's first line. Otherwise it treats the whole
file, `---` markers included, as skill content." Boolean-valued fields — `disable-model-invocation`,
`user-invocable`, `background` — accept more spellings than a strict YAML boolean: "Boolean fields
accept `yes`, `no`, `on`, `off`, `1`, and `0` in any letter case, in addition to `true` and `false`."

`[VERSION]` That expanded boolean acceptance is itself version-gated: "Before v2.1.218, Claude Code
recognized only `true` and `false`." At this file's target version (v2.1.2xx, August 2026) the wider
set is already in effect, so `user-invocable: No` and `user-invocable: false` behave identically today
— but a `SKILL.md` written for or tested against a pre-v2.1.218 binary that used `No` would have had
that field silently ignored rather than parsed as a boolean, because the field simply would not have
matched the two spellings that build recognized.

**Code.** A skill file with a stray leading blank line — the exact failure mode this rule produces:

```markdown

---
name: branch-context
description: Explains the naming and protection rules for branches in this repository.
user-invocable: false
---

Branch names follow `<type>/<ticket>-<slug>`; `main` and `release/*` are protected and reject direct
pushes.
```

That leading blank line means position one is not `-`, so Claude Code does not treat this as
frontmatter at all — the entire file, both `---` fences included, becomes the skill's body text.
`name`, `description`, and `user-invocable` are never parsed as fields; they appear to Claude, if the
skill is ever loaded, as four lines of literal markdown. Deleting the blank line so the file begins
with `---name: branch-context` — no, precisely: begins with `---` as line one — restores the intended
parse.

**Gotcha, carried as the Pitfall:** the symptom of this bug is uniquely quiet. There is no parse
error, because there was never an attempt to parse frontmatter in the first place — the file is
perfectly valid markdown, it just is not a skill with any configuration. The skill directory name
still makes `/branch-context` typeable (directory-based naming does not depend on frontmatter at all),
and it appears to work, in the sense that it injects text. What it never does is fire automatically,
because there is no `description` for Claude to match against, and `user-invocable: false` never took
effect either, so nothing about its behavior looks obviously broken until someone specifically asks
"why doesn't Claude ever suggest this on its own."

**Pitfall:** believing a `SKILL.md` with `---` fences "somewhere near the top" has working frontmatter.
**Symptom:** the skill silently has no name override, no description, no trigger — it never fires
automatically, `/skill-name` still works because the directory supplies the command, and nothing in
the harness ever reports an error. **Fix:** the opening `---` must be byte position zero of the file —
no blank line, no comment, nothing — before it; `claude plugin validate` or `--debug` surfaces the
empty-metadata state directly instead of relying on noticing the absence of a behavior.

**Interview:** "What happens if you put a blank line before the frontmatter fence in a `SKILL.md`?" —
one-line answer: nothing parses as frontmatter at all — the whole file, including both `---` lines,
becomes the skill's plain-text body, so the skill loses `description`-based auto-invocation but keeps
its directory-derived `/name`.

> Frontmatter exists only when the file's very first byte begins a `---` fence; anything else and the
> entire file — fences included — is skill content, with no error to announce the difference.

## §1.5.10 — who invokes: three settings, four shapes `[DOC]`

**Concept.** By default a skill has two independent front doors: a human types `/name`, or Claude
matches the conversation against `description` and loads it unprompted. Three frontmatter fields let
an author close either door, or replace the automatic one with a narrower, file-scoped version.

**Why it exists.** Not every skill should be reachable the same way. A deploy procedure has side
effects a human must deliberately trigger; a block of background knowledge about a legacy subsystem is
never something a human types as a command; a convention checker only matters while a specific kind
of file is being touched. One invocation model does not fit all three.

**How it works.** `[DOC]` `disable-model-invocation: true` — quoted: "Only you can invoke the skill.
Use this for workflows with side effects or that you want to control timing, like `/commit`,
`/deploy`, or `/send-slack-message`. You don't want Claude deciding to deploy because your code looks
ready." `user-invocable: false` — quoted: "Only Claude can invoke the skill. Use this for background
knowledge that isn't actionable as a command." `paths:` narrows *automatic* activation only — quoted:
"Claude loads the skill automatically only when working with files matching the patterns" — a human
can still type `/name` for a `paths`-scoped skill outside any matching file; the glob gates when
Claude reaches for it on its own, not whether a person may ask for it directly.

Three independent booleans-and-a-glob, four meaningful combinations:

| `disable-model-invocation` | `user-invocable` | `paths` | Who can invoke, and when | Real use |
|---|---|---|---|---|
| `false` (default) | `true` (default) | unset | Both — human `/name` any time, Claude auto-fires on a `description` match anywhere | `checklist-refresh` — either side may want it, on any file |
| `true` | `true` (default) | unset | Human only, `/name`, any time; Claude never fires it itself | `deploy` — a human must decide the timing, never inferred |
| `false` (default) | `false` | unset | Claude only, auto-fired on a `description` match; no `/name` exists to type | a `legacy-system-context` skill — background knowledge, never a command |
| `false` (default) | `true` (default) | `**/*.java` | Both, but Claude's automatic side only fires while a matching file is in play; `/name` still works anywhere | `java-conventions` (§1.5.7) — auto-checks Java edits, but a human can still ask for the check on demand |

**Code.** The human-only deploy from the docs, complete:

```yaml
---
name: deploy
description: Deploy the application to production.
disable-model-invocation: true
---

Deploy $ARGUMENTS to production:
1. Run the test suite.
2. Build the application.
3. Push to the deployment target.
4. Verify the deployment succeeded.
```

If Claude tries to run the deploy sequence on its own anyway — say, by literally typing out the four
steps as ordinary instructions rather than invoking the skill — that is not `disable-model-invocation`
being bypassed; the field only blocks the skill's *own* automatic invocation. It does not, and cannot,
prevent Claude from independently deciding to run `git push` through ordinary `Bash` calls if your
permission settings allow that. The field closes one specific door, not the destination behind it.

**Gotcha:** setting both `disable-model-invocation: true` and `user-invocable: false` on the same
skill produces a skill nobody and nothing can invoke — not a stricter combination of the other two,
a dead skill. There is no fourth row in the table above for that pairing because it is not a
meaningful configuration; if you find yourself writing both, you almost certainly meant to delete the
skill instead.

**Interview:** "You want a skill only Claude uses, purely as background context, never as a typed
command — which fields?" — one-line answer: `user-invocable: false` alone; `disable-model-invocation`
is the opposite lock (human-only), and combining both disables the skill entirely.

> `disable-model-invocation` removes Claude's automatic door, `user-invocable` removes the human's
> `/name` door, and `paths` narrows Claude's automatic door to files matching a glob without touching
> the human's door at all — three independent locks on two different doors.

## Pitfalls

- **Belief:** "`allowed-tools: [Read]` sandboxes a skill to reading files." **Outcome:** a false sense
  of least privilege — the skill runs `Bash` the moment the session's own permission settings allow
  it, because `allowed-tools` never removed `Bash` from the pool; it only pre-cleared `Read`. **What
  actually gets the guarantee:** `disallowed-tools: [Bash, Write, Edit]` in the skill's frontmatter for
  the duration the skill is active, or a project `permissions.deny` rule for a guarantee that holds
  even against a hostile skill body. **Why people believe it:** the field's name reads as a fence
  ("allowed" implying "and nothing else"), when the mechanism is a grant, not a fence.
- **Belief:** "the frontmatter block is whatever `---`-fenced YAML sits near the top of the file."
  **Outcome:** a skill with a stray blank line, comment, or even a single leading space before the
  opening fence silently has no name override, no description, no trigger — it never auto-fires, and
  nothing errors to say why. **What actually gets the guarantee:** the opening `---` must be the
  file's literal first line; `claude plugin validate` or `--debug` surfaces the empty-metadata state.
  **Why people believe it:** markdown tooling elsewhere is forgiving about leading whitespace and blank
  lines, so the strictness here is not the reader's prior.
- **Belief:** "`model:` in a skill's frontmatter permanently pins that skill to a cheaper or stronger
  model." **Outcome:** confusion when the very next prompt, after the skill's turn ends, is back on
  the session's original model with no explanation. **What actually gets the guarantee:** the override
  lasts only "for the rest of the current turn" and is never written to settings — pin a model for
  every session by setting it in `settings.json` instead. **Why people believe it:** `model:` sitting in
  a persisted file (`SKILL.md`, checked into a repo) reads as persistent configuration by association.

## Cheat sheet

| Fact | Value |
|---|---|
| Per-entry listing cap | 1,536 characters, `description` + `when_to_use` combined; tuned by `skillListingMaxDescChars` |
| Whole-listing pool budget | ~1% of the model's context window by default; tuned by `skillListingBudgetFraction` or `SLASH_COMMAND_TOOL_CHAR_BUDGET` |
| Past the pool budget | Least-invoked skills lose their description entirely (name-only) — `/name` still works, auto-invocation stops silently |
| Frontmatter fields | 20 total: identity/trigger (5), invocation/tools (4), execution context (5), automation (2: `hooks`, `paths`), misc (4) |
| `allowed-tools` | Pre-approves for the invoking turn only; clears next message; does **not** restrict |
| `disallowed-tools` | Removes tools from the pool while the skill is active; clears next message; can't strip the last-remaining `EndConversation` |
| Real restriction | `disallowed-tools` (skill-scoped) or `permissions.deny` (absolute, session-scoped) |
| Frontmatter is read only if | The opening `---` is the file's literal first line — else the whole file is content |
| Boolean spellings | `true/false`, plus `yes/no/on/off/1/0` (any case) since v2.1.218 |
| `disable-model-invocation: true` | Human-only door closed for Claude; also skips subagent preload and scheduled-task firing |
| `user-invocable: false` | Human `/name` door closed; Claude-only |
| `paths:` | Narrows Claude's *automatic* door to matching files; never affects `/name` |
| Both invocation locks set | A dead skill — nobody and nothing can invoke it |

## Self-test

1. Why can a skill with `allowed-tools: [Read]` still successfully call `Bash`?
<details><summary>Answer</summary>
`allowed-tools` only pre-approves the listed tools for the turn that invokes the skill so they need no
prompt — it never removes any other tool from the pool. `Bash` stays exactly as callable as the
session's ordinary permission settings already allow; nothing in `allowed-tools` touches it.
</details>

2. Which field actually removes a tool from what a skill can call, and for how long does the removal
   last?
<details><summary>Answer</summary>
`disallowed-tools`. The restriction applies while the skill is active and clears the moment you send
your next message — like `allowed-tools`, it is scoped to the invocation, not permanent, and it can't
remove `EndConversation` while any other tool still remains.
</details>

3. A `SKILL.md` has a blank line before its opening `---` fence. What does Claude Code do with the
   file?
<details><summary>Answer</summary>
Nothing is parsed as frontmatter — the opening `---` is not the file's first line, so the entire file,
including both `---` markers, is treated as the skill's body content. No `name`, `description`, or any
other field takes effect.
</details>

4. Since which version does `disable-model-invocation: off` behave the same as
   `disable-model-invocation: false`, and what happened before that version?
<details><summary>Answer</summary>
v2.1.218. Before it, Claude Code recognized only the literal `true`/`false` spellings, so `off` would
not have matched either and the field would effectively have been left at its default rather than
being read as `false`.
</details>

5. What is the practical difference between `disable-model-invocation: true` and
   `user-invocable: false`?
<details><summary>Answer</summary>
`disable-model-invocation: true` closes Claude's automatic door only — a human can still type
`/name`. `user-invocable: false` closes the human's `/name` door only — Claude can still auto-invoke
it. Setting both closes every door and makes the skill unreachable by anyone or anything.
</details>

6. A project has thirty skills, most near the 1,536-character per-entry cap, and the combined listing
   exceeds the pool budget. What happens to the skills used least often, and does `/name` still work
   for them?
<details><summary>Answer</summary>
Their descriptions are dropped entirely and they list name-only, so Claude can no longer match the
conversation against them and stops auto-invoking them. `/name` is unaffected — it comes from the
directory name, not from the truncated description text — so a human can still invoke them directly.
</details>

7. Which two frontmatter fields tune the two different listing-size limits, and which limit does each
   one govern?
<details><summary>Answer</summary>
`skillListingMaxDescChars` tunes the per-entry cap (default 1,536 characters, one skill's own
`description` + `when_to_use`). `skillListingBudgetFraction` tunes the total pool budget across every
skill's entries combined (default ~1% of the context window).
</details>

## Open questions

None.

---

**Leaves covered:** 1.5.6–1.5.10 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-38
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 488
