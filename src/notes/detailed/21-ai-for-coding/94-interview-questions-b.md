# 21 AI for Coding — the questions, second four — INTERVIEW (§5.1.5–5.1.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 5 of 6** | [Index](00-index.md)
Previous: [the questions, first four](94-interview-questions-a.md) · Next: [the questions, third four](94-interview-questions-c.md)

Four more questions at speaking length — the answer a candidate would actually say, not a summary of
where the mechanism lives. Read `94-interview-questions-a.md` first for the register; this file does
not repeat any of §5.1.1–5.1.4's material.

## §5.1.5 "Deny beats allow — why does that matter?"

**The one-sentence trap, then the deeper point it's standing in for.**

> The trap in one sentence: a broad `deny` rule can't carry allowlist exceptions, because `deny` is
> checked first and stops the pipeline the instant it matches — so `permissions.deny: ["Bash(aws
> *)"]` blocks `Bash(aws s3 ls)` even with `permissions.allow: ["Bash(aws s3 ls)"]` sitting right next
> to it, and no narrower allow rule anywhere in any settings layer can rescue it, because the pipeline
> never reaches the allow list at all. But the reason that trap exists is bigger than one gotcha: deny
> composition isn't "highest layer wins," which is how most engineers already think about settings
> precedence everywhere else in this tool. General settings keys — like which model to use, or which
> statusline to render — really do resolve as "the highest layer that sets the key wins outright,"
> managed beats command-line beats project beats user. Permission deny doesn't work that way at all.
> Every settings layer's deny rules are collected together first, and if *any* of them matches, the
> call is blocked — full stop, and that block reaches through `--allowedTools` on the command line and
> through managed settings the same way. So the fix for the `aws` case isn't a narrower allow rule, it
> never was; it's narrowing the deny rule itself — `Bash(aws * !s3)`, or listing the destructive verbs
> explicitly and leaving `aws s3 ls` unmatched by anything. And a `PreToolUse` hook doesn't rescue it
> either, for the same underlying reason: a hook fires after rule evaluation, so it can only narrow
> what a rule already allows — turn an allow into an ask or a deny — it structurally cannot carve an
> exception into a deny that's already fired, because by the time the hook runs the pipeline has
> already stopped. If you don't say both halves — the sentence, and the fact that this is a different
> composition rule than the one governing everything else in settings — the answer sounds like a
> single memorized gotcha instead of an understood mechanism.

![D-28 — Permission evaluation: deny, then ask, then allow](diagrams/D-28-permission-evaluation-order.svg)

**D-28** — Permission evaluation: `deny` collected across every layer and checked first, then `ask`,
then `allow`; first match wins, and no allow rule is ever reached once a deny matches.

**Interview:** "If I add a narrower allow rule, why doesn't it override the broad deny?" — Because
deny composition isn't precedence at all; every layer's deny rules are pooled and checked before any
allow rule is consulted, so a matching deny stops the pipeline before the allow list is even read. Fix
the deny rule, not the allow rule.

## §5.1.6 "What is the difference between `CLAUDE.md`, a skill, and a hook?"

**Always-on context, on-demand context, guaranteed execution — and the mechanical reason each one is
what it is.**

> The three sound similar because they all "give Claude instructions," but they sit on three different
> points of a single spectrum: how much you pay for them by default, and how much you can trust them
> to actually happen. `CLAUDE.md` is always-on context — every file in its hierarchy loads into every
> turn of the session, whether or not the current task touches what it describes, which is exactly why
> it belongs to conventions that never change rather than to a fifty-item procedure library: it's
> delivered to the model as a user message inserted before your own first turn, not as part of the
> system prompt, and that's not a technicality — it means the model is *choosing* to follow it the
> same way it chooses to follow anything else you type, weighed against everything else in the
> conversation, not obeying a privileged instruction channel. A skill is on-demand context: its name
> and one-line description sit resident in every turn so the model can decide whether to reach for it,
> but the actual body — the procedure, the reference files — loads only on the turn the skill fires.
> That's the entire reason fifty skills are affordable where fifty `CLAUDE.md` entries would not be —
> you're paying for fifty short listings on every turn, not fifty full bodies. A hook is the only one
> of the three that isn't context at all — it's code the harness runs regardless of what the model
> decided to do, on a fixed event like `PreToolUse` or `SessionStart`, and its exit code or JSON output
> can block a tool call before it executes. `CLAUDE.md` and a skill are both things the model reads and
> may or may not act on; a hook is something that runs whether or not the model cooperates. That last
> distinction is the one to lead with if the interviewer pushes on "why not just put it all in
> `CLAUDE.md`": a rule that must never be violated — never touch this table, always run this linter
> first — cannot live in `CLAUDE.md` or a skill at all, because both are advisory; it has to be a hook,
> because a hook is the only one of the three actually enforced by code the model's own reasoning can't
> talk its way around.

![D-41 — Which mechanism for which need](diagrams/D-41-mechanism-decision-tree.svg)

**D-41** — Which mechanism for which need, terminal by terminal: `CLAUDE.md` for what's always true,
a skill for what's sometimes needed, a hook for what must never be skipped. Each terminal carries its
enforcement strength — context the model weighs, versus code the harness runs regardless.

**Interview:** "Why not just put everything in `CLAUDE.md`?" — Because `CLAUDE.md` arrives as a user
message the model may weigh against the rest of the conversation, not as enforced code; anything that
must happen every single time — a destructive-command block, a formatting pass — has to be a hook,
because a hook runs whether or not the model decided to cooperate, and `CLAUDE.md` structurally
cannot.

## §5.1.7 "When do you use a subagent?"

**Verbose-in/small-out, parallel with disjoint writes, a different capability set — and the 2× cost
you're paying to get there.**

> Three shapes of task earn a subagent dispatch. First, verbose-in/small-out: a task that has to read
> or churn through a lot — a dozen log files, a wide grep across the repo — to produce a short answer.
> Dispatched, all of that reading happens inside the subagent's own context window, which is discarded
> the moment it returns; only its final message re-enters my transcript, so a 150,000-token
> investigation can come back as a 200-word summary that's all that ever gets re-sent on every
> subsequent turn for the rest of the session. Second, genuine parallelism over disjoint writes —
> several independent pieces of work that don't touch the same files, dispatched together rather than
> one after another. Third, a different capability set: a subagent can be scoped to a narrower tool
> list or a different model than my main session, which is its own reason to reach for one even with
> no context-isolation benefit at all. None of that is free, though, and I'd rather state the cost
> honestly than pretend a subagent is a free lunch: a fresh dispatch pays a fixed per-dispatch tax
> before it does a single token of real work — a new system prompt, fresh tool schemas, the
> `CLAUDE.md` hierarchy re-supplied, the task string itself — none of which is servable from my
> already-cached inline prefix, because a non-fork subagent starts with none of that prefix at all. On
> a worked example I've actually priced out — 2,000 tokens for the system prompt, 1,200 for tool
> schemas, 1,300 for `CLAUDE.md`, 300 for the task string, plus 3,000 tokens of the work itself and 200
> tokens for the returned message re-entering my transcript — that's 8,000 tokens total for the
> subagent path, against a 4,000-token marginal cost for doing the same modest task inline against an
> already-resident cached prefix: `8,000 / 4,000 = 2.0×`. That 2.0× isn't a law of physics, it's this
> worked example's answer — the ratio is entirely a function of how large the inline marginal cost
> would have been, so a task with almost nothing new to process inline can push the ratio well past
> 2×, and a task with a lot of genuinely new inline work dilutes the same fixed tax toward a smaller
> multiple. A team of subagents pushes that to 3–4×, because every member re-pays that same fixed tax
> independently and the lead additionally pays for the coordination messages assigning and collecting
> the work. So the actual decision isn't "is 2× acceptable" in isolation — it's whether the task's
> value is mostly in the exploration or mostly in the final answer; for the first kind, a 150,000-token
> burn that returns 200 words wins by two to three orders of magnitude on the ledger that actually
> compounds, my own transcript's re-send cost, even while losing on the total-token ledger. One
> constraint that isn't a cost trade-off at all and that people forget: `AskUserQuestion` is not
> available inside a subagent under any circumstance, so if the task needs a human decision partway
> through, that gate has to sit in the parent session before dispatch — the subagent can't pause and
> ask, it can only guess or come back one turn too late asking to be asked.

![D-46 — Where a subagent's 2× comes from](diagrams/D-46-subagent-2x-cost.svg)

**D-46** — Where a subagent's 2× comes from: the fixed per-dispatch tax against a modest task's
marginal inline cost, `8,000 / 4,000 = 2.0×`; and the case it wins anyway — 150,000 tokens burned
inside, ~200 words re-entering the parent's transcript.

**Interview:** "Isn't a subagent always more expensive, so why use one?" — Yes, roughly 2× total
tokens on a modest task, because of a fixed per-dispatch tax a same-conversation tool call never pays;
but the ledger that actually decides most real choices is what re-enters the *parent's* re-sent
transcript, and a large exploratory task returning a small summary wins that ledger overwhelmingly
even while losing the total-token one.

## §5.1.8 "How would you run this in CI?"

**The invocation, the three ceilings, the settings fix, the credential, and what must not be there.**

> Headless in CI is `claude -p "<the task>" --output-format json`, never the interactive mode — `-p`
> means print the result and exit rather than hold a terminal open, and `--output-format json` turns
> the exit into a machine-parseable envelope with fields like `total_cost_usd`, `num_turns`, and
> `is_error` that a pipeline can branch on without scraping text. Around that one call sit three
> independent ceilings, and they need to be three because each bounds a different resource and needs
> its own kind of exception: `--max-turns` bounds agency — how many agentic turns the run gets before
> it's stopped, hard, with an error rather than a graceful partial result; `--max-budget-usd` bounds
> money — cumulative USD spend, subagent spend included; and a wrapper's own wall-clock timeout bounds
> time, independently of both, because a run can sit on cheap, fast-looping turns for hours without
> ever tripping a cost ceiling sized for a normal task. None of the three substitutes for another, and
> the arithmetic proves it rather than just asserting it: a real, measured `--max-budget-usd 0.0001`
> call still billed **$0.06197725** — a 619× overshoot on a cap that was supposed to hold spend near
> zero — because the ceiling is enforced *between* API calls, not partway through one; the call that's
> already in flight when the check runs finishes and gets billed regardless of the cap. Next, the
> settings fix: pass `--settings <absolute path>`, not `--setting-sources project`, because
> `--setting-sources project` resolves relative to the process's `cwd`, and a subagent or a per-story
> worktree frequently has no local `.claude/` at all — which is exactly the root cause behind an
> incident where a coder subagent silently lost its `permissions.allow`/`deny` rules and fell back to
> bare `acceptEdits` defaults that couldn't run `mvn`, `git commit`, `chmod`, or `java`. `--settings
> <absolute path>` loads a specific file independent of `cwd`, so it doesn't care where the process
> happened to be launched from. For the credential, `claude setup-token` generates a long-lived OAuth
> token meant to be run once, interactively, by a human, and stored as a CI secret — it's the right
> tool for giving an unattended pipeline a credential without a browser to click through consent in.
> I'll say plainly that I did not run it live while building this out, because the command prints a
> live, usable credential to stdout the moment it runs — which is exactly the property that makes it
> the wrong thing to demonstrate on a shared screen or paste into a transcript, and the same discipline
> applies to CI logs: never let that token, or the output of a command that could print it, land in a
> build log or a script's stdout capture. Last, what must not be present in a CI configuration, because
> each is a real incident waiting to happen rather than a hypothetical: `bypassPermissions` outside a
> container — it disables the permission layer entirely, on infrastructure that runs untrusted
> automation; an unpinned dependency — a floating version that changes what a pipeline does between two
> runs of the identical commit; a `Stop` hook slow enough that someone eventually just disables it
> rather than waits on it, which quietly removes whatever guarantee it existed for; and no human on any
> outward-facing or irreversible action, because CI has no equivalent of a human confirmation gate
> unless one is deliberately built in. One correction worth stating unprompted, because it's the
> subtler and more commonly wrong version of "does CI trust a repo automatically": a `-p` or SDK
> session run against a folder nobody has trusted does **not** apply that repository's committed
> `allow` rules — it runs with those rules withheld and prints a `this workspace has not been trusted`
> warning to stderr, which is the safe direction. The real hole isn't the first run; it's that once any
> human or pre-seeded state has trusted a given checkout path a single time, trust is keyed to that
> path and never re-checked against the commit's content, so every later `-p`/SDK run in that same path
> silently applies whatever `allow` rules the currently checked-out commit contains — including one
> that just landed in a pull request nobody reviewed for that purpose.

**Interview:** "What's the one flag people get wrong when moving a Claude Code call from local into
CI?" — `--setting-sources project`, because it resolves against `cwd`, which in a subagent worktree or
a CI checkout is frequently not where the intended `.claude/` lives; `--settings <absolute path>`
loads the file directly and doesn't care where the process was launched from.

---

## Pitfalls

**Belief in action:** "I denied the broad case and allowed the narrow one, so the narrow allow should
win as an exception." **Surprising outcome:** the narrow allow is never even reached — `Bash(aws *)`
in `deny` blocks `Bash(aws s3 ls)` in `allow`, and adding more allow rules, or a `PreToolUse` hook that
returns `permissionDecision: allow`, changes nothing, because both a hook and every layer's allow list
sit downstream of a deny match that already stopped the pipeline. **What actually gets it right:**
narrow the deny rule itself — `Bash(aws * !s3)`, or an explicit list of the destructive verbs — so the
call in question is simply never matched by anything that blocks it. **Why people believe it:**
"more specific wins" is how settings precedence works for ordinary keys elsewhere in this tool, and it
reads naturally onto permission rules too, but deny composition is a pooled-block rule, not a
precedence rule, and the two get conflated constantly.

**Belief in action:** `CLAUDE.md`, a skill, and a hook are three interchangeable places to put an
instruction, and the choice is a style preference. **Surprising outcome:** a "must never happen"
instruction placed in `CLAUDE.md` or a skill gets violated under exactly the conditions it existed to
prevent — a long session where compaction evicted it, or a task that never triggered the skill —
because both are context the model weighs, not enforced code. **What actually gets it right:** route
"always true regardless of task" to `CLAUDE.md`, "needed sometimes, procedural" to a skill, and "must
never be skipped, ever" to a hook, because only a hook is code the harness runs whether or not the
model decided to cooperate. **Why people believe it:** all three read as "instructions I give Claude,"
and nothing about writing them distinguishes advisory context from enforced execution until something
actually goes wrong.

**Belief in action:** a subagent is worth dispatching whenever a task feels big or research-heavy,
without pricing what it costs. **Surprising outcome:** a modest task dispatched to a subagent burns
roughly double the tokens of doing it inline — 8,000 against 4,000 in a worked example — for no
context-isolation benefit at all, because the fixed per-dispatch tax (fresh system prompt, tool
schemas, `CLAUDE.md`, task string) dominates when the task itself is small. **What actually gets it
right:** dispatch the tasks whose value is lopsided toward exploration — a large, throwaway
investigation that returns a small summary — because that is the shape where the parent-transcript
ledger, not the total-token ledger, decides the bill, and keep small, cheap-inline tasks in the main
session. **Why people believe it:** "isolate the context" sounds like a pure win with no downside
stated, when the downside is a specific, priced fixed tax that a same-conversation tool call never
pays.

**Belief in action:** `--max-turns` or `--max-budget-usd` alone is a sufficient guardrail for an
unattended CI run, and whichever one is set covers the other's failure mode too. **Surprising
outcome:** a run can die mid-task at a turn ceiling having spent almost nothing, or blow past a naive
dollar expectation because the budget check only fires between calls — a real `--max-budget-usd
0.0001` call still billed $0.06197725, a 619× overshoot, because the in-flight call finished and got
billed before the next check could stop it. **What actually gets it right:** set all three ceilings
independently — turns for agency, budget for money, a wrapper wall-clock timeout for time — because
each bounds a resource the other two don't see at all, and layer them with a way to resume or salvage
partial work rather than treating any one of them as sufficient on its own. **Why people believe it:**
"turns" and "dollars" both sound like proxies for "how much this run is doing," so capping one feels
like it should implicitly bound the other, but an agent loop can be turn-cheap and cost-expensive or
the reverse depending entirely on what each turn does.

## Cheat sheet

| Question | The one sentence that must be in the answer | The number or ranking that proves you know it |
|---|---|---|
| Deny beats allow — why does that matter? | A broad deny can't carry allowlist exceptions because deny is pooled across every layer and checked before allow is ever read — it isn't "highest layer wins," and a `PreToolUse` hook can't rescue it either since a hook only narrows. | `Bash(aws *)` in deny blocks `Bash(aws s3 ls)` in allow; fix is `Bash(aws * !s3)`, not a wider allow |
| `CLAUDE.md` vs skill vs hook? | Always-on context, on-demand context, guaranteed execution — only a hook is code the harness runs regardless of what the model decides. | `CLAUDE.md` arrives as a user message, not the system prompt; a skill's body loads only on the turn it fires |
| When do you use a subagent? | Verbose-in/small-out, parallel disjoint writes, a different capability set — paid for with a fixed per-dispatch tax. | `8,000 / 4,000 = 2.0×` (3–4× for a team); 150K burned inside vs. ~200 words returned; `AskUserQuestion` unavailable inside a subagent |
| How would you run this in CI? | `-p --output-format json`, three independent ceilings (turns/money/time), `--settings <absolute path>` not `--setting-sources project`, `setup-token` for the credential. | `--max-budget-usd 0.0001` still billed $0.06197725 (619× overshoot); no `bypassPermissions` outside a container, no unpinned dependency, no slow disabled `Stop` hook, no missing human gate |

## Self-test

1. Why doesn't adding a narrower rule to `permissions.allow` override a broad `permissions.deny` match?
<details><summary>Answer</summary>Deny composition isn't precedence — every settings layer's deny rules are pooled together and checked before the allow list is consulted at all. A matching deny stops the evaluation pipeline immediately, so the allow list, no matter how narrow or specific, is never reached for that call.</details>

2. Can a `PreToolUse` hook that returns `permissionDecision: allow` override a matching deny rule? Why or why not?
<details><summary>Answer</summary>No. A hook fires after rule evaluation and can only narrow what a rule already permits — turning an allow into an ask or a deny — it has no mechanism to carve an exception into a deny that has already matched and stopped the pipeline.</details>

3. What does "settings precedence is highest-layer-wins" actually apply to, and why doesn't it apply to permission deny rules?
<details><summary>Answer</summary>It applies to ordinary settings keys — model choice, statusline, and similar single-value settings — where the highest layer that sets the key wins outright. Permission deny doesn't resolve that way at all: every layer's deny rules are collected and any match blocks, regardless of which layer it came from, which is a pooled-block rule rather than a precedence rule.</details>

4. Why is `CLAUDE.md` advisory rather than enforced, mechanically?
<details><summary>Answer</summary>CLAUDE.md content is delivered to the model as a user message inserted before the first real turn, not as part of a privileged system-prompt channel. The model weighs it against everything else in the conversation the same way it weighs any other text, rather than obeying it as configuration the harness enforces.</details>

5. Why are fifty skills affordable in context terms when fifty equivalent CLAUDE.md entries would not be?
<details><summary>Answer</summary>A skill keeps only its name and a short description resident in every turn so the model can decide whether to invoke it; the full body loads only on the turn it actually fires. CLAUDE.md content has no such gate — every file in the hierarchy loads into every turn regardless of whether the current task touches it, so its cost scales with total entries rather than with how many actually get used.</details>

6. Work through the arithmetic behind the "2×" subagent cost figure: what four costs make up the numerator, and what makes up the denominator?
<details><summary>Answer</summary>Numerator (subagent, cold-start): a fresh system prompt (2,000 tok) + fresh tool schemas (1,200 tok) + the CLAUDE.md hierarchy re-supplied (1,300 tok) + the task string (300 tok) + the work itself (3,000 tok) + the returned message re-entering the parent transcript (200 tok) = 8,000 tokens. Denominator (inline, marginal only): the work's fresh processing (1,000 tok) + the output (3,000 tok) = 4,000 tokens, excluding the already-resident cached prefix as sunk cost. 8,000 / 4,000 = 2.0×.</details>

7. Why is 2.0× "this worked example's answer" rather than a fixed law?
<details><summary>Answer</summary>The fixed per-dispatch tax (4,800 tokens: system prompt, tool schemas, CLAUDE.md) stays roughly constant regardless of task size, so the ratio it produces depends entirely on how large the inline path's marginal cost would have been. A task with a larger marginal inline cost dilutes the same fixed tax toward a smaller multiple; a task with almost no marginal inline cost pushes the ratio well past 2×.</details>

8. A subagent's task requires asking the user a yes/no question partway through. What actually happens, and what should have been done instead?
<details><summary>Answer</summary>Nothing asks anything — AskUserQuestion is withheld from every subagent regardless of type. The subagent either guesses and proceeds on an unreviewed assumption, or its final message comes back asking to be asked, one turn too late. The fix is to resolve the decision in the parent session before dispatch and hand it down as a settled fact in the task string, not as an open question for the subagent to raise mid-task.</details>

9. Why does capping `--max-budget-usd` alone not guarantee a run stays near that budget?
<details><summary>Answer</summary>The budget ceiling is enforced between API calls, not within one — a call already in flight when the cumulative check runs finishes and gets billed regardless of the cap. A measured `--max-budget-usd 0.0001` run still billed $0.06197725, a 619× overshoot, purely from a single call finishing after the cap had effectively been reached.</details>

10. Why is `--settings <absolute path>` the fix for a subagent that silently loses its permission rules, and not `--setting-sources project`?
<details><summary>Answer</summary>`--setting-sources project` only says a project-scope layer should be consulted; it still has to be found by walking from the process's cwd. A subagent's worktree or a CI checkout frequently has no local .claude/ at that cwd, so the project layer silently fails to load. `--settings <absolute path>` loads a specific file directly, independent of cwd, so it doesn't matter where the process was launched from.</details>

## Open questions

None.

---

**Leaves covered:** 5.1.5–5.1.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** re-embedded by id where an answer turns on one
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 290
