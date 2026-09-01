# 21 AI for Coding — a skill and a command — BUILD IT (§4.3.1–4.3.3)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [the `Stop` gate, and the diff against the real one](02-three-hooks-b.md) · Next: [injection, and the diff against the real one](03-a-skill-and-a-command-b.md)

`build-it/01` already shipped one skill for `invoice-ledger-service` — `mvn-test-runner`, the
"procedure" limb of §1.5.26's decision table: locate the owning Maven module, then run the fast test
loop scoped to it. This file's three leaves are not that skill again under a new name. They build a
genuinely different skill, `checklist-refresh` — a pre-review checklist grounded in the module's real
diff, not a test-runner — then the same capability as a bare `.claude/commands/*.md` file, then two
more skills, `post-invoice-reversal` and `money-minor-units-conventions`, chosen to show the two
invocation-control fields' opposite failure modes rather than to run another Maven command.

All work below runs under `/tmp/21-skills-scratch/invoice-ledger-service` — a real git checkout with
one committed file and one uncommitted edit, built for this file only, never inside this repository
and never inside sdlc-harness.

## §4.3.1 — a skill: frontmatter, `$ARGUMENTS`, one injection, one on-demand file `[BUILD]`

**Concept.** A skill with all four moving parts at once: YAML frontmatter that names it and scopes
its tools, an `$ARGUMENTS` placeholder that takes the module name at invocation time, a
`` !`command` `` line that runs before Claude ever sees the file, and a `references/` file that is
part of the skill's own directory but does not enter context until the skill's body tells Claude to
read it.

**Why it exists.** `mvn-test-runner` answers "which module, and did the tests pass." Nothing in this
project's `.claude/` folder answers "is this diff ready for review" — and that check needs the actual
current diff, not a description of one, plus a checklist detailed enough that inlining it in every
`CLAUDE.md`-resident line would be wasteful on every turn that never runs it.

**How it works.** Claude Code reads the frontmatter only because the opening `---` is the file's
literal first line (§1.5.9) — one leading blank line above it and the whole file becomes inert
content, silently. `allowed-tools: Bash(git diff --stat *)` pre-approves exactly that one command for
the invoking turn; it does not remove any other tool from the pool, and the grant clears the moment
the next user message is sent (§1.5.8, D-38 — not embedded here, this row's manifest carries no
diagram; see D-38 in `skills/`). The `` !`git diff --stat` `` line runs once, before the rendered
content is sent to Claude, and its output is spliced in as literal text — not re-scanned for a second
placeholder (§1.5.12). The `references/checklist-full.md` file sits beside `SKILL.md` in the same
skill directory and is not resident in context at all until the skill's own body — step 3 below —
tells Claude to read it; that gap between "listed" and "read" is exactly what D-36 draws (see D-36 in
`skills/`, not embedded — no diagram in this row's manifest).

**The artefact**, complete:

```yaml
---
name: checklist-refresh
description: Refresh the pre-review checklist for a touched module in invoice-ledger-service before opening a pull request, grounded in the module's real uncommitted diff. Use when the user asks to prep a PR, refresh the review checklist, or check whether a module's changes are ready for review.
argument-hint: <module-name>
allowed-tools: Bash(git diff --stat *)
---

## Diff for $ARGUMENTS

!`git diff --stat`

## Your task

1. Read the diff stat above. It is the real, current uncommitted diff for this checkout — not a
   description of one.
2. Confirm every changed file in the stat belongs to the `$ARGUMENTS` module's own `src/` tree. A
   file from a different module in the same diff means the change crossed a module boundary and the
   checklist below does not clear it.
3. For the full per-item checklist text — the record-vs-class rule, the ArchUnit constructor-injection
   check, and the `AmountMinorUnits` boundary rule — load
   [references/checklist-full.md](references/checklist-full.md) now. Do not answer from memory or
   summarize the rule names without reading the file; the wording there is what review is measured
   against.
4. Report which checklist items in that file pass, which fail, and which file in the diff stat each
   failure belongs to.
```

The on-demand file it defers to, `.claude/skills/checklist-refresh/references/checklist-full.md`:

```markdown
# Pre-review checklist — invoice-ledger-service

Loaded only when `checklist-refresh` actually runs. Not resident in the skill listing and not
resident in context until step 3 of `SKILL.md` reads this file.

1. **Records at the API boundary.** Every class under `invoice-ledger-api` that crosses the REST
   boundary — request body, response body, or a query-parameter bundle — is a Java 21 `record`.
   A hand-written getter class or a Lombok `@Data` class fails this item.
2. **No field-injected `@Autowired`.** Every `@Service`, `@Component`, and `@RestController`
   changed in the diff takes its dependencies through a single constructor. This is enforced at
   `./mvnw -q verify` by this repository's own ArchUnit rule, but the checklist catches it before
   the build does.
3. **Money never crosses a module boundary as `long` or `double` alone.** Any changed method
   signature that accepts or returns a bare numeric amount instead of `AmountMinorUnits` fails this
   item, regardless of which module the signature lives in.
4. **A changed `invoice-ledger-persistence` `@Entity` stays a plain class.** A `record` in this
   position fails to load under Hibernate's lazy-proxy subclassing and is flagged even if it
   compiles.
```

**Prove step.** The frontmatter fence, checked against the actual file rather than assumed:

```
$ head -6 .claude/skills/checklist-refresh/SKILL.md
---
name: checklist-refresh
description: Refresh the pre-review checklist for a touched module in invoice-ledger-service before opening a pull request, grounded in the module's real uncommitted diff. Use when the user asks to prep a PR, refresh the review checklist, or check whether a module's changes are ready for review.
argument-hint: <module-name>
allowed-tools: Bash(git diff --stat *)
---
```

The command the injection line runs, executed directly against the real scratch checkout — one
committed file in `invoice-ledger-api`, one uncommitted one-line edit to it — to confirm the exact
text Claude would receive in place of `` !`git diff --stat` ``:

```
$ git diff --stat
 invoice-ledger-api/src/main/java/Dummy.java | 1 +
 1 file changed, 1 insertion(+)
```

And the directory the skill needs, confirmed to actually hold both files:

```
$ find .claude/skills/checklist-refresh -type f
.claude/skills/checklist-refresh/SKILL.md
.claude/skills/checklist-refresh/references/checklist-full.md
```

The one part of this prove step that stays out of reach in this writing task — Claude Code actually
invoking `/checklist-refresh invoice-ledger-api`, reading the diff-stat injection, and then reading
`references/checklist-full.md` on its own — needs a live session; a nested `claude -p` invocation from
inside this running session was refused outright:

```
Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by
classifier.
```

**Unverified:** live invocation of `checklist-refresh` in a real session — everything above it
(frontmatter parsing point, injection output, directory shape) is directly observed; the model's own
behavior on receiving the rendered content is not. Recorded in `## Open questions`.

**Gotcha.** The injection line must start at column zero or immediately after whitespace —
`` DIFF=!`git diff --stat` `` would leave the whole thing as literal text and the command would never
run, per §1.5.13 (D-39, not embedded here). `checklist-refresh`'s injection line sits alone on its own
line specifically to avoid that trap.

> A skill's `references/` file is not a second skill — it is content the skill's own body chooses to
> pull into context, on a turn the body itself decides, which is the mechanism that lets a skill's
> standing cost stay small while its total knowledge does not.

**What this costs — two numbers, kept separate.** The **standing listing cost**, paid on every turn
regardless of whether `checklist-refresh` ever fires: `name` (17 characters) plus `description` (283
characters) is 300 characters of the combined text the skill listing carries for this entry — nowhere
near the 1,536-character per-entry cap `skills` documents — ≈75 tokens at this guide's 4-characters-
per-token estimate, resident every turn the skill stays listed. The **one-off body cost**, paid only on
a turn that actually invokes it: the whole rendered `SKILL.md`, measured directly —

```
$ wc -c .claude/skills/checklist-refresh/SKILL.md
1310 .claude/skills/checklist-refresh/SKILL.md
```

≈327 tokens, once, the turn it fires — then resident going forward per the skill content lifecycle
(§1.5.15), not re-paid on every later turn the way the listing is. A third, deeper layer sits behind
even that: `references/checklist-full.md` is 1,242 bytes (≈311 tokens) that is not part of either
number above — it is paid only if step 3 actually executes, which is the entire point of shipping it
as a separate file rather than folding its four items into the body directly.

## §4.3.2 — the same capability as a bare command file, and what the skill form bought `[BUILD]`

**Concept.** `skills` states the identity plainly: "A file at `.claude/commands/deploy.md` and a
skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way." A command file
supports the same frontmatter as a skill, "except `name` and `paths`, which Claude Code ignores in a
command file" — so `$ARGUMENTS`, `` !`command` `` injection, `allowed-tools`, `argument-hint`,
`disable-model-invocation`, and `user-invocable` all behave identically in a bare command file.

**The artefact**, `.claude/commands/checklist-refresh.md` — the command-name comes from the file name,
not a `name` field, so none is written:

```yaml
---
description: Refresh the pre-review checklist for a touched module in invoice-ledger-service before opening a pull request, grounded in the module's real uncommitted diff. Use when the user asks to prep a PR, refresh the review checklist, or check whether a module's changes are ready for review.
argument-hint: <module-name>
allowed-tools: Bash(git diff --stat *)
---

## Diff for $ARGUMENTS

!`git diff --stat`

## Your task

1. Read the diff stat above. It is the real, current uncommitted diff for this checkout — not a
   description of one.
2. Confirm every changed file in the stat belongs to the `$ARGUMENTS` module's own `src/` tree. A
   file from a different module in the same diff means the change crossed a module boundary and the
   checklist below does not clear it.
3. Walk this checklist directly — there is no second file to load:
   - Records at the API boundary: every class crossing the REST boundary is a Java 21 `record`.
   - No field-injected `@Autowired`: every changed `@Service`/`@Component`/`@RestController` takes
     dependencies through a single constructor.
   - Money never crosses a module boundary as a bare `long` or `double`; only `AmountMinorUnits`.
   - A changed `invoice-ledger-persistence` `@Entity` stays a plain class, never a `record`.
4. Report which items pass, which fail, and which file in the diff stat each failure belongs to.
```

Behaviorally, `/checklist-refresh invoice-ledger-api` typed against either form runs the same
injection, receives the same `$ARGUMENTS` substitution, and is gated by the same `allowed-tools`
grant for the same one turn. What actually differs, checked point by point rather than asserted:

| Property | Skill (§4.3.1) | Bare command (this section) |
|---|---|---|
| Command name source | Directory name (`checklist-refresh/`) | File name (`checklist-refresh.md`) |
| `name` frontmatter field | Sets the display label in `/skills` listings | Ignored — no listing label to set |
| Supporting files | `references/checklist-full.md` ships in the skill's own directory, loaded on demand | No natural directory of its own — the four checklist items had to be inlined into the one file, so they cost their ≈311 tokens' worth of space every time this command fires, never conditionally |
| Visible in `/skills` menu | Yes, with its own entry and toggle state | No — command files don't appear in `/skills`; only in `/` autocomplete |
| Name/skill precedence | A skill and a command sharing a name: the skill wins | — |
| Everything else (`$ARGUMENTS`, injection, `allowed-tools`, invocation-control fields) | Identical | Identical |

**Prove step.** The command file, measured against the skill's body directly — same content, no
`references/` split, so it is heavier as a single file even though nothing behaves differently at
invocation:

```
$ wc -c .claude/commands/checklist-refresh.md
1389 .claude/commands/checklist-refresh.md
```

**What the skill form actually bought.** Not new behavior — the identical `git diff --stat` injection
runs either way, and the identical four-item review either passes or fails either way. What the skill
form bought is **progressive disclosure as a directory shape**: a place to put the detailed checklist
text that is not always paid for, plus a `/skills` menu entry a project maintainer can review, toggle,
or override with `skillOverrides` (§1.5, not re-derived here) without editing the file's own
frontmatter. A team standardizing dozens of these procedures gets a place to grow each one without
inflating the always-loaded body; a team with one three-line procedure and no reference material gets
nothing measurable from the switch.

**What this costs.** The bare command file has no separate listing entry the way a skill does — it
still counts toward the combined slash-command listing Claude Code shows, but there is no `name` +
`description` pair distinct from the file's own frontmatter to total separately, so its standing cost
and its firing cost collapse into the same 1,389-byte (≈347-token) figure, paid whenever it fires,
with nothing conditional behind it.

No gotcha beyond §4.3.1's injection-column-position trap, which applies identically here since the
line is copied verbatim.

> Two files that behave identically at invocation can still cost differently at rest — the difference
> is not in what runs, it is in whether the detail behind the four checklist items is a directory the
> skill controls or text baked permanently into the one file that fires.

## §4.3.3 — invocable only the intended way `[BUILD]` `[PROVE]`

**Concept.** `skills` frontmatter gives two independent invocation-control fields, and this leaf pairs
one of each against the failure mode it exists to prevent:

| Field | Skill built here | You can invoke | Claude can invoke | Description in context |
|---|---|---|---|---|
| (default) | — | Yes | Yes | Always |
| `disable-model-invocation: true` | `post-invoice-reversal` | Yes | **No** | **Not in context at all** |
| `user-invocable: false` | `money-minor-units-conventions` | **No** | Yes | Always |

**Why it exists.** A reversal posting is exactly the side-effecting action `skills` names as the
reason for `disable-model-invocation`: "you don't want Claude deciding to deploy because your code
looks ready," and here you specifically do not want Claude reversing a posted invoice because a
conversation about invoices happened to mention one. `money-minor-units-conventions` is the opposite
shape — background knowledge with no side effect and nothing for a user to trigger by typing its name,
so hiding it from the `/` menu costs nothing while its description stays available for Claude to
match against.

**The two artefacts**, complete.

`post-invoice-reversal` — `disable-model-invocation: true`:

```yaml
---
name: post-invoice-reversal
description: Post a reversing ledger entry for an already-posted invoice in invoice-ledger-service. Only invoke on explicit user request — never trigger this automatically from a conversation about invoices.
argument-hint: <invoice-id>
disable-model-invocation: true
allowed-tools: Bash(./mvnw -q test -pl invoice-ledger-service *)
---

Post a reversal for invoice `$ARGUMENTS`:

1. Locate the original posting in `invoice-ledger-service`'s `LedgerEntryRepository` by invoice id.
2. Create a new `LedgerEntry` with the sign of every `AmountMinorUnits` flipped and a
   `reversalOf` reference to the original entry's id. Never mutate or delete the original row.
3. Run `./mvnw -q test -pl invoice-ledger-service` and report the real output before considering
   the reversal posted.
4. Report the new entry's id back to the user.
```

`money-minor-units-conventions` — `user-invocable: false`:

```yaml
---
name: money-minor-units-conventions
description: Background knowledge on why invoice-ledger-service represents money as AmountMinorUnits (long minor units plus a Currency) rather than BigDecimal or a raw double, and where the rule stops applying. Load when a change touches a money field, an amount parameter, or a currency conversion.
user-invocable: false
---

`AmountMinorUnits` (`record AmountMinorUnits(long value, Currency currency)`) is the only money type
allowed to cross a module boundary in this repository. A raw `long`, `double`, or `BigDecimal` amount
in a method signature that crosses `invoice-ledger-api`, `invoice-ledger-service`, or
`invoice-ledger-persistence` fails code review, because a `double` amount silently loses precision on
currency arithmetic and a bare `long` loses the currency it is denominated in.

The rule stops at the boundary, not inside a single class: a private helper method fully contained
inside one class may still compute with a primitive `long` internally, as long as the value never
becomes a parameter or return type another module depends on.
```

**Prove step.** `[PROVE]` Real files, real measurements, walked through against the documented rule
each field enforces — this is the argument, not the conclusion:

```
$ find .claude/skills/post-invoice-reversal .claude/skills/money-minor-units-conventions -type f
.claude/skills/post-invoice-reversal/SKILL.md
.claude/skills/money-minor-units-conventions/SKILL.md
$ wc -c .claude/skills/post-invoice-reversal/SKILL.md .claude/skills/money-minor-units-conventions/SKILL.md
     863 .claude/skills/post-invoice-reversal/SKILL.md
    1097 .claude/skills/money-minor-units-conventions/SKILL.md
```

Working the invocation table's two rows through, term by term, against `skills`' own text:

- **`post-invoice-reversal`, typed directly.** Nothing in `disable-model-invocation` touches your own
  typed invocation — the field description is explicit that this is "only you can invoke" the skill.
  Typing `/post-invoice-reversal INV-40231` loads the full 863-byte body exactly as written above.
- **`post-invoice-reversal`, Claude trying it unprompted.** Per `skills`: "Description not in context"
  for a `disable-model-invocation: true` skill — Claude has no listing entry to match against in the
  first place, so the ordinary path (Claude reading a description, deciding it fits, invoking it) has
  nothing to trigger on. If Claude were somehow still directed at it, the documented behavior is that
  "Claude Code blocks the call and instructs it not to reproduce the deploy steps another way" — the
  same sentence `skills` uses for its own `deploy` example, generalized to any skill carrying the
  field.
- **`money-minor-units-conventions`, typed directly.** `user-invocable: false` means "Claude Code
  hides it from the `/` menu and doesn't run it when you type `/name`" — typing
  `/money-minor-units-conventions` does not run the skill; it is absent from autocomplete and the
  name resolves to nothing invocable.
- **`money-minor-units-conventions`, Claude reaching for it.** Its description stays resident in the
  skill listing exactly like an ordinary skill's — the table's own "Description in context: Always"
  column — so Claude can still load and apply it the moment a change touches a money field, an amount
  parameter, or a currency conversion, with no user action required.

The one step this task cannot drive directly is a live session actually exercising either path — the
same nested-`claude` classifier refusal from §4.3.1 blocks it here too:

```
Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by
classifier.
```

**Unverified:** the live blocked-call message Claude Code shows when it attempts a
`disable-model-invocation: true` skill, and the live `/` autocomplete list actually omitting
`money-minor-units-conventions`, were not captured directly in this session for the same reason
§4.3.1's live invocation was not. The reasoning above is worked through against `skills`' own quoted
text rather than asserted from memory. Recorded in `## Open questions`.

**Gotcha.** The two fields are independent, not a spectrum — a skill can carry both
`disable-model-invocation: true` and `user-invocable: false` at once, which would leave it invocable
by neither you nor Claude except through the `Skill` tool's own permission rules; neither artefact
here does that, because each is built to demonstrate exactly one restriction; combining them is a
distinct third shape this leaf does not ask for.

> `disable-model-invocation` removes the description from context entirely, so Claude never even sees
> a listing to reach for; `user-invocable: false` leaves the description exactly where it always was
> and removes only the human's typed path — the two fields fail closed on opposite sides of the same
> listing.

**What this costs — two numbers, kept separate, and asymmetric between the two skills.**
`post-invoice-reversal`'s standing listing cost is **zero**: per the table above, its description is
not in context at all when `disable-model-invocation: true` is set, so nothing about it rides along on
a turn that never invokes it by name. Its one-off body cost, paid only the turn `/post-invoice-reversal`
actually runs, is the full 863 bytes ≈216 tokens. `money-minor-units-conventions` is the mirror image:
its standing listing cost is **not zero** — `name` (29 characters) plus `description` (286 characters)
is 315 characters, ≈79 tokens, resident every turn precisely because `user-invocable: false` does
nothing to its listing visibility to Claude — and its one-off body cost, paid the turn Claude actually
loads it, is the full 1,097 bytes ≈274 tokens. The asymmetry is the leaf's own point: hiding a skill
from the user's typed menu (`user-invocable: false`) is free in behavior but not in standing cost;
hiding it from the model's automatic consideration (`disable-model-invocation: true`) removes the
standing cost entirely, because there is no listing left to pay for.

## Pitfalls

- **Belief:** "`allowed-tools: Bash(git diff --stat *)` on `checklist-refresh` means Claude can only
  run that one command while the skill is active." **Outcome:** every other tool Claude already had —
  `Read`, `Edit`, arbitrary other `Bash` invocations subject to the ordinary permission settings —
  stays fully available; the field only pre-approves the one listed pattern so it does not prompt.
  **Fix:** read `allowed-tools` as "no prompt for this," never as "nothing else is possible." **Why
  people believe it:** the name reads like a restriction, and `disallowed-tools` — the field that
  actually removes tools — sits right next to it in the same table with a name that sounds like its
  opposite rather than its complement.
- **Belief:** "moving `checklist-refresh` from a skill to a bare command file loses the `$ARGUMENTS`
  substitution and the `` !`command` `` injection, since those feel like 'skill' features." **Outcome:**
  §4.3.2's command file runs the identical substitution and the identical injection — `skills`
  documents both as working "the same way" in `.claude/commands/`, with only `name` and `paths` ignored
  there. **Fix:** treat the two forms as one mechanism with two file layouts, and reserve the actual
  decision — skill vs. command — for whether the procedure needs a `references/` directory or a
  `/skills` menu entry, not for whether it needs `$ARGUMENTS`.
  **Why people believe it:** the feature list under "skills" in the documentation reads as a single
  bundle, obscuring that most of it was never skill-exclusive.
- **Belief:** "`user-invocable: false` and `disable-model-invocation: true` are two settings of the
  same knob — pick whichever hides the skill from the part of the surface you don't want using it."
  **Outcome:** they hide it from opposite audiences and, per §4.3.3's cost note, from opposite cost
  columns — `disable-model-invocation` drops the description from context and removes standing cost;
  `user-invocable: false` keeps both and only removes the human's typed path. Setting the wrong one on
  `post-invoice-reversal` — `user-invocable: false` instead of `disable-model-invocation: true` — would
  leave Claude free to reverse a posting on its own initiative, which is exactly the failure this skill
  exists to prevent. **Fix:** name the audience you are restricting first — "not Claude" is
  `disable-model-invocation`; "not the user" is `user-invocable: false` — then set the field for that
  audience, never by which one "sounds more restrictive."
  **Why people believe it:** both fields are booleans in the same frontmatter block with parallel-
  sounding names, which invites treating them as interchangeable strength dials rather than
  orthogonal, audience-scoped switches.

## Cheat sheet

| Item | Value |
|---|---|
| §4.3.1 skill | `checklist-refresh` — frontmatter + `$ARGUMENTS` + one injection + `references/checklist-full.md` |
| §4.3.1 injection proof | `git diff --stat` → real 2-line stat against the scratch checkout |
| §4.3.1 costs | Listing 300 chars ≈75 tokens/turn; body 1,310 B ≈327 tokens on fire; `references/` 1,242 B ≈311 tokens, deeper still — only if step 3 runs |
| §4.3.2 form | `.claude/commands/checklist-refresh.md` — same fields, same injection, no `name`, no `references/` |
| §4.3.2 what the skill form bought | A directory (`references/`) for on-demand content, plus a `/skills` menu entry — not different behavior |
| §4.3.2 cost | 1,389 B ≈347 tokens, always inline, every firing — no conditional layer to defer to |
| §4.3.3 `disable-model-invocation: true` | `post-invoice-reversal` — you can invoke, Claude cannot; description not in context; standing cost **0** |
| §4.3.3 `user-invocable: false` | `money-minor-units-conventions` — Claude can invoke, you cannot; description always in context; standing cost ≈79 tokens/turn |
| §4.3.3 costs on fire | `post-invoice-reversal` 863 B ≈216 tokens; `money-minor-units-conventions` 1,097 B ≈274 tokens |
| Live-session blocker (both §4.3.1 and §4.3.3 prove steps) | Nested `claude` invocation refused by the auto-mode classifier — quoted verbatim in both sections |

## Self-test

<details><summary>1. Why does allowed-tools: Bash(git diff --stat *) on checklist-refresh not stop Claude from running other Bash commands while the skill is active?</summary>
allowed-tools pre-approves the listed pattern so it runs without a permission prompt for the turn that invokes the skill; it does not shrink the available tool pool. Every other tool, including other Bash invocations, is still governed by the session's ordinary permission settings. disallowed-tools is the field that actually removes tools from the pool while a skill is active.
</details>

<details><summary>2. Why is references/checklist-full.md not counted in either of §4.3.1's two standing cost numbers?</summary>
The listing cost (name + description, ≈75 tokens) is what is resident every turn regardless of invocation. The body cost (the rendered SKILL.md, ≈327 tokens) is paid once, the turn the skill actually fires. references/checklist-full.md is a third, deeper layer: it is not read at all unless the skill's own body — step 3 — tells Claude to load it, so it is not resident on a turn that merely invokes the skill without reaching that step.
</details>

<details><summary>3. What does moving checklist-refresh from a skill to a bare .claude/commands/checklist-refresh.md file actually change, given that $ARGUMENTS and the git diff --stat injection behave identically in both?</summary>
Nothing behavioral at invocation time. What changes is the file layout: the command form has no directory of its own to hold references/checklist-full.md, so the four checklist items had to be inlined into the single file and are paid in full every time the command fires, with no conditional layer behind them. The command also carries no separate /skills menu entry, and its name field is ignored — the command name comes from the file name instead.
</details>

<details><summary>4. Why does post-invoice-reversal's standing listing cost come out to zero, while money-minor-units-conventions's does not, even though both are skills with disallowed default invocation for one party?</summary>
disable-model-invocation: true removes the skill's description from context entirely — there is no listing entry for it to occupy on a turn that never invokes it by name, so its standing cost is zero. user-invocable: false only hides the skill from the user's typed / menu; its description stays in context exactly as an ordinary skill's would, so its standing listing cost (name + description) is unchanged and non-zero.
</details>

<details><summary>5. A teammate sets user-invocable: false on post-invoice-reversal instead of disable-model-invocation: true, reasoning that both fields "hide" the skill. What actually goes wrong?</summary>
user-invocable: false only removes the human's typed /post-invoice-reversal path; it leaves Claude fully able to invoke the skill automatically, because Claude-invocation is governed by disable-model-invocation, not user-invocable. The skill would remain listed to Claude with its description in context, so Claude could still decide, on its own initiative, to reverse a posted invoice from an ordinary conversation about invoices — precisely the outcome the skill was built to prevent.
</details>

<details><summary>6. Why does the SKILL.md frontmatter for checklist-refresh have to start with --- as the file's literal first line, and what happens if it doesn't?</summary>
Claude Code reads frontmatter only when the opening --- is the first line of the file. If even a single blank line or comment precedes it, Claude Code treats the entire file, --- markers included, as skill content rather than as frontmatter plus body — the skill silently never fires as configured, because none of name, description, allowed-tools, or the invocation-control fields are parsed.
</details>

<details><summary>7. Why is neither post-invoice-reversal nor money-minor-units-conventions live-tested against an actual Claude Code session in this file, and what stands in for that proof?</summary>
A nested claude invocation from inside this writing session was refused outright by the auto-mode classifier, both when testing checklist-refresh's live invocation and when testing the two invocation-control skills — the denial is quoted verbatim in both sections. In its place, the file walks each documented behavior through against skills' own quoted text (the invocation table, the "blocks the call" sentence, the "hides it from the / menu" sentence) term by term, and marks the live-observation gap explicitly as Unverified rather than asserting the outcome as observed.
</details>

## Open questions

- **Unverified:** live invocation of `checklist-refresh` in a real Claude Code session — that it reads
  the `git diff --stat` injection, then reads `references/checklist-full.md` on its own per step 3 —
  was not captured directly; a nested `claude` invocation from inside this writing task was refused by
  the auto-mode classifier (§4.3.1).
- **Unverified:** the live blocked-call message for `post-invoice-reversal` (`disable-model-invocation`)
  and the live absence of `money-minor-units-conventions` from `/` autocomplete
  (`user-invocable: false`) were not captured directly, for the same reason (§4.3.3). Both are worked
  through against `skills`' own documented text instead of asserted as observed.

---

**Leaves covered:** 4.3.1–4.3.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-36 to D-40 in the `skills/` folder draw this row's mechanisms
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 477
