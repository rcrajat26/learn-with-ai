# 03 Java Core — Part 2 interview wrap-up — INTERMEDIATE (§2.1–§2.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](00-index.md)
Previous: [Part 1 interview wrap-up](90-interview-basics.md) · Next: [Part 3 interview wrap-up](92-interview-internals.md)

## Summary table

| Section | What it owns | The one thing that gets asked | Where it is written |
|---|---|---|---|
| §2.1 Cost model | Per-operation nanosecond bands, escape analysis, JIT elimination, JVM flags that govern all of it | "Is this micro-optimisation real or noise" — defend a number with a measurement, not folklore | [Cost model](cost-model/02-master-cost-table.md) |
| §2.2 String performance and text | `String` concatenation strategy, `StringBuilder` growth, regex compilation cost, charsets, code points | Why `+=` in a loop is quadratic and `Pattern.compile` inside a method is a leak of CPU, not memory | [Performance and text](strings/02-performance-and-text.md) |
| §2.3 Immutability design | The five rules, defensive copy in/out, `List.copyOf` vs `unmodifiableList`, `final`-field freeze | Copy-in depth must match mutability depth — a shallow copy of a two-hop-mutable object is still mutable | [Immutability](immutability-and-design/02-immutability.md) |
| §2.4 Numbers and money | `BigDecimal` structure, scale vs precision, rounding modes, `double` unsuitability for money | Why `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is `false` while `compareTo` is `0` | [Numbers and money](numbers-and-money/02-numbers-and-money.md) |
| §2.5 Date and time | `java.time` type map, `Instant`/`LocalDateTime`/`ZonedDateTime`, `Duration` vs `Period`, DST gaps and overlaps | Which type survives a DST transition and which one silently drifts by an hour | [Date and time](date-and-time/02-date-and-time.md) |
| §2.6 Exceptions in practice | Checked-vs-unchecked design test, exception hierarchies, translation at boundaries, logging discipline | The design test is "can the immediate caller act on it", never "is this recoverable in the abstract" | [Exceptions in practice](exceptions/02-in-practice.md) |
| §2.7 Generics in anger | PECS, wildcard vs type variable, type tokens, generic arrays, self-types, migration/erasure at the API surface | When to reach for a wildcard, a named type variable, or a `Class<T>` witness, and why they are not interchangeable | [Generics in anger](generics/02-in-anger.md) |
| §2.8 Copying and composite equality | Shallow vs deep copy, `clone()`'s four failure modes, copy constructors, `Comparable`/`Comparator`, JPA equality traps | Why `clone()` is close to unusable on your own types and a copy constructor is not | [Copying and composite equality](objects-equality-and-lifecycle/02-copying-and-composite-equality.md) |
| §2.9 Object lifecycle and references | GC roots, strong/soft/weak/phantom references, `Cleaner`, `finalize()`'s deprecation, `ThreadLocal` leaks | The exact clear-then-enqueue order for soft/weak versus phantom, and why it matters for cleanup correctness | [Lifecycle and references](objects-equality-and-lifecycle/03-lifecycle-and-references.md) |
| §2.10 Serialization | Default protocol mechanics, magic methods, `Externalizable`, records' serial form, gadget-chain risk, filters | Why deserialization bypassing the constructor is the whole security problem, and how records close that hole | [Serialization](serialization/02-serialization.md) |
| §2.11 Null discipline | Collection null tolerance, `Optional`'s correct position, `orElse` vs `orElseGet`, null-object pattern, NPE diagnostics | `Optional.orElse(T)` evaluates its argument unconditionally — the eager-vs-lazy trap every reviewer should catch | [Null discipline](null-discipline/02-null-discipline.md) |
| §2.12 Reflection | `Class` identity, access checks, `MethodHandle`, proxies, generic-signature survival at runtime, final-field mutation | The cold-call tax: first `Method.invoke` costs ~14,000× a direct call, warmed costs ~4.6× | [Reflection](reflection/02-reflection.md) |
| §2.13 Pass-by-value | The single unifying rule, call-by-sharing terminology, copy-in for mutable parameters, varargs, `final` parameters | The one program that proves Java has no reference parameters, and why the folklore survives anyway | [Pass-by-value](immutability-and-design/03-pass-by-value.md) |
| §2.14 Design idioms | Static factories, telescoping-constructor failure, builders, four singleton forms, utility-class construction | Why the holder-class idiom needs no `volatile` and DCL does | [Design idioms](immutability-and-design/04-design-idioms.md) |
| §2.15 Which construct | The decision tables: record vs class vs enum, interface vs sealed vs abstract class, exception vs `Result`, money in domain vs on the wire | The two ordered questions that decide checked-vs-unchecked, and why frequency is not one of them | [Which construct](immutability-and-design/05-which-construct.md) |

## The twenty facts of Part 2

| Fact | Why it is true | Section |
|---|---|---|
| `"CLIENT_" + "BONUS_RESERVED"` costs 0.0755 ns/op, 23× cheaper than the same expression with one non-constant operand | `javac` constant-folds it at compile time (JLS 15.29) — nothing runs at C2 at all | §2.1 |
| A non-escaping 24-byte allocation costs 0.30–0.56 ns, but the same object forced to escape costs 4.4 ns | Escape analysis proves the object never leaves the method and elides the allocation entirely; escaping defeats the proof | §2.1 |
| `stake += "…"` in a loop is O(n²) copies in every Java version, but a single `+` expression compiles to `invokedynamic makeConcatWithConstants` (Java 9+) | The loop form allocates and copies on every iteration; the single-expression form is planned once, at one exact-size array | §2.2 |
| `List.copyOf` never sees a source list's later writes; `Collections.unmodifiableList` does | `copyOf` (Java 10) makes a genuine copy; `unmodifiableList` (Java 1.2) wraps the same backing list as a read-only view | §2.3 |
| `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is `false`, but `.compareTo(...)` is `0` | `equals` compares scale before it ever inspects the significand; `compareTo` ignores scale entirely | §2.4 |
| A 3.33 stake splits as 0.33 bonus + 3.00 cash, never 0.34 + 3.00 | The bonus portion always rounds `DOWN`; rounding the other way manufactures 0.01 of money that did not exist | §2.4 |
| `LocalDate.of(2026,1,31).plusMonths(1)` gives `2026-02-28`, and two chained `plusMonths(1)` calls land three days away from one `plusMonths(2)` | `plusMonths` clamps to the last valid day of the target month rather than overflowing; each hop clamps independently | §2.5 |
| `ZonedDateTime.of` on a DST spring-forward gap never throws; on an autumn overlap it silently picks the earlier of two valid offsets | Both are engineering defaults, not exceptions — `getValidOffsets` returns `[]` for a gap and two entries for an overlap, and the API resolves rather than fails | §2.5 |
| `Objects.requireNonNull(x)` throws `NullPointerException`, never `IllegalArgumentException`, for a null argument | Convention fixed since Java 7's `Objects.requireNonNull`; verified against the JDK 21.0.7 source, which throws `NullPointerException` directly | §2.6 |
| A lambda body that throws `SQLException` fails to compile inside `Function<T,R>` | `Function.apply` declares no `throws`; this is the ordinary catch-or-declare rule applied to the functional interface's single method, not a lambda-specific restriction | §2.6 |
| A type that appears in a method's return type should never be a wildcard | A wildcard return gives the caller an opaque handle it cannot name or act on; a named type variable is required whenever the type must be referenced again | §2.7 |
| `(T[]) new Object[n]` compiles with only a warning for unbounded `T` but throws `ClassCastException` immediately when `T extends LedgerEntry` | The cast's erasure is `Object[]` in the unbounded case (a no-op `javac` elides) and the bound's array type in the bounded case, which a plain `Object[]` genuinely is not | §2.7 |
| `Object.clone()` never calls a constructor and copies shallowly by default | Fields are set "as if by assignment" via `Object`'s native implementation, bypassing every invariant check the real constructor would run | §2.8 |
| `PhantomReference.get()` always returns `null`, on every JDK version | Its whole purpose is post-mortem cleanup notification via a `ReferenceQueue`, never re-access to the referent — unlike soft/weak, which clear the referent and only then enqueue it | §2.9 |
| Deserializing a plain `Serializable` class bypasses its constructor and can write `final` fields directly; deserializing a record invokes the canonical constructor | The default protocol allocates via a synthesized constructor chaining to the first non-serializable superclass and sets fields by reflection; a record's spec-mandated serial form routes through its real constructor instead, so compact-constructor validation runs | §2.10 |
| `Optional.orElse(T)` evaluates its argument unconditionally, even when the `Optional` is present | JLS 15.12.4 evaluates the argument expression before the call; `orElseGet(Supplier)` defers evaluation to the empty case only | §2.11 |
| The first cold `Method.invoke` call costs roughly 13,791 ns; the warmed steady state is ~4.5 ns/op | The JDK generates a bytecode accessor for a reflected member once, on first invocation; every subsequent call reuses it — the tax is per-member, not per-call | §2.12 |
| Assignment to a reference parameter is invisible to the caller; mutation through it is visible | `astore_n` rewrites this frame's local slot only; a mutating call like `putfield` writes the one shared heap object both caller and callee can see — Java is always pass-by-value, and "call-by-sharing" is the accurate name for the reference case | §2.13 |
| The holder-class singleton idiom needs no `volatile` on its field | `JVMS 5.5` guarantees the JVM's own per-class initialization lock supplies the happens-before edge; after initialization the read compiles to a plain `getstatic` | §2.14 |
| `Money` is a `BigDecimal` at scale 2 inside the domain but a minor-unit `long` on the wire and in the database | The domain needs exact decimal arithmetic with rounding-mode control; the wire and `NUMERIC(19,4)` column need a fixed, unambiguous integer representation with one conversion class at the boundary | §2.15 |

---

## Interview Q&As

### "Why can't you just use `double` for money, and what does `BigDecimal` actually fix?"

`double` is IEEE 754 binary floating point, and most decimal fractions — including 0.1 — have no finite binary expansion, the same way 1/3 has no finite decimal one. `0.1 + 0.2` prints `0.30000000000000004` because the bits stored for 0.1 and 0.2 are already off by a tiny amount before the addition even runs.

That error doesn't stay tiny at scale. I've watched this drift on QuizStakes-shaped volumes: summing 2,800,000 stake reservations of 4.20 naively drifts to `1.1759999999664538E7` against an exact `11,760,000.00`, and summing 3,100 bonus grants of 42.42 lands on `131501.99999999543` against an exact `131502.00`. Neither error is close to zero, and neither is predictable — they depend on the exact sequence of additions.

`BigDecimal` fixes this by storing an exact unscaled integer plus a separate scale — `value = unscaledValue × 10^(−scale)` — so `3.33` is stored as exactly the integer `333` at scale 2, with no approximation anywhere.

Constructing it correctly matters just as much as using it: `new BigDecimal(0.1)` does *not* fix anything, because it captures the exact 55-digit binary value of the `double` you already had — `0.1000000000000000055511151231257827021181583404541015625` — so the only correct way to get money into a `BigDecimal` is from a `String` or a minor-units `long`, never from a `double` literal or variable.

```java
BigDecimal stake = new BigDecimal("3.33");
BigDecimal bonusAvailable = new BigDecimal("0.33");
BigDecimal bonusRate = stake.multiply(new BigDecimal("0.10"));
BigDecimal bonusPortion = bonusAvailable.min(bonusRate)
        .setScale(2, RoundingMode.DOWN);          // 0.33 — never rounds up
BigDecimal cashPortion = stake.subtract(bonusPortion); // derived, never rounded separately
// bonusPortion=0.33, cashPortion=3.00 — sums exactly to 3.33
```

The follow-up an interviewer usually asks next is "why derive the cash portion by subtraction instead of rounding it too?" — because rounding both portions independently is exactly how you manufacture money: `0.335` split naively could round to `0.34` bonus and `3.00` cash, an invariant-violating `3.34` total. Deriving one side by subtraction is the only way to guarantee the two sum exactly to the stake. And two more traps worth naming unprompted: `BigDecimal.equals` compares scale, so `2.00.equals(2.0)` is `false` even though `compareTo` returns `0` — always compare money with `compareTo`, never `equals`, and never rely on `HashSet` membership without normalizing scale first.

### "When do you reach for `Instant` versus `ZonedDateTime`, and what actually breaks across a DST transition?"

The organizing question is whether you need a point on the timeline or a calendar reading with no timeline position at all. `Instant` is nanosecond-resolution UTC — the right type for "this ledger entry was posted at this exact moment," stored in a `TIMESTAMP WITH TIME ZONE` column that normalises to UTC on write. `LocalDate`/`LocalDateTime` carry no zone whatsoever — there is no zero-argument `toInstant()` on `LocalDateTime`; you must supply a `ZoneOffset` or call `atZone(ZoneId)` before it can become a point on the timeline. `ZonedDateTime` is the one type whose arithmetic actually respects daylight saving, which makes it the right choice for a future scheduled event like a `PaymentRun` window — it carries the region, not just a fixed offset, so it re-resolves correctly against future rule changes.

The place this breaks is `Duration` versus `Period`. `Duration.ofDays(1)` is always exactly `PT24H`, full stop — it measures elapsed seconds and nanos. `Period.ofDays(1)` means "the same wall-clock time, one calendar day later," and its actual elapsed length changes across a spring-forward or fall-back boundary. On `Europe/London` in 2026, the spring gap runs `01:00Z` to `+01:00` and the autumn overlap runs `02:00+01:00` back to `Z`, each a one-hour jump measured directly against the tzdb rules:

```java
ZoneId london = ZoneId.of("Europe/London");
LocalDateTime gapLocal = LocalDateTime.of(2026, 3, 29, 1, 30);
ZonedDateTime resolved = ZonedDateTime.of(gapLocal, london);
System.out.println(resolved); // 2026-03-29T02:30+01:00[Europe/London] — never throws

Instant beforeGap = ZonedDateTime.of(gapLocal, london).minusHours(24).toInstant();
Instant afterOneDayLater = beforeGap.plus(Duration.ofDays(1)); // exactly 24h later
```

Critically, `ZonedDateTime.of` never throws on either the gap or the overlap: on a gap it silently shifts the local time forward past the missing hour, as shown above (`01:30` becomes `02:30+01:00`, not an exception), and on an overlap it silently picks the *earlier* of the two valid offsets unless you call `withLaterOffsetAtOverlap()` explicitly.

The interviewer's natural follow-up is "so what actually breaks in production" — and the answer is a reconciliation or scheduling job that computes a window using `plusHours(24)` when it meant "the same time tomorrow," or `plusDays(1)` when it meant "24 hours later." Those two calls diverge by exactly one hour twice a year, the code compiles and passes every test that doesn't cross a DST boundary, and the bug only shows up as a one-hour discrepancy in a settlement window on exactly two calendar days a year.

### "You have a `PaymentRun` that's supposedly immutable, but an audit shows a field changed after construction. Walk me through how you'd find the bug."

Immutability in Java is not a keyword — it's five separate rules, and violating any one of them reopens the object to mutation even though every field is `private final` and there's no setter in sight. I'd walk them in order. First, the class itself should be `final` or have a private constructor, so no subclass can reintroduce mutable state or override a method to break an invariant. Second, every field must be `private final` — but `final` on a *reference* field only means the reference is never repointed; it says nothing about the object it points to.

That gap between rule two and rule four is almost always where the bug lives:

```java
public final class PaymentRun {
    private final List<LedgerEntry> entries;

    public PaymentRun(List<LedgerEntry> entries) {
        this.entries = entries;              // BUG: aliases the caller's list
        // this.entries = List.copyOf(entries);  // fix — real defensive copy
    }

    public List<LedgerEntry> entries() {
        return entries;                       // BUG: leaks the mutable backing list out
        // return List.copyOf(entries);        // fix, if the field itself stayed mutable
    }
}
```

If the constructor stores the caller's `List<LedgerEntry>` directly, the caller still holds a live handle and can mutate it after the constructor returns, and the field being `final` does nothing to stop that — `List.copyOf(entries)` is the fix, not `Collections.unmodifiableList(entries)`, because `copyOf` makes a genuine copy that never observes later writes to the source, while `unmodifiableList` is a live view that does.

The mirror bug sits on the way out: rule five requires the accessor to return a copy or an immutable view of any still-mutable field, and `return this.entries;` on a plain `ArrayList` hands every caller a mutable alias into the object's internals.

There's a subtler third failure an audit sometimes surfaces: even with correct copy-in and copy-out, if the constructor calls an overridable method before every field is set — including implicitly, via a superclass constructor dispatching to a subclass override — that method runs against a half-initialized object, and a reader on another thread can observe a `final` field still at its default value. The fix there is a constructor that only calls `private`, `static`, or `final` methods, ever.

### "How do you decide whether a new exception type should be checked or unchecked?"

The test is not "is this recoverable" in the abstract — it's "can the *immediate* caller do something specific about it, and will it." If yes, checked; if the caller can only log and abort, or the failure is really a bug — a violated precondition, a programming error — it's unchecked. The strongest real case for checked is an API whose only correct use involves handling the failure, like a PSP timeout with a genuine retry-or-fallback decision at the exact call site.

Three forces push the JDK itself away from checked exceptions in modern APIs, and I'd name all three unprompted because together they explain why `java.time`, `Optional`, and the `Stream` API avoid them entirely. First, no composition with lambdas: `Function<T,R>.apply` declares no `throws`, so a lambda body that throws a checked exception fails to compile inside it —

```java
Function<PaymentIntent, ReceiptRef> submit = intent -> {
    return paymentGateway.submit(intent); // if submit() throws SQLException:
    // error: unreported exception SQLException; must be caught or declared to be thrown
};
```

— and there's no clean fix short of wrapping it in an unchecked type (the JDK's own precedent is `UncheckedIOException`) or a custom `ThrowingFunction` that won't plug into `Stream.map` anyway.

Second, a checked exception low in a call stack pollutes every intermediate signature up to the top, coupling callers to an implementation detail they don't actually care about. Third, the compiler only demands catch-or-declare, not correct handling — it can't stop an empty catch block, so the "forced handling" benefit is weaker than it looks.

When I design a hierarchy, I keep one unchecked base per bounded context — `FundsException`, `ComplianceException`, `LifecycleException` — rather than one type per error code (too granular to catch as a category) or one root for the whole application (`catch (QuizStakesException e)` catching every category indiscriminately). Each base is `abstract`, so nobody can throw a bare, uncategorized instance, and I always pass the caught lower-level exception as the `cause` when translating across a layer boundary — dropping the cause loses the original type, the stack frames, and any structured data the instant the `catch` block exits.

Spring's own persistence layer is a real-world example of this translation discipline done at scale: `SQLExceptionTranslator` converts a checked `SQLException` into an unchecked `DataAccessException`, with concrete subtypes like `DuplicateKeyException` for a unique-constraint violation and `CannotAcquireLockException` for contention — the checked JDBC exception never crosses into application code at all. It's a best-effort translation, driven by a vendor-specific SQLState table, so an untranslated case still falls through to `UncategorizedSQLException` rather than silently losing information. And one convention worth citing precisely: since `Objects.requireNonNull`, a null-argument violation throws `NullPointerException`, not `IllegalArgumentException` — `IllegalArgumentException` is for an argument that is present but wrong, `IllegalStateException` for an argument that's fine but the receiver can't honour the call right now.

### "Someone tells you Java passes objects by reference. What's wrong with that, and what's the one example that proves it?"

Java is always pass-by-value — no exceptions — and this is normative text in JLS §8.4.1: a parameter is a local variable initialized by the value of the argument. For a reference type, what gets copied is the *reference itself*, not the object it points to; the accurate name for the resulting behavior is call-by-sharing, because caller and callee end up sharing one heap object through two independent reference copies.

```java
static void swap(Reservation a, Reservation b) {
    Reservation tmp = a;
    a = b;
    b = tmp;               // astore_n — rewrites only this frame's local slots
}
// swap(r1, r2) leaves the caller's r1 and r2 completely unchanged

static void settle(Reservation r) {
    r.markSettled();        // putfield — writes the one shared heap object
}
// settle(r1) IS visible to the caller — r1.isSettled() now true
```

`swap` is not just ineffective, it's *unexpressible* any other way — no bytecode instruction reaches into another frame's local variables, so reassigning a parameter can never propagate back to the caller. `settle` mutates through the shared reference and that mutation is visible everywhere, because both frames' reference copies point at the identical heap object.

The folklore survives because people watch `settle`-style mutation work and conclude "pass by reference," without separating it from the `swap`-style reassignment that provably does not work.

The follow-up worth pre-empting: does `final` on a parameter change anything here? No — `final` only blocks reassigning the parameter *inside the method body*; it has zero effect on the caller, the method's descriptor, overload resolution, overriding, or whether the referenced object itself can be mutated. And if you genuinely need to return two values out of one call, the idiomatic fix is a record like `SwapResult(Reservation first, Reservation second)`, never an out-parameter array.

### "What makes Java's default serialization dangerous enough that you'd tell a team never to use it for persistence?"

The core danger is structural, not a patchable bug: `readObject()` loads classes, allocates the target object via a synthesized constructor that bypasses your real one entirely, and runs `readObject`/`readResolve` hooks — all before your code gets any chance to validate anything. I've reproduced exactly what that bypass allows: a plain `Serializable` class holding a two-field split invariant that should always sum correctly comes back as `Split2[34+300=333]` after a forged byte stream, a value the real constructor would have rejected outright, because the reflective field-setting path used at deserialization skips it completely.

```java
// A forged stream can set final fields directly, bypassing this constructor:
public Split2(int bonusMinor, int cashMinor) {
    if (bonusMinor + cashMinor != stakeMinor) throw new IllegalArgumentException();
    this.bonusMinor = bonusMinor;
    this.cashMinor = cashMinor;
}
```

Two more facts make this worse than "a bug I could catch in review." The class name embedded in the stream is attacker-controlled text, resolved before any `serialVersionUID` check even runs. And a "gadget chain" needs no single buggy class at all — it's a composition of ordinary classes already on your classpath, chained by an attacker to reach arbitrary code execution once your process deserializes their bytes; `ysoserial` is the public tool cataloguing known chains, useful for auditing your own classpath defensively.

The JDK's mitigation, `ObjectInputFilter`, defaults to `null` on JDK 21 — nothing is rejected unless a team explicitly configures a filter, and even a configured filter covers only `java.io.ObjectInputStream`, not Jackson, SnakeYAML, or Kryo.

Records are structurally safer for one specific reason worth citing: their spec-mandated serial form invokes the canonical constructor with the stream's values, so the identical forged split against an equivalent record throws `InvalidObjectException` instead of silently succeeding. On the mitigation side, `ObjectInputFilter` itself has real limits worth naming: it can be scoped per-stream, process-wide via `jdk.serialFilter`, or composed through a filter factory (`jdk.serialFilterFactory`, JDK 17+, JEP 415) so a per-stream filter doesn't just silently overwrite the process-wide one — but even a correctly configured filter only ever inspects the class being resolved, never field values or what an already-allowed class's own code does once it's let through. That's why the rule I'd actually give a team is simpler than any mitigation: no Java serialization for persistence or wire formats — JSON or Protobuf — with the caveat that polymorphic JSON type handling can reintroduce the same code-execution class of risk if it isn't allow-listed too.

### "What's wrong with `orElse(computeExpensiveDefault())`, and where else does this eager-versus-lazy trap show up?"

`Optional.orElse(T)` takes an already-evaluated value as its argument, and JLS 15.12.4 evaluates argument expressions before the method is even called — so `orElse(computeExpensiveDefault())` runs `computeExpensiveDefault()` on every single invocation, present or empty.

```java
Optional<Bonus> active = bonusService.findActive(clientId);
Bonus fallback = active.orElse(bonusService.grantDefaultBonus(clientId));
// grantDefaultBonus() runs EVERY time, even when active is already present

Bonus correct = active.orElseGet(() -> bonusService.grantDefaultBonus(clientId));
// only runs when active is empty
```

If the fallback is a constant already sitting in a field — `orElse(Money.ZERO)` — this is completely fine and arguably clearer. But a database lookup, a fresh allocation, or anything with a side effect belongs behind `orElseGet(Supplier<T>)`.

The same eager/lazy split shows up in logging: `log.debug("x " + expensiveToString(v))` builds the string unconditionally even when `DEBUG` is disabled, while `log.debug("x {}", v)` defers formatting into the logging framework, which only touches it once the level check has already passed.

The interviewer's natural next question is "where should `Optional` actually live?" — and the answer is: a method's return type only, never a field (it isn't even `Serializable` — `Optional.class.getInterfaces()` is empty), never a parameter (it just pushes the null-handling problem onto the caller, who still has to unwrap a possibly-empty `Optional`), and never a collection element (a missing map entry already expresses absence, via `getOrDefault` or `computeIfAbsent`). One asymmetry worth naming unprompted: `Optional.of(null)` throws immediately, while `Optional.ofNullable(null)` quietly produces an empty `Optional` — the API forces a decision, at the call site, about whether null was ever expected.

The same eager-vs-lazy pair exists outside `Optional` too, and I'd mention it to show the pattern generalises: `Objects.requireNonNullElse(value, dflt)` is the eager form — `dflt` itself must never be null, or it throws — while `Objects.requireNonNullElseGet(value, Supplier)`, added in Java 9, defers construction of the default to only the null case, exactly mirroring `orElse` versus `orElseGet` on `Optional`.

### "You need to inspect a private field for a mapper library. What does that actually cost, and what's the one call that makes it expensive?"

Reflection has two very different cost profiles depending on whether you're measuring metadata lookup or invocation, and conflating them is the single most common mistake in this area. A warmed `Method.invoke` call costs about 4.5 ns per operation — roughly 4.6× a direct virtual call, nowhere near the "orders of magnitude slower" folklore — because after enough invocations the JVM generates a real bytecode accessor for that specific member and reuses it. The number that actually matters is the *first* cold call: a single measured sample at roughly 13,791 ns, close to 14,000× a direct call, because that accessor generation happens once per member, the moment it's first invoked reflectively.

```java
// Wrong: resolves the Method object and pays part of the cost on every call
for (Client c : batch) {
    Method getter = Client.class.getDeclaredMethod("balance");
    getter.invoke(c);
}
// Right: resolve once, reuse the warmed accessor
Method getter = Client.class.getDeclaredMethod("balance");
getter.setAccessible(true);
for (Client c : batch) getter.invoke(c);   // ~4.5 ns/op once warmed
```

That's exactly why a mapper library reflecting over the same fields on every request, instead of caching the resolved `Field`/`Method` handles once at startup, pays the cold-call tax needlessly on a hot path — and every `getField`/`getDeclaredField` call also allocates a fresh array, so the resolve-once discipline matters even after warm-up.

If raw speed matters more than the metadata introspection, a `static final MethodHandle` with `invokeExact` measures at roughly 0.80 ns — indistinguishable from a direct call, because the JIT can constant-fold a `static final` handle; the identical handle in a non-static field costs about 3.1× more, since it can no longer be treated as a compile-time constant.

On module boundaries, the follow-up question is usually "does `setAccessible(true)` always work" — no: it succeeds unconditionally on your own classes but throws `InaccessibleObjectException` against JDK-internal fields unless the owning module `opens` that package or you pass `--add-opens`; the old `--illegal-access` escape hatch was removed in Java 17 and now only prints an ignored warning.

### "What's a type token, and why can't you get `List<Money>` back out of a live `List` at runtime?"

Generics use erasure — `List<Money>` and a raw `List` compile to exactly the same class-file descriptor, `Ljava/util/List;`, which is precisely how a `.class` file compiled against generics stays binary-compatible with pre-1.5 code under JLS 13. The practical consequence: a live instance never carries its type argument. `list.getClass()` reports bare `ArrayList`, with no trace of `Money` anywhere, because the type argument only ever existed in the compiler's own bookkeeping.

```java
Class<Money> moneyToken = Money.class;
Object payload = fetchUntyped();
Money m = moneyToken.cast(payload);   // real check, throws ClassCastException here, names both types

// versus an unchecked cast — compiles, fails silently, breaks somewhere else later:
@SuppressWarnings("unchecked")
Money m2 = (Money) payload;           // no checkcast inserted at this line at all
```

`Class.cast` performs a real check inside its own body and throws immediately at the boundary where untyped data enters typed code — strictly better than an unchecked `(T) x` cast, which inserts no `checkcast` here at all and can fail far away, wherever the compiler had to insert its own implicit cast to satisfy some more specific static type.

What *does* survive erasure is a declared *signature*: a field or method's `Signature` attribute is emitted unconditionally, so `Field.getGenericType()` can recover `List<Money>` from where something was declared, even though no live object can report its own type argument.

The natural follow-up is "what if I need the whole parameterized type, not just one witness class?" — a single `Class<T>` token isn't enough for `List<Money>` itself, which is what a super type token solves: capture the parameterized type as an anonymous subclass of a generic abstract carrier and read it back off `getGenericSuperclass()`. That's the exact mechanism behind Jackson's `TypeReference<T>`, Spring's `ParameterizedTypeReference<T>`, and Guice's `TypeLiteral<T>` — none of them are magic, they're the same anonymous-subclass trick riding on the same `Signature`-attribute survival.

### "Give me a concrete number that changed how you write a hot path, and explain why the change matters."

The clearest one is stackless exceptions. Constructing a full exception with a captured stack trace at a realistic depth of around 5 frames costs roughly 278–282 ns, and `fillInStackTrace`'s unconditional stack walk is the dominant cost, not the throw-and-catch machinery — throwing and catching that same exception only adds about 6 ns on top of construction, roughly 2% of the total bill.

```java
// Preallocated, stackless — reused, not constructed per throw:
static final class FastReject extends RuntimeException {
    FastReject() { super(null, null, false, false); } // writableStackTrace=false
    @Override public synchronized Throwable fillInStackTrace() { return this; }
}
static final FastReject REJECT = new FastReject();
// throw+catch of REJECT measures 1.34–1.46 ns — versus 278–282 ns to construct fresh
```

That preallocated instance measures 1.34–1.46 ns for the same throw-and-catch — 190–211× cheaper — and the ratio is depth-dependent, not a flat constant: at depth 1 it's closer to 49×, and it climbs as depth increases because the capture cost, not the shared unwind cost, scales with frame count.

This is exactly why a hot validation path that legitimately needs to signal failure via an exception — a malformed-input parser distinguishing thousands of well-formed requests from a rare malformed one — should either avoid the exception on the fast path entirely (a boolean pre-check measures about 66 ns for the whole operation, two orders of magnitude cheaper than any exception) or, when the type must be a real `Throwable` for API reasons, reuse a preallocated instance with `fillInStackTrace()` overridden to no-op, at the cost of losing the stack trace entirely — acceptable only for a control-flow signal nobody will ever debug from, never for a genuine error a human needs to diagnose.

The number that keeps every other number honest is the JIT floor: an empty measurement loop on this build measures 0.51–0.63 ns, so any claimed cost within about 1 ns of that floor is unresolved noise, not a real measurement — the same discipline that separates "the compiler constant-folded this to 0.0755 ns" from "I forgot to warm up the benchmark."

## Predict the output

```java
import java.math.BigDecimal;
import java.util.HashSet;
import java.util.TreeSet;

public class BonusLedgerPuzzle {
    public static void main(String[] args) {
        BigDecimal a = new BigDecimal("2.0");
        BigDecimal b = new BigDecimal("2.00");

        System.out.println(a.equals(b));
        System.out.println(a.compareTo(b) == 0);

        HashSet<BigDecimal> hashSet = new HashSet<>();
        hashSet.add(a);
        hashSet.add(b);
        System.out.println(hashSet.size());

        TreeSet<BigDecimal> treeSet = new TreeSet<>();
        treeSet.add(a);
        treeSet.add(b);
        System.out.println(treeSet.size());
    }
}
```

**Output**
```
false
true
2
1
```

**Why** `BigDecimal.equals` compares both the unscaled significand and the scale, and fails fast the moment the scales differ — `"2.0"` parses to scale 1, `"2.00"` to scale 2, so `equals` returns `false` even though they represent the same number. `compareTo` ignores scale and compares numeric value only, so it agrees they're equal. `HashSet` uses `hashCode`/`equals`, and `BigDecimal.hashCode()` is scale-sensitive too (`2.0.hashCode()` is `621`, `2.00.hashCode()` is `6202`), so both values land in the set as distinct entries, size 2. `TreeSet` uses `compareTo` for both ordering and deduplication, so it sees the second insert as "equal" to the first and keeps only one, size 1 — the same underlying values sit in two different-sized collections purely because of which comparison method each collection type uses internally.

```java
import java.time.LocalDate;

public class ClampPuzzle {
    public static void main(String[] args) {
        LocalDate start = LocalDate.of(2026, 1, 31);
        LocalDate chained = start.plusMonths(1).plusMonths(1);
        LocalDate direct = start.plusMonths(2);

        System.out.println(chained);
        System.out.println(direct);
        System.out.println(java.time.temporal.ChronoUnit.DAYS.between(chained, direct));
    }
}
```

**Output**
```
2026-03-28
2026-03-31
3
```

**Why** `plusMonths` never overflows into the next month and never throws on an invalid target day — it clamps to the last valid day of the target month. The first `plusMonths(1)` lands on `2026-02-28` (February has no 31st), and clamping is not remembered: the second `plusMonths(1)` from `2026-02-28` lands on `2026-03-28`, exactly 28 days into March, because the "31" from the original date is already lost. `plusMonths(2)` applied directly to `2026-01-31` computes the target month (March, which has 31 days) in one step and needs no clamp at all, landing on `2026-03-31`. Two calls that look mathematically equivalent to one diverge by three days purely because of where the intermediate clamp happens to fall.

```java
public class StakeSplit {
    record Split(int bonusMinor, int cashMinor) {
        Split {
            cashMinor = 420 - bonusMinor;
        }
    }

    public static void main(String[] args) {
        Split split = new Split(33, 999);
        System.out.println(split.bonusMinor() + " " + split.cashMinor());
    }
}
```

**Output**
```
33 387
```

**Why** In a compact constructor, the compiler emits the field-writing `putfield` instructions *after* your compact-constructor body runs, reading from the parameter slots at that point — so the only way to change what actually gets stored is to assign to the parameter *name*, not `this.fieldName`, which the language disallows entirely in a compact constructor. Here `cashMinor = 420 - bonusMinor;` reassigns the `cashMinor` parameter slot before the implicit field write happens, so the field ends up holding `420 - 33 = 387`, not the caller's original `999`. `bonusMinor` was never reassigned, so it keeps the caller's `33` unchanged. The general trap this exposes: writing `entries = List.copyOf(entries);` in a compact constructor genuinely replaces what's stored, but forgetting the assignment — writing only `List.copyOf(entries);` as a statement with no effect — silently discards the copy and stores the caller's original, mutable list instead, with no compiler warning either way.

```java
import java.util.Optional;

public class OrElsePuzzle {
    static int calls = 0;

    static int expensiveDefault() {
        calls++;
        return -1;
    }

    public static void main(String[] args) {
        Optional<Integer> present = Optional.of(420);
        int result = present.orElse(expensiveDefault());
        System.out.println(result);
        System.out.println(calls);
    }
}
```

**Output**
```
420
1
```

**Why** `Optional.orElse(T)` takes an already-computed value as its argument, and JLS 15.12.4 evaluates argument expressions before the method call happens — so `expensiveDefault()` runs unconditionally, once, regardless of whether `present` holds a value. The returned result is still `420`, because `orElse` only *uses* its argument when the `Optional` is empty; it just doesn't avoid *computing* that argument first. `calls` ends at `1`, not `0`, which is exactly the bug this pattern hides in production: a database lookup or heavy computation passed to `orElse` runs on every single call site, present or not. `orElseGet(OrElsePuzzle::expensiveDefault)` would print `calls == 0` here, because a `Supplier` is only invoked when the `Optional` is actually empty.

```java
import java.util.List;

public class GenericArrayPuzzle {
    record LedgerEntry(String label) {}

    static <T> T[] unboundedArray(int n) {
        return (T[]) new Object[n];
    }

    static <T extends LedgerEntry> T[] boundedArray(int n) {
        return (T[]) new Object[n];
    }

    public static void main(String[] args) {
        String[] fine = unboundedArray(3);
        System.out.println(fine.length);

        try {
            LedgerEntry[] broken = boundedArray(3);
            System.out.println("unreachable");
        } catch (ClassCastException e) {
            System.out.println("caught: " + e.getClass().getSimpleName());
        }
    }
}
```

**Output**
```
3
caught: ClassCastException
```

Note: `unboundedArray`'s assignment to `String[] fine` does not itself throw at that line — the returned reference is secretly an `Object[]`, and an `ArrayStoreException` or `ClassCastException` would only surface later, the moment code actually tries to store into or read the array as `String[]` in a way the JVM enforces; `fine.length` alone never touches element type. The `boundedArray` call throws immediately, inside the method, before it ever returns.

**Why** The cast `(T[]) new Object[n]` compiles to a `checkcast` against the erasure of `T[]`. For an unbounded `T`, that erasure is `Object[]`, and casting `Object[]` to `Object[]` is a no-op `javac` elides entirely — nothing can fail at that line, though the returned array is still, at runtime, actually an `Object[]` wearing a `T[]`-shaped static type, a mismatch that surfaces later and elsewhere. For `T extends LedgerEntry`, the erasure of `T[]` is `LedgerEntry[]`, and casting an actual `Object[]` instance to `LedgerEntry[]` is a real, enforced check that fails immediately, inside `boundedArray`, before the method can even return — which is why the safest fix for a method that needs to produce a generic array is to return `List<T>` instead of `T[]`, sidestepping the erasure mismatch completely.

---

**Leaves covered:** none — Part 2 wrap-up over §2.1–§2.15, whose leaves are owned by the files linked in the summary table
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 429
