### §4.1 A `.claude` folder from nothing

4.1.1 A `CLAUDE.md` under 100 lines for a real Spring Boot service: build command, test command,
      layout, three conventions, two things Claude gets wrong here. `[BUILD]` `[JAVA]`
4.1.2 Split it: move the always-true facts to `CLAUDE.md`, one procedure to a skill, and one
      file-type convention to a `paths`-scoped rule in `.claude/rules/`. Measure `/context`
      before and after. `[BUILD]` `[PROVE]`
4.1.3 A `settings.json`: permissions for the real build/test commands, deny for `git push`, `.env`
      and `secrets/**`, `env` for one variable, `model` and `effortLevel`. `[BUILD]`
### §4.1 A `.claude` folder from nothing

4.1.4 A `settings.local.json` that overrides exactly one key, and proof that it wins. `[BUILD]`
      `[PROVE]`
4.1.5 Commit it, then verify a fresh clone behaves identically — including the workspace-trust
      step. `[BUILD]` `[PROVE]`



### §4.2 Three hooks

4.2.1 `PostToolUse` on `Edit|Write`: run the formatter on the changed file only, using `jq` over
      stdin to get `tool_input.file_path`. `[BUILD]`
4.2.2 `PreToolUse` on `Bash`: block a destructive command with a JSON `permissionDecision: "deny"`
      and a reason the model can act on; then the exit-2 variant, and a comparison. `[BUILD]`
      `[PROVE]`
4.2.3 `SessionStart`: inject branch, dirty-file count and failing-test count as tagged advisory
      lines. `set +e`, `exit 0`, a timeout on anything network-bound. `[BUILD]`
### §4.2 Three hooks

4.2.4 `Stop`: refuse to end the turn while the build is red, using `continue`. Then explain why
      this is dangerous if the build takes four minutes. `[BUILD]` `[TRAP]`
4.2.5 Prove all four fired: `/hooks`, the debug log, and an intentional violation each. `[BUILD]`
      `[PROVE]`
4.2.6 Diff vs the real one: `check-init.sh`, `doc-update-reminder.sh`, `prod-guard-bash.sh` —
      concurrency safety, path resolution, tool fallbacks, locale pinning, failure posture.



### §4.3 A skill and a command

4.3.1 A skill with frontmatter, `$ARGUMENTS`, one `` !`command` `` injection and a `references/`
      file that loads only on demand. `[BUILD]`
4.3.2 The same capability as a bare `.claude/commands/*.md` file; then state what the skill form
      bought. `[BUILD]`
4.3.3 A `disable-model-invocation: true` workflow skill, and a `user-invocable: false` knowledge
      skill. Show that each is invocable only the intended way. `[BUILD]` `[PROVE]`
### §4.3 A skill and a command

4.3.4 A `paths`-gated skill that activates only for `**/*.java`. `[BUILD]` `[JAVA]` `[PROVE]`
4.3.5 A composed pair: a thin wrapper skill that inlines a shared executor with a ` ```! ` block
      and states only its overrides. `[BUILD]`
4.3.6 Diff vs the real one: `bootstrap/SKILL.md` and `/implement-story` — plan-then-confirm,
      delegation to tested scripts, rejected-flag handling.



### §4.4 Two subagents

4.4.1 A read-only reviewer: `tools` allowlist, `model`, a fixed output contract, and a verdict
      line. `[BUILD]`
4.4.2 A test-runner for a Maven project: `Bash(mvn test *)` only, returns failing tests and
      nothing else. Measure the context saved versus running it inline. `[BUILD]` `[JAVA]`
      `[PROVE]`
4.4.3 Give one of them `memory: project` and show what it accumulates across two sessions.
      `[BUILD]` `[PROVE]`
### §4.4 Two subagents

4.4.4 Deny an agent to itself (`tools` without `Agent`) and prove it cannot spawn. `[BUILD]`
      `[PROVE]`
4.4.5 Diff vs the real one: `progress-verifier.md` and `calibrator.md` — pointer bodies, write
      boundaries, withheld tools, artefact-only evidence.



### §4.5 A headless orchestrator

4.5.1 `[JAVA]` A Java 21 `ClaudeRunner`: `ProcessBuilder` around `claude -p`, `--output-format
      json`, a record for the envelope, Jackson parsing, and the unparseable-input snippet
      preserved on failure. `[BUILD]` `[JAVA]`
4.5.2 `[JAVA]` Add the three ceilings: `--max-turns`, `--max-budget-usd`, and a
      `Process.waitFor(Duration)` wall clock, each with a distinct exception type. `[BUILD]`
      `[JAVA]`
### §4.5 A headless orchestrator

4.5.3 `[JAVA]` Add `--settings <absolute path>` and explain, in a comment, the §3.7 incident it
      prevents. `[BUILD]` `[JAVA]`
4.5.4 `[JAVA]` Add parameter → env → default resolution for every knob, checked so an explicit
      zero survives. `[BUILD]` `[JAVA]`
### §4.5 A headless orchestrator

4.5.5 `[JAVA]` Add a bounded retry that keeps the last parsed error envelope, and a bulkhead on
      concurrency. `[BUILD]` `[JAVA]` `[X-REF 05]`
4.5.6 A two-stage pipeline over it: stage 1 writes a file, stage 2 reads it, neither writes to its
      own input. Prove stage 2 is independently re-runnable. `[BUILD]` `[PROVE]`
### §4.5 A headless orchestrator

4.5.7 Emit a cost and token report per stage from the envelopes. `[BUILD]`
4.5.8 Diff vs the real one: `engine/agent.py` — persona loading with frontmatter stripping,
      envelope extraction, the retry loop, the resolution order, `--resume` continuation legs, and
      every default constant with its recorded reason.



### §4.6 A plugin

4.6.1 Package §4.2–§4.4 as a plugin: `.claude-plugin/plugin.json`, `skills/`, `agents/`,
      `hooks/hooks.json`. Test with `--plugin-dir`. `[BUILD]`
4.6.2 `claude plugin validate`, then `--strict`. Fix what it reports. `[BUILD]` `[PROVE]`
4.6.3 Publish it to a local marketplace: `.claude-plugin/marketplace.json`, `/plugin marketplace
      add`, `/plugin install`, `/reload-plugins`. `[BUILD]`
### §4.6 A plugin

4.6.4 Bump `version` and prove an installed copy updates. `[BUILD]` `[PROVE]`
4.6.5 Add a `dependencies` entry on a second local plugin, and demonstrate both the unresolved
      state and the `claude plugin list --json` `errors` array that reveals it. `[BUILD]` `[PROVE]`
4.6.6 Diff vs the real one: the sdlc-harness plugin and marketplace — cross-marketplace
      dependency trust, `${CLAUDE_PLUGIN_ROOT}` path discipline, content-hash version nudging, and
      a bootstrap skill that provisions what a plugin cannot install declaratively.



### §4.7 Verification harness

4.7.1 A `verify.sh` for this repository's own notes: text-ness assertion first, then every
      structural check, then re-run every fenced listing. `[BUILD]`
4.7.2 Make one check fail deliberately and confirm it fails loudly rather than skipping. `[BUILD]`
      `[PROVE]`
### §4.7 Verification harness

4.7.3 Wire it as a `Stop` hook and as a CI job, and state which failures belong in which. `[BUILD]`
4.7.4 A skill eval: three prompts that should trigger a skill and three that should not; run and
      score them. `[BUILD]` `[PROVE]`







