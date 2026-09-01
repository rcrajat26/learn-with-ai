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
