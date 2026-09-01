### §5.1 The questions, with the answer shape

5.1.1 "How do you use AI in your workflow?" — the 60-second answer that is about systems, not
      tools, and the three follow-ups it invites.
5.1.2 "What is a context window?" — the answer that includes the cost consequence, not just the
      number.
5.1.3 "Why does a long session get worse?" — compaction, prefix cost, and drift, in that order.
5.1.4 "How do you stop an agent doing something destructive?" — deny rules, `PreToolUse` blocking
      hooks, sandbox, withheld tools, human gates. Ranked by strength, and why prompting is not on
      the list.
5.1.5 "Deny beats allow — why does that matter?" — the allowlist-exception trap in one sentence.
5.1.6 "What is the difference between `CLAUDE.md`, a skill, and a hook?" — always-on context,
      on-demand context, guaranteed execution.
5.1.7 "When do you use a subagent?" — verbose-in/small-out, parallel with disjoint writes,
      different capability set. Plus the 2× cost.
5.1.8 "How would you run this in CI?" — `-p --output-format json`, the three ceilings,
      `--settings` by absolute path, `setup-token`, and what must not be present.
