# Ad-hoc Paper 3 — API Contracts, Git Craft, Testing & AWS Breadth

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `ad-hoc-paper-3-key.md`. Suggested time: 80 min.
18 questions, 1 mark each.

**Why this paper exists:** the earlier papers measured API *basics* (verbs,
status codes — consistently strong) but never the design specifics that make up
an LLD round; git *commands* but never recovery, archaeology or debugging
methodology; testing *definitions* but never the tooling; and AWS *service
names* but never the mechanics behind them. Difficulty sits at the easy→medium
boundary.

Where a question asks you to **design** something, a bulleted contract is fine —
prose paragraphs are not what an interviewer wants either.

## Section 1 — API contracts and evolution

**Q1.** A payments endpoint charges a card. The client's network times out and
it retries; the customer is charged twice. Design the fix end to end: what the
client sends, what the server stores and when, what happens on a replay, what
happens when the same key arrives while the first request is still in flight,
and what happens when the same key arrives with a *different* body.

**Q2.** Your `/api/orders` response must change: `customerName` splits into
`firstName` and `lastName`, and you must not break existing clients.
(a) Which changes to a response are safe to make without any versioning at all,
and which are not? (b) Compare URI versioning, header versioning and query
versioning in one line each. (c) You decide to retire `/v1` — give the sequence
of steps from decision to deletion.

**Q3.** Error responses. (a) What is wrong with returning
`200 OK {"success": false, "error": "not found"}`? (b) Name the standard for
HTTP error bodies, its content type, and the fields that make an error
machine-readable and debuggable. (c) Two things must never appear in an error
body — name them. (d) A request fails validation on three fields; what do you
return?

**Q4.** Pick the right status code and say why, in one line each:
(a) a POST created a resource; (b) an update was rejected because someone else
modified the row first; (c) the caller is authenticated but not allowed;
(d) the caller exceeded their rate limit; (e) the work was accepted and will
finish later.

**Q5.** Design the read side of "list a customer's orders" for a table with
50 million rows and clients that page through all of it.
(a) Why does `LIMIT 20 OFFSET 200000` get slower as the client pages, and what
second problem appears if rows are being inserted while they page?
(b) Give the cursor-based alternative — the query, what the cursor contains, and
why a tiebreaker column is mandatory. (c) Name one thing offset gives you that
cursor does not, and one server-side guard the endpoint must enforce regardless.

**Q6.** You must notify a partner system when an order ships.
(a) Choose between polling, SSE, WebSocket and a webhook, and justify from the
direction and the trust boundary. (b) Name four things a production webhook
sender must do. (c) Name two things the receiver must do.

## Section 2 — Git craft and debugging

**Q7.** You ran `git reset --hard HEAD~3` on your local branch and the three
commits contained a day's work. (a) Are they recoverable, and by what mechanism?
(b) Give the exact commands. (c) Name the one situation in which this recovery
is impossible.

**Q8.** `revert` vs `reset` vs `restore`/`checkout`: what does each do, and
which one do you use for a bad commit that is **already pushed to main**?
Then: you revert a merge commit and later want to merge that branch again —
what goes wrong?

**Q9.** A bug exists on `main` today; release `v2.4` from 300 commits ago was
clean. (a) Name the tool and explain why it takes ~8 tests rather than 300.
(b) Give the command sequence, including the automated form. (c) State the two
preconditions that make it work, and what the exit code 125 means.

**Q10.** A colleague force-pushed and erased two of your commits from the shared
branch. (a) What should they have used instead, and what exactly does it check?
(b) State the golden rule about rebasing. (c) During a rebase, the conflict
markers say "ours" and "theirs" — why is this a trap?

**Q11.** An API key was committed three weeks ago and merged to main. It has
since been deleted in a later commit. (a) Is the repository safe? Explain.
(b) Give the correct remediation sequence, in order — the first step is not a
git command. (c) Name two controls that prevent a recurrence.

**Q12.** A bug reproduces for roughly 1% of requests and never on your machine.
(a) State the debugging loop you would follow as a sequence of steps.
(b) "What changed?" — list the five categories worth checking.
(c) Name three concrete patterns that a "random" 1% failure usually turns out
to have, and one technique for making it reproduce more often.

## Section 3 — Testing in practice

**Q13.** You are testing a repository that runs real SQL. (a) What is the case
against H2 in-memory — name three concrete ways it gives false confidence.
(b) What do you use instead, and what is the one configuration detail that
keeps the suite fast enough to be the default?

**Q14.** Spring Boot test slices. (a) Name four slice annotations and say what
each one loads and does not load. (b) Spring caches application contexts
between tests — what is the cache key, and name two common things that destroy
the caching and make the suite crawl.

**Q15.** `[CODE — 20 min]` A service method:
```java
public Receipt charge(String customerId, BigDecimal amount) {
    if (amount.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
    Customer c = customers.findById(customerId).orElseThrow(() -> new CustomerNotFound(customerId));
    String ref = gateway.charge(c.token(), amount);
    return receipts.save(new Receipt(ref, customerId, amount, clock.instant()));
}
```
Write JUnit 5 + Mockito tests covering: the happy path (assert the saved
`Receipt`, including its timestamp, deterministically), the invalid-amount case,
and the customer-not-found case. Use an `ArgumentCaptor` at least once.

**Q16.** Coverage and flakiness. (a) Your team hits 85% line coverage — state
precisely what that does and does not tell you, and name the technique that
measures the difference. (b) Name four distinct causes of flaky tests with the
specific fix for each. (c) Why is "retry the test up to 3 times" the wrong fix?

## Section 4 — AWS mechanics

**Q17.** IAM. (a) Your application on ECS needs to read from S3. Explain the
mechanism by which a role gets credentials to the SDK — where do they come from,
how long do they last, and what is on disk? (b) Why is that better than an
access key in an environment variable? (c) A policy grants `s3:GetObject` and
another explicitly denies it — what happens, and what is the general evaluation
order?

**Q18.** Two service A → service B connectivity failures.
(a) A connects to B and the TCP connection establishes, then hangs forever with
no response. The security groups look correct. What is the likely cause and
which layer is it at? (b) A gets "connection timed out" immediately with no
response at all. Name the two most likely causes and the tool that tells you
which.
Then: your RDS instance failed over at 02:00, the DB came back in 40 seconds,
but the JVM kept trying the old IP for an hour. Explain the mechanism and the
fix.