# Easy Paper 4 — Answer Key

**Q1.** Allocates a bigger array (~1.5× old capacity) and copies all
elements over. Pre-sizing avoids repeated grow-and-copy cycles when you
know you'll add many elements — fewer allocations and copies.

**Q2.**
```java
Map<Character, Integer> freq = new HashMap<>();
for (char c : s.toCharArray()) freq.merge(c, 1, Integer::sum);
```
(`getOrDefault` + `put`, or `computeIfAbsent`, equally fine.) Time O(n);
space O(k) for k distinct characters (O(1) if alphabet bounded, O(n) worst
case).

**Q3.** (a) One copy per class, shared by all instances, exists without any
instance. (b) Callable on the class, no `this`. Static methods have no
instance context — there is no particular object whose fields they could
read; instance fields require a `this`.

**Q4.** Prints `1`. `map` lowercases everything → ["anna", "bob", "anna",
"cara"]; `filter` keeps names starting with "a" → ["anna", "anna"];
`distinct` collapses the duplicates → ["anna"]; `count` → 1. Answering 2
means `distinct` was overlooked — score 0.

**Q5.** Prefer `Runnable` (or `Callable`): separates the task from the
execution mechanism, your class stays free to extend something else, and
it's what pools accept. `start()` creates a new thread that runs `run()`
concurrently; calling `run()` directly executes it synchronously on the
CURRENT thread — no concurrency at all.

**Q6.** Automatic reclamation of heap memory. Eligible: objects no longer
reachable from any live reference chain (GC roots — stacks, statics).
`System.gc()` is a hint only — the JVM may ignore it; no guarantee.

**Q7.** The base file holds defaults for all environments; profile files
hold environment-specific overrides. When a profile is active
(`spring.profiles.active=prod`), `application-prod.yml` values override the
base file's for overlapping keys; non-overlapping base values still apply.

**Q8.** LAZY: the association is loaded on first access, not with the owner.
EAGER: loaded immediately together with the owner. Defaults:
`@OneToMany`/`@ManyToMany` → LAZY; `@ManyToOne`/`@OneToOne` → EAGER.

**Q9.** (a) returns zero rows — `= NULL` evaluates to UNKNOWN for every row
(NULL isn't equal to anything, including NULL); (b) returns the rows where
the column is NULL. NULL requires the special `IS [NOT] NULL` predicate —
three-valued logic.

**Q10.** Atomicity: all of the transaction's changes or none. Consistency:
constraints/invariants hold before and after. Isolation: concurrent
transactions don't see each other's intermediate states (per isolation
level). Durability: once committed, survives crashes.

**Q11.** The loopback address — traffic to it never leaves the machine;
`localhost` on the teammate's machine is THEIR machine, not yours. Reaching
your app requires your machine's network IP (and the app listening on
0.0.0.0 rather than binding only to 127.0.0.1, plus firewall allowing it).

**Q12.** Encrypted remote shell (and file transfer/tunnels) into another
machine. Auth: password, or public/private key pair. Keys are preferred —
no interactive secret, revocable per key, and required for
automation/scripts.

**Q13.** Path param: `42` (identifies the resource). Query params:
`status=SHIPPED`, `page=2` (filtering/pagination modifiers). Path =
resource identity; query = optional filters, sorting, pagination on reads;
body = the data payload of writes (POST/PUT/PATCH).

**Q14.** Attacker-controlled input concatenated into SQL becomes SQL.
Vulnerable: `stmt.executeQuery("SELECT * FROM users WHERE name = '" + name + "'");`
— input `' OR '1'='1` dumps the table. Safe:
`PreparedStatement ps = con.prepareStatement("SELECT * FROM users WHERE name = ?"); ps.setString(1, name);`

**Q14b.** Encryption is reversible by design: whoever/whatever holds the
private key can decrypt EVERY password — the key becomes a single point of
total compromise (and it must live somewhere the application can reach).
Correct approach: salted, deliberately-slow one-way hashing (bcrypt,
argon2, scrypt); verification = re-hash the login attempt and compare. The
property encryption lacks: **irreversibility** — with hashing, the
plaintext is never recoverable by anyone, including you; there is no key
whose theft reveals passwords. (Salt defeats rainbow tables; slowness
defeats brute force.)

**Q15.** A holding queue for messages that repeatedly fail processing.
Path: consumer throws → message redelivered → after N failed attempts the
broker moves it to the DLQ. Monitor it because messages there represent
unprocessed business events — a silent DLQ is silent data loss; someone
must inspect, fix, and replay.

**Q16.** In-process: no network hop — fastest possible reads. External:
shared by all instances, survives restarts, one copy of truth. With 4
instances, each in-process cache is independent: inconsistent values across
instances, 4× memory, and invalidation must somehow reach all four.

**Q17.** Failure messages read "expected X but was Y" — swapped arguments
produce misleading diagnostics and slow debugging. A test without
assertions passes as long as no exception is thrown — it verifies nothing
and gives false confidence (coverage without checking).

**Q18.** Automatically building and validating every change as it's pushed,
so integration problems surface immediately. Typical PR checks (any three):
compile/build, unit tests, integration tests, linter/static analysis,
security/dependency scan, code-coverage gate.

**Q19.** Write to stdout/stderr; the platform (Docker/K8s/ECS) ships them
to a central system (CloudWatch, ELK, Loki). Local files: lost when the
container dies/redeploys, invisible across instances, fill the disk, and
you can't grep 12 containers one by one.

**Q20.** An endpoint reporting whether the instance can serve (optionally
checking its dependencies). Callers (any two): load balancer — stops
routing to unhealthy instances; orchestrator (K8s/ECS) — restarts failed
containers / gates deploy progress; monitoring/alerting — pages a human on
sustained failure.

---

**Interpretation (out of 21):** 18+ solid; 13–17 targeted review; < 13
record section losses as findings. Q14b is a retest of the E2 Q14
password-storage miss — score it honestly and note the outcome in the
valuation.
