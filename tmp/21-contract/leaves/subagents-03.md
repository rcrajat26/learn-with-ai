### §2.1 Subagents

2.1.20 The three cases where it pays: verbose input with a small answer; genuinely parallel work
       with non-overlapping writes; a different capability set (read-only auditor, no-network
       reviewer). `[NUM]`
2.1.21 The output protocol that makes delegation actually save context: **agents write findings to
       files and return status + a few findings + a path.** Message bodies are not a data channel.
2.1.22 `[CASE]` `progress-verifier.md` — 20 lines, and four transferable design properties: body as
       a pointer to a versioned prompt file; a machine-parseable output contract
       (`## Progress Verdict: progressing|stalled`); explicit read boundaries; artifacts-only
       evidence discipline with an explicit ban on inspecting the coder's live session. `[CASE]`
2.1.23 `[CASE]` `calibrator.md` — enumerated write boundaries (two paths it may write, four it may
       not) and the line **"No Jira API tool is ever given to this agent."** Capability denied at
       the tool layer; the prose only documents it. `[CASE]`
2.1.24 `[TRAP]` Parallel agents must partition the **filesystem**, not the topic. Folder-scoped
       lanes plus one flat shared directory is not a partition. A same-slug collision overwrites
       silently and leaves no orphan to notice. **One writer per output path, ever.** `[TRAP]`
       `[INCIDENT]`
2.1.25 `[BUILD]` Write a `test-runner` agent for a Java repo: read-only plus `Bash(mvn test *)`,
       `model: haiku`, a fixed output contract, and a verdict line the caller can grep. `[BUILD]`
       `[JAVA]`



