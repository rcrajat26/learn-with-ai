# 21 AI for Coding — three real skills, read closely — BASICS (§1.5.19–1.5.22)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [the content lifecycle and supporting files](04-lifecycle-and-supporting-files.md) · Next: [built-ins, kill switches and the decision table](06-builtins-and-decision-table.md)

The last four files built the model of a skill in the abstract: where it lives, what progressive
disclosure means, the frontmatter fields, `${CLAUDE_PLUGIN_ROOT}` substitution, and how a skill's
content moves through a session. This file spends that model on three skills that exist in a real
production repository — the sdlc-harness — and on one description-writing mistake that is common
enough to earn its own leaf. Everything quoted below was read from disk immediately before being
quoted.

### §1.5.19 — a reference library that costs nothing until needed

**Mental model.** A skill's `references/` folder is a card catalogue, not a bookshelf someone
already pulled every volume off of. The catalogue card (the skill's name and description) sits on
the desk all the time. The volume itself only comes off the shelf when a specific question needs it,
and even then only that one volume — not the whole shelf.

**Why it exists.** A tool with forty commands and ten operational modes cannot fit its full manual
in the always-resident system prompt without taxing every single turn of every conversation for
material that is relevant to almost none of them. Splitting the manual into a thin top-level `SKILL.md`
plus a `references/` folder of narrow, single-purpose files means the always-on cost is the size of
the pointer, not the size of the manual.

**How it works.** The harness's `playwright-cli` skill lives at repo-root
`.claude/skills/playwright-cli/` — **a repo-root skill, not a plugin skill.** The plugin's own three
skills (`bootstrap`, `compose-playbook`, `prod-triage`) live under
`plugins/sdlc-harness/skills/`; `playwright-cli` is a separate, project-scoped skill checked directly
into `.claude/skills/` and must not be filed alongside the plugin's three. Its frontmatter, read and
quoted verbatim:

```yaml
---
name: playwright-cli
description: Automate browser interactions, test web pages and work with Playwright tests.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*) Bash(npm:*)
---
```

`references/` under that same directory holds **nine** files, not the ten the leaf names — a
divergence worth stating plainly rather than padding the count: `element-attributes.md`,
`playwright-tests.md`, `request-mocking.md`, `running-code.md`, `session-management.md`,
`storage-state.md`, `test-generation.md`, `tracing.md`, `video-recording.md`. `SKILL.md`'s own
"Specific tasks" section links all nine by relative path, in the form
`[Storage state (cookies, localStorage)](references/storage-state.md)` — one line per reference file, so the body itself is the index; nothing
outside `SKILL.md` needs to enumerate them.

**The arithmetic.** What sits in context on every single turn, whether or not the skill is ever
used, is the listing entry — the `name` plus `description` line the harness shows the model so it can
decide whether to invoke the skill at all (see `01-basics-what-a-skill-is.md` and D-36 for how that
listing is built). Measuring the two fields above: `playwright-cli` (14 characters) plus `Automate
browser interactions, test web pages and work with Playwright tests.` (76 characters) is 90
characters. At the standard rough estimate of 4 characters per token used throughout this guide,
that is **≈23 tokens**, resident on every turn of every conversation in the project, for as long as
the skill is installed.

Compare that to what the same content would cost if it were not a skill at all — if `SKILL.md`'s
body and the whole `references/` tree were pasted into `CLAUDE.md` and therefore resent on every
turn the way `CLAUDE.md` is (see `04-lifecycle-and-supporting-files.md`). `SKILL.md` itself is 12,587
bytes on disk; the nine reference files sum to 665 + 1,690 + 2,182 + 5,642 + 5,671 + 5,198 + 16,114 +
3,440 + 5,387 = 45,989 bytes. Total: 58,576 bytes ≈ **14,644 tokens**, every single turn.

That is a **≈636×** multiplier (14,644 ÷ 23) between "always-on" and "progressive disclosure",
and it is the whole economic argument for putting a reference library behind a skill rather than in
`CLAUDE.md`: the fat payload is paid exactly once, only in the turn the skill actually fires (the
body, ≈3,147 tokens), and an individual reference file (as small as 665 bytes ≈ 166 tokens for
`element-attributes.md`, as large as 16,114 bytes ≈ 4,029 tokens for `test-generation.md`) is paid
only if the model, mid-task, decides that specific narrow topic is worth a `Read` call.

**Gotcha:** the reference files are not automatically pulled in when `SKILL.md`'s body loads —
loading `SKILL.md` costs its own ≈3,147 tokens, and each `references/*.md` costs its own tokens
again on top, only if and when the model issues a `Read` for that specific file. A skill whose body
front-loads a summary of every reference file inside `SKILL.md` itself (rather than linking out)
defeats the whole point — it pays the `references/` cost on every invocation instead of on the rare
occasion a narrow topic is actually needed.

> A reference library behind a skill costs the size of its listing entry on every turn, the size of
> its body on the turn it fires, and the size of one reference file only when that one file is read.

### §1.5.20 — the `bootstrap` skill: an orchestrator, not a rewrite

**Mental model.** `bootstrap`'s `SKILL.md` is a table of contents for a filing cabinet of shell
scripts, not a novel written from scratch each time someone opens the drawer. The skill body decides
*which* drawer to open and *in what order*; the drawer itself does the actual, deterministic work.

**Why it exists.** Provisioning a development workspace — cloning repositories, writing settings,
installing tools — is exactly the kind of task where "ask the model to figure it out fresh each
time" produces silent drift: one session's model writes the deny-list slightly differently than
another's, one forgets a step under time pressure, and nobody can point to a single tested
implementation when something breaks. `bootstrap` exists to make every one of those steps
deterministic and idempotent, while keeping the handful of genuinely judgment-requiring decisions —
which existing clone to adopt, which service paths to link — inside the conversation.

**How it works.** `plugins/sdlc-harness/skills/bootstrap/SKILL.md`'s frontmatter, quoted verbatim:

```yaml
---
name: bootstrap
description: "Provision everything the sdlc-harness plugin cannot install declaratively: a workspace home (HARNESS_ROOT), the user-scope fail-closed prod-AWS deny-list, the ig-superclaude/mattpocock-skills dependencies, and the full dev-tooling set (handbook, services/ scaffold, pre-commit, glab, LSP servers, Playwright). Feature-complete port of scripts/init-harness.sh -- this is the standard onboarding path going forward."
when_to_use: "Invoke once after installing the sdlc-harness plugin, before the first /run-harness (or any other harness command) in a session. Also invoke to re-check/repair an existing setup -- every step is idempotent, so a re-run only does the work that is still missing."
allowed-tools: [Bash, Read, AskUserQuestion]
---
```

The body opens by naming its own design property, quoted verbatim: "This is an **orchestrator, not
a rewrite** — each step below detects state and delegates to a small deterministic script bundled
with the plugin (`${CLAUDE_PLUGIN_ROOT}/scripts/`). Do not reimplement any of this logic inline; call
the scripts exactly as written, so the decision logic lives in one tested place, not duplicated
across every session that runs this skill."

The leaf asks for the "why deterministic scripts and not model judgment" paragraph, quoted verbatim
exactly as it appears — its wording is "why deterministic scripts and not model judgment", bolded as
its own lead-in inside the body, not a separate heading:

> **Why deterministic scripts and not model judgment:** resolving paths, merging JSON, and creating
> symlinks all have a single correct answer given the inputs — there is no ambiguity for a model to
> resolve. The only genuinely agentic parts are asking the user *which* existing clones/paths to use
> (step 1, if no adopt candidate is found, and step 4's service-linking) — everything else, including
> step 3's handbook provisioning, is mechanical/mandatory and must not be re-derived or turned into a
> question by the assistant on every run.

That paragraph is the design rule this whole skill is organized around: a step either has one
correct answer given its inputs (delegate to a script) or it does not (ask the user, and only then).
The body's own numbered steps (0, 1, 3, 3a, 3b, 4, 4b, 4c, 5, 6, 6b–6g, 7) each name the script they
delegate to. The scripts live under `plugins/sdlc-harness/scripts/` — **not `hooks/`**, which holds
an entirely different family (`check-init.sh`, the `prod-guard-*.sh` trio, `doc-update-reminder.sh`,
`calibration-nudge.sh`) invoked by `hooks.json` on session and tool events rather than by a skill
body. `scripts/` holds fifteen `bootstrap-*.sh` files plus three `triage-*.sh` files. Several named
by the leaf and confirmed on disk: `bootstrap-uv.sh` (step 0, installs `uv`), `bootstrap-user-scope.sh`
(step 5, writes the fail-closed prod-AWS deny-list to `~/.claude/settings.json`), `bootstrap-lsp.sh`
(step 6e, installs `pyright-langserver`, `typescript-language-server`, `jdtls`), and
`bootstrap-write-version.sh` (step 7, stamps the content-hash marker `check-init.sh` reads on the
next session).

**What would break without it.** If step 5 — writing the prod-AWS deny-list — were described in
prose instead ("write the deny markers and these three env keys to the user's settings file") rather
than delegated to `bootstrap-user-scope.sh`, every session that ever ran `bootstrap` would be
free to phrase that JSON merge slightly differently: a different key order, a dropped existing
`permissions.deny` entry the user already had, a scope written to project instead of user (exactly
the mistake the skill's own Gotchas section calls out — project scope is silently ignored the moment
the session's working directory leaves `HARNESS_ROOT`). A tested script either lands the same bytes
every time or exits non-zero and says why; a model re-deriving JSON-merge logic from a paragraph of
prose has no such guarantee, and a fail-closed safety control — this is the control that keeps
`prod-guard-bash.sh` able to block a mutating AWS command against production — cannot rest on "the
model probably phrased it the same way as last time."

**Connecting to §1.5.8.** The prior file established that a skill's `allowed-tools` field
*pre-approves* a set of tools for the invoking turn — it does not fence the skill body to only
those tools, and it clears on the next user message. `bootstrap`'s frontmatter reads
`allowed-tools: [Bash, Read, AskUserQuestion]`. Reading this file honestly means not concluding that
`bootstrap` is somehow sandboxed to running shell commands, reading files, and asking questions and
nothing else — every other tool available in the session (`Edit`, `Write`, `WebFetch`, whatever
else the session has) stays callable throughout the skill's execution; `Bash`, `Read`, and
`AskUserQuestion` are simply pre-approved so the fifteen-plus `bash "${CLAUDE_PLUGIN_ROOT}/scripts/…"`
calls this skill's own body issues do not each stop for a fresh permission prompt. The field is a
convenience grant, not a capability boundary — and `bootstrap`'s own design (delegate everything with
one correct answer to a script; ask the user only for genuine judgment calls) is precisely the kind
of skill where that distinction matters least in practice, because the body was written to need
almost nothing beyond those three tools anyway — but the field itself does not enforce that; the
author's discipline does.

**No gotcha beyond the one just stated: the rule has no further surprising edge here** — this leaf's
gotcha *is* the §1.5.8 connection above, so it is not repeated as a separate beat.

> `bootstrap` is a skill body that never performs a state-mutating action itself; it detects state
> and calls a tested `bootstrap-*.sh` for every step that has one correct answer, and asks the user
> only for the steps that do not.

### §1.5.21 — prompt composition without duplication

**Mental model.** `/implement-story` is a thin shim bolted onto `/run-conductor`'s full body, the
way a specialized REST endpoint might delegate its entire implementation to a shared service method
and only override the handful of parameters that make it specialized — never re-typing the shared
method's logic at the call site.

**Why it exists.** Two command files that describe the same underlying mechanism — here, driving a
feature workspace through the RFC 0006 deterministic conductor — will drift the moment either one is
edited without the other. A bug fix, a new ACTION kind, a clarified gotcha applied to only one of the
two copies silently becomes a lie about the other. The fix is the same one covered in
`03-substitution-and-injection.md` for dynamic content: **one canonical source, injected verbatim,
plus a thin, explicit delta.**

**How it works.** `plugins/sdlc-harness/commands/implement-story.md` inlines
`plugins/sdlc-harness/commands/run-conductor.md` with a ` ```! ` injection block, quoted verbatim:

````
```!
cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"
```
````

This is the same `${CLAUDE_PLUGIN_ROOT}`-substitution and shell-injection mechanism
`03-substitution-and-injection.md` already taught, applied here to compose one prompt file's body
out of another's rather than out of a script's stdout. When `/implement-story` is invoked, the
harness resolves `${CLAUDE_PLUGIN_ROOT}` to the plugin's install path, runs the `cat`, and splices
`run-conductor.md`'s full text into the rendered prompt before the model ever sees it — the model
receives `/run-conductor`'s entire five-ACTION-kind loop (`exec`, `dispatch_headless`,
`dispatch_interactive`, `checkpoint`, `done`) as if it had been retyped, without either file's
maintainer having retyped it.

`implement-story.md` then states only what it changes, quoted verbatim:

```
## Binding overrides (the ONLY things this wrapper adds over the run-conductor spec above)

- The harness target is FIXED to `implement-story`: every `conductor
  init` this wrapper issues passes `--playbook implement-story`.
  Ignore run-conductor.md's `--playbook <name>` argument entirely — there is
  no playbook to select here, and it is never resolved from $ARGUMENTS.
- This wrapper binds `implement-story` to the **conductor** executor
  (`/run-conductor`), not the prose executor (`/run-harness`) — the two are
  not interchangeable, and the routing decision for every stage in this
  playbook comes back from `conductor advance` exactly as run-conductor.md
  describes.

### Forwarded flags

Pass through unchanged to the run-conductor flow above, exactly as
`/run-conductor` itself would consume them:

- `--feature <name>` — the feature workspace slug (same meaning as
  run-conductor.md's own `--feature`/`features/<slug>` positional).
- `--from <stage>` — forwarded as-is toward resuming an existing run; the
  conductor derives the actual in-flight stage from folded run state
  (`--run-id` against the shared `features/<slug>/state/harness.db`), never
  from this flag directly.

### Rejected flags

`implement-story` runs through the conductor executor, which does not yet
have a documented executor-level contract for these — each MUST be rejected
with an explicit error naming the flag — never silently ignored or
reinterpreted:

- `--resume-at <stage>` — reject. The conductor has no stage-injection
  resume; use `--run-id <id>` (against the same feature's `harness.db`) to
  resume a run at whatever stage `conductor advance` derives from folded
  state.
- `--main-pipeline-id <id>` — reject. This threaded an already-running CI
  pipeline id into the prose flow's `dev_pipeline`/`mr_deploy_and_watch`
  hand-off; the conductor CLI has a `conductor init --main-pipeline-id` flag
  (AP-12738 AC6), but this wrapper does not yet forward it — extending
  run-conductor.md's own executor spec to use it is separate follow-on work,
  not part of this shortcut.
- `--dry-run` — reject. There is no conductor dry-run mode; every `conductor
  init`/`conductor advance` call has a real, recorded effect on the run's
  state db.
- `--override-pull` — reject. This waived the prose flow's own service-repo
  pre-pull step; the conductor executor has no such step to waive.
```

**The design property.** This is DRY applied to prompts rather than to code: one canonical
description of "how the conductor loop works" (`run-conductor.md`), read fresh on every invocation of
either command, plus a thin delta file that states nothing more than what is different about the
specialized case. Without the injection, `implement-story.md` would need its own full copy of the
five-ACTION-kind loop — the `exec`/`monitor` branching, the `dispatch_headless` envelope handling, the
checkpoint decision vocabulary — and the next time `run-conductor.md` gained a sixth ACTION kind or
fixed a wording bug in how `--token` is described, the two files would silently disagree about how
the same mechanism works, with no compiler or test to catch it. The injection makes that
impossible by construction: there is exactly one place the loop is described, and every consumer of
it reads that place at render time.

**Rejected flags, and why refusing beats approximating.** The interesting design choice is not the
forwarded flags — those are the easy case, a straight pass-through. It is the four *rejected* flags.
Each of `--resume-at`, `--main-pipeline-id`, `--dry-run`, and `--override-pull` existed as a real,
meaningful flag on the older prose executor (`/run-harness`), and each one maps to *nothing* the
conductor executor currently supports: no stage-injection resume mechanism, no forwarded
pipeline-id plumbing, no dry-run mode, no pre-pull step to waive. `implement-story.md` could have
quietly accepted any of the four and either silently dropped it or tried to approximate its old
behavior with the nearest conductor primitive. It does neither — it names each flag and rejects it
with an explicit error. An approximated `--dry-run` that actually still mutates `harness.db` is worse
than no flag at all, because the caller believes they got the safety property the flag's name
promises and did not. A rejected flag fails loudly, at the point of the mistake, in a form the caller
can act on; an approximated one fails silently, later, in a form that looks like a bug in something
else entirely.

**Gotcha:** the injection block runs `cat` at **render time**, once, when `/implement-story` is
invoked — not at plugin-install time and not on every keystroke while the reader is typing the
command's arguments. If `run-conductor.md` is edited after a long-running `/implement-story`
invocation has already rendered its prompt for that turn, the change takes effect on the *next*
invocation, not retroactively on the current one — the same one-shot substitution timing
`03-substitution-and-injection.md` established for `${CLAUDE_PLUGIN_ROOT}` and for `` ```! `` blocks
generally (see D-39b in that file).

> Prompt composition without duplication means one file states the mechanism in full and every
> specialized caller injects it verbatim, then states only its overrides, its forwarded flags, and
> the flags it explicitly refuses rather than approximates.

### §1.5.22 `[TRAP]` — a description that names the topic, not the trigger

**Pitfall:** a skill's `description` field is the only text the model sees when deciding whether to
invoke that skill — the listing built from every installed skill's `name` and `description`, as
`01-basics-what-a-skill-is.md` and `02-frontmatter-and-invocation.md` already established, and
truncated at **1,536 characters** per entry. A description that states *what the skill covers*
rather than *when to reach for it* gives the model no way to distinguish "the user's message is
about this subject" from "the user's message needs this tool invoked right now." The failure runs in
both directions: a description so broad it matches almost any message about the topic makes the
skill fire on requests it should not touch (effectively always-on); a description so narrow or
so abstractly worded that it never matches a real user phrasing makes the skill invisible — installed,
correctly written, and never once invoked.

Three real bad descriptions, rewritten, each connected to a listing mechanism a reader now knows:

| # | Bad (names the topic) | Why it fails the listing | Good (names the trigger) |
|---|---|---|---|
| 1 | `"Playwright browser automation."` | Reads as a subject-matter tag, not a decision rule — the model has to guess whether "check if the login page renders" counts as "browser automation" | `"Automate browser interactions, test web pages and work with Playwright tests."` (the harness's actual `playwright-cli` description, §1.5.19) — it names concrete actions (automate, test, interact) a request would actually ask for |
| 2 | `"Bootstrap and provisioning helper."` | Vague enough to match almost any setup-shaped request, including ones this specific skill cannot help with (e.g. provisioning an unrelated CI runner), risking an always-on false trigger that burns the skill's body tokens on the wrong task | `"Provision everything the sdlc-harness plugin cannot install declaratively: a workspace home (HARNESS_ROOT), the user-scope fail-closed prod-AWS deny-list, the ig-superclaude/mattpocock-skills dependencies, and the full dev-tooling set…"` (the harness's actual `bootstrap` description, §1.5.20) — it names the exact artefacts this skill provisions, so a request about an unrelated tool does not match |
| 3 | `"Deterministic conductor execution model documentation."` | Reads like a section title from a design doc, not something any engineer would type — the model has no trigger phrase to pattern-match against, so the skill sits installed and never fires | `"Run a feature through the RFC 0006 deterministic conductor — a thin five-branch executor over \`conductor init\`/\`conductor advance\`, piloted on implement-story-lite."` (the harness's actual `/run-conductor` description, §1.5.21) — it states the action a caller performs (run a feature through the conductor) rather than the concept the command implements |

**Fix:** write the description as the sentence a caller's actual request would need to match against
— actions and artefacts, not subject headings — and keep it inside the 1,536-character listing
budget, because the model chooses which skill to invoke from that listing text alone, never from the
skill's full body (which is not loaded until after the choice is made).

---

**No diagram of its own.** This row draws nothing new: D-36 (progressive disclosure — see
`01-basics-what-a-skill-is.md`) explains why §1.5.19's arithmetic works the way it does, D-37 (the
skill/command hierarchy) is the picture behind repo-root vs. plugin-scoped skills in §1.5.19, D-38
(`allowed-tools` vs. `disallowed-tools`) is the mechanism §1.5.20 connects back to §1.5.8, and D-39b
(substitution runs once) is the timing gotcha closing §1.5.21. No SVG link applies to this file — all
four are referenced by id in the four preceding files, not re-embedded here.

## Pitfalls

1. Believing `.claude/skills/playwright-cli/` is a plugin skill because it sits in a `.claude/`
   tree the way plugin-provided skills do. The plugin's own three skills are `bootstrap`,
   `compose-playbook`, and `prod-triage` under `plugins/sdlc-harness/skills/`; `playwright-cli` is a
   separate, repo-root, project-scoped skill. Check the path prefix, not the presence of a
   `SKILL.md`. **Why people believe it:** both shapes use the identical `SKILL.md` file format and
   frontmatter, so nothing about the file's *contents* signals which scope it was installed at.
2. Believing `bootstrap`'s `allowed-tools: [Bash, Read, AskUserQuestion]` means the skill cannot use
   any other tool. It pre-approves those three for the invoking turn; every other tool the session
   already has stays callable, and the grant clears on the next user message (§1.5.8). Check
   `disallowed-tools` if the intent is an actual restriction. **Why people believe it:** the field
   name and its position right next to `name`/`description` read like a capability manifest, the
   way a Java method's declared checked exceptions read like an exhaustive list of what can go
   wrong.
3. Believing a vague, subject-naming skill description ("browser automation", "provisioning helper")
   is more discoverable because it "covers more ground." It does the opposite — the model matches
   descriptions against the actual wording of a request, so a description with no concrete trigger
   phrase either never matches or matches everything, neither of which is discoverability. Write the
   description as the action a real request performs. **Why people believe it:** description fields
   elsewhere (a Javadoc summary, a README's opening line) reward broad topic statements; a skill
   description is closer to a search-engine query match than to documentation prose.

## Cheat sheet

| Case | File(s) | Claim | Verified number |
|---|---|---|---|
| `playwright-cli` | `.claude/skills/playwright-cli/SKILL.md` + `references/` (9 files) | reference library costs nothing until needed | listing ≈23 tokens vs. always-on ≈14,644 tokens (≈636×) |
| `bootstrap` | `plugins/sdlc-harness/skills/bootstrap/SKILL.md` | orchestrator, not a rewrite | 15 `bootstrap-*.sh` + 3 `triage-*.sh` under `scripts/`, not `hooks/` |
| `implement-story` / `run-conductor` | `plugins/sdlc-harness/commands/{implement-story,run-conductor}.md` | prompt composition without duplication | ` ```! ` block running `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"` |
| description trap | any `SKILL.md` | trigger, not topic | listing truncated at 1,536 characters per entry |

## Self-test

1. Is `.claude/skills/playwright-cli/` a plugin skill or a repo-root skill, and how do you tell?
<details><summary>Answer</summary>Repo-root, project-scoped skill — it lives at `.claude/skills/playwright-cli/`, not under `plugins/sdlc-harness/skills/` where the plugin's own three skills (`bootstrap`, `compose-playbook`, `prod-triage`) live. The `SKILL.md` format is identical either way, so scope is determined by the path prefix, not the file's contents.</details>

2. Why does putting a large reference library behind a skill's `references/` folder cost less than
   pasting the same material into `CLAUDE.md`?
<details><summary>Answer</summary>`CLAUDE.md` is resent on every turn in full. A skill's listing entry (name + description, ≈23 tokens for `playwright-cli`) is what is resident on every turn instead; the skill's body (≈3,147 tokens for `SKILL.md`) is paid only on the turn the skill actually fires, and each individual reference file is paid only if and when the model issues a `Read` for that specific file. The full tree pasted into `CLAUDE.md` would cost ≈14,644 tokens on every single turn regardless of relevance.</details>

3. What does `bootstrap`'s own body name as the two genuinely agentic decisions, versus everything
   else?
<details><summary>Answer</summary>Asking the user which existing clone/path to adopt (step 1, when no adopt candidate is found) and step 4's service-linking. Everything else, including step 3's handbook provisioning, is mechanical and mandatory — delegated to a script, never turned into a question.</details>

4. Where do `bootstrap-*.sh` scripts live, and what is the common wrong guess?
<details><summary>Answer</summary>`plugins/sdlc-harness/scripts/` — fifteen `bootstrap-*.sh` files plus three `triage-*.sh` files. The common wrong guess is `hooks/`, which instead holds `check-init.sh`, the `prod-guard-*.sh` trio, `doc-update-reminder.sh`, and `calibration-nudge.sh` — a different family invoked by `hooks.json` on session/tool events, not by a skill body.</details>

5. Does `bootstrap`'s `allowed-tools: [Bash, Read, AskUserQuestion]` restrict the skill to only those
   three tools?
<details><summary>Answer</summary>No. `allowed-tools` pre-approves those three for the invoking turn so the skill's many `bash "${CLAUDE_PLUGIN_ROOT}/scripts/…"` calls do not each stop for a permission prompt; every other tool already available in the session stays callable, and the grant clears on the next user message. `disallowed-tools` is the field that actually removes a tool's availability.</details>

6. What mechanism does `/implement-story` use to avoid retyping `/run-conductor`'s full loop, and
   when does that mechanism actually run?
<details><summary>Answer</summary>A ` ```! ` injection block running `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, which splices that file's full text into the rendered prompt. It runs once, at render time, when `/implement-story` is invoked — not at install time and not retroactively if `run-conductor.md` is edited mid-run.</details>

7. Name one flag `/implement-story` rejects rather than forwards or approximates, and explain why
   rejecting is the right call.
<details><summary>Answer</summary>`--dry-run` — the conductor executor has no dry-run mode; every `conductor init`/`conductor advance` call has a real, recorded effect on the run's state db. Approximating a dry-run (e.g. silently no-op'ing some calls) would let the caller believe they got a safety property they did not actually get, which is worse than an explicit, immediate rejection naming the flag.</details>

8. Why does `"Bootstrap and provisioning helper."` make a poor skill description even though it is
   accurate?
<details><summary>Answer</summary>It names the topic, not a trigger — it is vague enough to match almost any setup-shaped request, including ones the skill cannot actually help with, risking an always-on false match that consumes the skill's body tokens on the wrong task. The model matches the listing description against the literal wording of a request, so the description needs to name concrete actions and artefacts, not a category label.</details>

## Open questions

None.

---

**Leaves covered:** 1.5.19–1.5.22 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — this row's mechanisms are drawn by D-36 to D-40 in the four preceding files
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 399
