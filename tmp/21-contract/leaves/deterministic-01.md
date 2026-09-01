### §2.8 Deterministic vs agentic — the central engineering judgment

2.8.1 The rule, stated once and referenced forever: **if the inputs determine one correct answer,
      write a script; if the task needs judgment, write a prompt.** `[CASE]`
2.8.2 `[CASE]` The source of that rule in the harness's `bootstrap` skill, quoted verbatim:
      "resolving paths, merging JSON, and creating symlinks all have a single correct answer given
      the inputs — there is no ambiguity for a model to resolve." `[CASE]`
2.8.3 `[CASE]` The consequence in the same file: the skill is "an **orchestrator, not a rewrite**",
      every step delegates to a tested `bootstrap-*.sh`, and the assistant is explicitly forbidden
      from re-deriving the logic inline on each run. `[CASE]`
2.8.4 The decision table: one-correct-answer → script; judgment/synthesis → prompt; must-happen →
      hook; verbose-in/small-out → subagent; needs human authority → confirmation gate with the
      tool denied. `[NUM]`
2.8.5 Why "the model could do it" is not an argument for letting it: cost, variance, and the fact
      that a script is testable and a prompt is not. `[PROVE]`
2.8.6 Idempotence as the property that makes a bootstrap safe to re-run, and why every step in the
      harness's is written that way. `[CASE]`
2.8.7 `[CASE]` The one documented exception and its reasoning: `bootstrap-uv.sh` self-installs a
      package manager because without `uv` no playbook can pass its first stage, so "a bootstrap
      that leaves the engineer to separately find and run a curl-to-shell command isn't actually a
      single-command setup". An exception stated with its justification is not an inconsistency.
      `[CASE]`
2.8.8 Human-authority gates: the calibrator mines and groups, and a human confirms and files.
      Deny the tool; do not instruct the agent to abstain. `[CASE]`
2.8.9 `[TRAP]` Prompting for determinism. Symptoms: a step that works four times in five, and a
      failure mode nobody can reproduce. `[TRAP]`



