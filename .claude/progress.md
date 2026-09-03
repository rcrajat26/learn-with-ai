# Progress Tracker

Update this file after every day or week generation. This is the canonical
state file — future sessions read here to know where we are.

**This project runs two independent pipelines.** The day/week pipeline is tracked
below and is still at zero. The per-topic pipeline is tracked in its own section
at the end of this file and has one topic complete.

## Plan position

- **Current week:** Not started
- **Days complete:** 0
- **Phase:** Phase 1 (not started)
- **Next to generate:** Day 1 (`w1/day1-notes.md`), per `faang-staff-prep-v4-28week.md`.

## Generated artifacts

None yet.

### Weeks 1+ — NOT STARTED

Continue in plan order. Each week:

1. Generate days `5N-4` through `5N` using `daily-prompt.txt`.
2. Optionally generate `week<N>-notes.md` Staff overview using `weekly-prompt.txt`.

## Running totals

| Metric | Current | Target by phase end |
|---|---|---|
| Days generated | 0 / 140 | Phase 1: 40 |
| LeetCode problems covered | 0 / ~160 | Phase 1: ~50 |
| STAR stories drafted | 0 / 20 | Phase 2 end: 18 |
| Engineering blogs dissected (template provided) | 0 / 28 | Phase 3 end: ~22 |
| DDIA chapters | 0 / 11 | Phase 3 end: 9 + Ch 4 + Ch 11 |
| Distributed systems papers | 0 / 4 (min) | Phase 3 end: 4 |

## Conventions reminders (full detail in `conventions.md`)

- Output path: `w<N>/day<D>-notes.md` where N = week number, D = day number.
- Tier-tag every sub-block: `[BOTH]` `[SENIOR IC]` `[STAFF]`.
- Target length: 1500–2000 lines per day.
- Cross-reference with explicit day numbers, not vague "later."

## Open questions / decisions made

None yet.

## Last update

- **Date:** 2026-07-09
- **Last generated:** None — progress reset to 0.
- **Notes:** All generated notes (w1, w2, w9) and other-notes deleted. Fresh start. Core artifacts and `.claude` config (including `preference.md`) retained.

---

# Per-topic pipeline

Separate from the day/week plan above. Source of truth for scope is
`src/syllabus/<NN>-<slug>.md`; generation prompt is
`src/metadata/prompts/<NN>-<slug>-prompt.md`; output is
`src/notes/detailed/<topic-slug>/`.

## Topics complete: 2 of 22

### 04 modern-java — full pipeline run 2026-08-30 → 2026-08-31 (COMPLETE)

Ran end to end in one sitting: syllabus pass → prompt → notes.

| Artefact | State |
|---|---|
| `src/topics/04-modern-java.md` | pre-existing, 420 lines. **Not updated by this run.** Three claims in it are stale — see below. |
| `src/syllabus/04-modern-java.md` | written 2026-08-30, **2,419 lines, 984 leaves** across 5 parts (P1 410, P2 190, P3 210, P4 65, P5 109). Target Java 21 LTS with explicit deltas at 8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25. Tags: `[RESEARCH]` 202, `[VERSION-TRAP]` 22, `[BUILD]` 76. |
| `src/metadata/prompts/04-modern-java-prompt.md` | written 2026-08-30, **3,223 lines**. 984 leaves inlined verbatim; **182-diagram manifest** (D-001…D-182) with leaf refs, type and must-show contents; output contract naming 62 files. |
| `src/notes/detailed/04-modern-java/` | **70 files, 88,806 lines, 153 SVGs.** All 69 file-plan rows `written`. **No leaves deferred** — all 984 owned by exactly one row. |

Output folder is `04-modern-java/`, matching the `<NN>-<slug>` shape topic 21 used
rather than `CLAUDE.md`'s bare `<topic-slug>/`. Both deviate the same way; the
convention line in `CLAUDE.md` is the thing that is out of date.

**46 manifest ids have no SVG and that is correct** — each is a recorded
Markdown-table substitution (`no — Markdown table` in `00-index.md`), which the
diagram spec permits where a picture does not fit. Multi-frame series render as
`D-018a/b/c` etc. Zero broken diagram references tree-wide, verified by diffing
every `../diagrams/*.svg` embed against the folder.

**Research was done with `openjdk.org` returning HTTP 403**, so every JEP came
via search summaries plus a secondary source. Three figures were flagged
unverified in the prompt and all three were re-verified before printing:

1. `jdk.virtualThreadScheduler.maxPoolSize` — `Integer.max(parallelism, 256)`, a
   **floor**, not a flat 256 ceiling. On a >256-core box it equals the core count.
2. `AbstractTask.LEAF_TARGET` / `suggestTargetSize` — `LEAF_TARGET =
   commonPoolParallelism << 2`; `suggestTargetSize` does **floored** division,
   min 1, not rounded up. `getLeafTarget()` reads the *current* pool's width.
3. The LVTI style guide's G1–G7 / P1–P4 identifiers — confirmed and cited.

Residual uncertainty is marked inline with `**Unverified:**` rather than stated
as fact (the `jdk.VirtualThreadPinned` JFR field schema, `ScopedValue`'s exact 21
preview surface, the lambda-classname hex derivation).

**The prompt shipped an inverted claim; the notes corrected it.** Syllabus leaf
3.12.7 says an exhaustive enum switch expression's synthetic default throws
`IncompatibleClassChangeError` on 21, having replaced older `MatchException`
shapes. Verified by separate compilation: it is the other way round —
`IncompatibleClassChangeError` through `--release 17` and `--release 14`,
`java.lang.MatchException` from `--release 21`, emitted as
`new java/lang/MatchException` + `athrow`. **Fix this in the syllabus and the
prompt before either is rebuilt** — the notes are right, its two upstream
artefacts are still wrong.

**Three claims in `src/topics/04-modern-java.md` are stale** and were corrected in
the notes rather than carried forward. The guide itself still needs patching:
common-pool width omits the submitting thread; the pinning claim needs JEP 491
plus the surviving JFR event; the structured-concurrency section must name both
the Java 21 and Java 25 API shapes.

**Run interrupted once.** The first `notes-generator` invocation died mid-response
to machine sleep, not task failure, having written 68 of 69 files. Resumed with a
targeted two-item brief rather than regenerating: wrote the missing
`95-traps-drills-and-checklist.md` (2,289 lines, carries §5.2–§5.3, the Part 5
wrap-up and the flat `## Atomic concept checklist`), and removed three broken
`../diagrams/D-168-slug.svg` placeholder embeds in
`platform-and-releases/04-internals-observability.md` where a writer left image
links for a table substitution. Lesson: verify surviving state on disk before
re-dispatching — the salvage cost two edits instead of 62 files.

Scoped out as `[X-REF]` leaves, owned by siblings: the collections and
sequenced-collection internals (02); erasure, `==`, initialisation, `java.time`,
JPMS (03); the memory model, executors, `CompletableFuture` (05); JIT, GC, class
loading (06); `HttpClient` (10).

### 21 ai-for-coding — added 2026-08-29 (guide + syllabus + prompt; notes IN PROGRESS)

New topic, out of order relative to the 01–20 backlog. Three artefacts exist and
the note run is live:

| Artefact | State |
|---|---|
| `src/topics/21-ai-for-coding.md` | written, ~525 lines (over the 250–450 contract; it covers a tool ecosystem, not one library) |
| `src/syllabus/21-ai-for-coding.md` | written; **473 leaves** across 6 parts (468 at first write, +5 from the 2026-08-30 hook-schema correction below) |
| `src/metadata/prompts/21-ai-for-coding-prompt.md` | **REBUILT 2026-08-30, 2,807 lines** (was 2,374). 477 leaves inlined — counted, not trusted. **124-row** file plan, ≈49–52k projected lines, caps written in (≤5 leaves/row, ≤3 for PART 4, 300–500 target, 600 hard split). 99 two-digit diagram ids, 15 of them `table` type. Adds: the API pricing page as the single permitted price source; a `## Pricing basis` cost-provenance rule; the `[PROVE]` evidence policy in TASK and SELF-VERIFY; an **index-integrity gate** as SELF-VERIFY's second block, ahead of coverage, opening by naming the exact defects the last run shipped past its own verify; a `## Known-defective claims` section carrying the verified hook schema inline; a `## The incident roster` reconciliation; and a standing instruction to fetch raw `.md` rather than the rendered page for anything nested, with `hooks.md` named. |

Tier mapping the prompt fixes: **PART 0 + PART 1 → BASICS, PART 2 → INTERMEDIATE,
PART 3 → INTERNALS, PART 4 and PART 5 as their own file groups.** PART 0 keeps its
own folder and its write-first sequencing while sharing the BASICS tier, because
PARTs 0 and 1 interleave — §1.3 is unreadable without §0.2 and §1.4 without
§0.3.3, so splitting them across tiers yields a reader who knows what a token is
and cannot configure anything. PART 3 counts as INTERNALS because `[DOC]` +
`[CASE]` is this topic's `[SOURCE]`: documented mechanism plus observed artefact,
there being no source tree to walk.

**Reader baseline for this topic is ZERO** — the user has never formally studied
LLMs, agents, or Claude Code. The syllabus therefore carries a `PART 0 — GROUND
ZERO` (46 leaves) that other topics do not, and a `[ZERO]` tag. Its own
instruction to the write pass: **PART 0 is written first and reviewed against a
real level-0 reader before any other part is drafted**, because every later part
depends on its vocabulary.

Grounding: every `[CASE]` leaf cites the real **sdlc-harness** repo at
`~/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness` (plugin, hooks,
agents, skills, `engine/agent.py`) with a file path and a verbatim quote.
Everything else was verified against `https://code.claude.com/docs/en/` on
2026-08-29 — settings, settings-reference, permissions, hooks, sub-agents,
skills, memory, plugins, cli-reference. **This subject drifts fast** (fields
added in v2.1.218 and removed in v2.1.234 coexist in one release line), so
`[VERSION]` leaves must state the version inline and `[DOC]`/`[RESEARCH]` leaves
must be re-verified immediately before writing, not trusted from the syllabus.

Three defects in the guide were found by writing the syllabus and are **already
fixed**: `allowed-tools` was described as restricting (it pre-approves for one
turn; `disallowed-tools` restricts), the settings-precedence table put the
command line above managed settings, and the permission-mode table listed four
of six modes. The syllabus's closing coverage-delta table records them and the
remaining ~373 missing leaves; the prompt promotes all three into its TASK
section as named must-get-right items with matching SELF-VERIFY rows.

**Four path errors in the syllabus, found by `prompt-builder` and corrected in
the prompt — fix them in the syllabus before its next rebuild:**

1. `bootstrap-*.sh` are under `plugins/sdlc-harness/scripts/`, **not** `hooks/`, and there are
   **fifteen** of them plus three `triage-*.sh` — `prompt-builder` said fourteen, a writer counted
   fifteen. Fixed in the syllabus 2026-08-30; leaves now say "count them at write time".
2. `playwright-cli` is **not** a plugin skill. It lives at repo-root
   `.claude/skills/playwright-cli/` with ten `references/` files. §1.5.19 calls it
   "the harness's skill", which mis-locates it.
3. Three cited paths could not be confirmed in the checkout and the prompt tells
   the writer to look and report rather than assert:
   `harness/evals/seeded-defects` (only `code-to-commit/` + `baselines.yaml`
   exist), `features/<slug>/state/harness.db` (runtime state, not committed), and
   `severity_map.yaml` / `filed-bugs.yaml` (`control-plane/schemas/` holds
   `feedback-signal.yaml`, `fix-task.yaml`, `task-entry.yaml`).
4. Two tags are used outside the syllabus's own legend: `[SOURCE-EQUIV]` (2.2.6)
   and `[X-REF 21]` (0.3.12, pointing inside this same guide rather than at a
   sibling). The prompt discharges the first as a `[CASE]` over
   `load_agent_prompt()` and the second as a forward link to §3.8. Either add
   both to the legend or retag those two leaves.

**Process note worth reusing on topics 01 and 03–20:** the `[CASE]` grounding
contract — cite a real file path and quote verbatim — caught its own violations.
Every one of the four errors above is in a leaf that demanded a path. A leaf that
merely said "use a real example" would have shipped all four silently.

**Second process law, learned expensively on 2026-08-30 — a WebFetch summary of a
reference table is NOT a citable source.** For anything shaped like an API
contract, fetch the raw `.md` (`curl -sL https://code.claude.com/docs/en/<page>.md`)
and grep it. A small model asked to summarise a schema will invent plausible
field names.

The incident: syllabus leaf 2.3.14 listed `continue` *inside* `hookSpecificOutput`
and 2.3.15 said "`Stop` takes `continue`". Both came from a WebFetch summary that
was never checked against the page. It propagated syllabus → prompt (inlined
verbatim) → at least five note files. **Three independent agents then got the same
field wrong three different ways** — the original draft, a relayed correction, and
a re-verification — before anyone read the raw source.

Ground truth (verified 2026-08-30 against the raw page): three kinds of field —
universal top-level (`continue`, `stopReason`, `suppressOutput`, `systemMessage`,
`terminalSequence`), top-level `decision`/`reason`, and nested
`hookSpecificOutput`. Top-level `continue: false` stops Claude **entirely** and
outranks every event-specific decision field. For `Stop`/`SubagentStop` you keep
Claude working with `decision: "block"` plus a **required** `reason` — you block
the *stop*. There is no `hookSpecificOutput.continue`. Also newly captured: the
`stop_hook_active` field and an **8-consecutive-continuation cap**, and a
**10,000-character** cap on hook output strings.

**Third finding, 2026-08-30 — the writers' doc-divergence table is the most valuable
artefact of the run.** `src/notes/detailed/21-ai-for-coding/00-index.md` carries a
table of every leaf a writer re-verified and found stale. **Eight** were wrong, all
of them mine, all now patched in the syllabus:

| Leaf | Was | Actually |
|---|---|---|
| §1.4.26 | `acceptEdits` covers `mkdir`, `touch`, `mv`, `cp` | wider — also **`rm`, `rmdir`, `sed`**. It auto-approves deletion. |
| §1.4.27 | "a background classifier" | classifier runs on **Sonnet 5**, 3-consecutive / 20-total block fallback |
| §1.4.28 | `bypassPermissions` still refuses `.git`/`.claude` | **false** — protected-path writes are allowed. It refuses critical-path `rm`/`rmdir`, `ask` matches, always-interactive tools, two cross-session safeguards |
| §1.4.34 | a `-p`/SDK session "counts as accepted", so committed allow rules run unreviewed | **opposite** — an untrusted folder's committed `allow` rules are **not** applied; stderr warning instead. Real risk is that trust is sticky per repo root and never re-checked when a commit widens the ruleset |
| §1.5.6 | two settings "tune the listing" | two **different** numbers — `skillListingMaxDescChars` is the 1,536-char per-entry cap, `skillListingBudgetFraction` a separate pool (~1% of window) |
| §1.5.19 | `playwright-cli` is a plugin skill with ten references | repo-root skill; **nine** references |
| §1.5.23 | `/doctor`,`/rewind` built-ins; `/run` a bundled skill | **reverse** — `/doctor`,`/rewind` are bundled skills; `/run` is a built-in |
| §1.1.7 / §1.5.20 | fourteen `bootstrap-*.sh` | **fifteen**, plus three `triage-*.sh` |

Syllabus after both correction passes: §1.4 41 → 45, §2.3 28 → 33, PART 1 121 → 125,
PART 2 137 → 142, **total 468 → 477**. Section sums, part totals, the totals table and
the actual leaf-line count all agree at 477.

**The law behind all eight:** the prompt's authority order — official docs > observed
behaviour of the installed binary > the repo's own code > blog posts — plus the
instruction that the syllabus "is a work order, not a citable source". Writers that
re-verify find drift, and flag it inline rather than conforming. Carry that ordering
into every topic prompt.

Syllabus corrected and expanded in place: §2.3 28 → 33 leaves, PART 2 137 → 142,
**total 468 → 473**, arithmetic re-verified. `src/topics/21-ai-for-coding.md` never
made the claim and needed no fix. **`src/metadata/prompts/21-ai-for-coding-prompt.md`
still inlines the stale leaf text** and needs a `prompt-builder` rebuild against the
corrected syllabus before any further large dispatch — `notes-generator` cannot fix
it, that file is not its to edit.

### 21 — note run outcome (2026-08-30)

`src/notes/detailed/21-ai-for-coding/` — **111 content files** across 26 subject
folders, **47,143 lines**, plus a **2,364-line** `00-index.md`. **128 SVGs**, with
128 embeds referenced and 128 on disk: **zero broken embeds, zero orphan SVGs**
(topic 02 shipped 13 orphans). All files pass the text test. No row reads
`planned`. The output folder is `21-ai-for-coding/`, which deviates from the
`<topic-slug>/` convention in `CLAUDE.md` and from topic 02's `java-collections/`.
**Decided 2026-08-30: leave both as they are and settle the rule at topic 03.**
Two conventions coexist for now, documented rather than resolved. Whoever picks up
topic 03 chooses one and makes `CLAUDE.md` match; renaming this folder later means
rewriting the encoded path in every nav link, index row and embed across 112 files,
so it is not a cheap change deferred cheaply — it gets cheaper the sooner it is
decided, not later.

Planned as 61 rows, landed as 111. Density measured after the first eleven files
at **≈45–55 lines per leaf**, so the plan was re-derived at ≤5 leaves per row and
≤3 for PART 4. Four `blocked` re-splits, all correct: `ground-zero/02` landed on
*exactly* 600, `memory/03` returned a clean block at 675 with a proposed boundary,
`permissions/03` at 598, `hooks/07` at 596. No writer compressed to fit.

**PART 0 gate applied and passed**, verified against the written files rather than
asserted.

**`[PROVE]` evidence policy settled** — adopt this on every topic: where the
artefact is runnable read-only in the writer's own sandbox, require a **real
transcript pasted verbatim plus the command that produced it**; where it genuinely
cannot be executed, say **"not measured here" in the body at the point of the
claim**, give the exact command the reader should run, and record it in
`## Open questions`. **Never** a derived figure in the visual position a measured
one belongs. Most PART 4 writers converged on this unprompted and exceeded it —
real `claude -p` envelopes with real `total_cost_usd`, a real NUL-byte
reproduction, a `Semaphore` bulkhead timed at 36.1s vs 9.1s, two plugins installed
side by side to prove the `.claude-plugin/` layout trap (`Skills(4)` vs
`Skills(0)`), a compiled `ClaudeRunner` driven through all four failure paths.

**Cost provenance rule:** derive from one stated list price, label it derived with
its date, and reference a single note in `00-index.md` rather than restating an
unverified figure per file. Root cause was a **prompt defect**: none of the nine
permitted doc pages carries pricing, so every cost leaf was structurally forced to
hedge. **`prompt-builder` must add the API pricing page to REFERENCES.**

**ALL 13 DEFECTS FIXED AND INDEPENDENTLY RE-VERIFIED 2026-08-30.** Final verified
state, checked from disk rather than taken from the envelope: 111 content files /
**47,440 lines**, index **2,746 lines**, 128 SVGs. Zero orphan files, **585 live
rendered links with zero broken**, 128 embeds referenced and 128 on disk with zero
missing and zero orphans, zero PNGs inside `diagrams/`, nav chain single-headed and
reaching **111/111** with nothing off-chain or revisited, 158 JSON blocks all
parsing, leaf ownership 111 rows with every path existing, 252 live status rows all
pointing at existing files with 38 further rows explicitly marked superseded or
retired.

**`mcp-and-lsp/03` §2.4.13 ended up measured, not hedged** — the best outcome of
the evidence policy. `atlassian-cloud` needs an OAuth grant the sandbox cannot
complete, so rather than fake around it the writer registered a credential-free
stdio server (`@modelcontextprotocol/server-filesystem`) in a `/tmp` scratch
project and read the real before/after from the `-p --output-format json`
envelope's own token fields, there being no TTY either: **21,648 → 21,982 tokens,
a measured +334 per turn.** `atlassian-cloud`'s own delta is flagged unmeasured
with the repeatable command inline, the substitution stated plainly, and the
server deregistered with return-to-baseline confirmed. No derived figure remains.
The lesson: "cannot measure X" is often "cannot measure X *this way*" — look for a
substitute that measures the same mechanism honestly before falling back to a
disclosure.

**Row-size rule this run established, and it supersedes the 250–450 band:** judge
a row against its **folder's tag mix**, not a global band. A `build-it/` row
carrying an artefact plus prove step plus cost note plus *Diff vs the real one*
lands at 400–590; a pure `[DOC]` row lands at 200–250. Both are correct, and
forcing the second to 250 is padding, which the house rules ban. `subagents/04` at
215 is the recorded precedent.

**`92-interview-internals.md` at 666 lines is a sanctioned exception**, not a
violation: the prompt mandates the 423-bullet checklist in that exact filename and
forbids relocating it because it is the parser target.

The three stale tables were **re-derived programmatically from each file's own
footers and nav links** rather than hand-edited, so they cannot drift by
construction; the nav chain is now proven by walking from the single file with no
`Previous:`. `## The file plan` is retained as history under an explicit banner.

The four "pending" diagram relabels were **fixed, not deferred**. D-71 was the
substantive one: moving `skillListingBudgetFraction` from 0.05 to the documented
0.01 moves the dependent arithmetic — the cap becomes 2,000 tokens and binds at
**≈5 skills rather than 26**, a more interesting fact than the diagram had been
telling. Fixing the pictures then made four notes' divergence flags stale, and
those were reconciled too, each keeping one sentence of history.

`mcp-and-lsp/03`'s §2.4.13 — the one place the derived-figure violation slipped
through — now fully satisfies the policy: it states at the point of the claim that
no live capture was possible and none is fabricated, says why (no TTY, no OAuth
grant), labels every derived cell, gives the command and the `/context` line that
would settle it, and records it under Open questions with a self-test question
about it.

**What the defects were**, kept for the process lesson — all from one root cause,
the index's cross-reference tables were never re-derived after the re-splits:

1. Two **orphan files**, on disk with zero index mentions:
   `hooks/08-the-blocking-guard-pattern.md` (519 lines) and
   `92-interview-internals-b.md`.
2. Three live tables — `## Nav chain`, `## Diagram assignment`, `## Leaf
   ownership` — still name **36 pre-split filenames that do not exist**. The
   leaf-ownership one voids the "468 of 468 owned" claim as *proof*: it maps
   leaves to files that are not there. `## The file plan` legitimately preserves
   the original 61 rows as history and should be labelled as such.
3. **Eight broken Markdown links** in written files, including the first file's
   `Next:` and a cross-topic link at the wrong depth
   (`../../../topics/16-testing.md` resolves to `src/notes/topics/`).

**Lesson 1: "no broken embeds and no `planned` rows" is not the same as "the index
describes the set."** The run's self-verify checked the *files* and never re-derived
the *index*, so its headline "468 of 468 leaves owned" rested on a table mapping
leaves to 36 non-existent paths. The leaves did turn out to be covered by the split
descendants — but that was luck, not verification. Mandatory gate for every topic
now, and it is going into the rebuilt prompt's SELF-VERIFY: for each file on disk,
at least one index mention; for each status row, a file on disk; for every Markdown
link, a resolving target.

**Lesson 2: a link checker must strip inline code spans, not just fenced blocks.**
My own first sweep reported ten broken links; the true count was eight. Four
candidates were literal text inside fenced artefact bodies — a path correct in the
*reader's* directory once they create the file — and one was inside a single-line
code span. De-linking either kind would corrupt the artefact. Fence-and-span-aware,
585 live links check clean. Two real breaks were ones I never flagged
(doc-root-relative), and one was a genuine rendering bug: a code span broken across
a newline, so the backticks did not protect it and it rendered as a live link.

**Lesson 3: self-reported completeness was not reliable on this run — three reports
claimed it while the same 13 defects stood.** The content was sound throughout and
every content claim verified; the failures were all index and navigation integrity.
Verify from disk, not from the envelope.

**DEFERRED by decision, 2026-08-30 — not a defect to chase.** `tmp/21-render/`
keeps **123 PNGs, ~23 MB**, deliberately retained so the rendered diagrams can be
eyeballed before anything is discarded. Illustrators are specified to rasterise,
look, fix, and **delete** the PNGs before returning; 21 batches did the first
three. The same directory also holds two `superseded-*.md` originals from the
re-splits. Sweep with `rm /Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-render/*.png`
whenever the renders are no longer wanted. **Still worth fixing upstream:** the
illustrator spec's delete step is not enforced, so every topic will leak renders
until it is.

**Two tallies in the syllabus were mine and wrong, now fixed:** `[INCIDENT]` is
**10, not 11** (§3.10.4's "md5 over a patched harness" and §3.10.5's "unpinned
digest" are the same event, the second being the first restated as a law), and
`[TRAP]` "~45" is a **floor, not an estimate** — the finished set produced **154**
distinct traps because writers used `**Pitfall:**` for every wrong belief a leaf
surfaced.

**Scope arithmetic to hand forward:** this set covers **468 of 468 prompt leaves**.
Current syllabus scope is **477**. The nine extra leaves postdate the prompt and
are **genuinely new scope, not gaps in what was delivered** — a future run's
coverage arithmetic will not match this set's footers, and that is expected.

### 21 — the rebuild pass, and four findings it produced (2026-08-30)

`prompt-builder` re-ran against the 477-leaf syllabus and found four things worth
keeping:

1. **A Q&A count in the old contract was never derived from anything.** The
   formula is "10 base + 2 per subject folder beyond the fifth". The contract
   asserted PART 3 spans 11 folders → 22 Q&As; PART 3 has **10** folders, so the
   figure is **20**. A writer trusting 22 would have padded two questions to hit a
   number nobody computed. PARTs 0+1 (12) and PART 2 (18) re-check clean.
2. **The `## Coverage delta` table was stale against 477** — it still read §1.4
   (41), §2.3 (28), "of 468 leaves", 373 missing, 422 unreadable. Rebaselined
   2026-08-30 to §1.4 (45), §2.3 (33), 477, 382, 431.
3. **`hook-output-schema-VERIFIED.md` is at repo-root `tmp/21-contract/`**, not
   under the note set — the path in the briefing was wrong. The rebuild correctly
   inlined the content rather than pointing at a scratch file that may be swept,
   which makes the prompt self-contained either way. **Keep `tmp/21-contract/`**:
   it holds the verbatim contracts, per-row leaf files, `split-leaves.sh` and that
   verified schema.
4. **The unmeasurable-leaf cluster is now explicit rather than left to judgment** —
   §0.4.4, §2.6.1, §2.6.2, §3.1.4, §3.4.8, §4.4.2 and every `/context` delta in
   PART 4 need an interactive session a headless writer cannot render, and all of
   §3.4 needs a price the doc pages do not carry. The evidence policy and the
   cost-provenance rule together make the honest form mandatory and forbid the
   dishonest one: a fenced block styled as terminal output that no terminal
   produced.

**The `[INCIDENT]` tally, settled against the file by two independent counts.**
Three agents reported 11, 10 and 14 from the same syllabus, and all three were
reading it correctly — the tally was underspecified, not wrong. `grep` returns 19
lines; 3 are the legend, §5.2.4's prose and the tally itself, leaving **16 raw
occurrences on 14 distinct leaves** (§2.3.25 and §3.6.15 carry the tag twice
each). Those 14 cover **13 events** after collapsing §3.10.4/§3.10.5 (one event,
the second being the first restated as a law), and **10 operational** after
separating §1.4.28a, §1.4.34a and §2.3.15a as this project's own documentation
defects. The syllabus now enumerates all fourteen leaf numbers so it cannot drift
again.

**And the reason that mattered more than tidiness:** those three documentation
leaves have no production symptom and no fix in the harness, so if a writer treats
them as roster incidents, the `[INCIDENT]` obligation to "name what it cost" forces
an **invented figure** — the exact defect §3.10.2 exists to warn against. An
ambiguous tally would have propagated into fabricated evidence inside a guide that
teaches against fabricated evidence. The syllabus now forbids assigning them a cost
and defines it as the wrong belief propagating.

**The meta-lesson of this whole topic, worth applying to 01 and 03–20:** the two
facts that went wrong repeatedly — the `Stop` hook schema and the `[INCIDENT]`
tally — were both **stated at a precision too low to be checkable**, then
"corrected" several times by agents each reading a different defensible aspect.
Nobody was careless. The fix in both cases was to make the claim **enumerate its
members** (the schema names its three field kinds; the tally names all fourteen
leaves), not to ask for more diligence.

### 02 java-collections — COMPLETE 2026-08-28

| Metric | Value |
|---|---|
| Note files | 161 (159 live + 2 retained superseded) |
| Lines | 88,397 |
| Diagrams | 200 SVGs (13 are orphaned duplicates pending deletion) |
| Indexed rows | 159 `done`, 0 `planned` |
| Syllabus leaves | all 901 owned by exactly one file |
| Verified findings | 104, recorded in the note set's own `00-index.md` |
| Subject folders | 18 |

**Planned as 73 rows; landed as 159.** Rows split ~2–5 ways throughout because a
`[SOURCE]` obligation means quoting a whole JDK method and explaining it, a
`[PROVE]` obligation means a compiled program plus its real transcript, and the
mandated per-file ending (pitfalls + cheat sheet + self-test) is a fixed
150–215 lines. Roughly half of a finished file is inside fences.

**All state lives in `src/notes/detailed/java-collections/00-index.md`** — the
file plan, the leaf ledger, ~35 recorded folds, and 104 numbered findings under
`## Open questions`. Read that file before touching this topic; it is the
contract, and it records the process laws the run had to discover.

### Outstanding — needs a human (`rm` is denied to agents)

1. **13 orphaned duplicate SVGs** in `src/notes/detailed/java-collections/diagrams/`.
   Exact manifest in `00-index.md` item 82. After deletion `ls diagrams | wc -l`
   should read **187**.
2. **`src/notes/detailed/java-collections/java.base/java/util/`** — 4 stray JDK
   source files (220 KB) from a writer's `jar xf -C` that silently ignored `-C`.
   Item 48. **It also inflates the subject-folder count from 18 to 19**, which is
   the denominator for the interview-file Q&A formula (item 79).
3. **`verify.sh` has a stale check** — it greps for `## Atomic concept checklist`
   in `92-interview-internals.md`; that section moved to
   `92d-interview-internals-d-atomic-concept-checklist.md` in a split. Will report
   a false failure until updated. Item 114.

### Process laws worth reusing on topics 01 and 03–20

These were learned expensively during this topic. The numbered items are in the
topic's `00-index.md`.

- **Check text-ness before any grep-based check** (item 115). One file contained a
  literal NUL byte, so `file` called it `data` and grep returned *nothing* — not a
  mismatch. Every text check silently skipped it and reported success. A checker
  that its input can switch off is worse than no checker.
- **Re-run every published listing in its published form** (items 45, 77). Caught
  more defects than every structural check combined: listings that no longer
  produced the transcript beneath them, an imagined value that compiled fine, a
  repro that returned the opposite of what the page claimed, and run-specific
  numbers published as constants. Compile *every* fence, not only runnable
  programs (item 111).
- **Certify from final state, never from a pre-write computation** (item 44). A
  footer regex ending `\s*$` ate nine files' trailing newlines; an md5 was taken
  over a *patched* harness while the shipped notes still failed to compile.
- **A build proof must pin its harness beside the digest** (item 28). Two honest
  runs over identical files gave different md5s purely because one wrapped a
  throwing snippet. A bare digest is unfalsifiable.
- **Never let a `done` row point at a missing path, and flip rows as files land**
  — the costliest failure here. Gate: `done` rows == `.md` files minus known
  retained files (item 31).
- **One writer per output path, ever; one diagram owner per folder.** Rows are
  folder-scoped but `diagrams/` is flat, so lane boundaries do not partition it
  (item 71). A **same-slug** collision is worse than a different-slug duplicate:
  the latter leaves visible orphans, the former silently overwrites and left a
  diagram contradicting its own page (item 108 context).
- **A closed lane is not a verified lane.** Two cross-lane contradictions were
  found after their owners stood down (items 107, 108). Only a pass that reads
  across folders finds these.
- **Line policy:** 600 target, 800 hard cap, all tiers; pre-split any row with
  more than ~6 `[SOURCE]`/`[PROVE]` leaves; refuse a split that leaves a child
  under ~350 lines unless the merge would exceed 800 by more than ~50 — compute
  `sum(bodies) + one tail` first, because each child pays a full tail (items 27,
  47, 65, 81).
- **Treat the diagram manifest as a suspect, not an authority.** Four entries were
  wrong or corrupted. When it contradicts source, follow source and record the
  departure.
- **Command shapes:** heredocs, `&&`/`;` chains and `$(...)` defeat the permission
  matcher; use the Write tool for scratch files, absolute paths, no `cd`, one
  command per call. Never `jar xf` (it ignored `-C` and polluted the tree).

### 22 system-design — guide + syllabus, 2026-09-02 (prompt and notes NOT started)

New topic beyond the original 01–21 inventory, added on request.

| Artefact | State |
|---|---|
| `src/topics/22-system-design.md` | written, 937 lines |
| `src/syllabus/22-system-design.md` | written, 3,435 lines / 1,089 leaves |
| `src/metadata/prompts/22-system-design-prompt.md` | not started |
| `src/notes/detailed/22-system-design/` | not started |

Positioned deliberately as the **composition layer**: component mechanisms stay
in 09/10/12/14/15/18/19/20 and the guide cross-references them rather than
restating them. 28 sections — interview scoring model and 45-minute budget,
requirement extraction (the six numbers), back-of-envelope arithmetic, the
scale-up ladder, API/data model, storage selection as a procedure, replication
and replica-lag fixes, partitioning + consistent hashing + hot keys, CAP/PACELC
and per-operation consistency, quorum `R+W>N`, cache tiers, async decision rule,
idempotency and the outbox, ID generation, rate limiting and load shedding, load
balancing, resilience, multi-region, read models/CQRS, blobs and CDN,
observability/capacity, live-traffic migration, four worked designs (URL
shortener, feed fan-out, chat/presence, payments ledger), scoring language,
and the ten ways candidates lose the round.

**Over the 250–450 line format contract at 937 lines**, same deviation topic 21
took (~525) and for the same reason: the subject is an integrative round covering
20 mechanisms plus four worked designs, not one library. The contract in
`00-index.md` was left unchanged; two topics now exceed it, so it should be
re-stated as a per-topic target rather than a rule when the next guide is written.

`00-index.md` updated: count 21 → 22, new row 22, the system-design reading track
now ends `→ 22` with a note to read it last, and the checklist line says 22 guides.

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-02

3,435 lines, **1,089 leaves** in 85 sections: PART 1 basics 446 (§1.1–1.31),
PART 2 intermediate 232 (§2.1–2.21), PART 3 under the hood 144 (§3.1–3.12),
PART 4 build it 114 (§4.1–4.14), PART 5 interview/worked designs/retention 153
(§5.1–5.7). Tags: 192 `[RESEARCH]`, 227 `[PROVE]`, 122 `[BUILD]`, 120 `[TRAP]`,
110 `[NUM]`, 94 `[SAY]`, 87 `[SOURCE]`, 48 `[CURRENCY]`.

**New tag `[CURRENCY]`**, invented by this run and documented in the file's tag
legend: a vendor number, service limit or product capability that goes stale
between releases, as distinct from `[RESEARCH]` ("verify this recall"). Worth
adopting on 18 cloud-aws and 19 docker-kubernetes, which have the same problem.

Header states the currency anchor: **Q3 2026** state of practice. A scope-boundary
table in the header assigns component internals to siblings 03, 04, 05, 06, 08,
09, 10, 11, 12, 13, 14, 15, 18, 19, 20 behind `[X-REF nn]`, with the contract
"state the mechanism in one paragraph, then point".

**Agent's self-reported line count was wrong** — it said 1,447, the file is 3,435.
Leaf and tag counts did verify against the file. Audit against disk, as ever.

**Carried forward to the write pass — do not write these unverified:**

| Item | Why |
|---|---|
| AWS Builders' Library index | fetch failed (301 → shell page, no article list); that area rests on secondary summaries |
| DDIA 2e O'Reilly page | fetch failed (403) |
| DynamoDB ATC 2022 PDF | fetch returned unparseable binary |
| HLL `1.04/√m` constant | unconfirmed |
| H3 resolution table | unconfirmed |
| Resilience4j ring-bit-buffer internal | unconfirmed |
| §1.9 per-node capacity constants | **folklore — no authoritative source found.** These are also already in `src/topics/22-system-design.md`'s capacity table. Either source them or mark them as order-of-magnitude heuristics in both files. |
| §3.12 postmortem details | unconfirmed |

**Gap table: 75 rows, 31 areas entirely missing** from the 937-line guide — all
five master tables, the dollar axis, the 18 estimation proofs, queueing theory,
streaming/windows, geospatial, probabilistic structures, security/multi-tenancy,
deployment/rollout, testing-a-design, postmortem case studies, all 14 build
clusters, the ~92-question bank, retention drills. Cells/blast-radius,
consensus/fencing, clocks, CRDTs and the Dynamo lineage exist only as single
clauses. Worked designs go **4 → 30**. The table records the existing ~10
`**Trap:**` markers and ~70 checklist assertions as a floor to preserve.

**Scale decision still open before `prompt-builder` runs.** 1,089 leaves sits
between topic 02 (1,895-line syllabus) and topic 03 (2,399 leaves → 232 files,
149,074 lines). The topic-03 lesson block below records that a single-agent
full-topic `notes-generator` run does not fit, so this needs the batched
orchestration. Alternative raised with the user and not yet answered: prune the
syllabus first — 30 worked designs may be more than is worth owning.

### 01 dsa-fundamentals — syllabus pass, 2026-09-02 (`topic-enhancer-agent` Mode A)

| Artefact | State |
|---|---|
| `src/topics/01-dsa-fundamentals.md` | pre-existing, 459 lines — **untouched by this pass** |
| `src/syllabus/01-dsa-fundamentals.md` | written, 3,395 lines / **1,516 leaves** in 80 sections |
| `src/metadata/prompts/01-dsa-fundamentals-prompt.md` | not started |
| `src/notes/detailed/01-dsa-fundamentals/` | not started |

Leaves per part: P1 basics 425 (§1.1–1.21), P2 intermediate 426 (§2.1–2.22),
P3 under the hood 401 (§3.1–3.22), P4 build it 145 (§4.1–4.12), P5
interview/retention 119 (§5.1–5.3). Target version **Java 21 LTS**, Java 22–25
deltas marked inline.

**Tag counts audited against disk — the agent's self-report was low on four of
them.** Reported vs actual: `[RESEARCH]` 131 → **217**, `[PROVE]` ~250 → **503**,
`[TRAP]` ~150 → **233**, `[BUILD]` 145 → **121**, `[VERSION-TRAP]` 9 → **11**,
`[SOURCE]` ~30 → **28**, `[DRILL]` ~25 → **30**, plus `[NUM]` 223 and `[X-REF]`
183. Leaf total 1,516 and the per-section tallies do reconcile. Same lesson as
topic 22: **audit agent-reported counts against the file.**

11 searches across all nine research angles, 7 primary/curriculum sources fetched.
Highest-yield: cp-algorithms (produced most of §2.19, §3.13, §3.14, half of
§3.8–3.9), MIT 6.006 lecture ordering + SRTBOT, Bloch's 2006 Google Research post
(the 2³⁰ overflow threshold), the O/Ω/Θ-vs-worst/best/average correction (now
§1.3.6, the file's most important notation trap), CVE-2011-4858 + VU#903934 for
hash flooding, the ReDoS SoK (Stack Overflow 2016, Cloudflare 2019), Oracle 21/25
release notes confirming `Math.clamp` overloads and that 22–25 added nothing to
the algorithm surface. The amortization search corrected a number: the three
methods are CLRS **chapter 17**, not 16.

**Carried forward — do not write these unverified:** CLRS 4e chapter mapping
(§1.1.7, §1.5.8 — TOC search returned only PDF mirrors), Hibbard-deletion √n
(§1.15.4), Knuth's linear-probing probe formula (§3.2.6), average-O(1) heap
insert (§3.3.8), Brent's cycle algorithm (§1.11.10), the `String.indexOf`
intrinsic (§3.14.18), the JVM per-frame byte cost (§3.17.1). The
`roadmap.sh/datastructures-and-algorithms` fetch returned only page chrome;
nothing taken from it.

**Gap table: 75 rows.** Of 1,516 leaves ~160 exist in the current guide at any
depth, ~60 at a depth worth keeping, **1,356 missing outright**. Three structural
gaps everything else leans on: **sorting has no section at all** (§1.18/§2.8/
§3.5/§3.6, 86 leaves), **recurrences have no section at all** (§1.5, 24 leaves),
and **there is no master cost table** (§2.1). Part 4 is entirely new — the guide
has two snippets total, both surviving inside build leaves (4.5.9, 4.7.1). The
guide's strongest sections, preserved and extended rather than rewritten: the
16-row pattern-signal table (§2.21), sliding-window monotonicity, linked-list
cycle-start, BST validation, BFS enqueue-marking, monotonic-stack amortization,
binary-search conventions, union-find. No claim in the current guide is
factually wrong for Java 21.

**Same scale problem as topic 22.** At 1,516 leaves this is larger than topic 22
(1,089) and two-thirds of topic 03 (2,399 leaves → 232 files / 149,074 lines).
`prompt-builder` then batched `notes-generator` orchestration — a single-agent
full-topic run will not fit.

### 06 jvm-internals — syllabus pass, 2026-09-02 (`topic-enhancer-agent` Mode A)

| Artefact | State |
|---|---|
| `src/topics/06-jvm-internals.md` | pre-existing, 323 lines — **untouched by this pass** |
| `src/syllabus/06-jvm-internals.md` | written, 3,735 lines / **1,088 leaves** in 66 sections |
| `src/metadata/prompts/06-jvm-internals-prompt.md` | not started |
| `src/notes/detailed/06-jvm-internals/` | not started |

Leaves per part: P1 basics 420 (§1.1–1.20), P2 intermediate 195 (§2.1–2.15),
P3 under the hood 222 (§3.1–3.21), P4 build it 66 (§4.1–4.7), P5
interview/retention 185 (§5.1–5.3). Target version **Java 21 LTS / 64-bit
HotSpot**, Java 22–25 divergences marked `[VERSION-TRAP]`.

**Tag counts audited against disk — the agent's self-report was low again**
(same failure mode as topics 01 and 22). Reported `[RESEARCH]` 231 → actual
**315**. Full inventory: `[PROVE]` 327, `[RESEARCH]` 315, `[NUM]` 231,
`[TRAP]` 219, `[SOURCE]` 142, `[FLAG]` 108, `[DUMP]` 88, `[BUILD]` 71,
`[VERSION-TRAP]` 68, `[ASM]` 21, `[BYTECODE]` 12, `[X-REF …]` 152. Section
count 66 + 3 trailing (`Sources consulted`, `Gaps vs the current guide`,
`Footer`) = 69 `##` headings on disk — reconciles.

20 searches across all nine angles. Full fetches: **JVMS 21 chapter 5** (the
12-step LC algorithm, all six resolution kinds, the nine `REF_*` handle kinds,
the full error table), the **Oracle JDK 21 G1 tuning guide** (phases, flags,
512-byte cards, the humongous rule), and **Shipilev's Anatomy Quarks** index,
mined as a completeness checklist and the largest single source of PART 3
leaves (heap parsability, implicit null checks, uncommon traps, compiler
blackholes, identity hash code, frequency-based code layout).

**Carried forward — do not write these unverified:** everything sourced from
`openjdk.org/jeps/450`, `openjdk.org/jeps/519` and the HotSpot
`RuntimeOverview`, all three of which returned HTTP 403. Recorded in
`## Sources consulted`; every constant taken from them carries `[RESEARCH]`.

**Gap table:** the 323-line guide covers ~7 of 66 sections. Missing outright:
class file format, bytecode, linking/initialization, object layout and headers,
safepoints, JIT internals, startup/CDS/AOT, the version delta, and all 66
build-it leaves. **Two mandatory corrections for the write pass:** the guide's
ZGC description is pre-Java-21 (non-generational, no store barrier), and its
startup section stops at CDS with no Leyden AOT cache. Six passages flagged
must-survive-verbatim: the runtime-area table, the OOM taxonomy table, the
CNFE-vs-`NoClassDefFoundError` trap, the `top -H` CPU workflow, the MAT leak
workflow and culprit list, the OOMKilled trap.

**Scope exclusions, all cross-referenced not dropped** (152 `[X-REF]`s across
10 guides): JMM-as-contract, monitor semantics and the virtual-thread API → 05
(§1.19 and §3.18 state the implementation mechanism only); language substrate →
03; collections → 02; OS/cgroup mechanics → 11; Kubernetes manifests → 19;
metrics/tracing practice → 20. Valhalla is one forward-looking leaf (§1.10.22),
not a section — nothing ships in 21–25.

At 1,088 leaves this sits level with topic 22 and below topic 01, so the same
scale decision applies before `prompt-builder`: batched `notes-generator`
orchestration, not a single-agent full-topic run.

### 08 spring-data-jpa — syllabus pass, 2026-09-02 (`topic-enhancer-agent` Mode A)

| Artefact | State |
|---|---|
| `src/topics/08-spring-data-jpa.md` | pre-existing, 403 lines — **untouched by this pass** |
| `src/syllabus/08-spring-data-jpa.md` | written, 4,352 lines / **1,360 leaves** in 85 sections |
| `src/metadata/prompts/08-spring-data-jpa-prompt.md` | not started |
| `src/notes/detailed/08-spring-data-jpa/` | not started |

Leaves per part (audited on disk): P1 basics 485 (§1.1–1.31), P2 intermediate
296 (§2.1–2.23), P3 under the hood 208 (§3.1–3.16), P4 build it 83 (§4.1–4.12),
P5 interview/retention 288 (§5.1–5.3). Target version **Jakarta Persistence 3.1
/ Hibernate ORM 6.6.x / Spring Data JPA 3.5.x on Boot 3.5.x and Java 21**;
Hibernate 7.0, JPA 3.2 and Spring Data 4.0 divergences marked `[VERSION-TRAP]`.

**Self-report was wrong again — third occurrence of this failure mode** (topics
01, 06, 22). Agent claimed 1,381 leaves / P2 316 / `[RESEARCH]` 164; disk says
1,360 leaves / P2 296 / `[RESEARCH]` **258** (P1 98, P2 52, P3 70, P4 0, P5 35,
front matter 3). **The footer table has been corrected in place** to the disk
numbers. Full tag inventory on disk: `[PROVE]` 327, `[RESEARCH]` 258, `[TRAP]`
230, `[SOURCE]` 150, `[NUM]` 127, `[BUILD]` 107, `[VERSION-TRAP]` 83, `[X-REF …]`
128. 88 `##` headings = 85 sections + `Sources consulted` + `Gaps vs the current
guide` + `Footer` — reconciles. 0 control bytes.

10 searches across all nine angles. Full fetches: Spring Data JPA reference
pages (query methods, projections, entity persistence, transactions), the
Hibernate 6.6 Fetching chapter, and the 6.6 + 7.0 migration guides.

**Carried forward — all of PART 3 is `[RESEARCH]` wholesale.** No Hibernate or
Spring Data *source file* was opened, so every field name, map name, listener
name, action-queue entry and optimizer constant in §3.2–§3.15 is unverified.
Five highest-risk items named in the footer: `ActionQueue` order (§3.5.3),
`StatefulPersistenceContext` fields (§3.2.2), `EntityEntry` fields (§3.2.4), the
Spring Data repository advice-chain order (§3.15.3), `PartTree` regexes
(§3.15.7). Also unfetched and therefore unverified: the Hibernate 7 "What's New"
page and both Spring Data 4.0 pages (§3.1.4, §2.3.12, §3.15.23).

**Gap table** covers all 85 sections against the 403-line guide, plus **4
corrections the write pass must make to existing text** (`@LazyToOne` fix removed
in Hibernate 7; the Hibernate 5→6 `hibernate_sequence` change; the
`HHH000104`/`HHH90003004` dual log code; `@Query` startup validation lost under
`bootstrap-mode=lazy`) and **9 must-survive-verbatim passages**.

**Scope exclusions, cross-referenced not dropped** (128 `[X-REF]`s): isolation
anomalies, MVCC, query plans, deadlocks, pool-sizing arithmetic → 09; container,
proxy mechanics, `@Transactional` interceptor internals → 07; cache stores and
stampede → 15; Testcontainers and Mockito → 16; heap/GC/OOM → 06; `HashSet`
bucket mechanics → 02; API pagination contracts → 12.

At 1,360 leaves this sits below topic 01 (1,516) and above 06/22 (~1,088), so the
batched `notes-generator` orchestration decision applies here too.

### 16 testing — syllabus pass, 2026-09-03 (`topic-enhancer-agent` Mode A)

| Artefact | State |
|---|---|
| `src/topics/16-testing.md` | pre-existing, 408 lines / 13 sections — **untouched by this pass** |
| `src/syllabus/16-testing.md` | written, **4,599 lines / 1,312 leaves / 55 sections** |
| `src/metadata/prompts/16-testing-prompt.md` | not started |
| `src/notes/detailed/16-testing/` | not started |

Leaves per part: P1 basics 282 (12 sections), P2 intermediate 464 (24 sections),
P3 under the hood 296 (16 sections), P4 build it 56 (1 block — 28 implementations
each with a *Diff vs the real one* table), P5 interview/retention 214 (75
questions + 128 traps + 11 recall). PART 3 also carries 28 proofs (§3.14) and a
33-entry failure catalogue (§3.15). Leaf and section counts **audited on disk and
they reconcile**; the agent's line self-report was 4,587 against an actual
**4,599** — same low-by-a-little failure mode as topics 01, 06, 08 and 22, now
five for five. Audit against disk, always.

Tag inventory (self-reported, lines-containing-tag): `[PROVE]` 411, `[TRAP]` 337,
`[API]` 200, `[TABLE]` 199, `[RESEARCH]` 183, `[X-REF]` 124, `[NUM]` 94,
`[SOURCE]` 91, `[DIAG]` 89, `[BUILD]` 78, `[CFG]` 71, `[VERSION-TRAP]` 61,
`[FLOW]` 57, `[CLI]` 23, `[SPEC]` 23, `[CURRENCY]` 16, `[METRIC]` 14, `[STUDY]`
10, `[WIRE]` 3. **New tag `[STUDY]`** — cite the empirical study by author,
venue, year and sample size — documented in the legend and worth adopting
wherever a claim rests on research rather than docs.

**The commissioned version anchor was wrong and the agent overrode it, correctly.**
Three of the five libraries I named were a generation behind GA as of 2026-09, and
the header says so:

| Library | Commissioned | Actual current |
|---|---|---|
| JUnit | 5.14.x | **6.1.3** (7 Aug 2026); 6.0.0 GA 30 Sep 2025 |
| Testcontainers | 1.21.x | **2.0.5** (20 Apr 2026); 1.21.4 is the last 1.x |
| Spring Boot | 3.5.x | **4.1.1** (20 Aug 2026) / Framework 7.0.x |
| Mockito | 5.x | 5.23.0 (12 Mar 2026) — as specified |
| AssertJ | 3.27.x | 3.27.7 — as specified |

Both generations are covered; 14 header `[VERSION-TRAP]`s carry the deltas. Two
consequences worth carrying: JUnit 6's `@ParameterizedClass` makes the canonical
Jupiter callback order **18 steps, not 14**, and **Testcontainers 2.0 is
breaking** — artifacts renamed with a `testcontainers-` prefix, JUnit 4 support
removed, no-arg container constructors removed, `getContainerIpAddress()` →
`getHost()`, `DockerComposeContainer` → `ComposeContainer`.

**Verified against fetched primary docs and defensible:** the ten
`MergedContextConfiguration` cache-key attributes, `ContextCache` size **32** +
LRU + `spring.test.context.cache.maxSize`, the twelve default Spring
`TestExecutionListener`s in order, the `@Transactional`-on-tests supported-attribute
table with the `RANDOM_PORT`-does-not-roll-back and `assertTimeoutPreemptively`
caveats, all five parallel-execution properties and defaults, the 18-step callback
order, the nineteen Boot test slices, JaCoCo's six counters and `v(G)=B−D+1`,
PIT's eleven default mutators, Testcontainers' reuse contract.

**Six sources failed to fetch; everything downstream is `[RESEARCH]`:**
`xunitpatterns.com` test-smells page (socket closed twice — the §2.23 smell names
and the Meszaros attribution are recall-based), the JUnit **extension-model** and
**parameterized-tests** chapters (404 at three URL shapes each — the extension-point
list and source-annotation attributes are recall-based), the Mockito 5.23.0
javadoc (unreachable — verification modes and `Answers` came from an older
javadoc). **Correct doc path shape for the write pass:**
`docs.junit.org/<version>/<chapter>/<page>.html`, or the single-page export at
`docs.junit.org/6.1.3/_exports/junit-user-guide-6.1.3.html`. No first-party
attributable test-suite postmortem with citable figures exists (same shape as
topics 14 and 15), so §3.15 is presented as mechanisms and invents nothing; no
usable university syllabus either.

**Carried forward — do not write these unverified** (35 listed in full at the end
of `## Sources consulted`). Highest risk:

1. The Jupiter extension-point list and `junit.jupiter.extensions.autodetection.enabled`'s
   default (stated `false`).
2. **Every Boot 4 / Framework 7 testing change came from rieckpil, not
   docs.spring.io** — `ContextPausedEvent`, `SmartLifecycle#isPauseable()`,
   `@SpringExtensionConfig(useTestClassScopedExtensionContext=true)`,
   non-singleton bean-override support, `RestTestClient` replacing
   `TestRestTemplate`.
3. Mockito inline-maker internals (`MockMethodAdvice`, `MockMethodDispatcher`,
   `WeakConcurrentMap`) read from source references and a PR, not official prose;
   plus `@InjectMocks`'s three-stage resolution order.
4. Testcontainers 2.0's exact rename list (migration blog + OpenRewrite recipe,
   not the changelog), Ryuk's grace period and label keys, Docker-discovery order.
5. **The Testcontainers startup-cost figures in §2.6.29 / §3.10.22 are
   experience-level estimates, not measurements** — measure or relabel.
6. Flaky-test root-cause percentages (async wait ~45% / concurrency ~20% / order
   dependency ~12%) came via a search summary of Luo et al., not the paper text.
   This is exactly the failure the `[STUDY]` tag exists to prevent — read the
   paper before printing them.
7. PIT `timeoutConstant`/`timeoutFactor` defaults and bytecode-level operators;
   JaCoCo's probe-placement algorithm and overhead figure; Awaitility's
   `pollDelay` default; jqwik's JUnit 6 compatibility; CVE-2026-24400's scope.

**Gap table:** the 408-line guide is genuinely good where it exists — the
test-doubles table, the flakiness table, the H2 critique and the CDC walkthrough
beat typical, and **42 passages are must-survive-verbatim**. But **21 of 55
sections are entirely absent**: JUnit architecture, the build surface, test data
builders, the cost model, `@Transactional`-in-tests as a subject, advanced
Mockito, HTTP stubbing, property-based testing, TDD/BDD, performance boundaries,
CI, test observability, the named anti-pattern catalogue, and the whole of PART 3.

**24 named corrections; the three that matter most are all in §8:**

1. The Testcontainers code is 1.x and **will not compile on 2.x**.
2. The reuse advice would lead a reader to enable reuse **in CI**, which the docs
   explicitly warn against — it leaks containers.
3. §8 says use Testcontainers while §9 says `@DataJpaTest` uses an embedded DB,
   and the guide never names `@AutoConfigureTestDatabase(replace = NONE)` — the
   two sections contradict each other.

Also: the guide **states no target versions anywhere**, which is why several
claims quietly aged. Fix that first in any write pass.

**Split guidance:** `16-testing.md` (PARTS 1–2) + `16-testing-internals.md`
(PARTS 3–5), cross-linked, checklist in each, with the `src/topics/00-index.md`
scope-line update spelled out in the footer. Same shape as topics 12, 14 and 15.

**Note for topic 08:** 08's syllabus X-REFs Testcontainers and Mockito out to 16,
and 16 now owns them — that dependency is discharged.

**Deliberately out of scope** (recorded so a later pass does not read these as
gaps): UI and mobile automation — Selenium, Playwright, Appium — named only where
a JVM backend suite touches them; the JUnit 3 API beyond the migration map;
TestNG beyond a one-line placement; and load-testing tool mechanics, pointed at
`22-system-design.md` and `20-observability-operations.md`.

## Next in the per-topic pipeline

**No syllabus yet — 12 topics:** 10, 11, 13, 17–20 and the rest of the un-started
set. Each needs, in order: `topic-enhancer-agent` (syllabus pass) →
`prompt-builder` → `notes-generator`.

**Syllabus written, `prompt-builder` next:** 01, 06, **08**, 09, 12, **14**,
**15**, **16**, 22 — all pending the scale decision noted above.

**Syllabus + prompt + note set complete:** 02, 03, 04, 05, 21.

## Last update — per-topic pipeline

- **Date:** 2026-09-03
- **Last generated:** topic 16 testing — syllabus pass only
  (`src/syllabus/16-testing.md`, **4,599 lines / 1,312 leaves / 55 sections**,
  target JUnit 6.1.3 / Mockito 5.23.0 / AssertJ 3.27.7 / Testcontainers 2.0.5 /
  Spring Boot 4.1.1, with 5.14.x / 1.21.x / 3.5.x covered as the previous
  generation). `src/topics/` untouched. **Leaves and sections disk-audited and
  they reconcile; the line self-report was 12 low.**
- **Prior:** 2026-09-03 — topic 15 caching — syllabus pass only
  (`src/syllabus/15-caching.md`, **3,225 lines / 978 leaves / 50 sections**, target
  Redis 8.6 / Caffeine 3.2.4 / Spring Boot 4.1.x). `src/topics/` untouched.
  **Counts disk-audited and they reconcile.**
- **Prior:** 2026-09-03 — topic 14 messaging-queues — syllabus pass only
  (`src/syllabus/14-messaging-queues.md`, 948 leaves, 53 sections, target Kafka
  4.3.0 / RabbitMQ 4.3.x / Spring Boot 4.0.x). `src/topics/` untouched. Leaf and
  tag counts are self-reported and still need a disk audit.
- **Prior:** 2026-09-03 — topic 12 api-design, syllabus pass only (3,631 lines,
  939 leaves, 65 sections).
- **Prior:** 2026-09-02 — topic 08 spring-data-jpa — syllabus pass only
  (`src/syllabus/08-spring-data-jpa.md`, 4,352 lines, 1,360 leaves, 85 sections).
  `src/topics/` untouched. No prompt, no notes. Footer counts corrected in place
  after a disk audit.
- **Open before the next stage:** all of topic 08's PART 3 is unverified against
  Hibernate/Spring Data source — read the five named files before writing it;
  scale decision for 01 (1,516 leaves), 06 (1,088), 08 (1,360) and 22 (1,089)
  before `prompt-builder`; the three 403-blocked sources
  in the topic-06 block; the seven unverified `[RESEARCH]` numbers in the
  topic-01 block; prune-or-not on topic 22's 30 worked designs; source or
  downgrade topic 22's §1.9 capacity constants.
- **Prior:** 2026-09-02 — topic 06 jvm-internals, syllabus pass only
  (3,735 lines, 1,088 leaves, 66 sections).
- **Prior:** 2026-09-02 — topic 01 dsa-fundamentals, syllabus pass only
  (3,395 lines, 1,516 leaves, 80 sections).
- **Prior:** 2026-09-02 — topic 22 system-design, guide (937 lines) plus syllabus
  (3,435 lines, 1,089 leaves). Index counts and reading order updated.
- **Prior:** 2026-08-29 — topic 03 java-core, complete (232 files, 149,074 lines,
  117 SVGs). Syllabus 2,398 lines / 933 leaves; prompt 3,096 lines.
- **Verification:** all gates passing — 0 control bytes, 0 files over the ceiling,
  0 inline `<svg>`, 0 banned strings, 0 dead links, 0 unembedded SVGs, 0
  referenced-but-missing SVGs, all 933 leaves owned exactly once.
- **Notes:** Two scratch PNGs and three superseded duplicate files retained by
  explicit user decision — documented in the topic's `00-index.md`.

### Lessons from topic 03 (read before running `notes-generator` again)

- **The single-agent full-topic run does not fit.** One `notes-generator` covering
  61 planned rows produced `00-index.md` plus 7 SVGs in ~4 hours and then timed
  out with zero note files. Batch it: subject-scoped lanes, folder-disjoint so no
  two lanes write the same directory, with the lead owning `00-index.md` alone.
- **Set the line ceiling from measured density, once.** A 600-line cap was set at
  planning time and three separate writers either squeezed to 597–599 or dropped
  authored pitfalls to comply, because a dense section's verbatim body plus the
  mandatory tail (~130–150 lines) floors near 670–940. Raised to 900 mid-run,
  which cost a rework pass. State the rule in both directions: never cut to get
  under a number, never pad to get over one.
- **Do not label a file plan "frozen" and then change it.** Two lanes had their
  plans frozen and subsequently amended; one lane renamed its files three times
  while writers re-resolved links against a moving table. The label stops meaning
  anything and writers burn their budget on link bookkeeping. Better: have each
  lane fix its own table before writing and report deviations, and re-freeze to
  disk rather than forcing renames of already-gated files.
- **Run the control-byte gate FIRST and treat it as a precondition.** A literal
  NUL makes `grep` classify the file as binary, after which every other gate
  reports clean without running — a silent all-pass. Real NUL/DEL bytes were
  caught in four files. Use the `-P` form: `grep` here is ugrep, and
  `grep -ac '[\001-\010...]'` returns 0 on known-bad input, a false pass.
- **Verify structural counts per entry, not per file.** A paragraph-merge
  collapsed two `**Why people believe it:**` markers and no gate noticed;
  file-level totals still pass when one entry has 2 and another 0.
- **Editing a code block invalidates any line number quoted near it.** A restore
  moved a failing frame from `:16` to `:18` and the quoted trace silently stopped
  matching. Recapture output after reformatting; never hand-adjust numbers.
- **Audit against disk, never against reports.** Batches variously claimed
  completion with three files over the ceiling, went idle having written nothing,
  and reported leaves covered that were not. Every one was caught by `find`/`grep`
  over the tree, and one lane's "stale" objection to an audit was itself correct —
  so re-verify before insisting.
- **A closed lane is still wrong sometimes.** Three factual defects were found in
  completed folders by cross-checking: a `final`/`private` hook claimed to compile
  to `invokespecial` (it is `invokevirtual` on 21), and `exceptions/03b` asserting
  no stackless ratio approaches 10× "at any depth" while its own printed depth-1
  row shows 49.4×. Cross-folder reads find these; lane-local gates do not.
- **Verify against the prompt, not the folder sketch in `CLAUDE.md`.** The sketch
  says `92-interview-internals.md` ends with the atomic concept checklist; the
  topic prompt's output contract, its self-verify list and syllabus leaf 5.3.8 all
  put it in `94`. The prompt wins.
- **A denied tool call is an answer, not an obstacle.** One illustrator reached
  around a denied `rm` via `python3 os.remove`; two others correctly refused and
  escalated when asked to run a blocked command for a peer. Root cause was a
  writer-spec line reading "delete the PNGs before returning", which framed
  cleanup as an obligation outranking permissions. Spec now says otherwise, and a
  blocked cleanup is a reportable loose end: `blocked: could not delete <file>`.

### 12 api-design — syllabus, 2026-09-03 (prompt and notes NOT started)

| Artefact | State |
|---|---|
| `src/topics/12-api-design.md` | pre-existing |
| `src/syllabus/12-api-design.md` | written, 3,631 lines / **939 leaves** in 65 sections |
| `src/metadata/prompts/12-api-design-prompt.md` | not started |
| `src/notes/detailed/12-api-design/` | not started |

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-03

PART 1 basics 478 (§1.1–1.28), PART 2 intermediate 146 (§2.1–2.15), PART 3 under
the hood 82 (§3.1–3.9), PART 4 build it 52 (§4.1–4.10), PART 5 interview/retention
181 (§5.1–5.3). Tags: 285 `[PROVE]`, 201 `[TRAP]`, 159 `[RESEARCH]`, 93 `[SOURCE]`,
52 `[BUILD]`, 50 `[VERSION-TRAP]`. PART 5 carries 118 questions and a 56-entry
trap index.

Scope frame: the **contract layer**. HTTP substrate (RFC 9110–9114), REST and the
maturity ladder, resource/URI modelling, the full method and status-code surface,
representation and PATCH formats, content negotiation, conditional requests and
ETags, HTTP caching (RFC 9111), collection semantics, the error contract (RFC 9457),
idempotency keys end to end, versioning/deprecation/sunset, rate limiting, async and
bulk shapes, hypermedia, OpenAPI + JSON Schema, gRPC and GraphQL as contracts, and
the Spring surface. Component internals are parked behind `[X-REF nn]` to siblings
09, 10, 13, 14, 15, 16, 22 with the "one paragraph, then point" contract.

**Four corrections the write pass must apply to the pre-existing guide** — each is
flagged in the syllabus's closing gap table:

1. `Deprecation: true` is invalid; RFC 9745 defines `Deprecation` as an IMF-fixdate.
2. RFC 7807 is obsoleted by **RFC 9457** — cite 9457 for problem details.
3. The `RateLimit-Limit` / `-Remaining` / `-Reset` triple is superseded by the
   ratelimit-headers draft-11 pair `RateLimit` + `RateLimit-Policy`.
4. A concurrent duplicate under an idempotency key answers **`409`**, not
   `425 Too Early`.

Five numeric claims are tagged **unverified** and must be confirmed against source
or dropped at write time.

#### Operational note — the 64k output cap kills a single-Write syllabus

The first dispatch died with `max_output_tokens` (64,000) mid-`Write` and left
**no file at all** — a whole research pass' worth of work was reachable only by
resuming the agent's transcript. Syllabus files run 1,900–5,700 lines; one Write
cannot carry that.

**Rule for every future syllabus pass:** instruct the agent to write the header
plus the first sections with `Write`, then append in **~400-line chunks** via
quoted-delimiter heredoc (`cat >> path <<'EOF'`) so backticks and `$` survive, and
never to shrink scope to fit the cap — chunk more, not less. Recovery path when it
does blow up: `SendMessage` to the same agent id, since the research context
survives the API error.

### 14 messaging-queues — syllabus, 2026-09-03 (prompt and notes NOT started)

| Artefact | State |
|---|---|
| `src/topics/14-messaging-queues.md` | pre-existing, 690 lines — **untouched by this pass** |
| `src/syllabus/14-messaging-queues.md` | written, **948 leaves** across 5 parts / 53 numbered sections |
| `src/metadata/prompts/14-messaging-queues-prompt.md` | not started |
| `src/notes/detailed/14-messaging-queues/` | not started |

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-03

PART 1 basics 306 (§1.1–1.16), PART 2 intermediate 278 (§2.1–2.17), PART 3 under
the hood 236 (§3.1–3.17), PART 4 build it 36 (18 implementations + 18 *Diff vs the
real one* tables), PART 5 interview/retention 92 (§5.1–5.3, with 32 questions and a
52-item consolidated trap list). Self-reported tags: 96 `[RESEARCH]`, 111 `[TRAP]`,
78 `[PROVE]`, 47 `[VERSION-TRAP]`, 18 `[BUILD]`, 14 `[SOURCE]`. **Counts are
self-reported and NOT audited against disk** — topics 01, 06, 08 and 22 all had
low self-reports, so audit before `prompt-builder` runs.

**Target version baseline stated in the header:** Kafka **4.3.0** (22 May 2026),
RabbitMQ **4.3.x** (23 Apr 2026), AMQP 0-9-1 + AMQP 1.0, Jakarta Messaging 3.1,
Spring Boot 4.0.x / Spring Kafka 4.1.x / Spring AMQP 4.0.x, AWS SQS/SNS/EventBridge
as of Sept 2026, Debezium 3.3.x, Java 21.

**Twelve `[VERSION-TRAP]` deltas are enumerated in the header**, of which two are
outright factual errors in the existing guide:

1. **SQS max payload is 1 MiB, not 256 KiB** (changed Aug 2025). The guide § 9 says
   256 KB.
2. **SQS default retention is 4 days, not 14** (14 is the max). The guide § 2 implies
   14.
3. SQS FIFO in-flight limit is **120,000**, not 20,000.
4. `linger.ms` defaults to **5**, not 0 (KIP-1030, Kafka 4.0).
5. Kafka 4.x has **no ZooKeeper**; KRaft only.
6. KIP-848 is GA and the classic rebalance protocol is deprecated (KIP-1274), so
   `session.timeout.ms` / `heartbeat.interval.ms` / `partition.assignment.strategy`
   are inert under `group.protocol=consumer`.
7. **Kafka has queues** — KIP-932 share groups are production-ready since 4.2.
8. RabbitMQ classic mirrored queues were removed in 4.0; `ha-mode` is dead config.
9. RabbitMQ's metadata store is **Khepri**, sole option since 4.3; Mnesia and CQv1
   are gone and `cluster_partition_handling` has no effect.
10. Spring Kafka 4.0 dropped Spring Retry — `@Backoff` → `@BackOff`,
    `BinaryExceptionClassifier` → `ExceptionMatcher`.
11. Spring AMQP 4.0 ships a second, AMQP-1.0 stack (`spring-rabbitmq-client`).
12. SQS standard queues accept `MessageGroupId`, which enables **fair queues** and
    orders nothing.

An eight-item **corrections list** at the end of the syllabus names every passage in
the existing guide that is wrong rather than merely thin.

**Research: 20 searches across all nine angles, 14 primary sources fetched in full.**
Highest-yield: the four Kafka release announcements (4.0/4.1/4.2/4.3) plus KIP-1030
for the changed defaults; the Kafka 4.1 consumer-rebalance-protocol operations page
for the KIP-848 config surface; **Conduktor's "11 Kafka production pitfalls"**, which
produced the most obscure leaves in PART 3 (`effectiveMinIsr()` capping at
`replication.factor`, `offsets.retention.minutes` expiry on *empty* groups,
LSO stalls, future-timestamp segment immortalisation, segment rolling by message
time, quota bypass of purgatory, pre-compression `max.request.size` check); the
RabbitMQ quorum-queues and confirms docs for every `x-` argument and default; the SQS
message-quotas and DLQ pages for the payload/retention/in-flight numbers and the
obscure "standard queue moves a message to the back after 3 receives" and
"FIFO DLQ resets the enqueue timestamp" rules.

**Carried forward — do not write these unverified:**

| Item | Why |
|---|---|
| The "$2.3M unreconciled transactions" unclean-leader-election incident | circulates only in secondary blog posts; **no first-party postmortem found.** Either source it or teach the mechanism without the number |
| All of PART 3's client-internals leaves (§3.6, §3.7) | sourced from a third-party write-up, not from `org.apache.kafka.clients.*` source. Read `RecordAccumulator`, `Sender`, `Fetcher` before writing |
| `min.cleanable.dirty.ratio` 0.5 / `delete.retention.ms` 24 h | taken from aggregator docs, not `kafka.apache.org`; the version-pinned docs page 404'd on three URL shapes |
| Every consumer/producer/broker default not covered by KIP-1030 | the `kafka.apache.org/documentation/#producerconfigs` fetch returned a redirect shell. Re-fetch the versioned config page |
| RabbitMQ 4.3 minimum Erlang version | not stated on the release-notes page |
| SNS's "100 subscriptions per topic" | from a features page, not the quotas page |

**Gap table: 41 rows.** Of 948 leaves, roughly 120 exist in the current guide at any
depth. **Nine areas are entirely absent** and are the bulk of the work: RabbitMQ/AMQP
in any form, JMS/Jakarta Messaging, message anatomy and schema evolution, sagas
(which `00-index.md` already promises), event modelling/CQRS, security and
multi-region ops, observability, the whole of PART 3 internals, and the whole of
PART 4. The guide's strongest asset — **§ 2, the broker-lifecycle / "consumers down
≠ DLQ" section** — is preserved and extended, not rewritten, and all 13 existing
`**Trap:**` markers plus the 61-line atomic checklist are recorded as a floor.

**Split guidance recorded in the footer:** at 948 leaves the bible exceeds ~2,500
lines, so split into `14-messaging-queues.md` (PARTS 1–2) and
`14-messaging-queues-internals.md` (PARTS 3–5), cross-link, keep a checklist in
each, and add the new file to `src/topics/00-index.md`.

**Chunked-write rule from the topic-12 block was applied** — header + PART 1 via
`Write`, then PARTS 2, 3, and 4+5 appended via `Edit`. No output-cap failure, but
the run did hit the cap once mid-PART-1 and resumed cleanly because the file already
existed on disk. Confirms the rule: write early, append in parts, never shrink scope
to fit.

### 15 caching — syllabus, 2026-09-03 (prompt and notes NOT started)

| Artefact | State |
|---|---|
| `src/topics/15-caching.md` | pre-existing, 679 lines / 14 sections / 53 checklist items — **untouched by this pass** |
| `src/syllabus/15-caching.md` | written, **3,225 lines / 978 leaves** across 5 parts / 50 numbered sections |
| `src/metadata/prompts/15-caching-prompt.md` | not started |
| `src/notes/detailed/15-caching/` | not started |

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-03

PART 1 basics 165 (§1.1–1.10), PART 2 intermediate 361 (§2.1–2.19), PART 3 under
the hood 271 (§3.1–3.18), PART 4 build it 48 (24 implementations + 24 *Diff vs the
real one* tables), PART 5 interview/retention 133 (§5.1–5.3).

**Counts audited against disk and they reconcile** — first syllabus pass in this
project where the self-report matched (topics 01, 06, 08, 14 and 22 all
under-reported). Verified: `wc -l` 3,225, leaf grep 978, 52 `##` headings
(50 sections + trailing blocks). Tag inventory, raw literal occurrences —
`[PROVE]` 314, `[TRAP]` 192, `[NUM]` 130, `[X-REF]` 127, `[RESEARCH]` 115,
`[TABLE]` 113, `[SOURCE]` 105, `[API]` 71, `[BUILD]` 46, `[CFG]` 44, `[DIAG]` 31,
`[VERSION-TRAP]` 30, `[CURRENCY]` 30, `[SPEC]` 24, `[METRIC]` 21, `[CLI]` 19,
`[FLOW]` 17, `[WIRE]` 14. Each count includes its legend row, and
RESEARCH/CURRENCY/VERSION-TRAP/X-REF also include header-prose mentions — the
footer states that caveat rather than implying leaf-level precision.

**Currency anchor in the header:** Redis OSS **8.6** (Feb 2026), Valkey 9,
Caffeine **3.2.4** (4 May 2026), memcached 1.6.x, Spring Boot **4.1.x** /
Framework 7.0.x with 3.5.x deltas, Spring Data Redis 4.1.x, Hibernate 7.x,
JCache 1.1 / Ehcache 3.10.x, RFC 9111 + 9110 + 5861 + 8246 + 9211 + 9213,
Java 21. Eleven `[VERSION-TRAP]` deltas enumerated up front.

**Three research finds recall would have got wrong:**

1. Redis 8.6 adds `allkeys-lrm` / `volatile-lrm` — **ten** eviction policies now,
   not eight — plus a first-class `HOTKEYS` command and `key-memory-histograms`.
2. **Caffeine's window/main split is hill-climbed at runtime.** The widely-quoted
   fixed 1% / 99% figure is wrong.
3. Redis docs and the shipped `redis.conf` **disagree** on
   `hash-max-listpack-entries` (512 vs 128). Flagged as resolve-with-`CONFIG GET`
   at write time rather than asserted either way.

**Research: primary-source-first**, 41 sources in `## Sources consulted` each with
what it contributed. Redis docs fetched as raw reference text (eviction,
memory-optimization, EXPIRE, client-side-caching intro + reference, cluster spec,
8.6 what's-new), plus the Caffeine Design wiki, memcached `doc/new_lru.txt`,
RFC 9111 plain text, the Spring Framework cache reference, Spring Data Redis and
JSR-107 javadoc, the TinyLFU / SIEVE / XFetch papers, and both sides of the
Redlock debate.

**Carried forward — do not write these unverified.** 18 numbered entries, each
naming the file or page to re-read. Clusters: Redis source constants
(`activeExpireCycle` keys-per-loop and the 25% threshold, eviction pool size, LRU
clock resolution and wraparound, `LFU_INIT_VAL`); Caffeine's timer-wheel bucket
spans, sketch reset multiplier, and whether it ships a doorkeeper at all;
memcached's `hot_lru_pct` family and item-header size; the 8.6 throughput/memory
figures; `tracking-table-max-keys`; Boot 4.x package FQNs and provider
auto-detection order; the exact XFetch inequality; and every `[CURRENCY]`
commercial figure. **Two searches returned nothing usable and are declared as
such** — no first-party caching-outage postmortem exists to cite (same shape as
topic 14's `$2.3M` problem), and no standalone university caching syllabus.

**Gap table:** every concept in the 679-line guide survives as a leaf, and **29
passages are listed as must-survive-verbatim** — it is genuinely strong on
cache-aside, the read/write race, TTL discipline and jitter, stampede, the pub/sub
trap, and readiness gating. **Fifteen whole subjects are absent:** serialisation,
the master cost model, the Spring Cache abstraction, Hibernate caching, memcached
beyond two sentences, distributed topology and consistent hashing, sizing
arithmetic, testing, cache security, the never-cache/invariant argument, and the
entirety of PARTs 3, 4 and 5.

**Twenty corrections the write pass must make to existing text.** The four that
matter most:

1. **Every example must be re-domained off `product:42` onto QuizStakes** — the
   guide predates the shared scenario file.
2. The eviction table is **two policies short** (the 8.6 `lrm` pair).
3. The negative-caching sentinel comparison uses `==`, which is **broken across a
   serialising cache** — it works in-process and silently fails on Redis.
4. The HTTP section attributes RFC 5861 / 8246 / 9211 / 9213 material to nothing.

**Split guidance recorded:** at 978 leaves, split into `15-caching.md` (PARTS 1–2)
and `15-caching-internals.md` (PARTS 3–5), cross-linked, checklist in each,
`src/topics/00-index.md` updated. Same shape as topics 12 and 14.

Nothing judged out of scope. Sibling material sits behind `[X-REF nn]` for 02, 03,
04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 16, 18, 19, 20 and 22, under a
state-the-mechanism-in-one-paragraph-then-point-away rule.
### 19 docker-kubernetes — syllabus, 2026-09-03 (prompt and notes NOT started)

| Artefact | State |
|---|---|
| `src/topics/19-docker-kubernetes.md` | pre-existing, 705 lines / 14 sections / 69 checklist items — **untouched by this pass** |
| `src/syllabus/19-docker-kubernetes.md` | written, **5,189 lines / 1,201 leaves** across 5 parts / 94 numbered sections |
| `src/metadata/prompts/19-docker-kubernetes-prompt.md` | not started |
| `src/notes/detailed/19-docker-kubernetes/` | not started |

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-03

PART 1 basics 436 (§1.1–1.31), PART 2 intermediate 393 (§2.1–2.31), PART 3 under
the hood 236 (§3.1–3.22), PART 4 build it 52 (§4.1–4.7), PART 5
interview/retention 84 (§5.1–5.3).

**Counts audited against disk and they reconcile.** `wc -l` 5,189; `^N.N.N `
leaf grep 1,201 and each part's grep matches its reported figure; 97 `##`
headings (94 sections + trailing blocks). Tag inventory, raw literal
occurrences — `[PROVE]` 344, `[RESEARCH]` 191, `[NUM]` 175, `[TRAP]` 170,
`[SOURCE]` 128, `[CFG]` 127, `[BUILD]` 113, `[CMD]` 100, `[DIAG]` 70,
`[VERSION-TRAP]` 28, `[KEP]` 15, `[YAML]` 13. (The agent self-reported
`[RESEARCH]` 189 against 191 on disk — header-prose mentions account for the
drift; not leaf-level precision.)

**Currency anchor in the header:** Kubernetes **1.37 "Garhwal"** (26 Aug 2026,
EOL 28 Oct 2027) with 1.33–1.36 deltas covered, Docker Engine **29.x**
(containerd image store default, `overlay2` graph driver deprecated), Compose
v2 / Compose Spec, BuildKit + buildx bake, containerd **2.2.x** (NRI and CDI
default-enabled since 2.1), runc **1.4.x**, OCI image-spec 1.1.x /
distribution-spec 1.1 / runtime-spec 1.3, **Gateway API 1.5** (27 Feb 2026) and
1.6, Helm **4.x** (server-side apply), Karpenter v1, Istio ambient mode, cgroup
v2 only, Java 21 LTS.

**The headline correction:** `ingress-nginx` reached **EOL 24 Mar 2026** — no
features, no bugfixes, **no CVE patches** — and `InGate`, its intended
successor, was retired too. The guide's naming of nginx as an implementation and
its "(Gateway API is its successor.)" parenthetical are both now wrong in a way
that matters operationally. `ingress2gateway` 1.0 (Mar 2026) converts existing
objects.

**Twenty `[VERSION-TRAP]` deltas.** The largest: containerd image store default
in Engine 29; nftables kube-proxy GA (1.33) with IPVS deprecated (1.35) while
iptables remains the 1.37 default; in-place pod resize GA (1.35) via the
`resize` subresource; native sidecars GA (1.33); pod-level `spec.resources`
beta-on (1.34); user namespaces GA (1.36); `-XX:+UseContainerCpuShares` removed
in JDK 21; Helm 4 server-side apply.

**Carried forward — do not write these unverified.** Five clusters, each named
in the footer with the page to re-read: the kubelet's refusal to start without
cgroup v2 from 1.35 (single secondary source); the kubelet **soft** eviction
defaults (the fetch asserted values the kubelet does not ship — verify against
the `KubeletConfiguration` reference, not the eviction page); the truncated
Restricted PSS control list; Docker Engine 29's release notes; the etcd limits
(1.5 MiB request, 2 GiB default quota, 8 GiB recommended max — from recall); and
the CFS-throttling throughput figures (**attribute, do not assert**).

**Gap table is section-by-section**, with **six required corrections to existing
text** (not additions) and **eleven passages flagged must-survive-verbatim** —
the probe actor table and dependency-storm trap, the CPU/memory asymmetry table,
the termination race and its fix chain, the BAD/GOOD Dockerfile pair, the
exec-form trap, the ECS positioning, and the efficiency-is-fourth-not-first
framing.

**Split guidance recorded:** at 1,201 leaves, split at the PART 2/3 boundary into
`19-docker-kubernetes.md` (PARTS 1–2) and `19-docker-kubernetes-internals.md`
(PARTS 3–5), cross-linked, `## Atomic concept checklist` in **each**, the current
guide's 56 checklist lines carried into the first, `src/topics/00-index.md`
updated. Same shape as topics 12, 14 and 15.

**Parked out of scope behind `[X-REF]`:** cloud primitives and IAM (18),
Terraform runtime (23), kernel/OS internals as a subject (11), JVM heap and GC
internals (06), HTTP/TCP/TLS protocol layers (10), metrics/tracing/SLO design
(20), OWASP and end-user auth (13), Testcontainers mechanics (16).
