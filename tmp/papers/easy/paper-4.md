# Easy Paper 4

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-4-key.md`. Suggested time: 65 min.
21 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** How does an `ArrayList` grow when it runs out of capacity? Why is
`new ArrayList<>(10_000)` sometimes worth writing?

**Q2.** `[CODE — 10 min]` Write a method `Map<Character, Integer>
charFrequencies(String s)` returning how often each character appears in
`s`. Then state its time and space complexity.

## Section 2 — Java Core

**Q3.** What does `static` mean on (a) a field and (b) a method? Why can't
a static method access instance fields directly?

**Q4.** Predict the output and explain:
```java
List<String> names = List.of("anna", "bob", "ANNA", "cara");
long n = names.stream()
    .map(String::toLowerCase)
    .filter(s -> s.startsWith("a"))
    .distinct()
    .count();
System.out.println(n);
```

## Section 3 — Concurrency & JVM

**Q5.** Two ways to define work for a thread: implementing `Runnable` vs
extending `Thread` — which is preferred and why? What's the difference
between calling `start()` and calling `run()` directly?

**Q6.** What is garbage collection? Which objects are eligible? Does
`System.gc()` guarantee a collection?

## Section 4 — Spring & JPA

**Q7.** What is the difference between `application.properties` /
`application.yml` and Spring profiles (`application-prod.yml`)? When does
the profile-specific file win?

**Q8.** In JPA, what do LAZY and EAGER fetching mean? Which associations
default to which (name one of each)?

## Section 5 — SQL & Databases

**Q9.** Predict the results:
(a) `SELECT * FROM users WHERE middle_name = NULL;`
(b) `SELECT * FROM users WHERE middle_name IS NULL;`
Why do they differ?

**Q10.** ACID: name the four properties and give a one-line meaning of each.

## Section 6 — Networking & OS

**Q11.** What is `localhost` / `127.0.0.1`? Your app "works on localhost"
but a teammate can't reach `http://localhost:8080` from their machine — why
is that expected?

**Q12.** What does SSH give you? What are the two common ways to
authenticate an SSH session, and which is preferred for automation?

## Section 7 — API & Web Security

**Q13.** For `GET /users/42/orders?status=SHIPPED&page=2`, identify the path
parameter and the query parameters. When does data belong in the path vs
the query string vs the request body?

**Q14.** What is SQL injection? Show a one-line vulnerable Java example
(string-built query) and the safe version.

**Q14b.** A colleague proposes securing stored user passwords by
encrypting them with an RSA public/private key pair, "so even the DB admin
can't read them." Explain what's wrong with this design, what the correct
approach is, and name the property the correct approach has that ANY
encryption scheme lacks.

## Section 8 — Messaging & Caching

**Q15.** What is a dead letter queue (DLQ)? Describe the path a message
takes to end up there, and why a DLQ needs monitoring.

**Q16.** In-process cache (e.g., a `HashMap`/Caffeine inside your service)
vs external cache (e.g., Redis): one advantage of each. What goes wrong
with in-process caches when you run 4 instances of the service?

## Section 9 — Testing & Craft

**Q17.** `assertEquals(expected, actual)` — why does argument order matter
in practice? And why is a test with no assertions still "passing" a problem?

**Q18.** What is Continuous Integration? Name three checks a typical CI
pipeline runs on every pull request.

## Section 10 — Cloud & DevOps

**Q19.** Where do application logs go in a containerized/cloud setup, and
why is writing them to a local file on the container a bad idea?

**Q20.** What is a health-check endpoint (e.g., `/health`)? Name two
systems that call it and what each does with the answer.
