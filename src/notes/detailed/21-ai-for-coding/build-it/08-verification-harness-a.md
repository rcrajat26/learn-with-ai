# 21 AI for Coding — a verification harness — BUILD IT (§4.7.1–4.7.2)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [publishing, the version bump, and the diff against the real one](07-a-plugin-b.md) · Next: [re-running the listings, and where each gate belongs](08-verification-harness-b.md)

Everything built across `01-a-claude-folder-a.md` through `07-a-plugin-b.md` — a `.claude` folder,
four hooks, four skills, three agents, a Java 21 `ClaudeRunner`, a versioned plugin in a real
marketplace — is only as trustworthy as the thing that checks it. §0.1.8 opened this whole guide
with the claim everything since has applied: **fluency is worthless as a correctness signal.** D-91,
in `verification/03-internals-a-evidence-and-the-nul-byte.md`, ranked the evidence a reviewer can
have, and put **the agent's own claim of success at the bottom** — weakest, not because agents lie,
but because the claim and the artefact come from the same ungrounded process. This file builds the
thing one step above that: a script.

## Concept — `verify.sh`, and why a shell script outranks a model's opinion of its own output

**Concept.** `verify.sh` is a shell gate over this note set's own Markdown files under
`src/notes/detailed/21-ai-for-coding/`: it asserts every target file is genuinely text before
touching it, then runs structural checks against the files that survive that assertion.

**Why it exists.** A note-generation pipeline that asks a model "does this file meet the contract?"
is asking the same kind of question `verification/03-internals-a-evidence-and-the-nul-byte.md`'s
§3.10.1 already disqualified: a fluency check, not a correctness check. A model asked to grade its
own footer format will produce a fluent, plausible "yes" whether or not the footer is actually
present, because emitting the grade and emitting the file are the same ungrounded process. A shell
script that greps for the literal footer string either finds it or it doesn't — the check is
independent of the thing being checked, which is the one property `verification/03-internals-b-the-sibling-laws.md`
names as the recurring failure's remedy: **the check must assert its own preconditions and fail
loudly when it cannot run**, rather than degrade to a green that means nothing.

**When to reach for it, and when not.** A shell gate is the right tool for anything mechanically
checkable against the file's own text: does the required header line exist, does the footer carry
`**Leaves covered:**`, is `## Open questions` present. It is the *wrong* tool for anything requiring
judgment — whether a `[STAFF]` extension is actually pitched at L6, whether a Java example is
idiomatic — because those questions have no string to grep for. That is `92-interview-internals.md`'s
job (a human or a judge-rubric reviewer, not a shell script), not this file's.

**How it works.** Gate 1 asks `file --mime-encoding` whether a target is text-like at all, before any
`grep`-based check runs against it. Gate 2 runs the structural checks — required header/footer lines,
required closing sections — against every file gate 1 passed. Gate 3, re-running every fenced
listing in a file and diffing it against the printed output, is built in the next file,
`08-verification-harness-b.md` (§4.7.3–4.7.4), alongside the decision of which gates run in the
`Stop` hook and which run in CI. D-99 draws that three-gate order end to end so the boundary between
this file and the next is visible on the page, not just stated in prose.

![D-99 — `verify.sh` gate order](../diagrams/D-99-verify-sh-gate-order.svg)

**D-99** — `verify.sh` gate order. Text-ness is gate 1 because a check that cannot run reports the
same green as one that passed.

**Code.** The complete script is built and proved below (§4.7.1). **Gotcha.** Named in that section's
own Pitfall — the gate order is not stylistic; reversing it (structural checks first, text-ness
second) reopens exactly the NUL-byte failure this file exists to close.

> `verify.sh` is a shell script that asserts every target file is text before it greps it, then
> checks each one against this note set's structural contract, exiting non-zero the instant any
> file fails either check.

## §4.7.1 — The complete artefact: gates 1 and 2, and their failure posture `[BUILD]`

**The artefact, real, complete, run for real under `/tmp/21-verify-harness-demo`, never inside a
repository:**

```bash
#!/usr/bin/env bash
# verify.sh -- Gate 1 (text-ness) then Gate 2 (structural checks) over this note
# set's own Markdown files. Gate 3 (re-running every fenced listing) and the
# Stop-hook-vs-CI split belong to 08-verification-harness-b.md (§4.7.3-4.7.4).
#
# Failure posture, stated explicitly (never leave this implicit):
#   - NOT `set -e`. This gate's whole job is to enumerate every violation across
#     every file in one run. Under `set -e`, a single unexpected non-zero from
#     `file` or a command substitution assigned to a variable can abort the
#     script after file #1, silently hiding every later file's result behind
#     a single early exit -- exactly the "check whose success is
#     indistinguishable from its absence" failure this whole file is about.
#   - `set -uo pipefail` IS used: an unset variable (a typo'd flag, a caller
#     forgetting the directory argument) is a bug in the gate itself and should
#     abort loudly and immediately, which is a different class of failure from
#     "gate 2 found a violation in file 7."
#   - Every violation increments `fail_count`; the script exits non-zero iff
#     `fail_count > 0`, once, at the very end, after every file has been checked.
set -uo pipefail

target_dir="${1:?usage: verify.sh <directory-of-.md-files>}"
fail_count=0

log_fail() {
  echo "FAIL: $1" >&2
  fail_count=$((fail_count + 1))
}

# ---- Gate 1: text-ness, before ANY grep-based check touches file content ----
# Rationale: grep in default mode exits 1 with zero stdout on a file `file(1)`
# classifies as binary -- not a mismatch, nothing -- so a gate that skips this
# assertion reports the same green on an unchecked file as on a checked one.
while IFS= read -r -d '' f; do
  encoding="$(file --brief --mime-encoding "$f")"
  if [ "$encoding" = "binary" ]; then
    log_fail "gate1-textness: '$f' reports mime-encoding 'binary' -- refusing to grep it. A grep-based gate silently exits 1 with zero stdout on binary content; that looks identical to 'checked, found nothing' unless gate 1 catches it first."
  fi
done < <(find "$target_dir" -name '*.md' -print0)

# ---- Gate 2: structural checks, only on files that survived gate 1 ----
while IFS= read -r -d '' f; do
  encoding="$(file --brief --mime-encoding "$f")"
  [ "$encoding" = "binary" ] && continue   # already failed at gate 1; do not double-count

  grep -q '^\*\*Leaves covered:\*\*' "$f" \
    || log_fail "gate2-footer: '$f' missing required '**Leaves covered:**' footer line"

  grep -q '^## Open questions' "$f" \
    || log_fail "gate2-open-questions: '$f' missing required '## Open questions' section"

  grep -q '^\*\*Target version: Claude Code v2\.1\.2xx' "$f" \
    || log_fail "gate2-header: '$f' missing required version header line"
done < <(find "$target_dir" -name '*.md' -print0)

file_count="$(find "$target_dir" -name '*.md' | wc -l | tr -d ' ')"
echo "verify.sh: ${fail_count} failure(s) across ${file_count} file(s)"

[ "$fail_count" -gt 0 ] && exit 1
exit 0
```

**Why `set +e`/`set -e` cut where they cut, stated once more, concretely.** A gate that must report
*all* failures cannot die on the first one — `set -e` on a script iterating 40+ note files would turn
"file #3 is missing its footer" into "the run stopped after file #3 and files #4 through #40 were
never checked," which is silently indistinguishable, to a reader glancing at a non-zero exit code,
from "every file after #3 also failed." `set -uo pipefail` stays on because an *unset variable* is a
bug in the gate's own invocation (a missing argument, a typo'd flag name), not a finding about the
files under test, and that class of failure should abort immediately rather than produce a
misleading partial report.

**Prove step 1 — a passing input.** Built under `/tmp/21-verify-harness-demo/pass-set/day-sample.md`,
a file carrying every required marker:

```
$ ./verify.sh pass-set
verify.sh: 0 failure(s) across 1 file(s)
$ echo "exit=$?"
exit=0
```

**Prove step 2 — a failing input**, `/tmp/21-verify-harness-demo/fail-set/day-sample.md`, a file with
its header intact but its footer and `## Open questions` section deliberately removed:

```
$ ./verify.sh fail-set
FAIL: gate2-footer: 'fail-set/day-sample.md' missing required '**Leaves covered:**' footer line
FAIL: gate2-open-questions: 'fail-set/day-sample.md' missing required '## Open questions' section
verify.sh: 2 failure(s) across 1 file(s)
$ echo "exit=$?"
exit=1
```

Both violations are reported in the same run, from the same invocation — the direct payoff of not
using `set -e`: a single pass caught two independent defects in the one file instead of stopping
after the first `grep -q` failure.

**What this costs.** Every run above completed in **well under one second of wall clock**
(`0.32s`, `0.10s`, `0.06s` total across the three timed runs on this machine, per `time`) and spent
**zero tokens** — no `claude` invocation, no model call, appears anywhere in this script. That is the
entire argument for putting this class of check in a script rather than asking a model to grade its
own output: a model grading a footer format costs a real API call, is subject to the same fluency
problem this file opened with, and is slower than the mechanical check by roughly three orders of
magnitude. Where the check *can* be reduced to a string match, doing so is strictly dominant — faster,
free, and, unlike a model's opinion, either right or wrong with no room for a plausible-sounding
wrong answer.

## §4.7.2 — Deliberate failure: the NUL-byte case, made to fail loudly rather than skip `[BUILD]` `[PROVE]`

`verification/03-internals-a-evidence-and-the-nul-byte.md`'s §3.10.3 told this incident in full: a
generated file carried a literal NUL byte (`\x00`), `file` reported it as `data`, and a bare
`grep`-based gate exited `1` with **zero stdout** — not a mismatch, nothing — so every downstream
consumer checking only the exit code read that silence as "ran cleanly, found no violation." That is
this leaf's deliberate failure: make a file that defeats grep the same way, run `verify.sh` against
it, and confirm gate 1 catches it loudly instead of gate 2 silently reporting a clean pass over a
file it never actually inspected.

**The file, built for real, under `/tmp/21-verify-harness-demo/nul-set/`:**

```
$ printf '# 21 AI for Coding -- sample note\n\n**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6**\n\nresult: 47/47 checks passing\x00 trailing bytes after the NUL\n' \
  > nul-set/nul-byte-sample.md
$ file --brief --mime-encoding nul-set/nul-byte-sample.md
binary
```

**Sanity check — what a bare grep-based gate, with no gate 1, would have reported on this exact
file**, reproducing the incident's own silence before showing the fix:

```
$ grep -q '^\*\*Leaves covered:\*\*' nul-set/nul-byte-sample.md
$ echo "exit=$?"
exit=1
```

Exit `1`, zero stdout, no error, no warning about binary content — indistinguishable, to a caller
checking only the exit code, from "ran cleanly and found the pattern absent because the file is
genuinely missing its footer" rather than "declined to inspect the content at all." That is the
defect §3.10.3 named; the file above reproduces it fresh, on this machine, rather than citing the
earlier file's numbers secondhand.

**Prove step — `verify.sh` against the same file, gate 1 first:**

```
$ ./verify.sh nul-set
FAIL: gate1-textness: 'nul-set/nul-byte-sample.md' reports mime-encoding 'binary' -- refusing to grep it. A grep-based gate silently exits 1 with zero stdout on binary content; that looks identical to 'checked, found nothing' unless gate 1 catches it first.
verify.sh: 1 failure(s) across 1 file(s)
$ echo "exit=$?"
exit=1
```

Gate 1 fires **before** gate 2 ever calls `grep` on this file — the `continue` inside gate 1's loop
means gate 2's structural checks are skipped for this file entirely, so the run never gets the chance
to report a false clean pass over content it could not read. This is the difference between a check
that fails closed (loud, named, non-zero, and correct about *why*) and one that fails open (silent,
green, and wrong about what it means): the NUL-byte file above produces exactly one `FAIL` line, not
zero, and the reader is told the specific reason — `binary` mime-encoding — rather than left to
wonder why a footer check came back clean on a file that plainly has no `## Open questions` section
at all.

**What this costs.** The NUL-byte run completed in **0.06 seconds** of wall clock and, as with §4.7.1,
**zero tokens** — the deliberate-failure proof costs exactly the same near-nothing as the
passing-input proof, because both are the same script running the same gates; the only difference is
which branch of gate 1 fires.

**Pitfall:** the wrong belief is "gate order doesn't matter, as long as both checks eventually run."
**Symptom:** running the structural checks (gate 2) *before* the text-ness assertion (gate 1) on this
exact NUL-byte file reproduces the incident precisely — `grep -q` against the binary content exits
`1`, `log_fail` fires for the *wrong reason* ("missing footer," when the real problem is "this file
was never actually readable"), and if that grep had instead been guarding a *required-absence* check
(fail if a forbidden pattern is found) the same binary content would have produced a **false pass**
indistinguishable from a genuinely clean file. **Fix:** assert text-ness first, unconditionally,
before any other check is allowed to run against a file's content — exactly the order D-99 draws and
`verify.sh` enforces with its `continue` on a binary verdict. **Why people believe it:** grep's own
documented contract only describes its behaviour on text; nothing in a quick read of `man grep`
warns that binary input degrades to silent, unflagged non-matching rather than an error.

## Portability

Every command above ran on **macOS (Darwin 25.5.0), `file-5.41`, `bash 3.2.57`** — the same platform
where an earlier file in this set (`plugins/*`) already found that `grep -P` is unavailable and
`sed -i` takes a mandatory backup-suffix argument that GNU's does not. `verify.sh` avoids both traps
deliberately: it uses no `-P`/PCRE flag on `grep` (every pattern above is a plain basic/extended
literal or anchor, portable to BSD grep, GNU grep, and the `ugrep`-aliased binary this machine
actually runs), and it never calls `sed -i` at all. `find … -print0` paired with `bash`'s `read -r -d
''` is supported by both BSD `find`/`bash 3.2` (as run here) and GNU `find`/any modern `bash`, so no
Homebrew prerequisite is needed for this particular script.

**Pitfall:** the wrong belief is "if a shell gate ran clean on my machine, it will run clean in CI."
**Symptom:** a gate written and tested only on a GNU/Linux CI runner, then handed to a reader on
macOS, silently misbehaves the moment it reaches for `grep -P` (not installed by default; `brew
install grep` provides `ggrep -P` under a different binary name) or `sed -i 's/x/y/'` without a
suffix argument (GNU accepts this; BSD/macOS `sed -i` requires `sed -i '' 's/x/y/'` or errors).
**Fix:** for this script specifically, both traps are avoided by construction — no `-P`, no `-i` —
and that avoidance is a deliberate choice, not an accident, precisely so the artefact is copy-pasteable
on either platform without a prerequisite install. **Why people believe it:** most engineers' daily
shell is whichever platform they carry, and `grep -P`/`sed -i` differences only surface the first time
the same script is run somewhere else.

## Pitfalls

- **Belief:** "a verification script that checks everything it's supposed to is thereby a good gate."
  **Surprising outcome:** a script that runs structural checks before asserting text-ness reports a
  clean, specific-sounding failure reason ("missing footer") on a file it never actually managed to
  read, which is worse than an honest "cannot check this file" because it actively misdirects the
  fix. **What actually gets the guarantee:** assert every precondition a later check silently assumes
  — here, "this file is text" — before that later check is allowed to run, and make the precondition
  failure a distinct, named `FAIL` line rather than folding it into whatever the next check happens to
  report. **Why people believe it:** the two failure modes ("missing footer" vs "not text at all")
  both print a `FAIL` line and both exit non-zero, so a glance at the output looks equally
  informative either way, and only running the NUL-byte case specifically exposes the difference.
- **Belief:** "`set -e` is always the safer default for a shell script." **Surprising outcome:** on a
  gate whose job is to enumerate every violation across many files, `set -e` turns the *first*
  unexpected non-zero exit anywhere in the loop into a silent early stop — every file after the one
  that tripped it is never checked, and nothing in the exit code distinguishes "one failure found,
  all files checked" from "the third file's `file` invocation hiccuped and everything after it was
  skipped." **What actually gets the guarantee:** count failures explicitly in a variable, keep
  iterating regardless, and check the count once at the very end — exactly `verify.sh`'s own
  `fail_count` pattern. **Why people believe it:** `set -e` is the textbook default for "fail fast and
  don't proceed on a broken assumption," which is the right posture for a build step, but is the
  wrong posture for a gate whose entire value is completeness of its own report.

## Cheat sheet

| Item | Value |
|---|---|
| Script | `verify.sh <directory-of-.md-files>` |
| Gate 1 | `file --brief --mime-encoding "$f"` equals `binary` → `log_fail`, `continue` (skip gate 2 for this file) |
| Gate 2 | `grep -q` for required header line, required footer line, required `## Open questions` section |
| Gate 3 | Built in `08-verification-harness-b.md` (§4.7.3–4.7.4) — re-run every fenced listing, diff against printed output |
| Failure posture | `set -uo pipefail`, deliberately **not** `set -e`; `fail_count` accumulated, checked once at the end |
| Pass-set run | `0 failure(s)`, exit `0`, `0.32s` wall clock, $0 |
| Fail-set run | `2 failure(s)` (footer + open-questions), exit `1`, both reported in one run |
| NUL-byte run | `1 failure(s)` — `gate1-textness`, exit `1`, gate 2 never touches the file |
| Cost | $0, sub-second wall clock, per run — the argument for a script over a model grading its own output |
| Portability traps avoided | No `grep -P` (uses only basic/extended patterns); no `sed -i` (not called at all) |

## Self-test

**Q1.** Why does `verify.sh` use `set -uo pipefail` but deliberately not `set -e`?

<details><summary>Answer</summary>

`set -uo pipefail` catches a bug in the gate's own invocation — an unset variable such as a missing directory argument — which should abort immediately. `set -e` is deliberately omitted because the gate's job is to enumerate every violation across every file in one run; under `set -e`, the first unexpected non-zero exit anywhere in the loop would silently stop the script, leaving every later file unchecked with no distinguishing signal in the exit code.

</details>

**Q2.** What exact exit code and stdout did a bare `grep -q` produce against the NUL-byte file, reproduced fresh in this leaf?

<details><summary>Answer</summary>

Exit code `1` with zero stdout — no error, no warning about binary content, no partial match. That is indistinguishable, to a caller checking only the exit code, from "ran cleanly and found the pattern genuinely absent."

</details>

**Q3.** Why does gate 1's loop use `continue` when it finds a binary file, and what would go wrong without it?

<details><summary>Answer</summary>

`continue` skips gate 2's structural checks for that specific file after gate 1 has already logged the real failure. Without it, gate 2 would still run `grep -q` against the binary content, which would silently fail (exit 1, no match) and get logged as "missing footer" or "missing Open questions" — a misleading, specific-sounding wrong reason instead of the true one, "this file was never actually readable."

</details>

**Q4.** Name the two shell portability traps this script avoids by construction, and what each one breaks on macOS if used carelessly.

<details><summary>Answer</summary>

`grep -P` (PCRE mode) is not available in macOS's default `grep`/`ugrep` binary the way it is on GNU/Linux without a separate install. `sed -i 's/x/y/'` (no suffix argument) works on GNU `sed` but errors on BSD/macOS `sed`, which requires an explicit (even empty) backup-suffix argument. `verify.sh` uses neither, so it needs no Homebrew prerequisite to run identically on both platforms.

</details>

**Q5.** What does "what this costs" actually measure for `verify.sh`, and why is that the argument for using a script rather than asking a model to grade the same files?

<details><summary>Answer</summary>

It measures wall-clock time (sub-second across every run — 0.32s, 0.10s, 0.06s) and token cost (zero, since no `claude` invocation appears anywhere in the script). That is the argument for a script: a model asked to grade a footer format would cost a real API call, would be subject to the same fluency-over-correctness problem this file opened with, and would be orders of magnitude slower than a string match that is either right or wrong with no room for a plausible-sounding wrong answer.

</details>

**Q6.** Per the Pitfall on gate ordering, what would happen if a required-*absence* check (fail if a forbidden pattern is found) ran against the NUL-byte file before gate 1?

<details><summary>Answer</summary>

`grep -q` for the forbidden pattern would exit `1` (pattern not found) on the binary content regardless of whether the forbidden pattern was actually present, because grep in default mode declines to inspect binary content past deciding "this looks binary." A required-absence check reads that as a pass — a false pass indistinguishable from a genuinely clean file, which is strictly worse than the required-presence case in this leaf because nothing about the output even looks like a failure.

</details>

## Open questions

None.

---

**Leaves covered:** 4.7.1–4.7.2 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-99
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 361
