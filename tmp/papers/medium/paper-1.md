# Medium Paper 1

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor
(no autocomplete-driven guessing). Answer separately before opening
`paper-1-key.md`. Suggested time: 90 min. 20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** State the equals/hashCode contract, then describe concretely what
goes wrong inside a `HashMap` when a class overrides `equals` but not
`hashCode` and instances are used as keys.

**Q2.** Walk through what happens internally on `map.put(key, value)` for a
`HashMap`: how the bucket is chosen, what happens on a collision, and what
happens when the map gets "too full."

## Section 2 — Java Core

**Q3.** Predict the output and explain precisely:
```java
List<Integer> list = new ArrayList<>(List.of(5, 10, 15));
list.remove(10);
System.out.println(list);
```

**Q4.** Predict the outputs and explain the difference:
```java
Integer a = 127, b = 127;
Integer c = 500, d = 500;
System.out.println(a == b);
System.out.println(c == d);
System.out.println(c.equals(d));
```

## Section 3 — Concurrency & JVM

**Q5.** `synchronized` vs `volatile`: state exactly what each guarantees
(two properties are in play). Give one example where `volatile` alone is
sufficient and one where it is not.

**Q6.** Spot the bug and fix it:
```java
private final Map<String, Config> cache = new ConcurrentHashMap<>();
Config get(String key) {
    if (!cache.containsKey(key)) {
        cache.put(key, loadFromDb(key));   // expensive call
    }
    return cache.get(key);
}
```

## Section 4 — Spring & JPA

**Q7.** How do `@Transactional` and `@Cacheable` actually work at runtime?
Describe the mechanism Spring uses and one concrete limitation that
mechanism imposes on your code.

**Q8.** Predict the behavior and explain:
```java
@Service
public class OrderService {
    @Transactional
    public void process(Order o) { repo.save(o); this.audit(o); }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void audit(Order o) { auditRepo.save(auditOf(o)); }
}
```
`process()` is called from a controller. Does `audit` get its own
transaction? Give two fixes.

## Section 5 — SQL & Databases

**Q9.** `[CODE]` Tables: `employees(id, name, dept_id, salary)`,
`departments(id, name)`. Write the query: the top 2 earners in each
department (employee name, department name, salary).

**Q10.** A composite index exists on `(customer_id, created_at)`. For each
query, say whether the index can be used efficiently and why:
(a) `WHERE customer_id = 42`
(b) `WHERE customer_id = 42 AND created_at > '2025-01-01'`
(c) `WHERE created_at > '2025-01-01'`

## Section 6 — Networking & OS

**Q11.** Walk through everything that happens between typing
`https://shop.example.com` and the page rendering. Cover at minimum: DNS
(with caching), TCP, TLS, and the HTTP exchange — in order, with one
sentence of mechanism each.

**Q12.** Your HTTP client calling a downstream service "hangs." Explain the
difference between connect timeout and read timeout, what each one's firing
tells you about the failure, and what the default is in many Java clients
if you configure neither.

## Section 7 — API & Web Security

**Q13.** PUT vs PATCH vs POST for updates: semantic difference, which are
idempotent, and why idempotency matters when a client retries after a
timeout.

**Q14.** Design the pagination for `GET /orders` (high-volume, frequently
inserted). Offset-based vs cursor-based: how each works, two failure modes
of offset at scale, and what the response body should contain in your
chosen design.

## Section 8 — Messaging & Caching

**Q15.** At-most-once vs at-least-once vs exactly-once delivery: define
each via WHERE the acknowledgment happens relative to processing. Which is
the practical default, and what obligation does it place on the consumer?

**Q16.** Describe the cache-aside pattern's read path and write path. On
writes, why is deleting the cache key generally preferred over updating the
cached value in place?

## Section 9 — Testing & Craft

**Q17.** Mock vs stub vs fake — define each. A service uses (a) a
repository interface, (b) an HTTP client for a third-party API, (c) a pure
`TaxCalculator` class. In a unit test, what do you do with each and why?

**Q18.** Your business logic calls `LocalDate.now()` internally. Why is
that a testing problem (give the concrete bug class), and what's the
standard fix — show the shape of the fixed code and the test.

## Section 10 — Cloud & DevOps

**Q19.** Why do cloud services (ECS tasks, EC2 instances) use IAM roles
instead of an access key + secret in configuration? Explain what a role
gives you mechanically.

**Q20.** Liveness vs readiness checks: what question does each answer, who
acts on each, and describe the failure storm caused by wiring a dependency
outage into the liveness check.
