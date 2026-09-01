# 21 AI for Coding — PART 3 — the Q&As and puzzles — ADVANCED (INTERNALS) (§3.1–§3.10)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](00-index.md)
Previous: [PART 3 summary and the atomic concept checklist](92-interview-internals.md) · Next: [a `.claude` folder from nothing](build-it/01-a-claude-folder-a.md)

## Interview questions and answers

### 1. Why does it matter, mechanically, that `CLAUDE.md` arrives as a user message and not the system prompt?

It matters because the two roles carry different weight with the model, and that weight difference is
the whole reason `CLAUDE.md` behaves like guidance rather than policy. A system prompt is the highest-
authority instruction channel a request has — it is where Claude Code's own built-in behaviour lives,
and it is what `--system-prompt` replaces wholesale and `--append-system-prompt` decorates. `CLAUDE.md`
is not there: it is assembled into segment 3 of the request, injected as a `user`-role message alongside
the memory system, sitting in the same cached prefix as the tool schemas but carrying the authority of
"something the user told me," not "something the harness is telling me how to behave."

![D-70 — `CLAUDE.md` is a user message, not the system prompt. The left panel is the belief; it is false.](diagrams/D-70-claude-md-not-system-prompt.svg)

**D-70** — `CLAUDE.md` is a user message, not the system prompt; the left panel is the common belief,
and it is false.

That is the mechanical reason a model can and does deviate from a `CLAUDE.md` instruction under
pressure from a more specific, later message — it competes on the same footing as anything else a user
said, not overriding the system-level frame. It also explains why `--append-system-prompt` differs in
kind, not just degree: it raises an instruction to the authority tier `CLAUDE.md` never reaches. A
candidate who calls `CLAUDE.md` "basically a second system prompt" has it backwards; the honest answer
is "strong, cached, always-present guidance, but still just a message the model can weigh against
others" — which is also why a `CLAUDE.md` rule that keeps getting ignored gets moved into a hook (a
guarantee), not rewritten louder.

### 2. Why is there no published default compaction threshold percentage?

Because the threshold isn't a constant to publish — it's computed at runtime from a server-side table
keyed by the model's context window, not a fixed fraction baked into the client. The documented relation
is a ratio: used tokens over window size crosses some threshold and compaction fires. What that ratio
resolves against differs per context window, and the table lives server-side — exactly why no single
percentage appears on any of this topic's nine permitted doc pages; publishing one would be wrong for
at least one window size the moment it shipped.

The one lever a reader can actually turn, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, is undocumented on those
same nine pages, and doesn't behave the way a naive percentage override should. It resolves as
`threshold = min(floor(window × pct/100), window − 13,000)` — a hard floor of 13,000 tokens below the
window size that no percentage, however aggressive, can cross. Someone setting the override to `100`
expecting to defer compaction until the window is full instead gets compaction at `window − 13,000`,
guaranteed, because compaction is itself a model call that needs room to read the transcript and write
a summary — deferring right up to the wall would risk the summarization call itself failing to fit.

### 3. Walk through skill re-attachment across a compaction — what survives and at what cost?

Say a session has invoked four skills, each a separate `user`-role injection on first fire, and a
compaction happens. The skill *listing* — names and descriptions — is cheap and always present, but the
**body content** each skill injected is conversation state, which doesn't survive by default.

The harness instead re-attaches the **most recent invocation of each skill**, capped at 5,000 tokens
per skill and 25,000 combined, newest-first. If four skills' combined most-recent bodies come to 30,000
tokens, the oldest-by-recency body is evicted outright to stay under the 25,000 cap — not truncated,
evicted whole. A fifth skill invoked twenty turns ago and never used again simply doesn't reappear; only
its listing entry survives. Practical consequence: a skill you're actively cycling through stays cheap
across compactions, but one used once and abandoned has to be re-invoked from scratch — the harness
doesn't guess you still need its body.

### 4. Is it accurate to say the `PreToolUse` hook runs "strictly after" permission rule evaluation?

Not exactly — the tidy phrase is more confident than the documentation itself. The `permissions` doc
page's own wording, re-verified against the live pages, is narrower and asymmetric rather than a clean
"hook second" ordering. It says a `PreToolUse` hook runs "before the permission prompt" — a claim about
timing relative to the interactive-prompt stage, not the `deny`/`ask`/`allow` check. For a *blocking*
hook (one that exits code 2), the docs say it "stops the tool call before permission rules are
evaluated," which read literally puts its effect *ahead of* rule evaluation, not after it.

![D-74 — The full permission-evaluation pipeline, one tool call from entry to outcome.](diagrams/D-74-permission-evaluation-pipeline.svg)

**D-74** — The full permission-evaluation pipeline, one tool call from entry to outcome; the hook stage
sits where the docs' asymmetric guarantee, not a strict "after," actually places it.

What both framings agree on — and what actually matters — is the guarantee that holds regardless of how
you draw the diagram: `deny` and `ask` are evaluated *regardless of* what the hook returned, so a hook
returning `allow` can never reopen a call the settings layer already denied, but a hook can add a block
on top of a call the settings layer would otherwise have allowed. Narrow never widens. That's the
honest answer — not "hook runs after rules," which is close enough for the common case but wrong about
why a blocking hook's timing actually works.

### 5. What does `--max-budget-usd 0.0001` actually do, and why did it still bill money?

It's tempting to think a budget ceiling this low would make the very first call refuse to run. It
doesn't, because the enforcement point is *between* calls, not inside one. `--max-budget-usd` accumulates
spend across the run — including subagent spend, with cap enforcement live from v2.1.217 — and checks
the running total against the ceiling after each call completes, before deciding whether to permit the
next one. A single call that's already in flight when the check would fire is not interrupted mid-call;
it finishes, gets billed for whatever it actually cost, and only *then* does the harness see that the
ceiling has been blown and refuse to start another one.

So `--max-budget-usd 0.0001` on a run that makes exactly one real call still bills that call's full
cost — in one observed run, `$0.06197725` — because there was never a second call for the ceiling to
prevent. The ceiling is a circuit breaker between invocations, not a per-token meter inside one. The
lesson: a budget cap protects against a runaway loop of many calls, not against one expensive call
being expensive. If a single call's worst case exceeds your tolerance, use a different control —
trimming the prompt, capping `--max-turns`, or a cheaper model tier — because the budget flag alone
will let that one call through and bill you for it.

### 6. Why does the guide prefer observed `total_cost_usd` over quoting a per-token price?

Because no per-token price for any model tier appears on any of the nine permitted documentation pages,
and stating one from memory would be exactly the blog-sourced, version-stale number this guide avoids —
API pricing changes on its own schedule, independent of the Claude Code release line this guide targets.
What *is* stable and observable is the `-p --output-format json` envelope's `total_cost_usd` field and
the `usage.*` breakdown of input, output, cache-creation and cache-read tokens underneath it.

The cost material here is built entirely from real invocations rather than a pricing table: two
identical one-line questions run back to back, one cold at `$0.17333975` (writing 27,379 tokens of
system-prompt prefix into the cache) and one warm at `$0.0157805` (reading the same tokens back at
roughly a tenth the write rate) — a gap of about 11× (`0.17333975 / 0.0157805 ≈ 10.99`) for identical
work. That pair of numbers proves the mechanism — cache reads dominate, cache writes are the expensive
tier — without a published rate card this guide has no permitted source for anyway.

### 7. What happens when a headless run is invoked with `--no-session-persistence` and `--output-format json` together, and the pre-flight check fails?

The honest answer here is a real inconsistency, not a clean contract. `--output-format json` is a
promise: the caller is telling the harness "give me a machine-parseable envelope, always" — that's the
whole point of scripting against it. But when `--no-session-persistence` triggers a pre-flight failure —
the harness deciding, before the model is ever invoked, that it cannot proceed without writing a
transcript to disk — that failure is reported as **plain text on stderr, with exit code 1**, not as a
JSON envelope with `is_error: true`. The `--output-format json` request is simply not honoured for this
particular failure class.

For a caller that parses only JSON and treats any non-JSON stdout as an unexpected crash, this is a real
integration hazard: a wrapper expecting "every failure comes back as `is_error: true` inside an
envelope" will choke here, because there is no envelope at all — just a message and a nonzero exit
code. The fix is defensive: treat "nonzero exit with non-JSON stdout" as its own distinct failure
class, checked before attempting to parse JSON at all, because this pre-flight path isn't the same
contract the rest of headless mode gives you.

### 8. What does a resumed `claude -p --resume <id>` call actually cost, and how do you prove it?

Resuming a session doesn't mean the harness picks up mid-conversation the way a human reopening a tab
would — the entire prior transcript is re-sent as part of the next request, because the context window
is the argument list of the next call, not a persistent memory the model reaches into. `--resume`
restores the session's `session_id` and re-supplies that stored transcript as input; it does not mean
only the new turn's tokens get billed.

The proof is a cache-token jump readable directly in the envelope: resuming after a gap shows up as a
spike in `cache_creation_input_tokens` (TTL expired) or a large `cache_read_input_tokens` figure (still
warm) — either way, a token count roughly the size of the entire prior transcript, not just the new
prompt. A caller who assumes resuming is cheap because "it's just continuing" will be surprised by that
number; the mechanism is the same "whole conversation re-sent every turn" rule that governs every other
turn, `--resume` included.

### 9. Name the three failure classes a headless wrapper has to distinguish, and how each is handled differently.

The taxonomy is three classes, and conflating any two produces a wrapper that either retries forever on
something that will never succeed, or gives up on something that would have worked on a retry.

![D-81 — A wrapper's failure taxonomy. Three branches, three different handlings — and the last parsed envelope is kept.](diagrams/D-81-wrapper-failure-taxonomy.svg)

**D-81** — A wrapper's failure taxonomy: infrastructure, contract, and agent — three branches, three
handlings.

First, **launch or timeout failures** — the subprocess never produced a usable envelope because it
crashed, hung past the wall-clock limit, or the binary wasn't found. Infrastructure, and retryable: the
same call run again might succeed. Second, an **unparseable envelope** — the process exited and printed
something, but it isn't valid JSON when `--output-format json` was requested. A contract failure, and
the dangerous one to get wrong: it repeats forever on retry if the cause is systemic (a version
mismatch, a broken flag), since the identical malformed request produces the identical malformed
response. Third, `is_error: true` inside a well-formed envelope — the agent's own failure, correctly
reported in the shape the contract promised, not the wrapper's plumbing; whether it's worth retrying
depends on the subtype — `error_max_turns` is terminal, others may be transient. Getting these three
apart is the difference between a wrapper that self-heals and one that loops on a broken contract or
discards a recoverable infrastructure blip.

### 10. What gets captured when an envelope fails to parse, and why keep it at all?

When class two of the taxonomy above fires — the process exited but its stdout isn't valid JSON — the
wrapper doesn't discard the output; it captures a 500-character snippet, checking stdout first and
falling back to stderr if stdout is empty. The snippet is deliberately bounded because an unparseable
envelope is exactly the situation where output might be enormous (a stack trace, a wall of diagnostic
text), and unbounded capture would turn a failure path into its own resource problem.

The reason to keep it: it's often the only diagnostic signal for what went wrong upstream — what a human
debugging a systemic failure (a version mismatch between expected flags and an upgraded binary's output
shape) reads first. The companion discipline is keeping the **last successfully parsed error envelope**,
not just the most recent raw failure: if a run fails on attempt N after several `is_error: true`
envelopes on attempts 1 through N-1, the last *parsed* one carries more diagnostic value than a fresh
unparseable blob, since it's the last point the system was still speaking the expected contract.

### 11. Walk through the resolution-order pattern for `max_turns`, and why it uses `is not None` instead of `or`.

Every tunable knob in the sdlc-harness's `run_agent` — timeout, max turns, permission mode, setting
sources — answers the same question at each call site: did the caller of this specific invocation ask
for something explicit? If not, is there an environment-level override for this whole process? If
neither, fall back to a hardcoded default. The actual code for max turns:

```python
resolved_max_turns = (
    max_turns if max_turns is not None
    else int(os.environ.get("HARNESS_AGENT_MAX_TURNS", DEFAULT_MAX_TURNS))
)
```

The reason this checks `is not None` rather than writing the more idiomatic-looking
`max_turns or int(os.environ.get(...))` is that `0` is a legitimate, meaningful explicit value for
`max_turns` — a caller might genuinely want to cap a call at zero agentic turns for some diagnostic
purpose — and `or` cannot distinguish "the caller explicitly passed `0`" from "the caller passed
nothing at all," because both are falsy in Python. `is not None` can, because `None` is the one value
Python reserves specifically for "nothing was passed." Contrast this with `permission_mode` and
`setting_sources` in the same file, which do use plain `or`, because both are strings where an empty
string is never a meaningful explicit choice — there's no "explicit but falsy" permission mode the way
there's an explicit but falsy `0` turn count. The operator chosen (`is not None` versus `or`) is picked
per parameter based on whether that parameter's own falsy value is a legitimate explicit choice or just
noise — not applied uniformly.

### 12. Why is `DEFAULT_MAX_TURNS` 160 rather than a rounder number like 100 or 200, and is that number a measured optimum?

It's 160 because of a specific, dated incident, and the comment sitting directly above the constant in
`agent.py` says so explicitly — it is *not* a measured-data derivation. The history is three values in
sequence: 40 was the original NIT-3 runaway-cost backstop, chosen when the only defense against an agent
burning turns unsupervised was a low ceiling. It rose to 80 once per-commit progress started streaming
live to a human via `HARNESS_PROGRESS_LOG`, because a human watching live closed most of the gap that
the low ceiling used to cover.

Then, on 2026-08-10, a dogfood run produced 13 green tests and a correct, spec-matching fix — real,
reviewable output — but exhausted the full 80-turn leg before ever reaching a commit, costing $5.16 for
zero landed work, because a fresh story's first leg is disproportionately reads and exploration, not
runaway looping. The response was to double the ceiling to 160: not to make the agent faster or smarter
(it was already producing correct work), but to give the *same* leg's work room to reach the one event
— a commit — that makes the work count downstream. The comment is explicit this is a cost-versus-dev-
experience trade-off, not a measured optimum; the wall-clock `DEFAULT_TIMEOUT` of 1800 seconds remains
unchanged throughout as the backstop for a failure a turn ceiling alone can't catch — an agent that
stays inside budget but takes too long doing it.

### 13. What broke in the `--setting-sources project` incident, and what still worked despite it?

`--setting-sources project` resolves `.claude/settings.json` against the session's `cwd` — with no
worktree fallback. In this incident, an isolated per-story git worktree meant the session's `cwd` was
the worktree's own directory, not the main checkout's root, and `.claude/settings.json` did not exist at
that path (it only existed in the main checkout). The result: the harness's own project-level
`permissions.allow` — most notably a broad `Bash(*)` rule — never loaded at all. The agent silently fell
back to the bare `acceptEdits` defaults with no permission file layered on top.

![D-83c — The observed symptom, itemised: read/edit/mkdir/touch/mv/cp/sed working, mvn/git commit/chmod/java refused](diagrams/D-83c-symptom.svg)

**D-83c** — The observed symptom, itemised: exactly the `acceptEdits` boundary, nothing more, nothing
less.

What still worked was precisely the built-in `acceptEdits` allowlist — `mkdir`, `touch`, `rm`, `rmdir`,
`mv`, `cp`, `sed`, and file edits via `Edit`/`Write` — because it doesn't depend on any settings file
loading. What got refused was everything the missing `permissions.allow` block was supposed to add:
`mvn`, `git commit`, `chmod`, `java`. That precise split — generic filesystem verbs work, build/VCS/
interpreter invocations refuse — is precise enough on its own to name the cause: whatever loaded the
extra rules for those specific commands didn't run. Two caveats worth stating precisely: a plain
worktree normally *does* inherit `.claude/settings.local.json` from the main checkout (a fallback the
tracked `settings.json` lacks), and the deny-list that also matters here sat at **user** scope per ADR
0026 — the run was under-permissioned by the missing allow rule, not fully unguarded, since the
user-scope deny-list still loaded independently of `cwd`.

### 14. What's the general law the `--setting-sources` incident establishes about `cwd`-relative resolution?

Resolve absolutely, or derive the root explicitly and refuse loudly — never fall back silently. The
specific failure here was a relative resolution (`cwd`) silently producing a *reduced* but still
plausible-looking configuration rather than an error; the agent didn't crash, it just ran with fewer
permissions than intended, and nothing in the run's own output flagged that a settings layer had failed
to load. The fix that landed cites its own ADR in the code comment specifically so the next engineer who
hits the same symptom pattern finds the incident record rather than re-diagnosing from scratch.

The law generalizes to a distinction worth stating precisely: fail safe on authorization — deny by
default when something is ambiguous — but fail *loud* on configuration — refuse to proceed if a
requested settings layer can't be found, rather than silently degrading. Those are not the same
property, and this incident conflated them: it failed "safe" (nothing dangerous happened) but failed
*silently* on configuration, which is worse than a crash, since a crash gets noticed immediately and a
silent degradation is discovered only when someone tries a command that should have worked. Three other
systems in this guide hit the identical `cwd`-relative shape: `${CLAUDE_PLUGIN_ROOT}` resolution, hook
command paths, and a `cron` job invoking a script by relative path.

### 15. For an SDK session over an untrusted folder, does a committed `allow` rule apply the way it would in the CLI?

No — the same subtlety the CLI's own `-p` flag has, restated at the SDK level. Workspace trust gates
whether committed permission rules from a project's tracked settings apply at all, and that gate is
one-sided: it can restrict, but trust status isn't something an SDK session gets to assume just because
it's programmatic rather than interactive. For a folder the harness hasn't marked trusted, an SDK
session doesn't apply the folder's committed `allow` rules, and prints a stderr warning saying so rather
than silently proceeding under a reduced rule set.

The consequence for an SDK-driven pipeline: pointing the SDK at an arbitrary, un-vetted checkout and
expecting its `.claude/settings.json` allowlist to govern the session is not safe to assume — the trust
boundary still applies; the SDK gets no pass just because there's no human watching a trust dialog
(there'd be none to show in a non-interactive session anyway). The fix is the same the CLI needs:
establish trust deliberately, or rely only on layers that don't require it — most notably managed
settings, which compose regardless of `settingSources` or trust state, the floor no session opts out of.

### 16. Why does `conductor init` reject `--resume-at` rather than approximating it, even though `run-harness.md` documents the flag?

This is a genuine, verified divergence between two layers of the same system, not a hypothetical.
`run-harness.md`, for the prose-driven `/run-harness` executor, documents `--resume-at` as a real,
working way to continue from a named point. But `conductor init` — the entry point for the
deterministic `/run-conductor` executor — rejects the flag outright rather than approximating it.

The reason traces to what each executor guarantees. `/run-conductor` is built on the promise that the
same input produces the same output — the whole value proposition of choosing it over the prose-driven
executor, which makes no such guarantee. `--resume-at` for `/run-harness` resumes from a *named stage*,
requiring the executor to reconstruct enough of the prior run's folded state to make that meaningful.
`/run-conductor` instead resumes via `--run-id`, restoring the exact folded state that run produced —
not an approximation of "what state should exist starting from this stage." Mapping `--resume-at` onto
something close to `--run-id`'s semantics would produce a resumption that *looks* like it worked but
silently isn't backed by the same determinism guarantee — so the flag is rejected outright, the
harness's pattern of failing loud on a configuration mismatch rather than silently degrading.

### 17. What is folded state, and why does it beat stored state for resuming a multi-stage run?

Stored state, naively, would mean recording every intermediate artefact and decision in full, so a
resume can replay from any point by reading back the entire history. Folded state instead means the
pipeline's state at any checkpoint is the *accumulated result* of everything up to that point, collapsed
into a single representation sufficient to continue — not a log of every step that produced it.

Why this matters for resumption: a `--run-id`-based resume in `/run-conductor` doesn't need to replay
six prior stages' decisions to reconstruct where it left off — it reads the folded state and continues,
cheaper (nothing to re-derive) and more robust (no dependence on intermediate history staying intact).
The trade-off: folded state discards the step-by-step narrative that produced it — knowing *how* the
pipeline arrived there is a separate question from resuming it, one the folded form doesn't answer.

### 18. How many rubric files does the calibration loop actually use, and why is that number worth knowing precisely?

Six, not five. The natural assumption — one rubric per obvious pipeline stage (plan, implement, review,
test, deploy) — undercounts by one, and the sixth is exactly what a candidate who's only skimmed the
pipeline's shape would miss. The full set: `progress-verifier`, `code-review`, `story-reviewer`,
`prd-reviewer`, `requirements`, and `functional-tests-reviewer` — six distinct, versioned judge rubrics,
each a different evaluative checkpoint, not five collapsed into one generic "review" rubric. The
`progress-verifier` rubric is the one wired into the continuation-checkpoint mechanism deciding whether
a run counts as progressing or stalled, independent of which executor is driving it.

### 19. What's the ranking formula for calibration friction, and why does it favor cheap-to-fix issues over merely frequent ones?

The formula is `frequency × severity × (1 / fix_complexity)`. Frequency alone would rank "a typo in a
rarely-touched log message that happens on every run" above "a rare but catastrophic failure that takes
a week to fix" — neither extreme belongs at the top of a backlog. Multiplying by severity pulls the
catastrophic-but-rare issue back up. Dividing by fix complexity is easy to miss: two issues with
identical frequency and severity rank differently if one is a one-line fix and the other an architecture
change — the cheap fix earns priority because addressing it returns more calibration value per unit of
effort spent.

That ranking feeds a human gate whose job is narrower than "decide if this is worth filing" — it
confirms no PII or leak is present, nothing more; the actual triage judgment moved to Jira triage as of
a 2026-07-22 policy change. The calibration loop's human checkpoint is a safety gate, not a
prioritization gate, and conflating the two overstates what that step is deciding.

### 20. What does `verify.sh`'s design say about ranking evidence, and where does the agent's own claim sit on that ranking?

The rank, from strongest to weakest: re-run the artefact in its published form, then a real test suite
run, then a compile check, then reading the transcript, then a diff review, then a regex-based
structural check, then — at the very bottom — the agent's own claim that its work succeeded.

That ordering follows directly from the asymmetry this whole verification area is built around:
writing is cheap for an agent, but the same agent is not positioned to credibly check its own output —
a confabulating agent producing fluent, plausible success text is exactly as capable of writing "tests
pass" as of writing correct code; fluency was never a correctness signal. Re-running the artefact in its
real, executable form outranks everything else because it can't be fooled by an agent that merely
*describes* success; a regex-based structural check ranks low but above the self-report because it at
least inspects real bytes on disk rather than trusting a narrative. The agent's own claim sits at the
bottom because it's the one form of evidence the thing being evaluated produced about itself.

### 21. Why does a grep-based verification gate over a file containing a NUL byte exit with zero stdout instead of erroring?

Because `grep` in its default mode treats a file containing a NUL byte as binary content and silently
declines to search it in text mode — it doesn't error, doesn't warn, and doesn't partially match. It
exits with code 1, its ordinary "pattern not found" code, having produced no output at all. On the
actual machine this was tested against (`ugrep 7.8.4`), the reproduction is exact: `printf 'result:
47/47 passing\x00 extra' > file.txt; grep -n "passing" file.txt` produces zero lines of output and exit
code 1, even though the string "passing" is unambiguously present in the file — running the same grep
with `-a` to force text mode finds it immediately.

This is worse than an ordinary false negative: exit code 1 is indistinguishable, to a caller that only
checks the exit code, from "ran cleanly, found nothing to complain about." A gate built as `grep -q
'BAD_PATTERN' file || exit 1` silently reports success regardless of what the disallowed pattern
actually was, because grep never inspected the content past deciding the file looked binary. The fix is
not a smarter grep invocation — it's asserting text-ness before the check runs, typically via `file
--mime-encoding`, so the *absence* of a real check becomes a loud failure instead of a silent,
indistinguishable green light.

### 22. State the four "sibling laws" from the verification internals material, in one line each, and say what unifies them.

Pin the harness version beside any digest it produced — a hash without the tool version that computed
it can't be trusted to mean the same thing on a re-run. Never let a status row point at a missing path
— a reporting surface that references a file without confirming it exists degrades into false misses
the moment the referenced path stops resolving. A closed lane is not a verified lane — closing a
verification lane records only that the *process* completed, not that what it checked was actually
sound; one incident here closed three lanes while one turned out to be an impossible spec rubber-
stamped through. Executable evidence outranks structural evidence, on a specific ranked scale — the
same ranking from question 20 above, re-derived from a different incident.

What unifies all four: each is the same general shape — a system that fails silently trains its
operators to trust it, because every prior success looked exactly like every prior silent failure. An
unrecognized settings key silently ignored, a path-scoped permission rule on a tool that doesn't
consult paths, a `skills/` directory one level too deep shipping zero skills, a settings layer failing
to load and degrading capability rather than erroring, a grep gate silently declining on binary content
— all the same failure mode in different subsystems' clothes, and the fix every time is the same: make
the absence of a real check loud, never silent.

## Predict the output

### Puzzle 1 — the `is not None` versus `or` resolution chain

```python
import os

DEFAULT_MAX_TURNS = 160

def resolve_max_turns(max_turns):
    return max_turns or int(os.environ.get("HARNESS_AGENT_MAX_TURNS", DEFAULT_MAX_TURNS))

def resolve_max_turns_correct(max_turns):
    return (
        max_turns if max_turns is not None
        else int(os.environ.get("HARNESS_AGENT_MAX_TURNS", DEFAULT_MAX_TURNS))
    )
```

A caller explicitly wants to cap a diagnostic run at zero agentic turns and invokes both functions with
`max_turns=0`, with `HARNESS_AGENT_MAX_TURNS` unset in the environment. What does each function return?

<details><summary>Answer</summary>

`resolve_max_turns(0)` returns `160`, not `0`. In Python, `0 or x` evaluates `x` because `0` is falsy —
`or` cannot distinguish "the caller explicitly passed `0`" from "the caller passed nothing at all
(`None`)," so the deliberate choice of zero turns is silently discarded and replaced with the default.

`resolve_max_turns_correct(0)` returns `0`, correctly, because `0 is not None` evaluates to `True`, and
`None` is the one value Python reserves for "nothing was passed." This is exactly the distinction the
real `agent.py` chain draws deliberately — `max_turns` uses `is not None` because `0` is a legitimate
explicit value for it, unlike `permission_mode` or `setting_sources`, which use plain `or` because an
empty string is never a meaningful explicit choice.

</details>

### Puzzle 2 — `--setting-sources project` from a worktree

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(*)"
    ]
  }
}
```

This file is committed at `<main-checkout-root>/.claude/settings.json`. A story is run inside an
isolated git worktree at `<main-checkout-root>/../worktrees/story-482/`, and the harness launches:

```
claude -p "run the story" --output-format json \
  --setting-sources project \
  --permission-mode acceptEdits
```

with `cwd` set to the worktree path. The reader is asked: does `mvn test` run? Does `mkdir tmp` run?
Does `git commit -am "wip"` run?

<details><summary>Answer</summary>

`mkdir tmp` runs. `mvn test` and `git commit -am "wip"` are both refused.

`--setting-sources project` resolves `.claude/settings.json` against the session's `cwd`, with no
worktree fallback — and `cwd` here is the worktree path, where that file doesn't exist (only the main
checkout has it). So the `Bash(*)` allow rule above never loads; the session falls back to bare
`acceptEdits` defaults with no project-level permission file layered on top.

`acceptEdits`'s own built-in allowlist covers generic filesystem verbs — `mkdir`, `touch`, `rm`,
`rmdir`, `mv`, `cp`, `sed`, and `Edit`/`Write` — so `mkdir tmp` succeeds regardless of whether the
settings file loaded. `mvn test` and `git commit` aren't in that built-in allowlist; they were only
ever going to be permitted by the `Bash(*)` rule that failed to load, so both are refused. The fix is
`--settings <absolute path>`, which resolves independently of `cwd`.

</details>

### Puzzle 3 — `--max-budget-usd` on one expensive call

```
$ export ANTHROPIC_MODEL=claude-opus-5
$ claude -p "Read every file under src/ and produce an exhaustive line-by-line \
  code review with inline suggestions for each file." \
  --output-format json \
  --max-budget-usd 0.0001
```

The repository has forty source files. What is the observed behaviour: does the call refuse to start,
does it run and get billed, or does it stop partway through?

<details><summary>Answer</summary>

It runs to completion and gets billed in full — in one observed run of a single expensive call under an
equivalently tiny ceiling, the total was `$0.06197725`, far above the `$0.0001` cap.

`--max-budget-usd` enforces its ceiling *between* calls, checking accumulated spend after each completed
call before deciding whether to permit the next one — it's not a per-token meter that interrupts a call
in flight. This invocation makes exactly one real call — reading forty files and writing one review is
one turn's worth of tool calls and one model response inside a single `claude -p` invocation, not forty
top-level calls — so there's no second call for the ceiling to block, and the one call that ran gets
billed its actual cost regardless of how far that exceeds the stated cap.

</details>

### Puzzle 4 — a grep-based gate over a file with a NUL byte

```bash
#!/usr/bin/env bash
set -euo pipefail

if grep -q "TODO(unresolved)" "generated-report.txt"; then
  echo "gate: found an unresolved TODO, failing build" >&2
  exit 1
fi

echo "gate: clean, proceeding"
exit 0
```

`generated-report.txt` was produced by an upstream step that, as an ordinary byproduct of how it
assembled the file, embedded one literal NUL byte partway through, and the text `TODO(unresolved)`
appears in the file, thirty bytes *after* that NUL byte. What does this script print, and what exit code
does it produce?

<details><summary>Answer</summary>

It prints `gate: clean, proceeding` and exits `0` — the gate reports success despite the disallowed
`TODO(unresolved)` marker being present in the file.

`file generated-report.txt` on a file like this reports `data`, not text, and `grep` in default mode
treats a NUL-containing file as binary and declines to search it as text — silently, no warning, no
partial match. `grep -q "TODO(unresolved)" file` returns exit code 1 (ordinary "pattern not found")
with zero stdout, exactly as if the pattern genuinely weren't present, so the script's `if grep -q
...; then ... fi` takes the false branch and falls through to success. The fix is asserting text-ness
before the grep runs — `file --mime-encoding generated-report.txt | grep -qv binary` as a guard — so a
binary-classified input fails the gate loudly instead of silently passing a check that never ran.

</details>

### Puzzle 5 — a `PreToolUse` hook returning `allow` against a `deny` rule

```json
{
  "permissions": {
    "deny": [
      "Bash(git push:*)"
    ]
  }
}
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"reviewed and approved by pre-push-check.sh\"}}'"
          }
        ]
      }
    ]
  }
}
```

Both files are active project settings and hooks configuration. The agent calls `Bash(git push
origin main)`. What is the outcome, and why?

<details><summary>Answer</summary>

`BLOCKED`. The `deny` rule wins, and the hook's `"permissionDecision": "allow"` has no effect on this
call.

The documentation's own guarantee, re-verified against the live `permissions` page, is that Claude Code
evaluates `deny` and `ask` rules regardless of what a `PreToolUse` hook returns — a matching `deny` rule
blocks the call even when the hook returned `"allow"`, preserving deny-first precedence across every
settings layer, including managed settings. A hook can *narrow* the stage-2 outcome — turn an `allow`
into a block, or force a prompt — but never *widen* it; no JSON output a hook returns reopens a call a
`deny` rule already closed. The hook script ran and produced a syntactically valid `allow` decision, but
that decision was irrelevant, because `Bash(git push:*)` in `deny` had already decided the call before
the hook's opinion was ever consulted.

</details>

## Open questions

None.

---

**Leaves covered:** none exclusively — this file carries PART 3's Q&As and puzzles; §3.1–§3.10's summary table and the topic-wide checklist live in `92-interview-internals.md`
**Leaves deferred:** none
**Diagrams included:** re-embedded by id where an answer turns on one — D-70, D-74, D-81, D-83c
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 596
