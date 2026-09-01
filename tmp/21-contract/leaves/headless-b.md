### §3.6 Headless mode — the programmable surface

3.6.10 Failure taxonomy for a wrapper, three classes handled differently: launch/timeout
       (infrastructure), unparseable envelope (contract), `is_error: true` (the agent failed).
       `[CASE]`
3.6.11 `[CASE]` `extract_json_envelope()` preserves a **500-character snippet** of what the
       subprocess actually printed when parsing fails — because a zero-cost envelope failure was
       previously "only diagnosable by reproducing it interactively (2026-07-30 calibration
       finding)". General law: **when you parse a subprocess's output, capture the unparseable
       input.** `[CASE]` `[NUM]` `[INCIDENT]`
3.6.12 `[CASE]` The retry loop keeps the **last parsed error envelope** so cost and token counts
       survive a failure. Why discarding them makes the run unbillable and unauditable. `[CASE]`
3.6.13 `[CASE]` The harness's resolution order for every knob — explicit parameter → environment
       variable → module default — checked with `is not None` so an explicit `0` is not silently
       treated as omitted. Copy this pattern. `[CASE]` `[JAVA]`
3.6.14 `[CASE]` `DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`,
       `DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160`. Each number with its reason. `[CASE]`
       `[NUM]`
3.6.15 `[INCIDENT]` Why `DEFAULT_MAX_TURNS` is 160 and not 40. Raised 40 → 80 → 160; the 2026-08-10
       dogfood run produced **13 green tests and a correct fix but exhausted 80 turns before
       reaching a commit — $5.16 for zero landed work.** A fresh story's first leg is
       disproportionately reads and exploration, not a runaway. The comment records it as "an
       explicit engineer call to trade cost for dev experience, not a measured-data derivation" —
       an honest constant. `[INCIDENT]` `[CASE]` `[NUM]`
3.6.16 `[CASE]` Both ceilings overridable by environment (`HARNESS_AGENT_MAX_TURNS`,
       `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`,
       `HARNESS_AGENT_SETTINGS`) so tuning never requires a code change. `[CASE]`
3.6.17 `[CASE]` `--resume <session_id>` as the continuation mechanism, and the rule that the coder
       resumes its own leg while the verifier **never** does — it judges artifacts. Why mixing the
       two destroys the verdict's reproducibility. `[CASE]`
3.6.18 `[CASE]` `--add-dir` deliberately unused in the code-to-commit loop: agents write only
       inside the worktree and reports ride the envelope. A seam kept open, not used by default.
       `[CASE]`



