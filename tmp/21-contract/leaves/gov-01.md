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
