# 21 AI for Coding — the six permission modes — BASICS (§1.4.25–1.4.29)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [web, MCP, Agent and Cd rules](04-web-mcp-agent-and-cd-rules.md) · Next: [working directories and workspace trust](06-directories-and-trust.md)

## The concept: a permission mode is a baseline, rules are the override on top of it

Files 01–04 covered the three rule lists (`allow`/`ask`/`deny`) and every specifier shape a rule can
take — `Bash`, path, `WebFetch`, MCP, `Agent`, `Tool(param:value)`, `Cd`. All of that machinery answers
one question per tool call: *does a rule already settle this?* A **permission mode** is the separate
layer underneath that question — it sets what happens for the calls no rule mentions at all. Rules are
still evaluated first inside every mode; a mode only changes the default when no rule matches.

**Why it exists.** Writing a rule for every tool call an agentic session might ever make is not
tractable — the whole point of an agent is that it decides its own next action. A session still needs
*some* default answer for "may this specific untargeted class of action run without asking a human,"
and that default has to be settable per situation: reviewing unfamiliar code wants a human in the loop
on every write, iterating on code already open in an editor wants edits waved through, and a locked-down
CI job wants nothing waved through that was not pre-listed. One mode cannot serve all three; hence six.

`[DOC]` `[NUM]` Re-verified against `https://code.claude.com/docs/en/permission-modes`, 2026-08-29.
There are **six** permission modes, not four:

> Each mode makes a different tradeoff between convenience and oversight. The table below shows what
> Claude can do without a permission prompt in each mode.

— *Choose a permission mode*, re-verified 2026-08-29.

| Config value | CLI/UI label | What runs without asking |
|---|---|---|
| `default` | **Manual** | Reads only |
| `acceptEdits` | Edit automatically | Reads, file edits, and common filesystem commands |
| `plan` | Plan | Reads, plus classifier-approved commands when auto mode is available |
| `auto` | Auto | Everything, with background safety checks |
| `dontAsk` | (no separate UI label) | Only pre-approved tools |
| `bypassPermissions` | Bypass permissions | Everything |

**Insight — the version trap named directly.** A four-mode mental model (`default`, `acceptEdits`,
`plan`, `bypassPermissions`) is the stale form of this table, not a simplification of it. `auto` and
`dontAsk` are not recent afterthoughts bolted onto a stable set of four; `auto` is, as of this target
version, the **built-in starting mode on Pro, Max, and Team plans** — the mode a brand-new session lands
in by default is one that a four-mode answer omits entirely. An interviewer or a colleague who asks "how
many permission modes are there" and expects "four" is asking a stale-form question; the correct answer
names all six and says which one is now the default.

`[DOC]` `[VERSION]` The `default` mode's *label* is **Manual** everywhere except the config value —
CLI, `claude --help`, the VS Code and JetBrains extensions, and the desktop app all display "Manual";
`"defaultMode": "default"` is what settings files and hooks read. The CLI additionally accepts `manual`
as a typed alias for `default` — `claude --permission-mode manual` and `"defaultMode": "manual"` both
work — but that alias, and the Manual label in the CLI specifically, **require Claude Code v2.1.200 or
later**. On an older binary the CLI still calls the mode `default` and `manual` is not accepted as a
value.

`[DOC]` `[VERSION]` The built-in starting mode is `auto` on Pro, Max, and Team plans, but only from
**v2.1.228 or later on macOS/Linux/WSL and v2.1.233 or later on native Windows**; on an earlier binary,
or on an Enterprise plan, or via `claude -p`/the Agent SDK, or when feature-flag fetching is off, the
built-in starting mode is `default` (Manual) instead. A session that resolves to `auto` but where auto
mode isn't actually available (model doesn't support it, or an administrator turned it off) silently
starts in Manual instead — there is no error, only the absence of the `auto` banner at session start.

**D-33** — The six permission modes.

| Mode | Exactly what is auto-approved | What still prompts | What it never allows | Setting that disables it |
|---|---|---|---|---|
| `default` / `manual` | Reads only, within the working directory and `additionalDirectories` | File edits, Bash beyond the built-in read-only set, network, everything else | Nothing mode-specific — it is the fallback every other mode reduces to when turned off | n/a — it is the baseline, not a mode with a kill switch |
| `acceptEdits` | Reads; file edits; `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed` (incl. prefixed by safe env vars or `timeout`/`nice`/`nohup`) — all scoped to the working directory or `additionalDirectories` | Paths outside that scope; protected-path writes; every other Bash command except the built-in read-only set | Writes outside the working-directory/`additionalDirectories` scope without a prompt | No dedicated kill switch — pinned or removed via `permissions.defaultMode` and the `Shift+Tab` cycle |
| `plan` | Reads; classifier-approved shell commands during planning, when auto mode is available | Shell commands outside the read-only set when auto mode is unavailable; every file edit, pending plan approval | File edits before you approve the plan, except in sessions where bypass permissions are already available | No dedicated kill switch — set as a project's `defaultMode` |
| `auto` | Everything; a background classifier reviews each action instead of a human | Explicit `ask` rules; `AskUserQuestion`; MCP tools marked `requiresUserInteraction`; org connector tools set to `ask` | Broad categories the classifier blocks by default (`curl \| bash`, prod deploys/migrations, force push, secret exfiltration, IAM/repo permission grants, and more) | `permissions.disableAutoMode: "disable"` in managed settings |
| `dontAsk` | Calls matching `permissions.allow`; the built-in read-only Bash set; calls a `PreToolUse` hook approves | Nothing — it never prompts; anything unmatched is denied outright, not queued | Explicit `ask`-rule matches; `AskUserQuestion`; `requiresUserInteraction` MCP tools; critical-path `rm`/`rmdir` | No dedicated kill switch documented — only reachable via `--permission-mode dontAsk`, not the `Shift+Tab` cycle |
| `bypassPermissions` | Everything, immediately, including protected-path writes — no classifier, no prompt | Critical-path `rm`/`rmdir` removals; explicit `ask` rules; `AskUserQuestion`/`requiresUserInteraction` tools; the `isolatePeerMachines` cross-session prompt | Entry from a `--restricted` session; starting as root/`sudo` on Linux/macOS outside a recognised sandbox | `permissions.disableBypassPermissionsMode: "disable"` in managed settings |

## §1.4.26 — `acceptEdits` in detail: the real command list, and the point of the §3.7 incident

`[DOC]` The documentation states the covered command set directly, and it is larger than "file edits
plus `mkdir`, `touch`, `mv`, `cp`":

> In addition to file edits, `acceptEdits` mode auto-approves common filesystem Bash commands: `mkdir`,
> `touch`, `rm`, `rmdir`, `mv`, `cp`, and `sed`. These commands are also auto-approved when prefixed
> with safe environment variables such as `LANG=C` or `NO_COLOR=1`, or process wrappers such as
> `timeout`, `nice`, or `nohup`. Like file edits, auto-approval applies only to paths inside your
> working directory or `additionalDirectories`. Paths outside that scope, writes to protected paths,
> `rm` and `rmdir` removals targeting a critical path, and all other Bash commands except the built-in
> read-only set still prompt.

— *Choose a permission mode*, re-verified 2026-08-29.

`mkdir`, `touch`, `mv`, `cp` (the syllabus's four) are a subset of the real list — `rm`, `rmdir`, and
`sed` are also auto-approved, subject to the same scope and the same critical-path exception described
in file 04's `Cd` section and revisited below. The scope test is identical for every command in the
list: the target path must resolve inside the working directory or a directory named in
`additionalDirectories`; a command whose target resolves outside that scope still prompts even though
the command name itself is on the auto-approved list.

Enabling `acceptEdits` for a session that also has the PowerShell tool turned on:

```json
{
  "permissions": {
    "defaultMode": "acceptEdits"
  }
}
```

With that file loaded, `mkdir build`, `touch NOTES.md`, `mv src/A.java src/B.java`, and `cp config.yaml
config.yaml.bak` all run with no prompt when the working directory is the project root. `sed -i
's/8080/9090/' application.yml` in that same directory also runs unprompted — the reader who only
memorised the syllabus's four names would expect a prompt here and be surprised when none appears.

**What `acceptEdits` does not cover is the point of the §3.7 incident.** The auto-approved list is
*exactly* the seven filesystem commands quoted above, plus ordinary `Edit`/`Write` tool calls — nothing
else. `mvn test`, `./gradlew build`, `git commit`, `chmod +x deploy.sh`, and running `java -jar
app.jar` are every one of them **outside** the `acceptEdits` list: none of them is a filesystem-scoped
command from that set, so all four still hit the ordinary Bash prompt (or the ordinary `ask`/`deny`
rule evaluation) exactly as if the mode were `default`. A team that treats `acceptEdits` as "trust
whatever the build needs" discovers the gap the first time a build step prompts mid-session anyway.
The full incident this gap produced — a compile step that ran under a different resolved settings
scope than the engineer assumed — is walked start to finish in
[`setting-sources-incident/03-internals-root-cause.md`](../setting-sources-incident/03-internals-a-the-failure.md);
this file only names the shape of the gap that made the incident possible, not the incident itself.

**Gotcha:** `acceptEdits` auto-approval is command-name-plus-scope, not "anything that touches the
filesystem." A command that both edits a file and does something else — a build script that writes
build artifacts *and* runs a compiler — is not partially approved; the whole Bash call is evaluated
under the ordinary rule (does this specific command string match an `allow`/`ask`/`deny` rule, does it
fall in the built-in read-only set), and being "mostly a filesystem operation" does not change that.

## §1.4.27 — `auto` mode: a classifier reviews instead of you

`[ZERO]` A **classifier**, in this context, is a second model invocation Claude Code makes on your
behalf — not the model you are talking to, and not a rule lookup — that is asked to judge one pending
action and answer allow or block. It is a judgment call from a model, not a deterministic check.

`[DOC]` `[VERSION]` Re-verified against `https://code.claude.com/docs/en/permission-modes`,
2026-08-29:

> Auto mode lets Claude execute without routine permission prompts. A separate classifier model
> reviews actions before they run, blocking anything that escalates beyond your request, targets
> unrecognized infrastructure, or appears driven by hostile content Claude read.

— *Choose a permission mode*, re-verified 2026-08-29.

The classifier runs on **Claude Sonnet 5 by default**, not on whatever model `/model` has selected for
the session — a server-side classifier model configured by Anthropic takes precedence over that
default, and the session's own model is used instead when the session runs on Sonnet 4.6, or when
`availableModels` excludes Sonnet 5 (falling back to Opus when the session runs on Fable 5). This
matters for the cost model: on Enterprise plans and API-key accounts, **classifier calls count toward
token usage** — each check sends a slice of the transcript plus the pending action, adding a round
trip before the action executes. Reads and in-scope working-directory edits skip the classifier
entirely, so the overhead is concentrated on shell commands and network calls, not on the bulk of an
editing session.

`[NUM]` Two fixed thresholds govern how long auto mode tolerates being blocked before it gives up and
falls back to prompting: **3 consecutive classifier blocks, or 20 total blocks in the session**,
whichever comes first. These numbers are not configurable. Any allowed action resets the consecutive
counter; the total counter persists for the rest of the session.

Two settings keys shape what the classifier itself sees and does, both scoped to **user or managed**
settings, never a project file:

- `autoMode` — the object an administrator uses to layer custom allow/deny rules onto the classifier's
  judgment, on top of the fixed rule lists documented on the page.
- `autoMode.classifyAllShell` — forces **every** shell command through the classifier, even one a
  narrow `allow` rule already matches. Without it, a rule like `Bash(npm test)` still short-circuits
  straight to "run," bypassing the classifier for that one command.

```json
{
  "autoMode": {
    "classifyAllShell": true
  }
}
```

`disableAutoMode` removes `auto` from the mode cycle outright; see §1.4.29 below for why that key
belongs in managed settings rather than here.

**Insight:** a classifier is not a deny rule. A `deny` rule is deterministic — the same specifier
either matches a call or it doesn't, every single time, with no model involved in deciding. The
classifier is itself a language model making a judgment call on a natural-language description of an
action; it can be wrong in either direction, and the documentation says so directly with a warning that
auto mode "reduces permission prompts but does not guarantee safety." Choosing `auto` over hand-written
`allow`/`deny` rules trades a guarantee for convenience — appropriate when the residual risk is
tolerable and the rule surface would otherwise be enormous, wrong when the action needs a guarantee
rather than a probably-correct judgment.

**Interview:** "What's the difference between an auto-mode allow and a `permissions.allow` rule?" — a
rule is evaluated deterministically and, once it matches, is not itself capable of being fooled by
phrasing; a classifier verdict is a model's judgment on the described action and is explicitly
documented as *not* a safety guarantee, which is why a `deny` rule still blocks in every mode
including `auto`, but nothing analogous exists to force a classifier decision.

## §1.4.28 — `bypassPermissions`: not "it turns off permissions"

`[DOC]` `[TRAP]` Re-verified against `https://code.claude.com/docs/en/permission-modes`, 2026-08-29:

> `bypassPermissions` mode disables permission prompts and safety checks so tool calls execute
> immediately, including writes to protected paths.

— *Choose a permission mode*, re-verified 2026-08-29.

That last clause is a correction the reader needs to sit with, because it runs counter to what an
older or half-remembered version of this topic states. **On the currently documented behaviour,
`bypassPermissions` does *allow* writes to protected paths** — `.git`, `.claude`, `.vscode`, `.idea`,
and the rest of the protected-directory list are explicitly listed as **Allowed**, not refused, in
`bypassPermissions` mode's row of the protected-paths table. A syllabus or a study note claiming this
mode "still refuses `.git` and `.claude`" is describing a version-stale or simply incorrect model of
the current mode, and this file corrects it here rather than repeating it: **do not carry forward "it
still protects `.git`" as a fact about `bypassPermissions`.**

What `bypassPermissions` actually still refuses, per the same page, falls into four groups:

1. **Critical-path deletions.** An `rm` or `rmdir` targeting the filesystem root, a top-level directory
   such as `/usr` or `/etc`, the home directory, a Windows drive root, or the working directory and its
   parents still **prompts for approval** even in `bypassPermissions` — the one place this mode does
   not skip a check, because the circuit breaker exists specifically to guard against a model mistake
   rather than against an untrusted human action.
2. **Actions no mode auto-approves, at all** — explicit `ask`-rule matches, the built-in
   `AskUserQuestion` tool, MCP tools marked `requiresUserInteraction`, and org connector tools an
   administrator set to `ask`. `bypassPermissions` is a mode, and these are documented as exceptions to
   every mode, not just this one.
3. **Two cross-session messaging safeguards**, named explicitly as surviving this mode:

   > Two cross-session messaging safeguards still apply in this mode... The `isolatePeerMachines`
   > approval prompt for messages to your sessions beyond this machine still appears. When no
   > `crossSessionInbound` value applies, Claude Code holds an inbound message from another of your
   > sessions for your approval, and delivers without asking only when the sending session identifies
   > itself as also bypassing permission prompts.

   — *Choose a permission mode*, re-verified 2026-08-29.

4. **Entry itself, in two cases** — a session started with `--restricted` refuses `bypassPermissions`
   outright, and on Linux/macOS the mode refuses to start under `root`/`sudo` (outside a recognised
   sandbox) with the literal message `--dangerously-skip-permissions cannot be used with root/sudo
   privileges for security reasons`.

Everything else — file writes anywhere, protected-path writes, arbitrary shell commands, network
access — runs immediately, with no classifier, no prompt, and no deny-rule-style guarantee beyond the
four exceptions above (an explicit `deny` rule in settings still blocks its match even here, since
"deny rules block in every mode, including `bypassPermissions`" is a separate, orthogonal fact about
rules rather than about the mode).

`[DOC]` The documentation states directly why this mode is defensible **only in a container or a
VM**:

> Only use this mode in isolated environments like containers, VMs, or dev containers without internet
> access, where Claude Code cannot damage your host system.
>
> `bypassPermissions` offers no protection against prompt injection or unintended actions. For
> background safety checks with far fewer permission prompts, use auto mode instead.

— *Choose a permission mode*, re-verified 2026-08-29.

**Pitfall:** the wrong belief is "`bypassPermissions` turns off permissions, so nothing bad can happen
beyond what I'd approve myself anyway — it still keeps the important guardrails like protecting `.git`
and `.claude`." The symptom, on the currently documented behaviour, is the opposite of reassuring: a
prompt-injected instruction encountered mid-session (a hostile string in a fetched web page, a file the
agent reads) can rewrite `.claude/settings.json`, corrupt `.git`'s internals, or edit any other
protected path with no prompt and no classifier standing in the way, because those specific writes are
explicitly **allowed** in this mode. The fix is the mental model this section states plainly: treat
`bypassPermissions` as "no permission system at all, on a machine you are willing to lose" — the only
guardrails left standing are the critical-path deletion prompt, the small set of always-refused
interactive tools, and the two cross-session messaging safeguards, and none of those defends against a
hostile instruction quietly rewriting a config file. **Why people believe it:** a *different* protected
path, `.git`, is prompted for even in the much weaker `default` and `acceptEdits` modes, so it reads as
a universal floor every mode respects; it is not, once you are in the one mode designed to disable
exactly those floors.

## §1.4.29 — the kill switches, and why they live in managed settings

`[DOC]` Three settings keys govern the mode surface itself rather than any one mode's behaviour, and
the documentation states the scope for each:

> `permissions.defaultMode` — Set the permission mode new sessions start in. Scope: Any file (User,
> Project, Local, or Managed).
>
> `disableAutoMode` — Remove auto mode from the permission mode cycle. Scope: Any file.
>
> `disableBypassPermissionsMode` — Prevent anyone from entering `bypassPermissions` mode. Scope: Any
> file.

— *Settings reference*, `https://code.claude.com/docs/en/settings-reference`, re-verified 2026-08-29.

Although the reference table above marks all three as settable from "any file," the mode-specific
pages state the operative constraint directly for the two kill switches: an administrator "can turn it
off for the organization by setting `permissions.disableAutoMode` to `"disable"` in managed settings,"
and "administrators can block this mode by setting `permissions.disableBypassPermissionsMode` to
`"disable"` in managed settings." A project's own `.claude/settings.json` *can* technically hold either
key, but only a value reaching the session from **managed settings** carries the guarantee the key
exists to provide.

```json
{
  "permissions": {
    "disableAutoMode": "disable",
    "disableBypassPermissionsMode": "disable"
  }
}
```

**Why these belong in managed settings, not a project file.** Files 01–02 already established the
settings-precedence chain this topic relies on: **managed outranks the command line, which outranks
project-local and shared-project settings, which outrank the user's own `~/.claude/settings.json`.**
That order is exactly why these two keys have to live at the managed layer to do their job. A key
placed in `.claude/settings.json` is a *default* — a starting point any engineer can override with
`--permission-mode bypassPermissions` on the command line for one run, and a default in a *shared*
project file competes on equal footing with whatever any other reachable settings file says. A key
placed in **managed** settings is not competing at that level at all: because managed settings
outrank the command-line flag itself, `permissions.disableBypassPermissionsMode: "disable"` set there
cannot be reopened by any `--permission-mode bypassPermissions` an engineer types, by any project
`defaultMode`, or by any personal `~/.claude/settings.json` — there is no flag or file below managed
settings capable of contesting it. This is the concrete, worked instance of "managed cannot be flagged
away" that file 01 introduced in the abstract: here, the abstract precedence claim cashes out as one
administrator being able to guarantee, org-wide, that nobody's terminal session — however that
engineer configures their own machine — can ever reach `bypassPermissions` at all.

`permissions.defaultMode`, by contrast, is a genuine default rather than a hard floor: it sets what a
session starts in, but the ordinary resolution order (`--permission-mode` flag, then
`permissions.defaultMode` from the first settings file that sets it, then the built-in default) still
lets a command-line flag override it for one run. It belongs at whatever scope wants to state its
preference; the two `disable*` keys belong specifically at the managed scope because a preference is
not what they are for.

## Pitfalls

- **Belief:** "There are four permission modes." **Outcome:** the reader has no name for `auto` — the
  built-in starting mode on Pro, Max, and Team plans as of this target version — or for `dontAsk`, and
  is caught flat-footed by a session that starts in `auto` with no `Shift+Tab` history to explain why.
  **Fix:** the answer is six — `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`,
  `bypassPermissions` — and naming only four is itself the fact worth stating in an interview, since it
  flags the candidate's information as stale. **Why people believe it:** older guides, blog posts, and
  a genuinely earlier version of Claude Code shipped only the first four modes; `auto` and `dontAsk`
  were added later and the four-mode form is still what most search results describe.
- **Belief:** "`acceptEdits` covers `mkdir`, `touch`, `mv`, `cp` — and any build or VCS command needed
  to keep iterating." **Outcome:** `mvn test`, `git commit`, `chmod`, and running the built jar all
  still hit the ordinary Bash prompt mid-session, because none of them is on the documented list.
  **Fix:** the auto-approved command set is exactly `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed`
  (scoped to the working directory or `additionalDirectories`) plus file edits — nothing broader. **Why
  people believe it:** the mode's own name, "accept edits," reads as "accept whatever this coding
  session needs to do," not as a literal, fixed, seven-command allowlist.
- **Belief:** "`bypassPermissions` turns off permissions but still protects `.git` and `.claude`."
  **Outcome:** on the currently documented behaviour, writes to every protected path — including
  `.git` and `.claude` — are explicitly **allowed** in this mode; the only survivors are critical-path
  deletion prompts, a handful of always-interactive tools, and two cross-session messaging safeguards.
  **Fix:** treat `bypassPermissions` as defensible only inside a container or VM with nothing to lose,
  never as "mostly safe because the important files are still guarded." **Why people believe it:**
  `.git` is one of the paths prompted for even in the much weaker `default` and `acceptEdits` modes, so
  the protection reads as a universal floor rather than as something this one mode is specifically
  built to remove.

## Cheat sheet

| Fact | Value |
|---|---|
| Number of permission modes | Six: `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
| `default` config value, CLI label | `default` / **Manual**; `manual` alias requires v2.1.200+ |
| Built-in starting mode, Pro/Max/Team | `auto`, from v2.1.228+ (mac/Linux/WSL) / v2.1.233+ (Windows) |
| `acceptEdits` auto-approved commands | `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed` — scoped to working dir / `additionalDirectories` |
| `acceptEdits` does NOT cover | build tools, `git commit`, `chmod`, running compiled/interpreted programs |
| `auto` classifier default model | Sonnet 5, unless server override or model/`availableModels` fallback applies |
| `auto` fallback thresholds | 3 consecutive blocks or 20 total blocks → resumes prompting |
| `auto` disable key | `permissions.disableAutoMode: "disable"` (managed settings) |
| `autoMode.classifyAllShell` | forces every shell command through the classifier, even allow-rule matches |
| `bypassPermissions` allows | protected-path writes (`.git`, `.claude`, etc.) — immediately, no classifier |
| `bypassPermissions` still refuses | critical-path `rm`/`rmdir`; `ask` rules; `AskUserQuestion`/`requiresUserInteraction`; `isolatePeerMachines` + held inbound cross-session messages |
| `bypassPermissions` disable key | `permissions.disableBypassPermissionsMode: "disable"` (managed settings) |
| Why kill switches need managed scope | managed settings outrank the CLI flag itself — no flag or lower file can reopen a managed disable |

## Self-test

<details><summary>1. How many permission modes does Claude Code have, and name all six.</summary>
Six: `default` (labelled Manual), `acceptEdits`, `plan`, `auto`, `dontAsk`, and `bypassPermissions`. A
four-mode answer omits `auto` and `dontAsk` and describes a stale version of the mode set.
</details>

<details><summary>2. A settings file sets `"defaultMode": "acceptEdits"`. Does `git commit -m "message"` run without a prompt?</summary>
No. `acceptEdits` auto-approves exactly `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed`, and file
edits, scoped to the working directory or `additionalDirectories`. `git commit` is not on that list, so
it still hits the ordinary Bash permission check.
</details>

<details><summary>3. What reviews an action in `auto` mode instead of a human, and is that a guarantee?</summary>
A separate classifier model — Sonnet 5 by default — reviews the pending action and returns allow or
block. It is explicitly not a guarantee: the documentation states auto mode "reduces permission prompts
but does not guarantee safety," unlike a deterministic `deny` rule.
</details>

<details><summary>4. On the currently documented behaviour, does `bypassPermissions` mode still refuse a write to `.claude/settings.json`?</summary>
No. Protected-path writes, including `.git` and `.claude`, are explicitly listed as Allowed under
`bypassPermissions`. What it still refuses is narrower: critical-path deletions, explicit `ask`-rule
matches, always-interactive tools, and two cross-session messaging safeguards.
</details>

<details><summary>5. Why is `bypassPermissions` described as defensible only in a container or VM?</summary>
Because it disables essentially every permission check, including protecting the repository's own
`.git` and Claude's own `.claude` configuration, with no classifier and no prompt standing in the way of
a hostile or mistaken action — it "offers no protection against prompt injection or unintended
actions," so the only safety margin left is that the environment itself has nothing worth protecting.
</details>

<details><summary>6. Where should `permissions.disableBypassPermissionsMode` be set to guarantee no engineer in an organization can ever enable that mode, and why there specifically?</summary>
In managed settings. Because managed settings outrank the command line, a value set there cannot be
overridden by a `--permission-mode bypassPermissions` flag, a project's `defaultMode`, or any personal
`~/.claude/settings.json` — there is no lower-precedence source capable of reopening what a managed
disable closes.
</details>

<details><summary>7. What does `autoMode.classifyAllShell` change, and where can it be set?</summary>
It forces every shell command through the auto-mode classifier, even one an existing narrow `allow`
rule (such as `Bash(npm test)`) already matches outright. It is scoped to user or managed settings
only, never a project file.
</details>

<details><summary>8. A session in `bypassPermissions` mode runs `rm -rf ~`. Does it execute immediately?</summary>
No. `rm`/`rmdir` targeting a critical path — including the home directory — is one of the documented
exceptions that still prompts for approval even in `bypassPermissions`, because that check exists to
guard against a model mistake rather than to protect against the human who chose this mode.
</details>

## Open questions

None.

---

**Leaves covered:** 1.4.25–1.4.29 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-33
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 429
