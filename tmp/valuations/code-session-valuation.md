# Valuation — Deferred Code Session (easy tier)

**Answers:** `tmp/papers/answers/easy-code-answers.txt`
**Score: 1 / 3** (E2 Q2: 0.5 · E4 Q2: 0.5 · E5 Q10: 0). M5 Q1 (longest
substring) not attempted — still open; fold it into the redo session below.
**Verdict: write-fluency is now MEASURED, and it is a real gap — the widest
theory-vs-practice split the whole tier produced.**

## Per-question

### E2 Q2 — isPalindrome · **0.5**

What was submitted is a correct **algorithm in English**, not code:
lowercase → filter alphanumeric → reverse → compare is a valid approach
that would score full marks *if implemented*. But `[CODE]` questions ask
for code an interviewer could run; pseudocode is what candidates write when
they can see the solution but haven't built the muscle to type it. The
~8-line implementation:

```java
boolean isPalindrome(String s) {
    StringBuilder sb = new StringBuilder();
    for (char c : s.toCharArray())
        if (Character.isLetterOrDigit(c)) sb.append(Character.toLowerCase(c));
    return sb.toString().contentEquals(sb.reverse());
}
```
(Two-pointer version avoids the extra string — worth doing once too.)

### E4 Q2 — charFrequencies · **0.5**

Real code this time, and the core idiom (HashMap + containsKey/put) is
right. Two defects:

1. **It doesn't compile** — the method declares `Map<Character, Integer>`
   but never `return cf;`. An editor was allowed; compiling before
   submitting would have caught it in seconds. Rule from here: code
   answers must have been compiled/run, not just typed.
2. **The asked complexity statement is missing** (the question explicitly
   required time AND space): O(n) time, O(k) space for k distinct chars.
   Same asked-instance pattern, now in code form.

Polish note: `cf.merge(c, 1, Integer::sum)` — one line, no branch. Also
noted and appreciated: your `// checked for function name` comments were
honest about looking up method names. For diagnostic value, mark lookups
that way every time — but budget them out before medium tier; interviews
allow zero.

### E5 Q10 — SQL aggregation · **0**

```sql
select * from table where created_at>'2025-01-01' and amount>10000 order by amount desc;
```

This is the session's most important result. The query doesn't aggregate
at all — and the question is an aggregation problem in disguise: "TOTAL
per customer … exceeding 10,000" means SUM + GROUP BY + HAVING:

```sql
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'
GROUP BY customer_id
HAVING SUM(amount) > 10000
ORDER BY total DESC;
```

Specific defects: filtered individual order `amount > 10000` (a
row-level condition) where the requirement was a customer-level total (a
group condition — the WHERE-vs-HAVING distinction you explained correctly
in E2 Q9!); no GROUP BY/SUM; `FROM table` instead of `orders`; date filter
has no upper bound (includes 2026+); ordered by row amount, not total.

The diagnosis that matters: **in E2 Q10 you produced GROUP BY/HAVING when
the question named the operations ("count per dept having more than 10");
here, where the aggregation was implied by the words "total per customer,"
you didn't recognize the problem shape.** Prompted recall exists;
unprompted recognition doesn't yet. That's precisely what SQL word-problem
drills fix — and what interview SQL screens test.

## Findings → `qbank/13-scoring-and-report.md` + gaps.md

1. **CONFIRMED GAP (HIGH): code write-fluency.** Theory across the tier
   was ~71%; the code session produced 0 fully-correct artifacts out of 3.
   Failure modes: describing instead of implementing, submitting
   uncompiled code, and not recognizing an aggregation problem unprompted.
   This measured result upgrades gaps.md §1.1's DSA-volume argument and
   §2.2's SQL-drill recommendation from "anticipated" to "evidence-backed."
2. **The fix is reps, not reading.** Daily 20–30 min in a REAL editor,
   compile-and-run mandatory, starting with a redo gate (below). LeetCode
   easies + pgexercises word problems are exactly the right instruments.
3. **Asked-instance pattern reaches into code** (missing complexity
   statement) — the pre-submit clause-check applies to code answers too.

## Gate before medium tier (redo session)

Redo, in an editor, compile/run each, no references:
1. isPalindrome — as actual Java, both variants (clean-and-reverse, then
   two-pointer).
2. charFrequencies — compiling, with `merge`, complexity stated.
3. The E5 SQL — against a scratch table (or paper, but with exact
   syntax), plus TWO fresh word-problem variants: "customers whose 2025
   order COUNT exceeds 5" and "each customer's LARGEST single order in
   2025."
4. M5 Q1 (longest substring) — attempt with the 25-min timebox; it's the
   one real algorithm problem still unmeasured.

Submit as one file; when all four pass, medium tier opens (with the
between-tier syllabus from the E5 wrap-up done in parallel). Expected
timeline: 3–5 days alongside primer-2 study — no need to pause everything.