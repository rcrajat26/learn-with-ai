# 21 AI for Coding — plugin structure — INTERMEDIATE (§2.5.1–2.5.4)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [LSP: symbol lookup versus read-and-grep](../mcp-and-lsp/03-lsp.md) · Next: [namespacing and the skills directory](02-namespacing-and-skills-dir.md)

The §1.5.26 decision table back in PART 1 already gave you one line of this area for free: "distribution
to a team → plugin." And `settings/02-keys-and-verification.md` quoted the harness's own project
settings with `enabledPlugins` carrying four entries — three official LSP plugins plus the harness's
own, `sdlc-harness@sdlc-harness`. Both were forward pointers to a mechanism this file now opens
properly: what a **plugin** actually is, what directory it lives in, and the one directory-layout
mistake that ships a plugin with nothing inside it and no error to tell you.

A note on this file's leaf numbering before anything else: the syllabus row that commissioned this
file described §2.5.3 as "`plugin.json` fields" and §2.5.4 as "version semantics." The leaf file this
file is actually bound to numbers them differently — §2.5.2 is the standalone-vs-plugin trade-off,
§2.5.3 is the full directory layout, and §2.5.4 is the `.claude-plugin/` trap itself. The leaf file
wins per this pipeline's contract, so that is the structure below. `plugin.json`'s fields and the
version-update rule are both real, load-bearing facts the reader needs, so they are covered here too —
folded into §2.5.3's "Code" step and §2.5.4's "Gotcha" step respectively, rather than invented as a
fifth and sixth leaf that do not exist in the leaf file.

## §2.5.1–2.5.2 What a plugin is, and when it earns its cost `[ZERO]` `[DOC]`

**Mental model.** Everything a plugin can contain — a **skill** (a Markdown file that teaches Claude a
procedure, invoked as a slash command or picked automatically), an **agent** (a named persona with its
own system prompt, tools and model), a **hook** (a shell command the harness runs at a fixed point in
its lifecycle, such as after every edit), an MCP or LSP server configuration, a background **monitor**
(a long-running command whose output streams into the session as it happens), an executable, and a
default settings file — the reader can already write by hand, today, under their own `.claude/`
directory. A plugin does not add a new capability. It takes a `.claude/` tree that already works and
wraps it so it can be **installed, versioned, and updated on someone else's machine** instead of
copy-pasted.

**Why it exists.** Before plugins, sharing a hook or a skill with a teammate meant sending them the
file and asking them to drop it in the right place by hand — no version, no update path, no record of
which copy is current. A plugin turns that into `claude plugin install <name>@<marketplace>`, gives the
result a `version` field that can be bumped, and namespaces its skills (`/plugin-name:skill-name`) so
two plugins can each ship a skill called the same thing without colliding.

**When to reach for it, and when not.** The official quickstart states this trade-off directly: *"Start
with standalone configuration in `.claude/` for quick iteration, then convert to a plugin when you're
ready to share."* Standalone and plugin are not two different capabilities — they are the same content
at two different distribution stages.

| | Standalone (`.claude/`) | Plugin |
|---|---|---|
| Skill invocation | `/hello` | `/plugin-name:hello` |
| Shareable across projects | Copy the files by hand | `claude plugin install` from a marketplace |
| Versioned, updatable | No — whatever is on disk is what runs | Yes — `version` in `plugin.json`, bumped per release |
| Iteration speed | Edit a file, it's live next turn | Edit a file, then `/reload-plugins`, or `--plugin-dir` while developing |
| Best for | Personal workflows, one project, quick experiments | Sharing with teammates, community distribution, reusable installs |

**What it costs.** A plugin is strictly more indirection than a `.claude/` file: an install step, a
cache directory the harness manages rather than one you edit directly, and — as §2.5.18 covers later in
this area — a path-resolution hazard when a plugin's own scripts need to find files inside their own
plugin directory rather than the project the plugin is running in. None of that is a reason to avoid
plugins; it is the reason "start standalone" is the right default, and "convert when you share" is the
trigger that makes the extra machinery worth it.

**Code.** Confirming what is actually enabled in a running session costs one command:

```bash
claude plugin list
```

This lists every installed plugin by its `name@marketplace` id — the same form seen as
`sdlc-harness@sdlc-harness` in the harness's own `enabledPlugins` block. `claude plugin details <name>`
goes one step further and reports the plugin's component inventory and its projected token cost for the
session — the same "everything costs tokens up front" accounting that MCP servers pay, covered in
`mcp-and-lsp/02-the-per-turn-tax.md`.

**Gotcha.** A plugin with zero components — no `skills/`, no `agents/`, no `hooks/`, nothing — is not a
contradiction; it still needs the manifest below to be recognized as a plugin at all, which is exactly
what the next section is about.

> A plugin is a self-contained, installable, versioned directory of skills, agents, hooks, MCP/LSP
> configuration, monitors, executables and default settings — the same things `.claude/` already
> holds, packaged so someone else's machine can install and update them.

## §2.5.3–2.5.4 The directory layout, and the trap that ships nothing `[DOC]` `[TRAP]`

**Mental model.** PART 1 spent an entire area establishing that `.claude/` **is** the content
directory — skills live at `.claude/skills/`, agents at `.claude/agents/`, hooks are configured directly
inside `.claude/settings.json`. A plugin looks like it should follow the same pattern with
`.claude-plugin/` standing in for `.claude/`. It does not. **`.claude-plugin/` is a manifest folder,
not a content folder** — it holds exactly one file, `plugin.json`, and nothing else. Every actual
component — `skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`,
`settings.json` — sits at the **plugin root**, as a sibling of `.claude-plugin/`, not a child of it.

**Why it exists.** The manifest has to be readable by tooling — the plugin manager, the marketplace
installer, `claude plugin validate` — without that tooling first walking and interpreting every
skill, hook and agent file inside the plugin. Isolating the one file that says "here is this plugin's
name, description and version" into its own folder lets that lookup be a single, cheap file read
instead of a directory-wide scan. The convert-existing-configuration migration in the official plugins
guide makes the split explicit: files that lived in `.claude/commands/`, `.claude/agents/`,
`.claude/skills/` are copied to the **plugin root** unchanged; only the new `plugin.json` goes into the
new `.claude-plugin/` folder.

**How it works — every directory, its location, and what's missing without it:**

| Path | Location | Contributes | Missing means |
|---|---|---|---|
| `.claude-plugin/plugin.json` | Plugin root | Name, description, version — the manifest | The directory is not recognized as a plugin at all |
| `skills/<name>/SKILL.md` | Plugin root | Model-invoked or slash-invoked skills, namespaced `/plugin-name:name` | No skills load; a plugin shipping exactly one skill may instead place `SKILL.md` directly at the plugin root |
| `commands/*.md` | Plugin root | Flat-file skills, the pre-`skills/` form; `skills/` is preferred for new plugins | No flat-file commands load |
| `agents/*.md` | Plugin root | Custom subagent definitions | No plugin-provided agents appear in `/context` |
| `hooks/hooks.json` | Plugin root | Event handlers — `PreToolUse`, `PostToolUse`, `SessionStart`, and the rest of the hook events from `hooks/01-…` | No plugin-provided hooks fire |
| `.mcp.json` | Plugin root | MCP server configuration | No plugin-provided MCP servers connect |
| `.lsp.json` | Plugin root | LSP server configuration for code intelligence | No plugin-provided language servers start |
| `monitors/monitors.json` | Plugin root | Background monitors — commands whose stdout streams into the session as it runs | No plugin-provided monitors start |
| `bin/` | Plugin root | Executables added to the Bash tool's `PATH` while the plugin is enabled | Scripts the plugin ships cannot be invoked by their bare name |
| `settings.json` | Plugin root | Default settings applied when the plugin is enabled — currently only the `agent` and `subagentStatusLine` keys, per the docs | The plugin cannot set a default active agent or status line for the reader |

![D-58 — The plugin directory layout. Only `plugin.json` goes inside `.claude-plugin/`.](../diagrams/D-58-plugin-directory-layout.svg)

**D-58** — The plugin directory layout. Only `plugin.json` goes inside `.claude-plugin/`.

**Pitfall:** the wrong belief is "`.claude-plugin/` is this plugin's `.claude/`, so my skills go
inside it" — a direct, reasonable extrapolation from everything PART 1 just taught about `.claude/`
being the content directory. The symptom is a plugin that installs cleanly, appears in
`claude plugin list`, and has **zero skills, agents or hooks** — no error, no warning, just silence,
because the loader only ever looks for content at the plugin root and never descends into
`.claude-plugin/` for anything but `plugin.json`. The fix is to move every content directory back out to
the plugin root as a sibling of `.claude-plugin/`, never a child of it. One more form of the same
mistake: the plugin root is the plugin's **own** directory — the one passed to `--plugin-dir` or the one
containing `.claude-plugin/plugin.json` — and it is **never** `~/.claude/`; a `.mcp.json` dropped at
`~/.claude/.mcp.json` is not read as anyone's plugin configuration.

**Why people believe it:** every mechanism in PART 1 — skills, agents, hooks, settings — lives inside
`.claude/`, so "the special-dot-folder is where the content goes" is a pattern the reader has
correctly internalized four times running before this file breaks it on the fifth.

**Code — a complete, valid `plugin.json`.** Building on the naming already used for the `[BUILD]`
scripts elsewhere in this guide (`mvn-test-runner`, a Maven test runner exposed as a Claude Code
skill plus a `bin/` executable), here is its manifest:

```json
{
  "name": "mvn-test-runner",
  "description": "Runs the failing subset of a Maven module's test suite and summarizes JUnit output as a skill.",
  "version": "1.2.0",
  "author": {
    "name": "IG Group"
  },
  "homepage": "https://github.com/ig-group/mvn-test-runner-plugin",
  "repository": "https://github.com/ig-group/mvn-test-runner-plugin",
  "license": "proprietary"
}
```

Of these, `name` and `description` are the two fields the docs give with no "Optional" qualifier —
`name` is both the display identity and the skill-namespace prefix (`/mvn-test-runner:run-failing`),
`description` is what a reader browsing a marketplace sees before installing. `version`, `author`,
`homepage`, `repository` and `license` are all documented as optional; `author` is "helpful for
attribution" and nothing more. The harness's own manifest (§2.5.17, in `plugins/05-cases-and-conversion.md`)
adds one more optional field this example omits — a `dependencies` array naming another plugin and the
marketplace it comes from — because `mvn-test-runner` here has no dependency to declare.

**Gotcha — version semantics.** The consequential fact about `version` is not that it exists for
display: **an installed copy of a plugin updates only when `version` changes.** `claude plugin update`
itself documents this in its own `--help` text — updating "a plugin to the latest version" requires "a
restart... to apply" even once the update lands, and the update check in the first place is keyed off
whether the manifest's `version` moved. Concretely: if you edit `mvn-test-runner`'s `SKILL.md` in place
inside an already-installed copy and reload, you have **not** given every user of that installed plugin
your new behaviour — you have edited a file inside a cache directory that the next `claude plugin
update` may or may not even look at, because nothing told it the version changed. This is precisely why
"start standalone, convert when you share" from §2.5.1–2.5.2 matters for the *developer* of a plugin,
not only its users: while you are actively iterating on `mvn-test-runner`'s own files, you want
`--plugin-dir ./mvn-test-runner` pointed at your working copy, not an installed-and-versioned one. The
later files in this §2.5 area and PART 4's `build-it/07` cover `--plugin-dir` development workflow and
the full publish path in depth — this file only needs you to know the rule exists before you hit it.

> `.claude-plugin/` holds exactly one file, `plugin.json`; every actual component sits at the plugin
> root as its sibling, and an installed plugin only picks up new behaviour once `plugin.json`'s
> `version` field changes.

## Pitfalls

- **Belief:** "`.claude-plugin/` is this plugin's `.claude/` — my `skills/` folder goes inside it,
  same as it would at project scope." **Surprising outcome:** the plugin installs without error,
  `claude plugin list` shows it as present, and it contributes nothing — no skill is invocable, no
  hook fires. **What actually gets the guarantee:** every content directory (`skills/`, `commands/`,
  `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, `settings.json`) at the plugin
  root, `.claude-plugin/` holding only `plugin.json`. **Why people believe it:** four straight PART 1
  mechanisms taught the opposite pattern — that the dot-prefixed folder is where content lives.
- **Belief:** "I edited the plugin's file and reloaded, so the update is live for everyone who has it
  installed." **Surprising outcome:** other installs of the same plugin stay on the old behaviour
  indefinitely, because nothing changed the one field the update mechanism checks. **What actually
  gets the guarantee:** bump `version` in `plugin.json` before publishing a change, or use
  `--plugin-dir` against your own working copy while you iterate. **Why people believe it:** editing a
  file in `.claude/` takes effect on the very next turn with no version concept at all, so the reader
  reasonably expects the same immediacy from a plugin's files.

## Cheat sheet

| Question | Answer |
|---|---|
| What goes inside `.claude-plugin/`? | `plugin.json`, and nothing else |
| Where do `skills/`, `agents/`, `hooks/` go? | Plugin root — siblings of `.claude-plugin/` |
| Symptom of the trap | Installs cleanly, lists fine, zero components load, no error |
| Is the plugin root ever `~/.claude/`? | No — it is the plugin's own directory |
| Required `plugin.json` fields | `name`, `description` |
| Optional `plugin.json` fields | `version`, `author`, `homepage`, `repository`, `license`, `dependencies` |
| When does an install pick up new behaviour? | Only after `version` changes |
| Pre-publish iteration tool | `--plugin-dir ./plugin-path` |
| Reload after editing a `--plugin-dir` plugin | `/reload-plugins` |
| Standalone vs plugin, in one line | Same content, `.claude/` for iteration, plugin for distribution |

## Self-test

1. You put a `skills/` folder inside `.claude-plugin/` instead of at the plugin root. What happens
   when the plugin is installed?
<details><summary>Answer</summary>
It installs without error and appears in `claude plugin list`, but the skills inside it never load —
the loader only looks inside `.claude-plugin/` for `plugin.json`, never for content. Nothing tells you
this happened; you find out by trying to invoke the skill and it not existing.
</details>

2. Where does `hooks/hooks.json` live relative to `.claude-plugin/`?
<details><summary>Answer</summary>
As a sibling — `hooks/` sits at the plugin root, alongside `.claude-plugin/`, not inside it.
</details>

3. Name the two fields `plugin.json` requires with no "Optional" qualifier in the documentation.
<details><summary>Answer</summary>
`name` and `description`.
</details>

4. You bump nothing in `plugin.json` but change a hook script's contents and push the change. Does an
   existing installed copy of the plugin pick it up?
<details><summary>Answer</summary>
Not automatically — an installed plugin only updates when `version` in `plugin.json` changes; the
update mechanism is keyed off that field, not off the file contents changing.
</details>

5. What is the plugin root, precisely, and what is it never?
<details><summary>Answer</summary>
The plugin's own directory — the one passed to `--plugin-dir` or the one containing
`.claude-plugin/plugin.json`. It is never `~/.claude/`.
</details>

6. Why does "start standalone in `.claude/`, convert to a plugin when you share" apply even to
   someone actively developing a plugin they intend to publish?
<details><summary>Answer</summary>
Because an installed-and-versioned copy only updates when `version` changes, editing files inside an
already-installed plugin does not reliably propagate; the fast-iteration answer while developing is
`--plugin-dir` against your working directory, the same "edit and it's live" speed `.claude/` gives
you standalone.
</details>

7. List three components, besides `plugin.json`, that a plugin can ship, and what each contributes.
<details><summary>Answer</summary>
Any three of: `skills/` (model- or slash-invoked procedures, namespaced `/plugin-name:name`);
`agents/` (custom subagent personas); `hooks/hooks.json` (event handlers like `PreToolUse` /
`PostToolUse`); `.mcp.json` (MCP server configuration); `.lsp.json` (LSP server configuration);
`monitors/monitors.json` (background commands streaming output into the session); `bin/` (executables
added to Bash's `PATH`); `settings.json` (default settings, currently the `agent` and
`subagentStatusLine` keys).
</details>

## Open questions

None.

---

**Leaves covered:** 2.5.1–2.5.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-58
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 271
