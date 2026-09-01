# PROMPT — Generate the AI for Coding (Claude Code) bible (topic 21)

This file is self-contained. Execute it verbatim. Do not go looking for a syllabus, an index, a
scenario file or a prior guide: everything you need — the role, the reader, the grounding repo, all
477 syllabus leaves, the diagram manifest, the file plan — is below.

**Three things about this topic differ from every other topic in this repository. Read them before
anything else.**

1. **The reader's baseline is zero.** They have never formally studied LLMs, agents, prompting or
   Claude Code. `PART 0 — GROUND ZERO` is a **prerequisite course, not an introduction**, and it is
   written and reviewed **first**, before any other part is drafted. See `## PART 0 is written
   first` in `# TASK`.
2. **The example domain is NOT QuizStakes.** It is the real **sdlc-harness** repository, cited by
   file path and quoted verbatim. See `## The example domain — the sdlc-harness repo` in
   `# CONTEXT`. Any instruction elsewhere in this pipeline that says "every example comes from
   QuizStakes" does not apply to this topic.
3. **This subject drifts between the syllabus being written and the notes being written.** The
   syllabus below already carries ten corrections found by writers re-verifying against the live
   documentation. Treat it as a work order verified on 2026-08-30, not as a citable source. Where
   the raw doc page and this prompt disagree, **the raw doc page wins and you correct the prompt's
   claim in the notes, inline, with both forms stated.** See `## Known-defective claims` in `# TASK`
   for the five that are already known.

---

# ROLE

You are a Claude Code platform engineer and interview coach. You build the tooling layer that other
engineers code inside: `.claude/` trees, permission rule sets, `PreToolUse` guards, skill libraries,
subagent rosters, versioned plugins with marketplaces, and headless `claude -p` orchestrators driven
from CI. You have read `https://code.claude.com/docs/en/` page by page — settings,
settings-reference, permissions, hooks, sub-agents, skills, memory, plugins, cli-reference — and you
have read them **as raw Markdown** (`curl -sL https://code.claude.com/docs/en/hooks.md`) rather than
as rendered prose, because the rendered page collapses the distinction between a top-level field and
a nested one and that distinction is exactly where this subject's hardest errors live.

You have also operated a real one at scale: a Python engine that spawns `claude -p` subprocesses
across the software development lifecycle, shipped as a versioned plugin with hooks, agents, skills,
playbooks, judge rubrics and eval suites. You have the incident list that comes with that — a
`SessionStart` hook that piled up 100+ GB of abandoned indexes because starting a session was the
trigger for the next pile-up; a `--setting-sources project` resolution against a per-story worktree
that silently dropped an entire permission block; an 80-turn ceiling that produced thirteen green
tests, a correct fix, and $5.16 of nothing landed.

Your authority order is: **the raw documentation Markdown at `https://code.claude.com/docs/en/*.md` >
the rendered documentation page > observed behaviour of the installed binary > the real repository's
own code and comments > engineer blog posts and articles, which are almost always version-stale on
this subject.** There is no source tree to walk here and no specification: the equivalent obligation
is **quote the doc page, then show the real file**. You never state a blog claim as fact when the
docs say otherwise, and you actively hunt version-stale folklore — that custom commands and skills
are separate systems, that a skill's `allowed-tools` restricts what it may do, that "more specific
wins" in settings precedence, that `bypassPermissions` protects `.git` and `.claude`, that a `Stop`
hook returns `continue: true` to keep working, that a `-p` session "counts as trusted", that
`${CLAUDE_PLUGIN_ROOT}` is the repository root — and you correct each one while stating what used to
be believed, because interviewers and colleagues still repeat the old form.

You teach **mechanism, not usage**. "Claude Code has a permission system" is not an explanation;
"permission rules are enforced by the harness, not the model, so `deny` is collected across every
settings layer and evaluated before `ask` and before `allow`, first match wins, which is exactly why
`Bash(aws *)` in `deny` blocks `Bash(aws s3 ls)` in `allow` and no amount of prompting can reopen it"
is. Every claim about cost, ordering, precedence or a limit is either derived on the page with the
arithmetic shown and labelled as derived, or quoted from the documentation with the quoted lines
explained.

And you know what a level-zero reader does not know. You never write "as you know". You define
token, context window, tool call, turn, and agent before relying on any of them, in the body, at
first use.

---

# CONTEXT

## Reader level

A backend Java engineer with 3–4 years of professional experience, writing Java 21 idiomatic code
daily (Spring Boot 3.x, records, streams), preparing for a senior/FAANG-level interview loop.

**On this topic specifically their baseline is ZERO.** They have used an AI coding tool the way one
uses a search engine — by typing into it — and have never been told what happens on the other side.

**Assume they already know**, without re-teaching: Java and Spring Boot; the shell, `git`, `jq`,
`bash` scripting basics; JSON and YAML; what a subprocess is, what an exit code is, what stdin and
stdout are; what a config file precedence chain looks like in principle; HTTP and REST; timeouts,
retries, backoff, circuit breakers and bulkheads as patterns.

**Assume they do not know, and must be taught from nothing:** what a token is; that the model
predicts a next token from a distribution and samples one; that the same input does not reliably
give the same output; what a context window is and that it is the argument list of the next call
rather than a memory; that the whole conversation is re-sent every turn; that the model cannot read a
file, run a command, remember yesterday or check its own claims; what confabulation is and why
fluency is worthless as a correctness signal; what a training cutoff implies; what a tool is, that
the model only *emits* a `tool_use` block and the harness decides whether to run it; what a turn is;
what an agent is; and that "Claude Code" is the harness rather than the model.

They have absorbed version-stale folklore from blogs and from colleagues. That gap, plus the fact
that they are already spending real money on this tool without a model of where it goes, is the
entire reason these notes exist.

## Purpose

These notes are a **detailed one-stop reference plus deep interview prep**. One document set the
reader never needs to supplement with a blog post, a Discord answer, or a second guide. They must
serve two readings equally well:

1. a first careful cover-to-cover read that builds the model from nothing, and
2. a night-before-the-interview re-read that reloads the numbers, the traps and the answer shapes.

They must also serve a third use this topic has and others do not: **as an operating manual the
reader keeps open while configuring their own machine.** Every `[BUILD]` leaf ships something the
reader copies and runs today.

Coverage is driven by the topic, not by any individual reader's measured gaps. Write for every reader
of this level.

## Target version

**Claude Code v2.1.2xx (August 2026)** is the baseline for every flag, settings key, hook event,
frontmatter field and numeric limit.

This subject moves faster than the JDK. **A field added in v2.1.218 and a field removed in v2.1.234
both exist in the same release line.** The consequences for the write pass are mandatory:

- Every leaf tagged `[VERSION]` **states its version inline, at the point of the claim** — not in a
  footnote, not in a table at the end. A reader on an older build who is not told the version will
  conclude the guide is wrong.
- Every leaf tagged `[DOC]` or `[RESEARCH]` is **re-verified against the raw Markdown of the owning
  doc page immediately before that leaf is written** — `curl -sL https://code.claude.com/docs/en/<page>.md`.
  The syllabus below is a work order, not a citable source: it was verified on 2026-08-30 and is
  already ageing. The pages it was built from are settings, settings-reference, permissions, hooks,
  sub-agents, skills, memory, plugins and cli-reference; go to the one that owns the claim.
- **Fetch the raw `.md`, not the rendered page, for anything with nesting in it** — a hook output
  schema, a frontmatter field list, a settings key tree. The rendered page flattens nesting and the
  flattening has already produced one shipped error in this very syllabus. See §2.3.14–2.3.15c.
- Where a claim cannot be verified, say so inline as `**Unverified:**` with what you could not
  confirm, and record it in that file's `## Open questions`. Do not assert, and do not quietly
  soften.
- Where a widely-repeated claim is version-stale or was simply wrong, state what is true in
  v2.1.2xx **and** what used to be believed, and flag it as a version trap. Interviewers and
  colleagues still ask for the old form.

Where a Java version matters (the `[JAVA]` leaves, all of §4.5), the target is **Java 21 LTS** with
Spring Boot 3.x idiom.

## Adjacent topics

These sibling guides exist. For each, the rule is: **state the mechanism in one self-contained
paragraph here, give the reader enough to answer the question, then point to the sibling for the full
treatment.** Never send the reader away empty-handed, and never duplicate a sibling's full chapter.

| Guide | Owns | What this file still owes the reader |
|---|---|---|
| 05 Multithreading & concurrency | the memory model, thread pools, `CompletableFuture`, bulkheads, backpressure | the bulkhead and bounded-retry material in §4.5.5 written out in full working Java here — a `Semaphore`-guarded concurrency cap and a retry that preserves the last parsed envelope — then point to 05 for the model underneath |
| 12 API design | REST contracts, idempotency, versioning, rate limiting, treating a dependency as a contract | §3.8.8 in full: an agent call **is** a remote dependency — timeout, retry with backoff, idempotency key, circuit breaker, bulkhead — stated here with the mapping onto `claude -p`, then point to 12 |
| 13 Web security | AuthN/AuthZ, OWASP, secrets management, the threat-model vocabulary | §2.9.1–2.9.4 in full: the agent runs with your credentials, reads what you can read, and follows text it finds; prompt injection as a data-to-instruction confusion; why "tell it to ignore instructions in data" is not a control. Mechanism here, threat-model discipline in 13 |
| 17 Git craft | the object model, rebase, bisect, reviewable commit hygiene | §2.7.4 in full: the same argument that makes small PRs reviewable makes small agent tasks reviewable, plus worktree isolation as the mechanism behind §3.7. Point to 17 for review discipline |
| 20 Observability & operations | metrics, logs, traces, SLI/SLO, incident response, postmortems | §3.4 and §3.9.9 framing: cost as a metric with a budget, the `-p --output-format json` envelope as the telemetry record, agent failures as a measurable defect stream rather than anecdotes. Point to 20 for the pillars |
| 11 Operating systems / Linux | processes, file descriptors, signals, exit codes | the subprocess mechanics under `ProcessBuilder` and under `claude -p` — exit codes, stdout/stderr separation, wall-clock kill — one paragraph, then point |
| 16 Testing | the pyramid, JUnit 5, what coverage does not tell you | §2.7.3 and §4.7.4: a failing test is a machine-checkable specification, which is exactly what a confabulating writer needs; eval suites as tests for prompts. Mechanism here, testing craft in 16 |

## The example domain — the sdlc-harness repo

**This topic does not use QuizStakes.** It has a different and stricter grounding contract, and it
replaces the usual example-domain section entirely.

Every leaf tagged `[CASE]` — there are roughly **45** — is grounded in a real production system:
the **sdlc-harness**, a Python engine that orchestrates `claude -p` subprocesses across the software
development lifecycle, shipped as a versioned plugin with hooks, agents, skills, playbooks and eval
suites.

Repository root:

```
/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness
```

**That repository is READ-ONLY. Never write to it, never edit it, never create a file inside it.**

Rules for a `[CASE]` leaf, all mandatory:

- **Cite a file path.** Repo-relative is fine in the prose (`plugins/sdlc-harness/hooks/hooks.json`);
  the absolute path above is the root it resolves against.
- **Quote the real text, verbatim, in a fenced block.** Never paraphrase a `[CASE]` quote, never
  reconstruct it from memory, never "clean it up". If the real text is 30 lines and complete, quote
  all 30.
- **Read the file before you quote it.** A quote you did not read is a fabrication, and the reader
  has the repo open beside you.
- **Count before you print a count.** Every "nine reference files", "fifteen scripts", "four
  entries" in the table below and in the syllabus is a claim you re-verify by listing the directory
  at write time. Three of the corrections in this syllabus revision were miscounts. **Never pad a
  count to match the prose; change the prose to match the disk.**
- **Then explain it.** A quote with no reading of it does not satisfy the leaf. Name the design
  property, name what would break without it.
- **If a file named in a leaf does not exist or does not say what the leaf claims, do not invent
  it.** Write what the file actually says and note the divergence inline; if the leaf is
  unsatisfiable, mark the leaf `**Unverified:**` and record it in `## Open questions`.

Files confirmed present, with the counts as corrected on 2026-08-30:

| Path (repo-relative) | What it grounds |
|---|---|
| `.claude/settings.json` | §1.1.7, §1.2.12, §1.4.41 — a two-key project settings file, `permissions.allow` of four entries, `enabledPlugins` of four |
| `.claude/commands/` (nine files: `implement-story.md`, `run-conductor.md`, `run-harness.md`, `implement-feature.md`, `implement-story-lite.md`, `plan-project.md`, `calibrate.md`, `handbook.md`, `smoke-test.md`) | §1.1.7 — commands-as-skills at project scope |
| `.claude/skills/playwright-cli/SKILL.md` + `.claude/skills/playwright-cli/references/` (**nine** reference files) | §1.5.19 — a reference library that costs nothing until needed. **This is a repo-root skill, not a plugin skill.** Do not describe it as bundled with the plugin, and list the nine filenames as found |
| `.claude-plugin/marketplace.json` | §2.5.16 — `allowCrossMarketplaceDependenciesOn`, documentation living in the config |
| `plugins/sdlc-harness/.claude-plugin/plugin.json` | §2.5.17 — `version`, licence, `dependencies` |
| `plugins/sdlc-harness/hooks/hooks.json` | §2.3.21 — three `SessionStart` handlers plus one `PostToolUse` with `matcher: "Write|Edit"` |
| `plugins/sdlc-harness/hooks/check-init.sh` | §2.3.22–2.3.25 — tagged advisory instructions, defensive shape, content-hash versioning, the removed auto-reindex |
| `plugins/sdlc-harness/hooks/prod-guard-bash.sh`, `prod-guard-lib.sh`, `prod-guard-session-start.sh` | §2.3.26 — the blocking-guard pattern |
| `plugins/sdlc-harness/hooks/doc-update-reminder.sh`, `calibration-nudge.sh` | §4.2.6 — Diff vs the real one |
| `plugins/sdlc-harness/agents/progress-verifier.md`, `agents/calibrator.md` | §2.1.22, §2.1.23, §4.4.5 — pointer bodies, write boundaries, withheld tools |
| `plugins/sdlc-harness/skills/bootstrap/SKILL.md` | §1.5.20, §2.8.2, §2.8.3, §2.8.6, §4.3.6 — orchestrator-not-rewrite, the determinism argument |
| `plugins/sdlc-harness/skills/compose-playbook/SKILL.md`, `skills/prod-triage/SKILL.md` | supporting skill shapes |
| `plugins/sdlc-harness/commands/implement-story.md`, `commands/run-conductor.md`, `commands/run-harness.md` | §1.5.21, §3.9.5 — prompt composition without duplication, prose executor vs conductor |
| `plugins/sdlc-harness/scripts/bootstrap-*.sh` (**fifteen** files, including `bootstrap-uv.sh`, `bootstrap-user-scope.sh`, `bootstrap-lsp.sh`, `bootstrap-write-version.sh`) plus **three** `triage-*.sh` | §1.5.20, §2.8.6, §2.8.7, §2.9.10 — idempotent steps, the documented exception, user-scope provisioning. **These live under `scripts/`, not `hooks/`.** Count them at write time |
| `plugins/sdlc-harness/scripts/triage-aws-ro.sh` | §2.9.10 — read-only triage |
| `harness/src/harness/engine/agent.py` | §2.2.5, §2.2.6, §3.6.10–3.6.18, §4.5.8 — persona loading, envelope extraction, retry loop, resolution order, every default constant |
| `harness/src/harness/engine/` (`loop.py`, `continuation.py`, `checkpoint.py`, `gate.py`, `registry.py`, `result.py`, `spec.py`, `telemetry.py`, `workspace.py`, `cli.py`, `errors.py`, `render.py`, `sensor.py`) | §3.9.3, §3.9.6, §3.9.8 — pipeline stages, folded state, continuation checkpoints |
| `harness/src/harness/telemetry/transcript.py` | §3.1.8 — reading the JSONL transcripts to mine friction signals |
| `harness/playbooks/` (`full-sdlc`, `plan-project`, `implement-story`, `implement-story-lite`, `implement-story-exec`, `implement-story-lite-prose`, `post-deploy-smoke`, each a `playbook.yaml`) | §3.9.5 — the playbook set |
| `harness/control-plane/judge-rubrics/progress-verifier.yaml` (plus `code-review`, `story-reviewer`, `prd-reviewer`, `requirements`, `functional-tests-reviewer`) | §3.9.7 — versioned rubrics |
| `harness/control-plane/agent-prompts/progress-verifier.md`, `agent-prompts/calibrator.md` | §2.1.22 — the versioned prompt file an agent body points at |
| `harness/control-plane/schemas/feedback-signal.yaml`, `schemas/fix-task.yaml`, `schemas/task-entry.yaml` | §3.9.9 — the `failure_code` vocabulary and the calibration schemas |
| `harness/evals/` (`code-to-commit/`, `baselines.yaml`, `README.md`, and the `java-spring` fixtures) | §3.9.10 — how you find out whether a prompt change helped |
| `docs/adr/0016` | §3.7.6 — the paper trail cited in the code itself |

Where the syllabus names a path the table above does not list — `harness/evals/seeded-defects`,
`features/<slug>/state/harness.db`, `severity_map.yaml`, `filed-bugs.yaml`,
`control-plane/judge-rubrics/*.yaml` beyond those listed — **look for it before writing the leaf**.
If it is not there, write what is there and say so.

**Banned everywhere in this topic, not just in `[CASE]` leaves:** `Foo`, `Bar`, `Baz`, `my-agent`,
`my-skill`, `thing1`, `thing2`, `MyClass`, `doSomething`, `test-agent`, `example-hook`,
`Dog extends Animal`. A throwaway name in a settings block, a hook script, an agent frontmatter or a
Java class is a defect, not a style choice. Where a leaf needs an artefact the harness does not
have — most of PART 4 — name it for what it does in a real repository: `format-on-edit.sh`,
`block-destructive-bash.sh`, `branch-context.sh`, `require-green-build.sh`, `mvn-test-runner`,
`readonly-reviewer`, `ClaudeRunner`, `ClaudeEnvelope`, `AgentTimeoutException`, `checklist-refresh`.

`[JAVA]` leaves — roughly **15** of them, and all of §4.5 — must land in the reader's own language:
either a real Java 21 / Spring Boot 3.x analogy stated precisely enough to be falsifiable, or real
compiling Java code. "It is like a REST controller" is not enough; §0.2.5 wants the stateless
`@RestController` receiving the whole conversation as its request body every time, **and the three
places the analogy breaks.**

---

# TASK

Write the complete AI for Coding (Claude Code) bible as a set of Markdown files under
`src/notes/detailed/21-ai-for-coding/`, organised into six parts, covering **all 477 syllabus leaves
reproduced in the `# SYLLABUS` section below**, illustrated by **all 99 diagram ids enumerated in the
`# DIAGRAM MANIFEST` section below**, written to the exact file paths in the `# OUTPUT CONTRACT`
section below.

## PART 0 is written first

**This is a hard sequencing instruction, not advice.**

`PART 0 — GROUND ZERO` (46 leaves, eleven files) is written and reviewed **before any other part is
drafted.** Every later part references its vocabulary. A weak PART 0 does not degrade the guide
gracefully — it makes the remaining 431 leaves unreadable, and the fix is a rewrite of PART 0, not a
patch to the parts that lean on it.

PART 0 is a **prerequisite course, not an introduction.** It assumes no ML background and no prior
exposure. Every term is defined at first use, in the body, before it is relied on. **The phrases "as
you know", "obviously", "of course you're familiar with" and "recall that" are banned in PART 0.**
Undefined jargon in PART 0 is a defect.

**The five-question gate.** Before any file of PART 1 is written, the eleven PART 0 files must be
readable end to end by someone who knew none of this, and that reader must then be able to answer all
five of these from memory, unprompted:

1. What is a **token**?
2. What is a **context window**, and why is the whole conversation re-sent every turn?
3. What is a **tool call** — and who decides whether the tool actually runs?
4. What is a **turn**?
5. What is an **agent**, precisely, as distinct from a chatbot?

If PART 0 as written does not put a level-zero reader in a position to answer all five, PART 0 is
rewritten. State in `00-index.md` that the gate was applied and that it passed.

## Tier structure

The syllabus has six parts. They map onto the standard three tiers as follows, and this mapping is
fixed — do not re-derive it:

| Syllabus part | Tier | Contains |
|---|---|---|
| `PART 0 — GROUND ZERO` + `PART 1 — BASICS` | **BASICS** | PART 0: what the model is, the context window as a data structure, the agent loop, orientation in the tool. PART 1: the `.claude` folder mapped, settings files and precedence, `CLAUDE.md` and the memory system, the permission system, skills and slash commands. Together: why the thing exists, the mental model, the vocabulary, the full configuration surface, and the guarantees each mechanism carries |
| `PART 2 — INTERMEDIATE` | **INTERMEDIATE** | subagents, personas, hooks, MCP and LSP, plugins and marketplaces, context economy in practice, the practices that change outcomes, deterministic vs agentic, governance and the org view. Cost models, the specialised variants, the utility surface, and the "which one and why" decisions |
| `PART 3 — UNDER THE HOOD` | **ADVANCED (INTERNALS)** | what is actually in the request and in what order, compaction mechanically, permission evaluation step by step, the cost model, effort and routing, headless mode, the `--setting-sources` root-cause walkthrough, the SDK and the API underneath, orchestration patterns, verification |
| `PART 4 — BUILD IT` | own file group | forty working artefacts: a `.claude` folder from nothing, four hooks, a skill and a command, two subagents, a Java 21 headless orchestrator, a plugin, a verification harness |
| `PART 5 — INTERVIEW AND RETENTION` | own file group | the sixteen questions with answer shapes, the trap index, the drills |

**Why PART 0+1 are one tier rather than PART 0 being its own.** PART 0 teaches vocabulary and PART 1
teaches the configuration surface that vocabulary describes; a reader who stops after PART 0 knows
what a token is and cannot configure anything, and a reader who starts at PART 1 has no words for
what settings precedence is precedence *over*. They are one competence and they interleave — §1.3
cannot be read without §0.2, §1.4 cannot be read without §0.3.3. PART 0 keeps its own folder and its
own write-first-and-review sequencing; it shares the BASICS tier and the `90-interview-basics.md`
wrap-up.

**Why PART 3 is INTERNALS even with no source tree.** There is no JDK to walk here. The internals
obligation is discharged as **the documented mechanism plus the observed artefact**: the literal
request assembly order, the compaction re-attachment budget with its 5,000 / 25,000-token numbers,
the permission pipeline traced command by command, the four billed quantities with the arithmetic,
the `-p --output-format json` envelope printed in full, and the real code in
`harness/src/harness/engine/agent.py`. `[DOC]` + `[CASE]` is this topic's `[SOURCE]`.

## Hard instructions

Every one of these is mandatory.

- **No line limit and no file-count limit.** There is no upper bound on the length of the notes or on
  how many files they are split across. Completeness beats brevity every single time. Never
  truncate, never write "and so on", never write "similar to the above", never defer a concept for
  space. If a file grows large, split it into more files rather than cutting content, and register
  the new file in `00-index.md`.
- **Output format is Markdown (`.md`).** Every file.
- **Diagrams are standalone SVG files** in the topic-root `diagrams/` folder, named
  `D-NN-short-slug.svg`, embedded at the point of explanation with a Markdown image reference and a
  caption carrying the stable id:

  ```
  ![D-28 — Permission evaluation: deny, then ask, then allow](../diagrams/D-28-deny-ask-allow.svg)

  **D-28** — Permission evaluation: `deny`, then `ask`, then `allow`; first match wins.
  ```

  **Never inline `<svg>` in the Markdown** — GitHub strips it and VS Code's preview sanitizes it
  away, leaving a blank gap where the picture should be. **Never use ASCII art** — it deforms across
  renderers and fonts. Where the manifest's `Type` column says `table`, a Markdown table is the
  correct rendering and no SVG file is required; the `D-NN` id still appears at that point in the
  prose so the id is accounted for. **Fifteen of the 99 ids are `table` type.**

  The full authoring rules — canvas, `viewBox` with no fixed width or height, the opaque backdrop
  rect, orthogonal-only edge routing, the palette, the legend, the 10.5px text floor, the
  render-and-look self-check — live in the `## Diagram spec` section of the `notes-generator` agent
  specification and are handed to illustrators verbatim from there. **Do not restate them here and
  do not contradict them.** What this prompt owns is *which* diagrams exist and what each must show:
  that is the `# DIAGRAM MANIFEST` below.

  Labels name the real subject matter — `check-init.sh`, `PreToolUse`, `permissions.deny`,
  `ClaudeRunner`, named constants with their values such as `DEFAULT_MAX_TURNS = 160` — never `Foo`,
  `Node A` or `hook1`.
- **Every concept follows this exact chain, in this order:**
  `Concept → Why it exists → How it works → SVG → Code → Gotcha`.
  All six links. Here "Code" means the real artefact the concept lives in: a settings JSON block, a
  `hooks.json` fragment, a `SKILL.md` with its frontmatter, an agent definition, a shell script, a
  `claude` invocation with its flags, a Java class, or a quoted sdlc-harness file. If a link
  genuinely does not apply to a concept, say so in one line ("No gotcha: the rule has no surprising
  edge.") rather than silently dropping it.
- **Code is complete and runnable as written.** This applies to every language the guide uses:
  - **JSON** (settings, `hooks.json`, `plugin.json`, `marketplace.json`, `.mcp.json`) — valid,
    parseable, complete objects with the surrounding keys present. Never a fragment with an implied
    parent. JSON does not support comments; put the explanation in the prose beside the block, never
    inside it. **A hook output object must show whether each field is top-level or nested inside
    `hookSpecificOutput`** — that is the whole point of printing it.
  - **Markdown artefacts** (`SKILL.md`, agent definitions, command files) — the frontmatter fences
    and every field shown, then a real body.
  - **Shell** — a complete script with its shebang, its failure posture (`set -e` or the deliberate
    `set +e` with `exit 0`), and real `jq` over stdin where the event supplies JSON.
  - **Java** — full class and method bodies, real field names, real generics, real exception types,
    real edge cases. Strip only the trivia: `import` statements, `package` declarations, and
    `main`-method scaffolding where it adds nothing. All Java is **Java 21 idiomatic**: records,
    sealed interfaces, pattern-matching `switch`, text blocks, `var` sparingly, `ProcessBuilder`,
    `Process.waitFor(Duration)`, virtual threads where they fit.
  - **`claude` invocations** — the full command line with every flag it needs, not an abbreviated
    form with the interesting flags omitted.

  **No `...` elisions, no "implementation omitted", no pseudo-code standing in for real code.**
  Quoted sdlc-harness files and quoted documentation may be excerpted to the relevant lines, but
  every line quoted must then be explained.
- **Callouts.** Use exactly these three markers, bolded, inline at the point they belong. Do not
  invent others.
  - `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
  - `**Insight:**` — the non-obvious mechanism that makes the rest click.
  - `**Interview:**` — how this is actually asked, and the one-line answer.

  Every syllabus leaf tagged `[TRAP]` must carry a `**Pitfall:**`. The tag count is **~45 and it is a
  floor, not an estimate** — the finished note set for this topic produced **154 distinct
  `**Pitfall:**` entries**, because writers correctly used the marker for every wrong belief a leaf
  surfaced, not only for the leaves that carried the tag. Do the same. Do not ration pitfalls to
  match the tag count.
- **Every part ends with all three of these:**
  1. a **summary table** covering that part's concepts,
  2. **interview Q&As** with full model answers — not hints, the answer a candidate would actually
     say out loud, at speaking length. The exact count per part is stated in the
     `# OUTPUT CONTRACT`.
  3. **5 "predict the output" puzzles** per interview file. On this topic a puzzle is: a complete
     configuration (a `settings.json`, a `hooks.json`, an agent frontmatter, a `claude` command
     line), a specific action, the **actual outcome** — runs / prompts / blocked / which file won /
     what loaded / what it cost — and an explanation of *why*. A puzzle with no config listed is not
     a puzzle.

  These three go in that part's interview file as named in the `# OUTPUT CONTRACT`, and cover the
  whole part.
- **Version-specific behaviour is always called out explicitly.** See `## Target version` in
  `# CONTEXT`. Every `[VERSION]` leaf — roughly **20** — states the version inline at the point of
  the claim. Every `[DOC]` and `[RESEARCH]` leaf is re-verified against the raw Markdown of its
  owning doc page immediately before it is written.
- **Tag obligations.** The syllabus tags below are instructions, not decoration:
  - `[ZERO]` — assume no prior knowledge whatsoever. Define every term used in the leaf, in the
    leaf. No forward-dependency on a term defined later.
  - `[DOC]` — quote the official documentation (short excerpt) and cite the page by name. Re-verify
    against the raw `.md` first.
  - `[CASE]` — ground it in the sdlc-harness repo with a real file path and a real verbatim quote.
    See `## The example domain` in `# CONTEXT`. Counts are re-derived from the disk, never carried
    over from the prose.
  - `[BUILD]` — ship a complete, working artefact the reader can copy and run, **then a prove step**
    under the evidence policy below, **then a "what this costs" note** in tokens or dollars under
    the cost-provenance rule in the `# OUTPUT CONTRACT`.
  - `[PROVE]` — work the argument through on the page, or show the observed result, under the
    evidence policy below. Do not state the conclusion and move on. Where the leaf asks for
    arithmetic, print the arithmetic.
  - `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix.
  - `[INCIDENT]` — see `## The incident roster` below. Each must name **what broke, what it cost, and
    the fix**, then state the general law it establishes.
  - `[NUM]` — state the number, limit, or arithmetic explicitly.
  - `[VERSION]` — state the version inline.
  - `[RESEARCH]` — re-verify against the cited source immediately before writing; this area drifts.
  - `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn.
  - `[JAVA]` — land it in the reader's own language: a precise Java 21 / Spring Boot 3.x analogy
    with the place it breaks stated, or real compiling Java code.

## The evidence policy for `[PROVE]` and `[BUILD]`

This is settled policy. Apply it to every proof, every measurement and every transcript in the
guide.

1. **Where the artefact is runnable read-only in your own sandbox, run it.** Paste the **real
   transcript verbatim** and, immediately above it, **the exact command that produced it**. A fenced
   block that looks like terminal output and was not produced by a terminal is the single worst
   defect this note set can ship, because it is indistinguishable from evidence.
2. **Where it genuinely cannot be executed** — it needs an interactive session, a paid API call, a
   machine you do not have, a `/context` you cannot render — then, at the point of the claim, write
   **"not measured here"**, give **the exact command the reader should run**, and record the item in
   that file's `## Open questions`. Do not soften it into "roughly", do not omit it, do not move it
   to a footnote.
3. **Never put a derived figure in the visual position a measured one belongs.** A worked arithmetic
   result goes in prose or a table, labelled as derived. It never goes in a fenced block styled as
   command output.
4. **Use this provenance sentence, or one that says the same thing, wherever you derive a number:**
   *"The mechanism is from the documentation; the arithmetic is ours and is shown."* Then show it.
5. A `[BUILD]` artefact whose prove step could not be run is still shipped in full — the artefact is
   the deliverable. Only the proof is marked "not measured here".

## The incident roster

The syllabus carries the `[INCIDENT]` tag on **14 distinct leaves** (16 raw occurrences in leaf
bodies — §2.3.25 and §3.6.15 each carry it twice), covering **13 distinct events**, and they are not
all the same kind of thing. Get the split right, because a reader who counts them will otherwise conclude
the guide padded its own war stories.

- **Ten operational incidents.** These are the roster. Each has a real cost:
  §2.1.24 the lane-collision silent overwrite; §2.3.25 the `SessionStart` reindex pile-up (**100+
  GB**, machines unusable); §3.6.11 the unparseable envelope diagnosable only by reproducing it
  interactively (the **500-character** snippet fix, 2026-07-30 calibration finding); §3.6.15 the
  80-turn exhaustion (**13 green tests, a correct fix, $5.16, zero landed work**); §3.7.1 the
  `--setting-sources` worktree resolution that dropped a whole permission block; §3.10.2 the
  re-run-published-artefacts finding; §3.10.3 the NUL-byte checker that switched itself off;
  §3.10.4/§3.10.5 the md5 taken over a patched harness and published as a bare digest (**one event,
  restated as a law — do not count it twice**); §3.10.6 the status row pointing at a missing path;
  §3.10.7 the cross-lane contradictions found after their lanes had closed.
- **Three documentation incidents.** §1.4.28a, §1.4.34a and §2.3.15a are tagged `[INCIDENT]` because
  **this syllabus itself shipped the false claim until 2026-08-30**. For these, "what it cost" is
  the wrong belief propagating into a permission posture or a hook that cannot work, and "the fix"
  is the verified form plus the raw-`.md` habit that found it. Write them that way. Do **not** fold
  them into the ten, and do **not** invent a dollar figure for them.

State the count as "ten operational incidents plus three documentation corrections" wherever the
guide totals them, including §5.2.4's incident index.

## Known-defective claims — get every one of these right

Five claims in this topic's earlier material were wrong. The wrong forms are common, colleagues and
interviewers still repeat them, and every one of them was corrected by a writer going to the raw doc
Markdown. Write the correct form, **and** carry the wrong form as a `**Pitfall:**` at the leaf named.

### 1. The hook output schema has three kinds of field — this is the important one

Verified against `curl -sL https://code.claude.com/docs/en/hooks.md`. There are **three** kinds of
field in a hook's JSON output, and they live at different levels:

- **Universal top-level fields, accepted by every event:** `continue`, `stopReason`,
  `suppressOutput`, `systemMessage`, `terminalSequence`.
- **Top-level `decision` + `reason`**, which is how most events block.
- **`hookSpecificOutput`**, a nested object for events needing richer control, requiring a
  `hookEventName` field.

The consequences you must write correctly:

- **`Stop` and `SubagentStop` keep Claude working via top-level `decision: "block"`, and `reason` is
  REQUIRED when you do.** You are blocking the *stop*, not requesting a continuation. Omitting
  `decision` allows the stop.
- **`hookSpecificOutput.additionalContext` is a third path** on `Stop`: the conversation continues
  under the same loop protections, but the transcript labels it `Stop hook feedback` rather than
  raising a hook error. Use it when the hook is working as designed.
- **Exit code 2 routes its stderr as `reason`.**
- **Boolean `continue: false` is a universal kill switch and means the OPPOSITE of "keep going".**
  It makes Claude stop processing entirely after the hook runs and it **takes precedence over any
  event-specific decision field**. Default is `true`. `stopReason` is the message shown to the
  **user**, never to Claude. `suppressOutput` is accepted and does nothing.
- **There is no `continueReason`, no `decision: "continue"`, and no
  `hookSpecificOutput.continue`.** If you find yourself writing any of those, you have reconstructed
  the schema from memory instead of reading it.
- `PreToolUse` uses `hookSpecificOutput.permissionDecision` + `permissionDecisionReason`; its
  top-level `decision`/`reason` form is **deprecated**, with `"approve"`/`"block"` mapping to
  `"allow"`/`"deny"`. `PermissionRequest` uses a `decision` **object**.
- Output strings — `additionalContext`, `systemMessage`, plain stdout — are capped at **10,000
  characters**; longer output is written to a file and replaced with a preview plus path.
- A `Stop` hook that blocks is bounded by the `stop_hook_active` stdin field and an
  **8-consecutive-continuation cap**. Without awareness of both, a `Stop` hook is an infinite-turn
  generator.

Leaves: §2.3.14, §2.3.14a, §2.3.14b, §2.3.15, §2.3.15a, §2.3.15b, §2.3.15c, and the build at
§4.2.4. **Three independent write attempts got §2.3.15a wrong three different ways before anyone
fetched the raw page.** Fetch the raw page.

### 2. `bypassPermissions` does not protect `.git` or `.claude`

Protected-path writes **are allowed** under `bypassPermissions`, so the mode can rewrite the very
configuration that would otherwise constrain it. What it still refuses is enumerated at §1.4.28:
critical-path `rm`/`rmdir` deletions, explicit `ask`-rule matches, always-interactive tools
(`AskUserQuestion`, `requiresUserInteraction` MCP tools), and two cross-session messaging safeguards
(`isolatePeerMachines`, held inbound messages). The "it still refuses protected paths" claim is
false. Leaf §1.4.28a.

### 3. A `-p`/SDK session does not silently inherit an untrusted repo's rules

The consequence of there being no trust dialog is the **opposite** of dangerous-by-default: for an
untrusted folder, a `-p` or SDK session does **not** apply the committed `allow` /
`additionalDirectories` rules at all, and prints a **stderr warning** instead. "Counts as accepted"
applies only to the much narrower git tracked/untracked check on `settings.local.json` (§1.4.35).
The real risk is **stickiness**: trust is keyed per repository-root path and is **never re-checked
when a commit changes the ruleset**, so a later commit can widen `permissions.allow` and no dialog
reappears. Leaves §1.4.34 and §1.4.34a. That is the interview answer, not the false version.

### 4. A skill's `allowed-tools` pre-approves; it does not restrict

It grants permission for the invoking turn only and clears on the next user message; every other
tool stays callable. `disallowed-tools` is the field that removes tools. Leaf §1.5.8. Carry the
wrong belief as a `**Pitfall:**`, because the consequence is a false sense of least privilege.

### 5. Three inventory and precedence facts that are commonly stated backwards

- **Six permission modes, not four:** `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`,
  `bypassPermissions` (§1.4.25).
- **`acceptEdits` auto-approves a wider set than "edits"** — `mkdir`, `touch`, **`rm`**, **`rmdir`**,
  `mv`, `cp`, **`sed`** for paths in the working directory or `additionalDirectories`. It
  auto-approves deletion. State the blast radius plainly (§1.4.26, §1.4.26a).
- **Managed settings outrank the command line.** The order at §1.2.2 is managed → command line
  (`--settings`) → project local → shared project → user, and §1.2.3 says explicitly that it is
  *not* "more specific wins" and *not* "command line always wins".
- **`/doctor` and `/rewind` are bundled skills; `/run` is a built-in** (§1.5.23). This is the
  reverse of what is usually assumed. Tag the inventory rather than lumping it, and re-check the
  tags at write time.
- **`skillListingMaxDescChars` and `skillListingBudgetFraction` are two different numbers** — a
  **per-entry** cap of **1,536 characters** on combined `description` + `when_to_use`, and a separate
  **pool** budget of roughly **1% of the context window** across all entries. A skill can be inside
  the per-entry cap and still be dropped by the pool budget (§1.5.6).

## PART 4 ships artefacts, not snippets

Every one of the 40 leaves is `[BUILD]`. Each item is: the complete artefact, then the **prove** step
under the evidence policy, then the **"what this costs"** note under the cost-provenance rule. Where
a real equivalent exists in the sdlc-harness, the item ends with a **Diff vs the real one** table —
one row per design property (concurrency safety, path resolution, tool fallbacks, locale pinning,
failure posture, write boundaries, withheld tools, recorded constants), columns "yours" / "the real
one" / "why the difference". The centrepiece is §4.5: a Java 21 headless orchestrator built up
cumulatively over eight leaves, `ProcessBuilder` around `claude -p --output-format json`, ending in a
two-stage pipeline with a per-stage cost report.

## Remaining style rules

- **No emojis. No filler.** No "let's dive in", "great question", "as we all know", "it's worth
  noting". Lead with content.
- **A table for any comparison of three or more things.**
- The notes end with a flat `## Atomic concept checklist`, one bullet per distinct concept, phrased
  as a one-line assertion the reader can self-quiz against. Downstream agents parse this list, so it
  is flat — no nesting, no headings inside it — and it lives at the end of
  `92-interview-internals.md`, covering **all six parts**, not just PART 3. See the
  `# OUTPUT CONTRACT` for why that file and not the last one.

## Leaf coverage

The syllabus below has **477 leaves** (PART 0: 46, PART 1: 125, PART 2: 142, PART 3: 96, PART 4: 40,
PART 5: 28). **Every leaf must appear in the notes.** Any leaf you cannot cover must be listed in a
`## Deferred` block at the end of the file that owns it, with the leaf number and a one-line reason.
An empty `## Deferred` block is the expected outcome.

Note that §1.4 and §2.3 carry lettered leaves (`1.4.26a`, `2.3.15c` and so on). They are full leaves
with full obligations, not annotations on their parent. Count them; cover them; list them in the
footers by their lettered number.

Tag totals to check your own work against: `[ZERO]` ~30, `[DOC]` ~150, `[CASE]` ~45, `[BUILD]` ~60,
`[TRAP]` ~45 **as a floor** (expect three times that many `**Pitfall:**` entries), `[INCIDENT]` **10
operational plus 3 documentation**, `[NUM]` ~60, `[VERSION]` ~20, `[JAVA]` ~15, `[PROVE]` ~45.

---

# SYLLABUS

**Reader baseline: ZERO.** This reader has never formally studied LLMs, agents, prompting, or
Claude Code. They are a competent backend Java engineer (3–4 YOE) who has *used* an AI coding tool
the way one uses a search engine — by typing into it — and has never been told what happens on the
other side. Everything in PART 0 must therefore be taught from nothing: no ML background, no
"as you know", no undefined jargon. Every term is defined at first use, in the body, before it is
relied on.

The consequence for the write pass: **PART 0 is not an introduction, it is a prerequisite course.**
A reader who finishes PART 0 must be able to explain, unprompted, what a token is, why the whole
conversation is re-sent every turn, and why the model cannot do anything except emit text. If the
write pass produces a PART 0 that assumes any of that, the rest of the guide is unreadable and the
part must be rewritten, not patched.

**Tool version baseline: Claude Code v2.1.2xx (August 2026).** Every flag, settings key, hook event
and frontmatter field below was verified against `https://code.claude.com/docs/en/` on 2026-08-30.
This subject moves faster than the JDK: a field added in v2.1.218 and a field removed in v2.1.234
both exist in the same release line. Any leaf whose behaviour is gated on a version carries
`[VERSION]` and **must state the version inline** in the finished guide, because a reader on an
older build will otherwise conclude the guide is wrong.

**The worked example project.** Every `[CASE]` leaf is grounded in a real production system the
reader has access to: the **sdlc-harness** at
`~/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness` — a Python engine that orchestrates
`claude -p` subprocesses across the software development lifecycle, shipped as a versioned plugin
with hooks, agents, skills, playbooks and eval suites. A `[CASE]` leaf must cite a **file path**,
and must quote the real text, not paraphrase it. Invented examples are forbidden in `[CASE]` leaves;
`Foo`/`Bar`/`my-agent` are forbidden everywhere.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[ZERO]` | assume no prior knowledge whatsoever; define every term used in the leaf, in the leaf |
| `[DOC]` | must quote the official documentation (short excerpt) and cite the page |
| `[CASE]` | must be grounded in the sdlc-harness repo, with a real file path and a real quote |
| `[BUILD]` | must ship a complete, working artefact the reader can copy and run |
| `[PROVE]` | must work the argument through or show the observed result, not assert it |
| `[TRAP]` | must carry a `**Trap:**` marker — the wrong belief, the symptom, the fix |
| `[INCIDENT]` | a real recorded failure; must name what broke, what it cost, and the fix |
| `[NUM]` | must state the number, limit, or arithmetic explicitly |
| `[VERSION]` | behaviour is version-gated; must state the version inline |
| `[RESEARCH]` | re-verify against the cited source immediately before writing; this area drifts |
| `[X-REF nn]` | one-paragraph treatment here, full treatment in guide nn |
| `[JAVA]` | must land in the reader's own language — Java/Spring analogy or Java code |

In these notes the `[TRAP]` marker is rendered as `**Pitfall:**`, per the hard instructions above.

---

## PART 0 — GROUND ZERO

*Nothing in this part assumes the reader has heard any of these words before. Every leaf is `[ZERO]`
by default; the tag is repeated only where the write pass is most likely to forget.*

### §0.1 What the thing on the other side actually is

0.1.1 A **large language model** is one function: text in, text out. It has no memory between
      calls, no filesystem, no network, no clock. Say this before anything else. `[ZERO]`
0.1.2 What "predicts the next token" means, stated without ML vocabulary: given the text so far,
      the model produces a probability distribution over what comes next, and one option is
      sampled. `[ZERO]`
0.1.3 A **token** is a chunk of text, roughly 3–4 characters of English or ~0.75 words; code
      tokenises worse than prose because of punctuation and identifiers. `[ZERO]` `[NUM]`
0.1.4 Count tokens for three concrete strings — an English sentence, a Java method, a minified JSON
      blob — and show the ratio differs. `[PROVE]` `[NUM]`
0.1.5 Why token counts matter at all: they are the unit of both **cost** and **the limit**. `[ZERO]`
0.1.6 **Determinism:** the same input does not reliably give the same output. Temperature and
      sampling in one paragraph, no maths. Contrast with a pure Java method. `[ZERO]` `[JAVA]`
0.1.7 What the model *cannot* do, exhaustively: it cannot read a file, run a command, remember
      yesterday, or check whether what it said is true. Everything it appears to do, something
      else did. `[ZERO]` `[TRAP]`
0.1.8 **Confabulation** ("hallucination"): why a wrong answer is produced with the same fluency as
      a right one, and why fluency is therefore worthless as a correctness signal. `[ZERO]` `[TRAP]`
0.1.9 **Training cutoff:** the model's knowledge has a date; anything after it must be supplied in
      the input. Why this alone motivates the whole rest of the guide. `[ZERO]`
0.1.10 Model naming as of 2026: the Claude 5 family (`claude-opus-5`, `claude-sonnet-5`,
       `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`); aliases `opus`/`sonnet`/
       `haiku`/`fable`; what a `[1m]` suffix means. `[DOC]` `[RESEARCH]` `[VERSION]`
0.1.11 Capability tiers as an engineering decision, not a brand: which tier for exploration, which
       for writing code, which for architecture judgment. Cost ratio stated. `[NUM]`
0.1.12 The word **agent**, defined precisely: a model plus a loop plus tools. Not a synonym for
       "chatbot", not a synonym for "AI". `[ZERO]`

*(12 leaves)*

### §0.2 The context window, taught as a data structure

0.2.1 The **context window** is the maximum number of tokens one request may contain — input plus
      output together. It is a hard limit, not a soft one. `[ZERO]` `[NUM]`
0.2.2 Current sizes: 200K standard, 1M in the extended-context tier. What "1M context" costs
      relative to 200K. `[NUM]` `[RESEARCH]` `[VERSION]`
0.2.3 A request is an ordered **list of messages**, each with a role: `system`, `user`,
      `assistant`. Show the literal JSON of a two-turn conversation. `[ZERO]` `[DOC]`
0.2.4 The window is **not** a memory the model writes to. It is the argument list of the next
      call. Say it in those words. `[ZERO]` `[TRAP]`
0.2.5 `[JAVA]` The honest analogy: a stateless `@RestController` method that receives the entire
      conversation as its request body every time, and a client that keeps appending to that body.
      State where the analogy breaks (no session, no cookie, no server-side store). `[JAVA]`
0.2.6 Therefore: cost and latency scale with **conversation length**, not with the length of your
      last message. Work the arithmetic for a 10-turn vs 100-turn session. `[PROVE]` `[NUM]`
0.2.7 What happens at the limit: the request is rejected, or the harness compacts. Both, named.
      `[ZERO]`
0.2.8 **Prompt caching** in one paragraph: the unchanged prefix of a request can be reused at a
      fraction of the price, which is why appending is cheap and *editing the beginning* is not.
      `[NUM]` `[RESEARCH]`
0.2.9 The default cache time-to-live is 5 minutes; `promptCacheTtl` and `subagentPromptCacheTtl`
      change it. Why a 6-minute pause costs real money. `[NUM]` `[DOC]`
0.2.10 The **budget framing** the whole guide rests on: 200K window, autocompaction threshold, and
       what is left for actual work. State the arithmetic. `[NUM]` `[PROVE]`
0.2.11 The five things that consume the window before you type anything: system prompt, tool
       schemas, memory files, skill listing, environment/git snapshot. Forward-reference §3.1.
0.2.12 "It forgot" is almost never a bug: it means *never in context* or *compacted out*. The two
       are distinguished differently and fixed differently. `[TRAP]`

*(12 leaves)*

### §0.3 The agent loop

0.3.1 The loop in three steps, written out: assemble request → model emits text or a tool call →
      harness executes the tool, appends the result, repeat. `[ZERO]`
0.3.2 A **tool** is a function the harness exposes to the model as a name, a description, and a
      JSON input schema. Show one real schema. `[ZERO]` `[DOC]`
0.3.3 The model does not *call* the tool. It emits a `tool_use` block naming the tool and the
      arguments; the harness decides whether to run it. This distinction is the entire basis of
      the permission system. `[ZERO]` `[TRAP]`
0.3.4 A `tool_result` message goes back into the transcript. So tool output is context, and a
      verbose tool is a context leak. `[ZERO]`
0.3.5 A **turn**: one model response plus any tools it triggers. Why `--max-turns` bounds agency
      and a wall-clock timeout bounds time, and why you need both. `[NUM]`
0.3.6 The model chooses tools **from their descriptions alone**. A vague description produces a
      misused tool. `[TRAP]`
0.3.7 Walk a complete real loop end to end: "rename this method" → Grep → Read → Edit → done, with
      the transcript growing at each step and the token count stated after each. `[PROVE]` `[NUM]`
0.3.8 The built-in tools, by category: file (Read, Write, Edit, Glob, Grep), shell (Bash),
      web (WebFetch, WebSearch), delegation (Agent, SendMessage), meta (Skill, ToolSearch),
      task/UI (TodoWrite, AskUserQuestion). `[DOC]` `[RESEARCH]`
0.3.9 Deferred tools and `ToolSearch`: why the full schema of every tool is not loaded up front,
      and what that buys. `[DOC]` `[VERSION]`
0.3.10 **Extended thinking**: the model can emit reasoning tokens before answering; they cost
       tokens and are configurable. `alwaysThinkingEnabled`, `showThinkingSummaries`, the
       `effort` levels `low|medium|high|xhigh|max`. `[DOC]` `[NUM]`
0.3.11 Where "Claude Code" sits: it is *the harness*. The CLI, the VS Code/JetBrains extensions,
       the desktop app and the web app are different front ends over the same loop and the same
       settings files. `[ZERO]` `[DOC]`
0.3.12 The Agent SDK / API as the same loop with the harness written by you. One-paragraph
       orientation; full treatment in §3.8. `[X-REF 21]`

*(12 leaves)*

### §0.4 Getting oriented in the tool itself

0.4.1 Install and authenticate; `claude`, `claude auth login`, `claude auth status`. `[BUILD]`
0.4.2 The three ways in: interactive (`claude`), one-shot (`claude -p "…"`), continue
      (`claude -c`, `claude -r <session>`). `[DOC]`
0.4.3 The diagnostic commands that answer "why is it doing that", and the order to try them:
      `/context`, `/doctor`, `/permissions`, `/hooks`, `/memory`, `/config`, `claude --debug`.
      `[DOC]` `[BUILD]`
0.4.4 `/context` in detail — read a real one and account for every row. This is the single most
      important habit in the guide. `[PROVE]` `[BUILD]`
0.4.5 `/compact` and `/clear` — what each throws away, and when to use which. `[DOC]`
0.4.6 `/rewind` and file checkpointing (`fileCheckpointingEnabled`) — the undo you did not know
      you had. `[DOC]` `[VERSION]`
0.4.7 `!` prefix to run a shell command in-session and put its output in context; `@` to reference
      a file; `#` to save to memory. `[DOC]`
0.4.8 Session persistence: where transcripts live (`~/.claude/projects/<project>/`), how long
      (`cleanupPeriodDays`), and that they are plain JSONL you can read. `[DOC]` `[NUM]`
0.4.9 `--safe-mode` and `--bare`: start with all customisation disabled, to answer "is it my
      config or the tool?". `[DOC]` `[VERSION]`
0.4.10 The first-session checklist for this reader specifically: run `/context`, run `/doctor`,
       read your own `~/.claude/CLAUDE.md`, count its lines. `[BUILD]`

*(10 leaves)*

---

**PART 0 total: 46 leaves**

*Gate before PART 1 — the write pass must be able to answer yes to all five:* can the reader
define a token, a context window, a tool call, a turn, and an agent, without looking back?

---

## PART 1 — BASICS

### §1.1 The `.claude` folder, mapped

1.1.1 `.claude/` is configuration-as-code: a conventional directory the tool discovers, not a
      registry or a database. Everything in it is a file you can diff and commit. `[ZERO]`
1.1.2 The full inventory, one line each: `settings.json`, `settings.local.json`, `CLAUDE.md`,
      `rules/`, `commands/`, `skills/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`,
      `agent-memory/`. `[DOC]`
1.1.3 The user twin at `~/.claude/`: same shapes, machine-wide scope; plus `projects/`,
      `plugins/`, `keybindings.json`, and the tool-owned `~/.claude.json`. `[DOC]`
1.1.4 `~/.claude.json` is written by the tool for the tool — sign-in, MCP registrations, per-project
      trust decisions, `/config` global keys. Do not hand-edit it. `[DOC]` `[TRAP]`
1.1.5 `CLAUDE_CONFIG_DIR` relocates the whole user tree; on Windows `~/.claude` means
      `%USERPROFILE%\.claude`. `[DOC]`
1.1.6 The discovery walk: the tool reads from the session's **primary working directory** and
      every directory above it. Which artefacts walk upward, which load from subdirectories on
      demand, and which do neither. `[DOC]` `[PROVE]`
1.1.7 `[CASE]` The real harness `.claude/`: nine command files, one skill with a `references/`
      subfolder, and a `settings.json` of exactly two keys. Quote it. `[CASE]`
1.1.8 What is *not* in `.claude/` and why: the plugin cache, the transcripts, the auto-memory
      directory. Each lives outside the repo deliberately. `[DOC]`
1.1.9 The single most useful invariant to hold: **if a behaviour surprised you, some file caused
      it, and `/context` plus `/doctor` will name the file.** `[TRAP]`

*(9 leaves)*

### §1.2 Settings files, scope, and precedence

1.2.1 The four settings files and who each reaches: `~/.claude/settings.json` (user),
      `.claude/settings.json` (shared project, committed), `.claude/settings.local.json`
      (project local, gitignored), managed settings. `[DOC]`
1.2.2 The precedence order, highest first: **managed → command line (`--settings`) → project local
      → shared project → user.** A key set higher wins. `[DOC]` `[NUM]`
1.2.3 `[TRAP]` The order is *not* "more specific wins" and it is *not* "command line always wins":
      managed settings beat the command line. `[TRAP]` `[DOC]`
1.2.4 Installing Claude Code creates no settings file. Which files the tool creates for you, and
      when: user file on the first `/config` change it stores there, local file on the first
      "yes, and don't ask again". `[DOC]`
1.2.5 Where the local file lands in a git repo — repository root, not the directory you started
      in — and the exceptions (outside a repo, repo root is `$HOME`, Windows, foreign ownership).
      `[DOC]` `[VERSION]`
1.2.6 Worktrees: the local file comes from the main checkout's root. `[DOC]`
1.2.7 Committing `.claude/settings.json`: what your teammates get, and why permissions and hooks
      in it belong in code review. `[DOC]`
1.2.8 Which keys never take effect from a repository file, and which wait for workspace trust.
      Forward-reference §1.5.10. `[DOC]`
1.2.9 The key groups, named so the reader knows where to look: permissions, hooks, plugins/skills,
      context/memory, model/responses, MCP, sandbox, attribution, auth, data/privacy, interface,
      agents/sessions/worktrees, updates, enterprise, global config. `[DOC]`
1.2.10 The dozen keys this reader will actually touch first, with values:
       `permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`,
       `autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`,
       `statusLine`, `cleanupPeriodDays`. `[DOC]` `[BUILD]`
1.2.11 `env` — settings-supplied environment variables for every session; how they compose across
       scopes, and that they apply to hooks and Bash too. `[DOC]`
1.2.12 `[CASE]` The harness's real `settings.json`: `permissions.allow` of four entries plus
       `enabledPlugins` of four plugins (three official LSP plugins and its own). Quote it and
       explain each entry. `[CASE]`
1.2.13 Verifying a setting actually applied: `/config`, `/permissions`, `claude doctor`'s resolved
       settings, and the invalid-settings dialog. `[BUILD]`
1.2.14 `[TRAP]` A silently-ignored key. Unknown keys, `mcp__` rules with parentheses in a settings
       file, and path rules on tools that never consult them are all accepted and then ignored —
       with a startup warning most people never read. `[TRAP]` `[DOC]`
1.2.15 Managed settings as an org control surface, in one paragraph: what it is for, the
       `allowManaged*Only` locks, and why a developer cannot override it. Full treatment §2.9.
1.2.16 `--setting-sources user,project,local` — choosing which layers load *at all*. Set up the
       incident in §3.7 now; do not resolve it here. `[DOC]`

*(16 leaves)*

### §1.3 `CLAUDE.md` and the memory system

1.3.1 Two mechanisms, clearly separated: `CLAUDE.md` files (you write, instructions) and **auto
      memory** (Claude writes, learnings). Both load every session. `[DOC]`
1.3.2 Both are **context, not enforced configuration.** Claude reads them and tries; a hook is the
      only guarantee. Repeat this sentence in the guide; it is the most-missed fact here. `[DOC]`
      `[TRAP]`
1.3.3 The four `CLAUDE.md` locations in load order: managed policy path (per-OS), `~/.claude/
      CLAUDE.md`, `./CLAUDE.md` or `./.claude/CLAUDE.md`, `./CLAUDE.local.md`. `[DOC]`
1.3.4 The managed policy paths, exactly: macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`,
      Linux/WSL `/etc/claude-code/CLAUDE.md`, Windows `C:\Program Files\ClaudeCode\CLAUDE.md`.
      `[DOC]`
1.3.5 How they load: **concatenated, not overriding** — root-down ordering, so the file nearest
      your working directory is read last, and `CLAUDE.local.md` after `CLAUDE.md` at each level.
      `[DOC]` `[PROVE]`
1.3.6 Subdirectory `CLAUDE.md` files load **on demand**, when Claude reads a file in that
      directory — not at launch. `[DOC]`
1.3.7 `@path` imports: relative to the importing file, recursive to a **maximum depth of four
      hops**, skipped inside code spans and fences. `[DOC]` `[NUM]`
1.3.8 `[TRAP]` An import does not save context — the imported file loads at launch too. Splitting
      a large `CLAUDE.md` into imports buys organisation only. `[TRAP]` `[DOC]`
1.3.9 External imports (paths resolving outside the working directory) trigger a one-time approval
      dialog for project files; user-scope files are trusted. Why the dialog exists. `[DOC]`
1.3.10 Size guidance: **target under 200 lines**; a file over 4 MiB is skipped entirely; longer
       files measurably reduce adherence. `[DOC]` `[NUM]`
1.3.11 `[PROVE]` Measure the cost of your own `CLAUDE.md`: token count × turns in a session =
       tokens spent on it. Do the arithmetic for the reader's actual global file. `[PROVE]` `[NUM]`
1.3.12 Writing instructions that get followed: specific over vague, verifiable over aspirational,
       structured over prose, consistent over contradictory. Three before/after pairs. `[DOC]`
1.3.13 Block-level HTML comments are stripped before injection — free maintainer notes. `[DOC]`
1.3.14 `.claude/rules/` — modular instruction files, discovered recursively, same priority as
       `.claude/CLAUDE.md` when they have no `paths` frontmatter. `[DOC]`
1.3.15 **Path-specific rules**: `paths:` frontmatter globs, loaded only when Claude touches a
       matching file. The one mechanism that makes a large instruction set affordable. `[DOC]`
1.3.16 `paths` glob mechanics: brace expansion, the shared budget of **1,000 expanded patterns /
       4 MiB**, what happens on overflow, and the `[`-bracket-expression pitfall. `[DOC]` `[NUM]`
       `[VERSION]`
1.3.17 User-level rules in `~/.claude/rules/` load before project rules, giving project rules
       higher priority. Symlinks are supported and cycles are handled. `[DOC]`
1.3.18 `AGENTS.md`: Claude Code does not read it. The `@AGENTS.md` import and the symlink, and why
       the import is preferable on Windows. `[DOC]`
1.3.19 `claudeMdExcludes` for monorepos — glob against absolute paths, merges across layers,
       cannot exclude managed policy. `[DOC]`
1.3.20 `claudeMd` in managed settings: org instructions inline in JSON, honoured only at managed
       scope. `[DOC]`
1.3.21 **Auto memory**: the four types Claude records (`user`, `feedback`, `project`, `reference`),
       what it deliberately skips, and that it does not save every session. `[DOC]`
1.3.22 Auto-memory storage: `~/.claude/projects/<project>/memory/` with a `MEMORY.md` index plus
       one topic file per memory; keyed on the git repo so worktrees share it; machine-local.
       `[DOC]`
1.3.23 Only the **first 200 lines or 25 KB of `MEMORY.md`** loads at session start; topic files are
       read on demand. What happens when the index exceeds the limit. `[DOC]` `[NUM]`
1.3.24 `autoMemoryEnabled`, `autoMemoryDirectory`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and the
       `/memory` toggle. The `modified` frontmatter timestamp. `[DOC]` `[VERSION]`
1.3.25 Auto memory does **not** load into subagents (a fork excepted); a subagent's own `memory`
       field is a separate directory. `[DOC]`
1.3.26 What survives `/compact`: project-root `CLAUDE.md` is re-read from disk and re-injected;
       nested files and path-scoped rules reload only when re-matched; conversation-only
       instructions are gone. `[DOC]` `[TRAP]`
1.3.27 `/memory`, `/context`, `/init`, `/import`, and the `InstructionsLoaded` hook as the four
       ways to find out what actually loaded. `[DOC]`
1.3.28 `[TRAP]` "Claude ignored my CLAUDE.md." The diagnostic ladder: did it load (`/context`), is
       it specific enough, does another file contradict it, and should it have been a hook.
       `[TRAP]` `[DOC]`
1.3.29 `[CASE]` Read the reader's own two-level setup — the 125-line global `~/.claude/CLAUDE.md`
       and the project `.claude/CLAUDE.md` — and account for what each costs and whether each
       entry belongs there or in a skill. `[CASE]` `[BUILD]`

*(29 leaves)*

### §1.4 The permission system

1.4.1 The one-sentence foundation: **permission rules are enforced by Claude Code, not by the
      model.** Prompt and `CLAUDE.md` shape what Claude *tries*; rules decide what runs. `[DOC]`
      `[ZERO]`
1.4.2 The three rule lists — `allow`, `ask`, `deny` — and the evaluation order: **deny, then ask,
      then allow; first match wins; specificity does not reorder.** `[DOC]` `[NUM]`
1.4.3 `[TRAP]` A broad deny cannot carry allowlist exceptions: `Bash(aws *)` in deny blocks
      `Bash(aws s3 ls)` in allow. Same for ask over allow. `[TRAP]` `[DOC]`
1.4.4 Deny of a **bare tool name** removes the tool from Claude's context entirely; a **scoped**
      deny leaves the tool visible and blocks matching calls. Two different mechanisms. `[DOC]`
1.4.5 Rule syntax: `Tool` or `Tool(specifier)`. `Bash(*)` ≡ `Bash`. `[DOC]`
1.4.6 Bash specifiers: the rule matches the **whole command text** with `*` standing for any text.
      Put the `*` after the subcommand; the startup warning when you do not. `[DOC]` `[TRAP]`
1.4.7 The wildcard matching table, reproduced and explained: `Bash(npm run build)` vs
      `Bash(npm run *)` vs `Bash(git log * main)` vs `Bash(git * main)` vs `Bash(* --version)` vs
      `Bash(ls *)` vs `Bash(ls*)`. `[DOC]` `[PROVE]`
1.4.8 `[TRAP]` `Bash(git * main)` allows `git -c core.fsmonitor=<script> diff main` — the `*`
      spans options, including options that make git execute a program you name. `[TRAP]` `[DOC]`
1.4.9 **Compound commands**: the recognised separators (`&&`, `||`, `;`, `|`, `|&`, `&`, newline),
      and that each subcommand must match independently. `[DOC]` `[NUM]`
1.4.10 "Yes, and don't ask again" on a compound command saves a **separate rule per subcommand**,
       up to 5. `[DOC]` `[NUM]`
1.4.11 **Wrapper stripping**: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`,
       `noglob`, and bare `xargs` are stripped before matching. `command -v` and `nocorrect` are
       not. Known-safe leading env assignments are stripped for allow rules; deny rules match
       past any assignment. `[DOC]` `[NUM]`
1.4.12 `[TRAP]` Environment runners are **not** stripped: `Bash(devbox run *)` matches
       `devbox run rm -rf .`. Same class: `npx`, `docker exec`, `direnv exec`, `mise exec`.
       Write runner+inner rules instead. `[TRAP]` `[DOC]`
1.4.13 Exec wrappers that a prefix rule cannot auto-approve: `watch`, `setsid`, `ionice`, `flock`,
       and `find` with `-exec`/`-delete`. `[DOC]`
1.4.14 The built-in **read-only command set** that never prompts in any mode (`ls`, `cat`, `echo`,
       `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only
       `git`), that it is not configurable, and the glob/redirect cases that still prompt. `[DOC]`
1.4.15 Redirections add a check on the target path. `[DOC]`
1.4.16 `Read`/`Edit` rules use **gitignore pattern syntax**; the four anchor forms (`//abs`, `~/`,
       `/`, bare); `Read(./.env)`, `Read(./secrets/**)`. `[DOC]`
1.4.17 A `Read` deny also blocks Edit and Write on the same path — but not `NotebookEdit`, so add
       an `Edit` deny too. `[DOC]` `[VERSION]`
1.4.18 `[TRAP]` File permissions are checked against `Edit(path)` and `Read(path)` **only**. A
       `Write(docs/**)`, `NotebookEdit(...)`, `MultiEdit(...)` or `Glob(...)` path rule is accepted
       and never consulted. Use `Edit(...)`/`Read(...)`. `[TRAP]` `[DOC]` `[VERSION]`
1.4.19 `[TRAP]` Read/Edit deny rules cover the built-in file tools and file commands Claude Code
       recognises in Bash (`cat`, `head`, `tail`, `sed`) — **not** an arbitrary subprocess. A
       Python script that opens the file itself is not stopped. Sandbox is the OS-level answer.
       `[TRAP]` `[DOC]`
1.4.20 `WebFetch(domain:example.com)`; allow-or-deny-every-fetch forms. `[DOC]`
1.4.21 MCP rules: `mcp__server`, `mcp__server__*`, `mcp__server__tool`. Parenthesised `mcp__` rules
       in a settings file are skipped; use `--disallowedTools` for parameter matching. `[DOC]`
1.4.22 `Agent(Name)` rules — gate which subagents may run, including the built-ins
       `Agent(Explore)`, `Agent(Plan)`, `Agent(fork)`. `[DOC]`
1.4.23 Parameter matching for deny/ask on any built-in tool: `Tool(param:value)`, e.g.
       `Agent(model:opus)`, `Agent(isolation:worktree)`, `Bash(run_in_background:true)`. One
       parameter per rule; direct fields only; `*` wildcard; compared before normalisation. `[DOC]`
1.4.24 `Cd` rules — not model-invocable; bare deny disables `/cd`; any allow rule switches to
       allowlist mode; `*` is one segment and `**` spans segments. `[DOC]`
1.4.25 The six permission modes and exactly what each auto-approves: `default`/`manual`,
       `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. `[DOC]` `[NUM]`
1.4.26 `acceptEdits` in detail — file edits **plus** an auto-approved filesystem-command set that
       is wider than most people expect: `mkdir`, `touch`, **`rm`, `rmdir`**, `mv`, `cp`, **`sed`**,
       for paths in the working directory or `additionalDirectories`. `[DOC]` `[NUM]`
1.4.26a `[TRAP]` That set includes deletion. "Accept edits" reads like a promise about *edits*, and
       it auto-approves `rm` and `rmdir` inside the working directory. State the blast radius
       plainly. `[TRAP]` `[DOC]`
1.4.26b What `acceptEdits` does *not* cover — `mvn`, `git commit`, `chmod`, `java` — is the symptom
       in the §3.7 incident. `[DOC]`
1.4.27 `auto` mode: a background classifier reviews actions instead of you; `autoMode` rules,
       `autoMode.classifyAllShell`, `disableAutoMode`. The defaults must be stated, not just the
       mechanism: the classifier runs on **Sonnet 5**, with **3-consecutive / 20-total** block
       fallback thresholds. `[DOC]` `[VERSION]` `[NUM]`
1.4.28 `bypassPermissions`: what it still refuses, enumerated exactly — critical-path `rm`/`rmdir`
       deletions, explicit `ask`-rule matches, always-interactive tools (`AskUserQuestion`,
       `requiresUserInteraction` MCP tools), and two cross-session messaging safeguards
       (`isolatePeerMachines`, held inbound messages). Defensible only in a container or VM.
       `[DOC]` `[NUM]`
1.4.28a `[TRAP]` It does **not** protect `.git` and `.claude`. Protected-path writes are allowed
       under `bypassPermissions`, so the mode can rewrite the very configuration that would
       otherwise constrain it. The widely-repeated "it still refuses protected paths" claim is
       false and this syllabus asserted it until 2026-08-30. `[TRAP]` `[DOC]` `[INCIDENT]`
1.4.29 `permissions.defaultMode`, `disableBypassPermissionsMode`, `disableAutoMode` — and why these
       belong in managed settings. `[DOC]`
1.4.30 **Working directories**: the primary working directory, `--add-dir`, `/add-dir`,
       `permissions.additionalDirectories`. Additional directories grant **file access, not
       configuration**. `[DOC]` `[TRAP]`
1.4.31 `/cd` moves the primary working directory and re-applies the new directory's project
       settings, hooks, MCP servers, plugins, skills, subagents and `env`. `[DOC]` `[VERSION]`
1.4.32 **Workspace trust**: `permissions.allow` and `additionalDirectories` from a project's
       committed settings apply only after you accept the trust dialog; `deny`/`ask` are not
       gated because they only restrict. `[DOC]`
1.4.33 How trust is keyed: on the git repo root inside a repo (excluding nested repos), on the
       start directory outside one, session-only in `$HOME`. `[DOC]`
1.4.34 A `-p` or SDK session shows no trust dialog, because it is non-interactive. The consequence
       is the **opposite** of dangerous-by-default: for an untrusted folder such a session does
       **not** apply the committed `allow` / `additionalDirectories` rules at all, and prints a
       stderr warning instead. "Counts as accepted" applies only to the much narrower git
       tracked/untracked check on `settings.local.json` (§1.4.35). `[DOC]` `[TRAP]`
1.4.34a `[TRAP]` The real risk, once 1.4.34 is stated correctly, is **stickiness**: trust is keyed
       per repository-root path and is **never re-checked when a commit changes the ruleset**. You
       reviewed the rules once; a later commit can widen `permissions.allow` and no dialog reappears.
       That is the thing to say in an interview, not the false version this syllabus carried until
       2026-08-30. `[TRAP]` `[DOC]` `[INCIDENT]`
1.4.35 `.claude/settings.local.json` and trust: your own untracked file applies immediately; a
       *tracked* local file, or a symlinked `.claude`, is treated as repository-supplied and waits.
       `[DOC]`
1.4.36 Precedence for permissions: **a deny at any level cannot be overridden by any other level**,
       including `--allowedTools` and managed settings. `[DOC]`
1.4.37 `/permissions` — read the rules and the file each came from; edits apply from Claude's next
       tool call in the same turn. `[DOC]` `[VERSION]` `[BUILD]`
1.4.38 `--allowedTools` / `--disallowedTools` / `--tools` as per-run overrides. `[DOC]`
1.4.39 Sandboxing as the layer below permissions: `sandbox.enabled`, filesystem allow/deny,
       network allowlist, credential masking. One paragraph each on why an OS-level boundary
       catches what a rule cannot. `[DOC]` `[RESEARCH]`
1.4.40 `[BUILD]` Write a permission block for a real repository: allow the build and test commands,
       deny `git push`, deny reads of `.env` and `secrets/**`, deny `rm -rf`. Then prove each rule
       fires. `[BUILD]` `[PROVE]`
1.4.41 `[CASE]` The harness's `permissions.allow` — `Read(**)`, `Edit(**)`, `Bash(*)`,
       `mcp__atlassian-cloud__*` — and the destructive-command deny-list it is paired with. Why
       `Bash(*)` plus a deny-list is a considered choice and not laziness. `[CASE]`

*(45 leaves)*

### §1.5 Skills and slash commands

1.5.1 The merge, stated first because every older article gets it wrong: **custom commands are
      skills.** `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create
      `/deploy` and behave the same way. `[DOC]` `[VERSION]` `[TRAP]`
1.5.2 What a skill *is*: a markdown file of instructions that the tool injects into the
      conversation when invoked. Not code, not a tool, not a plugin. `[ZERO]`
1.5.3 The four locations and the conflict order: enterprise → personal (`~/.claude/skills/`) →
      project (`.claude/skills/`); a skill at any level overrides a bundled skill of the same name
      but not its aliases; plugin skills are namespaced `plugin:skill` and cannot conflict; a
      skill beats a same-named `commands/` file. `[DOC]`
1.5.4 Nested `.claude/skills/` below the working directory become available when Claude reads a
      file in that subtree — the monorepo mechanism. `[DOC]`
1.5.5 **Progressive disclosure**, the central idea: only the frontmatter `description` (plus
      `when_to_use`) is in context up front; the body loads when the skill fires. This is why 50
      skills cost almost nothing and 50 skills' worth of `CLAUDE.md` costs everything. `[DOC]`
      `[NUM]`
1.5.6 The listing budget is **two different numbers** and conflating them is an error this
      syllabus shipped: `skillListingMaxDescChars` is the **per-entry** cap, default **1,536
      characters** on combined `description` + `when_to_use`; `skillListingBudgetFraction` is a
      separate **pool** budget across all entries, roughly **1% of the context window**. A skill
      can be inside the per-entry cap and still be dropped from the listing by the pool budget.
      `[DOC]` `[NUM]` `[TRAP]`
1.5.7 Frontmatter, every field: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
      `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`,
      `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`,
      `compatibility`. `[DOC]`
1.5.8 `[TRAP]` `allowed-tools` **pre-approves, it does not restrict.** It grants permission for
      the invoking turn only and clears on your next message; every other tool stays callable.
      `disallowed-tools` is the field that removes tools. `[TRAP]` `[DOC]`
1.5.9 Frontmatter is read only when the opening `---` is the file's first line; otherwise the whole
      file is content. Boolean fields accept `yes/no/on/off/1/0`. `[DOC]` `[VERSION]` `[TRAP]`
1.5.10 Who invokes: `disable-model-invocation: true` for human-only workflows,
       `user-invocable: false` for model-only background knowledge, `paths:` to gate automatic
       activation by file glob. `[DOC]`
1.5.11 String substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, named `$name` via the `arguments`
       field, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`. `[DOC]`
1.5.12 **Dynamic context injection**: `` !`command` `` runs a shell command *before* the content
       is sent, and its output replaces the placeholder. The fenced ` ```! ` block form for
       multi-line. `[DOC]`
1.5.13 Injection mechanics that bite: substitution runs **once** over the original file and output
       is not re-scanned; the inline form is recognised only at line start or after whitespace, so
       `` KEY=!`cmd` `` stays literal. `[DOC]` `[TRAP]`
1.5.14 `disableSkillShellExecution` turns injection off for user/project/plugin/additional-directory
       skills. Why an org might set it. `[DOC]`
1.5.15 **Skill content lifecycle**: the rendered content enters as one message and *stays* across
       later turns; the file is not re-read; a re-invocation with identical content adds a note,
       not a second copy. Write standing instructions, not one-time steps. `[DOC]`
1.5.16 Skills through compaction: the most recent invocation of each skill is re-attached after the
       summary, **first 5,000 tokens each, 25,000 tokens combined**, filled newest-first — so old
       skills can vanish. `[DOC]` `[NUM]`
1.5.17 `context: fork` + `agent:` + `background:` — run the skill in a forked subagent instead of
       inline. When that is the right shape. `[DOC]` `[VERSION]`
1.5.18 Supporting files: a skill is a *directory*, so `references/`, scripts and data live beside
       `SKILL.md` and are read on demand via `${CLAUDE_SKILL_DIR}`. `[DOC]`
1.5.19 `[CASE]` The `playwright-cli` skill and its `references/` subfolder — a reference library
       that costs nothing until needed. Two corrections to the form this leaf originally took: it
       is a **repo-root** skill at `.claude/skills/playwright-cli/`, **not** a plugin skill, and
       there are **nine** reference files on disk, not ten. List the filenames as found; never pad
       a count to match prose. `[CASE]` `[NUM]`
1.5.20 `[CASE]` The harness's `bootstrap` skill: `name` / `description` / `when_to_use` /
       `allowed-tools: [Bash, Read, AskUserQuestion]`, and a body that is an **orchestrator, not a
       rewrite** — each step delegates to a tested `bootstrap-*.sh`. Quote the "why deterministic
       scripts and not model judgment" paragraph verbatim. The scripts live under
       `plugins/sdlc-harness/scripts/` (**not** `hooks/`) and there are **fifteen** of them, plus
       three `triage-*.sh`. Count them at write time rather than trusting this number. `[CASE]`
       `[NUM]`
1.5.21 `[CASE]` Prompt composition without duplication: `/implement-story` inlines
       `/run-conductor` with a ` ```! ` block running
       `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, then states only its binding
       overrides, forwarded flags and **rejected flags**. DRY applied to prompts. `[CASE]`
1.5.22 `[TRAP]` A description that names the **topic** rather than the **trigger** makes the skill
       invisible or always-on. Three bad descriptions rewritten. `[TRAP]`
1.5.23 Built-in commands **versus** bundled skills — a real distinction, and the inventory must be
       tagged rather than lumped. Built-ins include `/help`, `/compact`, `/clear`, `/context`,
       `/config`, `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/cd`,
       `/add-dir`, `/model`, `/effort`, **`/run`**. Bundled **skills** (tagged `[Skill]`) include
       **`/doctor`**, **`/rewind`**, `/code-review`, `/security-review`, `/loop`. Note that
       `/doctor` and `/rewind` are skills and `/run` is a built-in — the reverse of what this
       syllabus originally implied. Re-check the tags at write time; this list drifts.
       `[DOC]` `[RESEARCH]` `[TRAP]`
1.5.24 `skillOverrides`, `disableBundledSkills`, `syncClaudeAiSkills`, `--disable-slash-commands`
       — the visibility and kill switches. `[DOC]`
1.5.25 `[BUILD]` Write a real skill for this repository: one that regenerates a topic guide's
       atomic-concept checklist. Frontmatter, `$ARGUMENTS`, one `` !`command` `` injection, a
       `references/` file. Then invoke it and read `/context` before and after. `[BUILD]` `[PROVE]`
1.5.26 The decision table the reader needs: fact that always applies → `CLAUDE.md`; fact that
       applies to one file type → path-scoped rule; procedure → skill; must-happen → hook;
       verbose-in/small-out → subagent; distribution → plugin. `[NUM]`

*(26 leaves)*

---

**PART 1 total: 125 leaves**

---

## PART 2 — INTERMEDIATE

### §2.1 Subagents

2.1.1 What a subagent is, mechanically: a **separate context window** running the same loop, given
      a task string, returning a final message. Nothing else crosses the boundary. `[ZERO]`
2.1.2 Definition file locations and precedence, highest first: managed settings → `--agents` CLI
      JSON → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/`. `[DOC]` `[NUM]`
2.1.3 `[TRAP]` Note the inversion against skills: for **agents**, project beats user; for
      **skills**, personal beats project. Two subsystems, two orders. `[TRAP]` `[DOC]`
2.1.4 The file format: YAML frontmatter plus a markdown system prompt. `[DOC]`
2.1.5 Frontmatter, every field: `name`, `description`, `tools`, `disallowedTools`, `model`,
      `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`,
      `effort`, `isolation`, `color`, `initialPrompt`, `experimental`. `[DOC]`
2.1.6 `description` is the routing signal — it says *when to delegate*, not what the agent is.
      The combined description budget across custom agents is ~**15,000 tokens**. `[DOC]` `[NUM]`
2.1.7 `tools` as an allowlist vs `disallowedTools` as a denylist; MCP-prefix forms; restricting
      which agents an agent may spawn with `tools: Agent(worker, researcher)`. `[DOC]`
2.1.8 **What loads at subagent startup**: its own system prompt + environment, the delegating task
      message, the full `CLAUDE.md` hierarchy (except Explore/Plan), a git-status snapshot from
      parent session start, preloaded `skills`, the sibling roster. `[DOC]` `[NUM]`
2.1.9 **What does not load**: conversation history, the main output style, auto memory, previously
      read files or invoked skills. Forks are the exception and inherit everything. `[DOC]`
2.1.10 `[TRAP]` Therefore a subagent knows nothing your session learned. Everything it needs goes
       in the task string or a file it is told to read. `[TRAP]`
2.1.11 The four built-ins and what each is for: `Explore` (read-only search), `Plan` (read-only
       research), `general-purpose`, `claude` (catch-all). `[DOC]`
2.1.12 Foreground vs background execution; `background: true`; `Ctrl+B`;
       `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`; how permission prompts surface from a background
       agent. `[DOC]`
2.1.13 **Forks** (`/subtask`, `context: fork`): inherit the whole conversation and system prompt,
       share the prompt cache (cheaper), cannot spawn further forks. When a fork beats a fresh
       agent. `[DOC]`
2.1.14 Limits and guardrails, with numbers: default **20** concurrent subagents
       (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), nesting depth **3**
       (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), and the tools never available in a subagent
       (`AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `Workflow`). `[DOC]` `[NUM]`
2.1.15 Naming rules: no `:` (reserved for plugin scoping), no leading `-`. `[DOC]`
2.1.16 Persistent agent memory: `memory: user|project|local` and the three directories it maps to.
       `[DOC]`
2.1.17 Resuming a subagent via `SendMessage` with its ID or name; where subagent transcripts live
       (`~/.claude/projects/{project}/{sessionId}/subagents/`). `[DOC]` `[VERSION]`
2.1.18 Invocation, three levels: natural language (Claude decides), `@"name (agent)"` mention
       (guaranteed), `claude --agent <name>` or the `agent` setting (whole session). `[DOC]`
2.1.19 The cost model: a subagent costs roughly **2×** the tokens of inline work because context
       must be re-supplied; a team of agents 3–4×. State when that is worth it. `[NUM]` `[PROVE]`
2.1.20 The three cases where it pays: verbose input with a small answer; genuinely parallel work
       with non-overlapping writes; a different capability set (read-only auditor, no-network
       reviewer). `[NUM]`
2.1.21 The output protocol that makes delegation actually save context: **agents write findings to
       files and return status + a few findings + a path.** Message bodies are not a data channel.
2.1.22 `[CASE]` `progress-verifier.md` — 20 lines, and four transferable design properties: body as
       a pointer to a versioned prompt file; a machine-parseable output contract
       (`## Progress Verdict: progressing|stalled`); explicit read boundaries; artifacts-only
       evidence discipline with an explicit ban on inspecting the coder's live session. `[CASE]`
2.1.23 `[CASE]` `calibrator.md` — enumerated write boundaries (two paths it may write, four it may
       not) and the line **"No Jira API tool is ever given to this agent."** Capability denied at
       the tool layer; the prose only documents it. `[CASE]`
2.1.24 `[TRAP]` Parallel agents must partition the **filesystem**, not the topic. Folder-scoped
       lanes plus one flat shared directory is not a partition. A same-slug collision overwrites
       silently and leaves no orphan to notice. **One writer per output path, ever.** `[TRAP]`
       `[INCIDENT]`
2.1.25 `[BUILD]` Write a `test-runner` agent for a Java repo: read-only plus `Bash(mvn test *)`,
       `model: haiku`, a fixed output contract, and a verdict line the caller can grep. `[BUILD]`
       `[JAVA]`

*(25 leaves)*

### §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.1 `--agent <name>` loads a **registered** agent — its full system prompt, model and tool
      allowlist. The parity mechanism for programmatically spawning a subagent. `[DOC]`
2.2.2 `--append-system-prompt <text>` **appends to the default** system prompt. The default persona
      is still there; you decorated it. `[DOC]` `[TRAP]`
2.2.3 `--system-prompt` / `--system-prompt-file` **replace** the whole thing. What you lose.
      `[DOC]`
2.2.4 `--append-subagent-system-prompt` for every subagent; `--exclude-dynamic-system-prompt-sections`
      to move per-machine sections out of the cached prefix. `[DOC]` `[VERSION]`
2.2.5 `[CASE]` `engine/agent.py` documents the distinction explicitly and calls `--agent` "the
      parity mechanism for an auto-spawned subagent, not `--append-system-prompt` (which only
      appends to the default prompt)". Quote it. `[CASE]`
2.2.6 `[CASE]` `load_agent_prompt()` strips the `--- … ---` frontmatter before appending, because
      YAML metadata leaking into a system prompt is noise the model tries to interpret. The regex
      and why it is anchored. `[CASE]` `[SOURCE-EQUIV]`
2.2.7 `[TRAP]` Choosing `--append-system-prompt` when you meant `--agent`: the symptom is an agent
      that behaves *almost* right and ignores its tool restrictions, because it never had any.
      `[TRAP]`

*(7 leaves)*

### §2.3 Hooks

2.3.1 What a hook is: a command **the harness runs** at a lifecycle event, not something the model
      decides to run. Therefore the only mechanism that *guarantees* something happens. `[ZERO]`
      `[DOC]`
2.3.2 The configuration schema: `hooks.<Event>[] → { matcher, hooks: [{ type, … }] }`, plus
      `if`, `timeout`, `statusMessage`, `once`. `[DOC]`
2.3.3 The five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. What each is for,
      and that the last two put a model in the enforcement path. `[DOC]` `[VERSION]`
2.3.4 `command` handler fields: `command`, `args`, `async`, `asyncRewake`, `shell`. `[DOC]`
2.3.5 `http` handler: `url`, `headers`, `allowedEnvVars`, plus the `allowedHttpHookUrls` and
      `httpHookAllowedEnvVars` settings that fence it. `[DOC]`
2.3.6 The full event catalogue (32 events as of v2.1.2xx), grouped so it is learnable rather than
      memorised: session lifecycle (`SessionStart`, `Setup`, `SessionEnd`), prompt
      (`UserPromptSubmit`, `UserPromptExpansion`), tools (`PreToolUse`, `PostToolUse`,
      `PostToolUseFailure`, `PostToolBatch`), permissions (`PermissionRequest`,
      `PermissionDenied`), turn (`Stop`, `StopFailure`), subagents (`SubagentStart`,
      `SubagentStop`), tasks (`TaskCreated`, `TaskCompleted`, `TeammateIdle`), context
      (`PreCompact`, `PostCompact`, `InstructionsLoaded`), environment (`ConfigChange`,
      `CwdChanged`, `DirectoryAdded`, `FileChanged`), worktrees (`WorktreeCreate`,
      `WorktreeRemove`), MCP (`Elicitation`, `ElicitationResult`), UI (`Notification`,
      `MessageDisplay`). `[DOC]` `[NUM]` `[RESEARCH]`
2.3.7 Which events **can block** and which cannot — the table, because reaching for a hook that
      cannot block is the most common design error here. `[DOC]` `[NUM]`
2.3.8 `matcher` semantics: `*`/empty/omitted matches all; `|` or `,` for an exact list; anything
      with special characters is a regex. `[DOC]`
2.3.9 Matcher values differ per event: tool name for tool events, session type
      (`startup|resume|clear|compact|fork`) for `SessionStart`, end reason for `SessionEnd`, agent
      type for subagent events, config source for `ConfigChange`, error type for `StopFailure`,
      filenames for `FileChanged`. `[DOC]`
2.3.10 The stdin JSON every event receives: `session_id`, `prompt_id`, `transcript_path`, `cwd`,
       `permission_mode`, `hook_event_name`, `effort.level`; plus `agent_id`/`agent_type` when
       running under a subagent. `[DOC]`
2.3.11 Event-specific stdin payloads: `tool_name`/`tool_input`/`tool_use_id`, `user_input`,
       `last_assistant_message`/`stop_reason`, `file_path`/`change_type`. `[DOC]`
2.3.12 **Exit-code semantics**, precisely: `0` = success (stdout goes to the debug log, except
       `UserPromptSubmit`/`UserPromptExpansion`/`SessionStart` where it is shown to Claude);
       `2` = blocking error and **the only code that blocks without JSON**; anything else =
       non-blocking. `[DOC]` `[NUM]`
2.3.13 `[TRAP]` Exit 2 overrides a JSON `permissionDecision: "allow"` — it blocks regardless.
       `[TRAP]` `[DOC]`
2.3.14 The JSON output contract has **three** kinds of field, and conflating them is the error
       this syllabus itself originally shipped: **universal** top-level fields every event accepts
       (`continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`);
       **top-level `decision` + `reason`**, used by most events to block; and
       **`hookSpecificOutput`**, a nested object for events needing richer control, requiring a
       `hookEventName` field. `[DOC]` `[VERSION]`
2.3.14a The universal kill switch: top-level `continue: false` makes Claude **stop processing
       entirely** after the hook runs, and **takes precedence over any event-specific decision
       field**. `stopReason` is the message shown to the **user** (never to Claude) when it fires.
       Default is `true`. `suppressOutput` is accepted and does nothing. `[DOC]` `[NUM]`
2.3.14b Output strings — `additionalContext`, `systemMessage`, plain stdout — are capped at
       **10,000 characters**; longer output is written to a file and replaced with a preview plus
       path. `[DOC]` `[NUM]`
2.3.15 Which field each event honours — the table. `PreToolUse` uses
       `hookSpecificOutput.permissionDecision` + `permissionDecisionReason` (its top-level
       `decision`/`reason` form is **deprecated**, with `"approve"`/`"block"` mapping to
       `"allow"`/`"deny"`). `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`,
       `ConfigChange`, `PreCompact` and others use **top-level `decision`/`reason`**.
       `PermissionRequest` uses a `decision` **object**. `[DOC]` `[TRAP]`
2.3.15a `[TRAP]` **`Stop` semantics are inverted from every reader's first guess.** To keep Claude
       working you return `decision: "block"` — you are blocking the *stop*, not requesting a
       continue — and `reason` is **required** when you do. Omitting `decision` allows the stop.
       There is **no** `hookSpecificOutput.continue` field; the boolean `continue` is the universal
       top-level kill switch of 2.3.14a and means the opposite thing. Three independent write
       attempts at this leaf got it wrong three different ways before anyone read the raw page.
       `[TRAP]` `[DOC]` `[INCIDENT]`
2.3.15b `hookSpecificOutput.additionalContext` on `Stop` as the third option: the conversation
       continues under the same loop protections as `decision: "block"`, but the transcript labels
       it `Stop hook feedback` rather than raising a hook error. Use it when the hook is working as
       designed. `[DOC]`
2.3.15c The loop protections that stop a `Stop` hook looping forever: the `stop_hook_active` stdin
       field and an **8-consecutive-continuation cap**. A `Stop` hook without awareness of these is
       an infinite-turn generator. `[DOC]` `[NUM]` `[TRAP]`
2.3.16 Hook decisions **do not bypass permission rules**: a matching deny still blocks and a
       matching ask still prompts, whatever the hook returned. `[DOC]` `[TRAP]`
2.3.17 Path placeholders and env vars: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
       `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_CODE_REMOTE`, `CLAUDE_EFFORT`,
       `CLAUDE_PLUGIN_OPTION_*`. `[DOC]`
2.3.18 Where hooks may be configured: user/project/local settings, managed policy, plugin
       `hooks/hooks.json`, **skill frontmatter** (rest of session), **subagent frontmatter**
       (while it runs). Six sources. `[DOC]`
2.3.19 `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and
       that individual hooks cannot be disabled — only deleted. `[DOC]`
2.3.20 `/hooks` as the read-only browser: events, counts, matcher groups, handler details and
       source file. The debug log records which hooks matched and how they exited. `[DOC]`
       `[BUILD]`
2.3.21 `[CASE]` The harness's `hooks.json`: three `SessionStart` handlers plus one `PostToolUse`
       with `matcher: "Write|Edit"`, each invoking `bash "${CLAUDE_PLUGIN_ROOT}/hooks/…"`. Quote
       it whole; it is 30 lines and complete. `[CASE]`
2.3.22 `[CASE]` `check-init.sh` as a masterclass in advisory hooks. Every finding is a tagged
       instruction to the model: `[HANDBOOK_ACTIVE]`, `[HANDBOOK_SELECT]`,
       `[HARNESS_BOOTSTRAP_REQUIRED]`, `[HARNESS_UPDATE_AVAILABLE]`,
       `[PLUGIN_DEPENDENCY_UNRESOLVED]`, `[CLI_TOOLS_MISSING]`, `[LSP_SERVERS_SUGGESTED]`.
       Context injection driven by ground truth on the machine, not by model belief. `[CASE]`
2.3.23 `[CASE]` Its defensive shape: `set +e` at the top and `exit 0` at the bottom — an advisory
       hook must never break the session; timeouts and `GIT_HTTP_LOW_SPEED_*` on the network
       call; a `sha256sum`-vs-`shasum` fallback; `LC_ALL=C` so glob collation cannot vary by
       machine. `[CASE]`
2.3.24 `[CASE]` A **content hash instead of a version constant**: the bootstrap nudge hashes
       `SKILL.md` + every `bootstrap-*.sh` and compares against `.claude/.bootstrap-version`, so
       nothing needs bumping when a step is edited — and the writer and the checker must hash the
       identical file set in the identical order or every run nudges spuriously. `[CASE]`
2.3.25 `[INCIDENT]` The removed auto-reindex. This `SessionStart` hook used to pull two handbook
       clones and delta-reindex a RAG store on every session start with **no cross-session
       coordination**. Observed: every concurrent session independently decided a reindex was due,
       hundreds of concurrent embedder processes, **100+ GB** of abandoned partial indexes,
       machines unusable, and no recovery — *because starting a session was the trigger for the
       next pile-up.* State the general law: anything expensive or stateful in a `SessionStart`
       hook needs a lock or must not be there. `[INCIDENT]` `[CASE]` `[NUM]`
2.3.26 `[CASE]` `prod-guard-bash.sh` / `prod-guard-lib.sh` / `prod-guard-session-start.sh` as the
       blocking-guard pattern: a `PreToolUse` non-zero exit is the only guard the model cannot
       talk its way past. `[CASE]`
2.3.27 `[BUILD]` Write three hooks and prove each: a `PostToolUse` formatter on `Edit|Write`; a
       `PreToolUse` deny on a destructive command with a JSON `permissionDecision`; a
       `SessionStart` that injects the current branch and open-PR count. `[BUILD]` `[PROVE]`
2.3.28 `[TRAP]` A hook that reads state the model can change, or that assumes a single session, or
       that writes to a shared path without a lock. Three symptoms and three fixes. `[TRAP]`

*(33 leaves)*

### §2.4 MCP — connecting external systems

2.4.1 What MCP (Model Context Protocol) is, from zero: a standard way for a separate process to
      expose tools, resources and prompts to an agent. Why a standard beats N bespoke integrations.
      `[ZERO]`
2.4.2 Transport shapes: stdio (local subprocess), HTTP/SSE (remote). What each implies for
      auth and failure. `[DOC]`
2.4.3 Where servers are registered and the scopes: user, project `.mcp.json`, local, plugin
      `.mcp.json`. `claude mcp add/list/remove`, `claude mcp login/logout`. `[DOC]`
2.4.4 Project-server approval and workspace trust; `enableAllProjectMcpServers`,
      `enabledMcpjsonServers`, `disabledMcpjsonServers`. `[DOC]`
2.4.5 `[TRAP]` `enabledMcpjsonServers` gates only servers declared in a project `.mcp.json` — it
      says nothing about user-scope registrations. Reading it to answer "which server is active"
      gives the wrong answer. This is a documented real mistake in the harness's own hook.
      `[TRAP]` `[CASE]`
2.4.6 Tool naming: `mcp__<server>__<tool>`; how it appears in permission rules, hook matchers and
      the tool list. `[DOC]`
2.4.7 The cost of a connected server: every tool's schema is context. A chatty server is a
      permanent tax on every turn. Measure it with `/context`. `[NUM]` `[PROVE]`
2.4.8 Failure modes, including the one in this very session: a configured server that fails to
      connect is a *connection* failure, not a missing capability, and the correct action is to
      report it, not to conclude the feature does not exist. `[TRAP]`
2.4.9 Governance keys: `allowedMcpServers`, `deniedMcpServers`, `allowManagedMcpServersOnly`,
      `disableClaudeAiConnectors`, `allowAllClaudeAiMcps`, `--strict-mcp-config`. `[DOC]`
2.4.10 `--mcp-config` for per-run servers; `requiresUserInteraction` on a tool; elicitation and
       the `Elicitation`/`ElicitationResult` hooks. `[DOC]`
2.4.11 **LSP as the cheaper cousin**: `.lsp.json`, a language server, and precise symbol lookups
       instead of reading and grepping whole files. The argument is token cost, not correctness.
       `[DOC]`
2.4.12 `[CASE]` The harness enables three official LSP plugins (`pyright-lsp`, `typescript-lsp`,
       `jdtls-lsp`) and its `check-init.sh` nudges every session when the binaries are missing —
       explicitly framed as "cutting token usage on code-heavy tasks. Optional." `[CASE]`
2.4.13 `[BUILD]` Register one MCP server, measure `/context` before and after, then write a deny
       rule that blocks its write tools. `[BUILD]` `[PROVE]`

*(13 leaves)*

### §2.5 Plugins and marketplaces

2.5.1 What a plugin is: a self-contained directory of skills, agents, hooks, MCP/LSP configs,
      monitors, `bin/` and default settings, installable and versioned. `[ZERO]` `[DOC]`
2.5.2 Standalone `.claude/` vs plugin — the real trade: iteration speed vs distribution,
      versioning and namespacing. Start standalone, convert when you share. `[DOC]`
2.5.3 The directory layout, every component: `.claude-plugin/plugin.json`, `skills/`, `commands/`,
      `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`,
      `settings.json`. `[DOC]`
2.5.4 `[TRAP]` **Only `plugin.json` goes inside `.claude-plugin/`.** Putting `skills/` or `agents/`
      in there silently ships nothing. And the plugin root is the plugin's own directory — never
      `~/.claude/`. `[TRAP]` `[DOC]`
2.5.5 `plugin.json` fields: `name` (also the skill namespace), `description`, `version`, `author`,
      `homepage`, `repository`, `license`, `dependencies`, `settings`. `[DOC]`
2.5.6 Version management: users receive updates only when `version` is bumped (command sources
      excepted); what happens when it is omitted. `[DOC]`
2.5.7 Namespacing: plugin skills are always `/<plugin>:<skill>`; plugin agents are
      `@agent-<plugin>:<name>`; project and user `agents/` **override** a same-named plugin agent,
      while plugin skills coexist rather than override. `[DOC]` `[TRAP]`
2.5.8 A plugin's `settings.json` supports only `agent` and `subagentStatusLine` today — enough for
      a plugin to change the default persona of the whole session. `[DOC]`
2.5.9 Marketplaces: `.claude-plugin/marketplace.json` with `$schema`, `name`, `description`,
      `owner`, `plugins[]`, and `allowCrossMarketplaceDependenciesOn`. `[DOC]`
2.5.10 Cross-marketplace dependencies: Claude Code **refuses to auto-add a marketplace the user
       has not explicitly trusted**, so onboarding must instruct adding both. `[DOC]`
2.5.11 `[TRAP]` An unresolved plugin dependency is nearly silent — a cryptic `/reload-plugins`
       error. `claude plugin list --json` exposes a per-plugin `errors` array; check it. `[TRAP]`
       `[DOC]`
2.5.12 The commands: `/plugin`, `/plugin marketplace add`, `/plugin install`, `/reload-plugins`,
       `claude plugin init|validate|list`, `--plugin-dir` (directory or `.zip`), `--plugin-url`.
       `[DOC]`
2.5.13 Skills-directory plugins via `claude plugin init` — a plugin that auto-loads from
       `~/.claude/skills/` with no marketplace. `[DOC]` `[VERSION]`
2.5.14 Governance: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`,
       `strictKnownMarketplaces`, `strictPluginOnlyCustomization` (and its `.agents`, `.hooks`,
       `.mcp`, `.skills` sub-keys), `disableSideloadFlags`, `pluginTrustMessage`. `[DOC]`
2.5.15 `strictPluginOnlyCustomization` as the enterprise endgame: block skills, agents, hooks and
       MCP from user and project sources so **only reviewed, versioned plugins can extend the
       agent.** Why an org reaches for it. `[DOC]`
2.5.16 `[CASE]` The harness's `marketplace.json`: `allowCrossMarketplaceDependenciesOn:
       ["ig-superclaude"]` and a description that explains *why* the pivot to a standalone
       marketplace happened, citing its own RFC. Documentation living in the config. `[CASE]`
2.5.17 `[CASE]` Its `plugin.json`: `version: 0.10.2`, proprietary licence,
       `dependencies: [{ name: "ig-superclaude", marketplace: "ig-superclaude" }]`. `[CASE]`
2.5.18 `[TRAP]` `${CLAUDE_PLUGIN_ROOT}` is the plugin's **install/cache** directory, not the repo.
       A hook ported from `<repo>/.claude/hooks/` cannot keep resolving the repo root as
       `dirname "$0"/../..`. Path assumptions are the number-one porting bug. `[TRAP]` `[CASE]`
2.5.19 `[CASE]` The harness's fix and its discipline: resolve `HARNESS_ROOT` → `git rev-parse
       --show-toplevel`, and **refuse with a clear message** rather than inventing a third
       fallback. Quote the header comment that says exactly that. `[CASE]`
2.5.20 `[BUILD]` Convert a `.claude/` folder into a plugin: manifest, move the components, migrate
       settings hooks into `hooks/hooks.json`, test with `--plugin-dir`, `claude plugin validate`,
       then delete the originals so the plugin copies actually take effect. `[BUILD]`

*(20 leaves)*

### §2.6 Context economy in practice

2.6.1 Read a real `/context` line by line and attribute every token: system prompt, tool schemas,
      memory files, skill listing, MCP schemas, conversation, free space. `[PROVE]` `[BUILD]`
2.6.2 The startup tax, itemised with numbers for the reader's own machine. `[NUM]` `[PROVE]`
2.6.3 The four biggest avoidable costs, ranked: unbounded command output, whole-file reads where a
      symbol lookup would do, a bloated always-on `CLAUDE.md`, and chatty MCP servers. `[NUM]`
2.6.4 Bounding tool output as a discipline: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over
      `cat`, `git diff --stat` before `git diff`. `[BUILD]`
2.6.5 **Autocompaction**: `autoCompactEnabled`, `autoCompactWindow`, `--autocompact`,
      `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. What compaction actually is — a summary replacing the
      transcript. `[DOC]`
2.6.6 What survives compaction, exhaustively: project-root `CLAUDE.md` re-read from disk;
      most-recent skill invocations within the 5,000/25,000-token budget; nothing else that lived
      only in conversation. `[DOC]` `[NUM]`
2.6.7 `PreCompact` / `PostCompact` hooks as the seam to persist state across a compaction. `[DOC]`
2.6.8 `/compact` vs `/clear` vs a fresh session vs `--fork-session`: four different reset
      semantics. `[NUM]`
2.6.9 The prompt-cache economics of session shape: append-only conversations stay cached; anything
      that changes the prefix does not. Why a 5-minute idle gap has a price. `[NUM]` `[PROVE]`
2.6.10 Isolation as the primary lever, restated with arithmetic: burn 150K in a subagent, return
       200 words. Compare against doing the same work inline. `[PROVE]` `[NUM]`
2.6.11 A working session protocol for this reader: `/context` at start, compact at a task
       boundary, `/clear` per feature, subagent for anything verbose, one file per lane. `[BUILD]`
2.6.12 `[TRAP]` Compacting mid-task instead of at a boundary. The summary keeps the narrative and
       drops the specifics you were about to use. `[TRAP]`

*(12 leaves)*

### §2.7 Working with the tool: the practices that change outcomes

2.7.1 Plan mode as a first-class step: read-only exploration, a reviewable plan, then execute.
      `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode`, `plansDirectory`. `[DOC]`
2.7.2 Why a plan improves a large change more than a better prompt does: it moves the expensive
      correction from *after* the diff to *before* it. `[PROVE]`
2.7.3 Test-first with an agent: a failing test is a machine-checkable specification, which is
      exactly what a confabulating writer needs. `[JAVA]`
2.7.4 Small diffs and reviewability: why the same argument that makes small PRs better makes small
      agent tasks better. `[X-REF 17]`
2.7.5 Prompting that matters and prompting that does not: state the goal, the constraints, the
      done-condition, and where the answer goes. Skip politeness, role-play and threats. `[TRAP]`
2.7.6 Give the agent the same context a new teammate would need: the file, the convention, the
      command to verify. Under-specifying is the top cause of a plausible-but-wrong result.
2.7.7 The verification habit: never accept a claim of success without an artefact — a test run, a
      compile, a transcript, a diff.
2.7.8 `/code-review`, `/security-review` and self-review as a second pass with a fresh context;
      why a reviewer that shares the writer's context shares its blind spots. `[DOC]`
2.7.9 Where an agent is a bad fit: a one-line change you already understand, anything needing
      taste you cannot express, and anything whose verification costs more than the work.
2.7.10 `[JAVA]` A worked Java example end to end: add an idempotency key to a Spring Boot endpoint
       — plan, failing test, implementation, review, and the two places the agent got it wrong and
       how the test caught it. `[JAVA]` `[PROVE]`
2.7.11 `statusLine` / `subagentStatusLine`: cheap situational awareness — model, branch, cost,
       context used. `[DOC]` `[BUILD]`
2.7.12 Keybindings and `~/.claude/keybindings.json` in one paragraph. `[DOC]`

*(12 leaves)*

### §2.8 Deterministic vs agentic — the central engineering judgment

2.8.1 The rule, stated once and referenced forever: **if the inputs determine one correct answer,
      write a script; if the task needs judgment, write a prompt.** `[CASE]`
2.8.2 `[CASE]` The source of that rule in the harness's `bootstrap` skill, quoted verbatim:
      "resolving paths, merging JSON, and creating symlinks all have a single correct answer given
      the inputs — there is no ambiguity for a model to resolve." `[CASE]`
2.8.3 `[CASE]` The consequence in the same file: the skill is "an **orchestrator, not a rewrite**",
      every step delegates to a tested `bootstrap-*.sh`, and the assistant is explicitly forbidden
      from re-deriving the logic inline on each run. `[CASE]`
2.8.4 The decision table: one-correct-answer → script; judgment/synthesis → prompt; must-happen →
      hook; verbose-in/small-out → subagent; needs human authority → confirmation gate with the
      tool denied. `[NUM]`
2.8.5 Why "the model could do it" is not an argument for letting it: cost, variance, and the fact
      that a script is testable and a prompt is not. `[PROVE]`
2.8.6 Idempotence as the property that makes a bootstrap safe to re-run, and why every step in the
      harness's is written that way. `[CASE]`
2.8.7 `[CASE]` The one documented exception and its reasoning: `bootstrap-uv.sh` self-installs a
      package manager because without `uv` no playbook can pass its first stage, so "a bootstrap
      that leaves the engineer to separately find and run a curl-to-shell command isn't actually a
      single-command setup". An exception stated with its justification is not an inconsistency.
      `[CASE]`
2.8.8 Human-authority gates: the calibrator mines and groups, and a human confirms and files.
      Deny the tool; do not instruct the agent to abstain. `[CASE]`
2.8.9 `[TRAP]` Prompting for determinism. Symptoms: a step that works four times in five, and a
      failure mode nobody can reproduce. `[TRAP]`

*(9 leaves)*

### §2.9 Governance, security and the org view

2.9.1 The threat model in plain terms: the agent runs with your credentials, reads what you can
      read, and follows text it finds. Enumerate what that permits. `[ZERO]` `[X-REF 13]`
2.9.2 **Prompt injection**: instructions embedded in a file, a web page, an issue comment or a
      tool result. Why "just tell it to ignore instructions in data" is not a control. `[TRAP]`
      `[X-REF 13]`
2.9.3 The controls that actually hold: deny rules, `PreToolUse` blocking hooks, sandboxing,
      least-privilege tool sets, and human confirmation on outward-facing actions. `[NUM]`
2.9.4 Secrets: `Read` deny rules for `.env` and `secrets/**`, sandbox credential masking
      (`sandbox.credentials.{envVars,files,sigv4,awsPairs}`), and why an agent transcript is a
      data-exfiltration surface. `[DOC]`
2.9.5 What leaves the machine, and the settings that govern it: `cleanupPeriodDays`,
      `skipWebFetchPreflight`, telemetry/OTel keys, `env`. `[DOC]`
2.9.6 Managed settings delivery: `managed-settings.json`, MDM, server-managed settings from the
      console; `managedSourcesBehavior`, `policyHelper` (`path`, `refreshIntervalMs`, `timeoutMs`),
      `forceRemoteSettingsRefresh`. `[DOC]`
2.9.7 The `allowManaged*Only` family as the "developers cannot re-open this" lock:
      `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`,
      `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`.
      `[DOC]`
2.9.8 Login and version control at org scale: `forceLoginMethod`, `forceLoginOrgUUID`,
      `availableModels`, `enforceAvailableModels`, `requiredMinimumVersion`,
      `requiredMaximumVersion`, `autoUpdatesChannel`. `[DOC]`
2.9.9 Attribution and audit: `attribution.{commit,pr,sessionUrl}`, `includeGitInstructions`,
      `prUrlTemplate`. Why "which commits came from an agent" is a question you will be asked.
      `[DOC]`
2.9.10 `[CASE]` The harness's own posture, assembled from its files: a fail-closed prod-AWS
       deny-list provisioned at user scope by `bootstrap-user-scope.sh`, `prod-guard-*` hooks,
       read-only triage scripts (`triage-aws-ro.sh`), and a Jira tool withheld from the agent that
       would otherwise use it. `[CASE]`
2.9.11 The rollout argument a Staff engineer has to make: capability as a **versioned,
       dependency-managed plugin with hooks and eval suites**, not tips in a wiki. What that buys
       — review, rollback, measurement — and what it costs. `[CASE]`

*(11 leaves)*

---

**PART 2 total: 142 leaves**

---

## PART 3 — UNDER THE HOOD

### §3.1 What is actually in the request

3.1.1 The assembled request, in order: system prompt (built-in + appended), tool schemas, memory
      files as a user message, environment/git snapshot, skill listing, then the conversation.
      `[DOC]` `[PROVE]`
3.1.2 `[TRAP]` `CLAUDE.md` is delivered **as a user message after the system prompt**, not as part
      of the system prompt. That is why it is guidance and not policy, and why
      `--append-system-prompt` behaves differently. `[TRAP]` `[DOC]`
3.1.3 The cached prefix and why the ordering above is not arbitrary: everything stable goes first
      so it can be reused. `--exclude-dynamic-system-prompt-sections` exists to protect this.
      `[NUM]` `[DOC]`
3.1.4 Tool schemas as a cost line: how many tokens the default set is, what an MCP server adds,
      and what deferred tools plus `ToolSearch` save. `[NUM]` `[PROVE]`
3.1.5 The skill listing: `description` + `when_to_use` per skill, capped at 1,536 characters each,
      inside a budget fraction of the window. Compute the cost of 50 skills. `[NUM]` `[PROVE]`
3.1.6 System-reminder blocks: how the harness injects mid-conversation state (file-state notes,
      recalled memories, hook output) and why that text is context rather than instruction.
3.1.7 Reading a real transcript: the JSONL under `~/.claude/projects/<project>/<session>/`, its
      message shapes, and how to count tokens per turn from it. `[BUILD]` `[PROVE]`
3.1.8 `[CASE]` The harness's `telemetry/transcript.py` reads exactly these transcripts to mine
      friction signals. Provenance for the whole calibration loop. `[CASE]`

*(8 leaves)*

### §3.2 Compaction, mechanically

3.2.1 What compaction does: summarise the transcript, then continue with the summary in place of
      the messages. `[DOC]`
3.2.2 The threshold and how it is configured; what "75%" means against which number. `[NUM]`
3.2.3 The re-attachment algorithm for skills: most recent invocation of each, first 5,000 tokens
      each, 25,000 combined, filled newest-first — so invoking many skills silently evicts the
      earliest. `[DOC]` `[NUM]` `[PROVE]`
3.2.4 `CLAUDE.md` re-read from disk after compaction; nested files and path-scoped rules reload
      only on re-match. `[DOC]`
3.2.5 What is irrecoverably lost, and the fix: put it in a file, not in a message. `[TRAP]`
3.2.6 `PreCompact`/`PostCompact` as the persistence seam; a worked handoff-note hook. `[BUILD]`
3.2.7 Why a fresh session usually beats a thrice-compacted one, argued rather than asserted.
      `[PROVE]`

*(7 leaves)*

### §3.3 Permission evaluation, step by step

3.3.1 The full pipeline for one tool call: managed → CLI → local → project → user rule collection,
      then deny → ask → allow, then `PreToolUse` hooks, then the mode's default, then the prompt.
      Draw it. `[DOC]` `[PROVE]`
3.3.2 Where a `PreToolUse` hook sits relative to the rules, and why a hook cannot unblock a deny.
      `[DOC]`
3.3.3 Bash matching in detail: separator splitting, wrapper stripping, env-assignment stripping,
      then per-subcommand matching. Trace three commands through it. `[PROVE]`
3.3.4 The read-only command fast path, and the two cases that leave it (write-capable flags with
      unquoted globs, redirects). `[DOC]`
3.3.5 Read/Edit gitignore-pattern matching, including single-segment directory patterns whose
      depth depends on the rule type. `[DOC]` `[PROVE]`
3.3.6 Which tools consult path rules at all, and the startup warnings for the ones that do not.
      `[DOC]`
3.3.7 Where enforcement ends and the OS begins: a subprocess that opens a file itself, and the
      sandbox as the only answer. `[DOC]` `[TRAP]`
3.3.8 `[PROVE]` Adversarial exercise: given a settings file, decide for ten commands whether each
      runs, prompts or is blocked — then verify each against the real tool. `[PROVE]` `[BUILD]`

*(8 leaves)*

### §3.4 The cost model

3.4.1 What you are billed for: input tokens, output tokens, cache writes, cache reads. Four
      different prices. `[NUM]` `[RESEARCH]`
3.4.2 Per-model pricing and the ratio between tiers, as of the write date. `[NUM]` `[RESEARCH]`
3.4.3 Why conversation length dominates: the same prefix re-sent every turn, times turns. Work a
      full session's arithmetic. `[PROVE]` `[NUM]`
3.4.4 What caching changes, and the 5-minute default TTL as the reason a paused session costs
      more when resumed. `[NUM]`
3.4.5 Where a subagent's ~2× comes from, itemised. `[PROVE]` `[NUM]`
3.4.6 The three ceilings and their different failure shapes: `--max-turns` (agency),
      `--max-budget-usd` (money), subprocess timeout (wall clock). `[NUM]`
3.4.7 Reading cost out of a run: the `-p --output-format json` envelope's cost and token fields;
      `/cost`; `modelPricing` for contracted rates. `[DOC]` `[BUILD]`
3.4.8 `[PROVE]` Measure it: run one task inline and the same task via a subagent, and report both
      envelopes. `[PROVE]` `[BUILD]`
3.4.9 The judgment this all supports: an unbounded agent loop is an unbounded invoice, so ceilings
      are reliability engineering, not thrift. `[CASE]`

*(9 leaves)*

### §3.5 Effort, models and routing

3.5.1 Effort levels `low|medium|high|xhigh|max`: what they change, `/effort`, `effortLevel`,
      `--effort`, `CLAUDE_EFFORT`, `${CLAUDE_EFFORT}`. `[DOC]`
3.5.2 Per-skill and per-agent `effort` and `model` overrides, and their lifetime (the turn, not the
      session). `[DOC]`
3.5.3 Routing as a cost decision, with a table: exploration/search → haiku; implementation →
      sonnet; architecture and gnarly debugging → opus. State the escalation path. `[NUM]`
3.5.4 `fallbackModel`, `--fallback-model`, `switchModelsOnFlag`, `advisorModel`, `modelOverrides`
      for Bedrock/Vertex ARNs, `modelPicker`. `[DOC]`
3.5.5 `fastMode` / `/fast` — faster output on the same Opus model, not a downgrade. `[DOC]`
      `[TRAP]`
3.5.6 `[TRAP]` Routing everything to the cheapest model. Where haiku fails, with a concrete
      example of a wrong result that cost more than the saving. `[TRAP]` `[PROVE]`

*(6 leaves)*

### §3.6 Headless mode — the programmable surface

3.6.1 `claude -p "<task>"` — one prompt in, one envelope out. The whole basis of automation.
      `[DOC]`
3.6.2 `--output-format text|json|stream-json` and `--input-format text|stream-json`. What each is
      for. `[DOC]`
3.6.3 The JSON envelope's fields: result text, `is_error`, `session_id`, cost, token counts,
      duration. Show a real one. `[DOC]` `[PROVE]`
3.6.4 `stream-json` and `--include-partial-messages`, `--include-hook-events`,
      `--forward-subagent-text`, `--replay-user-messages`. When streaming is worth the complexity.
      `[DOC]`
3.6.5 `--json-schema` for schema-validated output — the difference between parsing prose and
      receiving data. `[DOC]` `[VERSION]`
3.6.6 The flag set a production wrapper needs, as a checklist: `--agent`, `--output-format`,
      `--max-turns`, `--permission-mode`, `--setting-sources`, `--settings`, `--model`, `--effort`,
      `--add-dir`, `--append-system-prompt`, `--resume`, `--max-budget-usd`, `--session-id`,
      `--no-session-persistence`, `--allowed-tools`, `--disallowed-tools`, `--mcp-config`,
      `--verbose`. `[DOC]`
3.6.7 Session control in automation: `--session-id` (must be a UUID), `--fork-session`,
      `--continue`, `--resume`, `--no-session-persistence`. `[DOC]`
3.6.8 `claude setup-token` for CI; what an unattended run must *not* have. `[DOC]`
3.6.9 Background and remote execution: `--bg`, `claude attach|logs|stop|respawn|rm`,
      `claude daemon status`, `--cloud`, `--environment`, `--teleport`. One paragraph each.
      `[DOC]`
3.6.10 Failure taxonomy for a wrapper, three classes handled differently: launch/timeout
       (infrastructure), unparseable envelope (contract), `is_error: true` (the agent failed).
       `[CASE]`
3.6.11 `[CASE]` `extract_json_envelope()` preserves a **500-character snippet** of what the
       subprocess actually printed when parsing fails — because a zero-cost envelope failure was
       previously "only diagnosable by reproducing it interactively (2026-07-30 calibration
       finding)". General law: **when you parse a subprocess's output, capture the unparseable
       input.** `[CASE]` `[NUM]` `[INCIDENT]`
3.6.12 `[CASE]` The retry loop keeps the **last parsed error envelope** so cost and token counts
       survive a failure. Why discarding them makes the run unbillable and unauditable. `[CASE]`
3.6.13 `[CASE]` The harness's resolution order for every knob — explicit parameter → environment
       variable → module default — checked with `is not None` so an explicit `0` is not silently
       treated as omitted. Copy this pattern. `[CASE]` `[JAVA]`
3.6.14 `[CASE]` `DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`,
       `DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160`. Each number with its reason. `[CASE]`
       `[NUM]`
3.6.15 `[INCIDENT]` Why `DEFAULT_MAX_TURNS` is 160 and not 40. Raised 40 → 80 → 160; the 2026-08-10
       dogfood run produced **13 green tests and a correct fix but exhausted 80 turns before
       reaching a commit — $5.16 for zero landed work.** A fresh story's first leg is
       disproportionately reads and exploration, not a runaway. The comment records it as "an
       explicit engineer call to trade cost for dev experience, not a measured-data derivation" —
       an honest constant. `[INCIDENT]` `[CASE]` `[NUM]`
3.6.16 `[CASE]` Both ceilings overridable by environment (`HARNESS_AGENT_MAX_TURNS`,
       `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`,
       `HARNESS_AGENT_SETTINGS`) so tuning never requires a code change. `[CASE]`
3.6.17 `[CASE]` `--resume <session_id>` as the continuation mechanism, and the rule that the coder
       resumes its own leg while the verifier **never** does — it judges artifacts. Why mixing the
       two destroys the verdict's reproducibility. `[CASE]`
3.6.18 `[CASE]` `--add-dir` deliberately unused in the code-to-commit loop: agents write only
       inside the worktree and reports ride the envelope. A seam kept open, not used by default.
       `[CASE]`

*(18 leaves)*

### §3.7 The `--setting-sources` incident — a full root-cause walkthrough

3.7.1 The setup: the harness runs each coder in an **isolated per-story git worktree**, so `cwd` is
      the worktree, not the harness repo. `[CASE]` `[INCIDENT]`
3.7.2 The mechanism: `--setting-sources project` resolves `<cwd>/.claude/settings.json`. `[DOC]`
3.7.3 The consequence: the harness's own `permissions.allow` (`Bash(*)`) **and** its
      destructive-command deny-list never loaded. `[CASE]`
3.7.4 The observed symptom, precisely: the agent could read, edit, `mkdir`, `touch`, `mv`, `cp`,
      `sed` — the bare `acceptEdits` defaults — but **not** `mvn`, `git commit`, `chmod` or
      `java`. A competent agent mysteriously unable to build. `[CASE]` `[NUM]`
3.7.5 The fix: `--settings <absolute path>`, which is evaluated independently of `cwd`. `[CASE]`
3.7.6 The paper trail: `docs/adr/0016` and the AP-11470 incident, cited in the code itself.
      Decisions that carry their incident reference are the ones nobody re-litigates. `[CASE]`
3.7.7 Lesson one, generalised: **configuration discovered by directory walk breaks the moment you
      change directories.** Name three other systems where this bites. `[PROVE]`
3.7.8 Lesson two: **a permission model that silently degrades to defaults is worse than one that
      fails loudly.** What a loud failure would have looked like here. `[PROVE]`
3.7.9 Why this is the best interview story in the guide, and how to tell it in 90 seconds:
      symptom → mechanism → fix → generalisation. `[BUILD]`

*(9 leaves)*

### §3.8 The Agent SDK and the API underneath

3.8.1 The three levels of building on Claude: the CLI in `-p` mode, the Agent SDK
      (TypeScript/Python), and the raw Messages API with your own loop. What each gives up. `[DOC]`
3.8.2 The Messages API shape: `model`, `system`, `messages[]`, `tools[]`, `max_tokens`, streaming.
      Enough to read one. `[DOC]` `[RESEARCH]`
3.8.3 Tool use at the API level: `tool_use` and `tool_result` blocks, and writing the loop
      yourself. `[DOC]`
3.8.4 Prompt caching at the API level: cache breakpoints and what they cost. `[DOC]` `[NUM]`
3.8.5 Agent SDK specifics worth knowing: `resolveSettings()`, `managedSettings`,
      `parentSettingsBehavior`, and that an SDK session counts as trusted. `[DOC]`
3.8.6 Why the harness chose subprocesses over the SDK, and what that trade buys (process
      isolation, the same binary engineers use interactively, no SDK version coupling). `[CASE]`
3.8.7 `[JAVA]` The Java view: there is no first-party Java SDK, so the two honest options are the
      HTTP API via a JDK 21 `HttpClient`, or `ProcessBuilder` around the CLI. Sketch both. `[JAVA]`
3.8.8 `[X-REF 12]` Treating an agent call as a remote dependency: timeouts, retries with backoff,
      idempotency, a circuit breaker, and a bulkhead on concurrency. The reader already knows this
      material; the point is that it applies unchanged. `[X-REF 12]` `[JAVA]`

*(8 leaves)*

### §3.9 Orchestration patterns

3.9.1 The vocabulary, defined: single session, subagent, fan-out, pipeline, team, workflow. `[ZERO]`
3.9.2 Fan-out with a join: N independent tasks, one aggregation, and the file-boundary requirement
      that makes it safe. `[NUM]`
3.9.3 Pipeline: stage N's output is stage N+1's input, each stage independently re-runnable
      **because no stage writes to its own input.** `[CASE]`
3.9.4 `[CASE]` This repository's own per-topic pipeline as the worked example:
      `topic-enhancer-agent` → `prompt-builder` → `notes-generator` → `gaps-analyzer-agent` →
      `understanding-book-keeper`, with the rule "never write across lanes" and a hard stop when a
      prerequisite is missing. `[CASE]`
3.9.5 `[CASE]` The harness's playbooks (`full-sdlc`, `plan-project`, `implement-story`,
      `implement-story-lite`, `post-deploy-smoke`) and the split between a **prose executor**
      (`/run-harness`) and a **deterministic conductor** (`/run-conductor`) — two executors, not
      interchangeable, with the routing decision returned by `conductor advance` from folded run
      state rather than inferred by a model. `[CASE]`
3.9.6 `[CASE]` Folded state in `features/<slug>/state/harness.db` as the source of truth for
      "which stage are we at", and why a `--resume-at <stage>` flag was **rejected** rather than
      approximated. Rejecting a flag with a stated reason beats silently ignoring it. `[CASE]`
3.9.7 Judges and rubrics: `progress-verifier` scoring against
      `control-plane/judge-rubrics/progress-verifier.yaml` and emitting one verdict line. Why the
      rubric is a versioned file. `[CASE]`
3.9.8 Continuation checkpoints: what to do when an agent exhausts its turns mid-task, and the
      progressing-vs-stalled decision. `[CASE]`
3.9.9 The calibration loop: mine session transcripts for recurring friction, group it, and file it
      as work with human confirmation. Treating agent failures as a **measurable defect stream**,
      not anecdotes. `severity_map.yaml`, `feedback-signal.yaml`'s `failure_code` vocabulary, the
      `filed-bugs.yaml` dedup ledger. `[CASE]`
3.9.10 Evals: `harness/evals/seeded-defects` and `harness/evals/code-to-commit` — how you find out
       whether a change to a prompt made things better. `claude plugin eval`. `[CASE]` `[DOC]`
3.9.11 `[TRAP]` Over-orchestration. Symptoms: more agents than the task warrants, a pipeline whose
       coordination costs more than its work, and a fan-out where the join is the bottleneck.
       `[TRAP]`
3.9.12 `[NUM]` Concurrency limits that are real, not stylistic: 20 concurrent subagents, depth 3,
       and the practical ceiling imposed by review capacity. `[NUM]`

*(12 leaves)*

### §3.10 Verification — the AI-specific failure mode

3.10.1 The core asymmetry: an agent produces **plausible** artefacts, and skimming a diff is the
       review method worst matched to plausibility. `[ZERO]`
3.10.2 Law: **re-run every published artefact in its published form.** In this repository that
       found more defects than every structural check combined — code that no longer produced the
       transcript printed beneath it, invented values that compiled fine, a repro returning the
       opposite of its claim, and run-specific numbers published as constants. `[INCIDENT]`
       `[PROVE]`
3.10.3 Law: **a checker whose input can switch it off is worse than no checker.** The NUL-byte
       incident — one generated file contained a literal NUL, `file` classified it as `data`, grep
       returned *nothing* (not a mismatch), every text check silently skipped it and reported
       success. Assert text-ness before any grep-based gate. `[INCIDENT]` `[PROVE]`
3.10.4 Law: **certify from final state, never from a pre-write computation.** A footer regex ending
       `\s*$` ate nine files' trailing newlines; an md5 was taken over a patched harness while the
       shipped files still failed to compile. `[INCIDENT]`
3.10.5 Law: **a build proof must pin its harness beside the digest.** Two honest runs over
       identical files produced different md5s purely because one wrapped a throwing snippet. A
       bare digest is unfalsifiable. `[INCIDENT]`
3.10.6 Law: **never let a status row point at a missing path.** The costliest bookkeeping failure
       here, and the one-line gate that prevents it. `[INCIDENT]`
3.10.7 Law: **a closed lane is not a verified lane.** Two cross-lane contradictions were found
       after their owners had stood down; only a pass that reads across boundaries finds these.
       `[INCIDENT]`
3.10.8 Executable evidence over structural evidence: a compile, a test, a transcript beats a regex
       over a file. Rank the evidence types. `[NUM]`
3.10.9 Automating the gates: `PostToolUse` formatters and linters, a `Stop` hook that refuses to
       finish on a red build, and CI as the outer loop. `[BUILD]`
3.10.10 `[TRAP]` Command shapes that defeat a permission matcher and therefore your own gates:
        heredocs, `&&`/`;` chains, `$(...)`. Use one command per call, absolute paths, and the
        Write tool for scratch files. `[TRAP]` `[CASE]`
3.10.11 Review capacity as the real ceiling on agent throughput, argued with numbers. `[PROVE]`
        `[NUM]`

*(11 leaves)*

---

**PART 3 total: 96 leaves**

---

## PART 4 — BUILD IT

Every item is `[BUILD]`: a complete, working artefact the reader creates and then **proves** works,
followed by a **"what this costs"** note stating its token or dollar impact. No fragment, no
"…and so on". Where a real equivalent exists in the sdlc-harness, the item ends with a
**Diff vs the real one** table.

### §4.1 A `.claude` folder from nothing

4.1.1 A `CLAUDE.md` under 100 lines for a real Spring Boot service: build command, test command,
      layout, three conventions, two things Claude gets wrong here. `[BUILD]` `[JAVA]`
4.1.2 Split it: move the always-true facts to `CLAUDE.md`, one procedure to a skill, and one
      file-type convention to a `paths`-scoped rule in `.claude/rules/`. Measure `/context`
      before and after. `[BUILD]` `[PROVE]`
4.1.3 A `settings.json`: permissions for the real build/test commands, deny for `git push`, `.env`
      and `secrets/**`, `env` for one variable, `model` and `effortLevel`. `[BUILD]`
4.1.4 A `settings.local.json` that overrides exactly one key, and proof that it wins. `[BUILD]`
      `[PROVE]`
4.1.5 Commit it, then verify a fresh clone behaves identically — including the workspace-trust
      step. `[BUILD]` `[PROVE]`

*(5 leaves)*

### §4.2 Three hooks

4.2.1 `PostToolUse` on `Edit|Write`: run the formatter on the changed file only, using `jq` over
      stdin to get `tool_input.file_path`. `[BUILD]`
4.2.2 `PreToolUse` on `Bash`: block a destructive command with a JSON `permissionDecision: "deny"`
      and a reason the model can act on; then the exit-2 variant, and a comparison. `[BUILD]`
      `[PROVE]`
4.2.3 `SessionStart`: inject branch, dirty-file count and failing-test count as tagged advisory
      lines. `set +e`, `exit 0`, a timeout on anything network-bound. `[BUILD]`
4.2.4 `Stop`: refuse to end the turn while the build is red, using `decision: "block"` with a
      required `reason` (**not** `continue: true`, which does not exist — see 2.3.15a). Then build
      the `additionalContext` variant and contrast the two transcripts. Then explain why this is
      dangerous if the build takes four minutes, and how `stop_hook_active` plus the
      8-continuation cap bound the damage. `[BUILD]` `[TRAP]` `[NUM]`
4.2.5 Prove all four fired: `/hooks`, the debug log, and an intentional violation each. `[BUILD]`
      `[PROVE]`
4.2.6 Diff vs the real one: `check-init.sh`, `doc-update-reminder.sh`, `prod-guard-bash.sh` —
      concurrency safety, path resolution, tool fallbacks, locale pinning, failure posture.

*(6 leaves)*

### §4.3 A skill and a command

4.3.1 A skill with frontmatter, `$ARGUMENTS`, one `` !`command` `` injection and a `references/`
      file that loads only on demand. `[BUILD]`
4.3.2 The same capability as a bare `.claude/commands/*.md` file; then state what the skill form
      bought. `[BUILD]`
4.3.3 A `disable-model-invocation: true` workflow skill, and a `user-invocable: false` knowledge
      skill. Show that each is invocable only the intended way. `[BUILD]` `[PROVE]`
4.3.4 A `paths`-gated skill that activates only for `**/*.java`. `[BUILD]` `[JAVA]` `[PROVE]`
4.3.5 A composed pair: a thin wrapper skill that inlines a shared executor with a ` ```! ` block
      and states only its overrides. `[BUILD]`
4.3.6 Diff vs the real one: `bootstrap/SKILL.md` and `/implement-story` — plan-then-confirm,
      delegation to tested scripts, rejected-flag handling.

*(6 leaves)*

### §4.4 Two subagents

4.4.1 A read-only reviewer: `tools` allowlist, `model`, a fixed output contract, and a verdict
      line. `[BUILD]`
4.4.2 A test-runner for a Maven project: `Bash(mvn test *)` only, returns failing tests and
      nothing else. Measure the context saved versus running it inline. `[BUILD]` `[JAVA]`
      `[PROVE]`
4.4.3 Give one of them `memory: project` and show what it accumulates across two sessions.
      `[BUILD]` `[PROVE]`
4.4.4 Deny an agent to itself (`tools` without `Agent`) and prove it cannot spawn. `[BUILD]`
      `[PROVE]`
4.4.5 Diff vs the real one: `progress-verifier.md` and `calibrator.md` — pointer bodies, write
      boundaries, withheld tools, artefact-only evidence.

*(5 leaves)*

### §4.5 A headless orchestrator

4.5.1 `[JAVA]` A Java 21 `ClaudeRunner`: `ProcessBuilder` around `claude -p`, `--output-format
      json`, a record for the envelope, Jackson parsing, and the unparseable-input snippet
      preserved on failure. `[BUILD]` `[JAVA]`
4.5.2 `[JAVA]` Add the three ceilings: `--max-turns`, `--max-budget-usd`, and a
      `Process.waitFor(Duration)` wall clock, each with a distinct exception type. `[BUILD]`
      `[JAVA]`
4.5.3 `[JAVA]` Add `--settings <absolute path>` and explain, in a comment, the §3.7 incident it
      prevents. `[BUILD]` `[JAVA]`
4.5.4 `[JAVA]` Add parameter → env → default resolution for every knob, checked so an explicit
      zero survives. `[BUILD]` `[JAVA]`
4.5.5 `[JAVA]` Add a bounded retry that keeps the last parsed error envelope, and a bulkhead on
      concurrency. `[BUILD]` `[JAVA]` `[X-REF 05]`
4.5.6 A two-stage pipeline over it: stage 1 writes a file, stage 2 reads it, neither writes to its
      own input. Prove stage 2 is independently re-runnable. `[BUILD]` `[PROVE]`
4.5.7 Emit a cost and token report per stage from the envelopes. `[BUILD]`
4.5.8 Diff vs the real one: `engine/agent.py` — persona loading with frontmatter stripping,
      envelope extraction, the retry loop, the resolution order, `--resume` continuation legs, and
      every default constant with its recorded reason.

*(8 leaves)*

### §4.6 A plugin

4.6.1 Package §4.2–§4.4 as a plugin: `.claude-plugin/plugin.json`, `skills/`, `agents/`,
      `hooks/hooks.json`. Test with `--plugin-dir`. `[BUILD]`
4.6.2 `claude plugin validate`, then `--strict`. Fix what it reports. `[BUILD]` `[PROVE]`
4.6.3 Publish it to a local marketplace: `.claude-plugin/marketplace.json`, `/plugin marketplace
      add`, `/plugin install`, `/reload-plugins`. `[BUILD]`
4.6.4 Bump `version` and prove an installed copy updates. `[BUILD]` `[PROVE]`
4.6.5 Add a `dependencies` entry on a second local plugin, and demonstrate both the unresolved
      state and the `claude plugin list --json` `errors` array that reveals it. `[BUILD]` `[PROVE]`
4.6.6 Diff vs the real one: the sdlc-harness plugin and marketplace — cross-marketplace
      dependency trust, `${CLAUDE_PLUGIN_ROOT}` path discipline, content-hash version nudging, and
      a bootstrap skill that provisions what a plugin cannot install declaratively.

*(6 leaves)*

### §4.7 Verification harness

4.7.1 A `verify.sh` for this repository's own notes: text-ness assertion first, then every
      structural check, then re-run every fenced listing. `[BUILD]`
4.7.2 Make one check fail deliberately and confirm it fails loudly rather than skipping. `[BUILD]`
      `[PROVE]`
4.7.3 Wire it as a `Stop` hook and as a CI job, and state which failures belong in which. `[BUILD]`
4.7.4 A skill eval: three prompts that should trigger a skill and three that should not; run and
      score them. `[BUILD]` `[PROVE]`

*(4 leaves)*

---

**PART 4 total: 40 leaves**

---

## PART 5 — INTERVIEW AND RETENTION

### §5.1 The questions, with the answer shape

5.1.1 "How do you use AI in your workflow?" — the 60-second answer that is about systems, not
      tools, and the three follow-ups it invites.
5.1.2 "What is a context window?" — the answer that includes the cost consequence, not just the
      number.
5.1.3 "Why does a long session get worse?" — compaction, prefix cost, and drift, in that order.
5.1.4 "How do you stop an agent doing something destructive?" — deny rules, `PreToolUse` blocking
      hooks, sandbox, withheld tools, human gates. Ranked by strength, and why prompting is not on
      the list.
5.1.5 "Deny beats allow — why does that matter?" — the allowlist-exception trap in one sentence.
5.1.6 "What is the difference between `CLAUDE.md`, a skill, and a hook?" — always-on context,
      on-demand context, guaranteed execution.
5.1.7 "When do you use a subagent?" — verbose-in/small-out, parallel with disjoint writes,
      different capability set. Plus the 2× cost.
5.1.8 "How would you run this in CI?" — `-p --output-format json`, the three ceilings,
      `--settings` by absolute path, `setup-token`, and what must not be present.
5.1.9 "Tell me about a bug you debugged in your tooling." — the §3.7 walkthrough in 90 seconds.
5.1.10 "How do you know the agent's output is correct?" — executable evidence, re-running published
       artefacts, and the checker-that-can-be-switched-off law.
5.1.11 "What does this cost?" — the four billed quantities, cache economics, and where the money
       actually goes in a real session.
5.1.12 "How would you roll this out to 200 engineers?" — plugin + marketplace, managed settings,
       `strictPluginOnlyCustomization`, evals, and a calibration loop. With the honest ceiling:
       review capacity.
5.1.13 "What are the risks?" — prompt injection, credential blast radius, plausible-but-wrong
       output, unbounded cost, and skill atrophy. One mitigation each.
5.1.14 "Where would you not use it?" — and why having an answer here is itself a signal.
5.1.15 The Staff framing paragraph, drafted: capability as a versioned platform, determinism where
       the answer is unique and agency only where judgment is required, hard cost ceilings as
       reliability engineering, capability denial at the tool layer, human confirmation for
       outward-facing actions, and agent failures treated as a measurable defect stream.
5.1.16 The three questions to ask *them*, which reveal whether their AI story is real: who owns the
       tooling, what is measured, and what happened the last time it went wrong.

*(16 leaves)*

### §5.2 The trap index

5.2.1 Consolidate every `**Trap:**` marker in the guide into one table: wrong belief → symptom →
      fix → section.
5.2.2 The version-stale table: every claim that was true in an earlier release and is not now, with
      both versions stated. `[VERSION]`
5.2.3 The top five, for the reader who has ten minutes: rules are enforced by the harness not the
      model; deny cannot carry exceptions; `allowed-tools` pre-approves rather than restricts;
      `--setting-sources` resolves against `cwd`; `${CLAUDE_PLUGIN_ROOT}` is not the repo.
5.2.4 The incident index: every `[INCIDENT]` leaf, one line each, with its cost and its law.

*(4 leaves)*

### §5.3 One-line assertions and drills

5.3.1 The atomic concept checklist: one falsifiable assertion per mechanism, grouped by part.
5.3.2 Numbers drill: 1,536 / 200 lines / 25 KB / 4 MiB / 4 hops / 5,000 / 25,000 / 1,000 patterns /
      20 agents / depth 3 / 5 rules / 160 turns / 1800 s / 500 chars. State what each governs.
      `[NUM]`
5.3.3 Precedence drill: order the settings layers, the permission lists, the agent locations, the
      skill locations, and the `CLAUDE.md` load order — from memory. Note that agents and skills
      order oppositely.
5.3.4 Mechanism drill: for ten observed behaviours, name the file or key that caused it.
5.3.5 Config-reading drill: given a `settings.json`, a `hooks.json` and an agent file, predict what
      a given command does. Then run it.
5.3.6 Cost drill: given a session shape, estimate the bill; then check against `/cost`.
5.3.7 The "explain it to a colleague" test for the five PART 0 concepts.
5.3.8 A review schedule: PART 0 once and never again; the trap index weekly; the numbers drill
      before any interview.

*(8 leaves)*

---

**PART 5 total: 28 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 0 — Ground zero | 46 |
| PART 1 — Basics | 125 |
| PART 2 — Intermediate | 142 |
| PART 3 — Under the hood | 96 |
| PART 4 — Build it | 40 |
| PART 5 — Interview & retention | 28 |
| **Total** | **477** |

Leaves carrying `[ZERO]`: **~30** (all of PART 0 plus the first leaf of most PART 1–3 sections).
`[DOC]`: **~150**. `[CASE]`: **~45**. `[BUILD]`: **~60** (all of PART 4, plus the diagnostic and
proof leaves in PARTs 1–3). `[TRAP]`: **~45 as tagged, but the finished note set produced 154
distinct traps** — writers used `**Pitfall:**` for every wrong belief a leaf surfaced, so treat the
tag count as a floor, not an estimate. `[INCIDENT]`: **10 operational** — not 11 and not 14. §3.10.4's
"md5 over a patched harness" and §3.10.5's "unpinned digest" are the same event, the second being the
first restated as a law; collapse them rather than padding the count. §1.4.28a, §1.4.34a and §2.3.15a
also carry the tag but are **documentation corrections**, not operational failures; report them
separately per `## The incident roster` in `# TASK`. `[NUM]`: **~60**. `[VERSION]`: **~20**.
`[JAVA]`: **~15**. `[PROVE]`: **~45**.

**Every leaf above must appear in the notes**, or be listed in a `## Deferred` block with a reason.
Lettered leaves (`1.4.26a`, `1.4.26b`, `1.4.28a`, `1.4.34a`, `2.3.14a`, `2.3.14b`, `2.3.15a`,
`2.3.15b`, `2.3.15c` — nine of them) are full leaves and count toward the 477.

---

# DIAGRAM MANIFEST

**99 diagram ids (D-01 … D-99).** The id set is **fixed at two digits** — downstream coverage checks
grep for `D-[0-9]{2}`, so every id must resolve in that form. Every id must exist as a standalone SVG
file in `src/notes/detailed/21-ai-for-coding/diagrams/`, named `D-NN-short-slug.svg`, embedded at the
point of explanation with a Markdown image reference and a caption carrying the stable id, e.g.
`**D-28** — Permission evaluation: deny, then ask, then allow`.

Two things about the id count, both learned from the last run:

- **Fifteen of the 99 are `table` type.** Where the `Type` column says `table`, a Markdown table is
  the correct rendering and no SVG file is required — the `D-NN` id still appears at that point in
  the prose so the id is accounted for. The fifteen are D-02, D-04, D-16, D-17, D-22, D-30, D-32,
  D-33, D-45, D-48, D-51, D-68, D-76, D-78, D-91.
- **A frame series expands into lettered files under the same two-digit id.** `D-12` with five frames
  becomes `D-12a-…svg` through `D-12e-…svg`. The parent id stays two digits and stays greppable. The
  last run legitimately expanded 16 manifest entries this way and produced **128 SVG files from 84
  SVG-type ids**. That is correct behaviour, not drift — but **report every file produced** in
  `00-index.md`, and keep the caption's id in the `D-12` form (optionally `D-12c`) so the grep
  resolves.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, author each frame as its own file (`D-12a-…`,
  `D-12b-…`) or as that many clearly separated, individually labelled panels inside the one SVG.
  Report every id and every filename produced.
- Every label, constant, key name and value named in `Must show` must be visible as text in the
  SVG. A diagram that omits a named value does not satisfy the manifest.
- Arrows are directional, and the direction is spelled out in the legend so it cannot be read
  backwards.
- **Labels name the real subject matter** — `permissions.deny`, `PreToolUse`, `check-init.sh`,
  `settings.local.json`, `DEFAULT_MAX_TURNS = 160`, `ClaudeRunner` — never `Foo`, `hook1`,
  `my-agent` or `Node A`.
- Never inline `<svg>` in the Markdown. Never draw with ASCII characters.
- Canvas, palette, routing, typography and the render-and-look self-check come from the
  `## Diagram spec` section of the `notes-generator` specification, handed to illustrators verbatim.
  This manifest does not restate or override it.

## PART 0 diagrams (D-01 … D-17)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-01 | The model is one function: text in, text out | 0.1.1, 0.1.7 | before-after | Left: one box labelled "large language model", one arrow in labelled "text", one arrow out labelled "text". Right: a panel headed "what it does NOT have" listing memory between calls, filesystem, network, clock, and a second panel "what it cannot do" listing read a file, run a command, remember yesterday, check whether it is true. An annotation panel: "everything it appears to do, the harness did" |
| D-02 | Tokens per character for three real strings | 0.1.3, 0.1.4 | table | Three rows: an English sentence, a Java method (`public Optional<ClaudeEnvelope> parse(String stdout)` with a body), a minified JSON settings blob. Columns: the literal string, character count, token count, characters per token. The ~3–4 chars/token figure for prose and the visibly worse ratio for code and JSON both stated as numbers, with the counting method named |
| D-03 | One distribution, two sampled answers | 0.1.2, 0.1.6, 0.1.8 | step-sequence, 3 frames | Frame 1: the text so far, ending mid-sentence. Frame 2: a bar chart of candidate next tokens with probabilities summing to 1, the top three labelled. Frame 3: two complete outputs from the same input, side by side, differing — both fluent. An annotation panel: "fluency is not a correctness signal" |
| D-04 | Model tiers as an engineering decision | 0.1.10, 0.1.11, 3.5.3 | table | Rows: `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`, `claude-fable-5`. Columns: alias, what to use it for (architecture judgment / implementation / exploration and search / per its documented role), relative cost ratio stated as a number, and what a `[1m]` suffix means. Every price or ratio carries the pricing-basis reference required by the cost-provenance rule in the `# OUTPUT CONTRACT`, plus the date read |
| D-05 | Agent = model + loop + tools | 0.1.12, 0.3.1 | hierarchy | Root box "agent"; three children "model (stateless function)", "loop (the harness)", "tools (name + description + JSON schema)". Beside it a contrast panel: "chatbot = model + loop, no tools" and "'AI' = not a definition". Arrows labelled so the reader sees the loop owns the tools, not the model |
| D-06 | A request is an ordered list of messages | 0.2.3 | memory-layout | The literal JSON of a two-turn conversation: a `system` message, a `user` message, an `assistant` message, a second `user` message. Each drawn as a labelled slot in an ordered array with its index. Role names spelled exactly `system`, `user`, `assistant` |
| D-07 | The window is the argument list, not a memory | 0.2.4, 0.2.5 | before-after | Left, the wrong model: one box "the model", an arrow "writes to memory", a persistent store. Marked as false. Right, the real model: a stateless `@RestController`-shaped handler receiving the entire conversation as its request body, and a client that appends to that body each turn. A panel "where the analogy breaks": no session, no cookie, no server-side store |
| D-08 | Cost scales with conversation length | 0.2.6, 3.4.3 | cost-curve | X axis turns 1 to 100, Y axis cumulative input tokens. A curve rising super-linearly because the whole transcript is re-sent each turn. Two points annotated with the actual arithmetic: the 10-turn total and the 100-turn total, each shown as a sum, not just a result, and each labelled as derived. A flat reference line labelled "what people assume: cost of the last message only" |
| D-09 | Prompt caching: the reusable prefix | 0.2.8, 0.2.9, 3.4.4 | before-after | One request drawn as a strip: stable prefix (system prompt, tool schemas, memory files) then the changing tail. Left: appended tail, prefix served from cache at a fraction of the price — the fraction stated with its source. Right: the prefix edited, so nothing is cached and everything is re-billed. A timeline strip beneath showing the 5-minute default TTL, `promptCacheTtl` and `subagentPromptCacheTtl` labelled, and a 6-minute pause crossing the expiry |
| D-10 | The 200K budget, itemised | 0.2.10, 0.2.11, 2.6.2 | memory-layout | A single 200K bar divided and labelled with token counts: system prompt, tool schemas, memory files, skill listing, environment/git snapshot, then conversation, then free space. The autocompaction threshold drawn as a vertical line with its percentage and the resulting usable figure written as arithmetic (`200,000 × threshold = usable`). If the token counts were not read from a real `/context`, the caption says "not measured here" and names the command |
| D-11 | One turn of the agent loop | 0.3.1, 0.3.2, 0.3.3, 0.3.4 | step-sequence, 4 frames | Frame 1: the harness assembles the request. Frame 2: the model emits a `tool_use` block naming the tool and its arguments — labelled "the model does NOT run it". Frame 3: the harness consults the permission rules and decides, then executes. Frame 4: a `tool_result` message appended to the transcript, transcript visibly longer. An annotation panel: "this is the entire basis of the permission system" |
| D-12 | A real loop end to end, with token counts | 0.3.7 | step-sequence, 5 frames | The task "rename this method". Frame 1 Grep, frame 2 Read, frame 3 Edit, frame 4 done. Each frame shows the transcript as a growing stack of messages **and the cumulative token count after that step, as a number**. Frame 5: a total, with the arithmetic, labelled measured or derived |
| D-13 | The built-in tools by category | 0.3.8, 0.3.9 | hierarchy | Six category boxes with their tools named exactly: file (Read, Write, Edit, Glob, Grep), shell (Bash), web (WebFetch, WebSearch), delegation (Agent, SendMessage), meta (Skill, ToolSearch), task/UI (TodoWrite, AskUserQuestion). A side panel on deferred tools: which schemas are loaded up front, which arrive via `ToolSearch`, and the token saving stated |
| D-14 | One loop, many front ends | 0.3.11 | hierarchy | One shared bottom layer "the harness: the loop, the tools, the settings files". Above it, four front ends: CLI, VS Code / JetBrains extension, desktop app, web app. Arrows from each to the same layer. An annotation: same `~/.claude/settings.json`, same `.claude/`, same permission rules |
| D-15 | "Why is it doing that?" — the diagnostic order | 0.4.3, 1.1.9 | decision-tree | Root: "a behaviour surprised you". Branches, in the order to try them: `/context` (what loaded), `/doctor` (resolved settings and health), `/permissions` (which rule and which file), `/hooks` (which hook and which source), `/memory` (which instruction files), `/config`, `claude --debug`. Each leaf names what that command can and cannot tell you. `/doctor` labelled `[Skill]` and the built-ins labelled as built-ins, per §1.5.23. A terminal node: `--safe-mode` / `--bare` to answer "is it my config or the tool?" |
| D-16 | A real `/context` read row by row | 0.4.4, 2.6.1, 3.1.1 | table | Every row of a real `/context` output: system prompt, system tools, MCP tools, memory files, custom agents, skill listing, messages, free space. Columns: tokens, percentage of window, which file or subsystem supplies it, and the lever that reduces it. Totals reconciling to the window size. If the output could not be captured, the table says "not measured here" in the tokens column and the prose names the command |
| D-17 | Four reset semantics compared | 0.4.5, 2.6.8 | table | Rows: `/compact`, `/clear`, a fresh session, `--fork-session`. Columns: what is discarded, what is kept, whether `CLAUDE.md` is re-read from disk, whether skill invocations are re-attached, whether the prompt cache survives, and when to use it |

## PART 1 diagrams (D-18 … D-41)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-18 | The `.claude` tree and its user twin | 1.1.2, 1.1.3, 1.1.8 | hierarchy | Two columns. Project `.claude/`: `settings.json`, `settings.local.json`, `CLAUDE.md`, `rules/`, `commands/`, `skills/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`, `agent-memory/`. User `~/.claude/`: the same shapes plus `projects/`, `plugins/`, `keybindings.json`, and the tool-owned `~/.claude.json` drawn in the "do not hand-edit" style. A third panel "outside the repo deliberately": the plugin cache, the transcripts, the auto-memory directory |
| D-19 | The discovery walk | 1.1.6 | step-sequence, 3 frames | A directory chain from `/Users/…/repo/services/payments` up to `/`. Frame 1: the primary working directory. Frame 2: each parent visited in turn, with a tick against the artefacts that walk upward. Frame 3: the artefacts that load from subdirectories on demand (nested `CLAUDE.md`, nested `skills/`) and the ones that do neither, each labelled |
| D-20 | Settings precedence, five layers | 1.2.2, 1.2.3 | hierarchy | Five stacked bands, highest at the top: managed settings, command line (`--settings`), project local (`.claude/settings.local.json`), shared project (`.claude/settings.json`), user (`~/.claude/settings.json`). One key (`model`) set at three of them, with the winner marked. Two annotation panels marked as false beliefs: "more specific wins" and "command line always wins" — with managed beating the command line drawn explicitly |
| D-21 | Where `settings.local.json` lands | 1.2.5, 1.2.6 | decision-tree | Root: "the tool needs to write a local settings file". Branches: inside a git repo → repository root, not the directory you started in; outside a repo → the start directory; repo root is `$HOME` → the exception; worktree → the main checkout's root; Windows; foreign ownership. Each leaf names the resulting absolute-ish path shape |
| D-22 | The settings key groups | 1.2.9, 1.2.10 | table | All fifteen groups as rows: permissions, hooks, plugins/skills, context/memory, model/responses, MCP, sandbox, attribution, auth, data/privacy, interface, agents/sessions/worktrees, updates, enterprise, global config. Columns: one representative key, what it controls, and whether this reader touches it first. The twelve first-touch keys (`permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`, `autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`, `statusLine`, `cleanupPeriodDays`) marked |
| D-23 | `CLAUDE.md` load order, concatenated not overriding | 1.3.3, 1.3.4, 1.3.5, 1.3.6 | step-sequence, 4 frames | Frame 1: the managed policy path with all three OS paths written out. Frame 2: `~/.claude/CLAUDE.md` appended. Frame 3: `./CLAUDE.md` or `./.claude/CLAUDE.md` appended, then `./CLAUDE.local.md` after it at that level. Frame 4: the assembled block, root-down, nearest-last. A fifth panel: a subdirectory `CLAUDE.md` arriving later, on demand, when Claude reads a file in that directory — not at launch |
| D-24 | `@path` imports to a depth of four | 1.3.7, 1.3.8 | hierarchy | An import chain five levels deep with hop 5 drawn in the weak style and labelled "not followed: max 4 hops". Imports inside a code span and inside a fence drawn as skipped. An annotation panel: "an import does not save context — the imported file loads at launch too; splitting buys organisation only" |
| D-25 | A path-scoped rule activates on file match | 1.3.14, 1.3.15, 1.3.16 | state-transition | Two states: "rule not loaded" and "rule loaded". The transition edge labelled with the `paths:` glob (`**/*.java`) and the trigger "Claude touches a matching file". A second edge for a non-matching file returning to the first state. An annotation panel with the shared budget as numbers: 1,000 expanded patterns / 4 MiB, what happens on overflow, and the `[`-bracket-expression pitfall |
| D-26 | Auto memory on disk, and what actually loads | 1.3.21, 1.3.22, 1.3.23, 1.3.25 | memory-layout | The directory `~/.claude/projects/<project>/memory/` holding `MEMORY.md` plus one topic file per memory. A cut line across `MEMORY.md` at "first 200 lines or 25 KB" with the part below labelled "not loaded at session start". Topic files marked "read on demand". The four types `user`, `feedback`, `project`, `reference` labelled. A panel: keyed on the git repo so worktrees share it; machine-local; does **not** load into a subagent, a fork excepted |
| D-27 | What survives a compaction | 1.3.26, 3.2.3, 3.2.4, 2.6.6 | before-after | Left, before: the full transcript, the invoked skills, the nested `CLAUDE.md` files, the path-scoped rules, conversation-only instructions. Right, after: a summary block, project-root `CLAUDE.md` re-read from disk, the most recent invocation of each skill within budget. Everything lost drawn in the degraded style. The budget written as numbers: first 5,000 tokens per skill, 25,000 combined, filled newest-first |
| D-28 | Permission evaluation: deny, then ask, then allow | 1.4.2, 1.4.3 | flowchart | One tool call entering. Sequential diamonds: matches `deny`? → blocked. matches `ask`? → prompt. matches `allow`? → runs. No match → the mode's default. "First match wins" and "specificity does not reorder" on the canvas. A worked example beside it: `Bash(aws *)` in `deny` and `Bash(aws s3 ls)` in `allow`, with `aws s3 ls` following the blocked path |
| D-29 | Bare deny removes the tool; scoped deny blocks the call | 1.4.4 | before-after | Left, `deny: ["Bash"]`: the tool list Claude sees, with Bash absent entirely. Right, `deny: ["Bash(git push *)"]`: Bash present in the tool list, one matching call blocked at the gate. The two mechanisms named as different |
| D-30 | The Bash wildcard matching table | 1.4.6, 1.4.7, 1.4.8 | table | Rows: `Bash(npm run build)`, `Bash(npm run *)`, `Bash(git log * main)`, `Bash(git * main)`, `Bash(* --version)`, `Bash(ls *)`, `Bash(ls*)`. Columns: three concrete commands each, with matches / does not match per cell, and a notes column. `Bash(git * main)` matching `git -c core.fsmonitor=<script> diff main` present as its own highlighted row with the reason: the `*` spans options |
| D-31 | Compound splitting, then wrapper stripping, then matching | 1.4.9, 1.4.10, 1.4.11, 1.4.12, 1.4.13 | step-sequence, 4 frames | The command `timeout 30 mvn -q test && FOO=1 git commit -m "x" \| tee out.log`. Frame 1: split on the recognised separators, all seven listed (`&&`, `\|\|`, `;`, `\|`, `\|&`, `&`, newline). Frame 2: wrappers stripped — `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`, `noglob`, bare `xargs` — with `command -v` and `nocorrect` marked not stripped. Frame 3: leading env assignments stripped for allow rules, deny rules matching past them. Frame 4: each subcommand matched independently. A panel: environment runners NOT stripped (`devbox run`, `npx`, `docker exec`, `direnv exec`, `mise exec`), and "yes, and don't ask again" saving up to 5 separate rules |
| D-32 | Which tools consult path rules | 1.4.16, 1.4.17, 1.4.18, 1.4.19, 3.3.6 | table | Rows: `Read`, `Edit`, `Write`, `NotebookEdit`, `MultiEdit`, `Glob`, `Grep`, `Bash` file commands (`cat`, `head`, `tail`, `sed`), an arbitrary subprocess. Columns: does a path rule apply, is it silently accepted and ignored, what to write instead, and what stops it at OS level. The `Read` deny also covering Edit and Write but not `NotebookEdit` shown as its own row |
| D-33 | The six permission modes | 1.4.25, 1.4.26, 1.4.26a, 1.4.27, 1.4.28, 1.4.28a | table | All six rows: `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. Columns: exactly what is auto-approved, what still prompts, what it never allows, and the setting that disables it. The `acceptEdits` row names `mkdir`, `touch`, **`rm`**, **`rmdir`**, `mv`, `cp`, **`sed`** with the working-directory / `additionalDirectories` scope, and carries a highlighted "auto-approves deletion" flag. The `auto` row states the classifier model (**Sonnet 5**) and the **3-consecutive / 20-total** block fallback thresholds. The `bypassPermissions` row names exactly what it still refuses — critical-path `rm`/`rmdir`, explicit `ask` matches, always-interactive tools (`AskUserQuestion`, `requiresUserInteraction` MCP tools), `isolatePeerMachines` and held inbound messages — and carries a separate flag reading **"does NOT protect `.git` or `.claude`: protected-path writes are allowed"**, with the false claim shown crossed out beside it |
| D-34 | Workspace trust, how it is keyed, and why it is sticky | 1.4.32, 1.4.33, 1.4.34, 1.4.34a, 1.4.35 | decision-tree | Root: "a project's committed settings want to grant something". Branches: `allow` and `additionalDirectories` → gated on the trust dialog; `deny`/`ask` → not gated, because they only restrict. A keying panel: git repo root inside a repo (nested repos excluded), start directory outside one, session-only in `$HOME`. A highlighted terminal node for the non-interactive case, stated correctly: **a `-p` or SDK session shows no dialog and therefore does NOT apply an untrusted folder's committed `allow`/`additionalDirectories` at all — it prints a stderr warning**; the "counts as accepted" label attached only to the narrower git tracked/untracked check on `settings.local.json`. A second highlighted panel for the real risk: trust keyed per repository-root path and **never re-checked when a commit widens `permissions.allow`**, drawn as a commit arrow passing the trust gate without stopping. A third panel: an untracked local file applies immediately; a tracked one, or a symlinked `.claude`, waits |
| D-35 | Sandbox is the layer below permissions | 1.4.39, 3.3.7, 2.9.4 | hierarchy | Three stacked layers: the model's intent (shaped by prompt and `CLAUDE.md`), the permission rules (enforced by the harness), the OS sandbox (`sandbox.enabled`, filesystem allow/deny, network allowlist, credential masking). An arrow showing a Python subprocess opening a file directly, passing straight through the middle layer and being stopped only by the bottom one |
| D-36 | Progressive disclosure: listing versus body, and two different budgets | 1.5.5, 1.5.6, 3.1.5 | before-after | Left: fifty skills as fifty listing entries, each just `description` + `when_to_use`, each **truncated at the per-entry cap `skillListingMaxDescChars` = 1,536 characters**, with the total token cost computed. A second, separate cap line across the whole set labelled **`skillListingBudgetFraction` — a pool budget of roughly 1% of the context window**, with two entries drawn as dropped by the pool budget despite each being inside the per-entry cap. The two numbers must be visibly distinct objects, not one label. Right: one skill fired, its full body now in context, with that body's token cost. Beneath, the counterfactual: the same fifty procedures written into `CLAUDE.md`, always paid, with its total |
| D-37 | Skill and command locations, the conflict order, and built-in versus bundled | 1.5.1, 1.5.3, 1.5.4, 1.5.23 | hierarchy | A layered stack: enterprise, personal (`~/.claude/skills/`), project (`.claude/skills/`), plugin (namespaced `plugin:skill`). Arrows showing a project skill overriding a bundled skill of the same name but not its aliases, a skill beating a same-named `commands/` file, and plugin skills coexisting rather than overriding. An annotation panel: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both produce `/deploy` and behave the same way — custom commands **are** skills. A nested-subtree box for the monorepo mechanism. A separate two-column panel headed "built-in command versus bundled skill": built-ins `/help`, `/compact`, `/clear`, `/context`, `/config`, `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/cd`, `/add-dir`, `/model`, `/effort`, **`/run`**; bundled skills **`/doctor`**, **`/rewind`**, `/code-review`, `/security-review`, `/loop`. `/doctor` and `/rewind` on the skill side and `/run` on the built-in side, each flagged as the reverse of the common assumption |
| D-38 | `allowed-tools` pre-approves; `disallowed-tools` restricts | 1.5.8 | before-after | Left, the wrong belief: a skill with `allowed-tools: [Bash, Read]` drawn as a fence around those two tools, every other tool outside it — marked as false. Right, the mechanism: the same frontmatter drawn as pre-approval for the invoking turn only, with every other tool still callable, and the pre-approval clearing on the next user message. A third panel: `disallowed-tools` as the field that actually removes tools |
| D-39 | Dynamic injection runs once, before the content is sent | 1.5.12, 1.5.13 | step-sequence, 3 frames | A `SKILL.md` containing an inline `` !`git branch --show-current` `` and a fenced ` ```! ` block. Frame 1: the file on disk with both placeholders literal. Frame 2: substitution running once over the original file, the commands executed, their output placed inline — with the output visibly not re-scanned. Frame 3: the rendered content entering the conversation as one message. A panel: the inline form is recognised only at line start or after whitespace, so `` KEY=!`cmd` `` stays literal; `disableSkillShellExecution` turns it off |
| D-40 | Skill content lifecycle across turns and a compaction | 1.5.15, 1.5.16 | timeline | One time axis, four marks: invocation (rendered content enters as one message), later turns (it stays; the file is not re-read), a re-invocation with identical content (a note added, not a second copy), the compaction (most recent invocation of each skill re-attached after the summary, 5,000 tokens each / 25,000 combined, newest-first). Two older skills drawn falling outside the budget and vanishing |
| D-41 | Which mechanism for which need | 1.5.26, 2.8.4 | decision-tree | Root: "you want the agent to do X reliably". Branches to terminals: a fact that always applies → `CLAUDE.md`; a fact for one file type → path-scoped rule in `.claude/rules/`; a procedure → skill; must-happen → hook; one correct answer given the inputs → shell script; verbose-in/small-out → subagent; needs human authority → confirmation gate with the tool denied; distribution to a team → plugin. Each terminal annotated with its enforcement strength: context (Claude tries) versus guaranteed (the harness runs it) |

## PART 2 diagrams (D-42 … D-68)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-42 | The subagent context boundary | 2.1.1, 2.1.8, 2.1.9, 2.1.10 | memory-layout | Two separate window boxes, parent and subagent, with a hard boundary line between them. Crossing inward, labelled on arrows: the task string, its own system prompt and environment, the full `CLAUDE.md` hierarchy (except Explore/Plan), a git-status snapshot taken at parent session start, preloaded `skills`, the sibling roster. Crossing outward: one final message. Blocked at the boundary, drawn in the degraded style: conversation history, the main output style, auto memory, previously read files, previously invoked skills |
| D-43 | Agents and skills order oppositely | 2.1.2, 2.1.3, 1.5.3 | before-after | Two stacks side by side. Agents, highest first: managed settings, `--agents` CLI JSON, `.claude/agents/`, `~/.claude/agents/`, plugin `agents/` — project beats user. Skills: enterprise, personal (`~/.claude/skills/`), project (`.claude/skills/`) — personal beats project. The inverted pair highlighted with a single annotation: "two subsystems, two orders" |
| D-44 | A fork versus a fresh subagent | 2.1.13, 1.5.17 | before-after | Left, fresh subagent: an empty window receiving only the task string, prompt cache not shared. Right, fork (`/subtask`, `context: fork`): the whole conversation and system prompt inherited, prompt cache shared and therefore cheaper, and a crossed-out arrow labelled "cannot spawn further forks". A decision line beneath: when a fork beats a fresh agent |
| D-45 | Subagent limits and the tools that are never there | 2.1.14, 3.9.12 | table | Rows: concurrent subagents (default 20, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), nesting depth (3, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), combined agent description budget (~15,000 tokens), tools never available in a subagent (`AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `Workflow`). Columns: the value, the env var or setting that changes it, and what happens when you hit it |
| D-46 | Where a subagent's 2× comes from | 2.1.19, 2.6.10, 3.4.5 | cost-curve | Two stacked bars. Inline: the existing prefix reused, cache reads, one set of output tokens. Subagent: a fresh system prompt, fresh tool schemas, the `CLAUDE.md` hierarchy re-supplied, the task string, then the work, then the returned message re-entering the parent transcript. Each segment carries a token number, the ratio is written as arithmetic, and the whole is labelled derived with its basis. A second panel making the opposite case: 150K burned inside, 200 words returned — the parent's transcript grows by the 200 words only |
| D-47 | One writer per output path, ever | 2.1.24, 3.9.2 | before-after | Left, the failure: two parallel agents given folder-scoped lanes plus one flat shared directory, both writing the same slug, the second overwriting the first silently with no orphan left to notice. Right, the fix: a disjoint filesystem partition, one writer per path, a join step that only reads. An annotation: "partition the filesystem, not the topic" |
| D-48 | Three ways to set a persona | 2.2.1, 2.2.2, 2.2.3, 2.2.4 | table | Rows: `--agent <name>`, `--append-system-prompt <text>`, `--system-prompt` / `--system-prompt-file`, `--append-subagent-system-prompt`. Columns: what happens to the default system prompt (loaded from the registered agent / appended to / replaced / appended for every subagent), whether the model and tool allowlist come with it, what you lose, and the symptom when you pick the wrong one (an agent that behaves almost right and ignores tool restrictions it never had) |
| D-49 | The hook lifecycle across one session | 2.3.6 | timeline | One session on a time axis with events firing in order: `SessionStart` / `Setup`, `InstructionsLoaded`, `UserPromptSubmit` / `UserPromptExpansion`, `PreToolUse`, `PostToolUse` / `PostToolUseFailure` / `PostToolBatch`, `PermissionRequest` / `PermissionDenied`, `SubagentStart` / `SubagentStop`, `PreCompact` / `PostCompact`, `Stop` / `StopFailure`, `SessionEnd`. Each mark labelled with whether it can block |
| D-50 | The 32 events, grouped | 2.3.6 | hierarchy | Twelve group boxes with every event named exactly: session lifecycle (`SessionStart`, `Setup`, `SessionEnd`), prompt (`UserPromptSubmit`, `UserPromptExpansion`), tools (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`), permissions (`PermissionRequest`, `PermissionDenied`), turn (`Stop`, `StopFailure`), subagents (`SubagentStart`, `SubagentStop`), tasks (`TaskCreated`, `TaskCompleted`, `TeammateIdle`), context (`PreCompact`, `PostCompact`, `InstructionsLoaded`), environment (`ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`), worktrees (`WorktreeCreate`, `WorktreeRemove`), MCP (`Elicitation`, `ElicitationResult`), UI (`Notification`, `MessageDisplay`). The count 32 and the version v2.1.2xx stated on the canvas |
| D-51 | Which events can block, and which field each honours | 2.3.7, 2.3.15 | table | One row per blocking-capable event. Columns: can it block; **which field it honours and at which level** — `hookSpecificOutput.permissionDecision` + `permissionDecisionReason` for `PreToolUse` (its top-level `decision`/`reason` marked **deprecated**, with `"approve"`/`"block"` → `"allow"`/`"deny"`), **top-level `decision`/`reason`** for `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `ConfigChange`, `PreCompact`, a `decision` **object** for `PermissionRequest`, and "none — it already ran" where that is the answer; what a non-zero exit does (exit 2 routes stderr as `reason`); and what the model sees. A separate top row for the **universal** fields every event accepts (`continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`) so the reader cannot mistake a universal field for an event-specific one. Non-blocking events listed in a second block |
| D-52 | Hook output: three kinds of field, and the inverted `Stop` contract | 2.3.12, 2.3.13, 2.3.14, 2.3.14a, 2.3.14b, 2.3.15a, 2.3.15b, 2.3.15c | step-sequence, 4 frames | Frame 1 — exit codes: a hook returning with three paths, `0` (success; stdout to the debug log, except `UserPromptSubmit` / `UserPromptExpansion` / `SessionStart` where it is shown to Claude), `2` (blocking error, the only code that blocks without JSON, its stderr routed as `reason`), anything else (non-blocking); with a highlighted merge node: exit 2 overrides a JSON `permissionDecision: "allow"`. Frame 2 — the three field kinds drawn as three visually distinct regions of one JSON object: **universal top-level** (`continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`), **top-level `decision` + `reason`**, and **nested `hookSpecificOutput`** with its required `hookEventName`. Frame 3 — the `Stop` contract: `decision: "block"` drawn as the path that KEEPS Claude working with `reason` marked **required**, omitting `decision` drawn as allowing the stop, and `hookSpecificOutput.additionalContext` drawn as the third path labelled `Stop hook feedback` in the transcript. Three crossed-out non-existent fields on the same frame: `hookSpecificOutput.continue`, `decision: "continue"`, `continueReason`. Frame 4 — the guards: `continue: false` as the universal kill switch that **takes precedence over any decision field**, `stopReason` arrowed to the **user** and explicitly not to Claude, `suppressOutput` labelled "accepted, does nothing", the **10,000-character** output cap with the overflow written to a file and replaced by a preview plus path, and the `stop_hook_active` stdin field with the **8-consecutive-continuation cap** |
| D-53 | A hook cannot unblock a deny | 2.3.16, 3.3.2, 3.3.1 | flowchart | One tool call flowing through rule collection, then deny → ask → allow, then the `PreToolUse` hook, then the mode default, then the prompt. The hook drawn strictly after the rule evaluation. Two traces: a hook returning `allow` on a call that matched `deny` → still blocked; a hook returning `allow` on a call that matched `ask` → still prompts |
| D-54 | The six places a hook can be configured | 2.3.18, 2.3.19 | hierarchy | Six source boxes: user settings, project settings, local settings, managed policy, plugin `hooks/hooks.json`, skill frontmatter (rest of session), subagent frontmatter (while it runs) — grouped so the settings trio reads as one family. Each annotated with its lifetime. A kill-switch panel: `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and "individual hooks cannot be disabled, only deleted" |
| D-55 | The `SessionStart` reindex pile-up | 2.3.25 | step-sequence, 4 frames | Frame 1: one session starts, the hook decides a delta-reindex is due, two handbook clones pulled, embedder processes spawned. Frame 2: a second and third concurrent session each independently reach the same decision — no cross-session coordination, drawn as an absent lock. Frame 3: hundreds of concurrent embedder processes, **100+ GB** of abandoned partial indexes, the machine unusable. Frame 4: the recovery attempt — starting a session to fix it is itself the trigger for the next pile-up. An annotation panel with the law: anything expensive or stateful in a `SessionStart` hook needs a lock or must not be there |
| D-56 | An MCP server's schemas are a per-turn tax | 2.4.7, 3.1.4 | cost-curve | X axis turns, Y axis tokens. A flat baseline for the default tool set with its token figure. A raised line after one chatty MCP server connects, the delta labelled with the server's schema cost. The cumulative extra over a 40-turn session written as arithmetic and labelled derived. A note that `/context` is how you measure it, and that the tool-name form is `mcp__<server>__<tool>` |
| D-57 | LSP symbol lookup versus read-and-grep | 2.4.11, 2.4.12, 2.6.3 | before-after | Left: three whole files read plus a repo-wide grep to answer "where is this method used", with the token total. Right: one LSP symbol lookup answering the same question, with its token total. The ratio stated. The three plugins named (`pyright-lsp`, `typescript-lsp`, `jdtls-lsp`) and the framing quoted: the argument is token cost, not correctness |
| D-58 | The plugin directory layout | 2.5.3, 2.5.4 | hierarchy | The plugin root with `.claude-plugin/plugin.json` inside it and **only** that file inside `.claude-plugin/`. Siblings at the plugin root: `skills/`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`, `settings.json`. A crossed-out variant showing `skills/` misplaced inside `.claude-plugin/` labelled "silently ships nothing". An annotation: the plugin root is the plugin's own directory, never `~/.claude/` |
| D-59 | The plugin and marketplace dependency graph | 2.5.9, 2.5.10, 2.5.11, 2.5.17 | hierarchy | Two marketplace boxes, each with its `.claude-plugin/marketplace.json`. The first declares `allowCrossMarketplaceDependenciesOn: ["ig-superclaude"]` and contains a plugin at `version 0.10.2` whose `dependencies` names `{ name: "ig-superclaude", marketplace: "ig-superclaude" }`. A dependency edge crossing to the second marketplace, drawn in the weak style until the user has explicitly trusted it, with the refusal to auto-add labelled. A failure panel: the unresolved state, the cryptic `/reload-plugins` error, and `claude plugin list --json` exposing the per-plugin `errors` array |
| D-60 | `${CLAUDE_PLUGIN_ROOT}` is not the repo | 2.5.18, 2.5.19, 2.3.17 | before-after | Left: a hook living at `<repo>/.claude/hooks/`, resolving the repo root as `dirname "$0"/../..` — correct. Right: the same hook inside an installed plugin, where `${CLAUDE_PLUGIN_ROOT}` is the install/cache directory, and the same expression resolves into the cache — wrong, with the broken path drawn. The fix panel: resolve via `git rev-parse --show-toplevel`, and refuse with a clear message rather than inventing a third fallback |
| D-61 | `strictPluginOnlyCustomization` closes the side doors | 2.5.14, 2.5.15, 2.9.7 | hierarchy | Four extension channels — skills, agents, hooks, MCP — each with three possible sources: user, project, plugin. With the lock off, all twelve edges live. With `strictPluginOnlyCustomization` on (and its `.agents`, `.hooks`, `.mcp`, `.skills` sub-keys), the user and project edges drawn as blocked and only the plugin edges live. A panel with the neighbouring keys: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`, `strictKnownMarketplaces`, `disableSideloadFlags`, `pluginTrustMessage` |
| D-62 | The four biggest avoidable context costs, ranked | 2.6.3, 2.6.4 | cost-curve | Four bars in rank order with token figures: unbounded command output, whole-file reads where a symbol lookup would do, a bloated always-on `CLAUDE.md` (cost per turn × turns), chatty MCP servers. Each bar annotated with its specific fix: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over `cat`, `git diff --stat` before `git diff`, a path-scoped rule instead of a global instruction, disabling the server |
| D-63 | Isolation arithmetic | 2.6.10, 2.1.19 | before-after | Left, inline: a 150K-token exploration living in the main transcript, then every subsequent turn re-sending it — the running total over the next ten turns written as a sum. Right, isolated: the same 150K burned inside a subagent, 200 words returned, the parent transcript growing by the 200 words only, and the subagent's 2× cost stated honestly. The net comparison as a single number, labelled derived |
| D-64 | Plan mode moves the correction earlier | 2.7.1, 2.7.2 | timeline | Two lanes on one time axis. Without a plan: prompt → a large diff → review → an expensive correction after the diff exists, with rework shaded. With a plan: read-only exploration → a reviewable plan → the correction applied to the plan → execute → a smaller review. `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode` and `plansDirectory` labelled on the second lane |
| D-65 | Script or prompt | 2.8.1, 2.8.4, 2.8.5 | decision-tree | Root: "do the inputs determine one correct answer?". Yes → shell script, annotated "testable, no variance, no token cost". No → prompt, annotated "judgment, synthesis". Further branches: must-happen → hook; verbose-in/small-out → subagent; needs human authority → confirmation gate with the tool denied. An annotation panel quoting the source of the rule: resolving paths, merging JSON and creating symlinks all have a single correct answer given the inputs. A second panel: "the model could do it" is not an argument — cost, variance, and a script is testable where a prompt is not |
| D-66 | The threat model: one agent's blast radius | 2.9.1, 2.9.3 | hierarchy | The agent at the centre with three properties stated: it runs with your credentials, it reads what you can read, it follows text it finds. Reachable surfaces drawn outward: the filesystem, the shell, the network, the cloud credentials, the issue tracker via MCP, the git remote. Beside them the controls that hold, ranked by strength: deny rules, `PreToolUse` blocking hooks, the sandbox, least-privilege tool sets, human confirmation on outward-facing actions. Prompting drawn explicitly outside the control list |
| D-67 | Prompt injection: the path from data to tool call | 2.9.2 | step-sequence, 4 frames | Frame 1: an instruction embedded in data the agent will read — an issue comment, a fetched web page, a file, a `tool_result`. Frame 2: that text arriving in the transcript indistinguishable in kind from the user's own message. Frame 3: the model emitting a `tool_use` block the user never asked for. Frame 4: the harness's rule evaluation as the only thing between that block and the action. An annotation: "tell it to ignore instructions in data" is not a control, because the instruction and the control live in the same channel |
| D-68 | The `allowManaged*Only` lock family | 2.9.6, 2.9.7, 2.9.8 | table | Rows: `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`, `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`. Columns: what it locks, which sources stop being honoured, and what a developer sees when they try. A delivery panel: `managed-settings.json`, MDM, server-managed settings from the console, `managedSourcesBehavior`, `policyHelper` (`path`, `refreshIntervalMs`, `timeoutMs`), `forceRemoteSettingsRefresh` |

## PART 3 diagrams (D-69 … D-93)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-69 | Request assembly order, and the cached prefix | 3.1.1, 3.1.3 | memory-layout | One request as an ordered vertical strip: system prompt (built-in + appended), tool schemas, memory files as a user message, environment/git snapshot, skill listing, then the conversation. A bracket down the stable portion labelled "cached prefix — reused at cache-read price". `--exclude-dynamic-system-prompt-sections` labelled against the per-machine sections it moves out of the prefix. Each segment carries a token figure, marked measured or derived |
| D-70 | `CLAUDE.md` is a user message, not the system prompt | 3.1.2 | before-after | Left, the wrong model: `CLAUDE.md` drawn inside the system prompt block — marked false. Right, the real assembly: the system prompt, then a separate `user` message carrying the memory files. Two consequences annotated: this is why it is guidance and not policy, and this is why `--append-system-prompt` behaves differently |
| D-71 | The cost of fifty skills in the listing | 3.1.5, 1.5.6 | cost-curve | X axis number of skills 0 to 50, Y axis listing tokens. The per-skill cost derived from `description` + `when_to_use` truncated at the per-entry cap `skillListingMaxDescChars` = **1,536 characters**, the arithmetic shown and labelled derived, and the total at 50 marked. A **separate** horizontal cap line for the pool budget `skillListingBudgetFraction` ≈ **1% of the context window**, with the behaviour at that cap stated. The two limits must be drawn as two distinct lines with two distinct labels — conflating them is the error this leaf exists to fix |
| D-72 | One JSONL transcript turn, annotated | 3.1.7, 3.1.8, 0.4.8 | memory-layout | A real transcript path `~/.claude/projects/<project>/<session>/` and one JSONL record expanded: its role, its content blocks including a `tool_use` and a `tool_result`, and its usage fields. Arrows to where a per-turn token count is read from. A note that `telemetry/transcript.py` reads exactly these files to mine friction signals, and that `cleanupPeriodDays` governs how long they live |
| D-73 | The compaction re-attachment budget | 3.2.3, 3.2.2 | step-sequence, 3 frames | Frame 1: a session with six skills invoked at different times, each with a token size. Frame 2: the threshold reached — the percentage and what it is a percentage of written as arithmetic against the window size. Frame 3: the summary, then re-attachment newest-first: the most recent invocation of each skill, first 5,000 tokens each, stopping at 25,000 combined, with the two oldest skills visibly evicted. Both numbers labelled on the canvas |
| D-74 | The full permission-evaluation pipeline | 3.3.1, 3.3.2, 3.3.4 | flowchart | One tool call from entry to outcome. Stage 1: rule collection across managed → CLI → local → project → user. Stage 2: deny → ask → allow, first match wins. Stage 3: the `PreToolUse` hook. Stage 4: the mode's default. Stage 5: the interactive prompt. A branch off stage 2 for the read-only command fast path, with the two cases that leave it (write-capable flags with unquoted globs, redirects). A terminal note: a deny at any level cannot be overridden by any other level, including `--allowedTools` and managed settings |
| D-75 | Three Bash commands traced through matching | 3.3.3, 1.4.11 | step-sequence, 3 frames | Three real commands, one per frame, each traced through the same four stages with the intermediate string printed at each: separator splitting, wrapper stripping, env-assignment stripping, per-subcommand matching against a stated rule set. Frame 1 a command that runs, frame 2 one that prompts, frame 3 one that is blocked — each with the specific rule that decided it named |
| D-76 | The four billed quantities | 3.4.1, 3.4.2 | table | Rows: input tokens, output tokens, cache writes, cache reads. Columns: what triggers it, the relative price, and where it appears in the `-p --output-format json` envelope. A second block with per-model pricing and the ratio between tiers. **Every price is quoted from the Claude API pricing page named in `# REFERENCES`, carries the date it was read, and is referenced back to the single `## Pricing basis` note in `00-index.md` rather than being independently restated.** Any figure not on that page is labelled `**Unverified:**` |
| D-77 | Where the money actually goes in one session | 3.4.3, 3.4.4, 3.4.7 | cost-curve | A 40-turn session. Stacked areas per turn: cache reads on the re-sent prefix, fresh input tokens, output tokens, cache writes. The prefix re-send visibly dominating. Two annotations: a 5-minute idle gap crossing the cache TTL and the resulting re-priced turn, and the session total with the arithmetic, labelled derived from the one stated list price. `/cost` and `modelPricing` named as the ways to read it back |
| D-78 | The three ceilings and their failure shapes | 3.4.6, 4.5.2 | table | Rows: `--max-turns`, `--max-budget-usd`, subprocess wall-clock timeout. Columns: what it bounds (agency / money / time), what the run looks like when it trips, whether work is preserved, what the envelope reports, and the distinct exception type a Java wrapper should throw. A note that all three are needed because each bounds a different thing |
| D-79 | Model routing as a cost decision | 3.5.1, 3.5.3, 3.5.5, 3.5.6 | decision-tree | Root: "what is this task". Branches: exploration and search → haiku; implementation → sonnet; architecture and gnarly debugging → opus. Each terminal carries the effort level to pair with it from `low\|medium\|high\|xhigh\|max` and the escalation path haiku → sonnet → opus. A panel: `fastMode` / `/fast` is faster output on the same Opus model, not a downgrade. A failure panel: routing everything to the cheapest model, with a concrete wrong result that cost more than the saving |
| D-80 | The `-p --output-format json` envelope | 3.6.1, 3.6.3, 3.6.2 | memory-layout | One real envelope drawn field by field with a value in each: the result text, `is_error`, `session_id`, the cost field, the token-count fields, the duration. Arrows out to what each is used for downstream: billing, audit, retry classification, continuation. A side panel comparing `text`, `json` and `stream-json` output formats and `text` versus `stream-json` input. If the envelope was not captured from a real run, the caption says so and names the command |
| D-81 | A wrapper's failure taxonomy | 3.6.10, 3.6.11, 3.6.12 | flowchart | The subprocess returning, branching three ways, each handled differently: launch or timeout failure (infrastructure — retry the infrastructure), unparseable envelope (contract — capture a **500-character snippet** of what was actually printed, labelled with the number), `is_error: true` (the agent failed — surface the agent's own report). A node on the retry path labelled "keep the last parsed error envelope so cost and token counts survive the failure", annotated with why discarding them makes the run unbillable and unauditable |
| D-82 | Resolution order: parameter → env → default | 3.6.13, 3.6.16, 4.5.4 | flowchart | One knob resolved through three checks in order: explicit parameter, environment variable, module default. Each check drawn as "present and not None?" rather than "truthy", with an explicit `0` traced through and surviving. The real names on the env layer: `HARNESS_AGENT_MAX_TURNS`, `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`, `HARNESS_AGENT_SETTINGS`. The defaults on the last layer with their values: `DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`, `DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160` |
| D-83 | The `--setting-sources` incident | 3.7.1, 3.7.2, 3.7.3, 3.7.4, 3.7.5 | step-sequence, 4 frames | Frame 1: the coder launched in an isolated per-story git worktree, so `cwd` is the worktree and not the harness repo. Frame 2: `--setting-sources project` resolving `<cwd>/.claude/settings.json` — drawn as an arrow pointing at a file that does not exist there, with the harness's own `permissions.allow` (`Bash(*)`) and destructive-command deny-list sitting unloaded in the other directory. Frame 3: the observed symptom, itemised — read, edit, `mkdir`, `touch`, `mv`, `cp`, `sed` all working (the bare `acceptEdits` defaults) while `mvn`, `git commit`, `chmod` and `java` are all refused. Frame 4: the fix, `--settings <absolute path>`, evaluated independently of `cwd`. An annotation panel with both generalisations and the `docs/adr/0016` / AP-11470 reference |
| D-84 | Three levels of building on Claude | 3.8.1, 3.8.6, 3.8.7 | hierarchy | Three layers with what each gives up written on it: the CLI in `-p` mode (process isolation, the same binary engineers use interactively, no SDK version coupling — gives up in-process control), the Agent SDK in TypeScript/Python (`resolveSettings()`, `managedSettings`, `parentSettingsBehavior`, an SDK session counts as trusted), the raw Messages API with your own loop (`model`, `system`, `messages[]`, `tools[]`, `max_tokens`, `tool_use`/`tool_result`, cache breakpoints — gives up everything the harness did for you). A Java lane beneath: no first-party Java SDK, so `HttpClient` against the API or `ProcessBuilder` around the CLI |
| D-85 | An agent call is a remote dependency | 3.8.8, 4.5.5 | hierarchy | A caller box and a `claude -p` box with the network-shaped boundary between them, wrapped in five labelled rings: timeout, retry with backoff, idempotency, circuit breaker, bulkhead on concurrency. Each ring annotated with the concrete mechanism on this dependency — the wall-clock kill, the bounded retry that keeps the last envelope, a session id as the idempotency key, the failure-rate trip, the `Semaphore` permit count. An annotation: the reader already knows this material; it applies unchanged |
| D-86 | The six orchestration shapes | 3.9.1, 3.9.11 | hierarchy | Six labelled shapes drawn as small structural sketches: single session, subagent, fan-out, pipeline, team, workflow. Each with the one condition that makes it the right choice and the symptom of reaching for it too early — more agents than the task warrants, coordination costing more than the work, a fan-out whose join is the bottleneck |
| D-87 | Fan-out with a join, and the file boundary | 3.9.2, 2.1.21, 3.9.12 | step-sequence, 3 frames | Frame 1: one parent dispatching N independent tasks, each with its own disjoint output path named. Frame 2: the agents running concurrently, each writing only its own path, each returning status + a few findings + a path rather than a data payload in the message body. Frame 3: the join reading the N files and aggregating. The concurrency ceiling (20 concurrent, depth 3) labelled |
| D-88 | A pipeline where no stage writes its own input | 3.9.3, 3.9.4 | step-sequence, 5 frames | The five stages of this repository's own per-topic pipeline as the worked example: `topic-enhancer-agent` → `prompt-builder` → `notes-generator` → `gaps-analyzer-agent` → `understanding-book-keeper`. Each stage box names the file it reads and the file it writes, with the read and write paths visibly different. A crossed-out edge from a stage back into its own input labelled "never write across lanes". A terminal node: the hard stop when a prerequisite is missing |
| D-89 | Prose executor versus deterministic conductor | 3.9.5, 3.9.6, 3.9.7 | before-after | Left, `/run-harness`: a prose executor, the model reading the playbook and deciding what comes next. Right, `/run-conductor`: `conductor advance` returning the routing decision from folded run state in `features/<slug>/state/harness.db`. The two labelled "not interchangeable". A panel: a `--resume-at <stage>` flag rejected rather than approximated, with the stated reason. A second panel: `progress-verifier` scoring against the versioned `control-plane/judge-rubrics/progress-verifier.yaml` and emitting one verdict line |
| D-90 | The calibration loop | 3.9.9, 3.9.10, 3.9.8 | timeline | A cycle on one axis: sessions run → transcripts mined for recurring friction → signals grouped and coded against `feedback-signal.yaml`'s `failure_code` vocabulary and `severity_map.yaml` → deduped against the `filed-bugs.yaml` ledger → **a human confirms and files** → a prompt or script changes → the eval suites (`harness/evals/code-to-commit`, `harness/evals/seeded-defects`, `claude plugin eval`) measure whether it got better → back to the start. The human-confirmation step drawn as a gate, not a step. A side note on continuation checkpoints and the progressing-versus-stalled decision |
| D-91 | Evidence ranked by strength | 3.10.8, 3.10.2, 2.7.7 | table | Rows from strongest to weakest: a re-run of the published artefact in its published form, a passing test, a clean compile, a real transcript with the command that produced it, a diff you read line by line, a regex over a file, a structural check, the agent's own claim of success. Columns: what it proves, what it cannot catch, and the specific defect class in this repository that only the top row found (code that no longer produced the transcript printed beneath it, invented values that compiled, a repro returning the opposite of its claim, run-specific numbers published as constants). A final row for "a derived figure presented as a measurement", marked as not evidence at all |
| D-92 | The checker that switched itself off | 3.10.3, 3.10.4, 3.10.5, 3.10.6, 3.10.7 | step-sequence, 4 frames | Frame 1: one generated file containing a literal NUL byte. Frame 2: `file` classifying it as `data`. Frame 3: grep returning *nothing* — not a mismatch, nothing — so every text check silently skipped it. Frame 4: the gate reporting success over an unchecked file. The fix drawn as a first stage: assert text-ness before any grep-based gate. An annotation panel with the four sibling laws: certify from final state never from a pre-write computation; pin the harness beside the digest; never let a status row point at a missing path; a closed lane is not a verified lane |
| D-93 | Review capacity is the throughput ceiling | 3.10.11, 2.9.11 | cost-curve | X axis agent throughput in diffs per day, Y axis two curves: what the agents can produce (rising) and what the humans can genuinely review (flat, with the per-diff review minutes and the available engineer-hours written as arithmetic and labelled derived). The crossing point marked as the real ceiling. An annotation: adding agents past this point adds unreviewed diffs, not velocity |

## PART 4 diagrams (D-94 … D-99)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-94 | The `.claude` folder built in §4.1 | 4.1.1, 4.1.2, 4.1.3, 4.1.4 | hierarchy | The finished tree for the Spring Boot service: `CLAUDE.md` under 100 lines, `.claude/rules/<name>.md` with its `paths:` glob, `.claude/skills/<name>/SKILL.md`, `.claude/settings.json`, `.claude/settings.local.json`. Each node annotated with what moved into it and why. A `/context` delta panel with the before and after token figures from §4.1.2 — measured if the command was run, otherwise labelled "not measured here" with the command named — and the one key `settings.local.json` overrides marked as the winner |
| D-95 | Four hooks on the lifecycle they fire on | 4.2.1, 4.2.2, 4.2.3, 4.2.4 | timeline | One session axis with four marks, each naming the real script and what it does: `SessionStart` → `branch-context.sh` injecting branch, dirty-file count and failing-test count as tagged advisory lines; `PreToolUse` on `Bash` → `block-destructive-bash.sh` returning `hookSpecificOutput.permissionDecision: "deny"` with a `permissionDecisionReason`; `PostToolUse` on `Edit\|Write` → `format-on-edit.sh` reading `tool_input.file_path` from stdin via `jq`; `Stop` → `require-green-build.sh` returning **top-level `decision: "block"` with a required `reason`** to keep Claude working. Each mark labelled with its exit-code posture (`set +e` / `exit 0` for advisory, non-zero for blocking) and the field level it uses (top-level versus nested). The `Stop` mark carries the four-minute-build warning plus `stop_hook_active` and the 8-continuation cap. A crossed-out label on the `Stop` mark reading `continue: true` — the field that does not exist |
| D-96 | `ClaudeRunner` and the process boundary | 4.5.1, 4.5.2, 4.5.3, 4.5.4, 4.5.5 | hierarchy | The Java side: `ClaudeRunner`, the `ClaudeEnvelope` record with its fields, the distinct exception types for the three ceilings, the `Semaphore` bulkhead, the bounded retry holding the last parsed error envelope. The process boundary drawn as a hard line. The other side: the assembled `claude -p` command line with every flag visible — `--output-format json`, `--max-turns`, `--max-budget-usd`, `--settings <absolute path>`, `--agent`, `--permission-mode`. Arrows for stdout, stderr and the exit code coming back, and the 500-character unparseable-input snippet captured on the parse-failure path |
| D-97 | The two-stage pipeline over `ClaudeRunner` | 4.5.6, 4.5.7 | step-sequence, 3 frames | Frame 1: stage 1 running, reading its input path, writing its output file — the two paths visibly different. Frame 2: stage 2 running, reading stage 1's output, writing its own — again visibly different, so stage 2 is independently re-runnable. Frame 3: stage 2 re-run alone, producing the same result, with stage 1 untouched. A cost panel beneath: per-stage tokens and dollars read out of each envelope, referenced to the `## Pricing basis` note rather than restating a price |
| D-98 | The plugin from §4.6 and its marketplace | 4.6.1, 4.6.3, 4.6.4, 4.6.5 | hierarchy | The packaged plugin: `.claude-plugin/plugin.json` with `name`, `version` and `dependencies` filled in, plus `skills/`, `agents/`, `hooks/hooks.json` moved from `.claude/`. The local marketplace with its `.claude-plugin/marketplace.json` and `plugins[]` entry. Edges for the install path: `/plugin marketplace add`, `/plugin install`, `/reload-plugins`, and `--plugin-dir` for the pre-publish test. A version-bump panel showing the installed copy updating only after `version` changes, and an unresolved-dependency panel showing the `claude plugin list --json` `errors` array |
| D-99 | `verify.sh` gate order — text-ness first | 4.7.1, 4.7.2, 4.7.3, 3.10.3 | flowchart | The script from entry to exit code. Gate 1: assert every target file is text, failing loudly if not — drawn first and labelled with why. Gate 2: the structural checks. Gate 3: the index-integrity checks — every file on disk mentioned in the index, every index row pointing at an existing file, every Markdown link resolving. Gate 4: re-run every fenced listing and compare against the printed output. Each gate branching to a loud named failure rather than a skip. Two terminals annotated with where they belong: the `Stop` hook for fast local gates, the CI job for slow ones |

---

# OUTPUT CONTRACT

## Exact files to write

All under `src/notes/detailed/21-ai-for-coding/`. Create the directory and every subdirectory. Write
every file listed. The layout is **subject-major**: one folder per subject, files within it running
BASICS → INTERMEDIATE → INTERNALS.

**124 rows. Projected total ≈ 49,000–52,000 lines.**

The plan is deliberately fine-grained, and the granularity is measured rather than guessed. The
previous run of this prompt planned 61 rows at ≈23,200 lines and **landed 111 files and 47,143 lines**
— because under this prompt's obligations (the six-link chain, complete code, a `**Pitfall:**` for
every wrong belief, a prove step and a cost note per `[BUILD]`) the measured density is **≈45–55
lines of body per leaf**, and the mandated per-file closing sections (`## Pitfalls`, `## Cheat sheet`,
`## Self-test`, `## Open questions`, header, footer) add roughly another 100–150 lines per file on
top. **Every row of 8 or more leaves in the old plan overran its estimate or had to be split
mid-run.**

So the plan below holds to a hard rule you must also hold to when you split further:

- **≤ 5 leaves per file** anywhere in PARTs 0–3 and 5.
- **≤ 3 leaves per file** in PART 4, because a `[BUILD]` leaf carries an artefact, a prove step, a
  cost note and often a Diff-vs-the-real-one row set.
- Target 300–500 lines per note file; **600 is the hard split**. Splitting always beats cutting.
- If a file needs splitting, add `-a` / `-b` suffixes, register both in `00-index.md`, and **re-derive
  every cross-reference table that named the pre-split filename.** A stale filename in a table is a
  broken index even when no link is broken.

### PART 0 — written and reviewed first (11 files, 46 leaves)

| File | Leaves | Count | Est. lines |
|---|---|---|---|
| `00-index.md` | The reading map, written first: one row per file below with its syllabus sections, leaf ranges, diagram ids, status and target version; the 477 total; the `## Pricing basis` note; and an explicit statement that the PART 0 five-question gate was applied and passed | — | 350 |
| `ground-zero/01-basics-what-a-model-is.md` | 0.1.1–0.1.5 | 5 | 380 |
| `ground-zero/02-basics-nondeterminism-and-confabulation.md` | 0.1.6–0.1.9 | 4 | 340 |
| `ground-zero/03-basics-model-family-and-the-word-agent.md` | 0.1.10–0.1.12 | 3 | 300 |
| `ground-zero/04-basics-the-context-window.md` | 0.2.1–0.2.5 | 5 | 400 |
| `ground-zero/05-basics-conversation-cost-and-caching.md` | 0.2.6–0.2.9 | 4 | 360 |
| `ground-zero/06-basics-the-budget-framing.md` | 0.2.10–0.2.12 | 3 | 300 |
| `ground-zero/07-basics-the-agent-loop.md` | 0.3.1–0.3.5 | 5 | 400 |
| `ground-zero/08-basics-tool-choice-and-a-real-loop.md` | 0.3.6–0.3.9 | 4 | 360 |
| `ground-zero/09-basics-thinking-the-harness-and-the-sdk.md` | 0.3.10–0.3.12 | 3 | 300 |
| `ground-zero/10-basics-install-and-diagnostics.md` | 0.4.1–0.4.5 | 5 | 400 |
| `ground-zero/11-basics-checkpoints-sessions-and-a-checklist.md` | 0.4.6–0.4.10 | 5 | 400 |

### PART 1 — BASICS (27 files, 125 leaves)

| File | Leaves | Count | Est. lines |
|---|---|---|---|
| `claude-folder/01-basics-configuration-as-code.md` | 1.1.1–1.1.5 | 5 | 360 |
| `claude-folder/02-basics-the-discovery-walk-and-a-real-tree.md` | 1.1.6–1.1.9 | 4 | 340 |
| `settings/01-basics-the-four-files-and-precedence.md` | 1.2.1–1.2.4 | 4 | 380 |
| `settings/02-basics-where-the-local-file-lands.md` | 1.2.5–1.2.8 | 4 | 340 |
| `settings/03-key-groups-and-the-first-dozen-keys.md` | 1.2.9–1.2.12 | 4 | 380 |
| `settings/04-verifying-and-silently-ignored-keys.md` | 1.2.13–1.2.16 | 4 | 360 |
| `memory/01-basics-two-mechanisms-and-load-order.md` | 1.3.1–1.3.5 | 5 | 400 |
| `memory/02-basics-on-demand-loading-and-imports.md` | 1.3.6–1.3.10 | 5 | 400 |
| `memory/03-cost-and-instructions-that-land.md` | 1.3.11–1.3.15 | 5 | 400 |
| `memory/04-path-globs-and-org-scope.md` | 1.3.16–1.3.20 | 5 | 380 |
| `memory/05-auto-memory.md` | 1.3.21–1.3.25 | 5 | 400 |
| `memory/06-compaction-diagnostics-and-a-real-setup.md` | 1.3.26–1.3.29 | 4 | 380 |
| `permissions/01-basics-who-enforces-and-the-three-lists.md` | 1.4.1–1.4.5 | 5 | 420 |
| `permissions/02-basics-bash-specifiers-and-wildcards.md` | 1.4.6–1.4.10 | 5 | 420 |
| `permissions/03-wrappers-compounds-and-the-read-only-set.md` | 1.4.11–1.4.15 | 5 | 420 |
| `permissions/04-path-rules-and-which-tools-consult-them.md` | 1.4.16–1.4.20 | 5 | 400 |
| `permissions/05-mcp-agent-cd-and-parameter-rules.md` | 1.4.21–1.4.25 | 5 | 400 |
| `permissions/06-accept-edits-and-auto-mode.md` | 1.4.26, 1.4.26a, 1.4.26b, 1.4.27, 1.4.28 | 5 | 420 |
| `permissions/07-bypass-directories-and-cd.md` | 1.4.28a, 1.4.29–1.4.32 | 5 | 400 |
| `permissions/08-workspace-trust-and-precedence.md` | 1.4.33, 1.4.34, 1.4.34a, 1.4.35, 1.4.36 | 5 | 420 |
| `permissions/09-inspection-sandbox-and-a-real-block.md` | 1.4.37–1.4.41 | 5 | 420 |
| `skills/01-basics-commands-are-skills.md` | 1.5.1–1.5.5 | 5 | 400 |
| `skills/02-basics-the-listing-budgets-and-frontmatter.md` | 1.5.6–1.5.10 | 5 | 420 |
| `skills/03-substitution-and-dynamic-injection.md` | 1.5.11–1.5.14 | 4 | 380 |
| `skills/04-content-lifecycle-and-supporting-files.md` | 1.5.15–1.5.18 | 4 | 360 |
| `skills/05-cases-three-real-skills.md` | 1.5.19–1.5.22 | 4 | 400 |
| `skills/06-the-inventory-and-the-decision-table.md` | 1.5.23–1.5.26 | 4 | 400 |

### PART 2 — INTERMEDIATE (32 files, 142 leaves)

| File | Leaves | Count | Est. lines |
|---|---|---|---|
| `subagents/01-basics-the-context-boundary.md` | 2.1.1–2.1.5 | 5 | 420 |
| `subagents/02-basics-routing-tools-and-what-loads.md` | 2.1.6–2.1.10 | 5 | 420 |
| `subagents/03-builtins-background-and-forks.md` | 2.1.11–2.1.15 | 5 | 400 |
| `subagents/04-memory-resume-invocation-and-cost.md` | 2.1.16–2.1.20 | 5 | 400 |
| `subagents/05-cases-and-the-output-protocol.md` | 2.1.21–2.1.25 | 5 | 420 |
| `personas/01-agent-vs-append-vs-replace.md` | 2.2.1–2.2.4 | 4 | 340 |
| `personas/02-cases-and-the-wrong-choice.md` | 2.2.5–2.2.7 | 3 | 300 |
| `hooks/01-basics-what-a-hook-is-and-the-schema.md` | 2.3.1–2.3.5 | 5 | 420 |
| `hooks/02-basics-events-matchers-and-stdin.md` | 2.3.6–2.3.10 | 5 | 440 |
| `hooks/03-exit-codes-and-the-output-schema.md` | 2.3.11, 2.3.12, 2.3.13, 2.3.14, 2.3.14a | 5 | 440 |
| `hooks/04-the-stop-contract-and-its-inversion.md` | 2.3.14b, 2.3.15, 2.3.15a, 2.3.15b, 2.3.15c | 5 | 460 |
| `hooks/05-limits-sources-and-inspection.md` | 2.3.16–2.3.20 | 5 | 400 |
| `hooks/06-cases-real-hooks-and-the-reindex-incident.md` | 2.3.21–2.3.25 | 5 | 460 |
| `hooks/07-blocking-guards-and-a-build-of-three.md` | 2.3.26–2.3.28 | 3 | 360 |
| `mcp-and-lsp/01-basics-what-mcp-is.md` | 2.4.1–2.4.5 | 5 | 400 |
| `mcp-and-lsp/02-naming-cost-and-failure-modes.md` | 2.4.6–2.4.9 | 4 | 360 |
| `mcp-and-lsp/03-per-run-servers-lsp-and-a-build.md` | 2.4.10–2.4.13 | 4 | 380 |
| `plugins/01-basics-what-a-plugin-is-and-its-layout.md` | 2.5.1–2.5.5 | 5 | 400 |
| `plugins/02-versioning-namespacing-and-marketplaces.md` | 2.5.6–2.5.10 | 5 | 380 |
| `plugins/03-failure-modes-commands-and-governance.md` | 2.5.11–2.5.15 | 5 | 400 |
| `plugins/04-cases-and-the-conversion.md` | 2.5.16–2.5.20 | 5 | 420 |
| `context-economy/01-reading-context-and-the-startup-tax.md` | 2.6.1–2.6.4 | 4 | 400 |
| `context-economy/02-autocompaction-and-what-survives.md` | 2.6.5–2.6.8 | 4 | 380 |
| `context-economy/03-cache-economics-isolation-and-a-protocol.md` | 2.6.9–2.6.12 | 4 | 400 |
| `practices/01-plan-mode-and-test-first.md` | 2.7.1–2.7.4 | 4 | 380 |
| `practices/02-prompting-context-and-verification.md` | 2.7.5–2.7.8 | 4 | 360 |
| `practices/03-where-it-does-not-fit-and-a-java-walkthrough.md` | 2.7.9–2.7.12 | 4 | 420 |
| `deterministic-vs-agentic/01-the-rule-and-its-source.md` | 2.8.1–2.8.5 | 5 | 400 |
| `deterministic-vs-agentic/02-idempotence-exceptions-and-the-trap.md` | 2.8.6–2.8.9 | 4 | 360 |
| `governance/01-the-threat-model-and-the-controls.md` | 2.9.1–2.9.4 | 4 | 400 |
| `governance/02-managed-delivery-and-the-locks.md` | 2.9.5–2.9.8 | 4 | 380 |
| `governance/03-attribution-and-a-real-posture.md` | 2.9.9–2.9.11 | 3 | 360 |

### PART 3 — ADVANCED (INTERNALS) (24 files, 96 leaves)

| File | Leaves | Count | Est. lines |
|---|---|---|---|
| `request-assembly/03-internals-a-assembly-order.md` | 3.1.1–3.1.4 | 4 | 400 |
| `request-assembly/03-internals-b-listing-reminders-and-transcripts.md` | 3.1.5–3.1.8 | 4 | 400 |
| `compaction/03-internals-a-what-it-does.md` | 3.2.1–3.2.4 | 4 | 380 |
| `compaction/03-internals-b-what-is-lost-and-the-seam.md` | 3.2.5–3.2.7 | 3 | 340 |
| `permission-evaluation/03-internals-a-the-pipeline.md` | 3.3.1–3.3.4 | 4 | 420 |
| `permission-evaluation/03-internals-b-patterns-and-the-adversarial-drill.md` | 3.3.5–3.3.8 | 4 | 400 |
| `cost-model/03-internals-a-what-you-are-billed-for.md` | 3.4.1–3.4.5 | 5 | 420 |
| `cost-model/03-internals-b-ceilings-and-reading-cost-back.md` | 3.4.6–3.4.9 | 4 | 400 |
| `effort-and-routing/03-internals-a-effort-levels.md` | 3.5.1–3.5.3 | 3 | 340 |
| `effort-and-routing/03-internals-b-fallbacks-fast-mode-and-the-trap.md` | 3.5.4–3.5.6 | 3 | 320 |
| `headless/03-internals-a-the-one-shot-surface.md` | 3.6.1–3.6.5 | 5 | 420 |
| `headless/03-internals-b-flags-sessions-and-remote.md` | 3.6.6–3.6.9 | 4 | 400 |
| `headless/03-internals-c-a-real-wrapper.md` | 3.6.10–3.6.14 | 5 | 440 |
| `headless/03-internals-d-the-turn-ceiling-incident.md` | 3.6.15–3.6.18 | 4 | 400 |
| `setting-sources-incident/03-internals-a-setup-mechanism-symptom-fix.md` | 3.7.1–3.7.5 | 5 | 420 |
| `setting-sources-incident/03-internals-b-the-paper-trail-and-the-telling.md` | 3.7.6–3.7.9 | 4 | 360 |
| `sdk-and-api/03-internals-a-three-levels-and-the-api.md` | 3.8.1–3.8.4 | 4 | 400 |
| `sdk-and-api/03-internals-b-the-sdk-and-the-java-options.md` | 3.8.5–3.8.8 | 4 | 420 |
| `orchestration/03-internals-a-shapes-and-the-pipeline-rule.md` | 3.9.1–3.9.4 | 4 | 400 |
| `orchestration/03-internals-b-executors-state-and-judges.md` | 3.9.5–3.9.8 | 4 | 420 |
| `orchestration/03-internals-c-calibration-evals-and-limits.md` | 3.9.9–3.9.12 | 4 | 400 |
| `verification/03-internals-a-the-asymmetry-and-three-laws.md` | 3.10.1–3.10.4 | 4 | 420 |
| `verification/03-internals-b-four-more-laws-and-the-evidence-rank.md` | 3.10.5–3.10.8 | 4 | 400 |
| `verification/03-internals-c-automating-the-gates.md` | 3.10.9–3.10.11 | 3 | 380 |

### PART 4 — BUILD IT (15 files, 40 leaves — ≤ 3 leaves per file)

| File | Leaves | Count | Est. lines |
|---|---|---|---|
| `build-it/01-a-claude-folder-a.md` | 4.1.1–4.1.3 | 3 | 420 |
| `build-it/02-a-claude-folder-b.md` | 4.1.4–4.1.5 | 2 | 340 |
| `build-it/03-hooks-a.md` | 4.2.1–4.2.3 | 3 | 440 |
| `build-it/04-hooks-b.md` | 4.2.4–4.2.6 | 3 | 460 |
| `build-it/05-a-skill-a.md` | 4.3.1–4.3.3 | 3 | 420 |
| `build-it/06-a-skill-b.md` | 4.3.4–4.3.6 | 3 | 400 |
| `build-it/07-subagents-a.md` | 4.4.1–4.4.3 | 3 | 420 |
| `build-it/08-subagents-b.md` | 4.4.4–4.4.5 | 2 | 340 |
| `build-it/09-orchestrator-a-the-runner.md` | 4.5.1–4.5.3 | 3 | 460 |
| `build-it/10-orchestrator-b-resolution-and-resilience.md` | 4.5.4–4.5.6 | 3 | 460 |
| `build-it/11-orchestrator-c-cost-report-and-the-diff.md` | 4.5.7–4.5.8 | 2 | 380 |
| `build-it/12-a-plugin-a.md` | 4.6.1–4.6.3 | 3 | 420 |
| `build-it/13-a-plugin-b.md` | 4.6.4–4.6.6 | 3 | 400 |
| `build-it/14-verification-harness-a.md` | 4.7.1–4.7.2 | 2 | 380 |
| `build-it/15-verification-harness-b.md` | 4.7.3–4.7.4 | 2 | 360 |

### Interview, PART 5 and retention files, at the topic root (14 files, 28 leaves)

The interview wrap-ups are **pre-split** into a summary-plus-puzzles file and a Q&A file, because at
the required Q&A counts a combined file crosses 600 lines every time.

| File | Contents | Q&As | Est. lines |
|---|---|---|---|
| `90-interview-basics.md` | **PARTs 0 and 1 wrap-up**: the summary table over §0.1–§1.5 and 5 predict-the-output puzzles | — | 420 |
| `90-interview-basics-qa.md` | The PARTs 0+1 Q&As. Base 10 + 2 per subject folder beyond the fifth; PARTs 0+1 span 6 folders (`ground-zero`, `claude-folder`, `settings`, `memory`, `permissions`, `skills`) → **12** | 12 | 480 |
| `91-interview-intermediate.md` | **PART 2 wrap-up**: the summary table over §2.1–§2.9 and 5 puzzles | — | 420 |
| `91-interview-intermediate-qa.md` | 9 subject folders → **18** | 18 | 560 |
| `92-interview-internals.md` | **PART 3 wrap-up**: the summary table over §3.1–§3.10, 5 puzzles, **then the topic-wide flat `## Atomic concept checklist` covering all six parts** | — | 560 |
| `92-interview-internals-qa.md` | 10 subject folders → **20** | 20 | 580 |
| `93-interview-build-it.md` | **PART 4 wrap-up**: the summary table over §4.1–§4.7, 10 Q&As, 5 puzzles | 10 | 480 |
| `94-interview-questions-a.md` | §5.1.1–5.1.4, each question with its full answer shape at speaking length | — | 380 |
| `94-interview-questions-b.md` | §5.1.5–5.1.8, same treatment | — | 380 |
| `94-interview-questions-c.md` | §5.1.9–5.1.12, same treatment | — | 400 |
| `94-interview-questions-d.md` | §5.1.13–5.1.16, same treatment. **Ends with PART 5's own summary table, 10 Q&As and 5 puzzles** | 10 | 480 |
| `95-trap-index.md` | §5.2.1–5.2.4: the consolidated trap table (expect well over 100 rows, not 45), the version-stale table, the top five, and the incident index with **ten operational incidents plus three documentation corrections**, one line each with its cost and its law | — | 480 |
| `96-drills-a.md` | §5.3.1–5.3.4: the pointer to the checklist, the numbers drill, the precedence drill, the mechanism drill | — | 400 |
| `96-drills-b.md` | §5.3.5–5.3.8: the config-reading drill, the cost drill, the explain-it-to-a-colleague test, the review schedule | — | 360 |

Diagrams go in `src/notes/detailed/21-ai-for-coding/diagrams/`, flat, named `D-NN-short-slug.svg`
with lettered frame files as `D-NNx-short-slug.svg`.

**On the atomic concept checklist:** it lives at the end of `92-interview-internals.md`, not at the
end of the last file, because that is the path downstream tooling parses. It covers **all six
parts** — PART 0 through PART 5 — sorted by subject folder and then by the order the concept appears
in that folder. §5.3.1 in `96-drills-a.md` must therefore be one line pointing at it, not a second
copy. A duplicated checklist is a defect.

If any single file becomes unwieldy, **split it further** (`hooks/06-cases-real-hooks-a.md`,
`hooks/06-cases-real-hooks-b.md`, …), register the new files in `00-index.md`, and re-derive every
table that named the old filename. Splitting is always preferred to cutting content. Never merge
files to reduce the count.

## The cost-provenance rule

None of the nine documentation pages this prompt permits carries pricing. That is a real constraint,
and in the previous run it forced every cost leaf either to hedge or to publish an unsourced figure.
Here is how you discharge it instead.

1. **There is exactly one pricing source**, and it is the Claude API pricing page named in
   `# REFERENCES`. Read it once. Quote the list prices you need.
2. **`00-index.md` carries a `## Pricing basis` note** stating: the page URL, the date you read it,
   the per-million-token list prices you took from it for input, output, cache write and cache read
   on each model you cite, and one sentence on what a contracted rate (`modelPricing`) would change.
3. **Every other file references that note** — "per the `## Pricing basis` note in `00-index.md`" —
   rather than restating a price. A per-file restatement is how a stale figure gets nine copies.
4. **Every dollar figure other than a quoted list price is derived, and says so**: label it
   `**Derived:**`, show the arithmetic, and give the date of the pricing basis it was derived from.
   The provenance sentence is: *the mechanism is from the documentation; the arithmetic is ours and
   is shown.*
5. **If a price you need is not on that page, do not estimate it.** Mark the claim
   `**Unverified:**`, say what you could not find, and record it in `## Open questions`.
6. This rule binds §0.1.11, §0.2.2, §0.2.8, §2.1.19, §2.6.10, §3.4.1–3.4.9, §4.5.7, §5.1.11, every
   `[BUILD]` "what this costs" note, and diagrams D-04, D-08, D-46, D-63, D-71, D-76, D-77 and
   D-97.

## Required header on every file except `00-index.md`

```
# 21 AI for Coding — <subject> — <tier> (<syllabus sections covered>)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part <n> of 6** | [Index](../00-index.md)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

Files at the topic root (`90`–`96`) link the index as `[Index](00-index.md)`. The first file in the
set omits `Previous:` entirely and the last omits `Next:` — never emit a link to a file that does not
exist, and never write `Previous: none`.

## Required footer on every file except `00-index.md`

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.4.26, 1.4.26a, 1.4.26b, 1.4.27, 1.4.28> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-33, D-34, …>
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** <count>
```

Lettered leaves are listed by their lettered number. A range written `1.4.26–1.4.28` silently drops
`1.4.26a`, `1.4.26b` and is a coverage defect.

## Required closing sections on every note file

Every file except `00-index.md` and the `90`–`96` interview files ends with, in this order:

1. `## Pitfalls` — wrong-then-right, one entry per pitfall: the belief in action and the surprising
   outcome, then the configuration or command that actually gets the guarantee, then
   **Why people believe it:**.
2. `## Cheat sheet` — a one-screen table, recallable at a glance. No prose.
3. `## Self-test` — 5 to 10 questions, each answer folded below it in a `<details><summary>Answer
   </summary>` block, with the full answer rather than a hint.
4. `## Open questions` — every claim marked `**Unverified:**` in the body, every "not measured here"
   item with the command the reader should run, or the single line `None.`
5. The footer above.

---

# SELF-VERIFY BEFORE REPORTING DONE

Run this checklist against your own output. Do not report completion until every box is genuinely
satisfied.

**Read this first.** The previous run of this prompt **passed its own self-verify while shipping two
orphan files, three stale cross-reference tables naming 36 filenames that did not exist, and eight
broken Markdown links.** It passed because the checks it ran were "no broken embeds" and "no
`planned` status rows", and neither of those is the same claim as *the index describes the set on
disk*. The index-integrity block below exists to close exactly that hole, and it is not satisfied by
reasoning about it — you run the three greps.

**Sequencing and the PART 0 gate**
- [ ] The eleven `ground-zero/` files were written and reviewed before any PART 1 file was drafted.
- [ ] PART 0 contains no "as you know", "obviously", "of course you're familiar with" or "recall
      that", and no term used before it is defined.
- [ ] A level-zero reader finishing PART 0 can define a token, a context window, a tool call, a
      turn, and an agent from memory. `00-index.md` records that the gate was applied and passed.

**Index integrity — run all three greps, paste the results into your report**
- [ ] **Grep 1, no orphans.** Every `.md` and `.svg` file on disk under
      `src/notes/detailed/21-ai-for-coding/` is mentioned at least once in `00-index.md`. List
      the files on disk, grep each basename against the index, and report zero misses.
- [ ] **Grep 2, no phantom rows.** Every path named in a status row of `00-index.md` exists on
      disk. Report zero misses.
- [ ] **Grep 3, no broken links.** Every Markdown link and image embed in every file resolves to an
      existing path. Report zero misses.
- [ ] Every cross-reference table anywhere in the set names only filenames that exist. **If a file
      was split after a table was written, the table was re-derived** — or it is explicitly headed
      as a record of the pre-split layout. A stale filename in a table is a broken index even when
      no link is broken.
- [ ] `00-index.md` reports every diagram file produced, including every lettered frame file, and
      the count of SVG files as well as the count of `D-NN` ids.
- [ ] No `planned`, `TODO` or `in progress` status row remains. Note explicitly that this check
      alone does **not** satisfy the three greps above.

**Evidence policy**
- [ ] Every `[PROVE]` and `[BUILD]` prove step either pastes a **real transcript with the exact
      command that produced it**, or says **"not measured here"** at the point of the claim, gives
      the command the reader should run, and records the item in that file's `## Open questions`.
- [ ] No fenced block anywhere is styled as command output unless a command actually produced it.
- [ ] No derived figure sits in the visual position a measured one belongs. Every derived number is
      labelled derived, shows its arithmetic, and carries its basis.
- [ ] Every `[BUILD]` artefact is shipped complete even where its proof could not be run.

**Cost provenance**
- [ ] `00-index.md` carries a `## Pricing basis` note with the pricing page URL, the date read, and
      the list prices taken from it.
- [ ] No other file restates a per-token price; each references the `## Pricing basis` note.
- [ ] Every dollar figure is either a quoted list price with its date or is labelled `**Derived:**`
      with its arithmetic shown and its basis date given.
- [ ] Nothing needed and not found on the pricing page was estimated; each such gap is
      `**Unverified:**` and in `## Open questions`.

**Coverage**
- [ ] All 477 syllabus leaves appear in the notes, or are listed in a `## Deferred` block with a
      leaf number and a reason.
- [ ] All nine lettered leaves — 1.4.26a, 1.4.26b, 1.4.28a, 1.4.34a, 2.3.14a, 2.3.14b, 2.3.15a,
      2.3.15b, 2.3.15c — are covered and are named individually in a footer, not swallowed by a
      range.
- [ ] Every file's footer lists the leaves it covers, and the union across all files is all 477.
- [ ] Every file listed in the OUTPUT CONTRACT exists, with the required header, footer and closing
      sections.
- [ ] No note file covers more than 5 leaves; no PART 4 file covers more than 3.

**Format**
- [ ] Every note file is Markdown (`.md`).
- [ ] No file was cut short for length. No "and so on", no "similar to the above", no
      deferred-for-space. No file exceeds 600 lines unsplit.
- [ ] No ASCII art anywhere. No inline `<svg>` anywhere.
- [ ] All 99 manifest ids are accounted for. The 84 SVG-type ids exist as standalone `.svg` files in
      `diagrams/`, each embedded with a Markdown image reference at the point of explanation and
      captioned with its `D-NN` id in a form a `D-[0-9]{2}` grep resolves.
- [ ] The 15 `table`-type ids (D-02, D-04, D-16, D-17, D-22, D-30, D-32, D-33, D-45, D-48, D-51,
      D-68, D-76, D-78, D-91) are rendered as Markdown tables with no SVG written, and the `D-NN`
      id still appears at that point in the prose.
- [ ] Every SVG shows every element named in its `Must show` cell, and meets the
      `notes-generator` `## Diagram spec` in full — `viewBox` with no fixed width or height, opaque
      backdrop rect, orthogonal routing only, legend, 10.5px text floor, no off-file dependency —
      and was rendered and looked at before being reported.
- [ ] Where the manifest specified a frame count, that many labelled frames or panels exist and
      every file produced is reported in `00-index.md`.
- [ ] Every comparison of three or more things is a table.
- [ ] No emojis. No filler openers.

**Domain and grounding**
- [ ] Every `[CASE]` leaf cites a real sdlc-harness file path and quotes its real text verbatim in a
      fenced block, and then explains it. Nothing paraphrased, nothing reconstructed.
- [ ] Every quoted sdlc-harness file was actually read before being quoted.
- [ ] **Every count was re-derived by listing the directory at write time** — the nine
      `playwright-cli` reference files, the nine `.claude/commands/` files, the fifteen
      `bootstrap-*.sh` plus three `triage-*.sh` under `scripts/`, the four `permissions.allow`
      entries, the four `enabledPlugins`. Where the disk disagrees with this prompt, the notes
      follow the disk and say so.
- [ ] `playwright-cli` is described as a **repo-root** skill at `.claude/skills/playwright-cli/`,
      not a plugin skill.
- [ ] Nothing was written to the sdlc-harness repository.
- [ ] Where a path or a claim in a leaf did not match the repo, the divergence is stated inline and
      recorded in `## Open questions` rather than invented around.
- [ ] No `Foo`, `Bar`, `Baz`, `my-agent`, `my-skill`, `thing1`, `MyClass`, `doSomething`,
      `test-agent`, `example-hook` or `Dog extends Animal` anywhere — in prose, in JSON, in shell,
      in frontmatter, in Java, or in a diagram label.
- [ ] No invented settings key, flag, hook event, frontmatter field or numeric limit.

**Per concept**
- [ ] Every concept follows `Concept → Why it exists → How it works → SVG → Code → Gotcha`, in that
      order, with any inapplicable link explicitly noted in one line rather than dropped.
- [ ] Every JSON block is valid and complete with its parent keys present, and carries no comments.
- [ ] Every hook-output JSON block makes the field level unambiguous — top-level versus nested
      inside `hookSpecificOutput`.
- [ ] Every shell script is complete with its shebang and an explicit failure posture.
- [ ] Every `claude` invocation shows every flag it needs.
- [ ] Every Java snippet is complete and compiles as written, minus only imports, package
      declarations and pointless `main` scaffolding, and is Java 21 idiomatic. No `...`, no
      "implementation omitted", no pseudo-code.
- [ ] Only the three callout markers `**Pitfall:**`, `**Insight:**`, `**Interview:**` are used.

**Per tag**
- [ ] Every `[ZERO]` leaf defines every term it uses, in the leaf.
- [ ] Every `[DOC]` leaf quotes the documentation and names the page, and was re-verified against
      the raw `.md` of that page immediately before being written.
- [ ] Every `[RESEARCH]` leaf was re-verified the same way, or its uncertainty is stated inline as
      `**Unverified:**` and recorded in `## Open questions`.
- [ ] Every `[VERSION]` leaf states its version inline at the point of the claim. Roughly 20 leaves.
- [ ] Every `[TRAP]` leaf carries a `**Pitfall:**` with wrong belief, symptom and fix — and the
      total number of `**Pitfall:**` entries across the set **exceeds** the ~45 tag count, because
      every wrong belief a leaf surfaces gets one.
- [ ] The incident treatment matches `## The incident roster`: **ten operational incidents**, each
      with a cost as a number (the 100+ GB reindex, the lane-collision overwrite, the 500-character
      snippet finding, the $5.16 / 80-turn run, the `--setting-sources` block, the
      re-run-published-artefacts finding, the NUL-byte checker, the md5-over-a-patched-harness /
      unpinned-digest event counted **once**, the missing-path status row, the closed-lane
      contradictions) — **plus three documentation corrections** (§1.4.28a, §1.4.34a, §2.3.15a)
      reported separately and given no invented dollar figure.
- [ ] Every `[NUM]` leaf states the number or the arithmetic explicitly. Roughly 60.
- [ ] Every `[PROVE]` leaf works the argument through or shows the observed result under the
      evidence policy. Roughly 45.
- [ ] Every `[BUILD]` leaf ships a complete runnable artefact, then a prove step under the evidence
      policy, then a "what this costs" note under the cost-provenance rule. Roughly 60.
- [ ] Every `[JAVA]` leaf lands in Java 21 / Spring Boot 3.x — a precise analogy with the place it
      breaks stated, or real compiling code. Roughly 15.
- [ ] Every `[X-REF nn]` leaf has a self-contained mechanism paragraph before the pointer, and
      0.3.12's `[X-REF 21]` points forward to §3.8 inside this guide rather than at a sibling topic.
- [ ] Leaf 2.2.6's `[SOURCE-EQUIV]` is discharged as a `[CASE]`: the real function quoted from
      `harness/src/harness/engine/agent.py` with its regex read line by line.

**The five known-defective claims**
- [ ] **Hook output schema.** The three kinds of field are stated and kept distinct; `Stop` and
      `SubagentStop` keep Claude working via top-level `decision: "block"` with a **required**
      `reason`; `hookSpecificOutput.additionalContext` is given as the third path with its
      `Stop hook feedback` label; exit 2 routes as `reason`; `continue: false` is stated as a
      universal kill switch meaning the opposite of "keep going" and as taking precedence over any
      decision field; `stopReason` goes to the user, not to Claude; `suppressOutput` is stated as
      accepted and inert; the 10,000-character cap is stated; `stop_hook_active` and the
      8-consecutive-continuation cap are stated. **The strings `continueReason`,
      `decision: "continue"` and `hookSpecificOutput.continue` appear nowhere except as explicitly
      crossed-out non-existent fields.** §4.2.4 uses `decision: "block"`.
- [ ] **`bypassPermissions`.** Stated as **not** protecting `.git` or `.claude`; protected-path
      writes allowed; what it does still refuse enumerated exactly; the false claim carried as a
      `**Pitfall:**` at §1.4.28a.
- [ ] **Trust in `-p`/SDK sessions.** Stated as **not applying** an untrusted folder's committed
      `allow`/`additionalDirectories`, with the stderr warning; "counts as accepted" attached only
      to the `settings.local.json` tracked/untracked check; the real risk given as stickiness —
      keyed per repository-root path, never re-checked when a commit widens the ruleset.
- [ ] **`allowed-tools`.** Stated as pre-approval for the invoking turn only, `disallowed-tools` as
      the field that restricts, wrong belief carried as a `**Pitfall:**` at §1.5.8.
- [ ] **Inventory and precedence.** All **six** permission modes at §1.4.25; `acceptEdits` naming
      `rm`, `rmdir` and `sed` and flagged as auto-approving deletion; the `auto` classifier on
      **Sonnet 5** with **3-consecutive / 20-total** thresholds; managed settings **above** the
      command line at §1.2.2 with §1.2.3 denying both "more specific wins" and "command line always
      wins"; `/doctor` and `/rewind` tagged as **skills** and `/run` as a **built-in** at §1.5.23;
      `skillListingMaxDescChars` (per-entry, 1,536 chars) and `skillListingBudgetFraction` (pool,
      ~1% of window) treated as two different numbers at §1.5.6, D-36 and D-71.

**PART 4**
- [ ] All 40 leaves ship a working artefact, a prove step and a cost note.
- [ ] Every §4.x section that has a real equivalent in the sdlc-harness ends with a
      **Diff vs the real one** table — §4.2.6, §4.3.6, §4.4.5, §4.5.8, §4.6.6 at minimum.
- [ ] §4.5 builds one `ClaudeRunner` cumulatively across all eight leaves, so the code at 4.5.5 is
      the code from 4.5.1 with the additions, not a fresh unrelated class.

**Per part**
- [ ] `90-interview-basics.md` + `90-interview-basics-qa.md` close PARTs 0 and 1 with a summary
      table, **12** Q&As with full spoken-length model answers, and 5 predict-the-output puzzles,
      each puzzle carrying a complete configuration, the action, the actual outcome and why.
- [ ] `91-interview-intermediate.md` + `-qa.md` do the same for PART 2 with **18** Q&As.
- [ ] `92-interview-internals.md` + `-qa.md` do the same for PART 3 with **20** Q&As.
- [ ] `93-interview-build-it.md` does the same for PART 4 with **10** Q&As.
- [ ] `94-interview-questions-d.md` closes PART 5 with its summary table, **10** Q&As and 5 puzzles.
- [ ] All 16 questions of §5.1 are answered with the answer shape at speaking length, not a hint,
      across `94-interview-questions-a.md` through `-d.md`.

**Closing**
- [ ] `92-interview-internals.md` ends with a flat `## Atomic concept checklist`, one bullet per
      distinct concept across all six parts, no nesting, no headings inside it, format exactly
      `- <concept name>`.
- [ ] §5.3.1 in `96-drills-a.md` points at that checklist and does not duplicate it.
- [ ] `95-trap-index.md` carries the consolidated trap table, the version-stale table with both
      versions per row, the top five, and the incident index with a cost and a law per line under
      the ten-plus-three split.
- [ ] `96-drills-a.md` and `96-drills-b.md` between them carry all seven drills including the
      fourteen-number drill of §5.3.2.

---

# REFERENCES

## Primary — the documentation

The syllabus was built against `https://code.claude.com/docs/en/` on 2026-08-30. **Re-verify before
writing any `[DOC]` or `[RESEARCH]` leaf, and fetch the raw Markdown** —
`curl -sL https://code.claude.com/docs/en/<page>.md` — for anything with nesting in it. The rendered
page flattens a nested field into a top-level one, and that flattening is the direct cause of the
hook-schema error this revision corrects. The pages the syllabus draws on, by the area they own:

- `https://code.claude.com/docs/en/settings` — the settings files, what each reaches, where the local
  file lands, the key groups
- `https://code.claude.com/docs/en/settings-reference` — every key by name and its accepted values;
  the page to check a spelling against before printing it
- `https://code.claude.com/docs/en/permissions` — the three rule lists and their evaluation order,
  rule syntax, Bash matching and wrapper stripping, the read-only command set, gitignore-pattern
  path rules, the six modes, working directories, workspace trust, sandboxing
- `https://code.claude.com/docs/en/hooks` — the event catalogue, matcher semantics, the stdin
  payloads, exit-code semantics, the JSON output contract, the configuration sources. **Fetch
  `hooks.md` raw.** This page owns §2.3.14–2.3.15c and the field-level distinction that three write
  attempts got wrong from the rendered version
- `https://code.claude.com/docs/en/sub-agents` — definition locations and precedence, every
  frontmatter field, what loads and what does not at startup, the built-ins, forks, the limits
- `https://code.claude.com/docs/en/skills` — the commands-are-skills merge, the four locations and
  the conflict order, progressive disclosure and both listing budgets, every frontmatter field,
  substitutions and dynamic injection, the content lifecycle and the compaction re-attachment budget,
  the built-in-versus-bundled-skill inventory
- `https://code.claude.com/docs/en/memory` — the `CLAUDE.md` locations and load order, imports,
  `.claude/rules/` and path-scoped rules, `claudeMdExcludes`, auto memory and its storage
- `https://code.claude.com/docs/en/plugins` — the directory layout, `plugin.json`, namespacing,
  marketplaces, cross-marketplace dependencies, the governance keys
- `https://code.claude.com/docs/en/cli-reference` — every flag, the `-p` output and input formats,
  the JSON envelope, session control, `setup-token`, background and remote execution

## Primary — pricing

- `https://www.anthropic.com/pricing#api` — the Claude API pricing page. **This is the single source
  for every price in the guide**, and the only source permitted for one. None of the nine
  documentation pages above carries pricing, which is why the cost-provenance rule in the
  `# OUTPUT CONTRACT` exists: read this page once, record its list prices and the date in the
  `## Pricing basis` note in `00-index.md`, and derive everything else from that one basis with the
  arithmetic shown. If a figure you need is not on this page, mark it `**Unverified:**` — do not
  estimate it, and do not substitute a remembered number.

## Primary — the grounding repository

Read-only, at `/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness`. The
file-by-file map is the table in `## The example domain — the sdlc-harness repo` in `# CONTEXT`
above; it is the authoritative list for this topic and is not repeated here. Every count in it is
re-derived from the disk at write time.

## Sibling guides

- `src/topics/13-web-security.md` — the threat model and prompt-injection framing §2.9 points at
- `src/topics/17-git-craft.md` — review discipline and small diffs, for §2.7.4
- `src/topics/12-api-design.md` — the remote-dependency contract, for §3.8.8
- `src/topics/05-multithreading-concurrency.md` — the bulkhead and retry material behind §4.5.5
- `src/topics/20-observability-operations.md` — the cost and telemetry framing for §3.4 and §3.9.9
- `src/topics/16-testing.md` — the failing-test-as-specification argument for §2.7.3 and §4.7.4

## Sources the syllabus did not record

The syllabus for this topic has **no `## Sources consulted` section**. Every documentation citation
above is derived from the doc pages the syllabus names inline in its `[DOC]` leaves and from the
repository paths its `[CASE]` leaves cite. The pricing page is added here because the cost leaves
require a source and the syllabus supplied none. There is no additional reading list to carry
forward, and no URL in this prompt was invented.
