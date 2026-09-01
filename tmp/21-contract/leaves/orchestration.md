### §3.9 Orchestration patterns

3.9.1 The vocabulary, defined: single session, subagent, fan-out, pipeline, team, workflow. `[ZERO]`
3.9.2 Fan-out with a join: N independent tasks, one aggregation, and the file-boundary requirement
      that makes it safe. `[NUM]`
3.9.3 Pipeline: stage N's output is stage N+1's input, each stage independently re-runnable
      **because no stage writes to its own input.** `[CASE]`
3.9.4 `[CASE]` This repository's own per-topic pipeline as the worked example:
      `topic-enhancer-agent` → `prompt-builder` → `notes-generator` → `gaps-analyzer-agent` →
      `understanding-book-keeper`, with the rule "never write across lanes" and a hard stop when a
      prerequisite is missing. `[CASE]`
3.9.5 `[CASE]` The harness's playbooks (`full-sdlc`, `plan-project`, `implement-story`,
      `implement-story-lite`, `post-deploy-smoke`) and the split between a **prose executor**
      (`/run-harness`) and a **deterministic conductor** (`/run-conductor`) — two executors, not
      interchangeable, with the routing decision returned by `conductor advance` from folded run
      state rather than inferred by a model. `[CASE]`
3.9.6 `[CASE]` Folded state in `features/<slug>/state/harness.db` as the source of truth for
      "which stage are we at", and why a `--resume-at <stage>` flag was **rejected** rather than
      approximated. Rejecting a flag with a stated reason beats silently ignoring it. `[CASE]`
3.9.7 Judges and rubrics: `progress-verifier` scoring against
      `control-plane/judge-rubrics/progress-verifier.yaml` and emitting one verdict line. Why the
      rubric is a versioned file. `[CASE]`
3.9.8 Continuation checkpoints: what to do when an agent exhausts its turns mid-task, and the
      progressing-vs-stalled decision. `[CASE]`
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



