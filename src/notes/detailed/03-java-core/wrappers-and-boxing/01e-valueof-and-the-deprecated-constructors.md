# 03 Java Core — The deprecated wrapper constructors — BASICS (§1.9, 1.9.13)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Wrapper `equals` and `hashCode`](01d-wrapper-equals-and-hashcode.md) · Next: [`parseInt` versus `valueOf(String)`](01e2-parseint-versus-valueof-string.md)

One question in this file, and it is the most frequently mangled entry point into
`java.lang.Integer`: `new Integer(1)` still compiles on Java 21, so why is every static analyser in
the industry shouting about it, and what exactly did the JDK commit to when it marked it for removal?

The answer turns on one idea. `valueOf` is a **factory**, and a factory is free to hand you an object
you already have. A constructor is not — it is a promise to allocate something new. That single
asymmetry is the whole chapter.

---

## 1. The constructors are terminally deprecated, and `valueOf` is the only correct factory (1.9.13)

`[RESEARCH]` A constructor in Java is a promise with a hard guarantee attached: `new X(x)` **must**
produce an object distinct from every other object that exists or ever will exist. The JLS gives you
that guarantee unconditionally — it is what `new` *means*. Now hold that next to what an
`Integer` is supposed to be. An `Integer` is a number wearing an object costume. Two `Integer`s
holding 3 are not two things that happen to be equal; they are the *same number*, and the only
reason there are two of them at all is that Java 5 and earlier had no way to put an `int` into a
`Collection`. So `new Integer(3)` is a request for something the type does not want to have: a
distinct, individually-addressable, lockable, identity-hash-bearing heap object representing the
number three. The constructor is not deprecated for being slow. It is deprecated for **keeping a
promise nobody wants kept**.

### Why it exists

Autoboxing did not exist until Java 5 (JSR 201). Before then, putting a retry count into a
`Map<String, Integer>` meant writing `new Integer(retryCount)` by hand — the constructor was not a
mistake, it was the only door. Two decades of code walked through it, which is why it is still on the
class in 21 and why interviewers still ask about it.

The removal path has three distinct milestones, and getting them muddled is the commonest way to
fail this question. Keep them separate:

| Version | What happened to `Integer(int)` |
|---|---|
| **Java 5 (2004)** | Autoboxing arrives; `javac` starts emitting `Integer.valueOf(int)` instead. The constructor becomes redundant, not deprecated. |
| **Java 9 (2017)** | Annotated `@Deprecated(since="9", forRemoval = true)`. Both parts land in the same release. |
| **Java 16 (2021)** | **JEP 390, *Warnings for Value-Based Classes***. The wrappers are annotated `@jdk.internal.ValueBased`, and `javac` gains the `[synchronization]` warning. The `forRemoval` designation is reaffirmed as terminal deprecation. |
| **Java 21 LTS (this file's baseline)** | Still present. Still compiles. Emits a `[removal]` warning with **no flags**, and is an error under `-Werror`. |

The reason behind JEP 390 is Project Valhalla. Valhalla's plan for the wrappers is to make them
**value classes** — classes whose instances have no identity at all, so that `==` degenerates to
field-wise comparison and the JVM is free to flatten them into registers or into an enclosing
object's layout. A value class cannot have a constructor that guarantees a distinct object, because
there is no "distinct" left to guarantee. That is why the deprecation is *terminal* rather than
advisory: the constructor is not merely unfashionable, it is **incompatible with the type's intended
future semantics**.

**Insight:** The constructor is not deprecated for being slow — it is deprecated for *guaranteeing
identity*, which is the one thing a value class cannot do. Every other consequence (the extra
allocation, the broken `==`, the lockable monitor) is downstream of that single guarantee.

### When to reach for which

There is no legitimate remaining use of the wrapper constructors. Not "prefer `valueOf`" — `valueOf`
always, in new code and in code you are touching for other reasons.

The one case people reach for the constructor deliberately is wanting a **guaranteed distinct
object**: a private monitor to `synchronized` on, or a sentinel that `==` can distinguish from every
real value. That is a real requirement and the constructor really does satisfy it, which is why the
argument feels compelling. It is still the wrong answer, because the requirement is not "I need a
distinct `Integer`" — it is "I need a distinct object", and `Integer` is simply the wrong type to
get one from. Use a `private static final Object` for the monitor, or a domain type for the sentinel:

| Requirement | Wrong tool | Right tool |
|---|---|---|
| A private monitor for a critical section | `new Integer(0)` or a boxed `static final Integer` | `private static final Object STAKE_RESERVATION_LOCK = new Object();` |
| A sentinel distinguishable by `==` | `new Integer(-1)` | a domain type, or `Optional`, or a `record`-based result |
| A boxed value for a collection or a generic | `new Integer(n)` | `Integer.valueOf(n)`, or just `n` and let `javac` do it |
| A boxed value parsed from text | `new Integer(s)` | `Integer.parseInt(s)`, then box only if needed |

### The mechanism

The annotation is on the source, in JDK 21.0.7's `Integer.java`, on both constructors:

```java
@Deprecated(since="9", forRemoval = true)
public Integer(int value) {
    this.value = value;
}

@Deprecated(since="9", forRemoval = true)
public Integer(String s) throws NumberFormatException {
    this.value = parseInt(s, 10);
}
```

Two things to read off that. `since="9"` and `forRemoval = true` are on the same annotation, so on
JDK 21 you cannot separate "deprecated in 9" from "marked for removal" by reading the class — the
JDK 9 deprecation was already the ordinary kind and JDK 16's JEP 390 is what made the removal intent
load-bearing across the whole wrapper family. And `Integer(String)` is not a parser in its own
right; it delegates to `parseInt(s, 10)`, exactly as `Integer.valueOf(String)` does — so the
string-taking constructor was never anything but a boxed `parseInt`, and dropping it costs nothing.
See [`01e2-parseint-versus-valueof-string.md`](01e2-parseint-versus-valueof-string.md).

At the class level, measured on JDK 21.0.7, `Integer.class.getAnnotations()` returns:

```
[@jdk.internal.ValueBased()]
```

That is the marker JEP 390 added. It is `jdk.internal`, so you cannot apply it to your own classes,
and it is what `javac` consults to decide whether synchronizing on an expression deserves a warning.

**What the compiler actually says.** Compile this on JDK 21.0.7:

```java
public class Warn {
    static Integer legacy() { return new Integer(3); }
    static final Integer STAKE_LOCK = 1;
    static void reserve() { synchronized (STAKE_LOCK) { } }
}
```

`javac -Xlint:all` produced exactly:

```
src/Warn.java:2: warning: [removal] Integer(int) in Integer has been deprecated and marked for removal
    static Integer legacy() { return new Integer(3); }
                                     ^
src/Warn.java:4: warning: [synchronization] attempt to synchronize on an instance of a value-based class
    static void reserve() { synchronized (STAKE_LOCK) { } }
                            ^
2 warnings
```

Three measured facts about that output, each of which people get wrong:

1. **Both warnings fire with no compiler flags at all.** `-Xlint:all` in the command above is
   incidental. `[removal]` warnings are on by default, unlike ordinary `[deprecation]` warnings
   which need `-Xlint:deprecation` to become anything more than a "uses or overrides a deprecated
   API" note. Terminal deprecation is deliberately louder.
2. **They are warnings, not errors, on 21.** The class above compiled and ran. Add `-Werror` and you
   get `error: warnings found and -Werror specified` — which is how a build turns advice into a gate.
3. The `[synchronization]` warning fires on a `static final Integer` that was never constructed with
   `new` at all. `STAKE_LOCK = 1` is autoboxed, and measured, `STAKE_LOCK == Integer.valueOf(1)` is
   **true** — so the monitor is the **process-wide shared cached instance** from `IntegerCache`.

### The cost, in instructions

`[BYTECODE]` Same class, two methods, `javap -p -c` on JDK 21.0.7:

```
  static java.lang.Integer legacyRetryCount();
    Code:
       0: new           #7                  // class java/lang/Integer
       3: dup
       4: iconst_3
       5: invokespecial #9                  // Method java/lang/Integer."<init>":(I)V
       8: areturn

  static java.lang.Integer modernRetryCount();
    Code:
       0: iconst_3
       1: invokestatic  #12                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
       4: areturn
```

Read the first one instruction by instruction. `new` allocates a zeroed `Integer` on the heap and
pushes the reference — the allocation is committed here, before any field is set, and it is
unconditional. `dup` copies the reference because `invokespecial` will consume one and `areturn`
needs the other. `iconst_3` pushes the argument. `invokespecial` runs `<init>` and consumes the
duplicate. Four instructions, one guaranteed heap allocation of 16 bytes.

The second: `iconst_3` pushes 3, `invokestatic` calls the factory. Two instructions, and for a value
inside the cache range, **zero** allocations — `valueOf` returns
`IntegerCache.cache[i + (-IntegerCache.low)]`, an array read. See
[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md) for the cache itself and
[`03c-internals-boxing-bytecode.md`](03c-internals-boxing-bytecode.md) for the full bytecode walk.

And the observable consequence, measured:

```
new Integer(3) == new Integer(3)          -> false
Integer.valueOf(3) == Integer.valueOf(3)  -> true
```

That difference is the entire risk in the migration below.

**Interview:** *"Why is `new Integer(1)` deprecated?"* — Because a constructor guarantees a distinct
object, and the wrappers are `@jdk.internal.ValueBased` classes that Project Valhalla intends to
turn into identity-free value classes, which cannot make that guarantee. Deprecated in 9, marked
`forRemoval` in the same annotation and reaffirmed by JEP 390 in 16, still compiling in 21 with a
default-on `[removal]` warning. Secondary answer: `valueOf` can return a cached instance and is two
bytecodes instead of four.

### Diagram

No diagram for this concept: the evidence is two short `javap` listings and a two-line measured
identity result, and reading those directly is clearer than any redrawing of them.

### A concrete example

A real migration. `DocumentRequirements` tracks how many times a client has re-uploaded a document
before the application hits `AA-699 DOCUMENTS_EXHAUSTED`. The legacy shape builds its counts with
constructors, and — critically — compares one of them with `==`:

```java
import java.util.HashMap;
import java.util.Map;

/** Legacy shape, as it exists in the codebase today. Compiles on 21 with two warnings. */
final class DocumentRequirementsLegacy {

    private static final Integer EXHAUSTED_AFTER = new Integer(3);   // [removal] warning

    private final Map<String, Integer> attemptsByRequirementCode = new HashMap<>();

    Integer recordUpload(String requirementCode) {
        Integer current = attemptsByRequirementCode.get(requirementCode);
        Integer next = new Integer(current == null ? 1 : current.intValue() + 1); // [removal]
        attemptsByRequirementCode.put(requirementCode, next);
        return next;
    }

    /** Intent: has this requirement burned its retry budget? */
    boolean isExhausted(String requirementCode) {
        Integer attempts = attemptsByRequirementCode.get(requirementCode);
        return attempts == EXHAUSTED_AFTER;
    }

    String statusCodeFor(String requirementCode) {
        return isExhausted(requirementCode) ? "AA-699 DOCUMENTS_EXHAUSTED"
                                            : "AA-610 DOCUMENTS_UPLOADED";
    }
}
```

`isExhausted` has been returning `false` forever. `recordUpload` builds every count with `new`, so
the reference in the map is never the reference in `EXHAUSTED_AFTER`, so `==` is never true, so no
application has ever reached `AA-699` through this path. The bug has been latent and silent since it
was written.

Now do the mechanical rewrite — constructors to `valueOf`, nothing else. Only two lines of
`DocumentRequirementsLegacy` change, and `isExhausted` is not one of them:

```java
    // was: new Integer(3)
    private static final Integer EXHAUSTED_AFTER = Integer.valueOf(3);

    // was: new Integer(current == null ? 1 : current.intValue() + 1)
    Integer next = Integer.valueOf(current == null ? 1 : current.intValue() + 1);

    // unchanged, and now TRUE when attempts == 3
    boolean isExhausted(String requirementCode) {
        Integer attempts = attemptsByRequirementCode.get(requirementCode);
        return attempts == EXHAUSTED_AFTER;
    }
```

The warnings are gone and the behaviour changed. 3 is inside the cache range, so
`Integer.valueOf(3)` returns the same shared instance every time, so `==` now succeeds, so
applications start reaching `AA-699 DOCUMENTS_EXHAUSTED` — arguably correctly, but on a Tuesday,
in a release whose changelog says "removed deprecated API usage", with no test covering it. And it
would still be broken if the threshold were 200 rather than 3, because 200 is outside the default
cache and `==` would go back to failing.

The correct end state removes the identity dependence entirely:

```java
final class DocumentRequirementsFixed {

    private static final int EXHAUSTED_AFTER = 3;

    private final Map<String, Integer> attemptsByRequirementCode = new HashMap<>();

    int recordUpload(String requirementCode) {
        int next = attemptsByRequirementCode.getOrDefault(requirementCode, 0) + 1;
        attemptsByRequirementCode.put(requirementCode, Integer.valueOf(next));
        return next;
    }

    boolean isExhausted(String requirementCode) {
        return attemptsByRequirementCode.getOrDefault(requirementCode, 0) >= EXHAUSTED_AFTER;
    }

    String statusCodeFor(String requirementCode) {
        return isExhausted(requirementCode) ? "AA-699 DOCUMENTS_EXHAUSTED"
                                            : "AA-610 DOCUMENTS_UPLOADED";
    }
}
```

`EXHAUSTED_AFTER` is an `int`, so the comparison is `if_icmpge` on primitives and no cache boundary
can reach it. `getOrDefault(code, 0)` unboxes into an `int` at the `+`, and the only box left is the
one the map genuinely needs.

### The gotcha

The constructor-to-`valueOf` rewrite is behaviour-preserving **except** where identity was being
relied on, which means the safe order is fixed:

1. Find every `==` and `!=` on a wrapper-typed operand. Fix those first, independently, with tests.
2. Then replace the constructors.

Do it the other way round and you ship two changes as one, with the behavioural change invisible in
the diff. A blind find-and-replace across a repository is not a safe refactor for this API; a
find-and-replace **after** the comparisons are clean is.

For the `==` half — why 127 and 128 behave differently, and what `==` on two wrappers actually
compiles to — see
[`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md). For
what `valueOf` returns and when, see [`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md).

One more consequence of `@jdk.internal.ValueBased`, in one sentence: synchronizing on a boxed value
is a correctness bug, because the monitor you acquire may be the process-wide cached instance that
unrelated code also locks — the `[synchronization]` warning above is the compiler telling you
exactly that. The mechanism, including the measured `monitorenter`/`monitorexit` pair on the shared
object, lives in `03f-internals-monitors-and-valhalla.md`; the memory-model half belongs to guide
**05 Concurrency** and is not taught here.

> **Definition.** The wrapper constructors are terminally deprecated
> (`@Deprecated(since="9", forRemoval = true)`, reaffirmed by JEP 390 in Java 16) because they
> guarantee a distinct identity that a `@jdk.internal.ValueBased` class cannot keep, and
> `valueOf` is the only correct way to obtain a wrapper — it is free to return a cached instance and
> free to allocate nothing.

---

`parseInt` returns a primitive and `valueOf(String)` returns a box; the full treatment, including
the shared `NumberFormatException` and the `decode` traps, is in
[`01e2-parseint-versus-valueof-string.md`](01e2-parseint-versus-valueof-string.md).

---

## Pitfalls

### Using the `Integer` constructor deliberately to get a distinct object

**Wrong**

```java
final class AccountMaintenance {
    // "I need a lock nobody else can hold, and a boxed 0 gives me a fresh object."
    private static final Integer STAKE_LOCK = new Integer(0);

    void applyRestriction(String restrictionType) {
        synchronized (STAKE_LOCK) {
            // mutate the restriction set
        }
    }
}
```

Compiled on JDK 21.0.7 this produces two warnings with no flags — `[removal] Integer(int) in Integer
has been deprecated and marked for removal` and `[synchronization] attempt to synchronize on an
instance of a value-based class` — and under `-Werror` it produces `error: warnings found and
-Werror specified`. The construction really does give a distinct object today, which is why the
belief survives; it is on a removal path, and the moment anyone "cleans it up" to
`Integer.valueOf(0)` the lock becomes the process-wide shared cached instance that any other code in
the JVM can also acquire.

**Right**

```java
final class AccountMaintenance {
    private static final Object STAKE_RESTRICTION_LOCK = new Object();

    void applyRestriction(String restrictionType) {
        synchronized (STAKE_RESTRICTION_LOCK) {
            // mutate the restriction set
        }
    }
}
```

`new Object()` is the smallest thing in the language that guarantees a distinct identity, is not
value-based, is not deprecated, and cannot be reached by anyone who does not hold the private field.
For a sentinel rather than a monitor, use a domain type — a `RestrictionKey` or a dedicated
`record` — so that `equals` carries the meaning instead of `==`.

**Why people believe it:** the requirement ("I need a distinct object") is real, and the constructor
genuinely satisfies it. The error is in the type, not the requirement: `Integer` is a value-based
class being asked to supply identity, and every wrapper is annotated `@jdk.internal.ValueBased`
precisely to flag that request as a mistake.

### Blind find-and-replace of `new Integer(x)` to `Integer.valueOf(x)`

**Wrong**

```java
// Before: reliably false, because every `new` is a fresh object.
private static final Integer EXHAUSTED_AFTER = new Integer(3);
Integer attempts = new Integer(uploadCount);
boolean exhausted = attempts == EXHAUSTED_AFTER;      // always false

// After a repo-wide mechanical rewrite: now TRUE for 3, because 3 is cached.
private static final Integer EXHAUSTED_AFTER = Integer.valueOf(3);
Integer attempts = Integer.valueOf(uploadCount);
boolean exhausted = attempts == EXHAUSTED_AFTER;      // true when uploadCount == 3
```

Measured: `new Integer(3) == new Integer(3)` is **false**, `Integer.valueOf(3) ==
Integer.valueOf(3)` is **true**. Applications that never reached `AA-699 DOCUMENTS_EXHAUSTED` start
reaching it, in a release whose diff reads as a lint fix, with no test covering the change.

**Right**

```java
// Step 1, shipped and tested on its own: remove the identity dependence.
private static final int EXHAUSTED_AFTER = 3;
int attempts = uploadCount;
boolean exhausted = attempts >= EXHAUSTED_AFTER;      // primitive if_icmpge, no cache involved

// Step 2, a separate change: replace the constructors, which is now behaviour-preserving.
```

Fix the comparisons first, the constructors second. After step 1 there is no wrapper identity left
for step 2 to perturb.

**Why people believe it:** the rewrite genuinely is behaviour-preserving almost everywhere —
`equals`, `hashCode`, `intValue`, collection membership and arithmetic are all unaffected — so it
reads as a pure lint fix. The exception is `==`, and `==` on wrappers is invisible in a diff because
it is syntactically identical to `==` on primitives.

### Suppressing the `[removal]` warning instead of migrating

**Wrong**

```java
final class AccountMaintenance {

    // "The warning is noise, the build is clean again, and the method still works.
    //  We will migrate when the JDK actually removes it."
    @SuppressWarnings("removal")
    static Integer legacyRetryCount(int uploadCount) {
        return new Integer(uploadCount);
    }
}
```

This compiles with **zero** warnings on JDK 21.0.7, which is precisely the problem. The annotation
does not change the code's status: the constructor is still `@Deprecated(since="9", forRemoval =
true)`, still on a removal path, and still four bytecodes and a guaranteed 16-byte allocation
(`new` / `dup` / `iconst` / `invokespecial`) where `valueOf` is two and often none. What the
annotation removes is the only mechanism that would have told you where the work is. Grep for
`new Integer(` in a large codebase and you will miss every call site behind a class-level or
method-level suppression, so on the day the constructor is actually removed the migration has no
inventory and the build fails in places nobody has a list of.

**Right**

```java
final class AccountMaintenance {

    // Migrated. No suppression needed, because there is nothing left to suppress.
    static Integer legacyRetryCount(int uploadCount) {
        return Integer.valueOf(uploadCount);
    }
}
```

If a call genuinely cannot be migrated in the current change — because its `==` comparisons have not
been audited yet, per the previous pitfall — then the suppression is acceptable **only** as a
narrowly scoped, individually justified, tracked step:

```java
// Suppressed pending the == audit in AA-699 retry-budget handling; not a permanent state.
@SuppressWarnings("removal")
static Integer legacyRetryCount(int uploadCount) {
    return new Integer(uploadCount);
}
```

The distinguishing property is that the suppression carries a reason and an owner, sits on the
smallest possible element rather than the class or the package, and is expected to be deleted. A
suppression with no comment is indistinguishable from a suppression that was forgotten.

**Why people believe it:** the reasoning is genuinely sound as far as it goes. `@SuppressWarnings`
is the language's sanctioned mechanism for silencing a warning you have consciously accepted, a green
build has real value, and the constructor demonstrably still works on 21 — measured, the class
compiles and runs. The flaw is in the timeline, not the logic: `forRemoval = true` commits the JDK to
removal without naming a release, so "we will migrate when it breaks" schedules the work for a date
you do not control and cannot plan around, having first destroyed the only inventory of what needs
migrating. Under `-Werror` the difference is even starker — the un-suppressed form fails the build
today, on your schedule, which is the entire point of `-Werror`.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `new Integer(int)` on 21 | Present, compiles, `@Deprecated(since="9", forRemoval = true)` |
| Deprecated in | Java 9 |
| `forRemoval = true` since | Java 9, same annotation; reaffirmed by JEP 390 in Java 16 |
| JEP 390 | *Warnings for Value-Based Classes*, Java 16 |
| Class annotation, measured | `Integer.class.getAnnotations()` → `[@jdk.internal.ValueBased()]` |
| `[removal]` warning needs a flag | **No.** On by default, unlike `[deprecation]` |
| `-Werror` effect | `error: warnings found and -Werror specified` |
| Removal warning text | `[removal] Integer(int) in Integer has been deprecated and marked for removal` |
| Sync warning text | `[synchronization] attempt to synchronize on an instance of a value-based class` |
| `new Integer(3)` bytecode | `new` / `dup` / `iconst_3` / `invokespecial` — 4 instructions, 1 allocation |
| `Integer.valueOf(3)` bytecode | `iconst_3` / `invokestatic` — 2 instructions, 0 allocations if cached |
| `new Integer(3) == new Integer(3)` | **false** (measured) |
| `Integer.valueOf(3) == Integer.valueOf(3)` | **true** (measured) |
| Why the constructor is doomed | It guarantees identity; a Valhalla value class cannot |
| Right tool for a private monitor | `private static final Object` |
| Safe migration order | Fix `==` comparisons first, replace constructors second |
| `Integer(String)` body | `this.value = parseInt(s, 10);` — also deprecated for removal |
| Text-parsing rows | Moved to `01e2-parseint-versus-valueof-string.md` |
| `Integer.valueOf(int)` body | `if (i >= IntegerCache.low && i <= IntegerCache.high) return IntegerCache.cache[i + (-IntegerCache.low)];` |
| `valueOf` fallback when uncached | `return new Integer(i);` — the JDK calls its own deprecated constructor |
| Which wrappers are `@jdk.internal.ValueBased` | All eight |
| Can you apply `@jdk.internal.ValueBased` yourself | No; it is `jdk.internal` |
| Deprecated constructors on `Integer` | Both: `Integer(int)` and `Integer(String)` |
| `Long`'s constructors | Same treatment: `@Deprecated(since="9", forRemoval = true)` |
| `[deprecation]` warning needs a flag | **Yes**, `-Xlint:deprecation`. `[removal]` does not |
| `@SuppressWarnings("removal")` | Silences it and destroys the migration inventory. Not a fix |
| Removal release named anywhere | **No.** `forRemoval` commits to intent, not to a version |
| `static final Integer LOCK = 1` | `== Integer.valueOf(1)` is **true** — a process-wide shared monitor |
| `synchronized` on a boxed value | `monitorenter`/`monitorexit` on the shared cached object: a correctness bug |
| Project Valhalla's plan | Make the wrappers value classes with no identity |
| Why a value class cannot have that constructor | There is no "distinct" left to guarantee |

---

## Self-test

**Q1.** `new Integer(1)` still compiles on Java 21. Why is it deprecated, and what does
`forRemoval = true` actually commit the JDK to?

<details><summary>Answer</summary>

It is deprecated because a constructor carries an unconditional language guarantee that it produces
a distinct object, and the wrappers are annotated `@jdk.internal.ValueBased` — Project Valhalla
intends to make them value classes with no identity at all, and a value class cannot keep that
guarantee. So the constructor is not merely inefficient, it is semantically incompatible with the
type's intended future. The timeline is: deprecated with `forRemoval = true` in Java 9, reaffirmed by
JEP 390 (*Warnings for Value-Based Classes*) in Java 16 which added the `@jdk.internal.ValueBased`
annotation and the `[synchronization]` compiler warning, and still present and compiling in Java 21.
`forRemoval = true` commits the JDK to *intent* — it says the API is scheduled to disappear and
turns the compiler warning on by default rather than behind `-Xlint:deprecation` — but it names no
release, imposes no deadline, and does not itself remove anything. Measured on 21.0.7, the warning is
a warning and the class compiles and runs; only `-Werror` makes it fatal.

</details>

**Q2.** You run a repo-wide replacement of `new Integer(x)` with `Integer.valueOf(x)`. What can
break, and what is the safe order?

<details><summary>Answer</summary>

Any `==` or `!=` comparison between wrapper-typed operands. `new` guarantees a fresh object, so such
a comparison was reliably `false` for every value; `valueOf` returns the shared cached instance for
values in −128..127, so the same comparison becomes `true` for small values and stays `false` for
large ones. Measured: `new Integer(3) == new Integer(3)` is false,
`Integer.valueOf(3) == Integer.valueOf(3)` is true. In practice that means a comparison that had
been silently failing starts succeeding — a retry-budget check against a threshold of 3 that never
fired begins driving applications to `AA-699 DOCUMENTS_EXHAUSTED`, in a release whose diff looks like
a lint fix, with no test covering it. The safe order is: first find every wrapper `==`, remove the
identity dependence by comparing primitives or calling `equals`, and ship that with tests; then
replace the constructors, which at that point is genuinely behaviour-preserving. Everything else the
rewrite touches — `equals`, `hashCode`, `intValue`, collection membership, arithmetic — is
unaffected either way.

</details>

**Q3.** Somebody wants a private lock and writes `private static final Integer LOCK = new
Integer(0);`. Two warnings fire. Name them and give the correct code.

<details><summary>Answer</summary>

`[removal] Integer(int) in Integer has been deprecated and marked for removal`, and
`[synchronization] attempt to synchronize on an instance of a value-based class`. Both fire with no
compiler flags at all — removal warnings are on by default, and the synchronization warning came in
with JEP 390 in Java 16 — and `-Werror` turns them into `error: warnings found and -Werror
specified`. The correct code is `private static final Object STAKE_RESTRICTION_LOCK = new Object();`.
The requirement is real: the author does need an object with a distinct identity. The error is the
type. `Integer` is `@jdk.internal.ValueBased`, so its identity is not something to build on, and the
trap is that "cleaning up" the deprecated constructor to `Integer.valueOf(0)` makes it much worse —
measured, a `static final Integer` initialised to a small value is `==` to
`Integer.valueOf` of that value, so the monitor becomes the process-wide shared cached instance that
any other code in the JVM can also acquire.

</details>

**Q4.** Read the bytecode difference between `new Integer(3)` and `Integer.valueOf(3)` instruction by
instruction. How many allocations does each guarantee?

<details><summary>Answer</summary>

Measured with `javap -p -c` on 21.0.7, `new Integer(3)` compiles to `new` / `dup` / `iconst_3` /
`invokespecial #9 // Method java/lang/Integer."<init>":(I)V` / `areturn`. `new` allocates a zeroed
`Integer` on the heap and pushes the reference — the allocation is committed at that instruction,
before any field is written, and it is unconditional. `dup` copies the reference because
`invokespecial` will consume one and `areturn` needs the other. `iconst_3` pushes the argument.
`invokespecial` runs `<init>` and consumes the duplicate. Four instructions, exactly one guaranteed
16-byte heap allocation, every single call. `Integer.valueOf(3)` compiles to `iconst_3` /
`invokestatic #12 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;` / `areturn` — two
instructions, and because 3 is inside the cache range the factory returns
`IntegerCache.cache[i + (-IntegerCache.low)]`, an array read, so **zero** allocations. Outside the
cache range `valueOf` falls back to `return new Integer(i);` and allocates one, so the win is
conditional on the value — but it is never worse, and the identity consequence
(`valueOf(3) == valueOf(3)` is true, `new Integer(3) == new Integer(3)` is false) applies regardless.

</details>

**Q5.** Which of `[deprecation]` and `[removal]` needs a compiler flag, and what does `-Werror` change?

<details><summary>Answer</summary>

`[deprecation]` needs `-Xlint:deprecation` to say anything more than a summary "uses or overrides a
deprecated API" note. `[removal]` is **on by default** — measured on 21.0.7, the `[removal] Integer(int)
in Integer has been deprecated and marked for removal` warning fires with no compiler flags at all,
and so does `[synchronization]`. That asymmetry is deliberate: terminal deprecation is louder than
ordinary deprecation because the API is going to stop existing, not merely stop being recommended.
`-Werror` turns any warning into `error: warnings found and -Werror specified`, so it converts the
default-on removal warning from advice into a build gate — which is the correct place to put it, since
it fails on your schedule rather than on the JDK's. The thing not to do is `@SuppressWarnings("removal")`
as a permanent measure: it restores the green build and simultaneously destroys the only inventory of
which call sites still need migrating.

</details>

**Q6.** What is `@jdk.internal.ValueBased`, which classes carry it, and what does it change about how
you write code?

<details><summary>Answer</summary>

It is the marker annotation JEP 390 (Java 16) added to identify value-based classes to the compiler.
Measured on 21.0.7, `Integer.class.getAnnotations()` returns `[@jdk.internal.ValueBased()]`, and all
eight wrappers carry it. Because it lives in `jdk.internal` you cannot apply it to your own types. Two
things change in how you write code. First, `javac` consults it to emit
`[synchronization] attempt to synchronize on an instance of a value-based class`, so any
`synchronized` block on a boxed value is flagged — correctly, because a boxed small value is the
process-wide shared cached instance and locking it is a correctness bug, with the mechanism in
`03f-internals-monitors-and-valhalla.md` and the memory-model half in guide 05 Concurrency. Second, it
is the forward-compatibility contract: it declares that the class's identity is not something the
platform guarantees to preserve, which is why the constructors are terminally deprecated and why you
should never depend on `==`, on `System.identityHashCode`, or on a wrapper as a lock. Write code that
would still be correct if two equal `Integer`s were literally indistinguishable, because that is the
direction the platform is moving.

</details>

## Open questions

- **When the wrapper constructors will actually be removed.** `forRemoval = true` commits the JDK to
  the intent and to the default-on warning, and JEP 390 ties it to Valhalla's value-class plan, but
  no JEP or release note read for this file names a target release, and they are still present in
  21.0.7 as measured. What would settle it: a JEP with a `Targeted` status naming the removal
  release, or a `java.base` API-removal entry in a release note. Any release number stated before
  then is speculation.
- **Whether `Integer.valueOf(int)`'s own fallback path will be rewritten before the constructors are
  removed.** Quoted from 21.0.7 source, `valueOf` ends with `return new Integer(i);` — the JDK calls
  its own terminally-deprecated constructor for every uncached value. That is unremarkable today
  (the JDK compiles itself with the warning suppressed) but it means the constructor cannot simply be
  deleted without an internal replacement, and no such replacement is visible in 21.0.7 source. What
  would settle it: a Valhalla JEP or an OpenJDK changeset showing the intended internal construction
  path for wrapper instances once value classes land.

---

**Leaves covered:** 1.9.13 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 662
