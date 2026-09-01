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
