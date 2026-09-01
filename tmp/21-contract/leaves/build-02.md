### §4.2 Three hooks

4.2.1 `PostToolUse` on `Edit|Write`: run the formatter on the changed file only, using `jq` over
      stdin to get `tool_input.file_path`. `[BUILD]`
4.2.2 `PreToolUse` on `Bash`: block a destructive command with a JSON `permissionDecision: "deny"`
      and a reason the model can act on; then the exit-2 variant, and a comparison. `[BUILD]`
      `[PROVE]`
4.2.3 `SessionStart`: inject branch, dirty-file count and failing-test count as tagged advisory
      lines. `set +e`, `exit 0`, a timeout on anything network-bound. `[BUILD]`
4.2.4 `Stop`: refuse to end the turn while the build is red, using `continue`. Then explain why
      this is dangerous if the build takes four minutes. `[BUILD]` `[TRAP]`
4.2.5 Prove all four fired: `/hooks`, the debug log, and an intentional violation each. `[BUILD]`
      `[PROVE]`
4.2.6 Diff vs the real one: `check-init.sh`, `doc-update-reminder.sh`, `prod-guard-bash.sh` —
      concurrency safety, path resolution, tool fallbacks, locale pinning, failure posture.



