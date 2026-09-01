# 03 Java Core — Parsing and formatting numbers — INTERMEDIATE (§2.4, 2.4.23–2.4.24)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Money in storage, BigInteger, and what exactness costs](02d-storage-biginteger-and-cost.md) · Next: [BigDecimal and BigInteger internals](03-internals-bigdecimal.md)

This file owns two traps at the boundary where a number becomes text: parsing
a human-entered number with the wrong locale, and sharing a `DecimalFormat`
instance across threads. Both leaves are `[TRAP]`. No diagram belongs to this
file — the pictures for adjacent material live in
`02b-equality-scale-and-rounding.md` (D-073, D-074) and
`03-internals-bigdecimal.md` (D-125). Measurements below were taken on Oracle
JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64.

---

## 1. Parsing user-entered numbers (2.4.23)

`[TRAP]`. A decimal number typed by a human is not a number — it is a **string
in a locale**, and the same eleven characters mean two different amounts
depending on whose keyboard typed them. `"3,33"` is three-and-a-third to a
German client and three thousand three hundred thirty-three to an American
one, and nothing about the string itself says which.

### Why it exists

`Locale`-aware parsing exists because the decimal separator and the grouping
separator are swapped between locale families — a comma is the decimal point
in `de-DE` and a thousands grouping mark in `en-US`, and vice versa for the
dot. A parser that ignores locale has to guess, and Java's default guess is
whatever `Locale.getDefault()` resolves to on the running JVM.

### How it works

The measurement from §6.19 is the entire lesson:

| Call | Result | Correct? |
|---|---|---|
| `NumberFormat.getInstance(Locale.GERMANY).parse("3,33")` | `3.33` | Correct — comma is the decimal separator in `de-DE` |
| `NumberFormat.getInstance(Locale.US).parse("3,33")` | **`333`** | Wrong by 100x — comma read as a grouping separator |
| `NumberFormat.getInstance(Locale.US).parse("3.33")` | `3.33` | Correct |
| `NumberFormat.getInstance(Locale.GERMANY).parse("3.33")` | **`333`** | Wrong by 100x — mirror image |

**Neither wrong case throws.** `NumberFormat.parse` accepts `"3,33"` under a
US locale as a perfectly well-formed grouped integer with the comma
interpreted as a thousands separator, and returns `333` with no exception at
all.

The QuizStakes symptom this produces: a German client types `3,33` into a
deposit form whose backend parses the raw string with a default-locale or
US-locale `NumberFormat`. The parse succeeds, returns `333`, and the deposit
proceeds — a 100x error with no exception anywhere in the call chain. The
`DEP-301 CAPTURED` status is recorded against the wrong amount, and the ledger
takes it as fact; nothing downstream has any signal that anything went wrong,
because from the ledger's point of view a valid deposit of 333 was captured.

The second half of the trap is where the default locale comes from.
`NumberFormat.getInstance()` with no `Locale` argument resolves to the JVM's
*default* locale — the server's, not the client's — which is a hidden
dependency on the host exactly as `ZoneId.systemDefault()` is a hidden
dependency on the host's time zone (`../date-and-time/02a-instant-local-and-zoned.md`
covers that exact pattern for time). The consequence: this bug's behaviour
changes when the container's locale configuration changes — a base image
upgrade, a `-Duser.country` flag added or dropped, an orchestration platform
that sets `LANG` differently — and not when a single line of application code
changes. A parsing bug with no code diff to explain it is the signature of a
default-locale dependency.

`setParseBigDecimal(true)`, measured from §6.19:

```
DecimalFormat df = new DecimalFormat("#,##0.00");
df.parse("3.33")                     -> 3.33          (returns a Double)
df.setParseBigDecimal(true);
df.parse("3.33").getClass()          -> java.math.BigDecimal
df.parse("3.33")                     -> 3.33
```

Without `setParseBigDecimal(true)`, `DecimalFormat.parse` returns a `Double` —
exactness is lost the moment the parse happens, before any `BigDecimal`
constructor is ever reached, the same defect `02a`'s leaf 2.4.9 measured
arriving by a different route (`new BigDecimal(double)` versus a parse that
never gets the chance to use the `String` constructor at all). With the flag
set, `parse` returns a `BigDecimal` directly from the digit string, with no
binary-floating-point value ever constructed in between. For money, this is a
rule, not an optimisation: **`setParseBigDecimal(true)` is mandatory on any
`DecimalFormat` that will parse an amount.**

A complete, runnable parser that gets both halves right — explicit `Locale`,
`setParseBigDecimal(true)`, and rejection of trailing garbage via
`ParsePosition` rather than silently ignoring it:

```java
import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.text.ParsePosition;
import java.util.Locale;

final class LocalizedAmountParser {

    private final Locale locale;

    LocalizedAmountParser(Locale locale) {
        this.locale = locale;
    }

    BigDecimal parse(String rawInput) {
        DecimalFormat format = new DecimalFormat(
                "#,##0.##", DecimalFormatSymbols.getInstance(locale));
        format.setParseBigDecimal(true);

        ParsePosition position = new ParsePosition(0);
        BigDecimal result = (BigDecimal) format.parse(rawInput, position);

        if (result == null || position.getErrorIndex() != -1) {
            throw new IllegalArgumentException(
                    "Not a valid amount for locale " + locale + ": " + rawInput);
        }
        if (position.getIndex() != rawInput.length()) {
            throw new IllegalArgumentException(
                    "Trailing characters after amount for locale " + locale
                            + ": " + rawInput);
        }
        return result;
    }
}
```

`ParsePosition` matters because `DecimalFormat.parse(String)` without it stops
at the first character it cannot consume and silently returns whatever it
parsed up to that point — `"3.33abc"` would parse as `3.33` with the trailing
`"abc"` never reported. Checking `position.getIndex()` against the input's
full length turns that silent truncation into a thrown exception.

The honest alternative, and when it is better: for a machine-to-machine
boundary — a JSON request body, a wire contract between two services — do not
localise the number at all. Require a canonical dot-decimal string
(`"3.33"`, never `"3,33"`) and parse it directly with `new BigDecimal(String)`,
because there is no human on the other end of that boundary whose locale needs
respecting, and every `Locale`-aware code path is pure risk with no benefit.
Localise on the way *out*, to a human reading a screen, and never on the way
*in*, from a machine — a rule guide 12 (API design) covers in full for what
belongs on the wire versus what belongs in a UI layer.
`../strings/02b-text-and-encoding.md` covers text formatting and locale
handling more broadly.

**Pitfall:** parsing a user-entered amount with `NumberFormat.getInstance()`
(no explicit `Locale`) or with a hardcoded `Locale.US` regardless of who is
typing, produces a value that is either right or wrong by exactly 100x
depending on which locale the input string happens to match — and never
throws in either case.

> A number typed by a human is a string in a locale, not a number — parse it
> with the client's explicit `Locale` and `setParseBigDecimal(true)`, or
> require a canonical dot-decimal string at a machine boundary and skip
> locale entirely.

---

## 2. `DecimalFormat` is not thread-safe (2.4.24)

`[TRAP]`. The mechanism, not just the warning: `DecimalFormat` carries a
shared mutable `DigitList` internally and inherits the same mutable-state
design `java.text` used throughout the `Calendar` era. A single
`DecimalFormat` instance held in a `static final` field looks exactly like the
safe, allocation-avoiding move — because `DateTimeFormatter`, built two
decades later on an immutable design, genuinely is safe held that way — and
that resemblance is what makes the mistake so easy to make.

### Why it exists

`format` and `parse` both need scratch state to build up digits one at a time
before assembling the final string or number — a `DigitList` buffer that gets
filled, read, and reused. `java.text` classes from the original JDK 1.1 era
were designed as short-lived, per-call objects, not as shared singletons, so
that scratch state was never made thread-local or synchronized internally.

### How it works

The reproduced measurement from §6.18, in full. One shared
`new DecimalFormat("#,##0.00")` with `setParseBigDecimal(true)`, 8 threads ×
200,000 parses, half the calls parsing `"4.20"` and half parsing
`"1,234,567.89"`:

```
distinct wrong results : 8,693
exceptions              : 78 x java.lang.NumberFormatException: No digits found.
```

Real captured wrong values:

```
in "4.20"          ->  1.2327894
in "1,234,567.89"  ->  4.34456786E+12
in "1,234,567.89"  ->  2.03456789E+14
in "1,234,567.89"  ->  4204567.89289
```

A 4.20 stake parsed as 1.23; a 1,234,567.89 withdrawal parsed as 4.34
trillion. The shared mutable `DigitList` is the corrupted state: two threads
interleave a write and a read on the same buffer, and one thread's digits
bleed into another thread's result. At QuizStakes' settlement burst of
3,400/sec, a shared `DecimalFormat` on that hot path is not a rare-edge-case
risk — it is a near-certain corruption under realistic concurrency, and 78 of
those 1,600,000 calls threw `NumberFormatException: No digits found` outright,
meaning the corruption was sometimes visible as a crash and sometimes silent
data damage, with no way to predict which from the caller's side.

**State the honest limit of this measurement explicitly.** Under the same
load pattern applied to `format` instead of `parse` — 8 threads × 200,000
formats, on this build — the result was **0 wrong results and 0 exceptions**.
`DecimalFormat.format` did **not** visibly corrupt in this run. That does not
make `format` safe: the Javadoc states plainly that `DecimalFormat` is not
synchronized and that callers must synchronize externally if an instance is
shared across threads, so `format` is unsafe by contract regardless of what
one run observed. "Did not lose a race in one run" is not "is safe" — a
different JIT warm-up pattern, a different thread count, or a different JDK
build could surface the same class of bug `parse` demonstrated here. Do not
claim a `format` corruption beyond what was actually measured.

The fixes, with their real costs:

| Fix | Cost | Correct? |
|---|---|---|
| New instance per call | One small, short-lived allocation per call | Yes — simplest, no shared state at all |
| `ThreadLocal<DecimalFormat>` | Avoids the per-call allocation | Yes, but leaks in a container with pooled threads that outlive the request, and fits poorly with virtual threads (one per task, so the `ThreadLocal` gains little and adds bookkeeping) |
| External synchronisation (`synchronized` block around every call) | Serialises the hot path — every caller queues behind one lock | Yes, but defeats the purpose of a shared instance in a concurrent settlement path |

The fourth option is the actual recommendation, and it sidesteps the whole
class of bug rather than working around it: for parsing, skip `java.text`
entirely and use `new BigDecimal(String)` on a canonical dot-decimal string —
there is no shared mutable state to race on, because `BigDecimal`'s
constructor is a pure function of its input; for formatting where no
localisation is actually needed, `BigDecimal.toPlainString()` produces a
locale-independent, thread-safe string directly from the value with nothing
shared between callers.

`../date-and-time/02d-formatting-and-parsing.md` covers `DateTimeFormatter` in
full — it is the direct contrast to everything in this leaf: immutable and
thread-safe by construction, because its printer/parser tree is built once by
`DateTimeFormatterBuilder` and never mutated afterward, which is exactly the
class of design `DecimalFormat` predates. Guide 05 (Concurrency) covers the
memory-model half of why an unsynchronised shared mutable object produces
exactly this kind of interleaved corruption under concurrent access.

**Pitfall:** holding a `DecimalFormat` in a `static final` field because
`DateTimeFormatter` is safe held that way is a category error — the two
classes look identical from the call site (`format(value)`, `parse(string)`)
but have opposite thread-safety designs, and nothing at the call site signals
which one is being used.

> `DecimalFormat` carries mutable scratch state (`DigitList`) with no internal
> synchronization, so a shared instance corrupts under concurrent `parse` —
> measured, 8,693 distinct wrong results and 78 exceptions over 1.6M calls —
> and is unsafe by contract for `format` even where a given run shows no
> visible corruption.

---

## Pitfalls

### A locale-agnostic `NumberFormat.getInstance()` is assumed safe for any user input

**Wrong**

```java
NumberFormat parser = NumberFormat.getInstance();
Number amount = parser.parse(request.getDepositAmount());   // e.g. "3,33"
BigDecimal deposit = BigDecimal.valueOf(amount.doubleValue());
```

On a server running with the US default locale, `request.getDepositAmount() =
"3,33"` from a German client parses as `333` — measured,
`NumberFormat.getInstance(Locale.US).parse("3,33")` returns `333`, a 100x
error, with no exception thrown at any point in this chain.

**Right**

```java
DecimalFormat format = new DecimalFormat(
        "#,##0.##", DecimalFormatSymbols.getInstance(clientLocale));
format.setParseBigDecimal(true);
ParsePosition position = new ParsePosition(0);
BigDecimal deposit = (BigDecimal) format.parse(
        request.getDepositAmount(), position);
if (deposit == null || position.getIndex() != request.getDepositAmount().length()) {
    throw new IllegalArgumentException("Invalid amount: " + request.getDepositAmount());
}
```

Parsing with the client's explicit `Locale` and `setParseBigDecimal(true)`
gets `"3,33"` correctly as `3.33` for a German client and rejects genuinely
malformed input via `ParsePosition` instead of silently truncating it.

**Why people believe it:** `NumberFormat.getInstance()` compiles, runs without
exception on every test the author tries locally (where the local machine's
locale happens to match the test data), and returns a plausible-looking
number in every case — there is no signal at the call site that a locale
mismatch is even possible, let alone which direction it would be wrong in.

### `DecimalFormat` in a `static final` field, by analogy with `DateTimeFormatter`

**Wrong**

```java
final class SettlementFormatter {
    static final DecimalFormat AMOUNT_FORMAT = new DecimalFormat("#,##0.00");
    static {
        AMOUNT_FORMAT.setParseBigDecimal(true);
    }
}
// called concurrently from many settlement threads
BigDecimal amount = (BigDecimal) SettlementFormatter.AMOUNT_FORMAT.parse(raw);
```

Measured under 8 threads × 200,000 concurrent parses on this shared instance:
8,693 distinct wrong results and 78 `NumberFormatException: No digits found`,
with real captures like `"4.20"` parsed as `1.2327894`.

**Right**

```java
BigDecimal amount = new BigDecimal(canonicalDigitString);
```

`new BigDecimal(String)` has no shared mutable state at all — it is a pure
function of its input — so it has nothing to race on regardless of how many
threads call it concurrently, and it is the correct choice whenever the input
is already a canonical dot-decimal string with no locale to respect.

**Why people believe it:** `DateTimeFormatter.ofPattern("yyyy-MM-dd")` held as
a `static final` field is not just safe but the documented, recommended
pattern, because its printer/parser tree is immutable by construction —
`DecimalFormat` predates that design and looks identical from the call site
(`format(x)`, `parse(s)`), so the same "build once, share, avoid the
allocation" instinct that is correct for one is silently wrong for the other.

### One clean concurrent run of `DecimalFormat.format` is taken as proof it is safe

**Wrong**

```java
// "We load-tested format() under concurrency and saw zero corruption,
//  so it's fine to share this instance for formatting."
static final DecimalFormat DISPLAY_FORMAT = new DecimalFormat("#,##0.00");
```

The measured run in §6.18 — 8 threads × 200,000 formats — indeed produced 0
wrong results and 0 exceptions on this build, but that outcome is a property
of one run on one JDK build under one thread-count and timing pattern, not a
guarantee.

**Right**

```java
String display = amount.toPlainString();   // or a per-call DecimalFormat instance
```

Treat `DecimalFormat.format` as unsafe under concurrency regardless of what
any single test run showed, because the Javadoc states the contract
explicitly: not synchronized, external synchronization required for shared
use. `BigDecimal.toPlainString()` sidesteps the question entirely when no
localisation is needed.

**Why people believe it:** the measurement genuinely showed zero corruption
for `format` in this run, and it is tempting to read an absence of observed
failure as proof of safety — but `parse`, sharing the same underlying
`DigitList`-based design, did corrupt under an equivalent load, which shows
the design itself is unsafe even where one particular access pattern happened
not to trigger a visible failure.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `NumberFormat.getInstance(Locale.GERMANY).parse("3,33")` | `3.33` (correct — de-DE decimal separator) |
| `NumberFormat.getInstance(Locale.US).parse("3,33")` | `333` (wrong 100x — comma as grouping) |
| `NumberFormat.getInstance(Locale.US).parse("3.33")` | `3.33` (correct) |
| `NumberFormat.getInstance(Locale.GERMANY).parse("3.33")` | `333` (wrong 100x — mirror) |
| Either wrong case throws? | No — never |
| `NumberFormat.getInstance()` default | Resolves the JVM's default locale, a hidden host dependency |
| Same pattern elsewhere | `ZoneId.systemDefault()` — hidden host dependency |
| `DecimalFormat.parse` without the flag | Returns `Double` — exactness already lost |
| `setParseBigDecimal(true)` | Mandatory for any money parse; returns `BigDecimal` directly |
| Trailing garbage without `ParsePosition` | Silently truncated, not rejected |
| Machine-to-machine number boundary | Canonical dot-decimal string; `new BigDecimal(String)`; no locale |
| Rule of thumb | Localise on the way out to a human; never on the way in from a machine |
| `DecimalFormat` internal state | Shared mutable `DigitList`; no internal synchronization |
| `DecimalFormat.parse`, shared, 8 threads × 200k | 8,693 distinct wrong results, 78 `NumberFormatException` |
| Real captured wrong parse | `"4.20"` -> `1.2327894`; `"1,234,567.89"` -> `4.34456786E+12` |
| `DecimalFormat.format`, shared, 8 threads × 200k | 0 wrong, 0 exceptions **on this build** — not proof of safety |
| Javadoc contract | Not synchronized; caller must synchronize externally |
| `DateTimeFormatter` contrast | Immutable printer/parser tree; thread-safe by construction |
| Fix: new instance per call | Simplest; one small allocation; correct |
| Fix: `ThreadLocal<DecimalFormat>` | Avoids allocation; leaks with pooled/virtual threads |
| Fix: external synchronization | Correct; serialises the hot path |
| Recommended fix | `new BigDecimal(String)` for parsing; `toPlainString()` for formatting |

---

## Self-test

**Q1.** `NumberFormat.getInstance(Locale.US).parse("3,33")` returns `333`, not `3.33`, and throws no exception. Why?

<details><summary>Answer</summary>

Under `Locale.US`, the comma is the grouping (thousands) separator, not the
decimal separator, so `NumberFormat` reads `"3,33"` as the perfectly
well-formed integer `333` with a grouping mark in an unusual position — it has
no way to know the author intended the comma as a decimal point, because that
is only true in other locales such as `de-DE`. Nothing in the string itself
signals which locale it was typed under, so the parser applies whichever
locale it was configured with, correctly by its own rules, and produces a
100x-wrong number with no exception because nothing about the parse is
actually invalid under `Locale.US`'s rules.

</details>

**Q2.** What does `NumberFormat.getInstance()` (no `Locale` argument) actually resolve to, and why is that a problem for a service running in a container?

<details><summary>Answer</summary>

It resolves to the JVM's default locale, which comes from the *server's*
configuration — its `-Duser.language`/`-Duser.country` flags, its base image,
or its container platform's locale settings — not from the client making the
request. That makes the parsing behaviour a hidden dependency on the host
environment: the same code, unchanged, can start parsing amounts differently
after a base image upgrade or an orchestration platform change, with no
corresponding code diff to point to. It is the identical failure shape as
`ZoneId.systemDefault()` depending on the host's time zone configuration.

</details>

**Q3.** Why is `setParseBigDecimal(true)` described as mandatory rather than optional for parsing money with `DecimalFormat`?

<details><summary>Answer</summary>

Without it, `DecimalFormat.parse` returns a `Double`, so the parsed value has
already lost exactness — measured, `parse("3.33")` without the flag yields a
`Double`, and any binary-floating-point value constructed from parsing a
decimal string carries the same representation error `02a` measured for
`new BigDecimal(double)`. With `setParseBigDecimal(true)`, `parse` returns a
`BigDecimal` built directly from the digit string with no `double`
intermediate at all, which is the only way to guarantee the parsed amount is
exact.

</details>

**Q4.** Measured over 8 threads × 200,000 concurrent `DecimalFormat.parse` calls on one shared instance: 8,693 distinct wrong results and 78 exceptions. What is the shared mutable state responsible, and why doesn't `DateTimeFormatter` have the same problem?

<details><summary>Answer</summary>

`DecimalFormat` carries a shared mutable `DigitList` buffer used internally
during both formatting and parsing; two threads interleaving a write and a
read on that one buffer causes one thread's digits to bleed into another
thread's result, producing the corrupted values and the occasional
`NumberFormatException` measured. `DateTimeFormatter` has no equivalent
problem because its printer/parser tree is built once by
`DateTimeFormatterBuilder` and is immutable thereafter — there is no shared
mutable scratch state for concurrent calls to race on, so it is thread-safe
by construction rather than by locking.

</details>

**Q5.** The same measurement found that `DecimalFormat.format` produced 0 wrong results and 0 exceptions under equivalent concurrent load. Does that mean `format` is safe to share across threads? Why or why not?

<details><summary>Answer</summary>

No. That result describes one run, on one JDK build, under one specific
thread count and timing pattern — it is evidence that `format` did not lose a
race in this particular test, not proof that it cannot. The `DecimalFormat`
Javadoc states explicitly that the class is not synchronized and that callers
must synchronize externally for shared use, so `format` is unsafe by contract
regardless of any single run's outcome, and a different execution pattern
could still surface a race the way `parse` did in the same measurement.

</details>

**Q6.** For a JSON API endpoint that accepts a deposit amount, is `DecimalFormat` with an explicit client `Locale` the right tool for parsing that field? What should be used instead, and why?

<details><summary>Answer</summary>

No — a JSON body is a machine-to-machine boundary, not a human-facing form,
so there is no client locale to respect at all: the wire contract should
specify a canonical dot-decimal string (`"3.33"`, never a locale-formatted
`"3,33"`), and the server should parse it directly with
`new BigDecimal(String)`. That removes every `java.text` locale-parsing risk
from the machine boundary entirely — both the 100x locale-mismatch trap and
the `DecimalFormat` thread-safety trap — and reserves locale-aware parsing for
the one place it is actually needed: a form filled in by a human.

</details>

---

## Open questions

None. Every numeric claim in this file traces to §6.18 or §6.19 of the
measured brief, or to the `DecimalFormat`/`NumberFormat`/`BigDecimal` Javadoc
cited inline.

---

**Leaves covered:** 2.4.23–2.4.24 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 510
