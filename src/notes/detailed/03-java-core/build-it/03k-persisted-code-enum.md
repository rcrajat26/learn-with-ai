# 03 Java Core — Enum-shaped builds — a persisted code, a static lookup, and a tolerant fromCode — BUILD IT (§4.5.2)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The pre-Java-5 typesafe enum pattern](03-enums-exceptions-resources.md) · Next: [The strategy enum](03f-strategy-enum.md)

---

## What gets built here

One `enum` with three parts that are usually missing, and each missing part is a production bug:

| Part | What it is | What goes wrong without it |
|---|---|---|
| An immutable `code` field | `DOCUMENTS_UPLOADED` carries `AA-610`, distinct from both `name()` and `ordinal()` | Persisting `ordinal()` reinterprets history when a constant is inserted; persisting `name()` breaks when someone renames |
| A static `Map<String, X>`, built in a `static` block | Populated after the constants exist, wrapped in `Map.copyOf`, duplicates rejected at class-initialisation time | A constructor-populated map does not compile; a `HashMap` handed out publicly is mutable; a duplicate code silently resolves to whichever constant came last |
| `fromCode` returning `Optional<X>` | Tolerance at a persistence boundary | An unknown code throws 5xx or returns `null` during every rolling deployment, which is a normal state, not a bug |

Preceded by [the pre-Java-5 typesafe enum pattern](03-enums-exceptions-resources.md), which proves
what `enum` buys; followed by [the strategy enum](03f-strategy-enum.md), which puts behaviour on
the constants.

Everything here is `[BUILD]`: complete, compiling Java 21, compiled and run on
**Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, with real output
pasted.

---

## 4.5.2 A persisted code, a static lookup map, and a tolerant `fromCode`

### The shape

An `enum` whose identity in the codebase is its constant name and whose identity *in the database
and on the wire* is a separate immutable `String`. Two names for the same thing, deliberately
decoupled, because they change on different schedules. Plus a static `Map<String, X>` built once
at class initialisation and a lookup that returns `Optional` instead of throwing.

### Why not `ordinal()`

`ordinal()` is a small dense `int`, which makes it the most tempting column type in the world, and
it is defined as the constant's *position in the declaration list*. Insert a constant and every
later position shifts. Nothing throws. Here is release 1 writing three application rows, and
release 2 — which added `DOCUMENTS_REFERRED` in the middle, because referrals became a first-class
stage — reading the same three rows.

```java
public enum DocumentStage {           // release 1
    DOCUMENTS_REQUESTED,
    DOCUMENTS_UPLOADED,
    DOCUMENTS_VERIFIED,
    ACTIVATED
}
```

```java
public enum DocumentStage {           // release 2
    DOCUMENTS_REQUESTED,
    DOCUMENTS_UPLOADED,
    DOCUMENTS_REFERRED,   // inserted in release 2: referrals became a first-class stage
    DOCUMENTS_VERIFIED,
    ACTIVATED
}
```

```java
import java.util.List;

/** Two application rows, persisted as ordinal() by release 1, read back by the running build. */
public final class OrdinalPersistence {

    record ApplicationRow(String applicationId, int stageOrdinal) { }

    // Written by release 1, when DOCUMENTS_VERIFIED was ordinal 2 and ACTIVATED was 3.
    private static final List<ApplicationRow> ROWS = List.of(
            new ApplicationRow("APP-7f21", 1),
            new ApplicationRow("APP-7f22", 2),
            new ApplicationRow("APP-7f23", 3));

    public static void main(String[] args) {
        System.out.println("constants in this build: " + List.of(DocumentStage.values()));
        for (ApplicationRow row : ROWS) {
            DocumentStage read = DocumentStage.values()[row.stageOrdinal()];
            System.out.printf("%s  stored ordinal %d  reads back as %s%n",
                    row.applicationId(), row.stageOrdinal(), read);
        }
    }
}
```

```console
=== release 1 (schema as written) ===
constants in this build: [DOCUMENTS_REQUESTED, DOCUMENTS_UPLOADED, DOCUMENTS_VERIFIED, ACTIVATED]
APP-7f21  stored ordinal 1  reads back as DOCUMENTS_UPLOADED
APP-7f22  stored ordinal 2  reads back as DOCUMENTS_VERIFIED
APP-7f23  stored ordinal 3  reads back as ACTIVATED
=== release 2 (one constant inserted) ===
constants in this build: [DOCUMENTS_REQUESTED, DOCUMENTS_UPLOADED, DOCUMENTS_REFERRED, DOCUMENTS_VERIFIED, ACTIVATED]
APP-7f21  stored ordinal 1  reads back as DOCUMENTS_UPLOADED
APP-7f22  stored ordinal 2  reads back as DOCUMENTS_REFERRED
APP-7f23  stored ordinal 3  reads back as DOCUMENTS_VERIFIED
```

Read the last two lines as the business would. A client whose documents were **verified** now
reads as **referred to a human**. A client who was **activated** now reads as merely
**verified** — so `AccountActivation` will not treat the account as active, and every money action
stays restricted. No exception, no log line, no failed deployment. At 7.2k applications reaching
`AO-400` per day, that is a silent incident spread across the whole hot window.

`Enum.ordinal()`'s own javadoc says it is "designed for use by sophisticated enum-based data
structures, such as `EnumSet` and `EnumMap`". That is the entire sanctioned use.

### Why not `name()` either

`name()` is stable against insertion — it is the identifier, not the position. It is not stable
against *renaming*, and renaming an identifier is the single most ordinary refactor there is; the
IDE will do it across the codebase in one keystroke and will not touch the 2.4M rows.

```java
public final class NameRename {
    /** Release 2 renamed DOCUMENTS_UPLOADED to DOCUMENTS_RECEIVED; the rows did not change. */
    enum DocumentStageRenamed { DOCUMENTS_REQUESTED, DOCUMENTS_RECEIVED, DOCUMENTS_VERIFIED }

    public static void main(String[] args) {
        String persistedByName = "DOCUMENTS_UPLOADED";   // written by release 1
        try {
            System.out.println(DocumentStageRenamed.valueOf(persistedByName));
        } catch (IllegalArgumentException e) {
            System.out.println("valueOf(\"" + persistedByName + "\") -> "
                    + e.getClass().getName() + ": " + e.getMessage());
        }
        System.out.println("fromCode(\"AA-610\") still resolves: "
                + ActivationStatus.fromCode("AA-610").map(Enum::name).orElse("<none>"));
    }
}
```

```console
valueOf("DOCUMENTS_UPLOADED") -> java.lang.IllegalArgumentException: No enum constant NameRename.DocumentStageRenamed.DOCUMENTS_UPLOADED
fromCode("AA-610") still resolves: DOCUMENTS_UPLOADED
```

That failure is at least *loud* — a thrown exception beats a wrong answer. But it is still an
outage caused by a rename, and the fix under pressure is always the same ugly one: a hard-coded
alias table. A separate `code` field is that alias table, designed in from the start, and it is
the whole reason this leaf exists. `AA-610` never changes, whatever the constant is called.

### The build

```java
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/** Activation-phase status with a persisted code independent of name() and ordinal(). */
public enum ActivationStatus {

    SCREENING_IN_PROGRESS   ("AA-500", Disposition.IN_PROGRESS),
    SCREENING_CLEAR         ("AA-501", Disposition.SUCCESS),
    DOCUMENTS_REQUESTED     ("AA-600", Disposition.IN_PROGRESS),
    DOCUMENTS_UPLOADED      ("AA-610", Disposition.IN_PROGRESS),
    DOCUMENTS_VERIFIED      ("AA-611", Disposition.SUCCESS),
    DOCUMENTS_REFERRED      ("AA-650", Disposition.REFERRED),
    REVIEW_QUEUED           ("AA-700", Disposition.IN_PROGRESS),
    REVIEW_APPROVED         ("AA-711", Disposition.SUCCESS),
    ACTIVATING              ("AA-800", Disposition.IN_PROGRESS),
    ACTIVATED               ("AA-801", Disposition.SUCCESS);

    public enum Disposition { IN_PROGRESS, SUCCESS, REFERRED, FAILED }

    private final String code;
    private final Disposition disposition;

    ActivationStatus(String code, Disposition disposition) {
        this.code = code;
        this.disposition = disposition;
    }

    /** Built in a static initialiser, which runs AFTER every constant exists. */
    private static final Map<String, ActivationStatus> BY_CODE;

    static {
        Map<String, ActivationStatus> building = new LinkedHashMap<>();
        for (ActivationStatus status : values()) {
            ActivationStatus clash = building.put(status.code, status);
            if (clash != null) {
                throw new IllegalStateException(
                        "Duplicate persisted code " + status.code
                        + " on " + clash.name() + " and " + status.name());
            }
        }
        BY_CODE = Map.copyOf(building);
    }

    public String code() { return code; }

    public Disposition disposition() { return disposition; }

    /** The phase digit of XX-Nnn. Structural, and safe to read off the code. */
    public int phase() { return code.charAt(3) - '0'; }

    public boolean referredToHuman() { return disposition == Disposition.REFERRED; }

    /** Tolerant: an unknown code means the database is ahead of this deployment. */
    public static Optional<ActivationStatus> fromCode(String code) {
        return Optional.ofNullable(BY_CODE.get(code));
    }

    public static Map<String, ActivationStatus> byCode() { return BY_CODE; }
}
```

The `Disposition` is an explicit constructor argument, not a digit parsed out of the code, and
that is a deliberate refusal. The `XX-Nnn` structure says the middle digit is the disposition —
`0` in progress, `1` success, `5` referred, `9` failed or blocked — and the phase digit does hold
across the whole code space, which is why `phase()` can read it off `charAt(3)`. But the middle
digit does not: `AA-800 ACTIVATING` and `AA-801 ACTIVATED` both carry middle digit `0`, and
`AO-110 CONTACT_VERIFICATION_PENDING` carries `1`. Deriving semantics from a digit that is
*mostly* systematic is how you get a system that is right in tests and wrong in production. Store
what you mean.

```java
import java.util.Optional;

public final class CodeLookupDemo {
    public static void main(String[] args) {
        System.out.println("map size  = " + ActivationStatus.byCode().size());
        System.out.println("map class = " + ActivationStatus.byCode().getClass().getName());

        for (String persisted : new String[] { "AA-610", "AA-611", "AA-650", "AA-801", "AA-999" }) {
            Optional<ActivationStatus> found = ActivationStatus.fromCode(persisted);
            System.out.printf("%s -> %-26s phase=%s disposition=%s referred=%s%n",
                    persisted,
                    found.map(Enum::name).orElse("<unknown: db ahead of code>"),
                    found.map(s -> String.valueOf(s.phase())).orElse("-"),
                    found.map(s -> s.disposition().name()).orElse("-"),
                    found.map(s -> String.valueOf(s.referredToHuman())).orElse("-"));
        }

        try {
            ActivationStatus.byCode().put("AA-999", ActivationStatus.ACTIVATED);
        } catch (UnsupportedOperationException e) {
            System.out.println("lookup map immutable: " + e.getClass().getName());
        }

        String row = "AA-650";
        System.out.println(ActivationStatus.fromCode(row)
                .filter(ActivationStatus::referredToHuman)
                .map(s -> "route to REVIEW_QUEUED for " + s.name())
                .orElse("no routing rule for row " + row));

        String ahead = "AA-699";
        System.out.println(ActivationStatus.fromCode(ahead)
                .map(ActivationStatus::name)
                .orElse("park application, alert operator: unrecognised status " + ahead));
    }
}
```

```console
map size  = 10
map class = java.util.ImmutableCollections$MapN
AA-610 -> DOCUMENTS_UPLOADED         phase=6 disposition=IN_PROGRESS referred=false
AA-611 -> DOCUMENTS_VERIFIED         phase=6 disposition=SUCCESS referred=false
AA-650 -> DOCUMENTS_REFERRED         phase=6 disposition=REFERRED referred=true
AA-801 -> ACTIVATED                  phase=8 disposition=SUCCESS referred=false
AA-999 -> <unknown: db ahead of code> phase=- disposition=- referred=-
lookup map immutable: java.lang.UnsupportedOperationException
route to REVIEW_QUEUED for DOCUMENTS_REFERRED
park application, alert operator: unrecognised status AA-699
```

### Building the lookup map correctly

Three things have to be true of that `static` block, and each of them is a bug if it is not.

**One: it must run after the constants exist, which means it cannot live in the constructor.** The
tempting version registers each constant as it is built. `javac` refuses:

```java
public enum EagerLookupStatus {

    DOCUMENTS_UPLOADED("AA-610"),
    DOCUMENTS_VERIFIED("AA-611");

    private static final Map<String, EagerLookupStatus> BY_CODE = new HashMap<>();

    private final String code;

    EagerLookupStatus(String code) {
        this.code = code;
        BY_CODE.put(code, this);   // register myself as I am constructed
    }
}
```

```console
bad/EagerLookupStatus.java:15: error: illegal reference to static field from initializer
        BY_CODE.put(code, this);   // register myself as I am constructed
        ^
1 error
```

This is JLS §8.9.2: a constructor, instance initialiser or instance variable initialiser of an
enum class may not access a static field of that class unless the field is a constant variable.
The rule exists because the constants are constructed *inside* `<clinit>`, textually before any
static field declared after them has been assigned — so `BY_CODE` would be `null` and every
constant's constructor would throw `NullPointerException` inside an `ExceptionInInitializerError`.
The compiler turning a guaranteed runtime failure into a compile error is the language doing you a
favour, and it is the reason the ordering hazard from §4.5.1 cannot bite here.

**Two: the map must be immutable.** `Map.copyOf` gives an `ImmutableCollections$MapN`, as the
output shows, and mutation attempts get `UnsupportedOperationException`. Handing out a
`HashMap` from a `public static` accessor means any caller can add a row and every subsequent
`fromCode` in the JVM sees it.

**Three: duplicate codes must fail at class initialisation, not silently overwrite.**
`Map.put` returns the previous value; if it is non-null, two constants claim one code, and a
plain `put` would leave `fromCode` resolving that code to whichever constant was declared last.

```java
public enum DuplicateCodeStatus {

    DOCUMENTS_UPLOADED("AA-610"),
    DOCUMENTS_VERIFIED("AA-611"),
    DOCUMENTS_REFERRED("AA-650"),
    REVIEW_QUEUED     ("AA-650");   // copy-paste slip: AA-650 already taken

    private final String code;

    DuplicateCodeStatus(String code) { this.code = code; }

    private static final Map<String, DuplicateCodeStatus> BY_CODE;

    static {
        Map<String, DuplicateCodeStatus> building = new LinkedHashMap<>();
        for (DuplicateCodeStatus status : values()) {
            DuplicateCodeStatus clash = building.put(status.code, status);
            if (clash != null) {
                throw new IllegalStateException(
                        "Duplicate persisted code " + status.code
                        + " on " + clash.name() + " and " + status.name());
            }
        }
        BY_CODE = Map.copyOf(building);
    }

    public static int size() { return BY_CODE.size(); }
}
```

Touching it twice, catching both times:

```console
attempt 1 -> java.lang.ExceptionInInitializerError: null
           cause: java.lang.IllegalStateException: Duplicate persisted code AA-650 on DOCUMENTS_REFERRED and REVIEW_QUEUED
attempt 2 -> java.lang.NoClassDefFoundError: Could not initialize class DuplicateCodeStatus
           cause: java.lang.ExceptionInInitializerError: Exception java.lang.IllegalStateException: Duplicate persisted code AA-650 on DOCUMENTS_REFERRED and REVIEW_QUEUED [in thread "main"]
```

Loud, correct, and diagnostically nasty in a specific way. The first touch reports the real
problem. The class is now permanently in the **erroneous** state for the life of the JVM, and
every later touch throws `NoClassDefFoundError: Could not initialize class DuplicateCodeStatus` —
whose `getMessage()` says nothing about `AA-650`. In JDK 21 the original
`ExceptionInInitializerError` *is* chained as the cause, so a handler that logs the full cause
chain still sees it; a handler that logs `e.getMessage()` only, which is most of them, loses it
entirely. If your service initialises `ActivationStatus` lazily on the first request rather than
at startup, the request that gets the honest error is one request out of thousands and it is not
the one your operator screenshots. `../classes-and-initialization/01d-class-initialization-triggers.md`
owns that failure mode and the erroneous-state rules.

**Insight:** validate invariants over an enum's constants in the `static` block, not in a unit
test. The `static` block runs in every environment the class is loaded in, including the one where
someone cherry-picked a constant onto a release branch and skipped CI.

### Why `fromCode` returns `Optional`

`fromCode` sits on a persistence boundary, and the boundary has a state that is neither success
nor bug: **the database is ahead of the code**. During a rolling deployment, release 2 writes
`AA-699 DOCUMENTS_EXHAUSTED` while three release-1 pods are still serving. Those pods will read
that row. That is not corruption and it is not a programming error — it is the expected shape of
every deployment that is not a full outage.

The three candidate signatures, and what each does to that pod:

| Signature | Unknown code becomes | What the caller is forced to do | Verdict |
|---|---|---|---|
| `X fromCode(String)` throwing `IllegalArgumentException` | an exception on a read path | catch, or crash the read | Wrong: turns a normal deployment window into 5xx responses |
| `X fromCode(String)` returning `null` | `null` flowing into domain logic | remember to null-check, forever | Wrong: the check is invisible and will be skipped |
| `Optional<X> fromCode(String)` | an empty `Optional` | decide explicitly — park, alert, or default | Right: the type states that absence is possible |

The `orElse` branch in the output shows the decision being made:
`park application, alert operator: unrecognised status AA-699`. The application is not advanced,
not failed, and a human is told. Contrast the ordinal version, which advanced it to the wrong
state without telling anyone.

`Optional` is not free — it is an allocation per lookup unless escape analysis removes it, and at
`ActivationStatus.fromCode` call rates that is irrelevant next to the database round trip that
produced the string. Guide 04 owns `Optional` idiom; the trade-off here is one allocation against
a class of silent-corruption bug.

> **Definition.** A persisted-code enum keeps three identities apart on purpose: `ordinal()` for
> `EnumSet` and `EnumMap` only, `name()` for the codebase, and an immutable `code` field for the
> database and the wire — resolved through an immutable static map built in a `static` block that
> validates uniqueness at class initialisation, and read through a lookup that returns `Optional`
> because an unknown code means the store is ahead of the code.

### Diff vs the real one — this lookup vs what the JDK gives you

| Axis | This build | `Enum.valueOf` / `enumConstantDirectory` |
|---|---|---|
| Edge cases | Unknown code returns empty; a null argument returns empty, because `HashMap.get(null)` is legal and `Map.copyOf`'s `MapN.get(null)` returns null rather than throwing | `Enum.valueOf(null)` throws `NullPointerException("Name is null")`; unknown name throws `IllegalArgumentException` |
| Intrinsics | None. One `ImmutableCollections$MapN` probe | None either; `Class.enumConstantDirectory` is a lazily built, `@Stable`-free `HashMap` cached on the `Class` |
| Serialization | You persist `code()` and resolve with `fromCode`; enum-to-string is your decision | Java serialization writes `name()` as a `TC_ENUM` record; JPA's `EnumType.ORDINAL` and `EnumType.STRING` persist exactly the two things this leaf tells you not to |
| Null policy | `fromCode(null)` returns empty — arguably too tolerant; add `Objects.requireNonNull` if a null code means a bug upstream | Explicit `NullPointerException` |
| Thread safety | Safe: `BY_CODE` is a `final` static assigned in `<clinit>` and immutable thereafter | Safe: the directory is built under the `Class`'s own lock |
| Allocation tricks | Fixed cost at class init: one `LinkedHashMap`, one `MapN`, ten `String` constants from the constant pool. One `Optional` per lookup | One `HashMap` per enum class, built on first `valueOf` and cached forever |
| Why the JDK bothers | It does not — there is no JDK support for a persisted code, which is why this is a build-it leaf | The JDK ships name-based resolution only, because it has no opinion about your database |

**Interview:** *"How do you store an enum in a database?"* — Not `ordinal()`, because inserting a
constant renumbers history silently; not `name()`, because renaming is a one-keystroke refactor
that breaks the store; a dedicated immutable code column, resolved through a validated static map,
read through an API that can return "unknown" without throwing.

---

The §4.5-wide **diff vs the compiler's generated enum** — `$VALUES`, `$SwitchMap`, the `Enum`
superclass, and the constructor injection of name and ordinal — is leaf 4.5.7, in
[The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md).

---

## Pitfalls

### Persisting `ordinal()` because it is a compact `int`

**Wrong**

```java
// schema: application.stage SMALLINT
statement.setInt(1, stage.ordinal());
DocumentStage stage = DocumentStage.values()[resultSet.getInt("stage")];
```

Run against release 1, then against release 2 which inserted `DOCUMENTS_REFERRED` in the middle:

```console
APP-7f22  stored ordinal 2  reads back as DOCUMENTS_VERIFIED     <- release 1
APP-7f22  stored ordinal 2  reads back as DOCUMENTS_REFERRED     <- release 2
APP-7f23  stored ordinal 3  reads back as DOCUMENTS_VERIFIED     <- was ACTIVATED
```

**Right**

```java
statement.setString(1, status.code());                       // "AA-611"
ActivationStatus status = ActivationStatus.fromCode(resultSet.getString("status_code"))
        .orElseThrow(() -> new IllegalStateException("unknown status code, park for operator"));
```

`AA-611` means `DOCUMENTS_VERIFIED` in every release, because the code is data and the declaration
order is not.

**Why people believe it:** `ordinal()` is stable *within a build*, so every test passes and every
local run is correct; the corruption only appears at the moment a constant is inserted, in a
different release, in rows nobody re-reads until a client complains. `SMALLINT` also genuinely
indexes better than `CHAR(6)`, so the wrong choice has a real argument behind it.

### Persisting `name()` and then renaming a constant

**Wrong**

```java
enum DocumentStageRenamed { DOCUMENTS_REQUESTED, DOCUMENTS_RECEIVED, DOCUMENTS_VERIFIED }
DocumentStageRenamed.valueOf("DOCUMENTS_UPLOADED");   // the value release 1 wrote
```

```console
valueOf("DOCUMENTS_UPLOADED") -> java.lang.IllegalArgumentException: No enum constant NameRename.DocumentStageRenamed.DOCUMENTS_UPLOADED
```

**Right**

Keep the code independent of the identifier, and rename freely:

```java
DOCUMENTS_UPLOADED("AA-610", Disposition.IN_PROGRESS),   // rename the constant whenever you like
```

```console
fromCode("AA-610") still resolves: DOCUMENTS_UPLOADED
```

**Why people believe it:** `name()` really is immune to the insertion problem, so it looks like
the fixed version of the `ordinal()` mistake, and `EnumType.STRING` is the JPA setting everyone is
told to prefer. The remaining coupling — that a refactor tool can now break a database — is
invisible until the refactor happens.

### Initialising a static lookup map from inside the constant constructor

**Wrong**

```java
private static final Map<String, EagerLookupStatus> BY_CODE = new HashMap<>();

EagerLookupStatus(String code) {
    this.code = code;
    BY_CODE.put(code, this);   // register myself as I am constructed
}
```

```console
bad/EagerLookupStatus.java:15: error: illegal reference to static field from initializer
        BY_CODE.put(code, this);   // register myself as I am constructed
        ^
1 error
```

**Right**

```java
static {
    Map<String, ActivationStatus> building = new LinkedHashMap<>();
    for (ActivationStatus status : values()) {
        ActivationStatus clash = building.put(status.code, status);
        if (clash != null) {
            throw new IllegalStateException("Duplicate persisted code " + status.code
                    + " on " + clash.name() + " and " + status.name());
        }
    }
    BY_CODE = Map.copyOf(building);
}
```

**Why people believe it:** self-registration is a real and useful pattern for ordinary classes, and
it feels DRY — each constant declares its own code once and puts itself in the map. The enum case
is special because the constants are constructed inside `<clinit>` before later static fields are
assigned, which JLS §8.9.2 turns into a compile error rather than a `NullPointerException`. The
same self-registration written into a plain class compiles and works, which is why the instinct is
hard to unlearn.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| Persist `ordinal()` | Never. Inserting a constant renumbers every later one and reinterprets historical rows, silently |
| Persist `name()` | Only if you will never rename. A rename makes `valueOf` throw `IllegalArgumentException` at read time |
| Persist | A separate immutable `code` field — `AA-610` for `DOCUMENTS_UPLOADED`, `AA-611` for `DOCUMENTS_VERIFIED`, `AA-650` for `DOCUMENTS_REFERRED`, `AA-801` for `ACTIVATED` |
| `ordinal()`'s sanctioned use | `EnumSet` and `EnumMap` internals only, per its own javadoc |
| JPA equivalents | `EnumType.ORDINAL` and `EnumType.STRING` persist exactly the two things to avoid |
| Lookup map, where | A `static` block, never a constructor |
| Static field from an enum constructor | Compile error: `illegal reference to static field from initializer`, JLS §8.9.2 |
| Lookup map, immutability | `Map.copyOf` → `ImmutableCollections$MapN`; mutation throws `UnsupportedOperationException` |
| Duplicate codes | Detect with `Map.put`'s return value and throw from the `static` block |
| Failed `<clinit>`, first touch | `ExceptionInInitializerError`, cause = your `IllegalStateException` |
| Failed `<clinit>`, later touches | `NoClassDefFoundError: Could not initialize class X`; in JDK 21 the original is chained as cause, but `getMessage()` alone loses it |
| `fromCode` return type | `Optional<X>`. Not throwing, not `null` |
| Why tolerance | An unknown code means the store is ahead of the code — the normal state of a rolling deploy |
| Deriving meaning from the code digits | Phase digit (`charAt(3)`) is structural and safe; the disposition digit is not — `AA-800` and `AA-801` both carry `0`. Store the disposition as a field |
| §4.5 diff table | Leaf 4.5.7, in `03b-enum-values-cache-and-diff.md` |

---

## Self-test

**Q1.** `application.stage` is a `SMALLINT` holding `ordinal()`. A release inserts one constant in
the middle. What does the deployment do, and what does it log?

<details><summary>Answer</summary>

Nothing. It logs nothing. `values()[2]` now returns a different constant, so historical rows
reinterpret: a row written as `DOCUMENTS_VERIFIED` reads back as `DOCUMENTS_REFERRED`, and one
written as `ACTIVATED` reads back as `DOCUMENTS_VERIFIED`. Every read is in range, so no
`ArrayIndexOutOfBoundsException` and no exception at all. Activated clients stop being treated as
active and stay restricted; verified applications get routed to human review. The only signal is
a business one, arriving through complaints, and by then the wrong states have been written back.

</details>

**Q2.** Why can the lookup map not be populated from each constant's constructor, and what exact
error do you get?

<details><summary>Answer</summary>

`bad/EagerLookupStatus.java:15: error: illegal reference to static field from initializer` — a
compile error, per JLS §8.9.2, which forbids a constructor or instance initialiser of an enum from
accessing a static field of that enum unless the field is a constant variable. The reason is
ordering: the constants are constructed inside `<clinit>`, textually before any static field
declared after them has been assigned, so the field would be `null` and each constructor would
throw `NullPointerException` wrapped in `ExceptionInInitializerError`. Populate in a `static`
block iterating `values()`, which runs after all constants exist.

</details>

**Q3.** Your `static` block throws on a duplicate code. What does the *second* attempt to use the
class see, and why is that a diagnostic problem?

<details><summary>Answer</summary>

`NoClassDefFoundError: Could not initialize class DuplicateCodeStatus`. Class initialisation is
one-shot: a `<clinit>` that completes abruptly puts the class permanently in the erroneous state
for that class loader in that JVM, and every later touch gets `NoClassDefFoundError` rather than
the original `ExceptionInInitializerError`. In JDK 21 the original is chained as the cause, so a
handler that logs the full chain still sees `Duplicate persisted code AA-650` — but a handler that
logs only `getMessage()` sees nothing about `AA-650`. If the class is first loaded lazily on a
request path, exactly one request gets the honest error and the rest get the useless one.

</details>

**Q4.** `fromCode` could throw, return `null`, or return `Optional`. A rolling deployment is in
progress. Argue for one.

<details><summary>Answer</summary>

`Optional`. During a rolling deployment release 2 writes `AA-699 DOCUMENTS_EXHAUSTED` while
release-1 pods are still serving reads, so a release-1 pod *will* see a code it has never heard of.
That is neither success nor a programming error — it is the expected shape of any deployment that
is not a full outage.

Throwing `IllegalArgumentException` turns that window into 5xx responses on a read path, and the
only defence available to the caller is a `try`/`catch` around a getter. Returning `null` puts an
untyped absence into domain logic where the check is invisible and will eventually be skipped, and
the resulting `NullPointerException` surfaces far from the lookup. `Optional<ActivationStatus>`
states in the signature that absence is possible and forces the caller to decide — the demo's
`orElse` branch parks the application and alerts an operator rather than advancing it. The cost is
one allocation per lookup unless escape analysis removes it, which is nothing beside the database
round trip that produced the string.

</details>

**Q5.** The status codes are documented as `XX-Nnn` with the middle digit as the disposition — `0`
in progress, `1` success, `5` referred, `9` failed. Why does the build pass `Disposition` to the
constructor instead of reading that digit?

<details><summary>Answer</summary>

Because the convention does not actually hold across the whole code space, and a rule that is
*mostly* systematic is worse than no rule. `AA-800 ACTIVATING` and `AA-801 ACTIVATED` both carry
middle digit `0`, so a digit-derived disposition would report `ACTIVATED` as in progress —
`AccountActivation` would never treat the account as active and every money action would stay
restricted. `AO-110 CONTACT_VERIFICATION_PENDING` carries `1`, which the convention reads as
success while the constant name says pending.

The phase digit at `charAt(3)` *is* structural and consistent — `AA-6xx` documents, `AA-7xx`
review, `AA-8xx` activation — so `phase()` reads it off the code. Everything semantic is stored,
not parsed. The general form of the rule: never derive behaviour from the syntax of an identifier
you do not control end to end.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.5.2 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 663
