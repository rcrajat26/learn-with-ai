# 21 AI for Coding — publishing, the version bump, and the diff against the real one — BUILD IT (§4.6.4–4.6.6)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [a plugin](07-a-plugin-a.md) · Next: [a verification harness](08-verification-harness-a.md)

`07-a-plugin-a.md` packaged `invoice-ledger-service`'s whole PART 4 payload — four hooks, four
skills, three agents — into `invoice-ledger-tooling`, proved it with `--plugin-dir`, ran `claude
plugin validate` and `--strict` for real, and published it to a real local marketplace
(`invoice-ledger-marketplace`), catching the D-58 wrong-layout trap live along the way. Two things
that file could not reach: `/reload-plugins` (no prior running session to reload) and the version
bump. Both are this file's job, and the version bump does not behave the way its own name suggests.
Every command below ran for real, under `/tmp/21-plugin-scratch`, against the same `claude 2.1.251`
binary, reusing the exact `invoice-ledger-tooling` and `invoice-ledger-marketplace` directories
`07-a-plugin-a.md` built. **No repository was written to — this repo's own files, and the
read-only sdlc-harness, were only ever read.** Every marketplace and plugin created for this file's
proofs was removed again before it ends; the removal commands and their output are included, not
just promised.

## §4.6.4 — bump `version`, and prove what an installed copy actually does `[BUILD]` `[PROVE]`

**Concept.** A plugin's `version` field is the signal a marketplace-installed copy uses to decide
whether a newer copy exists. `[DOC]` Re-verified against `plugins` immediately before writing this
leaf, its own manifest table states the field plainly: *"`version` — Optional. If set, users only
receive updates when you bump this field, except for a `command` source... If omitted, the version
comes from the next source in version management."* Read at face value, that sentence describes
exactly the workflow this leaf's syllabus line names: edit the plugin, the installed copy stays
frozen at the old `version`; bump `version`, the installed copy catches up. That is true, and this
leaf proves it — but only for one half of what "an installed copy" turns out to mean, and the other
half is the finding worth carrying away.

**Why it exists.** Without a version signal, "install once, update later" cannot exist at all: every
`claude plugin update` call would either always say "nothing changed" (never re-pull) or always
re-pull everything on every check (expensive, and indistinguishable from a real new release). The
field is the cheapest possible answer to "did anything change" — a string comparison — pushed onto
the plugin author rather than computed by diffing file contents.

**How it works, and the real surprise in it.** `invoice-ledger-tooling`'s manifest at
`/tmp/21-plugin-scratch/invoice-ledger-marketplace/plugins/invoice-ledger-tooling/.claude-plugin/plugin.json`
started this leaf at `"version": "1.0.0"`, marketplace-registered and installed exactly as
`07-a-plugin-a.md` left it (`claude plugin marketplace add`, then `claude plugin install
invoice-ledger-tooling@invoice-ledger-marketplace -s local -y`, re-run fresh for this file since the
previous one's cleanup had removed both). A baseline, real session — not `--plugin-dir`, the
actually-installed marketplace copy, run from inside `/private/tmp/21-plugin-scratch` so the
`local`-scope install resolves — confirmed the starting component set:

```
$ claude -p --setting-sources project,local,user \
    "List every skill visible to you right now under the invoice-ledger-tooling namespace, by exact name, and nothing else." \
    --output-format json
```
```
invoice-ledger-tooling:checklist-refresh
invoice-ledger-tooling:money-minor-units-conventions
invoice-ledger-tooling:mvn-test-runner
```
Three, not four — `post-invoice-reversal`'s `disable-model-invocation: true` still holds, exactly as
`07-a-plugin-a.md` found with `--plugin-dir`; packaging into a real marketplace install changed
nothing about that field's effect.

A fifth skill, `invoice-void-audit`, was then added straight into the plugin's source directory —
`skills/invoice-void-audit/SKILL.md`, a real, complete skill file, reviewing an invoice void's status
transition and its `reversalOf` linkage before approval — **with `version` left untouched at
`1.0.0`.** `claude plugin update invoice-ledger-tooling -s local -y` was run immediately after:

```
Checking for updates for plugin "invoice-ledger-tooling" at local scope…
✔ invoice-ledger-tooling is already at the latest version (1.0.0).
```

That much matches the doc's claim exactly — no version change, no update offered. But the same
session-listing command, re-run at that exact moment, **before any version bump and before running
`claude plugin update` a second time**, already shows the new skill:

```
$ claude -p --setting-sources project,local,user \
    "List every skill visible to you right now under the invoice-ledger-tooling namespace, by exact name, and nothing else." \
    --output-format json
```
```
- invoice-ledger-tooling:checklist-refresh
- invoice-ledger-tooling:invoice-void-audit
- invoice-ledger-tooling:money-minor-units-conventions
- invoice-ledger-tooling:mvn-test-runner
```

**This is the real finding, not a scripting error: for a marketplace entry whose `source` is a plain
local directory path (`"./plugins/invoice-ledger-tooling"`), a session started at `-s local` scope
reads the skill set live off that directory on every start, regardless of `version`.** Nothing was
re-installed, no `marketplace update` or `plugin update` was run between the edit and this listing —
confirmed by running the listing again immediately after adding the file and before touching either
command at all, with the identical result. The version bump was then performed for completeness and
to exercise the actual `update` path:

```json
{
  "name": "invoice-ledger-tooling",
  "description": "The invoice-ledger-service .claude tooling -- four hooks, four skills, and three subagents built across build-it/01-04 -- packaged as an installable, versioned plugin.",
  "version": "1.1.0",
  "author": { "name": "IG Group" },
  "license": "proprietary"
}
```
```
$ claude plugin marketplace update invoice-ledger-marketplace
Updating marketplace: invoice-ledger-marketplace...Validating local marketplace
✔ Successfully updated marketplace: invoice-ledger-marketplace

$ claude plugin update invoice-ledger-tooling -s local -y
Checking for updates for plugin "invoice-ledger-tooling" at local scope…
✔ Plugin "invoice-ledger-tooling" updated from 1.0.0 to 1.1.0 for scope local (/private/tmp/21-plugin-scratch). Restart to apply changes.
```

`claude plugin details invoice-ledger-tooling` afterward reports `Skills (5)` at version `1.1.0`, and
the on-disk cache now holds two version-stamped directories side by side — confirmed directly:

```
$ find ~/.claude/plugins/cache/invoice-ledger-marketplace/invoice-ledger-tooling -maxdepth 2
.../invoice-ledger-tooling/1.0.0   (now carrying its own .orphaned_at marker)
.../invoice-ledger-tooling/1.1.0   (skills/invoice-void-audit present here, not in 1.0.0)
```

So the version-stamped cache directory is real and does exist per version — the bump did produce a
genuinely new, separately-named snapshot. What it evidently is *not*, for a local-directory source at
`local` scope, is the thing a running session actually reads from: that reads the marketplace's
`source` path live, and the cache directory functions as a version-labelled record for `claude
plugin list --json`, `claude plugin update`'s own before/after bookkeeping, and (§4.6.5, next)
dependency version pins — not as the gate on what a session loads.

**What this costs.** Every command in this leaf — `plugin marketplace update`, `plugin update`,
`plugin details` — is CLI-level, exactly like `07-a-plugin-a.md`'s `plugin validate`: no session
starts, no model is called, so the bump-and-check cycle itself costs **$0**. The two real `claude -p`
listing calls used to observe the skill set each billed one small Sonnet-turn read of the plugin's
system-prompt injection; at `invoice-ledger-tooling`'s own measured ≈723-tokens-always-on rate
(`07-a-plugin-a.md`), each such probe costs a few cents, not the version bump's own cost — the bump
itself is free.

**Pitfall:** the belief, read directly off the documentation's own wording, is "editing a plugin's
files has no effect on an installed copy until `version` changes." **Outcome:** true for the
version-stamped cache directory and for what `claude plugin update` reports, **false** for what a
live session actually loads when the marketplace entry's `source` is a local filesystem path — the
new skill was visible with zero version change and zero explicit reload command. **Fix:** treat the
version bump as required for keeping `claude plugin update`'s own state machine, `claude plugin
list --json`'s version field, and any dependent plugin's version pin (§4.6.5) meaningful — not as
the mechanism that makes a local edit visible to a session, which for a `local`-path source it
already is. **Why people believe it:** the manifest table's own wording states the rule without
qualifying it by source type, and for a plugin distributed by git or by a hosted URL — where there
is a real fetch step to trigger — the rule is very plausibly exact; that case was not independently
reproduced here (see `## Open questions`).

**Insight.** Three commands can each answer "did the plugin update" and disagree with each other in
a way that is not a bug in any one of them: `claude plugin update` answers *"does the manifest's
version field say there's something new"*; `claude plugin details` answers *"what does the
currently-resolved copy structurally contain"*; only an actual running session answers *"what can
the model call right now."* §4.6.5 below produces a sharper version of exactly this three-way split.

## §4.6.5 — an unresolved dependency, and the `claude plugin list --json` `errors` array `[BUILD]` `[PROVE]`

**Concept.** `plugin.json`'s optional `dependencies` array names other plugins — each an object with
a `name` and the `marketplace` it lives in — that must be installed alongside this one. `07-a-plugin-a.md`
already showed the real sdlc-harness shape this takes: one entry, `{"name": "ig-superclaude",
"marketplace": "ig-superclaude"}`, quoted and explained in `plugins/05-cases-and-conversion.md`
(`[CASE]`, not re-quoted here). This leaf builds a second, real local plugin carrying the identical
shape of dependency, deliberately unresolved, to see what actually happens rather than assume it.

**Why it exists.** `invoice-ledger-tooling` is entirely self-contained — every hook, skill, and agent
it ships runs inside `invoice-ledger-service` alone. A second, genuinely different plugin,
`invoice-reconciliation-addon`, was built for this leaf to need something `invoice-ledger-tooling`
does not: a shared money-report formatting convention that — in this leaf's scenario — lives in a
separate, not-yet-added plugin, `ig-superclaude`, from a separate marketplace also named
`ig-superclaude`. That is precisely the shape a real cross-team dependency takes: one plugin's skill
assumes another plugin's shared conventions are present, and nothing in `claude plugin install`
forces the second one to already exist.

**The artefact — `invoice-reconciliation-addon`, real values:**

```json
{
  "name": "invoice-reconciliation-addon",
  "description": "A second, real local plugin, mirroring sdlc-harness's own unpinned ig-superclaude dependency, to prove the claude plugin list --json errors array for an unresolved dependency.",
  "version": "1.0.0",
  "author": { "name": "IG Group" },
  "license": "proprietary",
  "dependencies": [
    { "name": "ig-superclaude", "marketplace": "ig-superclaude" }
  ]
}
```

Its one skill, `reconciliation-report`, cross-checks the ledger's `SETTLED` invoices for the current
business day against the payment gateway's own settlement export — a real, complete `SKILL.md`,
registered in `invoice-ledger-marketplace` alongside `invoice-ledger-tooling` at
`"source": "./plugins/invoice-reconciliation-addon"`. Neither the `ig-superclaude` plugin nor the
`ig-superclaude` marketplace it names was ever added to this machine for this leaf — the whole point
is to observe what an install does when that reference cannot resolve.

**Prove step, three commands, three different answers.** `[PROVE]` `claude plugin validate` on the
addon's own directory passes clean — a `dependencies` entry naming an unregistered marketplace is not
a manifest-shape defect, so validation has nothing to flag:

```
$ claude plugin validate /tmp/21-plugin-scratch/invoice-ledger-marketplace/plugins/invoice-reconciliation-addon
Validating plugin manifest: .../invoice-reconciliation-addon/.claude-plugin/plugin.json

✔ Validation passed
```

`claude plugin install` also succeeds outright, with no warning printed at all:

```
$ claude plugin install invoice-reconciliation-addon@invoice-ledger-marketplace -s local -y
Installing plugin "invoice-reconciliation-addon@invoice-ledger-marketplace"...
✔ Successfully installed plugin: invoice-reconciliation-addon@invoice-ledger-marketplace (scope: local)
```

`claude plugin list --json` is the one place the unresolved state actually surfaces, in a per-plugin
`errors` array sitting beside a `"enabled": true`:

```json
{
  "id": "invoice-reconciliation-addon@invoice-ledger-marketplace",
  "version": "1.0.0",
  "scope": "local",
  "enabled": true,
  "installPath": "/Users/rajat.chikkodikar/.claude/plugins/cache/invoice-ledger-marketplace/invoice-reconciliation-addon/1.0.0",
  "installedAt": "2026-08-30T13:59:01.884Z",
  "lastUpdated": "2026-08-30T13:59:01.884Z",
  "projectPath": "/private/tmp/21-plugin-scratch",
  "errors": [
    "Dependency \"ig-superclaude@ig-superclaude\" is not installed — run `claude plugin install ig-superclaude@ig-superclaude`, or check that its marketplace is added"
  ]
}
```

`claude plugin details invoice-reconciliation-addon` disagrees with that `errors` array's implication
in a way worth naming precisely: it reports the plugin's own component inventory in full, as if
nothing were wrong —

```
invoice-reconciliation-addon 1.0.0
Component inventory
  Skills (1)  reconciliation-report
  Agents (0)
  Hooks (0)
```

— but a real session, probed exactly as in §4.6.4, shows the truth underneath both of those signals:
the skill never loads at all.

```
$ claude -p --setting-sources project,local,user \
    "List every skill visible to you right now under the invoice-reconciliation-addon namespace, by exact name, and nothing else." \
    --output-format json
```
```
No skills are visible under an `invoice-reconciliation-addon` namespace — that namespace doesn't
appear in my available skills. The only namespaced plugin skills present are under
`invoice-ledger-tooling` (plus `ig:` and `sc:`).
```

**Fix.** The install itself is not the enforcement point, and neither is `enabled: true`, nor
`details`' inventory — the only reliable signal that a plugin's dependency is actually blocking it is
`claude plugin list --json`'s per-plugin `errors` array, and the only reliable confirmation of the
practical effect is asking a real session what it can see. The remedy the error message itself names
is exact: add and trust the missing marketplace, then install the dependency —
`claude plugin marketplace add <ig-superclaude source>` followed by `claude plugin install
ig-superclaude@ig-superclaude` — after which `list --json`'s `errors` array for
`invoice-reconciliation-addon` empties and the skill starts resolving in a session the same way
`invoice-ledger-tooling`'s skills already do.

**What this costs.** `claude plugin details` reports `reconciliation-report`'s own always-on
component cost at ≈105 tokens — but since the dependency is unresolved and the skill never actually
loads into a session (confirmed above), that number is never really paid: it is the cost the plugin
*would* add once the dependency resolves, not the cost of running it broken. `validate`, `install`,
and `list --json` are all CLI-level and cost **$0**, identical to every other `claude plugin`
subcommand this row has run.

**Pitfall:** the belief is "if `claude plugin install` and `claude plugin details` both report
success, the plugin's dependencies are satisfied." **Outcome:** both did, for a plugin whose one
skill never became callable. **Fix:** check `claude plugin list --json`'s `errors` array specifically
— it is the one place this state is named — and confirm with a real session probe, not `details`.
**Why people believe it:** `install`'s own success message and `details`' clean inventory both read as
unconditional "this plugin is fine," and neither is built to check a fact that only becomes true or
false relative to a second, separately-installed plugin.

**Cleanup, performed for real.** Every plugin and the marketplace built across §4.6.4 and §4.6.5 was
removed before this file ends:

```
$ claude plugin uninstall invoice-reconciliation-addon@invoice-ledger-marketplace --scope local
✔ Successfully uninstalled plugin: invoice-reconciliation-addon (scope: local)
$ claude plugin uninstall invoice-ledger-tooling@invoice-ledger-marketplace --scope local
✔ Successfully uninstalled plugin: invoice-ledger-tooling (scope: local)
$ claude plugin marketplace remove invoice-ledger-marketplace
✔ Successfully removed marketplace: invoice-ledger-marketplace
```

`claude plugin list --json` afterward shows neither plugin — only this machine's own pre-existing,
unrelated `claude-router@0xrdan-plugins` install, untouched throughout — and this scratch project's
own `.claude/settings.local.json` reverted to `"enabledPlugins": {}`, matching `07-a-plugin-a.md`'s
own cleanup outcome exactly.

## §4.6.6 — Diff vs the real one: `invoice-ledger-tooling` and `invoice-ledger-marketplace` against `sdlc-harness`

`plugins/05-cases-and-conversion.md` already quoted both real manifests verbatim —
`.claude-plugin/marketplace.json` at the sdlc-harness repository root and
`plugins/sdlc-harness/.claude-plugin/plugin.json` — and is not re-quoted here; the values below are
reasoned from that file's own quotes. `${CLAUDE_PLUGIN_ROOT}` path discipline is excluded from this
table: `07-a-plugin-a.md` already proved both plugins get this right (mine by fixing the trap it
found; the real one's `hooks/hooks.json` and `scripts/bootstrap-*.sh` invocations use
`${CLAUDE_PLUGIN_ROOT}` throughout), so there is no difference left to report.

| Design property | Yours (`invoice-ledger-tooling`) | The real one (`sdlc-harness`) | Why the difference |
|---|---|---|---|
| Dependencies | None — `dependencies` key absent; every hook, skill, and agent is self-contained | One entry, **unpinned**: `{"name": "ig-superclaude", "marketplace": "ig-superclaude"}` — no `version` key | The real one factors a shared framework (`ig-superclaude`) out into its own product with its own release cadence; yours has nothing shared to factor out. Unpinned trades version safety — the dependency can change under it between installs — for staying in lockstep with that shared framework without a second manual pin to maintain; reasonable inside one organisation where both plugins ship from the same team, less reasonable across an untrusted supply chain |
| Cross-marketplace trust | Not applicable — no dependency, so no other marketplace is ever consulted | `marketplace.json` declares `"allowCrossMarketplaceDependenciesOn": ["ig-superclaude"]` — an explicit allow-list, not implicit trust of whatever a `dependencies` entry happens to name | §4.6.5's own unresolved-dependency proof shows the failure mode this list exists to bound: a dependency naming a marketplace nobody added just sits in the `errors` array forever. The real one names its one trusted marketplace explicitly so that installing `sdlc-harness` can pull `ig-superclaude` automatically without the marketplace author having to trust every marketplace in existence |
| Documentation inside the manifest | `description` fields are short, single-purpose strings — what the plugin is | The real `marketplace.json`'s `description` cites RFC numbers and gives onboarding instructions ("must instruct adding both marketplaces") — prose written for the human reading the file, not for `claude plugin marketplace add`'s parser | Buys a single source of truth: the manifest a human already has open to check `source` paths also carries the reason those paths exist, so the RFC context travels with the config instead of drifting out of sync in a separate README. Costs discoverability the other way — a `$schema`-validating tool, or a future stricter parser, has no obligation to preserve free-text prose, and a long paragraph inside a JSON string is markedly harder to diff in a pull request than the same words in a `.md` file |
| Version discipline | Bumped `1.0.0` → `1.1.0` in this file's own §4.6.4 proof, on a bare local-directory `source` — observed there to not even gate whether a session picks up a new file | `0.10.2`, unchanged since D-59 (`plugins/05-cases-and-conversion.md`) | The real one is presumably installed from a genuinely fetched source (its own marketplace is the thing a teammate adds and installs from, not a scratch directory on one machine), where §4.6.4's finding suggests the version bump is exactly the gate the documentation describes; this file's own local-path proof does not exercise that fetch path, so the two are not proven equivalent — recorded below as open |
| Non-declarative provisioning | None needed — all four hooks, four skills, and three agents are fully expressed by manifest, `hooks.json`, and Markdown; nothing external must be created first | Ships `skills/bootstrap/SKILL.md`, an orchestrator skill (`07-a-plugin-a.md` §4.6.1 already named it as the real dependency-shape reference) that provisions a workspace home, installs `uv`, and clones external handbook repositories — none of which a `plugin.json` can express declaratively | Yours has no environment state to create beyond files the plugin itself ships; the real one depends on tools and clones that live outside any manifest's reach, so it ships an imperative fallback — a skill that runs deterministic scripts — for exactly the gap a plugin manifest cannot close |
| Content-hash version nudging | None — a plain manual `version` bump is the only staleness signal this plugin has | `check-init.sh` hashes `skills/bootstrap/SKILL.md` plus every `scripts/bootstrap-*.sh` with `sha256sum`/`shasum -a 256`, compares it to a marker written by `scripts/bootstrap-write-version.sh`, and nudges a re-run of `/sdlc-harness:bootstrap` on mismatch — explicitly *not* keyed to `plugin.json`'s own `version` field | The real one needs a staleness signal scoped to one specific file set (the bootstrap steps) that can change on a schedule independent of the plugin's overall release `version` — a content hash tracks exactly that subset without demanding a manifest bump for every internal bootstrap edit. Yours has no comparable subset that changes independently of its own single-digit release cadence, so a manual bump is sufficient |

## Pitfalls

- **Belief:** "if `claude plugin update` reports `already at the latest version`, nothing about the
  installed plugin has changed since the last install." **Outcome:** for a local-directory-sourced
  marketplace entry, a brand-new skill file was already visible in a real session with the version
  field untouched and `claude plugin update` reporting no update available. **Fix:** for this source
  shape, treat the marketplace `source` directory itself as the live truth; treat `version` as
  bookkeeping for `claude plugin update`, `list --json`, and dependency pins, not as a gate on
  visibility. **Why people believe it:** `plugins`' own manifest table states the version-gates-updates
  rule without naming an exception for a bare directory `source`.
- **Belief:** "a clean `claude plugin install` plus a clean `claude plugin details` means a plugin's
  dependencies are satisfied." **Outcome:** both succeeded for `invoice-reconciliation-addon` while
  its one skill never became callable in a real session. **Fix:** check `claude plugin list --json`'s
  per-plugin `errors` array, and confirm with an actual session probe. **Why people believe it:**
  neither `install` nor `details` is built to evaluate a fact that depends on a second plugin's
  presence, so both report cleanly on the only thing they actually inspect — this plugin's own files.

## Cheat sheet

| Item | Value |
|---|---|
| §4.6.4 command | `claude plugin update <name> -s <scope> -y` — reports `already at the latest version` or `updated from X to Y... Restart to apply changes` |
| §4.6.4 real finding | Local-directory `source`, `local` scope: a session reads the plugin's skill/agent set live from `source`, independent of `version` — confirmed with zero commands run between the file edit and the observation |
| §4.6.4 what version actually gates | `claude plugin update`'s own before/after report; the version-labelled cache directory (`.../invoice-ledger-tooling/1.0.0` vs `1.1.0`); a dependent plugin's version pin |
| §4.6.4 cost | $0 — `marketplace update`, `plugin update`, `plugin details` are all CLI-level |
| §4.6.5 artefact | `invoice-reconciliation-addon`, one skill, `dependencies: [{"name": "ig-superclaude", "marketplace": "ig-superclaude"}]`, unresolved on purpose |
| §4.6.5 real finding | `install` succeeds silently; `list --json` carries the dependency's `errors` array with `enabled: true` alongside it; `details` reports a full, misleading component inventory; a real session shows the skill absent |
| §4.6.5 fix | Add and trust the missing marketplace, then install the dependency — the exact remedy the `errors` array's own message states |
| §4.6.5 cost | $0 for every CLI check; ≈105 tok always-on is what `reconciliation-report` would cost once resolved, never actually paid while broken |
| §4.6.6 richest diff rows | Unpinned cross-marketplace dependency + explicit `allowCrossMarketplaceDependenciesOn` trust; documentation prose inside a machine-read manifest; a bootstrap skill for non-declarative provisioning; content-hash version nudging decoupled from `plugin.json`'s own `version` |
| §4.6.6 excluded row | `${CLAUDE_PLUGIN_ROOT}` path discipline — already proved identical on both sides in `07-a-plugin-a.md` |
| Cleanup | `plugin uninstall … --scope local` ×2, `plugin marketplace remove` — verified via `list --json` and `.claude/settings.local.json` reverting to `enabledPlugins: {}` |

## Self-test

<details><summary>1. A plugin's version field is left unchanged, but a new skill file is added straight to its marketplace source directory. Will a fresh installed session see the new skill?</summary>
For a marketplace entry whose `source` is a plain local directory path, at `local` scope, yes — confirmed directly: the new skill appeared in a real session with the version field untouched, with no marketplace update or plugin update run in between. The version field still gates what `claude plugin update` reports and what version label the cache directory carries, but it did not gate what the running session actually loaded in this case. Whether the same holds for a git- or URL-sourced marketplace, which involves a real fetch step, was not independently tested here.
</details>

<details><summary>2. `claude plugin install` and `claude plugin details` both report success for a plugin with an unresolved dependency. Does that mean the dependency problem doesn't matter?</summary>
No. Neither command evaluates whether a named dependency is actually installed. `claude plugin list --json` is the command that surfaces it, in a per-plugin `errors` array sitting alongside `"enabled": true`. Confirming the practical effect requires a real session probe — in the reproduced case, the dependent plugin's own skill never became callable at all despite the clean install and clean details output.
</details>

<details><summary>3. What message does claude plugin list --json actually put in a plugin's errors array for an unresolved dependency, and what does it tell you to do?</summary>
`"Dependency \"ig-superclaude@ig-superclaude\" is not installed — run \`claude plugin install ig-superclaude@ig-superclaude\`, or check that its marketplace is added"` — it names the exact plugin@marketplace id that's missing and gives the exact install command, or points at the marketplace-registration step if that's what's actually missing.
</details>

<details><summary>4. Name one design property where invoice-ledger-tooling and the real sdlc-harness plugin genuinely differ on dependencies, and state which is the safer choice and which is the more practical one.</summary>
sdlc-harness carries one unpinned dependency on ig-superclaude (no version key); invoice-ledger-tooling carries none, having nothing shared to depend on. Pinning would be the safer choice for sdlc-harness — an unpinned dependency can change under it between installs — but leaving it unpinned is the more practical one inside a single organisation where both plugins ship from the same team and are expected to move together.
</details>

<details><summary>5. Why does sdlc-harness's check-init.sh use a content hash rather than comparing plugin.json's own version field to decide whether to nudge a bootstrap re-run?</summary>
The signal it needs is scoped to one specific file set — skills/bootstrap/SKILL.md plus the scripts/bootstrap-*.sh scripts — that can change independently of the plugin's overall release version. A content hash over exactly that file set changes precisely when those files change, with nothing to remember to bump; keying it to plugin.json's version would either miss a bootstrap-only edit that didn't warrant a full version bump, or force a version bump for a change that has nothing to do with the plugin's public release history.
</details>

<details><summary>6. What did claude plugin details report for invoice-reconciliation-addon's component inventory, and why was that report misleading?</summary>
It reported `Skills (1) reconciliation-report`, a normal, clean inventory, as if the plugin were fully functional. It was misleading because the skill's dependency on ig-superclaude was unresolved, and a real session confirmed the skill never actually became callable — details reports what the plugin's own files structurally contain, not whether a runtime precondition for using them has been met.
</details>

## Open questions

- **Unverified:** whether the "local-directory `source` resolves live regardless of `version`"
  finding in §4.6.4 also holds for a marketplace entry sourced from git, a GitHub repo, or a hosted
  `.zip` URL — none of which were built for this leaf. `plugins`' own wording for the `version` field
  does not distinguish source types, so a genuinely fetched source may well require the bump exactly
  as documented; this file only confirms the local-path case.
- **Unverified:** whether the same live-resolution behaviour holds at `-s user` or `-s project`
  scope rather than the `-s local` scope used throughout this file and `07-a-plugin-a.md`.

---

**Leaves covered:** 4.6.4–4.6.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-98 in the previous file draws the packaged plugin, its marketplace, the install path and the version-bump panel
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 396
