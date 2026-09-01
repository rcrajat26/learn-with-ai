# 21 AI for Coding — injection, and the diff against the real one — BUILD IT (§4.3.4–4.3.6)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [a skill and a command](03-a-skill-and-a-command-a.md) · Next: [two subagents](04-two-subagents-a.md)

`build-it/03-a-skill-and-a-command-a.md` shipped four skills for `invoice-ledger-service`, all under
`/tmp/21-skills-scratch/invoice-ledger-service` — a real git checkout with one committed file and one
uncommitted edit. This file extends that same checkout, adds three more skills, and does not rebuild or
rename any of the earlier four (`checklist-refresh`, its bare-command twin, `post-invoice-reversal`,
`money-minor-units-conventions`). The nested-`claude`-invocation blocker that file recorded — a live
session refusing to run inside this writing task — applies here too; where it recurs, this file quotes
the same refusal rather than inventing a transcript, and records the gap in `## Open questions`.

## §4.3.4 — a `paths`-gated skill that activates only for `**/*.java` `[BUILD]` `[JAVA]` `[PROVE]`

**Concept.** Every skill so far in this set fires because someone typed its name or because Claude
matched its `description` against a request. `paths` is a third trigger: a skill that Claude Code
"loads... automatically only when working with files matching the patterns" (`skills`, frontmatter
reference table), with no typing and no description-matching decision involved at all — the file
itself is the trigger.

**Why it exists.** `checklist-refresh` (§4.3.1) answers "is this diff ready to review" — a question
asked once, deliberately, before opening a pull request. Nothing in this project enforces
`checklist-full.md`'s record-shape rules (items 1 and 4) at the moment a `.java` file is actually being
written, which is the moment a wrong shape is cheapest to catch. Waiting for `checklist-refresh` to run
later means the wrong shape has already been typed, reviewed against, and possibly committed.

**How it works.** The `paths` field "accepts a comma-separated string or a YAML list… uses the same
format as path-specific rules" (`skills`, frontmatter reference table) — the glob table documented for
`.claude/rules/*.md` on the `memory` page: `**/*.ts` matches "all TypeScript files in any directory,"
`src/**/*` matches "all files under `src/` directory." The pattern here, `**/*.java`, has the identical
shape scoped to the other extension. `memory` additionally states, for a path-scoped *rule*, that
"path-scoped rules trigger when Claude reads files matching the pattern, not on every tool use" — this
guide has not found the equivalent sentence written for a `paths`-gated *skill* specifically, so this
file treats the timing claim as **Unverified** for skills rather than asserting the rules-page wording
carries over unchanged (recorded in `## Open questions`).

**D-36** through **D-40** (the standing-cost-vs-body-cost distinction, the injection-column-position
trap, and neighbouring skill-mechanism diagrams) live in the `skills/` folder of this note set and are
not repeated here — this row's manifest carries no diagram of its own.

**The artefact**, complete:

```yaml
---
name: record-boundary-guard
description: Enforce invoice-ledger-service's two record-shape rules on every Java file Claude touches, not only at review time -- a class crossing the REST boundary must be a record, and a JPA @Entity must stay a plain class. Fires automatically while editing Java source.
paths: "**/*.java"
---

## Your task

A `.java` file is in view. Before writing or editing it, check which of these two rules it is
subject to, and only that one:

1. If the class is a request body, a response body, or a query-parameter bundle crossing the REST
   boundary in `invoice-ledger-api` — it must be a Java 21 `record`. A hand-written getter class or
   a Lombok `@Data` class fails this rule.
2. If the class carries `@Entity` in `invoice-ledger-persistence` — it must stay a plain class,
   never a `record`. Hibernate's lazy-proxy subclassing cannot subclass a `record` (`record` types are
   implicitly `final`), so an entity written as a `record` fails to load at runtime even though it
   compiles.

A class that is neither — an internal service-layer type, a mapper, a test fixture — is not subject
to either rule; say nothing about record shape for it.
```

**`[JAVA]`** — the two shapes this skill exists to keep apart, real and compiling, committed into the
scratch checkout at the paths a real reviewer would expect:

`invoice-ledger-persistence/src/main/java/LedgerEntry.java` — a plain class, correct:

```java
@Entity
public class LedgerEntry {

    @Id
    @GeneratedValue
    private Long id;

    private long amountMinorUnits;
    private String currencyCode;
    private Long reversalOf;

    protected LedgerEntry() {
        // required by Hibernate's proxy generator
    }

    public LedgerEntry(long amountMinorUnits, String currencyCode, Long reversalOf) {
        this.amountMinorUnits = amountMinorUnits;
        this.currencyCode = currencyCode;
        this.reversalOf = reversalOf;
    }

    public Long getId() { return id; }
    public long getAmountMinorUnits() { return amountMinorUnits; }
    public String getCurrencyCode() { return currencyCode; }
    public Long getReversalOf() { return reversalOf; }
}
```

`invoice-ledger-api/src/main/java/ReversalRequest.java` — a record at the API boundary, correct:

```java
public record ReversalRequest(String invoiceId, String reason) {

    public ReversalRequest {
        if (invoiceId == null || invoiceId.isBlank()) {
            throw new IllegalArgumentException("invoiceId must not be blank");
        }
    }
}
```

**Where the analogy would break if `LedgerEntry` were written as a `record LedgerEntry(...)` instead:**
it still compiles — a `record` is a legal top-level class and `@Entity` places no restriction the
compiler enforces. It breaks at runtime, the first time Hibernate needs a lazy proxy for a
`@ManyToOne`/`@OneToMany` reference to it: proxy generation subclasses the entity, and a `record` is
implicitly `final` (JLS record classes are always final), so there is no subclass to generate. The
failure surfaces as a `HibernateException` at first lazy access, not at `./mvnw compile` — exactly the
gap `checklist-full.md` item 4 exists to catch before the build even attempts it, and exactly the gap
this `paths`-gated skill exists to catch before `checklist-full.md` is ever consulted.

**Prove step.** `[PROVE]` The pattern this skill's frontmatter carries, matched by hand against real
paths in the scratch checkout rather than assumed to work, using the same suffix rule the field
documents:

```
$ bash -c '
paths=(
  "invoice-ledger-api/src/main/java/Dummy.java"
  "invoice-ledger-api/src/main/java/ReversalRequest.java"
  "invoice-ledger-persistence/src/main/java/LedgerEntry.java"
  ".claude/skills/checklist-refresh/references/checklist-full.md"
  ".claude/skills/record-boundary-guard/SKILL.md"
)
for p in "${paths[@]}"; do
  case "$p" in
    *.java) echo "MATCH   $p" ;;
    *)      echo "NO MATCH $p" ;;
  esac
done
'
MATCH   invoice-ledger-api/src/main/java/Dummy.java
MATCH   invoice-ledger-api/src/main/java/ReversalRequest.java
MATCH   invoice-ledger-persistence/src/main/java/LedgerEntry.java
NO MATCH .claude/skills/checklist-refresh/references/checklist-full.md
NO MATCH .claude/skills/record-boundary-guard/SKILL.md
```

The three real `.java` files this checkout now holds match; the skill's own reference file and its own
`SKILL.md` — both Markdown, both under `.claude/`, exactly the sort of file a careless pattern would
accidentally sweep in — do not. What this step cannot drive is Claude Code actually loading
`record-boundary-guard` the moment one of those `.java` files is opened in a live session — the same
class of live-invocation gap §4.3.1 and §4.3.3 hit, for the same underlying reason: a nested `claude`
invocation from inside this writing task is refused —

```
Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by
classifier.
```

**Unverified:** live automatic activation of `record-boundary-guard` on a matching file was not
observed directly; the pattern-match logic above is directly executed and directly observed. Recorded
in `## Open questions`.

**Gotcha.** A skill's `paths` match is evaluated against the file Claude is about to read or edit, not
against every tool call in the turn — a `Bash(./mvnw test)` invocation that happens to touch `.java`
files only through the compiler, with no `Read`/`Edit` tool call naming a `.java` path directly, is not
established by the documentation fetched for this file to trigger the match. Treat `paths` as a
file-tool gate, not a topic gate.

> A `paths`-gated skill has no `description` for Claude to reason about and no name for a user to type
> — the file the tool is about to touch is the entire activation condition.

**What this costs — two numbers, kept separate.** Standing listing cost: `name` (21 characters) plus
`description` (260 characters) is 281 characters ≈70 tokens, resident every turn this skill is
discoverable at all — and per the mechanism above, "discoverable" here may mean "resident only while a
matching file is in view" rather than every turn regardless, which this file cannot verify further
without the live session. One-off body cost, paid the turn it actually fires:

```
$ wc -c .claude/skills/record-boundary-guard/SKILL.md
1186 .claude/skills/record-boundary-guard/SKILL.md
```

≈297 tokens, once, the turn a matching file triggers it.

## §4.3.5 — a composed pair: a thin wrapper skill and a shared executor `[BUILD]`

**Concept.** Two skills can compose the same way `/implement-story` composes with `/run-conductor` in
the sdlc-harness: a thin wrapper's body opens with a fenced `` ```! `` block that runs a shell command
whose output is the *entire rendered body* of another file, then adds a short "the only things this
wrapper adds" section rather than repeating the shared procedure.

**Why it exists.** `mvn-test-runner` (`build-it/01`) runs the fast test loop for one module.
`checklist-refresh` (§4.3.1) reviews a diff. Neither answers "is the whole project, as a unit, ready to
tag as a release candidate" — full `verify` across every module, plus a clean working tree. That
procedure and the plain per-module `verify` procedure share almost everything; writing them as two
independent skill bodies would duplicate the executor logic and let the two drift.

**How it works.** `` !`command` `` "runs shell commands before the skill content is sent to Claude…
[s]ubstitution runs once over the original file… inserted as plain text and is not re-scanned for
further placeholders" (`skills`, Inject dynamic context). For a multi-line command "use a fenced code
block opened with `` ```! `` instead of the inline form" (`skills`, same section) — exactly the form
`/implement-story` in sdlc-harness uses to pull in `run-conductor.md` wholesale:

```
```!
cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"
```
```

(`plugins/sdlc-harness/commands/implement-story.md`, quoted verbatim above — the block that follows the
line "Arguments: $ARGUMENTS"). The composed pair below is the same mechanism, `${CLAUDE_PROJECT_DIR}`
in place of `${CLAUDE_PLUGIN_ROOT}` because these are project skills, not plugin skills.

**The two artefacts**, complete. The executor:

```yaml
---
name: mvn-verify-executor
description: Run the full Maven verify lifecycle (compile, test, ArchUnit rules, packaging) for one module of invoice-ledger-service and report the real result. The shared procedure other skills in this project bind to a fixed module rather than re-implementing.
argument-hint: <module-name>
allowed-tools: Bash(./mvnw -q verify -pl *)
---

## Your task

1. Run `./mvnw -q verify -pl $ARGUMENTS` and capture the real exit code and output.
2. If it exits non-zero, report FAILED, quote the first failing line from the output, and stop —
   do not report the module as verified.
3. If it exits zero, report VERIFIED for `$ARGUMENTS`, naming the module.

This skill knows nothing about which module matters more than another, and nothing about what
happens after verification succeeds or fails — that judgment belongs to whatever invokes it.
```

The wrapper — its body carries only the injection and the overrides, per the concept above:

```yaml
---
name: release-candidate-check
description: Confirm invoice-ledger-service's own root module is ready to tag as a release candidate -- full verify passes and the working tree is clean. Use when the user asks to cut a release candidate or check release readiness.
allowed-tools: Bash(git status --porcelain)
---

## Executor

```!
cat "${CLAUDE_PROJECT_DIR}/.claude/skills/mvn-verify-executor/SKILL.md"
```

## Binding overrides (the ONLY things this wrapper adds over the executor spec above)

- The module is FIXED to `invoice-ledger-service`, the parent aggregator — running `verify` there
  builds and tests every child module in one pass. Ignore the executor's `$ARGUMENTS` placeholder
  entirely; there is no module name to select here, and none is read from this skill's own
  invocation text.
- After the executor reports VERIFIED, run one additional check the executor does not perform:

```!
git status --porcelain
```

  A non-empty result means uncommitted changes exist. Report NOT A RELEASE CANDIDATE and list the
  changed paths — a release candidate is cut from a clean tree, verified or not.
- Only when the executor reports VERIFIED **and** the working tree is clean, report RELEASE
  CANDIDATE READY.
```

**Prove step.** Both injected commands, run directly against the real scratch checkout to show the
exact text each `` ```! `` block would splice in — the executor's block splices in the entire other
file, byte for byte:

```
$ cat "${CLAUDE_PROJECT_DIR}/.claude/skills/mvn-verify-executor/SKILL.md"
---
name: mvn-verify-executor
description: Run the full Maven verify lifecycle (compile, test, ArchUnit rules, packaging) for one module of invoice-ledger-service and report the real result. The shared procedure other skills in this project bind to a fixed module rather than re-implementing.
argument-hint: <module-name>
allowed-tools: Bash(./mvnw -q verify -pl *)
---
[... full body, identical to the artefact above ...]
```

and the second block, run against this checkout's actual state:

```
$ git status --porcelain
 M invoice-ledger-api/src/main/java/Dummy.java
?? .claude/
?? invoice-ledger-api/src/main/java/ReversalRequest.java
?? invoice-ledger-persistence/
```

Non-empty — this checkout, as built across both files in this note set, is not a release candidate by
`release-candidate-check`'s own rule regardless of whether `verify` passes, which is the predictable
output a reader can check their own copy against.

**What this costs — two numbers, and a third that only a composed pair has.** Standing listing cost is
paid **twice**, not once: `release-candidate-check` lists at 241 characters (`name` 23 + `description`
218) ≈60 tokens, and `mvn-verify-executor` lists **separately**, at 268 characters ≈67 tokens, because
it remains its own independently invocable skill — composing two skills costs two listing entries every
turn, not one, even though only one of them is ever invoked directly for this workflow. One-off cost on
the file actually written to disk:

```
$ wc -c .claude/skills/release-candidate-check/SKILL.md .claude/skills/mvn-verify-executor/SKILL.md
    1226 .claude/skills/release-candidate-check/SKILL.md
     873 .claude/skills/mvn-verify-executor/SKILL.md
```

But the *rendered* content Claude actually receives the turn `release-candidate-check` fires is neither
of those numbers — the injection unconditionally splices the executor's 873 bytes into the wrapper's
1,226, in place of the fenced block, producing 2,019 bytes ≈505 tokens every single time the wrapper
runs. This is the sharpest difference from `references/checklist-full.md` in §4.3.1: a `references/`
file is *conditional* — read only if the skill's own body tells Claude to read it, on a turn the body
decides. A `` ```! `` injection is *unconditional* — every firing pays the full spliced size, with no
lazier path available; composing two skills this way buys shared authorship, not a shared cost.

No gotcha beyond §4.3.1's injection-column-position trap, which applies identically to both `` ```! ``
blocks here.

## §4.3.6 — Diff vs the real one

The composed pair above (§4.3.5) is this repository's version of the exact pattern
`plugins/sdlc-harness/commands/implement-story.md` and `plugins/sdlc-harness/skills/bootstrap/SKILL.md`
both use in the real sdlc-harness: a thin layer that composes a shared procedure and states only its
own additions. Diffed against both real artefacts on the three properties the leaf names, plus three
more the comparison surfaces:

| Property | Yours (§4.3.5's composed pair) | The real one (`bootstrap/SKILL.md`, `/implement-story`) | Why the difference |
|---|---|---|---|
| Plan-then-confirm | Neither skill ever asks. `allowed-tools` pre-approves both Bash patterns; nothing here is a judgment call about the engineer's own disk state | `bootstrap` step 1 asks "Where should the harness workspace live?" when no clone is detected, and step 4 asks whether to link existing service clones before running anything mutating | `bootstrap`'s own gotchas say to "[r]eserve 'ask first'… for genuine judgment calls about the *engineer's own disk state* — never for 'should this dev tool be installed.'" A fixed module name and an observed `verify` exit code are not judgment calls; there is nothing here of the shape bootstrap reserves a question for |
| Delegation unit | The wrapper delegates to *another skill's prose* (`mvn-verify-executor`), read via `cat` and interpreted by the model exactly like the rest of the body | `bootstrap` delegates to *shell scripts* — fourteen `bootstrap-*.sh` files under `scripts/`, each independently testable, each returning a real exit code the skill's prose only relays | `bootstrap`'s steps each resolve a question with one correct answer given the inputs (a path, a JSON merge, a hash) — extracting that into a script removes it from model interpretation entirely. `release-candidate-check`'s two computations already reduced to a single Bash call each (`./mvnw verify`, `git status --porcelain`); there is no further judgment left to extract into a script, so composing at the skill layer costs nothing a script would have saved. **The move a reader's own skill should make once it stops applying:** the moment a wrapped step needs branching logic beyond "relay this exit code" — parsing structured output, merging two files, resolving an ambiguous path — that logic belongs in a tested script, not in more prose for the model to re-derive on every run |
| Rejected-flag handling | None. `release-candidate-check` declares no `arguments` and never writes `$ARGUMENTS` in its body; an extra argument at invocation is silently appended as literal `ARGUMENTS: <value>` text per `skills`' own substitution rule, never named or rejected | `/implement-story` explicitly rejects `--resume-at`, `--main-pipeline-id`, `--dry-run`, and `--override-pull`, "each MUST be rejected with an explicit error naming the flag — never silently ignored or reinterpreted" | `/implement-story` forwards a large flag surface from `/run-conductor` and has real, similarly-named flags from a *different* executor (`/run-harness`) that must not be silently accepted. `release-candidate-check` takes no arguments by design — the module is fixed — so there is no flag surface to police, and the honest gap is that a stray argument goes unnoticed rather than erroring loudly |
| Tool scoping | `Bash(./mvnw -q verify -pl *)` and `Bash(git status --porcelain)` — narrow patterns naming the exact commands each skill runs | `allowed-tools: [Bash, Read, AskUserQuestion]` — the unscoped tool names, no command patterns at all | `bootstrap` calls fifteen different scripts at paths not fixed until runtime (`${CLAUDE_PLUGIN_ROOT}` resolves per install, `<HARNESS_ROOT from step 1>` resolves per engineer) — no fixed pattern could enumerate them. The composed pair's two commands are both fully known at authoring time, so narrowing costs nothing and shrinks the blast radius of an unintended Bash call during the turn |
| Recorded constants / locale pinning | None — neither skill writes a marker file or caches anything across runs; each invocation re-observes `git status --porcelain` and the `verify` exit code fresh | `bootstrap-write-version.sh` computes `LC_ALL=C cat SKILL.md scripts/bootstrap-*.sh \| sha256sum`, pinning the C locale so "collation can't vary this order across machines/locales," with a `shasum -a 256` fallback when `sha256sum` is absent, written to a workspace-scoped marker so a later `check-init.sh` run knows the workspace is current | `bootstrap`'s underlying fact — "is this workspace's tooling current with this plugin version" — is expensive to re-derive every session and must survive across sessions, so it is cached, deliberately, with a hash format stable enough to compare release to release. `release-candidate-check`'s underlying facts (working tree clean, tests pass right now) are cheap to re-observe and actively wrong to cache — a stale "clean" from a prior run is a lie the moment a new edit lands |

**Excluded, and why:** *concurrency safety* — neither system has concurrent writers in play; `bootstrap`
runs once per engineer session and the composed pair runs within a single turn, so there is no race to
compare. *Path resolution* — `bootstrap-workspace.sh` resolves an ambiguous filesystem location
(`--adopt`/`--workspace-home`) via `cd … && pwd`; the composed pair's "path" is a fixed Maven module id
known at authoring time, never resolved at runtime, so there is nothing to diff. *Write boundaries* —
`bootstrap`'s user-scope-only write (never project scope, "RFC 0002 section 6.3") is a single-repo
design property with no comparable write anywhere in the composed pair, which writes no file at all.

## Pitfalls

- **Belief:** "a `paths`-gated skill and a `description`-matched skill cost the same thing, since both
  just sit in the listing until needed." **Outcome:** both do carry the same standing listing cost
  (§4.3.4's 281 characters ride along regardless of trigger type), but the *trigger condition* differs
  in a way that changes what "until needed" means — a `description`-matched skill needs Claude to
  reason about relevance on a request with no file in view at all; a `paths`-gated skill needs no
  reasoning step, only a file-tool call against a matching path. **Fix:** read `paths` as replacing the
  relevance judgment, not the listing cost. **Why people believe it:** both fields sit in the same
  frontmatter table and both are described as "automatic," which reads as one mechanism rather than two
  different activation conditions with the same price tag.
- **Belief:** "composing two skills with a `` ```! `` injection is cheaper than writing one long skill,
  since the shared logic only exists once." **Outcome:** §4.3.5 measured the opposite on both axes that
  matter — the standing listing cost is paid twice (two entries, 241 + 268 characters) instead of once,
  and the one-off firing cost is the *sum* of both files (2,019 rendered bytes), not the smaller of the
  two. **Fix:** compose for shared authorship and drift prevention, not for a lower token bill — a
  single skill with no composition would list once and fire once, at whichever size it actually is.
  **Why people believe it:** "shared code" habits from software carry over, where extracting a common
  function usually does shrink the compiled artifact; a skill's `` ```! `` injection is a copy at
  render time, not a reference, so the analogy breaks exactly where the injection resolves.
- **Belief:** "if the real `bootstrap` skill delegates every step to a script, my own skill should too,
  or it isn't doing this properly." **Outcome:** `release-candidate-check`'s two computations already
  bottom out in a single Bash call each with no further branching logic to remove from the model's
  hands — extracting a script would save no judgment, only relocate two one-line commands. **Fix:**
  extract to a script when a step has genuine branching, parsing, or path-merging logic with one
  correct answer given the inputs; leave it in the skill's own prose when the step already reduces to
  "run this one command and relay its exit code." **Why people believe it:** `bootstrap`'s own text
  states its principle plainly enough to over-generalize — the principle is scoped to steps with real
  decision logic, not to every step regardless of how little logic it has left.

## Cheat sheet

| Item | Value |
|---|---|
| §4.3.4 skill | `record-boundary-guard` — `paths: "**/*.java"`, fires on file, not on request |
| §4.3.4 trigger doc | `skills`: "loads the skill automatically only when working with files matching the patterns"; live activation timing vs `memory`'s rules-page wording is Unverified for skills specifically |
| §4.3.4 Java break point | `record` entity compiles; fails at first Hibernate lazy-proxy access because a `record` is implicitly `final` |
| §4.3.4 costs | Listing 281 chars ≈70 tokens/turn; body 1,186 B ≈297 tokens on fire |
| §4.3.5 pair | `mvn-verify-executor` (shared, `$ARGUMENTS`-driven) + `release-candidate-check` (wrapper, fixed module, `` ```! `` injection) |
| §4.3.5 injection mechanism | `` ```! `` fenced block, same form as `/implement-story`'s `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"` |
| §4.3.5 costs | Two listings: 241 + 268 chars ≈60 + 67 tokens/turn; rendered fire cost 2,019 B ≈505 tokens — sum, not shared, unlike a `references/` file |
| §4.3.6 sharpest diff | Real one delegates to *tested scripts* (one correct answer per input); yours delegates to *another skill's prose* because nothing left needs extracting |
| §4.3.6 rejected flags | Real one names and rejects four flags explicitly; yours has none declared and silently appends a stray argument as inert text |
| §4.3.6 excluded rows | Concurrency safety, path resolution, write boundaries — no comparable mechanism on one side |
| Live-session blocker (§4.3.4, recurring) | Nested `claude` invocation refused by the auto-mode classifier — same quoted refusal as §4.3.1/§4.3.3 |

## Self-test

<details><summary>1. What activates record-boundary-guard, and what does not?</summary>
Its paths: "**/*.java" frontmatter field activates it when Claude works with a file matching that glob — verified by hand-matching real paths against the *.java suffix rule the field documents. It carries no description-based relevance judgment and no typed invocation; a request that never touches a .java file, however related to Java it sounds, is not established to trigger it by the documentation this file could verify.
</details>

<details><summary>2. Why does a record-typed @Entity compile cleanly but fail only at runtime?</summary>
Nothing in @Entity's contract is checked by javac — the annotation only matters to Hibernate at runtime. The actual failure happens the first time Hibernate needs a lazy-loading proxy for a reference to that entity: proxy generation subclasses the entity class, and a Java record is implicitly final, so there is no subclass to generate. The compiler has no opinion on finality-vs-proxying; only the ORM does, and only when it actually tries.
</details>

<details><summary>3. In the composed pair, why is mvn-verify-executor's standing listing cost paid even on a turn that only invokes release-candidate-check?</summary>
mvn-verify-executor remains its own independently invocable skill with its own name and description in the skill listing — nothing about being cat-injected into another skill's body removes it from that listing. Composing two skills this way costs two listing entries every turn, not one, regardless of which one a given turn actually fires.
</details>

<details><summary>4. Why is the rendered size of release-candidate-check larger than the file actually saved to disk?</summary>
The ```! block in its body doesn't just reference mvn-verify-executor.SKILL.md — at render time its output (the entire 873-byte file, spliced in verbatim by the cat command) replaces the fenced block. The 1,226 bytes on disk therefore become roughly 2,019 rendered bytes the turn the skill fires, because the injection is unconditional: every firing re-splices the full executor body, unlike a references/ file that only loads if the skill's own steps ask for it.
</details>

<details><summary>5. Why does bootstrap/SKILL.md delegate every step to a shell script, while release-candidate-check delegates to another skill's prose instead of a script?</summary>
bootstrap's steps each resolve a question that has one correct answer given the inputs — a path to resolve, a JSON file to merge, a hash to compute — so extracting that logic into a tested script removes it from model interpretation entirely, and a script can be tested independently of any skill that calls it. release-candidate-check's two steps already reduce to a single Bash call each with no further branching left to extract; writing a wrapper script around "run ./mvnw verify" or "run git status --porcelain" would relocate one line without removing any judgment, so composing at the skill-prose layer costs nothing a script would have saved at this scale.
</details>

<details><summary>6. What happens if someone invokes /release-candidate-check with an extra argument, and how does that differ from how /implement-story handles an unsupported flag?</summary>
release-candidate-check declares no arguments field and never writes $ARGUMENTS anywhere in its body, so per skills' own substitution rule an argument with no placeholder to receive it is appended as literal "ARGUMENTS: <value>" text — silently, with no error. /implement-story instead explicitly names and rejects specific unsupported flags (--resume-at, --main-pipeline-id, --dry-run, --override-pull) with a stated error, precisely because it forwards a large flag surface from one executor while sharing flag names with a different, incompatible one. release-candidate-check has no flag surface at all by design, so the gap is a stray argument going unnoticed rather than a wrong flag being silently reinterpreted.
</details>

<details><summary>7. Why does bootstrap-write-version.sh pin LC_ALL=C when computing its hash, and why doesn't release-candidate-check need anything like it?</summary>
The hash has to match byte-for-byte between two different scripts (bootstrap-write-version.sh's writer and check-init.sh's reader) run on potentially different machines; LC_ALL=C forces the glob expansion order for scripts/bootstrap-*.sh to be stable regardless of the machine's locale/collation settings, so both sides concatenate the files in the identical order before hashing. release-candidate-check never caches or compares anything across runs or machines — it re-observes git status --porcelain and the verify exit code fresh every time — so there is no cross-run, cross-machine comparison for a locale-dependent ordering bug to threaten in the first place.
</details>

## Open questions

- **Unverified:** whether a `paths`-gated skill's standing listing cost is paid every turn regardless of
  whether a matching file is in view, or only while one is — `skills`' frontmatter table states the
  *activation* condition ("loads the skill automatically only when working with files matching the
  patterns") but this file could not confirm whether that also governs *listing* presence, and the
  `memory` page's stronger claim ("trigger when Claude reads files matching the pattern, not on every
  tool use") is documented for path-scoped CLAUDE.md rules, not for a skill's `paths` field specifically
  (§4.3.4).
- **Unverified:** live automatic activation of `record-boundary-guard` against a real `.java` file edit
  in a running Claude Code session — a nested `claude` invocation from inside this writing task was
  refused by the auto-mode classifier, the same blocker recorded in §4.3.1 and §4.3.3 of the previous
  file (§4.3.4).

---

**Leaves covered:** 4.3.4–4.3.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-36 to D-40 in the `skills/` folder draw this row's mechanisms
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 445
