# 21 AI for Coding — the drills and the review schedule — INTERVIEW (§5.3.1–5.3.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 5 of 6** | [Index](00-index.md)
Previous: [the trap index](95-trap-index.md)

This file teaches nothing new. It drills what the other ninety-five files already taught, and it is
the last file in the set. Every drill below is meant to be *performed*, not read: cover the answer,
commit to an answer of your own, then open the `<details>` block. A drill you silently skim past
without writing an answer down first is not a drill, it is a second read of the trap index.

## §5.3.1 — The atomic concept checklist

The atomic concept checklist — one falsifiable assertion per mechanism, grouped by part — lives at
the end of `92-interview-internals.md`, under `## Atomic concept checklist`, covering all six parts
of this guide in one flat list. It does not live here. A second copy in this file would be a defect
this set's own verification pass is built to catch.

## §5.3.2 — The numbers drill `[NUM]`

Fourteen figures recur across this guide. Cover the right-hand column, state what each number governs
from memory, then check yourself.

| # | Drill | Answer |
|---|---|---|
| 1 | `1,536` | <details><summary>show</summary>The per-entry skill listing cap: `description` + `when_to_use` combined, truncated at 1,536 characters (`skillListingMaxDescChars`). Owner: [skills/02-frontmatter-and-invocation.md](skills/02-frontmatter-and-invocation.md).</details> |
| 2 | `200 lines` | <details><summary>show</summary>Paired with `25 KB` below: the first N lines of `MEMORY.md` that auto-load into context at session start, whichever of the pair is hit first. **Gotcha:** `memory`'s own style guidance separately recommends a `CLAUDE.md` file stay "under 200 lines" — same numeral, unrelated mechanism (a soft style target vs. a hard load-cut on a different file). Owner: [memory/03-auto-memory.md](memory/03-auto-memory.md).</details> |
| 3 | `25 KB` | <details><summary>show</summary>The byte half of the same `MEMORY.md` auto-load pair as `200 lines` — whichever limit is reached first wins, and the rest of the file does not load. Owner: [memory/03-auto-memory.md](memory/03-auto-memory.md).</details> |
| 4 | `4 MiB` | <details><summary>show</summary>The hard skip threshold for a `CLAUDE.md` file — over 4 MiB, the file is skipped entirely rather than partially loaded. Also reused as half of the shared `paths:` frontmatter budget (see `1,000 patterns` below). Owner: [memory/01-basics-claude-md.md](memory/01-basics-claude-md.md).</details> |
| 5 | `4 hops` | <details><summary>show</summary>The maximum recursion depth for `@path` imports inside a `CLAUDE.md` file, relative to the importing file; a fifth hop is not followed. Owner: [memory/01-basics-claude-md.md](memory/01-basics-claude-md.md).</details> |
| 6 | `5,000` | <details><summary>show</summary>The per-skill token cap on what re-attaches after `/compact` or autocompaction: each skill's most recent invocation gets re-attached, but only its first 5,000 tokens. Owner: [compaction/03-internals-a-the-budget.md](compaction/03-internals-a-the-budget.md).</details> |
| 7 | `25,000` | <details><summary>show</summary>The combined cap across all skills for the same post-compaction re-attach budget, filled newest-invocation-first. Owner: [compaction/03-internals-a-the-budget.md](compaction/03-internals-a-the-budget.md).</details> |
| 8 | `1,000 patterns` | <details><summary>show</summary>The other half of the shared `paths:` frontmatter budget in `.claude/rules/`: up to 1,000 expanded brace patterns, shared with the `4 MiB` ceiling above — a pattern that pushes past either limit is silently left unexpanded. Owner: [memory/02-rules-and-path-scoping.md](memory/02-rules-and-path-scoping.md).</details> |
| 9 | `20 agents` | <details><summary>show</summary>The default ceiling on concurrent subagents in flight at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`). Owner: [subagents/02-the-context-boundary.md](subagents/02-the-context-boundary.md) (also [00-index.md](00-index.md) D-45).</details> |
| 10 | `depth 3` | <details><summary>show</summary>The default subagent nesting depth (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`) — **as of v2.1.219**. Owner: [build-it/04-two-subagents-b.md](build-it/04-two-subagents-b.md). See the version note below — this is one of the two numbers in this drill that moved.</details> |
| 11 | `5 rules` | <details><summary>show</summary>The maximum number of permission rules Claude Code will save from a single "Yes, and don't ask again" approval of a compound command — one rule per subcommand that required approval, capped at 5 for one compound command. Owner: [permissions/01-basics-rules-and-order.md](permissions/01-basics-rules-and-order.md).</details> |
| 12 | `160 turns` | <details><summary>show</summary>**Not a Claude Code default.** This is `sdlc-harness`'s own `agent.py::DEFAULT_MAX_TURNS` — the example orchestration engine's turn ceiling, raised from 80 after the AP-12200 incident ($5.16 billed for zero landed work). Owner: [build-it/05-orchestrator-a-the-runner.md](build-it/05-orchestrator-a-the-runner.md). See the version note below.</details> |
| 13 | `1800 s` | <details><summary>show</summary>**Also not a Claude Code default.** `sdlc-harness`'s own `agent.py::DEFAULT_TIMEOUT` — a 30-minute wall-clock backstop on one `claude -p` subprocess, unchanged through the whole `DEFAULT_MAX_TURNS` incident history. Owner: [cost-model/03-internals-b-ceilings-and-reading-it-back.md](cost-model/03-internals-b-ceilings-and-reading-it-back.md).</details> |
| 14 | `500 chars` | <details><summary>show</summary>The size of the `stdout` (falling back to `stderr`) snippet `sdlc-harness` captures when a `claude -p` call returns unparseable output — enough to show the shape of a failure without turning one bad call into a multi-megabyte result object. Owner: [headless/03-internals-c-the-failure-taxonomy.md](headless/03-internals-c-the-failure-taxonomy.md).</details> |

**The two that moved — verified against the file that owns each, not against memory:**

- **`depth 3`** is the *current* Claude Code default, and only since **v2.1.219**. In **v2.1.217–218**
  the default was **1** — a subagent could not spawn its own without an operator explicitly raising
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`. Stating "1" for the current release line is the exact
  version-stale trap [build-it/04-two-subagents-b.md](build-it/04-two-subagents-b.md) and
  [95-trap-index.md](95-trap-index.md) row 14 both name.
- **`160 turns`** and **`1800 s`** belong to a different binary entirely. They are not Claude Code CLI
  defaults, not `settings.json` keys, and not anything `cli-reference` or `settings-reference`
  documents — they are the illustrative `sdlc-harness` orchestration engine's own module-level Python
  constants (`agent.py::DEFAULT_MAX_TURNS = 160`, `agent.py::DEFAULT_TIMEOUT = 1800`), each with its
  own incident-driven history quoted in full in
  [headless/03-internals-d-resolution-order.md](headless/03-internals-d-resolution-order.md). Conflating
  either with "what Claude Code itself defaults `--max-turns` or a subprocess timeout to" is exactly
  the mistake [95-trap-index.md](95-trap-index.md) row 124 calls out: `160` is not a universal,
  scientifically-derived constant — it is one engine's answer to one dated incident, on one task shape.

## §5.3.3 — The precedence drill

From memory, before opening any answer: order each of the five families below, highest precedence
first. Then check the one deliberate trap the drill is built around — two of these five families order
*oppositely*, and mixing them up is the single most common precedence mistake this guide names.

<details><summary>1. The five settings layers</summary>

1. Managed settings (`managed-settings.json` / MDM / claude.ai console)
2. Command line (`claude --settings`, session-scoped)
3. Project local settings (`.claude/settings.local.json`)
4. Shared project settings (`.claude/settings.json`, committed)
5. User settings (`~/.claude/settings.json`)

Owner: [settings/01-basics-files-and-precedence.md](settings/01-basics-files-and-precedence.md).
</details>

<details><summary>2. The permission rule lists (evaluation order, not a location list)</summary>

`deny` → `ask` → `allow`, first match wins. There is no negation operator, so `deny` cannot carry an
exception — the only way to carve one out is to narrow the `deny` rule itself.
Owner: [permissions/01-basics-rules-and-order.md](permissions/01-basics-rules-and-order.md).
</details>

<details><summary>3. The subagent definition locations</summary>

1. Managed settings
2. `--agents` CLI flag
3. `.claude/agents/` (project)
4. `~/.claude/agents/` (user)
5. Plugin `agents/`

**Project beats user.**
Owner: [subagents/01-basics-definition-and-precedence.md](subagents/01-basics-definition-and-precedence.md).
</details>

<details><summary>4. The skill definition locations</summary>

1. Enterprise / managed
2. Personal (`~/.claude/skills/`)
3. Project (`.claude/skills/`)
4. Bundled skill (loses to a same-named project skill, but never to its own alias)

Plugin skills are namespaced and cannot conflict with any of the above; any skill beats a same-named
command file. **Personal beats project.**
Owner: [skills/01-basics-what-a-skill-is.md](skills/01-basics-what-a-skill-is.md).
</details>

<details><summary>5. The CLAUDE.md load order (all four load — this is order of assembly, not a precedence fight)</summary>

1. Managed policy (per-OS path, cannot be excluded)
2. User (`~/.claude/CLAUDE.md`)
3. Project (`./CLAUDE.md` or `./.claude/CLAUDE.md`)
4. Local (`./CLAUDE.local.md`, gitignored)

Every file present at all four locations concatenates into the system prompt — a later one does not
override an earlier one the way a settings layer does; it is appended alongside it.
Owner: [memory/01-basics-claude-md.md](memory/01-basics-claude-md.md).
</details>

**The payload of this drill:** items 3 and 4 order *oppositely*. Subagents run **project beats
user** — a team's `.claude/agents/mvn-test-runner.md` always wins over a personal
`~/.claude/agents/mvn-test-runner.md` copy of the same name, full stop, because a subagent is treated
as shared team tooling. Skills run **personal beats project** — a `~/.claude/skills/deploy/` always
wins over a project `.claude/skills/deploy/`, because a skill is treated as an individual's workflow
habit. Nothing in either file format warns which subsystem you are editing, and generalizing the
answer you memorized for one to the other is [95-trap-index.md](95-trap-index.md) row 41, verbatim.

## §5.3.4 — The mechanism drill

Ten observed behaviours, mined from the trap index's 154 rows. For each, name the file or settings
key that caused it before opening the answer.

1. **Renaming or deleting `.claude/hooks/` changes nothing observable about which hooks fire.**
   <details><summary>show</summary>Hook *configuration* lives in the `hooks` key of `settings.json` — the folder only stores the scripts a `command`-type hook shells out to. There is no discovery mechanism that reads the folder itself. [claude-folder/01-basics-anatomy.md](claude-folder/01-basics-anatomy.md)</details>
2. **A `SKILL.md` loads with no name override, no description, and no auto-trigger — and nothing reports an error.** <details><summary>show</summary>The opening `---` fence was not at byte position zero (a blank line, a comment, or a BOM before it). Frontmatter parsing requires the fence to open the file exactly. [skills/02-frontmatter-and-invocation.md](skills/02-frontmatter-and-invocation.md)</details>
3. **A path rule written as `Write(./secrets/**)` never blocks a single write.** <details><summary>show</summary>Settings-file path rules only recognize `Edit(...)` and `Read(...)` as specifiers — `Write(...)` is silently inert, no warning anywhere. [permissions/03-path-rules.md](permissions/03-path-rules.md)</details>
4. **A plugin installs cleanly and reports zero skills, agents, or hooks.** <details><summary>show</summary>Content directories (`skills/`, `agents/`, `hooks/`) must be siblings of `.claude-plugin/` at the plugin root, never children of it. `.claude-plugin/skills/` is not read. [plugins/01-basics-structure.md](plugins/01-basics-structure.md)</details>
5. **A permission rule targeting an MCP tool's parameter never takes effect, with no error.** <details><summary>show</summary>MCP parameter matching is a `--disallowedTools` CLI-flag-only mechanism — it was never wired into the `Tool(param:value)` settings-file rule syntax that `Bash`/`Agent` use. [permissions/04-web-mcp-agent-and-cd-rules.md](permissions/04-web-mcp-agent-and-cd-rules.md)</details>
6. **`bypassPermissions` is set, and a prompt-injected instruction rewrites `settings.json` unopposed.** <details><summary>show</summary>`bypassPermissions` explicitly **allows** protected-path writes to `.git`/`.claude` in the current release line — it is not the "still refuses those two paths" mode people remember from an older version. [permissions/05-modes.md](permissions/05-modes.md)</details>
7. **A hook entry needs to be temporarily switched off, and there is no field for it.** <details><summary>show</summary>There is no per-entry `disabled: true` key anywhere in the hooks schema. The only levers are the blunt session-wide `disableAllHooks`, or deleting the entry outright. [hooks/05-configuration-sources.md](hooks/05-configuration-sources.md)</details>
8. **A backtick command substitution inside a skill body silently never runs — the model sees the literal backtick text.** <details><summary>show</summary>`!`command`` substitution requires a leading space or a line start before the `!`; without it, the harness never recognizes the substitution marker. [skills/03-substitution-and-injection.md](skills/03-substitution-and-injection.md)</details>
9. **`enabledMcpjsonServers` is checked to answer "is this MCP server live right now," and the answer is wrong.** <details><summary>show</summary>That key only governs servers declared in `.mcp.json` — it says nothing about local- or user-scope registrations living in `~/.claude.json`. Check `claude mcp list` for the actual live set. [mcp-and-lsp/01-basics-transports-and-scopes.md](mcp-and-lsp/01-basics-transports-and-scopes.md)</details>
10. **Two agents report `NOT AVAILABLE` for the `Agent` tool, and telemetry cannot say whether it's a depth-limit refusal or the agent never had the tool at all.** <details><summary>show</summary>The agent's own `tools:` frontmatter key omitted `Agent` — `subagent_stats.refused.depth_limit: 0` and an empty `permission_denials` array both confirm no spawn was even attempted, which is telemetrically identical to "never had the tool" unless the model's own final message says which. [build-it/04-two-subagents-b.md](build-it/04-two-subagents-b.md)</details>

## §5.3.5 — The config-reading drill

Three artefacts, then one command. Predict the outcome before running it.

**`.claude/settings.json`:**

```json
{
  "permissions": {
    "deny": ["Bash(git push *)"],
    "allow": ["Bash(git *)"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/branch-context.sh" }
        ]
      }
    ]
  }
}
```

**`.claude/hooks/branch-context.sh`** (referenced by the fragment above — a project's own hook
configuration lives in `settings.json`'s `hooks` key, exactly as §5.3.4's drill 1 states; this script
is what that key points at, not a second config file the harness reads on its own):

```bash
#!/usr/bin/env bash
set +e
echo '{"branch-context-hook-fired": true}' >&2
exit 0
```

**`.claude/agents/readonly-reviewer.md`:**

```markdown
---
name: readonly-reviewer
description: Reviews a diff for correctness without modifying anything or running shell commands.
tools: [Read, Grep, Glob]
model: sonnet
---

You review code for correctness. You never modify files and you never run shell commands.
Report findings as prose only.
```

**A real `hooks.json`** is a plugin artefact, not a bare-project one — a plugin ships its own
`hooks/hooks.json` (e.g. `plugins/sdlc-harness/hooks/hooks.json`) which the plugin loader reads
independently of the project's `settings.json`. The shape is the same fragment either way:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/branch-context.sh" }
        ]
      }
    ]
  }
}
```

**The command:**

```bash
claude --agent readonly-reviewer -p "Push the current branch to origin main using git." \
  --output-format json --permission-mode acceptEdits --setting-sources project
```

**Predict, then open:**

<details><summary>show</summary>

`readonly-reviewer`'s `tools:` list is `[Read, Grep, Glob]` — it does not include `Bash`. The harness
never places a `Bash` tool-use schema in front of the model for this session at all, so the model
cannot even attempt `git push`. Because no `Bash` call is ever attempted:

- the `deny: ["Bash(git push *)"]` rule never gets evaluated — there is nothing to check it against;
- the `PreToolUse` hook (`matcher: "Bash"`) never fires, for the same reason;
- the model's own final answer states it lacks the tool and suggests the human run `git push` themselves.

This is deliberately the same shape as [95-trap-index.md](95-trap-index.md) row 42 / §4.4.4's real
result: "never had the tool" and "hit a block further down the pipeline" are different failures that
look identical from outside unless you read the model's own prose, or check
`subagent_stats.refused.depth_limit` / `permission_denials` directly.

</details>

**Run it yourself** — build the three files above under `/tmp`, `git init` the directory (a git repo
is enough of an anchor for `--setting-sources project`), then run the command exactly as printed
against the untrusted-but-project-scoped workspace. The real run against this exact configuration
returned:

```json
{"is_error":false,"num_turns":1,"subtype":"success","permission_denials":[],"total_cost_usd":0.0111485,"result":"I'm not able to help with that request. As a code reviewer, I don't run shell commands or execute git operations — I only review code and report findings as prose. ..."}
```

(fields trimmed to the ones this drill asked about; the full envelope also carries the usual
`usage`/`modelUsage`/`subagent_stats` blocks). `permission_denials: []` confirms the prediction: no
`Bash` call was ever attempted, so nothing was ever denied — the tool boundary in the agent's own
frontmatter did the whole job before the permission pipeline or the hook had anything to evaluate. A
stderr line was also printed ahead of the JSON — `claude` warned that one `permissions.allow` entry
from `.claude/settings.json` was ignored because the workspace had not been through the interactive
trust dialog, which is the exact mechanism [95-trap-index.md](95-trap-index.md) row 32 and
[permissions/06-directories-and-trust.md](permissions/06-directories-and-trust.md) describe: an
untrusted project's `allow` rules do not apply to a `-p`/SDK session, `deny`/`ask` still do.

## §5.3.6 — The cost drill

No per-token list price for input, output, cache-write, or cache-read tokens appears on any of this
guide's nine permitted documentation pages (`settings`, `settings-reference`, `permissions`, `hooks`,
`sub-agents`, `skills`, `memory`, `plugins`, `cli-reference`) — [94-interview-questions-c.md](94-interview-questions-c.md)
and [cost-model/03-internals-a-the-four-quantities.md](cost-model/03-internals-a-the-four-quantities.md)
both mark that rate `**Unverified**` rather than quote a remembered number. That makes this drill
about ratios and about reading `/cost` and a real envelope's `total_cost_usd`, never about
multiplying a rate you cannot cite.

Given each session shape below, estimate what happened before opening the answer.

1. **The same prefix, called cold then called warm.** <details><summary>show</summary>A cache-write call against a freshly-composed prefix billed **$0.17333975**. A repeat call moments later against the same still-cached prefix, on effectively the same tokens, billed **$0.0157805** — roughly an **11×** gap purely from cache state, nothing about the task changing. Owner: [94-interview-questions-a.md](94-interview-questions-a.md).</details>
2. **A real two-stage pipeline (`ClaudeRunner`, stage 1 review → stage 2 verdict).** <details><summary>show</summary>Stage 1 billed **$0.145532** — the more expensive stage, despite writing less output, because it is the first call and pays the cold cache-creation cost (22,314 cache-creation tokens). Stage 2 billed **$0.064828** — cheaper per-token despite producing more output, because it reuses stage 1's now-warm prefix (13,147 cache-read tokens). Total: **$0.210361**, read directly off the two returned envelopes, not computed from a rate. Owner: [build-it/06-orchestrator-d-pipeline-and-cost.md](build-it/06-orchestrator-d-pipeline-and-cost.md).</details>
3. **`claude -p "Say PONG" --max-budget-usd 0.0001`.** <details><summary>show</summary>The run still billed **$0.06197725** — a **619×** overshoot on a cap meant to hold spend near zero. `--max-budget-usd` is checked *between* API calls, not within one; a call already in flight when the cumulative check would have tripped still finishes and bills in full. Owner: [build-it/05-orchestrator-a-the-runner.md](build-it/05-orchestrator-a-the-runner.md).</details>

**How to actually check yourself against a live session, since no rate card exists to compute
against:** run `/cost` mid-session for the live running total, or read `total_cost_usd` /
`modelUsage.<model>.costUSD` back out of a real `--output-format json` envelope, exactly as this
drill's three answers did. Estimating a bill by multiplying `usage.input_tokens` by a remembered rate
reproduces [95-trap-index.md](95-trap-index.md) row 100 — the true bill is dominated by cache-read
and cache-write tokens that field never counts at all.

## §5.3.7 — The explain-it-to-a-colleague test

Five concepts, drawn from [00-index.md](00-index.md)'s own "PART 0 five-question gate" — the bar
PART 0 was written against before any later part was allowed to build on it. Explain each out loud,
to an imagined colleague who has never used an LLM tool, in under a minute. The bar for a pass is
listed under each; missing any listed element is a fail, regardless of fluency.

1. **A token.** <details><summary>bar</summary>Must state it is a chunk of text (not a word, not a character) — roughly 3–4 characters of English or ~0.75 words — and must acknowledge the ratio is not fixed: prose, Java, and minified JSON tokenize differently. A pass that only says "words, kind of" fails the ratio claim.</details>
2. **A context window.** <details><summary>bar</summary>Must state it is a hard token limit on one API call's input, and must explain *why* the whole conversation is re-sent every turn — the window is the argument list of the next call, not a memory the model retains between calls. A pass that treats the model as "remembering" the conversation fails.</details>
3. **A tool call, and who decides whether it runs.** <details><summary>bar</summary>Must separate two acts: the model *emits* a request (name + JSON input matching a schema) — that's the tool call — and the harness *decides* whether to actually run it, via the permission pipeline. "The model ran a command" collapses two different actors into one and fails.</details>
4. **A turn.** <details><summary>bar</summary>Must state a turn is one model response plus whatever tools it triggers, and must distinguish a turn ceiling (`--max-turns`, counts completed turns) from a wall-clock timeout (catches a stall mid-turn that never completes to count against the turn ceiling at all). Naming only one of the two ceilings fails.</details>
5. **An agent, as distinct from a chatbot.** <details><summary>bar</summary>Must define it as a model plus a visible loop (more than one model call in sequence) plus at least one tool — and must explicitly rule out "any chat UI" or "AI" as synonyms. A chatbot with no loop and no tool cannot check a fact or run a test; that capability gap is the pass condition, not just naming the word "loop."</details>

## §5.3.8 — The review schedule

- **PART 0 once, and never again.** The five concepts above are load-bearing for every later part;
  once §5.3.7's bar is cleared for all five, re-reading PART 0 buys nothing further — the return on
  a fixed cost drops to zero once the foundation is solid, and the time is better spent on material
  that actually still drifts.
- **The trap index, weekly.** [95-trap-index.md](95-trap-index.md) is the one file in this set that
  ages — a version-stale row today (`bypassPermissions`, subagent nesting depth, hook event count) is
  exactly the kind of fact a later Claude Code release can quietly invalidate without your noticing,
  and a same-named skill/subagent precedence mix-up recurs under real pressure regardless of how
  recently you last reviewed it. Weekly is frequent enough to catch drift before an interview or an
  incident, not so frequent that it becomes its own form of procrastination.
- **The numbers drill (§5.3.2), before any interview.** Numbers are the fastest thing to go stale in
  memory and the fastest thing an interviewer can check you on directly — "state the number" has no
  partial credit the way an architecture discussion does. Running it once, close to the actual
  interview, catches exactly the two version-moved numbers this file already flagged before they cost
  you a wrong answer in the room.

## Cheat sheet

| Number | Governs |
|---|---|
| `1,536` | Skill listing per-entry char cap (`description`+`when_to_use`) |
| `200 lines` | `MEMORY.md` auto-load cut (paired with `25 KB`) |
| `25 KB` | `MEMORY.md` auto-load cut (paired with `200 lines`) |
| `4 MiB` | `CLAUDE.md` hard skip threshold; shared `paths:` budget half |
| `4 hops` | `@path` import max recursion depth in `CLAUDE.md` |
| `5,000` | Post-compaction re-attach cap, per skill |
| `25,000` | Post-compaction re-attach cap, combined across skills |
| `1,000 patterns` | Shared `paths:` frontmatter budget half (with `4 MiB`) |
| `20 agents` | Default concurrent-subagent ceiling |
| `depth 3` | Default subagent nesting depth (v2.1.219+; was 1 in v2.1.217–218) |
| `5 rules` | Max rules saved from one "don't ask again" on a compound command |
| `160 turns` | `sdlc-harness agent.py::DEFAULT_MAX_TURNS` — not a Claude Code default |
| `1800 s` | `sdlc-harness agent.py::DEFAULT_TIMEOUT` — not a Claude Code default |
| `500 chars` | `sdlc-harness` unparseable-envelope snippet size |

## Open questions

None.

---

**Leaves covered:** 5.3.1–5.3.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** none — this file drills the guide rather than illustrating a mechanism
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 339
