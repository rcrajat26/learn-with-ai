### §1.4 The permission system

1.4.35 `.claude/settings.local.json` and trust: your own untracked file applies immediately; a
       *tracked* local file, or a symlinked `.claude`, is treated as repository-supplied and waits.
       `[DOC]`
1.4.36 Precedence for permissions: **a deny at any level cannot be overridden by any other level**,
       including `--allowedTools` and managed settings. `[DOC]`
1.4.37 `/permissions` — read the rules and the file each came from; edits apply from Claude's next
       tool call in the same turn. `[DOC]` `[VERSION]` `[BUILD]`
1.4.38 `--allowedTools` / `--disallowedTools` / `--tools` as per-run overrides. `[DOC]`
