# 03 Java Core — The eighty questions, 1–16 — INTERVIEW (§5.1, 5.1.1–5.1.16)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Part 4 interview wrap-up](93-interview-build-it.md) · Next: [The eighty questions, 17–32](94a-interview-questions-17-32.md)

## How to use these eighty questions

Part 5 opens with eighty questions an interviewer actually asks about Java core, split across
five files by number: **1–16 here**, 17–32 in `94a-interview-questions-17-32.md`, 33–48 in
`94b-interview-questions-33-48.md`, 49–64 in `94c-interview-questions-49-64.md`, and 65–80 in
`94d-interview-questions-65-80.md`.

Every answer below comes in two registers. **The 30-second answer** is what you say first, out
loud, before the interviewer has decided how deep to go — it is the whole answer for a screening
round, and it should stand alone. **The 5-minute answer** is what you give when they say "go on":
the mechanism, at source level, with real field names, real constants and their actual values, and
bytecode where the bytecode is the point. Q1 is written as the worked example of this two-register
shape, because the syllabus asks for it explicitly there; every question after it follows the same
skeleton without calling it out again. After the answer: a runnable QuizStakes-domain code snippet
where code makes the point land, the follow-up question an interviewer chains onto this one with
its own short answer, and a link to where the note set proves the claim in full.

The trap index that catalogues the wrong-but-plausible answers to this exact question set is
[`94e-interview-trap-index.md`](94e-interview-trap-index.md). The retention drills — spaced repetition
prompts, the atomic-concept checklist and the puzzle set — are in
[`94f-interview-drills-and-retention.md`](94f-interview-drills-and-retention.md). Neither is duplicated here.

## The questions

### Q1. "What is the difference between `==` and `equals`?"

**The 30-second answer.** `==` on references always compares identity — the two variables' slots,
which for a compressed-oop reference is a 4-byte address comparison — and never anything else,
because it is not overloadable. `equals` is a method, `Object.equals(Object)`, whose default body
is literally `return this == obj;`, so a class that overrides nothing is silently doing identity
comparison under an equality-shaped name. A class that overrides `equals` decides for itself what
"equal" means — usually field-by-field content comparison. On primitives `==` compares values
directly; there is no `equals` for primitives at all. The one place the two blur is a boxed
primitive inside its cache range, where two different-looking expressions can land on the same
cached object and make `==` and `equals` agree by accident, not by rule.

**The 5-minute answer.** Three separate questions get conflated in casual speech: identity (same
object — `System.identityHashCode`, `==` on references), equality (what `.equals()` says, entirely
author-defined), and domain equivalence (what the business considers "the same," which may or may
not match either of the first two). `==` only ever answers the first question, for every reference
type, in every version of Java — JLS §15.21.3 defines it as reference equality with no operator
overloading hook. `Integer.valueOf(1000) == Integer.valueOf(1000)` is `false` on JDK 21.0.7,
measured, while `Integer.valueOf(127) == Integer.valueOf(127)` is `true` — not because `==`
sometimes compares values, but because `valueOf` returns a shared cached instance for `-128..127`
(JLS §5.1.7) and a fresh `new Integer(i)` outside it, so the two expressions happen to reduce to the
same object slot inside the cache and different ones outside it. `equals`'s default body inherits
straight from `Object`:
```java
public boolean equals(Object obj) {
    return (this == obj);
}
```
so `newInstance.equals(newInstance)` is `true` and `newInstance.equals(anyOtherIdenticalInstance)`
is `false`, for exactly the reason `==` would say so — a class gains nothing from `equals` until it
overrides it. Records generate a real override automatically: component-by-component comparison,
using each component's own `equals`. A hand-written `equals` must satisfy five clauses (reflexive,
symmetric, transitive, consistent, and `x.equals(null)` is `false` and never throws) — the full
contract, including the transitive-break-in-a-subclass-chain proof, is Q12's territory.

```java
record Money(BigDecimal amount, Currency currency) { }

Money reservationA = new Money(new BigDecimal("3.33"), Currency.getInstance("GBP"));
Money reservationB = new Money(new BigDecimal("3.33"), Currency.getInstance("GBP"));

boolean identity = reservationA == reservationB;        // false — two distinct heap allocations
boolean equality = reservationA.equals(reservationB);   // true — record equals compares components
```

**The follow-up they will ask.** "So why is `Integer a = 127, b = 127; a == b` true but `128` isn't?"
The cache boundary, exactly — answered in full in Q2.

**Where this is written**
[`objects-equality-and-lifecycle/01-basics.md`](objects-equality-and-lifecycle/01-basics.md) §5 (identity/equality/equivalence, the `Object.equals` default) and [`01b-equals-hashcode-and-object-methods.md`](objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md) §1 (the five-clause contract).

---

### Q2. "Why does `Integer a = 127, b = 127; a == b` print true but 128 print false?"

**The 30-second answer.** `Integer a = 127` autoboxes to `Integer.valueOf(127)`, and
`Integer.valueOf` hands back a shared cached instance for every value in `-128..127` — JLS §5.1.7
requires exactly that range to be interned. Both calls to `valueOf(127)` return the identical
object, so `==`, which is reference comparison, is `true`. `128` is outside the mandated range, so
each call falls through to `new Integer(128)`, two distinct objects, and `==` is `false`. Nothing
about the number 127 is special to the JVM — it is `IntegerCache.high`, the cache's own boundary.

**The 5-minute answer.** The whole of `Integer.valueOf` on JDK 21.0.7:
```java
@IntrinsicCandidate
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```
`IntegerCache` is a private static nested class holding `low = -128` (a literal), `high` (default
127, a blank final assigned once from a VM property), and a 256-element `Integer[] cache` built —
on a default JDK 21 JVM, usually mapped from the CDS archive rather than constructed by a loop.
Measured identity-hash evidence on Oracle JDK 21.0.7: at 127 both boxings report identity hash
`692404036` (consistent with, though not proof of, one object); at 128 they report `1670675563`
and `723074861` — two different values, which *is* conclusive proof of two distinct objects, since
one object has exactly one identity hash for its lifetime. Proving the boundary belongs to the
cache and not the number 127: the same flip happens at the low end,
`Integer.valueOf(-128) == Integer.valueOf(-128)` is `true` and `-129` is `false`, and the upper flip
*moves* — with `-XX:AutoBoxCacheMax=1000`, `Integer.valueOf(1000) == Integer.valueOf(1000)` measures
`true`. A property of the literal 127 could not produce either result.

```java
final class RetryCountProbe {
    static boolean sharesInstance(int retryCount) {
        return Integer.valueOf(retryCount) == Integer.valueOf(retryCount);
    }

    public static void main(String[] args) {
        System.out.println(sharesInstance(127));   // true  — slot 255
        System.out.println(sharesInstance(128));   // false — off the end of the 256-entry cache
    }
}
```

**The follow-up they will ask.** "Can you widen the range, and what's the lower bound?" — Q3.

**Where this is written**
[`wrappers-and-boxing/01a-the-wrapper-caches.md`](wrappers-and-boxing/01a-the-wrapper-caches.md) §1 and [`01b-cache-coverage-and-reference-equality.md`](wrappers-and-boxing/01b-cache-coverage-and-reference-equality.md) §2.

---

### Q3. "Can you change the Integer cache range? What is the lower bound?"

**The 30-second answer.** You can *raise* the upper bound with `-XX:AutoBoxCacheMax=n` or
`-Djava.lang.Integer.IntegerCache.high=n` — both work, and they feed the same single configuration
path. You cannot lower it: the source clamps with `Math.max(parseInt(prop), 127)`, so anything at
or below 127 is silently ignored. The lower bound, `-128`, cannot move at all — it is a
`static final int` literal, mandated by JLS §5.1.7, with no property read anywhere near it. You
should not touch the upper bound except against a measured allocation problem, because it changes
`==` semantics process-wide for every library in the JVM, not just your code.

**The 5-minute answer.** `IntegerCache.low = -128` is a bare literal — a compile-time constant that
`javac` folds directly, with zero runtime cost and zero configurability. `IntegerCache.high` is a
*blank final*, assigned once in the static initialiser from a value read via
`jdk.internal.misc.VM.getSavedProperty("java.lang.Integer.IntegerCache.high")` — a **saved**
property, captured at VM init level 0 and then deliberately masked out of `System.getProperties()`
by name in a five-case `switch` in `System.createProperties`. Measured: `System.getProperty` for
that key returns `null` in every configuration, including one where `-XX:AutoBoxCacheMax=1000`
demonstrably widened the cache — you cannot ask the running process what its range is; you can only
probe behaviour. The clamp itself, quoted from JDK 21.0.7:
```java
h = Math.max(parseInt(integerCacheHighPropValue), 127);
h = Math.min(h, Integer.MAX_VALUE - (-low) - 1);
```
`Math.max(..., 127)` is the one-directional gate — measured, `-XX:AutoBoxCacheMax=50` produces
byte-identical behaviour to no flag at all: 127 shared, 128 not. The `Math.min` clamp caps `high` at
`2147483647 - 128 - 1 = 2147483518`, so `size = (high - low) + 1` never overflows `int`. An
unparseable property value (`=banana`) is swallowed by an empty `catch (NumberFormatException)` and
silently keeps `high = 127` — no warning, exit code 0 — whereas the same typo on the `-XX` form
refuses to boot the JVM outright. Raising the flag also has a side effect nobody expects: on Java 21
the default 256-entry cache is usually memory-mapped from the CDS archive rather than built by a
loop, and any `high` above 127 makes `size > archivedCache.length` true, so the archive is mapped
*and then thrown away*, and the loop constructs a fresh, larger array anyway — you pay for both.

```java
public static void main(String[] args) {
    System.out.println(System.getProperty("java.lang.Integer.IntegerCache.high")); // null, always
    System.out.println(Integer.valueOf(-128) == Integer.valueOf(-128));            // true, unconditionally
    System.out.println(Integer.valueOf(-129) == Integer.valueOf(-129));            // false — proves the low boundary
}
```

**The follow-up they will ask.** "What does raising it cost you that isn't obvious?" — the CDS
archive discard above, plus every other library in the process silently changing `==` semantics for
values it never asked to have cached.

**Where this is written**
[`wrappers-and-boxing/03a-internals-cache-configuration-and-cds.md`](wrappers-and-boxing/03a-internals-cache-configuration-and-cds.md) §1–2 and [`01a2-the-archived-cache.md`](wrappers-and-boxing/01a2-the-archived-cache.md) §1.

---

### Q4. "Why is String immutable, and why is it also final?"

**The 30-second answer.** `String` is immutable because the platform hands the same character data
to code it does not trust — file paths, class names, security-check strings, `HashMap` keys — and
if any of those could be mutated after the check, every check would be a time-of-check-to-time-of-use
bug. Immutability is what lets a `String` be a safe map key, a lock-free shared constant across
threads with no synchronisation, and cacheable in the string pool. `final` is what makes the
immutability actually hold: without it, a subclass could override a method or expose a mutator and
break the guarantee for every caller holding a reference typed as `String`.

**The 5-minute answer.** The field set on JDK 21 is the whole design:
```java
@Stable
private final byte[] value;   // never written after the constructor
private final byte coder;     // LATIN1 = 0, UTF16 = 1
private int hash;             // memoised hashCode, 0 = "not yet computed"
private boolean hashIsZero;   // disambiguates "not computed" from "computed, and it's 0"
```
`value` is `final` as a *reference* — the JLS does not forbid writing into a `byte[]`'s contents —
so immutability here is a design invariant, not a language one: every mutating-looking method
(`substring`, `replace`, `toUpperCase`, concatenation) allocates a fresh array and returns a new
`String`, and no method ever leaks `value` itself (`toCharArray`, `getBytes`, `chars` all copy or
decode). `hash`/`hashIsZero` are the one deliberately mutable pair, and they are a benign data
race: content is frozen, so every thread that recomputes the hash computes the identical `int`, so
an unsynchronised write is safe. `final class String` closes the hole `private final` alone cannot:
a hostile `MutableString extends String` overriding `toCharArray()` to return a live backing array
— or simply adding a public mutator — would silently defeat every one of those guarantees for any
caller holding the subclass through a `String`-typed reference. `final` on the class is rule 1 of
the five-rule immutability discipline (no subclass can exist); `private final` fields (rule 2) is
necessary but nowhere near sufficient alone — `private final List<X>` is not immutable if the list
itself is mutable and never copied.

```java
final class IdempotencyKey {          // final class: no hostile subclass, no override surface
    private final String value;       // private final: no external write, no reassignment

    IdempotencyKey(String value) {
        this.value = Objects.requireNonNull(value, "value must not be null");
    }

    String value() { return value; }  // returns the field directly: String is already immutable
}
```

**The follow-up they will ask.** "Is `final` on a field the same guarantee as `final` on the
class?" No — `final` on an instance field buys the JMM freeze action and a reassignment check, not
folding and not immutability of what it points to; Q14 covers the distinction in full.

**Where this is written**
[`strings/01-basics.md`](strings/01-basics.md) (field set, "why it exists") and [`immutability-and-design/02-immutability.md`](immutability-and-design/02-immutability.md) §1 (the five rules, worked through on `Movement`).

---

### Q5. "Where does the string pool live, and what changed in Java 7?"

**The 30-second answer.** The pool — `StringTable` — is a single JVM-wide native hash table mapping
string content to one canonical `String` object; every literal is installed into it on first
resolution by `ldc`, and `intern()` is the same lookup exposed to user code. Through Java 6, the
`String` objects the table pointed at lived in PermGen, a small, separately-sized region, so
aggressive interning caused `OutOfMemoryError: PermGen space` and interned strings were effectively
never collected. **Java 7 moved the pooled objects to the ordinary heap** (JDK-6962931); PermGen
itself was removed entirely in Java 8. On JDK 21 the table holds *weak* references, so an interned
string with no other strong holder is collected exactly like any other object.

**The 5-minute answer.** The `StringTable` is native HotSpot memory, not Java heap memory — it is a
`ConcurrentHashTable` of `WeakHandle`s, default start size `StringTableSize = 65536` buckets
(confirmed on Oracle JDK 21.0.7), rounded up to a power of two and growing concurrently once
live-items-per-bucket exceeds 2.0 — this growability is itself a version trap, since through JDK 9
the table was a fixed-size `BasicHashtable` that never resized, which is why older material fixates
on tuning `-XX:StringTableSize`. What actually changed in Java 7 is narrower than "the pool moved":
before, a pooled `String` sat in PermGen and PermGen's garbage collection barely touched it in
practice, so `intern()`-heavy code accumulated forever; after, the `String` objects are ordinary
heap objects reachable only weakly from the table, so they are collected like anything else once
nothing else holds them — the table *node* itself is swept later, when dead nodes reach 0.5× the
bucket count. The corrected modern failure mode is not "OOM in a dedicated region" but "unbounded
table growth that never shrinks," because `StringTable` has no eviction API at all.

```java
String pooled = "AA-801";
String copied = new String("AA-801");     // shares the same value[] array, but not pooled
String interned = copied.intern();

pooled == copied;      // false — distinct headers, new String never installs itself
pooled == interned;    // true  — intern() found the table's existing entry
```

**The follow-up they will ask.** "So should FundsLedger intern its 21 status codes?" Yes — a
bounded, closed value set is exactly the case interning is for; see Q6's canonicaliser discussion.

**Where this is written**
[`strings/01b-the-string-pool.md`](strings/01b-the-string-pool.md) §1 and [`03b-internals-stringtable-and-interning.md`](strings/03b-internals-stringtable-and-interning.md) §1 and "3.2.13 — the pool moved to the heap".

---

### Q6. "What does `intern()` do, and when would you call it?"

**The 30-second answer.** `intern()` is a native method that looks the string's content up in
`StringTable`; on a hit it returns the existing canonical instance, on a miss it installs `this` and
returns `this`. Call it only for a small, closed, known value set that repeats a lot — status codes,
currency codes — where you want `==` to work and the memory win is real. Never call it on unbounded
input (client names, free-text memos, anything from an HTTP body): the table has no eviction API and
never shrinks, so an unbounded key set degrades every subsequent `intern()` and every literal
resolution in the whole JVM, forever.

**The 5-minute answer.** `intern()`'s cost is not "a map lookup" — it is a native call that
recomputes the string's hash in native code (`java_lang_String::hash_code`, which cannot use the
Java-side cached `hash` field), probes the read-only CDS archive table first, then probes the live
mutable table. Shipilev's JDK 8u131 measurement put a `HashMap<String,String>` canonicaliser at
roughly 8× faster than `intern()` for interning a million strings — a fixed-table-era number,
explicitly not re-verified on JDK 21's resizable table, but the *direction* (native call plus
uncached hash loses to an inlined Java probe) follows from the source regardless. For QuizStakes:
`FundsLedger` parses ~19.8M status-code strings a day from a set of ~21 distinct contents. A record
compact constructor rewriting the field to a canonical instance removes the retention penalty with
no `intern()` call at all, because the 21 literals are already pool-resident from class-load `ldc`
resolution:
```java
public record LedgerEntry(long rowId, AccountId accountId, String statusCode, Money amount) {
    public LedgerEntry {
        statusCode = LedgerStatusCodes.canonical(statusCode);   // HashMap probe, not intern()
    }
}
```
Reach for `String.intern()` itself specifically when you need `==` to work *across unrelated code
paths that do not share your canonicaliser* — cross-module, cross-classloader identity is exactly
what the JVM-wide table gives you for free, which a private `HashMap` cannot.

```java
final class StatusCodeCanonicaliser {
    private final Map<String, String> canonical = new ConcurrentHashMap<>(32);

    String canonicalise(String parsed) {
        String existing = canonical.get(parsed);
        if (existing != null) return existing;
        return canonical.size() < 64
                ? canonical.computeIfAbsent(parsed, String::valueOf)
                : parsed;                    // refuse to grow past the known-set size
    }
}
```

**The follow-up they will ask.** "What if a client memo field got interned by accident — what
breaks?" Table bloat with no eviction and growing chain lengths — nothing crashes, every subsequent
literal resolution and `intern()` call in the whole JVM just gets slower, invisibly.

**Where this is written**
[`strings/01b-the-string-pool.md`](strings/01b-the-string-pool.md) §1 ("When to intern, and when not") and [`03b-internals-stringtable-and-interning.md`](strings/03b-internals-stringtable-and-interning.md) §1.

---

### Q7. "Is `\"hel\" + \"lo\" == \"hello\"` true? What if one side is a variable? What if it is a final variable?"

**The 30-second answer.** `"hel" + "lo" == "hello"` is `true` — both are compile-time constant
expressions, so `javac` folds the concatenation into a single pooled literal and both sides of `==`
resolve to the identical object. If one side becomes a plain (non-`final`) variable, it is `false`:
the concatenation is no longer a constant expression, so it compiles to a runtime call that
allocates a fresh `String`, and `==` compares that fresh object against the pooled literal. If the
variable is made `final` *and* initialised with a constant expression, folding comes back and it is
`true` again — but "effectively final" is not enough; the `final` keyword itself is required by the
specification.

**The 5-minute answer.** JLS §4.12.4 defines a *constant variable* as a `final` variable of
primitive or `String` type initialised with a constant expression (§15.29); only a reference that
qualifies gets folded. Compiled bytecode makes the difference concrete:
```java
final String prefix = "AA-";
(prefix + "801") == "AA-801";     // true
```
compiles to two `ldc` instructions loading the *same* pooled `"AA-801"` — the local is dead, `javac`
already evaluated the concatenation at compile time. Delete `final`:
```java
String prefix = "AA-";            // no 'final'
(prefix + "801") == "AA-801";     // false
```
and `javac` instead emits `invokedynamic makeConcatWithConstants` (JEP 280, Java 9+) — a real
runtime call that allocates a fresh, non-pooled `String` every execution, compared against the
pooled literal by `if_acmpne`. "Effectively final" — good enough for lambda capture, for `var`
inference — does **not** qualify here; constant-variable status is specifically one of the few
places the JLS demands the keyword itself, not just the compiler's own effective-finality analysis.

```java
final class AccountActivation {
    static boolean folded() {
        final String prefix = "AA-";
        return (prefix + "801") == "AA-801";       // true — javac folds it
    }
    static boolean notFolded() {
        String prefix = "AA-";                     // no 'final'
        return (prefix + "801") == "AA-801";       // false — invokedynamic, fresh object
    }
}
```

**The follow-up they will ask.** "Why does that matter beyond a trivia answer?" Because relying on
folding for correctness is fragile — deleting an unused-looking `final` during cleanup silently
flips a `==` from `true` to `false` with no compiler warning; the fix is to never compare strings
with `==` at all, only `equals`.

**Where this is written**
[`strings/01b-the-string-pool.md`](strings/01b-the-string-pool.md) §"Constant folding depends on `final`" and [`classes-and-initialization/04-internals-final-and-constant-folding.md`](classes-and-initialization/04-internals-final-and-constant-folding.md) §3.

---

### Q8. "How is `+` on strings compiled, and what changed in Java 9?"

**The 30-second answer.** Through Java 8, every `+` on strings desugared at compile time into
`new StringBuilder().append(...).append(...).toString()` — frozen policy, baked into the class file
forever. Since Java 9 (JEP 280, "Indify String Concatenation"), `javac` instead emits a single
`invokedynamic` call to `StringConcatFactory.makeConcatWithConstants`, and the actual strategy —
how the result is built — is decided by the JDK at link time, the first time that call site
executes, and can improve on a newer JVM with no recompilation. On Java 15+ this is the *only*
strategy the JDK ships; the alternate strategies and their `-D` selector were deleted in JDK 15.

**The 5-minute answer.** Take `"client " + clientId + " -> " + statusCode`. On Java 8, `javap -c`
shows `new StringBuilder`, `dup`, `invokespecial <init>` (allocating a default `char[16]` the
compiler chose blind), four `append` calls, and a final `invokevirtual toString` that copies the
whole live prefix into a new `String` — nine method calls and at least two array allocations. On
JDK 21:
```
0: aload_1
1: aload_2
2: invokedynamic #7, 0    // makeConcatWithConstants:(String;String;)String;
7: areturn
```
Two instructions. The literals `"client "` and `" -> "` never appear on the operand stack at all —
they moved into the `BootstrapMethods` attribute as a *recipe* string, `client \1 -> \1`, where
`\1` (`TAG_ARG`) marks each variable-argument hole. The bootstrap runs once per call site, on first
execution, and installs a `ConstantCallSite` holding a `MethodHandle` chain specialised to that
exact expression's static argument types — it measures every argument's length and coder up front,
allocates the result `byte[]` **once at exactly the final size**, and writes each piece in with zero
extra copies and zero growth reallocations. A hand-written `StringBuilder` cannot do that: it starts
at capacity 16, discovers the length as it grows, reallocates, and then `toString()` copies the
whole thing one final time — strictly more copying for the identical expression. The one place
`StringBuilder` still wins is a **loop**: one `+` expression per iteration still copies the entire
prefix on every iteration, because `invokedynamic` is one call site *linked* once but *invoked* n
times — the asymptotics did not change, only the constant factor roughly halved (Q9 works this in
full). `[VERSION-TRAP]`: "always use `StringBuilder` instead of `+`" is Java 8 advice; on Java 21,
replacing a single `+` expression with a hand-rolled builder makes the code both longer and slower.

```java
public final class AccountActivation {
    public String activationLog(String clientId, String statusCode) {
        return "client " + clientId + " -> " + statusCode;   // one indy call, exact-size array
    }
}
```

**The follow-up they will ask.** "Then why is `+=` in a loop still slow?" — see Q9.

**Where this is written**
[`strings/04-internals-stringbuilder-and-concat.md`](strings/04-internals-stringbuilder-and-concat.md) and [`04b-internals-indified-concat.md`](strings/04b-internals-indified-concat.md) §1, plus [`primitives-and-conversions/02d-string-concatenation.md`](primitives-and-conversions/02d-string-concatenation.md).

---

### Q9. "Why is string concatenation in a loop O(n²)?"

**The 30-second answer.** `String` is immutable, so every `+=` allocates a fresh array and copies
the *entire current accumulator* into it, not just the new piece. Iteration `k` copies roughly `k`
units of data, so total copying across `n` iterations is `1 + 2 + ... + n = n(n+1)/2` — quadratic in
the number of appends, for a linear amount of final output. Since Java 9 the desugaring is
`invokedynamic`, not a per-iteration `StringBuilder`, which made the constant factor cheaper, but
the copy-the-whole-prefix-every-time shape is unchanged, so the complexity class is unchanged. The
fix is to hoist one mutable `StringBuilder` out of the loop, whose growth is geometric and therefore
amortised linear — or, at real scale, stream straight to a `Writer` and never hold the whole result
in memory at all.

**The 5-minute answer.** The compiled loop makes the quadratic term visible directly. For
`report += formatRow(entry) + "\n"` inside a `for`, JDK 21 `javap`:
```
30: aload_2               // push the WHOLE current accumulator — every iteration
31: aload   4
33: invokevirtual         // formatRow-equivalent producing the new row
36: invokedynamic #35, 0  // makeConcatWithConstants — allocates fresh, copies aload_2's contents in
41: astore_2              // overwrite the local; the old accumulator is now garbage
```
`aload_2` at offset 30 pushes the entire current `report` as argument 0 of the indy call on every
single pass — that push, not the call itself, is the quadratic term, because the call behind it
allocates a `report.length() + line.length()` array and copies `report` into it in full. For
`FundsLedger`'s daily reconciliation report over ~19.8M `LedgerEntry` rows at ~180 bytes/row: output
size is `19.8M x 180 ≈ 3.56` GB, but bytes actually copied by `+=` is `n^2 * w / 2 ≈ 3.53 x 10^16` —
**about 35 petabytes** of `arraycopy` to produce 3.56 GB of answer, plus 19.8M dead byte arrays, many
large enough to bypass the young generation entirely as G1 "humongous" allocations. Hoisting a
single `StringBuilder` fixes the asymptotic class but not the peak memory — a pre-sized builder for
that report still peaks around 7.1 GB of live character data (the 3.56 GB result, the array being
copied out of during the final growth, and `toString()`'s own copy), because `StringBuilder`'s own
growth (`2 * oldCapacity + 2` characters per reallocation, not plain doubling) is amortised O(1) but
still holds the whole result live. The real production fix at 19.8M rows is neither `+=` nor a
`StringBuilder` held in memory: stream to a `Writer`, which is O(n) time *and* O(1) memory.

```java
// Quadratic — never ship this at real scale.
String reconciliationReportQuadratic(List<LedgerEntry> entries) {
    String report = "";
    for (LedgerEntry entry : entries) {
        report += formatRow(entry) + "\n";     // copies the WHOLE accumulator every time
    }
    return report;
}

// The actual fix at 19.8M rows: O(n) time, O(1) memory.
void writeReconciliationReport(List<LedgerEntry> entries, Writer sink) throws IOException {
    for (LedgerEntry entry : entries) {
        sink.write(formatRow(entry));
        sink.write('\n');
    }
}
```

**The follow-up they will ask.** "How do I size the builder?" Pre-size to the known output length
with `new StringBuilder(n)` — every growth copy disappears, though never `toString()`'s own copy.

**Where this is written**
[`strings/02-performance-and-text.md`](strings/02-performance-and-text.md) §"`+` in a loop is quadratic" and [`04-internals-stringbuilder-and-concat.md`](strings/04-internals-stringbuilder-and-concat.md) §"`newCapacity` is `2 x old + 2`" and §"The growth arithmetic for a million characters".

---

### Q10. "How does `String.hashCode` work and why 31?"

**The 30-second answer.** `String.hashCode()` computes `s[0]*31^(n-1) + s[1]*31^(n-2) + ... +
s[n-1]`, implemented as the running fold `h = 31*h + s[i]` in wraparound `int` arithmetic, and
caches the result in a private `hash` field so it is computed at most once per instance (with a
second flag, `hashIsZero`, distinguishing "not yet computed" from "computed, and it genuinely is
zero"). 31 is chosen because it is odd (an even multiplier would zero out low bits and collapse
long strings into one `HashMap` bucket), prime (coprime with 2^32, so the multiply never merges two
accumulator states by itself), and historically cheap — `31*i == (i << 5) - i`, a shift and a
subtract, faster than a multiply on 1990s hardware, though the constant is frozen forever now
because it is specified in the javadoc and every persisted hash bucket depends on it.

**The 5-minute answer.** The cached implementation on JDK 21:
```java
public int hashCode() {
    int h = hash;
    if (h == 0 && !hashIsZero) {
        h = isLatin1() ? StringLatin1.hashCode(value) : StringUTF16.hashCode(value);
        if (h == 0) { hashIsZero = true; } else { hash = h; }
    }
    return h;
}
```
`hash == 0` alone is ambiguous — `""` and (famously) `"polygenelubricants"` both hash to exactly 0 —
so before JDK 13 those non-empty strings recomputed their full hash on *every* call; JDK 13 added
`hashIsZero` to record the proof once. The write to `hash`/`hashIsZero` is deliberately
unsynchronised: since the string's content is frozen, any two threads racing to compute the hash
compute the *identical* value, so the worst case is duplicated work, never a wrong answer — a
textbook benign data race. Derive the 31 arithmetic on `"AA"` (`'A' = 65`): `h = 31*65 + 65 = 2080`.
The three properties matter for a `HashMap` bucket-selection argument specifically: `HashMap` masks
the *low* bits of the (spread) hash to pick a bucket, so an even multiplier would guarantee the
bottom `k` bits are zero after `k` rounds, collapsing long strings sharing a prefix — like
`CLIENT_CASH_AVAILABLE` and `CLIENT_CASH_RESERVED`, which differ only near the end — into the same
bucket. With 31, a difference at *any* character position propagates across the whole 32-bit word,
which `HashMap`'s own `hash ^ (hash >>> 16)` spread then folds back down into the low bits it
actually uses.

```java
final class PositionIndex {
    private final Map<String, Money> byName = new HashMap<>();
    // Every get() calls hashCode() on the key; for a repeated key it is a cached field read.
    Optional<Money> find(String positionName) {
        return Optional.ofNullable(byName.get(positionName));
    }
}
```

**The follow-up they will ask.** "Does the compaction change (byte[] instead of char[]) change the
hash value?" No — the polynomial and its result are identical across JDK versions; only the
plumbing (a vectorised intrinsic on 21) that computes it changed.

**Where this is written**
[`strings/03a-internals-hash-and-equality.md`](strings/03a-internals-hash-and-equality.md) §1, "Why 31".

---

### Q11. "What is compact strings?"

**The 30-second answer.** Compact strings (JEP 254, Java 9) changed `String`'s backing storage from
`char[]` (always two bytes per character) to `byte[]` plus a one-byte `coder` field: `LATIN1 = 0`
means one byte per character, `UTF16 = 1` means two, and the coder is chosen automatically at
construction based on whether every character fits in Latin-1. Most real strings — status codes,
identifiers, ASCII text — are Latin-1, so most strings now use half the payload bytes they used to.
JEP 254 itself publishes **no percentage heap saving**; it states only the qualitative motivation
that most heap-resident strings are Latin-1-only, so quote a measured number from your own workload,
never the commonly repeated "~25%" figure.

**The 5-minute answer.** The mechanism is entirely in two methods:
```java
byte coder() { return COMPACT_STRINGS ? coder : UTF16; }
public int length() { return value.length >> coder(); }
```
`COMPACT_STRINGS` is a `static final boolean` set once from `-XX:±CompactStrings` (default `true`
on 21), and being `static final` it is JIT-folded so every `if (COMPACT_STRINGS)` in the class costs
nothing at runtime once the flag is off; when it is off, `coder()` unconditionally returns `UTF16`,
disabling every Latin-1 path through one branch rather than a second code path. `length()` derives
the character count from the array length and coder rather than storing it separately — a `String`
does not know its own length except by this shift. Worked arithmetic for
`"DOCUMENTS_VERIFIED"` (18 characters, ASCII), compressed oops assumed: Java 8's `char[]` costs a
24-byte shell plus a 56-byte array (16-byte header + 36 payload bytes, padded) = **80 bytes total**;
Java 21's Latin-1 `byte[]` costs the same 24-byte shell plus a 40-byte array (16 + 18, padded) =
**64 bytes total** — a real 16-byte, 20% saving for this string. The honest counter-case: a
non-Latin-1 display name like `"Łukasz Wiśniewski"` forces `coder = UTF16` and costs **exactly the
same 80 bytes Java 8 always charged** — compaction is a wash for non-Latin-1 content, not a
regression, but it is not free either: every operation now carries a coder branch, and concatenating
a Latin-1 operand with a UTF-16 one requires *inflating* the Latin-1 side byte by byte first.

```java
final class LedgerFootprint {
    static boolean isLatin1(String text) {
        return text.chars().allMatch(codeUnit -> codeUnit <= 0xFF);
    }
    // "DOCUMENTS_VERIFIED" -> 64 bytes; "Łukasz Wiśniewski" -> 80 bytes (coder flips to UTF16).
}
```

**The follow-up they will ask.** "What happens if a `StringBuilder` holding Latin-1 content appends
one non-Latin-1 character?" One-way inflation: the *whole* buffer, used and unused capacity alike,
is rewritten to UTF-16 immediately, doubling its byte footprint with no partial state and no way
back for that builder — covered in Q8's sibling material on `StringBuilder` internals.

**Where this is written**
[`strings/03-internals-string.md`](strings/03-internals-string.md) §1, "Compact strings and the memory arithmetic".

---

### Q12. "Explain the equals/hashCode contract and what breaks when you violate it."

**The 30-second answer.** `equals` must be reflexive, symmetric, transitive, consistent, and
`x.equals(null)` must be `false` without throwing. `hashCode`'s one hard rule is that equal objects
**must** produce equal hashes; unequal objects producing equal hashes is legal (a collision, costs
performance only). Violate the transitive clause and generic algorithms like `Set.of(a,b).equals(...)`
silently disagree depending on argument order. Violate the hash rule — most commonly by hashing on
a field that later mutates — and a `HashMap.get` on a key that is provably `equals`-equal to a
stored entry returns `null`: the lookup computes the *current* hash, probes the wrong bucket, and
`equals` is never even reached to say otherwise. The entry is still there; it is just permanently
unreachable through that key.

**The 5-minute answer.** The five `equals` clauses, each with the concrete break: **reflexive**
breaks if `equals` reads live mutable state (e.g. `Instant.now()`) instead of the object's own
fields. **Symmetric** breaks with an asymmetric `instanceof`/`getClass()` mismatch (Q13). **Transitive**
breaks in a three-class chain where a child compares an extra field only when *both* sides are that
child type, falling back to the parent's comparison otherwise — `p.equals(t1)` and `p.equals(t2)`
can both be `true` while `t1.equals(t2)` is `false`, because the parent is a lossy bridge that
never looks at the field the children disagree on. **Consistent** breaks the same way `hashCode`
does: comparing a field that mutates outside the object's control between two calls. **The `null`
clause** breaks by casting the parameter before checking its type —
`if (!(obj instanceof RestrictionKey other)) return false;` satisfies the null check and the
type check in one line, because `instanceof` is specified to return `false`, never throw, for a
`null` operand. The `hashCode` proof, worked on a `RestrictionKey(type, source)` whose `hashCode`
reads both fields and whose `source` mutates via a `relift` method: insert `k` at hash `h1`
(bucket 14, illustrative); mutate `source`; `hashCode()` now recomputes to `h2` (bucket 2);
`get(k)` computes the hash *now*, walks straight to bucket 2, finds nothing — the entry is still
sitting in bucket 14, because a `HashMap` never re-buckets an entry on its own after insertion.
`k.equals(k)` is trivially `true` throughout; `equals` is simply never called, because the lookup
fails one step earlier. **Insight**: this is asymmetric in severity — a `hashCode` that reads
*fewer* fields than `equals` (legal, just slower, collisions resolved by `equals`) is completely
different from a `hashCode` that reads a field which can change after the object becomes a live key
(a structural bug with no partial credit).

```java
final class RestrictionKey {
    private RestrictionType type;
    private RestrictionSource source;   // mutable — the bug

    void relift(RestrictionSource newSource) { this.source = newSource; }

    @Override public boolean equals(Object obj) {
        return obj instanceof RestrictionKey other && type == other.type && source == other.source;
    }
    @Override public int hashCode() { return Objects.hash(type, source); }   // reads the mutable field
}
// map.put(k, restriction); k.relift(ADMIN); map.get(k) -> null, but map.size() is still 1.
```

**The follow-up they will ask.** "What's the structural fix, not the bug fix?" Make every field
`hashCode` reads effectively immutable for the object's lifetime as a key — a record, or `final`
fields set once — or never mutate a live key: remove, mutate, reinsert.

**Where this is written**
[`objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`](objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md) §1–2 and [`04-internals-hashcode-and-identity.md`](objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).

---

### Q13. "`getClass()` or `instanceof` in `equals`?"

**The 30-second answer.** `instanceof` is Liskov-friendly but breaks symmetry the moment a subtype
adds a field that participates in equality: a supertype's `equals` accepts the subtype (since it
*is* an instance) while the subtype's `equals` rejects the plain supertype, so `a.equals(b)` and
`b.equals(a)` disagree depending on which side is which. `getClass()` restores symmetry — both
sides must be the *exact* same runtime class — at the cost of Liskov substitution: no subtype can
ever equal any instance of its supertype, even one with identical state. The honest resolution for
almost every value type in a real domain is to sidestep the question: make the class `final` (or a
record), so there is no subtype left to be asymmetric with.

**The 5-minute answer.** Prove the `instanceof` asymmetry directly. Let `r = new Restriction(TYPE, SOURCE)`
and `t = new TimedRestriction(TYPE, SOURCE, someExpiry)`, where `TimedRestriction extends Restriction`
and adds `expiresAt` to its own `equals`:
```java
class Restriction {
    @Override public boolean equals(Object obj) {
        return obj instanceof Restriction other && type == other.type && source == other.source;
    }
}
final class TimedRestriction extends Restriction {
    @Override public boolean equals(Object obj) {
        return obj instanceof TimedRestriction other
                && type == other.type && source == other.source && expiresAt.equals(other.expiresAt);
    }
}
```
`r.equals(t)`: `t instanceof Restriction` is `true` (a `TimedRestriction` *is* a `Restriction`), so
`r.equals(t)` is `true`. `t.equals(r)`: `r instanceof TimedRestriction` is `false` (a plain
`Restriction` is never a `TimedRestriction`), so `t.equals(r)` is `false`. `r.equals(t) !=
t.equals(r)` — symmetry is broken, in exactly one direction: the supertype is too permissive about
what it accepts. Switching both to `getClass() != obj.getClass()` fixes the symmetry (both
directions now `false`) but pays the real Liskov cost: a `TimedRestriction` cannot equal *any*
`Restriction`, including one constructed with identical `type`/`source` and passed around through a
generic `List<Restriction>` deduplication pass for unrelated reasons. Mixing the two strategies
within one hierarchy — one class `instanceof`, its sibling `getClass()` — reintroduces the
asymmetry in a different shape and is strictly worse than picking either consistently. For value
types (identified entirely by their fields, which is most of what a domain model has), the
resolution that avoids the trade-off entirely is composition over inheritance: `TimedRestriction`
*wraps* a `Restriction` plus an `expiresAt`, with its own independent `equals`, rather than
extending it.

```java
// The honest resolution for a value type: no subtype, no question.
final class Restriction { /* instanceof-based equals is now unconditionally safe */ }
record TimedRestriction(Restriction restriction, Instant expiresAt) { }   // composition, not extension
```

**The follow-up they will ask.** "Does a `record` have this problem?" No — records are implicitly
`final`, so the subtype that would create the asymmetry cannot exist; the generated `equals`
compares components, which is exactly the `getClass()`-equivalent safety with zero code.

**Where this is written**
[`objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`](objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md) §3.

---

### Q14. "What does `final` actually guarantee? Is a `final` list immutable?"

**The 30-second answer.** On an instance field, `final` guarantees exactly two things: the field
cannot be reassigned after construction (checked at compile time), and any thread that first
obtains a reference to the object *after* its constructor has fully exited is guaranteed to see the
correctly constructed value of that field — the JMM "freeze action" (JLS §17.5), which is what lets
immutable objects be shared across threads with zero synchronisation. It says **nothing** about the
object the reference points to. `final List<X> items` means the variable `items` cannot be pointed
at a different list later — it says nothing about whether that list can still be mutated through
`items.add(...)`, and by default it can be. A `final` reference to a mutable object is not immutable;
it is a mutable object you cannot swap out.

**The 5-minute answer.** This is the single most common immutability defect in real code, and it
survives code review specifically because it *looks* correct: `private final List<LedgerEntry>
entries` reads as "immutable field," and `final` on a reference-type field is necessary but nowhere
near sufficient. Proof, on a class with every field `private final` and no mutators visible:
```java
final class MovementLeaky {
    private final List<LedgerEntry> entries;   // final. Never reassigned. Still mutable.
    MovementLeaky(List<LedgerEntry> entries) {
        this.entries = Objects.requireNonNull(entries);   // NO copy — stores the caller's own list
    }
    public boolean balances() { /* sums entries, checks the total is zero */ }
}
```
Measured: `entryCount=2 balances=true`, then, with *no method on `MovementLeaky` ever called*, the
caller mutates the very `ArrayList` it originally passed in — `entryCount=3 balances=false`. The
double-entry invariant the constructor checked is now false, and nothing in `MovementLeaky` did
anything wrong syntactically. The fix is rule 4 of the five immutability rules: copy on the way in,
`this.entries = List.copyOf(entries)`, so the field points at an object the caller can never reach
again — and rule 5 (return the field directly once genuinely immutable; never wrap a still-mutable
field in `Collections.unmodifiableList` and call it done, since that only stops the *returned
reference* from mutating while the backing list keeps changing underneath every view already handed
out). The freeze-action guarantee has the same shape of escape: it is conditional on the reference
not leaving the constructor early — `MoneyRegistry.register(this)` as line 1, before `final` fields
are written, lets a reader through that registry legally observe a `null` `amount`, because the
antecedent ("sees the reference only after construction completes") is false, not merely weakened.

```java
// The fix: copy on the way in (rule 4), independent of the final keyword.
Movement(List<LedgerEntry> entries) {
    this.entries = List.copyOf(entries);      // now genuinely unreachable from the caller
}
```

**The follow-up they will ask.** "What happens if you leak `this` from the constructor before the
`final` fields are set?" The freeze guarantee's antecedent is false, so a racing reader can legally
observe an uninitialised field — void, not merely weaker; the fix is a private constructor plus a
static factory that registers the object only after it returns fully built.

**Where this is written**
[`classes-and-initialization/02-modifiers.md`](classes-and-initialization/02-modifiers.md) and [`04-internals-final-and-constant-folding.md`](classes-and-initialization/04-internals-final-and-constant-folding.md) §1, plus [`immutability-and-design/02-immutability.md`](immutability-and-design/02-immutability.md) §1 (the five rules) and §5 (`List.copyOf` versus `Collections.unmodifiableList`).

---

### Q15. "What happens if you change a `public static final int` and only recompile its class?"

**The 30-second answer.** Nothing visible, and that is the whole danger. A `static final int`
initialised with a literal is a *constant variable* under JLS §4.12.4, and JLS §13.1 **requires**
every reference to it — including inside the declaring class itself — to be resolved to the literal
value at compile time. There is no `Fieldref`, no `getstatic`, and no symbolic name left in the
caller's class file to relink: the value was copied in, byte for byte, when the caller was
compiled. Recompile only the declaring class, deploy only that jar, and every already-compiled
caller keeps using the *old* value, forever, with no exception, no `NoSuchFieldError`, and no log
line anywhere — because the JVM was never asked to resolve a field it could report as missing or
changed.

**The 5-minute answer.** Measured on Oracle JDK 21.0.7, two classes:
```java
public final class BonusRules {
    public static final int MAX_BONUS = 100;   // ConstantValue: int 100 in the class file
}
public final class BonusService {
    public int grant(int firstDeposit) {
        return Math.min(firstDeposit / 10, BonusRules.MAX_BONUS);
    }
}
```
`javap -v -c` on `BonusService.grant` shows `6: bipush 100` — the literal is an operand byte of an
instruction in `BonusService`'s *own* method. Grepping the full constant pool for `MAX_BONUS`
returns zero matches. Change `BonusRules.MAX_BONUS` to `150` and recompile **only** `BonusRules`:
`javap` on the new `BonusRules.class` correctly reports `ConstantValue: int 150`, but
`BonusService.class` is byte-identical to before — still `bipush 100` — because it was never
touched. Run it: prints `100`. No error at any point; this is a category the JLS itself names,
*binary compatible and behaviourally incompatible simultaneously*, with chapter 13 explicitly
promising only the first property. The fix, if the value must be changeable independently of its
callers' compilation, is to break one of the three conjuncts that make it a constant variable —
cheapest is the initialiser: `public static final int MAX_BONUS = Integer.valueOf(150);`. That
single change removes the `ConstantValue` attribute, forces `javac` to synthesise a real `<clinit>`
that `putstatic`s the value, and restores a genuine `Fieldref` plus `getstatic` in every caller — at
the real cost of losing usability as a `case` label or annotation value, and of the field's read now
triggering `BonusRules`' class initialisation, which it did not before. Why this survives CI: a
clean build recompiles both sides, so the stamp is always refreshed; an incremental build that
tracks *types referenced* rather than *constants inlined* will not mark `BonusService` dirty,
because after inlining it genuinely does not reference `BonusRules` at all — the bug is invisible in
CI and appears only in a partial deploy or a per-module jar release.

**The follow-up they will ask.** "How would you even detect this in a real fleet?" There is no
runtime signal — the only reliable check is a build-graph rule that any module depending on a
constants artifact is rebuilt whenever that artifact changes, regardless of whether the dependency
tracker thinks a type reference exists.

**Where this is written**
[`classes-and-initialization/04-internals-final-and-constant-folding.md`](classes-and-initialization/04-internals-final-and-constant-folding.md) §3 (the full JLS §13.1 walk-through and the `BonusRules`/`BonusService` reproduction) and [`02-modifiers.md`](classes-and-initialization/02-modifiers.md) §1 (leaves 1.14.7–1.14.8, diagram D-042).

---

### Q16. "What is the difference between `final`, `finally` and `finalize`?"

**The 30-second answer.** Three unrelated words that happen to share a root. `final` is a modifier
— on a class it forbids subclassing, on a field it forbids reassignment after construction (plus,
for an instance field, a memory-model freeze guarantee), on a method it forbids overriding, and on
a local or parameter it is a `javac`-only compile-time check with zero bytecode trace. `finally` is
a block attached to `try` that runs on every way the `try` can exit — normal completion, an
exception, a `return`, a `break` — and it is a language keyword, not a method. `finalize()` is a
deprecated instance method inherited from `Object`, once called by the garbage collector before
reclaiming an object, now `@Deprecated(since = "9", forRemoval = true)` and replaced by
`java.lang.ref.Cleaner` because it delayed reclamation by a proven extra GC cycle and permitted
"resurrection" — an object bringing itself back to life from inside its own finalizer.

**The 5-minute answer.** The one genuinely dangerous confusion is a `finally` block's interaction
with control flow, not the three-way name collision itself. `finally`'s only real trap: whatever it
does *last*, abruptly, wins — a `return` or a `throw` inside `finally` unconditionally supersedes
whatever the `try` block was already doing to complete, discarding it with **no trace whatsoever**,
not caught, not suppressed, not chained. Measured on JDK 21.0.7:
```java
static int stake(int stakeMinor) {
    try { return stakeMinor; } finally { return -1; }
}
// stake(4200) returns -1. The computed 4200 is never observed by anything, ever.
```
The bytecode proof is an exception-table row of `type any` covering the whole `try` — `finally` is
a universal catch-all that runs regardless of what, if anything, is propagating, and a
`return`/`throw` inside it completes the method or rethrows before the original completion ever
finishes. `finalize()`'s defect, proved rather than asserted: a finalizable object cannot be
reclaimed on the GC pass that first finds it unreachable, because its contract requires
`finalize()` to run *first* — the collector queues it, runs the finalizer (on a thread and at a
time you do not control), then **re-checks reachability**, because the finalizer can store `this`
into a `static` field or any other GC root, resurrecting the object. That second pass is an
unavoidable structural cost paid by every finalizable object whether or not it ever actually
resurrects — and the javadoc guarantees `finalize()` runs **at most once**, so a resurrected
object's second death gets no cleanup hook at all. `Cleaner` (Java 9+) fixes both defects
structurally: the cleanup action is a *different* object registered against the referent via a
phantom reference, so even a careless action cannot resurrect the referent through the structure
watching it — the one trap that remains is the action capturing the referent by accident (a lambda
implicitly closing over `this` via an instance-field read), which keeps the object strongly
reachable forever and the action never runs.

```java
final class ReservationFinalizerDemo {
    static Reservation resurrected;             // a GC root — storing `this` here is resurrection
    static final class Reservation {
        @Override protected void finalize() { resurrected = this; }
    }
}
```

**The follow-up they will ask.** "If `finalize` is deprecated for removal, what do you use for
native-resource cleanup today?" `AutoCloseable` plus try-with-resources for the deterministic path,
with a `Cleaner`-registered `static` nested action class as the backstop for callers who forget to
close — never a lambda that reads an instance field of the object being watched.

**Where this is written**
[`exceptions/01d-finally-traps.md`](exceptions/01d-finally-traps.md) §1–2 (the `return`/`throw`-inside-`finally` proofs) and [`objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`](objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md) §1 (the `Cleaner` capture trap) and §3 (the resurrection proof and deprecation timeline), plus [`classes-and-initialization/02-modifiers.md`](classes-and-initialization/02-modifiers.md) (`final` as a modifier on class/field/method/local).

---

**Leaves covered:** 5.1.1–5.1.16 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 890
