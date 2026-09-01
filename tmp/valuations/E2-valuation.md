# Valuation — Easy Paper 2

**Answers:** `tmp/papers/answers/E2-paper.txt` · **Key:** `tmp/papers/easy/paper-2-key.md`
**Score: 12.5 / 19** — Q2 (code) deferred per the deferred-code policy, removed
from the denominator. Band 12–16 equivalent, and DOWN from E1's 14.5.
Scoring: 1 = matches key's key points · 0.5 = right idea, gap/imprecision · 0 = wrong or blank · — = `[CODE]` deferred to the end-of-tier code session.

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | Loop complexity | **1** | Both parts right, triangular reasoning correct. |
| 2 | `[CODE]` palindrome | **—** | Deferred: per your policy, all `[CODE]` questions will be answered together at the end of the tier and evaluated then. Not scored, not counted in the denominator. |
| 3 | Checked vs unchecked | **0.5** | Examples both correct. The mechanism is off though: both kinds "exist at compile time" — the difference is **enforcement**: checked = compiler forces catch-or-declare (`throws`); unchecked = `RuntimeException` subtypes, no enforcement. "Compiler isn't aware" of unchecked is the wrong model. |
| 4 | Interface vs abstract | **0.5** | State/constructor difference right. But **interfaces have default methods too (Java 8+)** — you attributed them to abstract classes as a differentiator. Must-use case ("partial implementations") too vague to score full: the forcing case is **shared mutable state or constructor logic**. |
| 5 | Thread pools | **0** | "Not aware" — honest, recorded. (Reuse-over-creation-cost + bounding concurrency were the marks.) |
| 6 | `synchronized` | **0.5** | Mutual exclusion described (wording confuses thread/object, but the lock model is there). Missing the second guarantee entirely: **visibility** — writes before release are visible to the next acquirer. |
| 7 | Spring Boot / starters | **1** | Auto-configuration + embedded Tomcat + on-the-go annotations — accepted. |
| 8 | JPA entity / @Id / @GeneratedValue | **1** | All three correct. |
| 9 | `[CODE]` SQL select | **0.5** | Logic perfect — filters, `ORDER BY salary DESC`. But the question asked for **names and salaries**; you wrote `SELECT *`. Same miss-the-asked-instance pattern as E1 Q9/Q10. |
| 10 | `[CODE]` GROUP BY/HAVING | **0.5** | Concept right despite the self-doubt — GROUP BY + HAVING chosen correctly. Two defects: **`dept` missing from the SELECT** (question: "each dept with its count"), and `HAVING cnt > 10` — **column aliases aren't visible in HAVING** in Postgres/standard SQL (MySQL tolerates it); write `HAVING COUNT(*) > 10`. |
| 11 | Status classes | **1** | Correct throughout. |
| 12 | IP vs port | **1** | Clean answer with 80/22 examples — better than the key demanded. |
| 13 | GET vs POST | **1** | Caching, body, idempotency — three differences given. |
| 14 | Password storage | **0** | **The most important miss in the paper.** Diagnosing plain text as bad is fine, but the fix you proposed — public/private-key encryption, Diffie-Hellman — is still **reversible encryption**: whoever holds the private key can decrypt every password, which is exactly the flaw the question flagged (and Diffie-Hellman is a key-*exchange* protocol, unrelated to storage). The answer: **salted, deliberately-slow one-way hashing** (bcrypt / argon2) — you never store anything recoverable; you verify by re-hashing the attempt. This is an interview red-flag topic: a wrong answer here reads worse than "I don't know." |
| 15 | TTL | **1** | Full answer including the small-TTL-vs-stale trade-off — above the bar. |
| 16 | Async transcoding | **1** | Async + "accepted for processing" response — correct (`202 Accepted` + status URL is the crisp version). |
| 17 | commit/push, fetch/pull | **1** | All four right — and yes, `git pull --rebase` is real; your hedge was correct. |
| 18 | Merge conflict | **0.5** | When-raised: right. Resolution incomplete: choosing ours/theirs/both is the *decision*; the *steps* are edit the file, remove the `<<<<<<<` markers, `git add`, then complete the merge/rebase (`commit` / `--continue`). |
| 19 | Env vars | **0.5** | One reason given (change without rebuild). Needed two — the missing big ones: **secrets stay out of source control**, and **one artifact runs in every environment**. |
| 20 | Load balancer | **0** | The question asked for two things **beyond** spreading traffic; the answer restated spreading. Marks were: health checks (stop routing to dead instances), zero-downtime deploys via draining, TLS termination, horizontal-scaling enablement. |

## Section rollup (with E1 comparison)

| Section | E2 | E1 | Read |
|---|---|---|---|
| DSA | 1/1 | 1.5/2 | Theory fine; code item deferred to end-of-tier session |
| Java Core | 1/2 | 1.5/2 | Mechanism-level imprecision both papers |
| **Concurrency & JVM** | **0.5/2** | **0.5/2** | **No improvement after E1 flagged it → escalation triggered** |
| Spring & JPA | 2/2 | 1.5/2 | Consistently the strongest theory area |
| SQL & DB | 1/2 | 1/2 | Concepts present; write-precision defects (projection, alias-in-HAVING) |
| Networking & OS | 2/2 | 1.5/2 | Solid |
| API & Security | 1/2 | 2/2 | Dragged down by the **password-storage misconception** |
| Messaging & Caching | 2/2 | 2/2 | Consistently strong |
| Testing & Craft | 1.5/2 | 1.5/2 | Git fine; process steps half-known |
| Cloud & DevOps | 0.5/2 | 1.5/2 | Weaker than E1 suggested — env-var/LB depth missing, self-flagged |

## Findings → `qbank/13-scoring-and-report.md`

1. **ESCALATED TO CRITICAL: Concurrency.** E1's decision rule said: if Section 3 lands ≤1 on E2, escalate. It landed 0.5 — identical to E1, with a flat "not aware" on thread pools. Escalation executed: gaps.md updated, and a dedicated primer now exists at `tmp/primers/concurrency-primer.md`. **Do not take E3 until you've worked through it** — E3 Q5/Q6 (heap-vs-stack, deadlock) are the verification questions.
2. **NEW GAP (high): security-fundamentals misconception, not just a gap.** Password storage answered with confident wrong mechanism (reversible asymmetric encryption). Added to gaps.md; a retest question has been added to E4 (see below).
3. **CONFIRMED PATTERN (3rd occurrence): answers miss the asked instance.** `SELECT *` for "names and salaries"; `dept` absent from the GROUP BY select; "beyond spreading traffic" answered with spreading. This is now a standing drill: after answering, re-read the question and tick off every clause.
4. ~~Write-it avoidance~~ — **WITHDRAWN.** The blank was policy, not avoidance: all `[CODE]` questions are deferred to one end-of-tier session by the candidate's choice. Deferred so far: E2 Q2 (palindrome). Any further blank `[CODE]` items get marked "—", tracked in the deferred list, and evaluated together at the end.
5. **Cloud/DevOps softer than E1 indicated** (0.5 vs 1.5) — E1 sampled its strong spots (EC2/S3/RDS one-liners), E2 sampled operational depth (12-factor config, LB features). Real level is likely L1. Watch E3 Q19/Q20.

## Actions taken with this valuation

- `tmp/gaps.md` — appended a diagnostic-evidence section: concurrency → CRITICAL, password-storage misconception added, asked-instance pattern and cloud-depth downgrades recorded.
- `tmp/primers/concurrency-primer.md` — created; ~1 evening of focused reading targeted at exactly the E1+E2 concurrency misses. E3/E4/E5's concurrency questions remain unmodified and act as the verification.
- `tmp/papers/easy/paper-4.md` — **modified**: added Q14b (password-storage retest from a different angle) + key entry; E4 is now scored /21.
- E3/E5 left unmodified — their existing questions already retest today's other misses (E3: heap/stack, deadlock, PK/FK, index basics; E5: volatile, thread states, LB-adjacent scaling).

## Sequencing instruction

Study order before E3: (1) concurrency primer (~2–3h), (2) the five-line misconception log in E1's valuation, (3) password-hashing correction above (15 min — read the OWASP Password Storage Cheat Sheet summary once). Then E3 closed-book. Expected if study lands: Section 3 ≥ 1.5, overall ≥ 15.