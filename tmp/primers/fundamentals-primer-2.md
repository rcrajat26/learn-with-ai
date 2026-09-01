# Fundamentals Primer #2 — ACID · Broker Lifecycle · CORS · volatile

Targeted at the open easy-tier misses (E4 Q10, E5 Q10b/Q15/Q14/Q5, plus the
E3/E4 broker slips). ~90 minutes. Same rule as primer #1: after each part,
close the file and explain it aloud. Retests: M3 Q10 (isolation), M1 Q15 +
M3 Q15 (broker), M2 Q14 (CORS), M1 Q5 (volatile).

## Part 1 — ACID, anchored to one story

One transaction: **transfer ₹500 from A to B** = `debit A; credit B; commit`.

**Atomicity — "all or none."**
Crash after the debit, before the credit? On recovery the debit is rolled
back. There is never a committed half-transfer. *You had this right in E5.*

**Isolation — "concurrent transactions don't see each other's middles."**
A report running DURING the transfer never sees A debited but B not yet
credited — it sees the state before, or after, never between.
→ This was E5's "report never sees debited-but-not-credited" scenario.
**Any question about what another concurrently-running transaction can
observe = Isolation.**

**Durability — "committed means committed."**
The instant the user sees "transfer confirmed," the change is on disk
(write-ahead log). Power failure one millisecond later? Still there after
restart. **Any question about surviving crashes/power-loss AFTER commit =
Durability.**

**Consistency — "valid state to valid state."**
Constraints and invariants hold before and after every transaction:
`balance >= 0`, total money across A+B unchanged. Consistency is about
RULES ON THE DATA, not about who sees what and not about time.

### The disambiguator you keep needing

- Mentions **another transaction watching / intermediate states** → Isolation.
- Mentions **crash or power failure AFTER commit** → Durability.
- Mentions **crash MID-transaction, nothing half-done** → Atomicity.
- Mentions **constraints/invariants/no-money-created** → Consistency.

Your E4→E5 confusion was mapping "report doesn't see the middle" to
Consistency and "survives power failure" to Isolation. Run the four
scenarios above out loud until the mapping is reflexive.

## Part 2 — What a broker actually does with a message

The model you've answered with three times: "broker retries, then DLQs."
That model is wrong in a specific way. Here is the real lifecycle:

```
Producer ──publish──► [ QUEUE stores message durably ]
                              │
              consumer ALIVE? ├── no ──► message just WAITS.
                              │          Hours, days — up to retention.
                              │          No retries. No DLQ. No failure
                              │          has happened yet. When consumers
                              │          return, they drain the backlog.
                              ▼
                      consumer receives it
                              │
                 processing SUCCEEDS ──► consumer acks → message deleted
                              │
                 processing FAILS/crashes before ack
                              │
                              ▼
                  broker makes it visible AGAIN (redelivery)
                  ... after N failed DELIVERY ATTEMPTS ...
                              ▼
                  moved to the DLQ (+ alert; inspect, fix, replay)
```

The two facts to internalize:

1. **Consumers down ≠ failure.** Nothing is "attempted," so nothing
   retries and nothing dead-letters. Messages accumulate — that BUFFERING
   is the reason queues exist (contrast: a plain HTTP call to a down
   service exhausts its retries in seconds and the data is gone).
2. **The DLQ is for poison messages** — ones that were DELIVERED and
   repeatedly FAILED PROCESSING (malformed payload, bug, persistent
   downstream error). Path: deliver → fail → redeliver → ... → N attempts
   exhausted → DLQ.

One sentence version for interviews: *"If consumers are down, messages
wait in the queue; the DLQ only receives messages that were delivered and
failed processing N times."*

## Part 3 — CORS in one page

**The default rule (same-origin policy):** a browser running a page from
`app.example.com` will not let that page's JavaScript READ responses from
`api.other.com`. Origin = scheme + host + port.

**CORS is the server saying "allow it":** the API responds with
`Access-Control-Allow-Origin: https://app.example.com` (plus
`-Allow-Methods`, `-Allow-Headers`). For non-simple requests (JSON
content-type, Authorization header), the browser first sends an `OPTIONS`
**preflight** asking permission, then the real request.

**Who enforces it: the BROWSER.** The server only *declares* policy in
headers; the browser reads them and decides whether to hand the response
to the page's JS. That's why your curl intuition was right for the wrong
reason: **curl ignores CORS entirely** — it's not a browser and has no
user to protect. CORS protects browser USERS (their cookies/sessions being
exploited by malicious pages); it is NOT server access control. Server
protection = authentication/authorization, always.

Misconfigured-CORS symptom you'll meet in real work: the SPA gets
"blocked by CORS policy" in the console while curl to the same endpoint
works fine — now you know exactly why.

## Part 4 — volatile vs atomicity (primer #1 §3, sharpened)

`volatile` gives **visibility + ordering**: a write is immediately visible
to other threads' reads; no caching-stale-values, no reordering around it.

`volatile` does NOT give **atomicity**. `counter++` compiles to
read → add → write. Two threads can both read 5 and both write 6 — a lost
update — and volatile does nothing about it, because each individual step
was perfectly visible; the INTERLEAVING is the problem.

| Use case | volatile enough? |
|---|---|
| `volatile boolean running` — one thread writes, others poll | ✅ yes |
| `volatile int counter` with `counter++` from many threads | ❌ no — `AtomicInteger` |
| Publishing an immutable config object reference | ✅ yes |
| Any read-modify-write or check-then-act | ❌ no — atomic classes or locks |

Litmus test before answering "is X thread-safe": *does the operation
read a value and then write something derived from it?* If yes, visibility
alone can never save it.

## Self-check (before M1)

1. Map all four transfer scenarios to their ACID property, out loud.
2. "Producer publishes for an hour while consumers are down — what
   happens, and when does a DLQ get involved?" — one-sentence answer.
3. Who enforces CORS, and does it stop curl? Why is that OK?
4. Is `volatile int counter; counter++` thread-safe? What is, instead?