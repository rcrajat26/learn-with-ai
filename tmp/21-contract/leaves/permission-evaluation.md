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
3.3.5 Read/Edit gitignore-pattern matching, including single-segment directory patterns whose
      depth depends on the rule type. `[DOC]` `[PROVE]`
3.3.6 Which tools consult path rules at all, and the startup warnings for the ones that do not.
      `[DOC]`
3.3.7 Where enforcement ends and the OS begins: a subprocess that opens a file itself, and the
      sandbox as the only answer. `[DOC]` `[TRAP]`
3.3.8 `[PROVE]` Adversarial exercise: given a settings file, decide for ten commands whether each
      runs, prompts or is blocked — then verify each against the real tool. `[PROVE]` `[BUILD]`



