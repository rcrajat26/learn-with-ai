# 17 — Git Craft, Code Review & Debugging Method

Scope: the day-to-day craft signals that separate a mid-level engineer from a senior one. Git
mechanics (including the recovery tools), how to review code, and how to debug systematically rather
than by guessing.

---

## 1. The mental model: three trees and a graph

Git tracks **snapshots**, not diffs. Every commit stores a full tree, addressed by the SHA-1/SHA-256
hash of its content plus its parent(s), author, and message. Because the hash covers the parent, the
history is a tamper-evident **directed acyclic graph** — and changing any old commit necessarily
changes every commit after it. That single fact explains rebasing, force-pushing, and why rewriting
shared history is disruptive.

Four places a change can live:

| Area | What it is | Moves out with |
|---|---|---|
| **Working directory** | your files on disk | `git add` |
| **Index / staging area** | the proposed next commit | `git commit` |
| **Local repository** | your commit graph | `git push` |
| **Remote repository** | the shared graph | `git fetch` (inbound) |

A **branch is just a movable pointer to a commit.** `HEAD` points to the current branch (or directly
to a commit when "detached"). Creating a branch is writing 41 bytes to a file — which is why branching
is free in Git and was expensive in older VCSs, and why "branch liberally" is sound advice.

---

## 2. Core mechanics

```bash
git status                      # the single most useful command; run it constantly
git add -p                      # stage HUNK BY HUNK — review your own diff as you stage
git commit -m "subject"         # commit staged changes
git commit --amend              # rewrite the last commit (message or content)
git log --oneline --graph --decorate --all      # see the actual DAG
git diff                        # working dir vs index
git diff --staged               # index vs HEAD  (what you're about to commit)
git diff main...HEAD            # what my branch adds relative to the merge base
```

`git add -p` deserves emphasis: it forces you to read every hunk before committing, which catches
stray debug statements, commented-out code, and accidental file inclusions before a reviewer does. It
also makes it natural to split unrelated changes into separate commits.

### fetch vs pull

```bash
git fetch origin                # download remote commits; touch NOTHING local
git pull                        # = fetch + merge  (creates a merge commit)
git pull --rebase               # = fetch + rebase (linear; usually what you want)
git config --global pull.rebase true    # make rebase the default
```

**`fetch` is always safe.** It updates your remote-tracking refs (`origin/main`) and changes nothing
in your working tree. `pull` is `fetch` plus an *integration step that can conflict or rewrite*.
Habit worth building: `git fetch && git log --oneline HEAD..origin/main` to see what's incoming
*before* you integrate it.

### push

```bash
git push -u origin feature/x    # set upstream on first push
git push --force-with-lease     # safe force — see §4
git push --force                # DANGEROUS — see §4
```

A push is rejected when the remote has commits you don't have. The fix is to integrate (rebase or
merge) then push — **never** to reach for `--force` reflexively, which is the reflex that deletes a
colleague's work.

---

## 3. Branching and PR discipline

**Why branch at all?** So that `main` is always releasable. If work in progress lives on `main`, you
cannot deploy a hotfix without shipping someone's half-finished feature. Trunk-based development with
short-lived branches (hours to a couple of days) is the norm at high-performing organisations; long
branches are where merge pain and integration bugs come from.

The rule to state in an interview: **`main` must be deployable at every commit.** Everything else —
CI on every PR, required reviews, protected branches, feature flags — is machinery in service of
that one invariant.

**Feature flags decouple deploy from release.** Merge incomplete work behind a flag that's off in
production, rather than keeping a branch open for three weeks. You get continuous integration, small
diffs, and the ability to turn a feature off without a rollback. Cost: flag debt — every flag needs an
owner and a removal date.

**PR discipline:**
- Small (see §11 for the evidence), single-purpose, with a description covering **what changed, why,
  and how it was verified**.
- CI green before requesting review. Don't spend a reviewer's attention on something the build would
  have caught.
- Self-review the diff in the web UI first. You will find something every time.
- Link the ticket; include screenshots or the actual test output for behavioural change.
- Rebase on `main` before merging so CI tests what will actually land.

**Merge strategies for the PR itself:**

| Strategy | Result | Best for |
|---|---|---|
| **Merge commit** | preserves all commits + a merge node | large features where the individual commits are meaningful |
| **Squash merge** | one commit on `main` per PR | the common default: clean history, one revertable unit, messy WIP commits disappear |
| **Rebase merge** | replays commits linearly, no merge node | when every commit is individually well-formed and tested |

Squash-merge is the pragmatic default because it makes `git revert` and `git bisect` operate on
whole, coherent features.

---

## 4. Merge vs rebase

**Merge** creates a new commit with two parents, joining the histories. Nothing is rewritten; the
history shows what actually happened, including the topology of parallel work.

**Rebase** replays your commits one at a time onto a new base. The result is linear — but the replayed
commits are **new objects with new hashes**. The originals are orphaned (recoverable via reflog, §6).

```
Merge:                          Rebase:
      A---B---C feature               A'--B'--C' feature
     /         \                     /
D---E---F---G---H main        D---E---F---G main
```

| | Merge | Rebase |
|---|---|---|
| History | true, branching | linear, readable |
| Hashes | preserved | rewritten |
| Conflicts | resolved once | potentially once **per commit** |
| Safe on shared branches | yes | **no** |
| `git bisect` / `git log` | noisier | cleaner |

### The golden rule

> **Never rebase commits that others have based work on.**

Rewriting shared history means everyone else's clone disagrees with the remote about what the
commits *are*. Their next `pull` produces duplicated commits or a mess of conflicts. In practice:
rebase freely on your own unpushed or unshared feature branch; never on `main`, `develop`, a release
branch, or a branch a colleague has checked out.

Standard workflow: **rebase your feature branch onto `main` to keep it current; merge (or
squash-merge) the feature into `main` at the end.** You get a linear, readable history and never
rewrite anything shared.

### `--force-with-lease`

After rebasing an already-pushed feature branch you must force-push — the remote's commits no longer
exist in your history.

```bash
git push --force-with-lease
```

`--force` says "make the remote match me, whatever is there" — if a colleague pushed to your branch
in the meantime, their commits are **silently destroyed**.

`--force-with-lease` says "make the remote match me, **but only if it's still at the commit I last
saw**." If someone else pushed, the push is rejected and you investigate. It costs nothing and
prevents the worst Git accident there is. Alias it; never type plain `--force`.

Caveat worth knowing: `--force-with-lease` compares against your remote-tracking ref, so a
`git fetch` immediately beforehand updates the "lease" and quietly removes the protection. Use
`--force-with-lease` *without* a preceding blind fetch, or use `--force-if-includes` (Git 2.30+) which
also verifies you've actually integrated what's there.

---

## 5. Conflict resolution

A conflict occurs when two branches change the same region of the same file, or when one edits a file
the other deleted. Git cannot decide which intent wins, so it asks you.

```
<<<<<<< HEAD
int timeout = 30;          ← "ours": the branch you're on / rebasing onto
=======
int timeout = 60;          ← "theirs": the incoming commits
>>>>>>> feature/timeouts
```

> **Trap:** "ours" and "theirs" **swap meaning during a rebase.** In a merge, "ours" is your current
> branch. In a rebase, your commits are being replayed *onto* the other branch, so "ours" is the
> **upstream** branch and "theirs" is **your own** work. Reversing them here is how people accidentally
> discard their entire change. When unsure, use `git log --merge` or `git diff` to see the content
> rather than trusting the label.

**Procedure:**
```bash
git status                     # 1. list conflicted files
git diff                       # 2. see the conflicts
# 3. edit each file: understand BOTH intents, produce code that satisfies both.
#    Do not just pick a side because it compiles.
git add <file>                 # 4. mark resolved
# 5. RUN THE TESTS. A resolution that compiles is not a resolution that works.
git commit                     # merge:  finish
git rebase --continue          # rebase: proceed to the next commit
git merge --abort  /  git rebase --abort    # bail out safely at any point
```

`git checkout --ours <file>` / `--theirs <file>` take one side wholesale — fine for lock files and
generated artefacts, dangerous for hand-written code.

**Reducing conflicts** matters more than resolving them well: small PRs, short-lived branches,
frequent rebases onto `main`, and agreed formatting (a committed formatter config plus a pre-commit
hook removes whitespace conflicts entirely).

`git rerere` ("reuse recorded resolution") remembers how you resolved a conflict and replays it
automatically next time — genuinely useful during a long rebase where the same conflict recurs on
every commit. Enable with `git config --global rerere.enabled true`.

---

## 6. Undo: revert vs reset vs restore

This table is worth memorising outright. Picking the wrong tool here is how people lose work.

| Command | What it does | History | Safe on pushed commits? |
|---|---|---|---|
| `git revert <sha>` | creates a **new** commit that undoes `<sha>` | adds to it | **Yes — the only correct option** |
| `git reset --soft <sha>` | moves HEAD; **keeps** index and working dir | rewrites | no |
| `git reset --mixed <sha>` (default) | moves HEAD, resets index, **keeps** working dir | rewrites | no |
| `git reset --hard <sha>` | moves HEAD, resets index **and working dir** — uncommitted work is gone | rewrites | no |
| `git restore <file>` | discards working-dir changes to a file | none | n/a (but the change is gone) |
| `git restore --staged <file>` | unstages, keeps the change | none | n/a |
| `git checkout <sha> -- <file>` | pull one file from another commit | none | n/a |
| `git clean -fd` | delete untracked files/dirs | none | **irreversible — not even reflog** |

**Decision rule:**
- The commit is **pushed / shared** → `git revert`. Always. It's the only undo that doesn't rewrite
  history others depend on, and it leaves an auditable record of the decision.
- The commit is **local only** → `reset` is fine, and often nicer.
- Want to **redo the last few commits differently** → `git reset --soft HEAD~3` puts all three commits'
  changes back in the index, ready to recommit as one.
- Want to **unstage** something → `git restore --staged <file>`.
- Want to **throw away** working changes → `git restore <file>` (verify first; this is unrecoverable).

`git restore` and `git switch` (Git 2.23+) exist because `git checkout` was overloaded to do four
unrelated things. Prefer the modern, unambiguous commands.

> **Trap:** `git reset --hard` **discards uncommitted work irrecoverably** — the reflog can recover
> *commits*, but never anything that was only in your working directory. If you're unsure, `git stash`
> first; it costs a second and it's a real commit under the hood.

> **Trap:** `git clean -fd` deletes untracked files. Config files, `.env`, local scratch scripts, and
> anything gitignored (with `-x`) are gone with no recovery path. Run `git clean -nd` (dry run) first,
> every time.

**Reverting a merge commit** needs `-m 1` to say which parent is "mainline":
```bash
git revert -m 1 <merge-sha>
```
And note the sequel: re-merging that branch later won't reintroduce the changes, because Git thinks
they were already merged. You must revert the revert. This surprises everyone once.

---

## 7. Reflog — the safety net that makes Git nearly lossless

**Mechanism.** Every time `HEAD` moves — commit, checkout, reset, rebase, merge, amend — Git appends
an entry to the reflog recording the previous position. Orphaned commits remain in the object
database (default: ~90 days for reachable-from-reflog, 30 for unreachable) until garbage collection.

```bash
git reflog
# 7a1b2c3 HEAD@{0}: reset: moving to HEAD~3
# 9f8e7d6 HEAD@{1}: commit: add retry with backoff      ← the work I "lost"
# 3c4d5e6 HEAD@{2}: commit: extract client
```

**Recovery:**
```bash
git reflog                          # find the SHA of the good state
git reset --hard HEAD@{1}           # go back to it
# or, non-destructively:
git branch recovered 9f8e7d6        # give the orphaned commit a name
git cherry-pick 9f8e7d6             # or just take that one commit
```

This recovers from: a bad `reset --hard`, a botched rebase, a deleted branch, a bad `--force` push
(the old commits are still local), a wrong `amend`. **The only things it cannot recover are changes
that were never committed** — uncommitted working-directory edits, and files removed by `git clean`.

Practical implication: **commit early and often on your own branch.** Once something is committed, it
is essentially impossible to lose. Ugly WIP commits can be squashed later (§9). This is the single
highest-value Git habit.

Also: `git fsck --lost-found` finds dangling commits that even the reflog missed (e.g. from an
abandoned rebase in a different working tree).

---

## 8. Bisect — binary search for the commit that broke it

You know it worked at v1.4 and it's broken at HEAD, with 400 commits in between. Reading them is
hopeless; bisecting is ~9 tests.

```bash
git bisect start
git bisect bad                 # HEAD is broken
git bisect good v1.4           # this tag was fine
# Git checks out the midpoint. Test it, then:
git bisect good     # or: git bisect bad
# ...repeat ~log2(N) times...
# → "abc1234 is the first bad commit"
git bisect reset               # return to where you were
```

**Automate it** — this is where bisect becomes genuinely powerful:
```bash
git bisect start HEAD v1.4
git bisect run ./scripts/reproduce.sh
```
The script must **exit 0 for good, 1 for bad, and 125 for "cannot test this commit"** (doesn't
compile, etc.). Git then walks the whole search unattended. A test that reliably reproduces the bug
plus `bisect run` will find a regression in a 10,000-commit history in minutes.

Requirements and gotchas:
- You need a **deterministic, fast reproduction**. Investing 20 minutes in a reliable repro script is
  almost always worth it.
- Every commit must be buildable — another argument for keeping `main` green and for squash-merging
  PRs so that no commit on `main` is a broken intermediate state.
- `git bisect skip` for untestable commits.
- Works for performance regressions too: make the script assert a threshold.

---

## 9. Stash, cherry-pick, and interactive rebase

### Stash
```bash
git stash push -m "wip: retry logic"    # shelve tracked changes
git stash -u                            # include untracked files (often what you want)
git stash list
git stash show -p stash@{0}             # inspect before applying
git stash pop                           # apply and remove
git stash apply stash@{1}               # apply and keep
git stash drop / git stash clear
```
For "I need to switch branches right now." Don't let stashes accumulate — an unlabelled stash from
three weeks ago is unidentifiable. A WIP commit on a branch is usually better than a stash, because
it's named, pushable, and visible in the reflog.

### Cherry-pick
```bash
git cherry-pick <sha>            # apply that commit's change here as a new commit
git cherry-pick <sha1>..<sha2>   # a range
git cherry-pick -x <sha>         # record the source SHA in the message — do this for backports
```
Legitimate use: backporting a hotfix from `main` to a release branch. **Illegitimate use:** as a
substitute for merging — repeated cherry-picking creates duplicate commits with different hashes, and
a later merge between the two branches conflicts against changes that are logically already there.

### Interactive rebase
```bash
git rebase -i HEAD~5
git rebase -i main            # clean up everything since branching
```
```
pick   a1b2c3 add retry client
squash d4e5f6 fix typo              ← fold into the previous commit
reword 7g8h9i add backoff           ← edit the message
edit   j1k2l3 extract config        ← stop here to amend the content
drop   m4n5o6 debug logging         ← remove entirely
# reorder lines to reorder commits
```
Use it to turn eight messy WIP commits into two coherent ones before opening the PR. `--autosquash`
with `git commit --fixup=<sha>` automates the common case. Same golden rule as §4: **only on unshared
commits.** If your team squash-merges PRs anyway, this matters less — but a clean commit series still
makes review substantially easier.

---

## 10. Commit message craft

```
Add exponential backoff to payment client retries

The payment gateway returns 503 during their nightly maintenance window,
and our fixed 100ms retry interval turned a 30-second blip into a
5-minute outage as retries from all 12 pods synchronised.

Uses full jitter (random 0..cap) rather than plain exponential so that
retries from multiple instances spread out rather than arriving in waves.
Cap is 30s, matching the gateway's documented recovery time.

Fixes PAY-4821
```

**Rules:**
- **Subject:** imperative mood ("Add", "Fix", "Remove" — completing the sentence "this commit
  will…"), ≤50 chars, capitalised, no trailing period.
- **Blank line** after the subject. Git tooling depends on it.
- **Body wrapped at 72 chars**, explaining **why**, not what. The diff already shows what changed;
  it cannot show what you knew, what you rejected, or what constraint forced the design.
- Reference the ticket/issue.

**The test:** in eighteen months someone will `git blame` this line during an incident. Does the
message tell them why the line exists? "Fix bug", "update", "changes", and "address PR comments" fail
that test completely.

Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`) add machine-readable structure and can
drive semantic versioning and changelogs. Useful if the team adopts it consistently; the *why* in the
body matters more than the prefix.

---

## 11. Code review method

### Priority order — review in this sequence, and weight comments accordingly

1. **Correctness.** Does it do what it claims? Off-by-ones, null/empty handling, error paths,
   concurrency, transaction boundaries, edge cases at boundaries.
2. **Security.** Injection (SQL/command/template), authz checks on every entry point (not just the UI),
   secrets in code or logs, unvalidated input, sensitive data in log lines, dependency risk.
3. **Tests.** Do they cover the *behaviour*, including the failure paths, or just the happy path?
   Would they actually fail if the code were wrong?
4. **Design and maintainability.** Right abstraction level, sensible boundaries, no duplicated
   concept, fits the existing architecture, doesn't leak internals.
5. **Performance.** N+1 queries, unbounded collections, missing indexes, synchronous calls in a hot
   loop, unbounded caches. Only where it matters — don't micro-optimise cold paths.
6. **Operability.** Can you debug this at 3am? Logging with context, metrics, error messages that name
   the failing input, timeouts on every remote call.
7. **Style — last, and ideally not by you.** Formatting, naming conventions, import order. **This
   should be automated** (formatter, linter, CI check). Human attention spent on style is human
   attention not spent on items 1–6, and style comments are what make reviews feel adversarial.

A review that produces six style nits and misses a missing authorisation check is a failed review,
even though it looks thorough.

### PR sizing — the evidence

The empirical findings (SmartBear's Cisco study and the broader review literature) are consistent:
- Defect-detection effectiveness drops sharply beyond **200–400 changed lines**.
- Review effectiveness falls off after **~60 minutes** of continuous reviewing.
- Reviewing faster than ~500 LOC/hour finds materially fewer defects.

The practical consequence: **a 1,000-line PR does not get reviewed, it gets approved.** Reviewers
skim, spot two cosmetic things, and hit approve — and everyone can feel it happening. Splitting the
same change into four 250-line PRs finds several times more defects for the same total effort.

How to split: separate refactoring from behaviour change (a pure-refactor PR is fast to review and
makes the behavioural diff legible), land infrastructure/scaffolding first, use feature flags to merge
incomplete work, and split by layer or by endpoint. If a PR genuinely can't be split, review it
**commit by commit** and say so in the description.

### Blocking vs non-blocking — label every comment

Ambiguity about whether a comment must be addressed is the main source of review friction. Adopt
explicit prefixes:

- **`blocking:`** — must change before merge (a bug, a security hole, missing tests on new logic).
- **`suggestion:`** — I'd prefer this; your call.
- **`nit:`** — trivial/cosmetic; feel free to ignore. (If you have more than a couple, automate them
  instead.)
- **`question:`** — I don't understand; explain or clarify.
- **`praise:`** — genuinely useful. Reviews that are 100% criticism corrode a team, and pointing out a
  good decision teaches as effectively as pointing out a bad one.

### Question-form feedback

Compare:
- ✗ "This is wrong, it'll NPE when the list is empty."
- ✓ "What happens here if `items` is empty — does `get(0)` throw?"

The question form is better for three concrete reasons, not just politeness:
1. **You might be wrong.** There may be an upstream guarantee you can't see. An assertion that turns
   out false costs you credibility; a question costs nothing.
2. **It transfers the reasoning.** The author works out the answer and remembers it. Being told the
   answer teaches much less.
3. **It's not personal.** It targets the code's behaviour rather than the author's competence, which
   keeps the discussion technical.

Other norms worth stating: review promptly (a PR blocked for two days is worse than a slightly worse
review delivered in two hours); explain the *why* behind requested changes and link a reference;
approve with minor comments rather than blocking on nits; and **take the discussion to a call after
two round trips** — a five-minute conversation beats a twenty-comment thread, with the conclusion
written back into the PR.

As an **author**: respond to every comment (even "done"), don't take it personally, push fixes as
separate commits so the reviewer can see just the delta, and re-request review explicitly.

---

## 12. Debugging methodology

The difference between an hour and a day is almost never knowledge — it's method. Random changes
until the symptom disappears is the default failure mode, and it produces "fixes" that mask the bug.

### 12.1 Hypothesis-driven debugging

The loop:

1. **Observe precisely.** What is the *exact* error, the exact input, the exact time, the affected
   scope? "The API is broken" is not an observation. "POST /orders returns 500 for tenant 42 since
   14:03, ~8% of requests, `NullPointerException` in `PricingService:88`" is.
2. **Reproduce.** A reliable reproduction is most of the fix. Without one, you cannot know whether you
   fixed it or the symptom moved. Shrink it to the smallest case that still fails.
3. **Form a hypothesis.** A *specific, falsifiable* statement: "the price is null because the
   currency-conversion cache returns null for currencies added after startup."
4. **Predict.** "If that's true, then it fails only for currencies added today, and the cache metric
   shows a miss."
5. **Test the prediction** — one variable at a time.
6. **Confirm or discard, and iterate.** Discarding a hypothesis is progress; note it so you don't
   re-test it at hour four.
7. **Fix the cause, not the symptom.** A null check that hides a missing cache entry is not a fix.
8. **Add a regression test** that fails before the fix and passes after. Otherwise the bug comes back.

**Binary search the problem space.** Bisect the code path (does the value exist at the service
boundary? at the repository? in the DB?), bisect the timeline (`git bisect`, §8), bisect the input
(which field triggers it?), bisect the environment (staging vs prod — what differs?). Each bisection
halves the search space; guessing does not.

### 12.2 What changed first

Before deep investigation, ask: **what changed?** The overwhelming majority of production incidents
correlate with a change.

- A deploy — yours or a dependency's? (`git log --since='2 hours ago'`, deployment history)
- Config or a feature flag toggled?
- Traffic pattern — a marketing campaign, a new client, a batch job, a retry storm?
- Data — a new tenant, a large record, a null that was never null before, a migration?
- Infrastructure — a scaling event, a node replacement, a certificate expiry, a DNS change?
- Time itself — month-end, DST, a certificate or token expiring, a leap day?

**Correlate the symptom's start time with the change log.** This single step resolves a large fraction
of incidents in minutes and is the first thing an experienced on-call engineer does. If nothing
changed on your side, something changed on someone else's.

### 12.3 Correlation IDs and distributed debugging

In a distributed system, the logs of one service are almost useless alone. A **correlation ID**
(a.k.a. request ID, trace ID) generated at the edge and propagated through every call — HTTP header,
message property, MDC — is what makes it possible to reconstruct one request's path.

```java
// Inbound filter
String correlationId = request.getHeader("X-Correlation-Id");
if (correlationId == null) correlationId = UUID.randomUUID().toString();
MDC.put("correlationId", correlationId);
try {
    chain.doFilter(request, response);
} finally {
    MDC.clear();                     // essential: threads are pooled and reused
}
```

Then propagate it on every outbound HTTP call and every message you publish, and include it in the
log pattern. Now `grep correlationId=abc-123` across aggregated logs gives you the whole story.

Practical notes: return it in a response header so users can quote it in a bug report; include it in
DLQ'd messages (topic 14 §5); MDC uses `ThreadLocal`, so it does **not** propagate across
`@Async`/executor boundaries or reactive chains without a decorator — a common and frustrating gap.
See topic 20 §2 for the observability side.

### 12.4 The 1% bug

Intermittent bugs are the hard ones because the naive loop (reproduce → fix → verify) breaks down:
you can't reliably reproduce, and you can't tell whether your fix worked or you got lucky.

**Approach:**

1. **Find the pattern.** "Random" almost never is. Correlate by: time (hourly batch job, TTL expiry
   period, DST), instance (one bad pod/node/AZ), input (a specific tenant, a large payload, a
   particular character encoding), load (only at peak), sequence (only the first request after idle —
   a stale pooled connection, topic 10 §9), or cardinality (only when a cache is cold).
2. **Suspect the usual causes of intermittency**, and check them explicitly:
   - **Race conditions / missing synchronisation** — shared mutable state, check-then-act.
   - **Connection-pool state** — stale connections, idle-timeout mismatch, pool exhaustion under load.
   - **Timeouts and retries** — a p99 that occasionally exceeds a limit.
   - **Caching** — you hit a stale entry, or one instance out of ten has a different value (topic 15 §7).
   - **Load balancing** — one instance is misconfigured, so 1/N of requests fail. **The failure rate
     matching 1/(instance count) is a very strong signal.**
   - **Clock skew, DST, timezone** — especially around date boundaries.
   - **Resource exhaustion at the edge** — fd limits, ephemeral ports (topic 10 §8), thread pool full.
   - **Ordering assumptions** — messages arriving out of order (topic 14 §6).
3. **Add observability rather than guesses.** If you can't reproduce it, instrument it: log the inputs
   and the intermediate state on the failure path, add a metric with useful (low-cardinality!)
   dimensions, capture a thread dump on the condition. Ship the instrumentation, wait for the next
   occurrence, and now you have data instead of theories.
4. **Increase the failure rate deliberately.** Run the suspect code path in a tight loop, with more
   threads, with artificial latency injected, with a smaller pool, on a constrained container. A 1%
   bug at 100 rps becomes reproducible at 10,000 rps.
5. **Verify statistically.** After a fix, "I ran it once and it worked" proves nothing about a 1% bug.
   You need enough runs, or enough production time, for the absence to be meaningful — and a metric
   that would have shown the old failure rate.

---

## 13. `.gitignore` and secrets in history

```gitignore
target/
build/
*.class
.env
.env.local
*.pem
*.key
.idea/
.DS_Store
application-local.yml
```

Commit the `.gitignore`. Also commit an `.env.example` with the *names* of required variables and no
values, so the next person knows what's needed.

`git check-ignore -v <file>` tells you which rule is ignoring a file — useful when a file mysteriously
won't stage. And note: **`.gitignore` only affects untracked files.** Once a file is tracked, adding it
to `.gitignore` changes nothing; you need `git rm --cached <file>`.

### Secrets committed by accident

> **Trap:** Deleting a secret in a new commit does **nothing**. The value is still in the history,
> still in every clone, still on the remote, still in every fork, still in CI caches, and still
> retrievable via the GitHub API long after a force-push. Anyone who has ever cloned the repo has it.

**The response, in this order:**

1. **Rotate the credential immediately.** This is the actual remediation and it comes first. Assume it
   is compromised the moment it was pushed — public repos are scanned by bots within *seconds*.
2. **Check for use.** Audit logs for the credential: was it used from an unexpected IP or at an
   unexpected time?
3. **Then** clean the history, if worthwhile:
   ```bash
   # git-filter-repo is the current recommended tool (filter-branch is deprecated and slow)
   git filter-repo --path config/secrets.yml --invert-paths
   # or, for a value rather than a file:
   git filter-repo --replace-text expressions.txt
   ```
   BFG Repo-Cleaner is the older, still-serviceable alternative.
4. This **rewrites every commit hash**, so everyone must re-clone. Coordinate it. On GitHub, also ask
   support to purge cached views and delete affected forks — a rewrite alone does not remove dangling
   objects from the remote.
5. **Prevent recurrence:** pre-commit secret scanning (`gitleaks`, `detect-secrets`, `talisman`),
   server-side push protection (GitHub Secret Scanning), and a real secret store (topic 18 §6) so
   there's no reason for a secret to be in a file at all.

The order matters and is frequently got backwards in interviews: **rotate first, clean second.**
History cleaning is hygiene; rotation is the fix.

---

## Atomic concept checklist

- [ ] Git stores snapshots; commit hashes cover the parent, so rewriting one commit rewrites all descendants.
- [ ] Four areas: working directory → index → local repo → remote.
- [ ] A branch is a movable pointer to a commit; `HEAD` points to the current branch.
- [ ] `git add -p` stages hunk by hunk and makes you review your own diff.
- [ ] `git diff` = unstaged, `git diff --staged` = what you're about to commit, `git diff main...HEAD` = your branch's contribution.
- [ ] **`fetch` is always safe**; `pull` = fetch + integrate and can conflict. Prefer `pull --rebase`.
- [ ] `main` must be deployable at every commit — that invariant justifies branching, CI, and flags.
- [ ] Short-lived branches and feature flags beat long-lived branches; flags decouple deploy from release.
- [ ] Squash-merge is the pragmatic default: one revertable, bisectable unit per PR.
- [ ] Merge preserves true history; rebase produces linear history with **new hashes**.
- [ ] **Golden rule: never rebase commits others have based work on.**
- [ ] Standard flow: rebase your feature onto `main`, then merge/squash the feature in.
- [ ] `--force-with-lease` rejects the push if the remote moved; plain `--force` silently destroys colleagues' commits.
- [ ] A blind `git fetch` before `--force-with-lease` defeats it; consider `--force-if-includes`.
- [ ] **"ours"/"theirs" swap meaning during a rebase** — verify by content, not by label.
- [ ] Conflict procedure: status → understand both intents → edit → `add` → **run tests** → continue; `--abort` is always available.
- [ ] `rerere` replays recorded conflict resolutions during long rebases.
- [ ] **`revert` for pushed commits** (new commit, safe); `reset` only for local history.
- [ ] `reset --soft` keeps index + working dir; `--mixed` keeps working dir; `--hard` destroys both.
- [ ] `git reset --hard` and `git clean -fd` destroy uncommitted work **irrecoverably** — dry-run or stash first.
- [ ] `git restore` / `git switch` replace the overloaded `git checkout`.
- [ ] Reverting a merge needs `-m 1`, and blocks a later re-merge until you revert the revert.
- [ ] **Reflog records every HEAD movement** and recovers bad resets, botched rebases, deleted branches, bad amends.
- [ ] Reflog cannot recover what was never committed — so commit early and often, and squash later.
- [ ] `git fsck --lost-found` finds dangling commits the reflog missed.
- [ ] `git bisect` binary-searches history: ~log2(N) tests instead of reading N commits.
- [ ] `git bisect run <script>` automates it; exit **0 = good, 1 = bad, 125 = skip**.
- [ ] Bisect needs a deterministic repro and buildable commits — another reason to keep `main` green.
- [ ] `git stash -u` includes untracked files; prefer a named WIP commit over long-lived stashes.
- [ ] `cherry-pick -x` for backports; repeated cherry-picking as a merge substitute creates duplicates and conflicts.
- [ ] `rebase -i`: pick/squash/reword/edit/drop/reorder — unshared commits only; `--autosquash` with `--fixup`.
- [ ] Commit subject: imperative, ≤50 chars, blank line, body at 72 explaining **why**.
- [ ] The test for a commit message: does it help someone doing `git blame` during an incident in 18 months?
- [ ] **Review priority: correctness → security → tests → design → performance → operability → style last.**
- [ ] Automate style entirely; style nits crowd out the review attention that finds real defects.
- [ ] Defect detection collapses beyond **200–400 changed lines** and after ~60 minutes of reviewing.
- [ ] A 1,000-line PR gets approved, not reviewed — split refactor from behaviour change.
- [ ] Label every comment: `blocking:` / `suggestion:` / `nit:` / `question:` / `praise:`.
- [ ] Question-form feedback: you might be wrong, it transfers reasoning, and it depersonalises.
- [ ] After two round trips, take it to a call and write the conclusion back into the PR.
- [ ] Debug loop: observe precisely → reproduce → **falsifiable hypothesis** → predict → test one variable → fix the cause → regression test.
- [ ] Binary-search the problem space: code path, timeline, input, environment.
- [ ] **Ask "what changed?" first** — deploy, config/flag, traffic, data, infrastructure, or the date.
- [ ] Correlation IDs generated at the edge and propagated everywhere are what make distributed debugging possible.
- [ ] MDC is `ThreadLocal`: clear it in a `finally`, and it won't cross async boundaries without a decorator.
- [ ] "Random" 1% bugs almost always have a pattern: time, instance, input, load, sequence, or cold cache.
- [ ] A failure rate matching **1/(instance count)** points at one bad instance.
- [ ] Usual intermittency causes: races, stale pooled connections, timeout/retry edges, cache divergence, clock skew, resource exhaustion, out-of-order messages.
- [ ] If you can't reproduce it, **instrument it and wait** rather than guessing.
- [ ] Amplify the failure rate (load, concurrency, injected latency) to make a 1% bug reproducible.
- [ ] Verify a rare-bug fix statistically, with a metric — one successful run proves nothing.
- [ ] `.gitignore` only affects untracked files; use `git rm --cached` for already-tracked ones.
- [ ] Deleting a secret in a later commit does not remove it from history, clones, forks, or CI caches.
- [ ] **Rotate the credential first**, audit for use, *then* rewrite history with `git filter-repo`.
- [ ] History rewriting changes every hash and forces everyone to re-clone — coordinate it.
- [ ] Prevent recurrence with pre-commit secret scanning, push protection, and a real secret store.