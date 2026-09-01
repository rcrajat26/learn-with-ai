# Primer #3 — Cache-Aside · Test Doubles · Keyset Pagination · Delivery Semantics · Clock

The M1 blanks, chaptered (two were explicit chapter requests). ~75 minutes.
Retests: cache-aside → M2 Q16-adjacent + M3 Q15; test doubles → M2 Q17,
M3 Q17; pagination → M4 Q9-adjacent, M3 Q9; delivery semantics → M3 Q15;
Clock → M4 Q17 (code).

## §1 — Cache-aside (the pattern you already half-use)

Your E2 TTL answer already described the read path — this just names and
completes it.

**Read path:** try cache → HIT: return it → MISS: load from DB → put into
cache with TTL → return.
**Write path:** update the DB, then **DELETE** the cache key. Next read
misses and repopulates fresh.

**Why delete, not update-in-place?** Two writers racing:
```
W1 updates DB to A          W2 updates DB to B (final truth = B)
W2 writes cache = B         W1 writes cache = A   ← stale A cached "forever"
```
Set-operations can interleave in the wrong order; delete-then-repopulate
converges because the next reader fetches current DB truth. TTL remains
the backstop for the small window where a reader repopulates old data.

Name the cousins once: **write-through** (write cache+DB together),
**write-behind** (write cache, flush to DB async — fast, risky). Cache-aside
is the default because the cache can die without losing writes.

## §2 — Test doubles: mock vs stub vs fake, and the decision rule

- **Stub:** returns canned answers. "When `findById(42)` → this user."
  You use it to *arrange state*.
- **Mock:** a stub that also **verifies interactions** — "assert
  `save()` was called with X." You use it when the interaction IS the
  behavior (an email got sent).
- **Fake:** a real, working, lightweight implementation — an in-memory
  repository backed by a HashMap. Behaves properly, no verification API.

(Mockito blurs stub/mock into one object — `when()` = stubbing,
`verify()` = mocking. The taxonomy still matters for *deciding*.)

**The decision rule, applied to M1 Q17's service:**
- (a) repository interface → **mock/stub it** — a boundary you own; you're
  testing the service, not the DB.
- (b) third-party HTTP client → **don't mock it directly** — you don't own
  that interface; wrap it in your own thin interface and mock the wrapper
  ("don't mock what you don't own" — their API changes, your mocks lie).
- (c) pure `TaxCalculator` → **use the real thing.** It's fast,
  deterministic logic; mocking it welds the test to implementation and
  verifies nothing.

One-line rule: **mock boundaries you own, wrap boundaries you don't,
never mock pure logic.**

## §3 — Keyset (cursor) pagination, quick form

**Why OFFSET dies at depth:** `LIMIT 20 OFFSET 1000000` walks and DISCARDS
a million rows every page — the DB can't "jump," offset = count-and-throw-
away. And under concurrent inserts, rows shift between pages (skips/dupes).

**Keyset:** remember where the last page ended and seek there directly:
```sql
SELECT * FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
The composite index on `(created_at, id)` lets the DB seek straight to the
cursor position — constant-ish cost at ANY depth; `id` breaks timestamp
ties so the order is total and the cursor unambiguous. API shape: response
carries `items` + opaque `next_cursor` (encodes that pair) + `has_more`.
Trade-off: no jump-to-page-50; that's almost never a real requirement.

## §4 — Delivery semantics: taxonomy in four lines

Defined by WHERE the ack sits relative to processing:
- **At-most-once:** ack/commit BEFORE processing → crash mid-work loses
  the message. (Metrics, telemetry — losing one is fine.)
- **At-least-once:** ack AFTER processing → crash between work and ack
  causes redelivery → duplicates. **The practical default.**
- **Exactly-once:** marketing, unless qualified — the broker and your DB
  are two systems; the achievable thing is **at-least-once delivery +
  idempotent consumer** (unique constraint on event id, same transaction
  as the business write) = exactly-once *effect*.
- Obligation the default places on YOU: every consumer must tolerate
  seeing the same message twice. (Connects to primer-2 §2's lifecycle.)

## §5 — Clock injection, one page

**The bug class:** logic calling `LocalDate.now()` internally is
untestable at boundaries — the anniversary/expiry/month-end branch only
runs when the calendar cooperates; tests written today silently skip it,
and it fails in prod on the boundary date.

**The fix — time is a dependency, inject it:**
```java
public class SubscriptionService {
    private final Clock clock;                       // injected
    public SubscriptionService(Clock clock) { this.clock = clock; }
    boolean isExpired(Subscription s) {
        return s.expiresOn().isBefore(LocalDate.now(clock));   // now(clock)!
    }
}
// prod wiring:  new SubscriptionService(Clock.systemUTC())
// test:         Clock fixed = Clock.fixed(Instant.parse("2026-03-01T00:00:00Z"),
//                                         ZoneOffset.UTC);
//               → test the day before, the day of, and the day after. Deterministically.
```
Same trick for randomness (`Supplier<UUID>`, seeded `Random`). If you
can't control an input, you can't test the branch it selects.

## Self-check (before M2)

1. Cache-aside write path — why delete beats update, with the two-writer race.
2. The mock/wrap/real rule for repository / third-party client / pure logic.
3. Write the keyset WHERE clause from memory; why does it need the id column?
4. Ack-position definitions of the three semantics + the consumer obligation.
5. Sketch Clock injection: constructor, `now(clock)`, `Clock.fixed` test.