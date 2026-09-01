### §4.5 A headless orchestrator

4.5.5 `[JAVA]` Add a bounded retry that keeps the last parsed error envelope, and a bulkhead on
      concurrency. `[BUILD]` `[JAVA]` `[X-REF 05]`
4.5.6 A two-stage pipeline over it: stage 1 writes a file, stage 2 reads it, neither writes to its
      own input. Prove stage 2 is independently re-runnable. `[BUILD]` `[PROVE]`
4.5.7 Emit a cost and token report per stage from the envelopes. `[BUILD]`
4.5.8 Diff vs the real one: `engine/agent.py` — persona loading with frontmatter stripping,
      envelope extraction, the retry loop, the resolution order, `--resume` continuation legs, and
      every default constant with its recorded reason.



