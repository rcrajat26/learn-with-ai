### §3.8 The Agent SDK and the API underneath

3.8.5 Agent SDK specifics worth knowing: `resolveSettings()`, `managedSettings`,
      `parentSettingsBehavior`, and that an SDK session counts as trusted. `[DOC]`
3.8.6 Why the harness chose subprocesses over the SDK, and what that trade buys (process
      isolation, the same binary engineers use interactively, no SDK version coupling). `[CASE]`
3.8.7 `[JAVA]` The Java view: there is no first-party Java SDK, so the two honest options are the
      HTTP API via a JDK 21 `HttpClient`, or `ProcessBuilder` around the CLI. Sketch both. `[JAVA]`
3.8.8 `[X-REF 12]` Treating an agent call as a remote dependency: timeouts, retries with backoff,
      idempotency, a circuit breaker, and a bulkhead on concurrency. The reader already knows this
      material; the point is that it applies unchanged. `[X-REF 12]` `[JAVA]`



