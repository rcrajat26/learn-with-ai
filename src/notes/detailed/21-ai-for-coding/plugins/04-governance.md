# 21 AI for Coding — plugin governance — INTERMEDIATE (§2.5.13–2.5.15)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [marketplaces and cross-marketplace dependencies](03-marketplaces-and-dependencies.md) · Next: [three real plugin files, and converting a `.claude/` tree](05-cases-and-conversion.md)

The previous file answered where a plugin comes from and how a dependency crosses from one
marketplace's catalog into another's. This file answers two different questions that only make sense
once a plugin ecosystem exists at all: how does a developer get a plugin onto their own machine
*without* a marketplace, and how does an organization stop the plugin channel — and every other
extension channel — from becoming an unreviewed side door into what runs on an engineer's laptop.

## §2.5.13 `claude plugin init`: a plugin that needs no marketplace `[DOC]` `[VERSION]`

**Mental model.** Every plugin so far in this set has had a `source` field pointing somewhere — a
relative path inside a marketplace repo, a `git-subdir` object, a plain URL. `claude plugin init`
skips all of that. It scaffolds a plugin directly inside the personal skills directory the reader
already has, `~/.claude/skills/`, and Claude Code auto-loads whatever lives there on the next session
start. There is no catalog entry, no `marketplace add`, no `install` step — the plugin's "source" is
just its own presence on disk in a folder Claude Code already watches.

**Why it exists.** Sharing a plugin needs a marketplace; *developing* one does not, and forcing a
marketplace detour onto every plugin author before they can even try their own skill against a real
session is friction with no payoff. `--plugin-dir` (§2.5.12) solves the same "try it without a
marketplace" problem for a single session, but it has to be typed on every launch. A skills-directory
plugin is the persistent version of the same idea: scaffold once, and it loads automatically from then
on, the same way a hand-written entry under `~/.claude/skills/` always has.

**How it works.** Verified against the installed v2.1.251 binary and the "Develop a plugin in your
skills directory" section of the `plugins` documentation page:

```bash
claude plugin init mvn-test-runner
```

This creates `~/.claude/skills/mvn-test-runner/` containing a `.claude-plugin/plugin.json` manifest
and a starter `SKILL.md` — the same two artefacts a marketplace-distributed plugin ships, just placed
directly under the personal skills root instead of inside a marketplace-resolved cache directory. On
the **next** session — not the one that ran `init` — it loads as `mvn-test-runner@skills-dir`, and
`@skills-dir` is a synthetic marketplace name Claude Code assigns to every plugin scaffolded this way,
so it shows up in `claude plugin list` exactly like a real install, just with `skills-dir` where a real
marketplace name would sit.

**Code.** The resulting layout is indistinguishable in shape from a marketplace plugin — the same
`.claude-plugin/plugin.json`, the same `skills/` convention if it grows past one skill:

```json
{
  "name": "mvn-test-runner",
  "description": "Runs the Maven test suite for the module under the cursor and summarizes failures.",
  "version": "0.1.0",
  "author": {
    "name": "IG Group"
  }
}
```

**Gotcha.** `[VERSION]` A skills-directory plugin loads only "on the next session" — running `claude
plugin init` and then trying `/mvn-test-runner:hello` in the *same* session fails silently by omission,
the same category of surprise as any other plugin change that needs `/reload-plugins`, except here
even a reload does not help: the auto-load scan that discovers `~/.claude/skills/<name>/` as a plugin
runs at startup, not on reload, so a fresh `claude` launch is the only thing that picks it up.

> A skills-directory plugin is a plugin whose install mechanism is simply existing under
> `~/.claude/skills/`; `claude plugin init` scaffolds one, and it auto-loads as `<name>@skills-dir` on
> the next session with no marketplace and no install step.

## §2.5.14 The governance surface: seven keys, all managed-only but one `[DOC]`

**Mental model.** Every plugin mechanism covered in this set so far — `plugin.json`, namespacing,
marketplaces, cross-marketplace trust, `--plugin-dir`, skills-directory plugins — is written from the
point of view of a developer choosing what runs on their own machine. This section flips the point of
view: an organization deciding what its engineers are *allowed* to choose. Seven settings keys carry
that decision, and six of the seven only mean anything when written into **managed settings** — the
settings file the reader met at §1.2.2, deployed by an organization and outranking every other layer,
including the command line.

**Why it exists.** A marketplace add, a plugin install, a `--plugin-dir` flag, and an `enabledPlugins`
toggle are all developer-initiated actions. Left alone, a security-conscious organization has no lever
over any of them beyond asking nicely. These seven keys are that lever: which marketplaces exist at
all, which plugins are actually turned on, whether the sideload flags even parse, and — the subject of
§2.5.15 — whether *any* extension channel other than a reviewed plugin can contribute anything at all.

**How it works.** Re-verified against the `settings-reference` documentation page immediately before
writing this table:

| Key | What it locks | Scope | What a developer sees when they hit it |
|---|---|---|---|
| `enabledPlugins` | Turns individual plugins on or off, per plugin id (`<name>@<marketplace>`), independent of whether it is installed | Any settings file (managed, user, project, local) | A plugin they installed shows in `claude plugin list` but its skills, agents, hooks and MCP servers do not load — `enabled: false` in `claude plugin list --json`, with no error, because being installed and being enabled are separate states |
| `blockedMarketplaces` | Blocks specific marketplace sources by name or URL pattern for the whole organization | Managed only | `claude plugin marketplace add` for a blocked source fails outright, naming the block rather than a network or auth error |
| `extraKnownMarketplaces` | Pre-registers marketplaces for a repository or an organization, so engineers do not each run `marketplace add` themselves | Any settings file | A marketplace appears already added the first time an engineer opens the project — no `marketplace add` step, no prompt |
| `strictKnownMarketplaces` | Allow-lists the *only* marketplace sources a user is permitted to add or install from at all | Managed only | `claude plugin marketplace add` for anything not on the allow-list fails, even if the source is reachable and otherwise valid — a personal fork of a marketplace repo included |
| `strictPluginOnlyCustomization` | Blocks skills, agents, hooks and MCP servers from user and project sources, leaving plugin (and managed) sources as the only ones that load — §2.5.15 | Managed only | A hand-written `.claude/skills/`, `.claude/agents/`, `.claude/settings.json` hook, or project `.mcp.json` entry stops loading — no error at the point of writing it, just silent absence from `/context` and `/plugin` |
| `disableSideloadFlags` | Rejects the CLI flags that sideload plugins, subagents, and MCP servers at launch — `--plugin-dir`, `--plugin-url`, `--agents`, `--mcp-config` and siblings | Managed only | `claude --plugin-dir ./mvn-test-runner` starts the session but the flag is refused; the plugin the flag named never loads, and `--strict-mcp-config`-style enforcement applies uniformly rather than per-flag |
| `pluginTrustMessage` | Appends organization-authored text to the trust warning Claude Code shows before a plugin's first run | Managed only | The standard "this plugin can run commands on your machine" prompt gains an extra line — a link to an internal review process, a contact, a policy reference — before the engineer can accept |

**Code.** A managed settings object using all seven keys together — the shape an enterprise deployment
actually ships, not a fragment of one:

```json
{
  "enabledPlugins": {
    "sdlc-harness@sdlc-harness": true,
    "readonly-reviewer@ig-superclaude": true
  },
  "blockedMarketplaces": ["claude-community"],
  "extraKnownMarketplaces": {
    "sdlc-harness": {
      "source": { "source": "github", "repo": "ig-group/sdlc-harness" }
    },
    "ig-superclaude": {
      "source": { "source": "github", "repo": "ig-group/ig-superclaude-framework" }
    }
  },
  "strictKnownMarketplaces": ["sdlc-harness", "ig-superclaude", "claude-plugins-official"],
  "strictPluginOnlyCustomization": {
    "agents": true,
    "hooks": true,
    "mcp": true,
    "skills": true
  },
  "disableSideloadFlags": true,
  "pluginTrustMessage": "Internal plugins are pre-reviewed. For anything else, file a request at go/plugin-review before installing."
}
```

**Gotcha.** `enabledPlugins` is the one key in the table that is *not* managed-only, and that
asymmetry is deliberate rather than an oversight: it is the toggle an individual engineer uses every
day to turn a plugin off temporarily without uninstalling it, so it stays writable at every scope. The
other six exist specifically so that an organization's choice cannot be quietly overridden by a
project's own `.claude/settings.json` or a developer's `--flag` — and per the precedence order at
§1.2.2, managed settings outrank the command line, so none of the managed-only six can be flagged away
no matter how the CLI invocation is composed.

> Seven settings keys govern plugins and marketplaces at the organizational level; six of the seven —
> every one except the always-writable `enabledPlugins` — only take effect when written into managed
> settings, which the precedence chain at §1.2.2 places above every other layer including the command
> line.

## §2.5.15 `strictPluginOnlyCustomization`: the enterprise endgame `[DOC]`

**Mental model.** Everything the reader spent PART 1 learning to write by hand under `.claude/` —
skills in `.claude/skills/`, agents in `.claude/agents/`, hooks in `settings.json`, MCP servers in
`.mcp.json` — is a **side door**: a way to extend what the agent can do that bypasses the plugin
system's review and versioning entirely. `strictPluginOnlyCustomization` is the setting that closes
every one of those side doors at once, for the whole organization, leaving exactly one channel open:
a plugin, which by definition came from a registered, name-known marketplace and carries a version
number.

**Why an org reaches for it.** A plugin has provenance — a marketplace entry, a `plugin.json` version,
optionally a pinned commit SHA in a curated catalog (§2.5.10's `claude-plugins-community`, pinned to a
SHA that CI bumps). A hand-written `.claude/hooks` entry in a cloned repository, or a personal skill
under `~/.claude/skills/`, has none of that: nobody reviewed it, nobody versioned it, and it can run
arbitrary shell the moment its owning event fires. For an organization whose threat model includes "an
engineer's cloned repository ships a hook that exfiltrates credentials on the next `PostToolUse`
event," restricting every extension channel to the one path that goes through marketplace review is
not a preference, it is the control.

**How it works.** Re-verified against the `settings-reference` documentation page: the top-level key
"blocks skills, agents, hooks, and MCP servers from user and project sources," and each of its four
sub-keys — `.agents`, `.hooks`, `.mcp`, `.skills` — independently locks *one* of those four channels to
plugin sources, so an organization can, for instance, lock down hooks and MCP servers while still
letting engineers write their own personal skills:

```json
{
  "strictPluginOnlyCustomization": {
    "agents": false,
    "hooks": true,
    "mcp": true,
    "skills": false
  }
}
```

Setting the key to a bare `true` rather than an object locks all four channels at once — the
per-channel object form exists specifically so the lock does not have to be all-or-nothing.

![D-61 — `strictPluginOnlyCustomization` closes the side doors. With the lock on, only the plugin channel is live.](../diagrams/D-61-strict-plugin-only-customization.svg)

**D-61** — `strictPluginOnlyCustomization` closes the side doors. With the lock on, only the plugin
channel is live.

D-61 draws four extension channels — skills, agents, hooks, MCP — each fed by three possible sources:
user, project, plugin. With the lock off, all twelve source-to-channel edges are live: any of the four
channels can be populated from any of the three sources, which is the default, ungoverned state every
example in PART 1 and PART 2 has assumed so far. With the lock on, the user and project edges go dead
on every channel at once, and only the four plugin edges remain — twelve edges collapse to four, and
the ones that survive are, by construction, the ones that came from a reviewed, versioned source.

**Insight.** This is the same restriction-by-source pattern the reader has already met once, applied
to a narrower slice. `allowManagedHooksOnly`, at §2.3.19, restricts hooks specifically to organization-
deployed sources; `strictPluginOnlyCustomization.hooks` restricts the same channel to plugin sources
instead, and the two are not the same allow-list even though both are "restrict hooks by where they
came from." The full family of `allowManaged*Only` keys, and D-68's picture of how they compose with
this lock, is `governance/02-the-lock-family.md`'s material — the shape to hold here is only that
source-based restriction is a recurring tool in this settings surface, not a one-off invented for
plugins.

**Gotcha.** The lock has a real cost, and stating it as free would be dishonest: with
`strictPluginOnlyCustomization` on, a developer's own perfectly good local skill — one they wrote
correctly, that does nothing suspicious, that has been reliable for months under `~/.claude/skills/` —
stops loading with no error at the point of writing it, only a silent absence from `/context` and from
`/plugin`. The friction lands on that developer, not on whatever threat the org was actually worried
about; the org is trading every engineer's ability to write a quick personal skill or hook for the
guarantee that nothing unreviewed can extend the agent. That trade is the right one for some
organizations and the wrong one for others, and the setting does not make that judgment call for you —
it only enforces whichever call was made.

> `strictPluginOnlyCustomization` blocks skills, agents, hooks and MCP servers from user and project
> sources — as a bare `true` for all four channels or per-channel via `.agents`/`.hooks`/`.mcp`/
> `.skills` — so that only reviewed, versioned plugins can extend the agent, at the cost of breaking
> every hand-written local extension an engineer already relies on.

## Pitfalls

- **Belief:** running `claude plugin init` makes the new skills-directory plugin available
  immediately, the way editing a hook in `settings.json` takes effect on the next tool call.
  **Surprising outcome:** `/my-plugin:hello` in the same session that ran `init` fails, and even
  `/reload-plugins` does not fix it. **What actually gets the guarantee:** start a new `claude`
  session; the auto-load scan for `~/.claude/skills/<name>/` as a plugin runs at startup only.
  **Why people believe it:** most other plugin and skill edits in this topic are picked up by
  `/reload-plugins` without a restart, so the one that is not reads as an inconsistency rather than a
  documented exception.
- **Belief:** `strictPluginOnlyCustomization: true` is a clean, no-cost hardening step, since it only
  stops "unreviewed" things from running. **Surprising outcome:** an engineer's own working personal
  skill or hook silently stops loading, with no error at the point of writing it and no message
  pointing at the lock as the cause. **What actually gets the guarantee:** treat the lock as a
  deliberate trade — migrate any skill, agent, hook or MCP server the organization still wants into a
  plugin before turning the lock on, or scope it to the sub-keys (`.agents`, `.hooks`, `.mcp`,
  `.skills`) that actually need it. **Why people believe it:** the setting's name and description talk
  about what it blocks, not about what an engineer loses, so the cost side of the trade is easy to
  skip past when only reading the settings-reference entry.

## Cheat sheet

| Question | Answer |
|---|---|
| Scaffold a plugin with no marketplace | `claude plugin init <name>` → `~/.claude/skills/<name>/`, loads as `<name>@skills-dir` next session |
| When does a skills-directory plugin load | Next session start only — not the current session, not on `/reload-plugins` |
| Toggle a plugin on/off without uninstalling | `enabledPlugins` — the one governance key writable at every scope |
| Block a marketplace source org-wide | `blockedMarketplaces` (managed only) |
| Pre-register a marketplace for everyone | `extraKnownMarketplaces` (any scope) |
| Allow-list the *only* marketplaces users may add | `strictKnownMarketplaces` (managed only) |
| Block skills/agents/hooks/MCP from user+project sources | `strictPluginOnlyCustomization` (managed only), bare `true` or per-channel object |
| Its four sub-keys | `.agents`, `.hooks`, `.mcp`, `.skills` |
| Reject sideload CLI flags org-wide | `disableSideloadFlags` (managed only) |
| Add org text to the plugin trust prompt | `pluginTrustMessage` (managed only) |
| Outranks the command line? | Yes — managed settings sit above the command line at §1.2.2, so none of the six managed-only keys can be flagged away |
| Related but distinct hook-only restriction | `allowManagedHooksOnly` (§2.3.19) — full `allowManaged*Only` family at `governance/02-the-lock-family.md` |

## Self-test

1. What is the one difference between how `--plugin-dir` and `claude plugin init` make a plugin
   available, given that both skip marketplaces entirely?
<details><summary>Answer</summary>
`--plugin-dir` loads the plugin for the current session only and must be passed on every launch.
`claude plugin init` scaffolds the plugin under `~/.claude/skills/<name>/` and it auto-loads
persistently, as `<name>@skills-dir`, starting from the next session.
</details>

2. You run `claude plugin init mvn-test-runner` and immediately try `/mvn-test-runner:hello` in the
   same session. It fails. You then run `/reload-plugins`. Does that fix it?
<details><summary>Answer</summary>
No. The auto-load scan that discovers a skills-directory plugin runs at session startup only, not on
`/reload-plugins`. A new `claude` session is required.
</details>

3. Which one of the seven plugin governance keys is not managed-only, and why is that the exception
   rather than the rule?
<details><summary>Answer</summary>
`enabledPlugins`. It is the everyday per-plugin on/off toggle an individual engineer uses, so it stays
writable at every settings scope; the other six exist specifically to prevent a project or a CLI flag
from overriding an organization's choice, which requires managed-only scope.
</details>

4. An organization sets `strictPluginOnlyCustomization: { "hooks": true, "mcp": true }` and leaves
   `agents` and `skills` at their default. What still works, and what stops?
<details><summary>Answer</summary>
Hooks and MCP servers from user and project sources stop loading — only plugin-sourced hooks and MCP
servers remain live. Agents and skills are unaffected by this key and continue to load from user,
project, and plugin sources as before, since only the two named sub-keys were set.
</details>

5. Per the precedence order established at §1.2.2, can a developer disable
   `strictPluginOnlyCustomization` or `disableSideloadFlags` by passing a different `--settings` file
   on the command line?
<details><summary>Answer</summary>
No. Both keys are managed-only, and managed settings outrank the command line in the precedence chain
— the command line cannot override a managed setting no matter what file it points at.
</details>

6. A developer's personal skill under `~/.claude/skills/checklist-refresh/` stops appearing in
   `/context` after an organization deploys `strictPluginOnlyCustomization: true`. What error message
   should they expect to see explaining why?
<details><summary>Answer</summary>
None. The lock produces silent absence, not an error — the skill simply stops loading with nothing in
`/context` or `/plugin` pointing at the lock as the cause. This is the cost the leaf calls out
explicitly: the friction is invisible at the point it lands.
</details>

7. Name the settings key from §2.3.19 that restricts hooks by source in the same spirit as
   `strictPluginOnlyCustomization.hooks`, and state why they are not the same allow-list.
<details><summary>Answer</summary>
`allowManagedHooksOnly`. It restricts hooks to organization-deployed sources specifically;
`strictPluginOnlyCustomization.hooks` restricts the same channel to plugin sources instead — both are
"restrict hooks by origin," but they name different permitted origins.
</details>

## Open questions

None.

---

**Leaves covered:** 2.5.13–2.5.15 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-61
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 319
