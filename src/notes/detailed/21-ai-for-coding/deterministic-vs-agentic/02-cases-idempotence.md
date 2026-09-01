# 21 AI for Coding — idempotence and human authority — INTERMEDIATE (§2.8.6–2.8.9)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [script or prompt: the central judgment](01-the-central-judgment.md) · Next: [the threat model](../governance/01-the-threat-model.md)

**No diagram in this file.** The manifest gives this row no `D-NN` id — the decision tree lives one
file back at D-65 (`01-the-central-judgment.md`), and the mechanism-selection tree it feeds into is
D-41 in `skills/06-builtins-and-decision-table.md`. Reference both by id; the six-link chain's "SVG"
link is not applicable here, per the writer contract.

## 1. Idempotence: the property that makes a bootstrap safe to re-run

**Mental model.** A script that is idempotent behaves like a thermostat, not like a light switch you
flip once. Run it against a machine already in the target state and it looks at that state, sees
nothing to do, and says so — it never "flips" a second time and breaks something that was already
correct. Run it against a machine in *any* other state and it moves that machine to the same target
state, regardless of how it got there. The property is not "the script is safe to run" — a script
that always does its one action is also "safe" the first time — the property is specifically that
**running it a second, third, or tenth time changes nothing beyond the first successful run.**

**Why it exists.** The previous file (§2.8.1–2.8.5) established the underlying rule: if the inputs
determine one correct answer, a script computes it, with no sampling step and no drift between runs.
Idempotence is that same rule applied across *repeated invocations of the same script* rather than
across a single run: given the same starting filesystem/JSON/PATH state, the transform still has
exactly one correct output, and that output is "no-op" whenever the target state is already reached.
Without it, an orchestrating skill would have to track, separately from the scripts themselves, which
steps already ran — a second and independently fallible piece of state, exactly the kind of
bookkeeping a deterministic script is supposed to remove rather than add.

**How it works.** `[CASE]` The mechanism is a guard clause at the top (or inline at the point of
effect) that detects the already-done state and exits before doing any work. Read from
`plugins/sdlc-harness/scripts/bootstrap-uv.sh`:

```bash
if command -v uv >/dev/null 2>&1; then
  echo "SKIPPED: uv already installed ($(uv --version 2>/dev/null || echo present))"
  exit 0
fi
```

`command -v uv` is the detector — "does this state already hold" — and `exit 0` before the
`curl | sh` install line is the guard: no install is attempted, no network call is made, no file is
touched. The same shape recurs, differently instrumented, in `bootstrap-lsp.sh` for each of the three
binaries it provisions:

```bash
if command -v pyright-langserver >/dev/null 2>&1; then
  echo "SKIPPED: pyright-langserver already installed"
elif command -v npm >/dev/null 2>&1; then
  ...
```

Here the guard is an `if`/`elif` chain rather than an early `exit`, but the property is identical: the
`SKIPPED` branch is checked first, and only a genuinely absent tool falls through to the installing
branch. `bootstrap-user-scope.sh` guards at a coarser grain — not "does the binary exist" but "does
the target JSON already contain everything required" — computed once and checked before any write is
attempted:

```python
if not wrong_env_keys and not missing_markers and not missing_allow_markers:
    print("SKIPPED: already satisfied (env keys + all deny markers + all allow markers present)")
    sys.exit(0)
```

`[PROVE]` The second-run behaviour this buys: call `bootstrap-uv.sh` twice in a row on a machine that
already has `uv`. The first call and the second call print the identical line —
`SKIPPED: uv already installed (uv 0.x.x)` — and neither call touches the network, writes a file, or
changes `PATH` beyond the in-process `export` that only affects the running script's own subshell.
Compare that to a script with no guard: a second run of a bare `curl -LsSf ... | sh` would re-download
and re-run the installer, which for `uv` is merely wasteful, but for `bootstrap-user-scope.sh`'s JSON
merge, a missing guard would mean re-appending the same deny markers on every run, growing the
`permissions.deny` array without bound.

**The count, corrected.** `[CASE]` `plugins/sdlc-harness/scripts/` holds **fifteen** `bootstrap-*.sh`
files, not fourteen — some editions of this material say fourteen, and that figure is wrong; verified
directly against the directory listing: `bootstrap-functional-tests.sh`, `-glab`,
`-handbook-skills`, `-handbook`, `-link-service`, `-lsp`, `-mmdc`, `-playwright-skills`,
`-plugin-update`, `-pre-commit`, `-services-scaffold`, `-user-scope`, `-uv`, `-workspace`,
`-write-version` — plus three `triage-*.sh` (`triage-aws-ro.sh`, `triage-preflight.sh`,
`triage-report-lint.sh`) that live alongside them. **All eighteen files live under `scripts/`, never
under `hooks/`** — an older wording of this material says `hooks/`, and that is also wrong. `hooks/`
in this repository is reserved for the `PreToolUse`/`PostToolUse`/etc. lifecycle scripts covered in
§2.3; `scripts/` holds standalone, directly-invoked deterministic helpers, and `bootstrap-*.sh` are
the latter — called by name from `bootstrap/SKILL.md`'s numbered steps, never wired to a Claude Code
lifecycle event.

**bootstrap-user-scope.sh: a different risk class.** `[CASE]` Every other script named above writes
inside the repository it provisions, or into a location the harness itself owns
(`$HARNESS_ROOT/services/`, a symlink, a cloned handbook). `bootstrap-user-scope.sh` is the one script
that reaches outside the repository entirely, into the reader's own account-scoped configuration:

```
SETTINGS_PATH="${HARNESS_GUARD_USER_SETTINGS:-$HOME/.claude/settings.json}"
```

That is the **user-scope** settings file from §1.2 — the file that applies to every Claude Code
session the account ever starts, not just sessions rooted at this one repository. §1.2.1–1.2.8
already established that `~/.claude/settings.json` sits above project settings in precedence and
reaches every project; a bug in a script that writes there does not stay contained to one checkout,
it follows the reader everywhere. That is exactly the property the script's own comment invokes as
the *justification* for writing there rather than avoiding the risk: "project-scope permissions do
not apply once a session's CWD leaves `HARNESS_ROOT`, so user scope is the only write that is a
control regardless of where `/run-harness` runs from." A project-scope deny-list would be *narrower*
and therefore safer to get wrong — but it would also silently stop protecting the reader the moment
they `cd` into a service repository, which is precisely when the prod-AWS guard is needed. The script
accepts the wider blast radius because the alternative, a scoped-but-bypassable guard, is not a guard
at all.

**Insight:** the harder a script's write target is to recover from, the more that script's idempotence
has to be *proven*, not assumed — which is why `bootstrap-user-scope.sh` is the one script in the
directory that re-reads its own output and fails closed if the read doesn't match what it just wrote,
rather than trusting the write call to have succeeded:

```
if [ "$VERIFIED" != "true" ]; then
  echo "FAIL-CLOSED: post-write verification ... did not find the required deny markers ..." >&2
  exit 1
fi
```

No other `bootstrap-*.sh` file in the directory re-reads and verifies its own output this way — the
LSP and `uv` installers report `INSTALLED`/`FAILED` from the install command's own exit code, which is
sufficient when the write target is disposable tooling. A wrong write to `~/.claude/settings.json`
is not disposable in the same sense: it is silently trusted by every future session until someone
notices, so this script pays for a second, independent check that the other fourteen do not need.

> **Idempotence** is the property that running a script against a system already in its target state
> performs no work and reports that fact, so that a re-run is always safe regardless of what state
> the system started in.

## 2. The documented exception: `bootstrap-uv.sh`

**Concept.** `[CASE]` Almost every `bootstrap-*.sh` file in the directory shares one boundary, stated
identically in `bootstrap-lsp.sh`'s own header comment: *"Does NOT install npm/Node.js or Homebrew
themselves if missing — same one-level-of-automation boundary as the other `bootstrap-*.sh`
scripts."* The rule is: a script may install the tool it is responsible for, but it may not
self-install a *package manager* — brew, npm — on the reader's behalf. `bootstrap-uv.sh` breaks that
rule on purpose, and both the script and `bootstrap/SKILL.md` say so in the same words, verbatim:

```
# Idempotent installer for uv (astral.sh/uv) -- the one package-manager
# exception to this repo's "never self-install a package manager" boundary
# (see plugins/sdlc-harness/skills/bootstrap/SKILL.md Gotchas). uv is not a
# quality-of-life tool here: scripts/check-prereqs.sh's own gate says it
# plainly -- every stage transition calls `python3 -m harness.state.cli` via
# `uv run`, so without uv NO playbook can get past its first stage.
```

**Why it exists.** `bootstrap/SKILL.md` gives the reasoning `[CASE]` the leaf itself quotes: *"A
bootstrap that leaves the engineer to separately find and run a curl-to-shell command isn't actually
a single-command setup."* Every other tool this bootstrap provisions (`glab`, LSP servers, `mmdc`,
Playwright) degrades gracefully when missing — Claude Code falls back to reading and grepping instead
of using an LSP, for instance, at a token cost but with no hard stop. `uv` is different in kind, not
degree: `scripts/check-prereqs.sh`'s own gate calls `uv run` on every playbook stage transition, so a
machine without `uv` cannot get past the *first* stage of any harness playbook. Treating `uv` the same
as `brew`/`npm` — "report `FAILED` with a manual one-liner" — would leave `bootstrap` reporting itself
complete while the very first `/run-harness` invocation afterward hard-fails on a missing
prerequisite the reader was never actually asked to fix.

**How it works.** The exception is scoped as narrowly as the justification allows: `bootstrap-uv.sh`
self-installs `uv` via the same official installer `scripts/init-harness.sh` already runs (`curl
-LsSf https://astral.sh/uv/install.sh | sh`), and nothing else in the directory gets the same
allowance. `bootstrap-pre-commit.sh`, `bootstrap-glab.sh`, `bootstrap-lsp.sh`,
`bootstrap-playwright-skills.sh`, and `bootstrap-mmdc.sh` all still refuse to self-install `brew` or
`npm` — the `SKILL.md` Gotchas section states this explicitly, by name, as a boundary future edits
must not widen: *"`uv` (step 0) is the one deliberate exception ... do not extend that exception to
`brew`/`npm`."*

**Code.** The idempotence guard on the exception is identical in shape to every non-exceptional
script — `command -v uv` before any install attempt — which is the point: the exception is about
*what the script is allowed to install*, not about relaxing the idempotence discipline for the one
script that gets special install permission. See §1's quoted guard clause above; it is not repeated
differently here.

**Gotcha.** `**Pitfall:**` Reading "one documented exception" as license to add a second one for
convenience. Symptom: a future script adds a `brew install` fallback for its own missing dependency,
reasoning "well, `bootstrap-uv.sh` gets to self-install a package manager, why can't I." Fix: the
justification is not "this script is important," it is the specific, narrow fact that `check-prereqs.sh`
hard-blocks on `uv` for *every* playbook stage, which is not true of `brew` or `npm` for anything else
in this directory — an exception argued from importance alone re-opens the boundary the `SKILL.md`
Gotcha exists to close. **Why people believe it:** "this is important enough to justify breaking the
rule" generalizes easily in a way that "this specific gate blocks everything downstream" does not —
the second is a testable claim about the dependency graph, the first is a feeling about priority.

**Insight:** an exception with its reasoning written down beside it, in the same file a reader would
consult to add a second exception, is the mark of a discipline that is actually enforced rather than
merely stated once and hoped for — the comment does the enforcement work a lint rule can't, because
"don't self-install a package manager" has no machine-checkable form. **What would break without the
written reasoning:** the next engineer to touch `bootstrap-*.sh` would have no way to tell "one
documented, load-bearing exception" apart from "nobody got around to fixing this one either," and the
boundary would erode one plausible-sounding addition at a time.

> **A documented exception** states, at the point it deviates from the rule, exactly which condition
> justifies the deviation — so the exception itself becomes the record that prevents the next
> plausible-sounding deviation from riding in on its coattails.

## 3. Human-authority gates: deny the tool, not the model's willingness

**Concept.** `[CASE]` `/calibrate`'s Jira-filing step is the harness's clearest instance of a human-
authority gate. The `calibrator` agent mines session transcripts for recurring friction and groups
them by `failure_code` — mechanical work, no external side effect — and then stops. Filing the ticket
is a *human's* action, and the mechanism that makes this a guarantee rather than a request is named
explicitly in the agent's own definition:

```
Never calls the Jira API itself — filing requires human confirmation each time.
```

and, more specifically, in its write-boundaries section:

```
**No Jira API tool is ever given to this agent.** Filing a friction bug is a
human-confirmed, team-lead-altitude action (see `plugins/sdlc-harness/commands/calibrate.md`).
You mine and group the pattern; the team lead builds, previews, confirms, and files.
```

**Why it exists.** §1.3.2 and §2.3.1 already established the load-bearing distinction this leaf reuses:
a hook (or, here, a withheld tool) is a guarantee, because the harness enforces it outside the model's
control; a system-prompt instruction telling the model to behave a certain way is a preference the
model can misread, forget under compaction, or override under a sufficiently persuasive later
instruction. `calibrator.md` does not say "please ask before filing" — it says the agent is never
*given* `createJiraIssue` at all. There is no tool in its schema for the model to call, correctly or
incorrectly, that would post to Jira. The gate is enforced the same way a `PreToolUse` deny is
enforced: by the harness deciding what the model's tool palette contains, before the model ever gets
a turn.

**How it works.** The mechanism has a second load-bearing reason beyond "denial beats persuasion":
`AskUserQuestion` — the built-in that would let an agent pause and ask a human directly — is **not
available inside a subagent** (§2.1.14). The calibrator is dispatched as exactly that: a subagent
spawned by `/calibrate`. Even if the design wanted the calibrator itself to pause and ask "should I
file this," the tool that would let it do so does not reach delegated work. A gate built as "the
agent asks the user" cannot live inside a subagent's own turn — it has to live in the orchestrating
skill, running in the parent context, which is exactly where `/calibrate`'s step 3 puts it:

```
2. **Show the preview to the engineer and get explicit confirmation, per ticket.** Do not
   proceed to step 3 on silence or an ambiguous reply — ask directly: "No PII or other
   sensitive leaks in this preview — file as a Jira bug under AP-10772? (y/n)".
```

The shape, stated concretely: the outward-facing action — a Jira `createJiraIssue` call, which posts
to a shared project outside the reader's own machine — is denied to the agent that produces the
candidate content, by never equipping it with the tool. A human, in the parent session, then performs
the irreversible step, or explicitly approves it before the orchestrating skill performs it on the
human's confirmed behalf. `createJiraIssue` is called by `/calibrate`'s own step 4, in the parent
context, using the identical payload the human already reviewed — never rebuilt, so the reviewed
preview and the filed ticket are provably the same object.

**Code.** `[CASE]` The confirmation prompt's own text narrows what a "yes" actually authorizes — worth
quoting because it is easy to over-read the gate as a quality check it is explicitly not:

```
**What the engineer's confirmation is for (2026-07-22 policy):** it is a check for
PII or other sensitive leaks in the built payload — names, hostnames, session/account
IDs — before anything goes to a shared Jira project. It is explicitly **not** a
judgment call on whether the finding is a "real" bug, severe enough, or worth
engineering time.
```

**Gotcha.** `**Pitfall:**` Believing a system-prompt instruction telling an agent "don't file without
asking" would have been an equivalent control. Symptom: the instruction survives most sessions, then
one session compacts the conversation, or a later user turn phrases a request in a way that reads as
"go ahead and file these," and the model complies — no error, no denial, just a Jira ticket that
skipped the PII check. Fix: withhold the tool from the agent's schema entirely, the way `calibrator.md`
does, so there is no `createJiraIssue` call for the model to make correctly or incorrectly — the
"gate" is a fact about what functions exist, not a fact about what the model has been told to do.
**Why people believe it:** an instruction that has worked in the last dozen manual tests looks
identical, from the outside, to a control that cannot fail — until the one session where the model's
sampled response lands somewhere the instruction didn't anticipate.

**Interview:** "How would you make sure an agent never posts to an external system without a human in
the loop?" — the one-line answer is: don't give the agent the tool that posts; put the posting call in
the orchestrating layer, gated on an explicit human confirmation, and never let a subagent hold that
tool at all, since `AskUserQuestion` — the mechanism that would let it ask — isn't reachable from
inside one anyway.

This connects forward to §2.9's threat model: a withheld tool is one instance of bounding an agent's
blast radius, the general property §2.9 covers in full.

> **A human-authority gate** is the outward-facing or irreversible action removed from an agent's own
> tool palette entirely, so a human — in the parent session, with full context — performs it or
> explicitly approves the exact payload before it fires, rather than the model being asked to abstain.

## 4. Prompting for determinism

`[TRAP]` **Pitfall:** treating a system-prompt instruction as a substitute for the guard clauses in
§1, on the theory that "the model understands the rule, so it will apply it consistently." Symptom:
the step works four times in five — the merge looks right, the symlink points where it should, the
version bump lands on the expected number — and then, on the fifth run, or under slightly different
input formatting six weeks later, it produces a subtly different result that nobody can reproduce on
demand, because the failure was never a bug in an algorithm, it was one draw from a probability
distribution landing somewhere the previous four draws hadn't. §2.8's earlier file already worked
through why this happens mechanically: next-token sampling has no reproducibility guarantee even at
`temperature = 0`, and a prompt asking the model to "merge this JSON, preserving existing keys" is
exactly that kind of draw, every time it runs. Fix: the fix is not a better-worded prompt — no
wording closes a sampling-variance gap — the fix is the guard clause itself, computed by a script,
the way §1's quoted `command -v uv` and `wrong_env_keys` checks are. **Why people believe it:** four
consistent runs in a manual test look exactly like a guaranteed algorithm from the outside; only a
fifth run, or a change in the input the first four never exercised, reveals that the first four were
lucky rather than correct — and by then the failure surfaces as "nobody can reproduce it," which is
the actual signature of prompted determinism rather than a red flag that gets noticed early.

## Pitfalls

**Pitfall:** believing "one documented exception" licenses a second exception argued from importance
alone. Symptom: a future `bootstrap-*.sh` self-installs `brew` or `npm` because its own dependency
felt equally load-bearing. Fix: the test is not "how important is this," it is whether every downstream
gate depends on this one tool the way `check-prereqs.sh` depends on `uv` for every playbook stage — a
narrower, checkable claim than a feeling about priority. **Why people believe it:** importance
generalizes faster than the specific dependency-graph fact that actually justifies the exception.

**Pitfall:** telling a subagent to "ask the user before doing X" as a human-authority gate. Symptom:
the instruction is silently unenforceable, because `AskUserQuestion` is not available inside a
subagent (§2.1.14) — there is no tool call the model could even make to comply, so the instruction
either gets ignored or the model proceeds without asking. Fix: withhold the irreversible tool from the
subagent's own schema and put the confirmation step in the orchestrating skill, in the parent context,
the way `/calibrate` step 3 does. **Why people believe it:** "ask before doing X" reads as a complete
instruction in isolation, without checking whether the executing context has the tool that "asking"
would require.

**Pitfall:** prompting a model to "always merge the JSON consistently" instead of writing the guard
clause. Symptom: a step that passes four manual tests in five, and a fifth-run failure with no
reproducible trigger. Fix: replace the prompt with the deterministic guard — `wrong_env_keys`,
`missing_markers` and an early `exit 0`/`sys.exit(0)` — because a script's output space has one
member and a prompt's does not. **Why people believe it:** a handful of consistent manual runs are
indistinguishable, from the outside, from a guaranteed algorithm.

## Cheat sheet

| Case | Property | Mechanism | File |
|---|---|---|---|
| `bootstrap-uv.sh`, `bootstrap-lsp.sh` | Idempotent | `command -v <tool>` guard before install; `SKIPPED`/`INSTALLED`/`FAILED` | `scripts/bootstrap-uv.sh`, `scripts/bootstrap-lsp.sh` |
| `bootstrap-user-scope.sh` | Idempotent + fail-closed verify | `wrong_env_keys`/`missing_markers` guard, then re-read and verify after write | `scripts/bootstrap-user-scope.sh` |
| `bootstrap-uv.sh` | Documented exception | Self-installs `uv` (the one package manager allowed); every other script refuses | `scripts/bootstrap-uv.sh`, `skills/bootstrap/SKILL.md` Gotchas |
| Jira filing | Human-authority gate | `createJiraIssue` never given to the `calibrator` subagent; parent skill confirms then files | `agents/calibrator.md`, `commands/calibrate.md` |
| "the model will apply the rule consistently" | Not a guarantee | No guard clause = a sampled result each run, not a computed one | this file, §2.8 the previous file |

## Self-test

1. What makes a script idempotent, precisely — not "safe to run" but idempotent?
<details><summary>Answer</summary>Running it against a system already in its target state performs no work and reports that fact (`SKIPPED`), and running it against any other starting state moves the system to the same target state — a second, third, or tenth run changes nothing beyond the first successful run.</details>

2. How many `bootstrap-*.sh` files does `plugins/sdlc-harness/scripts/` actually hold, and where do they live?
<details><summary>Answer</summary>Fifteen `bootstrap-*.sh` files, plus three `triage-*.sh` files (eighteen total), all under `plugins/sdlc-harness/scripts/` — never under `hooks/`, which is reserved for lifecycle-event scripts.</details>

3. Why is `bootstrap-uv.sh` allowed to self-install a package manager when every other `bootstrap-*.sh` script is not?
<details><summary>Answer</summary>`scripts/check-prereqs.sh`'s own gate calls `uv run` on every playbook stage transition, so without `uv` no playbook can get past its first stage — a bootstrap that can't provision it isn't a genuine single-command setup. No other missing tool in the directory blocks every stage the way `uv`'s absence does; `brew`/`npm` never get the same exception.</details>

4. Why does `bootstrap-user-scope.sh` write to `~/.claude/settings.json` instead of a project-scope settings file, and why does that make it a different risk class?
<details><summary>Answer</summary>Project-scope permissions stop applying the moment a session's CWD leaves `HARNESS_ROOT`, so user scope is the only write that is a control regardless of where `/run-harness` is invoked from. That also means a bug in this one script follows the reader into every future Claude Code session on that account, not just sessions rooted at this repository — which is why it is the only script in the directory that re-reads and verifies its own write before reporting success.</details>

5. Why is "deny the tool" the correct human-authority mechanism for the calibrator's Jira filing, rather than an instruction telling it to ask first?
<details><summary>Answer</summary>A hook or a withheld tool is a guarantee enforced by the harness outside the model's control; a prompt instruction is a preference the model can misread or override under a later, more persuasive turn. The calibrator is never given the `createJiraIssue` tool at all, so there is no call for the model to make correctly or incorrectly.</details>

6. Why couldn't the calibrator itself pause and ask the user for confirmation, even if it were given the Jira tool?
<details><summary>Answer</summary>`AskUserQuestion` is not available inside a subagent, and the calibrator runs as a subagent dispatched by `/calibrate`. A gate that depends on the agent asking a human cannot live inside delegated work — it has to live in the orchestrating skill, in the parent session, which is exactly where `/calibrate` step 3 places the confirmation.</details>

7. What is the calibrator's Jira confirmation actually checking, and what is it explicitly not checking?
<details><summary>Answer</summary>It checks for PII or other sensitive leaks (names, hostnames, session/account IDs) in the built payload before it goes to a shared Jira project. It is explicitly not a judgment call on whether the finding is a real bug, severe enough, or worth engineering time — that assessment belongs to Jira triage after filing.</details>

8. What is the actual fix for "prompting for determinism," and why doesn't a better-worded prompt work?
<details><summary>Answer</summary>The fix is a guard clause computed by a script — the same `command -v`/`wrong_env_keys`-style check from §1 — not a more careful instruction. No wording closes a sampling-variance gap, because next-token sampling has no reproducibility guarantee even at temperature 0; the model's output remains one draw from a distribution regardless of how the prompt is phrased.</details>

## Open questions

None.

---

**Leaves covered:** 2.8.6–2.8.9 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-65 in the previous file draws the decision tree and D-41 in `skills/06` draws the mechanism selection
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 374
