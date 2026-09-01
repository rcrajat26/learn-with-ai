# Easy Paper 3

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-3-key.md`. Suggested time: 60 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** `HashMap` vs `TreeMap`: what ordering does each give when you
iterate, and what are the complexities of `get`/`put` in each?

**Q2.** Binary search requires a precondition on the data. What is it, why
does the algorithm break without it, and how many comparisons (roughly) does
it need for 1,000,000 elements?

## Section 2 — Java Core

**Q3.** What are the three distinct uses of the `final` keyword, and what
does each prevent? Does a `final List` field mean the list can't change?

**Q4.** Primitives vs wrapper classes (`int` vs `Integer`): name two
differences, and one place where only the wrapper works.

## Section 3 — Concurrency & JVM

**Q5.** JVM memory: what lives on the heap vs on a thread's stack? Which
error does each produce when exhausted?

**Q6.** What is a deadlock? Describe the minimal setup with two threads and
two locks that produces one.

## Section 4 — Spring & JPA

**Q7.** What does `@Transactional` on a service method do — what starts,
and what are the two possible endings?

**Q8.** Spring Data JPA's `findById` returns `Optional<T>`. What problem
does that design solve compared to returning `T` (or null)?

## Section 5 — SQL & Databases

**Q9.** Primary key vs foreign key vs unique constraint — one sentence each
on what they enforce.

**Q10.** What is a database index? What does it speed up, and what does it
cost you?

## Section 6 — Networking & OS

**Q11.** What extra protection does HTTPS give over HTTP? Name the two main
things an attacker on the same network can do to plain HTTP traffic.

**Q12.** You suspect a process is hogging the CPU on a Linux box. Which
command shows you live per-process CPU/memory? And how do you stop a
process once you know its PID (name the polite way and the forceful way)?

## Section 7 — API & Web Security

**Q13.** Authentication vs authorization — define each, and give the HTTP
status code conventionally used when each one fails.

**Q14.** What does it mean for an operation to be idempotent? Which HTTP
methods are idempotent by contract, and why does it matter for retries?

## Section 8 — Messaging & Caching

**Q15.** In messaging, what do the terms producer, consumer, and broker
mean? What happens to messages if all consumers are temporarily down?

**Q16.** Cache hit vs cache miss. Your cache shows a 15% hit ratio — is the
cache helping? What would you check?

## Section 9 — Testing & Craft

**Q17.** Read this test and state what it verifies, and one thing about its
structure that follows good practice:
```java
@Test
void appliesTenPercentDiscountForLoyalCustomers() {
    Customer c = new Customer("id-1", LoyaltyTier.GOLD);   // given
    BigDecimal price = service.priceFor(c, item);           // when
    assertThat(price).isEqualByComparingTo("90.00");        // then
}
```

**Q18.** Why do teams use feature branches and pull requests instead of
everyone committing straight to `main`? Two reasons.

## Section 10 — Cloud & DevOps

**Q19.** AWS: what is a region, what is an availability zone, and why would
you run a service across two AZs?

**Q20.** What is a rollback? Name two things about how you build/deploy
that make rollbacks fast and safe.
