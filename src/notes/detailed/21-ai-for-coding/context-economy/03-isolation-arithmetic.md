# 21 AI for Coding — isolation arithmetic — INTERMEDIATE (§2.6.9–2.6.12)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [bounding output and compaction in practice](02-bounding-and-compaction.md) · Next: [plan mode and test-first](../practices/01-plan-mode-and-test-first.md)

The previous two files in this area measured a session and bounded what grows inside it. This file
closes context economy with the one lever that changes the *shape* of a session rather than trimming
it — where you put the work in the first place — and turns two arguments this guide already made
once, quickly, into budgeting rules you actually apply: §0.2.8's cache mechanism restated as a
session-shape habit, and §2.1.19's subagent cost model restated as the decision you make before you
dispatch, not after.

## §2.6.9 Session shape and the cache: why append-only stays cheap and a pause is not free

**Mental model.** Think of the cached prefix as a stack of paper the API keeps warm on a shelf,
already read once. Every turn that only adds a new page on top costs almost nothing — the shelf copy
is reused. Every turn that instead walks back and rewrites a page already on the shelf forces the
whole stack above that page to be re-read from scratch. Session shape is just the discipline of never
walking back, and the TTL is the shelf's expiry clock: leave the room too long and the shelf gets
cleared before you return.

**Why it exists.** §0.2.8 already established the mechanism: a cache read is billed at roughly 10% of
the standard input rate, matched against an exact, unchanged prefix, and the cache expires after a
period of inactivity — one hour for the main conversation on a subscription, five minutes everywhere
else, both overridable via `promptCacheTtl` / `subagentPromptCacheTtl` (v2.1.242+). This leaf is not
re-deriving that mechanism. It is turning it into the one practical question a reader actually asks
mid-session: **given that mechanism, what session shape keeps a long session cheap, and what does
one idle gap actually cost when it crosses the TTL?**

**When to reach for it, and when this doesn't help.** Append-only conversation shape is free to
maintain — it is simply not editing `CLAUDE.md`, not switching models, not disconnecting an MCP
server, and not letting the terminal sit idle past the TTL mid-task. It buys nothing, however, once a
session is already long enough that the *quadratic* re-send cost from §0.2.6 dominates — a long
append-only session still re-sends its whole (cheaply-cached) history every turn, it is just billed
at 10% instead of 100%. Append-only shape and bounding/compaction (the previous file) solve two
different problems: one keeps a given transcript size cheap per turn, the other keeps the transcript
from growing unboundedly in the first place. Neither substitutes for the other.

**How it works, with the arithmetic printed.** Take a session sitting at turn 40 with a
180,000-token prefix already resident and cached — a realistic size for a long refactor session,
consistent with this note set's own worked examples (§2.4.7, §3.4.3). Two paths for the next turn:

```
normal turn, cache hit:
  180,000 tok read from cache at 0.10x base rate = 18,000 price-units

turn after a TTL-crossing idle gap, cache miss:
  180,000 tok reprocessed at full price          = 180,000 price-units
  (plus a fresh cache-write premium on the same 180,000 tok, which
   costs more than a plain input token per §0.2.8 — paid once, so a
   later turn can read this rebuilt prefix cheaply again)

ratio: 180,000 / 18,000 = 10x
```

That 10x is not a hypothetical worst case — it is the direct, mechanical consequence of the TTL
expiring: the moment the idle gap exceeds five minutes (the default outside the main conversation,
or the main conversation's own default off a subscription), the *entire* prefix loses its cache
credit on the very next call, not just the portion that changed, because nothing in this scenario
changed — only time passed. A session that takes three such coffee-break gaps across its life pays
that 10x multiplier three separate times, once per gap, each one sized to whatever the prefix had
grown to by that point in the session — which is why the same six-minute pause costs far more late
in a long session than it would on turn 2.

**Gotcha.** The 10x above is specific to this file's 180,000-token example, exactly the way §2.1.19's
2.0x was specific to its own worked numbers — the ratio is always `(prefix size at full price) /
(prefix size at 0.10x)`, which reduces to a flat **10x** regardless of how large the prefix actually
is, because both sides scale by the same prefix size. What changes session to session is not the
ratio but the absolute cost: a 20,000-token prefix crossing the TTL is a rounding error, a
180,000-token prefix crossing it is a genuinely expensive single call, and the only variable a reader
controls is *when* the gap happens, not whether the 10x multiplier applies.

**Interview:** "Why would stepping away from your terminal for a coffee cost more, in one request,
than the rest of a long session combined?" Because the cache TTL — five minutes by default outside a
subscription's main-conversation bucket — resets on every hit and expires on inactivity; crossing it
does not cost 10% more, it costs the entire prefix at full price on the very next call, and the
longer the session had grown before the pause, the larger that one call is. The fix is not "don't
take breaks" — it's knowing the number before you decide whether a long idle gap mid-task is worth
it, or whether `/compact`ing first (previous file) shrinks the prefix that would otherwise get
re-billed at full price.

> Append-only session shape keeps a long conversation's history at the cache-read rate (roughly 10%
> of base input price); anything that edits the prefix, or an idle gap that crosses the cache TTL
> (five minutes by default outside a subscription's main-conversation bucket), forces the entire
> prefix to be reprocessed at full price on the next call — a flat 10x per crossing, sized by however
> large the prefix had grown to be at that point.

## §2.6.10 Isolation as the primary lever, with the arithmetic worked as a budgeting rule

**Mental model.** §2.1.19 already showed where a subagent's 2× comes from — the fixed per-dispatch
tax nobody in the same conversation ever pays. This leaf asks the question that tax number does not
answer on its own: given that a subagent costs more in total tokens burned, when does isolating a
task still come out *cheaper for the session as a whole*? The answer turns on which ledger you're
reading — total tokens burned, or tokens that land in the parent's own re-sent transcript — and D-63
puts both ledgers on the page at once.

**Why it exists.** §0.2.6 already established that the parent's transcript is re-sent, in full, on
every subsequent turn until the next `/compact` or `/clear`. A large exploratory task run inline does
not cost "150,000 tokens once" — it costs 150,000 tokens *added permanently to the running total*
that every future turn re-pays. A subagent dispatch pays its own fixed tax once, but whatever it
burns internally never joins that running total at all; only its final message does.

**How it works, with the arithmetic printed.** Take the same 150,000-token exploration §2.1.19 used
for its Panel 2, and extend it across the next ten turns of the same session — the horizon that
actually determines whether isolating it was worth the fixed tax.

```
inline, running total over the next 10 turns:
  150,000 + 150,000 + 150,000 + 150,000 + 150,000
  + 150,000 + 150,000 + 150,000 + 150,000 + 150,000
  = 1,500,000 tok

isolated, stated honestly (subagent's own 2x cost from §2.1.19, not hidden):
  150,000 x 2 = 300,000 tok burned inside the subagent, discarded after
  ~200 words (roughly 260-300 tok) re-enter the parent transcript once,
  and that is the only figure the next 10 turns re-send

net comparison: 1,500,000 / 300,000 = 5x cheaper isolated,
  even after paying the subagent's own 2x cost honestly
```

![D-63 — Isolation arithmetic. The left column's running total is what people forget to add up.](../diagrams/D-63-isolation-arithmetic.svg)

**D-63** — Isolation arithmetic. The left column's running total is what people forget to add up.

**The decision rule.** Isolate a task when both of these hold:

1. **The task's output is much smaller than its input** — reading, searching, or exploring a large
   amount of material to produce a short answer, a summary, a verdict, or a small diff, rather than
   material the parent needs to keep reasoning over in full.
2. **The input, if kept inline, would persist in the transcript for the rest of the session** — not
   a one-off read that the very next message renders irrelevant, but exploration whose bulk would sit
   in the re-sent history for every remaining turn.

Isolation loses, and inline wins, in the cases the rule excludes on purpose:

| Case | Why isolation loses here |
|---|---|
| A small task (a few thousand tokens of work) | The fixed per-dispatch tax (§2.1.19: ~4,800 tok) is a larger share of a small task's total cost than the tax is worth paying to avoid — the task was never going to bloat the running total much even left inline. |
| The parent genuinely needs the intermediate detail | If the parent's next several turns have to reason over the specifics — which files, which line numbers, which failed attempts — a 200-word summary throws away exactly the material the parent needed; isolation trades detail for a smaller transcript, and here that trade is a net loss. |
| The task needs `AskUserQuestion` mid-task | Withheld from every subagent regardless of type or configuration (§2.1.14) — a task that genuinely needs to pause and ask the human something partway through cannot be dispatched as a subagent at all; the decision has to be resolved before dispatch and handed down as a settled fact, or the work has to stay inline where `AskUserQuestion` is available. |

**Pitfall:** "A subagent costs 2x, so I should do the work inline instead and save tokens." The
premise is correct — §2.1.19 worked that 2x honestly, it is not exaggerated. **Symptom:** the reader
keeps a 150,000-token exploration inline to "save" the subagent's fixed tax, and that exploration now
sits in the transcript being re-sent on all ten of the next turns, for a running total of 1,500,000
tokens — five times what isolating it would have cost even after paying the 2x. **Fix:** the 2x and
the isolation win are two different ledgers (§2.1.19's own insight, restated here as the rule you
actually apply): total tokens burned end-to-end versus tokens that land in the parent's long-lived,
quadratically-re-sent transcript. A correct premise compared against the wrong quantity is exactly
how "subagents cost more" turns into the wrong conclusion for the one class of task — large,
exploratory, mostly-throwaway — where isolation wins by the widest margin.

**Interview:** "Doesn't isolating a task always cost more, since a subagent pays extra overhead a
same-conversation call never pays?" In total tokens burned, usually yes — state the 2x honestly. But
the number that decides most real dispatches is what re-enters the *parent's* transcript, because
that transcript is what gets re-sent every subsequent turn; a 150,000-token exploration returning a
200-word summary keeps the parent's running total roughly five times smaller over the next ten turns
than doing the same exploration inline, even counting the subagent's own 2x cost against it.

> Isolate a task when its output is much smaller than its input and that input would otherwise sit in
> the re-sent transcript for the rest of the session; keep it inline when the task is small, when the
> parent needs the intermediate detail rather than a summary, or when the task needs
> `AskUserQuestion` — a tool withheld from every subagent regardless of configuration.

## §2.6.11 A working session protocol, shipped as a `SessionStart` reminder

**Mental model.** A protocol that lives only as a paragraph the reader remembers to follow degrades
the same way any un-enforced discipline does — reliably, under deadline pressure, exactly when it
matters most. The fix already established for "what must be true no matter what the model or the
human decides" is a hook: a `SessionStart` handler that prints the five-step protocol into context at
the start of every session, so following it stops depending on memory.

**Why it exists.** Every piece is already covered individually elsewhere in this guide — `/context`
as a routine (§2.6.1), compacting at a task boundary rather than mid-task (previous file), `/clear`
per finished feature (previous file), a subagent for anything verbose (§2.6.10 above), and one file
per lane as this note set's own working convention. Nothing until now packaged the five into a single
artefact the reader actually runs.

**The artefact**, a complete `SessionStart` hook configuration plus the script it calls:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/session-protocol.sh"
          }
        ]
      }
    ]
  }
}
```

```bash
#!/usr/bin/env bash
set -euo pipefail

# session-protocol.sh — SessionStart hook. Injects the working session
# protocol as additionalContext so the five-step discipline is visible at
# the top of every session rather than depending on the reader remembering
# it. Fires on "startup" and "resume" only, not on "clear" or "compact" —
# those already get their own fresh-context treatment for other reasons.

input_json="$(cat)"
reason="$(echo "$input_json" | jq -r '.source // "startup"')"

protocol=$(cat <<'EOF'
Working session protocol for this project:
1. Run /context at the start of any session expected to run long.
2. Compact at a task boundary, once the current task is done, not mid-task.
3. /clear once a feature is genuinely finished, never to "tidy up" mid-task.
4. Dispatch a subagent for anything verbose whose output is much smaller
   than its input (a large read-and-summarize, a broad search) — keep small
   tasks and anything needing AskUserQuestion inline.
5. One file per lane: never write across a stage boundary you don't own.
EOF
)

jq -n --arg ctx "$protocol" --arg reason "$reason" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
```

**Prove step**, invoking the hook directly with a representative stdin payload rather than waiting on
a real session start:

```
$ echo '{"source":"startup"}' | bash .claude/hooks/session-protocol.sh
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Working session protocol for this project:\n1. Run /context at the start of any session expected to run long.\n2. Compact at a task boundary, once the current task is done, not mid-task.\n3. /clear once a feature is genuinely finished, never to \"tidy up\" mid-task.\n4. Dispatch a subagent for anything verbose whose output is much smaller\n   than its input (a large read-and-summarize, a broad search) — keep small\n   tasks and anything needing AskUserQuestion inline.\n5. One file per lane: never write across a stage boundary you don't own.",
    "reason": "startup"
  }
}
```

**What this costs.** The hook itself runs as a local shell command — zero model tokens to execute.
The `additionalContext` it injects, however, is not free: at roughly 120 tokens of protocol text,
injected once per session start via `startup|resume`, it becomes part of the prefix every subsequent
turn re-sends for the rest of that session, the same as any other early context (§0.2.11, D-10) — a
flat, small, one-time-per-session tax, not a recurring one paid per turn beyond that.

**Gotcha.** The matcher `startup|resume` deliberately excludes `clear` and `compact` — re-injecting
the protocol on every compaction would waste tokens restating something the model has already seen
once this session, and `/clear` already gets a fresh `CLAUDE.md` load that could carry the same
reminder if the reader prefers it live there instead of in a hook. A reader who wants the protocol
re-stated after every compaction specifically should broaden the matcher to `startup|resume|compact`,
trading a small recurring cost for a stronger guarantee against exactly the next leaf's trap.

> A working session protocol enforced only in prose is a discipline that degrades under pressure; a
> `SessionStart` hook matched on `startup|resume` that injects it as `additionalContext` makes the
> five-step routine — `/context` at start, compact at a boundary, `/clear` per feature, a subagent for
> anything verbose, one file per lane — visible every session for a flat, small, one-time cost rather
> than a memory the reader has to sustain on their own.

## §2.6.12 The trap: compacting mid-task instead of at a boundary

**Pitfall:** the belief in action is "the context is getting full, I should compact now" — treating
`/compact` as a pressure-relief valve to pull the moment `/context` looks uncomfortably high,
regardless of where the current task stands. **Symptom:** the compaction fires in the middle of a
multi-step task — say, three files into a five-file refactor, with two more files' worth of specific
line numbers, variable names, and half-finished edits still needed. The summary that replaces the
transcript keeps the *narrative* — "refactoring the payment module to use the new retry policy" — and
drops exactly the specifics the very next turn needed to keep going: which lines were already
touched, which edge case the third file's change was compensating for, what the fourth file's
existing code looked like before this session started reading it. The next turn does not fail loudly;
it proceeds confidently on a plausible-sounding but incomplete picture, which is the worse failure
mode — a wrong turn taken with confidence is harder to catch than an error message.

**Fix:** compact at a task boundary, not at a pressure threshold. If `/context` is uncomfortably full
*and* the current task is unfinished, the correct move is not `/compact` — it is to first write the
in-progress specifics somewhere that survives the compaction on purpose: a `PreCompact` hook
(previous file) that checkpoints the current file list and next steps to disk, or the reader manually
noting the remaining steps into a scratch file, *before* triggering the compact. Compacting a
finished task loses nothing that matters — the narrative is all that was ever going to be needed
again. Compacting an unfinished one bets that the model's own one-pass summary happened to preserve
the one specific fact the next several turns will actually need, and per the previous file's own
pitfall, a summary is a lossy compression optimized for a plausible overview, not a curated archive of
whatever the future asks for.

**Why people believe it:** `/context`'s percentage is the only signal most readers actively watch,
and it says nothing about task state — a session can be 85% full mid-task or 85% full between tasks,
and the number looks identical either way. Reacting to the percentage alone, rather than checking
whether the current task has actually finished first, is the natural mistake for exactly the reader
this guide's PART 0 built the `/context` habit for in the first place: it built the instrument, not
yet the judgment call about when reading it should trigger action versus when it should trigger a
checkpoint-then-compact instead.

**Interview:** "Your context is at 90% and you're two steps into a five-step migration. What do you
do?" Not a bare `/compact` — first checkpoint the specific state that matters (files touched, what's
left, any decision made only in conversation) to disk or via a `PreCompact` hook, then compact. The
threshold tells you compaction is coming soon regardless; task state tells you whether that
compaction is safe to take right now or needs a checkpoint first.

## Pitfalls

- **Belief in action:** "A subagent costs 2x, so doing a big exploratory task inline saves tokens."
  **Surprising outcome:** the 150,000-token exploration stays in the transcript and gets re-sent on
  every one of the next ten turns, for a running total of 1,500,000 tokens — five times what isolating
  it would have cost even counting the subagent's own honest 2x. **What actually gets the guarantee:**
  compare the right two ledgers — total tokens burned versus tokens landing in the parent's re-sent
  transcript — and isolate exactly the tasks whose output is much smaller than their input. **Why
  people believe it:** "2x" reads as a blanket verdict on subagents rather than a statement about one
  specific ledger, leaving the parent-transcript ledger — the one that usually decides the actual bill
  — unexamined.
- **Belief in action:** "Context is getting full, so I should `/compact` right now regardless of where
  the current task stands." **Surprising outcome:** the summary keeps the task's narrative and drops
  the specific line numbers, edge cases, and half-finished edits the very next turn needed, and the
  session proceeds confidently on an incomplete picture rather than failing loudly. **What actually
  gets the guarantee:** checkpoint the in-progress specifics to disk (a `PreCompact` hook, or a manual
  note) before compacting mid-task; compact freely once the task has actually finished. **Why people
  believe it:** `/context`'s percentage is the only signal most readers watch, and it carries no
  information about whether the current task is done.
- **Belief in action:** "A six-minute break mid-session is harmless — it's just a break." **Surprising
  outcome:** the cache TTL (five minutes by default outside a subscription's main-conversation bucket)
  has already expired, so the very next call reprocesses the entire prefix at full price — a flat 10x
  over the cached rate, sized by however large the prefix had grown to be. **What actually gets the
  guarantee:** know the TTL before stepping away mid-task, and either keep the gap under it or accept
  the one-time reprocessing cost consciously rather than by accident. **Why people believe it:** the
  break itself consumes no tokens, so the cost feels like it should be zero — it is not the break that
  costs, it is the cache-cold call immediately after it.

## Cheat sheet

| Question | Answer |
|---|---|
| Cache-read rate vs. full price | ~10% of base input rate; append-only shape keeps the whole prefix at this rate |
| Cost of crossing the TTL | Flat 10x on the whole prefix, at whatever size it had grown to — not just the changed portion, because nothing here changed except elapsed time |
| Default cache TTL outside subscription main-conversation | Five minutes (`promptCacheTtl` / `subagentPromptCacheTtl`, v2.1.242+, override to `5m`/`1h`) |
| Isolation net comparison (D-63) | 1,500,000 tok inline over 10 turns vs. 300,000 tok isolated (150K x 2, stated honestly) = **5x cheaper isolated** |
| Isolate when | output << input, and the input would otherwise sit in the re-sent transcript for the rest of the session |
| Keep inline when | task is small; parent needs the intermediate detail; task needs `AskUserQuestion` (withheld from every subagent, §2.1.14) |
| Session protocol, in order | `/context` at start -> compact at a task boundary -> `/clear` per finished feature -> subagent for anything verbose -> one file per lane |
| Protocol artefact | `SessionStart` hook, matcher `startup\|resume`, injects the protocol as `additionalContext` |
| Compaction trap | Compacting mid-task loses the specifics the summary doesn't know matter; checkpoint first, or compact only at a boundary |

## Self-test

1. A session's prefix has grown to 180,000 tokens. What is the token cost of the next call if it hits
   the cache, versus if a six-minute idle gap has just crossed the TTL?
<details><summary>Answer</summary>
Cache hit: 18,000 price-units (180,000 x 0.10). Cache miss after the TTL crossing: 180,000 price-units
at full price, plus a fresh cache-write premium on the same tokens — a flat 10x over the cached
figure, because the entire prefix loses its cache credit once the gap exceeds the TTL, not just the
part that changed (nothing changed except elapsed time).
</details>

2. Why is the 10x ratio in the previous answer independent of how large the prefix actually is?
<details><summary>Answer</summary>
The ratio is `(prefix size at full price) / (prefix size at 0.10x)`, and both the numerator and
denominator scale by the same prefix size, so it always reduces to 10x. What changes with prefix size
is the absolute cost of a crossing, not the ratio — a 20,000-token prefix crossing the TTL is a
rounding error, a 180,000-token one is a genuinely expensive single call.
</details>

3. D-63 compares 1,500,000 tok (inline, ten turns) against 300,000 tok (isolated, honest 2x). Walk the
   arithmetic that produces the 5x figure, and name the one thing the isolated side pays that the
   inline side never pays a fixed cost for.
<details><summary>Answer</summary>
Inline: 150,000 tok added to the transcript once, then re-sent on each of the next 10 turns, summing
to 1,500,000 tok. Isolated: the subagent burns 150,000 x 2 = 300,000 tok internally (the honest 2x
from §2.1.19), and only its ~200-word return re-enters the parent transcript once, so that figure —
not 150,000 — is what the next 10 turns re-send. 1,500,000 / 300,000 = 5x. The isolated side pays the
subagent's fixed per-dispatch tax (fresh system prompt, tool schemas, `CLAUDE.md`) that the inline
side never pays at all — it just doesn't matter here because the inline side pays a far larger,
recurring cost instead.
</details>

4. Name two situations where isolating a task is the wrong call even though its output is smaller
   than its input.
<details><summary>Answer</summary>
The task needs `AskUserQuestion` mid-task — withheld from every subagent regardless of configuration
(§2.1.14), so the decision has to be resolved before dispatch. Or the parent genuinely needs the
intermediate detail rather than a summary — a 200-word return throws away exactly the specifics the
parent's next several turns would have needed to keep reasoning correctly.
</details>

5. What does the `session-protocol.sh` `SessionStart` hook actually cost, given that the hook itself
   is a shell script and not a model call?
<details><summary>Answer</summary>
The script's own execution is free — zero model tokens. What is not free is the `additionalContext`
it injects (roughly 120 tokens of protocol text): once injected at session start, it becomes part of
the prefix every subsequent turn in that session re-sends, a flat one-time-per-session tax rather than
a recurring per-turn one.
</details>

6. Why is the matcher on the `session-protocol.sh` hook `startup|resume` rather than including
   `compact`?
<details><summary>Answer</summary>
Re-injecting the protocol on every compaction would restate something the model has already seen once
this session, at a small recurring cost each time. The matcher deliberately excludes `compact` to
avoid that repeated tax; a reader who wants the protocol re-asserted after every compaction specifically
can broaden the matcher to `startup|resume|compact` as a deliberate trade.
</details>

7. A session is at 90% context and mid-task, two steps into a five-step migration. What is the wrong
   move, and what is the right one?
<details><summary>Answer</summary>
Wrong: `/compact` immediately, because the resulting summary keeps the task's narrative and drops the
specific line numbers, edge cases, and half-finished edits the next steps need, and the session
proceeds confidently on an incomplete picture. Right: checkpoint the in-progress specifics first — a
`PreCompact` hook or a manual note of files touched and steps remaining — then compact.
</details>

8. Why does compacting a finished task lose "nothing that matters," while compacting an unfinished one
   is a bet?
<details><summary>Answer</summary>
A finished task's narrative — what was done and why — is all a summary was ever going to need to
preserve, since nothing further will query its specifics. An unfinished task still has specific facts
(exact line numbers, which edge case a change compensated for) that future turns will need, and the
summarisation call is a single, imperfect pass with no way to know in advance which specific detail
that will be — so relying on it to have preserved the right one is a bet, not a guarantee.
</details>

## Open questions

None.

---

**Leaves covered:** 2.6.9–2.6.12 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-63
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 432
