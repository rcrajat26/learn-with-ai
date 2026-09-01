# 21 AI for Coding — settings keys and verification — BASICS (§1.2.9–1.2.16)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [settings files and precedence](01-basics-files-and-precedence.md) · Next: [`CLAUDE.md` and the memory system](../memory/01-basics-claude-md.md)

The previous file established four files and a five-layer precedence stack — *which file wins* when
two of them set the same key. This file is about *which keys exist to fight over in the first place*:
the fifteen groups those keys sort into, the twelve you will actually touch in your first week, the
`env` key's reach into hooks and Bash, how to check that a key you set actually took effect, one key
that is silently thrown away no matter how you write it, and the flag that decides which of the four
files even gets read before precedence has anything to arbitrate.

## §1.2.9 The fifteen key groups, and §1.2.10 the twelve you touch first

**[DOC]** Quoting `settings-reference` (`https://code.claude.com/docs/en/settings-reference`,
re-verified before this leaf): the page organizes every settings key under one of these topic
headings — Permission settings, Hooks and automation, Model and responses, Memory and context,
Interface and terminal, Plugins and skills, Agents, sessions, and worktrees, Remote, desktop, and
notifications, Authentication and providers, Updates and versioning, Privacy and telemetry, Git and
attribution, MCP, Sandbox settings, and Enterprise and managed settings — plus a separate Global
config category for keys that live in `~/.claude.json` rather than in a settings file at all. That
is the fifteen-group map this leaf asks for, renamed slightly below to match how engineers actually
talk about them (Data/Privacy for Privacy and telemetry, Auth for Authentication and providers,
Attribution for Git and attribution).

You do not need all of them on day one. Twelve keys cover almost everything a new user configures in
their first week: `permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`,
`autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`, `statusLine`,
`cleanupPeriodDays`. All twelve are re-verified spellings against `settings-reference` — none is
guessed.

| Group | Representative key | What it controls | Reader touches first? |
|---|---|---|---|
| Permissions | `permissions` | Allow/ask/deny rules and the starting permission mode | **Yes** |
| Hooks and automation | `hooks` | Run your own commands at points in Claude Code's lifecycle | **Yes** |
| Plugins and skills | `enabledPlugins` | Turn individual plugins on or off, per scope | **Yes** |
| Memory and context | `autoCompactEnabled` | Turn automatic compaction off or on | **Yes** |
| Model and responses | `model` | The model a session starts with | **Yes** |
| MCP | `allowedMcpServers` | Allowlist which MCP servers people can use | No |
| Sandbox settings | `sandbox.enabled` | Turn on Bash sandboxing on macOS, Linux, WSL2 | No |
| Git and attribution | `attribution.commit` | Change or hide the trailer Claude Code adds to commits | No |
| Authentication and providers | `forceLoginMethod` | Restrict login to claude.ai, Console, or a cloud gateway | No |
| Privacy and telemetry | `cleanupPeriodDays` | Days Claude Code keeps transcripts before deleting them | **Yes** |
| Interface and terminal | `statusLine` | Run your own command to render a status line | **Yes** |
| Agents, sessions, worktrees | `agent` | Start every session as a named subagent | No |
| Updates and versioning | `autoUpdatesChannel` | Follow the stable release channel instead of latest | No |
| Enterprise and managed | `forceRemoteSettingsRefresh` | Block startup until managed settings refresh from the server | No |
| Global config (`~/.claude.json`) | `autoConnectIde` | Auto-connect to a running VS Code/JetBrains IDE | No |

**D-22** — The settings key groups, and the twelve this reader touches first.

Seven of the fifteen rows above already name a first-touch key as their representative. The
remaining five first-touch keys live inside groups already represented by a different key:
`env`, `autoCompactWindow`, `autoMemoryEnabled`, and `claudeMdExcludes` all sit in **Memory and
context** alongside `autoCompactEnabled`; `effortLevel` sits in **Model and responses** alongside
`model`. That is not a coincidence — memory/context and model/responses are the two groups a brand
new user has the most reason to touch, because they govern cost and behaviour directly, so the
syllabus concentrates five of the twelve first-touch keys in exactly those two groups.

### `[DOC]` `[BUILD]` The twelve keys, with values

A single, complete, valid `settings.json` setting all twelve — no elisions, no implied parent keys,
no comments (JSON has none; the explanation sits beside the block):

```json
{
  "permissions": {
    "allow": ["Bash(mvn -q test)", "Bash(git status)", "Bash(git diff:*)"],
    "ask": ["Bash(git push:*)"],
    "deny": ["Bash(rm -rf *)"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": ".claude/hooks/format-on-edit.sh" }]
      }
    ]
  },
  "env": {
    "MAVEN_OPTS": "-Xmx2g"
  },
  "model": "claude-sonnet-5",
  "effortLevel": "high",
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true
  },
  "autoCompactEnabled": true,
  "autoCompactWindow": 20000,
  "autoMemoryEnabled": true,
  "claudeMdExcludes": ["legacy/**/CLAUDE.md"],
  "statusLine": {
    "type": "command",
    "command": ".claude/statusline.sh"
  },
  "cleanupPeriodDays": 30
}
```

Every value here is a realistic one for a Java/Spring engineer's project file: an `allow` list of the
read-only and test commands used every day, a `deny` on the one command that would wipe a working
tree, a `PostToolUse` hook that reformats a file the moment Claude edits it, a `MAVEN_OPTS` bump for a
memory-hungry build, `effortLevel: "high"` (the default reasoning level on Sonnet 5 and Opus 5;
**[VERSION]** the value `"max"` is accepted by `/effort` in an interactive session but is **not**
a legal value for the `effortLevel` key in a settings file — the only way to run at `max` is the
`CLAUDE_CODE_EFFORT_LEVEL` environment variable for that one session), a compaction window set to
trigger a little earlier than the default so a long refactor doesn't blow past it mid-edit, and a
90-day-shorter-than-default transcript retention.

**Prove.** After writing the file above at project scope, start a session in that directory and run:

```
$ claude --print "/status"
```

The Status tab's `Setting sources` line lists `Shared project settings` among the files it loaded,
and the same dialog's model line shows `claude-sonnet-5` with `(project)` next to it — the
project-scope `model` key is not merely present in the file, it is the value the session actually
started with. `claude doctor` confirms independently: its resolved-settings view shows
`effortLevel: high`, `autoCompactWindow: 20000`, and `cleanupPeriodDays: 30` each attributed to the
project file, with no rejected entries listed.

**What this costs.** Nothing to write or load — settings files are read once at startup and are not
re-sent as part of the conversation, so they consume zero tokens per turn. The cost is indirect and
runs entirely through the *behaviour* the keys turn on: `effortLevel: "high"` versus `"low"` on the
same prompt is the single biggest per-turn cost lever in this file (§3.4's material has the
arithmetic), and a `hooks.PostToolUse` entry that shells out on every edit adds wall-clock latency,
not tokens, to every `Write`/`Edit` call.

## §1.2.11 `env`: settings-supplied environment variables, and their reach into hooks and Bash

**Mental model.** `env` in a settings file is not a convenience for *your* shell — it is Claude Code
injecting variables into the environment of **every process it spawns for the session**: the model
subprocess's own tool calls, every hook script, and every Bash command the session runs, exactly as
if you had `export`ed them before launching `claude` yourself.

**[DOC]** Quoting `settings-reference`: `env` "Set environment variables for every session and its
subprocesses." That phrase — "and its subprocesses" — is the entire leaf. A hook is a subprocess
(§2.3's material); a `Bash` tool call is a subprocess. Both inherit whatever `env` sets, with no
opt-out.

**How it composes across scopes.** `env` is a plain object, and Claude Code merges it the way it
merges any object-valued key across the five layers: key by key, not whole-object replacement. A
user-scope `env` setting `JAVA_HOME` and a project-scope `env` setting `MAVEN_OPTS` are both present
in the final session — they don't collide, because they set different keys. When two layers set the
**same** environment variable name, ordinary precedence applies: the higher layer's value wins for
that name, same as any scalar key, per the five-layer rule from §1.2.2.

**Security consequence.** Because `env` reaches Bash and hooks and not just the model's own reasoning,
a project-scope `env` entry is a vector for a hostile repository: a cloned project whose committed
`.claude/settings.json` sets `NODE_OPTIONS` or an `HTTP_PROXY`-style variable is not merely changing
what the *model* sees, it is changing what every shell command in the session executes against,
including commands the reader typed themselves before Claude touched anything. This is exactly why
most `env` values are one of the keys workspace trust gates (§1.2.8's trust list, quoted there):
an untrusted clone's `env` entries do not apply until the folder is explicitly trusted, which is the
harness's actual defence against this vector, not any property of `env` itself.

**Interview:** *"If a settings file sets `env`, does that apply to commands I run in Bash?"* — Yes.
`env` sets variables for the session's subprocesses generally, which includes both hook scripts and
every `Bash` tool invocation, not only the model's own context; that is also why most `env` values
wait for workspace trust before an untrusted project's file can inject them.

> **`env` in a settings file exports environment variables into every subprocess the session
> spawns — hooks and Bash included, not only the model's own tool calls — merging per-variable-name
> across layers with ordinary precedence deciding a name-level collision.**

## §1.2.12 `[CASE]` The harness's real `settings.json`

The full, real, project-scope settings file at `sdlc-harness/.claude/settings.json`, quoted verbatim
and in full — it is short:

```json
{
  "permissions": {
    "allow": ["Read(**)", "Edit(**)", "Bash(*)", "mcp__atlassian-cloud__*"]
  },
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true,
    "typescript-lsp@claude-plugins-official": true,
    "jdtls-lsp@claude-plugins-official": true,
    "sdlc-harness@sdlc-harness": true
  }
}
```

Two keys, four entries each. Every entry, explained:

**`permissions.allow`, four entries:**

- `Read(**)` — pre-approves reading any file, at any depth, within the working directory and
  configured additional directories. Without it, every file read the harness's own agents perform
  while orchestrating a story would otherwise be a no-op anyway (reads are approval-free by default
  per the permission table in `permissions`), so this entry's real job is documentation of intent
  rather than a behaviour change — it states plainly, for anyone auditing the file, "this project
  expects unrestricted reads," rather than leaving it implicit.
- `Edit(**)` — pre-approves file edits anywhere reachable, which **is** a behaviour change: without
  it, every `Edit` or `Write` the harness's engine performs while implementing a story would prompt.
  A tool that spawns dozens of `claude -p` subprocesses across a pipeline (§3.9's material) cannot
  have a human standing by to click "yes" on each one; this rule is what makes the headless pipeline
  runnable at all.
- `Bash(*)` — pre-approves every shell command with no restriction on which one. This is the widest
  possible `Bash` rule available; the harness's own build, test, and lint steps all run through
  `mvn`, `uv`, and similar tools invoked as Bash commands from inside its own orchestrated sessions,
  and a narrower allowlist would have to be re-derived and maintained by hand every time a playbook
  step added a new command.
- `mcp__atlassian-cloud__*` — pre-approves every tool from one named MCP server, `atlassian-cloud`,
  using the wildcard form anchored to a literal `mcp__<server>__` prefix (§1.2.14 explains why the
  server segment specifically cannot itself be a wildcard). This is the harness reading and writing
  Jira/Confluence state as part of its SDLC pipeline without a prompt on every ticket lookup.

**`enabledPlugins`, four entries, three official LSP plugins plus its own:**

- `pyright-lsp@claude-plugins-official` — Python language-server support, so agents get real
  type information and go-to-definition over Python sources rather than treating them as plain text.
- `typescript-lsp@claude-plugins-official` — the same for TypeScript/JavaScript sources.
- `jdtls-lsp@claude-plugins-official` — the same for Java, via the Eclipse JDT language server —
  the one of the three most relevant to this reader's own Java 21/Spring Boot work, since it is what
  gives an agent editing a `.java` file real symbol resolution instead of regex-level guessing.
- `sdlc-harness@sdlc-harness` — the harness's own plugin, enabling itself: its hooks, agents,
  skills, and commands only load into a session if this entry (or an equivalent one at another
  scope) turns the plugin on. A repository can ship a plugin without this entry and it simply
  won't activate.

**Design property named:** this file buys the harness **unattended, cross-language operability** —
every read, every edit, every shell command, and one MCP server's tools all run without a human in
the loop, while three LSP plugins give agents structural understanding of the three languages the
repository's own code and the code it operates on are written in. **What would break without it:**
strip `Edit(**)` and `Bash(*)` and the headless `claude -p` engine in
`harness/src/harness/engine/agent.py` (§2.2's material) would stall on the very first file write or
`mvn` invocation, waiting on a permission prompt no terminal is attached to answer; strip
`sdlc-harness@sdlc-harness` and none of the plugin's own hooks, agents, or skills would be available
in a session at all, regardless of how the repository's other files are configured.

## §1.2.13 `[BUILD]` Verifying a setting actually applied

Four independent ways to check whether a key you just wrote is the key actually in effect, from
weakest to strongest:

1. **`/config`** — opens a dialog on the Config tab. **[DOC]** the Config tab "isn't a view of your
   `settings.json` contents"; it's a UI for editing user-scope preferences (theme, editor mode) and
   writes back to `~/.claude/settings.json` when you change something there. Use it to *change* a
   user-scope key, not to audit what a project file set.
2. **`/permissions`** — **[DOC]** "You can view and manage Claude Code's tool permissions with
   `/permissions`. The dialog lists all permission rules and the `settings.json` file each rule
   comes from." This is the right tool specifically for `permissions.allow`/`ask`/`deny`: it names
   the winning rule **and** which of the four files supplied it, which a plain read of any one file
   cannot tell you when more than one file sets overlapping rules.
3. **`claude doctor`'s resolved settings** — **[DOC]** quoting `settings`: "To list entries Claude
   Code rejected, run `claude doctor`." Run it after any settings edit; it enumerates every key it
   resolved and, separately, every entry it threw out, which is the only one of the four checks here
   that surfaces a *silently dropped* value rather than a correctly-applied one.
4. **The invalid-settings dialog** — **[DOC]** at the start of an interactive session, "Claude Code
   shows a dialog that lets you fix the file with Claude's help, exit, or continue without the broken
   settings" whenever a user, project, or local file has invalid JSON or a value the schema rejects.
   A `-p` (headless) run shows no dialog and silently continues with the broken file skipped —
   `claude doctor` after the run is how you find out what a headless run dropped.

**Prove.** Take the `settings.json` from §1.2.10, deliberately misspell one key as `autocompactWindow`
(wrong case) and start an interactive session:

```
$ claude
```

The invalid-settings dialog appears immediately, naming the offending file and offering to fix it.
Choosing "continue without the broken settings" and then running `/status` shows `Setting sources`
still lists the file (it loaded, minus the bad entry), and `claude doctor` lists the misspelled key
under rejected entries with the file path that set it.

**What this costs.** All four checks are local, synchronous, and free — none of them is a model call,
so none consumes a token or a dollar. The cost of *skipping* them is what the rest of this file (and
§1.2.14 next) is about: time spent debugging a setting that "should have worked."

## §1.2.14 `[TRAP]` `[DOC]` The silently-ignored key

Three distinct cases, all accepted by the settings loader and then thrown away, each with its own
mechanism:

1. **An unrecognized key or a malformed rule.** **[DOC]** quoting `settings`: "**Settings Warning**:
   only individual entries fail, such as a malformed permission rule or an unknown hook event name.
   Claude Code skips those values and keeps the rest of the file in effect." The file as a whole is
   not rejected — only the bad entry is, silently, with the rest of the file still active.
2. **An `mcp__` rule written with parentheses.** **[DOC]** quoting `permissions`: "When Claude Code
   loads a settings file, it skips any `mcp__` rule that has parentheses. Claude Code lists the
   skipped rule in the invalid-settings dialog when an interactive session starts, and in
   `claude doctor` output." A rule like `"mcp__atlassian-cloud__search(project:ENG)"` — written by
   someone who assumes an MCP tool parameter can be scoped the same way `WebFetch(domain:...)` or
   `Bash(git diff:*)` scope a built-in tool — parses as valid JSON and is silently dropped in full.
   The correct mechanism for scoping an MCP tool parameter is `--disallowedTools` on the command
   line, not a parenthesized settings rule.
3. **A path-shaped rule on a tool whose content field isn't matchable that way.** **[DOC]** quoting
   `permissions`: "You can't match a tool's primary content field this way: `command` for Bash and
   PowerShell, `file_path` for Read, Edit, and Write, `path` for Grep and Glob, `notebook_path` for
   NotebookEdit, and `url` for WebFetch. A rule like `Bash(command:rm *)` would be bypassable by a
   compound command, so Claude Code ignores it and emits a startup warning." Someone writing
   `Bash(command:rm *)` because they read `WebFetch(domain:example.com)` and generalized the pattern
   gets a rule that is accepted, printed back by no error, and never once evaluated.

**Pitfall:** the belief in action is "I added the rule, so it's enforced" — the settings file
parses, `git diff` shows the new line committed, and nothing in the terminal's normal output objects.
The surprising outcome is the config looking right while the behaviour doesn't match it at all: a
denied command still runs, an MCP scope never narrows, a permission the author was certain they'd
locked down is wide open. All three cases share one symptom — a startup warning is emitted, but it is
printed once, scrolls past in a wall of session-start text, and is not repeated. **The fix**, every
time, is `claude doctor`: it is the one check from §1.2.13 that lists rejected entries by name rather
than only confirming the ones that succeeded. **Why people believe it:** most config systems either
reject an invalid file outright (so the mistake is loud) or apply exactly what's written (so the
mistake is silent but at least matches the file); Claude Code's settings loader does neither — it
accepts the file, drops only the bad line, and reports the drop in a channel (`claude doctor`, the
invalid-settings dialog) the author has to go looking for rather than one that interrupts them.

## §1.2.15 Managed settings as an org control surface

Managed settings exist so an organization can set security policy that individual engineers cannot
switch off from their own laptop, no matter which of the other four files they edit: keys like
`allowManagedPermissionRulesOnly` (referenced from `permissions`: "unless your organization sets
`allowManagedPermissionRulesOnly`", which otherwise lets project/user `permissions.allow` rules merge
in alongside the managed ones) lock a category of key to the managed source exclusively, so a
developer who adds their own conflicting `permissions.allow`, `model`, or `enabledPlugins` entry
finds it silently ignored rather than merged or overridden — the same "accepted but discarded"
shape as §1.2.14, but here it is the deliberate, documented behaviour of a security control rather
than a typo. A developer cannot override an `allowManaged*Only` lock by any combination of the other
four files or the command line, because the five-layer stack (§1.2.2) puts managed settings above
all of them and this family of keys additionally removes the normal per-key merge that would
otherwise let a lower layer contribute alongside it. The full treatment — the complete lock list, how
several managed sources combine with each other, and the "invalid entries in managed settings" fallback
behaviour — is `governance/01-security-and-the-org-view.md`, §2.9; this leaf states only that the
surface exists and why a developer cannot route around it.

## §1.2.16 `[DOC]` `--setting-sources`: choosing which layers load at all

Every leaf so far in §1.2 assumed all four settings files that exist get read, and precedence decides
which one wins a given key. `--setting-sources` operates one level earlier than that: it decides
which files are **read in the first place**, before precedence has anything to arbitrate.

**[DOC]** Quoting `cli-reference`, re-verified before this leaf: the flag takes a comma-separated
list drawn from `user`, `project`, `local`, and controls which settings layers load at all for that
invocation — not precedence among the ones that do load. `--setting-sources user,project` loads only
the user and project layers and skips project-local entirely, for that one invocation.

```
claude --setting-sources user,project -p "Run the mvn-test-runner playbook against the story worktree"
```

**Insight:** `--setting-sources` and the five-layer precedence order answer two different questions
that are easy to conflate because both involve the word "settings." Precedence answers "given that
files A and B both set key K, which value wins?" `--setting-sources` answers "does file B even get
opened this session?" — a file excluded by `--setting-sources` isn't outranked, it's never read, so
it cannot win *or* lose a precedence fight over any key. Note that managed settings are not one of
the three names this flag accepts at all — there's no way to use `--setting-sources` to exclude an
organization's managed policy; the flag only ever narrows the three non-managed layers.

This is exactly the mechanism at the centre of a real production incident: a `--setting-sources
project` invocation against a per-story git worktree silently dropped an entire permission block the
team assumed was in effect. That incident is walked in full — what broke, what it cost, and the fix —
in `setting-sources-incident/03-internals-root-cause.md`, §3.7. The mechanism stated here is
everything needed to follow it; the root cause is not spoiled in this file.

## Pitfalls

**Belief in action:** "I added `mcp__atlassian-cloud__search(project:ENG)` to `permissions.allow` to
scope which project the tool can search." **Surprising outcome:** the rule is accepted as valid JSON,
never appears in any error, and the tool remains unscoped — every project is searchable exactly as
before. **What actually gets the guarantee:** scope an MCP tool parameter with `--disallowedTools` on
the command line; a settings-file rule can only ever name the tool, never a parameter inside it, and
any `mcp__` rule with parentheses is skipped on load. **Why people believe it:** `WebFetch(domain:...)`
and `Bash(git diff:*)` both use parentheses to scope a built-in tool successfully, so generalizing the
same syntax to an MCP tool's own parameter looks consistent — it isn't, and nothing at write time
tells you so.

**Belief in action:** "I set a key in a managed-locked category from my own user settings because I
have a legitimate reason to differ from the org default." **Surprising outcome:** the key is accepted
by the JSON parser, shows up if you cat the file, and is completely inert — the managed value governs
regardless. **What actually gets the guarantee:** raise the disagreement with whoever owns the
managed file; no combination of the other four files, and no CLI flag, reaches a key an
`allowManaged*Only` lock has claimed. **Why people believe it:** every other key in a settings file
that a developer can write does take effect somewhere in the five-layer stack, so it's a reasonable
default assumption that writing a key is sufficient — for this specific family of keys, it isn't.

## Cheat sheet

| Question | Answer |
|---|---|
| How many key groups does `settings-reference` organize keys into? | 15 |
| The twelve first-touch keys | `permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`, `autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`, `statusLine`, `cleanupPeriodDays` |
| Does `env` reach Bash and hooks, or only the model? | Both Bash and hooks — every subprocess the session spawns |
| Is `effortLevel: "max"` legal in a settings file? | No — `low`/`medium`/`high`/`xhigh` only; `max` requires `CLAUDE_CODE_EFFORT_LEVEL` for one session |
| Tool that names which file supplied a winning permission rule | `/permissions` |
| Tool that lists entries the loader rejected | `claude doctor` |
| `mcp__` rule with parentheses in a settings file | Skipped silently on load, listed in `claude doctor` and the invalid-settings dialog |
| `Bash(command:rm *)` | Ignored, startup warning — a tool's primary content field (`command`, `file_path`, `path`, `notebook_path`, `url`) can't be path-matched this way |
| `--setting-sources user,project,local` controls | Which layers load at all, not which one wins |
| Does `--setting-sources` include a `managed` value? | No — only `user`, `project`, `local`; managed settings always load |

## Self-test

1. Name the fifteen settings key groups.
<details><summary>Answer</summary>Permission settings, Hooks and automation, Model and responses, Memory and context, Interface and terminal, Plugins and skills, Agents/sessions/worktrees, Remote/desktop/notifications, Authentication and providers, Updates and versioning, Privacy and telemetry, Git and attribution, MCP, Sandbox settings, and Enterprise/managed settings — plus Global config for `~/.claude.json` keys.</details>

2. Which settings-file value for `effortLevel` is rejected, and how do you get the equivalent effect
   for one session anyway?
<details><summary>Answer</summary>`"max"` is not a legal `effortLevel` value in a settings file — only `low`, `medium`, `high`, `xhigh` are. To run at `max`, set the `CLAUDE_CODE_EFFORT_LEVEL` environment variable, which applies only to that one session.</details>

3. You wrote `"deny": ["mcp__jira__update(status:closed)"]` to block one specific update. What
   actually happens?
<details><summary>Answer</summary>Nothing is blocked. Claude Code skips any `mcp__` rule that has parentheses when it loads the settings file; the rule is listed as skipped in `claude doctor` and in the invalid-settings dialog, but the tool remains fully callable with no scoping applied.</details>

4. Why does `Bash(command:rm *)` fail to do what its author intended?
<details><summary>Answer</summary>`command` is Bash's primary content field, and content fields (`command` for Bash/PowerShell, `file_path` for Read/Edit/Write, `path` for Grep/Glob, `notebook_path` for NotebookEdit, `url` for WebFetch) can't be path-matched this way because a compound command would bypass it. Claude Code ignores the rule and emits a startup warning; the correct rule is `Bash(rm *)`.</details>

5. In the sdlc-harness's `.claude/settings.json`, what would happen to the headless pipeline if
   `Edit(**)` were removed from `permissions.allow` but everything else stayed the same?
<details><summary>Answer</summary>Every `Edit`/`Write` call the engine's subprocesses make would require a permission prompt, and there is no attached terminal to answer one during a `claude -p` run — the pipeline would stall on its first file write.</details>

6. What is the difference between what `--setting-sources` controls and what the five-layer
   precedence order controls?
<details><summary>Answer</summary>`--setting-sources` decides which settings files are read for the session at all (drawn from `user`, `project`, `local`); precedence decides which value wins when two files that were both actually loaded set the same key. A file excluded by `--setting-sources` can't win or lose a precedence fight — it was never in the merge.</details>

7. Which of the four verification tools (`/config`, `/permissions`, `claude doctor`, the
   invalid-settings dialog) is the only one that reliably surfaces a silently dropped entry?
<details><summary>Answer</summary>`claude doctor` — it enumerates rejected entries by name and by source file. `/config` edits user-scope preferences rather than auditing a project file; `/permissions` names which file a winning rule came from but doesn't list what was dropped; the invalid-settings dialog only appears in an interactive session and only for file-level (not always entry-level) failures, and never appears at all in a `-p` run.</details>

8. Can `--setting-sources` exclude managed settings?
<details><summary>Answer</summary>No. The flag's accepted values are `user`, `project`, and `local` only; managed settings always load regardless of what `--setting-sources` names.</details>

## Open questions

None.

---

**Leaves covered:** 1.2.9–1.2.16 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** D-22
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 436
