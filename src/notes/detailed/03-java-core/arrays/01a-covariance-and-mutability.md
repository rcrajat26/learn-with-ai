# 03 Java Core — Array covariance, mutability, and the shallow `clone()` — BASICS (§1.22, 1.22.5–1.22.7)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Arrays are objects](01-basics.md) · Next: [The `Arrays` utilities and `System.arraycopy`](01b-array-utilities-and-arraycopy.md)

`01-basics.md` established that an array is a real object with a synthesised class, a `length` field, and zero-fill on creation. This file is about three ways that object's guarantees are weaker than they look: the compile-time element type can be a lie that only a runtime check catches (§1.22.5), `final` on an array variable protects nothing inside the array (§1.22.6), and copying an array copies its slots, not what the slots point at (§1.22.7). All three come from the same root cause — an array is a reference to mutable storage, and Java's type system only ever constrains the reference, never the storage behind it. Everything about `Arrays`, `System.arraycopy`, memory layout, and varargs is handed to the next three files in this batch; this file stays on covariance, mutability, and `clone()`.

## 1. Array covariance and the runtime `ArrayStoreException` (1.22.5)

**Concept.** In Java's type system, if `CashEntry` is a subtype of `LedgerEntry`, then `CashEntry[]` is a subtype of `LedgerEntry[]`. That single rule — arrays are **covariant** — is what lets you pass a `CashEntry[]` anywhere a `LedgerEntry[]` is expected, no cast, no wrapper. It also means the compiler will happily let you store a `BonusEntry` into that same reference, because as far as the declared type `LedgerEntry[]` is concerned a `BonusEntry` fits. The array underneath is still, physically, a `CashEntry[]` — it was allocated with `new CashEntry[3]` and its class-file component type never changes. So the store has to be refused *somewhere*, and Java refuses it at the one place both facts are visible at once: the instant of the store, at runtime.

### Why it exists

Arrays predate generics by a decade. `java.lang.Object` gained `Object[]` covariance in Java 1.0 because it was the only way to write one method — `void sort(Object[] a)`, `Arrays.equals(Object[], Object[])` — that worked over every reference array type without writing it once per type. There were no type parameters to make a `sort` generic over; array covariance was the mechanism that gave you polymorphic array-processing code at all. Generics arrived in Java 5 with the opposite design — `List<CashEntry>` is *not* a subtype of `List<LedgerEntry>` — precisely because the JDK team had thirteen years of `ArrayStoreException` field experience and decided compile-time rejection was the better failure mode for a fresh design. Arrays could not retrofit that fix without breaking every `Object[]`-taking method already shipped, so they stayed covariant, and the runtime check that catches the resulting lie stayed permanently in the storage instruction itself.

### The mechanism

`[PROVE]` Walk the argument instead of asserting the result. Start from a `CashEntry[]` that is genuinely a `CashEntry[]` at allocation:

```java
CashEntry[] cashBatch = new CashEntry[3];
cashBatch[0] = new CashEntry(UUID.randomUUID(), stake);
```

The compiler accepts the widening assignment below — `LedgerEntry[]` is a supertype of `CashEntry[]` under covariance, so no cast is needed:

```java
LedgerEntry[] widened = cashBatch;
```

`widened` and `cashBatch` are now two references to the *same* array object, whose actual, physical component type is still `CashEntry`. The compiler also accepts this store, because `BonusEntry` is a `LedgerEntry` and `widened` is declared `LedgerEntry[]`:

```java
static void postFirstEntry(LedgerEntry[] batch, LedgerEntry entry) {
    batch[0] = entry;   // compiles: entry is a LedgerEntry, batch is LedgerEntry[]
}
postFirstEntry(widened, new BonusEntry(UUID.randomUUID(), stake));
```

Follow it through: if this store were allowed to succeed, `cashBatch[0]` — the *same slot*, reached through the *other* reference — would now hold a `BonusEntry`. Every future read of `cashBatch[0]` as `CashEntry` would be unsound: the JVM would hand back a `BonusEntry` wearing a `CashEntry` badge, and the very next line that called a `CashEntry`-only method on it would corrupt memory or crash with no diagnostic pointing at the real cause. The array's element-type guarantee — "every slot holds a `CashEntry` or `null`" — would be a lie the type system printed but the runtime did not enforce. So the JVM enforces it: **every** store into a reference array checks, at the instant of the store, whether the value's actual class is assignable to the array's actual, physical component type — not its declared type at the call site, which the JVM does not even have visibility into once erasure and widening have happened. Compiled and run on JDK 21.0.7, `postFirstEntry` throws:

```
Exception in thread "main" java.lang.ArrayStoreException: ArrayStoreDemo$BonusEntry
	at ArrayStoreDemo.postFirstEntry(ArrayStoreDemo.java:16)
	at ArrayStoreDemo.main(ArrayStoreDemo.java:25)
```

The message names `BonusEntry` — the class that was *rejected*, not the array's declared type and not the array's actual component type. That is deliberate and it is the detail that makes a production log readable: without it you would know a store failed somewhere in a `LedgerEntry[]`-typed call chain and have to reconstruct which concrete class caused it. With it, the stack trace already answers "what got rejected", and the frame at line 16 answers "where."

`javap -c` on the compiled class shows exactly one instruction doing the store:

```
static void postFirstEntry(LedgerEntry[], LedgerEntry);
  Code:
     0: aload_0
     1: iconst_0
     2: aload_1
     3: aastore
     4: return
```

`aastore` — "store into object array" — is the whole store. There is no separate `checkcast` before it and no branch after it in the bytecode; `javac` emits nothing extra because it does not need to. The array-store check is **inside** the `aastore` instruction's own specified behavior (JVMS §6.5, `aastore`): the JVM interpreter or JIT-compiled equivalent reads the array's actual component type from the array's own class-file-level type metadata (not from any local variable's declared type) and compares it against the runtime class of the value being stored, on every single execution of that instruction. That is why nothing in `javap` output ever looks like a check — it is not a separate op you could omit, and there is no flag or annotation that turns it off.

Contrast with a primitive array. `long[]` cannot be covariant with anything — there is no primitive supertype relationship for `javac` to exploit, so there is nothing to lie about, and the JVM does not check:

```
static void writeLast(long[], long);
  Code:
     0: aload_0
     1: aload_0
     2: arraylength
     3: iconst_1
     4: isub
     5: lload_1
     6: lastore
     7: return
```

`lastore` stores a `long` into a `long[]` slot with no type comparison at all — the value's bit pattern goes straight into the slot. There is no `ArrayStoreException` for a primitive array because there is no possible mismatch: every `long[]` slot can only ever legally hold a `long`.

**The cost, and its escape hatch.** The `aastore` check is paid per store, every time, unconditionally at the bytecode-semantics level. Using this batch's numbers: stake reservations run at 2.8M/day with a peak of 1,200/sec, and each reservation that posts into a `LedgerEntry[]`-typed buffer pays one `aastore` check; the ledger's write rate as a whole peaks at 13,600/sec, so if every one of those writes goes through a covariant reference-array store, that is 13,600 checks/sec at peak, sustained. That arithmetic tells you the *shape* of the cost — the JIT's actual behavior does not. The JIT is permitted to prove, at a given call site, that the array's exact runtime type is known (for example, if it can see the array was allocated as `CashEntry[]` and never escapes to code that could re-store into it as a different concrete type) and eliminate the check entirely for that site; whether it does so, and by how much that changes wall-clock time here, is **`**Unverified:**`** — this file has not profiled it on this machine, and no nanosecond figure is printed here because none has been measured. What the instruction specifies and what the JIT is permitted to optimize are two different claims; only the first is backed by the `javap` output above.

The escape hatches, compared:

| Escape hatch | When the check moves | Cost |
|---|---|---|
| Use the exact array type, never widen it (`CashEntry[]`, never assign to a `LedgerEntry[]` variable) | Check still runs, but nothing can ever fail it — you removed the *possibility* of a mismatched store, not the instruction | None beyond `aastore` itself; safest, easiest to lose by accident on the next refactor |
| `List<CashEntry>` instead of an array | Compile time — `javac` rejects `list.add(bonusEntry)` before it ever runs | No per-write runtime check at all; boxing/list overhead if the element is a primitive-shaped value |
| A primitive array (`long[]`, not `Long[]`) | Never applicable — no covariance, no check exists | None; only usable when the component is genuinely primitive |

### No diagram

No diagram: the manifest assigns this section none; the `javap`/`java` excerpts above are the picture. The variance *contrast* between arrays and generics — why `List<CashEntry>` is invariant while `CashEntry[]` is covariant, side by side — is owned by `../generics/01b-variance-and-wildcards.md`, which carries diagram D-056; this file only shows the array side of the mechanism and cross-links there rather than rebuilding that comparison.

### Code

The complete, compiled, run program behind every excerpt above:

```java
import java.math.BigDecimal;
import java.util.Currency;
import java.util.UUID;

public class ArrayStoreDemo {

    sealed interface LedgerEntry permits CashEntry, BonusEntry {
        UUID id();
        Money amount();
    }
    record Money(BigDecimal amount, Currency currency) {}
    record CashEntry(UUID id, Money amount) implements LedgerEntry {}
    record BonusEntry(UUID id, Money amount) implements LedgerEntry {}

    static void postFirstEntry(LedgerEntry[] batch, LedgerEntry entry) {
        batch[0] = entry;
    }

    public static void main(String[] args) {
        Money stake = new Money(new BigDecimal("4.20"), Currency.getInstance("USD"));
        CashEntry[] cashBatch = new CashEntry[3];
        cashBatch[0] = new CashEntry(UUID.randomUUID(), stake);

        LedgerEntry[] widened = cashBatch;
        postFirstEntry(widened, new BonusEntry(UUID.randomUUID(), stake));

        System.out.println("unreachable: " + widened[0]);
    }
}
```

### Gotcha

**Pitfall:** the wrong belief is "if it compiled, the array holds what I declared." A `CashEntry[]` widened to `LedgerEntry[]` and handed into any method that stores a differently-typed `LedgerEntry` through that reference compiles cleanly and throws `ArrayStoreException` only at the exact moment of the errant store, potentially deep in a call stack far from the widening — the symptom shows up nowhere near the cause. The fix is either of the first two escape hatches above: keep the exact array type all the way through, or switch to a generic `List` so the mismatch is a compile error instead of a 2 a.m. production stack trace.

One line each on where this reaches: array covariance is the exact reason generic array creation (`new T[n]`) is illegal in the first place — a generic array could never enforce this same runtime check because its erased component type is unknown at the store site (`../generics/03b-internals-reifiable-types-and-generic-arrays.md`); and it is the same `aastore` check that fires when a `(T[]) new Object[n]` cast escapes a method and gets stored into elsewhere as though it were really a `T[]` (`../generics/02b-generic-arrays-and-self-types.md`).

`**Interview:**` "Why does `ArrayStoreException` exist at all?" — because arrays are covariant by a design decision from 1995, before generics existed, and covariance means the compile-time element type of an array reference can differ from its allocated, physical component type; the only place both are simultaneously knowable is the store instruction itself, so the JVM checks there, every time, forever.

> Array covariance lets `CashEntry[]` stand in for `LedgerEntry[]`, so the JVM checks every reference-array store against the array's actual allocated component type inside the `aastore` instruction itself, because the compiler's promise about element type cannot be trusted at runtime the way it can for a `List`.

## 2. Arrays are always mutable; `final` is not `const` (1.22.6)

**Concept.** `final` applied to an array-typed field or variable constrains exactly one thing: the reference cannot be reassigned to point at a different array. It says nothing about the ten, or three, or three-thousand slots that array points at. There is no modifier, no keyword, and no library type in Java, at any version through 21, that produces an array whose *elements* cannot be changed. `final Money[] DEPOSIT_TIERS` is a promise that `DEPOSIT_TIERS` will always denote the same array object — not a promise about what that array object contains a moment from now.

### Why it exists

`final` on a variable is a single, uniform rule in the JLS (§4.12.4): once assigned, the variable cannot be reassigned. That rule was designed for variables in general — locals, fields, parameters — long before anyone needed a container-specific "this whole structure is now frozen" guarantee, and it was never extended to reach through a reference into the referent's own mutable state. `String` gets to look immutable because every mutating-looking method on `String` returns a new object instead of touching the old one's fields, which are themselves `final` all the way down. An array has no such class design behind it — indexed assignment (`arr[i] = x`) is a language-level operation on the array object's storage, not a method call that some class author could have made a no-op or a copy-on-write. There is nothing in the array's synthesised class for `final` to reach into.

### The mechanism

The QuizStakes version, deliberately built as a `static final` "constant":

```java
static final class DepositTiers {
    static final Money[] DEPOSIT_TIERS = {
        new Money(new BigDecimal("10.00"), Currency.getInstance("USD")),
        new Money(new BigDecimal("50.00"), Currency.getInstance("USD")),
        new Money(new BigDecimal("100.00"), Currency.getInstance("USD"))
    };
}
```

Any other class in the same module can do this, with no cast, no reflection, nothing exotic:

```java
static void tamper() {
    DepositTiers.DEPOSIT_TIERS[0] =
        new Money(new BigDecimal("999999.00"), Currency.getInstance("USD"));
}
```

Compiled and run on JDK 21.0.7:

```
before: [Money[amount=10.00, currency=USD], Money[amount=50.00, currency=USD], Money[amount=100.00, currency=USD]]
after:  [Money[amount=999999.00, currency=USD], Money[amount=50.00, currency=USD], Money[amount=100.00, currency=USD]]
```

`final` never fired, because `final` had nothing to say about an assignment to `DEPOSIT_TIERS[0]` — that statement never reassigns the field `DEPOSIT_TIERS`, it writes through it. The field still points at the exact array object it always did; `javac` has no basis to reject the write.

There is a deeper reason a `static final` array can never be treated as a compile-time constant, and it connects to `../classes-and-initialization/04-internals-final-and-constant-folding.md`, which owns the full `ConstantValue` attribute story: the JVM's constant-folding machinery (the `ConstantValue` class-file attribute, and `javac`'s inlining of `final` values at their use sites) only applies to `final` fields of a primitive type or `String`, initialized with a compile-time constant expression — because only those types are guaranteed, by the language itself, to be genuinely unchangeable after that point. An array reference fails that test at the first requirement: even if the reference itself never gets reassigned, the referent is mutable state, so nothing about a `Money[]`-typed `DEPOSIT_TIERS` array literal is a "constant" in the sense the class-file format understands. `javac` cannot inline `DEPOSIT_TIERS` the way it inlines a `final int MAX_TIERS = 3` — every reader has to go fetch the live array and read its current, possibly-tampered slots.

Three real fixes, compared:

| Fix | What the caller gets | Cost |
|---|---|---|
| Return `array.clone()` from an accessor instead of the field itself | An independent array; mutating it never touches the original | One shallow-copy allocation per call — cheap for a flat array of records, see §3 for what "shallow" means when elements are themselves mutable |
| Expose `List.of` or `Collections.unmodifiableList` instead of an array | A structurally unmodifiable view; calling `set` throws `UnsupportedOperationException` | Loses array-specific APIs (primitive arrays, `Arrays.sort` in place); fine for a `List<Money>` constant, not for a `long[]` |
| `EnumSet`/`EnumMap` when the elements are enum constants | A collection with its own well-defined mutability contract, not array aliasing surprises | Only applicable when the domain is genuinely an enum — see `../enums/01b-collections-patterns-and-guarantees.md` for the enum-collection route in full |

Defensive copying as a design discipline in general — not just for this one array case — is owned by `../immutability-and-design/02-immutability.md` (a later batch; forward-link only).

**Insight:** the subtler half of this leaf is that `Arrays.asList(array)` does not give you a copy either — it gives you a *view* backed by the same array. `01b-array-utilities-and-arraycopy.md` owns `Arrays.asList` in full, including its fixed-size behavior and the `UnsupportedOperationException` on `add`/`remove`; the fact that belongs here, because it is squarely a mutability fact, is that writes through the list-view reach the underlying array and vice versa. Proven on the same `DEPOSIT_TIERS` array:

```java
Money[] source = DepositTiers.DEPOSIT_TIERS;
var view = Arrays.asList(source);
view.set(1, new Money(new BigDecimal("1.00"), Currency.getInstance("USD")));
```

Output on JDK 21.0.7:

```
array through view mutation: [Money[amount=999999.00, currency=USD], Money[amount=1.00, currency=USD], Money[amount=100.00, currency=USD]]
```

`source[1]` changed even though the mutation was written through `view`, not through `source` — a `final` array wrapped in `Arrays.asList` is still fully mutable through either handle, because both handles denote the exact same backing storage.

### No diagram

No diagram: the manifest assigns this section none.

### Code

Full program, compiled and run to produce every line above:

```java
import java.math.BigDecimal;
import java.util.Arrays;
import java.util.Currency;

public class FinalArrayMutation {

    record Money(BigDecimal amount, Currency currency) {}

    static final class DepositTiers {
        static final Money[] DEPOSIT_TIERS = {
            new Money(new BigDecimal("10.00"), Currency.getInstance("USD")),
            new Money(new BigDecimal("50.00"), Currency.getInstance("USD")),
            new Money(new BigDecimal("100.00"), Currency.getInstance("USD"))
        };
    }

    static void tamper() {
        DepositTiers.DEPOSIT_TIERS[0] =
            new Money(new BigDecimal("999999.00"), Currency.getInstance("USD"));
    }

    public static void main(String[] args) {
        System.out.println("before: " + Arrays.toString(DepositTiers.DEPOSIT_TIERS));
        tamper();
        System.out.println("after:  " + Arrays.toString(DepositTiers.DEPOSIT_TIERS));

        Money[] source = DepositTiers.DEPOSIT_TIERS;
        var view = Arrays.asList(source);
        view.set(1, new Money(new BigDecimal("1.00"), Currency.getInstance("USD")));
        System.out.println("array through view mutation: " + Arrays.toString(source));
    }
}
```

### Gotcha

**Pitfall:** the wrong belief is "I marked it `final static`, so it's a safe constant to expose." `final` on an array field freezes the reference, never the contents, so any class that can see the field can mutate its elements directly, and wrapping it in `Arrays.asList` does not fix this — the view still writes through to the same storage. The fix is to never expose the raw array: return `array.clone()`, or expose an unmodifiable `List`, or move to `EnumSet`/`EnumMap` when the domain fits.

`**Interview:**` "Can you make an array truly immutable in Java?" — no, not the array itself, at any Java version; you can only make the *reference* to it `final`, and the standard fix is to never let the raw array escape — clone it out, or don't use an array for the public contract at all.

> `final` on an array variable freezes which array the variable points at, not the elements inside it — there is no modifier or library array type in Java that makes an array's contents unmodifiable.

## 3. `array.clone()` is a shallow copy (1.22.7)

**Concept.** `clone()` on an array copies the slots — one assignment per slot, top to bottom. A slot holding a primitive value copies that value; the two arrays are then completely independent. A slot holding a *reference* copies the reference, not the object it points at; the two arrays end up with different slots pointing at the *same* objects. For a one-dimensional array of records that distinction barely matters if the records are immutable. For a two-dimensional array it matters immediately, because a `long[][]`'s outer array holds references to `long[]` rows, and cloning the outer array clones exactly one level — the rows themselves are shared, unclone.

### Why it exists

Arrays predate `Cloneable` as a general contract, and `Object.clone()`'s native, JVM-implemented behavior — a raw, field-by-field bitwise copy of the object's storage — is exactly what an array's `clone()` does, because an array's "fields" are its slots. That is the cheapest possible copy the JVM can produce without knowing anything about what the slots mean; going one level deeper (copying what a reference slot points at, and what *that* points at) is a decision only the caller can make correctly, because only the caller knows whether the referenced objects are meant to be shared or duplicated. The JDK gave arrays the cheap, shallow, universally-correct-for-primitives version and left "does the referenced state need copying too" as the caller's problem — the same reasoning `Object.clone()` and the `Cloneable` contract embody generally; that contract and the deep-versus-shallow copying question as a subject belong to `../objects-equality-and-lifecycle/01c-object-methods.md` and `../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`, and are not re-argued here.

### The mechanism

`[BUILD]` One program, three cases, printed identity comparisons rather than assertions of the result:

```java
long[] stakes = {420, 815, 1200};
long[] stakesCopy = stakes.clone();
stakesCopy[0] = 999;
```

Case 1, `long[]` — a complete, independent copy, because every slot holds a primitive value:

```
long[] independent: original[0]=420 copy[0]=999
```

Case 2, a reference-typed array — the clone's slots point at the *same* objects as the original's slots:

```java
CashEntry[] batch = { new CashEntry(UUID.randomUUID(), new Money(new BigDecimal("4.20"), Currency.getInstance("USD"))) };
CashEntry[] batchCopy = batch.clone();
```

```
same element reference: true
```

`batch[0] == batchCopy[0]` is `true` — two different array objects, but slot 0 in each points at the exact same `CashEntry`. This is harmless here specifically because `CashEntry` is an immutable record: sharing a reference to something nobody can mutate is indistinguishable from having two independent copies of it. That is the design lesson this leaf teaches — shallow sharing is only safe when what's shared is itself immutable.

Case 3, the one that bites — a two-dimensional array is, underneath, a one-dimensional array of references to one-dimensional arrays:

```java
long[][] ledgerRows = { {1, 2}, {3, 4} };
long[][] rowsCopy = ledgerRows.clone();
rowsCopy[1][0] = 99;
```

```
row aliasing visible through original: original[1][0]=99
same row reference: true
```

`ledgerRows.clone()` copied the *outer* array's slots — each of which is a reference to a `long[]` row — so the clone's row 1 and the original's row 1 are the same `long[]` object. Mutating `rowsCopy[1][0]` is not writing into a copy of row 1; it is writing into the one and only row 1, visible from both the original and the "copy." This is exactly why `Arrays.deepEquals` and `Arrays.deepToString` exist as separate methods from `Arrays.equals`/`Arrays.toString` — the shallow versions compare or print the outer array's element references (or, for a `long[][]`, would need `equals`/`toString` on each row, which the plain versions do not descend into), and a shallow `clone()` is the reason a shallow `equals` is insufficient the moment you have nested arrays. `01b-array-utilities-and-arraycopy.md` owns the full `Arrays` surface including `deepEquals`/`deepToString`; the connection to make here is only that clone's shallowness is the same shallowness those methods exist to see past.

One line on the type fact from `01-basics.md`: `array.clone()` is declared to return the array's own covariant type — `CashEntry[] copy = batch.clone();` needs no cast — unlike `Object.clone()` on an ordinary class, which returns `Object` and forces a cast at every call site. That asymmetry, and the `Cloneable` contract behind it, is `../objects-equality-and-lifecycle/01c-object-methods.md`'s subject, not re-argued here.

Three deep-copy recipes for the `long[][]` case, since the JDK ships no library deep-copy for arrays at all:

| Recipe | Code shape | Cost |
|---|---|---|
| Manual per-row loop | `for (i) deep[i] = original[i].clone();` | One outer allocation plus one `clone()` per row — the most explicit, easiest to get right for jagged arrays |
| `Arrays.stream` mapped over `long[]::clone` | `Arrays.stream(outer).map(long[]::clone).toArray(long[][]::new)` | Same underlying work as the loop, routed through a stream; readable, slightly more allocation from the stream pipeline itself |
| Construct new elements | `new CashEntry(UUID.randomUUID(), row.amount())` per element | Needed instead of `clone()` when the elements themselves are mutable and sharing them (as in Case 2) would be unsafe — the only recipe that produces genuinely independent *objects*, not just independent array structure |

`[PROVE]` discharged: run and print, on JDK 21.0.7:

```
manual deep copy isolated: original[1][0]=99 deep[1][0]=-1
stream deep copy isolated: original[0][0]=1 deep[0][0]=-2
```

Both recipes leave the original untouched after mutating the "deep" copy — confirming the row-level independence the shallow `clone()` in Case 3 did not provide.

Last: `Arrays.copyOf`, `copyOfRange`, and `System.arraycopy` all copy at exactly this same depth — one level of slots, references-not-referents — so a `Money[][]` produced by `Arrays.copyOf` still shares its inner rows with the source, for the identical reason `clone()` does. `01b-array-utilities-and-arraycopy.md` owns all three in full, including `System.arraycopy`'s parameter order; the fact to carry forward is only that "shallow" is not a `clone()`-specific quirk, it is what every array-copying primitive in the JDK does.

### No diagram

No diagram: the manifest assigns this section none; the printed identity comparisons above are the picture.

### Code

Full program, compiled and run to produce every line above:

```java
import java.math.BigDecimal;
import java.util.Arrays;
import java.util.Currency;
import java.util.UUID;

public class CloneShallow {

    record Money(BigDecimal amount, Currency currency) {}
    record CashEntry(UUID id, Money amount) {}

    public static void main(String[] args) {
        long[] stakes = {420, 815, 1200};
        long[] stakesCopy = stakes.clone();
        stakesCopy[0] = 999;
        System.out.println("long[] independent: original[0]=" + stakes[0] + " copy[0]=" + stakesCopy[0]);

        CashEntry[] batch = { new CashEntry(UUID.randomUUID(), new Money(new BigDecimal("4.20"), Currency.getInstance("USD"))) };
        CashEntry[] batchCopy = batch.clone();
        System.out.println("same element reference: " + (batch[0] == batchCopy[0]));

        long[][] ledgerRows = { {1, 2}, {3, 4} };
        long[][] rowsCopy = ledgerRows.clone();
        rowsCopy[1][0] = 99;
        System.out.println("row aliasing visible through original: original[1][0]=" + ledgerRows[1][0]);
        System.out.println("same row reference: " + (ledgerRows[1] == rowsCopy[1]));

        long[][] manualDeep = new long[ledgerRows.length][];
        for (int i = 0; i < ledgerRows.length; i++) {
            manualDeep[i] = ledgerRows[i].clone();
        }
        manualDeep[1][0] = -1;
        System.out.println("manual deep copy isolated: original[1][0]=" + ledgerRows[1][0] + " deep[1][0]=" + manualDeep[1][0]);

        long[][] streamDeep = Arrays.stream(ledgerRows).map(long[]::clone).toArray(long[][]::new);
        streamDeep[0][0] = -2;
        System.out.println("stream deep copy isolated: original[0][0]=" + ledgerRows[0][0] + " deep[0][0]=" + streamDeep[0][0]);
    }
}
```

### Gotcha

**Pitfall:** the wrong belief is "I called `clone()`, so I have my own independent copy." For any array of reference type, `clone()` only duplicates the outer array's slots — the objects those slots point at, and for a multi-dimensional array the *rows themselves*, are shared between original and clone. Mutating a nested row through the "copy" mutates it for the original too. The fix is to pick one of the three deep-copy recipes above based on whether the elements are immutable (sharing is fine, a shallow clone suffices) or mutable (you need a manual per-element or per-row rebuild).

> `array.clone()` copies exactly one level of slots — primitives are duplicated, references are shared — so a clone of a multi-dimensional array or an array of mutable elements is not independent of the original at any level below the outermost.

## Supporting facts

### `ArrayStoreException` is unchecked and extends `RuntimeException`

It is a subclass of `RuntimeException` (via `IndexOutOfBoundsException`'s sibling hierarchy — specifically it extends `RuntimeException` directly), so it is never declared in a `throws` clause and the compiler never forces a `catch`. **Gotcha:** because it is unchecked, a covariant-array store bug can ship to production with zero compile-time signal; the only defense is the escape hatches in §1, not a `catch` block bolted on afterward.

> `ArrayStoreException` is an unchecked exception thrown by the JVM at the point of an `aastore` that violates the array's actual component type.

### Autoboxing does not exempt wrapper arrays from covariance

`Integer[]` is exactly as covariant as any other reference array — it is `Object[]`'s subtype rules, not a primitive rule, that apply, because `Integer` is a reference type. A `Number[]` reference pointing at an actual `Integer[]` will throw `ArrayStoreException` the moment code stores a `Double` such as `3.14` into it, for the identical reason `LedgerEntry[]` does in §1. **Gotcha:** it is easy to assume boxed-numeric arrays behave like primitive arrays because the values "feel primitive" — they do not; only `int[]`, `long[]`, `double[]`, and the other seven true primitive-component arrays are exempt from the check.

> Wrapper-type arrays such as `Integer[]` and `Long[]` are reference arrays and are fully covariant and fully checked by `aastore`, unlike their primitive-component counterparts.

### `Object[].clone()` still needs no cast, but `Object.clone()` alone does

Any array's `clone()` — including `Object[]`'s — is specified to return the exact same array type it was called on, which is why `CashEntry[] copy = batch.clone();` compiles with no cast even though `Object`'s own `clone()` is declared to return `Object`. **Gotcha:** this makes array cloning look like it uses covariant return types the way a normal method override can — it does, but the JVM special-cases arrays' `clone()` at the bytecode level rather than generating an ordinary override; `../objects-equality-and-lifecycle/01c-object-methods.md` has the full mechanism.

> Every array type overrides `clone()` with a covariant return type built into the array's synthesised class, so no cast is needed at the call site the way one is for `Object.clone()`.

## Pitfalls

### "If my code compiled, the array only ever holds what I declared it to hold"

**Wrong**

```java
LedgerEntry[] widened = cashBatch;   // cashBatch is actually CashEntry[3]
postFirstEntry(widened, new BonusEntry(UUID.randomUUID(), stake));
// throws at runtime:
// Exception in thread "main" java.lang.ArrayStoreException: ArrayStoreDemo$BonusEntry
//     at ArrayStoreDemo.postFirstEntry(ArrayStoreDemo.java:16)
```

**Right**

```java
// keep the exact allocated type all the way through, never widen the reference:
CashEntry[] cashBatch = new CashEntry[3];
postCashEntry(cashBatch, new CashEntry(UUID.randomUUID(), stake)); // compiles AND runs safely

// or: switch to a generic collection, which rejects the mismatch at compile time
List<CashEntry> cashList = new ArrayList<>();
cashList.add(new CashEntry(UUID.randomUUID(), stake));
// cashList.add(new BonusEntry(UUID.randomUUID(), stake));  // would not even compile
```

**Why people believe it:** the compiler accepted every line up to the store, and Java engineers correctly learn to trust `javac` for generics-based collections, where a compile error really would have appeared. Arrays are the one corner of the type system where "it compiled" and "it is type-safe" diverge, because covariance was chosen deliberately, in 1995, to make polymorphic array code possible before generics existed.

### "`final` on my array field makes it a safe, read-only constant"

**Wrong**

```java
static final Money[] DEPOSIT_TIERS = buildTiers();
// anywhere else in the codebase, no cast, no reflection:
DepositTiers.DEPOSIT_TIERS[0] = new Money(new BigDecimal("999999.00"), Currency.getInstance("USD"));
// after: [Money[amount=999999.00, currency=USD], Money[amount=50.00, currency=USD], Money[amount=100.00, currency=USD]]
```

**Right**

```java
private static final Money[] DEPOSIT_TIERS = buildTiers();

static List<Money> depositTiers() {
    return List.of(DEPOSIT_TIERS);   // structurally unmodifiable; .set() throws
}
// or, if callers genuinely need an array:
static Money[] depositTiersSnapshot() {
    return DEPOSIT_TIERS.clone();    // caller's copy; mutating it never touches the original
}
```

**Why people believe it:** `final` genuinely does make primitives and `String` fields behave like constants — `static final int MAX_TIERS = 3` really cannot change — and it is a short, understandable leap to expect the same guarantee from `final Money[] DEPOSIT_TIERS`. The leap fails because `final` only ever constrains the reference, and an array's mutable state lives entirely behind that reference, out of `final`'s reach.

### "`clone()` gives me an independent copy of my array"

**Wrong**

```java
long[][] ledgerRows = { {1, 2}, {3, 4} };
long[][] rowsCopy = ledgerRows.clone();
rowsCopy[1][0] = 99;
// original[1][0] is now 99 too — the "copy" shared row 1 with the original
```

**Right**

```java
long[][] rowsCopy = new long[ledgerRows.length][];
for (int i = 0; i < ledgerRows.length; i++) {
    rowsCopy[i] = ledgerRows[i].clone();   // clone each row too — now genuinely independent
}
rowsCopy[1][0] = 99;   // original[1][0] is untouched
```

**Why people believe it:** `clone()` on a `long[]` really is a complete, independent copy, and that is most people's first and most memorable experience of array cloning, so the mental model generalizes to "clone always gives independence" — it holds for exactly one level of primitive slots and stops being true the moment a slot itself holds a reference, which is every row of every multi-dimensional array.

## Cheat sheet

| Fact | One-liner |
|---|---|
| Array covariance | `CashEntry[]` is a subtype of `LedgerEntry[]`; lets covariant assignment compile |
| Enforcement point | `aastore` bytecode instruction, checked on every reference-array store, no separate `checkcast` |
| Primitive contrast | `lastore`, `iastore`, and the other primitive store instructions never check — no covariance exists for primitive arrays |
| `ArrayStoreException` | unchecked `RuntimeException`; message names the *rejected* class, not the array's declared type |
| Escape hatches | exact array type (no widening); `List<T>` (compile-time check); primitive array (no check exists) |
| `final` on an array | freezes the reference only; slots remain fully mutable through any handle |
| No immutable array type | none exists at any Java version; only `array.clone()`, `List.of`, `EnumSet`/`EnumMap` fake it |
| `Arrays.asList(arr)` | a *view*, not a copy; writes through it reach `arr` and vice versa |
| `array.clone()` depth | exactly one level: primitives duplicated, references shared |
| Multi-dimensional clone | outer array copied; every row object is the *same* row as the original |
| Deep copy in the JDK | no library method does it for arrays; manual loop, `stream().map(T[]::clone)`, or rebuild elements |
| `clone()` return type | covariant per array type — `CashEntry[] c = batch.clone();` needs no cast |

## Self-test

**Q1.** Why does `ArrayStoreException` exist, and why is it thrown at runtime instead of caught by the compiler?

<details><summary>Answer</summary>

It exists because arrays are covariant — `CashEntry[]` is a compile-time subtype of `LedgerEntry[]` — a rule from Java 1.0, before generics gave any other way to write one method that processes every reference-array type. Covariance means the compile-time declared element type of an array reference can differ from the array's actual, physical, allocated component type. The compiler only ever sees the declared type at a given call site, so it cannot know, statically, that a `LedgerEntry[]`-typed reference is really backed by a `CashEntry[]` allocation. The one place both the declared type and the actual allocated type are simultaneously available is the store itself, so the JVM checks there, inside the `aastore` instruction, on every execution, and throws `ArrayStoreException` naming the rejected class when the check fails.

</details>

**Q2.** What is the difference in the bytecode between storing into a `long[]` and storing into a `LedgerEntry[]`?

<details><summary>Answer</summary>

Storing into a `long[]` compiles to `lastore`, which writes the value's bit pattern into the slot with no type comparison at all — there is nothing to check because `long[]` has no covariant relationship with any other array type. Storing into a `LedgerEntry[]` compiles to `aastore`, which is specified to compare the runtime class of the value being stored against the array's actual component type before writing, and throws `ArrayStoreException` if they are incompatible. There is no separate `checkcast` instruction added by `javac` for either case — the check for `aastore` is part of that single instruction's own specified behavior.

</details>

**Q3.** Given a `static final Money[] DEPOSIT_TIERS` array field, can any code outside the declaring class change the contents of `DEPOSIT_TIERS`? If so, how, and if not, why not?

<details><summary>Answer</summary>

Yes, trivially: any code with visibility to the field can write `DEPOSIT_TIERS[i] = someOtherMoney;` with no cast and no reflection, because that statement writes through the array reference into the array's storage — it never reassigns the field `DEPOSIT_TIERS` itself, which is the only thing `final` protects. `final` on a field constrains reassignment of the field's own value (here, which array object it points at); it has no mechanism to reach into that array object's mutable slots. There is no modifier or wrapper type in Java that makes array elements themselves unmodifiable — the real fixes are to never expose the raw array (return `array.clone()` or an unmodifiable `List` from an accessor instead).

</details>

**Q4.** Why can't a `static final` array field be constant-folded by `javac` the way `static final int MAX_TIERS = 3` is?

<details><summary>Answer</summary>

Constant folding via the class file's `ConstantValue` attribute only applies to `final` fields of a primitive type or `String` initialized with a compile-time constant expression, because those are the only types the language guarantees stay unchanged forever after initialization — `javac` can safely inline their value at every use site. An array reference fails this immediately: even though the reference itself cannot be reassigned once `final`, the array object it points at is mutable state, so the "value" is not actually constant in any sense the class-file format can represent. Every reader has to fetch the live array and read its current slots; nothing can be inlined.

</details>

**Q5.** What does `Arrays.asList(array)` return, and how does that interact with an array declared `final`?

<details><summary>Answer</summary>

`Arrays.asList(array)` returns a fixed-size `List` view backed directly by the given array — not a copy. Reads and writes through the list (via `get`/`set`) go straight to the same underlying storage as the array. This means a `final` array wrapped in `Arrays.asList` is exactly as mutable as it always was: `final` never stopped element mutation through the array reference, and this view doesn't add any new protection — it just gives you a second handle onto the identical mutable storage, so a `set()` through the view is visible immediately when you read the original array.

</details>

**Q6.** If `batch.clone()` is called on a `CashEntry[]` where `CashEntry` is an immutable record, is the shallow copy actually safe? What changes if `CashEntry` were mutable?

<details><summary>Answer</summary>

Yes, it's safe in that case specifically because sharing a reference to something nobody can ever mutate is behaviorally indistinguishable from having an independent copy of it — `batch[0] == batchCopy[0]` is `true`, but since `CashEntry` is an immutable record, nothing can ever observe a difference between "the same object" and "an equal, independent object." If `CashEntry` were mutable, that guarantee disappears: mutating the shared object through one array would be visible through the other, which is exactly the multi-dimensional-array bug in a different shape — the fix is the same, either clone each element individually or construct new element instances for the copy.

</details>

**Q7.** Given `long[][] ledgerRows` and `long[][] rowsCopy = ledgerRows.clone()`, what does `rowsCopy[1][0] = 99;` actually mutate, and why?

<details><summary>Answer</summary>

It mutates the one and only row-1 array, which both `ledgerRows[1]` and `rowsCopy[1]` reference — `ledgerRows[1] == rowsCopy[1]` is `true` after the clone. `clone()` on the outer `long[][]` only duplicates the outer array's slots, and each of those slots holds a *reference* to a `long[]` row, not the row's contents; cloning copies the reference, so both the original and the clone end up pointing at the identical row objects. `rowsCopy[1][0] = 99` therefore writes into that shared row, and `ledgerRows[1][0]` reads back `99` as well, even though `ledgerRows` was never touched by name.

</details>

**Q8.** Name two ways to produce a genuinely independent deep copy of a `long[][]`, and explain why neither is a single library call.

<details><summary>Answer</summary>

One: a manual per-row loop — allocate a new outer array of the same length, then set `deep[i] = original[i].clone()` for each row, cloning every row individually rather than relying on the outer clone to do it. Two: `Arrays.stream(original).map(long[]::clone).toArray(long[][]::new)`, which performs the identical per-row cloning through a stream pipeline instead of an explicit loop. Neither is a single library call because the JDK ships no `Arrays.deepClone` or equivalent — `Arrays.copyOf`, `copyOfRange`, and `System.arraycopy` are all exactly as shallow as `clone()` itself, so achieving genuine depth always requires explicitly cloning (or rebuilding) each nested level yourself.

</details>

## Open questions

- **Unverified:** whether the JIT actually eliminates the `aastore` type check for a given call site under realistic escape-analysis conditions in this codebase's hot paths, and by how much that changes measured throughput at the ledger's 13,600/sec peak write rate. Settling it needs a JMH microbenchmark against representative `LedgerEntry[]`-shaped code plus `-XX:+PrintCompilation`/JIT-compilation-log inspection on this machine's JDK 21.0.7, which has not been run.

---

**Leaves covered:** 1.22.5, 1.22.6, 1.22.7 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 580
