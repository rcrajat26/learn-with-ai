# 03 Java Core — Generic arrays and self-referential type bounds — INTERMEDIATE (§2.7, 2.7.8–2.7.10)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Type tokens and generic reflection](02a-type-tokens-and-generic-reflection.md) · Next: [Inference and the limits of generics](02c-inference-and-generic-limits.md)

This file covers the two ways a generic class fakes an array of its type parameter, the exact
failure you get when the cheaper fake escapes, and the self-referential bound `<T extends
Builder<T>>` that lets a fluent builder hierarchy return the right subclass from an inherited
method. It hands off *why* `new T[n]` is illegal and what reifiable means to
`01a-erasure-and-its-consequences.md` and the deep `ArrayList.elementData` source walk to
`03b-internals-reifiable-types-and-generic-arrays.md`; it hands off the array-covariance store
check itself to `../arrays/01a-covariance-and-mutability.md`; it hands off `@SuppressWarnings`
scoping discipline to `01c-raw-types-and-unchecked-warnings.md`, the grammar of a recursive bound
to `01d-recursive-bounds-and-heterogeneous-containers.md`, and `Class<T>` token mechanics to
`02a-type-tokens-and-generic-reflection.md`. Every claim below was compiled and run on Oracle JDK
21.0.7 (`21.0.7+8-LTS-245`); no output here is reconstructed from memory.

## 1. The two ways to fake a generic array (2.7.8)

Picture what `ArrayList<CashEntry>` actually holds at runtime: not a `CashEntry[]`, but a plain
`Object[]` that the class casts back to what it needs at the boundary. Every generic container in
the JDK does some version of this, because `new T[n]` cannot be written at all — the JVM has to
know a concrete component type to allocate an array, and by the time the class file exists, `T`
has been erased. There are exactly two ways to manufacture the array anyway, and the difference
between them is *where the truth about the component type lives*: nowhere (you lie and hope), or
in a `Class<T>` token the caller hands you.

### Why it exists

Before generics (Java 1.4 and earlier), a container that needed array storage typed it as
`Object[]` and every caller cast on the way out — `(String) list.get(i)` — with no compiler help
at all. Generics were supposed to move that cast inside the library and make it type-checked at
the call site. But the library still needs *some* array to back a resizable buffer, a `toArray()`
result, or a fixed-capacity ring — and erasure means the class file never had a concrete `T` to
allocate against. So the two idioms below both exist to answer the same question forced on every
generic container: *how do I get an array-shaped piece of storage for a type I don't know at
runtime?*

### The mechanism

**Way one — the unchecked cast.** Declare the field `T[]`, allocate `Object[]`, and cast:

```java
final class WayOneBuffer<T> {
    // Way one: cast an Object[] to T[] and hide the lie behind a narrow,
    // documented @SuppressWarnings. The runtime array is Object[]; only the
    // declared field type is T[]. Erasure means javac cannot tell the
    // difference at this point, so it trusts the cast.
    @SuppressWarnings("unchecked") // safe: only this.add(T) ever stores into
                                    // slots, so every element really is a T
    private final T[] entries = (T[]) new Object[8];
    private int size;

    void add(T entry) {
        entries[size++] = entry;
    }

    T get(int index) {
        return entries[index];
    }

    int size() {
        return size;
    }

    Class<?> runtimeComponentType() {
        return entries.getClass().getComponentType();
    }
}
```

`[PROVE]` — but this only compiles *and runs* cleanly for an **unbounded** `T`. The cast `(T[])
new Object[8]` compiles to a `checkcast` whose target is the erasure of `T[]`, and the erasure of
an unbounded `T` is `Object`, so the erasure of `T[]` is `Object[]` — the checkcast becomes a
no-op against a value that already has exactly that type, and `javac` elides it entirely.
`javap -c -p` on the compiled constructor above, on JDK 21.0.7, shows no `checkcast` at all:

```
WayOneBuffer();
  Code:
     0: aload_0
     1: invokespecial #1   // Method java/lang/Object."<init>":()V
     4: aload_0
     5: bipush        8
     7: anewarray     #2   // class java/lang/Object
    10: putfield      #7   // Field entries:[Ljava/lang/Object;
    13: return
```

Change the class to `WayOneBuffer<T extends LedgerEntry>` — a bound most engineers would reach
for without a second thought, since our domain's buffers should only ever hold ledger entries —
and the erasure of `T[]` becomes `LedgerEntry[]`, not `Object[]`. Now the same cast really has
work to do, and `javap` on the constructor shows the inserted `checkcast`:

```
BoundedWayOneFails();
  Code:
     0: aload_0
     1: invokespecial #1   // Method java/lang/Object."<init>":()V
     4: aload_0
     5: bipush        8
     7: anewarray     #2   // class java/lang/Object
    10: checkcast     #7   // class "[LLedgerEntry;"
    13: putfield      #9   // Field entries:[LLedgerEntry;
    16: return
```

Running `new BoundedWayOneFails<CashEntry>()` throws immediately, before a single element is ever
stored — an actual `Object[]` is never assignable to `LedgerEntry[]`, because array types carry
their exact runtime component type, unlike a generic's fully-erased type parameter:

```
Exception in thread "main" java.lang.ClassCastException: class [Ljava.lang.Object; cannot be
cast to class [LLedgerEntry; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap';
[LLedgerEntry; is in unnamed module of loader 'app')
	at BoundedWayOneFails.<init>(BoundedWayOneFails.java:10)
	at BoundedWayOneFails.main(BoundedWayOneFails.java:14)
```

**Insight:** the classic "cast `Object[]` to `T[]`" idiom (Joshua Bloch's `Stack<E>` in *Effective
Java*) only ever works because that book's `E` is unbounded. The moment your type parameter has
a real upper bound — which a `LedgerEntry`-only buffer obviously wants — the identical line stops
being merely unchecked and becomes permanently broken, and it fails at construction, not at first
use. That is why way one, above, is deliberately written with unbounded `T`, and why way two below
is the one that accepts the bound.

**Way two — the reflective array with a real token.** Take a `Class<T>` at construction and let
`java.lang.reflect.Array.newInstance` allocate the real array:

```java
final class WayTwoBuffer<T extends LedgerEntry> {
    // Way two: the caller hands in a Class<T> token at construction, and
    // Array.newInstance uses it to allocate an array whose runtime component
    // type is the real T, not Object. No @SuppressWarnings is needed on the
    // field's meaning - the cast below is checked by the JVM at the
    // allocation site, not merely trusted by javac.
    private final T[] entries;
    private int size;

    @SuppressWarnings("unchecked") // Array.newInstance returns Object; the
                                    // cast to T[] is honest because
                                    // componentType really is T's class
    WayTwoBuffer(Class<T> componentType, int capacity) {
        this.entries = (T[]) Array.newInstance(componentType, capacity);
    }

    void add(T entry) {
        entries[size++] = entry;
    }

    T get(int index) {
        return entries[index];
    }

    int size() {
        return size;
    }

    Class<?> runtimeComponentType() {
        return entries.getClass().getComponentType();
    }
}
```

`Array.newInstance` is confirmed on JDK 21.0.7 by the `javap` of the constructor above:
`invokestatic java/lang/reflect/Array.newInstance:(Ljava/lang/Class;I)Ljava/lang/Object;` — it
takes a `Class<?>` and an `int`, and returns bare `Object`, which is why the constructor still
needs an unchecked cast — but this cast succeeds, because the object it is casting really is a
`LedgerEntry[]` (in fact a `CashEntry[]`) at the JVM level, not a disguised `Object[]`.

`[PROVE]` — the difference is invisible in either class's source and only shows up at the boundary.
Constructing `new WayOneBuffer<CashEntry>()` and `new WayTwoBuffer<>(CashEntry.class, 8)`, adding
one `CashEntry` to each, then printing `entries.getClass().getComponentType()` from inside each
class gives two different answers on the same JDK, from what looks like the same declared field
type:

```
WayOneBuffer:  component type=class java.lang.Object
WayTwoBuffer:  component type=class CashEntry
```

No diagram: the manifest assigns this section none; the two `javap` excerpts above are the
picture — one has no `checkcast` because there is nothing to check, the other has a real one that
succeeds because the reflective allocation already produced the right shape.

| | `(T[]) new Object[n]` | `Array.newInstance(componentType, n)` |
|---|---|---|
| Runtime component type | `Object` (or the bound's erasure — and then it throws, see above) | the real `T` (`CashEntry`, `BonusEntry`, …) |
| Can the array safely escape as `T[]`? | No — see §2 | Yes, as long as `componentType` was accurate |
| Extra cost per construction | none | one reflective call to `Array.newInstance` |
| Caller must supply | nothing | a `Class<T>` token |
| Works with a bounded `T`? | only if the bound is `Object` (i.e. `T` unbounded) | yes, any bound |

**Where the JDK itself uses each.** `ArrayList` keeps a plain `Object[] elementData` field — it
never even attempts `(E[])`, it casts to `E` only at the point of `get()` — which sidesteps the
bound question entirely because `elementData` is never declared as `E[]`. `Arrays.copyOf(T[],
int)` and `Collection.toArray(T[])`, by contrast, use the array-typed / reflective route, because
their contract promises the caller a real, narrowly-typed array back. The full
`ArrayList.elementData` source walk belongs to `03b-internals-reifiable-types-and-generic-arrays.md`
— one line here is enough: it is evidence that even the JDK's own most-used collection avoids
declaring a field `E[]` at all, for exactly the reason proven above.

No gotcha beyond the one already proven: the bound silently changes which idiom is even legal to
attempt, and that is the whole reason this section exists.

> A generic class cannot allocate `new T[n]`; it can only manufacture an array shaped like `T[]`
> by casting a same-shaped `Object[]` (which only survives an unbounded `T`) or by asking a real
> `Class<T>` token to allocate the genuine array through `Array.newInstance`.

## 2. The escaping generic array: `ClassCastException` versus `ArrayStoreException` (2.7.9)

Way one from §1 is not merely inelegant — it is a ticking `ClassCastException` the moment the
array is allowed to leave the class that built it. The field is declared `T[]`; the object behind
it is `Object[]`; as long as every read stays inside the class, nothing outside ever asks the JVM
to check the lie. The instant a caller receives that array and assigns it to a narrower type, the
lie is checked, and it fails — but at the *caller's* line, with no cast visible in the caller's
own source.

### Why it exists

This is not a design flaw so much as the direct, unavoidable consequence of §1: any class that
uses the unchecked-cast idiom for a bounded-looking field and then hands that field to the outside
world has made a promise (`T[]`) that its own storage cannot keep. Understanding exactly which
exception fires, and where, is the difference between debugging this in thirty seconds versus
an afternoon, because the stack trace looks nothing like the source code that caused it.

### The mechanism

Take a container that exposes its internal array — a `toArray()` returning `T[]`, in the same
unbounded-`T`, way-one shape as §1's `WayOneBuffer` (renamed here for the domain: a
`ReservationBuffer<T>` of stake reservations):

```java
final class ReservationBuffer<T> {
    @SuppressWarnings("unchecked")
    private final T[] entries = (T[]) new Object[4];
    private int size;

    void add(T entry) {
        entries[size++] = entry;
    }

    T get(int index) {
        return entries[index];
    }

    T[] toArray() {
        return entries;
    }

    Object rawArray() {
        return entries;
    }
}
```

**Failure 1 — the escaping cast.** A caller with `T` inferred as `CashEntry` calls `toArray()` and
assigns the result to a `CashEntry[]`:

```java
ReservationBuffer<CashEntry> buffer = new ReservationBuffer<>();
buffer.add(new CashEntry(UUID.randomUUID()));
CashEntry[] cashEntries = buffer.toArray();
System.out.println("unreachable: " + cashEntries.length);
```

`[PROVE]` — `toArray()`'s declared return type is `T[]`, erased to `Object[]`; the *caller's*
static type for the assignment is `CashEntry[]`, so `javac` inserts a `checkcast` at the call
site, in the caller's own bytecode, not inside `toArray()`. `javap -c -p` on `main` confirms it:

```
22: aload_1
23: invokevirtual #25   // Method ReservationBuffer.toArray:()[Ljava/lang/Object;
26: checkcast     #29   // class "[LCashEntry;"
29: astore_2
```

Running it on JDK 21.0.7 throws at that exact call site — line 35 of the frozen listing
(`CashEntry[] cashEntries = buffer.toArray();`), not anywhere inside `ReservationBuffer`:

```
Exception in thread "main" java.lang.ClassCastException: class [Ljava.lang.Object; cannot be
cast to class [LCashEntry; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap';
[LCashEntry; is in unnamed module of loader 'app')
	at EscapeCce.main(EscapeCce.java:35)
```

**Pitfall:** the wrong belief is "this is an `ArrayStoreException`, because arrays are involved."
The symptom is a `ClassCastException`, not `ArrayStoreException`, and it fires at an assignment
that has no visible cast in its own source. The fix is to never let a way-one array escape typed
as `T[]` at all — see the table below.

**Failure 2 — the polluted write, and which exception you actually get.** This is the other half
of the leaf, and it depends entirely on *which way* built the array. Take the same
`ReservationBuffer<T>` (way one, backed by a genuine `Object[]`), expose the raw array, and let a
caller write the wrong subtype into it:

```java
ReservationBuffer<CashEntry> buffer = new ReservationBuffer<>();
buffer.add(new CashEntry(UUID.randomUUID()));
buffer.add(new CashEntry(UUID.randomUUID()));
Object[] raw = (Object[]) buffer.rawArray();
raw[1] = new BonusEntry(UUID.randomUUID());
System.out.println("write succeeded, no ArrayStoreException");
CashEntry polluted = buffer.get(1);
System.out.println("unreachable: " + polluted);
```

`[PROVE]` — an `Object[]` accepts any `Object` at every array-store slot, so `raw[1] = new
BonusEntry(UUID.randomUUID())` succeeds with **no** `ArrayStoreException`; the array is silently polluted. The
failure surfaces later, at an unrelated read, when `buffer.get(1)` is assigned to a `CashEntry`
variable and `javac`'s checkcast at that assignment finds a `BonusEntry` instead:

```
write succeeded, no ArrayStoreException
Exception in thread "main" java.lang.ClassCastException: class BonusEntry cannot be cast to
class CashEntry (BonusEntry and CashEntry are in unnamed module of loader 'app')
	at EscapePollution.main(EscapePollution.java:35)
```

Now repeat the identical write against a **way-two** buffer — `Array.newInstance(CashEntry.class,
4)`, so the runtime array really is a `CashEntry[]`:

```java
TokenedBuffer<CashEntry> buffer = new TokenedBuffer<>(CashEntry.class, 4);
buffer.add(new CashEntry(UUID.randomUUID()));
buffer.add(new CashEntry(UUID.randomUUID()));
Object[] raw = (Object[]) buffer.rawArray();
raw[1] = new BonusEntry(UUID.randomUUID());
System.out.println("unreachable: write should have thrown");
```

`[PROVE]` — here the write itself fails, immediately, with `ArrayStoreException`, because the
array-store check (owned in full by `../arrays/01a-covariance-and-mutability.md`) runs on every
reference-array write and compares the value's class against the array's *actual* runtime
component type — `CashEntry`, not `Object`:

```
Exception in thread "main" java.lang.ArrayStoreException: BonusEntry
	at EscapeAse.main(EscapeAse.java:34)
```

So the two dispositions are not interchangeable and do not both apply to the same array: a
way-one (`Object[]`-backed) array pollutes silently and blows up at a later, unrelated read as
`ClassCastException`; a way-two (`Array.newInstance`-backed) array fails loudly and immediately,
at the write, as `ArrayStoreException`. The second is strictly better for debugging — it points
at the actual bug — which is itself an argument for way two beyond honesty about the component
type.

| Fix | Mechanism | Cost |
|---|---|---|
| Never let the array escape | return a `List<T>` view (`List.of(entries)` or an unmodifiable wrapper) instead of `T[]` | one allocation for the view, no array-typing risk at all |
| Use `Array.newInstance` with a token | the runtime array is honestly `T[]`, so both escape and cross-write fail the *useful* way | caller must supply `Class<T>`; reflective allocation cost |
| Take a `T[]` from the caller | mirror `Collection.toArray(T[] a)`'s real signature — `<T> T[] toArray(T[] a)` — and either fill the caller's array or allocate a same-typed one via `java.lang.reflect.Array` if it's too small | caller must have a `T[]` to hand you in the first place |

That third row is *why* `toArray(T[])` has the signature it does: it is the one way to get an
honestly-typed array out of a generic collection without either the class holding a `Class<T>`
token forever or reflectively allocating on every call — the caller's own array supplies the
component type for free.

**Interview:** "you have a generic class with a `T[]` field — what's wrong with it?" One-line
answer: nothing, as long as the field never leaves the class and `T` is unbounded; the moment
either condition breaks — a bound is added, or the array is returned/exposed — it becomes either
a `ClassCastException` waiting at the boundary or (if built via `Array.newInstance`) a correctly
loud `ArrayStoreException` at the point of misuse.

> A `T[]`-declared field backed by an actual `Object[]` behaves correctly only while it never
> crosses a method boundary that narrows its type; the moment it does, the checkcast that erasure
> deferred finally runs, and it runs at the caller's line, not yours.

## 3. Generic bounds and self-referential types: the builder pattern with `<T extends Builder<T>>` (2.7.10)

`<T extends Builder<T>>` is a class saying "my subclass will tell me its own name" — this is the
Curiously Recurring Template Pattern (CRTP), borrowed from C++ template metaprogramming into
Java's generics. The payoff: an inherited setter can return the *subclass* type instead of the
declaring superclass's type, so a fluent chain through an inherited method keeps compiling all
the way down to the concrete builder.

### Why it exists

Without a self-type, an abstract builder's setters can only be declared to return the abstract
builder itself — that is the only type the superclass knows about. A fluent chain that calls a
base setter and then a subclass-only setter breaks, because the compile-time type after the base
setter has already forgotten which subclass it started from:

```java
abstract class PlainBuilder {
    protected UUID id = UUID.randomUUID();
    protected Money amount;

    PlainBuilder amount(Money amount) {
        this.amount = amount;
        return this;
    }
}

final class PlainCardWithdrawalBuilder extends PlainBuilder {
    private String cardLast4;

    PlainCardWithdrawalBuilder cardLast4(String cardLast4) {
        this.cardLast4 = cardLast4;
        return this;
    }

    WithdrawalTransaction build() {
        return new WithdrawalTransaction(id, amount, "CARD", cardLast4);
    }
}
```

`[PROVE]` — chaining `.amount(money)` before `.cardLast4("4242")` fails on the real `javac`, because
`amount()`'s declared return type is `PlainBuilder`, which has never heard of `cardLast4`:

```
PlainBuilderProblem.java:35: error: cannot find symbol
                .cardLast4("4242")
                ^
  symbol:   method cardLast4(String)
  location: class PlainBuilder
1 error
```

### The mechanism

`[BUILD]` The fix: the abstract builder parameterises itself over its own eventual subclass, and
every inherited setter returns through a single `self()` method instead of `this` directly:

```java
abstract class Builder<T extends Builder<T>> {
    protected UUID id = UUID.randomUUID();
    protected Money amount;

    @SuppressWarnings("unchecked") // sound only if every subclass declares
                                    // itself as its own T; nothing in the
                                    // language enforces that
    protected T self() {
        return (T) this;
    }

    T amount(Money amount) {
        this.amount = amount;
        return self();
    }
}

final class CardWithdrawalBuilder extends Builder<CardWithdrawalBuilder> {
    private String cardLast4;

    CardWithdrawalBuilder cardLast4(String cardLast4) {
        this.cardLast4 = cardLast4;
        return self();
    }

    WithdrawalTransaction build() {
        return new WithdrawalTransaction(id, amount, "CARD", cardLast4);
    }
}
```

```java
WithdrawalTransaction transaction = new CardWithdrawalBuilder()
        .amount(new Money(BigDecimal.valueOf(180), Currency.getInstance("USD")))
        .cardLast4("4242")
        .build();
System.out.println(transaction);
```

Run on JDK 21.0.7:

```
WithdrawalTransaction[id=ea1ba7f6-ac03-4c9a-baca-7dce52dd98f3, amount=Money[amount=180,
currency=USD], rail=CARD, cardLast4=4242]
```

The base setter `amount()` now returns `T`, which `CardWithdrawalBuilder` has bound to itself, so
`cardLast4()` is visible right after the call to `amount()` and the chain compiles and runs.

No diagram: the manifest assigns this section none; the compile error above and the compiling fix
below it are the picture.

**Insight:** the `(T) this` cast inside `self()` is, at the bytecode level, almost always a
no-op. `T`'s bound is `Builder<T>`, whose erasure is the raw `Builder`, and `this` is always
already a `Builder` — so `javap` on `self()` shows a bare `aload_0; areturn`, no `checkcast` at
all. The real enforcement point is wherever a caller narrows the return type to a *concrete*
class, e.g. `CardWithdrawalBuilder.cardLast4()`, whose own `javap` shows `invokevirtual
self:()LBuilder;` immediately followed by `checkcast #8 // class CardWithdrawalBuilder` before
the value is returned. That checkcast, not the one inside `self()`, is what would catch a lying
subclass.

**The honesty this pattern costs.** `[PROVE]` — nothing in the language stops a subclass from
declaring the wrong type argument. A second builder can extend `Builder<CardWithdrawalBuilder>`
instead of `Builder<BankWithdrawalBuilder>` — the bound `T extends Builder<T>` is still satisfied,
because `CardWithdrawalBuilder` really does extend `Builder<CardWithdrawalBuilder>`; the compiler
has no way to know that is the *wrong* `T` for this particular subclass:

```java
// Lies about its own type: declares itself a Builder<CardWithdrawalBuilder>
// instead of Builder<BankWithdrawalBuilder>. Nothing in the language stops
// this - the bound T extends Builder<T> is satisfied because
// CardWithdrawalBuilder really does extend Builder<CardWithdrawalBuilder>.
final class BankWithdrawalBuilder extends Builder<CardWithdrawalBuilder> {
    private String sortCode;

    BankWithdrawalBuilder sortCode(String sortCode) {
        this.sortCode = sortCode;
        return this;
    }
}
```

```java
BankWithdrawalBuilder builder = new BankWithdrawalBuilder();
builder.sortCode("12-34-56");
CardWithdrawalBuilder result =
        builder.amount(new Money(BigDecimal.valueOf(260), Currency.getInstance("USD")));
System.out.println("unreachable: " + result);
```

Compiles cleanly, and throws at the first point a caller narrows the result to the concrete type
`BankWithdrawalBuilder` lied about:

```
Exception in thread "main" java.lang.ClassCastException: class BankWithdrawalBuilder cannot be
cast to class CardWithdrawalBuilder (BankWithdrawalBuilder and CardWithdrawalBuilder are in
unnamed module of loader 'app')
	at CrtpBuilderLie.main(CrtpBuilderLie.java:54)
```

Joshua Bloch's *Effective Java* covers this ground under **Item 2: *Consider a builder when
faced with many constructor parameters***, and names the technique used above the "simulated
self-type" idiom — the language has no true `Self` type, so this pattern simulates one through
the recursive bound. (The item-number mapping for this edition is on this project's standing
unverified list; the title is what to cite if a number is challenged.)

One line on when to reach for this at all in Java 21: records plus a `with`-style copy method
remove the need for a builder in many cases — a record with a handful of required fields and no
validation is simpler as a record with copy-and-modify helpers than as a CRTP builder hierarchy.
A builder is still the right tool once there are many optional fields, defaulting, or validation
that has to run at `build()` time. Guide `04 Modern Java` owns records as a language feature.

Reading a recursive bound like `<T extends Comparable<? super T>>` left to right, and the `Object
&` intersection form `Collections.max` actually declares, is
`01d-recursive-bounds-and-heterogeneous-containers.md`'s grammar to own; this section only owns
the builder *application* of that same recursive-bound machinery.

> `<T extends Builder<T>>` lets a superclass method return the caller's own subclass type by
> routing every return through an unchecked `self()` cast — sound in practice because every
> subclass conventionally names itself as `T`, not because the compiler can verify it.

## Supporting facts

### `Collection.toArray(T[])`'s real signature

`<T> T[] toArray(T[] a)` — the caller supplies the array, and its component type (not any
`Class<T>` field on the collection) is what lets the implementation return an honestly-typed
array without ever calling `Array.newInstance` itself when the given array is already large
enough. If `a` is too small, the real implementations (e.g. `ArrayList.toArray(T[])`) allocate a
new array of the same runtime type as `a` via `java.lang.reflect.Array.newInstance(a.getClass()
.getComponentType(), size)` — the caller's array is the token.

> `toArray(T[] a)` exists so a generic collection can hand back a correctly-typed array without
> ever holding a `Class<T>` itself.

### `ArrayList` never declares an `E[]` field

`ArrayList.elementData` is `Object[]`, not `E[]` — it sidesteps both idioms in §1 by never
promising the narrower type in its field declaration at all, and only performing the unchecked
cast to `E` inside `get(int)`, one call at a time. The full source walk is
`03b-internals-reifiable-types-and-generic-arrays.md`'s to own.

> The simplest way to avoid the generic-array problem is to never type the backing field `T[]` in
> the first place.

## Pitfalls

### "`(T[]) new Object[n]` is always safe once it compiles with only a warning"

**Wrong**

```java
final class BoundedWayOneFails<T extends LedgerEntry> {
    @SuppressWarnings("unchecked")
    private final T[] entries = (T[]) new Object[8];
}

new BoundedWayOneFails<CashEntry>();
```

```
Exception in thread "main" java.lang.ClassCastException: class [Ljava.lang.Object; cannot be
cast to class [LLedgerEntry; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap';
[LLedgerEntry; is in unnamed module of loader 'app')
	at BoundedWayOneFails.<init>(BoundedWayOneFails.java:10)
```

**Right**

```java
final class WayTwoBuffer<T extends LedgerEntry> {
    private final T[] entries;

    @SuppressWarnings("unchecked")
    WayTwoBuffer(Class<T> componentType, int capacity) {
        this.entries = (T[]) Array.newInstance(componentType, capacity);
    }
}
```

Use `Array.newInstance` with a real `Class<T>` whenever `T` carries a bound narrower than
`Object` — which is nearly every field you would actually declare `T extends LedgerEntry` for.

**Why people believe it:** the unbounded-`T` version of this exact idiom (Bloch's `Stack<E>`)
really does compile and run with nothing worse than an unchecked warning, and most engineers
copy the shape without noticing that adding a bound changes what the erased cast target is.

### "A generic method returning `T[]` behaves like one returning `List<T>`"

**Wrong**

```java
ReservationBuffer<CashEntry> buffer = new ReservationBuffer<>();
buffer.add(new CashEntry(UUID.randomUUID()));
CashEntry[] cashEntries = buffer.toArray();
```

```
Exception in thread "main" java.lang.ClassCastException: class [Ljava.lang.Object; cannot be
cast to class [LCashEntry; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap';
[LCashEntry; is in unnamed module of loader 'app')
	at EscapeCce.main(EscapeCce.java:35)
```

**Right**

```java
List<T> toList() {
    return List.copyOf(Arrays.asList(entries).subList(0, size));
}
```

Return a `List<T>` view instead of `T[]`; `List<T>`'s type argument is erased uniformly and
carries no runtime component-type promise the way an array does, so there is nothing for a
narrowing assignment to fail against.

**Why people believe it:** `List<T>.get(int)` and `T[]`'s indexing both read as "get me a `T`",
and nothing in ordinary usage exercises the one case — an array assigned to a narrower array
type — where the two stop being equivalent.

### "Writing the wrong subtype into a shared generic array always throws `ArrayStoreException`"

**Wrong**

```java
ReservationBuffer<CashEntry> buffer = new ReservationBuffer<>();
buffer.add(new CashEntry(UUID.randomUUID()));
buffer.add(new CashEntry(UUID.randomUUID()));
Object[] raw = (Object[]) buffer.rawArray();
raw[1] = new BonusEntry(UUID.randomUUID());
CashEntry polluted = buffer.get(1);
```

```
write succeeded, no ArrayStoreException
Exception in thread "main" java.lang.ClassCastException: class BonusEntry cannot be cast to
class CashEntry (BonusEntry and CashEntry are in unnamed module of loader 'app')
	at EscapePollution.main(EscapePollution.java:35)
```

**Right**

```java
TokenedBuffer<CashEntry> buffer = new TokenedBuffer<>(CashEntry.class, 4);
buffer.add(new CashEntry(UUID.randomUUID()));
buffer.add(new CashEntry(UUID.randomUUID()));
Object[] raw = (Object[]) buffer.rawArray();
raw[1] = new BonusEntry(UUID.randomUUID());
```

```
Exception in thread "main" java.lang.ArrayStoreException: BonusEntry
	at EscapeAse.main(EscapeAse.java:34)
```

Build the buffer with `Array.newInstance` and a real `Class<T>` token so the runtime array
genuinely is `CashEntry[]`; only then does the JVM's per-write array-store check have a real
component type to enforce, and the failure moves from a silent, delayed pollution to an
immediate, loud one at the actual bad write.

**Why people believe it:** `ArrayStoreException` is the textbook example for array covariance,
so it is easy to assume any array misuse gets that exception — without noticing that a way-one
buffer's backing array genuinely is `Object[]`, which accepts anything by definition.

### "`<T extends Builder<T>>` guarantees `self()` returns the right subclass"

**Wrong**

```java
final class BankWithdrawalBuilder extends Builder<CardWithdrawalBuilder> {
    BankWithdrawalBuilder sortCode(String sortCode) { this.sortCode = sortCode; return this; }
}

CardWithdrawalBuilder result =
        new BankWithdrawalBuilder().amount(new Money(BigDecimal.valueOf(260), Currency.getInstance("USD")));
```

```
Exception in thread "main" java.lang.ClassCastException: class BankWithdrawalBuilder cannot be
cast to class CardWithdrawalBuilder (BankWithdrawalBuilder and CardWithdrawalBuilder are in
unnamed module of loader 'app')
	at CrtpBuilderLie.main(CrtpBuilderLie.java:54)
```

**Right**

Nothing in the language forbids this, so treat the self-type as a documented contract, not a
compiler-checked one: keep builder hierarchies one level deep, make concrete builders `final`,
and give each one exactly one, unambiguous `extends Builder<ThisExactClass>` declaration.

**Why people believe it:** the bound reads like a guarantee ("`T` must be a `Builder<T>`"), but
it only constrains what `T` looks like in isolation — it has no way to see which concrete class
is doing the extending, so a sibling class can supply a syntactically valid but semantically
wrong `T`.

## Cheat sheet

| Question | Answer |
|---|---|
| Two ways to fake a `T[]`? | `(T[]) new Object[n]` (unbounded `T` only) vs `Array.newInstance(Class<T>, n)` |
| Which one is honest about the runtime component type? | `Array.newInstance` — `(T[]) new Object[n]` is always secretly `Object[]` (or throws, if bounded) |
| Does `(T[]) new Object[n]` work for `T extends LedgerEntry`? | No — throws `ClassCastException` at construction, not at use |
| Escaping way-one array assigned to a narrower array type? | `ClassCastException` at the caller's assignment line |
| Wrong-subtype write into a way-one (`Object[]`) array? | Silent — no `ArrayStoreException`; fails later as `ClassCastException` at read |
| Wrong-subtype write into a way-two (`Array.newInstance`) array? | Immediate `ArrayStoreException` at the write |
| Safest fix for an escaping generic array? | Return `List<T>`, not `T[]` |
| `Collection.toArray(T[])` signature | `<T> T[] toArray(T[] a)` — caller's array supplies the component type |
| `<T extends Builder<T>>` — what does it buy? | inherited setters return the concrete subclass, not the abstract superclass |
| Is the self-type checked by the compiler? | No — `self()`'s cast is unchecked; a sibling subclass can lie about its own `T` |
| Effective Java reference | Item 2: *Consider a builder when faced with many constructor parameters* — "simulated self-type" idiom |

## Self-test

**Q1.** Why does `(T[]) new Object[n]` compile with only an unchecked warning for an unbounded
`T`, but throw a `ClassCastException` immediately for `T extends LedgerEntry`?

<details><summary>Answer</summary>

The cast compiles to a `checkcast` whose target is the erasure of `T[]`. For unbounded `T` that
erasure is `Object[]`, and casting an `Object[]` to `Object[]` is a no-op that `javac` elides
entirely — nothing runs, nothing can fail. For `T extends LedgerEntry`, the erasure of `T[]` is
`LedgerEntry[]`, so the cast becomes a real `checkcast` against a value that is genuinely
`Object[]` at runtime — and an `Object[]` instance is never assignable to `LedgerEntry[]`, because
arrays carry their exact runtime component type, so the cast fails the moment it executes, which
is at construction, before anything is stored.

</details>

**Q2.** A container's `toArray()` is declared to return `T[]`, backed internally by `(T[]) new
Object[n]`. A caller assigns the result to a `CashEntry[]` variable. What exception fires, and
where — inside `toArray()`, or at the caller?

<details><summary>Answer</summary>

`ClassCastException`, and it fires at the caller's assignment line, not inside `toArray()`.
`toArray()`'s erased return type is `Object[]`; the caller's static type for the assignment is
`CashEntry[]`, so `javac` inserts the `checkcast` at the call site in the caller's own bytecode.
`toArray()` itself never touches a narrower type and returns successfully every time.

</details>

**Q3.** Two generic buffers both expose their backing array as `Object[]`, and both have a
`BonusEntry` written into a slot meant for `CashEntry`. One buffer was built with `(T[]) new
Object[n]`, the other with `Array.newInstance(CashEntry.class, n)`. Which one throws
`ArrayStoreException` at the write, and which one pollutes silently?

<details><summary>Answer</summary>

The `Array.newInstance(CashEntry.class, n)` buffer throws `ArrayStoreException` immediately at
the write, because its backing array genuinely has runtime component type `CashEntry`, and the
JVM's per-write array-store check rejects a `BonusEntry` against it. The `(T[]) new Object[n]`
buffer's backing array is genuinely `Object[]`, which accepts any object at every slot, so the
write succeeds silently; the pollution only surfaces later, as a `ClassCastException`, at whatever
unrelated read first assigns that slot's value to a `CashEntry` variable.

</details>

**Q4.** What is the actual, documented signature of `Collection.toArray(T[])`, and why does it
take an array parameter at all instead of just returning `T[]` directly?

<details><summary>Answer</summary>

`<T> T[] toArray(T[] a)`. It takes the array so the caller supplies the true component type —
if `a` is big enough, the implementation fills and returns it directly; if not, the
implementation allocates a new array of `a`'s own runtime component type, typically via
`Array.newInstance(a.getClass().getComponentType(), size)`. This lets a generic collection hand
back an honestly-typed array without ever holding a `Class<T>` token itself.

</details>

**Q5.** Why does an abstract builder need a self-type parameter (`<T extends Builder<T>>`) at
all — what breaks without it?

<details><summary>Answer</summary>

Without it, every setter declared on the abstract builder can only return the abstract builder's
own type, because that is the only type the superclass knows about. Chaining a base setter and
then a subclass-only setter fails to compile, because the compile-time type after the base setter
call is the abstract superclass, which has never heard of the subclass method. `javac` reports
"cannot find symbol" for the subclass method, located against the superclass.

</details>

**Q6.** Inside `Builder<T extends Builder<T>>`'s `self()` method, is the cast `(T) this` checked
by the JVM at runtime? What does `javap` actually show?

<details><summary>Answer</summary>

Almost always no. `T`'s bound is `Builder<T>`, whose erasure is the raw `Builder`, and `this`
inside `self()` is always already typed `Builder`, so the erased cast target matches the value's
static type exactly and `javac` elides the `checkcast`. `javap` on `self()` shows a bare
`aload_0; areturn` — no cast instruction at all. The real enforcement point is wherever a caller
or subclass narrows the return of an inherited builder method to a *concrete* class; that call
site does get a `checkcast`, and that is where a lying subclass's mistake would actually surface.

</details>

**Q7.** Can a second builder subclass declare `extends Builder<CardWithdrawalBuilder>` by
mistake, and if so, does the compiler catch it?

<details><summary>Answer</summary>

Yes, and no. The bound `T extends Builder<T>` only requires that whatever `T` is, it extends
`Builder<T>` — and `CardWithdrawalBuilder` genuinely does extend `Builder<CardWithdrawalBuilder>`,
so the bound is satisfied regardless of which class is doing the extending. The compiler has no
way to know that the *particular* subclass declaring `extends Builder<CardWithdrawalBuilder>`
should have named itself instead. It compiles cleanly and only fails at runtime, as a
`ClassCastException`, the first time a caller narrows a builder-chain result to the concrete type
the mistaken subclass claimed to be.

</details>

**Q8.** Why does `ArrayList` declare its backing field as `Object[] elementData` instead of
`E[] elementData`?

<details><summary>Answer</summary>

Declaring it `E[]` would force `ArrayList` to pick one of the two idioms in this file for every
allocation and resize — either an unchecked cast that only survives because `E` is unbounded, or
a reflective `Array.newInstance` call that `ArrayList` has no `Class<E>` token to drive. Declaring
it `Object[]` sidesteps the whole problem: the field never promises a narrower type, and the only
place a cast to `E` happens is inside `get(int)`, one unchecked cast per read, which is cheap and
never needs to survive being exposed outside the class.

</details>

## Open questions

None.

---

**Leaves covered:** 2.7.8, 2.7.9, 2.7.10 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 865
