# 03 Java Core — The limits of erasure, and capture conversion — INTERNALS (§3.5, 3.5.11–3.5.13)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Heap pollution and `@SafeVarargs`](03c-internals-heap-pollution-and-safevarargs.md) · Next: [Why erasure, and super type tokens](03e-internals-why-erasure-and-super-type-tokens.md)

This file walks three places where the source language expresses something the class file has no room for, and shows that the compiler's three responses to that shortage are genuinely three different responses, not one rule wearing three costumes. Given two overloads whose descriptors coincide, `javac` refuses to compile (§1) — a structural impossibility in the `methods` table, not a style objection. Given a `static` field on a generic class, `javac` compiles it, but silently collapses every parameterisation onto the single slot the class file actually has room for (§2) — no error, no warning, just one shared number where the source reads like there ought to be several. Given a wildcard-typed expression, `javac` cannot name the unknown type it is reasoning about, so it invents a fresh name for the duration of one expression and prints that invented name — `CAP#1` — in the diagnostic (§3), then discards it before anything reaches a class file. Refuse, collapse, invent: three different reactions to the same underlying fact, that the class file cannot always hold what the source said. `02c-inference-and-generic-limits.md` already gave the overload clash and the static-member prohibition at the rule-and-workaround level for an INTERMEDIATE reader; this file supplies the class-file mechanism under each of the three, plus the one topic no earlier file owned end to end: reading a `CAP#1` diagnostic. `01a-erasure-and-its-consequences.md` owns erasure itself and its consequences list; `03-internals-erasure.md` owns what erasure emits and the `Signature` attribute; `03a-internals-bridge-methods.md` owns bridge methods, which §1 below depends on directly; `03e-internals-why-erasure-and-super-type-tokens.md` owns why Java chose erasure at all — none of that argument is repeated here. All `javac`/`javap`/`java` output below is real, produced on Oracle JDK 21.0.7 (`21.0.7+8-LTS-245`) — the build is named once here and every quoted diagnostic in this file came from it.

## 1. The erased overload clash, from the class-file side (3.5.11)

A `.class` file's `methods` table is not a list keyed by "what a human would call this method" — it is keyed by the pair (name, descriptor), and JVMS 21 §4.6 is explicit that a class file may not contain two `method_info` entries with the same name-and-descriptor pair. Everything in this section is that one sentence working itself out against real generic overloads.

### Why it exists

Before generics, two overloads with different parameter *types* always erased to different descriptors, because there was no erasure step — the source parameter type and the descriptor's field-type entry were the same thing. Generics broke that guarantee: a type parameter's descriptor is the erasure of its leftmost bound (`03-internals-erasure.md` derives this in full), so two source signatures that look different — `List<CashEntry>` and `List<BonusEntry>` — can erase to the identical descriptor. `javac` has to check for this at compile time, because the class file format gives it no way to represent the collision if it let both through.

### The mechanism

`[PROVE]`, worked from the file format rather than asserted: JVMS 21 §4.6 states of the `methods` table that each value must be a `method_info` structure "giving a complete description of a method in this class or interface"; if neither of its `ACC_NATIVE` and `ACC_ABSTRACT` flags are set, that structure "also supplies the code for the method." Separately, §4.6 requires the pair (name index, descriptor index) to be unique among the class's own members — two entries sharing both would be indistinguishable to anything that resolves a method by name-and-descriptor, which is exactly how `invokevirtual`/`invokestatic`/`invokespecial` resolution and reflection's `getDeclaredMethod` both work. Two source declarations that erase to one descriptor are, from the class file's point of view, one entry being asked to hold two different bodies — not a style problem, a structural impossibility in a table whose whole contract is "one row per (name, descriptor)."

Compile the case directly:

```java
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

interface LedgerEntry { UUID id(); BigDecimal amount(); }
record CashEntry(UUID id, BigDecimal amount) implements LedgerEntry {}
record BonusEntry(UUID id, BigDecimal amount) implements LedgerEntry {}

class FundsLedger {
    void post(List<CashEntry> entries) { }
    void post(List<BonusEntry> entries) { }
}
```

`javac -Xlint:all` on JDK 21.0.7:

```
Clash1.java:11: error: name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure
    void post(List<BonusEntry> entries) { }
         ^
1 error
```

`List<CashEntry>` and `List<BonusEntry>` both erase to the raw `List`, so both declarations reduce to the identical descriptor `(Ljava/util/List;)V`. `javac` catches this during the member-declaration pass, before it ever attempts to emit a `methods` table entry — it is not that the class file *would* fail to build; the compiler refuses to try, because JVMS 21 §4.6's uniqueness rule guarantees the attempt is doomed. `02c-inference-and-generic-limits.md` §3 (2.7.13) already gave this exact diagnostic and the workaround table — rename, add a distinguishing `Class<T>` parameter, or collapse to one method with an `instanceof`-based `switch`; this file does not repeat that table.

`[PROVE]` again, the sharper form that proves the rule is about descriptors and not about "having type arguments": a generic method whose type parameter is bounded, alongside a plain overload whose parameter type happens to be that same bound.

```java
interface LedgerEntry { UUID id(); BigDecimal amount(); }
record CashEntry(UUID id, BigDecimal amount) implements LedgerEntry {}

class FundsLedger {
    <T extends LedgerEntry> void post(T entry) { }
    void post(LedgerEntry entry) { }
}
```

```
Clash2.java:9: error: name clash: post(LedgerEntry) and <T>post(T) have the same erasure
    void post(LedgerEntry entry) { }
         ^
  where T is a type-variable:
    T extends LedgerEntry declared in method <T>post(T)
1 error
```

Neither declaration has a type-argument-carrying parameter here — one parameter is the plain type `LedgerEntry`, the other is a type variable `T`. They still clash, because `T`'s erasure is the erasure of its leftmost bound, `LedgerEntry`, so both descriptors are `(LLedgerEntry;)V`. This is the proof that the rule reads descriptors, not source syntax: nothing about a parameterised type is required to trigger it, only two declarations whose erased parameter types coincide.

A third shape, in an inheritance chain, produces a differently-worded diagnostic:

```java
class AbstractStore<E extends LedgerEntry> {
    void save(E entry) { }
}

class CashEntryStore extends AbstractStore<CashEntry> {
    <T extends LedgerEntry> void save(T entry) { }
}
```

```
Clash3.java:12: error: name clash: save(T) in CashEntryStore and save(CashEntry) in AbstractStore have the same erasure, yet neither overrides the other
    <T extends LedgerEntry> void save(T entry) { }
                                 ^
  where T is a type-variable:
    T extends LedgerEntry declared in method <T>save(T)
1 error
```

Work the descriptors through directly: `T`'s bound is `LedgerEntry`, so the new `<T>save(T)` declared on `CashEntryStore` erases to `(LLedgerEntry;)V`. `save(E)` reads as `save(CashEntry)` at the source level inside `CashEntryStore`, but the class file inherits `AbstractStore`'s own compiled descriptor — the erasure of `E`'s bound, `LedgerEntry` — so the inherited method's descriptor is also `(LLedgerEntry;)V` (`03a-internals-bridge-methods.md` §1 derives exactly this erasure). Both land on `(LLedgerEntry;)V`. `javac` cannot treat the new declaration as an override — an override requires a matching signature under the override rules, and `<T>save(T)`'s signature does not match `save(E)`'s — so it is neither a legal override nor a legal overload; hence the more elaborate wording, "yet neither overrides the other."

| Source shape | Diagnostic | Structural rule violated |
|---|---|---|
| Two plain generic overloads (`post(List<CashEntry>)`, `post(List<BonusEntry>)`) | `name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure` | JVMS §4.6 (name)+(descriptor) uniqueness in the `methods` table |
| Generic-method / plain-parameter overload with matching erasure (`<T extends LedgerEntry> post(T)`, `post(LedgerEntry)`) | `name clash: post(LedgerEntry) and <T>post(T) have the same erasure` (with a `where T is a type-variable` block) | Same rule; proves the descriptor, not the source syntax, is what collides |
| Subclass method erasing onto an inherited method it does not override (`<T> save(T)` alongside inherited `save(E)`) | `name clash: save(T) in CashEntryStore and save(CashEntry) in AbstractStore have the same erasure, yet neither overrides the other` | Same descriptor collision, plus a failed override match under the language's own override rules |

**Insight:** the one case where two descriptors sharing a name *are* allowed to coexist in a class file is exactly the case `03a-internals-bridge-methods.md` §2 walks — return-type-only differences. A method's descriptor includes its return type, so `LedgerEntry create()` (descriptor `()LLedgerEntry;`) and a subclass's narrower `CashEntry create()` (descriptor `()LCashEntry;`) are two genuinely different descriptors, and the `methods` table happily holds both — one as the real override, one as the synthetic bridge that repairs the mismatch for callers dispatching through the wider type. `javap -p -c -v` on that pair, quoted in full in `03a-internals-bridge-methods.md` §2, shows `CashEntry create();` at descriptor `()LCashEntry;` and `LedgerEntry create();` at descriptor `()LLedgerEntry;` sitting side by side in one `methods` table without complaint. Overloading on return type alone is illegal to *write* in Java source (the language has no syntax that lets two source declarations differ only in return type at the same parameter list — the compiler treats that as redeclaring the same method), but the class file underneath has always been able to hold it, which is precisely the room `javac`'s own bridge-generation machinery uses.

**Interview:** "Why can't you overload two methods that both take a generic list?" The one-line answer: overload resolution is a source-level concept, but the class file the compiler must produce identifies a method purely by name and erased descriptor, and JVMS §4.6 forbids two entries sharing both — so two overloads whose type arguments vanish under erasure are, structurally, one entry being asked to do two jobs. Interviewers who press further are checking whether the candidate knows this is a hard file-format wall and not a `javac` heuristic — the return-type contrast above is the fact that separates the two.

## 2. Static fields shared across every parameterisation (3.5.12)

`Repository<CashEntry>` and `Repository<BonusEntry>` are not two classes at runtime. They are one loaded `Class` object, `Repository`, viewed through two different compile-time lenses that both vanish after `javac` finishes. A `static` field belongs to that one `Class` object, so it has exactly one storage slot regardless of how many parameterisations a program writes at the source level — a counter that looks, at the source level, like it should track "per-`T`" state is actually tracking one shared total.

### Why it exists

This is not a rule the language wrote on purpose so much as a direct corollary of there being exactly one class file per generic declaration (`01a-erasure-and-its-consequences.md` states the consequence; this file supplies the mechanism). `static` fields were never given per-instantiation storage because generics arrived as a source-level, compile-time-checked feature layered onto a class-file format that predates them and has no notion of "this field, but one copy per type argument." The alternative — reifying generics so each parameterisation got its own runtime identity and its own static storage — is the design `03e-internals-why-erasure-and-super-type-tokens.md` argues Java deliberately did not take.

### The mechanism

`[PROVE]` by running it, not by asserting it. A `Repository<T extends LedgerEntry>` intends `postedCount` as a per-entry-type counter — it looks that way at the call site, since each `Repository<CashEntry>` and `Repository<BonusEntry>` is constructed and used separately:

```java
import java.math.BigDecimal;
import java.util.UUID;

interface LedgerEntry { UUID id(); BigDecimal amount(); }
record CashEntry(UUID id, BigDecimal amount) implements LedgerEntry {}
record BonusEntry(UUID id, BigDecimal amount) implements LedgerEntry {}

class Repository<T extends LedgerEntry> {
    static long postedCount = 0;

    void post(T entry) {
        postedCount++;
    }
}

public class Statics {
    public static void main(String[] args) {
        Repository<CashEntry> cashRepo = new Repository<>();
        Repository<BonusEntry> bonusRepo = new Repository<>();

        cashRepo.post(new CashEntry(UUID.randomUUID(), BigDecimal.TEN));
        cashRepo.post(new CashEntry(UUID.randomUUID(), BigDecimal.ONE));
        cashRepo.post(new CashEntry(UUID.randomUUID(), BigDecimal.TWO));
        bonusRepo.post(new BonusEntry(UUID.randomUUID(), BigDecimal.ONE));

        System.out.println("cashRepo.postedCount = " + Repository.postedCount);
        System.out.println("bonusRepo.postedCount = " + Repository.postedCount);
        System.out.println("cashRepo.getClass() == bonusRepo.getClass(): "
                + (cashRepo.getClass() == bonusRepo.getClass()));
    }
}
```

Three posts through `cashRepo`, one through `bonusRepo`. If the field were really per-parameterisation, the expected output would be `cashRepo.postedCount = 3` and `bonusRepo.postedCount = 1`. Real output on JDK 21.0.7:

```
cashRepo.postedCount = 4
bonusRepo.postedCount = 4
cashRepo.getClass() == bonusRepo.getClass(): true
```

Both read `4` — the total across *both* repositories, not either one's own count — because there is only one counter to increment. `getClass()` returning the same `Class` object for both confirms the mechanism directly: `cashRepo` and `bonusRepo` are, at runtime, both plain instances of the one class `Repository`, with no runtime trace of `CashEntry` or `BonusEntry` anywhere on either object.

`javap -p -v Repository.class` on the same build shows why there was never a second slot to increment:

```
Constant pool:
   #7 = Fieldref           #8.#9          // Repository.postedCount:J
   #8 = Class              #10            // Repository
   #9 = NameAndType        #11:#12        // postedCount:J
{
  static long postedCount;
    descriptor: J
    flags: (0x0008) ACC_STATIC

  void post(T);
    descriptor: (LLedgerEntry;)V
    Code:
       0: getstatic     #7                  // Field postedCount:J
       3: lconst_1
       4: ladd
       5: putstatic     #7                  // Field postedCount:J
       8: return
    Signature: #18                          // (TT;)V
}
```

One `fields` table entry, `static long postedCount;`. One constant-pool `Fieldref`, `#7`, resolving to `Repository.postedCount:J` — a name and a descriptor, nothing else; there is no slot anywhere in a `Fieldref`'s `NameAndType` for "and this copy belongs to the `CashEntry` parameterisation." `getstatic #7` and `putstatic #7` both name that one `Fieldref` regardless of which `Repository<T>` instance called `post`, because `post`'s own bytecode has erased away to operating on `LedgerEntry`-typed values with no `T` left to distinguish by. The `(TT;)V` you see is only the `Signature` attribute, read by reflection and by `javac` itself when it recompiles against this class — it is not consulted by `getstatic`/`putstatic`, which is why it changes nothing about which physical slot gets incremented.

| Fix | Mechanism | Trade |
|---|---|---|
| `Map<Class<?>, Long>` keyed on the entry type | One shared static field, but its *value* is a map from a runtime `Class<?>` token to a per-type count | Needs a `Class<CashEntry>`/`Class<BonusEntry>` token at each call site (`02a-type-tokens-and-generic-reflection.md` owns the token pattern); the map itself is still one shared mutable structure needing its own concurrency care |
| Instance field, not static | `postedCount` moves onto each `Repository` object; `cashRepo` and `bonusRepo` are different objects even though they share a `Class` | Only counts per-*instance*, not per-type — two `Repository<CashEntry>` instances would each keep their own separate count, which may or may not be the actual requirement |
| A separate non-generic holder class per entry type, each with its own static field | `CashEntryCounters.postedCount` and `BonusEntryCounters.postedCount` are two distinct classes, two distinct `Class` objects, two genuinely separate static slots | Duplicated boilerplate per entry type; new entry types need a new class, not just a new type argument |

`01d-recursive-bounds-and-heterogeneous-containers.md` owns the `Map<Class<?>, V>` heterogeneous-container pattern the first row leans on in full; this file only states the one line needed here.

The related-but-different rule, `02c-inference-and-generic-limits.md`'s leaf 2.7.14 — that `static T last;` referring to the *class's own type parameter* does not compile at all — is a distinct prohibition, not the same fact restated. `static long postedCount` above compiled fine and ran; it is merely shared. `static T last;` never gets that far, because `T` itself has no meaning outside an instantiation and the language refuses the declaration outright rather than let a field exist whose declared type cannot be resolved to anything concrete at the class level. One is permitted and silently surprising; the other is forbidden and loud. Do not conflate them.

Also worth stating in one place: static *initialisers* run exactly once per class, at class initialisation, not once per parameterisation and not once per instance — a `static final Map<K, V>` built inside a generic class's `<clinit>` is therefore the same shared, cached structure no matter how many different `T`s the class is used with at the source level. `../classes-and-initialization/03-internals-class-loading-and-init.md` owns the full timing of when `<clinit>` runs relative to first active use; the fact that matters here is only that "once per class" and "once per `Repository`" are the same claim, because there is exactly one class.

**Pitfall:** a per-type static cache, believed per-parameterisation. See below, in the shared Pitfalls section.

**Interview:** "Does each `List<String>` get its own copy of a static field on a generic class?" One-line answer: there is no such thing as "a `List<String>`'s own copy" at runtime — `List` (or any user-defined generic class) loads once, and every static field on it has exactly one slot in that one loaded class, shared by every parameterisation a program ever writes.

> A generic class's static field has exactly one runtime slot, because erasure guarantees exactly one loaded `Class` object regardless of how many parameterisations the source declares.

## 3. Capture conversion, and reading a `CAP#1` diagnostic (3.5.13)

Every wildcard the compiler has to reason about *as a specific, if unknown, type* — rather than merely as "some subtype of X" — gets a name invented for the duration of one expression. That invented name is `CAP#1`, `CAP#2`, `CAP#3`, each one a fresh compiler-only variable. It is not a real type, it is never written by a programmer, it never survives past the one diagnostic or the one piece of internal type-checking it was created for, and it has no representation anywhere in a compiled class file. This section is where every earlier `CAP#1` this batch's INTERMEDIATE-tier files quoted without explaining finally gets explained.

### Why it exists

`?` by itself is not enough for the compiler to type-check certain expressions. Given `List<? extends LedgerEntry> entries`, the compiler knows every element is *some* subtype of `LedgerEntry`, but it does not know it is the *same* subtype across two separate uses of `entries` unless it gives that unknown subtype an actual name to track through the rest of the expression. Capture conversion is that naming step — `JLS 21 §5.1.10` describes it as a conversion from the wildcard-bearing parameterized type to a parameterized type with fresh type variables standing in for each wildcard, so the rest of type-checking has something concrete to reason about for exactly as long as it needs to.

### The mechanism

`[RESEARCH]`, quoted directly from **JLS 21 §5.1.10, Capture Conversion**, clause by clause:

> "There exists a capture conversion from a parameterized type `G<T1,…,Tn>` to a parameterized type `G<S1,…,Sn>`, where, for `1 ≤ i ≤ n`:
> - If `Ti` is a wildcard type argument of the form `?`, then `Si` is a fresh type variable whose upper bound is `Ui[A1:=S1,…,An:=Sn]` and whose lower bound is the null type.
> - If `Ti` is a wildcard type argument of the form `? extends Bi`, then `Si` is a fresh type variable whose upper bound is `glb(Bi, Ui[A1:=S1,…,An:=Sn])` and whose lower bound is the null type.
> - If `Ti` is a wildcard type argument of the form `? super Bi`, then `Si` is a fresh type variable whose upper bound is `Ui[A1:=S1,…,An:=Sn]` and whose lower bound is `Bi`.
> - Otherwise, `Si = Ti`."

Read it against `List<? extends LedgerEntry>`: `G` is `List`, `n` is `1`, `U1` (the declared bound of `List`'s own type parameter `E`) is `Object`. The single argument `? extends LedgerEntry` matches the second bullet, so the captured `S1` is a fresh type variable whose upper bound is `glb(LedgerEntry, Object)` — which reduces to `LedgerEntry`, since `LedgerEntry` is already the more specific of the two — and whose lower bound is the null type. That fresh `S1` is exactly what a diagnostic prints as `CAP#1 extends LedgerEntry from capture of ? extends LedgerEntry`. `List<? super BonusEntry>` matches the third bullet instead: the fresh variable's upper bound stays at `List`'s own declared bound (`Object`, since `List<E>` declares no bound on `E`), and its lower bound becomes `BonusEntry` — printed as `CAP#1 extends Object super: BonusEntry from capture of ? super BonusEntry`.

The clause that matters most for reading diagnostics is "fresh": every application of capture conversion to a wildcard produces a brand-new type variable, and **two separate `?` occurrences — even two occurrences of the textually identical `? extends LedgerEntry` — capture to two different fresh variables that the compiler is not permitted to assume are equal.** Prove it:

```java
import java.util.List;

interface LedgerEntry { java.util.UUID id(); java.math.BigDecimal amount(); }
record CashEntry(java.util.UUID id, java.math.BigDecimal amount) implements LedgerEntry {}

class FundsLedger {
    void reconcile(List<? extends LedgerEntry> source, List<? extends LedgerEntry> destination) {
        destination.addAll(source);
    }
}
```

```
Capture1.java:10: error: incompatible types: List<CAP#1> cannot be converted to Collection<? extends CAP#2>
        destination.addAll(source);
                           ^
  where CAP#1,CAP#2 are fresh type-variables:
    CAP#1 extends LedgerEntry from capture of ? extends LedgerEntry
    CAP#2 extends LedgerEntry from capture of ? extends LedgerEntry
```

Read this the way the diagnostic wants to be read, piece by piece: `CAP#1` and `CAP#2` are the names the compiler invented for `source`'s wildcard and `destination`'s wildcard respectively — two occurrences of the same written text, `? extends LedgerEntry`, captured independently because capture conversion has no notion of "this wildcard occurrence and that one must agree." The `where CAP#1,CAP#2 are fresh type-variables:` block underneath is `javac` disclosing exactly what it invented and why, and the trailing `from capture of ? extends LedgerEntry` clause on each line is the whole key to the error — it names the exact wildcard occurrence in your source that produced that particular capture variable. Without that clause the error would just say two unrelated-looking type variables don't match; with it, the reader can walk back to the two parameter declarations and see that they are two independent unknowns, never guaranteed equal, which is exactly why `addAll` cannot type-check: nothing forces `destination`'s element type to be `source`'s element type, or even a supertype of it.

A single-capture case, using a lower bound, shows the `? super` clause of the JLS text landing in a real diagnostic:

```java
record BonusEntry(java.util.UUID id, java.math.BigDecimal amount) implements LedgerEntry {}

class FundsLedger {
    void voidStake(List<? super BonusEntry> reversals) {
        reversals.set(0, new CashEntry(java.util.UUID.randomUUID(), java.math.BigDecimal.ONE));
    }
}
```

```
Capture2.java:11: error: incompatible types: CashEntry cannot be converted to CAP#1
        reversals.set(0, new CashEntry(UUID.randomUUID(), BigDecimal.ONE));
                         ^
  where CAP#1 is a fresh type-variable:
    CAP#1 extends Object super: BonusEntry from capture of ? super BonusEntry
```

`CAP#1`'s upper bound is `Object` (`List<E>`'s own undeclared bound) and its lower bound is `BonusEntry`, matching the third JLS bullet exactly. The compiler only knows `reversals` holds *some* supertype of `BonusEntry` — it could be `LedgerEntry`, could be `Object` — so it refuses `CashEntry`, which is not provably assignable to an unknown that might be as narrow as `BonusEntry` itself. `02-in-anger.md` owns the wildcard-capture *helper-method* idiom that exists precisely to give this fresh variable a real, spellable name (`<T> void voidStake(List<T> reversals, T entry)`) instead of leaving it anonymous; one line and a pointer is all this file needs — naming the type parameter directly means the compiler is told the identity once, in the declaration, instead of inventing and forgetting a fresh one per call.

`01b-variance-and-wildcards.md` and `02-in-anger.md` both quoted `CAP#1`/`CAP#2` diagnostics of this shape without deriving them; this section is what those quotes were standing on.

`[PROVE]` that capture never reaches the class file: compile a method whose body relies on capture conversion to type-check at all, and read its `Signature` attribute.

```java
class FundsLedger {
    LedgerEntry firstOf(List<? extends LedgerEntry> entries) {
        return entries.get(0);
    }

    void fill(List<? super CashEntry> reversals, CashEntry entry) {
        reversals.set(0, entry);
    }
}
```

`javap -p -c -v FundsLedger.class` on JDK 21.0.7:

```
  LedgerEntry firstOf(java.util.List<? extends LedgerEntry>);
    descriptor: (Ljava/util/List;)LLedgerEntry;
    Code:
       0: aload_1
       1: iconst_0
       2: invokeinterface #7,  2            // InterfaceMethod java/util/List.get:(I)Ljava/lang/Object;
       7: checkcast     #13                 // class LedgerEntry
      10: areturn
    Signature: #26                          // (Ljava/util/List<+LLedgerEntry;>;)LLedgerEntry;

  void fill(java.util.List<? super CashEntry>, CashEntry);
    descriptor: (Ljava/util/List;LCashEntry;)V
    Code:
       0: aload_1
       1: iconst_0
       2: aload_2
       3: invokeinterface #15,  3           // InterfaceMethod java/util/List.set:(ILjava/lang/Object;)Ljava/lang/Object;
       8: pop
       9: return
    Signature: #29                          // (Ljava/util/List<-LCashEntry;>;LCashEntry;)V
```

`entries.get(0)` type-checked in the source only because capture conversion gave that call site a fresh variable to reason about; by the time `javac` emits bytecode, `firstOf`'s descriptor has erased that fresh variable away entirely, to plain `(Ljava/util/List;)LLedgerEntry;`, and the only place any trace of the wildcard survives is the `Signature` attribute — `(Ljava/util/List<+LLedgerEntry;>;)LLedgerEntry;`. `[RESEARCH]`, decoded against **JVMS 21 §4.7.9.1**'s `TypeArgument` grammar (`FieldType | * | + FieldType | - FieldType`): `+LLedgerEntry;` is `? extends LedgerEntry` (the `+` production), and in `fill`'s signature, `-LCashEntry;` is `? super CashEntry` (the `-` production); the unbounded `*` (for a bare `?`) appears nowhere in either signature because neither example uses one, but is the same grammar's third alternative. `03-internals-erasure.md` walks the `Signature` attribute's grammar for plain type variables and parameterized types; this is the one piece of that grammar — the wildcard markers — that file had no reason to need and this one does. Nowhere in either descriptor or either `Signature` string does `CAP#1` or any invented name appear — capture conversion is checked once, during type-checking, and is fully discharged before code generation ever begins. It has no run-time or class-file identity at all, which is also why capture conversion "never requires a special action at run time and therefore never throws an exception at run time" (the JLS's own closing sentence on §5.1.10) — there is nothing left of it by the time there is any run time to speak of.

**Insight:** the reason a capture-helper method (`02-in-anger.md`'s idiom) fixes the two-wildcard failure above is now visible in the JLS text itself: a *declared* type parameter `<T>` is not "fresh" per call in the way a captured wildcard is — it is one name, bound once per call, and every use of `T` inside that one method body refers to the same binding. Capture conversion, by contrast, invents a new `Si` at every site a wildcard-bearing type is used, with no promise that two sites agree. Naming the unknown turns two independent captures into one shared type variable — the exact gap the `CAP#1`/`CAP#2` diagnostic above is complaining about.

**Interview:** "What is `CAP#1` in a `javac` error?" One-line answer: a fresh, compiler-invented type variable standing in for one specific use of a wildcard, created by capture conversion (JLS §5.1.10) so the compiler has a concrete type to reason about for the length of one expression; it never exists outside that one compile-time check, and two textually identical wildcards still capture to two different, unrelated `CAP#n` variables.

> Capture conversion invents a fresh type variable for each use of a wildcard-typed expression so the compiler can reason about "some specific unknown type" instead of a wildcard; the invented variable — printed as `CAP#1`, `CAP#2`, … — lives only inside the compiler and leaves no trace in the class file.

## Supporting facts

### `glb` in the JLS text is ordinary intersection, spelled out for a reason

The `? extends Bi` clause of §5.1.10 computes the captured upper bound as `glb(Bi, Ui[A1:=S1,…,An:=Sn])`, and the JLS defines `glb(V1,…,Vm)` as literally `V1 & … & Vm` — an intersection type, the same notation a bounded type parameter like `<T extends LedgerEntry & Comparable<T>>` uses. In practice, for a type parameter with a single-interface or single-class bound like `List<E>`'s unbounded `E extends Object`, the intersection with `Object` reduces to just the wildcard's own bound, which is why the worked examples above only ever printed one bound. The general form matters once a type parameter itself carries multiple bounds — `01-basics.md` owns bounded type parameter syntax; this note only flags that the collapse to a single visible bound in the diagnostics above is a special case, not the general rule.

> `glb` in capture conversion is plain intersection; it only looks like "just the wildcard's bound" when the underlying type parameter's own declared bound is `Object`.

### `? super` capture's upper bound is not the lower-bound argument

A common misreading of `CAP#1 extends Object super: BonusEntry from capture of ? super BonusEntry` is that `BonusEntry` is somehow the upper bound — it is not; per the JLS's third bullet, the *upper* bound stays at the type parameter's own declared bound (here `Object`, `List<E>`'s own unbounded `E`), and `BonusEntry` is only the *lower* bound. That is why assigning a `CashEntry` into that slot fails even though `CashEntry` and `BonusEntry` are siblings under `LedgerEntry` — the compiler only knows the captured type is *at least as general as* `BonusEntry`, never that it is `BonusEntry` itself or narrower.

> `? super B` captures to a fresh variable bounded above by the type parameter's own bound and below by `B` — `B` is never the upper bound.

### Capture conversion is not applied recursively

The JLS states this as a standalone sentence: "Capture conversion is not applied recursively." A nested wildcard, such as the outer argument of `List<List<? extends LedgerEntry>>`, only has capture conversion applied to the outermost application that needs it — the inner `?` is not independently captured unless something separately forces it to be. This rarely surfaces in ordinary QuizStakes code, where wildcards are not usually nested, but it is worth knowing the sentence exists rather than assuming capture conversion walks a whole type tree.

> Capture conversion converts one parameterized type's wildcards in a single pass; it does not recurse into nested type arguments on its own.

## Pitfalls

### "A `static` field on a generic class is per-parameterisation, like an instance field feels"

**Wrong**

```java
class Repository<T extends LedgerEntry> {
    static long postedCount = 0;
    void post(T entry) { postedCount++; }
}
// Repository<CashEntry> cashRepo = new Repository<>();
// Repository<BonusEntry> bonusRepo = new Repository<>();
// three posts through cashRepo, one through bonusRepo
// expected: cashRepo-side count 3, bonusRepo-side count 1
// actual, JDK 21.0.7:
// cashRepo.postedCount = 4
// bonusRepo.postedCount = 4
```

**Right**

```java
class Repository<T extends LedgerEntry> {
    private static final Map<Class<?>, Long> postedCounts = new java.util.concurrent.ConcurrentHashMap<>();
    private final Class<T> entryType;

    Repository(Class<T> entryType) { this.entryType = entryType; }

    void post(T entry) {
        postedCounts.merge(entryType, 1L, Long::sum);
    }
}
// new Repository<>(CashEntry.class) and new Repository<>(BonusEntry.class)
// now key on the actual runtime type token, so each entry type gets its own count
```

**Why people believe it:** an *instance* field genuinely does get one copy per object, and `Repository<CashEntry>` versus `Repository<BonusEntry>` reads, at the source level, like two different kinds of object — it is easy to extend that same "one copy per kind" intuition to `static`, without noticing that `static` was never scoped to "kind" at all, only to the one loaded `Class`.

### "`javac`'s `CAP#1` error means my wildcard types don't match"

**Wrong**

```java
class FundsLedger {
    void reconcile(List<? extends LedgerEntry> source, List<? extends LedgerEntry> destination) {
        destination.addAll(source);
        // Capture1.java:10: error: incompatible types: List<CAP#1> cannot be converted
        // to Collection<? extends CAP#2>
        //   where CAP#1,CAP#2 are fresh type-variables:
        //     CAP#1 extends LedgerEntry from capture of ? extends LedgerEntry
        //     CAP#2 extends LedgerEntry from capture of ? extends LedgerEntry
    }
}
```

**Right**

```java
class FundsLedger {
    <T extends LedgerEntry> void reconcile(List<T> source, List<T> destination) {
        destination.addAll(source);
    }
}
```

Naming the type parameter `T` once and using it in both places tells the compiler the two lists share one element type, instead of letting each `?` capture independently — the fix is the wildcard-capture-helper idiom `02-in-anger.md` owns in full.

**Why people believe it:** both parameters are declared with the textually identical wildcard, `? extends LedgerEntry`, so it looks like they must be "the same type" already — nothing in the source hints that capture conversion treats every occurrence as its own fresh unknown, since that machinery is entirely internal to the compiler and only ever surfaces in the diagnostic's fine print.

### "Two overloaded methods that both take a `List<T>` should always be legal, the way overloading on any other parameter type is"

**Wrong**

```java
class FundsLedger {
    void post(List<CashEntry> entries) { }
    void post(List<BonusEntry> entries) { }
    // Clash1.java:11: error: name clash: post(List<BonusEntry>) and post(List<CashEntry>)
    // have the same erasure
}
```

**Right**

```java
class FundsLedger {
    void postCash(List<CashEntry> entries) { }
    void postBonus(List<BonusEntry> entries) { }
    // or, if a single call site genuinely needs to dispatch by element type at runtime,
    // a Class<T> token parameter distinguishes the erased descriptors instead of the name:
    <T extends LedgerEntry> void post(List<T> entries, Class<T> entryType) { }
}
```

**Why people believe it:** overloading on the *type argument* of a parameterised parameter looks, syntactically, exactly like overloading on any other type — `post(List<CashEntry>)` and `post(String)` are both "overloading on the parameter type" at a glance — but only one of those two survives erasure with a distinct descriptor, and nothing about the source syntax warns which case you are in until `javac` says so.

## Cheat sheet

| Leaf | One-line rule | Diagnostic / evidence |
|---|---|---|
| 3.5.11 overload clash | Two overloads erasing to the same descriptor cannot both occupy the `methods` table (JVMS §4.6) | `name clash: have the same erasure` (or `…, yet neither overrides the other` for the override case) |
| 3.5.11 legal contrast | Return-type-only differences are legal — the descriptor includes the return type | `03a-internals-bridge-methods.md` §2's `()LLedgerEntry;` vs `()LCashEntry;` pair |
| 3.5.12 static sharing | One `Class` object per generic declaration ⇒ one slot per `static` field, shared by every parameterisation | Printed count totals across parameterisations instead of splitting; one `Fieldref` in the constant pool |
| 3.5.12 distinct-from | `static T last;` (class's own type parameter) does not compile at all — a different, stricter rule | `02c-inference-and-generic-limits.md` 2.7.14 |
| 3.5.12 fix | `Map<Class<?>, V>` keyed on a type token, or an instance field, or a per-type non-generic holder class | See the fix table in §2 |
| 3.5.13 capture conversion | Each wildcard use gets a fresh, compiler-only type variable per JLS §5.1.10; two occurrences never provably agree | `CAP#1`, `CAP#2`, … plus the `from capture of ?` clause naming the source wildcard |
| 3.5.13 in bytecode | Capture conversion is fully discharged before code generation; no `CAP#n` in any descriptor or `Signature` | `javap -v` shows only `+`/`-`/`*` wildcard grammar (JVMS §4.7.9.1) in `Signature`, never a capture name |
| 3.5.13 fix | Name the unknown with a real type parameter instead of leaving it an anonymous wildcard | `02-in-anger.md`'s capture-helper idiom |

## Self-test

**Q1.** Two methods, `post(List<CashEntry>)` and `post(List<BonusEntry>)`, fail to compile together. Explain the failure starting from the class file, not from "generics are erased."

<details><summary>Answer</summary>

A class file's `methods` table holds one `method_info` per distinct (name, descriptor) pair — JVMS §4.6 requires that pair to be unique. Erasure replaces `List<CashEntry>` and `List<BonusEntry>` with the same raw `List`, so both source declarations produce the identical descriptor `(Ljava/util/List;)V`. `javac` refuses to compile because it cannot legally emit two entries sharing both fields — it is not a language-level squeamishness, it is that the target file format has no way to hold the result even if the compiler allowed it.

</details>

**Q2.** Why does `<T extends LedgerEntry> void post(T entry)` alongside `void post(LedgerEntry entry)` clash, when neither declaration contains a parameterised type like `List<T>`?

<details><summary>Answer</summary>

The clash rule is about erased descriptors, not about source syntax containing angle brackets. A type variable's descriptor is the erasure of its leftmost bound — here `T`'s bound is `LedgerEntry`, so `post(T)` erases to `post(LedgerEntry)`, the identical descriptor as the plain overload. Any two declarations whose parameter types erase to the same thing clash, whether or not either one visibly mentions a type parameter.

</details>

**Q3.** A subclass declares a method that erases onto an inherited method but is not a valid override. What does the diagnostic say, and why is the wording different from the plain overload clash?

<details><summary>Answer</summary>

`javac` reports "name clash: save(T) in CashEntryStore and save(CashEntry) in AbstractStore have the same erasure, yet neither overrides the other." It's worded differently because the compiler checked two things and both failed: the two methods are not distinguishable overloads (same erased descriptor), and the new declaration also fails to qualify as an override of the inherited one under the language's own override-matching rules, because its signature — a generic method with its own type parameter — does not match the inherited method's signature. It's neither a legal overload nor a legal override, so both failures get named.

</details>

**Q4.** `static long postedCount` on `Repository<T extends LedgerEntry>` is incremented three times through a `Repository<CashEntry>` and once through a `Repository<BonusEntry>`. What does each side print, and why?

<details><summary>Answer</summary>

Both print `4`. There is exactly one loaded `Repository` class regardless of how many parameterisations the source uses, so `postedCount` has exactly one storage slot — confirmed by `javap` showing a single `fields` table entry and a single constant-pool `Fieldref` that `getstatic`/`putstatic` both reference, with no way to encode "and this copy belongs to `CashEntry`" anywhere in the constant pool. All four increments land on the same slot, so both call sites read the shared total.

</details>

**Q5.** How does the static-sharing rule differ from the rule that makes `static T last;` fail to compile at all on the same generic class?

<details><summary>Answer</summary>

They're different failure shapes. `static long postedCount` compiles and runs — it's legal, just silently shared across every parameterisation, because a plain `long` needs no per-`T` identity. `static T last;` never compiles, because it names the *class's own* type parameter directly in a static context, and there is no instantiation active at the class level for `T` to resolve against — the language refuses the declaration outright rather than let a field exist whose declared type can never be concrete. One is permitted-and-surprising; the other is forbidden-and-loud.

</details>

**Q6.** What is `CAP#1` in a `javac` diagnostic, precisely — not "some generics thing," the actual mechanism?

<details><summary>Answer</summary>

It's a fresh type variable that capture conversion (JLS §5.1.10) invents to stand in for one specific use of a wildcard-typed expression, so the compiler has a concrete type to reason about instead of the wildcard itself. Its bounds come from the wildcard: `? extends B` gives it an upper bound derived from `B`; `? super B` gives it a lower bound of `B`. It's "fresh" per use, meaning two separate occurrences of even the identical wildcard capture to two different, unrelated `CAP#n` variables that the compiler can never assume are equal.

</details>

**Q7.** Given `reconcile(List<? extends LedgerEntry> source, List<? extends LedgerEntry> destination)` failing to compile `destination.addAll(source)`, explain exactly what the `CAP#1`/`CAP#2` diagnostic is telling you, reading its `from capture of` clauses.

<details><summary>Answer</summary>

The diagnostic prints `CAP#1 extends LedgerEntry from capture of ? extends LedgerEntry` and the same for `CAP#2` — the `from capture of` clause tells you exactly which source-level wildcard occurrence produced that variable: `CAP#1` came from `source`'s wildcard, `CAP#2` from `destination`'s. Even though both wildcards are written identically, capture conversion gives them independent fresh variables, so the compiler has no basis for assuming `destination`'s element type is the same as, or a supertype of, `source`'s — hence `addAll` can't type-check.

</details>

**Q8.** Does a captured type variable like `CAP#1` ever appear in a compiled `.class` file? What replaces it?

<details><summary>Answer</summary>

No. Capture conversion is entirely a compile-time type-checking device — the JLS states it "never requires a special action at run time." A method whose body relied on capture, once compiled, has its parameter erased to the raw type in its descriptor, and the only remaining trace of the wildcard is in the `Signature` attribute, written using the `+`/`-`/`*` wildcard grammar from JVMS §4.7.9.1 (`+LLedgerEntry;` for `? extends LedgerEntry`, `-LCashEntry;` for `? super CashEntry`). No `CAP#n` name appears in either the descriptor or the `Signature` string.

</details>

**Q9.** In `List<? super BonusEntry>`, is `BonusEntry` the captured variable's upper bound or its lower bound? What confuses people about this?

<details><summary>Answer</summary>

Lower bound. Per JLS §5.1.10's third bullet, a `? super B` wildcard captures to a fresh variable whose *upper* bound stays at the type parameter's own declared bound (`Object`, for `List<E>`'s unbounded `E`) and whose *lower* bound is `B`. People read `super BonusEntry` and expect `BonusEntry` to constrain the type from above, the way `extends` does, but `super` constrains it from below — the confusion is exactly why assigning a sibling type like `CashEntry` into that slot still fails, even though `CashEntry` and `BonusEntry` share a common supertype.

</details>

**Q10.** Two overloads differ only in return type — `LedgerEntry create()` versus a subclass's `CashEntry create()`. Why is this legal in the class file when it would be illegal to write as two overloads with the same parameter list in one class?

<details><summary>Answer</summary>

A method's descriptor includes its return type, so `()LLedgerEntry;` and `()LCashEntry;` are two genuinely different descriptors, and the `methods` table has no trouble holding both — that's exactly the mechanism `03a-internals-bridge-methods.md` uses for covariant-return bridges, where the compiled class holds both the narrower real override and a wider synthetic bridge. Java source syntax simply never gives you a way to write two overloads that differ *only* in return type in the same class — the compiler treats that as a duplicate declaration — but the class file underneath was never the thing enforcing that restriction; source-level rules are.

</details>

## Open questions

None.

---

**Leaves covered:** 3.5.11, 3.5.12, 3.5.13 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 543
