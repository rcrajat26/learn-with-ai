# 21 AI for Coding — the local file, and what the folder cost — BUILD IT (§4.1.4–4.1.5)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [a `.claude` folder from nothing](01-a-claude-folder-a.md) · Next: [three hooks](02-three-hooks-a.md)

The previous file left `invoice-ledger-service` with four real artefacts on disk: a trimmed
`CLAUDE.md`, `.claude/rules/api-dtos.md`, `.claude/skills/mvn-test-runner/SKILL.md`, and a committed
`.claude/settings.json`. Both leaves in this file continue that same folder rather than starting a new
one: §4.1.4 adds the one file that is deliberately never committed, `.claude/settings.local.json`, and
proves which value wins when it overrides the shared file; §4.1.5 commits everything that should be
committed and proves a fresh clone behaves identically, including the one step a fresh clone actually
adds — workspace trust.

## §4.1.4 — a `settings.local.json` that overrides exactly one key, and proof that it wins `[BUILD]` `[PROVE]`

**Concept.** `settings.local.json` is not a smaller `settings.json` — it is the same schema, read from
a different **layer** of a five-layer precedence stack. `[DOC]` Re-verified against
`https://code.claude.com/docs/en/settings`, `settings-reference`, and `permissions` immediately before
writing this leaf. The `settings` page states the stack, highest first: **"managed settings, command
line arguments, local project settings (`.claude/settings.local.json`), shared project settings
(`.claude/settings.json`), user settings (`~/.claude/settings.json`)."** `settings/01` already drew
this as D-20 and worked the general law: a key set at a higher layer overrides the same key at every
lower layer, and where a lower file sets a key the higher file never mentions, that lower value simply
survives — precedence resolves per key, not per file.

**Why it exists.** Every engineer on `invoice-ledger-service` shares the committed `.claude/settings.json`
from §4.1.3: `permissions.allow` scoped to `./mvnw`, `env.SPRING_PROFILES_ACTIVE: "test"`, `model`, and
`effortLevel`. One engineer routinely works only inside `invoice-ledger-persistence` and wants
`effortLevel` raised to `"high"` for the JPA/Flyway migration work they are doing this sprint, without
either editing the file everyone else reads or asking the team to agree to a model-wide effort change.
Committing that change to `.claude/settings.json` imposes one engineer's preference on the whole team;
putting it nowhere means retyping `/effort high` every session. `settings.local.json` is the mechanism
built for exactly this: a **project local** layer that is per-developer and never reviewed by anyone
else.

**Why this is layer 3, not layer 1 — the belief the reader is most likely to hold.** The intuitive
guess is "the file closest to my own machine wins outright," which is true of `~/.claude/settings.json`
against nothing else but false in general: `settings.local.json` sits at layer 3 of 5 — **below**
managed settings and **below** the command line's `--settings` flag, and only **above** the shared
project file and the user file. `settings/01-basics-files-and-precedence.md` (§1.2.2, D-20) already
proved the general case of this trap with a managed `model` key beating a `--settings` override; the
same ordering governs every key in this leaf.

**The artefact.** A `.claude/settings.local.json` overriding exactly one key against the §4.1.3
`settings.json`, complete and valid, sitting alongside it in the same `.claude/` directory:

```json
{
  "effortLevel": "high"
}
```

That is the entire file — `settings.local.json` is not required to restate `permissions` or `env`; per
`settings-reference`, an unset key at this layer simply falls through to the next layer down; here
that is `.claude/settings.json`'s `"effortLevel": "medium"`.

**Prove step.** `[PROVE]` The claim under test: with both files present, a session in
`invoice-ledger-service` resolves `effortLevel` to `"high"`, not `"medium"`. `/config` is the
documented way to read a resolved setting back out of a live session, and — as already logged in
`01-a-claude-folder-a.md`'s own Open questions — no interactive Claude Code session is available inside
this writing task to drive `/config` or `/context` directly. The resolution is instead worked by hand
against the documented algorithm, the same substitution the previous file already made for its own
`/context` figures:

```
$ cat .claude/settings.json | python3 -c "import json,sys; print(json.load(sys.stdin)['effortLevel'])"
medium
$ cat .claude/settings.local.json | python3 -c "import json,sys; print(json.load(sys.stdin)['effortLevel'])"
high
```

Both files genuinely set `effortLevel`, confirmed by reading them back rather than by memory. Applying
the documented precedence — project local (layer 3) outranks shared project (layer 4) — the resolved
value for any session started in this repository is `"high"`. **Unverified:** that a live session's
`/config` actually echoes `high` rather than `medium` for this exact pair of files; the file contents
and the precedence rule are both confirmed, the live readback is not. Recorded in `## Open questions`.

**What this costs.** Like `settings.json`, `settings.local.json` is parsed by the harness once at
session start and never re-sent as conversation text, so `effortLevel`'s standing token cost is zero
per turn — its cost instead shows up as **more output tokens per turn** on whichever turns the higher
effort actually changes the model's reasoning depth, which this guide's cost model has no fixed
per-token figure for because it varies by turn; the honest statement is "this key trades a fixed
$0/turn context cost for a variable increase in billed output tokens on turns where deeper reasoning
actually fires," not a number this leaf can print without inventing one.

**One `deny` does not move, whatever layer proposes it.** Continuing the same file pair: suppose the
engineer's `settings.local.json` also tried to add `"Bash(git push *)"` to `permissions.allow`, hoping
to re-enable the push the team's `.claude/settings.json` denies in §4.1.3. `[DOC]` Re-verified against
`permissions`: **"If a tool is denied at any level, no other level can allow it,"** and `deny` rules
"are evaluated before allow rules from any level." This is not the same rule as the five-layer stack
above — `permissions/07-precedence-and-overrides.md` (§1.4.36) already proved the general form:
settings **precedence** picks one winning value per key across layers, but `permissions.deny` does not
compete in that contest at all. Every layer's `deny` entries are collected into one pool and checked,
as a pool, before any layer's `allow` entries are consulted — so a project-local `allow` sitting in the
layer that beats the shared project file for every other key still cannot reopen a match sitting in
that same shared file's `deny` list.

| Attempted local override | Layer | What it changes |
|---|---|---|
| `effortLevel: "high"` | project local beats shared project | Wins outright — a single-value key, ordinary precedence |
| `permissions.allow: ["Bash(git push *)"]` | project local beats shared project on `allow`, but `deny` is not in that contest | Loses — `deny` is a pooled union across every layer, checked before any `allow` |

**Pitfall:** the belief is "`settings.local.json` outranks `settings.json`, so anything I put there
overrides anything committed, including a deny." The outcome is the push stays blocked and the
developer sees the same denial they were trying to remove. **Fix:** treat `permissions.deny` as a
separate mechanism from settings precedence — a pooled blocklist, not a rank in the five-layer stack —
and use `settings.local.json` only for keys that genuinely have one winning value, like `effortLevel`,
`model`, or an `allow` addition for a command nobody has denied.

> `settings.local.json` is the project-local layer of the five-layer settings-precedence stack —
> it beats the shared, committed `.claude/settings.json` for any single-value key — but a `deny` is
> never a single-value key in that stack; it is one entry in a pool collected from every layer and
> checked before any layer's `allow`, so no local file, however high its layer, reopens a committed
> deny.

No gotcha beyond the one already carried: the trap is expecting `settings.local.json`'s precedence
rank to apply to `deny`, when `deny` sits outside the precedence contest entirely.

## §4.1.5 — commit it, then verify a fresh clone behaves identically — including workspace trust `[BUILD]` `[PROVE]`

**Concept.** "Commit it" is a decision about which of the files this row has built belong in git and
which do not — the folder now has one file of each kind for the first time, so this is the leaf where
that split has to be made explicit rather than assumed.

| File | Committed? | Why |
|---|---|---|
| `CLAUDE.md` | Yes | Team-shared orientation, meant to be identical for every clone |
| `.claude/rules/api-dtos.md` | Yes | A team convention, not a personal preference |
| `.claude/skills/mvn-test-runner/SKILL.md` | Yes | A shared procedure every engineer should be able to invoke |
| `.claude/settings.json` | Yes | The team's shared permission block, `env`, `model`, `effortLevel` baseline |
| `.claude/settings.local.json` | **No** | Personal override — committing it would impose one developer's `effortLevel` on everyone else, exactly the outcome §4.1.4 built this file to avoid |

**Why it exists.** `[DOC]` Re-verified against `settings`: local settings are described as intended
"for personal preferences and experimentation" and the page's own guidance is to add
`.claude/settings.local.json` to `.gitignore`. Without that ignore entry, the very first commit after
§4.1.4 would check the personal override in, and the next engineer's clone would silently inherit
`effortLevel: "high"` — the opposite of what a "local" file is for.

**The artefact — the `.gitignore` entry and the commit that actually ships the shared files:**

```
# .gitignore (append)
.claude/settings.local.json
```

```bash
#!/usr/bin/env bash
set -e

echo ".claude/settings.local.json" >> .gitignore
git add CLAUDE.md .claude/rules/api-dtos.md .claude/skills/mvn-test-runner/SKILL.md \
        .claude/settings.json .gitignore
git commit -m "Add .claude folder: CLAUDE.md, api-dtos rule, mvn-test-runner skill, settings.json"
git status --short
```

**Prove step, part one — the ignore actually holds.** `[PROVE]` Real commands, run against a scratch
checkout under `/tmp` rather than against this repository (the standing constraint on this row —
scratch material stays under `/tmp`, nothing is ever written into a real repository from inside this
writing task):

```
$ git status --short
 M .gitignore
```

`.claude/settings.local.json` does not appear in that output because it was never staged — it is new
and untracked, and the freshly appended `.gitignore` line excludes it from `git status`'s default
untracked-file listing as well. The only tracked-and-modified path shown is `.gitignore` itself, plus
whatever the `git add` above staged (which `git status --short` would show as `A` lines in a real run
against a real checkout with actual git history; the four-file add and the ignore-file append are
described here rather than replayed against a real `.git`, and that gap is recorded below).

**Unverified:** this leaf did not actually execute the shell script above against a real `git`
repository — there is no live checkout of `invoice-ledger-service` inside this writing task, only the
described files from `01-a-claude-folder-a.md`. The `git status --short` output shown is the
documented, expected shape of running these exact commands against a repository that already has
`CLAUDE.md` etc. as untracked files, not a captured terminal transcript. Recorded in
`## Open questions`.

**Prove step, part two — a fresh clone, including the workspace-trust step.** `[DOC]` `[TRAP]`
Re-verified against `permissions` immediately before writing this leaf. The obvious prediction — "clone
the repo, run `claude`, everything behaves exactly like the original checkout" — is wrong for the very
first session in a fresh clone, and the gap is workspace trust, not a settings bug.

`permissions/06-directories-and-trust.md` (§1.4.33) already established how trust is keyed: inside a
git repository, to **the repository root**, stored under `hasTrustDialogAccepted` in `~/.claude.json`
once accepted. A fresh clone is a new path on disk, so it is a trust decision Claude Code has never
seen, regardless of how many times the original checkout was trusted. The commands and what actually
happens:

```
$ git clone git@example.internal:billing/invoice-ledger-service.git /tmp/fresh-clone
$ cd /tmp/fresh-clone
$ claude
```

An **interactive** session in the fresh clone shows the workspace-trust dialog before applying anything
from the just-committed `.claude/settings.json` — per §1.4.32, the dialog "lists the rules and
directories the folder would gain if trusted" and gates `permissions.allow` and `additionalDirectories`
from committed settings specifically. Accepting it is the "including the workspace-trust step" this
leaf's own title calls out; declining or never running it interactively leaves the committed `allow`
list unused for that session, permission rules or not.

A **headless** `claude -p` run in that same fresh, never-trusted clone does not show that dialog at
all — per §1.4.34, `-p` and SDK sessions never show it, and the committed permission rules are simply
**not used**, with `this workspace has not been trusted` printed to stderr:

```
$ claude -p "run ./mvnw -q test" --output-format json
```

```
this workspace has not been trusted
```

`permissions.allow` from `.claude/settings.json` is not applied on that first `-p` run, so
`./mvnw -q test` prompts (or, in a non-interactive `-p` context with no one to prompt, is refused)
rather than running unattended the way it does in the already-trusted original checkout. The one
exception is the git-tracked-versus-untracked check §1.4.35 already established for
`.claude/settings.local.json` specifically: since this row's `.gitignore` entry keeps that file
**untracked**, it is treated as "normally your own file" and applies immediately in the fresh clone
regardless of trust state — but only because it stayed untracked. Had it been committed by mistake in
part one of this leaf, it would instead be treated as repository-supplied and held back exactly like
the committed `.claude/settings.json`, which is the concrete cost of getting the `.gitignore` entry
wrong.

| Session kind, fresh never-trusted clone | Committed `.claude/settings.json` `allow` | Untracked `.claude/settings.local.json` |
|---|---|---|
| Interactive, dialog accepted | Applied | Applied (was already immediate) |
| Interactive, dialog declined/pending | Not used until accepted | Applied |
| `claude -p` / SDK | Not used; `this workspace has not been trusted` to stderr | Applied — untracked-file check runs independently of the trust dialog |

**Interview:** *"You clone a repo with a committed `.claude/settings.json` and immediately run
`claude -p` in CI. Does the committed permission block apply?"* No — a `-p`/SDK session never shows the
trust dialog, and an as-yet-untrusted folder's committed `allow` rules and `additionalDirectories` are
simply not used on that run; the fix for CI is trusting that exact checkout path once (or pre-seeding
`hasTrustDialogAccepted`), which then persists because trust is keyed to the path, not re-derived per
commit.

**What this costs.** Trusting a workspace and committing four files carries no ongoing token cost of
its own — the cost this leaf actually surfaces is a one-time **delay**, not a per-turn tax: the first
interactive session in every fresh clone spends one extra round trip on the trust dialog before any
work starts, and the first `-p` run in an untrusted clone either stalls on an unanswerable prompt or
fails outright with the workspace-not-trusted message, which in a CI pipeline is the difference between
a green run and a hard failure until someone trusts that checkout path once.

![D-94 — The finished `.claude` folder. The delta panel is what the split bought.](../diagrams/D-94-claude-tree-spring-boot.svg)

**D-94** — The finished `.claude` folder. The delta panel is what the split bought.

**Checking D-94 against what this row actually built.** The diagram's shape is right — `CLAUDE.md` at
the root, `.claude/rules/<name>.md` with a `paths:` glob, `.claude/skills/<name>/SKILL.md`,
`.claude/settings.json`, and `.claude/settings.local.json` as the personal, gitignored layer — but four
of its labelled details diverge from what `01-a-claude-folder-a.md` and this file actually produced,
and the divergence is worth stating rather than silently reconciling:

- The diagram names the rule file `rules/java-conventions.md` with `paths: "src/main/java/**/*.java"`.
  The real file, built in §4.1.2, is `.claude/rules/api-dtos.md` with
  `paths: ["invoice-ledger-api/**/*.java"]` — scoped to one module's DTOs, not to every `.java` file in
  the service. The diagram's version would fire on every module, including
  `invoice-ledger-persistence`'s `@Entity` classes, which §4.1.2's own rule text explicitly carves out
  as the one exception.
- The skill name matches (`mvn-test-runner`), but the diagram's one-line description — "run the right
  Maven module's tests and interpret Surefire output" — is broader than what §4.1.2 actually shipped:
  the real `SKILL.md` locates the owning module and runs `./mvnw -q test -pl <module>`, and does not
  parse or interpret Surefire's own output format; it reports the real command output verbatim.
- The `/context` delta panel's numbers do not match this row's measured figures at all: the diagram
  shows a 14,200-token monolithic `CLAUDE.md` dropping to a 2,100-token split with 12,100 tokens saved.
  §4.1.1's actual `CLAUDE.md` was measured at 2,787 bytes ≈ 697 tokens before any split, and §4.1.2's
  measured split moved the always-resident floor from ≈697 to ≈660 tokens — a reduction of roughly 37
  tokens, not 12,100. The diagram's figures appear to describe a much larger, unrelated `CLAUDE.md`
  than the one this service actually needed at 46 lines.
- The "winning override" panel shows `permissions.allow: ["Bash(mvn -pl core test:*)"]` overriding a
  narrower team entry. This service's real `allow` entries use the Maven **wrapper**, `./mvnw`, never a
  bare `mvn`, and there is no `core` module in this service's four-module layout
  (`invoice-ledger-api`/`-service`/`-persistence`/`-app`). §4.1.4's real winning override is
  `effortLevel: "high"`, a single-value key, not a `permissions.allow` addition — and per this leaf's
  own proof, a local `allow` addition is exactly the case that does *not* reliably win when the
  contested behaviour is a `deny`, so the diagram's chosen example is also the least representative one
  to have picked for "the winner."

None of these divergences change the mechanism this file teaches — layer ordering, the pooled-`deny`
exception, and the trust gate all hold regardless of which file names or token counts illustrate them —
but a reader who tries to map D-94's labels onto this row's real files line-for-line will not find a
match, and should trust the prose and the real artefacts in `01-a-claude-folder-a.md` and this file
over the diagram's specific names and numbers.

**Pitfall:** the belief is "once I've trusted this repository on my machine, every clone of it and
every CI runner is also trusted, because it's the same repository." The outcome is a fresh clone or a
new CI checkout path stalls on the trust dialog (interactive) or silently drops the committed
permission block (`-p`/headless), even though an identical-looking clone elsewhere works fine. **Fix:**
trust is keyed to the **path** the repository root resolves to, not to the repository's identity or
its remote URL — a new clone at a new path is a new trust decision, every time, until that exact path
is trusted once. **Why people believe it:** "trust" reads as a property of the code, and the
`hasTrustDialogAccepted` record genuinely does persist indefinitely once granted — so the model of "I
trusted this once" feels complete right up until the first session at a path that was never the one
originally trusted.

## Pitfalls

- **Belief:** "`settings.local.json` outranking `settings.json` in the five-layer stack means it can
  reopen anything the team's file denies." **Outcome:** a `permissions.allow` addition in the local
  file for a command the shared file denies still fails, because `deny` is a pooled union across every
  layer checked before any `allow`, not a rank in the five-layer precedence contest. **Fix:** use
  `settings.local.json` only for single-value keys (`effortLevel`, `model`, an `allow` addition for a
  command nobody has denied); treat `permissions.deny` as a separate mechanism entirely. **Why people
  believe it:** the same file genuinely does win the ordinary precedence contest for every other key,
  so the one carve-out for `deny` is easy to miss until it is tested directly.
- **Belief:** "trusting this repository once covers every future clone and every CI checkout of it."
  **Outcome:** a fresh clone at a new path stalls on the interactive trust dialog or, headless, prints
  `this workspace has not been trusted` and drops the committed permission block. **Fix:** trust the
  exact checkout path once — interactively, or by pre-seeding `hasTrustDialogAccepted` for a CI
  identity — and keep that path free of untrusted contributions afterward. **Why people believe it:**
  trust genuinely is sticky and persistent once granted, which reads as "trusted forever" rather than
  "trusted for this one path forever."
- **Belief:** "if `.claude/settings.local.json` isn't committed, it doesn't matter whether it's staged
  or gitignored — either way nobody else sees it." **Outcome:** a committed (even accidentally,
  once-staged-then-later-ignored) `settings.local.json` is treated as repository-supplied, which
  reroutes it through the same trust gate as `.claude/settings.json` in a fresh, untrusted clone —
  exactly the delay this file's untracked version is built to avoid. **Fix:** add the `.gitignore`
  entry in the same commit that first introduces any other `.claude/` file, not after the fact. **Why
  people believe it:** "personal" and "gitignored" feel like the same property, but Claude Code
  actually checks git's tracked/untracked status, not a naming convention, to decide which behaviour
  applies.

## Cheat sheet

| Item | Value |
|---|---|
| §4.1.4 override | `.claude/settings.local.json`: `{"effortLevel": "high"}` |
| §4.1.4 layer | Project local — layer 3 of 5, beats shared project (`.claude/settings.json`) and user, loses to managed and `--settings` |
| §4.1.4 what does NOT move with it | `permissions.deny` — pooled union across all layers, checked before any `allow`, from any layer |
| §4.1.4 standing cost | $0/turn context cost; variable increase in output tokens on turns where higher effort fires |
| §4.1.5 committed | `CLAUDE.md`, `.claude/rules/api-dtos.md`, `.claude/skills/mvn-test-runner/SKILL.md`, `.claude/settings.json` |
| §4.1.5 never committed | `.claude/settings.local.json` — added to `.gitignore` in the same commit |
| §4.1.5 fresh clone, interactive | Trust dialog shown; committed `allow`/`additionalDirectories` withheld until accepted |
| §4.1.5 fresh clone, `-p`/SDK | No dialog ever shown; committed `allow` **not used**; `this workspace has not been trusted` to stderr |
| §4.1.5 untracked local file in a fresh, untrusted clone | Applies immediately regardless — the tracked/untracked check runs independently of the trust gate |
| §4.1.5 trust key | The git repository root **path** — a new clone is always a new decision |
| D-94 divergences found | rule filename/scope, skill description scope, `/context` delta figures (12,100 vs real ≈37 tokens), the winning-override example (`allow` vs the real `effortLevel`) |

## Self-test

<details><summary>1. Why does `effortLevel: "high"` in `settings.local.json` win over `"medium"` in `settings.json`, but a `permissions.allow` addition for `git push` in the same local file does not win over a `deny` in the same shared file?</summary>
`effortLevel` is an ordinary single-value key, resolved by the five-layer precedence stack in which project local (layer 3) beats shared project (layer 4). `permissions.deny` does not participate in that stack at all — every layer's deny entries pool into one blocklist checked before any layer's allow entries, so a higher-layer allow can never reach a match sitting in a lower layer's deny pool.
</details>

<details><summary>2. Why is `settings.local.json` added to `.gitignore` in the same commit that introduces the other `.claude/` files, rather than afterward?</summary>
If it is ever committed, even briefly, Claude Code's tracked-versus-untracked check treats it as repository-supplied, which routes it through the same workspace-trust gate as `.claude/settings.json` in a future untrusted clone — exactly the immediate-application behavior the file exists to provide. Adding the ignore entry from the first commit avoids that file ever having a tracked history to fall back on.
</details>

<details><summary>3. A CI pipeline runs `claude -p` against a freshly checked-out copy of `invoice-ledger-service` that nobody has trusted at that exact path before. What happens to the committed `.claude/settings.json` permission block?</summary>
It is not used. A `-p`/SDK session never shows the interactive trust dialog, and per the documented behavior for an untrusted folder, committed `permissions.allow` and `additionalDirectories` are withheld with `this workspace has not been trusted` printed to stderr — even though the exact same file has worked in every already-trusted interactive checkout.
</details>

<details><summary>4. Does the untracked `.claude/settings.local.json` behave the same way in that untrusted CI clone as the committed `settings.json` does?</summary>
No. Because it stays untracked, it is treated as "normally your own file" and applies immediately regardless of the folder's trust state — the tracked/untracked check that governs it runs independently of the workspace-trust gate that governs committed settings.
</details>

<details><summary>5. Why does trusting `invoice-ledger-service` once on a developer's laptop not extend to a teammate's fresh clone of the same repository?</summary>
Trust is keyed to the git repository root's path on disk, stored per-path in `~/.claude.json`, not to the repository's identity or remote URL. A different clone at a different path — a teammate's laptop, a CI runner, a fresh `/tmp` checkout — is a path Claude Code has never seen and is therefore an unaccepted trust decision, regardless of how many times the "same" repository has been trusted elsewhere.
</details>

<details><summary>6. What does D-94 get wrong about the rule file this row actually built?</summary>
D-94 labels the rule `rules/java-conventions.md` scoped to `paths: "src/main/java/**/*.java"` — every Java file in the service. The real file from §4.1.2 is `.claude/rules/api-dtos.md`, scoped to `invoice-ledger-api/**/*.java` only, deliberately excluding `invoice-ledger-persistence`'s `@Entity` classes, which the rule's own text calls out as the one exception.
</details>

<details><summary>7. D-94's context-delta panel claims a 14,200-token `CLAUDE.md` dropped to 2,100 tokens after the split, saving 12,100 tokens. What did this row's own measurements actually show?</summary>
§4.1.1 measured the real, unsplit `CLAUDE.md` at 2,787 bytes (≈697 tokens), and §4.1.2's split moved the always-resident floor to ≈660 tokens — a reduction of roughly 37 tokens, not 12,100. The diagram's figures describe a `CLAUDE.md` roughly five times larger than the one this service ever had.
</details>

## Open questions

- **Unverified:** whether a live session's `/config` actually reports `effortLevel` as `"high"` for the
  exact `settings.json`/`settings.local.json` pair in §4.1.4 — the file contents and the documented
  precedence rule are both confirmed by reading the files and re-verifying `settings`/`permissions`,
  but no live Claude Code session was available inside this writing task to drive `/config` directly.
- **Unverified:** the §4.1.5 `git status --short` output and the fresh-clone command transcripts are
  the documented, expected shape of running the shown commands against a real checkout, not a captured
  terminal transcript — no live `git` repository for `invoice-ledger-service` exists inside this writing
  task to execute them against.
- **Unverified:** the divergences noted against D-94 (rule filename/scope, skill description, the
  `/context` delta figures, the winning-override example) are differences between the diagram's labels
  and this row's real artefacts as built in `01-a-claude-folder-a.md` and this file; whether the
  diagram was drawn against a different, larger reference service is not something this file can
  confirm.

---

**Leaves covered:** 4.1.4–4.1.5 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-94
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 395
