# Quick Notes — running keep-list

Requested-to-remember items and confirmed traps from paper valuations.
One line of trap, one line of truth. Re-read before any paper or interview.
(Future "add this to notes" requests append here.)

## Java

- **`list.remove(10)` on `List<Integer>`** → overload resolution picks
  `remove(int index)`, NOT `remove(Object)` → IndexOutOfBounds on short
  lists. Remove the value: `list.remove(Integer.valueOf(10))`. *(requested, M1 Q3)*
- **Integer cache:** autoboxing caches −128..127 → `Integer a=127, b=127;
  a==b` is TRUE; `500==500` boxed is FALSE. Never `==` on wrappers. *(M1 Q4)*
- **ArrayList grows ~1.5×; HashMap doubles** (at load factor 0.75; buckets
  ≥8 treeify to red-black trees). Don't swap the constants. *(E4 Q1, M1 Q2)*
- **Loop string concatenation** creates ordinary heap objects (not pooled
  literals) and is O(n²) from copying → StringBuilder. *(E1 Q4)*
- **`OutOfMemoryError` is an Error, not Exception.** StackOverflowError is
  not an OOM kind. *(E3 Q5, M5 Q6)*
- **volatile = visibility + ordering, NEVER atomicity.** `volatile int
  counter; counter++` is NOT thread-safe (read-modify-write). Flag =`
  volatile` OK; counter = AtomicInteger. *(E5 Q5, M1 Q5 — missed twice)*
- **Concurrent collections make single ops atomic, not compound ones.**
  containsKey-then-put is a race → `computeIfAbsent`. *(M1 Q6)*
- **Threads share the HEAP; each owns its STACK.** *(E1 Q5 → fixed E3)*

## Spring / JPA

- **The proxy model (learn once, unlocks everything):** @Transactional/
  @Cacheable work via a proxy wrapping the bean; `this.method()` bypasses
  it → annotations on self-called methods silently ignored (REQUIRES_NEW
  included). Fix: separate bean or self-injection. *(M1 Q7/Q8 — 0/2)*
- **Checked exceptions do NOT roll back @Transactional by default** —
  only unchecked. `rollbackFor = Exception.class`. *(M-paper key, E-tier)*
- **Fetch defaults:** @OneToMany/@ManyToMany → LAZY; @ManyToOne/@OneToOne
  → EAGER. *(E4 Q8)*

## SQL / DB

- **`WHERE x = NULL` returns zero rows silently** (no error) → `IS NULL`. *(E4 Q9)*
- **Alias not visible in HAVING** (Postgres/standard) → repeat the
  aggregate: `HAVING COUNT(*) > 10`. *(E2 Q10)*
- **"Total/count per X exceeding N" in words = SUM/COUNT + GROUP BY +
  HAVING** — recognize aggregation without being told. *(code session E5 Q10)*
- **Leftmost-prefix rule:** index `(a, b)` serves `a=`, `a= AND b`, `a=
  AND b-range` — NOT `b` alone. B-trees are sorted, not hashed. *(M1 Q10)*
- **ACID disambiguator:** other txn watching → Isolation; post-commit
  crash → Durability; mid-txn crash, no halves → Atomicity; invariants →
  Consistency. *(E4/E5 — still being drilled)*

## Networking / API

- **Many Java HTTP clients default to NO timeouts (infinite)** — always
  set connect + read. *(M1 Q12)*
- **TCP = SYN → SYN-ACK → ACK; TLS = cert chain proves server, then
  symmetric session keys.** Two sentences, always available. *(M1 Q11)*
- **CORS is enforced by the BROWSER** (server only declares policy);
  curl ignores it; it is not server access control. *(E5 Q14)*
- **WebSocket** (Upgrade handshake, bidirectional) ≠ **SSE** (server→client
  stream) ≠ **webhook** (server-to-server HTTP callback). *(M5 Q11)*
- **401 = unauthenticated, 403 = unauthorized.** *(solid since E1 — keep)*

## Messaging / Caching

- **Consumers down → messages WAIT in the broker (durability). DLQ is only
  for delivered-and-repeatedly-FAILED-processing.** *(E3/E4/E5 — 3× miss)*
- **At-most-once = ack before processing; at-least-once = ack after (the
  practical default) → consumer must be IDEMPOTENT; exactly-once =
  at-least-once + idempotency.** *(M1 Q15)*
- **Cache-aside writes: DELETE the key, don't update it in place**
  (concurrent-writer stale-set race). *(M1 Q16 / primer-3 §1)*

## Cloud / Ops

- **IAM roles = temporary auto-rotated credentials from the platform** —
  the point is no static secrets, not finer granularity. *(M1 Q19)*
- **Liveness → orchestrator restarts; readiness → LB routes.** DB outage
  in liveness = restart storm of healthy pods. *(M1 Q20)*
- **`top` → find; `kill PID` = SIGTERM (polite); `kill -9` = SIGKILL.** *(E3 Q12)*
- **Containers share the host kernel** — an image is layered filesystem,
  not "an OS copy." *(E1 Q20)*

## Process (costs marks every paper)

- **Tick every clause of the question** (~10+ occurrences of partial
  answers on multi-part questions).
- **Scan the answer file for placeholders before submitting.**
- **Code answers must be compiled/run first**; mark any name lookups.