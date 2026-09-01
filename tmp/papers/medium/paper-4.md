# Medium Paper 4

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-4-key.md`. Suggested time: 90 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** `[CODE — 20 min]` You have `boolean isBad(int version)` over
versions `1..n`; once a version is bad, all later ones are bad. Write
`int firstBad(int n)` minimizing calls to `isBad`. It must handle
first-bad = 1, first-bad = n, and avoid integer overflow. Test with a stub.

**Q2.** For each requirement, name the best-fit structure and justify in
one line: (a) always retrieve the smallest element ≥ x, with ongoing
inserts; (b) top-10 most frequent items from a large stream; (c) O(1)
insert, delete, and get-random-element; (d) sliding-window maximum.

## Section 2 — Java Core

**Q3.** `Optional`: show correct usage as a return type and TWO abuses.
Then: what's the practical difference between `orElse(loadDefault())` and
`orElseGet(this::loadDefault)`?

**Q4.** Working with money: why is `double` wrong for currency
(the mechanism), why does `new BigDecimal(0.1)` not fix it, and what's the
difference between `equals` and `compareTo` for
`new BigDecimal("1.0")` vs `new BigDecimal("1.00")`?

## Section 3 — Concurrency & JVM

**Q5.** `counter++` on a shared `int` field is broken under concurrency.
Show three progressively better/different fixes (`synchronized`,
`AtomicInteger`, `LongAdder`) and state when each is the right choice.

**Q6.** What is a `ThreadLocal`? Describe a legitimate use and the classic
leak scenario when the threads come from a pool — why does the leak happen
and what's the discipline that prevents it?

## Section 4 — Spring & JPA

**Q7.** Describe the JPA/Hibernate first-level cache (persistence context)
behavior: within one transaction you call `findById(42)` twice — how many
SQL queries run? Then a batch job loads 500k entities in one transaction
and slowly OOMs — connect the two and give the fix.

**Q8.** `merge()` on a detached entity: what exactly does it do, what's the
classic bug with the method's return value, and how does Spring Data's
`save()` decide between persist and merge?

## Section 5 — SQL & Databases

**Q9.** `[CODE]` Table `payments(id, user_id, amount, status, created_at)`.
Write: (a) each user's most recent payment (full row); (b) find users with
two or more FAILED payments within any single calendar day.

**Q10.** UPSERT: you want "insert this row; if the key exists, update it"
without a race under concurrency. Why is `SELECT`-then-`INSERT/UPDATE` in
application code broken, and what's the single-statement Postgres solution?

## Section 6 — Networking & OS

**Q11.** DNS in a failover scenario: your DB endpoint's DNS was repointed
to a standby, but your Java service keeps connecting to the dead primary
for a long time. Name two distinct caching layers that can cause this and
the fix for the JVM-side one.

**Q12.** You're on a production box that "feels slow." Give the specific
commands/readings to determine whether the bottleneck is CPU, memory, or
disk I/O — and explain what load average means relative to core count and
how `%wa` (iowait) changes your conclusion.

## Section 7 — API & Web Security

**Q13.** Session-cookie auth vs stateless JWT auth: how does each handle
(a) horizontal scaling, (b) immediate revocation (user logged out /
compromised), (c) what data lives where? Conclude with when you'd choose
each.

**Q14.** Why do prepared statements stop SQL injection — explain the
mechanism (what travels where), not the slogan. Then: does the same
principle have an analog for preventing XSS? Name it.

## Section 8 — Messaging & Caching

**Q15.** Retries with exponential backoff: why is backoff alone
insufficient when a downstream service recovers from an outage, what does
jitter add, and what is a retry storm?

**Q16.** Your team runs a `@Scheduled` cleanup job inside the service. It
worked with one instance; now there are three and the job runs three times.
Give three distinct solutions with one trade-off each.

## Section 9 — Testing & Craft

**Q17.** `[CODE — 20 min]` Write JUnit 5 + Mockito tests for:
```java
public class SubscriptionService {
    private final SubscriptionRepo repo;      // interface
    private final Clock clock;
    /** Renews if active and expiring within 7 days of 'today'.
     *  Returns false if not due. Throws NotFoundException if id unknown. */
    public boolean renewIfDue(String subscriptionId) { ... }
}
```
Cover: due-and-renewed, not-yet-due, unknown id. Control time properly.

**Q18.** You ran `git reset --hard HEAD~3` and realize those 3 commits
weren't pushed anywhere. Are they gone? Explain the mechanism of recovery
and the command that makes it possible.

## Section 10 — Cloud & DevOps

**Q19.** Explain Docker image layers: what creates a layer, how the build
cache uses them, and the correct ordering of a Java service's Dockerfile
instructions to maximize cache hits during normal development.

**Q20.** Walk through the full lifecycle of a zero-downtime instance
replacement behind a load balancer: from "new version deployed" to "old
instance terminated," naming the role of readiness checks, connection
draining, and SIGTERM.
