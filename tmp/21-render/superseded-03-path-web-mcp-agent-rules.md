# 21 AI for Coding — path, web, MCP and Agent rules — BASICS (§1.4.16–1.4.24)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [Bash matching](02-bash-matching.md) · Next: [the six permission modes](04-modes.md)

## Files 01 and 02 covered Bash. This file covers everything else a path or a name can gate.

Files 01–02 covered the `deny → ask → allow` pipeline and the Bash transformation pipeline. Bash is
one tool among many a permission rule can name. This file covers the rest: a **filesystem path**
(`Read`, `Edit`), a **domain** (`WebFetch`), an **MCP server or tool name**, an **agent or
built-in-tool parameter** (`Agent`, and parameter matching generally), and `Cd`, which is not
model-invocable at all. The throughline is the lesson §1.4.18 exists to teach: a permission rule is
only as real as the tool name Claude Code actually consults it against, and several tool names that
look like the right place to write a path rule are silently decorative.

## §1.4.16 — `Read`/`Edit` path syntax: gitignore patterns, four anchors

`[ZERO]` A **path rule** is a permission specifier whose parenthesised argument names a file or
directory instead of a command — `Read(./.env)` rather than `Bash(npm test)`. **Gitignore pattern
syntax** is the matching language `.gitignore` files use: a bare name matches at any depth, `*`
matches within one path segment, `**` matches across any number of segments, and a trailing `/**`
matches the directory itself and everything under it. Claude Code reuses this exact syntax for `Read`
and `Edit` rules rather than inventing its own.

`[DOC]` The official documentation states the anchor forms directly:

> Read and Edit rules both use gitignore pattern syntax with four distinct pattern types.

| Pattern | Meaning | Example | Matches |
|---|---|---|---|
| `//path` | Absolute path from filesystem root | `Read(//Users/alice/secrets/**)` | `/Users/alice/secrets/**` |
| `~/path` | Path from home directory | `Read(~/Documents/*.pdf)` | `/Users/alice/Documents/*.pdf` |
| `/path` | Path relative to the settings source | `Edit(/src/**/*.ts)` | `<primary working directory>/src/**/*.ts` in project settings |
| `path` or `./path` | Path relative to current directory | `Read(*.env)` | `<cwd>/*.env` |

— *Configure permissions*, `https://code.claude.com/docs/en/permissions`, re-verified 2026-08-29.

A worked example for each anchor, against a session whose primary working directory is
`/Users/alice/sdlc-harness`:

- **`//abs`** — `Read(//Users/alice/.ssh/id_rsa)` denies exactly one absolute path, regardless of the
  launch directory or which settings file holds the rule — the only anchor that means the same thing
  everywhere.
- **`~/`** — `Read(~/.aws/credentials)` denies the current user's AWS credentials file no matter what
  project is open. Written in user settings, this is how to block a secret file across every project
  at once — a bare `/` or relative rule in user settings would instead resolve against `~/.claude/`.
- **`/`** — `Edit(/src/**/*.ts)` written in `.claude/settings.json` at the project root resolves to
  `<primary working directory>/src/**/*.ts`. The same literal rule in `~/.claude/settings.json`
  instead resolves to `~/.claude/src/**/*.ts` — a directory that almost certainly does not exist —
  because a `/`-anchored rule resolves against **the settings file that defines it**, not the project
  the session happens to be in.
- **bare / `./`** — `Read(./.env)` and `Read(./secrets/**)` are the documentation's own paste-ready
  examples for excluding sensitive files: `Read(./.env)` denies `<cwd>/.env`, and
  `Read(./secrets/**)` denies the `<cwd>/secrets/` directory and everything under it.

Bare filenames follow gitignore depth semantics — `Read(.env)` and `Read(**/.env)` are equivalent,
blocking any `.env` at or under the current directory but not a parent or sibling project. A
single-segment directory pattern like `Read(secrets/**)` additionally matches `secrets` **at any
depth** for `deny`/`ask`, but only the top-level `<cwd>/secrets` for `allow` — deliberate, so a deny
can't be dodged by nesting the directory elsewhere, and an allow can't accidentally widen to a copy
three levels deep.

**Insight:** the four anchors resolve against different roots, so identical pattern text produces
different denied paths depending only on the prefix. Writing `/secrets/**` in user settings meaning
"every project's secrets," when it resolves to `~/.claude/secrets/**`, is a silent no-op, not an error.

## §1.4.17 — a `Read` deny also blocks `Edit` and `Write`, but not `NotebookEdit`

`[DOC]` `[VERSION]` The documentation states the coverage and the version gate together:

> A `Read` deny rule also blocks the Edit and Write tools on the same path, including creating a new
> file there. NotebookEdit isn't covered, so add an `Edit` deny rule for paths no tool may change.
> The check requires Claude Code v2.1.208 or later on edits, and v2.1.228 or later on writes.

— *Configure permissions*, re-verified 2026-08-29.

**On Claude Code v2.1.2xx (the target version for this guide), both halves of that check are active** —
edits have been covered since v2.1.208 and writes since v2.1.228, both well before the current
release line. A reader on an older binary between those two version numbers would find a `Read` deny
already blocking `Edit` while a brand-new file created via `Write` at the same path still succeeded —
the version trap to carry forward if this claim is ever repeated about an older build.

Concretely:

```json
{
  "permissions": {
    "deny": [
      "Read(./secrets/**)"
    ]
  }
}
```

With only this rule, on v2.1.2xx: `Read`, `Edit`, and `Write` on a file under `secrets/` are all
blocked — but `NotebookEdit` on a `.ipynb` under `secrets/` **succeeds**, since `NotebookEdit` is not
one of the tools a `Read` deny propagates to. The fix is a second, explicit rule:

```json
{
  "permissions": {
    "deny": [
      "Read(./secrets/**)",
      "Edit(./secrets/**)"
    ]
  }
}
```

Adding the `Edit` deny does not close the `NotebookEdit` gap on its own — see §1.4.18: `Edit(path)`
is one of only two rule forms ever consulted for file permissions, and a `NotebookEdit(...)` path rule
is never consulted regardless of how it is written. There is no rule that blocks notebook edits by
path; the only lever is a bare tool-name deny, `"deny": ["NotebookEdit"]`, which removes the tool from
Claude's context entirely rather than scoping it to one path.

**Pitfall:** the wrong belief is "I denied `Read` on the secrets folder, so nothing can touch it." The
symptom is a notebook file under that folder getting edited anyway, with no warning when the rule was
written — it silently covers three tools and omits a fourth. The fix: name every tool explicitly —
`Read`, `Edit`, and, if notebooks are in scope, a bare `NotebookEdit` deny. **Why people believe it:**
`Read` deny propagating to `Edit`/`Write` at all already feels generous; the natural next assumption
is that it is complete.

## §1.4.18 — file permissions are checked against `Edit(path)` and `Read(path)` only

`[TRAP]` `[DOC]` `[VERSION]` This is the single most dangerous silently-ignored configuration in the
whole permission system, because the settings file that gets it wrong reads exactly as though the
restriction exists. The documentation is explicit and names every tool the mistake is made with:

> Claude Code checks file permissions against `Edit(path)` and `Read(path)` rules only. If you write
> a path rule for `Write`, `NotebookEdit`, `Glob`, or the legacy `MultiEdit` tool instead, Claude Code
> accepts the rule but never consults it, and warns at startup, except for a `Glob` rule passed in
> `--allowedTools`. Use `Edit(docs/**)` in place of `Write(docs/**)`, `NotebookEdit(docs/**)`, or
> `MultiEdit(docs/**)`, and `Read(docs/**)` in place of `Glob(docs/**)`. Claude Code doesn't warn
> about a tool-name rule with no path, such as a deny rule for `Write`; it matches that rule at the
> tool level everywhere. **Requires Claude Code v2.1.210 or later.**

— *Configure permissions*, re-verified 2026-08-29.

`[VERSION]` The startup warning itself — the one safety net that would catch this mistake before it
bites — is only present from **v2.1.210 onward**. Loaded by an older binary, a `Write(docs/**)` path
rule produces no warning at all: silently accepted, silently never consulted, no signal anything is
wrong. On v2.1.2xx the warning fires — a reader troubleshooting an older install, or reading a blog
screenshot with no warning banner, should not conclude the rule ever worked.

Here is the settings object that looks like it protects `docs/` from being written, and does not:

```json
{
  "permissions": {
    "deny": [
      "Write(docs/**)"
    ]
  }
}
```

Nothing about this JSON is malformed — it parses, it loads, Claude Code accepts `Write(docs/**)` as a
syntactically valid deny rule, and then never checks a single `Write` call against it, because `Write`
calls are not gated by path rules at all; only `Edit(path)` and `Read(path)` are ever consulted. Every
`Write` into `docs/` proceeds exactly as if this deny rule were never written. The corrected object:

```json
{
  "permissions": {
    "deny": [
      "Edit(docs/**)"
    ]
  }
}
```

`Edit(docs/**)` is the rule form Claude Code actually checks, and it blocks the built-in tools that
edit files — which, per §1.4.17, already includes `Write` on this target version, so this single
`Edit` deny does what the author of the first JSON block believed `Write(docs/**)` already did.

| Rule form the author writes | What Claude Code does with it |
|---|---|
| `Write(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `NotebookEdit(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `MultiEdit(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ (legacy tool) |
| `Glob(docs/**)` in a settings file | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `Glob(docs/**)` passed via `--allowedTools` | the one documented exception — **is** consulted |
| `Write` (bare, no path) | matched at the tool level everywhere — **no warning, because there is nothing wrong**: a bare tool-name deny removes the whole tool from context |
| `Edit(docs/**)` | the correct form — **is** consulted |
| `Read(docs/**)` | the correct form for read-gating — **is** consulted |

**Pitfall:** the wrong belief is "I wrote a `Write` path rule, so writes to this path are blocked."
The symptom: the rule reads as intentional, produces an easy-to-miss startup warning, and every
`Write` proceeds unblocked. The fix is mechanical: any path-scoped file-permission rule is written as
`Edit(...)` or `Read(...)`, never `Write(...)`, `NotebookEdit(...)`, `MultiEdit(...)`, or `Glob(...)`
(except the `--allowedTools` exception for `Glob`). **Why people believe it:** `Write` sounds exactly
like the tool that should own a "block writes here" rule, and the schema accepts the string silently.

**Interview:** "You wrote `Write(docs/**)` in deny and writes to `docs/` still happen. Why?" — file
permissions are checked against `Edit(path)` and `Read(path)` only; every other tool name in a path
rule is parsed and silently never consulted. Use `Edit(docs/**)` instead, which also propagates to
`Write` per §1.4.17 on this target version.

**D-32** — Which tools consult path rules.

| Tool | Path rule consulted? | Silently accepted and ignored? | Write instead | Stops it at OS level |
|---|---|---|---|---|
| `Read` | Yes | — | — | sandbox filesystem restriction |
| `Edit` | Yes | — | — | sandbox filesystem restriction |
| `Write` | No | Yes (warns on v2.1.210+) | `Edit(path)` | sandbox filesystem restriction |
| `NotebookEdit` | No | Yes (warns on v2.1.210+) | `Edit(path)` — but per §1.4.17, needs an *explicit* `Edit` deny, since a `Read` deny alone doesn't propagate here either | sandbox filesystem restriction |
| `MultiEdit` (legacy) | No | Yes (warns on v2.1.210+) | `Edit(path)` | sandbox filesystem restriction |
| `Glob` | No, in a settings file | Yes (warns on v2.1.210+) — **except** via `--allowedTools`, which *is* consulted | `Read(path)` | sandbox filesystem restriction |
| `Grep` | Not gated directly; Claude Code makes a **best-effort attempt** to apply `Read` rules to it | not silently-ignored — a best-effort extension of `Read`, not a separate rule shape | — | sandbox filesystem restriction |
| Bash file commands (`cat`, `head`, `tail`, `sed`) | Yes — recognised against these specific Bash forms | — | — | sandbox blocks the process, not the rule |
| An arbitrary subprocess (e.g. a Python script opening the file itself) | **No** — reached by no rule | no rule form exists for this | — | **the sandbox is the only answer** — §1.4.19 |

## §1.4.19 — the boundary: built-in tools and recognised Bash commands, not an arbitrary subprocess

`[TRAP]` `[DOC]` §1.4.17–§1.4.18 describe what a `Read`/`Edit` deny *does* cover. This leaf states the
outer boundary — the point past which no permission rule reaches, and only the sandbox does.

> Read and Edit deny rules apply to Claude's built-in file tools and to file commands Claude Code
> recognizes in Bash, such as `cat`, `head`, `tail`, and `sed`. They don't apply to arbitrary
> subprocesses that read or write files indirectly, like a Python or Node script that opens files
> itself. For OS-level enforcement that blocks all processes from accessing a path, enable the
> sandbox.

— *Configure permissions*, re-verified 2026-08-29.

So the same `Read(./secrets/**)` deny rule that stops the built-in `Read` tool, and stops
`cat ./secrets/token.txt` run through the `Bash` tool, does **nothing at all** to:

```python
python3 -c "print(open('./secrets/token.txt').read())"
```

if that one-liner is itself launched through `Bash`. Claude Code's Bash-side recognition of `cat`,
`head`, `tail`, and `sed` is a **named-command allowlist for enforcement purposes**, not a general
"detect any file access inside a subprocess" mechanism — a script that opens a file handle in its own
interpreter, rather than invoking a recognised command name, is invisible to the permission layer
entirely. §1.4.17–§1.4.19 are one argument: a `Read` deny covers `Edit` and `Write` but not
`NotebookEdit`; the only rule forms ever consulted for file access are `Edit(path)` and `Read(path)`;
and even a correctly-written `Read`/`Edit` deny only reaches built-in tools and recognised Bash
commands, not an arbitrary subprocess. Each leaf narrows what "the permission system protects this
path" can mean — less than a reader who stopped at §1.4.16 would assume.

**Pitfall:** the wrong belief is "a `Read` deny is a filesystem-level guarantee — nothing in this
session can read that path." The symptom is a `python3` or `node` invocation, run through `Bash`,
reading a denied path successfully, because the file access never went through a recognised command
name or a built-in tool. The fix is **enable the sandbox** for OS-level enforcement that blocks every
process regardless of recognition. **Why people believe it:** "deny" reads like an absolute security
boundary, and for the tools it actually covers, it is one.

## §1.4.20 — `WebFetch(domain:…)` and the allow-or-deny-every-fetch forms

`[DOC]` A `WebFetch` rule gates the tool by the hostname of the URL it is about to fetch, using a
`domain:` prefix rather than a path:

> WebFetch rules use a `domain:` prefix and match against the hostname of the requested URL. Matching
> is case-insensitive, supports `*` wildcards, and strips a trailing `.` from both the rule and the
> hostname so `example.com.` and `example.com` are treated the same.

— *Configure permissions*, re-verified 2026-08-29.

| Rule | Matches |
|---|---|
| `WebFetch(domain:example.com)` | requests to `example.com` |
| `WebFetch(domain:*.example.com)` | any subdomain at any depth (`api.example.com`, `a.b.example.com`), not `example.com` itself |
| `WebFetch(domain:*)` | every domain — but not equivalent to a bare `WebFetch` rule, see below |
| `WebFetch(domain:example.*)` | `example.org` (`*` fills one segment between dots), not `example.evil.com` (crossing a dot) |

`[NUM]` `[VERSION]` Wildcards in `WebFetch` rules require **v2.1.172 or later** to match fetches at
all — on an older binary, a `domain:*.example.com` rule is accepted but never matches anything.

A **bare `WebFetch` rule** (the tool name, no `domain:` part) and `WebFetch(domain:*)` both cover
every URL, but they are not interchangeable — this is a second instance of the same lesson as
§1.4.18, where two syntactically different rules that look like they mean the same thing are
consulted differently:

| Rule | In `allow` | In `deny` |
|---|---|---|
| `WebFetch` (bare) | fetches without prompting; does **not** change which hosts sandboxed Bash commands can reach | removes the `WebFetch` tool entirely — Claude cannot fetch at all; does not change the sandbox's allowed hosts |
| `WebFetch(domain:*)` | fetches without prompting, **and** sandboxed commands can reach any host | keeps the tool, refuses every fetch, **and** sandboxed commands cannot reach any host |

Only the `domain:` form feeds the sandbox's own allowed/denied domain list; the bare form only touches
the tool's own prompt behaviour. To let Claude fetch freely while leaving the sandbox allowlist
untouched, write the bare form:

```json
{
  "permissions": {
    "allow": ["WebFetch"]
  }
}
```

**Insight:** the same "tool name vs. scoped specifier" split as §1.4.18's `Write` vs. `Edit` confusion,
transplanted onto `WebFetch` — the rule that looks maximally permissive (`domain:*`) is actually
**more** consequential than the bare tool name, because it also widens the sandbox's network
boundary, not just the permission prompt.

## §1.4.21 — the three MCP rule forms, and the parenthesised form that is silently skipped

`[ZERO]` **MCP** (Model Context Protocol) is the protocol Claude Code uses to talk to external tool
servers — a running process exposing named tools the model can call, the same way it calls a
built-in tool like `Bash` or `Read`. An MCP tool's canonical name is always `mcp__<server>__<tool>`.

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
attempt to deny the tool only for one repository — is **not** a recognised MCP rule shape. It parses
as JSON and loads, then Claude Code skips that entry outright at load time, surfacing it only in the
invalid-settings dialog and `claude doctor` — neither shown by a headless `claude -p` run in CI. The
parameter-matching path that actually works for an MCP tool is the CLI flag named in the quote:

```
claude --disallowedTools "mcp__github__create_issue(repo:internal-secrets)"
```

**Pitfall:** the wrong belief is "MCP tools support the same `Tool(param:value)` syntax as `Agent`
and `Bash`, written straight into `settings.json`." The symptom is the rule silently never taking
effect. The fix: parameter matching on an MCP tool is a `--disallowedTools` CLI flag, never a
parenthesised rule in a settings file — the three settings-file forms never take a parameter argument.
**Why people believe it:** `Agent(model:opus)` and `Bash(run_in_background:true)` in §1.4.23 use
exactly this shape and work fine in settings, so it reads as universal rather than an exception.

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

A rule can equally name a custom subagent, e.g. `Agent(readonly-reviewer)`. To disable the built-in
`Explore` agent entirely:

```json
{
  "permissions": {
    "deny": ["Agent(Explore)"]
  }
}
```

The same gate is available at the CLI via `--disallowedTools "Agent(Explore)"`.

**Gotcha:** denying `Agent(Explore)` does not remove the *capability* it provides — the primary
session can still read files and grep directly. It removes only the option of delegating that work to
the specialised subagent, which matters for cost and context isolation, not for whether the files can
be read at all.

## §1.4.23 — parameter matching for deny/ask on any built-in tool

`[DOC]` `Tool(param:value)` is a distinct specifier shape from a path or a Bash command string: it
matches a **named input parameter** on any built-in tool's call, for `deny`/`ask` rules only.

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
  `Agent(model:opus)` and `Agent(isolation:worktree)` — never combined into one specifier.
- **Direct fields only.** "The parameter name must be a direct field of the tool's input... fields
  nested inside an object or array are not matchable." A parameter buried inside a nested object on
  a tool's call cannot be targeted this way at all.
- **`*` wildcard supported.** The value accepts `*` as a wildcard matching any sequence of
  characters — `Agent(isolation:*)` matches any *explicit* isolation value, but "a parameter the
  model omits is never matched, so `Agent(model:*)` doesn't match a call that leaves `model` unset."
- **Compared before normalisation.** "The value is compared against the literal input Claude sends,
  before any normalization. `Agent(model:opus)` matches the alias `opus` but not a full model ID."

— *Configure permissions*, re-verified 2026-08-29.

That last constraint has a direct consequence: if the model emits the fully-qualified model identifier
for Opus rather than the short alias `opus`, `Agent(model:opus)` does **not** match — the deny rule
the author believed covered "every call that uses Opus" only covers calls sending the literal alias
`opus`. `--verbose` shows the exact parameter names and values on each call, the only reliable way to
confirm the literal string a rule must match before normalisation.

There is also a documented **content-field exclusion**: a tool's primary content field — `command`
for `Bash`/`PowerShell`, `file_path` for `Read`/`Edit`/`Write`, `path` for `Grep`/`Glob`,
`notebook_path` for `NotebookEdit`, `url` for `WebFetch` — cannot be matched this way. A rule like
`Bash(command:rm *)` is ignored with a startup warning, because a compound command could smuggle past
it; use each tool's own specifier syntax (`Bash(rm *)`, `Read(./path)`, `WebFetch(domain:host)`)
instead.

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
   session's primary working directory at all, for the rest of the session.
3. **Any allow rule switches `/cd` to allowlist mode.** "Adding any `Cd` allow rule switches `/cd` to
   allowlist mode: the resolved target directory must match one of your allow rules, or `/cd`
   refuses. With no `Cd` rules configured, `/cd` keeps its default behavior and prompts you to trust
   an unfamiliar directory." The surprising one — one narrow `Cd` allow rule does not merely *add* a
   directory to what was reachable before; it **replaces** "prompt to trust anywhere" with "only these
   directories, ever."
4. **`*` is one segment, `**` spans segments.** Path patterns share the `//`, `~/`, `/` anchors from
   Read/Edit rules, but matching is anchored to the whole directory path rather than gitignore-style.
   `*` matches exactly one path segment, `**` matches across segments, and a trailing `/**` also
   matches its named root.

— *Configure permissions*, re-verified 2026-08-29.

| Rule | Matches | Does not match |
|---|---|---|
| `Cd(~/code/*)` | `~/code/app` | `~/code/app/src`, `~/code` |
| `Cd(~/code/**)` | `~/code` and any directory under it | directories outside `~/code` |
| `Cd(**/node_modules)` | any `node_modules` directory at any depth | `node_modules/pkg` |

**Pitfall:** the wrong belief is "I added `Cd(~/code/**)` to allow, so I can still `/cd` anywhere I
could before, plus that directory." The symptom is every other previously-reachable directory now
refusing `/cd` outright, with the trust-prompt fallback gone. The fix is to treat the first `Cd` allow
rule as a hard mode switch: once written, every directory the session will ever `/cd` into must have
its own allow rule, or `/cd` refuses. **Why people believe it:** `permissions.allow` for every other
tool family in this file is additive — writing an `allow` entry only ever widens what is permitted on
top of the existing default, and `Cd` is the one family in the whole permission system where adding an
`allow` rule *narrows* the default instead.

## Pitfalls

- **Belief:** "I wrote `Write(docs/**)` in deny, so writes to `docs/` are blocked." **Outcome:**
  accepted and parsed, never consulted — file permissions check `Edit(path)`/`Read(path)` only, so
  every `Write` proceeds (warns at startup on v2.1.210+, easy to miss). **Fix:** write `Edit(docs/**)`
  instead. **Why people believe it:** the tool name matches intent so exactly that a clean load reads
  as confirmation.
- **Belief:** "A `Read` deny on a path is a filesystem-level guarantee." **Outcome:** a
  `python3 -c "open(...).read()"` one-liner through `Bash` reads the path successfully — Read/Edit
  deny covers built-in tools and recognised Bash commands only, not an arbitrary subprocess. **Fix:**
  enable the sandbox for OS-level enforcement. **Why people believe it:** "deny" reads as an absolute
  boundary, and for the tools it covers, it is one.
- **Belief:** "MCP tools take the same `Tool(param:value)` rule as `Agent`/`Bash`." **Outcome:**
  Claude Code skips any parenthesised `mcp__` rule at load time, surfacing only in the
  invalid-settings dialog and `claude doctor` — not in `claude -p`. **Fix:** use `--disallowedTools`
  for MCP parameter matching. **Why people believe it:** the parenthesised shape works for other
  built-in tools on the same page, so it reads as universal rather than a documented exception.
- **Belief:** "Adding one `Cd` allow rule just opens an extra directory on top of normal behaviour."
  **Outcome:** the first `Cd` allow rule switches `/cd` into allowlist mode — every uncovered
  directory now refuses `/cd`. **Fix:** once one `Cd` allow rule exists, write one per directory the
  session will ever `/cd` into. **Why people believe it:** `allow` is additive everywhere else in
  this file — Bash, Read/Edit, WebFetch, MCP, Agent — so `Cd` surprises only after the fact.

## Cheat sheet

| Fact | Value |
|---|---|
| Read/Edit path syntax | gitignore pattern syntax |
| Four anchors | `//path` (filesystem root), `~/path` (home), `/path` (settings-source-relative), `path`/`./path` (cwd-relative) |
| `Read(./.env)`, `Read(./secrets/**)` | documentation's own paste-ready sensitive-file examples |
| Read deny propagates to | `Edit`, `Write` (not `NotebookEdit`) |
| Version gate on that propagation | edits: v2.1.208+; writes: v2.1.228+ |
| File permissions consulted for | `Edit(path)`, `Read(path)` — only |
| Path rules accepted but never consulted | `Write(...)`, `NotebookEdit(...)`, `MultiEdit(...)`, `Glob(...)` in settings (except `Glob` via `--allowedTools`) |
| Startup warning for ignored path rule | v2.1.210+ |
| Bare tool-name deny (no path) | matched at tool level everywhere — no warning, nothing wrong |
| Read/Edit deny reaches | built-in file tools, recognised Bash commands (`cat`, `head`, `tail`, `sed`, …) |
| Read/Edit deny does NOT reach | an arbitrary subprocess reading the file itself (e.g. a Python script) |
| OS-level fix for that gap | enable the sandbox |
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

<details><summary>1. Why does `Read(~/secrets/**)` written in user settings not block a `secrets/` directory inside a project?</summary>
`~/` anchors at the home directory regardless of which project is open, so the rule denies only
`~/secrets/**`; a project's own `secrets/` under the project root is a different path, untouched.
</details>

<details><summary>2. A settings file denies `Read(./secrets/**)` only. Does a `Write` into a brand-new file under `secrets/` succeed? Does a `NotebookEdit` there succeed?</summary>
`Write` and `Edit` both fail — a `Read` deny propagates to both (v2.1.208+/v2.1.228+). `NotebookEdit`
is not covered by that propagation, so it succeeds unless a separate `Edit` (or bare `NotebookEdit`)
deny is added.
</details>

<details><summary>3. A project denies `Write(docs/**)`. Does this block writes into `docs/`? What is the correct rule?</summary>
No. File permissions are checked against `Edit(path)` and `Read(path)` only; the `Write` rule is
parsed but never consulted (warns at startup on v2.1.210+). The correct rule is `Edit(docs/**)`.
</details>

<details><summary>4. `Read(./secrets/**)` and `Edit(./secrets/**)` are both denied. Does `cat ./secrets/token.txt` through Bash succeed? Does `python3 -c "print(open('./secrets/token.txt').read())"` through Bash succeed?</summary>
`cat` is blocked — it's a recognised Bash command for Read/Edit enforcement. The Python one-liner
succeeds — Read/Edit deny covers built-in tools and recognised Bash commands, not an arbitrary
subprocess doing its own file I/O. Only the sandbox blocks that case.
</details>

<details><summary>5. What is the difference between a bare `WebFetch` deny rule and `WebFetch(domain:*)` in deny?</summary>
A bare `WebFetch` deny removes the tool entirely and doesn't touch sandboxed hosts. `WebFetch(domain:*)`
in deny keeps the tool, refuses every fetch, and also removes every host from the sandbox's
allowed-domain list — the more consequential of the two despite looking like a simple wildcard.
</details>

<details><summary>6. A settings file contains `"deny": ["mcp__github__create_issue(repo:internal-secrets)"]`. What happens when Claude Code loads it?</summary>
Skipped entirely at load time — it's an MCP rule with parentheses, and settings-file MCP rules are
only `mcp__server`, `mcp__server__*`, or `mcp__server__tool`. The skip surfaces only in the
invalid-settings dialog and `claude doctor`, neither shown in `claude -p`. Use `--disallowedTools`.
</details>

<details><summary>7. Name the three built-in `Agent(Name)` rule targets and what each one is.</summary>
`Agent(Explore)` — fast, read-only search/analysis agent. `Agent(Plan)` — research agent for plan
mode. `Agent(fork)` — a subagent that inherits the entire conversation instead of starting fresh.
</details>

<details><summary>8. Why doesn't `Agent(model:opus)` in deny reliably block every call that uses the Opus model?</summary>
Parameter matching compares the literal pre-normalisation value. `Agent(model:opus)` matches the
alias `opus` but not a call carrying the fully-qualified model ID — that call slips through unmatched.
`--verbose` shows which literal string is on the wire.
</details>

<details><summary>9. Can `Bash(command:rm *)` be written to gate the Bash tool's `command` parameter directly?</summary>
No. A tool's primary content field (`command`, `file_path`, `path`, `notebook_path`, `url`) is
excluded from parameter matching — a compound command could smuggle past a naive match. Claude Code
ignores the rule with a startup warning; use `Bash(rm *)` instead.
</details>

<details><summary>10. A settings file has no `Cd` rules at all. An author adds `Cd(~/code/**)` to `allow`, intending only to add that directory to what `/cd` can already reach. What actually happens?</summary>
Any `Cd` allow rule switches `/cd` into allowlist mode: the target must match an allow rule or `/cd`
refuses outright. Every directory outside `~/code/**` that used to be reachable via the trust prompt
is no longer reachable — the rule narrows the default rather than extending it.
</details>

## Open questions

None.

---

**Leaves covered:** 1.4.16–1.4.24 (9 leaves)
**Leaves deferred:** none
**Diagrams included:** D-32
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 598
