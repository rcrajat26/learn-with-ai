# 21 AI for Coding — subagent definition and precedence — INTERMEDIATE (§2.1.1–2.1.5)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [PARTs 0 and 1 — the interview wrap-up](../90-interview-basics.md) · Next: [the subagent context boundary](02-the-context-boundary.md)

## What a subagent is

The mental model first, before any definition: right now, in this conversation, there is exactly one agent loop running — one context window, growing turn by turn, with your whole exchange re-sent on every call. A **subagent** is what happens when that loop spawns a *second*, independent loop: a fresh, empty context window, seeded with a task description instead of your conversation history, that runs its own sequence of model calls and tool calls to completion and then hands back exactly one message. The parent loop pauses while this happens and resumes with that one message appended to its own history — it never sees the subagent's intermediate tool calls, file reads, or dead ends.

This matters because two things you already know look similar and are not the same mechanism:

- **A skill** (PART 1) is a block of instructions injected into *this* conversation's context. No new loop starts, no new context window opens, nothing returns — the skill's content just becomes part of what the current agent is reading on its next call.
- **A subagent** starts a *second* agent loop with its *own* context window. The parent's context does not grow by the subagent's internal work — only by the one summary message that comes back.
- **A fork** (§2.1.13, covered two files from here) also starts a second loop, but seeds it with the *entire* parent conversation rather than a blank task string — it inherits, a subagent does not.

Definition, from the official docs: "Subagents are specialized AI assistants that handle specific types of tasks. Use one when a side task would flood your main conversation with search results, logs, or file contents you won't reference again: the subagent does that work in its own context and returns only the summary." Mechanically: "Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions. When Claude encounters a task that matches a subagent's description, it delegates to that subagent, which works independently and returns results." (Source: `sub-agents` doc page, re-verified 2026-08-29 against `https://code.claude.com/docs/en/sub-agents`.)

Nothing else crosses the boundary in either direction beyond what those two sentences describe — no shared file handles, no shared conversation state, no live back-and-forth. The next file, §2.1.6–2.1.10, walks that boundary leaf by leaf: what goes in, what single thing comes out, and what is blocked at the line. Here you need only the shape of it, because the shape is what "definition file" and "precedence" are definitions *of*.

![D-42 — The subagent context boundary. What crosses in, what crosses out, and what is blocked at the line.](../diagrams/D-42-subagent-context-boundary.svg)

**D-42** — The subagent context boundary. What crosses in, what crosses out, and what is blocked at the line. The next file walks each of these crossings one at a time; here it is enough to see that the boundary exists and that it is asymmetric — a task string goes in, one message comes out, and everything in between is invisible to the parent.

**Insight:** the reason subagents exist at all is context economy. If a task would require reading twelve log files to find one root cause, doing that inline burns your main context window on eleven files' worth of dead weight you'll never reference again. A subagent absorbs that cost in a context window that gets thrown away when it returns, and your main conversation only grows by the one-paragraph answer.

Put a number on that, because "context economy" is otherwise just a slogan. Suppose those twelve log files average 2,000 tokens each read in full — 24,000 tokens. Read inline, every one of those 24,000 tokens is re-sent on every subsequent turn of the conversation for as long as it stays in the context window, because (from PART 0) the whole conversation is re-sent every turn. Dispatched to a subagent instead, those 24,000 tokens are spent once, inside a context window that is discarded the moment the subagent returns its summary — the parent's context grows by however long that summary is, commonly a few hundred tokens, not by 24,000. The saving compounds: a conversation that goes another thirty turns after the investigation pays the re-send cost of that summary thirty times, not the re-send cost of twelve raw log files thirty times.

> A subagent is a separate agent loop, with its own context window, invoked with a task description and returning exactly one final message to the loop that spawned it.

## Where a subagent is defined, and the precedence order

Like skills, a subagent is a file, not a database row — a Markdown file with YAML frontmatter, found by the harness at startup by scanning a fixed set of locations. Unlike skills, this family has **five** locations, not two, and (state this once, plainly, and defer the comparison) the order runs the *opposite* direction from the skill order the reader already knows.

From the `sub-agents` doc page, the precedence table, highest first:

| Priority | Location | Scope |
|---|---|---|
| 1 (highest) | Managed settings | Organization-wide |
| 2 | `--agents` CLI flag | Current session |
| 3 | `.claude/agents/` | Current project |
| 4 | `~/.claude/agents/` | All your projects |
| 5 (lowest) | Plugin's `agents/` directory | Where the plugin is enabled |

**`.claude/agents/` (priority 3) outranks `~/.claude/agents/` (priority 4). Project beats user.** When two locations define an agent with the same `name`, the one from the higher-priority location wins outright — the loser is not merged in, not consulted as a fallback; it simply never loads.

**Pitfall:** for skills (§1.5, PART 1) you learned personal beats project — `~/.claude/skills/` outranks `.claude/skills/` — because a skill is a personal workflow habit you carry between projects. Subagents invert that: `.claude/agents/` outranks `~/.claude/agents/`, because a subagent is closer to shared team tooling — a `readonly-reviewer` or an `mvn-test-runner` that the whole team should get identically when they clone the repo, not something an individual silently overrides from their home directory. Two subsystems, two opposite orders, and mixing them up produces exactly the failure it sounds like: an engineer edits `~/.claude/agents/mvn-test-runner.md` expecting to override the project's version, and the project's copy in `.claude/agents/` keeps winning because project beats user for agents, full stop. **Fix:** if a project-scoped agent needs a personal override, there isn't one — edit the project file, or use the `--agents` CLI flag (priority 2) for a session-scoped override, since that outranks the project directory. The full side-by-side of both orderings, with the ordering diagram, is the next file's opening section (§2.1.6) — do not reach for it here.

**Interview:** "Which wins, a project-level or a user-level subagent with the same name?" — Project. `.claude/agents/` is priority 3, `~/.claude/agents/` is priority 4, and lower-numbered priority wins. It's the mirror image of the skill answer, and naming that mirror is the whole answer an interviewer wants.

### A complete agent definition

The file format is YAML frontmatter followed by a Markdown system prompt — the same two-part shape as a `SKILL.md`, but a different field set and a different role: where a skill's body is instructions injected into the *current* loop, an agent's body is the system prompt for a *new* one.

Here is a complete, real definition — `readonly-reviewer`, a subagent that reviews a diff without being able to touch the working tree:

```markdown
---
name: readonly-reviewer
description: Reviews a git diff or pull request for correctness bugs and code-quality issues without modifying any files. Use proactively after a feature branch is ready for review, before opening a pull request.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: sonnet
permissionMode: default
maxTurns: 40
---

You are a code reviewer with read-only access to the repository. You never modify
files — your only output is a written review.

Given a diff or a branch name:

1. Run `git diff` (or `git diff <base>...<head>`) to see the full change set.
2. Read any file the diff touches in full, not just the changed hunks, so you can
   see the surrounding logic the diff assumes.
3. Look for: correctness bugs, missing null/empty checks, resource leaks, and
   places where existing project conventions are broken.
4. Report findings as a ranked list: most severe first, each with a one-line
   summary, the file and line, and the concrete failure scenario.

Do not attempt to fix anything. Do not run any command that writes to the
repository, even if asked.
```

Every field earns its place: `name` is how the parent addresses it and how other definitions collide by name during precedence resolution; `description` is what the parent reads to decide whether this is the right subagent for the current task (§2.1.4 below); `tools` and `disallowedTools` together fix its capability surface; `model` pins which underlying model runs the loop; `permissionMode` and `maxTurns` bound how it behaves once running. The body below the frontmatter is a real system prompt — a numbered procedure and an explicit negative instruction — not a placeholder paragraph.

A second example, this time showing what a *collision* looks like rather than a single well-formed definition. Suppose both `.claude/agents/progress-verifier.md` (project-scoped, checked into the repo, priority 3) and `~/.claude/agents/progress-verifier.md` (a personal experiment, priority 4) exist with the same `name: progress-verifier`:

```markdown
---
name: progress-verifier
description: Reads a story's acceptance criteria and its diff, then reports whether the implementation actually satisfies each criterion. Use proactively before marking a story done.
tools: Read, Grep, Glob, Bash
model: sonnet
maxTurns: 25
---

You verify completed work against its stated acceptance criteria. You do not
implement fixes and you do not approve work you have not personally checked
against the diff.

Given a story's acceptance criteria and its branch:

1. Read each acceptance criterion individually.
2. For each one, find the specific lines of the diff that satisfy it, or
   conclude that nothing in the diff satisfies it.
3. Report a per-criterion verdict: SATISFIED (with the file and line), or
   NOT SATISFIED (with what is missing).

Never report SATISFIED without pointing to the specific lines that satisfy it.
```

Whatever the personal `~/.claude/agents/progress-verifier.md` file says — a looser `description`, a different `model`, extra `tools` — none of it loads. The harness resolves the name once, at the highest-priority location that defines it, and stops looking. There is no merge across locations and no fallback to the loser if the winner's definition is somehow incomplete; an incomplete winner is just an incomplete subagent.

**No gotcha here beyond the one already stated above:** the file-location precedence has exactly one surprising edge, and it's the inversion already covered as a `**Pitfall:**`. There is nothing further to trip over in *where* the file lives once you know that order.

## Every frontmatter field

The full field list, re-verified against the `sub-agents` doc page immediately before writing this section:

| Field | Required | What it does |
|---|---|---|
| `name` | Yes | Unique identifier, lowercase letters and hyphens. The filename does not have to match it. Cannot contain `:` — that character is reserved for plugin-scoped identifiers. |
| `description` | Yes | The sentence the parent model reads to decide whether to delegate here. See §2.1.4. |
| `tools` | No | The tools this subagent may use. See §2.1.5. |
| `disallowedTools` | No | Tools to deny, removed from the inherited or specified list. If both `tools` and `disallowedTools` are set, `disallowedTools` is applied first, then `tools` is resolved against what remains — a tool listed in both is removed. |
| `model` | No | `sonnet`, `opus`, `haiku`, `fable`, a full model ID (e.g. `claude-opus-5`), or `inherit`. Defaults to `inherit` — the subagent runs on whatever model the parent session is using unless told otherwise. |
| `permissionMode` | No | One of `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, or `manual` (an alias for `default`). Ignored for plugin subagents. |
| `maxTurns` | No | Caps the number of agentic turns before the subagent is stopped mid-task. When the cap is hit, Claude Code returns the output marked as partial rather than silently truncating it. |
| `skills` | No | Skills to preload into the subagent's own context at startup — the full skill content is injected before the subagent's first turn, not merely made available for it to invoke. |
| `mcpServers` | No | MCP servers available to this subagent; each entry is either a server name or an inline definition. Ignored for plugin subagents. |
| `hooks` | No | Lifecycle hooks scoped to this subagent alone. Ignored for plugin subagents. |
| `memory` | No | Persistent memory scope: `user`, `project`, or `local` — enables the subagent to carry learning across separate invocations. |
| `background` | No | `true` keeps this subagent running in the background even when the parent asks for it in the foreground. |
| `effort` | No | Overrides the session's effort level while this subagent is active: `low`, `medium`, `high`, `xhigh`, or `max`. |
| `isolation` | No | `worktree` runs the subagent against a temporary git worktree — an isolated copy of the repository — rather than the live working tree. |
| `color` | No | Display color in the UI: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, or `cyan`. Cosmetic only. |
| `initialPrompt` | No | Auto-submitted as the first user turn when this definition is run as the *main session* agent (via `--agent` or the `agent` setting) rather than delegated to — a different mode from ordinary subagent delegation. |
| `experimental` | No | A map of experimental options; today its only documented key is `cacheTtl`, set to `5m` or `1h` to choose the prompt-cache lifetime for this subagent's requests. |

`permissionMode` deserves one more sentence beyond the table, because it is easy to conflate with `tools`/`disallowedTools` and the two do different jobs. `tools` and `disallowedTools` decide *which* tools exist for this subagent at all — the capability surface. `permissionMode` decides how the harness handles a permission check for a tool that *is* in that surface — whether an edit is auto-approved (`acceptEdits`), whether every tool call still asks (`default`/`manual`), or whether checks are skipped entirely (`bypassPermissions`). A `readonly-reviewer` with `tools: Read, Grep, Glob, Bash` and `permissionMode: bypassPermissions` is not thereby granted Write or Edit — `bypassPermissions` only removes the ask-step for tools already inside the `tools` allowlist; it cannot widen that allowlist. The two fields are independent, and setting one aggressively does not compensate for a loose setting of the other.

**`[VERSION]`** this field list is current as of Claude Code v2.1.2xx (August 2026); several of these fields — `background`, `effort`, `isolation`, `memory`, `experimental` — are recent additions to the subagent frontmatter and did not exist in earlier release lines. A guide or blog post written against an older binary will show only `name`, `description`, `tools`, and `model`, and will describe that shorter list as complete. It was complete, for its version.

Three of the newer fields are worth a second look because they change what "returns one message" (the definition from §2.1.1) can mean in practice, without contradicting it. `isolation: worktree` does not change how many messages cross the boundary — still exactly one — but it changes what the subagent's tool calls are allowed to touch while it runs: a temporary git worktree rather than the shared working tree, so a subagent doing exploratory edits cannot collide with files the parent or a sibling subagent is touching concurrently. `background: true` changes when that one message arrives, not whether one arrives — the parent can keep working and collect the result later instead of blocking on it. `memory` is the one field that appears to violate "own, blank context window" from §2.1.1, and it is worth being precise about why it does not: memory is not conversation history carried forward — the subagent still starts each dispatch with an empty context window and no visibility into its own prior runs' turns — it is a small persisted note the subagent can choose to write and read back, scoped to `user`, `project`, or `local`. The boundary in D-42 still holds; `memory` is a side channel that writes to disk, not a wire that stays open between dispatches.

## The `description` field decides whether the subagent is ever used

This is the field that matters in practice, and the reader has already met the shape of the problem twice: the parent model chooses a tool to call from nothing but that tool's description (§0.3.6), and it chooses a skill to load from nothing but that skill's listing entry (§1.5.22). A subagent is chosen the same way — **from its `description` alone**, before any of its other fields are ever read.

From the docs: "Claude uses each subagent's description to decide when to delegate tasks. When you create a subagent, write a clear description so Claude knows when to use it." And, on the delegation decision itself: "Claude automatically delegates tasks based on the task description in your request, the `description` field in subagent configurations, and current context. To encourage proactive delegation, include phrases like 'use proactively' in your subagent's description field." (Source: `sub-agents` doc page, re-verified 2026-08-29.)

The failure this produces is the same failure the reader has now seen in two other subsystems, so name the pattern rather than re-deriving it: **a description that names the topic instead of the trigger produces a subagent that is either never selected or always selected.** `description: Reviews code` names a topic — every task in a coding session is arguably "about code" in some loose sense, so the parent either never has a confident enough match to delegate, or (worse) matches on everything and hijacks tasks that should stay inline. Compare that to `readonly-reviewer`'s actual description above — "Reviews a git diff or pull request for correctness bugs and code-quality issues without modifying any files. Use proactively after a feature branch is ready for review, before opening a pull request." — which names a concrete trigger (a diff exists, a branch is ready) and an explicit invitation to act on it unprompted.

**Pitfall:** writing `description: Handles testing` for an agent meant to run Maven's test suite and summarize failures. The belief is that the description is documentation for a human reading the file. The symptom is that the parent either never delegates to it (nothing says "handles testing" strongly enough to beat just running the tests inline) or delegates to it for unrelated tasks that happen to mention the word "test" in passing — a task about writing a test plan document, say. **Fix:** `description: Runs the full Maven test suite and reports which tests failed and why. Use proactively after any change to source under src/main/java, before the change is considered done.` — names the concrete action (`mvn test`), the concrete trigger (a `src/main/java` change), and invites proactive use in the same sentence the docs recommend for it. Give it a name that matches: `mvn-test-runner`, not `test-agent`.

## The `tools` field: a genuine restriction, not a pre-approval

The reader has just learned, in PART 1, that a skill's `allowed-tools` field is commonly misread as a security boundary when it is actually a pre-approval that grants permission for the invoking turn only and clears on the next user message — every other tool stays callable regardless. **A subagent's `tools` field is the opposite of that: it is a genuine allowlist, and it is a real restriction on what the subagent can do, not a one-turn permission grant.**

From the docs, stated directly: "To restrict tools, use the `tools` field as an allowlist or the `disallowedTools` field as a denylist," illustrated with `tools: Read, Grep, Glob, Bash`, of which the docs say plainly: "The subagent can't edit files, write files, or use any MCP tools." That is an enforced capability boundary for the entire lifetime of the subagent's run, not a single-turn grant — there is no "next user message" for a subagent to fall back past, because the subagent's whole life is one dispatch.

If `tools` is omitted entirely, the subagent "inherits every tool available to subagents if omitted" — the default is maximal, not minimal, so a definition with no `tools` field at all is not "no tools," it is "every tool the parent session itself has access to." The `readonly-reviewer` definition above relies on both mechanisms together: `tools: Read, Grep, Glob, Bash` names what it may use, and `disallowedTools: Write, Edit` removes two of the more dangerous ones explicitly even though they weren't listed in `tools` to begin with, giving a reviewer of someone else's code two independent reasons it cannot silently start editing the diff it's supposed to be critiquing. Where both fields are set, `disallowedTools` is applied first and `tools` is resolved against what remains, so a tool named in both is removed — `disallowedTools` cannot be defeated by also naming the same tool in `tools`.

**Insight:** this is the precise reverse of the skill case, and that reversal is the whole point of putting the two fields side by side. `allowed-tools` on a skill answers "what may this skill invoke *without an extra prompt* for the rest of this one turn" — a convenience, not a fence. `tools` on a subagent answers "what can this subagent ever touch, for the whole of its dispatched life" — an actual fence, enforced by the harness for every tool call the subagent's loop attempts to make. Reading `tools` as a mere pre-approval, by analogy with the skill field, produces the opposite mistake from the skill pitfall: someone omits `tools` from a subagent definition assuming that's the safe, minimal default, when the doc-confirmed default is the maximal one — every tool the parent session has.

**Interview:** "Does a subagent's `tools` field actually restrict what it can do, or is it just a hint like a skill's `allowed-tools`?" — It's a real restriction: the harness enforces it as an allowlist for the whole run, `disallowedTools` is applied first as a denylist, and if either eliminates a tool the subagent needs to complete its task it typically fails to launch or errors on the call, rather than silently ignoring the boundary.

One more failure mode worth naming explicitly, because it follows directly from "genuine restriction" rather than "pre-approval": if the `tools` list names an entry that does not resolve to any real tool the parent session actually has — a typo, or a tool gated behind a permission the parent itself lacks — the docs state the consequence plainly: "If no entry in the list resolves to a tool, the subagent usually fails to launch with an error." That failure happens at dispatch time, before the subagent's system prompt ever runs a single turn, which is exactly what you would expect from an enforced allowlist and would not expect from a pre-approval mechanism — a skill with a broken `allowed-tools` entry does not refuse to load, because that field was never gating anything to begin with.

## Deferred

None.

## Pitfalls

- **Belief in action:** "I'll drop a personal override into `~/.claude/agents/mvn-test-runner.md` to change how the project's test-runner subagent behaves for me alone." **Surprising outcome:** the project's `.claude/agents/mvn-test-runner.md` keeps winning every time, silently — the personal file never loads while a same-named project file exists. **What actually gets the guarantee:** edit the project file directly (it's shared, that's the design), or pass a session-scoped override via the `--agents` CLI flag, which sits at priority 2, above `.claude/agents/` at priority 3. **Why people believe it:** they generalize from the skill precedence they learned first, where `~/.claude/skills/` (personal) legitimately outranks `.claude/skills/` (project) — the two subsystems simply order oppositely, and nothing in either file format warns you which one you're editing.
- **Belief in action:** "I left `tools` off my subagent definition, so it starts with nothing and I'll add tools as I need them." **Surprising outcome:** the subagent launches with every tool the parent session itself has — including `Bash`, `Write`, and `Edit` — because omitting `tools` inherits the maximal set, not the empty one. **What actually gets the guarantee:** name the allowed tools explicitly, e.g. `tools: Read, Grep, Glob, Bash`, or add `disallowedTools` to remove specific dangerous ones from the inherited set. **Why people believe it:** in most permission systems outside Claude Code, an unconfigured allowlist defaults to empty ("deny by default"); this one defaults to "inherit everything," which is the opposite convention and easy to assume away.

## Cheat sheet

| Item | Value |
|---|---|
| What a subagent is | A separate agent loop, own context window, task in / one message out |
| Definition file locations, highest first | Managed settings → `--agents` CLI → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/` |
| Agent precedence winner | Project (`.claude/agents/`) beats user (`~/.claude/agents/`) |
| Skill precedence winner (for contrast) | User (`~/.claude/skills/`) beats project (`.claude/skills/`) — the inverse |
| File format | YAML frontmatter + Markdown system prompt |
| Required fields | `name`, `description` |
| Selection mechanism | Parent model reads `description` alone to decide whether to delegate |
| `tools` omitted | Inherits every tool available to the subagent |
| `tools` field | Enforced allowlist for the entire run |
| `disallowedTools` field | Enforced denylist; applied before `tools` is resolved |
| `model` default | `inherit` (runs on the parent session's model) |

## Self-test

1. What crosses the subagent boundary, in each direction?
<details><summary>Answer</summary>A task description crosses in from the parent. Exactly one final message crosses back out. Nothing else — no shared conversation state, no intermediate tool calls, no file handles — crosses in either direction.</details>

2. Rank the five subagent definition locations from highest to lowest precedence.
<details><summary>Answer</summary>Managed settings, then the `--agents` CLI flag, then `.claude/agents/` (project), then `~/.claude/agents/` (user), then a plugin's `agents/` directory.</details>

3. For subagents, does project or user scope win when both define an agent with the same name? How does this compare to skills?
<details><summary>Answer</summary>Project wins for subagents (`.claude/agents/` outranks `~/.claude/agents/`). This is the inverse of skills, where user/personal scope (`~/.claude/skills/`) outranks project scope (`.claude/skills/`).</details>

4. What decides whether the parent model delegates a task to a given subagent?
<details><summary>Answer</summary>The subagent's `description` field alone — the same mechanism by which the model picks a tool from a tool description or a skill from its listing entry. There is no separate matching step that reads the subagent's body or its other frontmatter fields before deciding to delegate.</details>

5. What happens if a subagent definition's `description` names the topic ("Handles testing") rather than a concrete trigger?
<details><summary>Answer</summary>It produces a subagent that is either never selected — because nothing signals confidently enough that this is the right moment — or selected for unrelated tasks that happen to share vocabulary with the topic. The fix is a description naming a concrete action and a concrete trigger, e.g. "Runs the full Maven test suite... use proactively after any change to source under src/main/java."</details>

6. Is a subagent's `tools` field a restriction or a pre-approval? Contrast it with a skill's `allowed-tools`.
<details><summary>Answer</summary>It is a genuine, enforced restriction — an allowlist for the entire lifetime of the subagent's dispatch. A skill's `allowed-tools`, by contrast, only pre-approves tool calls for the invoking turn and clears on the next user message; every other tool remains callable regardless, so it is not a security boundary at all.</details>

7. What is the default tool set for a subagent definition that omits `tools` entirely?
<details><summary>Answer</summary>It inherits every tool available to subagents — the maximal set, not the empty one. Omitting `tools` is not the same as denying all tools.</details>

8. If both `tools` and `disallowedTools` are set on the same subagent and a tool appears in both, which one wins?
<details><summary>Answer</summary>`disallowedTools` is applied first, removing that tool from the inherited pool; `tools` is then resolved against what remains. A tool named in both ends up removed either way.</details>

9. What is the default value of the `model` field on a subagent, and what does it mean?
<details><summary>Answer</summary>`inherit` — the subagent runs on whichever model the parent session is currently using, unless the definition explicitly pins `sonnet`, `opus`, `haiku`, `fable`, or a full model ID.</details>

## Open questions

None.

---

**Leaves covered:** 2.1.1–2.1.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-42
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 234
