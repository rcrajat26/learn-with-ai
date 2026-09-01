# Easy Paper 5

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-5-key.md`. Suggested time: 65 min.
21 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** Arrays vs linked lists: compare them on (a) access by index,
(b) insertion in the middle, (c) memory layout. Which usually wins in
practice on modern hardware, and why?

**Q2.** What is recursion? What two things must every correct recursive
function have, and what happens at runtime if one of them is missing?

## Section 2 — Java Core

**Q3.** `List`, `Set`, `Map` — for each, name its defining property and one
concrete situation where it's the right choice.

**Q4.** What are generics for? What does `List<String>` give you at compile
time that a raw `List` doesn't, and what class of runtime error does it
prevent?

## Section 3 — Concurrency & JVM

**Q5.** What does the `volatile` keyword guarantee, and what does it NOT
guarantee? Is `volatile int counter; counter++;` thread-safe?

**Q6.** Name the states a Java thread can be in between creation and death
(approximate names accepted), and what typically causes a thread to be
BLOCKED vs WAITING.

## Section 4 — Spring & JPA

**Q7.** `@RestController` vs `@Controller` — what's the difference, and
what does `@RequestBody` / `@ResponseBody` have to do with it?

**Q8.** What are database migrations (Flyway/Liquibase style)? Why are they
preferred over letting Hibernate auto-create/update the schema
(`ddl-auto=update`) in production?

## Section 5 — SQL & Databases

**Q9.** `DELETE FROM t WHERE ...` vs `TRUNCATE TABLE t` vs `DROP TABLE t` —
what does each do, and which can be selective?

**Q10.** `[CODE]` Table `orders(id, customer_id, amount, created_at)`.
Write the query: total order amount per customer in 2025, largest total
first, only customers whose total exceeds 10,000.

**Q10b.** A money-transfer service crashes after debiting account A but
before crediting account B — yet no money is lost when the system comes
back. Separately: a report running mid-transfer never sees the debited-
but-not-credited state, and a transfer confirmed to the user survives a
power failure. Name the database property responsible for each of these
three behaviors, and the fourth property of the same family with its
meaning.

## Section 6 — Networking & OS

**Q11.** When your browser requests `https://example.com`, name the
protocol layers/steps involved in order, from typing the URL to receiving
HTML (high-level — four or five steps).

**Q12.** What is a firewall / security group rule? Your Spring Boot app on
a cloud VM runs fine locally on the VM (`curl localhost:8080` works) but
isn't reachable from outside — name two likely causes.

## Section 7 — API & Web Security

**Q13.** What is a bearer token? Where does it travel in an HTTP request,
and why must such requests only be sent over HTTPS?

**Q14.** What is CORS at a high level? Which side (browser or server)
enforces it, and does it protect the server from non-browser clients like
`curl`?

## Section 8 — Messaging & Caching

**Q15.** If a producer keeps publishing while all consumers are down for an
hour, what happens (a) with a queue like SQS, (b) with a plain HTTP call
retried a few times? What does this tell you about why queues exist?

**Q16.** What is Redis? Name two data structures it offers beyond plain
key→string, and one typical use for each.

## Section 9 — Testing & Craft

**Q17.** What makes a good commit message? Write a good one for a change
that fixes a bug where discounts were applied twice for gold-tier customers.

**Q18.** What is a code review for? Give three distinct things a reviewer
should look for, in priority order.

## Section 10 — Cloud & DevOps

**Q19.** Vertical vs horizontal scaling — define each, one limitation of
each, and which one a load balancer enables.

**Q20.** What is the difference between a deployment environment
(dev/staging/prod) and why should staging resemble prod? Name one bug class
that only shows up when they differ.
