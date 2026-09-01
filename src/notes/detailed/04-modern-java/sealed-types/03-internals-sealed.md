# 04 Modern Java — Sealed types — INTERNALS (§3.10)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Sealed types — data oriented programming](02-data-oriented-programming.md) · Next: [Pattern matching — basics](../pattern-matching/01-basics.md)

Parts 1–2 covered sealed hierarchies as a design tool: how `permits` shapes a closed type
family, and how that closure lets `switch` become exhaustive without a `default`. This part
goes underneath the keyword. `sealed`, `non-sealed`, and `permits` are compiler-only vocabulary —
by the time you have a `.class` file, exactly one artifact survives to describe any of it, and
knowing what that artifact is (and is not) explains every enforcement behaviour a sealed
hierarchy exhibits at runtime, including the ones that surprise people who only ever read the
source.

## The shape of what actually survives to bytecode

Four class-file states are possible for a class or interface that participates in a sealed
family. The table is the map; the rest of this file is the streets.

| Source-level declaration | `PermittedSubclasses` attribute present? | `ACC_FINAL` set? | Can gain a new direct subtype later without recompiling this class file? |
|---|---|---|---|
| `sealed interface Verdict permits A, B, C, D` | Yes — lists `A`, `B`, `C`, `D` by constant-pool index | No (interfaces never carry `ACC_FINAL`) | No — the JVM rejects any fifth subtype at load time |
| `final class DocumentVerdict implements Verdict` | No | Yes | N/A — cannot be subclassed at all |
| `non-sealed class WealthVerdict implements Verdict` | No | No | Yes — an ordinary open class from here down |
| An ordinary, unsealed `class`/`interface` | No | Depends on source | Yes — the JVM performs no permitted-subclass check at all |

The load-bearing fact in that table, and the one this whole file unpacks: **only the sealed
declaration itself carries anything in the class file.** `final` reuses an access flag that has
existed since Java 1.0. `non-sealed` reuses nothing — it emits no attribute, no flag, no trace.
The JVM's enforcement machinery has exactly one hook to pull on the whole hierarchy: the
`PermittedSubclasses` attribute on the sealed supertype. Everything below follows from that one
fact.

---

### `PermittedSubclasses` is a class-file attribute, and there is no `ACC_SEALED` flag

**Mental model.** A sealed class file does not carry a badge that says "I am sealed." It carries
a guest list. `Verdict.class` does not have a bit anywhere that flips to 1 for "sealed" — it has
a named, structured attribute in its `attributes` table whose payload is four constant-pool
indices, each pointing at a `CONSTANT_Class_info` entry for one permitted subclass. The JVM's
question at class-derivation time is never "is my superclass sealed?" It is "does my superclass
carry a `PermittedSubclasses` attribute, and if so, am I on the list?" A class with that attribute
*is* sealed, full stop, regardless of what else is or is not set in its access-flags word — being
sealed is a property of *having the attribute*, not of any flag being on.

**Why it exists.** Before JDK 17, "closed hierarchy" was pure source-code fiction enforced by
convention: `abstract class Verdict` with a `private` constructor and every subclass declared as
a `static` nested class of `Verdict` itself, or the classic *Effective Java* visitor-pattern idiom
— one interface, an enumerable but *unenforced* set of implementations, and a `visit` method per
implementation because the language had no way to make `switch` check you covered every case. The
compiler had zero visibility into whether that set was actually closed; a second compilation unit
on the classpath could add `class RogueVerdict extends Verdict` and nothing structural stopped it
— only social convention and code review did. JEP 409 (finalized in Java 17, after two rounds as
a preview feature in 15 and 16) needed a mechanism that a *pattern-matching switch* could ask
"have I covered every case?" and get a trustworthy yes — trustworthy meaning verifiable by the
compiler at the call site and re-verified by the JVM at every class load, not merely asserted by
whoever wrote the hierarchy.

**When to reach for it, and when not.** Reach for a sealed hierarchy exactly when you want the
compiler to prove `switch` exhaustiveness over a fixed, small family of shapes — `Verdict`'s four
outcome kinds (`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`) is the
canonical shape: closed by design, one variant behaviour each, never expected to grow without a
deliberate source change. Prefer a plain `enum` when the variants differ only by *value*, never by
*shape* — `RestrictionType` (`DEPOSIT_BLOCKED`, `STAKE_BLOCKED`, ...) needs no per-constant class
body, so an enum's simpler, singleton-per-constant model wins outright. Prefer the pre-17
open-visitor idiom, or a genuinely open interface, when third-party or plugin code must be able to
add a new implementation without recompiling your module at all — that is precisely the case
sealing forecloses, by design. A sealed hierarchy that later needs to grow past its permitted set
is not a bug to route around at the call site; it is a decision to reopen at the source, which
means touching the `permits` clause and recompiling everything downstream — see the
separate-compilation hazard later in this file for exactly what happens if you forget that last
part.

**How it works — the source and spec walk.** JVMS §4.7.31 defines the attribute's shape, added at
class file version 61.0 (Java SE 17):

```
PermittedSubclasses_attribute {
    u2 attribute_name_index;
    u4 attribute_length;
    u2 permitted_subclasses_count;
    u2 classes[permitted_subclasses_count];
}
```

Read it field by field: `attribute_name_index` is a constant-pool index whose UTF-8 value is
literally the string `"PermittedSubclasses"` — attributes in the class file format are named by
convention, not by a fixed opcode, so the JVM's attribute parser dispatches on this string.
`attribute_length` is the byte count of everything after it, standard for every attribute.
`permitted_subclasses_count` is `u2` (an unsigned 16-bit int, [NUM] max value 65,535 — nobody is
going to hit that ceiling with a sealed hierarchy, but it is the same width every other `*_count`
field in the class file uses, e.g. `interfaces_count`, `fields_count`). `classes[]` is the payload:
each entry is a `u2` constant-pool index, and each of those indices must resolve to a
`CONSTANT_Class_info` structure — the exact same constant-pool entry kind used for `this_class`,
`super_class`, and every entry in the `interfaces[]` table. There is nothing exotic about how a
permitted subclass is named; it is named the same way any other class reference in the file is
named.

Now compile the concrete example and read the real constant pool. `Verdict` is `QuizStakes`'s
sealed outcome hierarchy — a `Verdict(outcome, reason, decidedAt, decidedBy)` shape realised as
four leaf kinds:

```java
public sealed interface Verdict
        permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}

public final class DocumentVerdict implements Verdict {}
public final class ScreeningVerdict implements Verdict {}
public final class ReviewVerdict implements Verdict {}
public non-sealed class WealthVerdict implements Verdict {}
```

`javac --release 21` on that, then `javap -v Verdict.class`:

```
  minor version: 0
  major version: 65
  flags: (0x0601) ACC_PUBLIC, ACC_INTERFACE, ACC_ABSTRACT
  this_class: #1                          // Verdict
  super_class: #3                         // java/lang/Object
Constant pool:
   #7 = Utf8               PermittedSubclasses
   #8 = Class              #9             // DocumentVerdict
   #9 = Utf8               DocumentVerdict
  #10 = Class              #11            // ScreeningVerdict
  #11 = Utf8               ScreeningVerdict
  #12 = Class              #13            // ReviewVerdict
  #13 = Utf8               ReviewVerdict
  #14 = Class              #15            // WealthVerdict
  #15 = Utf8               WealthVerdict
PermittedSubclasses:
  DocumentVerdict
  ScreeningVerdict
  ReviewVerdict
  WealthVerdict
```

Read the `flags` line first, because this is the crux of leaf 3.10.2: `(0x0601) ACC_PUBLIC,
ACC_INTERFACE, ACC_ABSTRACT`. `[NUM]` `0x0601` decomposes as `0x0001 (ACC_PUBLIC) | 0x0200
(ACC_INTERFACE) | 0x0400 (ACC_ABSTRACT)` — three flags any ordinary public interface already
carries, nothing added. JVMS §4.1's Table 4.1-B enumerates every legal class-access flag that
exists: `ACC_PUBLIC (0x0001)`, `ACC_FINAL (0x0010)`, `ACC_SUPER (0x0020)`, `ACC_INTERFACE
(0x0200)`, `ACC_ABSTRACT (0x0400)`, `ACC_SYNTHETIC (0x1000)`, `ACC_ANNOTATION (0x2000)`,
`ACC_ENUM (0x4000)`, `ACC_MODULE (0x8000)`. There is no `ACC_SEALED` anywhere on that list, in
Java 21 or in any later spec revision as of this writing — sealing was never given a bit. The
class-pool dump below `flags` is where the real signal lives: `PermittedSubclasses` appears as a
named attribute at constant-pool index `#7`, and the four permitted names follow as ordinary
`Class` constant-pool entries at `#8`, `#10`, `#12`, and (not shown above but present) a fourth
for `WealthVerdict`. **`Verdict` is sealed because it carries this attribute, not because of
anything in its flags word.**

**D-152 — `PermittedSubclasses` is enforced at load time**, embedded here because this is the
point in the explanation where the reader needs the whole picture at once — the attribute's
shape, the bytecode-manipulated intruder, and the JVM's rejection of it, in one sequence:

![D-152 — `PermittedSubclasses` is enforced at load time](../diagrams/D-152-permittedsubclasses-enforced-load-time.svg)
**D-152** — `PermittedSubclasses` is enforced at load time

Frame 1 of that diagram is exactly the `javap` dump above: `Verdict`'s class file, its
`PermittedSubclasses` attribute listing four constant-pool indices, and the explicit callout that
no `ACC_SEALED` flag exists anywhere on it. Frames 2 and 3 are the load-time enforcement story,
which the next primary concept below walks through with its own runtime reproduction. The note in
the diagram about `non-sealed` emitting no attribute at all is this section's other half — proved
right now, before moving on.

`non-sealed class WealthVerdict implements Verdict` compiles to a class file that is, in every
byte that matters, indistinguishable from an ordinary open class:

```
javap -v WealthVerdict.class
  flags: (0x0020) ACC_SUPER
```

That is the *only* flag: `ACC_SUPER`, the historical flag every class file has carried since
before `invokespecial`'s modern semantics were nailed down, and which `javac` sets on essentially
every class regardless of sealing. Grep the whole class file — `attributes` table, flags word,
constant pool — and there is no `PermittedSubclasses`, no marker interface, no synthetic method,
nothing that says "this class used to be `non-sealed`." Leaf 3.10.3's claim is exactly this: `non
-sealed` is a **compile-time-only acknowledgement**. The compiler *requires* the modifier — try
compiling `WealthVerdict` as a bare `class` (no modifier) implementing sealed `Verdict` and you
get a compile error, because `javac` insists every direct subtype of a sealed type spell out
its own sealing intent (`sealed`, `final`, or `non-sealed`) so that intent is never accidental.
But once that requirement is satisfied at the source level, the compiler discards the information
completely. `WealthVerdict.class` retains no evidence it was ever constrained. If `WealthVerdict`
itself gains a subclass tomorrow, nothing in `WealthVerdict.class` needs to change, because
nothing in it ever recorded the constraint in the first place — the class file has always looked
exactly like an ordinary open class, because from the JVM's perspective, past its own definition,
that is exactly what it is.

**Insight:** this is why `Class.isSealed()` (leaf 3.10.7, covered later in this file) has to be
reflection over the *live* class object's cached metadata, not a bytecode search — but more
importantly, it is why `non-sealed` cannot be un-done by any means short of recompiling the source
with a different modifier. There is no bit to flip back.

**The gotcha.** People assume `sealed`, `final`, and `non-sealed` are three flavors of the same
kind of class-file marking, because they read like three keywords in the same grammar production
(`ClassModifier`). They are not three flavors of one thing. `final` is an access flag that
predates sealed types by two decades and would forbid subclassing with or without JEP 409 ever
having existed. `non-sealed` is compiler bookkeeping that leaves zero trace. Only the *sealed*
declaration itself produces a new, JEP-409-specific class-file artifact. Three keywords, one
attribute.

> A sealed class or interface is one whose class file carries a `PermittedSubclasses` attribute;
> sealing is recorded as data listing permitted subtypes by constant-pool index, never as an
> access flag, and `non-sealed` leaves no trace at all in the class file that declares it.

---

### Load-time enforcement: sealing survives bytecode manipulation

**Mental model.** The compiler's exhaustiveness check and the JVM's sealing check are two
separate gates guarding the same door, and only one of them is a security boundary. `javac`
refusing to compile `class RogueVerdict implements Verdict` (because `RogueVerdict` is not in
`permits`) is a *courtesy* — it stops an honest mistake at the earliest, cheapest point. It is not
what actually keeps a sealed hierarchy closed, because `javac` is not in the loop for every class
file that ever reaches a JVM. Class files can be generated by other compilers, retrieved from a
different classpath entry than the one that built the sealed type, or hand-assembled with a
bytecode library. The real gate — the one that cannot be bypassed by skipping `javac` — sits
inside `ClassLoader.defineClass`, at the moment any class is actually derived into a runnable
`Class` object.

**Why it exists.** If sealing were only a `javac` diagnostic, it would be exactly as strong as
`private` was before Java 9's module system: a convention the compiler enforces for the classes it
happens to compile together, and nothing stops a class file assembled by any other means from
simply not going through that check. Exhaustive `switch` over a sealed type is a genuine safety
property — the compiler tells you a `switch` covers every case with no `default` needed, and the
whole value of that guarantee evaporates if "every case" can silently grow a case the switch was
never told about. JEP 409's design has to close that gap at the only point every class,
regardless of provenance, is forced to pass through: class loading.

**When to reach for it, and when not.** This is not a mechanism you invoke — it is one you rely
on implicitly the moment you write `permits`. The place this matters practically: if you are
reasoning about whether a sealed hierarchy is trustworthy against adversarial or just
poorly-behaved bytecode (a plugin system, a serialization library that reconstructs objects by
class name, a malformed JAR on the classpath), the answer is "yes, load-time enforcement holds,"
full stop — you do not need `javac` to have been anywhere near the offending class file for the
protection to apply. The place it does *not* help you: reflection can still *construct* an
instance of any class already validly loaded, sealed or not, via `setAccessible(true)` on a
private constructor — sealing constrains the *type hierarchy*, not construction access, and those
are different concerns entirely.

**How it works — the JVMS text, quoted and read.** JVMS §5.3.5, "Deriving a Class from a `class`
File Representation," step 3 (direct superclass) and step 4 (direct superinterfaces, applied per
interface) both state the identical rule; here is the superinterface form, which is the one
`Verdict` (an interface) exercises:

```
Otherwise, for each direct superinterface named by C, if the superinterface has a
PermittedSubclasses attribute (§4.7.31) and any of the following is true, derivation
throws an IncompatibleClassChangeError:

  * The superinterface is in a different run-time module than C (§5.3.6).
  * C does not have its ACC_PUBLIC flag set (§4.1) and the superinterface is in a
    different run-time package than C (§5.3).
  * No entry in the classes array of the superinterface's PermittedSubclasses
    attribute refers to a class or interface with the name N.
```

Read each line. The first bullet is the module check (leaf 3.10.5, expanded on its own below).
The second bullet is the unnamed-module fallback: without modules in play, package identity
substitutes for module identity, but only when `C` itself is not `public` — a subtlety worth
sitting with, because it means a **public** permitted subclass in a *different* package from its
sealed supertype passes this particular bullet regardless of package, and is checked purely on
module identity instead. The third bullet is the one everyone remembers: `C`'s binary name has to
appear, byte for byte, in the array of names the superinterface's `PermittedSubclasses` attribute
carries. Fail any of the three, and the JVM does not link `C` at all — it throws
`IncompatibleClassChangeError`, a `LinkageError` subtype, out of class derivation, which happens
inside `ClassLoader.defineClass` before `C` becomes a usable `Class` object at all. There is no
partial load, no way to catch the exception and proceed with a half-defined class; the JVM
verifier refuses to produce the class at all.

**[PROVE]** — reproduce it rather than take the spec's word for it. Compile `Verdict4` with five
permitted subclasses, including a fifth, `RogueVerdict`:

```java
// v1 — compiled once, with RogueVerdict legitimately in the permits list
public sealed interface Verdict4
        permits DocumentVerdict4, ScreeningVerdict4, ReviewVerdict4, WealthVerdict4, RogueVerdict {}
public final class RogueVerdict implements Verdict4 {}
```

`RogueVerdict.class`, compiled against that version, is a perfectly legitimate, `javac`-produced
class file — nothing about it is hand-edited. Now recompile *only* `Verdict4` and its four
intended subclasses from a second source tree that drops `RogueVerdict` from `permits`:

```java
// v2 — recompiled without RogueVerdict
public sealed interface Verdict4
        permits DocumentVerdict4, ScreeningVerdict4, ReviewVerdict4, WealthVerdict4 {}
```

`javap -v` on the v2 class file confirms the guest list shrank to four names — `DocumentVerdict4`,
`ScreeningVerdict4`, `ReviewVerdict4`, `WealthVerdict4` — exactly the shape D-152's frame 1 shows.
Put the *old* `RogueVerdict.class` (from v1) on the classpath together with the *new* `Verdict4
.class` (from v2) — simulating a fifth subclass that reached the classpath by any means other
than a clean, synchronized recompilation, bytecode manipulation included, since from the JVM's
point of view a hand-edited class file and a stale one from an earlier compilation are
indistinguishable — and load it:

```
Exception in thread "main" java.lang.IncompatibleClassChangeError: Failed listed permitted subclass check: class RogueVerdict is not a permitted subclass of Verdict4
	at java.base/java.lang.ClassLoader.defineClass1(Native Method)
	at java.base/java.lang.ClassLoader.defineClass(ClassLoader.java:962)
	at java.base/java.security.SecureClassLoader.defineClass(SecureClassLoader.java:144)
	at java.base/jdk.internal.loader.BuiltinClassLoader.defineClass(BuiltinClassLoader.java:776)
	at java.base/jdk.internal.loader.BuiltinClassLoader.findClassOnClassPathOrNull(BuiltinClassLoader.java:691)
	at java.base/jdk.internal.loader.BuiltinClassLoader.loadClassOrNull(BuiltinClassLoader.java:620)
	at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:578)
	at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:490)
	at java.base/java.lang.Class.forName0(Native Method)
	at java.base/java.lang.Class.forName(Class.java:467)
	at java.base/java.lang.Class.forName(Class.java:458)
	at User4.main(User4.java:3)
```

That is D-152's frames 2 and 3, reproduced on real Java 21 bytecode semantics (run here on a JDK
25 runtime with `--release 21` class files, so the class-file version and API surface match Java
21 exactly, even though the JIT and exact diagnostic string formatting come from the runtime
actually executing). Notice where the stack trace bottoms out: `ClassLoader.defineClass1`, a
native method — the check is not Java-level reflection, it is inside the class-parsing machinery
itself, the same layer that rejects a class file with a bad magic number or an unverifiable
bytecode sequence. `RogueVerdict`'s own bytecode is completely valid, standalone; it fails purely
because the interface it claims to implement no longer lists it.

**The gotcha.** The natural mistake is to think "I recompiled the sealed interface, so anything
that used to implement it and got left behind will just silently stop being one of its subtypes."
It does not silently stop being anything — it fails to *link* at all, loudly, the first time the
JVM tries to derive it, which for a class loaded lazily (the JVM default) can be arbitrarily far
into a program's run, long after start-up succeeded. This is the general case of leaf 3.10.8's
separate-compilation hazard, covered in full later in this file with the pattern-matching-`switch`
variant specifically.

> A permitted subclass is enforced against its sealed supertype at class derivation
> (JVMS §5.3.5), inside `ClassLoader.defineClass`, every time that subclass is loaded — not once,
> at compile time, by whichever compiler happened to produce the two class files — which is
> exactly why sealing holds even against a class file that never went through `javac` at all.

---

### Same-module (or same-package) enforcement — the boundary the check actually draws

**Mental model.** `PermittedSubclasses` names subclasses by binary name only — a string like
`RogueVerdict` inside a `u2` index into a `CONSTANT_Class_info`. A bare name says nothing about
*where* that class is allowed to come from. The second and third bullets of the §5.3.5 rule quoted
above are what close that gap: they tie a permitted name to a *place* — the same run-time module,
or (for a non-`public` permitted subclass with no module system in play) the same run-time
package — so that a same-named class smuggled in from a different module cannot satisfy the
check.

**Why it exists.** Without a locality requirement, the name-matching bullet alone is a much weaker
guarantee than it looks: `Verdict.PermittedSubclasses` lists the *string* `"WealthVerdict"`, and
if any module on the runtime module path could define a class named `WealthVerdict` that happened
to implement `Verdict`, sealing would only be closed against classes of *other* names — an
attacker (or, far more commonly, a build misconfiguration producing two shaded copies of the same
class) could still satisfy the third bullet with a class that was never part of the intended
hierarchy at all. Tying the check to run-time module or package identity, not just name, is what
makes "permitted" mean "permitted from a specific, already-trusted place," not merely "permitted
if named correctly."

**When to reach for it, and when not.** This is not something you configure — it falls out of how
you already package the hierarchy. A sealed interface and every one of its permitted subclasses
living in the same JPMS module (the common case for an application module that is not split
across module boundaries) always satisfies the module bullet trivially, because "same module" is
the default outcome of ordinary compilation. It only becomes a decision point if you are
deliberately splitting a sealed hierarchy's declaration from one or more of its implementations
across module boundaries — at which point the answer is: don't, unless the split module also
exports the sealed type to the implementing module and both modules are visible to each other at
run time, because the module bullet will otherwise fail regardless of the name matching correctly.

**How it works.** Re-reading the two locality bullets from §5.3.5 side by side: bullet one fires
whenever the permitted subclass's run-time module differs from its sealed supertype's run-time
module — this check applies unconditionally, independent of anyone's `public`/package-private
status, because module boundaries are the primary locality unit in a modular runtime. Bullet two
is the fallback for code that is not modularized at all, or where the permitted class is not
`public`: run-time package identity substitutes for module identity, but *only* when the
permitted class is not `public`. That asymmetry is deliberate — a `public` sealed hierarchy is
explicitly designed to let a `public` permitted subclass live in a different package for API
organisation reasons (a common pattern: the sealed interface in a `verdict` package, its four
leaf records fanned out into narrower sub-packages by concern), while a non-`public` permitted
subclass has no other visibility path to the outside world, so package co-location is the only
thing standing in for "we both agree this is intentional."

`[X-REF 03]` The classloader identity and module-graph machinery this check leans on — what
"run-time module" and "run-time package" formally mean, how the boot/platform/application
classloader delegation model decides which loader defines a given class, and why two classes with
identical binary names loaded by different classloaders are, from the JVM's point of view, simply
different types — is guide 03 (Java core)'s territory in full; the load-time check here consumes
that identity model as a black box, it does not define it.

**The gotcha.** The check is phrased as "run-time module," not "compile-time module," which
matters the moment you introduce a custom classloader, an application server with per-deployment
classloader isolation, or an OSGi-style dynamic module graph: two classes compiled from source
that lived in the same module at build time can end up in different *run-time* modules if the
deployment topology splits them across classloaders, and the sealing check will fail exactly as
if they had never been related at all — a failure mode that looks identical to the recompiled-
without-the-subclass hazard from the previous section, but has a completely different root cause
(deployment topology, not staleness), so misdiagnosing one as the other wastes real debugging
time.

> A permitted subclass satisfies §5.3.5 only if its binary name is listed *and* it shares its
> sealed supertype's run-time module — or, for a non-`public` permitted subclass with no modules
> involved, its run-time package — so a same-named class from the wrong place is rejected exactly
> as hard as a class that was never on the list at all.

---

### Narrowing reference conversion over a sealed hierarchy

**Mental model.** An unchecked-widening/narrowing cast between two unrelated open reference types
is `javac`'s way of saying "I cannot prove this is wrong, so I will let the runtime `ClassCastException`
sort it out." A cast between two *sibling* leaves of a sealed hierarchy is different: `javac` has
complete, closed knowledge of every possible runtime type either side of the cast could ever hold,
because sealing has already told it the exhaustive list — so it can actually *prove* certain casts
are impossible, and it rejects them the same way it rejects casting an `int` to a `String`.

**Why it exists.** JLS §5.5 has always defined narrowing reference conversion with a legality
question attached: is it *possible*, given the two static types, for some object to be an instance
of both? For two unrelated ordinary classes, the answer is always "maybe" (multiple interface
implementation, or a subclass yet to be written that implements both), so the compiler must permit
the cast and defer the real check to `checkcast` at run time. For two *disjoint leaves of the same
sealed hierarchy*, the compiler can answer definitively: no object can simultaneously be a
`DocumentVerdict` and an unrelated `WealthVerdict`-only-shaped type, because `final` (or, for
`WealthVerdict`, its own closed continuation) forecloses any subclass that could implement both.
Sealing converts "maybe" into "no" for a whole category of casts, and the compiler exploits that.

**When to reach for it, and when not.** You do not "reach for" this — it is a side effect the
compiler gives you for free once a hierarchy is sealed, and it is one of the strongest arguments
for sealing a hierarchy you already control end to end: a bug that would silently compile as a
runtime `ClassCastException` risk against an open hierarchy becomes a *compile error* against a
sealed one. The sibling this loses against: an **open** hierarchy — any interface without
`permits` — where the compiler cannot make this argument at all, and every narrowing cast between
unrelated implementors compiles and is deferred to `checkcast`, succeeding or throwing only at
run time.

**How it works — proving it, not asserting it.** Declare a small closed pair and an unrelated
type, then attempt the cast:

```java
sealed interface Verdict2 permits DocumentVerdict2, ScreeningVerdict2 {}
final class DocumentVerdict2 implements Verdict2 {}
final class ScreeningVerdict2 implements Verdict2 {}
final class WealthVerdict2 {}   // deliberately NOT part of the Verdict2 hierarchy

class Narrow {
    static void cast(DocumentVerdict2 d) {
        Object o = (WealthVerdict2) d;   // attempted narrowing cast
    }
}
```

`javac --release 21`:

```
Narrow.java:7: error: incompatible types: DocumentVerdict2 cannot be converted to WealthVerdict2
        Object o = (WealthVerdict2) d;
                                    ^
1 error
```

This is a hard compile error, not a warning, and it fires specifically because `DocumentVerdict2`
is `final` — the compiler can enumerate every possible runtime type of a `DocumentVerdict2`-typed
reference (there is exactly one: `DocumentVerdict2` itself), see that `WealthVerdict2` is not among
them and is itself unrelated and `final`, and conclude the cast can never succeed for any object,
ever. Contrast the same cast with an **open** hierarchy: replace `sealed interface Verdict2` with
a plain, unsealed `interface Verdict2Open {}` and the identical cast compiles cleanly, deferring to
a runtime `checkcast` bytecode that throws `ClassCastException` only if some concrete object at
that call site genuinely fails the check — because now `javac` cannot rule out a future,
as-yet-unwritten class implementing both types.

**The gotcha.** This only fires when the compiler can see the *full* picture — both types have to
resolve to compile-time-known classes on the same compilation's classpath, and the sealed type
has to actually be sealed at the version being compiled against. If `DocumentVerdict2` is
compiled against a *stale* copy of `Verdict2` that predates sealing (a classpath ordering bug, or
a shaded dependency shipping an old class file), the impossible-cast proof silently does not
trigger — the compiler reasons from whatever `Verdict2.class` it can actually see, and an
unsealed view of a hierarchy that is sealed in the "real" copy on the runtime classpath produces
no warning that the safety net has quietly gone missing.

> Between two disjoint leaves of a sealed hierarchy the compiler can prove no object satisfies
> both static types, so it rejects the narrowing cast at compile time — a promotion from a
> `ClassCastException` you might hit in production to a build failure you hit at `javac`, available
> only because sealing gives the compiler a closed set of possibilities to reason over.

---

### `Class.isSealed()` and `Class.getPermittedSubclasses()` (supporting fact)

**Mechanism.** `java.lang.Class` exposes two reflective methods added alongside sealed types:
`isSealed()` returns `true` exactly when the receiver's class-file metadata includes a
`PermittedSubclasses` attribute (the same signal §5.3.5 checks, exposed as a boolean), and
`getPermittedSubclasses()` returns a `Class<?>[]` resolved from that attribute's entries — an
empty array for a class that is not sealed, never `null`. Both are pure reads over metadata the
JVM already parsed and cached when the class was loaded; neither triggers any additional class
loading of the permitted subclasses themselves beyond what `Class` objects require to exist as
values in the returned array.

```java
System.out.println(Verdict.class.isSealed());                         // true
for (Class<?> c : Verdict.class.getPermittedSubclasses()) {
    System.out.println(c.getName());
}
// DocumentVerdict
// ScreeningVerdict
// ReviewVerdict
// WealthVerdict
System.out.println(WealthVerdict.class.isSealed());                   // false — non-sealed leaves no trace, per the earlier section
```

The practical use this API earns its keep for: writing a test that asserts a sealed hierarchy's
exhaustiveness contract has not silently regressed — iterate `getPermittedSubclasses()` and assert
some property (a `record` component shape, a required annotation, a naming convention) holds for
every current permitted subclass, so that adding a fifth `Verdict` variant without updating every
downstream `switch` fails a test immediately rather than waiting for a `MatchException` in
production, which is exactly the failure mode the next section covers in full.

**Gotcha.** `getPermittedSubclasses()` returns *direct* permitted subclasses only, one level of
the hierarchy — it does not recursively flatten a multi-level sealed hierarchy (a sealed
interface permitting another sealed interface, which itself permits concrete leaves) down to the
concrete leaves. Walking a multi-level sealed tree to its leaves requires recursing on
`isSealed()`/`getPermittedSubclasses()` yourself.

> `Class.isSealed()` and `Class.getPermittedSubclasses()` are direct reflective reads of the
> `PermittedSubclasses` attribute's cached metadata — one level deep, never recursive, and the
> only two program-visible booleans/arrays a sealed hierarchy exposes about its own shape.

---

### The separate-compilation hazard: `MatchException`, not a link error

**Mental model.** A `switch` expression pattern-matching over a sealed type without a `default`
arm is exhaustive *as of the moment it is compiled* — the compiler burns the then-current
permitted-subclass list into the `switch`'s generated dispatch logic. That dispatch logic does not
re-derive "have I covered every case" from the sealed type's *current* `PermittedSubclasses`
attribute at run time; it re-derives it from what the sealed type's attribute looked like when the
`switch` itself was compiled. If the two ever drift — the sealed hierarchy gains a member and gets
recompiled, but the module containing the `switch` does not — the `switch` is now silently
*not* exhaustive against the hierarchy it is actually running against, and something has to fire
when a value of the new, unanticipated shape shows up.

**Why it exists.** This is the direct cost of buying compile-time exhaustiveness proofs at all:
any proof burned into bytecode at compile time is a snapshot, and every snapshot can go stale
against a world that keeps moving. The alternative — re-deriving exhaustiveness from the sealed
type's live metadata on every `switch` evaluation — would make every pattern-matching `switch` pay
a reflective-lookup cost per invocation for a guarantee the compiler could otherwise give for
free at zero runtime cost in the common case where nothing has drifted. Java's design keeps the
zero-cost path for the common case and accepts a well-defined runtime failure for the
separate-compilation case, rather than paying for a check the vast majority of `switch`
evaluations do not need.

**When to reach for it, and when not.** There is nothing to "reach for" here — this is a hazard
to defend against, not a feature to use. The defense is organisational, not linguistic: a sealed
hierarchy and every `switch` over it that omits a `default` are one *release unit*. If your build
graph allows the sealed hierarchy's module to be republished independently of every module that
switches over it (a shared library scenario is the classic trigger), you have built exactly the
topology this hazard needs. `[X-REF 03]` guide 03 (Java core) covers binary compatibility rules in
general; this is the sealed-types-specific instance of the broader class.

**[PROVE][BYTECODE]** — the mechanism, worked from source through bytecode to the actual thrown
exception. Compile a two-leaf sealed interface and an exhaustive `switch` over it in one pass:

```java
public sealed interface Verdict3 permits DocA, DocB {}
public final class DocA implements Verdict3 {}
public final class DocB implements Verdict3 {}

public class User {
    static String describe(Verdict3 v) {
        return switch (v) {
            case DocA a -> "A";
            case DocB b -> "B";
        };
    }
}
```

`javap -c` on `User.class`'s `describe` method shows exactly how the exhaustiveness proof is
encoded:

```
static java.lang.String describe(Verdict3);
    Code:
         0: aload_0
         1: dup
         2: invokestatic  #7                  // Method java/util/Objects.requireNonNull:(Ljava/lang/Object;)Ljava/lang/Object;
         5: pop
         6: astore_1
         7: iconst_0
         8: istore_2
         9: aload_1
        10: iload_2
        11: invokedynamic #13,  0             // InvokeDynamic #0:typeSwitch:(Ljava/lang/Object;I)I
        16: lookupswitch  { // 2
                       0: 54
                       1: 64
                 default: 44
            }
        44: new           #17                 // class java/lang/MatchException
        47: dup
        48: aconst_null
        49: aconst_null
        50: invokespecial #19                 // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
        53: athrow
        54: aload_1
        55: checkcast     #22                 // class DocA
        58: astore_3
        59: ldc           #24                 // String A
        61: goto          72
        64: aload_1
        65: checkcast     #26                 // class DocB
        68: astore        4
        70: ldc           #28                 // String B
        72: areturn
```

Read it instruction by instruction. `invokedynamic #13` calling `typeSwitch:(Ljava/lang/Object;I)I` is
the pattern-matching `switch` bootstrap (`SwitchBootstraps.typeSwitch`, generated by `javac`,
resolved once at first use via `invokedynamic`'s call-site linkage) — it takes the scrutinee and a
starting index and returns which case label index matched, `-1` semantics folded into whichever
index falls through to `default`. `lookupswitch` then dispatches on that returned integer: label
`0` (bound to `DocA`, seen at line `54`'s `checkcast #22`) goes to offset `54`, label `1` (`DocB`)
to `64`, and — this is the entire mechanism the hazard depends on — anything else, including an
index the bootstrap could never have produced for the two cases the `switch` *knew about at
compile time*, falls to `default: 44`. Offset `44` onward is the synthetic default: `new
MatchException`, `dup`, push two `null`s for the `(String, Throwable)` constructor, `invokespecial`
the constructor, `athrow`. There is no branch anywhere in this bytecode that consults `Verdict3
.class`'s *current* `PermittedSubclasses` at run time — the two cases the `lookupswitch` knows
about are baked into the `lookupswitch` table itself, at the offsets `javac` chose when it
compiled `describe`, against whatever `Verdict3.class` looked like at that moment.

Now reproduce the hazard exactly. Compile `Verdict3`/`DocA`/`DocB`/`User` together (this is the
"before" world — two permitted subclasses, `describe` exhaustive over both). Confirm it runs:
`describe(new DocA())` prints `A`. Then, **without touching `User.java` or recompiling it**, add a
third leaf to the source and recompile only the hierarchy:

```java
public sealed interface Verdict3 permits DocA, DocB, DocC {}
public final class DocC implements Verdict3 {}
```

Put the freshly recompiled `Verdict3`/`DocA`/`DocB`/`DocC` class files on the classpath ahead of
the *original* `User.class` and call `describe(new DocC())`. The measured result on this machine:

```
Exception in thread "main" java.lang.MatchException
	at User.describe(User.java:3)
	at User.main(User.java:10)
```

`DocC` loads without incident — `Verdict3`'s own `PermittedSubclasses` attribute now lists three
names, `DocC` is one of them, §5.3.5's check passes cleanly, this is not a `linkage` failure. The
failure happens one level up, inside `describe`'s own bytecode, at run time, the first time that
stale `lookupswitch` is handed a `DocC` instance the `typeSwitch` bootstrap has never seen before
and cannot match to either of the two indices `describe` was compiled to expect — the bootstrap
falls through to `default`, and the synthetic default throws `MatchException`.

**`[VERSION-TRAP]`** the exception type thrown by this synthetic default is itself
version-sensitive, and widely-repeated material states it backwards. Verified by compiling the
identical exhaustive-enum-switch-expression shape at three `--release` targets and running each:

```
release 14 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 17 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 21 -> Exception in thread "main" java.lang.MatchException
```

`javap -c` on the `--release 21` class file confirms it constructs `MatchException` with the
`(String, Throwable)` constructor, exactly as `describe`'s bytecode above does. The correct
statement, and the version trap worth stating explicitly because interviewers still ask for the
pre-21 form: **the synthetic default has existed since exhaustive switch expressions themselves
did, but the type it throws changed at Java 21** — `IncompatibleClassChangeError` through Java 20
(the same exception §5.3.5's *linkage*-level checks throw, which is exactly why it is easy to
conflate the two failure modes and why leaf 3.10.8's phrasing separates them), `java.lang
.MatchException` from Java 21 onward, purpose-built so a stale-switch failure is distinguishable
from an actual class-loading linkage failure by exception type alone.

**Pitfall:** believing this failure is a `LinkageError` — a class that would not even load — and
therefore assuming it would surface immediately at start-up, the same way a missing-class
`NoClassDefFoundError` would.

**Wrong**

```java
try {
    Verdict3 v = /* obtained from a service boundary compiled against a newer Verdict3 */;
    String label = switch (v) {
        case DocA a -> "A";
        case DocB b -> "B";
        // no default — "exhaustive," the developer believes, forever
    };
} catch (LinkageError e) {          // never fires — this is not what MatchException is
    label = "unknown";
}
```

**Right**

```java
String label = switch (v) {
    case DocA a -> "A";
    case DocB b -> "B";
    default -> throw new IllegalStateException(
        "Verdict3 gained a variant this switch was not recompiled against: " + v.getClass());
};
```

or, better, treat "the sealed hierarchy's module and every non-`default` switch over it recompile
together" as a release invariant enforced by the build (a single Gradle/Maven module, or a CI
check that fails a release if the hierarchy's version changed without every dependent recompiling)
rather than something to catch at run time at all — by the time `MatchException` fires, a
production request has already failed.

**Why people believe it:** `IncompatibleClassChangeError` genuinely is the exception a *related*
sealed-types failure throws — the §5.3.5 load-time rejection covered earlier in this file uses
exactly that type — so the two failure modes (a class rejected at load time versus a `switch`
falling through its stale synthetic default) get merged into one mental bucket of "sealed types
throw `IncompatibleClassChangeError` when something's out of sync," which was even *true* for the
`switch` case before Java 21 changed which exception the synthetic default constructs.

> A pattern-matching `switch`'s exhaustiveness proof is fixed at the compilation that produced it;
> recompiling the sealed hierarchy without recompiling every non-`default` switch over it leaves
> those switches silently non-exhaustive against the live hierarchy, surfacing at run time as
> `java.lang.MatchException` (Java 21+) or `IncompatibleClassChangeError` (before 21) the first
> time an unanticipated variant reaches the stale switch — never as a class-loading link error,
> because the class itself loads perfectly validly.

---

## Pitfalls

### Assuming `ACC_SEALED` exists and checking for it via bytecode tooling

**Wrong**

```java
// A hypothetical bytecode-analysis tool author's first instinct:
int flags = classNode.access;
boolean isSealed = (flags & ACC_SEALED) != 0;   // ACC_SEALED does not exist — this
                                                  // constant is not in java.lang.reflect
                                                  // or any bytecode library's access-flag set
```

Every access-flags bit position in the JVMS (`0x0001` through `0x8000`, per JVMS §4.1 Table 4.1-B)
is already assigned to something else — there is no free bit sealing could have used even if the
JEP's authors had wanted a flag.

**Right**

```java
boolean isSealed = someClass.isSealed();                       // java.lang.Class, Java 17+
// or, at the raw class-file level with a bytecode library:
boolean hasPermittedSubclassesAttr = classNode.permittedSubclasses != null
                                       && !classNode.permittedSubclasses.isEmpty();
```

**Why people believe it:** `final`, `abstract`, `interface`, `enum`, and every other class
modifier that predates Java 17 *is* an access flag, so a new keyword-driven modifier reads, on
first encounter, like it should follow the same pattern. Sealing was deliberately given a
structured attribute instead, specifically because it needs to carry a *list* of names, and an
access flag is a single bit with no room to name anything.

### Assuming a class recompiled against a newer sealed hierarchy is automatically safe once it compiles

**Wrong**

```java
// Module A recompiles Verdict to add a fifth leaf, WealthVerdict5.
// Module B, which switches over Verdict without a default, is NOT recompiled,
// because "it still compiles against the old Verdict.class on its own classpath"
// and nobody re-ran the build for B.
```

The failure here is invisible at Module B's own build time — B's build never sees the new
`Verdict.class` at all, so nothing red-flags anything. It only manifests the first time a live
`WealthVerdict5` instance reaches B's stale `switch` in production.

**Right**

Treat the sealed hierarchy and every non-`default` `switch` over it as one release unit — same
module, or a build-graph dependency that forces every consumer to recompile whenever the
hierarchy's `permits` clause changes. If cross-module distribution is unavoidable, require a
`default` arm on every `switch` over a sealed type that crosses a module boundary you do not fully
control the release cadence of, accepting the loss of the compiler's exhaustiveness proof in
exchange for a defined runtime behaviour instead of a hard failure.

**Why people believe it:** "if it compiles, it's safe" is true for almost everything else in Java
— type errors are exactly the class of bug the compiler is supposed to catch before you ship. A
`switch`'s exhaustiveness proof is unusual precisely because it is a proof about a *different*
compilation unit's current state, one the compiler has no way to re-check unless that unit is
recompiled in the same pass.

## Cheat sheet

| Fact | Detail |
|---|---|
| What sealing adds to a class file | `PermittedSubclasses` attribute (JVMS §4.7.31, class file 61.0 / Java 17), listing permitted subtypes by constant-pool index |
| `ACC_SEALED` flag | Does not exist. Not in JVMS §4.1 Table 4.1-B, in Java 21 or any later spec revision as of writing |
| `non-sealed` in the class file | Nothing at all — no attribute, no flag. Compile-time-only bookkeeping the compiler discards |
| Where enforcement happens | JVMS §5.3.5, "Deriving a Class," inside `ClassLoader.defineClass`, at every class load |
| What a rejected class throws | `IncompatibleClassChangeError` — a `LinkageError`, thrown before the class becomes usable |
| Locality rule | Permitted subclass must share the sealed supertype's run-time module, or (if non-`public`, no modules) its run-time package |
| Narrowing cast between sealed siblings | Compile error, not a runtime `ClassCastException` — the compiler can prove impossibility over a closed set |
| `Class.isSealed()` / `getPermittedSubclasses()` | Direct, one-level, non-recursive reads of the cached attribute metadata |
| Exhaustive `switch`'s exhaustiveness proof | Fixed at compile time; not re-derived from live `PermittedSubclasses` at run time |
| Stale-switch failure exception (Java 21+) | `java.lang.MatchException`, `(String, Throwable)` constructor |
| Stale-switch failure exception (before Java 21) | `IncompatibleClassChangeError` — same type as a load-time rejection, but a different mechanism entirely |
| Bytecode dispatch mechanism for pattern `switch` | `invokedynamic` to `SwitchBootstraps.typeSwitch`, then `lookupswitch` on the returned index, `default` arm throws the synthetic exception |

## Self-test

**Q1.** Why is `PermittedSubclasses` implemented as a class-file attribute instead of an access
flag?

<details><summary>Answer</summary>

Every bit position in the JVMS access-flags word (§4.1, Table 4.1-B) is already assigned, and more
fundamentally, sealing needs to carry a *list* of permitted names, not a single true/false bit —
an access flag has no room to name anything. A structured attribute, parsed by name
(`PermittedSubclasses`) rather than by a reserved bit, can carry an arbitrary-length array of
constant-pool indices, which is exactly the shape the feature needs.

</details>

**Q2.** A class file declares `class WealthVerdict implements Verdict {}` with no `sealed`,
`final`, or `non-sealed` modifier, where `Verdict` is a sealed interface. What happens?

<details><summary>Answer</summary>

`javac` refuses to compile it. Every direct subtype of a sealed type must declare exactly one of
`sealed`, `final`, or `non-sealed` — the compiler requires the author to state their sealing
intent explicitly rather than defaulting to one silently, precisely because an accidental default
either way (accidentally open, or accidentally further sealed) is a meaningful design decision
that should never happen by omission.

</details>

**Q3.** `RogueVerdict.class` was compiled at a time when `Verdict`'s `PermittedSubclasses`
attribute listed it. `Verdict` is later recompiled without `RogueVerdict` in `permits`, and the
old `RogueVerdict.class` is still on the classpath. What happens when something tries to load
`RogueVerdict`, and where does the failure occur?

<details><summary>Answer</summary>

`ClassLoader.defineClass` throws `IncompatibleClassChangeError` (measured message: `"Failed listed
permitted subclass check: class RogueVerdict is not a permitted subclass of Verdict"`) the moment
`RogueVerdict` is derived — JVMS §5.3.5's third bullet fails because no entry in `Verdict`'s
(new, four-name) `PermittedSubclasses` array refers to `RogueVerdict` by name. The failure is at
class *derivation*, inside the native class-parsing path, not at any point that ran `javac` — the
bytecode of `RogueVerdict.class` itself is completely valid on its own terms.

</details>

**Q4.** Why does casting between two `final` leaves of the same sealed hierarchy fail to compile,
while the identical cast between two implementors of an *open*, unsealed interface compiles and
only fails (if it fails) at run time?

<details><summary>Answer</summary>

Over a sealed hierarchy, the compiler has complete, closed knowledge of every class that could
ever implement the interface — sealing guarantees no future class can join the set. If two
sibling leaves are each `final` and unrelated to each other, the compiler can prove no single
object could ever be an instance of both, so the narrowing cast is provably always false and
becomes a compile error (JLS §5.5's narrowing reference conversion rules). Over an open interface,
the compiler cannot rule out a not-yet-written class implementing both, so it must permit the cast
and defer to a runtime `checkcast`, which throws `ClassCastException` only if the actual object at
that call site fails.

</details>

**Q5.** What, precisely, does `non-sealed` leave in the compiled class file of the class that
declares it?

<details><summary>Answer</summary>

Nothing sealing-specific. `javap -v` on a `non-sealed` class's file shows the same flags an
ordinary open class would carry (in the measured example, only `ACC_SUPER`) and no
`PermittedSubclasses` attribute, no synthetic marker method, and no other trace. `non-sealed` is a
compiler-enforced, source-level acknowledgement — required by `javac` when directly implementing a
sealed type, then completely discarded once compilation succeeds.

</details>

**Q6.** A module boundary separates a sealed interface from one of its `permits`-listed
implementations, and the implementation is not `public`. What does JVMS §5.3.5 do with this class
at load time, and why?

<details><summary>Answer</summary>

It throws `IncompatibleClassChangeError`. The rule's second bullet allows run-time-package
identity to substitute for run-time-module identity only when the permitted class is *not*
`public`, but that substitution still requires the two classes to be co-located — being in
different modules does not automatically satisfy "same run-time package" (packages are themselves
scoped per module in the module system), so a non-`public` class separated by a module boundary
from its sealed supertype fails both the module bullet and the package-substitution bullet
simultaneously. There is no locality path that permits this configuration to load.

</details>

**Q7.** Two versions of the same exhaustive-switch-over-a-sealed-type failure exist depending on
Java version. Name both exception types, the versions each applies to, and explain why they are
easy to conflate with an unrelated sealed-types failure.

<details><summary>Answer</summary>

Before Java 21, the synthetic default of an exhaustive switch expression throws
`IncompatibleClassChangeError`; from Java 21 onward it throws `java.lang.MatchException`,
constructed with a `(String, Throwable)` constructor. They are easy to conflate with the
load-time §5.3.5 rejection because, before 21, both failure modes threw the *identical* exception
type (`IncompatibleClassChangeError`) for two mechanically unrelated reasons — one a class-loading
linkage failure, the other a stale-switch runtime fallthrough — and Java 21's introduction of
`MatchException` specifically for the switch case was motivated by making the two distinguishable
by type alone.

</details>

**Q8.** Why does `Verdict.class.getPermittedSubclasses()` not help you enumerate the leaves of a
sealed hierarchy that is three levels deep (a sealed interface permitting another sealed
interface, which itself permits the concrete leaves)?

<details><summary>Answer</summary>

`getPermittedSubclasses()` returns only the *direct* entries of the caller's own
`PermittedSubclasses` attribute — one level, non-recursively. For a multi-level sealed hierarchy,
some of those direct entries are themselves sealed interfaces rather than concrete leaves, so
fully enumerating the concrete leaves requires recursively calling `isSealed()` /
`getPermittedSubclasses()` down through every intermediate sealed type yourself; the JVM's
metadata for any one type never flattens the whole tree for you.

</details>

## Deferred

None.

## Open questions

None.

---

**Leaves covered:** 3.10.1–3.10.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** D-152
**Target version:** Java 21 LTS
**Lines:** 944
