### §4.5 A headless orchestrator

4.5.1 `[JAVA]` A Java 21 `ClaudeRunner`: `ProcessBuilder` around `claude -p`, `--output-format
      json`, a record for the envelope, Jackson parsing, and the unparseable-input snippet
      preserved on failure. `[BUILD]` `[JAVA]`
4.5.2 `[JAVA]` Add the three ceilings: `--max-turns`, `--max-budget-usd`, and a
      `Process.waitFor(Duration)` wall clock, each with a distinct exception type. `[BUILD]`
      `[JAVA]`
4.5.3 `[JAVA]` Add `--settings <absolute path>` and explain, in a comment, the §3.7 incident it
      prevents. `[BUILD]` `[JAVA]`
4.5.4 `[JAVA]` Add parameter → env → default resolution for every knob, checked so an explicit
      zero survives. `[BUILD]` `[JAVA]`
