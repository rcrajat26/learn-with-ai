# 21 AI for Coding — secrets, attribution and review capacity — INTERMEDIATE (§2.9.9–2.9.11)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [the `allowManaged*Only` lock family](02-the-lock-family.md) · Next: [PART 2 — the interview wrap-up](../91-interview-intermediate.md)

**Leaf-file note.** The dispatch for this file names its subject "secrets, attribution, and
review capacity" and supplies a full worked instruction for a secrets section (a `Read`/`Edit`
deny on `.env` and `secrets/**`, the fact that a `Read` deny does not stop an arbitrary
subprocess, `env` reaching hooks and Bash). The leaf file at `tmp/21-contract/leaves/gov-03.md`
assigns this file exactly three leaves — §2.9.9 (`[DOC]` attribution and audit), §2.9.10
(`[CASE]` the harness's own governance posture), §2.9.11 (`[CASE]` the rollout argument) — and
contains **no secrets leaf and no dedicated review-capacity leaf**. Per the leaf-file rule, the
leaf file is authoritative: this file covers §2.9.9–2.9.11 only. It does not open a standalone
"secrets" section, because doing so would mean covering a leaf that is not in the leaf file
while risking padding past the ones that are. The secrets mechanisms the dispatch describes are
all already on the page the reader has read: the `Read`/`Edit` deny pair on `.env` and
`secrets/**` and the fact that a `Read` deny does not stop an arbitrary subprocess are
`governance/01-the-threat-model.md`, §3's rank-1 and rank-3 controls (§1.4.17–1.4.19,
§1.4.39); `env` reaching hooks and Bash is `governance/02-the-lock-family.md`, §3. Nothing new
would be said by repeating them here. Review capacity appears below, in §3's discussion of
what a rollout costs, exactly to the extent §2.9.11's leaf earns it — as a forward pointer, not
a re-derivation.

## 1. Attribution and audit: who made this commit

`[DOC]` `[VERSION]` **Mental model.** A commit an agent authors looks, in `git log`, exactly
like a commit a person authored — same author line, same message shape — unless something
deliberately marks it otherwise. The question "which of the commits in this repository's
history came from an agent" is not one anyone asks in the moment a commit lands; it is a
question asked weeks or months later, during an incident review, a license audit, or a "why
does this function look like this" archaeology session, by someone who was not in the room
when the commit was made. Configuring attribution costs nothing today and is unrecoverable
after the fact — you cannot retroactively stamp a commit that already shipped without it.

**Why it exists.** Left to its own defaults, Claude Code adds a trailer to commits it authors
and a line to pull request descriptions it writes, so that provenance is present by default
rather than something a team has to remember to add. But "by default" cuts both ways: a team
running a squash-merge workflow, or one with a policy against exposing tooling internals in a
public-facing PR description, needs to turn the same behaviour off just as cleanly. `attribution`
and its relatives exist to make both directions — turn it on with a custom shape, or turn it off
entirely — first-class settings rather than something worked around with a `git commit --amend`
after the fact.

**How it works.** Six `settings-reference` keys, verified 2026-08-30 against
`https://code.claude.com/docs/en/settings-reference`, all filed under that page's "Git and
attribution" topic and all settable in **any** settings file — user, project, local, or managed:

| Key | What it does |
|---|---|
| `attribution` | Customises the attribution Claude Code adds to commits and pull requests — the parent key for the two below |
| `attribution.commit` | Changes or hides the trailer Claude Code adds to commits |
| `attribution.pr` | Changes or hides the attribution line in pull request descriptions |
| `attribution.sessionUrl` | Omits the claude.ai session link from cloud and Remote Control commits specifically |
| `includeGitInstructions` | Removes the built-in commit and PR instructions from the system prompt entirely |
| `prUrlTemplate` | Points PR links at an internal code-review tool instead of `github.com` |

`[VERSION]` A seventh key, `includeCoAuthoredBy`, still appears on the same page but is marked
**deprecated** — its own row says to use `attribution` to hide or change commit and PR
attribution instead. A reader who learned the old form from a blog post or a colleague's
`settings.json` from an earlier release line will reach for `includeCoAuthoredBy: false` first;
it may still work in v2.1.2xx as a compatibility shim, but the documented, forward-looking
control is `attribution.commit`, and a settings file built today should use that key, not the
one the docs already call out as superseded.

**Insight:** every key in this table is "Any file" scope — a plain developer setting, not a
member of the `allowManaged*Only` lock family from `governance/02-the-lock-family.md`. There is
no `allowManagedAttributionOnly` key documented at v2.1.2xx. That is a real gap relative to the
locks covered two files ago: an organization that wants provenance on every commit an agent
makes across its fleet cannot currently force it the way it can force a permission rule or a
hook — a developer can locally set `attribution.commit: false` and nothing at the managed tier
stops them. The honest answer to "can we guarantee every agent commit carries a trailer" at
v2.1.2xx is: only by convention and code review, not by a managed lock.

**No SVG.** This leaf has no diagram in the manifest; the table above is the mechanism map.

**Code.** A settings block for a team that wants attribution kept on but pointed at an internal
tool rather than GitHub, and that wants the session URL suppressed because their claude.ai
sessions live behind a VPN a reviewer outside the team cannot reach:

```json
{
  "attribution": {
    "commit": "Generated by Claude Code — reviewed by the committing engineer.",
    "pr": "Opened via Claude Code. See the linked story for the acceptance criteria.",
    "sessionUrl": false
  },
  "includeGitInstructions": true,
  "prUrlTemplate": "https://code-review.internal.example.com/pr/{number}"
}
```

**Gotcha.** `**Pitfall:**` Reaching for `includeCoAuthoredBy` because that is the name that
shows up in older documentation snapshots, blog posts, and colleagues' existing
`settings.json` files from a prior release line. **Symptom:** the setting appears to do
nothing, or behaves inconsistently across versions, because it is deprecated in the current
docs in favour of `attribution`. **Fix:** use `attribution.commit` / `attribution.pr` for any
new configuration; treat `includeCoAuthoredBy` as a value you might still see in an existing
file, not one you write into a new one.

> **Attribution settings** are `attribution` (and its `commit`/`pr`/`sessionUrl` children),
> `includeGitInstructions`, and `prUrlTemplate` — all "Any file" scope, all governing whether and
> how a commit or PR Claude Code authors declares that it did — with `includeCoAuthoredBy` kept
> only as the deprecated predecessor of `attribution`.

## 2. `[CASE]` The harness's own governance posture, assembled

`[CASE]` **Mental model.** Every control in this guide's §2.9.1–2.9.8 — a `deny` rule, a
blocking hook, the sandbox, least-privilege tool sets, a managed lock — is a primitive. A real
system's governance posture is never one of them; it is several assembled to cover the actual
gaps each one leaves on its own. The sdlc-harness repository is a working instance of that
assembly, not a hypothetical one, and it is worth reading precisely because its own comments
argue for *why* each layer exists rather than just declaring that it does.

**Why it exists.** A single `permissions.deny` entry for production AWS calls is fail-open in
three specific ways its own author documents: there is no guard at all during the window
between install and bootstrap; a fresh workspace has no pre-existing project-level deny-list to
inherit; and `/run-harness` can be invoked from any working directory, and project-scope
settings only apply while the working directory is inside the project. A team that stops at
"we wrote a deny rule" has covered none of those three gaps.

**How it works.** `plugins/sdlc-harness/scripts/bootstrap-user-scope.sh` is the harness's
answer to the first two gaps — it writes the deny-list into **user-scope** `~/.claude/settings.json`
rather than project scope, specifically because user scope survives regardless of which
directory a session starts from:

```
# Idempotent, fail-closed writer for the RFC 0002 section 6.3 prod guard's
# data half: required env vars + permissions.deny in USER-SCOPE
# ~/.claude/settings.json (never project scope -- see section 6.1/6.3:
# project scope does not apply once CWD leaves HARNESS_ROOT, so user scope
# is the only write that is a control regardless of where /run-harness runs
# from).
```

and its own exit-code contract refuses to claim success on a partial write:

```
# Exit codes:
#   0  already satisfied (no write needed) OR write + verify succeeded
#   1  post-write verification failed (refuses to report success -- the
#      whole point of this script existing: bootstrap must never claim
#      completion without the deny-list actually present)
#   2  usage error
```

That is rank-1 (`deny`) made durable against the two install-time gaps. The third gap — a
guard that only exists at bootstrap time is not a guard at *invocation* time — is closed by
`plugins/sdlc-harness/hooks/prod-guard-bash.sh`, a `PreToolUse` hook whose own header states the
same reasoning from the enforcement side: `permissions.deny` alone is fail-open, so the hook
makes "the user-scope deny-list is verified present" a runtime precondition of every harness
workflow invocation and every mutating-or-prod AWS command, not merely a one-time bootstrap
check. This is rank-1 and rank-2 from `governance/01-the-threat-model.md` layered on top of
each other for the same threat, closing gaps neither one closes alone.

`plugins/sdlc-harness/scripts/triage-aws-ro.sh` — already introduced in
`governance/01-the-threat-model.md` as "the tool set genuinely does not contain the dangerous
verb" — is rank-4 discipline in the same posture: its allowlist gate is nine read-only AWS
calls, full stop:

```
ALLOWED_CALLS=(
    "dynamodb get-item"
    "dynamodb query"
    "stepfunctions describe-execution"
    "stepfunctions list-executions"
    "stepfunctions get-execution-history"
    "sqs get-queue-attributes"
    "sqs receive-message"
    "sts get-caller-identity"
    "logs filter-log-events"
)
```

A call outside that list — anything with a write verb, however plausible — is denied with exit
code 1 before it ever reaches the real `aws` binary, so an incident-triage agent literally
cannot request a write against production, not because a rule tells it not to, but because the
verb is not in the table it is scripted against.

The fourth piece is a tool withheld from an agent by design, at the agent-definition level
rather than the permission-system level. `plugins/sdlc-harness/agents/calibrator.md` mines
session transcripts for recurring friction patterns and hands each one to a human for Jira
filing — and its own body states the boundary explicitly:

```
**No Jira API tool is ever given to this agent.** Filing a friction bug is a
human-confirmed, team-lead-altitude action (see `plugins/sdlc-harness/commands/calibrate.md`).
You mine and group the pattern; the team lead builds, previews, confirms, and files.
```

This is rank-4 (least-privilege tool sets) applied to an *external* system rather than a shell
command: the calibrator agent's job is pattern-mining, and filing a ticket on an external
tracker is a different, higher-stakes action than mining — one this design keeps behind a human,
by never handing the agent a tool that could do it unsupervised in the first place.

**No SVG.** D-66 in `governance/01-the-threat-model.md` already draws the shape this section
instantiates — the blast radius and the ranked controls that bound it. This section is that
diagram's controls, observed actually assembled in one running system, not a new picture.

**Gotcha.** `**Pitfall:**` Reading `bootstrap-user-scope.sh`, `prod-guard-bash.sh`, and
`triage-aws-ro.sh` as three independent, redundant safety nets and concluding that any one of
them alone would have been "probably fine." **Symptom:** a team ships only the deny-list write
(skips the `PreToolUse` hook, say, as "belt and suspenders we don't need yet") and is then
surprised that a session invoked from an unrelated working directory, before the user-scope
write ever ran, sailed straight through. **Fix:** each of the four pieces closes a *specific*
gap the others leave open — the deny-list write closes the "no pre-existing project settings"
gap, the hook closes the "guard must hold at invocation time, not just at bootstrap time" gap,
the allowlist closes the "least privilege must mean the verb isn't available, not that a rule
says not to use it" gap, and the withheld Jira tool closes the "an external side-effect needs a
human, not a rule" gap. Removing any one reopens the specific gap it was closing, not a
generic amount of "extra" safety.

> **The harness's governance posture** is not one control — it is a fail-closed prod-AWS
> deny-list durable across the install-and-bootstrap window (`bootstrap-user-scope.sh`), a
> `PreToolUse` hook that re-verifies that guard at every invocation regardless of working
> directory (`prod-guard-bash.sh`), a verb-level allowlist that removes the dangerous action from
> the tool set entirely rather than trusting a rule to withhold it (`triage-aws-ro.sh`), and a
> tool never handed to an agent at all because the action it would perform belongs to a human
> (`calibrator.md`'s withheld Jira access) — four different gaps, four different mechanisms,
> assembled rather than substituted for each other.

## 3. `[CASE]` The rollout argument: capability as a versioned plugin, not tips in a wiki

`[CASE]` **Mental model.** "Be careful with the agent" typed into a wiki page has no version, no
dependency graph, no rollback, and no way to prove after the fact that it didn't make things
worse. A capability shipped as a plugin has all four, because a plugin is exactly the kind of
artifact software engineering already knows how to manage — and the argument a Staff engineer
has to make to a skeptical organization is precisely that an agentic capability should be held
to that same bar, not a lower one because it happens to be "just prompts."

**Why it exists.** Once more than a few engineers depend on a shared set of hooks, agents,
skills, and playbooks, informal distribution — copy this `CLAUDE.md` section into your own,
paste this hook script in — stops scaling for the same reason copy-pasted library code stops
scaling: nobody can tell which copy is current, a fix to one copy doesn't reach the others, and
there is no single point to roll a bad change back from.

**How it works.** The sdlc-harness itself is packaged this way. `plugins/sdlc-harness/.claude-plugin/plugin.json`
carries a semantic version and a declared dependency, not an informal "latest" pointer:

```json
{
  "name": "sdlc-harness",
  "version": "0.10.2",
  "description": "AI-SDLC harness — deterministic multi-agent workflows (full-sdlc, plan-project, implement-story, post-deploy-smoke) for running Claude agents across the software development lifecycle.",
  "author": {
    "name": "IG Group"
  },
  "license": "proprietary",
  "dependencies": [
    { "name": "ig-superclaude", "marketplace": "ig-superclaude" }
  ]
}
```

`plugins/sdlc-harness/hooks/hooks.json` ships the hooks as part of that same versioned unit —
three `SessionStart` handlers and one `PostToolUse` handler, arriving and being removed
atomically with a version bump rather than as separately-maintained scripts a developer might
or might not have pulled:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/check-init.sh\"" },
          { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/prod-guard-session-start.sh\"" },
          { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/calibration-nudge.sh\"" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/doc-update-reminder.sh\"" }
        ]
      }
    ]
  }
}
```

And `harness/evals/` is the measurement half — a quality-regression suite that runs whenever a
"quality-bearing artifact" (a judge rubric, a workflow, a template) changes, scoring a frozen
corpus of goldens and seeded defects against recorded baselines in `baselines.yaml`. Its own
`README.md` states the non-negotiable direction of travel for those baselines: "Baselines may
rise on a reviewed improvement, **never silently fall** — lowering one is an explicit commit."
That sentence is the rollback-and-measurement half of the argument in one line: a regression in
prompt or rubric quality is a number that moved the wrong way and was caught, not an anecdote
someone eventually notices.

**What this buys.** Three things a wiki page cannot: **review** (a plugin version bump is a diff
someone approves, not an edit someone happens to notice); **rollback** (pin the dependency back
to `0.10.1` and the hooks, agents, and skills that shipped in `0.10.2` disappear atomically,
rather than needing to be hand-reverted one copy-paste at a time); and **measurement** (the eval
suite's baselines are a machine-checkable answer to "did this change make things worse," not a
gut feeling).

**What it costs.** The version and dependency discipline is real overhead — someone has to cut
releases, someone has to maintain the eval corpus and keep its baselines current as the
capability legitimately improves, and a dependency on `ig-superclaude` at the marketplace level
means this plugin's own rollout is coupled to that marketplace's rollout. None of that is free,
and the rollout argument only wins the trade if the organization is actually going to scale
past the size where informal distribution was working.

`[X-REF verification/03]` There is a second, sharper cost this rollout argument runs into once
an organization does scale: a versioned plugin with hooks and eval suites lowers the cost of
producing more agent output, but it does nothing by itself about the cost of a human *reviewing*
that output — and that second cost does not scale the same way. §0.1.8 already established the
reason a human has to stay in that loop at all: fluency is worthless as a correctness signal, so
an agent's own claim that a task succeeded is the weakest evidence available that it did, which
is exactly why "we shipped it as a plugin with an eval suite" cannot be read as "so a human no
longer needs to look at the diff." What agents can produce, given more compute and more
capability, rises. What a human can genuinely review — read closely enough to catch the
mistake the eval suite didn't anticipate — does not rise at the same rate; it is closer to flat,
because it is bounded by the same human attention this whole guide has spent §2.9.1–2.9.10
arguing cannot be replaced by a rule. Past the point where those two lines cross, adding another
agent adds unreviewed diffs, not velocity. `verification/03-internals-c-automation-and-review-capacity.md`
(§3.10.11) draws that crossing point as D-93 and works the argument through in full; this file
only owes the reader the shape of the claim and the pointer, because the diagram and the
worked argument both belong to PART 3.

**Gotcha.** `**Pitfall:**` Treating "we shipped it as a versioned plugin with hooks and an eval
suite" as the finished rollout, full stop. **Symptom:** the plugin ships, adoption grows, the
eval suite stays green — and six months later a postmortem finds that most of the agent-authored
diffs landing on `main` were approved by reviewers skimming for shape rather than reading for
correctness, because the volume of diffs grew past what the review team could actually read
closely, and nothing about the plugin's own versioning or eval gate measures *that*. **Fix:**
the plugin argument buys review, rollback, and measurement of the *capability* — it does not by
itself buy review capacity for the *output volume* that capability enables, and a rollout plan
that stops at "shipped as a plugin" without a plan for the review-capacity ceiling has only
solved the easier half of the problem.

> **The rollout argument** is that agentic capability belongs in a versioned, dependency-managed
> plugin with its own hooks and eval suite — buying review, rollback, and measurement a wiki page
> cannot — at the cost of real release and eval-maintenance overhead, and that this argument
> alone does not solve the separate, harder problem of review capacity once the plugin succeeds
> at its job and the volume of agent output grows past what humans can still read closely.

## Pitfalls

**Pitfall:** setting `includeCoAuthoredBy` because that is the name remembered from an older
guide or an existing `settings.json`. **Symptom:** inconsistent or absent effect across
versions, because the key is deprecated in favour of `attribution`. **Fix:** configure
`attribution.commit` / `attribution.pr` in new settings files. **Why people believe it:** the
deprecated key still appears in the documentation's own reference table and in files written
before `attribution` existed, so it reads as current.

**Pitfall:** treating any one of `bootstrap-user-scope.sh`, `prod-guard-bash.sh`, or
`triage-aws-ro.sh` as redundant with the others and safe to drop. **Symptom:** removing one
reopens the exact gap that piece was closing — the install-window gap, the invocation-time gap,
or the "verb not available at all" gap — while the remaining pieces provide no coverage for it.
**Fix:** treat the four-piece assembly in §2 as load-bearing in combination, not as three
independent nets stacked for extra margin. **Why people believe it:** all four pieces sit under
one umbrella term ("the prod guard"), which reads as one control rather than four.

**Pitfall:** believing a versioned plugin with hooks and an eval suite is a complete governance
rollout on its own. **Symptom:** the plugin ships clean, the eval suite stays green, and the
organization only discovers months later that reviewers were rubber-stamping a volume of
agent-authored diffs no team could actually read closely. **Fix:** plan for the review-capacity
ceiling separately — see `verification/03-internals-c-automation-and-review-capacity.md`
(§3.10.11, D-93) — rather than treating "shipped as a plugin" as the end of the rollout. **Why
people believe it:** the plugin argument answers every question about the *capability itself*
(review, rollback, measurement), so it feels complete even though it never addressed the
*output volume* the capability enables.

## Cheat sheet

| Item | One line |
|---|---|
| `attribution` / `.commit` / `.pr` / `.sessionUrl` | Customise or hide the commit trailer, PR line, and session-URL attribution; "Any file" scope |
| `includeGitInstructions` | Removes the built-in commit/PR instructions from the system prompt |
| `prUrlTemplate` | Points PR links at an internal review tool instead of `github.com` |
| `includeCoAuthoredBy` | Deprecated — use `attribution` instead |
| No managed lock on attribution | No `allowManagedAttributionOnly` key at v2.1.2xx — a developer can still turn attribution off locally |
| `bootstrap-user-scope.sh` | Writes the prod-AWS deny-list to **user scope**, fail-closed, verifies the write before reporting success |
| `prod-guard-bash.sh` | `PreToolUse` hook re-verifying the deny-list is present at every invocation, regardless of CWD |
| `triage-aws-ro.sh` | Nine-call read-only allowlist; anything else is denied before reaching `aws` |
| `calibrator.md` | Never given a Jira tool — filing is human-confirmed, team-lead-altitude only |
| `plugin.json` version + `dependencies` | Capability as a versioned, dependency-declared artifact |
| `hooks.json` | Hooks arrive/leave atomically with the plugin version |
| `baselines.yaml` | Eval baselines "may rise… never silently fall" — the measurement half of the rollout argument |
| Review-capacity ceiling | What agents can produce rises; what humans can review does not — full treatment in `verification/03-internals-c-automation-and-review-capacity.md`, D-93 |

## Self-test

1. Why can a developer still disable commit attribution locally even at an organization that wants it enforced fleet-wide?
<details><summary>Answer</summary>Every attribution key (`attribution`, `attribution.commit`, `attribution.pr`, `attribution.sessionUrl`, `includeGitInstructions`, `prUrlTemplate`) is documented as "Any file" scope, and there is no `allowManagedAttributionOnly` key in the `allowManaged*Only` family at v2.1.2xx. A managed source can set a value, but nothing stops a developer's own settings file from overriding it the way the lock family stops it for permissions, hooks, MCP servers, or sandbox allowlists.</details>

2. Why does `bootstrap-user-scope.sh` write the prod-AWS deny-list to user scope rather than project scope?
<details><summary>Answer</summary>Because project-scope settings only apply while the session's working directory is inside the project, and `/run-harness` can be invoked from any CWD. A user-scope write is a control regardless of where the workflow runs from; a project-scope one would silently stop applying the moment the CWD left the project tree.</details>

3. What specific gap does `prod-guard-bash.sh` close that `bootstrap-user-scope.sh` alone does not?
<details><summary>Answer</summary>`bootstrap-user-scope.sh` only guarantees the deny-list is present after bootstrap runs; it says nothing about invocation time. `prod-guard-bash.sh` is a `PreToolUse` hook that re-verifies the deny-list is present at every harness-workflow invocation and every mutating/prod AWS command, making the guarantee hold at runtime rather than only at bootstrap.</details>

4. Why is `triage-aws-ro.sh`'s allowlist a stronger form of least privilege than a permission rule that denies write verbs?
<details><summary>Answer</summary>The allowlist removes every verb except nine specific read-only calls from what the wrapper script will even forward to the real `aws` CLI — the dangerous verb is not present in the tool set at all, rather than being present and merely disallowed by a rule the model's own tool call could in principle still attempt.</details>

5. Why is the calibrator agent never given a Jira API tool, even though its whole job is to surface bugs worth filing?
<details><summary>Answer</summary>Filing a ticket on an external tracker is a human-confirmed, team-lead-altitude action in this design. The calibrator's job is to mine and group friction patterns; handing it a Jira tool would let it take an external, harder-to-reverse action unsupervised, which is exactly the class of action this design keeps behind a human by withholding the tool rather than relying on a rule to stop it being used.</details>

6. What three things does packaging a capability as a versioned plugin with hooks and an eval suite buy, according to this file, and what does it not automatically buy?
<details><summary>Answer</summary>It buys review (a version bump is a diff someone approves), rollback (pin the dependency back and the change disappears atomically), and measurement (eval baselines that must rise on a reviewed improvement and must never silently fall). It does not automatically buy review capacity for the growing volume of agent output the capability enables — that is a separate ceiling.</details>

7. Why can't a `CLAUDE.md` instruction or a rule fix the review-capacity ceiling the way it can fix a permission gap?
<details><summary>Answer</summary>Because the ceiling isn't a permission being granted or withheld — it's the flat rate at which humans can read a diff closely enough to catch what an eval suite didn't anticipate. §0.1.8 already established that an agent's own claim of success is the weakest evidence of correctness, which is exactly why a human has to read the diff at all; no rule increases how many diffs a human can read per day.</details>

## Open questions

None.

---

**Leaves covered:** 2.9.9–2.9.11 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-66 and D-67 in `governance/01` draw the threat model, D-68 in `governance/02` tables the locks, and D-93 in `verification/03-internals-c` draws the review-capacity ceiling
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 418
