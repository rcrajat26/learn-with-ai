### §2.3 Hooks

2.3.18 Where hooks may be configured: user/project/local settings, managed policy, plugin
       `hooks/hooks.json`, **skill frontmatter** (rest of session), **subagent frontmatter**
       (while it runs). Six sources. `[DOC]`
2.3.19 `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and
       that individual hooks cannot be disabled — only deleted. `[DOC]`
2.3.20 `/hooks` as the read-only browser: events, counts, matcher groups, handler details and
       source file. The debug log records which hooks matched and how they exited. `[DOC]`
       `[BUILD]`
