# 21 — AI for Coding: Claude Code as an Engineered System

Scope: Claude Code treated the way you'd treat any runtime you depend on — what the agent loop
actually does per turn, where its configuration lives and in what precedence, the five distinct
channels that put bytes into the context window, and how to drive it non-interactively from a
program. The worked example throughout is a real system: the **sdlc-harness** at
`~/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness`, a Python engine that orchestrates
`claude -p` subprocesses across the software development lifecycle.

This guide is mechanism-first like the other twenty. The interview value is not "I use Claude Code"
— every candidate says that. It is being able to explain *why a context window is a budget you
design against*, and *when a step must be a shell script rather than a prompt*.

---

## 1. The mental model: a stateless model inside a stateful loop

The model itself is a pure function: `(prompt tokens) -> (output tokens)`. It has no memory, no
filesystem, no network. Everything else is harness.

One **turn** is:

1. The harness assembles a request: system prompt + tool schemas + full conversation so far + the
   new user message.
2. The model emits either text (done) or a **tool_use** block (a function call it wants run).
3. The harness executes the tool, appends the result as a **tool_result** message, and loops to 1.

Three consequences fall straight out of this and explain almost every behaviour you will observe:

| Fact | Consequence |
|---|---|
| The whole conversation is re-sent every turn | Cost and latency grow with conversation length, not with the last message |
| The model cannot see anything not in the transcript | "It forgot" is nearly always "it was never in context" or "it was compacted out" |
| The model chooses tools from schemas alone | A tool with a vague description is a tool that gets called wrongly |

**Trap:** treating the agent as a process with state. It is a *replayed transcript*. A subagent
started fresh knows nothing your main session learned — which is exactly why the harness's
`progress-verifier` agent is fed `git log` and diff-stat text inside its task string rather than
being pointed at "the coder's session".

### The context window is a budget, not a container

A 200K window with autocompaction at 75% gives roughly 150K usable. Spend it on the wrong things —
a 4 MB log file catted into the transcript, a 900-file `find`, whole JDK sources — and the useful
signal gets summarised away. Two structural fixes, both of which the harness uses:

- **Isolation** — run verbose work (test suites, large reads, exploration) in a subagent whose
  transcript is discarded, and return only a verdict. This is the single biggest lever.
- **Precision over breadth** — an LSP symbol lookup costs a few hundred tokens where reading and
  grepping three files costs tens of thousands. The harness's `check-init.sh` hook nudges engineers
  to install `pyright-langserver`, `typescript-language-server` and `jdtls` for exactly this reason,
  and is explicit that it is a token-cost argument, not a correctness one.

---

## 2. Anatomy of the `.claude` folder

`.claude/` is configuration-as-code: a conventional directory the CLI discovers by walking from the
working directory upward, plus a user-level twin at `~/.claude/`.

```
.claude/
├── settings.json          # shared, committed: permissions, hooks, env, enabled plugins
├── settings.local.json    # personal, gitignored: machine-specific overrides
├── CLAUDE.md              # always-loaded project memory (the "constitution")
├── commands/<name>.md     # slash commands  ->  /name
├── agents/<name>.md       # subagent definitions
├── skills/<name>/SKILL.md # progressively-loaded skills
└── hooks/*.sh             # scripts the harness (not the model) executes on events
```

The real harness in the example project has exactly this shape: nine command files under
`.claude/commands/` (`implement-story.md`, `run-conductor.md`, `calibrate.md`, …) and a
`playwright-cli` skill with a `references/` subfolder.

### Scope precedence

Configuration resolves in layers, later winning over earlier:

Configuration resolves in layers. **Highest first** — a key set higher wins:

| Precedence | Layer | Location | Committed? |
|---|---|---|---|
| 1 | Managed policy | OS-level managed path, MDM, or the console | by IT |
| 2 | Command line | `claude --settings`, `--permission-mode`, … | n/a |
| 3 | Project (local) | `<repo>/.claude/settings.local.json` | no (gitignore) |
| 4 | Project (shared) | `<repo>/.claude/settings.json` | **yes** |
| 5 | User | `~/.claude/settings.json` | no |

**Trap:** the command line does *not* win outright — managed settings outrank it. And for
permissions specifically, a **deny at any level cannot be overridden by any other level**, including
`--allowedTools`.

**Trap:** putting a personal permission grant in `settings.json` and committing it. Anything that
grants your teammates' agents new powers belongs in review; anything machine-specific belongs in
`settings.local.json`.

### `settings.json` — the keys that matter

```json
{
  "permissions": {
    "allow": ["Read(**)", "Edit(**)", "Bash(*)", "mcp__atlassian-cloud__*"],
    "deny":  ["Bash(rm -rf *)", "Read(./.env)"]
  },
  "enabledPlugins": { "sdlc-harness@sdlc-harness": true },
  "hooks":  { "PostToolUse": [ /* see §6 */ ] },
  "env":    { "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "75" }
}
```

That `permissions` block is the real one from the harness repo. Note what it implies: a *deny* rule
is the load-bearing safety mechanism, and deny beats allow. The harness pairs `Bash(*)` with a
destructive-command deny-list — and there is an incident (AP-11470, referenced in
`engine/agent.py`) whose entire root cause was that deny-list **failing to load** in a spawned
agent. More on that in §7; it is the best interview story in this guide.

**Permission modes** change how the loop treats an un-matched tool call:

| Mode | Behaviour |
|---|---|
| `default` (labelled *Manual*, alias `manual`) | prompt on first use of each tool not allow-listed |
| `acceptEdits` | auto-accept file edits **plus** common filesystem commands (`mkdir`, `touch`, `mv`, `cp`) for paths in the working directory or `additionalDirectories`; still prompt for everything else |
| `plan` | read-only exploration; no source-file edits |
| `auto` | a background classifier reviews tool calls instead of you |
| `dontAsk` | auto-**deny** anything not pre-approved by an allow rule |
| `bypassPermissions` | no prompts, except for protected paths such as `.git` and `.claude` — only defensible in a container or VM |

Note what `acceptEdits` does *not* cover: `mvn`, `git commit`, `chmod`, `java`. That gap is the
symptom in the incident in §7.

---

## 3. How context is supplied — the five channels

This is the section to actually internalise. There are five distinct mechanisms, and they differ on
one axis: **when the tokens enter the window.**

| # | Channel | Loaded | Cost when unused |
|---|---|---|---|
| 1 | **System prompt** (built-in + `--append-system-prompt`) | every request | always paid |
| 2 | **`CLAUDE.md` memory** | session start, every request thereafter | always paid |
| 3 | **Slash commands** (`.claude/commands/*.md`) | when invoked | ~0 (name + description only) |
| 4 | **Skills** (`SKILL.md`) | when the description matches the task | ~0 until triggered |
| 5 | **Tool results** (Read/Bash/MCP/subagent reports) | mid-turn, on demand | ~0 |

### Channel 1 & 2 — the always-on tax

`CLAUDE.md` is prepended to context for the entire session. Everything in it is rent you pay on
every single turn. That is why it should hold only rules that apply to ≥80% of work; a 2,000-line
`CLAUDE.md` is a self-inflicted context leak. The harness repo's own is 441 lines.

`--append-system-prompt` appends to the *default* system prompt. It is additive context, **not** a
persona swap — a distinction `engine/agent.py` documents explicitly, and §5 explains why it matters.

### Channel 3 — slash commands are prompt templates

A command file is markdown with optional frontmatter, expanded into the conversation when you type
`/name`:

```markdown
---
description: "Run implement-story through the deterministic conductor."
argument-hint: "features/<workspace> [--from <stage>] [--dry-run]"
---
# /implement-story
Run the feature workspace through the conductor. Arguments: $ARGUMENTS
```

`$ARGUMENTS` interpolates what the user typed. Commands can also **inline other files' contents at
expansion time** — the real `/implement-story` composes itself out of `/run-conductor` with:

````markdown
```!
cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"
```
````

…then states only its own overrides. That is DRY applied to prompts: one executor spec, many thin
pre-bound wrappers. `${CLAUDE_PLUGIN_ROOT}` is the plugin's own install directory, which is *not*
the repo — see the trap in §8.

### Channel 4 — skills and progressive disclosure

A skill is a folder with a `SKILL.md` whose frontmatter is the only part loaded up front:

```yaml
---
name: bootstrap
description: "Provision everything the plugin cannot install declaratively…"
when_to_use: "Invoke once after installing the plugin, before the first /run-harness…"
allowed-tools: [Bash, Read, AskUserQuestion]
---
```

The body — and any `references/` files it points to — loads only when the skill fires. This is
**progressive disclosure**: 50 skills can be installed at near-zero standing token cost, whereas 50
skills' worth of text in `CLAUDE.md` would consume the window before you typed anything.

**Trap:** `allowed-tools` **pre-approves; it does not restrict.** It grants permission for the
listed tools during the turn that invokes the skill, so Claude uses them without prompting, and the
grant clears on your next message. Every other tool stays callable. The field that removes tools is
`disallowed-tools`.

**Trap:** writing a skill description that describes the *topic* ("about testing") instead of the
*trigger* ("when the user asks to run or fix a failing test suite"). The description is the only
thing the model routes on; a topical description makes the skill invisible or, worse, always-on.

### Channel 5 — tool results, and the subagent as a context firewall

Every `Read`, `Bash`, `Grep` and MCP call injects its output into the transcript. This is where
context goes to die. A subagent is the firewall: it gets its own window, burns 200K exploring, and
returns 200 words. The project convention in this repo — *agents write findings to files, and return
only status + 3 findings + a path* — is that principle as a rule.

---

## 4. Subagents

An agent definition is markdown-with-frontmatter under `.claude/agents/` (or a plugin's `agents/`):

```markdown
---
name: progress-verifier
description: >
  Judges whether a coder that just exhausted its turn allotment mid-story is
  genuinely advancing toward the story's acceptance criteria or is stalled.
  Evidence is artifacts only: git log, diff stat, relayed milestones.
---
Read your system prompt at: harness/control-plane/agent-prompts/progress-verifier.md
Then read the rubric you score against: .../judge-rubrics/progress-verifier.yaml
Finish your FINAL message with exactly one verdict line:
    ## Progress Verdict: progressing|stalled
```

Four design properties are visible in that 20-line file, and all four are transferable:

1. **The body is a pointer, not the content.** The heavy prompt lives in a separate versioned file;
   the agent definition stays cheap to load and easy to diff.
2. **A structured output contract.** "Finish with exactly one verdict line" makes the reply
   machine-parseable — the calling engine greps for it. An agent whose output must be read by code
   needs a grammar, not a vibe.
3. **Explicit write boundaries.** The sibling `calibrator` agent enumerates the two paths it may
   write and the four it may not, and states plainly: *"No Jira API tool is ever given to this
   agent."* Capability is denied at the tool layer, and the prose merely documents it.
4. **Evidence discipline.** The verifier judges artifacts only and is forbidden from inspecting the
   coder's live session. That keeps its verdict reproducible from stored state.

### When a subagent earns its cost

Subagents cost roughly 2× the tokens of doing the work inline, because context must be re-supplied.
Spend that when:

- the work is **verbose but the answer is small** (test runs, builds, codebase sweeps);
- the work is **genuinely parallel with non-overlapping writes**;
- you need a **different capability set** (a read-only auditor, a no-network reviewer).

Do not spend it for a task whose whole output you'd have to read anyway.

**Trap:** parallel agents writing into the same directory. Lanes must partition the *filesystem*,
not just the topic. This repo learned it the hard way: note-writing lanes were folder-scoped but the
`diagrams/` folder was flat, so two lanes owned the same slug and one silently overwrote the other,
leaving a diagram that contradicted its own page. **One writer per output path, ever.**

---

## 5. Personas: `--agent` vs `--append-system-prompt`

These look interchangeable and are not.

- `--agent <name>` loads a **registered** agent definition — its full system prompt, model, and tool
  allow-list. This is the parity mechanism for auto-spawning a subagent programmatically.
- `--append-system-prompt <text>` **appends to the default** system prompt. The default persona is
  still there; you have decorated it, not replaced it.

`engine/agent.py` says this outright, and its `load_agent_prompt()` helper does one extra thing worth
copying: it **strips the `--- … ---` frontmatter** before appending, because YAML metadata leaking
into a system prompt is noise the model will try to interpret.

---

## 6. Hooks — deterministic code on lifecycle events

A hook is a shell command **the harness runs**, not something the model decides to run. That is the
whole point: hooks are the only way to guarantee something happens.

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command",
                    "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh\"" }] }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [{ "type": "command",
                    "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/doc-update-reminder.sh\"" }] }
    ]
  }
}
```

Common events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`,
`SubagentStop`. `matcher` is a regex over the tool name. Hooks receive JSON on stdin (tool name,
inputs, session paths) and communicate back through **stdout** (surfaced to the model as context)
and **exit code** — a non-zero `PreToolUse` exit blocks the call, which is how you build a guard
that the model cannot talk its way past. The harness ships `prod-guard-bash.sh` on exactly this
seam.

Look at what `check-init.sh` actually emits — every line is a tagged instruction *to the model*:

```
[HANDBOOK_ACTIVE] ig-markets is the active handbook platform. To switch, run /sdlc-harness:handbook.
[CLI_TOOLS_MISSING] Tell the user: 'Required CLI tools are missing: glab (…), aws (…).'
[LSP_SERVERS_SUGGESTED] Tell the user once, non-blocking: …
```

That is channel-5 context injection driven by *ground truth on the machine* — is `glab`
authenticated, is a handbook MCP server registered, does the bootstrap content-hash match — rather
than by anything the model believes. Note also that the script ends `exit 0` and starts `set +e`: a
crashing advisory hook must not break the session.

**Trap (a real incident, worth memorising):** this hook used to auto-reindex a RAG store on every
session start, with no cross-session coordination. Every concurrent session independently decided a
reindex was due, spawning hundreds of embedder processes, 100+ GB of partial indexes, and machines
that could not recover — *because starting a session was the trigger for the next pile-up*. Hooks
run on **every** session, including the ten you open in parallel. Anything expensive or stateful in
a `SessionStart` hook needs a lock or must not be there at all.

---

## 7. Driving Claude Code from a program (headless mode)

This is the part that separates "I use the CLI" from "I built a system on it". The one-liner:

```bash
claude -p "<task>" --output-format json --max-turns 160 --permission-mode acceptEdits
```

`-p` is print/non-interactive: one prompt in, an envelope out. With `--output-format json` you get a
machine-readable result carrying the text, cost, token counts, an `is_error` flag and a
`session_id`. The harness's `run_agent()` composes exactly this, and its flag set is a good checklist
of what a production wrapper needs:

| Flag | Purpose |
|---|---|
| `--agent <name>` | load a registered persona (§5) |
| `--output-format json` | parseable envelope with cost/tokens/session_id |
| `--max-turns <n>` | agent-turn cap — the runaway-cost backstop |
| `--permission-mode <mode>` | default `acceptEdits` in the harness |
| `--setting-sources <list>` | **which config layers to load at all** (default `user,project`) |
| `--settings <path>` | load a settings file by absolute path, independent of `cwd` |
| `--model` / `--effort` | capability/cost tier per step |
| `--add-dir <path>` | extend the writable workspace beyond `cwd` |
| `--append-system-prompt` | additive context (§5) |
| `--resume <session_id>` | continue a prior stateless session |
| `--max-budget-usd <n>` | hard dollar ceiling for this invocation |

### Two independent stop conditions

`--max-turns` bounds *agency*; the subprocess `timeout` bounds *wall clock*. You need both, and they
fail differently. The harness sets 160 turns / 1800 s, and the comment above the constant is an
honest artefact: it was 40, then 80, then raised to 160 after a dogfood run where the coder produced
13 green tests and a correct fix but **exhausted its turns before reaching a commit — $5.16 for zero
landed work.** A fresh story's first leg is disproportionately reads and exploration, not a runaway.
Both are overridable per-run by env (`HARNESS_AGENT_MAX_TURNS`, `HARNESS_AGENT_TIMEOUT`) so tuning
never requires a code change.

### The AP-11470 lesson: `--setting-sources` resolves against `cwd`

`--setting-sources project` loads `<cwd>/.claude/settings.json`. The harness runs each coder inside an
**isolated per-story git worktree**, so `cwd` was the worktree — not the harness repo. Result: the
harness's own `permissions.allow` (`Bash(*)`) *and* its destructive-command deny-list never loaded,
and the agent ran with bare `acceptEdits` defaults — able to read, edit, `mkdir`, `mv`, `sed`, but
**not** `mvn`, `git commit`, `chmod` or `java`. The fix was `--settings <absolute path>`, which is
evaluated independently of `cwd`.

Two general lessons, both interview-grade: **configuration discovered by directory walk breaks the
moment you change directories**, and **a permission model that silently degrades to defaults is
worse than one that fails loudly** — the symptom here was a competent agent mysteriously unable to
build.

### Parsing: never trust the envelope

`extract_json_envelope()` pulls the JSON object out of stdout and, on failure, preserves a 500-char
snippet of what was actually printed. The reason is recorded in a calibration finding: a zero-cost
envelope failure was previously only diagnosable by reproducing it interactively. **When you parse a
subprocess's output, capture the unparseable input** — otherwise your error path destroys the only
evidence.

### Retries, and what "error" means

The loop retries on timeout/`OSError` and on error envelopes, keeping the *last parsed* error so
cost and token counts survive. Distinguish three failure classes, because they need different
handling: launch/timeout (infrastructure), unparseable envelope (contract), and `is_error` (the agent
itself failed).

---

## 8. Plugins and marketplaces

A **plugin** packages commands, agents, skills, hooks and scripts for distribution:

```
plugins/sdlc-harness/
├── .claude-plugin/plugin.json   # name, version, description, dependencies
├── commands/  agents/  skills/  scripts/
└── hooks/hooks.json
```

A **marketplace** is a `.claude-plugin/marketplace.json` listing installable plugins, added by an
engineer via `/plugin marketplace add`. Plugins may declare `dependencies` on plugins in *other*
marketplaces, but only if the depended-on marketplace is named in
`allowCrossMarketplaceDependenciesOn` — Claude Code refuses to auto-add a marketplace the user has
not explicitly trusted. `settings.json`'s `enabledPlugins` then gates which installed plugins are
live per project.

**Trap:** `${CLAUDE_PLUGIN_ROOT}` is the plugin's install location — a cache directory — not the
repo you are working in. A hook ported from `<repo>/.claude/hooks/` into a plugin cannot keep
resolving the repo root as `dirname "$0"/../..`; the harness's ported hooks resolve
`HARNESS_ROOT` → `git rev-parse --show-toplevel` instead, and **refuse with a clear message** rather
than guessing a third fallback. Path assumptions are the number-one porting bug when a `.claude`
folder becomes a plugin.

**Trap:** an unresolved plugin dependency is nearly silent — you get a cryptic `/reload-plugins`
error. `claude plugin list --json` exposes a per-plugin `errors` array; the harness checks it every
session start and surfaces it, which is the pattern to copy for any dependency the tool resolves
lazily.

---

## 9. Deterministic vs agentic — the actual engineering judgment

The most senior idea in this whole guide, and it is stated in the harness's own `bootstrap` skill:

> **Why deterministic scripts and not model judgment:** resolving paths, merging JSON, and creating
> symlinks all have a single correct answer given the inputs — there is no ambiguity for a model to
> resolve.

So the skill is an **orchestrator, not a rewrite**: each step detects state and delegates to a small,
tested `bootstrap-*.sh`. The only genuinely agentic steps are the ones that ask a human *which* path
to adopt. The decision rule:

| Signal | Build it as |
|---|---|
| One correct answer given the inputs | a script (deterministic, testable, free, idempotent) |
| Judgment, ambiguity, natural language, or synthesis across sources | a prompt |
| Must happen regardless of what the model decides | a hook |
| Verbose input, small output | a subagent |
| Needs human authority (filing, deploying, deleting) | a confirmation gate, tool denied to the agent |

Corollaries visible in the same codebase: the calibrator agent is **never given the Jira tool**
because filing needs a human; and content hashes replace hand-maintained version constants, so
nothing needs bumping when a step is edited.

---

## 10. Verification: the AI-specific failure mode

An agent produces plausible artefacts. Plausible is the problem — it makes review the bottleneck and
the default review (skimming a diff) worst-matched to it. Two laws this repo paid for:

- **Re-run every published listing in its published form.** This found more defects than every
  structural check combined: code that no longer produced the transcript printed beneath it,
  invented values that compiled fine, a repro returning the *opposite* of the claim, and
  run-specific numbers published as constants.
- **A checker whose input can switch it off is worse than no checker.** One generated file contained
  a literal NUL byte, so `file` classified it as `data` and `grep` returned *nothing* — not a
  mismatch, nothing. Every text-based check silently skipped it and reported success. Assert
  text-ness before any grep-based gate.

Generalised: **verify from final state, never from a pre-write computation**, and prefer executable
evidence (a compile, a test, a transcript) over structural evidence (a regex over a file).

---

## 11. Interview framing

Expect "how do you use AI in your workflow?" as a culture-fit probe with a real technical answer
underneath. Answer in system terms, not tool terms.

**Senior IC altitude** — mechanism fluency: the agent loop and why cost scales with transcript
length; `CLAUDE.md` as always-paid context versus skills as progressive disclosure; subagents as
context isolation; hooks as the deterministic escape hatch; `-p --output-format json` for
scripting; and one concrete bug you diagnosed (`--setting-sources` resolving against a worktree
`cwd` is a perfect one).

**Staff altitude** — the platform argument: AI capability shipped as a *versioned, dependency-managed
plugin with hooks and eval suites* rather than as tips in a wiki. Name the trade-offs: determinism
where the answer is unique and agency only where judgment is required; hard cost ceilings
(`--max-turns`, `--max-budget-usd`, wall-clock timeout) as reliability engineering, since an
unbounded loop is an unbounded invoice; capability denial at the tool layer, with human confirmation
for outward-facing actions; and a calibration loop that mines session transcripts for recurring
friction and files it as work — treating agent failures as a measurable defect stream, not anecdotes.
Then be honest about the ceiling: review capacity is the new bottleneck, and verification has to be
executable to keep up.

---

## Atomic concept checklist

- [ ] I can state the agent loop in three steps and explain why cost grows with transcript length, not message length.
- [ ] I know "it forgot" almost always means "never in context" or "compacted out", not a memory bug.
- [ ] I can name the five context channels and say, for each, when its tokens enter the window.
- [ ] I know `CLAUDE.md` is a per-turn tax and skills are near-free until triggered — and why that drives what goes where.
- [ ] I can order the settings precedence layers: enterprise → user → project → project-local → CLI flags.
- [ ] I know rules are evaluated deny → ask → allow, first match wins, and that a broad deny cannot carry allowlist exceptions.
- [ ] I know a deny-list that fails to load is the dangerous case, and that managed settings outrank the command line.
- [ ] I know a skill's `allowed-tools` pre-approves for one turn and `disallowed-tools` is what restricts.
- [ ] I can distinguish the four permission modes and say which one belongs in CI.
- [ ] I know `--agent` swaps the persona while `--append-system-prompt` only appends to the default.
- [ ] I know to strip YAML frontmatter before appending an agent file's body to a system prompt.
- [ ] I can write an agent definition with a structured output contract and explicit write boundaries.
- [ ] I know a subagent costs ~2× and can name the three cases where it still pays.
- [ ] I know lanes must partition the filesystem, and that a same-slug collision overwrites silently.
- [ ] I can name six hook events and say what stdout and a non-zero exit code each do.
- [ ] I know a `PreToolUse` non-zero exit is the only guard the model cannot talk its way past.
- [ ] I know why an expensive `SessionStart` hook without a lock destroys a machine under concurrent sessions.
- [ ] I can build a headless invocation with a turn cap, a wall-clock timeout, and a dollar ceiling, and say why all three differ.
- [ ] I know `--setting-sources` resolves against `cwd`, and that `--settings <abs path>` is the fix when `cwd` is a worktree.
- [ ] I preserve the unparseable input when envelope parsing fails, and distinguish launch/contract/agent failures.
- [ ] I know `${CLAUDE_PLUGIN_ROOT}` is the plugin cache, not the repo, and that path assumptions are the top porting bug.
- [ ] I know a cross-marketplace dependency needs explicit trust and that unresolved ones are nearly silent.
- [ ] I can apply the deterministic-vs-agentic rule: one correct answer → script; judgment → prompt; must-happen → hook.
- [ ] I deny the tool rather than instructing the agent not to use it, for anything needing human authority.
- [ ] I verify by re-running published artefacts, and I assert text-ness before trusting any grep-based gate.
- [ ] I can give the Staff answer: AI capability as a versioned platform with cost ceilings, capability denial, and a calibration loop.
