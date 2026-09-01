# 03 Java Core — Diagnostic harnesses — the constructor-calls-an-overridable-method trap — BUILD IT (§4.8 (4.8.2))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The puzzler harness, snippets 9–15](05f-puzzler-harness-part-two.md) · Next: [Class-initialization order](05g-class-initialization-order.md)

One harness, one printed sequence. The leaf is `[PROVE]`, and the printed sequence *is* the
argument — so every line of output below was captured from a real run on **Oracle JDK 21.0.7
(build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, compressed oops on. Nothing here is
predicted. The class-initialization order this trap depends on is proved separately in
[Class-initialization order](05g-class-initialization-order.md).

---

## 4.8.2 The constructor that calls an overridable method `[PROVE]`

An `Application` object becomes polymorphic before it becomes initialized. That is the whole
shape of the bug.

When you write `new OnboardingApplication("GB-ENG", 42000)`, the JVM allocates the object,
zeroes every field, and then runs `OnboardingApplication`'s constructor. The first thing that
constructor does — always, whether you wrote it or `javac` inserted it — is call the
superclass constructor. So `Application`'s constructor body runs while
`OnboardingApplication`'s own field initializers have not executed yet. But the object's
class pointer already says `OnboardingApplication`, so a virtual call from inside
`Application`'s constructor dispatches to `OnboardingApplication`'s override. That override
reads fields that are still at their default values.

The five states an object passes through, in order:

| Step | What runs | What the subclass's fields hold |
|---|---|---|
| 1 | allocation, header written, all fields zeroed | defaults (`null`, `0`, `false`) |
| 2 | subclass constructor entered, `super` call dispatched | defaults |
| 3 | superclass constructor body — **virtual dispatch already works here** | defaults |
| 4 | subclass instance field initializers and instance blocks | assigned, textual order |
| 5 | subclass constructor body statements | assigned |

Step 3 is the gap. Everything the trap does lives in the distance between step 3 and step 4.

### The harness

```java
import java.util.ArrayList;
import java.util.List;

/** 4.8.2 — a superclass constructor calling an overridable method. */
public class ConstructionTrap {

    /** The base onboarding case. Its constructor asks the subclass what gates apply. */
    static abstract class Application {
        private final String statusCode;

        Application(String statusCode) {
            this.statusCode = statusCode;
            // The trap: virtual dispatch on a subclass that has not run its own
            // field initializers yet.
            System.out.println("  [Application ctor] gates during construction = " + initialGates());
        }

        /** Overridable. That is the whole problem. */
        List<String> initialGates() {
            return List.of("AO-110 CONTACT_VERIFICATION_PENDING");
        }

        final String statusCode() {
            return statusCode;
        }
    }

    static final class OnboardingApplication extends Application {
        private final String jurisdiction;          // final, set from a ctor argument
        private final int maxStakeMinorUnits;       // primitive, reads 0 mid-construction
        private final List<String> requiredDocuments = new ArrayList<>();

        OnboardingApplication(String jurisdiction, int maxStakeMinorUnits) {
            super("AO-120 ADDRESS_PENDING");        // runs BEFORE the three lines below
            this.jurisdiction = jurisdiction;
            this.maxStakeMinorUnits = maxStakeMinorUnits;
            this.requiredDocuments.add("PROOF_OF_ADDRESS");
        }

        @Override
        List<String> initialGates() {
            return List.of(
                    "jurisdiction=" + jurisdiction,
                    "maxStakeMinorUnits=" + maxStakeMinorUnits,
                    "requiredDocuments=" + requiredDocuments);
        }
    }

    public static void main(String[] args) {
        System.out.println("constructing OnboardingApplication(\"GB-ENG\", 42000):");
        OnboardingApplication application = new OnboardingApplication("GB-ENG", 42000);
        System.out.println("  [after construction]      gates = " + application.initialGates());
        System.out.println("  [after construction] statusCode = " + application.statusCode());
    }
}
```

```bash
javac -Xlint:all ConstructionTrap.java   # exit 0, no warnings
java ConstructionTrap
```

```console
constructing OnboardingApplication("GB-ENG", 42000):
  [Application ctor] gates during construction = [jurisdiction=null, maxStakeMinorUnits=0, requiredDocuments=null]
  [after construction]      gates = [jurisdiction=GB-ENG, maxStakeMinorUnits=42000, requiredDocuments=[PROOF_OF_ADDRESS]]
  [after construction] statusCode = AO-120 ADDRESS_PENDING
```

Same method, same object, two reads, three fields, all different. The first read happened at
step 3; the second at step 5-plus.

### A `final` field reads as `null` too

`jurisdiction` is declared `private final String`. It is assigned from a constructor
argument that is definitely non-null (`"GB-ENG"`). It reads `null`.

What `final` on an instance field actually guarantees is two things, and neither of them is
"set before anyone can look". First, the compiler's definite-assignment analysis guarantees
the field is assigned **exactly once on every path** that reaches the end of a constructor —
not before that constructor's `super` call, and not before that constructor runs at all.
Second, the JVM inserts a **final-field freeze** at the end of the constructor, so a thread
that reads the object through a reference published *after* construction completed is
guaranteed to see the constructor's writes to `final` fields without any further
synchronization. Both guarantees are anchored to *the end of construction*. Mid-construction,
`final` buys you nothing at all — the field is simply an ordinary field holding its default.
`final` semantics and constant folding belong to
[`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md);
safe publication belongs to
[`../immutability-and-design/02-immutability.md`](../immutability-and-design/02-immutability.md);
the memory model itself is guide 05's.

**Insight:** the JVM has no notion of a "partly constructed" type. The class word in the
object header is final from allocation onwards, so the vtable is complete from allocation
onwards. Field values catch up afterwards. Polymorphism is a property of the *type*;
initialization is a property of the *instance*. They are not synchronized with each other.

### A primitive reads as its default, not as garbage

`maxStakeMinorUnits` reads `0`, not garbage — the JVM zeroes the whole object on allocation,
so there is no uninitialized memory to read. That is exactly what makes this the dangerous
variant: `0` is a plausible number. A `null` jurisdiction blows up on the next
`jurisdiction.equals` call in the same request and you get a stack trace pointing at the
constructor. A `maxStakeMinorUnits` of `0` silently produces a limit set where every stake is
rejected, or — with the comparison written the other way — one where no stake is ever
rejected. Both pass a unit test that only asserts "the object was created". This is the
version of the bug that reaches production, and it reaches production through a `Money`
amount or a count.

**Pitfall:** you cannot detect this by null-checking in the overridden method. A guard like
`if (jurisdiction == null) throw new IllegalStateException()` turns the silent bug into a
loud one for reference fields but does nothing for `int`, `long` or `boolean`, where the
default is a legal value. The fix has to be structural, not defensive.

### The `this` escape

The same defect with the arrow reversed: instead of the superclass constructor *calling into*
a not-yet-initialized subclass, it *hands out* a reference to the not-yet-initialized object.
`ApplicationHistory.register(applicationId, this)` inside `Application`'s constructor puts a
half-built `OnboardingApplication` into a process-wide map, where any other code — and, if
the registry is shared, any other thread — can find it.

```java
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 4.8.2 continued — the `this` escape, and the static-factory fix. */
public class ThisEscape {

    /** A process-wide registry that other code reads. */
    static final class ApplicationHistory {
        private static final Map<String, Application> BY_ID = new LinkedHashMap<>();

        static void register(String applicationId, Application application) {
            BY_ID.put(applicationId, application);
            System.out.println("  [ApplicationHistory] registered " + applicationId
                    + " -> " + application.audit());
        }

        static Application lookup(String applicationId) {
            return BY_ID.get(applicationId);
        }
    }

    static abstract class Application {
        private final String applicationId;

        Application(String applicationId) {
            this.applicationId = applicationId;
            ApplicationHistory.register(applicationId, this);   // `this` escapes here
        }

        abstract String audit();

        final String applicationId() {
            return applicationId;
        }
    }

    static final class OnboardingApplication extends Application {
        private final String jurisdiction;
        private final List<String> requiredDocuments;

        OnboardingApplication(String applicationId, String jurisdiction) {
            super(applicationId);
            this.jurisdiction = jurisdiction;
            this.requiredDocuments = new ArrayList<>(List.of("PROOF_OF_ADDRESS"));
        }

        @Override
        String audit() {
            return "AO-120 ADDRESS_PENDING jurisdiction=" + jurisdiction
                    + " requiredDocuments=" + requiredDocuments;
        }
    }

    /** The fix that generalises: construct, then initialise, then publish. */
    static final class SafeOnboardingApplication {
        private final String applicationId;
        private final String jurisdiction;
        private final List<String> requiredDocuments;

        private SafeOnboardingApplication(String applicationId, String jurisdiction,
                                         List<String> requiredDocuments) {
            this.applicationId = applicationId;
            this.jurisdiction = jurisdiction;
            this.requiredDocuments = List.copyOf(requiredDocuments);
        }

        static SafeOnboardingApplication open(String applicationId, String jurisdiction) {
            var application = new SafeOnboardingApplication(
                    applicationId, jurisdiction, List.of("PROOF_OF_ADDRESS"));
            System.out.println("  [factory] fully constructed: " + application.audit());
            return application;
        }

        String audit() {
            return "AO-120 ADDRESS_PENDING applicationId=" + applicationId
                    + " jurisdiction=" + jurisdiction
                    + " requiredDocuments=" + requiredDocuments;
        }
    }

    public static void main(String[] args) {
        System.out.println("escaping version:");
        new OnboardingApplication("APP-7201", "GB-ENG");
        System.out.println("  [registry read after ctor returned] "
                + ApplicationHistory.lookup("APP-7201").audit());

        System.out.println("static-factory version:");
        SafeOnboardingApplication.open("APP-7202", "GB-SCT");
    }
}
```

```bash
javac -Xlint:all ThisEscape.java   # exit 0, no warnings
java ThisEscape
```

```console
escaping version:
  [ApplicationHistory] registered APP-7201 -> AO-120 ADDRESS_PENDING jurisdiction=null requiredDocuments=null
  [registry read after ctor returned] AO-120 ADDRESS_PENDING jurisdiction=GB-ENG requiredDocuments=[PROOF_OF_ADDRESS]
static-factory version:
  [factory] fully constructed: AO-120 ADDRESS_PENDING applicationId=APP-7202 jurisdiction=GB-SCT requiredDocuments=[PROOF_OF_ADDRESS]
```

This is strictly worse than the null read, for two reasons. The null read is *transient* —
one bad observation inside one constructor, and the object is correct a microsecond later.
The escape is *durable*: the reference is now in a map that outlives the constructor, and any
consumer that read it during the window kept whatever it derived from those default values.
And the escape adds a memory-model failure the null read does not have. Publishing a
reference before the final-field freeze means another thread can legally observe the object
with some fields assigned and some still zero, indefinitely, with no data race on the fields
themselves — the race is on the publication. Registering a listener, adding to a static
collection, and `new Thread(this).start()` inside a constructor are the same bug wearing
three costumes.

### What the compiler and tooling actually say

Checked rather than asserted. `javac -Xlint:all` on both harnesses above exited `0` with no
diagnostic of any kind:

```bash
javac -Xlint:all ConstructionTrap.java   # no output, exit 0
javac -Xlint:all ThisEscape.java         # no output, exit 0
```

`javac` does not warn about this, and that is not an oversight — calling an overridable method
from a constructor is legal Java and occasionally deliberate (a template-method base that only
reads *its own* fields). The compiler cannot tell the two apart. Static analysers can, and
these check names are verified against their published catalogues:

| Tool | Check identifier | Verified against |
|---|---|---|
| SpotBugs | `MC_OVERRIDABLE_METHOD_CALL_IN_CONSTRUCTOR` | `spotbugs/etc/findbugs.xml`, detector `edu.umd.cs.findbugs.detect.FindOverridableMethodCall` |
| SpotBugs | `MC_OVERRIDABLE_METHOD_CALL_IN_CLONE` | same detector — `clone()` has the identical hazard |
| SpotBugs | `MC_OVERRIDABLE_METHOD_CALL_IN_READ_OBJECT` | same detector — deserialization has it too |
| PMD | `ConstructorCallsOverridableMethod` (errorprone ruleset) | PMD rule docs: "Reports calls to overridable methods on `this` during object initialization." |
| Checkstyle (sevntu) | `OverridableMethodInConstructorCheck` | sevntu-checks published API docs |

**Unverified:** the ErrorProne check names commonly quoted for this defect —
`ConstructorInvokesOverridable` and `ConstructorLeaksThis` — do **not** appear in ErrorProne's
published bug-pattern catalogue at `errorprone.info/bugpatterns` as fetched for this note
(both per-pattern pages return HTTP 404, and a scan of the catalogue's `Constructor`-containing
entries lists only `ChainingConstructorIgnoresParameter`,
`AssistedInjectAndInjectOnSameConstructor`, `InjectOnConstructorOfAbstractClass`,
`AssistedInjectAndInjectOnConstructors`, `PrivateConstructorForNoninstantiableModule` and
`PrivateConstructorForUtilityClass`). Do not quote those two names as ErrorProne checks
without confirming against the version you actually run. Tooling ownership is guide 16's.

### The fixes, ranked

| Rank | Fix | What it buys | What it costs |
|---|---|---|---|
| 1 | Make the class `final` | no subclass, so no override, so no gap | closes extension entirely |
| 2 | Make the called method `final` or `private` | dispatch is static; the base reads only its own fields | subclasses cannot customise the hook |
| 3 | Static factory: construct, then initialise, then publish | generalises; also fixes the escape | one more level of indirection |

Rank 2, enforced by the compiler — `final` on `initialGates()` makes the override a
compile error, so the trap cannot be reintroduced by a later change:

```bash
javac FinalMethodFix.java
```

```console
FinalMethodFix.java:10: error: initialGates() in OnboardingApplication cannot override initialGates() in Application
        java.util.List<String> initialGates() { return java.util.List.of("AO-120 ADDRESS_PENDING"); }
                               ^
  overridden method is final
1 error
```

Rank 3 is `SafeOnboardingApplication` above, already compiled and run: the constructor is
`private` and does nothing but assign fields, the factory does the work, and nothing sees the
reference until the constructor has returned. `List.copyOf` on the way in makes the copy at
the only moment where a copy is guaranteed to be of a complete list. Instance initialization
order in detail is
[`../classes-and-initialization/01b-initialization-order.md`](../classes-and-initialization/01b-initialization-order.md);
overriding and virtual dispatch are
[`../inheritance-and-dispatch/01-basics.md`](../inheritance-and-dispatch/01-basics.md).

**Interview:** "Why is calling an overridable method from a constructor a bug?" — Because the
superclass constructor runs before the subclass's field initializers, so the override executes
against a subclass whose fields are all still at their defaults; `final` fields included, and
primitives read as `0` rather than failing loudly.

### Diff vs the real one

The "real one" here is a production framework base class that legitimately calls into its
subclass during construction — the pattern this harness is a stripped-down model of.

| Axis | This harness | A real framework base class |
|---|---|---|
| Edge cases | one hierarchy level, one hook method | hooks called from several constructor overloads, plus `readObject` and `clone` paths, plus deep hierarchies where an intermediate class also overrides |
| Intrinsics | none; `System.out.println` dominates the whole run | none available — there is no intrinsic that can make a field readable before it is written |
| Serialization | not `Serializable` | `readObject` reconstructs without running constructors at all, so a hook called from `readObject` sees defaults for exactly the same reason; SpotBugs has a separate pattern for it |
| Null policy | the harness *shows* the `null`; no guard | frameworks that must do this pass the needed values as `super` arguments so the base never reads a subclass field |
| Thread safety | single-threaded, so only the null read bites | the escape variant makes the partly-built object visible to other threads before the final-field freeze; that is the version that produces unreproducible bugs |
| Allocation tricks | none; each `initialGates()` call allocates a fresh `List.of` | a real base caches the gate set in a `final` field computed once, which is precisely why it must be computed *after* construction |
| Why the JDK bothers | — | the JDK largely refuses to: `String`, `Integer`, `Optional` and the record classes are `final`; where the JDK does expose a constructor hook it makes it `protected final` or documents the hazard, and `Thread`'s `init` chain is careful never to publish `this` |

> **Definition.** A constructor that invokes an overridable method invokes it on an object that
> is already fully polymorphic and not yet initialized at all, so the override reads every
> subclass field — `final` ones included — at its default value.

---

## Pitfalls

### Calling an overridable method from a constructor

**Wrong**

```java
static abstract class Application {
    Application() { System.out.println(initialGates()); }
    List<String> initialGates() { return List.of("AO-110 CONTACT_VERIFICATION_PENDING"); }
}
static final class OnboardingApplication extends Application {
    private final String jurisdiction = "GB-ENG";
    @Override List<String> initialGates() { return List.of("jurisdiction=" + jurisdiction); }
}
```

Captured from the harness run above:

```console
  [Application ctor] gates during construction = [jurisdiction=null, maxStakeMinorUnits=0, requiredDocuments=null]
```

**Right**

Make the hook `final`, so the compiler forbids the override — the trap cannot be reintroduced
by a later change:

```console
FinalMethodFix.java:10: error: initialGates() in OnboardingApplication cannot override initialGates() in Application
  overridden method is final
1 error
```

Or use the static factory, `SafeOnboardingApplication.open("APP-7202", "GB-SCT")`, which
constructs, initialises, and only then publishes:

```console
  [factory] fully constructed: AO-120 ADDRESS_PENDING applicationId=APP-7202 jurisdiction=GB-SCT requiredDocuments=[PROOF_OF_ADDRESS]
```

**Why people believe it:** the template-method pattern is taught as good design, and a
constructor looks like the natural place for the hook — "initialise, then ask the subclass
what it needs". It reads correctly because the source shows the subclass's field declarations
*above* the method that uses them.

### Believing a `final` field is set before the superclass constructor returns

**Wrong**

```java
private final String jurisdiction;
OnboardingApplication(String jurisdiction) {
    super("AO-120 ADDRESS_PENDING");   // superclass reads jurisdiction here
    this.jurisdiction = jurisdiction;
}
```

```console
  [Application ctor] gates during construction = [jurisdiction=null, maxStakeMinorUnits=0, requiredDocuments=null]
```

**Right**

Pass the value up, so the base never reads a subclass field:

```java
static abstract class Application {
    private final String jurisdiction;
    Application(String statusCode, String jurisdiction) {
        this.jurisdiction = jurisdiction;
        System.out.println(statusCode + " jurisdiction=" + jurisdiction);
    }
}
```

`final` guarantees exactly-once assignment on every constructor path and safe publication
*after* construction via the final-field freeze. Neither guarantee applies mid-construction.

**Why people believe it:** `final` is described as "immutable" and "set at construction", and
that compresses to "set before anything can observe it". The `super` call is invisible when
implicit, so the ordering that breaks the belief is not on the page.

### Believing the escape window is too short to matter

**Wrong**

```java
Application(String applicationId) {
    this.applicationId = applicationId;
    ApplicationHistory.register(applicationId, this);   // "the ctor returns in nanoseconds"
}
```

```console
  [ApplicationHistory] registered APP-7201 -> AO-120 ADDRESS_PENDING jurisdiction=null requiredDocuments=null
  [registry read after ctor returned] AO-120 ADDRESS_PENDING jurisdiction=GB-ENG requiredDocuments=[PROOF_OF_ADDRESS]
```

The registry saw the incomplete object and `register` already acted on it. The window was not
the problem; the escape was.

**Right**

Construct, initialise, then publish — the reference leaves the factory only after the
constructor has returned:

```console
  [factory] fully constructed: AO-120 ADDRESS_PENDING applicationId=APP-7202 jurisdiction=GB-SCT requiredDocuments=[PROOF_OF_ADDRESS]
```

**Why people believe it:** the window is reasoned about as a *timing* race, and constructors
really are fast, so "nothing could interleave" feels safe. But the escaping reference is
durable — it stays in the map after the constructor returns, and anything that read it during
construction kept whatever it derived from the default values. And the reference was published
before the final-field freeze, so another thread may keep observing a mix of assigned and zero
fields indefinitely. The race is on the publication, not on the fields.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Why does the override see defaults? | the superclass constructor runs before this class's field initializers |
| Virtual dispatch inside a superclass constructor? | live, from allocation onwards — the class word is written at allocation |
| Subclass `final` field read there? | `null` / `0` / `false` |
| What `final` on an instance field actually guarantees | exactly-once assignment on every path that completes a constructor; safe publication *after* construction via the final-field freeze |
| Primitive reads garbage? | no — the JVM zeroes the object, so the default is a legal value; that is the silent variant |
| Order inside one constructor | `super` call → this level's field initializers and instance blocks (textual) → ctor body statements |
| The escape variant | `this` handed to a registry, a listener list or a thread; durable, and published before the final-field freeze |
| `-Xlint:all` on the trap | silent, exit 0, both harnesses |
| Analysers that catch it | SpotBugs `MC_OVERRIDABLE_METHOD_CALL_IN_CONSTRUCTOR` / `_IN_CLONE` / `_IN_READ_OBJECT`; PMD `ConstructorCallsOverridableMethod`; sevntu `OverridableMethodInConstructorCheck` |
| Fixes, ranked | class `final` → method `final`/`private` → static factory that constructs then initialises |
| Compiler-enforced fix | `final` on the hook turns the override into `overridden method is final`, exit 1 |
| Defensive null check enough? | no — an `int`, `long` or `boolean` default is a legal value, so the guard never fires |

---

## Self-test

**Q1.** `OnboardingApplication` declares `private final String jurisdiction` and assigns it
from a constructor argument. Why does the superclass constructor see `null`?

<details><summary>Answer</summary>

The assignment happens after the `super` call. `javac` compiles the subclass constructor as
`invokespecial` on the superclass constructor, then the subclass's field initializers and
instance blocks, then the constructor body statements — which is where
`this.jurisdiction = jurisdiction` lives. While the superclass constructor runs, the
assignment has not executed, so the field holds its allocation-time default. `final` does not
change this: its two guarantees are exactly-once assignment on every path that completes a
constructor, and safe publication once the constructor finishes (the final-field freeze). Both
are anchored to the *end* of construction.

</details>

**Q2.** Why is a `0` from `maxStakeMinorUnits` more dangerous than a `null` from
`jurisdiction`?

<details><summary>Answer</summary>

`0` is a plausible value and `null` is not. The JVM zeroes the whole object on allocation, so
a primitive read mid-construction returns a legal number, not garbage. A `null` jurisdiction
dereferenced downstream produces a `NullPointerException` with a trace pointing at the
constructor. A `maxStakeMinorUnits` of `0` produces a limit set that either rejects every
stake or, with the comparison written the other way, rejects none — and both survive a test
that only asserts the object was created. The silent variant is the one that reaches
production.

</details>

**Q3.** The `this` escape and the null field read come from the same ordering fact. Why is the
escape worse?

<details><summary>Answer</summary>

Duration and visibility. The null read is transient — one wrong observation inside one
constructor, and the object is correct a microsecond later. The escape is durable: the
reference is in a registry, a listener list or a running thread that outlives the constructor,
and anything that read it during the window kept whatever it derived from the default values.
The escape also adds a memory-model failure the null read does not have — publishing before
the final-field freeze lets another thread observe some fields assigned and some still zero,
with the race on the publication rather than on the fields.

</details>

**Q4.** Does `javac -Xlint:all` warn about calling an overridable method from a constructor?

<details><summary>Answer</summary>

No. Both harnesses in this file compile with `-Xlint:all` at exit `0` with no diagnostic. That
is deliberate: the construct is legal and occasionally intentional — a base whose hook reads
only its own already-assigned fields is fine — and the compiler cannot distinguish the safe
use from the unsafe one. Catching it is a static-analysis job: SpotBugs'
`MC_OVERRIDABLE_METHOD_CALL_IN_CONSTRUCTOR` (with sibling patterns for `clone` and
`readObject`), PMD's `ConstructorCallsOverridableMethod`, or sevntu-checkstyle's
`OverridableMethodInConstructorCheck`.

</details>

**Q5.** Rank the three fixes and say what each one costs.

<details><summary>Answer</summary>

First, make the class `final`: no subclass exists, so no override exists, so the gap cannot
open. It costs extension entirely. Second, make the called method `final` or `private`: the
call becomes statically bound and the base reads only its own already-assigned fields, and the
compiler enforces it — an attempted override fails with `overridden method is final`, exit 1.
It costs the subclass's ability to customise that hook. Third, the static factory: a `private`
constructor that only assigns fields, and a factory method that constructs, initialises, and
only then returns the reference. It costs one level of indirection and is the one that
generalises, because it fixes the `this`-escape variant as well as the null read.

</details>

**Q6.** SpotBugs ships three patterns from one detector — `_IN_CONSTRUCTOR`, `_IN_CLONE` and
`_IN_READ_OBJECT`. Why do `clone` and `readObject` need their own?

<details><summary>Answer</summary>

Because they are the two other ways an object comes into existence in a partly-initialized
state. `Object.clone` produces a field-by-field copy and then lets the overriding `clone` fix
it up, so a virtual call made before that fix-up sees whatever the shallow copy contained.
`readObject` is worse: deserialization does not run constructors at all, and it does not run
field initializers either, so a virtual call from `readObject` sees defaults for exactly the
same reason a superclass constructor does — with no `super` call anywhere in the picture to
hint at the ordering. All three come from the detector
`edu.umd.cs.findbugs.detect.FindOverridableMethodCall`, which is the tell that SpotBugs treats
them as one defect with three entry points.

</details>

---

## Open questions

- **ErrorProne check names.** `ConstructorInvokesOverridable` and `ConstructorLeaksThis` are
  widely quoted for this defect but do not appear in ErrorProne's published catalogue at
  `errorprone.info/bugpatterns` (both per-pattern URLs return HTTP 404, and the catalogue's
  `Constructor`-containing entries do not include them). Settled by running `-Xep:help` against
  a specific ErrorProne release, or by grepping `google/error-prone`'s `bugpatterns` tree for a
  `@BugPattern` annotation with those names.

---

**Leaves covered:** 4.8.2 (1 leaf)
**Leaves deferred:** none — 4.8.3 moved to `05g-class-initialization-order.md` (order 27a) on a re-split
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 625
