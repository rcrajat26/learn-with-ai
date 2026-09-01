# Medium Paper 2

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-2-key.md`. Suggested time: 90 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** Explain why adding n elements to an `ArrayList` is O(n) total even
though individual `add` calls occasionally trigger a full copy. What is the
term for this kind of analysis?

**Q2.** `[CODE — 15 min]` Write `int[] twoSum(int[] nums, int target)`
returning the indices of the two numbers that sum to `target` (exactly one
solution) in O(n) time. State why your solution is O(n).

## Section 2 — Java Core

**Q3.** Predict what happens and explain the mechanism:
```java
List<String> l = new ArrayList<>(List.of("a", "b", "c"));
for (String s : l) {
    if (s.equals("b")) l.remove(s);
}
```
Give two correct ways to remove matching elements while iterating.

**Q4.** Explain type erasure in one paragraph. Then explain what PECS
(`? extends` / `? super`) is for, using a method that copies from one list
to another as the example.

## Section 3 — Concurrency & JVM

**Q5.** Spot the bug and fix it — two accounts, concurrent transfers:
```java
void transfer(Account from, Account to, long amt) {
    synchronized (from) {
        synchronized (to) {
            from.debit(amt); to.credit(amt);
        }
    }
}
```

**Q6.** For a `ThreadPoolExecutor`: explain the roles of core pool size,
max pool size, and the work queue — in what order are they exercised as
load rises? What surprising behavior results from using an unbounded queue?

## Section 4 — Spring & JPA

**Q7.** A singleton `@Service` holds
`private final List<Order> pending = new ArrayList<>()` which request
handlers add to and a scheduled method drains. Name the TWO distinct
problems with this design and how you'd restructure it.

**Q8.** In JPA, explain the entity states (transient, managed, detached,
removed) and what the persistence context is. Why does calling `save()` on
a managed entity inside a transaction do nothing extra?

## Section 5 — SQL & Databases

**Q9.** Predict the result and explain:
```sql
SELECT count(*) FROM employees
WHERE dept_id NOT IN (SELECT dept_id FROM excluded_departments);
```
where `excluded_departments.dept_id` contains one NULL row. What's the safe
rewrite?

**Q10.** Give four distinct reasons why the query planner might NOT use an
existing index on `email` for `SELECT * FROM users WHERE ...` — with a
one-line explanation each.

## Section 6 — Networking & OS

**Q11.** A service making thousands of short-lived outbound HTTP calls per
minute starts failing with "cannot assign requested address." Explain the
mechanism (name the TCP state involved) and the structural fix.

**Q12.** What does a TLS handshake accomplish? Name its three goals and
explain why asymmetric cryptography is only used at the start, with
symmetric keys doing the rest.

## Section 7 — API & Web Security

**Q13.** A JWT arrives at your API. List everything the server must
validate before trusting it, and explain why the payload being base64
(readable by anyone) is not a flaw in the design — what does the signature
actually protect?

**Q14.** An SPA at `https://app.example.com` calls your API at
`https://api.example.com` with an `Authorization` header and JSON body.
Describe exactly what the browser does before your controller ever runs,
and what response headers your API must send. Does this mechanism protect
your API from a malicious script running outside a browser?

## Section 8 — Messaging & Caching

**Q15.** Your consumer processed a message (wrote to Postgres) and crashed
before acknowledging; the broker redelivers. Design idempotent handling —
be specific about what the dedup key is, where it's stored, and what makes
the check race-proof.

**Q16.** A hot cache key expires and 5,000 concurrent requests all miss and
hit the database simultaneously. Name this problem and describe three
distinct mitigations.

## Section 9 — Testing & Craft

**Q17.** Name four distinct causes of flaky tests and the specific fix for
each.

**Q18.** merge vs rebase: what does each do to history, what's the golden
rule about rebasing, and when is `git push --force-with-lease` (vs
`--force`) acceptable?

## Section 10 — Cloud & DevOps

**Q19.** Spot at least four problems in this Dockerfile and explain the
consequence of each:
```dockerfile
FROM openjdk:latest
COPY . /app
WORKDIR /app
RUN ./mvnw package
ENV DB_PASSWORD=prodSecret123
EXPOSE 8080
CMD ["java", "-jar", "target/service.jar"]
```

**Q20.** The same container image must run in staging and prod with
different database endpoints and credentials. Describe the correct setup:
where configuration and secrets each live, how they reach the container,
and two places secrets must never appear.
