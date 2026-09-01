# Easy Paper 2 — Answer Key

**Q1.** O(n²) — n iterations of an n-step inner loop. With `j = i`: still
O(n²) (triangular number ≈ n²/2; constants drop).

**Q2.** Two pointers from both ends, skipping non-alphanumeric
(`Character.isLetterOrDigit`), comparing lowercased chars. Full mark:
handles empty string and all-punctuation input. Building a cleaned string
then comparing with its reverse also earns full mark if correct.

**Q3.** Checked: compiler forces callers to catch or declare (`throws`) —
e.g., `IOException`, `SQLException`. Unchecked: subclasses of
`RuntimeException`, no compiler enforcement — e.g.,
`NullPointerException`, `IllegalArgumentException`.

**Q4.** Differences (any two): abstract classes can hold state
(instance fields) and constructors, interfaces can't; a class extends one
abstract class but implements many interfaces; interface methods are
implicitly public. Must-use-abstract-class: shared mutable state or a base
with constructor logic/protected helpers (template-method style).

**Q5.** Any two: thread creation/destruction is expensive — pools reuse;
bounds concurrency (unbounded thread creation exhausts memory/CPU);
queueing, lifecycle management, and metrics come built in.

**Q6.** Mutual exclusion — one thread at a time in any synchronized method
of that object (same monitor) — plus visibility: writes made before
releasing the monitor are visible to the next acquirer.

**Q7.** Boot adds auto-configuration, embedded server, opinionated defaults
— running app without XML/manual wiring. A starter brings a curated,
version-compatible dependency set AND triggers matching auto-configuration
(e.g., `spring-boot-starter-web` → Tomcat + Spring MVC + Jackson,
configured).

**Q8.** `@Entity` annotation + a mapped table (+ no-arg constructor
requirement). `@Id` marks the primary-key field. `@GeneratedValue`
delegates key generation to the provider/DB (identity/sequence) instead of
you assigning ids.

**Q9.**
```sql
SELECT name, salary FROM employees
WHERE dept = 'SALES' AND salary > 50000
ORDER BY salary DESC;
```

**Q10.**
```sql
SELECT dept, COUNT(*) AS cnt FROM employees
GROUP BY dept HAVING COUNT(*) > 10;
```
Using WHERE for the count condition = 0.

**Q11.** 2xx success; 3xx redirection (go elsewhere / not modified); 4xx
client error — the request is wrong (fix the caller); 5xx server error —
the request was acceptable, the server failed (fix the server).

**Q12.** IP identifies a host on the network; a port identifies a specific
process/service on that host. One machine runs many networked services
simultaneously — ports let the OS route packets to the right one.

**Q13.** Any two: GET has no meaningful body / POST carries one; GET is
cacheable and bookmarkable (params in URL — also a leak risk), POST isn't
by default; GET is safe/idempotent by contract, POST isn't; browsers may
re-prompt on POST refresh.

**Q14.** Plain text: any DB leak exposes every password (reused across
sites). Reversible encryption: the key lives somewhere — whoever/whatever
has it can decrypt them all. Instead: salted, deliberately-slow one-way
hashing; verify by hashing the attempt. Bonus names: bcrypt, argon2, scrypt.

**Q15.** Time-to-live — the entry auto-expires after the duration. Read
after expiry = miss → reload from source → repopulate. Acceptable because
cached data tolerates bounded staleness by design; TTL caps how stale.

**Q16.** Asynchronous — transcoding takes minutes; holding the HTTP request
open would time out and pin resources. API responds `202 Accepted` with a
job id / status URL (or fires a callback/notification when done).

**Q17.** `commit`: records a snapshot locally. `push`: uploads local commits
to the remote. `fetch`: downloads remote changes without touching your
branch. `pull`: fetch + merge (or rebase) into your branch.

**Q18.** Both branches changed the same region of the same file (or one
deleted it); git can't pick automatically — it inserts `<<<<<<<`/`>>>>>>>`
markers. Resolve: edit the file to the intended content, remove markers,
`git add`, then complete the merge/rebase (`commit` / `rebase --continue`).

**Q19.** Any two: same artifact runs in every environment (build once,
configure at runtime); secrets stay out of source control; ops can change
config without rebuild/redeploy of code.

**Q20.** Distributes requests across instances. Beyond spreading (any two):
health checks — stops routing to dead instances (availability); enables
horizontal scaling and zero-downtime deploys (drain one instance while
others serve); single entry point for TLS.

---

**Interpretation:** 17+ solid; 12–16 targeted review; < 12 record section
losses as findings.
