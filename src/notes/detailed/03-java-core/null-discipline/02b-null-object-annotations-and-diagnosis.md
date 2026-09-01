# 03 Java Core — Null discipline: the null-object pattern, annotations and diagnosis — INTERMEDIATE (§2.11, 2.11.5, 2.11.7–2.11.9)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Optional and the defaulting helpers](02a-optional-and-defaulting.md) · Next: [Reflection and dynamic access](../reflection/02-reflection.md)

`02-null-discipline.md` owns the origin of nulls, the null-in-collections matrix, and the language
constructs that treat null specially. `02a-optional-and-defaulting.md` owns `Optional` and the
defaulting helpers. This file closes §2.11 with the patterns that remove null from an API entirely,
the annotation ecosystem that documents nullability at the boundary, and how to read the NPE you
did get when a null still escaped. The question this file answers, in bold: **how do you design an
API that never hands a caller a null, and when one still escapes, how do you find it in one
reading?**

## 1. The null-object pattern and empty collections (2.11.5)

Picture a caller who receives a `Restriction` and calls `.blocks("STAKE_PLACE")` on it, no branch,
no check, every time — whether the client has three restrictions or none. That is the null-object
pattern: give the "nothing here" case a real instance that satisfies the interface and does
nothing, so the caller has no `if (x != null)` to forget. Every branch you delete this way is a
branch that can no longer be wrong.

### Why it exists

A method that sometimes returns null and sometimes returns a real object pushes a decision onto
every single caller: check, or crash. Most callers check correctly the first ten times and forget
the eleventh, usually on the code path nobody exercises in a demo — the client with zero
restrictions, the deposit with no attached bonus. The null-object pattern removes the decision by
making the "nothing" case behave, not just compile.

### How it works

`ClientRestrictions.findRestriction` never returns null. When no restriction is on file for the
key, it hands back a shared `Restriction.NONE` whose `blocks(String)` always returns `false`:

```java
public record Restriction(RestrictionKey key, boolean active) {

    public static final Restriction NONE =
            new Restriction(new RestrictionKey(null, RestrictionSource.SYSTEM_LIFECYCLE), false);

    public boolean blocks(String actionCode) {
        return active;
    }
}

public final class ClientRestrictions {

    private final Map<RestrictionKey, Restriction> byKey;

    public ClientRestrictions(Map<RestrictionKey, Restriction> byKey) {
        this.byKey = byKey;
    }

    public Restriction findRestriction(RestrictionKey key) {
        return byKey.getOrDefault(key, Restriction.NONE);
    }
}
```

The caller never branches on presence:

```java
if (restrictions.findRestriction(key).blocks("STAKE_PLACE")) {
    throw new RestrictedActionException(key);
}
```

The pattern works cleanly here because `blocks` has a meaningful identity element — a predicate
that is always false for "nothing to report." It works for a transform whose identity element is
"return the input unchanged," or a sink whose identity element is "discard silently." It does
**not** work when the caller genuinely needs to distinguish "absent" from "present and inactive,"
and for QuizStakes that distinction is real: a lifted `SELF_EXCLUDED` restriction and no
`SELF_EXCLUDED` restriction at all are different compliance states, and an audit trail that cannot
tell them apart is a finding waiting to happen. When the distinction matters, reach for `Optional`
(`02a-optional-and-defaulting.md`) or an explicit sealed result, not a null object standing in for
"I don't know."

```java
public sealed interface RestrictionLookup permits Found, NotFound {}
public record Found(Restriction restriction) implements RestrictionLookup {}
public record NotFound() implements RestrictionLookup {}
```

Pattern-matching `switch` makes the caller's exhaustiveness a compile-time check rather than a
runtime hope:

```java
String verdict = switch (lookup) {
    case Found(Restriction r) when r.key().type() == RestrictionType.SELF_EXCLUDED -> "excluded";
    case Found(Restriction r) -> "restricted:" + r.key().type();
    case NotFound() -> "clear";
};
```

See `../records-and-sealed/01a-object-methods-sealed-and-fit.md` for sealed hierarchies as generated
types and `../control-flow/01c-switch-expressions-and-patterns.md` for the exhaustiveness rule that
makes this safe.

The second half of 2.11.5 is a narrower, absolute rule: **a method whose return type is a
collection, a map, an array, or a stream never returns null.** Three reasons carry the weight. The
caller's enhanced `for` throws an NPE on a null collection and reads as if it could not fail. The
caller cannot chain `.stream()` onto null. And every call site grows a null check that the return
type already implied was unnecessary — the type `List<DocumentRequirement>` promises a list, zero
or more elements, and null breaks that promise silently until the one caller who forgot to guard
it.

```java
public final class DocumentRequirements {

    private final Map<ApplicationId, List<DocumentRequirement>> byApplication;

    public DocumentRequirements(Map<ApplicationId, List<DocumentRequirement>> byApplication) {
        this.byApplication = byApplication;
    }

    public List<DocumentRequirement> outstandingFor(ApplicationId id) {
        List<DocumentRequirement> found = byApplication.get(id);
        return found == null ? Collections.emptyList() : List.copyOf(found);
    }
}
```

The toolbox, each with its version: `List.of()` / `Map.of()` / `Set.of()` (Java 9, immutable,
reject null elements and keys — measured in `02-null-discipline.md`'s matrix), `Collections
.emptyList()` / `emptyMap()` / `emptySet()` (Java 1.5, immutable, and each returns a shared
singleton, so calling it costs nothing to allocate), `Stream.empty()`, and a zero-length array. The
one people get wrong is the canonical `toArray` argument: `list.toArray(new Movement[0])` is the
idiomatic form, and the received wisdom is that a zero-length array is not measurably slower than a
correctly-sized one on a modern JVM because the JIT can elide the allocation entirely when it proves
the array escapes nowhere else. **Unverified:** I have not run that benchmark myself; treat it as
received wisdom, not a measured claim in this file.

**Pitfall:** `Collections.unmodifiableList` (and `unmodifiableMap`, `unmodifiableSet`) return a
*view*, not an immutable copy. The underlying collection can still change, and the view changes
with it — measured in the collections matrix: `Collections.unmodifiableMap(mapWithNullKey).get
(null)` returned `1`, because the wrapper adds no null contract of its own, it just forwards. `List
.copyOf` / `Map.copyOf` / `Set.copyOf` (Java 10) are the actual copies, and they reject nulls —
`Map.copyOf` on a map holding a null key throws `NullPointerException`. Whether "return an
unmodifiable view of my internal list" is safe hinges entirely on this distinction, and usually it
is not: a caller can hold the view past the moment your object mutates the backing list, and now
they are iterating over a collection changing under them.

Fold the domain arithmetic in: `ClientRestrictions` is consulted before every money-moving action,
and at 2.8M stake reservations/day, 95k card deposits/day and 11k card withdrawals/day, the "no
restriction found" case is the overwhelming majority of calls. `Collections.emptyList()`'s shared
singleton is not a micro-optimisation here — it is the difference between allocating nothing per
call and allocating roughly 2.9M short-lived list objects a day that immediately become garbage.
Guide 02 (Java collections) owns the internals of the `List.of`/`Map.of` immutable factories — the
compact array-backed implementations and why they reject null at construction rather than on first
read — by number, not re-derived here.

**Gotcha:** returning `Collections.emptyList()` on one path and a live, mutable `ArrayList` on
another looks harmless until a caller who tested only the happy path ships code that calls `.add()`
on whatever they got back. On the empty-list day, that throws `UnsupportedOperationException` in
production. Be consistent about mutability across every return path of a method — prefer immutable
on all of them.

> A null object is a real instance that makes the "nothing here" case behave like any other case,
> and an API that returns collections should treat "empty" as the only legal way to say "nothing,"
> never null.

## 2. Nullability annotations: JSR-305, JSpecify, and enforcement (2.11.7)

Java's type system has no way to say "this reference is never null" — `String` means "a `String`
reference or null," full stop, in every position. The ecosystem bolted nullability on top with
annotations, and because no single body owned the effort, it produced at least eight incompatible
ways to spell the same word. The fragmentation is the concept: a reader who understands *why*
there are eight will not waste an afternoon hunting for the canonical one.

### Why it exists

Tooling — IDEs, static analyzers, build-time checkers — needs *something* in the source to hang a
warning on, since the compiler itself enforces nothing about nullability. Every family below exists
to answer the same question — "can this reference be null?" — for a different toolchain, and
because they arrived independently and at different times, they disagree on package, on retention,
and on what positions they can even annotate.

### How it works

| Family | Annotation names | Notes on retention / target | What actually enforces it | Status |
|---|---|---|---|---|
| JSR-305 | `javax.annotation.Nullable`, `@Nonnull`, `@CheckForNull` | `RUNTIME` retention; targets fields, methods, parameters | IDE inspections; SpotBugs/FindBugs-lineage tools | **Dormant — the JSR was never finalised.** The `com.google.code.findbugs:jsr305` jar that ships these classes is a de-facto artifact people depend on, not a JCP standard, and its dormancy is the root cause of the fragmentation this concept describes |
| JetBrains | `org.jetbrains.annotations.Nullable`, `@NotNull` | class-file retention | IntelliJ IDEA's editor inspections | Active, IDE-scoped |
| Checker Framework | `org.checkerframework.checker.nullness.qual.Nullable`, `@NonNull` | designed for `TYPE_USE` positions | The Checker Framework's Nullness Checker — a real `javac` annotation processor that fails the build | Active, sound by design; requires annotating dependencies you don't own |
| Eclipse JDT | `org.eclipse.jdt.annotation.Nullable`, `@NonNull` | targets types (`TYPE_USE`-style) | The Eclipse Java compiler's own null analysis | Active, effectively Eclipse-only |
| Spring | `org.springframework.lang.Nullable`, `@NonNull`, `@NonNullApi`, `@NonNullFields` | class-file retention | IDE support plus Spring's own tooling; Spring's reference documentation describes them as aligned with JSR-305 conventions for tool interoperability | Active. Spring's specific alignment with JSpecify on a given Spring Boot 3.x release is a version claim I could not confirm — see Open questions |
| Android / AndroidX | `androidx.annotation.Nullable`, `@NonNull` | class-file retention | Android Lint | Active, Android-scoped |
| JSpecify | `org.jspecify.annotations.Nullable`, `@NonNull`, `@NullMarked`, `@NullUnmarked` | designed for `TYPE_USE`, with an explicit written specification for generic and array positions | Any tool that adopts the spec: NullAway, the Checker Framework, IDE support | Active — a cross-ecosystem specification effort aimed at ending exactly this fragmentation |

Two facts make the mess navigable rather than paralysing.

**Insight:** annotations do nothing at runtime by themselves. An annotation is a class-file
attribute — data sitting next to a method or parameter — and nothing reads that data unless some
tool goes looking for it at build time or generates a runtime check from it. A parameter marked
`@NonNull` that receives null produces exactly no error, no exception, nothing, unless a checker ran
during compilation or a framework wrapped the method with a generated guard. Most of the families
above use `CLASS` or `RUNTIME` retention, meaning the attribute survives into the `.class` file even
though nothing in the plain JVM ever consults it; a `SOURCE`-retention annotation would not even
make it that far. `../language-substrate/02-packages-modules-annotations.md` owns retention and the
annotation mechanism itself. This is the answer to "we annotated everything and still got NPEs in
production": annotating is documentation until a checker is wired into the build.

What actually turns that documentation into an enforced guarantee, concretely: an IDE's own
inspection warns in the editor only, and a teammate on the command line or in CI never sees it. The
Checker Framework's Nullness Checker is a real annotation processor invoked by `javac` — it fails
the build on a violation, it is sound (no false negatives it claims to catch), and the cost is that
every type it reasons about, including ones in your dependencies, needs to be annotated or stubbed.
NullAway, an Error Prone plugin, is the pragmatic middle: fast, deliberately unsound at the edges
(it accepts some gaps to stay fast and low-friction), and the one most teams that adopt anything
actually adopt. The Kotlin compiler treats recognised nullability annotations as real type
information rather than warnings — covered as Concept 3 below.

JSpecify exists specifically as the answer to the fragmentation: it is a specification effort with
an explicit, written semantics for what `@Nullable` means in positions the older families were
ambiguous about, chiefly generics and arrays. The concrete ambiguity: `List<@Nullable Movement>`
says the list may hold null elements; `@Nullable List<Movement>` says the list reference itself may
be null, and says nothing about its elements. Most of the pre-JSpecify families could not express
this difference at all, because their `@Target` did not include `TYPE_USE` — a `@Nullable` on a
field or return type meant "this reference may be null" with no vocabulary for "and here is which
type argument." `TYPE_USE` as an annotation target arrived in Java 8, and it is the mechanism that
makes the distinction expressible in the first place. **Unverified:** I have not confirmed the exact
`@Target` list for every family in the table above against its own source, so treat "which older
families lack `TYPE_USE`" as the general shape rather than a per-family fact.

The practical rule for QuizStakes: annotate the boundary, not the whole codebase, and back the
annotation with a real check, because the annotation documents and the check enforces:

```java
public interface PaymentService {

    PaymentIntent authorise(ClientId clientId, Money amount, @Nullable IdempotencyKey key);
}

public final class CardPayments implements PaymentService {

    @Override
    public PaymentIntent authorise(ClientId clientId, Money amount, @Nullable IdempotencyKey key) {
        Objects.requireNonNull(clientId, "clientId");
        Objects.requireNonNull(amount, "amount");
        IdempotencyKey effectiveKey = key != null ? key : IdempotencyKey.generate();
        return PaymentIntent.authorised(clientId, amount, effectiveKey);
    }
}
```

`clientId` and `amount` carry no annotation because the boundary's convention is that unmarked
means non-null, and the constructor-time `requireNonNull` is what actually stops a null from
propagating past this method — the annotation alone would not. `key` is explicitly `@Nullable`
because idempotency is optional here, and the method generates one when the caller omits it. The
honest cost: annotating one boundary interface like `PaymentService` is an afternoon; annotating
an entire codebase and turning on a sound checker is a multi-week migration, and the practical
escape hatch teams use is running NullAway on new code only, so the payoff starts immediately
without a stop-the-world rewrite.

**Interview:** "Why doesn't `@Nullable` throw when you pass it a null?" — because it is metadata,
not a runtime check; nothing reads it unless a build-time tool or framework was told to.

**Gotcha:** two of these families in the same codebase — say Spring's `@Nullable` on one module and
JSR-305's on another — do not conflict at compile time, they just silently fail to compose: a
checker configured to trust one family says nothing about code annotated with the other.

> A nullability annotation is metadata describing an intended contract; it becomes an enforced
> guarantee only when a specific tool — a checker, a linter, a compiler plugin — is configured to
> read it and fail the build on a violation.

## 3. Package-level defaults and Kotlin interop (2.11.8)

Annotating every single reference in a codebase is unworkable — most references in most methods
are non-null, and marking each one is pure noise. Every family above therefore offers a way to flip
the default: say once, "non-null is the rule in this package," and mark only the exceptions. That
inversion, from annotating the common case to annotating the rare one, is the only form of this
that scales past a handful of files.

### Why it exists

A codebase with thousands of parameters and zero annotations tells a checker nothing. A codebase
with thousands of parameters individually marked `@NonNull` is unreadable and unmaintainable. A
package-level default gives the checker a rule it can apply everywhere and asks the author to
speak up only where reality diverges from the rule — which is rare, so the annotation burden stays
proportional to the actual risk.

### How it works

The shape is a `package-info.java` carrying a default annotation, applied automatically to every
type in that package:

```java
@org.jspecify.annotations.NullMarked
package com.quizstakes.payments;
```

JSpecify's `@NullMarked` can sit at module, package, class, or method level, with `@NullUnmarked`
as the escape hatch for the rare file that cannot yet comply — an incremental-adoption path baked
directly into the specification rather than bolted on afterward. Spring's older convention is
`@NonNullApi` on the package (parameters and return types default non-null) paired with
`@NonNullFields` (fields default non-null), applied the same way:

```java
@org.springframework.lang.NonNullApi
@org.springframework.lang.NonNullFields
package com.quizstakes.payments;
```

**Unverified:** whether `@NonNullApi`/`@NonNullFields` remain Spring's recommended form on current
Spring Boot 3.x, versus a newer JSpecify-aligned convention, I could not confirm against a specific
release and have parked it in Open questions rather than asserting a version.

The mechanism underneath most of these is a meta-annotation: the JSR-305 lineage defines
`@TypeQualifierDefault`, which an annotation like `@NonNullApi` itself carries, telling a consuming
tool "apply this qualifier by default to every element in the annotated scope." Granularity differs
between families — some default at the package boundary only, some allow class- or method-level
overrides — and the commonest way to get contradictory results in a real codebase is mixing two
families' defaults across module boundaries, where neither tool knows the other's convention
exists.

Kotlin interop is where this stops being a style preference and starts changing what compiles.
Kotlin's own type system distinguishes `String` from `String?` and enforces the distinction at
compile time. A plain Java type carries none of that information, so Kotlin models an unannotated
Java reference as a **platform type** — written `String!` in diagnostics — assignable to both a
Kotlin `String` and a Kotlin `String?`, with the null check deferred to runtime. That is a
deliberate escape valve: Kotlin trusts the Java caller rather than forcing every interop boundary to
be a nullable type. **When** the Java declaration carries a nullability annotation Kotlin
recognises, Kotlin uses it directly, and the type on the Kotlin side becomes a real, compile-time
checked `String` or `String?` instead of a platform type.

```kotlin
val restriction: Restriction = clientRestrictions.findRestriction(key) // platform type, assumed non-null
val country: String = jurisdiction.country()!!    // forced non-null assertion, throws at this line if wrong
```

The concrete failure this produces: a Kotlin caller assigns an unannotated Java platform type to a
non-nullable `val`, and if the Java method actually returns null, Kotlin's compiler-generated
intrinsic null check throws an NPE **at the assignment**, not at the eventual dereference three
lines later — which is a genuinely useful diagnostic property, not a bug, but it surprises people
who expect the crash where the null is finally used. Attribute the platform-type mechanism to the
Kotlin language reference documentation. **Unverified:** the exact list of Java annotation families
Kotlin's compiler recognises for this purpose, and the exact name of the generated intrinsic check,
I have not confirmed against that documentation directly — parked in Open questions.

So the practical consequence for a mixed QuizStakes codebase: annotating the Java side of a
boundary is what makes the Kotlin side's null safety real rather than nominal. An un-annotated Java
API is a hole straight through Kotlin's guarantees — every value crossing it becomes a platform type
on the Kotlin side, and Kotlin's compiler can no longer help.

The honest scorecard for a Java-only team, most readers here: package-level defaults paired with a
build-time checker (NullAway or the Checker Framework) is the only combination that changes runtime
outcomes. Annotations alone, without a checker wired into the build, change documentation and
nothing else. Guide 07 (Spring core) owns Spring's annotation processing machinery, and guide 12
(API design) owns the boundary-contract discipline this feeds into, both by number.

**Insight:** a Kotlin platform type is Kotlin admitting it does not know — `String!` is not "nullable
`String`," it is "I have no information, trust the caller." An annotated Java boundary converts "no
information" into a checked fact on the Kotlin side without either language changing.

**Gotcha:** mixing JSpecify's `@NullMarked` on a new module with Spring's `@NonNullApi` on an older
one in the same build is not a conflict a compiler flags — it is two independent defaults that
happen to agree most of the time and disagree exactly where it costs you a debugging session to
notice.

> A package-level nullability default inverts the annotation burden from "mark every non-null
> reference" to "mark every exception to non-null," and it only changes runtime behaviour once a
> build-time checker — or, across a Java/Kotlin boundary, Kotlin's own compiler — actually reads it.

## 4. Reading a helpful NPE message to find which link was null (2.11.9)

A helpful `NullPointerException` message is a sentence with a fixed grammar, and once you can parse
the grammar you get the answer without opening a debugger. The grammar is: `Cannot <the operation
that failed> because <the expression that was null> is null`. Two halves. The first names what you
tried to do. The second names which link in the chain was empty. The half people skip reading
carefully is the one that actually answers the question.

### Why it exists

Before this feature, `NullPointerException` carried a stack trace and a line number and nothing
else — on a line with four chained calls, the line number told you the neighbourhood, not the
house. Measured on the target JVMs here: `java -XX:+PrintFlagsFinal -version` on Oracle JDK 21.0.7
and JDK 17.0.15 both print `ShowCodeDetailsInExceptionMessages = true {manageable} {default}`; the
same grep against JDK 11.0.27 returns nothing at all — the flag does not exist there. So the
capability is absent in 11, on by default in 17 and 21, and it can be toggled at runtime through the
management interface since it is `{manageable}`. Turning it off on JDK 21 with
`-XX:-ShowCodeDetailsInExceptionMessages` was measured directly: every message below returned
literal `null` from `getMessage()` instead of its text — the JVM did not merely shorten the message,
it dropped it entirely.

### How it works

Take the worked example, a chained record access, verbatim from measurement:

```java
record Jurisdiction(String country, String subdivision) {}
record Address(Jurisdiction jurisdiction) {}
record Application(Address address) {}

Application app = new Application(new Address(null));
app.address().jurisdiction().country().length();
```

produces:

```
Cannot invoke "Ver8$Jurisdiction.country()" because the return value of "Ver8$Address.jurisdiction()" is null
```

On the line `app.address().jurisdiction().country().length()` there are four candidate nulls:
`app`, the result of `.address()`, the result of `.jurisdiction()`, the result of `.country()`. The
message names exactly one: the return value of `Address.jurisdiction()`. Not `app`, not
`.address()`, not `.country()`. That single line of output is the entire value of the feature —
it replaces however many minutes it would take to step through the chain in a debugger.

The vocabulary, built from measured messages on the same JVM:

| Message fragment | What it means | Measured example |
|---|---|---|
| `Cannot invoke "T.m()"` | An instance method call was attempted on a null reference | `Cannot invoke "String.trim()" because the return value of "java.util.Map.get(Object)" is null` |
| `because the return value of "T.m()" is null` | The null came from a method call, not a stored variable | Same example — `Map.get(Object)` returned null |
| `because "<localN>" is null` | The null is a local variable, and its source name was not available | `Cannot store to int array because "<local2>[1]" is null` |
| `because "name" is null` | The null is a local, parameter, or field whose real name **is** available | `Cannot invoke "java.lang.Comparable.compareTo(Object)" because "k1" is null` |
| `Cannot read the array length because "x" is null` | An array-length read (`.length` on an array, or an operation that needs it) on a null array | `Cannot read the array length because "value" is null` |
| `Cannot store to int array because "x[1]" is null` | An array *store*, with the index folded into the description | `Cannot store to int array because "<local2>[1]" is null` |
| `Cannot invoke "java.lang.Integer.intValue()"` (or similarly named unboxing accessor) | An **unboxing** NPE — no method call visible at the source line at all | `Cannot invoke "java.lang.Integer.intValue()" because "<local0>" is null` from `int j = i;` where `Integer i = null` |

`k1` in the `Comparable.compareTo` example is not a name you chose — it is a parameter name from
inside the JDK's own compiled code (`TreeMap`'s comparison path), which is why it reads as a real
identifier rather than a slot number. `key` in `Hashtable.put(null, 1)`'s message
(`Cannot invoke "Object.hashCode()" because "key" is null`) is the same story. See
`../primitives-and-conversions/03a-promotion-boxing-and-inference.md` for the unboxing NPE's
mechanism in full.

**Insight:** the `<localN>` versus real-name split is not random — it is the presence or absence of
the `LocalVariableTable` attribute in the method's `Code` attribute. The JVM builds the description
by walking the bytecode backwards from the failing instruction; for a local variable, recovering
the source name requires that table, and `javac` only emits it when compiled with `-g` or
`-g:vars`. Code inside `java.base` ships with that information, which is why the JDK's own methods
give you `key`, `k1`, `value` in these messages, while a production jar built with default flags
gives you `<local0>`, `<local1>`, `<local2>`. `../language-substrate/03a-internals-class-file-format
.md` owns the `Code` attribute's structure in full; the operational rule that follows from it is:
**build production jars with `-g:vars` (or `-g:lines,vars`) if you want these messages to name
things instead of numbering them.** The cost is a marginally larger class file; `-g:lines` alone —
which most build setups already enable, since it is what gives a stack trace its line numbers — is
not the same flag and does not recover local names.

Five limits worth carrying into a debugging session so the message is not over-trusted. It
describes exactly one null; if a line has two candidates, it names whichever failed first, and
fixing that one may reveal the second on the next run. It is derived from bytecode, so a lambda
body or a compiler-generated bridge method describes the *compiled* shape, which can look
unfamiliar next to your source. It says nothing about *why* the value was null, only where — the
"why" is still yours to trace. A `getMessage()` returning literal `null` means the flag is off, not
that the JVM had no explanation — measured directly above. And an NPE thrown deliberately by library
code carries no derived detail at all: `Objects.requireNonNull(null, "clientId")` produces the bare
message `clientId`, because that string is what you supplied, not something the JVM derived from
bytecode.

**Insight:** a short, meaningful NPE message means a human checked deliberately and told you what
was missing — that is good news, it is doing its job. A long, mechanically derived message means
nobody checked, and the JVM is doing the diagnosis for you instead.

The version framing matters because a lot of still-circulating advice predates it: material written
against Java 8 or 11 will tell you an NPE carries no useful information beyond a line number, and
habits built under that constraint — wrapping every risky call in a try/catch purely to attach
context, splitting a five-call chain across five separate statements just to isolate the null — are
largely obsolete on 17 and 21, where the message already tells you which call in the chain failed.
The commonly-cited origin story is that JEP 358 delivered this capability in JDK 14 disabled by
default, and that JDK bug id 8233014 turned it on by default in JDK 15. **Unverified:** I could not
verify either identifier against openjdk.org directly (the fetch returned HTTP 403); the 11 → 17 →
21 boundary itself is measured and solid, the specific JEP number and bug id are not confirmed in
this file. When a production NPE shows a bare `null` message, the first thing to check is the
`{manageable}` flag, not the JVM version.

**Interview:** "How do you find which object in a chained call was null without a debugger?" — read
the second half of the message, after "because"; on 17 and 21 it names the exact call or variable
that returned null, and it is on by default.

Close it out on the domain: a `DEP-301 CAPTURED` deposit is being scored for a bonus, and the
scoring code walks `deposit.application().address().jurisdiction().country()` to check
jurisdiction eligibility. The `Application`'s address chain is incomplete — the address was
captured before the jurisdiction lookup ran — and the call throws:

```
Cannot invoke "String.length()" because the return value of "Jurisdiction.country()" is null
```

The one-line diagnosis: `Jurisdiction.country()` returned null, which means this `Address` record
was built with a null `Jurisdiction.country`, not that `deposit`, `application()`, or `address()`
were missing — so the fix belongs in whatever populated the `Jurisdiction`, not in a defensive null
check three calls downstream.

**Gotcha:** No gotcha on the grammar itself — it is stable across a chain of any length. The only
trap is trusting it past its scope: it names one null on one line, nothing about the call stack
above it.

> A helpful NPE message states, in order, the operation that failed and the specific expression
> that was null; on Java 17 and 21 with the default JVM flags, the second half is the direct answer
> to "which link in the chain was empty," recoverable without a debugger.

## Pitfalls

### `Collections.unmodifiableList` on a collection makes that collection immutable

**Wrong**

```java
Map<String, Integer> mutable = new HashMap<>();
mutable.put(null, 1);
Map<String, Integer> view = Collections.unmodifiableMap(mutable);
System.out.println(view.get(null));   // 1
mutable.put(null, 2);
System.out.println(view.get(null));   // 2 - the "immutable" view moved with the source
```

**Right**

```java
Map<String, Integer> mutable = new HashMap<>();
mutable.put("clientId", 42);
Map<String, Integer> frozen = Map.copyOf(mutable);   // an actual, independent copy
mutable.put("clientId", 99);
System.out.println(frozen.get("clientId"));           // 42 - unaffected
```

**Why people believe it:** the method name literally says "unmodifiable," and calling `.put()` on
the returned reference does throw `UnsupportedOperationException` — so the surface behaviour
matches the name right up until someone mutates the *original* reference instead, and the view
reflects that change too.

### Returning null from a method whose return type is a collection saves an allocation

**Wrong**

```java
public List<DocumentRequirement> outstandingFor(ApplicationId id) {
    List<DocumentRequirement> found = load(id);
    return found.isEmpty() ? null : found;   // caller's for-each throws NPE on the empty case
}
```

**Right**

```java
public List<DocumentRequirement> outstandingFor(ApplicationId id) {
    List<DocumentRequirement> found = load(id);
    return found.isEmpty() ? Collections.emptyList() : found;   // shared singleton, zero allocation
}
```

**Why people believe it:** returning null looks like it avoids constructing an empty list — but
`Collections.emptyList()` already returns a cached singleton, so the "optimisation" costs the same
zero allocations while adding a null check to every call site that the type signature promised was
unnecessary.

### An `@NonNull` annotation stops a null from being passed at runtime

**Wrong**

```java
public void authorise(@NonNull ClientId clientId, Money amount) {
    ledger.reserve(clientId, amount);   // compiles and runs fine even if clientId is null
}
```

```java
authorise(null, amount);   // no exception here; the annotation is metadata, not a guard
```

**Right**

```java
public void authorise(@NonNull ClientId clientId, Money amount) {
    Objects.requireNonNull(clientId, "clientId");   // the actual enforcement
    ledger.reserve(clientId, amount);
}
```

**Why people believe it:** the annotation reads like a language keyword, and IDEs do underline the
violation in red — but that warning is the IDE's own inspection running at edit time, not a check
the compiled `.class` file carries, so a caller built by a different toolchain, or one whose IDE
inspection is silenced, sails past it.

### A helpful NPE message always tells you why the value was null

**Wrong**

```java
Objects.requireNonNull(deposit.application(), "application");
// getMessage() -> "application"
// looks unhelpful compared to the JVM-derived messages, so it's assumed to be a lesser feature
```

**Right**

```java
// Recognise the two message shapes as different tools instead of ranking them:
// a bare message like "application" means a developer checked deliberately at that exact
// point and told you what was missing.
// A long, JVM-derived message like:
//   Cannot invoke "X.y()" because the return value of "Z.w()" is null
// means nobody checked and the JVM reconstructed the location for you.
// Both are informative; neither one explains the root cause, only the location.
Objects.requireNonNull(deposit.application(), "application");
```

**Why people believe it:** the derived messages are longer and more detailed-looking, so a short,
supplied message reads as if the feature "didn't work" here — when in fact it correctly recognised
there was nothing to derive, because the exception was thrown explicitly rather than by the JVM
walking bytecode.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Null-object pattern | Real instance for "nothing," identity-element behaviour; fails when absent vs. present-empty must be distinguishable |
| Collection-returning method | Never returns null; use `List.of()`/`Map.of()`/`Set.of()` (Java 9), `Collections.emptyList()` et al. (Java 1.5, shared singleton), `Stream.empty()`, or a zero-length array |
| `Collections.unmodifiableX` | A live view — mutates with its source; not a copy |
| `List.copyOf` / `Map.copyOf` / `Set.copyOf` | Actual immutable copies (Java 10); reject null elements/keys |
| JSR-305 (`javax.annotation.Nullable`) | Never finalised as a JCP standard; the `jsr305` jar is a de-facto artifact, root cause of the annotation split |
| Annotations at runtime | Do nothing by themselves — metadata only; enforcement requires a checker (Checker Framework, NullAway) or framework support |
| JSpecify | Cross-ecosystem spec with explicit `@Nullable` semantics for generic/array (`TYPE_USE`) positions |
| `@NullMarked` / `@NonNullApi` | Package (or module/class/method)-level default flip: non-null unless marked otherwise |
| Kotlin platform type | `String!` — unannotated Java type, assignable to `String` or `String?`, null-checked at runtime on assignment to a non-null `val` |
| `ShowCodeDetailsInExceptionMessages` | Absent in JDK 11; `true` and `{manageable}` by default in JDK 17 and 21 (measured) |
| NPE grammar | `Cannot <operation> because <expression> is null` — the clause after "because" names the actual null |
| `<localN>` in an NPE message | Missing `LocalVariableTable`; compile with `-g:vars` to get real names instead of slot numbers |
| `Objects.requireNonNull(null, "msg")` | `getMessage()` returns exactly `"msg"` — no derived code details, because you supplied it |

## Self-test

**Q1.** Why does the null-object pattern fail for a lookup where the caller needs to distinguish
"no restriction on file" from "restriction present but lifted"?

<details><summary>Answer</summary>

Because the null object collapses both cases into a single instance whose methods report "nothing
to worry about" — a `blocks()` that returns `false`. That is correct behaviour for "no restriction,"
but "present and lifted" is a distinct, meaningful state for an audit trail (it proves a check was
made and later reversed), and a single `NONE` instance cannot represent both. Use a sealed result
type or `Optional` when the distinction itself carries information, not just when the absence needs
a safe default.

</details>

**Q2.** What does `Collections.unmodifiableMap(mapWithNullKey).get(null)` return, and why does that
demonstrate the view is not an immutable copy?

<details><summary>Answer</summary>

It returns whatever value is currently associated with the null key in the underlying map —
measured as `1` in this file's harness. The wrapper only intercepts mutating calls made through
itself (`put`, `remove`, and every other mutator) by throwing `UnsupportedOperationException`; it does not clone
the data or block changes made directly on the original map reference. So the view's contents track
the source's contents in real time, which is the opposite of what "immutable" implies.

</details>

**Q3.** Why is JSR-305 described as "dormant" rather than as a standard, and what practical
consequence follows from that?

<details><summary>Answer</summary>

The JSR was never finalised by the JCP, so `javax.annotation.Nullable` and `@Nonnull` never became
an official Java standard. What ships instead is `com.google.code.findbugs:jsr305`, a de-facto jar
maintained outside any standards process. The practical consequence is that no tool is obligated to
recognise it, no successor spec formally builds on it, and every later family (JetBrains, Checker
Framework, JSpecify) had to either duplicate the idea under its own package or attempt to bridge to
it informally — which is the direct cause of the fragmentation this concept describes.

</details>

**Q4.** An IDE underlines a null-safety violation in red, but the same code compiles cleanly with
`javac` on the command line and passes CI. What does that tell you about the annotation involved?

<details><summary>Answer</summary>

It tells you that whatever annotation triggered the underline is being read by the IDE's own
inspection engine, not by anything wired into the actual build. Annotations carry no runtime
behaviour on their own; the IDE chose to warn as a courtesy, but `javac` performs no nullability
analysis by default, and unless a build-time processor like the Checker Framework or NullAway is
configured in the CI pipeline, nothing will stop the same violation from shipping.

</details>

**Q5.** What is a Kotlin platform type, and what changes about it once the underlying Java method
is annotated with a nullability annotation Kotlin recognises?

<details><summary>Answer</summary>

A platform type (written `String!` in diagnostics) is how Kotlin represents a Java-declared type
that carries no nullability information — it is assignable to both a non-null `String` and a
nullable `String?`, with the actual null check deferred to runtime at the point of use. Once the
Java declaration carries a nullability annotation Kotlin recognises, Kotlin drops the platform type
and treats the value as a genuine `String` or `String?`, checked at compile time like any native
Kotlin type — the annotation converts "unknown" into a real, statically enforced fact.

</details>

**Q6.** Given the measured message `Cannot invoke "Ver8$Jurisdiction.country()" because the return
value of "Ver8$Address.jurisdiction()" is null`, which specific object was null, and which three
other candidate expressions on the same call chain were *not* the cause?

<details><summary>Answer</summary>

The null was the return value of `Address.jurisdiction()` — that call returned null. The chain was
`app.address().jurisdiction().country().length()`; the message rules out `app` being null (it was
not), the return value of `.address()` being null (it was not, since `jurisdiction()` was called
successfully on it), and the return value of `.country()` being null (that call was never reached,
because `jurisdiction()` had already returned null first).

</details>

**Q7.** Why does a production jar built without `-g:vars` produce `Cannot invoke "String.trim()"
because "<local2>" is null` instead of naming the actual variable, while the same kind of message
inside `java.base` always shows a real name?

<details><summary>Answer</summary>

The JVM recovers a local variable's source name from the `LocalVariableTable` attribute in the
method's `Code` attribute. `javac` only emits that table when compiled with `-g` or `-g:vars`; a
default build omits it, so the JVM falls back to printing the local variable's slot index instead,
shown as `<localN>`. The JDK's own `java.base` classes are compiled with that debug information
retained, which is why methods like `Hashtable.put` or `TreeMap`'s comparison path report real
parameter names (`key`, `k1`) in their NPE messages instead of slot numbers.

</details>

**Q8.** Why does `Objects.requireNonNull(null, "clientId")` produce the bare message `clientId`
instead of a longer, JVM-derived description, and is that a defect in the feature?

<details><summary>Answer</summary>

It is not a defect. The helpful-NPE machinery only derives a description when the JVM itself
constructs the exception from a failed bytecode instruction, walking backwards to identify the
null expression. Here, the exception is thrown explicitly by library code that was handed the
string `"clientId"` as its message argument — there is nothing for the JVM to derive, because a
human already supplied the answer. A short, deliberate message like this is a sign someone checked
proactively, which is the better outcome, not a lesser one.

</details>

## Open questions

1. The precise JEP number (commonly cited as JEP 358) and JDK bug id (commonly cited as
   JDK-8233014) behind helpful NPE messages shipping disabled in JDK 14 and enabled by default in
   JDK 15 — openjdk.org returned HTTP 403 on the primary-source lookup attempted for this file.
   Settle with direct access to the JEP index or the JDK Bug System.
2. Whether Spring's recommended nullability convention on current Spring Boot 3.x releases is still
   `@NonNullApi`/`@NonNullFields`, or has moved to a JSpecify-aligned form. Settle against the
   Spring Framework reference documentation for the specific release in question.
3. The exact `@Target` element types (in particular, whether `TYPE_USE` is included) for each
   pre-JSpecify annotation family in the Concept 2 table. Settle by inspecting each family's
   annotation source directly.
4. The exact list of Java nullability annotation families the Kotlin compiler recognises for
   platform-type resolution, and the precise name of the generated intrinsic null-check. Settle
   against the Kotlin language reference documentation's Java interoperability section.

---

**Leaves covered:** 2.11.5, 2.11.7, 2.11.8, 2.11.9 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 759
