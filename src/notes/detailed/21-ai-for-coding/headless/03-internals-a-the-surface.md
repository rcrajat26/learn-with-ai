# 21 AI for Coding — the headless surface — ADVANCED (INTERNALS) (§3.6.1–3.6.5)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [effort, models and routing](../effort-and-routing/03-internals-routing.md) · Next: [formats, sessions and background execution](03-internals-b-formats-and-execution.md)

Every prior file in Part 3 treated Claude Code as something a person drives — a terminal session with
a trust dialog, a permission prompt, a slash command typed at a keyboard. `[ZERO]` **Headless mode**
is the same binary run a second way: no terminal to prompt, no keyboard to wait on, one process
invocation that takes a task and returns an answer a *program* can read. `-p` (its long form
`--print`) is the flag that switches it on. This is the seam PART 4 is built on — every wrapper, every
CI job, every orchestrator that calls Claude Code programmatically calls it through this surface, and
nothing else. This file covers the five leaves that define the contract: the invocation itself, the
three output and two input formats it can be wired with, the JSON envelope's fields with a real one
quoted in full, the streaming flags that trade simplicity for liveness, and `--json-schema`, the
difference between parsing prose and receiving data.

### 1. `claude -p` — one prompt in, one envelope out

**Mental model.** An interactive `claude` session is a conversation: the process stays alive, waits at
a prompt, and the human decides when it is done. `claude -p "<task>"` is a **function call** dressed
as a CLI invocation — the process starts, does the task, prints one result, and exits. Nothing waits
on a human, because there is no human in the loop by design.

**Why it exists.** A CI job, a pre-commit hook, a scheduled job, or another program cannot "sit at a
terminal and wait for a prompt" — it needs a call it can make, a return value it can inspect, and an
exit code it can branch on. Before `-p`, the only way to drive Claude Code from another process was to
script a pseudo-terminal around the interactive UI, parsing rendered output meant for a human. `-p`
removes the human from the contract entirely: input arrives as an argument (or on stdin), output
arrives as a value, and the process's exit status is the same signal any other CLI tool gives a
caller.

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30, quoted exactly:

> `--print`, `-p` — Print response without interactive mode (see [Agent SDK documentation] for
> programmatic usage details)
>
> Example: `claude -p "query"`

Bare `claude -p "query"` still does everything an interactive turn does internally — it reads
settings, evaluates permissions, may call tools, may spawn subagents — the only thing missing is the
part aimed at a human: no trust dialog, no permission-prompt UI, no rendered transcript. That absence
is not cosmetic; §1.4.34 of `permissions/06-directories-and-trust.md` establishes that a `-p` (or SDK)
session **never shows the trust dialog**, and for an *untrusted* folder's committed
`permissions.allow` rules and `additionalDirectories`, the documented behavior is not "runs them
anyway" but the opposite: those rules go unused and Claude Code prints a `this workspace has not been
trusted` warning to stderr instead. **Insight:** the intuitive fear about headless mode — "a CI job on
a fresh, untrusted checkout will silently inherit whatever `allow` rules are committed to the repo" —
is backwards for a first-ever run in a path nobody has trusted; the safer, more restrictive rule
applies precisely because there is no dialog to have skipped past. The narrower "counts as accepted"
phrasing that *does* apply to `-p`/SDK governs a different, internal check (whether
`.claude/settings.local.json` is git-tracked), not the general untrusted-folder case — see that file
for the corrected form; this row exists to warn a reader wiring `-p` into a pipeline not to assume
either direction without reading the actual stderr output.

**Code.** The minimal, complete invocation this file's later leaves build on:

```bash
claude -p "Summarize what changed in the last commit and flag anything that looks unsafe to merge." \
  --output-format json
```

No interactive UI opens. Stdout carries exactly one JSON object (§3 below); stderr carries warnings,
including the trust warning above if the working directory is untrusted; the process exit code is
non-zero on internal failure (a crash, a bad flag) and zero on a completed run regardless of whether
the *task itself* succeeded — that distinction is `is_error` inside the envelope, not the process exit
code, and is exactly why §3 matters: a caller that only checks `$?` will treat a task that failed
gracefully as a success.

**Gotcha.** `[TRAP]` **Pitfall:** treating `-p`'s exit code as the task's success/failure signal. The
symptom: a CI script that does `claude -p "run the migration" --output-format json; if [ $? -eq 0 ];
then echo ok; fi` reports "ok" even when the model's own answer says the migration failed, because the
process itself exited cleanly — it printed a well-formed envelope, and printing an envelope is not the
same claim as the task succeeding. The fix: parse the envelope and branch on `is_error` and
`subtype`, not on the shell's `$?`. **Why people believe it:** every other CLI tool a backend engineer
has scripted around uses exit code as the pass/fail signal, and `-p` looks like an ordinary CLI tool
from the outside.

> `claude -p "<task>"` runs one task to completion with no interactive UI and exits, printing a single
> result Claude Code intends a program, not a person, to read.

### 2. The three output formats and two input formats — table, then the choice criterion

**Mental model.** `--output-format` is not a formatting preference, it is a decision about **when** the
caller gets data and **how much parsing** it has to do to get it; `--input-format` is the mirror
decision for what a caller can *send*, not just receive. Both exist because a "CI job that wants one
answer at the end" and "a live UI that wants to show progress as it happens" are different consumers
with genuinely different requirements, not the same consumer with a style preference.

**Why it exists.** Plain text on stdout is enough for a human piping `-p` output into `less`. It is not
enough for a program that needs to know *whether the run succeeded*, *what it cost*, or *which session
to resume* — none of that fits in a bare result string, so `json` exists to carry it. `json` in turn
withholds everything until the run is completely finished, which is wrong for a caller that wants to
show the user something *while* the model is still working — so `stream-json` exists as a third option
that trades a harder parsing job (one JSON object per line, arriving throughout the run) for liveness.
The input side has the same split for the opposite direction: a single string is enough to *start* a
task, but a wrapper driving a multi-turn agent loop needs to inject prior turns and tool results, which
a bare string cannot represent.

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30:

| Output format | What it emits | When the caller gets it | Parseable incrementally? | Pick this for |
|---|---|---|---|---|
| `text` | Plain result string on stdout | Once, at process exit | No — it is not structured at all | A human reading a terminal; never a wrapper, because there is no `is_error`, `session_id`, cost, or usage to act on |
| `json` | One JSON object (the full envelope, §3) | Once, after the run completes | No — the object is only valid once fully written | A CI job: it needs one pass/fail verdict and one cost figure per run, and can afford to wait for the whole thing |
| `stream-json` | One JSON object per line as the run progresses (tool calls, partial text, then the final envelope as the last line) | Continuously, throughout the run | Yes — each line is a complete, independently-parseable JSON value | A live progress feed: a UI that must show the user something is happening before the model finishes |

| Input format | What a caller sends | Can it carry prior turns / tool results mid-stream? | Pick this for |
|---|---|---|---|
| `text` | One prompt string, piped or given as an argument | No | A one-shot task with no need to feed anything back in after the process starts |
| `stream-json` | A sequence of message objects on stdin, including `tool_result` blocks | Yes | A wrapper driving a multi-turn agent loop that must inject tool results or additional turns while the process is running (`--input-format stream-json`, combinable with `--output-format stream-json` for a fully bidirectional pipe) |

`[DOC]` Exact flag text, re-verified against `cli-reference`, 2026-08-30:

> `--output-format` — Specify output format for print mode (options: `text`, `json`, `stream-json`)
>
> `--input-format` — Specify input format for print mode (options: `text`, `stream-json`)

![D-80 — The `-p --output-format json` envelope, field by field, and what each field is for downstream.](../diagrams/D-80-cli-json-envelope-fields.svg)

**D-80** — The `-p --output-format json` envelope, field by field, and what each field is for
downstream: billing, audit, retry classification, continuation. The panel on the right of D-80 is
this table's `json` and `stream-json` rows drawn side by side; its bottom panel is this file's
input-format row.

**Code.** The CI-versus-live-feed choice, made concrete:

```bash
# CI job: one verdict, one cost figure, wait for it
claude -p "Run the test suite and report failures." --output-format json > result.json
jq '.is_error, .total_cost_usd' result.json

# Live progress feed: a UI process reading lines as they arrive
claude -p --output-format stream-json --verbose --include-partial-messages \
  "Refactor the connection pool for correctness." | while read -r line; do
    echo "$line" | jq -c '.type'
  done
```

**Gotcha.** No gotcha beyond the parsing-cost tradeoff already stated in the table: `stream-json` is
strictly more capable than `json` for a caller that wants both liveness and a final verdict (the last
line of a `stream-json` stream *is* the same envelope `json` alone would have printed), but every line
before it has to be parsed and discarded or handled, which is real complexity a `json`-only caller
does not carry. Choosing `stream-json` for a plain CI job is not wrong, only unnecessary.

> `--output-format` chooses when a caller learns the result (`text`/`json` only at the end,
> `stream-json` throughout) and `--input-format` chooses what a caller can send while the process runs
> (`text` once, `stream-json` a sequence including tool results) — a CI job wants the first pair's
> `json`, a live UI or a multi-turn wrapper wants the second pair's `stream-json`.

### 3. The JSON envelope's fields, and a real one

**Mental model.** The `json`-format envelope is not a log of what happened, it is an **interface
contract**: a fixed shape a caller is entitled to depend on, distinct from the extra fields a given
release happens to also include. Reading it as a contract means asking, for every field, three
questions: is it documented and therefore stable, does it appear in every format, and what would a
caller actually do with it.

**Why it exists.** `cost-model/03-internals-a-the-four-quantities.md` already worked the billing angle
of this same envelope in full, and it stays load-bearing rather than being re-derived here — this
leaf's question is different: **what can a caller build against**, not what the numbers cost. A
wrapper deciding whether to retry, whether to resume a session, or how to attribute spend to a team
needs specific, named fields to read, not "the JSON that came back."

**How it works.** `[DOC]` The fields this leaf owns, re-verified against `cli-reference`, 2026-08-30,
with the downstream use each one is named for on D-80:

| Field | Downstream use |
|---|---|
| `result` | The task's answer text — fed back as the next turn's input in a multi-call wrapper, or shown to a human |
| `is_error` | Retry classification — the branch point between "the task itself failed" and "the process failed," which the shell exit code does not distinguish (§1's gotcha) |
| `session_id` | Continuation — the argument to `--resume`/`-r` to pick the same conversation back up in a later `-p` call |
| `total_cost_usd` | Billing rollup — per-run spend, already summed across every model the run touched (§2 of the cost-model file shows this summation is not a single model's `costUSD` alone) |
| `usage.*` (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) | Token accounting and cache-hit efficiency — the four billed quantities, at the per-run granularity |
| `duration_ms` / `duration_api_ms` | Audit and latency/SLA tracing |

`[PROVE]` This is not a constructed example. It is the complete, unedited `--output-format json`
result of a real `claude -p` call made while writing this file, against `claude-opus-5[1m]`, on
Claude Code v2.1.251:

```json
{
  "duration_api_ms": 14217,
  "stop_reason": "end_turn",
  "session_id": "b495440a-5f00-4ed1-80b5-8eb682ca0505",
  "total_cost_usd": 0.22098275,
  "usage": {
    "input_tokens": 6,
    "cache_creation_input_tokens": 28249,
    "cache_read_input_tokens": 55515,
    "output_tokens": 627,
    "output_tokens_details": { "thinking_tokens": 195 },
    "server_tool_use": { "web_search_requests": 0, "web_fetch_requests": 0 },
    "service_tier": "standard",
    "cache_creation": { "ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 28249 },
    "inference_geo": "global",
    "iterations": [
      {
        "input_tokens": 2, "output_tokens": 243,
        "cache_read_input_tokens": 28030, "cache_creation_input_tokens": 219,
        "cache_creation": { "ephemeral_5m_input_tokens": 219, "ephemeral_1h_input_tokens": 0 },
        "type": "message"
      }
    ],
    "speed": "standard"
  },
  "modelUsage": {
    "claude-haiku-4-5-20251001": {
      "inputTokens": 904, "outputTokens": 12,
      "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0,
      "webSearchRequests": 0, "costUSD": 0.000964,
      "contextWindow": 200000, "maxOutputTokens": 32000,
      "canonicalModel": "claude-haiku-4-5", "provider": "firstParty", "costBasis": "list"
    },
    "claude-opus-5[1m]": {
      "inputTokens": 6, "outputTokens": 627,
      "cacheReadInputTokens": 55515, "cacheCreationInputTokens": 28249,
      "webSearchRequests": 0, "costUSD": 0.22001875,
      "contextWindow": 1000000, "maxOutputTokens": 64000,
      "canonicalModel": "claude-opus-5", "provider": "firstParty", "costBasis": "list"
    }
  },
  "permission_denials": [
    {
      "tool_name": "Skill", "tool_use_id": "toolu_01MFQM4BCNwuWWxvG4K4FFbF",
      "tool_input": { "skill": "claude-api", "args": "prompt caching purpose" }
    }
  ],
  "terminal_reason": "completed",
  "fast_mode_state": "off",
  "fast_mode_disabled_reason": "sdk_opt_in_required",
  "subagent_stats": {
    "spawned": 0, "requested": { "background": 0, "foreground": 0, "unset": 0 },
    "started_in_background": 0, "max_depth": 0, "spawned_by_subagents": 0,
    "completed": 0, "failed": 0,
    "killed": { "parent": 0, "user": 0, "system": 0 },
    "refused": { "depth_limit": 0, "concurrency_limit": 0, "budget": 0 },
    "by_type": {}
  },
  "is_error": false,
  "num_turns": 3,
  "subtype": "success",
  "api_error_status": null,
  "result": "Prompt caching lets you mark a stable prefix of your prompt (system instructions, tool definitions, long documents) so the API reuses that already-processed context across requests — cutting latency and cost on the cached portion instead of re-reading the same tokens every call.\n\nNote: the `claude-api` skill failed to load...",
  "ttft_ms": 3978,
  "type": "result",
  "duration_ms": 18332,
  "uuid": "ecec79c9-49b7-426b-84a0-f008af33d7af",
  "ttft_stream_ms": 1838,
  "time_to_request_ms": 131,
  "queued_turn_count": 0
}
```

**Insight:** this real envelope is the argument for reading it as a *contract*, not a *dump*. Roughly
half the top-level keys — `permission_denials`, `fast_mode_state`, `subagent_stats`, `ttft_ms`,
`iterations`, `queued_turn_count` — are not in the field list `cli-reference` documents for this row,
and a caller that hard-codes an exact expected key set will break the moment a future release adds or
removes one of these. The six fields in this leaf's table are the ones a caller may rely on across
versions; everything else is diagnostic bonus, present because this particular run happened to deny a
`Skill` tool call and spawn a Haiku subcall, not because the envelope guarantees those keys exist on
every run.

**Gotcha.** `[TRAP]` **Pitfall:** assuming the envelope's shape is identical across `--output-format`
values. The symptom: code that does `jq '.total_cost_usd'` against `text`-format output gets nothing —
`text` mode never emits `total_cost_usd`, `session_id`, or `usage` at all (§2's table), so a caller
that switches output formats for a "quick check" silently loses every field this leaf's table promises.
The fix: any caller that reads `is_error`, `session_id`, cost, or usage must run `--output-format
json` or `stream-json`, never `text` — the fields are a property of the format, not of the task.
**Why people believe it:** `-p "task"` with no `--output-format` flag at all still runs and prints
something, so it looks interchangeable with the flagged forms until the parsing code reaches for a
field that was never there.

> The `json` envelope is a versioned interface contract, not a log — `result`, `is_error`,
> `session_id`, `total_cost_usd`, `usage.*`, and `duration_ms` are the fields a caller may build
> against; every other key present in a given release is diagnostic bonus, absent from `text` output
> entirely, and not guaranteed to persist.

### 4. `stream-json` extras — when streaming earns its complexity

**Mental model.** `stream-json` alone gives a caller *that something is happening*; the four flags in
this leaf are the difference between "a heartbeat" and "a transcript" — each one turns on one more
category of internal event the base stream would otherwise omit.

**Why it exists.** A bare `stream-json` output already contains tool calls and their results. That is
enough to show *that* work is happening, but not enough to show *what the model is thinking while
writing its reply*, *what a subagent said*, *what a hook did*, or *whether the harness is echoing back
what it received* — each of those is a separate concern a caller may or may not want, so each is its
own flag rather than one all-or-nothing verbosity switch.

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30:

| Flag | What it adds to the stream | Requires |
|---|---|---|
| `--include-partial-messages` | Partial streaming events — the model's reply text as it is generated, not only once complete | `--print` and `--output-format stream-json` |
| `--include-hook-events` | Hook lifecycle events in the stream. `SessionStart` and `Setup` are always included regardless of this flag; some events (`Notification`, `SessionEnd`, `PreCompact`, `PostCompact`) never produce a `hook_started` event even with it — Claude Code instead emits `hook_progress` while a slow command hook is producing output, and `hook_response` only when a background hook finishes | `--output-format stream-json` |
| `--forward-subagent-text` | `[VERSION]` Subagent text and thinking blocks as `assistant`/`user` messages carrying `parent_tool_use_id`, so a caller can reconstruct each subagent's transcript rather than seeing only its `tool_use`/`tool_result` pair. Nested-subagent forwarding (setting `parent_tool_use_id` to the spawning Agent call's ID) requires v2.1.219+; the flag itself requires v2.1.211+ | `--print` and `--output-format stream-json` |
| `--replay-user-messages` | Re-emits stdin user messages back on stdout, for acknowledgment that the harness received them | `--input-format stream-json` and `--output-format stream-json` |

**Code.** A wrapper that wants a full subagent transcript plus hook visibility, matching D-80's
"parseable incrementally" claim line by line:

```bash
claude -p --output-format stream-json --verbose \
  --include-partial-messages --include-hook-events --forward-subagent-text \
  "Have a subagent audit the connection-pool changes for a resource leak, then summarize the finding."
```

Each line of stdout is now one independently-parseable JSON object; a caller reading with `jq -c
'select(.type=="assistant" and .parent_tool_use_id != null)'` isolates exactly the subagent's own
turns from the parent's, which the base `stream-json` stream (no extra flags) would not distinguish
from an ordinary tool result.

**Gotcha.** `[TRAP]` **Pitfall:** turning on every one of these flags by default "to be safe." The
symptom: a caller now has to handle several new event shapes it never asked for — hook lifecycle
events that never resolve to `hook_started` for some hook types, subagent messages carrying a
`parent_tool_use_id` the parsing code was not written to expect — for a workflow that only needed the
final answer. The fix: add each flag only when its specific downstream need exists (a UI that shows
subagent progress needs `--forward-subagent-text`; one that reports hook side effects needs
`--include-hook-events`; neither needs both). **Why people believe it:** each flag reads as strictly
additive ("more events can't hurt"), but more events is more parsing surface, and parsing surface a
caller does not act on is a caller now silently swallowing or mishandling events it does not
recognize.

> Each `stream-json` extra flag turns on one category of internal event the base stream omits —
> partial text, hook lifecycle, subagent transcripts, or replayed input — and each is worth its
> parsing cost only when the caller has a specific, named use for that category, not by default.

### 5. `--json-schema` — the difference between parsing prose and receiving data

**Mental model.** Every format in §2 still hands a caller a `result` field that is *prose* — text a
model wrote, however well-structured. `--json-schema` changes what `result` (functionally) is: instead
of a string the caller must parse with its own regex or a second LLM call, the caller gets a value
already validated against a schema it supplied, so "did the model return well-formed data" stops being
the caller's problem to solve after the fact.

**Why it exists.** A wrapper that needs a specific shape back — a list of file paths, a severity
enum, a structured diff summary — has historically had two bad options: ask the model to "return
JSON" in the prompt and hope it complies exactly, or run a second pass just to coerce free text into a
shape. `--json-schema` moves the validation into the harness itself, so a caller either gets a value
matching the schema or a hard failure, never a plausible-looking string that turns out subtly
malformed three fields in.

**How it works.** `[DOC]` `[VERSION]` Re-verified against `cli-reference`, 2026-08-30, quoted exactly:

> `--json-schema` — Get validated JSON output matching a JSON Schema after the agent completes its
> workflow (print mode only)... Claude Code exits with an error on an invalid schema and accepts the
> `format` keyword as an annotation without client-side validation

**Unverified:** the documented flag entry carries no minimum Claude Code version for `--json-schema`
itself (unlike `--forward-subagent-text`'s explicit v2.1.211 floor in §4) — treat it as available
across the v2.1.2xx line this guide targets, and re-check `cli-reference` before relying on it against
an older installation. Two structural facts the quoted text states directly: first, this is **print
mode only** — it composes with `-p`, not with an interactive session, which fits the same headless
seam every other leaf in this file lives on. Second, the `format` keyword (a JSON Schema annotation
such as `"format": "date-time"`) is accepted but **not validated** client-side — the schema's shape is
enforced, an annotation inside it is not, which matters for a caller that assumed `format: "email"`
in a schema was a guarantee rather than a hint.

**Code.** A schema-validated call, contrasted with what §2's plain `json` format would have returned
for the same task:

```bash
claude -p "List every public method added to ConnectionPool in the last commit, with a one-line risk note for each." \
  --output-format json \
  --json-schema '{
    "type": "object",
    "properties": {
      "methods": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "risk": { "type": "string", "enum": ["low", "medium", "high"] }
          },
          "required": ["name", "risk"]
        }
      }
    },
    "required": ["methods"]
  }'
```

Without `--json-schema`, the envelope's `result` field is prose the caller would have to parse itself
("`acquire()` looks medium-risk because…") — brittle against a model that phrases the same fact two
different ways on two different runs. With it, `result` is a JSON value already checked against the
`methods` array's shape; a run that cannot produce a conforming value exits with an error instead of
returning something that merely looks parseable.

**Gotcha.** `[TRAP]` **Pitfall:** believing a schema field marked `"format": "email"` (or any other
JSON Schema `format` annotation) is enforced the same way `"type"` and `"enum"` are. The symptom: a
caller ships a schema expecting malformed-looking values to be rejected outright, then finds a value
that violates the `format` hint slipping through as "valid," because the documented behavior is that
`format` is accepted as an annotation *without client-side validation* — only the structural
constraints (`type`, `required`, `enum`, and similar) are actually enforced. The fix: put anything
that must be strictly guaranteed into `enum` or a stricter `type`/`pattern` constraint rather than a
`format` annotation, and treat `format` as documentation for a human reading the schema, not a runtime
check. **Why people believe it:** in most JSON Schema tooling outside this specific flag, `format`
validators are common and the keyword *looks* like every other constraint in the same object.

> `--json-schema` turns the envelope's `result` field from prose a caller must parse into a value
> already validated against a caller-supplied schema — enforced for structural keywords, accepted but
> not enforced for `format` annotations, print-mode only, and exiting with an error rather than
> returning a non-conforming value.

## Pitfalls

- **Belief in action:** a `-p` run's exit code tells the caller whether the task succeeded.
  **Surprising outcome:** the process can exit `0` while the envelope's own `is_error` is `true`,
  because a completed, well-formed run and a successful task are two different claims. **What
  actually gets the guarantee:** parse the envelope and branch on `is_error`/`subtype`, never on `$?`
  alone. **Why people believe it:** every other scripted CLI tool uses exit code as the pass/fail
  signal.
- **Belief in action:** the `json` envelope's field set is identical regardless of `--output-format`.
  **Surprising outcome:** `text` mode never emits `total_cost_usd`, `session_id`, or `usage` at all —
  switching formats for "a quick check" silently drops every field a wrapper depends on. **What
  actually gets the guarantee:** always use `--output-format json` or `stream-json` when any of those
  fields are needed. **Why people believe it:** `-p "task"` runs and prints *something* in every
  format, so the formats look interchangeable until a specific field goes missing.
- **Belief in action:** a fresh, untrusted checkout run with `claude -p "run the tests"` silently
  inherits the repository's committed `permissions.allow` rules because "`-p` counts as accepted."
  **Surprising outcome:** for that general case the documented behavior is the opposite — those rules
  go unused and a `this workspace has not been trusted` warning prints to stderr; "counts as accepted"
  governs a narrower, different internal check (§1). **What actually gets the guarantee:** read the
  actual stderr output of a first `-p` run in a new checkout rather than assuming either direction.
  **Why people believe it:** the same page's language about `-p`/SDK "counting as accepted" is real,
  just scoped to a different question than "do committed `allow` rules apply."

## Cheat sheet

| Item | Answer |
|---|---|
| Turn on headless mode | `-p` / `--print` |
| Get one final answer, once, machine-readable | `--output-format json` |
| Get liveness while the run progresses | `--output-format stream-json` |
| Send prior turns / tool results while running | `--input-format stream-json` |
| Envelope fields a caller may rely on | `result`, `is_error`, `session_id`, `total_cost_usd`, `usage.*`, `duration_ms` |
| Show model text as it streams | `--include-partial-messages` (needs `stream-json`) |
| Show hook lifecycle in the stream | `--include-hook-events` (needs `stream-json`) |
| Reconstruct a subagent's own transcript | `--forward-subagent-text`, v2.1.211+ (nested subagents v2.1.219+) |
| Echo received stdin messages back | `--replay-user-messages` (needs `stream-json` both ways) |
| Get schema-validated data instead of prose | `--json-schema '<schema>'` — print mode only, `format` unenforced |
| Untrusted folder + `-p` + committed `allow` rules | Not used; stderr warning instead |

## Self-test

1. Why is `claude -p`'s process exit code not a reliable success/failure signal on its own?
<details><summary>Answer</summary>Exit code 0 means the process ran to completion and printed a well-formed result — it says nothing about whether the task itself succeeded. A task that failed gracefully still produces a complete envelope and a clean exit; the actual pass/fail signal is the envelope's own `is_error` field (and `subtype`), which the shell's `$?` cannot see.</details>

2. A caller pipes `claude -p "task" --output-format text` into `jq '.total_cost_usd'` and gets nothing. Why, and what should it have done instead?
<details><summary>Answer</summary>`text` output format is a plain result string with no `total_cost_usd`, `session_id`, or `usage` fields at all — those only exist in `json` and `stream-json` output. The caller should have used `--output-format json` (or `stream-json`) to get the structured envelope those fields live in.</details>

3. Name the one structural difference between `json` and `stream-json` that makes `stream-json` viable for a live progress UI.
<details><summary>Answer</summary>`json` emits a single object only after the entire run completes, so nothing is available until the end. `stream-json` emits one complete, independently-parseable JSON object per line throughout the run — tool calls, partial text, then the final envelope as the last line — so a UI can read and display each line as it arrives.</details>

4. A wrapper needs to reconstruct exactly what a subagent said, not just its tool calls. Which flag, and what does it set on each forwarded message that a base `stream-json` stream would not include?
<details><summary>Answer</summary>`--forward-subagent-text` (requires `--print` and `--output-format stream-json`, v2.1.211+). It forwards the subagent's text and thinking blocks as `assistant`/`user` messages carrying `parent_tool_use_id`, letting the caller reconstruct the subagent's own transcript; without the flag only the subagent's `tool_use`/`tool_result` pair is visible.</details>

5. A `--json-schema` includes a property with `"format": "email"`. Does Claude Code reject a value that violates that format?
<details><summary>Answer</summary>No. The documented behavior is that Claude Code accepts the `format` keyword as an annotation without client-side validation — only structural constraints (`type`, `required`, `enum`, and similar) are actually enforced. A value that violates a `format` hint but satisfies the structural schema is still treated as valid.</details>

6. A caller's parsing code assumes the `json` envelope always contains exactly the fields documented on `cli-reference` and breaks when a new release adds a key. What was the actual guarantee, and which fields does it cover?
<details><summary>Answer</summary>The documented field set (`result`, `is_error`, `session_id`, `total_cost_usd`, `usage.*`, `duration_ms`) is the stable contract; a real envelope can and does carry additional keys (e.g. `permission_denials`, `subagent_stats`, `fast_mode_state`) that are diagnostic bonus for that release, not guaranteed to persist. Parsing code should read named fields it needs and tolerate unknown extra keys, not assume an exact closed key set.</details>

7. A fresh clone of a repository, never trusted by anyone, is run for the first time as `claude -p "run the tests"`. Does its committed `.claude/settings.json` `permissions.allow` list apply?
<details><summary>Answer</summary>No. `permissions/06-directories-and-trust.md` §1.4.34, re-verified against current documentation, establishes that for this general case those rules go unused and Claude Code prints a `this workspace has not been trusted` warning to stderr — the opposite of "counts as accepted" for that specific question. The "counts as accepted" phrasing governs a different, narrower check (whether `.claude/settings.local.json` is git-tracked).</details>

## Open questions

- **Unverified:** whether `--json-schema` carries a minimum Claude Code version floor — the `cli-reference` entry re-verified 2026-08-30 states no version number, unlike `--forward-subagent-text`'s explicit v2.1.211 floor in the same document.

---

**Leaves covered:** 3.6.1–3.6.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-80
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 478
