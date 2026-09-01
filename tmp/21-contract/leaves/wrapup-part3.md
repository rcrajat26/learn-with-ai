### §3.1 What is actually in the request

3.1.1 The assembled request, in order: system prompt (built-in + appended), tool schemas, memory
      files as a user message, environment/git snapshot, skill listing, then the conversation.
      `[DOC]` `[PROVE]`
3.1.2 `[TRAP]` `CLAUDE.md` is delivered **as a user message after the system prompt**, not as part
      of the system prompt. That is why it is guidance and not policy, and why
      `--append-system-prompt` behaves differently. `[TRAP]` `[DOC]`
3.1.3 The cached prefix and why the ordering above is not arbitrary: everything stable goes first
      so it can be reused. `--exclude-dynamic-system-prompt-sections` exists to protect this.
      `[NUM]` `[DOC]`
3.1.4 Tool schemas as a cost line: how many tokens the default set is, what an MCP server adds,
      and what deferred tools plus `ToolSearch` save. `[NUM]` `[PROVE]`
### §3.1 What is actually in the request

3.1.5 The skill listing: `description` + `when_to_use` per skill, capped at 1,536 characters each,
      inside a budget fraction of the window. Compute the cost of 50 skills. `[NUM]` `[PROVE]`
3.1.6 System-reminder blocks: how the harness injects mid-conversation state (file-state notes,
      recalled memories, hook output) and why that text is context rather than instruction.
3.1.7 Reading a real transcript: the JSONL under `~/.claude/projects/<project>/<session>/`, its
      message shapes, and how to count tokens per turn from it. `[BUILD]` `[PROVE]`
3.1.8 `[CASE]` The harness's `telemetry/transcript.py` reads exactly these transcripts to mine
      friction signals. Provenance for the whole calibration loop. `[CASE]`



### §3.2 Compaction, mechanically

3.2.1 What compaction does: summarise the transcript, then continue with the summary in place of
      the messages. `[DOC]`
3.2.2 The threshold and how it is configured; what "75%" means against which number. `[NUM]`
3.2.3 The re-attachment algorithm for skills: most recent invocation of each, first 5,000 tokens
      each, 25,000 combined, filled newest-first — so invoking many skills silently evicts the
      earliest. `[DOC]` `[NUM]` `[PROVE]`
3.2.4 `CLAUDE.md` re-read from disk after compaction; nested files and path-scoped rules reload
      only on re-match. `[DOC]`
### §3.2 Compaction, mechanically

3.2.5 What is irrecoverably lost, and the fix: put it in a file, not in a message. `[TRAP]`
3.2.6 `PreCompact`/`PostCompact` as the persistence seam; a worked handoff-note hook. `[BUILD]`
3.2.7 Why a fresh session usually beats a thrice-compacted one, argued rather than asserted.
      `[PROVE]`



### §3.3 Permission evaluation, step by step

3.3.1 The full pipeline for one tool call: managed → CLI → local → project → user rule collection,
      then deny → ask → allow, then `PreToolUse` hooks, then the mode's default, then the prompt.
      Draw it. `[DOC]` `[PROVE]`
3.3.2 Where a `PreToolUse` hook sits relative to the rules, and why a hook cannot unblock a deny.
      `[DOC]`
3.3.3 Bash matching in detail: separator splitting, wrapper stripping, env-assignment stripping,
      then per-subcommand matching. Trace three commands through it. `[PROVE]`
3.3.4 The read-only command fast path, and the two cases that leave it (write-capable flags with
      unquoted globs, redirects). `[DOC]`
### §3.3 Permission evaluation, step by step

3.3.5 Read/Edit gitignore-pattern matching, including single-segment directory patterns whose
      depth depends on the rule type. `[DOC]` `[PROVE]`
3.3.6 Which tools consult path rules at all, and the startup warnings for the ones that do not.
      `[DOC]`
3.3.7 Where enforcement ends and the OS begins: a subprocess that opens a file itself, and the
      sandbox as the only answer. `[DOC]` `[TRAP]`
3.3.8 `[PROVE]` Adversarial exercise: given a settings file, decide for ten commands whether each
      runs, prompts or is blocked — then verify each against the real tool. `[PROVE]` `[BUILD]`



### §3.4 The cost model

3.4.1 What you are billed for: input tokens, output tokens, cache writes, cache reads. Four
      different prices. `[NUM]` `[RESEARCH]`
3.4.2 Per-model pricing and the ratio between tiers, as of the write date. `[NUM]` `[RESEARCH]`
3.4.3 Why conversation length dominates: the same prefix re-sent every turn, times turns. Work a
      full session's arithmetic. `[PROVE]` `[NUM]`
3.4.4 What caching changes, and the 5-minute default TTL as the reason a paused session costs
      more when resumed. `[NUM]`
### §3.4 The cost model

3.4.5 Where a subagent's ~2× comes from, itemised. `[PROVE]` `[NUM]`
3.4.6 The three ceilings and their different failure shapes: `--max-turns` (agency),
      `--max-budget-usd` (money), subprocess timeout (wall clock). `[NUM]`
3.4.7 Reading cost out of a run: the `-p --output-format json` envelope's cost and token fields;
      `/cost`; `modelPricing` for contracted rates. `[DOC]` `[BUILD]`
3.4.8 `[PROVE]` Measure it: run one task inline and the same task via a subagent, and report both
      envelopes. `[PROVE]` `[BUILD]`
3.4.9 The judgment this all supports: an unbounded agent loop is an unbounded invoice, so ceilings
      are reliability engineering, not thrift. `[CASE]`



### §3.5 Effort, models and routing

3.5.1 Effort levels `low|medium|high|xhigh|max`: what they change, `/effort`, `effortLevel`,
      `--effort`, `CLAUDE_EFFORT`, `${CLAUDE_EFFORT}`. `[DOC]`
3.5.2 Per-skill and per-agent `effort` and `model` overrides, and their lifetime (the turn, not the
      session). `[DOC]`
3.5.3 Routing as a cost decision, with a table: exploration/search → haiku; implementation →
      sonnet; architecture and gnarly debugging → opus. State the escalation path. `[NUM]`
3.5.4 `fallbackModel`, `--fallback-model`, `switchModelsOnFlag`, `advisorModel`, `modelOverrides`
      for Bedrock/Vertex ARNs, `modelPicker`. `[DOC]`
3.5.5 `fastMode` / `/fast` — faster output on the same Opus model, not a downgrade. `[DOC]`
      `[TRAP]`
3.5.6 `[TRAP]` Routing everything to the cheapest model. Where haiku fails, with a concrete
      example of a wrong result that cost more than the saving. `[TRAP]` `[PROVE]`



### §3.6 Headless mode — the programmable surface

3.6.1 `claude -p "<task>"` — one prompt in, one envelope out. The whole basis of automation.
      `[DOC]`
3.6.2 `--output-format text|json|stream-json` and `--input-format text|stream-json`. What each is
      for. `[DOC]`
3.6.3 The JSON envelope's fields: result text, `is_error`, `session_id`, cost, token counts,
      duration. Show a real one. `[DOC]` `[PROVE]`
3.6.4 `stream-json` and `--include-partial-messages`, `--include-hook-events`,
      `--forward-subagent-text`, `--replay-user-messages`. When streaming is worth the complexity.
      `[DOC]`
3.6.5 `--json-schema` for schema-validated output — the difference between parsing prose and
      receiving data. `[DOC]` `[VERSION]`
### §3.6 Headless mode — the programmable surface

3.6.6 The flag set a production wrapper needs, as a checklist: `--agent`, `--output-format`,
      `--max-turns`, `--permission-mode`, `--setting-sources`, `--settings`, `--model`, `--effort`,
      `--add-dir`, `--append-system-prompt`, `--resume`, `--max-budget-usd`, `--session-id`,
      `--no-session-persistence`, `--allowed-tools`, `--disallowed-tools`, `--mcp-config`,
      `--verbose`. `[DOC]`
3.6.7 Session control in automation: `--session-id` (must be a UUID), `--fork-session`,
      `--continue`, `--resume`, `--no-session-persistence`. `[DOC]`
3.6.8 `claude setup-token` for CI; what an unattended run must *not* have. `[DOC]`
3.6.9 Background and remote execution: `--bg`, `claude attach|logs|stop|respawn|rm`,
      `claude daemon status`, `--cloud`, `--environment`, `--teleport`. One paragraph each.
      `[DOC]`
### §3.6 Headless mode — the programmable surface

3.6.10 Failure taxonomy for a wrapper, three classes handled differently: launch/timeout
       (infrastructure), unparseable envelope (contract), `is_error: true` (the agent failed).
       `[CASE]`
3.6.11 `[CASE]` `extract_json_envelope()` preserves a **500-character snippet** of what the
       subprocess actually printed when parsing fails — because a zero-cost envelope failure was
       previously "only diagnosable by reproducing it interactively (2026-07-30 calibration
       finding)". General law: **when you parse a subprocess's output, capture the unparseable
       input.** `[CASE]` `[NUM]` `[INCIDENT]`
3.6.12 `[CASE]` The retry loop keeps the **last parsed error envelope** so cost and token counts
       survive a failure. Why discarding them makes the run unbillable and unauditable. `[CASE]`
3.6.13 `[CASE]` The harness's resolution order for every knob — explicit parameter → environment
       variable → module default — checked with `is not None` so an explicit `0` is not silently
       treated as omitted. Copy this pattern. `[CASE]` `[JAVA]`
3.6.14 `[CASE]` `DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`,
       `DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160`. Each number with its reason. `[CASE]`
       `[NUM]`
### §3.6 Headless mode — the programmable surface

3.6.15 `[INCIDENT]` Why `DEFAULT_MAX_TURNS` is 160 and not 40. Raised 40 → 80 → 160; the 2026-08-10
       dogfood run produced **13 green tests and a correct fix but exhausted 80 turns before
       reaching a commit — $5.16 for zero landed work.** A fresh story's first leg is
       disproportionately reads and exploration, not a runaway. The comment records it as "an
       explicit engineer call to trade cost for dev experience, not a measured-data derivation" —
       an honest constant. `[INCIDENT]` `[CASE]` `[NUM]`
3.6.16 `[CASE]` Both ceilings overridable by environment (`HARNESS_AGENT_MAX_TURNS`,
       `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`,
       `HARNESS_AGENT_SETTINGS`) so tuning never requires a code change. `[CASE]`
3.6.17 `[CASE]` `--resume <session_id>` as the continuation mechanism, and the rule that the coder
       resumes its own leg while the verifier **never** does — it judges artifacts. Why mixing the
       two destroys the verdict's reproducibility. `[CASE]`
3.6.18 `[CASE]` `--add-dir` deliberately unused in the code-to-commit loop: agents write only
       inside the worktree and reports ride the envelope. A seam kept open, not used by default.
       `[CASE]`



### §3.7 The `--setting-sources` incident — a full root-cause walkthrough

3.7.1 The setup: the harness runs each coder in an **isolated per-story git worktree**, so `cwd` is
      the worktree, not the harness repo. `[CASE]` `[INCIDENT]`
3.7.2 The mechanism: `--setting-sources project` resolves `<cwd>/.claude/settings.json`. `[DOC]`
3.7.3 The consequence: the harness's own `permissions.allow` (`Bash(*)`) **and** its
      destructive-command deny-list never loaded. `[CASE]`
3.7.4 The observed symptom, precisely: the agent could read, edit, `mkdir`, `touch`, `mv`, `cp`,
      `sed` — the bare `acceptEdits` defaults — but **not** `mvn`, `git commit`, `chmod` or
      `java`. A competent agent mysteriously unable to build. `[CASE]` `[NUM]`
3.7.5 The fix: `--settings <absolute path>`, which is evaluated independently of `cwd`. `[CASE]`
### §3.7 The `--setting-sources` incident — a full root-cause walkthrough

3.7.6 The paper trail: `docs/adr/0016` and the AP-11470 incident, cited in the code itself.
      Decisions that carry their incident reference are the ones nobody re-litigates. `[CASE]`
3.7.7 Lesson one, generalised: **configuration discovered by directory walk breaks the moment you
      change directories.** Name three other systems where this bites. `[PROVE]`
3.7.8 Lesson two: **a permission model that silently degrades to defaults is worse than one that
      fails loudly.** What a loud failure would have looked like here. `[PROVE]`
3.7.9 Why this is the best interview story in the guide, and how to tell it in 90 seconds:
      symptom → mechanism → fix → generalisation. `[BUILD]`



### §3.8 The Agent SDK and the API underneath

3.8.1 The three levels of building on Claude: the CLI in `-p` mode, the Agent SDK
      (TypeScript/Python), and the raw Messages API with your own loop. What each gives up. `[DOC]`
3.8.2 The Messages API shape: `model`, `system`, `messages[]`, `tools[]`, `max_tokens`, streaming.
      Enough to read one. `[DOC]` `[RESEARCH]`
3.8.3 Tool use at the API level: `tool_use` and `tool_result` blocks, and writing the loop
      yourself. `[DOC]`
3.8.4 Prompt caching at the API level: cache breakpoints and what they cost. `[DOC]` `[NUM]`
### §3.8 The Agent SDK and the API underneath

3.8.5 Agent SDK specifics worth knowing: `resolveSettings()`, `managedSettings`,
      `parentSettingsBehavior`, and that an SDK session counts as trusted. `[DOC]`
3.8.6 Why the harness chose subprocesses over the SDK, and what that trade buys (process
      isolation, the same binary engineers use interactively, no SDK version coupling). `[CASE]`
3.8.7 `[JAVA]` The Java view: there is no first-party Java SDK, so the two honest options are the
      HTTP API via a JDK 21 `HttpClient`, or `ProcessBuilder` around the CLI. Sketch both. `[JAVA]`
3.8.8 `[X-REF 12]` Treating an agent call as a remote dependency: timeouts, retries with backoff,
      idempotency, a circuit breaker, and a bulkhead on concurrency. The reader already knows this
      material; the point is that it applies unchanged. `[X-REF 12]` `[JAVA]`



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



### §3.10 Verification — the AI-specific failure mode

3.10.1 The core asymmetry: an agent produces **plausible** artefacts, and skimming a diff is the
       review method worst matched to plausibility. `[ZERO]`
3.10.2 Law: **re-run every published artefact in its published form.** In this repository that
       found more defects than every structural check combined — code that no longer produced the
       transcript printed beneath it, invented values that compiled fine, a repro returning the
       opposite of its claim, and run-specific numbers published as constants. `[INCIDENT]`
       `[PROVE]`
3.10.3 Law: **a checker whose input can switch it off is worse than no checker.** The NUL-byte
       incident — one generated file contained a literal NUL, `file` classified it as `data`, grep
       returned *nothing* (not a mismatch), every text check silently skipped it and reported
       success. Assert text-ness before any grep-based gate. `[INCIDENT]` `[PROVE]`
3.10.4 Law: **certify from final state, never from a pre-write computation.** A footer regex ending
       `\s*$` ate nine files' trailing newlines; an md5 was taken over a patched harness while the
       shipped files still failed to compile. `[INCIDENT]`
### §3.10 Verification — the AI-specific failure mode

3.10.5 Law: **a build proof must pin its harness beside the digest.** Two honest runs over
       identical files produced different md5s purely because one wrapped a throwing snippet. A
       bare digest is unfalsifiable. `[INCIDENT]`
3.10.6 Law: **never let a status row point at a missing path.** The costliest bookkeeping failure
       here, and the one-line gate that prevents it. `[INCIDENT]`
3.10.7 Law: **a closed lane is not a verified lane.** Two cross-lane contradictions were found
       after their owners had stood down; only a pass that reads across boundaries finds these.
       `[INCIDENT]`
3.10.8 Executable evidence over structural evidence: a compile, a test, a transcript beats a regex
       over a file. Rank the evidence types. `[NUM]`
### §3.10 Verification — the AI-specific failure mode

3.10.9 Automating the gates: `PostToolUse` formatters and linters, a `Stop` hook that refuses to
       finish on a red build, and CI as the outer loop. `[BUILD]`
3.10.10 `[TRAP]` Command shapes that defeat a permission matcher and therefore your own gates:
        heredocs, `&&`/`;` chains, `$(...)`. Use one command per call, absolute paths, and the
        Write tool for scratch files. `[TRAP]` `[CASE]`
3.10.11 Review capacity as the real ceiling on agent throughput, argued with numbers. `[PROVE]`
        `[NUM]`








