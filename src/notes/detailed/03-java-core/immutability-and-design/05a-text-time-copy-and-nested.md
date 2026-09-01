# 03 Java Core — Which construct: text, time, copying, nested types, and the consolidated table — INTERMEDIATE (§2.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Which construct do I reach for](05-which-construct.md) · Next: [Numbers, BigDecimal, and money](../numbers-and-money/02-numbers-and-money.md)

---

[`05-which-construct.md`](05-which-construct.md) settled the first five decisions of §2.15 — what to reach for when you are modelling a value, a contract, a constant, an error signal, and a number — and embedded **D-089**, the decision tree for the whole of §2.15. This file settles the remaining four decisions and then collapses all nine, plus four more that Part 2 settled elsewhere, into one card. The shape of every section is the same as the previous file's: a table whose columns actually discriminate, a decision rule you can apply to a diff in front of you, and the QuizStakes instance for every leaf of that rule. It is deliberately not a summary of the mechanisms — the mechanism files are named at each point, and the job here is the *choice* those mechanisms imply.

Everything measured below ran on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, single-file source launch, output pasted as printed. Costs quoted in nanoseconds are quoted from [`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md) and not re-derived here.

---

## 1. Text: `String` vs `StringBuilder` vs `char[]` vs `byte[]` (2.15.6)

`[X-REF 13]` `[BUILD]` `[VERSION-TRAP]`

Four representations of the same bytes, and the question that picks between them is not "which is fastest" — it is **what has to be true of those bytes after you are done with them.** If nothing in particular has to be true, you want `String`, because immutability, `equals`, `hashCode`, pooling and every library signature in the platform come for free. If the bytes are being assembled a piece at a time and only the finished result matters, you want `StringBuilder`, because a `String` per intermediate step is the one thing immutability genuinely costs. If the bytes must be **gone from memory** at a known instant, you want `char[]`, because it is the only one of the four you can overwrite. And if they are not text at all — if they are a payload whose encoding is somebody else's decision — you want `byte[]`, because the moment you decode them you have made that decision on their behalf.

### Why it exists

Because `String`'s immutability, which is the reason it is safe to share across the 14k steady concurrent sessions without a lock, is exactly the reason it is unsafe for a credential: an object nobody can change is also an object *you* cannot change, including to erase it. The JDK's own API surface admits this split directly — `java.io.Console.readPassword()` returns `char[]`, while `Scanner.nextLine()` returns `String`, and that difference in return type is a security decision made in the signature, not a stylistic one. `byte[]` exists as a separate answer for the same structural reason in the other direction: `String` in Java has no charset, so every conversion into or out of it is a lossy-by-default decode against *some* charset, and a payload whose bytes are load-bearing cannot survive a guess.

### When to reach for it, and when not

| Representation | Mutable | Erasable | Interned / pooled | Cost to build up incrementally | QuizStakes case |
|---|---|---|---|---|---|
| `String` | No — the backing `byte[]` is private and never handed out | **No.** No API zeroes it; you can only drop the reference and wait for GC | Yes — literals are interned automatically, `intern()` on demand (measured 62–65 ns) | One `String` + one `byte[]` **per step**; quadratic in a loop | `StatusCode.variant()`, `IdempotencyKey.value()`, a coupon code, every log line |
| `StringBuilder` | Yes, by design | In principle (`setLength(0)` does *not* zero; the old chars stay in the buffer) | No | Amortised O(1) per append, one array growth doubling | Assembling a PSP payout-file line from a `PaymentRun`'s entries |
| `char[]` | Yes | **Yes** — `Arrays.fill(pw, '\0')`, at a moment you choose | No | Manual; you own the sizing | A supplied credential inside `JwtService` / login, and nothing else |
| `byte[]` | Yes | Yes — same `Arrays.fill` | No | Manual, or via `ByteArrayOutputStream` | A PSP callback body whose HMAC signature is computed over the raw bytes |

The rule, applied in this order: **is it a credential? `char[]`. Is it an un-decoded payload? `byte[]`. Is it being built in a loop? `StringBuilder`. Otherwise `String`** — and "otherwise" is the overwhelming majority of QuizStakes text, which is why the other three read as exceptions and should.

### How it works

**`char[]` for a credential — the `[X-REF 13]` mechanism.** A `String`'s characters live in a `private final byte[] value` that is never exposed and never overwritten, so there is no operation, anywhere in the platform, that turns a live `String`'s contents into zeroes. A password read into a `String` therefore stays in the heap — visible in full plaintext in any heap dump taken by an operator, a JFR recording, or a crash — until the collector happens to reclaim it, and you have no way to make that sooner. Worse, if the value was ever a literal or passed through `intern()`, it is additionally reachable from the string table (`StringTableSize = 65536` on this build) and lives for the JVM's lifetime by design. A `char[]`, being an ordinary mutable array, can be overwritten with `Arrays.fill(pw, '\0')` in a `finally` block the instant the comparison completes, which shrinks the plaintext's window from "until GC, at least" to "the duration of one method call". Guide 13 owns credential handling end to end — hashing parameters, transport, storage; this paragraph is the part that belongs to the *type* decision. `../strings/03-internals-string.md` owns the `byte[]`-plus-`coder` layout, and `../strings/01b-the-string-pool.md` owns interning and the string table.

**The honest limit, because the folklore overstates this one badly.** The `char[]` guarantee is **best-effort, not absolute**, and a candidate who states it as absolute is wrong in a way a good interviewer will push on. Three reasons: the JIT may have copied the array's contents into registers or a stack slot that your `Arrays.fill` does not reach; a copying collector may have moved the array during its lifetime and left a stale, un-zeroed copy in the vacated region; and, most commonly of all, the bytes may already have been a `String` on the way in. That last one is the decisive practical caveat — an HTTP form parameter or a JSON body field has been decoded into a `String` by the servlet container or Jackson long before your code sees it, and calling `.toCharArray()` at that point erases nothing, because the original `String` is still on the heap. So `char[]` is the right **default type for a credential parameter** — it keeps the plaintext out of the pool, gives you a real erase point, and documents the intent in the signature — and it is *not* a claim that the plaintext has been erased.

**`byte[]` versus `String` at a boundary.** Encoding in Java happens at exactly two places: `String.getBytes(Charset)` on the way out and `new String(byte[], Charset)` on the way in. A `String` itself has no charset — it is UTF-16 code units, or Latin-1 code units under compact strings (`CompactStrings = true`), which is why a Latin-1-only password is stored one byte per character inside the `String`'s own `byte[]`. `[VERSION-TRAP]` The no-argument forms, `getBytes()` and `new String(byte[])`, use the JVM's default charset, and that is **UTF-8 unconditionally from Java 18 onward under JEP 400** — confirmed on this build, which printed `default charset = UTF-8` — where on **Java 17 and earlier it was derived from the host locale** and could be `windows-1252`, `US-ASCII` or UTF-8 for the same jar on three different machines. Both halves matter operationally: a JDK 17 service and a JDK 21 service running the same code disagree about what `getBytes()` produces. `../strings/02b-text-and-encoding.md` owns encoding in full, including the `-Dfile.encoding=COMPAT` escape hatch.

The consequence for the decision: a PSP callback whose HMAC signature is computed by the PSP over the *raw request bytes* must stay `byte[]` until the signature verifies, because a round trip through a `String` with a charset that is not the sender's changes the bytes. Measured on this build for the four characters of `café`:

```
utf8  = [99, 97, 102, -61, -87]
l1    = [99, 97, 102, -23]
```

Five bytes against four, for the same four characters. Any signature computed over one and verified against the other fails, and the failure looks like a wrong secret rather than a wrong charset — which is why this bug survives so long in production.

**`StringBuilder`, briefly, because it is over-recommended.** It is the answer for genuinely incremental construction — a loop, a conditional append, a recursive walk — and nothing else. For joining a known collection, `String.join`, `StringJoiner` and `Collectors.joining` express the intent better and do the same work. `[VERSION-TRAP]` And a `+` chain inside a *single expression* has compiled to an `invokedynamic` call against `StringConcatFactory` since **Java 9**, which builds a right-sized buffer in one pass and is usually *faster* than a hand-written `StringBuilder`; before Java 9 `javac` desugared it to an explicit `StringBuilder` chain, which is where the "always use `StringBuilder`" advice came from and why it is now backwards for the single-expression case. `../strings/02-performance-and-text.md` owns the performance chapter and `../strings/04b-internals-indified-concat.md` the indified-concat mechanism.

### Diagram

No diagram of its own — this file has none, and the decision tree covering all of §2.15 is **D-089**, embedded in [`05-which-construct.md`](05-which-construct.md); refer to it rather than expecting a second copy here. The adjacent picture for this concept is **D-067**, code unit versus code point versus grapheme cluster, owned by [`../strings/02b-text-and-encoding.md`](../strings/02b-text-and-encoding.md), which is the diagram that explains why "length" has three different answers for the same text.

### A concrete example

A QuizStakes credential check, complete, with the erase in the `finally` and the two other erases most implementations forget:

```java
public final class ClientCredentials {

    private static final int PBKDF2_ITERATIONS = 210_000;
    private static final int PBKDF2_KEY_BITS = 256;

    private final byte[] salt;
    private final byte[] expectedHash;

    public ClientCredentials(byte[] salt, byte[] expectedHash) {
        this.salt = Arrays.copyOf(salt, salt.length);
        this.expectedHash = Arrays.copyOf(expectedHash, expectedHash.length);
    }

    /**
     * @param supplied the plaintext credential. Erased by this method before it
     *     returns, so the caller must not reuse the array afterwards.
     */
    public boolean matches(char[] supplied) {
        PBEKeySpec spec = new PBEKeySpec(supplied, salt, PBKDF2_ITERATIONS, PBKDF2_KEY_BITS);
        byte[] actual = null;
        try {
            SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
            actual = factory.generateSecret(spec).getEncoded();
            return MessageDigest.isEqual(expectedHash, actual);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("PBKDF2WithHmacSHA256 unavailable", e);
        } finally {
            spec.clearPassword();
            if (actual != null) {
                Arrays.fill(actual, (byte) 0);
            }
            Arrays.fill(supplied, '\0');
        }
    }
}
```

Three erases, not one. `spec.clearPassword()` is needed because `PBEKeySpec`'s constructor makes its own internal copy of the `char[]` — erasing only `supplied` would leave that copy live. `Arrays.fill(actual, (byte) 0)` clears the derived key, which is as sensitive as the password for replay purposes. `Arrays.fill(supplied, '\0')` is the erase people write, and it is the least of the three. `MessageDigest.isEqual` rather than `Arrays.equals` because the comparison must not short-circuit on the first differing byte; that is guide 13's territory and named here only so the code is not quietly wrong.

The erase, measured, printed as code points so the zeroes are visible without emitting control bytes:

```
before = U+0053 U+0075 U+0070 U+0033 U+0072 U+0053 U+0065 U+0063 U+0072 U+0065 U+0074 U+0021
length check passes = true
after  = U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000 U+0000
interned identical literal is the same object = true
```

The last line is the counterpart fact: the same credential written as a `String` literal is `==` to another occurrence of that literal, because both resolve to the one pooled instance — which is the pool holding plaintext for the process lifetime, and the reason the literal form is worse than "just not erasable".

### The gotcha

**Pitfall:** believing `char[]` gives you erasure. The wrong belief is that switching a login endpoint's parameter type from `String` to `char[]` removes the plaintext from the heap. The symptom is a heap dump taken during an incident that still contains every password submitted in the last GC cycle, because the framework decoded the request body into a `String` before dispatch and `.toCharArray()` merely made a second copy of something already interned-or-not-but-certainly-live. The fix is to push `char[]` as far up the boundary as the framework allows — `Console.readPassword()` where there is a console, a streaming JSON parser configured to hand out a `char[]` where there is not — and to be explicit in review that below that point `char[]` is intent and hygiene rather than a guarantee.

> **Definition.** `String` is the default because immutability buys sharing, pooling and free `equals`/`hashCode`; `StringBuilder` is for incremental construction only, and loses to `invokedynamic`-compiled `+` inside one expression since Java 9; `char[]` is the right declared type for a credential because it is the only one of the four you can overwrite at a chosen instant, best-effort; and `byte[]` is for bytes whose charset is not yours to choose, since encoding happens only at `getBytes(Charset)` and `new String(bytes, Charset)` and the no-arg forms are UTF-8 from Java 18 and platform-dependent before it.

---

## 2. Time: `Instant` vs `LocalDate` vs `ZonedDateTime` vs epoch millis (2.15.7)

`[TRAP]` `[NUM]`

Nearly every `java.time` question dissolves once you notice that **three genuinely different questions are being asked, and they want three different types.** "When did this happen, as a point on the universal timeline?" is `Instant`. "What calendar day is this, in nobody's particular zone?" is `LocalDate`. "What wall-clock reading will a human in a named zone see, including that zone's daylight-saving rules?" is `ZonedDateTime`. Epoch millis is not a fourth answer to a fourth question; it is a *serialization format* for the first one, and the entire class of bugs in this leaf comes from treating it as a type.

### Why it exists

Because `java.util.Date` answered all three questions with one mutable object that was secretly an epoch-millis wrapper with a `toString` that lied about a zone, and `Calendar` answered them with a mutable object whose field arithmetic silently rolled. `java.time`, shipped in Java 8, split them apart on purpose: the type you pick now *states which question you are answering*, so a reviewer can see a category error in a field declaration rather than in a production incident three months later.

### When to reach for it, and when not

| Type | What it identifies | Carries a zone | Arithmetic respects DST | Resolution | QuizStakes field |
|---|---|---|---|---|---|
| `Instant` | A point on the UTC timeline | No — it *is* UTC, which is not the same as carrying a zone | Not applicable; there is no DST on the timeline | Nanoseconds | `LedgerEntry.postedAt` — a ledger entry happened at a moment, and the ledger is the source of truth for money |
| `LocalDate` | A calendar day, in no zone | No | Not applicable | One day | A client's date of birth, and the coupon's 14-day validity window's end date |
| `ZonedDateTime` | A wall-clock reading in a named zone, plus that zone's rules | Yes, a `ZoneId` with its full rule set | **Yes** — this is the only one of the four that does | Nanoseconds | A `PaymentRun`'s operator sign-off window — the banking partner's four windows a day are wall-clock times |
| `long` epoch millis | Nothing, by itself — it is an encoding of an `Instant` | No | No | Milliseconds; **cannot round-trip an `Instant`** | Only on the wire and in a legacy column, converted at the boundary |

The rule: **`Instant` for anything that happened, `LocalDate` for anything on a calendar, `ZonedDateTime` only where a human's wall clock is part of the requirement, and epoch millis nowhere inside the domain.** The `ZonedDateTime` restriction is the one people get wrong in the generous direction — it looks like the most informative type, so it becomes the default, and then every comparison between two of them has to reason about two zones' rule sets when the question was only ever "which came first".

The date-of-birth case is worth naming as the classic failure it is: stored as an `Instant` (or worse, epoch millis), a date of birth acquires a time-of-day of midnight in whichever zone did the conversion, and a later conversion in a zone one hour behind renders it as the previous day. On a platform whose `AO-119 AGE_INELIGIBLE` gate is a date comparison, an off-by-one-day is an off-by-one-*decision* for anyone registering on their eighteenth birthday. A `LocalDate` has no time and no zone, so there is nothing for a conversion to shift.

### How it works

**`Duration` versus `Period` — the sharpest edge in this leaf.** `Duration` is an amount of *elapsed time*, held as seconds plus nanos: `Duration.ofDays(1)` is exactly 86,400 seconds, always. `Period` is an amount of *calendar time*, held as years, months and days: `Period.ofDays(1)` means "the same wall-clock reading, one calendar day later". On a `ZonedDateTime` those give different answers across a DST transition, and the divergence is not subtle. Measured on JDK 21.0.7, starting from `2026-03-28T23:30` in `Europe/London` — the night the UK clocks go forward at 01:00 — and adding one day each way:

```
base          = 2026-03-28T23:30Z[Europe/London]
+Duration 1d  = 2026-03-30T00:30+01:00[Europe/London]
+Period   1d  = 2026-03-29T23:30+01:00[Europe/London]
+1 day zone rules skipped hour? offset base=Z after=+01:00
```

`Duration.ofDays(1)` added 86,400 real seconds and landed on **2026-03-30T00:30**, because one of those hours was skipped by the transition, so 86,400 seconds of elapsed time carries the wall clock 25 hours forward. `Period.ofDays(1)` landed on **2026-03-29T23:30** — the same wall-clock reading, one calendar day later — which is only 82,800 real seconds away. Both are correct; they answer different questions. **Pitfall:** using `Duration.ofDays` for a business rule expressed in days. The bonus's 30-day expiry from grant, and the coupon's 14-day validity from registration, are calendar rules — an operator asked "is it still within 14 days" means calendar days — so they are `Period`, or better still `LocalDate.plusDays` on a `LocalDate`, and `Duration.ofDays(14)` will be wrong by an hour twice a year in a way that only bites the grants issued in the hour either side of a transition. `../date-and-time/02-date-and-time.md` owns `java.time` in full and carries the pictures: D-076 and D-077 for the type map and the DST gap/overlap, and D-078 for `Duration` versus `Period`.

**Why epoch millis is a storage format and not a type.** Three defects, each independently disqualifying. It has no zone, so it cannot express the `ZonedDateTime` question at all. It has millisecond resolution, so it cannot round-trip an `Instant` — measured on this build:

```
instant       = 2026-03-20T09:46:40.123456789Z
roundtrip ms  = 2026-03-20T09:46:40.123Z
```

456,789 nanoseconds destroyed by a round trip through `toEpochMilli()`. That is real data loss, and on a ledger where ordering within a millisecond can matter at the 13,600/sec peak write rate, it is data loss with consequences. And it has no type safety: `long postedAt` and `long clientId` are the same type to the compiler, so a transposed argument list is a runtime mystery rather than a compile error — which is exactly the argument `05-which-construct.md`'s value-type leaf makes for `ClientId` over `UUID`, applied to time. The rule: **convert at the boundary, in one place, and keep `Instant` everywhere inside.**

**The three clock reads, priced.** Quoted from [`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md), measured on this build, not re-derived here: `Instant.now()` **19.79–20.30 ns**, `System.currentTimeMillis()` **13.55–13.70 ns**, `System.nanoTime()` **9.18–9.70 ns**. All three leave the JVM for an OS clock, which is why none of them is foldable or hoistable, and the ordering surprises people — `nanoTime` is the *cheapest*, against folklore that says it is the expensive one, and `Instant.now()` is the dearest because it adds a wrapper allocation on top of a `currentTimeMillis`-class call. At one timestamp per ledger entry and 13,600 entries/sec at peak, `Instant.now()` costs 13,600 × 20 ns ≈ **272 microseconds/sec of CPU**, or 0.027% of one core — which is the number to bring when somebody proposes caching timestamps, because it settles the argument in the direction of not doing that.

**`System.nanoTime()` is not a wall clock.** It has no defined epoch, its absolute value is meaningless, and it is only valid for *differences* measured within one JVM. Using it as a `LedgerEntry.postedAt` produces timestamps that are monotonic, unrelated to any calendar, and incomparable across processes. `../language-substrate/02-packages-modules-annotations.md` covers the distinction and carries D-062.

**Injecting a `Clock`.** Never call `Instant.now()` inside domain logic — take a `java.time.Clock` as a dependency and call `Instant.now(clock)`, so a test can supply `Clock.fixed(...)` and assert on the 30-day bonus expiry without sleeping or freezing the system clock. Guide 16 owns testing; the type decision is that `Clock` is a collaborator, not a utility. How the timestamp lands in the database — `TIMESTAMP WITH TIME ZONE` against a `NUMERIC` epoch column — is guide 09's.

### Diagram

No diagram of its own in this file; **D-089** in [`05-which-construct.md`](05-which-construct.md) is the decision tree for all of §2.15, including this leaf. The adjacent pictures live in [`../date-and-time/02-date-and-time.md`](../date-and-time/02-date-and-time.md), which carries D-076 and D-077 for the `java.time` type map and the DST gap and overlap, and D-078 for `Duration` against `Period`.

### A concrete example

The three types side by side on one aggregate, with the `Clock` injected and the epoch-millis conversion confined to a single boundary method:

```java
public record PaymentRun(
        UUID runId,
        LocalDate businessDate,
        ZonedDateTime signOffWindowStart,
        Instant submittedAt,
        List<WithdrawalTransaction> entries) {

    public PaymentRun {
        entries = List.copyOf(entries);
    }

    /** The banking partner's four windows a day are wall-clock times in a named zone. */
    public static PaymentRun openFor(LocalDate businessDate,
                                     ZoneId partnerZone,
                                     LocalTime windowStart,
                                     Clock clock) {
        return new PaymentRun(
                UUID.randomUUID(),
                businessDate,
                ZonedDateTime.of(businessDate, windowStart, partnerZone),
                Instant.now(clock),
                List.of());
    }

    /** True once the partner's wall clock has reached the window, whatever the offset is that day. */
    public boolean windowOpen(Clock clock) {
        return !Instant.now(clock).isBefore(signOffWindowStart.toInstant());
    }

    /** The single boundary where epoch millis is allowed to exist. */
    public long submittedAtEpochMilli() {
        return submittedAt.toEpochMilli();
    }
}
```

`businessDate` is a `LocalDate` because "which day's batch is this" has no time and no zone. `signOffWindowStart` is a `ZonedDateTime` because the requirement is stated in the partner's wall clock. `submittedAt` is an `Instant` because it is a moment that happened. `submittedAtEpochMilli()` is the one method that produces the lossy form, named so a reviewer can see every place it is called.

### The gotcha

**Pitfall:** comparing a `ZonedDateTime` to a `ZonedDateTime` with `equals` when you meant "the same moment". `ZonedDateTime.equals` compares the local date-time, the offset **and** the zone, so `2026-06-01T12:00+01:00[Europe/London]` and `2026-06-01T11:00Z[UTC]` — the same instant — are not equal. The symptom is a deduplication check on a `PaymentRun` sign-off that lets a second sign-off through because the operator's client sent the same moment in a different zone. The fix is to compare instants: `a.toInstant().equals(b.toInstant())`, or `a.isEqual(b)`, which is the method `java.time` provides for exactly this and is the one nobody reaches for because `equals` is right there.

> **Definition.** `Instant` answers "when, on the universal timeline"; `LocalDate` answers "which calendar day, in no zone"; `ZonedDateTime` answers "what wall clock will a human in a named zone read, under that zone's DST rules", and is the only one of the three whose arithmetic is zone-aware; epoch millis answers no question at all — it is a lossy serialization of an `Instant` that discards nanoseconds and carries no type safety, so it belongs at a boundary and nowhere inside the domain.

---

## 3. Copying: view vs shallow copy vs deep copy vs immutable rebuild (2.15.8)

`[TRAP]`

Four operations that all read as "make me another one", and what separates them is **what the copy shares with the original.** A view shares everything and is a window onto the original. A shallow copy shares the *elements* but not the container. A deep copy shares nothing. An immutable rebuild shares whatever was already immutable — which is safe precisely because sharing an immutable object is not sharing mutable state, and that is the observation that makes the whole decision collapse.

### Why it exists

Because Java has no language-level notion of copy depth, so every one of the four is spelled out of the same-looking library calls, and three of them are one character apart in a code review. `Collections.unmodifiableList(itemIds)` and `List.copyOf(itemIds)` differ by nothing visible at the call site except the method name, and they differ completely in whether a later write to `itemIds` is observable through the result.

### When to reach for it, and when not

| Operation | What is shared | Sees later writes to the source | Cost | When it is right |
|---|---|---|---|---|
| **View** (`Collections.unmodifiableList`) | Everything — it wraps the same backing list | **Yes.** This is the aliasing bug | One small wrapper object | Only when the source is provably not retained by anyone else, or when live-ness is the intent |
| **Shallow copy** (`List.copyOf`, `Arrays.copyOf`, a copy constructor) | The elements, by reference; not the container | No | One array of n references; no per-element work | The container is mutable but the elements are not — the common case |
| **Deep copy** | Nothing | No | O(total reachable graph), plus an allocation per node | The elements are mutable too, and you cannot change that |
| **Immutable rebuild** (`withX`, a builder) | Whatever was already immutable | No — there is nothing mutable to see | One object, frequently eliminated entirely | Whenever the type is under your control, which makes it the answer that dissolves the question |

The decision rule is one question asked twice: **is the thing you are copying mutable, and one level down, are its elements mutable?**

- Neither is mutable: no copy is needed at all. Handing out the original reference is correct and free, and a defensive copy here is pure cost. This is the case immutability is *for*.
- The container is mutable, the elements are not: `List.copyOf` is exactly right — an independent snapshot with no per-element work, and it is a no-op that returns the same instance when the argument is already one of the immutable `List.of` implementations.
- The elements are mutable too: only a deep copy is honest, **and the better move is almost always to make the element type immutable instead**, which converts this row into the first row and removes the copy entirely.

The measured version of the view-versus-copy distinction, on the pair the earlier files established, with `itemIds` mutated *after* both are taken:

```
view = [WD-1, WD-2, WD-3] size=3
copy = [WD-1, WD-2] size=2
```

The `unmodifiableList` view rejects `add` through itself and still reports the third element, because the third element was added to the list it wraps. `List.copyOf` does not. [`02-immutability.md`](02-immutability.md) §5 owns that comparison in both directions and [`02a-shallow-deep-and-building-blocks.md`](02a-shallow-deep-and-building-blocks.md) owns the second hop — an immutable list of settable `LedgerEntry` objects, which is where `List.copyOf` stops being sufficient. [`../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`](../objects-equality-and-lifecycle/02-copying-and-composite-equality.md) owns deep-copy mechanics.

### How it works

Two things this decision adds that the mechanism files do not.

**`clone()` is absent from the table on purpose.** It is a shallow copy with a broken contract: `Cloneable` is a marker interface that declares no `clone` method at all, so implementing it does not oblige you to provide one and does not let a caller invoke it through the interface; `Object.clone` is `protected` and `native`, and it copies fields bit-for-bit, which means every reference field in the copy aliases the original's referent. Nothing it does is unavailable from a copy constructor or a `withX` method, and both of those are visible in the source, participate in `final` field initialisation, and work with records. **The rule: never `clone()` an object you wrote; copy defensively out of one you did not.** [`../objects-equality-and-lifecycle/01-basics.md`](../objects-equality-and-lifecycle/01-basics.md) carries **D-036**, the picture of `clone()` being shallow.

**`Arrays.copyOf` is the only defence for an array**, because **no immutable array form exists in Java.** `final long[] amounts` fixes the reference and leaves every slot writable; there is no `Array.of` and no wrapper that makes the elements unwritable. So an array crossing a boundary in either direction needs `Arrays.copyOf(a, a.length)`, per element if the elements are themselves mutable, and the structurally better answer is to not have an array in the API — `List.copyOf`, or a record wrapping the values. [`../arrays/01-basics.md`](../arrays/01-basics.md) owns arrays.

**The immutable rebuild, priced.** A `withX` method or a builder produces a new object that shares only immutable parts, so there is no depth question left to answer — which is the whole reason it is the answer this section closes on rather than a fourth option. The price, quoted from [`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md) and not re-derived: a small object that **escapes** measured **4.394 ns** on this build, and one that does **not** escape measured **0.301–0.559 ns**, at the harness floor, because C2's escape analysis removed the allocation entirely. C2 makes no documented guarantee about when it will do that, so neither figure is a rule — but the direction is the point: a rebuild that stays inside a method is frequently free, and a rebuild that escapes costs single-digit nanoseconds. Against that, a copy on the 13,600/sec peak ledger-write path deserves a measurement rather than a reflex in either direction: 13,600 × 4.4 ns is about 60 microseconds/sec, which is nothing, but the same copy inside a loop over a `PaymentRun`'s entries is a different arithmetic problem and has to be counted rather than assumed.

### Diagram

No diagram of its own in this file; **D-089** in [`05-which-construct.md`](05-which-construct.md) covers the §2.15 decision including this leaf. The adjacent picture is **D-036**, `clone()` being shallow, owned by [`../objects-equality-and-lifecycle/01-basics.md`](../objects-equality-and-lifecycle/01-basics.md).

### A concrete example

The rule applied to one aggregate, with all four cases visible and each one labelled by which row of the table it is:

```java
public final class WithdrawalBatch {

    private final List<String> transactionRefs;   // elements immutable -> shallow copy
    private final long[] amountsMinor;            // array -> Arrays.copyOf, no alternative
    private final Money total;                    // immutable -> share the reference, free

    public WithdrawalBatch(List<String> transactionRefs, long[] amountsMinor, Money total) {
        this.transactionRefs = List.copyOf(transactionRefs);
        this.amountsMinor = Arrays.copyOf(amountsMinor, amountsMinor.length);
        this.total = total;
    }

    /** View row: safe here only because the field is already an immutable list. */
    public List<String> transactionRefs() {
        return transactionRefs;
    }

    /** Array row: copy out as well as in, or the caller writes into our state. */
    public long[] amountsMinor() {
        return Arrays.copyOf(amountsMinor, amountsMinor.length);
    }

    public Money total() {
        return total;
    }

    /** Immutable-rebuild row: no depth question, because nothing shared is mutable. */
    public WithdrawalBatch withTotal(Money newTotal) {
        return new WithdrawalBatch(transactionRefs, amountsMinor, newTotal);
    }
}
```

`transactionRefs()` returns the field directly and is still correct, because the field is a `List.copyOf` result and not a wrapper over something a caller holds — that is the "neither is mutable, no copy needed" row, and it is why getting the constructor right removes work from every getter. `amountsMinor()` cannot do the same, because there is no immutable array to have stored.

### The gotcha

**Pitfall:** reaching for `Collections.unmodifiableList` in a constructor to make a field safe. The wrong belief is that "unmodifiable" and "immutable" are the same word. The symptom is an aggregate whose contents change after construction with no mutator ever called on it, because the caller kept its `ArrayList` and added to it — the view reports the addition, as measured above, and every invariant the constructor validated is now stale. The fix is `List.copyOf` in the constructor and the view only on the way *out*, where the thing being wrapped is a field nobody outside the object holds a second reference to.

> **Definition.** A view shares the original's storage and therefore sees later writes to it; a shallow copy shares the elements but not the container; a deep copy shares nothing and costs the whole reachable graph; and an immutable rebuild shares only what was already immutable, which is why it has no depth to decide — so the decision is the single question "is this mutable, and are its elements mutable", and the best answer to a "yes" on the second half is usually to make the element type immutable rather than to deep-copy it.

---

## 4. Nested type: static nested vs inner vs local vs anonymous vs lambda (2.15.9)

`[TRAP]` `[BYTECODE]`

Five candidates, and the column everybody skips is the one that decides it: **does this thing capture the enclosing instance, and what does that keep alive?** Every other difference — can it be named, can it have two methods, can it be reused — is a syntax question you can answer by looking. Retention is a lifetime question you cannot, and it is the one that shows up as a leak.

### Why it exists

Because a callback needs state, and Java's answer to "where does the state come from" has been rewritten three times: an inner class gets it by holding a pointer back to the object that made it, a local or anonymous class gets it by copying the locals it uses into synthetic fields, and a lambda gets it by having its captures passed as arguments to a synthesized method. Those three mechanisms have three different retention profiles, which is exactly why the five-way choice is not a style preference.

### When to reach for it, and when not

| Kind | Needs an enclosing instance | What it captures | What `this` means inside | Nameable and reusable | QuizStakes case |
|---|---|---|---|---|---|
| **`static` nested** | No | Nothing | The nested instance | Yes | `StakeSplit`, `GateSet.Builder` — a helper type that belongs to the outer type's namespace and nothing more |
| **Inner (non-static member)** | Yes | The enclosing instance, live, via synthetic `this$0` | The inner instance; `Outer.this` reaches the enclosing one | Yes | Almost nothing. An iterator over an aggregate's own storage is the honest case |
| **Local** | Only if declared in an instance method and it uses the enclosing instance | Effectively-final locals, copied into `val$` fields | The local-class instance | Named, but scoped to one block | A comparator-with-state genuinely private to one method of `PaymentService` |
| **Anonymous** | Same rule as local | Same as local | **The anonymous instance** — not the enclosing one | No | A `DocumentVerification` callback needing two methods at one call site |
| **Lambda** | Only if the body reads `this` or an instance member | Effectively-final locals, passed as `invokedynamic` arguments | **The enclosing instance** | No | Every single-method callback: a `Predicate<Restriction>`, a `Comparator<LedgerEntry>` |

The rule is mechanical enough to apply in a review without thinking: **`static` nested unless you need the enclosing instance; a lambda if the contract is one method and you do not need `this`; anonymous only if you need `this` or more than one method and there is exactly one call site; inner almost never; local when the type is genuinely a single method's private detail.**

### How it works

**`this$0` retention, which is why "inner almost never" is defensible rather than dogma.** A non-static inner class holds a synthetic final field, conventionally named `this$0`, pointing at the instance that created it, and every one of its constructors takes that instance as a hidden first parameter. So an inner-class instance that *outlives* its enclosing object keeps the enclosing object — and the entire object graph reachable from it — strongly reachable. Make it concrete: a `PaymentRun` progress listener written as an inner class of `PaymentService`, registered with a long-lived `NotificationService` and never unregistered, keeps that `PaymentService` alive, and with it the `FundsLedger`, the `JdbcTemplate`, the connection pool and every cache any of them holds. One forgotten listener, one whole service graph, and the heap dump shows the leak rooted at the listener registry rather than at anything anyone suspects. `[BYTECODE]` The refinement that keeps this accurate: `javap -c -p` on JDK 21.0.7 shows `javac` emits the `this$0` field **only when the inner class actually uses its enclosing instance** — though the constructor descriptor still takes the enclosing instance either way, so you cannot tell from the source. Design-wise still assume an inner class retains its enclosing instance, because adding one enclosing-field access in a later edit silently puts the field back with no signal at the call site. [`../inheritance-and-dispatch/02-nested-classes.md`](../inheritance-and-dispatch/02-nested-classes.md) owns nested classes and carries D-049 and D-050; [`../inheritance-and-dispatch/04-internals-nested-classes.md`](../inheritance-and-dispatch/04-internals-nested-classes.md) owns the synthetic fields and carries D-120.

**`this` in a lambda versus an anonymous class** — the most-asked distinction in this leaf, and it has a real mechanism behind the one-line answer. Inside an anonymous class, `this` is the anonymous instance, because there *is* an anonymous instance: `javac` emits a whole class file for it. Inside a lambda, `this` is the **enclosing** instance, because a lambda is not a class instance of its own — its body compiles to a method on the enclosing class, and the lambda object is a `MethodHandle`-backed instance spun at first execution by `LambdaMetafactory` through `invokedynamic`. Measured on this build:

```
anon: this.getClass() = Probe$PaymentRunSignOff$1
lambda: this.getClass() = Probe$PaymentRunSignOff / this.label() = PaymentRun sign-off window
anon class name   = Probe$PaymentRunSignOff$1
lambda class name = Probe$PaymentRunSignOff$$Lambda/0x000000f801159a18
```

Read the four lines. In the anonymous body, `this.getClass()` is `Probe$PaymentRunSignOff$1` — the synthesized anonymous class, one of a numbered series. In the lambda body, `this.getClass()` is `Probe$PaymentRunSignOff`, the *enclosing* class, and `this.label()` calls the enclosing instance's method with no qualification. The last line is the lambda's runtime class as seen from outside: `Probe$PaymentRunSignOff$$Lambda/0x000000f801159a18`, a hidden class with no class file on disk, generated at the first execution of that `invokedynamic` call site — which is also why it has no name you can reference and no constructor you can call.

Three consequences fall straight out of "a lambda has no `this` of its own": a lambda **cannot be recursive by name** (there is no name and no `this` to reach itself through — the workaround is a field or a local array holding the reference, or a named method reference); it **cannot shadow an enclosing field** with `this.field`, because `this.field` reads the enclosing field; and it **does not create a new `this$0`**, so a lambda that reads no instance member captures nothing and its body compiles to a private *static* method. That last point is the retention answer: a lambda that touches no instance state is the only one of the five that is guaranteed to hold nothing, and a lambda that touches instance state retains exactly as much as an inner class would.

**The capture rule, which applies to the last three.** A captured local must be **effectively final** — assigned once and never reassigned. The reason is the pass-by-value fact [`03-pass-by-value.md`](03-pass-by-value.md) established: the capture copies the variable's *value* into a synthetic field or an `invokedynamic` argument, so a mutable local would leave two copies with divergent lives and no defined way to reconcile them, and Java refuses to pretend otherwise rather than picking a semantics. Guide 04 owns lambdas, `invokedynamic` and `LambdaMetafactory`.

### Diagram

No diagram of its own in this file; **D-089** in [`05-which-construct.md`](05-which-construct.md) is the §2.15 decision tree. The adjacent pictures are **D-049** and **D-050**, the four nested-class kinds and `this$0` retention, both owned by [`../inheritance-and-dispatch/02-nested-classes.md`](../inheritance-and-dispatch/02-nested-classes.md), with the synthetic-field detail in D-120 in [`../inheritance-and-dispatch/04-internals-nested-classes.md`](../inheritance-and-dispatch/04-internals-nested-classes.md).

### A concrete example

The same listener written the leaking way and the correct way, plus the anonymous-versus-lambda `this` demonstration that produced the output above:

```java
public class PaymentService {

    private final NotificationService notifications;
    private final FundsLedger fundsLedger;

    public PaymentService(NotificationService notifications, FundsLedger fundsLedger) {
        this.notifications = notifications;
        this.fundsLedger = fundsLedger;
    }

    /** LEAKS: the inner class holds this$0, so the registry keeps this whole service alive. */
    class RunProgressListenerInner implements Consumer<PaymentRun> {
        @Override public void accept(PaymentRun run) {
            fundsLedger.recordProgress(run.runId(), run.entries().size());
        }
    }

    /** Correct: a static nested class holding only what it needs. */
    static final class RunProgressListener implements Consumer<PaymentRun> {
        private final FundsLedger fundsLedger;

        RunProgressListener(FundsLedger fundsLedger) {
            this.fundsLedger = fundsLedger;
        }

        @Override public void accept(PaymentRun run) {
            fundsLedger.recordProgress(run.runId(), run.entries().size());
        }
    }

    public void registerLeaking() {
        notifications.onRunProgress(new RunProgressListenerInner());
    }

    public void registerCorrect() {
        notifications.onRunProgress(new RunProgressListener(fundsLedger));
    }
}
```

`RunProgressListenerInner` retains the entire `PaymentService` — the ledger, the notification service, everything either of them holds — for as long as `NotificationService` keeps the listener. `RunProgressListener` retains one `FundsLedger`, which is what the callback actually uses, and the `static` keyword is the whole difference. A lambda, `run -> fundsLedger.recordProgress(run.runId(), run.entries().size())`, is *also* leaking here, because `fundsLedger` is an instance field, so the lambda captures `this` to read it — the fix is the same either way: pass what is needed rather than reaching for it.

And the `this` demonstration, complete and runnable:

```java
public class SignOffProbe {

    interface StakeAudit { String describe(); }

    static class PaymentRunSignOff {
        String label() { return "PaymentRun sign-off window"; }

        StakeAudit anonymousForm() {
            return new StakeAudit() {
                @Override public String describe() {
                    return "this.getClass() = " + this.getClass().getName();
                }
            };
        }

        StakeAudit lambdaForm() {
            return () -> "this.getClass() = " + this.getClass().getName()
                    + " / this.label() = " + this.label();
        }
    }

    public static void main(String[] args) {
        PaymentRunSignOff run = new PaymentRunSignOff();
        System.out.println("anon: " + run.anonymousForm().describe());
        System.out.println("lambda: " + run.lambdaForm().describe());
        System.out.println("anon class name   = " + run.anonymousForm().getClass().getName());
        System.out.println("lambda class name = " + run.lambdaForm().getClass().getName());
    }
}
```

Worth knowing that the anonymous version *cannot* be written to check `this instanceof PaymentRunSignOff` — that is a compile error on this build, `incompatible types: <anonymous StakeAudit> cannot be converted to PaymentRunSignOff`, because `javac` knows statically that `this` is the anonymous type. The lambda version compiles, which is the same fact from the other side.

### The gotcha

**Pitfall:** converting an anonymous class to a lambda mechanically, when the body uses `this`. The wrong belief is that a single-method anonymous class and a lambda are interchangeable syntax. The symptom is code that compiles and misbehaves: `this.getClass().getSimpleName()` in a logging line suddenly reports the enclosing service instead of the callback, `this.equals(other)` compares the wrong object, and a recursive call by name stops compiling. The fix is to check three things before the conversion — does the body mention `this`, is it recursive, does it declare more than one method — and to keep the anonymous class if any of the three holds.

> **Definition.** The five nested forms differ in what they retain: a `static` nested class retains nothing, an inner class retains its enclosing instance through a synthetic `this$0` field emitted when it uses that instance, local and anonymous classes additionally copy effectively-final locals into `val$` fields, and a lambda has no class instance of its own — so `this` inside it is the enclosing instance, it cannot be recursive by name, and it retains the enclosing instance only if its body actually reads instance state.

---

## 5. The consolidated decision table (2.15.10)

`[RESEARCH]`

This is the card §2.15 exists to produce: one row per decision, across the nine its leaves 2.15.1–2.15.9 settle, plus the four decisions Part 2 settled elsewhere that belong on the same screen. Read it by column two — find the question that matches the one you are actually asking, take the answer, and follow column five when you need the mechanism rather than the verdict. Its picture is **D-089** in [`05-which-construct.md`](05-which-construct.md), which is the same decision as a tree. This section is a table rather than an argued concept, so it carries the `### Diagram` line and the boxed definition and skips the other beats deliberately — a "why it exists" and a "concrete example" for a lookup table would be padding, and the house rules ban that.

### Diagram

No diagram of its own; **D-089** in [`05-which-construct.md`](05-which-construct.md) *is* this table drawn as a decision tree, and it is the picture to look at first if you are meeting §2.15 for the first time rather than reloading it.

| What you are modelling | The question that decides it | The answer | The QuizStakes instance | Where the mechanism lives |
|---|---|---|---|---|
| A **value type** | Is it defined entirely by its components, with no identity of its own? | A `record`; a wrapper type over a raw `UUID`/`String` even for one field | `Money`, `ClientId`, `StakeSplit`, `IdempotencyKey(String value)` | `05-which-construct.md`; [`../records-and-sealed/01-basics.md`](../records-and-sealed/01-basics.md) |
| A **contract** | Is the set of implementations open, or closed and known? | Open: an `interface`. Closed: a `sealed interface` with a pattern-matching `switch` | `Verdict` sealed over `DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict` | `05-which-construct.md`; [`../records-and-sealed/01a-object-methods-sealed-and-fit.md`](../records-and-sealed/01a-object-methods-sealed-and-fit.md) |
| A **constant** | Is the set of values fixed at compile time and closed? | Fixed and closed: an `enum`. A single value with behaviour: `static final`. A compile-time literal: `static final` primitive or `String` | `RestrictionType`, `RestrictionSource`, `AccountStatus`; `BONUS_CAP = 100` | `05-which-construct.md`; [`../enums/01-basics.md`](../enums/01-basics.md), [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md) |
| An **error signal** | Can the *immediate* caller do something specific about it, and will it? | Yes, at this call site: checked. No: unchecked. Per-element in a pipeline: a `Result` type | `PspTimeoutException` checked; `InsufficientFundsException` unchecked; `Result` for a batched `PaymentRun` | `05-which-construct.md`; [`../exceptions/02-in-practice.md`](../exceptions/02-in-practice.md), [`../exceptions/02a-checked-exceptions-and-lambdas.md`](../exceptions/02a-checked-exceptions-and-lambdas.md) |
| A **number** | Is it money, or a count, or a measurement? | Money: `BigDecimal` (or a `long` of minor units) inside a `Money` type. Count: `long`/`int`. Measurement where error is tolerable: `double` | `Money(BigDecimal amount, Currency currency)`; the 3.33 stake splitting 0.33 bonus + 3.00 cash | `05-which-construct.md`; [`../numbers-and-money/02-numbers-and-money.md`](../numbers-and-money/02-numbers-and-money.md) |
| **Text** | What has to be true of the bytes after you are done? | Nothing special: `String`. Built incrementally: `StringBuilder`. Erasable: `char[]`. Encoding is not yours: `byte[]` | `char[]` for a supplied credential; `byte[]` for a PSP callback body under HMAC | §1 above; [`../strings/02b-text-and-encoding.md`](../strings/02b-text-and-encoding.md), [`../strings/02-performance-and-text.md`](../strings/02-performance-and-text.md) |
| **Time** | A point on the timeline, a calendar day, or a human's wall clock? | `Instant` / `LocalDate` / `ZonedDateTime`. Epoch millis only on the wire | `LedgerEntry.postedAt`; a date of birth; a `PaymentRun` sign-off window | §2 above; [`../date-and-time/02-date-and-time.md`](../date-and-time/02-date-and-time.md) |
| **Copying** | Is it mutable, and are its elements mutable? | Neither: share it. Container only: `List.copyOf`. Elements too: deep copy, or make the element type immutable. Yours to design: a `withX` rebuild | `List.copyOf(itemIds)` in the constructor; `Arrays.copyOf` for `long[] amountsMinor` | §3 above; [`../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`](../objects-equality-and-lifecycle/02-copying-and-composite-equality.md) |
| A **nested type** | Does it need the enclosing instance, and what would that retain? | `static` nested by default; lambda for one method without `this`; anonymous for `this` or two methods at one site; inner almost never; local for one method's private detail | `RunProgressListener` as `static` nested, not inner, so a stale listener does not retain `PaymentService` | §4 above; [`../inheritance-and-dispatch/02-nested-classes.md`](../inheritance-and-dispatch/02-nested-classes.md) |
| **Mutability** | Does anything actually need to change after construction? | Immutable by default; mutable only when a measured requirement forces it | Every value type; `Application`'s status machine returning a new instance per transition | [`02-immutability.md`](02-immutability.md), [`02a-shallow-deep-and-building-blocks.md`](02a-shallow-deep-and-building-blocks.md) |
| **Construction** | How many parameters, and how many are optional? | Few and all required: a static factory. Many or optional: a builder. Never a telescoping constructor | `StatusCode.of(...)`; `GateSet.Builder` | [`04-design-idioms.md`](04-design-idioms.md) |
| **Reuse** | Is this genuinely an "is-a", verified against the Liskov substitution test? | Composition and delegation by default; inheritance only for a type you also control and designed for it | `PaymentService` composes `FundsLedger`; it does not extend it | [`04a-composition-and-cross-index.md`](04a-composition-and-cross-index.md) |
| **Absence** | One value that might be missing, or a collection that might be empty? | Single value: `Optional<T>` as a **return** type only. Collection: `List.of()`, never `null` | `Optional<Bonus> activeBonus(ClientId)`; `List<Restriction> restrictions()` returning `List.of()` | [`../null-discipline/02-null-discipline.md`](../null-discipline/02-null-discipline.md) |

> **Definition.** §2.15 is thirteen independent decisions that share one shape: each is settled by a single discriminating question about the thing being modelled — what defines its identity, whether its implementation set is closed, whether it can change, what has to be true of it afterwards, and what it would retain — and the answer is a construct, not a preference.

---

## Pitfalls

### Switching a login parameter from `String` to `char[]` removes the password from the heap

**Wrong**

```java
@PostMapping("/login")
public ResponseEntity<Void> login(@RequestBody LoginRequest body) {
    char[] pw = body.password().toCharArray();   // body.password() is already a String
    try {
        return credentials.matches(pw) ? ResponseEntity.ok().build()
                                       : ResponseEntity.status(401).build();
    } finally {
        Arrays.fill(pw, '\0');
    }
}
```

The `finally` erases a *copy*. `body.password()` is a `String` that Jackson created while parsing the request body, and it is still fully live on the heap after this method returns — a heap dump taken any time before the next collection contains every password submitted since the last one, in plaintext.

**Right**

```java
public record LoginRequest(String clientRef, char[] password) {
    // Jackson binds a JSON string to char[] directly, so no String is ever created
    // for the credential. Erase it at the end of the request, in one place.
}

@PostMapping("/login")
public ResponseEntity<Void> login(@RequestBody LoginRequest body) {
    try {
        return credentials.matches(body.password()) ? ResponseEntity.ok().build()
                                                    : ResponseEntity.status(401).build();
    } finally {
        Arrays.fill(body.password(), '\0');
    }
}
```

The `char[]` starts at the deserialization boundary, so no `String` is ever constructed for the credential and the erase covers the only copy the application made. Even then, state the limit out loud: the JIT may have copied the array, a copying collector may have left a stale region behind, and the plaintext existed in a network buffer before Jackson saw it. This is hygiene with a real, bounded benefit — not erasure.

**Why people believe it:** the `char[]`-for-passwords advice is genuinely correct and genuinely old, and it is almost always taught as the rule without the boundary condition — so the type change looks like the whole fix rather than the half of it that only works if the type change reaches the boundary.

### `Duration.ofDays(1)` and `Period.ofDays(1)` are two spellings of the same thing

**Wrong**

```java
ZoneId london = ZoneId.of("Europe/London");
ZonedDateTime grantedAt = ZonedDateTime.of(2026, 3, 28, 23, 30, 0, 0, london);
ZonedDateTime expiresAt = grantedAt.plus(Duration.ofDays(30));   // "30 days from grant"
```

Measured on JDK 21.0.7, the one-day version of exactly this divergence:

```
base          = 2026-03-28T23:30Z[Europe/London]
+Duration 1d  = 2026-03-30T00:30+01:00[Europe/London]
+Period   1d  = 2026-03-29T23:30+01:00[Europe/London]
```

`Duration` added 86,400 real seconds and moved the wall clock 25 hours, because the transition skipped an hour. A bonus granted at 23:30 the night the clocks change expires an hour later on the wall clock than the operator's screen says it should, and the row that disagrees is the one the client complains about.

**Right**

```java
ZonedDateTime expiresAt = grantedAt.plus(Period.ofDays(30));
```

or, better, because a 30-day expiry is a calendar rule and does not need a time or a zone at all:

```java
LocalDate expiresOn = grantedAt.toLocalDate().plusDays(30);
```

`Period` means "the same wall-clock reading, n calendar days later", which is what "30 days from grant" means to a human and to a regulator. `LocalDate.plusDays` removes the zone from the question entirely and is measured at 3.26–3.36 ns in the master cost table, so there is no performance argument for the wrong one either.

**Why people believe it:** both classes implement `TemporalAmount`, both have an `ofDays` factory, and on any date that is not within a day of a transition they agree exactly — so the wrong one passes every test written on an arbitrary Tuesday and fails twice a year in production.

### `Collections.unmodifiableList` in a constructor makes the field safe

**Wrong**

```java
public final class WithdrawalBatch {
    private final List<String> transactionRefs;

    public WithdrawalBatch(List<String> transactionRefs) {
        this.transactionRefs = Collections.unmodifiableList(transactionRefs);
    }

    public List<String> transactionRefs() {
        return transactionRefs;
    }
}
```

Measured on this build, with the caller's list mutated after construction:

```
view = [WD-1, WD-2, WD-3] size=3
copy = [WD-1, WD-2] size=2
```

The `unmodifiableList` field is the `view` row. The batch grew a third transaction after its constructor finished validating two, and no mutator was ever called on the batch.

**Right**

```java
public final class WithdrawalBatch {
    private final List<String> transactionRefs;

    public WithdrawalBatch(List<String> transactionRefs) {
        this.transactionRefs = List.copyOf(transactionRefs);   // snapshot, not a window
    }

    public List<String> transactionRefs() {
        return transactionRefs;   // already immutable; no copy needed on the way out
    }
}
```

`List.copyOf` takes an independent snapshot, so a later `add` to the caller's list is invisible, and it returns the argument unchanged when the argument is already one of the immutable implementations — so the defensive copy is free in the common case where the caller passed a `List.of`.

**Why people believe it:** "unmodifiable" reads as a property of the data, and the returned object does throw on `add`, so the half of the guarantee that is easy to test passes. The half that fails is the half about a reference somebody else still holds.

### A lambda and a single-method anonymous class are interchangeable

**Wrong**

```java
StakeAudit audit = new StakeAudit() {
    @Override public String describe() {
        return "audited by " + this.getClass().getSimpleName();
    }
};
// mechanically "modernised" to:
StakeAudit audit = () -> "audited by " + this.getClass().getSimpleName();
```

Measured on this build, the two `this` values are different objects of different classes:

```
anon: this.getClass() = Probe$PaymentRunSignOff$1
lambda: this.getClass() = Probe$PaymentRunSignOff / this.label() = PaymentRun sign-off window
```

The anonymous body's `this` is the callback; the lambda body's `this` is the enclosing instance, so the "modernised" line silently starts logging the service's class name instead of the callback's. The same substitution breaks a recursive callback outright, because a lambda has no name and no `this` to reach itself through.

**Right**

```java
StakeAudit audit = new StakeAudit() {
    @Override public String describe() {
        return "audited by " + this.getClass().getSimpleName();
    }
};
```

Keep the anonymous class when the body mentions `this`, is recursive, or declares more than one method. Convert to a lambda only when none of those holds — which is the overwhelming majority of single-method callbacks, and is why the conversion is usually right and worth checking anyway.

**Why people believe it:** the IDE offers the conversion as a safe automated refactor, and it *is* safe for the common shape. `this` inside a lambda meaning the enclosing instance is a consequence of a lambda not being a class instance at all, which is exactly the kind of mechanism a refactoring quick-fix cannot explain in a tooltip.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| Text, the question | What has to be true of the bytes afterwards — not which is fastest |
| `String` | Default. Immutable, poolable, free `equals`/`hashCode`. **Not erasable at all** |
| `StringBuilder` | Incremental construction only. `+` in one expression is `invokedynamic` since Java 9 and usually faster |
| `char[]` | The right declared type for a credential. `Arrays.fill(pw, '\0')` in a `finally`. Best-effort, not erasure |
| `char[]` limits | JIT copies, copying-GC stale regions, and the value having already been a `String` at the framework boundary |
| Erase count in a PBKDF2 check | Three: the supplied `char[]`, `PBEKeySpec.clearPassword()`, and the derived key `byte[]` |
| `byte[]` | For a payload whose charset is not yours — a PSP body under HMAC stays `byte[]` until verified |
| Encoding happens at | `getBytes(Charset)` and `new String(bytes, Charset)`, nowhere else |
| Default charset | UTF-8 from Java 18 (JEP 400); platform-dependent on 17 and earlier |
| `café` measured | UTF-8 `[99, 97, 102, -61, -87]` (5 bytes) vs ISO-8859-1 `[99, 97, 102, -23]` (4 bytes) |
| `Instant` | A point on the UTC timeline. Nanosecond resolution. `LedgerEntry.postedAt` |
| `LocalDate` | A calendar day, no time, no zone. A date of birth, and the 14-day coupon window |
| `ZonedDateTime` | A wall clock in a named zone. The **only** one whose arithmetic respects DST |
| Epoch millis | A serialization format, not a type. No zone, millisecond-truncating, no type safety |
| Millis truncation, measured | `2026-03-20T09:46:40.123456789Z` round-trips to `...40.123Z` |
| `Duration` vs `Period` | 86,400 s vs "same wall clock, n days later". Measured divergence over 2026-03-29 Europe/London |
| Clock reads (cost table) | `nanoTime` 9.18–9.70 ns · `currentTimeMillis` 13.55–13.70 ns · `Instant.now()` 19.79–20.30 ns |
| `Instant.now()` at peak | 13,600/sec × 20 ns ≈ 272 microseconds/sec ≈ 0.027% of a core. Do not cache it |
| `System.nanoTime()` | No epoch, monotonic, elapsed time within one JVM only. Never a timestamp |
| Testability | Inject a `Clock`; `Instant.now(clock)`, never bare `Instant.now()` in domain logic |
| Copy, the question | Is it mutable, and are its elements mutable? Asked twice, one level apart |
| View vs copy, measured | `unmodifiableList` reported size 3 after the source grew; `List.copyOf` reported 2 |
| `clone()` | Shallow, `Cloneable` declares no `clone`, `Object.clone` is `protected native`. Never on your own types |
| Arrays | No immutable array form exists. `Arrays.copyOf` in and out is the only defence |
| Rebuild cost (cost table) | Escaping small object 4.394 ns; non-escaping 0.301–0.559 ns, eliminated. No documented guarantee |
| Nested, the question | Does it capture the enclosing instance, and what does that retain? |
| The rule | `static` nested by default · lambda for one method without `this` · anonymous for `this` or 2 methods · inner almost never · local for one method's detail |
| `this$0` | Synthetic field on an inner class, emitted by javac 21 only when the enclosing instance is used |
| `this` in an anonymous class | The anonymous instance — measured `Probe$PaymentRunSignOff$1` |
| `this` in a lambda | The **enclosing** instance — measured `Probe$PaymentRunSignOff`. No recursion by name, no shadowing, no new `this$0` |
| Lambda runtime class | A hidden class, e.g. `Probe$PaymentRunSignOff$$Lambda/0x000000f801159a18`, spun by `LambdaMetafactory` |
| Capture rule | Effectively final, because the capture copies the value — the pass-by-value fact, again |

---

## Self-test

**Q1.** Why is `char[]` the right declared type for a password parameter, and what exactly does it fail to guarantee?

<details><summary>Answer</summary>

A `String`'s characters live in a private `byte[]` that is never handed out and never overwritten, so there is no operation anywhere in the platform that zeroes a live `String`. A password in a `String` therefore stays in the heap in plaintext — visible in any heap dump, JFR recording or crash dump — until the collector happens to reclaim it, and if it was a literal or went through `intern()` it is additionally reachable from the string table (`StringTableSize = 65536` on this build) for the JVM's lifetime. A `char[]` is an ordinary mutable array, so `Arrays.fill(pw, '\0')` in a `finally` block shrinks the plaintext's window to one method call. What it does *not* guarantee is that the plaintext is gone: the JIT may have copied the array's contents into registers or a stack slot your `fill` does not reach; a copying collector may have relocated the array and left a stale un-zeroed copy behind; and most commonly, the value may already have been a `String` on the way in, since a servlet container or Jackson decodes an HTTP body into `String` long before your code runs — `Console.readPassword()` returns `char[]` precisely so that path exists, while `Scanner.nextLine()` does not. So `char[]` is correct as the default type for a credential — it keeps plaintext out of the pool, gives a real erase point, and documents intent in the signature — and it is hygiene, not erasure.

</details>

**Q2.** A PSP callback arrives with an HMAC signature computed over the request body. Why must the body stay `byte[]`?

<details><summary>Answer</summary>

Because the signature is over bytes, and a round trip through `String` can change them. A `String` in Java carries no charset — it is UTF-16 (or Latin-1 under compact strings) code units — so encoding happens at exactly two places, `getBytes(Charset)` and `new String(bytes, Charset)`, and if the charset you decode and re-encode with is not the sender's, the byte sequence differs. Measured on JDK 21.0.7, `café` is five bytes in UTF-8, `[99, 97, 102, -61, -87]`, and four in ISO-8859-1, `[99, 97, 102, -23]`; any HMAC over one fails against the other. The no-argument `getBytes()` makes this worse by hiding the charset: it is UTF-8 unconditionally from Java 18 under JEP 400 and platform-dependent on Java 17 and earlier, so a JDK 17 service and a JDK 21 service running identical code disagree. The rule is to verify the signature over the raw `byte[]` first, and only then decode — and when you do decode, name the charset explicitly at both ends.

</details>

**Q3.** Three fields: a ledger entry's timestamp, a client's date of birth, and a `PaymentRun`'s operator sign-off window. Pick the type for each and justify it.

<details><summary>Answer</summary>

`LedgerEntry.postedAt` is an `Instant`: it records a moment that happened, on the universal timeline, and the ledger is the source of truth for money so ordering and precision matter — `Instant` has nanosecond resolution, which epoch millis does not. A date of birth is a `LocalDate`: it is a calendar fact with no time and no zone, and storing it as an `Instant` gives it a midnight in whichever zone did the conversion, so a later conversion in a zone one hour behind renders the previous day — which on the `AO-119 AGE_INELIGIBLE` gate turns an off-by-one-day into an off-by-one-decision for anyone registering on their eighteenth birthday. The sign-off window is a `ZonedDateTime`: the banking partner's four windows a day are stated as wall-clock times in a named zone, and `ZonedDateTime` is the only one of the three whose arithmetic respects that zone's DST rules, so "09:00 in the partner's zone" stays 09:00 across a transition instead of drifting to 08:00 or 10:00. Epoch millis is not a fourth candidate — it has no zone, truncates to milliseconds (measured: `...40.123456789Z` round-trips to `...40.123Z`), and gives no type safety, since `long postedAt` and `long clientId` are the same type to the compiler. Convert at the boundary, keep `Instant` inside, and inject a `Clock` so `Instant.now(clock)` is testable.

</details>

**Q4.** Work through why `Duration.ofDays(1)` and `Period.ofDays(1)` disagree, with the measured output.

<details><summary>Answer</summary>

`Duration` is elapsed time held as seconds plus nanos, so `ofDays(1)` is exactly 86,400 seconds. `Period` is calendar time held as years, months and days, so `ofDays(1)` means "the same wall-clock reading, one calendar day later". Across a DST transition those are different quantities of real time. Measured on JDK 21.0.7 from `2026-03-28T23:30` in `Europe/London`, the night the UK clocks go forward at 01:00: the base is `2026-03-28T23:30Z[Europe/London]`; adding `Duration.ofDays(1)` gives `2026-03-30T00:30+01:00[Europe/London]`, because 86,400 real seconds carry the wall clock 25 hours forward when one hour is skipped; adding `Period.ofDays(1)` gives `2026-03-29T23:30+01:00[Europe/London]`, the same wall clock one calendar day on, which is only 82,800 real seconds away. Both are correct answers to different questions. The practical rule: a business rule expressed in days — the bonus's 30-day expiry, the coupon's 14-day validity — is calendar time, so it is `Period`, or better `LocalDate.plusDays` on a `LocalDate` where there is no time or zone in the requirement at all. `Duration.ofDays` there is wrong by an hour twice a year, only for the grants near a transition, which is why it survives testing.

</details>

**Q5.** `Collections.unmodifiableList` versus `List.copyOf` for a constructor field: state the difference and the measured evidence.

<details><summary>Answer</summary>

`Collections.unmodifiableList` returns a **view** — a wrapper over the same backing list — so it rejects `add` through itself but reports every change made to the list it wraps. `List.copyOf` returns an independent **snapshot**. Measured on JDK 21.0.7: take both from an `ArrayList` of `["WD-1", "WD-2"]`, then `add("WD-3")` to the source, and the view prints `[WD-1, WD-2, WD-3] size=3` while the copy prints `[WD-1, WD-2] size=2`. In a constructor that matters completely, because the caller keeps its list: an aggregate whose field is a view can change after construction with no mutator ever called on it, invalidating every invariant the constructor validated. So `List.copyOf` on the way in, and the view — or the field itself, since it is already immutable — on the way out. `List.copyOf` is also cheap in the common case: it returns the argument unchanged when the argument is already one of the immutable `List.of` implementations, so a caller who passed `List.of(...)` pays nothing.

</details>

**Q6.** When is an inner class the wrong choice, and what is the mechanism that makes it wrong?

<details><summary>Answer</summary>

Whenever the instance can outlive its enclosing object. A non-static inner class holds a synthetic final field, conventionally `this$0`, pointing at the instance that created it, and every constructor takes that instance as a hidden first parameter — so the inner instance keeps the enclosing object, and everything reachable from it, strongly reachable. Concretely: a `PaymentRun` progress listener written as an inner class of `PaymentService`, registered with a long-lived `NotificationService` and never unregistered, retains that `PaymentService` and with it the `FundsLedger`, the `JdbcTemplate`, the connection pool and every cache any of them holds. One forgotten listener, one whole service graph, and the heap dump roots the leak at the listener registry rather than anywhere anyone suspects. The refinement worth knowing: verified with `javap -c -p` on JDK 21.0.7, `javac` emits `this$0` only when the inner class actually uses its enclosing instance — but the constructor descriptor takes the enclosing instance either way, and you cannot tell from the source, so design as though an inner class always retains its enclosing instance, because one added field access in a later edit puts the field back with no signal. The fix is a `static` nested class taking exactly what it needs as a constructor parameter; note that a lambda reading an instance field has the same problem for the same reason.

</details>

**Q7.** What does `this` refer to inside a lambda, versus inside an anonymous class, and why?

<details><summary>Answer</summary>

Inside an anonymous class, `this` is the anonymous instance, because there genuinely is one — `javac` emits a class file for it. Inside a lambda, `this` is the **enclosing** instance, because a lambda is not a class instance of its own: its body compiles to a method on the enclosing class, and the object implementing the functional interface is spun at the first execution of an `invokedynamic` call site by `LambdaMetafactory`. Measured on JDK 21.0.7: from inside the anonymous body, `this.getClass().getName()` is `Probe$PaymentRunSignOff$1`; from inside the lambda body it is `Probe$PaymentRunSignOff`, the enclosing class, and `this.label()` calls the enclosing instance's method unqualified. From outside, the lambda's runtime class is a hidden class with no file on disk — `Probe$PaymentRunSignOff$$Lambda/0x000000f801159a18` on that run. Three consequences follow: a lambda cannot be recursive by name, since there is no name and no `this` to reach itself through; it cannot shadow an enclosing field with `this.field`; and it creates no new `this$0`, so a lambda touching no instance member compiles to a private *static* method and retains nothing. That last point is the retention answer, and it is also why mechanically converting an anonymous class whose body mentions `this` into a lambda compiles and misbehaves.

</details>

**Q8.** A reviewer proposes caching `Instant.now()` per request to save clock reads on the ledger-write path. Answer with numbers.

<details><summary>Answer</summary>

Decline, with the arithmetic. Quoted from the master cost table, measured on this build: `Instant.now()` is 19.79–20.30 ns, `System.currentTimeMillis()` 13.55–13.70 ns and `System.nanoTime()` 9.18–9.70 ns — all three leave the JVM for an OS clock, so none is foldable or hoistable and the cost is real. At the peak ledger write rate of 13,600/sec, one timestamp per entry is 13,600 × 20 ns ≈ 272 microseconds/sec of CPU, or roughly 0.027% of one core. That is not a cost worth a correctness risk, and the risk is real: a cached timestamp makes every entry in a batch claim the same moment, which destroys within-batch ordering on a ledger that is the sole source of truth for money. Two side notes worth having ready. The ordering of those three figures contradicts the usual folklore — `nanoTime` is the cheapest, not the dearest, and `Instant.now()` is the dearest because it adds a wrapper allocation on top of a `currentTimeMillis`-class call. And `System.nanoTime()` is not a substitute for either: it has no defined epoch, is only meaningful as a difference within one JVM, and as a `postedAt` value would produce timestamps unrelated to any calendar and incomparable across processes.

</details>

---

## Open questions

- **C2's escape-analysis and scalar-replacement heuristics.** §3 quotes the master cost table's 4.394 ns escaping against 0.301–0.559 ns non-escaping for a small object on JDK 21.0.7, but the JVM makes no documented guarantee about when either optimisation applies, so neither figure can be turned into a rule about your own rebuild. Only a JMH measurement of the specific call site settles it.
- **The extent to which `Arrays.fill` on a `char[]` actually removes plaintext from process memory.** §1 states the three reasons it is best-effort — JIT-held copies, copying-collector stale regions, and an upstream `String` — but the *degree* to which each occurs on a given build and collector is not something this file measured, and would need a native heap inspection under a controlled GC configuration to settle rather than a Java-level experiment.
- **Whether Jackson binds a JSON string to a `char[]` record component without materialising an intermediate `String`** in the pitfall's "Right" form. Jackson is not on this machine's classpath, so that is a documentation-level claim about the binding path, not a verified one; the databind source for `CharArrayDeserializer` would settle it.

---

**Leaves covered:** 2.15.6, 2.15.7, 2.15.8, 2.15.9, 2.15.10 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-089 in `05-which-construct.md` is the §2.15 decision tree
**Target version:** Java 21 LTS
**Lines:** 774
