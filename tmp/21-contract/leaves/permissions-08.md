### §1.4 The permission system

1.4.39 Sandboxing as the layer below permissions: `sandbox.enabled`, filesystem allow/deny,
       network allowlist, credential masking. One paragraph each on why an OS-level boundary
       catches what a rule cannot. `[DOC]` `[RESEARCH]`
1.4.40 `[BUILD]` Write a permission block for a real repository: allow the build and test commands,
       deny `git push`, deny reads of `.env` and `secrets/**`, deny `rm -rf`. Then prove each rule
       fires. `[BUILD]` `[PROVE]`
1.4.41 `[CASE]` The harness's `permissions.allow` — `Read(**)`, `Edit(**)`, `Bash(*)`,
       `mcp__atlassian-cloud__*` — and the destructive-command deny-list it is paired with. Why
       `Bash(*)` plus a deny-list is a considered choice and not laziness. `[CASE]`



