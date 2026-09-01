# VERIFIED hook JSON output schema — Stop / SubagentStop and the universal fields

**Provenance:** fetched as raw markdown, not via a summarising tool —
`curl -sL https://code.claude.com/docs/en/hooks.md` — and read directly from the
`## JSON output` common-fields table and the `#### Stop decision control` section.
**Verified 2026-08-30 against Claude Code v2.1.2xx.**

**Three agents on this run got this field wrong three different ways before anyone read the raw
page. A WebFetch summary of a reference table is not a citable source: it is a small model's
reconstruction of a schema, and it will invent plausible field names. For anything shaped like an
API contract, fetch the raw `.md` and grep it.**

## The three kinds of field, and conflating them is the whole bug

Quoted verbatim from the page:

> * **Universal fields** like `continue` are listed in the table below. Every event accepts them, but
>   some events discard them or deliver `systemMessage` somewhere other than the transcript.
> * **Top-level `decision` and `reason`** are used by some events to block or provide feedback.
> * **`hookSpecificOutput`** is a nested object for events that need richer control. It requires a
>   `hookEventName` field set to the event name.

### 1. Universal, top-level — every event accepts these

| Field | Default | Description (verbatim) |
|---|---|---|
| `continue` | `true` | If `false`, Claude stops processing entirely after the hook runs. Takes precedence over any event-specific decision fields |
| `stopReason` | none | Message shown to the user when `continue` is `false`. Not shown to Claude |
| `suppressOutput` | `false` | Has no effect: Claude Code accepts the field but doesn't act on it. A successful hook's stdout is never shown in the transcript and is recorded in the debug log |
| `systemMessage` | none | Warning message shown to the user |
| `terminalSequence` | none | A terminal escape sequence for Claude Code to emit on your behalf. Restricted to OSC `0`/`1`/`2`/`9`/`99`/`777` and BEL |

**So the boolean `continue` is a universal kill switch, and it means the OPPOSITE of "keep going".**
`continue: true` is not how you continue — it is the default. `continue: false` stops everything.
`stopReason` pairs with it and is shown to **the user, not to Claude**.

### 2. `Stop` / `SubagentStop` decision control — verbatim from `#### Stop decision control`

| Field | Description (verbatim) |
|---|---|
| `decision` | `"block"` prevents Claude from stopping. Omit to allow Claude to stop |
| `reason` | Required when `decision` is `"block"`. Tells Claude why it should continue |
| `hookSpecificOutput.additionalContext` | Non-error feedback for Claude. The conversation continues so Claude can act on it, but unlike `decision: "block"` it is shown in the transcript as hook feedback rather than a hook error |

> A hook that blocks by exiting 2 routes the same way as `reason`: Claude receives the stderr message
> as the explanation for why it should continue.

The page's own two examples, verbatim:

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

## THE TRAP — and it is why everyone got it backwards

**To keep Claude working you BLOCK THE STOP.** `{"decision": "block", "reason": "..."}`.

There is **no** `hookSpecificOutput.continue`. There is **no** `continueReason` field anywhere in
this schema. There is **no** `decision: "continue"` enum value. The semantics are inverted from the
intuitive reading, which is exactly what makes this good interview material and exactly what made
three independent readings wrong.

## Two facts that were missing entirely, and both belong in the notes

**Loop protections on `Stop`**, verbatim:

> In addition to the common input fields, Stop hooks receive `stop_hook_active`,
> `last_assistant_message`, `background_tasks`, and `session_crons`. The `stop_hook_active` field is
> `true` when Claude Code is already continuing as a result of a stop hook. Check this value or
> process the transcript to avoid blocking on a condition that will never resolve. **Claude Code
> overrides the hook and ends the turn after 8 consecutive blocks.**

`additionalContext` keeps the conversation going *through the same loop protections* as
`decision: "block"` — the `stop_hook_active` input and the 8-consecutive-continuation cap — but the
transcript labels it `Stop hook feedback` and no hook error notification is shown.

**A `Stop` hook written without checking `stop_hook_active` is an infinite-turn generator**, bounded
only by that 8-block cap. That is the honest mechanical answer to "why is a four-minute build in a
`Stop` hook dangerous".

**The 10,000-character output cap**, verbatim:

> Hook output strings, including `additionalContext`, `systemMessage`, and plain stdout, are capped
> at 10,000 characters. Output that exceeds this limit is saved to a file and replaced with a preview
> and file path.

And where several hooks return `additionalContext` for the same event, Claude receives all the
values; a value over 10,000 characters is written to a file in the session directory and Claude gets
the path plus a short preview.
