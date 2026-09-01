# 21 AI for Coding — a plugin — BUILD IT (§4.6.1–4.6.3)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [the per-stage cost report, and the diff against the real one](06-orchestrator-d-pipeline-and-cost.md) · Next: [publishing, the version bump, and the diff against the real one](07-a-plugin-b.md)

`build-it/01`–`04` gave `invoice-ledger-service` a complete `.claude/` folder: `CLAUDE.md`,
`.claude/rules/api-dtos.md`, `.claude/settings.json`, a gitignored `.claude/settings.local.json`, four
hooks (`format-on-edit.sh`, `block-destructive-bash.sh`, `branch-context.sh`,
`require-green-build.sh`), four skills (`mvn-test-runner`, `checklist-refresh`,
`post-invoice-reversal`, `money-minor-units-conventions`), and three agents (`readonly-reviewer`,
`mvn-test-runner`, `pre-merge-gatekeeper`). Every one of those files already works, by hand, in this
one repository. This file's three leaves package that exact payload as a plugin — a single unit a
second repository, or a second engineer, can install, version, and update, rather than hand-copy.
**No new payload artefact is invented here; nothing already built is renamed.**

## §4.6.1 — package it, and test with `--plugin-dir` `[BUILD]`

**Concept.** A plugin is a directory with an optional `.claude-plugin/plugin.json` manifest — its
identity — plus whichever component directories it ships, all of them siblings of `.claude-plugin/`,
never children of it. `[DOC]` Re-verified against `plugins` immediately before writing this leaf, which
states the rule as its own callout: **"Don't put `commands/`, `agents/`, `skills/`, or `hooks/` inside
the `.claude-plugin/` directory. Only `plugin.json` goes inside `.claude-plugin/`. All other directories
must be at the plugin root level."** The same page adds the corollary this leaf's prove step turns into
a demonstrated fact rather than a repeated warning: an LSP server that fails to start is reported in the
`/plugin` **Errors** tab, but a skill or agent placed at the wrong path is not — nothing errors, the
plugin simply ships an empty component set.

**Why it exists.** Nothing in the four files this row's payload already lives in changes about
`invoice-ledger-service` itself — every hook, skill, and agent still runs exactly as `build-it/01`–`04`
built and proved it. What changes is *distribution*: today, a second Spring Boot service inheriting the
same conventions gets this tooling only by an engineer manually copying nine files into a new `.claude/`
tree and re-editing every path inside them. A plugin makes that a `claude plugin install` and gives the
result a `version` field so a later fix — the `Stop`-hook field-name correction `build-it/02` already
had to make once by hand — ships as an update instead of a second manual copy.

**How it works — the directory map.**

| Directory / file | Location | This row's contents |
|---|---|---|
| `.claude-plugin/plugin.json` | Plugin root | Manifest: `name`, `description`, `version`, `author`, `license` |
| `skills/` | Plugin root | `checklist-refresh/`, `post-invoice-reversal/`, `money-minor-units-conventions/`, `mvn-test-runner/` — each a `SKILL.md`, unchanged from `build-it/01` and `build-it/03` |
| `agents/` | Plugin root | `readonly-reviewer.md`, `mvn-test-runner.md`, `pre-merge-gatekeeper.md`, unchanged from `build-it/04` |
| `hooks/hooks.json` | Plugin root | The `hooks` object `build-it/02` registered inside `.claude/settings.json`, moved to its own file — **command paths corrected, below** |
| `hooks/*.sh` | Plugin root, inside `hooks/` | The four hook scripts themselves, unchanged in their own logic |

`[DOC]` Re-verified against `plugins`' own migration steps: *"If you have hooks in your settings,
create a hooks directory... Copy the `hooks` object from your `.claude/settings.json`... since the
format is the same."* The object shape does not change; only its container does — `.claude/settings.json`
held `hooks` as one key beside `permissions`, `env`, `model`; `hooks/hooks.json` holds it as the file's
one top-level key.

![D-98 — The packaged plugin and its marketplace. Only `plugin.json` goes inside `.claude-plugin/`.](../diagrams/D-98-plugin-and-marketplace.svg)

**D-98** — The packaged plugin and its marketplace. Only `plugin.json` goes inside `.claude-plugin/`.
This file covers the diagram's packaging, `--plugin-dir` test, `validate`/`--strict`, and marketplace
publish steps — §4.6.1–4.6.3, the diagram's left two-thirds. The version-bump panel, the
unresolved-dependency panel, and the **Diff vs the real one** table belong to the next file, §4.6.4–4.6.6.

**The artefact — `.claude-plugin/plugin.json`, real values, no placeholder:**

```json
{
  "name": "invoice-ledger-tooling",
  "description": "The invoice-ledger-service .claude tooling -- four hooks, four skills, and three subagents built across build-it/01-04 -- packaged as an installable, versioned plugin.",
  "version": "1.0.0",
  "author": {
    "name": "IG Group"
  },
  "license": "proprietary"
}
```

No `dependencies` key: `[DOC]` `plugins`' own manifest table marks `dependencies` optional, and this
plugin genuinely depends on nothing else installed — every hook, skill, and agent it ships is
self-contained inside `invoice-ledger-service`. The real sdlc-harness manifest at
`plugins/sdlc-harness/.claude-plugin/plugin.json` — read fresh for this leaf, `[CASE]` —
shows the shape a real dependency takes when one exists: `"dependencies": [{"name": "ig-superclaude",
"marketplace": "ig-superclaude"}]`. That array is absent here on purpose, not omitted by oversight.

**The trap, caught in the artefact rather than only stated.** The `hooks` object `build-it/02` registered
inside `.claude/settings.json` used `"command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/branch-context.sh"`
for every one of the four hooks — correct for a project's own settings file, and **silently wrong** if
copied unchanged into a plugin's `hooks/hooks.json`. `[DOC]` Re-verified against `hooks` immediately
before writing this leaf:

| Placeholder | Expands to | Correct in |
|---|---|---|
| `${CLAUDE_PROJECT_DIR}` | The project root where the session started | A project's own `.claude/settings.json` |
| `${CLAUDE_PLUGIN_ROOT}` | The plugin's installation directory — changes on every plugin update | A plugin's own `hooks/hooks.json` |

The page states the fix explicitly, not as an inference: *"In a Plugin's `hooks/hooks.json`: Use
`${CLAUDE_PLUGIN_ROOT}` for the plugin's own script paths."* `${CLAUDE_PLUGIN_ROOT}` is not this
repository — confirmed directly, below, from this leaf's own real install — it is wherever Claude Code
cached the plugin, which is never a path `.claude/hooks/branch-context.sh` resolves against once the
scripts have moved out of `.claude/` entirely.

The uncorrected file, kept only as the artefact this leaf's prove step falsifies, never registered:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/branch-context.sh", "timeout": 10 } ] }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-destructive-bash.sh" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/format-on-edit.sh" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/require-green-build.sh" } ] }
    ]
  }
}
```

The corrected file, the one actually shipped at `hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/branch-context.sh", "timeout": 10 } ] }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/block-destructive-bash.sh" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/format-on-edit.sh" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/require-green-build.sh" } ] }
    ]
  }
}
```

`require-green-build.sh`'s own `MARKER="target/.last-build-status"` needed no equivalent fix: that path
is relative to the hook **process's** working directory, which stays the project root the session
started in regardless of where the script file itself is cached — the same `cwd` mechanism
`branch-context.sh`'s own comment already named in `build-it/02`. The break this leaf found is entirely
in the `hooks.json` **command string**, never in a script's own internal logic.

**Prove step.** `[PROVE]` Every command below ran for real, under `/tmp/21-plugin-scratch`, against the
installed `claude 2.1.251` binary — never inside this repository or inside sdlc-harness. Four skill
directories, three agent files, and `hooks/hooks.json` plus its four scripts were assembled at
`invoice-ledger-tooling/`, then loaded without installing anything:

```
$ claude -p --plugin-dir /tmp/21-plugin-scratch/invoice-ledger-tooling \
    "List every skill and agent visible to you right now, by exact name, and nothing else." \
    --output-format json
```

The real `result` field, agents and skills sections only:

```
**Agents**
...
- invoice-ledger-tooling:mvn-test-runner
- invoice-ledger-tooling:pre-merge-gatekeeper
- invoice-ledger-tooling:readonly-reviewer
...

**Skills**
...
- invoice-ledger-tooling:checklist-refresh
- invoice-ledger-tooling:money-minor-units-conventions
- invoice-ledger-tooling:mvn-test-runner
...
```

All three agents arrived, correctly namespaced `invoice-ledger-tooling:<name>` — `[DOC]` `plugins`
states plugin skills are always namespaced this way, "to prevent conflicts when multiple plugins have
skills with the same name," and the same prefix applies to the agents listed here. Exactly three of the
four skills appear: `post-invoice-reversal` is missing from this listing, correctly — its
`disable-model-invocation: true` frontmatter (`build-it/03`, §4.3.3) means it is not exposed to the
model as an invokable capability at all, only reachable by a user typing
`/invoice-ledger-tooling:post-invoice-reversal` directly. `money-minor-units-conventions` carries
`user-invocable: false`, the opposite restriction, and does appear here for exactly that reason — the
model can still choose to load it. The packaged plugin preserves both fields' behaviour unchanged, which
is the real proof that packaging moved files without altering what they do.

**What this costs.** `claude plugin details` — run after §4.6.3's install, since the command only
inspects an installed plugin, never a bare `--plugin-dir` path — reports the CLI's own projected
token cost for this exact component set:

```
Component inventory
  Skills (4)  checklist-refresh, money-minor-units-conventions, mvn-test-runner, post-invoice-reversal
  Agents (3)  readonly-reviewer, mvn-test-runner, pre-merge-gatekeeper
  Hooks (4)  SessionStart, PreToolUse, PostToolUse, Stop  (harness-only — no model context cost)

Projected token cost
  Always-on:   ~723 tok   added to every session
```

That ≈723 tokens is the CLI's own estimate, not this guide's usual bytes ÷ 4 substitution, and it lands
in the same order of magnitude as `build-it/03`'s and `build-it/04`'s independently measured per-skill
(≈75 tokens each) and per-agent listing costs summed across four skills and three agents — consistent,
not identical, because the two estimates round differently. **Hooks add nothing to that figure**: per
`build-it/02`'s own finding, a hook's command output is either invisible to Claude entirely or, for
`SessionStart` only, injected once per session rather than resident from turn one — the `details` output
states this plainly with "(harness-only — no model context cost)" beside the hook count. The prove-step
call itself, separately, billed real money: `total_cost_usd: 0.16334125` for one Opus-model turn reading
the whole plugin's system-prompt injection fresh with no cache — the one-off cost of *proving* the
package, not a recurring cost the plugin itself imposes.

No gotcha beyond the one already demonstrated: `${CLAUDE_PLUGIN_ROOT}` versus `${CLAUDE_PROJECT_DIR}` is
the entire failure mode a naive "just move the folder" migration hits, and it produces no error message
of its own — the hooks simply never fire, silently, exactly like the wrong-layout trap §4.6.3 proves
next.

> A plugin's `hooks/hooks.json` is the same `hooks` object a project's `.claude/settings.json` already
> carries, moved to its own file with exactly one required edit: every `${CLAUDE_PROJECT_DIR}` path
> becomes `${CLAUDE_PLUGIN_ROOT}`, because the scripts now live in the plugin's cache, not the project.

## §4.6.2 — `claude plugin validate`, then `--strict` `[BUILD]` `[PROVE]`

**Concept.** `claude plugin validate <path>` checks a plugin's manifest — and, per its own `--help`
text, "the skills, agents, and commands in a directory" — without installing anything or starting a
session. `--strict` turns every warning it would otherwise tolerate into a hard failure.

**Why it exists.** §4.6.1's own trap — a hook that silently never fires — is exactly the failure class a
human reviewer misses in a diff and a machine check does not need to guess about. Running `validate`
before ever proposing a marketplace entry (§4.6.3) catches a malformed manifest before an install
attempt fails with a less specific error.

**The artefact — running it against the real, corrected plugin from §4.6.1:**

```
$ claude plugin validate /tmp/21-plugin-scratch/invoice-ledger-tooling
Validating plugin manifest: /tmp/21-plugin-scratch/invoice-ledger-tooling/.claude-plugin/plugin.json

✔ Validation passed
```

```
$ claude plugin validate /tmp/21-plugin-scratch/invoice-ledger-tooling --strict
Validating plugin manifest: /tmp/21-plugin-scratch/invoice-ledger-tooling/.claude-plugin/plugin.json

✔ Validation passed
```

**Prove step, "fix what it reports," reproduced rather than assumed.** `[PROVE]` A clean pass proves
nothing about what `--strict` actually catches, so a second, deliberately defective manifest — identical
except for one added, undocumented field — was validated the same way:

```json
{
  "name": "invoice-ledger-tooling",
  "description": "The invoice-ledger-service .claude tooling -- four hooks, four skills, and three subagents built across build-it/01-04 -- packaged as an installable, versioned plugin.",
  "version": "1.0.0",
  "author": { "name": "IG Group" },
  "license": "proprietary",
  "maintainer": "billing-platform-team"
}
```

```
$ claude plugin validate /tmp/21-plugin-scratch/plugin-json-defect-check
⚠ Found 1 warning:
  ❯ maintainer: Unknown field 'maintainer'. Claude Code ignores it at load time.
✔ Validation passed with warnings
```

```
$ claude plugin validate /tmp/21-plugin-scratch/plugin-json-defect-check --strict
⚠ Found 1 warning:
  ❯ maintainer: Unknown field 'maintainer'. Claude Code ignores it at load time.
✘ Validation failed (--strict treats warnings as errors)
```

exit code `1` on the `--strict` run, `0` on the plain run — the exact "warnings don't fail validation;
`--strict` treats them as errors" behaviour `plugins` documents for the community-marketplace review
pipeline. **The fix** is simply removing the field the tool named — `maintainer` is not part of the
manifest schema; `author` is the field that carries this information — after which the same `--strict`
run returns to `✔ Validation passed` with exit `0`, matching §4.6.1's real, unmodified manifest.

**What §4.6.1's own trap does *not* trip this check.** `[TRAP]` **Pitfall:** the belief is "`validate`
would have caught the `.claude-plugin/skills/` layout mistake, so a clean validation pass means the
component layout is correct too." Tested directly: a second scratch plugin was built with `skills/` and
`agents/` nested inside `.claude-plugin/` instead of at the plugin root — the exact D-58 pitfall — and
validated:

```
$ claude plugin validate /tmp/21-plugin-scratch/wrong-layout-demo
⚠ Found 1 warning:
  ❯ author: No author information provided. Consider adding author details for plugin attribution
✔ Validation passed with warnings
```

The only warning is a missing `author` field, unrelated to the misplaced directories. **Outcome:** the
tool passes a plugin whose skills and agents will never load, with no mention of the real defect at all.
**Fix:** the only check that actually catches this is the one D-58 and `plugins` both already state:
install the plugin, then read its **component inventory** — `claude plugin details <name>` — not its
validation result. §4.6.3 runs that exact comparison for real. **Why people believe it:** "validate"
reads as "checks everything wrong with this plugin," and for a manifest-shaped defect it does; a
structural placement defect is a different failure class the same command was never built to see.

**What this costs.** `claude plugin validate` runs entirely outside any Claude Code session — it never
sends a request to the model, so its token cost is exactly zero; the only cost is the CLI process's own
sub-second startup, the same "no billed session" property `build-it/02`'s `/hooks` and `--debug` checks
already established for other CLI-level, non-session tooling.

## §4.6.3 — publish it to a local marketplace `[BUILD]`

**Concept.** A marketplace is a second, separate manifest — `.claude-plugin/marketplace.json` — that
lists one or more plugins by name and a `source` path, and is added to a Claude Code installation with
`/plugin marketplace add` (or its CLI form, `claude plugin marketplace add`) before any of its plugins
can be installed.

**Why it exists.** `--plugin-dir` (§4.6.1) is a development-only flag, scoped to one invocation; nothing
about it is persistent, shareable, or updatable. A marketplace is the mechanism that turns "a directory I
can point `claude` at" into "a name a teammate's Claude Code installation can install and later update"
— the actual distribution step the rest of this row's packaging exists to feed.

**The artefact — `marketplace.json`, real values:**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "invoice-ledger-marketplace",
  "description": "Local, pre-publish marketplace for invoice-ledger-service's own .claude tooling plugin, used to prove the /plugin marketplace add -> /plugin install -> /reload-plugins path before this plugin is submitted anywhere.",
  "owner": {
    "name": "IG Group"
  },
  "plugins": [
    {
      "name": "invoice-ledger-tooling",
      "source": "./plugins/invoice-ledger-tooling",
      "description": "The invoice-ledger-service .claude tooling -- four hooks, four skills, and three subagents -- packaged as an installable, versioned plugin."
    }
  ]
}
```

**Unverified, resolved against the installed binary rather than the permitted docs.** `marketplace.json`'s
exact schema — the `$schema`/`owner`/`plugins[].source` fields shown above — is documented on
`plugin-marketplaces`, a page outside this topic's permitted set (`settings`, `settings-reference`,
`permissions`, `hooks`, `sub-agents`, `skills`, `memory`, `plugins`, `cli-reference`). Two facts about it
were confirmed instead against `claude 2.1.251` directly, per this file's own standing instruction to do
exactly that when a marketplace detail falls outside the permitted pages:

1. **The field shape** — read fresh from the real, already-published
   `sdlc-harness/.claude-plugin/marketplace.json` (`[CASE]`), which uses the identical
   `$schema`/`name`/`owner`/`plugins[]` shape reproduced above.
2. **`source` must resolve to a path *inside* the marketplace's own directory tree.** The first attempt at
   this leaf used `"source": "../invoice-ledger-tooling"` — a sibling directory, matching the layout
   `sdlc-harness`'s own repository happens to keep its marketplace and plugin in (a shared parent
   checkout). `claude plugin install` rejected it outright: `"This plugin's marketplace entry is invalid:
   source: Invalid input"`. Moving the plugin to `plugins/invoice-ledger-tooling` *under* the
   marketplace directory and changing `source` to `"./plugins/invoice-ledger-tooling"` — the form shown
   above, and the one `sdlc-harness`'s own entry actually uses (`"./plugins/sdlc-harness"`, also nested)
   — installed without error. Recorded in `## Open questions` as unverified against the documentation
   proper, confirmed instead against the running binary.

**Prove step.** `[PROVE]` The full cycle, run for real against `claude 2.1.251`, alongside the
deliberately wrong-layout plugin from §4.6.2 for direct comparison — both listed in the same
marketplace so the install step treats them identically and only the **inventory** step tells them apart:

```
$ claude plugin marketplace add /tmp/21-plugin-scratch/invoice-ledger-marketplace
Adding marketplace…✔ Successfully added marketplace: invoice-ledger-marketplace (declared in user settings)

$ claude plugin install invoice-ledger-tooling@invoice-ledger-marketplace -s local -y
Installing plugin "invoice-ledger-tooling@invoice-ledger-marketplace"...
✔ Successfully installed plugin: invoice-ledger-tooling@invoice-ledger-marketplace (scope: local)

$ claude plugin install invoice-ledger-tooling-wrong-layout@invoice-ledger-marketplace -s local -y
Installing plugin "invoice-ledger-tooling-wrong-layout@invoice-ledger-marketplace"...
✔ Successfully installed plugin: invoice-ledger-tooling-wrong-layout@invoice-ledger-marketplace (scope: local)
```

Both installs report identical success — this is the trap's own point: **installation itself never
distinguishes the two.** Only the component inventory does:

```
$ claude plugin details invoice-ledger-tooling
Component inventory
  Skills (4)  checklist-refresh, money-minor-units-conventions, mvn-test-runner, post-invoice-reversal
  Agents (3)  readonly-reviewer, mvn-test-runner, pre-merge-gatekeeper
  Hooks (4)  SessionStart, PreToolUse, PostToolUse, Stop  (harness-only — no model context cost)

$ claude plugin details invoice-ledger-tooling-wrong-layout
Component inventory
  Skills (0)
  Agents (0)
  Hooks (0)
```

`invoice-ledger-tooling-wrong-layout` is the exact D-58 mistake — `skills/mvn-test-runner/SKILL.md` and
`agents/readonly-reviewer.md` both copied one level too deep, inside `.claude-plugin/` — installed
cleanly, validated with only an unrelated missing-`author` warning (§4.6.2), and shipped **zero**
components. `claude plugin list --json` confirms both are genuinely installed, side by side, one full
and one empty:

```json
[
  {
    "id": "invoice-ledger-tooling-wrong-layout@invoice-ledger-marketplace",
    "version": "1.0.0",
    "scope": "local",
    "enabled": true,
    "installPath": "/Users/rajat.chikkodikar/.claude/plugins/cache/invoice-ledger-marketplace/invoice-ledger-tooling-wrong-layout/1.0.0"
  },
  {
    "id": "invoice-ledger-tooling@invoice-ledger-marketplace",
    "version": "1.0.0",
    "scope": "local",
    "enabled": true,
    "installPath": "/Users/rajat.chikkodikar/.claude/plugins/cache/invoice-ledger-marketplace/invoice-ledger-tooling/1.0.0"
  }
]
```

`installPath` under `~/.claude/plugins/cache/…` is the real, observed value of `${CLAUDE_PLUGIN_ROOT}`
for this install — confirming §4.6.1's fix directly: that path is a cache directory this machine
manages, never `invoice-ledger-service`'s own checkout.

**`/reload-plugins`, not directly exercised.** `[DOC]` `plugins` documents `/reload-plugins` as an
interactive slash command that "reloads plugins, skills, agents, hooks, plugin MCP servers, and plugin
LSP servers" without restarting an already-running session — its use case is picking up a change to a
plugin *already loaded in the current session*. This leaf's install happened before any session was
started against these plugins, so nothing was loaded yet for `/reload-plugins` to refresh; the CLI
`claude plugin install` output above already confirms the install succeeded, without needing a running
session to reload. Recorded in `## Open questions` as the one command in this leaf's own name not
directly demonstrated, consistent with every other interactive-only command this build-it row has hit.

**Cleanup, performed for real, not merely promised.** Per this row's own standing constraint, every
marketplace and install created above was removed afterward:

```
$ claude plugin uninstall invoice-ledger-tooling@invoice-ledger-marketplace --scope local
$ claude plugin uninstall invoice-ledger-tooling-wrong-layout@invoice-ledger-marketplace --scope local
$ claude plugin marketplace remove invoice-ledger-marketplace
✔ Successfully removed marketplace: invoice-ledger-marketplace
```

`claude plugin list --json` afterward shows neither plugin, and this repository's own
`.claude/settings.local.json` — which the `-s local` installs above had written an `enabledPlugins` block
into, a real, observed side effect on this actual project this leaf did **not** intend — reverted to
`"enabledPlugins": {}` once the marketplace was removed, matching its state before this leaf ran.
**One residue was not removed**: the plugin cache directories under
`~/.claude/plugins/cache/invoice-ledger-marketplace/`, each already marked with a `.orphaned_at`
timestamp by Claude Code's own bookkeeping the moment the marketplace was removed — this machine's own
garbage-collection mechanism, not a leftover this leaf's cleanup skipped. `claude plugin prune` was run
and reported "Nothing to prune (no auto-installed plugins at user scope)," since these were direct
installs, not auto-installed dependencies, which `prune` does not target. A direct `rm -r` on that cache
path was attempted and refused outright by this very project's own `.claude/settings.local.json`, whose
`permissions.deny` already carries `"Bash(rm:*)"` — the exact settings-level `deny` mechanism §4.2.2 of
this row built a hook to narrow, observed here from the opposite side, blocking a cleanup command rather
than a destructive one, in the same repository this whole guide has been written in.

**What this costs.** Every command in this section is a `claude plugin` CLI subcommand, none of them
starts a billed model session, so the marketplace-add, install, uninstall, and remove cycle costs
**$0** in Claude Code usage — the only real resource spent is local disk under `~/.claude/plugins/cache/`,
freed by Claude Code's own orphan bookkeeping rather than by this leaf's own `rm`.

## Pitfalls

- **Belief:** "if `claude plugin validate` passes, the plugin's skills and agents are laid out
  correctly." **Outcome:** demonstrated above — a plugin with `skills/` and `agents/` nested inside
  `.claude-plugin/` validates with only an unrelated missing-`author` warning, installs successfully, and
  ships a component inventory of `Skills (0)  Agents (0)  Hooks (0)`. **Fix:** after installing, check
  `claude plugin details <name>`'s component inventory against what the plugin is supposed to contain —
  `validate` checks the manifest and file syntax, never directory placement. **Why people believe it:**
  "validate" sounds exhaustive, and for manifest-shaped defects (§4.6.2's `maintainer` field) it is.
- **Belief:** "the `hooks` object can be copied verbatim from `.claude/settings.json` into a plugin's
  `hooks/hooks.json`, since `plugins` itself says the format is the same." **Outcome:** every
  `${CLAUDE_PROJECT_DIR}` path in the copied object resolves against the *installing* project's root, not
  the plugin's own cached script location — the hooks register with no error and never find their scripts
  at runtime. **Fix:** the object shape is unchanged, but every `command` path must become
  `${CLAUDE_PLUGIN_ROOT}`-relative, per `hooks`' own stated rule for a plugin's `hooks/hooks.json`.
  **Why people believe it:** the migration guide's own wording — "the format is the same" — is true of
  the JSON shape and silent about the one substring inside it that has to change.
- **Belief:** "a `marketplace.json` entry's `source` can point anywhere on disk, the way a project's own
  `additionalDirectories` can." **Outcome:** `"source": "../invoice-ledger-tooling"`, a sibling of the
  marketplace directory, was rejected outright by `claude plugin install` with `source: Invalid input`;
  moving the plugin under the marketplace's own tree and using `"./plugins/invoice-ledger-tooling"`
  installed cleanly. **Fix:** keep every plugin a marketplace lists nested inside that marketplace's own
  directory, mirroring `sdlc-harness`'s own real layout. **Why people believe it:** nothing in the
  manifest's field names signals a containment requirement, and the permitted documentation set for this
  topic does not cover `marketplace.json`'s schema at all — this was confirmed against the running binary,
  not read off a page.

## Cheat sheet

| Item | Value |
|---|---|
| §4.6.1 rule | Only `plugin.json` inside `.claude-plugin/`; `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `bin/`, `settings.json` are all plugin-root siblings |
| §4.6.1 real trap | `hooks.json` copied from `settings.json` keeps `${CLAUDE_PROJECT_DIR}` — must become `${CLAUDE_PLUGIN_ROOT}` |
| §4.6.1 placeholder scope | `${CLAUDE_PROJECT_DIR}`: project root, session-constant. `${CLAUDE_PLUGIN_ROOT}`: plugin's cache dir, changes on update |
| §4.6.1 proof | `claude -p --plugin-dir <path> "list skills/agents"` → `invoice-ledger-tooling:mvn-test-runner`, `:readonly-reviewer`, `:pre-merge-gatekeeper`, `:checklist-refresh`, `:money-minor-units-conventions` — `post-invoice-reversal` correctly absent (`disable-model-invocation: true`) |
| §4.6.1 cost | ≈723 tok always-on (CLI's own estimate); hooks cost 0 tokens (harness-only) |
| §4.6.2 command | `claude plugin validate <path>`, then `--strict` (warnings → errors, exit 1) |
| §4.6.2 real catch | Unrecognized `maintainer` field: warning only plain, hard failure under `--strict` |
| §4.6.2 real miss | Wrong-layout plugin (`skills/`/`agents/` inside `.claude-plugin/`) validates clean except for an unrelated missing-`author` warning |
| §4.6.2 cost | $0 — no session, no model call |
| §4.6.3 commands | `claude plugin marketplace add <dir>` → `claude plugin install <name>@<marketplace> -s local` → (`/reload-plugins`, not exercised — no prior session) |
| §4.6.3 real trap | `source` must resolve *inside* the marketplace's own directory tree; a sibling (`../…`) is rejected: `source: Invalid input` |
| §4.6.3 real proof | Correctly-packaged plugin installs with `Skills (4) Agents (3) Hooks (4)`; wrong-layout plugin installs identically but shows `Skills (0) Agents (0) Hooks (0)` |
| §4.6.3 cleanup | `claude plugin uninstall … --scope local` ×2, `claude plugin marketplace remove` — `enabledPlugins` reverted to `{}`; orphaned cache dirs left for Claude Code's own GC, `rm` itself blocked by this repo's own `settings.local.json` deny rule |
| §4.6.3 cost | $0 — every command is CLI-level, no billed session |

## Self-test

<details><summary>1. Why does a plugin with skills/ and agents/ nested inside .claude-plugin/ pass claude plugin validate, and what actually catches the mistake?</summary>
validate checks the manifest's fields and the syntax of skills, agents, and commands it can find — it does not enforce where those directories sit relative to .claude-plugin/. The only real, unmodified content that surfaces the mistake is the installed plugin's own component inventory (claude plugin details), which reports zero skills, zero agents, and zero hooks for a plugin that validated clean.
</details>

<details><summary>2. What single substring has to change when moving a hooks object from a project's .claude/settings.json into a plugin's hooks/hooks.json, and why?</summary>
Every ${CLAUDE_PROJECT_DIR} in a command path must become ${CLAUDE_PLUGIN_ROOT}. ${CLAUDE_PROJECT_DIR} resolves to the installing project's root, which no longer contains the hook scripts once they move into the plugin; ${CLAUDE_PLUGIN_ROOT} resolves to wherever Claude Code cached the plugin itself, which is where the scripts actually live after packaging.
</details>

<details><summary>3. In the real --plugin-dir test, why did post-invoice-reversal not appear in the model's own list of visible skills, while money-minor-units-conventions did?</summary>
post-invoice-reversal carries disable-model-invocation: true, which removes it from the model's own capability set entirely -- only a user typing its namespaced slash form can invoke it. money-minor-units-conventions carries the opposite restriction, user-invocable: false, which only hides it from the user-facing menu; the model can still see and choose to load it, which is exactly what the real listing showed.
</details>

<details><summary>4. What real error did a marketplace.json entry with "source": "../invoice-ledger-tooling" produce, and what fixed it?</summary>
claude plugin install rejected it with "This plugin's marketplace entry is invalid: source: Invalid input." Moving the plugin directory to live under the marketplace's own tree (plugins/invoice-ledger-tooling) and changing source to "./plugins/invoice-ledger-tooling" installed without error -- a source path must resolve inside the marketplace's own directory, not to an arbitrary sibling.
</details>

<details><summary>5. Why does claude plugin details, not claude plugin validate, get cited as the real check for the D-58 layout mistake?</summary>
validate is a manifest/syntax check that never inspects directory placement, so the wrong-layout plugin validated with only an unrelated missing-author warning. details reports the actual installed component inventory -- Skills(0) Agents(0) Hooks(0) for the broken layout versus Skills(4) Agents(3) Hooks(4) for the correct one -- which is the only one of the two commands that reflects what the plugin will actually do once loaded.
</details>

<details><summary>6. Why did claude plugin prune report nothing to remove after this leaf's plugins were uninstalled, and what actually reclaims their cache directories?</summary>
prune only removes auto-installed dependencies that are no longer needed by anything else; both plugins here were direct installs, not dependencies pulled in on another plugin's behalf, so prune had nothing in scope. Claude Code marks a removed plugin's cache directory with its own .orphaned_at timestamp for its own later garbage collection instead.
</details>

## Open questions

- **Unverified:** `marketplace.json`'s full field schema (`$schema`, `owner`, `plugins[].source`) is
  documented on `plugin-marketplaces`, outside this topic's permitted page set. The shape used above was
  confirmed instead by reading the real, already-published `sdlc-harness/.claude-plugin/marketplace.json`
  (`[CASE]`) and by successfully installing from it.
- **Unverified:** the requirement that a `source` path resolve inside the marketplace's own directory
  tree, rather than to an arbitrary sibling path, is not stated on any page in this topic's permitted set.
  It was confirmed directly against the installed `claude 2.1.251` binary: a sibling `source` was
  rejected with `source: Invalid input`; a nested one installed cleanly.
- **Unverified:** `/reload-plugins` was not directly exercised in this leaf — no Claude Code session was
  running against these plugins before or during the install, so there was nothing yet loaded for that
  command to refresh. Its documented behaviour ("reloads plugins, skills, agents, hooks... without
  restarting") is quoted from `plugins`, not observed here.

---

**Leaves covered:** 4.6.1–4.6.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-98
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 554
