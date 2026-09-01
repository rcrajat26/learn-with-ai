### §0.1 What the thing on the other side actually is

0.1.1 A **large language model** is one function: text in, text out. It has no memory between
      calls, no filesystem, no network, no clock. Say this before anything else. `[ZERO]`
0.1.2 What "predicts the next token" means, stated without ML vocabulary: given the text so far,
      the model produces a probability distribution over what comes next, and one option is
      sampled. `[ZERO]`
0.1.3 A **token** is a chunk of text, roughly 3–4 characters of English or ~0.75 words; code
      tokenises worse than prose because of punctuation and identifiers. `[ZERO]` `[NUM]`
0.1.4 Count tokens for three concrete strings — an English sentence, a Java method, a minified JSON
      blob — and show the ratio differs. `[PROVE]` `[NUM]`
0.1.5 Why token counts matter at all: they are the unit of both **cost** and **the limit**. `[ZERO]`
0.1.6 **Determinism:** the same input does not reliably give the same output. Temperature and
      sampling in one paragraph, no maths. Contrast with a pure Java method. `[ZERO]` `[JAVA]`
0.1.7 What the model *cannot* do, exhaustively: it cannot read a file, run a command, remember
      yesterday, or check whether what it said is true. Everything it appears to do, something
      else did. `[ZERO]` `[TRAP]`
0.1.8 **Confabulation** ("hallucination"): why a wrong answer is produced with the same fluency as
      a right one, and why fluency is therefore worthless as a correctness signal. `[ZERO]` `[TRAP]`
0.1.9 **Training cutoff:** the model's knowledge has a date; anything after it must be supplied in
      the input. Why this alone motivates the whole rest of the guide. `[ZERO]`
0.1.10 Model naming as of 2026: the Claude 5 family (`claude-opus-5`, `claude-sonnet-5`,
       `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`); aliases `opus`/`sonnet`/
       `haiku`/`fable`; what a `[1m]` suffix means. `[DOC]` `[RESEARCH]` `[VERSION]`
0.1.11 Capability tiers as an engineering decision, not a brand: which tier for exploration, which
       for writing code, which for architecture judgment. Cost ratio stated. `[NUM]`
0.1.12 The word **agent**, defined precisely: a model plus a loop plus tools. Not a synonym for
       "chatbot", not a synonym for "AI". `[ZERO]`



### §0.2 The context window, taught as a data structure

0.2.1 The **context window** is the maximum number of tokens one request may contain — input plus
      output together. It is a hard limit, not a soft one. `[ZERO]` `[NUM]`
0.2.2 Current sizes: 200K standard, 1M in the extended-context tier. What "1M context" costs
      relative to 200K. `[NUM]` `[RESEARCH]` `[VERSION]`
0.2.3 A request is an ordered **list of messages**, each with a role: `system`, `user`,
      `assistant`. Show the literal JSON of a two-turn conversation. `[ZERO]` `[DOC]`
0.2.4 The window is **not** a memory the model writes to. It is the argument list of the next
      call. Say it in those words. `[ZERO]` `[TRAP]`
0.2.5 `[JAVA]` The honest analogy: a stateless `@RestController` method that receives the entire
      conversation as its request body every time, and a client that keeps appending to that body.
      State where the analogy breaks (no session, no cookie, no server-side store). `[JAVA]`
0.2.6 Therefore: cost and latency scale with **conversation length**, not with the length of your
      last message. Work the arithmetic for a 10-turn vs 100-turn session. `[PROVE]` `[NUM]`
0.2.7 What happens at the limit: the request is rejected, or the harness compacts. Both, named.
      `[ZERO]`
0.2.8 **Prompt caching** in one paragraph: the unchanged prefix of a request can be reused at a
      fraction of the price, which is why appending is cheap and *editing the beginning* is not.
      `[NUM]` `[RESEARCH]`
0.2.9 The default cache time-to-live is 5 minutes; `promptCacheTtl` and `subagentPromptCacheTtl`
      change it. Why a 6-minute pause costs real money. `[NUM]` `[DOC]`
0.2.10 The **budget framing** the whole guide rests on: 200K window, autocompaction threshold, and
       what is left for actual work. State the arithmetic. `[NUM]` `[PROVE]`
0.2.11 The five things that consume the window before you type anything: system prompt, tool
       schemas, memory files, skill listing, environment/git snapshot. Forward-reference §3.1.
0.2.12 "It forgot" is almost never a bug: it means *never in context* or *compacted out*. The two
       are distinguished differently and fixed differently. `[TRAP]`



### §0.3 The agent loop

0.3.1 The loop in three steps, written out: assemble request → model emits text or a tool call →
      harness executes the tool, appends the result, repeat. `[ZERO]`
0.3.2 A **tool** is a function the harness exposes to the model as a name, a description, and a
      JSON input schema. Show one real schema. `[ZERO]` `[DOC]`
0.3.3 The model does not *call* the tool. It emits a `tool_use` block naming the tool and the
      arguments; the harness decides whether to run it. This distinction is the entire basis of
      the permission system. `[ZERO]` `[TRAP]`
0.3.4 A `tool_result` message goes back into the transcript. So tool output is context, and a
      verbose tool is a context leak. `[ZERO]`
0.3.5 A **turn**: one model response plus any tools it triggers. Why `--max-turns` bounds agency
      and a wall-clock timeout bounds time, and why you need both. `[NUM]`
0.3.6 The model chooses tools **from their descriptions alone**. A vague description produces a
      misused tool. `[TRAP]`
0.3.7 Walk a complete real loop end to end: "rename this method" → Grep → Read → Edit → done, with
      the transcript growing at each step and the token count stated after each. `[PROVE]` `[NUM]`
0.3.8 The built-in tools, by category: file (Read, Write, Edit, Glob, Grep), shell (Bash),
      web (WebFetch, WebSearch), delegation (Agent, SendMessage), meta (Skill, ToolSearch),
      task/UI (TodoWrite, AskUserQuestion). `[DOC]` `[RESEARCH]`
0.3.9 Deferred tools and `ToolSearch`: why the full schema of every tool is not loaded up front,
      and what that buys. `[DOC]` `[VERSION]`
0.3.10 **Extended thinking**: the model can emit reasoning tokens before answering; they cost
       tokens and are configurable. `alwaysThinkingEnabled`, `showThinkingSummaries`, the
       `effort` levels `low|medium|high|xhigh|max`. `[DOC]` `[NUM]`
0.3.11 Where "Claude Code" sits: it is *the harness*. The CLI, the VS Code/JetBrains extensions,
       the desktop app and the web app are different front ends over the same loop and the same
       settings files. `[ZERO]` `[DOC]`
0.3.12 The Agent SDK / API as the same loop with the harness written by you. One-paragraph
       orientation; full treatment in §3.8. `[X-REF 21]`



### §0.4 Getting oriented in the tool itself

0.4.1 Install and authenticate; `claude`, `claude auth login`, `claude auth status`. `[BUILD]`
0.4.2 The three ways in: interactive (`claude`), one-shot (`claude -p "…"`), continue
      (`claude -c`, `claude -r <session>`). `[DOC]`
0.4.3 The diagnostic commands that answer "why is it doing that", and the order to try them:
      `/context`, `/doctor`, `/permissions`, `/hooks`, `/memory`, `/config`, `claude --debug`.
      `[DOC]` `[BUILD]`
0.4.4 `/context` in detail — read a real one and account for every row. This is the single most
      important habit in the guide. `[PROVE]` `[BUILD]`
0.4.5 `/compact` and `/clear` — what each throws away, and when to use which. `[DOC]`
0.4.6 `/rewind` and file checkpointing (`fileCheckpointingEnabled`) — the undo you did not know
      you had. `[DOC]` `[VERSION]`
0.4.7 `!` prefix to run a shell command in-session and put its output in context; `@` to reference
      a file; `#` to save to memory. `[DOC]`
0.4.8 Session persistence: where transcripts live (`~/.claude/projects/<project>/`), how long
      (`cleanupPeriodDays`), and that they are plain JSONL you can read. `[DOC]` `[NUM]`
0.4.9 `--safe-mode` and `--bare`: start with all customisation disabled, to answer "is it my
      config or the tool?". `[DOC]` `[VERSION]`
0.4.10 The first-session checklist for this reader specifically: run `/context`, run `/doctor`,
       read your own `~/.claude/CLAUDE.md`, count its lines. `[BUILD]`








### §1.1 The `.claude` folder, mapped

1.1.1 `.claude/` is configuration-as-code: a conventional directory the tool discovers, not a
      registry or a database. Everything in it is a file you can diff and commit. `[ZERO]`
1.1.2 The full inventory, one line each: `settings.json`, `settings.local.json`, `CLAUDE.md`,
      `rules/`, `commands/`, `skills/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`,
      `agent-memory/`. `[DOC]`
1.1.3 The user twin at `~/.claude/`: same shapes, machine-wide scope; plus `projects/`,
      `plugins/`, `keybindings.json`, and the tool-owned `~/.claude.json`. `[DOC]`
1.1.4 `~/.claude.json` is written by the tool for the tool — sign-in, MCP registrations, per-project
      trust decisions, `/config` global keys. Do not hand-edit it. `[DOC]` `[TRAP]`
1.1.5 `CLAUDE_CONFIG_DIR` relocates the whole user tree; on Windows `~/.claude` means
      `%USERPROFILE%\.claude`. `[DOC]`
1.1.6 The discovery walk: the tool reads from the session's **primary working directory** and
      every directory above it. Which artefacts walk upward, which load from subdirectories on
      demand, and which do neither. `[DOC]` `[PROVE]`
1.1.7 `[CASE]` The real harness `.claude/`: nine command files, one skill with a `references/`
      subfolder, and a `settings.json` of exactly two keys. Quote it. `[CASE]`
1.1.8 What is *not* in `.claude/` and why: the plugin cache, the transcripts, the auto-memory
      directory. Each lives outside the repo deliberately. `[DOC]`
1.1.9 The single most useful invariant to hold: **if a behaviour surprised you, some file caused
      it, and `/context` plus `/doctor` will name the file.** `[TRAP]`



### §1.2 Settings files, scope, and precedence

1.2.1 The four settings files and who each reaches: `~/.claude/settings.json` (user),
      `.claude/settings.json` (shared project, committed), `.claude/settings.local.json`
      (project local, gitignored), managed settings. `[DOC]`
1.2.2 The precedence order, highest first: **managed → command line (`--settings`) → project local
      → shared project → user.** A key set higher wins. `[DOC]` `[NUM]`
1.2.3 `[TRAP]` The order is *not* "more specific wins" and it is *not* "command line always wins":
      managed settings beat the command line. `[TRAP]` `[DOC]`
1.2.4 Installing Claude Code creates no settings file. Which files the tool creates for you, and
      when: user file on the first `/config` change it stores there, local file on the first
      "yes, and don't ask again". `[DOC]`
1.2.5 Where the local file lands in a git repo — repository root, not the directory you started
      in — and the exceptions (outside a repo, repo root is `$HOME`, Windows, foreign ownership).
      `[DOC]` `[VERSION]`
1.2.6 Worktrees: the local file comes from the main checkout's root. `[DOC]`
1.2.7 Committing `.claude/settings.json`: what your teammates get, and why permissions and hooks
      in it belong in code review. `[DOC]`
1.2.8 Which keys never take effect from a repository file, and which wait for workspace trust.
      Forward-reference §1.5.10. `[DOC]`
### §1.2 Settings files, scope, and precedence

1.2.9 The key groups, named so the reader knows where to look: permissions, hooks, plugins/skills,
      context/memory, model/responses, MCP, sandbox, attribution, auth, data/privacy, interface,
      agents/sessions/worktrees, updates, enterprise, global config. `[DOC]`
1.2.10 The dozen keys this reader will actually touch first, with values:
       `permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`,
       `autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`,
       `statusLine`, `cleanupPeriodDays`. `[DOC]` `[BUILD]`
1.2.11 `env` — settings-supplied environment variables for every session; how they compose across
       scopes, and that they apply to hooks and Bash too. `[DOC]`
1.2.12 `[CASE]` The harness's real `settings.json`: `permissions.allow` of four entries plus
       `enabledPlugins` of four plugins (three official LSP plugins and its own). Quote it and
       explain each entry. `[CASE]`
1.2.13 Verifying a setting actually applied: `/config`, `/permissions`, `claude doctor`'s resolved
       settings, and the invalid-settings dialog. `[BUILD]`
1.2.14 `[TRAP]` A silently-ignored key. Unknown keys, `mcp__` rules with parentheses in a settings
       file, and path rules on tools that never consult them are all accepted and then ignored —
       with a startup warning most people never read. `[TRAP]` `[DOC]`
1.2.15 Managed settings as an org control surface, in one paragraph: what it is for, the
       `allowManaged*Only` locks, and why a developer cannot override it. Full treatment §2.9.
1.2.16 `--setting-sources user,project,local` — choosing which layers load *at all*. Set up the
       incident in §3.7 now; do not resolve it here. `[DOC]`



### §1.3 `CLAUDE.md` and the memory system

1.3.1 Two mechanisms, clearly separated: `CLAUDE.md` files (you write, instructions) and **auto
      memory** (Claude writes, learnings). Both load every session. `[DOC]`
1.3.2 Both are **context, not enforced configuration.** Claude reads them and tries; a hook is the
      only guarantee. Repeat this sentence in the guide; it is the most-missed fact here. `[DOC]`
      `[TRAP]`
1.3.3 The four `CLAUDE.md` locations in load order: managed policy path (per-OS), `~/.claude/
      CLAUDE.md`, `./CLAUDE.md` or `./.claude/CLAUDE.md`, `./CLAUDE.local.md`. `[DOC]`
1.3.4 The managed policy paths, exactly: macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`,
      Linux/WSL `/etc/claude-code/CLAUDE.md`, Windows `C:\Program Files\ClaudeCode\CLAUDE.md`.
      `[DOC]`
1.3.5 How they load: **concatenated, not overriding** — root-down ordering, so the file nearest
      your working directory is read last, and `CLAUDE.local.md` after `CLAUDE.md` at each level.
      `[DOC]` `[PROVE]`
1.3.6 Subdirectory `CLAUDE.md` files load **on demand**, when Claude reads a file in that
      directory — not at launch. `[DOC]`
1.3.7 `@path` imports: relative to the importing file, recursive to a **maximum depth of four
      hops**, skipped inside code spans and fences. `[DOC]` `[NUM]`
1.3.8 `[TRAP]` An import does not save context — the imported file loads at launch too. Splitting
      a large `CLAUDE.md` into imports buys organisation only. `[TRAP]` `[DOC]`
1.3.9 External imports (paths resolving outside the working directory) trigger a one-time approval
      dialog for project files; user-scope files are trusted. Why the dialog exists. `[DOC]`
1.3.10 Size guidance: **target under 200 lines**; a file over 4 MiB is skipped entirely; longer
       files measurably reduce adherence. `[DOC]` `[NUM]`
1.3.11 `[PROVE]` Measure the cost of your own `CLAUDE.md`: token count × turns in a session =
       tokens spent on it. Do the arithmetic for the reader's actual global file. `[PROVE]` `[NUM]`
1.3.12 Writing instructions that get followed: specific over vague, verifiable over aspirational,
       structured over prose, consistent over contradictory. Three before/after pairs. `[DOC]`
1.3.13 Block-level HTML comments are stripped before injection — free maintainer notes. `[DOC]`
### §1.3 `CLAUDE.md` and the memory system

1.3.14 `.claude/rules/` — modular instruction files, discovered recursively, same priority as
       `.claude/CLAUDE.md` when they have no `paths` frontmatter. `[DOC]`
1.3.15 **Path-specific rules**: `paths:` frontmatter globs, loaded only when Claude touches a
       matching file. The one mechanism that makes a large instruction set affordable. `[DOC]`
1.3.16 `paths` glob mechanics: brace expansion, the shared budget of **1,000 expanded patterns /
       4 MiB**, what happens on overflow, and the `[`-bracket-expression pitfall. `[DOC]` `[NUM]`
       `[VERSION]`
1.3.17 User-level rules in `~/.claude/rules/` load before project rules, giving project rules
       higher priority. Symlinks are supported and cycles are handled. `[DOC]`
1.3.18 `AGENTS.md`: Claude Code does not read it. The `@AGENTS.md` import and the symlink, and why
       the import is preferable on Windows. `[DOC]`
1.3.19 `claudeMdExcludes` for monorepos — glob against absolute paths, merges across layers,
       cannot exclude managed policy. `[DOC]`
1.3.20 `claudeMd` in managed settings: org instructions inline in JSON, honoured only at managed
       scope. `[DOC]`
### §1.3 `CLAUDE.md` and the memory system

1.3.21 **Auto memory**: the four types Claude records (`user`, `feedback`, `project`, `reference`),
       what it deliberately skips, and that it does not save every session. `[DOC]`
1.3.22 Auto-memory storage: `~/.claude/projects/<project>/memory/` with a `MEMORY.md` index plus
       one topic file per memory; keyed on the git repo so worktrees share it; machine-local.
       `[DOC]`
1.3.23 Only the **first 200 lines or 25 KB of `MEMORY.md`** loads at session start; topic files are
       read on demand. What happens when the index exceeds the limit. `[DOC]` `[NUM]`
1.3.24 `autoMemoryEnabled`, `autoMemoryDirectory`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and the
       `/memory` toggle. The `modified` frontmatter timestamp. `[DOC]` `[VERSION]`
1.3.25 Auto memory does **not** load into subagents (a fork excepted); a subagent's own `memory`
       field is a separate directory. `[DOC]`
1.3.26 What survives `/compact`: project-root `CLAUDE.md` is re-read from disk and re-injected;
       nested files and path-scoped rules reload only when re-matched; conversation-only
       instructions are gone. `[DOC]` `[TRAP]`
1.3.27 `/memory`, `/context`, `/init`, `/import`, and the `InstructionsLoaded` hook as the four
       ways to find out what actually loaded. `[DOC]`
1.3.28 `[TRAP]` "Claude ignored my CLAUDE.md." The diagnostic ladder: did it load (`/context`), is
       it specific enough, does another file contradict it, and should it have been a hook.
       `[TRAP]` `[DOC]`
1.3.29 `[CASE]` Read the reader's own two-level setup — the 125-line global `~/.claude/CLAUDE.md`
       and the project `.claude/CLAUDE.md` — and account for what each costs and whether each
       entry belongs there or in a skill. `[CASE]` `[BUILD]`



### §1.4 The permission system

1.4.1 The one-sentence foundation: **permission rules are enforced by Claude Code, not by the
      model.** Prompt and `CLAUDE.md` shape what Claude *tries*; rules decide what runs. `[DOC]`
      `[ZERO]`
1.4.2 The three rule lists — `allow`, `ask`, `deny` — and the evaluation order: **deny, then ask,
      then allow; first match wins; specificity does not reorder.** `[DOC]` `[NUM]`
1.4.3 `[TRAP]` A broad deny cannot carry allowlist exceptions: `Bash(aws *)` in deny blocks
      `Bash(aws s3 ls)` in allow. Same for ask over allow. `[TRAP]` `[DOC]`
1.4.4 Deny of a **bare tool name** removes the tool from Claude's context entirely; a **scoped**
      deny leaves the tool visible and blocks matching calls. Two different mechanisms. `[DOC]`
1.4.5 Rule syntax: `Tool` or `Tool(specifier)`. `Bash(*)` ≡ `Bash`. `[DOC]`
1.4.6 Bash specifiers: the rule matches the **whole command text** with `*` standing for any text.
      Put the `*` after the subcommand; the startup warning when you do not. `[DOC]` `[TRAP]`
1.4.7 The wildcard matching table, reproduced and explained: `Bash(npm run build)` vs
      `Bash(npm run *)` vs `Bash(git log * main)` vs `Bash(git * main)` vs `Bash(* --version)` vs
      `Bash(ls *)` vs `Bash(ls*)`. `[DOC]` `[PROVE]`
1.4.8 `[TRAP]` `Bash(git * main)` allows `git -c core.fsmonitor=<script> diff main` — the `*`
      spans options, including options that make git execute a program you name. `[TRAP]` `[DOC]`
1.4.9 **Compound commands**: the recognised separators (`&&`, `||`, `;`, `|`, `|&`, `&`, newline),
      and that each subcommand must match independently. `[DOC]` `[NUM]`
1.4.10 "Yes, and don't ask again" on a compound command saves a **separate rule per subcommand**,
       up to 5. `[DOC]` `[NUM]`
### §1.4 The permission system

1.4.11 **Wrapper stripping**: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`,
       `noglob`, and bare `xargs` are stripped before matching. `command -v` and `nocorrect` are
       not. Known-safe leading env assignments are stripped for allow rules; deny rules match
       past any assignment. `[DOC]` `[NUM]`
1.4.12 `[TRAP]` Environment runners are **not** stripped: `Bash(devbox run *)` matches
       `devbox run rm -rf .`. Same class: `npx`, `docker exec`, `direnv exec`, `mise exec`.
       Write runner+inner rules instead. `[TRAP]` `[DOC]`
1.4.13 Exec wrappers that a prefix rule cannot auto-approve: `watch`, `setsid`, `ionice`, `flock`,
       and `find` with `-exec`/`-delete`. `[DOC]`
1.4.14 The built-in **read-only command set** that never prompts in any mode (`ls`, `cat`, `echo`,
       `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only
       `git`), that it is not configurable, and the glob/redirect cases that still prompt. `[DOC]`
1.4.15 Redirections add a check on the target path. `[DOC]`
### §1.4 The permission system

1.4.16 `Read`/`Edit` rules use **gitignore pattern syntax**; the four anchor forms (`//abs`, `~/`,
       `/`, bare); `Read(./.env)`, `Read(./secrets/**)`. `[DOC]`
1.4.17 A `Read` deny also blocks Edit and Write on the same path — but not `NotebookEdit`, so add
       an `Edit` deny too. `[DOC]` `[VERSION]`
1.4.18 `[TRAP]` File permissions are checked against `Edit(path)` and `Read(path)` **only**. A
       `Write(docs/**)`, `NotebookEdit(...)`, `MultiEdit(...)` or `Glob(...)` path rule is accepted
       and never consulted. Use `Edit(...)`/`Read(...)`. `[TRAP]` `[DOC]` `[VERSION]`
1.4.19 `[TRAP]` Read/Edit deny rules cover the built-in file tools and file commands Claude Code
       recognises in Bash (`cat`, `head`, `tail`, `sed`) — **not** an arbitrary subprocess. A
       Python script that opens the file itself is not stopped. Sandbox is the OS-level answer.
       `[TRAP]` `[DOC]`
1.4.20 `WebFetch(domain:example.com)`; allow-or-deny-every-fetch forms. `[DOC]`
1.4.21 MCP rules: `mcp__server`, `mcp__server__*`, `mcp__server__tool`. Parenthesised `mcp__` rules
       in a settings file are skipped; use `--disallowedTools` for parameter matching. `[DOC]`
1.4.22 `Agent(Name)` rules — gate which subagents may run, including the built-ins
       `Agent(Explore)`, `Agent(Plan)`, `Agent(fork)`. `[DOC]`
1.4.23 Parameter matching for deny/ask on any built-in tool: `Tool(param:value)`, e.g.
       `Agent(model:opus)`, `Agent(isolation:worktree)`, `Bash(run_in_background:true)`. One
       parameter per rule; direct fields only; `*` wildcard; compared before normalisation. `[DOC]`
1.4.24 `Cd` rules — not model-invocable; bare deny disables `/cd`; any allow rule switches to
       allowlist mode; `*` is one segment and `**` spans segments. `[DOC]`
### §1.4 The permission system

1.4.25 The six permission modes and exactly what each auto-approves: `default`/`manual`,
       `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. `[DOC]` `[NUM]`
1.4.26 `acceptEdits` in detail — file edits **plus** common filesystem commands (`mkdir`, `touch`,
       `mv`, `cp`) for paths in the working directory or `additionalDirectories`. What it does
       *not* cover is the point of the §3.7 incident. `[DOC]`
1.4.27 `auto` mode: a background classifier reviews actions instead of you; `autoMode` rules,
       `autoMode.classifyAllShell`, `disableAutoMode`. `[DOC]` `[VERSION]`
1.4.28 `bypassPermissions`: what it still refuses (protected paths such as `.git` and `.claude`,
       cross-session messaging safeguards), and that it is defensible only in a container or VM.
       `[DOC]` `[TRAP]`
1.4.29 `permissions.defaultMode`, `disableBypassPermissionsMode`, `disableAutoMode` — and why these
       belong in managed settings. `[DOC]`
### §1.4 The permission system

1.4.30 **Working directories**: the primary working directory, `--add-dir`, `/add-dir`,
       `permissions.additionalDirectories`. Additional directories grant **file access, not
       configuration**. `[DOC]` `[TRAP]`
1.4.31 `/cd` moves the primary working directory and re-applies the new directory's project
       settings, hooks, MCP servers, plugins, skills, subagents and `env`. `[DOC]` `[VERSION]`
1.4.32 **Workspace trust**: `permissions.allow` and `additionalDirectories` from a project's
       committed settings apply only after you accept the trust dialog; `deny`/`ask` are not
       gated because they only restrict. `[DOC]`
1.4.33 How trust is keyed: on the git repo root inside a repo (excluding nested repos), on the
       start directory outside one, session-only in `$HOME`. `[DOC]`
1.4.34 `[TRAP]` **A `-p` or SDK session never shows the trust dialog and counts as accepted.**
       Automation therefore runs a repository's allow rules without a human ever reviewing them.
       `[TRAP]` `[DOC]`
### §1.4 The permission system

1.4.35 `.claude/settings.local.json` and trust: your own untracked file applies immediately; a
       *tracked* local file, or a symlinked `.claude`, is treated as repository-supplied and waits.
       `[DOC]`
1.4.36 Precedence for permissions: **a deny at any level cannot be overridden by any other level**,
       including `--allowedTools` and managed settings. `[DOC]`
1.4.37 `/permissions` — read the rules and the file each came from; edits apply from Claude's next
       tool call in the same turn. `[DOC]` `[VERSION]` `[BUILD]`
1.4.38 `--allowedTools` / `--disallowedTools` / `--tools` as per-run overrides. `[DOC]`
### §1.4 The permission system

1.4.39 Sandboxing as the layer below permissions: `sandbox.enabled`, filesystem allow/deny,
       network allowlist, credential masking. One paragraph each on why an OS-level boundary
       catches what a rule cannot. `[DOC]` `[RESEARCH]`
1.4.40 `[BUILD]` Write a permission block for a real repository: allow the build and test commands,
       deny `git push`, deny reads of `.env` and `secrets/**`, deny `rm -rf`. Then prove each rule
       fires. `[BUILD]` `[PROVE]`
1.4.41 `[CASE]` The harness's `permissions.allow` — `Read(**)`, `Edit(**)`, `Bash(*)`,
       `mcp__atlassian-cloud__*` — and the destructive-command deny-list it is paired with. Why
       `Bash(*)` plus a deny-list is a considered choice and not laziness. `[CASE]`



### §1.5 Skills and slash commands

1.5.1 The merge, stated first because every older article gets it wrong: **custom commands are
      skills.** `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create
      `/deploy` and behave the same way. `[DOC]` `[VERSION]` `[TRAP]`
1.5.2 What a skill *is*: a markdown file of instructions that the tool injects into the
      conversation when invoked. Not code, not a tool, not a plugin. `[ZERO]`
1.5.3 The four locations and the conflict order: enterprise → personal (`~/.claude/skills/`) →
      project (`.claude/skills/`); a skill at any level overrides a bundled skill of the same name
      but not its aliases; plugin skills are namespaced `plugin:skill` and cannot conflict; a
      skill beats a same-named `commands/` file. `[DOC]`
1.5.4 Nested `.claude/skills/` below the working directory become available when Claude reads a
      file in that subtree — the monorepo mechanism. `[DOC]`
1.5.5 **Progressive disclosure**, the central idea: only the frontmatter `description` (plus
      `when_to_use`) is in context up front; the body loads when the skill fires. This is why 50
      skills cost almost nothing and 50 skills' worth of `CLAUDE.md` costs everything. `[DOC]`
      `[NUM]`
### §1.5 Skills and slash commands

1.5.6 The listing budget: combined `description` + `when_to_use` is truncated at **1,536
      characters**; `skillListingBudgetFraction` and `skillListingMaxDescChars` tune the listing.
      `[DOC]` `[NUM]`
1.5.7 Frontmatter, every field: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
      `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`,
      `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`,
      `compatibility`. `[DOC]`
1.5.8 `[TRAP]` `allowed-tools` **pre-approves, it does not restrict.** It grants permission for
      the invoking turn only and clears on your next message; every other tool stays callable.
      `disallowed-tools` is the field that removes tools. `[TRAP]` `[DOC]`
1.5.9 Frontmatter is read only when the opening `---` is the file's first line; otherwise the whole
      file is content. Boolean fields accept `yes/no/on/off/1/0`. `[DOC]` `[VERSION]` `[TRAP]`
1.5.10 Who invokes: `disable-model-invocation: true` for human-only workflows,
       `user-invocable: false` for model-only background knowledge, `paths:` to gate automatic
       activation by file glob. `[DOC]`
### §1.5 Skills and slash commands

1.5.11 String substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, named `$name` via the `arguments`
       field, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`. `[DOC]`
1.5.12 **Dynamic context injection**: `` !`command` `` runs a shell command *before* the content
       is sent, and its output replaces the placeholder. The fenced ` ```! ` block form for
       multi-line. `[DOC]`
1.5.13 Injection mechanics that bite: substitution runs **once** over the original file and output
       is not re-scanned; the inline form is recognised only at line start or after whitespace, so
       `` KEY=!`cmd` `` stays literal. `[DOC]` `[TRAP]`
1.5.14 `disableSkillShellExecution` turns injection off for user/project/plugin/additional-directory
       skills. Why an org might set it. `[DOC]`
### §1.5 Skills and slash commands

1.5.15 **Skill content lifecycle**: the rendered content enters as one message and *stays* across
       later turns; the file is not re-read; a re-invocation with identical content adds a note,
       not a second copy. Write standing instructions, not one-time steps. `[DOC]`
1.5.16 Skills through compaction: the most recent invocation of each skill is re-attached after the
       summary, **first 5,000 tokens each, 25,000 tokens combined**, filled newest-first — so old
       skills can vanish. `[DOC]` `[NUM]`
1.5.17 `context: fork` + `agent:` + `background:` — run the skill in a forked subagent instead of
       inline. When that is the right shape. `[DOC]` `[VERSION]`
1.5.18 Supporting files: a skill is a *directory*, so `references/`, scripts and data live beside
       `SKILL.md` and are read on demand via `${CLAUDE_SKILL_DIR}`. `[DOC]`
### §1.5 Skills and slash commands

1.5.19 `[CASE]` The harness's `playwright-cli` skill with its `references/` subfolder — a reference
       library that costs nothing until needed. `[CASE]`
1.5.20 `[CASE]` The harness's `bootstrap` skill: `name` / `description` / `when_to_use` /
       `allowed-tools: [Bash, Read, AskUserQuestion]`, and a body that is an **orchestrator, not a
       rewrite** — each step delegates to a tested `bootstrap-*.sh`. Quote the "why deterministic
       scripts and not model judgment" paragraph verbatim. `[CASE]`
1.5.21 `[CASE]` Prompt composition without duplication: `/implement-story` inlines
       `/run-conductor` with a ` ```! ` block running
       `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, then states only its binding
       overrides, forwarded flags and **rejected flags**. DRY applied to prompts. `[CASE]`
1.5.22 `[TRAP]` A description that names the **topic** rather than the **trigger** makes the skill
       invisible or always-on. Three bad descriptions rewritten. `[TRAP]`
### §1.5 Skills and slash commands

1.5.23 Built-in and bundled: `/help`, `/compact`, `/clear`, `/context`, `/config`, `/doctor`,
       `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/rewind`, `/cd`,
       `/add-dir`, `/model`, `/effort`, plus bundled skills such as `/code-review`, `/security-review`,
       `/loop`, `/run`. `[DOC]` `[RESEARCH]`
1.5.24 `skillOverrides`, `disableBundledSkills`, `syncClaudeAiSkills`, `--disable-slash-commands`
       — the visibility and kill switches. `[DOC]`
1.5.25 `[BUILD]` Write a real skill for this repository: one that regenerates a topic guide's
       atomic-concept checklist. Frontmatter, `$ARGUMENTS`, one `` !`command` `` injection, a
       `references/` file. Then invoke it and read `/context` before and after. `[BUILD]` `[PROVE]`
1.5.26 The decision table the reader needs: fact that always applies → `CLAUDE.md`; fact that
       applies to one file type → path-scoped rule; procedure → skill; must-happen → hook;
       verbose-in/small-out → subagent; distribution → plugin. `[NUM]`







