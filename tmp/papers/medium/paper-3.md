# Medium Paper 3

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-3-key.md`. Suggested time: 90 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** `[CODE — 15 min]` Write `boolean isValid(String s)` for bracket
strings of `()[]{}` — valid means correct types and nesting order. Must
handle `"([)]"` → false and `"("` → false. State the complexity.

**Q2.** Give the time and space complexity of each, with one line of
justification:
(a) ```java
for (int i = 1; i < n; i *= 2)
    for (int j = 0; j < n; j++) work();
```
(b) ```java
int f(int n) { return n <= 1 ? 1 : f(n-1) + f(n-1); }
```

## Section 2 — Java Core

**Q3.** `[CODE — 15 min]` Given
`record Employee(String dept, String name, double salary)` and a
`List<Employee>`, write stream expressions for:
(a) sorted by dept ascending, then salary descending;
(b) `Map<String, Double>` of average salary per dept;
(c) `Map<String, List<String>>` of employee names per dept.

**Q4.** What's fragile about this code? Explain the two distinct issues:
```java
List<String> adults = users.stream()
    .filter(u -> u.getAge() >= 18)
    .peek(u -> u.setVerified(true))
    .map(User::getName)
    .toList();
```

## Section 3 — Concurrency & JVM

**Q5.** Predict what this prints and explain; then show how to handle the
error properly:
```java
CompletableFuture<String> f = CompletableFuture
    .supplyAsync(() -> { throw new IllegalStateException("boom"); })
    .thenApply(s -> s + "!");
f.thenAccept(System.out::println);
Thread.sleep(200);
```

**Q6.** Explain the JVM's generational garbage collection: what the
generational hypothesis says, what young vs old generations are for, and
why frequent short-lived allocations are usually cheap.

## Section 4 — Spring & JPA

**Q7.** A teammate writes all dependencies as `@Autowired` fields. Make the
case for constructor injection: give three concrete advantages, including
what breaks first with field injection.

**Q8.** Spot the bug:
```java
@Transactional
public void importOrders(File f) throws ParseException {
    repo.save(parseHeader(f));       // succeeds
    for (Line l : parseBody(f))      // throws ParseException (checked)
        repo.save(toOrder(l));
}
```
The file is malformed mid-way. What state is the database left in and why?
How do you fix the annotation?

## Section 5 — SQL & Databases

**Q9.** Spot the bug — this report must show ALL departments including
zero-employee ones, but some vanish:
```sql
SELECT d.name, COUNT(e.id)
FROM departments d
LEFT JOIN employees e ON e.dept_id = d.id
WHERE e.hired_on >= '2025-01-01'
GROUP BY d.name;
```
Explain the mechanism and give the fix.

**Q10.** Define the read anomalies: dirty read, non-repeatable read,
phantom read. For READ COMMITTED and SERIALIZABLE, state which anomalies
each permits. What's PostgreSQL's default level?

## Section 6 — Networking & OS

**Q11.** HTTP/1.1 with keep-alive vs HTTP/2: what limitation of 1.1 did
multiplexing solve, how did browsers work around it before, and what
head-of-line blocking problem does HTTP/2 still have (that HTTP/3
addresses)?

**Q12.** What happens to a Java platform thread when it calls
`socket.read()` and no data is available? Relate this to (a) why
thread-per-request has a scaling ceiling, and (b) what "Too many open
files" means and how you'd diagnose it.

## Section 7 — API & Web Security

**Q13.** Explain CSRF: the attack scenario step by step, why it works with
cookie-based sessions, why a bearer token in the `Authorization` header is
not vulnerable, and two defenses for the cookie case.

**Q14.** Design REST endpoints for: (a) listing a customer's orders,
(b) cancelling an order, (c) retrying a failed payment — the last two are
not plain CRUD. Give paths + methods and justify your handling of the
non-CRUD actions.

## Section 8 — Messaging & Caching

**Q15.** A malformed message crashes your consumer; it restarts, reads the
same message, crashes again — the queue is now blocked. Design the fix:
cover retry policy, the retryable vs non-retryable distinction, and what
happens to the message at the end.

**Q16.** Why is global ordering across a distributed message system
fundamentally at odds with throughput? What is the standard compromise, how
do you choose the partition key, and what new problem can a bad key choice
create?

## Section 9 — Testing & Craft

**Q17.** Testing the repository layer: H2 in-memory vs Testcontainers with
real Postgres — give the trade-off, one concrete example of a bug H2 hides,
and your recommendation.

**Q18.** A bug exists on `main`; release `v2.3` (about 400 commits ago) was
fine. Describe the most efficient way to find the offending commit, roughly
how many steps it takes, and how to automate it if you have a script that
reproduces the bug.

## Section 10 — Cloud & DevOps

**Q19.** Your service must scale from 2 to 10 instances under load. List
four kinds of state that must be evicted from the instances first, and
where each goes.

**Q20.** Logs vs metrics vs traces: define each, state what question each
answers best, and give one example where only that pillar can answer it.
