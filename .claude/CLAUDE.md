# Project: FAANG Staff / Tech-Lead Prep — Day-by-Day Notes

This project generates **exhaustive, dual-audience study notes** for a 28-week
FAANG Staff / Tech-Lead interview prep plan. The reader is a 6-year backend
engineer (Java/Spring) targeting Senior IC (L5) OR Staff / Tech Lead (L6).

## Core artifacts (DO NOT delete or rename)

| File | Purpose |
|---|---|
| `faang-staff-prep-v4-28week.md` | Master plan — single source of truth for what each day covers. Has Appendices A (Senior IC framing), B (prep anti-patterns), C (daily hours by phase). |
| `example-day-notes.md` | Day-1 canonical reference. Depth/structure/tone benchmark for all daily notes. |
| `example-week-notes.md` | Week-1 canonical reference. Depth/structure benchmark for all weekly notes. |
| `daily-prompt.txt` | The prompt template for generating a day's notes. Fill in DAY-SPECIFIC INPUT block. |
| `weekly-prompt.txt` | The prompt template for generating a week's notes (Staff-only audience). |
| `.claude/CLAUDE.md` | This file — project instructions, auto-loaded. |
| `.claude/progress.md` | Running progress tracker. Update after every generation. |
| `.claude/conventions.md` | File-naming, structure, tier-tagging discipline (detailed). |
| `.claude/workflow.md` | How to generate Day-N or Week-N notes step by step. |

## Folder structure

```
rough/
├── faang-staff-prep-v4-28week.md          (master plan)
├── example-day-notes.md                    (Day-1 benchmark)
├── example-week-notes.md                   (Week-1 benchmark)
├── daily-prompt.txt                        (day-notes generator)
├── weekly-prompt.txt                       (week-notes generator)
├── .claude/                                (this folder — project state)
│   ├── CLAUDE.md
│   ├── progress.md
│   ├── conventions.md
│   ├── workflow.md
│   └── agents/                             (project subagent definitions)
├── w<N>/                                   (per-week folder — day/week pipeline)
│   ├── week<N>-notes.md                    (weekly Staff-only overview)
│   ├── day<5N-4>-notes.md                  (e.g., w2/day6-notes.md)
│   ├── day<5N-3>-notes.md
│   ├── day<5N-2>-notes.md
│   ├── day<5N-1>-notes.md
│   └── day<5N>-notes.md                    (e.g., w2/day10-notes.md)
├── src/                                    (per-topic pipeline — see below)
│   ├── topics/                             (flat one-file-per-topic guides, 00-index.md + 01–20)
│   ├── syllabus/                           (<NN>-<slug>.md — exhaustive leaf enumeration)
│   ├── metadata/prompts/                   (<NN>-<slug>-prompt.md — self-contained generation prompts)
│   ├── knowledge/                          (gaps.md, understanding.md — measured state)
│   ├── scenario/scenario.md                (QuizStakes — the shared example domain, read-only)
│   └── notes/detailed/<topic-slug>/        (the deep multi-file note sets)
│       ├── 00-index.md                     (file plan + status, written first)
│       ├── <subtopic-slug>/                (one subfolder per subject)
│       │   ├── 01-basics.md
│       │   ├── 02-<intermediate-theme>.md
│       │   └── 03-internals-<theme>.md
│       ├── 90-interview-basics.md          (per-tier: summary + 10 Q&As + 5 puzzles)
│       ├── 91-interview-intermediate.md
│       ├── 92-interview-internals.md       (ends with atomic concept checklist)
│       └── diagrams/                       (flat, topic-scoped, D-NN-slug.svg)
│   └── notes/tailored/topic/<topic-slug>/   (tailored-topic pipeline)
│       ├── 00-map.md                       (question inventory + source ledger + file plan)
│       ├── 01-….md … NN-interview.md       (numbered by teaching order, basics → advanced)
│       └── diagrams/
└── tmp/                                    (diagnostic evidence — valuations, answers, papers)
```

Week-N covers days `5N-4` through `5N`. Example: w3/ holds day11–day15-notes.md.

## The two pipelines

**Day/week pipeline** — `faang-staff-prep-v4-28week.md` → `w<N>/day<N>-notes.md`.
Driven by the master plan and `daily-prompt.txt` / `weekly-prompt.txt`. Dual
audience, tier-tagged `[BOTH]` / `[SENIOR IC]` / `[STAFF]`. Rules below apply here.

**Per-topic pipeline** — subject-major deep dives, single audience (backend Java
engineer, 3–4 YOE), staged across agents in `.claude/agents/`:

```
topic-enhancer-agent (SYLLABUS pass)  →  src/syllabus/<NN>-<slug>.md
prompt-builder                        →  src/metadata/prompts/<NN>-<slug>-prompt.md
notes-generator                       →  src/notes/detailed/<topic-slug>/**
gaps-analyzer-agent                   →  src/knowledge/gaps.md
understanding-book-keeper             →  src/knowledge/understanding.md
```

**Tailored-topic pipeline** — one named subject, taught front to back, single
agent, no syllabus:

```
topic-note-maker  →  src/notes/tailored/topic/<topic-slug>/00-map.md + 01..NN + diagrams/
```

Works for any shape of Java topic — a type/API, a language mechanic, a runtime
subsystem, a model/contract, a framework subsystem, or a practice. It derives its
own scope (expertise pass → question inventory → coverage frame), harvests
`src/notes/detailed/` read-only for material, then orchestrates one writer per
file. Output is **self-contained** — no provenance lines in the notes; provenance
lives in `00-map.md`'s source ledger. It reuses `notes-generator`'s
`## Diagram spec` and `## The example domain` sections verbatim rather than
forking them.

Each stage reads the prior stage's output and writes only its own. Never write
across lanes — a stage that edits its input stops being independently re-runnable.
`notes-generator` **hard-stops** if the topic has no prompt; run `prompt-builder`
first. All examples in this pipeline come from the shared QuizStakes domain in
`src/scenario/scenario.md` — entities, status codes, and every number taken
verbatim; never `Dog extends Animal`, `Foo`, or `thread1`. That file is read-only. Diagrams in this pipeline are standalone SVG files embedded at the point of
explanation, never inline `<svg>` (GitHub and VS Code strip it) and never ASCII art.

## Generation rules (non-negotiable)

1. **Read the master plan's Day-N section before generating any day's notes.**
   Use absolute file path; do not paraphrase the plan from memory.
2. **Match or exceed `example-day-notes.md` depth.** Target 1500–2000 lines per day.
3. **Tier-tag every distinct sub-block** with `[BOTH]` / `[SENIOR IC]` / `[STAFF]`.
4. **Every theory topic gets all 15 § 2 sub-sections.** Never skip.
5. **Every problem gets all 17 § 3 sub-sections.** Always show brute force before optimal.
6. **Cross-reference prior days and foreshadow forward days with explicit day numbers.**
7. **Update `.claude/progress.md` after every generation.**
8. **Write notes inline. NEVER delegate to subagents.** (Day/week pipeline only.
   The per-topic pipeline is explicitly orchestrated: `notes-generator` owns
   `00-index.md` and dispatches one writer per note file plus illustrators for
   the diagrams. See its Execution model.)
9. **No emojis. No filler phrases ("Let's dive in", "Great question"). Lead with content.**
10. **Java code = Java 21 idiomatic** (records, var sparingly, pattern matching, modern Spring Boot 3.x).

## Audience tier discipline

- **[BOTH]** applies to Senior IC and Staff equally. Default tag when in doubt.
- **[SENIOR IC]** required for L5 bar — mechanics, fluency, correctness.
- **[STAFF]** L6 extensions — architecture, trade-offs, distributed variants,
  scale, organizational judgment, real-world failure case studies, 3-axis
  trade-off drills.

When tier diverges within a section: keep [SENIOR IC] base, add [STAFF]
extension as a separate sub-sub-section. Do not blend.

## Quality bar — verify before reporting done

- [ ] Every theory topic has all 15 § 2 sub-sections.
- [ ] Every problem has all 17 § 3 sub-sections.
- [ ] Every sub-block is tier-tagged.
- [ ] Brute force shown before optimal for every problem.
- [ ] At least 1 [STAFF] real-world failure case per theory topic.
- [ ] At least 1 [STAFF] streaming/distributed variant per problem.
- [ ] Cross-references (callbacks + foreshadows) explicit with day numbers.
- [ ] Java code Java 21 idiomatic, fenced, runnable.
- [ ] Tables for any ≥3-item comparison.
- [ ] Cheatsheet, self-assessment checklist, glossary, references all present.
- [ ] Footer reports line count, sections, coverage assessment per tier, deferred items.

## See also

- `.claude/workflow.md` for the step-by-step generation procedure.
- `.claude/conventions.md` for naming, structure, and tier-tagging details.
- `.claude/progress.md` for current state and what's next.