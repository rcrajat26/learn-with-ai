# 03 Java Core — Reifiable types, and how `ArrayList` gets away with it — INTERNALS (§3.5, 3.5.7, 3.5.8)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Bridge methods](03a-internals-bridge-methods.md) · Next: [Heap pollution and `@SafeVarargs`](03c-internals-heap-pollution-and-safevarargs.md)

This file covers the two leaves under §3.5.7–3.5.8: what "reifiable" precisely means at the
runtime-entity level, and why the one place the JDK itself has to touch a raw array under a type
parameter — `ArrayList.elementData` — is built the way it is. `01a-erasure-and-its-consequences.md`
already gave you the reifiable/non-reifiable list at BASICS depth; this file does not restate that
list, it explains why the JVM needs the concept at all, derives the array-creation restriction from
first principles rather than asserting it, and reads the real JDK 21 `ArrayList` source line by
line. What you write instead of `new T[n]` — the `(T[]) new Object[n]` cast, `Array.newInstance`,
and the escaping-array failure modes — is `02b-generic-arrays-and-self-types.md`'s territory, cross-
linked at the point it comes up rather than re-derived here.

## 1. Reifiable types, precisely (3.5.7)

Start from a question, not a list: **for a given compile-time type, is there a runtime entity that
exactly represents it?** "Reifiable" is the spec's name for "yes." It is not a property the type
system carries for its own sake — it is the answer the JVM's verifier needs before it will let three
instructions exist at all.

Three instructions name a type in their operand and use that name to perform a runtime check:
`checkcast` (does this reference refer to an object of this type, throw `ClassCastException` if
not), `instanceof` (does this reference refer to an object of this type, push a boolean), and
`anewarray` (allocate an array whose component type is this type). A fourth check rides along
implicitly: every `aastore` into a reference array re-checks the element against the array's actual
component type at the store site, not against whatever static type the compiler saw — that check is
what makes `ArrayStoreException` possible, and it needs the same runtime type identity the other
three need. All four need the same thing: a type that can be named in the constant pool as a class,
interface, or array reference, resolved at class-load or link time to one concrete runtime entity.

If a compile-time type has no such entity — if `List<Money>` and `List<CashEntry>` and
`List<BonusEntry>` all erase to the identical runtime class `java.util.List` — then none of the four
operations can be emitted for the parameterized form without lying about what they check. Rather
than silently checking the erasure and calling it done (which is exactly what happens for the
*component* type on generic array creation, see §2 below, and exactly why that path is closed off),
the language refuses to let you write the source form that would require the check in the first
place. That refusal is precisely the boundary this leaf draws.

### Why it exists

Before generics (Java 1.4 and earlier), every declarable type already had exactly one runtime
entity representing it — there was no parameterization to erase, so every type was trivially what
we would now call reifiable. Generics (Java 5, JSR 14) added a second dimension to a type — its type
arguments — that `javac` checks at compile time but the JVM has never been taught to check at run
time, because doing so would have meant a binary-incompatible bytecode format and a mandated
recompilation of every existing class file (`03e-internals-why-erasure-and-super-type-tokens.md`
argues that trade-off in full; it is not re-argued here). Once erasure was chosen, the spec needed a
name for "the type arguments survived erasure without loss" versus "they didn't," because that
distinction is exactly what determines which `checkcast`/`instanceof`/`anewarray` forms remain legal
to write in source. §4.7 is that name.

### The mechanism

`[RESEARCH]` `[SOURCE]` — verified against the live JLS 21 text (`docs.oracle.com/javase/specs/jls/se21/html/jls-4.html#jls-4.7`), quoted verbatim, not paraphrased from an older edition or a summary:

> A type is *reifiable* if and only if one of the following holds:
>
> - It refers to a non-generic class or interface type declaration.
> - It is a parameterized type in which all type arguments are unbounded wildcards (§4.5.1).
> - It is a raw type (§4.8).
> - It is a primitive type (§4.2).
> - It is an array type (§10.1) whose element type is reifiable.
> - It is a nested type where, for each type T separated by a ".", T itself is reifiable.
>
>   For example, if a generic class X&lt;T&gt; has a generic member class Y&lt;U&gt;, then the type
>   X&lt;?&gt;.Y&lt;?&gt; is reifiable because X&lt;?&gt; is reifiable and Y&lt;?&gt; is reifiable.
>   The type X&lt;?&gt;.Y&lt;Object&gt; is not reifiable because Y&lt;Object&gt; is not reifiable.
>
> An intersection type is not reifiable.

Read each clause against QuizStakes types:

- **Non-generic class or interface** — `Money`, `CashEntry`, `LedgerEntry` itself (the interface
  declaration, not a parameterization of it) are all reifiable. There is exactly one `Class` object
  for each, and it never varies with how the type was used at a call site.
- **Parameterized with all-unbounded-wildcard arguments** — `List<?>` is reifiable; `Repository<?>`
  is reifiable. The wildcard carries no information erasure would need to preserve, so nothing is
  lost by collapsing `List<?>` to the same runtime entity as raw `List`.
- **Raw type** — `List`, `Repository` used with no type arguments at all. Reifiable by definition,
  because a raw type already *is* the erasure — there is nothing above the erasure to lose.
- **Primitive type** — `int`, `long`. Never generic, always reifiable, included in the enumeration
  mostly so the recursive array clause below has a base case to bottom out on.
- **Array whose element type is reifiable** — `LedgerEntry[]` is reifiable because `LedgerEntry` is.
  `List<?>[]` is reifiable because `List<?>` is. `List<Money>[]` is **not** reifiable, because
  `List<Money>` is not — and that single fact is the entire reason `new List<Money>[n]` is illegal
  (§2 derives the mechanism, not just the label).
- **The nested clause, the one every summary drops.** A nested type `T1.T2` is reifiable only if
  *every* segment separated by `.` is itself reifiable. Take `Repository<T extends LedgerEntry>`
  with a generic member `Cursor` (non-generic itself, but nested inside a generic outer):
  `Repository<?>.Cursor` is reifiable, because `Repository<?>` is reifiable (unbounded wildcard) and
  `Cursor` is reifiable (non-generic). `Repository.Cursor` (raw outer) is reifiable for the same
  reason via the raw-type clause. But `Repository<CashEntry>.Cursor` is **not** reifiable, because
  `Repository<CashEntry>` is not — a parameterized type with an actual type argument, not a wildcard,
  fails the second clause, and the nested clause's "for each T" then fails on that first segment.
  This is provable, not asserted — `[PROVE]` compiled below.

Compiled on JDK 21.0.7:

```java
interface LedgerEntry { java.util.UUID id(); }
record CashEntry(java.util.UUID id) implements LedgerEntry {}

class Repository<T extends LedgerEntry> {
    class Cursor { }
}

class NestedReif {
    public static void main(String[] args) {
        Repository<CashEntry> repo = new Repository<>();
        Object oc = repo.new Cursor();
        System.out.println(oc instanceof Repository<?>.Cursor);   // reifiable segment-by-segment
        System.out.println(oc instanceof Repository.Cursor);      // raw outer, reifiable
    }
}
```

Both print `true` — both forms compile, because in both, every dot-separated segment is reifiable.
Change the first line to `oc instanceof Repository<CashEntry>.Cursor` and `javac` refuses it outright:

```
NestedReifFail.java:14: error: Object cannot be safely cast to Repository<CashEntry>.Cursor
        System.out.println(oc instanceof Repository<CashEntry>.Cursor);
                           ^
1 error
```

That is the nested clause enforced, not merely stated.

**Table — QuizStakes types against §4.7, clause by clause:**

| Type | Reifiable? | §4.7 clause that decides it |
|---|---|---|
| `int` | Yes | primitive type |
| `Money` | Yes | non-generic class type |
| `LedgerEntry` | Yes | non-generic interface type |
| `LedgerEntry[]` | Yes | array type, element `LedgerEntry` is reifiable |
| `List` (raw) | Yes | raw type |
| `List<?>` | Yes | parameterized type, all arguments unbounded wildcards |
| `List<?>[]` | Yes | array type, element `List<?>` is reifiable |
| `List<Money>` | **No** | parameterized type with an actual type argument — none of the reifiable clauses fire |
| `List<? extends LedgerEntry>` | **No** | bounded wildcard is not "unbounded wildcard" — the second clause requires *all* arguments to be `?` with no bound |
| `Repository<CashEntry>` | **No** | parameterized type with an actual type argument |
| `T` (type variable) | **No** | not covered by any clause — a type variable is neither primitive, non-generic, raw, nor a qualifying parameterized or array type |
| `T[]` | **No** | array type whose element type (`T`) is not reifiable |

Now connect every "yes" to a concrete runtime object, because that connection is the entire point of
the INTERNALS tier. A reifiable type has exactly one `Class` object that names it precisely; a
non-reifiable type has no such object — the only `Class` in the neighbourhood is the erasure's, and
using it to stand in for the parameterized type is the exact move that produces an unchecked warning
everywhere else in this note set. Verified on JDK 21.0.7:

```java
List<CashEntry> ledger = List.of(new CashEntry(UUID.randomUUID()));
System.out.println(ledger.getClass());        // class java.util.ImmutableCollections$List12
System.out.println(List.class);               // interface java.util.List

CashEntry[] arr = new CashEntry[0];
System.out.println(arr.getClass());            // class [LReif$CashEntry;
System.out.println(arr.getClass().getComponentType());  // class Reif$CashEntry
```

`List.class` is a `Class<List>` — there is no expression in the Java language that produces a
`Class<List<CashEntry>>`, because no such runtime entity exists to be its value; the only class
literal `List<CashEntry>` could name is the one that also serves `List<BonusEntry>` and raw `List`.
`LedgerEntry[].class` (equivalently `arr.getClass()` above) genuinely names an array class distinct
from `Object[].class`, and `getComponentType()` genuinely answers `CashEntry` — because the array
type's component is reifiable, `anewarray` recorded that exact type in the constant pool at creation,
and the resulting `Class` object carries it forward for the array's whole lifetime.

The bytecode consequence follows directly. `x instanceof List<?>` compiles, because `List<?>` is
reifiable and the compiler can name it in the constant pool and let the verifier check it. Compiled
and disassembled on JDK 21.0.7 (`javap -c -p InstanceofOk.class`):

```
6: aload_1
7: instanceof    #10                 // class java/util/List
10: istore_2
```

The `instanceof` operand is `java/util/List` — the erasure, because `List<?>`'s runtime identity
*is* the erasure (the wildcard clause says so). Now the non-reifiable form, `x instanceof
List<Money>` — same source shape, one type argument changed from `?` to a concrete `Money`:

```
InstanceofFail.java:8: error: Object cannot be safely cast to List<Money>
        boolean b = x instanceof List<Money>;
                    ^
1 error
```

No bytecode was ever generated, because there is no `Class<List<Money>>` for `instanceof` to test
against, and the compiler will not let a runtime check silently degrade into a check against the
erasure without telling you that is what it did. (Contrast a `checkcast` on erasure return values,
which *does* happen silently at every generic read site — that is `03-internals-erasure.md`'s
subject, not this one: the difference is that a `checkcast` there is inserted *by the compiler*
against a type it already proved sound at the call site, never written *by you* against a type it
cannot resolve.)

**Insight:** reifiability is not about what the type system can express — `List<Money>` is a
perfectly well-formed type. It is about what the JVM's operand-naming instructions can point at. The
gap between those two is exactly the set of things erasure took away.

**Interview:** "Why can't you write `x instanceof List<String>`?" — the one-line answer is "because
there's no runtime `Class` object that represents `List<String>` distinctly from any other
parameterization of `List`, and `instanceof` needs to name a real class in the constant pool to
check against." Naming `checkcast`/`instanceof`/`anewarray` by name, unprompted, is what separates a
candidate who has read §4.7 from one reciting "generics use erasure."

No diagram: the manifest assigns this section none; the `javap` excerpts above are the picture.

> A type is reifiable exactly when a runtime `Class` object exists that represents it precisely — no more, no less — and only a reifiable type may be named by `checkcast`, `instanceof`, or `anewarray`.

## 2. Why `new T[n]` is illegal, and `ArrayList`'s answer (3.5.8)

### Why it exists

The one-line answer — "`anewarray` needs a reifiable component type and `T` isn't one" — is true but
shallow; it explains the mechanical block without explaining why the language bothers to enforce it
rather than just erasing `T` to `Object` the way it erases everywhere else. The deeper reason is
array covariance. Java arrays are covariant — `CashEntry[]` is-a `LedgerEntry[]` — and that
covariance is made safe only by a runtime check on every store: `aastore` looks at the array's actual
component type, not the compile-time reference type, and throws `ArrayStoreException` the moment an
incompatible element is written (`../arrays/01a-covariance-and-mutability.md` owns that check's full
mechanics; the one fact borrowed here is that the check exists and runs at every `aastore`).

`[PROVE]` Walk what would happen if `new T[n]` were allowed and erased the way every other generic
construct is erased — to `new Object[n]`:

1. A field or local of declared type `T[]` would, at runtime, actually reference an `Object[]`.
2. Every `aastore` into that array checks against the array's *actual* component type, which is now
   `Object`, not `T` — because the component type is baked into the array object at creation, and
   creation used `Object`.
3. `Object` accepts anything. The one runtime guarantee arrays exist to provide — that a
   `LedgerEntry[]` cannot silently accept a `String` — would be void for every generic array, silently,
   with no exception at the store site and no compiler warning strong enough to explain why. The
   `ClassCastException` that *should* have fired at the illegal store instead fires later, at some
   unrelated read site, on some unrelated line, against some caller who did nothing wrong.

That is worse than erasure's other compromises: a `List<Money>` that silently accepts a `BonusEntry`
through a raw-type back door at least fails at a `checkcast` on the very next read — heap pollution
through generics is contained to "the next read of this reference"
(`03c-internals-heap-pollution-and-safevarargs.md` walks that sequence exactly). A `T[]` that is
secretly an `Object[]` fails the store-time guarantee arrays are built around, so the language closes
the hole at the only place it can be closed for free: compile time, by refusing the source form.

### The mechanism

`anewarray`'s operand is a constant-pool reference to a class, interface, or array type — resolved
once, at class-load or link time, to one concrete entity. It cannot take a type variable, because a
type variable resolves to a different erasure per instantiation site and there is no single constant
pool entry that could mean all of them. The compiler enforces that fact at the source level as
"generic array creation," and the wording is real `javac` output, not a paraphrase — captured on
JDK 21.0.7:

```java
class GenArr1<T> {
    T[] illegal(int n) {
        return new T[n];
    }
}
```

```
GenArr1.java:5: error: generic array creation
        return new T[n];
               ^
1 error
```

Four cases, one table, each row a real diagnostic captured on this machine — so you know exactly
where the reifiability line falls, not just that it exists:

| Form | Result | Why |
|---|---|---|
| `new T[n]` | illegal — `generic array creation` | `T` is a type variable; not reifiable; no clause of §4.7 covers it |
| `(T[]) new Object[n]` | legal, `[unchecked] unchecked cast` warning (suppressible) | creates a real `Object[]`, casts the *reference* to `T[]` — the array object itself never becomes a `T[]` at runtime, only the compile-time view of the variable does |
| `new List<?>[n]` | legal, no warning | component type `List<?>` is reifiable (unbounded-wildcard clause); `anewarray` can name `java/util/List` directly |
| `new List<Money>[n]` | illegal — `generic array creation` | component type `List<Money>` is not reifiable; same failure as row 1, one level down |

Row 2's warning, uncommented, on JDK 21.0.7:

```
GenArr2NoSuppress.java:3: warning: [unchecked] unchecked cast
        return (T[]) new Object[n];
                     ^
  required: T[]
  found:    Object[]
  where T is a type-variable:
    T extends Object declared in class GenArr2NoSuppress
```

Row 3's `anewarray` operand, disassembled (`javap -c -p GenArr3.class`, JDK 21.0.7) — proof, not
assertion, that a reifiable component type is exactly what lets the instruction exist at all:

```
java.util.List<?>[] legal(int);
  Code:
     0: iload_1
     1: anewarray     #7                  // class java/util/List
     4: areturn
```

The constant-pool entry names `java/util/List` — the erasure of `List<?>`, which *is* `List<?>`'s
runtime identity because the unbounded-wildcard clause makes them the same reifiable type. There is
no equivalent instruction to show for `new List<Money>[n]`: it never reaches bytecode, because
`javac` stops it at the same "generic array creation" check as row 1.

The full covariance/wildcard contrast that motivates why arrays and generics disagree on variance in
the first place — array covariance is a runtime-checked, load-bearing feature; generic invariance is
a compile-time-only discipline with no runtime check to fall back on — is
`01b-variance-and-wildcards.md`'s subject; one sentence of it is borrowed above and no more.

**Pitfall:** believing the suppressed cast in row 2 makes the array *become* a `T[]`. It does not —
it makes the compiler stop complaining about a mismatch that is still there. The array object
created by `new Object[n]` has component type `Object` for its entire lifetime; the `(T[])` cast is
purely a compile-time fiction that lets the reference type-check. The moment that reference escapes
somewhere that later performs its own `aastore` or reflective component-type check against the
*expected* `T`, the fiction shows — that failure mode, and how to avoid ever letting the array
escape, is `02b-generic-arrays-and-self-types.md`'s subject in full; one line and a pointer is all
this file owes it.

### `ArrayList`'s answer — `[SOURCE]` the real JDK 21 source

`ArrayList<E>` needs a backing array and cannot write `new E[initialCapacity]` for exactly the reason
above. Its answer, quoted from the actual JDK 21.0.7 `java.base/java/util/ArrayList.java` (extracted
from `$J21/lib/src.zip`):

```java
transient Object[] elementData; // non-private to simplify nested class access
```

`transient` — because `ArrayList` implements `Serializable` and hand-writes its own serialized form
in `writeObject` rather than letting default serialization walk the array field:

```java
private void writeObject(java.io.ObjectOutputStream s)
    throws java.io.IOException {
    // Write out element count, and any hidden stuff
    int expectedModCount = modCount;
    s.defaultWriteObject();
    // Write out size as capacity for behavioral compatibility with clone()
    s.writeInt(size);
    // Write out all elements in the proper order.
    for (int i=0; i<size; i++) {
        s.writeObject(elementData[i]);
    }
    if (modCount != expectedModCount) {
        throw new ConcurrentModificationException();
    }
}
```

`defaultWriteObject()` serializes every non-transient, non-static field of the instance as-is; if
`elementData` were not `transient`, that call would also serialize the backing array itself —
including its unused trailing capacity slots — as an `Object[]`, doubling the write and leaking an
implementation detail (the over-allocated capacity) into the wire format. Marking it `transient` and
writing only `size` followed by exactly `size` live elements, by hand, is `ArrayList`'s serialized
form staying stable across the field's own capacity-growth churn. (Full serialization mechanics are
`../serialization/02-serialization.md`'s territory — this is the one sentence this file needs from
it.)

The accessor that turns that raw `Object[]` back into an `E` at read time:

```java
@SuppressWarnings("unchecked")
E elementData(int index) {
    return (E) elementData[index];
}
```

Every line explained: the method is package-private (no access modifier, `E elementData(int index)`)
— an internal helper, never part of the public API, called only from other `ArrayList` methods that
already know the invariant holds. The cast `(E) elementData[index]` is the same unchecked cast row 2
of the table above produces — no runtime check backs it, because `E` is erased and there is no `E`
for the JVM to check against. The `@SuppressWarnings("unchecked")` on the method, not on the call
site inside some larger method, is deliberate scoping: the annotation's safety argument has to hold
for the *entire* body it's attached to, and here that body is one line, so the argument is
trivially auditable — "only `add(E)` and its overloads ever write into this array, and every one of
them is declared to accept only `E`, so every slot in `[0, size)` already holds an `E` by
construction." Attaching the suppression to `get(int)` instead (a much larger method with bounds
checking, iteration support, and more) would hide that one unchecked line among dozens of checked
ones — `01c-raw-types-and-unchecked-warnings.md` owns the general discipline of suppressing at the
narrowest scope that carries the actual argument; this is that discipline's canonical library
example.

**Design lesson, the transferable part:** `ArrayList` is honest at exactly one point. The array is
`Object[]` for its entire life — it is never cast to `E[]` and returned to a caller, never assigned
to an `E[]`-typed field, never leaves the object's internals in a form that claims to be more
specific than it is. The single unchecked cast is isolated in a private accessor whose safety
argument is one sentence long and provably true from the class's own write paths. The failure mode
this design specifically avoids — a generic array that *does* escape as a `T[]` and produces a
`ClassCastException` or `ArrayStoreException` far from where the array was created — is
`02b-generic-arrays-and-self-types.md`'s subject; this file's job was to show you the shape that
avoids it, not the shape that falls into it.

`[X-REF 02]` This shape — an untyped backing array plus one narrowly-scoped unchecked cast at the
read boundary — recurs everywhere in the collections library: `ArrayDeque` backs onto an
`Object[]` ring buffer with the identical cast pattern at its `elementAt` accessor; `PriorityQueue`
backs its binary heap onto `Object[]` with the same cast in `siftUp`/`siftDown`; `HashMap`'s bucket
array is `Node<K,V>[] table`, itself created as `(Node<K,V>[]) new Node[cap]` with the same
suppressed-cast shape one level up (a `Node` array rather than an `E` array, but the same reason:
`Node` is itself a generic class, so `new Node<K,V>[cap]` would hit the identical "generic array
creation" error this section derived). Guide `02 Java collections` owns the full internals of each of
those; the pattern is the transferable fact, not the four implementations.

The one place the JDK does the *opposite* — using reflection to get a real, precisely-typed array
back instead of hiding behind `Object[]` — is worth naming because it is the escape hatch
`02b-generic-arrays-and-self-types.md` teaches you to reach for. `Arrays.copyOf`'s three-argument
overload, real signature confirmed via `javap -p java.util.Arrays` on JDK 21.0.7:

```
public static <T, U> T[] copyOf(U[], int, java.lang.Class<? extends T[]>);
```

The `Class<? extends T[]>` parameter is a type token for the array class itself — the caller
supplies the one thing erasure destroyed, a runtime `Class` object naming the *exact* array type
wanted, and `copyOf` uses `Array.newInstance` under that token to allocate an array whose runtime
component type is genuinely `T`, not `Object`. `Collection.toArray(T[])` (`public abstract <T> T[]
toArray(T[])`, confirmed the same way) takes the same idea one step further: the caller passes a
*sample* array, and the implementation inspects `a.getClass()` at runtime, via `getComponentType()`
introduced in §1 above, to decide whether the supplied array is large enough to reuse or whether it
must allocate a fresh one of the same reified component type via `Arrays.copyOf(elementData, size,
a.getClass())` — a real line from `ArrayList.toArray(T[])` in the same source file quoted above.
Reflection is the one place a component type can be supplied at run time instead of resolved at
compile time from a type variable that no longer exists — which is exactly what `anewarray` cannot
do and `Array.newInstance` can.

No diagram: the manifest assigns this section none; the `javap` and source excerpts above are the
picture.

> `new T[n]` is illegal because `anewarray` needs a reifiable, constant-pool-nameable component type and a type variable has none; `ArrayList` sidesteps the restriction by never creating a `T[]` at all — it keeps an `Object[]` for life and isolates the one unchecked cast in a single narrowly-scoped accessor whose safety argument is provable from the class's own write paths.

## Supporting facts

### `getComponentType()` as the reification witness

`Class.getComponentType()` returns the exact component type an array was created with — `Class`,
not `Class<?>`, because arrays predate generics and their reflective API was never retrofitted with
type parameters. For a reifiable-component array this answer is precise (`LedgerEntry[].class
.getComponentType()` returns `LedgerEntry`); for the `(T[]) new Object[n]` fiction it returns
`Object`, because that is genuinely what the array was created as — the method cannot see past the
cast, because the cast never touched the array object itself, only the reference's static type.

> `getComponentType()` reports the runtime truth of what an array is, which is exactly why it cannot be fooled by a compile-time cast.

### Intersection types are never reifiable

The JLS §4.7 text closes with a one-line clause of its own: "An intersection type is not reifiable."
A bound like `<T extends Comparable<T> & Serializable>` produces an intersection type for `T` at
certain use sites, and no clause of the main enumeration covers it — there is no single `Class`
object that could represent "implements both of these," so `instanceof`, `checkcast`, and array
creation against an intersection type are all as restricted as against a bare type variable.

> An intersection type has no single runtime representative, so it inherits every restriction a non-reifiable type carries, with no separate rule needed.

### `Class<List>` versus the phantom `Class<List<Money>>`

`List.class` has static type `Class<List>` — the raw type, because a class literal's type parameter
is always the erasure of the type named. There is no source-level expression that types as
`Class<List<Money>>`, because doing so would require a runtime entity distinct per parameterization,
which is precisely what §1 established does not exist. Reaching for the type argument anyway is what
`02a-type-tokens-and-generic-reflection.md`'s super-type-token workaround exists to solve at the
reflective-metadata level, not the `Class`-object level; one sentence and a pointer is all this file
owes it.

> A class literal's static type is always `Class<Erasure>`, never `Class<Parameterization>`, because the literal names one `Class` object and that object is the erasure's.

## Pitfalls

### "The suppressed cast in `(T[]) new Object[n]` makes the array a real `T[]`"

**Wrong**

```java
class GenArr2NoSuppress<T> {
    T[] legalWithWarning(int n) {
        return (T[]) new Object[n];
    }
}
```

```
GenArr2NoSuppress.java:3: warning: [unchecked] unchecked cast
        return (T[]) new Object[n];
                     ^
  required: T[]
  found:    Object[]
  where T is a type-variable:
    T extends Object declared in class GenArr2NoSuppress
```

The warning is `javac` telling you the cast has no runtime backing — silencing it with
`@SuppressWarnings` removes the message, not the fact. The returned array's actual runtime component
type is still `Object`, forever; nothing about the cast changed what `new Object[n]` allocated.

**Right**

```java
static <T> T[] copyInto(T[] sample, java.util.List<? extends T> source) {
    T[] result = java.util.Arrays.copyOf(sample, source.size());
    for (int i = 0; i < source.size(); i++) {
        result[i] = source.get(i);
    }
    return result;
}
```

`Arrays.copyOf(sample, n)` reads `sample.getClass()` at run time and allocates the *new* array with
that exact reified component type via reflection, so the array this method returns really is a
`T[]` at runtime, provided the caller passed a real `T[]` sample — the caller supplies the
reification the callee has no other way to obtain. This is `02b-generic-arrays-and-self-types.md`'s
full pattern; this pitfall only needs the contrast.

**Why people believe it:** the cast compiles, the variable is declared `T[]`, and nothing throws at
the point of the cast — the failure, if the array escapes and is later checked against its true
component type, happens somewhere else entirely, often much later, which hides the connection back
to this line.

### "`instanceof List<?>` and `instanceof List<Money>` are the same kind of check, one just more specific"

**Wrong**

```java
Object x = List.of(new Money(100));
boolean b = x instanceof List<Money>;
```

```
InstanceofFail.java:8: error: Object cannot be safely cast to List<Money>
        boolean b = x instanceof List<Money>;
                    ^
1 error
```

**Right**

```java
Object x = List.of(new Money(100));
boolean isList = x instanceof List<?>;
if (isList && !((List<?>) x).isEmpty() && ((List<?>) x).get(0) instanceof Money) {
    // narrowed by hand, one element at a time, because the JVM cannot narrow List<?> to List<Money>
}
```

`List<?>` is reifiable (unbounded-wildcard clause), so `instanceof` can check it directly against the
erasure `java.util.List`. `List<Money>` is not reifiable, so there is no `Class` object the check
could run against — the compiler refuses the form outright rather than silently checking the erasure
and calling the result "instanceof List&lt;Money&gt;."

**Why people believe it:** `List<?>` and `List<Money>` look like two points on the same specificity
scale in source, so it reads as though the JVM should just be able to "check less precisely" for one
and "more precisely" for the other — but there is no runtime object for the more-precise check to
run against, so "less precise" is not a fallback, it is the only form that was ever going to compile.

### "The nested-type reifiability rule only matters for exotic library code"

**Wrong**

```java
class Repository<T> {
    class Cursor { }
}
Repository<CashEntry> someRepository = new Repository<>();
Object oc = someRepository.new Cursor();
boolean b = oc instanceof Repository<CashEntry>.Cursor;
```

```
NestedReifFail.java:14: error: Object cannot be safely cast to Repository<CashEntry>.Cursor
        System.out.println(oc instanceof Repository<CashEntry>.Cursor);
                           ^
1 error
```

**Right**

```java
class Repository<T> {
    class Cursor { }
}
Repository<CashEntry> someRepository = new Repository<>();
Object oc = someRepository.new Cursor();
boolean b = oc instanceof Repository<?>.Cursor;   // reifiable segment by segment
boolean raw = oc instanceof Repository.Cursor;    // reifiable via the raw-type clause
```

Any generic class with a non-static inner class inherits this the moment someone tries to narrow a
reference back to the inner type with a concrete type argument on the outer — a completely ordinary
`Repository<CashEntry>.Cursor` shape, not an exotic one. The fix is the same move as everywhere else
in this file: drop to the wildcard or raw form, because those are the only reifiable options.

**Why people believe it:** the nested clause is the one JLS §4.7 clause every informal summary of
"reifiable types" omits, so most engineers have simply never seen the rule stated, let alone
recognised that their own inner-class-of-a-generic code depends on it.

## Cheat sheet

| Fact | Detail |
|---|---|
| Reifiable means | a `Class` object exists that represents the type exactly |
| Instructions that require it | `checkcast`, `instanceof`, `anewarray`; implicit at every `aastore` element check |
| §4.7 reifiable list (6 clauses) | non-generic type; unbounded-wildcard parameterization; raw type; primitive; array of reifiable element; nested type with every segment reifiable |
| Not reifiable | type variable (`T`), any parameterized type with a real or bounded-wildcard argument, intersection types |
| `new T[n]` | illegal — `generic array creation` — `anewarray` cannot name a type variable |
| `(T[]) new Object[n]` | legal, unchecked-cast warning, array stays `Object[]` for life |
| `new List<?>[n]` | legal, no warning — component `List<?>` is reifiable |
| `new List<Money>[n]` | illegal — component `List<Money>` is not reifiable |
| `ArrayList`'s backing field | `transient Object[] elementData` |
| `ArrayList`'s one unchecked cast | `@SuppressWarnings("unchecked") E elementData(int index) { return (E) elementData[index]; }` |
| Why `transient` | serialization writes elements by hand in `writeObject`, so the raw array is never itself serialised |
| Reflective escape hatch | `Arrays.copyOf(U[], int, Class<? extends T[]>)` and `Collection.toArray(T[])` use a runtime `Class` to allocate the real component type |

## Self-test

**Q1.** What question is "reifiable" actually the answer to, and which three bytecode instructions need that answer to be yes?

<details><summary>Answer</summary>

It answers "does a runtime `Class` object exist that represents this exact compile-time type?" The
instructions that need the answer to be yes are `checkcast`, `instanceof`, and `anewarray` — each
takes a constant-pool reference to a class, interface, or array type and needs that reference to
resolve to one concrete runtime entity. `aastore` rides along implicitly: it checks every store
against the array's actual component type, which only means something if that component type was
itself nameable at creation.

</details>

**Q2.** Name all six clauses of JLS §4.7's reifiable-type enumeration, from memory, not just "primitives and non-generic types."

<details><summary>Answer</summary>

Non-generic class or interface type; parameterized type where every type argument is an unbounded
wildcard; raw type; primitive type; array type whose element type is reifiable; and the nested-type
clause — a nested type where every dot-separated segment is itself reifiable. Most people stop after
four; the array and nested clauses are the ones that actually explain generic-array and inner-class
behaviour.

</details>

**Q3.** Why is `Repository<CashEntry>.Cursor` not reifiable, when `Repository<?>.Cursor` is?

<details><summary>Answer</summary>

The nested clause requires every dot-separated segment to be reifiable. `Repository<?>` is reifiable
because its only type argument is an unbounded wildcard, so `Repository<?>.Cursor` passes segment by
segment. `Repository<CashEntry>` has a concrete type argument, which fails every clause of the
enumeration, so it is not reifiable — and the moment one segment fails, the whole nested type fails
with it, regardless of whether `Cursor` itself is generic.

</details>

**Q4.** Derive, don't just state, why `new T[n]` is illegal — connect it to array covariance, not just to `anewarray`'s operand format.

<details><summary>Answer</summary>

`anewarray` needs a reifiable component type because its operand is a single constant-pool class
reference resolved once at link time, and `T` has no single runtime identity to resolve to. But the
deeper reason the language doesn't just erase `T` to `Object` and allow it anyway is array
covariance: Java arrays carry their true component type at runtime and check every `aastore` against
it, which is what makes `ArrayStoreException` meaningful. If `new T[n]` erased to `new Object[n]`,
the array's actual component type would be `Object`, every store would check against `Object`
instead of `T`, and the array would silently accept anything — voiding the one runtime guarantee
arrays are built around, with the resulting `ClassCastException` surfacing much later at some
unrelated read site instead of at the illegal store.

</details>

**Q5.** What field does `ArrayList<E>` actually use for storage, and why is it declared `transient`?

<details><summary>Answer</summary>

`transient Object[] elementData` — not `E[]`, because `new E[n]` is illegal for the same reason as
`new T[n]`. It's `transient` because `ArrayList` implements `Serializable` but writes its own
serialized form by hand in `writeObject`: it calls `defaultWriteObject()` for the other fields, then
writes `size` followed by exactly `size` live elements one at a time. If `elementData` weren't
transient, default serialization would also dump the backing array itself, including its unused
spare capacity, which is exactly the implementation detail the hand-written form avoids leaking.

</details>

**Q6.** Where does `ArrayList` put its one unchecked cast, and why there specifically rather than on `get(int)`?

<details><summary>Answer</summary>

In a package-private helper, `elementData(int index)`, whose entire body is `return (E)
elementData[index];`, annotated `@SuppressWarnings("unchecked")` at the method level. It's scoped
there rather than on `get(int)` because the suppression's safety argument — "every slot in [0, size)
already holds an E, because only add(E) and its overloads ever write into this array" — has to be
auditable against everything the annotation covers. On a one-line method that argument is trivial to
verify. Attached to `get(int)`, which also does bounds checking and other logic, the same suppression
would silently cover any future unchecked cast added to that larger method too.

</details>

**Q7.** What is genuinely different about `Arrays.copyOf(U[] original, int newLength, Class<? extends T[]> newType)` compared to everything else in this file?

<details><summary>Answer</summary>

It is the one place the JDK deliberately gets a real, precisely-typed array back instead of hiding
behind `Object[]`. It takes a `Class` token for the target array type as an explicit parameter — the
caller supplies at run time the exact information erasure removed at compile time — and uses that
token with reflection (`Array.newInstance` underneath) to allocate an array whose actual runtime
component type is the real target type, not `Object`. It's the reflective escape hatch from the
restriction the rest of this file derives, not an exception to it.

</details>

**Q8.** Is `List<? extends LedgerEntry>` reifiable? Why or why not?

<details><summary>Answer</summary>

No. The unbounded-wildcard clause requires every type argument to be an unbounded wildcard — literally
`?` with no bound. `? extends LedgerEntry` is a bounded wildcard, so it doesn't qualify, and no other
clause of §4.7 covers a parameterized type with any kind of real type-argument content. Only `List<?>`
is reifiable; `List<? extends LedgerEntry>` and `List<LedgerEntry>` are both erased the same way at
runtime but neither has a distinct `Class` object of its own.

</details>

## Open questions

None.

---

**Leaves covered:** 3.5.7, 3.5.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 732
