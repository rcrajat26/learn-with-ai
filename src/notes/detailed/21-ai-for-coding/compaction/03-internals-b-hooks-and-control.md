# 21 AI for Coding — compaction hooks and control — ADVANCED (INTERNALS) (§3.2.5–3.2.7)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [the compaction budget](03-internals-a-the-budget.md) · Next: [the permission-evaluation pipeline](../permission-evaluation/03-internals-a-the-pipeline.md)

The previous file established the mechanism: compaction is one summarization call that replaces the
transcript, its threshold is a session-resolved fraction of the window rather than a published
constant, `CLAUDE.md` reloads from disk on the other side, and skills survive only through a
5,000/25,000-token recency budget. Everything in that list is either automatic or explicitly bounded.
This file is about the part that is neither: whatever a session was holding that fits none of those
categories — an in-progress plan, a half-finished review, a decision made once in chat and never
written down. §2.3.1 already established, in the hooks area, that a hook is the only *guaranteed*
seam in the whole harness; §2.3.6 named `PreCompact` and `PostCompact` as the two lifecycle events
sitting on either side of this exact mechanism. This file is what a project can actually do with
that seam — precisely bounded, because the seam is smaller than it first looks.

### 1. What is irrecoverably lost, and the fix: put it in a file, not in a message

**Mental model.** The previous file's summary is a single pass, made once, by a model that does not
know which detail the *next* turn will need. Treat every fact that exists only as chat text the way
you would treat a whiteboard note the night before an office move — legible right now, and gone the
moment nobody thought to photograph it, because nothing about "the movers are lossy" tells you which
particular note they will decide is worth keeping.

**Why it exists as a distinct question.** Concept 4 of the previous file drew the survivor list in
full: project-root `CLAUDE.md`, unconditionally, and the single most recent invocation of each skill,
bounded. Everything not on that list rides entirely on the summarization pass's judgment, and that
pass optimizes for a plausible overview of a conversation, not for preserving a specific fact a later
turn will query. The gap this concept names precisely: an in-progress checklist, a partial diff
review, a set of files already inspected in a long refactor — none of these are `CLAUDE.md`, none of
them are a skill invocation, so none of them get a guarantee, no matter how many times they were
restated in chat.

**How it works.** There is no mechanism that widens the survivor list — the fix is procedural, not a
setting. `[TRAP]` The wrong belief is specific enough to name directly:

**Pitfall:** the wrong belief is "the assistant clearly registered this, it even repeated it back to
me, so it will still know it after a compaction." **Symptom:** three turns after an automatic
compaction fires, the assistant re-asks a question that was already answered, or repeats work that
was already done, because the fact lived only in messages the summarization pass condensed away or
never surfaced in the summary it produced. **Fix:** anything that must survive has to land on disk
before the compaction happens — in the project-root `CLAUDE.md` if it is a durable, reusable rule, or
in a file a `PreCompact` hook writes if it is transient, task-specific, in-progress state that does
not belong in `CLAUDE.md` at all. A fact typed into chat, however many times, is not on that list
until something moves it off the transcript and onto the filesystem.

`context-economy/02-bounding-and-compaction.md` already gave the three-step checklist this pitfall
implies — durable facts into `CLAUDE.md`, skills re-invoked before an expected compaction, everything
else onto disk by hand or by hook — and this file does not repeat it. What that file left as its
third step, "write it to a file yourself, or let a `PreCompact` hook do it automatically," is what
concept 2 below builds in full, because "let a hook do it" is doing a lot of unexamined work in that
sentence: a hook can write the file, but writing the file is not the whole guarantee, as concept 2's
gotcha shows.

**Code.** No settings key changes what survives. The only artifact this concept has to offer is the
negative case — a `CLAUDE.md` entry that *looks* like it solves this and does not:

```markdown
## Session notes
Remember: the refactor in progress touches only `billing/` and `shipping/` is out of scope.
```

Writing "remember" into a durable, always-loaded file for a fact that is true only for *this*
refactor pollutes every future session that reads the same `CLAUDE.md` after the refactor ships —
concept 1's fix is "put transient state in a file," not "put transient state in `CLAUDE.md`
specifically." The distinction matters enough to state as its own line: `CLAUDE.md` is for what is
always true; a `PreCompact` checkpoint is for what is true right now.

**Gotcha.** Restating a fact more emphatically, or more often, does not change which category it
falls into. Ten mentions of a decision across a session are still zero mentions on disk, and the
summarization pass treats all ten identically to one.

> Anything that exists only as conversation text is not guaranteed to survive a compaction no matter
> how clearly it was stated or how many times — the only two guarantees are the project-root
> `CLAUDE.md`, reloaded from disk, and the recency-bounded skill budget; everything else has to be
> moved onto disk, deliberately, before the compaction fires.

### 2. `PreCompact` and `SessionStart` as the persistence seam: a worked handoff-note round trip

**Mental model.** A `PreCompact` hook is a fire warden's checklist read out one minute before an
evacuation: it guarantees the warden calls out what to grab, every time, on schedule. It does not
guarantee anyone is standing at the exit to receive the things being handed out — that has to be a
second, separately-staffed post.

**Why it exists.** Concept 1 named the gap: transient, task-specific state that belongs in neither
`CLAUDE.md` nor a skill invocation. `PreCompact` is the harness's only guaranteed callback at the
exact moment before that state is about to be summarized away, which makes it the only place a
project can reliably intervene rather than hoping the model remembers to write a checkpoint on its
own initiative.

**How it works.** `[DOC]` `hooks`, re-fetched immediately before writing this leaf, states the shape
of both halves of the round trip this concept builds. `PreCompact`'s matcher values are `manual` and
`auto`, distinguishing a typed `/compact` from an automatic trigger. Critically, re-fetching the
page's own "Exit code 2 behavior per event" table for this leaf finds `PreCompact` **absent from it
entirely** — the table enumerates `PreToolUse`, `PermissionRequest`, `UserPromptSubmit`,
`UserPromptExpansion`, `Stop`, `SubagentStop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`,
`ConfigChange`, `StopFailure`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, and
`PermissionDenied`, and no compaction event appears on it. **This file therefore treats `PreCompact`
as unable to block a compaction via exit code 2**, and flags that this diverges from
`context-economy/02-bounding-and-compaction.md`'s claim that "exiting the hook command with status 2
prevents the compaction from proceeding at all." This file follows the freshly re-verified table over
the sibling file's claim; the sibling file's dedicated `PreCompact` prose section could not be
retrieved intact on this pass either, so the divergence is recorded in `## Open questions` rather than
stated as a settled correction. What is settled either way: **`PreCompact` cannot choose what the
summary keeps** — the summarization call runs on its own logic regardless of anything the hook does —
so its only reliable job is persistence, not curation, whether or not it can also block.

The other half of the round trip is the read side concept 1's pitfall named as commonly skipped.
`SessionStart` supports a `compact` matcher — "Session is starting after automatic context
compaction" — and its documented output shape is exactly the injection mechanism this concept needs:

> "`SessionStart` hooks can return `additionalContext` to inject text into the session context, where
> Claude will see it as system information about the environment or session state."

with the JSON shape, quoted verbatim from `hooks`:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Environment ready. Node v18.0.0 installed. Database connection established."
  }
}
```

`[BUILD]` This is the artefact: a write half and a read half, wired to the same fixed filename so the
read half never has to guess which checkpoint is current. This is a **different artefact** from
`context-economy/02-bounding-and-compaction.md`'s `checklist-refresh.sh`, not an extension of it —
that script writes a timestamped file (`pre-compact-$(date +%Y%m%dT%H%M%S).md`) and stops there,
which is exactly the half that file's own gotcha flags as insufficient ("getting it read back into
context still requires... a `SessionStart` hook"). A timestamped filename also has no "latest"
pointer a second script could find without first listing a directory, so the write side below uses a
single fixed name instead, deliberately, to make the read side trivial:

`.claude/hooks/handoff-write.sh` — the `PreCompact` hook:

```bash
#!/usr/bin/env bash
set -euo pipefail

# handoff-write.sh — PreCompact hook. Writes a fixed-name handoff note before
# compaction discards the turns it was drawn from. Fixed name (not timestamped)
# so handoff-read.sh, run from SessionStart, always knows where to look without
# listing a directory first.

input_json="$(cat)"
trigger="$(echo "$input_json" | jq -r '.hook_event_name // "PreCompact"')"
matcher_source="$(echo "$input_json" | jq -r '.matcher // "unknown"')"
transcript_path="$(echo "$input_json" | jq -r '.transcript_path // empty')"

checkpoint_dir=".claude/checkpoints"
mkdir -p "$checkpoint_dir"
handoff_file="$checkpoint_dir/handoff-latest.md"

recent_turns=""
if [[ -n "$transcript_path" && -r "$transcript_path" ]]; then
  recent_turns="$(tail -n 20 "$transcript_path" 2>/dev/null || true)"
fi

{
  echo "# Handoff note"
  echo "Written by: $trigger ($matcher_source)"
  echo "Written at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Last 20 transcript lines before compaction"
  echo '```'
  if [[ -n "$recent_turns" ]]; then
    echo "$recent_turns"
  else
    echo "(transcript unreadable at hook time)"
  fi
  echo '```'
} > "$handoff_file"

echo "Handoff note written to $handoff_file" >&2
exit 0
```

`.claude/hooks/handoff-read.sh` — the `SessionStart` hook, matched on `compact`, closing the loop:

```bash
#!/usr/bin/env bash
set -euo pipefail

# handoff-read.sh — SessionStart hook, matcher "compact". Reads the fixed-name
# handoff note handoff-write.sh left behind and re-injects it via
# hookSpecificOutput.additionalContext, then removes the note so a session that
# starts normally next time does not see a stale one.

handoff_file=".claude/checkpoints/handoff-latest.md"

if [[ ! -f "$handoff_file" ]]; then
  exit 0
fi

content="$(cat "$handoff_file")"
rm -f "$handoff_file"

jq -n --arg ctx "$content" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $ctx
  }
}'
```

The complete, valid `settings.json` wiring both halves — this is the whole file, not a fragment:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/handoff-write.sh" }
        ]
      },
      {
        "matcher": "manual",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/handoff-write.sh" }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/handoff-read.sh" }
        ]
      }
    ]
  }
}
```

**Prove step**, firing both halves directly with representative stdin rather than waiting on a real
compaction:

```
$ echo '{"hook_event_name":"PreCompact","matcher":"auto","transcript_path":"/tmp/fake-transcript.jsonl"}' \
    | bash .claude/hooks/handoff-write.sh
Handoff note written to .claude/checkpoints/handoff-latest.md

$ bash .claude/hooks/handoff-read.sh
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "# Handoff note\nWritten by: PreCompact (auto)\nWritten at: 2026-08-30T09:15:00Z\n\n## Last 20 transcript lines before compaction\n```\n(transcript unreadable at hook time)\n```\n"
  }
}

$ ls .claude/checkpoints/handoff-latest.md
ls: .claude/checkpoints/handoff-latest.md: No such file or directory
```

The last line is deliberate, not an oversight: `handoff-read.sh` deletes the note after consuming it,
so a session that starts normally (matcher `startup`, not `compact`) never runs this hook at all, and
a *second* consecutive compaction does not re-inject an already-stale note from three compactions ago.

**What this costs.** Both halves run as local shell commands, not model calls, so writing and
deleting the note costs zero tokens beyond the compaction's own summarization cost from the previous
file. The cost this round trip *does* add is on the very next turn after a compaction: whatever text
`additionalContext` injects is sent on that turn like any other system content, so a 20-line handoff
note of a few hundred tokens costs a few hundred tokens once, on the first post-compaction turn — a
one-time, bounded charge, in exchange for not silently losing the state concept 1 named.

**Gotcha.** The read half only fires on the `compact` matcher. A manually-typed `/clear` or a fresh
session both start with matcher `startup` or `clear`, neither of which triggers `handoff-read.sh` —
which is correct, not a bug: concept 1's fix is for state that should survive a *compaction*
specifically, and `/clear`'s own contract (§2.6.8's four-resets table) is that it deletes on purpose.
Wiring `handoff-read.sh` to fire on every `SessionStart` matcher regardless would reintroduce stale
task state into sessions that were deliberately started clean.

> A `PreCompact` hook guarantees a checkpoint gets written before a compaction discards the state that
> produced it; on its own that is only half a guarantee, because nothing about writing the file
> injects it back into context. The other half is a `SessionStart` hook matched on `compact`,
> returning `hookSpecificOutput.additionalContext` — the two halves paired, on a fixed filename, are
> what closes concept 1's gap, and `PreCompact` alone, however reliably it fires, does not.

### 3. Why a fresh session usually beats a thrice-compacted one, argued rather than asserted

**Mental model.** A single compaction summarizes a transcript. A *second* compaction on the same
session summarizes a transcript that is itself already a summary plus whatever survived by
guarantee — the input to pass two is qualitatively different from the input to pass one, the way a
photocopy of a photocopy degrades in a way a single photocopy does not, even though both are "just
compaction" by name.

**Why this needs an argument rather than a claim.** "A fresh session is cleaner" is the kind of
statement this whole notes set treats as documentation, not analysis, unless it carries its own cost
and its own escape hatch. `[PROVE]` Two independent arguments, each worked through rather than
asserted, and a third case where the claim does not hold.

**Argument 1 — the summarization cost compounds, arithmetically.** The previous file's insight
established that a compaction is itself one summarization call, charged in full on the triggering
turn, at whatever size the transcript has grown to. A session that compacts three times over its life
pays that cost three times, and each successive transcript is larger before it compacts again, because
the shortened-by-summary session keeps accumulating new turns on top of the summary until it refills
the window:

```
compaction 1 fires at ~150,000 tokens used  → summarization call costs  ~150,000 input tokens
compaction 2 fires at ~150,000 tokens used  → summarization call costs  ~150,000 input tokens
                                               (the summary from #1 plus new turns, refilled)
compaction 3 fires at ~150,000 tokens used  → summarization call costs  ~150,000 input tokens
                                               total summarization overhead: ~450,000 input tokens
```

Against that: concept 2's handoff note plus the project-root `CLAUDE.md` are the entire cost of
starting fresh instead — a few hundred to a few thousand tokens, once, on the first turn of the new
session, not three separate 150,000-token summarization calls spread across the old one's life. The
break-even is not close: three compactions' summarization overhead alone is one to two orders of
magnitude larger than one fresh start's re-orientation cost, before counting anything the summaries
themselves left out.

**Argument 2 — fidelity loss compounds independently of cost, and is not recoverable by any later
pass.** Compaction 2 does not re-read the original conversation; concept 1 in the previous file
established that the transcript is *replaced*, not archived alongside its summary. So compaction 2's
only input, for everything except the guaranteed survivors, is compaction 1's own lossy output. A
detail compaction 1 judged unimportant enough to drop is not recoverable by compaction 2, however
important it turns out to be later — there is nothing left for compaction 2 to reconsider it against.
Three compactions are not three independent 25%-ish chances a detail survives; they are one chance,
at compaction 1, with compactions 2 and 3 only able to further compress whatever already made it that
far. `D-27` (`memory/03-auto-memory.md`) draws exactly this asymmetry for `CLAUDE.md` specifically —
the one category that resets to the same disk copy every time rather than compounding — which is the
mechanical reason the guaranteed survivors do not degrade this way and everything else does.

The skill budget compounds the same way from a different angle. `D-73c` (previous file) showed a
single compaction evicting two of six invoked skills outright once the 25,000-token combined cap is
reached. A session that has already compacted twice, and invoked further skills in between each time,
is repeating that eviction against an already-thinned set of survivors — the newest-first rule has no
memory of which skill was evicted at compaction 1 versus still present at compaction 2; it just reapplies
the same recency cutoff to whatever is currently invoked, so a skill's guidance can quietly vanish and
never come back even though nothing about the skill itself changed.

**The case where the claim does not hold.** `[NUM]` A session that has compacted exactly once, with a
`PreCompact`/`SessionStart` round trip from concept 2 in place, and no long-tail of chat-only facts
that predate the compaction, is not meaningfully worse than fresh — its one summarization cost is
already paid, its guaranteed survivors reloaded correctly, and its handoff note covered the rest. The
argument above is about *thrice*-compacted specifically: it is the compounding across repeated passes,
not compaction itself, that degrades. One compaction is the intended steady state this whole area is
built around; three in the same session is usually a sign the task should have been split, or that
`/clear` (task actually finished) or a fresh session (task unrelated) was the correct §2.6.8 choice
several turns earlier than it was actually made.

**Interview:** *"If compaction preserves `CLAUDE.md` and skills, why would a fresh session ever beat
compacting again?"* Because the two guaranteed categories are the only things that don't compound
loss across repeated compactions — everything else is being summarized from an already-summarized
input, and the cost of each additional summarization call is not small: roughly the size of whatever
the transcript refilled to, paid again and again, versus a bounded one-time re-orientation cost for a
fresh start.

> A single compaction is the mechanism working as designed. A third compaction on the same session
> summarizes an already-lossy input at a cost comparable to several fresh-session restarts combined,
> while recovering none of what the first pass already discarded — so the case for a fresh session
> over a thrice-compacted one is a compounding argument, not a preference: two independent costs
> (summarization tokens, and unrecoverable fidelity) both scale with repeated passes in a way a fresh
> start's bounded re-orientation cost does not.

## Pitfalls

- **Belief:** stating something clearly in chat, even repeatedly, is enough for it to survive a
  compaction because the summary is supposed to capture what matters.
  **Surprising outcome:** the summarization pass has no way to know which specific detail a later
  turn will need, and chat-only facts are outside both guaranteed-survivor categories entirely.
  **What actually gets the guarantee:** move it onto disk — `CLAUDE.md` if durable, a `PreCompact`
  checkpoint if transient — before the compaction happens.
  **Why people believe it:** "summary" implies deliberate selection of what matters, which reads as
  safety; it is closer to lossy compression than curated preservation.

- **Belief:** a `PreCompact` hook that writes a checkpoint file has solved the persistence problem
  on its own.
  **Surprising outcome:** the file exists, correctly, every time — and the very next turn behaves as
  if it doesn't, because nothing reads it back into context automatically.
  **What actually gets the guarantee:** pair it with a `SessionStart` hook matched on `compact`,
  returning `hookSpecificOutput.additionalContext`, as concept 2 builds in full.
  **Why people believe it:** the hook's own exit code and log line prove it ran, and it is easy to
  conflate "the hook fired" with "the information is back in the model's input."

- **Belief:** `PreCompact` can be used to stop an unwanted compaction outright with exit code 2, the
  way `PreToolUse` blocks a tool call.
  **Surprising outcome:** re-verifying `hooks`'s own "Exit code 2 behavior per event" table for this
  leaf finds no `PreCompact` row in it at all, and this file could not retrieve a dedicated
  `PreCompact` prose section confirming blocking either way — see `## Open questions`.
  **What actually gets the guarantee:** treat `PreCompact` as a persistence seam, not a veto; if a
  compaction must not happen at a given moment, control it upstream via `autoCompactWindow` or by not
  typing `/compact`, not by trying to cancel it from inside the hook.
  **Why people believe it:** several other lifecycle events in the same table (`PreToolUse`,
  `UserPromptSubmit`, `Stop`) do block on exit code 2, so it reads as a general hook capability rather
  than an event-specific one.

## Cheat sheet

| Question | Answer |
|---|---|
| What survives without any hook | Project-root `CLAUDE.md` (reload) + most recent skill invocation within 5,000/25,000-token budget |
| What needs a hook to survive | Any transient, task-specific in-progress state — a checklist, a partial review, a decision made once in chat |
| Hook that writes a checkpoint | `PreCompact`, matcher `auto` or `manual` |
| Hook that re-injects it | `SessionStart`, matcher `compact`, via `hookSpecificOutput.additionalContext` |
| Does `PreCompact` block the compaction? | No confirmed exit-code-2 blocking row for it in `hooks`'s table — treat it as persistence-only |
| Cost of the write half | Zero tokens — a local shell command, not a model call |
| Cost of the read half | Whatever the injected `additionalContext` text costs, once, on the first post-compaction turn |
| One compaction vs three | One is the designed steady state; three compounds both summarization cost and unrecoverable fidelity loss |
| When a fresh session beats compacting again | After repeated compactions on the same session, or when `/clear`/fresh session was already the right §2.6.8 choice |

## Self-test

1. Why doesn't restating a fact three times in chat improve its odds of surviving a compaction?
<details><summary>Answer</summary>
Because the summarization pass treats chat-only content as a single undifferentiated input regardless
of repetition, and neither guaranteed-survivor category (project-root `CLAUDE.md`, in-budget skill
invocations) is defined by how often something was said in conversation. Repetition changes nothing
about which category the fact falls into.
</details>

2. A `PreCompact` hook writes a checkpoint file every time it fires. Is that sufficient on its own to
   get the checkpoint back into the model's context after the compaction? What else is needed?
<details><summary>Answer</summary>
No. Writing the file is only the persistence half of the guarantee. Getting it read back into context
requires a second hook — `SessionStart` matched on `compact` — that reads the file and returns
`hookSpecificOutput.additionalContext`, or an explicit `CLAUDE.md` instruction telling the model to
check the checkpoint location itself.
</details>

3. Why does `handoff-write.sh` in this file use a fixed filename (`handoff-latest.md`) instead of a
   timestamped one?
<details><summary>Answer</summary>
So the paired `SessionStart` read-side hook always knows exactly where to look without first listing
a directory to find the most recent file. A timestamped filename (as in the sibling
`checklist-refresh.sh`) has no built-in "latest" pointer for a second script to consume automatically.
</details>

4. Does this file confirm or deny that `PreCompact` can block a compaction with exit code 2?
<details><summary>Answer</summary>
It finds no `PreCompact` row in `hooks`'s "Exit code 2 behavior per event" table on re-verification,
which this file treats as evidence against blocking support, while noting it could not retrieve
`PreCompact`'s own dedicated prose section to settle the question definitively — recorded as an open
question rather than a flat denial, and flagged as a divergence from a sibling file's stronger claim.
</details>

5. Give the two independent reasons a session that has compacted three times is argued to be worse
   than a fresh session with a good handoff note, not merely asserted to be worse.
<details><summary>Answer</summary>
First, cost: each compaction is a full summarization call charged at the transcript's current size, so
three compactions pay that cost three times — arithmetically far larger than one bounded
re-orientation cost for a fresh start. Second, fidelity: compaction 2 summarizes compaction 1's output,
not the original conversation, so anything compaction 1 already dropped cannot be recovered by any
later pass — the loss compounds one-directionally rather than resetting each time.
</details>

6. Under what circumstance does the "fresh session beats compaction" argument in this file *not* hold?
<details><summary>Answer</summary>
After exactly one compaction, especially with a `PreCompact`/`SessionStart` handoff round trip already
in place — one compaction is the intended steady state, and its one-time summarization cost and
fidelity loss are not yet compounded by a second or third pass.
</details>

7. Why does `handoff-read.sh` delete the checkpoint file immediately after reading it?
<details><summary>Answer</summary>
So a subsequent `SessionStart` that is not matcher `compact` (a plain `startup` or a `/clear`) never
encounters a stale note from an earlier compaction, and so a second consecutive compaction's read-back
does not re-inject an already-consumed, now-outdated handoff note.
</details>

## Open questions

- **Unverified:** whether `PreCompact` has any exit-code-based blocking capability at all. Re-fetching
  `hooks`'s "Exit code 2 behavior per event" table for this leaf finds no `PreCompact` row, which this
  file treats as evidence against blocking, but repeated fetches of the page could not retrieve
  `PreCompact`'s own dedicated prose section intact to confirm this directly (the page truncates
  before that section in every fetch attempted). This directly diverges from
  `context-economy/02-bounding-and-compaction.md`'s claim that "exiting the hook command with status 2
  prevents the compaction from proceeding at all." Would be settled by a direct, complete fetch of the
  `PreCompact` section of `hooks`, or by observing the behavior against a live compaction.

---

**Leaves covered:** 3.2.5–3.2.7 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-73 in the previous file draws the budget, and D-27 in `memory/03-auto-memory.md` draws what survives
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 483
