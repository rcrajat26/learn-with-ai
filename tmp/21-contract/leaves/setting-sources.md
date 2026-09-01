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
3.7.6 The paper trail: `docs/adr/0016` and the AP-11470 incident, cited in the code itself.
      Decisions that carry their incident reference are the ones nobody re-litigates. `[CASE]`
3.7.7 Lesson one, generalised: **configuration discovered by directory walk breaks the moment you
      change directories.** Name three other systems where this bites. `[PROVE]`
3.7.8 Lesson two: **a permission model that silently degrades to defaults is worse than one that
      fails loudly.** What a loud failure would have looked like here. `[PROVE]`
3.7.9 Why this is the best interview story in the guide, and how to tell it in 90 seconds:
      symptom → mechanism → fix → generalisation. `[BUILD]`



