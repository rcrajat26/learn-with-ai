### §2.8 Deterministic vs agentic — the central engineering judgment

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



