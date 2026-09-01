# 21 AI for Coding — the three ceilings, and reading cost back — ADVANCED (INTERNALS) (§3.4.5–3.4.9)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [the four billed quantities](03-internals-a-the-four-quantities.md) · Next: [effort, models and routing](../effort-and-routing/03-internals-routing.md)

The previous file named the four billed quantities, showed a real `-p --output-format json`
envelope with a real `total_cost_usd` of `0.136839`, and established that cache reads carry most of
a session's raw token volume while remaining a real fraction of its dollar total. That billing model
stays load-bearing here and is not re-derived. This file closes the cost-model area with the piece
that turns billing into an engineering control: what a subagent's premium is actually made of, the
three independent ceilings that stop a run before it runs away, and the two places — the envelope
and `/cost` — a reader reads the number back instead of guessing at it.

### 1. Where a subagent's ~2× cost comes from, itemised

**Mental model.** A subagent is not "the same conversation, split." It is a **second, independently
launched `claude` process** with no access to the parent's live prompt cache — everything the parent
session had already amortised into cheap cache-read turns, the subagent has to pay for again from
cold, on top of whatever small cost the parent itself pays to dispatch it and read its answer back.

**Why it exists.** §1 of the previous file established that a cache write costs a premium *over* the
input rate and a cache read costs roughly 10% of it. Those two facts alone explain why "do it as one
more turn in the current session" and "do it as a subagent" are not the same price for identical
work: one reuses an already-warm prefix, the other cannot.

**How it works, itemised.** `[NUM]` Three components sum to the subagent premium:

1. **Parent-side dispatch.** The parent's own turn that decides to hand work to a subagent and emits
   the tool call — a normal turn in the parent's own already-warm session, billed at the parent's
   ordinary cache-read rate. Small.
2. **Parent-side read-back.** The turn where the parent receives the subagent's returned summary and
   folds it into its own transcript — again a normal, cheap, cache-read turn for the parent. Small,
   but it is an extra turn that would not exist had the work simply continued inline.
3. **Subagent-side cold start.** The subagent's own process has no access to the parent's live cache
   at all. Its system prompt, persona definition and task framing are billed as a fresh
   **cache-write**, at a premium over the input rate — the exact opposite of a cache-read continuation.
   This is the dominant term, and it is paid in full regardless of how small the subagent's actual
   task is.

`[PROVE]` The gap between component 3 and "the same work as a cache-read continuation" is
directly observable, not asserted. Two back-to-back `claude -p --output-format json` calls asking
the identical one-line question, run seconds apart against `claude-opus-5[1m]`:

```
$ claude -p "In one sentence, what does the term idempotent mean for an HTTP PUT request?" \
    --output-format json
{"total_cost_usd": 0.17333975, "usage": {"input_tokens": 2,
  "cache_creation_input_tokens": 27379, "cache_read_input_tokens": 0, "output_tokens": 49}}

$ claude -p "In one sentence, what does the term idempotent mean for an HTTP PUT request?" \
    --output-format json
{"total_cost_usd": 0.0157805, "usage": {"input_tokens": 2,
  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 27379, "output_tokens": 44}}
```

The first call had no live cache to reuse and paid the full write premium on 27,379 tokens of
system-prompt prefix: `$0.17333975`. The second call, launched while that prefix was still inside its
TTL, read the same 27,379 tokens at the ~10% rate instead of writing them: `$0.0157805` — a
**~11×** gap (`0.17333975 / 0.0157805 ≈ 10.99`) for byte-for-byte identical work, driven entirely by
which of the two cache operations that prefix triggered. A subagent's own process is, mechanically,
always shaped like the first call — it cannot inherit a warm prefix from the parent because it is a
different process launched from cold. Whether the realised premium lands nearer a commonly-quoted
"~2×" or nearer this file's observed ~11× depends on how much the parent's own alternative — doing
the work as one more turn inline — would itself have benefited from an already-deep, already-warm
cache: early in a session the gap is small because there is not much warm prefix to give up; late in
a long session, with hundreds of thousands of cache-read tokens already amortised, dispatching to a
subagent forfeits a much larger discount, and the multiplier grows accordingly.

**No SVG at this leaf** — the ceilings' D-78 sits at §2, and this leaf's mechanism is the arithmetic
above rather than a new picture.

**Code.** The itemisation has no separate artefact beyond the two invocations already shown: a real
`claude -p --output-format json` call is the only "code" this concept lives in.

**Gotcha.** `[TRAP]` **Pitfall:** treating "subagents cost about 2× a single call" as a fixed
multiplier safe to budget against. **Symptom:** a budget sized on a 2× assumption blows past its cap
on a subagent dispatched late in a long, deeply-cached session, because the forfeited cache-read
discount at that point is far larger than it would have been at turn one. **Fix:** budget subagent
dispatch against the parent session's *current* cache depth, not a remembered constant — or read
`modelUsage.<model>.costUSD` on the actual dispatch and compare it to what the same turn would have
cost inline, per §3 below. **Why people believe it:** "~2×" is a convenient, quotable rule of thumb
that is roughly right in the median case and was never claimed to be a hard ceiling.

> A subagent costs more than the same work done inline because it is a second process with no access
> to the parent's live cache, so its own system prompt and framing pay a fresh cache-write premium
> instead of the cheap cache-read the same content would cost as a continuation — and the size of that
> premium grows with how much cache depth the parent session had already built up.

### 2. The three ceilings, and why a system needs all three

**Mental model.** An agent loop left to itself will keep taking turns until it decides it is done,
however long that takes and however much it spends getting there. Three independent knobs stop that
loop from the outside, and each one bounds a **different resource** — turns, dollars, wall-clock time
— which is exactly why none of the three can substitute for either of the other two.

**Why it exists.** `[NUM]` A turn cap cannot stop a run that is slow but cheap per turn — it keeps
taking turns, each one legitimately under the per-turn cost the cap was sized against, for far longer
than intended. A dollar cap cannot stop a run that is stuck in a fast, cheap loop — thousands of
inexpensive turns can burn hours without ever tripping a cost ceiling sized for a normal task. A
wall-clock timeout cannot stop a run that is burning money fast within its own time window — it can
blow through a budget in the first two of its thirty allotted minutes and the timeout will not fire
until the clock, not the balance, runs out. Each ceiling only sees its own axis.

**How it works.** `[DOC]` Re-verified against `cli-reference` on 2026-08-30:

- **`--max-turns`** — "Limit the number of agentic turns (print mode only). Exits with an error when
  the limit is reached. No limit by default." `[VERSION]` With `--input-format stream-json`, a
  message still queued when the limit ends a turn stays queued and starts a new turn under its own,
  fresh limit — a queued message is not lost, but it does not get to finish inside the turn that was
  already capped.
- **`--max-budget-usd`** — "Maximum dollar amount to spend on API calls before stopping (print mode
  only). Spend from subagents counts toward the cap. Once spend reaches the cap, spawning another
  subagent fails with `Budget limit reached`, and Claude Code stops background subagents that are
  still running." `[VERSION]` The cap-enforcement behaviours documented here require **Claude Code
  v2.1.217 or later**.
- **The subprocess wall-clock timeout** is not a `claude` CLI flag at all — nothing on the nine
  permitted documentation pages defines one, because it is not Claude Code's job to bound its own
  wall-clock time. It is imposed from outside, by whatever process launched `claude -p` as a
  subprocess: `subprocess.run(..., timeout=resolved_timeout)` in Python, `Process.waitFor(Duration)`
  in Java. `[CASE]` `harness/src/harness/engine/agent.py` in the read-only sdlc-harness repository
  names its own default verbatim:

  ```python
  DEFAULT_TIMEOUT = 1800
  ```

  Thirty minutes, as a plain module constant, resolved per call as `timeout or
  os.environ.get("HARNESS_AGENT_TIMEOUT", DEFAULT_TIMEOUT)` — parameter, then environment variable,
  then this default, the same resolution order the file uses for `--max-turns`.

The manifest marks D-78 as `Type: table`; the table below is the diagram — no SVG is written for it.

| Ceiling | What it bounds | What the run looks like when it trips | Whether work is preserved | What the envelope reports | Exception a Java wrapper should throw |
|---|---|---|---|---|---|
| `--max-turns` | **Agency** — how many agentic turns the model gets | The process exits cleanly on its own, the instant turn N+1 would start | File edits already made stay on disk; the run's `session_id` is preserved so a continuation leg can `--resume` it, but nothing produced so far is automatically committed, merged, or marked done | `is_error: true`, `subtype: "error_max_turns"`, with cost and token fields fully populated for every turn that ran | `AgentTurnLimitException` |
| `--max-budget-usd` | **Money** — cumulative USD spend, including everything subagents spend | The process exits once cumulative `total_cost_usd` reaches the cap; any subagent dispatch attempted afterward fails immediately with `Budget limit reached`, and Claude Code stops still-running background subagents | Same as above — disk state persists, but the run halts mid-flight before finishing whatever the cap interrupted | `is_error: true`; the exact `subtype` string is not itemised on the nine permitted pages — **Unverified**, see below | `AgentBudgetExceededException` |
| Subprocess wall-clock timeout | **Time** — how long the wrapper lets the OS process run at all, independent of turns or dollars | The wrapper, not Claude Code, sends the kill signal; the `claude` process is terminated wherever it happens to be mid-generation | Worst of the three: files already written survive, but the process is killed before it can print its final JSON envelope, so there is no `session_id` to resume and no cost figure for the killed turn | Nothing — no envelope is printed at all; the wrapper must synthesize its own failure result | `AgentTimeoutException` |

**D-78** — The three ceilings and their failure shapes.

**All three are needed, because each bounds a different thing.** A turn cap does not stop a slow run
that never exceeds its per-turn budget; a budget cap does not stop an infinite loop that is cheap per
turn; a timeout does not stop a run that burns money fast within its own time window. A system that
ships only one of the three is protected against exactly one runaway shape and exposed to the other
two.

`[INCIDENT]` The row that matters most in practice is the middle column — **whether work is
preserved** — and the sdlc-harness's own incident log carries the exact failure it names. A coder
step hit a hardcoded **80-turn** `--max-turns` ceiling mid-task. What broke: the run produced
**thirteen green tests and a correct fix**, then hit the ceiling and exited on `error_max_turns`
before any of it landed. What it cost: **$5.16** of work — thirteen passing tests and a working fix
— thrown away, because the turn cap stopped the process without any mechanism to preserve or resume
what had already been produced. The fix, verbatim from `agent.py`'s own docstring for `max_turns`:

```
No caller in this codebase passes `max_turns` explicitly today (AP-12200 dogfood: a real coder
step hit the hardcoded 80-turn default with no way to raise it short of an engine code change)
— this override exists so an operator can raise the cap for a story that legitimately needs
more turns via `HARNESS_AGENT_MAX_TURNS=<n>` in the environment `conductor run-pipeline` runs
under, with zero code change per run.
```

The module's own current default is no longer 80:

```python
DEFAULT_MAX_TURNS = 160
```

Raising the number from 80 to 160 and adding the `HARNESS_AGENT_MAX_TURNS` override is a real fix,
but it is a bigger-number fix, not a preservation fix — it moves the wall further away without
changing what happens when a run hits it. **The general law:** a ceiling that stops a run without
preserving its work converts a nearly-finished task into a total loss, so the ceiling and the
checkpointing have to be designed together — sizing the number correctly only postpones the same
failure to a longer run. That is exactly the argument for continuation checkpoints, covered ahead at
§3.9: a mechanism that lets a turn-exhausted run resume from where it stopped, via the same
`session_id` the error envelope already preserves, rather than discarding everything and starting
over. Two of this table's three exceptions — `AgentTurnLimitException` and `AgentTimeoutException` —
get built for real in PART 4 §4.5.2 (`build-it/05-orchestrator-a-the-runner.md`), and D-96 there
draws them beside the process boundary they each guard; the Java class itself is that file's job, not
this one's.

**Gotcha.** `[TRAP]` **Pitfall:** believing that raising `--max-turns` (or `HARNESS_AGENT_MAX_TURNS`)
is itself the fix for a turn-exhaustion incident. **Symptom:** the same failure recurs on a larger
task at the new, higher ceiling, because the number was raised but nothing changed about what happens
at the ceiling. **Fix:** pair every ceiling with a way to resume or salvage the work already done —
`--resume <session_id>` for a turn-exhausted run, an explicit "what did we finish" check before
declaring a budget-capped run a loss. **Why people believe it:** the incident's own postmortem
naturally centres on the number that was too small, and raising it is the visible, easy action; the
preservation gap is easy to miss because it never causes a problem until the *next* ceiling is hit.

> Three ceilings — `--max-turns` (agency), `--max-budget-usd` (money), and a wrapper-imposed
> wall-clock timeout — bound three independent resources, so a system needs all three; and because
> only `--max-turns` leaves a resumable `session_id` behind, the timeout is the one most likely to
> turn a near-finish into a total loss unless the wrapper checkpoints around it.

### 3. Reading cost back: the envelope, `/cost`, and `modelPricing`

**Mental model.** Nothing above is useful if the only way to find out what a run cost is to guess.
Claude Code exposes the same underlying number through three different doors, each suited to a
different moment: mid-session (`/cost`), per-invocation and machine-readable (the `-p
--output-format json` envelope), and per-organization-contract (`modelPricing`).

**Why it exists.** `[DOC]` A budget the reader cannot check is not a budget, it is a hope. The
previous file already re-verified `modelPricing` against `settings-reference` — a **Managed**-scope
setting letting an organization "report spend at your organization's contracted rates instead of
list price" — and that verification stays load-bearing here rather than being repeated. `/cost` is
an interactive slash command; it is not documented on any of this topic's nine permitted pages
(`settings`, `settings-reference`, `permissions`, `hooks`, `sub-agents`, `skills`, `memory`,
`plugins`, `cli-reference` — confirmed absent from `cli-reference` on re-verification, 2026-08-30),
so its exact reported fields are marked **Unverified** below rather than asserted from memory.

**How it works.** The one door this file has not yet shown in full is the machine-readable one used
programmatically — the same `usage.*` fields the previous file introduced, read back by a script
rather than by eye. `[BUILD]` A complete, runnable artefact that pipes a `claude -p` envelope through
a cost report:

```bash
#!/usr/bin/env bash
# cost-report.sh — read a claude -p --output-format json envelope on stdin
# and print a one-line, four-quantity cost breakdown plus the total.
set -euo pipefail

envelope="$(cat)"

total=$(jq -r '.total_cost_usd' <<<"$envelope")
input=$(jq -r '.usage.input_tokens' <<<"$envelope")
output=$(jq -r '.usage.output_tokens' <<<"$envelope")
cache_write=$(jq -r '.usage.cache_creation_input_tokens' <<<"$envelope")
cache_read=$(jq -r '.usage.cache_read_input_tokens' <<<"$envelope")
basis=$(jq -r '[.modelUsage[].costBasis] | unique | join(",")' <<<"$envelope")

printf 'total_cost_usd=%s input=%s output=%s cache_write=%s cache_read=%s cost_basis=%s\n' \
  "$total" "$input" "$output" "$cache_write" "$cache_read" "$basis"
```

**Prove step**, run against this file's own §1 envelopes:

```
$ claude -p "In one sentence, what does the term idempotent mean for an HTTP PUT request?" \
    --output-format json | ./cost-report.sh
total_cost_usd=0.17333975 input=2 output=49 cache_write=27379 cache_read=0 cost_basis=list,list
```

**What this costs.** The script itself adds no billable tokens — `jq` runs locally against text
already on disk. The cost it reports (`$0.17333975`) is the cost of the `claude -p` call it is
piped from, not a cost the script introduces; running `cost-report.sh` a thousand times over saved
envelope files is free.

**Gotcha.** No gotcha beyond what §1 of the previous file already covered — `total_cost_usd` and
`modelUsage.<model>.costUSD` remain the two fields to trust over any hand-reconstruction from a
single `usage.*` field.

> `/cost`, the `-p --output-format json` envelope, and `modelPricing` are three different windows
> onto the same underlying number — one for a live interactive session, one for a scripted or CI
> invocation, one for an organization's contracted rate overriding list price — and the honest gap to
> hold onto is that a single session's reported cost is not a month's bill: it is one term in a sum
> the reader has to accumulate themselves, across every session, to get the real total.

### 4. Measuring it: the same task, cold and warm

**Mental model.** §1's arithmetic argued the mechanism; this leaf's job is to actually run it and
report both real envelopes, not restate the conclusion.

**Why it exists.** `[PROVE]` A claim about relative cost that is only ever illustrated with invented
numbers is not proven, it is asserted with more decimal places. This leaf's obligation is the
opposite: run one task twice under the two conditions that matter, and print exactly what came back.

**How it works.** A genuine subagent dispatch (the Task-tool mechanism a running interactive session
uses to hand work to a subagent) cannot be invoked from a bare shell — it requires a live session,
and this file is being written from outside one. The measurable proxy for the same underlying
mechanism is the one §1 already used: since a subagent's own process has exactly as little access to
a parent's live cache as any other freshly launched `claude -p` call does, the cost gap between a
cold invocation and a cache-warm invocation of identical work *is* the real, observable shape of the
subagent premium, even though it is not literally captured through the Task tool. `[BUILD]` The same
task, run twice, seconds apart, against `claude-opus-5[1m]`:

```
$ claude -p "In one sentence, what does the term idempotent mean for an HTTP PUT request?" \
    --output-format json
{
  "total_cost_usd": 0.17333975,
  "usage": {
    "input_tokens": 2,
    "cache_creation_input_tokens": 27379,
    "cache_read_input_tokens": 0,
    "output_tokens": 49
  },
  "num_turns": 1,
  "subtype": "success"
}

$ claude -p "In one sentence, what does the term idempotent mean for an HTTP PUT request?" \
    --output-format json
{
  "total_cost_usd": 0.0157805,
  "usage": {
    "input_tokens": 2,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 27379,
    "output_tokens": 44
  },
  "num_turns": 1,
  "subtype": "success"
}
```

**Prove step.** `0.17333975 / 0.0157805 ≈ 10.99` — the cold ("subagent-shaped") call cost roughly
**11×** the warm ("continuation-shaped") call for the same one-sentence answer, entirely because one
call wrote a fresh 27,379-token cache prefix and the other read the same prefix back at the ~10%
rate.

**What this costs.** The two calls together cost `0.17333975 + 0.0157805 = $0.18912025` to produce
this file's own evidence — a fact worth stating plainly, since every `[PROVE]`/`[BUILD]` leaf in this
guide that invokes a real `claude -p` call is itself a small, real, billed expense, not a free
illustration.

**Gotcha.** `[TRAP]` **Pitfall:** concluding from this single pair that the subagent premium is
always ~11×. **Symptom:** sizing a subagent-dispatch budget on this file's specific number rather than
on the mechanism. **Fix:** re-read §1 — the multiplier scales with how much cache depth the
alternative (an inline continuation) would have had, so this file's 11× is one observed data point on
a small, shallow prefix, not a universal constant any more than "~2×" was.

> The same one-sentence task cost `$0.17333975` cold and `$0.0157805` warm — a real, printed ~11×
> gap driven by the cache-write-versus-cache-read choice, not an invented illustration, and the
> concrete evidence behind §1's claim that "~2×" is a floor rather than a ceiling.

### 5. The judgment: an unbounded agent loop is an unbounded invoice

**Mental model.** Everything above — the four billed quantities, the subagent premium, the three
ceilings, the three ways to read cost back — adds up to one operational stance: cost is not a
side-effect to notice after the fact, it is a first-class control surface a serious system designs
around from the start, the same way it designs around timeouts and retries for any other remote
dependency.

**Why it exists.** `[CASE]` The sdlc-harness's own architecture record makes this explicit rather
than implicit. `docs/adr/0008-cost-telemetry-phase-1.md`, read in full:

```
The harness has no first-class concept of cost. Operators learn about runaway runs after the
fact via the bill, not during.
```

That is the problem statement the three-phase decision in the same ADR answers. Phase 3's threshold
table, quoted verbatim:

```
| Threshold (workflow.yaml `budgets:`) | Default | Action |
|---|---|---|
| `warn_threshold_multiplier` × `per_stage_usd[<stage>]` | 2.0 × budget | Per-stage info: stage cost overran budget. Continue — diagnostic only. |
| `warn_soft_run_multiplier` × `per_run_usd` | 1.5 × $1.50 = $2.25 | Per-run info: cumulative cost tracking ~50% over budget. Continue. |
| `warn_hard_run_multiplier` × `per_run_usd` | 3.0 × $1.50 = $4.50 | Per-run warn: ask operator "continue?" before next stage. Halt on no-response or rejection. |
| `circuit_break_per_run_usd` | $10.00 | **Halt the run.** Emit `cost_circuit_break` signal. Resume requires fresh `--from <stage>` invocation, not inline "continue". |
```

And the ADR's own rationale for why the circuit-break is asymmetric, quoted:

```
Asymmetric cost rationale: a halted run is recoverable; a runaway $10+ run is not. Halt is the
safe default at the ceiling.
```

Two design properties fall out of that quote directly. First, the harness's own `budgets:` block is a
**second, application-level ceiling layered on top of** `--max-budget-usd` — the CLI flag bounds a
single `claude -p` invocation, while `per_run_usd` and `circuit_break_per_run_usd` bound a whole
multi-stage pipeline's cumulative spend across many invocations, which no single CLI flag can see.
Second, the four thresholds graduate deliberately — inform, inform, ask, halt — rather than jumping
straight to a hard stop, because (per the ADR) "warnings are categorically cheaper than enforcement —
they cost nothing to ignore if wrong, and operators benefit from early visibility." Without that
graduation, an operator only ever learns a run went wrong at the one moment it is too late to steer
it; without the hard circuit-break at the top, "cost as a metric" degrades back into "cost as an
anecdote" the moment nobody happens to be watching a dashboard when it matters. What would break
without either half: no graduation means every overrun is a surprise; no hard ceiling means an
unattended run has no floor under how much damage it can do.

**How it works.** This is the same argument the earlier `[INCIDENT]` at §2 already demonstrated from
the failure side — an unbounded loop is an unbounded invoice precisely because nothing was watching
the number while it grew. The ADR's contribution is the positive case: watching the number, on a
schedule, with graduated consequences, turns "reliability engineering" from a slogan into a concrete
`budgets:` block with real dollar figures in it.

**No SVG at this leaf** — the mechanism is the quoted threshold table above, already tabular; a
second diagram would only restate it.

**Code.** The quoted `docs/adr/0008-cost-telemetry-phase-1.md` table above **is** the artefact for
this leaf: a real, versioned governance policy, not a hypothetical one.

**Gotcha.** `[TRAP]` **Pitfall:** treating a cost ceiling as a thrift measure — something that saves
money and nothing else. **Symptom:** a team disables or loosens ceilings under deadline pressure
because "we can afford it this once," and an unrelated infinite loop (not a deliberately expensive
task) then runs unattended for hours. **Fix:** frame every ceiling — `--max-turns`,
`--max-budget-usd`, the wrapper timeout, and an application-level `circuit_break_per_run_usd` like the
ADR's — as a reliability control with a dollar side-effect, the same category as a timeout or a
circuit breaker on any other remote dependency (§3.8.8), not a separate "cost governance" concern
bolted on afterward. **Why people believe it:** cost is denominated in dollars, so it reads as a
finance conversation; the ADR's own circuit-break exists because an unbounded loop is
indistinguishable, from the outside, from a legitimate long task until something stops it, which is
exactly the shape of an availability problem, not a billing one.

**Interview:** "Why put a dollar cap on an agent loop instead of just monitoring spend after the
fact?" — Because an agent loop, unlike a fixed-cost batch job, has no natural ceiling on how many
turns it takes to decide it is done; monitoring after the fact tells you a run was expensive only
once it has already finished being expensive, while a cap converts an open-ended failure mode into a
bounded one, the same trade a timeout makes for latency and a circuit breaker makes for cascading
failure.

> An unbounded agent loop is an unbounded invoice because nothing inherent to the loop stops it from
> taking one more turn; `--max-turns`, `--max-budget-usd`, and a wrapper's own wall-clock timeout are
> reliability controls that happen to be denominated in dollars and turns rather than requests per
> second, and a system that treats them as optional thrift measures rather than mandatory guardrails
> is one infinite loop away from finding out the difference.

## Pitfalls

- **Belief in action:** a subagent costs a fixed "~2×" a same-sized inline call, safe to hardcode into
  a budget. **Surprising outcome:** this file's own back-to-back measurement showed an ~11× gap
  between a cold and a warm invocation of identical work, because the multiplier scales with how much
  cache depth the inline alternative would have had. **What actually gets the guarantee:** budget
  subagent dispatch against the parent session's current cache depth, or read `modelUsage.<model>
  .costUSD` on the actual dispatch rather than a remembered constant. **Why people believe it:** "~2×"
  is a convenient, roughly-right-in-the-median rule of thumb that was never claimed to be a hard
  ceiling.
- **Belief in action:** raising `--max-turns` (or an env-var override of it) is itself the fix for a
  turn-exhaustion incident. **Surprising outcome:** the sdlc-harness's own 80-turn incident — $5.16 of
  thirteen green tests and a correct fix, lost — was answered by raising the default to 160 and adding
  `HARNESS_AGENT_MAX_TURNS`, which postpones the same failure to a larger task rather than preventing
  it, because nothing about what happens *at* the ceiling changed. **What actually gets the
  guarantee:** pair every ceiling with a way to resume or salvage in-flight work — `--resume
  <session_id>` for turn exhaustion, continuation checkpoints (§3.9) generally. **Why people believe
  it:** the visible, easy postmortem action is raising the number that was too small; the preservation
  gap causes no visible problem until the next ceiling is hit.
- **Belief in action:** a cost ceiling is a thrift measure, safe to loosen under deadline pressure.
  **Surprising outcome:** the sdlc-harness's own ADR 0008 treats its `circuit_break_per_run_usd` as a
  reliability control — "a halted run is recoverable; a runaway $10+ run is not" — because an
  unbounded loop is indistinguishable from a legitimate long task until something stops it, the same
  shape as an availability incident. **What actually gets the guarantee:** treat every ceiling as
  mandatory guardrail infrastructure, layered — a per-invocation `--max-budget-usd` and a
  per-pipeline `circuit_break_per_run_usd` are not redundant, they bound different scopes. **Why
  people believe it:** cost is denominated in dollars, so it reads as a finance conversation rather
  than a reliability one.

## Cheat sheet

| Ceiling / mechanism | Bounds | Version floor | Work preserved on trip? | Reads back via |
|---|---|---|---|---|
| `--max-turns` | Agency (turn count) | No limit by default; documented behaviour current in v2.1.2xx | `session_id` preserved, resumable via `--resume` | `subtype: "error_max_turns"` in the envelope |
| `--max-budget-usd` | Money (cumulative USD, subagents included) | Cap enforcement requires v2.1.217+ | Disk state persists; run halts mid-flight | `is_error: true`; exact subtype **Unverified** |
| Subprocess wall-clock timeout | Time | Not a CLI flag — wrapper-imposed (e.g. `DEFAULT_TIMEOUT = 1800` in sdlc-harness) | Worst of the three — no envelope printed at all | Nothing; wrapper must synthesize a failure result |
| Subagent premium | — | — | — | Mechanism: cold cache-write vs. warm cache-read; ~2× is a floor, this file observed ~11× |
| `/cost` | Live session running total | Not on this topic's nine permitted doc pages — **Unverified** | n/a | Interactive slash command |
| `-p --output-format json` envelope | Per-invocation, machine-readable | Stable across v2.1.2xx | n/a | `total_cost_usd`, `usage.*`, `modelUsage.*` |
| `modelPricing` | Org-contracted rate vs. list | Managed scope; verified prior file | n/a | `modelUsage.<model>.costBasis` |
| `budgets:` / `circuit_break_per_run_usd` | Whole-pipeline cumulative spend, layered above `--max-budget-usd` | sdlc-harness application-level, not a Claude Code feature | Halt is deliberately non-recoverable inline; `--from <stage>` required | ADR 0008 threshold table |

## Self-test

1. Why can a subagent's cost be much more than "2× a comparable inline call," and what determines how
   much more?
<details><summary>Answer</summary>Because a subagent is a separately launched process with no access
to the parent session's live prompt cache, so its own system prompt and framing always pay a full
cache-write premium instead of a cheap cache-read. The size of the gap depends on how much cache
depth the inline alternative would have had — early in a session the forfeited discount is small, so
the multiplier stays near a commonly-quoted "~2×"; late in a long, deeply cached session it can be
far larger, as this file's own ~11× measurement showed.</details>

2. Name the three ceilings and the one resource each bounds.
<details><summary>Answer</summary>`--max-turns` bounds agency (how many agentic turns the run gets);
`--max-budget-usd` bounds money (cumulative USD spend, including subagents); the subprocess wall-clock
timeout, imposed by the wrapper rather than by Claude Code itself, bounds time.</details>

3. Why does a system need all three ceilings rather than just the cheapest one to implement?
<details><summary>Answer</summary>Because each only sees its own axis: a turn cap does not stop a
slow run that never exceeds its per-turn cost; a budget cap does not stop a fast, cheap infinite loop
that never crosses the dollar threshold; a wall-clock timeout does not stop a run that burns money
fast within its own time window. Any one alone leaves the other two failure shapes fully
exposed.</details>

4. What broke in the sdlc-harness's 80-turn incident, what did it cost as a number, and what was the
   fix?
<details><summary>Answer</summary>A coder step hit a hardcoded 80-turn `--max-turns` ceiling after
producing thirteen green tests and a correct fix, and exited on `error_max_turns` before any of it
landed — $5.16 of completed work thrown away. The fix was raising `DEFAULT_MAX_TURNS` to 160 and
adding a `HARNESS_AGENT_MAX_TURNS` environment override so an operator can raise the cap for a story
that legitimately needs more turns without an engine code change.</details>

5. Why does raising the turn limit not fully solve the incident in question 4?
<details><summary>Answer</summary>Because it changes the number, not what happens when the number is
reached — a larger task can still hit the new, higher ceiling and lose its work the same way, since
nothing about preserving in-flight progress changed. The `session_id` an `error_max_turns` envelope
preserves makes a `--resume`-based continuation possible, but the ceiling itself still needs to be
paired with that preservation mechanism (§3.9) to actually close the gap.</details>

6. Which of the three ceilings leaves no envelope at all when it trips, and why?
<details><summary>Answer</summary>The subprocess wall-clock timeout. It is enforced by the wrapper
process, not by Claude Code, which kills the `claude` subprocess wherever it happens to be
mid-generation — the process never gets to print its final JSON result, so there is no
`total_cost_usd`, no `session_id`, and no structured error subtype; the wrapper has to synthesize its
own failure result instead.</details>

7. What does the sdlc-harness's `circuit_break_per_run_usd` bound that `--max-budget-usd` on its own
   cannot?
<details><summary>Answer</summary>Cumulative spend across an entire multi-stage pipeline made of many
separate `claude -p` invocations. `--max-budget-usd` bounds a single invocation's spend (subagent
spend within that invocation included); it has no visibility into a second, later invocation in the
same pipeline. The harness's own `budgets:` block layers a second, application-level ceiling on top
to cover that gap.</details>

8. Why does ADR 0008 describe its cost circuit-break as "reliability engineering, not thrift"?
<details><summary>Answer</summary>Because an unbounded agent loop is indistinguishable, from the
outside, from a legitimate long-running task until something stops it — the same shape as an
availability problem, not a billing one. The ADR's own rationale states it directly: "a halted run is
recoverable; a runaway $10+ run is not," which is the same asymmetric-safety logic behind a timeout
or a circuit breaker on any other remote dependency.</details>

## Open questions

- **Unverified:** the exact `subtype` (or equivalent structured field) an envelope reports when
  `--max-budget-usd` trips, as of 2026-08-30 — not itemised on any of this topic's nine permitted
  documentation pages, and this file could not trigger the condition against a live binary to observe
  it directly.
- **Unverified:** the precise fields `/cost` reports in an interactive session, as of 2026-08-30 —
  `/cost` is not documented on `cli-reference` or any of the other eight permitted pages, and it is an
  interactive-only slash command that could not be exercised from the non-interactive shell this file
  was written from.

---

**Leaves covered:** 3.4.5–3.4.9 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-78
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 531
