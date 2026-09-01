### §2.9 Governance, security and the org view

2.9.1 The threat model in plain terms: the agent runs with your credentials, reads what you can
      read, and follows text it finds. Enumerate what that permits. `[ZERO]` `[X-REF 13]`
2.9.2 **Prompt injection**: instructions embedded in a file, a web page, an issue comment or a
      tool result. Why "just tell it to ignore instructions in data" is not a control. `[TRAP]`
      `[X-REF 13]`
2.9.3 The controls that actually hold: deny rules, `PreToolUse` blocking hooks, sandboxing,
      least-privilege tool sets, and human confirmation on outward-facing actions. `[NUM]`
2.9.4 Secrets: `Read` deny rules for `.env` and `secrets/**`, sandbox credential masking
      (`sandbox.credentials.{envVars,files,sigv4,awsPairs}`), and why an agent transcript is a
      data-exfiltration surface. `[DOC]`
2.9.5 What leaves the machine, and the settings that govern it: `cleanupPeriodDays`,
      `skipWebFetchPreflight`, telemetry/OTel keys, `env`. `[DOC]`
2.9.6 Managed settings delivery: `managed-settings.json`, MDM, server-managed settings from the
      console; `managedSourcesBehavior`, `policyHelper` (`path`, `refreshIntervalMs`, `timeoutMs`),
      `forceRemoteSettingsRefresh`. `[DOC]`
2.9.7 The `allowManaged*Only` family as the "developers cannot re-open this" lock:
      `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`,
      `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`.
      `[DOC]`
2.9.8 Login and version control at org scale: `forceLoginMethod`, `forceLoginOrgUUID`,
      `availableModels`, `enforceAvailableModels`, `requiredMinimumVersion`,
      `requiredMaximumVersion`, `autoUpdatesChannel`. `[DOC]`
2.9.9 Attribution and audit: `attribution.{commit,pr,sessionUrl}`, `includeGitInstructions`,
      `prUrlTemplate`. Why "which commits came from an agent" is a question you will be asked.
      `[DOC]`
2.9.10 `[CASE]` The harness's own posture, assembled from its files: a fail-closed prod-AWS
       deny-list provisioned at user scope by `bootstrap-user-scope.sh`, `prod-guard-*` hooks,
       read-only triage scripts (`triage-aws-ro.sh`), and a Jira tool withheld from the agent that
       would otherwise use it. `[CASE]`
2.9.11 The rollout argument a Staff engineer has to make: capability as a **versioned,
       dependency-managed plugin with hooks and eval suites**, not tips in a wiki. What that buys
       — review, rollback, measurement — and what it costs. `[CASE]`







