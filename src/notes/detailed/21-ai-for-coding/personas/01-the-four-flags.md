# 21 AI for Coding — four ways to set a persona — INTERMEDIATE (§2.2.1–2.2.4)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [write boundaries, withheld tools and the return protocol](../subagents/06-write-boundaries-and-protocol.md) · Next: [how a real engine loads a persona](02-cases-persona-loading.md)

The subagents area established where a subagent lives, what its context boundary is, what a fork
shares, and that a `tools:` field is a hard ceiling while a prose sentence is not. All of that
assumed you already had a *registered* agent — `.claude/agents/readonly-reviewer.md` or
`plugins/sdlc-harness/agents/calibrator.md` — sitting on disk before `--agent <name>` ever loaded
it. This file is about the moment before that: an engineer at a terminal, or a headless pipeline in
CI, decides they want a persona and reaches for one of four flags. Only one of them is `--agent`.
The other three look similar enough on the page that picking the wrong one is the single most
common way a persona goes wrong without anyone noticing until later.

## §2.2.1–2.2.4 The four flags, side by side

**D-48 first, because this file is built on the comparison, not on four separate stories.**

| Flag | What happens to the default system prompt | Model + tool allowlist come with it? | What you lose | Symptom when you pick the wrong one |
|---|---|---|---|---|
| `--agent <name>` | Loaded from the registered agent definition — the agent's own system prompt **replaces** the default one entirely | Yes — both ship with the definition | The default Claude Code persona and any tool the agent's `tools:` field omits | None if this is what you meant to do — this is the only flag of the four that carries an enforced tool boundary |
| `--append-system-prompt <text>` | **Appended** to the end of the default system prompt — the default persona is still there, decorated | No — no model field, no tool allowlist | Nothing structural — you only add text | **An agent that behaves almost right and ignores a tool restriction it never had** — the text can *ask* for restraint, but every tool the session already had stays fully callable |
| `--system-prompt <text>` / `--system-prompt-file <path>` | **Replaced** wholesale — the default prompt is gone, not decorated | No — no model field, no tool allowlist | The tool-use conventions and the environment framing (working directory, environment info, memory paths, git-repo flag) the default prompt was supplying | The model loses track of things it used to be told for free — confusion about the working directory, about whether it is inside a git repo, about `CLAUDE.md` memory it can no longer assume was surfaced |
| `--append-subagent-system-prompt <text>` | **Appended** to the end of *every subagent's* own system prompt for the run, nested subagents included | No — the flag only adds text, per subagent | The illusion that a persona addition is a one-agent decision — it now reaches agents you did not name | An org-wide policy note believed to live in one agent's file turns out to be silently duplicated into every subagent dispatched that run, at a token cost per dispatch |

**D-48** — Three ways to set a persona, and the fourth that reaches every subagent.

Re-verified against `https://code.claude.com/docs/en/cli-reference` and
`https://code.claude.com/docs/en/sub-agents` immediately before writing this file. The
`cli-reference` page states, verbatim, for each flag:

> `--agent` — "Specify an agent for the current session (overrides the `agent` setting)"
> `--append-system-prompt` — "Append custom text to the end of the default system prompt"
> `--system-prompt` — "Replace the entire system prompt with custom text"
> `--system-prompt-file` — "Load system prompt from a file, replacing the default prompt"
> `--append-subagent-system-prompt` — "Append custom text to the end of every subagent's system
> prompt, nested subagents included, apart from a forked subagent, which reuses the conversation's
> own prompt. Only applies in non-interactive mode with `-p`. Requires Claude Code v2.1.205 or
> later"

And the `sub-agents` page adds the detail the table above depends on for row one:

> "Pass `--agent <name>` to start a session where the main thread itself takes on that subagent's
> system prompt, tool restrictions, and model… The subagent's system prompt replaces the default
> Claude Code system prompt entirely, the same way `--system-prompt` does."

That last clause is the one worth sitting with: `--agent` is not a fifth, independent mechanism —
it is `--system-prompt`'s full-replace behaviour, plus a model field, plus a tool allowlist, all
three sourced from one registered file instead of typed at the command line. None of the four flags
here were found renamed or removed against v2.1.2xx; no divergence to flag on this row.

### `--agent <name>` versus `--append-system-prompt <text>` — the core confusion

**Mental model.** `--agent <name>` swaps the engine. `--append-system-prompt <text>` puts a bumper
sticker on the one that was already running. Both change what the model says about itself at the
start of the conversation; only one of them changes what the model is *permitted to do*.

**Why it exists.** `--append-system-prompt` exists because most persona needs are small — "this
repository's money fields are `BigDecimal`, never suggest `double`" — and registering a whole agent
file, with its own `tools:` list and its own `model:` field, is disproportionate for one sentence of
house style. `--agent` exists for the opposite case: a fixed, reusable, restricted persona that
needs the same tool ceiling every time it runs, unattended, inside a pipeline.

**When to reach for it, and when not.** Reach for `--append-system-prompt` when the only thing you
want to change is what the model is told, and the default tool set and default model are exactly
what you still want. Reach for `--agent` the moment the persona is supposed to come with a
restriction — "this run may only read and grep, never write or run shell commands" — because that
restriction has to live in a `tools:` field to be real, and `--append-system-prompt` has no `tools:`
field to put it in.

**How it works.** The default system prompt — Claude Code's own persona, the tool-use conventions
that tell the model the shape of a `tool_use` block and when to reach for one, and the environment
framing covered next — stays fully in place under `--append-system-prompt`; the custom text is
concatenated onto the end of it. Nothing about the session's tool set, model, or permission mode
moves. `--agent <name>` instead loads the named definition's `system prompt, tool restrictions, and
model` (`sub-agents` page, quoted above) and the loaded prompt **replaces** the default one — the
tool-use conventions and environment framing you get under `--agent` are whatever that agent
definition's own prompt supplies, not automatically Claude Code's defaults.

**Code.** The same review task, dispatched two ways from a shell:

```console
$ claude --append-system-prompt "This repository's money fields are java.math.BigDecimal; never propose double or float for currency." "Review the diff in payment-service for correctness"
```

```console
$ claude --agent readonly-reviewer "Review the diff in payment-service for correctness"
```

where `readonly-reviewer` is a registered agent definition —
`.claude/agents/readonly-reviewer.md` — whose frontmatter carries `tools: [Read, Grep, Glob]` and
no `Bash`, `Write`, or `Edit` at all. The first invocation's session still has every default tool
available, `Bash` included; the second's session cannot emit a `Write` or `Bash` `tool_use` block in
the first place, because the harness never offers it the schema.

**Gotcha — the failure mode this file exists to name.** Take the append form one step further: an
engineer, wanting the restriction rather than just the house style, writes
`--append-system-prompt "You are a read-only reviewer. Never edit files, never run destructive
commands."` and ships it. The resulting session **behaves almost right** — a reasonably well-behaved
model mostly does stick to reading and grepping, because the text is a real instruction and the
model does attend to it — **and ignores a tool restriction it never had.** `Write`, `Edit`, and
`Bash` are all still fully callable tools in that session; nothing stops the model from using one if
the task, an ambiguous instruction, or a confabulated shortcut makes it reach for one anyway. This is
the exact shape `06-write-boundaries-and-protocol.md`'s §2.1.23 named for a subagent with no
`tools:` field at all: **believing a restriction exists because a sentence describes it, when the
only thing that would make it real is a schema the model was never given.** The fix is not a
stronger sentence — it is `--agent <name>` pointed at a definition whose `tools:` field is the
narrow list, because that is the only one of these four flags where the tool allowlist travels with
the persona.

**Pitfall:** reaching for `--append-system-prompt` because it is one flag on the command line and
registering an agent file feels like overhead, then trusting the appended sentence as if it were a
permission boundary. **Symptom:** the model reads files it should not have written to, or runs a
command the persona text told it never to run, with no error and no denied-tool prompt, because
there was never a tool to deny. **Fix:** if the persona needs a restriction rather than a preference,
it needs `--agent <name>` against a definition with an explicit `tools:` list, not appended text.

**Interview:** "Someone says `--append-system-prompt` locked their session to read-only. What's
wrong with that?" — nothing is locked; `--append-system-prompt` only edits what the model is told,
never what tools it can call, so the session still has every default tool available and the
"read-only" behaviour is unenforced good behaviour, not a ceiling.

> `--append-system-prompt` decorates the default persona with text and changes nothing about which
> tools, model, or permissions the session has; only `--agent <name>` swaps in a tool allowlist and
> a model along with the prompt.

### `--system-prompt` / `--system-prompt-file` — replacing, not decorating

**Mental model.** `--append-system-prompt` adds a paragraph to the end of a book that is still
there. `--system-prompt` burns the book and hands the model a different one. It looks like a bigger
version of the same flag; it is a different act entirely, because everything the original book was
doing for the reader — not just its opening self-description — goes with it.

**Why it exists.** A headless integration that embeds Claude Code as a component of someone else's
product — the sdlc-harness's own `ClaudeRunner` is exactly this shape, discussed in full in
§3.6 — sometimes wants total authorship over what the model is told it is, with no trace of Claude
Code's own default framing bleeding through into a customer-facing tool. `--append-system-prompt`
cannot do that; the default persona is always still in there underneath whatever gets appended.
`--system-prompt` / `--system-prompt-file` can.

**When to reach for it, and when not.** Reach for it when the persona must be authored from a blank
page — a fixed, versioned prompt file that some other engineering team owns and that must not
silently pick up whatever Claude Code's own default prompt says this month. Do not reach for it for
the common case of "add a house-style note to an otherwise normal session" — that is
`--append-system-prompt`'s job, and it is the only one of the two that leaves the default
tool-use conventions and environment framing intact for free.

**How it works.** `--system-prompt <text>` takes the replacement inline on the command line;
`--system-prompt-file <path>` loads the same replacement text from a file, which is the practical
form for anything long enough to want version control. Both **replace the entire system prompt**
(`cli-reference`, quoted above) rather than appending to it. What "the entire system prompt" was
carrying, concretely, is named by the doc text for the sibling flag `--exclude-dynamic-system-prompt-sections`
below: **working directory, environment info, memory paths, and the git-repo flag** — plus the
tool-use conventions that tell the model the shape and etiquette of a `tool_use` block, covered in
§3.1's forward references and in PART 0. None of that ships automatically once `--system-prompt` is
set. If the replacement text does not re-state where the working directory is, whether the session
is inside a git repository, or where `CLAUDE.md` memory files were found, the model was never told
any of it — the harness does not fall back to appending its own framing underneath a full
replacement.

**Code.** A CI-owned persona file, loaded rather than typed inline, feeding a headless pipeline run
by `mvn-test-runner`'s sibling orchestration step:

```console
$ claude -p --system-prompt-file ./ci/personas/story-verification.txt --output-format json "Verify story-142's acceptance criteria against the merged diff"
```

`./ci/personas/story-verification.txt` is a plain text file — the flag's whole point is that it is
not JSON, not frontmatter, just the prompt text a platform team version-controls and reviews like
any other pipeline artefact.

**Gotcha.** The failure this produces looks different from the append-flag's failure: instead of a
tool it should not have, the model is missing context it used to get for free. A prompt author who
wrote `--system-prompt-file` content assuming the model would still know its own working directory
sees a session that asks the user where the repository is, or that treats a non-git directory as a
git repository because nothing told it otherwise — the same class of confusion
`--exclude-dynamic-system-prompt-sections` below exists to move somewhere else on purpose, happening
here by omission instead.

> `--system-prompt` and `--system-prompt-file` replace the default system prompt outright, taking
> with them the tool-use conventions and the environment framing the default prompt supplied —
> anything the replacement needs, the replacement has to re-state.

### `--append-subagent-system-prompt <text>` — the one that reaches every subagent

**Mental model.** `--append-system-prompt` is a note stuck to one desk. `--append-subagent-system-prompt`
is the same note photocopied and stuck to every desk in the building, including ones set up after
the memo went out — every subagent dispatched during that run, nested subagents included, gets its
own copy appended to its own system prompt, not shared, not deduplicated.

**Why it exists.** `06-write-boundaries-and-protocol.md`'s §2.1.19 already priced a fixed overhead
paid on every subagent dispatch — the 2× floor a subagent's own system prompt and tool schema cost
before it does any work. `--append-subagent-system-prompt` is that same per-dispatch tax, deliberately
incurred, in exchange for injecting one policy line into every subagent an orchestrator spawns
without hand-editing every registered agent file it might ever call. This is an **org-shaped
control**, not a per-run convenience: it belongs on the top-level invocation of a pipeline that
fans out to many subagents — an sdlc-harness-style `claude -p` orchestrator dispatching
`mvn-test-runner`, `readonly-reviewer`, and `progress-verifier` in the same run — where a platform
team wants one house-style fact ("this module's currency fields are `BigDecimal`") to reach all
three without touching three separate agent definitions.

**How it works.** The text is appended to the end of every subagent's own system prompt for that
run — the subagent still starts from its registered definition (or a built-in), and the extra text
lands after it, the same append semantics as `--append-system-prompt`, just fanned out. Nested
subagents (a subagent that itself dispatches a subagent) inherit the append too. **A forked
subagent does not** — per the doc text quoted in D-48, a fork "reuses the conversation's own
prompt," which is the same fact `05-cases-pointer-bodies.md` and `03-builtins-and-forks.md`
established about forks sharing the parent's own context rather than getting a fresh persona; there
is no separate subagent system prompt for the append to land on. Two constraints bound it further,
both from the doc text: **it only applies in non-interactive mode with `-p`**, and it **requires
Claude Code v2.1.205 or later** — an engineer on an older v2.1.1xx build who reaches for it gets no
effect from a flag their binary does not recognise as this feature, a version trap worth checking
before assuming the flag fired.

**Code.** The top-level orchestrator invocation, dispatching a verification pass that itself fans
out to subagents:

```console
$ claude -p --append-subagent-system-prompt "This repository's currency fields are java.math.BigDecimal; a subagent must never propose double or float for money." --output-format json "Run the full verification pass over story-142: run the test suite, review the diff, and check progress against the acceptance criteria"
```

The text never appears in the top-level session's own prompt — only `mvn-test-runner`,
`readonly-reviewer`, and `progress-verifier`, dispatched from inside that run, each get it appended
to their own system prompt.

**What this costs.** Every subagent dispatch that run pays the appended text's token count on top
of its own system prompt and tool schema, exactly the shape §2.1.19 priced as a per-dispatch tax —
a 40-token policy line appended across four subagent dispatches in one run is 160 extra input
tokens that run, and it recurs on every future run of the same pipeline, because the flag is set at
invocation time, not once in a file. That is the trade the "org-shaped control" framing is naming:
cheaper than editing every agent file by hand, not free.

**Gotcha.** The scope is the surprise, not the mechanism: a platform engineer who reasons about this
flag as "add a note to the subagent I'm about to dispatch" is really adding it to *every* subagent
the run touches, including ones added to the pipeline after the flag was set and forgotten about.
An audit of "why does `readonly-reviewer` mention `BigDecimal` when its own file never says that"
has to check the invoking command line, not just the agent definition.

**Interview:** "How would you inject one policy line into every subagent a pipeline dispatches,
without editing each agent file?" — `--append-subagent-system-prompt` on the top-level `-p`
invocation, understanding that it is a standing, per-dispatch cost paid by every subagent for the
life of that flag, not a one-time edit.

> `--append-subagent-system-prompt` appends text to every subagent's own system prompt for a
> non-interactive run, nested subagents included and forked subagents excluded, and is a per-dispatch
> cost incurred by an org-level decision rather than a single agent's own configuration.

### `--exclude-dynamic-system-prompt-sections` — supporting fact

**Mechanism.** Moves the **per-machine** parts of the default system prompt — working directory,
environment info, memory paths, and the git-repo flag — out of the system prompt itself and into
the first user message instead. The rest of the default prompt is unaffected. The stated purpose,
per the doc text, is prompt-cache reuse: a fixed system prompt with no per-machine text in it is
identical across different users and machines running the same scripted task, so it can share a
cache prefix where a system prompt carrying today's working directory could not. Intended usage is
scripted, multi-user workloads run with `-p`.

**Gotcha.** It only has an effect on the default system prompt — the doc text is explicit that it
is "ignored when `--system-prompt` or `--system-prompt-file` is set." An engineer who sets both
flags together, expecting the exclusion to also strip per-machine text out of their own replacement
prompt, gets no such effect; a full replacement was never carrying the dynamic sections it moves,
because those sections belong to the default prompt this flag is scoped to.

> `--exclude-dynamic-system-prompt-sections` relocates the default prompt's per-machine sections
> into the first user message to improve cache reuse across machines, and has no effect once
> `--system-prompt` or `--system-prompt-file` has already replaced the prompt it would have edited.

## Pitfalls

- **Belief:** "`--append-system-prompt` telling the model to stay read-only is the same guarantee as
  `--agent` pointed at a read-only agent definition." **Symptom:** the appended text is followed most
  of the time, and every tool including `Write`, `Edit`, and `Bash` is still fully callable, so the
  one time the model reaches for one anyway there was never a restriction to stop it. **Fix:** use
  `--agent <name>` against a definition whose `tools:` field is the actual narrow list. **Why people
  believe it:** both flags visibly change "what the model says about its own role" in the same way,
  and only one of them changes what the model is *allowed* to do — that difference is invisible from
  the command line alone.
- **Belief:** "`--system-prompt-file` is just a bigger `--append-system-prompt`." **Symptom:** the
  model loses track of its own working directory, whether it is inside a git repository, and where
  `CLAUDE.md` memory files were found, because the replacement prompt never re-stated any of it and
  the default framing that used to supply it is gone, not appended-to. **Fix:** treat a full replace
  as authorship from zero — re-state the environment framing the default prompt used to carry, or
  accept the model will not have it. **Why people believe it:** "append" and "replace" read as a
  difference of degree on the page, not a difference of kind.
- **Belief:** "`--append-subagent-system-prompt` only affects the one subagent I'm about to
  dispatch." **Symptom:** every subagent the run touches — including ones added to the pipeline
  later — carries the appended text, and an audit of one agent's odd persona detail has to check the
  top-level invocation rather than that agent's own file. **Fix:** treat the flag as a standing,
  per-dispatch policy decision set at the orchestrator's invocation, and price its token cost across
  every subagent the run will ever dispatch, not just the next one.

## Cheat sheet

| Flag | Default prompt | Model + tools travel with it | Scope |
|---|---|---|---|
| `--agent <name>` | Replaced (from the registered definition) | Yes | The one invoked session |
| `--append-system-prompt <text>` | Appended to | No | The one invoked session |
| `--system-prompt` / `--system-prompt-file` | Replaced (from your text) | No | The one invoked session |
| `--append-subagent-system-prompt <text>` | Appended to, per subagent | No | Every subagent dispatched that run, nested included, forks excluded — `-p` only, v2.1.205+ |
| `--exclude-dynamic-system-prompt-sections` | Per-machine parts relocated, not removed | N/A | Default prompt only — ignored once `--system-prompt`/`-file` is set |

## Self-test

1. What is the one structural thing `--agent <name>` carries that `--append-system-prompt` never
   does?
   <details><summary>Answer</summary>A model field and a tool allowlist. `--append-system-prompt`
   only edits the text the model is told; it cannot add or remove a callable tool or change the
   model.</details>
2. An engineer runs `--append-system-prompt "Never run destructive Bash commands"` and the model
   later runs one anyway. Was this a bug in the flag?
   <details><summary>Answer</summary>No — the flag never removed `Bash` from the session's tool
   set, so there was never a restriction to violate. The sentence was a request the model could
   ignore, not a ceiling.</details>
3. What does `--system-prompt` do to the default system prompt, and name two concrete things that
   are lost when it fires.
   <details><summary>Answer</summary>It replaces the default prompt entirely. Lost: the tool-use
   conventions (how/when to format a `tool_use` block) and the environment framing — working
   directory, whether the session is inside a git repository, where memory files were found — unless
   the replacement text re-states them.</details>
4. Which subagents does `--append-subagent-system-prompt` reach, and which does it not?
   <details><summary>Answer</summary>Every subagent dispatched during that run, nested subagents
   included. It does not reach a forked subagent, because a fork reuses the parent conversation's
   own system prompt rather than getting its own.</details>
5. Under what two conditions does `--append-subagent-system-prompt` have no effect at all?
   <details><summary>Answer</summary>In interactive mode (it only applies with `-p`), and on a
   Claude Code build older than v2.1.205.</details>
6. Why is `--append-subagent-system-prompt` described as an "org-shaped control" rather than a
   per-run convenience?
   <details><summary>Answer</summary>Because it is set once, at the top-level invocation, and from
   then on it silently reaches every subagent the pipeline ever dispatches — including ones added
   later — rather than being a one-time edit to a single agent's file.</details>
7. Does `--exclude-dynamic-system-prompt-sections` remove the working directory and git-repo
   information from what the model is told?
   <details><summary>Answer</summary>No — it relocates that information from the system prompt into
   the first user message. The model still receives it; only its position, and therefore its effect
   on prompt-cache reuse across machines, changes.</details>
8. Why does `--exclude-dynamic-system-prompt-sections` have no effect when combined with
   `--system-prompt-file`?
   <details><summary>Answer</summary>Per the documentation it is ignored once `--system-prompt` or
   `--system-prompt-file` has replaced the prompt — a full replacement was never carrying the
   default prompt's dynamic sections in the first place, so there is nothing for the exclusion flag
   to move.</details>

## Open questions

None.

---

**Leaves covered:** 2.2.1–2.2.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-48
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 354
