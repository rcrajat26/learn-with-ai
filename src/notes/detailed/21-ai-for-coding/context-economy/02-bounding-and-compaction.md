# 21 AI for Coding — bounding output and compaction in practice — INTERMEDIATE (§2.6.5–2.6.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [measuring and ranking context cost](01-measuring-and-ranking.md) · Next: [isolation arithmetic](03-isolation-arithmetic.md)

The previous file measured a session's context and ranked the four biggest avoidable costs, closing
with bounding tool output as the cheapest of the four fixes. This file is what happens once bounding
alone is not enough — the session is long, the transcript is large, and something has to give. That
something is compaction: an automatic or manual summarisation that replaces the transcript with a
shorter one. This file covers when to let it happen automatically, when to trigger it yourself, when
to reach for `/clear` or a fresh session instead, and the one hook seam — `PreCompact` — that lets you
save what a compaction is about to throw away.

## Autocompaction: the settings that decide when it fires

**Mental model.** Autocompaction is a smoke detector, not a fire extinguisher you reach for. It
watches one number — how full the context window is — and when that number crosses a threshold, it
acts on its own, without asking, replacing the transcript with a summary before the window actually
fills and the session hard-stops. A reader who has only ever typed `/compact` by hand has experienced
the extinguisher; most compactions in a long session are the smoke detector firing first.

**Why it exists.** §0.2.6 already established that every turn re-sends the whole conversation, and
§1.3.11 showed that cost only grows across a session — nothing shrinks the transcript on its own.
Left alone, a long enough session eventually fills the context window entirely and the harness cannot
send the next turn. Autocompaction exists so that failure mode never happens without the user's
input: the harness compacts pre-emptively, at a configurable point before the window is actually full.

**How it works.** Two settings keys, verified against `settings-reference` immediately before writing
this leaf:

| Key | Type | What it does |
|---|---|---|
| `autoCompactEnabled` | boolean | Turn automatic compaction off or on |
| `autoCompactWindow` | number | Set how full the context gets before Claude Code compacts |

`[DOC]` — both descriptions above are quoted verbatim from `settings-reference`; both are documented
as valid in any of the four settings-file scopes (user, project, local, managed) with no restriction
to project-root files.

The session-scoped override is the `--autocompact` CLI flag, confirmed against the installed binary
(`claude 2.1.251`, matching the v2.1.2xx target line) since the flag's accepted value forms are not
spelled out in full on the `cli-reference` page fetched for this leaf:

```
$ claude --help | grep -A2 -- --autocompact
  --autocompact <auto|tokens>           Auto-compact window size (auto, or
                                        100k–1M tokens)
```

So `autoCompactWindow` and `--autocompact` both take either the literal `auto` or an explicit token
threshold between 100k and 1M — not a bare percentage, despite the setting's own description reading
"how full the context gets." A settings file that sets a session's compaction point looks like this,
complete and valid:

```json
{
  "autoCompactEnabled": true,
  "autoCompactWindow": "auto"
}
```

The equivalent one-off override, without touching the saved settings file:

```bash
claude --autocompact 500k
```

**Unverified:** the global `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` environment variable — named in some
external configuration guides as a way to set the autocompaction threshold as a raw percentage — does
not appear on the `settings-reference` or `cli-reference` pages, and `claude --help` lists no
environment-variable table at all. This guide cannot confirm the variable exists in v2.1.2xx, confirm
its spelling, or confirm what it overrides. Treat any claim built on it as unverified until the
`env-vars` documentation page — outside this leaf's permitted page set — settles it. Recorded below in
`## Open questions`.

No diagram of its own here: D-27 (in `01-instruction-files.md`, cited at §1.3.26) already draws the
compaction event itself — what a compaction produces and what an instruction file does across it. This
leaf only adds the settings that decide *when* that event fires, not what it does; there is nothing
new to draw.

**Pitfall:** believing `/compact` and autocompaction are the same feature with two names. They share a
mechanism — both replace the transcript with a summary — but autocompaction is a background policy
keyed to `autoCompactWindow`, while `/compact` (below) is an explicit, immediate command a person
types. Turning `autoCompactEnabled` off does not disable `/compact`; it only stops the background
trigger.

**Insight:** compaction is not free. It is itself a call to the model — the transcript is sent once
more, in full, to produce the summary that replaces it — so a compaction costs one summarisation
request's worth of input tokens on top of whatever the session was already carrying, and it happens
on the turn where the threshold is crossed, not spread out. A session that compacts five times across
its life pays that summarisation cost five times.

**Interview:** *"Why would a team disable autocompaction rather than just raising the threshold?"*
Because a summary is lossy — every compaction discards detail the session doesn't know it will need
again — and a team running long, disciplined sessions with explicit checkpointing (the `PreCompact`
hook below, or a deliberate `/clear` at task boundaries) sometimes prefers a hard stop they control
over a silent summarisation they don't; raising the threshold delays the loss, disabling it forces the
team to manage the window by hand instead.

> Autocompaction is a background policy — `autoCompactEnabled` on or off, `autoCompactWindow` set to
> `auto` or an explicit 100k–1M token threshold — that replaces the transcript with a summary before
> the context window actually fills, at the cost of one summarisation call charged on the triggering
> turn.

## What survives a compaction, and what to do before one happens

**Mental model.** A compaction is not a save. It is closer to a lossy photograph of the room right
before the movers arrive: the furniture that was bolted to the floor is still there afterward, and
everything else is gone unless someone carried it out first.

**Why it exists as a practice question, not just a mechanism.** §1.3.26 and D-27 already gave the
exhaustive list of what survives: project-root `CLAUDE.md` is re-read from disk after the event rather
than carried forward as text, nested and path-scoped instruction files reload only once a matching
path is touched again, and anything that lived only in the conversation — a decision made three turns
ago and never written down, a constraint the user stated once in chat — is gone. §1.5.16 and D-40
already gave the skill re-attachment budget: only the most recent invocation of each skill survives,
capped at 5,000 tokens each and 25,000 combined, newest-first. This file does not re-derive either
list. What it adds is the practice: given that list, what do you do *before* a compaction to keep from
losing the parts that were never going to survive on their own?

**How it works, as a checklist.** Three moves, each aimed at one gap in what survives:

1. **Push durable facts into `CLAUDE.md` before you need them to survive**, not after. A decision made
   only in conversation is exactly the content the surviving-list excludes; the same decision written
   into the project-root file is re-read from disk on the other side of the event, per §1.3.26.
2. **Re-invoke a skill you'll need again, on the turn before you expect a compaction**, rather than
   trusting an invocation from forty turns ago to still be inside the 5,000/25,000-token budget by the
   time it matters — the budget keeps the *most recent* invocation, not the *most relevant* one.
3. **For anything that fits neither of the first two — an in-progress plan, a list of files already
   checked, a partial result — write it to a file on disk yourself, or let a `PreCompact` hook do it
   automatically.** That is the next leaf.

`[NUM]` — restating the two hard numbers from §1.5.16 at the point this leaf actually uses them,
because a checklist that says "budget" without the figures is not a checklist: **5,000 tokens per
skill, 25,000 tokens combined, most-recent-invocation-per-skill, newest-first when the combined cap is
hit.**

**Gotcha:** step 1 only works for the project-root `CLAUDE.md`. A nested or path-scoped instruction
file does not reload just because a compaction happened — per §1.3.26 it reloads only when a matching
path is touched again in the new, shorter transcript. Writing a durable fact into a path-scoped rule
file is not equivalent to writing it into the project root for the purpose of surviving a compaction;
it survives on disk, but it will not be back in context until the session touches that path again.

**Pitfall:** treating "it's written down somewhere in this session's history" as equivalent to "it
will survive." A fact stated once in chat, even emphatically, even three times, is conversation —
exactly the category the surviving-list excludes. Only a file on disk that gets re-read (the
project-root `CLAUDE.md`) or re-attached (a skill within budget) crosses the compaction boundary; nothing
that lived purely as chat text does.

> What survives a compaction is exactly two categories — the project-root `CLAUDE.md`, re-read from
> disk, and the single most recent invocation of each skill within a 5,000/25,000-token budget — so
> the practice is to move anything else that matters into one of those two categories, or onto disk
> directly, before the compaction happens rather than after.

## `PreCompact` and `PostCompact`: the hook seam for what the list above doesn't cover

**Mental model.** Hooks were established earlier in this topic as a guarantee, not a suggestion — a
shell command the harness runs at a fixed lifecycle point, every time, whether or not the model
"remembers" to run it. `PreCompact` is that guarantee applied to the one moment in a session's life
where data loss is scheduled and predictable: the instant before a summarisation call throws most of
the transcript away.

**Why it exists.** The checklist above covers `CLAUDE.md` and skills — both first-class, harness-level
concepts with a defined survival rule. It does not cover an ad hoc in-progress state: a list of files
already reviewed in a long refactor, a partial checklist, a decision tree half-walked. Nothing
automatic preserves that. `PreCompact` is the seam that lets a project preserve it anyway, without
relying on the model to remember to write it down.

**How it works.** Verified against `hooks`, re-fetched for this leaf: `PreCompact` and `PostCompact`
are lifecycle events — "Before context compaction" and "After context compaction completes"
respectively — and both support a `matcher` of `manual` or `auto`, letting a hook distinguish a
user-typed `/compact` from an automatic one triggered by `autoCompactWindow`. `PreCompact` can block:
exiting the hook command with status `2` prevents the compaction from proceeding at all. `PostCompact`
cannot block anything — by the time it runs, the summarisation has already happened, so there is
nothing left to prevent.

Configured in `settings.json`, as a complete `hooks` block — this is the whole file, not a fragment:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/checklist-refresh.sh"
          }
        ]
      }
    ]
  }
}
```

The script the hook runs, complete, reading the current transcript path from the hook's own stdin
JSON and writing a durable checkpoint file the project-root `CLAUDE.md` can later point at:

```bash
#!/usr/bin/env bash
set -euo pipefail

# checklist-refresh.sh — PreCompact hook. Persists an in-progress checklist to
# disk before an automatic compaction discards the conversation turns it lived
# in. Reads the hook's stdin JSON for the transcript path; writes a plain-text
# checkpoint file that a human, or the next turn's model, can read back.

input_json="$(cat)"
transcript_path="$(echo "$input_json" | jq -r '.transcript_path')"
trigger="$(echo "$input_json" | jq -r '.hook_event_name // "PreCompact"')"

checkpoint_dir=".claude/checkpoints"
mkdir -p "$checkpoint_dir"

checkpoint_file="$checkpoint_dir/pre-compact-$(date +%Y%m%dT%H%M%S).md"

{
  echo "# Pre-compaction checkpoint"
  echo "Triggered by: $trigger"
  echo "Transcript: $transcript_path"
  echo
  echo "## Last 40 lines of the transcript, verbatim, before summarisation"
  tail -n 40 "$transcript_path" 2>/dev/null || echo "(transcript unreadable at hook time)"
} > "$checkpoint_file"

echo "Checkpoint written to $checkpoint_file" >&2
exit 0
```

**Prove step**, simulating the hook firing by invoking it directly with a representative stdin
payload rather than waiting on a real compaction:

```
$ echo '{"transcript_path":"/tmp/fake-transcript.jsonl","hook_event_name":"PreCompact"}' \
    | bash .claude/hooks/checklist-refresh.sh
Checkpoint written to .claude/checkpoints/pre-compact-20260830T091500.md

$ cat .claude/checkpoints/pre-compact-20260830T091500.md
# Pre-compaction checkpoint
Triggered by: PreCompact
Transcript: /tmp/fake-transcript.jsonl

## Last 40 lines of the transcript, verbatim, before summarisation
(transcript unreadable at hook time)
```

**What this costs:** the hook itself runs as a local shell command, not a model call, so triggering it
costs zero tokens on top of the compaction's own summarisation cost from the previous leaf; the only
recurring cost is disk space for the checkpoint files, which is a filesystem concern, not a context
one.

**Gotcha — what `PreCompact` cannot do.** It cannot inject its output back into the *post-compaction*
context automatically; writing a checkpoint file to disk does not make that file's contents part of
the summary or the surviving transcript. Getting the checkpoint back into context after the compaction
still requires either a `SessionStart` hook matched on `compact` reading it back in, or the
project-root `CLAUDE.md` explicitly telling the model where to look. `PreCompact` guarantees the write
happens; it does not guarantee the write gets read.

**Pitfall:** assuming a `PreCompact` hook that writes a checkpoint has "solved" compaction loss.
**Symptom:** the checkpoint file exists on disk, correctly, every time — and the next turn's model
still behaves as if the lost detail never existed, because nothing told it to read the file back.
**Fix:** pair every `PreCompact` write with either a matching `SessionStart` hook on the `compact`
matcher, or an explicit pointer in `CLAUDE.md` ("if resuming after a compaction, check
`.claude/checkpoints/` for the most recent file") — the write and the read are two separate
guarantees, and only the write is automatic here.

> `PreCompact` is a blocking-capable hook that fires immediately before a compaction, matched on
> `manual` or `auto`; it is the only guaranteed seam for persisting ad hoc in-progress state that
> neither `CLAUDE.md` nor the skill-invocation budget would otherwise carry across the event, but it
> only guarantees the write — reading the checkpoint back requires a separate `SessionStart` hook or
> an explicit `CLAUDE.md` pointer.

## Four resets, compared for when to reach for each

**Mental model.** All four operations in this section make a session's context smaller. They differ
in exactly one axis that matters in practice: how much of what came before is still there afterward,
from "everything, verbatim" down to "nothing, not even the working directory's identity."

**Why this table, here, rather than a re-derivation.** §0.4.5 and D-17 already drew the four reset
semantics — `/compact`, `/clear`, a fresh session, and `--fork-session` — in full. Re-teaching that
comparison here would be the exact re-derivation this leaf's brief forbids. What belongs here instead
is the decision layer: given that comparison, which one do you actually reach for, and when.

| Operation | What's left afterward | Reach for it when |
|---|---|---|
| `/compact` | A model-generated summary standing in for the transcript; `CLAUDE.md` and in-budget skills reload per the leaf above | The session is productive but long, and you want to keep working in the *same* conversational thread without losing the thread's continuity entirely |
| `/clear` | Nothing from the transcript; `CLAUDE.md` still loads fresh at the new turn 1 | The current task is genuinely finished and the next one is unrelated — a summary of the old task would be noise, not help, in the new one |
| A fresh session (new terminal invocation) | Nothing; a new session ID, no reference to the old one at all | Switching projects or contexts entirely, or when even `/clear`'s residual session metadata (session ID, resumability) is unwanted |
| `--fork-session` (with `--resume` or `--continue`) | Everything the resumed session had, copied into a *new* session ID rather than continuing to mutate the original | You want to try a risky next step — a large refactor, an experimental prompt — without overwriting the original session's own resumability if the experiment goes wrong |

`[NUM]` — the practical decision rule this table encodes is threshold-shaped, not free-form: `/compact`
degrades quality gradually (one summarisation, some detail lost, per the leaf above) while `/clear` and
a fresh session cost nothing in tokens but the full loss of the surviving-list categories from the
second leaf in this file. There is no operation on this table that is "safe by default" — each trades
a specific, nameable class of continuity for a specific, nameable savings.

**Insight:** `--fork-session` is not a fifth kind of reset alongside the other three — verified
against `cli-reference` for this leaf, its own description is "When resuming, create a new session ID
instead of reusing the original," which only makes sense paired with `--resume` or `--continue`. It
answers a different question than the other three ("which session ID do I mutate going forward?"), not
"how much context survives?" — forking a session and then immediately compacting the fork still loses
exactly what compacting anything else loses.

**Pitfall:** reaching for `/clear` to "clean up" a long session that is still mid-task, on the belief
that a shorter context is strictly better. **Symptom:** the next turn has no idea what the task even
was, because `/clear` does not summarise — it deletes. **Fix:** `/compact` is the operation for a
long-but-unfinished task; `/clear` is for a task that has actually ended. **Why people believe it:**
both commands visibly shrink the token count in `/context`, so they look interchangeable from the
outside; only one of the two preserves a summary of what happened.

> `/compact`, `/clear`, a fresh session, and `--fork-session` all shrink or replace a session's
> context, but they trade away different things — a lossy summary, the whole transcript, the whole
> transcript plus session identity, and a new identity for an otherwise-intact copy, respectively — so
> the choice is driven by whether the task is unfinished, finished, unrelated, or merely risky, not by
> which command is fastest to type.

## Pitfalls

- **Belief:** `/compact` and autocompaction are the same feature, so disabling one disables both.
  **Surprising outcome:** `autoCompactEnabled: false` in settings, and the session still compacts the
  moment someone types `/compact` by hand.
  **What actually gets the guarantee:** treat them as two triggers on the same mechanism — a policy
  and a command — and disable or guard each independently.
  **Why people believe it:** both produce the identical artefact (a summary replacing the transcript),
  so the trigger difference is invisible unless you go looking for it.

- **Belief:** a fact stated clearly in the conversation will still be "in there somewhere" after a
  compaction, because the model wrote a summary and summaries are supposed to keep the important
  parts.
  **Surprising outcome:** the summarisation call is itself a single, imperfect pass over a long
  transcript, and it has no way to know which specific detail the user will need three turns later —
  it optimises for a plausible overview, not for preserving every fact a future turn might query.
  **What actually gets the guarantee:** only `CLAUDE.md`, in-budget skill invocations, and anything a
  `PreCompact` hook explicitly wrote to disk are guaranteed; everything else riding on the summary's
  judgment is a bet, not a guarantee.
  **Why people believe it:** "summary" implies a deliberate act of selection, which suggests
  correctness; it is closer to a lossy compression than a curated archive.

- **Belief:** writing a `PreCompact` hook that saves a checkpoint file solves the data-loss problem on
  its own.
  **Surprising outcome:** the checkpoint exists, correctly, on disk — and the next turn behaves as if
  it doesn't, because nothing read it back into context.
  **What actually gets the guarantee:** pair the `PreCompact` write with a `SessionStart` hook matched
  on `compact`, or an explicit `CLAUDE.md` instruction to check the checkpoint directory.
  **Why people believe it:** the hook clearly "fired" — its own exit code and log line prove that —
  and it is easy to conflate "the hook ran" with "the information is back in context."

## Cheat sheet

| Question | Answer |
|---|---|
| Two settings that control autocompaction | `autoCompactEnabled` (bool), `autoCompactWindow` (`auto` or 100k–1M tokens) |
| Session-scoped override, no settings-file edit | `claude --autocompact 500k` |
| What survives a compaction | Project-root `CLAUDE.md` (re-read from disk) + most recent invocation of each skill, 5,000 tok cap each / 25,000 combined |
| What never survives | Anything that lived only as conversation text |
| Hook that can block a compaction outright | `PreCompact`, exit code `2` |
| Hook that fires after, cannot block | `PostCompact` |
| Matcher values for both compaction hooks | `manual`, `auto` |
| `/compact` | Summarise, keep working in the same thread |
| `/clear` | Delete, task is actually finished |
| Fresh session | Delete + new identity, switching projects entirely |
| `--fork-session` (with `--resume`/`--continue`) | Copy into a new ID, try something risky without touching the original |

## Self-test

1. Does turning `autoCompactEnabled` off in settings also disable the `/compact` command?
<details><summary>Answer</summary>
No. `autoCompactEnabled` only controls the background policy tied to `autoCompactWindow`. `/compact`
is a separate, explicit trigger on the same underlying summarisation mechanism, and it still works
with autocompaction fully disabled.
</details>

2. What value forms does `autoCompactWindow` / `--autocompact` accept, and what is notably absent from
   that list given the setting's own description?
<details><summary>Answer</summary>
It accepts the literal `auto` or an explicit token threshold between 100k and 1M tokens (confirmed
against the installed `claude --help` for v2.1.251). A bare percentage is notably absent, even though
the setting's own description reads "how full the context gets," which reads like a percentage.
</details>

3. Name the two categories that survive a compaction, with their exact numeric limits where they have
   one.
<details><summary>Answer</summary>
The project-root `CLAUDE.md`, re-read from disk with no numeric cap of its own, and the most recent
invocation of each skill, capped at 5,000 tokens per skill and 25,000 tokens combined, kept
newest-first when the combined cap is exceeded.
</details>

4. Why can a `PostCompact` hook not block anything, while a `PreCompact` hook can?
<details><summary>Answer</summary>
`PreCompact` fires before the summarisation call runs, so exiting with status `2` can stop that call
from happening at all. `PostCompact` fires only after the compaction has already completed — there is
nothing left in that moment for a block to prevent.
</details>

5. A `PreCompact` hook writes a checkpoint file every time it fires, correctly and reliably. Is that
   enough to guarantee the checkpoint's contents are usable by the next turn? Why or why not?
<details><summary>Answer</summary>
No. Writing the file is a guarantee; getting it read back into context is a separate step that
`PreCompact` does not perform on its own. It needs a matching `SessionStart` hook on the `compact`
matcher, or an explicit instruction in `CLAUDE.md` telling the model to check the checkpoint directory.
</details>

6. A task is genuinely finished and the next task is unrelated. Which of the four resets in this file
   is the right one, and why not `/compact` instead?
<details><summary>Answer</summary>
`/clear`. `/compact` produces a summary of the old task that would be pure noise inside an unrelated
new task — there is nothing in the old task worth carrying forward as a summary, so paying the
summarisation cost buys nothing.
</details>

7. What does `--fork-session` actually change, and what does it leave completely unaffected?
<details><summary>Answer</summary>
It changes which session ID subsequent turns are written to — a new ID is created and the session's
state is copied into it — used with `--resume` or `--continue`. It leaves the amount of context that
survives completely unaffected: forking then compacting still loses exactly what compacting anything
else loses, because forking answers "which session gets mutated," not "how much survives."
</details>

## Open questions

- **Unverified:** whether the `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` environment variable exists in Claude
  Code v2.1.2xx, its exact spelling, and what it overrides. Not found on `settings-reference` or
  `cli-reference`; `claude --help` exposes no environment-variable table to check it against directly.
  Would be settled by the `env-vars` documentation page, which is outside this leaf's permitted page
  set (`settings`, `settings-reference`, `permissions`, `hooks`, `sub-agents`, `skills`, `memory`,
  `plugins`, `cli-reference`).

---

**Leaves covered:** 2.6.5–2.6.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-62 in the previous file ranks the costs, D-27 and D-17 in PARTs 1 and 0 draw compaction and the reset semantics, and D-73 in §3.2 walks the budget mechanically
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 436
