# 21 AI for Coding — PART 3 summary and the atomic concept checklist — ADVANCED (INTERNALS) (§3.1–§3.10)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](00-index.md)
Previous: [automation, and review capacity](verification/03-internals-c-automation-and-review-capacity.md) · Next: [PART 3 — the Q&As and puzzles](92-interview-internals-b.md)

This file carries two things only: a night-before-the-interview summary table over every INTERNALS
subject (§3.1–§3.10), and the atomic concept checklist over the whole guide, all six parts. The 22
Q&As and the 5 puzzles that would normally sit in a `92-interview-internals.md` live instead in
[92-interview-internals-b.md](92-interview-internals-b.md) — go there for those; this file keeps the
checklist because that is the parser target for the rest of the pipeline.

## Summary table

One table per subject folder, in the order the folders were taught. No prose — mechanism, number,
trap.

### Request assembly

| Segment | Contents | In default cached prefix? | Cost lever |
|---|---|---|---|
| 1. System prompt | Built-in + `--append-system-prompt` / `--system-prompt` | Yes | `--exclude-dynamic-system-prompt-sections` pulls per-machine facts out |
| 2. Tool schemas | Every registered tool's JSON schema, built-in + MCP | Yes | Disconnect unused MCP servers; defer tools behind `ToolSearch` |
| 3. Memory (`user` message) | `CLAUDE.md` (all scopes), `.claude/rules/*`, `MEMORY.md` index | Yes | Keep `CLAUDE.md` under 200 lines |
| 4. Environment/git snapshot | cwd, platform/OS, git branch+status, date | No (or moved here by the flag) | `--exclude-dynamic-system-prompt-sections` |
| 5. Skill listing | name + description + `when_to_use` per skill | No | Fewer auto-discovered skills |
| 6. Conversation | Prior user/assistant/tool messages | No | `/compact`, `/clear` |

| Fact | Value | Source |
|---|---|---|
| Per-skill description cap | 1,536 characters (`skillListingMaxDescChars`) | `skills` doc |
| Skill listing budget, default | 1% of context window (`skillListingBudgetFraction = 0.01`) | `skills` doc |
| Skill listing budget, doc's raise example | 0.02 (2%) | `skills` doc |
| What drops first when the listing overflows | Descriptions of least-invoked skills; names never drop | `skills` doc |
| Transcript path | `~/.claude/projects/<project-slug>/<session-id>.jsonl` | observed + `transcript.py` |
| Per-turn request-side cost | `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` | worked from a real record |
| What `transcript.py` extracts | `model`, `timestamp`, `usage.*`, tool `name` — nothing else | `transcript.py` DATA-SAFETY docstring |
| Transcript retention | `cleanupPeriodDays` (days), any settings file | `settings-reference` |

### Compaction

| Question | Answer |
|---|---|
| What compaction does | One summarization call replaces the accumulated transcript with a shorter one; not a deletion, not a save |
| Threshold formula | `used_tokens ÷ window_size = fraction consumed`; crossing the threshold fires compaction |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Undocumented; accepts `0 < pct ≤ 100`; threshold = `min(floor(window × pct/100), window − 13,000)` |
| Hard floor on any threshold | `window_size − 13,000` tokens |
| Skill re-attachment | 5,000 tokens per skill / 25,000 combined, newest-first; hitting the cap evicts the next candidate outright |
| `CLAUDE.md`, project-root | Reloads unconditionally, every compaction |
| `CLAUDE.md`, nested / path-scoped | Reloads only once a matching path is read again post-compaction |
| Conversation-only facts | Never survive a compaction |
| Persistence seam | `PreCompact` writes a checkpoint; `SessionStart` (matcher `compact`) re-injects it via `additionalContext` |
| Cost of the write half | Zero tokens — a local shell command |
| One compaction vs three | One is the designed steady state; three compounds both summarization cost and fidelity loss |

### Permission evaluation

| Stage | What it checks | Terminal outcomes |
|---|---|---|
| 1 — rule collection | managed → CLI → local project → shared project → user, merged into one deny/ask/allow set | none — assembly only |
| Branch — read-only fast path | one of 15 recognized read-only shapes, no write-capable-flag-glob or redirect exception | RUNS |
| 2 — deny/ask/allow | first match wins, in that order | BLOCKED (deny) |
| 3 — `PreToolUse` hook | may allow or block regardless of how the call reached it | BLOCKED (hook) |
| 4 — mode's default | only for calls stage 2 left unmatched | routes to stage 3 or 5 |
| 5 — interactive prompt | human approves or denies | BLOCKED (prompt deny) |
| Deny finality | a deny at any layer cannot be overridden by any other layer, `--allowedTools`, or managed settings | — |

| Fact | Value |
|---|---|
| Symlink path rule check | Two paths checked: the link and its target; allow needs both, deny needs either |
| Windows path matching | Normalized to POSIX first — `C:\Users\alice` → `/c/Users/alice` |
| `Grep`/`Glob` consultation | Resolve `path` to a directory, apply `Read` deny to that directory, never the search pattern |
| Excluded from `Tool(param:value)` matching | `command`, `file_path`, `path`, `notebook_path`, `url` |
| macOS sandbox primitive | Seatbelt (built in) |
| Linux/WSL2 sandbox primitive | bubblewrap (filesystem) + socat (network relay); optional seccomp |
| Sandbox network enforcement | A proxy outside the sandbox, hostname-only, no TLS inspection |
| Sandbox network limitation | Domain fronting can reach a disallowed host behind an allowed hostname |
| Sandbox scope | Bash subprocesses only — `Read`/`Edit`/`Write` go through permissions directly |

### Cost model

| Quantity | Relative price | Envelope field | Verified? |
|---|---|---|---|
| Input tokens | 1× (baseline) | `usage.input_tokens` | Baseline by definition |
| Output tokens | several× baseline | `usage.output_tokens` | Unverified exact multiplier |
| Cache writes | premium over baseline | `usage.cache_creation_input_tokens` | Premium direction verified, multiplier Unverified |
| Cache reads | ~10% of baseline | `usage.cache_read_input_tokens` | Verified |
| Model tier ratio (Haiku/Sonnet/Opus) | not on permitted doc pages | `modelUsage.<model>.costUSD`/`costBasis` | Unverified |
| Default cache TTL | 1h (subscription, main conv.) / 5m (everything else) | mechanism | Verified |
| TTL override | `promptCacheTtl`/`subagentPromptCacheTtl`, `5m`/`1h` only, v2.1.242+ | `settings-reference` | Verified |

| Ceiling / mechanism | Bounds | Version floor | Work preserved on trip? |
|---|---|---|---|
| `--max-turns` | Agency | No default limit | `session_id` preserved, resumable |
| `--max-budget-usd` | Money, subagents included | v2.1.217+ | Disk state persists; run halts mid-flight |
| Subprocess wall-clock timeout | Time | Not a CLI flag — wrapper-imposed | Nothing; wrapper must synthesize a failure |
| Subagent premium | — | — | Mechanism: cold cache-write vs. warm cache-read; ~2× is a floor, observed ~11× |
| `budgets:`/`circuit_break_per_run_usd` | Whole-pipeline spend, above `--max-budget-usd` | sdlc-harness app-level | Halt non-recoverable inline; `--from <stage>` required |

### Effort and routing

| Lever | Scope | Reverts automatically? | Chooses task tier? |
|---|---|---|---|
| `--effort` / `/effort` | This session | Yes | No — depth, not model |
| `effortLevel` | Persistent (settings file) | No | No — depth, not model |
| Skill `model:`/`effort:` frontmatter | Rest of the invoking turn | Yes | Yes, for that skill's invocations |
| Subagent `model:`/`effort:` frontmatter | That subagent's own run | Yes | Yes, for that subagent's dispatches |
| `fallbackModel`/`--fallback-model` | Availability fallback chain | Session/persistent | No — availability, not cost |
| `switchModelsOnFlag` | Safety-classifier response | Persistent | No |
| `advisorModel` | One internal tool | Persistent | No |
| `modelOverrides` | Provider ID mapping | Persistent | No |
| `modelPicker` | What `/model` lists, in what order | Persistent | No — presentation |
| `fastMode`/`/fast` | Output latency, same model | Session | No — speed, not tier |

### Headless

| Item | Answer |
|---|---|
| Turn on headless mode | `-p` / `--print` |
| One final answer, machine-readable | `--output-format json` |
| Liveness while the run progresses | `--output-format stream-json` |
| Envelope fields a caller may rely on | `result`, `is_error`, `session_id`, `total_cost_usd`, `usage.*`, `duration_ms` |
| Schema-validated data instead of prose | `--json-schema '<schema>'` |
| Pin a session's UUID | `--session-id <uuid>` |
| Resume a specific session | `--resume <id-or-name>` / `-r` |
| Never write a transcript | `--no-session-persistence` |
| `--resume` search scope | Current project + worktrees before v2.1.223; every project from v2.1.223 |
| Generate a CI credential | `claude setup-token` |
| Subagent spend and a budget cap | `--max-budget-usd` counts subagent spend, enforcement v2.1.217+ |
| Three failure classes | launch/timeout (infra), unparseable envelope (contract), `is_error: true` (agent) |
| Terminal, never-retried subtype | `error_max_turns` |
| Snippet size on unparseable envelope | 500 characters, stdout then stderr fallback |
| Resolution order for every knob | explicit parameter → environment variable → hardcoded default |
| `DEFAULT_PERMISSION_MODE` / `DEFAULT_SETTING_SOURCES` | `"acceptEdits"` / `"user,project"` |
| `DEFAULT_TIMEOUT` / `DEFAULT_MAX_TURNS` | `1800` / `160` — sdlc-harness only, not a Claude Code default |
| `DEFAULT_MAX_TURNS` history | `40` → `80` → `160` (2026-08-10, $5.16 spent, zero commits at 80) |

### Setting-sources incident

| Question | Answer |
|---|---|
| Where does `--setting-sources project` resolve `.claude/settings.json` from | The session's primary `cwd` — no worktree fallback |
| What DOES fall back to the main checkout in a worktree | Only `.claude/settings.local.json` |
| What broke | `Bash(*)` never applied — the agent fell back to bare `acceptEdits` defaults |
| What still worked | `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed`, file edits — the full `acceptEdits` allowlist |
| What was refused | `mvn`, `git commit`, `chmod`, `java` |
| The escape hatch | `--settings <absolute path>` — evaluated independently of `cwd` |
| Regression | `a8c0bbb` deleted the entire `permissions` object 9 days later |
| General law, `cwd`-relative resolution | Resolve absolutely, or derive the root explicitly and refuse loudly |
| General law, missing configuration layers | Fail safe on authorization, fail **loud** on configuration — not the same property |
| Other systems hit by the same `cwd` shape | `${CLAUDE_PLUGIN_ROOT}`, hook command paths, a `cron` job with a relative script path |

### SDK and API

| Level | Call shape | Gives up |
|---|---|---|
| 1 — CLI `-p` | `claude -p ... --output-format json` subprocess | In-process control |
| 2 — Agent SDK | `query()` / `ClaudeSDKClient` | Some process isolation |
| 3 — raw Messages API | `client.messages.create(...)`, your own loop | Everything the harness did: permissions, hooks, compaction, cost accounting, retry classification |
| Java route | `HttpClient` → Level 3, or `ProcessBuilder` around `claude -p` → Level 1 | No first-party Java SDK |

| Concept | One line |
|---|---|
| `resolveSettings()` | SDK-side composition of the precedence chain before the first request |
| `managedSettings` | Composed regardless of `settingSources` — the floor no session opts out of |
| `parentSettingsBehavior` | `"isolated"` vs inheriting the spawning process's resolved settings |
| Why subprocess over SDK | Same persona file (`--agent`), same deny-list, no SDK↔binary version coupling |
| `Process.waitFor(Duration)` | Returns `false` on timeout — does not throw or kill; call `destroyForcibly()` yourself |
| Retry ring | Bounded (`retries=3` default), classified — `error_max_turns` is terminal |
| Bulkhead ring | `Semaphore` permit count around concurrent `claude -p` calls |

### Orchestration

| Shape | Contexts | Right when | Ceiling |
|---|---|---|---|
| Single session | 1 | Whole task fits in one context | n/a |
| Subagent | 2 | One isolable sub-task | Depth 3 |
| Fan-out | 1 + N | Independent parallel sub-tasks | 20 concurrent, depth 3 |
| Pipeline | 1/stage, sequential | Real ordering constraint | n/a |
| Team | 1 lead + N | Non-overlapping files, live questions | Per-team limits |
| Workflow | Fixed script | Repeatable, deterministic procedure | n/a |

| Question | `/run-harness` | `/run-conductor` |
|---|---|---|
| Who decides the next stage | The model, reading prose | `conductor advance` |
| Same input twice, same output? | Not guaranteed | Guaranteed |
| Resume mechanism | `--from <stage_id>` / `--resume-at` | `--run-id <id>` |
| Continuation gates, in order | 1. depth ceiling → `story_oversized` 2. verdict != progressing → `stalled_no_progress` 3. deep + no commit → `stalled_no_progress` | — |

| Concept | Key fact |
|---|---|
| `failure_code` | Closed enum; `detail` carries nuance, `failure_code` the countable key |
| Ranking formula | `frequency × severity × (1 / fix_complexity)` |
| Human gate | Confirms no PII/leak only — not a worth-filing judgment |
| `baselines.yaml` | Populated by the first real eval run; may rise, never silently fall |
| Concurrent subagent ceiling | 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) |
| Nesting depth ceiling | 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`) |

### Verification

| Situation | Weak move | Strong move |
|---|---|---|
| Reviewing an agent's diff | Read for shape and plausibility | Re-run the specific claim in its published form |
| Gating on file content | `grep`, trust the exit code | Assert `file --mime-encoding` is text-like first |
| Certifying a build artefact | Hash the pre-write buffer | Hash the artefact after it is written |
| Ranking evidence | Trust the agent's own success claim | re-run > test > compile > transcript > diff > regex > structural check > agent's claim |

| Law | One-line rule | Real incident |
|---|---|---|
| §3.10.5 | Pin the harness beside the digest | MD5 over a patched, unwritten harness buffer |
| §3.10.6 | Never let a status row point at a missing path | `igm:snykAssistant`/`igm:wizAssistant` — 2 false misses, every preflight |
| §3.10.7 | A closed lane is not a verified lane | e2e-08: 3 lanes closed, 1 impossible spec rubber-stamped, $1.46 |
| §3.10.8 | Rank evidence; executable beats structural | 94 green tests vs. 1 real run — 0 vs. 1 defects caught |

| Item | One line |
|---|---|
| `PostToolUse` (`Write`\|`Edit`) | Formatter/linter, once per edit |
| `Stop` | Fast local check only (compile, not full suite) |
| CI | Full suite, security scans, eval baselines |
| Review-capacity arithmetic | 8 eng × 6 review-hrs/day = 48 eng-hrs/day; 20 min/diff = ⅓ eng-hr/diff; 144 diffs/day |
| Past the ceiling | More agents → unreviewed diffs, not velocity |

For the Q&As and the 5 puzzles built on this material, see
[92-interview-internals-b.md](92-interview-internals-b.md).

## Open questions

None.

## Atomic concept checklist

One flat, sorted list — by subject folder, then by the order the concept appears within that folder —
covering all six parts of the guide (PART 0 ground truth through PART 5 interview material). Each
bullet is a falsifiable, self-quizzable claim, not a topic label. Grouping is signalled only by this
prose, never by a heading inside the list, so the parser sees one unbroken flat list below.

- the model is one function: text in, text out
- the model generates via next-token prediction and sampling
- the token is the unit of both cost and the context limit
- fluent output does not imply correct output (confabulation)
- model names encode capability tiers as of August 2026
- an agent is a model plus a loop plus tools
- the context window is a hard ceiling on input plus output tokens together
- a request is an ordered list of role-tagged messages
- the context window is the argument list of the next call, not a persistent memory
- cost and latency scale with total conversation length, not the size of the latest message
- prompt caching makes appending cheap and editing the beginning of a prompt expensive
- the 200K token budget is itemised, and most of it is not free for task work
- "the model forgot" is almost never a bug — it is a context-budget effect
- the agent loop runs in three steps: call, tool_use, tool_result
- a tool is defined by a name, a description, and a JSON schema
- the model does not call a tool directly — it emits a tool_use block for the harness to execute
- a tool_result becomes context, so a verbose tool is a context leak
- a single turn is bounded by two different limits at once
- the model chooses which tool to call from its description alone, not its implementation
- a complete agent loop can be walked end to end with the token cost stated after every step
- Claude Code ships a fixed set of built-in tools grouped by category
- deferred tools and ToolSearch avoid loading every tool's full schema up front
- extended thinking spends reasoning tokens before the model answers
- Claude Code is the harness around the model, not the model itself
- the Agent SDK and the raw API run the same loop, with the harness written by you
- installing and authenticating is the first orientation step
- there are three ways into Claude Code: interactive, print mode, and the SDK
- the diagnostic ladder has a specific order to try steps in when something misbehaves
- reading a real /context output is the single most important orientation habit
- /compact, /clear, and a fresh session are three different resets with different costs
- /rewind restores file checkpoints, not just conversation state
- three input prefixes change what a typed line means to Claude Code
- a session's transcript lives on disk at a fixed path for a bounded retention period
- --safe-mode and --bare isolate whether a problem is your config or the tool itself
- a first-session checklist front-loads the orientation habits
- .claude/ is configuration-as-code, not a registry
- the project .claude/ tree has a full, fixed inventory of subdirectories and files
- ~/.claude/ mirrors the project tree for the user scope, and ~/.claude.json is a separate tool-owned file
- ~/.claude.json is written by Claude Code for Claude Code, not a file a human hand-edits
- CLAUDE_CONFIG_DIR relocates the entire user-scope configuration tree
- Claude Code discovers configuration by walking up from the working directory
- the sdlc-harness's real .claude/ tree shows a minimal working configuration in practice
- the harness's settings.json carries exactly two keys
- the harness ships nine command files as its command surface
- the harness ships exactly one skill, playwright-cli
- certain state deliberately does not live in .claude/
- one invariant about .claude/ discovery is the single most useful fact to remember
- four settings files each reach a different scope
- settings precedence has five layers, with managed settings always on top
- settings precedence is not simple specificity, and the CLI does not always win
- Claude Code creates only certain settings files automatically, and only at specific times
- the local settings file's relationship to git tracking changed across versions
- in a worktree, the local settings file follows the main checkout, not the worktree
- committing .claude/settings.json is a code-review decision about what teammates inherit
- some settings keys never apply from a repository file, and others wait for workspace trust
- settings keys fall into fifteen groups, of which twelve are touched first in practice
- the twelve commonly-touched settings keys each have documented concrete values
- the env settings key injects environment variables that reach both hooks and Bash
- the harness's real settings.json demonstrates a minimal working key set
- a setting's effect must be verified, not assumed, once written
- an unrecognised settings key is silently ignored rather than erroring
- managed settings are the organisational control surface, not a per-developer file
- --setting-sources chooses which settings layers load at all for a run
- CLAUDE.md loads from a location hierarchy, root down
- @path imports pull other files into CLAUDE.md
- a CLAUDE.md's size and cost trade off against whether its instructions actually get followed
- .claude/rules/ holds modular instruction files discovered recursively
- path-specific rules make a large instruction set affordable by scoping it
- the paths: glob frontmatter has brace-expansion mechanics, a shared budget, and a bracket pitfall
- user-level rules follow the same root-down loading logic as CLAUDE.md
- Claude Code does not read AGENTS.md
- claudeMdExcludes excludes paths from CLAUDE.md discovery in a monorepo
- claudeMd in managed settings can inject or restrict memory content org-wide
- auto memory is the four kinds of thing Claude Code writes down for itself
- auto memory's MEMORY.md load is capped at 200 lines or 25 KB, whichever hits first
- auto memory does not load into a subagent's context
- only part of auto memory survives a /compact
- what memory actually loaded into a session can be checked directly
- diagnosing "Claude ignored my CLAUDE.md" follows a fixed ladder of checks
- a reader's own two-level CLAUDE.md setup can be accounted for entry by entry
- a per-entry token accounting quantifies what each CLAUDE.md rule costs
- each CLAUDE.md entry should be judged for whether it belongs there, in a skill, or in a path-scoped rule
- permission enforcement lives in the harness, not in the model's judgment
- permission evaluation order is deny, then ask, then allow
- a broad deny rule cannot carry allowlist exceptions
- a bare deny removes the whole tool; a scoped deny blocks only the matching call
- permission rules follow a fixed syntax of tool, specifier, and pattern
- Bash permission specifiers match via a wildcard table, not free-form regex
- each part of a compound Bash command is matched and saved as a separate permission rule
- the Bash command string is rewritten before permission matching ever runs
- a fixed wrapper list is stripped before matching, but two wrapper shapes are not covered
- the env-assignment stripping asymmetry is deliberately the safe direction
- environment runners are not stripped by the wrapper list, which is a real permission hole
- some exec wrappers cannot be auto-approved by a prefix rule
- a built-in set of Bash commands is always treated as read-only for the fast path
- a shell redirection adds a permission check on its target path
- Read/Edit path rules use gitignore-style patterns with four possible anchors
- a Read deny also blocks Edit and Write on that path, but not NotebookEdit
- file permission rules are checked only against Edit(path) and Read(path), not other tool shapes
- the permission system's boundary covers built-in tools and recognised Bash commands, not an arbitrary subprocess
- WebFetch(domain:…) rules, plus a form that allows or denies every fetch, cover the web specifier
- MCP permission rules have three forms, and the parenthesised form is silently skipped
- Agent(Name) rules govern subagent dispatch, including the built-in agents
- parameter matching for deny/ask works on any built-in tool, not just Bash and paths
- Cd rules are not model-invocable, and allowlist mode flips their default
- a permission mode is a baseline; permission rules override it
- acceptEdits mode has a real, specific command list, which is the point of the setting-sources incident
- auto mode has a classifier review calls instead of the human
- bypassPermissions does not mean permissions are turned off
- permission kill switches live in managed settings so a developer cannot disable them
- a working directory is a file-access grant, not a configuration root
- /cd moves the configuration surface; --add-dir never does
- workspace trust gates specific behaviour, and the gate is one-sided
- workspace trust is keyed by a specific identity, not just a path string
- a -p or SDK session never shows the trust dialog
- a tracked local settings file, or a symlinked .claude, stops being treated as your own file
- a rule-source lookup is the scriptable part of /permissions
- deny is absolute — a different composition rule from ordinary settings precedence
- /permissions reads rules and their source file, and edits it makes land mid-turn
- three per-run flags override permissions, each with different reach
- the OS sandbox is a layer below the permission system, not a replacement for it
- a real permission block for a Java/Spring Boot repository can be proved rule by rule
- the harness pairs a broad Bash(*) allow with an explicit deny-list
- skills come from four locations but present one command surface
- a custom slash command is itself a skill
- a skill is a named, on-demand instruction bundle the model can invoke
- skills load from four locations with a fixed conflict order
- nested skills are the mechanism for scoping skills inside a monorepo
- a skill loads progressively — name and description first, body only on invocation
- the skill listing has a token budget, and descriptions are cut once it overflows
- a skill's frontmatter has a fixed, complete field set
- allowed-tools pre-approves tool calls; it does not restrict which tools a skill may use
- a skill's first line follows a specific rule, and frontmatter booleans have specific accepted spellings
- who can invoke a skill is governed by three settings across four invocation shapes
- a skill body supports seven string substitutions
- dynamic context injection runs a shell command and replaces its placeholder with the output
- three skill mechanics commonly bite in practice
- disableSkillShellExecution turns off dynamic context injection org-wide
- a skill's content is injected as one message and then stays in context
- a skill's re-attachment after compaction is capped at 5,000 tokens each and 25,000 combined, newest-first
- context: fork, agent:, and background: run a skill off to the side of the main conversation
- a skill is a directory, and ${CLAUDE_SKILL_DIR} resolves to its own supporting files
- a reference-library skill costs nothing until it is actually invoked
- the bootstrap skill is an orchestrator over existing agents, not a rewrite of their logic
- prompt composition lets a skill reuse another spec's body without duplicating it
- a skill description that names its topic instead of its trigger phrase fails to auto-invoke
- a built-in skill and a bundled skill are not the same kind of thing
- skills have both a visibility setting and a kill switch
- a real skill can be built for a specific repository's own checklist workflow
- a decision table exists for choosing among CLAUDE.md, a skill, a hook, and a subagent
- a subagent is a separate context running its own instructions
- a subagent definition location has a precedence order like other configuration
- a subagent definition's frontmatter has a fixed field set
- a subagent's description field decides whether it is ever automatically dispatched
- a subagent's tools field is a genuine restriction, unlike a skill's allowed-tools
- the parent's routing budget reads only subagent descriptions, and that has a ceiling
- tools and disallowedTools extend to MCP prefixes and can restrict a subagent's own sub-delegation
- only specific things cross the subagent context boundary inward
- the git-status snapshot a subagent sees is taken at parent session start, not at dispatch time
- a subagent returns exactly one message out, and most of its internal work does not cross back
- subagents and skills invert each other's context-isolation trade-off
- there are four built-in subagent types, each giving up something different
- foreground and background subagent dispatch trade off one real thing
- a fork subagent is the exception to the subagent context-isolation rules
- subagent concurrency and depth limits have numbers, and specific behaviour at each ceiling
- subagent names follow specific naming rules
- a subagent can have persistent memory across dispatches
- a subagent can be resumed rather than redispatched fresh
- a subagent can be invoked at three different levels
- a subagent's ~2x cost comes from a specific mechanism, and isolation still wins despite it
- delegating to a subagent only pays off under specific conditions
- the subagent output protocol writes findings to a file and keeps the return message small
- a pointer-body subagent definition names read/out-of-scope boundaries rather than inlining behavior
- a subagent has a write boundary, and specific tools it never gets regardless of its tools field
- exactly one writer owns each output path, ever, in a multi-agent pipeline
- the subagent return protocol is one message and a path, never a payload
- four CLI flags control persona/system-prompt behaviour, and they are easily confused
- --agent and --append-system-prompt are the core persona-flag confusion
- --system-prompt/--system-prompt-file replace the system prompt rather than decorating it
- --append-subagent-system-prompt is the one flag that reaches every subagent, not just the top-level session
- --exclude-dynamic-system-prompt-sections strips per-machine dynamic facts from the system prompt
- the harness engine itself chooses --agent, not --append-system-prompt, for persona loading
- load_agent_prompt() strips frontmatter with a regex before using an agent file as a persona
- choosing --append-system-prompt when the caller meant --agent is a common persona-flag mistake
- a hook is a guarantee, where CLAUDE.md and a skill are only context
- a hook's configuration schema is event, matcher group, and handler list
- hooks have five handler types, and two of them put a model back in the loop
- command and http are the two deterministic hook handler types
- hook events fall into twelve groups, and the exact count diverges from the widely-repeated figure
- only some hook events can block, and each uses a specific field to do it
- a hook payload has fields that are always present and fields that only appear for specific events
- a hook's stdin payload carries more fields than a first look through it shows
- hook exit codes define three paths, one of which needs no JSON output at all
- exit code 2 overrides a JSON permissionDecision: "allow"
- a hook's JSON output contract has a fixed set of fields
- each hook event honours a different decision field in its JSON output
- a hook cannot unblock a permission deny
- hook path placeholders and environment variables behave differently inside a plugin
- hooks can be configured from multiple sources, each with a different lifetime
- hooks have global kill switches but no per-hook switch
- /hooks is a read-only browser over the currently active hook configuration
- the harness's real hooks.json shows a working multi-handler configuration
- the harness uses three separate SessionStart handlers rather than one combined script
- the harness's PostToolUse matcher narrows which edits trigger the hook
- check-init.sh is a masterclass in writing an advisory (non-blocking) hook
- an advisory hook's output is tagged so the model can distinguish it from ordinary context
- an advisory hook script is written defensively so a script failure cannot break the session
- an advisory hook uses a content hash rather than a version constant to detect staleness
- the removed auto-reindex hook left a mark in the config, whose full story is told elsewhere
- the auto-reindex hook incident cost 100+ GB, and the first fix attempt made it worse
- three hooks were built end to end and proved to fire
- the blocking-guard pattern is the standard shape for a hook that must reliably deny a dangerous action
- a hook can lie to itself in three distinct ways
- MCP is a protocol that lets Claude Code call tools hosted by an external server
- MCP has multiple transports, and each one wins in a different deployment shape
- an MCP server registration lives at one of several configuration scopes
- a project-scoped MCP server requires an explicit approval step
- enabledMcpjsonServers answers a narrower question than its name suggests
- an MCP tool's naming form carries through into how it is matched in permissions and hooks
- every connected MCP server imposes a per-turn token tax whether or not it is used that turn
- an MCP failure mode can look like a permission refusal but is not one
- MCP governance keys can be locked at a specific settings scope
- --mcp-config registers per-run MCP servers from the command line
- an LSP server is the cheaper cousin of an MCP server for code-navigation tasks
- there are three official LSP plugins, and jdtls-lsp is the Java one
- an LSP server should be registered, its tax measured, and its write tools closed off
- a plugin bundles skills, agents, hooks, and MCP servers, and earns its cost only past a certain reuse point
- a plugin has a fixed directory layout, and one layout mistake ships a plugin that does nothing
- plugin.json's remaining fields govern how an update actually reaches an installed copy
- a plugin's skills always coexist by namespace, but its agents can be silently overridden by a same-named local agent
- a plugin's own settings.json carries exactly two keys
- .claude-plugin/marketplace.json is the marketplace manifest
- Claude Code refuses to auto-add a cross-marketplace plugin dependency
- an unresolved plugin dependency produces a cryptic error, but a specific diagnostic explains it
- the plugin command surface includes /plugin, marketplace commands, and two session-only flags
- claude plugin init scaffolds a plugin that needs no marketplace at all
- the plugin governance surface has seven keys, all but one managed-settings-only
- strictPluginOnlyCustomization is the enterprise endgame of plugin governance
- marketplace.json doubles as documentation living inside a machine-read config file
- a real plugin.json carries version, licence, and dependency fields together
- ${CLAUDE_PLUGIN_ROOT} resolves to the plugin's install directory, not the source repository
- fixing a plugin path bug means refusing to proceed rather than guessing at a path
- a .claude/ tree can be converted into a plugin
- reading /context should be a routine habit, not an occasional reference lookup
- a session's startup tax can be itemised for the reader's own machine
- the four biggest avoidable context costs can be ranked
- bounding tool output is a discipline for keeping context economical
- autocompaction fires based on specific settings, not a fixed universal threshold
- only specific state survives a compaction, which dictates what to do before one happens
- PreCompact and PostCompact are the hook seam for state a compaction would otherwise lose
- the last 40 lines of the transcript are kept verbatim before summarisation during a compaction
- there are four different resets, each right for a different situation
- an append-only session stays cache-cheap, but a paused session is not free
- isolation is the primary context-economy lever, and the arithmetic behind it can be worked as a budgeting rule
- a working session protocol can be shipped as a SessionStart reminder
- compacting mid-task instead of at a task boundary is a context-economy trap
- plan mode is a first-class step, not an optional courtesy
- a plan beats a better prompt because the correction point moves earlier
- test-first turns a failing test into a specification a machine can check
- small diffs are a practice that trades velocity for reviewability
- prompting that matters reduces ambiguity; it does not persuade the model
- briefing an agent means giving it what a new teammate would need, not a terse command
- the verification habit is never claiming success without a checkable artefact
- a second pass in fresh context — /code-review, /security-review, self-review — catches what the first pass could not see
- an agent is a bad fit for specific classes of task
- a worked Java example demonstrates the full practice end to end
- statusLine and subagentStatusLine give cheap situational awareness
- keybindings are configurable via ~/.claude/keybindings.json
- there is a central rule for choosing deterministic code over an agentic call, sitting above any mechanism-level table
- the deterministic-vs-agentic rule is sourced verbatim from the harness's own reasoning
- the deterministic-vs-agentic decision table continues beyond its first branch
- "the model could do it" is not an argument for using the model to do it
- worked examples show both sides of the deterministic/agentic line
- idempotence is the property that makes a bootstrap script safe to re-run
- bootstrap-uv.sh is a documented exception to the idempotence rule
- a human-authority gate should deny the tool, not rely on the model's willingness to refuse
- prompting can be used to push an agentic call toward deterministic behaviour
- the governance threat model can be stated in plain terms
- prompt injection is untrusted data becoming an instruction the model follows
- governance controls against prompt injection can be ranked by how well they actually hold
- managed settings must come from a specific trusted source before they can lock anything
- the lock family of settings closes the door on a developer editing a restriction back open
- telemetry, cleanup, and a network preflight are the things that leave the machine
- login and version pinning are governed at organisational scale
- attribution and audit settings determine who is recorded as making an agent-authored commit
- the harness's own governance posture can be assembled from its real configuration files
- shipping a capability as a versioned plugin, not tips in a wiki, is the harness's rollout argument
- an assembled request is built from six ordered segments
- CLAUDE.md lives in a specific segment of the assembled request, which is the whole point of ordering it there
- the cached prefix depends on segment ordering not being arbitrary
- tool schemas are a cost line inside the assembled request, independent of which tools get called
- the skill listing itself has a measurable, budgeted cost
- system-reminder blocks are injected state, not an instruction from the user
- a real transcript can be read to see exactly what was assembled and billed
- transcript.py is a real production reader that extracts usage data from a transcript
- a compaction replaces the transcript with a shorter one via a summarization call; it does not delete or save
- the compaction threshold is a ratio of used tokens to window size
- skill re-attachment after compaction is capped at 5,000 tokens per skill and 25,000 combined, newest-first
- project-root CLAUDE.md re-reads from disk on every compaction, but nested and path-scoped files reload only when their path is matched again
- conversation-only state is irrecoverably lost at compaction unless it is written to a file first
- PreCompact and SessionStart together form the persistence seam across a compaction
- a fresh session usually beats a session compacted three times, on both cost and fidelity
- one tool call passes through a five-stage permission evaluation pipeline
- the PreToolUse hook sits after the deny/ask/allow stage and cannot unblock a settings-level deny
- Bash permission matching can be traced command by command through the pipeline
- a read-only fast path skips full evaluation, except for two cases that force re-entry
- symlinks and Windows paths are two more inputs normalised into the same path matcher
- tool consultation for permission checks extends past the Edit/Read-only rule to other tools like Grep/Glob
- the OS sandbox enforces a specific boundary and has a specific blind spot
- a ten-command permission set can be verified end to end against the installed Claude Code binary
- four distinct token quantities are billed, each with its own envelope field
- per-model pricing differs by a ratio between model tiers
- conversation length dominates session cost, provable by working a full session's arithmetic
- prompt caching has a default TTL, and a paused session crossing it costs more on resumption
- a subagent's ~2x cost premium comes from a specific, itemisable mechanism
- a system needs three distinct ceilings — turns, budget, and wall-clock — because no one alone is sufficient
- cost can be read back through the JSON envelope, /cost, or modelPricing
- running the same task cold versus warm measures the real cache effect on cost
- an unbounded agent loop is an unbounded invoice
- an effort level changes reasoning depth, not which model is used
- effort and model can be overridden per skill or per agent, each with a different lifetime
- model routing is fundamentally a cost decision
- several knobs sit beneath the routing decision besides the visible model picker
- fastMode/\/fast produce faster output on the same model, not a cheaper downgrade
- routing everything to the cheapest model is a named failure mode
- claude -p takes one prompt in and returns one machine-readable envelope out
- headless mode has three output formats and two input formats, chosen by different criteria
- the JSON envelope has a fixed field set, demonstrable on a real example
- stream-json extras earn their complexity only under specific conditions
- --json-schema is the difference between parsing prose and receiving structured data
- a production headless wrapper needs a specific checklist of flags
- a session ID pins specific state, and resuming it restores only part of that
- claude setup-token generates the CI credential an unattended run needs, without exposing interactive login
- background and remote execution route output somewhere specific when no one is watching interactively
- headless failures fall into three distinct classes, not one undifferentiated bucket
- an unparseable envelope is captured as a 500-character snippet of stdout/stderr
- the last successfully parsed error envelope should be kept, not discarded
- every headless knob resolves in the order: parameter, then environment variable, then default
- the four module-level defaults each exist for a specific, documented reason
- DEFAULT_MAX_TURNS is 160, not 40, because of a specific incident history
- one resolution knob skips the environment-variable tier entirely
- --resume is used by the coder to resume its own leg, but the verifier never resumes
- --add-dir is a seam kept open in the harness but not used by default
- the incident setup is an isolated per-story git worktree, distinct from the main checkout
- --setting-sources project resolves .claude/settings.json against cwd, not the repository root
- in the incident, the harness's own project settings rules never loaded because of the cwd mismatch
- the incident's observed symptom was precise and diagnosable, not vague
- the incident fix lands at a specific, generalisable point
- the fix's code cites its own ADR so the next engineer finds the incident record
- resolving a path against cwd is a cwd-shaped bug, generalisable beyond this one incident
- silent degradation is worse than a loud failure, as a general law
- the incident can be told in 90 seconds as symptom, mechanism, fix, then generalisation
- there are three levels of building on Claude — CLI, Agent SDK, raw API — and each gives something up
- the Messages API request/response shape is small enough to read in full
- at the raw API level, you write the tool-use dispatch loop yourself
- prompt caching at the API level uses explicit cache breakpoints with their own cost
- the Agent SDK has specific settings-resolution mechanics: resolveSettings(), managedSettings, parentSettingsBehavior, and a trust shorthand
- the harness deliberately chose subprocess calls over the Agent SDK
- there is no first-party Java Agent SDK
- an agent call should be treated as a remote dependency with its own failure modes
- there are six named orchestration shapes for composing multiple agent calls
- a fan-out shape needs an explicit join step to combine its parallel results
- in a pipeline, no stage writes its own input — only its own output
- this repository's per-topic note pipeline is a real five-stage pipeline example
- /run-harness and /run-conductor are two different executors over the same underlying state
- both executors share folded state, but --resume-at behaves differently between them
- progress-verifier judges progress against a rubric, independent of which executor is driving
- continuation checkpoints classify a run as progressing or stalled
- a closed failure_code vocabulary, plus a human gate, guards the calibration loop
- an eval is the only way to know a prompt change actually helped
- verification has a fundamental asymmetry between writing and checking that the whole guide builds toward
- skimming a diff is the review method worst matched to what an agent-generated diff actually needs
- the law: re-run every published artefact in its published form, not a proxy for it
- the law: a checker whose input can switch it off is worse than no checker at all
- the law: certify from final on-disk state, never from a pre-write computation
- the law: pin the harness version beside any digest it produced
- the law: never let a status row point at a missing path
- the law: a closed lane is not a verified lane
- executable evidence outranks structural evidence, on a specific ranked scale
- automated gates should run fast checks in Stop and slow checks in CI
- certain command shapes defeat a permission matcher and therefore defeat your own automated gates
- review capacity, not any tool ceiling, is the real limit on how much agent output a team can safely ship
- a working CLAUDE.md under 100 lines can be built for a real service
- splitting a CLAUDE.md three ways and measuring the difference shows where the split earns its keep
- a complete settings.json can be built for the same example repository
- a settings.local.json overriding exactly one key can be proven to win over the tracked file
- committing settings and verifying a fresh clone behaves identically must also account for workspace trust
- a PostToolUse hook on Edit|Write can format only the one file that changed
- a PreToolUse hook on Bash can deny a destructive command, and this can be compared against a settings-level deny using exit code 2
- a SessionStart hook can report branch, dirty files, and failing tests as advisory lines
- a Stop hook can refuse to end the turn while the build is red
- all four hooks in the set can be proved to have fired
- a minimal skill combines frontmatter, $ARGUMENTS, one dynamic injection, and one on-demand file
- the same capability built as a bare command file shows exactly what the skill form buys over it
- a skill can be constrained to be invocable only the intended way
- a paths-gated skill activates only for matching files, such as **/*.java
- a thin wrapper skill and a shared executor can be composed as a pair without duplicating logic
- a read-only reviewer subagent combines a tools allowlist, a chosen model, a fixed output contract, and a verdict line
- a test-runner subagent can be restricted to Bash(mvn test *) only
- memory: project lets a subagent's memory persist across real sessions
- denying Agent in a subagent's own tools field proves it cannot spawn further subagents
- comparing a built subagent against the harness's real progress-verifier.md and calibrator.md reveals design choices
- ClaudeRunner is the process boundary between Java orchestration code and the claude CLI
- an orchestrator needs the same three ceilings — turns, budget, wall-clock — implemented in Java
- --settings <absolute path> prevents the cwd-relative resolution incident
- the Java orchestrator's resolution order must let an explicit zero survive, not be treated as absent
- a classified retry ring and a bulkhead ring wrap ClaudeRunner.run()
- a two-stage pipeline's invariant can be proved by re-running it
- a cost report can be built purely by reading the envelopes already in hand, with no extra API calls
- the built ClaudeRunner can be diffed against the harness's real agent.py
- a plugin can be packaged and tested locally with --plugin-dir
- claude plugin validate, and its --strict mode, checks a plugin before publishing
- a plugin can be published to a local marketplace for testing
- bumping a plugin's version and reinstalling proves what an installed copy actually runs
- claude plugin list --json's errors array surfaces an unresolved plugin dependency
- a built plugin and marketplace can be diffed against the harness's real ones
- verify.sh is a shell script that outranks a model's own opinion of its output
- a verification harness's first two gates each have a defined failure posture
- the NUL-byte case is made to fail loudly rather than silently skip
- verify.sh can be wired into both a Stop hook and a CI job using the same two gates
- a skill eval tests three prompts that should trigger the skill and three that should not
- a Staff-level interview answer needs a framing paragraph beyond the mechanism
- there are three good questions to ask an interviewer back, by design

---

**Leaves covered:** none exclusively — this file closes §3.1–§3.10 (96 leaves) and carries the topic-wide atomic concept checklist over all six parts
**Leaves deferred:** none
**Diagrams included:** none — this file indexes the guide rather than illustrating a mechanism
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 666
