# 03 Java Core — Why erasure, what reification would have cost, and super type tokens — INTERNALS (§3.5, 3.5.14–3.5.16)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The limits of erasure, and capture conversion](03d-internals-erasure-limits-and-capture.md) · Next: [Arrays: the basics](../arrays/01-basics.md)

This file closes the generics chapter with the question every other file in it has been dodging: was erasure the right call, what would the alternative have actually bought and cost, and did the platform leave any door open for getting some of it back. `3.5.14` proves the migration constraint that forced erasure rather than asserting it, and researches what C#/.NET and Project Valhalla do instead. `3.5.15` prices reification honestly, both columns, cross-linking every limitation this chapter already showed you as the "bought" side. `3.5.16` goes under `02a-type-tokens-and-generic-reflection.md`'s already-proven super-type-token mechanism to the class-file grammar itself and ships a build with the two things a tutorial always skips: the raw-construction guard and a cache-ready `equals`/`hashCode`. It hands off erasure's own consequences and reifiability to `01a-erasure-and-its-consequences.md`, migration compatibility's bill-of-costs table to `02d-migration-and-reading-signatures.md`, the `Signature` attribute's method-and-class-level decoding to `03-internals-erasure.md`, and the `+`/`-`/`*` wildcard indicators' meaning in a real capture site to `03d-internals-erasure-limits-and-capture.md` — this file only needs their grammar slot, not their story.

## 1. Why Java chose erasure: the migration constraint, proved (3.5.14)

`[PROVE]` The picture to hold in your head: in 2004, Java 5 was not a green-field language design choosing between two type-system strategies on their merits. It was a fifteen-year-old, already-deployed platform being asked to add a feature to a runtime with a decade of shipped class files sitting in application servers, and the non-negotiable requirement was that a class file compiled against JDK 1.4 and one compiled against JDK 5 had to link together, **in both directions**, inside the same running JVM, without recompilation. That single sentence is the entire reason for erasure, and it is provable rather than assertable: compile the same call two ways and watch the bytecode come out identical, then compile the two eras against each other and watch both directions run.

### Why it exists

Before generics, `java.util.List` held `Object`. Every application, every third-party JAR, every servlet container already on a customer's disk in 2004 called `List.add(Object)` and read back with a cast. Sun's constraint (stated explicitly in the generics design documents and restated by Neal Gafter and Josh Bloch in numerous talks on the JSR-14 process) was that Java 5 had to let a *new* class, compiled with `List<CashEntry>`, call into an *old* class, compiled and shipped years earlier against raw `List` — and the reverse: an old, unrecompiled class had to keep working when handed a `List` instance created by new, generic-aware code. A checked-generics runtime (one where `List<CashEntry>` and `List<BonusEntry>` are actually different runtime shapes) cannot satisfy that, because the old class's compiled bytecode has no idea any type argument exists — it was compiled before generics were invented. Erasure satisfies it by construction: `List<CashEntry>` and raw `List` compile to the **same** class, `java.util.List`, with the **same** method descriptors, so there is nothing for the old code to be incompatible with.

### The mechanism — prove the descriptor identity, then prove the bidirectional link

Compile one method against a raw `List` and a sibling against `List<CashEntry>`, doing the identical `add`, and read the constant pool each emits.

```java
import java.util.List;

public class DescriptorRaw {
    static boolean call(List list, CashEntry e) {
        return list.add(e);
    }
}
```

```java
import java.util.List;

public class DescriptorGeneric {
    static boolean call(List<CashEntry> list, CashEntry e) {
        return list.add(e);
    }
}
```

Compiled and disassembled on JDK 21.0.7 (`javap -c -p`), both methods' `invokeinterface` instruction reads:

```
2: invokeinterface #7,  2            // InterfaceMethod java/util/List.add:(Ljava/lang/Object;)Z
```

Byte for byte identical descriptor, `(Ljava/lang/Object;)Z`, in both class files — the parameterised caller's `CashEntry` never appears anywhere in the emitted instruction. That is erasure's whole load-bearing claim made concrete: `javac` replaces `E` (`List<E>`'s type variable, unbounded) with its erasure, `Object`, before it ever writes a descriptor, so there is no version of `List.add` for `javac` to have written differently between the two callers. Nothing downstream — the JVM's verifier, its method-resolution table, another class's `invokeinterface` against the same interface — can tell these two call sites apart, because at the level every one of those mechanisms actually operates on, they are not two things.

Now the bidirectional link itself, using a class shaped like real 1.4-era code (raw types throughout, no generics) called by a modern generic caller, and the reverse: a generic class called by a caller written with zero type arguments at all — exactly the shape a decade-old JAR still on a classpath would have.

```java
import java.util.ArrayList;
import java.util.List;

// Shaped like pre-generics (1.4-era) source: raw List in and out, nothing
// here would need to change to compile against JDK 1.4.
public class LegacyLedgerOps {
    public static List combine(List a, List b) {
        List out = new ArrayList();
        out.addAll(a);
        out.addAll(b);
        return out;
    }
}
```

```java
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class ModernCaller {
    public static void main(String[] args) {
        List<CashEntry> a = new ArrayList<>();
        a.add(new CashEntry(UUID.randomUUID(), 420));
        List<CashEntry> b = new ArrayList<>();
        b.add(new CashEntry(UUID.randomUUID(), 100));
        List combined = LegacyLedgerOps.combine(a, b);
        System.out.println("modern caller -> legacy callee, combined size=" + combined.size());
    }
}
```

Run on JDK 21.0.7, `ModernCaller` prints `modern caller -> legacy callee, combined size=2`: a generic-aware caller feeding a genuinely raw, 1.4-shaped method with no code anywhere needing to change. Now the reverse direction — a generic class, and a caller compiled with no type arguments whatsoever, exactly as an old JAR compiled before `GenericLedgerOps` existed would look if it were handed the new class on its classpath:

```java
import java.util.ArrayList;
import java.util.List;

public class GenericLedgerOps<T> {
    public List<T> wrap(T item) {
        List<T> list = new ArrayList<>();
        list.add(item);
        return list;
    }
}
```

```java
import java.util.List;
import java.util.UUID;

// Shaped like a pre-generics (1.4-era) caller: no type arguments at all.
public class RawCaller {
    public static void main(String[] args) {
        GenericLedgerOps ops = new GenericLedgerOps();
        List list = ops.wrap(new CashEntry(UUID.randomUUID(), 333));
        System.out.println("raw caller -> generic callee, wrap size=" + list.size());
    }
}
```

Run on JDK 21.0.7, `RawCaller` prints `raw caller -> generic callee, wrap size=1`. Both directions link, both run, and `javac -Xlint:all` on the raw-shaped files reports exactly the diagnostics you would expect (`rawtypes`, `unchecked`) and nothing that blocks compilation or linkage. `[PROVE]` discharged: the constraint was not asserted, it was demonstrated running on JDK 21.0.7 in both directions, with the descriptor identity above showing *why* it holds — there is only ever one shape of `List.add` for the linker to reconcile.

`02d-migration-and-reading-signatures.md` owns the full bill-of-costs table for what this constraint bought and cost in migration terms specifically (`Vector` versus `ArrayList`, the `Collections` utility methods that had to stay raw-friendly, among others) — this section is the mechanism proof underneath that table, not a second version of it.

No diagram: the manifest assigns this section none; the two `javap` excerpts above are the picture.

**Gotcha:** it is tempting to read the descriptor-identity proof and conclude erasure was "the compiler being lazy" — the far stronger reading is the opposite: type-*checking* generics is not erased at all (a `List<CashEntry> list; list.add(bonusEntry);` fails at `javac`, not at runtime), only the runtime *representation* is. Erasure is a deliberate split between compile-time soundness and runtime shape, made specifically so the runtime shape could stay unchanged.

### What C#/.NET does instead, and why it could afford to `[RESEARCH]`

The CLR takes the opposite design: **.NET generics are reified, not erased.** Confirmed against Microsoft's own generics documentation and corroborating primary-source engineering writeups (Don Syme's original CLR generics design notes, reproduced in Matt Warren's "How generics were added to .NET"): the CLR carries the type argument in metadata all the way to the JIT, and the JIT compiler generates a **separate, specialised native code body per value-type instantiation** — `List<int>` and `List<CashEntry>` (a struct, hypothetically) each get their own compiled machine code, with `int` stored unboxed inline — while **reference-type instantiations share a single compiled body**, because every reference is the same machine word regardless of what it points to, so `List<string>` and `List<CashEntryRef>` (a class) run the identical generated code with the type argument carried only in metadata for reflection and casts. That reference-type sharing is, in effect, erasure at the code-generation level even inside a reified runtime — the CLR is not "no erasure anywhere," it is "erasure exactly where sharing is safe, specialisation exactly where a boxing cost would otherwise be paid."

The decisive difference from Java's situation is not implementation cleverness, it is the *constraint* Microsoft was willing to accept and Sun was not: .NET generics shipped in .NET Framework 2.0 (2005) as a **CLR version change** — code targeting the reified generic CLR needed the new runtime, full stop. Microsoft accepted a runtime break; Sun's promise to the installed base of JDK 1.0–1.4 deployments explicitly ruled one out. **Unverified:** the exact scope of what broke or needed recompilation across the 1.1-to-2.0 CLR transition beyond "targets the new runtime" was not confirmed against a primary Microsoft migration document in this pass; what would settle it is Microsoft's own .NET Framework 1.1-to-2.0 breaking-changes documentation.

### Project Valhalla: what is actually shipping, stated precisely `[RESEARCH]`

Two claims need to be kept sharply apart, because the internet routinely blurs them. First: **nothing about existing generics changes.** Every erasure mechanism this chapter has proven — the descriptor identity above, bridge methods (`03a-internals-bridge-methods.md`), the erased overload clash (`03d-internals-erasure-limits-and-capture.md`) — is exactly as true on JDK 21 as it was on JDK 5, and Valhalla does not touch any of it for reference types. Second: what Valhalla *does* propose, verified against the project's own page and the JEP that has actually reached integration as of this writing (August 2026) rather than assumed from older commentary — **JEP 401, "Value Objects (Preview)"**, introduces **value classes**: identity-free, immutable class instances whose instances a JVM may *scalarize* into their constituent fields or *flatten* into a compact inline representation, changing what `==` means for those instances. JEP 401 has been integrated for JDK 28 (targeted for a March 2027 release; early-access builds are available now under `jdk.java.net/28`); JDK 27 (targeted September 2026) ships without it.

Specialised — sometimes called "universal" — generics, the feature that would let a `List<int>` or a `List<Money>`-as-value-class avoid boxing entirely by giving each value-type instantiation its own flattened representation, is **explicitly separate, later work**, not part of JEP 401 and not landing in JDK 28: without it, a `List<SomeValueClass>` still materialises each element as a heap object, because the collection's storage is still `Object[]`, and flattening a value class into an array slot requires the generic container itself to know the component's layout — exactly the specialisation problem Valhalla has stated it has not yet finished solving. Be precise about the shape of that future work rather than filling in a mechanism: what is public is that reference-type generics remain erased under any currently described design, and that specialisation is scoped to value-type instantiations, for the identical reason C#'s specialisation above is scoped that way — reference-type instantiations can share one body; value-type ones cannot without either boxing or a per-instantiation body. **Unverified:** the exact mechanism by which specialised generics will interoperate with already-erased reference-type generics in the same class file (a "universal generics" scheme was drafted and then reworked, per Valhalla's own project history) was not confirmed to a specific, currently-targeted design in this pass; what would settle it is a JEP number for that specific feature once one is formally targeted, which as of this writing does not yet exist.

### The verdict, worked rather than stated

Put the two proofs together. Erasure bought exactly the property proved in the mechanism section above: total, unconditional binary compatibility between every class file ever compiled for the platform, generic-aware or not, in both directions, with no recompilation and no runtime version bump. It cost every limitation the rest of this chapter has catalogued: no `new T[n]` (`03b-internals-reifiable-types-and-generic-arrays.md`), the overload clash and the capture-conversion workaround (`03d-internals-erasure-limits-and-capture.md`), heap pollution through varargs (`03c-internals-heap-pollution-and-safevarargs.md`), and the whole apparatus §3 of this file builds just to get one piece of that information back. No amount of better language design in 2004 would have made a different trade available — C#'s reification was affordable specifically because Microsoft was willing to break the runtime, and that option was not on Sun's table. **Interview:** "why are Java generics erased" gets asked constantly and answered with "for backward compatibility," which is true but too vague to demonstrate you understand it — the 90-second answer names the actual mechanism: `javac` had to guarantee that a class file compiled against `List<CashEntry>` and one compiled years earlier against raw `List` produce identical bytecode for the same operation, in both link directions, with no JVM version requirement, and erasure is the design that makes that guarantee trivially true rather than something to negotiate case by case.

> Erasure exists because Java 5 had to make new, generic-aware bytecode and old, pre-generics bytecode identical wherever they overlapped, in both link directions, without a runtime version bump — a constraint C#/.NET's reified generics did not have to satisfy, because Microsoft accepted a CLR version break that Sun's compatibility promise ruled out.

## 2. What reification would have bought and cost, priced honestly (3.5.15)

The mental model for this section: reification is not a single feature, it is a bundle of consequences that all follow from one change — giving every distinct `List<X>` its own runtime identity instead of collapsing them all into one `List`. Price both columns properly rather than gesturing at either.

### Why it exists (as a thought experiment)

Every limitation this chapter has spent five files proving traces back to the same root: the runtime has exactly one `List` shape, and generic instantiations are a compile-time fiction layered on top of it. Asking "what if it were not" is the only way to see which costs are erasure's fault specifically, versus which costs (invariance, chiefly) people blame on erasure but would survive unchanged.

### The mechanism — the bought column, cross-linked to where you already met the limitation

| What reification buys | What it removes, and where this chapter proved you needed it |
|---|---|
| `new T[n]` becomes legal and honest | The illegality of `new T[n]` and the `(T[]) new Object[n]` / `Array.newInstance` workarounds — `03b-internals-reifiable-types-and-generic-arrays.md` |
| `instanceof List<CashEntry>` becomes decidable | The `instanceof` restriction to reifiable types, and having to test the raw type or a wildcard instead — `02c-inference-and-generic-limits.md` |
| `List<CashEntry>.class` exists | Type tokens and super type tokens becoming unnecessary — `02a-type-tokens-and-generic-reflection.md`, and §3 of this file |
| The erased overload clash disappears | `void save(List<CashEntry>)` and `void save(List<BonusEntry>)` no longer collide at one descriptor — `03d-internals-erasure-limits-and-capture.md` |
| Static fields could be per-instantiation | `AbstractStore<E>`'s statics no longer forced to be shared across every `E` — `03d-internals-erasure-limits-and-capture.md` |
| No bridge method needed for the erasure-mismatch case | The synthetic bridge and its own extra `checkcast` disappear along with the mismatch it exists to paper over — `03a-internals-bridge-methods.md` |
| Heap pollution through generic varargs becomes impossible | The exact `Object[]` aliasing sequence `@SafeVarargs` exists to promise around — `03c-internals-heap-pollution-and-safevarargs.md` |

### The cost column, worked rather than invented `[PROVE]`

The single cost everyone reaches for is "code bloat," almost always stated as a number nobody has actually derived. Work it through instead of quoting one. A reference variable — any `T` bound only by `extends Object`, which is every collection element type in ordinary code — is one machine word (a pointer) regardless of what `T` is. `List<CashEntry>`'s internal storage, `Object[] elementData`, does not change size, layout, or access pattern whether `T` is `CashEntry`, `BonusEntry`, or `String`: every read is "load a pointer at this array offset," every write is "store a pointer at this array offset." A JIT-generated method body for `List<CashEntry>.get(int)` and one for `List<BonusEntry>.get(int)` would, under reification, be identical machine code apart from the label on the returned type — which is exactly why the CLR's own JIT (§1) shares one compiled body across every reference-type instantiation rather than generating one per instantiation. **The bloat cost of reification is real only where the element is a value type stored inline rather than by reference** — a `List<int>` where each element is genuinely a different number of bits than a `List<long>`'s, or (in Valhalla's future terms) a `List` of a flattened value class whose fields differ in layout from another value class's. That is precisely the boundary Valhalla's specialised generics are scoped to (§1): specialise only where the representation actually differs, share everywhere it does not. Reification for Java's actual, everyday case — collections of reference types, `String`, `CashEntry`, `BonusEntry`, `Money` — would have cost close to nothing in code size, because the JIT could have made the identical sharing decision the CLR makes.

The costs that are real regardless of the reference/value split: metadata size (every distinct instantiation needs a runtime record naming its type argument, even a shared one), class-loading time (verifying and linking that additional metadata at every generic type's first use), and the compatibility break §1 already proved was the actual blocker in 2004 — a reified JVM cannot honor the descriptor-identity proof from §1, because `List<CashEntry>.add` and `List<BonusEntry>.add` would need to *not* be the same method for reification to mean anything, which is the whole property old, pre-generics bytecode depends on staying true.

### What reification would not have fixed: variance

One paragraph, because this is the correction that matters most here. Generic invariance — `List<CashEntry>` is not a `List<LedgerEntry>` even though `CashEntry` is a `LedgerEntry` — is not a symptom of erasure at all; it is a **soundness property of the type system**, independent of runtime representation. `01b-variance-and-wildcards.md` proves this the direct way: if `List<CashEntry>` were assignable to `List<LedgerEntry>`, a caller holding the `List<LedgerEntry>` reference could legally call `add` with a freshly constructed `BonusEntry`, and the underlying storage — reified or erased, does not matter which — would now hold a `BonusEntry` where every other holder of a `List<CashEntry>` reference expects only `CashEntry`. A fully reified `List<CashEntry>` would still not be a `List<LedgerEntry>`, for exactly that reason; wildcards and PECS would still be necessary to get controlled variance where it is actually sound. Readers routinely blame erasure for invariance because both showed up in the same JDK 5 release; they are unrelated design decisions, and reification would have left this one completely untouched.

No diagram: the manifest assigns this section none; the table above is the picture.

**Gotcha:** the "bloat" objection is almost always raised against Java's actual workload — reference-typed collections — where the arithmetic above shows it barely applies; it is a real cost specifically for the value-type case Valhalla is now built to isolate, which is evidence the cost was correctly scoped rather than correctly avoided.

> Reification would have bought decidable `instanceof`, legal `new T[n]`, real per-instantiation `Class` objects, and the removal of the overload clash and bridge-method workaround — at a cost that is genuinely small for reference-typed generics (a shareable, single compiled body, exactly as the CLR already does) and genuinely large only for value-typed generics, which is precisely the boundary Project Valhalla's specialised generics are scoped to; it would not have touched generic invariance, which is a soundness property with nothing to do with erasure.

## 3. Super type tokens at the class-file grammar level, and the build `[SOURCE]` `[PROVE]` `[BUILD]`

`02a-type-tokens-and-generic-reflection.md` §2 already proved the mechanism this section goes under: an anonymous subclass's `extends` clause is a *declaration*, `javac` writes a `Signature` attribute for every generic declaration regardless of whether the declaring class's own body uses the argument, and `getGenericSuperclass()` reads that attribute back as a live `ParameterizedType`. Take that proof as read — do not re-derive it here. This section owes you three things that file stopped short of: the actual JVMS grammar the `Signature` string is written in, character by character; a build that survives the two failure modes every tutorial version of this pattern skips; and the walk through a genuinely nested type, because "recover `List<Money>`" and "recover `Map<ClientId, List<Money>>`" are not the same amount of reflection work.

### The mechanism — the exact grammar, quoted and decoded `[SOURCE]`

The asymmetry restated as the one sentence that explains everything below it: a type argument written in a `new` expression is erased and permanently gone; the same argument written in an `extends` clause is recorded in a `Signature` attribute and stays, because reflection's contract with the class-file format guarantees that declarations — never expressions — keep their generic shape.

Quoting JVMS 21 §4.7.9.1, "Signatures," the grammar productions that govern exactly this case, verbatim:

```
ClassSignature:
    [TypeParameters] SuperclassSignature {SuperinterfaceSignature}

SuperclassSignature:
    ClassTypeSignature

ClassTypeSignature:
    L [PackageSpecifier] SimpleClassTypeSignature {ClassTypeSignatureSuffix} ;

SimpleClassTypeSignature:
    Identifier [TypeArguments]

TypeArguments:
    < TypeArgument {TypeArgument} >

TypeArgument:
    [WildcardIndicator] ReferenceTypeSignature | *

WildcardIndicator:
    + | -
```

Read each line against what it is for, because the grammar is not decorative — it is the reason the recovery code below works at all. `ClassSignature` is the production a class-level `Signature` attribute holds when the class has a parameterised superclass — exactly the anonymous subclass's case, since its `SuperclassSignature` is where `VerdictTypeRef<List<Money>>` gets written. `ClassTypeSignature` is the leading-`L`, binary-name, trailing-`;` shape every object type takes in any class-file signature or descriptor, and it is recursive: `SimpleClassTypeSignature`'s optional `TypeArguments` block can itself contain another full `ReferenceTypeSignature`, which can itself be a `ClassTypeSignature`, which is exactly how `Ljava/util/List<LMoney;>;` nests one such object-type form inside another's angle brackets. `WildcardIndicator`'s `+`/`-` (covariant/contravariant, the `? extends`/`? super` spelling at the signature level) can appear only inside a `TypeArgument`, never at the top level of a `SuperclassSignature` — `03d-internals-erasure-limits-and-capture.md` owns what those indicators mean at a capture site; here they are simply the two characters that would have appeared inside this section's angle brackets had the example used a wildcard instead of a concrete `Money`.

Compile the anonymous subclass this grammar describes and read the actual attribute. Freeze this listing before capturing its output — the constant-pool index in the `Signature: #12` line below is bound to this exact class file and renumbers the moment anything above it changes.

```java
abstract class VerdictTypeRef<T> {
    private final Type type;

    protected VerdictTypeRef() {
        Type superclass = getClass().getGenericSuperclass();
        if (superclass instanceof ParameterizedType parameterized) {
            this.type = parameterized.getActualTypeArguments()[0];
        } else {
            throw new IllegalStateException(
                "VerdictTypeRef constructed without a type argument - " +
                "use new VerdictTypeRef<List<Money>>() {}, not new VerdictTypeRef() {}");
        }
    }

    Type type() {
        return type;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof VerdictTypeRef<?> other && this.type.equals(other.type);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(type);
    }
}
```

Compiled and disassembled on JDK 21.0.7 (`javap -p -v` on the anonymous subclass created by `new VerdictTypeRef<List<Money>>() {}`):

```
class VerdictTypeRefDemo2$1 extends VerdictTypeRef<java.util.List<Money>>
  minor version: 0
  major version: 65
  flags: (0x0020) ACC_SUPER
  this_class: #7                          // VerdictTypeRefDemo2$1
  super_class: #2                         // VerdictTypeRef
Signature: #12                          // LVerdictTypeRef<Ljava/util/List<LMoney;>;>;
```

`super_class: #2` is the plain, erased `VerdictTypeRef` constant-pool entry — the only supertype link the verifier and the JVM's own dispatch machinery ever consult, and it carries zero information about `List<Money>`. Walk the `Signature` string against the grammar just quoted, left to right: `LVerdictTypeRef` opens a `ClassTypeSignature` (`SuperclassSignature` in this context) for the supertype itself. The angle-bracket block immediately following it is that `ClassTypeSignature`'s `SimpleClassTypeSignature`'s `TypeArguments` block — one `TypeArgument`, no `WildcardIndicator`, whose `ReferenceTypeSignature` is itself a full nested `ClassTypeSignature`: `Ljava/util/List`, opening its own angle-bracket block around its own single `TypeArgument`, `LMoney;`. Each `;` closes the `ClassTypeSignature` it belongs to — there are three in the string, one per nesting level (`VerdictTypeRef`, `List`, `Money`), and the final `;` closes the outermost one, matching the grammar's requirement that every `ClassTypeSignature` production ends in exactly one `;`. `Money` is spelled out as a full identifier inside this string for the same reason the whole attribute exists: the `Signature` attribute is a UTF-8 constant-pool string, not executable bytecode, so nothing about erasure — which only deletes information from *instructions* the JVM interprets — has any purchase on it.

### The build `[BUILD]`

Run to completion, printing both the happy path and the two failure/utility modes a real implementation has to handle:

```java
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.List;
import java.util.Map;

public class VerdictTypeRefDemo2 {
    public static void main(String[] args) {
        VerdictTypeRef<List<Money>> ref = new VerdictTypeRef<List<Money>>() {};
        System.out.println("recovered: " + ref.type());

        VerdictTypeRef<List<Money>> ref2 = new VerdictTypeRef<List<Money>>() {};
        System.out.println("ref.equals(ref2): " + ref.equals(ref2));
        System.out.println("ref.hashCode()==ref2.hashCode(): " + (ref.hashCode() == ref2.hashCode()));

        try {
            VerdictTypeRef<?> raw = new VerdictTypeRef() {};
            System.out.println("unreachable: " + raw.type());
        } catch (IllegalStateException e) {
            System.out.println("raw construction rejected: " + e.getMessage());
        }

        VerdictTypeRef<Map<ClientId, List<Money>>> nested =
            new VerdictTypeRef<Map<ClientId, List<Money>>>() {};
        Type t = nested.type();
        System.out.println("nested top-level: " + t);
        if (t instanceof ParameterizedType pt) {
            System.out.println("  raw type: " + pt.getRawType());
            Type keyType = pt.getActualTypeArguments()[0];
            Type valueType = pt.getActualTypeArguments()[1];
            System.out.println("  key type: " + keyType);
            System.out.println("  value type: " + valueType);
            if (valueType instanceof ParameterizedType valuePt) {
                System.out.println("    value raw type: " + valuePt.getRawType());
                System.out.println("    value type argument: " + valuePt.getActualTypeArguments()[0]);
            }
        }
    }
}
```

Run on JDK 21.0.7:

```
recovered: java.util.List<Money>
ref.equals(ref2): true
ref.hashCode()==ref2.hashCode(): true
raw construction rejected: VerdictTypeRef constructed without a type argument - use new VerdictTypeRef<List<Money>>() {}, not new VerdictTypeRef() {}
nested top-level: java.util.Map<ClientId, java.util.List<Money>>
  raw type: interface java.util.Map
  key type: class ClientId
  value type: java.util.List<Money>
    value raw type: interface java.util.List
    value type argument: class Money
```

Three things that output proves, none of them the "happy path" a tutorial usually stops at. First, `equals`/`hashCode` on the recovered `Type`: two independently constructed tokens for the identical parameterisation compare equal and hash equal, because `ParameterizedType` implementations (the JDK's own `sun.reflect.generics.reflectiveObjects.ParameterizedTypeImpl`, confirmed by inspecting the runtime type of `ref.type()`) implement structural equality over their raw type and actual type arguments — which is exactly what lets a `VerdictTypeRef` key a `Map<VerdictTypeRef<?>, JavaType>` cache the way Jackson's `TypeReference` and Guice's `TypeLiteral` both do internally, rather than every deserialisation re-walking the reflection API from scratch. Second, the raw-construction guard: `new VerdictTypeRef() {}` compiles (with an unchecked/rawtypes warning) but throws the constructor's own `IllegalStateException` immediately, because that anonymous subclass's `extends VerdictTypeRef` has no `TypeArguments` block at all — confirmed directly by disassembling it, which carries **no `Signature` attribute whatsoever**, only the plain `super_class: #2` pointer, so there is nothing for `getGenericSuperclass()` to return but the bare `Class` object for `VerdictTypeRef`, and the `instanceof ParameterizedType` check correctly fails. Third, the nested walk: `Map<ClientId, List<Money>>` recovers as one `ParameterizedType` whose two `getActualTypeArguments()` slots are `ClientId` (a plain `Class`, no further nesting) and `List<Money>` (itself a `ParameterizedType`), and getting at `Money` requires walking one level deeper — exactly the shape a real deserialiser has to handle for any collection-of-collection or map-of-list field, and exactly why `JavaType` graphs in Jackson are recursive structures rather than a flat list.

No diagram: the manifest assigns this section none; the `javap` excerpt and the printed run above are the picture.

### The honest limits, stated as limits

Three, and none of them softens with a workaround. First, the trick recovers only what a **declaration** recorded — it cannot recover a type argument that only ever existed in a local variable or a bare `new` expression, for the identical reason §2.7.7 of `02a-type-tokens-and-generic-reflection.md` proved a local `List<Money>` variable is invisible to reflection: a `Signature` attribute exists only where `javac` was required to write one, and a `new` expression's type argument was never such a place. Second, the cost is real and per-token: every distinct parameterisation you need a token for is one more class, loaded once and retained for the process lifetime, not free the way a `Class<T>` field reference is. Third, and the one that trips people who have only ever used the pattern through a library: the recovered `Type` is a `ParameterizedType` **graph**, not a `Class` — you cannot `instanceof` a value against it, and you cannot hand it to any API whose parameter type is `Class<?>`. You have to walk it, exactly as the nested-map example above did, to get down to something a `Class`-based API (an `ObjectMapper`, a bean validator) can actually use.

**Interview:** "generics are erased, so how does Jackson deserialise a `List<Money>`?" — the strong version of the 90-second answer names the mechanism, not the magic: `new TypeReference<List<Money>>() {}`'s braces create an anonymous subclass whose `extends` clause `javac` cannot erase, because an `extends` clause is a declaration, and every generic declaration gets a `Signature` attribute per JVMS §4.7.9.1's `ClassSignature` production; the constructor calls `getGenericSuperclass()`, parses that attribute's string back into a `ParameterizedType`, and Jackson walks that graph — recursively, for a nested type — into its own `JavaType` model before deserialising a single byte. Saying "reflection magic" instead of naming the `Signature` attribute is the tell that the mechanism was never actually understood.

Tie the chapter's last three leaves together in one sentence: erasure was a compatibility decision proved necessary by the descriptor-identity argument in §1, its costs are the enumerable, cross-linkable list in §2, and the platform left exactly one door open on the way out — declarations keep their generic shape even when the code inside them never uses it — which is the door every serialisation and dependency-injection framework in the Java ecosystem walks through instead of asking for reification it was never going to get.

> A super type token defeats erasure by moving a type argument from a `new` expression — erased, per §1's descriptor-identity proof — into an anonymous subclass's `extends` clause, whose `ClassSignature` production (JVMS §4.7.9.1) `javac` must emit in full; `getGenericSuperclass()` parses that string back into a `ParameterizedType` graph that must be walked, not cast, to reach a nested argument.

## Supporting facts

### `Class<T>` per-instantiation objects are not the same idea as JIT specialisation

§1's C#/.NET discussion and §1's mechanism section both use the word "specialised," but for two different things: the CLR's JIT specialises *machine code bodies* per value-type instantiation, purely a code-generation decision invisible to the running program's object model. A hypothetical reified Java `Class<List<CashEntry>>` object (§2's "bought" column) would specialise *metadata* — one loaded `Class` object per instantiation, used by reflection and `instanceof` — which is a completely different axis and would exist even for reference types the JIT never bothers to compile separately.

> "Specialised" means a different thing depending on whether you are talking about generated machine code (a JIT decision) or a loaded `Class` object (a metadata decision) — conflating the two is how "reification would give every `List<X>` its own `Class` object" turns into the wrong claim "reification would bloat every method body."

### `javap`'s `Signature` output on a raw-constructed anonymous subclass has no attribute at all, not an empty one

`new VerdictTypeRef() {}` (§3's raw-construction guard) does not produce a `Signature` attribute containing an empty `TypeArguments` block — it produces **no `Signature` attribute on that class at all**, confirmed by disassembling it directly. `javac` only ever emits the attribute when the declaration in source actually used a type variable or parameterised type; a raw usage supplies neither, so there is nothing to record, not a placeholder for "nothing."

> Absence of a `Signature` attribute and presence of one with no arguments are not the same outcome — a raw declaration produces the former, and only the former, which is exactly why the `instanceof ParameterizedType` check in §3's build has to handle "returned a plain `Class`" as a real branch rather than an edge case.

## Pitfalls

### "Erasure was a shortcut Sun took to save implementation effort"

**Wrong**

```java
// "They just didn't want to rewrite the JVM's type system for generics."
// No code demonstrates a belief this vague - the wrongness is in treating
// the constraint as optional, which the descriptor-identity proof in §1
// shows it was not.
```

There is no code that "shows" this belief being acted on, because the belief itself never gets tested against anything — that is exactly the problem with it. It survives only because nobody ran the experiment §1 ran.

**Right**

```java
import java.util.List;

public class DescriptorRaw {
    static boolean call(List list, CashEntry e) {
        return list.add(e);
    }
}
```

Compiled and disassembled on JDK 21.0.7, this raw-typed method's `invokeinterface` descriptor for `List.add` reads `(Ljava/lang/Object;)Z` — identical to the descriptor a `List<CashEntry>`-typed sibling method emits. That identity is not a side effect of a shortcut; it is the specific property that makes 1.4-era bytecode and JDK-5-and-later generic bytecode link together in both directions, which §1 proves was the hard requirement, not a nice-to-have.

**Why people believe it:** "erasure" sounds like the compiler discarding information it could have kept, and discarding information sounds like laziness — but the information erasure discards (the type argument, at the instruction level) is exactly the information that would have made old and new bytecode incompatible if it had been kept, so the discarding was the requirement, not a corner cut to meet one.

### "Reification would have made every generic collection method bigger, across the board"

**Wrong**

```java
// Treating "reification means per-instantiation code" as universal, without
// asking whether List<CashEntry> and List<BonusEntry> need different bodies
// at all - they do not, because both store a plain reference.
List<CashEntry> cashList = new ArrayList<>();
List<BonusEntry> bonusList = new ArrayList<>();
// Under this belief: two separately compiled get(int) bodies exist for
// these two lists. Under the real CLR precedent, they would not.
```

Nothing in this snippet is illegal Java — the wrongness is in the unstated assumption about what a reified runtime *would have generated*, which the arithmetic in §2 works through explicitly.

**Right**

Reason about representation size before assuming bloat: `CashEntry` and `BonusEntry` references are both one machine word, so `ArrayList<CashEntry>.get(int)` and `ArrayList<BonusEntry>.get(int)` would be identical generated instructions apart from a type label a reified JVM's JIT could freely share — exactly the choice the CLR's own JIT makes for every reference-type instantiation today, confirmed in §1's `[RESEARCH]`. The bloat cost is real only where element representation genuinely differs in size or layout — value types — which is precisely the boundary Valhalla's specialised generics are scoped to, not "every generic type, unconditionally."

**Why people believe it:** "one class per type argument" is the naive mental model of what reification means, and it is true for the value-type case that gets talked about most (avoiding `int` boxing) — but generalising that one case to every generic instantiation, including the overwhelmingly common reference-type case, is the exact error the arithmetic in §2 was written to correct.

### "Any anonymous subclass of a generic type lets you recover the type argument, no matter how it's constructed"

**Wrong**

```java
VerdictTypeRef<?> raw = new VerdictTypeRef() {};
System.out.println(raw.type());
```

Run on JDK 21.0.7, this never reaches the `println` — the constructor itself throws:

```
Exception in thread "main" java.lang.IllegalStateException: VerdictTypeRef constructed without a type argument - use new VerdictTypeRef<List<Money>>() {}, not new VerdictTypeRef() {}
```

**Right**

```java
VerdictTypeRef<List<Money>> ref = new VerdictTypeRef<List<Money>>() {};
System.out.println(ref.type());   // java.util.List<Money>
```

The braces alone do not carry the type argument — the **type argument written between the angle brackets on the same line as the braces** is what the anonymous subclass's `extends` clause records. Drop the angle-bracket argument and the subclass's `Signature` attribute (§3's grammar walk) never gets written at all; `getGenericSuperclass()` then returns the plain, un-parameterised `Class` object for `VerdictTypeRef`, and the `instanceof ParameterizedType` check that gates the whole trick correctly fails.

**Why people believe it:** every worked example of this pattern — including this file's own — writes the type argument and the braces together so consistently that it is easy to mentally credit the braces alone with the magic, when the braces only create the subclass; the angle-bracket argument is what that subclass's declaration actually needs to contain for there to be anything to recover.

## Cheat sheet

| Question | Answer | Where proved |
|---|---|---|
| Why is erasure the design, not a runtime version bump like C#? | Binary compatibility, both link directions, no recompilation, no JVM version requirement — proved by identical descriptors and running both call directions | §1 |
| What does C#/.NET do instead? | Reifies: per-instantiation JIT-compiled bodies for value types, one shared body for reference types | §1 `[RESEARCH]` |
| What does Valhalla actually ship as of JDK 28? | JEP 401, value classes/objects (Preview) — identity-free, flattenable instances; specialised generics are separate, later work | §1 `[RESEARCH]` |
| What would reification have bought? | Legal `new T[n]`, decidable `instanceof List<X>`, real per-instantiation `Class` objects, no overload clash, no bridge-method workaround, no varargs heap pollution | §2 |
| What would reification have cost? | Metadata size, class-loading time, the compatibility break itself — and genuine code bloat only for value-typed instantiations | §2 |
| Would reification have fixed invariance? | No — invariance is a soundness property, independent of runtime representation | §2 |
| What survives erasure into a class file? | A type argument written in a *declaration* (`extends`, `implements`, a field, a method signature) — via a `Signature` attribute | §3 |
| What does not survive? | A type argument used only in a `new` expression or a local variable | §3 |
| Grammar for a class's `Signature` attribute | `ClassSignature: [TypeParameters] SuperclassSignature {SuperinterfaceSignature}`, each a `ClassTypeSignature` (leading `L`, binary name, trailing `;`, recursively nestable via `TypeArguments`) | §3, JVMS §4.7.9.1 |
| What breaks if you build the raw form of a super type token? | No `Signature` attribute is emitted at all; `getGenericSuperclass()` returns a plain `Class`, and the code must guard for it | §3 |
| Why give a super type token `equals`/`hashCode`? | So it can key a cache — exactly what Jackson's `TypeReference` and Guice's `TypeLiteral` do internally | §3 |

## Self-test

**Q1.** What exact property does the `invokeinterface` descriptor proof in §1 demonstrate, and why does that property force erasure rather than merely suggest it?

<details><summary>Answer</summary>

It demonstrates that a call to `List.add` compiles to the identical constant-pool descriptor, `(Ljava/lang/Object;)Z`, whether the caller was written against a raw `List` or a `List<CashEntry>`. That identity is not incidental — it is exactly the property that lets a class file compiled before generics existed and a class file compiled against a parameterised type link against each other with no recompilation and no runtime version requirement, in both directions. If `javac` had instead emitted a distinct descriptor per type argument, old bytecode calling into a new generic class (or vice versa) would fail to link, because the two sides would be looking for different method signatures — which is precisely the scenario Sun's 1.4-compatibility promise ruled out.

</details>

**Q2.** According to Microsoft's own generics documentation and corroborating primary engineering sources, how does the CLR treat a reference-type generic instantiation differently from a value-type one, and what Java-side concept does that reference-type treatment resemble?

<details><summary>Answer</summary>

For a value-type instantiation, the CLR's JIT generates a separate, specialised native code body per distinct type argument, because each value type has its own size and layout and storing it unboxed requires code tailored to that layout. For a reference-type instantiation, every type argument is just a pointer of identical size, so the JIT generates and shares a single compiled body across every reference-type instantiation of a generic type, carrying the actual type argument only in metadata. That reference-type sharing behaves, at the level of generated code, like Java's erasure — one shared implementation regardless of the specific reference type — even though the CLR is described as a reified, not erased, generics implementation overall.

</details>

**Q3.** As of this note's writing, what has Project Valhalla actually shipped, what is explicitly separate future work, and what does JEP 401 change about existing (reference-type) generics?

<details><summary>Answer</summary>

JEP 401, "Value Objects (Preview)," has been integrated for JDK 28 (targeted for release, with early-access builds already available; JDK 27 ships without it). It introduces value classes — identity-free, immutable instances a JVM may scalarize into fields or flatten into a compact representation, changing what `==` means for those instances. Specialised generics — the feature that would let a generic container avoid boxing a value class's fields by giving it its own flattened representation per instantiation — is explicitly separate, later work, not part of JEP 401 and not landing in JDK 28. JEP 401 changes nothing about existing reference-type generics: erasure, bridge methods, the overload clash, and every other mechanism this chapter has proven remain exactly as they are on JDK 21.

</details>

**Q4.** Work through, in size and layout terms, why reification's "code bloat" cost applies to a `List<CashEntry>` versus a `List<BonusEntry>` far less than it applies to a hypothetical `List<int>` versus `List<long>`.

<details><summary>Answer</summary>

`CashEntry` and `BonusEntry` are both reference types, so a `List` holding either stores a one-machine-word pointer per element regardless of which type it is — the generated code for `get(int)`, `add(Object)`, and every other method is identical between the two instantiations apart from a type label a JIT is free to share, exactly as the CLR's own JIT shares one compiled body across reference-type instantiations. `int` and `long` are different sizes (4 bytes versus 8) stored unboxed inline rather than by reference, so a reified `List<int>` and a reified `List<long>` genuinely need different storage layouts and different generated code to read and write elements correctly — there is no shared body that could serve both without either boxing (defeating the point) or generating two bodies. The bloat cost is real specifically where the underlying representation size differs, not wherever a distinct type argument appears.

</details>

**Q5.** Explain, using the argument in §2's variance paragraph, why a fully reified `List<CashEntry>` would still not be assignable to a `List<LedgerEntry>`.

<details><summary>Answer</summary>

If it were assignable, code holding the resulting `List<LedgerEntry>` reference could legally call `add` with a freshly constructed `BonusEntry`, because `BonusEntry` is a `LedgerEntry`. That call would insert a `BonusEntry` into storage that every other reference to the same list — still typed as `List<CashEntry>` elsewhere in the program — expects to contain only `CashEntry` instances. That unsoundness has nothing to do with whether the runtime representation is erased or reified; it follows purely from the fact that `List` is a mutable container and `add` accepts anything assignable to the declared element type. Reification changes how the runtime represents `List<CashEntry>`, not whether allowing this assignment would be unsound, so invariance is required either way.

</details>

**Q6.** Quote the `ClassSignature` and `ClassTypeSignature` productions from JVMS §4.7.9.1 and explain, using them, why `LVerdictTypeRef<Ljava/util/List<LMoney;>;>;` needs exactly three closing `;` characters and not one.

<details><summary>Answer</summary>

`ClassSignature: [TypeParameters] SuperclassSignature {SuperinterfaceSignature}`, and `SuperclassSignature` is itself a `ClassTypeSignature: L [PackageSpecifier] SimpleClassTypeSignature {ClassTypeSignatureSuffix} ;`. Each `ClassTypeSignature` production is self-contained and must terminate in its own `;` — and the grammar is recursive, because a `SimpleClassTypeSignature`'s optional `TypeArguments` block can itself contain a `TypeArgument` whose `ReferenceTypeSignature` is another full `ClassTypeSignature`. The example string nests three such productions: the outer one for `VerdictTypeRef`, one nested inside its type argument for `List`, and one nested inside that for `Money`. Each of the three needs its own closing `;` to be well-formed under the grammar, which is why the string ends in three consecutive `;` characters, one per nesting level, read from innermost to outermost.

</details>

**Q7.** Compiling `new VerdictTypeRef() {}` (no type argument) and disassembling the resulting anonymous class, what is present in place of a `Signature` attribute, and why does that matter for the code that reads it back?

<details><summary>Answer</summary>

Nothing is present in place of it — there is no `Signature` attribute on that class file at all, only the plain `super_class` constant-pool pointer to the erased `VerdictTypeRef`. That matters because `getGenericSuperclass()` has nothing to parse into a `ParameterizedType` in that case; it returns the ordinary `Class` object for `VerdictTypeRef` instead. Code that assumes `getGenericSuperclass()` always returns a `ParameterizedType` and casts directly gets a `ClassCastException` from the cast itself; the correct pattern, used in this file's build, is an `instanceof ParameterizedType` check with an explicit `else` branch that throws a clearer, purpose-written exception naming the actual problem.

</details>

**Q8.** Given `VerdictTypeRef<Map<ClientId, List<Money>>>`, describe the sequence of reflective calls needed to reach the `Money` type, and why one level of `getActualTypeArguments()` is not enough.

<details><summary>Answer</summary>

`ref.type()` returns a `ParameterizedType` whose raw type is `Map` and whose `getActualTypeArguments()` returns a two-element array: `ClientId` (a plain `Class`, since `ClientId` has no type arguments of its own) and `List<Money>` (itself a `ParameterizedType`, not a plain `Class`). To reach `Money`, the value at index 1 must be checked with `instanceof ParameterizedType` and, if it passes, its own `getActualTypeArguments()[0]` read — a second application of the same call. One level only reaches `List<Money>` as an opaque `Type`; because `Map`'s value type argument is itself parameterised, recovering what is inside it requires walking one level deeper, which is exactly what any deserialiser handling nested generic types has to do rather than assuming every type argument is a leaf `Class`.

</details>

## Open questions

- The exact scope of what broke or needed recompilation across the .NET Framework 1.1-to-2.0 CLR generics transition, beyond "code targeting reified generics needs the new runtime," was not confirmed against a primary Microsoft migration document in this pass. A Microsoft-published 1.1-to-2.0 breaking-changes or migration document would settle it.
- The specific design and JEP number, if any, that will carry Valhalla's specialised ("universal") generics feature was not confirmed, because as of this writing that work is described only as separate, later work with no formally targeted JEP number. A future JEP proposal from the Valhalla project, once one is filed and targeted, would settle it.

---

**Leaves covered:** 3.5.14, 3.5.15, 3.5.16 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 516
