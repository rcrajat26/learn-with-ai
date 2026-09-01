### §1.4 The permission system

1.4.30 **Working directories**: the primary working directory, `--add-dir`, `/add-dir`,
       `permissions.additionalDirectories`. Additional directories grant **file access, not
       configuration**. `[DOC]` `[TRAP]`
1.4.31 `/cd` moves the primary working directory and re-applies the new directory's project
       settings, hooks, MCP servers, plugins, skills, subagents and `env`. `[DOC]` `[VERSION]`
1.4.32 **Workspace trust**: `permissions.allow` and `additionalDirectories` from a project's
       committed settings apply only after you accept the trust dialog; `deny`/`ask` are not
       gated because they only restrict. `[DOC]`
1.4.33 How trust is keyed: on the git repo root inside a repo (excluding nested repos), on the
       start directory outside one, session-only in `$HOME`. `[DOC]`
1.4.34 `[TRAP]` **A `-p` or SDK session never shows the trust dialog and counts as accepted.**
       Automation therefore runs a repository's allow rules without a human ever reviewing them.
       `[TRAP]` `[DOC]`
