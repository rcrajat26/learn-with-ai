# 21 AI for Coding — script or prompt: the central judgment — INTERMEDIATE (§2.8.1–2.8.5)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the review skills and the interface](../practices/03-review-skills-and-interface.md) · Next: [idempotence and human authority](02-cases-idempotence.md)

## 1. The rule, and where it sits above the mechanism table

**Mental model.** Every other file in this topic answers "given that a model is involved, which
mechanism carries the instruction" — `CLAUDE.md`, a path-scoped rule, a skill, a hook, a subagent, a
plugin. §1.5.26's decision table (D-41, `skills/06-builtins-and-decision-table.md`) is that
mechanism-selection procedure, and it is drawn as a decision tree with its own root question. This
file is the layer above it: before asking *which* mechanism carries the instruction, ask whether a
model should carry it at all. Get this judgment wrong and the mechanism choice below it is moot — a
perfectly-scoped hook that shells out to a `claude -p` call is still a model call paying model costs
for a job that had one correct answer.

**Why it exists.** A coding agent can be asked to do almost anything phrased as English, and it will
usually produce *something* — fluent, confident, syntactically plausible. That capability is exactly
what makes the judgment necessary: the model's willingness to attempt a task is no evidence that a
model is the right tool for it. §0.1 already established that fluency and confidence are not
correctness signals in the model the way they are in a person (`ground-zero/01-basics-what-the-model-is.md`);
this file turns that fact into an engineering rule applied *before* the call is ever made, not a
recovery applied after it goes wrong.

**The rule, stated once and referenced forever:** if the inputs determine one correct answer, write
a script; if the task needs judgment, write a prompt. `[CASE]` "Correct answer" here means
determined by the inputs alone, with no synthesis step — the same inputs, run through the same
transform, produce the same output every time, and a human could write down the algorithm without
having to describe taste, priority, or interpretation.

![D-65 — Script or prompt. The root question is whether the inputs determine one correct answer.](../diagrams/D-65-script-or-prompt-decision-tree.svg)

**D-65** — Script or prompt. The root question is whether the inputs determine one correct answer.

## 2. The source of the rule, verbatim from the harness

`[CASE]` The rule is not house style invented for this guide — it is the design property the
sdlc-harness plugin's own `bootstrap` skill states about itself, at
`plugins/sdlc-harness/skills/bootstrap/SKILL.md`. The full "why deterministic scripts and not model
judgment" paragraph is already quoted and worked through in `skills/05-cases.md` §1.5.20 (the
`bootstrap`-as-orchestrator case study); this file does not re-quote the whole paragraph, only the
one sentence the rule in §1 rests on, verbatim:

```
resolving paths, merging JSON, and creating symlinks all have a single correct
answer given the inputs — there is no ambiguity for a model to resolve.
```

Each of those three examples earns its place because it names a category, not one script: "resolving
paths" covers every step in `bootstrap` that decides where `HARNESS_ROOT` lives or whether a clone
already exists at a candidate location; "merging JSON" covers `bootstrap-user-scope.sh` writing the
fail-closed prod-AWS deny-list into `~/.claude/settings.json` without clobbering keys already there;
"creating symlinks" covers `bootstrap-link-service.sh` wiring a service directory into the workspace
scaffold. None of the three has a second defensible answer once the inputs — the existing filesystem
state, the existing JSON, the target paths — are fixed.

`[CASE]` The consequence lives one paragraph earlier in the same file, also quoted verbatim:

```
This is an **orchestrator, not a rewrite** — each step below detects state and
delegates to a small deterministic script bundled with the plugin
(`${CLAUDE_PLUGIN_ROOT}/scripts/`). Do not reimplement any of this logic inline;
call the scripts exactly as written, so the decision logic lives in one tested
place, not duplicated across every session that runs this skill.
```

Read as a design property rather than a style note, this sentence is doing two jobs at once. First,
it names what `bootstrap/SKILL.md`'s body actually is: a table of contents — fourteen numbered
steps, each naming a script under `plugins/sdlc-harness/scripts/` (`bootstrap-uv.sh`,
`bootstrap-user-scope.sh`, `bootstrap-lsp.sh`, `bootstrap-write-version.sh`, and eleven more,
confirmed on disk) — not an implementation the model re-derives. Second, it forbids the one failure
mode a skill body invites: an assistant reading "merge the deny-list JSON" as an instruction to
write out the merge logic itself, inline, in that turn. Without the explicit "do not reimplement...
call the scripts exactly as written," a skill author gets a plausible-looking merge every run and a
byte-identical one on none of them — the deny-list is a fail-closed security control (§1.5.20), so
"plausible" is exactly the property that must not be tolerated there.

**What would break without it:** each of `bootstrap`'s fourteen steps is idempotent only because the
underlying script is idempotent and tested once. If the skill instead told the model "merge this
deny-list into the user's settings, preserving existing keys," every invocation would re-derive the
merge from scratch. Two sessions on two machines could disagree about whether an existing key
survives a re-run, and the disagreement would not surface as an error — it would surface as a
silently different deny-list, which is precisely the class of bug a security control cannot have.

## 3. The decision table beyond the first branch

The root question sorts a task into script or prompt. Once it lands on the prompt side, three
further branches (still `[NUM]`, because each is a discrete, enumerable category rather than a
sliding scale) decide which *kind* of prompt-carrying mechanism fits, and this is where D-65 and
D-41 connect: D-65's "prompt" leaf is the entry point into D-41's whole tree.

| Question | Answer | Mechanism | Reference |
|---|---|---|---|
| Do the inputs determine one correct answer? | Yes | Shell script | this file, D-65 |
| Do the inputs determine one correct answer? | No — needs judgment or synthesis | Prompt | this file, D-65 |
| Must this run every time, with zero drift allowed? | Yes | Hook | §1.5.26, D-41 |
| Is the input verbose and the needed output small? | Yes | Subagent (isolates the verbose context) | §1.5.26, D-41 |
| Does the action need human authority before it proceeds? | Yes | Confirmation gate, with the tool denied by default until approved | §1.5.26, D-41 |

The first row is this file's whole subject; the last three are D-41's territory and are named here
only to show the seam — this file does not redraw or re-argue D-41's tree. A must-happen-every-time
requirement (row 3) is itself a symptom that the underlying decision was already "one correct
answer, enforced," which is why hooks are shell scripts wired to lifecycle events rather than
prompts wired to them: a hook that phrased its blocking rule as "please refuse to commit if tests are
red" would be re-litigating a decision that has no second correct answer, on every commit, at model
cost and with model variance.

## 4. Why "the model could do it" is not an argument

`[PROVE]` The claim that has to be killed, not merely dismissed: a model can, mechanically, resolve
a path, merge two JSON objects, or create a symlink if asked in a prompt. That is true, and it is not
an argument for doing it that way. Three independent reasons hold, and each has already been
established elsewhere in this topic with a number or a mechanism behind it — this section is where
they meet the decision.

**Reason 1 — cost.** A script that shells out costs the CPU cycles to run `jq` or `ln`, which is
effectively free and does not touch the model's context window or its per-token bill. A prompt that
asks the model to perform the same merge pays for every token of the JSON going in and every token
of the merged result coming out, on *every single invocation*, forever — there is no amortization,
because there is no artifact to cache the result against. §2.6's cost ranking
(`context-economy/01-measuring-and-ranking.md`, D-62) already ranks avoidable context cost by size;
a model call standing in for a deterministic transform is exactly the "avoidable" category, because
the same bytes cross the wire on every run for a transform that a script computes once, correctly,
for zero marginal tokens.

**Reason 2 — variance.** §0.1 already worked through why the model is not `square(x)`
(`ground-zero/01-basics-what-the-model-is.md`): next-token sampling draws from a probability
distribution, and even at `temperature = 0` two runs of a large model are not guaranteed
bit-identical, because the arithmetic is spread across many processors and floating-point summation
order is not perfectly reproducible at that scale. Feed the same two JSON files to a prompt twice
and the merged result can differ in ways that are individually too small to notice and collectively
enough to break a downstream `diff`-based check. A shell script computing the same merge with `jq`
has no sampling step in it at all — `jq . a.json b.json` run twice on the same two files produces
byte-identical output, because there is no probability distribution anywhere in the call stack.

**Reason 3 — testability.** §2.7.3 (`practices/01-plan-mode-and-test-first.md`) already established
that a failing test is a machine-checkable specification — the property that catches a confabulating
model before its output ships. A script inherits that property directly: `bootstrap-user-scope.sh`
can be unit-tested by running it against a fixture settings file and asserting the merged JSON is
exactly what is expected, and that test either passes or fails, permanently, with no distribution of
outcomes to worry about. A prompt cannot be tested that way. Asserting exact string equality against
a model's output is the fragile-test anti-pattern §0.1 already named — the model may produce a
functionally equivalent but textually different JSON body on the next run, failing a brittle test
for no real defect, or it may drift on some low-probability run into a genuinely wrong merge that a
loose "looks reasonable" check would let through. There is no test posture that is both robust and
tight against a prompt's output the way there is against a script's, because the prompt's output is
not drawn from a distribution of one.

**Arithmetic, made concrete.** Take the deny-list merge in `bootstrap-user-scope.sh`, run once per
onboarding session across, say, 40 engineers a quarter re-bootstrapping after a laptop reimage. As a
script: 40 runs × (near-zero CPU cost, one deterministic test suite written once) = a fixed, sunk
cost that does not grow with usage. As a prompt: 40 runs × (the input JSON's token count + the
merged JSON's token count, on every run, at whatever the active model's per-token rate is that
month) = a cost that scales linearly with usage forever, on top of a non-zero chance, per run, that
the merge silently drops or duplicates a key because the model's judgment about "preserve existing
keys" landed on a different interpretation than the run before it. The script's cost curve is flat;
the prompt's is not, and its output is not even guaranteed correct in exchange for paying it.

**Insight:** the three reasons are not independent complaints about the same symptom — they compound.
A cost you pay repeatedly (reason 1) for an answer that is not guaranteed identical between runs
(reason 2) and that you cannot pin down with a test (reason 3) is a worse trade than any one of the
three read alone would suggest, because the lack of testability (3) is precisely what stops the
variance (2) from being caught before it costs something (1) in production.

## 5. Worked examples on both sides of the line

**Script side — each has exactly one correct answer given its inputs:**

- **Resolving a repository root.** Given a starting directory, walk parent directories until a
  `.git` is found; there is exactly one nearest ancestor containing `.git`, so this is a fixed-point
  computation, not a judgment call.

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  resolve_repo_root() {
      local dir="${1:-$PWD}"
      while [[ "$dir" != "/" ]]; do
          if [[ -d "$dir/.git" ]]; then
              printf '%s\n' "$dir"
              return 0
          fi
          dir="$(dirname "$dir")"
      done
      echo "resolve-repo-root: no .git found above $1" >&2
      return 1
  }

  resolve_repo_root "$@"
  ```

- **Merging two JSON settings files.** `deep-merge-settings.sh`, keeping the second file's keys as
  the override on conflict — a specified, total-order rule, so `jq` computes it exactly once:

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  base="$1"
  override="$2"

  jq -s '.[0] * .[1]' "$base" "$override"
  ```

- **Creating a symlink.** `link-service.sh` — given a source path and a target name, either the
  symlink already points at the source (no-op, idempotent) or it does not (create or replace it);
  there is no third outcome:

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  src="$1"
  target="$2"

  if [[ -L "$target" && "$(readlink "$target")" == "$src" ]]; then
      exit 0
  fi
  ln -sfn "$src" "$target"
  ```

- **Bumping a version string.** Given a semantic version and a bump kind (`major` / `minor` /
  `patch`), the next version is arithmetic, not interpretation:

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  bump-version.sh() {
      local version="$1" kind="$2"
      IFS='.' read -r major minor patch <<< "$version"
      case "$kind" in
          major) printf '%d.0.0\n' "$((major + 1))" ;;
          minor) printf '%d.%d.0\n' "$major" "$((minor + 1))" ;;
          patch) printf '%d.%d.%d\n' "$major" "$minor" "$((patch + 1))" ;;
          *) echo "bump-version: unknown kind $kind" >&2; exit 1 ;;
      esac
  }

  bump-version.sh "$@"
  ```

**Prompt side — the task needs judgment or synthesis, and no fixed algorithm produces the answer:**

- **Summarising why a test fails.** The stack trace and the assertion diff are inputs, but "why" is
  an explanation constructed from domain knowledge about what the test was trying to establish — two
  competent engineers can write defensibly different summaries of the same failure, which is the
  signature of a judgment task.

- **Deciding whether an API change is breaking.** Whether removing an optional field breaks a
  consumer depends on what consumers actually rely on, which is not recoverable from the diff alone
  — it requires reasoning about intent and usage, not a deterministic transform of the diff's text.

- **Writing a migration plan.** Ordering steps, deciding what needs a feature flag, deciding where a
  rollback boundary goes — these are synthesis over constraints with more than one defensible
  ordering, which is exactly what "judgment" means in the rule from §1.

**The hard case, reasoned through rather than asserted: "does this commit message follow the team's
format?"** At first glance this looks script-shaped — there is a stated format, so surely a regex
checks it. Work it through instead of asserting an answer. If the rule is purely syntactic
(`^(feat|fix|chore): .{1,72}$`), it is genuinely one correct answer per input string, and belongs on
the script side — a hook can enforce it on `commit-msg`, and it would be wasteful and non-reproducible
to spend a model call and accept sampling variance on a regex match. But most real commit-message
review is not purely syntactic: "does the summary line accurately describe what changed" requires
comparing the stated summary against the actual diff, which is exactly the synthesis category from
§1 — there is no fixed transform from a diff to "is this description accurate," because accuracy is
a judgment about correspondence between two different representations of the same change, not a
string match. The resolution is not "pick one side" but "split the check": the format regex is a
script (a hook, per §1.5.26 / D-41's must-happen branch), and the *accuracy* check, if it happens at
all, is a prompt — most likely deployed as a subagent given the diff and the message and asked to
flag a mismatch, per D-41's verbose-in/small-out branch, rather than inline in the main loop. The
lesson the hard case teaches: a single English-sounding requirement can straddle the line, and the
fix is to decompose it at the seam rather than force the whole requirement onto one side.

## Pitfalls

**Pitfall:** believing "the model got the right answer when I tried it" settles the question of
whether a task belongs on the prompt side. Symptom: a script-shaped task — resolving a path, merging
JSON — gets implemented as a prompt because it worked in the one manual test the author ran, and then
drifts on a run with slightly different input formatting six weeks later, in production, with no
test that would have caught it. Fix: apply the root question from §1 — do the inputs determine one
correct answer — before ever running the task once, not after observing that one run went well.
**Why people believe it:** the model's fluency makes a correct-looking answer indistinguishable from
a guaranteed-correct one in a single observation; only running it many times, or reasoning about the
input space rather than one instance of it, reveals the difference.

**Pitfall:** treating "the model could technically do this" as evidence for using the model.
Symptom: a `bootstrap`-style onboarding skill re-derives its JSON merge inline in the assistant's own
reasoning instead of calling `bootstrap-user-scope.sh`, and two engineers running the identical
onboarding flow end up with subtly different `~/.claude/settings.json` deny-lists. Fix: apply §4's
three reasons explicitly — cost it, name the variance risk, and ask whether a test could pin the
answer down — rather than stopping at "it can do it." **Why people believe it:** capability and
suitability look identical from the outside until the cost and variance are actually measured;
"can" answers a different question than "should."

## Cheat sheet

| Signal | Verdict | Mechanism |
|---|---|---|
| Inputs alone determine one correct answer | Script | Shell script (`jq`, `ln`, arithmetic) |
| Task requires judgment, synthesis, or interpretation | Prompt | Model call |
| Must run every time with zero drift | (downstream of script) | Hook |
| Verbose input, small needed output | (downstream of prompt) | Subagent |
| Needs human authority before proceeding | (downstream of prompt) | Confirmation gate, tool denied by default |
| "The model could do it" | Not an argument | Cost it (§2.6), name the variance (§0.1), ask if a test could pin it (§2.7.3) |

## Self-test

1. What is the root question D-65 asks before any mechanism is chosen?
<details><summary>Answer</summary>Do the inputs determine one correct answer? If yes, a shell script; if no — the task needs judgment or synthesis — a prompt.</details>

2. Quote the exact sentence from `bootstrap/SKILL.md` that gives the source of the rule, and name the three examples it uses.
<details><summary>Answer</summary>"resolving paths, merging JSON, and creating symlinks all have a single correct answer given the inputs — there is no ambiguity for a model to resolve." The three examples are resolving paths, merging JSON, and creating symlinks.</details>

3. Why is "the model could do it" not an argument for using a prompt? Name all three reasons.
<details><summary>Answer</summary>Cost — a prompt pays token cost on every invocation with no amortization, where a script is near-free. Variance — the model samples from a probability distribution and is not guaranteed to produce the same output twice, even at temperature 0. Testability — a script's output can be pinned with an exact-equality test; a prompt's output cannot be tested that tightly because it is not drawn from a distribution of one.</details>

4. How does this file relate to the §1.5.26 / D-41 decision table?
<details><summary>Answer</summary>D-41 answers "given that a model is involved, which mechanism carries the instruction" (CLAUDE.md, rule, skill, hook, subagent, plugin). This file answers the question one layer above that: whether a model should be involved at all. D-65's "prompt" leaf is the entry point into D-41's tree.</details>

5. Is resolving a repository root a script task or a prompt task, and why?
<details><summary>Answer</summary>Script — given a starting directory, there is exactly one nearest ancestor directory containing `.git`, so it is a deterministic walk with one correct answer, not a judgment call.</details>

6. In the hard case — checking a commit message against a team's format — why can't the whole requirement be assigned to one side of the line?
<details><summary>Answer</summary>It bundles two different checks: a purely syntactic format check (one correct answer per input string — script, enforced as a hook) and a semantic accuracy check (does the summary actually describe the diff — judgment, no fixed transform — prompt, likely a subagent). The fix is to decompose the requirement at the seam rather than force it entirely onto one side.</details>

7. What would break in `bootstrap` if the deny-list merge were re-derived inline by the model on every run instead of delegated to `bootstrap-user-scope.sh`?
<details><summary>Answer</summary>Each run could produce a subtly different merged JSON — a key silently dropped or handled differently — with no error raised, because there is no test catching a difference in a plausible-looking merge. Since the deny-list is a fail-closed security control, a silently different deny-list per session is exactly the failure mode that must not be tolerated.</details>

8. State the flat-vs-scaling cost argument from §4's arithmetic example.
<details><summary>Answer</summary>A script's cost is a fixed, sunk cost (near-zero CPU per run plus a test suite written once) that does not grow with usage. A prompt's cost scales linearly with usage forever — every run pays for the input and output tokens again — and is not even guaranteed to produce a correct result in exchange for that recurring cost.</details>

## Open questions

None.

---

**Leaves covered:** 2.8.1–2.8.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-65
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 344
