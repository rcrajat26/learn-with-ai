### §2.7 Working with the tool: the practices that change outcomes

2.7.1 Plan mode as a first-class step: read-only exploration, a reviewable plan, then execute.
      `--permission-mode plan`, `EnterPlanMode`/`ExitPlanMode`, `plansDirectory`. `[DOC]`
2.7.2 Why a plan improves a large change more than a better prompt does: it moves the expensive
      correction from *after* the diff to *before* it. `[PROVE]`
2.7.3 Test-first with an agent: a failing test is a machine-checkable specification, which is
      exactly what a confabulating writer needs. `[JAVA]`
2.7.4 Small diffs and reviewability: why the same argument that makes small PRs better makes small
      agent tasks better. `[X-REF 17]`
2.7.5 Prompting that matters and prompting that does not: state the goal, the constraints, the
      done-condition, and where the answer goes. Skip politeness, role-play and threats. `[TRAP]`
2.7.6 Give the agent the same context a new teammate would need: the file, the convention, the
      command to verify. Under-specifying is the top cause of a plausible-but-wrong result.
2.7.7 The verification habit: never accept a claim of success without an artefact — a test run, a
      compile, a transcript, a diff.
2.7.8 `/code-review`, `/security-review` and self-review as a second pass with a fresh context;
      why a reviewer that shares the writer's context shares its blind spots. `[DOC]`
2.7.9 Where an agent is a bad fit: a one-line change you already understand, anything needing
      taste you cannot express, and anything whose verification costs more than the work.
2.7.10 `[JAVA]` A worked Java example end to end: add an idempotency key to a Spring Boot endpoint
       — plan, failing test, implementation, review, and the two places the agent got it wrong and
       how the test caught it. `[JAVA]` `[PROVE]`
2.7.11 `statusLine` / `subagentStatusLine`: cheap situational awareness — model, branch, cost,
       context used. `[DOC]` `[BUILD]`
2.7.12 Keybindings and `~/.claude/keybindings.json` in one paragraph. `[DOC]`



