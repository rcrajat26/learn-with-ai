# 03 Java Core — Generics in anger: choosing a signature — INTERMEDIATE (§2.7, 2.7.1–2.7.4)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Recursive bounds and heterogeneous containers](01d-recursive-bounds-and-heterogeneous-containers.md) · Next: [Type tokens and generic reflection](02a-type-tokens-and-generic-reflection.md)

This file assumes you already have invariance, the three wildcard forms and the PECS mnemonic from `01b-variance-and-wildcards.md` — it does not re-teach any of that. What it covers instead is the question you face once you already know the rules: given a method you are about to write, which signature do you actually put on it — a wildcard, or a named type variable — and why does the JDK's own API look the way it does. Four leaves: the decision rule between a generic method and a wildcard (2.7.1), the wildcard-capture helper idiom that lets `Collections.swap` keep its simple public signature (2.7.2), PECS read off four real JDK signatures with the caller-visible breakage each wildcard prevents (2.7.3), and why a wildcard return type is never the right call (2.7.4). Raw types, recursive bounds and the heterogeneous container are handled in the two files this one follows; type tokens, generic arrays, inference failure and migration/`Optional` placement are the four files this one leads into — each gets one paragraph and a pointer where it is touched here, never a second treatment.

## 1. Generic method versus wildcard — the decision rule (2.7.1)

A wildcard says "some type, I don't need its name." A type variable says "some type, and I need to write its name down again somewhere else in this signature so two things can agree." That is the entire decision. Everything else below is that one sentence earned by working through the cases where each one is forced.

### Why it exists

Before Java 5's wildcards existed, every parameterised method that only *read* a collection still had to say exactly what it held, because raw types and `Object` were the only escape hatches. `void post(Collection<LedgerEntry> source)` rejects a `Collection<CashEntry>` even though a caller who only wants to iterate `LedgerEntry` values obviously has one. Generic methods with type variables fixed part of that — `<T extends LedgerEntry> void post(Collection<T> source)` accepts a `Collection<CashEntry>` by inferring `T = CashEntry` — but they buy that flexibility at the cost of a type variable the caller never needed to see, and of inference the compiler has to perform. Wildcards were added so the *simple* case — accept a family of types, use the value, never need to write the family's name a second time — did not have to pay for a type variable at all. The design problem is: which of these two tools do you reach for, and when does neither work?

### The mechanism

The rule falls out of counting occurrences of the type in the signature:

| The type appears, counting occurrences | Use | Example |
|---|---|---|
| exactly once, and never in the return type | wildcard | `void post(Collection<? extends LedgerEntry> source)` |
| twice (or more) and the two occurrences must be the *same* type | named type variable | `<T extends LedgerEntry> void transfer(Collection<T> source, Collection<T> destination)` |
| in the return type at all | named type variable (never a wildcard — this is 2.7.4) | `<T extends LedgerEntry> Collection<T> snapshot(Collection<T> source)` |
| only as an upper bound on a parameter you pass straight through without touching its elements | wildcard is still enough — you are not naming the type, just constraining it | `void archive(List<? extends LedgerEntry> entries)` |

Take the first row on a real `FundsLedger` operation. `post` reads a batch of entries and writes each to the ledger; nothing about calling `post` depends on knowing the *concrete* element type of the collection it was handed:

```java
class FundsLedger {
    static void post(Collection<? extends LedgerEntry> source) {
        for (LedgerEntry entry : source) {
            System.out.println("posted " + entry.id());
        }
    }
}
```

The alternative, `<T extends LedgerEntry> void post(Collection<T> source)`, compiles and behaves identically at every call site — but it is strictly worse. It gives the reader a type variable `T` to hold in their head that is used exactly once and never constrains anything relative to another parameter; it makes the compiler do inference work that has no payoff; and it invites a maintainer to add a second `T`-typed parameter later under the mistaken belief that `T` is already doing some linking work. `**Insight:**` a type variable that appears in only one parameter position and nowhere else is a signature smell — it is a wildcard that forgot to simplify itself.

Now the second row, where a wildcard genuinely cannot express the constraint. Moving withdrawals from one `Position`'s pending queue into another `Position`'s approved queue requires both collections to hold the *same* concrete element type — you cannot add a `CashEntry` you pulled out of one `Collection<?>` into a different `Collection<?>`, because each `?` is resolved independently:

```java
class TransferBad {
    static void transfer(Collection<?> source, Collection<?> destination) {
        destination.addAll(source);
    }
}
```

Compiling this on JDK 21.0.7 gives:

```
Domain.java:13: error: incompatible types: Collection<CAP#1> cannot be converted to Collection<? extends CAP#2>
        destination.addAll(source);
                           ^
  where CAP#1,CAP#2 are fresh type-variables:
    CAP#1 extends Object from capture of ?
    CAP#2 extends Object from capture of ?
```

Read the two capture names as the proof: `source`'s `?` captures to `CAP#1`, `destination`'s `?` captures to `CAP#2`, and the compiler has no way to know `CAP#1` and `CAP#2` name the same type — because nothing in the signature says they must. This is exactly the situation the table's second row names: the type appears in two places and those two places have to agree, so only a named type variable can carry that agreement across the signature:

```java
class Ledger {
    static <T extends LedgerEntry> void transfer(Collection<T> source, Collection<T> destination) {
        destination.addAll(source);
        source.clear();
    }
}
```

Compiled and run on JDK 21.0.7 with one `CashEntry` moved from `a` to `b`: output `a=0 b=1`, followed by `post(b)` printing `posted <uuid>`. The single `T` forces both parameters to the same inferred type at the call site, which is precisely the guarantee two independent `?`s cannot give you.

One paragraph on the neighbour you will hit immediately if you try to make the compiler infer `T` explicitly instead of relying on argument inference, or if `transfer`'s two arguments come from call sites with no common inferable type: that is a type-inference failure, not a wildcard-versus-generic-method question, and `02c-inference-and-generic-limits.md` owns the failure messages and the JLS 18 mechanism behind them.

No gotcha beyond the one already demonstrated: the temptation to reach for a wildcard because "it looks simpler" even when two occurrences must agree, and the compiler catching it immediately rather than letting it through.

> Use a wildcard when the type is named once and never returned; use a type variable the moment two occurrences must be the same type, or the type appears in the return.

## 2. The wildcard-capture helper idiom (2.7.2) `[PROVE]` `[BUILD]`

### Why it exists

You want to write `swap(List<?> list, int i, int j)` on a QuizStakes `PaymentRun`'s approved withdrawals list — reordering two entries has nothing to do with what element type the list holds, so by the 2.7.1 rule a wildcard is exactly right for the public signature. But the body of `swap` needs to *write back* the value it just *read out* of the same list, and that is where the wildcard, which was the right call for the signature, becomes an obstacle for the implementation.

### The mechanism

Write the API the way you want it first:

```java
class SwapBad {
    static void swap(List<?> approvedWithdrawals, int i, int j) {
        approvedWithdrawals.set(i, approvedWithdrawals.set(j, approvedWithdrawals.get(i)));
    }
}
```

Compiled on JDK 21.0.7:

```
SwapBad.java:5: error: incompatible types: Object cannot be converted to CAP#1
        approvedWithdrawals.set(i, approvedWithdrawals.set(j, approvedWithdrawals.get(i)));
                                                                                     ^
  where CAP#1 is a fresh type-variable:
    CAP#1 extends Object from capture of ?
```

`[PROVE]` Why the compiler cannot see the obvious: `List.get` on a `List<?>` returns whatever the *capture* of that `?` resolves to at that call — call it `CAP#1` — so `approvedWithdrawals.get(i)` really has static type `CAP#1`, not `Object`. `List.set` on the same `List<?>` demands an argument of that same `CAP#1` to write back, because writing into a `List<CAP#1>` requires exactly a `CAP#1`. The value you got out of `get(i)` genuinely *is* a `CAP#1` — but each mention of `?` in the method's own signature is only guaranteed to capture to the *same* unknown within a single expression if the compiler can see the two occurrences come from the same variable in the same statement; here the outer call to `set` at index `i` and the inner calls to `set` at index `j` and `get` at index `i` are different capture sites and `javac` does not try to unify them across separate calls. What the diagnostic is actually saying is narrower and more literal than "wildcards can't do this": the compiler briefly knows the precise capture type at each individual call, but it has no name for that type to carry between calls, so once the value leaves `get` as "whatever `CAP#1` is" and needs to go into another `set`, it cannot check that the two `CAP#1`s the type-checker invented for the two expressions are the same thing — because they are literally different, freshly-minted capture variables, one per call site. Naming the type is exactly what turns two different anonymous captures into one variable the checker can track.

`[BUILD]` The fix names it. A private generic helper introduces a real type variable `T`, and both `get` and `set` inside the helper are typed in terms of that one `T`:

```java
class WithdrawalOrdering {
    static void swap(List<?> approvedWithdrawals, int i, int j) {
        swapHelper(approvedWithdrawals, i, j);
    }

    private static <T> void swapHelper(List<T> list, int i, int j) {
        list.set(i, list.set(j, list.get(i)));
    }

    public static void main(String[] args) {
        List<CashEntry> approved = new ArrayList<>(List.of(
                new CashEntry(UUID.randomUUID(), new Money(new BigDecimal("10.00"), "GBP")),
                new CashEntry(UUID.randomUUID(), new Money(new BigDecimal("25.00"), "GBP")),
                new CashEntry(UUID.randomUUID(), new Money(new BigDecimal("40.00"), "GBP"))));
        swap(approved, 0, 2);
        for (CashEntry entry : approved) {
            System.out.println(entry.amount().amount());
        }
    }
}
```

Compiled and run on JDK 21.0.7, output in swapped order: `40.00`, `25.00`, `10.00`. The call `swapHelper(approvedWithdrawals, i, j)` from inside `swap` still type-checks against a `List<?>` argument, because passing a wildcard-typed value as the sole `List<T>` argument to a generic method is exactly what capture conversion is *for*: the compiler captures the `?` to a fresh `T` once, at the call boundary, and then `swapHelper`'s own body sees one consistent `T` throughout, which is the thing `SwapBad` never had.

No diagram: the manifest assigns this section none; the two `javac` transcripts above are the picture — one showing the capture that cannot be tracked across calls, one showing the capture happening cleanly once at the helper boundary.

The design point this idiom exists to make: the *public* signature stays `List<?>`. The type variable is purely an implementation detail that never leaks to a caller, who by the 2.7.1 rule should not have to see a type variable for an operation that never needs to name the list's element type. That is exactly why the real JDK does it this way — `javap -p -v java.util.Collections` on JDK 21.0.7 shows:

```
public static void swap(java.util.List<?>, int, int);
  descriptor: (Ljava/util/List;II)V
```

`Collections.swap`'s public descriptor is a wildcard, with no type variable in sight — because `Collections`' own source implements it with exactly this private-generic-helper pattern internally. `**Interview:**` "why doesn't `Collections.swap` take a type parameter" — because the caller never needs to name the element type, the implementation needs a name for it internally to satisfy the read/write agreement, and a private helper is where that name lives without leaking into the public contract.

> When a wildcard-typed API needs to read a value out and write it back into the same wildcard-typed structure, delegate to a private generic helper that gives the compiler one name for the captured type; the public signature keeps the simpler wildcard.

## 3. PECS on real JDK signatures — the caller-visible breakage (2.7.3) `[X-REF 02]`

### Why it exists

`01b-variance-and-wildcards.md` gives you PECS as a mnemonic: producer extends, consumer super. This section exists to show that the mnemonic is not a classroom simplification — it is a literal read of four signatures you use every day, and dropping the wildcard on any one of them breaks a caller who is doing something completely ordinary.

### The mechanism

| Signature | Producer position | Consumer position | What breaks without the wildcard |
|---|---|---|---|
| `Collection.addAll(Collection<? extends E> c)` | `c` produces elements into `this` | `this` is the consumer, typed exactly `E` | a `Collection<CashEntry>` could not be passed to `addAll` on a `Collection<LedgerEntry>` |
| `Collections.copy(List<? super T> dest, List<? extends T> src)` | `src` produces | `dest` consumes | you could not copy a `List<CashEntry>` into a `List<LedgerEntry>` |
| `List.sort(Comparator<? super E> c)` | — | `c` consumes `E` values to compare them | a shared `Comparator<LedgerEntry>` could not sort a `List<CashEntry>` |
| `Stream<T>.map(Function<? super T, ? extends R> mapper)` | `mapper`'s result is a producer of `R` | `mapper`'s argument is a consumer of `T` | a `Function<LedgerEntry, Money>` could not be used as the mapper for a `Stream<CashEntry>` |

Confirmed by `javap -p -v` on JDK 21.0.7 rather than from memory — `java.util.Collection`:

```
public abstract boolean addAll(java.util.Collection<? extends E>);
```

`java.util.Collections`:

```
public static <T extends java.lang.Object> void copy(java.util.List<? super T>, java.util.List<? extends T>);
```

`java.util.List`:

```
public default void sort(java.util.Comparator<? super E>);
```

`java.util.stream.Stream`:

```
public abstract <R extends java.lang.Object> java.util.stream.Stream<R> map(java.util.function.Function<? super T, ? extends R>);
```

Read each row against PECS: `addAll`'s parameter is pure producer (you only ever read elements out of `c` to add them), so `? extends E`. `copy`'s `src` is a producer (`? extends T`) and `dest` is a pure consumer (`? super T` — you only ever write into it, and the copy never reads back what was already there in a way that needs it typed as `T` exactly). `sort`'s comparator only ever consumes two `E` values to compare them and never hands one back to the caller, so `? super E`. `map`'s function is both: it consumes a `T` (contravariant position, `? super T`) and produces an `R` (covariant position, `? extends R`) — the two wildcard directions sit in the same parameter because a `Function` has both roles built in.

`map` is the one worth breaking on purpose, because the failure is the most common one a working engineer actually hits: reusing a `Function<LedgerEntry, Money>` — written once, generically, against the supertype — as the mapper for a `Stream<CashEntry>`. Reproducing the constraint with a narrowed, non-wildcarded `map` (real `Stream.map` already has the wildcard and would accept this call, which is the point — this shows what breaks the moment a hypothetical `map` is declared as `Function<T, R>` instead):

```java
interface NarrowStream<T> {
    <R> Stream<R> map(Function<T, R> mapper);
}

class MapBad {
    static void describe(NarrowStream<CashEntry> cashEntries) {
        Function<LedgerEntry, Money> extractAmount = LedgerEntry::amount;
        cashEntries.map(extractAmount);
    }
}
```

Compiled on JDK 21.0.7:

```
MapBad.java:19: error: method map in interface NarrowStream<T> cannot be applied to given types;
        cashEntries.map(extractAmount);
                   ^
  required: Function<CashEntry,R>
  found:    Function<LedgerEntry,Money>
  reason: cannot infer type-variable(s) R
    (argument mismatch; Function<LedgerEntry,Money> cannot be converted to Function<CashEntry,R>)
```

Exactly the caller-visible breakage the table predicts: a completely reasonable `Function<LedgerEntry, Money>` — reasonable because `amount()` is declared on `LedgerEntry`, the common supertype, so one function works for every `LedgerEntry` subtype — is rejected the instant the mapper parameter is typed as an exact match instead of `? super T`. The real `Stream.map`'s `Function<? super T, ? extends R>` is precisely what makes this call succeed instead.

No diagram: the manifest assigns this section none; the four `javap` excerpts above are the picture.

`[X-REF 02]` This shape — a producer parameter marked `? extends`, a consumer parameter marked `? super`, chosen so that a caller working one level up the hierarchy from the collection's element type is never rejected — is pervasive across `java.util` and `java.util.stream`: `Collections.max`/`min` take `Comparator<? super T>`, `PriorityQueue`'s comparator constructor does the same, `List.copyOf`/`Collectors.toList`-adjacent producer APIs favour `? extends`, and every `BiFunction`/`Consumer`/`Predicate` overload accepted by a stream operation follows the identical consumer-contravariant, producer-covariant shape. Guide `02 Java collections` owns the collections API surface and its internals in full; this file only establishes the reading technique.

`**Interview:**` "why does `Comparator<? super T>` and not `Comparator<T>`" appears constantly — the one-line answer is that a `Comparator<LedgerEntry>` is strictly more useful to a `List<CashEntry>.sort` than a `Comparator<CashEntry>` would be exclusive of it, because one comparator written against the supertype now sorts every subtype's lists, and `? super T` is the only spelling that admits it.

`**Pitfall:**` believing PECS is about *safety* rather than *usability* — none of these four signatures are less type-safe without the wildcard; `addAll(Collection<E> c)` would still be perfectly sound. The wildcard exists purely so ordinary calls — passing a `Collection<CashEntry>` where a `Collection<LedgerEntry>` producer is expected — are not rejected by a needlessly exact signature. The fix in each case above is not "insert an unsafe cast"; it is "use the standard-library signature as given," which is the entire lesson.

> `? extends` in a parameter position marks a producer you only read from; `? super` marks a consumer you only write into; dropping either wildcard rejects an ordinary caller working one level up or down the type hierarchy, not just a contrived one.

## 4. Never use a wildcard as a return type (2.7.4) `[PROVE]`

### Why it exists

A wildcard in a parameter is resolved by the *caller's* argument at the call site — the caller always knows the concrete type going in, even though the method signature does not name it. A wildcard in a *return* type has no such caller-supplied anchor: the value comes back already erased to an anonymous capture, and the caller who receives it has no way to name what they were handed.

### The mechanism

```java
class FundsLedger {
    private final List<CashEntry> cashEntries = new ArrayList<>();

    Collection<? extends LedgerEntry> recentEntries() {
        return cashEntries;
    }
}
```

`recentEntries()` looks harmless — it is even arguably "more flexible" by the same 2.7.1 instinct that made `post`'s parameter a wildcard. But a caller who receives the result cannot write into it:

```java
class ReturnBad {
    static void reconcile(FundsLedger ledger) {
        Collection<? extends LedgerEntry> entries = ledger.recentEntries();
        entries.add(new BonusEntry(UUID.randomUUID(), new Money(new BigDecimal("5.00"), "GBP")));
    }
}
```

Compiled on JDK 21.0.7:

```
ReturnBad.java:20: error: incompatible types: BonusEntry cannot be converted to CAP#1
        entries.add(new BonusEntry(UUID.randomUUID(), new Money(new BigDecimal("5.00"), "GBP")));
                    ^
  where CAP#1 is a fresh type-variable:
    CAP#1 extends LedgerEntry from capture of ? extends LedgerEntry
```

`[PROVE]` This is the same capture mechanism as 2.7.2, but now it is the *caller* who is stuck with it rather than the method's own implementer. Inside `FundsLedger`, `recentEntries` had full knowledge that the returned collection really holds `CashEntry` — that knowledge is simply thrown away by the return type. The caller receives `Collection<? extends LedgerEntry>`, and every `?` capture is independent, so the compiler has no basis for believing anything the caller constructs (a fresh `BonusEntry`, or anything else) matches the anonymous `CAP#1` the collection was captured as. The caller's only two options are to treat the result as read-only (fine for iteration, useless for the mutation this method's own field access would have supported) or write their own capture-helper method exactly as in 2.7.2 — which means the *caller* now has to solve a problem the *method author* was in a perfect position to solve once, for everyone, by choosing a better return type. That propagation — one sloppy signature generating a capture-helper obligation at every call site instead of one obligation at the declaration — is precisely why the rule is never a wildcard return type, no exceptions for "it felt more flexible."

The fix is either of two shapes, chosen by whether the caller needs to know the concrete element type:

```java
class FundsLedgerFixed {
    private final List<CashEntry> cashEntries = new ArrayList<>();

    Collection<CashEntry> recentEntries() {
        return cashEntries;
    }
}
```

or, if the method genuinely needs to stay generic over more than one `LedgerEntry` subtype, make the method itself generic and return the named type variable rather than a wildcard:

```java
class GenericLedgerView<T extends LedgerEntry> {
    private final List<T> entries;

    GenericLedgerView(List<T> entries) {
        this.entries = entries;
    }

    List<T> recentEntries() {
        return entries;
    }
}
```

Both give the caller a name — `CashEntry` in the first, the inferred `T` in the second — to write back into, with no capture involved.

No diagram: the manifest assigns this section none; the `javac` transcript above is the picture.

The one case people cite as a counter-example is `Class<?>` or a `List<?>` used as a genuinely opaque handle — and it is not actually an exception to this rule, because the reason a wildcard is fine there is exactly the reason it is not fine above: nobody receiving a `Class<?>` is expected to construct a new instance of its type argument or write an element into the list by name. The caller's only operations are ones that do not need the concrete type at all (`getName()`, iteration, size). The rule is not "never return a wildcard"; it is "never return a wildcard from a method whose caller needs to write something back typed to it" — and in ordinary QuizStakes domain code, almost every collection-returning method fails that test, because almost every caller eventually wants to add, remove, or replace an element.

`**Interview:**` "what's wrong with this method signature: `Collection<? extends LedgerEntry> recentEntries()`" — the one-line answer is that it forces every caller either to treat the result as read-only or to write their own wildcard-capture helper, because the anonymous capture type has no name the caller can spell; return the concrete parameterisation, or make the method itself generic.

> A wildcard in a return type erases the caller's ability to name what came back, forcing every caller into read-only use or their own capture-helper; return a concrete type argument, or make the method generic and return the named type variable.

## Supporting facts

### `? extends Object` versus a bare `<T>` declaration site

`javap` on `Collections.copy` prints `<T extends java.lang.Object>` for the method's own type-parameter declaration — that is not the wildcard rule from 2.7.3, it is the unrelated fact that every unbounded type parameter has an implicit `extends Object` written into the class file, regardless of whether the signature uses wildcards anywhere. No gotcha beyond not confusing the two `extends` — one is a wildcard bound, one is a type-parameter bound that is always there and rarely worth writing by hand.

> `<T>` and `<T extends Object>` are the same declaration; `javap` shows the bound explicitly because the class file always records it.

### `PECS` does not cover multiple wildcards interacting

2.7.1's `transfer` example already showed that two independently-declared `?`s in one signature capture independently and cannot be reconciled. PECS answers "which direction does this one wildcard face," not "do two wildcards in the same signature refer to the same type" — that second question is always answered by whether a named type variable was used instead, never by which wildcard direction was chosen. `**Pitfall:**` reaching for `Collection<? extends T> a, Collection<? extends T> b` believing the shared `T` name links them when `T` is itself unbound in that context — if `T` is not a declared type parameter of the enclosing method, `? extends T` at two sites is still two independent captures unless `T` is a real, single type parameter declared once on the method or class.

> Two wildcards never refer to the same unknown unless a real, single declared type parameter stands between them.

## Pitfalls

### "A wildcard parameter is less capable, so I should default to a type variable everywhere just to be safe"

**Wrong**

```java
class PostOverGeneric {
    static <T extends LedgerEntry> void post(Collection<T> source) {
        for (T entry : source) {
            System.out.println("posted " + entry.id());
        }
    }
}
```

This compiles and every existing call site keeps working — but it is not "safer." It adds a type variable `T` that appears exactly once, buys the caller nothing, and invites a future maintainer to add a second `T`-typed parameter under the false belief that `T` already links something.

**Right**

```java
class PostWithWildcard {
    static void post(Collection<? extends LedgerEntry> source) {
        for (LedgerEntry entry : source) {
            System.out.println("posted " + entry.id());
        }
    }
}
```

Same call sites accepted, same behaviour, one fewer name for the reader to track, and no unearned promise that a second parameter is coming.

**Why people believe it:** generic methods look more "generic" and therefore more general-purpose than a wildcard, and interview prep material that only shows `<T>` declarations without ever contrasting them against a wildcard reinforces the idea that naming the type is always the stronger move.

### "The swap-capture error means wildcards can't express read-then-write at all"

**Wrong**

```java
class SwapBad {
    static void swap(List<?> approvedWithdrawals, int i, int j) {
        approvedWithdrawals.set(i, approvedWithdrawals.set(j, approvedWithdrawals.get(i)));
    }
}
```

```
SwapBad.java:5: error: incompatible types: Object cannot be converted to CAP#1
```

Concluding from this that the public signature must abandon the wildcard and become generic throws away the exact simplicity 2.7.1 says to prefer.

**Right**

```java
class WithdrawalOrdering {
    static void swap(List<?> approvedWithdrawals, int i, int j) {
        swapHelper(approvedWithdrawals, i, j);
    }

    private static <T> void swapHelper(List<T> list, int i, int j) {
        list.set(i, list.set(j, list.get(i)));
    }
}
```

The public signature keeps its wildcard; only the private helper needs the name, because only the helper's body needs to prove the read and the write agree.

**Why people believe it:** the compiler error appears directly on the wildcard-typed body, so the obvious-looking fix is to remove the wildcard from wherever the error is pointing — but the error is pointing at the *implementation*, and the fix belongs one level down in a helper, not on the public signature itself.

### "Dropping `? extends`/`? super` on a JDK-style signature only matters for exotic subclass hierarchies"

**Wrong**

```java
interface NarrowStream<T> {
    <R> Stream<R> map(Function<T, R> mapper);
}

class MapBad {
    static void describe(NarrowStream<CashEntry> cashEntries) {
        Function<LedgerEntry, Money> extractAmount = LedgerEntry::amount;
        cashEntries.map(extractAmount);
    }
}
```

```
MapBad.java:19: error: method map in interface NarrowStream<T> cannot be applied to given types;
        cashEntries.map(extractAmount);
                   ^
  required: Function<CashEntry,R>
  found:    Function<LedgerEntry,Money>
```

The failing call uses `LedgerEntry::amount` — the single most ordinary method reference in this whole domain, not an exotic subclass hierarchy.

**Right**

Use the real `Stream<T>.map(Function<? super T, ? extends R> mapper)` as declared, or, when designing your own generic API, copy that exact shape:

```java
interface WideStream<T> {
    <R> Stream<R> map(Function<? super T, ? extends R> mapper);
}
```

Now `Function<LedgerEntry, Money>` is accepted for a `WideStream<CashEntry>`, because `? super CashEntry` admits `LedgerEntry`.

**Why people believe it:** the breakage only shows up when a caller reaches one level up the hierarchy from the exact element type, which most hand-written test cases never do because the test author already knows the concrete type and writes the function against it directly.

## Cheat sheet

| Situation | Choice | Real JDK example |
|---|---|---|
| Type named once, never returned | wildcard | `Collection.addAll(Collection<? extends E> c)` |
| Type named twice, must agree | named type variable | `Collections.<T>copy` (two `T`-typed lists via one type variable) |
| Type appears in the return | named type variable, never a wildcard | `Collections.copy`'s own `<T>` on the method, not on either list |
| Read-then-write on a wildcard-typed value inside the body | private generic helper (capture idiom) | `Collections.swap(List<?>, int, int)` |
| Parameter is a pure producer (you only read from it) | `? extends E` | `addAll`, `copy`'s `src` |
| Parameter is a pure consumer (you only write into it) | `? super E` | `copy`'s `dest`, `Comparator<? super E>` |
| Parameter both consumes and produces | both directions in one type | `Function<? super T, ? extends R>` |
| Opaque handle caller will never write into or name the element type of | wildcard return is fine | `Class<?>` |
| Everything else returned | concrete type or generic method, never a wildcard | `FundsLedger.recentEntries(): Collection<CashEntry>` |

## Self-test

**Q1.** You are about to write a method that iterates a collection of `LedgerEntry` values and never returns anything derived from them. Wildcard or type variable, and why?

<details><summary>Answer</summary>

Wildcard — `Collection<? extends LedgerEntry>`. The element type is named exactly once in the signature and never needs to match anything else, and it never appears in a return type, so by the decision rule a type variable would add a name the reader has to track for zero benefit. If a second parameter later needed to hold the *same* concrete type as this one, that would be the trigger to switch to a named type variable.

</details>

**Q2.** Why does `destination.addAll(source)` fail to compile when both `source` and `destination` are declared `Collection<?>`, even though at any real call site they obviously hold the same element type?

<details><summary>Answer</summary>

Because each `?` in the signature captures independently — `source`'s wildcard resolves to some `CAP#1` and `destination`'s to some `CAP#2`, and nothing in the signature states they are the same unknown. The compiler only ever sees two freshly-minted, unrelated capture variables, so `addAll` requires `Collection<? extends CAP#2>` and a `Collection<CAP#1>` doesn't satisfy that even though in practice they line up. Fixing it requires a single named type variable, `<T extends LedgerEntry> void transfer(Collection<T> source, Collection<T> destination)`, so both parameters are checked against the one `T`.

</details>

**Q3.** Walk through why `list.set(i, list.set(j, list.get(i)))` fails to compile when `list` is a `List<?>` parameter, even though the value clearly came out of that same list.

<details><summary>Answer</summary>

`list.get(i)` on a `List<?>` returns a value typed as the capture of that `?`, call it `CAP#1` — the compiler genuinely knows this is a `CAP#1`, but it has no name it can write down to carry that fact anywhere else. When that value is then passed to `list.set` at index `j`, `set` demands an argument of exactly `CAP#1` to satisfy the write, and the outer `set` at index `i` around it demands the same. Because `CAP#1` has no name usable outside its own expression, the compiler cannot prove the value flowing between the nested calls is the right type, even though at runtime it obviously is. Naming the type with a generic helper method typed `<T> void swapHelper(List<T> list, int i, int j)` fixes it because now there is one declared `T` the checker can actually track between the read and the write.

</details>

**Q4.** Why does `Collections.swap` keep the signature `swap(List<?> list, int i, int j)` in the real JDK instead of declaring a type parameter on the public method?

<details><summary>Answer</summary>

Because the caller of `swap` never needs to name the list's element type — by the 2.7.1 rule, a type appearing once with no cross-parameter agreement to enforce should be a wildcard. The type variable is only needed *inside* the implementation, to let the read and the write agree with each other, so the JDK puts it on a private generic helper method instead and keeps the public descriptor as `(Ljava/util/List;II)V` — confirmed by `javap` — with no type parameter at all.

</details>

**Q5.** In `Collections.copy(List<? super T> dest, List<? extends T> src)`, which parameter is the producer and which is the consumer, and what call would fail to compile if both were declared as plain `List<T>` instead?

<details><summary>Answer</summary>

`src` is the producer — it is only ever read from — so it gets `? extends T`. `dest` is the consumer — it is only ever written into — so it gets `? super T`. Without the wildcards, calling `copy` with `src` a `List<CashEntry>` and `dest` a `List<LedgerEntry>` would fail, because `List<CashEntry>` is not a `List<LedgerEntry>` under Java's invariance even though every `CashEntry` is a `LedgerEntry` and copying one into the other is perfectly sound.

</details>

**Q6.** A `Function<LedgerEntry, Money>` cannot be passed as the mapper to a hypothetical `Stream<CashEntry>.map(Function<T, R> mapper)`. What exactly changes if the parameter is declared `Function<? super T, ? extends R>` instead, and why does that fix it?

<details><summary>Answer</summary>

With the plain `Function<T, R>`, `T` is fixed to exactly `CashEntry`, so a `Function<LedgerEntry, Money>` is rejected because its input type parameter is `LedgerEntry`, not `CashEntry` — `javac` reports it cannot infer `R` because the argument doesn't match `Function<CashEntry, R>`. With `Function<? super T, ? extends R>`, the input position accepts any supertype of `CashEntry`, which includes `LedgerEntry`, and the output position accepts any subtype of the target `R`, which `Money` satisfies. That is the real `Stream.map` signature in the JDK, confirmed by `javap`, and it is why passing a supertype-typed function into a subtype's stream is completely ordinary code that just works.

</details>

**Q7.** Why is returning `Collection<? extends LedgerEntry>` from a method worse than accepting the same wildcard as a parameter?

<details><summary>Answer</summary>

As a parameter, the wildcard is resolved by whatever concrete argument the caller actually passes in — the caller always knows the real type going in, the method just doesn't need to name it. As a return type, there is no such anchor: the value comes back to the caller already erased to an anonymous capture that the caller cannot name, so the caller can only read it, never write into it, without writing their own capture-helper method. The problem that 2.7.2 solved once inside the method's own implementation gets pushed out to every caller instead.

</details>

**Q8.** Name the one situation where a wildcard return type is genuinely fine, and say precisely why it's different from `Collection<? extends LedgerEntry> recentEntries()`.

<details><summary>Answer</summary>

A `Class<?>` or a `List<?>` used purely as an opaque handle — where the caller is never expected to construct a new instance of the type argument or write an element into the collection by name. The difference is exactly the test the rule turns on: `recentEntries()`'s caller in this domain almost always wants to add, remove, or replace a `LedgerEntry`, which requires naming the captured type, whereas an opaque handle's only legitimate operations (iterate, query size, call `getName()`) never need that name at all.

</details>

## Open questions

None.

---

**Leaves covered:** 2.7.1, 2.7.2, 2.7.3, 2.7.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 525
