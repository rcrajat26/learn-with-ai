# 21 AI for Coding — MCP transports and scopes — INTERMEDIATE (§2.4.1–2.4.5)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the blocking-guard pattern](../hooks/08-the-blocking-guard-pattern.md) · Next: [the per-turn tax](02-the-per-turn-tax.md)

Since §0.3.2 a tool has been a fixed triple: a name, a description, and a JSON input schema, chosen
from by the model on description alone, out of whatever list the harness built for that session.
Every tool in that list so far has been one the Claude Code binary itself shipped — `Read`, `Edit`,
`Bash`, the rest of §0.3.1's built-in catalogue. MCP is the mechanism that lets a *different* process
add more triples to that same list. That is the whole concept, and the consequence is immediate:
**more tools means more schemas in every request**, because the full tool list — built-in and
MCP alike — goes out with every turn, not just the turn that uses one. §2.4.2 in the next file turns
that into an arithmetic tax with real token counts; this file does not repeat it, only names it, because
you cannot reason about the cost of a mechanism before you know what the mechanism is.

The other consequence is a security one: an MCP server hands the agent a door into a system it could
not otherwise reach — an issue tracker, a database, a cloud console. That is genuinely useful, and it
genuinely enlarges the blast radius of anything the agent is tricked into doing. §2.9's threat model
owns that discussion in full; this file states it once and moves on.

This file has no diagram of its own — the manifest gives this row none. Where a picture helps, it
points to D-13 (`ground-zero/03-basics-the-agent-loop.md`, the built-in tool categories) or forward to
D-56 (the next file, the per-turn token tax): the six-link chain's "SVG" step is not applicable to any
concept below, and each concept says so once rather than restating it per link.

## §2.4.1 What MCP is, and what it buys `[ZERO]`

**Concept.** Picture the tool list the model reasons over as a menu the harness assembles fresh for
every session. Until now, only the kitchen — Claude Code's own binary — could add dishes to that menu.
MCP (Model Context Protocol) is a wire protocol that lets a separate kitchen, running as its own
process, hand the harness a menu of its own: its tools, plus two things this file has not yet
mentioned — **resources** (named, retrievable pieces of content the agent can pull in, like a file or
a query result) and **prompts** (pre-written prompt templates the server exposes, distinct from a
project's own skills). All three arrive shaped exactly like the tools you already know: a name, a
description, and a schema, because that is the shape the model already knows how to reason over —
MCP does not invent a new shape, it only adds a new *source* for it.

**Why it exists.** Before a shared protocol, connecting an AI assistant to a real system — Jira,
a database, a cloud API — meant one team writing bespoke glue code for one assistant, and the next
team writing different bespoke glue code for a different assistant, for the same system. N systems
times M assistants is N×M integrations, each maintained separately, each drifting separately. A
standard protocol collapses that to N+M: a system's owner ships one MCP server, once, and every
MCP-speaking client — Claude Code, or any other — can talk to it without custom code on either side.
This is the ordinary "write once, integrate everywhere" argument, applied to tool exposure instead of
to a REST contract.

**How it works.** An MCP server is a running process (local) or a reachable endpoint (remote) that
speaks the MCP wire protocol. When Claude Code connects to one — at session start, for a server
registered in a scope the session loads — it asks the server to list what it has, and the server
answers with its tools, resources, and prompts. The harness folds the returned tools into the same
tool list the model already sees, under the naming rule from §1.4's permission chapter:
`mcp__<server>__<tool>`. A server named `atlassian-cloud` that exposes a tool called
`addCommentToJiraIssue` becomes, from the model's point of view, one more entry in the menu named
`mcp__atlassian-cloud__addCommentToJiraIssue` — indistinguishable in shape from `Read` or `Edit`, just
supplied by someone else's process instead of the Claude Code binary.

**Code.** The sdlc-harness's own `CLAUDE.md` shows what this looks like once it is wired up — real
tool names the model actually calls, not a hypothetical:

```
mcp__atlassian-cloud__addCommentToJiraIssue
mcp__atlassian-cloud__lookupJiraAccountId
```

Nothing about those two names is special-cased in the harness's prompts beyond being invoked like any
other tool; the `mcp__atlassian-cloud__` prefix is the only visible trace that they came from a server
rather than from the binary.

**Gotcha.** A reader who has only ever heard "MCP gives Claude tools" undercounts what a server can
add. Resources and prompts ride the same connection and the same registration — a server can expose a
document store as browsable resources, or ship its own prompt templates, with no tool involved at all.
Treating "MCP" and "MCP tools" as synonyms means missing half of what a given server's registration
actually grants.

> MCP is a protocol that lets an external process register tools, resources, and prompts into an
> agent's session at connection time, using the same name-description-schema shape the model already
> reasons over for the harness's own built-in tools.

## §2.4.2 The transports, and which one wins where `[DOC]`

**Concept.** A transport is how Claude Code physically reaches the server process to ask it "what do
you have?" and later to call what it returns. Verified against the installed v2.1.251 binary
(`claude mcp add --help`) immediately before writing this leaf — the public pages in this topic's
permitted set (`settings`, `settings-reference`) describe the *keys that gate* MCP servers but not the
transport mechanics themselves, so the authoritative source here is the running binary, per this
guide's stated authority order (documentation > observed binary behaviour). Three transports exist:
`stdio`, `sse`, and `http`. `stdio` is the default when `--transport` is omitted.

**Why it exists.** Servers live in two fundamentally different places. Some are a small program meant
to run on your own machine, with no network hop and no auth handshake — a filesystem browser, a local
git helper. Others are a hosted, multi-tenant service you don't run yourself and don't want running on
your laptop — Jira, Sentry, a company-wide knowledge base — reached over the network and usually
gated by OAuth. One transport shape cannot serve both well: a subprocess model has no answer for "the
service lives on someone else's infrastructure," and a network model is needless overhead for "the
tool is a five-line script sitting next to your dotfiles."

**When to reach for which — the sibling comparison.**

| Transport | Configured with | What must be running | Where it fails | What the failure looks like |
|---|---|---|---|---|
| `stdio` (default) | `claude mcp add <name> -- <command> [args...]` | a local subprocess that speaks MCP over its own stdin/stdout | the binary is missing, the wrong version is on `PATH`, the process crashes, or a bare URL is handed to it by mistake | `claude mcp list` reports `✘ Failed to connect` with a spawn-level error — observed directly against v2.1.251: `ENOENT: ENOENT: no such file or directory, posix_spawn '<value>'` when the "command" is actually a URL |
| `http` (current, recommended for remote) | `claude mcp add --transport http <name> <url>` | a reachable HTTP endpoint, typically behind OAuth (`claude mcp login <name>`) | DNS failure, the endpoint refusing the connection, or an expired/missing OAuth token | `claude mcp list` reports `✘ Failed to connect — ConnectionRefused: Unable to connect. Is the computer able to access the url?` (observed directly against v2.1.251 for an unreachable local HTTP endpoint), or a 401 that clears only after re-running `claude mcp login` |
| `sse` (legacy remote) | `claude mcp add --transport sse <name> <url>` | the same reachability and auth requirements as `http`, but framed as a Server-Sent Events stream rather than the newer Streamable-HTTP request/response shape | same failure shapes as `http`; several real providers, Atlassian's hosted MCP endpoint among them, are actively retiring `sse` in favor of `http` | connection refusal or an explicit deprecation response from the server, depending on how aggressively the provider has cut the old path |

`http` wins over `sse` for any new remote registration in v2.1.2xx: it is the transport providers are
migrating *to*, not away from, and the CLI's own help text lists it first. `stdio` wins over both for
anything that already lives on your machine and needs no network round trip — a local subprocess pays
no OAuth latency and has no DNS to fail.

**Code.** The exact invocation Claude Code prints when you omit `--transport` and hand it a URL —
this is the CLI warning you before it does the wrong thing, verified live:

```
$ claude mcp add oops-no-transport https://mcp.atlassian.com/v1/mcp
Warning: The command "https://mcp.atlassian.com/v1/mcp" looks like a URL, but is being interpreted as a stdio server as --transport was not specified.
If this is an HTTP server, use: claude mcp add --transport http oops-no-transport https://mcp.atlassian.com/v1/mcp
If this is an SSE server, use: claude mcp add --transport sse oops-no-transport https://mcp.atlassian.com/v1/mcp
Added stdio MCP server oops-no-transport with command: https://mcp.atlassian.com/v1/mcp  to local config
```

The corrected form, registering Atlassian's hosted Jira/Confluence server over the current recommended
transport:

```
claude mcp add --transport http atlassian-cloud https://mcp.atlassian.com/v1/mcp
claude mcp login atlassian-cloud
```

The second line runs the OAuth flow the `http` row above requires — `claude mcp login` works for
`http`, `sse`, and claude.ai connector servers, and needs v2.1.186 or later per `cli-reference`.

**Gotcha.** The CLI warns rather than silently misfiring, but it still **adds the broken registration**
before you fix it — the warning does not abort the command. A reader who reads only the first line and
skips the fix line ends up with a `stdio` server registered under a URL as its "command," which will
report `ENOENT` on every future connection attempt until removed (`claude mcp remove <name>`) and
re-added with the right transport.

> A transport is the wire Claude Code uses to reach an MCP server's process: `stdio` for a local
> subprocess talking over its own stdin/stdout, `http` for a reachable, typically OAuth-gated remote
> endpoint using the current Streamable-HTTP framing, and `sse` for the same remote shape over the
> older Server-Sent-Events framing that providers are now retiring in `http`'s favor.

## §2.4.3 The configuration scopes, and where a registration actually lives `[DOC]`

**Concept.** "Registering a server" does not mean editing one canonical file — which file receives the
registration depends on the **scope** you registered it at, and the scopes disagree on both visibility
(who else sees it) and mutability (whether you are meant to hand-edit the result). Verified against
the installed v2.1.251 binary (`claude mcp add --help` lists `-s, --scope <scope>` as `local`, `user`,
or `project`, default `local`) and against `plugins` (re-verified 2026-08-29), which documents the
fourth scope, plugin-shipped `.mcp.json`, immediately before writing this leaf.

**Why it exists.** A registration you make for yourself, on your own machine, to test a server you are
still evaluating, has nothing in common with a registration a team commits so every engineer on a repo
gets the same Jira connection. Collapsing those into one file would force a choice nobody wants: either
your personal experiments leak into the team's shared config, or the team's shared config has to live
in your personal, un-shared state. Four scopes exist because four different "who should see this"
answers exist.

**How it works, and where each one writes — observed directly against v2.1.251, since the two settings
pages in this topic's permitted citation set describe the *approval keys* over these scopes (§2.4.4)
but not the storage format itself:**

| Scope | `claude mcp add` flag | Where the registration is written | Who sees it |
|---|---|---|---|
| `local` (default) | `-s local` or omitted | `~/.claude.json`, under `projects["<absolute-project-path>"].mcpServers` | you, only inside this one project directory |
| `user` | `-s user` | `~/.claude.json`, under the top-level `mcpServers` key | you, in every project you open |
| `project` | `-s project` | `.mcp.json` at the repository root | everyone who checks out the repo — meant to be committed |
| plugin | not a `claude mcp add` flag — shipped by the plugin itself | `.mcp.json` at the **plugin's** root directory (`Plugin root` per `plugins`, quoted: *"`.mcp.json` — Plugin root — MCP server configurations"*) | everyone who installs that plugin |

This reconciles directly with §1.1.4's rule that `~/.claude.json` is **never hand-edited** — both
`local` and `user` scope write into that exact file, and the reconciliation is that you are not meant
to open it yourself for this purpose either. `claude mcp add -s local` or `claude mcp add -s user` is
the tool writing to its own state file *for* you, the same relationship §1.1.4 already established for
sign-in state and per-project trust. What you *do* author by hand is a `.mcp.json` — at a repository
root for `project` scope, or at a plugin's root as part of building the plugin — because that file is a
plain, committable project artefact, not tool-owned scratch state.

**Code.** A complete, valid `.mcp.json` for `project` scope, registering the same Atlassian server
`§2.4.2` connected over `http` — this is what `claude mcp add --scope project` writes, and what you
would commit at a repository root to share the registration with a team:

```json
{
  "mcpServers": {
    "atlassian-cloud": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp"
    }
  }
}
```

Compare that to what the same command writes for a local `stdio` server, observed directly:

```json
{
  "mcpServers": {
    "checklist-refresh": {
      "type": "stdio",
      "command": "checklist-refresh",
      "args": [],
      "env": {}
    }
  }
}
```

The parent key is always `mcpServers` regardless of scope; only the surrounding file and the
visibility differ. A `.mcp.json` fragment with the `atlassian-cloud` object but no `mcpServers` wrapper
is not valid input to Claude Code — the wrapper key is load-bearing, not decorative.

**Gotcha.** `claude mcp list` and `claude mcp get` merge all four scopes into one flat view with no
scope column, which is convenient for "is this server active" and actively unhelpful for "which file
do I edit to change it." §2.4.5 is exactly the failure mode this produces when someone tries to answer
the second question by reading a settings key instead of checking scope.

> A scope is which file an MCP registration is written to and who else can see it: `local` and `user`
> both live in the tool-owned `~/.claude.json` — never hand-edited, only written by `claude mcp add` —
> while `project` and plugin registrations live in a plain, hand-authored `.mcp.json` meant to be
> committed or shipped.

## §2.4.4 Project-server approval `[DOC]`

**Concept.** A `project`-scope server declared in a repository's `.mcp.json` does not connect the
moment you open that repository. Verified against `permissions` (re-verified 2026-08-29) and
`settings-reference` (re-verified 2026-08-29) immediately before writing this leaf: `claude mcp list`
and `claude mcp get` describe an unapproved `.mcp.json` server as **"⏸ Pending approval"** and state
plainly that Claude Code is "not connected to" it in that state — confirmed live, registering a
`project`-scope server in a fresh checkout produces exactly that status until approved.

**Why it exists.** This is the same reasoning §1.4.32 already gave you for `permissions.allow` and
`additionalDirectories`: a committed file is something a stranger — anyone who can open a pull request
against the repository — gets to write. A `.mcp.json` entry is at least as capable a grant as a
permission rule; it can hand the agent a live connection to an arbitrary command or an arbitrary
remote endpoint the moment the repository is opened. Applying that grant automatically, before you have
looked at what it is, would let a hostile fork run its server just by getting you to `cd` into it. The
fix is the same asymmetric gate: workspace trust plus one further approval step, applied to the
permissive direction only, exactly as it was for `allow` rules — this section does not re-teach that
mechanism, only names the surface it now covers.

**How it works.** Three settings keys govern the approval, all `[DOC]`, quoted from
`settings-reference` (re-verified 2026-08-29):

- `enableAllProjectMcpServers` — *"Approve every server in project `.mcp.json` files without a
  prompt."*
- `enabledMcpjsonServers` — *"Approve specific servers from a project's `.mcp.json`."*
- `disabledMcpjsonServers` — *"Reject specific servers from a project's `.mcp.json`."*

All three are scoped "Any file" per `settings-reference`, so a team can pre-approve or pre-reject
specific `project`-scope servers from `.claude/settings.json` rather than making every engineer click
through the same prompt individually. Without one of these, opening a repository with a new
`.mcp.json` server prompts you interactively to approve or reject it, the same trust-first posture
`allow` rules get.

**Code.** A `.claude/settings.json` that pre-approves exactly the Atlassian server from §2.4.3 for
everyone on the team, so it connects without a per-engineer prompt, while still leaving every other
`.mcp.json` entry ungated:

```json
{
  "enabledMcpjsonServers": ["atlassian-cloud"]
}
```

**Gotcha.** `enableAllProjectMcpServers` approving "every server" means every server **currently and
later** declared in that repository's `.mcp.json` — a team that sets it once to silence a prompt during
onboarding has also pre-approved whatever a future pull request adds to that file, with no further
review step. §2.4.5 covers the sharper, documented version of this same key's limits.

> Project-server approval is the workspace-trust gate applied to `.mcp.json`: a committed server does
> not connect until it is approved — interactively, or in bulk via `enableAllProjectMcpServers` /
> `enabledMcpjsonServers` — because a `.mcp.json` entry grants a live connection with the same "a
> stranger's file shouldn't get to widen this unreviewed" force as a permission `allow` rule.

## §2.4.5 `enabledMcpjsonServers` answers a narrower question than it looks like `[TRAP]` `[CASE]`

**Pitfall:** the belief in action is reading `enabledMcpjsonServers` to answer "which MCP server is
active in this session right now." The symptom: the key can say a server is approved while the
tools that server would provide are not the ones actually live, because `enabledMcpjsonServers` only
ever governs servers **declared in a `.mcp.json` file** — it has no jurisdiction over `local`- or
`user`-scope registrations, which live in `~/.claude.json` and were never subject to `.mcp.json`
approval in the first place. The fix: to know which server is actually live, check registration —
`claude mcp list` or the `mcpServers` contents of `~/.claude.json` — not this key.

This is not a hypothetical trap; it is a documented real mistake in the sdlc-harness's own scripts,
which is why it carries `[CASE]` alongside `[TRAP]`. `plugins/sdlc-harness/hooks/check-init.sh`,
lines 21–30, verbatim:

```bash
# Handbook-selection nudge (RFC handbook-platform-choice). The fact being read
# is which handbook MCP server is REGISTERED at user scope, matching
# scripts/resolve-active-handbook.sh exactly -- these two must never tell the
# engineer different stories about the same workspace.
#
# This deliberately does NOT read `enabledMcpjsonServers`: that key only gates
# servers declared in a `.mcp.json` (which this repo forbids committing), so it
# has no bearing on the user-scope registrations the handbooks actually use. An
# earlier version of this block read it and could report ig-trading active in a
# session where only igmarkets tools existed.
```

`scripts/select-handbook.sh`, lines 9–25, verbatim, gives the fuller incident this comment is
summarizing — the script that originally shipped the bug, and the fix it was rewritten to apply:

```bash
# WHY REGISTRATION, NOT `enabledMcpjsonServers`
# --------------------------------------------
# This script originally toggled `enabledMcpjsonServers` in
# .claude/settings.local.json. That key ONLY gates servers declared in a
# `.mcp.json` — it has no effect on servers registered at user scope in
# ~/.claude.json, which is how both handbooks are actually registered
# (`claude mcp add --scope user`, via each handbook's own start.sh).
#
# Demonstrated on a real workspace: `headroom` and `mcp-servicenow` run while
# absent from `enabledMcpjsonServers`. The key is not meaningless in general --
# it really does gate `.mcp.json`-declared servers, and an ancestor `.mcp.json`
# two levels above the harness was gating one there -- but `igmarkets-handbook`
# was ALSO registered at user scope, which the key cannot touch. So toggling it
# moved the resolver's answer (skill prefix + the five tokens) while the live
# user-scope server stayed put: the playbook would call `igt:rag-query` against
# an igmarkets-only session. Since bootstrap provisions via `start.sh --user`,
# user scope is the case that matters and the key can never govern it.
```

**Then explain it.** The design property this demonstrates is that an approval key and a registration
fact are two different sources of truth, and only one of them tells you what is actually connected.
The harness's two handbook MCP servers (`igmarkets-handbook`, `igtrading-handbook`) are both registered
at `user` scope via `claude mcp add --scope user`, invoked from each handbook's own `start.sh` — never
declared in a `.mcp.json`, because, per the comment, this repository forbids committing one. Toggling
`enabledMcpjsonServers` therefore changed what a **resolver script** believed (its own notion of "which
handbook is selected"), while the actual live server — the one the model could really call tools
against — stayed exactly as it was, registered at user scope, untouched by the key. The observable
failure: a playbook step could call an `igt:rag-query`-prefixed skill against a session where only
`igmarkets-handbook`'s tools were actually connected, because the resolver's answer and the real
registration had been allowed to diverge. The fix the second file documents is enforcing the "at most
one handbook" invariant on the fact the key cannot see — which server is *registered* — checked with
`claude mcp list` / `~/.claude.json` directly, rather than on a proxy key that only covers one of the
four scopes from §2.4.3.

**Why people believe it:** the name reads as general — "enabled MCP JSON servers" sounds like "which
MCP servers are enabled," full stop — and nothing in the key's name signals that it is scoped to one
file format out of the four registration paths in §2.4.3. An engineer who has only ever seen `project`-
scope servers in a given codebase has no occasion to discover the narrower truth until, as here, a
`user`-scope registration exists alongside it and the two disagree.

**Interview:** "What does `enabledMcpjsonServers` actually gate?" — Only servers declared in a project's
committed `.mcp.json`; it says nothing about `local`- or `user`-scope registrations in `~/.claude.json`,
so it can never be the source of truth for "which MCP server is live in this session" on its own —
check `claude mcp list` or the registration itself for that.

No gotcha beyond the pitfall itself: this leaf's entire content *is* the gotcha.

## Pitfalls

- **Belief in action:** "I'll check `enabledMcpjsonServers` in the settings file to see which MCP
  server this session is actually using." **Surprising outcome:** the key can list a server as
  approved, or omit one entirely, with no bearing on whether a `user`- or `local`-scope server is the
  one really connected — exactly the divergence `scripts/select-handbook.sh` shipped and then had to
  fix. **What actually gets the guarantee:** `claude mcp list`, or reading the `mcpServers` contents of
  `~/.claude.json` and the repository's `.mcp.json` directly. **Why people believe it:** the key's name
  sounds general-purpose, and most engineers meet `project`-scope servers before they meet `user`-scope
  ones, so the narrower truth never surfaces until the two scopes disagree.
- **Belief in action:** "`~/.claude.json` is just another config file — I'll add an MCP server to it by
  hand to save a command." **Surprising outcome:** the tool treats the file as its own scratch state,
  as §1.1.4 already established for permissions and trust, and a hand edit risks being overwritten on
  the next `/config` change or trust decision, with no warning that it happened. **What actually gets
  the guarantee:** `claude mcp add -s local` or `claude mcp add -s user`, letting the tool write its own
  file. **Why people believe it:** the file sits right beside `.claude/`, JSON-shaped, looking exactly
  like every other config file in the tree.
- **Belief in action:** "I'll register a remote server with `claude mcp add my-server <url>` and it'll
  figure out I mean HTTP." **Surprising outcome:** `stdio` is the default transport, so Claude Code
  tries to spawn the URL as a shell command and reports `ENOENT: ... posix_spawn '<url>'` on every
  connection attempt — verified live against v2.1.251. **What actually gets the guarantee:**
  `claude mcp add --transport http <name> <url>` (or `--transport sse` for a legacy endpoint), stated
  explicitly, never inferred. **Why people believe it:** the CLI's own warning message shows it *can*
  tell the argument looks like a URL, which reads as "so it must handle it correctly" rather than "so
  it is warning you that it won't."

## Cheat sheet

| Item | Value |
|---|---|
| Transports | `stdio` (default, local subprocess), `http` (current, remote, OAuth), `sse` (legacy remote, being retired) |
| Register a server | `claude mcp add [--transport stdio\|http\|sse] [-s local\|user\|project] <name> <commandOrUrl> [args...]` |
| Default scope | `local` |
| `local` scope storage | `~/.claude.json` → `projects["<path>"].mcpServers` |
| `user` scope storage | `~/.claude.json` → top-level `mcpServers` |
| `project` scope storage | `.mcp.json` at repo root (committed) |
| plugin scope storage | `.mcp.json` at the plugin's own root |
| Never hand-edit | `~/.claude.json` (`local` and `user` scope both live here) |
| List / inspect | `claude mcp list`, `claude mcp get <name>` |
| Remove | `claude mcp remove <name> [-s <scope>]` |
| OAuth login/logout | `claude mcp login <name> [--no-browser]`, `claude mcp logout <name>` (v2.1.186+) |
| Bulk-approve project servers | `enableAllProjectMcpServers: true` |
| Per-server approve/reject | `enabledMcpjsonServers: [...]`, `disabledMcpjsonServers: [...]` |
| What those three keys do **not** cover | `local`- or `user`-scope registrations in `~/.claude.json` |
| Unapproved project server state | `⏸ Pending approval` in `claude mcp list` / `claude mcp get` |

## Self-test

1. What three things can an MCP server register, and which of them is not a "tool"?
<details><summary>Answer</summary>Tools, resources, and prompts. Resources are named, retrievable content the agent can pull in; prompts are server-supplied prompt templates. Neither is a tool, though both arrive over the same connection and registration.</details>

2. Why does `stdio` fail with `ENOENT` if you hand `claude mcp add` a bare URL?
<details><summary>Answer</summary>`stdio` is the default transport when `--transport` is omitted, so Claude Code tries to spawn the value as a local command via `posix_spawn`. A URL is not an executable on `PATH`, so the spawn fails with `ENOENT`. The fix is `--transport http` or `--transport sse`.</details>

3. Where does a `user`-scope MCP registration live on disk, and who else can see it?
<details><summary>Answer</summary>The top-level `mcpServers` key inside `~/.claude.json`. Only you see it, but across every project you open — unlike `local` scope, which is scoped to one project's entry in the same file.</details>

4. Why is it safe to say "never hand-edit `~/.claude.json`" and still true that `claude mcp add -s user` writes to it constantly?
<details><summary>Answer</summary>Because the tool is writing its own state file for you, the same relationship established in §1.1.4 for sign-in state and trust decisions. The rule against hand-editing is about opening the file yourself and changing JSON by hand, not about the CLI commands whose entire job is to manage that file on your behalf.</details>

5. A repository's `.mcp.json` declares a new server. What has to happen before Claude Code connects to it, and why?
<details><summary>Answer</summary>It has to be approved — interactively, via `enableAllProjectMcpServers`, or by name via `enabledMcpjsonServers` — because a committed `.mcp.json` is something any contributor with a pull request can add to, and a server registration is at least as capable a grant as a permission `allow` rule. This is the same workspace-trust asymmetry §1.4.32 already established for `allow` rules and `additionalDirectories`, applied to MCP.</details>

6. What exactly does `enabledMcpjsonServers` gate, and what does it not gate?
<details><summary>Answer</summary>It gates approval for servers declared in a project's `.mcp.json` only. It has no effect on `local`- or `user`-scope registrations living in `~/.claude.json` — those connect (or don't) independent of this key entirely.</details>

7. In the sdlc-harness incident, what did toggling `enabledMcpjsonServers` actually change, and what stayed the same?
<details><summary>Answer</summary>It changed only what `select-handbook.sh`'s resolver believed about which handbook was "selected." The actual live MCP server — `igmarkets-handbook` or `igtrading-handbook`, registered at user scope via `claude mcp add --scope user` — stayed exactly as it was, because the key has no reach into user-scope registrations. The two could disagree, so a playbook could invoke a skill prefixed for one handbook against a session where only the other's tools existed.</details>

8. Between `http` and `sse` for a new remote registration in v2.1.2xx, which should you pick, and why?
<details><summary>Answer</summary>`http` — it is the current, recommended transport using the newer Streamable-HTTP framing, and real providers (Atlassian's hosted MCP endpoint among them) are actively retiring `sse` rather than adopting it further.</details>

## Open questions

None.

---

**Leaves covered:** 2.4.1–2.4.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-56 in the next file draws the cost, and D-13 in `ground-zero/03` drew the tool categories
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 435
