# Valuation — Easy Paper 3

**Answers:** `tmp/papers/answers/E3-paper.txt` · **Key:** `tmp/papers/easy/paper-3-key.md`
**Score: 14.5 / 20** → band 12–16. Trajectory: E1 14.5 → E2 12.5 → **E3 14.5**.
**Headline: the concurrency primer worked** — Section 3 went 0.5 → 1.5 (the target set in E2's valuation).

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | HashMap vs TreeMap | **1** | Ordering + complexities all correct. |
| 2 | Binary search | **1** | Precondition, why it breaks, log₂(10⁶) ≈ 20 — clean. |
| 3 | `final` | **1** | All three uses, correct prevention each, AND the reference-vs-contents nuance on the final List — exactly the trap the question set. Bonus observation (abstract can't be final) also correct. |
| 4 | Primitives vs wrappers | **1** | Two differences + collections-only-wrappers. (Third difference worth knowing: wrappers can be `null` — that's how DB nullable columns map.) |
| 5 | Heap vs stack | **1** | **Direct retest of your E1 zero — now correct.** Objects on heap; references + primitive locals on stack; both errors right. One naming nit: it's `OutOfMemoryError` (an Error, not Exception) — say "Error" in interviews. |
| 6 | Deadlock | **0.5** | Definition correct. But the two-thread/two-lock setup is literally an unfilled template — the answer file contains `***ADD ANSWER HERE***`. Scored what's present. The setup (from the primer §6): T1 locks A wants B, T2 locks B wants A, circular wait; fix = global lock order. If you knew it and forgot to paste, prove it in E4/E5's retests; if not, reread primer §6. Either way: **scan the answer file for placeholders before submitting.** |
| 7 | `@Transactional` | **0.5** | Both endings captured (all-commit / all-rollback). But the question's first clause — **what starts** (a database transaction is opened/joined before the method body) — went unanswered. 4th occurrence of the asked-instance pattern. |
| 8 | `Optional` | **0** | "Not sure" — recorded. The point: it makes might-not-exist explicit in the type so the compiler forces callers to handle absence (`orElseThrow`, `map`) instead of NPE-ing far from the cause. Retested at depth in medium paper 4. |
| 9 | PK / FK / unique | **1** | All three enforced-properties right. (PK is also implicitly NOT NULL — the one thing unique constraints don't give you.) |
| 10 | Index | **0.5** | Self-flagged, and it shows: "faster search + costs space" is half. Missing: what it speeds (lookups, **range queries, sorts, joins**) and the bigger cost — **every INSERT/UPDATE/DELETE must maintain the index** (write slowdown), not just storage. Indexing is a stated interview tiebreaker at your YOE — this goes on the study list. |
| 11 | HTTPS | **0.5** | Encryption point assumed (you wrote "HTTP encrypts" — typo taken charitably). The two attacker abilities stayed vague ("MiM I guess"): concretely, on plain HTTP an on-path attacker can **read everything** (credentials, cookies) and **modify traffic** (inject/redirect). HTTPS also gives integrity + server authentication, not just secrecy. |
| 12 | Linux triage | **0** | "Not sure." The answers: `top` (or `htop`) for live per-process CPU/memory; `kill <PID>` = polite SIGTERM, `kill -9 <PID>` = forceful SIGKILL. Cheapest possible interview points; 10 minutes of practice on any terminal. |
| 13 | AuthN vs AuthZ | **1** | Clean, with correct 401/403. |
| 14 | Idempotency | **0.5** | Definition and retry rationale good. Methods: you named GET and DELETE — **missed PUT**, which is the canonical idempotent-write example (same full replacement N times = same state). That omission usually costs the follow-up question. |
| 15 | Producer/consumer/broker | **0.5** | Terms fine. Consumers-down answer wrong: no "retry to consumers" happens — **messages accumulate durably in the broker** (queue/retention) and are processed when consumers return. That buffering IS the point of a broker (you had this right in E1 Q15 and E5-style questions — keep it consistent). |
| 16 | Hit ratio | **0.5** | Definitions fine, verdict right. Checks too thin: besides cache size/evictions — **TTL too short, key design mismatched to access pattern, caching rarely-re-read data**. One check named = half. |
| 17 | Test reading | **1** | Behavior identified, given-when-then named. |
| 18 | Branches/PRs | **1** | Review-gate + keeping main releasable — both accepted. |
| 19 | Region/AZ | **1** | Correct, including the HA rationale. |
| 20 | Rollback | **1** | Versioned artifacts/tags + rollback step in the pipeline — accepted. |

## Section rollup (trend across papers)

| Section | E3 | E2 | E1 | Read |
|---|---|---|---|---|
| DSA | 2/2 | 1/1 | 1.5/2 | Solid; E3 had no code items — `[CODE]` questions are deferred to the end-of-tier session |
| Java Core | 2/2 | 1/2 | 1.5/2 | Best showing yet — `final` nuance was full-mark work |
| **Concurrency & JVM** | **1.5/2** | 0.5/2 | 0.5/2 | **Primer verified working; deadlock setup still owed** |
| Spring & JPA | 0.5/2 | 2/2 | 1.5/2 | Dip is Optional (Java-API gap, not Spring) + asked-instance miss |
| SQL & DB | 1.5/2 | 1/2 | 1/2 | Constraints fine; **indexing depth is the gap** |
| Networking & OS | 0.5/2 | 2/2 | 1.5/2 | Dip = HTTPS vagueness + Linux tooling zero |
| API & Security | 1.5/2 | 1/2 | 2/2 | Good; PUT omission only |
| Messaging & Caching | 1/2 | 2/2 | 2/2 | Broker durability answered wrong — regression to note |
| Testing & Craft | 2/2 | 1.5/2 | 1.5/2 | Consistently fine |
| Cloud & DevOps | 2/2 | 0.5/2 | 1.5/2 | Conceptual AWS fine; the E2 dip was ops-practice depth (Q12 today confirms: tooling, not concepts) |

## Findings → `qbank/13-scoring-and-report.md`

1. **Concurrency: CRITICAL → HIGH (recovering).** Verification target met (Section 3 ≥ 1.5); heap/stack — the E1 zero — retested clean. Outstanding: the deadlock two-lock setup (unfilled placeholder) and the E4/E5 items (start-vs-run, volatile, thread states). Full downgrade to "closed" only after those score ≥1.5 combined.
2. **NEW (medium): practical Linux tooling is a blank, distinct from cloud concepts.** Q12 zero + E2's ops dip: concepts (regions, rollbacks) fine, hands-on tooling (top/kill, and presumably grep/tail under pressure) missing. Cheap fix: 30 minutes at a terminal beats any reading. Retest: medium paper 4 Q12 (box triage) already covers this at depth — no paper change.
3. **NEW (small, cheap): `Optional` purpose unknown** — medium paper 4 already retests; no paper change needed.
4. **Asked-instance pattern, 4th occurrence** (Q7 "what starts"). Also new process miss: **submitted an answer file containing an unfilled `ADD ANSWER HERE` placeholder** (Q6) — add "scan for placeholders" to the pre-submit ritual alongside "re-read each question's clauses."
5. **Indexing depth (medium):** self-flagged + 0.5. The write-cost half (index maintenance on every write) is the part interviews probe. E4 Q10-equivalent doesn't exist at easy tier; medium papers 1/2 hit composite indexes and planner behavior — the gap will be measured there; study before medium tier.
6. **Watch reversal:** messaging (previously 2/2 twice) dropped on broker durability — likely a slip, not a gap; no action unless it repeats.

## Actions taken with this valuation

- `tmp/gaps.md` §9 — appended E3 evidence: concurrency downgraded to HIGH-recovering, Linux-tooling gap added, indexing-depth noted, asked-instance count now 4.
- **No paper modifications.** A proposed E5 Linux-triage retest was withdrawn; medium paper 4 Q12 (box triage) already retests it at depth. E4 stands as previously modified (password retest Q14b) and carries the concurrency verification (Q5 start-vs-run, Q6 GC).
- **Deferred-code policy (candidate's choice):** all `[CODE]` questions across papers are answered in one session at the end of the tier and evaluated then — blanks on them are marked "—", not 0. Deferred list so far: E2 Q2 (palindrome); upcoming: E4 Q2 (char frequencies), E5 Q10 (SQL query) if left blank. E2's score restated as 12.5/19; its "write-it avoidance" finding withdrawn.

## Sequencing instruction

Before E4 (~1 hour total): (1) primer §6 — write the deadlock setup from memory once; (2) 30 min terminal practice — `top`, `htop`, `kill`/`kill -9`, `ps aux --sort=-%cpu`, `tail -f` + `grep` on any log file; (3) 15 min on B-tree index costs (what it speeds, what every write pays). Then E4 closed-book — it contains the password-storage retest (Q14b), so also re-check that OWASP summary if it's not cold-recallable yet.