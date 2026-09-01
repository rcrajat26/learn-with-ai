### §4.4 Two subagents

4.4.1 A read-only reviewer: `tools` allowlist, `model`, a fixed output contract, and a verdict
      line. `[BUILD]`
4.4.2 A test-runner for a Maven project: `Bash(mvn test *)` only, returns failing tests and
      nothing else. Measure the context saved versus running it inline. `[BUILD]` `[JAVA]`
      `[PROVE]`
4.4.3 Give one of them `memory: project` and show what it accumulates across two sessions.
      `[BUILD]` `[PROVE]`
4.4.4 Deny an agent to itself (`tools` without `Agent`) and prove it cannot spawn. `[BUILD]`
      `[PROVE]`
4.4.5 Diff vs the real one: `progress-verifier.md` and `calibrator.md` — pointer bodies, write
      boundaries, withheld tools, artefact-only evidence.



