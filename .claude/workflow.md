# Workflow — How to Generate Notes

## Daily notes — full procedure

### Step 1: Read state

- Read `.claude/progress.md` to see what's next.
- Identify the target day (e.g., Day 6).

### Step 2: Read the plan's Day-N section

- Open `faang-staff-prep-v4-28week.md`.
- Find the target day's bullet point. Pull verbatim:
  - Day title
  - Day type (DSA-D, HLD-D, LLD-D, Build-D, Review-D, Mock-D, DS-D, JSD-D, Auth-D, DistTx-D, Kafka/K8s session)
  - Problems for the day
  - Theory topics for the day
  - Companion content (blog read, paper section, behavioral block)

### Step 3: Confirm DAY-SPECIFIC INPUT with user

Present the proposed inputs in the form of `daily-prompt.txt`'s DAY-SPECIFIC INPUT
block. Ask clarifying questions only on truly ambiguous decisions
(output path, depth of overlap topics, optional companion blocks).

If user is comfortable with conventions, skip clarification on routine days.

Standard inputs:

```
Day number:           N
Week number:          ⌈N/5⌉
Day title:            (verbatim from plan)
Day type:             (per plan)
Source plan lines:    Day N of faang-staff-prep-v4-28week.md
Output file:          w<W>/day<N>-notes.md  (create w<W>/ if needed)
Problems for today:   (verbatim from plan)
Theory topics today:  (verbatim from plan; if implicit, infer from problems)
Project tie-ins:      (verify by searching plan for Project 1/2/3 work on this day)
Prior callbacks:      (list concepts from earlier days this day reinforces)
Forward setup:        (list day numbers this day enables)
Companion content:    (blog read, paper section, behavioral, mock — per plan)
```

### Step 4: Generate

- Single `Write` call to output path.
- Follow `.claude/conventions.md` structure exactly.
- Match `example-day-notes.md` depth and tone.
- Target 1500–2000 lines.

### Step 5: Verify

- Run `wc -l` on the output file.
- Confirm structure (§ 0 through § 10 + footer present).
- Confirm tier tags on every distinct sub-block.

### Step 6: Update state

- Edit `.claude/progress.md`:
  - Move generated day from "next" to "complete."
  - Increment running totals (LeetCode problems, STAR stories, blogs).
  - Update "Last update" date and "Next to generate" line.

### Step 7: Report to user

Brief summary:
- Final line count.
- Section count and topics covered.
- Anything deferred (with reasons).
- Senior IC + Staff coverage assessment paragraphs.
- Target reading times for both tracks.

## Weekly notes — full procedure

### When to generate

After completing all 5 days of a week, optionally generate the week's
overview file. This is a **Staff-only** summary, NOT a re-hash of dailies.

### Step 1: Read inputs

- `.claude/progress.md` to confirm all 5 days are complete.
- `weekly-prompt.txt` for the template.
- The 5 day files to extract synthesis material.

### Step 2: Confirm WEEK-SPECIFIC INPUT

```
Week number:          N
Week title:           (verbatim from plan)
Source plan lines:    Days 5N-4 through 5N of faang-staff-prep-v4-28week.md
Output file:          w<N>/week<N>-notes.md
Day-type mix:         (e.g., "4 DSA-D + 1 Review-D")
Primary problems:     (list verbatim)
Primary theory:       (list verbatim)
Project tie-ins:      (per plan)
Prior-week callbacks: (concepts from earlier weeks reinforced)
```

### Step 3: Generate

- Follow `weekly-prompt.txt` structure.
- Staff-only audience (NOT dual-track like dailies).
- Target 900–1300 lines.

### Step 4: Verify and update progress

Same as daily steps 5–7.

## Re-generation / corrections

If the user requests changes to an existing day:

- Read the existing file with `Read`.
- Use `Edit` for targeted changes; do NOT regenerate from scratch unless
  the change is structural.
- After change, verify the section / tier-tagging still conforms to
  `.claude/conventions.md`.
- Update `.claude/progress.md` with a note about the change.

## Common asks and how to handle

| User asks | Do |
|---|---|
| "Generate Day N" | Steps 1–7 above. |
| "Generate Day N, just go" | Skip clarification (Step 3). Use defaults from plan + conventions. |
| "Generate Week N overview" | Weekly notes procedure. Confirm all 5 days exist first. |
| "Adjust Day N's <section>" | Read + Edit. Don't regenerate whole file. |
| "What's next?" | Read `.claude/progress.md`; report "Next to generate" line. |
| "Show me Day N" | Read the file. |
| "Re-do the example files" | Reject — they're the benchmark. Only regenerate the w<N>/dayN-notes.md copies. |

## Anti-patterns (avoid)

- Generating without reading the plan's Day-N section first.
- Skipping clarification questions when day type is novel (e.g., first HLD-D, first JSD-D, first Auth-D).
- Generating multiple days in one batch without user confirmation per day.
- Compressing depth to "save tokens" — the user has explicitly stated no length cap.
- Re-using a template wholesale across days — each day's content must be unique.
- Deleting or renaming the example files.
- Skipping the `.claude/progress.md` update.

## Cross-session continuity

Future sessions should:

1. Read `.claude/CLAUDE.md` first (auto-loaded by harness).
2. Read `.claude/progress.md` to see state.
3. Continue from "Next to generate" line.

If state is ambiguous, ask the user before proceeding.