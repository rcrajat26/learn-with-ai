### §1.4 The permission system

1.4.25 The six permission modes and exactly what each auto-approves: `default`/`manual`,
       `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. `[DOC]` `[NUM]`
1.4.26 `acceptEdits` in detail — file edits **plus** common filesystem commands (`mkdir`, `touch`,
       `mv`, `cp`) for paths in the working directory or `additionalDirectories`. What it does
       *not* cover is the point of the §3.7 incident. `[DOC]`
1.4.27 `auto` mode: a background classifier reviews actions instead of you; `autoMode` rules,
       `autoMode.classifyAllShell`, `disableAutoMode`. `[DOC]` `[VERSION]`
1.4.28 `bypassPermissions`: what it still refuses (protected paths such as `.git` and `.claude`,
       cross-session messaging safeguards), and that it is defensible only in a container or VM.
       `[DOC]` `[TRAP]`
1.4.29 `permissions.defaultMode`, `disableBypassPermissionsMode`, `disableAutoMode` — and why these
       belong in managed settings. `[DOC]`
