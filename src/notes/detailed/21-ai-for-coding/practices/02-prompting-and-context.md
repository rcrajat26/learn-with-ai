# 21 AI for Coding — prompting and giving the agent what it needs — INTERMEDIATE (§2.7.5–2.7.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [plan mode, test-first and small tasks](01-plan-mode-and-test-first.md) · Next: [review skills and the interface](03-review-skills-and-interface.md)

The previous file covered *when* you let the agent commit to an approach (plan mode), *what counts
as done* when the thing writing the code cannot be trusted to grade itself (test-first), and *how
big* a unit of work should be before you hand it over (small diffs plus worktree isolation). This
file is narrower and easier to get wrong in the opposite direction: it is about the words you
actually type, and the discipline you apply once the agent says it is finished. Both are graded
against the same yardstick used everywhere else in this guide — not "does this feel like good
practice," but "what fact about the model does this practice exploit, and would it still work if
that fact stopped being true."

That yardstick rules a lot out. Most lists of "prompting tips" on the internet are folklore:
practices that were never tested against a mechanism, that got repeated because they felt like they
should work, and that survive because a fluent-sounding response after using them is indistinguishable
from a fluent-sounding response without them (§0.1.8 — fluency carries zero information about
correctness, which means it also carries zero information about whether your prompting trick did
anything). This file keeps only the practices that trace back to one of six facts already established
elsewhere in this guide: the model predicts from the text in front of it and nothing else
(§0.1.1–§0.1.2); it chooses a tool from that tool's description alone (§0.3.6), and a skill from its
listing entry alone (§1.5.22) — an instruction with the same vagueness produces the same kind of
misfire; an instruction file is context the model reads, not configuration the harness enforces
(§1.3.2); specific beats vague, verifiable beats aspirational, structured beats prose, and consistent
beats contradictory (§1.3.12); a claim of success carries no more evidence than its own fluency
(§0.1.8); and everything currently in the transcript is re-sent, and re-billed, on every subsequent
turn (§0.2.6). Every practice below is one of those six facts, applied.

## 1. Prompting that matters: reducing ambiguity, not persuading (§2.7.5)

**Mental model.** There is no back channel to the model. It is not inferring your mood, your
seniority, or how much you'll be disappointed if this goes wrong — the only thing that exists, at
the moment it generates the next token, is the literal text of the conversation so far (§0.1.1). A
sentence like "you are a 10x senior engineer, this is critical, please don't mess it up" changes the
token distribution exactly as much as those tokens change the distribution — which is to say it can
shift *style* (more hedging, more confident-sounding caveats, possibly more verbose reasoning
because "senior engineer" co-occurs with certain phrasings in training data) but it does not flip an
internal "try harder" switch, because no such switch exists to flip. There is no lever behind the
text. There is only the text.

**Why it exists.** Every one of the following beliefs is common, and every one is folklore because
it assumes a mechanism the model does not have:

| Folklore belief | What it assumes | What is actually true |
|---|---|---|
| Politeness ("please", "thank you") improves code quality | The model has a motivational state that responds to courtesy | The model has a token distribution conditioned on text; "please" adds four tokens of context, most of which correlate with nothing about correctness |
| Role-play ("act as a principal engineer at a FAANG company") raises the bar | Assigning a persona unlocks a higher competence tier | It can shift *style* toward text associated with that persona in training data — more hedged caveats, more architecture-flavoured vocabulary — but it does not grant capability the base model didn't have, and it costs the tokens of the framing on every subsequent turn (§0.2.6) |
| Threats or urgency ("this is extremely important", "you will be fired if this breaks") sharpen focus | The model allocates more "effort" under pressure | There is no effort dial reachable from prose. Some evaluations even show urgency-framed prompts correlating with slightly worse structured-output adherence, because urgency language crowds out the specific constraints that would have actually helped |
| A longer, more elaborate prompt is always safer | More words means more coverage | Ambiguity is reduced by covering the goal, the constraints, the done-condition, and the output location — not by word count. A long prompt that never states the done-condition is still ambiguous, and it now costs more per turn to boot |

The practices that *do* change outcomes are the ones that hand the model information it could not
otherwise have: the goal, the constraints, the done-condition, and where the answer goes. Those four
are not persuasion — they are the literal input to a process that has no other input.

**How it works.** Compare two versions of the same request, continuing the report-export scenario
from the previous file:

```
Before: "Can you add pagination to the report export? Thanks so much, you're the best,
take your time and do a really good job on this one."

After:  "Add cursor-based pagination to GET /reports/export in
ReportExportController. Constraint: keep the existing response shape — only add
`nextCursor` (nullable) to ReportPage. Done when
CursorPaginationTest passes and the existing ReportExportControllerTest suite still
passes unmodified. Write the change to
src/main/java/com/invoiceledger/reporting/ReportExportController.java and the matching
service class only — do not touch the CSV export path."
```

The "before" version is 24 tokens of which roughly none constrain the output — "take your time" is
not a constraint the model can act on, because there is no clock it is racing against inside a
single turn. The "after" version states the endpoint (goal), the response-shape constraint, the
exact done-condition (which tests pass), and the file boundary (where the answer goes and where it
must not go). Every one of those four pieces removes a decision the model would otherwise have to
guess, and every guess is a chance for a plausible-sounding wrong answer (§0.1.8) to get generated
with the same fluency as a right one.

The same shape appears in production prompts, not just examples built for a guide. The sdlc-harness
repository's `/implement-story` command,
`plugins/sdlc-harness/commands/implement-story.md`, states not only what it does but exactly what it
refuses and why, rather than leaving the model to infer the boundary:

```
### Rejected flags

`implement-story` runs through the conductor executor, which does not yet
have a documented executor-level contract for these — each MUST be rejected
with an explicit error naming the flag — never silently ignored or
reinterpreted:

- `--resume-at <stage>` — reject. The conductor has no stage-injection
  resume; use `--run-id <id>` (against the same feature's `harness.db`) to
  resume a run at whatever stage `conductor advance` derives from folded
  state.
```

Read this against the six-fact list above: the file does not say "be careful with flags" (aspirational,
unverifiable) — it names each rejected flag, the exact error behaviour required ("MUST be rejected...
never silently ignored"), and the alternative path. That is specific, verifiable, and structured —
exactly the §1.3.12 shape — applied to a real production prompt rather than a toy example.

**No diagram for this leaf:** the manifest assigns no `D-NN` to §2.7.5; the argument is textual, not
structural.

**Code:** the before/after pair above, and the invocation that carries it:

```bash
claude "Add cursor-based pagination to GET /reports/export in ReportExportController. \
Constraint: keep the existing response shape — only add nextCursor (nullable) to \
ReportPage. Done when CursorPaginationTest passes and the existing \
ReportExportControllerTest suite still passes unmodified. Write the change to \
src/main/java/com/invoiceledger/reporting/ReportExportController.java and the matching \
service class only — do not touch the CSV export path."
```

**Pitfall:** the wrong belief is "a warmer or more forceful tone changes how hard the model tries."
The symptom is time spent tuning adjectives and framing — "you are an expert," "this is critical,"
"take a deep breath and think carefully" — while the actual defect in the prompt (a missing
done-condition, an unstated file boundary) survives untouched, because tone-tuning and
ambiguity-reduction are different activities that happen to look similar from the outside. The fix:
before touching tone, check the prompt has all four of goal, constraint, done-condition, and output
location; if it does, further wordsmithing has diminishing and likely zero return; if it does not,
that gap — not the tone — is the actual defect. `[TRAP]` `**Pitfall:**`

> Prompting improves outcomes exactly to the extent that it removes ambiguity the model would
> otherwise have to guess through; anything added past that point is tokens spent on style, paid for
> on every subsequent turn, with no corresponding gain.

## 2. Give the agent what a new teammate would need (§2.7.6)

**Mental model.** Picture handing this same task to an engineer who started this morning: knows
Java and Spring Boot cold, has never opened this repository. Before they can start, they need the
file that owns the behaviour, the convention this codebase follows that isn't obvious from the
language alone (does pagination here use a cursor object or a raw string token? is `null` or an
empty string "no more pages"?), and the command that tells them whether they got it right. A senior
colleague on the team for two years doesn't need to be told any of that — they already have it. The
model is the new teammate on every single turn: it has no memory across sessions, and even within a
session `CLAUDE.md` and any other instruction file are text it reads as context, not configuration
the harness enforces on it (§1.3.2) — so nothing about "the project's conventions" persists unless it
is actually present, as text, in front of the model right now.

**Why it exists.** Under-specifying context, not under-specifying instructions, is the more common
and more expensive failure. §2.7.5's ambiguity was about the *task* (what to build); this leaf is
about the *facts* the model needs to build it correctly, which it cannot invent, only guess. And a
guess and a fact look identical once generated, because fluency carries no information about
correctness (§0.1.8) — so an under-specified prompt does not fail loudly with "I don't know how
pagination tokens work in this codebase." It fails silently, by picking a plausible convention (say,
a raw offset integer) that happens to be wrong for this codebase (which uses an opaque `Cursor`
type), and delivering it with exactly the same confident tone as if it had been right. This is what
"plausible-but-wrong" means concretely: not a crash, not a visible error, a result that reads fine
and is wrong.

**How it works.** The cheapest way to supply a fact the model cannot otherwise have is the in-session
`@` file reference and `!` shell-output mechanism from §0.4.7 — you are not describing the
convention in prose (which you might get slightly wrong or leave incomplete), you are handing the
model the actual file or the actual command output:

```
Before: "Add cursor-based pagination to the report export, following the pattern
we already use elsewhere in the codebase."

After:  "Add cursor-based pagination to the report export.
@src/main/java/com/invoiceledger/reporting/dto/Cursor.java is the existing cursor type —
use it, don't invent a new token shape.
@src/test/java/com/invoiceledger/reporting/CursorPaginationTest.java is the test this
must satisfy.
!mvn -q -pl reporting compile
should succeed before you consider this started — if it doesn't, the module is
already broken and that's a separate problem to report, not silently work around."
```

The "before" version says "following the pattern we already use," which is exactly the kind of
underspecified reference to tacit knowledge a new teammate would have to go find on their own —
except the model cannot go find it unless a tool call is spent doing so, and even then it might grep
the wrong file. The "after" version puts the actual `Cursor` class and the actual test into the
context directly: `@`-references are expanded to the literal file content before the model ever
predicts a token, so "use it, don't invent a new token shape" is now a constraint over text the model
has actually seen, not a constraint over a description of text it hasn't.

**Cost.** This is not free. Everything pulled in with `@` or `!` becomes part of the transcript from
that point forward, and the whole transcript is re-sent on every subsequent turn (§0.2.6) until it
either scrolls out of the window or the session compacts. Pulling in a 400-line file to reference one
20-line class means paying for the other 380 lines on every following turn. The corresponding
discipline is to reference the narrowest artefact that actually carries the fact — the one class, not
the package; the output of a scoped `mvn -pl reporting test`, not a full multi-module build log.

**No diagram for this leaf:** no `D-NN` in the manifest covers context-supply mechanics on their own;
D-64 (plan mode) and the mechanism decision tree at D-41 (referenced fully under §4 below) cover
adjacent but distinct decisions.

**Code:** the `@`/`!` prompt block above is the artefact — there is no separate settings key or
config file for this leaf; the mechanism lives entirely in what you type into the turn.

**Gotcha.** A `@`-reference supplies a fact once; it does not keep the model honest about that fact
on turn 40 of a long session, because compaction (covered in PART 3) can summarize the referenced
content out of the live window even though the fact was correct when it was first supplied. If a
convention matters for the whole session, re-reference it (or restate the constraint) after a
compaction boundary rather than assuming turn 3's `@`-reference is still verbatim in front of the
model at turn 40.

> Giving the agent what it needs means supplying, as literal text in the current turn, the specific
> file, convention, or command output a new teammate would ask for — because the model has no other
> way to acquire a fact it wasn't told, and a missing fact gets silently replaced with a plausible
> guess rather than a visible error.

## 3. The verification habit: no claim of success without an artefact (§2.7.7)

**Mental model.** This is the same argument that made the previous file's test-first leaf necessary,
generalized past the one case where a JUnit test happens to exist. §0.1.8 established that the
model's report of its own success is generated by the identical sampling process as everything else
it says — "yes, this handles the edge case correctly" carries the same fluency whether it is true or
false, because fluency is a property of the generation process, not of the underlying fact. Test-first
solved this for one narrow case: a failing test that turns green. The verification habit is the same
solution applied to every other kind of "done" claim the agent makes, most of which have no test to
check them.

**Why it exists.** An agent will say "the build passes," "the migration ran cleanly," "I checked and
the config is correct," or "the endpoint now returns 404 as expected" as a matter of course, because
these are the natural things to say at the end of a turn — and every one of those sentences is
exactly as confabulation-prone as any other model output. The habit is: never treat the sentence
itself as the evidence. Treat it as a claim, and ask what artefact would have to exist for the claim
to be checkable by something other than the model.

**How it works.** An artefact is something produced by a process other than the model's own token
generation — a compiler, a test runner, a shell exit code, `git diff` output you actually read. The
discipline is mechanical: after a "done" claim, either the artefact is already in the transcript
(because the agent ran the command and you can see its output above the claim), or you ask for it
before accepting the claim.

```bash
#!/usr/bin/env bash
set -euo pipefail

# verify-report-pagination.sh — run after the agent reports the pagination
# change is done. Produces an artefact (this script's own exit code and
# printed output), not a restatement of the agent's claim.

MODULE="reporting"
TEST_CLASS="CursorPaginationTest"

echo "== compiling ${MODULE} =="
mvn -q -pl "${MODULE}" compile

echo "== running ${TEST_CLASS} =="
mvn -q -pl "${MODULE}" test -Dtest="${TEST_CLASS}"

echo "== confirming the untouched suite still passes =="
mvn -q -pl "${MODULE}" test -Dtest='ReportExportControllerTest'

echo "VERIFIED: both suites green, ${MODULE} compiles."
```

Handed this script's actual stdout — not the agent's paraphrase of what the script would say, the
literal printed lines including `set -euo pipefail`'s hard stop on the first non-zero exit — you have
an artefact: either it printed `VERIFIED: both suites green` or `mvn` exited non-zero and the script
stopped at whichever stage failed, `set -e` propagating that failure rather than letting the script
limp forward and print a false "verified" after the real failure. Compare that to accepting "the
tests pass now" as a sentence: the sentence and the script's real output are indistinguishable in
tone, but only one of them was generated by something that cannot confabulate.

**No diagram for this leaf:** the manifest carries no `D-NN` for the verification habit as a general
practice; it is the same argument as §0.1.8 and the previous file's test-first leaf, restated at the
level of "any claim," not illustrated by a new picture.

**Gotcha.** An artefact is only as good as your reading of it. A test suite that always passes
(`assertTrue(true)`, covered as a `**Pitfall:**` in the previous file) is technically "an artefact" —
a real exit code, a real green line — and it proves nothing, because the artefact itself was never
built to be capable of failing. The habit is not "demand any artefact"; it is "demand an artefact,
and read what it actually checks before trusting the green." A `BUILD SUCCESS` line after a compile
with all the interesting warnings piped to `/dev/null` is the same failure mode wearing different
clothes.

> An artefact is evidence because it was produced by a process that cannot confabulate — a compiler,
> a test runner, a shell exit code; a claim of success is not evidence, no matter how confident it
> sounds, because it was produced by the exact process whose correctness is in question.

## 4. Second pass, fresh context: `/code-review`, `/security-review`, and self-review (§2.7.8)

**Mental model.** A reviewer reading the same conversation that wrote the code is not reading the
code cold — it is reading the code *plus* every assumption the writer already asserted along the way
("I'm assuming the cursor is never null here, that should be fine"), and the context window is the
entire argument list the next prediction conditions on (§0.2.1). A review turn appended to that same
transcript is conditioned on the writer's own justification for the choice it is supposed to be
checking, which is precisely the setup that makes a wrong assumption survive its own review: the
model isn't re-deriving "is this actually fine," it's continuing a conversation in which "that should
be fine" was already stated as settled three turns ago. A fresh context — a new session, or a
subagent that never saw the writing turns — starts from the diff and the requirement alone, with no
prior sentence anchoring it toward agreement.

**Why it exists.** This is the general form of an argument this guide already uses for a different
purpose: §1.5's skills and this file's §2.7.6 both rely on the model conditioning only on text
actually in front of it; here, the same fact cuts the other way — text in front of the model that you
*don't* want it conditioning on (the writer's own rationalizations) is exactly as available to it as
text you do want it using. A fresh context is the only way to withhold specific prior text from a
specific later turn.

**How it works — `/code-review` and `/security-review`.** Re-verified against the permitted
documentation set: the **skills** page states, in a note about built-in commands, that `/code-review`
is a bundled skill —

> "For built-in commands like `/help` and `/compact`, and bundled skills like `/debug` and
> `/code-review`, see the commands reference."

— confirming `/code-review` ships with Claude Code itself rather than being something a project has
to author. The skills page's note points onward to a commands-reference page that is outside this
guide's permitted citation set (`settings`, `settings-reference`, `permissions`, `hooks`,
`sub-agents`, `skills`, `memory`, `plugins`, `cli-reference`); per the authority order this guide
follows — documentation, then observed behaviour of the installed binary — `/security-review` is
confirmed the same way `/code-review` is: as a bundled skill directly visible in a running v2.1.2xx
installation's own skill listing, described there as completing "a security review of the pending
changes on the current branch." Both run as a fresh invocation over the current diff rather than as a
continuation of the session that produced it, which is the property this leaf is actually about —
not the specific wording of either skill's output.

The **sub-agents** documentation page grounds why a fresh context is worth reaching for at all, using
code review as its own worked example. Its subagent quickstart:

> "This walkthrough creates a user-level subagent that reviews code and suggests improvements."

and states the general benefit directly:

> "Preserve context by keeping exploration and implementation out of your main conversation."

A subagent runs in a context that never held the writing turns in the first place — stronger than a
same-session "please review your own diff" ask, because there is no "your" for it to be biased by.
`/code-review` and `/security-review` get most of this benefit cheaply, as a slash-invoked skill
rather than a hand-authored subagent definition; a project that wants a specific review rubric,
specific inputs, or a specific pass threshold reaches for a dedicated subagent instead, which is the
decision the mechanism tree at **D-41** (in `skills/06`) lays out — not reproduced here, since this
file owns no diagram of its own; see it there for the full "which mechanism and why" comparison
across skills, subagents, and hooks.

**Self-review, grounded in sdlc-harness.** The same argument is load-bearing enough that
sdlc-harness builds it into the pipeline as a named mode, not just a convention. Its concepts
document, `docs/onboarding/harness-concepts.md`, defines the distinction directly:

```
Each harness stage runs in one of two modes — interactive (UNDERSTAND, QA PLAN) or
stateless (Requirements Review, Coder, QA Execute, Code Reviewer).
```
```
**Stateless** (Requirements Review, Coder, QA Execute, Code Reviewer) — the teammate
receives a brief, produces an artifact, and returns. It cannot ask questions mid-run.
```
```
**Teammates** — subagents spawned for each stage ... Each teammate receives a scoped
brief, produces one artifact, and exits. They are stateless: they have no memory of
previous stages beyond what the team lead puts in their brief.
```

The `code_reviewer` stage's own entry in `docs/reference/stage-catalog.md` names the agent that
fills it as `code_reviewer / self-review`, running `stateless`, and lists its actual inputs:

```
**Inputs:**
- `outputs/rfc.md`
- `outputs/implementation/`
- `outputs/code-analysis.md` (written by `sc:analyze` pre-analysis step)
- `harness/control-plane/judge-rubrics/code-review.yaml`
```

Read that input list against the mental model above: it is the requirement document, the finished
implementation, a pre-computed static-analysis pass, and a scoring rubric — not the coder's own
conversation. The `self-review` teammate that reviews the code was never in the room while the code
was written; "no memory of previous stages beyond what the team lead puts in their brief" is the
sdlc-harness engine's own restatement of exactly the guarantee a fresh context provides, applied on
purpose rather than as an accident of how a chat session happens to be structured. The rubric it
scores against, `harness/control-plane/judge-rubrics/code-review.yaml`, is itself evidence for why
this matters: it weighs `correct_implementation`, `security_basics`, and `maintainability` at the
top of an eight-criterion, weighted scale with `pass_threshold: 8` — a fresh-context reviewer checking
a fixed, structured rubric against artefacts, not asking the writer "are you sure this is right."

**No diagram embedded here:** this leaf's decision (skill vs. subagent vs. self-review persona) is
exactly what D-41's mechanism tree in `skills/06` already draws; re-embedding it in this file would
duplicate that picture for the same decision. Reference it there.

**Gotcha.** A fresh context removes the writer's own rationalizations from what the reviewer sees —
it does not supply anything the reviewer needs beyond that. A `/code-review` invocation with no diff
in scope, or a `self-review`-style stateless stage handed an empty brief, reviews nothing more
capably than a same-session ask would; the benefit is specifically the *absence* of the writer's
prior turns, not a general quality boost. And self-review of any kind — same-session or fresh-context
— still shares one thing with the code under review: it is generated by the same kind of process
that produced the bug in the first place, so it is a real improvement over asking the writer directly,
not a substitute for a human reading the diff on anything that actually matters.

> A reviewer sharing the writer's context inherits every assumption the writer already stated as
> settled, because the context window is the argument list the next prediction conditions on; a
> fresh context — a bundled review skill, a dedicated subagent, or a stateless self-review stage
> that never held the writing turns — removes exactly that inheritance, and nothing else.

## Pitfalls

- **Belief:** "a warmer, more forceful, or more elaborate prompt gets better results out of the
  model." **What actually happens:** tone and framing shift style, not correctness, because there is
  no motivational or effort state behind the text for tone to act on — time spent tuning adjectives
  leaves the actual ambiguity (a missing done-condition, an unstated file boundary) untouched. **What
  gets the guarantee:** state the goal, the constraints, the done-condition, and where the answer
  goes; treat everything else as optional. **Why people believe it:** a more elaborate prompt
  sometimes does perform better, but because the elaboration happened to include a real constraint,
  not because of the tone — the two are easy to conflate when you only see the outcome.
- **Belief:** "I told it to follow our conventions, so it will." **What actually happens:** a
  convention that exists only as tribal knowledge, or as a sentence in a CLAUDE.md the model treats
  as context rather than enforced configuration (§1.3.2), gets silently replaced by whatever
  convention is statistically plausible from the model's training data — a raw offset integer where
  this codebase actually uses an opaque cursor type — delivered with the same confident tone either
  way. **What gets the guarantee:** hand over the actual file or actual command output with `@` and
  `!`, not a description of it. **Why people believe it:** the model frequently does infer the right
  convention correctly by chance or by grep, so the failure is intermittent and easy to miss until
  the one time it silently picks wrong.
- **Belief:** "it said the tests pass / the build is clean / the migration ran, so it's done."
  **What actually happens:** that sentence is generated by the same process, with the same fluency,
  whether or not it's true — it is not evidence. **What gets the guarantee:** an artefact produced by
  something other than the model's own generation — a real test-runner exit code, a real compiler
  output, a diff you actually read — checked, not just requested. **Why people believe it:** a
  correct "done" claim and a confabulated one are word-for-word indistinguishable, so believing the
  sentence works exactly as often as the model happens to be right, which is often enough to build
  the habit before it fails.
- **Belief:** "asking it to review its own diff in the same session is basically the same as a proper
  code review." **What actually happens:** the reviewing turn is conditioned on the writer's own
  prior justifications in the same transcript, which anchors the review toward agreeing with
  decisions already asserted as settled. **What gets the guarantee:** a fresh context — `/code-review`,
  `/security-review`, a dedicated subagent, or a stateless review stage that only ever sees the
  artefacts, never the writer's live session. **Why people believe it:** "review your own work" is
  sound advice for a human, who is not literally re-reading their own stated assumptions as
  established fact on every subsequent sentence the way a shared context window does.

## Cheat sheet

| Practice | What it supplies / removes | Mechanism it exploits | What it costs |
|---|---|---|---|
| Goal, constraint, done-condition, output location | Removes ambiguity the model would otherwise guess | The model conditions only on the literal text present (§0.1.1) | None beyond writing the prompt precisely |
| Politeness, role-play, threats, urgency | Nothing measurable | No effort/motivation state exists for tone to act on | Tokens, re-billed every subsequent turn (§0.2.6), for zero return |
| `@file`, `!command` context supply | The specific fact a new teammate would ask for | Model has no memory across sessions; a described convention can be guessed wrong, a supplied one cannot | Everything pulled in stays in the transcript, re-sent every turn, until compaction |
| Verification habit (artefact over claim) | Distinguishes a checked fact from a confident sentence | Fluency carries zero information about correctness (§0.1.8) | The discipline of actually running and reading the check, not just requesting it |
| `/code-review`, `/security-review`, self-review stage | A reviewing turn with no inherited writer rationalization | Context window is the argument list; a fresh one has none of the writer's prior claims in it | An extra invocation/round trip; only removes what a fresh context removes, adds nothing else |

## Self-test

1. Why doesn't a threatening or urgent prompt ("you will be fired if this breaks") make the model try
   harder?
<details><summary>Answer</summary>There is no internal effort or motivation state for such language
to act on — the model predicts the next token from the literal text in front of it. Urgency language
can shift style (more hedging, different vocabulary) but does not unlock additional capability or
correctness, and can crowd out space that would otherwise carry an actual constraint.</details>

2. What four pieces of information does a prompt need to actually reduce ambiguity, per §2.7.5?
<details><summary>Answer</summary>The goal, the constraints, the done-condition, and where the answer
goes (which file or files it should land in, and which it should not touch).</details>

3. Why is "add pagination following the pattern we already use elsewhere" a weaker prompt than one
   that includes an `@`-reference to the actual existing cursor type?
<details><summary>Answer</summary>The model has no memory across sessions and cannot reliably locate
or correctly infer the unstated convention; if it guesses, the guess is delivered with the same
fluent confidence as a correct answer, so "plausible but wrong" (e.g. inventing a raw-offset token
instead of using the existing opaque Cursor type) is the likely failure mode. An `@`-reference
supplies the actual class as literal text the model has actually seen.</details>

4. What is the cost of pulling a large file into context with `@` to reference one small fact inside
   it?
<details><summary>Answer</summary>The entire file becomes part of the transcript and is re-sent, and
re-billed, on every subsequent turn until it scrolls out of the context window or the session
compacts — not just the turn where it was referenced.</details>

5. Why does an agent's own claim that "the tests pass" not count as verification?
<details><summary>Answer</summary>That claim is generated by the same token-sampling process as
everything else the model says, with the same fluency whether it is true or false (§0.1.8) — fluency
carries no information about correctness, so a confident claim of success is not distinguishable from
a confabulated one by its wording alone.</details>

6. Give an example of an "artefact" that looks like verification but proves nothing.
<details><summary>Answer</summary>A test that always passes regardless of implementation correctness
(e.g. `assertTrue(true)`, or assertions derived from an already-written implementation rather than
from the requirement) — it is a real exit code and a real green line, but it was never capable of
failing, so passing it demonstrates nothing.</details>

7. Why does reviewing your own diff in the same conversation that wrote it produce a weaker review
   than a fresh context would?
<details><summary>Answer</summary>The context window is the argument list the next prediction
conditions on. A review turn appended to the writing conversation is conditioned on every assumption
the writer already asserted as settled in that same transcript, which anchors the "review" toward
agreeing with decisions the model itself already committed to in words, rather than re-deriving
whether they were correct.</details>

8. Per the sdlc-harness `docs/reference/stage-catalog.md` entry for `code_reviewer`, what does the
   stateless `self-review` teammate actually receive as input, and what does it specifically not
   receive?
<details><summary>Answer</summary>It receives `outputs/rfc.md`, `outputs/implementation/`, a
pre-computed `outputs/code-analysis.md`, and the `code-review.yaml` rubric — artefacts. It does not
receive the coder's own live conversation or session; per `docs/onboarding/harness-concepts.md`,
stateless teammates "have no memory of previous stages beyond what the team lead puts in their
brief."</details>

9. Are `/code-review` and `/security-review` project-authored skills or something Claude Code ships
   with?
<details><summary>Answer</summary>Both are bundled (built-in) skills. The skills documentation page
names `/code-review` explicitly as a bundled skill in its note about built-in commands;
`/security-review` is confirmed the same way, as a bundled skill visible directly in a running
v2.1.2xx installation's own skill listing.</details>

10. Does a fresh-context review guarantee a correct review?
<details><summary>Answer</summary>No. It removes one specific failure mode — inheriting the writer's
own stated rationalizations — and nothing else. The reviewer is still generated by the same kind of
process that produced the original code, so a fresh-context review is an improvement over
same-session self-review, not a substitute for a human reading the diff on anything that actually
matters.</details>

## Open questions

None.

---

**Leaves covered:** 2.7.5–2.7.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-64 in the previous file draws plan mode, and D-41 in `skills/06` draws the mechanism decision tree
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 519
