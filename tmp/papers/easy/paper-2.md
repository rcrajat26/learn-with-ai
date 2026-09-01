# Easy Paper 2

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-2-key.md`. Suggested time: 60 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** What is the time complexity of this snippet, and why?
```java
for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++)
        sum += a[i] + a[j];
```
Follow-up: and if the inner loop started at `j = i`?

**Q2.** `[CODE — 10 min]` Write a method `boolean isPalindrome(String s)`
that ignores case and non-alphanumeric characters ("A man, a plan, a canal:
Panama" → true).

## Section 2 — Java Core

**Q3.** Checked vs unchecked exceptions: what's the compiler-level
difference, and name one standard example of each.

**Q4.** Interface vs abstract class — two differences, and one situation
where you must use an abstract class.

## Section 3 — Concurrency & JVM

**Q5.** Why use a thread pool (`ExecutorService`) instead of creating a
`new Thread()` per task? Give two reasons.

**Q6.** What does the `synchronized` keyword guarantee when two threads call
the same synchronized method of one object?

## Section 4 — Spring & JPA

**Q7.** What does Spring Boot add on top of the Spring Framework? Name two
concrete things a "starter" dependency gives you.

**Q8.** What makes a class a JPA entity? What is `@Id` for, and what does
`@GeneratedValue` change?

## Section 5 — SQL & Databases

**Q9.** `[CODE]` Table `employees(id, name, dept, salary)`. Write the query:
names and salaries of employees in dept 'SALES' earning above 50000, highest
salary first.

**Q10.** `[CODE]` Same table. Write the query: each dept with its employee
count, only for depts having more than 10 employees.

## Section 6 — Networking & OS

**Q11.** What do the status-code classes 2xx, 3xx, 4xx, 5xx each mean?
Whose "fault" is a 4xx vs a 5xx?

**Q12.** What is an IP address and what is a port? Why does a machine with
one IP need ports at all?

## Section 7 — API & Web Security

**Q13.** GET vs POST: two differences beyond "GET reads, POST writes"
(think: caching, body, idempotency, URL visibility).

**Q14.** Why must passwords never be stored in plain text — and why is
encrypting them (reversibly) also wrong? What's done instead (name the
concept; naming an algorithm is a bonus)?

## Section 8 — Messaging & Caching

**Q15.** What does TTL mean on a cache entry? What happens on a read after
the TTL expires, and why is that usually acceptable?

**Q16.** Synchronous vs asynchronous processing: the user uploads a video
that needs transcoding. Which fits, and what does the API respond with?

## Section 9 — Testing & Craft

**Q17.** In git: `commit` vs `push`, and `fetch` vs `pull` — one sentence
each.

**Q18.** What is a merge conflict, when does git raise one, and what are
the manual steps to resolve it?

## Section 10 — Cloud & DevOps

**Q19.** Why configure a service through environment variables instead of
hardcoding values in the source or a committed file? Give two reasons.

**Q20.** What is a load balancer? Name two things it enables beyond
"spreading traffic."
