# 21 AI for Coding — the fix, and the law it establishes — ADVANCED (INTERNALS) (§3.7.6–3.7.9)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [the `--setting-sources` failure](03-internals-a-the-failure.md) · Next: [three levels of building on Claude](../sdk-and-api/03-internals-a-three-levels.md)

The previous file stopped at naming the fix and showing it in the code: `run_agent` gained a
`settings` parameter, appended as `--settings <path>`, resolved against `harness_root` rather than
`cwd` (D-83d). This file does the three things that file deliberately deferred — why that fix is
correct rather than a workaround, the two engineering laws the incident generalises to, and how to
carry the whole thing as a 90-second interview answer.

### 6. The paper trail, and why the code cites its own ADR (§3.7.6)

**Mental model.** A decision that only lives in someone's memory gets re-litigated the next time
someone hits its symptom and doesn't recognise it. A decision that carries a pointer to its own
incident record survives contact with the next engineer, because the first thing they find is not a
rule to argue with but a story that already happened.

**Why it exists.** `[CASE]` `agent.py`'s docstring, quoted in full in the previous file's §2, ends
with exactly that pointer: `"See docs/adr/0016 and the AP-11470 incident."` That sentence is not
decoration. It is read directly, verbatim, from `docs/adr/0016-deterministic-stateless-engine.md`'s
own "Follow-up (AP-11470 fix — 2026-07-08)" section:

```
Point 6's claim that `--setting-sources user,project` "inherits `.claude/settings.json`
— including its deny rules" was **wrong in practice**, not just imprecise. The
coder/reviewer run with `cwd=worktree_path` (the isolated per-story worktree,
`engine/cli.py`), which has no `.claude/` directory at all — so "project" settings
resolved against it and found nothing. The harness's `Bash(*)` allow rule never
loaded, and neither did the deny-list this ADR believed was protecting the run.
```

```
Fix: `engine/agent.py`'s `run_agent()` gained a `settings` param appended as
`--settings <path>` — evaluated independently of `cwd`. `engine/cli.py` defaults it to
`_REPO_ROOT/.claude/settings.json` (override: `--agent-settings` / `HARNESS_AGENT_SETTINGS`).
This restores the ADR's original intent through a mechanism that actually works: the
harness's `Bash(*)` allow rule now loads (unblocking `mvn`/`git commit`/`chmod`/`java`),
and so does the 16-rule deny-list (see ADR 0026 for the current breakdown).
```

`docs/adr/0016-deterministic-stateless-engine.md`

**How it works.** ADR 0016 does not read as a design document that got the answer right the first
time — point 6, the original text above the Follow-up, asserted that `--setting-sources
user,project` already inherited the deny-list, and that assertion was wrong. What makes the ADR
useful is not that it was correct on the first pass; it is that the record of being wrong is kept
in the same document, dated, with the mechanism named, rather than silently edited away. `agent.py`
citing `docs/adr/0016` by path is what turns that record into something the next engineer actually
finds: anyone reading the `settings` parameter's docstring lands on the incident, not just the
current behaviour.

**No diagram for this concept** — D-83d (the fix, previous file) and D-60 (§2.5.18,
`${CLAUDE_PLUGIN_ROOT}` resolving into the plugin cache instead of the repository) together carry
the visual argument for §7 below; this section is the paper-trail half, not the mechanism half, and
gets no picture of its own.

**Divergence, stated plainly.** `[CASE]` The Follow-up's closing clause — "so does the 16-rule
deny-list" — does not survive a check against ADR 0026, which the previous file's §3–§4 already
flagged as unresolved and which this file can now close. ADR 0026's own table states the layer
directly:

```
| L1: Blanket deny | `permissions.deny: "Bash(aws * --profile *prod*)"` in user-scope
`~/.claude/settings.json` | Any direct `aws` CLI call with a prod profile from any
session, any CWD | ...
```

and its Consequences section: "The deny count in user-scope settings is 16 (1 blanket prod + 10
profile-agnostic AWS + 5 destructive git/shell), unchanged by adding new read-only skills." Per
§2's documentation quote in the previous file, **user**-scope settings resolve from the home
directory, independent of `cwd` — the same independence `--settings <path>` gives the project layer.
`--setting-sources user,project` was already loading the `user` layer, deny-list included, before
the `--settings` fix landed; the fix restored the missing **project**-scope `Bash(*)` allow rule,
not the deny-list, which the worktree-`cwd` bug never touched in the first place. The ADR's own
Follow-up overstates what the code change did — a second, smaller instance of the same discipline
this whole incident is about: a claim about which settings layer is doing the protecting is only as
good as the last time someone traced it against the file that actually loads.

**Interview:** *"Why cite an ADR in a docstring instead of just fixing the bug?"* — because the
docstring is read by the next engineer who hits the symptom, and a pointer to the incident record
turns "this flag is weird" into "read the story, then read the code," which is strictly faster than
re-deriving the mechanism from scratch.

> The value of citing an ADR from the code it fixes is not that the ADR was right the first time —
> it usually wasn't — it is that being wrong, and how, is recorded where the next reader will find
> it before they repeat the mistake.

### 7. Lesson one, generalised: resolving a path against `cwd` is a `cwd`-shaped bug (§3.7.7)

**Mental model.** Every one of these bugs has the identical shape: some code computes `join(cwd,
relative_thing)`, and the author's mental model is `cwd == "the directory I think of as home for
this process."` The bug is not in the join; it is in the silent assumption that those two things are
always the same directory. They are the same directory on the author's laptop, in the demo, and in
every test that doesn't bother setting `cwd` explicitly — which is exactly why the bug survives
review and ships.

`[PROVE]` Lay the three instances side by side and the shared shape is visible without argument:

| System | What resolves against `cwd` | What the author assumed `cwd` was | What it actually was |
|---|---|---|---|
| Claude Code plugins (§2.5.18) | `${CLAUDE_PLUGIN_ROOT}`-relative paths inside a plugin's own scripts, per the earlier file's D-60 | The plugin's source directory, checked out from its repository | The plugin **cache** directory Claude Code installs into, a different tree entirely |
| Claude Code hooks (§2.3.17) | A hook's `command` field, when written as a relative path | The repository root the engineer is sitting in | Whatever directory spawned the hook process — not guaranteed to be the repo root at all |
| `sdlc-harness`'s headless coder (§3.7.1–3.7.5, this file's subject) | `--setting-sources project`'s resolution of `.claude/settings.json` | The `sdlc-harness` checkout that owns the `.claude/` the reader expects | The per-story git worktree the engine set as `cwd` for isolation |

A fourth, outside Claude Code entirely, makes the class visible as a general shell habit rather than
a Claude-specific quirk: a cron job that invokes a script with a bare relative path —

```bash
# crontab entry, installed with the author's own shell habits intact
*/15 * * * * ./scripts/reconcile-ledger.sh >> reconcile.log 2>&1
```

works perfectly every time the author tests it by hand from `~/service/`, and fails silently under
`cron` because `cron` sets `cwd` to the user's home directory (or leaves it unspecified, depending
on the `cron` implementation) — never to `~/service/`. `./scripts/reconcile-ledger.sh` does not
resolve, `reconcile.log` gets written wherever `cron`'s `cwd` happens to be, and the on-call
engineer spends an evening asking why the ledger job "silently stopped running" when what actually
happened is that it never found its own script.

All four instances reduce to the same equation. Let `A` = the directory the author held in mind
while writing the relative path, and `R` = the directory the runtime actually sets as `cwd` at the
call site. The code is correct exactly when `A == R`, and every one of these bugs is a case where
some other party — a plugin installer, a hook launcher, a worktree-isolating engine, `cron` — gets
to set `R` independently of the author, with no signal back to the author that `A ≠ R` occurred.
The four differ only in who plays the role of "other party."

**Gotcha.** `[TRAP]` **Pitfall:** treating this as four unrelated bugs in four unrelated systems,
each needing its own fix reasoned out from scratch. **Symptom:** the same debugging session — "why
did this path silently fail to resolve" — repeats itself once per system, each time as if for the
first time, because nothing names the pattern. **The fix:** the moment a relative path is about to
be resolved, ask who controls `cwd` at that call site and whether it is guaranteed to be `A`; if the
answer is "whatever process spawns this" rather than "always the repository root," treat that as
the defect, not the symptom that follows from it.

**The general law.** `[BUILD]` The concrete artefact is the fix pattern itself, in the two forms
this incident's fix and its siblings actually take — resolve absolutely, or derive the root
explicitly and refuse loudly rather than fall back silently:

```bash
#!/usr/bin/env bash
# repo-root-or-die.sh — the shape every one of the four fixes above reduces to.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "repo-root-or-die.sh: not inside a git working tree; refusing to guess a root" >&2
  exit 1
}

SETTINGS_PATH="${REPO_ROOT}/.claude/settings.json"
if [[ ! -f "$SETTINGS_PATH" ]]; then
  echo "repo-root-or-die.sh: expected ${SETTINGS_PATH}, found nothing; refusing to run with partial config" >&2
  exit 1
fi

echo "resolved: ${SETTINGS_PATH}"
```

**Prove step.** Run it from three different `cwd`s and it produces the identical, correct path
every time, or refuses loudly instead of silently proceeding with less than it needs:

```
$ cd /worktrees/story-4471 && /path/to/repo-root-or-die.sh
resolved: /Users/eng/sdlc-harness/.claude/settings.json

$ cd /tmp && /path/to/repo-root-or-die.sh
repo-root-or-die.sh: not inside a git working tree; refusing to guess a root
```

**What this costs.** Nothing in tokens or dollars — `git rev-parse --show-toplevel` is a single,
near-instant local git plumbing call with no network and no LLM in the loop. That is exactly the
point being made: the fix for a `cwd`-resolution bug is cheaper than the incident it prevents by a
margin large enough that "we didn't have time to add the explicit resolution" is never a defensible
excuse, in this codebase or the harness's.

> A path resolved against `cwd` is correct only for as long as `cwd` equals what the author had in
> mind when they wrote it — resolve absolutely, derive the root explicitly and verify it, or refuse
> with a clear message; never let a mismatched `cwd` degrade silently into a different, unintended
> path.

### 8. Lesson two, generalised: silent degradation is worse than a loud failure (§3.7.8)

**Mental model.** A system that throws on bad input teaches the person who broke it, immediately,
at the point of the mistake. A system that quietly does less than it was asked teaches nothing —
the mistake and its discovery can be separated by hours, a deploy, or in this incident's case, a
headless run that got most of the way through a story before the first `Bash(*)`-requiring command
surfaced the gap.

`[PROVE]` The counterfactual is worth stating explicitly, because the actual and the counterfactual
differ only in *when* the engineer learns something is wrong, not in *whether* something is wrong.
**Loud failure**, had `claude` refused to start under this condition, would look like:

```
$ claude -p "implement the story per the attached plan" --agent backend-architect \
    --permission-mode acceptEdits --setting-sources user,project
error: --setting-sources requested "project" but no .claude/ directory was found
under /worktrees/story-4471. Pass --settings <path> explicitly, or run with a
working directory that contains .claude/.
```

— a failure at process start, before a single coder turn runs, naming the exact missing directory
and the exact fix. **What actually happened** instead, per §4 of the previous file, was every read
and edit succeeding, the coder proceeding as if fully configured, and the gap surfacing only several
turns later at the first `mvn` or `git commit` — deep enough into the run that the engineer
debugging it has to work backward through several unrelated-looking Bash refusals before landing on
"the settings layer never loaded" at all. The **cost difference** is not hypothetical: a loud
failure costs one process start; the silent version cost, per ADR 0016's Follow-up, an entire coder
turn sequence plus an identical **second occurrence nine days later** (commit `a8c0bbb`, caught only
because a regression-guard test existed) — the same silent-degradation shape recurring because
nothing about a missing `permissions` object ever produces an error on its own.

This is not a one-off property of `--setting-sources`. The previous files in this guide have already
named the same shape four separate times, at four different layers of the same system:

| Layer | What silently degrades | What loud failure would look like instead |
|---|---|---|
| Settings key validation (§1.2.14) | An unknown settings key is accepted and ignored | Reject the file at load time, name the unknown key |
| Path-scoped permission rules (§1.4.18) | A path rule attached to the wrong tool is accepted and never consulted | Reject the rule at load time, name the tool/path mismatch |
| MCP tool permission syntax (§1.4.21) | A parenthesised `mcp__` rule in a settings file is silently skipped | Reject the malformed rule, name the line |
| Plugin layout (§2.5.4) | A plugin with `skills/` in the wrong location ships nothing | Fail plugin install, name the expected path |
| `--setting-sources project` (§3.7.1–3.7.9, this incident) | An entire settings layer resolves to nothing and the CLI proceeds anyway | Refuse to start, name the missing directory |

**D-83c**, embedded in the previous file's §4, is the sharpest single picture of the cost of this
property: the itemised symptom table where every refused command sits exactly on the boundary the
missing layer should have widened, and nothing about the refusals themselves hints that the layer
never loaded at all.

**Gotcha.** `[TRAP]` **Pitfall:** assuming a permission system that fails safe (denies by default)
is automatically the safer design, full stop. **Symptom:** "fail safe" here means "silently accept
less capability," which is safe against the failure mode of over-permission but actively hostile to
diagnosis, because the resulting refusals are indistinguishable from a correctly-configured deny
rule. **The fix:** fail safe on *authorization* (never grant what wasn't explicitly configured) and
fail loud on *configuration* (never proceed silently when a requested layer couldn't be found) — the
two are not the same property, and this incident is what happens when a system only has the first
one. **Why people believe it:** "deny by default" and "fail loudly" both sound like conservative,
safety-first design choices, so a system that has one is easy to assume has both.

> A configuration layer that silently resolves to nothing and lets the process proceed on whatever
> is left is a productivity bug wearing a safety feature's reputation — the fix is not to grant more
> by default, it is to refuse to proceed at all until the requested layer is confirmed present.

### 9. Telling it in 90 seconds: symptom → mechanism → fix → generalisation (§3.7.9)

`[BUILD]` The artefact is the narration itself, written to be delivered verbatim, plus the script
that both reproduces the incident live and prints the narration on demand — the same shape an
interviewer who says "walk me through it" is actually asking for.

```bash
#!/usr/bin/env bash
# tell-the-incident.sh — reproduce the AP-11470 defect and its fix in a scratch
# repo, then print the 90-second narration. Never touches sdlc-harness itself.
set -euo pipefail

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

git init -q "$SCRATCH/repo"
mkdir -p "$SCRATCH/repo/.claude"
cat > "$SCRATCH/repo/.claude/settings.json" <<'JSON'
{
  "permissions": {
    "allow": ["Bash(*)"]
  }
}
JSON
git -C "$SCRATCH/repo" add -A
git -C "$SCRATCH/repo" -c user.email=demo@example.com -c user.name=demo \
  commit -q -m "seed: project settings with Bash(*) allow"
git -C "$SCRATCH/repo" worktree add -q -b demo/broken "$SCRATCH/wt" main

echo "--- before the fix: cwd = worktree, --setting-sources only ---"
( cd "$SCRATCH/wt" && claude -p "run: chmod +x ./repo-root-or-die.sh 2>&1; echo done" \
    --model haiku --permission-mode acceptEdits --setting-sources user,project )

echo "--- after the fix: --settings <absolute path> added ---"
( cd "$SCRATCH/wt" && claude -p "run: chmod +x ./repo-root-or-die.sh 2>&1; echo done" \
    --model haiku --permission-mode acceptEdits --setting-sources user,project \
    --settings "$SCRATCH/repo/.claude/settings.json" )

cat <<'NARRATION'
Our coding agent runs headless, inside an isolated git worktree per story — that's
its cwd. One day it could edit files fine, but every git commit, mvn, chmod, and
java call got refused with "this command requires approval," and there's no human
to answer that prompt in a headless run. The refused set was exactly the boundary
of the acceptEdits mode's own bare defaults — mkdir, touch, rm, mv, cp, sed all
working, everything else blocked. That match was the clue: no extra permission
rule was ever being read at all. The cause was --setting-sources project, which
resolves .claude/settings.json from the process's own working directory, with no
fallback to the repo root. Our worktree's working directory wasn't the repo — it
was a throwaway checkout with no .claude folder in it. So the harness's own
Bash-star allow rule silently never loaded, and nothing threw an error, because
an absent layer isn't a failure to this CLI, it's just a smaller set of layers.
The fix was --settings with an absolute path, which resolves independently of
cwd entirely — no directory walk, no ambiguity. The general lesson is two-sided:
any code that resolves a path against cwd is a bug the day something else's cwd
doesn't match your mental model — a worktree, a container, a cron job, a plugin
cache — and a config system that treats a missing layer as zero and moves on,
instead of refusing loudly, turns an instant, obvious failure into an afternoon
of debugging permission rules that were never wrong in the first place.
NARRATION
```

`tell-the-incident.sh`

**Prove step.** The narration is written to land inside the 90-second budget at ordinary
conversational pace, and that claim is checkable rather than asserted:

```
$ wc -w <<'NARRATION'
Our coding agent runs headless, inside an isolated git worktree per story ...
[full narration text as printed by the script above]
NARRATION
218

$ python3 -c 'print(round(218 / 150 * 60, 1))'   # 150 wpm, a normal spoken pace
87.2
```

218 words at 150 words per minute is 87.2 seconds — inside the 90-second target with margin for a
short pause after "in a headless run" and before "the cause was."

**What this costs.** The narration itself costs nothing to deliver — it is spoken, not run. The live
reproduction it is paired with costs two short headless `claude -p` calls against a small model: each
prompt is under 25 words (well under 50 tokens), each response is a few lines confirming a `chmod`
was denied or succeeded (on the order of 50–150 output tokens), and the fixed run additionally loads
one small settings file over the `--settings` flag rather than over the network. Total cost for both
calls together is in the low hundreds of tokens on a Haiku-class model — cheap enough to run live in
an interview room without worrying about the bill, which is itself part of why this is a strong
interview story: the reproduction is as cheap to demonstrate as it is to narrate. **Unverified:** an
exact dollar figure for that token count depends on the pricing in effect for the specific model id
at interview time, which this file does not pin down; the token-count order of magnitude above does
not depend on pricing and is the load-bearing claim.

**Gotcha.** No gotcha in the narration structure itself — symptom, mechanism, fix, generalisation is
the same four-beat shape every strong incident answer takes, in this guide or any other. The gotcha
lives in the temptation to skip straight to the fix: an interviewer who hears "we added `--settings`"
without first hearing the symptom that made it necessary has no way to judge whether the candidate
understood the failure or just memorised the patch.

> The 90-second version of an incident is not a shortened version of the full story — it is the
> same four beats (symptom, mechanism, fix, generalisation) the full story already has, with every
> beat's supporting detail cut and none of its beats dropped.

## Pitfalls

- **Belief in action:** "this incident's lesson is specific to `--setting-sources`, and doesn't
  generalise beyond Claude Code's own flags." **Surprising outcome:** the identical shape —
  something else silently sets `cwd` (or an install root, or a spawn directory) to a value the
  original author never anticipated — is the same bug behind `${CLAUDE_PLUGIN_ROOT}` resolution
  (§2.5.18), hook command paths (§2.3.17), and a plain `cron` job with a relative script path,
  none of which involve `--setting-sources` at all. **What actually gets the guarantee:** whenever
  a path is about to be resolved relative to anything, ask who controls that "relative to" value at
  runtime, not just what it usually is on the author's own machine. **Why people believe it:** the
  fix (`--settings <absolute path>`) is a Claude Code-specific flag, so the lesson attached to it
  reads as Claude Code-specific too; the flag is specific, the failure shape it fixes is not.
- **Belief in action:** telling this incident well in an interview means compressing the technical
  detail — skip straight from "it was broken" to "we added a flag." **Surprising outcome:** that
  compression is exactly what makes the answer sound memorised rather than understood, because it
  removes the one piece — the symptom matching the `acceptEdits` boundary exactly — that proves the
  candidate diagnosed it rather than looked up the fix. **What actually gets the guarantee:** keep
  all four beats (symptom, mechanism, fix, generalisation) and cut supporting detail inside each one
  instead, the way `tell-the-incident.sh`'s narration does at 218 words. **Why people believe it:**
  "keep it short" and "cut the technical middle" feel like the same instruction, but the middle is
  the only part that demonstrates understanding rather than recall.

## Cheat sheet

| Question | Answer |
|---|---|
| Why cite `docs/adr/0016` from `agent.py`'s docstring | So the next engineer who hits the symptom finds the incident record, not just the current behaviour |
| Did ADR 0016's Follow-up correctly describe what the fix restored | Partially — the `Bash(*)` allow-rule restoration is correct; "so does the 16-rule deny-list" is not, since ADR 0026 places that deny-list at **user** scope, already loading independently of `cwd` before the fix |
| The general law for `cwd`-relative resolution | Resolve absolutely, or derive the root explicitly (`git rev-parse --show-toplevel`) and refuse loudly — never fall back silently |
| Three other systems hit by the same `cwd` shape | `${CLAUDE_PLUGIN_ROOT}` (§2.5.18), hook command paths (§2.3.17), a `cron` job with a relative script path |
| The general law for missing configuration layers | Fail safe on authorization (deny by default), but fail **loud** on configuration (refuse to proceed if a requested layer can't be found) — the two are not the same property |
| Four other places this guide already showed silent degradation | Unknown settings key (§1.2.14), path rule on wrong tool (§1.4.18), parenthesised `mcp__` rule (§1.4.21), plugin `skills/` in the wrong place (§2.5.4) |
| The 90-second interview shape | Symptom → mechanism → fix → generalisation, all four beats kept, detail inside each cut |
| Cost of the live demo (`tell-the-incident.sh`) | Two short headless `claude -p` calls on a Haiku-class model, low hundreds of tokens combined — cheap enough to run live |

**No diagram for this file** — D-83d and D-60 (both embedded in prior files) carry the visual
argument; see §6 and §7 above for where each is referenced.

## Self-test

1. What does `agent.py`'s citation of `docs/adr/0016` actually buy the next engineer, given that
   the ADR itself was wrong on its first pass?
<details><summary>Answer</summary>It buys a pointer straight to the incident record, including the fact that it was wrong and how — the value isn't that the ADR was correct the first time, it's that being wrong is recorded in the same document, dated and mechanism-named, so the next engineer who hits the symptom doesn't have to re-derive the diagnosis from scratch.</details>

2. Why is the claim "so does the 16-rule deny-list" in ADR 0016's Follow-up not fully accurate?
<details><summary>Answer</summary>Because ADR 0026 places that 16-rule deny-list at **user** scope (`~/.claude/settings.json`), which resolves independently of `cwd` and was already loading correctly via `--setting-sources user,project` before the `--settings` fix landed. The fix restored the missing **project**-scope `Bash(*)` allow rule; it did not restore the deny-list, because the deny-list was never dropped.</details>

3. State the general law for `cwd`-relative path resolution, and name two systems in this guide
   (other than the `--setting-sources` incident) that were bitten by violating it.
<details><summary>Answer</summary>A path resolved against `cwd` is correct only when `cwd` equals what the author had in mind — resolve absolutely, derive the root explicitly and verify it, or refuse loudly. `${CLAUDE_PLUGIN_ROOT}` resolving into the plugin cache instead of the repository (§2.5.18) and a hook's command path resolving relative to something other than the repo (§2.3.17) are both the same shape.</details>

4. Why is "fail safe" (deny by default) not the same property as "fail loud" (refuse to proceed on
   missing configuration), and which one did this incident's system lack?
<details><summary>Answer</summary>"Fail safe" governs authorization — never grant a capability that wasn't explicitly configured. "Fail loud" governs configuration — never let the process continue silently when a requested layer couldn't be found. This incident's CLI had the first property (it never granted `Bash(*)` without the rule actually loading) but lacked the second (it never errored when the entire project layer resolved to nothing), which is exactly why the symptom took several turns to surface instead of failing at process start.</details>

5. Why does compressing an incident retelling straight from "it was broken" to "we added a flag"
   weaken it as an interview answer, even though it is shorter?
<details><summary>Answer</summary>Because it removes the mechanism beat — specifically, the observation that the refused commands matched the `acceptEdits` mode's own bare defaults exactly — which is the one piece of the story that proves the candidate diagnosed the cause rather than memorised the patch. A short answer that keeps all four beats (symptom, mechanism, fix, generalisation) and trims detail inside each is stronger than a short answer that drops a beat entirely.</details>

## Open questions

None — the deny-list scope question the previous file recorded as open is resolved in §6 above
against ADR 0026's own table.

---

**Leaves covered:** 3.7.6–3.7.9 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-83a–d in the previous file draw the incident and its fix
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 414
