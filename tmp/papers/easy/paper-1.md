# Easy Paper 1

**Rules:** closed book, no search. Questions marked `[CODE]` allow a plain
editor. Write answers in a separate file before opening `paper-1-key.md`.
Suggested time: 60 min. 20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** State the time complexity of: (a) `HashMap.get(key)`, (b)
`ArrayList.get(index)`, (c) searching a sorted array with binary search,
(d) inserting at index 0 of an `ArrayList`.

**Q2.** You need FIFO processing of tasks, and separately LIFO undo history.
Which data structure for each? Name the Java class you'd actually use for both.

## Section 2 — Java Core

**Q3.** `String a = "hi"; String b = new String("hi");` — what do `a == b`
and `a.equals(b)` each return, and why?

**Q4.** Strings in Java are immutable. What does that mean, and name one
practical consequence for code that builds a large string in a loop.

## Section 3 — Concurrency & JVM

**Q5.** What is the difference between a process and a thread? What do two
threads of the same process share?

**Q6.** What is a race condition? Give a one-line code example of an
operation that looks atomic but isn't.

## Section 4 — Spring & JPA

**Q7.** In one sentence each: what problem does dependency injection solve,
and what does the `@Autowired`/constructor-injection mechanism actually do?

**Q8.** What's the difference between `@Component`, `@Service`, and
`@Repository`?

## Section 5 — SQL & Databases

**Q9.** What's the difference between `WHERE` and `HAVING`? Which runs first?

**Q10.** Explain `INNER JOIN` vs `LEFT JOIN`. If `orders` has a row whose
`customer_id` matches nothing in `customers`, which join keeps it (joining
orders → customers)?

## Section 6 — Networking & OS

**Q11.** TCP vs UDP: name two guarantees TCP gives that UDP doesn't, and one
real protocol/use-case built on each.

**Q12.** What does DNS do? What kind of value does an `A` record hold?

## Section 7 — API & Web Security

**Q13.** Distinguish 401 vs 403 vs 404 — one sentence each.

**Q14.** Map the four CRUD operations onto HTTP methods for a `/users`
resource (collection and single item).

## Section 8 — Messaging & Caching

**Q15.** Give two reasons to put a message queue between two services
instead of a direct HTTP call.

**Q16.** What is a cache? Why is reading from Redis typically much faster
than reading the same value from Postgres?

## Section 9 — Testing & Craft

**Q17.** Unit test vs integration test — define each. Which is usually
faster and why?

**Q18.** What is a mock and why do tests use them? Give one example of a
dependency you would mock.

## Section 10 — Cloud & DevOps

**Q19.** One-liners: what are EC2, S3, and RDS each for?

**Q20.** What is Docker? What's the difference between an image and a
container?
