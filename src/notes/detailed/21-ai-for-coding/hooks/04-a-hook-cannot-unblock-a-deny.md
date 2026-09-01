# 21 AI for Coding — a hook cannot unblock a deny — INTERMEDIATE (§2.3.15–2.3.17)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [payloads, exit codes and the JSON contract](03-payloads-and-exit-codes.md) · Next: [the six configuration sources](05-configuration-sources.md)

The previous file gave the JSON output contract field by field — what `permissionDecision`,
`updatedInput`, `continue`, and `retry` each do, and which event honours which. This file asks the
question that field list invites and does not answer on its own: when a `PreToolUse` hook returns
`permissionDecision: "allow"`, does that decision actually win? The answer is the single most
consequential fact in this whole area, because the wrong assumption about it produces a security
control that looks like it works and does not: **a hook can narrow what the rules already decided,
and it can never widen it.**

## §2.3.15 Which decision field each event honours

**Mechanism.** The previous file's field-by-field table answered "what does this field do, and on
which events." This leaf asks the same question from the other direction — for a given event, which
one field (if any) is the one that actually carries a decision:

| Event | Decision field it honours | What "no decision" looks like |
|---|---|---|
| `PreToolUse` | `permissionDecision` (`allow` \| `deny` \| `ask`) | exit `0`, no `hookSpecificOutput` — the call proceeds through the normal permission rules untouched |
| `PermissionRequest` | `permissionDecision` (a separately documented `decision` object also applies here; shape **unverified**, carried over from file 03's open question) | same as `PreToolUse` |
| `PostToolBatch` | `continue` (boolean) | `true`, or the field omitted — the batch ends as it would have anyway |
| `Stop`, `SubagentStop` | top-level `decision: "block"` (+ required `reason`) | field omitted — the turn ends as it would have anyway |
| `UserPromptExpansion` | `decision` — the **only** event that reads this nested field name | field omitted — the expansion proceeds unmodified |
| `PermissionDenied` | `retry` (boolean) | field omitted — the model is not told it may retry |
| `PostToolUse`, `PostToolUseFailure` | **none** | there is no decision field to omit — see below |

**Correction:** an earlier pass of this row listed `Stop`/`SubagentStop` alongside `PostToolBatch`
as sharing the `continue` mechanism, with `continue: false` (or `true`) as the decision. **`[VERIFIED]`**
against the raw `https://code.claude.com/docs/en/hooks.md` fetch on 2026-08-30: `Stop`/`SubagentStop`
honour top-level `decision: "block"` with a required `reason`; omitting `decision` allows the stop.
`continue` is a separate, universal top-level kill switch on **every** event — not scoped to
`Stop`/`SubagentStop` or `PostToolBatch` — and `continue: false` **takes precedence over any
event-specific decision field**, including `decision: "block"`. **Pitfall:** the semantics are
inverted from the intuitive reading — to keep Claude working past a `Stop` event, you *block the
stop*; there is no `continueReason` field and no `decision: "continue"` value anywhere in this schema.

**Gotcha.** `PostToolUse` and `PostToolUseFailure` fire after the tool call already ran. There is
nothing left to allow, deny, or ask about — the action already happened — so neither event exposes a
decision field at all, only `additionalContext` (informational, not a gate). A hook author who writes
`permissionDecision` into a `PostToolUse` handler's output is not making a mistake the harness
rejects; the field is simply not read on that event, silently, exactly like the `decision`-on-
`PreToolUse` mistake file 03 already covered.

> Each blockable event honours exactly one decision-bearing field — `permissionDecision` for tool and
> permission events, `continue` for `PostToolBatch`, top-level `decision`/`reason` for `Stop` and
> `SubagentStop`, nested `decision` for `UserPromptExpansion`, `retry` for `PermissionDenied` — and an
> event that has already run its action, like `PostToolUse`, honours none. The universal `continue`
> kill switch sits above all of these and overrides whichever one applies.

## §2.3.16 [DOC] [TRAP] A hook cannot unblock a deny

**Mental model.** Picture permission rules and a `PreToolUse` hook as two separate reviewers who both
get a vote, but whose votes are not weighted equally. The rules reviewer's `deny` is a hard veto that
no other vote can overturn. The rules reviewer's `ask` is a demand for a human in the loop that no
other vote can waive. The hook is a second reviewer who can vote to block or to demand confirmation —
and whose vote to *approve* only counts when the rules reviewer had no objection in the first place.
A hook is not a manager standing above the rules with the power to override them; it is a peer who can
only make the outcome stricter, never looser.

**Why it exists.** §1.4.3 elsewhere in this guide already establishes that a narrow `allow` cannot
rescue a call caught by a broader `deny`, and §1.4.36 establishes that a `deny` at any settings layer
is absolute, including one set in managed settings a project cannot override. This leaf is the third
face of that same rule, not a new one: if a narrowly-scoped `allow` rule cannot reopen a `deny`, then
a `PreToolUse` hook — which is even more dynamic and even easier for an individual engineer to attach
without organizational review — certainly cannot either. The alternative would make every `deny` rule
in every settings layer conditional on nobody, anywhere, ever attaching a hook that disagrees with it,
which would make `deny` meaningless as a control an organization can actually rely on.

**When to reach for a hook instead of a rule, and when it cannot substitute.** A hook is the right
tool when the condition for blocking or asking is too dynamic to express as a `permissions.deny`
glob — "block this `Bash` call only if the string it contains matches a URL denylist fetched at
runtime," say, which no static settings pattern can express. A hook is the *wrong* tool when the goal
is "guarantee this specific command is refused," because that guarantee already exists, unconditionally
and independent of any hook, the moment the command is expressed as a `deny` rule. Reaching for a hook
to *carve an exception out of* an existing `deny` is the specific mistake this leaf exists to close
off — that direction never works, by design.

**How it works, precisely — re-verified against `https://code.claude.com/docs/en/hooks` and
`https://code.claude.com/docs/en/permissions` on 2026-08-29.** The permissions page states this in
its own "Extend permissions with hooks" section, in exactly these terms:

> "When Claude Code makes a tool call, PreToolUse hooks run before the permission prompt, for every
> tool except `EndConversation`. The hook output can deny the tool call, force a prompt, or skip the
> prompt to let the call proceed."
>
> "Hook decisions don't bypass permission rules. Claude Code evaluates deny and ask rules regardless
> of what a PreToolUse hook returns: a matching deny rule blocks the call, and a matching ask rule
> still prompts even when the hook returned `"allow"` or `"ask"`. This preserves the deny-first
> precedence described in Manage permissions, including deny rules set in managed settings."
>
> "A blocking hook also takes precedence over allow rules. A hook that exits with code 2 stops the
> tool call before permission rules are evaluated, so the block applies even when an allow rule would
> otherwise let the call proceed."

**Divergence from this file's own header framing, stated plainly.** The syllabus row that commissioned
this file frames the guarantee as "the `PreToolUse` hook runs strictly after rule evaluation." The
live documentation's own words are more precise than that and do not fully match: a `PreToolUse` hook
runs **before the permission prompt**, and a *blocking* hook (exit `2`) is stated to stop the call
**before permission rules are evaluated** at all. What the documentation does guarantee — in the exact
wording quoted above — is not a strict "hook always runs after rules" ordering, but a **narrower,
asymmetric one**: deny and ask rules are evaluated *regardless of* what the hook returned, so an
`allow` from the hook can never suppress a matching `deny` or `ask` rule, while a `deny` from the hook
(exit `2`) *does* take effect ahead of an `allow` rule. The practical guarantee this guide's title
promises — **a hook cannot unblock a deny** — holds exactly as stated; the mechanism producing it is
"the rules are checked independently of the hook's approval" rather than a strict temporal "hook runs
second." Both framings agree on the one fact that matters for this file: **a hook can narrow (add a
block, or force a prompt) and it can never widen (turn a `deny` or `ask` into a proceed).**

The two failing cases that follow from this, stated as the syllabus names them:

- a hook returning `permissionDecision: "allow"` on a call that matches a `deny` rule → **still
  blocked**, because the deny rule is evaluated regardless of what the hook returned;
- a hook returning `permissionDecision: "allow"` on a call that matches an `ask` rule → **still
  prompts**, for the same reason.

![D-53 — A hook cannot unblock a deny. The PreToolUse hook sits after rule evaluation, so it can narrow and never widen.](../diagrams/D-53-hook-cannot-unblock-deny.svg)

**D-53** — A hook cannot unblock a deny. The `PreToolUse` hook sits after rule evaluation, so it can
narrow and never widen.

**Code.** The full quartet — the deny rule, the hook registration, the hook script, the triggering
call, and the observed outcome — because a claim this consequential is worth showing as real
configuration rather than asserting in prose.

The project settings file with the deny rule, complete:

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf *)"
    ],
    "allow": [
      "Bash(git *)",
      "Bash(mvn *)"
    ]
  }
}
```

A `hooks.json` registering a `PreToolUse` handler on `Bash`, complete, shipped alongside it:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/allow-safe-cleanup.sh"
          }
        ]
      }
    ]
  }
}
```

The hook script itself, complete, with an explicit failure posture and a real `jq` read over stdin —
an engineer's good-faith attempt to carve a narrow exception for a known-safe cleanup pattern out of
the broad `deny` above:

```bash
#!/usr/bin/env bash
set -e

INPUT_JSON="$(cat)"
COMMAND="$(echo "$INPUT_JSON" | jq -r '.tool_input.command // ""')"

if echo "$COMMAND" | grep -Eq '(^|[[:space:]])rm[[:space:]]+-rf[[:space:]]+(\./)?(build|target|node_modules)([[:space:]]|$)'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"rm -rf against a known throwaway build directory, not a real path"}}'
  exit 0
fi

exit 0
```

The command that triggers it, and the observed outcome:

```text
$ claude -p "clean the stale build output before recompiling" --output-format json
```

Claude proposes `Bash(rm -rf build)`. `allow-safe-cleanup.sh` fires on the `PreToolUse` matcher
`Bash`, matches the `build` directory pattern in its `grep`, and prints
`permissionDecision: "allow"` with a specific reason on exit `0`. The observed outcome is not
"proceeds" — it is **blocked**, with the permission denial attributed to the `Bash(rm -rf *)` deny
rule, not to the hook. `rm -rf build` matches that glob exactly as much as `rm -rf /` does; the deny
rule does not distinguish "safe" targets from dangerous ones, and the hook's `allow` — computed
correctly, for a reasonable-sounding exception — is never consulted for the yes/no outcome, per the
quoted documentation above. The engineer who wrote this hook to reopen a narrow, legitimate case
inside a broad `deny` has built a hook that runs, computes the intended answer, and changes nothing.

**Pitfall:** the wrong belief: "a `PreToolUse` hook is an escape hatch that sits above the permission
rules — if I need an exception to a `deny`, I can write a hook that returns `allow` for the specific
case I care about." The symptom: the hook fires (the debug log confirms it ran and returned `allow`),
and the tool call is refused anyway, with no error in the hook itself — nothing in the hook's own
behaviour looks broken, because the hook is not broken; the assumption about what its `allow` overrides
is. The fix: change the rule itself — narrow the `deny` to the pattern that actually needs blocking
(`Bash(rm -rf /*)` rather than `Bash(rm -rf *)`, if that is genuinely the intent), or do not write a
`deny` rule broad enough to catch the legitimate case in the first place. A hook cannot repair an
overly broad `deny`; only editing the rule can. **Why people believe it:** hooks are the newer,
more dynamic, more code-shaped mechanism, and engineers reasonably extrapolate from "hooks can do
things settings rules cannot express" (arbitrary logic, external lookups, rewriting inputs) to "hooks
therefore sit above settings rules in authority" — the two are unrelated. Hooks have *more expressive
power*, not *more authority*; a `deny` rule still outranks anything a hook can return.

**Insight:** the asymmetry is what makes `deny` a control an organization can actually rely on rather
than a suggestion. If any developer's locally-registered `PreToolUse` hook could reopen a `deny` set
in managed settings, then a security team publishing a `deny` list would have no way to know whether
it was actually enforced anywhere a hook happened to be present — the guarantee would depend on every
engineer in the organization never writing a hook that disagreed. By making `deny` and `ask`
unconditional regardless of hook output, and only letting a hook add a *stricter* outcome (a block, or
a forced prompt) on top of what the rules already decided, the harness makes the direction of drift
one-way: configuration can only get more restrictive at runtime, never less.

**Interview:** "A settings file has `Bash(aws *)` in `deny`. A developer writes a `PreToolUse` hook
that returns `permissionDecision: allow` whenever the command is `aws s3 ls`. Does that `aws s3 ls`
call proceed?" — no. `Bash(aws *)` is a deny rule, and deny rules are evaluated regardless of what a
`PreToolUse` hook returns; the hook's `allow` is not consulted for the yes/no decision, so the call is
still blocked. The only way to permit `aws s3 ls` is to change the rule itself — remove or narrow the
`deny`, or add a scoped exception the deny glob does not already catch.

> A `PreToolUse` hook can turn a call the rules would have allowed into a block or a forced prompt,
> and it can never turn a call the rules already decided to `deny` or `ask` about into a proceed —
> the harness evaluates `deny` and `ask` regardless of what the hook returns, so a hook narrows and
> never widens.

## §2.3.17 [DOC] Path placeholders and env vars, and what changes inside a plugin

**Mental model.** File 03 already introduced three of these placeholders and the specific failure of a
bare relative path inside a plugin hook. This leaf finishes the set — three more environment variables
a hook can read that are not path placeholders at all — and then answers the one question file 03
deliberately left open: given that `${CLAUDE_PLUGIN_ROOT}` is *some* directory a hook can rely on,
what is that directory actually *for*, and what does a hook do when what it actually wants is not the
plugin's own files but the project's git repository?

**How it works.** Re-verified against `https://code.claude.com/docs/en/hooks` on 2026-08-29, the
complete set of placeholders and environment variables a hook command can rely on:

| Name | Kind | What it resolves to |
|---|---|---|
| `${CLAUDE_PROJECT_DIR}` | path placeholder, also exported as an env var | the project root where the session started; pinned there even under a worktree (file 03) |
| `${CLAUDE_PLUGIN_ROOT}` | path placeholder, also exported as an env var | the plugin's own **installation directory** — "changes on each plugin update," per the live page |
| `${CLAUDE_PLUGIN_DATA}` | path placeholder, also exported as an env var | the plugin's persistent data directory, for state and dependencies that must survive a plugin update |
| `$CLAUDE_CODE_REMOTE` | env var only | `"true"` in a remote web environment, unset in the local CLI — a hook can branch on this to skip a step that only makes sense on a developer's own machine |
| `$CLAUDE_EFFORT` | env var only | the current effort level (`low` \| `medium` \| `high` \| `xhigh` \| `max`) in effect when the hook runs |
| `$CLAUDE_PLUGIN_OPTION_<KEY>` | env var only, one per configured option | a plugin's own user-configured option value, uppercased — `$CLAUDE_PLUGIN_OPTION_WEBHOOK_URL` for a `webhook_url` option declared in the plugin's own configuration schema |

**The plugin-root question, precisely.** `${CLAUDE_PLUGIN_ROOT}` is the directory Claude Code
installed the plugin *into* — a cache or install location the harness manages, not the plugin
author's own source repository, and not the project the session is actually working in. **Correct
one more piece of folklore here directly: `${CLAUDE_PLUGIN_ROOT}` is not the repository.** A hook
script that was written and tested from inside the plugin's own git checkout, where the install
directory and the working tree happen to be the same path during local development, can silently
assume they are always the same thing — and they are not, the moment that plugin is packaged,
published, and installed by someone else. `${CLAUDE_PLUGIN_ROOT}` "changes on each plugin update," per
the quoted line above, which is itself evidence that it names an install artifact with a lifecycle of
its own, not a fixed checkout a hook author controls.

That distinction matters concretely when a plugin's hook needs to act on **the project's own
repository** — say, a `PreToolUse` guard that wants to check whether a file being edited is tracked by
git, or a `PostToolUse` hook that wants to know the project's repo root to write a report next to it.
`${CLAUDE_PROJECT_DIR}` answers "where did the session start," which is usually what is wanted, but a
hook that needs the actual **git repository root** — which can differ from the session's start
directory when a session starts in a subdirectory of a larger repository — should ask git directly
rather than infer it from either placeholder:

```bash
#!/usr/bin/env bash
set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "plugin-repo-context.sh: not inside a git repository; refusing to guess a root" >&2
  exit 2
}

echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"repo root: ${REPO_ROOT}\"}}"
exit 0
```

`git rev-parse --show-toplevel` is the correct mechanism because it asks the one authority that
actually knows the answer — git itself, walking up from the process's current working directory until
it finds a `.git` — rather than the hook author reconstructing the answer from `${CLAUDE_PLUGIN_ROOT}`
(wrong: that is the plugin's own install directory) or from `${CLAUDE_PROJECT_DIR}` (usually right, but
not guaranteed to equal the git root when the session started in a subdirectory).

**Gotcha.** When `git rev-parse --show-toplevel` fails — the session is not inside a git repository at
all — the correct behaviour is to **refuse with a clear message on stderr and a nonzero exit**, exactly
as the script above does, not to invent a third fallback (guessing `$PWD`, falling back to
`${CLAUDE_PLUGIN_ROOT}`, or silently writing to `/tmp`). A fallback that "usually works" is precisely
the kind of assumption that turns into a silent no-op or a wrong-directory write the one time it does
not hold, and a hook that refuses loudly is far cheaper to diagnose than one that quietly did the
wrong thing. `[X-REF]` The full incident this general risk becomes concrete in — a plugin-shipped hook
that resolved correctly in the plugin author's own repository and silently no-op'd the moment it was
installed somewhere else — is worked through in full, with its own diagram, in
`plugins/05-cases-and-conversion.md` (§2.5.18, D-60); this file establishes the mechanism only and
does not resolve that incident here.

> A path placeholder or environment variable available to a hook answers one specific question —
> `${CLAUDE_PLUGIN_ROOT}` answers "where was this plugin installed," not "where is the project's git
> repository" — and a hook that needs the repository root asks git directly with
> `git rev-parse --show-toplevel`, refusing clearly when that fails rather than guessing.

## Pitfalls

- **Belief:** "A `PreToolUse` hook is an escape hatch above the permission rules — I can write one
  that returns `allow` to carve an exception out of a `deny` rule I don't want to loosen globally."
  **Symptom:** the hook runs, the debug log shows it returned `permissionDecision: "allow"` with a
  correct, specific reason, and the tool call is refused anyway, attributed to the `deny` rule rather
  than to any failure in the hook. **Fix:** edit the rule itself — narrow the `deny` glob to the
  pattern that actually needs blocking, or do not write a `deny` broad enough to catch the case that
  needs an exception. **Why people believe it:** hooks are more expressive than static settings
  patterns, and it is easy to over-generalize "hooks can do more" into "hooks outrank rules," when the
  two properties are independent — a `deny` rule is unconditional regardless of what any hook returns.
- **Belief:** "`${CLAUDE_PLUGIN_ROOT}` is the plugin's own git repository, so a hook can read or write
  files there the way it would in a normal checkout." **Symptom:** the hook works during local
  development, where the install directory and the working tree happen to coincide, and then silently
  reads stale or missing files — or writes somewhere the plugin author never intended — the moment the
  plugin is installed by someone else, where the two paths are no longer the same location. **Fix:**
  treat `${CLAUDE_PLUGIN_ROOT}` as an install artifact only; reach the project's actual repository with
  `git rev-parse --show-toplevel`, and refuse clearly if that fails rather than falling back to a
  guess. **Why people believe it:** during authoring and local testing, the plugin's checkout and its
  "installed" location are frequently the same directory, so the distinction never surfaces until the
  plugin is packaged and installed somewhere the two diverge.

## Cheat sheet

| Question | Answer |
|---|---|
| Can a `PreToolUse` hook's `permissionDecision: allow` override a matching `deny` rule? | No — `deny` is evaluated regardless of what the hook returns |
| Can it override a matching `ask` rule? | No — the call still prompts, even if the hook returned `allow` |
| Can a hook's blocking decision (exit `2`) override an `allow` rule? | Yes — a blocking hook takes precedence over `allow` |
| Net rule | a hook can narrow (add a block or a forced prompt); it can never widen (turn a `deny`/`ask` into a proceed) |
| Decision field, `PreToolUse` / `PermissionRequest` | `permissionDecision` |
| Decision field, `PostToolBatch` | `continue` |
| Decision field, `Stop` / `SubagentStop` | top-level `decision: "block"` (+ required `reason`); omit `decision` to allow the stop |
| Decision field, `UserPromptExpansion` | nested `decision` (the only event that reads this name at this nesting) |
| Decision field, `PermissionDenied` | `retry` |
| Decision field, `PostToolUse` / `PostToolUseFailure` | none — the action already ran |
| Universal kill switch, every event | `continue: false` (top-level) — overrides any of the above; `stopReason` pairs with it and is shown to the user, not Claude |
| `${CLAUDE_PLUGIN_ROOT}` | the plugin's install directory; changes on each update; **not** the plugin's own repo |
| Reach the project's repo from a plugin hook | `git rev-parse --show-toplevel`; refuse clearly if it fails |
| `$CLAUDE_CODE_REMOTE` | `"true"` in a remote web environment, unset locally |
| `$CLAUDE_EFFORT` | the active effort level: `low` \| `medium` \| `high` \| `xhigh` \| `max` |
| `$CLAUDE_PLUGIN_OPTION_<KEY>` | a plugin's own configured option value, one env var per option |

## Self-test

1. A settings file has `Bash(aws *)` in `deny`. A `PreToolUse` hook returns
   `permissionDecision: "allow"` for `aws s3 ls`. Does the call proceed?
   <details><summary>Answer</summary>No. Deny rules are evaluated regardless of what a `PreToolUse`
   hook returns; the hook's `allow` is not consulted for the yes/no outcome. The call is blocked,
   attributed to the deny rule.</details>
2. Same setup, but the rule is `Bash(aws *)` in `ask` instead of `deny`, and the hook returns `allow`.
   What happens?
   <details><summary>Answer</summary>The call still prompts. A matching `ask` rule is honoured
   regardless of what the hook returned.</details>
3. Can a hook's blocking decision override an `allow` rule?
   <details><summary>Answer</summary>Yes. A blocking hook (exit `2`) takes precedence over an `allow`
   rule — it stops the call before that rule would otherwise have let it through. This is the one
   direction a hook can move the outcome: stricter, never looser.</details>
4. What is the one-line summary of what a `PreToolUse` hook is allowed to do to the outcome the rules
   already computed?
   <details><summary>Answer</summary>Narrow it (turn a would-be-allowed call into a block or a forced
   prompt); never widen it (turn a `deny` or `ask` into a proceed).</details>
5. Which field does a `Stop` hook use to keep the turn from ending, and which field does a `PostToolUse`
   hook use for the same purpose?
   <details><summary>Answer</summary>`Stop` uses top-level `decision: "block"` with a required
   `reason` — omitting `decision` allows the stop. (The boolean `continue` is a separate, universal
   kill switch on every event, not the `Stop` mechanism; `continue: false` overrides `decision:
   "block"` if both are set.) `PostToolUse` has no such field at all — the tool call already ran, so
   there is nothing left to gate.</details>
6. What directory does `${CLAUDE_PLUGIN_ROOT}` actually point to, and what is the one widely-repeated
   wrong belief about it?
   <details><summary>Answer</summary>It points to the plugin's own installation directory, which
   changes on each plugin update. The wrong belief is that it is the plugin's git repository — it is
   an install artifact the harness manages, not a checkout the plugin author controls.</details>
7. A plugin's hook needs the project's actual git repository root, which may differ from
   `${CLAUDE_PROJECT_DIR}` when the session started in a subdirectory. What should the hook run, and
   what should it do if that fails?
   <details><summary>Answer</summary>`git rev-parse --show-toplevel`. If it fails (not inside a git
   repository), the hook should refuse with a clear message on stderr and a nonzero exit, rather than
   guessing a fallback path.</details>
8. Which environment variable lets a hook branch on whether it is running in a remote web environment
   versus the local CLI?
   <details><summary>Answer</summary>`$CLAUDE_CODE_REMOTE` — `"true"` in a remote web environment,
   unset in the local CLI.</details>

## Open questions

**Unverified:** the exact shape of `PermissionRequest`'s separately documented `decision` object,
distinct from `permissionDecision` — carried over from file 03's own open question, still unresolved
here; the live page's per-event schema subsection for `PermissionRequest` did not fully render in this
session's fetches.

---

**Leaves covered:** 2.3.15–2.3.17 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-53
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 408
