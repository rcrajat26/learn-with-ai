### §3.9 Orchestration patterns

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
