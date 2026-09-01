### §3.10 Verification — the AI-specific failure mode

3.10.1 The core asymmetry: an agent produces **plausible** artefacts, and skimming a diff is the
       review method worst matched to plausibility. `[ZERO]`
3.10.2 Law: **re-run every published artefact in its published form.** In this repository that
       found more defects than every structural check combined — code that no longer produced the
       transcript printed beneath it, invented values that compiled fine, a repro returning the
       opposite of its claim, and run-specific numbers published as constants. `[INCIDENT]`
       `[PROVE]`
3.10.3 Law: **a checker whose input can switch it off is worse than no checker.** The NUL-byte
       incident — one generated file contained a literal NUL, `file` classified it as `data`, grep
       returned *nothing* (not a mismatch), every text check silently skipped it and reported
       success. Assert text-ness before any grep-based gate. `[INCIDENT]` `[PROVE]`
3.10.4 Law: **certify from final state, never from a pre-write computation.** A footer regex ending
       `\s*$` ate nine files' trailing newlines; an md5 was taken over a patched harness while the
       shipped files still failed to compile. `[INCIDENT]`
3.10.5 Law: **a build proof must pin its harness beside the digest.** Two honest runs over
       identical files produced different md5s purely because one wrapped a throwing snippet. A
       bare digest is unfalsifiable. `[INCIDENT]`
3.10.6 Law: **never let a status row point at a missing path.** The costliest bookkeeping failure
       here, and the one-line gate that prevents it. `[INCIDENT]`
3.10.7 Law: **a closed lane is not a verified lane.** Two cross-lane contradictions were found
       after their owners had stood down; only a pass that reads across boundaries finds these.
       `[INCIDENT]`
3.10.8 Executable evidence over structural evidence: a compile, a test, a transcript beats a regex
       over a file. Rank the evidence types. `[NUM]`
3.10.9 Automating the gates: `PostToolUse` formatters and linters, a `Stop` hook that refuses to
       finish on a red build, and CI as the outer loop. `[BUILD]`
3.10.10 `[TRAP]` Command shapes that defeat a permission matcher and therefore your own gates:
        heredocs, `&&`/`;` chains, `$(...)`. Use one command per call, absolute paths, and the
        Write tool for scratch files. `[TRAP]` `[CASE]`
3.10.11 Review capacity as the real ceiling on agent throughput, argued with numbers. `[PROVE]`
        `[NUM]`








