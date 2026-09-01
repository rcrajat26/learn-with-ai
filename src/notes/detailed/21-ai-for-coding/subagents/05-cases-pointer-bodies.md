# 21 AI for Coding — pointer bodies and versioned prompts — INTERMEDIATE (§2.1.20–2.1.22)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [persistence, invocation, and where the 2× comes from](04-limits-and-cost.md) · Next: [write boundaries, withheld tools and the return protocol](06-write-boundaries-and-protocol.md)

This file has no diagram of its own — the manifest assigns this row none. Where the
mechanism benefits from the picture already drawn, it points at **D-42** (the
subagent context boundary, `02-the-context-boundary.md`) or **D-46** (the 2× cost,
`04-limits-and-cost.md`) by id rather than re-embedding either.

## §2.1.20 When delegating actually pays

**Mechanism.** `04-limits-and-cost.md` established that spinning up a subagent is
never free — a fresh subagent instance re-pays a fixed system-prompt-plus-tool-listing
overhead before it does a single unit of useful work, which is where the 2× figure in
**D-46** comes from. Delegating only nets a win when that fixed cost is bought back by
one of exactly **three** conditions:

| Case | What it looks like | Why the parent's context comes out ahead |
|---|---|---|
| Verbose input, small answer | running the full Maven test suite, fetching a multi-hundred-line API doc, grepping a log file for one stack trace | the wall of stdout/log text is consumed inside the subagent's own context; the parent's context grows by a summary, not by the wall of text |
| Genuinely parallel work with non-overlapping writes | three independent code-review passes over three different modules, dispatched together | each subagent's tool calls and results interleave inside its own isolated context instead of interleaving inside one shared context, and their writes never touch the same files, so there is nothing to serialize |
| A different capability set | a read-only auditor with no `Write`/`Edit` in its `tools` list, or a reviewer with no network-capable tool at all | the restriction is enforced at dispatch — not by asking the model nicely — because the subagent's tool list is fixed at definition time, as `03-builtins-and-forks.md` covered for `tools:`/`disallowedTools:` |

The official guidance backs the same three-way split. Per the `sub-agents` documentation
page: "Running tests, fetching documentation, or processing log files can consume
significant context. By delegating these to a subagent, the verbose output stays in
the subagent's context while only the relevant summary returns to your main
conversation" — that is case one, verbatim. The same page frames the decision as a
choice, not a default: reach for the main conversation instead when "the task needs
frequent back-and-forth or iterative refinement," when phases "share significant
context, such as planning, implementation, and testing," or when "latency matters" —
each of those is a description of case one, two, or three failing to hold.

**Gotcha.** None of the three cases requires *all* of the other two — a real dispatch
usually satisfies exactly one, and satisfying zero is the tell that the task belongs
in the main conversation instead. A `mvn-test-runner` dispatch (case one) does not
also need to run in parallel with anything to be worth delegating; a `calibrator`
dispatch is worth it purely for case three, even though it is a single sequential
run with no verbose stdout to hide. Treating "verbose" and "parallel" as a package
deal is how a reader talks themselves out of a delegation that would have paid for
itself on capability restriction alone.

> Delegating to a subagent pays for its own fixed 2× overhead in exactly three
> situations — verbose input collapsing to a small answer, genuinely parallel
> non-overlapping writes, or a deliberately different capability set — and in no
> other situation.

## §2.1.21 The output protocol: findings go to a file, the message stays small

**Mental model.** A subagent dispatch is not a function call that returns a value —
it is closer to handing a contractor a work order and telling them where to drop the
deliverable. What comes back over the phone (the returned message) is "done, three
issues, see the folder"; what actually contains the work is the folder, which the
person who asked only opens if they need to.

**Why it exists.** Case one of §2.1.20 only pays off if the *return* channel stays
small too. A subagent that swallows 8,000 lines of test output internally and then
pastes all 8,000 lines back into its final message has isolated nothing — the parent's
context grows by exactly as much as if it had run the tests itself. The documentation
states the intended shape directly: "the verbose output stays in the subagent's
context while only the relevant summary returns to your main conversation." Writing
durable findings to a file and returning a path is the concrete instance of "summary"
that a reader reaches for when the findings need to survive past the single reply —
a review report, a mined pattern file, an audit log — rather than merely being
compressed prose.

**How it works.** Nothing enforces this mechanically the way a tool restriction does;
there is no frontmatter field that makes a subagent's return value file-shaped. It is
a convention stated in the subagent's own instructions, and the sdlc-harness's
`calibrator` shows the real shape of it. Its versioned prompt,
`harness/control-plane/agent-prompts/calibrator.md`, ends Phase 1 like this:

```text
You do not build the Jira payload yourself — `scripts/build-jira-bug.py --mined
harness/calibration/friction/mined-{date}.yaml --dry-run` (run by the team lead) does
that deterministically, grouping by `failure_code` and building one ticket per group.
Your job here is done once `mined-{date}.yaml` exists and you've read it — summarize
what you found (distinct `failure_code`s, occurrence/session counts per group) for the
step-3 report; the team lead takes it from there per
`plugins/sdlc-harness/commands/calibrate.md`.
```

Read before quoted, from lines 75–81 of that file. The durable evidence — every mined
friction pattern, with its `sessions_affected` and `occurrences` counts — lands in
`harness/calibration/friction/mined-{date}.yaml` on disk. What the calibrator hands
back upward is the much smaller "distinct `failure_code`s, occurrence/session counts
per group" — a status plus a few findings plus, implicitly, the path the file was
written to. The team lead's own next step reads that file itself when it needs the
full detail; most of the time it does not need to, and the summary is enough to act on.

**Gotcha.** The isolation in **D-42** only holds up to the return message — a subagent
that pastes its entire working transcript, a full diff, or an entire log back into its
final reply defeats the boundary from the inside, because that text now re-enters the
parent's context exactly as if the parent had produced it directly. "Message bodies
are not a data channel" is the discipline that keeps §2.1.20's case one from being
undone at the last step: bulky evidence belongs on disk, and the message names where
to find it, not what it contains.

**Interview:** "You dispatch a subagent to review a 2,000-line diff. How do you stop
its findings from blowing up your context budget?" Have it write the full review to
a file and return three lines — status, the two or three findings that matter most,
and the file's path — rather than returning the full review inline; you read the file
only if you need more than the summary.

> The output protocol that makes delegation actually pay: a subagent writes its full,
> durable findings to a file inside its own dispatch and returns only a short status,
> the handful of findings that matter, and the file's path — the parent's context
> grows by that summary, never by the underlying evidence.

## §2.1.22 The pointer body — `progress-verifier.md`

**Mental model.** A Spring Boot engineer reaching for `@Value("${retry.max-attempts}")`
instead of hardcoding `3` inside an `@Bean` method already knows this shape: the class
that gets compiled and shipped names a stable binding point, and the actual value that
binding resolves to lives in `application.yml`, changeable without recompiling or
re-releasing the class that reads it. A pointer-body subagent definition is the same
move applied to a system prompt instead of a config value.

**Why it exists.** The `sub-agents` documentation is explicit that there is no field
for this: "the text after the closing `---` is the system prompt" — whatever
Markdown sits in the body of `plugins/sdlc-harness/agents/progress-verifier.md` *is*
the literal instructions the subagent runs on, verbatim, with no indirection built
into the frontmatter schema. `name`, `description`, `tools`, `disallowedTools`,
`model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`,
`background`, `effort`, `isolation`, `color`, `initialPrompt` and `experimental` are
the documented fields, and none of them accepts a path to an external prompt file.

Given that constraint, `plugins/sdlc-harness/agents/progress-verifier.md` ships as
part of the `sdlc-harness` plugin — versioned by `plugins/sdlc-harness/.claude-plugin/plugin.json`'s
own `version` field, from §2.5.17. If the judge's actual scoring instructions lived
directly in that body, every wording tweak to how the judge scores would require
bumping the plugin's version and republishing it, and the prompt's own edit history
would be buried inside the plugin's release commits alongside hook fixes, skill
changes and everything else the plugin ships. Instead, the body is written as a stub
that tells the agent to go read its real instructions from a second file that lives
outside the plugin folder entirely, under the harness's own `harness/` tree, where it
is a normal file in the same repository the harness's Python engine is developed in —
diffable, revertible and reviewable on its own commit history, with no plugin release
required to change it.

**How it works.** Read in full — it is short — this is the entire body of
`plugins/sdlc-harness/agents/progress-verifier.md`:

```markdown
---
name: progress-verifier
description: >
  Judges whether a coder that just exhausted its turn allotment mid-story is
  genuinely advancing toward the story's acceptance criteria or is
  stalled/circling. Invoked ONLY by the engine's code_to_commit continuation
  checkpoint (AP-12776) — never by a human, never resumed into the coder's own
  session. Evidence is artifacts only: git log, diff stat, relayed milestones.
---

Read your system prompt at: harness/control-plane/agent-prompts/progress-verifier.md

Then read the rubric you score against:
`harness/control-plane/judge-rubrics/progress-verifier.yaml`

Score the evidence in your task (git log, diff stat, relayed milestones) against
that rubric, then finish your FINAL message with exactly one verdict line:

    ## Progress Verdict: progressing|stalled

## Read boundaries

You have READ access only, over artifacts already embedded in your task text
(git log, diff stat, relayed milestones) — you never need to write anything,
and you never inspect the coder's own live conversation or session.

## Out of scope

- Never resume, inspect, or infer the coder's own `claude` session/conversation
  — you judge artifacts only (RFC R-15).
- Never write a verdict to a file or via a shell command — the engine captures
  your response text directly, the same contract the `self-review` reviewer
  persona already uses.
- Never re-derive a pass/fail threshold from your own per-criterion scores —
  the verdict line you emit IS the decision; the engine performs no scoring
  arithmetic of its own.
```

36 lines, confirmed by `wc -l` against the read-only repo. **Divergence from the
leaf:** the syllabus describes this file as "20 lines" — it is not; it is 36. The
leaf's claim does not hold and this note states what the file actually contains
rather than the stale count.

The line that matters is one sentence: `Read your system prompt at:
harness/control-plane/agent-prompts/progress-verifier.md`. That is not a special
Claude Code directive — it is plain English inside the system prompt, and it works
because the subagent's very first move under that instruction is to call its `Read`
tool on that path, exactly the way it would read any other file the task asked it
to. What that path resolves to is the real elaboration. Read in full, it opens:

```markdown
# Progress Verifier — System Prompt

## Role

You are the Progress Verifier. You are invoked ONLY at a continuation checkpoint of
the engine's `code_to_commit` coder step (AP-12776, RFC R-15) — the coder just
exhausted its `--max-turns` allotment mid-story, and the engine needs an
INDEPENDENT judgment of whether to resume it with another leg or escalate to a
human.

You are structurally independent from the coder: you are NEVER resumed into its
session, and you have no access to its conversation. Your entire evidence base is
the artifacts embedded in your task text — a git log since the previous checkpoint,
a diff stat, and any milestones the coder relayed via `record-progress.sh`. Judge
those artifacts on their own terms; do not assume or infer anything about what the
coder said or did outside them.
```

and, further down, restates the exact verdict-line contract found in the stub —
`## Progress Verdict: progressing|stalled` — plus the full per-criterion scoring
procedure against `judge-rubrics/progress-verifier.yaml` that the 36-line stub only
gestures at with "Score the evidence... against that rubric." The stub is where the
subagent starts; the 56-line file at `harness/control-plane/agent-prompts/progress-verifier.md`
is where its actual behaviour is defined.

**Insight — the pointer is partial, not total.** The stub does not delegate
everything: `## Read boundaries` and `## Out of scope` are written out **in both**
files, in near-identical wording. The safety-critical constraints — read-only,
never resume the coder's session, never let the verdict line drift from the
per-criterion scores — are duplicated locally in the plugin-shipped stub as well as
carried in full in the resolved prompt, so that even if a stale plugin release ever
served a stub whose pointer no longer matched the harness repo's current prompt file,
the constraint that matters most for safety — this agent never touches the coder's
live session — still binds from the stub alone. What gets pointed at, rather than
duplicated, is the *elaboration*: the full scoring walkthrough, the framing of "you
are not the gate," the reasoning behind the fail-closed verdict default. Design
property, precisely: **the plugin-shipped body is a stable, reviewable stub; the
behaviour that changes when the team tunes how strictly the judge scores lives in a
file that is versioned, diffable and swappable without republishing the plugin —
except for the handful of hard constraints important enough to duplicate rather
than trust to indirection.**

**What breaks without it.** Collapse the two files into one and every prompt-wording
tweak — loosening a scoring criterion, adding a new failure mode to watch for —
becomes a plugin version bump, gated behind whatever release process
`plugins/sdlc-harness/.claude-plugin/plugin.json` goes through, and the prompt's own
edit history stops being a readable sequence of harness commits and becomes a set of
diffs buried inside plugin release commits mixed with hook and skill changes that
have nothing to do with how the judge scores.

**The cost, named honestly.** The indirection buys versioning independence at a real
price: the definition that ships in the plugin no longer tells a reader what the
agent does. Someone auditing `plugins/sdlc-harness/agents/progress-verifier.md` for
what this subagent is permitted to do sees a `Read` instruction and a rubric
reference, not the actual scoring logic — a reader, or a permission reviewer working
through what a plugin installs, has to follow the pointer into a second file, in a
second directory, before the picture is complete. A one-file audit becomes a two-file
audit, silently, for every pointer-bodied agent in the plugin.

**Where the pointer resolves from — and where it does not use `${CLAUDE_PLUGIN_ROOT}`.**
The path in the stub, `harness/control-plane/agent-prompts/progress-verifier.md`, is
a bare project-relative path with no prefix at all — it is not written as
`${CLAUDE_PLUGIN_ROOT}/agent-prompts/progress-verifier.md`. Compare
`plugins/sdlc-harness/hooks/hooks.json`, which resolves every one of its handler
commands through that variable — `bash "${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh"` —
an environment variable Claude Code sets to the plugin's own absolute install
location, so a hook command resolves correctly no matter which project the plugin
gets installed into. `${CLAUDE_PLUGIN_ROOT}` gets its full mechanical treatment at
§2.5.18; the fact worth carrying forward from here is narrower: this agent's pointer
does **not** use it, and so it resolves against whatever the session's working
directory happens to be when the `Read` runs. That only lands on the right file
because this plugin is always installed at the root of the very repository it
governs — `harness/control-plane/agent-prompts/` is a path that exists relative to
the sdlc-harness repo root, not relative to the plugin's own folder. Install this
plugin into a different project that lacks a `harness/control-plane/agent-prompts/`
tree, and the pointer resolves to nothing.

**Pitfall:** the wrong belief is "this plugin's agents are as portable as its
hooks, since they're shipped from the same `plugins/sdlc-harness/` folder." The
symptom is a `progress-verifier` dispatch that tries to `Read` a path that does not
exist in whatever project the plugin got installed into, because the pointer was
written assuming the plugin is always co-located with `harness/control-plane/` at
the same repo root. The fix is to check, before reusing an agent definition from one
plugin in a different project, whether its body's `Read` targets are
`${CLAUDE_PLUGIN_ROOT}`-relative (portable) or bare project-relative (only correct
inside the repository the plugin was authored for) — `hooks.json`'s handlers are the
former, `progress-verifier.md`'s pointer is the latter.
**Why people believe it:** the plugin manifest and marketplace machinery (§2.5.16,
§2.5.17) are built for exactly this kind of portability, and most of what a plugin
ships — hooks, skills, commands — is written to be relocatable; this one agent
pointer is the exception, not the rule, inside the same plugin.

> A pointer body is a subagent definition whose Markdown body is a short, stable stub
> instructing the agent to read its real system prompt from a second, independently
> versioned file — cheap to review, but only as portable as the path it points to,
> and here that path is a bare project-relative one rather than
> `${CLAUDE_PLUGIN_ROOT}`-anchored.

## Pitfalls

- **Belief:** "the three cases in §2.1.20 are a checklist — the more of them a
  dispatch satisfies, the more it's worth delegating." **Surprising outcome:** a
  reader waits for a task to be verbose *and* parallel *and* capability-restricted
  before delegating anything, and under-delegates work that would have paid for
  itself on a single case. **What actually gets the guarantee:** any one of the three
  conditions in the §2.1.20 table is independently sufficient; `calibrator` is worth
  dispatching on case three alone, with nothing parallel and nothing verbose about it.
  **Why people believe it:** the three are presented together as a set, which reads
  like a conjunction rather than a disjunction on first pass.
- **Belief:** "a subagent that returns a compressed prose summary has satisfied the
  output protocol." **Surprising outcome:** a subagent asked to review a large diff
  pastes a condensed-but-still-long write-up into its final message, and the parent's
  context grows by most of what the diff review would have cost inline. **What
  actually gets the guarantee:** durable findings go to a file the subagent writes
  itself, and the returned message is a status line, the handful of findings that
  matter, and the file's path — per `calibrator.md`'s own Phase 1 hand-off. **Why
  people believe it:** "summary" sounds satisfied by shorter prose, and shorter prose
  is still much cheaper than the raw evidence, so the difference is easy to miss until
  the summaries themselves start accumulating across many dispatches.
- **Belief:** "an agent shipped inside a plugin folder is exactly as relocatable as
  the plugin's hooks are." **Surprising outcome:** copying `progress-verifier.md`
  into a different plugin, or installing `sdlc-harness` somewhere that is not the
  repo it governs, produces a `Read` call against a path that does not exist. **What
  actually gets the guarantee:** check whether the body's pointer path is
  `${CLAUDE_PLUGIN_ROOT}`-relative or bare-project-relative before assuming
  portability; this one is the latter. **Why people believe it:** `hooks.json` in the
  same plugin uses `${CLAUDE_PLUGIN_ROOT}` consistently, so the exception stands out
  only once a reader checks both files side by side.

## Cheat sheet

| Fact | Value |
|---|---|
| Three cases where delegating pays | verbose input → small answer; parallel non-overlapping writes; different capability set |
| Doc-cited reasons to stay in the main conversation | frequent back-and-forth, shared planning/implementation/testing context, latency matters |
| Output protocol | write durable findings to a file; return status + top findings + path |
| Real example of the protocol | `calibrator.md` Phase 1 → writes `mined-{date}.yaml`, returns grouped summary |
| `progress-verifier.md` (stub) length | 36 lines (leaf's "20 lines" is stale) |
| Pointer line | `Read your system prompt at: harness/control-plane/agent-prompts/progress-verifier.md` |
| Frontmatter field for an external prompt file | none exists — the body itself is always the literal system prompt |
| What is duplicated across stub and resolved prompt | `## Read boundaries`, `## Out of scope`, the verdict-line format |
| What lives only in the resolved prompt | the full per-criterion scoring walkthrough, the "not the gate" framing |
| Pointer path style here | bare project-relative — **not** `${CLAUDE_PLUGIN_ROOT}`-anchored (full treatment: §2.5.18) |

## Self-test

1. Why does a subagent dispatched purely for its restricted capability set (case
   three) still pay for itself even with no verbose output and no parallelism?
<details><summary>Answer</summary>
Because the value being bought is not context savings but an enforced boundary —
the subagent's tool list is fixed at definition time, so a task that must never touch
the network or must never write is guaranteed to comply, in a way that asking the
main session to "please stay read-only for this one task" is not. `calibrator`'s
missing Jira tool is exactly this: no dispatch of `calibrator` can ever call the Jira
API, regardless of what its prompt says, because the tool simply is not in its list.
</details>

2. What does the sub-agents documentation give as the fourth reason a task belongs
   in the main conversation instead of a subagent dispatch?
<details><summary>Answer</summary>
Latency — "latency matters" is stated as its own reason, alongside needing frequent
back-and-forth, needing a quick targeted change, and needing to share significant
context across planning/implementation/testing phases. A subagent dispatch pays a
fixed startup cost before it does anything, which a quick single-turn edit cannot
recoup.
</details>

3. Concretely, what does `calibrator.md`'s Phase 1 hand-off write to disk, and what
   does it return in its message?
<details><summary>Answer</summary>
It writes the full, occurrences-weighted set of mined friction patterns to
`harness/calibration/friction/mined-{date}.yaml` (produced earlier, in Phase 0, by
the miner subprocess). What it returns in its message is a summary: the distinct
`failure_code`s found and the occurrence/session counts per group — not the patterns
themselves, and not the file's contents.
</details>

4. How many lines is `plugins/sdlc-harness/agents/progress-verifier.md`, and how does
   that compare to what the leaf claims?
<details><summary>Answer</summary>
36 lines, confirmed with `wc -l` against the read-only repo. The leaf describes it as
"20 lines," which does not match; this file is written against the real 36-line
content rather than the stale count.
</details>

5. What single sentence inside `progress-verifier.md`'s stub is doing all the work of
   the "pointer"?
<details><summary>Answer</summary>
`Read your system prompt at: harness/control-plane/agent-prompts/progress-verifier.md`
— plain English instructing the subagent's first action to be reading a second file
and treating its contents as the real instructions. There is no frontmatter field or
built-in Claude Code mechanism that does this; it works purely because the model
follows the instruction and calls `Read` on the named path.
</details>

6. Is the pointer body in `progress-verifier.md` total or partial — does the stub
   contain zero behavioural content of its own?
<details><summary>Answer</summary>
Partial. The stub duplicates the safety-critical constraints — `## Read boundaries`,
`## Out of scope`, and the exact verdict-line format — locally, in addition to
pointing at the resolved file for the full scoring elaboration. Only the elaboration
is exclusively remote; the hard constraints are carried in both places.
</details>

7. Why doesn't `progress-verifier.md`'s pointer path use `${CLAUDE_PLUGIN_ROOT}` the
   way `hooks.json`'s handler commands do, and what does that cost?
<details><summary>Answer</summary>
It's written as a bare path relative to the project root instead —
`harness/control-plane/agent-prompts/progress-verifier.md` — which only resolves
correctly because this plugin is always installed at the root of the very
sdlc-harness repository it governs. `${CLAUDE_PLUGIN_ROOT}` would make the pointer
resolve relative to the plugin's own install location regardless of which project it
lands in, the way `hooks.json`'s `"${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh"` does.
The cost of not using it: this agent definition is not portable to a different
project the way the plugin's hooks are.
</details>

## Open questions

None.

---

**Leaves covered:** 2.1.20–2.1.22 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — this row's mechanisms are drawn by D-42 to D-46 in the preceding files
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 424
