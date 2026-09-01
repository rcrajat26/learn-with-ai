# 21 AI for Coding — web, MCP, Agent and Cd rules — BASICS (§1.4.20–1.4.24)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [path rules](03-path-rules.md) · Next: [the six permission modes](05-modes.md)

## The remaining specifier shapes: a domain, a server or tool name, a parameter, and a directory a human types.

File 03 covered path rules end to end — `Read`/`Edit`, their gitignore syntax, what a `Read` deny
propagates to, and the outer boundary of the whole mechanism. This file covers everything that is
**not** a path rule: a domain (`WebFetch`), an MCP server or tool name, a parameter on any built-in
tool's call (`Agent(param:value)` and friends), and `Cd`, the one rule family in this section that
does not gate the model at all. Two of these five leaves repeat a pattern file 03 already established
— a rule form that looks like a straightforward widening turns out to be a mode switch or a silent
skip instead — so the throughline from file 03 continues here even though none of these leaves touch
a file path.

## §1.4.20 — `WebFetch(domain:…)` and the allow-or-deny-every-fetch forms

`[DOC]` A `WebFetch` rule gates the tool by the hostname of the URL it is about to fetch, using a
`domain:` prefix rather than a path:

> WebFetch rules use a `domain:` prefix and match against the hostname of the requested URL. Matching
> is case-insensitive, supports `*` wildcards, and strips a trailing `.` from both the rule and the
> hostname so `example.com.` and `example.com` are treated the same.

— *Configure permissions*, `https://code.claude.com/docs/en/permissions`, re-verified 2026-08-29.

| Rule | Matches |
|---|---|
| `WebFetch(domain:example.com)` | requests to `example.com` |
| `WebFetch(domain:*.example.com)` | any subdomain at any depth (`api.example.com`, `a.b.example.com`), not `example.com` itself |
| `WebFetch(domain:*)` | every domain — but not equivalent to a bare `WebFetch` rule, see below |
| `WebFetch(domain:example.*)` | `example.org` (`*` fills one segment between dots), not `example.evil.com` (crossing a dot) |

`[NUM]` `[VERSION]` Wildcards in `WebFetch` rules require **v2.1.172 or later** to match fetches at
all — on an older binary, a `domain:*.example.com` rule is accepted but never matches anything, so
every fetch to a subdomain still prompts as if the rule were absent.

A **bare `WebFetch` rule** (the tool name, no `domain:` part) and `WebFetch(domain:*)` both cover
every URL, but they are not interchangeable — this is a second instance of the same lesson as file
03's §1.4.18, where two syntactically different rules that look like they mean the same thing are
consulted differently:

| Rule | In `allow` | In `deny` |
|---|---|---|
| `WebFetch` (bare) | fetches without prompting; does **not** change which hosts sandboxed Bash commands can reach | removes the `WebFetch` tool entirely — Claude cannot fetch at all; does not change the sandbox's allowed hosts |
| `WebFetch(domain:*)` | fetches without prompting, **and** sandboxed commands can reach any host | keeps the tool, refuses every fetch, **and** sandboxed commands cannot reach any host |

Only the `domain:` form feeds the sandbox's own allowed/denied domain list; the bare form only ever
touches the `WebFetch` tool's own prompt behaviour. A settings file that wants Claude to fetch freely
through the `WebFetch` tool while leaving the sandbox's network allowlist completely untouched writes
the bare form:

```json
{
  "permissions": {
    "allow": ["WebFetch"]
  }
}
```

With this settings object, asking Claude to fetch a page succeeds with no prompt. Asking it to run a
sandboxed `curl` against a host outside the sandbox allowlist still prompts for that host (or, in auto
mode, still reaches the classifier), because the bare rule never added the host to the allowlist in
the first place — the bare form and the sandbox's network boundary are two completely independent
gates that happen to share the same tool name in their rule text.

**Insight:** this is the same "tool name vs. scoped specifier" split as file 03's `Write` vs. `Edit`
confusion, transplanted onto `WebFetch` — the rule that looks maximally permissive (`domain:*`) is
actually **more** consequential than the bare tool name, because it is the one that also widens the
sandbox's network boundary, not just the permission prompt. A reader who reads `WebFetch(domain:*)`
as "the wildcard version of the bare rule, nothing more" under-estimates exactly what it opens up on a
sandboxed session.

## §1.4.21 — the three MCP rule forms, and the parenthesised form that is silently skipped

`[ZERO]` **MCP** (Model Context Protocol) is the protocol Claude Code uses to talk to external tool
servers — a running process that exposes a set of named tools the model can call, the same way the
model calls a built-in tool like `Bash` or `Read`. An MCP tool's canonical name is always
`mcp__<server>__<tool>`.

`[DOC]` The documentation states the three rule forms directly:

> MCP rules use the server name as configured in Claude Code, optionally followed by the name of a
> tool from that server.

— *Configure permissions*, re-verified 2026-08-29.

| Form | Matches |
|---|---|
| `mcp__server` | any tool provided by that server, e.g. `mcp__puppeteer` matches every `puppeteer` tool |
| `mcp__server__*` | the same thing, spelled with an explicit wildcard, e.g. `mcp__puppeteer__*` |
| `mcp__server__tool` | one named tool from that server, e.g. `mcp__puppeteer__puppeteer_navigate` |

`[DOC]` `[TRAP]` A fourth-looking form — an MCP rule with a **parenthesised parameter**, the way
`Bash(rm *)` or `Agent(model:opus)` carry a parenthesised argument — is not one of the three forms
above, and it does not do what its shape suggests:

> To match a parameter on an MCP tool, pass a deny rule with `--disallowedTools`. When Claude Code
> loads a settings file, it skips any `mcp__` rule that has parentheses. Claude Code lists the
> skipped rule in the invalid-settings dialog when an interactive session starts, and in
> `claude doctor` output.

— *Configure permissions*, re-verified 2026-08-29.

So a settings file containing `"deny": ["mcp__github__create_issue(repo:internal-secrets)"]` — an
author's attempt to deny the tool only when it targets one specific repository — is **not** a
recognised MCP rule shape at all. It parses as JSON, Claude Code loads the settings file successfully,
and then skips that one entry outright at load time, surfacing it only in the invalid-settings dialog
shown on interactive startup and in `claude doctor` output, neither of which a headless `claude -p` run
in CI ever displays. The parameter-matching path that actually works for an MCP tool is the CLI flag
named in the quote:

```
claude --disallowedTools "mcp__github__create_issue(repo:internal-secrets)"
```

**Pitfall:** the wrong belief is "MCP tools support the same `Tool(param:value)` parenthesised
parameter syntax as `Agent` and `Bash` do, written straight into `settings.json`." The symptom is the
rule silently never taking effect — no error at write time, no crash, just a skipped entry that only
surfaces in a dialog or a debug command most sessions never run, and in a CI pipeline running headless
`claude -p`, nothing at all. The fix is: **parameter matching on an MCP tool is a `--disallowedTools`
CLI flag, never a parenthesised rule inside a settings file.** The three settings-file forms
(`mcp__server`, `mcp__server__*`, `mcp__server__tool`) never take a parenthesised parameter argument,
under any circumstance. **Why people believe it:** `Agent(model:opus)` and
`Bash(run_in_background:true)` in §1.4.23 below use exactly this parenthesised shape and work
perfectly fine written directly into a settings file, so the shape reads as a general capability every
tool shares — it is not; MCP tools are the one documented exception, routed through a CLI flag
instead of a settings-file rule.

## §1.4.22 — `Agent(Name)` rules, including the built-ins

`[ZERO]` An **agent** (subagent) is a separate Claude invocation with its own tool access and
instructions, dispatched by the primary session to handle one bounded piece of work and report back a
result — distinct from the primary conversation the user talks to directly.

`[DOC]` `Agent(AgentName)` rules gate which subagents are permitted to run at all:

> Use `Agent(AgentName)` rules to control which subagents Claude can use.

— *Configure permissions*, re-verified 2026-08-29.

Three names an `Agent(...)` rule can gate are **built into Claude Code**, not project-defined:

| Built-in agent | What it does |
|---|---|
| `Agent(Explore)` | a fast, read-only agent optimised for searching and analysing codebases |
| `Agent(Plan)` | a research agent used during plan mode to gather context before presenting a plan |
| `Agent(fork)` | a subagent that inherits the entire conversation so far, rather than starting fresh |

— *Sub-agents*, `https://code.claude.com/docs/en/sub-agents`, re-verified 2026-08-29.

A rule can equally name a custom subagent, e.g. `Agent(readonly-reviewer)`, defined in a project's
`.claude/agents/` folder rather than built into the binary. To disable the built-in `Explore` agent
entirely:

```json
{
  "permissions": {
    "deny": ["Agent(Explore)"]
  }
}
```

The same gate is available at the CLI without editing a settings file, via
`--disallowedTools "Agent(Explore)"`.

**Gotcha:** denying `Agent(Explore)` does not remove the *capability* it provides — the primary
session can still read files and grep directly with its own `Read` and `Grep` tools. It removes only
the option of delegating that work to the specialised subagent, which matters for cost and context
isolation (a fork or a dedicated Explore call keeps large search results out of the primary
conversation's own context) but not for whether the underlying files can be read at all.

## §1.4.23 — parameter matching for deny/ask on any built-in tool

`[DOC]` `Tool(param:value)` is a distinct specifier shape from a path or a Bash command string: it
matches a **named input parameter** on any built-in tool's call, for `deny` and `ask` rules only.

> Deny and ask rules can match a top-level input parameter on any built-in tool with
> `Tool(param:value)`.

— *Configure permissions*, re-verified 2026-08-29.

| Rule | Matches |
|---|---|
| `Agent(model:opus)` | Agent calls that request the Opus model tier |
| `Agent(isolation:worktree)` | Agent calls that request a git worktree |
| `Bash(run_in_background:true)` | Bash calls that run in the background |

Four constraints govern every parameter rule, all stated in the documentation:

- **One parameter per rule.** To gate on both `model` and `isolation`, write two separate rules —
  `Agent(model:opus)` and `Agent(isolation:worktree)` — never combined into a single specifier such
  as `Agent(model:opus,isolation:worktree)`, which is not a recognised form at all.
- **Direct fields only.** "The parameter name must be a direct field of the tool's input... fields
  nested inside an object or array are not matchable." A parameter buried inside a nested object on a
  tool's call cannot be targeted this way under any circumstance, no matter how the dotted path is
  written.
- **`*` wildcard supported.** The value accepts `*` as a wildcard matching any sequence of
  characters — `Agent(isolation:*)` matches any *explicit* isolation value, but "a parameter the
  model omits is never matched, so `Agent(model:*)` doesn't match a call that leaves `model` unset."
- **Compared before normalisation.** "The value is compared against the literal input Claude sends,
  before any normalization. `Agent(model:opus)` matches the alias `opus` but not a full model ID."

— *Configure permissions*, re-verified 2026-08-29.

That last constraint has a direct, spelled-out consequence. If the model happens to emit the
fully-qualified model identifier for Opus — a concrete model ID string, rather than the short alias
`opus` — a rule written as `Agent(model:opus)` does **not** match that call. Concretely: suppose an
author writes `"deny": ["Agent(model:opus)"]` believing it blocks every subagent call that uses Opus,
for cost-control reasons. A call that Claude emits with `model: "opus"` is matched and blocked, exactly
as intended. A call that Claude instead emits with the resolved model ID (the fully-qualified
identifier string rather than the short alias) is checked against the same rule text and **does not
match**, because the comparison happens against the literal string on the wire before any alias is
expanded or any ID is normalised to a canonical form — the deny rule silently lets that call through,
with no warning that it only ever covered one of the two spellings the same model tier can arrive as.
`--verbose` is the documented way to see the exact parameter names and values in each tool call, and it
is the only reliable way to confirm which literal string a rule needs to match before writing it,
rather than guessing from the tier name alone.

There is also a documented **content-field exclusion**: a tool's primary content field — `command`
for `Bash`/`PowerShell`, `file_path` for `Read`/`Edit`/`Write`, `path` for `Grep`/`Glob`,
`notebook_path` for `NotebookEdit`, `url` for `WebFetch` — cannot be matched this way at all. A rule
like `Bash(command:rm *)` is ignored with a startup warning, because a compound command could smuggle
past it; the specifier syntax for those fields is each tool's own (`Bash(rm *)`, `Read(./path)`,
`WebFetch(domain:host)`), not the `param:value` form.

**Interview:** "Why doesn't `Agent(model:opus)` block every Opus call?" — because parameter matching
compares the literal, pre-normalisation value Claude Code receives; if the call carries a resolved
model ID rather than the alias `opus`, the rule simply doesn't match that string, and `--verbose` is
how you find out which literal value is actually on the wire before writing the rule.

## §1.4.24 — `Cd` rules: not model-invocable, and the allowlist-mode flip

`[DOC]` `Cd` rules gate a **user-typed command**, never something the model can trigger on its own.

> `Cd` rules control which directories the `/cd` command can move the session to. `Cd` is not a
> model-invocable tool: Claude can't call it, and the rules apply only when you run `/cd` yourself.

— *Configure permissions*, re-verified 2026-08-29.

Four properties, all documented:

1. **Not model-invocable.** No `tool_use` block the model emits can ever be a `Cd` call — `/cd` is a
   slash command the human at the keyboard types, and `Cd` rules only ever fire against that.
2. **A bare `Cd` deny disables `/cd` entirely.** `"deny": ["Cd"]` removes the ability to move the
   session's primary working directory at all, for the rest of the session — there is no narrower
   form of this deny, since `Cd` with no specifier already means "every target."
3. **Any allow rule switches `/cd` to allowlist mode.** "Adding any `Cd` allow rule switches `/cd` to
   allowlist mode: the resolved target directory must match one of your allow rules, or `/cd`
   refuses. With no `Cd` rules configured, `/cd` keeps its default behavior and prompts you to trust
   an unfamiliar directory." This is the surprising one — writing a single narrow `Cd` allow rule to
   permit one extra directory does not merely *add* that directory to whatever was reachable before;
   it **replaces** "prompt to trust anywhere" with "only these directories, ever," silently narrowing
   every other target that used to be reachable via the trust prompt.
4. **`*` is one segment, `**` spans segments.** Path patterns share the `//`, `~/`, and `/` anchors
   from Read and Edit rules, but matching is anchored to the whole directory path rather than
   gitignore-style. `*` matches exactly one path segment and `**` matches across segments. A trailing
   `/**` also matches its named root.

— *Configure permissions*, re-verified 2026-08-29.

| Rule | Matches | Does not match |
|---|---|---|
| `Cd(~/code/*)` | `~/code/app` | `~/code/app/src`, `~/code` |
| `Cd(~/code/**)` | `~/code` and any directory under it | directories outside `~/code` |
| `Cd(**/node_modules)` | any `node_modules` directory at any depth | `node_modules/pkg` |

Worked example of the allowlist-mode flip. A settings file starts with no `Cd` rules at all, so `/cd`
into any directory — `~/code/app`, `/tmp/scratch`, a colleague's checkout — works the ordinary way:
Claude Code prompts to trust the folder the first time, then moves the session there. An engineer adds
exactly one rule, intending only to skip the trust prompt for their own projects folder:

```json
{
  "permissions": {
    "allow": [
      "Cd(~/code/**)"
    ]
  }
}
```

From the moment this rule is loaded, `/cd /tmp/scratch` and `/cd ~/some-colleagues-checkout` both
**refuse outright**, with no trust prompt offered at all — not because either target is denied, but
because the single `allow` entry switched `/cd` into allowlist mode, and neither target matches
`~/code/**`. The only way to restore access to `/tmp/scratch` is to add a second allow rule naming it
explicitly; there is no way back to "prompt for anything not covered" once any `Cd` allow rule exists.

**Pitfall:** the wrong belief is "I added `Cd(~/code/**)` to allow, so I can still `/cd` anywhere I
could before, plus that directory." The symptom is every other previously-reachable directory now
refusing `/cd` outright, with the trust-prompt fallback gone entirely. The fix is to treat the first
`Cd` allow rule as a hard mode switch: once written, every directory the session will ever need to
`/cd` into must have its own allow rule, or `/cd` refuses. **Why people believe it:** `permissions.allow`
for every other tool family covered in this file and in file 03 — Bash, Read/Edit, WebFetch, MCP,
Agent — is purely additive, so `Cd` reads as an outlier only once the mode switch has already
surprised someone in a live session.

## Pitfalls

- **Belief:** "MCP tools take the same `Tool(param:value)` parenthesised parameter rule as `Agent`
  and `Bash`, written straight into settings.json." **Outcome:** Claude Code skips any `mcp__` rule
  that has parentheses at load time, silently, surfacing only in the invalid-settings dialog and
  `claude doctor` — neither shown in a headless `claude -p` run. **Fix:** use `--disallowedTools` for
  MCP parameter matching; settings-file MCP rules are only ever `mcp__server`, `mcp__server__*`, or
  `mcp__server__tool`, with no parenthesised argument. **Why people believe it:** the parenthesised
  parameter shape works for other built-in tools on the very next section of the same documentation
  page, so it reads as a universal mechanism rather than a documented exception.
- **Belief:** "`Agent(model:opus)` in deny blocks every subagent call that uses the Opus model."
  **Outcome:** a call carrying the resolved model ID rather than the short alias `opus` is compared
  against the same rule text and does not match, because parameter matching compares the literal
  pre-normalisation value. **Fix:** confirm the exact literal value with `--verbose` before writing
  the rule, rather than assuming the tier name alone is what gets matched. **Why people believe it:**
  "opus" reads as the name of the model tier itself, not as one specific spelling among several the
  same tier can arrive as on the wire.
- **Belief:** "Adding one `Cd` allow rule just opens up an extra directory, on top of the normal
  trust-prompt behaviour I already had." **Outcome:** the first `Cd` allow rule switches `/cd` into
  allowlist mode outright — every directory not covered by an allow rule now refuses `/cd`, with the
  trust-prompt fallback gone. **Fix:** once one `Cd` allow rule exists, write one for every directory
  the session will ever need to `/cd` into. **Why people believe it:** `allow` is purely additive for
  every other permission family in this guide — Bash, Read/Edit, WebFetch, MCP, Agent — so `Cd` reads
  as an outlier only after the mode switch has already surprised someone.

## Cheat sheet

| Fact | Value |
|---|---|
| `WebFetch(domain:example.com)` | matches that hostname |
| `WebFetch` bare vs `WebFetch(domain:*)` | bare: tool-level prompt only, no sandbox effect; `domain:*`: also widens/narrows sandbox host list |
| Wildcards in WebFetch rules require | v2.1.172+ |
| MCP rule forms | `mcp__server`, `mcp__server__*`, `mcp__server__tool` |
| Parenthesised `mcp__` rule in settings | silently skipped at load — use `--disallowedTools` for MCP parameter matching |
| `Agent(Name)` built-ins | `Agent(Explore)`, `Agent(Plan)`, `Agent(fork)` |
| `Tool(param:value)` constraints | one parameter per rule; direct top-level fields only; `*` wildcard; compared before normalisation |
| Content fields excluded from param matching | `command`, `file_path`, `path`, `notebook_path`, `url` |
| `Cd` model-invocable? | No — user-typed `/cd` only |
| Bare `Cd` deny | disables `/cd` entirely |
| Any `Cd` allow rule | switches `/cd` to allowlist mode |
| `Cd` wildcard segments | `*` = one segment, `**` spans segments |

## Self-test

<details><summary>1. What is the difference between a bare `WebFetch` deny rule and `WebFetch(domain:*)` in deny?</summary>
A bare `WebFetch` deny removes the tool from Claude's context entirely and has no effect on which
hosts sandboxed Bash commands can reach. `WebFetch(domain:*)` in deny keeps the tool present but
refuses every fetch, and additionally removes every host from the sandbox's allowed-domain list for
sandboxed commands — it is the more consequential of the two despite looking like a simple wildcard
of the bare form.
</details>

<details><summary>2. `allow` contains only `"WebFetch"` (bare). Does a sandboxed `curl` to a host outside the sandbox allowlist run without a prompt?</summary>
No. The bare `WebFetch` allow rule only affects the `WebFetch` tool's own prompt behaviour; it does
not add any host to the sandbox's allowed-domain list. A sandboxed `curl` to an unlisted host still
prompts (or reaches the auto-mode classifier) exactly as if the rule were absent.
</details>

<details><summary>3. A settings file contains `"deny": ["mcp__github__create_issue(repo:internal-secrets)"]`. What happens when Claude Code loads it?</summary>
The rule is skipped entirely at load time, because it is an MCP rule with parentheses — settings-file
MCP rules only ever take the forms `mcp__server`, `mcp__server__*`, or `mcp__server__tool`. The skip
is silent except for an entry in the invalid-settings dialog on interactive startup and in
`claude doctor` output; a headless `claude -p` run shows neither. Parameter matching on an MCP tool
requires `--disallowedTools` instead.
</details>

<details><summary>4. Name the three built-in `Agent(Name)` rule targets and what each one is.</summary>
`Agent(Explore)` — a fast, read-only agent for searching and analysing codebases. `Agent(Plan)` — a
research agent used during plan mode to gather context before presenting a plan. `Agent(fork)` — a
subagent that inherits the entire conversation so far instead of starting fresh.
</details>

<details><summary>5. Does denying `Agent(Explore)` stop the primary session from reading files and searching the codebase?</summary>
No. It removes only the option of delegating that work to the specialised `Explore` subagent — the
primary session can still call its own `Read` and `Grep` tools directly. It affects cost and context
isolation, not whether the underlying files can be read.
</details>

<details><summary>6. Why doesn't `Agent(model:opus)` in deny reliably block every call that uses the Opus model?</summary>
Parameter matching compares the literal value Claude sends before any normalisation. `Agent(model:opus)`
matches the short alias `opus` but not a call that carries the fully-qualified model ID instead — if
the call sends the resolved ID rather than the alias, the rule simply does not match, and `--verbose`
is the way to see which literal string is actually being sent.
</details>

<details><summary>7. Can `Bash(command:rm *)` be written to gate the Bash tool's `command` parameter directly?</summary>
No. A tool's primary content field — `command` for Bash/PowerShell, `file_path` for Read/Edit/Write,
`path` for Grep/Glob, `notebook_path` for NotebookEdit, `url` for WebFetch — is excluded from
parameter matching, because a compound command could smuggle past a naive match on `command`. Claude
Code ignores such a rule with a startup warning; use the tool's own specifier syntax, `Bash(rm *)`,
instead.
</details>

<details><summary>8. A settings file has no `Cd` rules at all. An author adds `Cd(~/code/**)` to `allow`, intending only to add that directory to what `/cd` can already reach. What actually happens to `/cd /tmp/scratch`?</summary>
Adding any `Cd` allow rule switches `/cd` from its default trust-prompt behaviour into allowlist
mode: the resolved target directory must now match an allow rule or `/cd` refuses outright. `/tmp/scratch`
does not match `~/code/**`, so `/cd /tmp/scratch` refuses with no trust prompt offered at all, even
though it was reachable before the rule was added.
</details>

<details><summary>9. Can `Cd` rules ever be triggered by something Claude itself decides to do mid-turn?</summary>
No. `Cd` is explicitly not a model-invocable tool — Claude cannot call it under any circumstance. The
rules apply only when the human at the keyboard runs `/cd` themselves.
</details>

## Open questions

None.

---

**Leaves covered:** 1.4.20–1.4.24 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 414
