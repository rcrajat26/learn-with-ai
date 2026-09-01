### §3.9 Orchestration patterns

3.9.9 The calibration loop: mine session transcripts for recurring friction, group it, and file it
      as work with human confirmation. Treating agent failures as a **measurable defect stream**,
      not anecdotes. `severity_map.yaml`, `feedback-signal.yaml`'s `failure_code` vocabulary, the
      `filed-bugs.yaml` dedup ledger. `[CASE]`
3.9.10 Evals: `harness/evals/seeded-defects` and `harness/evals/code-to-commit` — how you find out
       whether a change to a prompt made things better. `claude plugin eval`. `[CASE]` `[DOC]`
3.9.11 `[TRAP]` Over-orchestration. Symptoms: more agents than the task warrants, a pipeline whose
       coordination costs more than its work, and a fan-out where the join is the bottleneck.
       `[TRAP]`
3.9.12 `[NUM]` Concurrency limits that are real, not stylistic: 20 concurrent subagents, depth 3,
       and the practical ceiling imposed by review capacity. `[NUM]`



