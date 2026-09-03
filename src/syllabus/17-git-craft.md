# Syllabus — 17 Git Craft, Code Review & Debugging Method

**Target version: Git 2.55 (released 29 Jun 2026), checked 2026-09-03.** Every constant, default,
config name and command below is stated against 2.55 unless a leaf says otherwise. Because most
corporate estates run something older, every leaf that depends on a version boundary names the
release that introduced the behaviour, and the widely-repeated-but-now-stale claims carry
`[VERSION-TRAP]`.

| Layer | Release this file targets | Previous generation, also covered |
|---|---|---|
| Git | **2.55** (29 Jun 2026). 2.54 (20 Apr 2026), 2.53 (Feb 2026), 2.52 (Nov 2025), 2.51 (18 Aug 2025), 2.50 (Jun 2025) | **2.39–2.45** — the LTS-ish range shipped by Debian/RHEL/Ubuntu images and most CI runners |
| Default hash | **SHA-1 (with SHA-1DC collision detection)**; SHA-256 selectable via `git init --object-format=sha256` | SHA-256 becomes the *default* in **Git 3.0**, not before |
| Default ref backend | **`files`** (loose refs + `packed-refs`); `reftable` selectable via `git init --ref-format=reftable`, production-ready and no longer experimental as of 2.51 | `reftable` becomes the default in **Git 3.0** |
| Default merge strategy | **`ort`** (default since 2.34); `recursive` is a *synonym* for `ort` since **2.50** | `recursive` was the real implementation up to 2.33 |
| Default branch name | **`master`** with an advice warning; changes to `main` in **Git 3.0** | `init.defaultBranch` override since 2.28 |
| Maintenance strategy | **`geometric`** is the default for *manual* `git maintenance run` since **2.54**; `incremental` remains the default for *scheduled* maintenance | `gc` was the only strategy pre-2.30 |
| Build | Rust auto-detected in **2.52**, default-enabled in **2.55**, **mandatory in Git 3.0** | C-only builds |
| git-filter-repo | current release; `git filter-branch` is officially discouraged and warns on use | BFG Repo-Cleaner as the older alternative |
| Java runtime for all `[BUILD]` code | **Java 21 LTS** | — |

**The sixteen deltas that most often produce a stale answer in a 2026 Git interview**, each marked
`[VERSION-TRAP]` at its leaf:

1. **`recursive` is not a distinct strategy any more.** Since 2.34 `ort` is the default; since 2.50
   `-s recursive` is literally an alias for `ort`. Saying "we use recursive, ort is the new one" is
   describing a distinction that no longer exists in the code. `[RESEARCH]`
2. **SHA-256 is not the default yet.** It is fully implemented and selectable, and it is a declared
   Git 3.0 breaking change — but a 2.55 `git init` still produces a SHA-1 repository. Interop
   between SHA-1 and SHA-256 repositories is still groundwork as of 2.52. `[RESEARCH]`
3. **SHA-1 in Git is not plain SHA-1.** Since 2.13 Git uses **SHA-1DC** (collision-detecting SHA-1),
   which aborts on inputs bearing the SHAttered attack signature. "Git is broken because SHA-1 is
   broken" is a 2017 answer. `[RESEARCH]`
4. **`reftable` exists and is production-ready.** `git init --ref-format=reftable`, stable on
   Windows and macOS as of 2.51, default in 3.0. Any answer that says "refs are files, or lines in
   `packed-refs`" is now only two thirds of the truth. `[RESEARCH]`
5. **`git switch` and `git restore` are no longer experimental** — that label was dropped in **2.51**,
   six years after they were introduced in 2.23. And `git checkout` is explicitly **not** being
   deprecated in Git 3.0. `[RESEARCH]`
6. **`git history` exists** (experimental, 2.54): `git history reword`, `git history split`, and
   `git history fixup` (2.55). These do targeted history rewrites without an interactive rebase.
   `[RESEARCH]`
7. **Hooks can live in config now** (2.54): `[hook "linter"] event = pre-commit` plus `git hook list`
   and `hook.<name>.enabled`. 2.55 added parallel execution via `hook.<name>.parallel`, `hook.jobs`,
   `hook.<event>.jobs`. "Hooks are shell scripts in `.git/hooks` and therefore not shareable" is now
   a partly-obsolete complaint. `[RESEARCH]`
8. **`git maintenance` has a geometric strategy** (2.54) that replaces all-into-one `gc` repacks;
   `git maintenance geometric` landed as a task in 2.52. `[RESEARCH]`
9. **`git last-modified`** (2.52) gives tree-level blame — the closest ancestor commit touching each
   path — 5.48x faster than the `ls-tree` + `log` idiom people write by hand. `[RESEARCH]`
10. **`git repo info` / `git repo structure`** (2.52, experimental; extended in 2.53) is the built-in
    repository-health tool that used to require `git count-objects -vH` plus scripts. `[RESEARCH]`
11. **`git refs list` / `git refs exists`** (2.52) are the new spellings of `for-each-ref` and
    `show-ref --exists`. `[RESEARCH]`
12. **`git stash export` / `git stash import`** (2.51) make stashes transferable between machines —
    the long-standing "stashes are not pushable" objection now has an answer. `[RESEARCH]`
13. **`git rebase --update-refs`** rewrites every intermediate branch in a stack in one pass. This is
    the single most useful command for stacked PRs and is absent from every pre-2.38 tutorial.
14. **Cruft packs are on by default** (`gc.cruftPacks = true`): unreachable objects are packed into a
    `*.mtimes`-carrying cruft pack rather than exploded into loose objects. The classic
    "`git gc` turns your garbage into a million loose files" answer is stale. `[RESEARCH]`
15. **GitHub shipped native stacked PRs** — `gh-stack` CLI extension, private preview 13 Apr 2026,
    public preview 30 Jul 2026, with `gh stack sync` doing the cascading rebase. Squash-merge and
    rebase-merge break stack identity tracking; only merge commits work for intermediate PRs.
    `[RESEARCH]`
16. **Git 3.0 is a declared, documented set of breaking changes** (`git help BreakingChanges`), not a
    rumour: SHA-256 default, reftable default, `main` default, mandatory Rust,
    `safe.bareRepository=explicit`, removal of `git-pack-redundant`, `git-whatchanged`, grafts,
    `$GIT_COMMON_DIR/branches`, `name-rev --stdin`, `core.commentString=auto`,
    `core.preferSymlinkRefs=true`. No release date; the release before it will be an LTS.
    `[RESEARCH]`

**Scope boundary against the sibling guides.** This file owns **the version-control system as a
machine, and the two crafts that surround it**: how Git actually stores and moves data, how you
recover when it goes wrong, how a change becomes a reviewable unit, and how a defect is located by
method rather than by guessing. Owned elsewhere:

- Test frameworks, flakiness, coverage, mutation testing and Testcontainers live in
  `16-testing.md`; that guide explicitly parks "Git hooks and pre-commit gating" here. This guide
  owns hooks as a mechanism and the CI gate as a policy, not the tests themselves. `[X-REF 16]`
- Metrics, logs, traces, correlation/trace propagation, SLI/SLO, alerting, incident command and
  postmortem structure live in `20-observability-operations.md`. This guide owns the *debugging
  method* — hypothesis loop, "what changed", bisecting the problem space — and states the
  correlation-ID mechanism in one section before pointing there. `[X-REF 20]`
- Secret storage, KMS, vaults and rotation mechanics live in `18-cloud-aws.md` §6. This guide owns
  "a secret reached the object database" as an incident with an ordered response. `[X-REF 18]`
- OWASP, supply-chain and dependency risk live in `13-web-security.md`. This guide owns commit
  signing, `safe.directory`, hook execution as an attack surface, and the review checklist's
  security row. `[X-REF 13]`
- Container images, layer caching, CI runners and build reproducibility live in
  `19-docker-kubernetes.md`. This guide owns the clone/fetch cost model inside CI. `[X-REF 19]`
- Thread pools, `ThreadLocal`/MDC semantics and async boundaries live in
  `05-multithreading-concurrency.md`. This guide owns MDC only as the debugging carrier for a
  correlation ID. `[X-REF 05]`
- Connection pools, timeouts and retry storms as *causes* live in `10-networking-http.md` and
  `15-caching.md`. This guide owns them as entries in the intermittent-failure suspect list.
  `[X-REF 10]` `[X-REF 15]`
- Hashing as a data-structure concern (`hashCode`, collisions, load factor) lives in
  `02-java-collections.md`; cryptographic hashing as a primitive lives in `13-web-security.md`.
  This guide owns content addressing. `[X-REF 02]` `[X-REF 13]`
- AI-assisted commit messages, AI code review and agent-generated PRs live in
  `21-ai-for-coding.md`. This guide owns the review bar those tools must clear. `[X-REF 21]`
- "Design the version control system" as an interview prompt lives in `22-system-design.md`; this
  guide owns Git's own design decisions as the worked example. `[X-REF 22]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in **one paragraph** before pointing away — it never sends the reader off empty-handed.

**Every example, repository, service name, branch name and incident in the bible comes from the
QuizStakes domain in `src/scenario/scenario.md`.** Repositories are named for the services —
`funds-ledger`, `application-gateway`, `router-int`, `screening-service`, `account-opening`,
`client-restrictions`, `payment-service`, `notification-service`, `bonus-service`. Branches are
`feature/AO-4821-agreement-versioning`, `hotfix/FL-9930-stake-double-reserve`,
`release/2026.09`. Tickets are `AO-`, `FL-`, `CR-`, `PS-` prefixed. Commit messages, PR
descriptions, bisect scripts, review comments and incident narratives all use these. **The current
guide uses `feature/x`, `feature/timeouts`, `PAY-4821`, `PricingService:88`, `OrderService`,
`payment gateway`, `config/secrets.yml` and `tenant 42`; every one of those must be re-domained by
the write pass.**

**Domain facts the bible's examples must be consistent with** (scenario Appendix A): 2.4M registered
clients; 380k monthly active; 12k registrations/day (40k on campaign launch); 7.2k applications
reaching `AO-400`/day; **2.8M stake reservations/day at 1,200/sec**; 19.8M ledger entries/day at
230 writes/sec sustained and **13,600/sec peak**; a **30 ms** restriction-decision budget, a
**150 ms** stake-reservation budget, a **hard 500 ms** self-exclusion budget, a **4 s** card-deposit
end-to-end budget. **Invariant 8 — self-exclusion takes effect before the next stake** — is the
change that must never be reverted carelessly, never merged without review, and always bisectable.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real Git documentation, format spec, or Git source (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic Java 21 code, or a complete runnable script |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 2.55 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number / byte arithmetic explicitly |
| `[CFG]` | must give the exact config key spelling and its default value |
| `[CMD]` | must give the exact command line, copy-pasteable |
| `[HEX]` | must show a real hexdump / `xxd` / `git cat-file` output and read it byte by byte |
| `[RECOVER]` | a named recovery scenario: symptom → diagnosis → exact commands → verification |

---

# PART 1 — BASICS

## §1.1 Why Git exists at all, and what it decided differently

1.1.1 The April 2005 problem statement: BitKeeper's free licence for Linux kernel development was
      withdrawn, and no existing tool could handle a 20k-file tree with thousands of contributors
      and a maintainer hierarchy. Git was written in ten days to be *fast*, *distributed*, and
      *impossible to corrupt silently*. `[RESEARCH]`
1.1.2 Linus's three stated design goals, in his words: take CVS as an example of what **not** to do,
      support a distributed BitKeeper-like workflow, and include very strong safeguards against
      corruption. Every other property of Git falls out of these.
1.1.3 What "distributed" actually buys: every clone is a full backup with full history; commits,
      branches, diffs, log and blame are local and therefore fast; the network is only involved at
      `fetch`/`push`. Contrast with SVN/CVS/Perforce where `log` is a server round trip.
1.1.4 The central decision: **content addressing**. An object's name is the hash of its content, so
      identity and integrity are the same fact. This is why Git cannot silently corrupt data and
      why deduplication is automatic. `[PROVE]`
1.1.5 The second decision: **snapshots, not deltas**. A commit records a complete tree. Deltas exist
      only as a storage optimisation inside packfiles (§3.2), invisible to the model. `[TRAP]`
1.1.6 Why snapshots make rename detection a *heuristic* rather than a recorded fact, and why
      Subversion (which records renames) still loses to Git on merges. `[PROVE]` `[X-REF 22]`
1.1.7 The third decision: **history is immutable, and the hash chain proves it**. A commit hashes
      its tree, its parents, author, committer and message; changing anything changes the hash and
      every descendant hash. This single fact explains rebase, amend, force-push, and the golden
      rule. `[PROVE]`
1.1.8 Git as a *content-addressable filesystem with a VCS bolted on top* — Linus's own framing, and
      the reason `git hash-object`/`git cat-file` work on arbitrary bytes.
1.1.9 Plumbing versus porcelain as a deliberate architectural split: a small set of stable, scriptable
      low-level commands (plumbing) and a larger set of human-facing commands (porcelain) built on
      them. Porcelain output may change between releases; plumbing output is a contract.
1.1.10 The cost of these decisions: a UI that leaks implementation, an overloaded `checkout`, a
       staging area that confuses newcomers, poor handling of large binaries, and no first-class
       partial-repository checkout until 2.25.
1.1.11 The other VCSs worth being able to name and contrast: SVN (centralised, per-file revisions),
       Mercurial (distributed, immutable-by-default, `evolve`), Perforce (centralised, file locking,
       huge binaries), Fossil, Darcs (patch theory), Pijul, Sapling (Meta's Mercurial descendant),
       Jujutsu/`jj` (a Git-backed frontend with a working-copy-as-commit model). `[RESEARCH]`
1.1.12 Why the industry converged on Git despite the UI: network effects (GitHub 2008), the
       branching cost collapse, and the fact that its data model is correct even when its commands
       are not.
1.1.13 The 144 built-in commands as of 2.51 — you need roughly 25 daily, 20 more occasionally, and
       the rest never. Name the daily set explicitly so the reader can audit their own fluency.
       `[NUM]` `[RESEARCH]`
1.1.14 The interview framing this guide serves: turning "I use Git" into "I can explain what a
       commit is, recover a repository someone broke, and make a 900-line change reviewable."

*(14 leaves)*

## §1.2 The object database: four object types

1.2.1 Every object is stored as `<type> <size>\0<content>`, and its name is the hash of that entire
      byte string including the header. The header is why `sha1sum file` ≠ `git hash-object file`.
      `[PROVE]` `[HEX]` `[SOURCE]`
1.2.2 The four types and their type strings: `blob`, `tree`, `commit`, `tag`. There is no fifth type
      in the object database — everything else (index, reflog, packed-refs) is not an object.
1.2.3 **Blob** — raw file content, no filename, no mode, no timestamp. Two identical files anywhere
      in history are one blob. `[PROVE]`
1.2.4 A blob has no notion of "text" or "binary"; that judgement is made at diff time from content
      inspection and `.gitattributes` (§3.18). `[TRAP]`
1.2.5 **Tree** — a sorted list of entries, each `<mode> <name>\0<20-or-32-byte-raw-oid>`. Note the
      OID is **binary**, not hex, which is why `cat`-ing a tree object produces garbage. `[HEX]`
      `[SOURCE]`
1.2.6 The six legal modes and their exact octal values: `100644` regular file, `100755` executable,
      `120000` symlink, `040000` directory (written as `40000`, no leading zero), `160000` gitlink
      (submodule commit), `100664` (legacy, tolerated on read). `[NUM]` `[SOURCE]`
1.2.7 Git records exactly one permission bit — the executable bit. Not read/write bits, not owner,
      not group, not ACLs, not extended attributes. `core.fileMode=false` disables even that.
      `[TRAP]` `[CFG]`
1.2.8 Tree entry sort order is by byte value of the name, with directories sorted **as if they ended
      in `/`**. Getting this wrong is the classic bug when writing trees by hand. `[TRAP]` `[PROVE]`
1.2.9 Git has no concept of an empty directory: a tree with no entries is never written by
      porcelain. The `.gitkeep` convention is a workaround, not a feature. `[TRAP]`
1.2.10 **Commit** — a text object with `tree`, zero or more `parent` lines, `author`, `committer`,
       optional `gpgsig`/`gpgsig-sha256`, optional `encoding`, optional `mergetag`, a blank line,
       and the message. `[HEX]` `[SOURCE]`
1.2.11 Author versus committer, and every operation that makes them diverge: `rebase`, `cherry-pick`,
       `am`, `commit --amend`, `filter-repo`. GitHub's contribution graph uses the **author** date;
       `git log` sorts by **commit** date by default. `[TRAP]` `[NUM]`
1.2.12 The identity line format: `Name <email> <unix-timestamp> <±HHMM>`. Timezone is stored as a
       display hint only; ordering uses the epoch seconds.
1.2.13 Parent count semantics: 0 = root commit, 1 = ordinary, 2 = merge, ≥3 = octopus merge. Parent
       **order** matters — parent 1 is the branch you were on, and it is what `--first-parent` and
       `revert -m 1` mean. `[TRAP]`
1.2.14 A repository can have multiple root commits (`git checkout --orphan`, merged histories, `gh-pages`).
       `git log --max-parents=0` lists them.
1.2.15 **Tag object (annotated)** — `object`, `type`, `tag`, `tagger`, message, optional signature.
       A *lightweight* tag is not an object at all, just a ref pointing directly at a commit.
       `[TRAP]`
1.2.16 Tag objects can point at any object type, including blobs — the mechanism behind
       `git tag --annotate` on a public key blob.
1.2.17 The object graph is a **DAG** in two senses: commits point at parents, and commits point at
       trees which point at trees and blobs. Both are acyclic because a cycle would require a hash
       to contain itself. `[PROVE]`
1.2.18 `git cat-file -t <oid>`, `-s`, `-p`, `--batch`, `--batch-check`, `--batch-all-objects`,
       `--unordered`, `--filters` — the full read surface. `[CMD]`
1.2.19 `git hash-object -w --stdin`, `-t <type>`, `--path`, `--no-filters` — the full write surface.
       `[CMD]`
1.2.20 `git mktree`, `git commit-tree`, `git mktag`, `git write-tree`, `git read-tree` — building
       objects without porcelain. `[CMD]`
1.2.21 `git rev-parse <rev>` and `git rev-parse --verify`, `--short`, `--abbrev-ref`, `--git-dir`,
       `--show-toplevel`, `--is-inside-work-tree`, `--git-path` — the resolver you script against.
       `[CMD]`
1.2.22 Deduplication in practice: reverting a file to an earlier content adds zero new blobs;
       a 200 MB binary changed once adds a second 200 MB blob forever. `[NUM]` `[PROVE]`
1.2.23 Why Git stores whole objects rather than diffs at the model level, and what that buys:
       O(1) checkout of any revision, no delta-chain replay to read a file, and integrity that does
       not depend on the correctness of the delta algorithm. `[PROVE]`
1.2.24 Object size accounting: `git cat-file -s`, `git count-objects -vH`, and the newer
       `git repo structure` (2.52+, extended in 2.53 to report inflated size and disk size per
       object type). `[CMD]` `[RESEARCH]`

*(24 leaves)*

## §1.3 Hashing: SHA-1, SHA-1DC, and the SHA-256 transition

1.3.1 A 40-hex-character object name is a 160-bit SHA-1; a 64-hex-character name is a 256-bit
      SHA-256. `[NUM]`
1.3.2 Why the hash is over `<type> <size>\0<content>` and not the content alone: type separation
      prevents a blob and a commit with identical bytes colliding by construction. `[PROVE]`
1.3.3 The birthday bound: a random 160-bit collision needs ~2^80 objects. Real repositories have
      ~10^7 objects, so accidental collision is not the threat model. `[PROVE]` `[NUM]`
1.3.4 The actual threat: **chosen-prefix collisions**. SHAttered (Feb 2017) produced two PDFs with
      identical SHA-1; Shambles (2020) produced a chosen-prefix collision for ~$45k of compute.
      `[NUM]` `[RESEARCH]`
1.3.5 **Git does not use plain SHA-1.** Since 2.13 it uses `sha1collisiondetection` (SHA-1DC), which
      detects the unavoidable-bit-condition signature of a collision attack and **aborts** rather
      than producing a hash. The performance cost is ~2x on hashing, which is not the bottleneck.
      `[VERSION-TRAP]` `[RESEARCH]`
1.3.6 What a successful collision would actually let an attacker do, and what it would not: object
      substitution on a fetch/push, but not silent modification of an existing local object, because
      Git refuses to overwrite an existing object with the same name. `[PROVE]`
1.3.7 `git init --object-format=sha256`, `extensions.objectFormat = sha256`, and
      `GIT_DEFAULT_HASH`. `[CFG]` `[CMD]`
1.3.8 SHA-256 is a Git 3.0 *default* change, not a new capability. Selectable since 2.29.
      `[VERSION-TRAP]` `[RESEARCH]`
1.3.9 The interoperability problem: a SHA-256 repository cannot push to a SHA-1 remote today.
      Git 2.52 shipped "groundwork for SHA-1/SHA-256 interoperability" — a translation table
      mapping OIDs across formats — but the loop is not closed. This is why the transition is slow.
      `[RESEARCH]`
1.3.10 What breaks in your tooling when the OID length changes from 40 to 64: regexes, database
       columns typed `CHAR(40)`, log parsers, CI scripts, artifact naming, deploy manifests.
       `[TRAP]`
1.3.11 Abbreviated OIDs: `core.abbrev` (default `auto`), the minimum-uniqueness rule, and why the
       auto length grows with repository size (7 for small repos, 12 in the kernel). `[CFG]` `[NUM]`
1.3.12 **Trap:** an abbreviation that is unique today may become ambiguous tomorrow. Never write an
       abbreviated OID into a durable artefact — deploy manifests, release notes, or a database
       row. `[TRAP]`
1.3.13 `git rev-parse --disambiguate=<prefix>` and the `ambiguous argument` error.
1.3.14 The `--allow-unknown-type` and `--literally` escape hatches on `hash-object`/`cat-file`, used
       to construct objects Git would otherwise refuse.
1.3.15 Integrity verification end to end: `git fsck`, `git fsck --strict`, `git verify-pack -v`,
       and the pack trailer checksum. Every read from a pack verifies the object's own hash.
1.3.16 The `transfer.fsckObjects`, `fetch.fsckObjects`, `receive.fsckObjects` config trio — turning
       on validation of incoming objects, which is off by default for performance. `[CFG]`

*(16 leaves)*

## §1.4 Refs, HEAD, and the ref storage backends

1.4.1 A ref is a name mapping to an OID. Nothing more. Branches, tags and remote-tracking refs are
      all the same mechanism under different namespaces.
1.4.2 The namespace inventory: `refs/heads/*` (local branches), `refs/tags/*`, `refs/remotes/<remote>/*`,
      `refs/notes/*`, `refs/stash`, `refs/replace/*`, `refs/bisect/*`, `refs/rewritten/*`,
      `refs/prefetch/*` (from the `prefetch` maintenance task), `refs/worktree/*`, `refs/pull/*` and
      `refs/merge-requests/*` (host-created, not pushed by default). `[RESEARCH]`
1.4.3 The `files` backend: a loose ref is a file under `.git/refs/` containing 41 bytes — 40 hex
      characters plus a newline (65 bytes for SHA-256). "Creating a branch writes 41 bytes" is
      literally true. `[NUM]` `[HEX]`
1.4.4 `.git/packed-refs`: a sorted text file of `<oid> <refname>` lines, with `^<oid>` peel lines for
      annotated tags, and a `# pack-refs with: peeled fully-peeled sorted` header. `[SOURCE]`
      `[HEX]`
1.4.5 Lookup order under the `files` backend: loose ref first, then `packed-refs`. A loose ref
      **shadows** a packed one, which is how deletion of a packed ref requires rewriting the whole
      file. `[TRAP]`
1.4.6 `git pack-refs --all --prune` and the `pack-refs` maintenance task; the inode-exhaustion and
      `readdir` cost that motivates it in repositories with 100k+ refs. `[CMD]` `[NUM]`
1.4.7 Directory/file conflicts: you cannot have both `refs/heads/feature` and
      `refs/heads/feature/AO-4821` under the `files` backend, because one is a file and the other
      needs a directory of the same name. `[TRAP]` `[PROVE]`
1.4.8 Case-insensitive filesystems (macOS, Windows) collapse `refs/heads/Feature` and
      `refs/heads/feature`. Another `files`-backend-only failure. `[TRAP]`
1.4.9 **reftable**: a binary, block-structured, prefix-compressed, binary-searchable stack of tables
      that stores refs *and* reflogs together. `git init --ref-format=reftable`,
      `init.defaultRefFormat`, `extensions.refStorage = reftable`. Default in Git 3.0.
      `[CFG]` `[RESEARCH]`
1.4.10 Reftable's measured wins on Android's 866k-ref repository: **62.2 MB → 36.1 MB**, cold
       single-ref lookup **409,660 µs → 33.9 µs** (~12,000x), full scan 402 ms → 112 ms, reflog
       173 MB → 5 MB. Numbers this large are the whole argument. `[NUM]` `[RESEARCH]` `[SOURCE]`
1.4.11 What reftable fixes that packed-refs cannot: atomic multi-ref transactions in
       O(size-of-update) rather than O(size-of-all-refs), D/F conflicts, case-insensitive
       filesystems, deletion tombstones, and reflog scalability. `[PROVE]` `[RESEARCH]`
1.4.12 Reftable batched updates in 2.51: **22x faster `git fetch`, 18x faster `git push`** on large
       repositories. `[NUM]` `[RESEARCH]`
1.4.13 `HEAD` — normally a symbolic ref, the file `.git/HEAD` containing
       `ref: refs/heads/feature/AO-4821`. `[HEX]`
1.4.14 **Detached HEAD** — `.git/HEAD` contains a raw OID. What it is for (bisect, worktree
       `--detach`, `checkout <tag>`, submodules), why commits made there are only reachable via
       reflog, and the exact recovery. `[TRAP]` `[RECOVER]`
1.4.15 The other pseudo-refs, each with what writes it: `ORIG_HEAD` (before a destructive op),
       `FETCH_HEAD`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `REBASE_HEAD`,
       `BISECT_HEAD`, `AUTO_MERGE` (2.38+, the ort-produced auto-merge tree during a conflict).
       `[RESEARCH]`
1.4.16 `git symbolic-ref HEAD`, `git symbolic-ref --short HEAD`, `git update-ref`,
       `git update-ref --stdin` (batched atomic transactions), `git update-ref -d`. `[CMD]`
1.4.17 `git show-ref`, `git for-each-ref --format=...`, and the 2.52 spellings `git refs list` and
       `git refs exists`. `[CMD]` `[RESEARCH]`
1.4.18 `git for-each-ref` format atoms worth memorising: `%(refname:short)`, `%(objectname)`,
       `%(upstream:track)`, `%(committerdate:relative)`, `%(HEAD)`, `%(contents:subject)` — this is
       how you build a real branch dashboard. `[CMD]`
1.4.19 Ref namespaces on the server: `GIT_NAMESPACE` and `gitnamespaces`, used by hosts to serve many
       logical repos from one object store.
1.4.20 The reference-transaction hook (§2.13) fires on every ref update in `prepared`/`committed`/
       `aborted` states — the hook that makes server-side ref auditing possible. `[RESEARCH]`
1.4.21 `core.preferSymlinkRefs=true` is removed in Git 3.0; refs have been textual for years and
       reading symlinks remains supported only for compatibility. `[VERSION-TRAP]` `[RESEARCH]`
1.4.22 The mental model to state in an interview: **a branch is a 41-byte file whose content is a
       commit OID; branching is free because there is nothing to copy.** Everything about Git's
       branching ergonomics follows.

*(22 leaves)*

## §1.5 The three trees: working tree, index, HEAD

1.5.1 The four places a change can live, and the command that moves it out of each: working
      directory → `git add` → index → `git commit` → local repository → `git push` → remote. The
      current guide's table, preserved and extended with `git fetch` on the inbound edge.
1.5.2 The index is **not** "a list of staged files". It is a full, flat, sorted snapshot of the next
      commit's tree, with stat data for every path — including paths you have not touched.
      `[TRAP]` `[PROVE]`
1.5.3 Why the index exists at all, stated as three jobs: (a) allow partial commits, (b) cache stat
      data so `git status` does not have to hash every file, (c) hold the three conflict stages
      during a merge. Any explanation missing (b) misses the performance reason. `[PROVE]`
1.5.4 The stat-cache mechanism: `git status` compares `ctime`, `mtime`, `dev`, `ino`, `uid`, `gid`,
      `size` and mode against the index; only on a mismatch does it hash the file. `[PROVE]`
1.5.5 The racy-timestamp problem: a file modified within the same second the index was written is
      indistinguishable by mtime, so Git treats index-mtime-equal entries as "racily clean" and
      rehashes them. `[PROVE]` `[TRAP]`
1.5.6 `git status` versus `git status --short` versus `git status --porcelain=v1|v2` — and why
      scripts must use `--porcelain`, never the human output. `[CMD]`
1.5.7 The two-column XY status codes and every combination worth reading: ` M`, `M `, `MM`, `A `,
      `AM`, ` D`, `D `, `R `, `C `, `??`, `!!`, `UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`. `[SOURCE]`
1.5.8 `git add` variants: `-A`, `-u`, `.`, `-p`, `-i`, `-N`/`--intent-to-add`, `-f`, `--renormalize`,
      `--chmod=+x`, `--pathspec-from-file`. `[CMD]`
1.5.9 `git add -p` as a discipline, not just a command: it forces you to read every hunk before it
      becomes a commit, which catches debug statements, commented-out code and accidental file
      inclusion before a reviewer does. Preserve the current guide's emphasis verbatim.
1.5.10 The `add -p` sub-commands in full: `y`, `n`, `q`, `a`, `d`, `s` (split), `e` (edit hunk),
       `K`/`k`/`J`/`j`, `g` (goto), `/` (search), `?`. `e` is the one nobody learns and the one that
       lets you stage half a line. `[CMD]`
1.5.11 Git 2.54 improvements to `add -p`: visual indicators for previously accepted/skipped hunks,
       and `--no-auto-advance` to stop it jumping to the next file. `[RESEARCH]`
1.5.12 `--intent-to-add` and why it makes `git diff` show a new file's content: the path exists in
       the index with a zero-length blob, so a diff can be computed. `[PROVE]`
1.5.13 `git diff` = working tree vs index; `git diff --staged`/`--cached` = index vs HEAD;
       `git diff HEAD` = working tree vs HEAD. The three-way distinction is the single most useful
       fact in this section. Preserve the current guide's table.
1.5.14 `git diff main...HEAD` (three dots) = what my branch adds since the merge base;
       `git diff main..HEAD` (two dots) = the raw difference including what main added. **These are
       different questions and people ask the wrong one constantly.** `[TRAP]` `[PROVE]`
1.5.15 The three-dot/two-dot asymmetry between `git diff` and `git log`: for `log`, `A..B` is
       "reachable from B not A" and `A...B` is the symmetric difference; for `diff` the meanings do
       not line up with that intuition. `[TRAP]` `[PROVE]`
1.5.16 The conflict stages in the index: stage 0 resolved, stage 1 base, stage 2 ours, stage 3
       theirs. `git ls-files -u` shows them; `git checkout-index --stage=2` extracts one.
       `[NUM]` `[CMD]`
1.5.17 The cache-tree extension: precomputed tree OIDs for unmodified directories, which is why
       `git commit` on a 2M-file repository does not have to build 2M tree objects. `[PROVE]`
1.5.18 `git write-tree` fails if the index has unmerged entries — the plumbing-level expression of
       "you must resolve conflicts before committing". `[PROVE]`
1.5.19 `git ls-files` with `-s`, `-u`, `-o`, `-i`, `--exclude-standard`, `-v`, `-t`,
       `--debug` — reading the index directly. `[CMD]`
1.5.20 `git update-index` and its dangerous flags: `--assume-unchanged` (a *performance* promise you
       are making to Git) versus `--skip-worktree` (a *sparse-checkout* declaration). Neither is a
       way to ignore a tracked file, and both silently lose changes. `[TRAP]`
1.5.21 The index is per-worktree, lives at `$GIT_DIR/index`, and is protected by `index.lock` — the
       source of the "Another git process seems to be running" error and its correct resolution
       (check for the process; only then delete the lock). `[TRAP]` `[RECOVER]`
1.5.22 `git rm`, `git rm --cached`, `git mv` — and the fact that `git mv` is just remove + add, since
       Git does not record renames. `[PROVE]`

*(22 leaves)*

## §1.6 The commit DAG and revision syntax

1.6.1 Reachability as the fundamental relation: an object is *live* if some ref reaches it. Garbage
      collection, `fetch` negotiation, `bisect` and `gc` are all reachability computations.
      `[PROVE]`
1.6.2 Ancestry: `A` is an ancestor of `B` iff there is a parent-chain from `B` to `A`.
      `git merge-base --is-ancestor A B` answers it in one exit code. `[CMD]`
1.6.3 `HEAD~n` walks **first parents only**; `HEAD^n` selects the **nth parent** of one commit.
      `HEAD^2` is the second parent of a merge; `HEAD~2` is the grandparent. This is the single most
      commonly confused pair of operators in Git. `[TRAP]` `[PROVE]`
1.6.4 Combining them: `HEAD~3^2~1`, and reading such an expression left to right as a walk.
1.6.5 The full revision-selection grammar (`gitrevisions`): `<sha1>`, `<describeOutput>`,
      `<refname>`, `@`, `<refname>@{<date>}`, `<refname>@{<n>}`, `@{-<n>}` (previous checkout),
      `<branch>@{upstream}` / `@{u}`, `<branch>@{push}`, `<rev>^{<type>}`, `<rev>^{}` (peel a tag),
      `<rev>^{/<text>}`, `:/<text>`, `:<path>`, `:<n>:<path>`. `[SOURCE]`
1.6.6 `@` alone is a synonym for `HEAD` — short, legal, and almost never taught.
1.6.7 `@{-1}` is "the branch I was on before", which makes `git switch -` work.
1.6.8 Range syntax for `git log`: `A..B`, `A...B`, `^A B`, `--not A`, `B --not A`, and multiple
      ranges. `[PROVE]`
1.6.9 `git log --left-right A...B` to see which side each commit came from; `--cherry-mark`,
      `--cherry-pick`, `--cherry` to identify commits already present on the other side by patch-id.
      `[CMD]`
1.6.10 `--first-parent`: read a merge-heavy history as the sequence of integrations rather than the
       sequence of individual contributions. Essential on a repository that merges rather than
       squashes. `[PROVE]`
1.6.11 History-simplification flags and what each *removes*: default simplification, `--full-history`,
       `--dense`, `--sparse`, `--simplify-merges`, `--ancestry-path`. The reason
       `git log -- <path>` "loses" commits. `[TRAP]` `[SOURCE]`
1.6.12 Ordering flags: default (reverse chronological by commit date), `--topo-order`,
       `--date-order`, `--author-date-order`, `--reverse`. `[PROVE]`
1.6.13 **Trap:** commit dates can go backwards. Clock skew, `--committer-date-is-author-date`,
       rebases and imports all produce histories where a child is dated before its parent, which
       breaks naive date-sorted tooling. `[TRAP]` `[NUM]`
1.6.14 `git log --oneline --graph --decorate --all` as the one command that makes the DAG visible;
       Git 2.55 adds `--graph-lane-limit=<n>` to keep the graph readable on wide histories.
       `[CMD]` `[RESEARCH]`
1.6.15 Formatting: `--pretty=format:`, the placeholder inventory (`%H %h %T %P %an %ae %ad %cd %cr
       %s %b %d %D %G? %(trailers)`), `--date=` formats (`relative`, `iso`, `iso-strict`, `short`,
       `format:`, `human`, `unix`), and `log.date`. `[CMD]` `[CFG]`
1.6.16 Selection: `--author`, `--committer`, `--grep`, `--all-match`, `--invert-grep`, `-i`,
       `--since`/`--until`, `--since-as-filter`, `-n`, `--skip`, `--merges`, `--no-merges`,
       `--min-parents`/`--max-parents`. `[CMD]`
1.6.17 Git 2.55: `--max-count-oldest=<n>` selects the *oldest* n commits in a range, the complement
       of `-n`. `[RESEARCH]`
1.6.18 Content search: `-S<string>` (pickaxe — commits where the *count* of occurrences changed),
       `-G<regex>` (commits whose diff text matches), `--pickaxe-regex`, `--pickaxe-all`. The
       difference between `-S` and `-G` is a genuine interview question. `[PROVE]` `[TRAP]`
1.6.19 `git log -L <start>,<end>:<file>` and `-L :<funcname>:<file>` — line-history for a range or a
       function. Git 2.54 made `-L` compatible with `-S`/`-G`, patch formatting, `--word-diff` and
       `--color-moved`. `[RESEARCH]`
1.6.20 `git log --follow <file>` for rename-crossing history, and why it is a heuristic that only
       works for a single path. `[TRAP]`
1.6.21 `git shortlog -sne`, `--group=trailer:Co-authored-by`, and using it to find the owner of a
       subsystem before you open a PR. `[CMD]`
1.6.22 `git describe`, `--tags`, `--always`, `--dirty`, `--match`, `--exclude`, `--first-parent`, and
       the `v1.4-14-g2414721` output format read field by field. Used for build version strings.
       2.52 made it ~30% faster via a priority queue. `[NUM]` `[RESEARCH]`
1.6.23 `git name-rev` and its `--annotate-stdin` flag (`--stdin` is deprecated since 2.40 and removed
       in Git 3.0). `[VERSION-TRAP]` `[RESEARCH]`
1.6.24 `git rev-list` as the plumbing behind everything: `--count`, `--objects`, `--all`,
       `--no-walk`, `--boundary`, `--missing`, `--filter`. Git 2.55 extends `--path-walk` with
       `blob:none`, `blob:limit=<n>`, `tree:0`, `object:type=<type>`, `sparse:<oid>` filters.
       `[CMD]` `[RESEARCH]`
1.6.25 Pathspec syntax as a first-class language: literal paths, globs, `:(exclude)`/`:!`,
       `:(icase)`, `:(glob)`, `:(literal)`, `:(top)`/`:/`, `:(attr:<attr>)`. The `--` separator and
       why it disambiguates a path from a ref. `[SOURCE]` `[TRAP]`
1.6.26 `git merge-base`, `--all` (multiple bases exist for criss-cross histories),
       `--octopus`, `--fork-point`, `--independent`. The existence of *multiple* merge bases is the
       entire reason `ort` is recursive. `[PROVE]`

*(26 leaves)*

## §1.7 Recording changes: the daily porcelain

1.7.1 `git init`, `--bare`, `--template`, `--initial-branch`/`-b`, `--object-format`, `--ref-format`,
      `--shared`. `[CMD]`
1.7.2 `git clone`, `--depth`, `--shallow-since`, `--shallow-exclude`, `--single-branch`,
      `--no-tags`, `--branch`, `--filter`, `--recurse-submodules`, `--jobs`, `--bare`, `--mirror`,
      `--reference`, `--dissociate`, `--separate-git-dir`. `[CMD]`
1.7.3 `--bare` versus `--mirror`: mirror also copies remote-tracking refs and sets
      `remote.origin.mirror`, so `git fetch` overwrites everything. The right tool for a repository
      migration and the wrong tool for a backup you intend to work in. `[TRAP]`
1.7.4 Shallow clones: the `.git/shallow` file, grafted parents, and the operations that break —
      `git log` beyond the boundary, `git merge-base` with an old branch, `git describe`, and
      `git push` of the full history. `git fetch --unshallow` and `--deepen`. `[TRAP]`
1.7.5 **Trap:** a shallow clone in CI makes `git bisect`, `git blame` and
      `git diff origin/main...HEAD` silently wrong or impossible. `fetch-depth: 0` in GitHub Actions
      is the fix, and it costs clone time you must budget. `[TRAP]` `[X-REF 19]`
1.7.6 `git commit` flags in full: `-m`, `-F`, `-a`, `--amend`, `--no-edit`, `--allow-empty`,
      `--allow-empty-message`, `--fixup=<sha>`, `--squash=<sha>`, `--fixup=amend:<sha>`,
      `--fixup=reword:<sha>`, `-S`, `--no-verify`, `--author`, `--date`, `--signoff`,
      `--trailer`, `--cleanup=<mode>`, `-v` (put the diff in the editor). `[CMD]`
1.7.7 `git commit -v` is the highest-value flag nobody enables: it puts the full staged diff in the
      commit-message editor, so you review the change while writing the message. `commit.verbose`.
      `[CFG]`
1.7.8 `--no-verify` skips `pre-commit` and `commit-msg` hooks. It exists for emergencies and is
      abused as a habit; a team that types it daily has hooks that are too slow. `[TRAP]`
1.7.9 `git commit --amend` rewrites the last commit: new tree, new message, **new hash**, same
      parent. It is a rewrite even when you only change the message. `[PROVE]`
1.7.10 **Trap:** `--amend` after pushing requires a force-push. `--amend` on a commit that is a merge
       parent for someone else is the same golden-rule violation as a rebase. `[TRAP]`
1.7.11 Empty commits: `--allow-empty` is legitimate for triggering CI or marking a release point,
       and `git rebase --empty=drop|keep|stop` decides what happens to commits that *become* empty.
       `[CFG]`
1.7.12 `git show <rev>`, `<rev>:<path>`, `--stat`, `--name-only`, `--name-status`, `-m`,
       `--first-parent` for merges. Why `git show <merge>` shows nothing by default and what `-m`,
       `-c` and `--cc` each do. `[TRAP]` `[PROVE]`
1.7.13 `git diff` option surface: `--stat`, `--numstat`, `--shortstat`, `--name-only`,
       `--name-status`, `-w`/`--ignore-all-space`, `--ignore-space-change`,
       `--ignore-blank-lines`, `--word-diff`, `--word-diff-regex`, `--color-words`, `-U<n>`,
       `--function-context`, `--color-moved`, `--color-moved-ws`, `--find-renames`,
       `--find-copies-harder`, `--diff-filter=ACDMRTUXB`, `--patience`, `--histogram`,
       `--anchored`, `--no-index`. `[CMD]`
1.7.14 `--color-moved` is the review superpower: it distinguishes lines that *moved* from lines that
       *changed*, which turns an unreviewable 800-line refactor into a 30-line diff. `diff.colorMoved`.
       `[CFG]`
1.7.15 `git diff --no-index a b` works on files outside any repository — a better `diff(1)`.
1.7.16 `git blame`, `-L`, `-w`, `-M` (detect moved lines within a file), `-C` / `-CC` / `-CCC`
       (detect copies, from the same commit / any commit in the file's history / any commit),
       `--ignore-rev`, `--ignore-revs-file`, `-p` (porcelain), `--since`. `[CMD]`
1.7.17 `.git-blame-ignore-revs` plus `blame.ignoreRevsFile`: the mechanism that stops a whole-repo
       reformat from destroying blame. GitHub honours it too. `[CFG]` `[RESEARCH]`
1.7.18 Git 2.54 added `git blame --diff-algorithm=` (`histogram`, `patience`, `minimal`) — blame
       quality is a function of the diff algorithm. `[RESEARCH]`
1.7.19 `git last-modified` (2.52): the closest ancestor commit that touched each path in a tree.
       Tree-level blame, 5.48x faster than scripting it with `ls-tree` + `log`. `[RESEARCH]`
1.7.20 `git grep` and why it beats `grep -r`: it respects `.gitignore`, searches any revision
       (`git grep <pattern> <rev>`), `-n`, `-l`, `-c`, `-p` (show enclosing function), `-W`,
       `--and`/`--or`/`--not`, `-e`, `--untracked`, `--all-match`, `--threads`. `[CMD]`
1.7.21 `git bugreport` and `git diagnose` — the built-in "collect everything an upstream maintainer
       needs" commands. `[CMD]` `[RESEARCH]`
1.7.22 `git help <cmd>`, `git help -g` (guides), `git <cmd> --help-all` (works outside a repository
       since 2.52), `git help everyday`. `[RESEARCH]`
1.7.23 `git status` in Git 2.54 gains `status.compareBranches` — compare against upstream and/or the
       push remote. `[CFG]` `[RESEARCH]`
1.7.24 The `advice.*` config family: every "hint:" Git prints can be individually silenced, and
       reading the list is a fast way to learn what Git thinks people get wrong. `[CFG]`

*(24 leaves)*

## §1.8 Remotes, refspecs, and the three network verbs

1.8.1 A remote is a name, a URL (fetch), an optional pushurl, and a set of refspecs. Nothing more.
      `.git/config` `[remote "origin"]`.
1.8.2 `git remote add`, `-v`, `show`, `rename` (optimised in 2.52), `remove`, `set-url`,
      `set-url --push`, `set-head`, `prune`, `update`, `get-url --all`. `[CMD]`
1.8.3 The **refspec** grammar: `[+]<src>:<dst>`, the leading `+` meaning "allow non-fast-forward",
      wildcards, and the default fetch refspec
      `+refs/heads/*:refs/remotes/origin/*`. `[SOURCE]` `[PROVE]`
1.8.4 Reading `git push origin HEAD:refs/heads/feature/AO-4821` and
      `git push origin :refs/heads/old-branch` (delete by pushing an empty source) as refspecs.
      `[PROVE]`
1.8.5 Remote-tracking refs are a **local cache** of what the remote looked like at last fetch. They
      are not the remote, and they can be stale in either direction. `[TRAP]`
1.8.6 `git fetch` — downloads objects and updates `refs/remotes/*`. **It touches nothing in your
      working tree or your local branches.** Preserve the current guide's "fetch is always safe"
      framing and prove it. `[PROVE]`
1.8.7 `git fetch --all`, `--prune`, `--prune-tags`, `--tags`, `--no-tags`, `--depth`, `--unshallow`,
      `--force`, `--atomic`, `--jobs`, `--filter`, `--negotiation-tip`, `--refetch`. `[CMD]`
1.8.8 `fetch.prune`, `fetch.pruneTags`, `fetch.parallel`, `fetch.writeCommitGraph`,
      `fetch.negotiationAlgorithm` (`consecutive`, `skipping`, `noop`, `default`). `[CFG]`
1.8.9 The habit worth building: `git fetch && git log --oneline HEAD..origin/main` — see what is
      incoming *before* integrating it. Preserve verbatim from the current guide. `[CMD]`
1.8.10 `git pull` = fetch + integrate. `pull.rebase` (`false`, `true`, `merges`/`preserve`,
       `interactive`), `pull.ff` (`true`, `false`, `only`), `branch.<name>.rebase`. Since 2.27 Git
       *warns* when none of these is set. `[CFG]` `[VERSION-TRAP]`
1.8.11 `git pull --rebase` versus `git pull --rebase=merges`: the latter preserves merge topology in
       your local work instead of flattening it.
1.8.12 `git pull --ff-only` as the safest default: it refuses rather than guessing, and forces you to
       choose the integration explicitly. Arguably the correct global setting. `[CFG]`
1.8.13 `git push`, `-u`/`--set-upstream`, `--all`, `--tags`, `--follow-tags`, `--delete`, `--dry-run`,
       `--atomic`, `--porcelain`, `-o`/`--push-option`, `--signed`, `--no-verify`. `[CMD]`
1.8.14 `push.default` values and their exact semantics: `nothing`, `current`, `upstream`, `tracking`,
       `simple` (the default since 2.0), `matching` (the dangerous pre-2.0 default that pushed every
       matching branch). `[CFG]` `[VERSION-TRAP]`
1.8.15 `push.autoSetupRemote = true` (2.37+) removes the `-u` dance on every new branch. `[CFG]`
       `[RESEARCH]`
1.8.16 Why a push is rejected: the remote ref is not an ancestor of what you are pushing
       (non-fast-forward). The correct fix is to integrate, never to reach for `--force`. Preserve
       the current guide's framing.
1.8.17 `--force` versus `--force-with-lease` versus `--force-if-includes` (2.30+). The lease compares
       against your remote-tracking ref; `--force-if-includes` additionally verifies you have
       actually integrated the remote tip into your history. `[PROVE]` `[RESEARCH]`
1.8.18 **Trap:** a blind `git fetch` immediately before `--force-with-lease` updates the lease and
       silently removes the protection. Preserve the current guide's caveat and extend it with
       `--force-with-lease=<ref>:<expect>` for the explicit form. `[TRAP]`
1.8.19 Git 2.55: remote groups (`remotes.<name>`) now work with `git push`, so
       `git push publish main` fans out to a named set of remotes. `[RESEARCH]`
1.8.20 Git 2.55 fetch negotiation controls: include/restrict which refs participate in negotiation,
       with matching `remote.*` config. Matters on repositories with 100k refs. `[RESEARCH]`
1.8.21 Transport URLs: `https://`, `ssh://` and the `user@host:path` scp-like form, `git://` (no
       auth, no encryption — do not use), `file://` versus a plain path (the former forces the
       object-transfer path, the latter may hardlink). `[TRAP]`
1.8.22 Credential handling: `credential.helper` (`cache`, `store`, `osxkeychain`, `manager`,
       `libsecret`), the credential protocol, `GIT_ASKPASS`, `core.askPass`, and why
       `credential.helper store` writes plaintext to `~/.git-credentials`. `[CFG]` `[TRAP]`
1.8.23 `url.<base>.insteadOf` and `pushInsteadOf` — the rewrite rules that let a whole organisation
       switch HTTPS↔SSH without touching a single `.git/config`. `[CFG]`
1.8.24 `http.extraHeader`, `http.proxy`, `http.version`, `http.postBuffer` (the "RPC failed; curl 55"
       folklore fix and why it is usually the wrong diagnosis), and Git 2.54's HTTP 429 handling:
       `http.retryAfter`, `http.maxRetries`, `http.maxRetryTime` honouring the server's
       `Retry-After` header. `[CFG]` `[TRAP]` `[RESEARCH]`
1.8.25 Git 2.55 sanitises control characters in remote sideband progress messages by default, while
       preserving ANSI colour — a terminal-injection hardening you should be able to name.
       `[RESEARCH]` `[X-REF 13]`
1.8.26 `git ls-remote` — query a remote's refs without cloning. The command to reach for when
       diagnosing "which SHA is the server actually on". `[CMD]`

*(26 leaves)*

## §1.9 Branches in practice

1.9.1 `git branch`, `-a`, `-r`, `-v`, `-vv`, `--merged`, `--no-merged`, `--contains`,
      `--no-contains`, `--points-at`, `-d`, `-D`, `-m`, `-M`, `-c`, `--sort=-committerdate`,
      `--format`. `[CMD]`
1.9.2 `git branch --merged main` as the safe branch-cleanup query, and why `--merged` lies after a
      squash-merge: the squashed commit has different content-identity, so the branch never looks
      merged. `git cherry -v main <branch>` or `git log --cherry-pick` is the correct check.
      `[TRAP]` `[PROVE]`
1.9.3 `git switch` (2.23+, no longer experimental as of 2.51): `-c`, `-C`, `-d`/`--detach`,
      `--orphan`, `-t`/`--track`, `--guess`, `-m`/`--merge`, `-`. `[CMD]` `[RESEARCH]`
1.9.4 `git restore` (2.23+): `--staged`, `--worktree`, `--source=<rev>`, `--patch`, `--ours`,
      `--theirs`, `--merge`, `--overlay`/`--no-overlay`. `[CMD]`
1.9.5 Why `switch`/`restore` exist: `git checkout` was overloaded to switch branches, create
      branches, restore files, detach HEAD and extract from arbitrary commits. Preserve the current
      guide's point and add that `checkout` is explicitly **not** being removed in Git 3.0.
      `[VERSION-TRAP]` `[RESEARCH]`
1.9.6 Upstream tracking: `branch.<name>.remote`, `branch.<name>.merge`, `@{upstream}`/`@{u}`,
      `@{push}` (different when you push to a fork), `git branch -u`, `--unset-upstream`.
      `[CFG]` `[TRAP]`
1.9.7 `git status`'s "ahead 3, behind 5" is computed against `@{upstream}` from your **last fetch**,
      not from the live remote. `[TRAP]` `[PROVE]`
1.9.8 `branch.autoSetupMerge` (`false`, `true`, `always`, `inherit`, `simple`) and
      `branch.autoSetupRebase`. `[CFG]`
1.9.9 Branch naming as a machine-readable convention: `feature/AO-4821-agreement-versioning`,
      `hotfix/FL-9930-stake-double-reserve`, `release/2026.09`. What CI, branch-protection rules and
      changelog tooling parse out of it.
1.9.10 Deleting a branch deletes only the ref. The commits survive until `gc` prunes them, and the
       reflog still names them for 30–90 days. `[PROVE]` `[RECOVER]`
1.9.11 `git branch -d` refuses if unmerged; `-D` does not. What "merged" means precisely here
       (reachable from HEAD or from the upstream), and why it disagrees with your intuition after a
       rebase. `[TRAP]`
1.9.12 Recovering a deleted branch: `git reflog`, `git fsck --lost-found`, and — for a branch you
       only ever saw on the server — the host's ref log or the `refs/pull/*` namespace.
       `[RECOVER]`
1.9.13 `git checkout -` / `git switch -` and `@{-1}`; the two-branch ping-pong every reviewer does.
1.9.14 Long-lived branches as a *cost function*: divergence grows superlinearly with time, so merge
       pain and semantic-conflict risk grow with branch age. State this as the quantitative
       justification for short-lived branches. `[PROVE]`
1.9.15 Branch protection as machinery: required status checks, required reviews, required linear
       history, required signatures, disallow force-push, disallow deletion, restrict who can push,
       required merge queue. Name each and say what invariant it defends. `[X-REF 19]`
1.9.16 `HEAD` on the remote: `origin/HEAD`, `git remote set-head origin -a`, and why
       `git switch main` sometimes guesses wrong after a default-branch rename.
1.9.17 Renaming the default branch on a live repository: the ref rename, the redirect, the open PRs,
       the CI config, everyone's local `origin/master`, and `git remote prune origin`.
       `[RECOVER]`
1.9.18 `init.defaultBranch` and the Git 3.0 change of the built-in default from `master` to `main`
       (warned about since 2.28). `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`

*(18 leaves)*

## §1.10 Tags and releases

1.10.1 Lightweight tag = a ref in `refs/tags/`. Annotated tag = a tag *object* plus a ref. Signed
       tag = an annotated tag with a signature. `[PROVE]`
1.10.2 `git tag`, `-a`, `-m`, `-s`, `-u`, `-d`, `-l`, `--sort=-v:refname`, `--contains`,
       `--points-at`, `--merged`, `-f`, `--format`. `[CMD]`
1.10.3 Why releases should use **annotated** tags: they carry a tagger, a date, a message and an
       optional signature, and `git describe` only considers them by default.
1.10.4 Tags are not pushed by `git push`. `git push --tags` (all tags),
       `git push --follow-tags` (annotated tags reachable from what you are pushing — the correct
       default for release automation), `push.followTags`. `[TRAP]` `[CFG]`
1.10.5 **Trap:** moving a tag (`git tag -f`) is a rewrite. Clients that already fetched it will not
       update without `--force` or `fetch.pruneTags`, so half your fleet builds a different
       artefact from the same tag name. Tags must be immutable in a release process. `[TRAP]`
1.10.6 Deleting a tag locally versus on the remote (`git push origin :refs/tags/v2026.09.1` or
       `git push --delete`), and the fact that consumers keep it.
1.10.7 `git tag --verify`, `git verify-tag`, and signature verification in CI. `[X-REF 13]`
1.10.8 Semantic versioning as a tag convention, `v` prefix or not, prerelease and build metadata, and
       how `--sort=-v:refname` sorts them correctly where lexicographic sort does not. `[TRAP]`
1.10.9 Tag-driven release automation: `git describe --tags --dirty` in the build,
       `semantic-release`/`release-please`, Conventional Commits as the input, and the changelog as
       the output. `[X-REF 12]`
1.10.10 `git archive --format=tar.gz --prefix=funds-ledger-2026.09/ v2026.09.1` and the
        `export-ignore` / `export-subst` attributes that shape what lands in the tarball.
        `[CMD]` `[RESEARCH]`
1.10.11 GitHub/GitLab "Releases" are host constructs layered on tags; the tag is the durable artefact
        and the release notes are not in the repository unless you put them there.
1.10.12 `refs/tags/` is the namespace most likely to collide across forks; tag hygiene in a fork-heavy
        org.

*(12 leaves)*

## §1.11 Ignoring, attributing, and excluding

1.11.1 The four ignore sources in precedence order: command-line pathspec, `.gitignore` in the
       directory (deepest wins), `$GIT_DIR/info/exclude`, and `core.excludesFile`
       (`~/.config/git/ignore` by default). `[SOURCE]` `[CFG]`
1.11.2 Pattern syntax in full: blank lines, `#` comments, trailing-space handling, `!` negation,
       leading `/` anchoring, trailing `/` directory-only, `*`, `?`, `[a-z]`, `**/`, `/**`, `a/**/b`.
       `[SOURCE]`
1.11.3 **Trap:** you cannot re-include a file if its parent directory is excluded. `!` negation is
       powerless below an excluded directory, because Git never descends into it. The fix is
       `dir/**` plus `!dir/keep`. `[TRAP]` `[PROVE]`
1.11.4 **Trap:** `.gitignore` only affects **untracked** files. Once a file is tracked, ignoring it
       changes nothing; you need `git rm --cached`. Preserve verbatim from the current guide.
       `[TRAP]`
1.11.5 `git check-ignore -v <path>` prints the exact file, line number and pattern responsible.
       Preserve from the current guide. `[CMD]`
1.11.6 A worked `.gitignore` for a Java/Spring service — `target/`, `build/`, `*.class`, `.env`,
       `.env.local`, `*.pem`, `*.key`, `.idea/`, `.DS_Store`, `application-local.yml` — preserved
       verbatim from the current guide and extended with `*.jfr`, `hs_err_pid*.log`,
       `replay_pid*.log`, `.gradle/`, `.mvn/wrapper/maven-wrapper.jar`. `[X-REF 06]`
1.11.7 Commit `.env.example` with the *names* and no values. Preserved from the current guide.
1.11.8 `.gitattributes`: the file, its lookup precedence (`$GIT_DIR/info/attributes` >
       directory-local `.gitattributes` > parents > `~/.config/git/attributes` >
       `$(prefix)/etc/gitattributes`), and the four attribute states (Set, Unset, set-to-value,
       Unspecified) plus `!` reset. `[SOURCE]` `[RESEARCH]`
1.11.9 Line endings: `text`, `text=auto`, `eol=lf`, `eol=crlf`, `core.autocrlf`
       (`true`/`input`/`false`), `core.eol`, `core.safecrlf`. The correct 2026 answer is
       `* text=auto` in `.gitattributes` and leave `core.autocrlf` alone. `[TRAP]` `[CFG]`
1.11.10 **Trap:** the whole-repository line-ending flip. Changing `text` settings rewrites every file
        on next checkout, producing a diff touching every line of every file and destroying blame.
        `--renormalize` and a single dedicated commit added to `.git-blame-ignore-revs` are the
        controlled way. `[TRAP]` `[RECOVER]`
1.11.11 `binary` as a built-in macro expanding to `-diff -merge -text`; `delta=false` for
        already-compressed formats; `diff=java` for language-aware hunk headers.
1.11.12 `merge=union` for append-only files (CHANGELOG, `.gitignore`), and why it is dangerous
        anywhere else. `[TRAP]`
1.11.13 `conflict-marker-size` per path, and the case where it matters: files that legitimately
        contain `<<<<<<<` (documentation about Git, template files). `[TRAP]` `[RESEARCH]`
1.11.14 `git check-attr -a -- <path>` and `git check-attr <attr> --all` for debugging. `[CMD]`
1.11.15 `export-ignore` and `export-subst` (with `$Format:%H$` placeholders and the one-`%describe`
        DoS limit) for `git archive`. `[RESEARCH]`
1.11.16 `builtin_objectmode` as a pathspec magic: `:(attr:builtin_objectmode=160000)` to select all
        submodules. `[RESEARCH]`

*(16 leaves)*

## §1.12 Configuration resolution

1.12.1 The precedence chain, last value wins: `$(prefix)/etc/gitconfig` (system) →
       `$XDG_CONFIG_HOME/git/config` → `~/.gitconfig` (global) → `$GIT_DIR/config` (local) →
       `$GIT_DIR/config.worktree` (worktree) → `-c key=value` / `GIT_CONFIG_*` (command).
       `[SOURCE]` `[RESEARCH]`
1.12.2 The five scopes and their flags: `--system`, `--global`, `--local` (default for writes),
       `--worktree`, and `command`. `[CMD]`
1.12.3 **`git config --list --show-origin --show-scope`** is the debugging command. When a setting
       "doesn't work", this tells you which of six files won. `[CMD]` `[RECOVER]`
1.12.4 Multi-valued keys: `--add`, `--get-all`, `--get-regexp`, `--replace-all`, `--unset`,
       `--unset-all`. Some keys (`remote.*.fetch`, `include.path`, `safe.directory`) are lists, and
       `git config key value` silently replaces only the first. `[TRAP]`
1.12.5 The file syntax: sections, subsections (case-sensitive, quoted), variable names
       (case-insensitive), booleans (`true/yes/on/1`, `false/no/off/0`, valueless = true), integers
       with `k`/`m`/`g` suffixes (powers of 1024), and `\` line continuation. `[SOURCE]`
1.12.6 `--type=bool|int|bool-or-int|path|expiry-date|color`, and the legacy `--bool`/`--int` forms.
       `[RESEARCH]`
1.12.7 `include.path` — unconditional include, absolute, relative to the including file, or `~/`.
       `[RESEARCH]`
1.12.8 `includeIf` conditions in full: `gitdir:`, `gitdir/i:` (case-insensitive), `onbranch:`,
       and `hasconfig:remote.*.url:`. Glob rules — `**/` prepended when no prefix, trailing `/`
       implies `**`. `[SOURCE]` `[RESEARCH]`
1.12.9 The canonical `includeIf` use case: `~/work/**` gets your corporate `user.email` and signing
       key, `~/personal/**` gets your own. Committing with the wrong email is the most common
       identity mistake and this eliminates it. `[TRAP]`
1.12.10 **Protected configuration**: only `system`, `global` and `command` scopes may set
        security-sensitive options. A repository's own `.git/config` cannot escalate. This is why a
        cloned repo cannot silently set `core.fsmonitor` to a malicious binary. `[PROVE]`
        `[RESEARCH]` `[X-REF 13]`
1.12.11 `safe.directory` and the CVE-2022-24765 background: Git refuses to operate on a repository
        owned by another user. The correct fixes and the incorrect `safe.directory=*`. Git 3.0 also
        flips `safe.bareRepository` from `all` to `explicit`. `[TRAP]` `[RESEARCH]` `[X-REF 13]`
1.12.12 `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>` — passing config through
        an environment without a file. The CI-friendly form. `[CMD]`
1.12.13 `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` — pointing Git at a different (or `/dev/null`)
        config, essential for reproducible tests. `[CMD]`
1.12.14 The environment-variable surface worth knowing: `GIT_DIR`, `GIT_WORK_TREE`,
        `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
        `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_AUTHOR_*`, `GIT_COMMITTER_*`, `GIT_EDITOR`,
        `GIT_SEQUENCE_EDITOR`, `GIT_SSH_COMMAND`, `GIT_TERMINAL_PROMPT`, `GIT_TRACE`,
        `GIT_TRACE2`, `GIT_TRACE_PACKET`, `GIT_CURL_VERBOSE`. `[SOURCE]`
1.12.15 `GIT_SEQUENCE_EDITOR` is the one that makes interactive rebase scriptable:
        `GIT_SEQUENCE_EDITOR="sed -i 's/^pick/reword/'" git rebase -i HEAD~5`. `[CMD]`
1.12.16 Aliases: `[alias]` section, shell aliases with a leading `!`, argument handling (`$1`,
        `"$@"`, and the trailing-argument gotcha), and Git 2.54's subsection alias syntax
        `[alias "hämta"] command = fetch` for non-ASCII names. `[TRAP]` `[RESEARCH]`
1.12.17 A defended alias set for this guide's reader: `st`, `lg`, `co`, `sw`, `ap` (`add -p`),
        `fixup`, `ri`, `pf` (`push --force-with-lease`), `undo` (`reset --soft HEAD~1`),
        `wip`, `unwip`, `cleanup`, `recent`. Each with the reason it earns a slot. `[CMD]`
1.12.18 The config keys every backend engineer should set once, with values and justification:
        `pull.ff=only`, `push.default=simple`, `push.autoSetupRemote=true`,
        `rebase.autosquash=true`, `rebase.autostash=true`, `rebase.updateRefs=true`,
        `rerere.enabled=true`, `merge.conflictstyle=zdiff3`, `diff.algorithm=histogram`,
        `diff.colorMoved=zebra`, `fetch.prune=true`, `commit.verbose=true`, `core.fsmonitor=true`,
        `column.ui=auto`, `help.autocorrect=prompt`, `init.defaultBranch=main`,
        `transfer.fsckObjects=true`. `[CFG]`

*(18 leaves)*

## §1.13 Merging: the model

1.13.1 A merge produces one commit with **two or more parents** whose tree is the three-way merge of
       the two tips against their merge base. Nothing is rewritten. `[PROVE]`
1.13.2 Fast-forward: when the merge base *is* the current tip, Git can simply move the ref. No
       commit is created and no merge information is recorded. `[PROVE]`
1.13.3 `--ff` (default), `--no-ff` (always create a merge commit), `--ff-only` (refuse if not a
       fast-forward), `merge.ff`. The `--no-ff` argument: it records that a feature existed as a
       unit, which makes `git log --first-parent` a list of features. `[CFG]`
1.13.4 `--squash`: apply the merged tree's changes to the index without recording a merge or moving
       parents. `git merge --squash` does **not** create a commit — a detail that surprises people.
       `[TRAP]`
1.13.5 `git merge` option surface: `-m`, `--no-commit`, `--no-edit`, `--edit`, `--log`, `--squash`,
       `-s`, `-X`, `--abort`, `--continue`, `--quit`, `--allow-unrelated-histories`,
       `--autostash`, `--verify-signatures`. `[CMD]`
1.13.6 `--allow-unrelated-histories` exists because since 2.9 Git refuses to merge two roots by
       default — the safety net that catches "I cloned into the wrong directory". `[VERSION-TRAP]`
1.13.7 The merge state on disk: `MERGE_HEAD`, `MERGE_MSG`, `MERGE_MODE`, `AUTO_MERGE`, and the
       unmerged index entries. `git merge --abort` is `git reset --merge ORIG_HEAD` with extra care.
       `[PROVE]`
1.13.8 Octopus merges: >2 parents, used by kernel maintainers and almost nobody else. `octopus` is
       the default strategy when merging more than one branch, and it **refuses** any merge needing
       manual resolution. `[RESEARCH]`
1.13.9 The `ours` strategy (not `-X ours`): result tree is always the current branch's, discarding
       the other side entirely while still recording it as merged. Used to declare a branch
       superseded. `[TRAP]`
1.13.10 `-X ours` / `-X theirs` resolve *conflicting hunks* one way while still taking non-conflicting
        changes from both sides. **This is a completely different thing from the `ours` strategy**
        and confusing them is a classic. `[TRAP]` `[PROVE]`
1.13.11 `subtree` strategy and `-Xsubtree=<path>` for merging a project into a subdirectory.
1.13.12 What a merge *cannot* detect: a **semantic conflict**. Both sides merge cleanly, the code
        compiles, and it is wrong — one side renames `reserveStake` and the other adds a caller.
        Only tests catch this, which is the argument for merge queues (§2.19). `[PROVE]` `[TRAP]`
1.13.13 `git merge --no-commit --no-ff` as a "try the merge, look at it, decide" move.
1.13.14 Merge commit messages: the default `Merge branch 'x' into y`, `merge.log`, `--log=<n>` to
        include the merged commits' subjects, and why a merge commit deserves a real message when it
        represents a release integration.
1.13.15 `git merge-tree` (2.38+ rewritten form): compute a merge **without touching the working tree
        or index**, returning the resulting tree OID and the conflict list. This is how a host
        computes "can this PR merge cleanly" server-side. `[CMD]` `[RESEARCH]`
1.13.16 `git merge-file` — the three-way file merge as a standalone tool, with `--ours`/`--theirs`/
        `--union`, `--diff3`, `--marker-size`. `[CMD]`

*(16 leaves)*

## §1.14 Rebasing: the model

1.14.1 Rebase = for each commit in a range, compute its diff, apply it onto a new base, and create a
       **new commit with a new hash**. The originals become unreachable and survive only via reflog.
       `[PROVE]`
1.14.2 The three arguments: `git rebase [--onto <newbase>] [<upstream>] [<branch>]`, and reading
       `git rebase --onto main feature/base feature/child` as "move the child's own commits onto
       main". `[PROVE]`
1.14.3 The commit set is `upstream..branch`, minus commits whose patch-id already exists upstream —
       which is why a rebase after a cherry-pick silently drops commits.
       `--reapply-cherry-picks`/`--no-reapply-cherry-picks`. `[TRAP]` `[PROVE]`
1.14.4 `--keep-base` = "rebase onto the same merge base", i.e. clean up my commits without pulling in
       upstream changes. Equivalent to `--reapply-cherry-picks --no-fork-point --onto <upstream>...`.
       `[RESEARCH]`
1.14.5 `--fork-point` (default when no `--onto`): uses the reflog of the upstream to find a better
       base after the upstream itself was rewritten. The subtle reason two people get different
       rebase results. `[TRAP]` `[RESEARCH]`
1.14.6 `--root` to rebase from the first commit, including rewriting the root.
1.14.7 The state machine: `--continue`, `--skip`, `--abort`, `--quit`, `--edit-todo`,
       `--show-current-patch`. `--abort` restores; `--quit` leaves you where you are. `[TRAP]`
1.14.8 `--autostash` / `rebase.autostash`: stash, rebase, unstash. Removes the "cannot rebase: you
       have unstaged changes" friction entirely. `[CFG]`
1.14.9 `--exec <cmd>` / `-x`: run a command after every commit — `git rebase -x './mvnw -q test'
       origin/main` verifies every commit in the series is green, which is what makes a
       bisectable history real rather than aspirational. `[CMD]` `[PROVE]`
1.14.10 `--reschedule-failed-exec` and `rebase.rescheduleFailedExec`. `[CFG]`
1.14.11 `--update-refs` / `rebase.updateRefs`: force-update every branch pointing at a commit being
        rebased. **This is the stacked-PR primitive** — one rebase fixes the whole stack.
        `[CFG]` `[RESEARCH]`
1.14.12 `--rebase-merges[=rebase-cousins|no-rebase-cousins]` (`-r`): recreate merge commits instead
        of flattening them, using `label`/`reset`/`merge` todo commands. Replaces the removed
        `--preserve-merges`. `[VERSION-TRAP]` `[RESEARCH]`
1.14.13 `--committer-date-is-author-date`, `--ignore-date`/`--reset-author-date`, `--signoff`, and
        Git 2.54's `--trailer` (append a trailer to every rebased commit via
        `interpret-trailers`). `[RESEARCH]`
1.14.14 The two backends: `--apply` (old, uses `git am`, faster on simple cases, loses empty commits
        and does not support all options) versus `--merge` (default since 2.26, uses the sequencer
        and `ort`, supports `-X`, `rerere`, `--exec`). `rebase.backend`. `[CFG]` `[VERSION-TRAP]`
1.14.15 **The golden rule, stated exactly:** never rebase commits that others have based work on.
        Preserve the current guide's wording and its explanation of *why* (everyone's clone
        disagrees with the remote about what the commits are). `[TRAP]` `[PROVE]`
1.14.16 The standard workflow: rebase your feature onto `main` to stay current; merge or squash-merge
        into `main` at the end. Preserve verbatim from the current guide.
1.14.17 Conflicts during rebase are potentially resolved **once per commit**, not once — which is the
        real cost difference against merge, and the reason `rerere` exists. `[PROVE]`
1.14.18 `git rebase` versus `git replay` (2.45+, extended in 2.54 with atomic ref updates,
        `--revert`, dropping empty commits, and replay-to-root): a bare-repository-safe, headless,
        server-side history rewriter. Name it — it is how hosts will implement rebase-merge.
        `[RESEARCH]`

*(18 leaves)*

## §1.15 The undo surface

1.15.1 The decision table, preserved verbatim from the current guide and extended: `revert`,
       `reset --soft`, `reset --mixed`, `reset --hard`, `restore <file>`, `restore --staged`,
       `checkout <sha> -- <file>`, `clean -fd` — each with "what it does", "history", and "safe on
       pushed commits?". `[TRAP]`
1.15.2 `git revert <sha>` creates a **new** commit whose diff is the inverse. The only undo that is
       safe on shared history, and the only one that leaves an audit trail. `[PROVE]`
1.15.3 `git revert` options: `-n`/`--no-commit`, `-e`, `--no-edit`, `-m <parent>`, `-s`,
       `--continue`/`--skip`/`--abort`/`--quit`, and reverting a range `A..B`.
1.15.4 **Reverting a merge** needs `-m 1` to name the mainline parent. Preserve the current guide's
       example and its sequel: re-merging that branch later will **not** reintroduce the changes,
       because the merge base already includes them. You must revert the revert. `[TRAP]` `[PROVE]`
1.15.5 The five reset modes, not three: `--soft`, `--mixed` (default), `--hard`, `--merge`,
       `--keep`. `--merge` and `--keep` preserve local modifications and refuse rather than
       destroy, and almost nobody knows they exist. `[SOURCE]` `[TRAP]`
1.15.6 Reset as "move HEAD, then optionally the index, then optionally the working tree" — a
       three-stage model that makes all five modes fall out of one picture. `[PROVE]`
1.15.7 `git reset <paths>` (no mode) is a completely different operation: it copies from a commit
       into the index for those paths and never moves HEAD. Same command name, different verb.
       `[TRAP]`
1.15.8 `git reset --soft HEAD~3` to squash the last three commits into a re-do. Preserve from the
       current guide.
1.15.9 **Trap:** `git reset --hard` discards uncommitted work irrecoverably. The reflog recovers
       *commits*, never working-directory state. `git stash` first. Preserve verbatim. `[TRAP]`
1.15.10 **Trap:** `git clean -fd` deletes untracked files, including `.env`, local scratch scripts,
        and (with `-x`) everything gitignored, with **no recovery path at all** — not even
        `fsck`. Always `git clean -nd` first. Preserve verbatim and add `-X` (ignored only) and
        `-i` (interactive). `[TRAP]`
1.15.11 `git restore --staged --worktree <path>` as the "make this file exactly like HEAD" command,
        and `git restore --source=main~3 -- <path>` for pulling one file from another revision.
1.15.12 `git checkout <sha> -- <path>` still works and is what older documentation says; the modern
        spelling is `git restore --source=<sha> -- <path>`.
1.15.13 `ORIG_HEAD` is written before every destructive operation (`reset`, `merge`, `rebase`,
        `pull`), so `git reset --hard ORIG_HEAD` is the immediate one-step undo. `[RECOVER]`
1.15.14 The decision rule, preserved from the current guide: pushed → `revert`, always; local only →
        `reset` is fine; redo the last few commits → `reset --soft HEAD~n`; unstage →
        `restore --staged`; throw away working changes → `restore` (unrecoverable).
1.15.15 Reverting a revert: `git revert <revert-sha>` — legitimate, common after a rollback, and
        worth a clear commit message saying why. `[RECOVER]`
1.15.16 `git revert` on a squash-merged PR is one commit; on a merge-commit PR it is `-m 1`; on a
        rebase-merged PR it is a range. **This is the practical argument for squash-merge.**
        `[PROVE]`
1.15.17 Rolling back a bad deploy: revert the commit *and* redeploy, versus redeploying the previous
        artefact. Which one you choose depends on whether the artefact is immutable and whether the
        database migration is reversible. `[X-REF 20]`
1.15.18 `git rm --cached -r <dir>` to untrack without deleting; the follow-up `.gitignore` entry and
        the fact that everyone else's next pull **deletes their local copy**. `[TRAP]`
1.15.19 `git commit --amend --no-edit` versus `git commit --fixup` — the former destroys the previous
        version, the latter keeps a reviewable record until you squash. On a PR under review,
        `--fixup` is the courteous choice. `[PROVE]`
1.15.20 Undoing a `git add` of a huge file *before* commit versus after: `restore --staged` versus a
        history rewrite. The cost cliff between the two is why `add -p` matters. `[PROVE]`
1.15.21 `git checkout --ours` / `--theirs` during a conflict take one whole side of the *file*, not
        the hunk. Fine for lock files, dangerous for hand-written code. Preserve from the current
        guide.
1.15.22 `git switch --discard-changes` and `git checkout -f` — the two spellings of "throw away and
        switch".

*(22 leaves)*

## §1.16 The reflog

1.16.1 Mechanism: every ref update appends a line to `$GIT_DIR/logs/<ref>` recording
       `<old-oid> <new-oid> <identity> <timestamp> <tz>\t<action>: <message>`. `HEAD` has its own
       log at `.git/logs/HEAD`. `[HEX]` `[SOURCE]`
1.16.2 `HEAD@{n}` indexes by *position in the reflog*, `HEAD@{2.hours.ago}` by time,
       `main@{1}` for a branch's own log. These are not the same as `HEAD~n`. `[TRAP]` `[PROVE]`
1.16.3 `git reflog`, `git reflog show <ref>`, `--date=iso`, `git reflog expire`,
       `git reflog delete`, `git log -g --oneline`. `[CMD]`
1.16.4 Expiry defaults: `gc.reflogExpire = 90 days` for entries reachable from the ref,
       `gc.reflogExpireUnreachable = 30 days` for entries that are not. Both are configurable per
       ref pattern (`gc.<pattern>.reflogExpire`). `[NUM]` `[CFG]` `[RESEARCH]`
1.16.5 What the reflog recovers: a bad `reset --hard`, a botched rebase, a deleted branch, a bad
       amend, a bad force-push (locally), a wrong `checkout`. Preserve the current guide's list.
       `[RECOVER]`
1.16.6 What it cannot recover: anything never committed. Uncommitted working-tree edits and files
       removed by `git clean`. Preserve verbatim. `[TRAP]`
1.16.7 Recovery recipes: `git reset --hard HEAD@{1}`, `git branch recovered <oid>`,
       `git cherry-pick <oid>`, `git stash` on the recovered state. Preserve from the current guide.
       `[RECOVER]`
1.16.8 **The habit this implies: commit early and often on your own branch.** Once something is
       committed it is nearly impossible to lose; ugly WIP commits are squashed later. Preserve the
       current guide's emphasis — it is the single highest-value Git habit. `[PROVE]`
1.16.9 `git fsck --lost-found`, `--unreachable`, `--dangling`, `--no-reflogs`, and the
       `.git/lost-found/commit/` and `/other/` output directories. Finds dangling commits the reflog
       missed — e.g. from an aborted rebase in another worktree. Preserve from the current guide.
       `[RECOVER]`
1.16.10 A bare repository has **no reflog by default** (`core.logAllRefUpdates` defaults to true only
        when there is a working tree). This is why "the server force-pushed and we lost it" is a
        real risk and why hosts implement their own ref audit log. `[TRAP]` `[CFG]` `[PROVE]`
1.16.11 GitHub keeps unreachable commits accessible for ~90 days and exposes the events API and, on
        Enterprise, an audit log — the server-side reflog substitute. `[RESEARCH]`
1.16.12 `git reflog` on a *remote-tracking* ref (`origin/main@{1}`) tells you what the remote looked
        like at your previous fetch — the forensic tool for "someone force-pushed main".
        `[RECOVER]`
1.16.13 Reflog under the reftable backend: stored in log blocks in the same table stack, with
        `update_index` reversed so recent entries sort first. 34x smaller on Android's repository.
        `[NUM]` `[RESEARCH]`
1.16.14 The `reflog-expire` maintenance task (2.54+), `maintenance.reflog-expire.auto` (default 100).
        `[CFG]` `[RESEARCH]`

*(14 leaves)*

## §1.17 Stash

1.17.1 A stash entry is a real **commit** — in fact two or three: a commit of the index state, a
       commit of the working-tree state with the index commit as second parent, and optionally a
       third for untracked files. `refs/stash` plus its reflog is the stack. `[PROVE]` `[HEX]`
1.17.2 `git stash push -m`, `-u`/`--include-untracked`, `-a`/`--all`, `-p`/`--patch`,
       `-S`/`--staged`, `-k`/`--keep-index`, `--pathspec-from-file`, `--`, `<pathspec>`. `[CMD]`
1.17.3 `git stash list`, `show`, `show -p`, `apply`, `pop`, `branch <name>`, `drop`, `clear`,
       `create`, `store`. `[CMD]`
1.17.4 `--keep-index` is the "test what I am about to commit" move: stash everything, leave the index
       intact, run the tests. `[PROVE]`
1.17.5 `git stash branch <name>` when a stash no longer applies cleanly: it recreates the original
       branch point and applies there. The correct recovery for an old stash. `[RECOVER]`
1.17.6 `git stash export --to-ref refs/stashes/<name>` and `git stash import` (2.51): stashes are now
       transferable between machines. `[RESEARCH]` `[VERSION-TRAP]`
1.17.7 **Trap:** `git stash pop` on a conflict applies *and leaves the entry in the stash*, so people
       drop it twice or lose it. `apply` + explicit `drop` is the safer habit. `[TRAP]`
1.17.8 **Trap:** plain `git stash` does not include untracked files, so a brand-new file survives the
       stash, gets carried to the other branch, and gets committed there by accident. `-u` is
       usually what you want. Preserve from the current guide. `[TRAP]`
1.17.9 **Trap:** `git stash` does not stash `.gitignore`d files without `-a`, and `-a` will happily
       stash your `target/` directory.
1.17.10 A dropped stash is recoverable: `git fsck --unreachable | grep commit` then
        `git stash store` or `git branch`. It is a commit, so it is in the object database.
        `[RECOVER]` `[PROVE]`
1.17.11 Why a named WIP commit on a branch beats a stash: it is named, pushable, visible in the
        reflog and survives a `clean`. Preserve the current guide's recommendation.
1.17.12 Stash and `rerere`/conflicts: an apply that conflicts leaves you in a conflicted index with
        no `MERGE_HEAD`, which confuses tooling. `[TRAP]`
1.17.13 `git worktree add` as the alternative to stashing entirely: you do not need to switch
        branches if you have two working trees. §2.9.
1.17.14 Stash hygiene: an unlabelled stash from three weeks ago is unidentifiable. Preserve from the
        current guide, and add `git stash list --date=relative --pretty` for triage.

*(14 leaves)*

## §1.18 Cherry-pick

1.18.1 Mechanism: take the diff of `<commit>` against **its own parent**, apply it to HEAD, create a
       new commit with a new hash and (by default) the original author and message. `[PROVE]`
1.18.2 Options: `-x` (append `(cherry picked from commit <sha>)`), `-e`, `-n`/`--no-commit`, `-s`,
       `-m <parent>` (for a merge commit), `--ff`, `--allow-empty`, `--keep-redundant-commits`,
       `--strategy`, `-X`, `--continue`/`--skip`/`--abort`/`--quit`, ranges `A..B` and `A^..B`.
       `[CMD]`
1.18.3 `-x` is mandatory for backports: it is the only durable link between the release-branch commit
       and the `main` commit. Preserve from the current guide. `[TRAP]`
1.18.4 The range gotcha: `git cherry-pick A..B` **excludes A**. `A^..B` includes it. `[TRAP]`
1.18.5 Cherry-picking a merge commit requires `-m` to say which parent's diff to take, and the result
       is usually not what you want. Prefer picking the individual commits. `[TRAP]`
1.18.6 Legitimate use: backporting a hotfix from `main` to `release/2026.09`. Preserve from the
       current guide.
1.18.7 **Illegitimate use:** cherry-pick as a substitute for merging. Repeated picks create duplicate
       commits with different hashes; a later merge between the branches conflicts against changes
       that are logically already there. Preserve verbatim from the current guide. `[TRAP]` `[PROVE]`
1.18.8 `git cherry <upstream> <head>` and `git log --cherry-mark`: patch-id-based detection of "this
       change is already there in a different commit". The tool that makes the above survivable.
       `[PROVE]`
1.18.9 `git patch-id` and how equivalence is computed (whitespace-normalised diff hash, ignoring
       context line numbers). `--stable` versus `--unstable`. `[PROVE]` `[RESEARCH]`
1.18.10 The backport workflow end to end for `hotfix/FL-9930`: fix on `main`, verify, cherry-pick
        `-x` to `release/2026.09`, run the release branch's tests, tag, deploy, and record the
        mapping in the ticket. `[RECOVER]`
1.18.11 `git format-patch` / `git am` as the email-based cousin: `-M`, `-C`, `--cover-letter`,
        `-v2`, `--base`, and `git am --3way`, `--abort`, `--show-current-patch`. Still how the Git
        and Linux projects work, and the origin of the `--apply` rebase backend. `[CMD]`
1.18.12 `git range-diff <base>..<v1> <base>..<v2>` — diff two versions of a patch series. The correct
        tool for "what changed between force-pushes of this PR", and what GitHub's
        "force-pushed, compare" link approximates. `[CMD]` `[PROVE]`

*(12 leaves)*

## §1.19 A guided tour of `.git/`

1.19.1 `HEAD` — the symbolic ref or raw OID. `[HEX]`
1.19.2 `config` — the local scope. `description` — used only by GitWeb.
1.19.3 `index` — the binary staging area (§3.4).
1.19.4 `objects/` — `xx/` two-hex-digit fan-out directories of loose objects, `pack/` with
       `*.pack`/`*.idx`/`*.rev`/`*.mtimes`/`*.bitmap`, `info/packs`, `info/alternates`,
       `info/commit-graph`, `info/commit-graphs/`. `[HEX]`
1.19.5 The `xx/` fan-out exists because early filesystems degrade with >10k entries per directory;
       256 buckets keeps loose-object directories small. `[PROVE]`
1.19.6 `objects/info/alternates` — borrow objects from another repository. The mechanism behind
       `clone --reference`, CI cache reuse and host-side fork storage, and the reason a `gc` in the
       donor can corrupt the borrower. `[TRAP]`
1.19.7 `refs/heads/`, `refs/tags/`, `refs/remotes/`, and `packed-refs` at the top level.
1.19.8 `logs/HEAD` and `logs/refs/**` — the reflogs.
1.19.9 `hooks/` with `*.sample` files; `core.hooksPath` to relocate them.
1.19.10 `info/exclude`, `info/attributes`, `info/refs` (dumb HTTP), `info/grafts` (deprecated,
        removed in Git 3.0). `[RESEARCH]`
1.19.11 `shallow` — the grafted-parent boundary of a shallow clone.
1.19.12 `MERGE_HEAD`, `MERGE_MSG`, `MERGE_MODE`, `AUTO_MERGE`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`,
        `BISECT_*`, `REBASE_HEAD` — the operation-in-progress markers.
1.19.13 `rebase-merge/` (sequencer backend) with `git-rebase-todo`, `done`, `onto`, `head-name`,
        `interactive`; `rebase-apply/` (am backend) with `patch`, `next`, `last`. Reading these is
        how you understand "where am I in this rebase". `[HEX]`
1.19.14 `sequencer/` — the todo for `cherry-pick`/`revert` ranges.
1.19.15 `rr-cache/` — rerere's store (§3.11).
1.19.16 `worktrees/<name>/` with `gitdir`, `commondir`, `HEAD`, `index`, `locked`, `config.worktree`
        (§2.9).
1.19.17 `modules/<name>/` — the real git dirs of submodules (§2.10).
1.19.18 `lfs/` — Git LFS's local object cache (§2.12).
1.19.19 `FETCH_HEAD`, `ORIG_HEAD`, `COMMIT_EDITMSG`, `TAG_EDITMSG`, `gc.log`, `index.lock`,
        `*.lock` files generally.
1.19.20 The `.git` **file** (not directory) form: `gitdir: <path>`, used by submodules, worktrees and
        `--separate-git-dir`. `[HEX]`
1.19.21 `git rev-parse --git-dir`, `--git-common-dir`, `--git-path <name>`, `--show-toplevel`,
        `--show-superproject-working-tree` — resolving all of the above portably. `[CMD]`
1.19.22 An exercise the bible must include: build a repository from three commits and walk `.git/`
        with `find`, `xxd`, `git cat-file` and `git ls-files -s` until every file is accounted for.
        `[HEX]` `[BUILD]`

*(22 leaves)*

## §1.20 Plumbing versus porcelain

1.20.1 The distinction restated: plumbing has a stable, scriptable interface; porcelain is
       human-facing and may change output format between releases. Scripts that parse porcelain
       break. `[TRAP]`
1.20.2 The object-level plumbing inventory: `hash-object`, `cat-file`, `mktree`, `commit-tree`,
       `mktag`, `write-tree`, `read-tree`, `unpack-file`. `[CMD]`
1.20.3 The ref-level inventory: `update-ref`, `symbolic-ref`, `show-ref`, `for-each-ref`,
       `pack-refs`, `rev-parse`, `name-rev`, `describe`. `[CMD]`
1.20.4 The index-level inventory: `update-index`, `ls-files`, `checkout-index`, `diff-index`,
       `diff-files`, `diff-tree`, `ls-tree`. `[CMD]`
1.20.5 The graph-level inventory: `rev-list`, `merge-base`, `cherry`, `patch-id`, `show-branch`,
       `commit-graph`, `last-modified`. `[CMD]`
1.20.6 The pack-level inventory: `pack-objects`, `unpack-objects`, `index-pack`, `verify-pack`,
       `repack`, `prune`, `prune-packed`, `count-objects`, `multi-pack-index`. `[CMD]`
1.20.7 The transport inventory: `upload-pack`, `receive-pack`, `send-pack`, `fetch-pack`,
       `ls-remote`, `http-backend`. `[CMD]`
1.20.8 The three diff plumbing commands and what each compares: `diff-files` (working tree vs index),
       `diff-index` (index/tree vs tree), `diff-tree` (tree vs tree). Every porcelain diff is one of
       these. `[PROVE]`
1.20.9 `git ls-tree -r -l --name-only <rev>` and `git ls-tree -d` for directory-only.
1.20.10 `git cat-file --batch-check --batch-all-objects` as the "inventory the entire object
        database" one-liner, and the pipeline that finds your ten largest blobs. `[CMD]`
1.20.11 `git verify-pack -v <idx> | sort -k3 -n | tail` — the classic "what is making this repository
        huge" recipe, and its modern replacement `git repo structure`. `[CMD]` `[RESEARCH]`
1.20.12 `git count-objects -vH` fields read one by one: `count`, `size`, `in-pack`, `packs`,
        `size-pack`, `prune-packable`, `garbage`, `size-garbage`. `[NUM]`
1.20.13 `git fast-export` / `git fast-import` and the stream format — the substrate `filter-repo` and
        every importer is built on. 2.53 added `--signed-commits=strip-if-invalid`. `[RESEARCH]`
1.20.14 `git bundle create/verify/list-heads/unbundle` — a repository as a single file, for air-gapped
        transfer or a CI cache seed. `[CMD]`
1.20.15 `git notes` — attach metadata to a commit without changing its hash. `refs/notes/commits`,
        `notes.rewriteRef`, `--ref`, and why review systems and CI use it. Also why nobody pushes
        them (they are not in the default refspec). `[TRAP]`
1.20.16 `git replace` — a graft that *is* an object, `refs/replace/<oid>`, `--graft`, `--edit`,
        `GIT_NO_REPLACE_OBJECTS`, and the "shallow-but-with-a-full-history-available" trick.
        Supersedes `info/grafts`, which Git 3.0 removes. `[RESEARCH]`
1.20.17 `git repo info` / `git repo structure` (2.52, experimental; 2.53 adds inflated size and disk
        size per object type with human-friendly units) — the built-in repository health report.
        `[RESEARCH]`
1.20.18 `git format-rev --stdin-mode=text --format=<fmt>` (2.55, experimental) — format revisions
        read from stdin, including OIDs embedded in prose. `[RESEARCH]`

*(18 leaves)*

## §1.21 Versions, release cadence, and Git 3.0

1.21.1 Git ships roughly quarterly. The version you are answering about matters, and stating it is a
       seniority signal.
1.21.2 The releases this file spans, with dates: 2.50 (Jun 2025), 2.51 (18 Aug 2025), 2.52
       (Nov 2025), 2.53 (Feb 2026), 2.54 (20 Apr 2026), 2.55 (29 Jun 2026). `[NUM]` `[RESEARCH]`
1.21.3 `git help BreakingChanges` — the documented, versioned deprecation plan. Knowing this document
       exists is itself a differentiator. `[SOURCE]` `[RESEARCH]`
1.21.4 Git 3.0 default changes: hash `sha1`→`sha256`, ref format `files`→`reftable`, default branch
       `master`→`main`, `safe.bareRepository` `all`→`explicit`, Rust mandatory. `[RESEARCH]`
1.21.5 Git 3.0 removals: `git-pack-redundant`, `git-whatchanged` (both already gated behind
       `--i-still-use-this`), `info/grafts`, `$GIT_COMMON_DIR/branches/` and `remotes/`,
       `name-rev --stdin`, `core.commentString=auto`, `core.preferSymlinkRefs=true`. `[RESEARCH]`
1.21.6 `git checkout` is explicitly **not** being removed, despite `switch`/`restore`. `[RESEARCH]`
1.21.7 The `WITH_BREAKING_CHANGES` build flag lets you test against 3.0 semantics today; the release
       before 3.0 will be an LTS with 4 cycles of bug fixes and 6 of security fixes. `[RESEARCH]`
1.21.8 The Rust timeline: auto-detect in 2.52, default-on in 2.55 (opt out with `NO_RUST` /
       `-Drust=disabled`), mandatory in 3.0. What this means for anyone building Git in a CI image.
       `[RESEARCH]` `[X-REF 19]`
1.21.9 Meson as the second build system alongside the Makefile, and why it appears in modern build
       instructions.
1.21.10 Feature-availability table the bible must include: which Git version introduced
        `switch`/`restore` (2.23), sparse-checkout cone (2.25), `--merge` rebase backend default
        (2.26), `pull` warning (2.27), `init.defaultBranch` (2.28), SHA-256 (2.29),
        `--force-if-includes` (2.30), sparse index (2.32–2.34), `ort` default (2.34), SSH signing
        (2.34), `git maintenance` (2.30), `merge-tree --write-tree` (2.38), `--update-refs` (2.38),
        cruft packs (2.37), `zdiff3` (2.35), bundle URIs (2.38), `git replay` (2.44/2.45), reftable
        (2.45 experimental / 2.51 stable), `git history` (2.54), config hooks (2.54), geometric
        maintenance (2.54), parallel hooks (2.55). `[NUM]` `[RESEARCH]`
1.21.11 Why you must know the *minimum* Git version in your estate: CI images, Debian stable, RHEL,
        macOS's Apple Git (chronically old), and Windows Git-for-Windows. A workflow that depends
        on 2.54 config hooks fails silently on 2.39. `[TRAP]`
1.21.12 `git version --build-options` and reading it. `[CMD]`
1.21.13 Git's own security history worth naming: CVE-2022-24765 (`safe.directory`),
        CVE-2024-32002 (submodule symlink RCE on case-insensitive filesystems), CVE-2024-32004
        (local clone RCE), CVE-2025-* credential-helper leaks. Keeping Git patched is a supply-chain
        control. `[RESEARCH]` `[X-REF 13]`
1.21.14 The libraries that reimplement Git and where they lag: libgit2, JGit, go-git, Dulwich,
        gitoxide. Relevant when your tool "supports Git" but not reftable, partial clone or
        SHA-256. `[TRAP]`
1.21.15 Alternative frontends worth naming in 2026: Jujutsu (`jj`), Sapling, git-branchless,
        GitButler. Each keeps Git's object model and replaces the UI. `[RESEARCH]`
1.21.16 How to read a Git release note: the "Backward Compatibility Notes", "Updates since",
        "Performance, Internal Implementation" and "Fixes since" sections, and what each is for.

*(16 leaves)*

---

# PART 2 — INTERMEDIATE

## §2.1 The master cost and behaviour tables

2.1.1 **Master operation table** — one row per operation, columns: what it reads, what it writes,
      complexity in terms of (objects touched, refs touched, files in worktree), whether it touches
      the network, whether it rewrites history, whether it can lose uncommitted work, and the
      recovery path. Operations: `status`, `add`, `commit`, `commit --amend`, `diff`, `log`,
      `blame`, `branch`, `switch`, `merge (ff)`, `merge (3-way)`, `rebase`, `rebase -i`,
      `cherry-pick`, `revert`, `reset --soft/--mixed/--hard`, `restore`, `clean`, `stash`,
      `fetch`, `pull`, `push`, `push --force`, `clone`, `gc`, `repack`, `bisect`, `filter-repo`.
      `[NUM]`
2.1.2 **Complexity notes the table must justify**, not just assert: `status` is O(files in worktree)
      without fsmonitor and O(changed files) with it; `log` is O(commits walked) and O(1) per commit
      with a commit-graph; `blame` is O(commits touching the file × file size); `merge-base` is
      O(commits) without generation numbers and near-O(1) with them; checkout is O(files differing).
      `[PROVE]`
2.1.3 **Destructiveness table**: for each command, what is destroyed, whether reflog recovers it,
      whether `fsck` recovers it, and whether nothing recovers it. The last column has exactly three
      entries — `clean`, `reset --hard` on uncommitted work, and `checkout`/`restore` over
      uncommitted work — and that is the fact to memorise. `[NUM]` `[PROVE]`
2.1.4 **Safety table**: for each command, safe on a private branch / safe on a shared branch / safe
      on `main`. Three columns, no ambiguity.
2.1.5 **Storage table**: bytes added by a commit that changes one line in one file (new blob after
      zlib, new tree per changed directory, one commit object, one reflog line, one ref write) —
      with the arithmetic shown for a real 40-byte change. `[NUM]` `[PROVE]`
2.1.6 **Network table**: what `clone`, `fetch`, `pull`, `push`, `ls-remote`, `fetch --depth=1` and a
      partial clone each transfer, in objects and in bytes, for the QuizStakes `funds-ledger`
      repository. `[NUM]`
2.1.7 **Config default table**: every config key named in this guide with its default value and the
      version that introduced or changed it. `[CFG]` `[NUM]`
2.1.8 **Which-command-for-which-question table**: "who changed this line" → `blame`; "when did this
      string disappear" → `log -S`; "which commit broke it" → `bisect`; "what does my branch add" →
      `diff main...HEAD`; "is this commit in the release" → `git branch --contains` /
      `git tag --contains`; "what changed between two versions of this PR" → `range-diff`; "which
      commit last touched each file in this directory" → `last-modified`.

*(8 leaves)*

## §2.2 Merge versus rebase, decided rather than debated

2.2.1 The ASCII diagram of both outcomes, preserved verbatim from the current guide, and extended
      with the third option (squash) and the fourth (rebase-then-merge --no-ff).
2.2.2 The comparison table, preserved and extended: history shape, hash stability, conflict count,
      safety on shared branches, `bisect`/`log` legibility, revertability, and what CI actually
      tested. `[NUM]`
2.2.3 The property that decides it in practice: **a merge preserves the fact that the two lines of
      work were concurrent; a rebase asserts that they were sequential.** If that assertion is false
      and matters, merge. `[PROVE]`
2.2.4 Why rebase can produce a series where **no intermediate commit was ever tested**, and
      `rebase -x` as the only honest fix. `[PROVE]` `[TRAP]`
2.2.5 Why merge can produce a history where `git log` is unreadable and `git bisect` lands on merge
      commits — and `--first-parent` bisect (`git bisect start --first-parent`) as the answer.
      `[RESEARCH]`
2.2.6 The conflict-count asymmetry proved: merging resolves the combined difference once; rebasing
      resolves per commit, worst case n times for n commits. With `rerere` the marginal cost of the
      repeats collapses. `[PROVE]`
2.2.7 The team-level decision framework: what does `main` look like, how do you revert, how do you
      bisect, what does the PR review show, and what does the release changelog come from. Four
      questions, and the answer set determines merge policy.
2.2.8 The house style this guide recommends and defends: **rebase your feature onto `main` while it
      is in flight; squash-merge it in.** With the exception list — long release integrations use
      `--no-ff` merges; stacked PRs use merge commits because squash breaks stack identity.
2.2.9 `git pull --rebase` as the daily-integration form, and `git config --global pull.rebase true`
      versus `pull.ff=only`. Preserve from the current guide, and argue for `ff-only` as the
      safer default. `[CFG]`
2.2.10 What "linear history" is actually worth: `git log` readability, `git bisect` without merge
       commits, easy `revert`, and reflog-free reasoning. What it costs: force-pushes, lost
       concurrency information, and CI results attached to commits that no longer exist. `[PROVE]`
2.2.11 The GitHub/GitLab merge-button options mapped onto the above: "Create a merge commit"
       (`--no-ff`), "Squash and merge", "Rebase and merge" (which is `cherry-pick`, not `rebase
       --onto`, and produces commits with a new committer). `[TRAP]` `[RESEARCH]`
2.2.12 **Trap:** "Rebase and merge" on GitHub rewrites your commits' committer and hash, so the
       branch you pushed and the commits on `main` are different objects. Your local branch will
       appear unmerged. `[TRAP]`

*(12 leaves)*

## §2.3 Merge strategies and strategy options

2.3.1 The strategy inventory with exact names: `ort` (default), `recursive` (a synonym for `ort`
      since 2.50), `resolve`, `octopus` (default for >2 heads), `ours`, `subtree`. `[SOURCE]`
      `[RESEARCH]`
2.3.2 `ort` = "Ostensibly Recursive's Twin". Written by Elijah Newren, default since 2.34. It is a
      full rewrite, not a tweak: it works on in-memory trees rather than the index and working tree,
      which is what makes it fast and what makes `merge-tree` possible. `[RESEARCH]`
2.3.3 `resolve` handles exactly two heads, detects criss-cross ambiguity carefully, and does **not**
      handle renames. It exists as a fallback when `ort` produces a surprising result. `[RESEARCH]`
2.3.4 `octopus` refuses any merge requiring manual resolution — which is the whole point: it is for
      combining N already-compatible topic branches. `[RESEARCH]`
2.3.5 The `-X` strategy-option inventory, every one by exact name: `ours`, `theirs`,
      `ignore-space-change`, `ignore-all-space`, `ignore-space-at-eol`, `ignore-cr-at-eol`,
      `renormalize`, `no-renormalize`, `find-renames[=<n>]`, `rename-threshold=<n>` (deprecated
      synonym), `no-renames`, `diff-algorithm=(histogram|minimal|myers|patience)`, `histogram`
      (deprecated synonym), `patience` (deprecated synonym), `subtree[=<path>]`. `[SOURCE]`
      `[RESEARCH]`
2.3.6 **`ort` defaults to the `histogram` diff algorithm** for merges, unlike `git diff` which
      defaults to `myers`. Merge quality and diff quality are therefore not the same computation.
      `[TRAP]` `[RESEARCH]`
2.3.7 `-X renormalize` and `merge.renormalize`: virtual check-out/check-in of all three stages, the
      cure for a merge that conflicts on every line because the two branches disagree about line
      endings or a clean filter. `[CFG]` `[RESEARCH]`
2.3.8 `-X ignore-all-space` for merging across a reformat — and why it is a last resort that can
      silently drop a whitespace-significant change (Python, YAML, Markdown, heredocs). `[TRAP]`
2.3.9 `-X find-renames=<n>` and `merge.renames` (`true`, `false`, `copies`); `merge.renameLimit` and
      `diff.renameLimit` (the rename-detection matrix size cap, above which Git silently gives up
      and you get add/delete pairs instead of renames). `[CFG]` `[TRAP]` `[NUM]`
2.3.10 `merge.directoryRenames` (`false`, `conflict`, `true`) — the ort feature that puts a new file
       added to `src/main/java/ledger/` on one side into `src/main/java/funds/` when the other side
       renamed the directory. A genuinely hard problem, solved heuristically. `[CFG]` `[RESEARCH]`
2.3.11 `merge.verbosity`, `merge.stat`, `merge.autoStash`, `merge.tool`, `merge.guitool`,
       `mergetool.<tool>.cmd`, `mergetool.keepBackup`, `mergetool.prompt`. `[CFG]`
2.3.12 Custom merge drivers in `.gitattributes` + `.git/config`: `driver = <cmd> %O %A %B %L %P`,
       with `%S`/`%X`/`%Y` conflict labels, exit-0 for success, exit >128 for crash, and
       `merge.<driver>.recursive` for the internal merges of a recursive strategy. `[SOURCE]`
       `[RESEARCH]`
2.3.13 The three built-in file-level drivers: `text` (conflict markers), `binary` (take ours, mark
       conflicted), `union` (concatenate both sides, no markers). `[RESEARCH]`
2.3.14 A worked custom driver for the QuizStakes repo: a `merge=lockfile` driver that regenerates
       `pom.xml`'s dependency lock rather than merging it textually. `[BUILD]`
2.3.15 Strategy selection in `git pull`, `git rebase -s`, `git cherry-pick -s`, and
       `git revert -s` — the same machinery everywhere.
2.3.16 `git merge-tree --write-tree --name-only <b1> <b2>` for a headless merge in CI: get the tree
       OID and the conflict list without a working tree, which is how you pre-flight a merge queue.
       `[CMD]` `[RESEARCH]`

*(16 leaves)*

## §2.4 Conflict resolution as a procedure

2.4.1 A conflict occurs when the same region of the same file changed on both sides relative to the
      base, or when one side edited a file the other deleted, or renamed it differently, or a
      directory/file collision. Enumerate all conflict *kinds*, not just content conflicts.
      `[PROVE]`
2.4.2 The full conflict taxonomy with the exact `git status` wording for each: both modified,
      both added, added by us, added by them, deleted by us, deleted by them, both deleted,
      rename/rename, rename/delete, modify/delete, directory/file, submodule conflict, symlink
      conflict, binary conflict. `[SOURCE]` `[NUM]`
2.4.3 The conflict-marker anatomy, preserved verbatim from the current guide, with the QuizStakes
      re-domain: `<<<<<<< HEAD`, `=======`, `>>>>>>> feature/FL-9930-stake-timeout`. `[HEX]`
2.4.4 `merge.conflictStyle` values: `merge` (default, two-way markers), `diff3` (adds the
      `|||||||` base section), **`zdiff3`** (2.35+, diff3 with the common trailing/leading lines
      hoisted out of the conflict). `zdiff3` is the correct 2026 setting and almost nobody has it
      on. `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
2.4.5 Why the base section matters: without it you cannot tell whether "theirs" *added* a line or
      "ours" *deleted* it. Two opposite intents produce an identical two-way marker. `[PROVE]`
      `[TRAP]`
2.4.6 **Trap:** "ours" and "theirs" **swap meaning during a rebase**, because your commits are being
      replayed onto the other branch. In a merge, ours = your branch; in a rebase, ours = upstream
      and theirs = your work. Preserve verbatim from the current guide, add the `git rebase --merge`
      documentation's own wording confirming it, and add the same swap in `cherry-pick` and
      `revert`. `[TRAP]` `[SOURCE]` `[RESEARCH]`
2.4.7 The resolution procedure, preserved verbatim from the current guide: `git status` →
      `git diff` → understand **both** intents → edit → `git add` → **run the tests** →
      `git commit` / `git rebase --continue`; `--abort` always available. `[CMD]`
2.4.8 `git diff` during a conflict shows a **combined diff** against both parents, which is why it
      looks strange. `git diff --ours`, `--theirs`, `--base`, and `git diff --diff-filter=U`.
      `[PROVE]` `[CMD]`
2.4.9 `git log --merge -p <path>` — the commits on either side that touched the conflicted path.
      The single most useful conflict-investigation command and it is in nobody's muscle memory.
      `[CMD]`
2.4.10 `git checkout --conflict=diff3 <path>` to re-materialise the conflict with a different style
       after you have already mangled it. `[RECOVER]`
2.4.11 `git show :1:<path>`, `:2:<path>`, `:3:<path>` — extract the base, ours and theirs versions
       from the index by stage number. The escape hatch when the markers are unreadable.
       `[CMD]` `[PROVE]`
2.4.12 `AUTO_MERGE` (2.38+): the tree ort produced, so `git diff AUTO_MERGE` shows exactly what you
       have changed relative to the machine's attempt. `[RESEARCH]`
2.4.13 `git mergetool`, `--tool=`, the tool inventory (`vimdiff`, `nvimdiff`, `meld`, `kdiff3`,
       `bc`, `p4merge`, `vscode`, `intellij`), and `mergetool.keepBackup=false` to stop `.orig`
       files accumulating. `[CFG]`
2.4.14 IntelliJ's three-pane merge and VS Code's inline resolver as the tools this reader actually
       has; what each labels "ours"/"theirs"/"result" and how to verify the labelling before
       trusting it. `[TRAP]`
2.4.15 Binary conflicts: there is no merge. `git checkout --ours/--theirs`, then regenerate. For
       generated artefacts the correct fix is to stop committing them. `[TRAP]`
2.4.16 Lock-file conflicts (`package-lock.json`, `pom.xml` versions, `gradle.lockfile`): resolve by
       regenerating, never by hand-editing. A `merge=lockfile` driver (§2.3.14) automates it.
2.4.17 Conflict *prevention* beats resolution — preserve the current guide's list (small PRs,
       short-lived branches, frequent rebase onto `main`, committed formatter config plus a
       pre-commit hook) and quantify it: a formatter removes ~all whitespace conflicts, and branch
       age is the dominant term in conflict probability. `[PROVE]`
2.4.18 Team-level conflict reduction: module ownership, avoiding god files, splitting long files,
       codegen out of the repo, and an agreed import-ordering rule enforced in CI. `[X-REF 16]`
2.4.19 The "resolve by picking the side that compiles" antipattern, and why it is how self-exclusion
       logic silently reverts. Tie it to QuizStakes Invariant 8. `[TRAP]`
2.4.20 After any non-trivial resolution: run the tests, then `git diff HEAD~1` (merge) or
       `git range-diff` (rebase) and read the whole thing. A resolution is a change and deserves
       review. `[PROVE]`

*(20 leaves)*

## §2.5 rerere

2.5.1 "Reuse Recorded Resolution": record the conflicted state and your resolution, then replay it
      the next time the identical conflict appears. `rerere.enabled=true`. Preserve from the current
      guide. `[CFG]`
2.5.2 What "identical" means: a **conflict ID** hashed from the normalised conflicted automerge
      content, not from the file path or the branch names. The same conflict in a different file
      matches. `[PROVE]` `[RESEARCH]`
2.5.3 The three files per conflict ID in `.git/rr-cache/<id>/`: `preimage` (the conflicted state),
      `postimage` (your resolution), `thisimage` (the current conflicted state). `[HEX]`
      `[RESEARCH]`
2.5.4 The replay is a **three-way merge** between the earlier conflicted automerge, the earlier
      resolution, and the current conflicted automerge — not a blind copy. That is why it works when
      the surrounding code has moved. `[PROVE]` `[RESEARCH]`
2.5.5 Subcommands: `git rerere status`, `remaining`, `diff`, `forget <pathspec>`, `clear`, `gc`.
      `[CMD]` `[RESEARCH]`
2.5.6 `rerere.autoUpdate` (default `false`) stages the replayed resolution automatically. Turning it
      on is convenient and is exactly how a wrong recorded resolution gets committed without you
      seeing it. `[CFG]` `[TRAP]`
2.5.7 Expiry: `gc.rerereResolved = 60 days`, `gc.rerereUnresolved = 15 days`. `[NUM]` `[CFG]`
      `[RESEARCH]`
2.5.8 `git rerere clear` is invoked automatically by `git am --abort` and `git rebase --abort`.
      `[RESEARCH]`
2.5.9 **Trap:** rerere records a *wrong* resolution just as happily as a right one, and then replays
      it silently forever. `git rerere forget <path>` is the fix, and it must be run **while the
      conflict is present**. `[TRAP]` `[RECOVER]`
2.5.10 **Trap:** rerere keys on conflict-marker detection. A file that legitimately contains
       `<<<<<<<` breaks it; `conflict-marker-size` in `.gitattributes` is the workaround.
       `[TRAP]` `[RESEARCH]`
2.5.11 The workflow rerere was built for: a long-lived branch rebased repeatedly onto a moving
       `main`, where the same conflict recurs on every rebase and on every commit within it.
       Preserve the current guide's framing. `[PROVE]`
2.5.12 The "test merge" trick from the documentation: merge, resolve, record, `reset --hard HEAD^`,
       continue working, and let the real merge replay it later. `[RESEARCH]`
2.5.13 rerere and `git rebase -i`: the resolution is replayed per commit, which is what turns an
       n-commit rebase from n resolutions into one. `[PROVE]`
2.5.14 Sharing rr-cache across a team: technically possible (copy the directory), practically a bad
       idea, because one person's wrong resolution becomes everyone's. Say so explicitly. `[TRAP]`

*(14 leaves)*

## §2.6 Interactive rebase, autosquash, and the new `git history`

2.6.1 `git rebase -i HEAD~5`, `git rebase -i main`, `git rebase -i --root`. Preserve the current
      guide's examples.
2.6.2 The todo-list command inventory, every one: `pick`/`p`, `reword`/`r`, `edit`/`e`,
      `squash`/`s`, `fixup`/`f`, `fixup -c`, `fixup -C`, `exec`/`x`, `break`/`b`, `drop`/`d`,
      `label`/`l`, `reset`/`t`, `merge`/`m` (with `-C`/`-c`), `update-ref`. Preserve the current
      guide's five and add the rest. `[SOURCE]` `[RESEARCH]`
2.6.3 Reordering lines reorders commits; deleting a line drops it (and Git warns via
      `rebase.missingCommitsCheck` = `ignore`/`warn`/`error`). `[CFG]` `[TRAP]`
2.6.4 `edit` stops *after* applying the commit, so you amend; `break` stops *before* the next one,
      so you can inspect. Different tools for different jobs. `[PROVE]`
2.6.5 `squash` concatenates messages and opens the editor; `fixup` discards the message silently;
      `fixup -C` uses the fixup's message instead. `[NUM]`
2.6.6 `git commit --fixup=<sha>` and `git commit --squash=<sha>` write the magic
      `fixup! <subject>` / `squash! <subject>` prefixes; `git rebase -i --autosquash` reorders and
      marks them automatically. `rebase.autosquash=true` makes it the default. Preserve from the
      current guide and complete it. `[CFG]`
2.6.7 `--fixup=amend:<sha>` (amend the content *and* let you edit the message) and
      `--fixup=reword:<sha>` (message only, no content) — 2.32+. Almost unknown, exactly what you
      want when addressing review feedback. `[RESEARCH]`
2.6.8 The review workflow this enables: push `fixup!` commits so the reviewer sees only the delta,
      then `rebase -i --autosquash` immediately before merge. Ties directly to §2.17's "push fixes
      as separate commits".
2.6.9 `--exec`/`x` in the todo list to run tests after every commit, and `--reschedule-failed-exec`.
2.6.10 `--update-refs` inside an interactive rebase inserts `update-ref refs/heads/<branch>` lines
       automatically for every branch in the stack. `[RESEARCH]`
2.6.11 Splitting a commit: `edit` it, `git reset HEAD^`, then `git add -p` and commit twice. The
       canonical recipe. `[CMD]`
2.6.12 Splitting a commit in 2.54+: `git history split <commit>` does it with a hunk-selection UI
       and no manual reset dance. Experimental; does not support merges or conflicting operations.
       `[RESEARCH]` `[VERSION-TRAP]`
2.6.13 `git history reword <commit>` (2.54) — change an old commit's message in place without
       touching the working tree, and without an interactive rebase. `[RESEARCH]`
2.6.14 `git history fixup <commit>` (2.55) — apply currently-staged changes to an earlier commit and
       replay the descendants. Still experimental and requires a working tree. `[RESEARCH]`
2.6.15 The golden rule applies unchanged: interactive rebase only on unshared commits. Preserve from
       the current guide, including the nuance that it matters less when the team squash-merges but
       still makes review substantially easier. `[TRAP]`
2.6.16 Cleaning up eight WIP commits into two coherent ones before opening the PR — the worked
       example, on `feature/AO-4821-agreement-versioning`, showing the before todo list, the after
       todo list, and the resulting `git log --oneline`.
2.6.17 Recovering from a rebase you have already messed up: `git rebase --abort`, or if you already
       finished, `git reset --hard ORIG_HEAD`, or `git reflog` + `git reset --hard HEAD@{n}`.
       `[RECOVER]`
2.6.18 `git rebase --edit-todo` mid-rebase, and `.git/rebase-merge/git-rebase-todo` as the file you
       can just read. `[RECOVER]`
2.6.19 Scripting a rebase with `GIT_SEQUENCE_EDITOR` for bulk operations across 200 commits.
       `[BUILD]`

*(19 leaves)*

## §2.7 History rewriting at scale

2.7.1 What "rewriting history" means precisely: producing a new commit graph whose commits have
      different OIDs, then repointing refs at it. Every downstream clone now disagrees. `[PROVE]`
2.7.2 The three tools and their status: `git filter-branch` (**officially discouraged** — extremely
      slow, riddled with silent-corruption gotchas, and warns on use), **`git filter-repo`** (the
      recommended tool, a separate Python program built on `fast-export`/`fast-import`), and BFG
      Repo-Cleaner (older, JVM-based, still serviceable, narrower feature set). Preserve the current
      guide's recommendation. `[VERSION-TRAP]` `[RESEARCH]`
2.7.3 Why `filter-branch` is orders of magnitude slower: it forks a shell per commit per filter.
      `[PROVE]` `[RESEARCH]`
2.7.4 `git filter-repo` option surface: `--path`, `--path-glob`, `--path-regex`, `--invert-paths`,
      `--path-rename`, `--subdirectory-filter`, `--to-subdirectory-filter`, `--replace-text`,
      `--replace-refs`, `--mailmap`, `--strip-blobs-bigger-than`, `--strip-blobs-with-ids`,
      `--commit-callback`, `--blob-callback`, `--filename-callback`, `--message-callback`,
      `--refs`, `--force`, `--partial`, `--analyze`, `--dry-run`. `[CMD]` `[RESEARCH]`
2.7.5 `git filter-repo --analyze` writes a `.git/filter-repo/analysis/` report — biggest blobs,
      biggest directories, path renames, extension breakdown. **Run this first, always.**
      `[CMD]` `[RESEARCH]`
2.7.6 The `commit-map` and `ref-map` files: the old-OID → new-OID mapping, which is how you fix up
      external references (tickets, deploy manifests, CI history) after a rewrite. `[RESEARCH]`
2.7.7 `filter-repo` **removes the `origin` remote** on purpose, so you cannot accidentally push a
      rewrite over a live repository. Also why it insists on a fresh clone. `[TRAP]` `[RESEARCH]`
2.7.8 The named rewrite recipes the bible must ship, each complete: remove a file from all history;
      remove all blobs over 10 MB; redact a secret value; split a directory out into its own
      repository preserving history; merge two repositories preserving both histories; rewrite
      author emails via `--mailmap`; strip a vendored directory. `[CMD]` `[BUILD]`
2.7.9 `.mailmap` as the **non-rewriting** alternative for identity cleanup: it changes what `log`,
      `shortlog` and `blame` display without touching a single object. Reach for it before
      `filter-repo`. `[TRAP]` `[PROVE]`
2.7.10 The coordination protocol for a rewrite of a shared repository, as a checklist: announce,
       freeze pushes, close or note open PRs, rewrite on a fresh mirror clone, verify with `fsck`
       and a diff of the final tree, force-push all refs, have everyone **re-clone** (not pull),
       delete and re-create forks, invalidate CI caches, update anything that pinned a SHA.
       `[RECOVER]`
2.7.11 **Trap:** everyone `pull`ing instead of re-cloning is how a rewritten repository gets the old
       history pushed back into it an hour later. The old objects are still in their clones and
       still reachable from their local branches. `[TRAP]` `[PROVE]`
2.7.12 What a rewrite does **not** remove: objects already fetched by others, host-side caches,
       forks, `refs/pull/*` on GitHub, CI artefact stores, and the GitHub API's ability to serve a
       dangling commit by SHA. Preserve the current guide's point and expand it. `[TRAP]`
2.7.13 After a rewrite, the old objects are still local: `git reflog expire --expire=now --all &&
       git gc --prune=now --aggressive` is the local cleanup, and asking the host to run GC is the
       remote one. `[CMD]` `[RECOVER]`
2.7.14 Cost model: a rewrite of a 10-year, 200k-commit repository takes minutes with `filter-repo`
       and hours with `filter-branch`, and costs every engineer a re-clone. Budget both. `[NUM]`
2.7.15 `git replace --graft` as the **non-destructive** alternative for grafting a truncated history
       onto a full one, and `git filter-repo` consuming `refs/replace/*` to make it permanent.
       `[RESEARCH]`
2.7.16 Rewriting on the server side without a working tree: `git replay --onto <base> <range>`
       (2.44+), atomic ref updates and `--revert` since 2.54. `[RESEARCH]`

*(16 leaves)*

## §2.8 Bisect

2.8.1 The premise: a monotone predicate over a linear-ish history — it worked at `v2026.06`, it is
      broken at `HEAD`, and the transition happens exactly once. Binary search finds it in
      ⌈log2(N)⌉ tests. Preserve the current guide's 400-commits-in-~9-tests framing. `[PROVE]`
      `[NUM]`
2.8.2 The command sequence, preserved from the current guide: `git bisect start`, `bad`, `good <ref>`,
      test, `good`/`bad`, repeat, `git bisect reset`. `[CMD]`
2.8.3 The one-line start form: `git bisect start <bad> <good>`. `[CMD]`
2.8.4 `git bisect run <script>` — the exit-code contract: **0 = good, 1–124 and 126–127 = bad,
      125 = skip (untestable), 128+ = abort**. Preserve the current guide's 0/1/125 and complete the
      range. `[NUM]` `[SOURCE]` `[TRAP]`
2.8.5 `git bisect skip`, `git bisect skip <range>`, and what Git does when the skipped set makes the
      answer ambiguous (it reports "the first bad commit could be any of").
2.8.6 `git bisect terms --term-old=<x> --term-new=<y>` — bisecting a *fix* rather than a break
      (`old`/`new` instead of `good`/`bad`). The case everyone forgets exists. `[RESEARCH]`
2.8.7 `git bisect start -- <pathspec>` to restrict to commits touching a path, which shrinks N.
2.8.8 `git bisect start --first-parent` — bisect only the mainline, landing on the *merge* that
      introduced the regression rather than an intermediate commit inside a feature branch. Exactly
      right for a merge-heavy repository. `[RESEARCH]`
2.8.9 `git bisect log` and `git bisect replay <file>` — resume a bisect, or hand it to a colleague.
      `[CMD]` `[RECOVER]`
2.8.10 `git bisect visualize` / `view` to see the remaining candidate set.
2.8.11 `git bisect run` requirements, preserved and extended: a deterministic, fast reproduction;
       every commit must build (hence `skip` and hence `main` being green); the script must be
       *outside* the tree or restored each iteration, because bisect checks out old code over it.
       `[TRAP]`
2.8.12 **Trap:** your bisect script is in the repository and disappears when Git checks out a commit
       from before it existed. Keep it in `/tmp`, or use `git bisect run bash -c '...'`, or
       `git stash` it into place. This bites everyone once. `[TRAP]`
2.8.13 **Trap:** stale build artefacts. A bisect over Java code without `mvn clean` (or with a stale
       `target/`) gives false results. Either clean every iteration (slow) or prove your build is
       correctly incremental. `[TRAP]`
2.8.14 Bisecting a **performance** regression: the script asserts a threshold, with enough
       repetitions to beat noise and a JMH-style warmup. `[X-REF 06]` `[BUILD]`
2.8.15 Bisecting a **flaky** failure: run the test k times per commit and treat "failed at least
       once" as bad; compute how large k must be for a 1-in-20 flake to be detected with 95%
       confidence. `[PROVE]` `[NUM]`
2.8.16 Bisecting **data**, not code: the same binary search applied to inputs — which field, which
       tenant, which record — is the same algorithm and the bible must say so explicitly.
2.8.17 A complete `[BUILD]` bisect script for QuizStakes: reproduce the `FL-9930` double stake
       reservation, exit 125 if the module fails to compile, 1 if the reservation duplicates, 0
       otherwise, with a timeout so a hung commit does not stall the run. `[BUILD]`
2.8.18 Squash-merge makes bisect land on a whole feature; merge-commit history makes it land inside
       one. Preserve the current guide's point that squash-merging keeps every commit on `main`
       buildable. `[PROVE]`
2.8.19 What to do once bisect names the commit: read it, do not assume. The named commit may have
       *exposed* a latent bug rather than introduced it. `[TRAP]`

*(19 leaves)*

## §2.9 Worktrees

2.9.1 A linked worktree is a second checkout sharing one object database and one ref store. Not a
      clone: no duplicated objects, no second remote, refs are shared. `[PROVE]`
2.9.2 `git worktree add <path> [<branch>]`, `-b`, `-B`, `-d`/`--detach`, `--orphan`, `--track`,
      `--lock`, `--no-checkout`, `-f`. `[CMD]` `[RESEARCH]`
2.9.3 Subcommands: `list` (`--porcelain`, `-v`, `--expire`), `lock --reason`, `move`, `remove`,
      `prune` (`-n`, `--expire`), `repair`, `unlock`. `[CMD]` `[RESEARCH]`
2.9.4 The on-disk layout: the worktree's `.git` is a **file** containing
      `gitdir: /repo/.git/worktrees/<name>`, and that directory holds `gitdir`, `commondir`, `HEAD`,
      `index`, and `locked`. `[HEX]` `[RESEARCH]`
2.9.5 `$GIT_DIR` versus `$GIT_COMMON_DIR`: per-worktree state versus shared state. Which files live
      where, and why `git rev-parse --git-common-dir` exists. `[PROVE]` `[RESEARCH]`
2.9.6 Shared versus per-worktree refs: everything under `refs/` is shared **except**
      `refs/bisect/*`, `refs/worktree/*` and `refs/rewritten/*`. Access other worktrees' HEADs via
      `main-worktree/HEAD` and `worktrees/<name>/HEAD`. `[RESEARCH]`
2.9.7 The "branch already checked out" restriction, why it exists (two worktrees advancing one ref
      would corrupt each other's index expectations), and `--detach` or `-f` to override.
      `[PROVE]` `[TRAP]` `[RESEARCH]`
2.9.8 `extensions.worktreeConfig` and `config.worktree`, read after `.git/config`. Recommended
      per-worktree keys: `core.worktree`, `core.bare`, `core.sparseCheckout`. Incompatible with
      older Git. `[CFG]` `[RESEARCH]`
2.9.9 `gc.worktreePruneExpire` default **3.months.ago**, and the `worktree-prune` maintenance task.
      `[NUM]` `[CFG]` `[RESEARCH]`
2.9.10 `git worktree repair` after you move the main repository or a worktree by hand. `[RECOVER]`
2.9.11 The use cases that beat stashing: review a colleague's PR while your build runs; keep a
       long-running `release/2026.09` checkout for hotfixes; run a bisect in a scratch worktree
       without disturbing your feature branch; build two versions side by side for a perf
       comparison.
2.9.12 Worktrees and IDEs: IntelliJ/VS Code index each worktree separately, which is the point
       (no reindex on branch switch) and also the cost (n× disk and n× indexing CPU). `[NUM]`
2.9.13 **Trap:** deleting a worktree directory with `rm -rf` leaves stale administrative files;
       `git worktree remove` or `git worktree prune` is the correct cleanup. `[TRAP]`
2.9.14 Worktrees plus submodules: `git worktree move` refuses when submodules are present, and
       submodule checkouts are not automatically shared. `[TRAP]`

*(14 leaves)*

## §2.10 Submodules, subtrees, and the monorepo question

2.10.1 A submodule is a **gitlink**: a tree entry with mode `160000` whose OID is a *commit* in
       another repository. The superproject pins an exact commit, nothing more. `[PROVE]` `[NUM]`
2.10.2 `.gitmodules` (committed: `submodule.<name>.path`, `.url`, `.branch`, `.update`,
       `.shallow`, `.ignore`, `.fetchRecurseSubmodules`) versus `.git/config` (local, written by
       `git submodule init`). Two files, two lifetimes, and the source of most confusion.
       `[TRAP]` `[RESEARCH]`
2.10.3 `.git/modules/<name>/` holds the submodule's real git dir; the submodule's working directory
       has a `.git` *file* pointing there. `git submodule absorbgitdirs` migrates old layouts.
       `[RESEARCH]`
2.10.4 Subcommands: `add`, `status`, `init`, `deinit`, `update`, `set-branch`, `set-url`, `summary`,
       `foreach`, `sync`, `absorbgitdirs`. `[CMD]` `[RESEARCH]`
2.10.5 `git submodule update` modes: `checkout` (default, detached HEAD at the pinned commit),
       `rebase`, `merge`, `none`, and `!<command>`. `--init`, `--recursive`, `--remote`, `--depth`,
       `--single-branch`, `--jobs`, `--filter`, `--no-fetch`. `[RESEARCH]`
2.10.6 `git clone --recurse-submodules`, `submodule.recurse=true`, `--recurse-submodules` on
       `fetch`/`pull`/`push`/`checkout`/`switch`/`grep`, and `push --recurse-submodules=check|on-demand`.
       `[CFG]`
2.10.7 The status prefixes in `git submodule status`: `-` uninitialised, `+` checked-out commit ≠
       recorded commit, `U` conflicts, blank = clean. `[SOURCE]` `[RESEARCH]`
2.10.8 The pain points, each with the symptom: detached HEAD by default so commits inside a
       submodule are easy to lose; a superproject commit that pins a submodule commit nobody pushed;
       `git pull` not updating submodules; a submodule conflict that shows as two OIDs with no
       useful diff; relative URLs (`../repo.git`) breaking under SSH↔HTTPS switches; shallow
       submodules that cannot reach the pinned commit; CI that clones without `--recursive`.
       `[TRAP]` `[RESEARCH]`
2.10.9 `submodule.<name>.ignore` (`none`, `untracked`, `dirty`, `all`) and `diff.ignoreSubmodules` —
       stopping submodules from polluting `git status`. `[CFG]`
2.10.10 CVE-2024-32002: a submodule with a symlinked `.git` on a case-insensitive filesystem could
        run hooks from the clone. Why `--recurse-submodules` on an untrusted repository is a
        code-execution risk. `[RESEARCH]` `[X-REF 13]`
2.10.11 `git subtree add/pull/push/merge/split`, `--prefix`, `--squash`. The alternative that
        vendors the other project's *content* into your tree, so cloners need nothing extra.
        `[CMD]`
2.10.12 Submodule versus subtree versus package registry versus monorepo — a four-way table on:
        clone complexity, contributor friction, atomic cross-repo change, dependency pinning,
        CI cost, and who can break whom. This is the actual interview question. `[NUM]`
2.10.13 The honest recommendation: use a package registry (Maven/Artifactory) for library
        dependencies, a monorepo for code that changes together, and submodules only for
        genuinely-external pinned sources. Subtree when consumers must not need extra commands.
2.10.14 Monorepo consequences the bible must state: one CI graph and therefore build-affected-targets
        tooling (Bazel, Gradle build cache, Nx); one `CODEOWNERS`; one dependency version; huge
        `git status` cost; merge-queue contention at the trunk; and the sparse-checkout/partial-clone
        toolkit in §2.11. `[X-REF 19]`
2.10.15 Polyrepo consequences: version skew, cross-repo atomic changes are impossible, "which
        version of `router-int` is `funds-ledger` running against" becomes a real question, and
        release coordination becomes a project.
2.10.16 The QuizStakes shape: 25 services. Say explicitly what this guide would recommend and why —
        service-per-repo with a shared `platform-contracts` repo consumed as a versioned artefact,
        not a submodule. `[X-REF 12]`

*(16 leaves)*

## §2.11 Scaling: sparse-checkout, partial clone, sparse index, Scalar

2.11.1 The three independent axes of "the repository is too big": too much **history** (deep),
       too many **files** (wide), too much **content** (large blobs). Each has a different fix and
       conflating them is the classic mistake. `[PROVE]` `[TRAP]`
2.11.2 History → shallow clone (`--depth`, `--shallow-since`) or partial clone with
       `--filter=tree:0`. Files → sparse-checkout. Content → partial clone `--filter=blob:none` /
       `blob:limit=<n>`, or LFS. `[NUM]`
2.11.3 **Partial clone**: `git clone --filter=blob:none`, `--filter=blob:limit=1m`,
       `--filter=tree:0`, `--filter=sparse:oid=<oid>`, `--filter=object:type=<type>`.
       The `promisor` remote, `remote.<name>.promisor`, `remote.<name>.partialclonefilter`, and
       lazy on-demand fetch of missing objects. `[CFG]` `[RESEARCH]`
2.11.4 **Trap:** a partial clone makes `git log -p`, `git blame` and `git grep <rev>` issue
       thousands of tiny lazy fetches and become pathologically slow. `git backfill` (and, in 2.54,
       `git backfill <range>` and `git backfill -- '*.java'`) prefetches what you need.
       `[TRAP]` `[RESEARCH]`
2.11.5 **Sparse-checkout**: `git sparse-checkout init --cone`, `set <dirs>`, `add`, `list`,
       `disable`, `reapply`, and `clean` (2.52). Cone mode (directory prefixes, fast) versus
       non-cone mode (full gitignore-style patterns, slow, no sparse index). `[CMD]` `[RESEARCH]`
2.11.6 The mechanism: the `SKIP_WORKTREE` bit in the index. Files outside the cone stay in the index
       (so commits are complete) but are not written to disk. `[PROVE]` `[RESEARCH]`
2.11.7 **Trap:** `SKIP_WORKTREE` and `--assume-unchanged` are different bits with different meanings,
       and using `update-index --skip-worktree` by hand to "ignore" a tracked config file breaks
       merges, rebases and checkouts in ways that look like Git bugs. `[TRAP]`
2.11.8 **Sparse index**: `index.sparse=true` writes *directory* entries (path + tree OID) for
       everything outside the cone instead of one entry per file. Measured: index **180 MB → under
       10 MB**; `git status` on a 2M-file repository with 100k files in the cone **1.3 s → under
       200 ms**. `[NUM]` `[RESEARCH]` `[SOURCE]`
2.11.9 `command_requires_full_index` and `ensure_full_index()`: any command not yet sparse-aware
       silently expands the index and pays the full cost. The sparse-aware set grew over 2.33
       (`status`, `commit`, `checkout`), 2.34 (`add`, `merge`, `rebase`, `cherry-pick`, `reset`) and
       later (`diff`, `blame`, `clean`, `stash`, `sparse-checkout`). Naming this explains why
       "sparse-checkout didn't make it faster". `[TRAP]` `[RESEARCH]`
2.11.10 `core.sparseCheckout`, `core.sparseCheckoutCone`, `index.sparse`, and their interaction with
        `extensions.worktreeConfig`. `[CFG]` `[RESEARCH]`
2.11.11 **Scalar** (`scalar clone`, `scalar register`, `scalar unregister`, `scalar reconfigure`,
        `scalar run`) — now shipped *with* Git, not a separate Microsoft tool. It turns on partial
        clone, sparse-checkout cone, sparse index, commit-graph, fsmonitor, background prefetch and
        scheduled maintenance in one command. `[CMD]` `[RESEARCH]`
2.11.12 The combined measured effect: a 14-minute clone → 90 seconds; a 5 GB working directory →
        200 MB; a 50 GB monorepo behaving like a 500 MB one. `[NUM]` `[RESEARCH]`
2.11.13 **fsmonitor**: `core.fsmonitor=true` uses the built-in `git fsmonitor--daemon`
        (FSEvents on macOS, ReadDirectoryChangesW on Windows, and **inotify on Linux as of 2.55**).
        It turns `git status` from O(files) into O(changed files). `[CFG]` `[NUM]` `[RESEARCH]`
2.11.14 The untracked cache (`core.untrackedCache`), `core.checkStat`, `core.trustCtime`,
        `core.preloadIndex`, `core.longpaths` (Windows), and `feature.manyFiles` /
        `feature.experimental` as bundled presets. `[CFG]`
2.11.15 **commit-graph**: `git commit-graph write --reachable --changed-paths`,
        `core.commitGraph=true`, `gc.writeCommitGraph`, `fetch.writeCommitGraph`. Turns
        `merge-base`, `log --graph` and `log -- <path>` from graph walks into indexed lookups.
        `[CFG]` `[RESEARCH]`
2.11.16 **`git maintenance`**: `register`, `unregister`, `start`, `stop`, `run [--task=]`. Tasks by
        exact name: `gc`, `commit-graph`, `prefetch`, `loose-objects`, `incremental-repack`,
        `pack-refs`, `geometric` (2.54), `reflog-expire`, `worktree-prune`, `rerere-gc`.
        `[CMD]` `[RESEARCH]`
2.11.17 `maintenance.strategy` values: `none`, `gc`, `geometric` (2.54; default for **manual** runs),
        `incremental` (default for **scheduled** runs — hourly `prefetch`+`commit-graph`, daily
        `loose-objects`+`incremental-repack`, weekly `pack-refs`). `[CFG]` `[NUM]` `[RESEARCH]`
2.11.18 The auto thresholds, each by name and default: `maintenance.auto` (true),
        `maintenance.autoDetach` (true), `maintenance.commit-graph.auto` (100),
        `maintenance.loose-objects.auto` (100), `maintenance.loose-objects.batchSize` (50000),
        `maintenance.incremental-repack.auto` (10), `maintenance.geometric-repack.auto` (100),
        `maintenance.geometric-repack.splitFactor` (2), `maintenance.reflog-expire.auto` (100),
        `maintenance.rerere-gc.auto` (1), `maintenance.worktree-prune.auto` (1). `[NUM]` `[CFG]`
        `[RESEARCH]`
2.11.19 `prefetch` writes into `refs/prefetch/*` rather than `refs/remotes/*`, so a background fetch
        never changes what `git status` tells you. A subtle and important design choice.
        `[PROVE]` `[RESEARCH]`
2.11.20 **Bundle URIs** (`transfer.bundleURI`, `clone --bundle-uri`) — seed a clone from a CDN-hosted
        bundle, then fetch only the delta. The CI clone-cost fix at organisation scale.
        `[RESEARCH]` `[X-REF 19]`
2.11.21 CI clone strategy as a cost decision: full clone vs `--depth=1` vs `--filter=blob:none` vs
        cached workspace vs bundle URI, with what each breaks (`depth=1` breaks
        `diff origin/main...HEAD`, blame and bisect). A table. `[NUM]` `[X-REF 19]`
2.11.22 Monorepo trunk contention: merge-queue throughput as the limiting factor, batch merging,
        speculative parallel testing, and build-affected-target selection. `[X-REF 22]`

*(22 leaves)*

## §2.12 Large files and Git LFS

2.12.1 Why Git is bad at large binaries: every version is a full blob, deltas rarely help on
       compressed formats, and every clone downloads every version ever committed. A 50 MB asset
       changed weekly for two years is 5 GB of clone. `[PROVE]` `[NUM]`
2.12.2 **Git LFS**: the committed object is a small text **pointer file**
       (`version`, `oid sha256:<hex>`, `size`); the real bytes live on an LFS server addressed by
       that OID. `[HEX]` `[RESEARCH]`
2.12.3 The mechanism is `.gitattributes` `filter=lfs diff=lfs merge=lfs -text` plus the clean/smudge
       filter pair: **clean** on `git add` replaces content with a pointer and uploads;
       **smudge** on checkout replaces the pointer with content and downloads. `[PROVE]`
       `[RESEARCH]`
2.12.4 `filter.lfs.process` implements Git's long-running process filter protocol (pkt-line
       handshake, `git-filter-client`, capabilities `clean`/`smudge`/`delay`) so one LFS process
       handles a whole checkout instead of one fork per file. `[RESEARCH]`
2.12.5 `filter.lfs.required = true` means a checkout **fails** rather than silently writing pointer
       files when LFS is not installed — the cause of "my repository is full of 130-byte text files
       that should be PNGs". `[TRAP]` `[RESEARCH]`
2.12.6 Commands: `git lfs install`, `track`, `untrack`, `ls-files`, `status`, `push`, `pull`,
       `fetch --recent`, `checkout`, `prune`, `migrate import/export`, `lock`/`unlock`/`locks`,
       `env`, `fsck`. `[CMD]` `[RESEARCH]`
2.12.7 `GIT_LFS_SKIP_SMUDGE=1 git clone` then `git lfs pull` — the standard CI pattern, because
       smudging during clone makes Git's memory usage scale with the largest LFS file.
       `[TRAP]` `[RESEARCH]`
2.12.8 `git lfs migrate import --include="*.psd" --everything` converts existing history — which is
       a **history rewrite** with all of §2.7's consequences. `[TRAP]` `[RESEARCH]`
2.12.9 File locking (`git lfs lock`) for genuinely unmergeable binaries, and why it is the one place
       Git adopts a Perforce idea. `[RESEARCH]`
2.12.10 LFS costs and limits: server storage and bandwidth billing, GitHub's per-file and quota
        limits, the fact that LFS objects are **not** in the packfile so `gc` does not help, and
        `git lfs prune` for local cleanup. `[NUM]`
2.12.11 The alternatives: `git-annex`, artifact repositories (Artifactory, S3 with a manifest),
        content-addressed build caches, and simply not committing generated artefacts. For a
        backend Java service the right answer is usually **the last one**.
2.12.12 GitHub's hard limits worth knowing: warning at 50 MB, hard rejection at 100 MB per file,
        recommended repository size under 1 GB, 5 GB soft limit. `[NUM]` `[RESEARCH]`
2.12.13 A `pre-receive` or `pre-commit` guard that rejects blobs over a threshold, as the prevention
        that beats every cure in §2.7. `[BUILD]`

*(13 leaves)*

## §2.13 Hooks

2.13.1 A hook is an executable in `$GIT_DIR/hooks` (or `core.hooksPath`) named exactly for the event,
       with the executable bit set. No extension, no registration.
2.13.2 The **client-side** hook inventory with exact names, trigger, and whether non-zero aborts:
       `applypatch-msg`, `pre-applypatch`, `post-applypatch`, `pre-commit`, `pre-merge-commit`,
       `prepare-commit-msg`, `commit-msg`, `post-commit`, `pre-rebase`, `post-checkout`,
       `post-merge`, `pre-push`, `pre-auto-gc`, `post-rewrite`, `sendemail-validate`,
       `fsmonitor-watchman`, `post-index-change`. `[SOURCE]` `[RESEARCH]`
2.13.3 The **server-side** inventory: `pre-receive`, `update` (once per ref), `proc-receive`
       (when `receive.procReceiveRefs` is set), `post-receive`, `post-update`, `push-to-checkout`,
       `reference-transaction`. `[SOURCE]` `[RESEARCH]`
2.13.4 The `git-p4` hooks that exist and that you will never use: `p4-changelist`,
       `p4-prepare-changelist`, `p4-post-changelist`, `p4-pre-submit`. Listed for completeness.
       `[RESEARCH]`
2.13.5 `reference-transaction` fires in `prepared`, `committed` and `aborted` states and can abort in
       the first two — the hook that makes server-side ref auditing and "nobody may delete a
       release tag" enforceable. `[RESEARCH]`
2.13.6 `post-rewrite` receives the old→new OID mapping after `commit --amend` and `rebase` — how
       tooling keeps external state (review systems, notes) attached across a rewrite. `[PROVE]`
2.13.7 Hook arguments and stdin per hook, stated precisely for the four you will actually write:
       `pre-commit` (no args), `commit-msg` (path to the message file), `pre-push`
       (`<remote> <url>`, stdin lines of `<local-ref> <local-oid> <remote-ref> <remote-oid>`),
       `pre-receive` (stdin lines of `<old> <new> <ref>`). `[SOURCE]`
2.13.8 **Hooks are not version-controlled and not distributed by a clone.** This is the central
       limitation and the reason for every hook-manager tool. `[TRAP]` `[PROVE]`
2.13.9 `core.hooksPath` pointed at a committed `.githooks/` directory — the poor-man's distribution
       mechanism, plus the one-line bootstrap everyone must run.
2.13.10 **Config-based hooks (2.54)**: `[hook "spotless"] event = pre-commit` and
        `command = ./mvnw -q spotless:apply`; multiple hooks per event; `git hook list`;
        `hook.<name>.enabled = false` to disable without deleting. `.git/hooks` scripts still run,
        and run **last**. `[CFG]` `[RESEARCH]` `[VERSION-TRAP]`
2.13.11 **Parallel config hooks (2.55)**: `hook.<name>.parallel = true`, `hook.jobs`,
        `hook.<event>.jobs`, `git hook run -j`. `[CFG]` `[RESEARCH]`
2.13.12 `git hook run <event>` as the way to test a hook without performing the operation.
2.13.13 Hook managers and what each is for: `pre-commit` (Python, multi-language, the de facto
        standard), `husky` + `lint-staged` (JS ecosystem), `lefthook` (Go, fast, parallel),
        Maven/Gradle plugins that install hooks at build time. `[RESEARCH]`
2.13.14 What belongs in a `pre-commit` hook: formatter, fast linter, secret scan, forbidden-pattern
        check, large-file guard. Budget: **under 2 seconds**. Anything slower gets `--no-verify`'d
        into irrelevance. `[NUM]` `[PROVE]`
2.13.15 What belongs in `pre-push`: the fast test subset and a branch-name policy check. Budget:
        under 30 seconds.
2.13.16 What belongs in CI and **not** in a hook: the full test suite, integration tests, coverage
        gates, security scans. A hook is advisory; CI is authoritative. `[X-REF 16]`
2.13.17 **Trap:** hooks are trivially bypassed with `--no-verify`, and server-side hooks are the only
        enforcement. Any "policy" implemented purely in a client hook is a suggestion. `[TRAP]`
        `[PROVE]`
2.13.18 **Trap:** cloning an untrusted repository and running any Git command can execute code if a
        hook or a `core.fsmonitor`/filter config is planted. This is why `safe.directory` and
        protected-configuration scopes exist. `[TRAP]` `[X-REF 13]`
2.13.19 Complete `[BUILD]` hooks for the QuizStakes repo, runnable as written: a `commit-msg` hook
        enforcing `^(feat|fix|chore|refactor|test|docs|perf|build|ci)(\(.+\))?: .{1,60}$` plus a
        ticket trailer; a `pre-commit` hook running `spotless:check` on staged Java files only and a
        `gitleaks` scan; a `pre-push` hook refusing a push to `main`; a `pre-receive` hook rejecting
        blobs over 10 MB and force-pushes to protected refs. `[BUILD]`
2.13.20 Hook observability: log hook duration, and treat a slow hook as a defect in the developer
        experience with the same seriousness as a slow build. `[X-REF 20]`

*(20 leaves)*

## §2.14 Signing, provenance, and trust

2.14.1 What a signature covers: the commit or tag object's bytes, which transitively cover the tree
       and the parents. Signing a commit therefore attests to the whole history behind it.
       `[PROVE]`
2.14.2 GPG signing: `user.signingkey`, `commit.gpgsign`, `tag.gpgSign`, `gpg.program`, `git commit
       -S`, `git tag -s`, `git log --show-signature`, `%G?` format placeholder values
       (`G`, `B`, `U`, `X`, `Y`, `R`, `E`, `N`). `[CFG]` `[NUM]`
2.14.3 **SSH signing (2.34+)**: `gpg.format = ssh`, `user.signingkey = ~/.ssh/id_ed25519.pub`,
       `gpg.ssh.allowedSignersFile`, the allowed-signers line format
       `<email> namespaces="git" <public-key>`, and `git verify-commit`. Dramatically simpler than
       GPG and supported by GitHub and GitLab (not Bitbucket). `[CFG]` `[RESEARCH]`
2.14.4 `gpg.ssh.revocationFile`, and SSH signing with a hardware key or 1Password/`ssh-agent`.
       `[RESEARCH]`
2.14.5 X.509/S-MIME signing (`gpg.format = x509`, `gpg.x509.program = gpgsm`) for enterprises with a
       PKI. `[RESEARCH]`
2.14.6 `git merge --verify-signatures`, `git pull --verify-signatures`, and a `pre-receive` hook that
       rejects unsigned commits — the enforcement points. `[BUILD]`
2.14.7 `git push --signed` and `receive.certNonceSeed`: signing the **push** (which refs moved from
       where to where), not just the commits. The mechanism that would have detected a force-push
       forgery. `[RESEARCH]`
2.14.8 Signed tags for releases as the minimum viable provenance, and verifying them in the deploy
       pipeline. `[X-REF 19]`
2.14.9 **Trap:** "verified" on GitHub means the signature matched a key on the account, **not** that
       the author is who the `author` line says. Web-UI commits are signed by GitHub's own key, so
       a "verified" badge on a commit you did not make is normal. `[TRAP]` `[RESEARCH]`
2.14.10 **Trap:** commit authorship is self-declared. `git commit --author="Someone Else <x@y>"`
        needs no permission at all. Signing is the only thing that makes authorship meaningful.
        `[TRAP]` `[PROVE]`
2.14.11 Rebasing and signing: rebase drops signatures unless you re-sign
        (`git rebase --exec 'git commit --amend --no-edit -S'` or `rebase.gpgSign`). Squash-merge on
        the host re-signs with the host's key. `[TRAP]`
2.14.12 Supply-chain framing: signed commits, signed tags, provenance attestations (SLSA), and
        reproducible builds. What Git gives you and what it does not. `[X-REF 13]` `[X-REF 19]`
2.14.13 `git log --format='%h %G? %GS %an'` as the audit query. `[CMD]`

*(13 leaves)*

## §2.15 Branching models

2.15.1 **Trunk-based development**: everyone commits to `main` (or to branches lasting hours), CI on
       every commit, feature flags for incomplete work, release from trunk or from short-lived
       release branches. The DORA-endorsed model. `[RESEARCH]`
2.15.2 The invariant that justifies it all: **`main` must be deployable at every commit.** Preserve
       verbatim from the current guide — CI on every PR, required reviews, protected branches and
       feature flags are all machinery in service of this one rule. `[PROVE]`
2.15.3 **GitHub Flow**: branch, PR, review, merge, deploy. Simplest model that works; assumes
       continuous deployment and one production version.
2.15.4 **GitFlow**: `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`. What it was designed for
       (versioned, shipped-to-customers software with parallel supported versions) and why its own
       author added a note saying it is the wrong default for web services. `[TRAP]` `[RESEARCH]`
2.15.5 **GitLab Flow**: trunk plus environment branches (`staging`, `production`) or release
       branches, with merges flowing downstream only.
2.15.6 **Release branches**: `release/2026.09` cut from `main`, only fixes cherry-picked in with
       `-x`, tagged and deployed. When you need them (mobile, on-prem, regulated release windows)
       and when they are pure overhead.
2.15.7 **Feature flags decouple deploy from release.** Preserve the current guide's framing verbatim,
       including the cost: flag debt, every flag needs an owner and a removal date. Add the
       taxonomy: release toggles, experiment toggles, ops toggles, permission toggles — with
       different lifetimes. `[RESEARCH]`
2.15.8 Branch-by-abstraction as the alternative for changes too structural for a flag.
2.15.9 Expand/contract (parallel change) for schema and API changes that cannot be flagged: add the
       new, dual-write, migrate, read from new, remove the old. `[X-REF 09]` `[X-REF 12]`
2.15.10 **Stacked PRs**: a chain of dependent branches, each targeting the one below, so reviewers
        see 200-line diffs instead of an 800-line one. The mechanics: `--update-refs`, the
        base-branch retarget on merge, and the cascading rebase.
2.15.11 The tooling: `git rebase --update-refs` (built in), Graphite (`gt`), `git-branchless`
        (`git move`, `git sync`, commit-centric), `spr` (client-side, no server support needed),
        `ghstack`, and **GitHub's native `gh-stack`** — private preview 13 Apr 2026, public preview
        30 Jul 2026, `gh stack sync` doing the cascading rebase and force-push. `[RESEARCH]`
2.15.12 **Trap:** squash-merge and rebase-merge both rewrite hashes and therefore **break stack
        identity tracking**; only plain merge commits work for intermediate PRs in a stack. This is
        GitHub's own stated limitation and it is the reason stacked PRs and squash-merge policies
        conflict. `[TRAP]` `[RESEARCH]`
2.15.13 The practical ceiling on stack depth — GitHub cites 3–4 PRs before the coordination overhead
        outweighs the review benefit. `[NUM]` `[RESEARCH]`
2.15.14 Fork-based workflow (open source): `upstream` and `origin` remotes, `git remote add
        upstream`, keeping a fork current, and the `refs/pull/<n>/head` namespace for checking out a
        contributor's PR. `[CMD]`
2.15.15 Maintainer-side workflow: `git request-pull`, `git am` from a mailing list, topic branches,
        `next`/`master`/`maint` as the Git project itself uses them.
2.15.16 Choosing a model — the decision inputs: deploy frequency, number of supported versions,
        release approval process, team size, monorepo or not, and regulatory constraints. Give a
        decision table, not a preference. `[NUM]`
2.15.17 The QuizStakes recommendation with justification: trunk-based on `main`, squash-merge,
        short-lived `feature/<TICKET>-<slug>` branches, `release/YYYY.MM` cut only for the
        regulated self-exclusion changes, feature flags for everything else, and a merge queue.

*(17 leaves)*

## §2.16 The pull request as an artefact

2.16.1 PR discipline, preserved verbatim from the current guide: small, single-purpose, with a
       description covering **what changed, why, and how it was verified**; CI green before
       requesting review; self-review the diff in the web UI first; link the ticket; screenshots or
       real test output for behavioural change; rebase on `main` before merging so CI tests what
       will actually land.
2.16.2 A PR description template the bible must ship, with sections: Problem, Approach, Alternatives
       considered, Verification, Risk and rollback, Screenshots/output, Ticket. Plus a
       `.github/pull_request_template.md` implementation. `[BUILD]`
2.16.3 The three PR merge strategies table, preserved verbatim from the current guide (merge commit /
       squash / rebase) with "Result" and "Best for" columns, and extended with: what `git revert`
       looks like afterwards, what `git bisect` lands on, and what happens to the source branch's
       commits.
2.16.4 Why squash-merge is the pragmatic default: one revertable, bisectable unit per PR, and the
       WIP commits disappear. Preserve the current guide's argument. `[PROVE]`
2.16.5 Why squash-merge is sometimes wrong: it destroys a carefully-built commit series, it breaks
       stacked-PR identity, and it makes a 40-commit refactor unreadable as one commit. Name the
       exceptions.
2.16.6 Draft PRs, `WIP:` prefixes, and the "open early for direction, request review when ready"
       protocol.
2.16.7 `CODEOWNERS`: syntax, path matching, team ownership, required-review integration, and the
       failure mode where one team owns everything and becomes the bottleneck. `[TRAP]`
2.16.8 Auto-merge, required status checks, and "merge when checks pass" — plus the race where
       `main` moves between the check and the merge, which is exactly what a merge queue fixes.
       `[PROVE]`
2.16.9 PR templates, labels, and automation: size labels, `semantic-pull-request` title checks,
       changelog generation from PR titles, and the danger of automating the wrong signal.
2.16.10 Review requests: how many reviewers (one required, one optional domain expert is the usual
        sweet spot), round-robin assignment, and the review-load metric that shows when one person
        reviews everything. `[NUM]`
2.16.11 Time-to-first-review as the metric that actually predicts throughput; a PR blocked two days
        is worse than a slightly worse review in two hours. Preserve from the current guide.
        `[X-REF 20]`
2.16.12 Splitting a large change into a PR series: separate refactor from behaviour change, land
        scaffolding first, flag incomplete work, split by layer or endpoint, and if it truly cannot
        be split, review **commit by commit** and say so in the description. Preserve verbatim from
        the current guide. `[PROVE]`
2.16.13 The commit-series PR: when every commit is meaningful, tested and individually revertable,
        rebase-merge is correct and the reviewer reads commits, not the combined diff.
2.16.14 What a reviewer should be able to do in under 30 seconds: understand what problem this
        solves, and how to verify it. If the description does not deliver that, the PR is not ready.

*(14 leaves)*

## §2.17 Code review method

2.17.1 The priority order, preserved verbatim from the current guide and expanded one level each:
       **1 correctness, 2 security, 3 tests, 4 design and maintainability, 5 performance,
       6 operability, 7 style — last, and ideally not by a human.** `[PROVE]`
2.17.2 Correctness sub-checklist: off-by-one, null/empty/one/many, error paths, exception handling
       and swallowed exceptions, concurrency and shared mutable state, transaction boundaries,
       idempotency, boundary values, time zones and DST, integer overflow, `BigDecimal` for money.
       `[X-REF 03]` `[X-REF 05]` `[X-REF 08]`
2.17.3 Security sub-checklist: injection (SQL, command, template, log), authz on **every** entry
       point not just the UI, secrets in code or logs, unvalidated input, PII in log lines,
       dependency risk, SSRF, deserialization. Preserve the current guide's list. `[X-REF 13]`
2.17.4 Tests sub-checklist: do they cover behaviour including failure paths, would they fail if the
       code were wrong, are they deterministic, do they assert on the right thing, is there a test
       for the bug being fixed. Preserve the current guide's framing. `[X-REF 16]`
2.17.5 Design sub-checklist: right abstraction level, sensible boundaries, no duplicated concept,
       fits the existing architecture, does not leak internals, no premature generalisation.
2.17.6 Performance sub-checklist: N+1 queries, unbounded collections, missing indexes, synchronous
       remote calls in a loop, unbounded caches, allocation in a hot path — **only where it
       matters**. Preserve the current guide's "don't micro-optimise cold paths". `[X-REF 08]`
       `[X-REF 15]`
2.17.7 Operability sub-checklist: can you debug this at 3am — logging with context, metrics, error
       messages that name the failing input, timeouts on every remote call, retries with jitter,
       a runbook entry. Preserve verbatim. `[X-REF 20]`
2.17.8 Style: automate it entirely (formatter, linter, CI check). Human attention spent on style is
       attention not spent on 1–6, and style comments are what make reviews feel adversarial.
       Preserve verbatim. `[PROVE]`
2.17.9 The sentence to remember: **a review that produces six style nits and misses a missing
       authorisation check is a failed review, even though it looks thorough.** Preserve verbatim.
2.17.10 **PR sizing — the evidence**, preserved verbatim from the current guide: defect detection
        drops sharply beyond **200–400 changed lines**; effectiveness falls after **~60 minutes**;
        faster than **~500 LOC/hour** finds materially fewer defects. Source: SmartBear's Cisco
        study and the broader review literature. `[NUM]` `[RESEARCH]`
2.17.11 Corroborating 2026 data: PRs between 200 and 400 lines had ~40% fewer defects and were
        approved three times faster than larger ones. `[NUM]` `[RESEARCH]`
2.17.12 **A 1,000-line PR does not get reviewed, it gets approved.** Preserve verbatim, with the
        consequence: four 250-line PRs find several times more defects for the same total effort.
        `[PROVE]`
2.17.13 Comment labelling, preserved verbatim: `blocking:`, `suggestion:`, `nit:`, `question:`,
        `praise:` — with the note that more than a couple of nits means automate them instead, and
        that reviews which are 100% criticism corrode a team.
2.17.14 The Conventional Comments format as the published version of the same idea
        (`<label> [decorations]: <subject>`), for teams that want a standard to point at.
        `[RESEARCH]`
2.17.15 **Question-form feedback**, preserved verbatim with all three reasons: you might be wrong; it
        transfers the reasoning; it depersonalises. Include the current guide's two example
        phrasings. `[PROVE]`
2.17.16 The two-round-trip rule: after two exchanges, take it to a call, and **write the conclusion
        back into the PR**. Preserve verbatim.
2.17.17 Author-side norms, preserved verbatim: respond to every comment (even "done"), don't take it
        personally, push fixes as separate commits so the reviewer sees the delta, re-request review
        explicitly. Add: use `--fixup` so the delta is reviewable *and* the history ends clean
        (§2.6.8).
2.17.18 Reviewing your own PR first, in the web UI, before requesting review. "You will find
        something every time." Preserve verbatim.
2.17.19 Reviewing a large unavoidable diff: read the tests first, then the interfaces, then the
        implementation; use `--color-moved` and `-w`; review commit by commit; and check out the
        branch and run it.
2.17.20 Reviewing a refactor: verify it is behaviour-preserving by checking that tests were **not**
        modified. A refactor PR that changes tests is not a refactor. `[PROVE]` `[X-REF 16]`
2.17.21 Reviewing an AI-generated PR in 2026: the diff is plausible-looking by construction, so
        correctness and test-quality review matter more, not less. Check for hallucinated APIs,
        invented config keys, tests that assert the implementation, and silently changed behaviour.
        `[X-REF 21]`
2.17.22 Review as teaching: what a senior reviewer does that a junior does not — asks about the
        cases not in the diff, notices the missing test, spots the wrong abstraction, and says
        explicitly what is *good*.
2.17.23 Review anti-patterns to name: the rubber stamp, the drive-by nit, the architecture debate in
        a bug-fix PR, the reviewer who blocks and disappears, the author who force-pushes so the
        review comments detach from lines.
2.17.24 **Trap:** force-pushing a reviewed branch orphans review comments on GitHub and destroys the
        "changes since your last review" view. Push fixups instead, and only rebase immediately
        before merge. `[TRAP]`
2.17.25 Measuring review health without gaming it: time to first review, review round trips, PR
        size distribution, and post-merge defect rate. What each metric distorts when targeted.
        `[X-REF 20]`

*(25 leaves)*

## §2.18 Commit message craft

2.18.1 The worked example, preserved verbatim from the current guide in structure and re-domained to
       QuizStakes: subject, blank line, body explaining the incident and the reasoning, trailer.
2.18.2 The rules, preserved verbatim: imperative subject completing "this commit will…", ≤50 chars,
       capitalised, no trailing period; blank line after the subject (Git tooling depends on it);
       body wrapped at 72 explaining **why** not what; reference the ticket. `[NUM]`
2.18.3 Why 50/72: `git log --oneline` and `git shortlog` truncation, and 80-column terminals with
       `git log`'s 4-space indent. Show the arithmetic. `[NUM]` `[PROVE]`
2.18.4 **The test**, preserved verbatim: in eighteen months someone will `git blame` this line during
       an incident. Does the message tell them why the line exists? "Fix bug", "update", "changes",
       "address PR comments" all fail.
2.18.5 The diff shows *what*; it can never show what you knew, what you rejected, or what constraint
       forced the design. Preserve verbatim. `[PROVE]`
2.18.6 Trailers as structured data: `Signed-off-by`, `Co-authored-by`, `Reviewed-by`, `Fixes`,
       `Closes`, `Refs`, `Reported-by`, `Tested-by`, `Cc`. `git interpret-trailers`,
       `trailer.<token>.*` config, `git commit --trailer`, and
       `git shortlog --group=trailer:Co-authored-by`. `[CFG]` `[RESEARCH]`
2.18.7 `Signed-off-by` and the Developer Certificate of Origin — what it legally asserts, and why
       some projects require it. `git commit -s`, `git rebase --signoff`.
2.18.8 **Conventional Commits**: `<type>[optional scope][!]: <description>`, the type vocabulary
       (`feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`),
       `BREAKING CHANGE:` footer or `!`, and the mapping to SemVer (fix→patch, feat→minor,
       breaking→major). Preserve the current guide's mention and complete the spec. `[RESEARCH]`
2.18.9 What Conventional Commits buys (machine-readable changelogs, automated versioning via
       `semantic-release`/`release-please`, filterable history) and what it does not (it does not
       make the body good). Preserve the current guide's judgement that the *why* matters more than
       the prefix. `[PROVE]`
2.18.10 `commit.template`, `commit.cleanup` (`strip`, `whitespace`, `verbatim`, `scissors`,
        `default`), and `--cleanup=scissors` with `# ------------------------ >8 ---` for
        including the diff in the editor. `[CFG]`
2.18.11 `commit.verbose = true` again, here as a message-quality tool: you write a better message
        when the diff is on screen. `[CFG]`
2.18.12 The commit message of a **revert** and of a **merge**: both default to something useless and
        both deserve a real body saying why.
2.18.13 A commit-message quality checklist for review: does the subject stand alone, does the body
        explain a decision, is the ticket linked, would this be the right message if the commit were
        cherry-picked to a release branch.
2.18.14 The `commit-msg` hook that enforces the format, with the exact regex and the escape hatch for
        merge and revert commits. `[BUILD]`

*(14 leaves)*

## §2.19 CI integration and merge queues

2.19.1 What CI must run on a PR, and against **what**: the merge result, not the branch tip. GitHub
       Actions' `pull_request` event tests a synthetic merge commit; `push` tests the branch. Know
       which you are looking at. `[TRAP]` `[X-REF 19]`
2.19.2 The stale-base problem: PR A and PR B each pass against `main@t0`, both merge, and `main` is
       broken. Neither was ever tested against the other. `[PROVE]`
2.19.3 **Semantic conflicts** are the general case: one PR renames `reserveStake`, another adds a
       caller; both merge cleanly and the build fails. Git cannot detect this by construction.
       Preserve and extend §1.13.12. `[PROVE]`
2.19.4 **Merge queue / merge train**: serialise merges, and test each candidate against `main` plus
       every preceding item in the queue before it lands. This is the only mechanism that keeps
       `main` green under concurrency. `[PROVE]` `[RESEARCH]`
2.19.5 GitHub merge queue versus GitLab merge trains versus Graphite/Trunk.io/Mergify: static
       parallel window size, per-MR temporary refs with cumulative state, batch size, and the
       bisect-on-failure behaviour when a batch fails. `[RESEARCH]`
2.19.6 The throughput arithmetic: with a serial queue and a T-minute pipeline, the ceiling is 60/T
       merges per hour. Speculative parallel batches of k raise it at the cost of k× compute, and
       a failure in a batch costs a re-run. Work the numbers for a 12-minute pipeline. `[NUM]`
       `[PROVE]`
2.19.7 Required status checks, branch protection, and the difference between "required" and
       "reported" checks.
2.19.8 CI clone cost, revisited as a policy: `fetch-depth`, submodule recursion, LFS smudging,
       caching `.git`, and bundle URIs. Reference §2.11.21. `[X-REF 19]`
2.19.9 Computing "what changed" in CI correctly: `git diff --name-only origin/main...HEAD` needs the
       merge base, which needs a non-shallow fetch. The single most common broken-CI-Git
       interaction. `[TRAP]` `[RECOVER]`
2.19.10 Path-filtered CI in a monorepo: `paths:`/`paths-ignore:` filters, `git diff` driven job
        selection, and the correctness trap of skipping a job whose dependency changed.
        `[TRAP]` `[X-REF 19]`
2.19.11 Commit status and check-run APIs; posting review comments from CI (formatter diffs, coverage
        deltas) instead of failing opaquely.
2.19.12 Deploy provenance: the commit SHA in the artefact, in the health endpoint, in the logs, and
        in the metrics label. `git describe --tags --dirty --always` as the build stamp. This is
        what makes "what changed?" (§2.22) answerable in seconds. `[X-REF 20]`
2.19.13 Git-driven deploy models: tag-triggered releases, GitOps (the repository as the desired
        state, a controller reconciling), and environment branches. Name the trade-offs.
        `[X-REF 19]`
2.19.14 `git bisect run` inside CI as a scheduled regression hunter on a nightly benchmark.
2.19.15 Repository health in CI: a job that fails when a blob over 10 MB, a secret pattern, or a
        merge-conflict marker reaches `main`. `[BUILD]`

*(15 leaves)*

## §2.20 Secrets in history

2.20.1 **Trap:** deleting a secret in a new commit does nothing. It is still in the history, in every
       clone, on the remote, in every fork, in CI caches, and retrievable via the GitHub API long
       after a force-push. Preserve verbatim from the current guide. `[TRAP]` `[PROVE]`
2.20.2 The response order, preserved verbatim and expanded:
       **1 rotate the credential immediately** (public repos are scanned by bots within seconds);
       **2 audit for use** (unexpected IP, unexpected time); **3 then** clean the history if
       worthwhile; **4** coordinate the re-clone and ask the host to purge caches and forks;
       **5** prevent recurrence. `[RECOVER]`
2.20.3 **Rotate first, clean second.** Preserve verbatim — the order is frequently got backwards in
       interviews. Rotation is the fix; history cleaning is hygiene. `[PROVE]`
2.20.4 The cleaning commands, preserved from the current guide:
       `git filter-repo --path config/secrets.yml --invert-paths` and
       `git filter-repo --replace-text expressions.txt`; BFG as the older alternative. Re-domain the
       path to QuizStakes. `[CMD]`
2.20.5 The `expressions.txt` format for `--replace-text`: `literal:`, `regex:`, `glob:`, and
       `==>replacement`. `[SOURCE]` `[RESEARCH]`
2.20.6 Why a rewrite alone does not remove dangling objects from the remote, and what to ask the host
       to do (GitHub: contact support to purge cached views, delete affected forks). Preserve
       verbatim. `[TRAP]`
2.20.7 Prevention, preserved and expanded: pre-commit secret scanning (`gitleaks`, `detect-secrets`,
       `talisman`, `trufflehog`), server-side push protection (GitHub Secret Scanning with push
       protection, GitLab Secret Push Protection), and a real secret store so there is no reason for
       a secret to be in a file. `[X-REF 18]`
2.20.8 Detection at scale: `gitleaks detect --log-opts` over full history, partner-pattern scanning,
       and the fact that a scanner's false-negative rate on high-entropy strings is not zero.
2.20.9 The `.env` / `application-local.yml` discipline: never tracked, always in `.gitignore`, always
       with a committed `.example`, and configuration injected at runtime. `[X-REF 07]`
2.20.10 What counts as a secret beyond API keys: internal hostnames, database connection strings,
        JWT signing keys, customer PII in a test fixture, an internal architecture diagram, and a
        `.pem`. `[X-REF 13]`
2.20.11 The incident write-up for a leaked credential: timeline, blast radius (who could have read
        it and for how long), rotation confirmation, evidence of non-use, and the prevention
        control added. `[X-REF 20]`
2.20.12 A complete `[BUILD]` runbook for the QuizStakes case: a `FundsLedger` database password
        committed to `application-local.yml` on a public-mirror repository. `[BUILD]` `[RECOVER]`

*(12 leaves)*

## §2.21 The recovery cookbook

2.21.1 Every entry has the same four parts: **symptom → diagnosis command → exact fix → verification**.
       State this contract once and hold to it.
2.21.2 "I committed to the wrong branch." `git reset --soft HEAD~1` → switch → commit; or
       `git cherry-pick` then `git reset --hard`. `[RECOVER]`
2.21.3 "I committed a huge file." Before push: `reset --soft` and re-commit. After push:
       `filter-repo` plus a coordinated re-clone. `[RECOVER]`
2.21.4 "I `reset --hard`'d and lost commits." `git reflog` → `git reset --hard HEAD@{n}`.
       `[RECOVER]`
2.21.5 "I `reset --hard`'d and lost **uncommitted** work." Nothing in Git recovers it. Check your
       IDE's local history (IntelliJ keeps one), the editor's undo buffer, and the OS backup. State
       plainly that this is the one unrecoverable case. `[TRAP]` `[RECOVER]`
2.21.6 "I deleted a branch." `git reflog` or `git fsck --lost-found`, then `git branch <name> <oid>`.
       `[RECOVER]`
2.21.7 "Someone force-pushed over `main`." Find the old tip in **your** `origin/main` reflog, or the
       host's audit log, or any colleague's clone; restore and push; then turn on branch protection.
       `[RECOVER]`
2.21.8 "My rebase went wrong." `git rebase --abort` if in progress; otherwise
       `git reset --hard ORIG_HEAD`. `[RECOVER]`
2.21.9 "I amended a commit I should not have." `git reset --hard HEAD@{1}` — the pre-amend commit is
       in the reflog. `[RECOVER]`
2.21.10 "I'm in detached HEAD and made commits." `git branch <name>` before switching away; or
        `git reflog` afterwards. `[RECOVER]`
2.21.11 "`fatal: Unable to create '.git/index.lock': File exists.`" Check for a running Git process
        or a crashed IDE indexer first; only then delete. `[RECOVER]`
2.21.12 "`error: Your local changes would be overwritten by checkout.`" `stash`, `commit`, or
        `switch -m` to carry them across. `[RECOVER]`
2.21.13 "`refusing to merge unrelated histories`." Understand *why* before reaching for
        `--allow-unrelated-histories` — usually you cloned into the wrong place or re-initialised.
        `[RECOVER]`
2.21.14 "`fatal: refusing to fetch into branch ... checked out`" on a non-bare remote.
2.21.15 "The repository is corrupt." `git fsck --full`, `git cat-file -t` on the reported OID, the
        object-recovery order (another clone → the remote → a pack from a colleague → the reflog),
        and when the correct answer is "re-clone and cherry-pick your local work". `[RECOVER]`
2.21.16 "`error: object file ... is empty`" — the classic post-crash/full-disk corruption. Delete the
        zero-length loose object and re-fetch it. `[RECOVER]`
2.21.17 "I need one file from a commit I deleted." `git fsck --lost-found`, `git cat-file -p
        <tree>`, `git show <oid>:<path>`, `git restore --source=<oid>`. `[RECOVER]`
2.21.18 "The submodule points at a commit nobody has." Find who pushed the superproject commit, get
        them to push the submodule, or reset the gitlink. `[RECOVER]`
2.21.19 "CI can't compute the diff against `main`." `fetch-depth: 0` or an explicit
        `git fetch --deepen`. `[RECOVER]`
2.21.20 "My clone is 8 GB and `git status` takes 30 seconds." The diagnosis order:
        `git count-objects -vH` / `git repo structure`, then largest blobs, then ref count, then
        worktree file count, then `core.fsmonitor`, then `git maintenance`. `[RECOVER]` `[NUM]`
2.21.21 "Line endings changed on every file." Diagnose with `git ls-files --eol`, fix with
        `.gitattributes` + `--renormalize` in one dedicated commit added to
        `.git-blame-ignore-revs`. `[RECOVER]`
2.21.22 "`git push` says everything is up to date but the remote is different." Check
        `push.default`, the refspec, and whether you are pushing to a fork. `[RECOVER]`
2.21.23 The universal first move: **stop, and take a backup.** `cp -a .git /tmp/git-backup` or
        `git bundle create /tmp/rescue.bundle --all` before attempting any recovery. State this as
        rule zero. `[RECOVER]`

*(23 leaves)*

## §2.22 Debugging methodology

2.22.1 The framing, preserved verbatim: the difference between an hour and a day is almost never
       knowledge — it is method. Random changes until the symptom disappears is the default failure
       mode and it produces "fixes" that mask the bug.
2.22.2 The hypothesis loop, all eight steps preserved verbatim: observe precisely → reproduce →
       form a **falsifiable** hypothesis → predict → test one variable → confirm or discard and
       iterate → fix the cause not the symptom → add a regression test. `[PROVE]`
2.22.3 "Observe precisely" with the current guide's contrast preserved and re-domained: "the API is
       broken" versus "POST /stakes returns 500 for client segment X since 14:03, ~8% of requests,
       `NullPointerException` in `FundsLedger:88`".
2.22.4 Reproduction as most of the fix; shrinking to the smallest failing case; and why a test that
       reproduces is worth more than an hour of reading. `[X-REF 16]`
2.22.5 Discarding a hypothesis is progress — **write it down** so you do not re-test it at hour four.
       Preserve verbatim.
2.22.6 **Binary-search the problem space**, preserved verbatim: bisect the code path (does the value
       exist at the service boundary? the repository? the DB?), the timeline (`git bisect`), the
       input (which field?), the environment (staging vs prod — what differs?). Each bisection
       halves the search space; guessing does not. `[PROVE]`
2.22.7 **What changed first**, preserved verbatim with the full list: a deploy (yours or a
       dependency's), config or a feature flag, traffic pattern, data, infrastructure, or time
       itself (month-end, DST, certificate or token expiry, leap day). `[PROVE]`
2.22.8 `git log --since='2 hours ago'`, `git log --oneline main@{2.hours.ago}..main`, the deploy
       history, and the flag audit log — the four places "what changed" is actually recorded.
       `[CMD]`
2.22.9 **Correlate the symptom's start time with the change log.** Preserve verbatim: this single
       step resolves a large fraction of incidents in minutes, and if nothing changed on your side,
       something changed on someone else's.
2.22.10 Correlation IDs, preserved with the current guide's Java filter code, updated to Java 21 and
        re-domained to `ApplicationGateway`: generate at the edge if absent, `MDC.put`, `MDC.clear()`
        in a `finally` because threads are pooled. `[BUILD]` `[X-REF 20]`
2.22.11 Propagation on every outbound HTTP call and every published message; include it in the log
        pattern; return it in a response header so users can quote it; include it in DLQ'd messages.
        Preserve verbatim. `[X-REF 14]`
2.22.12 **Trap:** MDC is `ThreadLocal`, so it does not cross `@Async`/executor boundaries or reactive
        chains without a decorator (`TaskDecorator`, `ContextPropagation`). Preserve verbatim.
        `[TRAP]` `[X-REF 05]`
2.22.13 **The 1% bug**, preserved verbatim in structure: the naive loop breaks down because you
        cannot reliably reproduce and cannot tell whether the fix worked or you got lucky.
2.22.14 Step 1 — find the pattern. "Random" almost never is. Correlate by time (hourly batch, TTL
        expiry, DST), instance (one bad pod/node/AZ), input (a specific client, a large payload, an
        encoding), load (only at peak), sequence (only the first request after idle — a stale pooled
        connection), or cardinality (only when a cache is cold). Preserve verbatim. `[X-REF 10]`
2.22.15 Step 2 — the suspect list, preserved verbatim: races and missing synchronisation;
        connection-pool state; timeout and retry edges; caching divergence; load balancing; clock
        skew/DST/timezone; resource exhaustion at the edge (fds, ephemeral ports, thread pool);
        ordering assumptions. `[X-REF 05]` `[X-REF 10]` `[X-REF 14]` `[X-REF 15]`
2.22.16 **A failure rate matching 1/(instance count) points at one bad instance.** Preserve verbatim
        — it is the single strongest signal in the list. `[PROVE]` `[NUM]`
2.22.17 Step 3 — add observability rather than guesses: log inputs and intermediate state on the
        failure path, add a low-cardinality metric, capture a thread dump on the condition. Ship it,
        wait, and now you have data instead of theories. Preserve verbatim. `[X-REF 20]`
2.22.18 Step 4 — **increase the failure rate deliberately**: tight loop, more threads, injected
        latency, smaller pool, constrained container. A 1% bug at 100 rps becomes reproducible at
        10,000 rps. Preserve verbatim. `[NUM]`
2.22.19 Step 5 — **verify statistically.** One successful run proves nothing about a 1% bug; you need
        enough runs or enough production time, plus a metric that would have shown the old failure
        rate. Preserve verbatim. `[PROVE]` `[NUM]`
2.22.20 The Git tools that belong in the debugging loop, tied back: `bisect` for the timeline,
        `blame`/`log -L` for the line, `log -S` for when a string appeared or vanished,
        `range-diff` for what changed between two attempts, `last-modified` for a directory.
2.22.21 Rubber-ducking, the "explain it to someone from the top" reset, and the deliberate decision
        to stop and sleep on it — with the honest note that this is a real technique, not a joke.
2.22.22 Writing the debugging session down as you go: timestamps, hypotheses, evidence, and what you
        ruled out. It becomes the postmortem, and it is the difference between an incident that
        teaches and one that repeats. `[X-REF 20]`

*(22 leaves)*

## §2.23 Repository archaeology

2.23.1 The question catalogue and the command for each — this section is organised by question, not
       by command.
2.23.2 "When was this line last changed and why?" → `git blame -w -C -L`, then `git show` on the
       commit, then the PR it came from.
2.23.3 "Who should review this?" → `git shortlog -sne -- <path>` and `git log --format='%an' -20 --
       <path>`.
2.23.4 "When did this configuration value change?" → `git log -p -S'stake.reservation.timeout' --
       src/main/resources`.
2.23.5 "Which release contains this fix?" → `git tag --contains <sha>`, `git branch -r --contains`,
       `git describe --contains`.
2.23.6 "Is this commit already on the release branch?" → `git cherry -v release/2026.09 main` or
       `git log --cherry-pick --right-only`.
2.23.7 "What did this file look like at the incident?" → `git show 'main@{2026-08-14 14:00}:path'`.
2.23.8 "What changed between these two deploys?" → `git log --oneline <sha1>..<sha2>`,
       `--stat`, and `git diff --stat`.
2.23.9 "Why does this weird line exist?" → `git log -L` on the range, plus `--follow` across the
       rename.
2.23.10 "What was deleted and when?" → `git log --diff-filter=D --name-only -- <path>`.
2.23.11 "What is the biggest thing in this repository?" → `git repo structure`,
        `git verify-pack -v`, `git rev-list --objects --all | ... | sort`. `[CMD]`
2.23.12 "Who has been contributing and how has that changed?" → `git shortlog -sn --since`,
        `git log --format='%ad' --date=format:'%Y-%m' | sort | uniq -c`.
2.23.13 "Which files change together?" — a co-change analysis over `git log --name-only` as a
        coupling detector, and what it tells you about module boundaries. `[BUILD]`
2.23.14 "Which files change most?" — churn as a defect predictor, and the churn × complexity
        quadrant as a refactoring priority list. `[NUM]` `[BUILD]`
2.23.15 The tools built on this: `git-of-theseus`, `code-maat`, CodeScene, `git-quick-stats`,
        `hercules`. `[RESEARCH]`
2.23.16 **Trap:** every one of these analyses is distorted by whole-repo reformats, mass renames,
        vendored code and squash-merges. State the distortion before quoting the number. `[TRAP]`

*(16 leaves)*

## §2.24 Repository health and maintenance in practice

2.24.1 The health metrics worth tracking: object count, pack count, loose object count, ref count,
       repository size on disk, clone time, `git status` time, largest blob. `[NUM]`
2.24.2 `git count-objects -vH`, `git repo structure`, `git repo info`, and what a healthy set of
       numbers looks like for a 5-year Java service repository. `[NUM]` `[RESEARCH]`
2.24.3 `git gc` versus `git gc --aggressive` versus `git repack -adf --window=250 --depth=50` versus
       `git maintenance run`. What each actually does and when `--aggressive` is a waste of hours.
       `[TRAP]` `[NUM]`
2.24.4 `gc.auto = 6700` (loose objects), `gc.autoPackLimit = 50` (packs), `gc.autoDetach = true`,
       `gc.bigPackThreshold` (default disabled), `gc.aggressiveWindow = 250`,
       `gc.aggressiveDepth = 50`, `gc.pruneExpire = 2.weeks.ago`. Every one by name and default.
       `[NUM]` `[CFG]` `[RESEARCH]`
2.24.5 Why `gc.pruneExpire` has a two-week grace period: a concurrent process may hold a reference to
       an object it has not yet linked into a ref, and pruning it would corrupt the repository.
       `--prune=now` removes that safety. `[PROVE]` `[TRAP]` `[RESEARCH]`
2.24.6 **Cruft packs** (`gc.cruftPacks = true` by default, `gc.maxCruftSize`, `--expire-to=<dir>`):
       unreachable objects go into a pack with a `.mtimes` file recording per-object mtimes, instead
       of exploding into millions of loose files. `[NUM]` `[CFG]` `[RESEARCH]` `[VERSION-TRAP]`
2.24.7 `git prune`, `git prune-packed`, `git repack -d`, `git multi-pack-index write --bitmap`,
       and the `.keep` file that pins a pack. `[CMD]`
2.24.8 The `.git/gc.log` file and the "Auto packing the repository ... gc will not be run again" /
       "There are too many unreachable loose objects" warnings, and what to actually do about them.
       `[RECOVER]`
2.24.9 Geometric repacking (2.52 task, 2.54 default strategy): maintain a geometric progression of
       packs by object count so that repacking is amortised, instead of a periodic all-into-one
       repack that rewrites the whole repository. `repack.midxSplitFactor`,
       `repack.midxNewLayerThreshold`, `--geometric=2`. `[PROVE]` `[RESEARCH]`
2.24.10 Incremental MIDX repacking (2.55): `git repack --write-midx=incremental`, append-only MIDX
        chains. Measured bitmap generation 612 s → 294 s. `[NUM]` `[RESEARCH]`
2.24.11 Path-walk repacking (2.51 `--path-walk`, extended with filters in 2.55): collect objects in
        path order rather than revision order, producing ~16% smaller packs for blob-less workflows.
        `[NUM]` `[RESEARCH]`
2.24.12 Cruft-free MIDX (2.51, `repack.MIDXMustContainCruft`): 38% smaller MIDX, 35% faster writes,
        ~5% faster reads. `[NUM]` `[RESEARCH]`
2.24.13 Reachability bitmaps: `repack -b`, `pack.writeBitmaps`, pseudo-merge bitmaps (nearly 20x
        traversal speedup in 2.55), and why bitmaps matter for `clone`/`fetch` on the server rather
        than for you. `[NUM]` `[RESEARCH]`
2.24.14 What to run on a developer laptop: `git maintenance register` once, and nothing else ever.
2.24.15 What a Git host runs and why your `gc` is not the same problem: fork networks, alternates,
        many concurrent readers, and the need to never block a fetch. `[X-REF 22]`
2.24.16 A repository-health CI job: fail if the repo exceeds a size budget, if a blob exceeds a
        threshold, or if ref count crosses a line. `[BUILD]`

*(16 leaves)*

## §2.25 Ergonomics, tooling, and the shell

2.25.1 The prompt: `__git_ps1`, `git-prompt.sh`, starship, oh-my-zsh's `git` plugin — showing branch,
       dirty state, ahead/behind, and operation-in-progress. What each costs per prompt render on a
       large repository. `[NUM]` `[TRAP]`
2.25.2 Completion: `git-completion.bash`/`zsh`, and completing branch names, remotes and config keys.
2.25.3 `column.ui=auto`, `color.ui`, `color.diff.*`, `diff.colorMoved=zebra`,
       `diff.colorMovedWS=allow-indentation-change`, `core.pager` and `less` flags
       (`LESS=FRX`), `pager.<cmd>`, `--no-pager`. `[CFG]`
2.25.4 `delta`, `diff-so-fancy`, `difftastic` (syntax-aware structural diff) as pagers/diff drivers,
       and `diff.external`. `[RESEARCH]`
2.25.5 TUIs and GUIs worth naming: `tig`, `lazygit`, `gitui`, GitKraken, Fork, Sublime Merge,
       GitButler, and IntelliJ's built-in Git panel — what each is good at.
2.25.6 `gh` CLI: `gh pr create/checkout/view/diff/review/merge/status`, `gh run watch`,
       `gh api`, `gh pr checkout <n>` (which fetches `refs/pull/<n>/head`), and `gh stack`.
       `[CMD]` `[RESEARCH]`
2.25.7 `glab` for GitLab, and the equivalent verbs.
2.25.8 `help.autocorrect` (`0`, `1`, `immediate`, `never`, `prompt`) and `help.autoCorrect` typo
       handling. `[CFG]`
2.25.9 `GIT_TRACE=1`, `GIT_TRACE_PERFORMANCE=1`, `GIT_TRACE_PACKET=1`, `GIT_TRACE_SETUP=1`,
       `GIT_TRACE2_EVENT`, `GIT_TRACE2_PERF`, `trace2.*` config — how you find out why a Git command
       is slow. `[CMD]` `[X-REF 20]`
2.25.10 `git -c <key>=<value> <cmd>` for a one-shot override, and `git --no-optional-locks status`
        for a status that will not fight your IDE for `index.lock`. `[CMD]` `[TRAP]`
2.25.11 IDE integration traps: IntelliJ and VS Code both run background Git commands that take
        `index.lock`, both have their own conflict resolvers with their own "ours"/"theirs"
        labelling, and IntelliJ's Local History is a genuine safety net that is not Git. `[TRAP]`
2.25.12 `git config --global core.editor` and `GIT_EDITOR` for the commit message, versus
        `GIT_SEQUENCE_EDITOR` for the rebase todo. Two different editors, one common confusion.
        `[TRAP]`
2.25.13 A `.gitconfig` the bible ships in full, annotated line by line, combining §1.12.17's aliases
        and §1.12.18's settings. `[BUILD]`

*(13 leaves)*

---

# PART 3 — UNDER THE HOOD

## §3.1 Loose object storage

3.1.1 A loose object is the byte string `<type> <size>\0<content>`, zlib-deflated, written to
      `.git/objects/<first-2-hex>/<remaining-38-hex>`. `[HEX]` `[SOURCE]`
3.1.2 A hexdump walkthrough: `git hash-object -w` a 12-byte file, then
      `xxd .git/objects/xx/yyy...` and decompress it with `zlib-flate -uncompress` or
      `python3 -c 'import zlib,sys;sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))'`
      to see the header and the content. Read every byte. `[HEX]` `[BUILD]`
3.1.3 Compression level: `core.compression` (default -1 = zlib default = 6),
      `core.looseCompression`, `pack.compression`. The CPU/size trade-off and when it matters.
      `[CFG]` `[NUM]`
3.1.4 Objects are written to a temp file and **renamed** into place — an atomic operation on POSIX
      filesystems, which is why a crash mid-write leaves no half-object (but a crash mid-*rename* on
      some filesystems leaves a zero-length file; §2.21.16). `[PROVE]`
3.1.5 Objects are **immutable and never overwritten**. If the target file exists, Git skips the
      write. This is why a hash collision cannot silently replace an object. `[PROVE]`
3.1.6 File permissions and `core.sharedRepository`; the read-only bit on object files.
3.1.7 `core.fsync`, `core.fsyncMethod` (`fsync`, `writeout-only`, `batch`), `core.fsyncObjectFiles`
      (deprecated) — the durability-versus-speed knob, and why `git` on a laptop and `git` on a
      hosting server want different values. `[CFG]` `[RESEARCH]`
3.1.8 The two-character fan-out revisited quantitatively: 256 directories, so a 1M-object repository
      averages ~3900 files per directory before packing. Beyond that, `readdir` and inode pressure
      dominate, which is the direct motivation for packfiles. `[NUM]` `[PROVE]`
3.1.9 `objects/info/alternates` and the borrowed-object-store model; `GIT_ALTERNATE_OBJECT_DIRECTORIES`.
      The failure mode: the donor runs `gc`, prunes an object the borrower still references, and the
      borrower is now corrupt. `[TRAP]` `[PROVE]`
3.1.10 `git unpack-objects` and `git prune-packed` as the two directions between loose and packed.
3.1.11 Why loose objects exist at all when packs are better: writing a pack for one new commit would
       be absurd. Loose is the write path; packed is the storage and transfer path. `[PROVE]`

*(11 leaves)*

## §3.2 Packfiles and delta compression

3.2.1 The `.pack` header: 4-byte signature `PACK`, 4-byte version (2 or 3; Git writes 2), 4-byte
      object count, all network byte order. Then the objects. Then a trailing repository-hash
      checksum over everything preceding. `[HEX]` `[SOURCE]` `[NUM]`
3.2.2 The per-object header: a variable-length encoding carrying a **3-bit type** and a size —
      4 size bits in the first byte, then 7 per continuation byte. `[SOURCE]` `[NUM]` `[PROVE]`
3.2.3 The type numbers, all of them: 1 `OBJ_COMMIT`, 2 `OBJ_TREE`, 3 `OBJ_BLOB`, 4 `OBJ_TAG`,
      **5 reserved/invalid**, 6 `OBJ_OFS_DELTA`, 7 `OBJ_REF_DELTA`, 0 invalid. `[NUM]` `[SOURCE]`
3.2.4 The varint encoding used for sizes: 7 bits of payload per byte, MSB = "more follows", later
      bytes more significant. Worked example: `0x7F` = 127; two bytes reach 16383. `[PROVE]`
      `[NUM]` `[SOURCE]`
3.2.5 `OBJ_OFS_DELTA` stores a **negative relative offset** to the base object earlier in the same
      pack — compact, and self-contained. `OBJ_REF_DELTA` stores the base's full OID, which allows
      the base to be outside the pack. `[PROVE]` `[SOURCE]`
3.2.6 **Thin packs**: `REF_DELTA` bases outside the pack, used on the wire during `fetch`/`push`
      because both sides already have the base. `index-pack --fix-thin` completes them on receipt.
      `[PROVE]` `[RESEARCH]`
3.2.7 The delta payload format: base size (varint), reconstructed size (varint), then a sequence of
      instructions. `[SOURCE]`
3.2.8 **Copy instruction** (MSB = 1): the low 7 bits are a presence bitmap selecting which of 4
      offset bytes and 3 size bytes follow, little-endian, omitted bytes defaulting to 0; a size of
      0 means 0x10000. `[SOURCE]` `[NUM]` `[PROVE]`
3.2.9 **Insert instruction** (MSB = 0): the low 7 bits are a non-zero length, followed by that many
      literal bytes. Maximum 127 bytes per insert. `[SOURCE]` `[NUM]`
3.2.10 Instruction byte `0x00` is reserved and invalid — a validity check when writing a decoder.
       `[SOURCE]`
3.2.11 Delta chains: a delta whose base is itself a delta. `pack.depth` (default 50) caps the chain;
       reconstructing an object means walking the chain to a full base and replaying every delta.
       `[NUM]` `[CFG]` `[PROVE]`
3.2.12 **The cost model this implies:** deeper chains = smaller pack, slower read. The default 50 is
       a deliberate midpoint; `--aggressive` uses 250/50 window/depth. `[NUM]` `[PROVE]`
3.2.13 Delta *selection*: `pack.window` (default 10) — objects are sorted by type, then path name
       hash, then size descending, and each is compared against the previous `window` objects.
       `pack.windowMemory`. `[NUM]` `[CFG]` `[PROVE]`
3.2.14 **Deltas go from larger to smaller** (the newer, larger object is usually the base and the
       older one the delta), because history is usually read newest-first and you want the recent
       object cheap. This is counterintuitive and worth stating. `[PROVE]` `[TRAP]`
3.2.15 The name-hash heuristic: objects with similar path names are likely to delta well.
       `pack.useSparse`, name-hash v2, and the 2.51 `--path-walk` alternative that groups by actual
       path rather than by hash. `[RESEARCH]`
3.2.16 Why deltas cross file boundaries: Git deltas *objects*, not files, so a renamed file deltas
       perfectly against its old self. This is deduplication that a per-file VCS cannot do.
       `[PROVE]`
3.2.17 What does **not** delta: already-compressed content (JPEG, PNG, ZIP, JAR, class files in a
       jar), encrypted content, and anything marked `-delta` in `.gitattributes`. `[TRAP]`
3.2.18 `core.bigFileThreshold` (default 512 MiB): files above it are stored undeltified and not
       loaded whole into memory. `[NUM]` `[CFG]`
3.2.19 `git verify-pack -v <idx>` output read column by column: OID, type, size, size-in-pack,
       offset, depth, base-OID. The sort-by-size-in-pack recipe. `[HEX]` `[CMD]`
3.2.20 `git pack-objects` and `git index-pack` as the two halves; `--stdout`, `--revs`, `--thin`,
       `--delta-base-offset`, `--max-pack-size`, `--threads`. `[CMD]`
3.2.21 `pack.threads`, `pack.deltaCacheSize`, `pack.deltaCacheLimit`, `pack.packSizeLimit`,
       `pack.islandCore`/`pack.island` (delta islands, used by hosts to stop forks deltaing against
       each other). `[CFG]` `[RESEARCH]`
3.2.22 A worked packing arithmetic example: 200 versions of a 40 KB Java file, ~30 changed lines
       each. Loose: 200 × ~12 KB compressed ≈ 2.4 MB. Packed with deltas: one full base plus 199
       deltas of ~600 bytes ≈ 130 KB. Show the numbers. `[NUM]` `[PROVE]`

*(22 leaves)*

## §3.3 Pack indexes, reverse indexes, MIDX, and bitmaps

3.3.1 `.idx` **v1**: a 256-entry fan-out table (4 bytes each, cumulative count of objects whose first
      OID byte ≤ N), then 24-byte entries of 4-byte offset + OID, then the pack checksum and the
      index checksum. `[SOURCE]` `[NUM]`
3.3.2 `.idx` **v2**: magic `\377tOc` (`0xff744f63`), version 4-byte 2, the fan-out, then four
      parallel tables — sorted OIDs, CRC32 per object, 4-byte offsets with the MSB flagging a large
      offset, and an 8-byte large-offset table — then the two checksums. `[SOURCE]` `[NUM]` `[HEX]`
3.3.3 Why v2 exists: v1's 4-byte offsets cap a pack at 4 GiB, and v1 has no per-object CRC so a
      corrupt object cannot be detected without inflating it. `[PROVE]`
3.3.4 The lookup algorithm: fan-out gives the range for the first byte in O(1), then binary search
      within it — ~log2(objects/256) comparisons. Work the number for 5M objects. `[PROVE]` `[NUM]`
3.3.5 The CRC32 is computed over the *packed* representation (header + base ref + compressed data),
      which lets `repack` copy an object between packs without inflating it and still verify it.
      `[PROVE]` `[SOURCE]`
3.3.6 `.rev` reverse index: magic `RIDX` (`0x52494458`), version 1, hash-function byte (1 = SHA-1,
      2 = SHA-256), then index positions sorted by pack offset, then the two checksums. Answers
      "which object is at this offset", needed by `OFS_DELTA` resolution and by `verify-pack`.
      `[SOURCE]` `[NUM]`
3.3.7 `pack.writeReverseIndex`, and the in-memory alternative Git used before `.rev` existed.
      `[CFG]`
3.3.8 **MIDX** (`.git/objects/pack/multi-pack-index`): magic `MIDX`, 1-byte version (1 or 2), 1-byte
      OID version, 1-byte chunk count, 1-byte base-MIDX count, 4-byte pack count, then a chunk
      lookup table of (C+1) × 12 bytes, then chunks. `[SOURCE]` `[NUM]`
3.3.9 The MIDX chunk IDs by name: `PNAM` (pack names), `OIDF` (OID fan-out), `OIDL` (OID lookup),
      `OOFF` (object offsets), `LOFF` (large offsets), `RIDX` (reverse index), `BTMP` (bitmapped
      packs). `[SOURCE]` `[RESEARCH]`
3.3.10 What MIDX solves: with N packs, an object lookup is N binary searches. MIDX makes it one.
       This is what makes incremental repacking viable. `[PROVE]`
3.3.11 MIDX compaction and layer counts (2.54), and incremental append-only MIDX chains with
       `repack.midxSplitFactor` and `repack.midxNewLayerThreshold` (2.55). `[RESEARCH]`
3.3.12 **Reachability bitmaps** (`.bitmap`): for a set of selected commits, an EWAH-compressed
       bitmap over the pack's object positions marking everything reachable. Turns the
       "what do I need to send" traversal into bitwise OR/AND-NOT. `[PROVE]` `[RESEARCH]`
3.3.13 The four bitmaps per selected commit (commits, trees, blobs, tags) and the XOR/delta encoding
       between them.
3.3.14 `pack.writeBitmaps`, `repack -b`, `pack.writeBitmapHashCache`,
       `pack.writeBitmapLookupTable`, and MIDX bitmaps (`multi-pack-index write --bitmap`).
       `[CFG]`
3.3.15 **Pseudo-merge bitmaps**: a synthetic bitmap covering a group of refs, so a repository with
       500k refs does not need 500k bitmaps. Nearly **20x** traversal speedup with reduced
       generation overhead in 2.55. `[NUM]` `[RESEARCH]`
3.3.16 Why bitmaps are a *server* optimisation: they pay off on `clone` and `fetch` negotiation,
       which is a hosting workload, not a laptop workload. `[PROVE]`
3.3.17 The `.mtimes` file that accompanies a cruft pack: per-object mtimes so unreachable objects can
       still be expired by age while living inside a pack. `[PROVE]` `[RESEARCH]`
3.3.18 The `.keep` file: a pack marked `.keep` is never repacked or deleted. Used by
       `receive-pack` during a push to avoid racing with `gc`. `[PROVE]`
3.3.19 The full set of files a pack can have: `.pack`, `.idx`, `.rev`, `.bitmap`, `.keep`,
       `.mtimes`, `.promisor`. Naming all seven is a fluency signal. `[NUM]`

*(19 leaves)*

## §3.4 The index file format

3.4.1 Header: 4-byte signature `DIRC` ("dircache"), 4-byte version (2, 3, or 4), 4-byte entry count.
      Network byte order throughout. `[SOURCE]` `[HEX]` `[NUM]`
3.4.2 Entry layout in order: `ctime` seconds + nanoseconds (64 bits), `mtime` seconds + nanoseconds
      (64 bits), `dev`, `ino`, `mode`, `uid`, `gid`, `size` (32-bit, truncated), the object name
      (20 or 32 bytes), 16-bit flags, then (v3+) 16-bit extended flags, then the NUL-terminated
      path. `[SOURCE]` `[NUM]`
3.4.3 The 16-bit flags field decomposed: 1 bit assume-valid, 1 bit extended, **2 bits stage**,
      12 bits name length (0xFFF meaning "≥ 4095"). `[SOURCE]` `[NUM]` `[PROVE]`
3.4.4 The extended flags (v3+): `skip-worktree`, `intent-to-add`, and reserved bits. `[SOURCE]`
3.4.5 Version differences: v2 baseline; **v3** adds extended flags; **v4** adds path prefix
      compression (each entry stores how many leading bytes it shares with the previous path) and
      drops the padding. `index.version`. `[NUM]` `[CFG]` `[SOURCE]`
3.4.6 v2/v3 entries are NUL-padded to a multiple of 8 bytes; v4 is not. This is why v4 is smaller on
      a deep tree. `[PROVE]` `[NUM]`
3.4.7 Entries are sorted by path in **memcmp order**, then by stage. Binary search is therefore
      possible on the index. `[PROVE]`
3.4.8 The stage numbers again, at the bit level: 0 normal, 1 base, 2 ours, 3 theirs. Four entries can
      exist for one path during a conflict — or three, or two, depending on the conflict kind.
      `[NUM]` `[PROVE]`
3.4.9 `size` is a 32-bit truncation of the file size, so files ≥ 4 GiB compare by the low 32 bits.
      A real (if exotic) source of missed changes. `[TRAP]` `[NUM]`
3.4.10 The extension inventory by 4-byte signature: `TREE` (cache tree), `REUC` (resolve-undo),
       `link` (split index), `UNTR` (untracked cache), `FSMN` (fsmonitor), `EOIE` (end of index
       entry), `IEOT` (index entry offset table, for multithreaded loading), `sdir` (sparse
       directories). `[SOURCE]` `[RESEARCH]`
3.4.11 Uppercase first byte = optional extension (skippable by an older Git); lowercase = mandatory
       (an older Git must refuse). An elegant forward-compatibility rule worth calling out.
       `[PROVE]` `[SOURCE]`
3.4.12 The `TREE` cache-tree extension in detail: per-directory `<path>\0<entry_count> <subtree_count>\n<oid>`,
       with `entry_count = -1` meaning invalid. `git write-tree` reuses valid entries and only
       rebuilds invalidated subtrees. `[SOURCE]` `[PROVE]`
3.4.13 What invalidates a cache-tree entry: any `git add`, `rm` or index write touching a path in
       that directory, invalidating it and every ancestor up to the root. `[PROVE]`
3.4.14 `git ls-files --debug` and `test-tool dump-cache-tree` for reading it; the observable effect
       is `git commit` time on a large repository. `[NUM]`
3.4.15 `REUC` resolve-undo: after you resolve a conflict, the three stages are preserved so
       `git checkout -m` can recreate the conflict. This is how "undo my resolution" works.
       `[PROVE]` `[RESEARCH]`
3.4.16 The **split index** (`core.splitIndex`, `link` extension, `splitIndex.maxPercentChange`,
       `splitIndex.sharedIndexExpire`): a shared base index plus a small delta, so writing the index
       is O(changes) not O(files). `[CFG]` `[RESEARCH]`
3.4.17 The **untracked cache** (`UNTR`, `core.untrackedCache`): caches the untracked-file listing per
       directory with stat data, so `git status` skips `readdir` on unchanged directories. Requires
       a filesystem whose directory mtime is reliable — `git update-index --test-untracked-cache`.
       `[CFG]` `[PROVE]`
3.4.18 The **fsmonitor** extension (`FSMN`) and how the daemon's token is stored in the index so the
       next `status` asks "what changed since token T" instead of scanning. `[PROVE]`
3.4.19 `EOIE` and `IEOT` exist purely to enable **multithreaded index loading**: `IEOT` gives block
       offsets so N threads can parse N regions, `EOIE` lets a reader find the extensions without
       parsing all entries. `[PROVE]` `[RESEARCH]`
3.4.20 The trailing checksum over the whole file, and `index.skipHash` (2.40+) which skips computing
       it for speed on huge indexes. `[CFG]` `[RESEARCH]`
3.4.21 Index size arithmetic: ~80–100 bytes per entry plus the path. For 2M files that is ~180 MB —
       which is exactly the sparse-index motivating number from §2.11.8. `[NUM]` `[PROVE]`
3.4.22 The `sdir` sparse-directory extension and how a sparse index stores a directory entry with a
       tree OID and mode `040000` instead of its contents. `[RESEARCH]`

*(22 leaves)*

## §3.5 Ref backends in depth

3.5.1 The `files` backend's write protocol: create `<ref>.lock`, write, `fsync`, rename. Atomic per
      ref; **not** atomic across refs, which is why a multi-ref update can be half-applied.
      `[PROVE]` `[TRAP]`
3.5.2 `git update-ref --stdin` with `start`/`prepare`/`commit`/`abort` and the
      `update`/`create`/`delete`/`verify` verbs — the closest the `files` backend gets to a
      transaction. `[CMD]` `[SOURCE]`
3.5.3 Deleting a packed ref requires rewriting `packed-refs` in full — O(all refs) for one deletion.
      `[PROVE]` `[NUM]`
3.5.4 `packed-refs` peel lines (`^<oid>`) and the `fully-peeled`/`peeled` header traits: they let a
      reader resolve an annotated tag to its commit without reading the tag object. `[PROVE]`
      `[SOURCE]`
3.5.5 **reftable** file layout: a 24–28-byte header, then `ref_block`s, `ref_index`, `obj_block`s,
      `obj_index`, `log_block`s, `log_index`, and a footer. `[SOURCE]` `[RESEARCH]`
3.5.6 Block type bytes: `'r'` ref blocks, `'i'` index blocks, `'o'` object-to-ref blocks, `'g'`
      zlib-deflated log blocks. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.7 Prefix compression inside a block: store `prefix_length` plus the suffix.
      `refs/heads/master` → `refs/heads/main` encodes as `prefix_length=11, suffix="ain"`.
      `[PROVE]` `[HEX]` `[RESEARCH]`
3.5.8 **Restart points** every 16 records (configurable): a full key with no prefix compression, so
      binary search can land without decompressing the whole chain. The classic
      compression-versus-random-access trade. `[PROVE]` `[NUM]` `[RESEARCH]`
3.5.9 The reftable varint: `val = buf[ptr] & 0x7f; while (buf[ptr] & 0x80) { ptr++; val = ((val+1)
      << 7) | (buf[ptr] & 0x7f); }` — note the `+1`, which removes redundant encodings.
      `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.5.10 The **table stack**: `$GIT_DIR/reftable/tables.list` naming files like
       `00000001-00000001-<random>.ref`, ordered oldest to newest, later tables shadowing earlier
       ones. `[SOURCE]` `[HEX]` `[RESEARCH]`
3.5.11 The transaction protocol: lock `tables.list.lock`, read the stack, compute
       `update_index = max + 1`, write one new table containing **all** refs and logs in the
       transaction, append it atomically to `tables.list`, unlock. Atomic multi-ref update in
       O(size of update). `[PROVE]` `[RESEARCH]`
3.5.12 The `update_index` is what lets you later ask "which refs moved together" — a property
       `packed-refs` simply cannot express. `[PROVE]` `[RESEARCH]`
3.5.13 Log records: key is `ref_name '\0' reverse_int64(update_index)` so recent entries sort
       **first**, making `main@{4}` a forward scan. Value is old_id, new_id, committer identity,
       timestamp, tz, message. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.5.14 Deletion encoding: `new_id = 0` is a deletion tombstone; `old_id = 0` is a creation.
       Tombstones are what make shadowing work without rewriting lower tables. `[PROVE]`
       `[RESEARCH]`
3.5.15 **Compaction**: merge-join a contiguous range of tables, keep the newest value per key, drop
       tombstoned refs not present in lower tables, and carry min/max `update_index` forward.
       Replace the range in `tables.list` with one file. `[PROVE]` `[RESEARCH]`
3.5.16 The measured wins again, with the numbers, and the argument for why the 12,000x cold-lookup
       figure is real rather than a benchmark artefact: `packed-refs` requires reading and parsing a
       62 MB file to answer one question. `[NUM]` `[PROVE]` `[RESEARCH]`
3.5.17 Migration: `git refs migrate --ref-format=reftable`, what it does to reflogs, and what tooling
       breaks (anything that reads `.git/refs/` or `.git/packed-refs` directly — including some
       scripts, some CI images, older libgit2/JGit). `[CMD]` `[TRAP]` `[RESEARCH]`
3.5.18 Why hosts care more than you do: 866k refs on Android, fork networks, and `push` latency
       dominated by ref updates. `[X-REF 22]`

*(18 leaves)*

## §3.6 Reflog format and semantics

3.6.1 The line format byte by byte: `<40-hex-old> <40-hex-new> <name> <email> <unix-ts> <±HHMM>\t<message>\n`.
      `[HEX]` `[SOURCE]`
3.6.2 The message vocabulary and which command writes each: `commit:`, `commit (initial):`,
      `commit (amend):`, `commit (merge):`, `checkout: moving from X to Y`, `reset: moving to X`,
      `merge X: Fast-forward`, `merge X: Merge made by the 'ort' strategy`, `rebase (start)`,
      `rebase (pick)`, `rebase (finish)`, `cherry-pick`, `revert`, `pull:`, `clone: from <url>`,
      `branch: Created from`, `update by push`. Reading these is how you reconstruct what someone
      did. `[SOURCE]` `[NUM]`
3.6.3 `core.logAllRefUpdates`: `true` (default with a worktree — logs `refs/heads`, `refs/remotes`,
      `refs/notes`, `HEAD`), `false`, `always` (log every ref including `refs/tags`). `[CFG]`
      `[NUM]`
3.6.4 A bare repository defaults to `false`, which is the whole reason "the server lost it" is
      possible. Setting `core.logAllRefUpdates=true` on a bare mirror is a cheap insurance policy.
      `[PROVE]` `[RECOVER]`
3.6.5 `HEAD@{n}` resolution walks `.git/logs/HEAD` backwards n entries; `HEAD@{<date>}` finds the
      first entry at or before that timestamp and warns if the log does not go back that far.
      `[PROVE]`
3.6.6 `git reflog expire --expire=<time> --expire-unreachable=<time> --all --rewrite --updateref
      --stale-fix --dry-run`. What `--rewrite` and `--stale-fix` do. `[CMD]`
3.6.7 The interaction with `gc`: reflog entries are **GC roots**. An object referenced only by a
      reflog entry survives until that entry expires. This is exactly why recovery works and why
      `reflog expire --expire=now --all` before `gc --prune=now` is the "really delete it"
      incantation. `[PROVE]`
3.6.8 Reflog entries are per-ref *and* per-worktree for `HEAD`, so a commit made in another worktree
      is in that worktree's `HEAD` log, not yours — the exact case `fsck --lost-found` covers.
      `[TRAP]` `[PROVE]`
3.6.9 Reflogs are **not** transferred by clone, fetch or push. Ever. Your safety net does not travel.
      `[TRAP]` `[PROVE]`
3.6.10 Under reftable, reflogs are log blocks in the same stack, zlib-compressed and grouped by ref
       name — 34x smaller on Android. `[NUM]` `[RESEARCH]`
3.6.11 Building an audit trail that *does* survive: server-side `reference-transaction` hook writing
       to a durable log, or the host's own audit log. This is the correct answer to "how would you
       detect a malicious force-push". `[BUILD]` `[X-REF 13]`

*(11 leaves)*

## §3.7 Diff algorithms

3.7.1 The diff problem stated formally: find a minimal edit script transforming sequence A into
      sequence B, where the atoms are lines. Equivalent to the longest common subsequence problem.
      `[PROVE]`
3.7.2 **Myers** (1986), the default: an O(ND) greedy algorithm walking a diagonal frontier in an
      edit graph, where N = total length and D = edit distance. Explain the edit graph, the
      "furthest reaching D-path on diagonal k" recurrence, and why it is fast when the files are
      similar. `[PROVE]` `[SOURCE]`
3.7.3 Myers with the linear-space refinement (Hirschberg-style divide and conquer) — O(N) space
      instead of O(ND). `[PROVE]`
3.7.4 `--minimal`: spend extra time to guarantee the smallest possible diff. Exponential worst case,
      hence not the default. `[PROVE]`
3.7.5 **Patience diff**: match only lines that are **unique in both files**, take the longest
      increasing subsequence of those matches, and recurse between them. Produces far better output
      when a block was moved or a brace-only line would otherwise anchor the match. `[PROVE]`
3.7.6 The canonical patience-wins example: adding a function above an existing one, where Myers
      aligns the closing braces and produces a diff that reads as if the wrong function was added.
      Show both outputs. `[PROVE]` `[TRAP]`
3.7.7 **Histogram diff**: a patience variant that also handles non-unique lines by bucketing lines by
      occurrence count and preferring low-occurrence anchors. Faster than patience, similar quality;
      it is what `ort` uses for merges. `[PROVE]` `[RESEARCH]`
3.7.8 `diff.algorithm` (`myers`, `minimal`, `patience`, `histogram`), `--diff-algorithm=`, per-path
      `[diff "<name>"] algorithm = histogram` in config + `.gitattributes`. The recommendation:
      `diff.algorithm=histogram` globally. `[CFG]` `[RESEARCH]`
3.7.9 The xdiff library: Git's vendored, modified libxdiff. `xdl_diff`, the hash-and-bucket
      preprocessing, and heuristics like `xdl_change_compact` (slide hunks to the most "natural"
      position). 2.52 shipped multiple xdiff optimisations. `[SOURCE]` `[RESEARCH]`
3.7.10 The **indent heuristic** (`diff.indentHeuristic`, on by default since 2.14): among equally
       valid hunk placements, prefer the one whose boundaries have less indentation and more blank
       lines. This is why Git's diffs read better than `diff -u`'s. `[CFG]` `[PROVE]`
3.7.11 `--anchored=<text>` to force a line to be treated as a match anchor.
3.7.12 `--word-diff[=plain|color|porcelain]` and `--word-diff-regex`; `--color-words`. The atom
       becomes a word instead of a line. `[PROVE]`
3.7.13 `--color-moved=(no|default|plain|blocks|zebra|dimmed-zebra)` and
       `--color-moved-ws=(ignore-space-at-eol|ignore-space-change|ignore-all-space|allow-indentation-change)`.
       The moved-block detection is a second pass over the diff, matching removed blocks against
       added blocks. `[PROVE]` `[CFG]`
3.7.14 Hunk headers: the `@@ -a,b +c,d @@ <function context>` format read field by field, and
       `xfuncname` / the built-in language patterns (java, kotlin, python, rust, golang, cpp,
       csharp, php, ruby, css, html, markdown, tex, …) that supply the function context.
       `[SOURCE]` `[NUM]` `[RESEARCH]`
3.7.15 Whitespace handling: `-w`, `-b`, `--ignore-blank-lines`, `--ignore-space-at-eol`,
       `core.whitespace` error classes (`blank-at-eol`, `space-before-tab`, `indent-with-non-tab`,
       `tab-in-indent`, `blank-at-eof`, `trailing-space`, `cr-at-eol`, `tabwidth=<n>`),
       `apply.whitespace`, `git diff --check`. `[CFG]` `[NUM]`
3.7.16 Binary detection: a NUL byte in the first 8000 bytes, or `-diff` in `.gitattributes`, or size
       ≥ `core.bigFileThreshold`. `--binary` to produce an appliable binary patch (base85-encoded
       delta or literal). `[NUM]` `[PROVE]`
3.7.17 `textconv` and `cachetextconv` (with the cache in `refs/notes/textconv/<driver>`) for
       diffing PDFs, images or class files as text. `[RESEARCH]`
3.7.18 `difftastic` and other structural (AST-aware) diff tools: they change the *atom* from a line
       to a syntax node, which is a genuinely different algorithm and produces genuinely better
       diffs for reformatted code. `[RESEARCH]`
3.7.19 The 2.54 histogram fix: region re-diffing improved output quality. Cite it as evidence that
       diff quality is still an active area. `[RESEARCH]`

*(19 leaves)*

## §3.8 Rename and copy detection

3.8.1 Renames are **not stored**. They are inferred at diff time, every time, from content
      similarity. This is a direct consequence of §1.1.5. `[PROVE]`
3.8.2 Exact rename detection: a delete and an add with **identical blob OIDs** is an unambiguous
      rename, found in O(n) by hashing. This is the cheap pass and it runs first. `[PROVE]`
3.8.3 Inexact rename detection: for the remaining deletes × adds, compute a similarity score. The
      matrix is O(deletes × adds), which is why there is a limit. `[PROVE]` `[NUM]`
3.8.4 The similarity metric: Git hashes fixed-size chunks of each blob into a table of
      (hash, count) pairs and computes `similarity = 2 × common / (sizeA + sizeB)` — **not** a line
      diff. Cheap, order-insensitive, and the reason a reordered file still scores high. `[PROVE]`
      `[SOURCE]`
3.8.5 The default threshold is **50%** (`-M50%`), settable with `-M<n>`, `--find-renames=<n>`.
      `diff.renames` (`true` by default since 2.9, `copies`, `false`). `[NUM]` `[CFG]`
      `[VERSION-TRAP]`
3.8.6 `diff.renameLimit` and `merge.renameLimit`: above this many candidate paths, Git **gives up
      silently** and reports add/delete pairs. The warning is easy to miss and the consequence — a
      merge that conflicts on a whole file instead of merging a rename — is severe. `[TRAP]` `[NUM]`
      `[CFG]`
3.8.7 Copy detection: `-C` (find copies among modified files), `-C -C` / `--find-copies-harder`
      (search all files, expensive). Off by default because the cost is quadratic in tree size.
      `[NUM]`
3.8.8 `--break-rewrites` / `-B[<n>][/<m>]`: split a heavily-rewritten file into a delete+add so it
      becomes a rename candidate for something else. The flag nobody knows and the one that fixes
      "Git thinks I modified A when I actually replaced A and moved its content to B". `[PROVE]`
      `[TRAP]`
3.8.9 `--diff-filter=R` and reading the `R096` / `C085` score in `--name-status` output.
      `[NUM]` `[HEX]`
3.8.10 Rename detection in **merges** matters more than in diffs: if one side renames and the other
       modifies, failing to detect the rename produces a modify/delete conflict and silently loses
       the modification if you resolve carelessly. `[PROVE]` `[TRAP]`
3.8.11 **Directory rename detection** in `ort` (`merge.directoryRenames`): if ≥ some fraction of a
       directory's files moved to a new directory, new files added to the old directory on the other
       side are moved too. `conflict` mode reports it instead of guessing. `[PROVE]` `[CFG]`
       `[RESEARCH]`
3.8.12 `ort`'s rename-detection optimisations over `recursive`: skipping rename detection entirely
       when it cannot affect the result, caching rename results across the commits of a rebase, and
       trivial-directory-resolution. This is where most of ort's speedup comes from. `[PROVE]`
       `[RESEARCH]`
3.8.13 `git log --follow` uses the same machinery one commit at a time, which is why it is slow and
       why it only supports a single path. `[PROVE]` `[TRAP]`
3.8.14 The practical consequence for reviewers: a "moved a package" PR shows as thousands of
       deletions and additions unless rename detection fires. `-M`, `--color-moved`, and splitting
       the move into its own commit are the three fixes.

*(14 leaves)*

## §3.9 Three-way merge and merge-ort internals

3.9.1 The three-way merge rule at the hunk level: compare base→ours and base→theirs. If only one
      side changed a region, take it. If both changed it identically, take it. If both changed it
      differently, conflict. `[PROVE]`
3.9.2 Why the **base** is what makes this work: without it you cannot distinguish "they added" from
      "we deleted". Two-way merge is fundamentally ambiguous. `[PROVE]`
3.9.3 Finding the base: `git merge-base A B` = the lowest common ancestor in the DAG. The algorithm
      walks both sides marking reachability and takes the maximal common ancestors. `[PROVE]`
3.9.4 **Criss-cross merges** produce **multiple** merge bases, and there is no single correct one.
      Draw the classic diagram. `[PROVE]` `[NUM]`
3.9.5 The **recursive** solution (hence the name): merge the multiple bases together into a
      **virtual merge base** — recursively, since that merge may itself have multiple bases — then
      three-way merge against it. `ort` does the same thing, faster. `[PROVE]` `[RESEARCH]`
3.9.6 A virtual merge base can itself contain conflict markers, which is how you get a merge whose
      conflict includes `<<<<<<<` inside the base section. Rare, real, and confusing. `[TRAP]`
3.9.7 `merge-ort`'s architecture versus `merge-recursive`'s: ort computes entirely on in-memory
      trees and writes the result once, while recursive manipulated the index and working tree
      incrementally. That is why ort can run in a bare repository (`merge-tree`), why it is
      restartable, and why it is faster. `[PROVE]` `[RESEARCH]`
3.9.8 ort's phases: collect the three trees, detect renames (lazily), process each path (trivial
      cases short-circuited), handle directory renames, and finally write the tree. `[RESEARCH]`
3.9.9 The "trivial merge" fast paths that never touch content: identical trees, one side unchanged,
      and unmodified subtrees skipped wholesale by comparing tree OIDs. **This is the biggest
      single optimisation** — a merge of two branches touching 5 files in a 2M-file repo compares
      a handful of tree OIDs. `[PROVE]` `[NUM]`
3.9.10 Conflict *types* ort reports and their exact labels, mapping to the taxonomy in §2.4.2.
3.9.11 The file-level merge is `xdl_merge` from xdiff — the same library as diff, in three-way mode,
       with `zdiff3`/`diff3`/`merge` marker styles and `conflict-marker-size`. `[SOURCE]`
3.9.12 How `zdiff3` differs mechanically: after producing a diff3 conflict, hoist common leading and
       trailing lines out of the three sections. Show a before/after. `[PROVE]` `[RESEARCH]`
3.9.13 Rerere hooks into this at the point the conflicted file is written (§3.11).
3.9.14 `git merge-tree --write-tree` returns the tree OID plus a conflict report; the older
       `merge-tree` (pre-2.38) was a different, much less useful command. `[VERSION-TRAP]`
       `[RESEARCH]`
3.9.15 Why merge is a **tree** operation and rebase is a **patch** operation, and the observable
       consequence: rebase can succeed where merge conflicts and vice versa, because they are asking
       different questions. `[PROVE]` `[TRAP]`
3.9.16 The proof that a clean merge does not imply a correct merge: construct a two-line semantic
       conflict in QuizStakes' `FundsLedger` where both sides merge cleanly and Invariant 8 is
       violated. `[PROVE]` `[BUILD]`

*(16 leaves)*

## §3.10 The sequencer: rebase, cherry-pick, revert

3.10.1 One state machine serves `cherry-pick`, `revert`, `rebase --merge` and `rebase -i`: the
       **sequencer**. `.git/sequencer/todo`, `.git/sequencer/opts`, `.git/rebase-merge/*`.
       `[PROVE]` `[HEX]`
3.10.2 The todo file is read one instruction at a time, executed, and the executed line appended to
       `done`. That is why `--continue` can resume exactly, and why editing `git-rebase-todo`
       mid-rebase works. `[PROVE]`
3.10.3 `cherry-pick` implemented as a three-way merge: base = the commit's parent, ours = HEAD,
       theirs = the commit. **This is why "ours"/"theirs" are swapped relative to intuition**, and
       it is the same mechanism as a rebase step. `[PROVE]` `[TRAP]`
3.10.4 `revert` is the same merge with base and theirs exchanged: base = the commit, theirs = its
       parent. Symmetry worth stating explicitly. `[PROVE]`
3.10.5 The `--apply` backend: `format-patch` piped to `am`, applying a textual patch with fuzz and
       context matching rather than a three-way merge. `git am -3` falls back to three-way using the
       `index` line's blob OIDs. `[PROVE]`
3.10.6 Why `--apply` loses information: it cannot use rename detection or `-X` options, drops empty
       commits, and its "patch does not apply" failure mode is less informative than a conflict.
       `[PROVE]` `[TRAP]`
3.10.7 The `rebase.backend` history: `merge` became the default in 2.26; `--preserve-merges` was
       removed in favour of `--rebase-merges` in 2.35. `[VERSION-TRAP]`
3.10.8 `label`/`reset`/`merge`/`update-ref` todo commands and how `--rebase-merges` uses
       `refs/rewritten/<label>` (a per-worktree ref namespace) to hold intermediate tips.
       `[PROVE]` `[RESEARCH]`
3.10.9 The patch-id computation, precisely: hash the diff with whitespace normalised, context and
       line numbers ignored, and hunks sorted (`--stable`) or not (`--unstable`). This is what
       "already upstream" means. `[PROVE]` `[SOURCE]`
3.10.10 `--reapply-cherry-picks` internals: without it, rebase computes patch-ids for the upstream
        range and drops matching commits. On a large upstream range that computation is expensive,
        which is why it is skipped when the upstream is a merge base. `[PROVE]` `[NUM]`
3.10.11 `--fork-point` internals: it consults the **reflog of the upstream ref** to find where your
        branch actually diverged, even if the upstream has since been rewritten. Non-deterministic
        across machines because reflogs are local. `[PROVE]` `[TRAP]`
3.10.12 `--autosquash` internals: scan the todo for subjects starting `fixup! `/`squash! `/`amend! `
        and move each line after its target, converting `pick` to `fixup`/`squash`. Matching is by
        subject prefix or by OID. `[PROVE]`
3.10.13 `--update-refs` internals: before rebasing, record which refs point into the range; insert
        `update-ref` todo lines at the corresponding positions; on completion, update them all.
        Refs currently checked out in a worktree are skipped. `[PROVE]` `[RESEARCH]`
3.10.14 `git replay` internals: a bare-repository-safe, headless rebase that writes the new commits
        and returns ref updates on stdout for the caller to apply — atomically since 2.54.
        `[RESEARCH]`
3.10.15 `git history reword`/`split`/`fixup` internals (2.54/2.55): targeted rewrites that replay
        only the descendants of the touched commit. `reword` does not need a working tree; `split`
        and `fixup` do. `[RESEARCH]`
3.10.16 Why every rebase is a **rewrite of every descendant**: the parent OID is part of the commit's
        hash, so changing one commit changes every commit after it. Restate §1.1.7 here with the
        concrete cost: rebasing the 3rd of 40 commits creates 38 new commit objects. `[PROVE]`
        `[NUM]`

*(16 leaves)*

## §3.11 rerere internals

3.11.1 The conflict-ID computation: for each conflicted file, normalise the conflicted content
       (sort the two sides of each conflict block into a canonical order, strip the markers and
       the file-specific labels), hash it, and use the hex digest as the directory name in
       `.git/rr-cache/`. `[PROVE]` `[RESEARCH]`
3.11.2 The canonical ordering is what makes the same conflict match regardless of which branch was
       "ours" — a merge and the corresponding rebase produce the same ID. `[PROVE]`
3.11.3 `preimage` is the normalised conflicted content; `postimage` is written when you resolve and
       Git records it (at `git commit` of the merge, or at `git rebase --continue`);
       `thisimage` is the current conflict being matched. `[RESEARCH]`
3.11.4 The replay is `xdl_merge(preimage, postimage, thisimage)` — a three-way merge where the
       "base" is the old conflict and the two sides are your old resolution and the new conflict.
       Clean result → write it out. Conflict → leave the markers. `[PROVE]` `[RESEARCH]`
3.11.5 Why this survives surrounding code changes: only the conflicted region participates, and the
       three-way merge absorbs context drift. `[PROVE]`
3.11.6 Why it fails: if the conflict *shape* changes (a different number of lines, a different
       hunk boundary), the ID changes and there is no match. Silent no-op, not an error. `[TRAP]`
3.11.7 `rerere.autoUpdate` writes the resolved file **and stages it**, so a subsequent `git commit`
       records it without you ever seeing the file. The mechanism behind the §2.5.6 trap.
       `[PROVE]`
3.11.8 `git rerere diff` shows `preimage` vs the current working-tree state — i.e. what your
       resolution is about to be recorded as. Run it before committing a replayed resolution.
       `[CMD]`
3.11.9 `git rerere gc` and the `gc.rerereResolved = 60` / `gc.rerereUnresolved = 15` day thresholds,
       measured from the file mtimes in `rr-cache`. `[NUM]` `[CFG]` `[RESEARCH]`
3.11.10 Interaction with `MERGE_RR`: the file mapping conflicted paths to conflict IDs for the merge
        in progress. `[RESEARCH]`
3.11.11 rerere does not handle submodule conflicts; `git rerere remaining` exists specifically to
        report the ones it cannot track. `[RESEARCH]`
3.11.12 A `[BUILD]` exercise: construct a conflict, resolve it, inspect all three files in
        `rr-cache`, reset, recreate the conflict slightly differently, and observe whether it
        matches. `[BUILD]` `[HEX]`

*(12 leaves)*

## §3.12 commit-graph and generation numbers

3.12.1 The problem: answering "is A an ancestor of B", "what is the merge base", "sort these
       topologically" requires walking commits and parsing each commit object. On 1M commits that
       is 1M zlib inflations. `[PROVE]` `[NUM]`
3.12.2 The commit-graph file stores, per commit: the OID, the root tree OID, the commit date, and
       the parents **as integer positions** in the file rather than OIDs. Position-indexed parent
       lookup is the core speedup. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.12.3 Location: `.git/objects/info/commit-graph`, or a chain in
       `.git/objects/info/commit-graphs/graph-{hash}.graph` with `commit-graph-chain` listing the
       layers. `[RESEARCH]`
3.12.4 **Generation number v1** (topological level): root = 1, otherwise 1 + max(parent levels).
       `GENERATION_NUMBER_V1_MAX = 0x3FFFFFFF` (30 bits). `[NUM]` `[SOURCE]` `[RESEARCH]`
3.12.5 **Generation number v2** (corrected commit date): root = committer date (or 1 if zero),
       otherwise max(committer date, 1 + max(parent corrected dates)). Robust to clock skew while
       still usable as a date. `commitGraph.generationVersion = 2` is the default. `[NUM]`
       `[SOURCE]` `[RESEARCH]`
3.12.6 **The cutoff property** and its proof: if gen(A) < gen(B) then A cannot reach B. Therefore any
       traversal looking for ancestors of B can stop as soon as generation numbers fall below
       gen(B). This single inequality is what makes `merge-base` fast. `[PROVE]` `[RESEARCH]`
3.12.7 Why v1 alone is insufficient for date-based queries (`--since`), and why v2 fixes it: v1
       carries no time information, so `--since` still had to walk. `[PROVE]`
3.12.8 The mixed-chain rule: Git inspects the **topmost** layer for the generation version; if the
       top lacks corrected dates, only topological levels are used, and new layers include corrected
       dates only if the layer below has them. Consistency downward. `[PROVE]` `[RESEARCH]`
3.12.9 Chain merge policy: merge level N if `commits_in_level_N < X × commits_in_level_(N+1)` with
       default **X = 2**, or if `commits_in_level_(N+1) > C` with default **C = 64,000**. Keeps the
       layer count logarithmic. `[NUM]` `[PROVE]` `[RESEARCH]`
3.12.10 **Changed-path Bloom filters** (`--changed-paths`, `commitGraph.changedPathsVersion`): a
        per-commit Bloom filter over the paths that commit modified, so `git log -- <path>` can skip
        commits without diffing their trees. False positives cost a real diff; false negatives are
        impossible. `[PROVE]` `[CFG]` `[RESEARCH]`
3.12.11 Bloom-filter parameters: hash count, bits per entry, the maximum number of changed paths
        beyond which the filter is omitted, and version 2's fix to the murmur hash for non-ASCII
        paths. `[NUM]` `[RESEARCH]`
3.12.12 Bloom filters now support **multiple pathspec items** (2.51) and **wildcards** like
        `foo/bar/*/baz` (2.52). `[RESEARCH]`
3.12.13 Config: `core.commitGraph` (consume it), `gc.writeCommitGraph`, `fetch.writeCommitGraph`,
        and the `commit-graph` maintenance task. `[CFG]` `[RESEARCH]`
3.12.14 `git commit-graph write --reachable --changed-paths --split`, `git commit-graph verify`.
        `[CMD]`
3.12.15 **Trap:** the commit-graph is a **cache of immutable data**, so it is safe — but it only
        covers commits that existed when it was written, and it never covers commits reachable only
        from the reflog. A stale graph means new commits fall back to the slow path, not incorrect
        answers. `[TRAP]` `[PROVE]`
3.12.16 Measured effect: operations taking minutes on large repositories complete in seconds; state
        the specific ones (`log --graph`, `merge-base`, `status` on a repo with many branches,
        `log -- <path>`). `[NUM]` `[RESEARCH]`

*(16 leaves)*

## §3.13 Reachability, garbage collection, and pruning

3.13.1 The GC root set, enumerated completely: all refs (including remote-tracking, tags, notes,
       stash, replace), `HEAD` and every worktree's `HEAD`, the index (including all conflict
       stages), every reflog entry of every ref, `MERGE_HEAD`/`CHERRY_PICK_HEAD`/etc., and
       `.git/objects/info/alternates` consumers. Missing any one of these is how a GC corrupts a
       repository. `[PROVE]` `[NUM]`
3.13.2 Mark and sweep: traverse from the roots marking reachable objects, then delete unmarked ones
       older than the grace period. `[PROVE]`
3.13.3 The grace period is not politeness, it is **correctness**: a concurrent `git commit` may have
       written a blob and a tree but not yet the ref. Deleting them mid-write corrupts the
       repository. Hence `gc.pruneExpire = 2.weeks.ago`. `[PROVE]` `[TRAP]` `[RESEARCH]`
3.13.4 `--prune=now` removes that protection, which is why it appears only in the deliberate
       "actually delete the secret" recipe and never in routine maintenance. `[TRAP]`
3.13.5 `git gc` phases in order: `pack-refs`, `reflog expire`, `repack`, `prune-packed`, `prune`,
       `rerere gc`, `worktree prune`, and (if enabled) `commit-graph write`. `[NUM]`
3.13.6 `git gc --auto` triggers when loose objects exceed `gc.auto = 6700` or packs exceed
       `gc.autoPackLimit = 50`; `gc.autoDetach = true` runs it in the background so your command
       returns. `[NUM]` `[CFG]` `[RESEARCH]`
3.13.7 The estimation trick: rather than counting all loose objects, Git samples one fan-out
       directory (`objects/17/`) and multiplies by 256. A cheap approximation worth knowing.
       `[PROVE]` `[NUM]`
3.13.8 Cruft packs in detail: unreachable objects are written to a pack accompanied by a `.mtimes`
       file storing each object's mtime, so age-based expiry still works without loose files.
       `gc.cruftPacks = true` (default), `gc.maxCruftSize`, `--expire-to=<dir>`, `--max-cruft-size`.
       `[PROVE]` `[CFG]` `[RESEARCH]`
3.13.9 Why cruft packs were needed: exploding a large unreachable set into loose objects could
       produce millions of files and make the next `gc` worse than the last. The
       "`gc` made my repo slower" folklore has this as its cause. `[PROVE]` `[RESEARCH]`
3.13.10 `git prune --expire=<time> --dry-run -v`, `git prune-packed`, and why `git prune` alone is
        almost never the right command (use `gc`). `[TRAP]`
3.13.11 **Geometric repacking**, the algorithm: maintain packs whose object counts form a geometric
        progression with ratio `splitFactor` (default 2). When a new pack violates it, merge the
        smallest run that restores the progression. Amortised O(log n) rewrites per object instead
        of an all-into-one repack. `[PROVE]` `[NUM]` `[RESEARCH]`
3.13.12 Why geometric repacking matters: an all-into-one repack of a 20 GB repository rewrites 20 GB
        to absorb 2 MB of new commits. Geometric touches only the small packs. `[PROVE]` `[NUM]`
3.13.13 `git repack` flags: `-a`, `-A`, `-d`, `-l`, `-f`, `-F`, `--geometric=<n>`, `--window`,
        `--depth`, `--write-midx`, `--write-bitmap-index`, `--keep-pack`, `--filter`, `--cruft`,
        `--path-walk`. `[CMD]`
3.13.14 `-A` versus `-a`: `-A` keeps unreachable objects as loose (or cruft) so they can still be
        recovered; `-a` discards them subject to the grace period. `[PROVE]` `[TRAP]`
3.13.15 Partial-clone interaction: promisor packs (`.promisor`) must not be mixed with regular ones,
        and 2.53 made geometric repacking handle them separately to preserve the promisor marker.
        `[RESEARCH]`
3.13.16 `git fsck` internals: connectivity check from the roots, object-format validation
        (`--strict`), and the error vocabulary — `dangling`, `unreachable`, `missing`, `broken link`,
        `hash mismatch`, `null sha1`, `duplicateEntries`, `zeroPaddedFilemode`, `badTimezone`.
        `fsck.<msg-id>` to downgrade individual checks to warnings. `[SOURCE]` `[CFG]` `[NUM]`
3.13.17 `transfer.fsckObjects` and the class of attacks it defends against (malformed objects
        crafted to exploit a client parser). Off by default because it costs CPU on every fetch.
        `[X-REF 13]`
3.13.18 What a Git host does differently: never blocks readers, uses alternates and delta islands
        across a fork network, and delays GC indefinitely on repositories with live traffic.
        `[X-REF 22]`

*(18 leaves)*

## §3.14 The transfer protocols

3.14.1 The four transports: `git://` (daemon, port 9418, unauthenticated), `ssh://`, `https://`
       (smart HTTP), and `file://`/local. Dumb HTTP still exists and should not be used.
3.14.2 **pkt-line** framing: a 4-hex-digit length prefix (inclusive of the 4 bytes) followed by
       payload; `0000` = flush-pkt, `0001` = delim-pkt, `0002` = response-end-pkt. Everything in
       the protocol is pkt-lines. `[SOURCE]` `[HEX]` `[NUM]`
3.14.3 **Protocol v0/v1**: the server immediately advertises **every ref** with capabilities on the
       first line. On a repository with 500k refs this is megabytes before the client says what it
       wants. `[PROVE]` `[NUM]`
3.14.4 **Protocol v2** (default since 2.26): command-oriented and stateless-friendly. Commands
       `ls-refs` (with `ref-prefix` filtering) and `fetch`. The client asks for the refs it cares
       about, which is the fix for v0's advertisement cost. `protocol.version = 2`,
       `GIT_PROTOCOL`. `[CFG]` `[PROVE]` `[RESEARCH]`
3.14.5 Capability vocabulary worth recognising: `multi_ack`, `multi_ack_detailed`, `side-band`,
       `side-band-64k`, `thin-pack`, `ofs-delta`, `shallow`, `deepen-since`, `deepen-not`,
       `filter`, `no-progress`, `include-tag`, `allow-tip-sha1-in-want`,
       `allow-reachable-sha1-in-want`, `push-cert`, `atomic`, `object-format`, `agent`,
       `wait-for-done`, `packfile-uris`. `[SOURCE]` `[NUM]`
3.14.6 The **negotiation**: client sends `want <oid>` lines, then `have <oid>` lines in rounds; the
       server replies `ACK`/`NAK` until it knows a common base; then it sends a packfile.
       `[PROVE]`
3.14.7 Negotiation algorithms: `consecutive` (default, walk back linearly), `skipping` (exponential
       stride, far fewer rounds on divergent histories), `noop` (send nothing, get everything).
       `fetch.negotiationAlgorithm`, `--negotiation-tip`. `[CFG]` `[NUM]` `[RESEARCH]`
3.14.8 Why negotiation matters: each round is a network RTT. On a 200 ms link, 20 rounds is 4
       seconds before a byte of data moves. `[PROVE]` `[NUM]`
3.14.9 The **side-band** multiplexing: band 1 = packfile data, band 2 = progress messages (what you
       see as "Counting objects"), band 3 = fatal error. `side-band-64k` raises the frame size.
       This is why progress and data share one connection. `[PROVE]` `[NUM]`
3.14.10 2.55 sanitises control characters on band 2 by default while preserving ANSI colour — a
        terminal-escape-injection fix. `[RESEARCH]` `[X-REF 13]`
3.14.11 `receive-pack` on push: the client sends old→new→ref update commands plus a packfile; the
        server runs `pre-receive`, updates refs, runs `update` per ref, then `post-receive`.
        `--atomic` makes all updates succeed or all fail. `[PROVE]`
3.14.12 `push --signed` and the push certificate: a signed statement of the exact ref transitions,
        with `receive.certNonceSeed` providing replay protection. `[RESEARCH]`
3.14.13 `proc-receive` and `receive.procReceiveRefs`: how Gerrit-style "push to `refs/for/main`
        creates a review" works without the client knowing. `[RESEARCH]`
3.14.14 Partial clone on the wire: the `filter` capability, the promisor remote, and the on-demand
        `fetch` of a single missing blob mid-command. `[PROVE]`
3.14.15 `packfile-uris` and **bundle URIs**: the server can say "get most of the objects from this
        CDN URL, then fetch the delta from me". `transfer.bundleURI`, `clone --bundle-uri`.
        `[RESEARCH]`
3.14.16 `GIT_TRACE_PACKET=1` to watch the whole conversation, and `GIT_TRACE_CURL=1` /
        `GIT_CURL_VERBOSE=1` for HTTP. The debugging tool for "why is my fetch slow".
        `[CMD]` `[X-REF 20]`
3.14.17 `GIT_PROTOCOL` propagation over SSH requires the server's `sshd` to accept it
        (`AcceptEnv GIT_PROTOCOL`), which is why v2 silently falls back to v0 on some hosts and
        fetches get mysteriously slow. `[TRAP]` `[RESEARCH]`
3.14.18 HTTP specifics: `git-upload-pack` and `git-receive-pack` endpoints, `Content-Type:
        application/x-git-*`, chunked transfer, and why `http.postBuffer` is almost never the real
        fix for a failing push. `[TRAP]`

*(18 leaves)*

## §3.15 Filters, attributes, and the checkout pipeline

3.15.1 The **checkin** pipeline order: `filter` (clean) → `ident` → `text` (CRLF→LF).
       The **checkout** pipeline is the reverse: `text` (LF→CRLF) → `ident` → `filter` (smudge).
       Getting the order right explains every "my file changed on checkout" mystery. `[PROVE]`
       `[SOURCE]` `[RESEARCH]`
3.15.2 `filter.<name>.clean`, `.smudge`, `.process`, `.required`; the `%f` placeholder for the
       filename. `[CFG]` `[RESEARCH]`
3.15.3 The long-running **process filter protocol**: pkt-line handshake with `git-filter-client`,
       version 2, capabilities `clean`/`smudge`/`delay`; then command frames with `key=value` pairs
       and a flush; responses carry `status=success|error|abort`. One process for a whole checkout
       instead of a fork per file. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.15.4 The `delay` capability and `list_available_blobs` — how LFS overlaps network downloads with
       the rest of the checkout. `[RESEARCH]`
3.15.5 `filter.<name>.required = true` turns a filter failure into a hard error instead of silently
       writing unfiltered content. Always set it for LFS. `[TRAP]`
3.15.6 Idempotency requirement: `clean(clean(x)) == clean(x)` and
       `clean(smudge(clean(x))) == clean(x)`. A filter that violates this makes `git status`
       permanently dirty. `[PROVE]` `[TRAP]` `[RESEARCH]`
3.15.7 `ident` and `$Id$` expansion — the CVS holdover nobody should use, listed for completeness.
3.15.8 `working-tree-encoding` (e.g. `UTF-16LE`): Git stores UTF-8 in the object database and
       converts on checkout. Not supported by JGit/libgit2, slows everything down, and breaks on
       non-round-trip-safe encodings like SHIFT-JIS. `[TRAP]` `[RESEARCH]`
3.15.9 `core.autocrlf` versus `.gitattributes text`: attributes win, are committed, and are therefore
       the only correct cross-platform answer. `core.safecrlf` warns on irreversible conversions.
       `[CFG]` `[PROVE]`
3.15.10 `git ls-files --eol` to see, per file, the index EOL, the worktree EOL and the attributes
        that applied. The diagnostic command for every line-ending question. `[CMD]`
3.15.11 The macro attribute mechanism (`[attr]binary -diff -merge -text`), definable only in
        top-level attribute files, and only settable (never unsettable). `[RESEARCH]`
3.15.12 `git check-attr` as the ground truth when attributes seem not to apply.
3.15.13 Why filters make `git status` slow on large trees: every non-clean-cached file must be run
        through the clean filter to compare. `[PROVE]` `[NUM]`

*(13 leaves)*

## §3.16 Performance engineering of a Git repository

3.16.1 The measurement discipline: `GIT_TRACE2_PERF=1` or `GIT_TRACE_PERFORMANCE=1`, then attribute
       time to a region before changing anything. Never tune from folklore. `[CMD]` `[X-REF 20]`
3.16.2 `git status` cost decomposed: index read, lstat per tracked file, untracked-file scan,
       `.gitignore` matching, submodule status, and the terminal render. Each has a different fix
       (`index.version=4`/`splitIndex`, `fsmonitor`, `untrackedCache`, `status.showUntrackedFiles`,
       `submodule.ignore`, `--no-optional-locks`). `[PROVE]` `[NUM]`
3.16.3 `git log` cost: without a commit-graph, one zlib inflate per commit; with one, a
       memory-mapped array read. Measure both on a 100k-commit repo. `[NUM]`
3.16.4 `git blame` cost: O(commits touching the file) each requiring a diff. `-C -C -C` multiplies
       it. The commit-graph's changed-path Bloom filters cut the candidate set. `[PROVE]`
3.16.5 `git checkout`/`switch` cost: O(files differing) writes plus filter invocations plus the index
       write. Sparse-checkout reduces the first term, sparse index the third. `[PROVE]`
3.16.6 `git clone` cost decomposed: negotiation RTTs, server-side object enumeration (bitmaps),
       pack transfer bytes, client-side `index-pack` (CPU-bound delta resolution), and checkout.
       Which of the five dominates tells you which fix to apply. `[PROVE]` `[NUM]`
3.16.7 `git fetch` cost on a many-ref repository: ref advertisement (fixed by protocol v2), ref
       updates (fixed by reftable batching — 22x in 2.51), and negotiation.
       `[NUM]` `[RESEARCH]`
3.16.8 `git push` cost: local object enumeration, thin-pack construction, transfer, server-side
       `index-pack --fix-thin`, hook execution, ref updates. Server-side hooks are frequently the
       dominant term and nobody measures them. `[TRAP]`
3.16.9 The knobs, collected: `core.fsmonitor`, `core.untrackedCache`, `core.preloadIndex`,
       `index.version=4`, `index.skipHash`, `core.splitIndex`, `core.commitGraph`, `index.sparse`,
       `pack.threads`, `feature.manyFiles`, `feature.experimental`. `[CFG]`
3.16.10 `feature.manyFiles` as a bundle (`index.version=4`, `index.skipHash`,
        `core.untrackedCache`) — turning on a preset instead of five keys. `[CFG]` `[RESEARCH]`
3.16.11 Filesystem effects: APFS vs ext4 vs NTFS vs a network mount; case-insensitivity
        (`core.ignoreCase`); Windows path length (`core.longpaths`); antivirus scanning every
        checkout write; Docker bind mounts on macOS. Each is a real, measurable multiplier.
        `[TRAP]` `[NUM]` `[X-REF 19]`
3.16.12 `core.ignoreCase = true` on macOS/Windows and the class of bugs it produces: two files
        differing only in case, a rename that only changes case (`git mv --force`), and a CI on
        Linux that sees both files. `[TRAP]`
3.16.13 The Rust transition as a performance and safety story: varint encode/decode in 2.52,
        default-on in 2.55, mandatory in 3.0. What it means for anyone who builds Git.
        `[RESEARCH]`
3.16.14 A repository-performance triage flowchart the bible must include, from symptom to knob.
        `[BUILD]`

*(14 leaves)*

## §3.17 Concurrency, atomicity, and corruption

3.17.1 Git's concurrency model: no server, no daemon, no locks except per-file `*.lock` files. Two
       processes in one repository are coordinated only by those and by object immutability.
       `[PROVE]`
3.17.2 The lock inventory: `index.lock`, `<ref>.lock`, `packed-refs.lock`, `config.lock`,
       `tables.list.lock` (reftable), `shallow.lock`, `HEAD.lock`. Each is create-exclusive then
       rename. `[NUM]`
3.17.3 What is atomic and what is not: a single ref update is atomic; a multi-ref update is atomic
       only with `--atomic` (transport) or `update-ref --stdin` (local) or reftable; an index write
       is atomic; a `git commit` as a whole is **not** — objects are written before the ref moves.
       `[PROVE]` `[TRAP]`
3.17.4 The write-order invariant that makes crashes safe: **objects first, then the ref.** A crash
       between them leaves unreachable objects (garbage), never a ref pointing at a missing object.
       `[PROVE]`
3.17.5 The corruption sources, each with its signature: a full disk (zero-length loose objects),
       a crash during `fsync`-less writes, a killed `gc`, an alternates donor pruning, a networked
       filesystem with weak rename semantics, a filesystem-level bit flip, and copying a `.git`
       directory while Git is running. `[NUM]` `[TRAP]`
3.17.6 The corruption diagnosis order: `git fsck --full --strict`, then `git cat-file -t` on the
       named OID, then locate the object (loose? in which pack?), then decide the source of a
       replacement. `[RECOVER]`
3.17.7 Replacement sources ranked: another clone, the remote (`git fetch origin --refetch`), a
       colleague's pack, a bundle backup, the reflog, and last `git replace --graft` to route around
       the damage. `[RECOVER]`
3.17.8 Why "just re-clone" is usually correct and not a defeat: the object database is fully
       reconstructible from any complete clone, and your only unique data is unpushed commits, which
       you can export with `git bundle` or `format-patch` first. `[PROVE]` `[RECOVER]`
3.17.9 Backups that actually work: `git bundle create backup.bundle --all` (self-verifying, single
       file), a bare mirror clone with `core.logAllRefUpdates=true`, and *not* `rsync` of a live
       `.git`. `[BUILD]` `[TRAP]`
3.17.10 `git fsck --connectivity-only` for a fast check on a huge repository, and
        `git verify-pack` for pack-level verification. `[CMD]`
3.17.11 Two Git processes racing: `--no-optional-locks` for read-only commands, and why an IDE's
        background `git status` fighting your terminal is the single most common cause of
        `index.lock` errors. `[TRAP]`
3.17.12 Repositories on network filesystems (NFS, SMB, Dropbox, OneDrive, iCloud): rename semantics,
        locking, and mtime resolution all differ, and every one of them causes real corruption. Say
        plainly: do not put a working repository in a sync folder. `[TRAP]`

*(12 leaves)*

## §3.18 Reading Git's own source

3.18.1 The repository map: `builtin/` (one file per command), `refs/` (backends), `object.c`,
       `commit.c`, `tree.c`, `blob.c`, `tag.c`, `sha1-file.c`/`object-file.c`, `pack-objects.c`,
       `packfile.c`, `read-cache.c` (the index), `merge-ort.c`, `sequencer.c`, `rerere.c`,
       `diff.c`, `xdiff/`, `commit-graph.c`, `midx.c`, `transport.c`, `fetch-pack.c`,
       `send-pack.c`, `upload-pack.c`, `receive-pack.c`. `[SOURCE]`
3.18.2 `Documentation/technical/` as the real internals documentation: `pack-format`,
       `index-format`, `reftable`, `commit-graph-format`, `multi-pack-index`, `bitmap-format`,
       `protocol-v2`, `protocol-capabilities`, `pack-protocol`, `partial-clone`,
       `sparse-index`, `hash-function-transition`, `directory-rename-detection`,
       `rerere`, `bundle-uri`. Naming these is a strong seniority signal. `[SOURCE]` `[RESEARCH]`
3.18.3 `git log` on Git itself as the primary source for "why does it do that": the commit messages
       in this project are unusually good and frequently answer the question directly. `[PROVE]`
3.18.4 The mailing list (`git@vger.kernel.org`), `public-inbox`, and "What's cooking in git.git" as
       the design record. `[RESEARCH]`
3.18.5 `t/` — the test suite, `t/t*.sh`, and using a test as executable documentation of a
       behaviour you are unsure about. `[BUILD]`
3.18.6 `test-tool` helpers (`dump-cache-tree`, `read-midx`, `dump-untracked-cache`,
       `ref-store`, `dump-reftable`) for inspecting internal structures. `[CMD]` `[RESEARCH]`
3.18.7 Building Git from source: `make`, `meson setup`, `NO_RUST=1`, `DEVELOPER=1`,
       `make test`, and running a built binary via `bin-wrappers/git`. `[CMD]`
3.18.8 How to answer "how does X work" in an interview when you do not know: name the technical
       document, name the likely source file, and describe the constraint the design must satisfy.
       That is a better answer than a guess.

*(8 leaves)*

---

# PART 4 — BUILD IT

Every `[BUILD]` in this part ships **complete, compiling Java 21** (or a complete runnable
`bash`/`python3` script where the artefact is genuinely a script), followed by a **Diff vs the real
one** table. No `...` elisions. All code operates on a real repository created by the accompanying
setup script, and all example data comes from the QuizStakes `funds-ledger` repository.

## §4.1 A Git object reader

4.1.1 `GitObject` as a sealed interface with records `Blob`, `Tree`, `Commit`, `Tag` — Java 21
      sealed types and pattern matching used as intended. `[BUILD]` `[X-REF 04]`
4.1.2 `ObjectId` as a record wrapping `byte[20]`/`byte[32]` with hex parsing, `toString`, `equals`,
      `hashCode`, and abbreviation. `[BUILD]`
4.1.3 `LooseObjectStore.read(ObjectId)`: path from OID, `InflaterInputStream`, parse
      `<type> <size>\0`, validate the size, dispatch by type. `[BUILD]` `[HEX]`
4.1.4 `hashObject(type, content)`: build the header, hash with `MessageDigest.getInstance("SHA-1")`,
      and **verify against `git hash-object`** as the test. `[BUILD]` `[PROVE]`
4.1.5 `LooseObjectStore.write`: deflate, write to a temp file, atomic `Files.move` with
      `ATOMIC_MOVE`, skip if the target exists. `[BUILD]`
4.1.6 `TreeParser`: loop reading `<mode> <name>\0<raw-oid>`, handling the missing leading zero on
      `40000`, and the binary OID. `[BUILD]` `[HEX]`
4.1.7 `TreeWriter`: sort entries with the directories-sort-as-if-slashed rule, emit, hash, verify
      against `git mktree`. `[BUILD]` `[PROVE]`
4.1.8 `CommitParser`: headers until the blank line, multiple `parent` lines, identity-line parsing
      with the epoch and timezone, and a multi-line `gpgsig` continuation (leading space).
      `[BUILD]` `[TRAP]`
4.1.9 `TagParser` for annotated tags.
4.1.10 A `main` that walks from `HEAD` printing the commit graph — the "my own `git log`". `[BUILD]`
4.1.11 **Diff vs the real one**: no packfile support, no SHA-1DC, no `core.compression` honouring,
       no mmap, no object cache, no alternates, no partial-clone lazy fetch, no
       `GIT_ALTERNATE_OBJECT_DIRECTORIES`, no streaming for large blobs, and no `fsck`-grade
       validation. Explain why the real one bothers with each.

*(11 leaves)*

## §4.2 A ref resolver

4.2.1 `RefStore.resolve(String name)`: loose file, then `packed-refs`, honouring the shadowing rule.
      `[BUILD]`
4.2.2 Symbolic ref following with a depth limit (Git's is 5) to prevent cycles. `[BUILD]` `[NUM]`
4.2.3 `packed-refs` parsing including the header traits and the `^` peel lines. `[BUILD]` `[HEX]`
4.2.4 Revision expression evaluation for the subset that matters: `<name>`, `<oid>`, `HEAD`, `@`,
      `~n`, `^n`, `^{}`, `@{n}`. Recursive descent, ~120 lines. `[BUILD]` `[PROVE]`
4.2.5 `ReflogReader` parsing `.git/logs/HEAD` into records, and `HEAD@{n}` / `HEAD@{<date>}`
      resolution. `[BUILD]`
4.2.6 **Diff vs the real one**: no reftable backend, no worktree-scoped refs, no `GIT_NAMESPACE`,
      no lock protocol, no transactions, no `refs/replace` indirection, no disambiguation of
      ambiguous short names, and no `@{upstream}`/`@{push}` (which need config).

*(6 leaves)*

## §4.3 A packfile reader

4.3.1 `PackIndexV2`: parse the magic, version, 256-entry fan-out, OID table, CRC table, offset table
      and large-offset table; implement `findOffset(ObjectId)` with fan-out + binary search.
      `[BUILD]` `[HEX]` `[PROVE]`
4.3.2 `PackFile`: header validation, and `readObjectHeader` decoding the 3-bit type and the
      4+7·n-bit size. `[BUILD]` `[PROVE]`
4.3.3 `readVarint` and `readOffsetDelta` (the `((val+1)<<7)|...` negative-offset encoding).
      `[BUILD]` `[PROVE]`
4.3.4 `DeltaApplier`: parse base size and result size, then loop over copy (MSB=1, presence bitmap
      for 4 offset + 3 size bytes, size 0 ⇒ 0x10000) and insert (MSB=0, 1–127 literal bytes)
      instructions, rejecting instruction byte `0x00`. `[BUILD]` `[SOURCE]` `[PROVE]`
4.3.5 Delta-chain resolution with a depth guard and a small LRU base cache. `[BUILD]` `[NUM]`
4.3.6 `REF_DELTA` resolution by OID lookup, including the thin-pack case where the base is absent.
      `[BUILD]`
4.3.7 A `main` that prints, for a real pack, every object's type, size, size-in-pack and delta
      depth — i.e. a reimplementation of `git verify-pack -v` — and diff its output against the
      real command. `[BUILD]` `[PROVE]`
4.3.8 A histogram of delta depths and a "top 10 largest objects" report over the pack. `[BUILD]`
      `[NUM]`
4.3.9 **Diff vs the real one**: no `.rev`/MIDX/bitmap support, no mmap (Git memory-maps packs and
      pages them in), no CRC verification, no v1 index, no SHA-256, no multithreaded delta
      resolution, no `core.bigFileThreshold` streaming, and no `index-pack --fix-thin`.

*(9 leaves)*

## §4.4 An index reader and writer

4.4.1 `IndexHeader` parse: `DIRC`, version, entry count. Reject versions outside 2–4. `[BUILD]`
      `[HEX]`
4.4.2 `IndexEntry` as a record with every field from §3.4.2, decoding the flags into
      `assumeValid`, `extended`, `stage`, `nameLength`. `[BUILD]` `[PROVE]`
4.4.3 v2/v3 8-byte padding versus v4 prefix compression — implement both read paths. `[BUILD]`
      `[NUM]`
4.4.4 Extension dispatch on the 4-byte signature, with the uppercase-optional/lowercase-mandatory
      rule enforced. `[BUILD]` `[PROVE]`
4.4.5 `TREE` cache-tree parsing into a nested record, including the `-1` invalid marker. `[BUILD]`
4.4.6 Trailing-checksum verification. `[BUILD]`
4.4.7 A `main` that reproduces `git ls-files -s -v --debug` output and is diffed against it.
      `[BUILD]` `[PROVE]`
4.4.8 A conflict-stage reporter: given a conflicted index, print stages 1/2/3 per path — a
      reimplementation of `git ls-files -u`. `[BUILD]`
4.4.9 **Diff vs the real one**: read-only (writing needs the lock protocol and `fsync` policy), no
      split index, no untracked cache, no fsmonitor token, no sparse directories, no
      multithreaded parse via `IEOT`, and no racy-timestamp handling.

*(9 leaves)*

## §4.5 A commit-graph walker and merge-base finder

4.5.1 `CommitGraph` in memory: load commits lazily from the object store, cache by OID. `[BUILD]`
4.5.2 `RevWalk`: a priority queue ordered by commit date with a `seen` set — the actual algorithm
      `git log` uses. `[BUILD]` `[PROVE]`
4.5.3 Topological ordering via Kahn's algorithm over the in-degree of children, and why date order
      alone is wrong when clocks skew. `[BUILD]` `[PROVE]` `[X-REF 01]`
4.5.4 `mergeBase(a, b)`: mark reachability from both, collect common ancestors, remove any that are
      ancestors of another common ancestor. Return the set, not a single value. `[BUILD]`
      `[PROVE]`
4.5.5 Construct a criss-cross history in a test and assert that `mergeBase` returns **two** bases,
      matching `git merge-base --all`. `[BUILD]` `[PROVE]`
4.5.6 `isAncestor(a, b)` with an early cutoff, and the same function using generation numbers to
      show the speedup. `[BUILD]` `[PROVE]`
4.5.7 Compute generation numbers (v1 topological level) for the whole graph and demonstrate the
      cutoff property empirically by counting commits visited with and without. `[BUILD]` `[NUM]`
      `[PROVE]`
4.5.8 A `--graph`-style ASCII renderer for the DAG, and the lane-assignment algorithm behind it.
      `[BUILD]`
4.5.9 **Diff vs the real one**: no on-disk commit-graph file, no corrected commit dates, no Bloom
      filters, no history simplification, no pathspec limiting, and no incremental chain.

*(9 leaves)*

## §4.6 A three-way merge implementation

4.6.1 An LCS-based line differ (dynamic programming, O(NM)) as the baseline. `[BUILD]` `[X-REF 01]`
4.6.2 A Myers O(ND) differ, with the edit-graph explanation in code comments and a property test
      asserting both differs produce edit scripts of equal length. `[BUILD]` `[PROVE]`
4.6.3 A patience differ: unique-line matching + longest increasing subsequence + recursion.
      `[BUILD]` `[PROVE]` `[X-REF 01]`
4.6.4 A test that constructs the canonical "function added above" case and asserts patience produces
      the readable diff while Myers does not. `[BUILD]` `[PROVE]`
4.6.5 `threeWayMerge(base, ours, theirs)` producing either a merged text or a list of conflict
      regions, using the diff3 algorithm over matched/unmatched regions. `[BUILD]` `[PROVE]`
4.6.6 Conflict-marker rendering in `merge`, `diff3` and `zdiff3` styles, with the zdiff3 hoisting of
      common leading/trailing lines implemented. `[BUILD]` `[PROVE]`
4.6.7 A tree-level merge: recurse over three trees, short-circuit when two of the three tree OIDs
      are equal, and produce add/delete/modify/conflict per path. `[BUILD]` `[PROVE]`
4.6.8 Similarity-based rename detection: chunk-hash both blobs, compute
      `2·common/(sizeA+sizeB)`, apply the 50% threshold, and cap the candidate matrix. `[BUILD]`
      `[PROVE]` `[NUM]`
4.6.9 A test on real QuizStakes files where a rename plus a modification on the other side merges
      correctly with detection on and produces a modify/delete conflict with it off. `[BUILD]`
      `[PROVE]`
4.6.10 **Diff vs the real one**: no virtual merge base for criss-cross histories, no directory
       rename detection, no submodule or symlink handling, no `.gitattributes` merge drivers, no
       renormalisation, no rerere, no index/worktree writing, and no `AUTO_MERGE`.

*(10 leaves)*

## §4.7 Scripts and hooks that must actually run

4.7.1 A `commit-msg` hook enforcing Conventional Commits plus a `Refs: <TICKET>` trailer, with the
      exact regex, an allowlist for merge/revert/fixup commits, and a helpful error message.
      `[BUILD]`
4.7.2 A `pre-commit` hook that formats and lints **only staged Java files**, re-stages the
      formatter's output, and runs `gitleaks protect --staged`. Must complete in under 2 seconds.
      `[BUILD]` `[NUM]`
4.7.3 A `pre-push` hook refusing a direct push to `main`/`release/*` and running the fast test
      subset. `[BUILD]`
4.7.4 A `pre-receive` hook rejecting: blobs over 10 MB, force-pushes to protected refs, commits
      without a signature, and commit messages failing the format check. `[BUILD]`
4.7.5 The 2.54 config-hook equivalents of 4.7.1–4.7.3, showing both spellings side by side.
      `[BUILD]` `[RESEARCH]`
4.7.6 A `git bisect run` script for the `FL-9930` double-reservation regression: 125 on build
      failure, 1 on reproduction, 0 otherwise, with a hard timeout and a clean `target/`.
      `[BUILD]`
4.7.7 A `git bisect run` script for a **performance** regression against the 150 ms
      stake-reservation budget, with warmup, repetitions and a percentile assertion. `[BUILD]`
      `[NUM]` `[X-REF 06]`
4.7.8 A repository-health script: object count, pack count, ref count, largest 20 blobs, size on
      disk, and a pass/fail against budgets. Runnable in CI. `[BUILD]`
4.7.9 A co-change analysis script over `git log --name-only` producing a coupling matrix, with the
      distortion caveats from §2.23.16 printed in the output. `[BUILD]`
4.7.10 A churn-versus-complexity report identifying refactoring candidates. `[BUILD]` `[NUM]`
4.7.11 A secret-leak response runbook as an executable checklist script that walks the operator
       through rotate → audit → clean → coordinate → prevent, refusing to proceed to step 3 until
       step 1 is confirmed. `[BUILD]` `[RECOVER]`
4.7.12 A `filter-repo` rewrite script for the QuizStakes leaked-password case, with a `--dry-run`
       default, an `--analyze` pre-step, and a post-rewrite `fsck` verification. `[BUILD]`
4.7.13 A backup script: `git bundle create --all` plus verification plus retention. `[BUILD]`
4.7.14 A `.gitconfig` and a `.gitattributes` for a Java/Spring monorepo, both annotated line by line.
       `[BUILD]`
4.7.15 A GitHub Actions workflow demonstrating correct `fetch-depth`, changed-file computation
       against the merge base, path filtering, and a merge-queue-compatible required check.
       `[BUILD]` `[X-REF 19]`
4.7.16 A Java 21 `MDC` correlation-ID filter and an outbound `RestClient` interceptor that
       propagates it, plus a `TaskDecorator` that carries it across `@Async`. Preserves and
       modernises the current guide's snippet. `[BUILD]` `[X-REF 05]` `[X-REF 20]`
4.7.17 **Diff vs the real one** for the hook set: no cross-platform shell portability guarantees, no
       Windows support, no hook-manager integration, no caching, and no telemetry — and why a
       production hook set needs all five.

*(17 leaves)*

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question bank

5.1.1 **Object model (12 questions)**: what is a commit, exactly; what does a tree contain; why does
      `git hash-object` differ from `sha1sum`; how does Git deduplicate; what happens to the old
      blob when you edit a file; are renames stored; what is a lightweight tag; can a commit have
      three parents; what is the mode `160000`; how many bytes is a branch; what is `HEAD` when
      detached; why is the history a DAG.
5.1.2 **Hashing (6)**: why SHA-1 is still used; what SHA-1DC is; what a collision would let an
      attacker do; when does SHA-256 become the default; what breaks when OIDs get longer; why is
      abbreviating a SHA in a deploy manifest a bug.
5.1.3 **Index (8)**: what is the index really; why does it exist; what is stat caching; what are
      conflict stages; what is a cache tree; `--assume-unchanged` versus `--skip-worktree`; what
      does `git add -p` actually do; what is `index.lock`.
5.1.4 **Branching and refs (8)**: what is a branch; what does `git branch -d` refuse and why; why
      does `--merged` lie after a squash-merge; what is `packed-refs`; what is reftable and why;
      what is `origin/main`; what is `@{upstream}`; what is a refspec.
5.1.5 **Merge vs rebase (10)**: explain both mechanisms; when is each right; what is the golden rule
      and why; why does rebase conflict per commit; what does a merge base do; what happens with two
      merge bases; what is `ort`; what is a fast-forward; what does `--no-ff` buy; how do you undo
      each.
5.1.6 **Undo (10)**: revert vs reset vs restore; the three reset modes (and the other two); what is
      unrecoverable; how do you undo a pushed commit; how do you revert a merge; why does re-merging
      after a revert not work; what does `ORIG_HEAD` do; how do you recover a deleted branch; what
      does `git clean` destroy; how do you split the last commit in two.
5.1.7 **Recovery (8)**: what is the reflog; what can and cannot it recover; what is
      `fsck --lost-found`; how long do unreachable objects survive; how do you recover from a bad
      force-push; does a bare repo have a reflog; how do you recover a dropped stash; what is the
      first thing you do before any recovery.
5.1.8 **Rewriting (8)**: what does rewriting history actually change; filter-branch vs filter-repo vs
      BFG; what does a rewrite not remove; what is the coordination protocol; what is `.mailmap`
      for; what is `git replace`; what is `--update-refs`; what is `git history reword`.
5.1.9 **Internals (14)**: how does a packfile work; OFS vs REF delta; what caps delta depth; how does
      `.idx` lookup work; what is a MIDX; what is a bitmap for; what does the commit-graph store;
      what is a generation number and what property does it give you; what are changed-path Bloom
      filters; what is a cruft pack; what is protocol v2 for; what is a thin pack; what is
      negotiation; what is a promisor remote.
5.1.10 **Scale (8)**: three reasons a repo is slow and the fix for each; what is partial clone; what
       is sparse-checkout; what is the sparse index; what is Scalar; what is fsmonitor; what does
       `git maintenance` do; monorepo vs polyrepo.
5.1.11 **Workflow (10)**: trunk-based vs GitFlow; why must `main` be deployable; what do feature
       flags buy and cost; squash vs merge vs rebase merge; what is a merge queue and what does it
       fix; what is a semantic conflict; what are stacked PRs; what breaks stacked PRs; what is
       `CODEOWNERS` for; how do you handle a release branch.
5.1.12 **Hooks and CI (8)**: name five hooks and when they run; why are hooks not distributed; what
       is `core.hooksPath`; what are config-based hooks; what belongs in a hook versus in CI; how do
       you enforce policy that cannot be bypassed; why is `fetch-depth: 0` sometimes required; how
       do you compute changed files correctly in CI.
5.1.13 **Review (10)**: what order do you review in and why; what is the evidence on PR size; how do
       you split a large PR; what makes a review comment good; blocking versus nit; why question
       form; what do you do after two round trips; how do you review a refactor; how do you review
       an AI-generated PR; what is a failed review that looks thorough.
5.1.14 **Debugging (10)**: describe your method; what do you ask first; how do you binary-search a
       problem space; what makes a good hypothesis; how do you handle a bug you cannot reproduce;
       what does a 1/N failure rate suggest; how do you verify a fix for a rare bug; what is a
       correlation ID and where does it break; how do you use `git bisect run`; what makes a commit
       bisectable.
5.1.15 **Security and secrets (8)**: a key is in a public repo — what do you do, in order; why rotate
       first; what does a rewrite not remove; how do you prevent it; what does a signed commit
       prove; what does "Verified" on GitHub mean; what is `safe.directory`; why is cloning an
       untrusted repository dangerous.
5.1.16 **Staff-level design questions (8)**: how would you design version control from scratch; why
       content addressing; how would you scale Git to 10M files; how would you keep `main` green
       with 300 engineers; how would you migrate 400 repos to a monorepo; how would you roll out
       signed commits across an org; what is your branching policy for a regulated product; how
       would you measure whether code review is working. `[X-REF 22]`
5.1.17 **The command-recall drill**: given 40 natural-language intents, produce the exact command.
       This is the fluency test and it is the one that is actually asked.

*(17 leaves — ~146 individual questions)*

## §5.2 The trap index

5.2.1 Every `[TRAP]` in this file, collected into one numbered list with wrong belief → symptom →
      fix. The bible must contain all of them; this section is the index, not a summary.
5.2.2 The traps carried forward from the current guide, which must all survive: ours/theirs swap in
      rebase; `reset --hard` destroying uncommitted work; `clean -fd` being unrecoverable;
      `--force-with-lease` defeated by a preceding fetch; `.gitignore` not affecting tracked files;
      deleting a secret in a later commit doing nothing; MDC not crossing async boundaries;
      reverting a merge blocking a later re-merge.
5.2.3 The top ten traps by frequency-in-the-wild, ranked, with the estimated cost of each. `[NUM]`
5.2.4 The traps that lose data permanently — exactly three — highlighted separately.
5.2.5 The traps that are **version-stale beliefs** (`[VERSION-TRAP]`), collected: `recursive` as a
      distinct strategy; SHA-256 already being the default; refs only being files; `switch`/`restore`
      being experimental; `--preserve-merges`; `gc` exploding loose objects; hooks being
      undistributable; `filter-branch` being the tool.
5.2.6 The traps that are **shell/tooling** rather than Git: IDE background commands taking
      `index.lock`; antivirus on checkout; a repository in a cloud-sync folder;
      case-insensitive filesystems; `GIT_PROTOCOL` not surviving SSH.
5.2.7 The traps that only appear at scale: rename limits silently exceeded; shallow clone breaking
      merge-base; partial clone making blame pathological; ref-count-driven fetch slowness.

*(7 leaves)*

## §5.3 Drills and one-line assertions

5.3.1 **Numbers drill** — recite from memory: object header format; tree entry modes (`100644`,
      `100755`, `120000`, `40000`, `160000`); pack object types 1/2/3/4/6/7; `pack.window` 10;
      `pack.depth` 50; `gc.auto` 6700; `gc.autoPackLimit` 50; `gc.pruneExpire` 2 weeks;
      `gc.reflogExpire` 90 days; `gc.reflogExpireUnreachable` 30 days; `gc.rerereResolved` 60 days;
      `gc.rerereUnresolved` 15 days; `gc.worktreePruneExpire` 3 months; rename threshold 50%;
      `core.bigFileThreshold` 512 MiB; commit-graph chain X=2 / C=64000;
      `GENERATION_NUMBER_V1_MAX` 0x3FFFFFFF; PR size 200–400 lines; review 60 minutes / 500 LOC/hr;
      bisect exit codes 0/1/125. `[NUM]`
5.3.2 **Command drill** — 40 intents to exact commands, timed.
5.3.3 **Recovery drill** — the 23 scenarios of §2.21, given as symptoms only, answered from memory.
5.3.4 **Reading drill** — a real `git log --graph` output, a `git status` with every code, a
      `verify-pack -v` line, a reflog excerpt, a conflict in `zdiff3`, and a `.git` directory
      listing: read each aloud, field by field. `[HEX]`
5.3.5 **Whiteboard drill** — draw: the object graph for a two-commit repository; a merge versus a
      rebase; a criss-cross history with two merge bases; a stacked-PR chain before and after
      `--update-refs`; the three trees; the packfile layout.
5.3.6 **Explanation drill** — 60 seconds each, out loud: what a commit is; why rebase is dangerous
      on shared branches; how bisect works; what the index is for; why the reflog saves you; why
      Git deduplicates for free; what a merge queue fixes.
5.3.7 **The 100 one-line assertions** — the atomic-concept checklist expanded to cover this
      syllabus, each independently true, testable and memorisable. This becomes the bible's
      `## Atomic concept checklist`, and must **contain every one of the current guide's 56 lines
      verbatim or expanded**, never dropped.
5.3.8 The spaced-repetition plan: which 30 facts to review daily for a week before an interview,
      and which 20 only need recognition rather than recall.
5.3.9 The "what I would say if I did not know" script: name the mechanism family, name the
      constraint, name the document, and propose how you would verify. Better than a confident
      wrong answer, and interviewers reward it.
5.3.10 The three sentences that most reliably signal seniority in a Git conversation:
       "a commit is a snapshot whose hash covers its parents, which is why rewriting one rewrites
       all of them"; "rotate the credential first, clean the history second"; "the fix for a
       1,000-line PR is not a better reviewer".

*(10 leaves)*

---

## Sources consulted

Primary sources first. Where a fetch failed or a search returned nothing usable, that is stated
rather than padded. Every `[RESEARCH]` leaf must be re-verified against the source named here before
the write pass commits a number to the page. **Target version for all verification: Git 2.55.**

**Format specifications and official documentation (primary)**

- <https://git-scm.com/docs/gitformat-pack> — fetched in full. Source of §3.2 in its entirety: the
  12-byte `PACK` header, versions 2/3, object types 1/2/3/4/6/7 with 0 and 5 invalid, the
  3-bit-type + (n-1)·7+4-bit-length header encoding, the varint rule, OFS vs REF delta semantics,
  thin packs, the delta instruction encoding (copy with presence bitmap, insert with 1–127 byte
  length), and §3.3's `.idx` v1/v2 layouts (magic `\377tOc`, fan-out, CRC32 table, large-offset
  table), `.rev` (`RIDX`, version 1, hash-function byte), MIDX (magic, version, chunk lookup, chunk
  IDs `PNAM`/`OIDF`/`OIDL`/`OOFF`/`LOFF`/`RIDX`/`BTMP`), and the checksum rules.
- <https://git-scm.com/docs/index-format> — fetched in full. Source of §3.4: `DIRC`, versions 2/3/4,
  every entry field, the 16-bit flags decomposition (assume-valid / extended / 2-bit stage / 12-bit
  name length), extended flags, v4 prefix compression, stage numbers 0–3, and the extension
  inventory `TREE`/`REUC`/`link`/`UNTR`/`FSMN`/`EOIE`/`IEOT`/`sdir` plus the
  uppercase-optional/lowercase-mandatory rule.
- <https://git-scm.com/docs/reftable> — fetched in full. Source of §3.5.5–§3.5.16: block types
  `'r'`/`'i'`/`'o'`/`'g'`, prefix compression with the `refs/heads/master` → `refs/heads/main`
  example, restart points, the varint with the `+1`, `tables.list`, the `update_index` transaction
  protocol, reversed-`update_index` log keys, deletion tombstones, compaction by merge-join, and the
  Android measurements (62.2 M → 36.1 M, 409,660 µs → 33.9 µs, 402 ms → 112 ms, reflog 173 M → 5 M).
- <https://git-scm.com/docs/commit-graph> — fetched in full. Source of §3.12: what the file stores,
  generation number v1 (topological level, `GENERATION_NUMBER_V1_MAX = 0x3FFFFFFF`) and v2
  (corrected committer dates), the cutoff property, the chain files and `commit-graph-chain`, the
  merge policy (X=2, C=64,000), the mixed-chain downward-consistency rule, and the config keys
  `core.commitGraph`, `fetch.writeCommitGraph`, `gc.writeCommitGraph`,
  `commitGraph.generationVersion`, `commitGraph.changedPathsVersion`.
- <https://git-scm.com/docs/git-gc> — fetched in full. Source of every gc default in §2.24.4 and
  §3.13: `gc.aggressiveDepth` 50, `gc.aggressiveWindow` 250, `gc.auto` 6700, `gc.autoPackLimit` 50,
  `gc.autoDetach` true, `gc.bigPackThreshold` disabled, `gc.cruftPacks` true, `gc.pruneExpire`
  2.weeks.ago, `gc.worktreePruneExpire` 3.months.ago, `gc.reflogExpire` 90 days,
  `gc.reflogExpireUnreachable` 30 days, `gc.rerereResolved` 60 days, `gc.rerereUnresolved` 15 days,
  plus the cruft-pack and `--prune` semantics. **`gc.maxCruftSize` had no default stated on the
  page** — do not invent one.
- <https://git-scm.com/docs/git-maintenance> — fetched in full. Source of §2.11.16–§2.11.19: the
  task inventory (`gc`, `commit-graph`, `prefetch`, `loose-objects`, `incremental-repack`,
  `pack-refs`, `geometric`, `reflog-expire`, `worktree-prune`, `rerere-gc`), the strategies
  (`none`/`gc`/`geometric`/`incremental`) with `geometric` introduced in **2.54** and default for
  manual runs, `incremental` default for scheduled runs, the hourly/daily/weekly schedule, and every
  `maintenance.*.auto` threshold (100, 100, 50000, 10, 100, 2, 100, 1, 1).
- <https://git-scm.com/docs/githooks> — fetched in full. Source of §2.13.2–§2.13.5: all 28 hooks in
  documentation order with trigger and abort semantics, including `reference-transaction`,
  `post-index-change`, `proc-receive`, `push-to-checkout`, `sendemail-validate`, and the four
  `p4-*` hooks.
- <https://git-scm.com/docs/gitattributes> — fetched in full. Source of §1.11.8–§1.11.16, §2.3.12–
  §2.3.13 and §3.15: the five-level attribute-file precedence, the four attribute states plus `!`,
  `text`/`eol`/`working-tree-encoding`/`ident`, the filter driver keys and the long-running process
  protocol, the diff attributes (external driver, `algorithm`, `xfuncname` with the full built-in
  language list, `wordRegex`, `textconv`, `cachetextconv`, `binary`), the merge attribute with the
  `%O %A %B %L %P %S %X %Y` placeholders and the `text`/`binary`/`union` built-ins,
  `conflict-marker-size`, `whitespace`, `export-ignore`, `export-subst`, `delta`, `encoding`, the
  `binary` macro, `builtin_objectmode`, and the checkin/checkout pipeline order.
- <https://git-scm.com/docs/git-config> — fetched in full. Source of §1.12: the six-level precedence
  chain, the five scopes, `include.path`, all four `includeIf` conditions
  (`gitdir`, `gitdir/i`, `onbranch`, `hasconfig:remote.*.url`) with their glob rules, the
  `--type` values, and the **protected configuration** concept (system/global/command only).
- <https://git-scm.com/docs/merge-strategies> — fetched in full. Source of §2.3.1–§2.3.5: `ort` as
  default, **`recursive` a synonym for `ort` since v2.50.0** and the default from v0.99.9k to
  v2.33.0, `resolve`, `octopus`, `ours`, `subtree`, and every `-X` option including the deprecated
  `rename-threshold`/`histogram`/`patience` synonyms and the fact that **`ort` defaults to
  `histogram`**.
- <https://git-scm.com/docs/git-rebase> — fetched in full. Source of §1.14 and §2.6.2: every option
  (`--onto`, `--keep-base`, `--fork-point`, `--root`, `--exec`, `--empty=drop|keep|stop`,
  `--reapply-cherry-picks`, `--autosquash`, `--autostash`, `--signoff`,
  `--committer-date-is-author-date`, `--ignore-date`, `--reschedule-failed-exec`, `--strategy`,
  `--apply` vs `--merge`, `--rebase-merges`, `--update-refs`) and the full todo vocabulary
  (`pick`, `reword`, `edit`, `squash`, `fixup` with `-c`/`-C`, `exec`, `break`, `drop`, `label`,
  `reset`, `merge`, `update-ref`). Also confirms the ours/theirs swap under `--merge`.
- <https://git-scm.com/docs/git-rerere> — fetched in full. Source of §2.5 and §3.11: the
  `rr-cache/<id>/{preimage,postimage,thisimage}` layout, the conflict-ID hashing, the three-way
  replay, all six subcommands, `rerere.enabled`/`rerere.autoUpdate` defaults, the
  `gc.rerereResolved`/`gc.rerereUnresolved` day counts, the automatic invocation points, the
  conflict-marker-detection limitation and the `conflict-marker-size` workaround.
- <https://git-scm.com/docs/git-worktree> — fetched in full. Source of §2.9: all eight subcommands,
  the `.git` file pointer, the `gitdir`/`commondir`/`HEAD`/`index`/`locked` layout, `$GIT_DIR` vs
  `$GIT_COMMON_DIR`, the shared-vs-per-worktree ref rule (`refs/bisect`, `refs/worktree`,
  `refs/rewritten` are per-worktree), the branch-already-checked-out restriction and `-f`/`-f -f`,
  `extensions.worktreeConfig`, and `gc.worktreePruneExpire`.
- <https://git-scm.com/docs/git-submodule> — fetched in full. Source of §2.10.1–§2.10.9: gitlink
  mode 160000, `.gitmodules` vs `.git/config` vs `.git/modules/`, all eleven subcommands, the
  update modes (`checkout`/`rebase`/`merge`/`none`/`!cmd`), the status prefixes `-`/`+`/`U`, the
  performance options, and the documented pain points.
- <https://git-scm.com/docs/BreakingChanges> — fetched in full. Source of §1.21.3–§1.21.8: the five
  default changes (sha256, reftable, `main`, mandatory Rust, `safe.bareRepository=explicit`), the
  seven removals, the explicit statement that `git-checkout` is **not** being removed, the Rust
  schedule (2.52 auto-detect, 2.55 default-enable, 3.0 mandatory), the `WITH_BREAKING_CHANGES`
  build flag, the LTS plan, and the absence of a release date.

**Release notes (primary)**

- <https://github.blog/open-source/git/highlights-from-git-2-55/> — fetched. Release date
  **29 Jun 2026**. Source of: incremental MIDX repacking (`--write-midx=incremental`,
  `repack.midxSplitFactor`, `repack.midxNewLayerThreshold`), `git history fixup`, parallel config
  hooks (`hook.<name>.parallel`, `hook.jobs`, `hook.<event>.jobs`, `git hook run -j`), the Linux
  inotify `fsmonitor--daemon`, `git format-rev`, `--graph-lane-limit`, `--max-count-oldest`,
  `--path-walk` filters, remote groups for `git push`, fetch negotiation controls,
  `git checkout -m` autostash, sideband control-character sanitisation, bitmap generation
  612 s → 294 s, ~20x pseudo-merge speedup, ~16% smaller path-walk packs.
  **The article does not mention Rust, SHA-256, reftable or Git 3.0** — those numbers came from
  `BreakingChanges` and the 2.51/2.52 notes instead.
- <https://github.blog/open-source/git/highlights-from-git-2-54/> — fetched. Release date
  **20 Apr 2026**. Source of: `git history reword` / `git history split`, config-based hooks with
  `[hook "name"] event = ...`, `git hook list`, `hook.<name>.enabled`, `.git/hooks` running last,
  geometric repacking as the `git maintenance run` default with `maintenance.strategy`, `add -p`
  visual indicators and `--no-auto-advance`, `git replay --revert` and atomic ref updates,
  `git log -L` compatibility with `-S`/`-G`/`--word-diff`/`--color-moved`, `git rebase --trailer`,
  `git blame --diff-algorithm`, `status.compareBranches`, `git backfill` with revisions and
  pathspecs, HTTP 429 handling (`http.retryAfter`, `http.maxRetries`, `http.maxRetryTime`), MIDX
  compaction, ODB pluggable-backend refactoring, expired-GPG-key handling, and the histogram
  region-re-diff fix.
- <https://github.blog/open-source/git/highlights-from-git-2-52/> — fetched. Source of:
  `git last-modified` (5.48x), the `git maintenance geometric` task, `git refs list` /
  `git refs exists`, `git repo` / `git repo info` / `git repo structure`,
  `git sparse-checkout clean`, Bloom-filter wildcard pathspecs, `git describe` 30% faster,
  `git log -L` merge handling, `git remote rename` optimisation, xdiff optimisations, the
  `WITH_RUST` build flag, SHA-1/SHA-256 interoperability groundwork, `WITH_BREAKING_CHANGES`, and
  the `init.defaultBranch` Git 3.0 change.
- <https://github.blog/open-source/git/highlights-from-git-2-51/> — fetched. Source of:
  `repack.MIDXMustContainCruft` (38% smaller MIDX, 35% faster writes, ~5% faster reads),
  `--path-walk`, `git stash export`/`import`, `git cat-file --batch-check` submodule handling,
  multi-pathspec changed-path Bloom filters, **`git switch`/`git restore` no longer experimental**,
  `git whatchanged` deprecation with `--i-still-use-this`, the Git 3.0 reftable and SHA-256 default
  plans, and the count of **144 built-in commands**.
- <https://about.gitlab.com/blog/whats-new-in-git-2-53-0/> — fetched. Source of: geometric repacking
  with promisor remotes / partial clones, `git fast-import --signed-commits=strip-if-invalid`, and
  `git repo structure` reporting inflated and disk size per object type. Thin on other 2.53
  content; the write pass should re-check the 2.53 release notes directly for anything else.
- <https://about.gitlab.com/blog/whats-new-in-git-2-52-0/>, <https://lwn.net/Articles/1046835/>,
  <https://www.phoronix.com/news/Git-2.52-Released>, <https://www.phoronix.com/news/Git-2.55-Released>,
  <https://lwn.net/Articles/1079596/>, <https://linuxiac.com/git-2-55-lands-with-big-speedups-for-large-linux-repositories/>
  — corroborating the 2.52/2.55 feature lists and the Rust default-on change. Used only for
  cross-checking; the GitHub blog and `BreakingChanges` are authoritative.
- <https://www.helpnetsecurity.com/2025/08/19/git-2-51-sha-256/> and
  <https://cybersecuritynews.com/git-2-51-released/> — **these two sources state or imply that 2.51
  made SHA-256 the default. That is wrong**, and the contradiction with `BreakingChanges` is exactly
  why leaf 1.3.8 carries `[VERSION-TRAP]`. Recorded here as a caution, not as an authority.

**Scaling and performance (primary-ish)**

- <https://github.blog/open-source/git/make-your-monorepo-feel-small-with-gits-sparse-index/> —
  fetched in full. Source of §2.11.6–§2.11.10: the `SKIP_WORKTREE` bit, sparse directory entries,
  cone vs non-cone, `core.sparseCheckout`, `core.sparseCheckoutCone`, `index.sparse`,
  `command_requires_full_index` / `ensure_full_index()`, the per-version list of sparse-aware
  commands, and the measured **180 MB → under 10 MB** index and **1.3 s → under 200 ms**
  `git status` on a 2M-file repository with 100k files in the cone.
- <https://github.blog/open-source/git/bring-your-monorepo-down-to-size-with-sparse-checkout/> and
  <https://github.com/microsoft/scalar> — Scalar's feature set (partial clone, background prefetch,
  sparse-checkout, scheduled maintenance) and the sparse-checkout cone-mode introduction in 2.25.
  Basis of §2.11.5 and §2.11.11.
- <https://www.infoworld.com/article/2337202/how-microsofts-git-fork-scales-for-massive-monorepos.html>
  and <https://blog.gitbutler.com/git-tips-3-really-large-repositories> — the combined-effect
  numbers in §2.11.12 (14 min → 90 s clone; 5 GB → 200 MB working directory; a 50 GB monorepo
  behaving like 500 MB). **These are secondary and the figures are illustrative**; present them as
  reported measurements with attribution, not as guarantees.

**Workflow, review and process**

- <https://www.infoq.com/news/2026/04/github-stacked-prs/> — fetched in full. Source of §2.15.11–
  §2.15.13: the `gh-stack` CLI extension, announcement 29 Apr 2026, private preview 13 Apr 2026,
  `gh stack sync` cascading rebase and force-push, the explicit statement that **squash and rebase
  merges rewrite hashes and break stack identity tracking** so only merge commits work for
  intermediate PRs, the 3–4 PR practical ceiling, and cascading-rebase conflicts as unresolved.
  The public-preview date of **30 Jul 2026** came from the search summary of the same feature and
  **must be re-verified** against GitHub's changelog before the write pass states it.
- <https://graphite.com/guides/merge-queue-comparison-github-gitlab-graphite> and
  <https://mergify.com/learn/trunk-based-development> — merge queue vs GitLab merge trains,
  vertical parallelisation with a static window, per-MR temporary refs with cumulative state, the
  "merge skew" framing, the rename-vs-caller semantic-conflict example, and trunk-based development
  as a DORA-identified practice. Basis of §2.19.4–§2.19.6 and §2.15.1.
- <https://graphite.com/blog/stacked-prs>, <https://ejoffe.github.io/spr/>,
  <https://github.com/arxanas/git-branchless> (via search) — the stacked-PR tool ecosystem in
  §2.15.11, and the corroborating "PRs of 200–400 lines had ~40% fewer defects and were approved
  three times faster" figure in §2.17.11. **This figure is from a vendor blog** — attribute it as
  such and keep the SmartBear/Cisco numbers as the primary evidence.
- The SmartBear/Cisco code-review study numbers (200–400 lines, ~60 minutes, ~500 LOC/hour) are
  carried forward from the current guide. **No primary source for them was successfully fetched in
  this research pass**; the write pass should either cite SmartBear's "Best Kept Secrets of Peer
  Code Review" directly or present the numbers as the widely-reported findings of that study rather
  than as freshly verified measurements.
- <https://github.com/newren/git-filter-repo> — fetched. Source of §2.7.2–§2.7.7: why
  `filter-branch` is discouraged (unusably slow, gotcha-ridden, onerous, not backward-compatibly
  fixable), the option surface, the `commit-map`/`ref-map` outputs, `--analyze`, and the deliberate
  removal of the `origin` remote.
- <https://git-scm.com/book/en/v2> — fetched. The Pro Git 2nd-edition table of contents was mined
  as a completeness checklist and directly produced leaves this syllabus would otherwise have
  missed: credential storage (§1.8.22), bundling (§1.20.14), replace (§1.20.16), the refspec as a
  first-class topic (§1.8.3), the transfer protocols (§3.14), environment variables (§1.12.14),
  "An Example Git-Enforced Policy" (§4.7.4), and the plumbing-command taxonomy of Appendix C
  (§1.20).

**Commit signing, LFS, and misconceptions**

- <https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key>
  and <https://dbushell.com/2023/06/20/git-ssh-verify-allowed-signers/> (via search) — `gpg.format
  = ssh`, `user.signingkey` pointing at a `.pub`, `gpg.ssh.allowedSignersFile`, the allowed-signers
  line format with `namespaces="git"`, SSH signature verification requiring **Git 2.34+**, and the
  fact that GitHub and GitLab verify SSH signatures while Bitbucket does not. Basis of §2.14.3–
  §2.14.4. **Re-verify the allowed-signers line syntax against `man git-config` before writing it.**
- <https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-faq.adoc>,
  <https://manpages.debian.org/testing/git-lfs/git-lfs-filter-process.1.en.html> and
  <https://www.mankier.com/1/git-lfs-smudge> — the pointer-file format, the clean/smudge/process/
  required filter configuration, the process-filter handshake, the memory-scales-with-largest-file
  limitation, `GIT_LFS_SKIP_SMUDGE`, and `git lfs migrate import`. Basis of §2.12.
  **GitHub's specific size limits in §2.12.12 (50 MB warning / 100 MB hard / 1 GB recommended /
  5 GB) were not re-verified in this pass and must be checked against GitHub's current docs.**
- <https://www.biteinteractive.com/picturing-git-conceptions-and-misconceptions/> and
  <https://news.ycombinator.com/item?id=28392566> — the adversarial angle. Confirmed the three
  misconceptions the bible must attack head-on: that Git stores diffs, that Git tracks changes
  rather than commits, and that a branch is something other than a name for a commit. Basis of
  §1.1.5, §1.2.23 and §1.4.22.
- <https://evilmartians.com/chronicles/git-push---force-and-how-to-deal-with-it> and the
  force-push incident write-ups surfaced by the failure-mode search — the cascade described in
  §2.21.7 (everyone's clone diverges, CI caches the wrong commit, artefacts orphan), the fact that
  a force push removes only the branch pointer while the objects survive until GC, and GitHub's
  ~90-day retention of unreachable commits. Basis of §1.16.11 and §2.21.7.

**Searches that returned nothing usable**

- Searches for a *primary* source on the SmartBear/Cisco code-review study returned only secondary
  summaries; see the note above.
- Searches for published **university course syllabi** on Git internals returned nothing beyond
  book tables of contents; the curriculum angle was covered by Pro Git's TOC instead.
- The general "Git interview questions" listings (GeeksforGeeks, Guru99, Intellipaat, Toptal,
  Devinterview-io) were mined only for *question coverage* in §5.1 and contributed no technical
  claims. Their technical content is uniformly shallow and several pages repeat the version-stale
  beliefs catalogued in §5.2.5.
- No authoritative current source was found for a per-operation Git cost table. The complexities in
  §2.1.1–§2.1.2 must be presented as **derived from the mechanism** (with the derivation shown),
  not quoted as measurements.

---

## Gaps vs the current guide

`src/topics/17-git-craft.md` is **706 lines** across 13 sections plus a 56-item checklist. It is a
genuinely good practitioner's guide to *using* Git safely and to reviewing and debugging well — its
undo table, its force-push treatment, its review-priority list and its 1%-bug section are all
strong and must survive verbatim. It is not a bible: it contains **no object model, no plumbing, no
packfiles, no refs storage, no index format, no merge internals, no worktrees, no submodules, no
sparse-checkout or partial clone, no LFS, no signing, no maintenance/gc, no protocols, no version
history, and no build-it content at all**. The table below is the work order.

| Syllabus area | Present in `src/topics/17-git-craft.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why Git exists, design decisions, VCS landscape | — | ✅ entire section | |
| §1.2 the object database (blob/tree/commit/tag) | §1 (one clause: "stores snapshots… SHA-1/SHA-256 hash of its content plus its parent(s)") | ✅ the header format, all four types, tree entry modes, sort order, author vs committer, parent order, the plumbing read/write surface, deduplication | ✅ severely |
| §1.3 hashing, SHA-1DC, the SHA-256 transition | §1 (the phrase "SHA-1/SHA-256") | ✅ everything — SHA-1DC, SHAttered/Shambles, the birthday bound, `--object-format`, abbreviation rules, the Git 3.0 boundary | ✅ severely |
| §1.4 refs, HEAD, packed-refs, reftable | §1 (one sentence: "a branch is a movable pointer… 41 bytes") | ✅ the namespace inventory, `packed-refs`, D/F conflicts, reftable and its measured wins, the pseudo-ref list, `for-each-ref` | ✅ the 41-byte line is good and must be kept and expanded |
| §1.5 the three trees and the index | §1 (a 4-row table) + §2 (`add -p`) | ✅ what the index actually is, stat caching, racy timestamps, the `...` vs `..` diff distinction, conflict stages, cache tree, `ls-files`, `update-index`, `index.lock` | ✅ the table is good and must be preserved |
| §1.6 the DAG and revision syntax | §1 (one sentence on the DAG) | ✅ `~` vs `^`, the full `gitrevisions` grammar, range syntax, history simplification, ordering, pickaxe `-S` vs `-G`, `-L`, `--follow`, `describe`, pathspec magic, merge-base | ✅ |
| §1.7 the daily porcelain | §2 (7 commands) | ✅ clone/init options, shallow-clone consequences, the full `commit` flag set, `commit -v`, `show` on merges, the diff option surface, `--color-moved`, `blame -C`, `.git-blame-ignore-revs`, `git grep`, `last-modified` | ✅ the 7 commands are right and must be kept |
| §1.8 remotes, refspecs, fetch/pull/push | §2 (fetch vs pull vs push, ~25 lines) | ✅ refspec grammar, `push.default`, `push.autoSetupRemote`, transport URLs, credentials, `insteadOf`, HTTP knobs, `ls-remote`, remote groups | ✅ the "fetch is always safe" framing and the `HEAD..origin/main` habit are excellent and must be preserved verbatim |
| §1.9 branches in practice | §3 (why branch at all) | ✅ the `branch` flag surface, why `--merged` lies after squash, `switch`/`restore`, upstream config, branch protection, default-branch rename | ✅ |
| §1.10 tags and releases | — | ✅ entire section | |
| §1.11 ignoring and attributing | §13 (`.gitignore`, `check-ignore`, the tracked-file trap) | ✅ the whole of `.gitattributes`, line endings, the negation-below-excluded-directory trap, `merge=union`, `export-ignore` | ✅ the `.gitignore` content and the two traps must be preserved verbatim |
| §1.12 configuration resolution | — | ✅ entire section — and `includeIf` for work/personal identity is a daily-value item nobody teaches | |
| §1.13 merging: the model | §4 (merge described in two sentences) | ✅ fast-forward, `--no-ff`/`--ff-only`/`--squash`, merge state files, octopus, `ours` strategy vs `-X ours`, semantic conflicts, `merge-tree` | ✅ |
| §1.14 rebasing: the model | §4 (rebase described in two sentences + the diagram) | ✅ `--onto`, `--keep-base`, `--fork-point`, `--exec`, `--update-refs`, `--rebase-merges`, the two backends, patch-id dropping | ✅ the diagram, the comparison table and the golden rule must be preserved verbatim |
| §1.15 the undo surface | §6 (the 8-row table + decision rule + 2 traps + merge revert) | ✅ `reset --merge` and `--keep`, `reset <paths>`, `ORIG_HEAD`, revert-the-revert, the revert cost of each merge strategy, `rm --cached` consequences | ✅ **§6 is the guide's best content; every row, both traps and the `-m 1` sequel must survive verbatim** |
| §1.16 the reflog | §7 (mechanism, recovery, limits, `fsck --lost-found`) | ✅ the line format, the message vocabulary, `core.logAllRefUpdates`, bare repos having no reflog, remote-tracking reflogs, reftable logs | ✅ **the recovery recipes and the "commit early and often" conclusion must survive verbatim** |
| §1.17 stash | §9 (7 commands + advice) | ✅ stashes are commits, `--keep-index`, `stash branch`, `export`/`import`, the pop-on-conflict trap, recovering a dropped stash | ✅ the commands and the "prefer a WIP commit" advice must be preserved |
| §1.18 cherry-pick | §9 (3 commands + the duplicate-commits warning) | ✅ the mechanism, the range gotcha, `-m` on merges, `git cherry`/patch-id, `format-patch`/`am`, `range-diff` | ✅ **the `-x`-for-backports rule and the "not a substitute for merging" warning must survive verbatim** |
| §1.19 a tour of `.git/` | — | ✅ entire section | |
| §1.20 plumbing vs porcelain | — | ✅ entire section including `notes`, `replace`, `bundle`, `fast-export` | |
| §1.21 versions and Git 3.0 | §6 (one parenthetical: "Git 2.23+"), §4 (one: "Git 2.30+") | ✅ entire section — and it is the highest-value single addition, because most of this topic's folklore is version-stale | |
| §2.1 the master tables | — | ✅ all eight | |
| §2.2 merge vs rebase decided | §4 (the table + golden rule + standard workflow) | ✅ the concurrency-assertion framing, the untested-intermediate-commit problem, `--first-parent` bisect, the host merge-button mapping | ✅ the table and the golden rule are excellent and must be preserved verbatim |
| §2.3 merge strategies and `-X` | — | ✅ entire section — the guide never names `ort` at all | |
| §2.4 conflict resolution | §5 (markers, the ours/theirs trap, the procedure, `--ours`/`--theirs`, prevention) | ✅ the conflict taxonomy, `zdiff3`, `log --merge`, `show :2:<path>`, `AUTO_MERGE`, mergetools, binary and lock-file conflicts | ✅ **the ours/theirs trap, the procedure and the prevention list must survive verbatim** |
| §2.5 rerere | §5 (three sentences) | ✅ the conflict-ID mechanism, the three files, the subcommands, the expiry defaults, the wrong-resolution trap | ✅ severely |
| §2.6 interactive rebase and `git history` | §9 (the todo example with 5 commands + `--autosquash`) | ✅ the full todo vocabulary, `--fixup=amend:`/`reword:`, `--update-refs`, splitting commits, `git history reword/split/fixup`, scripting the sequence editor | ✅ the todo example must be preserved and completed |
| §2.7 history rewriting at scale | §13 (two `filter-repo` commands) | ✅ the tool comparison, the full option surface, `--analyze`, `commit-map`, the coordination protocol, `.mailmap`, `git replay` | ✅ |
| §2.8 bisect | §8 (the sequence, `bisect run`, exit codes, 4 gotchas) | ✅ the full exit-code range, `terms`, `--first-parent`, `log`/`replay`, the script-disappears trap, the stale-artefact trap, flaky and perf bisection | ✅ **§8 is strong; the 0/1/125 contract and the four requirements must survive verbatim** |
| §2.9 worktrees | — | ✅ entire section | |
| §2.10 submodules, subtrees, monorepo | — | ✅ entire section | |
| §2.11 sparse-checkout, partial clone, sparse index, Scalar, maintenance | — | ✅ entire section — and it is the answer to "how do you work in a huge repository", which is a standard senior question | |
| §2.12 Git LFS | — | ✅ entire section | |
| §2.13 hooks | §5 (one clause: "a pre-commit hook removes whitespace conflicts"), §13 (secret scanning) | ✅ entire section — the full hook inventory, config-based hooks, parallel hooks, the bypass trap, the four buildable hooks. **The index scope line promises "hooks" and the guide does not deliver them.** | ✅ severely |
| §2.14 signing and provenance | — | ✅ entire section | |
| §2.15 branching models | §3 (trunk-based, feature flags, `main` deployable) | ✅ GitFlow/GitHub Flow/GitLab Flow named and compared, release branches, branch-by-abstraction, expand/contract, stacked PRs and the tooling, fork workflow | ✅ **the "`main` must be deployable" invariant and the feature-flag framing must survive verbatim** |
| §2.16 the PR as an artefact | §3 (PR discipline + the 3-strategy table) | ✅ the description template, `CODEOWNERS`, auto-merge races, draft PRs, review-request policy, the commit-series PR | ✅ **the discipline list and the strategy table must survive verbatim** |
| §2.17 code review method | §11 (priority order, PR sizing evidence, comment labels, question form, norms) | ✅ per-row sub-checklists, Conventional Comments, reviewing refactors, reviewing AI-generated PRs, review anti-patterns, the force-push-orphans-comments trap, review metrics | ✅ **§11 is the guide's second-best section; every element must survive verbatim, including the "failed review" sentence and the 200–400/60min/500LOC numbers** |
| §2.18 commit message craft | §10 (the example, the rules, the test, Conventional Commits) | ✅ the 50/72 arithmetic, trailers and `interpret-trailers`, DCO, the full Conventional Commits spec and its SemVer mapping, `commit.template`/`cleanup`, the enforcing hook | ✅ **the worked example, the rules and the eighteen-months test must survive verbatim** |
| §2.19 CI integration and merge queues | §3 (one clause: "CI on every PR") | ✅ entire section — the stale-base problem, semantic conflicts, merge queues and trains, throughput arithmetic, the `fetch-depth` trap, deploy provenance, GitOps | ✅ severely |
| §2.20 secrets in history | §13 (rotate → audit → clean → coordinate → prevent) | ✅ the `--replace-text` format, detection at scale, what counts as a secret, the incident write-up, the executable runbook | ✅ **§13's ordered response and the "rotate first, clean second" rule must survive verbatim — it is the best-argued paragraph in the guide** |
| §2.21 the recovery cookbook | §6/§7 (scattered) | ✅ all 23 scenarios as a structured cookbook with symptom → diagnosis → fix → verification, including corruption, `index.lock`, CI diff failures, line-ending explosions, and rule zero (take a backup first) | ✅ |
| §2.22 debugging methodology | §12 (the loop, "what changed", correlation IDs, the 1% bug) | ✅ the Git tools tied into the loop, writing the session down | ✅ **§12 is excellent and must survive essentially verbatim — the 8-step loop, the "what changed" list, the MDC code and trap, and all five 1%-bug steps including the 1/N signal** |
| §2.23 repository archaeology | §12 (one command: `git log --since`) | ✅ entire section | |
| §2.24 repository health and maintenance | — | ✅ entire section — every gc default, cruft packs, geometric repacking, bitmaps | |
| §2.25 ergonomics and tooling | — | ✅ entire section | |
| §3.1 loose object storage | — | ✅ | |
| §3.2 packfiles and deltas | — | ✅ — the single largest internals gap | |
| §3.3 `.idx`/`.rev`/MIDX/bitmaps | — | ✅ | |
| §3.4 the index file format | — | ✅ | |
| §3.5 ref backends in depth | — | ✅ | |
| §3.6 reflog format | §7 (three example lines) | ✅ the format, the message vocabulary, `core.logAllRefUpdates`, GC-root semantics, the no-reflog-on-bare fact | ✅ the example lines are good and must be kept |
| §3.7 diff algorithms | — | ✅ — Myers, patience, histogram, the indent heuristic, `--color-moved` | |
| §3.8 rename and copy detection | — | ✅ — including the silent rename-limit failure, which is a real merge hazard | |
| §3.9 three-way merge and merge-ort | §5 (implicit) | ✅ entire section — the base's role, criss-cross, virtual merge bases, ort's architecture and fast paths, `zdiff3` mechanics | ✅ |
| §3.10 the sequencer | — | ✅ — and it explains the ours/theirs swap the guide correctly warns about but does not justify | |
| §3.11 rerere internals | — | ✅ | |
| §3.12 commit-graph and generation numbers | — | ✅ | |
| §3.13 reachability, gc, pruning | §7 (one parenthetical on 90/30 days) | ✅ the root set, the grace-period proof, cruft packs, geometric repacking, `fsck` internals | ✅ the 90/30 numbers are correct and must be kept |
| §3.14 the transfer protocols | — | ✅ | |
| §3.15 filters and the checkout pipeline | — | ✅ | |
| §3.16 performance engineering | — | ✅ | |
| §3.17 concurrency, atomicity, corruption | — | ✅ | |
| §3.18 reading Git's source | — | ✅ | |
| PART 4 — every `[BUILD]` (§4.1–§4.7) | — | ✅ all 71 leaves; the current guide contains no implementable content beyond one Java servlet-filter snippet | ✅ the MDC filter snippet must be preserved, modernised to Java 21 and re-domained |
| PART 5 — the question bank | — | ✅ all ~146 questions | |
| PART 5 — the trap index | 8 `**Trap:**` markers inline | ✅ all eight must be preserved and the rest added | |
| PART 5 — the drills | closing checklist (56 lines) | ✅ the numbers/command/recovery/reading/whiteboard/explanation drills | ✅ **the 56-line checklist must be preserved verbatim and extended, not rewritten — downstream agents parse it** |

Three corrections the write pass **must** make to existing text, not merely additions:

1. §1 of the current guide says commits are "addressed by the SHA-1/SHA-256 hash of its content plus
   its parent(s), author, and message". That is right in spirit but omits the object header and the
   *tree*, and it implies a repository can be either hash at will. State precisely what is hashed
   (`<type> <size>\0<content>`, where a commit's content includes the tree line), and state that
   the hash algorithm is a **repository-wide format choice** fixed at `init`, still defaulting to
   SHA-1 in 2.55.
2. §4 of the current guide calls `--force-with-lease` a comparison "against your remote-tracking
   ref" and correctly notes the blind-fetch defeat. It should also say that the lease can be given
   explicitly (`--force-with-lease=<ref>:<expected-oid>`), which is the form that is actually safe
   in a script, and that `--force-if-includes` (2.30+) is the flag to alias by default.
3. §7 of the current guide gives reflog retention as "~90 days for reachable-from-reflog, 30 for
   unreachable". The numbers are right but they are `gc.reflogExpire` and
   `gc.reflogExpireUnreachable`, they are configurable per ref pattern, and — critically — **a bare
   repository has no reflog at all by default**. The current text implies the safety net is
   universal, and on the server it is not.

Eight passages in the current guide are strong and must survive **verbatim or expanded**, not
rewritten: the four-areas table (§1), the "fetch is always safe" paragraph (§2), the merge-vs-rebase
diagram and comparison table plus the golden rule (§4), the ours/theirs rebase trap (§5), the
undo decision table with both destruction traps and the `revert -m 1` sequel (§6), the reflog
recovery recipes with the "commit early and often" conclusion (§7), the review priority order with
the PR-sizing evidence and the comment-label taxonomy (§11), and the rotate-first-clean-second
ordering for leaked secrets (§13).

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.21 | 390 |
| PART 2 — Intermediate | §2.1–§2.25 | 409 |
| PART 3 — Under the hood | §3.1–§3.18 | 279 |
| PART 4 — Build it | §4.1–§4.7 | 71 |
| PART 5 — Interview and retention | §5.1–§5.3 | 34 |
| **Total** | **74 sections** | **1183 leaves** |

`[RESEARCH]`-tagged leaves: **178** (PART 1: 41, PART 2: 74, PART 3: 55, PART 4: 1, PART 5: 0).
Each must be re-verified against its cited source during the write pass before any constant from it
is written down. The highest-risk clusters are:

- **Every Git 2.51–2.55 feature claim** (§1.21.10, §2.6.12–§2.6.14, §2.11.16–§2.11.18,
  §2.13.10–§2.13.11, §2.24.9–§2.24.13) — these are the leaves most likely to be misremembered or
  half-right, and they are also the ones that most distinguish a current answer from a 2024 one.
- **The SHA-256 / reftable default status** (§1.3.8, §1.4.9, §1.21.4) — at least two secondary
  sources found during research assert that 2.51 already made SHA-256 the default. It did not.
  Verify against `git help BreakingChanges` on a 2.55 build, not against a news article.
- **Every `gc.*` and `maintenance.*` default** (§2.24.4, §2.11.18, §3.13.6) — taken from the current
  man pages, but `gc.maxCruftSize` deliberately has **no value stated here** because the page did
  not give one. Do not invent it.
- **The GitHub stacked-PR public-preview date** (§2.15.11) — the private-preview and announcement
  dates are from InfoQ; the 30 Jul 2026 public-preview date is from a search summary only.
- **GitHub's LFS and file-size limits** (§2.12.12) — not re-verified in this pass.
- **The SmartBear/Cisco review numbers** (§2.17.10) — carried from the current guide, no primary
  source fetched. Attribute rather than assert.
- **The Scalar combined-effect figures** (§2.11.12) — secondary, illustrative, must be attributed.

A note on balance for the write pass: PART 1 is deliberately the largest part because this topic's
"basics" include the entire command surface, and a bible that leaves a command unnamed sends the
reader elsewhere. PART 3 is smaller than PART 1 in leaf count but is the part that will take the
most words per leaf — every `[SOURCE]` and `[HEX]` leaf in it requires a real excerpt read byte by
byte. If the file exceeds ~2500 lines, split at the PART 2/PART 3 boundary into
`17-git-craft.md` (PARTS 1–2) and `17-git-craft-internals.md` (PARTS 3–5), cross-link both, keep an
`## Atomic concept checklist` in each, and add the new file to `src/topics/00-index.md`.



