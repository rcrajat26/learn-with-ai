### §1.2 Settings files, scope, and precedence

1.2.1 The four settings files and who each reaches: `~/.claude/settings.json` (user),
      `.claude/settings.json` (shared project, committed), `.claude/settings.local.json`
      (project local, gitignored), managed settings. `[DOC]`
1.2.2 The precedence order, highest first: **managed → command line (`--settings`) → project local
      → shared project → user.** A key set higher wins. `[DOC]` `[NUM]`
1.2.3 `[TRAP]` The order is *not* "more specific wins" and it is *not* "command line always wins":
      managed settings beat the command line. `[TRAP]` `[DOC]`
1.2.4 Installing Claude Code creates no settings file. Which files the tool creates for you, and
      when: user file on the first `/config` change it stores there, local file on the first
      "yes, and don't ask again". `[DOC]`
1.2.5 Where the local file lands in a git repo — repository root, not the directory you started
      in — and the exceptions (outside a repo, repo root is `$HOME`, Windows, foreign ownership).
      `[DOC]` `[VERSION]`
1.2.6 Worktrees: the local file comes from the main checkout's root. `[DOC]`
1.2.7 Committing `.claude/settings.json`: what your teammates get, and why permissions and hooks
      in it belong in code review. `[DOC]`
1.2.8 Which keys never take effect from a repository file, and which wait for workspace trust.
      Forward-reference §1.5.10. `[DOC]`
