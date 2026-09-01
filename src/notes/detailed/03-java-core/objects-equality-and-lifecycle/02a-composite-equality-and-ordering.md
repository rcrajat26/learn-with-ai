# 03 Java Core — Composite equality and ordering — INTERMEDIATE (§2.8, 2.8.9–2.8.14)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Copying and cloning](02-copying-and-composite-equality.md) · Next: [Reachability and the reference ladder](03-lifecycle-and-references.md)

## Orientation

[02](02-copying-and-composite-equality.md) covered how far a copy goes down an object graph. This file covers a different question: given two references, how does the runtime — or a data structure holding them — decide their relative order, or whether one has silently become unreachable by the very key that was used to insert it. Three disasters share one root cause: a comparison whose result changes over the lifetime of the object being compared, or whose arithmetic secretly overflows. `WithdrawalTransaction` ordering, the stranded hash key, JPA entity equality across a persistence boundary, and Lombok's generated `equals`/`hashCode` are four faces of that one problem.

## 1. Ordering: `Comparable`, `Comparator`, and the `compareTo` contract (2.8.9, 2.8.10, 2.8.11)

The mental model: a comparator is a total order the sort algorithm trusts blindly. It never re-derives the order from first principles; it asks the comparator a question at each step and assumes the answers are mutually consistent. Feed it a comparator whose answers contradict each other and it has no way to detect the contradiction except by breaking.

### Why it exists

`WithdrawalTransaction`s in a `PaymentRun` must be processed in a stable, reproducible order — by `Money` amount, then by creation timestamp for ties. `Comparable<T>` lets a type declare its own natural order (`compareTo`); `Comparator<T>` lets any number of alternative or composed orders be supplied externally without touching the type. Both exist because "less than, equal to, greater than" needs a machine-checkable contract before any sort algorithm can rely on it.

### The mechanism: never subtract

```java
final class WithdrawalTransaction {
    private final long amountMinor; // minor-unit long, e.g. pence
    private final long createdAtEpochMillis;

    WithdrawalTransaction(long amountMinor, long createdAtEpochMillis) {
        this.amountMinor = amountMinor;
        this.createdAtEpochMillis = createdAtEpochMillis;
    }

    long amountMinor() {
        return amountMinor;
    }

    long createdAtEpochMillis() {
        return createdAtEpochMillis;
    }
}

final class BrokenComparator implements Comparator<WithdrawalTransaction> {
    @Override
    public int compare(WithdrawalTransaction left, WithdrawalTransaction right) {
        return (int) (left.amountMinor() - right.amountMinor()); // TRAP
    }
}
```

Work the overflow through arithmetically. Take `a = Integer.MIN_VALUE + 1 = -2147483647` and `b = Integer.MAX_VALUE = 2147483647` as two `int`-range minor-unit amounts (the same argument applies at `long` range with `Long.MIN_VALUE`/`Long.MAX_VALUE`, which is why minor-unit withdrawal amounts stored as `long` are not automatically safe either — the trap is the operation, not the width). `a - b = -2147483647 - 2147483647 = -4294967294`. That value does not fit in a 32-bit two's-complement `int` (whose range is `-2147483648..2147483647`); it wraps by adding `2^32 = 4294967296`, giving `-4294967294 + 4294967296 = 2`. The comparator reports `2` — **positive** — meaning "`a` is greater than `b`" — while `a` is in fact the far smaller number. A comparator built on subtraction between two large-magnitude values of opposite sign silently reports the wrong direction, not an exception, not a crash — a wrong, confidently-returned answer that a sort will trust.

```java
final class CorrectComparator implements Comparator<WithdrawalTransaction> {
    @Override
    public int compare(WithdrawalTransaction left, WithdrawalTransaction right) {
        int byAmount = Long.compare(left.amountMinor(), right.amountMinor());
        if (byAmount != 0) {
            return byAmount;
        }
        return Long.compare(left.createdAtEpochMillis(), right.createdAtEpochMillis());
    }
}
```

Idiomatically the same order is built without a hand-written class at all:

```java
Comparator<WithdrawalTransaction> byAmountThenTime =
    Comparator.comparingLong(WithdrawalTransaction::amountMinor)
              .thenComparingLong(WithdrawalTransaction::createdAtEpochMillis);
```

`Integer.compare`/`Long.compare` are specified to return a value whose **sign** encodes the relationship — negative, zero, or positive — never a value whose **magnitude** encodes the size of the difference. `compareTo` and `compare` are contractually not "the amount by which a exceeds b"; treating the return value as a magnitude (summing comparator results, for instance) is a second, subtler misuse of the same API.

### Why TimSort throws on an inconsistent comparator

`Comparator.comparing(keyExtractor).thenComparing(nextKeyExtractor)` chains and hand-written comparators must satisfy a total order: antisymmetric (`compare(a,b)` and `compare(b,a)` have opposite sign or are both zero), transitive (`a < b` and `b < c` implies `a < c`), and consistent (repeated calls on the same pair give the same answer). Java's `Collections.sort`/`Arrays.sort` for objects is TimSort, a merge sort that builds and merges "runs" while relying on these three properties to know which merges are safe to skip and which invariants about run lengths must hold. `[X-REF 02]` — the merge-run bookkeeping itself, and why treeified `HashMap` buckets have nothing to do with this, belong in [`../collections/02-`](../collections/); the self-contained fact needed here is that TimSort's algorithm keeps internal invariants about the relative order of runs that a broken comparator can make simultaneously true and false, and when the internal check finds that contradiction mid-merge it throws `IllegalArgumentException: Comparison method violates its general contract!` rather than silently producing a wrong order. That exception is a bug detector doing its job, not a JDK defect — a subtraction-based comparator, or any comparator that is antisymmetric almost always but wrong at an overflow boundary, is exactly the shape of bug it exists to catch. `BrokenComparator` above will pass on small inputs and can throw this exact exception the day a withdrawal amount crosses the overflow boundary in production data.

### `compareTo`/`equals` consistency, and `BigDecimal`'s trap

The recommended-but-not-enforced rule: `x.compareTo(y) == 0` should imply `x.equals(y)`. Nothing in the language checks this, and the JDK itself ships the canonical counter-example: `BigDecimal.compareTo` ignores scale (`new BigDecimal("3.30").compareTo(new BigDecimal("3.3")) == 0`) while `BigDecimal.equals` treats scale as significant (`new BigDecimal("3.30").equals(new BigDecimal("3.3"))` is `false`, because `equals` also compares scale). The practical bite: a `TreeSet<BigDecimal>` (ordered by `compareTo`) treats `3.30` and `3.3` as duplicates and keeps only one, while a `HashSet<BigDecimal>` (keyed by `equals`/`hashCode`) keeps both — the same two values, two different collections, two different answers to "how many distinct amounts are in this set." Full treatment of `BigDecimal` scale, `stripTrailingZeros`, and money representation is [`../numbers-and-money/02-numbers-and-money.md`](../numbers-and-money/02-numbers-and-money.md).

## 2. The stranded key (2.8.12)

The failure sequence, run end to end, with the actual output:

```java
final class Restriction {
    private final String type;
    private final String source;
    private String status; // ACTIVE -> LIFTED, mutable by design

    Restriction(String type, String source, String status) {
        this.type = type;
        this.source = source;
        this.status = status;
    }

    void lift() {
        this.status = "LIFTED";
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof Restriction other)) return false;
        return type.equals(other.type) && source.equals(other.source) && status.equals(other.status);
    }

    @Override
    public int hashCode() {
        return java.util.Objects.hash(type, source, status); // status feeds the hash
    }
}

void strandedKeyDemo() {
    Map<Restriction, String> notes = new HashMap<>();
    Restriction restriction = new Restriction("STAKE_BLOCKED", "SYSTEM_ONBOARDING", "ACTIVE");
    notes.put(restriction, "auto-lifts at AA-801");

    restriction.lift(); // status becomes "LIFTED" AFTER insertion

    System.out.println(notes.containsKey(restriction)); // false
    System.out.println(notes.get(restriction));          // null
    System.out.println(notes.size());                    // 1  -- the entry is still there
    for (Restriction key : notes.keySet()) {
        System.out.println(key.equals(restriction));      // true -- same object, equals agrees now
    }
}
```

`put` computed `hashCode()` while `status == "ACTIVE"` and filed the entry in the bucket for that hash. `lift()` mutates `status` in place, on the same object, without touching the map at all — `HashMap` has no way to know a key it is holding changed. `containsKey`/`get` now recompute the hash from the **current** `status` ("LIFTED"), land in a different bucket, find nothing there, and correctly report absence — correctly, given what they were asked, even though the key object is sitting in the map at that exact moment. `size()` still reports `1` because the entry was never removed; iterating `keySet()` finds the same `Restriction` instance and — now that both sides read the current, mutated `status` — `equals()` between the iterated key and the live reference agrees. The map is neither empty (`size() == 1`) nor usable (`get` returns `null`) for that key — a state a caller reading only `containsKey`/`get` cannot distinguish from "was never inserted."

Two real fixes: make the key immutable (drop `status` from `Restriction`'s identity entirely, since — per the domain rule — restriction identity is the pair `(type, source)`, not `status`), or, if the mutable field genuinely must factor into equality for some other use, always remove-then-mutate-then-reinsert rather than mutating in place while the object is a live key. The design rule this generalizes to: a map key is a value, not an entity — model it as a `record` or a `final` class over `final` fields, so that mutating "the same restriction" after lookup is impossible by construction:

```java
record RestrictionKey(String type, String source) { } // status deliberately excluded
```

**Pitfall:** including any field that changes over an object's lifetime in `hashCode()`, then using that object as a `HashMap` or `HashSet` key across a mutation. The fix is not "remember not to mutate it" — that discipline does not survive a codebase with more than one contributor — it is to make the key type structurally incapable of holding a stranded field, by excluding mutable fields from the key's identity or by using a genuinely immutable type as the key.

## Supporting facts

### `equals`/`hashCode` on JPA entities (2.8.13)

| Strategy | What breaks |
|---|---|
| Surrogate id (`@Id Long id`) | Two transient `Account` instances (not yet persisted) both have `id == null`, so an id-based `equals` returns `false` for what are logically "the same not-yet-saved row," and a `HashSet<Account>` built before flush can hold what looks like duplicates. Worse: the *same* instance's `equals` answer against a fixed reference changes across the flush that assigns its id — an entity newly added to a `HashSet` before flush can become unreachable in that set after flush, because its hash bucket was computed from `id == null` and the id is not null anymore. |
| Business key (a natural, always-populated field — e.g. a client's unique application reference) | Works across the transient/persistent boundary because the key never changes, but only if a genuinely unique, immutable business key exists; not every entity has one. |
| Identity comparison (`getClass()` or `instanceof`) | `getClass()` fails against a Hibernate lazy proxy: a lazily-loaded `Application` fetched via a `@ManyToOne` association is not literally an `Application` instance but a Hibernate-generated proxy subclass, so `realApplication.getClass() == proxyApplication.getClass()` is `false` even though both represent the same row. `instanceof Application` (or Hibernate's own `Hibernate.getClass()`/unproxying helper) survives the proxy; `getClass()` equality does not. |

Practical recommendation: an application-assigned, immutable identifier set in the constructor (a `UUID` generated client-side rather than a database-assigned surrogate id) sidesteps both the transient/persistent inconsistency and the proxy problem, because it exists and is stable from the moment the object is constructed. Full JPA identity, proxy mechanics, and session/cache implications: `[X-REF 08]` [`../spring-data-jpa/`](../spring-data-jpa/).

The transient/persistent inconsistency above is exactly the stranded-key bug from section 2, wearing a JPA costume: the field that "mutates after insertion" is the surrogate id going from `null` to a real value at flush time, rather than a `Restriction`'s `status`.

### Lombok `@Data`/`@EqualsAndHashCode`/`@Value` (2.8.14)

`@Data` on `Application` generates `equals`/`hashCode` over **every** field by default, including a lazy-loaded `List<Restriction>` association — calling `hashCode()` on such an entity can silently trigger a database query as Hibernate initializes the lazy collection to compute the hash, an expensive and non-obvious side effect of a method callers assume is free. `@EqualsAndHashCode(callSuper = false)` is Lombok's default, which means a subclass's generated `equals`/`hashCode` silently ignores every field declared on its superclass unless `callSuper = true` is written explicitly — two subclass instances that differ only in an inherited field compare equal. `@Value` is the right tool for an intended value type like `Money`: it makes every field `final`, the class itself `final`, and generates no setters, matching immutability with the language's own enforcement. `@Data` used on `Money` instead generates ordinary setters on what is meant to be a value type, defeating the immutability the type was supposed to guarantee and reopening every aliasing hazard described in [copying and cloning](02-copying-and-composite-equality.md). Lombok is fine for a plain data holder with no lazy fields, no inheritance to preserve, and mutability that is actually intended; a record or a hand-written value class is the better answer once any of those three conditions is violated. `[X-REF 08]` — Hibernate lazy-loading mechanics and the `N+1` shape this can trigger belong in [`../spring-data-jpa/`](../spring-data-jpa/).

## Pitfalls

### Subtracting to compare

**Wrong**

```java
Comparator<WithdrawalTransaction> byAmount =
    (left, right) -> (int) (left.amountMinor() - right.amountMinor());
```

The surprise: for `left.amountMinor() = Integer.MIN_VALUE + 1` and `right.amountMinor() = Integer.MAX_VALUE`, the true difference is `-4294967294`, which does not fit in an `int` and wraps to `2` — a positive number, telling the sort that the far smaller value is larger. TimSort can detect the resulting inconsistency mid-merge on a large enough input and throw `IllegalArgumentException: Comparison method violates its general contract!`, or — worse — silently produce a wrong order on an input too small to trip the check.

**Right**

```java
Comparator<WithdrawalTransaction> byAmount =
    Comparator.comparingLong(WithdrawalTransaction::amountMinor);
```

**Why people believe it:** subtraction is how humans compare two numbers by hand, it is one character shorter to write, and it works correctly on every small test value used while writing the code, so the overflow boundary never surfaces until real data crosses it.

### `compareTo() == 0` means `equals()` agrees

**Wrong**

```java
TreeSet<BigDecimal> amounts = new TreeSet<>();
amounts.add(new BigDecimal("3.30"));
amounts.add(new BigDecimal("3.3"));
// assumed: two distinct scaled amounts, both retained
```

The surprise: `TreeSet` orders and deduplicates purely by `compareTo`, and `BigDecimal.compareTo` ignores scale, so `new BigDecimal("3.30").compareTo(new BigDecimal("3.3")) == 0` makes the set treat the second insertion as a duplicate of the first. `amounts.size()` is `1`, silently discarding a value that was never equal by `equals()` — `new BigDecimal("3.30").equals(new BigDecimal("3.3"))` is `false`, because `equals` treats scale as significant.

**Right**

```java
Set<BigDecimal> amounts = new HashSet<>();
amounts.add(new BigDecimal("3.30"));
amounts.add(new BigDecimal("3.3"));
// size() == 2 -- HashSet is keyed by equals()/hashCode(), which treat scale as significant
```

**Why people believe it:** the `Comparable` javadoc's recommendation that `compareTo` and `equals` stay consistent is stated as a strong convention, so it is natural to assume every core JDK numeric type honors it; `BigDecimal` predates that recommendation being retrofitted and keeps the inconsistency for backward compatibility.

### A `HashMap` key with a mutable field feeding `hashCode`

**Wrong**

```java
record RestrictionKey(String type, String source, String status) { }
// used as: Map<RestrictionKey, String> restrictionNotes = new HashMap<>();
```

The surprise: `status` mutating after insertion — `ACTIVE` to `LIFTED` — moves the record to a different conceptual hash bucket without moving the actual map entry, so `containsKey`/`get` on a key built with the new `status` return `false`/`null` while `size()` still counts the stale entry, and the map slowly fills with unreachable data that never gets garbage collected because the map itself still references it.

**Right**

```java
record RestrictionKey(String type, String source) { } // status excluded from identity
```

**Why people believe it:** a record's auto-generated `equals`/`hashCode` includes every component by default, so it looks safe and "designed for this"; the bug only appears once a component that should never have been part of identity gets added to the record's component list for convenience.

### `getClass()` on a JPA entity works the same as on a plain object

**Wrong**

```java
@Override
public boolean equals(Object o) {
    if (o == null || getClass() != o.getClass()) return false;
    Application other = (Application) o;
    return applicationId.equals(other.applicationId);
}
```

The surprise: comparing a managed `Application` loaded eagerly against the same row fetched through a lazy `@ManyToOne` association fails, because the lazy side is a Hibernate-generated proxy subclass and `getClass()` on it returns that generated subclass, not `Application.class` — two representations of the identical row compare unequal.

**Right**

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Application other)) return false;
    return applicationId.equals(other.applicationId);
}
```

**Why people believe it:** *Effective Java*'s "Obey the general contract when overriding equals" recommends `getClass()` over `instanceof` specifically to preserve symmetry against subclasses that add fields — correct advice for ordinary inheritance, and exactly the advice that breaks against a proxying framework the book was not written with in mind.

### Lombok `@Data` on an entity is a free, safe `equals`/`hashCode`/`toString`

**Wrong**

```java
@Data
class Application {
    private Long id;

    @OneToMany(fetch = FetchType.LAZY)
    private List<Restriction> restrictions;
}
```

The surprise: putting an `Application` into a `HashSet`, logging it (`@Data` also generates `toString`), or simply calling `hashCode()` can silently trigger Hibernate to initialize the lazy `restrictions` collection — a database query fired as a side effect of what looks like a free, in-memory method call — and if that call happens outside an open Hibernate session, it throws `LazyInitializationException` instead of merely being slow.

**Right**

```java
@EqualsAndHashCode(of = "id")
@ToString(exclude = "restrictions")
class Application {
    private Long id;

    @OneToMany(fetch = FetchType.LAZY)
    private List<Restriction> restrictions;
}
```

**Why people believe it:** Lombok's own documentation describes `@Data` as generating "the boilerplate that's normally required," and for a plain DTO with no associations that is exactly true and free; the cost only appears once a field is a lazy-loaded JPA association, a framework-specific hazard a generic code generator has no way to detect.

## Cheat sheet

| Item | Value |
|---|---|
| Comparable vs Comparator | `Comparable` = one natural order declared on the type itself; `Comparator` = external, composable, any number of orders |
| Never subtract to compare | `a - b` overflows at the `int`/`long` range boundary; use `Integer.compare`/`Long.compare` |
| `compare`/`compareTo` return | Encodes sign only, never magnitude |
| TimSort's exception | `IllegalArgumentException: Comparison method violates its general contract!` — a real bug detector |
| `compareTo`/`equals` rule | `compareTo() == 0` should imply `equals()`; `BigDecimal` violates this by design (scale) |
| `BigDecimal` in `TreeSet` vs `HashSet` | `TreeSet` dedups `3.30`/`3.3` (`compareTo == 0`); `HashSet` keeps both (`equals` is scale-sensitive) |
| Stranded key | Mutating a field that feeds `hashCode()` after insertion strands the entry: `get`/`containsKey` fail, `size()` still counts it |
| Stranded-key fix | Exclude mutable fields from key identity, or remove-mutate-reinsert |
| JPA equals options | Surrogate id (breaks pre-flush), business key (needs one to exist), `instanceof` (survives proxies; `getClass()` doesn't) |
| JPA surrogate-id trap | `id == null` before flush; the transient/persistent boundary is a stranded-key bug in disguise |
| Hibernate proxy `getClass()` | Returns the generated proxy subclass, not the entity class — breaks `getClass()`-based `equals` |
| Recommended JPA identity | Application-assigned immutable `UUID`, set in the constructor, stable from creation |
| Lombok `@Data` risk | Includes lazy associations in generated `hashCode()`/`toString()` — can trigger a query or `LazyInitializationException` |
| Lombok `callSuper` | Defaults to `false` — silently drops inherited fields from generated `equals`/`hashCode` |
| Lombok `@Value` | `final` fields, `final` class, no setters — right tool for a value type like `Money` |

## Self-test

**Q1.** Work through why `(int) (a - b)` is unsafe as a comparator body, using `a = Integer.MIN_VALUE + 1` and `b = Integer.MAX_VALUE`.

<details><summary>Answer</summary>

`a = -2147483647`, `b = 2147483647`. The mathematically true difference is `a - b = -4294967294`, which is outside the representable `int` range of `-2147483648..2147483647`. Two's-complement arithmetic wraps by adding `2^32 = 4294967296`: `-4294967294 + 4294967296 = 2`. The comparator therefore returns `2`, a positive number, asserting that `a` is greater than `b` — the opposite of the truth. The fix is `Integer.compare(a, b)`, which is specified to never overflow because it derives its sign from branching comparisons rather than from subtraction.

</details>

**Q2.** A `HashMap<Restriction, String>` is built, a key's `status` field is mutated from `"ACTIVE"` to `"LIFTED"` after insertion, and `status` feeds `hashCode()`. Walk through what `containsKey`, `get`, and `size()` each report, and why they disagree.

<details><summary>Answer</summary>

`containsKey` and `get` both recompute `hashCode()` on the current object state (`status == "LIFTED"`) to locate a bucket, land in a different bucket than the one the entry was filed under at insertion time (computed when `status == "ACTIVE"`), find nothing there, and correctly report `false`/`null` for that bucket. `size()` is a simple counter of live entries maintained independently of any hash lookup — the entry was never removed, so it still counts as `1`. The three methods disagree because `containsKey`/`get` depend on the key's *current* hash matching the bucket its entry was filed under, while `size()` depends on nothing about the key at all — it is purely a count of entries physically present in the table.

</details>

**Q3.** Give the practical recommendation for `equals()` on a JPA entity that must work correctly both before and after the entity is persisted, and explain why a plain surrogate-id-based `equals()` fails that requirement.

<details><summary>Answer</summary>

Assign an application-generated, immutable identifier — typically a client-side `UUID` — in the entity's constructor, and base `equals()`/`hashCode()` on that identifier alone. A surrogate database id (`@Id Long id`, assigned by the database on insert) is `null` on every transient (not-yet-persisted) instance, so two distinct transient entities compare equal to each other under a naive null-tolerant comparison, or unequal to everything including themselves under a strict one — and the same instance's `equals` answer against a fixed value changes the moment the flush assigns its id, which is exactly the kind of hash-relevant mutation described in Q2, now happening to an entity sitting in a `HashSet` across a transaction boundary.

</details>

**Q4.** Why does `getClass()`-based equality fail for Hibernate-managed entities specifically, when *Effective Java* recommends `getClass()` over `instanceof` in general?

<details><summary>Answer</summary>

Hibernate implements lazy loading of associations by handing back a dynamically generated proxy subclass instead of the real entity class, so that accessing the association can be intercepted and trigger the actual database fetch on first use. `realEntity.getClass()` returns the true entity class; `lazyProxy.getClass()` returns the generated proxy subclass — different `Class` objects for what is logically the same row. `getClass()`-based equality was designed to preserve symmetry against ordinary subclasses that might add fields, which is sound advice absent a framework that manufactures subclasses transparently; `instanceof` (or Hibernate's own unproxying helper) survives the proxy because it only asks "is this assignable to the entity type," which both the real instance and its proxy satisfy.

</details>

**Q5.** Explain why `new TreeSet<BigDecimal>()` and `new HashSet<BigDecimal>()`, each loaded with `new BigDecimal("3.30")` and `new BigDecimal("3.3")`, end up with different sizes.

<details><summary>Answer</summary>

`TreeSet` orders and deduplicates purely through `compareTo`, and `BigDecimal.compareTo` ignores scale — `new BigDecimal("3.30").compareTo(new BigDecimal("3.3"))` is `0`, so the second insertion is treated as a duplicate of the first and discarded; `size()` is `1`. `HashSet` deduplicates through `equals()`/`hashCode()`, and `BigDecimal.equals` treats scale as significant — `new BigDecimal("3.30").equals(new BigDecimal("3.3"))` is `false` — so both values are kept as distinct elements; `size()` is `2`. The two collections give different answers to "how many distinct amounts are here" because they consult two different, and here inconsistent, notions of equivalence on the same pair of values.

</details>

**Q6.** Why can calling `hashCode()` on a Lombok `@Data` JPA entity trigger a database query, and what is the fix?

<details><summary>Answer</summary>

`@Data` generates `hashCode()` (and `equals()`, `toString()`) over every field of the class by default, with no awareness of which fields are JPA associations. If one of those fields is a `@OneToMany` or `@ManyToOne` association marked `FetchType.LAZY`, Hibernate has deliberately left it uninitialized until first access; computing a hash that reads the field's value counts as that first access, so Hibernate transparently issues the query needed to populate it — turning what looks like a cheap, in-memory method call into a database round trip, and throwing `LazyInitializationException` outright if no Hibernate session is open at that point. The fix is to scope the generated methods explicitly — `@EqualsAndHashCode(of = "id")` and `@ToString(exclude = "restrictions")` (or the equivalent Lombok annotations) — so lazy associations are never touched by code the developer did not write by hand.

</details>

## Open questions

- None.

---

**Leaves covered:** 2.8.9, 2.8.10, 2.8.11, 2.8.12, 2.8.13, 2.8.14 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 360
