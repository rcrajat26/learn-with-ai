# 21 AI for Coding (Claude Code) — the file plan

**Target version: Claude Code v2.1.2xx (August 2026).**
**Source prompt:** `src/metadata/prompts/21-ai-for-coding-prompt.md`
**Prompt content hash (md5):** `16e4863a0d6d797d54e66fb151f41ec4` — 205,374 bytes, last modified 2026-08-29 16:41:42.
**Syllabus leaves:** 468 (PART 0: 46, PART 1: 121, PART 2: 137, PART 3: 96, PART 4: 40, PART 5: 28).
**Diagram manifest:** 99 ids, `D-01`…`D-99`.
**Rows delivered:** 112 (111 content files + this index), against the prompt's OUTPUT CONTRACT of 61
rows. **Status: complete.** All 468 syllabus leaves are covered, all 99 diagram manifest ids are
accounted for, and no row remains `planned`. The prompt's OUTPUT CONTRACT lists 61
rows; two were re-split during the run, and the prompt explicitly permits splitting further and
registering the new files here. Splitting always beats cutting.

| Original row | Re-split into | Why |
|---|---|---|
| ~~`ground-zero/02-basics-context-window.md`~~ *(retired)* | `-a.md` (§0.2.1–0.2.7) + `-b.md` (§0.2.8–0.2.12) | Its writer reported landing on exactly 600 lines — a fit-to-limit signal, and the contract forbids compressing to fit. Split at the window-mechanics / window-economics boundary. |
| ~~`memory/03-auto-memory.md`~~ *(retired)* | `03-auto-memory.md` (§1.3.21–1.3.28) + `04-your-own-instruction-files.md` (§1.3.29) | Its writer returned `blocked` at 675 lines with all leaves covered and nothing compressed. §1.3.29 is a self-contained `[CASE]`/`[BUILD]` costing exercise in a different register from the mechanism content above it. |
| ~~`permissions/03-path-web-mcp-agent-rules.md`~~ *(retired)* | `03-path-rules.md` (§1.4.16–1.4.19) + `04-web-mcp-agent-and-cd-rules.md` (§1.4.20–1.4.24) | Landed at 598 lines, two under the ceiling — the same fit-to-limit signal. Split between the path-rule argument and the rule families that are not path rules. Forces the renumbering of the modes file to `05-modes.md`. |

### Two sanctioned exceptions to the size policy — settled, do not re-raise

**`subagents/04-limits-and-cost.md` at 215 lines, under the 250 floor. Accepted.** The 250–450 band
was this orchestrator's own estimate, not the prompt's, and it does not fit every folder. `subagents/`
is pure `[DOC]` — no `[CASE]` quotes to paste, no `[BUILD]` artefacts to ship, no `[PROVE]` arithmetic
to print — so its natural density is 200–235, which is exactly where its siblings sit
(`02-the-context-boundary.md` at 200, `01-basics-definition-and-precedence.md` at 234). The file was
re-dispatched once and gained a full `**Pitfall:**`, an `**Insight:**`, sibling decision-rule prose for
the three memory scopes, the resume-through-parent-session boundary, freshly verified `[DOC]` material,
two cheat-sheet rows and two self-test questions — and then declined to pad further, correctly.
Forcing 250 would be padding, which the house rules ban outright. **The floor that actually binds is
the ~120-line stub floor**, which 215 clears comfortably.

The general rule this establishes, for any reviewer of this or a sibling topic: **judge a row against
its folder's tag mix, not against a global band.** A `build-it/` row shipping an artefact plus a prove
step plus a cost note plus a *Diff vs the real one* table lands at 400–590; a pure `[DOC]` row lands
at 200–250; both are correct.

**`92-interview-internals.md` at 666 lines, over the 600 ceiling. Sanctioned, not a violation.** The
prompt requires this exact filename to carry the topic-wide `## Atomic concept checklist` — 423 flat
bullets over all six parts — and explicitly forbids relocating it, because it is the path downstream
tooling parses. The prompt also states there is no line limit and that completeness beats brevity. The
Q&As and puzzles were already split off into `92-interview-internals-b.md` per the prompt's own
provision; 666 is what remains after that split.

### Plan revision: the row-size rule for the rest of the run

**Measured, not assumed.** Across the first eleven files the realised density is **≈45–55 lines per
syllabus leaf** — the six-link concept chain, the `[BUILD]` artefact/prove/cost triad, the verbatim
`[CASE]` quotes and the `[PROVE]` arithmetic each cost real lines, and the prompt forbids trimming
any of them. Every row estimated at 8+ leaves has therefore either overrun or been re-split.

The estimates in the tables above are the prompt's OUTPUT CONTRACT and are left as the record of it.
For every row not yet written, the plan is re-derived under one rule:

- **At most 5 leaves per writer row**, and
- **at most 3 leaves for a PART 4 row**, since every PART 4 leaf ships an artefact plus a prove step
  plus a cost note plus, in five sections, a *Diff vs the real one* table.

This raises the file count well above the contract's 61. The prompt is explicit that this is the
correct trade: *"No line limit and no file-count limit… If a file grows large, split it into more
files rather than cutting content, and register the new file in `00-index.md`."* Splitting always
beats cutting, and a row planned small never needs a reactive re-split.

The derived rows are listed in `## Derived row plan` at the foot of this index. Section-to-file
ownership below is updated as each derived row lands.

On resume: if the hash above no longer matches the prompt, every row reverts to `planned` and the
set is rebuilt. Otherwise dispatch only the rows whose `Status` is `planned` or `blocked`.

---

## The example domain

**This topic does not use QuizStakes.** Every `[CASE]` leaf is grounded in the real **sdlc-harness**
repository at `/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness`, cited
by file path and quoted verbatim. That repository is **read-only** for this pipeline. The
authoritative file-by-file map is the table in `## The example domain — the sdlc-harness repo` of
the source prompt, reproduced verbatim for writers in
`tmp/21-contract/writer-prompt-contract.md`.

---

## The PART 0 five-question gate

**Status: applied, and passed.**

The four `ground-zero/` files were written and reviewed as a single first pass, before any PART 1
row was dispatched. The gate was then applied by reading all four files end to end against the five
questions the prompt names, checking that each answer is available in the body, at first use, without
forward reference:

| # | Question | Where PART 0 answers it | Verdict |
|---|---|---|---|
| 1 | What is a **token**? | §0.1.3 defines it as a chunk of text, ~3–4 characters of English / ~0.75 words, with §0.1.4 proving the ratio differs for prose, Java and minified JSON | pass |
| 2 | What is a **context window**, and why is the whole conversation re-sent every turn? | §0.2.1 defines the hard limit; §0.2.4 states the window is the argument list of the next call, not a memory; §0.2.5's stateless `@RestController` analogy and §0.2.6's 10-turn vs 100-turn arithmetic give the re-send | pass |
| 3 | What is a **tool call** — and who decides whether the tool actually runs? | §0.3.2 defines a tool as name + description + JSON input schema; §0.3.3 states the model only emits a `tool_use` block and the harness decides | pass |
| 4 | What is a **turn**? | §0.3.5 defines it as one model response plus any tools it triggers, and separates `--max-turns` from a wall-clock timeout | pass |
| 5 | What is an **agent**, precisely, as distinct from a chatbot? | §0.1.12 defines it as a model plus a loop plus tools, and rules out "chatbot" and "AI" as synonyms; D-05 draws the contrast | pass |

No PART 0 file uses "as you know", "obviously", "of course you're familiar with" or "recall that",
and no term is relied on before it is defined in the body.

**Evidence, checked against the written files rather than asserted:** the token definition lands in
`01-basics-what-the-model-is.md` with real per-string counts; the argument-list framing lands in
`02-basics-context-window-a.md` under its own heading, in the syllabus's own words; the
`tool_use`-versus-execution split lands in `03-basics-the-agent-loop.md` under a heading that names
it as the hinge of the guide, with the harness named as the decider; the turn and the agent both
close with a boxed one-sentence definition. A grep for the four banned phrases, for emojis and for
throwaway names returns nothing across all five files, every file carries the full closing set with
8–10 folded self-test answers, and all 22 diagram embeds resolve to files that exist.

---

## Reading orders

**First careful pass — cover to cover, in plan order.** PART 0 is a prerequisite course: do not skip
it and do not skim it. Nothing in PARTs 1–5 is readable without its vocabulary.

Plan order is: `ground-zero/` → `claude-folder/` → `settings/` → `memory/` → `permissions/` →
`skills/` → `90-interview-basics.md` → `subagents/` → `personas/` → `hooks/` → `mcp-and-lsp/` →
`plugins/` → `context-economy/` → `practices/` → `deterministic-vs-agentic/` → `governance/` →
`91-interview-intermediate.md` → `request-assembly/` → `compaction/` →
`permission-evaluation/` → `cost-model/` → `effort-and-routing/` → `headless/` →
`setting-sources-incident/` → `sdk-and-api/` → `orchestration/` → `verification/` →
`92-interview-internals.md` → `build-it/` → `93-interview-build-it.md` →
`94-interview-questions-a.md` → `-b.md` → `-c.md` → `-d.md` → `95-trap-index.md` →
`96-drills-and-review-schedule.md`.

**Night-before re-read — the numbers, the traps and the answer shapes only.**

1. `95-trap-index.md` — the consolidated trap table (154 rows), the version-stale table, the top
   five, the incident index, the fourteen-number drill.
2. `92-interview-internals.md` — the `## Atomic concept checklist` at its end, read as a self-quiz.
3. `permissions/01-basics-rules-and-order.md` and
   `permission-evaluation/03-internals-a-the-pipeline.md` —
   deny → ask → allow, first match wins, and the full pipeline.
4. `settings/01-basics-files-and-precedence.md` — managed above the command line.
5. `cost-model/03-internals-a-the-four-quantities.md` and `-b-ceilings-and-reading-it-back.md` — the
   four billed quantities and the three ceilings.
6. `94-interview-questions-a.md` and `-b.md` — the sixteen answer shapes, read aloud.

**Operating manual use — while configuring a machine.** `build-it/01`–`08` in order, with
`permissions/` and `hooks/` open beside them.

---

## The file plan

> # THIS SECTION IS HISTORY, NOT NAVIGATION
>
> **These tables are the source prompt's OUTPUT CONTRACT, preserved as the record of what was
> commissioned. 36 of their rows name file paths that DO NOT EXIST**, because those rows were
> re-split during the run. Do not navigate from here and do not resolve a leaf from here.
>
> **The live, disk-derived tables are `## Nav chain`, `## Diagram assignment`, `## Leaf ownership`
> and `## Derived row plan`.** Those four are generated from the files' own footers and nav links, so
> every path in them exists.
>
> **The live plan is `## Derived row plan`, further down this file.** A resumed run, or any agent
> asking "what does this file cover", must read that section and not these tables. One writer was
> briefly misled by a stale row here and nearly deferred a leaf that was in its scope; this banner
> exists because of it.

`Status` is `planned` until the writer's envelope returns, then `written`, or `blocked` with the
reason recorded under `## Open questions`. `Lines` is the actual `wc -l` from the envelope. Rows
marked **re-split, see derived plan** were superseded — their leaves are all covered, by more files
than the row names.

### PART 0 — GROUND ZERO (written and reviewed first)

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `ground-zero/01-basics-what-the-model-is.md` | what the model is | BASICS | 0.1.1–0.1.12 (12) | the model as one pure function text-in/text-out; next-token prediction and sampling; the token as the unit of cost and of the limit; non-determinism; confabulation and why fluency is not a correctness signal; agent = model + loop + tools | D-01, D-02 (table), D-03a/b/c, D-04 (table), D-05 | 380 | written | 529 |
| `ground-zero/02-basics-context-window-a.md` | the context window | BASICS | 0.2.1–0.2.7 (7) | the window as a hard token limit on input plus output together; the request as an ordered list of role-tagged messages; the window is the argument list of the next call, not a memory; cost and latency scale with conversation length | D-06, D-07, D-08 | 400 | written | 444 |
| `ground-zero/02-basics-context-window-b.md` | caching and the context budget | BASICS | 0.2.8–0.2.12 (5) | prompt caching and the reusable prefix; the cache TTL and why a six-minute pause costs money; the 200K budget itemised against what is left for work; the five things that consume the window before you type; "it forgot" as two different diagnoses | D-09, D-10 | 400 | written | 393 |
| `ground-zero/03-basics-the-agent-loop.md` | the agent loop | BASICS | 0.3.1–0.3.12 (12) | the three-step loop; a tool as name + description + JSON schema; the model emits `tool_use`, the harness decides; tool output is context; the turn; Claude Code is the harness, not the model | D-11a/b/c/d, D-12a/b/c/d/e, D-13, D-14 | 400 | written | 266 |
| `ground-zero/04-basics-orientation.md` | orientation in the tool | BASICS | 0.4.1–0.4.10 (10) | the three ways in; the diagnostic ladder and its order; `/context` read row by row; `/compact` vs `/clear` vs a fresh session; session transcripts as readable JSONL | D-15, D-16 (table), D-17 (table) | 350 | written | 301 |

### PART 1 — BASICS

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `claude-folder/01-basics-anatomy.md` | the `.claude` folder | BASICS | 1.1.1–1.1.9 (9) | configuration-as-code; the full project inventory; the user twin and the tool-owned `~/.claude.json`; the discovery walk; the invariant that some file caused it | D-18, D-19a/b/c | 300 | written | 370 |
| `settings/01-basics-files-and-precedence.md` | settings scope | BASICS | 1.2.1–1.2.8 (8) | the four settings files and their reach; the five-layer precedence order with managed above the command line; where `settings.local.json` lands; committing shared project settings | D-20, D-21 | 320 | written | 464 |
| `settings/02-keys-and-verification.md` | settings keys | BASICS | 1.2.9–1.2.16 (8) | the fifteen key groups; the twelve first-touch keys with values; `env` composition; verifying a setting actually applied; the silently-ignored key; `--setting-sources` as a loading choice | D-22 (table) | 330 | written | 436 |
| `memory/01-basics-claude-md.md` | `CLAUDE.md` | BASICS | 1.3.1–1.3.13 (13) | instructions vs auto memory; context is not enforced configuration; the four locations in load order; concatenated not overriding; `@path` imports to four hops; size guidance and what a `CLAUDE.md` costs per turn | D-23a–e, D-24 | 420 | written | 493 |
| `memory/02-rules-and-path-scoping.md` | rules and path scoping | BASICS | 1.3.14–1.3.20 (7) | `.claude/rules/` as modular instructions; `paths:` frontmatter as the affordability mechanism; the 1,000-pattern / 4 MiB budget; `claudeMdExcludes` for monorepos; `AGENTS.md` is not read | D-25 | 300 | written | 527 |
| `memory/03-auto-memory.md` | auto memory | BASICS | 1.3.21–1.3.28 (8) | the four recorded types; on-disk layout and the 200-line / 25 KB index cut; auto memory does not reach subagents; what survives `/compact`; the "Claude ignored my CLAUDE.md" diagnostic ladder | D-26, D-27 | 350 | written | 487 |
| `memory/04-your-own-instruction-files.md` | your own instruction files, costed | BASICS | 1.3.29 (1) | reading the reader's own two-level setup and accounting for what each entry costs per session; ruling entry by entry on whether it belongs in `CLAUDE.md`, in a path-scoped rule, or in a skill | — | 380 | written | 380 |
| `permissions/01-basics-rules-and-order.md` | permission rules | BASICS | 1.4.1–1.4.10 (10) | rules are enforced by the harness, not the model; deny → ask → allow, first match wins; a broad deny cannot carry exceptions; bare vs scoped deny; Bash specifiers match the whole command text; compound commands match independently | D-28, D-29, D-30 (table) | 400 | written | 462 |
| `permissions/02-bash-matching.md` | Bash matching | BASICS | 1.4.11–1.4.15 (5) | wrapper stripping and its exact list; environment runners are not stripped; exec wrappers a prefix rule cannot approve; the built-in read-only command set; redirections add a target-path check | D-31 | 320 | written | 488 |
| `permissions/03-path-web-mcp-agent-rules.md` | path, web, MCP and Agent rules | BASICS | 1.4.16–1.4.24 (9) | gitignore pattern syntax and the four anchor forms; only `Read`/`Edit` path rules are consulted; a Read deny does not stop an arbitrary subprocess; `WebFetch(domain:…)`; MCP rule forms; `Agent(Name)` and parameter matching | D-32 (table) | 380 | **superseded — re-split, see derived row plan** | |
| `permissions/04-modes.md` | permission modes | BASICS | 1.4.25–1.4.29 (5) | all six modes and exactly what each auto-approves; `acceptEdits` and the filesystem commands it covers; `auto` mode's background classifier; what `bypassPermissions` still refuses; the managed kill switches | D-33 (table) | 330 | **superseded — re-split, see derived row plan** | |
| `permissions/05-directories-and-trust.md` | directories and trust | BASICS | 1.4.30–1.4.38 (9) | additional directories grant file access not configuration; `/cd` re-applies a whole project surface; workspace trust and how it is keyed; a `-p` session never shows the dialog and counts as accepted; a deny at any level is final | D-34 | 380 | **superseded — re-split, see derived row plan** | |
| `permissions/06-sandbox-and-a-real-block.md` | sandbox and a real block | BASICS | 1.4.39–1.4.41 (3) | the sandbox as the OS layer below permissions; a permission block written and each rule proven to fire; why `Bash(*)` plus a deny-list is a considered choice | D-35 | 300 | **superseded — re-split, see derived row plan** | |
| `skills/01-basics-what-a-skill-is.md` **re-split, see derived plan** | what a skill is | BASICS | 1.5.1–1.5.10 (10) | custom commands **are** skills; the four locations and the conflict order; progressive disclosure and the listing budget; every frontmatter field; `allowed-tools` pre-approves and does not restrict; who may invoke | D-36, D-37, D-38 | 400 | written | 479 |
| ~~`skills/02-substitution-and-lifecycle.md`~~ **re-split, see derived plan** | substitution and lifecycle | BASICS | 1.5.11–1.5.18 (8) | the string substitutions; dynamic injection running once before send; the injection mechanics that bite; the content lifecycle across turns; the compaction re-attachment budget; a skill is a directory | D-39, D-40 | 380 | **superseded — re-split, see derived row plan** | |
| ~~`skills/03-cases-and-decision-table.md`~~ **re-split, see derived plan** | skill cases and the decision table | BASICS | 1.5.19–1.5.26 (8) | a reference library that costs nothing until needed; an orchestrator-not-rewrite skill body; prompt composition without duplication; a description that names the trigger not the topic; the mechanism decision table | D-41 | 400 | **superseded — re-split, see derived row plan** | |
| `90-interview-basics.md` | PARTs 0+1 wrap-up | BASICS | — (wrap-up over §0.1–§1.5) | summary table over PARTs 0 and 1; **12** Q&As with full spoken-length model answers; 5 predict-the-output puzzles | re-embeds as needed | 480 | written | 377 |

### PART 2 — INTERMEDIATE

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `subagents/01-basics-mechanics.md` | subagent mechanics | INTERMEDIATE | 2.1.1–2.1.10 (10) | the definition file and its locations; agents and skills order oppositely; the context boundary — what crosses in, what crosses out, what is blocked; the git snapshot taken at parent session start | D-42, D-43 | 400 | **superseded — re-split, see derived row plan** | |
| `subagents/02-builtins-forks-limits.md` | built-ins, forks, limits | INTERMEDIATE | 2.1.11–2.1.19 (9) | the built-in roster; foreground vs background; forks vs a fresh subagent; the concurrency and nesting limits; where a subagent's 2× comes from and when it still wins | D-44, D-45 (table), D-46 | 380 | **superseded — re-split, see derived row plan** | |
| `subagents/03-cases-and-protocol.md` | subagent cases and protocol | INTERMEDIATE | 2.1.20–2.1.25 (6) | pointer bodies and versioned prompt files; write boundaries and withheld tools; one writer per output path, ever; the return protocol that keeps the parent's transcript small | D-47 | 350 | **superseded — re-split, see derived row plan** | |
| `personas/01-agent-vs-system-prompt.md` | personas | INTERMEDIATE | 2.2.1–2.2.7 (7) | `--agent` vs `--append-system-prompt` vs `--system-prompt`; what comes with a registered agent and what does not; persona loading and envelope extraction in the real engine | D-48 (table) | 280 | **superseded — re-split, see derived row plan** | |
| `hooks/01-basics-what-a-hook-is.md` | what a hook is | INTERMEDIATE | 2.3.1–2.3.9 (9) | a hook is the only guarantee; the `command` and `http` forms; matcher semantics; the 32 events grouped; the lifecycle across one session; which events can block | D-49, D-50, D-51 (table) | 400 | written | 544 |
| `hooks/02-payloads-and-contracts.md` | payloads and contracts | INTERMEDIATE | 2.3.10–2.3.20 (11) | the stdin payload; exit-code semantics and the special-cased events; the JSON output contract field by field; exit 2 overriding a JSON allow; a hook cannot unblock a deny; the six configuration sources | D-52, D-53, D-54 | 430 | **superseded — re-split, see derived row plan** | |
| `hooks/03-cases-and-incidents.md` | hook cases and incidents | INTERMEDIATE | 2.3.21–2.3.28 (8) | tagged advisory instructions; the defensive shape; content-hash versioning; the `SessionStart` reindex pile-up and its law; the blocking-guard pattern | D-55 | 430 | **superseded — re-split, see derived row plan** | |
| `mcp-and-lsp/01-basics.md` | MCP and LSP | INTERMEDIATE | 2.4.1–2.4.13 (13) | transports and configuration scopes; the tool-name form and the per-turn schema tax; failure modes and governance keys; LSP symbol lookup versus read-and-grep as a token argument | D-56, D-57 | 400 | **superseded — re-split, see derived row plan** | |
| `plugins/01-basics-structure.md` | plugin structure | INTERMEDIATE | 2.5.1–2.5.8 (8) | the directory layout and the one file that belongs in `.claude-plugin/`; `plugin.json` fields; version semantics; namespacing; the skills-directory trap | D-58 | 350 | written | 271 |
| `plugins/02-marketplaces-and-governance.md` | marketplaces and governance | INTERMEDIATE | 2.5.9–2.5.15 (7) | marketplaces and their manifest; cross-marketplace dependencies and explicit trust; the unresolved-dependency failure; `strictPluginOnlyCustomization` closing the side doors | D-59, D-61 | 330 | **superseded — re-split, see derived row plan** | |
| `plugins/03-cases-and-conversion.md` | plugin cases and conversion | INTERMEDIATE | 2.5.16–2.5.20 (5) | documentation living in the config; a real `plugin.json` with licence and dependencies; `${CLAUDE_PLUGIN_ROOT}` is not the repo; converting a `.claude/` tree into a plugin | D-60 | 320 | **superseded — re-split, see derived row plan** | |
| `context-economy/01-in-practice.md` | context economy | INTERMEDIATE | 2.6.1–2.6.12 (12) | reading `/context` as a habit; the four biggest avoidable costs ranked with their fixes; bounding output; autocompaction and `PreCompact`; isolation arithmetic | D-62, D-63 | 420 | **superseded — re-split, see derived row plan** | |
| `practices/01-what-changes-outcomes.md` | practices | INTERMEDIATE | 2.7.1–2.7.12 (12) | plan mode moves the correction earlier; test-first as a machine-checkable specification; small reviewable tasks; prompting that changes outcomes; the bundled review skills; the status line | D-64 | 430 | **superseded — re-split, see derived row plan** | |
| `deterministic-vs-agentic/01-the-central-judgment.md` | deterministic vs agentic | INTERMEDIATE | 2.8.1–2.8.9 (9) | does the input determine one correct answer; script or prompt; idempotence and the documented exception; human-authority gates; "the model could do it" is not an argument | D-65 | 350 | written | 344 |
| `governance/01-security-and-the-org-view.md` | governance and security | INTERMEDIATE | 2.9.1–2.9.11 (11) | one agent's blast radius; prompt injection as data-to-instruction confusion; the controls that hold and the one that does not; the `allowManaged*Only` lock family; secrets, attribution, review capacity | D-66, D-67, D-68 (table) | 400 | **superseded — re-split, see derived row plan** | |
| `91-interview-intermediate.md` | PART 2 wrap-up | INTERMEDIATE | — (wrap-up over §2.1–§2.9) | summary table over PART 2; **18** Q&As with full spoken-length model answers; 5 predict-the-output puzzles | re-embeds as needed | 520 | written | 593 |

### PART 3 — ADVANCED (INTERNALS)

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `request-assembly/03-internals-what-is-in-the-request.md` | request assembly | INTERNALS | 3.1.1–3.1.8 (8) | the literal assembly order and the cached prefix; `CLAUDE.md` is a user message, not the system prompt; the skill listing's cost; the JSONL transcript as the observable artefact | D-69, D-70, D-71, D-72 | 380 | **superseded — re-split, see derived row plan** | |
| `compaction/03-internals-compaction.md` | compaction | INTERNALS | 3.2.1–3.2.7 (7) | the threshold as arithmetic against the window; what the summary keeps and drops; the re-attachment budget at 5,000 / 25,000 tokens newest-first; `PreCompact`/`PostCompact` | D-73 | 320 | **superseded — re-split, see derived row plan** | |
| `permission-evaluation/03-internals-pipeline.md` | permission pipeline | INTERNALS | 3.3.1–3.3.8 (8) | the five-stage pipeline traced end to end; rule collection across layers; the read-only fast path and the two cases that leave it; three Bash commands traced through matching | D-74, D-75 | 380 | **superseded — re-split, see derived row plan** | |
| `cost-model/03-internals-cost.md` | the cost model | INTERNALS | 3.4.1–3.4.9 (9) | the four billed quantities with the arithmetic; where the money actually goes in one session; the cache TTL re-pricing; the three ceilings and their failure shapes | D-76 (table), D-77, D-78 (table) | 380 | **superseded — re-split, see derived row plan** | |
| `effort-and-routing/03-internals-routing.md` | effort and routing | INTERNALS | 3.5.1–3.5.6 (6) | effort levels and what they cost; per-model and per-skill routing; the escalation path; `fastMode` is not a downgrade; routing everything cheap costs more | D-79 | 280 | written | 527 |
| `headless/03-internals-a-the-surface.md` | headless surface | INTERNALS | 3.6.1–3.6.9 (9) | `claude -p` and the JSON envelope field by field; the three output formats and the two input formats; `--json-schema`; background and remote execution | D-80 | 400 | written | 478 |
| `headless/03-internals-b-the-real-wrapper.md` | the real wrapper | INTERNALS | 3.6.10–3.6.18 (9) | the failure taxonomy and why each branch is handled differently; the 500-character snippet; keeping the last parsed envelope through a retry; resolution order parameter → env → default with every real constant | D-81, D-82 | 420 | **superseded — re-split, see derived row plan** | |
| `setting-sources-incident/03-internals-root-cause.md` | the `--setting-sources` incident | INTERNALS | 3.7.1–3.7.9 (9) | a per-story worktree changing what `project` resolves to; the itemised symptom; the fix evaluated independently of `cwd`; both generalisations and the paper trail | D-83 | 350 | **superseded — re-split, see derived row plan** | |
| `sdk-and-api/03-internals-sdk-and-java-options.md` | SDK and API | INTERNALS | 3.8.1–3.8.8 (8) | three levels of building on Claude and what each gives up; the raw Messages API loop; no first-party Java SDK; an agent call is a remote dependency | D-84, D-85 | 350 | **superseded — re-split, see derived row plan** | |
| `orchestration/03-internals-patterns.md` | orchestration patterns | INTERNALS | 3.9.1–3.9.12 (12) | the six shapes and the condition that picks each; fan-out with a join and the file boundary; a pipeline where no stage writes its own input; prose executor vs deterministic conductor; the calibration loop | D-86, D-87, D-88, D-89, D-90 | 450 | **superseded — re-split, see derived row plan** | |
| `verification/03-internals-laws.md` | verification | INTERNALS | 3.10.1–3.10.11 (11) | evidence ranked by strength; the checker that switched itself off; certify from final state; a closed lane is not a verified lane; review capacity as the throughput ceiling | D-91 (table), D-92, D-93 | 420 | **superseded — re-split, see derived row plan** | |
| `92-interview-internals.md` | PART 3 wrap-up + the topic-wide checklist | INTERNALS | — (wrap-up over §3.1–§3.10) | summary table over PART 3; **22** Q&As; 5 puzzles; **then the flat `## Atomic concept checklist` covering all six parts** — this file is the parser target and the checklist does not move | re-embeds as needed | 560 | written | 666 |

### PART 4 — BUILD IT

Every leaf in this part is `[BUILD]`: the complete artefact, then the prove step with its real
output, then a "what this costs" note in tokens or dollars. §4.2.6, §4.3.6, §4.4.5, §4.5.8 and
§4.6.6 additionally end with a **Diff vs the real one** table against the sdlc-harness equivalent.

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `build-it/01-a-claude-folder.md` | a `.claude` folder from nothing | BUILD | 4.1.1–4.1.5 (5) | a `CLAUDE.md` under 100 lines with a measured `/context` delta; a path-scoped rule; a first skill; a settings file and the one key the local file overrides | D-94 | 350 | **superseded — re-split, see derived row plan** | |
| `build-it/02-three-hooks.md` | three hooks | BUILD | 4.2.1–4.2.6 (6) | `SessionStart` branch context as tagged advisory lines; `PreToolUse` destructive-Bash block returning JSON; `PostToolUse` format-on-edit reading `tool_input.file_path` via `jq`; `Stop` require-green-build using `continue`; the Diff vs the real one | D-95 | 420 | **superseded — re-split, see derived row plan** | |
| `build-it/03-a-skill-and-a-command.md` | a skill and a command | BUILD | 4.3.1–4.3.6 (6) | a skill with real frontmatter, `$ARGUMENTS`, an injection and a `references/` file; the prove step through `/context` before and after; the Diff vs the real one | — | 400 | **superseded — re-split, see derived row plan** | |
| `build-it/04-two-subagents.md` | two subagents | BUILD | 4.4.1–4.4.5 (5) | a read-only reviewer with tools withheld; a test-runner with a write boundary; proving the boundary holds; the Diff vs the real one | — | 350 | **superseded — re-split, see derived row plan** | |
| `build-it/05-orchestrator-a-the-runner.md` | `ClaudeRunner`, part a | BUILD | 4.5.1–4.5.4 (4) | `ProcessBuilder` around `claude -p --output-format json`; the `ClaudeEnvelope` record; the three ceilings with distinct exception types; resolution order parameter → env → default | D-96 | 450 | written | 594 |
| `build-it/06-orchestrator-b-pipeline-and-cost.md` | `ClaudeRunner`, part b | BUILD | 4.5.5–4.5.8 (4) | a `Semaphore` bulkhead and a bounded retry that keeps the last parsed envelope; the two-stage pipeline where no stage writes its own input; the per-stage cost report; the Diff vs the real one | D-97 | 430 | **superseded — re-split, see derived row plan** | |
| `build-it/07-a-plugin.md` | a plugin | BUILD | 4.6.1–4.6.6 (6) | packaging the `.claude/` tree; the local marketplace; the install path and `--plugin-dir` pre-publish test; the version bump; the Diff vs the real one | D-98 | 380 | **superseded — re-split, see derived row plan** | |
| `build-it/08-verification-harness.md` | a verification harness | BUILD | 4.7.1–4.7.4 (4) | `verify.sh` with text-ness asserted first; the structural gates; re-running every fenced listing against its printed output; where each gate belongs — `Stop` hook or CI | D-99 | 300 | **superseded — re-split, see derived row plan** | |
| `93-interview-build-it.md` | PART 4 wrap-up | BUILD | — (wrap-up over §4.1–§4.7) | summary table over PART 4; **10** Q&As; 5 predict-the-output puzzles | re-embeds as needed | 400 | written | 429 |

### PART 5 — INTERVIEW AND RETENTION

| File | Subject | Tier | Leaves | Primary concepts | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| `94-interview-questions-a.md` | the questions, first half | PART 5 | 5.1.1–5.1.8 (8) | eight questions, each with its full answer shape at speaking length | re-embeds as needed | 400 | written | 301 |
| `94-interview-questions-b.md` | the questions, second half | PART 5 | 5.1.9–5.1.16 (8) | eight questions at speaking length, then PART 5's own summary table, **10** Q&As and 5 puzzles | re-embeds as needed | 450 | written | 290 |
| `95-trap-index-and-drills.md` | traps and drills | PART 5 | 5.2.1–5.3.8 (12) | the consolidated trap table; the version-stale table with both versions per row; the top five; the incident index with a cost and a law per line; the seven drills including the fourteen-number drill | re-embeds as needed | 450 | **superseded — re-split, see derived row plan** | |

§5.3.1 is **one line pointing at** the `## Atomic concept checklist` at the end of
`92-interview-internals.md`. A second copy is a defect.

---

## Nav chain

**Derived from the files themselves, not from the plan** — walked by following each file's own
`Previous:`/`Next:` links from the one file that has no `Previous:`. The chain is unbroken across all
111 files, with no file off it and no file visited twice. Reading order is chain order.

| # | File | Lines |
|---|---|---|
| 1 | `ground-zero/01-basics-what-the-model-is.md` | 529 |
| 2 | `ground-zero/02-basics-context-window-a.md` | 444 |
| 3 | `ground-zero/02-basics-context-window-b.md` | 393 |
| 4 | `ground-zero/03-basics-the-agent-loop.md` | 266 |
| 5 | `ground-zero/04-basics-orientation.md` | 301 |
| 6 | `claude-folder/01-basics-anatomy.md` | 370 |
| 7 | `settings/01-basics-files-and-precedence.md` | 464 |
| 8 | `settings/02-keys-and-verification.md` | 436 |
| 9 | `memory/01-basics-claude-md.md` | 493 |
| 10 | `memory/02-rules-and-path-scoping.md` | 527 |
| 11 | `memory/03-auto-memory.md` | 487 |
| 12 | `memory/04-your-own-instruction-files.md` | 380 |
| 13 | `permissions/01-basics-rules-and-order.md` | 462 |
| 14 | `permissions/02-bash-matching.md` | 488 |
| 15 | `permissions/03-path-rules.md` | 414 |
| 16 | `permissions/04-web-mcp-agent-and-cd-rules.md` | 414 |
| 17 | `permissions/05-modes.md` | 429 |
| 18 | `permissions/06-directories-and-trust.md` | 378 |
| 19 | `permissions/07-precedence-and-overrides.md` | 537 |
| 20 | `permissions/08-sandbox-and-a-real-block.md` | 553 |
| 21 | `skills/01-basics-what-a-skill-is.md` | 479 |
| 22 | `skills/02-frontmatter-and-invocation.md` | 488 |
| 23 | `skills/03-substitution-and-injection.md` | 348 |
| 24 | `skills/04-lifecycle-and-supporting-files.md` | 433 |
| 25 | `skills/05-cases.md` | 399 |
| 26 | `skills/06-builtins-and-decision-table.md` | 405 |
| 27 | `90-interview-basics.md` | 377 |
| 28 | `subagents/01-basics-definition-and-precedence.md` | 234 |
| 29 | `subagents/02-the-context-boundary.md` | 200 |
| 30 | `subagents/03-builtins-and-forks.md` | 285 |
| 31 | `subagents/04-limits-and-cost.md` | 215 |
| 32 | `subagents/05-cases-pointer-bodies.md` | 424 |
| 33 | `subagents/06-write-boundaries-and-protocol.md` | 508 |
| 34 | `personas/01-the-four-flags.md` | 354 |
| 35 | `personas/02-cases-persona-loading.md` | 335 |
| 36 | `hooks/01-basics-what-a-hook-is.md` | 544 |
| 37 | `hooks/02-the-event-catalogue.md` | 433 |
| 38 | `hooks/03-payloads-and-exit-codes.md` | 569 |
| 39 | `hooks/04-a-hook-cannot-unblock-a-deny.md` | 408 |
| 40 | `hooks/05-configuration-sources.md` | 507 |
| 41 | `hooks/06-cases-advisory-and-defensive.md` | 549 |
| 42 | `hooks/07-the-reindex-incident.md` | 454 |
| 43 | `hooks/08-the-blocking-guard-pattern.md` | 519 |
| 44 | `mcp-and-lsp/01-basics-transports-and-scopes.md` | 435 |
| 45 | `mcp-and-lsp/02-the-per-turn-tax.md` | 349 |
| 46 | `mcp-and-lsp/03-lsp.md` | 455 |
| 47 | `plugins/01-basics-structure.md` | 271 |
| 48 | `plugins/02-namespacing-and-skills-dir.md` | 342 |
| 49 | `plugins/03-marketplaces-and-dependencies.md` | 386 |
| 50 | `plugins/04-governance.md` | 319 |
| 51 | `plugins/05-cases-and-conversion.md` | 448 |
| 52 | `context-economy/01-measuring-and-ranking.md` | 498 |
| 53 | `context-economy/02-bounding-and-compaction.md` | 436 |
| 54 | `context-economy/03-isolation-arithmetic.md` | 432 |
| 55 | `practices/01-plan-mode-and-test-first.md` | 448 |
| 56 | `practices/02-prompting-and-context.md` | 519 |
| 57 | `practices/03-review-skills-and-interface.md` | 561 |
| 58 | `deterministic-vs-agentic/01-the-central-judgment.md` | 344 |
| 59 | `deterministic-vs-agentic/02-cases-idempotence.md` | 374 |
| 60 | `governance/01-the-threat-model.md` | 316 |
| 61 | `governance/02-the-lock-family.md` | 373 |
| 62 | `governance/03-secrets-attribution-review.md` | 418 |
| 63 | `91-interview-intermediate.md` | 593 |
| 64 | `request-assembly/03-internals-a-assembly-order.md` | 321 |
| 65 | `request-assembly/03-internals-b-listing-and-transcripts.md` | 491 |
| 66 | `compaction/03-internals-a-the-budget.md` | 494 |
| 67 | `compaction/03-internals-b-hooks-and-control.md` | 483 |
| 68 | `permission-evaluation/03-internals-a-the-pipeline.md` | 551 |
| 69 | `permission-evaluation/03-internals-b-traced-commands.md` | 241 |
| 70 | `cost-model/03-internals-a-the-four-quantities.md` | 406 |
| 71 | `cost-model/03-internals-b-ceilings-and-reading-it-back.md` | 531 |
| 72 | `effort-and-routing/03-internals-routing.md` | 527 |
| 73 | `headless/03-internals-a-the-surface.md` | 478 |
| 74 | `headless/03-internals-b-formats-and-execution.md` | 423 |
| 75 | `headless/03-internals-c-the-failure-taxonomy.md` | 430 |
| 76 | `headless/03-internals-d-resolution-order.md` | 376 |
| 77 | `setting-sources-incident/03-internals-a-the-failure.md` | 489 |
| 78 | `setting-sources-incident/03-internals-b-the-fix-and-the-law.md` | 414 |
| 79 | `sdk-and-api/03-internals-a-three-levels.md` | 284 |
| 80 | `sdk-and-api/03-internals-b-java-and-the-dependency-contract.md` | 275 |
| 81 | `orchestration/03-internals-a-shapes-and-fan-out.md` | 330 |
| 82 | `orchestration/03-internals-b-executor-vs-conductor.md` | 328 |
| 83 | `orchestration/03-internals-c-calibration-and-evals.md` | 270 |
| 84 | `verification/03-internals-a-evidence-and-the-nul-byte.md` | 440 |
| 85 | `verification/03-internals-b-the-sibling-laws.md` | 453 |
| 86 | `verification/03-internals-c-automation-and-review-capacity.md` | 500 |
| 87 | `92-interview-internals.md` | 666 |
| 88 | `92-interview-internals-b.md` | 596 |
| 89 | `build-it/01-a-claude-folder-a.md` | 522 |
| 90 | `build-it/01-a-claude-folder-b.md` | 395 |
| 91 | `build-it/02-three-hooks-a.md` | 590 |
| 92 | `build-it/02-three-hooks-b.md` | 517 |
| 93 | `build-it/03-a-skill-and-a-command-a.md` | 477 |
| 94 | `build-it/03-a-skill-and-a-command-b.md` | 445 |
| 95 | `build-it/04-two-subagents-a.md` | 498 |
| 96 | `build-it/04-two-subagents-b.md` | 346 |
| 97 | `build-it/05-orchestrator-a-the-runner.md` | 594 |
| 98 | `build-it/05-orchestrator-b-ceilings-and-resolution.md` | 534 |
| 99 | `build-it/06-orchestrator-c-bulkhead-and-retry.md` | 567 |
| 100 | `build-it/06-orchestrator-d-pipeline-and-cost.md` | 432 |
| 101 | `build-it/07-a-plugin-a.md` | 554 |
| 102 | `build-it/07-a-plugin-b.md` | 396 |
| 103 | `build-it/08-verification-harness-a.md` | 361 |
| 104 | `build-it/08-verification-harness-b.md` | 391 |
| 105 | `93-interview-build-it.md` | 458 |
| 106 | `94-interview-questions-a.md` | 301 |
| 107 | `94-interview-questions-b.md` | 290 |
| 108 | `94-interview-questions-c.md` | 357 |
| 109 | `94-interview-questions-d.md` | 332 |
| 110 | `95-trap-index.md` | 329 |
| 111 | `96-drills-and-review-schedule.md` | 339 |
## Diagram assignment

**Derived from each file's `**Diagrams included:**` footer.** Ids marked as tables carry no SVG, per
the manifest's `Type` column; the id still appears in that file's prose in a bold caption line.

| File | Diagrams |
|---|---|
| `ground-zero/01-basics-what-the-model-is.md` | D-01, D-02, D-03, D-04, D-05 |
| `ground-zero/02-basics-context-window-a.md` | D-06, D-07, D-08 |
| `ground-zero/02-basics-context-window-b.md` | D-09, D-10 |
| `ground-zero/03-basics-the-agent-loop.md` | D-11 (a–d), D-12 (a–e), D-13, D-14 |
| `ground-zero/04-basics-orientation.md` | D-15, D-16, D-17 |
| `claude-folder/01-basics-anatomy.md` | D-18, D-19 |
| `settings/01-basics-files-and-precedence.md` | D-20, D-21 |
| `settings/02-keys-and-verification.md` | D-22 |
| `memory/01-basics-claude-md.md` | D-23, D-24 |
| `memory/02-rules-and-path-scoping.md` | D-25 |
| `memory/03-auto-memory.md` | D-26, D-27 |
| `memory/04-your-own-instruction-files.md` | none |
| `permissions/01-basics-rules-and-order.md` | D-28, D-29, D-30 |
| `permissions/02-bash-matching.md` | D-31 |
| `permissions/03-path-rules.md` | D-32 |
| `permissions/04-web-mcp-agent-and-cd-rules.md` | none |
| `permissions/05-modes.md` | D-33 |
| `permissions/06-directories-and-trust.md` | D-34 |
| `permissions/07-precedence-and-overrides.md` | none — D-34 in the previous file carries this row's tracked-versus-untracked panel |
| `permissions/08-sandbox-and-a-real-block.md` | D-35 |
| `skills/01-basics-what-a-skill-is.md` | D-36, D-37 |
| `skills/02-frontmatter-and-invocation.md` | D-38 |
| `skills/03-substitution-and-injection.md` | D-39 |
| `skills/04-lifecycle-and-supporting-files.md` | D-40 |
| `skills/05-cases.md` | none — this row's mechanisms are drawn by D-36 to D-40 in the four preceding files |
| `skills/06-builtins-and-decision-table.md` | D-41 |
| `90-interview-basics.md` | re-embedded by id where an answer turns on one |
| `subagents/01-basics-definition-and-precedence.md` | D-42 |
| `subagents/02-the-context-boundary.md` | D-43 |
| `subagents/03-builtins-and-forks.md` | D-44, D-45 |
| `subagents/04-limits-and-cost.md` | D-46 |
| `subagents/05-cases-pointer-bodies.md` | none — this row's mechanisms are drawn by D-42 to D-46 in the preceding files |
| `subagents/06-write-boundaries-and-protocol.md` | D-47 |
| `personas/01-the-four-flags.md` | D-48 |
| `personas/02-cases-persona-loading.md` | none — D-48 in the previous file carries this area's comparison |
| `hooks/01-basics-what-a-hook-is.md` | D-49 |
| `hooks/02-the-event-catalogue.md` | D-50, D-51 |
| `hooks/03-payloads-and-exit-codes.md` | D-52 |
| `hooks/04-a-hook-cannot-unblock-a-deny.md` | D-53 |
| `hooks/05-configuration-sources.md` | D-54 |
| `hooks/06-cases-advisory-and-defensive.md` | none — D-49 to D-54 in the preceding files draw this area's mechanisms, and D-55 in the next file draws the incident |
| `hooks/07-the-reindex-incident.md` | D-55a, D-55b, D-55c, D-55d |
| `hooks/08-the-blocking-guard-pattern.md` | none — this file's leaves carry no diagram in the manifest |
| `mcp-and-lsp/01-basics-transports-and-scopes.md` | none — D-56 in the next file draws the cost, and D-13 in `ground-zero/03` drew the tool categories |
| `mcp-and-lsp/02-the-per-turn-tax.md` | D-56 |
| `mcp-and-lsp/03-lsp.md` | D-57 |
| `plugins/01-basics-structure.md` | D-58 |
| `plugins/02-namespacing-and-skills-dir.md` | none — D-58 in the previous file draws the layout, D-59 and D-61 in the next two draw marketplaces and the governance lock |
| `plugins/03-marketplaces-and-dependencies.md` | D-59 |
| `plugins/04-governance.md` | D-61 |
| `plugins/05-cases-and-conversion.md` | D-60 |
| `context-economy/01-measuring-and-ranking.md` | D-62 |
| `context-economy/02-bounding-and-compaction.md` | none — D-62 in the previous file ranks the costs, D-27 and D-17 in PARTs 1 and 0 draw compaction and the reset semantics, and D-73 in §3.2 walks the budget mechanically |
| `context-economy/03-isolation-arithmetic.md` | D-63 |
| `practices/01-plan-mode-and-test-first.md` | D-64 |
| `practices/02-prompting-and-context.md` | none — D-64 in the previous file draws plan mode, and D-41 in `skills/06` draws the mechanism decision tree |
| `practices/03-review-skills-and-interface.md` | none — D-64 in `practices/01` draws plan mode and D-41 in `skills/06` draws the mechanism decision tree |
| `deterministic-vs-agentic/01-the-central-judgment.md` | D-65 |
| `deterministic-vs-agentic/02-cases-idempotence.md` | none — D-65 in the previous file draws the decision tree and D-41 in `skills/06` draws the mechanism selection |
| `governance/01-the-threat-model.md` | D-66, D-67 |
| `governance/02-the-lock-family.md` | D-68 |
| `governance/03-secrets-attribution-review.md` | none — D-66 and D-67 in `governance/01` draw the threat model, D-68 in `governance/02` tables the locks, and D-93 in `verification/03-internals-c` draws the review-capacity ceiling |
| `91-interview-intermediate.md` | re-embedded by id where an answer turns on one |
| `request-assembly/03-internals-a-assembly-order.md` | D-69, D-70 |
| `request-assembly/03-internals-b-listing-and-transcripts.md` | D-71, D-72 |
| `compaction/03-internals-a-the-budget.md` | D-73 (D-73a, D-73b, D-73c) |
| `compaction/03-internals-b-hooks-and-control.md` | none — D-73 in the previous file draws the budget, and D-27 in `memory/03-auto-memory.md` draws what survives |
| `permission-evaluation/03-internals-a-the-pipeline.md` | D-74 |
| `permission-evaluation/03-internals-b-traced-commands.md` | D-75a, D-75b, D-75c |
| `cost-model/03-internals-a-the-four-quantities.md` | D-76, D-77 |
| `cost-model/03-internals-b-ceilings-and-reading-it-back.md` | D-78 |
| `effort-and-routing/03-internals-routing.md` | D-79 |
| `headless/03-internals-a-the-surface.md` | D-80 |
| `headless/03-internals-b-formats-and-execution.md` | none — D-80 in the previous file draws the envelope, and D-81 and D-82 in the next two draw the failure taxonomy and the resolution order |
| `headless/03-internals-c-the-failure-taxonomy.md` | D-81 |
| `headless/03-internals-d-resolution-order.md` | D-82 |
| `setting-sources-incident/03-internals-a-the-failure.md` | D-83a, D-83b, D-83c, D-83d |
| `setting-sources-incident/03-internals-b-the-fix-and-the-law.md` | none — D-83a–d in the previous file draw the incident and its fix |
| `sdk-and-api/03-internals-a-three-levels.md` | D-84 |
| `sdk-and-api/03-internals-b-java-and-the-dependency-contract.md` | D-85 |
| `orchestration/03-internals-a-shapes-and-fan-out.md` | D-86, D-87a, D-87b, D-87c, D-88a, D-88b, D-88c, D-88d, D-88e |
| `orchestration/03-internals-b-executor-vs-conductor.md` | D-89 |
| `orchestration/03-internals-c-calibration-and-evals.md` | D-90 |
| `verification/03-internals-a-evidence-and-the-nul-byte.md` | D-91, D-92 |
| `verification/03-internals-b-the-sibling-laws.md` | none — D-91 and D-92 in the previous file rank the evidence and tell the NUL-byte story, and D-93 in the next draws the review-capacity ceiling |
| `verification/03-internals-c-automation-and-review-capacity.md` | D-93 |
| `92-interview-internals.md` | none — this file indexes the guide rather than illustrating a mechanism |
| `92-interview-internals-b.md` | re-embedded by id where an answer turns on one — D-70, D-74, D-81, D-83c |
| `build-it/01-a-claude-folder-a.md` | none — D-94 draws this row's finished tree and is embedded in the next file |
| `build-it/01-a-claude-folder-b.md` | D-94 |
| `build-it/02-three-hooks-a.md` | D-95 |
| `build-it/02-three-hooks-b.md` | none — D-95 in the previous file carries this row's lifecycle, including the `Stop` mark built here |
| `build-it/03-a-skill-and-a-command-a.md` | none — D-36 to D-40 in the `skills/` folder draw this row's mechanisms |
| `build-it/03-a-skill-and-a-command-b.md` | none — D-36 to D-40 in the `skills/` folder draw this row's mechanisms |
| `build-it/04-two-subagents-a.md` | none — D-42 to D-47 in the `subagents/` folder draw this row's mechanisms |
| `build-it/04-two-subagents-b.md` | none — D-42 to D-47 in the `subagents/` folder draw this row's mechanisms |
| `build-it/05-orchestrator-a-the-runner.md` | D-96 |
| `build-it/05-orchestrator-b-ceilings-and-resolution.md` | none — D-96 in the previous file draws the class and the boundary, D-82 in `headless/03-internals-d` draws the resolution chain |
| `build-it/06-orchestrator-c-bulkhead-and-retry.md` | D-97a, D-97b, D-97c |
| `build-it/06-orchestrator-d-pipeline-and-cost.md` | none — D-96 and D-97 in the three preceding files draw the class, the boundary and the pipeline |
| `build-it/07-a-plugin-a.md` | D-98 |
| `build-it/07-a-plugin-b.md` | none — D-98 in the previous file draws the packaged plugin, its marketplace, the install path and the version-bump panel |
| `build-it/08-verification-harness-a.md` | D-99 |
| `build-it/08-verification-harness-b.md` | none — D-99 in the previous file draws the full gate order and both terminals |
| `93-interview-build-it.md` | re-embedded by id where an answer turns on one |
| `94-interview-questions-a.md` | re-embedded by id where an answer turns on one |
| `94-interview-questions-b.md` | re-embedded by id where an answer turns on one |
| `94-interview-questions-c.md` | re-embedded by id where an answer turns on one |
| `94-interview-questions-d.md` | re-embedded by id where an answer turns on one |
| `95-trap-index.md` | none — this file indexes the guide rather than illustrating a mechanism |
| `96-drills-and-review-schedule.md` | none — this file drills the guide rather than illustrating a mechanism |
### Diagram pass: complete

The illustrator pass ran to completion **before** the writer pass reached PART 1, in 21 batches of
four manifest rows each, so no writer ever discovers a missing SVG at write time.

- **84 SVG ids authored**, in **128 files** — the extra files are frame series, where a manifest row
  asked for N frames and the illustrator authored each frame as its own file (`D-03a`, `D-03b`,
  `D-03c`, and likewise for D-11, D-12, D-19, D-23, D-31, D-39, D-55, D-67, D-73, D-75, D-83, D-87,
  D-88, D-92, D-97). Every id produced is recorded in the owning file's footer.
- **15 ids carry no SVG, correctly**: D-02, D-04, D-16, D-17, D-22, D-30, D-32, D-33, D-45, D-48,
  D-51, D-68, D-76, D-78, D-91. The manifest's `Type` column says `table` for each, and the prompt
  is explicit that a Markdown table is the correct rendering and no SVG file is required — the
  `D-NN` id still appears at that point in the prose, in a bold caption line under the table, so
  the id is accounted for.
- Every diagram was rendered with `qlmanage` and looked at before being reported. Scratch PNGs live
  in `tmp/21-render/`, never in `diagrams/`, because `rm` is denied in this session.

**Note for anyone running the `notes-generator` verify script over this topic:** its diagram block
does `ls diagrams/$id-*.svg` for every `D-NN` found in the prompt and will therefore report 15
failures, one per table-type id. Those are expected and correct. The prompt overrides the script
here.

### Final verification, run against the written set

| Check | Result |
|---|---|
| Note files / total lines | **111 files, 47,143 lines** |
| Syllabus leaves covered | **468 of 468**, computed by parsing every file's `**Leaves covered:**` footer against the prompt's leaf list. Zero deferred |
| Manifest ids accounted for | **99 of 99** — 84 as SVGs (128 files, counting frame series), 15 as Markdown tables with the id in a bold caption |
| Orphaned SVGs | none — every one of the 128 files is embedded by at least one note file |
| Broken diagram embeds | none — every `../diagrams/…` and `diagrams/…` path resolves |
| Files over the 600-line ceiling | one, deliberately: `92-interview-internals.md` at 666 lines, because the prompt requires it to keep the 423-bullet topic-wide checklist and forbids moving it |
| Atomic concept checklist | present at the end of `92-interview-internals.md`, **423 flat bullets**, zero nested, no duplicate copy anywhere |
| Interview Q&A counts | 90: **12** · 91: **18** · 92-b: **22** · 93: **10** · 94-d: **10** — each with exactly **5** puzzles, matching the computed requirement |
| Required closing sections | every note file carries `## Pitfalls`, `## Cheat sheet`, `## Self-test`, `## Open questions` and the full footer, with 5–10 folded self-test answers |
| Emojis / inline `<svg>` / elisions | none |
| Banned throwaway names | none |
| QuizStakes contamination | none. Two writers leaked a `com.quizstakes` Java package into example paths; corrected to `com.invoiceledger`, this topic's own service |
| JSON blocks | **156 fenced JSON blocks, all parse** |
| Java blocks | zero `...` elisions, zero "implementation omitted" |
| `and so on` | removed from all six note-file occurrences; the one remaining instance is inside the verbatim leaf ledger, quoting the prompt's own rule against it |
| sdlc-harness repository | **unmodified** — no file changed since before this run |

### Diagram substitutions

A substitution is recorded when an illustrator reports a manifest id as not renderable as a picture.

_None._ No illustrator returned `blocked`; all 84 pictorial ids were authored as specified.

### Diagram corrections

Writers re-verify `[DOC]` claims against the live documentation at write time. Where that turned up a
figure a diagram had taken from the stale syllabus, the **diagram** is the thing that is wrong — the
manifest was written from the same work order, and the prompt's authority order puts the docs above
it. Corrections applied and pending:

| Diagram | Defect | Status |
|---|---|---|
| D-46 | Printed arithmetic worked out to `45,800 / 45,000 ≈ 1.02×` while the file name and `aria-label` claimed 2×, and leaf §2.1.19 states 2×. The re-supplied context was drawn as negligible against the work | **Fixed.** Re-authored so the marginal-cost division reads `8,000 / 4,000 = 2.0×`, with the resident cached prefix drawn but explicitly excluded from the ratio, and the `aria-label` agreeing. `subagents/04-limits-and-cost.md` was then re-dispatched to match and to add the leaf's `3–4×` team figure, which the first pass had omitted |
| D-50 | Canvas stated **32** events; a writer re-verifying `hooks` found **33**, the additions being `PreModelSwitch` and `PostModelSwitch` | **Fixed.** Both events added to the context/model group, count and `aria-label` updated to 33, version kept on the canvas. Filename left as `D-50-32-events-grouped.svg` deliberately — five files already embed that path, and the slug is cosmetic where the canvas text is not |
| D-71 | Canvas used `skillListingBudgetFraction` = **0.05**; the documented default is **0.01**. The caption also said further skills are "dropped from the listing", where the docs are more precise | **Fixed.** Set to 0.01, and **the dependent arithmetic re-derived**: the cap is now 0.01 × 200,000 = **2,000 tokens**, binding at **≈5 skills** rather than 26. The per-skill 384-token figure and the 19,200 total at 50 are unchanged, since they derive from the separate per-entry 1,536-character cap. Annotation reworded to "descriptions of the least-invoked skills drop first — names never drop". `request-assembly/03-internals-b` reconciled, and the ≈5-skill binding point is now foregrounded as the more interesting finding |
| D-96 | Labelled the three ceiling exception types `ClaudeTimeoutException` and siblings; the set settled on `AgentTimeoutException`, `AgentTurnLimitException`, `AgentBudgetExceededException`, which is what D-78's table and the §4.5 Java all use | **Fixed.** Relabelled on the canvas and in the `aria-label` to the names the compiled Java actually uses. `build-it/05-orchestrator-a` reconciled |
| D-88d | Labelled `gaps-analyzer-agent`'s read path as `src/notes/detailed/<topic>/**`; that agent's own spec declares its inputs as `src/topics/*.md` plus several `tmp/` evidence paths | **Fixed.** Relabelled from the agent's own spec, read directly: `src/topics/*.md`, `tmp/valuations/*.md`, `tmp/papers/answers/*.txt`, `tmp/gaps.md`, `tmp/primers/*.md`, `tmp/qbank/*.md`, with the write path `src/knowledge/gaps.md` still visibly disjoint. `orchestration/03-internals-a` reconciled and its `## Open questions` is now `None.` |
| D-69 | Drew the environment/git snapshot as an already-separate segment; `cli-reference` says those per-machine facts sit **inside** the default system prompt, and `--exclude-dynamic-system-prompt-sections` moves them **into the first user message** | **Fixed.** The snapshot is now nested inside the system-prompt block, with the flag drawn as the thing that relocates it into the first user message; cached-prefix bracket now spans segments 1–3 and segment 1's total is ≈3,030 tokens. `request-assembly/03-internals-a` reconciled |

---

## Findings on the paths the prompt flagged as unconfirmable

The prompt instructs the writer to look and report rather than assert. Probed at planning time
against the read-only checkout; these findings are handed to the owning writers in their packets.

| Path as the syllabus cites it | Finding |
|---|---|
| `harness/evals/seeded-defects` | **Present.** A real directory at `harness/evals/seeded-defects`. `harness/evals/` also holds `code-to-commit/`, `baselines.yaml`, `corpus.yaml`, `README.md`. |
| `features/<slug>/state/harness.db` | **Not present in a clean checkout — and correctly so: it is a runtime artefact created per feature slug.** The path itself is authoritative and documented: `plugins/sdlc-harness/commands/run-conductor.md:32` states "The state db defaults to `features/<slug>/state/harness.db`", and `commands/run-harness.md` uses it in a dozen `python3 -m harness.state.cli` invocations. `tests/smoke/init-harness-docker/canned-smoke.py:57` constructs `state/harness.db` under a tmp path. Write it as the documented default location of a runtime-created append-only state log, not as a file in the repo. |
| `severity_map.yaml` | **Present, at a different path than the syllabus implies.** It is `harness/calibration/severity_map.yaml`, alongside `harness/calibration/improvement-log.yaml` — **not** under `control-plane/judge-rubrics/`. State the real path. |
| `filed-bugs.yaml` | **Not present in the checkout; its authoritative path is recorded in the repo's own prose.** `plugins/sdlc-harness/agents/calibrator.md:28` names `harness/calibration/friction/filed-bugs.yaml` as the "team-lead-owned dedup ledger", and `commands/calibrate.md` references it at lines 44, 50, 73, 95 and 106. Like `harness.db` it is written at runtime. |
| `control-plane/judge-rubrics/*.yaml` | **Present — six files**, not five: `progress-verifier.yaml`, `code-review.yaml`, `story-reviewer.yaml`, `prd-reviewer.yaml`, `requirements.yaml`, `functional-tests-reviewer.yaml`. |

Two further corrections found at planning time, both already right in the prompt but worth pinning:

- `plugins/sdlc-harness/scripts/` holds **fifteen** `bootstrap-*.sh` files, not fourteen
  (`bootstrap-functional-tests.sh`, `-glab`, `-handbook-skills`, `-handbook`, `-link-service`,
  `-lsp`, `-mmdc`, `-playwright-skills`, `-plugin-update`, `-pre-commit`, `-services-scaffold`,
  `-user-scope`, `-uv`, `-workspace`, `-write-version`), plus three `triage-*.sh`
  (`triage-aws-ro.sh`, `triage-preflight.sh`, `triage-report-lint.sh`). They are under `scripts/`,
  **not** `hooks/`.
- `playwright-cli` is a **repo-root** skill at `.claude/skills/playwright-cli/`, not a plugin skill.
  The plugin ships three skills: `bootstrap`, `compose-playbook`, `prod-triage`.

---

## The evidence policy, and the one place it was retro-fitted

**Policy in force:** for a `[PROVE]` or `[BUILD]` leaf, either **really run it** — a real transcript
pasted verbatim plus the command that produced it — or say **"not measured here"** at the point of the
claim, in the body, with the exact command the reader should run, and record it in `## Open questions`
as well. **Never a derived figure in the visual position a measured one belongs.**

Most PART 4 writers converged on the first option unprompted and went further than the contract
required: real `claude -p` envelopes with real `total_cost_usd`, a real NUL-byte reproduction, a
`Semaphore` bulkhead timed at 36.1s against 9.1s, two plugins installed side by side to prove the
`.claude-plugin/` layout trap (`Skills(4)` against `Skills(0)`), and a compiled `ClaudeRunner` driven
through all four failure paths. Where they could not run something — an interactive `/context` grid, a
nested `claude` refused by the classifier — they quoted the real refusal and marked the gap.

**One file needed retro-fitting: `mcp-and-lsp/03-lsp.md`, §2.4.13.** Its prove step originally reused
D-56's generic +3,100 tokens-per-turn delta as a stand-in for a measurement it had not taken. It was
labelled as derived, but the number sat where a measured one belongs — and that is a counter-example
to §3.10's own laws sitting inside the same guide, which a level-zero reader could not detect.

It is now **measured.** `atlassian-cloud` needs an OAuth grant the sandbox cannot complete, so rather
than fake around it the writer registered a credential-free stdio server
(`@modelcontextprotocol/server-filesystem`) in a `/tmp` scratch project and measured the real
before/after from the `-p --output-format json` envelope's own token fields, since no TTY was
available for the interactive screen either: **21,648 tokens before, 21,982 after — a measured +334
tokens per turn.** `atlassian-cloud`'s own delta is now explicitly flagged as unmeasured, with the
repeatable command sequence given inline and in `## Open questions`, and the substitution stated
plainly. The server was deregistered afterwards and the return to baseline confirmed. No D-56-derived
figure remains in the leaf.

## Leaf coverage: two numbers, and why both matter

**468 of 468 against the source prompt. 468 of 477 against the current syllabus.** Both are true and
the second is the one that describes remaining scope.

The prompt was cut from a 468-leaf syllabus. After it was cut, nine leaves were added to
`src/syllabus/21-ai-for-coding.md` — five for the hook-output schema and four for the
`acceptEdits` / `bypassPermissions` / workspace-trust / listing-budget corrections, including new
lettered sub-leaves. **Every writer packet on this run was cut from the prompt, so no writer ever saw
those nine.** "468 of 468" is therefore complete delivery against the work order, and **not** complete
coverage of current scope.

The nine split cleanly into two groups, and the distinction is what a resumed run needs:

### Discharged in prose — the fact is already correct in the notes

These were found by writers re-verifying against the live documentation, so the notes already state
the corrected fact, flag the divergence, and in most cases carry it as a `**Pitfall:**` or a
version-trap row. A rebuild should confirm the leaf is satisfied rather than commission new writing.

| New leaf | Substance | Where it is already discharged |
|---|---|---|
| §1.4.26 revision + 1.4.26a/b | the wider `acceptEdits` set including `rm`/`rmdir`/`sed`; that "accept edits" auto-approves deletion; the `mvn`/`git commit`/`chmod`/`java` gap | `permissions/05-modes.md`, and the gap is the spine of `setting-sources-incident/03-internals-a-the-failure.md` |
| §1.4.28 revision + 1.4.28a | what `bypassPermissions` actually refuses, and that protected-path writes **are** allowed — so the mode can rewrite the configuration that would otherwise constrain it | `permissions/05-modes.md`, carried as a `**Pitfall:**` against the stale form |
| §1.4.34 revision + 1.4.34a | the real `-p`/SDK trust mechanics, and the relocated risk: trust is sticky per repository-root path and never re-checked when a commit widens the ruleset | `permissions/06-directories-and-trust.md`, which found the relocated risk independently; also `sdk-and-api/03-internals-a-three-levels.md` for the SDK case |
| §1.5.6 revision | `skillListingMaxDescChars` (per-entry, 1,536 chars) and `skillListingBudgetFraction` (a separate pool budget) are two different numbers | `skills/02-frontmatter-and-invocation.md` |
| §1.4.27 revision | the `auto` classifier's model and its 3-consecutive / 20-total fallback thresholds | `permissions/05-modes.md` |
| §1.5.19 revision | `playwright-cli` is repo-root, with **nine** reference files | `skills/05-cases.md`, which counted them rather than trusting the prose |
| §1.5.20 revision | `scripts/` not `hooks/`, **fifteen** `bootstrap-*.sh` plus three `triage-*.sh` | `skills/05-cases.md`, `deterministic-vs-agentic/02-cases-idempotence.md` |
| §1.5.23 revision | built-ins versus bundled skills, with the tags the right way round | `skills/06-builtins-and-decision-table.md` |

### Genuinely new scope — a rebuild should commission writing

| New leaf | Substance | Status |
|---|---|---|
| §2.3.14 split into three field kinds | universal top-level, top-level `decision`/`reason`, nested `hookSpecificOutput` | **Written.** `hooks/03-payloads-and-exit-codes.md`'s field table was restructured into exactly these three groups during the correction pass |
| §2.3.14a — the universal `continue` kill switch | `continue: false` stops Claude entirely and outranks any event-specific decision; `stopReason` is shown to the user, not Claude | **Written**, in `hooks/03` |
| §2.3.14b — the 10,000-character output cap | on `additionalContext`, `systemMessage` and plain stdout, with spill-to-file | **Written**, in `hooks/03` |
| §2.3.15 real per-event table + §2.3.15a the inverted-semantics `[TRAP]` | `decision: "block"` prevents stopping; to keep Claude working you block the stop | **Written**, in `hooks/02`, `hooks/04`, `95-trap-index.md` (trap row 155) and `93-interview-build-it.md` |
| §2.3.15b — `additionalContext` as the third path | conversation continues, labelled `Stop hook feedback` rather than a hook error | **Written**, in `hooks/02`/`hooks/03` |
| §2.3.15c — the loop protections | `stop_hook_active` and the 8-consecutive-block cap | **Written**, in `hooks/02`, `build-it/02-three-hooks-b.md`, `verification/03-internals-c`, `93-interview-build-it.md` |
| §4.2.4 revision — specify `decision: "block"` | the built `require-green-build.sh` must emit the real field | **Written and re-run.** `build-it/02-three-hooks-b.md`'s script was corrected and its four `Stop` payload transcripts re-captured |

**So: of the nine, all nine are substantively discharged in the notes** — the eight correction leaves
because writers found the same errors independently, and the hook-schema group because the correction
pass wrote them explicitly. What a rebuild buys is the *syllabus* agreeing with the notes, and leaf
numbering a future reader can cite. It does not buy missing content.

## The hook-output schema correction, and the process law it produced

**Three independent agents on this run described the `Stop` / `SubagentStop` decision field three
different wrong ways before anyone read the actual page.** In order: a boolean `continue`; then
`continue: true` / `continueReason`; then `decision: "continue"` / `continueReason` — each written by
an agent that believed it was *correcting* its predecessor, and each derived from a WebFetch summary
of the `hooks` reference table.

**The real schema, verified by fetching `https://code.claude.com/docs/en/hooks.md` as raw markdown
(`curl -sL`) and reading the `## JSON output` common-fields table and `#### Stop decision control`
directly, on 2026-08-30:**

- **`decision: "block"` prevents Claude from stopping.** Omit it to allow the stop.
- **`reason` is required when `decision` is `"block"`.**
- `hookSpecificOutput.additionalContext` is a third path — the conversation continues under the same
  loop protections, but the transcript labels it `Stop hook feedback` rather than raising a hook error.
- The boolean **`continue` is a universal kill switch on every event**: `continue: false` stops Claude
  entirely and **takes precedence over any event-specific decision field**. `stopReason` pairs with it
  and is shown to **the user, not to Claude**.
- There is **no `continueReason`**, **no `decision: "continue"`**, and **no
  `hookSpecificOutput.continue`** anywhere in the schema.

**The trap, which is why three readings failed: to keep Claude working you block the stop.** The
semantics are inverted from the intuitive reading. It is now carried as a trap row in
`95-trap-index.md`, in its version-stale table, and as an interview answer in
`93-interview-build-it.md`.

**Two facts nobody had at all**, both now in the notes: `Stop` hooks receive `stop_hook_active`, and
**Claude Code overrides the hook after 8 consecutive blocks** — so a `Stop` hook that does not check
it is an infinite-turn generator, which is the honest mechanical answer to why a slow gate there is
dangerous. And hook output strings — `additionalContext`, `systemMessage`, plain stdout — are capped
at **10,000 characters**, with overflow written to a file and replaced by a preview plus path.

**Nine files were corrected**, in three grouped passes so the semantics moved coherently rather than
file by file: `hooks/02`, `hooks/03`, `hooks/04`, `build-it/02-three-hooks-b`,
`build-it/08-verification-harness-a`, `build-it/08-verification-harness-b`, `verification/03-internals-c`,
`93-interview-build-it`, `95-trap-index`. `build-it/06-orchestrator-c` and `headless/03-internals-c`
were triaged and left alone — their `continue` mentions are about retry continuation, not hooks.

Because two of those files prove their artefacts by captured transcript, **their scripts were fixed
and re-run rather than hand-edited**: `require-green-build.sh` against all four `Stop` payload cases
including the `stop_hook_active` loop guard, and `verify-on-stop.sh` against its clean and broken
fixtures. Editing a transcript into the new shape would have been fabricated evidence, in files that
teach §3.10's laws against exactly that.

Every remaining occurrence of the wrong forms across the set is deliberate — a trap row, a
negation, or an explicit correction note. `verification/03-internals-c` says plainly that its own
earlier correction pass was also wrong, because a file claiming a fix while still carrying an error is
worse than the original.

### The process law

**A WebFetch summary of a reference table is not a citable source.** It is a small model's
reconstruction of a schema, and it will invent plausible field names. For anything shaped like an API
contract — a field table, an enum, a JSON schema — **fetch the raw `.md` and grep it.** This applies
to every topic in this repository, not just this one.

## Findings the run produced that the report should carry

Three things worth surfacing beyond the per-leaf divergences below.

**The `[INCIDENT]` count is 10, not 11.** The prompt's incident list names eleven, but reading every
tagged section found ten distinct events: *"the md5 taken over a patched harness"* and *"the unpinned
digest"* name the same real event — §3.10.4's incident, restated as §3.10.5's generalised law — rather
than two. `95-trap-index.md` records the collapse explicitly instead of padding the count back to 11.

**The trap inventory is far larger than the prompt's estimate.** The prompt expects roughly 45
`[TRAP]` leaves. Grepping `**Pitfall:**` across the finished set returns 167 raw matches, of which
**154 are distinct traps** — because writers used the marker for every wrong belief a leaf surfaced,
not only on `[TRAP]`-tagged leaves. All 154 are in the consolidated table.

**Writers repeatedly found the syllabus stale, which is the pipeline working as designed.** Better
than twenty leaves were corrected against the live documentation or the installed v2.1.251 binary at
write time. Several writers went further than the contract required and *ran* the thing — real
`claude -p` invocations with real `total_cost_usd` figures, a real NUL-byte reproduction, a real
`Semaphore` bulkhead timed by wall clock, two plugins installed side by side to prove a layout trap,
and a real compiled Java `ClaudeRunner` exercised against all four of its failure paths. Where a
writer could not observe something — an interactive `/context` grid, a nested `claude` call refused by
the classifier — it said so and marked the claim rather than inventing output.

## Divergences from the syllabus, found at write time

The prompt sets the authority order as **the official documentation > observed behaviour of the
installed binary > the repository's own code > blog posts**, and says explicitly that the syllabus
"is a work order, not a citable source: it was verified on 2026-08-29 and is already ageing." These
are the places a writer re-verified a leaf and found the leaf itself stale or incomplete. In each
case the notes state what the documentation currently says, and flag the divergence.

| Leaf | What the syllabus says | What the docs say at write time | Where it is handled |
|---|---|---|---|
| §1.4.28 | `bypassPermissions` still refuses protected paths such as `.git` and `.claude` | It **allows** protected-path writes. What it still refuses is critical-path `rm`/`rmdir` deletions, explicit `ask`-rule matches, always-interactive tools (`AskUserQuestion`, `requiresUserInteraction` MCP tools), and two cross-session messaging safeguards (`isolatePeerMachines`, held inbound messages) | `permissions/05-modes.md`, stated correctly and carried as a `**Pitfall:**` against the stale form |
| §1.4.26 | `acceptEdits` covers `mkdir`, `touch`, `mv`, `cp` | The auto-approved set is broader: `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed` | `permissions/05-modes.md`, with the wider list printed |
| §1.4.27 | `auto` mode runs a background classifier | Confirmed, and the docs add defaults the syllabus omits: the classifier runs on Sonnet 5, with 3-consecutive / 20-total block fallback thresholds | `permissions/05-modes.md` |
| §1.4.34 | a `-p` or SDK session never shows the trust dialog and **counts as accepted**, so a repository's committed `allow` rules run unreviewed in automation | The docs say the opposite for an untrusted folder: a `-p`/SDK session does **not** apply committed `allow` / `additionalDirectories` rules, and prints a stderr warning instead. "Counts as accepted" refers only to the narrower git tracked/untracked check on `settings.local.json` | `permissions/06-directories-and-trust.md`, which writes the corrected mechanics, flags the divergence inline, and relocates the real risk: trust is sticky per repository-root path and is never re-checked when a commit changes the ruleset |
| §1.5.6 | `skillListingBudgetFraction` and `skillListingMaxDescChars` tune "the listing" | They tune two **different** numbers: `skillListingMaxDescChars` is the 1,536-character per-entry cap; `skillListingBudgetFraction` is a separate pool budget (~1% of the context window) across all entries | `skills/02-frontmatter-and-invocation.md` |
| §1.5.19 | the `playwright-cli` skill has **ten** reference files | Nine on disk. The filenames are listed as found rather than padded to ten | `skills/05-cases.md` |
| §1.5.23 | the inventory implies `/doctor` and `/rewind` are built-ins and `/run` is a bundled skill | The reverse: `/doctor` and `/rewind` are bundled **skills** (tagged `[Skill]`), and `/run` is a **built-in** | `skills/06-builtins-and-decision-table.md` |
| §1.1.7 / §1.5.20 | the `bootstrap-*.sh` scripts, "fourteen files" | **Fifteen** `bootstrap-*.sh` under `plugins/sdlc-harness/scripts/` (not `hooks/`), plus three `triage-*.sh` | `claude-folder/01-basics-anatomy.md`, `skills/05-cases.md` |

This is the pipeline working as intended, not a defect in it: a version-volatile topic whose writers
re-verify will find drift, and finding it is the whole point of the `[DOC]` / `[RESEARCH]`
obligation.

## Open questions

Claims marked `**Unverified:**` in any note file are collected here as envelopes return.

1. `ground-zero/01-basics-what-the-model-is.md` — the per-string token counts in the D-02 table
   (20 / 44 / 38) are manually segmented estimates, not output from Anthropic's production
   tokenizer. Settled by running the three literal strings through the tokenizer endpoint or the
   `count_tokens` API and substituting the returned figures. The chars-per-token *ratios* the leaf
   actually turns on — prose ~3–4, code and minified JSON visibly worse — are unaffected.
2. `ground-zero/02-basics-context-window-b.md` — the compaction-trigger percentage for a 200K
   window is extrapolated from Sonnet 5's documented 1M-window figure (~967K/1M ≈ 96.7%); no
   explicit 200K percentage is published. Settled by reading `/context` on a 200K-window session as
   it approaches autocompaction, or by a documented figure for the 200K tier.
3. `ground-zero/03-basics-the-agent-loop.md` — which built-in Claude Code tools ship non-deferred
   versus deferred behind `ToolSearch` in v2.1.2xx is not enumerated on the pages checked; the
   mechanism and the token saving are documented, the concrete membership is not. Settled by
   reading `/context`'s tool rows on a stock session, or by a doc page that lists the split.
4. `ground-zero/04-basics-orientation.md` — three items: the `#` prefix as a save-to-memory
   shortcut is not found in the `commands`, `interactive-mode` or `memory` pages; and the exact
   introduction versions of `--safe-mode` / `--bare` and of `fileCheckpointingEnabled` are not
   stated in the docs. Settled by `claude --help` against an installed binary and by the release
   notes for the version that introduced each.
5. `claude-folder/01-basics-anatomy.md` — whether a bare, hand-authored `.claude/.lsp.json` outside
   any plugin is read as a standalone project artefact. The docs describe LSP configuration only via
   the plugin-shipped mechanism. Settled by placing one and reading `/doctor` or `claude --debug` on
   an installed binary.
6. `memory/04-your-own-instruction-files.md` — the per-session dollar figure in the cost note
   assumes a published input list price rather than a figure from this topic's re-verifiable doc set;
   `settings`, `settings-reference` and `memory` carry no pricing. The assumed rate and the date are
   stated inline. Settled by the pricing page, which is deliberately outside this topic's citation
   set, or by reading `/cost` on a real session.
7. `permissions/07-precedence-and-overrides.md` — the literal rendering of the `/permissions` dialog
   is not reproduced, because `/permissions` is interactive-only and no live session was available.
   The rule-source lookup was proven instead by a real script whose captured output is in the file.
   Settled by a screenshot or transcript of the dialog on an installed binary.
8. `skills/06-builtins-and-decision-table.md` — the `/context` before/after deltas for the
   `checklist-refresh` skill are computed from real measured byte counts (`SKILL.md` 2,131 bytes,
   references file 1,339 bytes, frontmatter listing 215 characters) using this guide's 4-characters-
   per-token estimate, not read off a live `/context` screen. Settled by invoking the skill in a live
   session and reading `/context` before and after.

---

## Deferred

**No leaf and no diagram is deferred.** All 468 prompt leaves are covered, all 99 manifest ids are
accounted for, and all four diagram corrections are applied.

### One item deferred to the user: a cleanup sweep

`rm` is denied to this session, and this project treats deletion as a human action, so the scratch
material below is left in place rather than removed. **It is all outside the deliverable** — nothing
under `src/notes/detailed/21-ai-for-coding/` needs deleting.

Two things accumulated:

- **`tmp/21-render/` — 123 PNGs, about 23 MB. Retained by the user's decision; not an open item.**
  The `## Diagram spec` asks an illustrator to rasterise, look, fix and then delete; across 21
  batches they did the first three and could not do the fourth, because `rm` is denied in this
  session. They were redirected out of `diagrams/` into scratch precisely so the deliverable stayed
  clean, which it is — **zero PNGs inside `diagrams/`**. The renders are the visual evidence behind
  every "rendered and looked at" claim in this run, so retaining them is defensible.
- **Two superseded originals**, retired there when their rows were re-split rather than deleted:
  `superseded-02-basics-context-window.md` and `superseded-03-path-web-mcp-agent-rules.md`.

The sweep, safe to run as one command:

```bash
rm -rf /Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-render
```

Writers also built and ran real artefacts under `/tmp`, which the OS clears on reboot. Removable now
if you prefer:

```bash
rm -rf /tmp/21-b4-01 /tmp/21-hooks-scratch /tmp/21-plugin-scratch /tmp/21-skills-scratch \
       /tmp/21-subagents-scratch /tmp/21-verify-harness-demo /tmp/claude-runner-test /tmp/drill-535
```

**Keep `tmp/21-contract/`.** It holds the verbatim writer and illustrator contracts, the per-row leaf
files, the diagram batches and `hook-output-schema-VERIFIED.md`. A resumed or rebuilt run reads from
it, and `split-leaves.sh` regenerates any row's leaf file.

---

## Leaf ownership

**Derived from each file's `**Leaves covered:**` footer**, so every row points at a file that exists.
Every one of the source prompt's 468 leaves is owned by exactly one file; see
`## Leaf coverage: two numbers` above for why the current syllabus scope is 477 rather than 468.

| Leaves | Owning file |
|---|---|
| 0.1.1–0.1.12 (12 leaves) | `ground-zero/01-basics-what-the-model-is.md` |
| 0.2.1–0.2.7 (7 leaves) | `ground-zero/02-basics-context-window-a.md` |
| 0.2.8–0.2.12 (5 leaves) | `ground-zero/02-basics-context-window-b.md` |
| 0.3.1–0.3.12 (12 leaves) | `ground-zero/03-basics-the-agent-loop.md` |
| 0.4.1–0.4.10 (10 leaves) | `ground-zero/04-basics-orientation.md` |
| 1.1.1–1.1.9 (9 leaves) | `claude-folder/01-basics-anatomy.md` |
| 1.2.1–1.2.8 (8 leaves) | `settings/01-basics-files-and-precedence.md` |
| 1.2.9–1.2.16 (8 leaves) | `settings/02-keys-and-verification.md` |
| 1.3.1–1.3.13 (13 leaves) | `memory/01-basics-claude-md.md` |
| 1.3.14–1.3.20 (7 leaves) | `memory/02-rules-and-path-scoping.md` |
| 1.3.21–1.3.28 (8 leaves) | `memory/03-auto-memory.md` |
| 1.3.29 (1 leaf) | `memory/04-your-own-instruction-files.md` |
| 1.4.1–1.4.10 (10 leaves) | `permissions/01-basics-rules-and-order.md` |
| 1.4.11–1.4.15 (5 leaves) | `permissions/02-bash-matching.md` |
| 1.4.16–1.4.19 (4 leaves) | `permissions/03-path-rules.md` |
| 1.4.20–1.4.24 (5 leaves) | `permissions/04-web-mcp-agent-and-cd-rules.md` |
| 1.4.25–1.4.29 (5 leaves) | `permissions/05-modes.md` |
| 1.4.30–1.4.34 (5 leaves) | `permissions/06-directories-and-trust.md` |
| 1.4.35–1.4.38 (4 leaves) | `permissions/07-precedence-and-overrides.md` |
| 1.4.39–1.4.41 (3 leaves) | `permissions/08-sandbox-and-a-real-block.md` |
| 1.5.1–1.5.5 (5 leaves) | `skills/01-basics-what-a-skill-is.md` |
| 1.5.6–1.5.10 (5 leaves) | `skills/02-frontmatter-and-invocation.md` |
| 1.5.11–1.5.14 (4 leaves) | `skills/03-substitution-and-injection.md` |
| 1.5.15–1.5.18 (4 leaves) | `skills/04-lifecycle-and-supporting-files.md` |
| 1.5.19–1.5.22 (4 leaves) | `skills/05-cases.md` |
| 1.5.23–1.5.26 (4 leaves) | `skills/06-builtins-and-decision-table.md` |
| none exclusively — this file closes §0.1–§1.5 (167 leaves), each written up in its own note file | `90-interview-basics.md` |
| 2.1.1–2.1.5 (5 leaves) | `subagents/01-basics-definition-and-precedence.md` |
| 2.1.6–2.1.10 (5 leaves) | `subagents/02-the-context-boundary.md` |
| 2.1.11–2.1.15 (5 leaves) | `subagents/03-builtins-and-forks.md` |
| 2.1.16–2.1.19 (4 leaves) | `subagents/04-limits-and-cost.md` |
| 2.1.20–2.1.22 (3 leaves) | `subagents/05-cases-pointer-bodies.md` |
| 2.1.23–2.1.25 (3 leaves) | `subagents/06-write-boundaries-and-protocol.md` |
| 2.2.1–2.2.4 (4 leaves) | `personas/01-the-four-flags.md` |
| 2.2.5–2.2.7 (3 leaves) | `personas/02-cases-persona-loading.md` |
| 2.3.1–2.3.5 (5 leaves) | `hooks/01-basics-what-a-hook-is.md` |
| 2.3.6–2.3.9 (4 leaves) | `hooks/02-the-event-catalogue.md` |
| 2.3.10–2.3.14 (5 leaves) | `hooks/03-payloads-and-exit-codes.md` |
| 2.3.15–2.3.17 (3 leaves) | `hooks/04-a-hook-cannot-unblock-a-deny.md` |
| 2.3.18–2.3.20 (3 leaves) | `hooks/05-configuration-sources.md` |
| 2.3.21–2.3.24 (4 leaves) | `hooks/06-cases-advisory-and-defensive.md` |
| 2.3.25, 2.3.27 (2 leaves) | `hooks/07-the-reindex-incident.md` |
| 2.3.26, 2.3.28 (2 leaves) | `hooks/08-the-blocking-guard-pattern.md` |
| 2.4.1–2.4.5 (5 leaves) | `mcp-and-lsp/01-basics-transports-and-scopes.md` |
| 2.4.6–2.4.10 (5 leaves) | `mcp-and-lsp/02-the-per-turn-tax.md` |
| 2.4.11–2.4.13 (3 leaves) | `mcp-and-lsp/03-lsp.md` |
| 2.5.1–2.5.4 (4 leaves) | `plugins/01-basics-structure.md` |
| 2.5.5–2.5.8 (4 leaves) | `plugins/02-namespacing-and-skills-dir.md` |
| 2.5.9–2.5.12 (4 leaves) | `plugins/03-marketplaces-and-dependencies.md` |
| 2.5.13–2.5.15 (3 leaves) | `plugins/04-governance.md` |
| 2.5.16–2.5.20 (5 leaves) | `plugins/05-cases-and-conversion.md` |
| 2.6.1–2.6.4 (4 leaves) | `context-economy/01-measuring-and-ranking.md` |
| 2.6.5–2.6.8 (4 leaves) | `context-economy/02-bounding-and-compaction.md` |
| 2.6.9–2.6.12 (4 leaves) | `context-economy/03-isolation-arithmetic.md` |
| 2.7.1–2.7.4 (4 leaves) | `practices/01-plan-mode-and-test-first.md` |
| 2.7.5–2.7.8 (4 leaves) | `practices/02-prompting-and-context.md` |
| 2.7.9–2.7.12 (4 leaves) | `practices/03-review-skills-and-interface.md` |
| 2.8.1–2.8.5 (5 leaves) | `deterministic-vs-agentic/01-the-central-judgment.md` |
| 2.8.6–2.8.9 (4 leaves) | `deterministic-vs-agentic/02-cases-idempotence.md` |
| 2.9.1–2.9.4 (4 leaves) | `governance/01-the-threat-model.md` |
| 2.9.5–2.9.8 (4 leaves) | `governance/02-the-lock-family.md` |
| 2.9.9–2.9.11 (3 leaves) | `governance/03-secrets-attribution-review.md` |
| none exclusively — this file closes §2.1–§2.9 (137 leaves), each written up in its own note file | `91-interview-intermediate.md` |
| 3.1.1–3.1.4 (4 leaves) | `request-assembly/03-internals-a-assembly-order.md` |
| 3.1.5–3.1.8 (4 leaves) | `request-assembly/03-internals-b-listing-and-transcripts.md` |
| 3.2.1–3.2.4 (4 leaves) | `compaction/03-internals-a-the-budget.md` |
| 3.2.5–3.2.7 (3 leaves) | `compaction/03-internals-b-hooks-and-control.md` |
| 3.3.1–3.3.4 (4 leaves) | `permission-evaluation/03-internals-a-the-pipeline.md` |
| 3.3.5–3.3.8 (4 leaves) | `permission-evaluation/03-internals-b-traced-commands.md` |
| 3.4.1–3.4.4 (4 leaves) | `cost-model/03-internals-a-the-four-quantities.md` |
| 3.4.5–3.4.9 (5 leaves) | `cost-model/03-internals-b-ceilings-and-reading-it-back.md` |
| 3.5.1–3.5.6 (6 leaves) | `effort-and-routing/03-internals-routing.md` |
| 3.6.1–3.6.5 (5 leaves) | `headless/03-internals-a-the-surface.md` |
| 3.6.6–3.6.9 (4 leaves) | `headless/03-internals-b-formats-and-execution.md` |
| 3.6.10–3.6.14 (5 leaves) | `headless/03-internals-c-the-failure-taxonomy.md` |
| 3.6.15–3.6.18 (4 leaves) | `headless/03-internals-d-resolution-order.md` |
| 3.7.1–3.7.5 (5 leaves) | `setting-sources-incident/03-internals-a-the-failure.md` |
| 3.7.6–3.7.9 (4 leaves) | `setting-sources-incident/03-internals-b-the-fix-and-the-law.md` |
| 3.8.1–3.8.4 (4 leaves) | `sdk-and-api/03-internals-a-three-levels.md` |
| 3.8.5–3.8.8 (4 leaves) | `sdk-and-api/03-internals-b-java-and-the-dependency-contract.md` |
| 3.9.1–3.9.4 (4 leaves) | `orchestration/03-internals-a-shapes-and-fan-out.md` |
| 3.9.5–3.9.8 (4 leaves) | `orchestration/03-internals-b-executor-vs-conductor.md` |
| 3.9.9–3.9.12 (4 leaves) | `orchestration/03-internals-c-calibration-and-evals.md` |
| 3.10.1–3.10.4 (4 leaves) | `verification/03-internals-a-evidence-and-the-nul-byte.md` |
| 3.10.5–3.10.8 (4 leaves) | `verification/03-internals-b-the-sibling-laws.md` |
| 3.10.9–3.10.11 (3 leaves) | `verification/03-internals-c-automation-and-review-capacity.md` |
| none exclusively — this file closes §3.1–§3.10 (96 leaves) and carries the topic-wide atomic concept checklist over all six parts | `92-interview-internals.md` |
| none exclusively — this file carries PART 3's Q&As and puzzles; §3.1–§3.10's summary table and the topic-wide checklist live in `92-interview-internals.md` | `92-interview-internals-b.md` |
| 4.1.1–4.1.3 (3 leaves) | `build-it/01-a-claude-folder-a.md` |
| 4.1.4–4.1.5 (2 leaves) | `build-it/01-a-claude-folder-b.md` |
| 4.2.1–4.2.3 (3 leaves) | `build-it/02-three-hooks-a.md` |
| 4.2.4–4.2.6 (3 leaves) | `build-it/02-three-hooks-b.md` |
| 4.3.1–4.3.3 (3 leaves) | `build-it/03-a-skill-and-a-command-a.md` |
| 4.3.4–4.3.6 (3 leaves) | `build-it/03-a-skill-and-a-command-b.md` |
| 4.4.1–4.4.3 (3 leaves) | `build-it/04-two-subagents-a.md` |
| 4.4.4–4.4.5 (2 leaves) | `build-it/04-two-subagents-b.md` |
| 4.5.1–4.5.2 (2 leaves) | `build-it/05-orchestrator-a-the-runner.md` |
| 4.5.3–4.5.4 (2 leaves) | `build-it/05-orchestrator-b-ceilings-and-resolution.md` |
| 4.5.5–4.5.6 (2 leaves) | `build-it/06-orchestrator-c-bulkhead-and-retry.md` |
| 4.5.7–4.5.8 (2 leaves) | `build-it/06-orchestrator-d-pipeline-and-cost.md` |
| 4.6.1–4.6.3 (3 leaves) | `build-it/07-a-plugin-a.md` |
| 4.6.4–4.6.6 (3 leaves) | `build-it/07-a-plugin-b.md` |
| 4.7.1–4.7.2 (2 leaves) | `build-it/08-verification-harness-a.md` |
| 4.7.3–4.7.4 (2 leaves) | `build-it/08-verification-harness-b.md` |
| none exclusively — this file closes §4.1–§4.7 (40 leaves), each built in its own note file | `93-interview-build-it.md` |
| 5.1.1–5.1.4 (4 leaves) | `94-interview-questions-a.md` |
| 5.1.5–5.1.8 (4 leaves) | `94-interview-questions-b.md` |
| 5.1.9–5.1.12 (4 leaves) | `94-interview-questions-c.md` |
| 5.1.13–5.1.16 (4 leaves) | `94-interview-questions-d.md` |
| 5.2.1–5.2.4 (4 leaves) | `95-trap-index.md` |
| 5.3.1–5.3.8 (8 leaves) | `96-drills-and-review-schedule.md` |
## Derived row plan

The rows actually dispatched, under the ≤5-leaf rule (≤3 for PART 4). This table, not the OUTPUT
CONTRACT tables above, is what a resumed run works from: **dispatch every row whose `Status` is
`planned`.** Leaf text for each row is at `tmp/21-contract/leaves/<leaf file>.md`, extracted verbatim
from the prompt; a row's file contains only that row's leaves.

Where a row is not yet dispatched its leaf file may not exist yet — regenerate it with
`tmp/21-contract/split-leaves.sh <name> <first-leaf-id> <last-leaf-id>`.

### PART 0 and PART 1 — complete

| File | Leaves | Leaf file | Diagrams | Status | Lines |
|---|---|---|---|---|---|
| `ground-zero/01-basics-what-the-model-is.md` | 0.1.1–0.1.12 | `ground-zero-01` | D-01, D-02ᵗ, D-03a/b/c, D-04ᵗ, D-05 | written | 529 |
| `ground-zero/02-basics-context-window-a.md` | 0.2.1–0.2.7 | (from `ground-zero-02`) | D-06, D-07, D-08 | written | 444 |
| `ground-zero/02-basics-context-window-b.md` | 0.2.8–0.2.12 | (from `ground-zero-02`) | D-09, D-10 | written | 393 |
| `ground-zero/03-basics-the-agent-loop.md` | 0.3.1–0.3.12 | `ground-zero-03` | D-11a–d, D-12a–e, D-13, D-14 | written | 266 |
| `ground-zero/04-basics-orientation.md` | 0.4.1–0.4.10 | `ground-zero-04` | D-15, D-16ᵗ, D-17ᵗ | written | 301 |
| `claude-folder/01-basics-anatomy.md` | 1.1.1–1.1.9 | `claude-folder-01` | D-18, D-19a/b/c | written | 370 |
| `settings/01-basics-files-and-precedence.md` | 1.2.1–1.2.8 | `settings-01` | D-20, D-21 | written | 464 |
| `settings/02-keys-and-verification.md` | 1.2.9–1.2.16 | `settings-02` | D-22ᵗ | written | 436 |
| `memory/01-basics-claude-md.md` | 1.3.1–1.3.13 | `memory-01` | D-23a–e, D-24 | written | 493 |
| `memory/02-rules-and-path-scoping.md` | 1.3.14–1.3.20 | `memory-02` | D-25 | written | 527 |
| `memory/03-auto-memory.md` | 1.3.21–1.3.28 | (from `memory-03`) | D-26, D-27 | written | 487 |
| `memory/04-your-own-instruction-files.md` | 1.3.29 | (from `memory-03`) | — | written | 380 |
| `permissions/01-basics-rules-and-order.md` | 1.4.1–1.4.10 | `permissions-01` | D-28, D-29, D-30ᵗ | written | 462 |
| `permissions/02-bash-matching.md` | 1.4.11–1.4.15 | `permissions-02` | D-31a–d | written | 488 |
| `permissions/03-path-rules.md` | 1.4.16–1.4.19 | (from `permissions-03`) | D-32ᵗ | written | 414 |
| `permissions/04-web-mcp-agent-and-cd-rules.md` | 1.4.20–1.4.24 | (from `permissions-03`) | — | written | 414 |
| `permissions/05-modes.md` | 1.4.25–1.4.29 | `permissions-05` | D-33ᵗ | written | 429 |
| `permissions/06-directories-and-trust.md` | 1.4.30–1.4.34 | `permissions-06` | D-34 | written | 378 |
| `permissions/07-precedence-and-overrides.md` | 1.4.35–1.4.38 | `permissions-07` | — | written | 537 |
| `permissions/08-sandbox-and-a-real-block.md` | 1.4.39–1.4.41 | `permissions-08` | D-35 | written | 553 |
| `skills/01-basics-what-a-skill-is.md` | 1.5.1–1.5.5 | `skills-01a` | D-36, D-37 | written | 479 |
| `skills/02-frontmatter-and-invocation.md` | 1.5.6–1.5.10 | `skills-02a` | D-38 | written | 488 |
| `skills/03-substitution-and-injection.md` | 1.5.11–1.5.14 | `skills-03a` | D-39a/b/c | written | 348 |
| `skills/04-lifecycle-and-supporting-files.md` | 1.5.15–1.5.18 | `skills-04a` | D-40 | written | 433 |
| `skills/05-cases.md` | 1.5.19–1.5.22 | `skills-05a` | — | written | 399 |
| `skills/06-builtins-and-decision-table.md` | 1.5.23–1.5.26 | `skills-06a` | D-41 | written | 405 |
| `90-interview-basics.md` | wrap-up, §0.1–§1.5 | — | re-embeds | written | 377 |

ᵗ = rendered as a Markdown table, no SVG, per the manifest's `Type` column.

### PART 2 — planned

| File | Leaves | Leaf file | Diagrams | Status |
|---|---|---|---|---|
| `subagents/01-basics-definition-and-precedence.md` | 2.1.1–2.1.5 | `sub-01` | D-42 | written |
| `subagents/02-the-context-boundary.md` | 2.1.6–2.1.10 | `sub-02` | D-43 | written |
| `subagents/03-builtins-and-forks.md` | 2.1.11–2.1.15 | `sub-03` | D-44, D-45ᵗ | written |
| `subagents/04-limits-and-cost.md` | 2.1.16–2.1.19 | `sub-04` | D-46 | written |
| `subagents/05-cases-pointer-bodies.md` | 2.1.20–2.1.22 | `sub-05` | — | written |
| `subagents/06-write-boundaries-and-protocol.md` | 2.1.23–2.1.25 | `sub-06` | D-47 | written |
| `personas/01-the-four-flags.md` | 2.2.1–2.2.4 | `pers-01` | D-48ᵗ | written |
| `personas/02-cases-persona-loading.md` | 2.2.5–2.2.7 | `pers-02` | — | written |
| `hooks/01-basics-what-a-hook-is.md` | 2.3.1–2.3.5 | `hook-01` | D-49 | written |
| `hooks/02-the-event-catalogue.md` | 2.3.6–2.3.9 | `hook-02` | D-50, D-51ᵗ | written |
| `hooks/03-payloads-and-exit-codes.md` | 2.3.10–2.3.14 | `hook-03` | D-52 | written |
| `hooks/04-a-hook-cannot-unblock-a-deny.md` | 2.3.15–2.3.17 | `hook-04` | D-53 | written |
| `hooks/05-configuration-sources.md` | 2.3.18–2.3.20 | `hook-05` | D-54 | written |
| `hooks/06-cases-advisory-and-defensive.md` | 2.3.21–2.3.24 | `hook-06` | — | written |
| `hooks/07-the-reindex-incident.md` | 2.3.25–2.3.28 | `hook-07` | D-55a–d | written |
| `mcp-and-lsp/01-basics-transports-and-scopes.md` | 2.4.1–2.4.5 | `mcp-01` | — | written |
| `mcp-and-lsp/02-the-per-turn-tax.md` | 2.4.6–2.4.10 | `mcp-02` | D-56 | written |
| `mcp-and-lsp/03-lsp.md` | 2.4.11–2.4.13 | `mcp-03` | D-57 | written |
| `plugins/01-basics-structure.md` | 2.5.1–2.5.4 | `plug-01` | D-58 | written |
| `plugins/02-namespacing-and-skills-dir.md` | 2.5.5–2.5.8 | `plug-02` | — | written |
| `plugins/03-marketplaces-and-dependencies.md` | 2.5.9–2.5.12 | `plug-03` | D-59 | written |
| `plugins/04-governance.md` | 2.5.13–2.5.15 | `plug-04` | D-61 | written |
| `plugins/05-cases-and-conversion.md` | 2.5.16–2.5.20 | `plug-05` | D-60 | written |
| `context-economy/01-measuring-and-ranking.md` | 2.6.1–2.6.4 | `ctx-01` | D-62 | written |
| `context-economy/02-bounding-and-compaction.md` | 2.6.5–2.6.8 | `ctx-02` | — | written |
| `context-economy/03-isolation-arithmetic.md` | 2.6.9–2.6.12 | `ctx-03` | D-63 | written |
| `practices/01-plan-mode-and-test-first.md` | 2.7.1–2.7.4 | `prac-01` | D-64 | written |
| `practices/02-prompting-and-context.md` | 2.7.5–2.7.8 | `prac-02` | — | written |
| `practices/03-review-skills-and-interface.md` | 2.7.9–2.7.12 | `prac-03` | — | written |
| `deterministic-vs-agentic/01-the-central-judgment.md` | 2.8.1–2.8.5 | `det-01` | D-65 | written |
| `deterministic-vs-agentic/02-cases-idempotence.md` | 2.8.6–2.8.9 | `det-02` | — | written |
| `governance/01-the-threat-model.md` | 2.9.1–2.9.4 | `gov-01` | D-66, D-67a–d | written |
| `governance/02-the-lock-family.md` | 2.9.5–2.9.8 | `gov-02` | D-68ᵗ | written |
| `governance/03-secrets-attribution-review.md` | 2.9.9–2.9.11 | `gov-03` | — | written |
| `91-interview-intermediate.md` | wrap-up, §2.1–§2.9 | — | re-embeds | written |

### PART 3 — planned

| File | Leaves | Leaf file | Diagrams | Status |
|---|---|---|---|---|
| `request-assembly/03-internals-a-assembly-order.md` | 3.1.1–3.1.4 | `req-01` | D-69, D-70 | written |
| `request-assembly/03-internals-b-listing-and-transcripts.md` | 3.1.5–3.1.8 | `req-02` | D-71, D-72 | written |
| `compaction/03-internals-a-the-budget.md` | 3.2.1–3.2.4 | `comp-01` | D-73a/b/c | written |
| `compaction/03-internals-b-hooks-and-control.md` | 3.2.5–3.2.7 | `comp-02` | — | written |
| `permission-evaluation/03-internals-a-the-pipeline.md` | 3.3.1–3.3.4 | `pe-01` | D-74 | written |
| `permission-evaluation/03-internals-b-traced-commands.md` | 3.3.5–3.3.8 | `pe-02` | D-75a/b/c | written |
| `cost-model/03-internals-a-the-four-quantities.md` | 3.4.1–3.4.4 | `cost-01` | D-76ᵗ, D-77 | written |
| `cost-model/03-internals-b-ceilings-and-reading-it-back.md` | 3.4.5–3.4.9 | `cost-02` | D-78ᵗ | written |
| `effort-and-routing/03-internals-routing.md` | 3.5.1–3.5.6 | `effort-routing` | D-79 | written |
| `headless/03-internals-a-the-surface.md` | 3.6.1–3.6.5 | `hl-01` | D-80 | written |
| `headless/03-internals-b-formats-and-execution.md` | 3.6.6–3.6.9 | `hl-02` | — | written |
| `headless/03-internals-c-the-failure-taxonomy.md` | 3.6.10–3.6.14 | `hl-03` | D-81 | written |
| `headless/03-internals-d-resolution-order.md` | 3.6.15–3.6.18 | `hl-04` | D-82 | written |
| `setting-sources-incident/03-internals-a-the-failure.md` | 3.7.1–3.7.5 | `ssi-01` | D-83a–d | written |
| `setting-sources-incident/03-internals-b-the-fix-and-the-law.md` | 3.7.6–3.7.9 | `ssi-02` | — | written |
| `sdk-and-api/03-internals-a-three-levels.md` | 3.8.1–3.8.4 | `sdk-01` | D-84 | written |
| `sdk-and-api/03-internals-b-java-and-the-dependency-contract.md` | 3.8.5–3.8.8 | `sdk-02` | D-85 | written |
| `orchestration/03-internals-a-shapes-and-fan-out.md` | 3.9.1–3.9.4 | `orch-01` | D-86, D-87a/b/c, D-88a–e | written |
| `orchestration/03-internals-b-executor-vs-conductor.md` | 3.9.5–3.9.8 | `orch-02` | D-89 | written |
| `orchestration/03-internals-c-calibration-and-evals.md` | 3.9.9–3.9.12 | `orch-03` | D-90 | written |
| `verification/03-internals-a-evidence-and-the-nul-byte.md` | 3.10.1–3.10.4 | `ver-01` | D-91ᵗ, D-92a–d | written |
| `verification/03-internals-b-the-sibling-laws.md` | 3.10.5–3.10.8 | `ver-02` | — | written |
| `verification/03-internals-c-automation-and-review-capacity.md` | 3.10.9–3.10.11 | `ver-03` | D-93 | written |
| `92-interview-internals.md` | wrap-up §3.1–§3.10 **+ the topic-wide `## Atomic concept checklist` over all six parts** | — | re-embeds | written |

### PART 4 — planned. Every leaf is `[BUILD]`: artefact, then prove step, then cost note.

| File | Leaves | Leaf file | Diagrams | Status |
|---|---|---|---|---|
| `build-it/01-a-claude-folder-a.md` | 4.1.1–4.1.3 | `b4-01` | D-94 | written |
| `build-it/01-a-claude-folder-b.md` | 4.1.4–4.1.5 | `b4-02` | — | written |
| `build-it/02-three-hooks-a.md` | 4.2.1–4.2.3 | `b4-03` | D-95 | written |
| `build-it/02-three-hooks-b.md` | 4.2.4–4.2.6 | `b4-04` | — | written |
| `build-it/03-a-skill-and-a-command-a.md` | 4.3.1–4.3.3 | `b4-05` | — | written |
| `build-it/03-a-skill-and-a-command-b.md` | 4.3.4–4.3.6 | `b4-06` | — | written |
| `build-it/04-two-subagents-a.md` | 4.4.1–4.4.3 | `b4-07` | — | written |
| `build-it/04-two-subagents-b.md` | 4.4.4–4.4.5 | `b4-08` | — | written |
| `build-it/05-orchestrator-a-the-runner.md` | 4.5.1–4.5.2 | `b4-09` | D-96 | written |
| `build-it/05-orchestrator-b-ceilings-and-resolution.md` | 4.5.3–4.5.4 | `b4-10` | — | written |
| `build-it/06-orchestrator-c-bulkhead-and-retry.md` | 4.5.5–4.5.6 | `b4-11` | D-97a/b/c | written |
| `build-it/06-orchestrator-d-pipeline-and-cost.md` | 4.5.7–4.5.8 | `b4-12` | — | written |
| `build-it/07-a-plugin-a.md` | 4.6.1–4.6.3 | `b4-13` | D-98 | written |
| `build-it/07-a-plugin-b.md` | 4.6.4–4.6.6 | `b4-14` | — | written |
| `build-it/08-verification-harness-a.md` | 4.7.1–4.7.2 | `b4-15` | D-99 | written |
| `build-it/08-verification-harness-b.md` | 4.7.3–4.7.4 | `b4-16` | — | written |
| `93-interview-build-it.md` | wrap-up, §4.1–§4.7 | — | re-embeds | written |

**§4.5 is cumulative:** the `ClaudeRunner` at 4.5.5 must be the class from 4.5.1 with additions, not
a fresh unrelated class. The four `build-it/05`–`06` rows are therefore dispatched **in order**, each
handed the code its predecessor wrote.

### PART 5 — planned

| File | Leaves | Leaf file | Status |
|---|---|---|---|
| `94-interview-questions-a.md` | 5.1.1–5.1.4 | `p5-01` | written |
| `94-interview-questions-b.md` | 5.1.5–5.1.8 | `p5-02` | written |
| `94-interview-questions-c.md` | 5.1.9–5.1.12 | `p5-03` | written |
| `94-interview-questions-d.md` | 5.1.13–5.1.16 | `p5-04` | written |
| `95-trap-index.md` | 5.2.1–5.2.4 | `p5-05` | written |
| `96-drills-and-review-schedule.md` | 5.3.1–5.3.8 | `p5-06` | written |

§5.3.1 in `96-drills-and-review-schedule.md` is **one line pointing at** the
`## Atomic concept checklist` at the end of `92-interview-internals.md`. A second copy is a defect.

### Interview-file Q&A counts

Computed from the subject-folder count at planning time, per the prompt's rule of ten base plus two
per subject folder beyond the fifth, so no writer has to guess:

| File | Subject folders in its part | Q&As required | Puzzles |
|---|---|---|---|
| `90-interview-basics.md` | 6 — `ground-zero`, `claude-folder`, `settings`, `memory`, `permissions`, `skills` | **12** | 5 |
| `91-interview-intermediate.md` | 9 — `subagents`, `personas`, `hooks`, `mcp-and-lsp`, `plugins`, `context-economy`, `practices`, `deterministic-vs-agentic`, `governance` | **18** | 5 |
| `92-interview-internals.md` | 11 — `request-assembly`, `compaction`, `permission-evaluation`, `cost-model`, `effort-and-routing`, `headless`, `setting-sources-incident`, `sdk-and-api`, `orchestration`, `verification` (+ the wrap-up itself) | **22** | 5 |
| `93-interview-build-it.md` | 1 — `build-it` | **10** | 5 |
| `94-interview-questions-d.md` | closes PART 5 | **10** | 5 |

The re-splits above changed **file** counts, not **subject-folder** counts, so these numbers are
unchanged from the prompt's OUTPUT CONTRACT.

---
# DIAGRAM MANIFEST

**99 diagrams (D-01 … D-99).** Every one must exist as a standalone SVG file in
`src/notes/detailed/21-ai-for-coding/diagrams/`, named `D-NN-short-slug.svg`, embedded at the point
of explanation with a Markdown image reference and a caption carrying the stable id, e.g.
`**D-28** — Permission evaluation: deny, then ask, then allow`. Where the `Type` column says
`table`, a Markdown table is the correct rendering and no SVG file is required — the `D-NN` id still
appears at that point in the prose so the id is accounted for.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, author each frame as its own file (`D-12a-…`,
  `D-12b-…`) or as that many clearly separated, individually labelled panels inside the one SVG.
  Report every id produced.
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
| D-02 | Tokens per character for three real strings | 0.1.3, 0.1.4 | table | Three rows: an English sentence, a Java method (`public Optional<Envelope> parse(String stdout)` with a body), a minified JSON settings blob. Columns: the literal string, character count, token count, characters per token. The ~3–4 chars/token figure for prose and the visibly worse ratio for code and JSON both stated as numbers |
| D-03 | One distribution, two sampled answers | 0.1.2, 0.1.6, 0.1.8 | step-sequence, 3 frames | Frame 1: the text so far, ending mid-sentence. Frame 2: a bar chart of candidate next tokens with probabilities summing to 1, the top three labelled. Frame 3: two complete outputs from the same input, side by side, differing — both fluent. An annotation panel: "fluency is not a correctness signal" |
| D-04 | Model tiers as an engineering decision | 0.1.10, 0.1.11, 3.5.3 | table | Rows: `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`, `claude-fable-5`. Columns: alias, what to use it for (architecture judgment / implementation / exploration and search / per its documented role), relative cost ratio stated as a number, and what a `[1m]` suffix means. A footnote: verified against the docs on the write date, with the date |
| D-05 | Agent = model + loop + tools | 0.1.12, 0.3.1 | hierarchy | Root box "agent"; three children "model (stateless function)", "loop (the harness)", "tools (name + description + JSON schema)". Beside it a contrast panel: "chatbot = model + loop, no tools" and "'AI' = not a definition". Arrows labelled so the reader sees the loop owns the tools, not the model |
| D-06 | A request is an ordered list of messages | 0.2.3 | memory-layout | The literal JSON of a two-turn conversation: a `system` message, a `user` message, an `assistant` message, a second `user` message. Each drawn as a labelled slot in an ordered array with its index. Role names spelled exactly `system`, `user`, `assistant` |
| D-07 | The window is the argument list, not a memory | 0.2.4, 0.2.5 | before-after | Left, the wrong model: one box "the model", an arrow "writes to memory", a persistent store. Marked as false. Right, the real model: a stateless `@RestController`-shaped handler receiving the entire conversation as its request body, and a client that appends to that body each turn. A panel "where the analogy breaks": no session, no cookie, no server-side store |
| D-08 | Cost scales with conversation length | 0.2.6, 3.4.3 | cost-curve | X axis turns 1 to 100, Y axis cumulative input tokens. A curve rising super-linearly because the whole transcript is re-sent each turn. Two points annotated with the actual arithmetic: the 10-turn total and the 100-turn total, each shown as a sum, not just a result. A flat reference line labelled "what people assume: cost of the last message only" |
| D-09 | Prompt caching: the reusable prefix | 0.2.8, 0.2.9, 3.4.4 | before-after | One request drawn as a strip: stable prefix (system prompt, tool schemas, memory files) then the changing tail. Left: appended tail, prefix served from cache at a fraction of the price — the fraction stated. Right: the prefix edited, so nothing is cached and everything is re-billed. A timeline strip beneath showing the 5-minute default TTL, `promptCacheTtl` and `subagentPromptCacheTtl` labelled, and a 6-minute pause crossing the expiry |
| D-10 | The 200K budget, itemised | 0.2.10, 0.2.11, 2.6.2 | memory-layout | A single 200K bar divided and labelled with token counts: system prompt, tool schemas, memory files, skill listing, environment/git snapshot, then conversation, then free space. The autocompaction threshold drawn as a vertical line with its percentage and the resulting usable figure written as arithmetic (`200,000 × threshold = usable`) |
| D-11 | One turn of the agent loop | 0.3.1, 0.3.2, 0.3.3, 0.3.4 | step-sequence, 4 frames | Frame 1: the harness assembles the request. Frame 2: the model emits a `tool_use` block naming the tool and its arguments — labelled "the model does NOT run it". Frame 3: the harness consults the permission rules and decides, then executes. Frame 4: a `tool_result` message appended to the transcript, transcript visibly longer. An annotation panel: "this is the entire basis of the permission system" |
| D-12 | A real loop end to end, with token counts | 0.3.7 | step-sequence, 5 frames | The task "rename this method". Frame 1 Grep, frame 2 Read, frame 3 Edit, frame 4 done. Each frame shows the transcript as a growing stack of messages **and the cumulative token count after that step, as a number**. Frame 5: a total, with the arithmetic |
| D-13 | The built-in tools by category | 0.3.8, 0.3.9 | hierarchy | Six category boxes with their tools named exactly: file (Read, Write, Edit, Glob, Grep), shell (Bash), web (WebFetch, WebSearch), delegation (Agent, SendMessage), meta (Skill, ToolSearch), task/UI (TodoWrite, AskUserQuestion). A side panel on deferred tools: which schemas are loaded up front, which arrive via `ToolSearch`, and the token saving stated |
| D-14 | One loop, many front ends | 0.3.11 | hierarchy | One shared bottom layer "the harness: the loop, the tools, the settings files". Above it, four front ends: CLI, VS Code / JetBrains extension, desktop app, web app. Arrows from each to the same layer. An annotation: same `~/.claude/settings.json`, same `.claude/`, same permission rules |
| D-15 | "Why is it doing that?" — the diagnostic order | 0.4.3, 1.1.9 | decision-tree | Root: "a behaviour surprised you". Branches, in the order to try them: `/context` (what loaded), `/doctor` (resolved settings and health), `/permissions` (which rule and which file), `/hooks` (which hook and which source), `/memory` (which instruction files), `/config`, `claude --debug`. Each leaf names what that command can and cannot tell you. A terminal node: `--safe-mode` / `--bare` to answer "is it my config or the tool?" |
| D-16 | A real `/context` read row by row | 0.4.4, 2.6.1, 3.1.1 | table | Every row of a real `/context` output: system prompt, system tools, MCP tools, memory files, custom agents, skill listing, messages, free space. Columns: tokens, percentage of window, which file or subsystem supplies it, and the lever that reduces it. Totals reconciling to the window size |
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
| D-33 | The six permission modes | 1.4.25, 1.4.26, 1.4.27, 1.4.28 | table | All six rows: `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. Columns: exactly what is auto-approved, what still prompts, what it never allows, and the setting that disables it. `acceptEdits` row naming `mkdir`, `touch`, `mv`, `cp` and the working-directory / `additionalDirectories` scope. `bypassPermissions` row naming the protected paths it still refuses (`.git`, `.claude`) and the cross-session messaging safeguards |
| D-34 | Workspace trust, and how it is keyed | 1.4.32, 1.4.33, 1.4.34, 1.4.35 | decision-tree | Root: "a project's committed settings want to grant something". Branches: `allow` and `additionalDirectories` → gated on the trust dialog; `deny`/`ask` → not gated, because they only restrict. A keying panel: git repo root inside a repo (nested repos excluded), start directory outside one, session-only in `$HOME`. A highlighted terminal node: **a `-p` or SDK session never shows the dialog and counts as accepted.** A second panel: an untracked local file applies immediately; a tracked one, or a symlinked `.claude`, waits |
| D-35 | Sandbox is the layer below permissions | 1.4.39, 3.3.7, 2.9.4 | hierarchy | Three stacked layers: the model's intent (shaped by prompt and `CLAUDE.md`), the permission rules (enforced by the harness), the OS sandbox (`sandbox.enabled`, filesystem allow/deny, network allowlist, credential masking). An arrow showing a Python subprocess opening a file directly, passing straight through the middle layer and being stopped only by the bottom one |
| D-36 | Progressive disclosure: listing versus body | 1.5.5, 1.5.6, 3.1.5 | before-after | Left: fifty skills as fifty listing entries, each just `description` + `when_to_use`, truncated at 1,536 characters, with the total token cost computed. Right: one skill fired, its full body now in context, with that body's token cost. Beneath, the counterfactual: the same fifty procedures written into `CLAUDE.md`, always paid, with its total. `skillListingBudgetFraction` and `skillListingMaxDescChars` labelled |
| D-37 | Skill and command locations, and the conflict order | 1.5.1, 1.5.3, 1.5.4 | hierarchy | A layered stack: enterprise, personal (`~/.claude/skills/`), project (`.claude/skills/`), plugin (namespaced `plugin:skill`). Arrows showing a project skill overriding a bundled skill of the same name but not its aliases, a skill beating a same-named `commands/` file, and plugin skills coexisting rather than overriding. An annotation panel: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both produce `/deploy` and behave the same way — custom commands **are** skills. A nested-subtree box for the monorepo mechanism |
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
| D-46 | Where a subagent's 2× comes from | 2.1.19, 2.6.10, 3.4.5 | cost-curve | Two stacked bars. Inline: the existing prefix reused, cache reads, one set of output tokens. Subagent: a fresh system prompt, fresh tool schemas, the `CLAUDE.md` hierarchy re-supplied, the task string, then the work, then the returned message re-entering the parent transcript. Each segment carries a token number, and the ratio is written as arithmetic. A second panel making the opposite case: 150K burned inside, 200 words returned — the parent's transcript grows by the 200 words only |
| D-47 | One writer per output path, ever | 2.1.24, 3.9.2 | before-after | Left, the failure: two parallel agents given folder-scoped lanes plus one flat shared directory, both writing the same slug, the second overwriting the first silently with no orphan left to notice. Right, the fix: a disjoint filesystem partition, one writer per path, a join step that only reads. An annotation: "partition the filesystem, not the topic" |
| D-48 | Three ways to set a persona | 2.2.1, 2.2.2, 2.2.3, 2.2.4 | table | Rows: `--agent <name>`, `--append-system-prompt <text>`, `--system-prompt` / `--system-prompt-file`, `--append-subagent-system-prompt`. Columns: what happens to the default system prompt (loaded from the registered agent / appended to / replaced / appended for every subagent), whether the model and tool allowlist come with it, what you lose, and the symptom when you pick the wrong one (an agent that behaves almost right and ignores tool restrictions it never had) |
| D-49 | The hook lifecycle across one session | 2.3.6 | timeline | One session on a time axis with events firing in order: `SessionStart` / `Setup`, `InstructionsLoaded`, `UserPromptSubmit` / `UserPromptExpansion`, `PreToolUse`, `PostToolUse` / `PostToolUseFailure` / `PostToolBatch`, `PermissionRequest` / `PermissionDenied`, `SubagentStart` / `SubagentStop`, `PreCompact` / `PostCompact`, `Stop` / `StopFailure`, `SessionEnd`. Each mark labelled with whether it can block |
| D-50 | The 32 events, grouped | 2.3.6 | hierarchy | Twelve group boxes with every event named exactly: session lifecycle (`SessionStart`, `Setup`, `SessionEnd`), prompt (`UserPromptSubmit`, `UserPromptExpansion`), tools (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`), permissions (`PermissionRequest`, `PermissionDenied`), turn (`Stop`, `StopFailure`), subagents (`SubagentStart`, `SubagentStop`), tasks (`TaskCreated`, `TaskCompleted`, `TeammateIdle`), context (`PreCompact`, `PostCompact`, `InstructionsLoaded`), environment (`ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`), worktrees (`WorktreeCreate`, `WorktreeRemove`), MCP (`Elicitation`, `ElicitationResult`), UI (`Notification`, `MessageDisplay`). The count 32 and the version v2.1.2xx stated on the canvas |
| D-51 | Which events can block, and with which field | 2.3.7, 2.3.15 | table | One row per blocking-capable event. Columns: can it block, which decision field it honours (`permissionDecision` for `PreToolUse`, `continue` for `Stop`, none for `PostToolUse` because it already ran), what a non-zero exit does, and what the model sees. Non-blocking events listed in a second block so the reader cannot mistake one for the other |
| D-52 | Hook exit codes and the JSON contract | 2.3.12, 2.3.13, 2.3.14 | flowchart | A hook returning, with three exit paths: `0` (success; stdout to the debug log, except `UserPromptSubmit` / `UserPromptExpansion` / `SessionStart` where it is shown to Claude), `2` (blocking error — the only code that blocks without JSON), anything else (non-blocking). A parallel path for JSON output listing every field of `hookSpecificOutput` (`hookEventName`, `permissionDecision`, `permissionDecisionReason`, `decision`, `additionalContext`, `continue`, `updatedInput`, `retry`, `systemMessage`) plus top-level `terminalSequence`. A highlighted merge node: exit 2 overrides a JSON `permissionDecision: "allow"` |
| D-53 | A hook cannot unblock a deny | 2.3.16, 3.3.2, 3.3.1 | flowchart | One tool call flowing through rule collection, then deny → ask → allow, then the `PreToolUse` hook, then the mode default, then the prompt. The hook drawn strictly after the rule evaluation. Two traces: a hook returning `allow` on a call that matched `deny` → still blocked; a hook returning `allow` on a call that matched `ask` → still prompts |
| D-54 | The six places a hook can be configured | 2.3.18, 2.3.19 | hierarchy | Six source boxes: user settings, project settings, local settings, managed policy, plugin `hooks/hooks.json`, skill frontmatter (rest of session), subagent frontmatter (while it runs) — grouped so the settings trio reads as one family. Each annotated with its lifetime. A kill-switch panel: `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and "individual hooks cannot be disabled, only deleted" |
| D-55 | The `SessionStart` reindex pile-up | 2.3.25 | step-sequence, 4 frames | Frame 1: one session starts, the hook decides a delta-reindex is due, two handbook clones pulled, embedder processes spawned. Frame 2: a second and third concurrent session each independently reach the same decision — no cross-session coordination, drawn as an absent lock. Frame 3: hundreds of concurrent embedder processes, **100+ GB** of abandoned partial indexes, the machine unusable. Frame 4: the recovery attempt — starting a session to fix it is itself the trigger for the next pile-up. An annotation panel with the law: anything expensive or stateful in a `SessionStart` hook needs a lock or must not be there |
| D-56 | An MCP server's schemas are a per-turn tax | 2.4.7, 3.1.4 | cost-curve | X axis turns, Y axis tokens. A flat baseline for the default tool set with its token figure. A raised line after one chatty MCP server connects, the delta labelled with the server's schema cost. The cumulative extra over a 40-turn session written as arithmetic. A note that `/context` is how you measure it, and that the tool-name form is `mcp__<server>__<tool>` |
| D-57 | LSP symbol lookup versus read-and-grep | 2.4.11, 2.4.12, 2.6.3 | before-after | Left: three whole files read plus a repo-wide grep to answer "where is this method used", with the token total. Right: one LSP symbol lookup answering the same question, with its token total. The ratio stated. The three plugins named (`pyright-lsp`, `typescript-lsp`, `jdtls-lsp`) and the framing quoted: the argument is token cost, not correctness |
| D-58 | The plugin directory layout | 2.5.3, 2.5.4 | hierarchy | The plugin root with `.claude-plugin/plugin.json` inside it and **only** that file inside `.claude-plugin/`. Siblings at the plugin root: `skills/`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`, `settings.json`. A crossed-out variant showing `skills/` misplaced inside `.claude-plugin/` labelled "silently ships nothing". An annotation: the plugin root is the plugin's own directory, never `~/.claude/` |
| D-59 | The plugin and marketplace dependency graph | 2.5.9, 2.5.10, 2.5.11, 2.5.17 | hierarchy | Two marketplace boxes, each with its `.claude-plugin/marketplace.json`. The first declares `allowCrossMarketplaceDependenciesOn: ["ig-superclaude"]` and contains a plugin at `version 0.10.2` whose `dependencies` names `{ name: "ig-superclaude", marketplace: "ig-superclaude" }`. A dependency edge crossing to the second marketplace, drawn in the weak style until the user has explicitly trusted it, with the refusal to auto-add labelled. A failure panel: the unresolved state, the cryptic `/reload-plugins` error, and `claude plugin list --json` exposing the per-plugin `errors` array |
| D-60 | `${CLAUDE_PLUGIN_ROOT}` is not the repo | 2.5.18, 2.5.19, 2.3.17 | before-after | Left: a hook living at `<repo>/.claude/hooks/`, resolving the repo root as `dirname "$0"/../..` — correct. Right: the same hook inside an installed plugin, where `${CLAUDE_PLUGIN_ROOT}` is the install/cache directory, and the same expression resolves into the cache — wrong, with the broken path drawn. The fix panel: resolve via `git rev-parse --show-toplevel`, and refuse with a clear message rather than inventing a third fallback |
| D-61 | `strictPluginOnlyCustomization` closes the side doors | 2.5.14, 2.5.15, 2.9.7 | hierarchy | Four extension channels — skills, agents, hooks, MCP — each with three possible sources: user, project, plugin. With the lock off, all twelve edges live. With `strictPluginOnlyCustomization` on (and its `.agents`, `.hooks`, `.mcp`, `.skills` sub-keys), the user and project edges drawn as blocked and only the plugin edges live. A panel with the neighbouring keys: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`, `strictKnownMarketplaces`, `disableSideloadFlags`, `pluginTrustMessage` |
| D-62 | The four biggest avoidable context costs, ranked | 2.6.3, 2.6.4 | cost-curve | Four bars in rank order with token figures: unbounded command output, whole-file reads where a symbol lookup would do, a bloated always-on `CLAUDE.md` (cost per turn × turns), chatty MCP servers. Each bar annotated with its specific fix: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over `cat`, `git diff --stat` before `git diff`, a path-scoped rule instead of a global instruction, disabling the server |
| D-63 | Isolation arithmetic | 2.6.10, 2.1.19 | before-after | Left, inline: a 150K-token exploration living in the main transcript, then every subsequent turn re-sending it — the running total over the next ten turns written as a sum. Right, isolated: the same 150K burned inside a subagent, 200 words returned, the parent transcript growing by the 200 words only, and the subagent's 2× cost stated honestly. The net comparison as a single number |
| D-64 | Plan mode moves the correction earlier | 2.7.1, 2.7.2 | timeline | Two lanes on one time axis. Without a plan: prompt → a large diff → review → an expensive correction after the diff exists, with rework shaded. With a plan: read-only exploration → a reviewable plan → the correction applied to the plan → execute → a smaller review. `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode` and `plansDirectory` labelled on the second lane |
| D-65 | Script or prompt | 2.8.1, 2.8.4, 2.8.5 | decision-tree | Root: "do the inputs determine one correct answer?". Yes → shell script, annotated "testable, no variance, no token cost". No → prompt, annotated "judgment, synthesis". Further branches: must-happen → hook; verbose-in/small-out → subagent; needs human authority → confirmation gate with the tool denied. An annotation panel quoting the source of the rule: resolving paths, merging JSON and creating symlinks all have a single correct answer given the inputs. A second panel: "the model could do it" is not an argument — cost, variance, and a script is testable where a prompt is not |
| D-66 | The threat model: one agent's blast radius | 2.9.1, 2.9.3 | hierarchy | The agent at the centre with three properties stated: it runs with your credentials, it reads what you can read, it follows text it finds. Reachable surfaces drawn outward: the filesystem, the shell, the network, the cloud credentials, the issue tracker via MCP, the git remote. Beside them the controls that hold, ranked by strength: deny rules, `PreToolUse` blocking hooks, the sandbox, least-privilege tool sets, human confirmation on outward-facing actions. Prompting drawn explicitly outside the control list |
| D-67 | Prompt injection: the path from data to tool call | 2.9.2 | step-sequence, 4 frames | Frame 1: an instruction embedded in data the agent will read — an issue comment, a fetched web page, a file, a `tool_result`. Frame 2: that text arriving in the transcript indistinguishable in kind from the user's own message. Frame 3: the model emitting a `tool_use` block the user never asked for. Frame 4: the harness's rule evaluation as the only thing between that block and the action. An annotation: "tell it to ignore instructions in data" is not a control, because the instruction and the control live in the same channel |
| D-68 | The `allowManaged*Only` lock family | 2.9.6, 2.9.7, 2.9.8 | table | Rows: `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`, `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`. Columns: what it locks, which sources stop being honoured, and what a developer sees when they try. A delivery panel: `managed-settings.json`, MDM, server-managed settings from the console, `managedSourcesBehavior`, `policyHelper` (`path`, `refreshIntervalMs`, `timeoutMs`), `forceRemoteSettingsRefresh` |

## PART 3 diagrams (D-69 … D-93)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-69 | Request assembly order, and the cached prefix | 3.1.1, 3.1.3 | memory-layout | One request as an ordered vertical strip: system prompt (built-in + appended), tool schemas, memory files as a user message, environment/git snapshot, skill listing, then the conversation. A bracket down the stable portion labelled "cached prefix — reused at cache-read price". `--exclude-dynamic-system-prompt-sections` labelled against the per-machine sections it moves out of the prefix. Each segment carries a token figure |
| D-70 | `CLAUDE.md` is a user message, not the system prompt | 3.1.2 | before-after | Left, the wrong model: `CLAUDE.md` drawn inside the system prompt block — marked false. Right, the real assembly: the system prompt, then a separate `user` message carrying the memory files. Two consequences annotated: this is why it is guidance and not policy, and this is why `--append-system-prompt` behaves differently |
| D-71 | The cost of fifty skills in the listing | 3.1.5, 1.5.6 | cost-curve | X axis number of skills 0 to 50, Y axis listing tokens. The per-skill cost derived from `description` + `when_to_use` truncated at 1,536 characters, the arithmetic shown, and the total at 50 marked. A horizontal cap line for the budget fraction of the window, with `skillListingBudgetFraction` and `skillListingMaxDescChars` labelled and the behaviour at the cap stated |
| D-72 | One JSONL transcript turn, annotated | 3.1.7, 3.1.8, 0.4.8 | memory-layout | A real transcript path `~/.claude/projects/<project>/<session>/` and one JSONL record expanded: its role, its content blocks including a `tool_use` and a `tool_result`, and its usage fields. Arrows to where a per-turn token count is read from. A note that `telemetry/transcript.py` reads exactly these files to mine friction signals, and that `cleanupPeriodDays` governs how long they live |
| D-73 | The compaction re-attachment budget | 3.2.3, 3.2.2 | step-sequence, 3 frames | Frame 1: a session with six skills invoked at different times, each with a token size. Frame 2: the threshold reached — the percentage and what it is a percentage of written as arithmetic against the window size. Frame 3: the summary, then re-attachment newest-first: the most recent invocation of each skill, first 5,000 tokens each, stopping at 25,000 combined, with the two oldest skills visibly evicted. Both numbers labelled on the canvas |
| D-74 | The full permission-evaluation pipeline | 3.3.1, 3.3.2, 3.3.4 | flowchart | One tool call from entry to outcome. Stage 1: rule collection across managed → CLI → local → project → user. Stage 2: deny → ask → allow, first match wins. Stage 3: the `PreToolUse` hook. Stage 4: the mode's default. Stage 5: the interactive prompt. A branch off stage 2 for the read-only command fast path, with the two cases that leave it (write-capable flags with unquoted globs, redirects). A terminal note: a deny at any level cannot be overridden by any other level, including `--allowedTools` and managed settings |
| D-75 | Three Bash commands traced through matching | 3.3.3, 1.4.11 | step-sequence, 3 frames | Three real commands, one per frame, each traced through the same four stages with the intermediate string printed at each: separator splitting, wrapper stripping, env-assignment stripping, per-subcommand matching against a stated rule set. Frame 1 a command that runs, frame 2 one that prompts, frame 3 one that is blocked — each with the specific rule that decided it named |
| D-76 | The four billed quantities | 3.4.1, 3.4.2 | table | Rows: input tokens, output tokens, cache writes, cache reads. Columns: what triggers it, the relative price, and where it appears in the `-p --output-format json` envelope. A second block with per-model pricing and the ratio between tiers as of the write date, each figure carrying the date it was verified and the source page |
| D-77 | Where the money actually goes in one session | 3.4.3, 3.4.4, 3.4.7 | cost-curve | A 40-turn session. Stacked areas per turn: cache reads on the re-sent prefix, fresh input tokens, output tokens, cache writes. The prefix re-send visibly dominating. Two annotations: a 5-minute idle gap crossing the cache TTL and the resulting re-priced turn, and the session total with the arithmetic. `/cost` and `modelPricing` named as the ways to read it back |
| D-78 | The three ceilings and their failure shapes | 3.4.6, 4.5.2 | table | Rows: `--max-turns`, `--max-budget-usd`, subprocess wall-clock timeout. Columns: what it bounds (agency / money / time), what the run looks like when it trips, whether work is preserved, what the envelope reports, and the distinct exception type a Java wrapper should throw. A note that all three are needed because each bounds a different thing |
| D-79 | Model routing as a cost decision | 3.5.1, 3.5.3, 3.5.5, 3.5.6 | decision-tree | Root: "what is this task". Branches: exploration and search → haiku; implementation → sonnet; architecture and gnarly debugging → opus. Each terminal carries the effort level to pair with it from `low\|medium\|high\|xhigh\|max` and the escalation path haiku → sonnet → opus. A panel: `fastMode` / `/fast` is faster output on the same Opus model, not a downgrade. A failure panel: routing everything to the cheapest model, with a concrete wrong result that cost more than the saving |
| D-80 | The `-p --output-format json` envelope | 3.6.1, 3.6.3, 3.6.2 | memory-layout | One real envelope drawn field by field with a value in each: the result text, `is_error`, `session_id`, the cost field, the token-count fields, the duration. Arrows out to what each is used for downstream: billing, audit, retry classification, continuation. A side panel comparing `text`, `json` and `stream-json` output formats and `text` versus `stream-json` input |
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
| D-91 | Evidence ranked by strength | 3.10.8, 3.10.2, 2.7.7 | table | Rows from strongest to weakest: a re-run of the published artefact in its published form, a passing test, a clean compile, a real transcript, a diff you read line by line, a regex over a file, a structural check, the agent's own claim of success. Columns: what it proves, what it cannot catch, and the specific defect class in this repository that only the top row found (code that no longer produced the transcript printed beneath it, invented values that compiled, a repro returning the opposite of its claim, run-specific numbers published as constants) |
| D-92 | The checker that switched itself off | 3.10.3, 3.10.4, 3.10.5, 3.10.6, 3.10.7 | step-sequence, 4 frames | Frame 1: one generated file containing a literal NUL byte. Frame 2: `file` classifying it as `data`. Frame 3: grep returning *nothing* — not a mismatch, nothing — so every text check silently skipped it. Frame 4: the gate reporting success over an unchecked file. The fix drawn as a first stage: assert text-ness before any grep-based gate. An annotation panel with the four sibling laws: certify from final state never from a pre-write computation; pin the harness beside the digest; never let a status row point at a missing path; a closed lane is not a verified lane |
| D-93 | Review capacity is the throughput ceiling | 3.10.11, 2.9.11 | cost-curve | X axis agent throughput in diffs per day, Y axis two curves: what the agents can produce (rising) and what the humans can genuinely review (flat, with the per-diff review minutes and the available engineer-hours written as arithmetic). The crossing point marked as the real ceiling. An annotation: adding agents past this point adds unreviewed diffs, not velocity |

## PART 4 diagrams (D-94 … D-99)

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-94 | The `.claude` folder built in §4.1 | 4.1.1, 4.1.2, 4.1.3, 4.1.4 | hierarchy | The finished tree for the Spring Boot service: `CLAUDE.md` under 100 lines, `.claude/rules/<name>.md` with its `paths:` glob, `.claude/skills/<name>/SKILL.md`, `.claude/settings.json`, `.claude/settings.local.json`. Each node annotated with what moved into it and why. A `/context` delta panel with the before and after token figures from §4.1.2, and the one key `settings.local.json` overrides marked as the winner |
| D-95 | Four hooks on the lifecycle they fire on | 4.2.1, 4.2.2, 4.2.3, 4.2.4 | timeline | One session axis with four marks, each naming the real script and what it does: `SessionStart` → `branch-context.sh` injecting branch, dirty-file count and failing-test count as tagged advisory lines; `PreToolUse` on `Bash` → `block-destructive-bash.sh` returning a JSON `permissionDecision: "deny"` with a reason; `PostToolUse` on `Edit\|Write` → `format-on-edit.sh` reading `tool_input.file_path` from stdin via `jq`; `Stop` → `require-green-build.sh` using `continue`. Each mark labelled with its exit-code posture (`set +e` / `exit 0` for advisory, non-zero for blocking) and the `Stop` mark carrying the four-minute-build warning |
| D-96 | `ClaudeRunner` and the process boundary | 4.5.1, 4.5.2, 4.5.3, 4.5.4, 4.5.5 | hierarchy | The Java side: `ClaudeRunner`, the `ClaudeEnvelope` record with its fields, the distinct exception types for the three ceilings, the `Semaphore` bulkhead, the bounded retry holding the last parsed error envelope. The process boundary drawn as a hard line. The other side: the assembled `claude -p` command line with every flag visible — `--output-format json`, `--max-turns`, `--max-budget-usd`, `--settings <absolute path>`, `--agent`, `--permission-mode`. Arrows for stdout, stderr and the exit code coming back, and the 500-character unparseable-input snippet captured on the parse-failure path |
| D-97 | The two-stage pipeline over `ClaudeRunner` | 4.5.6, 4.5.7 | step-sequence, 3 frames | Frame 1: stage 1 running, reading its input path, writing its output file — the two paths visibly different. Frame 2: stage 2 running, reading stage 1's output, writing its own — again visibly different, so stage 2 is independently re-runnable. Frame 3: stage 2 re-run alone, producing the same result, with stage 1 untouched. A cost panel beneath: per-stage tokens and dollars read out of each envelope, and the run total |
| D-98 | The plugin from §4.6 and its marketplace | 4.6.1, 4.6.3, 4.6.4, 4.6.5 | hierarchy | The packaged plugin: `.claude-plugin/plugin.json` with `name`, `version` and `dependencies` filled in, plus `skills/`, `agents/`, `hooks/hooks.json` moved from `.claude/`. The local marketplace with its `.claude-plugin/marketplace.json` and `plugins[]` entry. Edges for the install path: `/plugin marketplace add`, `/plugin install`, `/reload-plugins`, and `--plugin-dir` for the pre-publish test. A version-bump panel showing the installed copy updating only after `version` changes, and an unresolved-dependency panel showing the `claude plugin list --json` `errors` array |
| D-99 | `verify.sh` gate order — text-ness first | 4.7.1, 4.7.2, 4.7.3, 3.10.3 | flowchart | The script from entry to exit code. Gate 1: assert every target file is text, failing loudly if not — drawn first and labelled with why. Gate 2: the structural checks. Gate 3: re-run every fenced listing and compare against the printed output. Each gate branching to a loud named failure rather than a skip. Two terminals annotated with where they belong: the `Stop` hook for fast local gates, the CI job for slow ones |

---

# LEAF LEDGER (verbatim from the prompt)

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
and frontmatter field below was verified against `https://code.claude.com/docs/en/` on 2026-08-29.
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
1.4.26 `acceptEdits` in detail — file edits **plus** common filesystem commands (`mkdir`, `touch`,
       `mv`, `cp`) for paths in the working directory or `additionalDirectories`. What it does
       *not* cover is the point of the §3.7 incident. `[DOC]`
1.4.27 `auto` mode: a background classifier reviews actions instead of you; `autoMode` rules,
       `autoMode.classifyAllShell`, `disableAutoMode`. `[DOC]` `[VERSION]`
1.4.28 `bypassPermissions`: what it still refuses (protected paths such as `.git` and `.claude`,
       cross-session messaging safeguards), and that it is defensible only in a container or VM.
       `[DOC]` `[TRAP]`
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
1.4.34 `[TRAP]` **A `-p` or SDK session never shows the trust dialog and counts as accepted.**
       Automation therefore runs a repository's allow rules without a human ever reviewing them.
       `[TRAP]` `[DOC]`
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

*(41 leaves)*

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
1.5.6 The listing budget: combined `description` + `when_to_use` is truncated at **1,536
      characters**; `skillListingBudgetFraction` and `skillListingMaxDescChars` tune the listing.
      `[DOC]` `[NUM]`
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
1.5.19 `[CASE]` The harness's `playwright-cli` skill with its `references/` subfolder — a reference
       library that costs nothing until needed. `[CASE]`
1.5.20 `[CASE]` The harness's `bootstrap` skill: `name` / `description` / `when_to_use` /
       `allowed-tools: [Bash, Read, AskUserQuestion]`, and a body that is an **orchestrator, not a
       rewrite** — each step delegates to a tested `bootstrap-*.sh`. Quote the "why deterministic
       scripts and not model judgment" paragraph verbatim. `[CASE]`
1.5.21 `[CASE]` Prompt composition without duplication: `/implement-story` inlines
       `/run-conductor` with a ` ```! ` block running
       `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, then states only its binding
       overrides, forwarded flags and **rejected flags**. DRY applied to prompts. `[CASE]`
1.5.22 `[TRAP]` A description that names the **topic** rather than the **trigger** makes the skill
       invisible or always-on. Three bad descriptions rewritten. `[TRAP]`
1.5.23 Built-in and bundled: `/help`, `/compact`, `/clear`, `/context`, `/config`, `/doctor`,
       `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/rewind`, `/cd`,
       `/add-dir`, `/model`, `/effort`, plus bundled skills such as `/code-review`, `/security-review`,
       `/loop`, `/run`. `[DOC]` `[RESEARCH]`
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

**PART 1 total: 121 leaves**

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
2.3.14 The JSON output contract: `hookSpecificOutput.{hookEventName, permissionDecision,
       permissionDecisionReason, decision, additionalContext, continue, updatedInput, retry,
       systemMessage}` plus top-level `terminalSequence`. `[DOC]`
2.3.15 Which decision field each event honours — the table. `PreToolUse` takes
       `permissionDecision`; `Stop` takes `continue`; `PostToolUse` takes none because it already
       ran. `[DOC]`
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

*(28 leaves)*

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

**PART 2 total: 137 leaves**

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
4.2.4 `Stop`: refuse to end the turn while the build is red, using `continue`. Then explain why
      this is dangerous if the build takes four minutes. `[BUILD]` `[TRAP]`
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
| PART 1 — Basics | 121 |
| PART 2 — Intermediate | 137 |
| PART 3 — Under the hood | 96 |
| PART 4 — Build it | 40 |
| PART 5 — Interview & retention | 28 |
| **Total** | **468** |

Leaves carrying `[ZERO]`: **~30** (all of PART 0 plus the first leaf of most PART 1–3 sections).
`[DOC]`: **~150**. `[CASE]`: **~45**. `[BUILD]`: **~60** (all of PART 4, plus the diagnostic and
proof leaves in PARTs 1–3). `[TRAP]`: **~45**. `[INCIDENT]`: **11**. `[NUM]`: **~60**.
`[VERSION]`: **~20**. `[JAVA]`: **~15**. `[PROVE]`: **~45**.

**Every one of the 468 leaves must appear in the notes**, or be listed in a `## Deferred` block with
a leaf number and a one-line reason.

Two notes on tags that appear in the leaves above and are not in the legend:

- `[SOURCE-EQUIV]` at leaf 2.2.6 is this topic's stand-in for topic 02's `[SOURCE]`. Treat it as
  `[CASE]`: quote the real function from `harness/src/harness/engine/agent.py` and read the regex
  line by line.
- `[X-REF 21]` at leaf 0.3.12 points inside this same guide (§3.8), not at a sibling. Give the
  one-paragraph orientation and link forward to §3.8; do not point the reader at another topic.

