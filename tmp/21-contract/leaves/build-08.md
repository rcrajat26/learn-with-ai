### §4.7 Verification harness

4.7.1 A `verify.sh` for this repository's own notes: text-ness assertion first, then every
      structural check, then re-run every fenced listing. `[BUILD]`
4.7.2 Make one check fail deliberately and confirm it fails loudly rather than skipping. `[BUILD]`
      `[PROVE]`
4.7.3 Wire it as a `Stop` hook and as a CI job, and state which failures belong in which. `[BUILD]`
4.7.4 A skill eval: three prompts that should trigger a skill and three that should not; run and
      score them. `[BUILD]` `[PROVE]`







