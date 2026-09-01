# 21 AI for Coding — payloads, exit codes and the JSON contract — INTERMEDIATE (§2.3.10–2.3.14)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the event catalogue](02-the-event-catalogue.md) · Next: [a hook cannot unblock a deny](04-a-hook-cannot-unblock-a-deny.md)

The previous file established which of the 33 events can block and which field each one honours in
outline — a lookup table, not a mechanism. This file supplies the mechanism underneath that lookup:
the shape of the JSON a hook receives on stdin, the exact three-way exit-code contract that decides
whether a hook's output means anything at all, and the field-by-field contract for the JSON output a
hook prints. Two facts anchor everything below. First, exit code `2` is the only code that blocks
without any JSON at all, and stdout is normally invisible to the model except on a small, named set
of events. Second — and this is the one that actually bites in production — exit `2` overrides a
JSON `permissionDecision: "allow"` outright. A hook that computes "allow" and then crashes on an
unrelated line still blocks the call.

## §2.3.10–2.3.11 The stdin payload: what the previous file already showed, and what it did not

**Mental model.** Every hook handler that reads input gets exactly one JSON object per invocation —
the previous file already established the always-present core (`session_id`, `transcript_path`,
`cwd`, `permission_mode`, `hook_event_name`, and `prompt_id` from v2.1.196 onward) and the general
principle that event-specific keys ride alongside it. Two things from that core are worth pinning
down more precisely before moving on, and then this leaf's real job is the payload keys the
previous file did not enumerate: what `UserPromptSubmit`, `Stop`, and `FileChanged` carry beyond the
common set.

**§2.3.10, precisely.** `permission_mode` is not a free-form string — re-verified against
`https://code.claude.com/docs/en/hooks` on 2026-08-29, the harness sends exactly one of six values:
`default`, `plan`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`. This is the same six-mode
set §1.4.25 covers in full elsewhere in this guide; a hook script that switches behaviour by
permission mode should switch on these six spellings and no others. `transcript_path` carries one
more caveat the previous file's example did not surface: the docs note it **may lag the current
turn** — a hook that reads the transcript file to reconstruct recent history can be reading content
one turn stale, which is exactly why `Stop` and `SubagentStop` ship `last_assistant_message` directly
in the payload instead of asking the hook to go re-read the transcript for it.

**§2.3.11, the payloads not yet shown.** Three event families carry fields distinct from anything in
the tool-event or session-event examples already given:

- **`Stop` and `SubagentStop`** carry `last_assistant_message` — the final assistant text of the
  current turn, delivered inline specifically so a hook does not have to open `transcript_path` and
  race the lag just described. `[DOC]` confirmed by name against the live page: "Hooks that need the
  final assistant text of the current turn should use `last_assistant_message` on `Stop` and
  `SubagentStop` instead of reading the transcript." **Unverified:** whether `Stop`'s payload also
  carries a separately named `stop_reason` field distinct from `last_assistant_message`, as this
  file's leaf claims — the live page's per-event `Stop` schema section did not render in this
  session's fetch. Recorded in `## Open questions`.
- **`UserPromptSubmit`** carries the text the user typed, so a hook can inspect or reject a prompt
  before the model ever sees it. **Unverified:** the exact field name (`user_input` per this leaf's
  wording, but not independently confirmed against the rendered page in this session).
- **`FileChanged`** carries what changed. **Unverified:** the exact field names (`file_path` and
  `change_type` per this leaf's wording, not independently confirmed against the rendered page in
  this session) — file 02 already established that `FileChanged`'s `matcher` targets "literal
  filenames," which implies at minimum a path is present on the payload, but the precise key name is
  not re-confirmed here.

**Gotcha.** A script that assumes a field name it has not actually seen in a real payload — guessing
`user_input` instead of dumping the object and reading the key that is actually there — fails
silently under the same `jq // "unknown"` fallback pattern the previous file warned about: the
fallback swallows a wrong guess as cleanly as it swallows a genuinely absent key. The safe habit for
any event this file has not already shown a payload for: log `$(cat)` to a scratch file once during
development and read the real keys off it before writing the `jq` filter.

## §2.3.12 Exit-code semantics: three paths, one of which needs no JSON at all

**Mental model.** A hook's exit code is not "success or failure" the way a shell script's exit code
usually is — it is a **three-way switch** that decides whether the harness even looks at what the
hook printed. Think of it as a request dispatcher choosing between three completely different
codepaths based on one integer, the way an HTTP framework's status code decides whether the response
body is parsed as the payload, ignored as an error page, or something in between.

**Why it exists.** A hook script can fail for reasons that have nothing to do with the decision it
was trying to make — a missing binary, a network blip fetching a linter, a typo in a shell
conditional. If every nonzero exit blocked the action under review, hook authors would be
incentivised to swallow every possible failure just to avoid accidentally locking themselves out of
their own tool calls. Splitting "blocking error" (`2`) from "any other failure" (`1`, `3`–`255`) lets
a script fail loudly on genuine breakage without also holding a permission gate hostage to that
breakage.

**How it works.** Re-verified against `https://code.claude.com/docs/en/hooks` on 2026-08-29, the
three paths are:

| Exit code | Blocks? | What happens to stdout | What happens to JSON on stdout |
|---|---|---|---|
| `0` | No | Written to the debug log only, on nearly every event | On `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, **and `PostModelSwitch`**, plain-text stdout is instead added as context the model can see and act on |
| `2` | **Yes, unconditionally on a blockable event** | N/A — the block itself is the effect | Still parsed if present: a `permissionDecisionReason` in valid JSON supplies the reason shown to the model; otherwise stderr text supplies it |
| anything else (`1`, `3`–`255`) | No, with two named exceptions below | Non-blocking; valid JSON matching the event's schema is still honoured as the decision, invalid JSON or plain text is a non-blocking notice in the transcript | Honoured exactly as on exit `0` if it parses |

`[NUM]` `[VERSION]` Correct one widely repeated piece of folklore here: **exit code `1` is not the
blocking code.** Unix convention trains every backend engineer that `1` means "something went wrong,"
and on this contract that intuition is actively wrong — `1` behaves like every other non-`2`,
non-zero code: non-blocking, and if the script also printed valid matching JSON, that JSON is still
read and acted on. The two named exceptions to "non-`2` never blocks" are narrow and worth
memorising rather than generalising from: **`WorktreeCreate`** aborts worktree creation on *any*
nonzero exit, not just `2`, and **`PreModelSwitch`** blocks the model switch if its hook times out,
independent of what exit code it eventually would have returned.

![D-52 — Hook exit codes and the JSON contract. Follow the highlighted merge: exit 2 overrides a JSON `permissionDecision: "allow"`.](../diagrams/D-52-hook-exit-codes-json-contract.svg)

**D-52** — Hook exit codes and the JSON contract. Follow the highlighted merge: exit 2 overrides a
JSON `permissionDecision: "allow"`.

**Code.** `block-destructive-bash.sh`, extended from the previous file's `PreToolUse` guard to show
all three paths from one script by branching on what it finds, rather than three separate scripts:

```bash
#!/usr/bin/env bash
set -e

INPUT_JSON="$(cat)"
COMMAND="$(echo "$INPUT_JSON" | jq -r '.tool_input.command // ""')"

if echo "$COMMAND" | grep -Eq '(^|[[:space:]])rm[[:space:]]+-rf[[:space:]]+/'; then
  # Path 1: exit 2, no JSON needed at all — the blocking code stands on its own.
  echo "block-destructive-bash.sh: refusing rm -rf against root-rooted path: $COMMAND" >&2
  exit 2
fi

if echo "$COMMAND" | grep -Eq '(^|[[:space:]])rm([[:space:]]|$)'; then
  # Path 2: exit 0, JSON present, honoured because the exit code is 0.
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"rm without -rf /: confirm target before proceeding"}}'
  exit 0
fi

# Path 3: exit 0, no JSON — plain success, the command proceeds untouched.
exit 0
```

`jq -r '.tool_input.command // ""'` reads the real field path from §2.3.11's `PreToolUse` example in
the previous file — `tool_input.command` on a `Bash` call — not an invented key. The first branch
never constructs JSON at all: exit `2` alone is a complete, self-sufficient blocking signal, which is
the point this leaf exists to land. The second branch shows the ordinary allow-with-caveat path,
where the JSON only matters *because* the exit code is `0`.

**Insight:** the three-way split means a hook author never has to choose between "fail safe" and
"fail informative" — a genuine script bug (a missing `jq`, a syntax error) naturally exits with
whatever non-`2` code the shell assigns it, which is non-blocking by default, while the one code that
blocks is the one the author has to reach for on purpose. The framework's default direction is
"broken hook does not lock you out," and that default has to be deliberately overridden by writing
`exit 2`, not accidentally triggered by an unrelated crash — with one caveat, covered next, once JSON
is already in the mix.

**Gotcha.** No gotcha stands alone here beyond the one the next leaf develops in full — §2.3.13 is
this leaf's gotcha, promoted to its own numbered leaf because it is the specific, most expensive way
this three-way contract gets misused.

> Exit code `0` is success and non-blocking, exit code `2` is the sole blocking code and is honoured
> whether or not JSON is present, and every other code is non-blocking regardless of magnitude —
> with `WorktreeCreate` and a timed-out `PreModelSwitch` hook as the two named exceptions to "non-`2`
> never blocks."

## §2.3.13 `[TRAP]` Exit 2 overrides a JSON `permissionDecision: "allow"`

**Mental model.** Treat the exit code and the JSON body as two independent channels that both reach
the harness, but one of them has veto power. The JSON body is a *proposal* — "here is the decision I
computed." The exit code is the *ruling* — and when the ruling is `2`, the proposal's content is
demoted to supplying the *reason* for a block it does not get to prevent.

**Why it exists.** Re-verified against `https://code.claude.com/docs/en/hooks` on 2026-08-29, the
documentation states this in exactly these terms: **"Exit 2 blocks whether or not you print JSON:
even a JSON `permissionDecision` of `\"allow\"` cannot override it."** The reason this asymmetry
exists rather than "last write wins" or "JSON wins": exit codes are the layer a process-management
convention already trusts everywhere — a subprocess that returns `2` is signalling failure at the
level the operating system understands, and letting a JSON payload override that signal would mean a
script's own stdout could talk its way out of a failure state the shell itself is reporting.

**How it works.**

```bash
# What the documentation's own illustrative example prints:
echo '{"hookSpecificOutput": {"permissionDecision": "allow"}}'
exit 2  # Still blocks.
```

The JSON is not discarded — it is still parsed, because exit `2` always attempts to parse stdout as
JSON to look for a reason to show the model. But `permissionDecision` specifically is not consulted
for the yes/no question; only `permissionDecisionReason` is read, and only to supply *why* the
already-decided block happened. If that field is absent, the block's reason falls back to whatever
the script wrote to stderr instead.

**Code.** The concrete way this actually happens in a real script — not a contrived one-liner — is
`format-on-edit.sh`, a `PreToolUse` hook on `Edit|Write` that rewrites the tool's input via
`updatedInput` (mechanism in the next leaf) and, as a defensive habit, wraps its own logic in
`set -e` plus an `ERR` trap that the author believed was "fail safe":

```bash
#!/usr/bin/env bash
set -e
trap 'exit 2' ERR

INPUT_JSON="$(cat)"
FILE_PATH="$(echo "$INPUT_JSON" | jq -r '.tool_input.file_path')"
CONTENT="$(echo "$INPUT_JSON" | jq -r '.tool_input.content')"

if [[ "$FILE_PATH" == *.java ]] && [[ "$CONTENT" != *$'\n' ]]; then
  NEW_CONTENT="${CONTENT}"$'\n'
  UPDATED_INPUT="$(jq -n --arg fp "$FILE_PATH" --arg c "$NEW_CONTENT" \
    '{file_path: $fp, content: $c}')"
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"updatedInput\":${UPDATED_INPUT}}}"
fi

# A courtesy check the author added later, unrelated to the trailing-newline fix above:
prettier --check "$FILE_PATH" >/dev/null 2>&1

exit 0
```

**Pitfall:** the author's belief in action: "`trap 'exit 2' ERR` is a conservative safety net — if
anything in my hook goes wrong, block the write rather than silently letting a broken hook wave
things through." The symptom: `prettier` is not installed on this machine (or the binary is not on
`PATH` in the sandboxed environment the hook runs in), `command -v` inside `prettier --check` fails
with exit `127`, the `ERR` trap fires, and the script exits `2` — **after** it already echoed
`permissionDecision: "allow"` with a correct `updatedInput`. Per §2.3.13's rule, that `2` wins: every
`.java` edit on this machine is now blocked, for a reason that has nothing to do with the trailing
newline the hook actually exists to fix, and the block reason shown to the model is whatever stderr
happened to contain from the trap, not "prettier is missing." The fix: never let `set -e` or an `ERR`
trap turn an unrelated, non-decision-bearing command into the process's exit code once the script has
already computed and printed its real decision — guard optional steps explicitly (`prettier --check
"$FILE_PATH" || true`) and only ever call `exit 2` from the line that intends to block. **Why people
believe it:** `set -e` and `trap ... ERR` are genuinely the right defensive posture for an ordinary
shell script that is not also acting as a decision channel; the mistake is porting that habit
unchanged into a script where the exit code has a second, load-bearing meaning that ordinary shell
scripts never have to think about.

**Interview:** "A hook prints `permissionDecision: allow` and then exits 2. What happens, and to
whom does the model attribute the block?" — it blocks; exit `2` cannot be overridden by JSON, and the
model is told the reason from `permissionDecisionReason` if present, otherwise from stderr — the
`allow` in the JSON body is simply never consulted once the exit code is `2`.

## §2.3.14 The JSON output contract, field by field

**Mental model.** Every field below lives inside one JSON object a hook prints to stdout. Most sit
under a `hookSpecificOutput` wrapper keyed to the firing event; a small number sit at the top level
and apply regardless of which event fired. Not every field means anything on every event — a field
an event does not honour is not an error to include, it is simply ignored, which is precisely why a
copy-pasted hook that "does nothing" on a new event is such a common, silent failure mode.

**How it works.** The complete structure, re-verified against `https://code.claude.com/docs/en/hooks`
on 2026-08-29:

**`[VERIFIED]`** re-fetched as raw markdown from `https://code.claude.com/docs/en/hooks.md` on
2026-08-30, the `## JSON output` section names exactly **three kinds of field**, quoted verbatim:
"Universal fields like `continue` are listed in the table below. Every event accepts them, but some
events discard them or deliver `systemMessage` somewhere other than the transcript." "Top-level
`decision` and `reason` are used by some events to block or provide feedback." "`hookSpecificOutput`
is a nested object for events that need richer control. It requires a `hookEventName` field set to
the event name." **Conflating these three kinds — treating a universal field as event-specific, or
nesting a top-level field under `hookSpecificOutput`, or vice versa — is the exact bug this leaf
exists to close off**, and an earlier pass of this table did exactly that: it nested `continue` and
`stopReason` inside `hookSpecificOutput` and described `continue` as the `Stop`/`SubagentStop`
mechanism. Both corrections are folded into the structure and table below.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "string",
    "decision": "allow",
    "additionalContext": "string",
    "updatedInput": { "file_path": "string", "content": "string" },
    "retry": true
  },
  "decision": "block",
  "reason": "string",
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "string",
  "stopReason": "string",
  "terminalSequence": "string"
}
```

The page's own two illustrative examples for `Stop`/`SubagentStop`, verbatim — note both are
top-level, with nothing nested under `hookSpecificOutput` except the `additionalContext` variant:

```json
{
  "decision": "block",
  "reason": "Must be provided when Claude is blocked from stopping"
}
```

```json
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "Please run the test suite before finishing"
  }
}
```

`[DOC]` Two fields on the full structure are not in this row's own leaf text and are added here
because the live page names them and the syllabus's field list omits them: **`stopReason`**
(**top-level, universal** — not nested under `hookSpecificOutput` as an earlier pass of this table
had it — shown to **the user**, not Claude, when the universal `continue` is `false`) and
**`suppressOutput`** (top level, honoured on most events, suppresses the hook's stdout from being
shown even where it otherwise would be). Conversely, nothing the syllabus names is missing from the
live page — the full field list below is a superset of, not a departure from, §2.3.14's own
enumeration.

**Group 1 — universal, top-level. Every event accepts these**, per the verified quote above, even
though some events discard them or route `systemMessage` somewhere other than the transcript:

| Field | Default | Honoured by | Values | What it changes |
|---|---|---|---|---|
| `continue` | `true` | all events | boolean | `false` stops Claude entirely after the hook runs, and **takes precedence over any event-specific decision field** — including a `Stop` hook's own `decision: "block"`. This is a kill switch, not the `Stop` mechanism |
| `stopReason` | none | all events, paired with `continue` | free text | message shown to **the user** when `continue` is `false`; not shown to Claude |
| `suppressOutput` | `false` | most events | boolean | has no effect: Claude Code accepts the field but doesn't act on it |
| `systemMessage` | none | most events | free text | warning message shown to the user |
| `terminalSequence` | none | all events | raw terminal escape sequence text | a side-effect channel (notifications, window title) that fires **even when the rest of the output is discarded** — the only field on this table with that property |

**Group 2 — top-level `decision` and `reason`. Used by `Stop` and `SubagentStop` to block or provide
feedback:**

| Field | Level | Honoured by | Values | What it changes |
|---|---|---|---|---|
| `decision` | top-level | `Stop`, `SubagentStop` | `"block"` (only defined value) | `"block"` prevents Claude from stopping; **omitting the field allows the stop** — there is no `"continue"` value |
| `reason` | top-level | `Stop`, `SubagentStop` | free text | **required when `decision` is `"block"`**; tells Claude why it should continue |

**Correction:** an earlier pass of this table placed a boolean `continue` inside this group as the
`Stop`/`SubagentStop` mechanism, with `continue: false` meaning "keep going." That was wrong on two
counts — the real field is `decision`/`reason` (Group 2), and `continue` is the unrelated universal
kill switch in Group 1, where `continue: false` means the opposite: stop everything.

**Group 3 — `hookSpecificOutput`, nested, keyed to the firing event. Requires `hookEventName`:**

| Field | Honoured by | Values | What it changes |
|---|---|---|---|
| `hookEventName` | all events | the firing event's name | informational only — does not itself change behaviour |
| `permissionDecision` | `PreToolUse`, `PermissionRequest` | `allow` \| `deny` \| `ask` | the tool call proceeds, is denied, or is escalated to a manual prompt |
| `permissionDecisionReason` | the same tool/permission events | free text | shown to the model as the reason for a `deny` or `ask`, and as the reason for an exit-`2` block if present |
| `decision` | `UserPromptExpansion` only | event-specific | **honoured by exactly one event at this nesting level** — a silent no-op anywhere else, including `PreToolUse`, where `permissionDecision` is the field that actually does the work. (Do not confuse this nested, `UserPromptExpansion`-only `decision` with the top-level `decision` in Group 2 — same name, different level, different events, different value set.) |
| `additionalContext` | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop` | free text | extra text appended to what the model sees, independent of allow/deny; on `Stop`/`SubagentStop` this is a **third path** distinct from `decision: "block"` — the conversation continues, but the transcript labels it `Stop hook feedback` rather than a hook error |
| `updatedInput` | `PreToolUse` only | an object matching the tool's own input schema | the harness runs the tool with **this** input instead of the one the model proposed |
| `retry` | `PermissionDenied` only | boolean | tells the model it may attempt the same tool call again; does not itself re-run anything |

A field honoured by exactly one event is the common source of a silent no-op: setting the nested
`decision` on a `PreToolUse` hook, expecting it to behave like `permissionDecision`, produces no error
and no effect — the field is simply not read by that event. The same trap applies across levels, not
just across events: a top-level `decision: "block"` on anything other than `Stop`/`SubagentStop` is
equally a silent no-op.

**The 10,000-character output cap.** `[VERIFIED]` (same 2026-08-30 fetch), quoted verbatim: "Hook
output strings, including `additionalContext`, `systemMessage`, and plain stdout, are capped at
10,000 characters. Output that exceeds this limit is saved to a file and replaced with a preview and
file path." Where several hooks return `additionalContext` for the same event, Claude receives all
the values; a value over the limit is written to a file in the session directory and Claude gets the
path plus a short preview instead of the raw text.

**`updatedInput` deserves more than a table row.** It is the mechanism, not `permissionDecision`,
that lets a hook *rewrite* a tool call rather than merely gate it — `format-on-edit.sh` above uses it
to inject a trailing newline into `content` before the `Write` or `Edit` actually executes, so the
model's own diff never shows the fix; the file simply arrives on disk already correct. It is scoped
to `PreToolUse` alone, for the obvious reason that every other blockable event fires either before
there is a tool input to rewrite (`UserPromptSubmit`) or after the tool has already run
(`PostToolUse`) — there is nothing left to substitute into. **Gotcha:** the replacement object must
match the shape the tool itself expects (a `Write` needs `file_path` and `content`; an `Edit` needs
`file_path`, `old_string`, and `new_string`), because the harness hands `updatedInput` straight to the
tool's own schema validation — a `content`-only object handed to `Edit` fails there, not inside the
hook.

**`retry` deserves the same treatment.** It exists on exactly one event, `PermissionDenied`, and it
does not resurrect the call automatically — it sets a flag the model reads, and the model then has to
decide to re-issue the same tool call as a fresh proposal, which re-enters `PreToolUse` from the top
exactly as if the model had thought of it unprompted. `block-destructive-bash.sh` can supply the
worked example, extended to react to the event it did not previously handle:

```bash
#!/usr/bin/env bash
set -e

INPUT_JSON="$(cat)"
EVENT="$(echo "$INPUT_JSON" | jq -r '.hook_event_name')"

if [ "$EVENT" = "PermissionDenied" ]; then
  DENIED_COMMAND="$(echo "$INPUT_JSON" | jq -r '.tool_input.command // ""')"
  if echo "$DENIED_COMMAND" | grep -Eq '(^|[[:space:]])rm([[:space:]]|$)' && \
     ! echo "$DENIED_COMMAND" | grep -Eq -- '-rf[[:space:]]+/'; then
    # Not the root-rooted case §2.3.12's script hard-blocks — worth letting the model try again
    # after it has had a chance to see the denial reason and adjust the command.
    echo '{"hookSpecificOutput":{"retry":true}}'
  fi
  exit 0
fi

COMMAND="$(echo "$INPUT_JSON" | jq -r '.tool_input.command // ""')"
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])rm[[:space:]]+-rf[[:space:]]+/'; then
  echo "block-destructive-bash.sh: refusing rm -rf against root-rooted path: $COMMAND" >&2
  exit 2
fi

exit 0
```

Branching on `hook_event_name` — the same discipline the previous file's gotcha demanded — is what
lets one script own both the `PreToolUse` denial and the `PermissionDenied` follow-up without
guessing which keys are present.

**§2.3.14's path resolution.** A hook's `command` is not necessarily resolved the way a shell alias
would be. `[DOC]` re-verified: three placeholders exist specifically so a hook command does not have
to know where it happens to be running — `${CLAUDE_PROJECT_DIR}` (the project root where the session
started), `${CLAUDE_PLUGIN_ROOT}` (the installation directory of the plugin that shipped the hook),
and `${CLAUDE_PLUGIN_DATA}` (a plugin's own persistent data directory, for state that must survive a
plugin update). All three are also exported into the hook's process environment, so a script can read
`$CLAUDE_PROJECT_DIR` directly rather than relying on the placeholder having been substituted into
its own command line.

Absent a placeholder, a **relative path is resolved from the current working directory the hook
process runs in** — not from the repository root, not from the hook script's own location — and a
**bare command name with no `/` in it** is resolved from `PATH`, exactly like typing that name at a
shell prompt. `**Insight:**` this is the seed of a failure this guide names but does not resolve
here: a hook shipped inside a plugin and written with a bare relative path (`./scripts/check.sh`
instead of `${CLAUDE_PLUGIN_ROOT}/scripts/check.sh`) resolves against wherever the *session* happens
to be running, which is essentially never the plugin's own installation directory — and a hook that
happens to work during local development, where the working directory and the plugin directory
coincide, fails the moment it runs from a different project. `[X-REF]` The full incident this seeds —
a plugin-shipped hook that worked in one repository and silently no-op'd in another — is worked
through without resolution here; see `plugins/05-cases-and-conversion.md`. One more wrinkle worth
carrying forward from the live page rather than assuming: `${CLAUDE_PROJECT_DIR}` **stays pinned to
the original project root and does not follow the session into a worktree**, while the `cwd` field on
every hook's own stdin payload *does* track the worktree — a hook that needs to know where Claude is
actually working right now reads `cwd` from its input, not the placeholder.

**Gotcha.** A `hooks.json` entry that supplies both a `command` string and an `args` array is parsed
in **exec form**: each placeholder is substituted as a literal string into `command` and into each
`args` element, with no shell involved at all, so quoting for spaces is unnecessary and, if added
anyway, becomes part of the literal argument. Omitting `args` switches to **shell form**, where the
`command` string is handed to `sh -c` (or PowerShell on Windows) and the shell itself expands the
placeholder — which is exactly the case where a bare `${CLAUDE_PROJECT_DIR}` should be wrapped in
double quotes, because an unquoted path containing a space will otherwise be split into two
arguments by the shell.

> The JSON output contract has three kinds of field: universal top-level fields every event accepts
> (`continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`), top-level
> `decision`/`reason` used by `Stop`/`SubagentStop` to block or provide feedback, and fields nested
> under `hookSpecificOutput` keyed to the firing event. A field set on an event that does not read it
> is not an error, it is silently discarded, and `updatedInput` and `retry` are the two nested fields
> that change control flow rather than merely a yes/no outcome. `continue: false` is the one field
> that overrides everything else on the list, regardless of level or event.

## Pitfalls

- **Belief:** "A `Stop` hook keeps Claude working by returning `continue: true`, or a field named
  `continueReason`." **Symptom:** the hook prints one of those, exits `0`, and Claude stops anyway —
  no error, no signal anything was wrong, because neither field means what its name suggests on this
  event. **Fix:** to keep Claude working past a `Stop`/`SubagentStop` event, **block the stop**:
  `{"decision": "block", "reason": "..."}`. `reason` is required whenever `decision` is `"block"`.
  There is no `continueReason` field and no `decision: "continue"` value anywhere in the schema; the
  boolean `continue` is a separate, universal kill switch where `false` — not `true` — is the value
  that does something, and it stops Claude entirely rather than keeping it going. **Why people
  believe it:** "continue" reads as the intuitive opposite of "stop," and three independent readings
  of this exact table made the same inversion before the raw docs page was fetched and quoted
  directly (verified 2026-08-30) — an earlier version of this note repeated the error.
- **Belief:** "`set -e` plus a top-level `trap 'exit 2' ERR` is the conservative, fail-safe posture
  for a hook that also prints JSON." **Symptom:** an unrelated, non-decision-bearing command later in
  the same script (a missing `prettier` binary, a flaky network call) fails, the trap fires, the
  script exits `2`, and every subsequent call this hook is attached to is blocked for a reason that
  has nothing to do with the decision the script already computed and printed. **Fix:** guard
  optional or unrelated commands explicitly (`command || true`), and reserve `exit 2` for the one
  line in the script that is actually making the blocking decision. **Why people believe it:**
  `set -e`/`trap ERR` genuinely is the right posture for an ordinary shell script with no second
  meaning attached to its exit code; the failure mode only appears once the exit code is also a
  decision channel, which most shell-scripting habits never have to account for.
- **Belief:** "Exit code 1 means the hook failed, so it should block just like exit 2 does."
  **Symptom:** a script that treats any nonzero code as equivalent to `2` — for example by writing
  `some_check || exit 1` where the intent was "block if this check fails" — lets the tool call
  through anyway, because `1` is non-blocking on this contract regardless of intent. **Fix:** the
  blocking code is `2`, and only `2`, on every event except the two named exceptions
  (`WorktreeCreate`'s any-nonzero-blocks rule, and `PreModelSwitch`'s timeout rule); write `exit 2`
  explicitly wherever the intent is "stop this." **Why people believe it:** ordinary Unix convention
  reads any nonzero exit as failure, and this contract deliberately narrows "failure that blocks" to
  one specific value.
- **Belief:** "Setting `decision` in a hook's JSON output will gate a `PreToolUse` call the same way
  `permissionDecision` does." **Symptom:** the hook runs, prints valid JSON, exits `0` — and the tool
  call proceeds exactly as if the hook had done nothing, with no error surfaced anywhere. **Fix:**
  `decision` is honoured by `UserPromptExpansion` alone; a `PreToolUse` hook must set
  `permissionDecision`. **Why people believe it:** the two field names are close enough in spelling
  and intent that a hook author reasonably assumes they are interchangeable aliases rather than two
  fields scoped to two entirely different events.

## Cheat sheet

| Item | Value |
|---|---|
| Blocking exit code | `2`, and only `2`, except `WorktreeCreate` (any nonzero) and a timed-out `PreModelSwitch` |
| Exit `1` | non-blocking, same as any other non-`2` code — not the blocking code, despite Unix convention |
| Exit `2` vs JSON `permissionDecision: allow` | exit `2` wins unconditionally; the JSON supplies only the reason text if present |
| Stdout shown to the model on exit `0` | only on `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, `PostModelSwitch` — everywhere else, debug log only |
| `updatedInput` | `PreToolUse` only; rewrites the tool's input before it runs; must match that tool's own input schema |
| `retry` | `PermissionDenied` only; tells the model it may retry — does not re-run the call itself |
| `decision` vs `permissionDecision` | `decision` → `UserPromptExpansion` only; `permissionDecision` → `PreToolUse`/`PermissionRequest` |
| Path resolution, no placeholder | relative → resolved from the hook process's cwd; bare name → resolved from `PATH` |
| `${CLAUDE_PROJECT_DIR}` under a worktree | stays pinned to the original project root; use `cwd` from the payload for the live location |
| Extra fields the syllabus's own list omitted | `stopReason` (universal top-level, shown to the user), `suppressOutput` (top-level) |
| Keep a `Stop`/`SubagentStop` turn open | top-level `decision: "block"` + required `reason` — omit `decision` to allow the stop |
| Universal kill switch, every event | `continue: false` (top-level) — overrides any event-specific decision, including `decision: "block"`; pairs with `stopReason` (shown to the user, not Claude) |

## Self-test

1. A hook exits `2` after printing `{"hookSpecificOutput":{"permissionDecision":"allow"}}`. What
   happens?
   <details><summary>Answer</summary>The call is blocked. Exit `2` cannot be overridden by JSON;
   `permissionDecision: "allow"` is not consulted for the yes/no outcome once the exit code is `2` —
   only `permissionDecisionReason`, if present, is read, to supply the reason shown for the block.</details>
2. Does exit code `1` block a tool call the way exit code `2` does?
   <details><summary>Answer</summary>No. Exit `1` is non-blocking, identical in effect to any other
   non-`2` code, except on `WorktreeCreate` (any nonzero blocks) and a timed-out `PreModelSwitch`
   hook.</details>
3. On which events is exit-`0` stdout shown to the model rather than only written to the debug log?
   <details><summary>Answer</summary>`UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, and
   `PostModelSwitch` — four events, one more than this topic's own syllabus names.</details>
4. Which field lets a `PreToolUse` hook change the arguments a tool call actually runs with, and what
   must the replacement value match?
   <details><summary>Answer</summary>`updatedInput`, honoured only on `PreToolUse`; the replacement
   object must match the shape the tool's own input schema expects (e.g. `file_path`/`content` for
   `Write`), because the harness passes it straight into that tool's own validation.</details>
5. Does setting `retry: true` on a `PermissionDenied` hook automatically re-run the denied tool call?
   <details><summary>Answer</summary>No. It only tells the model it may attempt the call again; the
   model has to decide to re-issue it, which then re-enters `PreToolUse` from the top as a fresh
   proposal.</details>
6. Why does setting `decision` instead of `permissionDecision` on a `PreToolUse` hook silently do
   nothing?
   <details><summary>Answer</summary>`decision` is honoured only by `UserPromptExpansion`. A field
   set on an event that does not read it is not an error — it is discarded without any signal that
   anything went wrong.</details>
7. A relative hook command path with no placeholder — what is it resolved against?
   <details><summary>Answer</summary>The current working directory the hook process runs in, not the
   repository root and not the hook script's own file location. A bare name with no `/` is instead
   resolved from `PATH`.</details>
8. Under a worktree, does `${CLAUDE_PROJECT_DIR}` track the worktree's path or the original project
   root — and what should a hook read instead if it needs the live location?
   <details><summary>Answer</summary>It stays pinned to the original project root and does not follow
   into the worktree. A hook that needs Claude's current working directory should read the `cwd`
   field from its own stdin payload instead, which does track the worktree.</details>
9. What is the practical failure mode of wrapping a JSON-emitting hook in `set -e` plus
   `trap 'exit 2' ERR`?
   <details><summary>Answer</summary>Any unrelated command later in the script that fails for a
   reason unconnected to the actual decision (a missing binary, a network blip) triggers the trap and
   exits `2`, which blocks the call and overrides whatever correct JSON decision the script had
   already printed — the fix is to guard unrelated commands explicitly rather than let a shared trap
   turn every failure into a block.</details>

## Open questions

**Unverified:** whether `Stop`'s stdin payload carries a separately named `stop_reason` field
distinct from `last_assistant_message`, as this row's leaf 2.3.11 states — the live page's per-event
`Stop` input schema section did not render in this session's fetches. Settle by reading the `Stop`
event's own input-schema subsection of `https://code.claude.com/docs/en/hooks` directly.

**Unverified:** the exact field name `UserPromptSubmit` uses to carry the user's typed text (this
leaf's wording assumes `user_input`) — not independently confirmed against the rendered page in this
session.

**Unverified:** the exact field names `FileChanged`'s payload carries (this leaf's wording assumes
`file_path` and `change_type`) — not independently confirmed against the rendered page in this
session; file 02 confirms only that its `matcher` targets "literal filenames."

**Unverified:** the shape of `PermissionRequest`'s separately documented `decision` object (referenced
by the live page as distinct from `permissionDecision`, under a "PermissionRequest decision control"
subsection that did not render in this session's fetches) — carried over from the previous file's own
open question, still unresolved here.

---

**Leaves covered:** 2.3.10–2.3.14 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-52
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 569
