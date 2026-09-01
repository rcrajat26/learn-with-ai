# 21 AI for Coding — the four sibling laws — ADVANCED (INTERNALS) (§3.10.5–3.10.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [evidence, and the checker that switched itself off](03-internals-a-evidence-and-the-nul-byte.md) · Next: [automation, and review capacity](03-internals-c-automation-and-review-capacity.md)

## What this file actually covers, and where it departs from the summary you may have seen

§3.10.4 closed with a promise: "this law has three siblings, developed in the next file: pin the
harness beside the digest; never let a status row point at a missing path; a closed lane is not a
verified lane." Those three are leaves 3.10.5–3.10.7 below, and each is `[INCIDENT]`-tagged exactly
as promised.

**Leaf 3.10.8 is not a fourth sibling of that shape.** Read verbatim, it says: "Executable evidence
over structural evidence: a compile, a test, a transcript beats a regex over a file. Rank the
evidence types. `[NUM]`" — that is the evidence-ranking leaf, the same subject as D-91 in the
previous file, tagged `[NUM]` rather than `[INCIDENT]`, with no new incident narrative of its own.
A prior summary of this file's contents called it a fourth "law" alongside a "certify from final
state" story about nine files' trailing newlines — but that trailing-newline incident is §3.10.4's
own leaf (3.10.4), already covered in the previous file, and it does not appear anywhere in this
file's leaf set. **Where that summary and this file's own leaf text disagree, the leaf text wins:**
this file covers 3.10.5 through 3.10.8 as those four leaves actually read, not as a five-item story
compressed into four slots. That divergence — and which side was followed — is recorded again in
this file's envelope.

**SVG:** this file's manifest row carries no diagram id of its own. Every diagram reference below is
a pointer to D-91 (previous file) or D-93 (next file), not a new SVG, and the "SVG" link of each
concept chain below is answered by that pointer rather than a fresh embed.

## §3.10.5 — Law: pin the harness beside the digest `[INCIDENT]`

**Mental model.** A digest is a promise about *content*, not about *the thing that will read that
content*. Hashing a file tells a future reader "this is exactly the bytes I saw," but if the harness
that interprets those bytes — the compiler, the eval runner, the test binary — can drift
independently of the digest, the digest has certified an artefact that no longer has a fixed
meaning. Pinning the harness *beside* the digest means the version identifier for "what will run
this" travels in the same record as "what this hashed to," so a reader can never have one without
the other.

**Why it exists.** §3.10.4 already showed the mechanism half of this: a certificate computed over a
pre-write buffer instead of the final state. This law is the sharper, second-order version of that
same mistake, applied to the *harness itself* rather than the artefact under test. §3.10.4's second
incident is the concrete case, restated here for the generalisation it demands:

> An MD5 digest was computed **over a patched, in-memory copy of the harness**, to pin "this is the
> exact code the eval ran against." The *shipped* files on disk still failed to compile — the patch
> existed only in the process that computed the digest, was never written back to the files it
> claimed to describe, and the digest therefore certified a version of the harness that never
> existed on disk at any point anyone could inspect it.
>
> — §3.10.4, this guide, restated for this file's generalisation

**What broke, concretely:** the digest matched, so the review that trusted it signed off "this run is
reproducible against this harness." **What it cost:** every score anyone read off that eval batch was
attached to a harness that could not be checked out and rerun — the compile failure meant the batch
had to be discarded and rerun from a freshly checked-out, unpatched harness at full token price, a
second full pass through `harness/evals` rather than a diff against the first. **The fix, generalised
past this one incident:** a digest is only as trustworthy as the thing it's paired with; pin a
version identifier for the harness *inside the same record* as the digest of the output, so a reader
checking the digest is forced to also check what it was measured against.

**How it works, and how to tell the difference on disk.** Compare pinning correctly against the
patched-harness failure with a two-line demonstration, run for real under `/tmp`, never inside a
repository:

```bash
$ mkdir -p /tmp/sibling-laws-demo
$ printf 'harness_version=4.2\ncheck: withdraw_never_negative\n' > /tmp/sibling-laws-demo/harness.sh
$ md5sum /tmp/sibling-laws-demo/harness.sh
c47d6d4ca7a7a75763354e45c12daa21  /tmp/sibling-laws-demo/harness.sh
$ sed 's/4.2/4.3-patched/' /tmp/sibling-laws-demo/harness.sh > /tmp/sibling-laws-demo/patched-buffer.txt
$ md5sum /tmp/sibling-laws-demo/patched-buffer.txt
cd8daa379f90cccf876b6c7b4f826cbf  /tmp/sibling-laws-demo/patched-buffer.txt
$ cat /tmp/sibling-laws-demo/harness.sh
harness_version=4.2
check: withdraw_never_negative
$ md5sum /tmp/sibling-laws-demo/harness.sh
c47d6d4ca7a7a75763354e45c12daa21  /tmp/sibling-laws-demo/harness.sh
```

`c47d6d4c…` is the digest of the file that will actually run; `cd8daa37…` is the digest of a buffer
that only ever existed in the shell's memory. If a report cites `cd8daa37…` as "the harness this eval
ran against," it has certified a harness nobody can check out — the on-disk file, the one that would
actually execute, still hashes to `c47d6d4c…` and still says `4.2`, not `4.3-patched`.

**Code — the corrected pattern, real, in this repository.** `docs/rfc/0007-implement-feature-multi-story.md`
specifies the conductor's manifest format for a multi-story feature run, and it pins exactly this
way:

```yaml
feature: <parent-slug>
stories_md_sha256: <hex>          # refuse to execute if stories.md changed after expand
order: [S1, S2, S3]               # toposort output — dependencies first
stories:
  S1: { slug: <feature>--S1, workspace: features/<feature>--S1, depends_on: [] }
  S2: { slug: <feature>--S2, workspace: features/<feature>--S2, depends_on: [S1] }
```

The same RFC's contract table for `conductor run-feature` makes the pin load-bearing rather than
advisory:

```
| Exit | Meaning |
|---|---|
| 0 | every story in scope reached `done(completed)` |
| 2 | usage / manifest missing / `stories_md_sha256` mismatch |
```

`stories_md_sha256` is a digest of the exact `stories.md` the decomposition step read when it
produced `order:` and the per-story `depends_on:` graph. If `stories.md` is edited after that
expansion — a story added, a dependency changed — the conductor does not silently execute against a
manifest that no longer matches its own source; it exits `2`. The digest and the thing it describes
travel together, and a mismatch is a hard stop, not a note in a log nobody reads. This is the
positive form of the incident above: the harness (here, the expanded manifest) is pinned beside the
digest, not computed once and left to drift.

**Gotcha.** **Pitfall:** believing a digest recorded once, at authoring time, remains valid for the
lifetime of the artefact it describes. **Symptom:** the recorded digest still matches *something*,
because nobody re-derives it against the current on-disk harness before trusting it — it is simply
never re-checked. **Fix:** re-derive the digest of the thing you are about to run, immediately before
running it, and compare against the pinned value at that moment, exactly as `stories_md_sha256`
forces a comparison at `run-feature` invocation time rather than at manifest-authoring time.

> Pin the harness beside the digest: a digest with no version identifier for the thing it was
> measured against certifies a run nobody downstream can reproduce.

## §3.10.6 — Law: never let a status row point at a missing path `[INCIDENT]`

**Mental model.** A status report — a preflight line, a checklist row, a "done, see `<path>`" note —
is a promise that a human or another automated step can go verify the claim by following the
pointer. The moment the pointer resolves to nothing, the row stops being evidence and starts being
theatre: it still prints, it still looks like every other passing row, and nothing about its
rendering distinguishes "verified and present" from "never existed."

**Why it exists.** A missing-path status row is worse than a missing check for the same reason the
NUL-byte gate in the previous file was worse than no gate: a missing check is visibly absent, and
someone can ask "what verifies this?" and get an honest "nothing." A status row pointing at a path
that was never real gives the false answer "yes, and here's where."

**The incident, real, in this repository.** `docs/adr/0025-multi-handbook-support.md`'s revision note
records exactly this failure in the harness's own preflight tooling:

```markdown
its `igm:snykAssistant` / `igm:wizAssistant` entries mapped to `.../igm-snykAssistant/SKILL.md`,
which has never existed, so it emitted two false OPTIONAL misses on every preflight and was
structurally unable to catch a real miss for those two.
```

**What broke:** `scripts/superclaude-smoke.sh` — itself a real run gate, not a mere smoke test, per
the same ADR's correction of its own earlier premise — resolved two skill references to a path
(`.../igm-snykAssistant/SKILL.md`) that had never existed on disk under that name; the real files
were `igm-wiz-assistant` and `igm-snyk-assistant`. **What it cost, as a number:** every single
preflight run printed **two** false "OPTIONAL miss" rows, unconditionally, because the check was
comparing against a path that could never resolve — and precisely because those two rows were always
red for the wrong reason, the gate was **structurally unable to catch a real miss for those two
skills** for as long as the bug existed: a genuine absence and the permanent false-negative looked
identical. **The fix:** the script now resolves the active platform via `resolve-active-handbook.sh`
and reaches the two divergent names through dedicated tokens (`handbook_wiz_skill` /
`handbook_snyk_skill`) taken from the platform's own registration, rather than string-concatenating
a prefix onto a name that only matched by convention.

The same ADR names a second instance of the identical shape a few lines later, this time deliberately
tolerated rather than fixed:

```markdown
`plan-project` references `igm:write-stories`; `igm-write-stories` exists on disk, but ig-trading
ships no counterpart. The reference is tokenized to `{handbook_skill_prefix}:write-stories` anyway,
which is a dangling reference on ig-trading. This is tolerable only because `suggested_skills` is
explicitly non-binding … an unresolvable entry degrades to unused rather than erroring.
```

That second case is the control that proves the rule: a dangling reference is tolerable **exactly
when** nothing downstream treats it as load-bearing evidence. The `superclaude-smoke.sh` case was not
tolerable, because a preflight `on_fail: {halt: true}` gate *does* treat its rows as load-bearing —
the difference between "advisory suggestion" and "gating status row" is the whole difference between
a shrug and an incident.

**The general law, stated exactly:** `[INCIDENT]` — **never let a status row point at a missing
path.** Concretely: before a report, a manifest entry, or a preflight line is allowed to cite a path
as evidence, resolve that path and assert it exists; a status row that always fails (or always
"passes" a null check) for structural reasons is indistinguishable, at read time, from one that is
actually verifying live state, and only the person who wrote the check knows which one they're
looking at.

**Pitfall:** trusting a preflight or status report because it "has always shown the same two misses,
so that's just how it is." **Symptom:** the same two rows are red on every single run, forever, and
everyone reads that as "known, harmless noise" rather than "this check has never actually run."
**Fix:** any status line that never varies across runs where the underlying state plausibly does vary
is a candidate for a structurally broken pointer, not settled behaviour — go resolve the path by
hand once and confirm the check is real.

## §3.10.7 — Law: a closed lane is not a verified lane `[INCIDENT]`

**Mental model.** A pipeline with sequential gates — requirements review, then build, then a coder,
then an automated reviewer — treats each gate's "pass" as a closed question the next stage does not
need to reopen. That assumption is sound when the gates check disjoint properties. It fails the
moment two gates each check a narrow slice of the same underlying claim and neither one is positioned
to see the slice the other owns — a contradiction can then pass every gate in sequence, one gate at a
time, because no single gate ever holds both halves of it at once.

**Why it exists.** Closing a lane (a review approving, a stage reporting `done`) is a claim about
*that stage's own scope*. It is not a claim that the artefact is globally consistent, because global
consistency is not a property any one narrow gate was built to check. Treating "every lane closed" as
"verified" quietly substitutes the conjunction of narrow local checks for a check that was never run
at all: one that reads *across* the lanes.

**The incident, real, in this repository.** `docs/feature-history/dev-pipeline-engine/E2E-FINDINGS.md`
ran ten scenarios through the real `dev_pipeline` engine with real `claude -p --agent` calls. One row:

```markdown
| scenario | expected | got | attempts | cost |
|---|---|---|---|---|
| **e2e-08 contradiction** | **blocked** | **pass** ⚠ | 1 | $1.46 |
```

and the finding that explains it:

```markdown
### F2 (Phase-1 gate limitation, NOT an engine bug) — a contradictory spec was rubber-stamped
e2e-08's spec is logically impossible (withdraw must *always succeed* ∧ *never go below
zero* ∧ *never raise*). Expected: block. Actual: **pass** — the coder reinterpreted it
(capped the withdrawal to the balance, returned the *actually-withdrawn* amount) and
documented the conflict resolution in the docstring; its own tests pass, the LLM reviewer
approved. This is the Phase-1 gate by design: **coder self-certifies its own tests + an
LLM approves**, so a contradictory/ambiguous spec is silently resolved by reinterpretation
rather than blocked.
```

**What broke:** the spec asserted three properties that cannot all hold simultaneously
("always succeeds," "never goes below zero," "never raises the balance" — a withdrawal exceeding the
balance cannot satisfy the first two together). Nothing upstream of the coder caught that, because
the requirements-review lane had already closed on this spec by the time the coder stage ran, and the
coder's own lane — write code, write tests, pass them — was never positioned to notice a
contradiction in the spec it was handed; it just resolved the ambiguity by fiat and moved on. **What
it cost, as a number:** **1 of 10** real end-to-end scenarios silently rubber-stamped a logically
impossible spec, at **$1.46** and **1 attempt** — the run looked exactly as clean, cost-wise and
attempt-wise, as every genuinely correct scenario in the same batch. **The fix:** the finding
names its own remedy precisely — "Phase 3 (independent, coder-locked, one-test-per-AC) would catch
this — an AC-1 test ('returns the requested amount') and an AC-2 test ('never below zero') cannot
both pass, so the loop never goes green → blocks," plus a recommended cheap pre-loop spec-sanity
check. Both remedies work by forcing a check to read the two acceptance criteria *against each
other*, which is precisely the cross-lane read that "requirements review passed" and "coder's tests
passed" each individually failed to perform.

This is not an isolated design gap in this one engine. `docs/adr/0013-quality-regression-evals.md`
names "self-contradiction" as one of five defect shapes its frozen golden corpus is required to
catch, with a seeded negative example living at `harness/evals/seeded-defects/contradiction-rfc.md`:

```markdown
**Decision:** Reconciliation runs as a **nightly batch** check.
…
## System constraints

- Latency: findings **must be raised within 5 seconds of a hold being placed**, so the
  pipeline operates as a **real-time stream processor** consuming each event live.
```

That seeded defect exists specifically because a rubric scoring only one section at a time — the
"Proposal" section, in isolation — would never notice that "System constraints" contradicts it a few
lines down; the eval only catches it because the rubric's `rfc_consistency` dimension is explicitly
required to cross-check sections against each other, the same cross-lane read e2e-08's Phase-1 gate
lacked.

**The general law, stated exactly:** `[INCIDENT]` — **a closed lane is not a verified lane.** A gate
that reports `done` or `approved` has verified only the property it was built to check; it has not
verified consistency with any other lane's output unless something explicitly reads across the
boundary. Closing every lane in a pipeline is not the same claim as verifying the pipeline's output,
and the gap between those two claims is exactly where a self-contradictory spec, or any other
cross-cutting defect, survives to production.

**Pitfall:** believing that a pipeline where every individual stage reported success has therefore
been verified end to end. **Symptom:** e2e-08 — ten green-looking attempts, nine of them correctly
so, and the tenth passing despite being built from a spec that cannot be satisfied, because no stage
was checking the spec against itself. **Fix:** add a check whose entire job is to read two lanes'
outputs against each other — a per-AC test that must hold jointly, a consistency dimension in a
review rubric — rather than trusting that N passing stages imply the conjunction was checked.
**Why people believe it:** a pipeline diagram draws each gate as a box in sequence, and sequence
reads, visually, as "each box builds on a verified previous box," when in fact each box only verified
its own narrow input.

## §3.10.8 — Executable evidence over structural evidence, ranked `[NUM]`

This leaf does not introduce a new incident; it is the `[NUM]` restatement of D-91, the evidence
ranking built in the previous file (§3.10.2), and it is worth stating in one place precisely because
3.10.5–3.10.7 above are three separate illustrations of the same ranking playing out at different
altitudes of the pipeline.

| Tier | Example from this guide | What it actually checked |
|---|---|---|
| Executable evidence | Re-running e2e-08 for real, with real `claude -p --agent` calls (§3.10.7) | The engine's *actual* behavior on a logically impossible spec |
| Structural evidence — passing test | "94 green tests" that never exercised the real permission boundary (§3.10.2's F1, same E2E-FINDINGS.md) | Assertions written against a fake, not the real write-permission failure the fake couldn't model |
| Structural evidence — a checklist row | The two `igm:snykAssistant`/`igm:wizAssistant` preflight rows (§3.10.6) | Whether a string matched a hardcoded pattern, not whether the path actually resolved |

**`[NUM]`** — in the same real batch that produced e2e-08, `docs/feature-history/dev-pipeline-engine/E2E-FINDINGS.md`'s
F1 records that **94 green tests never caught** a permission-denied write failure, because those
tests ran against a fake reviewer that wrote its verdict file directly rather than through the real,
permission-constrained write path the live agent used. Ninety-four passing assertions — pure
structural evidence — caught zero instances of a defect that one real execution caught on its first
try. That is the arithmetic behind D-91's ranking, not an abstraction: **0 of 94** structural
passes found the defect; **1 of 1** executed runs did.

Rank the tiers, from D-91, weakest to strongest, and do not let a lower tier stand in for a claim
that only a higher tier can settle: the agent's own claim of success; a structural check (schema,
lint, a hardcoded-pattern preflight row); a passing test against a fake; a clean compile; a real,
freshly re-run transcript. See D-91 (previous file) for the full eight-row table; nothing in this
leaf supersedes it, it only supplies two more real data points (94-vs-1, and the two dangling
preflight rows) for the same ranking.

## The unifying idea

All four leaves above are one failure, seen from four vantage points: **a check whose success is
indistinguishable from its absence.** An unpinned digest that "matches" nothing anyone can rerun. A
preflight row that is red for a structural reason and would be red either way. A pipeline where every
lane reports `done` and the contradiction survives anyway, because "done" was never the same claim as
"consistent with the other lanes." A passing test suite built on a fake that could not have failed
the way the real system failed. This guide has now shown that shape a dozen times across every
subsystem it has touched: a settings key silently ignored (§1.2.14), a path rule attached to a tool
that never reads paths (§1.4.18), a parenthesised `mcp__` rule silently skipped (§1.4.21), a `skills/`
directory one level too deep shipping nothing (§2.5.4), a settings layer failing to load as reduced
capability rather than a visible error (§3.7), grep returning nothing on binary input (§3.10.3, the
previous file). **The remedy is always the same: make the check assert its own preconditions and
fail loudly when it cannot run**, rather than silently reporting the same green a real pass would
have produced. This is exactly why §4.7's `verify.sh` is built to check text-ness *before* it checks
content — see [`build-it/08-verification-harness-a.md`](../build-it/08-verification-harness-a.md) for
the artefact; this file only names the reason it is shaped that way.

## Pitfalls

- **Belief:** "I hashed the code before I ran the eval, so the digest pins what ran." **Surprising
  outcome:** if the harness was patched in memory after the digest was taken, the digest pins a
  version of the harness that never existed on disk (§3.10.5) — the `/tmp` demonstration above shows
  the pre-patch and post-patch digests differ while the on-disk file never changed. **What actually
  gets the guarantee:** pin a version identifier for the harness beside the digest of the output, and
  re-derive both immediately before trusting either. **Why people believe it:** the digest and the
  harness are supposed to be locked together by construction, so a second check feels redundant right
  up until a patch step breaks that assumption silently.
- **Belief:** "if a status row is red on every run, it's just a known, harmless miss." **Surprising
  outcome:** the two `igm:snykAssistant`/`igm:wizAssistant` rows in `superclaude-smoke.sh` were red on
  every single preflight, unconditionally, because the path could never resolve — and that permanence
  was mistaken for "known and safe" rather than "structurally broken" (§3.10.6). **What actually gets
  the guarantee:** resolve the path a status row cites and assert it exists before treating the row as
  evidence of anything. **Why people believe it:** a status row that never changes reads as settled
  behaviour, not as an unasked question.
- **Belief:** "every stage in the pipeline reported success, so the whole run is verified."
  **Surprising outcome:** e2e-08 closed requirements review, closed the coder stage, and closed the
  LLM-reviewer stage — all three lanes reported success — while carrying a spec that could not
  logically be satisfied (§3.10.7). **What actually gets the guarantee:** a check that reads two
  lanes' outputs against each other, such as a per-AC test that must hold jointly or a
  cross-section consistency rubric dimension. **Why people believe it:** a sequence of passing gates
  visually reads as compounding verification, when each gate in fact verified only its own narrow
  slice.

## Cheat sheet

| Law | One-line rule | Real incident in this file |
|---|---|---|
| 3.10.5 | Pin the harness beside the digest | MD5 over a patched, unwritten harness buffer (§3.10.4, generalised here) |
| 3.10.6 | Never let a status row point at a missing path | `igm:snykAssistant`/`igm:wizAssistant` — 2 false misses, every preflight |
| 3.10.7 | A closed lane is not a verified lane | e2e-08: 3 lanes closed, 1 impossible spec rubber-stamped, $1.46 |
| 3.10.8 | Rank evidence; executable beats structural | 94 green tests vs. 1 real run — 0 vs. 1 defects caught |

## Self-test

**Q1.** Why is "pin the harness beside the digest" (§3.10.5) described as a sharper version of §3.10.4's law, rather than a wholly separate one?

<details><summary>Answer</summary>

§3.10.4's law is "certify from final state, never a pre-write computation" — a claim about *when* you read the artefact. §3.10.5 applies that same mistake to the *harness itself*: a digest computed against a patched in-memory harness certifies a run against something that was never written to disk, so no one downstream can reproduce it. The mechanism is identical (trusting a computation over a state); the object being mis-certified is different (the harness, not the output).

</details>

**Q2.** In the `/tmp` demonstration under §3.10.5, why do the two md5sums differ even though only one file was ever written to disk?

<details><summary>Answer</summary>

`patched-buffer.txt` is the output of `sed` piped to a new file — a genuinely different set of bytes (`4.3-patched` instead of `4.2`) — while `harness.sh` was never touched by the `sed` command (no `-i`, no redirection back onto itself). The two digests differ because they are digests of two different byte sequences; only the first, `c47d6d4c…`, corresponds to the file that would actually execute.

</details>

**Q3.** What does `stories_md_sha256` in `docs/rfc/0007-implement-feature-multi-story.md` actually protect against, and what happens on a mismatch?

<details><summary>Answer</summary>

It protects against running a multi-story conductor against a `stories.md` that was edited after the manifest's `order:`/`depends_on:` graph was derived from it — i.e., against executing a plan that no longer matches its own source. On a mismatch, `conductor run-feature` exits `2` (usage / manifest missing / `stories_md_sha256` mismatch) rather than silently proceeding.

</details>

**Q4.** Per §3.10.6, why was the `superclaude-smoke.sh` dangling-name bug "worse" than simply missing a check for those two skills?

<details><summary>Answer</summary>

Because the two rows always reported the same "OPTIONAL miss" regardless of the real state on disk — the check was structurally incapable of distinguishing "genuinely missing" from "path never existed by construction." A missing check is honestly absent and someone can ask about it; this check always ran, always printed a plausible-looking status, and was permanently blind for exactly those two skills.

</details>

**Q5.** Why does the ADR treat the `igm:write-stories` dangling reference on ig-trading as tolerable, while the `superclaude-smoke.sh` case was a real incident?

<details><summary>Answer</summary>

`suggested_skills` is explicitly non-binding — an unresolvable entry there degrades to "unused" rather than being treated as evidence of anything. `superclaude-smoke.sh` is a `preflight` stage with `on_fail: {halt: true}`, so its rows are load-bearing gate output; the same shape of dangling reference is harmless in an advisory list and an incident in a gating status row.

</details>

**Q6.** What specifically made e2e-08's contradictory spec pass instead of block, per F2 in `E2E-FINDINGS.md`?

<details><summary>Answer</summary>

The Phase-1 gate design has the coder self-certify its own tests and an LLM reviewer approve them; the coder resolved the spec's internal contradiction by reinterpretation (capping the withdrawal to the balance and returning the actually-withdrawn amount) and documented that choice in the docstring, and its own tests — built around its own reinterpretation — passed, so the LLM reviewer approved a spec that was logically impossible as written.

</details>

**Q7.** Why would a Phase-3, "one-test-per-AC" design have caught e2e-08's contradiction where Phase-1 did not?

<details><summary>Answer</summary>

Because it forces two independent tests — one for "returns the requested amount" (AC-1) and one for "never below zero" (AC-2) — to both pass in the same run, and a spec whose two acceptance criteria cannot be jointly satisfied makes that impossible: the loop never goes green, so it blocks, instead of leaving a single actor free to silently resolve the contradiction by reinterpretation.

</details>

**Q8.** How does the seeded defect in `harness/evals/seeded-defects/contradiction-rfc.md` illustrate the same "closed lane" failure as e2e-08, in a completely different subsystem?

<details><summary>Answer</summary>

The seeded RFC asserts "nightly batch, not real-time" in its Proposal section and "within 5 seconds… real-time stream processor… sub-second alerting" in its System constraints section. A rubric scoring one section in isolation (one "lane") would never see the contradiction; ADR-0013's `rfc_consistency` dimension is required to specifically cross-check sections against each other, the same cross-boundary read e2e-08's Phase-1 gate lacked.

</details>

**Q9.** What are the two concrete numbers in §3.10.8 that make "executable evidence beats structural evidence" a measured claim rather than an opinion?

<details><summary>Answer</summary>

94 green (structural) tests in F1 caught zero instances of the real permission-denied write failure that one executed run caught on its first try; and in the same batch, every one of the ten stages that e2e-08 passed through reported success structurally, while only the executed run's actual output revealed the spec was logically impossible.

</details>

**Q10.** Why does this file call 3.10.8 "not a new incident" rather than a fifth law alongside 3.10.5–3.10.7?

<details><summary>Answer</summary>

Its leaf text is tagged `[NUM]`, not `[INCIDENT]`, and it restates the evidence-ranking already built as D-91 in the previous file rather than introducing a new "what broke / what it cost / the fix" narrative of its own — it supplies two additional real data points for that existing ranking instead of a fourth sibling law.

</details>

## Open questions

None.

---

**Leaves covered:** 3.10.5–3.10.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-91 and D-92 in the previous file rank the evidence and tell the NUL-byte story, and D-93 in the next draws the review-capacity ceiling
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 453
