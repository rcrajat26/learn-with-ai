# 21 AI for Coding — the blocking-guard pattern — INTERMEDIATE (§2.3.26, §2.3.28)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the `SessionStart` reindex incident](07-the-reindex-incident.md) · Next: [MCP: transports and scopes](../mcp-and-lsp/01-basics-transports-and-scopes.md)

The previous file told the story of a `SessionStart` hook that was never allowed to fail loudly and
failed catastrophically anyway, because it did unbounded work with no coordination. This file tells
the opposite story: a hook whose entire job is to say no, built so that saying no is exactly as safe
as it needs to be and no safer. Read the two files as a matched pair — one shows what happens when a
hook has no business blocking anything and stays advisory; this one shows what a hook looks like when
blocking is precisely its job.

## §2.3.26 — the blocking-guard pattern

**Mental model.** Where `check-init.sh` is a hook that is *never allowed* to stop a session,
`prod-guard-bash.sh` is a hook whose entire reason to exist is to stop a tool call. Both ship in the
same plugin, and both are legitimate designs — the axis that decides which posture a hook should take
is not "is this a `SessionStart` hook" or "is this a `PreToolUse` hook," it is **what happens when this
hook itself misbehaves, and what does a missed check cost?**

**Why it exists.** RFC 0002 §6.3 names the actual production gap this pattern defends against — not a
resource pile-up this time, but a live control gap. The prod-AWS deny-list (`permissions.deny` in
`.claude/settings.json`) is the *sole* control protecting production AWS calls in this plugin, and a
plugin cannot ship `permissions.*` keys itself — only a hook or a bootstrap step can write them into a
settings file. Quoted from the RFC, in full:

```
The prod-AWS deny-list is the **sole** control protecting production, and today it is
`permissions.deny` in `.claude/settings.json` with **no hook and no engine backstop** (§6.1). A
plugin cannot ship `permissions.*`, so bootstrap writes it. But making "bootstrap refuses to
*complete* without the deny-list" the only gate is **fail-open**, for three reasons:

1. `/plugin install` registers `/run-harness` (and `/full-sdlc`, …) **immediately**; bootstrap
   runs later and interactively — a workflow (or a raw `aws … prod` call) invoked in the
   install→bootstrap window hits no guard.
2. A workspace-only new user (§8 P5) who never clones the source has **no pre-existing project
   deny-list at all**.
3. `/run-harness` runs from **any CWD** (§5/§6.2). Claude Code loads `permissions` from user scope
   + the CWD's project scope — a deny-list written to `HARNESS_ROOT/.claude/settings.json` is **not
   loaded** when CWD is `~/dev/x-service`. Only a **user-scope** write (`~/.claude/settings.json`)
   survives the any-CWD model.

**Fixes (all required):**
- **Ship a guard hook *inside* the plugin** — SessionStart + a PreToolUse `Bash` matcher — that
  hard-refuses harness-workflow invocation **and** any mutating / `prod` AWS command unless it
  verifies the deny markers are present in the *resolved* settings. "Deny-list verified present"
  becomes a **runtime precondition of `/run-harness`**, not merely a bootstrap exit code. This is
  the true fail-closed control; the deny-list is data the hook enforces.
- **Write the deny-list to user scope** (`~/.claude/settings.json`), because project/workspace
  scope does not apply off-CWD (reason 3).
```

Read the three reasons carefully, because each is a distinct way a settings-only control fails, and
none of them is fixable by writing the settings file more carefully. Reason 1 is a timing gap — the
plugin's commands exist before bootstrap has had a chance to run interactively. Reason 2 is a
population gap — some users never go through the flow that would have written a project-scope
deny-list at all. Reason 3 is a scope gap — `/run-harness` is designed to run from any working
directory, and Claude Code's settings-loading model only guarantees user-scope permissions apply
regardless of CWD; a deny-list sitting only in the harness's own project settings is invisible the
moment the operator's shell is anywhere else. A settings file alone cannot close any of these three
gaps: it is either not written yet, was never written for this user, or is written to the wrong scope
for the CWD the command actually runs from. Only a hook — code that runs at the moment of the tool
call, regardless of which settings file exists or does not — can make "the deny-list is verified
present" a runtime precondition rather than a one-time bootstrap checkbox that can be silently false
by the time it matters.

**How it works — three files, one shared library.** `prod-guard-lib.sh` defines the deny markers and
the verification function once, quoted here in full:

```bash
#!/usr/bin/env bash
# Shared logic for the RFC 0002 §6.3 fail-closed prod-guard hooks
# (prod-guard-session-start.sh + prod-guard-bash.sh). Kept in one file so the
# deny-marker list and the "is this a harness-workflow / prod-AWS command"
# patterns can never drift between the advisory (SessionStart) half and the
# enforcing (PreToolUse:Bash) half — a single source of truth for what
# counts as "guarded".
#
# Why user scope, and why re-check on every Bash call rather than trust a
# session-start snapshot: RFC 0002 §6.3 reason 3 — `/run-harness` runs from
# ANY CWD, and Claude Code only guarantees loading *user*-scope permissions
# regardless of CWD (project scope does not apply once CWD leaves
# HARNESS_ROOT). A deny-list written anywhere but user scope is therefore
# not a control at all off-CWD. This library resolves user scope by a fixed
# path ($HOME, never git-toplevel/CWD) so the check is CWD-independent by
# construction — matching the enforcement model it backstops.
#
# Both hook scripts source this file, so it must not `exit` — only define
# functions/vars — and must tolerate being sourced under `set -u`.

# Override point for tests — a test run must never read or write a real
# developer's ~/.claude/settings.json.
: "${HARNESS_GUARD_USER_SETTINGS:=$HOME/.claude/settings.json}"
PROD_GUARD_USER_SETTINGS="$HARNESS_GUARD_USER_SETTINGS"

# The exact permission-deny strings bootstrap must have written to user
# scope (mirrors this repo's own project-scope .claude/settings.json deny
# list — same categories; see RFC 0002 §6.1 table). ALL must be present —
# partial credit is not fail-closed.
PROD_GUARD_REQUIRED_DENY_MARKERS=(
  "Bash(aws cloudformation delete-stack*)"
  "Bash(aws cloudformation update-stack*)"
  "Bash(aws cloudformation create-stack*)"
  "Bash(aws cloudformation execute-change-set*)"
  "Bash(aws ecs update-service*)"
  "Bash(aws lambda update-function-configuration*)"
  "Bash(aws lambda list-functions*)"
  "Bash(aws iam list-*)"
  "Bash(aws ssm * --name /prod/*)"
  "Bash(aws ssm * --path /prod/*)"
  "Bash(aws * --profile *prod*)"
)

# Exit 0 (true) if every required marker is present in the user-scope
# settings' permissions.deny array AND env.HARNESS_ROOT is set. Exit 1
# (false) otherwise — including when the file is missing/unparseable
# (fail-closed default: no file means not verified, never "trivially ok").
prod_guard_verified() {
  [[ -f "$PROD_GUARD_USER_SETTINGS" ]] || return 1
  python3 - "$PROD_GUARD_USER_SETTINGS" <<'PY'
import json, sys

path = sys.argv[1]
required = [
    "Bash(aws cloudformation delete-stack*)",
    "Bash(aws cloudformation update-stack*)",
    "Bash(aws cloudformation create-stack*)",
    "Bash(aws cloudformation execute-change-set*)",
    "Bash(aws ecs update-service*)",
    "Bash(aws lambda update-function-configuration*)",
    "Bash(aws lambda list-functions*)",
    "Bash(aws iam list-*)",
    "Bash(aws ssm * --name /prod/*)",
    "Bash(aws ssm * --path /prod/*)",
    "Bash(aws * --profile *prod*)",
]
try:
    with open(path) as f:
        data = json.load(f)
except (OSError, ValueError):
    sys.exit(1)

deny = set(((data.get("permissions") or {}).get("deny")) or [])
harness_root = (data.get("env") or {}).get("HARNESS_ROOT")
sys.exit(0 if (all(m in deny for m in required) and harness_root) else 1)
PY
}

# Is this Bash command one of the recognised harness-workflow entrypoints?
# Deliberately an allowlist of known runtime scripts/modules (not "any
# scripts/*.sh") — new harness entrypoints must be added here explicitly,
# same discipline as harness-commit-guard.sh's word-boundary care. These are
# exactly the deterministic scripts /run-harness's preflight/execute steps
# shell out to (harness/control-plane/team-formation.md + run-harness.md), so
# blocking the first one blocks the workflow before it does anything.
prod_guard_is_harness_entrypoint() {
  local cmd="$1"
  printf '%s' "$cmd" | grep -qE \
    'scripts/(check-prereqs|pull-services|next-run-id|agent-name|harness-commit|harness-commit-trailer|lint-rfc|discover-one|probe-stack-resources|build-check)\.(sh|py)|scripts/publish-stage-trace\.py|harness_state\.cli|(^|[[:space:]])(uv run )?python3? +-m +engine([[:space:]]|$)|harness/playbooks/(full-sdlc|plan-project|implement-story)/workflow\.yaml'
}

# Is this Bash command a mutating-or-prod AWS call? Mirrors the category
# reasoning of the project-scope deny list: destructive CFN/ECS/Lambda ops
# (regardless of environment), or anything scoped to a prod SSM path/profile.
prod_guard_is_mutating_or_prod_aws() {
  local cmd="$1"
  printf '%s' "$cmd" | grep -qE \
    'aws +cloudformation +(delete|update|create)-stack|aws +cloudformation +execute-change-set|aws +ecs +update-service|aws +lambda +update-function-configuration|aws +lambda +list-functions|aws +iam +list-|aws +ssm +.*(--name +/prod/|--path +/prod/)|aws +.*--profile +[^ ]*prod'
}
```

Notice what this file does and does not contain. It defines data (`PROD_GUARD_REQUIRED_DENY_MARKERS`),
one verification predicate (`prod_guard_verified`), and two classification predicates
(`prod_guard_is_harness_entrypoint`, `prod_guard_is_mutating_or_prod_aws`) — nothing that acts on any
of them. It never calls `exit`, because both hook scripts source it rather than execute it, and an
`exit` inside a sourced file would terminate whichever caller sourced it. `prod_guard_verified` returns
**1 (false, "not verified") on every failure path**: file missing, file unparseable, any single
required marker absent, or `HARNESS_ROOT` unset. There is no branch that returns success by default —
this is the fail-closed default stated as code, not merely asserted in a comment. The classification
functions are deliberately allowlists rather than broad heuristics ("any `scripts/*.sh`" would have
been far shorter to write): a new harness entrypoint has to be added to the regex explicitly, which
means the guard's coverage is exactly as wide as someone has deliberately made it, never wider by
accident and never narrower by an oversight in a catch-all pattern.

`prod-guard-bash.sh` is the enforcing half, a `PreToolUse` hook matched on `Bash`, quoted in full:

```bash
#!/usr/bin/env bash
# PreToolUse hook (Bash matcher) — RFC 0002 §6.3 fail-closed prod guard.
#
# This is the ENFORCING half (prod-guard-session-start.sh is advisory-only).
# The prod-AWS deny-list is the sole control protecting production, and
# `permissions.deny` alone is fail-open for three reasons (§6.3): the
# install→bootstrap window has no guard at all; a workspace-only new user
# has no pre-existing project deny-list; and `/run-harness` runs from any
# CWD, where project-scope permissions never apply. This hook makes "the
# user-scope deny-list is verified present" a runtime precondition of every
# harness-workflow invocation and every mutating/prod AWS command, not
# merely a bootstrap exit condition.
#
# Deterministic string/regex match, not a full command-injection-proof
# boundary (same caveat as harness-commit-guard.sh) — a determined command
# could still evade this via a subshell or alias. It exists to make the
# common, accidental case (running a harness workflow or a prod AWS command
# before bootstrap, or from an unrelated CWD with no project settings) fail
# loudly instead of silently proceeding unguarded.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./prod-guard-lib.sh
source "$SCRIPT_DIR/prod-guard-lib.sh"

INPUT="$(cat)"

COMMAND="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except (ValueError, TypeError):
    sys.exit(0)
print(data.get('tool_input', {}).get('command', ''), end='')
" 2>/dev/null)"

[ -n "$COMMAND" ] || exit 0

if prod_guard_is_harness_entrypoint "$COMMAND" || prod_guard_is_mutating_or_prod_aws "$COMMAND"; then
  if prod_guard_verified; then
    exit 0
  fi
  python3 -c "
import json
reason = (
    'BLOCKED by the fail-closed prod guard (RFC 0002 section 6.3): the '
    'user-scope prod-AWS deny-list and HARNESS_ROOT are not verified '
    'present, so harness-workflow invocation and mutating/prod AWS '
    'commands are refused until bootstrap completes. Run: '
    '/sdlc-harness:bootstrap'
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }
}))
"
  exit 0
fi

exit 0
```

Its own header comment is honest about the boundary of what a regex-based command match can promise:
"Deterministic string/regex match, not a full command-injection-proof boundary... a determined command
could still evade this via a subshell or alias." This hook is not trying to be a sandbox; it is trying
to make the *common, accidental* case — an engineer running `/run-harness` before bootstrap, or from an
unrelated repository with no project settings, with no intent to evade anything — fail loudly instead
of silently proceeding unguarded. That is a materially different, and more achievable, goal than
"no malicious actor can ever get a prod AWS call past this," and the comment says so rather than
overclaiming.

And `prod-guard-session-start.sh` is the advisory counterpart, deliberately non-blocking, quoted in
full:

```bash
#!/usr/bin/env bash
# SessionStart hook — advisory half of the RFC 0002 §6.3 fail-closed prod
# guard. prod-guard-bash.sh (PreToolUse:Bash) is the actual enforcement;
# this one only surfaces the guard's state at session start so a user isn't
# surprised by a deny mid-workflow — same non-blocking-nudge convention as
# check-init.sh's [HARNESS_INIT_REQUIRED] message.
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./prod-guard-lib.sh
source "$SCRIPT_DIR/prod-guard-lib.sh"

if ! prod_guard_verified; then
  echo "[PROD_GUARD_INACTIVE] Tell the user: 'The fail-closed prod-AWS guard is not active yet (user-scope deny-list / HARNESS_ROOT not verified). Harness workflows and mutating/prod AWS commands will be refused until you run: /sdlc-harness:bootstrap'"
fi

exit 0
```

This third file exists purely so an operator is not blindsided mid-workflow by a deny they had no
warning about — it calls the exact same `prod_guard_verified` function the enforcing half calls, so the
two halves can never disagree about whether the guard is active, but it never itself blocks anything;
it only ever informs.

**Divergence worth naming.** The leaf for this row describes the pattern as "a `PreToolUse` non-zero
exit is the only guard the model cannot talk its way past." Read `prod-guard-bash.sh` line by line and
that is not what it does: every path through the script, including the deny path, ends in `exit 0`.
The block is communicated entirely through the JSON contract this arc built earlier — a
`hookSpecificOutput.permissionDecision: "deny"` object printed to stdout on an exit-0 run — not through
a non-zero process exit code at all. This is the *stronger* mechanism, not a weaker substitute: a bare
non-zero exit only tells the harness "something failed," with no reason string for the user to read; the
JSON path carries a human-readable `permissionDecisionReason` the harness surfaces directly, which is
exactly the string quoted above ("BLOCKED by the fail-closed prod guard (RFC 0002 section 6.3)..."). The
model cannot argue its way past either form of block, but only the JSON form explains itself to the
human who is watching the transcript try to understand why a command was refused.

**The fail-closed versus fail-open choice, worked through.** A verification function like
`prod_guard_verified` has exactly two possible defaults for the case it cannot resolve cleanly — file
missing, file unparseable, a marker absent, `HARNESS_ROOT` unset — and the two defaults produce
opposite systems.

A **fail-open** design would treat "I could not confirm the deny-list is present" as "assume it's
fine, let the command through." This is attractive precisely because it is the path of least
resistance for every ordinary session: a corrupted settings file, a `python3` that briefly fails to
parse JSON for some transient reason, a race during a settings write — none of these would ever block
a legitimate workflow. But trace what that means for the exact three gaps RFC 0002 §6.3 names: the
install→bootstrap window (no settings file exists yet at all), the workspace-only new user (no
project-scope deny-list was ever written), and the off-CWD invocation (the file that does exist is not
even the one being checked). In every one of those three cases, "cannot confirm" is not a rare edge
case — it is the *default* state for exactly the population and exactly the window the guard exists to
protect. A fail-open guard would be verified-present on every machine where verification is easy and
silently absent on every machine where verification is hard, which is the precise inversion of what a
guard protecting production access needs to do.

A **fail-closed** design, the one `prod_guard_verified` actually implements, treats every one of those
same unresolved states as "not verified, refuse." The cost is symmetric and visible: a legitimate
session on a machine where the settings file happens to be temporarily unreadable gets refused too,
with no way to distinguish "attacker" from "unlucky read." But that cost is a single, loud, immediately
actionable failure — the `permissionDecisionReason` names the fix (`/sdlc-harness:bootstrap`) in the
same message that delivers the refusal — versus the fail-open cost, which is a production mutation that
proceeds with no operator ever knowing the guard silently was not active. Between "occasionally refuse
a legitimate command with a clear fix" and "occasionally allow a production mutation with no warning
at all," the RFC's own reasoning is that the first cost is the only one worth paying, and the code
matches that reasoning exactly: there is no branch in `prod_guard_verified` that resolves an unclear
state to success.

**Design properties, named.**

| Property | What it buys | What breaks without it |
|---|---|---|
| Shared `prod-guard-lib.sh` | one definition of the deny markers and the matcher regexes, sourced by both entry points | the `SessionStart` advisory and the `PreToolUse` enforcement could silently diverge on what counts as "guarded" — an update to one regex without the other |
| Fail-closed default in `prod_guard_verified` | missing file, unparseable file, and any single missing marker all resolve to "not verified" | a fail-open default would treat "cannot read the settings file" as "assume it's fine," defeating the guard on the exact machines (freshly installed, corrupted config) it exists to protect |
| User-scope resolution (`$HOME`, never `$(git rev-parse --show-toplevel)` or CWD) | the check is correct regardless of which directory `/run-harness` is launched from | a project-scope check would pass or fail based on CWD, reopening RFC 0002 §6.3 reason 3 verbatim |
| Allowlist classification, not a catch-all pattern | the guard's coverage is exactly as wide as someone deliberately made it | a broad heuristic ("any AWS call") either over-blocks harmless read-only calls or under-blocks a new mutating call nobody thought to exclude |
| JSON `permissionDecision` over a bare non-zero exit | a reason string reaches the user, not just a failure signal | the operator sees a hook "fail" with no explanation instead of the actionable "run `/sdlc-harness:bootstrap`" |

**The contrast with `check-init.sh`.** Two `SessionStart`-registered scripts in the same repository
choose opposite failure postures, and both are correct:

- `check-init.sh` is advisory only. It can never know something the model or the user needs to hear as
  a hard stop, so its whole contract is `set +e` at the top and `exit 0` at the bottom — its own
  failure must never be the reason a session cannot start.
- `prod-guard-session-start.sh` and `prod-guard-bash.sh` together are enforcing. Their whole job is to
  be the hard stop between a model that can be talked into anything and a production AWS mutation. The
  enforcing half still technically `exit 0`s on every path, but it achieves blocking through the JSON
  deny contract, and its *default when it cannot verify anything* is refusal, not silence.

The distinguishing question is not "does this hook ever fail," it is **"what should happen when this
hook cannot tell what state the world is in?"** `check-init.sh` answers "say nothing and let the
session proceed" because a missed advisory nudge costs nothing but a slightly less informed session.
`prod-guard-bash.sh` answers "refuse the action" because a missed guard costs a live production
mutation with no control in front of it. Neither posture is a paranoid overreaction or a lazy shortcut
once the cost of being wrong on each side is named — that cost is the entire design argument, and it is
the same argument this file's fail-closed-versus-fail-open section worked through in more detail above.

> A blocking guard earns the right to block by putting its verification logic in one shared library
> every entry point sources, defaulting to refusal on anything it cannot confirm, and communicating the
> block through a structured, human-readable decision object rather than a bare failing exit code — the
> opposite of an advisory hook's contract, and both are correct for what each one owes the session.

**Interview:** "Two `SessionStart`-adjacent hooks in the same plugin, one always exits 0 and prints
advice, the other can deny a tool call — is one of them wrong?" — no; the advisory one (`check-init.
sh`) can never know something worth stopping a session over, so its contract is "never break the
session," while the enforcing pair guards production AWS access, where the cost of a missed check is a
live mutation with no other control in front of it, so its contract is "refuse when unverified." The
posture follows the cost of being wrong, not a single house style.

## §2.3.28 — three ways a hook lies to itself

**Symptom 1 — the hook reads state the model can change.** A `PreToolUse` guard that checks a
workspace file the agent itself has `Write` access to (a JSON "safety flag" committed inside the repo,
say) can be defeated the moment the model edits that file before making the call it wants to make — the
guard is reading a fact the very actor it is supposed to constrain can rewrite. This is a subtler
version of the fail-open problem worked through above: the check itself is sound, but the *input* to
the check is not trustworthy.
**Fix:** ground the check in something outside the model's write surface. `prod_guard_verified` reads
`~/.claude/settings.json`, a path the model can technically still write to via `Bash`, but verification
here checks for `permissions.deny` entries that would themselves have to be present to permit that
write in the first place — the check and the thing it protects are the same layer, not a side file the
model can quietly edit around it. A guard that instead read, say, a bespoke `.guard-state.json` the
model has ordinary write access to would be checking a fact the model itself controls.

**Symptom 2 — the hook assumes a single session.** This is §2.3.25's incident in miniature, and worth
re-reading against it directly: a staleness gate, a counter, or a "have I already done this" flag
stored anywhere without a lock behaves correctly under one session and incorrectly under concurrency,
and the failure only appears once two sessions overlap — which may never happen in the author's own
testing, exactly as it apparently never happened during the reindex hook's original development.
**Fix:** either make the operation idempotent and cheap enough that redundant concurrent execution is
harmless (the option this arc's §2.3.27 formatter and destructive-command guard both take — running
`google-java-format` twice on the same file, or evaluating the deny regex twice, costs nothing extra
and produces no wrong state), or remove the automatic trigger entirely and require a manual,
single-operator invocation, which is the fix AP-12461 actually shipped.

**Symptom 3 — the hook writes to a shared path without a lock.** Any hook that writes a file at a
fixed, repo-wide or machine-wide path — a cache, an index, a log used as a semaphore — and is invoked
by more than one concurrent process races itself: two writers can interleave, one writer's output can
be partially overwritten by another's, and the "abandoned partial index" language in the AP-12461
comment describes exactly this failure at the filesystem level, not merely at the process-count level.
**Fix:** write to a per-session or per-PID temporary path and rename into place atomically only on
success (the pattern the removed reindex never had a chance to use, since it was deleted before anyone
needed to answer "and now make it safe under concurrency"), or, again, do not run the operation
automatically at all when no locking primitive is available to the hook's execution environment.

All three symptoms share one root cause worth stating plainly: each is a way a hook can be *technically
correct in isolation* — the logic is right for one session, one honest input, one writer — while being
silently wrong the moment its assumption (single actor, trustworthy input, exclusive access) stops
holding. A hook review that only asks "is this logic correct" and never asks "what happens if two of
these run at once, or if the thing it reads was just written by the actor it's supposed to constrain"
will pass every one of these three symptoms without noticing anything wrong.

## Pitfalls

**Belief:** "A hook that blocks a tool call must exit non-zero — that's how blocking works."
**In action:** an engineer reading `prod-guard-bash.sh` for the first time expects to find a non-zero
`exit` on the deny path, does not find one, and concludes the hook has a bug or is not actually
enforcing anything.
**Fix:** the block is carried entirely in the JSON `hookSpecificOutput.permissionDecision: "deny"`
object printed to stdout while the process itself still exits 0 — the harness reads that structured
decision, not the process exit code, to decide whether the tool call proceeds.
**Why people believe it:** every other Unix tool signals failure through its exit code, so a hook that
"fails" by exiting 0 anyway looks backwards until the JSON contract this arc built earlier is recalled.

**Belief:** "A fail-closed guard and a fail-open one are just a coin flip on which is more convenient
for the common case."
**In action:** an engineer implementing a similar guard defaults an unresolved verification state to
"allow," reasoning that the common case (a healthy machine with the settings file present) should not
be penalised by a rare parsing edge case.
**Fix:** name the population that actually hits the unresolved state before choosing a default —
`prod_guard_verified`'s unresolved cases are not rare edge cases on a healthy machine, they are the
*default* state for exactly the install→bootstrap window, the workspace-only new user, and the
off-CWD invocation the guard exists to protect; fail-open there means the guard is absent precisely
where it is needed.
**Why people believe it:** an unresolved verification state feels statistically rare in the abstract,
because most of the time a settings file is present and parses cleanly — the reasoning only breaks once
you ask which specific population is disproportionately likely to hit the unresolved branch, which is
exactly the question RFC 0002 §6.3 answers with its three named reasons.

## Cheat sheet

| Fact | Value |
|---|---|
| Files | `prod-guard-lib.sh` (shared checks), `prod-guard-bash.sh` (`PreToolUse:Bash`, enforcing), `prod-guard-session-start.sh` (`SessionStart`, advisory) |
| What it protects | production AWS mutations + harness-workflow invocation, per RFC 0002 §6.3 |
| Why settings alone are fail-open | install→bootstrap window has no guard; workspace-only users have no project deny-list; `/run-harness` runs from any CWD, where project scope doesn't apply |
| How the guard actually blocks | `hookSpecificOutput.permissionDecision: "deny"` JSON on an `exit 0` process — **not** a non-zero exit |
| Fail-closed default | `prod_guard_verified` returns false on missing file, unparseable file, any missing marker, or unset `HARNESS_ROOT` |
| Classification style | allowlist regexes (`prod_guard_is_harness_entrypoint`, `prod_guard_is_mutating_or_prod_aws`), not a broad catch-all |
| `check-init.sh` vs `prod-guard-bash.sh` | advisory (`set +e`/`exit 0`, never blocks) vs enforcing (fail-closed deny by default) — both correct for what each protects |
| §2.3.28 symptom 1 | hook reads state the model itself can write — ground the check outside the model's write surface |
| §2.3.28 symptom 2 | hook assumes a single session — make the op idempotent, or remove the automatic trigger |
| §2.3.28 symptom 3 | hook writes a shared path with no lock — write to a temp path, rename atomically, or don't automate it |

## Self-test

1. `prod-guard-bash.sh`'s deny path ends in `exit 0`. Does that mean it fails to block the tool call?
<details><summary>Answer</summary>No — it blocks through the JSON `hookSpecificOutput.
permissionDecision: "deny"` object printed to stdout, which the harness reads as the decision. The
process's own exit code is not the blocking mechanism here.</details>

2. Name the fail-closed default in `prod_guard_verified` and state what fail-open would have looked
   like instead.
<details><summary>Answer</summary>Fail-closed: a missing settings file, an unparseable one, any single
missing deny marker, or an unset `HARNESS_ROOT` all resolve to "not verified" (refuse). A fail-open
version would treat "I cannot read the file" as "assume it's fine," which defeats the guard on exactly
the freshly-installed or corrupted-config machines it exists to protect.</details>

3. Name RFC 0002 §6.3's three reasons a settings-only deny-list is fail-open, and explain why none of
   them is fixable by writing the settings file more carefully.
<details><summary>Answer</summary>The install→bootstrap window (commands register before bootstrap can
run), a workspace-only new user with no pre-existing project deny-list, and any-CWD invocation where
project scope does not apply off-CWD. None is fixable by writing the file more carefully because each
describes a case where the relevant file either does not exist yet, was never written for this user,
or is not the file being consulted for the current CWD — the problem is timing, population, or scope,
not care.</details>

4. `check-init.sh` and `prod-guard-bash.sh` are both `SessionStart`-adjacent hooks in the same plugin
   with opposite failure postures. Is one of them wrong?
<details><summary>Answer</summary>No. `check-init.sh` can never know something worth stopping a
session over, so its contract is "never break the session" (`set +e`/`exit 0`). `prod-guard-bash.sh`
guards production AWS access where a missed check costs a live mutation with no other control in front
of it, so its contract is "refuse when unverified." The right posture is set by the cost of being
wrong, not by a single house style.</details>

5. Why does `prod-guard-lib.sh` exist as a separate sourced file rather than being duplicated inside
   `prod-guard-bash.sh` and `prod-guard-session-start.sh`?
<details><summary>Answer</summary>So the deny-marker list and the classification regexes cannot drift
between the enforcing (`PreToolUse`) half and the advisory (`SessionStart`) half — both source the
identical definitions, so an update to one regex necessarily updates what both hooks consider
"guarded."</details>

6. What three symptoms mark a hook that will misbehave the same way the removed reindex hook did, even
   before it fails?
<details><summary>Answer</summary>It reads state the model itself can change; it assumes only one
session is ever running; and/or it writes to a shared path with no lock, so concurrent writers can
interleave or overwrite each other's output.</details>

7. Why is `prod-guard-bash.sh`'s classification of "which commands to guard" written as an allowlist
   regex rather than a broader heuristic like "any `aws` invocation"?
<details><summary>Answer</summary>An allowlist makes the guard's coverage exactly as wide as someone
deliberately made it — a broad heuristic would either over-block harmless read-only AWS calls or
under-block a new mutating call nobody thought to add, and either failure mode would be invisible until
someone hit it.</details>

## Open questions

None.

---

**Leaves covered:** 2.3.26, 2.3.28 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none — this file's leaves carry no diagram in the manifest
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 519
