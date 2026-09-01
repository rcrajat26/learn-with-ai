# Valuation — Easy Paper 5 (the real one) + EASY-TIER WRAP-UP

**Answers:** `tmp/papers/answers/E5-paper.txt` · **Key:** `tmp/papers/easy/paper-5-key.md`
**Score: 14 / 20** (Q10 code deferred). Easy tier scored run: 14.5 → 12.5/19 → 14.5 → 14.5 → **14.0** ≈ **71% aggregate (70/99)**.

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | Arrays vs LL | **0.5** | (a) and (c) right. Two gaps: LL middle-insert is O(1) only **if you already hold the node** — finding it is O(n); and the why-arrays-win answer missed the real reason: **CPU cache locality** (contiguous memory prefetches; pointer-chasing defeats caches). |
| 2 | Recursion | **1** | Base case + recursive progress + StackOverflowError — clean. |
| 3 | List/Set/Map | **1** | Properties + sensible examples. |
| 4 | Generics | **1** | Despite the self-flag: compile-time type restriction + ClassCastException prevention is exactly the mark. Your understanding is better than your confidence here. |
| 5 | `volatile` | **0.5** | Visibility half right. But "counter++ is thread-safe → I guess yes" is **wrong and was covered in the concurrency primer (§3)**: volatile gives visibility, NOT atomicity; `counter++` is still a three-step read-modify-write race. Needs `AtomicInteger` or a lock. Flagged as a primer regression — see findings. |
| 6 | Thread states | **0.5** | Approximate names half-there (TERMINATED missing; IDLE isn't one). The asked distinction missing: **BLOCKED** = stuck entering a `synchronized` monitor another thread holds; **WAITING** = parked deliberately (`wait()`, `join()`) until signaled. "Resource not available" blurs the two. |
| 7 | @RestController | **1** | Controller+ResponseBody, JSON vs view, Jackson — full. |
| 8 | Migrations | **0.5** | "Control + trackable" is the thin half. The full mark needed: **versioned, ordered scripts with a recorded schema history**, repeatable across environments — and why `ddl-auto=update` is dangerous in prod: it *guesses* diffs, can't rename safely, no review, potentially destructive against real data. |
| 9 | DELETE/TRUNCATE/DROP | **1** | All three + selectivity correct. |
| 10 | `[CODE]` SQL | **—** | Deferred (list: E2 Q2, E4 Q2, M5 Q1, E5 Q10). |
| 10b | **ACID retest** | **0.5** | Partial pass. Crash-no-lost-money → Atomicity: **correct** (that's progress from E4's zero). But report-never-sees-intermediate-state → you said Consistency (it's **Isolation**), and survives-power-failure → you said Isolation (it's **Durability**); fourth property unnamed. The Consistency↔Isolation swap is the exact E4 confusion persisting. Gap stays OPEN. You asked for a chapter — it now exists: `tmp/primers/fundamentals-primer-2.md`, part 1. |
| 11 | URL → page | **0.5** | DNS walk with TLD/A-record: good. But the required sequence compressed away two steps: after DNS comes the **TCP 3-way handshake**, then the **TLS handshake** (cert verification, session keys), *then* HTTP. "Hit the server on 443" skips exactly the parts interviews probe. |
| 12 | Firewall / unreachable app | **0.5** | Firewall definition fine. The two likely causes weren't given — the outsider isn't typing "localhost"; they're hitting the VM's IP and failing because: (1) **security group/firewall doesn't allow inbound 8080**, (2) **app bound to 127.0.0.1 instead of 0.0.0.0** (also: no public IP). Asked-instance pattern again. |
| 13 | Bearer token | **1** | Header, post-auth issuance, HTTPS-or-stolen — accepted. (Nuance: "bearer" is broader than JWT — any token whose possession grants access.) |
| 14 | CORS | **0.5** | Definition roughly there and the curl intuition was right — but the enforcement answer inverted the model: the **BROWSER enforces CORS**; the server merely *declares* policy via `Access-Control-Allow-*` headers. That's why curl sails through: CORS protects browser users, not servers. Chapter requested → primer part 3. |
| 15 | Consumers down 1 hour | **0.5** | (b) right. (a) wrong — and this is the **third paper in a row** with the same broker misconception: with no consumers running there are no processing failures, so nothing goes to DLQ. Messages simply **accumulate durably in the queue** and get processed when consumers return — that buffering IS why queues exist. DLQ is only for messages that repeatedly FAIL processing. Primer part 2 is dedicated to this lifecycle. |
| 16 | Redis structures | **0.5** | "Distributed caching" — yes, but the asked instance (two data structures + uses) went blank: **hash** (session/object fields), **sorted set** (leaderboards, rate-limit windows), list (queues), set (unique membership), per-key TTL. |
| 17 | Commit message | **0.5** | Your example subject names the bug — good. Two corrections: good messages are **concise subject + explanatory body** (not "detailed verbose"), and the body should carry the *why*/cause (double application in both pricing and checkout paths, e.g.). |
| 18 | Code review | **1** | Three distinct items, sane priority order (correctness → optimization → style-last). |
| 19 | Scaling | **1** | Both defined, LB → horizontal, and the leader-election/coordination limitation is an above-bar observation (it's exactly the scheduled-job double-run problem). |
| 20 | Environments | **0.5** | Definitions and staging rationale OK; the asked bug class blank. Classic answers: works-on-H2-fails-on-Postgres (different DB), missing prod config/secret, pool exhaustion invisible at staging's tiny load. |

## EASY-TIER WRAP-UP (5 papers, 99 scored answers, ~71%)

| Section | E1 | E2 | E3 | E4 | E5 | Tier read |
|---|---|---|---|---|---|---|
| DSA | 1.5 | 1/1 | 2 | 1/1 | 1.5 | Solid theory; write-fluency UNMEASURED until code session |
| Java Core | 1.5 | 1 | 2 | 1.5 | 2 | Strong; confidence lags competence (Q4 today) |
| Concurrency | 0.5 | 0.5 | 1.5 | 2 | 1 | Repaired 0.5→2.0, **but volatile/atomicity regressed today** |
| Spring/JPA | 1.5 | 2 | 0.5 | 1.5 | 1.5 | Consistently decent; JPA depth untested until medium |
| SQL & DB | 1 | 1 | 1.5 | 0.5 | 1.5 | **Weakest theme: ACID still open, mechanics imprecise** |
| Networking/OS | 1.5 | 2 | 0.5 | 1.5 | 1 | Concepts OK; handshake steps + tooling thin |
| API/Security | 2 | 1 | 1.5 | 2.5/3 | 1.5 | Strong overall; password gap closed; CORS model inverted |
| Messaging/Caching | 2 | 2 | 1 | 1.5 | 1 | **Split verdict: caching = banked strength; broker lifecycle = 3-paper systematic miss** |
| Testing/Craft | 1.5 | 1.5 | 2 | 1 | 1.5 | Fine; process-mechanics halves |
| Cloud/DevOps | 1.5 | 0.5 | 2 | 1.5 | 1.5 | Concept-level OK ≈ L1–L2; ops practice thin |

## Findings → `qbank/13-scoring-and-report.md`

1. **ACID: retest PARTIAL — stays open (HIGH).** Atomicity now anchored (E4: 0/4 → E5: correct); Isolation↔Consistency swap persists; Durability unmapped. Primer written (part 1); next retest = M3 Q10 (isolation anomalies) after primer study.
2. **Concurrency closure gets an asterisk.** The volatile/`counter++` verdict was wrong despite primer §3 covering it verbatim. Easy-tier closure stands for the repaired items (memory model, pools, start/run), but volatile-atomicity joins the medium-tier verification list (M1 Q5 tests it directly).
3. **Broker message lifecycle: upgraded to HIGH — 3 consecutive papers, same wrong model.** The recurring belief: broker "retries then DLQs" regardless of consumers. Correct model: consumers-down → messages WAIT (durability); DLQ only after repeated *processing failures*. Primer part 2; retests: M1 Q15, M3 Q15.
4. **CORS enforcement side inverted** (server ≠ enforcer) — primer part 3; retest M2 Q14.
5. **Asked-instance pattern: 3 more today** (Q12 causes, Q16 structures, Q20 bug class) — ~10 occurrences tier-total. This is now the single cheapest score lever you have: it cost ~2 marks per paper.
6. **Confidence miscalibration (new, mild):** two self-flagged answers (generics, scaling) scored FULL marks while two confident ones (volatile safety, SQS→DLQ) were wrong. In interviews, hedge less on the former kind, verify more on the latter.

## Actions taken

- `tmp/primers/fundamentals-primer-2.md` created — part 1: ACID with the exact scenario mapping you missed; part 2: broker message lifecycle (your 3-paper miss); part 3: CORS in one page; part 4: volatile vs atomicity refresher.
- `tmp/gaps.md` §9 — easy-tier wrap-up evidence appended.
- **No paper modifications**: medium papers already retest every open item (M1 Q5 volatile, M1/M3 Q15 broker, M2 Q14 CORS, M3 Q10 isolation).

## Next steps (tier transition)

1. **Deferred code session** — one file (`tmp/papers/answers/code-session.txt`): E2 Q2 palindrome, E4 Q2 char frequencies, E5 Q10 SQL, M5 Q1 longest substring. Timebox each per its paper. This settles the unmeasured write-fluency question.
2. **Between-tier study** (~1 week alongside normal plan work): fundamentals-primer-2, then the M5-preview syllabus (JPA LazyInit/N+1, indexing/keyset, heap internals, git recovery, isolation anomalies).
3. Then **M1** closed-book. Entry expectation at medium tier after study: ~10–12/20, rising across M2–M4.