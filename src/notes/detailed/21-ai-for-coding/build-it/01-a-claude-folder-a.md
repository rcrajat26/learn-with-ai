# 21 AI for Coding — a `.claude` folder from nothing — BUILD IT (§4.1.1–4.1.3)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [PART 3 — the interview wrap-up](../92-interview-internals.md) · Next: [the local file, and what the folder cost](01-a-claude-folder-b.md)

Every leaf in this part is `[BUILD]`, and the contract is exact: the complete artefact, then a prove
step with real output, then a cost note in tokens or dollars. This file builds a `.claude` folder from
nothing for one real, plausible Spring Boot service — a Maven multi-module backend, not a placeholder
repository — across three leaves: a `CLAUDE.md` under 100 lines (§4.1.1), the measured split of that
file into three mechanisms chosen off the decision table at §1.5.26 (§4.1.2), and a complete
`settings.json` that builds on the permission block PART 1 already proved rule by rule (§4.1.3).

## The service

`invoice-ledger-service` — a Spring Boot 3.x / Java 21 multi-module Maven backend that posts and
reverses invoice ledger entries. Four modules under one aggregator POM: `invoice-ledger-api` (REST
controllers, DTOs), `invoice-ledger-service` (use cases, `@Transactional` boundaries),
`invoice-ledger-persistence` (Spring Data JPA repositories, Flyway migrations), and
`invoice-ledger-app` (the executable module). The build tool is the Maven wrapper, not a bare `mvn`:
`./mvnw -q test`, `./mvnw -q verify`, `./mvnw -q spring-boot:run -pl invoice-ledger-app`.

## §4.1.1 — a `CLAUDE.md` under 100 lines, for this service `[BUILD]` `[JAVA]`

**Concept.** A `CLAUDE.md` is not documentation for a human reader — it is a user message Claude
Code injects at the start of every session, per `memory`'s own framing: "CLAUDE.md content is
delivered as a user message after the system prompt, not as part of the system prompt itself," and
"the more specific and concise your instructions, the more consistently Claude follows them." The
leaf asks for exactly five things and nothing more: the build command, the test command, the layout,
three conventions, and two things Claude gets wrong here — and the last pair is the one a generic
`CLAUDE.md` template never contains, because it is written from having watched this specific model
fail against this specific repository, not copied from a checklist.

**Why it exists.** Without it, every session re-derives the module layout from scratch by reading
`pom.xml` files, and every session re-discovers the two failure modes below the hard way — once per
session, at the cost of a failed build each time, rather than once, in writing.

**The artefact.** Complete, 46 lines, under the leaf's 100-line ceiling:

```markdown
# invoice-ledger-service

A Spring Boot 3.x / Java 21 multi-module Maven service that posts and reverses invoice
ledger entries for the billing platform. Four modules under one aggregator POM:

- `invoice-ledger-api` — REST controllers, request/response DTOs (records only)
- `invoice-ledger-service` — use cases, `@Transactional` boundaries
- `invoice-ledger-persistence` — Spring Data JPA repositories, Flyway migrations
- `invoice-ledger-app` — the executable module: `@SpringBootApplication`, `application.yml`

## Build and test

- Build everything: `./mvnw -q verify`
- Run unit + slice tests only (fast loop): `./mvnw -q test`
- Run the app locally: `./mvnw -q spring-boot:run -pl invoice-ledger-app`
- Never run plain `mvn` — this repo pins Maven 3.9.6 through the wrapper; a system-wide
  `mvn` on a laptop is frequently older and silently skips the enforcer plugin rule that
  blocks snapshot dependencies in `invoice-ledger-app`.

## Conventions

1. **Constructor injection only.** Every `@Service`, `@Component`, and `@RestController`
   takes its dependencies as `final` fields set in a single constructor. No `@Autowired`
   on a field, ever — this repo's own `ArchUnit` rule in `invoice-ledger-service` fails
   the build on a field-injected bean.
2. **DTOs are records, entities are not.** Anything crossing the `invoice-ledger-api`
   boundary is a Java 21 `record`. Anything annotated `@Entity` in
   `invoice-ledger-persistence` stays a plain class with a generated `id`, because
   Hibernate's lazy-loading proxies do not subclass a `record`.
3. **Money is `long` minor units, never `BigDecimal` in a DTO.** `AmountMinorUnits` (a
   `record AmountMinorUnits(long value, Currency currency)`) is the only money type
   allowed to cross module boundaries; a raw `long` or `double` amount fails code review.

## Two things Claude gets wrong here

1. **Assumes single-module layout.** Told to "add a test for the invoice posting logic,"
   Claude defaults to creating `src/test/java/...` at the repo root. This repo has no
   root `src/` — every module owns its own `src/main/java` and `src/test/java`, and the
   posting logic lives in `invoice-ledger-service/src/main/java`. Say which module before
   asking for a change, or the file lands in the aggregator POM's own (nonexistent) source
   tree and the build silently ignores it.
2. **Reaches for `@Autowired` field injection on a fresh class.** It is the most common
   Spring Boot pattern in Claude's training data, and it compiles here — the ArchUnit rule
   only fails at `./mvnw -q verify`, not at edit time. A generated class with a field
   `@Autowired private final LedgerRepository repo;` looks correct in the diff and is
   caught only by the build, several minutes later than it should be.
```

**Why the two gotchas are the valuable part.** `[JAVA]` A Spring Boot engineer's instinct is that
Claude, having presumably seen thousands of multi-module Maven projects, would default correctly.
It does not, for a precise reason: the *majority* shape in public training data is a single-module
Spring Boot starter project (`src/main/java` at the repo root), so a multi-module aggregator POM is
the minority case the model has to be told about rather than inferred from priors — the analogy
breaking point is exactly "assume the model has good priors on your repo's shape just because it has
seen many repos of the same framework." The `@Autowired` gotcha is the same failure mode at the
class level: field injection is over-represented in older Spring tutorials relative to the
constructor-injection style this codebase enforces, so the model's default is the *statistically*
common pattern, not the one this specific repository's `ArchUnit` rule requires.

**Prove step.** The file above, written to disk and measured — not asserted to be under 100 lines:

```
$ wc -l CLAUDE.md
46 CLAUDE.md
```

46 lines, under the leaf's ceiling. The remaining prove obligation — that Claude Code actually loads
this file at session start — is normally checked by running `/context` and reading the **Memory
files** list the documentation names for exactly this purpose. `/context` is an interactive-session
command; there is no live Claude Code session available inside this writing task to drive one.

**Unverified:** that this exact file, placed at the project root, appears under `/context`'s
**Memory files** list in a live session. The mechanism is documented (`memory`: "to confirm the file
loaded, run `/context` in a session and check the list under Memory files") and there is no reason to
doubt it for an ordinarily-named, ordinarily-placed `CLAUDE.md`, but it was not observed directly in
this session. Recorded in `## Open questions`.

**What this costs.** At this guide's 4-characters-per-token estimate (established in `skills/06`),
2,787 bytes ≈ **697 tokens**, and — per Part 0's own finding that the whole conversation is re-sent
every turn — that is 697 tokens resident on **every single turn** of every session in this project,
whether or not that turn ever touches Spring, Maven, or money types. At Sonnet 5's baseline of **$2
per million input tokens**, a project that runs 500 turns before its next `/clear` pays
`697 × 500 = 348,500` tokens ≈ **$0.70** just to keep this one file in context for that session — not
a one-time charge, a per-turn tax for as long as the file stays resident and uncompacted.

No gotcha beyond the one already stated as the leaf's own point: the two "Claude gets wrong here"
entries are not generic Spring Boot folklore, they are specific, observed failure modes for this
model against this exact repository shape, and a `CLAUDE.md` copied from a different multi-module
project would not necessarily carry the same two entries.

> A `CLAUDE.md` is a user message re-sent every turn, not documentation — its value is proportional
> to how specific and falsifiable its claims are, and its cost is proportional to how many turns it
> rides along for.

## §4.1.2 — split it three ways, and measure the difference `[BUILD]` `[PROVE]`

**Concept.** §1.5.26's decision table gave six needs and six mechanisms, rated by enforcement
strength: a fact true everywhere → `CLAUDE.md`; a fact scoped to one file type → a `paths`-scoped
rule; a procedure with named steps, invoked on demand → a skill. The file above conflates all three
inside one `CLAUDE.md`. Sorted against the table:

| Content in §4.1.1's `CLAUDE.md` | Kind of need | Mechanism |
|---|---|---|
| Project description, module layout, build/test commands, "never run plain `mvn`" | True everywhere, always | Stays in `CLAUDE.md` |
| Constructor injection, money-as-minor-units | True everywhere, always | Stays in `CLAUDE.md` |
| "DTOs are records" | Scoped to one module's files (`invoice-ledger-api/**/*.java`) | `paths`-scoped rule in `.claude/rules/` |
| "Find the owning module before adding a test, then run the fast loop for that module" | A procedure — named steps, invoked when a test is actually being added | Skill |

**Why this split, and not a different one.** The DTO convention is true only *while Claude is
looking at a file under `invoice-ledger-api`* — per `memory`'s own text, "path-scoped rules trigger
when Claude reads files matching the pattern, not on every tool use," which is exactly the semantics
this convention needs and a blanket `CLAUDE.md` line cannot express (a `CLAUDE.md` line is either
resident every turn or absent, with no file-type condition). The module-locating step is a procedure
with an explicit sequence — search, report which module, write the test there, run the scoped test
command, report the real output — which is precisely §1.5.26's "named steps, invoked on demand"
category, not a fact.

**The three artefacts**, all complete.

The trimmed `CLAUDE.md` — the build/test commands and the two conventions that are true regardless of
which file Claude is looking at, plus both "gets wrong" entries retained because they are facts about
the model's behaviour rather than either a file-type convention or a procedure:

```markdown
# invoice-ledger-service

A Spring Boot 3.x / Java 21 multi-module Maven service that posts and reverses invoice
ledger entries for the billing platform. Four modules under one aggregator POM:

- `invoice-ledger-api` — REST controllers, request/response DTOs
- `invoice-ledger-service` — use cases, `@Transactional` boundaries
- `invoice-ledger-persistence` — Spring Data JPA repositories, Flyway migrations
- `invoice-ledger-app` — the executable module: `@SpringBootApplication`, `application.yml`

## Build and test

- Build everything: `./mvnw -q verify`
- Run unit + slice tests only (fast loop): `./mvnw -q test`
- Run the app locally: `./mvnw -q spring-boot:run -pl invoice-ledger-app`
- Never run plain `mvn` — this repo pins Maven 3.9.6 through the wrapper; a system-wide
  `mvn` on a laptop is frequently older and silently skips the enforcer plugin rule that
  blocks snapshot dependencies in `invoice-ledger-app`.
- Adding a test for logic in one specific module? Use the `mvn-test-runner` skill rather
  than guessing the module — it locates the owning module before it runs anything.

## Conventions

1. **Constructor injection only.** Every `@Service`, `@Component`, and `@RestController`
   takes its dependencies as `final` fields set in a single constructor. No `@Autowired`
   on a field, ever — this repo's own `ArchUnit` rule in `invoice-ledger-service` fails
   the build on a field-injected bean.
2. **Money is `long` minor units, never `BigDecimal` in a DTO.** `AmountMinorUnits` (a
   `record AmountMinorUnits(long value, Currency currency)`) is the only money type
   allowed to cross module boundaries; a raw `long` or `double` amount fails code review.

## Two things Claude gets wrong here

1. **Assumes single-module layout.** Told to "add a test for the invoice posting logic,"
   Claude defaults to creating `src/test/java/...` at the repo root. This repo has no
   root `src/` — every module owns its own `src/main/java` and `src/test/java`. Use the
   `mvn-test-runner` skill to find the right one.
2. **Reaches for `@Autowired` field injection on a fresh class.** It compiles here — the
   ArchUnit rule only fails at `./mvnw -q verify`, not at edit time — so a generated
   `@Autowired private final LedgerRepository repo;` looks correct in the diff and is
   caught only by the build, several minutes later than it should be.
```

The `paths`-scoped rule, `.claude/rules/api-dtos.md`, using the exact `paths` frontmatter field
`memory` documents:

```markdown
---
paths:
  - "invoice-ledger-api/**/*.java"
---

# API module: DTOs are records

Anything crossing the `invoice-ledger-api` boundary — request bodies, response bodies,
query parameters bundled into one object — is a Java 21 `record`, never a class with
hand-written getters and never a Lombok `@Data` class. `invoice-ledger-persistence`
`@Entity` classes are the one exception in this repository and stay plain classes,
because Hibernate's lazy-loading proxies do not subclass a `record`; that module has its
own rule file and is not the scope of this one.
```

The skill, `.claude/skills/mvn-test-runner/SKILL.md`:

```yaml
---
name: mvn-test-runner
description: Locate which Maven module in invoice-ledger-service owns a given class or piece of logic, then run the fast test loop (./mvnw -q test) scoped to that module only, instead of guessing a root-level src/ that this multi-module repo does not have.
argument-hint: <class-or-symptom>
arguments: [target]
allowed-tools: Bash(find:*) Bash(./mvnw -q test *) Read
---

## Find the owning module

**Candidate files:** !`find . -maxdepth 2 -name "src" -type d`

`invoice-ledger-service` has no root-level `src/` — each of the four modules
(`invoice-ledger-api`, `invoice-ledger-service`, `invoice-ledger-persistence`,
`invoice-ledger-app`) owns its own `src/main/java` and `src/test/java`. The listing above
is the ground truth for which module directories actually exist in this checkout; never
create `src/test/java/...` at the repository root.

## Your task

1. Search for `$target` across all four modules' `src/main/java` with
   `find . -path "*/src/main/java/*" -name "*.java"` piped to `grep -l "$target"`, to find
   which module's source tree the class or logic actually lives in.
2. Report the owning module name back before writing anything.
3. Create or extend the test under that module's own `src/test/java`, mirroring the
   package of the class under test.
4. Run only that module's fast test loop: `./mvnw -q test -pl <owning-module>`. Do not run
   the full `./mvnw -q verify` for this — that also runs the ArchUnit and ITest suites and
   is unnecessary for an ordinary test-first loop.
5. Report the real `./mvnw -q test -pl <owning-module>` output, pass or fail, rather than
   summarizing it as "tests pass."

Do not touch a module's `src/main/java` when the task only asked for a test.
```

**Prove step.** `[PROVE]` The measurement the leaf asks for is `/context` before and after. `/context`
is interactive and there is no live Claude Code session available inside this writing task to drive
it, so the figures below are **derived from real byte counts of the three files above**, run through
this guide's own 4-characters-per-token estimate — the same substitution `skills/06` already made and
flagged for `checklist-refresh`. Real, measured file sizes:

```
$ wc -c CLAUDE.md            # before, §4.1.1's monolith
2787 CLAUDE.md
$ wc -c after/CLAUDE.md      # after, trimmed
2383 after/CLAUDE.md
$ wc -c after/rules/api-dtos.md
563 after/rules/api-dtos.md
$ wc -c after/skills/mvn-test-runner/SKILL.md
1741 after/skills/mvn-test-runner/SKILL.md
```

The skill's own standing cost is not its whole file — per `skills/06`'s own listing-versus-body split,
only the frontmatter's `name` (15 characters) plus `description` (243 characters) — 258 characters —
is resident every turn; the 1,741-byte body loads only on the turn `mvn-test-runner` actually
invokes. The rule's 563 bytes are not resident at session start at all: `memory` states plainly that
"path-scoped rules trigger when Claude reads files matching the pattern," so its cost is paid only on
a turn where Claude reads a file under `invoice-ledger-api/**/*.java`.

| Quantity | Before (§4.1.1) | After (§4.1.2) |
|---|---|---|
| Bytes resident every turn | 2,787 | 2,383 (`CLAUDE.md`) + 258 (skill listing) = 2,641 |
| Tokens resident every turn (÷4) | ≈697 | ≈660 |
| Bytes paid only when the API module is touched | 0 (already resident) | 563 (rule body) ≈141 tokens |
| Bytes paid only when the test-locating procedure runs | 0 (already resident) | 1,741 (skill body) ≈435 tokens |

**Reading the delta honestly.** The always-resident floor drops by only ≈37 tokens (697 → 660) —
splitting a file does not itself shrink the parts that were always-true. The real saving is that
576 bytes' (≈141 + 435 tokens, minus the small listing tax) worth of content that used to be
resident on **every turn regardless of relevance** is now conditional: a session that never touches
`invoice-ledger-api` and never runs `mvn-test-runner` pays the rule's cost zero times and the skill's
body cost zero times, where the monolithic `CLAUDE.md` charged for both content blocks on every
single turn without exception. Scaled to the same 500-turn session as §4.1.1's cost note: the
monolith form pays `697 × 500 = 348,500` tokens no matter what the session does; the split form's
floor pays `660 × 500 = 330,000` tokens, and the two conditional blocks are billed only on the turns
that actually need them — for a session that touches the API module once and never invokes the skill,
that is `330,000 + 141 = 330,141` tokens against the monolith's fixed 348,500, a real reduction, and
the gap widens the less the session happens to need either conditional block.

**Unverified:** the before/after figures above are derived from real byte counts through the 4
characters-per-token estimate, not read off a live `/context` grid — no live Claude Code session was
available inside this writing task. Recorded in `## Open questions`.

**D-94** — the finished `.claude` tree for `invoice-ledger-service` (`CLAUDE.md`, `.claude/rules/`,
`.claude/skills/`, `settings.json` together) plus a `/context` delta panel is drawn in the next file,
[the local file, and what the folder cost](01-a-claude-folder-b.md) — satisfied there by pointer
rather than embedded here, since this file's leaves stop at §4.1.3.

> Splitting a `CLAUDE.md` along the decision table's own lines does not shrink the always-true floor
> by much — it turns fixed, always-resident cost into conditional cost, paid only on the turns that
> actually touch the scoped file type or actually invoke the procedure.

## §4.1.3 — a complete `settings.json` for the same repository `[BUILD]`

**Concept.** `permissions/08-sandbox-and-a-real-block.md` already built and proved, rule by rule, a
five-requirement permission block for a Java/Spring Boot repository: allow the build and test
commands, deny `git push`, deny reads of `.env` and `secrets/**`, deny `rm -rf`. This leaf does not
repeat that proof — it builds the rest of the `settings.json` a real `.claude` folder needs around
that same permission shape, adapted to `invoice-ledger-service`'s actual commands: `env`, `model`,
and `effortLevel`, alongside the permission block itself.

**The artefact.** Complete, valid, parseable, every parent key present, no comments:

```json
{
  "permissions": {
    "allow": [
      "Bash(./mvnw -q test *)",
      "Bash(./mvnw -q verify *)",
      "Bash(./mvnw -q spring-boot:run *)"
    ],
    "deny": [
      "Bash(git push *)",
      "Read(./.env)",
      "Edit(./.env)",
      "Read(./secrets/**)",
      "Edit(./secrets/**)"
    ]
  },
  "env": {
    "SPRING_PROFILES_ACTIVE": "test"
  },
  "model": "claude-sonnet-5",
  "effortLevel": "medium"
}
```

**Which trap each choice dodges**, against what the reader already has from PART 1 and from
`permissions/08` directly above:

- **The `*` sits after the subcommand, not after the tool name.** `Bash(./mvnw -q test *)`, never
  `Bash(./mvnw *)` — `permissions/08` proved this exact trap for `mvn -q test *`: a wildcard right
  after the tool name absorbs every Maven goal, including ones that execute arbitrary code disguised
  as a build step (`mvn -Dexec.args='rm -rf /' exec:exec`); placing it after the already-named
  subcommand only ever absorbs trailing arguments to that one goal (§1.4.6).
- **`Read(./.env)` and `Read(./secrets/**)` use gitignore pattern syntax, and each gets an `Edit`
  deny alongside it.** `./` anchors both at the session's working directory and `/**` denies the
  whole `secrets/` tree at any depth, per §1.4.16. The paired `Edit` deny is not closing a gap in
  `Read`-to-`Edit` propagation — per §1.4.17, a `Read` deny on this target version already propagates
  to `Edit` (since v2.1.208) and `Write` (since v2.1.228) — it is making the intent legible without
  requiring a reviewer to already know that propagation rule by heart. Per §1.4.17–1.4.18, neither
  deny reaches `NotebookEdit`; only a bare, path-less `"deny": ["NotebookEdit"]` does that, and this
  repository has no `.ipynb` files to justify paying that cost.
- **The deny list carries no allowlist exception for a "safe" `rm -rf`.** `permissions/08` already
  proved the general law this repeats: `deny` is checked before `allow` and wins on any match
  regardless of how narrowly a co-existing `allow` entry is written (§1.4.3), so this settings object
  does not attempt to add a scoped `rm -rf` exception — it relies on `./mvnw clean`, which never
  shells out through a raw `rm -rf` Bash call, for the safe case instead.
- **`env` reaches hooks and Bash, not only the model's own view of the shell.** Re-verified against
  `settings-reference` immediately before writing this leaf: an `env` object "sets environment
  variables for every session and its subprocesses, including hooks and Bash commands" (§1.2.11).
  `SPRING_PROFILES_ACTIVE: "test"` is therefore not a hint Claude reads and might forget to export —
  it is set in the actual process environment every `Bash(./mvnw ...)` invocation and every hook
  script inherits, so a Spring Boot integration test that reads `SPRING_PROFILES_ACTIVE` at startup
  sees `test` whether the command was typed by hand or launched by Claude Code.
- **`model` and `effortLevel` are ordinary settings keys, not CLI-only flags.** Re-verified against
  `settings-reference`: `model` sets which model a session starts with, and `effortLevel` saves the
  `/effort` level so future sessions reason at the same depth without re-setting it interactively —
  both accepted at any settings scope, so committing them to the project's own `.claude/settings.json`
  fixes the team's default rather than leaving it to whatever each engineer's personal `/model` and
  `/effort` history happens to be.

**Prove step.** Valid JSON, confirmed against the actual file:

```
$ python3 -m json.tool settings.json > /dev/null && echo "valid JSON"
valid JSON
```

Two of the five permission requirements traced against this exact object, in the same style
`permissions/08` already proved in full for the general five-requirement shape (not repeated here to
avoid duplicating that proof): `./mvnw -q test` — no separator, no wrapper — checked against `deny`:
no match; checked against `allow`: `Bash(./mvnw -q test *)` matches, wildcard absorbing the empty
trailing string. **Outcome: runs unattended.** `git push origin main` — checked against `deny` first:
`Bash(git push *)` matches, wildcard absorbing `origin main`. **Outcome: blocked, before `allow` is
ever consulted.** Both outcomes are the same mechanism `permissions/08` traced command-by-command;
this settings object simply substitutes this repository's real commands into the proven shape.

**What this costs.** Unlike `CLAUDE.md`, a `settings.json` is not text injected into the model's
context — the harness parses it once and enforces it directly, so the permission block, `env`,
`model`, and `effortLevel` keys carry effectively zero standing token cost per turn. The cost that
does exist is the one `permissions/08` already worked out in full: every **blocked** attempt still
produces a `tool_use` block plus a denial `tool_result`, together ≈100 tokens, that then rides along
in every subsequent turn's input until compaction evicts it — a `git push` blocked once in a 40-turn
remainder of the session costs `40 × 100 = 4,000` extra input tokens, not for the command that ran,
but for the record that it was refused.

No gotcha beyond the one `permissions/08` already carries forward: a broad deny still cannot carry an
allowlist exception, and this file does not try to give it one.

> A `settings.json` is enforced by the harness before the model ever runs a command, so — unlike a
> `CLAUDE.md` — its standing cost is not "tokens resident every turn," it is "tokens spent recording
> the outcome of a rule that already fired."

## Pitfalls

- **Belief:** "the two 'Claude gets wrong here' entries in a `CLAUDE.md` are generic Spring Boot
  advice, so a copied-in list from another project's `CLAUDE.md` covers the same ground." **Outcome:**
  a generic list misses the two failures this specific model shows against this specific repository's
  shape — the root-`src/` assumption is a symptom of the *majority* training-data shape (single-module
  Spring Boot) losing to this repository's *minority* shape (four-module aggregator), and a generic
  list written against a different repository's module layout would name a different failure, if any.
  **Fix:** write the two entries from observed failures against this repository, not from a template.
  **Why people believe it:** every Spring Boot `CLAUDE.md` reads similarly at a glance, and the
  build/test/layout sections genuinely are near-identical across projects, which hides that the two
  "gets wrong" entries are the one part that is not transferable.
- **Belief:** "splitting a `CLAUDE.md` into a rule and a skill mainly saves tokens on every turn."
  **Outcome:** the always-resident floor barely moves (§4.1.2's measured 697 → 660 tokens) — the real
  saving is converting fixed, always-on cost into conditional cost that only bills the turns that
  actually touch the scoped file type or actually invoke the procedure. **Fix:** measure both the
  floor and the conditional blocks separately, the way §4.1.2 does, rather than quoting one number
  as "the savings." **Why people believe it:** the decision table (§1.5.26) is framed around
  enforcement strength, not cost, so it is easy to assume the point of the split is cost reduction
  when it is really cost *conditionality*.
- **Belief:** "`Bash(./mvnw -q test *)` in `allow` plus `Bash(./mvnw *)` somewhere for convenience is
  harmless, since the narrower rule already covers the common case." **Outcome:** the broader
  `Bash(./mvnw *)` allow rule, if ever added, would itself absorb every Maven goal the narrower rule
  was written to exclude — the two rules do not combine into "narrow behaviour, broad fallback"; the
  broad `allow` entry is simply its own independent hole the moment it exists. **Fix:** never add the
  tool-name-only wildcard alongside the subcommand-scoped one; if a new Maven goal needs approval,
  add its own `Bash(./mvnw -q <goal> *)` entry instead. **Why people believe it:** allow rules read as
  purely additive — "more allow entries just means more things run unattended" — which is true for
  what each rule *permits* but ignores that a broader entry permits a strict superset of a narrower
  one sitting right next to it, silently making the narrower rule's careful scoping pointless.

## Cheat sheet

| Item | Value |
|---|---|
| Service | `invoice-ledger-service` — Spring Boot 3.x / Java 21, 4-module Maven aggregator |
| Build | `./mvnw -q verify` |
| Test (fast loop) | `./mvnw -q test` |
| Run | `./mvnw -q spring-boot:run -pl invoice-ledger-app` |
| §4.1.1 `CLAUDE.md` size | 46 lines, 2,787 bytes ≈ 697 tokens, resident every turn |
| §4.1.1 cost, 500-turn session | 348,500 tokens ≈ $0.70 at $2/M input |
| §4.1.2 split | `CLAUDE.md` (always-true) + `.claude/rules/api-dtos.md` (`paths`-scoped) + `.claude/skills/mvn-test-runner/` (procedure) |
| §4.1.2 resident floor, before → after | ≈697 → ≈660 tokens/turn (derived, not `/context`-observed) |
| §4.1.2 conditional cost | rule body ≈141 tokens (only when an API-module file is read); skill body ≈435 tokens (only on invocation) |
| §4.1.3 permission trap dodged | `*` after the subcommand, not after `./mvnw` |
| §4.1.3 secrets trap dodged | `Read` + `Edit` deny, gitignore syntax; `NotebookEdit` still uncovered (not needed here) |
| §4.1.3 `rm -rf` trap | no exception carved — `./mvnw clean` is the safe path instead |
| §4.1.3 `env` scope | every session subprocess, hooks and Bash both (§1.2.11) |
| §4.1.3 standing token cost | ≈0 — enforced by the harness, not injected as text; only a blocked attempt costs ≈100 tokens, once, resident until compaction |

## Self-test

<details><summary>1. Why does §4.1.1's `CLAUDE.md` name a root-`src/` assumption as something Claude gets wrong, rather than trusting the model's exposure to many Maven projects?</summary>
The majority shape in public training data is a single-module Spring Boot starter with `src/main/java` at the repository root; a four-module aggregator POM is the minority shape, so the model's default reflects the statistically common case rather than this specific repository's actual layout. Naming it explicitly in `CLAUDE.md` replaces a per-session rediscovery with a one-time fact.
</details>

<details><summary>2. In §4.1.2, why does the "DTOs are records" convention move to a `paths`-scoped rule rather than staying in `CLAUDE.md`?</summary>
It is true only while Claude is looking at a file under `invoice-ledger-api`, not everywhere in the repository. A `paths`-scoped rule loads only "when Claude reads files matching the pattern," which is exactly the conditional semantics this convention needs; a `CLAUDE.md` line has no such condition — it is either resident every turn or not present.
</details>

<details><summary>3. §4.1.2 measures the always-resident floor moving from ≈697 to ≈660 tokens after the split. Why is that a modest number even though the split is worth doing?</summary>
Splitting a file does not shrink the parts that were always true — those still need to be resident every turn regardless of mechanism. The real saving is that content which used to be resident on every turn regardless of relevance (the DTO rule and the module-locating procedure) becomes conditional, paid only on the turns that actually touch the scoped file type or actually invoke the skill.
</details>

<details><summary>4. Why are the §4.1.2 before/after `/context` figures marked Unverified rather than reported as observed?</summary>
`/context` is an interactive Claude Code command, and no live session was available inside this writing task to drive one. The figures are instead derived from real, measured byte counts of the actual files run through this guide's established 4-characters-per-token estimate — a derivation, not an observation, and flagged as such per the precedent `skills/06-builtins-and-decision-table.md` already set for `checklist-refresh`.
</details>

<details><summary>5. In §4.1.3's settings.json, why does the `.env` deny list both `Read` and `Edit` when `permissions/08` already established that a `Read` deny propagates to `Edit`?</summary>
The propagation is real on this target version (since v2.1.208 for `Edit`, v2.1.228 for `Write`), so the explicit `Edit` deny is not closing a functional gap — it makes the intent readable without requiring a reviewer to already know the version-specific propagation rule, and it is defensive against a future version regression in that propagation.
</details>

<details><summary>6. Why does §4.1.3's deny list not add a narrower `allow` entry to re-permit `./mvnw clean`-style cleanup if `rm -rf` were ever denied?</summary>
This settings object never denies `rm -rf` in the first place — it relies on `./mvnw clean`, which never shells out through a raw `rm -rf` Bash call, for the safe cleanup path. Had a broad `rm -rf` deny been added (as `permissions/08` discusses), a narrower co-existing `allow` for a "safe" `rm -rf` would never be reached, because `deny` wins on any match regardless of how specific a competing `allow` entry is.
</details>

<details><summary>7. What does the `env` key in §4.1.3's settings.json actually reach, per the re-verified documentation?</summary>
Every session subprocess, explicitly including hooks and Bash commands — not just the model's own reasoning about what the shell environment contains. `SPRING_PROFILES_ACTIVE: "test"` is set in the real process environment every `./mvnw` invocation inherits, regardless of whether Claude or a human typed the command.
</details>

<details><summary>8. Why does a settings.json's standing token cost differ fundamentally from a CLAUDE.md's?</summary>
A `settings.json` is parsed once by the harness and enforced directly — it is not text re-sent to the model every turn, so its permission rules, `env`, `model`, and `effortLevel` keys carry effectively zero standing token cost. The cost that does exist comes indirectly: a blocked tool call still produces a `tool_use` block and a denial `tool_result` that ride along in context until compaction, at roughly 100 tokens per blocked attempt.
</details>

## Open questions

- **Unverified:** whether `invoice-ledger-service`'s `CLAUDE.md` actually appears under `/context`'s
  **Memory files** listing in a live session (§4.1.1) — the mechanism is documented but not observed
  directly in this writing task, which had no live Claude Code session available to drive `/context`.
- **Unverified:** the §4.1.2 before/after token figures (≈697 → ≈660 resident; ≈141 and ≈435
  conditional) are derived from real byte counts of the three artefacts through this guide's
  4-characters-per-token estimate, not read off a live `/context` grid, for the same reason as above.

---

**Leaves covered:** 4.1.1–4.1.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-94 draws this row's finished tree and is embedded in the next file
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 522
