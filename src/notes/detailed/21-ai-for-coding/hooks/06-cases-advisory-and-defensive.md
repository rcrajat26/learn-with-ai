# 21 AI for Coding — advisory hooks, read closely — INTERMEDIATE (§2.3.21–2.3.24)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the six configuration sources](05-configuration-sources.md) · Next: [the `SessionStart` reindex incident](07-the-reindex-incident.md)

Every hook mechanic from the last five files — the handler forms, matcher semantics, the event
catalogue, payloads and exit codes, the JSON contract, narrow-not-widen, the six configuration
sources — now gets tested against a script that has been running in a real repository under real
load. This file reads that script line by line. Nothing here is invented; every fenced block below
was read from the file at the path given, in full, before being quoted.

## §2.3.21 — the real `hooks.json`

The file lives at `plugins/sdlc-harness/hooks/hooks.json` inside the sdlc-harness repository. It is
33 lines, not the 30 the syllabus estimated — a small drift worth naming out loud rather than quietly
rounding away, since the reader will count for themselves. The claim about its shape holds exactly:
three `SessionStart` handlers plus one `PostToolUse` with `matcher: "Write|Edit"`. Quoted whole:

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

### Why three `SessionStart` handlers rather than one script

**Mental model.** Read the top-level `"SessionStart"` key as a list of matcher blocks (here, one,
because `SessionStart` has nothing to match against — every session start fires it), and read that
block's `"hooks"` array as three independent programs the harness runs in sequence for the one event.
Nothing forces them into one file.

**Why it exists.** `check-init.sh`, `prod-guard-session-start.sh` and `calibration-nudge.sh` answer
three unrelated questions: is this workspace bootstrapped and up to date, is a production credential
about to be exposed to an agentic session, and is a calibration cycle due. A single combined script
would need its own internal dispatch, its own combined failure posture, and a merge commit every time
one concern changed independent of the other two. Three files means three owners, three test files,
three independent `set +e` / `exit 0` postures, and a diff on one that never touches the other two's
logic.

**How it works.** `${CLAUDE_PLUGIN_ROOT}` is the plugin's own installed root — not the repository
root, and not the user's working directory — resolved once when the plugin loads, exactly as the
prior file in this set established for the `${CLAUDE_PLUGIN_ROOT}` version trap. The harness invokes
each `command` string through `bash`, in array order, and — per the exit-code table built in
`03-payloads-and-exit-codes.md` — `SessionStart` is one of the four events (alongside
`UserPromptSubmit`, `UserPromptExpansion`, `PostModelSwitch`) where an exit-`0` script's plain-text
stdout is not merely logged but **added to the model's context**. All three scripts in this array
lean on that fact; none of the three writes to a file, calls an API to notify anyone, or returns
structured JSON. They print English sentences on `exit 0` and trust the harness to hand those
sentences to the model.

**Code.** The array above, plus `check-init.sh` below.

**Gotcha.** Order in the array is execution order but not an isolation boundary — a `set -e` in one
handler that is meant to run all three at the plugin level would abort the remaining two on the first
non-zero exit, which is exactly why each of these three scripts declares `set +e` internally rather
than relying on the outer invocation to protect it. Order also matters for the reader of the
transcript, not for correctness: `check-init.sh`'s bootstrap message should land before a calibration
nudge that presumes the workspace already exists, and putting it first is a deliberate ordering
choice, not an accident of alphabetisation.

> Three `SessionStart` handlers on one `hooks.json` array are three independently ownable programs
> the harness happens to run back to back, not one combined script split for style.

### What the `PostToolUse` matcher buys

**Mental model.** `"matcher": "Write|Edit"` is a regular expression tested against the tool name in
the `PostToolUse` payload, the same matcher mechanism `04-a-hook-cannot-unblock-a-deny.md` walked for
`PreToolUse` — it is not special-cased per event.

**Why it exists.** `doc-update-reminder.sh`'s whole job is to notice when source changed and nudge
about documentation; a `Read`, a `Bash`, or a `Glob` call never changes a file's contents, so running
the reminder logic after those tools would be pure wasted invocation cost with zero chance of firing
anything useful.

**How it works.** Without a `matcher` key, an event array applies to every tool call for that event —
this is the same "narrow but never widen" register from the prior file: a matcher can only shrink the
set of tool calls a handler sees, never grant it visibility it would not otherwise have. `Write|Edit`
is an alternation, matched against the literal tool name, so it fires on exactly two tools and no
others — not `NotebookEdit`, which is a distinct tool name despite editing a file in spirit.

**Gotcha.** `NotebookEdit` falling outside `Write|Edit` is easy to miss reading the matcher casually —
a repository that edits notebooks and expects the same doc-update nudge on them gets silence instead,
because the string literally does not match. The fix is adding the third alternative, not assuming
the harness generalises "edits a file" for you.

> A `PostToolUse` matcher is a regular expression over the tool name that only narrows which
> invocations of that event a handler is run for.

## §2.3.22–2.3.24 — `check-init.sh`: a masterclass in advisory hooks

The file lives at `plugins/sdlc-harness/hooks/check-init.sh`. Read whole before any line below was
quoted. It runs on every `SessionStart` and checks seven independent things — workspace root
resolution, which handbook MCP server is registered, whether the bootstrap steps have drifted,
whether a harness update tag exists, whether a cross-marketplace plugin dependency is unresolved,
whether required CLI tools are present, whether LSP servers are installed — printing at most one
tagged line per finding and never touching the tool call the session is about to make.

### Property 1 — tagged advisory instructions

**Mental model.** Read every `echo` in this script as a message stapled with a return address. The
tag in square brackets — `[HANDBOOK_ACTIVE]`, `[HARNESS_BOOTSTRAP_REQUIRED]`, and the rest — is not
decoration for a human reading a log; it is how the model, receiving this text mixed into its own
context alongside the user's actual words, tells "the workspace itself is telling me a fact" apart
from "the user is telling me to do something."

**Why it exists.** This is the property the previous paragraph on §2.3.21 leaned on:
`SessionStart` is one of the small set of events (`UserPromptSubmit`, `UserPromptExpansion`,
`SessionStart`, `PostModelSwitch`) where exit-`0` stdout is shown to the model rather than only
written to the debug log. Without that routing, none of these seven checks could ever reach the
model — they would be visible only to a human tailing a log file no one tails. The tag is what makes
the mechanism safe to lean on: an untagged sentence dropped into context reads exactly like a user
instruction and the model has no way to discount it appropriately; a tagged one reads as "ground
truth reported by the harness," which is the entire design intent the leaf names — **context
injection driven by ground truth on the machine, not by model belief.**

**How it works.** Each finding is independently gated and independently tagged. The handbook block:

```bash
case "$HANDBOOK_STATE" in
  IGM)
    echo "[HANDBOOK_ACTIVE] ig-markets is the active handbook platform. To switch, run /sdlc-harness:handbook."
    ;;
  IGT)
    echo "[HANDBOOK_ACTIVE] ig-trading is the active handbook platform. To switch, run /sdlc-harness:handbook."
    ;;
  BOTH)
    echo "[HANDBOOK_SELECT] both -- igmarkets-handbook and igtrading-handbook are both registered as MCP servers (exclusivity violated: at most one may be active). Tell the user: run /sdlc-harness:handbook to pick igm/igt/none."
    ;;
  *)
    echo "[HANDBOOK_SELECT] none -- no handbook platform is currently registered. Tell the user: run /sdlc-harness:handbook to pick igm/igt/none."
    ;;
esac
```

`$HANDBOOK_STATE` is computed a few lines earlier by reading `~/.claude.json` (or
`$CLAUDE_CONFIG_DIR/.claude.json` when that variable is set) with a small inline `python3 -c` and
checking which of `igmarkets-handbook` / `igtrading-handbook` keys exist under `mcpServers`. Every one
of the four branches emits exactly one tag: `[HANDBOOK_ACTIVE]` when exactly one platform is
registered, `[HANDBOOK_SELECT]` when the state is ambiguous (both, or neither) and a human decision
is needed. Six more tags appear elsewhere in the same script for six unrelated findings:
`[HARNESS_BOOTSTRAP_REQUIRED]` (workspace root unresolved, or bootstrap steps changed since last
run), `[HARNESS_UPDATE_AVAILABLE]` (a newer git tag exists on `origin`),
`[PLUGIN_DEPENDENCY_UNRESOLVED]` (`claude plugin list --json` reports an error for this plugin),
`[CLI_TOOLS_MISSING]` (`glab` or `aws` absent or unauthenticated), `[LSP_SERVERS_SUGGESTED]`
(language servers absent — non-blocking). Every one follows the identical shape: compute a fact about
the actual machine and workspace, then, only if the fact is unfavourable, print one line naming the
tag and telling the model what to tell the user.

Two design choices are worth reading closely inside that same block. First, the comment above it
explains why it does **not** read `enabledMcpjsonServers`:

```bash
# This deliberately does NOT read `enabledMcpjsonServers`: that key only gates
# servers declared in a `.mcp.json` (which this repo forbids committing), so it
# has no bearing on the user-scope registrations the handbooks actually use. An
# earlier version of this block read it and could report ig-trading active in a
# session where only igmarkets tools existed.
```

That is the "ground truth, not belief" property made concrete by its own regression history: an
earlier version of this exact hook checked the wrong config key and told the model something false
about the workspace. Second, the script reads the config file directly with `python3 -c` rather than
shelling out to `claude mcp list`, because — per the comment a few lines above the CLI-tools check —
that command's output "merges scopes and decorates entries with connection status," which is a worse
source of ground truth for a yes/no exclusivity check than the raw JSON.

**Interview:** "How does a hook communicate a non-blocking fact to the model, and how does the model
avoid treating it as a user instruction?" — it writes plain text to stdout on an event whose exit-`0`
stdout is shown to the model (`SessionStart` here), and prefixes it with a bracketed tag so the text
is recognisably a harness-reported fact rather than conversational input.

> A tagged advisory line is stdout from a `SessionStart` hook, routed into the model's context by
> the harness because the exit code was `0`, carrying a bracket tag so the model can tell "the
> workspace is reporting a fact" from "the user just said something."

### Property 2 — the defensive shape

**Mental model.** Read the whole file as guarded on both ends: nothing inside it is allowed to stop
the session from starting, no matter what goes wrong.

**Why it exists.** This hook runs before every single session. If a `SessionStart` hook can abort a
session, every engineer on this repository loses their ability to open Claude Code the day a git
remote is unreachable, a Python interpreter is missing, or a CLI tool changes its output format. An
advisory hook — one that only ever informs — earns the right to run unconditionally exactly because
it is written so that its own failure cannot propagate.

**How it works — the guards, quoted, one per property named in the leaf.**

The failure posture bracketing the whole script:

```bash
#!/usr/bin/env bash
set +e
```

and, as the very last line of the file:

```bash
exit 0
```

`set +e` (bash's default, stated explicitly here rather than left implicit) means a failing command
inside the script — a `python3` call against a malformed JSON file, a `git` command against a
detached-HEAD workspace, a missing binary — does **not** abort the script the way `set -e` would.
The explicit `exit 0` at the end is the second half of the same guarantee: whatever happened in
between, the script's own exit code reported to the harness is always success, so the harness never
treats "an advisory check failed to run cleanly" as "this `SessionStart` hook failed." Without `set
+e`, one broken check (say, `python3` failing on a corrupt `.claude.json`) would kill every check
after it in the same script, including ones with no connection to the failure. Without the trailing
`exit 0`, a script that reaches the end having produced no output but tripped some non-zero exit
status along the way could still report failure upward — on `SessionStart`, a non-zero exit is shown
to the user as an error rather than silently absorbed, so an advisory-only hook reporting itself as
failed would train engineers to associate this specific safety mechanism with breakage it never
actually causes.

The network call is bounded on two independent axes so a slow or hung `origin` cannot hang the
session:

```bash
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout 5"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout 5"
else
  TIMEOUT_CMD=""
fi

CURRENT_TAG=$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")
LATEST_TAG=$(GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=5 \
  $TIMEOUT_CMD git -C "$REPO_ROOT" ls-remote --tags --sort=-version:refname origin 'v*' 2>/dev/null \
  | head -1 | sed 's/.*refs\/tags\///' | sed 's/\^{}//')
```

`timeout 5` (or macOS's `gtimeout`, since GNU `timeout` is not on macOS by default) is a wall-clock
kill switch on the whole `git ls-remote` process. `GIT_HTTP_LOW_SPEED_LIMIT=1000` /
`GIT_HTTP_LOW_SPEED_TIME=5` are git's own transfer-level cutoff — abort if throughput drops below
1000 bytes/second for 5 seconds — which catches a connection that is technically still open and
trickling bytes, a case wall-clock `timeout` alone would eventually also catch but only after the
full 5-second ceiling regardless of whether data is flowing. Without either guard, a session start on
a machine with a flaky VPN or an unreachable `origin` blocks indefinitely on this one advisory check
before the engineer can type a single prompt — the exact failure mode an advisory hook exists to
never cause.

The hash command falls back across platforms:

```bash
if command -v sha256sum >/dev/null 2>&1; then
  BOOTSTRAP_HASH_CMD="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  BOOTSTRAP_HASH_CMD="shasum -a 256"
else
  BOOTSTRAP_HASH_CMD=""
fi
```

`sha256sum` is the GNU coreutils name (Linux, and Homebrew's `coreutils` on macOS); `shasum -a 256` is
what ships with macOS's BSD userland by default. Without the fallback, this whole bootstrap-drift
check silently does nothing on a stock macOS machine with no `coreutils` installed — note that the
script chooses to degrade to "skip this check" rather than to fail, consistent with the advisory
contract, but it means an engineer on an unmodified Mac gets zero bootstrap-drift nudges until the
`if [[ -n "$BOOTSTRAP_HASH_CMD" ]]` guard around the hashing block is satisfied by installing one of
the two tools.

And the locale pin on the one line that expands a glob into the hash input:

```bash
CURRENT_BOOTSTRAP_HASH=$(LC_ALL=C cat "$BOOTSTRAP_SKILL_FILE" "$CLAUDE_PLUGIN_ROOT"/scripts/bootstrap-*.sh 2>/dev/null \
  | $BOOTSTRAP_HASH_CMD | awk '{print $1}')
```

Bash's glob expansion for `bootstrap-*.sh` is byte-order-lexical, but which byte order counts as
"lexical" is a property of the active locale's collation rules — a locale that collates `-` or digits
differently from the C locale could hand `cat` the same fourteen files in a different order on a
different machine, producing a different concatenation and therefore a different hash of files whose
contents did not change at all. `LC_ALL=C` pins the C locale's byte-wise ordering so the same file set
always concatenates in the same order everywhere, which matters doubly here because — per §2.3.24
below — the counterpart script computing the comparison hash must reproduce this exact order.

**Interview:** "Why does a `SessionStart` hook need `set +e` when most scripts want `set -e`?" — an
advisory hook that only informs must never be the reason a session fails to start; `set +e` plus a
trailing `exit 0` guarantees the script's own exit status is always success regardless of what broke
internally, while the individual `if` guards around each check keep one check's failure from silently
suppressing the others.

> The defensive shape of an advisory `SessionStart` hook is `set +e` at the top, `exit 0` at the
> bottom, a wall-clock and transfer-rate timeout on every network call, a tool-availability fallback
> before every external binary is invoked, and a fixed locale on every step whose output depends on
> ordering — each guard removes one specific way this hook could otherwise take the whole session
> down with it.

### Property 3 — a content hash instead of a version constant

**Mental model.** Instead of a maintained integer like `BOOTSTRAP_VERSION = 7` that a human must
remember to bump, the script fingerprints the actual bytes of the files that define what bootstrap
does, and compares that fingerprint to one recorded the last time bootstrap ran successfully.

**Why it exists.** A version constant needs a human to notice a bootstrap step changed and bump the
number in the same commit — miss that step and every workspace silently believes it is current when
it is not. A hash of the defining files needs no such discipline: any byte changed in any of those
files changes the hash, with no separate bookkeeping action required.

**How it works, quoted:**

```bash
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  BOOTSTRAP_SKILL_FILE="$CLAUDE_PLUGIN_ROOT/skills/bootstrap/SKILL.md"
  if [[ -f "$BOOTSTRAP_SKILL_FILE" ]]; then
    if command -v sha256sum >/dev/null 2>&1; then
      BOOTSTRAP_HASH_CMD="sha256sum"
    elif command -v shasum >/dev/null 2>&1; then
      BOOTSTRAP_HASH_CMD="shasum -a 256"
    else
      BOOTSTRAP_HASH_CMD=""
    fi
    if [[ -n "$BOOTSTRAP_HASH_CMD" ]]; then
      CURRENT_BOOTSTRAP_HASH=$(LC_ALL=C cat "$BOOTSTRAP_SKILL_FILE" "$CLAUDE_PLUGIN_ROOT"/scripts/bootstrap-*.sh 2>/dev/null \
        | $BOOTSTRAP_HASH_CMD | awk '{print $1}')
      BOOTSTRAP_MARKER="$REPO_ROOT/.claude/.bootstrap-version"
      STORED_BOOTSTRAP_HASH=""
      [[ -f "$BOOTSTRAP_MARKER" ]] && STORED_BOOTSTRAP_HASH=$(tr -d '[:space:]' < "$BOOTSTRAP_MARKER" 2>/dev/null)
      if [[ -n "$CURRENT_BOOTSTRAP_HASH" && "$STORED_BOOTSTRAP_HASH" != "$CURRENT_BOOTSTRAP_HASH" ]]; then
        echo "[HARNESS_BOOTSTRAP_REQUIRED] Tell the user: 'Bootstrap steps changed since you last ran it (or it has never completed in this workspace). Re-run: /sdlc-harness:bootstrap'"
      fi
    fi
  fi
fi
```

The hash covers exactly two kinds of file — `skills/bootstrap/SKILL.md` (the orchestrator script
`04-a-hook-cannot-unblock-a-deny.md`'s sibling file `2.8.2` calls "orchestrator-not-rewrite," covered
in full in `06-cases-advisory-and-defensive.md`'s sibling in PART 1) and every
`scripts/bootstrap-*.sh` under the current plugin root. It concatenates all of them (in the
`LC_ALL=C`-pinned order established above) into one hash. `$REPO_ROOT/.claude/.bootstrap-version` is
the stored marker, written the last time `/sdlc-harness:bootstrap` completed; a missing marker (never
bootstrapped, or bootstrapped before this hashing scheme existed) and a present-but-mismatched marker
are treated identically — both mean "cannot confirm this workspace is current" and both produce the
same nudge, because distinguishing them would not change what the engineer should do next.

**Why a hash beats a timestamp or a flag file here.** A timestamp answers "when did bootstrap last
run," not "is what it ran still what bootstrap does today" — a timestamp from Tuesday says nothing
about a bootstrap step edited on Wednesday. A boolean flag file (`.bootstrapped`) answers "did
bootstrap ever run," which has the identical blind spot: it stays true forever even after every
bootstrap step's logic changes underneath it. A content hash is the only one of the three that
actually answers the question the nudge needs answered — "does the recorded state still match what
bootstrap would do if run right now" — because it is computed from the same bytes that define the
behaviour, not from a side channel that must be kept in sync with those bytes by a separate human
action.

**Gotcha.** The comment directly above this block states the coupling this design creates:

```bash
# both must hash the identical file set with the
# identical tool/order or every run nudges spuriously.
```

The counterpart writer, `scripts/bootstrap-write-version.sh` — run as `/sdlc-harness:bootstrap`'s
final report step — has to hash the exact same file list, in the exact same order, with the exact
same tool, or the two sides disagree about a workspace that is genuinely current, and the nudge fires
every single session start regardless of whether anything actually changed. This is the cost a
timestamp or flag file does not carry: neither of those needs its writer and its checker to agree on
a byte-for-byte reproducible procedure.

**Insight:** a content hash turns "did behaviour change" into a question with a mechanical answer;
the price is that the writer and the reader of that hash become permanently coupled to computing it
identically, and drift between them looks exactly like a false positive rather than an obvious wiring
bug.

> A content hash of the files that define a step supersedes a version constant here because it
> answers "is recorded state still current with actual behaviour" directly from the bytes that define
> that behaviour, at the cost of requiring the writer and the checker to hash the identical file set
> in the identical order.

### The removed auto-reindex — a mark, not the story

`check-init.sh` carries the scar of a capability it used to have and no longer does. The relevant
block, quoted in full, sits between the bootstrap-hash check and the harness-update check:

```bash
# Handbook auto-reindex-on-session-start REMOVED (AP-12461 incident). This
# used to pull both handbook clones and delta-reindex each RAG store on every
# single session start, with no coordination between concurrent sessions.
# Observed in the wild: every session hitting the same staleness gate at once
# each independently decided a reindex was due and spawned its own
# seed-rag.mjs against the same .lancedb -- hundreds of concurrent embedder
# processes, 100+ GB of abandoned partial indexes, machines unusable, and no
# recovery possible because starting a session was the trigger for the next
# pile-up. Re-index manually when handbook content changes:
#   node <handbook-dir>/scripts/seed-rag.mjs
# or via that handbook's own update path (e.g. ./start.sh --update).
```

This is the only trace of AP-12461 inside `check-init.sh` itself — there is no executable branch left
to disable, only the comment, which is the mark this section promised: the capability is gone, and
the script says why in the space where the code used to run. A repo-wide search for the incident
label turns up nothing outside this comment — `docs/adr/` (checked through `0026`) has no entry filed
for it, and the only other hits for the surrounding vocabulary are `tests/calibration/test_adr_present.py`
and `tests/check-init/test_check_init.py`, both of which test *for* an ADR's presence and the current
script's behaviour rather than narrate the incident. The full story — what actually piled up,
why "session start is the trigger for the next pile-up" is the poisonous part, the number the
syllabus wants (100+ GB), the fix, and the general law it establishes about coordinating fixed-cost
work across concurrent sessions — belongs entirely to the next file, `07-the-reindex-incident.md`,
alongside diagram D-55. Nothing about the incident is re-explained here beyond confirming: the
capability existed, it was removed, and the removal is dated to a named incident by the comment
itself.

**No SVG here:** the six-link chain's "SVG" step is not applicable to this leaf group — the manifest
gives this row no diagram of its own. D-49 (the hook lifecycle) and D-52 (the exit-code routing
table) from the earlier files in this set already draw the mechanism this file's `SessionStart` array
and stdout-to-context behaviour depend on; D-54 (the six configuration sources) is the relevant
picture for where `hooks.json` itself sits among those sources. D-55, drawing the reindex incident
concurrency pile-up, belongs to the next file.

## Pitfalls

**Belief:** "A `SessionStart` hook that fails is a broken hook and should be fixed like any other bug
that raises an exit code."
**In action:** an engineer sees `check-init.sh` occasionally producing no output on a machine missing
`coreutils`, assumes something crashed, and starts hunting for a stack trace or an error the script
never produced — because on `set +e` with a trailing `exit 0`, a skipped check looks identical to a
check that never needed to run.
**Fix:** read the guard around each check (`if [[ -n "$BOOTSTRAP_HASH_CMD" ]]`, `if command -v
glab...`) before assuming absence of output means failure; an advisory hook's silence on one finding
is by design, not a symptom.
**Why people believe it:** every other script they have ever debugged treats a missing tool or a
malformed input as an error to surface, because most scripts are not required to survive every
possible failure the way a `SessionStart` hook is.

**Belief:** "The bootstrap nudge is checking whether bootstrap was ever run."
**In action:** an engineer who ran `/sdlc-harness:bootstrap` last month, then edited a
`bootstrap-*.sh` file directly, is confused when the nudge fires again — they believe having
bootstrapped once should be permanent.
**Fix:** `[HARNESS_BOOTSTRAP_REQUIRED]` compares a content hash of the current bootstrap files
against the hash recorded the last time bootstrap completed; editing any hashed file changes the
hash and re-triggers the nudge regardless of how recently bootstrap ran.
**Why people believe it:** most "have I set this up" checks in other tools are boolean flags, so a
content-hash check that can flip back to "needs attention" without any obvious external event reads
as a bug rather than the intended behaviour.

## Cheat sheet

| Fact | Value |
|---|---|
| `hooks.json` path | `plugins/sdlc-harness/hooks/hooks.json` |
| `hooks.json` length | 33 lines (leaf estimated 30) |
| `SessionStart` handlers | 3: `check-init.sh`, `prod-guard-session-start.sh`, `calibration-nudge.sh` |
| `PostToolUse` matcher | `Write\|Edit` — not `NotebookEdit` |
| Tagged findings in `check-init.sh` | `[HANDBOOK_ACTIVE]`, `[HANDBOOK_SELECT]`, `[HARNESS_BOOTSTRAP_REQUIRED]`, `[HARNESS_UPDATE_AVAILABLE]`, `[PLUGIN_DEPENDENCY_UNRESOLVED]`, `[CLI_TOOLS_MISSING]`, `[LSP_SERVERS_SUGGESTED]` |
| Why tags reach the model | `SessionStart` exit-`0` stdout is shown to the model, not just logged |
| Defensive shape | `set +e` top, `exit 0` bottom, `timeout`/`gtimeout` + `GIT_HTTP_LOW_SPEED_*` on the network call, `sha256sum`/`shasum` fallback, `LC_ALL=C` on the glob |
| Bootstrap staleness signal | content hash of `SKILL.md` + `bootstrap-*.sh`, vs `.claude/.bootstrap-version` |
| Hash coupling | writer (`bootstrap-write-version.sh`) and checker must hash identical files, identical order |
| Removed capability | handbook auto-reindex on `SessionStart` (AP-12461) — comment only, no live branch |
| Where the incident is told | next file, `07-the-reindex-incident.md`, with D-55 |

## Self-test

1. Why does `hooks.json` register three separate `SessionStart` scripts instead of one script with
   three sections?
<details><summary>Answer</summary>Each script answers an unrelated question (bootstrap/update
status, production-credential exposure, calibration due), so splitting them gives each its own
owner, its own test file, and its own independently declared failure posture, rather than forcing one
combined `set +e`/`exit 0` discipline and one diff surface across three unrelated concerns.</details>

2. Why does the `PostToolUse` matcher `Write|Edit` not fire on a notebook cell edit?
<details><summary>Answer</summary>The matcher is a regular expression tested against the literal tool
name in the payload; `NotebookEdit` is a distinct tool name from `Write` and `Edit`, so it does not
match the alternation even though it also edits a file's contents.</details>

3. What specific fact makes it safe for `check-init.sh` to hand the model a string like
`[HARNESS_BOOTSTRAP_REQUIRED] Tell the user: ...` at all?
<details><summary>Answer</summary>`SessionStart` is one of the events where an exit-`0` script's
plain-text stdout is routed into the model's context by the harness rather than only written to a
debug log — without that routing, this text would never reach the model no matter how it was
tagged.</details>

4. Remove `set +e` from the top of `check-init.sh` but keep everything else. What breaks?
<details><summary>Answer</summary>The script reverts to bash's default of aborting on the first
command that returns non-zero — a `python3` failure reading a malformed `.claude.json`, for example —
so every check after that point in the script silently never runs, and depending on what tripped it,
the script's own final exit status could stop being the `0` the trailing `exit 0` line is there to
guarantee.</details>

5. Why is `GIT_HTTP_LOW_SPEED_TIME`/`GIT_HTTP_LOW_SPEED_LIMIT` needed in addition to `timeout 5`?
<details><summary>Answer</summary>`timeout 5` only bounds total wall-clock time; a connection that is
technically transferring data, just very slowly, would still be "making progress" and could run the
full 5 seconds regardless. The git-level low-speed cutoff aborts specifically when throughput drops
below 1000 bytes/second for 5 seconds, catching the trickling-connection case on git's own terms
rather than waiting out the wall-clock ceiling.</details>

6. Why does the bootstrap-drift check use a content hash rather than a version number bumped by hand?
<details><summary>Answer</summary>A hand-bumped version number requires a human to remember to bump
it in the same commit that changes a bootstrap step, and any missed bump leaves every workspace
believing it is current when it is not; a hash of the defining files changes automatically the moment
any byte in those files changes, with no separate bookkeeping step required.</details>

7. What single line in the hashing block exists purely so two different machines produce the same
hash for files whose contents did not change?
<details><summary>Answer</summary>`LC_ALL=C cat "$BOOTSTRAP_SKILL_FILE" "$CLAUDE_PLUGIN_ROOT"/scripts/bootstrap-*.sh` —
pinning the C locale fixes the glob's collation order so the file concatenation order cannot vary by
machine or locale, which would otherwise change the hash of an unchanged file set.</details>

8. What did the auto-reindex capability do before it was removed, and what does `check-init.sh` show
of it today?
<details><summary>Answer</summary>It used to pull both handbook clones and delta-reindex each RAG
store on every `SessionStart`. Today `check-init.sh` shows only a comment marking it removed
("AP-12461 incident") with a pointer to the manual re-index command; there is no live branch left to
run, and the full incident narrative is deferred to the next file.</details>

## Open questions

None.

---

**Leaves covered:** 2.3.21–2.3.24 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-49 to D-54 in the preceding files draw this area's mechanisms, and D-55 in the next file draws the incident
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 549
