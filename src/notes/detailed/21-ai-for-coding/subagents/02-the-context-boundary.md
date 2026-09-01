# 21 AI for Coding — the subagent context boundary — INTERMEDIATE (§2.1.6–2.1.10)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [subagent definition and precedence](01-basics-definition-and-precedence.md) · Next: [built-ins and forks](03-builtins-and-forks.md)

## §2.1.6 The routing budget: `description` is what gets read, and it has a ceiling

The previous file already established that a subagent is chosen from its `description` field alone, before any other field is read, and walked the failure mode of a description that names a topic instead of a trigger. What it did not cover is that this field is not free: every custom subagent's `description` is loaded into the parent model's context so it can make that choice, and the combined size of all of them is capped.

**Why it exists:** if the parent had to load the full body of every subagent definition just to decide whether to delegate, the cost of merely *having* twenty subagents defined would scale with the size of twenty system prompts, paid on every single turn regardless of whether any of them fire. Capping the routing signal to descriptions only, and capping the total size of those descriptions, keeps that fixed cost small and predictable.

**How it works:** the combined `description` text across all custom agent definitions available to a session is budgeted at roughly **15,000 tokens**. `[NUM]` This is a shared pool across every agent definition the harness has loaded for that session — project, user, and plugin agents together — not a per-agent allowance. A session with a handful of tightly-written descriptions never approaches it; a session with dozens of verbose, multi-paragraph descriptions can exhaust it, at which point some agents' descriptions get truncated or dropped from what the parent sees, and a subagent the parent cannot read the description of is a subagent it will never delegate to, regardless of how well-designed its system prompt is.

**Pitfall:** treating an agent's `description` field as a place to also document its behaviour for a human reader — pasting in three paragraphs of internal design notes because "someone should explain what this thing does." The belief is that a longer description is more helpful. The symptom, at scale, is that the routing budget fills up on a handful of over-written agents, degrading delegation accuracy for every other agent in the same session. **Fix:** keep `description` to one or two sentences that name the trigger and the action — exactly the shape the previous file's `readonly-reviewer` example used — and put anything a human needs explained in the system-prompt body instead, which is never read for routing at all.

No gotcha beyond the one just stated: the budget is shared, not per-agent, and that is the surprising part. No diagram is assigned to this leaf — the manifest's diagrams for this file are D-42 (referenced, not re-embedded) and D-43 (below); the routing budget is a numeric fact, not a shape.

**Interview:** "Is there a limit on how much `description` text Claude Code will read to decide which subagent to use?" — Yes, roughly 15,000 tokens combined across every custom agent's description in the session; it's a shared budget, so one verbose agent's description can crowd out another agent's chance of ever being selected.

> The `description` routing budget is a shared ~15,000-token pool across every custom subagent's `description` field in a session — the fixed cost of being able to delegate at all, independent of whether delegation happens.

## §2.1.7 `tools` and `disallowedTools`, extended: MCP prefixes and restricting sub-delegation

The previous file established `tools` as a genuine, enforced allowlist and `disallowedTools` as a denylist applied first. Two more shapes that allowlist takes are worth naming precisely, because both show up the moment a subagent's toolset needs to reach past the built-in tool names.

**MCP-prefixed tool names.** An MCP (Model Context Protocol) server's tools are exposed to Claude Code with a namespaced name of the form `mcp__<server>__<tool>` — for example `mcp__ide__getDiagnostics`. A `tools` list can name one of these exactly, the same as it names `Read` or `Bash`, to grant a subagent access to one specific MCP tool without opening the whole server's surface: `tools: Read, Grep, mcp__ide__getDiagnostics` grants exactly that one MCP tool alongside the two built-ins, nothing else the `ide` server exposes.

**Restricting which agents a subagent may itself spawn.** A subagent can be given the `Agent` tool — the same dispatch mechanism the parent session uses — which lets it delegate further, to a sub-subagent. Left unconstrained, that is delegation with no floor: a subagent spawns a subagent spawns a subagent. The `tools` field lets a definition name which specific agents the `Agent` tool may target, in a parenthesized form: `tools: Agent(mvn-test-runner, readonly-reviewer)` grants the `Agent` tool but restricts its argument to those two names — an attempt to dispatch any third agent is rejected at the same enforcement point that blocks a disallowed built-in tool, because the restriction lives inside the allowlist mechanism the previous file already established as a real fence, not a suggestion.

Here is a complete definition using both extensions together — a coordinator that reviews a story's readiness by checking test results and code quality, but is restricted to exactly two named workers and one specific MCP tool rather than being handed the bare `Agent` tool or a whole MCP server:

```markdown
---
name: story-readiness-coordinator
description: Dispatches test verification and code review for a completed story, then combines both results into a single readiness verdict. Use proactively when a story's branch is marked ready for review.
tools: Read, Grep, Glob, Agent(mvn-test-runner, readonly-reviewer), mcp__ide__getDiagnostics
model: sonnet
maxTurns: 15
---

You coordinate two other subagents to assess whether a story's branch is ready
to merge. You do not run tests or review diffs yourself.

Given a branch name:

1. Dispatch `mvn-test-runner` to run the full test suite against the branch
   and report which tests failed and why.
2. Dispatch `readonly-reviewer` to review the branch's diff for correctness
   and quality issues.
3. Check `mcp__ide__getDiagnostics` for any compiler or linter diagnostics
   the IDE surfaces on the changed files.
4. Combine all three results into one verdict: READY, or NOT READY with the
   specific blocking items named.

Never dispatch any subagent other than `mvn-test-runner` and
`readonly-reviewer` — you have no authority to invoke any other agent.
```

If this coordinator's system prompt is later edited to say "dispatch `progress-verifier` too," the dispatch fails at the same enforcement point the previous file's typo case described for a plain `tools` entry: `progress-verifier` is not in the `Agent(...)` list, so it does not resolve, regardless of what the prose in the body asks for. The frontmatter is the fence; the body's instructions do not get a vote.

**Insight:** these are the same mechanism wearing two different clothes. `tools` does not merely gate *which named tools exist*; where a tool itself takes a further argument that selects among a family — an MCP server's individual tools, or the `Agent` tool's roster of dispatchable agents — the allowlist can gate *that argument* too. A `readonly-reviewer` that should never be able to invoke a second review subagent gets that guarantee from `tools: Read, Grep, Glob, Bash` simply omitting `Agent` entirely; a coordinator subagent that should delegate only to a fixed, audited set of workers gets it from `Agent(mvn-test-runner, progress-verifier)` rather than bare `Agent`.

**Gotcha:** naming an agent in the `Agent(...)` restriction that does not exist, or that is shadowed by precedence (the previous file's `.claude/agents/` vs `~/.claude/agents/` collision) so a different definition than the one intended answers to that name, fails the same way an unresolvable tool name fails per the previous file — the entry simply does not resolve, and dispatch to it is refused rather than silently falling through to some other agent.

> `tools` restricts not only which tool names are callable but, for tools that take a further selector — an MCP tool name, or an agent name for `Agent(...)` — which values of that selector are callable, enforced as the same real allowlist for the whole run.

## §2.1.8 What crosses the boundary inward

The previous file's D-42 showed the boundary's shape: a task string goes in, one message comes out, everything between is invisible to the parent. This section and the next name every item that crosses, on the authority of the `sub-agents` doc page, re-verified by WebFetch immediately before this file was written (2026-08-29).

Crossing **inward**, into a freshly-dispatched, non-fork subagent's initial context:

1. **The subagent's own system prompt, plus environment details Claude Code appends** — not the full Claude Code system prompt the parent runs on, its own.
2. **The task message** — the delegation prompt the parent composes and hands off; the previous file's phrase for this was "a task description instead of your conversation history."
3. **The full `CLAUDE.md` hierarchy** the main conversation loads — `~/.claude/CLAUDE.md`, project-level `CLAUDE.md`, `CLAUDE.local.md`, and managed policy files — with one stated exception: **"Explore and Plan are the only subagents that omit CLAUDE.md and git status."** `[DOC]` Every other subagent, custom or built-in, gets the full hierarchy; those two specifically do not, because they are read-only exploration and planning agents whose job is to answer a narrow question quickly, not to operate under project-wide behavioural rules.
4. **A git-status snapshot** — covered on its own in §2.1.9 below, because its timing is the leaf this row exists to make unmissable.
5. **Preloaded skills** — the full content of any skill named in the definition's `skills` frontmatter field (established in the previous file's field table) is injected before the subagent's first turn, exactly as if the subagent had already invoked it.
6. **The sibling roster** — a system reminder listing `main` and every other named agent active in the session, so a subagent can address a sibling by name with the same mechanism the parent uses. This one is itself version-gated: it requires **Claude Code v2.1.206 or later**. `[VERSION]` A subagent dispatched from an older binary in the same v2.1.2xx line does not receive this list at all.

**Why it exists:** every item on this list is something the subagent cannot function correctly without, and nothing more. It cannot follow project conventions without `CLAUDE.md`; it cannot reason about the current state of the repository without some git information; it cannot use a skill the definition explicitly preloaded without that skill's content actually being present; it cannot address a sibling it does not know exists. The inbound list is not generous — it is the minimum a fresh context window needs to be useful at all, drawn narrowly enough that everything not on it (§2.1.9) can be safely left out.

## §2.1.9 The git-status snapshot: taken at parent session start, not at dispatch

This is the one item on the inbound list whose *timing* is the actual hazard, and it deserves its own numbered leaf rather than being folded into the list above.

**How it works, precisely, quoting the doc:** "The git status is a snapshot taken at the start of the parent session" — not refreshed, not re-read, not taken at the moment a given subagent is dispatched. `[DOC]` It is absent under two conditions: when the working directory is not a git repository, or when `includeGitInstructions` is set to `false`.

**Why this is subtle:** every other inbound item (system prompt, task message, `CLAUDE.md`, preloaded skills, sibling roster) is either static for the whole session or freshly composed per dispatch. Git status is the one piece of *state about the world* on the inbound list, and it is frozen at a single point — session start — then handed unchanged to every subagent dispatched for the rest of that session, no matter how long the session runs or how much the working tree changes in the meantime.

**Pitfall:** a long-running session opens in the morning against a clean working tree, and that git-status snapshot is taken then. Over the following hour the engineer makes forty commits, merges a branch, and leaves three files mid-edit. Late in that same session they dispatch a subagent with the task "fix the failing test" — relying on the subagent to run `git status` itself would be the safe path, but if the subagent instead trusts the git-status text injected into its own startup context, it is looking at the picture from an hour and forty commits ago: files that snapshot shows as modified may be long since committed and clean; files it shows as clean may now carry uncommitted changes; a branch it names as current may no longer be checked out. **Fix:** for any subagent whose task depends on the *current* state of the working tree, the task message must tell it to run `git status` (or `git diff`) itself as a first step, rather than relying on the injected snapshot — the injected copy is a courtesy for orientation, not a live read. A `readonly-reviewer` reviewing "the current diff" is exactly the kind of task this bites: its own system prompt in the previous file already opens with "Run `git diff`... to see the full change set" for precisely this reason, not merely as a style choice.

**Why people believe otherwise:** every other piece of injected context is either genuinely current (the task message, composed at the moment of dispatch) or slow-changing enough that staleness rarely matters (`CLAUDE.md`, which changes on the timescale of pull requests, not commits). Git status is the odd one out — the fastest-changing piece of state on the list — and it is easy to assume something that fast-changing must be captured fresh, when the doc states plainly that it is not.

> The subagent's git-status snapshot is captured once, at the parent session's start, and handed unchanged to every subagent dispatched from that session afterward — never refreshed at dispatch time.

## §2.1.10 What does not cross, and what "one message out" means

**What is blocked at the line**, on the same authority, for a non-fork subagent:

- **Conversation history** — "subagents start fresh; they don't see your previous messages." The previous file's opening mental model — "a fresh, empty context window, seeded with a task description instead of your conversation history" — is this exact fact restated as doctrine.
- **The main session's output style** — a subagent runs its own system prompt, so whatever output style the parent session is configured with does not shape the subagent's responses. Forks are the stated exception (§2.1.13, next file).
- **Auto memory** — the main conversation's auto memory is not loaded into a subagent's context. This is the same fact the reader met at §1.3.25: auto memory does not cross into a subagent, a fork excepted, and a subagent's own `memory` frontmatter field (previous file's field table) is a wholly separate persistence mechanism — a small file it writes and reads back across its own invocations, not a channel into the parent's memory. The practical conclusion follows directly: a correction the reader has taught Claude over months of sessions — a naming convention it once got wrong and was told to stop doing, a project quirk it learned the hard way — is simply **absent** inside a delegated subagent unless the task message or a `CLAUDE.md` file restates it. The subagent does not inherit the parent's education; it inherits only what §2.1.8 lists.
- **Previously read files** — "each subagent has its own exploration context." A file the parent read three turns ago is not in the subagent's context merely because the parent has seen it; if the subagent needs that file's contents, its task message must name the path and it must read it itself.
- **Previously invoked skills** — "subagents don't see skills you've already used." Only skills the *definition's own* `skills` field preloads (§2.1.8, item 5) are present; a skill the parent loaded mid-conversation does not travel along.
- **Context window size** — stated for completeness rather than as a boundary crossing: a subagent's context window is sized by its own model, not inherited from the parent's.

**What crosses outward: one final message, and nothing else.** The doc does not use the exact phrase "one message" or "final message," but every statement it does make about the return path agrees on the shape: "Claude composes a delegation message that summarizes the task, and the subagent works from there," "each subagent invocation creates a new instance rather than continuing an earlier one," and, describing the fork case for contrast, "the fork's own tool calls still stay out of your conversation and only its final result comes back, so your main context window stays clean." `[DOC]` Every intermediate tool call, every file the subagent read, every dead end it explored on the way to an answer — none of it is visible to the parent. The parent's context grows by exactly the length of whatever the subagent's final response contains.

**Insight:** this is not a limitation grudgingly accepted — it is the entire mechanism that makes a subagent a *context boundary* at all, in the sense the reader has been using that phrase since the previous file. If more than one message came back, or if intermediate tool calls leaked through, the twelve-log-files arithmetic from the previous file's opening section would not hold: the parent's context would grow by some fraction of the subagent's internal work rather than by a fixed, small summary, and the whole cost-saving case for delegating in the first place would erode in proportion to how much leaked. "One message out" is what guarantees the saving is bounded regardless of how much work the subagent did to produce it.

This is also why the *shape* of that one message matters as much as its existence. A subagent that returns a wall of raw findings pasted back verbatim defeats the boundary's purpose almost as badly as if intermediate calls leaked through — the parent's context still grows by the full weight of the investigation, just relocated into a single message instead of many. The disciplined shape is a return protocol: status, a short list of findings, and a file path for anything long enough to be re-read on demand rather than re-paid for on every subsequent turn — never a raw data payload. §2.1.25, four files from here, is where that protocol gets its own full treatment; carry forward for now only that the one-message design is *why* the protocol exists, not an arbitrary style rule layered on top of it.

**`[TRAP]`** Put the two lists side by side and one law falls out of them directly: **a subagent knows nothing your session has learned, no matter how obvious that knowledge feels from inside the main conversation.** Everything it needs — the convention you corrected it on, the file whose contents matter, the skill whose output it should build on — has to be placed explicitly into either the task string or a file the task string tells it to read. Nothing crosses by osmosis.

**Pitfall:** dispatching a subagent with a task like "apply the same refactor we just discussed to the payment module" — a sentence that is perfectly clear inside the main conversation, where "we just discussed" resolves to specific messages sitting in context. **Surprising outcome:** the subagent has no conversation history (§2.1.10's first blocked item) and no idea what "the same refactor" refers to; it either asks a clarifying question it cannot actually get answered (it has no channel back except its one final message) or guesses, often wrongly. **Fix:** write the task string as if briefing a competent engineer who has never seen this codebase or this conversation — restate the refactor concretely, or point at a file that spells it out, rather than referring back to shared history that does not exist on the other side of the boundary. **Why people believe it:** the main session's fluency creates the illusion that context is a property of the *task*, when it is really a property of the *conversation* — and the conversation is exactly what does not cross.

**Interview:** "If a subagent reads through fifteen files while investigating a bug, does any of that show up in the main conversation afterward?" — No. Only the one final message the subagent returns is appended to the parent's history; every intermediate tool call, including all fifteen file reads, stays inside the subagent's own discarded context window. That is the mechanism, not an implementation detail — it is what makes delegating the investigation cheaper than doing it inline in the first place.

## The agents-versus-skills inversion, tabled

The previous file's closing pitfall named this inversion in passing, for subagent precedence specifically. Its mirror on the skills side is worth its own table, because the two orders really do run opposite, and there is no underlying principle that predicts either one from the other — each has to be memorized on its own terms.

| | Highest priority | → | → | → | Lowest priority |
|---|---|---|---|---|---|
| **Agents** | Managed settings | `--agents` CLI flag | `.claude/agents/` (project) | `~/.claude/agents/` (user) | Plugin `agents/` |
| **Skills** | Enterprise (managed settings) | Personal `~/.claude/skills/` | Project `.claude/skills/` | — | — |

For agents: **project beats user** — `.claude/agents/` (priority 3) outranks `~/.claude/agents/` (priority 4).

For skills, quoting the `skills` doc page directly: "Across levels, enterprise overrides personal, and personal overrides project." `[DOC]` So **personal beats project** — `~/.claude/skills/` outranks the project's own `.claude/skills/`; the doc's own worked example makes this concrete: "with a `deploy` skill in both `~/.claude/skills/` and your project's `.claude/skills/`, `/deploy` runs the personal one."

![D-43 — Agents and skills order oppositely. Two subsystems, two orders.](../diagrams/D-43-agents-vs-skills-precedence.svg)

**D-43** — Agents and skills order oppositely. Two subsystems, two orders.

**Insight:** the previous file's pitfall already gave the closest thing to a rationale either subsystem offers — a subagent leans toward shared team tooling, so the project copy should win over an individual's silent override; a skill leans toward personal workflow habit, so the individual's copy should win over whatever the project ships. That rationale is plausible, but it is a story told *after* the fact to make the two orders memorable, not a principle either doc derives its precedence table from — nothing in either file format enforces or even hints at the other's ordering, and nothing stops a future release from picking a third convention for the next kind of definition file it adds. **The honest position is that this has to be memorized, not derived**, which is exactly why it survives as durable interview material: it rewards a candidate who has actually used both systems long enough to have been bitten by the mismatch once, over one who has only read a single doc page.

**Interview:** "If both `~/.claude/skills/deploy/` and `.claude/skills/deploy/` define a `/deploy` skill, and both `~/.claude/agents/mvn-test-runner.md` and `.claude/agents/mvn-test-runner.md` define an `mvn-test-runner` agent, which wins in each case?" — The personal skill wins (`~/.claude/skills/` outranks project for skills), and the project agent wins (`.claude/agents/` outranks user for agents). Same shape of question, opposite answer, because the two subsystems are ordered in opposite directions and nothing besides memorizing the two tables tells you which is which.

## Pitfalls

- **Belief in action:** "This subagent's task is to fix whatever `git status` shows as dirty right now, and the subagent already has git status in its injected context, so it doesn't need to run the command itself." **Surprising outcome:** the injected git status was captured when the parent session started, potentially hours and dozens of commits earlier, so the subagent may "fix" files that are already clean, or miss ones that are now genuinely dirty. **What actually gets the guarantee:** put "run `git status` yourself before doing anything else" in the subagent's task message or system prompt whenever the task depends on the *current* working-tree state, exactly as the previous file's `readonly-reviewer` definition opens with `git diff` rather than trusting any injected snapshot. **Why people believe it:** every other piece of injected startup context is either genuinely fresh (the task message) or slow-changing enough that staleness rarely bites (`CLAUDE.md`); git status is the one fast-changing exception, and nothing in the frontmatter or the UI flags it as a snapshot rather than a live read.
- **Belief in action:** "I taught Claude months ago, through repeated correction, to always use constructor injection instead of field injection in this codebase — that preference is baked in by now, so any subagent I dispatch will follow it too." **Surprising outcome:** the subagent's context contains none of that history — auto memory does not cross the subagent boundary (a fork excepted), so a preference that exists only as accumulated conversational correction is simply absent inside a delegated task, and the subagent may reintroduce exactly the pattern it was trained out of in the main session. **What actually gets the guarantee:** promote the durable preference into `CLAUDE.md`, which does cross the boundary in full (§2.1.8), or restate it explicitly in the task message for that dispatch. **Why people believe it:** in the main session the correction feels permanent because it is still sitting in the same context window being re-sent every turn; nothing about that experience signals that the "memory" is really just conversation history that a fresh subagent context never receives.

## Cheat sheet

| Item | Value |
|---|---|
| `description` routing budget | ~15,000 tokens combined, shared across every custom agent in the session `[NUM]` |
| `tools` with an MCP tool | Name it exactly: `mcp__<server>__<tool>` |
| `tools` restricting sub-delegation | `Agent(agent-a, agent-b)` — grants `Agent`, restricts its target roster |
| Crosses inward | Own system prompt + env, task message, full `CLAUDE.md` hierarchy (Explore/Plan excepted), git-status snapshot from parent session start, preloaded `skills`, sibling roster (v2.1.206+) |
| Crosses outward | Exactly one final message |
| Blocked at the line | Conversation history, main output style, auto memory, previously read files, previously invoked skills |
| Git-status snapshot timing | Parent session start — not dispatch time, never refreshed |
| Fork exception | Inherits the entire conversation; all of the above no longer applies |
| Agent precedence, highest first | Managed settings → `--agents` CLI → project `.claude/agents/` → user `~/.claude/agents/` → plugin `agents/` |
| Skill precedence, highest first | Enterprise → personal `~/.claude/skills/` → project `.claude/skills/` |
| Agent vs. skill winner | Agents: project beats user. Skills: personal beats project. Opposite orders, no shared principle. |

## Self-test

1. What is the `description` routing budget, and is it per-agent or shared?
<details><summary>Answer</summary>Roughly 15,000 tokens, and it is a single shared pool across the combined `description` text of every custom agent definition loaded for the session — not a per-agent allowance. One verbose agent's description can crowd out another's chance of ever being selected.</details>

2. How does a subagent's `tools` field grant access to one specific MCP tool, and how does it restrict which agents it can itself dispatch to?
<details><summary>Answer</summary>For an MCP tool, name it in its fully namespaced form, `mcp__<server>__<tool>` (e.g. `mcp__ide__getDiagnostics`), alongside any built-in tool names. For sub-delegation, grant the `Agent` tool with a parenthesized allowlist of agent names, e.g. `Agent(mvn-test-runner, readonly-reviewer)`, which permits the `Agent` tool but restricts its argument to those names.</details>

3. List everything that crosses into a freshly-dispatched, non-fork subagent's initial context.
<details><summary>Answer</summary>Its own system prompt plus environment details; the task message; the full CLAUDE.md hierarchy (except for the built-in Explore and Plan agents, which omit CLAUDE.md and git status); a git-status snapshot taken at parent session start; any skills preloaded via the `skills` frontmatter field; and, from Claude Code v2.1.206 onward, a sibling roster naming `main` and every other named agent in the session.</details>

4. When exactly is the git-status snapshot handed to a subagent taken, and what is the practical consequence?
<details><summary>Answer</summary>At the start of the parent session, not at the moment the subagent is dispatched, and never refreshed afterward. A session running for hours across many commits dispatches every subagent with the same stale picture of the working tree from session start; a subagent whose task depends on current repository state must run `git status` or `git diff` itself rather than trust the injected snapshot.</details>

5. List everything that does not cross into a non-fork subagent, and name the one documented exception to all of them.
<details><summary>Answer</summary>Conversation history, the main session's output style, auto memory, previously read files, and previously invoked skills. Forks are the exception — a fork inherits the entire parent conversation, including all five of these, instead of starting fresh.</details>

6. How many messages does a subagent return to its parent, and why does that number matter?
<details><summary>Answer</summary>Exactly one final message; none of its intermediate tool calls, file reads, or dead ends are visible to the parent. That single-message return is what makes the context-economy argument for subagents (from the previous file) hold: the parent's context grows by a small, bounded summary regardless of how much work the subagent did internally, rather than by some fraction of that work leaking through.</details>

7. A reader has spent months correcting Claude's behaviour in their main session until it reliably follows a house convention. They then dispatch a subagent to make a related change. Does the subagent know the convention?
<details><summary>Answer</summary>Not automatically. That correction lives in the main session's auto memory or conversation history, neither of which crosses the subagent boundary (a fork excepted). Unless the convention is written into CLAUDE.md — which does cross in full — or restated explicitly in the task message, the subagent starts with no knowledge of it.</details>

8. Rank the precedence order for skill definition locations, highest first, and state which wins between personal and project.
<details><summary>Answer</summary>Enterprise (managed settings), then personal (`~/.claude/skills/`), then project (`.claude/skills/`). Personal beats project — the opposite of the agent ordering, where project beats user.</details>

9. Why does the agents-versus-skills precedence inversion make good interview material?
<details><summary>Answer</summary>Because there is no principle that predicts one ordering from the other — each doc's precedence table is its own convention, not a derivation from some shared rule — so answering correctly requires having actually used both systems and been bitten by the mismatch, not just having skimmed one page.</details>

## Open questions

None.

---

**Leaves covered:** 2.1.6–2.1.10 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-43
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 200
