# 21 AI for Coding — three real plugin files, and `${CLAUDE_PLUGIN_ROOT}` — INTERMEDIATE (§2.5.16–2.5.20)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [plugin governance](04-governance.md) · Next: [measuring and ranking context cost](../context-economy/01-measuring-and-ranking.md)

Every file in this set so far has quoted a plugin fragment built to demonstrate a mechanism. This one
quotes the two real manifests that actually run in production — `marketplace.json` and `plugin.json`
from the sdlc-harness repository — and then walks the one porting bug that every author who moves a
hook from `.claude/hooks/` into a plugin hits at least once: `${CLAUDE_PLUGIN_ROOT}` is not the
repository, and the fix is not a smarter guess, it is a refusal. It closes with the concrete move-by-
move mechanics of turning a `.claude/` tree into a plugin, which PART 4's `build-it/07-a-plugin-a.md`
then exercises end to end with a prove step.

## §2.5.16 `marketplace.json`: documentation living inside a machine-read config `[CASE]`

**Mental model.** §2.5.9 already established the shape of a marketplace manifest — `name`,
`description`, `owner`, `plugins`, `allowCrossMarketplaceDependenciesOn`. This section reads the real
one, at `.claude-plugin/marketplace.json` in the sdlc-harness repository root, verbatim, because the
interesting thing about it is not its shape — that is already familiar — but what its `description`
field is doing that the toy example in §2.5.9 was not.

**Why it exists.** A marketplace manifest is parsed by `claude plugin marketplace add`; nothing in the
schema requires its `description` to be more than a one-line blurb. This one is not a one-line blurb.

**How it works.** Read directly from the file, verbatim:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "sdlc-harness",
  "description": "The published sdlc-harness marketplace (RFC 0002 §4.2 pivot, RFC 0003 B9) — engineers add this marketplace via `/plugin marketplace add` to install the sdlc-harness plugin as a first-class, standalone product with its own publish/versioning surface. sdlc-harness depends on ig-superclaude, which lives in a separate marketplace (`ig-superclaude-framework/.claude-plugin/marketplace.json`); allowCrossMarketplaceDependenciesOn below is what lets that dependency auto-install, and onboarding must instruct adding both marketplaces.",
  "owner": {
    "name": "IG Group"
  },
  "allowCrossMarketplaceDependenciesOn": ["ig-superclaude"],
  "plugins": [
    {
      "name": "sdlc-harness",
      "source": "./plugins/sdlc-harness",
      "description": "AI-SDLC harness — deterministic multi-agent workflows (full-sdlc, plan-project, implement-story, post-deploy-smoke) for running Claude agents across the software development lifecycle."
    }
  ]
}
```

**Code.** The interesting field is the top-level `description`. It does not describe the marketplace to
a browsing user the way the `plugins[].description` one line below it does — it names an RFC section
(`RFC 0002 §4.2`), states *why* the marketplace exists as a standalone product rather than folded into
a bigger one (a "pivot"), and pre-explains the cross-marketplace dependency the reader has to configure
correctly two steps later: which marketplace it points at, and that onboarding must add both. **This is
documentation, written for a human who will next open this exact file to add the
`allowCrossMarketplaceDependenciesOn` entry, placed inside a manifest that Claude Code itself parses
only for `name`, `owner`, and `plugins[]`.**

**Insight.** An author does this because the alternative — a separate `README.md` or wiki page
explaining the pivot and the dependency wiring — drifts. The manifest is the one file guaranteed to be
open whenever someone edits `allowCrossMarketplaceDependenciesOn`, adds a plugin entry, or debugs why a
marketplace add failed; a comment field that ships in the same commit as the config it explains cannot
go stale the way a wiki page describing "the current marketplace setup" silently can. The cost is
symmetric: JSON has no comment syntax, so the explanation has to live inside a *string value* the
schema treats as opaque prose — `claude plugin marketplace add` never reads a word of it, a browsing UI
truncates it to a summary line, and a future editor who reformats the manifest with a JSON formatter
risks reflowing a paragraph that was never meant to be machine-processed. The description field is
being used as a comment field a comment-free format does not otherwise offer, and that trade — durable,
co-located documentation versus a bloated value a machine never reads — is deliberate here, not an
oversight.

**Gotcha.** Nothing in the marketplace schema distinguishes a description written for machines
(browsing UI truncation) from one written for humans (the RFC context above); both share the one
`description` string. An author who wants both has to accept that the UI-facing summary and the
onboarding rationale are the same sentence, or push the summary to the front and the rationale to the
back of one long value, exactly as this file does.

> A marketplace `description` is parsed by nothing but a browsing UI and a human reader; using it to
> carry RFC context and onboarding rationale trades JSON's lack of a comment syntax for documentation
> that cannot drift out of sync with the config it explains.

## §2.5.17 `plugin.json`: the real version, licence, and dependency `[CASE]`

**Mental model.** §2.5.10 quoted a `plugin.json` fragment naming `version: "0.10.2"` and a dependency
on `ig-superclaude` to illustrate the cross-marketplace mechanism. That fragment was built to match the
real file, not copied from it. This section reads the actual file at
`plugins/sdlc-harness/.claude-plugin/plugin.json`, verbatim, and checks whether the two still agree.

**How it works.** Read directly from the file, verbatim:

```json
{
  "name": "sdlc-harness",
  "version": "0.10.2",
  "description": "AI-SDLC harness — deterministic multi-agent workflows (full-sdlc, plan-project, implement-story, post-deploy-smoke) for running Claude agents across the software development lifecycle.",
  "author": {
    "name": "IG Group"
  },
  "license": "proprietary",
  "dependencies": [
    { "name": "ig-superclaude", "marketplace": "ig-superclaude" }
  ]
}
```

**Code.** Checked against D-59's earlier draw (§2.5.10, this same set): `version` is `0.10.2`, and
`dependencies` still names exactly one entry, `ig-superclaude` in the `ig-superclaude` marketplace. The
two files agree — the harness has not moved on since D-59 was drawn. The one field D-59 did not carry
is `license`: `"proprietary"`, a plain string rather than an SPDX identifier like `MIT` or
`Apache-2.0`, which is a legitimate value for a manifest field that documentation describes only as
"an SPDX identifier, or `"proprietary"` for private plugins" — an internal, non-redistributed plugin is
exactly the case that string exists for.

**Gotcha.** A `dependencies` entry with a bare `name` and `marketplace` field, as here, does not pin a
version — installing `sdlc-harness@sdlc-harness` resolves `ig-superclaude@ig-superclaude` to whatever
version is currently published in that marketplace, not to a version recorded anywhere in this file.
Pinning a dependency to a specific version needs an additional `version` key inside the dependency
object; its absence here means a breaking change published to `ig-superclaude` propagates to every
consumer of `sdlc-harness` without either file changing.

> Reading the real manifest instead of trusting an earlier fragment is the entire discipline of a
> `[CASE]` leaf: `plugin.json` here confirms `version: 0.10.2` and the single `ig-superclaude`
> dependency drawn at D-59 still hold, and surfaces a fact the fragment omitted — `license:
> "proprietary"` — that only reading the file would catch.

## §2.5.18 `${CLAUDE_PLUGIN_ROOT}` is the plugin's install directory, not the repository `[TRAP]` `[CASE]`

**Mental model.** A hook author who has only ever run their script from `<repo>/.claude/hooks/` builds
one reflex: find the repo root by walking up from the script's own path. `dirname "$0"/../..` does
exactly that — two levels up from `.claude/hooks/check-init.sh` lands on `<repo>`. That reflex is
correct exactly once, in exactly one location, and every plugin conversion breaks it, because the
script no longer lives at that location.

**Why it exists — or rather, why the bug is this shape.** Re-verified against the `hooks`
documentation page immediately before writing this section: `${CLAUDE_PLUGIN_ROOT}` "resolves to the
plugin's installation directory, for scripts bundled with a plugin" and the same page notes it
"changes on each plugin update." Once a hook ships inside a plugin, its `hooks.json` entry invokes it
as `bash "${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh"` — the same script, but now `$0` is a path inside
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`, not inside the cloned repository at all.
`dirname "$0"/../..` still executes without error. It just walks up inside the cache instead of the
repository, and produces a path that looks plausible and is wrong.

**How it works.** The real `hooks.json` for this plugin, verbatim from
`plugins/sdlc-harness/hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh\""
          },
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/prod-guard-session-start.sh\""
          },
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/calibration-nudge.sh\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/doc-update-reminder.sh\""
          }
        ]
      }
    ]
  }
}
```

Every command substitutes `${CLAUDE_PLUGIN_ROOT}` for the plugin root — correctly, for locating the
*script itself*. The bug is one layer further in: what the script does with `$0` once it is running.

![D-60 — `${CLAUDE_PLUGIN_ROOT}` is not the repository. The same `dirname "$0"/../..` resolves into the plugin cache.](../diagrams/D-60-plugin-root-is-not-repo.svg)

**D-60** — `${CLAUDE_PLUGIN_ROOT}` is not the repository. The same `dirname "$0"/../..` resolves into
the plugin cache.

D-60 draws the two runs of the same expression side by side. On the left, `check-init.sh` lives at
`<repo>/.claude/hooks/`; `$0` is that path; `dirname "$0"/../..` walks `.claude/hooks/` → `.claude/` →
`<repo>` and lands correctly. On the right, the same script lives inside an installed plugin; `$0` is
`${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh`, where `CLAUDE_PLUGIN_ROOT` is the cache path documentation
names above; the identical `dirname "$0"/../..` walks up **inside that cache** —
`~/.claude/plugins/cache/acme-tools/1.4.2` two levels up is still inside the cache tree, not the
repository the hook is supposed to be operating on.

**Pitfall:** the wrong belief is that `${CLAUDE_PLUGIN_ROOT}` (or a relative walk from the script's own
path) is, or can stand in for, the repository root once a hook ships as a plugin. The symptom is a hook
that runs without error, reads or writes the wrong files — inside `~/.claude/plugins/cache/...` instead
of the actual checkout — and produces no exception to point at the cause, because every path in the
walk exists; it is simply the wrong tree. The fix is §2.5.19's `git rev-parse --show-toplevel`, never a
path computed relative to `${CLAUDE_PLUGIN_ROOT}` or `$0`. **Why people believe it:** the walk worked
correctly, unmodified, for as long as the hook lived in `.claude/hooks/`, so nothing in local testing
during that phase would have surfaced the assumption as fragile — it only breaks at the one moment the
script's location changes, which is exactly the moment of conversion to a plugin.

> `${CLAUDE_PLUGIN_ROOT}` is the plugin's own install or cache directory — it changes on every plugin
> update — never the repository the hook operates on; any repo-root arithmetic derived from a plugin
> hook's own path (`$0`, `${CLAUDE_PLUGIN_ROOT}`) resolves into the cache instead of the checkout.

## §2.5.19 The fix, and the discipline of refusing rather than guessing `[CASE]`

**Mental model.** The naive fix — "compute the repo root a different way, relative to something more
stable than `$0`" — is still the same category of mistake: any path arithmetic anchored to where the
plugin happens to be installed inherits the same failure the moment that install location moves, which
plugin updates guarantee it will. The actual fix abandons path arithmetic entirely and asks git.

**How it works.** The header comment in the real, shipped hook, `plugins/sdlc-harness/hooks/check-init.sh`,
quoted verbatim:

```bash
#!/usr/bin/env bash
set +e
# Ported from .claude/hooks/check-init.sh (RFC 0003 B5). Same HARNESS_ROOT ->
# git-toplevel precedence as doc-update-reminder.sh's plugin port — see that
# file's header comment for why the clone-mode `dirname "$0"/../..` walk
# cannot be reused once this script runs from the plugin cache
# (${CLAUDE_PLUGIN_ROOT}/hooks/, not <repo>/.claude/hooks/). No third
# "package location" fallback tier here (unlike engine/_paths.py::repo_root)
# because there is no harness workspace to check-init against once neither
# tier resolves — refuse clearly instead of guessing one.
if [[ -n "${HARNESS_ROOT:-}" ]]; then
  REPO_ROOT="$HARNESS_ROOT"
else
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
fi
if [[ -z "$REPO_ROOT" ]]; then
  echo "[HARNESS_BOOTSTRAP_REQUIRED] Tell the user: 'Could not resolve the harness workspace root (no HARNESS_ROOT set and not inside a git checkout). Run: /sdlc-harness:bootstrap — it resolves or creates HARNESS_ROOT as its first step, no existing checkout required.'"
  exit 0
fi
```

**Code.** The resolution order is two tiers, not one, and the comment is explicit about why there is no
third: an `HARNESS_ROOT` environment variable, if a caller has set one (this is what lets a "dogfood"
session — Claude Code launched with `--plugin-dir` against a working checkout of the harness itself —
resolve correctly without needing git at all), and otherwise `git rev-parse --show-toplevel`, which
answers "what repository am I actually inside right now" independent of where the *hook script* lives.
If neither tier resolves — no env var, and the working directory is not inside a git checkout at
all — the script does not fall back to a third guess. It prints a message telling the user exactly what
is missing and which command fixes it (`/sdlc-harness:bootstrap`), and exits `0` rather than continuing
with a wrong root. The same discipline appears in the sibling `doc-update-reminder.sh`, whose own
header the comment above points to, and which the grep for the pattern across the repository confirms
uses the identical `HARNESS_ROOT` → `git rev-parse --show-toplevel` precedence rather than a
one-off fix local to `check-init.sh`.

**Insight.** "No third fallback tier" is the load-bearing sentence, not a throwaway aside. A script with
two resolution tiers and a clear refusal is honest about the one case it cannot handle. A script that
adds a third guess — "if git also fails, assume the current working directory," say — converts an honest
refusal into a wrong answer delivered with full confidence, which is strictly worse than stopping,
because nothing downstream can tell the difference between a correct resolution and a lucky one. The
reader will meet this exact judgment call again at §3.9.6, where a `--resume-at` flag is rejected
outright rather than approximated to the nearest checkpoint: a tool that guesses when it cannot know
produces a confidently wrong answer, and refusing is the correct behavior, not a missing feature.

**Interview:** "Your hook worked in `.claude/hooks/` and breaks after you ship it as a plugin — what
happened, and how do you fix it?" One line: `${CLAUDE_PLUGIN_ROOT}` (or the script's own `$0`) points
at the plugin's install/cache directory, not the repository, so any relative-path walk from either one
resolves into the cache; fix it by resolving the repo root independently via `git rev-parse
--show-toplevel` (with an optional environment-variable override for non-git contexts), and refuse with
a clear message if that fails rather than inventing a third fallback.

> The fix for a hook that needs the repository root, regardless of where the hook itself is installed,
> is `git rev-parse --show-toplevel` (optionally overridable by an explicit environment variable) —
> never path arithmetic relative to `${CLAUDE_PLUGIN_ROOT}` or `$0` — and a resolution failure should
> exit with a clear message rather than fall back to a guess.

## §2.5.20 Converting a `.claude/` tree into a plugin `[BUILD]`

**Mental model.** Everything the reader wrote by hand across PART 1 — skills under `.claude/skills/`,
agents under `.claude/agents/`, hooks wired into `settings.json`, commands under `.claude/commands/` —
is one `mkdir` and a handful of `cp` commands away from being a plugin. Nothing about the components
themselves changes; only where they live and how hooks are declared changes.

**Why it exists.** A `.claude/` tree only ever works in the one repository it was written in. The
moment a second project, or a teammate, wants the same skill or hook, the standalone form has no answer
better than "copy the files by hand" — which is exactly the "must manually copy to share" row the
official comparison table draws against a plugin's "install with `/plugin install`."

**How it works.** Re-verified against the "Convert existing configurations to plugins" section of the
`plugins` documentation page immediately before writing this section. The mapping, move by move:

| From (`.claude/` tree) | To (plugin) | What changes |
|---|---|---|
| Project root | `<plugin-name>/.claude-plugin/plugin.json` (new file) | Nothing to move — this file does not exist standalone; it is authored fresh: `name`, `description`, `version` |
| `.claude/commands/` | `<plugin-name>/commands/` | Plain `cp -r`; no format change |
| `.claude/agents/` | `<plugin-name>/agents/` | Plain `cp -r`; no format change |
| `.claude/skills/` | `<plugin-name>/skills/` | Plain `cp -r`; no format change |
| `hooks` object in `.claude/settings.json` or `settings.local.json` | `<plugin-name>/hooks/hooks.json` | The `hooks` object's *shape* is unchanged — the same `PostToolUse`/`SessionStart`-keyed structure — but it moves out of `settings.json` into its own file, and any relative path a hook command referenced now needs `${CLAUDE_PLUGIN_ROOT}` in place of a path relative to the repo root, per §2.5.18 |

Test before deleting anything:

```bash
claude --plugin-dir ./sdlc-harness
```

then exercise each component — run the commands, confirm agents appear in `/context` under Custom
Agents, and trigger the event each hook matches (edit a file for a `PostToolUse` hook) and confirm the
debug log records it firing. Once the plugin form is confirmed working, validate the manifest itself:

```bash
claude plugin validate ./sdlc-harness
```

which prints `✔ Validation passed` (or `✔ Validation passed with warnings`, promotable to a failure
with `--strict`).

**Gotcha.** `[TRAP]` The migration is not complete until the originals are deleted. Project and user
`.claude/agents/` definitions **override** a same-named plugin agent, so a copied-but-not-removed
`.claude/agents/readonly-reviewer.md` means the plugin's copy never takes effect no matter how correctly
it was converted — every edit to the plugin version appears to do nothing, because the standalone
original is still the one loading. Skills are the one component this does not apply to: plugin skills
are always namespaced (`/plugin-name:skill-name`), so an un-deleted `.claude/skills/` original and its
plugin copy coexist as two separately invocable skills rather than one silently shadowing the other —
delete it anyway, or the two drift apart the first time either one is edited.

**Code.** This is the mechanism; it is not the exercise. PART 4's `build-it/07-a-plugin-a.md` runs this
exact conversion end to end against a real `.claude/` tree, with a prove step showing the hook firing
identically before and after conversion and a token/dollar cost note for the exercise — that file is
where the reader does this, not this one.

> Converting a `.claude/` tree into a plugin is `cp -r` for commands, agents, and skills, a new
> `.claude-plugin/plugin.json`, and moving the `hooks` object out of `settings.json` into its own
> `hooks/hooks.json` — followed by deleting the originals, since a same-named `.claude/agents/` or
> `.claude/commands/` entry silently overrides the plugin copy rather than erroring.

## Pitfalls

- **Belief:** `${CLAUDE_PLUGIN_ROOT}`, or a relative walk from a hook script's own path, is a stable
  proxy for the repository root once the hook ships as a plugin. **Surprising outcome:** the hook runs
  without error and silently reads or writes inside the plugin's install/cache directory instead of the
  actual checkout — every path along the walk exists, so nothing signals the mistake at the point it
  happens. **What actually gets the guarantee:** resolve the repo root independently with `git
  rev-parse --show-toplevel` (optionally overridable via an explicit environment variable for non-git
  contexts), and refuse with a clear message if that fails rather than adding a third fallback tier.
  **Why people believe it:** the exact same expression worked correctly, unmodified, for the entire
  time the script lived at `.claude/hooks/`, so nothing in that phase of testing would have exposed the
  assumption as fragile.
- **Belief:** copying `.claude/agents/`, `.claude/skills/`, and `.claude/commands/` into a new plugin
  directory and testing with `--plugin-dir` completes the migration. **Surprising outcome:** edits to
  the plugin's agent definitions appear to do nothing, because the un-deleted `.claude/agents/` original
  is still the one Claude Code loads — project and user agent definitions override a same-named plugin
  agent. **What actually gets the guarantee:** delete the original `.claude/` files after confirming the
  plugin form works; for agents and commands this is required for the plugin copy to take effect at
  all, and for skills it is required to avoid the two copies silently drifting apart even though both
  remain separately invocable. **Why people believe it:** the migration steps as usually described stop
  at "copy the files and test," and the override behavior for agents is not visible until a second edit
  to the (now-shadowed) plugin copy produces no effect.

## Cheat sheet

| Question | Answer |
|---|---|
| Where does `marketplace.json`'s free-text `description` field actually get read | A browsing UI (truncated) and a human editor — never `claude plugin marketplace add`'s parser, which only needs `name`, `owner`, `plugins` |
| Real sdlc-harness `plugin.json` version | `0.10.2` — unchanged since D-59 |
| Real sdlc-harness `plugin.json` licence | `"proprietary"` (plain string, valid alongside SPDX identifiers) |
| Real sdlc-harness `plugin.json` dependency | One entry: `{ name: "ig-superclaude", marketplace: "ig-superclaude" }`, unpinned (no `version` key) |
| `${CLAUDE_PLUGIN_ROOT}` resolves to | The plugin's install/cache directory — changes on every plugin update, never the repo |
| Correct way to find the repo root from inside a plugin hook | `git rev-parse --show-toplevel`, optionally overridden by an explicit env var (e.g. `HARNESS_ROOT`) |
| What to do if neither resolves | Refuse with a clear message and a fix command; never add a third path-guessing fallback |
| `.claude/commands\|agents\|skills/` → plugin | `cp -r` into `<plugin>/commands\|agents\|skills/`; no format change |
| `hooks` in `settings.json` → plugin | Move the same `hooks` object into `<plugin>/hooks/hooks.json`; hook commands switch to `${CLAUDE_PLUGIN_ROOT}`-relative paths |
| Test before deleting originals | `claude --plugin-dir ./<plugin>`, then exercise every component |
| Validate the manifest | `claude plugin validate ./<plugin>` → `✔ Validation passed[ with warnings]` (`--strict` promotes warnings) |
| Must delete originals for | Agents, commands (silently overridden otherwise) — skills coexist but drift if not deleted |
| Where the exercise lives | `build-it/07-a-plugin-a.md` (PART 4) — this file is the mechanism, that one is the prove step |

## Self-test

1. What does `marketplace.json`'s `description` field in the real sdlc-harness manifest contain that a
   minimal, schema-satisfying marketplace manifest would not, and why does the author put it there
   instead of a separate README?
<details><summary>Answer</summary>
RFC references, the reason the marketplace is a standalone product rather than folded into a bigger
one, and onboarding instructions for the cross-marketplace dependency. It lives in the manifest because
that file is guaranteed to be open whenever someone edits `allowCrossMarketplaceDependenciesOn` or adds
a plugin entry, so it cannot drift out of sync with the config it explains the way a separate wiki page
could.
</details>

2. Read off the real `plugin.json`: does the harness still depend on `ig-superclaude`, and is that
   dependency version-pinned?
<details><summary>Answer</summary>
Yes, still depends on `ig-superclaude` (marketplace `ig-superclaude`), matching D-59. It is not
version-pinned — the dependency entry carries only `name` and `marketplace`, no `version` key, so
install resolves whatever version is currently published.
</details>

3. A hook file identical in every byte runs correctly from `.claude/hooks/` and incorrectly once
   shipped inside a plugin, using the same `dirname "$0"/../..` expression in both cases. What changed?
<details><summary>Answer</summary>
`$0` itself. In the repo, `$0` is a path inside the checkout, so walking up two levels lands on the
repo root. Inside a plugin, `$0` is a path inside `${CLAUDE_PLUGIN_ROOT}` — the plugin's install/cache
directory — so the identical walk lands two levels up inside the cache instead.
</details>

4. What are the two resolution tiers `check-init.sh` uses to find the repo root, and what does it do if
   neither one resolves?
<details><summary>Answer</summary>
First, an explicit `HARNESS_ROOT` environment variable if set; otherwise `git rev-parse
--show-toplevel`. If neither resolves, it prints a message naming the missing state and the fix command
(`/sdlc-harness:bootstrap`) and exits `0` — it does not add a third fallback that guesses a path.
</details>

5. Why is refusing with a clear message better engineering than adding a third fallback tier that
   guesses a plausible root?
<details><summary>Answer</summary>
A guess that happens to be wrong produces a confidently wrong answer with no signal that anything is
off, which is strictly worse than an honest refusal — nothing downstream can distinguish a correct
resolution from a lucky one. The same judgment reappears at §3.9.6, where a `--resume-at` flag is
rejected outright rather than approximated.
</details>

6. Converting a `.claude/agents/readonly-reviewer.md` into a plugin agent, you copy the file, test with
   `--plugin-dir`, confirm it works, and stop. Two weeks later a teammate edits the plugin's copy and
   nothing changes in their session. Why?
<details><summary>Answer</summary>
The original `.claude/agents/readonly-reviewer.md` was never deleted, and project/user agent
definitions override a same-named plugin agent — the standalone original is still the one loading, so
edits to the plugin copy have no visible effect until the original is removed.
</details>

7. Does the same silent-override risk apply to a skill left in both `.claude/skills/` and the new
   plugin's `skills/` directory?
<details><summary>Answer</summary>
No — plugin skills are always namespaced (`/plugin-name:skill-name`), so the original `/skill-name` and
the plugin's `/plugin-name:skill-name` both remain separately invocable rather than one shadowing the
other. The original should still be deleted, but the failure mode is drift between two copies, not
silent override.
</details>

## Open questions

None.

---

**Leaves covered:** 2.5.16–2.5.20 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-60
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 448
