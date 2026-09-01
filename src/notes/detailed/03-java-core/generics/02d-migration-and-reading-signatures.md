# 03 Java Core — Migration compatibility, `Optional` placement, and reading a hard signature — INTERMEDIATE (§2.7, 2.7.16–2.7.18)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Type inference and the limits of generics](02c-inference-and-generic-limits.md) · Next: [What erasure emits](03-internals-erasure.md)

This file closes the Intermediate generics tier with three leaves that are really one argument: the shape of Java generics is a historical artifact, not an accident, and once you accept that, every JDK signature stops looking arbitrary. It covers why raw types still compile and what that migration guarantee still costs you today (2.7.16), the three-part placement rule for `Optional<T>` and why each prohibition exists (2.7.17), and a full end-to-end read of a genuinely hard generic method signature, `Collectors.toMap` with four type parameters and a bounded return type (2.7.18). It hands off erasure's mechanics to `01a-erasure-and-its-consequences.md`, wildcard theory to `01b-variance-and-wildcards.md`, raw-type behaviour to `01c-raw-types-and-unchecked-warnings.md`, PECS-on-real-signatures to `02-in-anger.md`, and the "why erasure at all" counterfactual to `03e-internals-why-erasure-and-super-type-tokens.md` — this file only explains the *consequence*, never re-derives those arguments.

## 1. Migration compatibility: why raw types still compile, and the bill Java still pays (2.7.16)

Picture Java in 2004. There is a decade of deployed `.class` files, a collections library that half the industry's code already imports, and a language team that wants generics without forcing every one of those files to be recompiled before it can run on the new JVM. Erasure plus raw types is the answer to that constraint, not an aesthetic choice — and once you see the constraint, most of the language's ugliest generics rules stop looking like oversights and start looking like the price tag on a promise that was kept.

### Why it exists

Before Java 5, `java.util.List` had no type parameter. `List` held `Object`, and every read came out through a manual cast: `String s = (String) list.get(0);`. That was every collection in every shipped `.jar`, every compiled application server, every third-party library nobody was going to recompile on request. When generics arrived, the language designers had one non-negotiable constraint: a `.class` file compiled against pre-generics `List` in 1.4 has to keep working, unmodified, forever, calling into and being called by code compiled against the *generic* `List<E>` in every later release. That is **binary compatibility** as JLS 13 defines it — the guarantee that separately compiled units keep linking without recompilation — and it is a stronger promise than *source* compatibility (old source still compiles) or behavioural compatibility. Generics had to slot into that promise without breaking it, and the collections API specifically could not get a parallel "generic edition" living alongside the old one, because that would have split every API in the platform in two.

### The mechanism

Erasure delivers the guarantee directly: a generic type erases to *exactly* the descriptor its pre-generic ancestor had. `List<E>` erases to `List` erases to `Object`-typed elements at the descriptor level, which is bit-for-bit the same signature `java.util.List` had in 1.4. `**[PROVE]**` Here it is, worked through rather than asserted. Compile one caller against a raw `List` and one against `List<String>`, holding the called method identical:

```java
// RawCaller.java
static int sizeRaw(java.util.List l) { return l.size(); }

// GenCaller.java
static int sizeGen(java.util.List<String> l) { return l.size(); }
```

`javac` (JDK 21.0.7, no flags beyond the defaults) then `javap -p -c -v` on both:

```
static int sizeRaw(java.util.List);
  descriptor: (Ljava/util/List;)I
  Code:
     0: aload_0
     1: invokeinterface #7,  1   // InterfaceMethod java/util/List.size:()I
     6: ireturn

static int sizeGen(java.util.List<java.lang.String>);
  descriptor: (Ljava/util/List;)I
  Code:
     0: aload_0
     1: invokeinterface #7,  1   // InterfaceMethod java/util/List.size:()I
     6: ireturn
  Signature: #52   // (Ljava/util/List<Ljava/lang/String;>;)I
```

Both methods carry the identical `descriptor: (Ljava/util/List;)I` — that field is what the JVM's linker actually matches on when it resolves a call, and it is what makes the two callers binary-interchangeable with any `List` implementation compiled at any point since 1.4. The generic method differs in exactly one place: a `Signature` attribute, `(Ljava/util/List<Ljava/lang/String;>;)I`, which only the compiler and reflection ever read — the JVM's own dispatch and verification never look at it. The other difference shows up at the *call site*, not the declaration. Compiling a caller that reads an element back out:

```
// against sizeRaw(List) — the call site adds nothing
17: aload_1
21: invokestatic  #28   // Method sizeRaw:(Ljava/util/List;)I

// against sizeGen(List<String>) plus gen.get(0) — the call site adds a checkcast
17: aload_1
18: iconst_0
19: invokeinterface #22, 2   // InterfaceMethod java/util/List.get:(I)Ljava/lang/Object;
24: checkcast     #26        // class java/lang/String
27: astore_2
```

`List.get` returns `Object` at the descriptor level regardless of the type argument — erasure has already thrown that information away by the time bytecode exists — so the compiler inserts a `checkcast` at every read site where the generic type says the result should be narrower. That single `checkcast` is the entire runtime cost and the entire runtime safety net of generics: it is what turns a silent `ClassCastException` two calls later, back when `List` was raw and untyped, into an immediate one at the point of the unsound read. Binary compatibility is why the descriptor cannot change; the `checkcast` is the tax the caller pays for the language to have kept that promise while still checking anything at all.

Now the bill for keeping that promise, four items, because the mechanism above forces every one of them:

| Consequence | Why erasure forces it | Owned by |
|---|---|---|
| Raw types compile and switch off all generic checking on that variable | The pre-generics descriptor and behaviour must still be legally producible from source, so `List` with no arguments has to remain legal syntax with its 1.4 semantics | `01c-raw-types-and-unchecked-warnings.md` |
| No `new T[n]`, no `instanceof List<Money>` | The erased class file has no record of `T` or `Money` left at those points to check against | `01a-erasure-and-its-consequences.md` |
| Two overloads cannot differ only in type argument (`f(List<String>)` and `f(List<Integer>)` collide) | Both erase to the identical descriptor `f(Ljava/util/List;)V`, and the JVM overload-resolves on descriptors | `02c-inference-and-generic-limits.md` |
| Primitives cannot be type arguments — `List<Integer>` boxes every element instead of storing a `long` | A type argument has to erase to a reference type so a single erased implementation (`Object[]`-backed) serves every parameterisation; there is no way to erase `T` to `long` | `../wrappers-and-boxing/01-basics.md` |

The fourth line is not a footnote. `**[NUM]**` QuizStakes reserves stakes at 2.8M/day, 1,200/sec at peak, and if each reservation boxes one `Long` amount-in-minor-units into a `List<Long>` rather than storing it in a `long[]`, that is 2.8M boxed `Long` allocations a day just for that one field — each one a heap object with a 16-byte header plus the 8-byte payload versus zero allocation for a primitive slot, before you even count the pointer-chasing cost of walking a `List<Long>` versus a contiguous `long[]`. The exact bytes-per-object accounting and the aggregate cost across QuizStakes' actual ledger volumes belongs to `../wrappers-and-boxing/01-basics.md` and the rollup in `../cost-model/02-master-cost-table.md` — the point to take here is only that this line item is a direct, provable consequence of the erasure decision made in 2004, not an unrelated Java quirk.

The counterfactual — what a language with reified generics (C#) buys instead, and what Valhalla's specialised generics are expected to change — is one sentence and a pointer, not a second argument: reification would let a generic type carry its type argument at runtime and specialise storage per parameterisation, at the cost of the exact binary-compatibility guarantee this section just proved Java kept; the full trade-off lives in `03e-internals-why-erasure-and-super-type-tokens.md`.

Version honesty, and again `**verified rather than asserted**`: raw types have never been deprecated — there is no `@Deprecated` on `java.util.List` and no removal ever proposed — they are only warned about, and that warning is **off by default**. Compiling the exact snippet above with no flags at all produces only the generic unchecked note, not a rawtypes warning:

```
$ javac RawUse.java
Note: RawUse.java uses unchecked or unsafe operations.
Note: Recompile with -Xlint:unchecked for details.
```

but `-Xlint:all` on the identical source surfaces the specific category:

```
$ javac -Xlint:all RawUse.java
RawUse.java:5: warning: [rawtypes] found raw type: List
    static void addOne(List l) {
                       ^
  missing type arguments for generic class List<E>
RawUse.java:6: warning: [unchecked] unchecked call to add(E) as a member of the raw type List
        l.add("x");
             ^
RawUse.java:9: warning: [rawtypes] found raw type: List
```

That is JDK 21.0.7, plain `javac`: `[rawtypes]` exists as a lint category and is real, but it is silent unless you ask for it, which is exactly why fifteen-year-old raw-type usages sail through CI unnoticed to this day.

**Insight:** every "why does Java generics do that" complaint you will hear in an interview loop — no primitive type arguments, no `new T[]`, no overload on type argument, raw types compiling with a warning nobody enabled — is the same root cause restated four times: the descriptor a generic type erases to must equal the descriptor its pre-1.5 ancestor had, because JLS 13 binary compatibility does not get an exception for "but generics are nicer."

**Gotcha:** people assume raw-type usage is rare enough in 2026 that this is archaeology. It is not — every reflective framework that predates generics (`java.beans`, a good deal of JDBC's `ResultSet` metadata plumbing) and every JNI or legacy-interop boundary still hands you raw types today, unwarned, exactly as designed in 2004.

> Erasure makes a generic type's compiled descriptor identical to its pre-generics ancestor's, which is what let `java.util.List` gain a type parameter in 2004 without breaking a single already-compiled `.class` file — and every restriction generics impose today is the continuing cost of that one guarantee.

## 2. `Optional<T>` placement: a return type, never a field, a parameter, or a collection element (2.7.17) `[X-REF 04]`

### Why it exists

`Optional<T>` was added (Java 8) to give a method a way to say "there might genuinely be no answer, and the caller must handle that" in the type system itself, instead of the two folklore alternatives: returning `null` and hoping the caller remembers to check, or throwing an exception for a case that is not actually exceptional. It is a **rule about one specific position** — a method's return type — not a general-purpose "nullable" wrapper you can drop anywhere a value might be absent, and treating it as the latter is the single most common `Optional` misuse in production code.

### The mechanism

One self-contained fact before the rule, because you cannot reason about the placement restrictions without knowing what the object actually is: `Optional<T>` is a small **value-based class** — `public final class Optional<T>` — holding exactly one field, a possibly-null reference of type `T`, with no other state. `**[SOURCE]**` `javap -v` on the JDK 21 class confirms it carries the `jdk.internal.ValueBased` annotation (`RuntimeInvisibleAnnotations: 0: #186() jdk.internal.ValueBased`), which is the JDK's own marker that this class's identity is not meant to be programmed against: never lock on an `Optional`, never compare two `Optional`s with `==`, never serialize one expecting object identity to survive. That annotation is why the placement rules below are correctness rules and not merely style.

The rule itself: `Optional` belongs on a method's return type, and specifically the return type of a method whose "nothing to return" outcome is a *normal* result the caller is expected to branch on — `findAccountByEmail(String email)` returning `Optional<Account>` when no account matches that email is a completely ordinary lookup outcome, not an error. Then three prohibitions, each with its own reason:

| Never as a | Why | QuizStakes example |
|---|---|---|
| **Field** | `Optional` is not `Serializable` (confirmed above by the absence of any `implements` clause on JDK 21's `javap -p java.util.Optional`), and a field typed `Optional<T>` gives the object three states — the field reference is `null`, the field holds an empty `Optional`, or the field holds a present one — where the domain only ever had two | `StakeSplit(Money bonusPortion, Money cashPortion)` with `bonusPortion` typed `Optional<Money>` is wrong: the invariant is bonus + cash == stake, so "no bonus contributed" is `Money.ZERO`, not an empty `Optional`. A `StakeSplit` field that can itself be `null` on top of that gives you the exact three-state mess the type was invented to avoid |
| **Parameter** | It forces every caller to construct a wrapper just to make the call, and the callee still has to handle a literal `null` passed as the `Optional` argument — nothing about the type stops that — so it buys no safety and adds ceremony at every call site | A hypothetical `AssessmentService.score(Optional<LimitSet> overrideLimits)` is better as two overloads, `score(LimitSet overrideLimits)` and `score()`, or a single nullable parameter with the nullability documented — either gives the same information with none of the wrapper cost |
| **Collection element** | A `Map` already has a way to express "no value here": not containing the key. `List<Optional<Money>>` or `Map<ClientId, Optional<Account>>` reintroduces the null-vs-empty ambiguity the collection API already solved with `Map.getOrDefault` and `Map.computeIfAbsent` | `Map<ClientId, Optional<Account>>` mapping every known client to their (possibly missing) account is a design smell — the fix is `Map<ClientId, Account>` and simply omitting the entry when there is no account, then reading with `accounts.getOrDefault(clientId, null)` or, better, restructuring the caller around `containsKey`/`get` |

*Effective Java*, Item 55: *Return optionals judiciously* states this same rule directly and adds the corollary that an `Optional` should itself never be `null` — a method declared to return `Optional<T>` must never `return null;`, it must return `Optional.empty()`. (Cited by title per this project's standing rule: the item-number-to-edition mapping is unverified, so the title is load-bearing, the number is a convenience.)

`[X-REF 04]` `Optional`'s full API — `map`, `flatMap`, `filter`, `orElseThrow`, the stream-integration methods (`stream()`, `Stream.ofNullable`) — is guide `04 Modern Java`'s territory; this section only owns the placement rule. Likewise the broader null-handling story, including why `orElse(expensiveDefault())` evaluates its argument eagerly even when the `Optional` is present (a frequent follow-up to this exact interview question), belongs to `../null-discipline/02-null-discipline.md`.

**Interview:** "Where should `Optional` never appear?" — field, parameter, collection element; it belongs on a return type, and specifically one whose absent case is a normal outcome the caller must branch on, never a stand-in for "this value might be missing" wherever that thought occurs to you.

> `Optional<T>` is a return-type-only signal for "this method's absence case is a normal outcome the caller must handle" — never a field (loses `Serializable`, adds a third state), never a parameter (pushes wrapper cost onto every caller for no safety gain), and never a collection element (the collection already has `containsKey`).

## 3. Reading a hard JDK signature end to end: `Collectors.toMap` (2.7.18) `[PROVE]` `[X-REF 04]`

### Why it exists

Every engineer eventually meets a generic signature that looks like line noise on first read. The skill this section teaches is not "memorise `Collectors.toMap`" — it is a repeatable procedure for taking any such signature apart, token by token, until nothing in it is unexplained. That procedure is the actual interview skill; `Collectors.toMap` is just a strong enough example to force every technique in one signature.

### The mechanism

`**[SOURCE]**` verified against JDK 21.0.7's real `javap -p java.util.stream.Collectors`, not retyped from the syllabus (which gives the same shape, and the check confirms it matches exactly):

```
public static <T, K, U, M extends java.util.Map<K, U>>
java.util.stream.Collector<T, ?, M> toMap(
    java.util.function.Function<? super T, ? extends K> keyMapper,
    java.util.function.Function<? super T, ? extends U> valueMapper,
    java.util.function.BinaryOperator<U> mergeFunction,
    java.util.function.Supplier<M> mapSupplier);
```

`[PROVE]` — read every token in declaration order, in the order a caller actually has to resolve them, and justify each one rather than summarise the whole:

**The four type variables, and where each is pinned.** `T` is the stream's element type — it appears nowhere in the return type, only in both `Function` parameters' consuming position, so it is pinned by whatever stream calls `collect` with this collector. `K` is the map's key type, pinned by `keyMapper`'s result. `U` is the map's value type, pinned by both `valueMapper`'s result and `mergeFunction`'s operand and result types simultaneously — that double pinning is why `U` cannot be a wildcard, covered below. `M` is the concrete map type the caller wants back, pinned by `mapSupplier`'s result and constrained by the bound `M extends Map<K, U>`.

**Why the bound is `M extends Map<K, U>` and not `M extends Map<?, ?>`.** A weaker bound would let the caller hand in a `Supplier<TreeMap<String, Integer>>` while `keyMapper`/`valueMapper` produce `Position` and `Money` — nothing would tie the supplied map's key and value types to what the mappers actually produce, and the collector would either not compile usefully or would compile and then fail at the first `put`. Tying `M`'s bound to the *same* `K` and `U` the other three parameters already pinned is what lets the compiler catch a mismatched supplier at the call site, in source, before any bytecode runs — which is exactly what the deliberate-break example below demonstrates happening.

**Why `? super T` on both mappers, and `? extends K` / `? extends U` on their results — PECS in the one place it actually bites here.** Both `Function` parameters *consume* a `T` (the collector hands each stream element to them), so the parameter type is in contravariant position: `? super T` lets the caller pass a `Function<Object, K>` if they have one lying around, not only an exact `Function<T, K>`. Both mappers *produce* their respective outputs, so those positions are covariant: `? extends K` lets a mapper return any subtype of `K`, not exactly `K`. This is the identical PECS reasoning `02-in-anger.md` develops on `Collections.addAll`, `Collections.copy` and `Collections.sort` — this section applies it rather than re-deriving it.

**Why `BinaryOperator<U>` is bare `U`, invariant, while its neighbours are wildcarded.** `BinaryOperator<U>` extends `BiFunction<U, U, U>` — it both *consumes* two `U` values (to compare or combine on a key collision) and *produces* a `U` (the merged result) in the same type variable. PECS has no direction to offer when a position is simultaneously a consumer and a producer of the same variable: a `? extends U` would forbid passing two `U`s in (you cannot call a method that only promises to return some subtype of `U` with two `U` arguments unless it also accepts them, which `extends` doesn't guarantee), and a `? super U` would forbid trusting the result back out as `U`. The only sound choice, when one position is both ends of PECS on the same variable, is no wildcard at all.

**The `?` in `Collector<T, ?, M>` — the token every reader skips.** `Collector<T, A, R>`'s middle parameter, `A`, is the collector's internal accumulator type — for `toMap`, in practice a `HashMap` or similar mutable structure used during accumulation before an optional finishing transform produces the caller-visible `M`. `toMap` hides it behind a wildcard on purpose: the accumulator is an implementation detail the caller must never see, name, or write into — it might change between JDK releases without notice. **This is one of the legitimate uses of a wildcard in a return type**, which looks like a direct contradiction of `02-in-anger.md`'s "never a wildcard return type" rule until you notice what that rule was actually protecting against: a caller who needs to *write into* or *reconstruct* the hidden type having no way to do so, forced into a capture-helper workaround. Here, the caller is never expected to do either — nothing in the public API of `Collector<T, ?, M>` exposes `A` for reading or writing, so there is no capture problem to create. The rule and this signature agree: a wildcard return type is fine exactly when the wildcarded position is genuinely opaque to every caller, and broken exactly when a caller has a legitimate reason to name or construct that position, which is what `02-in-anger.md`'s own `recentEntries()` counter-example demonstrates.

Now use it, compiled and run on JDK 21.0.7. `LedgerEntry` entries collected into an `EnumMap<Position, Money>` with a real merge function that sums colliding entries:

```java
enum Position { CASH_AVAILABLE, BONUS_AVAILABLE }

record Money(BigDecimal amount, Currency currency) {
    Money plus(Money other) { return new Money(amount.add(other.amount), currency); }
}

record LedgerEntry(Position position, Money amount) {}

List<LedgerEntry> entries = List.of(
        new LedgerEntry(Position.CASH_AVAILABLE, new Money(new BigDecimal("4.20"), gbp)),
        new LedgerEntry(Position.CASH_AVAILABLE, new Money(new BigDecimal("3.00"), gbp)),
        new LedgerEntry(Position.BONUS_AVAILABLE, new Money(new BigDecimal("0.33"), gbp)));

BinaryOperator<Money> sumMoney = Money::plus;

Map<Position, Money> totals = entries.stream()
        .collect(Collectors.toMap(
                LedgerEntry::position,
                LedgerEntry::amount,
                sumMoney,
                () -> new EnumMap<>(Position.class)));
```

No type witness anywhere. `T` is inferred as `LedgerEntry` from the stream; `K` as `Position` and `U` as `Money` from the two method references; `M` as `EnumMap<Position, Money>` from the supplier lambda; the return-type bound `M extends Map<K, U>` is satisfied because `EnumMap<Position, Money>` really does extend `Map<Position, Money>`. Compiled and run on JDK 21.0.7:

```
{CASH_AVAILABLE=Money[amount=7.20, currency=GBP], BONUS_AVAILABLE=Money[amount=0.33, currency=GBP]}
```

`7.20` is `4.20 + 3.00` merged by `sumMoney` on the colliding `CASH_AVAILABLE` key — the bound and the merge function both did real work, not just type-checked.

Now break it deliberately: keep the same mappers (so `K` is still inferred as `Position`, `U` still `Money`), but hand in a `Supplier<TreeMap<String, Money>>` instead — a map keyed on `String`, not `Position`:

```java
Map<Position, Money> totals = entries.stream()
        .collect(Collectors.toMap(
                LedgerEntry::position,
                LedgerEntry::amount,
                sumMoney,
                () -> new TreeMap<String, Money>()));
```

`javac` on JDK 21.0.7 rejects it at the call site, before any bytecode exists:

```
error: no suitable method found for toMap(LedgerEntry::position,LedgerEntry::amount,BinaryOperator<Money>,()->new TreeMap<String,Money>())
    method Collectors.<T#3,K#3,U#3,M>toMap(Function<? super T#3,? extends K#3>,Function<? super T#3,? extends U#3>,BinaryOperator<U#3>,Supplier<M>) is not applicable
      (inference variable K#3 has incompatible bounds
        equality constraints: String
        lower bounds: Position)
```

Read that against the bound this section just walked through: `keyMapper` pinned `K` with a *lower bound* of `Position` (its actual return type), while the supplier's `TreeMap<String, Money>` forces `M`'s bound `M extends Map<K, U>` to require `K` to *equal* `String`. One inference variable cannot satisfy "must be exactly `String`" and "must be at least `Position`" simultaneously, so inference fails and the whole call is rejected — this is `M extends Map<K, U>` doing precisely the job identified above: catching a mismatched supplier in source, at compile time, rather than at the first `put` on a live `EnumMap`.

A transferable procedure for the next hard signature you meet, in the order that actually resolves it:

1. Read the type-variable declarations first (`<T, K, U, M extends Map<K, U>>`) — note every bound before looking at a single parameter.
2. Read the return type next (`Collector<T, ?, M>`) — it tells you what the method is *for* before you get lost in how it gets there.
3. Read each parameter in order, noting which type variable each one pins and in which direction (producer or consumer of that variable).
4. Check every wildcard against PECS — producer extends, consumer super — and for any bare (non-wildcarded) type variable, check whether that position is *both* a producer and a consumer of the same variable, which is exactly when invariance is forced.
5. For every `?` you have not yet accounted for, ask specifically what it is hiding and whether the caller is ever expected to name or construct that position — if never, the wildcard is legitimate even in a return type.

Applied, briefly, to a second real JDK 21 signature as the drill: `Collections.<T extends Comparable<? super T>> T max(Collection<? extends T> coll)`. Step 1: one type variable, `T`, recursively bounded — `T` must be comparable not necessarily to itself but to *some supertype* of itself, which is what lets a class implementing `Comparable<Number>` still be usable as the element type even though it isn't literally `Comparable<T>` for its own exact `T` (this is the recursive-bound pattern `01d-recursive-bounds-and-heterogeneous-containers.md` names precisely). Step 2: the return type is bare `T` — the caller gets back exactly the element type they put in, no hidden position. Step 3: one parameter, `Collection<? extends T>` — a pure producer, `max` only ever reads elements out of it. Step 4: `? extends T` is textbook PECS on a producer parameter, and `? super T` on the bound is the same producer logic one level up, applied to the comparison contract rather than the collection. Step 5: no `?` left unaccounted — there is no hidden position in this one, which is itself worth noticing: not every hard-looking signature has an opaque type to hunt for.

`[X-REF 04]` Streams and collectors as a subject — the rest of the `Collectors` factory methods, `Stream` pipeline construction, laziness and short-circuiting — belong to guide `04 Modern Java`; this section owns only the skill of reading the signature, not the API it sits in.

**Gotcha:** the natural instinct on meeting `Collector<T, ?, M>` is to assume the `?` is a mistake or a placeholder the author forgot to fill in. It is neither — it is the one wildcard position in this entire signature that is *supposed* to stay unnamed, and assuming otherwise is what sends people hunting for an accumulator type that the API deliberately never promises to keep stable across releases.

> Reading a hard generic signature is a fixed procedure — type-variable declarations, then return type, then each parameter's producer/consumer role against PECS, then every remaining `?` — and applying it turns `Collectors.toMap`'s four type variables and hidden accumulator from line noise into four ordinary, individually justified constraints.

## Supporting facts

### `List<Object>`, raw `List`, and `List<?>` are not the same migration story

Raw `List` is what 1.4 code used to write, unconditionally, with no generics at all — it is the migration-compatibility survivor this file's §1 covers. `List<Object>` and `List<?>` are both fully generic, post-1.5 constructs with completely different variance behaviour from each other and from raw `List`; that three-way distinction, and the unchecked-warning discipline around each, is `01c-raw-types-and-unchecked-warnings.md`'s territory, not this file's — this file only explains why the *raw* option exists at all.

### `Optional.of` vs `Optional.ofNullable`

`Optional.of(value)` throws `NullPointerException` immediately if `value` is `null`; `Optional.ofNullable(value)` returns `Optional.empty()` instead. Picking `of` when the value can genuinely be `null` converts a silent bug into a loud one at construction time rather than at first use — that is a feature, not a footgun, when the value is truly expected to be non-null at that call site.

> `Optional.of` asserts non-null at construction; `Optional.ofNullable` defers the null-vs-present decision to the type itself.

### Why raw-type unchecked warnings and `-Xlint:rawtypes` are separate categories

`javac`'s default output bundles several warning kinds under one generic "uses unchecked or unsafe operations" note and only breaks them out into `[rawtypes]`, `[unchecked]`, `[deprecation]` and the rest under an explicit `-Xlint:<category>` or `-Xlint:all`. This is a deliberate noise-reduction default from early in the lint mechanism's life, not a rawtypes-specific decision — but it means a raw-type usage compiling clean in a build without `-Xlint` configured is the normal, expected outcome, not a sign the code is unusually clean.

> The absence of a rawtypes warning in default `javac` output proves nothing about whether raw types are present — it only proves `-Xlint:rawtypes` was never asked for.

## Pitfalls

### "Erasure means Java could just as easily have kept raw types generic-checked at compile time only, with no runtime cost at all"

**Wrong**

```java
List<String> strings = new ArrayList<>();
List raw = strings;          // legal: List<String> is-a raw List
raw.add(42);                 // compiles with only an [unchecked] warning
String s = strings.get(0);   // ClassCastException here, not at raw.add(42)
```

**Right**

```java
List<String> strings = new ArrayList<>();
List<String> notRaw = strings;
// notRaw.add(42) does not compile at all — no assignment of int to String
```

Treat any raw-typed reference to a generic collection as a hole in the type system that the compiler cannot see through — the failure surfaces at the read, arbitrarily far from the write that actually caused it, because the `checkcast` proved in §1 only fires where the *generic* type is known, and once code goes through a raw reference that knowledge is gone.

**Why people believe it:** the `[unchecked]` warning at the `raw.add(42)` line looks like the compiler already caught the problem, so it is easy to assume the runtime is equally protected — it is not; the warning is advisory and the runtime failure is deferred to the next generically-typed read.

### "`Optional<T>` as a field is fine as long as I always check `isPresent()` before reading it"

**Wrong**

```java
record StakeSplit(java.util.Optional<Money> bonusPortion, Money cashPortion) {}

StakeSplit split = new StakeSplit(null, cashOnly);   // compiles — field is null, not empty
split.bonusPortion().isPresent();                    // NullPointerException
```

**Right**

```java
record StakeSplit(Money bonusPortion, Money cashPortion) {
    StakeSplit {
        if (bonusPortion.amount().signum() < 0 || cashPortion.amount().signum() < 0) {
            throw new IllegalArgumentException("stake split components must be non-negative");
        }
    }
}
// absent bonus is represented by Money.ZERO, not Optional.empty()
```

`Optional` never protects against `null` reaching the field itself — nothing in the type stops `new StakeSplit(null, cash)` from compiling — so the three-state hazard this file's §2 describes is not hypothetical, it is one constructor call away.

**Why people believe it:** discipline around calling `isPresent()`/`isEmpty()` feels like it closes the gap, but it only closes the gap for values that were actually assigned an `Optional` — it does nothing about a caller who passes a bare `null` where the field's declared type merely says `Optional<Money>`.

### "The compiler will tell me if my `Collectors.toMap` supplier doesn't match, so I don't need to read the bound myself"

**Wrong**

```java
Map<Position, Money> totals = entries.stream()
        .collect(Collectors.toMap(
                LedgerEntry::position,
                LedgerEntry::amount,
                sumMoney,
                HashMap::new));   // compiles, but silently drops EnumMap's ordering guarantee
```

**Right**

```java
Map<Position, Money> totals = entries.stream()
        .collect(Collectors.toMap(
                LedgerEntry::position,
                LedgerEntry::amount,
                sumMoney,
                () -> new EnumMap<>(Position.class)));   // explicit M, matches the intended iteration order
```

The compiler only rejects a supplier whose `M` fails the *type* bound `M extends Map<K, U>` — it has no opinion on which concrete `Map` implementation you actually wanted, so a `HashMap::new` supplier compiles cleanly in the first snippet while quietly losing the enum-declaration iteration order an `EnumMap` would have guaranteed. Reading the bound tells you what the compiler will catch; it does not tell you what it won't.

**Why people believe it:** the deliberate-break example in §3 shows the compiler catching a real mismatch, which makes it feel like the bound is a complete safety net — it only catches type mismatches, never a implementation choice that is type-correct but behaviourally wrong for the caller's needs.

## Cheat sheet

| Topic | One-line rule |
|---|---|
| Raw type binary compatibility | Generic type erases to its pre-1.5 ancestor's exact descriptor — JLS 13 binary compatibility, proven by identical `javap` descriptors |
| Raw type default warning | Silent under plain `javac`; `[rawtypes]` only appears under `-Xlint:all` or `-Xlint:rawtypes` |
| Cost of the migration guarantee | No `new T[n]`, no `instanceof List<Money>`, no overload-by-type-argument, no primitive type arguments |
| `Optional` — never a field | Not `Serializable`; turns a two-state value into a three-state one (`null` field / empty / present) |
| `Optional` — never a parameter | Forces caller-side wrapping; callee still has to handle a bare `null` `Optional` anyway |
| `Optional` — never a collection element | The collection already expresses absence via missing key (`getOrDefault`, `computeIfAbsent`) |
| `Optional` is | `jdk.internal.ValueBased` — no identity-sensitive operations (`==`, locking) |
| `Collectors.toMap` type variables | `T` stream element, `K`/`U` from the two mappers, `M` from the supplier, bound `M extends Map<K,U>` ties them together |
| `Collectors.toMap` mapper wildcards | `? super T` (consume), `? extends K` / `? extends U` (produce) — plain PECS |
| `BinaryOperator<U>` in `toMap` | Bare `U`, invariant — it both consumes and produces `U` in the same position |
| `Collector<T, ?, M>`'s `?` | The hidden accumulator type — legitimate wildcard return because no caller ever names or writes into it |
| Signature-reading procedure | Type variables → return type → each parameter's producer/consumer role → PECS check → what every remaining `?` hides |

## Self-test

**Q1.** Why does `List` compiled in Java 1.4 still link against code compiled against `List<CashEntry>` in Java 21, with no recompilation of the old code required?

<details><summary>Answer</summary>

Because generics use erasure: `List<CashEntry>` erases to exactly the descriptor `List` already had before generics existed — the same `Ljava/util/List;` type descriptor at every method site. The JVM's linker resolves calls by descriptor, and that descriptor never changed, so a `.class` file compiled in 1.4 and one compiled today against a parameterised `List` are binary-compatible under JLS 13 — the only difference is a `Signature` attribute the pre-generics file never had, which only the compiler and reflection read, and a `checkcast` inserted at the generic caller's read sites, not at the JVM's linking step.

</details>

**Q2.** Name three restrictions on generics that exist purely because of the migration-compatibility decision, and connect each one to the mechanism.

<details><summary>Answer</summary>

No `new T[n]` — the erased class file has no runtime record of `T` to allocate against. No `instanceof List<Money>` — same reason, the parameterisation is gone by the time bytecode exists. No overloading two methods that differ only in type argument, e.g. `f(List<String>)` and `f(List<Integer>)` — both erase to the identical descriptor `f(Ljava/util/List;)V`, and the JVM resolves overloads by descriptor, so the two would collide as the same method. All three trace back to the same fact: erasure deletes the type argument before the class file exists, and every one of these restrictions is a direct consequence of that deletion, not an independent design choice.

</details>

**Q3.** Is `[rawtypes]` a real `javac` warning category on JDK 21? Under what exact condition does it actually print?

<details><summary>Answer</summary>

Yes — confirmed by compiling a raw-type use with `-Xlint:all`, which prints `warning: [rawtypes] found raw type: List` at each raw-type site. Under plain `javac` with no `-Xlint` flag at all, the same source produces only a generic "uses unchecked or unsafe operations" note with no mention of `rawtypes` specifically — the category exists and is real, but it is off by default, so most CI pipelines that don't explicitly enable `-Xlint:rawtypes` or `-Xlint:all` never see it.

</details>

**Q4.** Why should `Optional<Money>` never be the type of a field on a record like `StakeSplit`, and what should replace it here specifically?

<details><summary>Answer</summary>

Two reasons. First, `Optional` is not `Serializable`, which rules it out as a field type anywhere serialization might be needed. Second, and more important for correctness, an `Optional<Money>` field creates three observable states — the field reference itself being `null`, the field holding `Optional.empty()`, and the field holding a present value — when the domain only has two: bonus contributed or not. For `StakeSplit`, the invariant is that bonus plus cash equals the stake exactly, so the "no bonus" case has a perfectly good non-`Optional` representation already: `Money.ZERO`. Using `Money.ZERO` instead of `Optional.empty()` removes the third state entirely and keeps the invariant checkable in a compact constructor.

</details>

**Q5.** In `Collectors.toMap`'s four-argument overload, why is `BinaryOperator<U>` written as bare `U` with no wildcard, while the two `Function` parameters both use wildcards?

<details><summary>Answer</summary>

Because `BinaryOperator<U>` (as a `BiFunction<U,U,U>`) both *consumes* two `U` values, to combine them on a key collision, and *produces* a `U`, the merged result, in the same type variable. PECS gives a direction — `extends` for producer positions, `super` for consumer positions — only when a position is one or the other. When a single position is simultaneously both, as `BinaryOperator<U>` is here, neither wildcard direction is sound: `? extends U` would forbid passing two `U` arguments in, and `? super U` would forbid trusting the returned value as a `U`. The two `Function` parameters don't have this problem because each one is purely a consumer of `T` and purely a producer of its own output type, so each gets its own independent, correctly-directed wildcard.

</details>

**Q6.** What does the `?` in `Collector<T, ?, M>` actually hide, and why doesn't this contradict the "never a wildcard return type" rule from `02-in-anger.md`?

<details><summary>Answer</summary>

It hides the collector's internal accumulator type — the mutable structure, typically something like a `HashMap`, that `toMap` uses to build up the result before any finishing transform produces the caller-visible `M`. It doesn't contradict the wildcard-return-type rule because that rule exists to stop a caller from being stuck unable to *name or reconstruct* a hidden position they actually need — the classic failure is a return type like `Collection<? extends LedgerEntry>` where the caller genuinely wants to add elements back in and can't. Here, no caller of `Collectors.toMap` is ever expected to read, write, or name the accumulator type at all; it is a pure implementation detail with zero legitimate caller-side use. A wildcard return type is fine exactly when the wildcarded position is genuinely opaque to every caller, and that's the case here.

</details>

**Q7.** A caller passes a `Supplier<TreeMap<String, Money>>` as the fourth argument to `Collectors.toMap`, while the key mapper returns `Position`. What happens, and why?

<details><summary>Answer</summary>

The call fails to compile. `keyMapper`'s return type pins the inference variable `K` with a lower bound of `Position`. The supplier's `TreeMap<String, Money>` forces `M`'s declared bound, `M extends Map<K, U>`, to require `K` to equal `String` exactly. A single inference variable can't simultaneously be "at least `Position`" and "exactly `String`" — those are incompatible bounds — so type inference fails and `javac` reports that no applicable `toMap` overload exists, quoting the conflicting bounds directly. This is the `M extends Map<K, U>` bound doing its job: catching a key-type mismatch between the mappers and the supplied map at compile time, before any `put` call could fail on a live map at runtime.

</details>

**Q8.** Give the five-step procedure for reading an unfamiliar generic signature, in order, and say why the order matters.

<details><summary>Answer</summary>

One: read the type-variable declarations and their bounds first, before looking at any parameter. Two: read the return type, to know what the method is actually for. Three: read each parameter in order, noting which type variable it pins and whether it's acting as a producer or consumer of that variable. Four: check every wildcard against PECS — producer gets `extends`, consumer gets `super` — and notice any bare, unwildcarded variable, which signals a position that's both producer and consumer at once. Five: for every remaining `?`, ask what it's hiding and whether any caller legitimately needs to name it. The order matters because the bounds from step one constrain everything that follows — you can't correctly judge whether a parameter's wildcard direction makes sense until you already know what that type variable is bounded by and where else it's used, and you can't tell whether a `?` in the return type is a genuine implementation-detail hiding as opposed to a bug until you've already accounted for every other type variable's role.

</details>

## Open questions

None.

---

**Leaves covered:** 2.7.16, 2.7.17, 2.7.18 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 429
