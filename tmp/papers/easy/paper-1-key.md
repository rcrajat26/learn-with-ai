# Easy Paper 1 — Answer Key

Score 1 = all key points; 0.5 = right idea with a gap; 0 = wrong/blank.

**Q1.** (a) O(1) average; (b) O(1); (c) O(log n); (d) O(n) — all later
elements shift right.

**Q2.** FIFO → queue; LIFO → stack. Java: `ArrayDeque` serves both
(`offer/poll` as queue, `push/pop` as stack). Accept `LinkedList` for queue;
`java.util.Stack` gets 0.5 (legacy, synchronized, discouraged).

**Q3.** `a == b` → false: `a` points to the string-pool literal, `new String`
forces a distinct heap object; `==` compares references. `a.equals(b)` →
true: compares character content.

**Q4.** The character content of a `String` object can never change; any
"modification" creates a new object. Consequence: `+=` in a loop copies the
whole string each time (O(n²)) — use `StringBuilder`. (Other valid
consequences: safe as map keys / thread-safe sharing / hashCode caching.)

**Q5.** Process = isolated memory space + resources; thread = unit of
execution inside a process. Threads of one process share the heap (objects,
static fields) and file handles; each has its own stack and program counter.

**Q6.** Two+ threads access shared data concurrently, at least one writes,
and the result depends on interleaving. Example: `counter++` — a
read-modify-write of three steps; concurrent increments can be lost.

**Q7.** DI: a class receives its dependencies instead of constructing them —
decoupling and easy substitution (e.g., mocks in tests). Mechanism: the
container instantiates beans and passes required beans into the constructor
(or injects fields) when building the object graph.

**Q8.** Mechanically near-identical — all mark a class for component
scanning. They differ semantically (layer labeling), plus `@Repository` adds
persistence-exception translation. Saying "no difference at all" = 0.5;
saying they're totally different mechanisms = 0.

**Q9.** `WHERE` filters rows before grouping/aggregation; `HAVING` filters
groups after aggregation. `WHERE` runs first. Aggregate conditions
(`COUNT(*) > 5`) must live in `HAVING`.

**Q10.** INNER keeps only matching rows from both sides; LEFT keeps every
row of the left table, NULL-filling right columns when unmatched. The
orphan order survives a LEFT JOIN (orders on the left), not an INNER JOIN.

**Q11.** TCP: reliable delivery (retransmission), ordering, connection +
flow/congestion control — HTTP(S), databases. UDP: none of those, just
datagrams — DNS queries, video/voice streaming, QUIC. Any two guarantees +
one example each.

**Q12.** Translates human-readable domain names into IP addresses via a
hierarchical lookup. An `A` record holds an IPv4 address.

**Q13.** 401: not authenticated — we don't know who you are (or credentials
invalid). 403: authenticated but not allowed to do this. 404: resource
doesn't exist (or you hide its existence).

**Q14.** Create → `POST /users`; Read → `GET /users` (list), `GET /users/{id}`
(single); Update → `PUT /users/{id}` (full) or `PATCH /users/{id}` (partial);
Delete → `DELETE /users/{id}`.

**Q15.** Any two: caller doesn't wait (async, lower latency for the user);
consumer can be down without losing requests (buffering/durability);
absorbs traffic spikes; producers and consumers scale independently.

**Q16.** Small, fast store holding copies of expensive-to-fetch data.
Redis: in-memory (no disk I/O on the read path), simple key lookup (no SQL
parsing/planning/locking). "It's in memory" is the essential point.

**Q17.** Unit: one class/component in isolation, collaborators replaced by
test doubles. Integration: multiple components with real collaborators (DB,
HTTP). Unit tests are faster — no I/O, no containers/context startup.

**Q18.** A stand-in object with programmed behavior, replacing a real
dependency — isolates the code under test, avoids slow/nondeterministic
calls, lets you simulate failures. Example: payment gateway client, external
HTTP API, repository.

**Q19.** EC2: rent virtual machines. S3: object storage — files/blobs behind
an HTTP API (not a filesystem). RDS: managed relational databases
(Postgres/MySQL — provisioning, backups, patching handled).

**Q20.** Docker packages an app + its dependencies into a portable unit
running isolated on a shared host kernel. Image: immutable template (layers).
Container: a running (or stopped) instance of an image with its own writable
layer.

---

**Interpretation:** 17+ solid; 12–16 review the misses; < 12 the easy tier
has real gaps — record which sections lost marks and feed into
`qbank/13-scoring-and-report.md` findings.
