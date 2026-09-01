# 03 Java Core — Null discipline: where nulls come from and how null behaves — INTERMEDIATE (§2.11, 2.11.1, 2.11.10, 2.11.11)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The attack surface, filters and the practical rule](../serialization/02c-attack-surface-filters-and-the-practical-rule.md) · Next: [Optional and defaulting](02a-optional-and-defaulting.md)

This file owns the origin of nulls, null in collections, and the places null behaves differently
from every other reference value. `02a-optional-and-defaulting.md` owns `Optional` and the
defaulting helpers built on top of it. `02b-null-object-annotations-and-diagnosis.md` owns the
null-object pattern, nullability annotations, and reading a helpful NPE. The question this file
answers, in bold: **where does a null actually come from in Java, and which language constructs
treat it as a value rather than an error?**

## 1. The billion-dollar mistake, and where nulls legitimately come from (2.11.1)

Picture the type system's promise: a variable declared `Bonus bonus` guarantees the compiler will
only let you assign a `Bonus` to it, and every operation you call on `bonus` will resolve against
`Bonus`'s methods. `null` breaks that promise in exactly one controlled way — it is a value of the
**null type**, a type with no name you can write in source, which the JLS defines as a subtype of
every reference type. So `bonus = null` type-checks, `Bonus b = null` type-checks, and yet the
value you now hold supports none of `Bonus`'s operations. The compiler's guarantee about *type*
held; its unstated assumption that a reference always has a live object behind it did not.

Tony Hoare, who designed the null reference into ALGOL W in 1965, called it his "billion-dollar
mistake" in a 2009 retrospective — not because null is a bad *value*, but because making it silently
assignable everywhere a reference type is expected turned an occasional real absence into a
default state that has to be defended against at every dereference. Java inherited the design
wholesale: every reference-typed field, array slot, and local variable defaults to or can be
assigned null, and the compiler enforces nothing about it.

### Why it exists

Reference types need a way to represent "no object here" that fits in the same slot as "an object
is here" — a field, a array element, a collection slot. Java chose to overload the reference
itself rather than introduce a separate "absent" wrapper into the language, because in 1995 doing
otherwise would have meant either a checked-optional type discipline (which nobody had shipped at
scale in a mainstream language yet) or forcing every reference type to define its own sentinel
instance. Both are more machinery than a null bit-pattern in a reference slot.

### How it works

The useful move, once you accept null exists, is to stop treating "a null showed up" as one
problem and start asking *which* of a small, enumerable set of sources produced it — because each
source has a different fix.

| Source | Example in QuizStakes | Legitimate? | The right defence |
|---|---|---|---|
| Field default before assignment | An `Account`'s `Bonus bonus` field between `new Account(clientId, jurisdiction)` and the constructor line that sets it | Yes, transiently | Keep the window short; never publish `this` before the constructor finishes |
| Deserialization skipping the constructor | Every field of a `LedgerEntry` rebuilt by `ObjectInputStream`, including a `transient` field, which always comes back `null` regardless of what the constructor would have set — see `../serialization/02-serialization.md` and the constructor-bypass mechanism in `../serialization/02a-magic-methods-and-constructor-bypass.md` | Yes, but dangerous | Validate in `readObject`/`readResolve`, not just the constructor |
| Array element default | `new Movement[24]` is 24 nulls; `new int[3][]` is 3 null rows, not 3 empty arrays | Yes | Never index past what you have populated; prefer `Arrays.fill` or a builder over a raw `new T[n]` |
| A map lookup that missed | `restrictionsByKey.get(new RestrictionKey(STAKE_BLOCKED, ADMIN))` when no such restriction is active | Yes — the single commonest source in real code | `getOrDefault`, or check `containsKey` first, or design the return type to make absence explicit |
| A "not found" return from a repository or remote call | `documentRepository.findByAccountId(id)` returning nothing | Yes, but the encoding is wrong | This is `Optional`'s actual use case — see `02a` |
| Uninitialised or partially initialised object | A `@Autowired ClientRestrictions` field before Spring finishes wiring; a field read from a superclass constructor before the subclass field initialiser runs | Yes, transiently, and a design smell if observed | See `../classes-and-initialization/01d-class-initialization-triggers.md` for the ordering that produces this window |
| Legacy or third-party API returning null on failure | `System.getProperty("quizstakes.region")`, `Map.get`, `ClassLoader.getResource`, a JDBC `ResultSet.getObject` on a SQL `NULL` | Yes, an API contract | Wrap at the boundary; never let the raw return propagate past one frame |
| SQL `NULL` crossing the JPA boundary | A nullable `NUMERIC(19,4)` payout column mapping to a `BigDecimal` field on `WithdrawalTransaction` | Yes | Guide 08 (Spring Data JPA) and guide 09 (SQL databases) own column-nullability mapping in full |
| JSON absent vs. JSON explicit null | A `reason` field missing from a `ReviewVerdict` payload and a `reason` field present as `null` both deserialize to `null` by default — and they mean different things ("not applicable" vs. "explicitly cleared") | Yes, but ambiguous | Guide 12 (API design) owns the `JsonNullable`/presence-tracking discipline |
| An explicit sentinel someone chose | A `Verdict` field left `null` to mean "not decided yet" | **No** — the domain already has `AA-700 REVIEW_QUEUED` for exactly that state | Use the domain's own vocabulary; a typed status beats an absence |

The last row is the only illegitimate one, and it is the one worth naming out loud: every other row
is null doing its actual job — representing absence at a boundary Java does not fully control (the
database, the wire, the JDK's own libraries, deserialization). The mistake is not that null exists;
it is reaching for it as a shorthand for a domain state that already has a name.

The design conclusion follows: you can ban null from your own domain model, and it is worth doing,
but you cannot ban it at the boundaries — the database, the wire format, the framework, and the
JDK's own APIs will hand you one regardless. The escape hatch is a validated boundary layer: every
value entering the domain passes through a constructor or factory that either rejects null
immediately or converts it into a domain-meaningful value before anything downstream sees it.

```java
public final class Restriction {

    private final RestrictionKey key;
    private final Instant appliedAt;
    private final boolean reversibleByOperator;

    public Restriction(RestrictionKey key, Instant appliedAt, boolean reversibleByOperator) {
        this.key = Objects.requireNonNull(key, "key");
        this.appliedAt = Objects.requireNonNull(appliedAt, "appliedAt");
        this.reversibleByOperator = reversibleByOperator;
    }

    public RestrictionKey key() {
        return key;
    }
}

public record RestrictionKey(RestrictionType type, RestrictionSource source) {

    public RestrictionKey {
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(source, "source");
    }
}
```

Constructing `new Restriction(null, Instant.now(), true)` fails immediately with
`java.lang.NullPointerException: key`, at the exact line where the bad value was about to enter the
domain. That is a better outcome than the same null surviving four call frames and surfacing as a
bare NPE inside `ClientRestrictions.isBlocked`, with no clue which restriction was missing. This is
also why `Objects.requireNonNull` exists as a one-line idiom rather than a hand-rolled null check
that throws its own `NullPointerException` — it is the same check, but it names the exact contract
violation at the call site instead of scattering ad hoc guard clauses through the codebase.

**Insight:** a null is never a bug on its own — it becomes a bug at the *distance* between where it
was created and where it was dereferenced. Every technique in this folder — `Optional`, the
null-object pattern, `@Nullable` annotations, helpful NPE messages — is a way of shortening that
distance, either by refusing to let the null travel or by making the eventual failure point
directly back at its origin.

**Interview:** "why does null exist if it causes so many bugs" — because Java needs a way to
represent a missing reference in a slot that otherwise holds live objects, and in 1995 the
alternative (a checked-optional type baked into the language) did not exist as prior art; the fix
available today is `Optional` and validated boundaries, not eliminating null from the language.

> A null is a value of the unnamed null type, a subtype of every reference type, that represents
> the absence of an object where the type system otherwise promises one is present.

## 2. Null in collections (2.11.10)

Picture three eras of the collections framework, each with a different philosophy toward null, and
notice that the era a type comes from predicts its null behaviour better than its interface does —
`Map` alone tells you nothing; which `Map` does.

- **Era one — the 1.0 synchronized types** (`Hashtable`, `Vector`'s null-rejecting cousins): reject
  null, and not on purpose so much as incidentally, because they call `hashCode()` on the key
  before anything else.
- **Era two — the 1.2 collections framework** (`HashMap`, `ArrayList`, `LinkedList`, `TreeMap` under
  a null-tolerant comparator): permit null deliberately, as a genuine "no value here" slot.
- **Era three — the 1.5+ concurrent types and the Java 9 immutable factories**
  (`ConcurrentHashMap`, `Map.of`, `List.of`, `Set.of`): reject null deliberately, each for a stated
  reason.

### Why it exists

`HashMap` and `ArrayList` were designed to hold whatever a program legitimately produces, and a
missing value is a legitimate thing for a program to produce — a slot that has not been filled yet,
or a value that is genuinely absent. `ConcurrentHashMap` and the `of` factories were designed later,
against sharper constraints (thread-safety, value-based immutability), and null does not fit either
constraint cleanly, so both reject it outright rather than define a partial answer.

### How it works — the measured matrix

Every row below was measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64.

| Operation | Measured result |
|---|---|
| `new HashMap<>().put(null, 1)` then `.put(null, 2)` | OK. `size()==1`, `get(null)==2`, `containsKey(null)==true` — exactly one null key, second `put` replaces the first |
| `new HashMap<>().put("CLIENT_CASH_AVAILABLE", null)` | OK. `get()` returns `null`, `containsKey()` returns `true` |
| `Map.of(null, 1)` | `NullPointerException` |
| `Map.of("k", null)` | `NullPointerException` |
| `Map.copyOf(aHashMapWithANullKey)` | `NullPointerException` |
| `List.of((Object) null)` | `NullPointerException` |
| `Set.of((Object) null)` | `NullPointerException` |
| `Arrays.asList("a", null)` | OK, `size()==2` |
| `new ArrayList<>().add(null)` | OK, `size()==1` |
| `new TreeMap<String,Integer>().put(null, 1)` (natural ordering) | `NullPointerException: Cannot invoke "java.lang.Comparable.compareTo(Object)" because "k1" is null` |
| `new ConcurrentHashMap<>().put(null, 1)` | `NullPointerException` |
| `new ConcurrentHashMap<>().put("k", null)` | `NullPointerException` |
| `new Hashtable<>().put(null, 1)` | `NullPointerException: Cannot invoke "Object.hashCode()" because "key" is null` |
| `Collections.unmodifiableMap(mapWithNullKey).get(null)` | OK, returned `1` — the wrapper adds no null check |
| `Arrays.asList("a", null).stream().toList()` | OK, `size()==2` — `Stream.toList()` permits nulls |
| `Arrays.asList("a", null).stream().collect(Collectors.toList())` | OK, `size()==2` |
| `Stream.of("a").collect(Collectors.toMap(s -> s, s -> null))` | `NullPointerException` |
| `Optional.of(null)` | `NullPointerException` |
| `Optional.ofNullable(null).isEmpty()` | OK, `true` |
| `mapWithNullValue.getOrDefault("k", "dflt")`, key present with null value | returned **`null`**, not `"dflt"` |
| `Objects.requireNonNull(null, "clientId")` | `NullPointerException: clientId` |
| `Objects.requireNonNullElse(null, "AA-801")` | returned `"AA-801"` |
| `Objects.equals(null, null)` | `true` |

The matrix is memorisable once you have the three reasons behind it:

- **`HashMap` permits one null key** because `hash(null)` is defined as `0`, and the key comparison
  short-circuits on reference equality (`key == null`) before ever calling `equals`. It permits any
  number of null values because the map already exposes `containsKey` to disambiguate "absent" from
  "present but null".
- **`ConcurrentHashMap` rejects both, and this is the strongest interview answer of the two:** in a
  map another thread can mutate concurrently, `get(k)` returning `null` is genuinely ambiguous
  between "no such key" and "key present, value null" — and unlike `HashMap`, you cannot resolve
  the ambiguity with a follow-up `containsKey(k)` call, because the map may have changed between the
  two calls. That is a correctness argument, not a style preference, and Doug Lea's Javadoc for
  `ConcurrentHashMap` states it in exactly those terms.
- **`Map.of`, `List.of`, `Set.of` reject null** because they are value-based, `equals`/`hashCode`
  driven immutable factories, free to choose an internal layout (a flat array, a specialised
  single-entry object) without a null-handling branch. The same construction rejects **duplicate
  keys** at call time — a related surprise from the same "no ambiguity, no compromise" design.

```java
Map<String, Integer> restrictionCounts = new HashMap<>();
restrictionCounts.put("STAKE_BLOCKED", null);
restrictionCounts.getOrDefault("STAKE_BLOCKED", 0);   // returns null, NOT 0
restrictionCounts.getOrDefault("WITHDRAWAL_BLOCKED", 0); // returns 0 — key genuinely absent
```

**Pitfall:** `getOrDefault` reads like "give me the default when there's nothing useful here", but
its contract is "default if the key is *absent*" — a key present with a `null` value is not
absence, and measured behaviour confirms it: `getOrDefault` returns the stored `null`, not the
default. Fix: either never store `null` as a value in a map you will call `getOrDefault` against, or
check `containsKey` explicitly when a stored null is possible.

**Pitfall:** `Collections.unmodifiableMap(mapWithNullKey)` is a *view*, not an immutable collection
— it forwards every read straight to the backing `HashMap`, including the null-key lookup that
returned `1` in the measurement above. Mistaking "returns an unmodifiable view" for "returns an
immutable collection" is exactly where the null-rejection contract of `Map.of` gets assumed
incorrectly onto a wrapped `HashMap` that never had it.

Two more shapes worth carrying into an interview: `Stream.toList()` (Java 16+) permits nulls in the
resulting list, matching `Arrays.asList`'s tolerance, while `Collectors.toMap` throws the moment a
`null` value would be inserted — the two "collect to a collection" idioms do not agree with each
other. And `TreeMap`'s null-key NPE is not the map's own check; it comes from `compareTo` being
invoked on the null key during the tree insert. A `TreeMap` constructed with an explicit
null-tolerant `Comparator` (one that special-cases `null` before calling `compareTo`) behaves
differently from the natural-ordering default — a sorted collection's null behaviour is its
comparator's null behaviour, not a fixed property of `TreeMap`.

The operational rule, in QuizStakes' own numbers: `ClientRestrictions` looks up restrictions by the
`(type, source)` key across 2.4M registered clients, and for the overwhelming majority of lookups
the client has no matching restriction — a miss is the normal case, not the exceptional one. The
map returning `null` for an absent key is the API working correctly, not a defect to guard against
with a null check at every call site; the discipline is `getOrDefault(key, Restriction.NONE)` or
returning an empty collection from the lookup method, decided once at the API boundary rather than
re-litigated at each call.

`[X-REF 02]` — this is a self-contained answer to the collections-and-null interview question, but
guide 02 (Java collections) owns the full internals behind it: `HashMap`'s bucket-0 treatment of
the null key, and `ConcurrentHashMap`'s striped-lock/CAS internals that make the ambiguity above a
genuine concurrency hazard rather than a theoretical one.

**Interview:** "why does `ConcurrentHashMap` reject null but `HashMap` doesn't" — because `get`
returning `null` in a concurrent map cannot be disambiguated from absence with a follow-up call (the
map can change between calls), while a single-threaded `HashMap` can always be disambiguated with
`containsKey` taken in the same breath.

> Collections split by era, not by interface: the 1.0 synchronized types reject null incidentally,
> the 1.2 framework permits it deliberately, and the 1.5+ concurrent and immutable-factory types
> reject it deliberately for stated correctness or design reasons.

## 3. Null and `switch`, `equals`, `==`, string concatenation, and autoboxing (2.11.11)

Picture null as a reference that supports no operations at all — except in a short, memorisable
list of places where the language or a library method deliberately handles it as data. Getting the
list right, rather than guessing per-construct, is the difference between a confident interview
answer and a coin flip.

### Why it exists

Each of these constructs was specified independently, at different times, with different
priorities: `switch` predates pattern matching by two decades and inherited a null-throws rule from
its `hashCode`-based desugaring; `equals` is asymmetric by contract, not by accident; `==` is
defined at the bit level and null has always fit it cleanly; `+` on strings was specified from day
one to treat null as printable text; autoboxing is a compiler-inserted method call with no visual
trace in the source. None of them coordinate with each other, which is exactly why the matrix has
to be memorised as a table, not derived from a single rule.

### How it works

| Construct | Behaviour with null | Why | Measured evidence |
|---|---|---|---|
| Classic `switch` on `String`/enum | Throws | Desugars to a `hashCode()`/`ordinal()` lookup, which is called before any case is compared | `NullPointerException: Cannot invoke "String.hashCode()" because "<local1>" is null` |
| Pattern `switch`, `case null` present | Matches the `case null` arm | Final, no-flag language feature on JDK 21; preview-only (`--enable-preview`) on JDK 17; does not compile at all on JDK 11 | `switch (nullString) { case null -> "matched null"; case "AA-801" -> "activated"; default -> "other"; }` returned `"matched null"` on JDK 21.0.7 with no flags |
| Pattern `switch`, no `case null`, `default` present | Throws — `default` does not catch null | Backward compatibility: switch has always thrown on null; pattern switch preserves that unless you opt in | `switch (nullObject) { case String s -> "str"; default -> "def"; }` threw `NullPointerException` |
| `x.equals(y)` where `x` is null | Throws | `equals` is an instance method; there is no receiver to dispatch on | `nullString.equals("x")` → `NullPointerException: Cannot invoke "String.equals(Object)" because "<local0>" is null` |
| `x.equals(y)` where `y` is null, `x` non-null | Returns `false` | The `equals` contract requires `x.equals(null)` to be `false` for any non-null `x` | `"x".equals(nullString)` → `false` |
| `Objects.equals(a, b)`, both null | Returns `true` | `Objects.equals` null-checks both sides before delegating | `Objects.equals(null, null)` → `true` |
| `x == null` | Never throws | `==` on references compares bit patterns; null is a valid bit pattern | Language guarantee, JLS 15.21 |
| `x instanceof T` where `x` is null | Always `false` | `instanceof` is specified to return `false` for a null operand regardless of `T` | Language guarantee, JLS 15.20.2 |
| `"AA-" + nullString` | `"AA-null"`, no exception | `+` on a `String` operand converts a null operand via `String.valueOf` | Measured, no exception |
| `String.valueOf((Object) null)` | `"null"` | The `Object` overload explicitly handles null | Measured |
| `String.valueOf((char[]) null)` | Throws | Overload resolution picks the more specific `char[]` overload, which reads the array's length | `NullPointerException: Cannot read the array length because "value" is null` |
| `Integer i = null; int j = i;` | Throws | Compiler inserts `i.intValue()` for the unboxing conversion | `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<local0>" is null` |

**`switch`.** The classic statement form's NPE message names `String.hashCode()` because a
`String`-typed switch desugars to a hash lookup followed by `equals` confirmation on the matching
bucket — the null blows up before any `case` label is even examined. `../control-flow/01b-string-and-enum-switch.md`
owns that desugaring in full, and `../control-flow/01c-switch-expressions-and-patterns.md` owns
switch expressions. Java 21's `case null` is the *only* way to handle a null selector in a switch —
the fact people get wrong is that a pattern switch's `default` label looks like it should be a
catch-all but is not; a null selector with no explicit `case null` throws regardless of how many
`default` or type-pattern arms exist. The combined form `case null, default ->` handles both in one
arm when the intent really is "null or unmatched, same treatment." Version trap, measured directly
across three JDKs (Oracle 21.0.7, 17.0.15, 11.0.27, macOS aarch64) by compiling and running
`switch (s) { case null -> "matched null"; case "AA-801" -> "activated"; default -> "other"; }`
with `s` a null `String`: on 21.0.7 with no flags it compiles and prints `matched null`; on 17.0.15
with no flags it fails to compile with `error: null in switch cases is a preview feature and is
disabled by default. (use --enable-preview to enable null in switch cases)`, and compiles and prints
`matched null` only when invoked with `--enable-preview --source 17`; JDK 11.0.27 has no pattern
switch at all, so the construct does not compile there under any flag. So `case null` is a preview
feature in Java 17 and a final, no-flag feature in Java 21. It was finalized as part of pattern
matching for switch; **Unverified:** the exact JEP number for that finalization (commonly cited as
JEP 441) could not be confirmed against the JEP text in this session.

**`equals`.** The asymmetry — `x.equals(y)` throws on null `x` but returns `false` on null `y` — is
the entire reason for the Yoda-comparison idiom `"x".equals(nullString)` over
`nullString.equals("x")` when one side is a literal or a known-non-null value. `Objects.equals(a,
b)` exists precisely to remove the asymmetry when neither side is guaranteed non-null; it is the
correct general-purpose tool, and its `(null, null) → true` result is exactly why the `equals`
contract is worded "for any non-null reference value x" — the contract deliberately says nothing
about what `x.equals(null)` does when `x` itself might be null, because that call is undefined
behaviour (an NPE), not a contract violation. `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`
owns the full `equals`/`hashCode` contract; this file only covers the null half.

**`==`.** The one construct where null is completely well-behaved: `null == null` is `true`, `x ==
null` never throws regardless of what `x` is, and `instanceof` on a null operand is always `false`.
That last fact is the reason `x instanceof Money m` is a safe, single-step null-and-type check —
no separate null guard needed — while `x.getClass() == other.getClass()` is not, because
`getClass()` on a null `x` throws before the comparison ever runs.

**String concatenation.** `"AA-" + nullString` never throws, because JLS 15.18.1 specifies that a
null operand of `+` is converted to the four characters `null` via `String.valueOf`. But
`String.valueOf` itself is not unambiguous the moment you write a bare `null` literal into it:
`String.valueOf((Object) null)` returns `"null"`, while `String.valueOf((char[]) null)` throws with
`Cannot read the array length because "value" is null`. That is not a null-handling inconsistency
in the method — it is overload resolution, decided at compile time. `javac` picks the most specific
applicable overload for the *static type* of the argument, and `char[]` is more specific than
`Object`; a caller writing `String.valueOf(null)` with no cast gets the `char[]` overload and an
NPE, not the friendly `"null"` string. `../inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md`
owns overload resolution in full.

```java
Object clientIdOrNull = null;
String logLine = "clientId=" + clientIdOrNull;   // "clientId=null" — no exception, ever
```

**Pitfall:** because `+` on a `String` operand never throws on a null operand, string-concatenating
a possibly-null value into a log message silently produces `"clientId=null"` in production instead
of failing at the point where the null was actually created. The failure that should have
surfaced four frames earlier — where the client ID was first lost — never happens; the log line just
looks slightly wrong. Guide 20 (Observability) owns the `{}`-placeholder discipline (structured
logging that preserves the null as a typed field rather than folding it into text) as the fix.

**Autoboxing.** `Integer i = null; int j = i;` throws with a message naming `Integer.intValue()`,
and there is no method call visible anywhere in that line of source — the compiler inserted it as
part of the unboxing conversion required to assign an `Integer` to an `int`. This is the
single most commonly asked null trap in interviews specifically because the stack trace points at a
line with no apparent method invocation, and the correct one-line answer is that the compiler, not
the runtime, put the call there.

The conditional operator interacts with this in a way that is widely misremembered. Folklore says
`flag ? 1 : nullInteger` throws even when `flag` is `true`. Measured on JDK 21, with `Integer n =
null` and `boolean f = true`, that is false:

| Expression | Result |
|---|---|
| `int r = f ? 1 : n;` | OK, `r == 1` — no exception |
| `int r = f ? n : 1;` | `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<local1>" is null` |
| `Integer r = f ? 1 : n;` | OK, `r == 1` |
| `Object o = f ? 1 : n;` | OK, `o == 1` |
| `Integer r = f ? n : 1;` | `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<local1>" is null` |
| `Long r = f ? null : 0L;` | OK, `r == null` |
| `long r = f ? null : 0L;` | `NullPointerException: Cannot invoke "java.lang.Long.longValue()"` |

The bytecode explains the asymmetry directly. `javac` on JDK 21 for these two methods:

```java
static int c(boolean f, Integer n) { Integer r = f ? 1 : n; return r; }
static int b(boolean f, Integer n) { int r = f ? n : 1; return r; }
```

produced, verbatim:

```
  static int c(boolean, java.lang.Integer);
    Code:
       0: iload_0
       1: ifeq          8
       4: iconst_1
       5: goto          12
       8: aload_1
       9: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
      12: invokestatic  #13                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
      15: astore_2
      16: aload_2
      17: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
      20: ireturn

  static int b(boolean, java.lang.Integer);
    Code:
       0: iload_0
       1: ifeq          11
       4: aload_1
       5: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
       8: goto          12
      11: iconst_1
      12: istore_2
      13: iload_2
      14: ireturn
```

Read `c` instruction by instruction: `iload_0`/`ifeq` tests `f`; if false, jump to offset 8, load
`n` (`aload_1`), and unbox it (`invokevirtual Integer.intValue`, offset 9); if true, fall through to
`iconst_1` and skip the unbox entirely. The unboxing instruction sits *inside* the reference
branch, not before the branch — it fires only when that branch is taken. In `c`, `f` is `true`, so
control never reaches offset 9 and nothing unboxes. In `b`, the reference branch (`aload_1` at
offset 4) is the one taken when `f` is `true`, so its unbox at offset 5 fires and throws.

The load-bearing fact: binary numeric promotion makes the conditional expression's *type* `int` in
both methods (because one arm is `int`-typed after promotion), so `javac` must produce an `int` on
every path — and the only way to do that from an `Integer` arm is to unbox it, but only on the
branch where that arm is actually selected. Also note the reboxing at offset 12 in `c`
(`Integer.valueOf`) — the *variable* `r` is declared `Integer`, so after computing the primitive
`int` result the compiler boxes it right back, a box-then-unbox round trip through the constant pool
that costs an allocation outside the `Integer` cache range (outside −128..127).

State the corrected rule plainly: the conditional operator's result type is computed from *both*
operands together and can come out primitive even when one operand is a boxed reference type; the
reference operand is then unboxed only if and when that branch is the one selected at runtime. It
does not throw simply because a reference-typed null sits in one arm of a ternary — it throws only
when execution actually takes that arm. `../primitives-and-conversions/02c-conditional-operator.md`
owns the full typing rules for `?:`; this file only owns the null half of the interaction.
`../primitives-and-conversions/03a-promotion-boxing-and-inference.md` owns promotion and boxing
conversions generally, and `../wrappers-and-boxing/01-basics.md` covers boxing itself, referenced by
path only — nothing here depends on it for a load-bearing claim.

Finally, every message quoted in this file exists because helpful NPE messages are on by default.
`java -XX:+PrintFlagsFinal -version` on this JDK printed, verbatim:

```
     bool ShowCodeDetailsInExceptionMessages       = true                                   {manageable} {default}
```

With `-XX:-ShowCodeDetailsInExceptionMessages`, every `getMessage()` quoted above returned `null`
instead of the descriptive text. The flag is `{manageable}`, meaning it can be flipped at runtime
without a restart. Version trap, measured directly with `java -XX:+PrintFlagsFinal -version` across
three JDKs on macOS aarch64: Oracle JDK 21.0.7 and Oracle JDK 17.0.15 both print the identical line
`bool ShowCodeDetailsInExceptionMessages       = true                                   {manageable} {default}`, while on Oracle JDK
11.0.27 the flag does not exist at all — grepping for it returns nothing. So helpful NPE messages
are on by default on every LTS from 17 onward, and the flag itself is absent entirely in 11.
**Unverified:** the commonly cited detail that JEP 358 delivered the mechanism in JDK 14 disabled by
default and JDK-8233014 enabled it by default in JDK 15 — narrowing the boundary to exactly Java
15 rather than "17 or earlier" — could not be confirmed against the JEP or bug-tracker text in this
session. Material and habits from Java 11 or any JVM run with the flag explicitly disabled will only
ever see a bare `NullPointerException` with a `null` message.
`02b-null-object-annotations-and-diagnosis.md` owns reading these messages in full detail.

**Interview:** "why doesn't `default` catch a null selector in a pattern switch" — backward
compatibility: switch has thrown on a null selector since Java 1.0, and pattern matching for switch
preserves that unless the developer opts in explicitly with `case null`.

**Interview:** "why write `"x".equals(y)` instead of `y.equals("x")`" — because `equals` throws when
the receiver is null but returns `false` when the argument is null; putting the known-non-null value
as the receiver avoids the throw entirely.

**Interview:** "how can an NPE be thrown on a line with no method call in the source" — autoboxing
and unboxing insert `valueOf`/`intValue`-style calls at compile time; the stack trace names the
inserted call, not anything visible in the source line.

> Null behaves as an ordinary value only where the JLS or a library method explicitly says so —
> `==`, `instanceof`, string concatenation via `+`, `case null` in a pattern switch, and the false
> side of `equals`'s asymmetry — and throws everywhere else a method would be dispatched on it.

---

## Pitfalls

### `getOrDefault` returns the default whenever the value "looks empty"

**Wrong**

```java
Map<String, Integer> restrictionCounts = new HashMap<>();
restrictionCounts.put("STAKE_BLOCKED", null);
int count = restrictionCounts.getOrDefault("STAKE_BLOCKED", 0);
// count is null, not 0 — this line throws NullPointerException on unboxing to int
```

**Right**

```java
Map<String, Integer> restrictionCounts = new HashMap<>();
restrictionCounts.put("STAKE_BLOCKED", null);
Integer stored = restrictionCounts.get("STAKE_BLOCKED");
int count = (stored != null) ? stored : 0;
// or: never store null values in a map you intend to call getOrDefault against
```

**Why people believe it:** the method's name reads as "give me a sensible value regardless of what's
in the map", but its actual contract is "default only if the key is absent" — a stored `null` is a
present value, not an absent key, and `getOrDefault` was measured to return it unchanged.

### `Collections.unmodifiableMap` gives you the same null-rejection as `Map.of`

**Wrong**

```java
Map<String, Integer> mutable = new HashMap<>();
mutable.put(null, 1);
Map<String, Integer> wrapped = Collections.unmodifiableMap(mutable);
wrapped.get(null);
// returns 1 — no exception, because unmodifiableMap adds no null check at all
```

**Right**

```java
Map<String, Integer> mutable = new HashMap<>();
mutable.put("STAKE_BLOCKED", 1);
Map<String, Integer> immutable = Map.copyOf(mutable);
// Map.copyOf rejects a null key or value at copy time with NullPointerException,
// giving the actual Map.of-style immutability contract
```

**Why people believe it:** "unmodifiable" and "immutable" sound like synonyms, and both `Collections
.unmodifiableMap` and `Map.of` prevent structural mutation through the returned reference — but only
`Map.of`/`Map.copyOf` also reject null at construction; `unmodifiableMap` is a thin view over
whatever the backing map already allows.

### The conditional operator always unboxes a null wrapper operand, regardless of which branch is taken

**Wrong**

```java
Integer bonusOverrideOrNull = null;
boolean useOverride = false;
int effectiveBonus = useOverride ? bonusOverrideOrNull : 0;
// This is believed to throw because bonusOverrideOrNull is null — it does not.
```

**Right**

```java
Integer bonusOverrideOrNull = null;
boolean useOverride = false;
int effectiveBonus = useOverride ? bonusOverrideOrNull : 0;
// useOverride is false, so the int-typed branch (0) is selected; bonusOverrideOrNull
// is never unboxed and effectiveBonus == 0, with no exception.
// Only "useOverride ? 0 : bonusOverrideOrNull" with useOverride == false would throw,
// because then the null reference branch is the one actually taken.
```

**Why people believe it:** the folklore version of this trap says the ternary throws "because one
side is null", which sounds like a static, type-level fact — but the measured behaviour and the
`javap -c` output both show the unboxing instruction lives inside the branch, so it only executes
when that specific branch is selected at runtime.

### `default` in a pattern `switch` is a catch-all, including for null

**Wrong**

```java
Object value = null;
String label = switch (value) {
    case String s -> "string";
    case Integer i -> "integer";
    default -> "other";
};
// Believed to print "other" for a null value — instead this throws NullPointerException
```

**Right**

```java
Object value = null;
String label = switch (value) {
    case null -> "null";
    case String s -> "string";
    case Integer i -> "integer";
    default -> "other";
};
// or, combined: "case null, default -> "other";" if null and unmatched share treatment
```

**Why people believe it:** every other exhaustiveness mechanism in Java treats `default` as "match
everything not already listed", and null looks like it should count as "not already listed" —  but
switch has thrown on a null selector since Java 1.0, and Java 21's pattern switch preserves that
unless `case null` opts in explicitly.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `HashMap` null key | One allowed; `hash(null) == 0`; second `put` replaces the first |
| `HashMap` null value | Any number allowed; disambiguate absence vs. null value with `containsKey` |
| `Map.of` / `List.of` / `Set.of` | Reject null key or value with `NullPointerException`; also reject duplicate keys |
| `TreeMap` natural ordering, null key | Throws — `compareTo` invoked on the null key |
| `ConcurrentHashMap` | Rejects null key and null value; correctness reason, not style |
| `Hashtable` null key | Throws — `hashCode()` invoked on the null key |
| `Collections.unmodifiableMap` | View only; does not add null rejection |
| `Stream.toList()` | Permits null elements |
| `Collectors.toMap` | Throws on a null value produced by the value mapper |
| `getOrDefault(k, dflt)` | Returns stored `null` if key present with null value; does not substitute `dflt` |
| Classic `switch` on `String`/enum, null selector | Throws — desugars to `hashCode()`/`ordinal()` |
| Pattern `switch`, `case null` present | Matches it explicitly; final no-flag on JDK 21, preview-only on JDK 17, absent on JDK 11 |
| Pattern `switch`, `default` only, no `case null` | Throws — `default` does not catch null |
| `x.equals(y)`, `x` null | Throws |
| `x.equals(y)`, `y` null, `x` non-null | `false` |
| `Objects.equals(null, null)` | `true` |
| `x == null`, `x instanceof T` on null | Never throw; `instanceof` on null is always `false` |
| `"str" + nullRef` | `"strnull"` — never throws |
| `String.valueOf((Object) null)` | `"null"` |
| `String.valueOf((char[]) null)` | Throws — overload resolution picks `char[]` |
| `Integer i = null; int j = i;` | Throws — compiler-inserted `intValue()` call |
| `flag ? primitiveArm : wrapperArm` | Unboxes only the branch actually taken, not both |
| Helpful NPE messages | On by default on JDK 17 and 21; flag absent entirely on JDK 11; flag name `ShowCodeDetailsInExceptionMessages`, `{manageable}` |

## Self-test

**Q1.** Why does `new HashMap<>().put(null, 1)` succeed while `new ConcurrentHashMap<>().put(null,
1)` throws, given that both implement `Map`?

<details><summary>Answer</summary>

`HashMap` defines `hash(null)` as `0` and short-circuits the key comparison with `==` before
calling `equals`, so a single null key fits cleanly into its bucket-0 slot; any ambiguity between
"absent" and "present with null" is resolvable with a same-thread follow-up `containsKey` call.
`ConcurrentHashMap` rejects null because in a map that other threads can mutate concurrently, `get`
returning `null` is genuinely ambiguous between those two states, and a follow-up `containsKey` call
cannot resolve it reliably — the map may have changed in between. This is a correctness argument
specific to concurrent access, not a stylistic difference between the two classes.

</details>

**Q2.** A `ClientRestrictions` lookup stores a restriction count as `Integer`, and one entry has a
`null` value meaning "count not yet computed." A caller writes
`restrictions.getOrDefault(key, 0)` expecting `0` when the count is not yet computed. What actually
happens, and why?

<details><summary>Answer</summary>

It returns the stored `null`, not `0`. `getOrDefault`'s contract triggers the default only when the
key is absent from the map; a key present with a `null` value is not absence, so the method returns
what is stored. If the returned `null` is then auto-unboxed into an `int`, this throws a
`NullPointerException`. The fix is either to never store `null` as a "not yet computed" sentinel
value in that map, or to check the retrieved value for `null` explicitly before using it as a
primitive.

</details>

**Q3.** Why does a pattern `switch` with a `default` arm still throw `NullPointerException` on a
null selector, even though `default` is meant to be a catch-all?

<details><summary>Answer</summary>

Switch has thrown on a null selector since Java 1.0, when there was no pattern matching and no
`case null` — the classic `String`/enum switch throws because it invokes `hashCode()`/`ordinal()` on
the selector before comparing any case. Java 21's pattern switch (finalized as a no-flag language
feature; the same `case null` construct only compiles on JDK 17 under `--enable-preview`) preserves
that historical behavior for backward compatibility: `default` still only matches non-null values
that fell through every type pattern; null selectors require the explicit `case null` label, or the
combined `case null, default ->` form, to be handled without throwing.

</details>

**Q4.** Explain, using the `javap -c` output, why `Integer r = flag ? 1 : nullInteger;` does not
throw when `flag` is `true`, but `int r = flag ? nullInteger : 1;` does throw when `flag` is `true`.

<details><summary>Answer</summary>

In both methods, binary numeric promotion makes the ternary's computed type `int`, so `javac` must
produce an `int`-typed value regardless of which arm is chosen — which means the `Integer`-typed
arm must be unboxed via `Integer.intValue()`, but that unbox instruction is emitted *inside* that
arm's branch, not before the branch selection. In the first method, when `flag` is `true`, control
takes the `iconst_1` branch and never reaches the `intValue()` call on `nullInteger`, so nothing
unboxes and no exception is thrown. In the second method, when `flag` is `true`, control takes the
branch that loads `nullInteger` and immediately invokes `intValue()` on it, which throws because the
reference is null. The general rule: the reference operand's unboxing only fires on the branch
actually selected at runtime, not unconditionally at the ternary's evaluation.

</details>

**Q5.** A log statement writes `"clientId=" + clientId` where `clientId` might be `null`. What
happens at runtime, and why is this a reliability problem rather than a safe fallback?

<details><summary>Answer</summary>

Nothing throws. JLS 15.18.1 specifies that `+` on a `String` operand converts a null operand to the
four characters `null` via `String.valueOf`, so the log line becomes `"clientId=null"`. This is a
reliability problem because the null concatenation absorbs the failure silently at the exact point
where the missing client ID could have been caught and reported with full context — instead the
program continues with a corrupted or missing identifier, and the eventual failure (if any) surfaces
far from its true cause. The fix is structured logging with typed placeholders that preserve the
null as data rather than folding it into text, as guide 20 (Observability) covers.

</details>

**Q6.** Why does `String.valueOf(null)` (no cast) throw `NullPointerException`, while
`String.valueOf((Object) null)` returns the string `"null"`?

<details><summary>Answer</summary>

`String.valueOf` is overloaded, including a `String.valueOf(Object)` overload that returns `"null"`
for a null argument, and a `String.valueOf(char[])` overload that reads the array's length and
throws on a null argument. Overload resolution happens at compile time based on the static type of
the argument expression; a bare `null` literal with no cast resolves to the most specific applicable
overload, which is `char[]`, not `Object`. So the NPE is a consequence of overload resolution
picking the array overload, not of `String.valueOf` mishandling null in general — casting to
`(Object)` forces the other overload and avoids the exception.

</details>

**Q7.** List three legitimate sources of null in a Java program and one illegitimate one, and state
the fix for the illegitimate case.

<details><summary>Answer</summary>

Legitimate: a map lookup that missed a key (e.g. `restrictionsByKey.get(key)` for a client with no
matching restriction), an array element that has not yet been populated (`new Movement[24]`
defaults every slot to null), and a legacy JDK API signalling failure by returning null
(`System.getProperty`, `ClassLoader.getResource`). Illegitimate: choosing null as a sentinel for a
domain state that already has a name, such as a `Verdict` field left null to mean "not decided yet"
when the domain defines `AA-700 REVIEW_QUEUED` for exactly that. The fix is to use the domain's own
typed status instead of overloading null as an implicit fourth state.

</details>

**Q8.** Why does `"x".equals(possiblyNull)` never throw, but `possiblyNull.equals("x")` can throw?

<details><summary>Answer</summary>

`equals` is an instance method dispatched on its receiver; if the receiver reference is null there
is no object to dispatch the call on, so `possiblyNull.equals("x")` throws `NullPointerException`
before any comparison logic runs. When the argument, not the receiver, is null — as in
`"x".equals(possiblyNull)` — the `equals` contract requires the method to return `false` for a null
argument rather than throw, because the contract states `x.equals(null)` must be `false` for any
non-null `x`. Putting the known-non-null value as the receiver (the Yoda-comparison idiom) exploits
this asymmetry to avoid the throwing path entirely.

</details>

## Open questions

None. The `case null` version boundary (preview on JDK 17, final no-flag on JDK 21, absent on JDK
11) and the helpful-NPE-message version boundary (flag absent on JDK 11, on by default on JDK 17
and 21) are both settled by direct measurement across three JDKs, cited inline where each claim
appears. The exact JEP numbers commonly associated with those changes (JEP 441, JEP 358,
JDK-8233014) remain individually unconfirmed against primary source text and are marked
`**Unverified:**` inline at the point each is named, rather than left as an open question.

---

**Leaves covered:** 2.11.1, 2.11.10, 2.11.11 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 734
