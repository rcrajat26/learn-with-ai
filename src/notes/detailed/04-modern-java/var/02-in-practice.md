# 04 Modern Java — `var` — INTERMEDIATE (§2.7)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [`var` — basics](01-basics.md) · Next: [`var` — internals inference](03-internals-inference.md)

Local-variable type inference (`var`, JEP 286, Java 10) is not a style toggle you flip on or
off for a whole codebase. It is a per-declaration judgment call, and the JDK's own language
architects wrote down the test for making it: the **OpenJDK LVTI style guide**
(`openjdk.org/projects/amber/guides/lvti-style-guide`), whose principles and guidelines are the
spine of this file. Re-fetched and verified reachable (HTTP 200) before this file was written,
so the identifiers below are quoted, not paraphrased:

> **P1** Reading code is more important than writing code.
> **P2** Code should be clear from local reasoning.
> **P3** Code readability shouldn't depend on IDEs.
> **P4** Explicit types are a tradeoff.

> **G1** Choose variable names that provide useful information.
> **G2** Minimize the scope of local variables.
> **G3** Consider `var` when the initializer provides sufficient information to the reader.
> **G4** Use `var` to break up chained or nested expressions with local variables.
> **G5** Don't worry too much about "programming to the interface" with local variables.
> **G6** Take care when using `var` with diamond or generic methods.
> **G7** Take care when using `var` with literals.

Everything in this file is one of those seven guidelines worked through on real QuizStakes
code, plus the two traps (interface-versus-implementation, numeric literals) that G5 and G7
exist specifically to head off, plus what happens to a `var` local when the code around it is
refactored. `01-basics.md` covered what `var` is and how type inference resolves the
initializer's type against the declaration; this file covers **when to reach for it and when
not to**, which is the question every reviewer actually asks.

---

## 1. Hierarchy: the four places `var` legally appears, and which ones this file covers

`var` is not one feature with one set of rules — the JLS restricts where it may appear, and the
style question is different in each place. `01-basics.md` proved the "local variable, not a
type" claim and worked the syntax; this table is the map before this file's streets.

| Where | Introduced | Style question this file answers | Covered here |
|---|---|---|---|
| Local variable declaration with initializer | Java 10 (JEP 286) | §2.7.1–2.7.7, 2.7.9–2.7.10 | Yes — the bulk of this file |
| Enhanced-`for` loop index/element | Java 10 | §2.7.4 | Yes |
| Try-with-resources resource variable | Java 10 | §2.7.3 | Yes |
| Implicitly-typed lambda parameter (JEP 323, Java 11) | Java 11 | §2.7.8 | Yes, briefly — it is a narrow case |

`var` cannot appear on a field, a method parameter (except the JEP 323 lambda form), a method
return type, or a variable with no initializer (`var x;` does not compile — there is nothing to
infer from). Those restrictions were `01-basics.md`'s territory; this file assumes the reader
already knows `var` is legal only where an initializer or a loop/resource binding gives the
compiler something to look at.

---

## 2.7.1 A style policy you can defend in review

### Mental model first

Treat every `var` declaration as a **two-party contract**: the initializer promises to name the
type clearly enough that a reader who cannot run an IDE can still tell what is in the variable.
`var` is not "let the compiler figure it out" from the *writer's* point of view — the compiler
always could, at compile time, from day one of Java. The question `var` raises is entirely about
the *reader*, six months later, in a code review diff, on GitHub, with no hover tooltip. If the
right-hand side already answers "what type is this", writing the type a second time on the left
is not safety — it is the same fact, twice, and now there are two places for it to drift out of
sync when one changes.

### Why it exists

Before Java 10, every local declaration repeated a type the compiler already knew:

```java
Map<RestrictionKey, Restriction> activeRestrictions = new HashMap<RestrictionKey, Restriction>();
```

Java 7's diamond operator (`<>`) trimmed the right-hand side's type arguments in 2011, but the
left-hand side stayed. Long generic chains — `PaymentIntent`, `StakeSplit`, nested
`Map<String, List<Map<String, Integer>>>` shapes over per-rail counts — turned declarations into
horizontal noise: the reader's eye has to skip past the type twice to find the variable name and
the actual logic. JEP 286 removed the second repetition, but **only for locals**, and the JEP's
own goal statement is explicit that this is a readability tool, not a terseness mandate: "to
improve the developer experience... while maintaining Java's commitment to static type
safety... without diminishing that safety." Type checking is unaffected — the compiler still
determines a fixed type at the declaration and enforces it from there on, exactly as
`01-basics.md` showed with the `javac`-produced descriptor.

### When to reach for it, and when not

Reach for `var` when the initializer already contains the type information a reader needs — a
constructor call, a static factory whose name states the type (`Executors.newFixedThreadPool`),
or a chain whose final method makes the return type obvious. Do not reach for it when the
right-hand side is a method call whose return type is not evident from its name, when the type
of the variable carries meaning beyond what the constructor already said (see §2.7.6), or when
naming the type is itself part of what the declaration is documenting (a numeric width, per
§2.7.7). The sibling that wins in the losing cases is simply: **write the type.** That is not a
failure of `var` — it is `var`'s own guide (P4) naming explicit types as a legitimate, sometimes
correct, choice.

### How it works

The style policy is not a personal taste axis with `var`-maximalist and `var`-never on opposite
ends and "moderate" in the middle. It is a single test, applied per declaration:

> **Does the initializer already name the type as clearly as an explicit declaration would?**
> If yes, `var` costs nothing and saves a repetition. If no, `var` costs the reader a lookup.

Concretely, apply G3 by asking three questions of the initializer, in order:

1. **Is it a constructor call or a `new` expression with a visible class name?** —
   `var restrictions = new HashMap<RestrictionKey, Restriction>();` names `HashMap` right there.
   Yes.
2. **Is it a well-known static factory whose name states the type?** — `var idempotencyKey =
   IdempotencyKey.of(reference);` — the factory is on the type itself, so the type is legible
   from the call. Yes.
3. **Is it a call whose declared return type is not evident from the method name alone?** —
   `var result = paymentService.reconcile(runId);` tells the reader nothing about what `result`
   is. No — write the type, or rename the variable so its *name* carries the missing
   information (`var reconciliationOutcome = ...` at least narrows the shape even without the
   exact type).

The QuizStakes team's actual review checklist, which is one legitimate instance of a policy that
satisfies all seven guidelines simultaneously:

| Situation | Verdict | Guideline |
|---|---|---|
| `var reservation = new Reservation(clientId, stakeAmount, roundId);` | Use `var` | G3 — constructor names the type |
| `var restrictionsByClient = ledger.loadRestrictions(clientId);` where `loadRestrictions` returns `List<Restriction>` in the method name's plain reading | Use `var` if the name states the shape, else write the type | G3, borderline |
| `var total = 0;` as a running sum | **Do not** use `var` unqualified — see §2.7.7 | G7 |
| `var writer = new BufferedWriter(new FileWriter(payoutFile));` inside try-with-resources | Use `var` | G4, §2.7.3 |
| `var reservationRepository = ReservationRepository.class;` (a `Class` literal being stored) | Write the type; `var` here obscures that this is metadata, not a repository instance | G1 |

### Diagram

![D-107 — A `var` policy you can defend in review](../diagrams/D-107-var-policy-can-defend.svg)
**D-107** — A `var` policy you can defend in review

The root question is exactly the test above: does the initializer already name the type? A
"yes" fans out to the three leaves this file covers as clean wins — the builder/fluent case
(§2.7.2), try-with-resources (§2.7.3), and the enhanced-`for` over `Map.Entry` (§2.7.4). A "no"
fans out to the three leaves where writing the type is the right call — an opaque factory return,
the accumulator-width trap (§2.7.7), and the interface-versus-implementation trap (§2.7.6). Each
"no" leaf in the diagram carries its concrete failure mode: `var total = 0` silently fixing the
accumulator at `int` and overflowing past `Integer.MAX_VALUE`, and `var
restrictions = new ArrayList<Restriction>()` pinning the local's static type to `ArrayList`
rather than `List` — which is exactly the trap §2.7.6 works through in full.

### A minimal concrete example

```java
// Reviewer-defensible: the constructor names the type, var costs nothing.
var restriction = new Restriction(
    new RestrictionKey(RestrictionType.STAKE_BLOCKED, RestrictionSource.SYSTEM_ONBOARDING),
    clientId,
    "onboarding restriction pending activation",
    Actor.system("AccountOpening"),
    Instant.now(),
    null,
    true
);

// Not reviewer-defensible: the method name alone does not say what comes back.
var outcome = screeningService.evaluate(clientId);
// Fix: write the type, because ScreeningVerdict vs. boolean vs. Optional<ScreeningVerdict>
// is exactly the information a reader needs and "evaluate" does not supply it.
ScreeningVerdict outcome = screeningService.evaluate(clientId);
```

### The gotcha

**Pitfall:** treating "does it compile" as the bar for using `var`. It always compiles — type
inference is a compile-time-only mechanism and every `var` local has one fixed static type from
the moment `javac` finishes. The bar this section argues for is a *readability* bar, not a
*legality* bar, and a codebase-wide lint rule that just checks "could this be `var`" enforces
the wrong thing.

> **Definition:** a defensible `var` policy is not "always" or "never" — it is per-declaration:
> use `var` exactly when the initializer already tells the reader the type, and write the type
> explicitly the moment that stops being true.

---

## 2.7.2 `var` with builders and fluent chains

### Mental model first

A fluent builder chain is a sentence, and `var` lets the reader read it as one. Without `var`,
the declaration's type takes up the entire left margin before the sentence even starts; with
`var`, the eye lands directly on the variable name and then the chain, which is where the actual
information is.

### Why it exists

Builder-style APIs became common in Java specifically because constructors with many optional
parameters are unreadable (`03-internals-*` and guide 07's Spring configuration territory both
cover the wider builder-pattern rationale; this file only covers what `var` does to it once it
exists). The builder's whole purpose is that the type of the final built object, not the
builder's own intermediate type, is what matters to the caller — and that final type is usually
named right there in the last call (`.build()`, `.create()`) or is the class whose static
`builder()` opened the chain in the first place.

### When to reach for it, and when not

Reach for `var` on a builder or fluent chain whenever the class being built is named at the
start of the chain (`Restriction.builder()...`) or the terminal call's target type is obvious
from context. Do not reach for it when the chain's terminal method returns something generic
relative to the chain (a chain that ends in `.orElse(...)` or `.map(...)` without a clear final
class in view) — there, name the type so the reader is not forced to trace the whole chain to
learn what came out the other end. This is G4 by name: `var` exists partly to let you break a
nested or chained expression into named intermediate steps without paying a second type-name
tax on each one.

### How it works

The mechanism is unchanged from `01-basics.md`: the compiler resolves the *entire* chain's
static type before inference happens, so `var` never changes which overload is picked or what
the chain returns — it only changes what appears on the left of `=`. The readability effect
comes purely from removing the repeated, often-long generic signature that would otherwise sit
between the reader and the chain:

```java
// Without var — the type occupies the same visual weight as the whole chain.
List<PaymentIntent> pendingCardWithdrawals = accountMaintenance.paymentsFor(clientId)
    .stream()
    .filter(intent -> intent.direction() == Direction.OUT)
    .filter(intent -> intent.rail() == Rail.CARD)
    .filter(intent -> intent.status() == PaymentStatus.PENDING)
    .toList();

// With var — PaymentIntent is stated once, at the point .paymentsFor(...) is defined;
// the declaration site no longer needs to restate the generic argument.
var pendingCardWithdrawals = accountMaintenance.paymentsFor(clientId)
    .stream()
    .filter(intent -> intent.direction() == Direction.OUT)
    .filter(intent -> intent.rail() == Rail.CARD)
    .filter(intent -> intent.status() == PaymentStatus.PENDING)
    .toList();
```

Both compile to the identical `List<PaymentIntent>` static type at the declaration; nothing
about stream laziness, terminal evaluation, or the `toList()` collector changes (guide 04's
`streams` files own that mechanism in full — this is purely the declaration-site question).

### Diagram

The builder and fluent-chain case is one of the "yes" leaves of D-107, embedded in §2.7.1 above.
This section does not introduce a new diagram; it is the worked expansion of that leaf.

### A minimal concrete example

```java
var restriction = Restriction.builder()
    .key(new RestrictionKey(RestrictionType.WITHDRAWAL_HELD, RestrictionSource.SYSTEM_COMPLIANCE))
    .clientId(clientId)
    .reason("AA-550 screening potential match pending review")
    .appliedBy(Actor.system("ScreeningService"))
    .appliedAt(Instant.now())
    .reversibleByOperator(false)
    .build();
```

`Restriction.builder()` names `Restriction` at the start of the chain; the reader knows the
target type before reading a single `.field(value)` call, so `var` costs nothing here and saves
repeating `Restriction` a second time on the left.

### The gotcha

**Pitfall:** using `var` on a builder chain whose *builder* type, not its *built* type, is what
gets assigned — for example, capturing an intermediate, still-mutable builder to pass around and
mutate further in multiple places. `var configuredBuilder = Restriction.builder().clientId(id);`
followed by branches that each call different further methods on `configuredBuilder` hides that
the variable is a **mutable builder**, not the immutable `Restriction` its name suggests. The
fix is either to name the type explicitly (`Restriction.Builder configuredBuilder = ...`) or,
better, to restructure so the builder is not held across branches at all.

> **Definition:** `var` on a fluent chain is defensible exactly when the chain's opening or
> closing call already states the resulting type; it exists to let a chained expression read as
> one sentence rather than a sentence with its subject restated on the left margin.

---

## 2.7.3 `var` with try-with-resources

### Mental model first

A try-with-resources resource variable is scoped to exactly one block and used for exactly one
purpose: get closed. Its declared type almost never matters beyond "does it have a `close()`
method that the compiler can call automatically" — which the compiler checks against
`AutoCloseable`/`Closeable` regardless of whether the declaration spells out the type or uses
`var`. This is one of the cleanest `var` wins in the language because the *initializer already
does all the naming work the resource statement needs*.

### Why it exists

JEP 286 explicitly extended `var` to the resource specification of try-with-resources (alongside
the enhanced-`for`), because both are declaration forms where a constructor call sits directly
next to the variable, in a syntactic slot with essentially no room for ambiguity about what type
results. Before Java 9's try-with-resources enhancement (which allowed referencing
already-declared *effectively-final* variables) and Java 10's `var`, a resource declaration was
one of the most repetitive lines in I/O-heavy code:

```java
try (BufferedWriter payoutFileWriter = new BufferedWriter(new FileWriter(payoutFile))) {
```

### When to reach for it, and when not

Reach for `var` whenever the resource is opened with a visible constructor or a clearly-named
static factory (`Files.newBufferedWriter(...)`), which is the overwhelming majority of
try-with-resources statements. Do not reach for it in the rare case where the resource's
declared type is deliberately a supertype narrower than the constructor return type — for
example, declaring a resource as `Closeable` rather than the concrete class specifically to
prevent a caller from later calling a subtype-specific method on it inside the block. That case
is exactly the interface-versus-implementation trap from §2.7.6, applied to a resource variable.

### How it works

The resource variable's scope is the try block plus the implicit compiler-generated
`finally`-equivalent that calls `close()` in reverse declaration order for multiple resources.
None of that changes with `var` — the JLS treats a `var` resource identically to an explicitly
typed one once its static type is inferred from the initializer, and the compiler still verifies
at compile time that the inferred type implements `AutoCloseable`.

```java
try (var payoutFileWriter = Files.newBufferedWriter(payoutFile.toPath())) {
    payoutFileWriter.write(renderPayoutFileLine(withdrawalTransaction));
} catch (IOException e) {
    throw new IllegalStateException("failed writing bank withdrawal payout file", e);
}
```

`Files.newBufferedWriter` names its return type in the method name itself (`BufferedWriter`),
which is precisely G3's test: the initializer already told the reader everything the explicit
type would have.

### Diagram

Try-with-resources is the second "yes" leaf of D-107, embedded in §2.7.1. No separate diagram.

### A minimal concrete example

```java
public void archiveBankSettlementBatch(PaymentRun paymentRun) throws IOException {
    var batchPath = Path.of("/var/quizstakes/payment-runs", paymentRun.id() + ".csv");
    try (var reader = Files.newBufferedReader(batchPath);
         var writer = Files.newBufferedWriter(batchPath.resolveSibling(batchPath.getFileName() + ".archived"))) {
        String line;
        while ((line = reader.readLine()) != null) {
            writer.write(line);
            writer.newLine();
        }
    }
}
```

Both resources use `var`: `Files.newBufferedReader`/`Files.newBufferedWriter` name their return
types, and multiple `var` resources in one try-with-resources statement close in the reverse of
their declaration order exactly as multiply-typed ones would — `writer` closes before `reader`.

### The gotcha

**Pitfall:** believing `var` changes anything about resource-closing order or exception
suppression. It does not — `Throwable.getSuppressed()` behaviour, the reverse-declaration-order
close sequence, and the requirement that the resource type implement `AutoCloseable` are all
resolved from the *inferred* static type at compile time, identically to an explicit
declaration. `var` is purely cosmetic here; the resource-management mechanics are untouched.

> **Definition:** `var` on a try-with-resources variable is close to a default-yes, because the
> constructor or factory that opens the resource almost always already names the type the
> declaration would otherwise repeat.

---

## 2.7.4 `var` in an enhanced-`for` over `Map.Entry<K, V>`

### Mental model first

`for (var entry : restrictionsByKey.entrySet())` replaces one of the ugliest repeated-generic
constructs left in ordinary Java code — a `Map.Entry<K, V>` loop header that names both `K` and
`V` a second time even though `restrictionsByKey.entrySet()` already pins them exactly. This is
the syllabus's own claim, and it holds up: of every `var` use case, this is the one with the
least controversy in real style guides, because the type being elided is pure repetition with
zero information loss.

### Why it exists

Before `var`, iterating a map's entries required writing the full parameterized `Map.Entry` type
in the loop header even though the map itself, one line above or even in the same expression,
already stated both type arguments:

```java
Map<RestrictionKey, Restriction> restrictionsByKey = restrictionRepository.findActive(clientId);
for (Map.Entry<RestrictionKey, Restriction> entry : restrictionsByKey.entrySet()) {
    ...
}
```

`RestrictionKey` and `Restriction` appear in that header for no reason beyond the language
requiring it — the compiler could derive both from `restrictionsByKey`'s own declared type. JEP
286 extended `var` to the enhanced-`for`'s element variable exactly to remove this specific,
maximally repetitive case.

### When to reach for it, and when not

Reach for `var` here essentially always, **provided the map's own declaration is typed clearly**
(explicitly, or itself a defensible `var` per §2.7.1). Do not reach for it if the map itself was
also declared with an undefensible `var` (an opaque factory call) — in that case the loop
header's `var` compounds a readability problem the map declaration already created, rather than
being the actual defect. Fix the map's declaration first; the loop follows once the map is
legible.

### How it works

Type inference resolves `entry`'s type from `restrictionsByKey.entrySet()`'s declared return
type, `Set<Map.Entry<RestrictionKey, Restriction>>`, and the enhanced-`for`'s own JLS rule that
the element variable's type is the set's element type — `Map.Entry<RestrictionKey,
Restriction>` — exactly as if it had been written out. `entry.getKey()` and `entry.getValue()`
are then statically typed as `RestrictionKey` and `Restriction` respectively at every use site
inside the loop, with full compile-time checking; nothing about `entrySet()`'s live view onto
the backing map, or the `ConcurrentModificationException` risk of mutating the map mid-iteration,
changes because of `var`.

### Diagram

The `Map.Entry` case is the third "yes" leaf of D-107, embedded in §2.7.1.

### A minimal concrete example

```java
Map<RestrictionKey, Restriction> restrictionsByKey = restrictionRepository.findActive(clientId);
var stakeBlockingSources = new ArrayList<RestrictionSource>();
for (var entry : restrictionsByKey.entrySet()) {
    RestrictionKey key = entry.getKey();
    Restriction restriction = entry.getValue();
    if (key.type() == RestrictionType.STAKE_BLOCKED && restriction.state() == RestrictionState.ACTIVE) {
        stakeBlockingSources.add(key.source());
    }
}
```

Compare the header alone against the pre-`var` form to see the whole point of this leaf:

```java
// Before: 40 characters of pure repetition before the loop variable's name even appears.
for (Map.Entry<RestrictionKey, Restriction> entry : restrictionsByKey.entrySet()) { ... }
// After: the same information, once, on the map's own declaration.
for (var entry : restrictionsByKey.entrySet()) { ... }
```

### The gotcha

**Pitfall:** assuming `var entry` makes `entry.getKey()`/`entry.getValue()` return `Object`.
They do not — inference pins the concrete parameterized `Map.Entry<RestrictionKey, Restriction>`
type at the declaration, so `getKey()` is statically `RestrictionKey` and a call like
`entry.getKey().nonexistentMethod()` still fails to compile, exactly as it would with the type
spelled out. `var` never widens to `Object` or erases generics at the use site — that confusion
usually comes from conflating `var` with raw types, which is an unrelated, much older Java
feature.

> **Definition:** `var` in an enhanced-`for` over `Map.Entry<K, V>` removes a pure repetition of
> the map's own already-declared type arguments, with the loop body's static typing completely
> unaffected.

---

## 2.7.5 `var` for deeply generic types

### Mental model first

The deeper the generic nesting, the stronger the case for `var` — and also the stronger the case
for checking that the initializer still names the type clearly, because a deeply nested generic
signature is exactly where an opaque factory call becomes hardest to reverse-engineer by eye.

### Why it exists

`Map<String, List<Map<String, Integer>>>` is a legitimate, if uncomfortable, shape for real
aggregation code — a per-rail breakdown of per-status counts, keyed first by rail name then by a
list of per-window count maps, is exactly the sort of structure a reporting job over QuizStakes'
95k/day card deposits or 6.5k/day bank deposits produces. Before `var`, that whole signature had
to be written twice per declaration: once on the left as the declared type, once on the right
inside the `new HashMap<>()` call's inferred diamond, or worse, spelled out on both sides before
Java 7's diamond operator existed at all.

### When to reach for it, and when not

Reach for `var` when the deeply nested generic type is being *constructed* right there
(`new HashMap<String, List<Map<String, Integer>>>()`) — the constructor call names every layer
of the nesting, so `var` removes a second, character-for-character identical restatement.
Do not reach for it when the deeply nested type comes back from a method whose name does not
make the *shape* obvious — `var breakdown = reportingService.summarize(runId);` tells the reader
nothing about whether `breakdown` nests three levels or five. In that case, either write the
type or, preferably, give the shape a name: define a small record or a type alias-equivalent
(a domain type such as `RailStatusBreakdown`) so the reader never has to parse a three-level
generic signature to understand what is in the variable at all. G1's own advice — "choose
variable names that provide useful information" — pulls the same direction: `var
countsByRailThenWindow` compensates for what the raw generic signature does not say.

### How it works

Nothing about generic type inference changes when `var` is layered on top of it — the compiler
first resolves the initializer expression's type, applying the diamond operator's own target-type
inference where relevant, and *then* assigns that fully-resolved parameterized type to the `var`
local. The two inference mechanisms are independent and run in a fixed order: diamond inference
happens first (bounded by the constructor's declared type parameters and any explicit type
witness), producing a complete parameterized type, and *that* complete type is what `var` then
binds to the local. There is no additional loss of type information from stacking the two — the
resulting static type of a `var`-declared, diamond-constructed local is identical to what an
explicit declaration would have produced.

### Diagram

Deeply generic types are not a separate leaf of D-107 — they are the general case of the "yes"
side (constructor already names the type) taken to its most extreme nesting, and of the "no"
side (opaque factory) when the nesting comes back from an unclear method name. No new diagram.

### A minimal concrete example

```java
// Per-rail card-deposit counts, grouped further by amount-band window — a genuinely
// deep shape that a reporting job over the 95k/day card-deposit volume would produce.
var depositCountsByRailThenBand = new HashMap<String, List<Map<String, Integer>>>();

var cardBandCounts = new HashMap<String, Integer>();
cardBandCounts.put("UNDER_50", 61_750);
cardBandCounts.put("50_TO_200", 28_500);
cardBandCounts.put("OVER_200", 4_750);
depositCountsByRailThenBand.put("CARD", List.of(cardBandCounts));

var bankBandCounts = new HashMap<String, Integer>();
bankBandCounts.put("UNDER_50", 900);
bankBandCounts.put("50_TO_200", 3_900);
bankBandCounts.put("OVER_200", 1_700);
depositCountsByRailThenBand.put("BANK", List.of(bankBandCounts));
```

The declared-and-constructed line names every generic layer once — `Map<String,
List<Map<String, Integer>>>` — and `var` removes only the character-for-character duplicate that
would otherwise sit on the left of the same line.

### The gotcha

**Pitfall:** using `var` to *avoid thinking about* a deeply nested generic shape rather than to
avoid *repeating* it. If a reviewer cannot tell from the declaration line alone what
`depositCountsByRailThenBand` contains, the fix is not to write the four-level generic type back
out — it is usually that the shape itself is too deep for a bare `Map`-of-`Map`-of-`List` and
should be a small domain type (`RailStatusBreakdown` as a record wrapping the same data with
named accessors). `var` correctly hides *repetition*; it should never be asked to hide
*complexity that the design itself should not have*.

> **Definition:** `var` scales *better*, not worse, as generic nesting deepens, provided the
> nested type is stated once, in full, at construction — the deeper the nesting, the more a
> second character-for-character copy on the declaration's left side costs the reader for zero
> benefit.

---

## 2.7.6 `var` and the interface-versus-implementation question

### Mental model first

An explicitly-typed local declared as `List<Restriction> restrictions = new
ArrayList<>();` has two types in play: the **static type** the rest of the method sees
(`List`) and the **runtime type** the object actually is (`ArrayList`). `var restrictions = new
ArrayList<>();` collapses those into one — the local's static type *becomes* `ArrayList`,
because there is no longer a left-hand-side type to program against. This is not a corner case;
it is the single mechanical fact this whole section exists to make unmissable.

### Why it exists

Explicit-type declarations gave Java developers a long-standing idiom, itself sometimes called
"program to the interface, not the implementation": declare the variable's type as the most
general interface that the rest of the code needs, even when the concrete object underneath is
a specific implementation. The idiom's benefit is that later code cannot accidentally call a
method that only the concrete class has, and swapping the concrete implementation later (say,
`ArrayList` to `LinkedList`, or `HashMap` to `LinkedHashMap`) requires touching only the
`new` expression, not every line that uses the variable. `var` removes the left-hand-side type
entirely, which removes the *place* that idiom lived.

### When to reach for it, and when not — `[PROVE]`

The syllabus tags this leaf `[TRAP]` and `[PROVE]`, so the claim is worked through with a
compiling example rather than asserted. Consider a method that builds a restriction list and
later needs only `List`'s contract:

```java
public List<Restriction> activeRestrictionsSortedByRecency(ClientId clientId) {
    var restrictions = restrictionRepository.findActive(clientId); // returns ArrayList<Restriction>
    restrictions.sort(Comparator.comparing(Restriction::appliedAt).reversed());
    return restrictions; // fine: List<Restriction> is a valid return type for an ArrayList<Restriction>
}
```

That compiles today. Now a teammate refactors `restrictionRepository.findActive` to return an
**immutable** `List` (say, `List.copyOf(...)` internally, still declared as returning
`List<Restriction>` from the repository's own signature — no signature change at all, only a
runtime-type change inside its implementation). Nothing about `var`'s *inference* changes: `var
restrictions` was never pinned to `ArrayList` here, because the repository method's own declared
return type was already `List<Restriction>`, and `var` copies exactly that declared type, not
whatever concrete class the method happens to return internally. **This example does not
demonstrate the trap** — it demonstrates the case where the trap does *not* fire, because the
initializer's own static type was already the interface.

The trap fires only when the initializer's expression *is itself* the concrete constructor call,
with no intervening method boundary to hide it:

```java
public List<Restriction> activeRestrictionsSortedByRecency(ClientId clientId) {
    var restrictions = new ArrayList<>(restrictionRepository.findActive(clientId));
    restrictions.sort(Comparator.comparing(Restriction::appliedAt).reversed());
    return restrictions; // still fine — ArrayList<Restriction> is-a List<Restriction>, upcast on return
}

// But now suppose a second method, added later, holds the same-shaped local for longer:
public void reindexActiveRestrictions(ClientId clientId) {
    var restrictions = new ArrayList<>(restrictionRepository.findActive(clientId));
    restrictions.removeIf(r -> r.state() != RestrictionState.ACTIVE);
    restrictions.trimToSize(); // ArrayList-only method — compiles ONLY because var pinned the
                               // local's static type to ArrayList, not List.
    restrictionIndex.rebuild(restrictions);
}
```

`restrictions.trimToSize()` compiles in the second method precisely *because* `var` inferred
`ArrayList<Restriction>` as the local's static type from the `new ArrayList<>(...)` expression.
If a future refactor changes the initializer to `List.copyOf(restrictionRepository
.findActive(clientId))` — swapping to an immutable list because someone decided the method
should not mutate the repository's data — the `restrictions.trimToSize()` line, and the earlier
`removeIf`, both stop compiling (`trimToSize` does not exist on `List.copyOf`'s returned type,
and mutation methods on an immutable list compile but throw `UnsupportedOperationException` at
runtime instead — a worse failure, because it surfaces only when that line executes). **That is
the proof**: `var`'s inferred type is not "whatever the code logically needs" — it is
*mechanically* the initializer expression's own static type, concrete class included, and every
later line in that variable's scope is checked against exactly that type. An explicit `List<
Restriction> restrictions = new ArrayList<>(...)` declaration would have caught
`restrictions.trimToSize()` as a compile error on the **first** line that tried it, at write
time, instead of only breaking later when the initializer changes.

### How it works

Static type resolution for `var` runs once, at the declaration, from the initializer expression's
own type — never from how the variable is used afterward, and never from what the surrounding
method's return type or contract implies it *should* be. `new ArrayList<>(...)` has static type
`ArrayList<Restriction>` (parameterized via diamond inference from the constructor argument);
`var` copies that exact type onto the local, full stop. G5's own guidance is deliberately
permissive here — "don't worry too much about programming to the interface with local
variables" — and the reasoning behind that permissiveness is scope: a *local* variable typically
lives for a handful of lines inside one method, which is a small enough surface for a human
reviewer to just look at every subsequent use and check none of them assume something
implementation-specific went wrong. A *field* or a *method parameter* is a much larger surface
(every caller, every subclass), which is exactly why G5 is scoped to locals and does not extend
to those.

### Diagram

The interface-versus-implementation trap is the third "no" leaf of D-107, embedded in §2.7.1,
captioned with `var list = new ArrayList<String>()` pinning the local's type to `ArrayList` as
its concrete failure mode.

### A minimal concrete example

```java
// Trap in miniature, self-contained and compiling:
var stakeSplitsByReservation = new LinkedHashMap<ReservationId, StakeSplit>();
stakeSplitsByReservation.put(reservation.id(), stakeSplit);
var firstEntry = stakeSplitsByReservation.entrySet().iterator().next();
// LinkedHashMap-specific guarantee (insertion order) is being relied upon here, but nothing
// in the declaration site records that reliance — a reader has to trace back to the `new
// LinkedHashMap<>()` call to know insertion order is even guaranteed, because the static
// type at every USE SITE is LinkedHashMap, not the interface Map.
```

### The gotcha

**Pitfall:** believing `var` is "the same as programming to the interface, just with less
typing." It is the opposite for the local's *own* static type — an explicit `List<Restriction>
restrictions = new ArrayList<>();` genuinely programs to the interface (later lines are checked
against `List`, and any accidental `ArrayList`-only call is a compile error at that line);
`var restrictions = new ArrayList<>();` programs to the concrete class, and the interface
discipline is preserved only at the method's **return statement**, where an implicit widening
reference conversion happens if the return type is declared as the interface. Inside the method
body, between declaration and return, the static type is the concrete class the whole time.

> **Definition:** `var`'s inferred type is the initializer expression's own static type,
> concrete class included when the initializer is a direct constructor call — G5's advice to not
> worry about this is scoped specifically to locals, where the blast radius of a later
> implementation-specific call is one method body, not every caller of a field or parameter.

---

## 2.7.7 `var` and numeric literals — `[TRAP]` `[NUM]` `[X-REF 03]`

### Mental model first

A numeric literal is itself the smallest possible initializer, and it carries almost no visual
signal about which primitive width it produces. `0`, `0L`, `0.0`, and `0.0f` are visually four
characters apart at most, but they select four different primitive types with four different
overflow behaviours — and `var` removes the one place, the explicit declared type, that used to
force the width decision to be made and stated.

### When to reach for it, and when not

Reach for `var` on a numeric literal declaration only when a suffix or an explicit cast already
states the width unambiguously — `var timeoutMillis = 30_000L;`, `var conversionRate = 1.0d;`.
Do not reach for it on a bare, unsuffixed integer literal used as an accumulator, counter, or
anything that will be added to repeatedly across a loop with an unknown or large iteration
count — write the type explicitly there, because the type is exactly the fact a reviewer needs
to check that the width is adequate for the values involved.

### How it works — `[NUM]`, worked with the arithmetic shown

Java's literal rules (JLS §3.10.1) assign every unsuffixed integer literal the type `int`, and
every unsuffixed floating-point literal the type `double`, regardless of context. `var` performs
no special-casing here — it copies whatever type the literal already has under those JLS rules.
So `var total = 0;` produces a **32-bit `int`** local, full stop, and every `total += x;` that
follows performs 32-bit two's-complement addition with silent wraparound on overflow.

The concrete overflow arithmetic, using QuizStakes' own volume figures (stake reservations run
2.8M/day at an average value of 4.20, expressed here in minor units — pence — so the numbers stay
integral): suppose a naive daily-total accumulator sums reservation amounts in minor units across
a single day's 2,800,000 reservations, each nominally 420 minor units:

```
2,800,000 reservations × 420 minor units = 1,176,000,000
Integer.MAX_VALUE                        = 2,147,483,647
```

That single day's total, 1,176,000,000, does not overflow `int` on its own — it sits comfortably
under `Integer.MAX_VALUE`. But accumulate **two** such days into the same `int` without resetting
(a plausible bug: a rolling accumulator that should have been scoped per-day but was not reset):

```
1,176,000,000 + 1,176,000,000 = 2,352,000,000
Integer.MAX_VALUE             = 2,147,483,647
overflow amount               = 2,352,000,000 - 2,147,483,647 - 1 = 204,516,352
wrapped result (two's complement) = 2,352,000,000 - 2^32
                                   = 2,352,000,000 - 4,294,967,296
                                   = -1,942,967,296
```

The accumulator silently becomes a large **negative** number rather than throwing — exactly the
same class of failure the verified-figures block demonstrates for `Collectors.summingInt`, which
this leaf cross-references directly: `summingInt`'s accumulator is a `new int[1]` holding the
running sum *as an `int`*, so a `Collectors.summingInt(...)` reduction over enough
QuizStakes-scale monetary values has the identical silent-wraparound failure mode as a bare `var
total = 0;` loop — proved on this machine (`javac --release 21`) by summing 1,000,000,000 three
times:

```
summingInt : -1294967296
summingLong: 3000000000
expected   : 3000000000
```

`averagingInt` is the one collector in that family that is genuinely safe from this, because its
accumulator is a `long[2]` (sum, count) rather than an `int[1]` — the width decision was made
correctly inside the JDK's own implementation, which is the whole point: **the width is a
decision, and it needs to be visible**, whether that visibility comes from an explicit `long
total = 0L;` declaration or from choosing `summingLong`/`averagingInt` over `summingInt`. The
full mechanism of which JDK collector accumulates into which array width is guide 04's
`collectors` files' territory in depth; the fact needed here is only that the same trap recurs at
every layer that hides an `int`-width accumulator behind a short declaration.

### Diagram

The numeric-literal trap is the second "no" leaf of D-107, embedded in §2.7.1, captioned with
`var total = 0` overflowing as its concrete failure mode.

### A minimal concrete example

```java
public Money sumReservationsUnsafely(List<Reservation> reservations) {
    var total = 0; // int — silently wraps past Integer.MAX_VALUE on large volumes
    for (var reservation : reservations) {
        total += reservation.amount().minorUnits(); // int addition, no overflow check
    }
    return Money.ofMinorUnits(total, Currency.getInstance("GBP"));
}

public Money sumReservationsSafely(List<Reservation> reservations) {
    long total = 0L; // explicit type states the width decision; var would have hidden it
    for (var reservation : reservations) {
        total = Math.addExact(total, reservation.amount().minorUnits()); // throws on overflow
    }
    return Money.ofMinorUnits(total, Currency.getInstance("GBP"));
}
```

### The gotcha

**Pitfall:** believing `var total = 0L;` and `var total = 0;` differ only in the number of
characters typed. They differ in width — 64 bits versus 32 — and the only signal that
distinguishes them is the `L` suffix on the literal itself. A reviewer scanning a diff for
`var total = 0` will not visually distinguish the safe form from the unsafe one nearly as fast as
they would distinguish `long total = 0;` from `int total = 0;`, because the suffix is one
character sitting inside a token, not a whole separate word at the start of the line.

**Why people believe it is fine:** most `var`-with-a-literal code in tutorials uses small,
bounded loop counters (`for (var i = 0; i < 10; i++)`) where overflow is never remotely reachable,
and the habit generalizes incorrectly to accumulators over unbounded or large-volume data, which
is exactly the QuizStakes-scale case where it stops being safe.

> **Definition:** `var` on a numeric literal inherits the JLS's own default widths — `int` for
> unsuffixed integers, `double` for unsuffixed decimals — so any accumulator whose total could
> plausibly exceed those widths' range must either keep an explicit type or add the width
> suffix; `var` provides no additional narrowing or widening behaviour of its own.

---

## 2.7.8 `var` in lambda parameters

### Mental model first

JEP 323 (Java 11) let a lambda's parameter list use `var` instead of either the fully-inferred
implicit form (`(x, y) -> ...`) or the fully-explicit form (`(RestrictionKey x, Restriction y)
-> ...`). It is the narrowest of the four `var` locations in this file, because the *only* thing
it adds over the plain implicit form is a syntactic place to hang an annotation.

### Why it exists

Before JEP 323, a lambda parameter had exactly two spellings: fully implicit or fully explicit,
and a lambda could not mix the two within one parameter list, and — critically — the implicit
form gave no syntactic slot for a type annotation such as `@NonNull`. JEP 323's stated purpose is
narrowly that: "allow `var` to be used when declaring the formal parameters of implicitly typed
lambda expressions," specifically so annotations could be attached without forcing the whole
parameter list into fully-explicit types.

### When to reach for it, and when not

Reach for `var` in a lambda parameter list only when an annotation needs a place to attach — for
example a nullability or a validation annotation from a framework guide 07 or 13's territory
might apply. Do not reach for it as a stylistic default over the plain implicit form: `(var
restriction) -> restriction.state() == RestrictionState.ACTIVE` gains nothing over `restriction
-> restriction.state() == RestrictionState.ACTIVE` and is strictly more characters for identical
information. All parameters in one lambda's parameter list must use the same form — the JLS
requires the list to be entirely implicit, entirely explicit, or entirely `var`; mixing (`(var
x, Restriction y) -> ...`) is a compile error.

### How it works

Lambda parameter types, whether implicit or spelled with `var`, are resolved through **target
typing** against the functional interface the lambda is assigned to, not through any inference
mechanism internal to the lambda itself — this is the same target-typing mechanism `01-basics.md`
and guide 04's `lambdas` files cover for the implicit form. `var` in this position is inference
*syntax* layered on top of target typing, not a second, independent inference pass: the compiler
determines the functional interface's abstract method signature first, and `var` simply lets that
already-determined parameter type be spelled with the keyword instead of omitted entirely.

```java
Predicate<Restriction> isActiveStakeBlock = (var restriction) ->
    restriction.key().type() == RestrictionType.STAKE_BLOCKED
        && restriction.state() == RestrictionState.ACTIVE;
```

Here `restriction`'s type is `Restriction`, exactly as it would be under the fully implicit
form — `Predicate<Restriction>`'s target type supplies it. `var` neither adds nor removes
information at the type level; it exists purely for the annotation slot.

### Diagram

Not diagrammed — the syllabus assigns this leaf no diagram, and it is a narrow, single-purpose
case rather than one of D-107's decision-tree leaves.

### A minimal concrete example

```java
BiPredicate<@NonNull RestrictionKey, @NonNull Restriction> keyMatchesRestriction =
    (@NonNull var key, @NonNull var restriction) -> restriction.key().equals(key);
```

Without `var`, `@NonNull key` and `@NonNull restriction` alone (with no type) do not compile —
an annotation on an implicit-form parameter has nothing to attach to syntactically. Writing the
full explicit type (`@NonNull RestrictionKey key`) works too, but forces every other parameter
in the list to also be explicit even if their types are long and add nothing. `var` is the
middle ground built specifically for this.

### The gotcha

**Pitfall:** reaching for `var` in a lambda parameter list as if it were a general style
preference the way §2.7.1–2.7.5 are. It is not — outside the annotation case, it is strictly a
wash against the implicit form, and using it as a default habit is the one place in this file's
scope where `var` adds characters without adding reader value.

> **Definition:** `var` in a lambda parameter list is target-typed exactly like the implicit
> form and differs from it only in providing a syntactic position for a parameter annotation —
> its sole legitimate use case.

---

## 2.7.9 `var` and refactoring — `[TRAP]`

### Mental model first

A `var` local's type is not looked up once and then forgotten — it is *derived*, every time the
file is compiled, from whatever the initializer's declared type happens to be at that moment.
Change the initializer's source — most commonly, change the return type of a method the
initializer calls — and every `var` local that captured that call's result silently re-derives
a new type on the next compile, with no edit to the declaration line itself.

### Why it exists — the mechanism, `[PROVE]`

This is not a special "refactoring mode" of `var` — it falls directly out of the basic
inference rule from `01-basics.md`: the compiler determines a `var` local's type from the
initializer expression's own static type, at every compile. An explicitly-typed local's
declared type is a separate, independent fact from the initializer's type (checked for
*assignability*, not *equality*, at compile time) — change the initializer's type underneath it,
and the explicit declaration either still compiles (if the new type is still assignable) or
fails loudly at the declaration line. A `var` local has no independent fact to check against —
there is nothing for the new initializer type to be assignable *to*, because the declaration's
own type **is** whatever the initializer says this time.

Worked through with a concrete two-step refactor:

```java
// Step 0 — before refactor
public interface RestrictionRepository {
    List<Restriction> findActive(ClientId clientId); // returns ArrayList<Restriction> today
}

public int countStakeBlocks(ClientId clientId) {
    var restrictions = restrictionRepository.findActive(clientId); // var -> List<Restriction>
    return (int) restrictions.stream()
        .filter(r -> r.key().type() == RestrictionType.STAKE_BLOCKED)
        .count();
}
```

```java
// Step 1 — a teammate changes ONLY the repository method's declared return type,
// from List<Restriction> to Collection<Restriction>, believing it a safe widening
// (every List is a Collection, so every existing CALLER site should still compile).
public interface RestrictionRepository {
    Collection<Restriction> findActive(ClientId clientId);
}
```

`countStakeBlocks` above still compiles without any edit, because `Collection<Restriction>`
still has `.stream()`. But now consider a *sibling* method that also called `findActive` and
also used `var`, and that — unlike `countStakeBlocks` — relied on `List`-specific behaviour:

```java
public Restriction mostRecentRestriction(ClientId clientId) {
    var restrictions = restrictionRepository.findActive(clientId); // was List<Restriction>,
                                                                     // now Collection<Restriction>
    return restrictions.get(restrictions.size() - 1); // Collection has no get(int) — COMPILE ERROR
}
```

Before the refactor, `restrictions` was `List<Restriction>` and `.get(int)` compiled. After the
refactor, `var` silently re-derives `restrictions` as `Collection<Restriction>`, and
`.get(restrictions.size() - 1)` fails to compile with `cannot find symbol: method get(int)` —
**at the call site, with no edit to that line**, which is exactly the behaviour the syllabus
leaf describes as "sometimes a compile error where you want one." That is the *good* outcome —
the compiler caught it. The syllabus's other half — "sometimes a behaviour change where you do
not" — needs a case where the new type is still assignment-compatible with everything the code
does, so nothing fails to compile, but semantics shift silently:

```java
public interface RestrictionRepository {
    List<Restriction> findActive(ClientId clientId); // Step 0: backed by ArrayList (any order kept)
}
// Step 1: teammate changes the IMPLEMENTATION only, still returning List<Restriction>, but now
// backed by a data structure with different iteration-order guarantees — say, from an ArrayList
// preserving insertion/query order to a sorted TreeList-equivalent reordered by appliedAt.
// The DECLARED type List<Restriction> does not change, so var's inferred type does not change
// either, and every caller — var or explicit — still compiles.
```

That variant shows the inverse: because the *declared* type did not change, `var` gives no
extra exposure here at all — an explicitly-typed `List<Restriction> restrictions = ...` local
would have exactly the same silent exposure to an iteration-order change, because that risk
lives in the implementation behind the declared type, not in the declaration syntax. The `[TRAP]`
this leaf actually targets is specifically the first variant — **a declared return-type change**
propagating silently through every `var` local that captured a call to it, whereas an explicitly
typed local would have needed the *declared* type to still be assignment-compatible, and would
have failed loudly at exactly the lines that relied on the narrower type.

### When to reach for it, and when not

This is not a "when to use `var`" question in the same sense as the earlier leaves — it is a
"what to check before merging a return-type-widening refactor" question. Reach for a
codebase-wide search of `var` locals that call the changed method before merging any refactor
that **widens** a method's declared return type (interface generalization, `List` to
`Collection`, a concrete class to an interface). Do not assume "I only widened the type, so
nothing downstream needs the diff reviewed" — that assumption is true for explicitly-typed
callers and false for `var` callers, which is precisely the asymmetry this leaf exists to name.

### How it works

Re-derivation happens at **every** compile, because `var` performs no caching of a previously
inferred type across compilations — there is no such concept. Each build is a fresh application
of the same inference rule from `01-basics.md` against whatever the initializer's current static
type is. This is also why `var` and refactoring interact more sharply with **binary-only**
changes than explicit types do: if `RestrictionRepository` lives in a separately-versioned
library and only its compiled artifact changes (return type widened, recompiled, republished),
every `var`-declared caller in the dependent module re-derives its local's type the next time
*that module* recompiles against the new artifact — with zero source edits in the dependent
module at all, and a diff that shows nothing changed in the file that broke.

### Diagram

Not a separate D-107 leaf — this is a consequence of the interface-versus-implementation trap
(§2.7.6) unfolding over time rather than a distinct decision-tree branch.

### A minimal concrete example

Already worked in full above (`countStakeBlocks` / `mostRecentRestriction` against a
`findActive` return-type widening from `List<Restriction>` to `Collection<Restriction>`).

### The gotcha

**Pitfall:** reviewing a return-type-widening pull request by checking only the callers that
show up as compile errors in CI and assuming that is the complete blast radius. It understates
the risk for `var` callers in exactly the second sense above: a `var` caller whose new inferred
type is *still* assignment-compatible with everything the method body does will not fail to
compile at all, so CI shows nothing, and the exposure is purely semantic — silent until a test
or production behaviour catches the difference.

> **Definition:** a `var` local's type is re-derived from its initializer at every compile with
> no independent declared type to check against, so a method's return-type change propagates
> through every `var`-declared caller either as a compile error (when the new type drops a
> capability the caller used) or as a silent semantic shift (when it does not) — an explicitly
> typed caller only ever gets the first outcome.

---

## 2.7.10 Team conventions, and why both extremes fail the style guide's own test

### Mental model first

"Never use `var`" and "always use `var`" are both attempts to replace a per-declaration judgment
call with a rule that needs no judgment. They fail for the same underlying reason, from opposite
directions: each optimizes for one of the two parties to the "two-party contract" from §2.7.1
mental model while ignoring the other.

### Why it exists — the two failure modes, worked

**"Never use `var"` fails P4 and G3 directly.** P4 states plainly that explicit types are a
*tradeoff* — not a default-correct choice — and a blanket ban treats every declaration as
belonging on the "write the type" side of the test in §2.7.1, including the ones where the
initializer already names the type as clearly as any explicit declaration would (a direct
constructor call, a factory named after its return type). Applied to `var restriction = new
Restriction(...)`, a "never" policy forces `Restriction restriction = new Restriction(...)`,
which is the exact repetition JEP 286 exists to remove, for zero readability gain — the
type appears twice, in the same visual position, saying the same thing.

**"Always use `var`" fails G3, G6, and G7 simultaneously.** Applied uniformly, it forces `var`
onto exactly the cases this file spent nine sections showing are the wrong call: `var outcome =
screeningService.evaluate(clientId);` (§2.7.1, opaque factory), `var total = 0;` used as an
accumulator (§2.7.7, width trap), and `var restrictions = new ArrayList<>();` where later code
needs the `List` contract enforced (§2.7.6, interface-versus-implementation trap). A blanket
"always" rule cannot distinguish any of these from the genuinely good cases in §2.7.2–2.7.5,
because the whole distinguishing test — does the initializer already name the type clearly
enough — is precisely the judgment a blanket rule is designed to avoid making.

### When to reach for it, and when not

The team convention this file argues for is not a third rule to memorize — it is the single test
from §2.7.1, applied consistently: **use `var` exactly when the initializer already tells the
reader the type as clearly as an explicit declaration would.** Do not adopt a linter rule that
scores "percentage of eligible declarations using `var`" as a code-quality metric — that metric
is satisfiable by exactly the "always" failure mode above, and it actively rewards violating
§2.7.6 and §2.7.7.

### How it works

A workable team policy is a **checklist a reviewer can apply in the few seconds a code-review
tool gives them**, not a philosophy. The one this file has built, section by section, is:

| Check | Pass → `var` is fine | Fail → write the type |
|---|---|---|
| Constructor/factory names the type (§2.7.1–2.7.5) | Yes | No |
| Not an unsuffixed numeric-literal accumulator (§2.7.7) | Yes | No |
| Not relying on a concrete-class-only method later in scope (§2.7.6) | Yes | No |
| Not a lambda parameter with no annotation to attach (§2.7.8) | N/A or yes | No (no benefit either way) |

### Diagram

This section synthesizes D-107 as a whole (embedded and explained in §2.7.1) rather than adding
a new one — the decision tree the diagram draws **is** the team convention.

### A minimal concrete example

```java
// A short method demonstrating a defensible, mixed policy in one place — not "all var"
// or "no var", but each declaration judged on the §2.7.1 test individually.
public Money settleWinningStake(Reservation reservation, Money winnings) {
    var stakeSplit = reservation.stakeSplit();               // constructor-backed record accessor — clear
    long bonusReturnedMinorUnits = stakeSplit.bonusPortion().minorUnits(); // width matters — explicit
    var ledgerEntries = new ArrayList<LedgerEntry>();         // constructor names the type — clear
    ledgerEntries.add(LedgerEntry.credit(CLIENT_CASH_AVAILABLE, winnings));
    ledgerEntries.add(LedgerEntry.credit(CLIENT_BONUS_AVAILABLE, stakeSplit.bonusPortion()));
    return winnings;
}
```

### The gotcha

**Pitfall:** adopting a team-wide `var` policy that a linter enforces mechanically by pattern
(for example, "always `var` when the right side has `new`") rather than by the actual test. A
mechanical "always `var` after `new`" rule gets §2.7.2–2.7.5 right by accident but still walks
straight into §2.7.6's trap on `var restrictions = new ArrayList<>();` followed by an
`ArrayList`-only call — the presence of `new` says nothing about whether later code needs the
interface.

> **Definition:** a defensible team `var` convention is not a threshold on how often `var`
> appears — it is a shared, applied answer to one question per declaration: does the initializer
> already tell the reader the type as clearly as writing it out would?

---

## Pitfalls

### Believing a codebase-wide `var`-usage percentage is a quality signal

**Wrong**

```java
// A linter rule scoring "78% of eligible locals use var" as good, pushing toward 100%.
var total = 0;                                    // accumulator — should stay explicit
var outcome = screeningService.evaluate(clientId); // opaque factory — should stay explicit
var restrictions = new ArrayList<Restriction>();   // fine on its own, but risky if later code
                                                    // needs List, per §2.7.6
```

**Right**

```java
long total = 0L;                                        // width stated explicitly
ScreeningVerdict outcome = screeningService.evaluate(clientId); // type states what came back
List<Restriction> restrictions = new ArrayList<>();      // interface enforced for the rest.md of scope
```

**Why people believe it:** a percentage is trivial to compute and put on a dashboard, and
"more `var`" superficially correlates with "shorter, more modern-looking code" — but the
correlation breaks exactly at the three cases this file spent most of its length on.

### Assuming `var` widens or erases generic information at use sites

**Wrong**

```java
for (var entry : restrictionsByKey.entrySet()) {
    Object key = entry.getKey(); // treating entry.getKey() as if var erased it to Object
}
```

**Right**

```java
for (var entry : restrictionsByKey.entrySet()) {
    RestrictionKey key = entry.getKey(); // entry.getKey() is statically RestrictionKey, not Object
}
```

**Why people believe it:** `var`'s keyword resembles JavaScript's dynamically-typed `var`/`let`,
and the surface similarity leads to importing an assumption about dynamic typing that Java's
`var` never had — Java's is 100% static, resolved once at compile time.

### Treating "always use `var` after `new`" as equivalent to the §2.7.1 test

**Wrong**

```java
var restrictions = new ArrayList<Restriction>();
restrictions.removeIf(r -> r.state() != RestrictionState.ACTIVE);
restrictions.trimToSize(); // compiles only because var pinned ArrayList — a mechanical
                           // "var after new" rule cannot see this risk coming
```

**Right**

```java
List<Restriction> restrictions = new ArrayList<>(); // trimToSize() correctly fails to compile
restrictions.removeIf(r -> r.state() != RestrictionState.ACTIVE);
```

**Why people believe it:** "`new` on the right means the type is obvious" is true for *what the
type is* but says nothing about *whether later code should be allowed to depend on it being that
concrete type* — two different questions that a mechanical rule conflates.

---

## Cheat sheet

| Case | Use `var`? | Guideline | Section |
|---|---|---|---|
| Constructor call, class named on the right (`new Restriction(...)`) | Yes | G3 | §2.7.1 |
| Fluent/builder chain, target type named at chain start or end | Yes | G4 | §2.7.2 |
| Try-with-resources, factory/constructor names the resource type | Yes | G4 | §2.7.3 |
| Enhanced-`for` over `Map.Entry<K, V>`, map itself typed clearly | Yes | JEP 286 | §2.7.4 |
| Deeply nested generic, constructed right there | Yes | G3 | §2.7.5 |
| Opaque method call whose name doesn't state the return type | No — write the type | G1, G3 | §2.7.1 |
| Local needs to be programmed against an interface for the rest of its scope | No — write the interface type | G5 (scoped) | §2.7.6 |
| Unsuffixed numeric-literal accumulator | No — write the width (`long`, suffix `L`) | G7 | §2.7.7 |
| Lambda parameter, no annotation needed | Either — no benefit from `var` | — | §2.7.8 |
| Lambda parameter, annotation needed | `var` (only way to attach it) | JEP 323 | §2.7.8 |
| Reviewing a return-type-widening refactor | Search all `var` callers of the changed method, not just CI failures | — | §2.7.9 |
| Team-wide policy | Per-declaration test, never a blanket "always"/"never" | P4, G3–G7 | §2.7.10 |

---

## Self-test

**Q1.** Under the OpenJDK LVTI style guide, what single question does G3 ask, and why does that
make "never use `var`" and "always use `var`" both fail?

<details><summary>Answer</summary>

G3 asks whether the initializer already provides sufficient information for the reader to know
the type. "Never" fails because it forces explicit types even where the initializer already
states the type clearly (a direct constructor call), producing pure repetition for no
readability gain — exactly the case JEP 286 exists to remove. "Always" fails because it applies
`var` even where the initializer does not state the type clearly (an opaque method call) or where
stating the type explicitly is itself the point (a numeric-literal accumulator's width, or a
local that needs an interface-typed contract for the rest of its scope) — both blanket rules
replace a per-declaration judgment with a rule that cannot make the judgment at all.

</details>

**Q2.** Given `var restrictions = new ArrayList<Restriction>();` followed later in the same
method by `restrictions.trimToSize();`, what is the local's static type, and what happens if the
initializer is later changed to `List.copyOf(...)`?

<details><summary>Answer</summary>

The local's static type is `ArrayList<Restriction>`, inferred directly from the `new
ArrayList<>()` constructor call — `var` copies the initializer expression's own static type
exactly, concrete class included. `trimToSize()` compiles today because `ArrayList` declares it.
If the initializer changes to `List.copyOf(...)`, the local's inferred type becomes whatever
`List.copyOf` declares as its return type (`List<Restriction>`), and `restrictions.trimToSize()`
stops compiling immediately — `trimToSize` is not a member of `List`. This is the
interface-versus-implementation trap: the failure surfaces at the *use site*, with no edit to
that line, because `var`'s inferred type tracks the initializer, not any independent declared
type on the local itself.

</details>

**Q3.** Why does `var total = 0;` risk silent overflow in a way that `long total = 0L;` does
not, and what JLS rule makes `0` an `int` in the first place?

<details><summary>Answer</summary>

JLS §3.10.1 assigns every unsuffixed integer literal the type `int`; `var` performs no
special-casing and simply copies that type onto the local, giving a 32-bit accumulator. Repeated
`+=` on that local performs 32-bit two's-complement addition, which wraps silently past
`Integer.MAX_VALUE` (2,147,483,647) rather than throwing — for example, two days of QuizStakes
stake-reservation minor-unit totals (1,176,000,000 each) summed into the same unreset `int`
accumulator produce 2,352,000,000, which wraps to −1,942,967,296. `long total = 0L;` (or the `L`
suffix on the literal) makes the accumulator 64 bits, whose range comfortably covers
QuizStakes-scale volumes, and the explicit declaration also makes the width decision visible to a
reviewer scanning the line — `var total = 0L;` hides that same width behind one character.

</details>

**Q4.** A method's declared return type changes from `List<Restriction>` to
`Collection<Restriction>`. Explain the two different outcomes a `var`-declared caller of that
method can have, and why an explicitly `List`-typed caller can only ever have one of them.

<details><summary>Answer</summary>

A `var`-declared caller re-derives its local's type at every compile from the initializer's
current declared type. If the caller's later code used a `List`-only capability (`get(int)`,
`trimToSize()` on a concrete `ArrayList`), the re-derived `Collection<Restriction>` type drops
that capability and the caller fails to compile at exactly those lines — a loud, safe outcome.
If the caller's later code used only `Collection`-compatible operations (`stream()`, iteration),
the re-derived type still supports everything the caller does, so nothing fails to compile, and
any behavioural difference is silent. An explicitly `List<Restriction>`-typed caller only ever
gets the first outcome: the declared type is checked for assignability against the new
`Collection<Restriction>` at the declaration line itself, and if that assignment is invalid,
the caller fails loudly there regardless of what the rest of the method does with the variable.

</details>

**Q5.** Why is `var` on a try-with-resources resource variable considered close to a
default-yes, and what would make it not a default-yes?

<details><summary>Answer</summary>

Resource variables are almost always initialized by a constructor call or a clearly-named
static factory (`Files.newBufferedWriter`), which already states the type as clearly as an
explicit declaration would, satisfying G3 with essentially no exceptions. It stops being a
default-yes in the rare case where the resource is deliberately declared as a narrower
supertype than the constructor's return type — for example, typed as `Closeable` specifically to
prevent later code in the block from calling a subtype-specific method — which is the
interface-versus-implementation trap (§2.7.6) applied to a resource variable; `var` would defeat
that deliberate narrowing.

</details>

**Q6.** What is the one legitimate reason to use `var` in a lambda parameter list, and why does
the plain implicit form (`x -> ...`) already cover every other case equally well?

<details><summary>Answer</summary>

The one legitimate reason is to give a parameter annotation (such as `@NonNull`) a syntactic
place to attach — JEP 323's stated purpose. The plain implicit form gives no such slot; writing
`(@NonNull x) -> ...` does not compile. Outside that need, `var` in a lambda parameter is
target-typed identically to the implicit form (both resolve the parameter's type from the
functional interface's abstract method via target typing, not from any inference internal to the
lambda), so `(var restriction) -> ...` and `restriction -> ...` produce the exact same static
type with no readability difference — `var` here adds characters without adding information.

</details>

**Q7.** In the enhanced-`for` loop `for (var entry : restrictionsByKey.entrySet())`, what
determines `entry`'s inferred type, and does `var` change anything about `ConcurrentModificationException`
risk during the loop?

<details><summary>Answer</summary>

`entry`'s type is inferred from `restrictionsByKey.entrySet()`'s declared return type,
`Set<Map.Entry<RestrictionKey, Restriction>>`, per the JLS's enhanced-`for` element-type rule —
exactly the type an explicit declaration would have produced. `var` changes nothing about
`ConcurrentModificationException` risk: `entrySet()` still returns a live view backed by the map,
and structurally mutating the map (adding or removing keys) during iteration still throws that
exception via the same fail-fast iterator mechanism, regardless of whether the loop variable is
declared with `var` or spelled out explicitly.

</details>

**Q8.** Why does the syllabus classify `summingInt` as sharing `var total = 0;`'s exact failure
mode, and what specifically makes `averagingInt` different?

<details><summary>Answer</summary>

`Collectors.summingInt`'s accumulator, verified in `java.util.stream.Collectors` at the
jdk-21+35 tag, is a `new int[1]` holding the running sum as an `int` — the same 32-bit,
silently-wrapping width as a bare `var total = 0;` accumulator, and the identical class of
failure (proved on this machine: summing 1,000,000,000 three times gives `-1294967296` instead
of `3000000000`). `averagingInt` is different because its accumulator is a `long[2]` holding
`{sum, count}` — the sum slot is 64 bits, so the same scale of input does not overflow; only the
final division (sum / count) happens at the end, over already-safe accumulated values.

</details>

**Q9.** State the team-convention test this file argues for in one sentence, and explain why a
linter metric of "percentage of eligible locals using `var`" fails that test.

<details><summary>Answer</summary>

The test: use `var` exactly when the initializer already tells the reader the type as clearly as
writing it out explicitly would; write the type the moment that stops being true. A percentage
metric fails it because it optimizes for a count rather than for the per-declaration judgment —
a codebase can hit 100% `var` coverage on eligible locals while getting every one of
§2.7.1/§2.7.6/§2.7.7's bad cases wrong (opaque factories, width-sensitive accumulators, locals
that need interface enforcement), and the metric would still report success.

</details>

---

## Deferred

None.

---

**Leaves covered:** 2.7.1–2.7.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** D-107
**Target version:** Java 21 LTS
**Lines:** 1362
