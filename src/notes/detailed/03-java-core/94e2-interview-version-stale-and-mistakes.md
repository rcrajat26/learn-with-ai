# 03 Java Core — The version-stale claims and the expensive mistakes — INTERVIEW (§5.2, 5.2.2–5.2.4)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The trap index](94e-interview-trap-index.md) · Next: [The drills and the retention schedule](94f-interview-drills-and-retention.md)

Version-stale folklore is the most dangerous category of wrong answer in this
whole guide, for a reason none of the other categories share: it is
confidently held, it was once demonstrably correct, and the person asking the
question may still believe the old form themselves. A candidate who says
"generics are erased" sounds less confident than a wrong answer but is
harder to catch out than one who states, with total conviction, that
`substring` is O(1) because it shares the backing array — a fact that was
true for a decade and has been false since 7u6. The candidate who learned
Java from a book published in 2012 and never revisited the fundamentals is
penalised twice: once for the wrong answer, and again for not knowing there
was ever a change to track. This file is the antidote — ten claims that
flip a widely-repeated belief, and it names the exact release, the exact
JEP, and the sentence to say instead. The second half covers a different
kind of danger: mistakes that compile, pass code review, and pass every
test that does not specifically probe for them, and the five wrong answers
that lose an interview outright because they sound more correct than the
truth.

## D-137 — The version-stale claims table

**D-137** — Ten stale claims: what older material says, what is true in Java 21.

| What older material says | What is true in Java 21 | The release that changed it | JEP or bug id | How an interviewer will phrase it |
|---|---|---|---|---|
| `strictfp` forces reproducible floating point and is worth adding "to be safe" | No-op; `javac` emits `flags: (0x0000)`, identical to a plain method, and warns that the keyword is not required | 17 | JEP 306 | "What does `strictfp` do, and would you ever add it to new code?" |
| The string pool lives in PermGen and interning risks `OutOfMemoryError: PermGen space` | Pool objects moved to the ordinary Java heap; PermGen itself was removed two releases later | 7 (moved), 8 (PermGen removed) | JDK-6962931; JEP 122 | "Why did people used to fear calling `intern()`?" |
| `substring` is O(1) because the returned `String` shares the parent's backing array via `offset`/`count` | `substring` allocates a new array and copies; O(n) in the substring length | 7u6 | JDK-6924259 | "Is `substring` free? What used to make people think that?" |
| `+` on strings compiles to a hand-written `StringBuilder` chain | Compiles to a single `invokedynamic` call against `StringConcatFactory.makeConcatWithConstants` | 9 | JEP 280 | "What does `+` compile to, and does that change anything about loop concatenation?" |
| A private member accessed from a nested class goes through a synthetic package-private `access$000` forwarder | Direct `invokevirtual`/`getfield`, JVM-enforced nest membership, no synthetic bridge | 11 | JEP 181 | "How does a nested class read a private field of its enclosing class?" |
| Reflection can never touch a `final` field, or conversely, the `modifiers`-field trick always works | A plain instance `final` field can be set via `Field.set` after `setAccessible(true)`; `static final` still throws; the `modifiers`-field trick throws `NoSuchFieldException` on 21; a future JEP is expected to restrict the instance case further | 9 removed the `modifiers` trick's target class shape changes; JEP 500 pending, not yet shipped | JEP 500 (pending) | "Can you set a `final` field with reflection? Is that changing?" |
| The JVM's default charset for charset-less APIs is derived from the host locale | Fixed to UTF-8 on every platform for every charset-less API | 18 | JEP 400 | "Is `new String(bytes)` safe to use without specifying a charset?" |
| Helpful NullPointerException messages are an opt-in debugging feature | On by default; toggled by a `{manageable}` flag, live-adjustable with no restart | 15 (default-on); shipped opt-in in 14 | JEP 358 | "Are helpful NPE messages on by default? What flag controls them?" |
| `super()` (or `this()`) must always be the first statement in a constructor | Still true through this guide's Java 21 baseline. Relaxed in a later release to allow a validating prologue before the delegation — beyond this guide's 21 baseline, and still asked | 25 (relaxed) | JEP 513 (final); JEP 447/482/492 (previews) | "Can validation run before `super()`? Has that always been true?" |
| Inner classes can only declare `static final` constant members, never ordinary `static` fields or methods | Inner classes may declare non-constant `static` members, and nested records/enums/interfaces | 16 | JEP 395 | "Can an inner (non-static-nested) class have a `static` field?" |

### `strictfp`

Java 1.2 relaxed the JLS's default floating-point evaluation mode to
accommodate the x87 FPU, whose internal registers hold 80 bits regardless of
whether the program asked for `float` or `double`. Ordinary code was free to
keep every intermediate result at that extended width, which meant identical
source could produce different bits on different hardware. `strictfp`
applied to a class or method forced every intermediate back to strict
binary32/binary64 rounding, and `javac` recorded that choice as the
`ACC_STRICT` bit (`0x0800`) in the compiled method or class. JEP 306
("Restore Always-Strict Floating-Point Semantics," Java 17) made strict
evaluation the only mode on every platform, because SSE2 and its
equivalents everywhere else made strictness free rather than a costly
opt-in — there is nothing left for the keyword to opt into. Verified by
recompiling identical source under `--release 21` versus `--release 16`:
the `--release 16` class file still carries `ACC_STRICT` on the annotated
method; the `--release 21` class file carries `flags: (0x0000)`, identical
to the unannotated method, and `javac` additionally warns that the keyword
is not required as of release 17. The sentence to say: "`strictfp` forced
strict rounding back when the JLS permitted wider x87 intermediates; JEP
306 in Java 17 made strict evaluation the only mode, so the keyword compiles
but changes nothing, and I'd flag it for removal in review rather than add
it." Detail: `numbers-and-money/04b-internals-strictfp-strictmath-and-fma.md`.

### String pool in PermGen

Through Java 6 the `StringTable`'s `String` objects lived in PermGen, a
fixed-size native region separate from the ordinary heap, and PermGen had
no eviction mechanism for interned strings — a program that interned an
unbounded set of values (a naive canonicalisation pass over user input, for
example) eventually hit `OutOfMemoryError: PermGen space` regardless of how
much regular heap was free. JDK-6962931 moved the pool's `String` objects
onto the ordinary Java heap in Java 7, which by itself did not remove the
fear because the `StringTable` structure itself was still a fixed-size
native hash table. PermGen was removed entirely in Java 8 (JEP 122,
replaced by Metaspace), which is the release most people actually mean when
they say "the pool problem was fixed." On Java 21 the table holds weak
references, so an interned string with no other strong reference is
reclaimable by ordinary GC; what remains true post-fix is that the native
table itself has no eviction API and never shrinks, so pushing far more
entries into it than its 65,536-bucket default degrades every subsequent
`intern()` call and lengthens the table's full-GC walk — a real cost, just
not the one from the old folklore. The sentence to say: "the pool moved out
of PermGen in Java 7 and PermGen was removed in Java 8; on 21 interned
strings are ordinary, collectable heap objects, and the actual constraint
left is native table growth, not an OOM class specific to interning."
Detail: `strings/01b-the-string-pool.md`, `strings/03b-internals-stringtable-and-interning.md`.

### `substring` sharing

Through Java 6, `String` carried `offset` and `count` fields alongside a
shared `char[] value`, so `substring` returned a new `String` header
pointing at the *same* backing array with adjusted bounds — genuinely O(1)
regardless of the substring's length. The retention cost was the trap even
then: an 8-character reference sliced out of a 4,096-character statement
line kept the entire 4,096-character array reachable through the small
substring, roughly 8.2 KB pinned alive instead of the ~48 bytes the
substring's own content needed. JDK-6924259 removed `offset` and `count` in
7u6, making `substring` allocate a fresh array and copy — O(n) in the
substring's own length, with no hidden retention. This is a rare case where
the interview-losing version is not a mechanism trap but a workaround trap:
the classic `new String(s.substring(0, 8))` idiom, which forced a copy to
escape the sharing bug, is now pure waste on Java 21 because `substring`
already copies. Note the two common misdatings worth pre-empting: the fix
landed in 7u6, not in Java 8, and not in the base Java 7 release. The
sentence to say: "`substring` shared the parent's array and was O(1) through
Java 6; JDK-6924259 in 7u6 made it copy, O(n), specifically to stop small
substrings retaining large parents — and the old defensive `new
String(...)` wrapper is now redundant." Detail: `strings/01-basics.md`,
`strings/03-internals-string.md`.

### `+` compiling to `StringBuilder`

From Java 5 through Java 8, `javac` compiled every non-constant `+`
concatenation chain into a hand-rolled sequence of `StringBuilder`
allocation, repeated `append` calls, and a final `toString()` — visible
directly in `javap` output as `new StringBuilder`, `invokevirtual append`,
`invokevirtual toString`. JEP 280 ("Indify String Concatenation," Java 9)
replaced that with a single `invokedynamic` call site bound to
`StringConcatFactory.makeConcatWithConstants`, whose bootstrap method
builds a method-handle chain that computes the exact result length before
allocating anything — one allocation, no intermediate `StringBuilder`
object at all for a single expression. This does not rescue `+=` inside a
loop: each loop iteration is a distinct concatenation expression and
therefore a distinct call site, copying the whole accumulated string every
time, so `out += line` over 19.8M ledger entries stays O(n²) on Java 21
exactly as it was on Java 8 — the fix changed *how one expression*
compiles, not the complexity of accumulating across many expressions. The
sentence to say: "since Java 9, `+` compiles to `invokedynamic` against
`StringConcatFactory`, not a `StringBuilder` chain, but that only helps a
single expression — building a string across loop iterations with `+=`
still needs an explicit, pre-sized `StringBuilder`." Detail:
`strings/04-internals-stringbuilder-and-concat.md`,
`primitives-and-conversions/02d-string-concatenation.md`.

### `access$000` bridges

Before Java 11, a nested class reading a `private` member of its enclosing
class (or the reverse) could not do so directly, because the JVM's
access-control model at the time checked only class identity, not nest
membership, and `private` meant private to the exact class. `javac` worked
around this by widening the member's effective accessibility: it emitted a
synthetic, package-private static forwarder method named `access$000` (and
`access$100`, `access$200`, ... as more were needed) on the enclosing class,
and every nested-class access went through an `invokestatic` call to that
forwarder instead of touching the private member directly. The forwarder
was package-private rather than private specifically so the nested class,
compiled to its own class file, could call it — which is itself a real
widening of accessibility beyond what the source's `private` keyword
states, and was a known bytecode-level attack surface: anything else in the
same package could call `access$000` too. JEP 181 ("Nest-Based Access
Control," Java 11) introduced true nest membership at the JVM level —
`NestHost` and `NestMembers` class-file attributes, checked mutually — so a
nested class can now access a private member with a direct `invokevirtual`
or `getfield`, verified by the JVM against nest membership rather than
routed through a widened synthetic method. The sentence to say: "before
Java 11, private cross-nested-class access went through a synthetic
package-private `access$NNN` forwarder, which was itself a small
accessibility leak; JEP 181 gave the JVM real nest membership, so on 21 the
access is direct and there is no forwarder in the class file at all."
Detail: `inheritance-and-dispatch/04-internals-nested-classes.md`.

### Reflection on `final` fields

The folklore here runs in both directions and both are wrong. One version
insists `final` fields are reflection-proof; measured on JDK 21.0.7, a plain
instance `final` field with no compile-time constant initializer accepts
`Field.set` after `setAccessible(true)` and both the reflective and a
direct field read observe the new value — reflection can and does mutate an
ordinary `final` field. The other version insists the classic "clear the
`modifiers` field to force any final write" trick still works; it does not
— `Field.class.getDeclaredField("modifiers")` throws
`NoSuchFieldException: modifiers` on 21, because `java.lang.reflect.Field`
no longer exposes a field reachable by that name. What is actually true on
21, precisely: a plain instance `final` field with no constant initializer
can be set; a `static final` field throws `IllegalAccessException`
regardless; a record component's backing field throws
`IllegalAccessException` too, with a message that omits the word `static`,
which is the only text-level way to tell the two `IllegalAccessException`
cases apart. A pending change narrows this further: JEP 500 is targeting a
future release to begin restricting `Unsafe`-based final-field mutation,
with a carve-out planned specifically for deserialization libraries — state
this as **pending**, not as shipped, because it has not landed as of this
guide's Java 21 baseline. The sentence to say: "on 21, `Field.set` succeeds
on an ordinary instance `final` field but throws on `static final`; the old
`modifiers`-field bypass is gone; and JEP 500, still pending, plans to
restrict this further with an exception carved out for serialization." Detail:
`reflection/02c-final-fields-and-security-surface.md`.

### Default charset

Through Java 17, every charset-less API — the no-argument `new
FileReader`, `new String(byte[])`, the default `PrintStream` — resolved its
charset from the host's locale: UTF-8 on a typical Linux container,
`windows-1252` on a Windows laptop, `US-ASCII` under an empty `LANG`. This
made a payout-file read or a log write silently produce different bytes on
different machines running the identical code, and it is exactly why
"always specify the charset explicitly" was correct advice on every prior
release too. JEP 400 (Java 18) fixed the default to UTF-8 unconditionally
on every platform, for every charset-less API, with `-Dfile.encoding=COMPAT`
as the escape hatch back to the old locale-derived behaviour if a
migrating system genuinely needs it. One nuance worth stating precisely:
`Files.readString(Path)` was already UTF-8 by contract from its
introduction in Java 11 — the bug lived specifically in the older,
charset-less legacy APIs, not in every I/O path predating 18. The sentence
to say: "default charset was locale-dependent through 17 and became a
fixed UTF-8 on every platform in Java 18 under JEP 400 — but specifying the
charset explicitly was, and still is, correct on every release." Detail:
`strings/02b-text-and-encoding.md`,
`language-substrate/04a-internals-version-history-18-onward.md`.

### Helpful NPE off by default

JEP 358 ("Helpful NullPointerExceptions") shipped in Java 14 as an opt-in
feature, requiring `-XX:+ShowCodeDetailsInExceptionMessages` to produce a
message like "Cannot invoke `StakeSplit.bonusPortion()` because the return
value of `Reservation.split()` is null" instead of a bare `null` message.
JDK-8233014 flipped the default to on in Java 15, and it has stayed on by
default since. The flag's category is `{manageable}` — it can be toggled on
a live, running process through `HotSpotDiagnosticMXBean.setVMOption` or
the equivalent `jcmd VM.set_flag` command, with no restart, which is
unusual: most HotSpot flags are fixed at JVM launch. This matters
operationally, not just historically — if a helpful NPE message is
discovered leaking internal class, field, method, or (with `-g`/`-g:vars`)
local-variable names across a trust boundary, the flag can be flipped off
on the affected live process immediately, buying time to fix the actual
boundary problem without a redeploy. The sentence to say: "helpful NPE
messages shipped opt-in in 14 and became default-on in 15; the flag is
live-toggleable via the management interface, which is the actual lever if
one leaks internal names into a response body." Detail:
`exceptions/03d-internals-npe-messages-and-diagnostics.md`.

### `super()` must be first — beyond this guide's Java 21 baseline

Through this guide's Java 21 baseline this rule holds with zero exception:
a constructor body that does not open with an explicit `this(...)` or
`super(...)` invocation gets one silently inserted by the compiler, the
grammar (JLS §8.8.7) permits nothing before it, and any attempt to run
validation logic first — checking a `Money` amount's sign before calling
`super(accountId, position)` — is a compile-time error. This was the actual
motivation for a specific defensive idiom: making the constructor private,
validating in a static factory method, and calling the private constructor
only once the check passed, precisely because the constructor itself had
no earlier point to validate at. **JEP 513, "Flexible Constructor Bodies,"
finalised in Java 25** — three releases and roughly two years past this
guide's Java 21 target — permits a prologue of statements before the
delegating `super(...)`/`this(...)` call, provided the prologue does not
read `this` and does not return a value; ordering afterward runs prologues
bottom-up, then epilogues top-down. Mark this explicitly: this row is past
the Java 21 baseline, and it is still asked, often by an interviewer testing
whether a candidate has kept up with anything released after their
day-to-day Java version. The sentence to say: "on 21, nothing may precede
`super()` or `this()` in a constructor, full stop — that's why the
validate-in-a-static-factory idiom exists. Java 25's flexible constructor
bodies, JEP 513, relax this with a prologue that can validate before
delegating, but that's beyond 21." Detail:
`classes-and-initialization/01c-class-anatomy-and-constructors.md`,
`inheritance-and-dispatch/02-nested-classes.md`,
`language-substrate/04a-internals-version-history-18-onward.md`.

### Inner classes cannot have static members

Through Java 15, a non-static inner class could declare only compile-time
constant `static final` fields — the JLS's own justification was that a
non-static context has no single class-level storage location distinct
from any particular enclosing instance, so an ordinary mutable `static`
field would be ambiguous about which "static state" it belonged to. Trying
to declare a non-constant `static` field or a `static` method on an inner
class produced `error: Illegal static declaration in inner class ...` /
`modifier 'static' is only allowed in constant variable declarations` on
JDK 11 and earlier. JEP 395 was the records JEP for Java 16, but the same
release also relaxed this specific restriction as a related cleanup: inner
classes may now declare non-constant `static` members, and nested records,
enums, and interfaces, all of which are implicitly static regardless of
where they are nested. The mechanical reason this could finally be allowed
is unrelated to closures or capture at all — it is purely a namespacing and
initialization-ordering relaxation, not a change to how `this$0` or capture
works. The sentence to say: "inner classes were restricted to constant
`static final` members through Java 15; Java 16 lifted that as part of the
records-adjacent cleanup, so an inner class can now hold an ordinary
mutable `static` field or a `static` method." Detail:
`inheritance-and-dispatch/02-nested-classes.md`,
`language-substrate/04a-internals-version-history-18-onward.md`. Cross-linked
against the release timeline's own [D-129, "What changed in which
release"](language-substrate/04-internals-version-history.md) so the two
diagrams do not disagree — D-129 corroborates each release and JEP cited
in D-137 above.

## D-138 — The five most expensive real-world mistakes

**D-138** — The five mistakes that cost the most, and how each is detected.

| The mistake | The QuizStakes flow it breaks | The observable symptom | How you detect it | The fix |
|---|---|---|---|---|
| `double` for money | The bonus split on a stake reservation | A ledger that fails `debit == credit` by a fraction of a minor unit, or a stated bonus figure that doesn't match the sum of its parts | Sum a batch of `double` amounts and compare to the exact `BigDecimal` total; the naive `double` sum of 2.8M stakes of 4.20 is off by ~0.34 from the exact 11,760,000.00 | `BigDecimal` end to end for every `Money` field, `RoundingMode` stated explicitly at every split |
| Shared `SimpleDateFormat` | A batched `PaymentRun` formatting each withdrawal's settlement timestamp | Silently wrong timestamps on some rows, not exceptions — measured 74.8% of format calls wrong under 8-way concurrent load, versus 0.32% throwing | Load-test the exact call path with concurrent threads and assert on the *value*, not just the absence of an exception | `DateTimeFormatter` (immutable, thread-safe by construction) in place of `SimpleDateFormat` |
| `==` on boxed values or strings from I/O | A deposit reconciliation comparing a parsed `DEP-301 CAPTURED` status code against a constant | A comparison that works in every unit test and fails only in production, for specific inputs, with no exception | Vary the comparison's operand size past the `Integer` cache boundary (128), or source one operand from `ResultSet.getString`/JSON instead of a literal | `.equals()` / `Objects.equals()`, or a `StatusCode`/enum type the compiler enforces |
| Swallowed `InterruptedException` | A worker thread processing a `ReserveStake` call, cancelled during a graceful shutdown | The thread keeps running after cancellation was requested; `isInterrupted()` reads `false` even though a cancellation was issued | Request a shutdown and assert the specific worker thread actually stopped within a bounded time, not just that no exception surfaced | Propagate (`throws InterruptedException`) where the signature allows it, or restore the flag and return where it does not |
| `LocalDateTime` stored as an event timestamp | A settlement event's `postedAt` field on a `Movement` | Two clients in different time zones computing different, both "correct-looking," elapsed durations from the same stored value; a DST-boundary write that is ambiguous or does not exist | Store the same event across a DST transition and try to convert the stored value back to an unambiguous instant with no supplied zone | `Instant` for "it happened," or `ZonedDateTime` when the zone's future rule changes must be honoured |

### `double` for money

`double` cannot represent most decimal fractions exactly, because binary
floating point stores fractions in base 2 and `0.1 = 1/10` has a factor of
5 in its denominator with no finite binary expansion — the identical
mathematical shape as `1/3` having no finite decimal expansion. The measured
consequence at QuizStakes scale: summing 2,800,000 stake reservations of
4.20 each with a naive `double` accumulator gives `1.1759999999664538E7`
against the exact `11760000.00`, and a batch of 3,100 bonus grants of 42.42
sums to `131501.99999999543` instead of `131502.00`. The canonical failure
is the bonus split itself: a stake of 3.33 must split as 0.33 bonus + 3.00
cash, because the bonus consumption rule is `min(BONUS_AVAILABLE, 10% of
stake)` with the bonus portion rounding **down** to the minor unit and cash
covering the remainder. Rounding the other way gives 0.34 + 3.00 = 3.34,
which manufactures one extra cent of money that did not exist in the
stake — and a `double`-based computation of `0.10 * 3.33` does not even
reliably land on 0.33 before rounding is applied, because the multiplication
itself already carries binary-representation error.

```java
// Wrong: double loses the exact decimal representation before rounding even runs.
double stake = 3.33;
double bonusPortion = Math.floor(stake * 0.10 * 100) / 100; // may not be 0.33 for every stake value
double cashPortion = stake - bonusPortion;

// Right: BigDecimal with an explicit scale and RoundingMode at the point of the split.
BigDecimal stakeAmount = new BigDecimal("3.33");
BigDecimal bonusPortion = stakeAmount
        .multiply(new BigDecimal("0.10"))
        .setScale(2, RoundingMode.DOWN);           // 0.33 -- rounds down, never up
BigDecimal cashPortion = stakeAmount.subtract(bonusPortion); // 3.00 -- invariant: sums to the stake
```

Detail: `numbers-and-money/02-numbers-and-money.md`,
`numbers-and-money/02f-double-comparison-and-float-choice.md`.

### Shared `SimpleDateFormat`

`SimpleDateFormat` is not thread-safe because `format` and `parse` mutate a
shared, internal `Calendar` and `NumberFormat` scratchpad across several
non-atomic steps — one `format` call is a `setTime` followed by several
`calendar.get(field)` calls, and another thread's concurrent `setTime` can
land in any of the gaps between them. Measured across 6,400,000 checked
operations with eight concurrent workers on JDK 21.0.7: 2,873,198 calls
returned a silently wrong result against only 20,182 throwing an
exception — roughly 142 wrong results for every one that fails loudly, and
every wrong string is still shaped like a valid `yyyy-MM-dd'T'HH:mm:ss.SSS`
timestamp, so nothing downstream distinguishes it from a correct one by
inspection. Making the field `volatile` does not help, because the defect
is atomicity, not visibility — the reference to the shared formatter never
changes, only its internal state does. The QuizStakes flow this breaks
concretely is a batched `PaymentRun`: several worker threads formatting
settlement timestamps for a bank-withdrawal batch against a single shared
formatter instance, each writing whichever thread's in-flight `Calendar`
state happened to be live at the moment its `get` calls ran.

```java
// Wrong: one formatter shared across every worker thread in the PaymentRun.
final class PaymentRun {
    private static final SimpleDateFormat SETTLEMENT_FORMAT =
            new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS");

    String formatSettledAt(Date settledAt) {
        return SETTLEMENT_FORMAT.format(settledAt); // races every other worker's format/parse call
    }
}

// Right: DateTimeFormatter is immutable and thread-safe by construction, shared freely.
final class PaymentRun {
    private static final DateTimeFormatter SETTLEMENT_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS").withZone(ZoneOffset.UTC);

    String formatSettledAt(Instant settledAt) {
        return SETTLEMENT_FORMAT.format(settledAt); // measured 0 wrong results under identical load
    }
}
```

Detail: `date-and-time/02-date-and-time.md`,
`build-it/05d-concurrency-and-time-harnesses.md`.

### `==` on boxed values or strings from I/O

Two independent but identically-shaped traps. `Integer` and its siblings
cache boxed values in a fixed range — `-128..127` for `Integer`, per JLS
§5.1.7 — so `==` on two boxed values that both happen to fall in that range
returns `true` by cache reuse, and the identical comparison on values just
outside it returns `false`, even though `equals` would agree in both cases.
Every value in this bug's range passes silently. The parallel string trap
is broader: `==` on two `String`s compares identity, and every literal in
source code is the pooled instance, so tests built from literals always
agree with `equals` — while a value parsed from I/O (`ResultSet.getString`,
a JSON body, `Files.readString`, `split`, `substring`, `StringBuilder`, or
`invokedynamic` concatenation) is a freshly allocated object whose content
matches but whose identity does not. The QuizStakes flow this breaks is a
deposit reconciliation: comparing a card deposit's parsed status code
against the literal `"DEP-301 CAPTURED"` with `==` works in every unit test
that hard-codes the literal on both sides and fails in production against
every deposit whose status arrived over the wire.

```java
// Wrong: works for every literal-vs-literal unit test, fails against parsed I/O.
String parsedStatus = resultSet.getString("status"); // fresh allocation, not pooled
if (parsedStatus == "DEP-301 CAPTURED") {             // always false for a real row
    markCaptured(deposit);
}

Integer attemptCount = countFromDatabase(reservationId); // may exceed 127
if (attemptCount == MAX_ATTEMPTS) {                        // == on two Integers: identity, not value
    escalate(reservationId);
}

// Right: equals for value comparison; a StatusCode/enum type removes the trap at the type level.
String parsedStatus = resultSet.getString("status");
if (parsedStatus.equals("DEP-301 CAPTURED")) {
    markCaptured(deposit);
}

Integer attemptCount = countFromDatabase(reservationId);
if (attemptCount.equals(MAX_ATTEMPTS)) {
    escalate(reservationId);
}
```

Detail: `wrappers-and-boxing/01b-cache-coverage-and-reference-equality.md`,
`strings/01b-the-string-pool.md`.

### Swallowed `InterruptedException`

`InterruptedException` is not a failure report — it is a transferred
obligation to cancel, delivered by the JVM the next time an interruptible
call is reached after another thread requested cancellation via
`Thread.interrupt()`. Catching it and continuing with neither propagating
it nor restoring the interrupt flag makes cancellation invisible to
everything downstream: a later call to `isInterrupted()` reads `false`,
because the empty `catch` block consumed the one signal that the flag was
ever set. The QuizStakes flow this breaks is a worker thread processing a
`ReserveStake` call under a graceful-shutdown protocol that interrupts
in-flight workers: a worker with a swallowed `InterruptedException` keeps
running its current reservation loop indefinitely, or until it happens to
finish on its own, rather than winding down when asked. The two correct
responses depend entirely on what the enclosing method's signature allows:
propagate by declaring `throws InterruptedException` where that is
possible, or, inside a `Runnable`/`Callable`-shaped method that cannot
declare it, restore the interrupt status with `Thread.currentThread().interrupt()`
and return, so a caller further up the stack still observes that
cancellation happened.

```java
// Wrong: catches, logs, and continues -- the cancellation signal vanishes.
void processReservations(BlockingQueue<Reservation> queue) {
    while (true) {
        try {
            Reservation next = queue.take();
            settle(next);
        } catch (InterruptedException e) {
            log.warn("interrupted, continuing anyway", e); // isInterrupted() now reads false
        }
    }
}

// Right: restore the flag and return, since Runnable cannot declare a checked throws.
void processReservations(BlockingQueue<Reservation> queue) {
    while (!Thread.currentThread().isInterrupted()) {
        try {
            Reservation next = queue.take();
            settle(next);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // restore, so the caller can observe it
            return;                              // stop processing, honour the cancellation
        }
    }
}
```

Detail: `exceptions/02e-resources-interrupts-and-testing.md`.

### `LocalDateTime` stored as an event timestamp

`LocalDateTime` has no `toEpochMilli()` and no zero-argument `toInstant()`
— it is, by design, a calendar-and-clock reading with no fixed point on the
timeline attached, and converting it to one requires supplying a
`ZoneOffset` (`toInstant(ZoneOffset)`) or a full `ZoneId`
(`atZone(ZoneId).toInstant()`) from somewhere else. Storing it as an
event's "when it happened" field defers that missing zone information to
whoever reads the value later, and different readers can supply different
zones and get different, individually plausible, instants back. The
QuizStakes flow this breaks is a settlement event's timestamp on a
`Movement`: a `Movement.postedAt` typed as `LocalDateTime` looks complete
because its `toString()` already resembles a full timestamp, but it cannot
answer "how many seconds ago was this" without an externally-supplied zone,
and around a DST transition the same wall-clock reading is either
ambiguous (the autumn overlap, where `Europe/London` at `01:30` on the 2026
transition resolves to two valid offsets, `+01:00` and `Z`) or does not
exist at all (the spring gap, where `01:30` on the 2026 transition resolves
to zero valid offsets). Measured footprint difference reinforces the
architectural point rather than being the reason to avoid it: `Instant` is
24.2 bytes per instance, `LocalDateTime` 72.0 — three times larger for a
type that additionally cannot answer the one question a timestamp exists
to answer.

```java
// Wrong: looks like a timestamp, is not a point on the timeline.
record Movement(AccountId accountId, Money amount, LocalDateTime postedAt) { }

Movement settled = new Movement(accountId, amount, LocalDateTime.now()); // whose zone?
// Two readers in different zones "convert" this differently -- both look correct.

// Right: Instant for "it happened"; ZonedDateTime only when future rule changes must be honoured.
record Movement(AccountId accountId, Money amount, Instant postedAt) { }

Movement settled = new Movement(accountId, amount, clock.instant()); // unambiguous, zone-free
```

Detail: `date-and-time/02a-instant-local-and-zoned.md`,
`date-and-time/02e-clock-precision-and-storage.md`.

## The five answers that lose the interview

| The wrong answer | Why it sounds right | What is actually true | What to say instead |
|---|---|---|---|
| "Java passes objects by reference" | Mutating a passed object through a method parameter is visible to the caller, which matches the layperson's idea of "by reference" | Java always passes by value; for a reference type, the value copied is the *reference itself* — a distinct copy that happens to point at the same object | "Everything is pass-by-value; for objects, the reference is copied, so mutating through it is visible but reassigning the parameter never is — call-by-sharing, not by-reference." |
| "`final` makes it immutable" | `final` blocks reassignment, and reassignment is the mutation people picture first | `final` on a field constrains only the reference slot, never the referent; a `final List<Movement>` field can still have entries added to the same list | "`final` is one of five independent rules for immutability — it stops reassignment, not mutation of the referenced object; the other four rules do the rest." |
| "Checked exceptions are always better because the compiler forces handling" | Compile-time enforcement genuinely catches missing handling that documentation-only conventions miss | The platform's own newer APIs (streams, `java.time`, `Optional`) deliberately avoid checked exceptions, because they don't compose with `Function`/`Consumer` and tend to produce empty `catch` blocks once "acknowledge" and "handle correctly" diverge | "Checked exceptions are right when the immediate caller has a specific, actionable response — not just when the failure is abstractly recoverable; everything else, including all precondition violations, is unchecked." |
| "`String` is immutable, so `==` is fine" | The premise is true — `String` genuinely is immutable — and immutability sounds like exactly the property that would make identity comparison safe | Immutability guarantees content can't change after construction; it says nothing about whether two equal-content strings are the *same object* — most strings from I/O are not | "Immutability is not the same property as pooling; only pool-guaranteed operands are safe under `==`, and in practice that means never using `==` for string comparison — use `.equals()`." |
| "Generics are checked at runtime just like arrays" | Arrays genuinely do carry and check their element type at runtime (`ArrayStoreException`), so it's a natural analogy to reach for | Generic type arguments are erased at compile time; the JVM never sees `List<Money>`, only raw `List`, and any type safety at a narrowing point comes from a `checkcast` the *compiler* inserted, not from a runtime generics check | "Generics are erased — `List<Money>` and `List<Restriction>` are one runtime class. Type safety comes entirely from compile-time checking plus compiler-inserted `checkcast`s at narrowing points, never from a runtime generics check." |

### "Java passes objects by reference"

The precise and complete statement is: Java is always pass-by-value, and
for a reference-type argument, the value being copied is the reference
itself, not the object it points to. The demonstration that separates the
two claims: a callee that does `res.status = "VOIDED"` then reassigns
`res = new Reservation("REPLACED", 0)` leaves the caller's original
variable reading `VOIDED` — proof that the reassignment never crossed the
call boundary, because if it had, the caller would see `REPLACED`. The
field mutation *did* cross, because both the caller's variable and the
callee's parameter briefly point at the same object; the accurate name for
that behaviour is call-by-sharing. Say it exactly this way: "everything is
pass-by-value; for a reference type, the copied value is the reference, so
mutating through it is visible to the caller but reassigning the parameter
itself never is."

### "`final` makes it immutable"

`final` on a field is exactly one of five independent rules that together
constitute immutability, and it is the narrowest of the five: it prevents
the field from being reassigned to point at a different object after
construction, and it says nothing whatsoever about whether the object
currently referenced can be mutated through its own methods. A `private
final List<Movement> entries` field is a textbook case — `final` stops
`this.entries = someOtherList`, but any caller holding a reference to the
same list (handed out by an accessor with no defensive copy) can call
`entries.add(...)` and change what the object reports, with `final` doing
nothing to stop it. The other four rules — a constructor-time defensive
copy of every mutable argument, an accessor-time copy or wrap of every
mutable field, no method that changes observable state, and either a
`final` class or a private constructor with static factories — are what
actually close the remaining gaps. Say it exactly this way: "`final`
constrains the reference, not the referent; genuine immutability needs
defensive copies in and copies or views out on top of it."

### "Checked exceptions are always better"

The honest steel-manned case for checked exceptions is real: forcing every
caller to confront a failure mode at compile time catches gaps that
documentation-only conventions miss, and for an API whose only correct use
genuinely involves handling the failure — an identity-vendor client with a
p99 latency of 38 seconds against a 30-second watchlist timeout, where
ignoring the timeout is a live, frequently-triggered bug rather than an
edge case — that compile-time enforcement is a real correctness win. The
platform's own trajectory away from making this the default is equally
real: `Function`, `Consumer`, and `Predicate` declare no `throws` clause at
all, so any checked-throwing method plugged into `Stream.map` or
`CompletableFuture.thenApply` fails to compile outright, and the empirical
tendency once a checked exception's only remaining option at a call site is
an empty `catch` block is exactly the outcome checked exceptions were meant
to prevent. The actual design test is narrower than "recoverable or not":
does the *immediate* caller — the specific frame that would write the
`catch` — have a specific, actionable response available right there. Say
it exactly this way: "checked exceptions are right when the immediate
caller has something specific to do about the failure, not merely when the
failure is recoverable somewhere in the system; that's why `LedgerImbalanceException`
is unchecked even though a ledger imbalance is, in the loosest sense,
eventually fixable by a human."

### "`String` is immutable so `==` is fine"

The premise is entirely true and the conclusion does not follow from it.
Immutability is a guarantee about a single object's content never changing
after construction; it says nothing about whether two different
`String` objects with equal content are, in fact, the *same* object.
Every string literal in source code does resolve to the single pooled
instance for that content, which is exactly why `==` "works" in every test
built from literals on both sides and creates a false sense that the
property generalises. It does not survive contact with I/O: a value parsed
from `ResultSet.getString`, a JSON body, `Files.readString`, `split`,
`substring`, a `StringBuilder`, or `invokedynamic` concatenation is a fresh
object every time, regardless of how many times the same content has been
seen before, and `==` against it returns `false` even though `.equals()`
would return `true`. Say it exactly this way: "immutability and pooling are
different properties — immutability guarantees content, pooling
guarantees identity for equal content, and only literals and a few
JLS-mandated cases get pooling automatically. Use `.equals()`; never `==`."

### "Generics are checked at runtime"

The array analogy is the trap: arrays genuinely do carry their element
type at runtime and throw `ArrayStoreException` on a mismatched store,
which trains the intuition that generics work the same way. They do not.
JLS §4.6 erasure replaces every parameterized type with its raw type and
every unbounded type variable with `Object` before the class file is even
produced — `Repository<CashEntry>`'s runtime descriptor is just
`Repository`, and the JVM never has a `List<Money>` versus `List<Restriction>`
distinction to check, because both compile to the identical runtime class
`List`. Whatever type safety exists at a point where an erased value is
narrowed back to something specific — the assignment `CashEntry entry =
repo.find(id)` — comes from a `checkcast` the *compiler* inserted at that
exact call site, based on the compile-time type argument the source
declared; there is no generics-aware runtime check anywhere in the JVM
itself. Say it exactly this way: "generics are erased, not reified —
`List<Money>` and `List<Restriction>` are one runtime class, and any
narrowing safety comes from a compiler-inserted `checkcast` at the call
site, never from the JVM checking a type parameter that no longer exists
at runtime."

---

**Leaves covered:** 5.2.2–5.2.4 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-137, D-138 (both Markdown tables)
**Target version:** Java 21 LTS
**Lines:** 633
