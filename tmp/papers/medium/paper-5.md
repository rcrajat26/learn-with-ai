# Medium Paper 5

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `paper-5-key.md`. Suggested time: 90 min.
20 questions, 1 mark each.

## Section 1 — DSA & Data Structures

**Q1.** `[CODE — 25 min]` Write
`int lengthOfLongestSubstring(String s)` — length of the longest substring
without repeating characters (`"abcabcbb"` → 3, `"pwwkew"` → 3, `""` → 0)
in O(n). Explain the invariant your window maintains.

**Q2.** `PriorityQueue` in Java: what structure backs it, complexities of
`peek`/`offer`/`poll`, why is arbitrary `remove(Object)` O(n), and what
ordering do you get when iterating it directly?

## Section 2 — Java Core

**Q3.** Design decisions for an immutable `DateRange` class (start, end):
list four things the class must do/avoid to be genuinely immutable,
including how to handle a constructor parameter or getter of a mutable type
(pretend the fields were `java.util.Date`).

**Q4.** Java 8 → 21, pick four features you'd actually use in a backend
service and give a one-line concrete use for each. (Records, sealed
interfaces, pattern-matching switch, virtual threads, text blocks, `var`,
`Optional`, Streams `toList()` are all fair game.)

## Section 3 — Concurrency & JVM

**Q5.** Double-checked locking for a lazy singleton: write or sketch the
correct version and explain why the `volatile` on the field is not
optional — what specifically can go wrong without it?

**Q6.** An OutOfMemoryError in production: name three DISTINCT kinds of
OOM the JVM can throw, what each indicates, and the single JVM flag you
want enabled in advance to make diagnosis possible.

## Section 4 — Spring & JPA

**Q7.** A controller returns a JPA `Order` entity; JSON serialization of
`order.getItems()` throws `LazyInitializationException`. Explain the exact
mechanism (what closed, what's missing), then give three different fixes
and rank them.

**Q8.** Spot the N+1 and fix it three ways:
```java
List<Author> authors = authorRepo.findAll();        // 200 authors
for (Author a : authors)
    report.add(a.getName() + ": " + a.getBooks().size());
```
State how many queries run as written.

## Section 5 — SQL & Databases

**Q9.** Explain, mechanically, why `ORDER BY created_at DESC LIMIT 20
OFFSET 1000000` is slow, and write the keyset-pagination replacement
(assume `(created_at, id)` are available and indexed).

**Q10.** Two transactions at READ COMMITTED both run
`SELECT balance FROM accounts WHERE id = 1` (returns 100), compute
`balance - 60` in application code, and `UPDATE accounts SET balance = 40`.
Both commit. What happened, why didn't the isolation level prevent it, and
give two distinct fixes.

## Section 6 — Networking & OS

**Q11.** WebSockets vs HTTP polling vs server-sent events: how does the
WebSocket connection get established (name the mechanism), and give one
scenario each where polling or SSE is actually the better choice.

**Q12.** Explain what happens at the OS level that allows a single thread
to serve tens of thousands of concurrent connections (the model behind
Netty/Node). Name the Linux facility, and contrast with the
thread-per-connection model.

## Section 7 — API & Web Security

**Q13.** Design rate limiting for a public API: pick an algorithm and
explain it, state what the client sees when limited (status + headers),
and name the complication when your API runs on 10 instances.

**Q14.** Your JWT-protected API must also serve machine-to-machine calls
from a partner's backend (no user involved). Which OAuth2 grant fits, how
does it work in three steps, and why are the implicit and password grants
deprecated?

## Section 8 — Messaging & Caching

**Q15.** Compare an SQS-style queue and a Kafka-style log for: what happens
to a message after consumption, adding a second independent consumer
application six months later, and reprocessing yesterday's data after a bug
fix. What does this imply about when each is the right choice?

**Q16.** Local in-process cache (Caffeine) vs distributed cache (Redis) for
a product-catalog lookup service running 6 instances: give two advantages
each, then describe the hybrid pattern and what problem remains with it.

## Section 9 — Testing & Craft

**Q17.** Mockito specifics: (a) when do you need `doThrow/doReturn` instead
of `when...thenReturn`? (b) what does `ArgumentCaptor` do that a matcher
can't — give a concrete use; (c) why is `verify(mock, times(1))` on every
single stubbed call an anti-pattern?

**Q18.** `revert` vs `reset` vs `checkout` (of a file): pick the right tool
for each of these and justify: (a) undo a bad commit already pushed to the
shared branch; (b) unstage and discard local changes to one file; (c) move
your local branch back 2 commits that only exist locally.

## Section 10 — Cloud & DevOps

**Q19.** Your Java container keeps getting OOMKilled by the orchestrator,
but there's no `OutOfMemoryError` in the logs. Explain why these are two
different events, what memory beyond the heap counts toward the container
limit, and two settings that fix the mismatch.

**Q20.** Alert design for a checkout API: give two alerts you SHOULD page
on and two "alerts" that should only be dashboards, and articulate the
principle separating them (include why p99 beats average latency in
alerting).
