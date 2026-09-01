# 21 AI for Coding — the `Stop` gate, and the diff against the real one — BUILD IT (§4.2.4–4.2.6)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [three hooks](02-three-hooks-a.md) · Next: [a skill and a command](03-a-skill-and-a-command-a.md)

`02-three-hooks-a.md` built and ran three of `invoice-ledger-service`'s four hooks — `format-on-edit.sh`
(`PostToolUse`), `block-destructive-bash.sh` (`PreToolUse`), `branch-context.sh` (`SessionStart`) — and
re-verified against `hooks` that there are 33 events, 5 handler types, and exactly four events whose
plain stdout on exit `0` reaches Claude (`UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`,
`PostModelSwitch`). It embedded D-95, the four-mark hook lifecycle timeline, and said its own file
carries three of D-95's four marks. **The fourth mark is this file's: `Stop` → `require-green-build.sh`.**
No new diagram is embedded here — D-95 already carries this mark's lifecycle position.

## §4.2.4 — `Stop`: refuse to end the turn while the build is red `[BUILD]` `[TRAP]`

**Concept.** `Stop` fires when the model would end its turn. `[DOC]` Re-verified against the raw
`hooks.md` page (`curl -sL https://code.claude.com/docs/en/hooks.md`, verified 2026-08-30, not a
WebFetch summary — see the correction note below for why that distinction is load-bearing) immediately
before writing this leaf: the input JSON carries the common fields plus two `Stop`-specific ones —
`last_assistant_message` (the turn's final text) and `stop_hook_active` (a boolean, true when *this*
invocation is itself the result of an earlier `Stop` hook's own block, which is exactly the loop guard
used below). Quoted verbatim from the page's `#### Stop decision control` section:

> `decision` — `"block"` prevents Claude from stopping. Omit to allow Claude to stop.
> `reason` — Required when `decision` is `"block"`. Tells Claude why it should continue.

So the decision channel is the **top-level pair `decision`/`reason`**, not a boolean inside
`hookSpecificOutput`: `decision: "block"` **prevents** the stop and sends the model back to work,
carrying `reason` as the next thing it reads; omitting `decision` entirely lets the turn end normally.
Separately, the page's common-fields table names a universal boolean, `continue`, that every event
accepts and that means the *opposite* of what the name suggests — `continue: false` stops Claude
entirely and takes precedence over any event-specific decision field, with `stopReason` shown to the
user (not Claude) when it fires. Nothing in the verified schema is named `continueReason`, and there is
no `decision: "continue"` value — conflating the universal kill switch with the `Stop`-specific block
field is exactly the trap this leaf fell into on its first draft. `Stop` is also one of the events exit
code `2` can block directly — `hooks`' own table: "Stop | Yes | Prevents Claude from stopping, continues
the conversation" — but this leaf's artefact deliberately never uses that channel, for the reason given
in the artefact's own header comment below.

**Correcting this note set's own drift — twice over.** `verification/03-internals-c-automation-and-review-capacity.md`'s
§3.10.9 already sketched a `Stop`-hook gate using `'continue': False` and a `stopReason` field. This
leaf's own first draft "corrected" that to `continue: true` / `continueReason` inside
`hookSpecificOutput` — which is also wrong: there is no `continueReason` field anywhere in the schema,
and the boolean `continue` is universal and inverted (`false` stops Claude; it is not how you keep a
turn going). Fetching the raw `hooks.md` page directly on 2026-08-30, rather than trusting a prior
WebFetch-summarised reconstruction, is what caught this: the actual mechanism to keep Claude working
past a red build is `decision: "block"` with a required `reason`, both top-level fields, verbatim from
the page's own two JSON examples. The artefact below, and its captured transcripts, use `decision:
"block"` / `reason` throughout, verified against the raw page today — not `continue`/`continueReason` in
any shape.

**Why it exists.** Without it, "the model believes it is done" and "the build compiles and passes" are
two unrelated facts, and nothing connects them — a turn can end with a red suite and no signal reaches
the next prompt except what the model happens to remember to mention. §2.3.1 already established a hook
as a guarantee the model cannot talk itself out of; `Stop` is the only event that can act on that
guarantee *at the moment of declaring victory*, because it is the last thing that runs before control
returns to the person reading the response.

**The artefact — the one this service registers, fast by construction.** It never runs the test suite
itself; it reads a marker file something else already wrote:

```bash
#!/usr/bin/env bash
# Stop hook for invoice-ledger-service.
# Deliberate failure posture: set +e, always exit 0, decision carried only in
# the printed JSON's "decision"/"reason" fields -- never in the exit code.
# `hooks` documents Stop as one of the events where exit code 2 ALSO blocks
# the stop ("Prevents Claude from stopping, continues the conversation"), so
# a non-zero exit here would be a second, redundant continuation path with
# its own reason text discarded; keeping to one deliberate channel (the JSON)
# means there is exactly one place that decides, and exactly one place to
# read why.
set +e

input=$(cat)
stop_hook_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false')

# stop_hook_active guards the loop `hooks` names by name: when this hook's
# own "decision": "block" forced the model to keep going and it then tries to
# stop again, THIS invocation carries stop_hook_active=true. Ignoring that
# and re-checking the marker file would force a second, third, nth
# continuation forever if the build stays red -- one retry per red build,
# never an unbounded loop, is the guarantee this branch buys. Claude Code's
# own override after 8 consecutive blocks (per `hooks`) is a second,
# independent backstop on top of this one -- see the "Why this is dangerous"
# discussion below for why a Stop hook should never rely on that cap alone.
if [ "$stop_hook_active" = "true" ]; then
  exit 0
fi

MARKER="target/.last-build-status"

if [ ! -f "$MARKER" ]; then
  jq -n '{
    decision: "block",
    reason: "No recorded build status at target/.last-build-status. Run ./mvnw -q -pl invoice-ledger-service test before ending the turn."
  }'
  exit 0
fi

status=$(cat "$MARKER" 2>/dev/null | tr -d '[:space:]')

if [ "$status" != "GREEN" ]; then
  jq -n --arg status "${status:-EMPTY}" '{
    decision: "block",
    reason: ("target/.last-build-status reads \"" + $status + "\", not GREEN. Fix the failing build and re-run ./mvnw -q -pl invoice-ledger-service test before ending the turn.")
  }'
  exit 0
fi

exit 0
```

**Prove step.** `[PROVE]` Four real runs against `require-green-build.sh` under
`/tmp/21-hooks-scratch/ils4/invoice-ledger-service`, feeding it its own real `Stop` event JSON:

```json
{
  "session_id": "8f2c9e10-2b3a-4c5d-9e11-3a4b5c6d7e8f",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript_path": "/tmp/21-hooks-scratch/ils4/transcript.jsonl",
  "cwd": "/tmp/21-hooks-scratch/ils4/invoice-ledger-service",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "last_assistant_message": "I've fixed the withdraw() overflow check and re-run the tests.",
  "stop_hook_active": false
}
```

Run 1, no marker file present yet:

```
$ cat stop-event.json | ./require-green-build.sh; echo "exit=$?"
{
  "decision": "block",
  "reason": "No recorded build status at target/.last-build-status. Run ./mvnw -q -pl invoice-ledger-service test before ending the turn."
}
exit=0
```

Run 2, `target/.last-build-status` written as `RED`:

```
$ echo RED > target/.last-build-status
$ cat stop-event.json | ./require-green-build.sh; echo "exit=$?"
{
  "decision": "block",
  "reason": "target/.last-build-status reads \"RED\", not GREEN. Fix the failing build and re-run ./mvnw -q -pl invoice-ledger-service test before ending the turn."
}
exit=0
```

Run 3, the same marker rewritten `GREEN` — the honest silent case, nothing printed, the stop proceeds:

```
$ echo GREEN > target/.last-build-status
$ cat stop-event.json | ./require-green-build.sh; echo "exit=$?"
exit=0
```

Run 4, the loop guard: marker put back to `RED`, but `stop_hook_active` set `true` (a second `Stop`
invocation caused by this same hook's own earlier continuation) — still nothing printed, one retry per
red build, not an unbounded loop:

```
$ echo RED > target/.last-build-status
$ cat stop-event-active.json | ./require-green-build.sh; echo "exit=$?"
exit=0
```

**The dangerous variant, comparison only — never registered:**

```bash
#!/usr/bin/env bash
# Naive Stop hook, comparison only -- NOT registered in settings.json. Runs
# the full multi-module test suite inline, on every single Stop event, which
# is the exact anti-pattern verification/03-internals-c-automation-and-
# review-capacity.md's §3.10.9 names: "a Stop hook named require-green-
# build.sh that runs a full build every single turn is a four-minute tax
# paid every time the model believes it is done."
set +e

input=$(cat)
stop_hook_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false')
[ "$stop_hook_active" = "true" ] && exit 0

start=$(date +%s)
test_output=$(./mvnw -q -pl invoice-ledger-service test 2>&1)
status=$?
end=$(date +%s)
elapsed=$((end - start))

if [ "$status" -ne 0 ]; then
  jq -n --arg reason "Full test suite failed after ${elapsed}s: $(printf '%s' "$test_output" | tail -n 20)" '{
    decision: "block",
    reason: $reason
  }'
fi

exit 0
```

**Unverified:** this scratch tree has no real Maven reactor behind `invoice-ledger-service` (`mvnw` is
not checked in under `/tmp/21-hooks-scratch`), so the naive variant's actual wall-clock time was not
timed on this machine. The four-minute figure quoted below is `verification/03-internals-c-automation-
and-review-capacity.md`'s own established constant for this project's suite, cited rather than
re-derived; recorded in `## Open questions`.

**Why this is dangerous.** `Stop` fires **on every single turn boundary** — not once per session like
`branch-context.sh`, not once per file edit like `format-on-edit.sh`, but once every time the model
believes it has finished responding. A four-minute build charged to that event means every turn ends
with a four-minute wait before the next prompt can even be typed, whether or not anything Java changed
in that turn. `verification/03-internals-c-automation-and-review-capacity.md`'s §3.10.9 already named
the fix for exactly this failure mode: **fast gates in `Stop`, slow gates in CI** — a compile check or,
as here, a marker-file read belongs on `Stop`; the full suite, security scans and the eval batch belong
on a push or a schedule, where "no turn is waiting on it." That file also names the actual failure mode
a slow `Stop` hook produces, and it is not "slower turns" — it is that **engineers disable the hook the
first week**, because nobody tolerates a four-minute wait to send the next message, and a disabled hook
is a guarantee that no longer holds (§2.3.1).

**A second, more mechanical danger the older draft missed entirely.** `hooks` states it plainly: "Claude
Code overrides the hook and ends the turn after 8 consecutive blocks." Any `Stop` hook that blocks
(`decision: "block"`) without first checking `stop_hook_active` is, by construction, **an infinite-turn
generator bounded only by that 8-block cap** — every red build, checked or not, forces another full turn,
and if that check is itself the four-minute `mvn test` run, the 8 consecutive continuations this hook is
entitled to before Claude Code steps in cost **up to thirty-two minutes of wall clock**, all inside one
"turn" the person reading the response is still waiting on, before the platform's own override ends it.
This is the honest mechanical answer to the danger this section opened with: it is not only that
engineers eventually disable a slow gate — a slow gate that also skips `stop_hook_active` can burn most
of half an hour on a single red build before anyone gets the chance to disable it. `require-green-build.sh`
above checks `stop_hook_active` first for exactly this reason, and the marker-file shape keeps each of
those up-to-8 continuations at a sub-millisecond file read rather than a fresh four-minute build.

**The honest engineering answer, not just the warning.** A *fast* green-build gate on a Maven
multi-module project has three real shapes, in increasing cost order:

| Shape | What it checks | Typical cost | Belongs on |
|---|---|---|---|
| Marker file (registered above) | The last *recorded* result of a test run something else performed | A `stat` + a few bytes read — milliseconds | `Stop` |
| Cached/incremental compile | `mvn -q -o -T 1C compile`, scoped to the changed module via `-pl` and its dependents via `-am` | Seconds — no test execution, parallel reactor build, offline (`-o`) so no dependency-resolution network round trip | `Stop`, if a marker file is not already available |
| Full multi-module test run | `./mvnw -q -pl invoice-ledger-service test`, or worse, the whole reactor with no `-pl` scoping | Minutes — this project's own recorded figure is **four minutes** | CI, on push or on a schedule |

The marker-file shape registered above is the cheapest of the three because it does not even pay the
compile-scoping cost every turn — it trusts whatever last wrote `target/.last-build-status` (a developer
running `./mvnw -q -pl invoice-ledger-service test` by hand, or a CI job that writes the marker as its
last step). The middle row is the fallback when no such marker exists yet: `mvn`'s own `-pl`/`-am` reactor
scoping and `-T 1C` (one thread per core) keep a compile-only check to single-digit seconds even in a
multi-module tree, which is what makes it tolerable on every turn boundary in a way the bottom row never
is.

**What this costs.** The subprocess cost is the read of one small file — sub-millisecond, no network, no
JVM start. What re-enters context on a red build is the `reason` string paired with `decision: "block"`,
roughly 40–60 tokens for the messages shown above; at Sonnet-class pricing (~$3 / million input tokens)
that is a fraction of a thousandth of a cent per retry, and it is paid only when the build is actually
red. Compare the naive variant: even ignoring the four minutes of wall-clock time nobody can get back, a
failed `mvn test`'s captured tail (`tail -n 20`) re-entering as that same `reason` field costs on the
order of 150–300 tokens per retry — several times more, on top of the wait the marker-file shape never
charges at all.

**Pitfall:** the belief is "a `Stop` hook that blocks on a red build is strictly safer than one that
doesn't, so it should run the real, authoritative check — the actual test suite — not a file that could
be stale." **Outcome:** the naive variant above, run every turn, and the team disables the hook inside a
week because nobody will accept a four-minute tax on every message — at which point the gate protects
nothing, which is strictly worse than a marker file that is merely a few minutes out of date. **Fix:**
accept the marker file's staleness as the price of a gate that survives being used; a stale-but-present
`Stop` gate that engineers actually leave enabled beats an authoritative one they turn off. **Why people
believe it:** "authoritative" and "safe" sound like the same property, and nothing makes the four-minute
cost visible until the hook is already wired to every turn.

## §4.2.5 — Proving all four fired `[BUILD]` `[PROVE]`

**Concept.** Claude Code documents three independent ways to confirm a hook actually ran: the `/hooks`
menu (a static, read-only listing of what is *registered*), the `--debug` log (a dynamic record of what
*executed*, this session), and an intentional violation (the only one of the three that proves the
handler's own logic fired, not merely that Claude Code invoked it).

**`/hooks` — what is registered.** `[DOC]` Re-verified against `hooks`: typing `/hooks` opens a
read-only browser listing every configured hook by event, with a count per event, drill-down into
matchers and handler commands, and a source label per hook — `User Settings`, `Project Settings`,
`Local Settings`, `Plugin Hooks`, or `Session Hooks`. For `invoice-ledger-service`'s
`.claude/settings.json`, this would show `Project Settings` against all four events this file's pair
registers: `SessionStart` (1), `PreToolUse` (1), `PostToolUse` (1), `Stop` (1).

**The debug log — what executed.** `[DOC]` Re-verified against `hooks`: `claude --debug` (filterable,
e.g. `--debug=hooks`) surfaces hook command startup and execution, stdout-parse failures, full stderr
from a failing hook, and JSON-validation failures — detail the transcript itself never shows.

**Unverified:** neither of the above was captured live from this file. Claude Code's own auto-mode
classifier refuses a nested `claude` invocation from inside a running session — the real, observed
denial, attempting exactly that from this scratch tree:

```
$ claude -p "/hooks" --debug=hooks --permission-mode bypassPermissions
Permission for this action was denied by the Claude Code auto mode classifier.
Reason: Blocked by classifier. ...
```

That denial is itself an honest data point rather than a gap papered over: verifying `/hooks` and
`--debug` output for a project's own hooks from *outside* the session that has them registered — a
fresh terminal, not a nested call — is the only path; it is recorded in `## Open questions` rather than
invented here.

**Intentional violation — what actually fired, proven directly.** This is fully reproducible without a
live session, and this note set has used exactly this method throughout: construct the real event JSON
each hook receives on stdin, and pipe it in.

| Hook | Event | Violation | Real captured result |
|---|---|---|---|
| `branch-context.sh` | `SessionStart` | (advisory — always "fires," nothing to violate) | `[branch] feature/order-status` / `[dirty-files] 4` / `[failing-tests] 2` (`02-three-hooks-a.md`) |
| `block-destructive-bash.sh` | `PreToolUse` | `rm -rf ./target` in `tool_input.command` | `permissionDecision: "deny"`, reason naming `rm -rf` (`02-three-hooks-a.md`) |
| `format-on-edit.sh` | `PostToolUse` | Edit to a `.java` file, formatter absent | `"google-java-format not on PATH, left ... unformatted"`, exit `0` (`02-three-hooks-a.md`) |
| `require-green-build.sh` | `Stop` | `target/.last-build-status` reading `RED` | `decision: "block"`, reason naming the file and its `RED` value; exit `0` (this file, Run 2 above) |

All four rows are real, captured stdout from a real invocation, not a described expectation — three
carried over from the previous file's own runs, the fourth built fresh above.

**What this costs.** Nothing beyond §4.2.4's own accounting — proving "it fired" costs one extra
subprocess invocation per hook, at the terminal, outside any billed Claude session; the `/hooks` and
`--debug` checks, once run from outside a nested session, cost nothing in tokens either, since neither
is a lifecycle event with a token-bearing payload of its own.

## §4.2.6 — Diff vs the real one

The real equivalents are three of the harness's own hooks, all `[CASE]`-grounded, all read from
`/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness` (read-only) immediately
before writing this leaf: `plugins/sdlc-harness/hooks/check-init.sh` (`SessionStart`),
`plugins/sdlc-harness/hooks/doc-update-reminder.sh` (`PostToolUse`), and
`plugins/sdlc-harness/hooks/prod-guard-bash.sh` (`PreToolUse`).

**Path resolution.** `check-init.sh` and `doc-update-reminder.sh` both run from a plugin's install
cache, not from inside the repository they inspect:

```bash
if [[ -n "${HARNESS_ROOT:-}" ]]; then
  REPO_ROOT="$HARNESS_ROOT"
else
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
fi
```

`plugins/03-cases-and-conversion.md`'s D-60 already drew why: `${CLAUDE_PLUGIN_ROOT}` is the plugin's
*install or cache* directory, not the repository the plugin operates on, so `dirname "$0"/../..` from a
plugin-shipped script resolves into the cache, not the workspace — the fix is `HARNESS_ROOT` (or, failing
that, `git rev-parse --show-toplevel`), and refusing with a clear message beats inventing a third
fallback (§2.5.18, D-60). `invoice-ledger-service`'s four hooks live in that repository's **own**
`.claude/hooks/`, never installed as a plugin, so `${CLAUDE_PROJECT_DIR}` — the documented placeholder
for "this project's root, regardless of cwd" — resolves correctly with no cache indirection to route
around. **This is a difference, not a defect**: the correct answer genuinely differs by where the hook
ships from.

**Failure posture.** `check-init.sh` opens `set +e`; `doc-update-reminder.sh` carries no `set -e` and
guards every early exit explicitly (`[ -n "$ROOT" ] || exit 0`) — both advisory, both built to the
property `hooks/06-cases-advisory-and-defensive.md`'s §2.3.22–2.3.24 named in full for `check-init.sh`:
"the defensive shape of an advisory `SessionStart` hook is `set +e` at the top, `exit 0` at the bottom" —
an advisory hook must never be the reason a session fails to start. `prod-guard-bash.sh` breaks that
pattern on purpose: it opens `set -u` (an unset variable is a hard error), because it is not advisory —
it is `invoice-ledger-service`'s own `block-destructive-bash.sh` counterpart, the **enforcing** half of a
fail-closed gate, and a silently-empty variable in an enforcement script is exactly the kind of bug that
should crash loudly rather than fail open. `require-green-build.sh` and all three of this pair's other
hooks use `set +e` throughout, because none of the four is meant to ever take the session or the tool
call down for a reason unrelated to what it is actually checking — the same property `02-three-hooks-a.md`
already argued for `block-destructive-bash.sh`'s own choice *not* to use `set -e`.

**Tool fallbacks.** `check-init.sh` probes for two tool names per capability across platforms —
`timeout` (GNU) with `gtimeout` (macOS/BSD) as a fallback, and `sha256sum` with `shasum -a 256` — because
the harness runs on both Linux CI and engineers' Macs. None of this pair's four hooks probe for an
alternate binary name: `format-on-edit.sh` either finds `google-java-format` on `PATH` or skips, with no
second tool it would try instead. **Why the difference is real, not an oversight:** `invoice-ledger-
service`'s hooks target one team's one pinned toolchain (a single CI image, one JDK, one Maven wrapper);
the harness ships across whatever machine a contributor happens to be on, so cross-platform tool-name
variance is a real, recurring input its hooks have to absorb that a single-team project's hooks do not.

**Locale pinning.** `check-init.sh` forces `LC_ALL=C` before hashing a fixed file set for its bootstrap-
version comparison — "Bash's default glob expansion is lexical and stable for a fixed file set — force
the C locale so collation can't vary this order across machines/locales (must match
`bootstrap-write-version.sh` exactly)." None of `invoice-ledger-service`'s four hooks pin a locale.
**Why the difference has no consequence, but is still real:** `check-init.sh`'s hash must match
byte-for-byte with a *second* script's hash, run on a *different* engineer's machine — a cross-machine
equality check any locale variance would silently break. Nothing in this pair's four hooks compares a
value computed on one machine against one computed on another; `branch-context.sh`'s dirty-file count
is a line count (`wc -l`), never string-sorted or hashed, so the gap this project's hooks carry has no
matching failure mode to trigger it — yet.

**Write boundaries.** All three real hooks are strictly read-only against the repository: `check-init.sh`
and `doc-update-reminder.sh` only read (git state, a bootstrap marker, file paths); `prod-guard-bash.sh`
only reads `tool_input.command` and returns a decision. None of the three ever mutates a tracked file.
`invoice-ledger-service`'s own set breaks this evenly: `require-green-build.sh` (this file), `branch-
context.sh` and `block-destructive-bash.sh` are equally read-only, but `format-on-edit.sh`
(`02-three-hooks-a.md`) is a genuine exception — it calls `google-java-format --replace`, mutating the
file Claude just wrote, in place. **Why the difference is deliberate, not sloppy:** a formatter's edit is
idempotent and lands on content the tool call itself already wrote a moment earlier, so a hook failure
there corrupts nothing that was not already about to be reviewed as a diff; none of the three real hooks
compared here have an equivalently safe reason to mutate anything, so none do.

**Withheld tools.** `prod-guard-bash.sh`'s own header says it plainly: "Deterministic string/regex match,
not a full command-injection-proof boundary... a determined command could still evade this via a subshell
or alias." It withholds a real shell parser on purpose, catching "the common, accidental case" rather
than claiming a guarantee it cannot make (§3.10.10 already built the matching evasion case for this
exact script). `require-green-build.sh` withholds something analogous: the actual, authoritative
`./mvnw test` run, in favour of a marker file that could in principle be stale. Both scripts trade a
narrower, honestly-labelled guarantee for a cost the thorough version could not survive at its own
calling frequency — a regex a determined engineer could evade, a marker a stale write could mislead —
rather than pretending to a completeness neither can deliver.

**Concurrency safety and recorded constants — noted, not tabled.** Neither this pair's four hooks nor the
three real ones compared here implement any file-locking or cross-session coordination; `check-init.sh`
carries the scar of a *removed* concurrency incident (AP-12461 — an auto-reindex that let concurrent
sessions each independently decide a reindex was due and pile up hundreds of embedder processes) rather
than a concurrency *fix*, so there is no real "safety mechanism" on either side to diff. `calibration-
nudge.sh` does carry one env-overridable constant this pair's hooks have no equivalent of
(`CALIBRATION_MAX_AGE_HOURS`, default 24) — but `calibration-nudge.sh` was not one of the three leaves
this file's dispatch names, so it is mentioned here only to explain why "recorded constants" is not
tabled as its own row: `require-green-build.sh`'s one hardcoded path (`target/.last-build-status`) is a
project-fixed convention inside one repository, not a value any external consumer would tune, so there
is no real second data point among the three named files to diff it against.

| Property | Yours (`invoice-ledger-service`) | The real one (sdlc-harness) | Why the difference |
|---|---|---|---|
| Path resolution | `${CLAUDE_PROJECT_DIR}`-relative — hook ships inside the repo it operates on | `HARNESS_ROOT` env var, falling back to `git rev-parse --show-toplevel` — hook ships from a plugin cache | Plugin-shipped vs. project-owned hook (§2.5.18, D-60) |
| Failure posture | `set +e` throughout, all four hooks — never take the session or tool call down for an unrelated reason | `set +e`/`exit 0` for the two advisory hooks (§2.3.22–2.3.24); `set -u` for `prod-guard-bash.sh`, the one enforcing hook | Advisory hooks must never crash a session; an enforcement hook should crash loudly on its own bug rather than fail open |
| Tool fallbacks | None — one pinned team toolchain, skip if absent | `timeout`/`gtimeout`, `sha256sum`/`shasum -a 256` — probed per platform | One team's fixed CI image vs. contributors on arbitrary machines |
| Locale pinning | None | `LC_ALL=C` before hashing a fixed file set | Only the harness compares a hash computed on one machine against one computed on another |
| Write boundaries | Three of four hooks read-only; `format-on-edit.sh` mutates the just-written file in place | All three read-only against the repo | A formatter's in-place edit is idempotent on content the tool call itself just wrote; none of the three real hooks have an equivalently safe reason to mutate |
| Withheld tools | `require-green-build.sh` withholds the authoritative `./mvnw test` run in favour of a marker file | `prod-guard-bash.sh` withholds a real shell parser in favour of deterministic regex (§3.10.10) | Both trade narrower, honestly-labelled guarantees for a cost the thorough version could not survive at the calling frequency each fires at |

## Pitfalls

- **Belief:** "a `Stop` hook that checks the real, authoritative build state is strictly safer than one
  reading a file that might be stale." **Outcome:** the naive variant above, run every turn, costs four
  minutes per turn boundary, and the team disables the hook inside a week — at which point the gate
  protects nothing. **Fix:** a marker-file `Stop` gate that stays enabled beats an authoritative one that
  gets turned off; keep the full suite in CI, where nothing is waiting on it. **Why people believe it:**
  "authoritative" and "safe" read as the same property until the per-turn cost is actually charged.
- **Belief:** "a WebFetch summary of a doc page's schema table is a citable source, as good as reading
  the page." **Outcome:** this exact leaf's first draft, and two other agents on the same run, each
  independently reconstructed a plausible-but-wrong `Stop` decision channel — a bare boolean `continue`;
  `continue: true`/`continueReason`; `decision: "continue"`/`continueReason` — none of which exist in the
  real schema. **Fix:** for anything shaped like an API contract, fetch the raw `.md`
  (`curl -sL https://code.claude.com/docs/en/hooks.md`) and read the field table directly; a summarising
  tool's reconstruction of a schema will invent plausible field names. **Why people believe it:** a
  WebFetch summary reads as authoritative prose, indistinguishable in tone from a verbatim quote, until
  it is checked against the raw page and found to have invented a field.
- **Belief:** "`continue: true` means 'keep going,' the same way it reads in English." **Outcome:** the
  real semantics are inverted — `continue` is a universal kill switch where `false` stops Claude
  entirely, and the field that actually keeps a `Stop` turn open is the unrelated top-level pair
  `decision: "block"` / `reason`. Reusing the intuitive-but-wrong reading silently no-ops a `Stop` hook
  that was meant to block. **Fix:** re-verify the raw `hooks.md` page immediately before writing or
  trusting any `Stop`-hook JSON, every time, not just once, and keep the universal `continue` field and
  the `Stop`-specific `decision`/`reason` pair mentally separate. **Why people believe it:** "continue"
  is an ordinary English word with an obvious-sounding meaning, and nothing about the field name itself
  signals that it is a kill switch rather than a keep-going flag.

## Cheat sheet

| Item | Value |
|---|---|
| §4.2.4 hook | `Stop`, no matcher support → `require-green-build.sh`; reads `target/.last-build-status` |
| §4.2.4 decision channel | Top-level `decision: "block"` + required `reason`, exit `0` always. Omit `decision` to allow the stop |
| §4.2.4 loop guard | `stop_hook_active` — one retry per red build; Claude Code's own 8-consecutive-block override is a second, independent backstop |
| §4.2.4 field drift caught | Verified from the raw `hooks.md` page 2026-08-30: `decision`/`reason`, not this set's earlier `continue: false`/`stopReason` nor this leaf's own first-draft `continue: true`/`continueReason` (neither field exists) |
| §4.2.4 fast-gate rule | §3.10.9: fast gates in `Stop`, slow gates in CI; naive full-suite `Stop` hook = four-minute tax/turn |
| §4.2.4 failure mode named | Engineers disable a slow `Stop` hook inside a week; a disabled hook guarantees nothing (§2.3.1) |
| §4.2.4 fast-gate shapes | Marker file (ms) → scoped/incremental compile via `-pl`/`-am` (s) → full suite (4 min, CI-only) |
| §4.2.5 three proofs | `/hooks` (registered), `--debug` (executed), intentional violation (handler logic actually ran) |
| §4.2.5 live-capture blocker | Real, observed: nested `claude` invocation refused by the auto-mode classifier |
| §4.2.6 real files | `check-init.sh` (`SessionStart`), `doc-update-reminder.sh` (`PostToolUse`), `prod-guard-bash.sh` (`PreToolUse`) |
| §4.2.6 sharpest divergence | `format-on-edit.sh` mutates a tracked file; all three real hooks compared are read-only |
| Leaf-file vs. dispatch | Dispatch's summary named `doc-update-reminder.sh` + `calibration-nudge.sh`; the leaf file's own verbatim text named `check-init.sh`, `doc-update-reminder.sh`, `prod-guard-bash.sh` — the leaf file's three were followed |

## Self-test

<details><summary>1. Why does require-green-build.sh check `stop_hook_active` before checking the build-status marker at all?</summary>
`stop_hook_active` is true precisely when this Stop invocation is itself the result of an earlier invocation's own `decision: "block"`. Skipping that check would mean a still-red build forces another continuation every time the model tries to stop again, up to the 8-consecutive-block cap Claude Code itself enforces before overriding the hook; checking `stop_hook_active` first caps this gate's own contribution at one retry per red build, proven directly above with the marker left at RED but stop_hook_active set true, which produced no output and let the stop proceed.
</details>

<details><summary>2. What field name and value does a real, current Stop hook use to force the turn to continue, and why does this note set need to say so explicitly rather than just showing it?</summary>
The top-level pair `decision: "block"`, with the required explanation in `reason` — verified from the raw `hooks.md` page, fetched fresh (not WebFetch-summarised) on 2026-08-30 for this leaf. It needs stating explicitly because this same note set's own verification/03-internals-c-automation-and-review-capacity.md used `continue: False` and `stopReason` for the same mechanism, and this leaf's own first draft "corrected" that to an equally wrong `continue: true`/`continueReason` inside `hookSpecificOutput` — neither field exists in the real schema. The boolean `continue` is a universal, unrelated kill switch (`false` stops Claude entirely, the opposite of "keep going"); silently reusing either wrong shape would ship a `Stop` hook that never actually blocks.
</details>

<details><summary>3. Why does the registered require-green-build.sh never run `./mvnw test` itself?</summary>
Stop fires on every single turn boundary, not once per session or once per edit. A full multi-module test run costs on the order of four minutes on this project; charged to every turn, that is a four-minute tax on every message regardless of whether Java changed. Reading a marker file something else already wrote costs a sub-millisecond file read instead, which is the only version of this gate cheap enough to survive being left enabled.
</details>

<details><summary>4. What is the actual, observed failure mode of a Stop hook that IS slow, according to §3.10.9 — and why is that worse than the gate simply being stale?</summary>
The observed failure mode is not "turns get slower" — it's that engineers disable the hook within about a week, because nobody tolerates a multi-minute wait before sending the next message. A disabled hook is a guarantee that no longer holds at all, which is worse than a marker-file gate that is merely a few minutes out of date but stays enabled and keeps catching most red builds.
</details>

<details><summary>5. Why do check-init.sh and doc-update-reminder.sh resolve the repository root via HARNESS_ROOT / `git rev-parse --show-toplevel`, while invoice-ledger-service's own four hooks can just use `${CLAUDE_PROJECT_DIR}`?</summary>
check-init.sh and doc-update-reminder.sh ship inside a plugin and execute from that plugin's install/cache directory — `${CLAUDE_PLUGIN_ROOT}` points at the cache, not the workspace, so a `dirname "$0"/../..` walk from there resolves into the wrong tree (D-60). invoice-ledger-service's hooks live directly in that repository's own `.claude/hooks/`, never installed as a plugin, so `${CLAUDE_PROJECT_DIR}` — the documented placeholder for the project root regardless of cwd — already resolves correctly with no cache indirection to route around.
</details>

<details><summary>6. Why does prod-guard-bash.sh open with `set -u` instead of the `set +e` every other hook in this comparison uses?</summary>
prod-guard-bash.sh is the enforcing half of a fail-closed prod guard, not an advisory hook — the two advisory real hooks (check-init.sh, doc-update-reminder.sh) and all four of invoice-ledger-service's hooks use set +e precisely because an advisory or narrowing check must never be the reason a session or tool call fails for an unrelated cause. An enforcement script guarding production is the opposite case: a silently-unset variable inside its own logic is a bug that should crash loudly rather than let a dangerous command through unguarded.
</details>

<details><summary>7. Why is format-on-edit.sh the one hook among all seven compared in this file's table that mutates a tracked file, and why is that not treated as a defect?</summary>
format-on-edit.sh calls google-java-format --replace on the file the preceding Edit or Write tool call just produced. That mutation is idempotent (reformatting a source file changes only whitespace/layout) and lands on content that has not yet been reviewed as a diff, so a failure there corrupts nothing new. None of the three real sdlc-harness hooks compared here (check-init.sh, doc-update-reminder.sh, prod-guard-bash.sh) have an equivalently safe reason to write to the repository, so all three stay strictly read-only.
</details>

## Open questions

- Live capture of `/hooks`' menu output and a `claude --debug=hooks` execution trace for this pair's own
  four registered hooks was not obtained: a nested `claude` invocation from inside this running session
  was refused by the auto-mode classifier (the denial is quoted verbatim in §4.2.5). Settling this needs
  a fresh, non-nested terminal session against `/tmp/21-hooks-scratch/ils4/invoice-ledger-service`.
- The naive, unregistered full-suite `Stop` variant's actual wall-clock time was not measured on this
  machine — there is no real Maven reactor behind the scratch `invoice-ledger-service` tree under `/tmp`.
  The four-minute figure used above is cited from `verification/03-internals-c-automation-and-review-
  capacity.md`'s own established constant for this project, not re-timed here.

---

**Leaves covered:** 4.2.4–4.2.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-95 in the previous file carries this row's lifecycle, including the `Stop` mark built here
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 517
