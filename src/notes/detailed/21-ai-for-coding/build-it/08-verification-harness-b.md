# 21 AI for Coding — re-running the listings, and where each gate belongs — BUILD IT (§4.7.3–4.7.4)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [a verification harness](08-verification-harness-a.md) · Next: [PART 4 — the interview wrap-up](../93-interview-build-it.md)

`08-verification-harness-a.md` built and ran `verify.sh`'s two gates — text-ness, then the
structural checks — under `/tmp/21-verify-harness-demo`, with real timings 0.32s / 0.10s / 0.06s and
zero tokens per run, and it closed by naming a gate 3 (re-running every fenced listing against its
own printed output) as this file's job, alongside the `Stop`-hook/CI split. Re-checking this file's
own sealed leaf definitions against `tmp/21-contract/leaves/b4-16.md` — the verbatim source the
standing contract makes authoritative over any other description of scope — turns up two different
obligations for §4.7.3–4.7.4: **wire the harness as a `Stop` hook and a CI job, stating which
failures belong in which** (§4.7.3), and **a skill eval: three prompts that should trigger a skill
and three that should not, run and scored for real** (§4.7.4). No fenced-listing gate 3 is one of
this file's two leaves. Per the leaf-file-wins rule, what follows is what the leaf file asks for; the
fenced-listing check the previous file and D-99's caption anticipated is not built here, and this
paragraph is the record of that divergence.

## §4.7.3 — Wiring `verify.sh`: the same two gates, a `Stop` hook, and a CI job `[BUILD]`

**Concept.** A gate that only ever runs when someone remembers to run it by hand is not a guarantee,
it is a suggestion with good intentions. `verify.sh` as built in the previous file is a script sitting
on disk; wiring it means picking the harness event and the CI trigger that actually invoke it, without
inventing a third, heavier gate to justify the file.

**Why it exists.** `verification/03-internals-c-automation-and-review-capacity.md`'s §3.10.9 already
established the general moment-pricing rule — `PostToolUse` for per-edit checks, `Stop` for a fast
per-turn check, CI for anything that needs real wall-clock time — and used a **four-minute build**
wired to `Stop` as the cautionary case: a guarantee that gets disabled within the week because nobody
tolerates that wait on every message. `verify.sh`'s own two gates are the opposite case: **0.32s / 0.10s
/ 0.06s** measured in the previous file, and **zero tokens**, because neither gate calls the model.
That earlier leaf never had to ask "is this gate cheap enough for `Stop`" for a check this fast — the
question this leaf actually has to answer is different: **if both gates are cheap enough for `Stop`,
what is CI's job at all?**

**How it works, and the actual split.** The wall-clock argument from §3.10.9 does not split gate 1 from
gate 2 — both together run in well under half a second regardless of which files changed, so pricing
is not what separates them. **Coverage is.** A `Stop` hook fires only inside the interactive session
that produced the edit — it never sees a commit made outside a Claude Code session, a direct push, a
squashed merge, or a contributor who has hooks disabled locally. CI fires on every push regardless of
where it came from. The split is therefore not "cheap gate here, slow gate there" — it is **the same
two gates, run twice, for two different populations of change**:

| Where | Trigger | What it catches | What it cannot catch |
|---|---|---|---|
| `Stop` hook | Every turn end, inside a live Claude Code session | Drift the instant it is written, while the session's own context is still loaded and a fix costs one more turn | Any file touched outside that session — a hotfix, a rebase, a colleague's local edit with hooks off |
| CI job | Every push, regardless of origin | Everything `Stop` cannot: the file that never went through a hook-wired session at all | Nothing gate 1/gate 2 already miss — CI runs the identical script, not a heavier one |

That is the cost argument this leaf actually has: **it is not a price argument, it is a coverage
argument.** `Stop` is cheap enough here that skipping it would waste a guarantee that costs nothing;
CI is not redundant with `Stop` because CI is the only one of the two that also runs over changes
`Stop` never had a chance to see. The diagram this split reuses is **D-99**, already embedded in the
previous file at §4.7's opening — its gate order (text-ness before structural checks) is the object
being placed into `Stop` and CI here, so it is referenced by id rather than re-drawn.

**Code — the `Stop` hook.** `verify-on-stop.sh`, reading the real `Stop` event JSON `hooks` documents
(`cwd`, `hook_event_name`, `stop_hook_active`) and reporting through the top-level `decision`/`reason`
channel — quoted verbatim from the raw `hooks.md` page (`curl -sL
https://code.claude.com/docs/en/hooks.md`, verified 2026-08-30): "`decision` — `\"block\"` prevents
Claude from stopping. Omit to allow Claude to stop." / "`reason` — Required when `decision` is
`\"block\"`." `build-it/02-three-hooks-b.md` re-verified this against the raw page and corrected this
note set's own two earlier wrong drafts against it — `decision: "block"` reopens the turn, `reason` is
what the model reads next; there is no `continueReason` field anywhere in the schema, and the universal
`continue` boolean is an unrelated kill switch (`false` stops Claude entirely — the opposite of a
continuation signal), never used here:

```bash
#!/usr/bin/env bash
# Stop hook for this note set: refuse to let a turn end while verify.sh's
# fast gates (text-ness + structural checks) are red over the topic's own
# Markdown files.
#
# Deliberate failure posture: set +e, always exit 0. The decision channel
# is the printed JSON's "decision"/"reason" fields alone -- never the exit
# code -- because `hooks` documents exit code 2 as a SECOND, independent
# path that can also block a Stop; keeping to one channel means there is
# exactly one place that decides and exactly one place to read why.
set +e

input="$(cat)"
target_dir="$(printf '%s' "$input" | jq -r '.cwd')/src/notes/detailed/21-ai-for-coding"

output="$("${CLAUDE_PROJECT_DIR:-.}/tools/verify.sh" "$target_dir" 2>&1)"
status=$?

if [ "$status" -ne 0 ]; then
  jq -n --arg reason "verify.sh failed for this turn's edits under $target_dir:
$output" '{
    decision: "block",
    reason: $reason
  }'
  exit 0
fi

exit 0
```

Registered in `.claude/settings.json` alongside this topic's other hooks, `verify.sh` itself living at
`tools/verify.sh` (a project-wide script, not something scoped to `.claude/`):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/verify-on-stop.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Code — the CI job.** The identical script, the identical target directory, run again on every push
so a change that never passed through a `Stop` hook still gets checked before merge:

```yaml
name: verify-notes
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run verify.sh against the topic 21 note set
        run: ./tools/verify.sh src/notes/detailed/21-ai-for-coding
```

**Prove step.** `[PROVE]` Two real runs of `verify-on-stop.sh` under `/tmp/21-verify-harness-demo`, a
fake `CLAUDE_PROJECT_DIR` whose `tools/verify.sh` is the unmodified script from the previous file. Run
1, a clean fixture — silent, nothing printed, the stop proceeds:

```
$ export CLAUDE_PROJECT_DIR=/tmp/21-verify-harness-demo/fake-project
$ cat stop-event.json | ./verify-on-stop.sh; echo "exit=$?"
exit=0
```

Run 2, the same fixture edited mid-turn — the footer and `## Open questions` not yet appended, exactly
the shape of a turn that ended before the note was finished:

```
$ cat stop-event.json | ./verify-on-stop.sh; echo "exit=$?"
{
  "decision": "block",
  "reason": "verify.sh failed for this turn's edits under /tmp/21-verify-harness-demo/fake-project/src/notes/detailed/21-ai-for-coding:\nFAIL: gate2-footer: '/tmp/21-verify-harness-demo/fake-project/src/notes/detailed/21-ai-for-coding/sample.md' missing required '**Leaves covered:**' footer line\nFAIL: gate2-open-questions: '/tmp/21-verify-harness-demo/fake-project/src/notes/detailed/21-ai-for-coding/sample.md' missing required '## Open questions' section\nverify.sh: 2 failure(s) across 1 file(s)"
}
exit=0
```

**What this costs.** The whole round trip — reading stdin, resolving `cwd`, shelling out to
`verify.sh`, building the `jq` response — measured **0.17s** wall clock on this machine, and, as with
the underlying gates, **zero tokens**: no `claude` invocation appears in `verify-on-stop.sh` itself.
The only tokens this gate ever spends are the ones the model reads back on failure — the `reason` string
re-entering context as ordinary text on the next turn, the same few-hundred-token cost
`verification/03-internals-c-automation-and-review-capacity.md` priced for the analogous compile gate.

**Gotcha.** **Pitfall:** assuming that because CI re-runs the same script, CI is redundant and can be
dropped once the `Stop` hook is wired. **Symptom:** a file edited outside any Claude Code session —
a teammate's direct commit, a rebase that reintroduces a stale footer — merges clean, because nothing
ever ran `verify.sh` against it; the `Stop` hook only fires inside sessions that have it registered.
**Fix:** keep both. `Stop` is not a faster substitute for CI here — both gates are already fast — it
is an *earlier* check for the population of edits CI would otherwise catch a push later, and CI is the
backstop for the population `Stop` structurally cannot see. **Why people believe it:** "the checks are
identical, so running them twice must be waste" reads as an efficiency argument until the actual
difference — which edits each one is even capable of observing — is stated explicitly.

## §4.7.4 — A skill eval: three prompts that should trigger it, three that should not `[BUILD]` `[PROVE]`

**Concept.** `04-two-subagents-a.md`, `03-a-skill-and-a-command-a.md`, and every other `[BUILD]` skill
in this part shipped an artefact and proved it runs once. A skill eval asks a different question: not
"does it work when invoked," but **"does the harness invoke it on the prompts it should, and stay
silent on the ones it shouldn't."** That is a property of the skill's `description` field, not of its
body, and the only way to check it is to actually send prompts through a real session and see what the
model decides.

**Why it exists.** `topics/16-testing.md` owns the pyramid, JUnit 5, and what coverage does and does
not tell a reader — but one idea from it is load-bearing here and belongs in full, not as a pointer
alone: **a failing test is a machine-checkable specification**, which is exactly what a confabulating
writer needs, established at §2.7.3. A skill's `description` is prose, and prose is exactly the kind
of artefact a fluent, ungrounded process can get plausibly wrong — a description that reads well to
the person who wrote it and still never matches the phrasing real users type. `§3.9.10` already applied
this idea to prompts as eval suites; a skill eval is the same idea applied to a skill's trigger
condition specifically: a small, fixed set of prompts with a known right answer, run for real, scored
against that answer rather than against how convincing the description sounds. For the pyramid this
sits inside and what a green suite does and does not prove beyond this one property, see
[`topics/16-testing.md`](../../../../topics/16-testing.md).

**How it works.** The subject is the real `checklist-refresh` skill this part already shipped in
`build-it/03-a-skill-and-a-command-a.md`, still installed at
`/tmp/21-skills-scratch/invoice-ledger-service/.claude/skills/checklist-refresh/SKILL.md`, description
unchanged: *"Refresh the pre-review checklist for a touched module in invoice-ledger-service before
opening a pull request... Use when the user asks to prep a PR, refresh the review checklist, or check
whether a module's changes are ready for review."* Six real `claude -p` calls, `--max-turns 1` so each
run stops at the model's *first* decision rather than paying for a full completion, from inside that
same scratch checkout so every other skill it ships (`post-invoice-reversal`, `mvn-verify-executor`,
`record-boundary-guard`, `release-candidate-check`, `money-minor-units-conventions`) is a real,
plausible distractor rather than an empty tool list. Scoring reads `--output-format json`'s
`permission_denials` array — a `Skill` entry there, even one the harness ultimately denies for lack of
an interactive approval channel, is proof the model *chose* to invoke it — and, for the one run with no
denial at all, the session's own transcript JSONL under `~/.claude/projects/`.

**Code — the six prompts and the real, scored result:**

| # | Prompt | Expected | What the model actually invoked | Correct? | Cost |
|---|---|---|---|---|---|
| P1 | "I'm about to open a PR for the invoice-ledger-api changes — can you refresh the pre-review checklist for that module?" | should trigger | `Skill(checklist-refresh, args="invoice-ledger-api")` | Yes | $0.1447 |
| P2 | "Check whether invoice-ledger-api is ready for review." | should trigger | `Skill(checklist-refresh, args="invoice-ledger-api")` | Yes | $0.0670 |
| P3 | "Prep the invoice-ledger-persistence module for a pull request." | should trigger | `Skill(checklist-refresh, args="invoice-ledger-persistence")` | Yes | $0.0671 |
| N1 | "Post a reversing ledger entry for invoice INV-4021." | should not trigger | No skill — plain `Bash(git status --short ...)` exploration | Yes | $0.0719 |
| N2 | "What's today's date?" | should not trigger | No skill — answered directly: "Today's date is 2026-08-30." | Yes | $0.0648 |
| N3 | "Run the full verification build for this service." | should not trigger | `Skill(mvn-verify-executor)` — a *different* skill, not `checklist-refresh` | Yes | $0.0690 |

`[PROVE]` The real command, unabridged:

```
$ cd /tmp/21-skills-scratch/invoice-ledger-service
$ claude -p "I'm about to open a PR for the invoice-ledger-api changes -- can you refresh the pre-review checklist for that module?" --output-format json --max-turns 1
```

and the field that decides P1's score, taken directly from that run's JSON:

```
$ cat eval-p1.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['permission_denials'])"
[{'tool_name': 'Skill', 'tool_use_id': 'toolu_01EGdZmFonr9jMYnEJu2Hv33', 'tool_input': {'skill': 'checklist-refresh', 'args': 'invoice-ledger-api'}}]
```

For N1, the same field comes back `[]` — no `Skill` tool use of any kind was attempted — so scoring
falls back to the session's own transcript, read straight from disk rather than re-asked of the model:

```
$ python3 -c "
import json
for line in open('/Users/rajat.chikkodikar/.claude/projects/-private-tmp-21-skills-scratch-invoice-ledger-service/61496005-a5e2-457c-8d6f-d943d61e453f.jsonl'):
    d = json.loads(line)
    for c in d.get('message', {}).get('content', []) if isinstance(d.get('message', {}).get('content'), list) else []:
        if c.get('type') == 'tool_use':
            print(c.get('name'), c.get('input'))
"
Bash {'command': 'git status --short && find . -path ./.git -prune -o -type f -print | head -50'}
Bash {'command': 'cat invoice-ledger-api/src/main/java/ReversalRequest.java invoice-ledger-api/src/main/java/Dummy.java 2>/dev/null'}
```

**Score: 6/6.** Three prompts that should have triggered `checklist-refresh` did; three that should
not have, did not — one of the three negatives triggered a *different* skill correctly, which is the
harder and more informative negative case, because it shows the model discriminating between two real
skills rather than merely staying silent.

**What this costs.** **$0.4844** total across the six runs, **$0.0807** average — real API spend, not
an estimate, because a skill eval has no cheaper substitute: the thing under test is a live decision
the model makes over its own tool list, and the only way to observe that decision is to actually run
the model. Every run used `--max-turns 1`, which is the entire cost-control lever available here: it
stops the session at the first tool-use attempt rather than paying for the skill's own body to execute,
so the eval prices the *decision* alone, not the full task. For comparison, `verify.sh` and its `Stop`
wrapper price out at **$0** per run — the gap between $0 and roughly $0.08 per prompt is exactly the
gap §4.7.3's coverage argument implicitly assumed: a check that can be reduced to a string match should
be, because the moment a check requires a live model decision, it stops being free at any scale.

**Gotcha.** **Pitfall:** treating a skill's `description` as validated once it reads clearly to the
person who wrote it. **Symptom:** a description that never gets exercised against a real negative
prompt drifts into over-triggering (firing on N1- or N3-shaped requests it was never meant to own) or
under-triggering (missing a P2-shaped rephrasing) without anyone noticing until a user complains.
**Fix:** run the six-prompt shape above — three positive, three negative, at least one negative that is
a plausible near-miss another real skill should own — every time a skill's `description` changes, the
same discipline §2.7.3 demands of a failing test. **Why people believe it:** a description that reads
right in isolation feels validated by the act of writing it clearly, but clarity to the author and
matching behavior in the harness are two different properties, and only one of them is machine-checked
by running the prompts for real.

## Pitfalls

- **Belief:** because both of `verify.sh`'s gates are already fast, CI is redundant once a `Stop` hook
  is wired. **Surprising outcome:** an edit made outside any Claude Code session — a teammate's direct
  commit, a rebase, hooks disabled locally — merges with a stale footer or a missing `## Open
  questions` section, because the `Stop` hook never saw it; nothing about hook speed changes which
  edits a hook is even positioned to observe. **What actually gets the guarantee:** run the identical
  script in both places — `Stop` for the fast, in-session catch, CI as the backstop for everything that
  never passed through a session at all. **Why people believe it:** "same checks, ran twice" reads as
  duplication until the actual difference between the two triggers' *coverage* is stated explicitly.
- **Belief:** a skill's `description` is validated once it reads clearly and specifically to the
  engineer who wrote it. **Surprising outcome:** three real, distinct near-miss prompts (a reversal
  request, a date question, a build request) are exactly the shapes a loosely-worded description can
  accidentally capture or a well-worded one can still miss on a rephrasing — and nobody finds out until
  a live prompt exercises it. **What actually gets the guarantee:** three prompts that should trigger
  it, three that should not, run for real through `claude -p --max-turns 1` and scored against
  `permission_denials` or the session transcript, exactly as done above. **Why people believe it:**
  writing a precise-sounding description feels like the same work as testing it, but only one of the
  two is machine-checked.

## Cheat sheet

| Item | Value |
|---|---|
| §4.7.3 split | Not price — both gates already sub-second. **Coverage**: `Stop` sees only in-session edits, CI sees every push |
| `Stop` hook script | `verify-on-stop.sh`: reads `cwd` from the event JSON, shells to `tools/verify.sh`, reports via top-level `decision`/`reason` only |
| `Stop` decision fields | `decision: "block"` reopens the turn (omit to allow the stop); `reason` (required with `decision: "block"`) is what the model reads next — never `continueReason`, which does not exist |
| CI job | `.github/workflows/verify-notes.yml`, identical `tools/verify.sh` invocation, on every push/PR |
| `Stop`-wrapper prove | Clean fixture: silent, exit 0. Broken fixture (missing footer + Open questions): `decision: "block"` JSON printed, exit 0 |
| `Stop`-wrapper cost | 0.17s wall clock, $0 — no `claude` invocation inside the hook itself |
| §4.7.4 subject | Real skill `checklist-refresh` from `build-it/03-a-skill-and-a-command-a.md`, real scratch checkout `/tmp/21-skills-scratch/invoice-ledger-service` |
| §4.7.4 method | 6 × `claude -p "<prompt>" --output-format json --max-turns 1`; score from `permission_denials` or the session transcript |
| §4.7.4 result | 6/6 correct: 3/3 positive triggered `checklist-refresh`; 3/3 negative did not (one triggered a different real skill instead) |
| §4.7.4 cost | $0.4844 total, $0.0807 average per prompt — real spend, no cheaper substitute for a live trigger decision |
| Testing tie-in | A failing test is a machine-checkable specification (§2.7.3); a skill eval is the same idea applied to a `description` field (§3.9.10, full treatment in `topics/16-testing.md`) |

## Self-test

**Q1.** Both of `verify.sh`'s gates run in well under a second. Given that, what is CI's job, and why isn't it redundant with the `Stop` hook?

<details><summary>Answer</summary>

CI is not there because the gates are slow — they aren't. It exists because a `Stop` hook only fires inside the interactive Claude Code session that produced an edit; it never sees a commit made outside that session (a direct push, a rebase, a teammate with hooks disabled). CI runs on every push regardless of origin, so it is the only one of the two checks that also covers changes `Stop` structurally cannot observe. Both places run the identical script — the split is about coverage of *which edits get checked*, not about price.

</details>

**Q2.** What two fields does `verify-on-stop.sh` use to signal a failure back to the model, and what does each contain?

<details><summary>Answer</summary>

`decision`, a top-level field set to `"block"`, which reopens the turn instead of letting it end; and `reason`, a string containing `verify.sh`'s own failure output, required whenever `decision` is `"block"` and read by the model on the next turn. This matches the correction `build-it/02-three-hooks-b.md` made against this note set's own two earlier, incorrect drafts — one that used `continue: false`/`stopReason`, another that used `continue: true`/`continueReason` — neither of which is a real field in the verified schema; the universal `continue` boolean is an unrelated kill switch, never the `Stop`-specific decision channel.

</details>

**Q3.** Why does `verify-on-stop.sh` use `set +e` and always `exit 0`, rather than exiting non-zero on a `verify.sh` failure?

<details><summary>Answer</summary>

`hooks` documents exit code 2 on `Stop` as a second, independent channel that can also block a stop, alongside the JSON `decision`/`reason` fields. Using both at once would create two separate decision paths with two separate reason texts, one of which would be silently discarded. Keeping to exit 0 and the JSON `decision`/`reason` fields means there is exactly one place that decides whether the turn continues, and exactly one place a reader can look to find out why.

</details>

**Q4.** In the skill eval, why does `--max-turns 1` matter for cost, and what does the eval actually price as a result?

<details><summary>Answer</summary>

`--max-turns 1` stops the session immediately after the model's first tool-use attempt, before the invoked skill's own body (its checklist read, its file loads) ever runs. That means each run's cost is the cost of the model's *triggering decision* alone, not the cost of completing the skill's task — which is the only thing a trigger eval needs to measure, and it keeps six real runs affordable ($0.4844 total) rather than paying for six full task completions.

</details>

**Q5.** How was N1 ("post a reversing ledger entry") scored as a correct negative, given that its JSON `permission_denials` array came back empty?

<details><summary>Answer</summary>

An empty `permission_denials` only means no tool call was *denied* — it does not by itself prove no `Skill` call was attempted and approved. Scoring N1 required reading the session's own transcript JSONL directly from `~/.claude/projects/.../<session_id>.jsonl` and checking every `tool_use` block by name: the transcript showed two plain `Bash` calls (`git status`, then reading two files) and no `Skill` invocation at all, confirming `checklist-refresh` correctly did not fire.

</details>

**Q6.** Why is N3 ("run the full verification build") a stronger negative test than N2 ("what's today's date")?

<details><summary>Answer</summary>

N2 has no skill anywhere in the installed set that plausibly matches it, so a correct non-trigger proves little beyond "the model didn't fire a skill at random." N3 sits close enough to the domain that a real, different skill (`mvn-verify-executor`) does fire — which means the model had to discriminate between two genuinely similar-sounding requests ("run a build" vs. "refresh a pre-review checklist") rather than simply staying silent. Correctly routing to the right skill is a harder and more informative pass than correctly doing nothing.

</details>

**Q7.** What is the one testing idea this file borrows from `topics/16-testing.md`, and how does a skill eval apply it?

<details><summary>Answer</summary>

That a failing test is a machine-checkable specification (§2.7.3) — the same shape §3.9.10 already applied to eval suites for prompts generally. A skill eval applies it to one specific field, a skill's `description`: instead of trusting that the description reads clearly to the person who wrote it, a fixed set of prompts with a known right answer is run for real and scored, exactly the way a unit test replaces "I read the code and it looks right" with an executable check.

</details>

**Q8.** What would it mean, concretely, if P3 ("prep the invoice-ledger-persistence module") had instead triggered `checklist-refresh` with `args: "invoice-ledger-api"`?

<details><summary>Answer</summary>

It would be a scored failure even though a `Skill` call to `checklist-refresh` did occur — the eval is not just "did the right skill fire" but "did it fire with the right argument," since `$ARGUMENTS` in the skill's own body is what scopes the diff check to one module. A `checklist-refresh` call with the wrong module name would refresh the wrong checklist silently, which is exactly the kind of pass-shaped failure a coarser eval (checking only "was `Skill` ever called") would miss.

</details>

## Open questions

None.

---

**Leaves covered:** 4.7.3–4.7.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-99 in the previous file draws the full gate order and both terminals
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 391
