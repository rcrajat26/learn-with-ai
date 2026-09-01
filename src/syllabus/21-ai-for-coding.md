# Syllabus — 21 AI for Coding (Claude Code)

**Reader baseline: ZERO.** This reader has never formally studied LLMs, agents, prompting, or
Claude Code. They are a competent backend Java engineer (3–4 YOE) who has *used* an AI coding tool
the way one uses a search engine — by typing into it — and has never been told what happens on the
other side. Everything in PART 0 must therefore be taught from nothing: no ML background, no
"as you know", no undefined jargon. Every term is defined at first use, in the body, before it is
relied on.

The consequence for the write pass: **PART 0 is not an introduction, it is a prerequisite course.**
A reader who finishes PART 0 must be able to explain, unprompted, what a token is, why the whole
conversation is re-sent every turn, and why the model cannot do anything except emit text. If the
write pass produces a PART 0 that assumes any of that, the rest of the guide is unreadable and the
part must be rewritten, not patched.

**Tool version baseline: Claude Code v2.1.2xx (August 2026).** Every flag, settings key, hook event
and frontmatter field below was verified against `https://code.claude.com/docs/en/` on 2026-08-29.
This subject moves faster than the JDK: a field added in v2.1.218 and a field removed in v2.1.234
both exist in the same release line. Any leaf whose behaviour is gated on a version carries
`[VERSION]` and **must state the version inline** in the finished guide, because a reader on an
older build will otherwise conclude the guide is wrong.

**The worked example project.** Every `[CASE]` leaf is grounded in a real production system the
reader has access to: the **sdlc-harness** at
`~/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness` — a Python engine that orchestrates
`claude -p` subprocesses across the software development lifecycle, shipped as a versioned plugin
with hooks, agents, skills, playbooks and eval suites. A `[CASE]` leaf must cite a **file path**,
and must quote the real text, not paraphrase it. Invented examples are forbidden in `[CASE]` leaves;
`Foo`/`Bar`/`my-agent` are forbidden everywhere.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[ZERO]` | assume no prior knowledge whatsoever; define every term used in the leaf, in the leaf |
| `[DOC]` | must quote the official documentation (short excerpt) and cite the page |
| `[CASE]` | must be grounded in the sdlc-harness repo, with a real file path and a real quote |
| `[BUILD]` | must ship a complete, working artefact the reader can copy and run |
| `[PROVE]` | must work the argument through or show the observed result, not assert it |
| `[TRAP]` | must carry a `**Trap:**` marker — the wrong belief, the symptom, the fix |
| `[INCIDENT]` | a real recorded failure; must name what broke, what it cost, and the fix |
| `[NUM]` | must state the number, limit, or arithmetic explicitly |
| `[VERSION]` | behaviour is version-gated; must state the version inline |
| `[RESEARCH]` | re-verify against the cited source immediately before writing; this area drifts |
| `[X-REF nn]` | one-paragraph treatment here, full treatment in guide nn |
| `[JAVA]` | must land in the reader's own language — Java/Spring analogy or Java code |

---

# PART 0 — GROUND ZERO

*Nothing in this part assumes the reader has heard any of these words before. Every leaf is `[ZERO]`
by default; the tag is repeated only where the write pass is most likely to forget.*

## §0.1 What the thing on the other side actually is

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

*(12 leaves)*

## §0.2 The context window, taught as a data structure

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

*(12 leaves)*

## §0.3 The agent loop

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

*(12 leaves)*

## §0.4 Getting oriented in the tool itself

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

*(10 leaves)*

---

**PART 0 total: 46 leaves**

*Gate before PART 1 — the write pass must be able to answer yes to all five:* can the reader
define a token, a context window, a tool call, a turn, and an agent, without looking back?

---

# PART 1 — BASICS

## §1.1 The `.claude` folder, mapped

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

*(9 leaves)*

## §1.2 Settings files, scope, and precedence

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

*(16 leaves)*

## §1.3 `CLAUDE.md` and the memory system

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

*(29 leaves)*

## §1.4 The permission system

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
1.4.25 The six permission modes and exactly what each auto-approves: `default`/`manual`,
       `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. `[DOC]` `[NUM]`
1.4.26 `acceptEdits` in detail — file edits **plus** an auto-approved filesystem-command set that
       is wider than most people expect: `mkdir`, `touch`, **`rm`, `rmdir`**, `mv`, `cp`, **`sed`**,
       for paths in the working directory or `additionalDirectories`. `[DOC]` `[NUM]`
1.4.26a `[TRAP]` That set includes deletion. "Accept edits" reads like a promise about *edits*, and
       it auto-approves `rm` and `rmdir` inside the working directory. State the blast radius
       plainly. `[TRAP]` `[DOC]`
1.4.26b What `acceptEdits` does *not* cover — `mvn`, `git commit`, `chmod`, `java` — is the symptom
       in the §3.7 incident. `[DOC]`
1.4.27 `auto` mode: a background classifier reviews actions instead of you; `autoMode` rules,
       `autoMode.classifyAllShell`, `disableAutoMode`. The defaults must be stated, not just the
       mechanism: the classifier runs on **Sonnet 5**, with **3-consecutive / 20-total** block
       fallback thresholds. `[DOC]` `[VERSION]` `[NUM]`
1.4.28 `bypassPermissions`: what it still refuses, enumerated exactly — critical-path `rm`/`rmdir`
       deletions, explicit `ask`-rule matches, always-interactive tools (`AskUserQuestion`,
       `requiresUserInteraction` MCP tools), and two cross-session messaging safeguards
       (`isolatePeerMachines`, held inbound messages). Defensible only in a container or VM.
       `[DOC]` `[NUM]`
1.4.28a `[TRAP]` It does **not** protect `.git` and `.claude`. Protected-path writes are allowed
       under `bypassPermissions`, so the mode can rewrite the very configuration that would
       otherwise constrain it. The widely-repeated "it still refuses protected paths" claim is
       false and this syllabus asserted it until 2026-08-30. `[TRAP]` `[DOC]` `[INCIDENT]`
1.4.29 `permissions.defaultMode`, `disableBypassPermissionsMode`, `disableAutoMode` — and why these
       belong in managed settings. `[DOC]`
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
1.4.34 A `-p` or SDK session shows no trust dialog, because it is non-interactive. The consequence
       is the **opposite** of dangerous-by-default: for an untrusted folder such a session does
       **not** apply the committed `allow` / `additionalDirectories` rules at all, and prints a
       stderr warning instead. "Counts as accepted" applies only to the much narrower git
       tracked/untracked check on `settings.local.json` (§1.4.35). `[DOC]` `[TRAP]`
1.4.34a `[TRAP]` The real risk, once 1.4.34 is stated correctly, is **stickiness**: trust is keyed
       per repository-root path and is **never re-checked when a commit changes the ruleset**. You
       reviewed the rules once; a later commit can widen `permissions.allow` and no dialog reappears.
       That is the thing to say in an interview, not the false version this syllabus carried until
       2026-08-30. `[TRAP]` `[DOC]` `[INCIDENT]`
1.4.35 `.claude/settings.local.json` and trust: your own untracked file applies immediately; a
       *tracked* local file, or a symlinked `.claude`, is treated as repository-supplied and waits.
       `[DOC]`
1.4.36 Precedence for permissions: **a deny at any level cannot be overridden by any other level**,
       including `--allowedTools` and managed settings. `[DOC]`
1.4.37 `/permissions` — read the rules and the file each came from; edits apply from Claude's next
       tool call in the same turn. `[DOC]` `[VERSION]` `[BUILD]`
1.4.38 `--allowedTools` / `--disallowedTools` / `--tools` as per-run overrides. `[DOC]`
1.4.39 Sandboxing as the layer below permissions: `sandbox.enabled`, filesystem allow/deny,
       network allowlist, credential masking. One paragraph each on why an OS-level boundary
       catches what a rule cannot. `[DOC]` `[RESEARCH]`
1.4.40 `[BUILD]` Write a permission block for a real repository: allow the build and test commands,
       deny `git push`, deny reads of `.env` and `secrets/**`, deny `rm -rf`. Then prove each rule
       fires. `[BUILD]` `[PROVE]`
1.4.41 `[CASE]` The harness's `permissions.allow` — `Read(**)`, `Edit(**)`, `Bash(*)`,
       `mcp__atlassian-cloud__*` — and the destructive-command deny-list it is paired with. Why
       `Bash(*)` plus a deny-list is a considered choice and not laziness. `[CASE]`

*(45 leaves)*

## §1.5 Skills and slash commands

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
1.5.6 The listing budget is **two different numbers** and conflating them is an error this
      syllabus shipped: `skillListingMaxDescChars` is the **per-entry** cap, default **1,536
      characters** on combined `description` + `when_to_use`; `skillListingBudgetFraction` is a
      separate **pool** budget across all entries, roughly **1% of the context window**. A skill
      can be inside the per-entry cap and still be dropped from the listing by the pool budget.
      `[DOC]` `[NUM]` `[TRAP]`
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
1.5.19 `[CASE]` The `playwright-cli` skill and its `references/` subfolder — a reference library
       that costs nothing until needed. Two corrections to the form this leaf originally took: it
       is a **repo-root** skill at `.claude/skills/playwright-cli/`, **not** a plugin skill, and
       there are **nine** reference files on disk, not ten. List the filenames as found; never pad
       a count to match prose. `[CASE]` `[NUM]`
1.5.20 `[CASE]` The harness's `bootstrap` skill: `name` / `description` / `when_to_use` /
       `allowed-tools: [Bash, Read, AskUserQuestion]`, and a body that is an **orchestrator, not a
       rewrite** — each step delegates to a tested `bootstrap-*.sh`. Quote the "why deterministic
       scripts and not model judgment" paragraph verbatim. The scripts live under
       `plugins/sdlc-harness/scripts/` (**not** `hooks/`) and there are **fifteen** of them, plus
       three `triage-*.sh`. Count them at write time rather than trusting this number. `[CASE]`
       `[NUM]`
1.5.21 `[CASE]` Prompt composition without duplication: `/implement-story` inlines
       `/run-conductor` with a ` ```! ` block running
       `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, then states only its binding
       overrides, forwarded flags and **rejected flags**. DRY applied to prompts. `[CASE]`
1.5.22 `[TRAP]` A description that names the **topic** rather than the **trigger** makes the skill
       invisible or always-on. Three bad descriptions rewritten. `[TRAP]`
1.5.23 Built-in commands **versus** bundled skills — a real distinction, and the inventory must be
       tagged rather than lumped. Built-ins include `/help`, `/compact`, `/clear`, `/context`,
       `/config`, `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/cd`,
       `/add-dir`, `/model`, `/effort`, **`/run`**. Bundled **skills** (tagged `[Skill]`) include
       **`/doctor`**, **`/rewind`**, `/code-review`, `/security-review`, `/loop`. Note that
       `/doctor` and `/rewind` are skills and `/run` is a built-in — the reverse of what this
       syllabus originally implied. Re-check the tags at write time; this list drifts.
       `[DOC]` `[RESEARCH]` `[TRAP]`
1.5.24 `skillOverrides`, `disableBundledSkills`, `syncClaudeAiSkills`, `--disable-slash-commands`
       — the visibility and kill switches. `[DOC]`
1.5.25 `[BUILD]` Write a real skill for this repository: one that regenerates a topic guide's
       atomic-concept checklist. Frontmatter, `$ARGUMENTS`, one `` !`command` `` injection, a
       `references/` file. Then invoke it and read `/context` before and after. `[BUILD]` `[PROVE]`
1.5.26 The decision table the reader needs: fact that always applies → `CLAUDE.md`; fact that
       applies to one file type → path-scoped rule; procedure → skill; must-happen → hook;
       verbose-in/small-out → subagent; distribution → plugin. `[NUM]`

*(26 leaves)*

---

**PART 1 total: 125 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 Subagents

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
2.1.16 Persistent agent memory: `memory: user|project|local` and the three directories it maps to.
       `[DOC]`
2.1.17 Resuming a subagent via `SendMessage` with its ID or name; where subagent transcripts live
       (`~/.claude/projects/{project}/{sessionId}/subagents/`). `[DOC]` `[VERSION]`
2.1.18 Invocation, three levels: natural language (Claude decides), `@"name (agent)"` mention
       (guaranteed), `claude --agent <name>` or the `agent` setting (whole session). `[DOC]`
2.1.19 The cost model: a subagent costs roughly **2×** the tokens of inline work because context
       must be re-supplied; a team of agents 3–4×. State when that is worth it. `[NUM]` `[PROVE]`
2.1.20 The three cases where it pays: verbose input with a small answer; genuinely parallel work
       with non-overlapping writes; a different capability set (read-only auditor, no-network
       reviewer). `[NUM]`
2.1.21 The output protocol that makes delegation actually save context: **agents write findings to
       files and return status + a few findings + a path.** Message bodies are not a data channel.
2.1.22 `[CASE]` `progress-verifier.md` — 20 lines, and four transferable design properties: body as
       a pointer to a versioned prompt file; a machine-parseable output contract
       (`## Progress Verdict: progressing|stalled`); explicit read boundaries; artifacts-only
       evidence discipline with an explicit ban on inspecting the coder's live session. `[CASE]`
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

*(25 leaves)*

## §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.1 `--agent <name>` loads a **registered** agent — its full system prompt, model and tool
      allowlist. The parity mechanism for programmatically spawning a subagent. `[DOC]`
2.2.2 `--append-system-prompt <text>` **appends to the default** system prompt. The default persona
      is still there; you decorated it. `[DOC]` `[TRAP]`
2.2.3 `--system-prompt` / `--system-prompt-file` **replace** the whole thing. What you lose.
      `[DOC]`
2.2.4 `--append-subagent-system-prompt` for every subagent; `--exclude-dynamic-system-prompt-sections`
      to move per-machine sections out of the cached prefix. `[DOC]` `[VERSION]`
2.2.5 `[CASE]` `engine/agent.py` documents the distinction explicitly and calls `--agent` "the
      parity mechanism for an auto-spawned subagent, not `--append-system-prompt` (which only
      appends to the default prompt)". Quote it. `[CASE]`
2.2.6 `[CASE]` `load_agent_prompt()` strips the `--- … ---` frontmatter before appending, because
      YAML metadata leaking into a system prompt is noise the model tries to interpret. The regex
      and why it is anchored. `[CASE]` `[SOURCE-EQUIV]`
2.2.7 `[TRAP]` Choosing `--append-system-prompt` when you meant `--agent`: the symptom is an agent
      that behaves *almost* right and ignores its tool restrictions, because it never had any.
      `[TRAP]`

*(7 leaves)*

## §2.3 Hooks

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
2.3.14 The JSON output contract has **three** kinds of field, and conflating them is the error
       this syllabus itself originally shipped: **universal** top-level fields every event accepts
       (`continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`);
       **top-level `decision` + `reason`**, used by most events to block; and
       **`hookSpecificOutput`**, a nested object for events needing richer control, requiring a
       `hookEventName` field. `[DOC]` `[VERSION]`
2.3.14a The universal kill switch: top-level `continue: false` makes Claude **stop processing
       entirely** after the hook runs, and **takes precedence over any event-specific decision
       field**. `stopReason` is the message shown to the **user** (never to Claude) when it fires.
       Default is `true`. `suppressOutput` is accepted and does nothing. `[DOC]` `[NUM]`
2.3.14b Output strings — `additionalContext`, `systemMessage`, plain stdout — are capped at
       **10,000 characters**; longer output is written to a file and replaced with a preview plus
       path. `[DOC]` `[NUM]`
2.3.15 Which field each event honours — the table. `PreToolUse` uses
       `hookSpecificOutput.permissionDecision` + `permissionDecisionReason` (its top-level
       `decision`/`reason` form is **deprecated**, with `"approve"`/`"block"` mapping to
       `"allow"`/`"deny"`). `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`,
       `ConfigChange`, `PreCompact` and others use **top-level `decision`/`reason`**.
       `PermissionRequest` uses a `decision` **object**. `[DOC]` `[TRAP]`
2.3.15a `[TRAP]` **`Stop` semantics are inverted from every reader's first guess.** To keep Claude
       working you return `decision: "block"` — you are blocking the *stop*, not requesting a
       continue — and `reason` is **required** when you do. Omitting `decision` allows the stop.
       There is **no** `hookSpecificOutput.continue` field; the boolean `continue` is the universal
       top-level kill switch of 2.3.14a and means the opposite thing. Three independent write
       attempts at this leaf got it wrong three different ways before anyone read the raw page.
       `[TRAP]` `[DOC]` `[INCIDENT]`
2.3.15b `hookSpecificOutput.additionalContext` on `Stop` as the third option: the conversation
       continues under the same loop protections as `decision: "block"`, but the transcript labels
       it `Stop hook feedback` rather than raising a hook error. Use it when the hook is working as
       designed. `[DOC]`
2.3.15c The loop protections that stop a `Stop` hook looping forever: the `stop_hook_active` stdin
       field and an **8-consecutive-continuation cap**. A `Stop` hook without awareness of these is
       an infinite-turn generator. `[DOC]` `[NUM]` `[TRAP]`
2.3.16 Hook decisions **do not bypass permission rules**: a matching deny still blocks and a
       matching ask still prompts, whatever the hook returned. `[DOC]` `[TRAP]`
2.3.17 Path placeholders and env vars: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
       `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_CODE_REMOTE`, `CLAUDE_EFFORT`,
       `CLAUDE_PLUGIN_OPTION_*`. `[DOC]`
2.3.18 Where hooks may be configured: user/project/local settings, managed policy, plugin
       `hooks/hooks.json`, **skill frontmatter** (rest of session), **subagent frontmatter**
       (while it runs). Six sources. `[DOC]`
2.3.19 `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and
       that individual hooks cannot be disabled — only deleted. `[DOC]`
2.3.20 `/hooks` as the read-only browser: events, counts, matcher groups, handler details and
       source file. The debug log records which hooks matched and how they exited. `[DOC]`
       `[BUILD]`
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

*(33 leaves)*

## §2.4 MCP — connecting external systems

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
2.4.11 **LSP as the cheaper cousin**: `.lsp.json`, a language server, and precise symbol lookups
       instead of reading and grepping whole files. The argument is token cost, not correctness.
       `[DOC]`
2.4.12 `[CASE]` The harness enables three official LSP plugins (`pyright-lsp`, `typescript-lsp`,
       `jdtls-lsp`) and its `check-init.sh` nudges every session when the binaries are missing —
       explicitly framed as "cutting token usage on code-heavy tasks. Optional." `[CASE]`
2.4.13 `[BUILD]` Register one MCP server, measure `/context` before and after, then write a deny
       rule that blocks its write tools. `[BUILD]` `[PROVE]`

*(13 leaves)*

## §2.5 Plugins and marketplaces

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
2.5.5 `plugin.json` fields: `name` (also the skill namespace), `description`, `version`, `author`,
      `homepage`, `repository`, `license`, `dependencies`, `settings`. `[DOC]`
2.5.6 Version management: users receive updates only when `version` is bumped (command sources
      excepted); what happens when it is omitted. `[DOC]`
2.5.7 Namespacing: plugin skills are always `/<plugin>:<skill>`; plugin agents are
      `@agent-<plugin>:<name>`; project and user `agents/` **override** a same-named plugin agent,
      while plugin skills coexist rather than override. `[DOC]` `[TRAP]`
2.5.8 A plugin's `settings.json` supports only `agent` and `subagentStatusLine` today — enough for
      a plugin to change the default persona of the whole session. `[DOC]`
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
2.5.13 Skills-directory plugins via `claude plugin init` — a plugin that auto-loads from
       `~/.claude/skills/` with no marketplace. `[DOC]` `[VERSION]`
2.5.14 Governance: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`,
       `strictKnownMarketplaces`, `strictPluginOnlyCustomization` (and its `.agents`, `.hooks`,
       `.mcp`, `.skills` sub-keys), `disableSideloadFlags`, `pluginTrustMessage`. `[DOC]`
2.5.15 `strictPluginOnlyCustomization` as the enterprise endgame: block skills, agents, hooks and
       MCP from user and project sources so **only reviewed, versioned plugins can extend the
       agent.** Why an org reaches for it. `[DOC]`
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

*(20 leaves)*

## §2.6 Context economy in practice

2.6.1 Read a real `/context` line by line and attribute every token: system prompt, tool schemas,
      memory files, skill listing, MCP schemas, conversation, free space. `[PROVE]` `[BUILD]`
2.6.2 The startup tax, itemised with numbers for the reader's own machine. `[NUM]` `[PROVE]`
2.6.3 The four biggest avoidable costs, ranked: unbounded command output, whole-file reads where a
      symbol lookup would do, a bloated always-on `CLAUDE.md`, and chatty MCP servers. `[NUM]`
2.6.4 Bounding tool output as a discipline: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over
      `cat`, `git diff --stat` before `git diff`. `[BUILD]`
2.6.5 **Autocompaction**: `autoCompactEnabled`, `autoCompactWindow`, `--autocompact`,
      `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. What compaction actually is — a summary replacing the
      transcript. `[DOC]`
2.6.6 What survives compaction, exhaustively: project-root `CLAUDE.md` re-read from disk;
      most-recent skill invocations within the 5,000/25,000-token budget; nothing else that lived
      only in conversation. `[DOC]` `[NUM]`
2.6.7 `PreCompact` / `PostCompact` hooks as the seam to persist state across a compaction. `[DOC]`
2.6.8 `/compact` vs `/clear` vs a fresh session vs `--fork-session`: four different reset
      semantics. `[NUM]`
2.6.9 The prompt-cache economics of session shape: append-only conversations stay cached; anything
      that changes the prefix does not. Why a 5-minute idle gap has a price. `[NUM]` `[PROVE]`
2.6.10 Isolation as the primary lever, restated with arithmetic: burn 150K in a subagent, return
       200 words. Compare against doing the same work inline. `[PROVE]` `[NUM]`
2.6.11 A working session protocol for this reader: `/context` at start, compact at a task
       boundary, `/clear` per feature, subagent for anything verbose, one file per lane. `[BUILD]`
2.6.12 `[TRAP]` Compacting mid-task instead of at a boundary. The summary keeps the narrative and
       drops the specifics you were about to use. `[TRAP]`

*(12 leaves)*

## §2.7 Working with the tool: the practices that change outcomes

2.7.1 Plan mode as a first-class step: read-only exploration, a reviewable plan, then execute.
      `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode`, `plansDirectory`. `[DOC]`
2.7.2 Why a plan improves a large change more than a better prompt does: it moves the expensive
      correction from *after* the diff to *before* it. `[PROVE]`
2.7.3 Test-first with an agent: a failing test is a machine-checkable specification, which is
      exactly what a confabulating writer needs. `[JAVA]`
2.7.4 Small diffs and reviewability: why the same argument that makes small PRs better makes small
      agent tasks better. `[X-REF 17]`
2.7.5 Prompting that matters and prompting that does not: state the goal, the constraints, the
      done-condition, and where the answer goes. Skip politeness, role-play and threats. `[TRAP]`
2.7.6 Give the agent the same context a new teammate would need: the file, the convention, the
      command to verify. Under-specifying is the top cause of a plausible-but-wrong result.
2.7.7 The verification habit: never accept a claim of success without an artefact — a test run, a
      compile, a transcript, a diff.
2.7.8 `/code-review`, `/security-review` and self-review as a second pass with a fresh context;
      why a reviewer that shares the writer's context shares its blind spots. `[DOC]`
2.7.9 Where an agent is a bad fit: a one-line change you already understand, anything needing
      taste you cannot express, and anything whose verification costs more than the work.
2.7.10 `[JAVA]` A worked Java example end to end: add an idempotency key to a Spring Boot endpoint
       — plan, failing test, implementation, review, and the two places the agent got it wrong and
       how the test caught it. `[JAVA]` `[PROVE]`
2.7.11 `statusLine` / `subagentStatusLine`: cheap situational awareness — model, branch, cost,
       context used. `[DOC]` `[BUILD]`
2.7.12 Keybindings and `~/.claude/keybindings.json` in one paragraph. `[DOC]`

*(12 leaves)*

## §2.8 Deterministic vs agentic — the central engineering judgment

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

*(9 leaves)*

## §2.9 Governance, security and the org view

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

*(11 leaves)*

---

**PART 2 total: 142 leaves**

---

# PART 3 — UNDER THE HOOD

## §3.1 What is actually in the request

3.1.1 The assembled request, in order: system prompt (built-in + appended), tool schemas, memory
      files as a user message, environment/git snapshot, skill listing, then the conversation.
      `[DOC]` `[PROVE]`
3.1.2 `[TRAP]` `CLAUDE.md` is delivered **as a user message after the system prompt**, not as part
      of the system prompt. That is why it is guidance and not policy, and why
      `--append-system-prompt` behaves differently. `[TRAP]` `[DOC]`
3.1.3 The cached prefix and why the ordering above is not arbitrary: everything stable goes first
      so it can be reused. `--exclude-dynamic-system-prompt-sections` exists to protect this.
      `[NUM]` `[DOC]`
3.1.4 Tool schemas as a cost line: how many tokens the default set is, what an MCP server adds,
      and what deferred tools plus `ToolSearch` save. `[NUM]` `[PROVE]`
3.1.5 The skill listing: `description` + `when_to_use` per skill, capped at 1,536 characters each,
      inside a budget fraction of the window. Compute the cost of 50 skills. `[NUM]` `[PROVE]`
3.1.6 System-reminder blocks: how the harness injects mid-conversation state (file-state notes,
      recalled memories, hook output) and why that text is context rather than instruction.
3.1.7 Reading a real transcript: the JSONL under `~/.claude/projects/<project>/<session>/`, its
      message shapes, and how to count tokens per turn from it. `[BUILD]` `[PROVE]`
3.1.8 `[CASE]` The harness's `telemetry/transcript.py` reads exactly these transcripts to mine
      friction signals. Provenance for the whole calibration loop. `[CASE]`

*(8 leaves)*

## §3.2 Compaction, mechanically

3.2.1 What compaction does: summarise the transcript, then continue with the summary in place of
      the messages. `[DOC]`
3.2.2 The threshold and how it is configured; what "75%" means against which number. `[NUM]`
3.2.3 The re-attachment algorithm for skills: most recent invocation of each, first 5,000 tokens
      each, 25,000 combined, filled newest-first — so invoking many skills silently evicts the
      earliest. `[DOC]` `[NUM]` `[PROVE]`
3.2.4 `CLAUDE.md` re-read from disk after compaction; nested files and path-scoped rules reload
      only on re-match. `[DOC]`
3.2.5 What is irrecoverably lost, and the fix: put it in a file, not in a message. `[TRAP]`
3.2.6 `PreCompact`/`PostCompact` as the persistence seam; a worked handoff-note hook. `[BUILD]`
3.2.7 Why a fresh session usually beats a thrice-compacted one, argued rather than asserted.
      `[PROVE]`

*(7 leaves)*

## §3.3 Permission evaluation, step by step

3.3.1 The full pipeline for one tool call: managed → CLI → local → project → user rule collection,
      then deny → ask → allow, then `PreToolUse` hooks, then the mode's default, then the prompt.
      Draw it. `[DOC]` `[PROVE]`
3.3.2 Where a `PreToolUse` hook sits relative to the rules, and why a hook cannot unblock a deny.
      `[DOC]`
3.3.3 Bash matching in detail: separator splitting, wrapper stripping, env-assignment stripping,
      then per-subcommand matching. Trace three commands through it. `[PROVE]`
3.3.4 The read-only command fast path, and the two cases that leave it (write-capable flags with
      unquoted globs, redirects). `[DOC]`
3.3.5 Read/Edit gitignore-pattern matching, including single-segment directory patterns whose
      depth depends on the rule type. `[DOC]` `[PROVE]`
3.3.6 Which tools consult path rules at all, and the startup warnings for the ones that do not.
      `[DOC]`
3.3.7 Where enforcement ends and the OS begins: a subprocess that opens a file itself, and the
      sandbox as the only answer. `[DOC]` `[TRAP]`
3.3.8 `[PROVE]` Adversarial exercise: given a settings file, decide for ten commands whether each
      runs, prompts or is blocked — then verify each against the real tool. `[PROVE]` `[BUILD]`

*(8 leaves)*

## §3.4 The cost model

3.4.1 What you are billed for: input tokens, output tokens, cache writes, cache reads. Four
      different prices. `[NUM]` `[RESEARCH]`
3.4.2 Per-model pricing and the ratio between tiers, as of the write date. `[NUM]` `[RESEARCH]`
3.4.3 Why conversation length dominates: the same prefix re-sent every turn, times turns. Work a
      full session's arithmetic. `[PROVE]` `[NUM]`
3.4.4 What caching changes, and the 5-minute default TTL as the reason a paused session costs
      more when resumed. `[NUM]`
3.4.5 Where a subagent's ~2× comes from, itemised. `[PROVE]` `[NUM]`
3.4.6 The three ceilings and their different failure shapes: `--max-turns` (agency),
      `--max-budget-usd` (money), subprocess timeout (wall clock). `[NUM]`
3.4.7 Reading cost out of a run: the `-p --output-format json` envelope's cost and token fields;
      `/cost`; `modelPricing` for contracted rates. `[DOC]` `[BUILD]`
3.4.8 `[PROVE]` Measure it: run one task inline and the same task via a subagent, and report both
      envelopes. `[PROVE]` `[BUILD]`
3.4.9 The judgment this all supports: an unbounded agent loop is an unbounded invoice, so ceilings
      are reliability engineering, not thrift. `[CASE]`

*(9 leaves)*

## §3.5 Effort, models and routing

3.5.1 Effort levels `low|medium|high|xhigh|max`: what they change, `/effort`, `effortLevel`,
      `--effort`, `CLAUDE_EFFORT`, `${CLAUDE_EFFORT}`. `[DOC]`
3.5.2 Per-skill and per-agent `effort` and `model` overrides, and their lifetime (the turn, not the
      session). `[DOC]`
3.5.3 Routing as a cost decision, with a table: exploration/search → haiku; implementation →
      sonnet; architecture and gnarly debugging → opus. State the escalation path. `[NUM]`
3.5.4 `fallbackModel`, `--fallback-model`, `switchModelsOnFlag`, `advisorModel`, `modelOverrides`
      for Bedrock/Vertex ARNs, `modelPicker`. `[DOC]`
3.5.5 `fastMode` / `/fast` — faster output on the same Opus model, not a downgrade. `[DOC]`
      `[TRAP]`
3.5.6 `[TRAP]` Routing everything to the cheapest model. Where haiku fails, with a concrete
      example of a wrong result that cost more than the saving. `[TRAP]` `[PROVE]`

*(6 leaves)*

## §3.6 Headless mode — the programmable surface

3.6.1 `claude -p "<task>"` — one prompt in, one envelope out. The whole basis of automation.
      `[DOC]`
3.6.2 `--output-format text|json|stream-json` and `--input-format text|stream-json`. What each is
      for. `[DOC]`
3.6.3 The JSON envelope's fields: result text, `is_error`, `session_id`, cost, token counts,
      duration. Show a real one. `[DOC]` `[PROVE]`
3.6.4 `stream-json` and `--include-partial-messages`, `--include-hook-events`,
      `--forward-subagent-text`, `--replay-user-messages`. When streaming is worth the complexity.
      `[DOC]`
3.6.5 `--json-schema` for schema-validated output — the difference between parsing prose and
      receiving data. `[DOC]` `[VERSION]`
3.6.6 The flag set a production wrapper needs, as a checklist: `--agent`, `--output-format`,
      `--max-turns`, `--permission-mode`, `--setting-sources`, `--settings`, `--model`, `--effort`,
      `--add-dir`, `--append-system-prompt`, `--resume`, `--max-budget-usd`, `--session-id`,
      `--no-session-persistence`, `--allowed-tools`, `--disallowed-tools`, `--mcp-config`,
      `--verbose`. `[DOC]`
3.6.7 Session control in automation: `--session-id` (must be a UUID), `--fork-session`,
      `--continue`, `--resume`, `--no-session-persistence`. `[DOC]`
3.6.8 `claude setup-token` for CI; what an unattended run must *not* have. `[DOC]`
3.6.9 Background and remote execution: `--bg`, `claude attach|logs|stop|respawn|rm`,
      `claude daemon status`, `--cloud`, `--environment`, `--teleport`. One paragraph each.
      `[DOC]`
3.6.10 Failure taxonomy for a wrapper, three classes handled differently: launch/timeout
       (infrastructure), unparseable envelope (contract), `is_error: true` (the agent failed).
       `[CASE]`
3.6.11 `[CASE]` `extract_json_envelope()` preserves a **500-character snippet** of what the
       subprocess actually printed when parsing fails — because a zero-cost envelope failure was
       previously "only diagnosable by reproducing it interactively (2026-07-30 calibration
       finding)". General law: **when you parse a subprocess's output, capture the unparseable
       input.** `[CASE]` `[NUM]` `[INCIDENT]`
3.6.12 `[CASE]` The retry loop keeps the **last parsed error envelope** so cost and token counts
       survive a failure. Why discarding them makes the run unbillable and unauditable. `[CASE]`
3.6.13 `[CASE]` The harness's resolution order for every knob — explicit parameter → environment
       variable → module default — checked with `is not None` so an explicit `0` is not silently
       treated as omitted. Copy this pattern. `[CASE]` `[JAVA]`
3.6.14 `[CASE]` `DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`,
       `DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160`. Each number with its reason. `[CASE]`
       `[NUM]`
3.6.15 `[INCIDENT]` Why `DEFAULT_MAX_TURNS` is 160 and not 40. Raised 40 → 80 → 160; the 2026-08-10
       dogfood run produced **13 green tests and a correct fix but exhausted 80 turns before
       reaching a commit — $5.16 for zero landed work.** A fresh story's first leg is
       disproportionately reads and exploration, not a runaway. The comment records it as "an
       explicit engineer call to trade cost for dev experience, not a measured-data derivation" —
       an honest constant. `[INCIDENT]` `[CASE]` `[NUM]`
3.6.16 `[CASE]` Both ceilings overridable by environment (`HARNESS_AGENT_MAX_TURNS`,
       `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`,
       `HARNESS_AGENT_SETTINGS`) so tuning never requires a code change. `[CASE]`
3.6.17 `[CASE]` `--resume <session_id>` as the continuation mechanism, and the rule that the coder
       resumes its own leg while the verifier **never** does — it judges artifacts. Why mixing the
       two destroys the verdict's reproducibility. `[CASE]`
3.6.18 `[CASE]` `--add-dir` deliberately unused in the code-to-commit loop: agents write only
       inside the worktree and reports ride the envelope. A seam kept open, not used by default.
       `[CASE]`

*(18 leaves)*

## §3.7 The `--setting-sources` incident — a full root-cause walkthrough

3.7.1 The setup: the harness runs each coder in an **isolated per-story git worktree**, so `cwd` is
      the worktree, not the harness repo. `[CASE]` `[INCIDENT]`
3.7.2 The mechanism: `--setting-sources project` resolves `<cwd>/.claude/settings.json`. `[DOC]`
3.7.3 The consequence: the harness's own `permissions.allow` (`Bash(*)`) **and** its
      destructive-command deny-list never loaded. `[CASE]`
3.7.4 The observed symptom, precisely: the agent could read, edit, `mkdir`, `touch`, `mv`, `cp`,
      `sed` — the bare `acceptEdits` defaults — but **not** `mvn`, `git commit`, `chmod` or
      `java`. A competent agent mysteriously unable to build. `[CASE]` `[NUM]`
3.7.5 The fix: `--settings <absolute path>`, which is evaluated independently of `cwd`. `[CASE]`
3.7.6 The paper trail: `docs/adr/0016` and the AP-11470 incident, cited in the code itself.
      Decisions that carry their incident reference are the ones nobody re-litigates. `[CASE]`
3.7.7 Lesson one, generalised: **configuration discovered by directory walk breaks the moment you
      change directories.** Name three other systems where this bites. `[PROVE]`
3.7.8 Lesson two: **a permission model that silently degrades to defaults is worse than one that
      fails loudly.** What a loud failure would have looked like here. `[PROVE]`
3.7.9 Why this is the best interview story in the guide, and how to tell it in 90 seconds:
      symptom → mechanism → fix → generalisation. `[BUILD]`

*(9 leaves)*

## §3.8 The Agent SDK and the API underneath

3.8.1 The three levels of building on Claude: the CLI in `-p` mode, the Agent SDK
      (TypeScript/Python), and the raw Messages API with your own loop. What each gives up. `[DOC]`
3.8.2 The Messages API shape: `model`, `system`, `messages[]`, `tools[]`, `max_tokens`, streaming.
      Enough to read one. `[DOC]` `[RESEARCH]`
3.8.3 Tool use at the API level: `tool_use` and `tool_result` blocks, and writing the loop
      yourself. `[DOC]`
3.8.4 Prompt caching at the API level: cache breakpoints and what they cost. `[DOC]` `[NUM]`
3.8.5 Agent SDK specifics worth knowing: `resolveSettings()`, `managedSettings`,
      `parentSettingsBehavior`, and that an SDK session counts as trusted. `[DOC]`
3.8.6 Why the harness chose subprocesses over the SDK, and what that trade buys (process
      isolation, the same binary engineers use interactively, no SDK version coupling). `[CASE]`
3.8.7 `[JAVA]` The Java view: there is no first-party Java SDK, so the two honest options are the
      HTTP API via a JDK 21 `HttpClient`, or `ProcessBuilder` around the CLI. Sketch both. `[JAVA]`
3.8.8 `[X-REF 12]` Treating an agent call as a remote dependency: timeouts, retries with backoff,
      idempotency, a circuit breaker, and a bulkhead on concurrency. The reader already knows this
      material; the point is that it applies unchanged. `[X-REF 12]` `[JAVA]`

*(8 leaves)*

## §3.9 Orchestration patterns

3.9.1 The vocabulary, defined: single session, subagent, fan-out, pipeline, team, workflow. `[ZERO]`
3.9.2 Fan-out with a join: N independent tasks, one aggregation, and the file-boundary requirement
      that makes it safe. `[NUM]`
3.9.3 Pipeline: stage N's output is stage N+1's input, each stage independently re-runnable
      **because no stage writes to its own input.** `[CASE]`
3.9.4 `[CASE]` This repository's own per-topic pipeline as the worked example:
      `topic-enhancer-agent` → `prompt-builder` → `notes-generator` → `gaps-analyzer-agent` →
      `understanding-book-keeper`, with the rule "never write across lanes" and a hard stop when a
      prerequisite is missing. `[CASE]`
3.9.5 `[CASE]` The harness's playbooks (`full-sdlc`, `plan-project`, `implement-story`,
      `implement-story-lite`, `post-deploy-smoke`) and the split between a **prose executor**
      (`/run-harness`) and a **deterministic conductor** (`/run-conductor`) — two executors, not
      interchangeable, with the routing decision returned by `conductor advance` from folded run
      state rather than inferred by a model. `[CASE]`
3.9.6 `[CASE]` Folded state in `features/<slug>/state/harness.db` as the source of truth for
      "which stage are we at", and why a `--resume-at <stage>` flag was **rejected** rather than
      approximated. Rejecting a flag with a stated reason beats silently ignoring it. `[CASE]`
3.9.7 Judges and rubrics: `progress-verifier` scoring against
      `control-plane/judge-rubrics/progress-verifier.yaml` and emitting one verdict line. Why the
      rubric is a versioned file. `[CASE]`
3.9.8 Continuation checkpoints: what to do when an agent exhausts its turns mid-task, and the
      progressing-vs-stalled decision. `[CASE]`
3.9.9 The calibration loop: mine session transcripts for recurring friction, group it, and file it
      as work with human confirmation. Treating agent failures as a **measurable defect stream**,
      not anecdotes. `severity_map.yaml`, `feedback-signal.yaml`'s `failure_code` vocabulary, the
      `filed-bugs.yaml` dedup ledger. `[CASE]`
3.9.10 Evals: `harness/evals/seeded-defects` and `harness/evals/code-to-commit` — how you find out
       whether a change to a prompt made things better. `claude plugin eval`. `[CASE]` `[DOC]`
3.9.11 `[TRAP]` Over-orchestration. Symptoms: more agents than the task warrants, a pipeline whose
       coordination costs more than its work, and a fan-out where the join is the bottleneck.
       `[TRAP]`
3.9.12 `[NUM]` Concurrency limits that are real, not stylistic: 20 concurrent subagents, depth 3,
       and the practical ceiling imposed by review capacity. `[NUM]`

*(12 leaves)*

## §3.10 Verification — the AI-specific failure mode

3.10.1 The core asymmetry: an agent produces **plausible** artefacts, and skimming a diff is the
       review method worst matched to plausibility. `[ZERO]`
3.10.2 Law: **re-run every published artefact in its published form.** In this repository that
       found more defects than every structural check combined — code that no longer produced the
       transcript printed beneath it, invented values that compiled fine, a repro returning the
       opposite of its claim, and run-specific numbers published as constants. `[INCIDENT]`
       `[PROVE]`
3.10.3 Law: **a checker whose input can switch it off is worse than no checker.** The NUL-byte
       incident — one generated file contained a literal NUL, `file` classified it as `data`, grep
       returned *nothing* (not a mismatch), every text check silently skipped it and reported
       success. Assert text-ness before any grep-based gate. `[INCIDENT]` `[PROVE]`
3.10.4 Law: **certify from final state, never from a pre-write computation.** A footer regex ending
       `\s*$` ate nine files' trailing newlines; an md5 was taken over a patched harness while the
       shipped files still failed to compile. `[INCIDENT]`
3.10.5 Law: **a build proof must pin its harness beside the digest.** Two honest runs over
       identical files produced different md5s purely because one wrapped a throwing snippet. A
       bare digest is unfalsifiable. `[INCIDENT]`
3.10.6 Law: **never let a status row point at a missing path.** The costliest bookkeeping failure
       here, and the one-line gate that prevents it. `[INCIDENT]`
3.10.7 Law: **a closed lane is not a verified lane.** Two cross-lane contradictions were found
       after their owners had stood down; only a pass that reads across boundaries finds these.
       `[INCIDENT]`
3.10.8 Executable evidence over structural evidence: a compile, a test, a transcript beats a regex
       over a file. Rank the evidence types. `[NUM]`
3.10.9 Automating the gates: `PostToolUse` formatters and linters, a `Stop` hook that refuses to
       finish on a red build, and CI as the outer loop. `[BUILD]`
3.10.10 `[TRAP]` Command shapes that defeat a permission matcher and therefore your own gates:
        heredocs, `&&`/`;` chains, `$(...)`. Use one command per call, absolute paths, and the
        Write tool for scratch files. `[TRAP]` `[CASE]`
3.10.11 Review capacity as the real ceiling on agent throughput, argued with numbers. `[PROVE]`
        `[NUM]`

*(11 leaves)*

---

**PART 3 total: 96 leaves**

---

# PART 4 — BUILD IT

Every item is `[BUILD]`: a complete, working artefact the reader creates and then **proves** works,
followed by a **"what this costs"** note stating its token or dollar impact. No fragment, no
"…and so on". Where a real equivalent exists in the sdlc-harness, the item ends with a
**Diff vs the real one** table.

## §4.1 A `.claude` folder from nothing

4.1.1 A `CLAUDE.md` under 100 lines for a real Spring Boot service: build command, test command,
      layout, three conventions, two things Claude gets wrong here. `[BUILD]` `[JAVA]`
4.1.2 Split it: move the always-true facts to `CLAUDE.md`, one procedure to a skill, and one
      file-type convention to a `paths`-scoped rule in `.claude/rules/`. Measure `/context`
      before and after. `[BUILD]` `[PROVE]`
4.1.3 A `settings.json`: permissions for the real build/test commands, deny for `git push`, `.env`
      and `secrets/**`, `env` for one variable, `model` and `effortLevel`. `[BUILD]`
4.1.4 A `settings.local.json` that overrides exactly one key, and proof that it wins. `[BUILD]`
      `[PROVE]`
4.1.5 Commit it, then verify a fresh clone behaves identically — including the workspace-trust
      step. `[BUILD]` `[PROVE]`

*(5 leaves)*

## §4.2 Three hooks

4.2.1 `PostToolUse` on `Edit|Write`: run the formatter on the changed file only, using `jq` over
      stdin to get `tool_input.file_path`. `[BUILD]`
4.2.2 `PreToolUse` on `Bash`: block a destructive command with a JSON `permissionDecision: "deny"`
      and a reason the model can act on; then the exit-2 variant, and a comparison. `[BUILD]`
      `[PROVE]`
4.2.3 `SessionStart`: inject branch, dirty-file count and failing-test count as tagged advisory
      lines. `set +e`, `exit 0`, a timeout on anything network-bound. `[BUILD]`
4.2.4 `Stop`: refuse to end the turn while the build is red, using `decision: "block"` with a
      required `reason` (**not** `continue: true`, which does not exist — see 2.3.15a). Then build
      the `additionalContext` variant and contrast the two transcripts. Then explain why this is
      dangerous if the build takes four minutes, and how `stop_hook_active` plus the
      8-continuation cap bound the damage. `[BUILD]` `[TRAP]` `[NUM]`
4.2.5 Prove all four fired: `/hooks`, the debug log, and an intentional violation each. `[BUILD]`
      `[PROVE]`
4.2.6 Diff vs the real one: `check-init.sh`, `doc-update-reminder.sh`, `prod-guard-bash.sh` —
      concurrency safety, path resolution, tool fallbacks, locale pinning, failure posture.

*(6 leaves)*

## §4.3 A skill and a command

4.3.1 A skill with frontmatter, `$ARGUMENTS`, one `` !`command` `` injection and a `references/`
      file that loads only on demand. `[BUILD]`
4.3.2 The same capability as a bare `.claude/commands/*.md` file; then state what the skill form
      bought. `[BUILD]`
4.3.3 A `disable-model-invocation: true` workflow skill, and a `user-invocable: false` knowledge
      skill. Show that each is invocable only the intended way. `[BUILD]` `[PROVE]`
4.3.4 A `paths`-gated skill that activates only for `**/*.java`. `[BUILD]` `[JAVA]` `[PROVE]`
4.3.5 A composed pair: a thin wrapper skill that inlines a shared executor with a ` ```! ` block
      and states only its overrides. `[BUILD]`
4.3.6 Diff vs the real one: `bootstrap/SKILL.md` and `/implement-story` — plan-then-confirm,
      delegation to tested scripts, rejected-flag handling.

*(6 leaves)*

## §4.4 Two subagents

4.4.1 A read-only reviewer: `tools` allowlist, `model`, a fixed output contract, and a verdict
      line. `[BUILD]`
4.4.2 A test-runner for a Maven project: `Bash(mvn test *)` only, returns failing tests and
      nothing else. Measure the context saved versus running it inline. `[BUILD]` `[JAVA]`
      `[PROVE]`
4.4.3 Give one of them `memory: project` and show what it accumulates across two sessions.
      `[BUILD]` `[PROVE]`
4.4.4 Deny an agent to itself (`tools` without `Agent`) and prove it cannot spawn. `[BUILD]`
      `[PROVE]`
4.4.5 Diff vs the real one: `progress-verifier.md` and `calibrator.md` — pointer bodies, write
      boundaries, withheld tools, artefact-only evidence.

*(5 leaves)*

## §4.5 A headless orchestrator

4.5.1 `[JAVA]` A Java 21 `ClaudeRunner`: `ProcessBuilder` around `claude -p`, `--output-format
      json`, a record for the envelope, Jackson parsing, and the unparseable-input snippet
      preserved on failure. `[BUILD]` `[JAVA]`
4.5.2 `[JAVA]` Add the three ceilings: `--max-turns`, `--max-budget-usd`, and a
      `Process.waitFor(Duration)` wall clock, each with a distinct exception type. `[BUILD]`
      `[JAVA]`
4.5.3 `[JAVA]` Add `--settings <absolute path>` and explain, in a comment, the §3.7 incident it
      prevents. `[BUILD]` `[JAVA]`
4.5.4 `[JAVA]` Add parameter → env → default resolution for every knob, checked so an explicit
      zero survives. `[BUILD]` `[JAVA]`
4.5.5 `[JAVA]` Add a bounded retry that keeps the last parsed error envelope, and a bulkhead on
      concurrency. `[BUILD]` `[JAVA]` `[X-REF 05]`
4.5.6 A two-stage pipeline over it: stage 1 writes a file, stage 2 reads it, neither writes to its
      own input. Prove stage 2 is independently re-runnable. `[BUILD]` `[PROVE]`
4.5.7 Emit a cost and token report per stage from the envelopes. `[BUILD]`
4.5.8 Diff vs the real one: `engine/agent.py` — persona loading with frontmatter stripping,
      envelope extraction, the retry loop, the resolution order, `--resume` continuation legs, and
      every default constant with its recorded reason.

*(8 leaves)*

## §4.6 A plugin

4.6.1 Package §4.2–§4.4 as a plugin: `.claude-plugin/plugin.json`, `skills/`, `agents/`,
      `hooks/hooks.json`. Test with `--plugin-dir`. `[BUILD]`
4.6.2 `claude plugin validate`, then `--strict`. Fix what it reports. `[BUILD]` `[PROVE]`
4.6.3 Publish it to a local marketplace: `.claude-plugin/marketplace.json`, `/plugin marketplace
      add`, `/plugin install`, `/reload-plugins`. `[BUILD]`
4.6.4 Bump `version` and prove an installed copy updates. `[BUILD]` `[PROVE]`
4.6.5 Add a `dependencies` entry on a second local plugin, and demonstrate both the unresolved
      state and the `claude plugin list --json` `errors` array that reveals it. `[BUILD]` `[PROVE]`
4.6.6 Diff vs the real one: the sdlc-harness plugin and marketplace — cross-marketplace
      dependency trust, `${CLAUDE_PLUGIN_ROOT}` path discipline, content-hash version nudging, and
      a bootstrap skill that provisions what a plugin cannot install declaratively.

*(6 leaves)*

## §4.7 Verification harness

4.7.1 A `verify.sh` for this repository's own notes: text-ness assertion first, then every
      structural check, then re-run every fenced listing. `[BUILD]`
4.7.2 Make one check fail deliberately and confirm it fails loudly rather than skipping. `[BUILD]`
      `[PROVE]`
4.7.3 Wire it as a `Stop` hook and as a CI job, and state which failures belong in which. `[BUILD]`
4.7.4 A skill eval: three prompts that should trigger a skill and three that should not; run and
      score them. `[BUILD]` `[PROVE]`

*(4 leaves)*

---

**PART 4 total: 40 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "How do you use AI in your workflow?" — the 60-second answer that is about systems, not
      tools, and the three follow-ups it invites.
5.1.2 "What is a context window?" — the answer that includes the cost consequence, not just the
      number.
5.1.3 "Why does a long session get worse?" — compaction, prefix cost, and drift, in that order.
5.1.4 "How do you stop an agent doing something destructive?" — deny rules, `PreToolUse` blocking
      hooks, sandbox, withheld tools, human gates. Ranked by strength, and why prompting is not on
      the list.
5.1.5 "Deny beats allow — why does that matter?" — the allowlist-exception trap in one sentence.
5.1.6 "What is the difference between `CLAUDE.md`, a skill, and a hook?" — always-on context,
      on-demand context, guaranteed execution.
5.1.7 "When do you use a subagent?" — verbose-in/small-out, parallel with disjoint writes,
      different capability set. Plus the 2× cost.
5.1.8 "How would you run this in CI?" — `-p --output-format json`, the three ceilings,
      `--settings` by absolute path, `setup-token`, and what must not be present.
5.1.9 "Tell me about a bug you debugged in your tooling." — the §3.7 walkthrough in 90 seconds.
5.1.10 "How do you know the agent's output is correct?" — executable evidence, re-running published
       artefacts, and the checker-that-can-be-switched-off law.
5.1.11 "What does this cost?" — the four billed quantities, cache economics, and where the money
       actually goes in a real session.
5.1.12 "How would you roll this out to 200 engineers?" — plugin + marketplace, managed settings,
       `strictPluginOnlyCustomization`, evals, and a calibration loop. With the honest ceiling:
       review capacity.
5.1.13 "What are the risks?" — prompt injection, credential blast radius, plausible-but-wrong
       output, unbounded cost, and skill atrophy. One mitigation each.
5.1.14 "Where would you not use it?" — and why having an answer here is itself a signal.
5.1.15 The Staff framing paragraph, drafted: capability as a versioned platform, determinism where
       the answer is unique and agency only where judgment is required, hard cost ceilings as
       reliability engineering, capability denial at the tool layer, human confirmation for
       outward-facing actions, and agent failures treated as a measurable defect stream.
5.1.16 The three questions to ask *them*, which reveal whether their AI story is real: who owns the
       tooling, what is measured, and what happened the last time it went wrong.

*(16 leaves)*

## §5.2 The trap index

5.2.1 Consolidate every `**Trap:**` marker in the guide into one table: wrong belief → symptom →
      fix → section.
5.2.2 The version-stale table: every claim that was true in an earlier release and is not now, with
      both versions stated. `[VERSION]`
5.2.3 The top five, for the reader who has ten minutes: rules are enforced by the harness not the
      model; deny cannot carry exceptions; `allowed-tools` pre-approves rather than restricts;
      `--setting-sources` resolves against `cwd`; `${CLAUDE_PLUGIN_ROOT}` is not the repo.
5.2.4 The incident index: every `[INCIDENT]` leaf, one line each, with its cost and its law.

*(4 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The atomic concept checklist: one falsifiable assertion per mechanism, grouped by part.
5.3.2 Numbers drill: 1,536 / 200 lines / 25 KB / 4 MiB / 4 hops / 5,000 / 25,000 / 1,000 patterns /
      20 agents / depth 3 / 5 rules / 160 turns / 1800 s / 500 chars. State what each governs.
      `[NUM]`
5.3.3 Precedence drill: order the settings layers, the permission lists, the agent locations, the
      skill locations, and the `CLAUDE.md` load order — from memory. Note that agents and skills
      order oppositely.
5.3.4 Mechanism drill: for ten observed behaviours, name the file or key that caused it.
5.3.5 Config-reading drill: given a `settings.json`, a `hooks.json` and an agent file, predict what
      a given command does. Then run it.
5.3.6 Cost drill: given a session shape, estimate the bill; then check against `/cost`.
5.3.7 The "explain it to a colleague" test for the five PART 0 concepts.
5.3.8 A review schedule: PART 0 once and never again; the trap index weekly; the numbers drill
      before any interview.

*(8 leaves)*

---

**PART 5 total: 28 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 0 — Ground zero | 46 |
| PART 1 — Basics | 125 |
| PART 2 — Intermediate | 142 |
| PART 3 — Under the hood | 96 |
| PART 4 — Build it | 40 |
| PART 5 — Interview & retention | 28 |
| **Total** | **477** |

Leaves carrying `[ZERO]`: **~30** (all of PART 0 plus the first leaf of most PART 1–3 sections).
`[DOC]`: **~150**. `[CASE]`: **~45**. `[BUILD]`: **~60** (all of PART 4, plus the diagnostic and
proof leaves in PARTs 1–3). `[TRAP]`: **~45 as tagged, but the finished note set produced 154 distinct traps** — writers used `**Pitfall:**` for every wrong belief a leaf surfaced, so treat the tag count as a floor, not an estimate. `[INCIDENT]`: **14 tagged leaves (16 raw occurrences — §2.3.25 and §3.6.15 each carry the tag twice, at the leaf's opening and its close) → 13 distinct events → 10 operational.** All three numbers are correct and the tally was previously underspecified, which is why three agents reported 11, 10 and 14. Enumerated so it cannot drift again: the 14 tagged leaves are 1.4.28a, 1.4.34a, 2.1.24, 2.3.15a, 2.3.25, 3.6.11, 3.6.15, 3.7.1, 3.10.2, 3.10.3, 3.10.4, 3.10.5, 3.10.6, 3.10.7. §3.10.4 ("md5 over a patched harness") and §3.10.5 ("unpinned digest") are **one event**, the second being the first restated as a law — collapse them rather than padding, giving 13 distinct events. Three of those are **not operational incidents** but this project's own documentation defects, recorded deliberately: 1.4.28a, 1.4.34a and 2.3.15a each mark a claim this syllabus itself asserted wrongly until 2026-08-30. Excluding those leaves **10 operational incidents**, which is the number §5.2.4's incident index should carry. **Report the three documentation corrections separately, and never assign them a cost figure:** they have no production symptom and no fix in the harness, so the `[INCIDENT]` obligation to "name what it cost" would force an invented number — the exact defect §3.10.2 exists to warn against. For those three, the cost is the wrong belief propagating, stated as such. Note 2.1.24 (the same-slug lane collision) IS operational — it happened during topic 02's run. `[NUM]`: **~60**.
`[VERSION]`: **~20**. `[JAVA]`: **~15**. `[PROVE]`: **~45**.

---

## Coverage delta vs the existing guide

The existing guide is `src/topics/21-ai-for-coding.md` (511 lines, written 2026-08-29). It was
written for a reader with working familiarity, not from zero, and against the harness repo plus
prior knowledge rather than against the docs. This table is what the write pass owes.

| Syllabus area | Present in the guide | Missing | Verdict |
|---|---|---|---|
| §0.1–0.4 ground zero (46) | §1's three-step loop and the three consequences table | **all 46 leaves as taught-from-zero content**: token, sampling, confabulation, cutoff, message roles, tool schema, `tool_use`/`tool_result`, the diagnostic command set, `/context` walkthrough | **the guide's largest gap**; it assumes the vocabulary it should teach |
| §1.1 `.claude` anatomy (9) | the folder tree, the harness's nine commands | the user twin's full inventory, `~/.claude.json`, `CLAUDE_CONFIG_DIR`, the discovery walk, `rules/`, `.lsp.json`, `agent-memory/` | tree without mechanism |
| §1.2 settings & precedence (16) | the five-layer table, four keys, the harness's real block | 15 of 16 key groups, `env` composition, where the local file lands, silently-ignored keys, verification path | correct but thin; the precedence table omits that managed beats CLI |
| §1.3 `CLAUDE.md` & memory (29) | "always-paid context", the 441-line observation, the 200-line-ish instinct | **auto memory entirely**, `.claude/rules/`, path-scoped rules, imports and the 4-hop limit, load order and concatenation, `AGENTS.md`, `claudeMdExcludes`, every number | one paragraph where a section is owed |
| §1.4 permissions (45) | deny-beats-allow, four modes, the harness's allow block | **41 of 45**: evaluation order, the wildcard table, compound commands, wrapper stripping, the read-only set, gitignore patterns, which tools consult path rules, `Agent()`/`Cd()`/parameter rules, workspace trust, the `-p`-counts-as-trusted trap, sandbox | the guide's second-largest gap; the mode table is also incomplete (four of six) |
| §1.5 skills & commands (26) | progressive disclosure, `$ARGUMENTS`, the ` ```! ` composition case, the topic-vs-trigger trap | the commands-are-skills merge, precedence, 15 of 20 frontmatter fields, substitutions, the content lifecycle, compaction re-attachment budgets, `context: fork` | **contains one outright error**: it claims `allowed-tools` narrows the capability surface. It pre-approves and does not restrict. Must be corrected, and kept as a `[TRAP]` |
| §2.1 subagents (25) | fresh-context isolation, the four design properties, the ~2× cost, the lane-collision incident | locations and precedence, 17 frontmatter fields, what loads/doesn't at startup, forks, all the numeric limits, agent memory, resume | the strongest existing section; still a third of the leaves |
| §2.2 personas (7) | `--agent` vs `--append-system-prompt`, frontmatter stripping | `--system-prompt` replacement, subagent prompt appending, the cache-protection flag | good for its length |
| §2.3 hooks (33) | six events named as "common", the schema, `check-init.sh`, the reindex incident | **31 of 33**: the 33-event catalogue, which can block, the five handler types, stdin fields, exit-code semantics, the JSON output contract, the six configuration sources | events named, mechanism absent |
| §2.4 MCP (13) | `mcp__server__tool` naming, one sentence on servers | 12 of 13, including the `enabledMcpjsonServers` trap the harness itself documents | effectively absent |
| §2.5 plugins (20) | structure, `plugin.json`, marketplace, cross-marketplace trust, the `CLAUDE_PLUGIN_ROOT` trap, the silent-dependency trap | monitors, `bin/`, `.lsp.json`, plugin `settings.json`, namespacing rules, the governance keys, `strictPluginOnlyCustomization` | good; missing the org-control half |
| §2.6 context economy (12) | isolation and precision as the two levers, the LSP token argument | `/context` attribution, autocompaction keys, what survives, cache economics, the session protocol | argued, not operationalised |
| §2.7 practices (12) | — | all 12 leaves, including the whole plan-mode and test-first discussion | absent |
| §2.8 deterministic vs agentic (9) | the rule, the bootstrap quote, the decision table | idempotence, the `uv` exception and its reasoning, the prompting-for-determinism trap | the guide's best section |
| §2.9 governance & security (11) | one line on capability denial | 10 of 11: threat model, prompt injection, secrets, managed delivery, the `allowManaged*Only` family, attribution | absent |
| §3.1 request assembly (8) | the five-channel framing | the actual order, the "CLAUDE.md is a user message" fact, schema costs, transcript reading | reframed, not opened |
| §3.2 compaction (7) | one clause | all 7 leaves | absent |
| §3.3 permission evaluation (8) | — | all 8 leaves | absent |
| §3.4 cost model (9) | the two-stop-condition argument, the $5.16 incident | the four billed quantities, pricing, cache arithmetic, reading cost from an envelope | one good story, no model |
| §3.5 effort & routing (6) | — | all 6 leaves | absent |
| §3.6 headless mode (18) | the flag table, both ceilings, the envelope-parsing law, the retry classes, the 160-turn incident | `stream-json`, `--json-schema`, session control, `setup-token`, background/remote, the resolution-order pattern, `--add-dir` as an unused seam | the second-strongest section |
| §3.7 the `--setting-sources` incident (9) | the mechanism, the symptom, the fix, both generalisations | the ADR trail and the 90-second telling | nearly complete |
| §3.8 SDK & API (8) | — | all 8 leaves, including the Java options the reader actually has | absent |
| §3.9 orchestration (12) | — | all 12 leaves: playbooks, conductor vs prose executor, folded state, judges, calibration, evals | absent, and it is where the harness has the most to teach |
| §3.10 verification (11) | two laws (re-run published artefacts, the NUL-byte checker) | 9 of 11, including the command-shape traps and the review-capacity ceiling | two laws, well told |
| PART 4 build it (40) | **nothing** — the guide has illustrative snippets only | all 40 leaves | — |
| §5.1 interview questions (16) | a two-paragraph Senior/Staff framing | 16 structured questions with answer shapes | framing without drill |
| §5.2 trap index (4) | 12 inline `**Trap:**` markers, all worth keeping | the consolidated table, the version-stale table, the top five, the incident index | — |
| §5.3 drills (8) | a 24-line atomic concept checklist, all lines worth keeping | the numbers, precedence, mechanism, config-reading and cost drills, and the review schedule | — |

Summary: of **477** leaves, roughly **95** are present in the existing guide at any depth, **70** of
those at a depth to keep and expand, and **382** are missing outright. (Written at 468 leaves and
rebaselined 2026-08-30 to 477; the §1.4 and §2.3 rows now include the lettered leaves the correction
passes added.) One existing claim is
**wrong** — that a skill's `allowed-tools` restricts its capability surface — and must be corrected
in place and re-published as a `[TRAP]`, because the belief is common and the consequence is a
false sense of least privilege. Two existing claims are **incomplete in a misleading direction**:
the permission-mode table lists four of six modes, and the settings-precedence table does not say
that managed settings outrank the command line.

The single structural decision for the write pass: **PART 0 must be written first and reviewed
against a real level-0 reader before any other part is drafted.** Every later part references its
vocabulary, so a weak PART 0 does not degrade the guide gracefully — it makes the remaining 431
leaves unreadable.
