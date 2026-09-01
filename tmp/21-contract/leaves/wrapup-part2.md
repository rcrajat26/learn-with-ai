### §2.1 Subagents

2.1.1 What a subagent is, mechanically: a **separate context window** running the same loop, given
      a task string, returning a final message. Nothing else crosses the boundary. `[ZERO]`
2.1.2 Definition file locations and precedence, highest first: managed settings → `--agents` CLI
      JSON → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/`. `[DOC]` `[NUM]`
2.1.3 `[TRAP]` Note the inversion against skills: for **agents**, project beats user; for
      **skills**, personal beats project. Two subsystems, two orders. `[TRAP]` `[DOC]`
2.1.4 The file format: YAML frontmatter plus a markdown system prompt. `[DOC]`
2.1.5 Frontmatter, every field: `name`, `description`, `tools`, `disallowedTools`, `model`,
      `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`,
      `effort`, `isolation`, `color`, `initialPrompt`, `experimental`. `[DOC]`
### §2.1 Subagents

2.1.6 `description` is the routing signal — it says *when to delegate*, not what the agent is.
      The combined description budget across custom agents is ~**15,000 tokens**. `[DOC]` `[NUM]`
2.1.7 `tools` as an allowlist vs `disallowedTools` as a denylist; MCP-prefix forms; restricting
      which agents an agent may spawn with `tools: Agent(worker, researcher)`. `[DOC]`
2.1.8 **What loads at subagent startup**: its own system prompt + environment, the delegating task
      message, the full `CLAUDE.md` hierarchy (except Explore/Plan), a git-status snapshot from
      parent session start, preloaded `skills`, the sibling roster. `[DOC]` `[NUM]`
2.1.9 **What does not load**: conversation history, the main output style, auto memory, previously
      read files or invoked skills. Forks are the exception and inherit everything. `[DOC]`
2.1.10 `[TRAP]` Therefore a subagent knows nothing your session learned. Everything it needs goes
       in the task string or a file it is told to read. `[TRAP]`
### §2.1 Subagents

2.1.11 The four built-ins and what each is for: `Explore` (read-only search), `Plan` (read-only
       research), `general-purpose`, `claude` (catch-all). `[DOC]`
2.1.12 Foreground vs background execution; `background: true`; `Ctrl+B`;
       `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`; how permission prompts surface from a background
       agent. `[DOC]`
2.1.13 **Forks** (`/subtask`, `context: fork`): inherit the whole conversation and system prompt,
       share the prompt cache (cheaper), cannot spawn further forks. When a fork beats a fresh
       agent. `[DOC]`
2.1.14 Limits and guardrails, with numbers: default **20** concurrent subagents
       (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), nesting depth **3**
       (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), and the tools never available in a subagent
       (`AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `Workflow`). `[DOC]` `[NUM]`
2.1.15 Naming rules: no `:` (reserved for plugin scoping), no leading `-`. `[DOC]`
### §2.1 Subagents

2.1.16 Persistent agent memory: `memory: user|project|local` and the three directories it maps to.
       `[DOC]`
2.1.17 Resuming a subagent via `SendMessage` with its ID or name; where subagent transcripts live
       (`~/.claude/projects/{project}/{sessionId}/subagents/`). `[DOC]` `[VERSION]`
2.1.18 Invocation, three levels: natural language (Claude decides), `@"name (agent)"` mention
       (guaranteed), `claude --agent <name>` or the `agent` setting (whole session). `[DOC]`
2.1.19 The cost model: a subagent costs roughly **2×** the tokens of inline work because context
       must be re-supplied; a team of agents 3–4×. State when that is worth it. `[NUM]` `[PROVE]`
### §2.1 Subagents

2.1.20 The three cases where it pays: verbose input with a small answer; genuinely parallel work
       with non-overlapping writes; a different capability set (read-only auditor, no-network
       reviewer). `[NUM]`
2.1.21 The output protocol that makes delegation actually save context: **agents write findings to
       files and return status + a few findings + a path.** Message bodies are not a data channel.
2.1.22 `[CASE]` `progress-verifier.md` — 20 lines, and four transferable design properties: body as
       a pointer to a versioned prompt file; a machine-parseable output contract
       (`## Progress Verdict: progressing|stalled`); explicit read boundaries; artifacts-only
       evidence discipline with an explicit ban on inspecting the coder's live session. `[CASE]`
### §2.1 Subagents

2.1.23 `[CASE]` `calibrator.md` — enumerated write boundaries (two paths it may write, four it may
       not) and the line **"No Jira API tool is ever given to this agent."** Capability denied at
       the tool layer; the prose only documents it. `[CASE]`
2.1.24 `[TRAP]` Parallel agents must partition the **filesystem**, not the topic. Folder-scoped
       lanes plus one flat shared directory is not a partition. A same-slug collision overwrites
       silently and leaves no orphan to notice. **One writer per output path, ever.** `[TRAP]`
       `[INCIDENT]`
2.1.25 `[BUILD]` Write a `test-runner` agent for a Java repo: read-only plus `Bash(mvn test *)`,
       `model: haiku`, a fixed output contract, and a verdict line the caller can grep. `[BUILD]`
       `[JAVA]`



### §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.1 `--agent <name>` loads a **registered** agent — its full system prompt, model and tool
      allowlist. The parity mechanism for programmatically spawning a subagent. `[DOC]`
2.2.2 `--append-system-prompt <text>` **appends to the default** system prompt. The default persona
      is still there; you decorated it. `[DOC]` `[TRAP]`
2.2.3 `--system-prompt` / `--system-prompt-file` **replace** the whole thing. What you lose.
      `[DOC]`
2.2.4 `--append-subagent-system-prompt` for every subagent; `--exclude-dynamic-system-prompt-sections`
      to move per-machine sections out of the cached prefix. `[DOC]` `[VERSION]`
### §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.5 `[CASE]` `engine/agent.py` documents the distinction explicitly and calls `--agent` "the
      parity mechanism for an auto-spawned subagent, not `--append-system-prompt` (which only
      appends to the default prompt)". Quote it. `[CASE]`
2.2.6 `[CASE]` `load_agent_prompt()` strips the `--- … ---` frontmatter before appending, because
      YAML metadata leaking into a system prompt is noise the model tries to interpret. The regex
      and why it is anchored. `[CASE]` `[SOURCE-EQUIV]`
2.2.7 `[TRAP]` Choosing `--append-system-prompt` when you meant `--agent`: the symptom is an agent
      that behaves *almost* right and ignores its tool restrictions, because it never had any.
      `[TRAP]`



### §2.3 Hooks

2.3.1 What a hook is: a command **the harness runs** at a lifecycle event, not something the model
      decides to run. Therefore the only mechanism that *guarantees* something happens. `[ZERO]`
      `[DOC]`
2.3.2 The configuration schema: `hooks.<Event>[] → { matcher, hooks: [{ type, … }] }`, plus
      `if`, `timeout`, `statusMessage`, `once`. `[DOC]`
2.3.3 The five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. What each is for,
      and that the last two put a model in the enforcement path. `[DOC]` `[VERSION]`
2.3.4 `command` handler fields: `command`, `args`, `async`, `asyncRewake`, `shell`. `[DOC]`
2.3.5 `http` handler: `url`, `headers`, `allowedEnvVars`, plus the `allowedHttpHookUrls` and
      `httpHookAllowedEnvVars` settings that fence it. `[DOC]`
### §2.3 Hooks

2.3.6 The full event catalogue (32 events as of v2.1.2xx), grouped so it is learnable rather than
      memorised: session lifecycle (`SessionStart`, `Setup`, `SessionEnd`), prompt
      (`UserPromptSubmit`, `UserPromptExpansion`), tools (`PreToolUse`, `PostToolUse`,
      `PostToolUseFailure`, `PostToolBatch`), permissions (`PermissionRequest`,
      `PermissionDenied`), turn (`Stop`, `StopFailure`), subagents (`SubagentStart`,
      `SubagentStop`), tasks (`TaskCreated`, `TaskCompleted`, `TeammateIdle`), context
      (`PreCompact`, `PostCompact`, `InstructionsLoaded`), environment (`ConfigChange`,
      `CwdChanged`, `DirectoryAdded`, `FileChanged`), worktrees (`WorktreeCreate`,
      `WorktreeRemove`), MCP (`Elicitation`, `ElicitationResult`), UI (`Notification`,
      `MessageDisplay`). `[DOC]` `[NUM]` `[RESEARCH]`
2.3.7 Which events **can block** and which cannot — the table, because reaching for a hook that
      cannot block is the most common design error here. `[DOC]` `[NUM]`
2.3.8 `matcher` semantics: `*`/empty/omitted matches all; `|` or `,` for an exact list; anything
      with special characters is a regex. `[DOC]`
2.3.9 Matcher values differ per event: tool name for tool events, session type
      (`startup|resume|clear|compact|fork`) for `SessionStart`, end reason for `SessionEnd`, agent
      type for subagent events, config source for `ConfigChange`, error type for `StopFailure`,
      filenames for `FileChanged`. `[DOC]`
### §2.3 Hooks

2.3.10 The stdin JSON every event receives: `session_id`, `prompt_id`, `transcript_path`, `cwd`,
       `permission_mode`, `hook_event_name`, `effort.level`; plus `agent_id`/`agent_type` when
       running under a subagent. `[DOC]`
2.3.11 Event-specific stdin payloads: `tool_name`/`tool_input`/`tool_use_id`, `user_input`,
       `last_assistant_message`/`stop_reason`, `file_path`/`change_type`. `[DOC]`
2.3.12 **Exit-code semantics**, precisely: `0` = success (stdout goes to the debug log, except
       `UserPromptSubmit`/`UserPromptExpansion`/`SessionStart` where it is shown to Claude);
       `2` = blocking error and **the only code that blocks without JSON**; anything else =
       non-blocking. `[DOC]` `[NUM]`
2.3.13 `[TRAP]` Exit 2 overrides a JSON `permissionDecision: "allow"` — it blocks regardless.
       `[TRAP]` `[DOC]`
2.3.14 The JSON output contract: `hookSpecificOutput.{hookEventName, permissionDecision,
       permissionDecisionReason, decision, additionalContext, continue, updatedInput, retry,
       systemMessage}` plus top-level `terminalSequence`. `[DOC]`
### §2.3 Hooks

2.3.15 Which decision field each event honours — the table. `PreToolUse` takes
       `permissionDecision`; `Stop` takes `continue`; `PostToolUse` takes none because it already
       ran. `[DOC]`
2.3.16 Hook decisions **do not bypass permission rules**: a matching deny still blocks and a
       matching ask still prompts, whatever the hook returned. `[DOC]` `[TRAP]`
2.3.17 Path placeholders and env vars: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
       `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_CODE_REMOTE`, `CLAUDE_EFFORT`,
       `CLAUDE_PLUGIN_OPTION_*`. `[DOC]`
### §2.3 Hooks

2.3.18 Where hooks may be configured: user/project/local settings, managed policy, plugin
       `hooks/hooks.json`, **skill frontmatter** (rest of session), **subagent frontmatter**
       (while it runs). Six sources. `[DOC]`
2.3.19 `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and
       that individual hooks cannot be disabled — only deleted. `[DOC]`
2.3.20 `/hooks` as the read-only browser: events, counts, matcher groups, handler details and
       source file. The debug log records which hooks matched and how they exited. `[DOC]`
       `[BUILD]`
### §2.3 Hooks

2.3.21 `[CASE]` The harness's `hooks.json`: three `SessionStart` handlers plus one `PostToolUse`
       with `matcher: "Write|Edit"`, each invoking `bash "${CLAUDE_PLUGIN_ROOT}/hooks/…"`. Quote
       it whole; it is 30 lines and complete. `[CASE]`
2.3.22 `[CASE]` `check-init.sh` as a masterclass in advisory hooks. Every finding is a tagged
       instruction to the model: `[HANDBOOK_ACTIVE]`, `[HANDBOOK_SELECT]`,
       `[HARNESS_BOOTSTRAP_REQUIRED]`, `[HARNESS_UPDATE_AVAILABLE]`,
       `[PLUGIN_DEPENDENCY_UNRESOLVED]`, `[CLI_TOOLS_MISSING]`, `[LSP_SERVERS_SUGGESTED]`.
       Context injection driven by ground truth on the machine, not by model belief. `[CASE]`
2.3.23 `[CASE]` Its defensive shape: `set +e` at the top and `exit 0` at the bottom — an advisory
       hook must never break the session; timeouts and `GIT_HTTP_LOW_SPEED_*` on the network
       call; a `sha256sum`-vs-`shasum` fallback; `LC_ALL=C` so glob collation cannot vary by
       machine. `[CASE]`
2.3.24 `[CASE]` A **content hash instead of a version constant**: the bootstrap nudge hashes
       `SKILL.md` + every `bootstrap-*.sh` and compares against `.claude/.bootstrap-version`, so
       nothing needs bumping when a step is edited — and the writer and the checker must hash the
       identical file set in the identical order or every run nudges spuriously. `[CASE]`
### §2.3 Hooks

2.3.25 `[INCIDENT]` The removed auto-reindex. This `SessionStart` hook used to pull two handbook
       clones and delta-reindex a RAG store on every session start with **no cross-session
       coordination**. Observed: every concurrent session independently decided a reindex was due,
       hundreds of concurrent embedder processes, **100+ GB** of abandoned partial indexes,
       machines unusable, and no recovery — *because starting a session was the trigger for the
       next pile-up.* State the general law: anything expensive or stateful in a `SessionStart`
       hook needs a lock or must not be there. `[INCIDENT]` `[CASE]` `[NUM]`
2.3.26 `[CASE]` `prod-guard-bash.sh` / `prod-guard-lib.sh` / `prod-guard-session-start.sh` as the
       blocking-guard pattern: a `PreToolUse` non-zero exit is the only guard the model cannot
       talk its way past. `[CASE]`
2.3.27 `[BUILD]` Write three hooks and prove each: a `PostToolUse` formatter on `Edit|Write`; a
       `PreToolUse` deny on a destructive command with a JSON `permissionDecision`; a
       `SessionStart` that injects the current branch and open-PR count. `[BUILD]` `[PROVE]`
2.3.28 `[TRAP]` A hook that reads state the model can change, or that assumes a single session, or
       that writes to a shared path without a lock. Three symptoms and three fixes. `[TRAP]`



### §2.4 MCP — connecting external systems

2.4.1 What MCP (Model Context Protocol) is, from zero: a standard way for a separate process to
      expose tools, resources and prompts to an agent. Why a standard beats N bespoke integrations.
      `[ZERO]`
2.4.2 Transport shapes: stdio (local subprocess), HTTP/SSE (remote). What each implies for
      auth and failure. `[DOC]`
2.4.3 Where servers are registered and the scopes: user, project `.mcp.json`, local, plugin
      `.mcp.json`. `claude mcp add/list/remove`, `claude mcp login/logout`. `[DOC]`
2.4.4 Project-server approval and workspace trust; `enableAllProjectMcpServers`,
      `enabledMcpjsonServers`, `disabledMcpjsonServers`. `[DOC]`
2.4.5 `[TRAP]` `enabledMcpjsonServers` gates only servers declared in a project `.mcp.json` — it
      says nothing about user-scope registrations. Reading it to answer "which server is active"
      gives the wrong answer. This is a documented real mistake in the harness's own hook.
      `[TRAP]` `[CASE]`
### §2.4 MCP — connecting external systems

2.4.6 Tool naming: `mcp__<server>__<tool>`; how it appears in permission rules, hook matchers and
      the tool list. `[DOC]`
2.4.7 The cost of a connected server: every tool's schema is context. A chatty server is a
      permanent tax on every turn. Measure it with `/context`. `[NUM]` `[PROVE]`
2.4.8 Failure modes, including the one in this very session: a configured server that fails to
      connect is a *connection* failure, not a missing capability, and the correct action is to
      report it, not to conclude the feature does not exist. `[TRAP]`
2.4.9 Governance keys: `allowedMcpServers`, `deniedMcpServers`, `allowManagedMcpServersOnly`,
      `disableClaudeAiConnectors`, `allowAllClaudeAiMcps`, `--strict-mcp-config`. `[DOC]`
2.4.10 `--mcp-config` for per-run servers; `requiresUserInteraction` on a tool; elicitation and
       the `Elicitation`/`ElicitationResult` hooks. `[DOC]`
### §2.4 MCP — connecting external systems

2.4.11 **LSP as the cheaper cousin**: `.lsp.json`, a language server, and precise symbol lookups
       instead of reading and grepping whole files. The argument is token cost, not correctness.
       `[DOC]`
2.4.12 `[CASE]` The harness enables three official LSP plugins (`pyright-lsp`, `typescript-lsp`,
       `jdtls-lsp`) and its `check-init.sh` nudges every session when the binaries are missing —
       explicitly framed as "cutting token usage on code-heavy tasks. Optional." `[CASE]`
2.4.13 `[BUILD]` Register one MCP server, measure `/context` before and after, then write a deny
       rule that blocks its write tools. `[BUILD]` `[PROVE]`



### §2.5 Plugins and marketplaces

2.5.1 What a plugin is: a self-contained directory of skills, agents, hooks, MCP/LSP configs,
      monitors, `bin/` and default settings, installable and versioned. `[ZERO]` `[DOC]`
2.5.2 Standalone `.claude/` vs plugin — the real trade: iteration speed vs distribution,
      versioning and namespacing. Start standalone, convert when you share. `[DOC]`
2.5.3 The directory layout, every component: `.claude-plugin/plugin.json`, `skills/`, `commands/`,
      `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`,
      `settings.json`. `[DOC]`
2.5.4 `[TRAP]` **Only `plugin.json` goes inside `.claude-plugin/`.** Putting `skills/` or `agents/`
      in there silently ships nothing. And the plugin root is the plugin's own directory — never
      `~/.claude/`. `[TRAP]` `[DOC]`
### §2.5 Plugins and marketplaces

2.5.5 `plugin.json` fields: `name` (also the skill namespace), `description`, `version`, `author`,
      `homepage`, `repository`, `license`, `dependencies`, `settings`. `[DOC]`
2.5.6 Version management: users receive updates only when `version` is bumped (command sources
      excepted); what happens when it is omitted. `[DOC]`
2.5.7 Namespacing: plugin skills are always `/<plugin>:<skill>`; plugin agents are
      `@agent-<plugin>:<name>`; project and user `agents/` **override** a same-named plugin agent,
      while plugin skills coexist rather than override. `[DOC]` `[TRAP]`
2.5.8 A plugin's `settings.json` supports only `agent` and `subagentStatusLine` today — enough for
      a plugin to change the default persona of the whole session. `[DOC]`
### §2.5 Plugins and marketplaces

2.5.9 Marketplaces: `.claude-plugin/marketplace.json` with `$schema`, `name`, `description`,
      `owner`, `plugins[]`, and `allowCrossMarketplaceDependenciesOn`. `[DOC]`
2.5.10 Cross-marketplace dependencies: Claude Code **refuses to auto-add a marketplace the user
       has not explicitly trusted**, so onboarding must instruct adding both. `[DOC]`
2.5.11 `[TRAP]` An unresolved plugin dependency is nearly silent — a cryptic `/reload-plugins`
       error. `claude plugin list --json` exposes a per-plugin `errors` array; check it. `[TRAP]`
       `[DOC]`
2.5.12 The commands: `/plugin`, `/plugin marketplace add`, `/plugin install`, `/reload-plugins`,
       `claude plugin init|validate|list`, `--plugin-dir` (directory or `.zip`), `--plugin-url`.
       `[DOC]`
### §2.5 Plugins and marketplaces

2.5.13 Skills-directory plugins via `claude plugin init` — a plugin that auto-loads from
       `~/.claude/skills/` with no marketplace. `[DOC]` `[VERSION]`
2.5.14 Governance: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`,
       `strictKnownMarketplaces`, `strictPluginOnlyCustomization` (and its `.agents`, `.hooks`,
       `.mcp`, `.skills` sub-keys), `disableSideloadFlags`, `pluginTrustMessage`. `[DOC]`
2.5.15 `strictPluginOnlyCustomization` as the enterprise endgame: block skills, agents, hooks and
       MCP from user and project sources so **only reviewed, versioned plugins can extend the
       agent.** Why an org reaches for it. `[DOC]`
### §2.5 Plugins and marketplaces

2.5.16 `[CASE]` The harness's `marketplace.json`: `allowCrossMarketplaceDependenciesOn:
       ["ig-superclaude"]` and a description that explains *why* the pivot to a standalone
       marketplace happened, citing its own RFC. Documentation living in the config. `[CASE]`
2.5.17 `[CASE]` Its `plugin.json`: `version: 0.10.2`, proprietary licence,
       `dependencies: [{ name: "ig-superclaude", marketplace: "ig-superclaude" }]`. `[CASE]`
2.5.18 `[TRAP]` `${CLAUDE_PLUGIN_ROOT}` is the plugin's **install/cache** directory, not the repo.
       A hook ported from `<repo>/.claude/hooks/` cannot keep resolving the repo root as
       `dirname "$0"/../..`. Path assumptions are the number-one porting bug. `[TRAP]` `[CASE]`
2.5.19 `[CASE]` The harness's fix and its discipline: resolve `HARNESS_ROOT` → `git rev-parse
       --show-toplevel`, and **refuse with a clear message** rather than inventing a third
       fallback. Quote the header comment that says exactly that. `[CASE]`
2.5.20 `[BUILD]` Convert a `.claude/` folder into a plugin: manifest, move the components, migrate
       settings hooks into `hooks/hooks.json`, test with `--plugin-dir`, `claude plugin validate`,
       then delete the originals so the plugin copies actually take effect. `[BUILD]`



### §2.6 Context economy in practice

2.6.1 Read a real `/context` line by line and attribute every token: system prompt, tool schemas,
      memory files, skill listing, MCP schemas, conversation, free space. `[PROVE]` `[BUILD]`
2.6.2 The startup tax, itemised with numbers for the reader's own machine. `[NUM]` `[PROVE]`
2.6.3 The four biggest avoidable costs, ranked: unbounded command output, whole-file reads where a
      symbol lookup would do, a bloated always-on `CLAUDE.md`, and chatty MCP servers. `[NUM]`
2.6.4 Bounding tool output as a discipline: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over
      `cat`, `git diff --stat` before `git diff`. `[BUILD]`
### §2.6 Context economy in practice

2.6.5 **Autocompaction**: `autoCompactEnabled`, `autoCompactWindow`, `--autocompact`,
      `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. What compaction actually is — a summary replacing the
      transcript. `[DOC]`
2.6.6 What survives compaction, exhaustively: project-root `CLAUDE.md` re-read from disk;
      most-recent skill invocations within the 5,000/25,000-token budget; nothing else that lived
      only in conversation. `[DOC]` `[NUM]`
2.6.7 `PreCompact` / `PostCompact` hooks as the seam to persist state across a compaction. `[DOC]`
2.6.8 `/compact` vs `/clear` vs a fresh session vs `--fork-session`: four different reset
      semantics. `[NUM]`
### §2.6 Context economy in practice

2.6.9 The prompt-cache economics of session shape: append-only conversations stay cached; anything
      that changes the prefix does not. Why a 5-minute idle gap has a price. `[NUM]` `[PROVE]`
2.6.10 Isolation as the primary lever, restated with arithmetic: burn 150K in a subagent, return
       200 words. Compare against doing the same work inline. `[PROVE]` `[NUM]`
2.6.11 A working session protocol for this reader: `/context` at start, compact at a task
       boundary, `/clear` per feature, subagent for anything verbose, one file per lane. `[BUILD]`
2.6.12 `[TRAP]` Compacting mid-task instead of at a boundary. The summary keeps the narrative and
       drops the specifics you were about to use. `[TRAP]`



### §2.7 Working with the tool: the practices that change outcomes

2.7.1 Plan mode as a first-class step: read-only exploration, a reviewable plan, then execute.
      `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode`, `plansDirectory`. `[DOC]`
2.7.2 Why a plan improves a large change more than a better prompt does: it moves the expensive
      correction from *after* the diff to *before* it. `[PROVE]`
2.7.3 Test-first with an agent: a failing test is a machine-checkable specification, which is
      exactly what a confabulating writer needs. `[JAVA]`
2.7.4 Small diffs and reviewability: why the same argument that makes small PRs better makes small
      agent tasks better. `[X-REF 17]`
### §2.7 Working with the tool: the practices that change outcomes

2.7.5 Prompting that matters and prompting that does not: state the goal, the constraints, the
      done-condition, and where the answer goes. Skip politeness, role-play and threats. `[TRAP]`
2.7.6 Give the agent the same context a new teammate would need: the file, the convention, the
      command to verify. Under-specifying is the top cause of a plausible-but-wrong result.
2.7.7 The verification habit: never accept a claim of success without an artefact — a test run, a
      compile, a transcript, a diff.
2.7.8 `/code-review`, `/security-review` and self-review as a second pass with a fresh context;
      why a reviewer that shares the writer's context shares its blind spots. `[DOC]`
### §2.7 Working with the tool: the practices that change outcomes

2.7.9 Where an agent is a bad fit: a one-line change you already understand, anything needing
      taste you cannot express, and anything whose verification costs more than the work.
2.7.10 `[JAVA]` A worked Java example end to end: add an idempotency key to a Spring Boot endpoint
       — plan, failing test, implementation, review, and the two places the agent got it wrong and
       how the test caught it. `[JAVA]` `[PROVE]`
2.7.11 `statusLine` / `subagentStatusLine`: cheap situational awareness — model, branch, cost,
       context used. `[DOC]` `[BUILD]`
2.7.12 Keybindings and `~/.claude/keybindings.json` in one paragraph. `[DOC]`



### §2.8 Deterministic vs agentic — the central engineering judgment

2.8.1 The rule, stated once and referenced forever: **if the inputs determine one correct answer,
      write a script; if the task needs judgment, write a prompt.** `[CASE]`
2.8.2 `[CASE]` The source of that rule in the harness's `bootstrap` skill, quoted verbatim:
      "resolving paths, merging JSON, and creating symlinks all have a single correct answer given
      the inputs — there is no ambiguity for a model to resolve." `[CASE]`
2.8.3 `[CASE]` The consequence in the same file: the skill is "an **orchestrator, not a rewrite**",
      every step delegates to a tested `bootstrap-*.sh`, and the assistant is explicitly forbidden
      from re-deriving the logic inline on each run. `[CASE]`
2.8.4 The decision table: one-correct-answer → script; judgment/synthesis → prompt; must-happen →
      hook; verbose-in/small-out → subagent; needs human authority → confirmation gate with the
      tool denied. `[NUM]`
2.8.5 Why "the model could do it" is not an argument for letting it: cost, variance, and the fact
      that a script is testable and a prompt is not. `[PROVE]`
### §2.8 Deterministic vs agentic — the central engineering judgment

2.8.6 Idempotence as the property that makes a bootstrap safe to re-run, and why every step in the
      harness's is written that way. `[CASE]`
2.8.7 `[CASE]` The one documented exception and its reasoning: `bootstrap-uv.sh` self-installs a
      package manager because without `uv` no playbook can pass its first stage, so "a bootstrap
      that leaves the engineer to separately find and run a curl-to-shell command isn't actually a
      single-command setup". An exception stated with its justification is not an inconsistency.
      `[CASE]`
2.8.8 Human-authority gates: the calibrator mines and groups, and a human confirms and files.
      Deny the tool; do not instruct the agent to abstain. `[CASE]`
2.8.9 `[TRAP]` Prompting for determinism. Symptoms: a step that works four times in five, and a
      failure mode nobody can reproduce. `[TRAP]`



### §2.9 Governance, security and the org view

2.9.1 The threat model in plain terms: the agent runs with your credentials, reads what you can
      read, and follows text it finds. Enumerate what that permits. `[ZERO]` `[X-REF 13]`
2.9.2 **Prompt injection**: instructions embedded in a file, a web page, an issue comment or a
      tool result. Why "just tell it to ignore instructions in data" is not a control. `[TRAP]`
      `[X-REF 13]`
2.9.3 The controls that actually hold: deny rules, `PreToolUse` blocking hooks, sandboxing,
      least-privilege tool sets, and human confirmation on outward-facing actions. `[NUM]`
2.9.4 Secrets: `Read` deny rules for `.env` and `secrets/**`, sandbox credential masking
      (`sandbox.credentials.{envVars,files,sigv4,awsPairs}`), and why an agent transcript is a
      data-exfiltration surface. `[DOC]`
### §2.9 Governance, security and the org view

2.9.5 What leaves the machine, and the settings that govern it: `cleanupPeriodDays`,
      `skipWebFetchPreflight`, telemetry/OTel keys, `env`. `[DOC]`
2.9.6 Managed settings delivery: `managed-settings.json`, MDM, server-managed settings from the
      console; `managedSourcesBehavior`, `policyHelper` (`path`, `refreshIntervalMs`, `timeoutMs`),
      `forceRemoteSettingsRefresh`. `[DOC]`
2.9.7 The `allowManaged*Only` family as the "developers cannot re-open this" lock:
      `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`,
      `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`.
      `[DOC]`
2.9.8 Login and version control at org scale: `forceLoginMethod`, `forceLoginOrgUUID`,
      `availableModels`, `enforceAvailableModels`, `requiredMinimumVersion`,
      `requiredMaximumVersion`, `autoUpdatesChannel`. `[DOC]`
### §2.9 Governance, security and the org view

2.9.9 Attribution and audit: `attribution.{commit,pr,sessionUrl}`, `includeGitInstructions`,
      `prUrlTemplate`. Why "which commits came from an agent" is a question you will be asked.
      `[DOC]`
2.9.10 `[CASE]` The harness's own posture, assembled from its files: a fail-closed prod-AWS
       deny-list provisioned at user scope by `bootstrap-user-scope.sh`, `prod-guard-*` hooks,
       read-only triage scripts (`triage-aws-ro.sh`), and a Jira tool withheld from the agent that
       would otherwise use it. `[CASE]`
2.9.11 The rollout argument a Staff engineer has to make: capability as a **versioned,
       dependency-managed plugin with hooks and eval suites**, not tips in a wiki. What that buys
       — review, rollback, measurement — and what it costs. `[CASE]`







